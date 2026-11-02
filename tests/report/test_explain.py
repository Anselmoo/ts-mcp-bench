"""Tests for `tsbench explain` (src/tsbench/report/explain.py): synthetic transcripts in tmp_path, no network, no key,
no real run data."""
from __future__ import annotations

import csv
import json
import pathlib

import pytest

HERE = pathlib.Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]

from tsbench.report import explain as explain_run  # noqa: E402
from tsbench.score.score import find_transcripts, score_dir  # noqa: E402
from tsbench.tasks import load  # noqa: E402

FIX = REPO_ROOT / "src" / "tsbench" / "run" / "fake_cli_fixtures"
MODEL = "claude-haiku-5-5"
TASKS = {t["id"]: t for t in load("pilot")}


def _init() -> dict:
    ev = json.loads((FIX / "init_C.json").read_text(encoding="utf-8"))
    ev["tools"] = list(ev["tools"]) + ["StructuredOutput"]
    return ev


def _result(structured=None, **over) -> dict:
    ev = json.loads((FIX / "result_error_not_logged_in.json").read_text(encoding="utf-8"))
    ev.update({"is_error": False, "subtype": "success", "api_error_status": None, "terminal_reason": "completed",
               "num_turns": 3,
               "duration_ms": 4200, "duration_api_ms": 4000, "total_cost_usd": 0.0123,
               "result": json.dumps(structured) if structured is not None else "",
               "usage": {"input_tokens": 10, "cache_creation_input_tokens": 100, "cache_read_input_tokens": 1000,
                         "output_tokens": 200, "output_tokens_details": {"thinking_tokens": 50}}})
    if structured is not None:
        ev["structured_output"] = structured
    ev.update(over)
    return ev


def _tool_pair(i: int, name: str, inp: dict, content, is_error: bool = False) -> list[dict]:
    uid = f"toolu_{i}"
    return [
        {"type": "assistant", "message": {"role": "assistant", "content": [
            {"type": "tool_use", "id": uid, "name": name, "input": inp}]}},
        {"type": "user", "message": {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": uid, "content": content,
             **({"is_error": True} if is_error else {})}]}},
    ]


def write_run(root: pathlib.Path, task_id: str, structured=None, *, k: int = 1, calls=(), result=None,
              cond: str = "C", meta=None) -> pathlib.Path:
    d = root / MODEL / cond / "medium"
    d.mkdir(parents=True, exist_ok=True)
    events = [_init()]
    for i, (name, inp, content) in enumerate(calls):
        events += _tool_pair(i, name, inp, content)
    if structured is not None:
        events += _tool_pair(99, "StructuredOutput", structured, "Structured output provided successfully")
    events.append(result if result is not None else _result(structured))
    path = d / f"{task_id}-k{k}.jsonl"
    path.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")
    if meta is not None:
        path.with_name(path.name[:-6] + ".meta.json").write_text(json.dumps(meta), encoding="utf-8")
    return path


FIT_CALL = ("mcp__tanabesugano__ts_fit_spectrum", {"d_count": 7, "observed_peaks_cm1": [8400, 18000, 21130]},
            '{"result":{"fitted_Dq":959.84,"fitted_B":928.42}}')


def fit_answer(dq, b, **kw):
    return {"Dq": dq, "B": b, "C": None, "out_of_scope": False, "reason": "x", **kw}


def test_correct_fit(tmp_path):
    p = write_run(tmp_path, "P-numerical-02", fit_answer(960, 928), calls=[FIT_CALL], meta={"wall_time_s": 5.5})
    d = explain_run.explain(p)
    assert d["verdict"]["correct"] is True and d["category"] == "correct" and d["outcome"] == "correct"
    assert [c["param"] for c in d["checks"]] == ["Dq", "B"] and all(c["ok"] for c in d["checks"])
    assert d["answer"]["source"] == "structured_output"
    assert d["usage"]["total_tokens"] == 10 + 100 + 1000 + 200 and d["usage"]["thinking_tokens"] == 50
    assert d["time"]["wall_time_s"] == 5.5 and d["cost"]["total_cost_usd"] == 0.0123
    assert d["cost"]["is_estimate"] is False
    assert [s["name"] for s in d["steps"]] == ["mcp__tanabesugano__ts_fit_spectrum", "StructuredOutput"]
    assert d["steps"][0]["result"].startswith('{"result"')
    assert d["traced"] == {"reported": 2, "traced": 2}
    text = explain_run.render(d)
    assert "VERDICT: CORRECT" in text and "ts:ts_fit_spectrum" in text and "spin-allowed" in text


