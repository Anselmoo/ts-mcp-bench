"""Treemap of line coverage: files grouped by package, tile area = statements, tile colour = line coverage step."""
from __future__ import annotations

from collections.abc import Callable, Sequence

from . import base

__all__ = ["equalise", "package_inner_area", "treemap"]

_HEAD = 16.0  # package header strip
_PAD = 3.0
_ITER = 40  # the most passes of `equalise`


def squarify(values: list[float], x: float, y: float, w: float, h: float) -> list[tuple[float, float, float, float]]:
    """Squarified treemap (Bruls, Huizing and van Wijk 2000): rectangles (x, y, w, h) in the order of `values`, each
    with an area proportional to its value, filling the box. `values` should be sorted from large to small."""
    total = sum(values)
    if total <= 0 or w <= 0 or h <= 0:
        return [(x, y, 0.0, 0.0) for _ in values]
    areas = [v / total * w * h for v in values]
    out: list[tuple[float, float, float, float]] = []

    def worst(row: list[float], side: float) -> float:
        s = sum(row)
        return max(max(side * side * a / (s * s), (s * s) / (side * side * a)) for a in row)

    i = 0
    while i < len(areas):
        side = min(w, h)
        row = [areas[i]]
        j = i + 1
        while j < len(areas) and worst(row + [areas[j]], side) <= worst(row, side):
            row.append(areas[j])
            j += 1
        s = sum(row)
        if w >= h:  # a column at the left
            cw = s / h
            yy = y
            for a in row:
                out.append((x, yy, cw, a / cw))
                yy += a / cw
            x, w = x + cw, w - cw
        else:  # a row at the top
            rh = s / w
            xx = x
            for a in row:
                out.append((xx, y, a / rh, rh))
                xx += a / rh
            y, h = y + rh, h - rh
        i = j
    return out


_Cell = tuple[float, float, float, float]


def equalise(values: Sequence[float], box: _Cell, effective_area: Callable[[int, _Cell], float]) -> list[_Cell]:
    """Squarified cells for `values` whose effective area (what is left for the tiles inside, after headers and
    padding) is proportional to the value. `effective_area(i, cell)` is that area for the i-th value in `cell`.
    `values` should be sorted from large to small."""
    weights = [float(v) for v in values]
    total = sum(values)
    for _ in range(_ITER):
        cells = squarify(weights, *box)
        areas = [effective_area(i, c) for i, c in enumerate(cells)]
        if sum(areas) <= 0 or total <= 0:
            return cells
        density = sum(areas) / total
        ratios = [a / (v * density) if v > 0 else 1.0 for a, v in zip(areas, values, strict=True)]
        if all(abs(r - 1) < 1e-4 for r in ratios):
            return cells
        weights = [w / r if r > 0 else w for w, r in zip(weights, ratios, strict=True)]
    return squarify(weights, *box)


def package_inner_area(_i: int, cell: _Cell) -> float:
    """The area of a package cell inside its header and padding, where its tiles lie."""
    return max((cell[2] - 2 * _PAD) * (cell[3] - _HEAD - _PAD), 1.0)


def _tile(x: float, y: float, w: float, h: float, name: str, pct: float | None, tip: str) -> str:
    cls = base.score_class(pct)
    out = [base.rect(x, y, w, h, f"tile {cls}", tip)]
    ink = base.ink(cls)
    fits = w >= base.text_width(name, base.SMALL_PX) + 8  # the name, whole, inside the tile; else no label
    if fits and h >= base.SMALL_PX + 6:
        out.append(base.text(x + 4, y + base.SMALL_PX + 2, name, "start", ink, size=base.SMALL_PX))
        label = base.percent(pct)
        if h >= 2 * base.SMALL_PX + 8 and w >= base.text_width(label, base.SMALL_PX) + 8:
            out.append(base.text(x + 4, y + 2 * base.SMALL_PX + 4, label, "start", ink, size=base.SMALL_PX))
    return "".join(out)


def _legend(y: float, summary: str, width: float) -> tuple[str, float]:
    """The score steps and the summary line from `y`; returns the SVG and the y below it."""
    leg, nxt = base.legend_rows(base.score_legend(), width, 0, y)
    return leg + base.text(0, nxt, summary, "start", "mut"), nxt + 8


def treemap(files: Sequence[dict], *, width: float = base.FULL_W) -> str:
    """Tiles per file `{"module", "package", "statements", "covered", "pct", "functions"}`, framed by package; files
    without statements are not drawn. A name is printed in a tile only when the whole name fits it; the ink is the
    one of the tile's step in both themes. Empty input returns ""."""
    rows = [f for f in files if f["statements"] > 0]
    if not rows:
        return ""
    pkgs: dict[str, list[dict]] = {}
    for f in rows:
        pkgs.setdefault(str(f["package"]), []).append(f)
    order = sorted(pkgs, key=lambda p: (-sum(f["statements"] for f in pkgs[p]), p))
    sizes = [float(sum(f["statements"] for f in pkgs[p])) for p in order]
    w_total = float(width)
    h_total = 500.0 if w_total >= 900 else 380.0
    cells = equalise(sizes, (0.0, 0.0, w_total, h_total), package_inner_area)
    out = []
    for p, (px, py, pw, ph) in zip(order, cells, strict=True):
        members = sorted(pkgs[p], key=lambda f: (-f["statements"], f["module"]))
        stm = sum(f["statements"] for f in members)
        cov = sum(f["covered"] for f in members)
        body = [base.rect(px, py, pw, ph, "frame",
                          f"{p}: {len(members)} files, {base.number(stm)} statements, "
                          f"{base.percent(100 * cov / stm)} covered")]
        if pw >= base.text_width(f"{p} · {base.number(stm)}", base.SMALL_PX) + 8 and ph > _HEAD:
            body.append(base.text(px + 4, py + base.SMALL_PX + 1, f"{p} · {base.number(stm)}", "start", "b",
                                  size=base.SMALL_PX))
        ix, iy, iw, ih = px + _PAD, py + _HEAD, pw - 2 * _PAD, ph - _HEAD - _PAD
        inner = squarify([float(f["statements"]) for f in members], ix, iy, iw, ih)
        prefix = f"tsbench.{p}."
        for f, (tx, ty, tw, th) in zip(members, inner, strict=True):
            name = base.module_name(str(f["module"]).removeprefix(prefix))
            tip = (f"{f['module']}: {base.number(f['statements'])} statements, {base.number(f['covered'])} covered, "
                   f"{base.percent(f['pct'])}")
            body.append(_tile(tx, ty, tw, th, name, f["pct"], tip))
        out.append(base.group(body))
    stm_all = sum(f["statements"] for f in rows)
    cov_all = sum(f["covered"] for f in rows)
    leg, bottom = _legend(h_total + 8 + base.TEXT_PX,
                          f"{len(rows)} files · {base.number(stm_all)} statements · "
                          f"{base.percent(100 * cov_all / stm_all)}",
                          w_total)
    out.append(leg)
    return base.figure(w_total, bottom, "Line coverage by package and file, area = statements", out)
