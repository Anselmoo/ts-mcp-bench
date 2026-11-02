"""Explain one run (one transcript) in plain text: task, tool calls, answer, reference, error per parameter, verdict
with its rule, failure category, tokens, time and cost.

    tsbench explain <run set>/<model>/<cond>/<effort>/<task>-k<i>.jsonl [--json]

Reads the transcript, its sidecar (`<task>-k<i>.meta.json`) and the pilot task set. The verdict comes from the same
functions as scores.csv (tsbench.score.score.score_transcript and tsbench.score.taxonomy.failure_category), not from a
copy of them. Only pilot tasks are explained; for a transcript of the confirmatory tasks (ids `C-...`, or a path through
a `confirmatory` folder) the command refuses before any task is loaded (exit 2). No API call, no access to keys or
environment values.
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import re
import sys

from tsbench.core.api_errors import is_context_overflow
from tsbench.report import page
from tsbench.report.base import HARNESS, not_evaluable
from tsbench.score.extract import STRUCTURED_TOOL, read_transcript
from tsbench.score.numeric import CURVE_X_MATCH, trace
from tsbench.score.score import score_transcript, usage_detail, wall_time
from tsbench.score.taxonomy import failure_category

_NAME = re.compile(r"^(?P<task>.+)-k(?P<k>\d+)\.jsonl$")
EXCERPT = 160


class Refusal(Exception):
    """The run may not be explained (confirmatory) or its task cannot be found."""


# ------------------------------------------------------------------ helpers
def clean(v):
    """JSON-safe: NaN/inf -> None, sets/tuples -> lists."""
    if isinstance(v, float):
        return v if math.isfinite(v) else None
    if isinstance(v, dict):
        return {str(k): clean(x) for k, x in v.items()}
    if isinstance(v, (list, tuple, set)):
        return [clean(x) for x in v]
    return v


def one_line(text, limit: int = EXCERPT) -> str:
    s = " ".join(str(text).split())
    return s if len(s) <= limit else s[: limit - 1] + "…"


def outcome_of(correct: bool, category: str, limited: bool) -> str:
    """The outcome key the report pages use: correct | wrong | harness | na429 (words in tsbench.report.page.STATUS).
    `limited`: the scorer leaves the run out (`base.not_evaluable`: HTTP 429 or another API error)."""
    if limited:
        return "na429"
    if correct:
        return "correct"
    return "harness" if category in HARNESS else "wrong"


def _short_input(name: str, inp) -> str:
    if isinstance(inp, dict):
        if name == "Bash" and isinstance(inp.get("command"), str):
            return one_line(inp["command"], 200)
        return one_line(json.dumps(inp, ensure_ascii=False), 200)
    return one_line(inp, 200)


def _blocks(event: dict) -> list:
    msg = event.get("message")
    content = msg.get("content") if isinstance(msg, dict) else None
    return content if isinstance(content, list) else []


def _flatten(content) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(_flatten(c) for c in content)
    if isinstance(content, dict):
        if isinstance(content.get("text"), str):
            return content["text"]
        return json.dumps(content, ensure_ascii=False)
    return str(content)


def steps_of(events: list[dict]) -> list[dict]:
    """Tool calls in order, each with the excerpt of the result that belongs to its tool_use_id."""
    steps, by_id = [], {}
    for ev in events:
        if ev.get("type") == "assistant":
            for b in _blocks(ev):
                if isinstance(b, dict) and b.get("type") == "tool_use" and not (
                        isinstance(b.get("id"), str) and b["id"] in by_id):
                    st = {
                        "n": len(steps) + 1,
                        "name": b.get("name", ""),
                        "input": _short_input(b.get("name", ""), b.get("input")),
                        "result": None,
                        "tool_error": False,
                    }
                    steps.append(st)
                    if isinstance(b.get("id"), str):  # a list or dict id cannot be a key
                        by_id[b["id"]] = st
        elif ev.get("type") == "user":
            for b in _blocks(ev):
                if isinstance(b, dict) and b.get("type") == "tool_result" \
                        and isinstance(b.get("tool_use_id"), str) and b["tool_use_id"] in by_id:
                    st = by_id[b["tool_use_id"]]
                    st["result"] = one_line(_flatten(b.get("content")))
                    st["tool_error"] = bool(b.get("is_error"))
    return steps


def _condition_from_tools(tools: list[str]) -> str:
    real = [t for t in tools if t != STRUCTURED_TOOL]
    if any(t.startswith("mcp__") for t in real):
        return "C"
    return "B" if "Bash" in real else "A"


def _path_facts(path: pathlib.Path) -> dict:
    m = _NAME.match(path.name)
    if not m:
        raise Refusal(f"file name does not match <task>-k<i>.jsonl: {path.name}")
    parts = path.resolve().parts
    model = cond = effort = None
    if len(parts) >= 4 and parts[-3] in ("A", "B", "C"):
        model, cond, effort = parts[-4], parts[-3], parts[-2]
    return {"task_id": m["task"], "k": int(m["k"]), "model": model, "condition": cond, "effort": effort}


def _sidecar(path: pathlib.Path) -> dict:
    meta = path.with_name(path.name[: -len(".jsonl")] + ".meta.json")
    try:
        d = json.loads(meta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return d if isinstance(d, dict) else {}


def load_pilot_task(task_id: str, path: pathlib.Path) -> dict:
    """The pilot task from the task set. Confirmatory ids (C-...) or a path through `confirmatory` are refused before
    any task is loaded."""
    if task_id.startswith("C-") or "confirmatory" in path.resolve().parts:
        raise Refusal(
            "Refused: this is a transcript of the confirmatory tasks. Task text, reference and tolerance stay "
            "hidden until preregistration; this command explains pilot runs only."
        )
    from tsbench.tasks import load  # the only permitted reader of the task file

    tasks = {t["id"]: t for t in load("pilot")}
    if task_id not in tasks:
        raise Refusal(f"Task {task_id} is not in the pilot split of the task set.")
    return tasks[task_id]


# ------------------------------------------------------------------ verdict explanation per schema
def _fit_checks(task: dict, row: dict, answer: dict | None) -> tuple[list[dict], list[str]]:
    tol = task.get("tolerance") or {}
    ref = task.get("reference") or {}
    checks, why = [], []
    if answer is None:
        return checks, ["No evaluable answer: neither structured_output nor a JSON line with Dq, B, out_of_scope."]
    oos = answer.get("out_of_scope")
    if task.get("expect_out_of_scope"):
        why.append("Rule (out-of-scope task): correct only if out_of_scope = true AND Dq = null AND B = null.")
        why.append(f"Answer: out_of_scope = {oos!r}, Dq = {answer.get('Dq')!r}, B = {answer.get('B')!r}.")
        return checks, why
    if oos is not False:
        why.append(f"Rule: out_of_scope must be the boolean false. Answer: {oos!r} "
                   "(true = the solvable task was declined; not a boolean = format error).")
        return checks, why
    why.append("Rule (solvable task): out_of_scope = false, and for every required parameter p "
               "|answer - reference| / |reference| <= tolerance[p].")
    if task.get("geometry") == "Td":
        why.append("Td geometry: Dq is compared as an absolute value.")
    for p in task.get("required") or []:
        rel = row.get(f"rel_err_{p.lower()}")
        t = tol.get(p)
        ok = isinstance(rel, float) and not math.isnan(rel) and t is not None and rel <= t + 1e-12
        checks.append(
            {
                "param": p,
                "answer": answer.get(p),
                "reference": ref.get(p),
                "abs_err": row.get(f"abs_err_{p.lower()}"),
                "rel_err": rel,
                "tolerance": t,
                "ok": bool(ok),
            }
        )
    return checks, why


def _curve_detail(task: dict, answer: dict | None) -> tuple[list[dict], list[str]]:
    tol = task.get("tolerance") or {}
    rel_tol, abs_tol = tol.get("curve_rel", 0.03), tol.get("curve_abs", 0.3)
    why = [f"Rule (curve): every E/B value must be within {abs_tol} absolute OR {rel_tol:.0%} relative; "
           "points are grouped by Dq/B (3 terms each) and sorted by E/B; term names do not count."]
    ref_pts = task.get("reference_curve") or []
    pts = (answer or {}).get("points")
    if answer is None or not isinstance(pts, list):
        return [], why + ["No list of points in structured_output (curve answers have no text fallback)."]
    if len(pts) != len(ref_pts):
        return [], why + [f"The answer has {len(pts)} points, the reference {len(ref_pts)}: wrong at once."]
    rows = []
    for x in dict.fromkeys(p["dq_over_b"] for p in ref_pts):
        want = sorted(p["e_over_b"] for p in ref_pts if p["dq_over_b"] == x)
        got = sorted(p["e_over_b"] for p in pts if abs(p["dq_over_b"] - x) <= CURVE_X_MATCH)
        if len(got) != len(want):
            return rows, why + [f"At Dq/B = {x} the answer has {len(got)} instead of {len(want)} points: wrong."]
        for g, w in zip(got, want, strict=False):
            err = abs(g - w)
            rel = err / abs(w) if w else (0.0 if err == 0 else math.inf)
            rows.append({"dq_over_b": x, "reference": w, "answer": g, "abs_err": err, "rel_err": rel,
                         "ok": err <= abs_tol + 1e-12 or rel <= rel_tol + 1e-12})
    return rows, why


def _batch_detail(task: dict, answer: dict | None) -> tuple[list[dict], list[str]]:
    from tsbench.score.batch_score import score_batch

    tol = (task.get("tolerance") or {}).get("item_rel") or 0.02
    why = [f"Rule (batch): every entry is matched to the reference by `input`; |result - reference| / |reference| "
           f"<= {tol:.0%}. Correct only if ALL entries match and none is missing or extra."]
    if answer is None:
        return [], why + ["No `values` list in structured_output."]
    sc = score_batch(task, answer)
    why.append(
        f"{sc['n_correct_items']} of {sc['n_items']} entries correct; missing {sc['n_missing']}, extra {sc['n_extra']}."
    )
    return sc["items"], why


def _pairing_detail(task: dict, row: dict) -> tuple[list[dict], list[str]]:
    why = ["Rule (pairing): correct only if node precision = node recall = edge F1 = 1 AND the ground terms of every "
           "configuration are right."]
    keys = ("node_precision", "node_recall", "edge_precision", "edge_recall", "edge_f1", "ground_correct")
    return [{k: row.get(k)} for k in keys], why


def _diagram_detail(task: dict, row: dict) -> tuple[list[dict], list[str]]:
    need = (task.get("tolerance") or {}).get("item_accuracy_min", 0.95)
    tol = task.get("tolerance") or {}
    why = [
        "Rule (diagram): each of the 54 values (9 points x 6 levels) counts if within "
        f"{tol.get('curve_abs', 0.3)} absolute "
        f"or {tol.get('curve_rel', 0.03):.0%} relative; correct if item_accuracy >= {need} (at most 2 wrong values)."
    ]
    return [{"item_accuracy": row.get("item_accuracy"), "n_correct_items": row.get("n_correct_items"),
             "label_accuracy": row.get("label_accuracy"), "rms_e_over_b": row.get("rms_e_over_b")}], why


def _error_reason(tr, result: dict | None, meta: dict) -> dict | None:
    """Why the run has no result or an error result; None for a normal end."""
    if result is None:
        why = "No result event in the transcript (run aborted, time limit or crash)."
        if meta.get("timed_out"):
            why += " The sidecar says timed_out = true."
        if meta.get("exit_code") not in (None, 0):
            why += f" Exit code of the process: {meta.get('exit_code')}."
        return {"kind": "no_result", "text": why}
    sub = result.get("subtype")
    left_out = not_evaluable(result)
    if left_out == "rate_limited":
        return {
            "kind": "http_429",
            "text": "HTTP 429: rate limit of the infrastructure (API gateway). This is no answer of the "
            "model; the reports count the run as 'not evaluable' and leave it out of the accuracy.",
        }
    if left_out == "api_error":
        return {
            "kind": "api_error",
            "text": "API error of the infrastructure (a server error, not a rate limit): "
            f"{one_line(result.get('result') or result.get('errors') or '', 200)}. This is no answer of the model; "
            "the reports count the run as 'not evaluable' and leave it out of the accuracy.",
        }
    if is_context_overflow(result):
        return {
            "kind": "context_overflow",
            "text": "Context overflow: the request outgrew the model's context window "
            f"({one_line(result.get('result') or '', 200)}). The run's own prompt and tool output grew too large; "
            "the reports count it as a wrong answer.",
        }
    if sub == "error_max_turns":
        return {
            "kind": "max_turns",
            "text": f"Max-turns limit reached (num_turns = {result.get('num_turns')}); no final "
            "answer, no structured_output.",
        }
    if sub == "error_max_budget_usd":
        return {"kind": "budget", "text": "Budget per call (--max-budget-usd) used up before the answer was given."}
    detail = result.get("result") or ((result.get("errors") or [""])[0] if isinstance(result.get("errors"), list)
                                      else "")
    if sub == "error_max_structured_output_retries":
        return {"kind": "structured_output_retries",
                "text": f"The CLI ended the run: every StructuredOutput call failed the answer schema "
                f"({one_line(detail, 200)}). A format failure of the model, no API error."}
    if result.get("is_error"):
        return {"kind": "api_error", "text": f"API/CLI error: {one_line(detail, 200)}"}
    if not isinstance(result.get("structured_output"), dict):
        return {"kind": "no_structured_output", "text": "The result has no structured_output (the model did not call "
                "StructuredOutput); for `fit` the last JSON line of the text is read instead."}
    return None


# ------------------------------------------------------------------ main function
def explain(path) -> dict:
    """Everything `render` prints, as a JSON-safe dict (also the output of `--json`)."""
    path = pathlib.Path(path)
    facts = _path_facts(path)
    task = load_pilot_task(facts["task_id"], path)
    tr = read_transcript(path)
    meta = _sidecar(path)
    res = tr.result or {}
    has_result = tr.result is not None
    schema = task.get("answer_schema", "fit")
    sc, answer = score_transcript(task, tr)
    row = {**sc, "has_result": has_result, "result_subtype": res.get("subtype"),
           "is_error": res.get("is_error") if has_result else None, "context_overflow": is_context_overflow(res)}
    category = failure_category(row, task)
    limited = not_evaluable(tr.result) is not None
    correct = bool(sc.get("correct"))

    if schema == "fit":
        checks, why = _fit_checks(task, row, answer)
    elif schema == "curve":
        checks, why = _curve_detail(task, answer)
    elif schema == "batch":
        checks, why = _batch_detail(task, answer)
    elif schema == "pairing":
        checks, why = _pairing_detail(task, row)
    else:
        checks, why = _diagram_detail(task, row)

    error = _error_reason(tr, tr.result, meta)
    if error and answer is None and error["kind"] != "no_structured_output":
        why.insert(0, "There is no answer because the run ended before it: " + error["text"])
    model = (tr.init or {}).get("model") or facts["model"]
    tools = list((tr.init or {}).get("tools") or [])
    cond = facts["condition"] or meta.get("condition") or (_condition_from_tools(tools) if tr.init else None)
    answer_source = sc.get("answer_source")
    answer_source = None if answer_source in (None, "none") else answer_source
    n_rep, n_tr = trace(answer, tr) if schema == "fit" else (0, 0)
    usage = usage_detail(res.get("usage")) if has_result else {}
    names = [s["name"] for s in steps_of(tr.events) if s["name"] != STRUCTURED_TOOL]
    free_model = bool(model) and not str(model).startswith("claude-")
    out = {
        "file": str(path),
        "run_id": meta.get("run_id"),
        "task": {
            "id": task["id"],
            "class": task["class"],
            "subtype": task.get("subtype"),
            "answer_schema": schema,
            "prompt": task["prompt"],
        },
        "model": model,
        "condition": cond,
        "effort": facts["effort"] or meta.get("effort"),
        "k": facts["k"],
        "init": {"n_tools": len(tools), "tools": tools, "mcp_servers": (tr.init or {}).get("mcp_servers") or []},
        "steps": steps_of(tr.events),
        "tool_names_used": names,
        "answer": {"source": answer_source, "value": answer},
        "reference": task.get("reference")
        if schema in ("fit", "batch")
        else (
            {"n_reference_points": len(task.get("reference_curve") or [])}
            if schema == "curve"
            else {"note": "large reference, see the task record in the pilot task set"}
        ),
        "tolerance": task.get("tolerance"),
        "expect_out_of_scope": bool(task.get("expect_out_of_scope")),
        "checks": checks,
        "verdict": {"correct": correct, "why": why},
        "scorer_row": {
            k: sc.get(k)
            for k in (
                "correct",
                "unparseable",
                "answer_out_of_scope",
                "rel_err_dq",
                "rel_err_b",
                "rel_err_c",
                "curve_max_rel_err",
                "item_accuracy",
                "median_rel_error",
            )
        },
        "category": category,
        "category_text": page.CATEGORY_TEXT.get(category, category),
        "outcome": outcome_of(correct, category, limited),
        "traced": {"reported": n_rep, "traced": n_tr} if schema == "fit" else None,
        "usage": usage,
        "num_turns": res.get("num_turns") if has_result else None,
        "time": {
            "duration_s": (res["duration_ms"] / 1000.0 if isinstance(res.get("duration_ms"), (int, float)) else None),
            "api_duration_s": (
                res["duration_api_ms"] / 1000.0 if isinstance(res.get("duration_api_ms"), (int, float)) else None
            ),
            "wall_time_s": wall_time(path),
        },
        "cost": {
            "total_cost_usd": res.get("total_cost_usd") if has_result else None,
            "is_estimate": free_model,
            "cost_unknown": meta.get("cost_unknown"),
        },
        "error": error,
        "result_flags": meta.get("flags"),
    }
    return clean(out)


# ------------------------------------------------------------------ text rendering
def _fmt(v, nd: int = 4) -> str:
    if v is None:
        return "–"
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, float):
        return f"{v:.{nd}g}"
    return str(v)


def render(d: dict) -> str:
    """The explanation as plain text, one fact per line."""
    t, L = d["task"], []
    add = L.append
    add(f"Run: {d['file']}")
    add(f"Task {t['id']}  (class {t['class']}, subtype {t['subtype']}, answer schema {t['answer_schema']})")
    add(f"Question: {t['prompt']}")
    add(f"Model: {d['model']}   Condition: {d['condition']}   Effort: {d['effort']}   Repetition k = {d['k']}")
    tools = [x for x in d["init"]["tools"]]
    shown = [x.replace("mcp__tanabesugano__", "ts:") for x in tools]
    more = f", … (+{len(shown) - 8})" if len(shown) > 8 else ""
    add(f"Tools ({len(tools)}): " + (", ".join(shown[:8]) + more if shown else "none"))
    add("")
    add(f"Steps ({len(d['steps'])} tool calls):")
    for s in d["steps"]:
        name = s["name"].replace("mcp__tanabesugano__", "ts:")
        add(f"  {s['n']}. {name}  {s['input']}")
        if s["result"] is not None:
            add(f"     -> {'ERROR: ' if s['tool_error'] else ''}{s['result']}")
    if not d["steps"]:
        add("  (no tool calls)")
    add("")
    a = d["answer"]
    add(f"Final answer ({a['source'] or 'no evaluable answer'}): "
        f"{json.dumps(a['value'], ensure_ascii=False) if a['value'] is not None else '–'}")
    add(
        f"Reference: {json.dumps(d['reference'], ensure_ascii=False)}   "
        f"Tolerance: {json.dumps(d['tolerance'], ensure_ascii=False)}"
    )
    if d["checks"]:
        add("Per parameter / value:")
        for c in d["checks"][:60]:
            if "param" in c:
                add(
                    f"  {c['param']}: answer {_fmt(c['answer'])}, reference {_fmt(c['reference'])}, "
                    f"abs. error {_fmt(c['abs_err'])}, "
                    f"rel. error {_fmt(c['rel_err'])} {'<=' if c['ok'] else '>'} tolerance {_fmt(c['tolerance'])}  -> "
                    f"{'ok' if c['ok'] else 'TOO LARGE'}"
                )
            elif "dq_over_b" in c:
                add(
                    f"  Dq/B {c['dq_over_b']}: reference {_fmt(c['reference'])}, answer {_fmt(c['answer'])}, "
                    "rel. error "
                    f"{_fmt(c['rel_err'])}  -> {'ok' if c['ok'] else 'TOO LARGE'}"
                )
            elif "input" in c:
                add(f"  input {c['input']}: reference {_fmt(c['reference'])}, answer {_fmt(c['result'])}, rel. error "
                    f"{_fmt(c['rel_error'])}  -> {'ok' if c['correct'] else 'wrong'}")
            else:
                add("  " + ", ".join(f"{k} = {_fmt(v)}" for k, v in c.items()))
        if len(d["checks"]) > 60:
            add(f"  … {len(d['checks']) - 60} more lines (--json shows all)")
    v = d["verdict"]
    add("")
    if d["outcome"] == "na429":
        add(
            "VERDICT: NOT EVALUABLE (HTTP 429 or API error). scores.csv lists the run as correct = False; "
            "the report pages leave it out."
        )
    else:
        add(f"VERDICT: {'CORRECT' if v['correct'] else 'WRONG'}")
    for w in v["why"]:
        add(f"  {w}")
    add(f"Category (failure taxonomy): {d['category']} = {d['category_text']}")
    add(f"Outcome on the report pages: {page.STATUS_TEXT.get(d['outcome'], d['outcome'])}")
    if d["error"]:
        label = "Note" if d["error"]["kind"] == "no_structured_output" else "Reason"
        add(f"{label}: {d['error']['text']}")
    if d["traced"] and d["traced"]["reported"]:
        add(f"Traced: {d['traced']['traced']} of {d['traced']['reported']} reported numbers appear in tool results.")
    u, tm, co = d["usage"], d["time"], d["cost"]
    add("")
    if u:
        thinking = "not reported" if u["thinking_tokens"] is None else u["thinking_tokens"]
        add(
            f"Tokens: input {u['uncached_input_tokens']} + cache write {u['cache_creation_tokens']} + cache read "
            f"{u['cache_read_tokens']}, output total "
            f"{u['total_tokens'] - u['uncached_input_tokens'] - u['cache_creation_tokens'] - u['cache_read_tokens']} "
            f"(of which thinking {thinking}), sum {u['total_tokens']}; turns {d['num_turns']}"
        )
    else:
        add("Tokens: no result event, no figures.")
    add(
        f"Time: total {_fmt(tm['duration_s'])} s, of which API {_fmt(tm['api_duration_s'])} s; "
        f"wall clock (runner) {_fmt(tm['wall_time_s'])} s"
    )
    cost = _fmt(co["total_cost_usd"], 6)
    add(
        f"Cost: {cost} USD"
        + (
            " (gateway run: the claude CLI's estimate from its default price list; the gateway reports no "
            "USD cost)"
            if co["is_estimate"]
            else ""
        )
    )
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="tsbench explain", description="Explain one pilot run in plain text.")
    ap.add_argument("transcript", help="<task>-k<i>.jsonl of a pilot run")
    ap.add_argument("--json", action="store_true", help="the same explanation as JSON")
    args = ap.parse_args(argv)
    path = pathlib.Path(args.transcript)
    if not path.is_file():
        print(f"no such file: {path}", file=sys.stderr)
        return 2
    try:
        d = explain(path)
    except Refusal as e:
        print(str(e), file=sys.stderr)
        return 2
    print(json.dumps(d, ensure_ascii=False, indent=2) if args.json else render(d))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
