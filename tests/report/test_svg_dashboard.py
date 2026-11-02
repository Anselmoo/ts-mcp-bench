"""Tests for src/tsbench/report/svg/dashboard.py: share with interval, paired differences."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET

import pytest
from svg_helpers import attr_or_zero as _num
from svg_helpers import classes as _cls
from svg_helpers import root as _root

from tsbench.report.svg import dashboard as D

NS = "{http://www.w3.org/2000/svg}"
SHARES = [
    {"cond": "A", "k": 10, "n": 50, "share": 0.20, "lo": 0.10, "hi": 0.34},
    {"cond": "B", "k": 9, "n": 50, "share": 0.18, "lo": 0.09, "hi": 0.31},
    {"cond": "C", "k": 41, "n": 50, "share": 0.82, "lo": 0.69, "hi": 0.91},
]
PAIRS = [
    {"pair": "C − A", "diff": 0.62, "lo": 0.46, "hi": 0.76, "only_first": 33, "only_second": 2},
    {"pair": "C − B", "diff": 0.64, "lo": 0.50, "hi": 0.78, "only_first": 33, "only_second": 1},
    {"pair": "B − A", "diff": -0.02, "lo": -0.16, "hi": 0.12, "only_first": 6, "only_second": 7},
]


def _texts(root: ET.Element) -> list[tuple[str, float, float]]:
    return [("".join(t.itertext()).replace("\u00a0", " "), _num(t, "x"), _num(t, "y"))
            for t in root.iter(f"{NS}text")]


def _titles(root: ET.Element) -> list[str]:
    return [(t.text or "").replace("\u00a0", " ") for t in root.iter(f"{NS}title")]


def _center(el: ET.Element) -> float:
    if el.tag == f"{NS}circle":
        return _num(el, "cx")
    if el.tag == f"{NS}rect":
        return _num(el, "x") + _num(el, "width") / 2
    xs = [float(p.split(",")[0]) for p in (el.get("points") or "").split()]
    return sum(xs) / len(xs)


def _marker(root: ET.Element, cond: str) -> ET.Element:
    found = [e for e in root.iter() if f"c-{cond}" in (e.get("class") or "").split() and "ribbon" not in _cls(e)]
    assert len(found) == 1
    return found[0]


def _x_of_text(root: ET.Element, label: str) -> float:
    return next(x for s, x, _ in _texts(root) if s == label)


def test_share_is_valid_svg_with_natural_width():
    svg = D.share_intervals(SHARES)
    root = _root(svg)
    w = _num(root, "width")
    assert 320 <= w <= 960
    assert (root.get("viewBox") or "").split()[2] == root.get("width")


def test_share_columns_carry_the_numbers():
    strings = [s for s, _, _ in _texts(_root(D.share_intervals(SHARES)))]
    for want in ("20 %", "18 %", "82 %", "10–34", "9–31", "69–91", "10/50", "9/50", "41/50"):
        assert want in strings


def test_share_tooltips_have_exact_numbers():
    titles = _titles(_root(D.share_intervals(SHARES)))
    assert any("A" in t and "10/50" in t and "20 %" in t and "10–34" in t for t in titles)
    assert any("C" in t and "41/50" in t and "82 %" in t and "69–91" in t for t in titles)


def test_share_points_sit_on_a_linear_zero_to_hundred_axis():
    root = _root(D.share_intervals(SHARES))
    x0, x100 = _x_of_text(root, "0"), _x_of_text(root, "100 %")
    for cond, share in (("A", 0.20), ("B", 0.18), ("C", 0.82)):
        assert _center(_marker(root, cond)) == pytest.approx(x0 + share * (x100 - x0), abs=0.1)


def test_share_interval_bar_runs_from_lo_to_hi():
    root = _root(D.share_intervals(SHARES))
    x0, x100 = _x_of_text(root, "0"), _x_of_text(root, "100 %")
    bars = [e for e in root.iter(f"{NS}rect") if "ribbon" in (e.get("class") or "").split()]
    assert len(bars) == 3
    c = next(b for b in bars if "c-C" in _cls(b))
    assert _num(c, "x") == pytest.approx(x0 + 0.69 * (x100 - x0), abs=0.1)
    assert _num(c, "width") == pytest.approx(0.22 * (x100 - x0), abs=0.1)


def test_share_rows_are_in_input_order_top_down():
    root = _root(D.share_intervals(SHARES))
    ys = [y for s, _, y in _texts(root) if s in ("20 %", "18 %", "82 %")]
    assert ys == sorted(ys)


def test_share_empty_and_deterministic():
    assert D.share_intervals([]) == ""
    assert D.share_intervals(SHARES) == D.share_intervals(list(SHARES))


def test_paired_columns_carry_the_numbers():
    strings = [s for s, _, _ in _texts(_root(D.paired_diffs(PAIRS)))]
    for want in ("+62 pp", "+64 pp", "−2 pp", "only C 33 · only A 2", "only C 33 · only B 1", "only B 6 · only A 7",
                 "+46 to +76", "+50 to +78", "−16 to +12"):
        assert want in strings


def test_paired_tooltips_have_exact_numbers():
    titles = _titles(_root(D.paired_diffs(PAIRS)))
    assert any("C − A" in t and "+62 pp" in t and "+46 to +76" in t and "33" in t for t in titles)
    assert any("B − A" in t and "−2 pp" in t and "−16 to +12" in t for t in titles)


def test_paired_axis_is_minus_hundred_to_plus_hundred_with_zero_line():
    root = _root(D.paired_diffs(PAIRS))
    xm, xz, xp = _x_of_text(root, "−100"), _x_of_text(root, "0"), _x_of_text(root, "+100")
    assert xz == pytest.approx((xm + xp) / 2, abs=0.1)
    zero = next(e for e in root.iter(f"{NS}line") if "zero" in (e.get("class") or "").split())
    assert _num(zero, "x1") == pytest.approx(xz, abs=0.1)
    # C − A has the first condition's marker; the points of the three pairs
    pts = [e for e in root.iter() if e.tag in (f"{NS}circle", f"{NS}rect", f"{NS}polygon")
           and re.search(r"\bc-[ABC]\b", e.get("class") or "") and "ribbon" not in _cls(e)]
    assert len(pts) == 3
    xs = [_center(p) for p in pts]
    for x, d in zip(xs, (0.62, 0.64, -0.02), strict=True):
        assert x == pytest.approx(xz + d * (xp - xm) / 2, abs=0.1)


def test_paired_interval_bar_crosses_zero_for_b_minus_a():
    root = _root(D.paired_diffs(PAIRS))
    xm, xz, xp = _x_of_text(root, "−100"), _x_of_text(root, "0"), _x_of_text(root, "+100")
    bars = [e for e in root.iter(f"{NS}rect") if "ribbon" in (e.get("class") or "").split()]
    assert len(bars) == 3
    x = _num(bars[2], "x")
    w = _num(bars[2], "width")
    assert x == pytest.approx(xz - 0.16 * (xp - xm) / 2, abs=0.1)
    assert x < xz < x + w


def test_paired_escapes_labels_and_is_well_formed():
    rows = [{"pair": "<i> − &", "diff": 0.1, "lo": 0.0, "hi": 0.2, "only_first": 1, "only_second": 2}]
    svg = D.paired_diffs(rows)
    _root(svg)
    assert "<i>" not in svg


def test_paired_empty_and_deterministic():
    assert D.paired_diffs([]) == ""
    assert D.paired_diffs(PAIRS) == D.paired_diffs(list(PAIRS))


# ---------------------------------------------------------------- two widths


def test_share_is_drawn_at_the_width_it_is_given(fig_width, fits):
    fits(D.share_intervals(SHARES, width=fig_width), fig_width)


def test_paired_is_drawn_at_the_width_it_is_given(fig_width, fits):
    fits(D.paired_diffs(PAIRS, width=fig_width), fig_width)


def test_columns_move_with_the_width():
    """the x positions of the number columns come from the width, not from constants."""
    def last_x(svg: str) -> float:
        return max(float(t.get("x") or 0) for t in _root(svg).iter(f"{NS}text"))
    assert last_x(D.share_intervals(SHARES, width=960)) > last_x(D.share_intervals(SHARES, width=464)) + 200
    assert last_x(D.paired_diffs(PAIRS, width=960)) > last_x(D.paired_diffs(PAIRS, width=464)) + 200


def test_paired_whole_points_round_a_half_up():
    rows = [{"pair": "C − A", "diff": d, "lo": lo, "hi": hi, "only_first": 1, "only_second": 1}
            for d, lo, hi in ((0.025, -0.025, 0.035), (0.035, -0.035, 0.045), (-0.025, -0.045, 0.025))]
    strings = [s for s, _, _ in _texts(_root(D.paired_diffs(rows)))]
    for want in ("+3 pp", "+4 pp", "−3 pp", "−3 to +4", "−4 to +5", "−5 to +3"):
        assert want in strings


def test_share_interval_ends_round_a_half_up():
    rows = [{"cond": "A", "k": 1, "n": 40, "share": 0.025, "lo": 0.025, "hi": 0.035}]
    strings = [s for s, _, _ in _texts(_root(D.share_intervals(rows)))]
    assert "3–4" in strings and "3 %" in strings
