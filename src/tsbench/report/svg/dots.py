"""Dot plots of the report: share correct per task class and reported against oracle values of the literature
systems.

Both are static SVG: a dot per condition on a thin axis, the exact numbers in the titles.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence

from . import base

__all__ = ["class_dots", "literature_dots"]


def _signed(x: float) -> str:
    """A signed percentage: "+20 %", "−3.5 %"; a value that rounds to zero has no sign: "0 %"."""
    s = base.number(x, 0 if abs(x) >= 10 or abs(x - round(x)) < 0.05 else 1)
    if s.lstrip("−") == "0":
        return "0 %"
    return f"{'+' if x > 0 else ''}{s} %"


def _tick(v: float) -> str:
    return _signed(v).replace(" %", "")


# ---------------------------------------------------------------- share correct per class


def _n_of(row: Mapping, cond: str) -> int:
    """The tasks of a class with an evaluable run under `cond` (all its tasks when the row has no `n_by`)."""
    return int((row.get("n_by") or {}).get(cond, row["n"]))


def _present(ks) -> list[str]:
    """The conditions some `k` mapping carries, in the order A, B, C; all three when none does. A condition with no
    evaluable run is absent from `k` and is not drawn as 0."""
    have = {c for k in ks for c in k}
    return [c for c in base.CONDS if c in have] or list(base.CONDS)


def class_dots(rows: Sequence[Mapping], *, width: float = base.FULL_W) -> str:
    """Dumbbell dot plot: one row per task class, x = k/n per condition, a line from the lowest to the highest dot.

    `rows` `[{"class", "n", "k": {"A": int, "B": int, "C": int}}]`, `k` with the conditions that have an evaluable
    run only (the others are not drawn); an optional `"n_by"` gives per condition the tasks
    with an evaluable run (default `n`), which is the n of that condition's share and label. The k/n labels stand in
    a column right of the plot, never on a marker: conditions with the same k share one label (`B C 3/5`), lowest k
    first. A condition with no evaluable run (n 0) has no marker and no line end, and its label says `no run`."""
    if not rows:
        return ""
    conds = _present(r["k"] for r in rows)
    pitch, top = 26.0, 40.0
    labels = [f"{r['class']} (n={r['n']})" for r in rows]
    left = max(base.text_width(s) for s in labels) + 16
    texts = []
    for r in rows:
        groups: dict[tuple[int, int], list[str]] = {}
        for c in conds:
            groups.setdefault((int(r["k"].get(c, 0)), _n_of(r, c)), []).append(c)
        texts.append([f"{' '.join(groups[g])} {g[0]}/{g[1]}" if g[1] else f"{' '.join(groups[g])} no run"
                      for g in sorted(groups)])
    col_w = max(sum(base.text_width(t) + 10 for t in row) for row in texts) - 10
    x_end = width - col_w - 28
    xs = base.Linear(0.0, 1.0, left, x_end)
    y_axis = top + len(rows) * pitch + 4
    body = [base.axis_bottom(xs, [0, 0.25, 0.5, 0.75, 1], y_axis, left, x_end, "share correct, k out of n",
                             lambda v: f"{base.round_half_up(100 * v)} %", top)]
    leg, _ = base.legend([(c, c) for c in conds], left, 14)
    body.append(leg)
    for i, r in enumerate(rows):
        y = top + (i + 0.5) * pitch
        ns = {c: _n_of(r, c) for c in conds}
        ks = {c: int(r["k"].get(c, 0)) for c in conds}
        share = {c: ks[c] / ns[c] for c in conds if ns[c]}  # a condition without an evaluable run has no share
        body.append(base.text(left - 10, y + base.TEXT_PX * 0.35, labels[i], "end"))
        lo, hi = min(share, key=lambda c: share[c], default=None), max(share, key=lambda c: share[c], default=None)
        if lo and hi and share[lo] != share[hi]:
            body.append(base.line(xs(share[lo]), y, xs(share[hi]), y, "ax", f"{r['class']}: lowest {ks[lo]}/{ns[lo]}, "
                                  f"highest {ks[hi]}/{ns[hi]}", width=2.0))
        for c in share:
            body.append(base.marker(c, xs(share[c]), y, True, 4.4,
                                    f"{r['class']} · {c}: {ks[c]}/{ns[c]} ({base.number(100 * share[c])} %)"))
        lx = x_end + 20
        for t in texts[i]:
            body.append(base.text(lx, y + base.TEXT_PX * 0.35, t, "start", "mut"))
            lx += base.text_width(t) + 10
    title = f"Share correct per task class, {len(rows)} classes"
    return base.figure(width, y_axis + 8 + 2 * base.TEXT_PX + 6, title, "".join(body))


# ---------------------------------------------------------------- literature systems


def _placed(mark: str, href: str | None, x: float, y: float, dev: float, edge: float) -> str:
    """A mark of the literature plot, linked when `href`; beyond the axis it carries an arrow (its value is printed
    by `_edge_labels`)."""
    out = [mark if href is None else base.link(href, mark)]
    if abs(dev) > edge:
        sign = 1 if dev > 0 else -1
        ax = x + sign * 5
        out.append(base.polygon([(ax + sign * 4, y), (ax, y - 3), (ax, y + 3)], "muted"))
    return "".join(out)


def _edge_labels(beyond: list[tuple[str, float, float, float]]) -> str:
    """One label per edge of a row for the values beyond the axis (`(name, dev, x, y)`), beside the first of them: a
    lone condition value alone, otherwise each value after its name ("B +282 % · C +313 %", "paper −80 %")."""
    out = []
    for sign in (1, -1):
        side = [b for b in beyond if (b[1] > 0) == (sign > 0)]
        if not side:
            continue
        named = len(side) > 1 or side[0][0] == "paper"
        label = " · ".join(f"{n} {_signed(d)}" if named else _signed(d) for n, d, _, _ in side)
        _, _, x, y = side[0]
        out.append(base.text(x - sign * 6, y + 4, label, "end" if sign > 0 else "start", "mut", base.SMALL_PX))
    return "".join(out)


def literature_dots(systems: Sequence[Mapping], *, width: float = base.FULL_W,
                    task_href: Callable[[str], str] | None = None) -> str:
    """One panel per required parameter (Dq, B and, where a system requires it, C), one row per system:
    x = reported / oracle − 1 in percent, axis ±50 %.

    `systems` `[{"system", "task", "oracle": {"Dq", "B", "C"}, "tol": {...}, "paper": {...}, "reported": {"A": {"Dq",
    "B", "C", "ok"} | None, ...}}]`, `tol` a fraction. The band behind a row is ± its tolerance. A condition mark is
    filled when the answer is correct (`ok`; without it: inside the band) and open when not; the diamond is the
    value of the paper. A deviation beyond ±50 % is drawn at the edge with an arrow and its value. A long name
    wraps to more lines; with `task_href` a mark and a name open the row of the task (`system["task"]`)."""
    if not systems:
        return ""
    qs = [q for q in ("Dq", "B", "C") if any((s.get("oracle") or {}).get(q) is not None for s in systems)]
    qs = qs or ["Dq", "B"]
    edge, lane = 50.0, 7.0
    top, gap, right = 54.0, 28.0 if width >= 600 else 30.0, 20.0
    left = min(max(base.text_width(str(s["system"])) for s in systems) + 16, 230.0 if width >= 600 else 128.0)
    pw = (width - left - (len(qs) - 1) * gap - right) / len(qs)
    names = [base.wrap(str(s["system"]), left - 22, least=4, split_words=True) or [str(s["system"])] for s in systems]
    heights = [max(4 * lane + 2, base.TEXT_PX * 1.15 * len(n) + 8) for n in names]
    rows_y = [top + sum(heights[:i]) for i in range(len(systems))]
    y_end = top + sum(heights)
    body = []
    leg, _ = base.legend([(c, c) for c in base.CONDS] + [("open", "open: not correct"), ("paper", "paper value")],
                         0, 14)
    body.append(leg)
    for j, q in enumerate(qs):
        x0 = left + j * (pw + gap)
        sc = base.Linear(-edge, edge, x0, x0 + pw)
        body.append(base.text(x0, top - 18, q, "start", "b"))
        if pw > 150:
            body.append(base.text(x0 + pw, top - 18, "reported / oracle − 1", "end", "mut"))
        long_label = f"{q}: deviation from the oracle value (%)"
        # centred on the panel, the long label runs over into the gap on both sides: it may use only part of it
        axis_label = long_label if pw > 150 and len(long_label) * 5.6 - pw <= gap - 8 else f"{q}: deviation (%)"
        body.append(base.axis_bottom(sc, [-50, 0, 50] if pw < 150 else [-50, -25, 0, 25, 50], y_end + 2, x0, x0 + pw,
                                     axis_label, _tick, top))
        for i, s in enumerate(systems):
            y, h = rows_y[i] + heights[i] / 2, heights[i]
            task = s.get("task")
            href = None if task_href is None or not task else task_href(str(task))
            oracle = (s.get("oracle") or {}).get(q)
            tol = (s.get("tol") or {}).get(q)
            if j == 0:
                ty = y - (len(names[i]) - 1) * base.TEXT_PX * 1.15 / 2 + base.TEXT_PX * 0.35
                label = "".join(base.text(left - 20, ty + n * base.TEXT_PX * 1.15, ln, "end")
                                for n, ln in enumerate(names[i]))
                body.append(label if href is None else base.link(href, label))
            if oracle is None:
                continue
            if tol is not None:
                body.append(base.rect(sc(-100 * tol), y - h * 0.42, sc(100 * tol) - sc(-100 * tol), h * 0.84,
                                      "band", f"{s['system']} · {q} tolerance ±{100 * tol:g} %"))

            beyond: list[tuple[str, float, float, float]] = []
            for k, c in enumerate(base.CONDS):
                rep = (s.get("reported") or {}).get(c)
                val = None if rep is None else rep.get(q)
                if rep is None or val is None or not oracle:
                    continue
                dev = (val / oracle - 1) * 100
                ok = rep.get("ok")
                inside = bool(ok) if ok is not None else tol is not None and abs(dev) <= 100 * tol + 1e-9
                tip = (f"{s['system']} · {q} · {c}: reported {base.number(val, 0)} · oracle {base.number(oracle, 0)} · "
                       f"{_signed(dev)}")
                mx, my = sc(max(-edge, min(edge, dev))), y + (k - 1.5) * lane
                body.append(_placed(base.marker(c, mx, my, inside, 3.3, tip), href, mx, my, dev, edge))
                if abs(dev) > edge:
                    beyond.append((c, dev, mx, my))
            paper = (s.get("paper") or {}).get(q)
            if paper is not None and oracle:
                dev = (paper / oracle - 1) * 100
                tip = (f"{s['system']} · {q} · paper: {base.number(paper, 0)} · oracle {base.number(oracle, 0)} · "
                       f"{_signed(dev)}")
                mx, my = sc(max(-edge, min(edge, dev))), y + 1.5 * lane
                body.append(_placed(base.diamond(mx, my, 3.8, tip), href, mx, my, dev, edge))
                if abs(dev) > edge:
                    beyond.append(("paper", dev, mx, my))
            body.append(_edge_labels(beyond))
        body.append(base.line(sc(0), top, sc(0), y_end, "zero"))
    return base.figure(width, y_end + 2 + 8 + 2 * base.TEXT_PX + 6, f"Reported against oracle values of {len(systems)} "
                       "systems", "".join(body))
