"""Этап 3: компоновка из болванок + грубые оболочки корпуса.

Запуск через build123d-mcp: execute_file("layout.py"), затем render_view.
Локально: python layout.py — печатает проверку пересечений.
"""
import itertools

import params as P
from dummies import KEEPOUT, all_dummies
import envelope

shells = envelope.build()
hardware = envelope.build.hardware
dummies = all_dummies()

# Пары, которые по смыслу соприкасаются/проходят насквозь — не ошибка.
FRONT_P, COVER_P = envelope.groups()
PANELS = {"base", "rear", *FRONT_P, *COVER_P}
EXPECTED = {
    ("spk_chamber_env", "speaker"), ("pr_body", "pr_rear_keepout"),
    ("key_plate", "key_switches"), ("key_switches", "key_caps"),
    ("scr_pcb", "scr_glass"), ("scr_pcb", "scr_back_keepout"),
    ("pr_body", "pr_lid_keepout"), ("pr_frame", "pr_lid_keepout"),
    (FRONT_P[0], "pr_frame"),                    # рамка принтера лежит на лице пояса
    ("rear", "kcd1"), ("rear", "cable"),         # проходят сквозь заднюю стенку
    ("screen_bezel", FRONT_P[-1]),
}
# стыки панелей — только касание по шву, объём пересечения ≈ 0, поэтому их НЕ исключаем


def clashes(min_vol=0.5):
    items = list(shells.items()) + list(dummies.items())
    out = []
    for (na, a), (nb, b) in itertools.combinations(items, 2):
        if (na, nb) in EXPECTED or (nb, na) in EXPECTED:
            continue
        if KEEPOUT(na) and KEEPOUT(nb) and not (na.startswith("pr_lid") or nb.startswith("pr_lid")):
            pass
        bba, bbb = a.bounding_box(), b.bounding_box()
        if (bba.max.X < bbb.min.X or bbb.max.X < bba.min.X or bba.max.Y < bbb.min.Y or
                bbb.max.Y < bba.min.Y or bba.max.Z < bbb.min.Z or bbb.max.Z < bba.min.Z):
            continue
        try:
            v = (a & b).volume
        except Exception as e:  # noqa: BLE001
            v = -1
            print("bool fail", na, nb, e)
        if v > min_vol:
            out.append((na, nb, round(v, 1)))
    return out


def lift_test(steps=(1, 3, 6, 10, 20, 40, 80, 120)):
    """Колпак (бока+крыша) поднимаем строго вверх: не должен цепляться за каркас и компоненты."""
    from build123d import Pos
    cover = None
    for n in COVER_P:
        cover = shells[n] if cover is None else cover + shells[n]
    others = {k: v for k, v in {**shells, **dummies}.items()
              if k not in COVER_P and not KEEPOUT(k)}
    bad = []
    for dz in steps:
        c = Pos(0, 0, dz) * cover
        for n, o in others.items():
            v = (c & o).volume
            if v > 0.5:
                bad.append((dz, n, round(v, 1)))
    return bad


def envelope_report():
    allc = None
    for s in shells.values():
        allc = s if allc is None else allc + s
    bb = allc.bounding_box()
    return f"envelope X {bb.size.X:.1f} × Y {bb.size.Y:.1f} × Z {bb.size.Z:.1f} мм (Ш×Г×В)"


try:
    show  # noqa: F821 — есть внутри build123d-mcp
    for n, s in {**shells, **dummies}.items():
        show(s, n)  # noqa: F821
    try:
        from dummies import screen_step
        show(screen_step(), "crowpanel")  # noqa: F821
    except Exception as e:  # noqa: BLE001
        print("crowpanel STEP not shown:", e)
    result = shells["panel"]
except NameError:
    pass

if __name__ == "__main__" or "show" in dir():
    print(envelope_report())
    for c in clashes():
        print("CLASH", c)
