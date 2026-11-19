"""Рендеры для PDF-инструкции по сборке → docs/instructions/img/*.png

Запуск: ~/.local/share/uv/tools/build123d-mcp/bin/python tools/instruction_renders.py
"""
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from build123d import Compound, Location, Pos  # noqa: E402

import fasteners as F  # noqa: E402
import params as P  # noqa: E402
from dummies import screen_plane  # noqa: E402
from render_layout import C, shapes  # noqa: E402
from tools.render import render  # noqa: E402

OUT = "docs/instructions/img/"
HI = "#e53935"      # новая деталь на шаге
GHOST = "#d9d4c8"   # уже установленное
GREY = "#bdb7aa"
ONLY = [a for a in sys.argv[1:]]


WHOLE = P.print_whole()
ALIAS = {"front_band": "front", "front_screen": None, "side_l": "cover", "side_r": None, "roof": None} if WHOLE else {}


def want(name):
    return not ONLY or any(o in name for o in ONLY)


def R(name, objs, view, **kw):
    if want(name):
        render([x for x in objs if x is not None], view, OUT + name + ".png", **kw)


def o(name, col=None, op=1.0, d=(0, 0, 0)):
    if name in ALIAS:
        name = ALIAS[name]
        if name is None:
            return None
    s = shapes[name]
    if d != (0, 0, 0):
        s = Pos(*d) * s
    return (name, s, col or C[name], op)


def along(n, k):
    return tuple(c * k for c in n)


N_SCR = (0, -math.cos(P.TILT), math.sin(P.TILT))      # нормаль экранной грани (наружу)
N_BAND = (0, -math.cos(P.BAND_TILT), math.sin(P.BAND_TILT))
INSIDE_FRONT = ((0.55, 1.4, 0.75), (0, 0, 1))          # взгляд на переднюю панель изнутри (сзади)
INSIDE_REAR = ((-0.55, -1.4, 0.75), (0, 0, 1))
BELOW = ((0.35, -0.9, -1.3), (0, 0, 1))

COVER = ["cover"] if WHOLE else ["side_l", "side_r", "roof"]
FRONT = (["front"] if WHOLE else ["front_band", "front_screen"]) + ["screen_bezel"]
SCREEN = ["crowpanel", "scr_aa"]
PRINTER = ["pr_frame", "pr_body"]
KEYS = ["key_plate", "key_switches", "key_caps"]
INNER = ["xl4015", "pcf8574", "speaker_box", "speaker"]
REAR_HW = ["kcd1", "cable"]

bosses = F.bottom_bosses()
loc_scr = Location(screen_plane())


def scr_pt(hx, hy, z):
    v = loc_scr * Pos(hx, hy, z)
    p = v.position
    return (p.X, p.Y, p.Z)


def boss_pts(part, z=P.WALL + 2):
    return [(x, y, z) for (pp, x, y) in bosses if pp == part]


def screws_for(parts, z0=-22.0):
    return Compound(children=[F.screw((x, y, z0), (0, 0, 1), 10.0) for (pp, x, y) in bosses if pp in parts])


def all_labels():
    cnt = {"П": 0, "З": 0, "К": 0}
    out = []
    for pp, x, y in bosses:
        k = "П" if pp == "front_band" else "З" if pp == "rear" else "К"
        cnt[k] += 1
        out.append((k + str(cnt[k]), (x, y, 0)))
    return out


# ============================================================ 0. обложка, обзор
R("00_cover", [o(n) for n in COVER + FRONT + ["rear", "base", "feet"] + SCREEN + PRINTER + ["key_caps"]],
  "iso_front", size=(1600, 1200), zoom=1.05)
R("01_rear_view", [o(n) for n in COVER + FRONT + ["rear", "base", "feet"] + REAR_HW], "iso_rear", size=(1200, 900))

# ============================================================ 1. печатные детали по одной
GALLERY = {"p_base": ["base"], "p_screen_bezel": ["screen_bezel"], "p_rear": ["rear"]}
if WHOLE:
    GALLERY.update({"p_front": ["front"], "p_cover": ["cover"]})
else:
    GALLERY.update({"p_front_band": ["front_band"], "p_front_screen": ["front_screen"], "p_side_l": ["side_l"],
                    "p_side_r": ["side_r"], "p_roof": ["roof"]})
