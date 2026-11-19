"""Силовая схема: бобышки, вставки, балки, уголки и винты (болванки винтов для сборки/рендера).

apply(parts, inner) → (parts с бобышками/отверстиями, hardware: name -> shape)
Все размеры — из params.py.
"""
import math

from build123d import Box, Compound, Cone, Cylinder, Location, Plane, Pos, Vector

import params as P
from dummies import screen_plane

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
    zt = P.WALL + P.BOSS_H
    out = []
    for x in P.BASE_SCREWS_BAND:
        out.append(("front_band", x, wall_in_band(zt) + r - 1.0))
    for x in P.BASE_SCREWS_REAR:
        out.append(("rear", x, wall_in_rear(zt) - r + 1.0))
    for y in P.BASE_SCREWS_SIDE:
        out.append(("side_r", wall_in_side(zt) - r + 1.0, y))
        out.append(("side_l", -(wall_in_side(zt) - r + 1.0), y))
    return out


def rails():
    """Верхние балки каркаса: от экранной грани до задней стенки."""
    w, h = P.RAIL_SEC
    z = P.RAIL_Z
    # внутренняя грань экранной панели на высоте z
    y_front = P.Y_TILT + (z - P.BAND_H) * math.tan(P.TILT) + P.WALL / math.cos(P.TILT)
    y_back = wall_in_rear(z)
    out = {}
    for side, sx in (("l", -1), ("r", 1)):
        x = sx * P.RAIL_X
        out[f"rail_{side}"] = Pos(x, (y_front + y_back) / 2, z) * Box(w, y_back - y_front - 0.2, h)
    return out, y_front, y_back


def roof_blocks():
    """Уголки крыша↔бок (печатные), под крышей у боковин."""
    z1 = P.H - P.WALL
    z0 = z1 - 9.0
    yc = (P.Y_TOP_FRONT + P.Y_TOP_REAR) / 2
    out = {}
    for side, sx in (("l", -1), ("r", 1)):
        for k, dy in (("f", -P.ROOF_BLOCK_DY), ("b", P.ROOF_BLOCK_DY)):
            xo = wall_in_side(z0) - 0.3
            out[f"roof_block_{side}{k}"] = Pos(sx * (xo - 5.5), yc + dy, (z0 + z1) / 2) * Box(11.0, 12.0, z1 - z0)
    return out


# ------------------------------------------------------------------ сборка
def apply(parts, inner, body):
    from build123d import offset
    solid_in = offset(body, amount=-0.6)   # чтобы бобышки врастали в стенку, но не вылезали наружу
    hw_screws, hw_inserts = [], []
    zb = P.WALL
    base_cuts = None
    # 1) нижние бобышки на стенках + потай в дне
    for part, x, y in bottom_bosses():
        b, hole = boss_up(x, y, zb, P.BOSS_H)
        b = b & solid_in
        parts[part] = parts[part] + b - hole
        c = _csk_hole(x, y, 0, P.WALL)
        base_cuts = c if base_cuts is None else base_cuts + c
        hw_screws.append(screw((x, y, 0), (0, 0, 1), 10.0))
        hw_inserts.append(insert((x, y, zb), (0, 0, 1)))
    parts["base"] = parts["base"] - base_cuts

    # 2) верхние балки каркаса: площадки на панелях, балка между ними, винт по оси Y в каждый торец
    rl, y_front, y_back = rails()
    pad_t = 5.0
    for name, r in rl.items():
        x = r.center().X
        w, h = P.RAIL_SEC
        parts[name] = Pos(x, (y_front + y_back) / 2, P.RAIL_Z) * Box(w, y_back - y_front - 2 * (pad_t + 3.0) - 0.4, h)
        for y_end, sgn, part in ((y_front, -1, "front_screen"), (y_back, 1, "rear")):
            y_face = y_end - sgn * (pad_t + 3.0)       # торец площадки (наклон грани ±2.9 мм по высоте балки)
            y0, y1 = sorted((y_end + sgn * 3.0, y_face))
            pad = Pos(x, (y0 + y1) / 2, P.RAIL_Z) * Box(P.BOSS_D + 2, y1 - y0, P.BOSS_D + 2)
            pad = pad & solid_in
            hole = _frame((x, y_face, P.RAIL_Z), (0, sgn, 0)) * Pos(0, 0, P.INSERT_DEPTH / 2 - 0.01) * \
                Cylinder(P.INSERT_HOLE / 2, P.INSERT_DEPTH)
            parts[part] = parts[part] + pad - hole
            hw_screws.append(screw((x, y_face - sgn * 9.0, P.RAIL_Z), (0, sgn, 0), 14.0, head="pan"))
            hw_inserts.append(insert((x, y_face, P.RAIL_Z), (0, sgn, 0)))

    # 3) уголки крыша↔бок: винт вверх в крышу и вбок в боковину
    for name, blk in roof_blocks().items():
        parts[name] = blk & inner
        c = blk.center()
        sx = 1 if c.X > 0 else -1
        hw_screws.append(screw((c.X - sx * 1.5, c.Y, c.Z - 4.5), (0, 0, 1), 8.0, head="pan"))
        hw_screws.append(screw((c.X - sx * 5.5, c.Y, c.Z), (sx, 0, 0), 10.0, head="pan"))

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
    feet = [Pos(x, y, -1.5) * Cylinder(P.FOOT_D / 2, 3.0) for x, y in P.FEET]

    hw = {"screws": Compound(children=hw_screws), "inserts": Compound(children=hw_inserts),
          "feet": Compound(children=feet)}
    return parts, hw
