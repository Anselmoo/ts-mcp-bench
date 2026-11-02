"""Rescue of answers given before a turn/budget stop, and runs that are not evaluable (HTTP 429, API errors).

Transcripts are built by hand in the shape of the real stream-json. No network, no API.
"""
from __future__ import annotations

import csv
import json
import pathlib

import pytest

from tsbench.score import extract, taxonomy
from tsbench.score import score as score_cli
from tsbench.tasks import load

MODEL = "claude-haiku-5-5"
PILOT = load("pilot")
FIT = next(t for t in PILOT if t["class"] == "closed_form")
CURVE = next((t for t in PILOT if t.get("answer_schema") == "curve"), None)


def good(task=FIT, **kw):
    ref = task["reference"]
    return {"Dq": ref["Dq"], "B": ref["B"], "C": ref["C"] if "C" in task["required"] else None,
            "out_of_scope": False, "reason": "r", **kw}


def bad(task=FIT):
    return good(task, Dq=good(task)["Dq"] * 1.5)


def tool_use(inp, n=0, name="StructuredOutput"):
    return {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": f"tu{n}", "name": name,
                                                           "input": inp}]}}


def result(subtype="success", is_error=False, **kw):
    return {"type": "result", "subtype": subtype, "is_error": is_error, "total_cost_usd": 0.01, "num_turns": 3,
            "usage": {"input_tokens": 1, "output_tokens": 1}, "permission_denials": [], **kw}


INIT = {"type": "system", "subtype": "init", "model": MODEL, "tools": ["StructuredOutput"], "mcp_servers": []}


def write(root, task, k, events, cond="A"):
    p = pathlib.Path(root) / MODEL / cond / "medium" / f"{task['id']}-k{k}.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("".join(json.dumps(e) + "\n" for e in [INIT, *events]), encoding="utf-8")
    return p


def score_one(tmp_path, events, task=FIT, cond="A"):
    p = write(tmp_path / "runs", task, 1, events, cond)
    tr = extract.read_transcript(p)
    return score_cli.score_transcript(task, tr)