def test_wrong_fit_names_the_parameter(tmp_path):
    p = write_run(tmp_path, "P-numerical-02", fit_answer(1000, 928), calls=[FIT_CALL])  # Dq 4.2 % off, tolerance 2 %
    d = explain_run.explain(p)
    dq, b = d["checks"]
    assert d["verdict"]["correct"] is False and d["category"] == "wrong_dq" and d["outcome"] == "wrong"
    assert dq["ok"] is False and dq["rel_err"] == pytest.approx(40 / 960) and dq["tolerance"] == 0.02
    assert b["ok"] is True
    assert "TOO LARGE" in explain_run.render(d) and "VERDICT: WRONG" in explain_run.render(d)


def test_boundary_is_accepted_like_the_scorer(tmp_path):
    p = write_run(tmp_path, "P-numerical-02", fit_answer(960 * 1.02, 928))  # exactly on the tolerance
    assert explain_run.explain(p)["verdict"]["correct"] is True


def test_false_refusal_rule(tmp_path):
    p = write_run(tmp_path, "P-numerical-02", fit_answer(None, None, out_of_scope=True))
    d = explain_run.explain(p)
    assert d["category"] == "false_refusal" and not d["checks"]
    assert "out_of_scope" in " ".join(d["verdict"]["why"])


def test_rate_limit_is_not_an_answer(tmp_path):
    res = _result(None, is_error=True, api_error_status=429, total_cost_usd=0.65,
                  result="API Error: Request rejected (429) · API rate limit exceeded")
    p = write_run(tmp_path, "P-numerical-02", None, result=res, cond="B")
    d = explain_run.explain(p)
    assert d["error"]["kind"] == "http_429" and d["outcome"] == "na429"
    assert d["verdict"]["correct"] is False and d["category"] == "api_error"
    assert "NOT EVALUABLE" in explain_run.render(d)


@pytest.mark.parametrize("over", [
    {"api_error_status": "429", "result": "x"},
    {"api_error_status": None, "result": "API Error: Request rejected (429)"},
    {"api_error_status": 502, "result": "Bad Gateway"},
    {"api_error_status": None, "terminal_reason": "api_error", "result": "x"},
    {"api_error_status": None, "result": "API Error: connection reset"},
])
def test_explain_leaves_out_what_the_scorer_leaves_out(tmp_path, over):
    """explain decides 'not evaluable' with score.not_evaluable_reason: 5xx, terminal_reason api_error, 'API Error:'
    text, a string status '429' and '(429)' text all end as na429, like in scores.csv."""
    from tsbench.score.score import not_evaluable_reason, read_transcript
    res = _result(None, is_error=True, total_cost_usd=0.1, **over)
    p = write_run(tmp_path, "P-numerical-02", None, result=res, cond="B")
    assert not_evaluable_reason(read_transcript(p)) is not None
    d = explain_run.explain(p)
    assert d["outcome"] == "na429" and "NOT EVALUABLE" in explain_run.render(d)
    assert "VERDICT: WRONG" not in explain_run.render(d)


def test_free_model_cost_is_flagged_as_estimate(tmp_path):
    d = tmp_path / "gemma-4-31b-it" / "B" / "medium"
    d.mkdir(parents=True)
    ev = [dict(_init(), model="gemma-4-31b-it"), _result(fit_answer(960, 928))]
    path = d / "P-numerical-02-k1.jsonl"
    path.write_text("\n".join(json.dumps(e) for e in ev), encoding="utf-8")
    out = explain_run.explain(path)
    assert out["cost"]["is_estimate"] is True and "estimate" in explain_run.render(out)


def test_max_turns_reason(tmp_path):
    res = _result(None, is_error=True, subtype="error_max_turns", num_turns=16)
    d = explain_run.explain(write_run(tmp_path, "P-numerical-02", None, calls=[FIT_CALL], result=res))
    assert d["error"]["kind"] == "max_turns" and d["category"] == "max_turns" and d["outcome"] == "harness"


def test_structured_output_retries_are_a_format_failure_not_an_api_error(tmp_path):
    bad = dict(fit_answer(960, 928), Dq="2044 cm-1")
    res = _result(None, is_error=True, subtype="error_max_structured_output_retries", result=None,
                  errors=["Failed to provide valid structured output after 5 attempts"])
    res.pop("result")
    calls = [("StructuredOutput", bad, "Output does not match required schema: /Dq: must be number,null")]
    d = explain_run.explain(write_run(tmp_path, "P-numerical-02", None, calls=calls, result=res))
    assert d["error"]["kind"] == "structured_output_retries" and d["category"] == "unparseable"
    assert d["outcome"] != "harness"
    assert "after 5 attempts" in d["error"]["text"]


