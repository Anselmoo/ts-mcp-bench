"""Size of the errors: a beeswarm of error in tolerance units, one band per condition on a log axis."""
from __future__ import annotations

import math
import statistics
from collections.abc import Callable, Sequence

from . import base

__all__ = ["beeswarm"]

_R = 3.6  # marker radius
_GAP = 2 * _R + 0.8  # least distance between two marker centres
_STEP = 1.0  # vertical search step of the placement, in px


def _num(v: float) -> str:
    """A ratio with two significant digits (never an exponent); whole numbers from 100 on."""
    if v >= 100 or v <= 0:
        return base.fixed(v)
    out = base.fixed(v, max(1 - math.floor(math.log10(v)), 0))
    return out.rstrip("0").rstrip(".") if "." in out else out


def _offsets(xs: Sequence[float]) -> list[float]:
    """Vertical offsets for dots at the sorted x positions `xs`: each dot takes the free offset nearest to zero
    (0, +1, −1, +2, ... px) that keeps `_GAP` to the dots already placed."""
    placed: list[tuple[float, float]] = []
    out: list[float] = []
    for x in xs:
        near = [(px, py) for px, py in placed if abs(px - x) < _GAP]
        k = 0
        while True:
            cands = (0.0,) if k == 0 else (k * _STEP, -k * _STEP)
            hit = next((o for o in cands if all(math.hypot(px - x, py - o) >= _GAP for px, py in near)), None)
            if hit is not None:
                break
            k += 1
        placed.append((x, hit))
        out.append(hit)
    return out


def beeswarm(groups: Sequence[dict], cap: float = 300.0, floor: float = 1e-3, *, width: float = base.FULL_W,
             task_href: Callable[[str], str] | None = None) -> str:
    """Error / tolerance per answer on a log axis from `floor` to `cap`; values outside sit at the edge. The zone
    ratio ≤ 1 is shaded. A mark is filled when the scorer called the answer correct (`ok`) and open when not; the
    ratio only places it. A bar marks the median of each condition; with `task_href` each mark opens its task."""
    if not any(g["values"] for g in groups):
        return ""
    w, x0, top = float(width), 84.0, 34.0
    x1 = w - 16.0
    sx = base.Log(floor, cap, x0, x1)
    bands = []
    for g in groups:
        vals = sorted(((sx(v["ratio"]), str(v["task"]), float(v["ratio"]), bool(v.get("ok", False)))
                       for v in g["values"] if v.get("ratio") is not None), key=lambda t: (t[0], t[1]))
        offs = _offsets([x for x, _, _, _ in vals])
        reach = max((abs(o) for o in offs), default=0.0)
        bands.append((g["cond"], vals, offs, max(56.0, 2 * reach + 2 * _R + 20), int(g.get("n_runs") or len(vals))))
    axis_y = top + sum(b[3] for b in bands) + 4
    out = [base.rect(x0, top, sx(1.0) - x0, axis_y - top, "band"),
           base.axis_bottom(sx, sx.ticks(), axis_y, x0, x1, "error / tolerance, log scale", lambda v: f"{v:g}",
                            grid_to=top),
           base.line(sx(1.0), top, sx(1.0), axis_y, "zero"),
           base.text(x0 + 4, top - 8, "within tolerance", "start", "mut"),
           base.text(x1, top - 8, "filled correct · open wrong", "end", "mut")]
    y = top
    for cond, vals, offs, bh, total in bands:
        cy = y + bh / 2
        out.append(base.text(0, cy - 8, cond, "start", "b"))
        of = f" of {total}" if total > len(vals) else ""
        out.append(base.text(0, cy + 6, f"n {len(vals)}{of}", "start", "mut", size=base.SMALL_PX))
        if vals:
            med = statistics.median(r for _, _, r, _ in vals)
            out.append(base.text(0, cy + 19, f"median {_num(med)}", "start", "mut", size=base.SMALL_PX))
            out.append(base.rect(sx(med) - 1.25, y + 8, 2.5, bh - 16, f"c-{cond}", f"{cond} median {_num(med)}"))
        for (x, task, ratio, ok), off in zip(vals, offs, strict=True):
            edge = " · drawn at the edge" if not floor <= ratio <= cap else ""
            tip = f"{task} · {cond} · error/tolerance {_num(ratio)}{edge}"
            mark = base.marker(cond, x, cy + off, ok, _R, tip)
            out.append(mark if task_href is None else base.link(task_href(task), mark))
        y += bh
    return base.figure(w, axis_y + 12 + 2 * base.TEXT_PX + 8, "Error in tolerance units per answer", out)
