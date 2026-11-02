from __future__ import annotations

import xml.etree.ElementTree as ET

from svg_helpers import root as _root
from svg_helpers import texts as _texts
from svg_helpers import tip as _tip

from tsbench.report.svg.bars import hbars, score_bars

NS = "{http://www.w3.org/2000/svg}"


def _rects(svg: str, cls: str | None = None) -> list[ET.Element]:
    out = [r for r in _root(svg).iter(f"{NS}rect") if r.find(f"{NS}title") is not None]
    return [r for r in out if cls is None or cls in r.get("class", "").split()]


ROWS = [{"label": "tests/core", "value": 120}, {"label": "tests/run", "value": 60}, {"label": "tests/x", "value": 0}]


def test_hbars_empty() -> None:
    assert hbars([], "tests") == ""


def test_hbars_width_is_proportional_to_value() -> None:
    svg = hbars(ROWS, "tests")
    bars = _rects(svg)
    assert len(bars) == 2  # the zero row has no bar
    assert abs(float(bars[0].get("width", "0")) / float(bars[1].get("width", "0")) - 2.0) < 0.01


def test_hbars_prints_values_and_labels() -> None:
    texts = _texts(hbars(ROWS, "tests"))
    for s in ("tests/core", "tests/run", "tests/x", "120", "60", "0"):
        assert s in texts


def test_hbars_titles_have_value_and_unit() -> None:
    tips = [_tip(r) for r in _rects(hbars(ROWS, "tests"))]
    assert any("tests/core" in t and "120" in t and "tests" in t for t in tips)


def test_hbars_rows_are_ordered_as_the_data() -> None:
    ys = [float(r.get("y", "0")) for r in _rects(hbars(ROWS, "tests"))]
    assert ys == sorted(ys)


def test_hbars_escape_and_determinism() -> None:
    svg = hbars([{"label": "<i>&", "value": 3}], "u")
    assert "<i>" not in svg
    _root(svg)
    assert svg == hbars([{"label": "<i>&", "value": 3}], "u")


def test_hbars_width_within_limits() -> None:
    w = float(_root(hbars(ROWS, "tests")).get("width", "0"))
    assert 320 <= w <= 960


SCORES = [{"label": "run", "pct": 92.7}, {"label": "figures", "pct": 46.3}, {"label": "cli", "pct": None},
          {"label": "zero", "pct": 0.0}, {"label": "top", "pct": 97.4}]


def test_score_bars_empty() -> None:
    assert score_bars([]) == ""


def test_score_bars_class_by_score() -> None:
    svg = score_bars(SCORES)
    by_label = {_tip(r).split(":")[0]: r.get("class", "") for r in _rects(svg) if r.get("class", "").startswith("g")}
    assert by_label["run"] == "g1"
    assert by_label["figures"] == "g4"
    assert by_label["top"] == "g0"


def test_score_bars_width_is_proportional_to_percent() -> None:
    svg = score_bars(SCORES)
    w = {_tip(r).split(":")[0]: float(r.get("width", "0")) for r in _rects(svg) if r.get("class", "").startswith("g")}
    assert abs(w["top"] / w["figures"] - 97.4 / 46.3) < 0.01


def test_score_bars_none_is_not_mutated_and_has_no_bar() -> None:
    svg = score_bars(SCORES)
    assert "not mutated" in _texts(svg)
    assert not [r for r in _rects(svg) if _tip(r).startswith("cli") and r.get("class", "").startswith("g")]
    assert any(_tip(r).startswith("cli") and "na" in r.get("class", "").split() for r in _rects(svg))


def test_score_bars_zero_is_printed_as_a_number() -> None:
    assert "0.0 %" in _texts(score_bars(SCORES))
    assert "92.7 %" in _texts(score_bars(SCORES))


def test_score_bars_titles() -> None:
    tips = [_tip(r) for r in _rects(score_bars(SCORES))]
    assert any("run" in t and "92.7" in t for t in tips)
    assert any("cli" in t and "not mutated" in t for t in tips)


def test_score_bars_title_and_none_text_are_arguments() -> None:
    svg = score_bars(SCORES, title="Line coverage per package, 0 to 100 percent", none_text="no coverage")
    root = _root(svg)
    assert root.get("aria-label") == "Line coverage per package, 0 to 100 percent"
    assert root.find(f"{NS}title").text == "Line coverage per package, 0 to 100 percent"
    assert "no coverage" in _texts(svg)
    assert "not mutated" not in _texts(svg)
    assert any("cli" in _tip(r) and "no coverage" in _tip(r) for r in _rects(svg))


def test_score_bars_default_keeps_the_mutation_text() -> None:
    assert _root(score_bars(SCORES)).get("aria-label") == "Mutation score per row, 0 to 100 percent"


def test_score_bars_deterministic() -> None:
    assert score_bars(SCORES) == score_bars(SCORES)


# ---------------------------------------------------------------- two widths


def test_hbars_are_drawn_at_the_width_they_are_given(fig_width, fits) -> None:
    fits(hbars(ROWS, "tests", width=fig_width), fig_width)
    long = [{"label": f"tests/a_very_long_folder_name_number_{i}", "value": 10 * i} for i in range(1, 12)]
    fits(hbars(long, "tests", width=fig_width), fig_width)


def test_score_bars_are_drawn_at_the_width_they_are_given(fig_width, fits) -> None:
    fits(score_bars(SCORES, width=fig_width), fig_width)
