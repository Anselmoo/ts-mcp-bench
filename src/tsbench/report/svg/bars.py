"""Plain bars: counts per row and scores per row, laid out inside the width they are given."""
from __future__ import annotations

from collections.abc import Sequence

from . import base

__all__ = ["hbars", "score_bars"]

_ROW_H = 24
_BAR_H = 14
_TOP = 22
_NUM_W = 64.0  # room for the number right of a bar


def _label_width(labels: Sequence[str], width: float) -> float:
    """The room for the row labels: the longest label, at most 40 % of the width."""
    return min(width * 0.4, max((base.text_width(s) for s in labels), default=0) + 4)


def _num(v: float) -> str:
    return base.number(v, 0 if float(v).is_integer() else 1)


def hbars(rows: Sequence[dict], unit: str, *, width: float = base.FULL_W) -> str:
    """Horizontal bars, one per row `{"label", "value"}`, the value printed right of the bar; `unit` names the count.
    The bars take the width the labels and the numbers leave."""
    if not rows:
        return ""
    w = float(width)
    label_w = _label_width([str(r["label"]) for r in rows], w)
    x0 = label_w + 12
    bar_w = max(w - x0 - 8 - _NUM_W, 40.0)
    top = max(float(r["value"]) for r in rows)
    scale = base.Linear(0, top if top > 0 else 1, 0, bar_w)
    h = _TOP + len(rows) * _ROW_H + 4
    out = [base.text(x0, base.TEXT_PX, unit, "start", "mut"), base.line(x0, _TOP - 4, x0, h - 4, "ax")]
    for i, r in enumerate(rows):
        y = _TOP + i * _ROW_H
        v = float(r["value"])
        out.append(base.text(label_w, y + _BAR_H / 2 + base.TEXT_PX * 0.35, base.fit(str(r["label"]), label_w), "end"))
        bw = scale(v)
        if bw > 0:
            out.append(base.rect(x0, y, bw, _BAR_H, "muted", f"{r['label']}: {_num(v)} {unit}"))
        out.append(base.text(x0 + bw + 6, y + _BAR_H / 2 + base.TEXT_PX * 0.35, _num(v)))
    return base.figure(w, h, f"Count of {unit} per row", out)


def score_bars(
    rows: Sequence[dict],
    *,
    width: float = base.FULL_W,
    title: str = "Mutation score per row, 0 to 100 percent",
    none_text: str = "not mutated",
) -> str:
    """Bars from 0 to 100 %, one per row `{"label", "pct"}`, coloured by `score_class`; a row without a score is
    printed `none_text` on an empty track, with no bar. `title` is the accessible name of the figure."""
    if not rows:
        return ""
    w = float(width)
    label_w = _label_width([str(r["label"]) for r in rows], w)
    x0 = label_w + 12
    bar_w = max(w - x0 - 8 - _NUM_W, 40.0)
    sx = base.Linear(0, 100, x0, x0 + bar_w)
    y_axis = 4 + len(rows) * _ROW_H
    h = y_axis + 8 + 2 * base.TEXT_PX
    out = []
    for i, r in enumerate(rows):
        y = 4 + i * _ROW_H
        ty = y + _BAR_H / 2 + base.TEXT_PX * 0.35
        p = r["pct"]
        out.append(base.text(label_w, ty, base.fit(str(r["label"]), label_w), "end"))
        if p is None:
            out.append(base.rect(x0, y, bar_w, _BAR_H, "na", f"{r['label']}: {none_text}"))
            out.append(base.text(x0 + 8, ty, none_text, "start", "mut"))
            continue
        out.append(base.rect(x0, y, bar_w, _BAR_H, "band"))
        if p > 0:
            tip = f"{r['label']}: {base.number(p, 1)} %"
            out.append(base.rect(x0, y, sx(p) - x0, _BAR_H, base.score_class(p), tip))
        out.append(base.text(x0 + bar_w + 6, ty, f"{base.number(p, 1)} %"))
    out.append(base.axis_bottom(sx, [0, 25, 50, 75, 100], y_axis, x0, x0 + bar_w, grid_to=4))
    return base.figure(w, h, title, out)
