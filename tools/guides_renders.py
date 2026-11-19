"""Рендеры направляющих склейки (режим печати из частей). Запуск при PRINT_WHOLE=False."""
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
from build123d import Pos  # noqa: E402

import layout as L  # noqa: E402
import params as P  # noqa: E402
from tools.render import render  # noqa: E402

assert not P.print_whole(), "запускать с PRINT_WHOLE = False"
S = L.shells
OUT = "docs/instructions/img/"
bis = (0, -(math.cos(P.BAND_TILT) + math.cos(P.TILT)), -(math.sin(P.BAND_TILT) + math.sin(P.TILT)))
nb = math.hypot(*bis)
k = 30
d_band = tuple(c / nb * k for c in bis)
render([("front_band", Pos(*d_band) * S["front_band"], "#e53935", 1.0), ("front_screen", S["front_screen"], "#d8c8a4", 1.0)],
       "iso_front", OUT + "g1_front_guides.png", cam_dir=((0.9, 1.4, 0.5), (0, 0, 1)), size=(1300, 1000),
       title="Перед из частей: полка-нахлёст + 2 шипа на нижней половине, гнёзда в экранной")
render([("front_band", S["front_band"], "#e53935", 1.0), ("front_screen", S["front_screen"], "#d8c8a4", 1.0)],
       "iso_front", OUT + "g2_front_joined.png", cam_dir=((0.9, 1.4, 0.5), (0, 0, 1)), size=(1300, 1000),
       title="Сложено: полка подпирает экранную половину изнутри — стык ровный сам")
render([("side_l", Pos(-30, 0, -30) * S["side_l"], "#e53935", 1.0), ("side_r", Pos(30, 0, -30) * S["side_r"], "#e53935", 1.0),
        ("roof", S["roof"], "#d8c8a4", 1.0)], "iso_front", OUT + "g3_cover_guides.png",
       cam_dir=((0.6, -0.9, -0.9), (0, 0, 1)), size=(1300, 1000),
       title="Колпак из частей: на боках полки под крышу + шипы, шов по середине скругления")
