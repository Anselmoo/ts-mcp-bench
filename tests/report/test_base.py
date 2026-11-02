"""The rules the report pages share (src/tsbench/report/base.py), and a check that no page keeps a private copy."""
from __future__ import annotations

import ast
import pathlib

import pytest

from tsbench.core import resource
from tsbench.report import base
from tsbench.score.run_sets import RunSet

REPORT = pathlib.Path(__file__).resolve().parents[2] / "src" / "tsbench" / "report"


@pytest.mark.parametrize(("cell", "want"), [
    ("True", True), ("true", True), ("TRUE", True), (" true ", True), ("1", True), (True, True), (1, True),
    ("False", False), ("FALSE", False), ("0", False), (False, False),
    ("", None), (None, None), ("yes", None), ("nan", None),
])
def test_boolean_cells_read_the_same_in_any_spelling(cell, want):
    assert base.as_bool(cell) is want
    assert base.is_true(cell) is (want is True)


@pytest.mark.parametrize(("cell", "want"), [
    ("1.5", 1.5), (2, 2.0), ("-3e2", -300.0), (" 4 ", 4.0), ("", None), (None, None), ("x", None), ("nan", None),
    (float("nan"), None),
])
def test_number_cells_leave_out_empty_text_and_nan(cell, want):
    assert base.as_number(cell) == want


def test_median_ignores_missing_values():
    assert base.median([3, None, 1, 2]) == 2 and base.median([1, 2, None, 3, 4]) == 2.5
    assert base.median([None]) is None and base.median([]) is None
    rows = [{"x": "1"}, {"x": ""}, {"x": "5"}, {"x": "nan"}, {}]
    assert base.median_of(rows, "x") == 3.0 and base.median_of(rows, "missing") is None


def _runs(*cells):
    """(task, correct cell) -> rows."""
    return [{"task_id": t, "correct": c} for t, c in cells]


def test_share_counts_correct_runs_with_a_task_clustered_interval():
    got = base.share(_runs(("a", "True"), ("a", "False"), ("b", "TRUE"), ("b", "true"), ("c", "False")))
    assert got is not None
    assert (got["k"], got["n"], got["tasks"], got["ids"]) == (3, 5, 3, ["a", "b", "c"])
    assert got["p"] == pytest.approx(0.6) and 0.0 <= got["lo"] <= got["p"] <= got["hi"] <= 1.0
    assert base.share([]) is None


def test_share_is_the_one_computation_of_the_pages_and_reads_any_spelling_of_true():
    assert (base.share(_runs(("a", "TRUE"), ("b", "True"))) or {}).get("k") == 2


def test_the_hero_of_the_dashboard_and_the_shares_of_the_full_report_agree_on_a_spreadsheet_saved_scores_csv():
    """scores.csv saved by a spreadsheet says `TRUE`: every page counts it as correct."""
    from tsbench.report import dashboard, facts, science
    rows = []
    for i, cell in enumerate(["TRUE", "true", "True", "FALSE"]):
        rows.append({"model": "m", "condition": "C", "_cond": "C", "task_id": f"P-x-0{i % 2}", "correct": cell,
                     "_task": {"id": "x"}, "_na": "", "_category": "correct" if cell != "FALSE" else "wrong"})
    hero = dashboard._hero(rows)
    assert hero[0]["text"].startswith("3 of 4 correct")
    got = facts._shares(science._Runs({"rows": rows}), "m", ["C"])
    assert [(s["k"], s["n"]) for s in got] == [(3, 4)]


def test_run_sets_and_plain_folders_become_run_sets(tmp_path):
    rs = RunSet("named", "Named", tmp_path / "x")
    got = base.as_run_sets([rs, tmp_path / "plain", str(tmp_path / "text")])
    assert got[0] is rs
    assert [(r.name, r.title, r.path) for r in got[1:]] == [
        ("plain", "plain", tmp_path / "plain"), ("text", "text", tmp_path / "text")]
    assert base.as_run_sets([]) == []


def test_pilot_hash_is_the_pilot_line_of_the_hash_file():
    line = next(x for x in resource("tasks/tasks.sha256").read_text(encoding="utf-8").splitlines()
                if x.split()[-1:] == ["pilot"])
    got = base.pilot_hash()
    assert got == line.split()[0] and len(got) == 64


def test_pilot_hash_is_none_without_a_pilot_line(monkeypatch):
    class Fake:
        def read_text(self, encoding):
            return "abc  confirmatory\n"
    monkeypatch.setattr(base, "resource", lambda name: Fake())
    assert base.pilot_hash() is None


def test_the_harness_categories_are_the_four_of_the_taxonomy():
    assert base.HARNESS == {"no_result", "max_turns", "budget", "api_error"}


@pytest.mark.parametrize(("result", "want"), [
    ({"is_error": True, "api_error_status": 429}, "rate_limited"),
    ({"is_error": True, "api_error_status": "429"}, "rate_limited"),
    ({"is_error": True, "result": "failed (429)"}, "rate_limited"),
    ({"is_error": True, "api_error_status": 502}, "api_error"),
    ({"is_error": True, "terminal_reason": "api_error"}, "api_error"),
    ({"is_error": True, "result": "API Error: connection reset"}, "api_error"),
    ({"is_error": True, "subtype": "error_max_turns", "terminal_reason": "max_turns"}, None),
    ({"is_error": False, "api_error_status": 429}, None), (None, None),
])
def test_not_evaluable_is_the_rule_of_the_scorer(result, want):
    assert base.not_evaluable(result) == want


# ---- no private copies
def _defined(tree: ast.AST) -> set[str]:
    names = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign):
            names |= {t.id for t in n.targets if isinstance(t, ast.Name)}
    return names


SHARED = {"HARNESS", "_HARNESS", "HARNESS_CATEGORIES", "_median", "_bool", "_true", "_as_float", "as_number",
          "as_bool", "_share", "_pilot_hash", "as_run_sets", "_as_run_sets", "is_rate_limited"}
SHARED_IN = {"dashboard.py": {"_num"}, "comparison.py": {"_num"}, "functional.py": {"_yes"}, "method.py": {"_row"}}
# the {item, value, source} row is facts.distinct_row; no page keeps a local `row` function of its own beside it
# run_figures._num and provenance._num read JSON values, method._yes reads the manifest word `yes`: other rules


def test_no_report_page_defines_a_private_copy_of_a_shared_rule():
    copies = {}
    for path in sorted(REPORT.glob("*.py")):
        if path.name == "base.py":
            continue
        got = _defined(ast.parse(path.read_text(encoding="utf-8"))) & (SHARED | SHARED_IN.get(path.name, set()))
        if got:
            copies[path.name] = sorted(got)
    assert copies == {}


def test_the_platform_table_has_no_local_copy_of_the_distinct_row():
    tree = ast.parse((REPORT / "facts.py").read_text(encoding="utf-8"))
    local = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "row"]
    assert local == []
