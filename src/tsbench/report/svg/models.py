"""Several models in one figure: share correct per model and condition, and the paired differences per model.

Both take the rows of `facts.models_overview`. A model is a band: its name at the left (wrapped at the characters
`-`, `_`, `.`, `/` and spaces, never cut), the lines of its conditions or pairs beside it, and the numbers in one
column right of the plot. A condition or a pair the model does not have leaves its line empty.
"""
from __future__ import annotations

import re
from collections.abc import Callable, Sequence

from . import base

__all__ = ["model_paired", "model_shares"]

_MINUS = "−"
_LINE = 22.0  # one condition or pair line
_PAD = 6.0  # above and below the lines of a band
_NAME_PITCH = 15.0  # between two lines of a wrapped name
_TOP = 30.0  # the legend row sits above
_BAR_H = 8.0
_GAP = 16.0  # between the columns
_EDGE = 4.0  # between the value column and the right edge
_NAME_CAP = 240.0  # the widest name column of a full figure
_NAME_SHARE = 0.3  # of the width
_NAME_CH = base.TEXT_PX * 0.6  # a bold character
_PAIRS = ("C − A", "C − B", "B − A")


def _wrap(name: str, per: int) -> list[str]:
    """`name` in lines of at most `per` characters, broken after a separator; a part longer than a line is split."""
    lines: list[str] = []
    cur = ""
    for part in re.split(r"(?<=[-_./ ])", name):
        while len(part) > per:  # a single part wider than the column: split it where the line is full
            room = per - len(cur)
            if room <= 0:
                lines.append(cur.rstrip())
                cur, room = "", per
            cur, part = cur + part[:room], part[room:]
        if len(cur) + len(part.rstrip()) > per and cur:
            lines.append(cur.rstrip())
            cur = ""
        cur += part
    if cur.strip() or not lines:
        lines.append(cur.rstrip())
    return lines


def _name_lines(names: Sequence[str], width: float) -> tuple[float, list[list[str]]]:
    """The width of the name column and the wrapped lines of every name: as wide as the longest name needs, at most
    30 % of the figure (240 px)."""
    cap = min(width * _NAME_SHARE, _NAME_CAP)
    col = min(cap, max((len(n) for n in names), default=0) * _NAME_CH + 2)
    per = max(int(col / _NAME_CH), 4)
    return col, [_wrap(n, per) for n in names]


def _bands(wrapped: Sequence[Sequence[str]], slots: int) -> list[float]:
    """The height of every band: the lines of its conditions or pairs, or its name when that is taller."""
    return [max(slots * _LINE, len(w) * _NAME_PITCH) + 2 * _PAD for w in wrapped]


def _frame(w: float, names: Sequence[str], slots: int, plot_left: Callable[[float], float], value_w: float,
           ticks: Sequence[float], lo: float, hi: float, label: str, fmt_tick: Callable[[float], str],
           title: str, lines: Callable[[int, float, base.Linear], str], zero: bool) -> str:
    """The shared figure: legend, name column, bands, axis. `lines(i, y, scale)` draws the lines of model `i` whose
    band starts at `y`, and `plot_left(name_col)` gives the left end of the axis."""
    col, wrapped = _name_lines(names, w)
    heights = _bands(wrapped, slots)
    x0 = plot_left(col)
    x1 = w - _EDGE - value_w - _GAP
    scale = base.Linear(lo, hi, x0, x1)
    axis_y = _TOP + sum(heights)
    out = [base.legend([(c, c) for c in base.CONDS], 0, 14)[0],
           base.axis_bottom(scale, ticks, axis_y, x0, x1, label, fmt_tick, grid_to=_TOP)]
    if zero:
        out.append(base.line(scale(0), _TOP, scale(0), axis_y, "zero"))
    y = _TOP
    for i, (parts, h) in enumerate(zip(wrapped, heights, strict=True)):
        if i:
            out.append(base.line(0, y, w, y, "grid"))
        out += [base.text(0, y + _PAD + base.TEXT_PX * 0.8 + j * _NAME_PITCH, s, "start", "b")
                for j, s in enumerate(parts)]
        out.append(lines(i, y + _PAD, scale))
        y += h
    return base.figure(w, axis_y + 12 + 2 * base.TEXT_PX + 8, title, out)


def _row_mark(cond: str, share: float, lo: float | None, hi: float | None, scale: base.Linear, cy: float,
              tip: str) -> str:
    """The interval bar (lo to hi on the scale) and the marker of a condition at `share`."""
    out = []
    if lo is not None and hi is not None:
        out.append(base.rect(scale(lo), cy - _BAR_H / 2, scale(hi) - scale(lo), _BAR_H, f"ribbon c-{cond}", tip))
    out.append(base.marker(cond, scale(share), cy, True, 5.0, tip))
    return "".join(out)


