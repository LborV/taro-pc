"""Силовая схема: бобышки, вставки, балки, уголки и винты (болванки винтов для сборки/рендера).

apply(parts, inner) → (parts с бобышками/отверстиями, hardware: name -> shape)
Все размеры — из params.py.
"""
import math

from build123d import Box, Compound, Cone, Cylinder, Location, Plane, Pos, Vector

from dummies import box_xyz

import params as P
from dummies import screen_plane  # noqa: E402

CSK_H = (P.M3_HEAD_CSK_D - P.M3_CLEAR) / 2   # высота потайной головки (90°)


# ------------------------------------------------------------------ примитивы
def _frame(origin, z_dir):
    z = Vector(*z_dir).normalized()
    x = Vector(1, 0, 0) if abs(z.X) < 0.9 else Vector(0, 1, 0)
    x = (x - z * x.dot(z)).normalized()
    return Location(Plane(origin=origin, x_dir=x, z_dir=z))


def screw(origin, direction, length, head="csk"):
    """Винт M3: origin — опорная плоскость головки, direction — куда входит стержень."""
    loc = _frame(origin, direction)
    shank = Pos(0, 0, length / 2) * Cylinder(1.5, length)
    if head == "csk":
        h = Pos(0, 0, CSK_H / 2) * Cone(P.M3_HEAD_CSK_D / 2, P.M3_CLEAR / 2, CSK_H)
    else:
        h = Pos(0, 0, -1.5) * Cylinder(2.75, 3.0)
    return loc * (shank + h)


def insert(origin, direction):
    """Латунная вставка: origin — торец со стороны винта, direction — вглубь."""
    return _frame(origin, direction) * Pos(0, 0, P.INSERT_L / 2) * Cylinder(P.INSERT_OD / 2, P.INSERT_L)


def boss_up(x, y, z0, h):
    """Вертикальная бобышка с отверстием под вставку снизу."""
    b = Pos(x, y, z0 + h / 2) * Cylinder(P.BOSS_D / 2, h)
    hole = Pos(x, y, z0 + P.INSERT_DEPTH / 2 - 0.01) * Cylinder(P.INSERT_HOLE / 2, P.INSERT_DEPTH)
    return b, hole


def _csk_hole(x, y, z_bottom, t):
    thru = Pos(x, y, z_bottom + t / 2) * Cylinder(P.M3_CLEAR / 2, t + 2)
    cone = Pos(x, y, z_bottom + CSK_H / 2 - 0.01) * Cone(P.M3_HEAD_CSK_D / 2 + 0.2, P.M3_CLEAR / 2, CSK_H)
    return thru + cone


# ------------------------------------------------------------------ положения
def wall_in_band(z):
    return z * math.tan(P.BAND_TILT) + P.WALL / math.cos(P.BAND_TILT)


def wall_in_rear(z):
    return P.y_rear(z) - P.WALL / math.cos(P.REAR_LEAN)


def wall_in_side(z):
    return P.half_w(z) - P.WALL / math.cos(P.SIDE_LEAN)


def bottom_bosses():
    """[(part, x, y)] — центры нижних бобышек (винты снизу через дно)."""
    r = P.BOSS_D / 2
    zt = P.BASE_T + P.BOSS_H
    out = []
    for x in P.BASE_SCREWS_BAND:
        out.append(("front_band", x, wall_in_band(zt) + r - 1.0))
    for x in P.BASE_SCREWS_REAR:
        out.append(("rear", x, wall_in_rear(zt) - r + 1.0))
    for y in P.BASE_SCREWS_SIDE:
        out.append(("side_r", wall_in_side(zt) - r + 1.0, y))
        out.append(("side_l", -(wall_in_side(zt) - r + 1.0), y))
    return out


def front_in_y(z):
    """Y внутренней грани экранной части передней панели на высоте z."""
    return P.Y_TILT + (z - P.BAND_H) * math.tan(P.TILT) + P.WALL / math.cos(P.TILT)


def rear_in_y(z):
    return wall_in_rear(z)


