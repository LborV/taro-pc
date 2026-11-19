"""Закрытая камера динамика ø40 у правой стенки, лицом к решётке колпака.

Динамик вклеивается ободом в посадку на ЛИЦЕВОЙ стенке камеры (магнит уходит внутрь через окно ø34),
так камера — одна закрытая деталь, подходит к любому ø40 без ушек. Между ободом и правым боком колпака —
поролон SPK_FOAM. Камера стоит на подставке, 2 ушка → 2 винта M3 в бобышки дна.
Внутренний объём — SPK_CHAMBER_IN (≈ 46 мл минус магнит).
Печать: стоя на подставке, как в сборке; лицевая стенка — мост 24 мм (нормально) .
"""
from build123d import Box, Compound, Cylinder, Location, Pos, Rot

import params as P
from dummies import box_xyz


def frame():
    """(Location камеры, xo, yc, zc): local X — наружу к решётке (по нормали наклонного бока)."""
    yc, zc = P.GRILLE_C[0] * P.D, P.GRILLE_C[1]
    xo = P.half_w(zc) - P.WALL - P.FIT - P.SPK_FOAM
    return Location((xo, yc, zc)) * Rot(0, -P.SIDE_LEAN_DEG, 0), xo, yc, zc


def chamber_local():
    ix, iy, iz = P.SPK_CHAMBER_IN
    w = P.WALL
    outer = box_xyz(-(ix + 2 * w), 0, -iy / 2 - w, iy / 2 + w, -iz / 2 - w, iz / 2 + w)
    inner = box_xyz(-(ix + w), -w, -iy / 2, iy / 2, -iz / 2, iz / 2)
    seat_d = P.SPK_D + 2 * P.FIT
    seat = Pos(-P.SPK_RIM_T / 2 + 0.01, 0, 0) * Rot(0, 90, 0) * Cylinder(seat_d / 2, P.SPK_RIM_T + 0.02)
    window = Pos(-w / 2, 0, 0) * Rot(0, 90, 0) * Cylinder(P.SPK_CONE_D / 2, w * 3)
    wire = Pos(-(ix + 1.5 * w), iy / 2 - 4, -iz / 2 + 4) * Rot(0, 90, 0) * Cylinder(1.25, w * 3)
    return outer - inner - seat - window - wire


def speaker_box():
    loc, xo, yc, zc = frame()
    ch = loc * chamber_local()
    bb = ch.bounding_box()
    ix, iy, iz = P.SPK_CHAMBER_IN
    # подставка: от дна до низа камеры, внутри наклонной камеры — без зазоров
    z_top = bb.min.Z + 6.0
    x0, x1 = bb.min.X + 3.0, bb.max.X - 4.0
    y0, y1 = yc - iy / 2, yc + iy / 2
    stand = box_xyz(x0, x1, y0, y1, P.BASE_T + P.FIT, z_top)
    stand -= box_xyz(x0 + 2.4, x1 - 2.4, y0 + 2.4, y1 - 2.4, P.BASE_T - 1, z_top - 8)   # облегчение
    # ушки на бобышки дна
    ze0 = P.BASE_T + P.SPK_EAR_Z
    ears = None
    for (px, py) in ear_points():
        e = box_xyz(px - 6, px + 6, min(py, (y0 if py < yc else y1)), max(py, (y0 if py < yc else y1)) , ze0, ze0 + 3.0)
        e = e + Pos(px, py, ze0 + 1.5) * Cylinder(6, 3.0)
        e = e - Pos(px, py, ze0 + 1.5) * Cylinder(P.M3_CLEAR / 2, 10)
        ears = e if ears is None else ears + e
    return ch + stand + ears


def ear_points():
    loc, xo, yc, zc = frame()
    ix, iy, iz = P.SPK_CHAMBER_IN
    cx = xo - (ix + 2 * P.WALL) / 2 - 1.0
    return [(cx, yc - iy / 2 - 7.0), (cx, yc + iy / 2 + 7.0)]


def base_bosses():
    """Бобышки на дне под ушки камеры (вставка M3 сверху)."""
    b, h = None, None
    for (px, py) in ear_points():
        bb = Pos(px, py, P.BASE_T + P.SPK_EAR_Z / 2 - 0.2) * Cylinder(P.BOSS_D / 2, P.SPK_EAR_Z + 0.4)
        hh = Pos(px, py, P.BASE_T + P.SPK_EAR_Z - P.INSERT_DEPTH / 2 + 0.01) * Cylinder(P.INSERT_HOLE / 2, P.INSERT_DEPTH)
        b = bb if b is None else b + bb
        h = hh if h is None else h + hh
    return b, h


def speaker_dummy():
    loc, *_ = frame()
    return loc * Pos(-P.SPK_RIM_T - P.SPK_DEPTH / 2 + 1.0, 0, 0) * Rot(0, 90, 0) * Cylinder(P.SPK_D / 2, P.SPK_DEPTH)


def hardware():
    scr, ins = [], []
    for (px, py) in ear_points():
        z = P.BASE_T + P.SPK_EAR_Z
        scr.append(Pos(px, py, z + 3.0 + 1.5) * Cylinder(2.75, 3.0) + Pos(px, py, z + 3.0 - 4.0) * Cylinder(1.5, 8.0))
        ins.append(Pos(px, py, z - P.INSERT_L / 2) * Cylinder(P.INSERT_OD / 2, P.INSERT_L))
    return Compound(children=scr), Compound(children=ins)


if __name__ == "__main__":
    s = speaker_box()
    ix, iy, iz = P.SPK_CHAMBER_IN
    print("speaker_box", round(s.volume), s.is_valid, len(s.solids()), s.bounding_box().size,
          "inner ml", round(ix * iy * iz / 1000, 1))
