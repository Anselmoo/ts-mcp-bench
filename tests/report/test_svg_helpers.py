"""The shared figure checks of the report tests (conftest.assert_fits and svg_helpers): they catch what they claim."""
from __future__ import annotations

import pytest
from svg_helpers import attr_or_zero, classes, root, text_boxes, texts, tip

from tsbench.report.svg import base


def _fig(body: str, width: float = 200) -> str:
    return base.figure(width, 60, "test figure", body)


def test_a_clean_figure_passes(fits):
    fits(_fig(base.text(10, 20, "left") + base.text(190, 20, "right", "end") + base.text(100, 40, "middle", "middle")),
         200)


def test_a_label_that_starts_inside_but_runs_out_on_the_right_fails(fits):
    svg = _fig(base.text(150, 20, "a label far too long for the room"))
    with pytest.raises(AssertionError, match="outside"):
        fits(svg, 200)


def test_a_label_that_ends_inside_but_runs_out_on_the_left_fails(fits):
    svg = _fig(base.text(20, 20, "a label far too long for the room", "end"))
    with pytest.raises(AssertionError, match="outside"):
        fits(svg, 200)


def test_a_middle_anchored_label_is_measured_from_its_centre(fits):
    with pytest.raises(AssertionError, match="outside"):
        fits(_fig(base.text(20, 20, "centred and too wide", "middle")), 200)
    fits(_fig(base.text(100, 20, "centred and too wide", "middle")), 200)


def test_two_labels_that_overlap_fail(fits):
    svg = _fig(base.text(10, 20, "75 %") + base.text(30, 20, "100 %"))
    with pytest.raises(AssertionError, match="overlap"):
        fits(svg, 200)


def test_labels_side_by_side_or_on_two_lines_pass(fits):
    fits(_fig(base.text(10, 20, "75 %") + base.text(120, 20, "100 %") + base.text(10, 40, "next line")), 200)


def test_a_turned_label_is_measured_along_its_turned_extent(fits):
    near = base.text(30, 50, "turned label", "start", rotate=True)
    fits(_fig(near), 200)
    with pytest.raises(AssertionError, match="overlap"):
        fits(_fig(near + base.text(24, 30, "crossing", "start")), 200)


def test_bold_text_is_wider_than_regular_text():
    regular = text_boxes(root(_fig(base.text(10, 20, "Wide label"))))[0]
    bold = text_boxes(root(_fig(base.text(10, 20, "Wide label", "start", "b"))))[0]
    assert bold.width > regular.width > 0


def test_text_boxes_follow_group_transforms():
    svg = _fig(base.group(base.text(0, 0, "x"), transform="translate(50,30)"))
    (box,) = text_boxes(root(svg))
    assert box.centre[0] > 50 and box.centre[1] < 30


def test_the_xml_helpers_read_titles_classes_numbers_and_texts():
    svg = _fig(base.rect(1, 2, 3, 4, "c-A k-A", "tip text") + base.text(5, 6, "hello"))
    r = root(svg)
    rect = next(r.iter("{http://www.w3.org/2000/svg}rect"))
    assert tip(rect) == "tip text" and classes(rect) == ["c-A", "k-A"] and attr_or_zero(rect, "width") == 3.0
    assert attr_or_zero(rect, "missing") == 0.0 and tip(r) == "test figure"
    assert texts(svg) == ["hello"]
