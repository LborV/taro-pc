"""Грубые оболочки деталей корпуса для этапа компоновки (не финальная геометрия)."""
from math import cos, sin

from build123d import Plane, Polygon, Pos, extrude

import params as P
from dummies import box_xyz


def _yz_prism(pts, x0, x1):
    """Призма: многоугольник в плоскости YZ (точки (y, z)), вытянутый по X от x0 до x1."""
    face = Plane.YZ.offset(x0) * Polygon(*pts, align=None)
    return extrude(face, amount=x1 - x0, dir=(1, 0, 0))


def panel_profile_front():
    """Лицевой контур панели (y, z) снизу вверх."""
    y_top, z_top = P.slope_point(P.UPPER_LEN)
    return [(0, 0), (0, P.Z_TILT), (y_top, z_top)]


def panel_shell():
    t = P.PANEL_T
    y_top, z_top = P.slope_point(P.UPPER_LEN)
    yb_top, zb_top = P.slope_point(P.UPPER_LEN, depth=t)
    yb_kn, zb_kn = P.slope_point(0, depth=t)
    pts = [(0, 0), (0, P.Z_TILT), (y_top, z_top), (yb_top, zb_top), (yb_kn, zb_kn), (t, 0)]
    plate = _yz_prism(pts, -P.W / 2, P.W / 2)
    xi = P.W / 2 - P.COVER_T - P.FIT
    flange = box_xyz(-xi, xi, t, t + P.PANEL_FLANGE_D, P.CH_T, P.CH_T + 3)
    panel = plate + flange
    # черновые вырезы — только чтобы на компоновке было видно экран/принтер/клавиши
    from build123d import Box, Location, Pos
    from dummies import key_centers, screen_plane
    win = Location(screen_plane()) * Pos(0, 0, 5) * Box(P.SCR_AA[0], P.SCR_AA[1], 30)
    cw, ch = P.PR_CUT
    prc = box_xyz(P.PR_X - cw / 2, P.PR_X + cw / 2, -1, t + 1, P.PR_CUT_Z0, P.PR_CUT_Z0 + ch)
    panel = panel - win - prc
    o = P.KEY_CAP_OPEN / 2
    for x in key_centers():
        panel = panel - box_xyz(x - o, x + o, -1, t + 1, P.KEY_Z - o, P.KEY_Z + o)
    return panel


def chassis_shell():
    xi = P.W / 2 - P.COVER_T - P.FIT
    plate = box_xyz(-xi, xi, P.PANEL_T + P.FIT, P.D, 0, P.CH_T)
    z_roof_in = roof_z() - P.COVER_T - P.FIT
    rear = box_xyz(-xi, xi, P.D - P.REAR_T, P.D, P.CH_T, z_roof_in)
    return plate + rear


def roof_z():
    return P.slope_point(P.UPPER_LEN)[1]


def cover_shell():
    t = P.COVER_T
    zr = roof_z()
    yb_top, _ = P.slope_point(P.UPPER_LEN, depth=P.PANEL_T)
    yb_kn, zb_kn = P.slope_point(0, depth=P.PANEL_T)
    side_pts = [(P.PANEL_T, 0), (P.D, 0), (P.D, zr), (yb_top, zr), (yb_kn, zb_kn)]
    xo = P.W / 2
    left = _yz_prism(side_pts, -xo, -xo + t)
    right = _yz_prism(side_pts, xo - t, xo)
    roof_pts = [(yb_top, zr - t), (P.D, zr - t), (P.D, zr), (yb_top, zr)]
    roof = _yz_prism(roof_pts, -xo, xo)
    return left + right + roof
