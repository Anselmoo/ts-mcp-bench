"""Tests for src/tsbench/report/svg/base.py: the error-kind classes and the ink on a fill."""
from __future__ import annotations

import pytest

from tsbench.report import facts
from tsbench.report.svg import base


def test_the_seven_error_kinds_of_the_report_get_seven_distinct_classes() -> None:
    keys = [k for k, _ in [*facts.CATEGORIES[1:], facts.OTHER]]
    assert len(keys) == 7
    classes = base.error_classes(keys)
    assert list(classes) == keys
    assert len(set(classes.values())) == 7


def test_a_kind_keeps_its_class_whatever_the_other_kinds_are() -> None:
    assert base.error_classes(["other"])["other"] == base.error_classes([k for k, _ in facts.CATEGORIES[1:]]
                                                                         + ["other"])["other"]
    assert base.error_classes(["limit"])["limit"] == base.error_classes(["gross", "limit"])["limit"]


def test_unknown_kinds_take_the_free_classes_in_order_and_never_collide_with_known_ones() -> None:
    classes = base.error_classes(["gross", "x1", "x2"])
    assert classes["gross"] == "e1"
    assert len(set(classes.values())) == 3


def test_more_kinds_than_classes_raise_instead_of_wrapping() -> None:
    with pytest.raises(ValueError, match="error kinds"):
        base.error_classes([f"k{i}" for i in range(len(base.ERROR_CLASSES) + 1)])


def test_every_error_class_has_an_ink() -> None:
    for cls in base.ERROR_CLASSES:
        assert base.ink(cls) == f"on-{cls}"


# ---------------------------------------------------------------- numbers, coordinates, text helpers


def test_coord_has_at_most_two_decimals_and_never_a_negative_zero() -> None:
    assert base.coord(3.0) == "3" and base.coord(3.456) == "3.46" and base.coord(3.4) == "3.4"
    assert base.coord(-0.001) == "0" and base.coord(0.0) == "0" and base.coord(-2.5) == "-2.5"


def test_number_uses_thin_spaces_the_minus_sign_and_a_dash_for_none() -> None:
    assert base.number(1234567) == "1\u2009234\u2009567" and base.number(-3.14159, 2) == "−3.14"
    assert base.number(None) == "–" and base.number(float("nan")) == "–" and base.number(None, dash="n/a") == "n/a"


def test_pct_is_a_share_with_its_unit() -> None:
    assert base.pct(0.2) == "20\u00a0%" and base.pct(0.256, 1) == "25.6\u00a0%" and base.pct(None) == "–"


def test_percent_is_a_value_in_percent_with_one_decimal_or_the_label() -> None:
    assert base.percent(87.3) == "87.3 %" and base.percent(100.0) == "100.0 %"
    assert base.percent(None) == "no value"
    assert base.percent(None, "n/a") == "n/a"


def test_polar_measures_the_angle_from_twelve_oclock_clockwise() -> None:
    import math

    x, y = base.polar(10.0, 20.0, 5.0, 0.0)
    assert (round(x, 9), round(y, 9)) == (10.0, 15.0)
    x, y = base.polar(10.0, 20.0, 5.0, math.pi / 2)
    assert (round(x, 9), round(y, 9)) == (15.0, 20.0)
    x, y = base.polar(10.0, 20.0, 5.0, math.pi)
    assert (round(x, 9), round(y, 9)) == (10.0, 25.0)


def test_plural_writes_the_count_and_the_word_in_its_number() -> None:
    assert base.plural(0, "run") == "0 runs" and base.plural(1, "run") == "1 run" and base.plural(2, "run") == "2 runs"
    assert base.plural(1, "char") == "1 char" and base.plural(1000, "char") == "1000 chars"


def test_plural_has_one_implementation_for_figures_and_pages() -> None:
    """The report pages use the figure helper: a y ending becomes ies, `words` names an irregular plural and
    `shown` is the printed count."""
    from tsbench.report import page
    assert page.plural is base.plural
    assert base.plural(3, "family") == "3 families" and base.plural(1, "family") == "1 family"
    assert base.plural(2, "class", "classes") == "2 classes" and base.plural(1, "class", "classes") == "1 class"
    assert base.plural(1234, "char", shown="1.2k") == "1.2k chars"
    assert base.plural(1, "char", shown="1") == "1 char"


