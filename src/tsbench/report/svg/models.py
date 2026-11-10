"""Several models in one figure: share correct per model and condition, the paired differences per model, a bubble
chart of tokens against share correct and a heat map of the classes.

`model_shares` and `model_paired` take the rows of `facts.models_overview`. A model is a band: its name at the left
(wrapped at the characters `-`, `_`, `.`, `/` and spaces, never cut), the lines of its conditions or pairs beside it,
and the numbers in one column right of the plot. A condition or a pair the model does not have leaves its line empty.
`model_bubbles` has one bubble per model and condition, `class_heat` one panel per condition.
"""
from __future__ import annotations

import math
import re
from collections.abc import Callable, Mapping, Sequence

from . import base

__all__ = ["class_heat", "model_bubbles", "model_paired", "model_shares"]

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


# ---------------------------------------------------------------- bubbles: tokens against share correct

_R_MAX = 24.0  # the bubble of the largest number of runs


def _box_free(box: tuple[float, float, float, float], taken: Sequence[tuple[float, float, float, float]]) -> bool:
    x0, y0, x1, y1 = box
    return all(x1 <= a or b <= x0 or y1 <= c or d <= y0 for a, c, b, d in taken)


def _name_at(name: str, cx: float, cy: float, r: float, taken: list[tuple[float, float, float, float]],
             limits: tuple[float, float, float, float]) -> str:
    """The name of a model beside its last bubble: above, below, right or left, the first place free of other names
    and bubbles and inside `limits`; above when none is."""
    w, h, gap = base.text_width(name) + 2, base.TEXT_PX, 3.0
    places = [(cx - w / 2, cy - r - gap - h), (cx - w / 2, cy + r + gap), (cx + r + gap, cy - h / 2),
              (cx - r - gap - w, cy - h / 2)]
    boxes = [(x, y, x + w, y + h) for x, y in places]
    ok = [b for b in boxes if _box_free(b, taken) and limits[0] <= b[0] and b[2] <= limits[2] and limits[1] <= b[1]
          and b[3] <= limits[3]]
    box = ok[0] if ok else boxes[0]
    taken.append(box)
    return base.text(box[0] + 1, box[1] + h * 0.8, name, "start", "b")


def model_bubbles(points: Sequence[Mapping], *, width: float = base.FULL_W, height: float = 420.0) -> str:
    """One bubble per model and condition: x = median output tokens per run (log axis), y = share correct, area = runs,
    colour = condition (the letter in the bubble says it again). A thin line joins the bubbles of one model in the order
    A, B, C; its name stands beside its last bubble. `points` `[{"model", "label", "cond", "tokens", "share", "k",
    "n"}]`; `label` is the short name of the model. A point without tokens or runs has no bubble."""
    pts = [p for p in points if p.get("tokens") and p.get("n")]
    if not pts:
        return ""
    w, top, x0, x1, axis_y = float(width), 34.0, 48.0, float(width) - 14.0, 34.0 + height
    lo = 10.0 ** math.floor(math.log10(min(float(p["tokens"]) for p in pts)))
    hi = 10.0 ** math.ceil(math.log10(max(float(p["tokens"]) for p in pts) * 1.01))
    sx, sy = base.Log(lo, hi, x0 + _R_MAX, x1 - _R_MAX), base.Linear(0.0, 1.0, axis_y - _R_MAX, top + _R_MAX)
    peak = max(int(p["n"]) for p in pts)
    radius = {id(p): _R_MAX * math.sqrt(int(p["n"]) / peak) for p in pts}
    out = [base.legend([(c, c) for c in base.CONDS if any(p["cond"] == c for p in pts)], x0, 14)[0],
           base.text(x1, 14, f"area = runs, largest {peak}", "end", "mut"),
           base.axis_bottom(sx, sx.ticks(), axis_y, x0, x1, "median output tokens per run, log scale",
                            lambda v: base.number(v, 0), grid_to=top),
           base.axis_left(sy, [0, 0.25, 0.5, 0.75, 1], x0, top, axis_y, "share correct", lambda v: base.number(100 * v),
                          grid_to=x1)]
    models = list(dict.fromkeys(str(p["model"]) for p in pts))
    own = {m: sorted((p for p in pts if str(p["model"]) == m), key=lambda p: base.CONDS.index(p["cond"]))
           for m in models}
    taken = [(sx(float(p["tokens"])) - radius[id(p)], sy(float(p["share"])) - radius[id(p)],
              sx(float(p["tokens"])) + radius[id(p)], sy(float(p["share"])) + radius[id(p)]) for p in pts]
    for m in models:
        line = own[m]
        out += [base.line(sx(float(a["tokens"])), sy(float(a["share"])), sx(float(b["tokens"])), sy(float(b["share"])))
                for a, b in zip(line, line[1:], strict=False)]
    for p in sorted(pts, key=lambda q: -int(q["n"])):
        cx, cy, r, c = sx(float(p["tokens"])), sy(float(p["share"])), radius[id(p)], p["cond"]
        tip = (f"{p['model']}, {c}: median {base.number(float(p['tokens']), 0)} output tokens, "
               f"{base.pct(float(p['share']))} correct, {p['k']}/{p['n']} runs")
        out.append(base.circle(cx, cy, r, f"bubble c-{c} k-{c}", tip))
        out.append(base.text(cx, cy + base.TEXT_PX * 0.35, c, "middle", "b"))
    for m in models:
        last = own[m][-1]
        cx, cy, r = sx(float(last["tokens"])), sy(float(last["share"])), radius[id(last)]
        out.append(_name_at(str(last.get("label") or m), cx, cy, r, taken, (x0, top, x1, axis_y)))
    return base.figure(w, axis_y + 12 + 2 * base.TEXT_PX + 8, "Median output tokens against share correct, one bubble "
                       "per model and condition", out)


