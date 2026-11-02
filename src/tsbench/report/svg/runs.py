"""Parallel coordinates of the runs: one polyline per run across the axes, static, no brushing and no script.

Each axis runs from its smallest to its largest value in the data; both are printed. The title of a line has the task,
the condition, the outcome and the value on every axis.
"""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

from . import base

__all__ = ["parallel_coords"]


def _num(v: float, cap: int = 4) -> str:
    """`v` with the fewest decimals (up to `cap`) that keep it; more digits are cut at `cap`."""
    for nd in range(cap + 1):
        if round(v, nd) == v:
            return base.number(v, nd)
    return base.number(v, cap)


def _tick(v: float, hi: float) -> str:
    """A tick value: fewest decimals that keep it, at most the decimals that give three digits at the high end."""
    top = abs(hi) if hi else 1.0
    cap = min(max(2 - math.floor(math.log10(top)), 0), 4)
    return _num(v, cap)


def _lines(label: str, room: float) -> list[str]:
    """The label on one line, or on two when it is wider than `room` and has a space."""
    if base.text_width(label) <= room or " " not in label:
        return [label]
    words = label.split(" ")
    best = min(range(1, len(words)), key=lambda i: abs(len(" ".join(words[:i])) - len(" ".join(words[i:]))))
    return [" ".join(words[:best]), " ".join(words[best:])]


def parallel_coords(runs: Sequence[Mapping], axes: Sequence[tuple[str, str]], log_axes: Sequence[str] = (),
                    width: float = 720.0, height: float = 300.0) -> str:
    """Parallel coordinates: `runs` `[{"cond", "task", "correct", "values": {key: float | None}}]`, `axes`
    `[(key, label)]`.

    One line per run, in the colour of its condition and dashed when the run is not correct. A missing value breaks
    the line. Axes named in `log_axes` (all values above zero) are logarithmic."""
    if not runs or not axes:
        return ""
    margin, top = 40.0, 70.0
    bottom = top + height
    gap = (width - 2 * margin) / max(len(axes) - 1, 1)
    xs = [margin + i * gap if len(axes) > 1 else width / 2 for i in range(len(axes))]
    scales, spans = [], []
    body: list[str] = []
    for i, (key, label) in enumerate(axes):
        vals = [float(r["values"][key]) for r in runs if (r.get("values") or {}).get(key) is not None]
        lo, hi = (min(vals), max(vals)) if vals else (0.0, 1.0)
        if lo == hi:
            lo, hi = lo - 1.0, hi + 1.0
        if key in log_axes and lo > 0:
            scales.append(base.Log(lo, hi, bottom, top))
        else:
            scales.append(base.Linear(lo, hi, bottom, top))
        spans.append((lo, hi))
        body.append(base.line(xs[i], top, xs[i], bottom, "ax"))
        for k, part in enumerate(_lines(label, gap - 6)):
            body.append(base.text(xs[i], 14 + k * (base.TEXT_PX + 2), part, "middle", "b"))
        body.append(base.text(xs[i], top - 10, _tick(hi, hi), "middle", "mut"))
        body.append(base.text(xs[i], bottom + 6 + base.TEXT_PX, _tick(lo, hi), "middle", "mut"))
    lines = []
    for cond in base.CONDS:
        for r in runs:
            if r.get("cond") != cond:
                continue
            vals = r.get("values") or {}
            d, prev = [], False
            tips = []
            for i, (key, label) in enumerate(axes):
                v = vals.get(key)
                if v is None:
                    prev = False
                    continue
                d.append(f"{'L' if prev else 'M'}{base.coord(xs[i])},{base.coord(scales[i](float(v)))}")
                tips.append(f"{label} {_num(float(v))}")
                prev = True
            if not d:
                continue
            ok = bool(r.get("correct"))
            tip = f"{r.get('task')} · {cond} · {'correct' if ok else 'not correct'} · " + " · ".join(tips)
            lines.append(base.path(" ".join(d), f"flow c-{cond}", tip, width=1.0, dash=None if ok else "4 3"))
    y = bottom + 6 + base.TEXT_PX + 26
    leg, x = base.legend([(c, c) for c in base.CONDS if any(r.get("cond") == c for r in runs)], margin, y)
    leg += base.line(x + 4, y - 4, x + 30, y - 4, "ax", dash="4 3", width=1.4) + base.text(x + 36, y, "not correct")
    return base.figure(width, y + 10, f"Parallel coordinates of {len(runs)} runs on {len(axes)} axes",
                       "".join(body) + "".join(lines) + leg)
