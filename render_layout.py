"""Рендеры компоновки (этап 3). Запуск: ~/.local/share/uv/tools/build123d-mcp/bin/python render_layout.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build123d import Box, Location, Pos  # noqa: E402

import layout as L  # noqa: E402
import params as P  # noqa: E402
from dummies import screen_plane, screen_step  # noqa: E402
from tools.render import render  # noqa: E402

BEIGE, BEIGE2, DARK = "#e3d3b0", "#d8c59c", "#3b3d40"
C = {"base": "#cdb98f", "front_band": BEIGE, "front_screen": "#e8d9b8", "rear": "#dccba6",
     "side_l": "#efe3c6", "side_r": "#efe3c6", "roof": "#f2e8cf",
     "rail_l": "#a08860", "rail_r": "#a08860",
     "roof_block_lf": "#a08860", "roof_block_lb": "#a08860", "roof_block_rf": "#a08860", "roof_block_rb": "#a08860",
     "screws": "#6d6f73", "inserts": "#c9a227", "feet": "#222222",
     "screen_bezel": DARK, "crowpanel": "#2f3b45",
     "scr_aa": "#cfe3f2",
     "scr_back_keepout": "#ff8a80", "scr_cable_keepout": "#ff5252", "scr_usb_keepout": "#ff5252",
     "pr_frame": "#26282b", "pr_body": "#8a8a8a", "pr_rear_keepout": "#ff8a80",
     "pr_clamp_l_keepout": "#ffa726", "pr_clamp_r_keepout": "#ffa726", "pr_lid_keepout": "#4fc3f7",
     "key_plate": "#9e9e9e", "key_switches": "#c62828", "key_caps": DARK, "key_wire_keepout": "#ff8a80",
     "xl4015": "#1565c0", "xl4015_side_keepout": "#ffa726", "pcf8574": "#5c6bc0",
     "spk_chamber_env": "#a1887f", "speaker": "#212121", "kcd1": "#1a1a1a", "cable": "#111111"}
shapes = {**L.shells, **L.dummies, **L.hardware}
shapes["crowpanel"] = screen_step()
shapes["scr_aa"] = Location(screen_plane()) * Pos(0, 0, 0.05) * Box(P.SCR_AA[0], P.SCR_AA[1], 0.1)
SKIP = {"scr_pcb", "scr_glass"}


def objs(exclude=(), keepouts=True, ko_op=0.3):
    out = []
    for n, col in C.items():
        if n in exclude or n in SKIP:
            continue
        ko = n.endswith("keepout")
        if ko and not keepouts:
            continue
        out.append((n, shapes[n], col, ko_op if ko else 1.0))
    return out


LEG = [("экран CrowPanel 5\" (STEP)", C["crowpanel"]), ("принтер CSN-A2", C["pr_body"]),
       ("клавиши MX", C["key_switches"]), ("XL4015", C["xl4015"]), ("PCF8574", C["pcf8574"]),
       ("камера динамика", C["spk_chamber_env"]), ("зоны: колодки / подстроечник", C["pr_clamp_l_keepout"]),
       ("зоны: кабели / разъёмы", C["scr_cable_keepout"]), ("откидывание крышки лотка", C["pr_lid_keepout"])]
NOCOVER = {"side_l", "side_r", "roof", "roof_block_lf", "roof_block_lb", "roof_block_rf", "roof_block_rb"}
EXPLODE = {"roof": (0, 0, 120), "roof_block_lf": (-50, 0, 95), "roof_block_lb": (-50, 0, 95),
           "roof_block_rf": (50, 0, 95), "roof_block_rb": (50, 0, 95), "side_l": (-110, 0, 40), "side_r": (110, 0, 40),
           "front_screen": (0, -90, 40), "screen_bezel": (0, -130, 60), "front_band": (0, -80, 0), "rear": (0, 90, 0),
           "rail_l": (0, 0, 70), "rail_r": (0, 0, 70), "base": (0, 0, -50), "feet": (0, 0, -50)}
PARTS_ONLY = list(EXPLODE) + ["screws"]


def exploded():
    from build123d import Pos as _P
    out = []
    for n in C:
        if n in EXPLODE or n == "screws":
            d = EXPLODE.get(n, (0, 0, 0))
            out.append((n, _P(*d) * shapes[n], C[n], 1.0))
    return out


if __name__ == "__main__" and "--panels" in sys.argv:
    D = "renders/layout/"
    render(exploded(), "iso_front", D + "10_exploded.png", title="Разнесённая: каркас + колпак (бока, крыша)")
    render(objs(keepouts=False), "bottom", D + "11_bottom_screws.png", title="Снизу: 10 винтов M3 потай + 4 ножки")
    render(objs(exclude=NOCOVER | {"crowpanel", "scr_aa"}, keepouts=False), "iso_rear", D + "12_carcass_nocover.png",
           title="Каркас без колпака: балки, бобышки, вставки")
    render(objs(keepouts=False), "iso_front", D + "1_iso_front.png", title="3/4 спереди")
    sys.exit(0)

if __name__ == "__main__":
    D = "renders/layout/"
    render(objs(keepouts=False), "iso_front", D + "1_iso_front.png", title="3/4 спереди")
    render(objs(keepouts=False), "iso_front_r", D + "2_iso_front_right.png", title="3/4 спереди справа (решётка)")
    render(objs(keepouts=False), "front", D + "3_front.png", title="Спереди")
    render(objs(keepouts=False), "right", D + "4_right.png", title="Справа")
    render(objs(keepouts=False), "rear", D + "5_rear.png", title="Сзади")
    render(objs(exclude=NOCOVER), "right", D + "6_section_x+34_printer.png", clip_spec=("x", 34.0, True),
           title="Разрез X=+34 (принтер, экран), без колпака", legend=LEG)
    render(objs(exclude=NOCOVER), "right", D + "7_section_x-62_keys.png", clip_spec=("x", -62.5, True),
           title="Разрез X=−62 (клавиши, PCF8574, XL4015)", legend=LEG)
    render(objs(exclude=NOCOVER | {"pr_lid_keepout"}), "top", D + "8_top_nocover.png", title="Сверху без колпака",
           legend=LEG)
    render(objs(exclude=NOCOVER | {"pr_lid_keepout"}), "iso_rear", D + "9_iso_rear_nocover.png",
           title="3/4 сзади без колпака", legend=LEG)