def top_tab(x, sgn, y_in):
    """Г-язычок на панели + паз в крыше. sgn=+1: панель спереди, язычок идёт назад."""
    t, w = 3.0, 12.0
    z_arm0 = P.TAB_Z - 4.0                  # горизонтальное плечо
    z_top = P.TAB_Z + P.TAB_FIN_H           # верх пера
    y0 = y_in(z_arm0) - sgn * 2.0           # врастает в стенку
    # перо — за наклонной стенкой даже на её верхней кромке, иначе ребро паза влезет в стенку
    y_top_edge = y_in(P.H - P.R_EDGE - 0.5)
    y_fin = y_top_edge + sgn * (0.6 + 2.4 + P.FIT)
    arm = box_xyz(x - w / 2, x + w / 2, min(y0, y_fin), max(y0, y_fin), z_arm0, P.TAB_Z)
    fin = box_xyz(x - w / 2, x + w / 2, min(y_fin, y_fin + sgn * t), max(y_fin, y_fin + sgn * t), z_arm0, z_top)
    tab = arm + fin
    # паз: два ребра с зазором FIT вокруг пера, свисают из-под крыши
    zr0 = P.TAB_Z + 1.0
    zr1 = P.H - P.WALL + 1.0
    lo, hi = sorted((y_fin, y_fin + sgn * t))
    rib_a = box_xyz(x - w / 2 - 1.5, x + w / 2 + 1.5, lo - P.FIT - 2.4, lo - P.FIT, zr0, zr1)
    rib_b = box_xyz(x - w / 2 - 1.5, x + w / 2 + 1.5, hi + P.FIT, hi + P.FIT + 2.4, zr0, zr1)
    return tab, rib_a + rib_b


# ------------------------------------------------------------------ сборка
def apply(parts, inner, body):
    from build123d import offset
    solid_in = offset(body, amount=-0.6)   # чтобы бобышки врастали в стенку, но не вылезали наружу
    hw_screws, hw_inserts = [], []
    zb = P.BASE_T
    base_cuts = None
    # 1) нижние бобышки на стенках + потай в дне
    for part, x, y in bottom_bosses():
        b, hole = boss_up(x, y, zb, P.BOSS_H)
        b = b & solid_in
        parts[part] = parts[part] + b - hole
        c = _csk_hole(x, y, 0, P.BASE_T)
        base_cuts = c if base_cuts is None else base_cuts + c
        hw_screws.append(screw((x, y, 0), (0, 0, 1), P.BASE_SCREW_L))
        hw_inserts.append(insert((x, y, zb), (0, 0, 1)))
    parts["base"] = parts["base"] - base_cuts

    # 2) верх передней и задней панели держит крыша: на панели Г-образный язычок с вертикальным пером,
    #    в крыше паз из двух рёбер. Всё вертикальное → колпак снимается строго вверх.
    for part, sgn, y_in in (("front_screen", 1, front_in_y), ("rear", -1, rear_in_y)):
        for x in (-P.TAB_X, P.TAB_X):
            tab, slot_ribs = top_tab(x, sgn, y_in)
            parts[part] = parts[part] + (tab & solid_in)
            parts["roof"] = parts["roof"] + (slot_ribs & solid_in)

    # 4) стойки экрана на лицевой панели (вставки, винты со стороны платы)
    loc = Location(screen_plane())
    z_in = P.SCR_RECESS + P.SCR_Z_GLASS_FRONT - P.WALL      # тыл панели в координатах экрана
    z_pcb = P.SCR_Z_PCB_FRONT
    hgt = z_in - z_pcb
    for (hx, hy) in P.SCR_HOLES:
        st = loc * Pos(hx, hy, z_pcb + (hgt + 0.6) / 2) * Cylinder(P.SCR_STANDOFF_D / 2, hgt + 0.6)
        hole = loc * Pos(hx, hy, z_pcb + P.INSERT_DEPTH / 2 - 0.01) * Cylinder(P.INSERT_HOLE / 2, P.INSERT_DEPTH)
        parts["front_screen"] = parts["front_screen"] + st - hole
        hw_inserts.append(loc * Pos(hx, hy, z_pcb + P.INSERT_L / 2) * Cylinder(P.INSERT_OD / 2, P.INSERT_L))
        hw_screws.append(loc * (Pos(hx, hy, P.SCR_Z_PCB_BACK - 1.5) * Cylinder(2.75, 3.0)
                                + Pos(hx, hy, P.SCR_Z_PCB_BACK + 3) * Cylinder(1.5, 6.0)))

    # 5) ножки
    feet = [Pos(x, y, -P.FOOT_T / 2) * Cylinder(P.FOOT_D / 2, P.FOOT_T) for x, y in P.FEET]

    hw = {"screws": Compound(children=hw_screws), "inserts": Compound(children=hw_inserts),
          "feet": Compound(children=feet)}
    return parts, hw
