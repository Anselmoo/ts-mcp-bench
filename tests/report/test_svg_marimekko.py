from __future__ import annotations

import xml.etree.ElementTree as ET

from svg_helpers import root as _root
from svg_helpers import texts as _texts
from svg_helpers import tip as _tip

from tsbench.report.svg.marimekko import marimekko

NS = "{http://www.w3.org/2000/svg}"
SEGS = [("correct", "correct", "ok"), ("wrong", "wrong", "bad")]
TOOL = [
    {"label": "B with call", "group": "B", "parts": {"correct": 0, "wrong": 7}},
    {"label": "B without call", "group": "B", "parts": {"correct": 9, "wrong": 34}},
    {"label": "C with call", "group": "C", "parts": {"correct": 40, "wrong": 9}},
    {"label": "C without call", "group": "C", "parts": {"correct": 1, "wrong": 0}},
]


def _segments(svg: str) -> list[ET.Element]:
    return [r for r in _root(svg).iter(f"{NS}rect") if r.find(f"{NS}title") is not None]


def test_empty_returns_empty_string() -> None:
    assert marimekko([], SEGS) == ""
    assert marimekko([{"label": "x", "group": "g", "parts": {"correct": 0, "wrong": 0}}], SEGS) == ""


def test_zero_parts_draw_no_rectangle() -> None:
    svg = marimekko(TOOL, SEGS)
    tips = [_tip(r) for r in _segments(svg)]
    assert len(tips) == 6  # B with call: wrong only; C without call: correct only
    assert not any("B with call" in t and "correct" in t for t in tips)


def test_column_width_is_the_sum_of_its_parts() -> None:
    svg = marimekko(TOOL, SEGS)
    by_label: dict[str, float] = {}
    for r in _segments(svg):
        label = _tip(r).split(":")[0]
        by_label[label] = float(r.get("width", "0"))
    assert abs(by_label["B with call"] / by_label["B without call"] - 7 / 43) < 0.01
    assert abs(by_label["C with call"] / by_label["B without call"] - 49 / 43) < 0.01


def test_segment_height_is_the_share_of_the_column() -> None:
    svg = marimekko(TOOL, SEGS)
    heights = {_tip(r).split(":")[0] + _tip(r).split(":")[1].split()[0]: float(r.get("height", "0"))
               for r in _segments(svg)}
    full = heights["B with callwrong"]
    assert abs(heights["B without callcorrect"] / full - 9 / 43) < 0.01
    assert abs(heights["B without callwrong"] / full - 34 / 43) < 0.01
    assert abs(heights["C with callcorrect"] / full - 40 / 49) < 0.01


def test_titles_carry_the_counts() -> None:
    svg = marimekko(TOOL, SEGS)
    tips = [_tip(r) for r in _segments(svg)]
    assert any("C with call" in t and "40" in t and "49" in t and "runs" in t for t in tips)
    assert any("B without call" in t and "34" in t and "43" in t for t in tips)


def test_columns_are_ordered_as_the_data() -> None:
    svg = marimekko(TOOL, SEGS)
    xs = {}
    for r in _segments(svg):
        xs.setdefault(_tip(r).split(":")[0], float(r.get("x", "0")))
    order = sorted(xs, key=xs.__getitem__)
    assert order == ["B with call", "B without call", "C with call", "C without call"]


def test_groups_have_a_label_and_a_gap() -> None:
    svg = marimekko(TOOL, SEGS)
    texts = _texts(svg)
    assert texts.count("B") == 1 and texts.count("C") == 1
    rects = {}
    for r in _segments(svg):
        rects.setdefault(_tip(r).split(":")[0], (float(r.get("x", "0")), float(r.get("width", "0"))))
    gap_in = rects["B without call"][0] - (rects["B with call"][0] + rects["B with call"][1])
    gap_between = rects["C with call"][0] - (rects["B without call"][0] + rects["B without call"][1])
    assert gap_between > gap_in


def test_unit_is_used_in_the_titles() -> None:
    svg = marimekko(TOOL, SEGS, unit="mutants")
    assert any("mutants" in _tip(r) for r in _segments(svg))
    assert "mutants" in _root(svg).get("aria-label", "")


def test_legend_lists_the_segments() -> None:
    texts = _texts(marimekko(TOOL, SEGS))
    assert "correct" in texts and "wrong" in texts


def test_many_narrow_columns_stay_within_960() -> None:
    cols: list[dict] = [{"label": f"module.name_{i}", "group": f"shard{i % 6}",
                         "parts": {"k": 100 + 40 * i, "s": 5 + i, "t": i % 3}} for i in range(39)]
    cols.sort(key=lambda c: c["group"])
    segs = [("k", "killed", "g0"), ("s", "survived", "g4"), ("t", "timeout", "warn")]
    svg = marimekko(cols, segs, unit="mutants")
    root = _root(svg)
    assert float(root.get("width", "0")) <= 960
    assert len(_segments(svg)) >= 39


def test_escapes_names() -> None:
    cols = [{"label": "<b>&x", "group": "g<1>", "parts": {"correct": 2, "wrong": 1}}]
    svg = marimekko(cols, SEGS)
    assert "<b>" not in svg
    _root(svg)  # well-formed
    assert any("<b>&x" in _tip(r) for r in _segments(svg))


def test_is_deterministic() -> None:
    assert marimekko(TOOL, SEGS) == marimekko(TOOL, SEGS)


# ---------------------------------------------------------------- two widths


def test_marimekko_is_drawn_at_the_width_it_is_given(fig_width, fits) -> None:
    fits(marimekko(TOOL, SEGS, width=fig_width), fig_width)
    cols: list[dict] = [{"label": f"module.name_{i}", "group": f"shard{i % 6}",
                         "parts": {"k": 100 + 40 * i, "s": 5 + i, "t": i % 3}} for i in range(39)]
    cols.sort(key=lambda c: c["group"])
    segs = [("k", "killed", "g0"), ("s", "survived", "g4"), ("t", "timeout", "warn")]
    fits(marimekko(cols, segs, unit="mutants", width=fig_width), fig_width)


def test_column_labels_are_not_rotated() -> None:
    """labels below the column, shortened, never turned."""
    root = _root(marimekko(TOOL, SEGS, width=464))
    assert not [t for t in root.iter(f"{NS}text") if "rotate" in (t.get("transform") or "")]
