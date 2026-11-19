"""Болванки компонентов (по габаритам) в координатах сборки. Только из params.py."""
import math

from build123d import Box, Compound, Cylinder, Location, Plane, Pos, Rot, Vector, import_step

import params as P


def box_xyz(x0, x1, y0, y1, z0, z1):
    """Бокс по границам в координатах сборки."""
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(x1 - x0, y1 - y0, z1 - z0)


def box_local(x0, x1, y0, y1, z0, z1):
    return box_xyz(x0, x1, y0, y1, z0, z1)


# ------------------------------------------------------------------ плоскости граней
def band_plane():
    """Нижний пояс: local X = мировой X, local Y = вверх по поясу (u), local Z = наружу; начало — низ лица."""
    n = Vector(0, -math.cos(P.BAND_TILT), math.sin(P.BAND_TILT))
    return Plane(origin=(0, 0, 0), x_dir=(1, 0, 0), z_dir=n)


def screen_plane():
    """Плоскость, переводящая координаты STEP-модели CrowPanel в сборку (начало = центр АО на лице стекла)."""
    n = Vector(0, -math.cos(P.TILT), math.sin(P.TILT))
    y, z = P.slope_point(P.SCR_AA_S, depth=P.SCR_RECESS + P.SCR_Z_GLASS_FRONT)
    x_dir = Vector(-1, 0, 0) if P.SCR_ROT_180 else Vector(1, 0, 0)
    return Plane(origin=(0, y, z), x_dir=x_dir, z_dir=n)


def rear_plane(x=0.0, z=0.0):
    n = (0, math.cos(P.REAR_LEAN), math.sin(P.REAR_LEAN))
    return Plane(origin=(x, P.y_rear(z), z), x_dir=(-1, 0, 0), z_dir=n)


# ------------------------------------------------------------------ экран
def screen_local():
    """Болванки экрана в координатах STEP (центр АО = 0,0; +Z к зрителю)."""
    pcb_w, pcb_h, pcb_t = P.SCR_PCB
    out = {}
    out["scr_pcb"] = Pos(0, P.SCR_PCB_CY, (P.SCR_Z_PCB_FRONT + P.SCR_Z_PCB_BACK) / 2) * Box(pcb_w, pcb_h, pcb_t)
    gz0, gz1 = P.SCR_Z_PCB_FRONT, P.SCR_Z_GLASS_FRONT
    out["scr_glass"] = Pos(0, P.SCR_GLASS_CY, (gz0 + gz1) / 2) * Box(*P.SCR_GLASS, gz1 - gz0)
    bz0, bz1 = P.SCR_Z_BACK_MAX, P.SCR_Z_PCB_BACK
    out["scr_back_keepout"] = Pos(0, P.SCR_PCB_CY, (bz0 + bz1) / 2) * Box(pcb_w, pcb_h, bz1 - bz0)
    y_top = P.SCR_PCB_CY + pcb_h / 2
    out["scr_cable_keepout"] = Pos(15, y_top + P.SCR_TOP_CABLE / 2, (bz0 + bz1) / 2) * Box(
        110, P.SCR_TOP_CABLE, bz1 - bz0 + 4)
    x0, x1, y0, y1, _ = P.SCR_CONNECTORS["USB-C"]
    out["scr_usb_keepout"] = Pos(-pcb_w / 2 - P.SCR_USB_PLUG / 2, (y0 + y1) / 2, -7.5) * Box(
        P.SCR_USB_PLUG, 12, 8)
    return out


def screen():
    loc = Location(screen_plane())
    return {k: loc * v for k, v in screen_local().items()}


def screen_step():
    """Настоящая модель платы (без акрилового корпуса) — для наглядных рендеров."""
    c = import_step("vendor/crowpanel5_bare.step")
    return Location(screen_plane()) * c


# ------------------------------------------------------------------ принтер (в плоскости пояса; глубина = -local Z)
def printer():
    loc = Location(band_plane())
    cw, ch = P.PR_CUT
    bw, bh = P.PR_BODY
    fw, fh = P.PR_FRAME
    uc = P.PR_CUT_U0 + ch / 2
    x = P.PR_X
    L = {}
    L["pr_frame"] = box_local(x - fw / 2, x + fw / 2, uc - fh / 2, uc + fh / 2, 0, P.PR_FRAME_T)
    L["pr_body"] = box_local(x - bw / 2, x + bw / 2, uc - bh / 2, uc + bh / 2, -P.PR_BEHIND, 0)
    L["pr_rear_keepout"] = box_local(x - bw / 2, x + bw / 2, uc - bh / 2, uc + bh / 2,
                                     -P.PR_BEHIND - P.PR_REAR_FREE, -P.PR_BEHIND)
    for side, sx in (("l", -1), ("r", 1)):
        xa = x + sx * bw / 2
        xb = xa + sx * P.PR_CLAMP_SIDE
        L[f"pr_clamp_{side}_keepout"] = box_local(min(xa, xb), max(xa, xb), uc - bh / 2, uc + bh / 2,
                                                  -P.PR_BEHIND, -P.PANEL_T)
    # откидывание крышки лотка: четверть цилиндра перед рамкой, ось вдоль X у верхней кромки рамки
    hu, hz = uc + fh / 2, P.PR_FRAME_T
    r = P.PR_LID_SWEEP
    cyl = Pos(x, hu, hz) * Rot(0, 90, 0) * Cylinder(r, fw)
    quad = box_local(x - fw, x + fw, hu - r - 1, hu + 1, hz, hz + r + 1)
    L["pr_lid_keepout"] = cyl & quad
    return {k: loc * v for k, v in L.items()}