def test_api_error_text_falls_back_to_the_errors_list(tmp_path):
    res = _result(None, is_error=True, subtype="error_during_execution", errors=["boom happened"])
    res.pop("result")
    d = explain_run.explain(write_run(tmp_path, "P-numerical-02", None, result=res))
    assert d["error"]["kind"] == "api_error" and "boom happened" in d["error"]["text"]


def test_budget_and_missing_result(tmp_path):
    res = _result(None, is_error=True, subtype="error_max_budget_usd")
    d = explain_run.explain(write_run(tmp_path, "P-numerical-02", None, result=res, k=1))
    assert d["error"]["kind"] == "budget" and d["category"] == "budget"
    p = write_run(tmp_path, "P-numerical-03", None, k=2, meta={"timed_out": True, "exit_code": -9})
    lines = [ln for ln in p.read_text(encoding="utf-8").splitlines() if '"type": "result"' not in ln]
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    d = explain_run.explain(p)
    assert d["error"]["kind"] == "no_result" and d["category"] == "no_result" and "timed_out" in d["error"]["text"]
    assert d["usage"] == {} and "no result event" in explain_run.render(d)


def test_rescued_answer_is_shown_with_the_scorer_source(tmp_path):
    ans = fit_answer(960, 928)
    res = _result(None, is_error=True, subtype="error_max_turns", num_turns=16)
    d = explain_run.explain(write_run(tmp_path, "P-numerical-02", ans, calls=[FIT_CALL], result=res))
    assert d["answer"] == {"source": "rescued_tool_call", "value": ans}
    assert d["verdict"]["correct"] is True
    text = explain_run.render(d)
    assert "Final answer (rescued_tool_call):" in text and "VERDICT: CORRECT" in text


def test_rescued_answer_without_result_event(tmp_path):
    ans = fit_answer(960, 928)
    p = write_run(tmp_path, "P-numerical-03", ans, calls=[FIT_CALL])
    lines = [ln for ln in p.read_text(encoding="utf-8").splitlines() if '"type": "result"' not in ln]
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    d = explain_run.explain(p)
    assert d["answer"]["source"] == "rescued_tool_call" and d["answer"]["value"] is not None


def test_answer_in_the_last_text_json_line_is_named_text_json(tmp_path):
    ans = fit_answer(960, 928)
    res = _result(None, result="done\n" + json.dumps(ans))
    d = explain_run.explain(write_run(tmp_path, "P-numerical-02", None, calls=[FIT_CALL], result=res))
    assert d["answer"]["source"] == "text_json" and d["answer"]["value"] == ans


def test_repeated_tool_use_event_is_one_step():
    use = {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": "toolu_x", "name": "Bash", "input": {"command": "ls"}}]}}
    res = {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "toolu_x", "content": "ok"}]}}
    steps = explain_run.steps_of([use, dict(use), res])
    assert len(steps) == 1 and steps[0]["result"] == "ok" and steps[0]["n"] == 1