def model_shares(rows: Sequence[dict], *, width: float = base.FULL_W) -> str:
    """Share correct per model and condition on a 0 to 100 % axis: marker, 95 % interval bar, then "82 % · 41/50"."""
    if not rows:
        return ""
    w = float(width)
    names = [str(r["model"]) for r in rows]
    cells = [{c: v for c, v in (r.get("cells") or {}).items() if c in base.CONDS and v.get("share") is not None}
             for r in rows]
    values = [[f"{base.pct(v['share'])} · {v['k']}/{v['n']}" for v in c.values()] for c in cells]
    value_w = max((base.text_width(s) for vs in values for s in vs), default=base.text_width("100 % · 100/100"))
    xv = w - _EDGE

    def lines(i: int, y: float, scale: base.Linear) -> str:
        out = []
        for j, cond in enumerate(base.CONDS):
            v = cells[i].get(cond)
            if v is None:
                continue
            cy = y + j * _LINE + _LINE / 2
            lo, hi = v.get("lo"), v.get("hi")
            ci = "" if lo is None or hi is None else f", 95 % CI {_pct_range(lo, hi)} %"
            kn = f"{v['k']}/{v['n']}"
            tip = f"{names[i]}, {cond}: {kn} correct, {base.pct(v['share'])}{ci}"
            out.append(_row_mark(cond, v["share"], lo, hi, scale, cy, tip))
            out.append(base.text(xv, cy + base.TEXT_PX * 0.35, f"{base.pct(v['share'])} · {kn}", "end"))
        return "".join(out)

    return _frame(w, names, len(base.CONDS), lambda col: col + _GAP, value_w, [0, 0.25, 0.5, 0.75, 1], 0.0, 1.0,
                  "share correct", lambda v: base.number(100 * v), "Share correct per model and condition with "
                  "95 % interval", lines, False)


def _pct_range(lo: float, hi: float) -> str:
    return f"{base.number(100 * lo)}–{base.number(100 * hi)}"


def _pair_order(paired: dict) -> list[str]:
    return [p for p in _PAIRS if p in paired] + [p for p in paired if p not in _PAIRS]


def model_paired(rows: Sequence[dict], *, width: float = base.FULL_W) -> str:
    """The paired differences C − A, C − B and B − A per model in percentage points on a −100 to +100 axis with a zero
    line: marker, 95 % interval bar, then "+62 pp"."""
    if not rows:
        return ""
    w = float(width)
    names = [str(r["model"]) for r in rows]
    paired = [{p: v for p, v in (r.get("paired") or {}).items() if v.get("diff") is not None} for r in rows]
    slots = max(len(_PAIRS), max((len(p) for p in paired), default=0))
    value_w = max((base.text_width(f"{base.signed_pp(v['diff'])} pp") for p in paired for v in p.values()),
                  default=base.text_width("+100 pp"))
    pair_w = max((base.text_width(k) for p in paired for k in p), default=base.text_width("C − A"))
    xv = w - _EDGE

    def lines(i: int, y: float, scale: base.Linear) -> str:
        out = []
        for j, pair in enumerate(_pair_order(paired[i])):
            v = paired[i][pair]
            cy = y + j * _LINE + _LINE / 2
            first = pair.split(_MINUS)[0].strip()
            cond = first if first in base.CONDS else "A"
            diff = f"{base.signed_pp(v['diff'])} pp"
            lo, hi = v.get("lo"), v.get("hi")
            ci = "" if lo is None or hi is None else f", 95 % CI {base.signed_pp(lo)} to {base.signed_pp(hi)} pp"
            tip = f"{names[i]}, {pair}: {diff}{ci}"
            out.append(base.text(scale.r0 - 2 * _GAP - pair_w, cy + base.TEXT_PX * 0.35, pair, "start", "mut"))
            out.append(_row_mark(cond, v["diff"], lo, hi, scale, cy, tip))
            out.append(base.text(xv, cy + base.TEXT_PX * 0.35, diff, "end"))
        return "".join(out)

    return _frame(w, names, slots, lambda col: col + _GAP + pair_w + 2 * _GAP, value_w,
                  [-1, -0.5, 0, 0.5, 1], -1.0, 1.0, "percentage points",
                  lambda v: "0" if v == 0 else base.signed_pp(v), "Paired differences in share correct per model",
                  lines, True)
