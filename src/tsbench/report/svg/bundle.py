"""Hierarchical edge bundling: modules on a circle grouped by package, imports as bundled B-spline links.

The layout is the radial cluster of d3 (package at half the radius, module on the circle) and the links are the
straightened B-splines of d3's `curveBundle` (beta 0.85) through the path module > package > root > package > module.
The package names stand outside the circle at the middle of their arc. A module label is printed only where the
width leaves room for it and the labels are at least a line apart; otherwise the nodes carry their name in a title.
"""
from __future__ import annotations

import math
from collections.abc import Sequence

from . import base

__all__ = ["edge_bundling"]

_BETA = 0.85
_MAX_R = 250.0
_LABEL_GAP = 8.0
_MIN_R = 120.0  # the least radius at which module labels are printed
_LINE = base.SMALL_PX + 2.0  # the least arc length per module label
_NODE_R = 3.2


def _basis_path(pts: list[tuple[float, float]]) -> str:
    """The path data of d3's basis curve through `pts` (a port of d3-shape curve/basis.js)."""
    d: list[str] = []
    x0 = y0 = x1 = y1 = 0.0
    state = 0
    for x, y in pts:
        if state == 0:
            state = 1
            d.append(_c("M", x, y))
        elif state == 1:
            state = 2
        else:
            if state == 2:
                state = 3
                d.append(_c("L", (5 * x0 + x1) / 6, (5 * y0 + y1) / 6))
            d.append(_curve(x0, y0, x1, y1, x, y))
        x0, x1 = x1, x
        y0, y1 = y1, y
    if state == 3:
        d.append(_curve(x0, y0, x1, y1, x1, y1))
    if state >= 2:
        d.append(_c("L", x1, y1))
    return "".join(d)


def _c(cmd: str, x: float, y: float) -> str:
    return f"{cmd}{base.coord(x)},{base.coord(y)}"


def _curve(x0: float, y0: float, x1: float, y1: float, x: float, y: float) -> str:
    c = base.coord
    return ("C" + f"{c((2 * x0 + x1) / 3)},{c((2 * y0 + y1) / 3)},{c((x0 + 2 * x1) / 3)},{c((y0 + 2 * y1) / 3)},"
            f"{c((x0 + 4 * x1 + x) / 6)},{c((y0 + 4 * y1 + y) / 6)}")


def _bundle(pts: list[tuple[float, float]], beta: float = _BETA) -> str:
    """d3's `curveBundle(beta)`: straighten the points towards the chord, then draw the basis curve."""
    j = len(pts) - 1
    if j < 1:
        return ""
    (xa, ya), (xb, yb) = pts[0], pts[-1]
    dx, dy = xb - xa, yb - ya
    strung = [(beta * x + (1 - beta) * (xa + i / j * dx), beta * y + (1 - beta) * (ya + i / j * dy))
              for i, (x, y) in enumerate(pts)]
    return _basis_path(strung)


