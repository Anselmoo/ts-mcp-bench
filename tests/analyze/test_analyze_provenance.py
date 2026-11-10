"""Tests for src/tsbench/analyze/provenance.py: where each number of an answer came from."""
from __future__ import annotations

import json
from typing import cast

import pytest
from analyze_runs import bash, mcp, read_csv, res, result, use, write_run, write_scores

from tsbench.analyze import provenance
from tsbench.analyze.common import load_tasks
from tsbench.score.extract import Transcript, read_transcript
from tsbench.score.numeric import trace
from tsbench.score.score import extract_answer

TASKS = load_tasks("pilot")
FIT = json.dumps({"result": {"d_count": 2, "fitted_Dq": 2043.7, "fitted_B": 763.8, "fitted_C": 3801,
                             "r_squared": 0.99}})


def _b_run(tmp_path, answer):
    code = "python3 - <<'EOF'\nB = 702.0\nprint('Dq', 2 * 1022.0, 'B', B)\nEOF"
    return write_run(tmp_path, "m/B/medium/P-numerical-01-k1", [*bash("a", code, "Dq 2044.0 B 702.0"),
                                                                 *result(answer)])


def test_numbers_of_a_b_run(tmp_path):
    answer = {"Dq": 2044.0, "B": 702.0, "C": 3100.0, "out_of_scope": False, "reason": "fit"}
    path = _b_run(tmp_path, answer)
    rows = provenance.numbers_of(path, read_transcript(path), TASKS["P-numerical-01"])
    by = {r["path"]: r for r in rows}
    assert set(by) == {"Dq", "B", "C"}
    assert by["Dq"]["source"] == "tool" and by["Dq"]["source_step"] == 0 and by["Dq"]["source_tool"] == "Bash"
    assert by["B"]["source"] == "typed" and by["B"]["source_step"] is None  # printed back from a typed literal
    assert by["C"]["source"] == "none" and by["C"]["traced"] is False
    assert by["Dq"]["traced"] is True and by["B"]["traced"] is True
    assert by["Dq"]["fit_relation"] == "" and by["Dq"]["fit_value"] is None  # no MCP fit in B


def test_the_traced_flags_agree_with_the_scorer(tmp_path):
    answer = {"Dq": 2044.0, "B": 702.0, "C": 3100.0, "out_of_scope": False, "reason": "fit"}
    path = _b_run(tmp_path, answer)
    tr = read_transcript(path)
    rows = provenance.numbers_of(path, tr, TASKS["P-numerical-01"])
    got = extract_answer(TASKS["P-numerical-01"], tr).answer
    assert sum(r["traced"] for r in rows if r["path"] in ("Dq", "B", "C")) == trace(got, tr)[1] == 2


def test_a_number_given_in_the_prompt_is_marked():
    # the prompt of P-crossover-01 writes "C = 3 509 cm-1" with a space between the digit groups
    task = TASKS["P-crossover-01"]
    assert provenance.in_prompt(3509.0, task) and provenance.in_prompt(807.0, task)
    assert not provenance.in_prompt(1479.4, task) and not provenance.in_prompt(5.0, None)


@pytest.mark.parametrize("dq,b,relation_dq,relation_b", [
    (2044.0, 763.8, "copied", "copied"),
    (2044.0, 800.0, "copied", "changed"),
])
def test_condition_c_compares_with_the_fit(tmp_path, dq, b, relation_dq, relation_b):
    answer = {"Dq": dq, "B": b, "C": None, "out_of_scope": False, "reason": "fit"}
    path = write_run(tmp_path, "m/C/medium/P-numerical-01-k1", [
        *mcp("a", "ts_fit_spectrum", {"d_count": 2}, json.dumps({"result": {"error": "Fitting failed"}})),
        *mcp("b", "ts_fit_spectrum", {"d_count": 2}, FIT), *result(answer)])
    by = {r["path"]: r for r in provenance.numbers_of(path, read_transcript(path), TASKS["P-numerical-01"])}
    assert by["Dq"]["fit_relation"] == relation_dq and by["B"]["fit_relation"] == relation_b
    assert by["Dq"]["fit_value"] == 2043.7 and by["B"]["fit_value"] == 763.8
    assert by["B"]["fit_rel_diff"] == pytest.approx(abs(b - 763.8) / 763.8)


def test_a_c_run_without_a_fit(tmp_path):
    answer = {"Dq": 2044.0, "B": 702.0, "C": None, "out_of_scope": False, "reason": "fit"}
    path = write_run(tmp_path, "m/C/medium/P-numerical-01-k1", [
        *mcp("a", "ts_terms_table_data", {"d_count": 2}, '{"rows": [1, 2]}'), *result(answer)])
    by = {r["path"]: r for r in provenance.numbers_of(path, read_transcript(path), TASKS["P-numerical-01"])}
    assert by["Dq"]["fit_relation"] == "no_fit" and by["Dq"]["source"] == "none"


