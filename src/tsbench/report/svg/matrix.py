"""Tool transition matrix: how often a call of the tool in a row is directly followed by the tool in a column.

Static SVG: one cell per pair, shaded by the count and carrying it, row totals at the right, column totals below,
the cells of the diagonal (a tool followed by itself) on a tinted ground. A tool that was never called keeps its row
and column, in the muted ink. The column heads stand at 45°; the cell size follows the width.
"""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

from . import base

__all__ = ["transition_matrix"]

CELL = 28.0  # the largest cell; a narrow figure takes smaller ones
MIN_CELL = 14.0
# The fill opacity of a cell. At MAX_OP the page ink on a C cell still has 4.5 : 1, in both themes.
MIN_OP, MAX_OP = 0.18, 0.54


def _cell(x: float, y: float, n: int, top: int, tip: str, size: float) -> str:
    """A cell in the condition C colour; the opacity (a number, not a colour) grows with the log of the count up to
    MAX_OP, so the count printed in the page ink keeps 4.5 : 1 on every cell."""
    op = round(MIN_OP + (MAX_OP - MIN_OP) * math.log1p(n) / math.log1p(top), 2)
    c = base.coord
    return (f'<rect class="c-C" x="{c(x + 1)}" y="{c(y + 1)}" width="{c(size - 2)}" height="{c(size - 2)}"'
            f' fill-opacity="{op}"><title>{base.escape(tip)}</title></rect>')


def transition_matrix(tools: Sequence[str], counts: Mapping[tuple[str, str], int], *,
                      width: float = base.FULL_W) -> str:
    """Matrix of `counts` `{(from, to): n}` over `tools` (rows = from, columns = to, in the given order).

    Names in `counts` that are not in `tools` follow the tools in sorted order. Empty without tools or counts."""
    if not tools or not counts:
        return ""
    names = list(tools) + sorted({t for pair in counts for t in pair} - set(tools))
    size = len(names)
    out_total = {a: sum(n for (x, _), n in counts.items() if x == a) for a in names}
    in_total = {b: sum(n for (_, y), n in counts.items() if y == b) for b in names}
    top_n = max(counts.values())
    sm = base.SMALL_PX
    longest = max(base.text_width(s, sm) for s in names)
    w = float(width)
    left = longest + 16
    right = max(54.0, longest * math.cos(math.radians(45)) + 8)  # the last head reaches this far past the matrix
    cell = max(MIN_CELL, min(CELL, (w - left - right) / size))
    head = longest * math.sin(math.radians(45)) + 30
    x0, y0 = left, head
    x1, y1 = x0 + size * cell, y0 + size * cell
    body = [base.text(x0 - 8, y0 - 26, "to", "end", "mut"), base.text(x0 - 8, y0 - 8, "from", "end", "mut"),
            base.text(x1 + 10, y0 - 8, "out", "start", "mut"), base.text(x0 - 8, y1 + 15, "in", "end", "mut")]
    for i in range(size):
        body.append(base.rect(x0 + i * cell, y0 + i * cell, cell, cell, "band"))
    for i in range(size + 1):
        body.append(base.line(x0 + i * cell, y0, x0 + i * cell, y1, "grid"))
        body.append(base.line(x0, y0 + i * cell, x1, y0 + i * cell, "grid"))
    for i, name in enumerate(names):
        used = out_total[name] + in_total[name] > 0
        cls = "" if used else "mut"
        body.append(base.text(x0 - 8, y0 + (i + 0.5) * cell + sm * 0.35, name, "end", cls, sm))
        body.append(base.text(x0 + (i + 0.5) * cell, y0 - 6, name, "start", cls, sm, angle=45.0))
        body.append(base.text(x1 + 10, y0 + (i + 0.5) * cell + sm * 0.35, base.number(out_total[name]), "start",
                              "" if out_total[name] else "mut", sm))
        body.append(base.text(x0 + (i + 0.5) * cell, y1 + 15, base.number(in_total[name]), "middle",
                              "" if in_total[name] else "mut", sm))
    for (a, b), n in sorted(counts.items(), key=lambda kv: (names.index(kv[0][0]), names.index(kv[0][1]))):
        if n <= 0:
            continue
        x, y = x0 + names.index(b) * cell, y0 + names.index(a) * cell
        body.append(_cell(x, y, n, top_n, f"{a} → {b}: {n}", cell))
        body.append(base.text(x + cell / 2, y + cell / 2 + sm * 0.35, base.number(n), "middle", "", sm))
    body.append(base.text(x1 + 10, y1 + 15, base.number(sum(counts.values())), "start", "b", sm))
    for i, line in enumerate(("cell: calls of the row tool", "directly followed by a call of the column tool")):
        body.append(base.text(x0, y1 + 36 + i * (base.TEXT_PX + 2), line, "start", "mut"))
    title = f"Tool transition matrix, {size} tools, {sum(counts.values())} transitions"
    return base.figure(w, y1 + 62, title, "".join(body))
