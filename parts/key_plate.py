"""Пластина клавиш: 1.5 мм в зоне вырезов 14×14, рёбра жёсткости сзади, 2 ушка на бобышки панели.

Координаты — плоскость пояса (dummies.band_plane): local X = мировой X, local Y = вверх по поясу (u),
local Z = наружу. Тыл передней панели — local Z = −WALL.
Печать: лицевой стороной (той, что к панели) вниз — плоско, без поддержек.
"""
from build123d import Box, Cylinder, Location, Pos

import params as P
from dummies import band_plane, key_centers


def plate_dims():
    w = (P.KEY_N - 1) * P.KEY_PITCH + P.KEY_CUT + 2 * P.KEY_PLATE_MARGIN
    h = P.KEY_CUT + 2 * P.KEY_PLATE_MARGIN
    return w, h


def ear_points():
    """Центры ушек (local x, u): сверху и снизу по центру ряда — по бокам мешали бы колодки принтера."""
    w, h = plate_dims()
    return [(P.KEY_X, P.KEY_U + h / 2 + 5.0), (P.KEY_X, P.KEY_U - h / 2 - 5.0)]


def _box(x0, x1, u0, u1, z0, z1):
    return Pos((x0 + x1) / 2, (u0 + u1) / 2, (z0 + z1) / 2) * Box(x1 - x0, u1 - u0, z1 - z0)


def plate_local():
    w, h = plate_dims()
    z_face = -P.WALL - P.FIT                       # прижата к тылу панели (с зазором)
    t = P.KEY_PLATE_T
    rt, rh = P.KEY_PLATE_RIB
    x0, x1 = P.KEY_X - w / 2, P.KEY_X + w / 2
    u0, u1 = P.KEY_U - h / 2, P.KEY_U + h / 2
    zb = z_face - t                                 # тыл пластины
    part = _box(x0, x1, u0, u1, zb, z_face)
    # рёбра: по периметру и между вырезами
    part += _box(x0, x1, u0, u0 + rt, zb - rh, zb) + _box(x0, x1, u1 - rt, u1, zb - rh, zb)
    part += _box(x0, x0 + rt, u0, u1, zb - rh, zb) + _box(x1 - rt, x1, u0, u1, zb - rh, zb)
    xs = key_centers()
    for a, b in zip(xs, xs[1:]):
        xm = (a + b) / 2
        part += _box(xm - rt / 2, xm + rt / 2, u0, u1, zb - rh, zb)
    for x in xs:
        part -= _box(x - P.KEY_CUT / 2, x + P.KEY_CUT / 2, P.KEY_U - P.KEY_CUT / 2, P.KEY_U + P.KEY_CUT / 2, -50, 50)
    # ушки: лежат на бобышках панели (высота KEY_PLATE_BOSS_H от тыла панели), перемычка к пластине
    ze1 = -P.WALL - P.KEY_PLATE_BOSS_H
    ze0 = ze1 - P.KEY_PLATE_EAR_T
    for ex, eu in ear_points():
        sgn = 1 if eu > P.KEY_U else -1
        ub = u1 if sgn > 0 else u0
        ear = _box(ex - 7, ex + 7, min(ub, eu + sgn * 5), max(ub, eu + sgn * 5), ze0, ze1)
        web = _box(ex - 7, ex + 7, min(ub - sgn * rt, ub), max(ub - sgn * rt, ub), ze0, zb)
        hole = Pos(ex, eu, ze0 + P.KEY_PLATE_EAR_T / 2) * Cylinder(P.M3_CLEAR / 2, 20)
        part = part + ear + web - hole
    return part


def bosses_local():
    """Бобышки на тыле передней панели под ушки (вставка M3 со стороны ушка)."""
    out, holes = None, None
    zt = -P.WALL - P.KEY_PLATE_BOSS_H
    for ex, eu in ear_points():
        b = Pos(ex, eu, (zt - P.WALL + 0.8) / 2) * Cylinder(P.BOSS_D / 2, P.KEY_PLATE_BOSS_H + 0.8)
        h = Pos(ex, eu, zt + P.INSERT_DEPTH / 2 - 0.01) * Cylinder(P.INSERT_HOLE / 2, P.INSERT_DEPTH)
        out = b if out is None else out + b
        holes = h if holes is None else holes + h
    return out, holes


def key_plate():
    return Location(band_plane()) * plate_local()


def panel_bosses():
    b, h = bosses_local()
    loc = Location(band_plane())
    return loc * b, loc * h


def hardware():
    """Винты M3×8 через ушки + вставки (для сборки/рендера)."""
    from build123d import Compound
    loc = Location(band_plane())
    zt = -P.WALL - P.KEY_PLATE_BOSS_H
    scr, ins = [], []
    for ex, eu in ear_points():
        scr.append(loc * (Pos(ex, eu, zt - P.KEY_PLATE_EAR_T - 1.5) * Cylinder(2.75, 3.0)
                          + Pos(ex, eu, zt - P.KEY_PLATE_EAR_T + 4.0) * Cylinder(1.5, 8.0)))
        ins.append(loc * Pos(ex, eu, zt + P.INSERT_L / 2) * Cylinder(P.INSERT_OD / 2, P.INSERT_L))
    return Compound(children=scr), Compound(children=ins)


if __name__ == "__main__":
    p = key_plate()
    print("key_plate", round(p.volume), p.is_valid, len(p.solids()), plate_dims())