for name, parts in GALLERY.items():
    view = "iso_front"
    cd = None
    if name in ("p_side_l", "p_cover"):
        cd = ((-1.3, -0.5, 0.6), (0, 0, 1))
    if name in ("p_side_r",):
        cd = ((1.3, -0.5, 0.6), (0, 0, 1))
    if name == "p_rear":
        cd = ((0.6, 1.3, 0.6), (0, 0, 1))
    R(name, [o(n, "#d8c8a4") for n in parts], view, size=(700, 560), cam_dir=cd, edges=True)

# ============================================================ 2. вставки
fb = boss_pts("front_band", P.WALL + P.BOSS_H)
labs = [(str(i + 1), p) for i, p in enumerate(fb)]
labs += [(str(i + 4), scr_pt(hx, hy, P.SCR_Z_PCB_FRONT)) for i, (hx, hy) in enumerate(P.SCR_HOLES)]
R("10_inserts_front", [o("front_band", "#d8c8a4"), o("front_screen", "#e5d7b6")], "iso_front",
  cam_dir=INSIDE_FRONT, labels=labs, size=(1300, 1000),
  title="Передняя панель изнутри: 7 вставок M3")
labs = [(str(i + 1), p) for i, p in enumerate(boss_pts("rear", P.WALL + P.BOSS_H))]
R("11_inserts_rear", [o("rear", "#d8c8a4")], "iso_front", cam_dir=INSIDE_REAR, labels=labs, size=(1300, 1000),
  title="Задняя стенка изнутри: 3 вставки M3")
labs = [(str(i + 1), p) for i, p in enumerate(boss_pts("side_l", P.WALL) + boss_pts("side_r", P.WALL))]
R("12_inserts_cover", [o(n, "#e5d7b6") for n in COVER], "iso_front", cam_dir=BELOW, labels=labs,
  size=(1300, 1000), title="Колпак снизу: 4 вставки M3 в бобышках боков")

# ============================================================ 3. склейка передней панели (только если печать из частей)
if WHOLE:
    ONLY_SKIP = {"20_glue_front", "70_cover_glue"}
else:
    ONLY_SKIP = set()
_R = R


def R(name, objs, view, **kw):  # noqa: F811
    if name not in ONLY_SKIP:
        _R(name, objs, view, **kw)



k = 35
bis = (0, -(math.cos(P.BAND_TILT) + math.cos(P.TILT)), -(math.sin(P.BAND_TILT) + math.sin(P.TILT)))
nb = math.hypot(*bis)
seam_y, seam_z = P.Y_TILT, P.BAND_H
R("20_glue_front", [o("front_band", HI, d=(0, -10, -k)), o("front_screen", "#d8c8a4", d=(0, 0, 10))],
  "iso_front", size=(1300, 1000),
  labels=[("клей", (0, seam_y, seam_z + 10)), ("клей", (0, seam_y - 10, seam_z - k))],
  title="Склеить нижнюю и экранную половины передней панели")
R("21_bezel", [o("front_band", GHOST), o("front_screen", "#d8c8a4"),
               o("screen_bezel", "#3b3d40", d=along(N_SCR, 45))],
  "iso_front", size=(1300, 1000), title="Тёмная рамка — в карман экранной грани")

# ============================================================ 4. экран
labs = [(str(i + 1), scr_pt(hx, hy, P.SCR_Z_PCB_BACK - 60)) for i, (hx, hy) in enumerate(P.SCR_HOLES)]
R("30_screen", [o("front_band", GHOST), o("front_screen", "#d8c8a4"), o("screen_bezel"),
                o("crowpanel", d=along(N_SCR, -60))],
  "iso_front", cam_dir=INSIDE_FRONT, labels=labs, size=(1300, 1000),
  title="Экран: стеклом в окно, 4 винта M3×6 через плату в стойки")
R("31_screen_done", [o("front_band", GHOST), o("front_screen", "#d8c8a4"), o("screen_bezel"), o("crowpanel"),
                     o("scr_aa")], "iso_front", size=(1300, 1000), title="Вид спереди: экран на месте")

# ============================================================ 5. клавиши
xs = [P.KEY_X + (i - 1) * P.KEY_PITCH for i in range(3)]
R("40_keys_plate", [o("front_band", "#d8c8a4"), o("front_screen", GHOST),
                    o("key_plate", HI, d=along(N_BAND, -40)), o("key_switches", "#c62828", d=along(N_BAND, -40))],
  "iso_front", cam_dir=INSIDE_FRONT, size=(1300, 1000),
  title="Переключатели защёлкнуть в пластину, пластину — изнутри к панели")