def edge_bundling(modules: Sequence[dict], edges: Sequence[tuple[str, str, int]], value_label: str = "line coverage",
                  none_label: str = "no value", *, width: float = base.FULL_W) -> str:
    """Modules `{"module", "package", "value"}` on a circle, grouped by package (in the order given), node class from
    `score_class(value)`; `edges` are `(src, dst, n)` import links, `n` statements wide. Edges that name an unknown
    module, or a module itself, are skipped. The figure is `width` px wide."""
    if not modules:
        return ""
    pkgs: list[str] = []
    for m in modules:
        if m["package"] not in pkgs:
            pkgs.append(m["package"])
    slots = len(modules) + len(pkgs)
    w = float(width)
    label_w = max(base.text_width(base.module_name(str(m["module"])), base.SMALL_PX) for m in modules)
    pkg_room = max(base.text_width(p) for p in pkgs) + 10
    r = min(_MAX_R, w / 2 - 6 - _LABEL_GAP - label_w - pkg_room)
    labelled = r >= _MIN_R and 2 * math.pi * r / slots >= _LINE
    if labelled:
        half = r + _LABEL_GAP + label_w + pkg_room
    else:
        r = max(min(_MAX_R, w / 2 - 6 - pkg_room - _LABEL_GAP), 60.0)
        half = r + _LABEL_GAP + pkg_room
    cx, cy = w / 2, half
    ang: dict[str, float] = {}
    pkg_ang: dict[str, float] = {}
    slot = 0
    for p in pkgs:
        members = [m for m in modules if m["package"] == p]
        slot += 1  # a gap before each package
        for m in members:
            ang[m["module"]] = 2 * math.pi * (slot - 0.5) / slots
            slot += 1
        pkg_ang[p] = (ang[members[0]["module"]] + ang[members[-1]["module"]]) / 2
    pkg_of = {m["module"]: m["package"] for m in modules}
    pos = {k: base.polar(cx, cy, r, a) for k, a in ang.items()}
    mid = {p: base.polar(cx, cy, r / 2, a) for p, a in pkg_ang.items()}
    out: list[str] = []
    links: list[str] = []
    for src, dst, n in edges:
        if src == dst or src not in pos or dst not in pos:
            continue
        ps, pd = pkg_of[src], pkg_of[dst]
        route = [pos[src], mid[ps], pos[dst]] if ps == pd else [pos[src], mid[ps], (cx, cy), mid[pd], pos[dst]]
        width = min(1.0 + 0.6 * (n - 1), 4.0)
        tip = f"{src} → {dst}: {base.plural(n, 'import statement', shown=base.number(n))}"
        links.append(base.path(_bundle(route), "flow ax", tip, width=width))
    out.append(base.group(links, "links"))
    nodes, labels = [], []
    for m in modules:
        k = m["module"]
        x, y = pos[k]
        v = m["value"]
        nodes.append(base.circle(x, y, _NODE_R, base.score_class(v),
                                 f"{k}: {value_label} {base.percent(v, none_label)} ({m['package']})"))
        if not labelled:
            continue
        a = ang[k]
        deg = math.degrees(a)
        flip = a >= math.pi
        c = base.coord
        tr = f"translate({c(cx)},{c(cy)}) rotate({c(deg - 90)}) translate({c(r + _LABEL_GAP)},0)"
        if flip:
            tr += " rotate(180)"
        labels.append(base.group(base.text(0, 0, base.module_name(str(k)), "end" if flip else "start",
                                           size=base.SMALL_PX, baseline="central"), transform=tr))
    out.append(base.group(nodes, "nodes"))
    out.append(base.group(labels, "labels"))
    out.append(base.group(_package_names(pkg_ang, cx, cy, r + _LABEL_GAP + (label_w if labelled else 0.0)), "packages"))
    leg, ly = base.legend_rows([*base.score_legend(), ("na", none_label)], w - 16, 8, 2 * half + 6 + base.TEXT_PX)
    out.append(leg)
    title = f"Imports between modules, {value_label} of each module"
    return base.figure(w, ly - base.TEXT_PX + 8, title, out)


def _package_names(pkg_ang: dict[str, float], cx: float, cy: float, radius: float) -> str:
    """The package names outside the circle, each at the middle of its arc, read away from the circle. In angle order,
    a name whose box meets a name already placed moves outward one line at a time."""
    out, boxes = [], []
    for p, a in sorted(pkg_ang.items(), key=lambda kv: kv[1]):
        side = math.sin(a)
        w = base.text_width(p)
        for step in range(12):
            x, y = base.polar(cx, cy, radius + 6 + step * (base.TEXT_PX + 2), a)
            if abs(side) < 0.3:  # near the top or the bottom: centred, above or below the point
                y, anchor, x0 = (y - 4 if math.cos(a) > 0 else y + base.TEXT_PX), "middle", x - w / 2
            else:
                y, anchor, x0 = y + base.TEXT_PX * 0.35, "start" if side > 0 else "end", x if side > 0 else x - w
            box = (x0, x0 + w, y - base.TEXT_PX, y + 3)
            if not any(box[0] < b[1] and b[0] < box[1] and box[2] < b[3] and b[2] < box[3] for b in boxes):
                break
        boxes.append(box)
        out.append(base.text(x, y, p, anchor, "b"))
    return "".join(out)
