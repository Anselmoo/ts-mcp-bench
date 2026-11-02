"""Tests for src/tsbench/report/svg/dots.py: class dumbbells and literature dots."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from svg_helpers import attr_float as _f
from svg_helpers import match as _m

from tsbench.report.svg import dots

NS = "{http://www.w3.org/2000/svg}"


def _titled(root):
    return [(el.tag.removeprefix(NS), el, t.text or "") for el in root.iter()
            if el is not root and (t := el.find(f"{NS}title")) is not None]


def _center(el):
    tag = el.tag.removeprefix(NS)
    if tag == "circle":
        return _f(el, "cx"), _f(el, "cy")
    if tag == "rect":
        return _f(el, "x") + _f(el, "width") / 2, _f(el, "y") + _f(el, "height") / 2
    pts = [tuple(map(float, p.split(","))) for p in el.get("points").split()]
    return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)


def _marks(root):
    return [(el, t) for tag, el, t in _titled(root) if tag in ("circle", "rect", "polygon")
            and re.search(r"\b[ABC]\b", t) and "tolerance" not in t]


def _texts(root):
    return [el.text for el in root.iter(f"{NS}text")]


# ---------------------------------------------------------------- class_dots

ROWS = [
    {"class": "batch", "n": 3, "k": {"A": 1, "B": 3, "C": 3}},
    {"class": "num<1>", "n": 10, "k": {"A": 2, "B": 5, "C": 9}},
    {"class": "pairing", "n": 1, "k": {"A": 0, "B": 0, "C": 1}},
]


def test_class_dots_empty():
    assert dots.class_dots([]) == ""


def test_class_dots_tick_labels_do_not_collide_at_half_width():
    """At 464 px with long class names the plot is narrow: the axis keeps the two end labels, 0 and 100 %, and
    drops the 50 % that would touch them (the ticks stay)."""
    rows = [dict(r, **{"class": "literature_all_long_name"}) for r in ROWS]
    root = ET.fromstring(dots.class_dots(rows, width=464))
    ticks = [t for t in _texts(root) if t and t.endswith(" %")]
    assert ticks == ["0 %", "100 %"]


def test_class_dots_use_the_tasks_with_an_evaluable_run_per_condition():
    rows = [{"class": "batch", "n": 3, "k": {"A": 1, "B": 3, "C": 3}, "n_by": {"A": 2, "B": 3, "C": 3}}]
    root = ET.fromstring(dots.class_dots(rows))
    titles = [t for _, _, t in _titled(root)]
    assert "batch · A: 1/2 (50 %)" in titles and "batch · B: 3/3 (100 %)" in titles
    assert "A 1/2" in _texts(root) and "B C 3/3" in _texts(root)


def test_class_dots_leave_out_a_condition_without_an_evaluable_run():
    """n_by 0 is no answer, not 0 %: no marker, no end of the dumbbell line, and the label says `no run`."""
    rows = [{"class": "curve", "n": 1, "k": {"A": 0, "B": 1, "C": 0}, "n_by": {"A": 1, "B": 1, "C": 0}},
            {"class": "diagram", "n": 2, "k": {"A": 1, "B": 0, "C": 0}, "n_by": {"A": 2, "B": 0, "C": 0}}]
    root = ET.fromstring(dots.class_dots(rows))
    titles = [t for _, _, t in _titled(root)]
    assert not [t for t in titles if "curve · C" in t or "diagram · B" in t or "diagram · C" in t]
    assert "curve · A: 0/1 (0 %)" in titles and "curve · B: 1/1 (100 %)" in titles
    assert "curve: lowest 0/1, highest 1/1" in titles  # the line runs between the conditions that answered
    assert not [t for t in titles if t.startswith("diagram:")]  # one condition answered: no line
    texts = _texts(root)
    assert "C no run" in texts and "B C no run" in texts and "A 1/2" in texts


def test_class_dots_markers_x_follow_share():
    svg = dots.class_dots(ROWS)
    assert svg == dots.class_dots(ROWS)
    root = ET.fromstring(svg)
    marks = {_m(r"^(.*) · ([ABC]):", t).groups(): _center(el) for el, t in _marks(root)}
    assert len(marks) == 9
    assert marks[("num<1>", "A")][0] < marks[("num<1>", "B")][0] < marks[("num<1>", "C")][0]
    assert marks[("batch", "B")][0] == marks[("batch", "C")][0]
    # x = k/n: C of the 10 task class (0.9) is further right than A of batch (0.33)
    assert marks[("num<1>", "C")][0] > marks[("batch", "A")][0]
    # rows keep the order of the input
    ys = [marks[(c, "A")][1] for c in ("batch", "num<1>", "pairing")]
    assert ys == sorted(ys)


def test_class_dots_titles_and_labels_carry_k_over_n():
    root = ET.fromstring(dots.class_dots(ROWS))
    titles = [t for _, t in _marks(root)]
    assert "num<1> · C: 9/10 (90 %)" in titles
    texts = _texts(root)
    for label in ("1/3", "3/3", "2/10", "5/10", "9/10", "0/1", "1/1"):
        assert any(t and t.endswith(label) for t in texts), label


def test_class_dots_dumbbell_spans_lowest_to_highest():
    root = ET.fromstring(dots.class_dots(ROWS))
    marks = {_m(r"^(.*) · ([ABC]):", t).groups(): _center(el) for el, t in _marks(root)}
    bells = [el for tag, el, t in _titled(root) if tag == "line"]
    assert len(bells) == 3
    first = bells[0]
    assert abs(_f(first, "x1") - marks[("batch", "A")][0]) < 0.01
    assert abs(_f(first, "x2") - marks[("batch", "C")][0]) < 0.01


def test_class_dots_escapes():
    assert "num<1>" not in dots.class_dots(ROWS)


def test_class_dots_draw_only_the_conditions_the_rows_carry():
    """A condition with no evaluable run is absent from `k`: no B marker, no `B: 0/n` title, no B legend entry."""
    rows = [{"class": "batch", "n": 3, "k": {"A": 1, "C": 3}}, {"class": "pairing", "n": 1, "k": {"A": 0, "C": 1}}]
    root = ET.fromstring(dots.class_dots(rows))
    titles = [t for _, _, t in _titled(root)]
    assert not [t for t in titles if re.search(r"\bB\b", t)]
    assert "batch · A: 1/3 (33 %)" in titles and "batch · C: 3/3 (100 %)" in titles
    texts = _texts(root)
    assert "B" not in texts and "A" in texts and "C" in texts
    assert not [t for t in texts if t and t.startswith("B ")]


def test_signed_zero_deviations_print_as_plain_zero():
    """A deviation that rounds to zero has no sign: `0 %`, never `−0 %` or `+0 %`."""
    assert dots._signed(-0.02) == "0 %" and dots._signed(0.02) == "0 %" and dots._signed(0.0) == "0 %"
    assert dots._signed(-0.04) == "0 %"
    assert dots._signed(20.0) == "+20 %" and dots._signed(-3.5) == "−3.5 %" and dots._signed(0.06) == "+0.1 %"


def test_literature_tooltips_of_a_near_oracle_value_have_no_signed_zero():
    systems = [{"system": "S", "task": "t", "oracle": {"Dq": 1854.3, "B": 800.0}, "tol": {"Dq": 0.05, "B": 0.05},
                "paper": {"Dq": 1854.31}, "reported": {"A": {"Dq": 1854.0, "B": 800.0, "ok": True},
                                                       "B": {"Dq": 1854.4, "B": 799.99, "ok": True}, "C": None}}]
    tips = [t for _, _, t in _titled(ET.fromstring(dots.literature_dots(systems)))]
    assert tips and not [t for t in tips if "−0 %" in t or "+0 %" in t]
    assert any(t.endswith("· 0 %") for t in tips)


# ---------------------------------------------------------------- literature_dots

SYSTEMS = [
    {"system": "[V(H2O)6]3+", "oracle": {"Dq": 1000.0, "B": 600.0}, "tol": {"Dq": 0.05, "B": 0.1},
     "reported": {"A": {"Dq": 1020.0, "B": 600.0}, "B": {"Dq": 1200.0, "B": 540.0}, "C": None}},
    {"system": "[Cr<x>]", "oracle": {"Dq": 2000.0, "B": None}, "tol": {"Dq": 0.05, "B": 0.1},
     "reported": {"A": {"Dq": 1000.0, "B": 700.0}, "B": None, "C": {"Dq": 2000.0, "B": None}}},
]


def test_literature_dots_empty():
    assert dots.literature_dots([]) == ""


def test_literature_dots_positions_and_panels():
    svg = dots.literature_dots(SYSTEMS)
    assert svg == dots.literature_dots(SYSTEMS)
    root = ET.fromstring(svg)
    marks = {}
    for el, t in _marks(root):
        m = _m(r"^(.*) · (Dq|B) · ([ABC]):", t)
        marks[m.groups()] = (el, t)
    v = "[V(H2O)6]3+"
    assert (v, "Dq", "C") not in marks and (v, "B", "C") not in marks  # no reported value, no mark
    assert not [k for k in marks if k[0] == "[Cr<x>]" and k[1] == "B"]  # no oracle B, no mark
    xa, xb = _center(marks[(v, "Dq", "A")][0])[0], _center(marks[(v, "Dq", "B")][0])[0]
    assert xa < xb
    # B panel lies right of the Dq panel
    assert _center(marks[(v, "B", "A")][0])[0] > xb
    # deviation printed in the title: 1200 / 1000 - 1 = +20 %
    assert "+20 %" in marks[(v, "Dq", "B")][1]


def test_literature_dots_open_outside_tolerance_and_clamped_at_the_edge():
    root = ET.fromstring(dots.literature_dots(SYSTEMS))
    marks = {}
    for el, t in _marks(root):
        marks[_m(r"^(.*) · (Dq|B) · ([ABC]):", t).groups()] = el
    v = "[V(H2O)6]3+"
    assert "c-A" in marks[(v, "Dq", "A")].get("class")  # +2 % within 5 %
    assert "o-B" in marks[(v, "Dq", "B")].get("class")  # +20 % outside 5 %
    # 1000 against 2000 is −50 %: the left edge of the Dq panel, left of its zero line
    x0 = _f([el for el in root.iter(f"{NS}line") if el.get("class") == "zero"][0], "x1")
    assert _center(marks[("[Cr<x>]", "Dq", "A")])[0] < x0


def test_literature_dots_band_has_tolerance_title():
    root = ET.fromstring(dots.literature_dots(SYSTEMS))
    bands = [t for tag, el, t in _titled(root) if tag == "rect" and el.get("class") == "band"]
    assert any("±5 %" in t for t in bands) and any("±10 %" in t for t in bands)


def test_literature_dots_clamp_beyond_axis():
    s = [{"system": "S", "oracle": {"Dq": 100.0, "B": 100.0}, "tol": {"Dq": 0.05, "B": 0.05},
          "reported": {"A": {"Dq": 1000.0, "B": 10.0}, "B": None, "C": None}}]
    root = ET.fromstring(dots.literature_dots(s))
    xs = sorted(_center(el)[0] for el, _ in _marks(root))
    assert len(xs) == 2
    panels = [el for el in root.iter(f"{NS}line") if el.get("class") == "zero"]
    assert len(panels) == 2
    titles = [t for _, t in _marks(root)]
    assert any("+900 %" in t for t in titles) and any("−90 %" in t for t in titles)


def test_literature_dots_escapes():
    assert "[Cr<x>]" not in dots.literature_dots(SYSTEMS)


def _mark_by_cond(root, cond):
    """The marks of one condition in drawing order (Dq panel first)."""
    return [el for el, t in _marks(root) if re.search(rf" · {cond}:", t)]


def test_literature_dots_clamp_marks_to_the_panel_edges():
    """A value beyond +-50 % sits exactly where +-50 % sits; without the clamp it would leave the panel."""
    def one(a_dq, b_dq):
        return [{"system": "S", "oracle": {"Dq": 100.0, "B": None}, "tol": {"Dq": 0.05, "B": 0.05},
                 "reported": {"A": {"Dq": a_dq, "B": None}, "B": {"Dq": b_dq, "B": None}, "C": None}}]
    for edge_value, far_value in ((150.0, 1000.0), (50.0, 10.0)):
        root = ET.fromstring(dots.literature_dots(one(edge_value, far_value)))
        edge_x = _center(_mark_by_cond(root, "A")[0])[0]
        far_x = _center(_mark_by_cond(root, "B")[0])[0]
        assert far_x == edge_x, (edge_value, far_value, edge_x, far_x)
    # and both sides of the zero line are told apart: the +50 % mark is right of the -50 % mark
    root = ET.fromstring(dots.literature_dots(one(150.0, 50.0)))
    assert _center(_mark_by_cond(root, "B")[0])[0] < _center(_mark_by_cond(root, "A")[0])[0]


def test_literature_dots_clamp_the_paper_diamond_to_the_panel_edge():
    """A paper value at +1000 % sits where the A mark at +50 % (the right edge) sits, not far outside the panel."""
    s = [{"system": "S", "oracle": {"Dq": 100.0, "B": None}, "tol": {"Dq": 0.05, "B": 0.05},
          "paper": {"Dq": 1100.0, "B": None},
          "reported": {"A": {"Dq": 150.0, "B": None}, "B": None, "C": None}}]
    root = ET.fromstring(dots.literature_dots(s))
    edge_x = _center(_mark_by_cond(root, "A")[0])[0]
    diamonds = [el for tag, el, t in _titled(root) if tag == "polygon" and "paper" in t]
    assert len(diamonds) == 1
    assert _center(diamonds[0])[0] == edge_x
    s[0]["paper"]["Dq"] = -900.0  # and the left edge: -50 % on the A side
    s[0]["reported"]["A"]["Dq"] = 50.0
    root = ET.fromstring(dots.literature_dots(s))
    diamond = [el for tag, el, t in _titled(root) if tag == "polygon" and "paper" in t][0]
    assert _center(diamond)[0] == _center(_mark_by_cond(root, "A")[0])[0]


def test_literature_dots_follow_the_ok_flag_of_a_reported_value_over_the_tolerance():
    """The agreement figure passes ok: ok=True is a filled mark and ok=False an open one, whatever the deviation."""
    s = [{"system": "S", "oracle": {"Dq": 100.0, "B": None}, "tol": {"Dq": 0.05, "B": 0.05},
          "reported": {"A": {"Dq": 140.0, "B": None, "ok": True},      # +40 %: outside the tolerance, but ok
                       "B": {"Dq": 101.0, "B": None, "ok": False},    # +1 %: inside the tolerance, but not ok
                       "C": {"Dq": 101.0, "B": None}}}]               # no flag: the tolerance decides
    root = ET.fromstring(dots.literature_dots(s))
    cls = {c: (_mark_by_cond(root, c)[0].get("class") or "").split() for c in "ABC"}
    assert "c-A" in cls["A"] and "o-A" not in cls["A"]
    assert "o-B" in cls["B"] and "c-B" not in cls["B"]
    assert "c-C" in cls["C"] and "o-C" not in cls["C"]


# ---------------------------------------------------------------- two widths


def test_class_dots_are_drawn_at_the_width_they_are_given(fig_width, fits):
    fits(dots.class_dots(ROWS, width=fig_width), fig_width)


def test_class_dot_labels_sit_in_a_column_right_of_the_plot():
    """the k/n labels do not sit on the markers."""
    root = ET.fromstring(dots.class_dots(ROWS, width=464))
    right = max(_center(el)[0] for el, _ in _marks(root))
    labels = [el for el in root.iter(f"{NS}text") if re.search(r"\d+/\d+$", el.text or "")]
    assert labels and all(_f(el, "x") > right + 4 for el in labels)


def test_literature_dots_are_drawn_at_the_width_they_are_given(fig_width, fits):
    fits(dots.literature_dots(SYSTEMS, width=fig_width), fig_width)


def test_literature_dots_draw_the_paper_value_as_its_own_marker():
    s = [{"system": "S", "task": "P-literature_new-01", "oracle": {"Dq": 1000.0, "B": 600.0},
          "tol": {"Dq": 0.05, "B": 0.1}, "paper": {"Dq": 1100.0, "B": 600.0},
          "reported": {"A": {"Dq": 1000.0, "B": 600.0, "ok": True}, "B": None, "C": None}}]
    root = ET.fromstring(dots.literature_dots(s))
    paper = [(el, t) for tag, el, t in _titled(root) if "paper" in t]
    assert len(paper) == 2  # one in the Dq panel, one in the B panel
    assert any("+10 %" in t for _, t in paper)
    assert not any(re.search(r"\bc-[ABC]\b|\bo-[ABC]\b", el.get("class") or "") for el, _ in paper)


def test_literature_dots_print_a_value_beyond_the_axis_at_the_edge():
    """a value beyond ±50 % gets an arrow and its value at the edge."""
    s = [{"system": "S", "oracle": {"Dq": 100.0, "B": 100.0}, "tol": {"Dq": 0.05, "B": 0.05},
          "reported": {"A": {"Dq": 1000.0, "B": 10.0}, "B": None, "C": None}}]
    texts = " ".join(t for t in _texts(ET.fromstring(dots.literature_dots(s))) if t)
    assert "+900 %" in texts and "−90 %" in texts


def test_literature_dots_join_the_edge_values_of_one_row_into_one_label():
    """Values beyond the same edge in one row share one label, each with its condition, so they do not overlap."""
    s = [{"system": "S", "oracle": {"Dq": 100.0, "B": 100.0}, "tol": {"Dq": 0.05, "B": 0.05},
          "reported": {"A": {"Dq": 100.0, "B": 100.0}, "B": {"Dq": 382.0, "B": 100.0}, "C": {"Dq": 413.0, "B": 100.0}},
          "paper": {"Dq": 20.0, "B": 100.0}}]
    texts = [t for t in _texts(ET.fromstring(dots.literature_dots(s))) if t]
    assert "B +282 % · C +313 %" in texts
    assert "paper −80 %" in texts and not any(t == "+282 %" for t in texts)


def test_literature_dots_wrap_long_names_instead_of_cutting_them():
    s = [{"system": "NiWO4 single crystal (wolframite)", "oracle": {"Dq": 100.0, "B": 100.0},
          "tol": {"Dq": 0.05, "B": 0.05}, "reported": {"A": {"Dq": 101.0, "B": 100.0}, "B": None, "C": None}}]
    texts = [t for t in _texts(ET.fromstring(dots.literature_dots(s, width=464))) if t]
    assert not any("…" in t for t in texts)
    assert "wolframite" in " ".join(texts)


def test_literature_marks_link_to_the_task_rows():
    s = [dict(SYSTEMS[0], task="P-literature_all-01")]
    root = ET.fromstring(dots.literature_dots(s, task_href=lambda t: f"#task-{t}"))
    assert "#task-P-literature_all-01" in [a.get("href") for a in root.iter(f"{NS}a")]


def test_dot_percentages_round_a_half_up():
    assert dots._signed(12.5) == "+13 %" and dots._signed(-12.5) == "−13 %" and dots._signed(14.5) == "+15 %"
