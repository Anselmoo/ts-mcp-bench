"""Scatter of line coverage against mutation score per module, with a rug of the modules that were not mutated."""
from __future__ import annotations

import math
from collections.abc import Sequence

from . import base

__all__ = ["coverage_mutation"]

_X0 = 106.0  # left margin: y axis and the rug label
_PLOT_H = 340.0
_TOP = 12.0
_RUG_H = 30.0
_PAD = 14.0  # room inside the plot for the largest point at the upper and right edge
_R_MIN, _R_MAX = 3.0, 13.0
Box = tuple[float, float, float, float]  # x, y, width, height


def _overlap(a: Box, b: Box, pad: float = 1.0) -> bool:
    return not (a[0] + a[2] + pad <= b[0] or b[0] + b[2] + pad <= a[0] or a[1] + a[3] + pad <= b[1]
                or b[1] + b[3] + pad <= a[1])


def _hits_circle(box: Box, cx: float, cy: float, r: float) -> bool:
    nx = min(max(cx, box[0]), box[0] + box[2])
    ny = min(max(cy, box[1]), box[1] + box[3])
    return (nx - cx) ** 2 + (ny - cy) ** 2 < (r + 1) ** 2


def _place_labels(items: Sequence[tuple[str, float, float, float, float]], bounds: Box
                  ) -> list[tuple[str, float, float, str, float, float]]:
    """Labels of the points `(key, x, y, radius, text width)` without overlap: for each point, in the order given, the
    first of eight positions around it whose box hits no placed label, no point and no edge. Points that find no
    position get no label. Returns `(key, box x, box y, anchor, width, height)`."""
    h = base.SMALL_PX
    placed: list[tuple[str, float, float, str, float, float]] = []
    boxes: list[Box] = []
    bx0, by0, bw, bh = bounds
    for key, x, y, r, w in items:
        g = 3.0
        d = r * 0.71
        cands = [
            (x + r + g, y - h / 2, "start"), (x - r - g - w, y - h / 2, "end"),
            (x - w / 2, y - r - g - h, "middle"), (x - w / 2, y + r + g, "middle"),
            (x + d + g, y - d - g - h, "start"), (x + d + g, y + d + g, "start"),
            (x - d - g - w, y - d - g - h, "end"), (x - d - g - w, y + d + g, "end"),
        ]
        for cx, cy, anchor in cands:
            box = (cx, cy, w, h)
            if cx < bx0 or cy < by0 or cx + w > bx0 + bw or cy + h > by0 + bh:
                continue
            if any(_overlap(box, o) for o in boxes):
                continue
            if any(_hits_circle(box, px, py, pr) for _, px, py, pr, _ in items):
                continue
            boxes.append(box)
            placed.append((key, cx, cy, anchor, w, h))
            break
    return placed


def _floor_to(v: float, step: float) -> float:
    return math.floor(v / step) * step


def coverage_mutation(points: Sequence[dict], unmutated: Sequence[dict], *, width: float = base.FULL_W) -> str:
    """Points `{"module", "coverage", "score", "mutants"}` (percent; area ~ mutants, class from the score) and the rug
    `{"module", "coverage"}` of modules without a mutation result, drawn under the x axis as "not mutated". The
    figure is `width` px wide."""
    if not points and not unmutated:
        return ""
    covs = [float(p["coverage"]) for p in points] + [float(u["coverage"]) for u in unmutated]
    xlo = min(_floor_to(min(covs) - 3, 5), 95.0)
    ylo = min(max(_floor_to(min((float(p["score"]) for p in points), default=0.0) - 5, 10), 0.0), 90.0)
    fig_w = float(width)
    x1 = fig_w - 20.0
    yb = _TOP + _PLOT_H
    y_axis = yb + _RUG_H
    sx = base.Linear(xlo, 100, _X0, x1 - _PAD)
    sy = base.Linear(ylo, 100, yb, _TOP + _PAD)
    out = [base.axis_left(sy, base.nice_ticks(ylo, 100, 5), _X0, _TOP, yb, "mutation score, %", grid_to=x1),
           base.line(_X0, yb, x1, yb, "grid")]
    # rug: one tick per coverage value; the tick grows with the number of files and its title lists them
    by_cov: dict[float, list[str]] = {}
    for u in unmutated:
        by_cov.setdefault(round(float(u["coverage"]), 2), []).append(str(u["module"]))
    for cov in sorted(by_cov):
        mods = by_cov[cov]
        shown = ", ".join(mods[:12]) + (f" and {len(mods) - 12} more" if len(mods) > 12 else "")
        tip = (f"{shown}: line coverage {base.number(cov, 1)} %, not mutated "
               f"({base.plural(len(mods), 'file', shown=base.number(len(mods)))})")
        n = min(len(mods), 4)
        x = sx(cov)
        out.append(base.line(x, yb + 8, x, yb + 8 + 6 + 4 * (n - 1), "ax", tip, width=1.6))
    if unmutated:
        label = f"not mutated ({base.number(len(unmutated))})"
        out.append(base.text(_X0 - 8, yb + 8 + base.SMALL_PX, label, "end", "mut", size=base.SMALL_PX))
    # points, the largest first so the small ones stay visible
    pts = sorted(points, key=lambda p: (-int(p["mutants"]), str(p["module"])))
    top_m = max((int(p["mutants"]) for p in pts), default=1) or 1
    items = []
    for p in pts:
        r = _R_MIN + (_R_MAX - _R_MIN) * math.sqrt(int(p["mutants"]) / top_m)
        x, y = sx(float(p["coverage"])), sy(float(p["score"]))
        tip = (f"{p['module']}: line coverage {base.number(p['coverage'], 1)} %, mutation score "
               f"{base.number(p['score'], 1)} %, {base.number(p['mutants'])} mutants")
        out.append(base.circle(x, y, r, f"{base.score_class(float(p['score']))} tile", tip))
        items.append((str(p["module"]), x, y, r, base.text_width(base.module_name(str(p["module"])), base.SMALL_PX)))
    for key, bx, by, anchor, w, h in _place_labels(items, (_X0, _TOP, x1 - _X0, yb - _TOP)):
        tx = bx if anchor == "start" else bx + w if anchor == "end" else bx + w / 2
        out.append(base.text(tx, by + h - 2, base.module_name(key), anchor, "mut", size=base.SMALL_PX))
    out.append(base.axis_bottom(sx, base.nice_ticks(xlo, 100, 6), y_axis, _X0, x1, "line coverage, %"))
    ly = y_axis + 8 + 2 * base.TEXT_PX + 22
    leg, nxt = base.legend_rows(base.score_legend(), fig_w - _X0 - 8, _X0, ly)
    out.append(leg)
    out.append(base.text(_X0, nxt + 2, "dot colour: mutation score; dot area: mutants", "start", "mut"))
    return base.figure(fig_w, nxt + 10, "Line coverage and mutation score per module", out)
