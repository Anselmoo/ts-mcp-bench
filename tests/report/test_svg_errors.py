"""Tests for src/tsbench/report/svg/errors.py: the beeswarm of error in tolerance units."""
from __future__ import annotations

import itertools
import math
import xml.etree.ElementTree as ET
from typing import Any

import pytest
from svg_helpers import attr_or_zero as _num
from svg_helpers import root as _root
from svg_helpers import tip as _tip

from tsbench.report.svg import errors as E

NS = "{http://www.w3.org/2000/svg}"
GROUPS: list[dict[str, Any]] = [
    {"cond": "A", "values": [{"task": "a1", "ratio": 0.5}, {"task": "a2", "ratio": 2.0}, {"task": "a3", "ratio": 3.0},
                              {"task": "a4", "ratio": 1.0}, {"task": "a5", "ratio": 1000.0},
                              {"task": "a6", "ratio": 0.0001}]},
    {"cond": "B", "values": [{"task": f"b{i}", "ratio": 5.0} for i in range(7)]},
    {"cond": "C", "values": [{"task": "c1", "ratio": 0.2}, {"task": "c2", "ratio": 0.4},
                              {"task": "c3", "ratio": 60.0}]},
]
for _g in GROUPS:  # the scorer's verdict of each answer: here every answer within its tolerance is correct
    for _v in _g["values"]:
        _v["ok"] = _v["ratio"] <= 1


def _marks(root: ET.Element) -> list[ET.Element]:
    shapes = (f"{NS}circle", f"{NS}rect", f"{NS}polygon")
    return [e for e in root.iter() if e.tag in shapes and e.find(f"{NS}title") is not None
            and "k-" in (e.get("class") or "") and (e.get("class") or "").split()[0][:2] in ("c-", "o-")]


def _center(el: ET.Element) -> tuple[float, float]:
    if el.tag == f"{NS}circle":
        return _num(el, "cx"), _num(el, "cy")
    if el.tag == f"{NS}rect":
        return _num(el, "x") + _num(el, "width") / 2, _num(el, "y") + _num(el, "height") / 2
    pts = [tuple(map(float, p.split(","))) for p in (el.get("points") or "").split()]
    return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)


def _title(el: ET.Element) -> str:
    return _tip(el)


def _mark(root: ET.Element, task: str) -> ET.Element:
    found = [m for m in _marks(root) if task in _title(m).split(" · ")[0].split()]
    assert len(found) == 1, task
    return found[0]


def _tick_x(root: ET.Element, label: str) -> float:
    return next(_num(t, "x") for t in root.iter(f"{NS}text") if "".join(t.itertext()) == label)


def test_one_mark_per_value_filled_when_ok():
    root = _root(E.beeswarm(GROUPS))
    marks = _marks(root)
    assert len(marks) == 6 + 7 + 3
    filled = {_title(m).split()[0]: (m.get("class") or "").startswith("c-") for m in marks}
    assert filled["a1"] and filled["a4"] and filled["a6"] and filled["c1"]
    assert not filled["a2"] and not filled["a5"] and not filled["b0"] and not filled["c3"]


def test_titles_carry_task_and_ratio():
    root = _root(E.beeswarm(GROUPS))
    assert "a2" in _title(_mark(root, "a2")) and "2" in _title(_mark(root, "a2"))
    assert "60" in _title(_mark(root, "c3"))


def test_outside_values_are_drawn_at_the_edge_and_say_so():
    root = _root(E.beeswarm(GROUPS))
    hi, lo = _center(_mark(root, "a5"))[0], _center(_mark(root, "a6"))[0]
    assert "edge" in _title(_mark(root, "a5")) and "1000" in _title(_mark(root, "a5"))
    assert "edge" in _title(_mark(root, "a6"))
    assert "edge" not in _title(_mark(root, "a2"))
    # the axis ends at the cap and the floor: the 1 sits between them on a log scale
    x1 = _tick_x(root, "1")
    assert lo < x1 < hi
    assert (x1 - lo) / (hi - lo) == pytest.approx(math.log10(1 / 1e-3) / math.log10(300 / 1e-3), abs=0.01)


def test_log_axis_is_log_spaced():
    root = _root(E.beeswarm(GROUPS))
    x01, x1, x10 = _tick_x(root, "0.1"), _tick_x(root, "1"), _tick_x(root, "10")
    assert x1 - x01 == pytest.approx(x10 - x1, abs=0.05)
    assert _center(_mark(root, "a2"))[0] == pytest.approx(x1 + (x10 - x1) * math.log10(2), abs=0.1)


def test_marks_of_a_condition_do_not_overlap():
    root = _root(E.beeswarm(GROUPS))
    b = [_center(m) for m in _marks(root) if _title(m).startswith("b")]
    assert len(b) == 7
    for p, q in itertools.combinations(b, 2):
        assert math.dist(p, q) >= 6.0


