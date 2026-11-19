"""Оболочка корпуса по концепт-арту: тело, полая скорлупа, черновое деление на детали.

Это ещё этап компоновки: форма, вырезы и линии разъёма — финальные детали
(пазы, бобышки, вставки, рёбра) будут в parts/*.py.
"""
import math
from math import cos, sin

from build123d import (Axis, Box, Cylinder, Location, Plane, Polygon, Pos, Rot, chamfer,
                       extrude, fillet, offset)

import params as P
from dummies import band_plane, box_xyz, key_centers, screen_plane


# ------------------------------------------------------------------ примитивы
def _prism_yz(pts, x0, x1):
    face = Plane.YZ.offset(x0) * Polygon(*pts, align=None)
    return extrude(face, amount=x1 - x0, dir=(1, 0, 0))


def _prism_xz(pts, y0, y1):
    face = Plane.XZ * Polygon(*pts, align=None)
    return Pos(0, y0, 0) * extrude(face, amount=y1 - y0, dir=(0, 1, 0))


def side_profile():
    """Силуэт сбоку (y, z)."""
    return [(0, 0), (P.D, 0), (P.Y_TOP_REAR, P.H), (P.Y_TOP_FRONT, P.H), (P.Y_TILT, P.BAND_H)]


def front_profile():
    hw0, hw1 = P.W / 2, P.half_w(P.H)
    return [(-hw0, 0), (hw0, 0), (hw1, P.H), (-hw1, P.H)]


# ------------------------------------------------------------------ тело
def body_raw():
    a = _prism_yz(side_profile(), -P.W, P.W)
    b = _prism_xz(front_profile(), -10, P.D + 10)
    return a & b


def body():
    b = body_raw()
    try:
        b = fillet(b.edges(), P.R_EDGE)
    except Exception as e:  # noqa: BLE001
        print("fillet all edges failed:", e)
    hx, hy, hd = P.HANDLE
    yc = (P.Y_TOP_FRONT + P.Y_TOP_REAR) / 2
    pocket = Pos(0, yc, P.H - hd / 2 + 0.01) * Box(hx, hy, hd + 0.02)
    pocket = fillet(pocket.edges().filter_by(Axis.Z), P.HANDLE_R)
    try:
        pocket = fillet(pocket.edges().group_by(Axis.Z)[0], 3.0)
    except Exception:  # noqa: BLE001
        pass
    return b - pocket


def shell(b=None):
    b = b or body()
    inner = offset(b, amount=-P.WALL)
    return b - inner, inner


# ------------------------------------------------------------------ вырезы
def _z_face():
    return P.SCR_RECESS + P.SCR_Z_GLASS_FRONT  # лицо панели в координатах экрана


def _screen_cuts():
    loc = Location(screen_plane())
    gw, gh = P.SCR_GLASS
    bw, bh = gw + 2 * P.SCR_BEZEL_W, gh + 2 * P.SCR_BEZEL_W
    pocket = loc * Pos(0, P.SCR_GLASS_CY, _z_face() + 5 - P.SCR_RECESS) * Box(bw, bh, 10)
    through = loc * Pos(0, P.SCR_GLASS_CY, 0) * Box(gw + 2 * P.SCR_BEZEL_GAP, gh + 2 * P.SCR_BEZEL_GAP, 40)
    return pocket + through


def screen_bezel():
    """Тёмно-серая рамка-вставка: заподлицо с панелью, окно по АО с фаской."""
    loc = Location(screen_plane())
    gw, gh = P.SCR_GLASS
    bw, bh = gw + 2 * P.SCR_BEZEL_W - 2 * P.FIT, gh + 2 * P.SCR_BEZEL_W - 2 * P.FIT
    t = P.SCR_RECESS
    frame = Pos(0, P.SCR_GLASS_CY, _z_face() - t / 2) * Box(bw, bh, t)
    frame = fillet(frame.edges().filter_by(Axis.Z), 2.0)
    aw, ah = P.SCR_AA
    frame = frame - Box(aw + 1.0, ah + 1.0, 30)
    try:
        top = frame.edges().group_by(Axis.Z)[-1]
        inner_edges = [e for e in top if abs(e.center().X) < aw / 2 + 2 and abs(e.center().Y) < ah / 2 + 2]
        frame = chamfer(inner_edges, 1.6)
    except Exception as e:  # noqa: BLE001
        print("bezel chamfer skipped:", e)
    return loc * frame


