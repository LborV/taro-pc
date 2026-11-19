"""Рендеры компоновки (этап 3). Запуск: ~/.local/share/uv/tools/build123d-mcp/bin/python render_layout.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tools.render import render
import layout as L
from dummies import screen_step

C = {"panel": "#e6d8b8", "cover": "#efe4c8", "chassis": "#c9b48a", "crowpanel": "#37474f",
     "scr_back_keepout": "#ff8a80", "scr_cable_keepout": "#ff5252", "scr_usb_keepout": "#ff5252",
     "pr_frame": "#3d3d3d", "pr_body": "#8a8a8a", "pr_rear_keepout": "#ff8a80",
     "pr_clamp_l_keepout": "#ffa726", "pr_clamp_r_keepout": "#ffa726", "pr_lid_keepout": "#4fc3f7",
     "key_plate": "#9e9e9e", "key_switches": "#c62828", "key_caps": "#455a64", "key_wire_keepout": "#ff8a80",
     "xl4015": "#1565c0", "xl4015_side_keepout": "#ffa726", "pcf8574": "#5c6bc0",
     "spk_chamber_env": "#a1887f", "speaker": "#212121", "kcd1": "#b71c1c", "cable": "#111111"}
shapes = {**L.shells, **L.dummies}
shapes["crowpanel"] = screen_step()
skip = {"scr_pcb", "scr_glass"}

def objs(exclude=(), keepouts=True, ko_op=0.3):
    out = []
    for n, col in C.items():
        if n in exclude or n in skip:
            continue
        ko = n.endswith("keepout") or n.endswith("_env")
        if ko and not keepouts:
            continue
        out.append((n, shapes[n], col, ko_op if n.endswith("keepout") else 1.0))
    return out

LEG = [("экран CrowPanel 5\" (STEP)", C["crowpanel"]), ("принтер CSN-A2", C["pr_body"]),
       ("клавиши MX", C["key_switches"]), ("XL4015", C["xl4015"]), ("PCF8574", C["pcf8574"]),
       ("камера динамика", C["spk_chamber_env"]), ("KCD1-11", C["kcd1"]),
       ("зоны: колодки/подстроечник", C["pr_clamp_l_keepout"]), ("зоны: кабели/разъёмы", C["scr_cable_keepout"]),
       ("откидывание крышки лотка", C["pr_lid_keepout"])]
D = "renders/layout/"
render(objs(keepouts=False), "front", D + "1_front.png", title="Вид спереди")
render(objs(exclude={"cover"}), "right", D + "2_side_x+10.png", clip_spec=("x", 10.0, True),
       title="Сбоку, разрез X=+10 (центр экрана), без колпака", legend=LEG)
render(objs(exclude={"cover"}), "right", D + "3_side_x+60.png", clip_spec=("x", 60.0, True),
       title="Сбоку, разрез X=+60 (принтер, динамик, выключатель)", legend=LEG)
render(objs(exclude={"cover"}), "right", D + "4_side_x-62.png", clip_spec=("x", -62.0, True),
       title="Сбоку, разрез X=-62 (клавиши, PCF8574, XL4015)", legend=LEG)
render(objs(exclude={"cover", "pr_lid_keepout"}), "top", D + "5_top_nocover.png",
       title="Сверху без колпака", legend=LEG)
render(objs(keepouts=False), "iso_front", D + "6_iso_front.png", title="3/4 спереди")
render(objs(exclude={"cover", "pr_lid_keepout"}), "iso_rear", D + "7_iso_rear_nocover.png",
       title="3/4 сзади без колпака", legend=LEG)
