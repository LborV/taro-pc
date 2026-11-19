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
        edges = [e for e in b.edges() if not (abs(e.vertices()[0].Z) < 1e-3 and abs(e.vertices()[-1].Z) < 1e-3)]
        b = fillet(edges, P.R_EDGE)   # низ без скругления: стоит на ножках, дно — плоская плита
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
    """Неглубокий карман под тёмную вставку-рамку + окно по активной области с фаской."""
    loc = Location(screen_plane())
    gw, gh = P.SCR_GLASS
    bw, bh = gw + 2 * P.SCR_BEZEL_W, gh + 2 * P.SCR_BEZEL_W
    zf = _z_face()
    pocket = loc * Pos(0, P.SCR_GLASS_CY, zf) * Box(bw, bh, 2 * P.SCR_BEZEL_T)
    aw, ah = P.SCR_AA
    window = loc * Pos(0, 0, zf) * Box(aw + 2.0, ah + 2.0, 40)
    return pocket + window


def screen_bezel():
    """Тёмно-серая вставка-рамка в кармане лицевой панели (заподлицо), окно по АО с фаской."""
    loc = Location(screen_plane())
    gw, gh = P.SCR_GLASS
    bw, bh = gw + 2 * P.SCR_BEZEL_W - 2 * P.FIT, gh + 2 * P.SCR_BEZEL_W - 2 * P.FIT
    t = P.SCR_BEZEL_T
    frame = Pos(0, P.SCR_GLASS_CY, _z_face() - t / 2) * Box(bw, bh, t)
    frame = fillet(frame.edges().filter_by(Axis.Z), 2.0)
    aw, ah = P.SCR_AA
    frame = frame - Box(aw + 1.0, ah + 1.0, 30)
    try:
        top = frame.edges().group_by(Axis.Z)[-1]
        inner_edges = [e for e in top if abs(e.center().X) < aw / 2 + 2 and abs(e.center().Y) < ah / 2 + 2]
        frame = chamfer(inner_edges, 0.8)
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


# ------------------------------------------------------------------ деление на плоские панели
PARTS = ["base", "front_band", "front_screen", "rear", "side_l", "side_r", "roof"]


def zones():
    """Зоны-призмы для деления скорлупы. Приоритет: крыша > бока > перед > зад > дно."""
    big = 2 * P.W
    r = P.R_EDGE + 0.5
    s = P.WALL + 0.6
    Z = {}
    Z["roof"] = box_xyz(-big, big, -big, big, P.H - r, P.H + 10)
    hx, hy, hd = P.HANDLE
    yc = (P.Y_TOP_FRONT + P.Y_TOP_REAR) / 2
    Z["roof"] = Z["roof"] + Pos(0, yc, P.H - (hd + P.WALL + 1) / 2) * Box(hx + 2 * P.WALL + 2, hy + 2 * P.WALL + 2,
                                                                       hd + P.WALL + 1)
    # бока владеют вертикальными скруглениями на углах → шов на переднем/заднем лице в 5.5 мм от угла
    hw0, hw1 = P.half_w(-10) - r, P.half_w(P.H + 10) - r
    Z["side_r"] = _prism_xz([(hw0, -10), (big, -10), (big, P.H + 10), (hw1, P.H + 10)], -big, big)
    Z["side_l"] = _prism_xz([(-big, -10), (-hw0, -10), (-hw1, P.H + 10), (-big, P.H + 10)], -big, big)
    front = [(-50, -10), (s / cos(P.BAND_TILT) + (-10) * math.tan(P.BAND_TILT), -10),
             (P.Y_TILT + s / cos(P.BAND_TILT), P.BAND_H),
             (P.Y_TOP_FRONT + s / cos(P.TILT) + 10 * math.tan(P.TILT), P.H + 10), (-50, P.H + 10)]
    Z["front"] = _prism_yz(front, -big, big)
    # шов между поясом и экранной гранью — по биссектрисе угла перегиба
    dy = cos(P.BAND_TILT) + cos(P.TILT)
    dz = -(sin(P.BAND_TILT) + sin(P.TILT))
    L = math.hypot(dy, dz)
    by, bz = P.Y_TILT, P.BAND_H
    p1 = (by + 300 * dy / L, bz + 300 * dz / L)
    Z["band"] = _prism_yz([(by, bz), p1, (p1[0], -50), (-50, -50), (-50, bz)], -big, big)
    sr = s / cos(P.REAR_LEAN)
    Z["rear"] = _prism_yz([(P.y_rear(-10) - sr, -10), (P.D + 50, -10), (P.D + 50, P.H + 10),
                           (P.y_rear(P.H + 10) - sr, P.H + 10)], -big, big)
    return Z


def split(sh):
    Z = zones()
    out = {}
    rest = sh
    out["roof"] = rest & Z["roof"]
    rest = rest - Z["roof"]
    for k in ("side_l", "side_r"):
        out[k] = rest & Z[k]
        rest = rest - Z[k]
    front = rest & Z["front"]
    out["front_band"] = front & Z["band"]
    out["front_screen"] = front - Z["band"]
    rest = rest - Z["front"]
    out["rear"] = rest & Z["rear"]
    out["base"] = rest - Z["rear"]
    return out


def build(with_fasteners=True):
    b = body()
    sh, inner = shell(b)
    sh = sh - _screen_cuts() - _band_cuts() - _grille_cuts() - _rear_cuts()
    parts = split(sh)
    parts["rear"] = parts["rear"] + rear_bushing()
    parts["screen_bezel"] = screen_bezel()
    hw = {}
    if with_fasteners:
        import fasteners
        parts, hw = fasteners.apply(parts, inner, b)
    build.hardware = hw
    return parts


build.hardware = {}
