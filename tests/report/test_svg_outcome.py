"""Tests for src/tsbench/report/svg/outcome.py: diverging outcome bars and the UpSet plot."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET

import pytest
from svg_helpers import attr_or_zero as _num
from svg_helpers import classes as _classes
from svg_helpers import root as _root
from svg_helpers import tip as _tip

from tsbench.report.svg import outcome as O

NS = "{http://www.w3.org/2000/svg}"
CATS = [("correct", "correct"), ("gross", "gross error"), ("several", "several parameters wrong"),
        ("dq", "Dq wrong"), ("bc", "B or C wrong"), ("limit", "limit missed / false refusal")]
ROWS = [
    {"cond": "A", "counts": {"correct": 10, "gross": 17, "several": 13, "dq": 5, "bc": 3, "limit": 2}},
    {"cond": "B", "counts": {"correct": 9, "gross": 20, "several": 11, "dq": 4, "bc": 3, "limit": 3}},
    {"cond": "C", "counts": {"correct": 41, "gross": 3, "several": 2, "dq": 0, "bc": 3, "limit": 1}},
]
IDS = {"ABC": 3, "AB": 0, "AC": 5, "BC": 5, "A": 2, "B": 1, "C": 28, "": 6}
SETS = [{"key": k, "tasks": [f"t{k or 'none'}{i:02d}" for i in range(n)]} for k, n in IDS.items()]


def _titles(root: ET.Element) -> list[str]:
    return [t.text or "" for t in root.iter(f"{NS}title")]


def _rect_with_title(root: ET.Element, start: str) -> ET.Element:
    found = [r for r in root.iter(f"{NS}rect") if _tip(r).startswith(start)]
    assert len(found) == 1, start
    return found[0]




# ---------------------------------------------------------------- outcome_diverging


def test_diverging_titles_carry_counts():
    titles = _titles(_root(O.outcome_diverging(ROWS, CATS)))
    assert "A: correct 10 of 50 runs" in titles
    assert "A: gross error 17 of 50 runs" in titles
    assert "B: several parameters wrong 11 of 50 runs" in titles
    assert "C: correct 41 of 50 runs" in titles


def test_diverging_prints_the_counts():
    texts = ["".join(t.itertext()) for t in _root(O.outcome_diverging(ROWS, CATS)).iter(f"{NS}text")]
    for want in ("10", "17", "13", "41", "20"):
        assert want in texts


def test_diverging_zero_count_has_no_mark():
    titles = _titles(_root(O.outcome_diverging(ROWS, CATS)))
    assert not any(t.startswith("C: Dq wrong") for t in titles)


def test_diverging_correct_goes_right_errors_left_in_given_order():
    root = _root(O.outcome_diverging(ROWS, CATS))
    zero = next(e for e in root.iter(f"{NS}line") if "zero" in (e.get("class") or "").split())
    x0 = _num(zero, "x1")
    ok = _rect_with_title(root, "A: correct")
    assert _num(ok, "x") == pytest.approx(x0, abs=0.01)
    gross = _rect_with_title(root, "A: gross error")
    several = _rect_with_title(root, "A: several parameters wrong")
    dq = _rect_with_title(root, "A: Dq wrong")
    assert _num(gross, "x") + _num(gross, "width") == pytest.approx(x0, abs=0.01)
    assert _num(several, "x") + _num(several, "width") == pytest.approx(_num(gross, "x"), abs=0.01)
    assert _num(dq, "x") + _num(dq, "width") == pytest.approx(_num(several, "x"), abs=0.01)


def test_diverging_widths_are_proportional_to_counts():
    root = _root(O.outcome_diverging(ROWS, CATS))
    unit = _num(_rect_with_title(root, "A: correct"), "width") / 10
    assert _num(_rect_with_title(root, "C: correct"), "width") == pytest.approx(41 * unit, abs=0.05)
    assert _num(_rect_with_title(root, "B: gross error"), "width") == pytest.approx(20 * unit, abs=0.05)


def test_diverging_rows_follow_input_order_top_down():
    root = _root(O.outcome_diverging(ROWS, CATS))
    ys = [_num(_rect_with_title(root, f"{c}: correct"), "y") for c in "ABC"]
    assert ys == sorted(ys)


def test_diverging_escapes_labels():
    cats = [("ok", "a<b & c"), ("x", "<script>")]
    svg = O.outcome_diverging([{"cond": "A", "counts": {"ok": 2, "x": 3}}], cats)
    _root(svg)
    assert "<script>" not in svg and "<b" not in svg.replace("<b>", "")


def test_diverging_empty_and_deterministic():
    assert O.outcome_diverging([], CATS) == ""
    assert O.outcome_diverging(ROWS, []) == ""
    assert O.outcome_diverging(ROWS, CATS) == O.outcome_diverging(list(ROWS), list(CATS))


def test_diverging_natural_width():
    assert 320 <= _num(_root(O.outcome_diverging(ROWS, CATS)), "width") <= 960


# ---------------------------------------------------------------- upset


def test_upset_bar_titles_carry_counts_and_task_ids():
    titles = _titles(_root(O.upset(SETS)))
    c_only = next(t for t in titles if t.startswith("C only"))
    assert "28 tasks" in c_only and "tC27" in c_only and "tC00" in c_only
    assert any(t.startswith("A, C only") and "5 tasks" in t for t in titles)
    assert any(t.startswith("none") and "6 tasks" in t for t in titles)
    assert any(t.startswith("A, B only") and "0 tasks" in t for t in titles)
    assert any(t.startswith("A, B, C") and "3 tasks" in t for t in titles)


def test_upset_without_any_condition_is_empty():
    """No condition has an evaluable run: nothing to draw, as with no subsets at all."""
    assert O.upset(SETS, conds=()) == ""
    assert O.upset([{"key": "", "tasks": ["t1"]}], conds=()) == ""


def test_upset_says_how_many_tasks_were_left_out():
    root = _root(O.upset(SETS, excluded=["t-a", "t-b"]))
    texts = ["".join(t.itertext()) for t in root.iter(f"{NS}text")]
    assert any(t.startswith("2 tasks left out") for t in texts)
    assert "t-a, t-b" in _titles(root)
    assert not any("left out" in "".join(t.itertext()) for t in _root(O.upset(SETS)).iter(f"{NS}text"))


def test_upset_draws_only_the_given_conditions():
    """With the conditions A and C only (B has no evaluable run): no B set size, no B row, no subset with B."""
    sets = [s for s in SETS if "B" not in s["key"]]
    root = _root(O.upset(sets, conds=("A", "C")))
    titles = _titles(root)
    assert not [t for t in titles if t.startswith("B") or "B, " in t or ", B" in t or "B only" in t]
    assert "A: 10 tasks" not in titles  # the union of A over the subsets without B
    assert any(t.startswith("A: ") for t in titles) and any(t.startswith("C: ") for t in titles)
    assert any(t.startswith("A, C only") for t in titles) and any(t.startswith("none") for t in titles)
    assert "B" not in ["".join(t.itertext()) for t in root.iter(f"{NS}text")]


def test_upset_drops_subsets_with_a_condition_that_is_not_given():
    """Even when the sets still list every subset (empty ones included), a subset with B is not drawn."""
    titles = _titles(_root(O.upset(SETS, conds=("A", "C"))))
    assert "A: 7 tasks" in titles and "C: 33 tasks" in titles
    assert not [t for t in titles if t.startswith(("B", "A, B", "B, C"))]


def test_upset_set_sizes_are_union_counts():
    titles = _titles(_root(O.upset(SETS)))
    assert "A: 10 tasks" in titles
    assert "B: 9 tasks" in titles
    assert "C: 41 tasks" in titles


def test_upset_bars_are_sorted_by_count_and_proportional():
    root = _root(O.upset(SETS))
    keys = ["C only", "none", "A, C only", "B, C only", "A, B, C", "A only", "B only", "A, B only"]
    bars = [_rect_with_title(root, k) for k in keys]
    xs = [_num(b, "x") for b in bars]
    assert xs == sorted(xs)
    unit = _num(bars[0], "height") / 28
    assert _num(bars[1], "height") == pytest.approx(6 * unit, abs=0.05)
    assert _num(bars[4], "height") == pytest.approx(3 * unit, abs=0.05)
    assert _num(bars[7], "height") == 0
    # all bars stand on one baseline
    base = {round(_num(b, "y") + _num(b, "height"), 2) for b in bars}
    assert len(base) == 1


def test_upset_matrix_has_one_filled_dot_per_member():
    root = _root(O.upset(SETS))
    for cond, n in (("A", 4), ("B", 4), ("C", 4)):
        dots = [c for c in root.iter(f"{NS}circle") if f"c-{cond}" in (c.get("class") or "").split()]
        assert len(dots) == n


def test_upset_input_order_does_not_change_the_drawing():
    assert O.upset(SETS) == O.upset(list(reversed(SETS)))


def test_upset_empty_and_deterministic():
    assert O.upset([]) == ""
    assert O.upset(SETS) == O.upset(list(SETS))


# ---------------------------------------------------------------- two widths


def test_diverging_is_drawn_at_the_width_it_is_given(fig_width, fits):
    fits(O.outcome_diverging(ROWS, CATS, width=fig_width), fig_width)


def test_upset_is_drawn_at_the_width_it_is_given(fig_width, fits):
    fits(O.upset(SETS, width=fig_width), fig_width)


def test_diverging_prints_a_count_only_inside_a_segment_wide_enough_for_it():
    """a count above a narrow segment crowds its neighbours; the table beside the figure holds every number."""
    root = _root(O.outcome_diverging(ROWS, CATS, width=464))
    segs = [e for e in root.iter(f"{NS}rect") if _tip(e)]
    texts = [t for t in root.iter(f"{NS}text") if (t.text or "").strip().isdigit()]
    for t in texts:
        x, y = _num(t, "x"), _num(t, "y")
        row = [r for r in segs if _num(r, "y") <= y <= _num(r, "y") + _num(r, "height")]
        if row:  # a number in a bar row (not an axis tick) sits inside one of its segments
            assert any(_num(r, "x") <= x <= _num(r, "x") + _num(r, "width") for r in row), t.text


def test_diverging_gives_each_of_six_error_kinds_its_own_colour():
    cats = [("correct", "correct"), *((f"k{i}", f"kind {i}") for i in range(6))]
    rows = [{"cond": "A", "n": 7, "counts": {k: 1 for k, _ in cats}}]
    root = ET.fromstring(O.outcome_diverging(rows, cats))
    fills = {_classes(r)[0] for r in root.iter(f"{NS}rect") if "tile" in _classes(r)}
    assert {"e1", "e2", "e3", "e4", "e5", "e6"} <= fills


def test_diverging_gives_each_of_the_seven_report_error_kinds_its_own_colour():
    """facts.CATEGORIES has six error kinds and facts.OTHER is the seventh: no colour may repeat."""
    from tsbench.report import facts
    cats = [*facts.CATEGORIES, facts.OTHER]
    rows = [{"cond": "A", "counts": {k: 1 for k, _ in cats}}]
    root = ET.fromstring(O.outcome_diverging(rows, cats))
    fills = [_classes(r)[0] for r in root.iter(f"{NS}rect") if "tile" in _classes(r)]
    assert len(fills) == 7 and len(set(fills)) == 7


def test_diverging_gives_a_context_overflow_its_own_colour_too():
    from tsbench.report import facts
    cats = [*facts.CATEGORIES, *facts.EXTRA]
    rows = [{"cond": "A", "counts": {k: 1 for k, _ in cats}}]
    root = ET.fromstring(O.outcome_diverging(rows, cats))
    fills = [_classes(r)[0] for r in root.iter(f"{NS}rect") if "tile" in _classes(r)]
    assert len(fills) == 8 and len(set(fills)) == 8 and "e8" in fills


# ---------------------------------------------------------------- several models


def test_outcome_rows_of_several_models_share_one_axis_and_carry_their_label():
    rows = [{"cond": "A", "label": "m-long-name · A", "group": "m1", "counts": {"correct": 4, "gross": 6}},
            {"cond": "C", "label": "m-long-name · C", "group": "m1", "counts": {"correct": 9, "gross": 1}},
            {"cond": "A", "label": "other · A", "group": "m2", "counts": {"correct": 1, "gross": 2}}]
    svg = O.outcome_diverging(rows, [("correct", "correct"), ("gross", "gross error")])
    assert "m-long-name · C: correct 9 of 10 runs" in svg and "other · A: gross error 2 of 3 runs" in svg
    x = float(re.search(r'<rect class="ok" x="([0-9.]+)"', svg).group(1))  # type: ignore[union-attr]
    assert x > 100  # the labels stay left of the bars
    assert svg.count('class="grid"') > 0


def test_upset_panels_with_one_scale_draw_equal_tasks_at_equal_height():
    small = [{"key": "C", "tasks": ["a", "b"]}]
    large = [{"key": "C", "tasks": ["a", "b"]}, {"key": "BC", "tasks": ["c", "d", "e", "f"]}]
    scale = O.upset_scale([small, large])
    assert scale == (4, 6)

    def height(sets: list[dict]) -> float:
        tagged = [e for e in _root(O.upset(sets, scale=scale)).iter() if _tip(e).startswith("C only")]
        return float(tagged[0].attrib["height"])

    assert height(small) == height(large)
    assert height(small) != float(next(e for e in _root(O.upset(small)).iter()
                                       if _tip(e).startswith("C only")).attrib["height"])
