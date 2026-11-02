"""Marimekko chart: column width is the count of a column, segment height is its share of the column.

The column labels stand below the columns, never turned: a label is shortened to what its column leaves, and a crowd
of narrow columns stagger their labels on up to three rows (a thin leader joins a lower row to its column)."""
from __future__ import annotations

from collections.abc import Sequence

from . import base

__all__ = ["marimekko"]

_PLOT_H = 260.0
_X0 = 52.0  # left margin: the percent axis
_RIGHT = 12.0  # right margin
_ROWS = 3  # label rows below the columns
_GAP_COL = 2.0
_GAP_GROUP = 18.0
_LEGEND_ROW = 22.0


def _group_spans(cols: list[dict], xs: list[float], ws: list[float]) -> list[tuple[str, float, float]]:
    """(group, x start, x end) for consecutive columns of one group; columns without a group are skipped."""
    spans: list[tuple[str, float, float]] = []
    for c, x, w in zip(cols, xs, ws, strict=True):
        g = str(c.get("group") or "")
        if not g:
            continue
        if spans and spans[-1][0] == g and abs(spans[-1][2] + _GAP_COL - x) < 1e-6:
            spans[-1] = (g, spans[-1][1], x + w)
        else:
            spans.append((g, x, x + w))
    return spans


def marimekko(columns: Sequence[dict], segments: Sequence[tuple[str, str, str]], unit: str = "runs",
              title: str | None = None, *, width: float = base.FULL_W) -> str:
    """Columns `{"label", "group", "parts": {key: count}}`, segments `(key, label, class)` stacked from the bottom.

    Column width is proportional to the column total, segment height to its share of the column. Columns of one group
    are adjacent and the group name stands above them. Empty input, or all counts zero, returns "".
    """
    cols = [c for c in columns if sum(int(c["parts"].get(k, 0)) for k, _, _ in segments) > 0]
    totals = [sum(int(c["parts"].get(k, 0)) for k, _, _ in segments) for c in cols]
    grand = sum(totals)
    if grand <= 0:
        return ""
    groups = [str(c.get("group") or "") for c in cols]
    n_gaps = sum(1 for i in range(1, len(cols)) if groups[i] != groups[i - 1])
    avail = float(width) - _X0 - _RIGHT - _GAP_COL * (len(cols) - 1 - n_gaps) - _GAP_GROUP * n_gaps
    xs, ws, x = [], [], _X0
    for i, tot in enumerate(totals):
        if i:
            x += _GAP_GROUP if groups[i] != groups[i - 1] else _GAP_COL
        w = tot / grand * avail
        xs.append(x)
        ws.append(w)
        x += w
    plot_r = x
    has_groups = any(groups)
    top = 38.0 + (18.0 if has_groups else 0.0)
    y_base = top + _PLOT_H
    sy = base.Linear(0, 100, y_base, top)
    out = [base.axis_left(sy, [0, 25, 50, 75, 100], _X0 - 6, top, y_base, grid_to=plot_r),
           base.text(0, 12, "share of column, %", "start", "mut")]
    # group labels above, on two rows when neighbours would overlap
    if has_groups:
        last_end = [-1e9, -1e9]
        for g, gx0, gx1 in _group_spans(cols, xs, ws):
            row = 0 if gx0 >= last_end[0] + 6 else 1
            if row == 1 and gx0 < last_end[1] + 6:
                row = 0
            gw = base.text_width(g)
            at_edge = gx0 + gw > plot_r  # the label would run past the plot: end it at the group's right edge
            last_end[row] = gx1 if at_edge else gx0 + gw
            ly = top - 6 - row * 14.0
            out.append(base.line(gx0, top - 3, gx1, top - 3, "ax"))
            out.append(base.text(gx1 if at_edge else gx0, ly - 4, g, "end" if at_edge else "start", "b"))
    # segments
    for c, tot, cx, cw in zip(cols, totals, xs, ws, strict=True):
        acc = 0
        for key, seg_label, cls in segments:
            n = int(c["parts"].get(key, 0))
            if n <= 0:
                continue
            y1, y0 = sy(100 * (acc + n) / tot), sy(100 * acc / tot)
            tip = (f"{c['label']}: {seg_label} {base.number(n)} of {base.number(tot)} {unit} "
                   f"({base.number(100 * n / tot, 1)} % of the column; "
                   f"column = {base.number(100 * tot / grand, 1)} % of "
                   f"{base.number(grand)})")
            out.append(base.rect(cx, y1, cw, y0 - y1, cls, tip))
            if cw >= base.text_width(base.number(n)) + 6 and y0 - y1 >= base.TEXT_PX + 4:
                out.append(base.text(cx + cw / 2, (y0 + y1) / 2 + base.TEXT_PX * 0.35, base.number(n), "middle",
                                     base.ink(cls)))
            acc += n
    # column labels: horizontal with the total when every label fits its column, else shortened and staggered
    out.append(base.line(_X0, y_base, plot_r, y_base, "ax"))
    labels = [str(c["label"]) for c in cols]
    horizontal = all(base.text_width(s) <= w + _GAP_COL for s, w in zip(labels, ws, strict=True))
    bottom = y_base
    if horizontal:
        for s, tot, cx, cw in zip(labels, totals, xs, ws, strict=True):
            out.append(base.text(cx + cw / 2, y_base + 4 + base.TEXT_PX, s, "middle", "mut"))
            out.append(base.text(cx + cw / 2, y_base + 4 + 2 * base.TEXT_PX + 2, base.number(tot), "middle", "mut"))
        bottom = y_base + 4 + 2 * base.TEXT_PX + 6
    else:
        row_end = [-1e9] * _ROWS
        used = 0
        step = base.SMALL_PX + 3
        for s, cx, cw in zip(labels, xs, ws, strict=True):
            mid = cx + cw / 2
            shown = base.fit(s, 96.0, base.SMALL_PX, blank=True)
            half = base.text_width(shown, base.SMALL_PX) / 2
            row = next((r for r in range(_ROWS) if mid - half >= row_end[r] + 4 and mid - half >= 0
                        and mid + half <= float(width)), None)
            if not shown or row is None:
                continue
            row_end[row] = mid + half
            used = max(used, row + 1)
            ty = y_base + 6 + (row + 1) * step - 3
            if row:
                out.append(base.line(mid, y_base, mid, ty - base.SMALL_PX, "grid"))
            out.append(base.text(mid, ty, shown, "middle", "mut", size=base.SMALL_PX))
        bottom = y_base + 8 + max(used, 1) * step
    leg, _ = base.legend([(cls, seg_label) for _, seg_label, cls in segments], _X0, bottom + _LEGEND_ROW)
    out.append(leg)
    w_total = float(width)
    caption = title or f"Share of {unit} per column; column width is the number of {unit}"
    return base.figure(w_total, bottom + _LEGEND_ROW + 8, caption, out)
