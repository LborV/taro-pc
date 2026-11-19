"""Колпачки клавиш MX (3 шт.): корпус + вставка символа вторым цветом.

Символы: 1 — одна карта, 2 — три карты веером, 3 — «?».
Печать верхом вниз: символ — первые слои (0.6 мм) вторым цветом, без поддержек.
"""
from build123d import (Align, Box, BuildSketch, Cylinder, Locations, Mode, Plane, Pos, Rectangle, Rot,
                       RectangleRounded, Text, extrude, fillet, loft, Sketch)

import params as P

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
INLAY = 0.6        # глубина символа
TOP_W = 14.5       # верх колпачка
WALL_CAP = 1.5
STEM_D = 5.6
STEM_DEPTH = 4.0


def _frustum(w0, w1, h, r0=1.5, r1=1.5, z0=0.0):
    s0 = Plane.XY.offset(z0) * RectangleRounded(w0, w0, r0)
    s1 = Plane.XY.offset(z0 + h) * RectangleRounded(w1, w1, r1)
    return loft([s0, s1])


def body_raw():
    w0 = P.KEY_CAP[0]
    h = P.KEY_CAP[2]
    outer = _frustum(w0, TOP_W, h, 2.0, 2.5)
    inner = _frustum(w0 - 2 * WALL_CAP, TOP_W - 2 * WALL_CAP - 0.6, h - WALL_CAP, 1.0, 1.2, z0=-0.01)
    cap = outer - inner
    # шток с крестом MX
    z_top_in = h - WALL_CAP
    stem = Pos(0, 0, z_top_in - STEM_DEPTH / 2 - 0.5 + 0.25) * Cylinder(STEM_D / 2, STEM_DEPTH + 1.0)
    sx, sy = P.KEY_STEM
    f = P.KEY_STEM_FIT
    cross = (Box(sx + f, sy + f, STEM_DEPTH * 2) + Box(sy + f, sx + f, STEM_DEPTH * 2))
    cross = Pos(0, 0, z_top_in - 0.5 - STEM_DEPTH) * cross
    return cap + stem - cross


def symbol_sketch(kind):
    """2D-символ (в мм), центр (0,0)."""
    with BuildSketch() as sk:
        if kind == 1:
            RectangleRounded(6.4, 9.0, 1.0)
            RectangleRounded(4.0, 6.6, 0.4, mode=Mode.SUBTRACT)
        elif kind == 2:
            for ang, dx in ((-18, -2.6), (0, 0), (18, 2.6)):
                with Locations(Pos(dx, 0) * Rot(0, 0, -ang)):
                    RectangleRounded(5.2, 7.6, 0.8)
            for ang, dx in ((-18, -2.6), (0, 0), (18, 2.6)):
                pass
        else:
            Text("?", font_size=10.5, font_path=FONT, align=(Align.CENTER, Align.CENTER))
    s = sk.sketch
    if kind == 2:
        # контуры трёх карт: вычитаем внутренности, верхняя карта перекрывает нижние
        out = None
        for i, (ang, dx) in enumerate(((-18, -2.6), (18, 2.6), (0, 0))):
            with BuildSketch() as a:
                with Locations(Pos(dx, 0) * Rot(0, 0, -ang)):
                    RectangleRounded(5.2, 7.6, 0.8)
            with BuildSketch() as b:
                with Locations(Pos(dx, 0) * Rot(0, 0, -ang)):
                    RectangleRounded(3.2, 5.6, 0.3)
            ring = a.sketch - b.sketch
            if out is None:
                out = ring
            else:
                out = (out - a.sketch) + ring
        s = out
    return s


def keycap(kind):
    """→ (корпус, вставка символа) в рабочей ориентации (низ колпачка на z=0)."""
    h = P.KEY_CAP[2]
    body = body_raw()
    sym = extrude(Plane.XY.offset(h - INLAY) * symbol_sketch(kind), amount=INLAY + 0.01)
    return body - sym, sym


if __name__ == "__main__":
    for k in (1, 2, 3):
        b, s = keycap(k)
        print(k, round(b.volume, 1), round(s.volume, 2), b.is_valid, s.is_valid)