def test_a_number_a_tool_only_echoes_from_its_input_is_typed(tmp_path):
    answer = {"Dq": 607.0, "B": 779.0, "C": None, "out_of_scope": False, "reason": "scan"}
    echo = json.dumps({"result": {"d_count": 5, "Dq": 607, "B": 779, "C": 3100, "rows": [{"energy_cm": 18950.5}]}})
    path = write_run(tmp_path, "m/C/medium/P-numerical-01-k1", [
        *mcp("a", "ts_terms_table_data", {"d_count": 5, "Dq": 607, "B": 779, "C": 3100}, echo), *result(answer)])
    by = {r["path"]: r for r in provenance.numbers_of(path, read_transcript(path), TASKS["P-numerical-01"])}
    assert by["Dq"]["source"] == "typed" and by["B"]["source"] == "typed" and by["Dq"]["source_step"] is None
    assert by["Dq"]["traced"] is True  # the scorer's test still finds it in a tool result


def test_an_inline_python_literal_is_typed(tmp_path):
    answer = {"Dq": 2044.0, "B": 702.0, "C": None, "out_of_scope": False, "reason": "fit"}
    path = write_run(tmp_path, "m/B/medium/P-numerical-01-k1", [
        *bash("a", "python3 -c 'print(2044.0, 702.0 * 1)'", "2044.0 702.0"), *result(answer)])
    by = {r["path"]: r for r in provenance.numbers_of(path, read_transcript(path), TASKS["P-numerical-01"])}
    assert by["Dq"]["source"] == "typed" and by["B"]["source"] == "typed"


def test_the_origin_of_a_run_answer():
    assert provenance.origin({"source": "tool", "fit_relation": "copied"}) == "fit_copied"
    assert provenance.origin({"source": "none", "fit_relation": "changed"}) == "fit_changed"
    assert provenance.origin({"source": "tool", "fit_relation": "changed"}) == "fit_other_tool"
    assert provenance.origin({"source": "typed", "fit_relation": "changed"}) == "fit_changed"
    assert provenance.origin({"source": "tool", "fit_relation": ""}) == "tool"
    assert provenance.origin({"source": "none", "fit_relation": "no_fit"}) == "none"
    assert provenance.origin(None) == "null"


def test_main_writes_numbers_runs_and_groups(tmp_path, capsys):
    runs, out = tmp_path / "runs", tmp_path / "out"
    _b_run(runs, {"Dq": 2044.0, "B": 702.0, "C": None, "out_of_scope": False, "reason": "fit"})
    write_run(runs, "m/C/medium/P-numerical-01-k1", [
        *mcp("b", "ts_fit_spectrum", {"d_count": 2}, FIT),
        *result({"Dq": 2044.0, "B": 800.0, "C": None, "out_of_scope": False, "reason": "fit"})])
    write_scores(runs, [{"run_id": "m/B/medium/P-numerical-01-k1", "correct": "True", "n_reported": "2",
                         "n_traced": "2"},
                        {"run_id": "m/C/medium/P-numerical-01-k1", "correct": "False", "n_reported": "2",
                         "n_traced": "2"}])
    assert provenance.main(["--runs", str(runs), "--out", str(out)]) == 0
    nums = read_csv(out / "numbers.csv")
    assert [(n["run_id"].split("/")[1], n["path"], n["source"]) for n in nums] == [
        ("B", "Dq", "tool"), ("B", "B", "typed"), ("C", "Dq", "tool"), ("C", "B", "none")]
    run_rows = read_csv(out / "runs.csv")
    assert [(r["dq_origin"], r["b_origin"]) for r in run_rows] == [("tool", "typed"), ("fit_copied", "fit_changed")]
    assert [(r["n_traced"], r["n_traced_scores"]) for r in run_rows] == [("2", "2"), ("1", "2")]
    groups = read_csv(out / "by_group.csv")
    c_b = [g for g in groups if g["condition"] == "C" and g["parameter"] == "B"]
    assert [(g["origin"], g["n_runs"], g["n_correct"]) for g in c_b] == [("fit_changed", "1", "0")]
    assert "provenance" in (out / "README.md").read_text(encoding="utf-8").lower()
    assert "numbers: 4" in capsys.readouterr().out


