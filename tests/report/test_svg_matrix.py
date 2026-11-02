"""Tests for src/tsbench/report/svg/matrix.py: the tool transition matrix."""
from __future__ import annotations

import xml.etree.ElementTree as ET

from svg_helpers import attr_float as _f
from svg_helpers import match as _m

from tsbench.report.svg import matrix

NS = "{http://www.w3.org/2000/svg}"


TOOLS = ["ts_a", "ts_b", "ts_unused", "StructuredOutput"]
COUNTS = {("ts_a", "ts_a"): 5, ("ts_a", "ts_b"): 2, ("ts_b", "StructuredOutput"): 7, ("ts_a", "StructuredOutput"): 1}


def _cells(root):
    out = {}
    for el in root.iter(f"{NS}rect"):
        t = el.find(f"{NS}title")
        if t is not None:
            m = _m(r"^(.*) → (.*): (\d+)$", t.text)
            out[(m.group(1), m.group(2))] = (el, int(m.group(3)))
    return out


def _texts(root):
    return [el.text for el in root.iter(f"{NS}text")]


def test_empty():
    assert matrix.transition_matrix([], COUNTS) == ""
    assert matrix.transition_matrix(TOOLS, {}) == ""


def test_one_cell_per_nonzero_count_and_positions_follow_tool_order():
    svg = matrix.transition_matrix(TOOLS, COUNTS)
    assert svg == matrix.transition_matrix(TOOLS, COUNTS)
    root = ET.fromstring(svg)
    cells = _cells(root)
    assert {k: v[1] for k, v in cells.items()} == COUNTS
    x = {k: _f(v[0], "x") for k, v in cells.items()}
    y = {k: _f(v[0], "y") for k, v in cells.items()}
    assert x[("ts_a", "ts_a")] < x[("ts_a", "ts_b")] < x[("ts_a", "StructuredOutput")]
    assert y[("ts_a", "ts_a")] < y[("ts_b", "StructuredOutput")]
    assert x[("ts_a", "StructuredOutput")] == x[("ts_b", "StructuredOutput")]  # one column shares x across rows
    assert y[("ts_a", "ts_a")] == y[("ts_a", "ts_b")]


def test_shade_grows_with_count_and_number_is_in_the_cell():
    root = ET.fromstring(matrix.transition_matrix(TOOLS, COUNTS))
    cells = _cells(root)
    op = {k: _f(v[0], "fill-opacity") for k, v in cells.items()}
    order = [("ts_b", "StructuredOutput"), ("ts_a", "ts_a"), ("ts_a", "ts_b"), ("ts_a", "StructuredOutput")]
    assert [op[k] for k in order] == sorted((op[k] for k in order), reverse=True)
    assert len({op[k] for k in order}) == 4
    texts = _texts(root)
    for n in ("5", "2", "7", "1"):
        assert n in texts
    assert all("c-C" in v[0].get("class") for v in cells.values())


def test_row_and_column_totals_and_unused_tools():
    root = ET.fromstring(matrix.transition_matrix(TOOLS, COUNTS))
    texts = _texts(root)
    assert "ts_unused" in texts  # the row exists even though it is empty
    # out totals: ts_a 8, ts_b 7, ts_unused 0, StructuredOutput 0; in totals: ts_a 5, ts_b 2, ts_unused 0, S.O. 8
    assert texts.count("8") >= 2
    assert "15" in texts  # the sum of all transitions
    muted = [el.text for el in root.iter(f"{NS}text") if el.get("class") == "mut"]
    assert "ts_unused" in muted and "ts_a" not in muted


def test_unknown_tool_names_are_appended_and_escaped():
    svg = matrix.transition_matrix(["ts_a"], {("ts_a", "x<y>"): 3})
    assert "x<y>" not in svg
    cells = _cells(ET.fromstring(svg))
    assert cells[("ts_a", "x<y>")][1] == 3


# ---------------------------------------------------------------- two widths


def test_matrix_is_drawn_at_the_width_it_is_given(fig_width, fits):
    fits(matrix.transition_matrix(TOOLS, COUNTS, width=fig_width), fig_width)


def test_column_heads_are_turned_by_45_degrees():
    """column heads at 45°, not 90°."""
    root = ET.fromstring(matrix.transition_matrix(TOOLS, COUNTS, width=960))
    heads = [t for t in root.iter(f"{NS}text") if t.text in TOOLS and t.get("transform")]
    assert heads and all("rotate(-45" in (t.get("transform") or "") for t in heads)


def _blend(fg: str, bg: str, op: float) -> tuple[float, ...]:
    f, b = (tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) for c in (fg, bg))
    return tuple(op * x + (1 - op) * y for x, y in zip(f, b, strict=True))


def _contrast(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    def lum(c: tuple[float, ...]) -> float:
        r, g, bl = (v / 255 / 12.92 if v / 255 <= 0.03928 else ((v / 255 + 0.055) / 1.055) ** 2.4 for v in c)
        return 0.2126 * r + 0.7152 * g + 0.0722 * bl
    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def test_the_count_in_every_cell_reads_at_4_5_to_1_in_both_themes():
    """The count is printed in the page ink on the C colour at the cell's opacity; the busiest cell must not make it
    unreadable (4.5 : 1 is the minimum for text on tiles).
    Colours: --s3, --plate and --plate-ink in svg.css and page.css."""
    themes = {"light": ("#b8336a", "#ffffff", "#1a1a1a"), "dark": ("#f07fae", "#161a20", "#e6e8ea")}
    root = ET.fromstring(matrix.transition_matrix(TOOLS, {**COUNTS, ("ts_b", "ts_b"): 500}))
    ops = [_f(el, "fill-opacity") for el, _ in _cells(root).values()]
    assert ops and max(ops) > 0.4
    for fg, plate, ink in themes.values():
        for op in ops:
            assert _contrast(_blend(fg, plate, op), tuple(int(ink[i:i + 2], 16) for i in (1, 3, 5))) >= 4.5, op