def test_median_bar_per_condition_at_the_median():
    root = _root(E.beeswarm(GROUPS))
    bars = [e for e in root.iter(f"{NS}rect") if e.get("class") == "c-A"]
    assert len(bars) == 1 and _title(bars[0]).startswith("A median 1.5")
    x1, x10 = _tick_x(root, "1"), _tick_x(root, "10")
    # median of A is (1.0 + 2.0) / 2 = 1.5
    assert _num(bars[0], "x") + _num(bars[0], "width") / 2 == pytest.approx(
        x1 + (x10 - x1) * math.log10(1.5), abs=0.1)
    texts = ["".join(t.itertext()) for t in root.iter(f"{NS}text")]
    assert "n 6" in texts and "median 1.5" in texts and "n 7" in texts


def test_tolerance_zone_ends_at_one():
    root = _root(E.beeswarm(GROUPS))
    zone = next(e for e in root.iter(f"{NS}rect") if "band" in (e.get("class") or "").split())
    assert _num(zone, "x") + _num(zone, "width") == pytest.approx(_tick_x(root, "1"), abs=0.05)


def test_bands_follow_group_order_top_down():
    root = _root(E.beeswarm(GROUPS))
    ys = [_center(_mark(root, t))[1] for t in ("a2", "b0", "c3")]
    assert ys == sorted(ys)


def test_escapes_task_ids():
    g = [{"cond": "A", "values": [{"task": "<x&y>", "ratio": 2.0}]}]
    svg = E.beeswarm(g)
    _root(svg)
    assert "<x&y>" not in svg


def test_empty_and_deterministic():
    assert E.beeswarm([]) == ""
    assert E.beeswarm([{"cond": "A", "values": []}]) == ""
    assert E.beeswarm(GROUPS) == E.beeswarm(list(GROUPS))
    assert 320 <= _num(_root(E.beeswarm(GROUPS)), "width") <= 960


# ---------------------------------------------------------------- two widths


def test_swarm_is_drawn_at_the_width_it_is_given(fig_width, fits):
    fits(E.beeswarm(GROUPS, width=fig_width), fig_width)


def test_a_mark_is_filled_from_ok_never_from_the_ratio():
    groups = [{"cond": "A", "values": [{"task": "t-pass-far", "ratio": 4.0, "ok": True},
                                       {"task": "t-fail-near", "ratio": 0.5, "ok": False}]}]
    root = _root(E.beeswarm(groups))
    assert (_mark(root, "t-pass-far").get("class") or "").startswith("c-")
    assert (_mark(root, "t-fail-near").get("class") or "").startswith("o-")


def test_median_has_two_significant_digits():
    """"median 0.00777" is printed as "median 0.0078"."""
    groups = [{"cond": "A", "values": [{"task": f"t{i}", "ratio": r, "ok": True}
                                       for i, r in enumerate((0.00777, 0.00777, 0.00777))]}]
    texts = ["".join(t.itertext()) for t in _root(E.beeswarm(groups)).iter(f"{NS}text")]
    assert "median 0.0078" in texts and not any("0.00777" in t for t in texts)


def test_task_marks_link_to_the_task_rows():
    svg = E.beeswarm(GROUPS, task_href=lambda t: f"#task-{t}")
    root = _root(svg)
    links = [a.get("href") for a in root.iter(f"{NS}a")]
    assert "#task-a2" in links and "#task-c3" in links
    assert len(_marks(root)) == 6 + 7 + 3


def test_a_row_names_the_answers_it_leaves_out():
    groups = [{"cond": "A", "values": [{"task": "a1", "ratio": 0.5, "ok": True}], "n_runs": 3},
              {"cond": "B", "values": [{"task": "b1", "ratio": 2.0, "ok": False}], "n_runs": 1}]
    texts = ["".join(t.itertext()) for t in _root(E.beeswarm(groups)).iter(f"{NS}text")]
    assert "n 1 of 3" in texts and "n 1" in texts


def test_a_ratio_label_rounds_a_half_up():
    assert [E._num(v) for v in (2.25, 2.35, 100.5, 101.5, 0.125, 0.135)] == ["2.3", "2.4", "101", "102", "0.13", "0.14"]


def test_bands_of_several_models_carry_their_label_and_name_the_model_in_the_tips():
    groups = [{"cond": "A", "model": "m-long-name", "label": "m-long-name · A", "n_runs": 3,
               "values": [{"task": "t1", "ratio": 2.0, "ok": False}]},
              {"cond": "A", "model": "m2", "label": "m2 · A", "n_runs": 3,
               "values": [{"task": "t1", "ratio": 0.5, "ok": True}]}]
    svg = E.beeswarm(groups)
    assert ">m-long-name · A<" in svg and ">m2 · A<" in svg
    assert "t1 · m-long-name · A · error/tolerance 2" in svg and "m2 · A median 0.5" in svg