@pytest.mark.parametrize("x,v,want", [
    (0.0, 0.0, True), (1.0, 0.0, False), (-0.0, 0.0, True),
    (1.0, 1.0, True), (1.004, 1.0, True), (1.006, 1.0, False), (0.0, 1.0, False),
    (1005.0, 1000.0, True), (995.0, 1000.0, True), (1005.5, 1000.0, False),  # the tolerance itself still matches
    (-1000.0, 1000.0, True), (1000.0, -1000.0, True),
])
def test_the_match_of_two_numbers(x, v, want):
    assert provenance._matches(x, v) is want


def test_the_relation_to_a_fitted_zero_has_no_relative_difference():
    assert provenance._fit_relation("Dq", 5.0, [{"Dq": 0.0}]) == ("changed", 0.0, None)
    assert provenance._fit_relation("Dq", 0.0, [{"Dq": 0.0}]) == ("copied", 0.0, None)


def test_a_copied_value_may_match_an_earlier_fit():
    assert provenance._fit_relation("B", 700.0, [{"B": 700.0}, {"Dq": 1.0}, {"B": 800.0}]) == ("copied", 800.0, 0.125)
    assert provenance._fit_relation("C", 700.0, [{"B": 700.0}]) == ("no_fit", None, None)


def test_the_source_prefers_the_last_step_that_ran_a_script():
    def step(scripts=(), runs=(), command=""):
        return {"command": command, "scripts": list(scripts), "runs": list(runs)}

    value = {"value": 2044.0, "weak": False, "steps": [0, 1, 2]}
    assert provenance._source(value, [step(scripts=[1]), step(runs=[1]), step()]) == 1
    assert provenance._source(value, [step(runs=[1]), step(scripts=[1]), step()]) == 1
    assert provenance._source(value, [step(), step(), step()]) == 2
    assert provenance._source(value, [step(runs=[1]), step(), step(runs=[1], command="2044.0")]) == 0
    assert provenance._source({**value, "weak": True}, [step(), step(), step()]) is None


def _fit(i, name, content):
    return [use(i, name, {}), res(i, content)]


def test_fits_read_only_the_fit_tool_and_go_on_after_a_bad_result(tmp_path):
    good = json.dumps({"result": {"fitted_Dq": 1.0}})
    fit = "mcp__tanabesugano__ts_fit_spectrum"
    path = write_run(tmp_path, "m/C/medium/P-numerical-01-k1", [
        *_fit("a", "mcp__tanabesugano__ts_terms_table_data", good),
        *_fit("b", "mcp__a__b__ts_fit_spectrum", good),  # the third part after the split is not the tool name
        *_fit("c", fit, "not json"),
        *_fit("d", fit, "[1, 2]"),
        *_fit("e", fit, '{"result": 3}'),
        *_fit("f", fit, json.dumps({"fitted_B": 2, "fitted_C": True})),  # no `result` wrapper; a flag is no number
        *_fit("g", "ts_fit_spectrum", json.dumps({"result": {"fitted_C": 3.5}, "fitted_B": 9})),
        *_fit("h", fit, json.dumps({"result": {"fitted_Dq": "x"}})),
        *_fit("i", fit, good)])
    assert provenance.fits(read_transcript(path)) == [{"B": 2.0}, {"C": 3.5}, {"Dq": 1.0}]


def test_every_field_of_a_number_row(tmp_path):
    answer = {"Dq": 2044.0, "B": 702.0, "C": 3100.0, "out_of_scope": False, "reason": "fit"}
    path = _b_run(tmp_path, answer)
    rows = provenance.numbers_of(path, read_transcript(path), TASKS["P-numerical-01"])
    assert rows[0] == {"path": "Dq", "value": 2044.0, "source": "tool", "source_step": 0, "source_tool": "Bash",
                       "n_linked_steps": 1, "weak": False, "traced": True, "in_prompt": False, "fit_value": None,
                       "fit_relation": "", "fit_rel_diff": None}
    assert rows[2] == {"path": "C", "value": 3100.0, "source": "none", "source_step": None, "source_tool": "",
                       "n_linked_steps": 0, "weak": False, "traced": False, "in_prompt": False, "fit_value": None,
                       "fit_relation": "", "fit_rel_diff": None}


def test_a_path_that_is_no_parameter_has_no_traced_flag(monkeypatch):
    values = [{"path": "points[0].e_over_b", "value": 1.5, "weak": False, "steps": []}]
    monkeypatch.setattr(provenance, "solution_path", lambda *a, **k: {"values": values, "steps": []})
    assert provenance.numbers_of("m/B/medium/x-k1.jsonl", cast(Transcript, None), None) == [
        {"path": "points[0].e_over_b", "value": 1.5, "source": "none", "source_step": None, "source_tool": "",
         "n_linked_steps": 0, "weak": False, "traced": None, "in_prompt": False, "fit_value": None,
         "fit_relation": "", "fit_rel_diff": None}]


