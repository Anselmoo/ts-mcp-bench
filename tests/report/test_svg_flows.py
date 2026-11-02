"""Tests for src/tsbench/report/svg/flows.py: sunburst and the path table."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any

from svg_helpers import match as _m
from svg_helpers import root as _root

from tsbench.report.svg import flows

NS = "{http://www.w3.org/2000/svg}"


def _titled(root):
    out = []
    for el in root.iter():
        t = el.find(f"{NS}title")
        if t is not None and el is not root:
            out.append((el.tag.removeprefix(NS), el, t.text or ""))
    return out


def _runs(title):
    return int(_m(r"(\d+) runs?", title).group(1))


# ---------------------------------------------------------------- sunburst and path rows

PATHS: list[dict[str, Any]] = (
    [{"cond": "C", "calls": ["Bash", "StructuredOutput"], "correct": True}] * 3
    + [{"cond": "C", "calls": ["Bash", "StructuredOutput"], "correct": False}]
    + [{"cond": "C", "calls": ["ts_fit", "ts_fit", "StructuredOutput"], "correct": True}] * 2
    + [{"cond": "B", "calls": ["Bash", "Bash", "StructuredOutput"], "correct": False}]
    + [{"cond": "B", "calls": ["Bash"], "correct": True}]
)


def test_sunburst_empty():
    assert flows.sunburst([]) == ""


def test_sunburst_counts_in_titles():
    svg = flows.sunburst(PATHS)
    assert svg == flows.sunburst(PATHS)
    root = _root(svg)
    titles = [t for _, _, t in _titled(root)]
    assert any(t.startswith("C: 6 runs") for t in titles)
    assert any(t.startswith("B: 2 runs") for t in titles)
    assert any(t.startswith("C → Bash: 4 runs") for t in titles)
    assert any(t.startswith("C → Bash → StructuredOutput → correct: 3 runs") for t in titles)
    assert any(t.startswith("C → Bash → StructuredOutput → not correct: 1 run") for t in titles)
    assert any(t.startswith("B → Bash → correct: 1 run") for t in titles)


def test_sunburst_arcs_are_paths_and_condition_ring_sums_to_all_runs():
    root = _root(flows.sunburst(PATHS))
    ring0 = [t for tag, _, t in _titled(root) if tag == "path" and re.match(r"^[ABC]: \d+ runs", t)]
    assert sum(_runs(t) for t in ring0) == len(PATHS)


def test_sunburst_depth_cuts_long_paths():
    long = [{"cond": "C", "calls": ["a", "b", "c", "d", "e"], "correct": True}] * 2
    svg = flows.sunburst(long, depth=2)
    titles = [t for _, _, t in _titled(_root(svg))]
    assert any(t.startswith("C → a → b → … → correct: 2 runs") for t in titles)
    assert not any(" → c →" in t for t in titles)


def test_sunburst_single_sector_full_circle_is_valid():
    one = [{"cond": "C", "calls": ["Bash"], "correct": True}] * 3
    root = _root(flows.sunburst(one))
    assert "nan" not in ET.tostring(root, encoding="unicode").lower()


def test_sunburst_escapes_names():
    svg = flows.sunburst([{"cond": "C", "calls": ["<b>"], "correct": True}])
    assert "<b>" not in svg
    assert "&lt;b&gt;" in svg


def test_path_rows_order_and_counts():
    rows = flows.path_rows(PATHS)
    assert rows[0] == {"cond": "C", "path": "Bash → StructuredOutput", "runs": 4, "correct": 3}
    assert rows[1] == {"cond": "C", "path": "ts_fit → ts_fit → StructuredOutput", "runs": 2, "correct": 2}
    assert [r["runs"] for r in rows] == [4, 2, 1, 1]
    assert {"cond": "B", "path": "Bash → Bash → StructuredOutput", "runs": 1, "correct": 0} in rows
    assert sum(r["runs"] for r in rows) == len(PATHS)


def test_path_rows_top_and_empty():
    assert flows.path_rows([]) == []
    rows = flows.path_rows(PATHS, top=2)
    assert [r["runs"] for r in rows] == [4, 2, 2]  # the two most frequent paths and one remainder row
    assert flows.path_rows([{"cond": "C", "calls": [], "correct": False}])[0]["path"] == "(no call)"


# ---------------------------------------------------------------- two widths


def test_sunburst_is_drawn_at_the_width_it_is_given(fig_width, fits):
    fits(flows.sunburst(PATHS, width=fig_width), fig_width)


def test_sunburst_has_no_arc_text_but_the_condition_letters():
    """no rotated text on the arcs; the inner ring carries its condition letter; the legend has two rows."""
    root = _root(flows.sunburst(PATHS, width=464))
    texts = list(root.iter(f"{NS}text"))
    assert not [t for t in texts if "rotate" in (t.get("transform") or "")]
    tools = {c for p in PATHS for c in p["calls"]}
    assert not [t.text for t in texts if t.text in tools]  # the call names are in the path table
    letters = [t.text for t in texts if t.text in ("B", "C")]
    assert sorted(set(letters)) == ["B", "C"]
    outcome_y = {t.get("y") for t in texts if t.text in ("correct", "not correct")}
    cond_y = {t.get("y") for t in texts if t.text in ("B", "C")}
    assert outcome_y and not outcome_y & cond_y  # condition and outcome are two legend rows


def test_path_rows_sum_to_the_runs_with_a_remainder_row_for_the_paths_beyond_the_top():
    """The runs column adds up to the number of runs (the sunburst's centre); the rows beyond `top` are one row."""
    rows = flows.path_rows(PATHS, top=2)
    assert sum(r["runs"] for r in rows) == len(PATHS) == 8
    other = rows[-1]
    assert other["other"] is True and other["path"] == "2 other paths"
    assert (other["runs"], other["correct"]) == (2, 1) and other["cond"] == ""
    assert all("other" not in r for r in rows[:-1])
    assert sum(r["correct"] for r in rows) == sum(bool(p["correct"]) for p in PATHS)
    assert flows.path_rows(PATHS, top=1)[-1]["path"] == "3 other paths"


def test_path_rows_have_no_remainder_when_every_path_is_listed():
    rows = flows.path_rows(PATHS)
    assert len(rows) == 4 and not any("other" in r for r in rows)
    assert flows.path_rows(PATHS, top=4) == rows


def test_path_rows_fold_runs_of_one_tool():
    """a run of one tool is written `name ×n`."""
    paths = [{"cond": "C", "calls": ["ts_terms_table_data"] * 9 + ["StructuredOutput"], "correct": True}]
    rows = flows.path_rows(paths)
    assert rows[0]["path"].count("ts_terms_table_data") == 1 and "×9" in rows[0]["path"]