# ------------------------------------------------------------------ клавиши
def key_centers():
    return [P.KEY_X + (i - (P.KEY_N - 1) / 2) * P.KEY_PITCH for i in range(P.KEY_N)]


def keys():
    loc = Location(band_plane())
    u = P.KEY_U
    t = P.PANEL_T
    pw = (P.KEY_N - 1) * P.KEY_PITCH + 14 + 2 * 3
    L = {}
    p0, p1 = -t - P.KEY_PLATE_T, -t           # пластина прижата к тылу панели
    L["key_plate"] = box_local(P.KEY_X - pw / 2, P.KEY_X + pw / 2, u - 14, u + 14, p0, p1)
    sw, caps = [], []
    cw, ch, cz = P.KEY_CAP
    for x in key_centers():
        sw.append(box_local(x - 7, x + 7, u - 7, u + 7, p0 - P.KEY_BELOW_PLATE, p0))
        sw.append(box_local(x - 7.8, x + 7.8, u - 7.8, u + 7.8, p1, p1 + P.KEY_ABOVE_PLATE))
        top = p1 + P.KEY_ABOVE_PLATE - 1.0 + cz
        caps.append(box_local(x - cw / 2, x + cw / 2, u - ch / 2, u + ch / 2, top - cz, top))
    L["key_switches"] = Compound(children=sw)
    L["key_caps"] = Compound(children=caps)
    L["key_wire_keepout"] = box_local(P.KEY_X - pw / 2, P.KEY_X + pw / 2, u - 12, u + 12,
                                      p0 - P.KEY_BELOW_PLATE - 10, p0 - P.KEY_BELOW_PLATE)
    return {k: loc * v for k, v in L.items()}


# ------------------------------------------------------------------ внутренности
def internals():
    out = {}
    z0 = P.BASE_T
    x, y = P.XL_POS
    w, d = P.XL_PAD
    out["xl4015"] = box_xyz(x - w / 2, x + w / 2, y - d / 2, y + d / 2, z0, z0 + P.XL_H)
    out["xl4015_side_keepout"] = box_xyz(x + w / 2, x + w / 2 + P.XL_SIDE_FREE, y - d / 2, y + d / 2,
                                         z0, z0 + P.XL_H)
    x, y = P.PCF_POS
    bw, bd, bt = P.PCF_BOARD
    zp = z0 + P.PCF_STANDOFF_H
    out["pcf8574"] = box_xyz(x - bw / 2, x + bw / 2, y - bd / 2, y + bd / 2, zp, zp + bt + 8.5)
    # динамик: лицом к решётке на правом боку; камера параллельна завалу боковины
    yc, zc = P.GRILLE_C[0] * P.D, P.GRILLE_C[1]
    cin = P.SPK_CHAMBER_IN
    xo = P.half_w(zc) - P.COVER_T - P.FIT - P.SPK_FOAM       # наружная грань камеры
    rot = Location((xo, yc, zc)) * Rot(0, -P.SIDE_LEAN_DEG, 0)
    cw = cin[0] + 2 * P.WALL
    out["spk_chamber_env"] = rot * box_xyz(-cw, 0, -cin[1] / 2 - P.WALL, cin[1] / 2 + P.WALL,
                                           -cin[2] / 2 - P.WALL, cin[2] / 2 + P.WALL)
    # подставка камеры до дна (печатается заодно с камерой)
    zb = zc - cin[2] / 2 - P.WALL
    out["spk_stand"] = box_xyz(xo - cw + 2, xo - 2, yc - cin[1] / 2, yc + cin[1] / 2, P.BASE_T + P.BASE_RIM_H + 0.5, zb - 2.0) if zb - 2.0 > P.BASE_T + P.BASE_RIM_H + 1.5 else None
    if out["spk_stand"] is None:
        del out["spk_stand"]
    out["speaker"] = rot * Pos(-P.WALL - P.SPK_DEPTH / 2, 0, 0) * Rot(0, 90, 0) * Cylinder(P.SPK_D / 2, P.SPK_DEPTH)
    # задняя стенка
    sx, sz = P.SW_POS
    out["kcd1"] = Location(rear_plane(sx, sz)) * box_xyz(-P.SW_CUT[0] / 2, P.SW_CUT[0] / 2,
                                                         -P.SW_CUT[1] / 2, P.SW_CUT[1] / 2, -P.SW_BODY_D, 2)
    cx, cz = P.CABLE_POS
    out["cable"] = Location(rear_plane(cx, cz)) * Pos(0, 0, -10) * Cylinder(P.CABLE_D / 2, 40)
    return out


def all_dummies():
    d = {}
    for f in (screen, printer, keys, internals):
        d.update(f())
    return d


def KEEPOUT(name):
    return name.endswith("_keepout") or name.endswith("_env")