def test_a_small_integer_a_step_printed_is_weak(tmp_path):
    answer = {"Dq": 12.0, "B": 702.0, "C": None, "out_of_scope": False, "reason": "fit"}
    path = write_run(tmp_path, "m/B/medium/P-numerical-01-k1", [*bash("a", "python3 a.py", "12 702.5"),
                                                                 *result(answer)])
    by = {r["path"]: r for r in provenance.numbers_of(path, read_transcript(path), TASKS["P-numerical-01"])}
    assert (by["Dq"]["source"], by["Dq"]["weak"], by["Dq"]["source_step"]) == ("weak", True, None)
    assert by["Dq"]["n_linked_steps"] == 1 and by["B"]["source"] == "tool"


def test_a_small_integer_no_step_printed_is_none(tmp_path):
    answer = {"Dq": 12.0, "B": 702.0, "C": None, "out_of_scope": False, "reason": "fit"}
    path = write_run(tmp_path, "m/B/medium/P-numerical-01-k1", [*bash("a", "python3 a.py", "5"), *result(answer)])
    by = {r["path"]: r for r in provenance.numbers_of(path, read_transcript(path), TASKS["P-numerical-01"])}
    assert (by["Dq"]["source"], by["Dq"]["weak"]) == ("none", True)


def test_numbers_of_uses_the_answer_of_the_scorer_and_the_given_transcript(tmp_path):
    answer = {"Dq": 2044.0, "B": 702.0, "C": None, "out_of_scope": False, "reason": "fit"}
    events = [*bash("a", "python3 a.py", "2044.0"), *result(None)]
    events[-1]["result"] = json.dumps(answer)  # only the scorer reads the answer from the final text
    path = write_run(tmp_path, "m/B/medium/P-numerical-01-k1", events)
    tr = read_transcript(path)
    path.unlink()  # the parsed transcript is enough
    rows = provenance.numbers_of(path, tr, TASKS["P-numerical-01"])
    assert [(r["path"], r["source"]) for r in rows] == [("Dq", "tool"), ("B", "none")]


def test_numbers_of_passes_the_task_to_the_prompt_check(tmp_path):
    answer = {"Dq": 500.0, "B": 807.0, "C": 3509.0, "out_of_scope": False, "reason": "fit"}
    path = write_run(tmp_path, "m/B/medium/P-numerical-01-k1", result(answer))
    prompt = {"id": "t", "class": "numerical", "prompt": "B = 807 and C = 3 509 cm-1"}
    by = {r["path"]: r for r in provenance.numbers_of(path, read_transcript(path), prompt)}
    assert (by["Dq"]["in_prompt"], by["B"]["in_prompt"], by["C"]["in_prompt"]) == (False, True, True)


def test_fits_are_compared_in_condition_c_only(tmp_path):
    answer = {"Dq": 2044.0, "B": 763.8, "C": None, "out_of_scope": False, "reason": "fit"}
    path = write_run(tmp_path, "m/B/medium/P-numerical-01-k1", [*mcp("a", "ts_fit_spectrum", {"d_count": 2}, FIT),
                                                                 *result(answer)])
    tr = read_transcript(path)
    by = {r["path"]: r for r in provenance.numbers_of(path, tr, TASKS["P-numerical-01"])}
    assert by["Dq"]["fit_relation"] == "" and by["Dq"]["fit_value"] is None
    by = {r["path"]: r for r in provenance.numbers_of(path, tr, TASKS["P-numerical-01"], condition="C")}
    assert by["Dq"]["fit_relation"] == "copied" and by["Dq"]["fit_value"] == 2043.7


def test_the_groups_of_the_origins_are_exact():
    def row(correct, fit_schema=True, model="m"):
        return {"model": model, "condition": "C", "fit_schema": fit_schema, "correct": correct,
                "dq_origin": "fit_copied", "b_origin": "tool", "c_origin": "null"}

    rows = [row(False, fit_schema=False), row(True), row(False), row(None), row(True), row(True, model="a")]
    got = provenance._groups(rows)
    assert got[0] == {"model": "a", "condition": "C", "parameter": "B", "origin": "tool", "n_runs": 1,
                      "n_correct": 1, "n_wrong": 0}
    assert [g for g in got if g["model"] == "m"] == [
        {"model": "m", "condition": "C", "parameter": p, "origin": o, "n_runs": 4, "n_correct": 2, "n_wrong": 2}
        for p, o in (("B", "tool"), ("C", "null"), ("Dq", "fit_copied"))]
