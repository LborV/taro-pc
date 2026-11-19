"""Оболочка корпуса по концепт-арту: тело, полая скорлупа, черновое деление на детали.

Это ещё этап компоновки: форма, вырезы и линии разъёма — финальные детали
(пазы, бобышки, вставки, рёбра) будут в parts/*.py.
"""
import math
from math import cos, sin

from build123d import (Axis, Box, Cylinder, Location, Plane, Polygon, Pos, Rot, Vector, chamfer,
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
    return b


def handle_pocket(grow=0.0):
    """Проём ручки с поднутрением под передней кромкой (сечение YZ, вытянуто по X).
    grow > 0 — тот же контур, раздутый на grow (наружная поверхность стенок ручки)."""
    from build123d import Kind
    hx, hy, hd = P.HANDLE
    u, r, c = P.HANDLE_UNDERCUT, P.HANDLE_RIM, P.HANDLE_CHAMFER
    yf, yb = P.HANDLE_Y - hy / 2, P.HANDLE_Y + hy / 2
    H = P.H
    pts = [(yb, H + 6), (yb, H - hd + c), (yb - c, H - hd), (yf - u + c, H - hd), (yf - u, H - hd + c),
           (yf - u, H - r), (yf, H - r), (yf, H + 6)]
    face = Plane.YZ * Polygon(*pts, align=None)
    if grow:
        face = offset(face, amount=grow, kind=Kind.INTERSECTION)
    face = Plane.YZ.offset(-hx / 2 - grow) * Polygon(*[(v.Y, v.Z) for v in face.vertices()], align=None) \
        if False else Pos(-hx / 2 - grow, 0, 0) * face
    pocket = extrude(face, amount=hx + 2 * grow, dir=(1, 0, 0))
    try:
        vert = [e for e in pocket.edges() if abs(e.tangent_at(0.5).Z) > 0.99 and e.length > 3]
        pocket = fillet(vert, 4.0 + grow)
    except Exception as e:  # noqa: BLE001
        print("handle fillet skipped:", e)
    return pocket


def shell(b=None):
    """Оболочка. Ручку вырезаем ПОСЛЕ offset(): поднутрение ломает offset() у OCC."""
    b = b or body()
    inner = offset(b, amount=-P.WALL)
    sh = b - inner
    pocket = handle_pocket()
    grown = handle_pocket(P.WALL)
    walls = (grown & b) - pocket
    sh = sh - pocket + walls
    inner = inner - grown
    try:   # скруглить кромку проёма — за неё тянут пальцами
        hx, hy, _ = P.HANDLE
        top = [e for e in sh.edges() if abs(e.center().Z - P.H) < 0.05 and abs(e.center().X) <= hx / 2 + 0.5
               and P.HANDLE_Y - hy / 2 - 0.5 <= e.center().Y <= P.HANDLE_Y + hy / 2 + 0.5]
        sh = fillet(top, 1.5)
    except Exception as e:  # noqa: BLE001
        print("handle rim fillet skipped:", e)
    return sh, inner


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
    pd, ph = P.SCR_BEZEL_PIN
    for (px, py) in P.SCR_BEZEL_PINS:
        pin = Pos(px, py, _z_face() - t - ph / 2 + 0.01) * Cylinder(pd / 2, ph + 0.02)
        try:
            pin = chamfer(pin.edges().group_by(Axis.Z)[0], 0.4)
        except Exception:  # noqa: BLE001
            pass
        frame = frame + pin
    return loc * frame


def bezel_backing_and_sockets():
    """Утолщение панели изнутри под полосой рамки (вне стекла) + гнёзда под шипы рамки."""
    loc = Location(screen_plane())
    gw, gh = P.SCR_GLASS
    bw, bh = gw + 2 * P.SCR_BEZEL_W, gh + 2 * P.SCR_BEZEL_W
    z_in = _z_face() - P.WALL
    t = P.SCR_BEZEL_BACKING
    outer = Pos(0, P.SCR_GLASS_CY, z_in - t / 2 + 0.3) * Box(bw, bh, t + 0.6)
    hole = Pos(0, P.SCR_GLASS_CY, z_in - t / 2) * Box(gw + 2 * P.SCR_BEZEL_GAP + 1.0, gh + 2 * P.SCR_BEZEL_GAP + 1.0, 20)
    backing = outer - hole
    pd, ph = P.SCR_BEZEL_PIN
    socks = None
    for (px, py) in P.SCR_BEZEL_PINS:
        sck = Pos(px, py, _z_face() - P.SCR_BEZEL_T - (ph + 0.3) / 2 + 0.01) * Cylinder(pd / 2 + 0.15, ph + 0.3)
        socks = sck if socks is None else socks + sck
    return loc * backing, loc * socks


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


def zones(extra=0.0):
    """Зоны-призмы для деления скорлупы. Приоритет: крыша > бока > перед > зад > дно.
    extra — расширить зоны стенок внутрь (для зазоров дна/бортика)."""
    big = 2 * P.W
    r = P.R_EDGE + 0.5 + extra
    s = P.WALL + 0.6 + extra
    Z = {}
    if P.print_whole():
        Z["roof"] = box_xyz(-big, big, -big, big, P.H - r, P.H + 10)
    else:
        # шов крыша↔бок — по биссектрисе угла (середина скругления), а не по плоскости бока
        t, c = math.tan(P.SIDE_LEAN), math.cos(P.SIDE_LEAN)
        xb = lambda z: P.W / 2 - z * t - (P.H - z) / c  # noqa: E731
        z0, z1 = P.H - 40, P.H + 10
        Z["roof_mitre"] = _prism_xz([(-xb(z0), z0), (xb(z0), z0), (xb(z1), z1), (-xb(z1), z1)], -big, big)
    hx, hy, hd = P.HANDLE
    yc = P.HANDLE_Y - P.HANDLE_UNDERCUT / 2
    handle = Pos(0, yc, P.H - (hd + P.WALL + 1) / 2) * Box(hx + 2 * P.WALL + 2, hy + P.HANDLE_UNDERCUT + 2 * P.WALL + 2,
                                                            hd + P.WALL + 1)
    if "roof" in Z:
        Z["roof"] = Z["roof"] + handle
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
    if "roof_mitre" in Z:
        m = Z.pop("roof_mitre")
        top = box_xyz(-big, big, -big, big, P.H - r, P.H + 10)
        sides_only = box_xyz(-big, big, -big, big, P.H - 40, P.H + 10) - Z["front"] - Z["rear"]
        Z["roof"] = (m & (top + sides_only)) + handle
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


def _walls_union(extra):
    Z = zones(extra)
    u = None
    for k in ("side_l", "side_r", "front", "rear"):
        u = Z[k] if u is None else u + Z[k]
    return u


def base_extras(b):
    """Дно толще (BASE_T) + бортик жёсткости по краю, с зазором FIT от стенок."""
    import fasteners as F
    big = 2 * P.W
    w1 = _walls_union(P.FIT)
    w2 = _walls_union(P.FIT + P.BASE_RIM_T)
    plate = (box_xyz(-big, big, -big, big, 0, P.BASE_T) & b) - w1
    zr = box_xyz(-big, big, -big, big, P.BASE_T - 0.01, P.BASE_T + P.BASE_RIM_H) & b
    rim = (zr & w2) - w1
    for _part, x, y in F.bottom_bosses():
        rim = rim - Pos(x, y, P.BASE_T + 5) * Cylinder(P.BOSS_D / 2 + P.FIT + 0.5, 20)
    return plate + rim


def split_guides(parts, b):
    """Направляющие для склейки (только при печати из частей):
    1) перегиб передней панели: на нижней половине — полка-нахлёст за экранной половиной + 3 шипа ø3,
       в экранной — гнёзда; половины встают только в одно положение, клей — по всей полке;
    2) крыша↔бок: на каждом боку — полка под крышей + 2 шипа вверх, в крыше — гнёзда."""
    big = 2 * P.W
    solid_in = offset(b, amount=-0.6)
    L_LIP, T_LIP, PIN_D, PIN_H = 10.0, 2.0, 3.0, 1.2
    # --- 1) перегиб
    n = Vector(0, -math.cos(P.TILT), math.sin(P.TILT))
    up = Vector(0, math.sin(P.TILT), math.cos(P.TILT))
    pl = Plane(origin=(0, P.Y_TILT, P.BAND_H), x_dir=(1, 0, 0), z_dir=n)
    loc = Location(pl)
    d0 = P.WALL + P.FIT
    xw = P.half_w(P.BAND_H) - P.R_EDGE - 4.0
    # над принтером места нет (верх корпуса принтера в 3 мм под перегибом) → полка только слева от принтера
    x_r = P.PR_X - P.PR_BODY[0] / 2 - P.PR_CLAMP_SIDE - 2.0
    x_l = -xw
    lip = loc * Pos((x_l + x_r) / 2, (L_LIP - 6.0) / 2, -(d0 + T_LIP / 2)) * Box(x_r - x_l, L_LIP + 6.0, T_LIP)
    lip = lip & solid_in
    pins = None
    socks = None
    for x in (x_l + 0.2 * (x_r - x_l), x_l + 0.8 * (x_r - x_l)):
        pin = loc * Pos(x, L_LIP * 0.6, -d0 + PIN_H / 2) * Cylinder(PIN_D / 2, PIN_H + 0.01)
        sock = loc * Pos(x, L_LIP * 0.6, -P.WALL + (PIN_H + 0.3) / 2 - 0.01) * Cylinder(PIN_D / 2 + 0.15, PIN_H + 0.3)
        pins = pin if pins is None else pins + pin
        socks = sock if socks is None else socks + sock
    parts["front_band"] = parts["front_band"] + lip + pins
    parts["front_screen"] = parts["front_screen"] - socks
    # --- 2) крыша↔бок
    zr = P.H - P.WALL - P.FIT
    y0, y1 = P.Y_TOP_FRONT + 14.0, P.Y_TOP_REAR - 14.0
    for side, sx in (("side_l", -1), ("side_r", 1)):
        xi = P.half_w(zr) - P.WALL / math.cos(P.SIDE_LEAN)
        xa, xb_ = sx * (xi + 1.0), sx * (xi - L_LIP)
        lip2 = box_xyz(min(xa, xb_), max(xa, xb_), y0, y1, zr - T_LIP, zr) & solid_in
        roof = parts["roof"]
        for d in ((sx * -P.FIT, 0, 0), (0, 0, -P.FIT), (sx * -P.FIT, 0, -P.FIT)):
            lip2 = lip2 - Pos(*d) * roof
        lip2 = lip2 - roof
        p2 = s2 = None
        for y in (y0 + 0.25 * (y1 - y0), y0 + 0.75 * (y1 - y0)):
            x = sx * (xi - L_LIP / 2)
            pin = Pos(x, y, zr + PIN_H / 2) * Cylinder(PIN_D / 2, PIN_H + 0.01)
            sock = Pos(x, y, zr + P.FIT + (PIN_H + 0.3) / 2 - 0.01) * Cylinder(PIN_D / 2 + 0.15, PIN_H + 0.3)
            p2 = pin if p2 is None else p2 + pin
            s2 = sock if s2 is None else s2 + sock
        parts[side] = parts[side] + lip2 + p2
        parts["roof"] = parts["roof"] - s2
    return parts


def printer_cradle():
    """Опора принтера на дне: 2 продольных ребра + поперечина, верх — по наклонному низу корпуса принтера."""
    loc = Location(band_plane())
    bw, bh = P.PR_BODY
    ch = P.PR_CUT[1]
    u_bot = P.PR_CUT_U0 + (ch - bh) / 2 - P.PR_CRADLE_GAP      # низ корпуса принтера минус зазор
    d0, d1 = P.PR_CRADLE_DEPTH
    t = P.PR_CRADLE_RIB
    blocks = None
    for dx in P.PR_CRADLE_X:
        x = P.PR_X + dx
        r = Pos(x, u_bot - 40, -(d0 + d1) / 2) * Box(t, 80, d1 - d0)
        blocks = r if blocks is None else blocks + r
    xa, xb = P.PR_X + P.PR_CRADLE_X[0], P.PR_X + P.PR_CRADLE_X[1]
    blocks += Pos((xa + xb) / 2, u_bot - 40, -d1 + t / 2) * Box(xb - xa, 80, t)
    big = 2 * P.W
    w = loc * blocks
    return w & box_xyz(-big, big, -big, big, P.BASE_T - 0.01, big)


def _seat(cx, cy, iw, ih):
    """Бортик посадочного места: внутренний размер iw × ih, разрывы по центру коротких сторон."""
    t, h = P.SEAT_WALL
    z0 = P.BASE_T - 0.01
    ring = box_xyz(cx - iw / 2 - t, cx + iw / 2 + t, cy - ih / 2 - t, cy + ih / 2 + t, z0, P.BASE_T + h)
    ring -= box_xyz(cx - iw / 2, cx + iw / 2, cy - ih / 2, cy + ih / 2, z0 - 1, P.BASE_T + h + 1)
    g = P.SEAT_GAP
    ring -= box_xyz(cx - iw / 2 - t - 1, cx + iw / 2 + t + 1, cy - g / 2, cy + g / 2, z0 - 1, P.BASE_T + h + 1)
    return ring


def base_seats():
    """Посадочные места на дне: XL4015 (на клей) и PCF8574 (2 стойки под саморезы M2.5)."""
    xl = _seat(*P.XL_POS, *P.XL_PAD)
    pcf = _seat(*P.PCF_POS, *P.PCF_PAD)
    x0 = P.PCF_POS[0] - P.PCF_BOARD[0] / 2
    y0 = P.PCF_POS[1] - P.PCF_BOARD[1] / 2
    holes = None
    for hx, hy in P.PCF_HOLES:
        st = Pos(x0 + hx, y0 + hy, P.BASE_T + P.PCF_STANDOFF_H / 2 - 0.01) * Cylinder(P.PCF_STANDOFF_D / 2,
                                                                                   P.PCF_STANDOFF_H + 0.02)
        hl = Pos(x0 + hx, y0 + hy, P.BASE_T + P.PCF_STANDOFF_H - 3.0) * Cylinder(1.1, 6.02)
        pcf = pcf + st
        holes = hl if holes is None else holes + hl
    return xl + pcf - holes


def groups():
    """Имена печатных деталей переднего узла и колпака (целиком или из частей)."""
    if P.print_whole():
        return ["front"], ["cover"]
    return ["front_band", "front_screen"], ["side_l", "side_r", "roof"]


def build(with_fasteners=True):
    b = body()
    sh, inner = shell(b)
    sh = sh - _screen_cuts() - _band_cuts() - _grille_cuts() - _rear_cuts()
    parts = split(sh)
    parts["base"] = parts["base"] + base_extras(b) + printer_cradle() + base_seats()
    parts["rear"] = parts["rear"] + rear_bushing()
    parts["screen_bezel"] = screen_bezel()
    bk, sk = bezel_backing_and_sockets()
    parts["front_screen"] = parts["front_screen"] + bk - sk
    hw = {}
    if with_fasteners:
        import fasteners
        parts, hw = fasteners.apply(parts, inner, b)
        from build123d import Compound

        from parts import key_plate as KP
        from parts import speaker_box as SB
        kb, kh = KP.panel_bosses()
        parts["front_band"] = parts["front_band"] + kb - kh
        parts["key_plate"] = KP.key_plate()
        sb, sh_ = SB.base_bosses()
        parts["base"] = parts["base"] + sb - sh_
        parts["speaker_box"] = SB.speaker_box()
        ks, ki = KP.hardware()
        ss, si = SB.hardware()
        hw["screws"] = Compound(children=list(hw["screws"]) + list(ks) + list(ss))
        hw["inserts"] = Compound(children=list(hw["inserts"]) + list(ki) + list(si))
    if not P.print_whole():
        parts = split_guides(parts, b)
    if P.print_whole():
        parts["front"] = parts.pop("front_band") + parts.pop("front_screen")
        parts["cover"] = parts.pop("side_l") + parts.pop("side_r") + parts.pop("roof")
    build.hardware = hw
    return parts


build.hardware = {}
