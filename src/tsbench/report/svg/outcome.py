"""Outcome figures: diverging stacked bars of outcome categories and the UpSet plot."""
from __future__ import annotations

from collections.abc import Sequence

from . import base

__all__ = ["outcome_diverging", "upset"]


def outcome_diverging(rows: Sequence[dict], categories: Sequence[tuple[str, str]], *,
                      width: float = base.FULL_W) -> str:
    """One bar per condition: the first category right of zero, the others stacked left of zero in the given order.
    A count is printed inside its segment when it fits, else not at all (the table beside the figure has every
    number)."""
    if not rows or not categories:
        return ""
    w, x0 = float(width), 34.0
    x1 = w - 16.0
    (good_key, good_label), errors = categories[0], list(categories[1:])
    left = max((sum(r["counts"].get(k, 0) for k, _ in errors) for r in rows), default=0)
    right = max((r["counts"].get(good_key, 0) for r in rows), default=0)
    sx = base.Linear(-max(left, 1), max(right, 1), x0, x1)
    err_cls = base.error_classes(k for k, _ in errors)
    legend_svg, top = base.legend_rows([("ok", good_label), *((err_cls[k], lab) for k, lab in errors)], x1 - x0, x0, 14)
    top += 8
    row_h, bar_h = 32.0, 20.0
    axis_y = top + len(rows) * row_h + 4
    ticks = base.nice_ticks(-max(left, 1), max(right, 1), 6)
    out = [legend_svg, base.axis_bottom(sx, ticks, axis_y, x0, x1, "runs", lambda v: base.number(abs(v)), grid_to=top)]
    for i, r in enumerate(rows):
        cond, counts = r["cond"], r["counts"]
        n = sum(counts.get(k, 0) for k, _ in categories)
        y = top + i * row_h + (row_h - bar_h) / 2
        out.append(base.text(0, y + bar_h / 2 + base.TEXT_PX * 0.35, cond, "start", "b"))
        segs = [(good_key, good_label, "ok", "on-ok", 0.0, counts.get(good_key, 0))]
        cum = 0
        for k, lab in errors:
            c = counts.get(k, 0)
            segs.append((k, lab, f"{err_cls[k]} tile", f"on-{err_cls[k]}", -(cum + c), c))
            cum += c
        for _, lab, cls, ink, start, c in segs:
            if c <= 0:
                continue
            sx0, sx1 = round(sx(start), 2), round(sx(start + c), 2)  # whole hundredths: the segments meet exactly
            out.append(base.rect(sx0, y, sx1 - sx0, bar_h, cls, f"{cond}: {lab} {c} of {n} runs"))
            if sx1 - sx0 >= 7.0 * len(str(c)) + 6:  # the count inside the segment, in the ink that reads on its fill
                out.append(base.text((sx0 + sx1) / 2, y + bar_h / 2 + base.TEXT_PX * 0.35, c, "middle", ink))
    out.append(base.line(sx(0), top, sx(0), axis_y, "zero"))
    return base.figure(w, axis_y + 12 + 2 * base.TEXT_PX + 8, "Outcome categories per condition", out)


# ---------------------------------------------------------------- UpSet

_BAR_W, _BAR_AREA, _ROW_H, _MX = 24.0, 120.0, 26.0, 150.0  # the widest bar; the rest are fixed sizes


def _members(key: str) -> str:
    return "".join(c for c in base.CONDS if c in key)


def _subset_label(key: str) -> str:
    return "none" if not key else f"{', '.join(key)} only"


def _tasks_tip(label: str, tasks: Sequence[str]) -> str:
    n = len(tasks)
    return f"{label}: {base.plural(n, 'task')}" + (f" ({', '.join(tasks)})" if tasks else "")


def upset(sets: Sequence[dict], *, width: float = base.FULL_W, excluded: Sequence[str] = (),
          conds: Sequence[str] = base.CONDS) -> str:
    """Counts of the subsets of `conds` (default {A, B, C}) as bars above a membership matrix, set sizes at the left.
    The subsets share the width right of the set sizes. A condition not in `conds` (it has no evaluable run) has no
    row and no set size, and no subset that contains it is drawn. `excluded` are the tasks left out of every subset
    because a condition has no evaluable run of them; the figure says how many."""
    conds = [c for c in base.CONDS if c in conds]
    items = sorted(((_members(s["key"]), [str(t) for t in s["tasks"]]) for s in sets
                    if set(_members(s["key"])) <= set(conds)), key=lambda kv: (-len(kv[1]), len(kv[0]), kv[0]))
    if not items:
        return ""
    peak = max(len(t) for _, t in items) or 1
    unit = _BAR_AREA / peak
    top = 24.0
    base_y = top + _BAR_AREA
    row0 = base_y + 34
    w = float(width)
    pitch = (w - _MX - 8) / len(items)
    bar_w = min(_BAR_W, pitch * 0.6)
    sizes = {c: sum(len(t) for k, t in items if c in k) for c in conds}
    size_unit = 80.0 / (max(sizes.values()) or 1)
    out = [base.axis_left(base.Linear(0, peak, base_y, top), base.nice_ticks(0, peak, 4), _MX - 8, top, base_y, "tasks",
                          grid_to=w),
           base.text(0, row0 - 14, "tasks per condition", "start", "mut")]
    for j, c in enumerate(conds):
        cy = row0 + j * _ROW_H
        out += [base.rect(112 - sizes[c] * size_unit, cy - 8, sizes[c] * size_unit, 16, f"c-{c}",
                          f"{c}: {sizes[c]} tasks"),
                base.text(108 - sizes[c] * size_unit, cy + base.TEXT_PX * 0.35, sizes[c], "end", "mut"),
                base.text(122, cy + base.TEXT_PX * 0.35, c, "start", "b")]
    for i, (key, tasks) in enumerate(items):
        cx = _MX + i * pitch + pitch / 2
        tip = _tasks_tip(_subset_label(key), tasks)
        h = len(tasks) * unit
        cls = f"c-{key}" if len(key) == 1 else ("muted" if key else "na")
        out += [base.rect(cx - bar_w / 2, base_y - h, bar_w, h, cls, tip),
                base.text(cx, base_y - h - 5, len(tasks), "middle")]
        rows = [j for j, c in enumerate(conds) if c in key]
        if len(rows) > 1:
            out.append(base.line(cx, row0 + rows[0] * _ROW_H, cx, row0 + rows[-1] * _ROW_H, "zero"))
        for j, c in enumerate(conds):
            on = c in key
            out.append(base.circle(cx, row0 + j * _ROW_H, 6.0 if on else 3.5, f"c-{c}" if on else "band",
                                   tip if on else ""))
    height = row0 + (len(conds) - 1) * _ROW_H + 16
    if excluded:
        n = len(excluded)
        note = (f"{base.plural(n, 'task')} left out: a condition has no evaluable run of "
                f"{'it' if n == 1 else 'them'}")
        out.append(base.group(base.text(0, height + 12, note, "start", "mut", base.SMALL_PX),
                              tip=", ".join(map(str, excluded))))
        height += 22
    return base.figure(w, height, "Tasks per subset of conditions", out)