def test_module_name_drops_the_package_prefix_only_at_the_start() -> None:
    assert base.module_name("tsbench.score.numeric") == "score.numeric"
    assert base.module_name("score.tsbench.numeric") == "score.tsbench.numeric"


# ---------------------------------------------------------------- scales and ticks


def test_linear_maps_the_domain_to_the_range_and_a_flat_domain_to_the_middle() -> None:
    sc = base.Linear(0, 10, 100, 200)
    assert sc(0) == 100 and sc(10) == 200 and sc(2.5) == 125
    assert base.Linear(5, 5, 0, 10)(5) == 5
    assert base.Linear(10, 0, 0, 100)(2.5) == 75  # a reversed domain maps in reverse
    assert base.Linear(0, 1, 100, 0)(0.25) == 75  # a reversed range (screen y)


def test_log_maps_decades_evenly_and_clamps_to_the_domain() -> None:
    sc = base.Log(0.01, 100, 0, 400)
    assert sc(0.01) == pytest.approx(0) and sc(1) == pytest.approx(200) and sc(100) == pytest.approx(400)
    assert sc(1e-6) == pytest.approx(0) and sc(1e6) == pytest.approx(400)
    assert sc(10) == pytest.approx(300)


def test_log_ticks_are_the_powers_of_ten_inside_the_domain() -> None:
    assert base.Log(0.01, 100, 0, 1).ticks() == [0.01, 0.1, 1.0, 10.0, 100.0]
    assert base.Log(0.5, 50, 0, 1).ticks() == [1.0, 10.0]


def test_nice_ticks_are_round_values_inside_the_range() -> None:
    assert base.nice_ticks(0, 100, 5) == [0, 20, 40, 60, 80, 100]
    assert base.nice_ticks(0, 1, 4) == [0, 0.5, 1.0] or base.nice_ticks(0, 1, 4) == [0, 0.25, 0.5, 0.75, 1.0]
    assert base.nice_ticks(3, 3) == [3]
    assert base.nice_ticks(10, 0, 5) == base.nice_ticks(0, 10, 5)  # a swapped range is the same range
    ticks = base.nice_ticks(-37, 112, 6)
    assert all(-37 <= t <= 112 for t in ticks) and len(ticks) >= 3
    steps = {round(b - a, 9) for a, b in zip(ticks, ticks[1:], strict=False)}
    assert len(steps) == 1


def test_linear_ticks_are_nice_ticks_of_the_domain() -> None:
    assert base.Linear(0, 100, 0, 1).ticks(5) == base.nice_ticks(0, 100, 5)


# ---------------------------------------------------------------- axes and legend


def test_axis_bottom_puts_a_tick_and_a_label_at_the_scaled_position_of_each_value() -> None:
    sc = base.Linear(0, 100, 50, 250)
    svg = base.axis_bottom(sc, [0, 50, 100], 80, 50, 250, "runs", grid_to=10)
    for v, x in ((0, "50"), (50, "150"), (100, "250")):
        assert f'<line class="ax" x1="{x}" y1="80" x2="{x}" y2="84"/>' in svg
        assert f'<line class="grid" x1="{x}" y1="10" x2="{x}" y2="80"/>' in svg
        assert f'x="{x}" y="{base.coord(80 + 4 + base.TEXT_PX)}" text-anchor="middle">{v}</text>' in svg
    assert svg.startswith('<line class="ax" x1="50" y1="80" x2="250" y2="80"/>')
    assert ">runs</text>" in svg


def test_axis_left_puts_a_tick_left_of_the_line_and_a_rotated_label() -> None:
    sc = base.Linear(0, 10, 100, 0)
    svg = base.axis_left(sc, [0, 10], 40, 0, 100, "tasks")
    assert '<line class="ax" x1="36" y1="100" x2="40" y2="100"/>' in svg
    assert '<line class="ax" x1="36" y1="0" x2="40" y2="0"/>' in svg
    assert 'transform="rotate(-90' in svg and ">tasks</text>" in svg


