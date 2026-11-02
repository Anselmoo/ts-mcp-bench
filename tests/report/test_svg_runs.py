"""Tests for src/tsbench/report/svg/runs.py: static parallel coordinates of the runs."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from tsbench.report.svg import runs

NS = "{http://www.w3.org/2000/svg}"
AXES = [("turns", "turns"), ("tokens", "output tokens"), ("cost", "cost (USD)")]
RUNS = [
    {"cond": "A", "task": "P-a-01", "correct": True, "values": {"turns": 2, "tokens": 1000.0, "cost": 0.01}},
    {"cond": "C", "task": "P-a-02", "correct": False, "values": {"turns": 12, "tokens": 5000.0, "cost": 0.25}},
    {"cond": "B", "task": "P-a<3>", "correct": True, "values": {"turns": 7, "tokens": None, "cost": 0.1}},
]


def _paths(root):
    out = {}
    for el in root.iter(f"{NS}path"):
        t = el.find(f"{NS}title")
        out[t.text.split(" · ")[0]] = el
    return out


def _pts(d):
    return [tuple(map(float, m)) for m in re.findall(r"[ML]\s*(-?[\d.]+)[ ,](-?[\d.]+)", d)]


def test_empty():
    assert runs.parallel_coords([], AXES) == ""
    assert runs.parallel_coords(RUNS, []) == ""


def test_one_path_per_run_with_condition_class_and_dash_when_wrong():
    svg = runs.parallel_coords(RUNS, AXES)
    assert svg == runs.parallel_coords(RUNS, AXES)
    assert "<script" not in svg
    paths = _paths(ET.fromstring(svg))
    assert len(paths) == 3
    assert paths["P-a-01"].get("class") == "flow c-A"
    assert paths["P-a-02"].get("class") == "flow c-C"
    assert paths["P-a-02"].get("stroke-dasharray")
    assert paths["P-a-01"].get("stroke-dasharray") is None


def test_values_scale_between_axis_min_and_max():
    paths = _paths(ET.fromstring(runs.parallel_coords(RUNS, AXES)))
    a, c = _pts(paths["P-a-01"].get("d")), _pts(paths["P-a-02"].get("d"))
    assert len(a) == 3 and len(c) == 3
    assert [p[0] for p in a] == [p[0] for p in c]
    assert a[0][0] < a[1][0] < a[2][0]
    # turns: 2 is the minimum, 12 the maximum: the lowest and the highest y of the axis
    assert a[0][1] > c[0][1]
    assert a[1][1] > c[1][1] and a[2][1] > c[2][1]


def test_none_breaks_the_line():
    paths = _paths(ET.fromstring(runs.parallel_coords(RUNS, AXES)))
    d = paths["P-a<3>"].get("d")
    assert d.count("M") == 2
    assert len(_pts(d)) == 2


def test_title_has_exact_values_and_outcome():
    svg = runs.parallel_coords(RUNS, AXES)
    root = ET.fromstring(svg)
    t = [x.text for x in root.iter(f"{NS}title") if x.text and x.text.startswith("P-a-02")][0]
    assert "C" in t and "not correct" in t and "output tokens 5\u2009000" in t and "cost (USD) 0.25" in t


def test_axis_labels_and_min_max_ticks():
    root = ET.fromstring(runs.parallel_coords(RUNS, AXES))
    texts = [el.text for el in root.iter(f"{NS}text")]
    for label in ("turns", "output tokens", "cost (USD)"):
        assert label in texts
    for tick in ("2", "12", "1\u2009000", "5\u2009000", "0.01", "0.25"):
        assert tick in texts, tick


def test_escapes_task_names():
    svg = runs.parallel_coords(RUNS, AXES)
    assert "P-a<3>" not in svg and "P-a&lt;3&gt;" in svg


def test_log_axis_places_geometric_mean_in_the_middle():
    rs = [{"cond": "A", "task": f"t{v}", "correct": True, "values": {"x": v}} for v in (1.0, 10.0, 100.0)]
    paths = _paths(ET.fromstring(runs.parallel_coords(rs, [("x", "x")], log_axes=("x",))))
    ys = {k: _pts(p.get("d"))[0][1] for k, p in paths.items()}
    assert abs((ys["t1.0"] + ys["t100.0"]) / 2 - ys["t10.0"]) < 0.01


# ---------------------------------------------------------------- two widths


def test_parallel_coordinates_are_drawn_at_the_width_they_are_given(fig_width, fits):
    fits(runs.parallel_coords(RUNS, AXES, width=fig_width), fig_width)
