"""Экспорт деталей на печать: out/stl/*.stl (в ориентации печати, на z=0) + out/step/*.step (в сборке).

Запуск: ~/.local/share/uv/tools/build123d-mcp/bin/python tools/export_parts.py
"""
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from build123d import Axis, Compound, Pos, export_step, export_stl  # noqa: E402

import envelope  # noqa: E402
import layout as L  # noqa: E402
import params as P  # noqa: E402
from parts.keycap import keycap  # noqa: E402

OUT_STL, OUT_STEP = "out/stl/", "out/step/"
os.makedirs(OUT_STL, exist_ok=True)
os.makedirs(OUT_STEP, exist_ok=True)


def to_bed(shape, rot=()):
    """Повернуть (список (ось, угол)) и поставить на стол: min Z = 0, центр XY = 0."""
    s = shape
    for ax, ang in rot:
        s = s.rotate(ax, ang)
    bb = s.bounding_box()
    return Pos(-(bb.min.X + bb.max.X) / 2, -(bb.min.Y + bb.max.Y) / 2, -bb.min.Z) * s


def tilt_to_down(normal_yz):
    """Угол поворота вокруг X, переводящий нормаль (0, ny, nz) в (0, 0, -1)."""
    ny, nz = normal_yz
    return math.degrees(-math.pi / 2 - math.atan2(nz, ny))


FRONT_P, COVER_P = envelope.groups()
N_SCR = (-math.cos(P.TILT), math.sin(P.TILT))
N_SIDE_R = None

plan = {}   # name -> (shape, rot, how, colour)
plan["base"] = (L.shells["base"], (), "низом вниз, бортик вверх", "бежевый")
plan["rear"] = (L.shells["rear"], (), "стоя, как в сборке (втулка ввода снаружи мешает класть плашмя); кайма 8 мм", "бежевый")
plan["screen_bezel"] = (L.shells["screen_bezel"], ((Axis.X, tilt_to_down(N_SCR)),), "лицом вниз", "тёмно-серый")
if P.print_whole():
    plan["front"] = (L.shells["front"], (), "стоя, как в сборке; кайма 8 мм", "бежевый")
    plan["cover"] = (L.shells["cover"], ((Axis.X, 180),), "крышей вниз; под ручкой мост 30 мм или поддержка", "бежевый")
else:
    plan["front_band"] = (L.shells["front_band"], ((Axis.X, tilt_to_down((-math.cos(P.BAND_TILT), math.sin(P.BAND_TILT)))),),
                          "лицом вниз", "бежевый")
    plan["front_screen"] = (L.shells["front_screen"], ((Axis.X, tilt_to_down(N_SCR)),), "лицом вниз", "бежевый")
    plan["side_l"] = (L.shells["side_l"], ((Axis.Y, -(90 - P.SIDE_LEAN_DEG)),), "наружной стороной вниз", "бежевый")
    plan["side_r"] = (L.shells["side_r"], ((Axis.Y, 90 - P.SIDE_LEAN_DEG),), "наружной стороной вниз", "бежевый")
    plan["roof"] = (L.shells["roof"], ((Axis.X, 180),), "верхом вниз", "бежевый")

report = []
for name, (shape, rot, how, col) in plan.items():
    s = to_bed(shape, rot)
    bb = s.bounding_box()
    fits = bb.size.X <= P.BED_X and bb.size.Y <= P.BED_Y and bb.size.Z <= P.BED_Z
    fits_rot = bb.size.Y <= P.BED_X and bb.size.X <= P.BED_Y and bb.size.Z <= P.BED_Z
    export_stl(s, OUT_STL + f"taro_{name}.stl", tolerance=0.02, angular_tolerance=0.1)
    export_step(shape, OUT_STEP + f"taro_{name}.step")
    report.append({"file": f"taro_{name}.stl", "size": [round(bb.size.X, 1), round(bb.size.Y, 1), round(bb.size.Z, 1)],
                   "orient": how, "colour": col, "fits_bed": bool(fits or fits_rot), "qty": 1,
                   "volume_cm3": round(shape.volume / 1000, 1)})
    print(f"{name:14s} {bb.size.X:6.1f} × {bb.size.Y:6.1f} × {bb.size.Z:6.1f}  fits={fits or fits_rot}  {how}")

# колпачки: корпус + символ (печать верхом вниз)
names = {1: "one_card", 2: "three_cards", 3: "question"}
for k, nm in names.items():
    body, sym = keycap(k)
    both = Compound(children=[body, sym]).rotate(Axis.X, 180)
    bb = both.bounding_box()
    shift = Pos(-(bb.min.X + bb.max.X) / 2, -(bb.min.Y + bb.max.Y) / 2, -bb.min.Z)
    b2 = shift * body.rotate(Axis.X, 180)
    s2 = shift * sym.rotate(Axis.X, 180)
    export_stl(b2, OUT_STL + f"taro_keycap_{k}_{nm}.stl", tolerance=0.01, angular_tolerance=0.1)
    export_stl(s2, OUT_STL + f"taro_keycap_{k}_{nm}_SYMBOL.stl", tolerance=0.01, angular_tolerance=0.1)
    export_step(Compound(children=[body, sym]), OUT_STEP + f"taro_keycap_{k}_{nm}.step")
    report.append({"file": f"taro_keycap_{k}_{nm}.stl + _SYMBOL.stl", "size": [P.KEY_CAP[0], P.KEY_CAP[1], P.KEY_CAP[2]],
                   "orient": "верхом вниз; _SYMBOL — вторым цветом (импортировать вместе как одну деталь)",
                   "colour": "тёмно-серый + светлый символ", "fits_bed": True, "qty": 1,
                   "volume_cm3": round(body.volume / 1000, 2)})
    print(f"keycap {k} ok")

# сборка целиком (для просмотра в CAD)
asm = Compound(children=[L.shells[n] for n in L.shells])
export_step(asm, OUT_STEP + "taro_assembly_case.step")
json.dump(report, open("out/parts.json", "w"), ensure_ascii=False, indent=1)
print("-> out/stl, out/step, out/parts.json")