def test_legend_gives_each_kind_its_mark_and_returns_the_x_after_the_last_entry() -> None:
    svg, end = base.legend([("A", "alpha"), ("open-B", "open"), ("g0", "good")], 0, 10)
    assert "<circle" in svg and "<rect" in svg and 'class="g0"' in svg and "alpha" in svg
    assert end > 3 * 15
    one, end1 = base.legend([("A", "alpha")], 0, 10)
    assert end > end1 > 15 and one in svg


def test_legend_rows_wrap_at_the_width_and_return_the_next_free_line() -> None:
    items = [("g0", "x" * 20)] * 6
    one_row, y1 = base.legend_rows(items, 10_000, 0, 14)
    assert y1 == 14 + 18
    wrapped, y2 = base.legend_rows(items, 300, 0, 14)
    assert y2 > y1 and wrapped.count("<text") == 6
    ys = {float(t) for t in __import__("re").findall(r'<text x="[^"]*" y="([^"]*)"', wrapped)}
    assert len(ys) == (y2 - 14) / 18


# ---------------------------------------------------------------- classes


def test_score_class_steps_start_at_the_lower_bound_of_each_step() -> None:
    assert base.score_class(None) == "na"
    assert [base.score_class(p) for p in (100, 95, 94.99, 90, 89.99, 75, 74.99, 50, 49.99, 0)] == [
        "g0", "g0", "g1", "g1", "g2", "g2", "g3", "g3", "g4", "g4"]


def test_ink_names_the_text_class_of_a_fill_class() -> None:
    assert base.ink("g2") == "on-g2" and base.ink("c-A") == "on-A" and base.ink("bad tile") == "on-bad"
    assert base.ink("") == "" and base.ink("band") == "" and base.ink("na") == ""


def test_escape_quotes_text_and_attributes() -> None:
    assert base.escape('<a href="x">&\'') == "&lt;a href=&quot;x&quot;&gt;&amp;&#x27;"
    assert base.escape(3) == "3"


def test_everything_in_all_is_defined() -> None:
    assert all(hasattr(base, name) for name in base.__all__)


# ---------------------------------------------------------------- rounding of shown numbers


def test_round_half_up_rounds_a_half_away_from_zero_not_to_the_even_neighbour() -> None:
    assert [base.round_half_up(x) for x in (0.5, 1.5, 2.5, 3.5, 26.5, 27.5)] == [1, 2, 3, 4, 27, 28]
    assert [base.round_half_up(x) for x in (-0.5, -2.5, -3.5)] == [-1, -3, -4]
    assert base.round_half_up(1.25, 1) == 1.3 and base.round_half_up(2.675, 2) == 2.68
    assert base.round_half_up(100 * 0.145) == 15  # 14.499999999999998 in floating point


def test_number_pct_and_percent_round_a_half_up() -> None:
    assert [base.number(x) for x in (2.5, 3.5, 3466.5, 3325.5, -2.5)] == ["3", "4", "3 467", "3 326", "−3"]
    assert base.number(0.125, 2) == "0.13" and base.number(-0.4) == "0"
    assert base.pct(0.025) == "3 %" and base.pct(0.035) == "4 %"
    assert base.percent(2.25) == "2.3 %" and base.percent(2.35) == "2.4 %"


def test_signed_pp_is_a_signed_whole_number_of_percentage_points() -> None:
    assert [base.signed_pp(v) for v in (0.62, -0.02, 0.004, 0.025, 0.035, -0.025, -0.035)] == [
        "+62", "−2", "0", "+3", "+4", "−3", "−4"]


# ---------------------------------------------------------------- figure role and task links


def test_a_figure_without_links_is_one_image_and_a_figure_with_task_links_is_a_group() -> None:
    """The children of role=img are presentational: a link inside would be a focus stop without a name."""
    plain = base.figure(100, 50, "Plain", base.rect(0, 0, 10, 10))
    linked = base.figure(100, 50, "Linked", base.link("#task-x", base.rect(0, 0, 10, 10, tip="x")))
    assert 'role="img"' in plain and 'role="group"' not in plain
    assert 'role="group"' in linked and 'role="img"' not in linked
    assert 'aria-label="Linked"' in linked and "<title>Linked</title>" in linked