# ---------------------------------------------------------------- heat map: model by class, per condition

_CELL_H = 26.0
_HEAD_H = 26.0  # the class names above a panel
_COND_H = 22.0  # the condition above a panel


def class_heat(rows: Sequence[Mapping], color: Callable[[float], tuple[str, str]], *,
               width: float = base.FULL_W) -> str:
    """Tasks solved per model and class, one panel per condition: a cell is shaded by k/n and prints it. `rows`
    `[{"model", "conds": [...], "classes": [{"class", "k": {cond: k}, "n_by": {cond: n}, "n": n}]}]`, a class in the
    order of its first appearance; `color(p)` gives (fill, ink) of a share. A cell with no evaluable run says `no run`
    and is not drawn as 0."""
    classes = list(dict.fromkeys(str(x["class"]) for r in rows for x in r["classes"]))
    conds = [c for c in base.CONDS if any(c in r["conds"] for r in rows)]
    if not classes or not conds:
        return ""
    w = float(width)
    names = [str(r["model"]) for r in rows]
    col, wrapped = _name_lines(names, w)
    x0 = col + _GAP
    cell_w = (w - x0) / len(classes)
    heights = [max(_CELL_H, len(n) * _NAME_PITCH + 6) for n in wrapped]
    by = [{str(x["class"]): x for x in r["classes"]} for r in rows]
    c = base.coord
    out: list[str] = []
    y = 0.0
    for cond in conds:
        out.append(base.text(0, y + base.TEXT_PX, f"Condition {cond}", "start", "b"))
        y += _COND_H
        for j, cls in enumerate(classes):
            label = base.fit(cls, cell_w - 4, base.SMALL_PX)
            out.append(base.text(x0 + (j + 0.5) * cell_w, y + base.SMALL_PX, label, "middle", "mut", base.SMALL_PX))
        y += _HEAD_H - 6
        for i, name in enumerate(names):
            h = heights[i]
            top_y = y + (h - len(wrapped[i]) * _NAME_PITCH) / 2
            out += [base.text(0, top_y + base.TEXT_PX * 0.9 + n * _NAME_PITCH, s) for n, s in enumerate(wrapped[i])]
            for j, cls in enumerate(classes):
                x = by[i].get(cls)
                n = int((x.get("n_by") or {}).get(cond, x["n"])) if x and cond in rows[i]["conds"] else 0
                tx, ty = x0 + (j + 0.5) * cell_w, y + h / 2 + base.TEXT_PX * 0.35
                if not n:
                    out.append(base.rect(x0 + j * cell_w + 1, y + 1, cell_w - 2, h - 2, "band",
                                         f"{name}, {cond}, {cls}: no run"))
                    out.append(base.text(tx, ty, "no run", "middle", "mut", base.SMALL_PX))
                    continue
                k = int(x["k"].get(cond, 0))
                fill, ink = color(k / n)
                tip = f"{name}, {cond}, {cls}: {k} of {n} tasks ({base.pct(k / n)})"
                out.append(f'<rect x="{c(x0 + j * cell_w + 1)}" y="{c(y + 1)}" width="{c(cell_w - 2)}" '
                           f'height="{c(h - 2)}" style="fill:{fill}"><title>{base.escape(tip)}</title></rect>')
                out.append(f'<text x="{c(tx)}" y="{c(ty)}" text-anchor="middle" style="fill:{ink}">{k}/{n}</text>')
            y += h
        y += 14
    return base.figure(w, y, "Tasks solved per model and class, one panel per condition", out)
