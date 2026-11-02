"""Dashboard rows: share correct with its 95 % interval, and the paired differences.

Both are drawn as rows: a label, a point with an interval bar on a fixed axis, and the exact numbers in columns at the
right. The columns sit at the right edge of the given width and the axis takes the rest. A paired row of a narrow
figure carries its discordant counts on a second line.
"""
from __future__ import annotations

from collections.abc import Sequence

from . import base

__all__ = ["paired_diffs", "share_intervals"]

_ROW = 32.0
_TOP = 30.0
_BAR_H = 8.0
_MINUS = "−"
_GAP = 12.0  # between two columns
_EDGE = 4.0  # between the last column and the right edge
_NARROW = 600.0  # below this width the discordant counts of a paired row move to a line of their own


def _columns(w: float, widths: Sequence[float]) -> tuple[list[float], float]:
    """The right edges of the number columns of the given widths, packed against the right edge of a figure of width
    `w`, and the x where the first of them starts."""
    rights, x = [], w - _EDGE
    for cw in reversed(widths):
        rights.append(x)
        x -= cw + _GAP
    return rights[::-1], x + _GAP


def _headers(cols: Sequence[tuple[float, str]]) -> str:
    return "".join(base.text(x, _TOP - 12, s, "end", "mut") for x, s in cols)


def share_intervals(rows: Sequence[dict], *, width: float = base.FULL_W) -> str:
    """Share correct per condition on a 0 to 100 % axis: point, 95 % interval bar, then share, interval and k/n."""
    if not rows:
        return ""
    w = float(width)
    (cx_share, cx_ci, cx_kn), left = _columns(
        w, [base.text_width("100 %"), base.text_width("95 % CI"), base.text_width("100/100")])
    x0, x1 = 34.0, left - 2 * _GAP
    sx = base.Linear(0, 1, x0, x1)
    axis_y = _TOP + len(rows) * _ROW + 4
    out = [_headers([(cx_share, "share"), (cx_ci, "95 % CI"), (cx_kn, "k/n")]),
           base.axis_bottom(sx, [0, 0.25, 0.5, 0.75, 1], axis_y, x0, x1,
                            fmt_tick=lambda v: "100\u00a0%" if v == 1 else base.number(100 * v), grid_to=_TOP)]
    for i, r in enumerate(rows):
        cond, cy = r["cond"], _TOP + i * _ROW + _ROW / 2
        lo, hi = base.round_half_up(100 * r["lo"]), base.round_half_up(100 * r["hi"])
        share, ci, kn = base.pct(r["share"]), f"{base.number(lo)}–{base.number(hi)}", f"{r['k']}/{r['n']}"
        tip = f"{cond}: {kn} correct, {share}, 95 % CI {ci} %"
        ty = cy + base.TEXT_PX * 0.35
        out += [base.text(0, ty, cond, "start", "b"),
                base.rect(sx(r["lo"]), cy - _BAR_H / 2, sx(r["hi"]) - sx(r["lo"]), _BAR_H, f"ribbon c-{cond}", tip),
                base.marker(cond, sx(r["share"]), cy, True, 5.0, tip),
                base.text(cx_share, ty, share, "end", "b"), base.text(cx_ci, ty, ci, "end", "mut"),
                base.text(cx_kn, ty, kn, "end", "mut")]
    return base.figure(w, axis_y + 12 + base.TEXT_PX + 8, "Share correct per condition with 95 % interval", out)


def _names(pair: str) -> tuple[str, str]:
    for sep in (_MINUS, "-"):
        a, _, b = pair.partition(sep)
        if b:
            return a.strip(), b.strip()
    return "first", "second"


def paired_diffs(rows: Sequence[dict], *, width: float = base.FULL_W) -> str:
    """Paired differences in percentage points on a −100 to +100 axis with a zero line; discordant counts at right
    (below the row in a narrow figure)."""
    if not rows:
        return ""
    w = float(width)
    narrow = w < _NARROW
    widths = [base.text_width("difference"), base.text_width("−100 to +100")]
    if not narrow:
        widths.append(base.text_width("discordant tasks"))
    rights, left = _columns(w, widths)
    cx_diff, cx_ci = rights[0], rights[1]
    cx_only = None if narrow else rights[2]
    x0, x1 = 48.0, left - 2 * _GAP
    row = _ROW + (base.TEXT_PX + 2 if narrow else 0)
    sx = base.Linear(-1, 1, x0, x1)
    axis_y = _TOP + len(rows) * row + 4
    heads = [(cx_diff, "difference"), (cx_ci, "95 % CI")] + ([] if cx_only is None else [(cx_only, "discordant tasks")])
    out = [_headers(heads),
           base.axis_bottom(sx, [-1, -0.5, 0, 0.5, 1], axis_y, x0, x1, "percentage points",
                            fmt_tick=lambda v: "0" if v == 0 else base.signed_pp(v), grid_to=_TOP),
           base.line(sx(0), _TOP, sx(0), axis_y, "zero")]
    for i, r in enumerate(rows):
        a, b = _names(r["pair"])
        cond = a if a in base.CONDS else "A"
        cy = _TOP + i * row + _ROW / 2
        diff, ci = f"{base.signed_pp(r['diff'])} pp", f"{base.signed_pp(r['lo'])} to {base.signed_pp(r['hi'])}"
        only = f"only {a} {r['only_first']} · only {b} {r['only_second']}"
        tip = f"{r['pair']}: {diff}, 95 % CI {ci} pp; {only}"
        ty = cy + base.TEXT_PX * 0.35
        out += [base.text(0, ty, r["pair"], "start", "b"),
                base.rect(sx(r["lo"]), cy - _BAR_H / 2, sx(r["hi"]) - sx(r["lo"]), _BAR_H, f"ribbon c-{cond}", tip),
                base.marker(cond, sx(r["diff"]), cy, True, 5.0, tip),
                base.text(cx_diff, ty, diff, "end", "b"), base.text(cx_ci, ty, ci, "end", "mut")]
        out.append(base.text(cx_only, ty, only, "end", "mut") if cx_only is not None
                   else base.text(0, cy + 6 + base.TEXT_PX, only, "start", "mut"))
    return base.figure(w, axis_y + 12 + 2 * base.TEXT_PX + 8, "Paired differences in share correct", out)