def test_a_task_link_is_not_a_tab_stop_because_the_task_tables_hold_the_same_link() -> None:
    assert base.link("#task-x", "<rect/>") == '<a href="#task-x" tabindex="-1"><rect/></a>'


# ---------------------------------------------------------------- score legend


def test_score_legend_names_the_ranges_of_the_score_steps_and_the_classes_of_their_colours() -> None:
    assert base.score_legend() == [("g0", "95 % and above"), ("g1", "90 to 95 %"), ("g2", "75 to 90 %"),
                                   ("g3", "50 to 75 %"), ("g4", "below 50 %")]
    assert [c for c, _ in base.score_legend()] == [base.score_class(p) for p in (100, 92, 80, 60, 10)]


def test_score_legend_follows_a_change_of_the_score_steps(monkeypatch) -> None:
    monkeypatch.setattr(base, "SCORE_STEPS", (97.5, 90.0, 75.0, 50.0))
    assert base.score_legend()[:2] == [("g0", "97.5 % and above"), ("g1", "90 to 97.5 %")]
    assert base.score_class(96.0) == "g1"


# ---------------------------------------------------------------- axis labels that would collide


def _label_boxes(svg: str) -> list[tuple[float, float]]:
    import re

    from svg_helpers import text_width
    return [(float(x) - text_width(t, base.TEXT_PX) / 2, float(x) + text_width(t, base.TEXT_PX) / 2)
            for x, t in re.findall(r'<text class="mut" x="([^"]*)" y="[^"]*" text-anchor="middle">([^<]*)</text>', svg)]


def test_axis_bottom_keeps_every_tick_but_drops_the_labels_that_would_touch_the_last_one_drawn() -> None:
    sc = base.Log(1.0, 1e9, 0.0, 320.0)
    svg = base.axis_bottom(sc, sc.ticks(), 80, 0, 320)
    assert svg.count('y2="84"') == 10  # all ten decade ticks stay
    boxes = _label_boxes(svg)
    assert 2 <= len(boxes) < 10
    assert all(b[0] >= a[1] for a, b in zip(boxes, boxes[1:], strict=False))
    assert ">1</text>" in svg  # the first label is drawn


def test_axis_bottom_draws_all_labels_that_fit() -> None:
    sc = base.Linear(0, 100, 0, 400)
    svg = base.axis_bottom(sc, [0, 25, 50, 75, 100], 80, 0, 400)
    assert len(_label_boxes(svg)) == 5


def test_log_ticks_take_a_stride() -> None:
    assert base.Log(1, 1e9, 0, 1).ticks(3) == [1.0, 1e3, 1e6, 1e9]
    assert base.Log(1, 1e9, 0, 1).ticks() == [10.0 ** e for e in range(10)]


# ---------------------------------------------------------------- one text estimate for every figure


def test_text_width_is_the_length_times_the_size_times_one_constant() -> None:
    assert base.text_width("abcd") == 4 * base.TEXT_PX * base.GLYPH_EM
    assert base.text_width("abcd", base.SMALL_PX) == 4 * base.SMALL_PX * base.GLYPH_EM
    assert base.text_width("") == 0


def test_fit_cuts_with_an_ellipsis_to_the_room_and_keeps_four_characters_at_least() -> None:
    per = 10
    room = per * base.TEXT_PX * base.GLYPH_EM + 0.5
    assert base.fit("x" * per, room) == "x" * per
    assert base.fit("x" * (per + 1), room) == "x" * (per - 1) + "…"
    assert base.fit("abcdefgh", 1.0) == "abc…"  # never fewer than four characters
    assert base.fit("abc", 1.0) == "abc"
    assert base.fit("abcdefgh", 1.0, blank=True) == ""  # blank: nothing when fewer than four fit
    assert base.fit("abcdefgh", 4.5 * base.SMALL_PX * base.GLYPH_EM, base.SMALL_PX, blank=True) == "abc…"