def read_csv(p):
    with open(p, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


# ------------------------------------------------------------------ rescue
@pytest.mark.parametrize("stop", ["error_max_turns", "error_max_budget_usd"])
def test_answer_before_a_turn_or_budget_stop_is_rescued_and_scored_normally(tmp_path, stop):
    sc, answer = score_one(tmp_path, [tool_use(good()), result(stop, True)])
    assert sc["correct"] is True and answer["Dq"] == good()["Dq"]
    assert (sc["answer_source"], sc["rescued"], sc["rescue_stop_reason"]) == ("rescued_tool_call", True, stop)
    # the same run, wrong in content: rescued, scored like any answer, and not correct
    sc, _ = score_one(tmp_path, [tool_use(bad()), result(stop, True)])
    assert sc["correct"] is False and sc["rescued"] is True and sc["answer_source"] == "rescued_tool_call"


def test_run_without_a_result_event_is_rescued_too(tmp_path):
    sc, _ = score_one(tmp_path, [tool_use(good())])
    assert sc["correct"] and sc["rescued"] and sc["rescue_stop_reason"] == "no_result"


def test_rescue_takes_the_last_valid_call_and_rejects_invalid_input(tmp_path):
    invalid = [{**good(), "Dq": "1000"},  # a string where the schema wants a number
               {**good(), "extra": 1},  # additionalProperties: false
               {"Dq": 1.0, "B": 2.0},  # required fields missing
               [1, 2, 3]]  # not an object
    for inp in invalid:
        # an earlier valid call survives an invalid later one ...
        sc, answer = score_one(tmp_path, [tool_use(bad(), 0), tool_use(inp, 1), result("error_max_turns", True)])
        assert sc["rescued"] and answer["Dq"] == bad()["Dq"], inp
        # ... and an invalid call alone rescues nothing
        sc, answer = score_one(tmp_path, [tool_use(inp, 1), result("error_max_turns", True)])
        assert answer is None and sc["rescued"] is False and sc["answer_source"] == "none" and sc["correct"] is False
    # the LAST valid one wins over an earlier valid one
    sc, _ = score_one(tmp_path, [tool_use(bad(), 0), tool_use(good(), 1), result("error_max_turns", True)])
    assert sc["correct"] is True
    # other tools named like an answer do not count
    sc, answer = score_one(tmp_path, [tool_use(good(), 0, name="Bash"), result("error_max_turns", True)])
    assert answer is None and not sc["rescued"]


def test_no_rescue_when_the_result_has_an_answer_or_the_run_ended_otherwise(tmp_path):
    sc, _ = score_one(tmp_path, [tool_use(bad()), result(structured_output=good(), result="x")])
    assert sc["correct"] and sc["answer_source"] == "structured_output" and not sc["rescued"]  # the result wins
    sc, _ = score_one(tmp_path, [tool_use(good()), result("success", True, api_error_status=500,
                                                           result="API Error: 500 boom")])
    assert not sc["rescued"] and sc["answer_source"] == "none" and sc["correct"] is False
    sc, _ = score_one(tmp_path, [tool_use(good()), result("success", False, result="no json here")])
    assert not sc["rescued"] and sc["correct"] is False  # a normal end without structured_output: unchanged


def test_text_json_is_labelled(tmp_path):
    text = json.dumps(good())
    sc, _ = score_one(tmp_path, [result("success", False, result="Done.\n" + text)])
    assert sc["correct"] and sc["answer_source"] == "text_json" and not sc["rescued"]


@pytest.mark.skipif(CURVE is None, reason="no curve task in the pilot split")
def test_rescue_checks_the_schema_of_the_run(tmp_path):
    ref = CURVE["reference_curve"]
    ans = {"points": [{"dq_over_b": p["dq_over_b"], "term": p["term"], "e_over_b": p["e_over_b"]} for p in ref],
           "reason": "r"}
    sc, _ = score_one(tmp_path, [tool_use(ans), result("error_max_budget_usd", True)], task=CURVE)
    assert sc["correct"] and sc["rescued"]
    # a fit-shaped call is not a curve answer
    sc, answer = score_one(tmp_path, [tool_use(good()), result("error_max_budget_usd", True)], task=CURVE)
    assert answer is None and not sc["rescued"]


def test_rescue_writes_scores_csv_columns_and_keeps_rates_honest(tmp_path):
    runs = tmp_path / "runs"
    write(runs, FIT, 1, [tool_use(good()), result("error_max_budget_usd", True)])
    write(runs, FIT, 2, [result(structured_output=good(), result="x")])
    write(runs, FIT, 3, [tool_use(bad()), result("error_max_turns", True)])
    out = score_cli.score_dir(runs, "pilot")
    rows = {r["k_index"]: r for r in read_csv(runs / "scores.csv")}
    assert (rows["1"]["answer_source"], rows["1"]["rescued"], rows["1"]["rescue_stop_reason"]) == (
        "rescued_tool_call", "True", "error_max_budget_usd")
    assert (rows["2"]["answer_source"], rows["2"]["rescued"]) == ("structured_output", "False")
    assert rows["3"]["rescued"] == "True" and rows["3"]["correct"] == "False"
    assert rows["1"]["result_subtype"] == "error_max_budget_usd"  # the stop stays visible
    rates = read_csv(runs / "rates.csv")
    assert len(rates) == 1 and (rates[0]["k"], rates[0]["n_correct"]) == ("3", "2")
    assert "rescued answers (last StructuredOutput call after a limit): 2" in "\n".join(score_cli.summary_lines(out))


def test_taxonomy_judges_a_rescued_answer_by_its_content():
    base = {"correct": False, "has_result": False, "rescued": True, "result_subtype": "error_max_turns",
            "is_error": True, "rel_err_dq": 0.5, "rel_err_b": 0.0, "answer_out_of_scope": False,
            "unparseable": False}
    t = {"required": ["Dq", "B"], "tolerance": {"Dq": 0.02, "B": 0.05}, "expect_out_of_scope": False}
    assert taxonomy.failure_category({**base, "rel_err_dq": 0.1}, t) == "wrong_dq"
    assert taxonomy.failure_category({**base, "correct": True}, t) == "correct"
    # not rescued: the stop is the category; a rescue opens no new path to "correct"
    assert taxonomy.failure_category({**base, "rescued": False, "has_result": True}, t) == "max_turns"
    assert taxonomy.failure_category({**base, "rescued": False}, t) == "no_result"
    assert taxonomy.failure_category({**base, "rescued": False, "has_result": True,
                                      "result_subtype": "error_max_budget_usd"}, t) == "budget"


# ------------------------------------------------------------------ not evaluable
RATE_LIMITED = result("success", True, api_error_status=429,
                      result="API Error: Request rejected (429) · API rate limit exceeded", total_cost_usd=0)
API_500 = result("success", True, api_error_status=500, terminal_reason="api_error",
                 result="API Error: 500 deepseek-v4-flash-0731 is not a multimodal model.")


def test_rates_exclude_runs_that_are_not_evaluable(tmp_path):
    runs = tmp_path / "runs"
    write(runs, FIT, 1, [result(structured_output=good(), result="x")])
    write(runs, FIT, 2, [result(structured_output=bad(), result="x")])
    write(runs, FIT, 3, [RATE_LIMITED])
    write(runs, FIT, 4, [tool_use(good()), API_500])
    other = next(t for t in PILOT if t["class"] == "closed_form" and t["id"] != FIT["id"])
    write(runs, other, 1, [RATE_LIMITED])  # a cell with nothing to evaluate
    out = score_cli.score_dir(runs, "pilot")
    rows = {(r["task_id"], r["k_index"]): r for r in read_csv(runs / "scores.csv")}
    r3, r4, ok = rows[(FIT["id"], "3")], rows[(FIT["id"], "4")], rows[(FIT["id"], "1")]
    assert (r3["evaluable"], r3["not_evaluable_reason"]) == ("False", "rate_limited")
    assert (r4["evaluable"], r4["not_evaluable_reason"]) == ("False", "api_error")
    assert (ok["evaluable"], ok["not_evaluable_reason"]) == ("True", "")
    assert r3["correct"] == "False" and r3["rescued"] == "False"  # the 500 run is not rescued either
    rates = read_csv(runs / "rates.csv")
    assert [(r["task_id"], r["k"], r["n_correct"], r["rate"]) for r in rates] == [(FIT["id"], "2", "1", "0.5")]
    lines = "\n".join(score_cli.summary_lines(out))
    assert "not evaluable (excluded from the rates): api_error 1, rate_limited 2" in lines
    acc_line = next(ln for ln in lines.splitlines() if ln.startswith(MODEL))
    assert acc_line.split()[-3:] == ["1", "2", "0.50"]  # correct, n (evaluable only), acc


def test_harness_limits_and_timeouts_stay_evaluable(tmp_path):
    runs = tmp_path / "runs"
    write(runs, FIT, 1, [result("error_max_turns", True)])
    write(runs, FIT, 2, [])  # no result event: a timeout
    score_cli.score_dir(runs, "pilot")
    assert {r["evaluable"] for r in read_csv(runs / "scores.csv")} == {"True"}
    assert read_csv(runs / "rates.csv")[0]["k"] == "2"