R("41_keycaps", [o("front_band", "#d8c8a4"), o("front_screen", GHOST), o("key_switches"),
                 o("key_caps", "#3b3d40", d=along(N_BAND, 25))],
  "iso_front", size=(1300, 1000), title="Колпачки — снаружи на крестовины")

# ============================================================ 6. принтер
R("50_printer", [o("front_band", "#d8c8a4"), o("front_screen", GHOST), o("screen_bezel"), o("crowpanel"),
                 o("key_caps"), o("pr_frame", "#26282b", d=along(N_BAND, 90)),
                 o("pr_body", "#8a8a8a", d=along(N_BAND, 90))],
  "iso_front", size=(1300, 1000), title="Принтер — спереди в вырез до упора рамкой")
R("51_printer_clamps", [o("front_band", "#d8c8a4"), o("front_screen", GHOST), o("pr_body"), o("pr_frame"),
                        o("pr_clamp_l_keepout", "#ffa726", 0.55), o("pr_clamp_r_keepout", "#ffa726", 0.55)],
  "iso_front", cam_dir=INSIDE_FRONT, size=(1300, 1000), title="Сзади: две штатные колодки в пазы, винты до упора")

# ============================================================ 7. задняя стенка
sx, sz = P.SW_POS
cx, cz = P.CABLE_POS
rp = lambda x, z: (x, P.y_rear(z), z)  # noqa: E731
R("60_rear", [o("rear", "#d8c8a4"), o("kcd1", "#1a1a1a"), o("cable")], "iso_rear", size=(1300, 1000),
  labels=[("1", rp(sx, sz)), ("2", rp(cx, cz))], title="Задняя стенка: 1 — выключатель, 2 — кабель 12 В")

# ============================================================ 8. колпак
R("70_cover_glue", [o("side_l", "#e5d7b6", d=(-45, 0, 0)), o("side_r", "#e5d7b6", d=(45, 0, 0)),
                    o("roof", HI, d=(0, 0, 45))], "iso_front", size=(1300, 1000),
  title="Колпак: бок + крыша + бок, склеить на ровном столе")

# ============================================================ 9. дно
labs = [(f"н{i + 1}", (x, y, -3)) for i, (x, y) in enumerate(P.FEET)]
R("80_base_feet", [o("base", "#d8c8a4"), o("feet")], "bottom", size=(1300, 1000), labels=labs,
  title="Дно снизу: 4 резиновые ножки")
R("81_base_inner", [o("base", "#d8c8a4")] + [o(n) for n in INNER], "iso_front", size=(1300, 1000),
  labels=[("XL4015", shapes["xl4015"].center()), ("PCF8574", shapes["pcf8574"].center()),
          ("динамик", shapes["speaker_box"].center())],
  title="Дно сверху: понижайка, PCF8574, камера динамика")

# ============================================================ 10. передняя панель → дно
front_all = FRONT + SCREEN + PRINTER + KEYS
R("90_front_on_base", [o("base", GHOST)] + [o(n) for n in INNER] +
  [o(n, HI if n in ("front_band", "front_screen") else None, d=(0, -60, 25)) for n in front_all],
  "iso_front", size=(1300, 1000), title="Передняя панель в сборе → на дно")
labs = [(str(i + 1), (x, y, 0)) for i, (x, y, z) in enumerate(boss_pts("front_band", 0))]
R("91_front_screws", [o("base", "#d8c8a4"), o("feet"), o("front_band"), o("front_screen"),
                      ("scr", screws_for({"front_band"}), "#111111", 1.0)],
  "bottom", size=(1300, 1000), labels=labs, title="Снизу: 3 винта M3×8 потай")

# ============================================================ 11. задняя стенка → дно
R("92_rear_on_base", [o("base", GHOST)] + [o(n, GHOST) for n in front_all + INNER] +
  [o("rear", HI, d=(0, 60, 25)), o("kcd1", d=(0, 60, 25)), o("cable", d=(0, 60, 25))],
  "iso_rear", size=(1300, 1000), title="Задняя стенка → на дно")
labs = [(str(i + 1), (x, y, 0)) for i, (x, y, z) in enumerate(boss_pts("rear", 0))]
R("93_rear_screws", [o("base", "#d8c8a4"), o("feet"), o("front_band"), o("rear"),
                     ("scr", screws_for({"rear"}), "#111111", 1.0)],
  "bottom", size=(1300, 1000), labels=labs, title="Снизу: 3 винта M3×8 потай")

