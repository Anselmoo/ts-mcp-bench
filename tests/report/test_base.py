"""The rules the report pages share (src/tsbench/report/base.py), and a check that no page keeps a private copy."""
from __future__ import annotations

import ast
import json
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


@pytest.mark.parametrize(("cells", "want"), [
    ([], False), (["True"], True), (["False"], False), (["True", "False"], False), (["1", "true", "False"], True),
    (["True", "False", "False"], False), (["", "True", "True"], True)])
def test_a_task_is_solved_by_more_than_half_of_its_runs(cells, want):
    assert base.solved([{"correct": c} for c in cells]) is want


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
          "as_bool", "_share", "_pilot_hash", "as_run_sets", "_as_run_sets", "is_rate_limited", "_solved"}
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


# ---- the task split of a report
def test_split_tasks_holds_the_records_of_one_split_by_id():
    pilot, conf = base.split_tasks("pilot"), base.split_tasks("confirmatory")
    assert len(pilot) == 50 and len(conf) == 55 and not set(pilot) & set(conf)
    assert {t["split"] for t in conf.values()} == {"confirmatory"}
    assert base.split_tasks() == pilot


def test_split_tasks_drops_a_record_of_another_split(monkeypatch):
    import tsbench.tasks as T
    monkeypatch.setattr(T, "load", lambda split: [{"id": "a", "split": split}, {"id": "b", "split": "other"}])
    assert set(base.split_tasks("confirmatory")) == {"a"}


def test_split_hash_is_the_line_of_its_split():
    lines = dict(reversed(x.split()) for x in resource("tasks/tasks.sha256").read_text(encoding="utf-8").splitlines())
    assert base.split_hash("confirmatory") == lines["confirmatory"] != base.split_hash("pilot") == lines["pilot"]
    assert base.pilot_hash() == base.split_hash("pilot")


def _set_of(tmp_path, name: str, split: str | None) -> RunSet:
    d = tmp_path / name
    d.mkdir()
    if split:
        (d / "MANIFEST.json").write_text(json.dumps({"split": split}), encoding="utf-8")
    return RunSet(name, name, d)


@pytest.mark.parametrize(("split", "recorded", "doi", "refused"), [
    ("pilot", "pilot", None, None),
    ("pilot", None, None, None),
    ("confirmatory", "confirmatory", "10.5281/zenodo.1", None),
    ("confirmatory", None, "10.5281/zenodo.1", None),
    ("confirmatory", "confirmatory", None, "--i-have-preregistered"),
    ("confirmatory", "confirmatory", "not-a-doi", "--i-have-preregistered"),
    ("pilot", "confirmatory", None, "--i-have-preregistered"),
    ("pilot", "confirmatory", "10.5281/zenodo.1", "--split confirmatory"),
    ("confirmatory", "pilot", "10.5281/zenodo.1", "--split pilot"),
])
def test_split_refusal_needs_a_doi_and_the_split_of_the_run_sets(tmp_path, split, recorded, doi, refused):
    got = base.split_refusal([_set_of(tmp_path, "s", recorded)], split, doi)
    assert (got is None) if refused is None else (refused in got)


# ---------------------------------------------------------------- the models


def test_the_models_have_one_order():
    models = ["zeta-1", "claude-opus-5-5", "alpha-2", "claude-sonnet-5-5", "claude-haiku-5-5"]
    assert sorted(models, key=base.model_key) == ["claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5", "alpha-2",
                                                  "zeta-1"]
    assert base.display_model("claude-haiku-5-5") == "Haiku" and base.display_model("gemma-4") == "gemma-4"
    assert base.is_claude("claude-x") and not base.is_claude("gemma-4")


def test_every_page_takes_the_models_and_their_colours_from_one_place():
    from tsbench.report import comparison, coverage, dashboard, gallery, literature, page, science

    assert comparison.model_key is base.model_key and comparison.display_model is base.display_model
    for module in (coverage, dashboard, gallery, science):
        assert module.model_key is base.model_key
    assert literature.comparison.model_key is base.model_key
    assert dashboard.COLORS == comparison.COLORS == {c: page.THEME[f"series-{i}"] for i, c in enumerate("ABC", 1)}


def test_the_coverage_page_lists_the_models_in_that_order(tmp_path, monkeypatch):
    from tsbench.report import coverage
    from tsbench.score import score

    found = [(tmp_path / m, m, "A", "medium", "P-closed_form-01", 1) for m in ("claude-opus-5-5", "gemma-4",
                                                                                 "claude-haiku-5-5")]
    monkeypatch.setattr(score, "check_runs_match", lambda *a: None)
    monkeypatch.setattr(score, "find_transcripts", lambda root: found)
    monkeypatch.setattr(score, "read_transcript", lambda path: None)
    monkeypatch.setattr(score, "not_evaluable_reason", lambda tr: None)
    assert coverage.coverage([tmp_path])["models"] == ["claude-haiku-5-5", "claude-opus-5-5", "gemma-4"]
