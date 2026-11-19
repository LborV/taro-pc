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
C = {"panel": BEIGE, "cover": BEIGE, "chassis": BEIGE2, "screen_bezel": DARK, "crowpanel": "#2f3b45",
     "scr_aa": "#cfe3f2",
     "scr_back_keepout": "#ff8a80", "scr_cable_keepout": "#ff5252", "scr_usb_keepout": "#ff5252",
     "pr_frame": "#26282b", "pr_body": "#8a8a8a", "pr_rear_keepout": "#ff8a80",
     "pr_clamp_l_keepout": "#ffa726", "pr_clamp_r_keepout": "#ffa726", "pr_lid_keepout": "#4fc3f7",
     "key_plate": "#9e9e9e", "key_switches": "#c62828", "key_caps": DARK, "key_wire_keepout": "#ff8a80",
     "xl4015": "#1565c0", "xl4015_side_keepout": "#ffa726", "pcf8574": "#5c6bc0",
     "spk_chamber_env": "#a1887f", "speaker": "#212121", "kcd1": "#1a1a1a", "cable": "#111111"}
shapes = {**L.shells, **L.dummies}
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
if __name__ == "__main__":
    D = "renders/layout/"
    NOCOVER = {"cover"}
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