# ============================================================ 12. каркас без колпака (для проверки)
R("95_open", [o(n) for n in ["base", "feet", "rear"] + front_all + INNER + REAR_HW], "iso_rear",
  size=(1300, 1000), title="Каркас перед закрытием: всё подключено и доступно")
tab_pts = []
for x in (-P.TAB_X, P.TAB_X):
    tab_pts.append(("Г", (x, F.front_in_y(P.TAB_Z) + 10, P.TAB_Z + 6)))
    tab_pts.append(("Г", (x, F.rear_in_y(P.TAB_Z) - 10, P.TAB_Z + 6)))
R("96_tabs", [o(n, "#d8c8a4") for n in ["base", "rear", "front_band", "front_screen"]], "iso_rear",
  size=(1300, 1000), labels=tab_pts, title="Г-язычки наверху панелей — войдут в пазы под крышей")

# ============================================================ 13. колпак
R("97_cover_down", [o(n) for n in ["base", "feet", "rear"] + front_all + REAR_HW] +
  [o(n, HI, d=(0, 0, 110)) for n in COVER], "iso_front", size=(1300, 1000),
  title="Колпак — строго сверху вниз, язычки в пазы")
labs = [(str(i + 1), (x, y, 0)) for i, (x, y, z) in enumerate(boss_pts("side_l", 0) + boss_pts("side_r", 0))]
R("98_cover_screws", [o(n) for n in ["base", "feet"] + COVER + ["front_band", "rear"]] +
  [("scr", screws_for({"side_l", "side_r"}), "#111111", 1.0)], "bottom", size=(1300, 1000), labels=labs,
  title="Снизу: 4 винта M3×8 потай")
R("99_all_screws", [o(n) for n in ["base", "feet"] + COVER + ["front_band", "rear"]] +
  [("scr", screws_for({"front_band", "rear", "side_l", "side_r"}), "#111111", 1.0)], "bottom",
  size=(1300, 1000),
  labels=all_labels(),
  title="Все 10 винтов снизу: П — перед, З — зад, К — колпак")
R("100_final", [o(n) for n in COVER + FRONT + ["rear", "base", "feet"] + SCREEN + PRINTER + ["key_caps"]],
  "iso_front_r", size=(1300, 1000), title="Готово")

# ============================================================ угол обзора экрана (сбоку)
def view_angle_numbers(eye_h, eye_d, tilt_deg=None):
    """Угол между линией взгляда и нормалью экрана, градусы. eye_d — от передней кромки корпуса."""
    t = math.radians(tilt_deg if tilt_deg is not None else P.TILT_DEG)
    c = scr_pt(0, 0, 0)
    ey, ez = -eye_d, eye_h
    vy, vz = ey - c[1], ez - c[2]
    ny, nz = -math.cos(t), math.sin(t)
    cosang = (vy * ny + vz * nz) / math.hypot(vy, vz)
    return math.degrees(math.acos(cosang)), c


EYES = [("сидя", 430.0, 480.0, (46, 125, 50)), ("стоя", 650.0, 420.0, (198, 40, 40))]
if want("05_view_angle"):
    c = scr_pt(0, 0, 0)
    lines = []
    ext = []
    for name, h, dd, col in EYES:
        ang, _ = view_angle_numbers(h, dd)
        k = 0.45
        pe = (c[0] + 120, c[1] + (-dd - c[1]) * k, c[2] + (h - c[2]) * k)
        lines.append((c, pe, col, 4, f"{name}: {ang:.0f}° от нормали"))
        ext.append(pe)
    pn = (c[0] + 120, c[1] + N_SCR[1] * 120, c[2] + N_SCR[2] * 120)
    lines.append((c, pn, (21, 101, 192), 3, "нормаль экрана"))
    ext.append(pn)
    R("05_view_angle", [o(n) for n in COVER + FRONT + ["rear", "base", "feet"] + SCREEN + PRINTER + ["key_caps"]],
      "right", size=(1300, 1000), lines=lines, extra_bounds=ext,
      title=f"Угол обзора: грань экрана {P.TILT_DEG:.0f}° от вертикали, центр экрана на высоте {c[2]:.0f} мм")
    for name, h, dd, col in EYES:
        a1, _ = view_angle_numbers(h, dd)
        a2, _ = view_angle_numbers(h, dd, 12.0)
        print(f"VIEW {name}: eye {h:.0f} high {dd:.0f} away → {a1:.1f}° (tilt {P.TILT_DEG}) vs {a2:.1f}° (tilt 12)")
