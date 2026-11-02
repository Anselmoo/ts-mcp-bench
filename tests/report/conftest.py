"""Shared checks of the report tests."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections.abc import Callable

import pytest
from svg_helpers import NS, assert_text_boxes_fit

from tsbench.report.svg import base

WIDTHS = (base.FULL_W, base.HALF_W)


def assert_fits(svg: str, width: float) -> None:
    """A figure drawn at `width` is an `<svg class="fig">` whose width attribute is exactly `width`; its
    lettering is the body size (no font-size) or 11 px; it names no colour (classes only); every text, measured with
    Arial widths from its anchor, lies inside the width, and no two texts overlap."""
    assert svg, "empty figure"
    root = ET.fromstring(svg)
    assert root.get("width") == base.coord(width), (root.get("width"), width)
    assert "fig" in (root.get("class") or "").split()
    sizes = {el.get("font-size") for el in root.iter() if el.get("font-size") is not None}
    assert sizes <= {"11px"}, sizes
    assert not re.search(r'="\s*#[0-9a-fA-F]{3,8}\s*"|:\s*#[0-9a-fA-F]{3,8}\b|rgba?\(', svg)
    for t in root.iter(f"{NS}text"):
        x = float(t.get("x") or 0)
        assert 0 <= x <= width, (x, "".join(t.itertext()))
    assert_text_boxes_fit(root, width)


@pytest.fixture(params=WIDTHS, ids=["full", "half"])
def fig_width(request) -> float:
    """The two figure widths of the page: full (960 px) and half (464 px)."""
    return request.param


@pytest.fixture()
def fits() -> Callable[[str, float], None]:
    return assert_fits