def test_steps_of_unhashable_ids_do_not_raise():
    use = {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": ["x"], "name": "Bash", "input": {"command": "ls"}}]}}
    res = {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": ["x"], "content": "ok"}]}}
    assert len(explain_run.steps_of([use, res])) == 1


def curve_points(task, delta=0.0):
    return [{"dq_over_b": p["dq_over_b"], "term": p["term"], "e_over_b": p["e_over_b"] + delta}
            for p in task["reference_curve"]]


def test_curve_correct_and_wrong(tmp_path):
    task = TASKS["P-curve-01"]
    ok = explain_run.explain(write_run(tmp_path, "P-curve-01", {"points": curve_points(task), "reason": ""}))
    assert ok["verdict"]["correct"] and ok["checks"] and all(c["ok"] for c in ok["checks"])
    bad_pts = curve_points(task)
    bad_pts[0]["e_over_b"] *= 1.5
    bad = explain_run.explain(write_run(tmp_path, "P-curve-01", {"points": bad_pts, "reason": ""}, k=2))
    assert not bad["verdict"]["correct"] and [c["ok"] for c in bad["checks"]].count(False) == 1
    assert bad["category"] in ("gross_error", "wrong_items")
    assert bad["scorer_row"]["curve_max_rel_err"] == pytest.approx(0.5)
    short = explain_run.explain(write_run(tmp_path, "P-curve-01", {"points": bad_pts[:-1], "reason": ""}, k=3))
    assert not short["verdict"]["correct"] and "points" in " ".join(short["verdict"]["why"])


def test_batch_lists_items(tmp_path):
    task = TASKS["P-batch-01"]
    vals = [{"input": v["input"], "result": v["result"]} for v in task["reference"]["values"]]
    ok = explain_run.explain(write_run(tmp_path, "P-batch-01", {"values": vals}))
    assert ok["verdict"]["correct"] and len(ok["checks"]) == len(vals)
    vals[2] = dict(vals[2], result=vals[2]["result"] * 1.10)
    bad = explain_run.explain(write_run(tmp_path, "P-batch-01", {"values": vals}, k=2))
    assert not bad["verdict"]["correct"] and [c["correct"] for c in bad["checks"]].count(False) == 1
    assert "7 of 8" in " ".join(bad["verdict"]["why"])
    assert "input 4.25" in explain_run.render(bad)


def test_confirmatory_is_refused(tmp_path, capsys):
    p = write_run(tmp_path, "C-closed_form-01", fit_answer(1, 1))
    with pytest.raises(explain_run.Refusal):
        explain_run.explain(p)
    assert explain_run.main([str(p)]) == 2
    err = capsys.readouterr()
    assert "confirmatory" in err.err and err.out == ""
    q = write_run(tmp_path / "confirmatory", "P-numerical-02", fit_answer(960, 928))
    assert explain_run.main([str(q)]) == 2


def test_unknown_task_and_missing_file(tmp_path, capsys):
    p = write_run(tmp_path, "P-nosuchclass-01", {"points": [], "reason": ""})
    assert explain_run.main([str(p)]) == 2
    assert "not in the pilot split" in capsys.readouterr().err
    assert explain_run.main([str(tmp_path / "missing-k1.jsonl")]) == 2


def test_json_output_roundtrips(tmp_path, capsys):
    p = write_run(tmp_path, "P-numerical-02", fit_answer(960, 928), calls=[FIT_CALL])
    assert explain_run.main([str(p), "--json"]) == 0
    d = json.loads(capsys.readouterr().out)
    assert d["verdict"]["correct"] is True and d["task"]["id"] == "P-numerical-02" and d["category"] == "correct"
    assert explain_run.main([str(p)]) == 0
    assert "VERDICT: CORRECT" in capsys.readouterr().out


def test_verdict_equals_scores_csv(tmp_path):
    """The explanation must agree with score_dir for every kind of run."""
    runs = tmp_path / "runs"
    task = TASKS["P-curve-01"]
    write_run(runs, "P-numerical-02", fit_answer(960, 928), calls=[FIT_CALL])
    write_run(runs, "P-numerical-02", fit_answer(1000, 928), k=2)
    write_run(runs, "P-numerical-03", fit_answer(None, None, out_of_scope=True))
    write_run(runs, "P-curve-01", {"points": curve_points(task, 5.0), "reason": ""})
    write_run(runs, "P-curve-01", {"points": curve_points(task), "reason": ""}, k=2)
    score_dir(runs, "pilot")
    with open(runs / "scores.csv", newline="", encoding="utf-8") as fh:
        rows = {(r["task_id"], int(r["k_index"])): r for r in csv.DictReader(fh)}
    assert len(rows) == 5
    for path, _m, _c, _e, task_id, k in find_transcripts(runs):
        d = explain_run.explain(path)
        assert str(d["verdict"]["correct"]) == rows[(task_id, k)]["correct"], (task_id, k)


def test_missing_thinking_count_reads_not_reported(tmp_path):
    res = _result(fit_answer(960, 928))
    del res["usage"]["output_tokens_details"]
    d = explain_run.explain(write_run(tmp_path, "P-numerical-02", fit_answer(960, 928), calls=[FIT_CALL], result=res))
    assert d["usage"]["thinking_tokens"] is None
    text = explain_run.render(d)
    assert "of which thinking not reported" in text and "None" not in text


def test_a_context_overflow_is_explained_as_a_model_failure(tmp_path):
    res = _result(None, is_error=True, api_error_status=400,
                  result="API Error: 400 litellm.ContextWindowExceededError: maximum context length exceeded")
    d = explain_run.explain(write_run(tmp_path, "P-numerical-02", None, result=res))
    assert d["error"]["kind"] == "context_overflow" and "context window" in d["error"]["text"]
    assert d["outcome"] == "wrong"
