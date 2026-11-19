"""Этап 3: компоновка из болванок + грубые оболочки корпуса.

Запуск через build123d-mcp: execute_file("layout.py"), затем render_view.
Локально: python layout.py — печатает проверку пересечений.
"""
import itertools

import params as P
from dummies import KEEPOUT, all_dummies
from envelope import chassis_shell, cover_shell, panel_shell

shells = {"panel": panel_shell(), "chassis": chassis_shell(), "cover": cover_shell()}
dummies = all_dummies()

# Пары, которые по смыслу соприкасаются/проходят насквозь — не ошибка.
EXPECTED = {
    ("panel", "pr_body"), ("panel", "pr_frame"),            # принтер вставлен в вырез (вырез ещё не прорезан)
    ("panel", "key_switches"), ("panel", "key_caps"),       # окна под клавиши ещё не прорезаны
    ("panel", "scr_glass"),                                  # окно экрана ещё не прорезано
    ("chassis", "kcd1"), ("chassis", "cable"),               # проходят сквозь заднюю стенку
    ("spk_chamber_env", "speaker"), ("pr_body", "pr_rear_keepout"),
    ("key_plate", "key_switches"), ("key_switches", "key_caps"),
    ("scr_pcb", "scr_glass"), ("scr_pcb", "scr_back_keepout"),
    ("pr_body", "pr_lid_keepout"), ("pr_frame", "pr_lid_keepout"),
    ("panel", "cover"),                                      # стык колпак↔панель: в деталях будет паз
}


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