def test_wrap_breaks_at_spaces_and_splits_a_long_word_only_on_request() -> None:
    room = 10 * base.TEXT_PX * base.GLYPH_EM + 0.5
    assert base.wrap("aaaa bbbb cccc", room) == ["aaaa bbbb", "cccc"]
    assert base.wrap("a" * 12, room) == ["a" * 12]
    assert base.wrap("a" * 12 + " bb", room, split_words=True) == ["a" * 10, "aa bb"]
    assert base.wrap("", room) == []
    assert base.wrap("aa bb", 1.0, least=8) == ["aa bb"]  # a line holds eight characters at least


def test_no_figure_module_keeps_its_own_glyph_width_or_plural() -> None:
    """The text estimate, the cut, the wrap and the plural live in base.py: a recalibration is one edit."""
    import pathlib
    import re
    glyph = re.compile(r"len\([^)\n]*\)[^\n]*\*[^\n]*0\.(55|56|6|62)\b|\*\s*0\.(55|56|62)\b")
    plural = re.compile(r"""\bif [\w.()]+ (?:==|!=) 1 else ["'](?:s|)["']|\bn == 1 else ["']s""")
    folder = pathlib.Path(base.__file__).parent
    for path in sorted(folder.glob("*.py")):
        if path.name == "base.py":
            continue
        code = path.read_text(encoding="utf-8")
        assert not glyph.search(code), f"{path.name} estimates a text width itself"
        assert not plural.search(code), f"{path.name} writes a plural itself"
        assert not re.search(r"^def _(tw|text_w|fit|cut|short)\(", code, flags=re.M), f"{path.name} has its own helper"


def test_a_non_finite_number_is_shown_as_python_shows_it_not_raised() -> None:
    assert base.number(float("inf")) == "inf" and base.number(float("-inf")) == "−inf"
    assert base.round_half_up(float("inf")) == float("inf")
    assert base.round_half_up(float("nan")) != base.round_half_up(float("nan"))  # nan stays nan


def test_a_huge_number_is_shown_not_raised() -> None:
    """Decimal's default 28 digits are not enough for 1e30 at nd 0 or 1e27 at nd 2."""
    assert base.number(1e30) == "1" + "\u2009000" * 10
    assert base.number(-1e27, 2) == "\u22121" + "\u2009000" * 9 + ".00"
    assert base.round_half_up(1e30) == 10**30 and base.round_half_up(2.5e26, 2) == 2.5e26
    assert base.fixed(1e300) == "1" + "0" * 300 and base.fixed(1e30, 2) == "1" + "0" * 30 + ".00"


def test_fixed_formats_a_half_up_without_a_separator_or_a_special_minus() -> None:
    assert [base.fixed(x, 1) for x in (12.25, 2.25, 0.05, -2.25, 5.25)] == ["12.3", "2.3", "0.1", "-2.3", "5.3"]
    assert [base.fixed(x, 2) for x in (0.125, 0.375, 1234.565)] == ["0.13", "0.38", "1234.57"]
    assert [base.fixed(x) for x in (2.5, 3.5, 12500.0)] == ["3", "4", "12500"] and base.fixed(-0.4) == "0"
    assert base.fixed(float("inf")) == "inf" and base.fixed(float("nan")) == "nan"
    assert base.fixed(0.25, 1, sign=True) == "+0.3" and base.fixed(-0.25, 1, sign=True) == "-0.3"
    assert base.fixed(0.0, 1, sign=True) == "0.0" and base.fixed(-0.04, 1, sign=True) == "0.0"


def test_significant_rounds_a_half_up_to_n_significant_digits():
    # a half rounds up at four significant digits: 3466.5 gives 3467 and 3467.5 gives 3468
    assert base.significant(3466.5) == "3 467"
    assert base.significant(3467.5) == "3 468"
    assert base.significant(0.12345) == "0.1235"
    assert base.significant(12.0) == "12"
    assert base.significant(0.0) == "0"
    assert base.significant(-2.5, 1) == "−3"