def _band_cuts():
    loc = Location(band_plane())
    cw, ch = P.PR_CUT
    cuts = loc * Pos(P.PR_X, P.PR_CUT_U0 + ch / 2, 0) * Box(cw, ch, 30)
    o = P.KEY_CAP_OPEN
    for x in key_centers():
        cuts += loc * Pos(x, P.KEY_U, 0) * Box(o, o, 30)
    return cuts


def grille_center():
    return P.GRILLE_C[0] * P.D, P.GRILLE_C[1]


def _grille_cuts():
    yc, zc = grille_center()
    cuts = None
    for ring, n in enumerate(P.GRILLE_RINGS):
        r = ring * P.GRILLE_PITCH
        for k in range(max(n, 1)):
            a = 2 * math.pi * k / max(n, 1) + (ring % 2) * math.pi / max(n, 1)
            y, z = yc + r * math.cos(a), zc + r * math.sin(a)
            c = Pos(P.half_w(z), y, z) * Rot(0, 90, 0) * Cylinder(P.GRILLE_HOLE / 2, 20)
            cuts = c if cuts is None else cuts + c
    return cuts


def rear_plane(x=0.0, z=0.0):
    """Плоскость по наружной задней грани; local Z — наружу (назад), local X — вправо при взгляде сзади."""
    n = (0, cos(P.REAR_LEAN), sin(P.REAR_LEAN))
    return Plane(origin=(x, P.y_rear(z), z), x_dir=(-1, 0, 0), z_dir=n)


def _rear_cuts():
    fw, fh, fd = P.REAR_FIELD
    zc = P.CH_T + 14 + fh / 2
    field = Box(fw, fh, 2 * fd)
    field = fillet(field.edges().filter_by(Axis.Z), 4.0)
    cuts = Location(rear_plane(0, zc)) * field
    sx, sz = P.SW_POS
    cuts += Location(rear_plane(sx, sz)) * Box(*P.SW_CUT, 30)
    cx, cz = P.CABLE_POS
    cuts += Location(rear_plane(cx, cz)) * Cylinder(P.CABLE_D / 2 + 0.25, 30)
    x0, x1, zb, n, h, pitch = P.VENTS
    for i in range(n):
        slot = fillet(Box(x1 - x0, h, 30).edges().filter_by(Axis.Z), h / 2 - 0.01)
        cuts += Location(rear_plane((x0 + x1) / 2, zb + i * pitch)) * slot
    return cuts


def rear_bushing():
    """Бортик-втулка вокруг кабельного ввода снаружи (в утопленном поле)."""
    cx, cz = P.CABLE_POS
    r_in = P.CABLE_D / 2 + 0.25
    ring = Cylinder(r_in + 2.2, 3.0) - Cylinder(r_in, 6)
    return Location(rear_plane(cx, cz)) * Pos(0, 0, -P.REAR_FIELD[2] + 1.5) * ring


# ------------------------------------------------------------------ деление на детали (черновое)
def split(sh):
    """Скорлупа → шасси (дно + задняя стенка), лицевая панель, колпак (бока + крыша)."""
    s = P.WALL + 0.05
    front_zone = [(-5, -5), (s / cos(P.BAND_TILT), -5),
                  (P.Y_TILT + s / cos(P.BAND_TILT), P.BAND_H),
                  (P.Y_TOP_FRONT + s / cos(P.TILT), P.H + 5), (-5, P.H + 5)]
    sr = s / cos(P.REAR_LEAN)
    rear_zone = [(P.D - sr, -5), (P.D + 5, -5), (P.D + 5, P.H + 5), (P.Y_TOP_REAR - sr, P.H + 5)]
    big = 2 * P.W
    fz = _prism_yz(front_zone, -big, big)
    rz = _prism_yz(rear_zone, -big, big) & box_xyz(-big, big, -big, big, -5, P.H - P.WALL - 0.05)
    bottom = box_xyz(-big, big, -big, big, -5, P.WALL + 0.05)
    panel = sh & fz
    rest = sh - fz
    chassis = (rest & bottom) + (rest & rz)
    cover = rest - bottom - rz
    return {"panel": panel, "chassis": chassis, "cover": cover}


def build():
    b = body()
    sh, _inner = shell(b)
    sh = sh - _screen_cuts() - _band_cuts() - _grille_cuts() - _rear_cuts()
    parts = split(sh)
    parts["chassis"] = parts["chassis"] + rear_bushing()
    parts["screen_bezel"] = screen_bezel()
    return parts
