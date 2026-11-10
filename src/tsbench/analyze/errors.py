"""Failing tool steps: which steps of a run failed, how, and what the run did after the first failure.

    tsbench analyze errors --runs RUNS --out DIR [--split confirmatory --i-have-preregistered DOI]

writes `DIR/runs.csv` (one row per run), `DIR/steps.csv` (one row per failing step), `DIR/exceptions.csv` (failing
steps per model, condition, kind, exception and missing name) and `DIR/by_group.csv` (per model and condition).
A step is one tool call other than the StructuredOutput answer; its result text is read, nothing is executed.
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict

from tsbench.analyze.common import accuracy, arguments, iter_runs, load_tasks, median, times, write_csv, write_readme
from tsbench.score.artifacts import _EXIT_RE, result_of, scan_tool_calls
from tsbench.score.extract import STRUCTURED_TOOL, Transcript, flatten_text

__all__ = ["KINDS", "MESSAGE_MAX", "classify", "main", "run_errors", "tool_steps"]

MESSAGE_MAX = 200
# the kinds of failure, in the order in which they are checked: the first that fits names the step
KINDS = ("timeout", "python", "shell", "tool_error", "mcp_error", "exit", "is_error")
_TRACEBACK = "Traceback (most recent call last)"
_EXCEPTION = re.compile(r"^(?P<type>[A-Za-z_][\w.]*(?:Error|Exception|Exit|Interrupt))(?::[ \t]*(?P<msg>.*))?$",
                        re.M)
_SHELL = re.compile(r"^(?:(?:/usr)?/bin/)?(?:ba)?sh: (?:line )?(?:\d+: )?(?P<msg>.+)$", re.M)
# an error line of a basic command (these print `<name>: ...` only on failure), python3 itself included
_COMMAND = re.compile(r"^(?:mkdir|cd|cp|mv|rm|sed|cat|ls|touch|chmod|tee|grep|head|tail|ln|find|python[0-9.]*"
                      r"|pip[0-9.]*): .+$", re.M)
_TIMEOUT = re.compile(r"\btimed out after \d")
_TOOL_ERROR = re.compile(r"<tool_use_error>(?P<msg>.*?)(?:</tool_use_error>|$)", re.S)
# the name an ImportError, ModuleNotFoundError, AttributeError or NameError says is missing
_MISSING = [
    (re.compile(r"cannot import name '(?P<n>[\w.]+)' from '(?P<m>[\w.]+)'"), "{m}.{n}"),
    (re.compile(r"No module named '(?P<m>[\w.]+)'"), "{m}"),
    (re.compile(r"module '(?P<m>[\w.]+)' has no attribute '(?P<n>\w+)'"), "{m}.{n}"),
    (re.compile(r"'(?P<m>[\w.]+)' object has no attribute '(?P<n>\w+)'"), "{m}.{n}"),
    (re.compile(r"name '(?P<n>\w+)' is not defined"), "{n}"),
]

README = """
# Failing tool steps

Inputs: the transcripts of one scored run folder and its `scores.csv` (for `correct` and `class`).

A step is one tool call other than the StructuredOutput answer. A step fails when its result shows one of these
kinds, checked in this order: `timeout` (the tool stopped the command: "timed out after"), `python` (a Python
exception line, `ValueError: ...`, after a Traceback, or with a non-zero exit or the error flag), `shell` (an error
line of the shell, `/bin/bash: line 3: pip: command not found`, or of a basic command such as mkdir, cd, sed or
python3 itself, `mkdir: cannot create directory`, also when the exit code is 0), `tool_error` (the harness refused
the call, such as an unknown tool name), `mcp_error` (an MCP result whose JSON has an `error` field), `exit` (a
non-zero exit code; the message is the first line after the exit code) and `is_error` (the result's error flag
alone). For `python` the exception type is the last exception line of the text (the one raised) and the missing name
is read from ImportError, ModuleNotFoundError, AttributeError and NameError messages (`scipy.special.sph_harm`). A
printed line that only looks like an exception, with exit code 0 and no Traceback, is not a failure.

`runs.csv`: per run the number of steps and of failing steps, the first failing step (0-based) with its kind,
exception and missing name, `steps_to_first_ok` (the steps before the first step that did not fail; empty when none
succeeded), `recovered` (a step after the first failure succeeded), `last_step_failed`, `span_s` (first to last
timestamp of the transcript), `wall_after_first_error_s` (from the result of the first failing step to the last
timestamp) and `failed_step_s` (the summed step times of the failing steps; a step's time runs from the result
before it, or the first timestamp, to its own result, so it holds the model's turn and the tool's run).

`steps.csv`: one row per failing step with the first line of its message. `exceptions.csv`: failing steps and runs
per model, condition, kind, exception and missing name. `by_group.csv`: per model and condition the runs, the steps,
the failing steps, the runs with a failure, how many of them recovered and were correct, the accuracy of runs with
steps with and without a failure, the median time after the first failure and the share of time in failing steps.
"""

RUN_COLUMNS = ["run_id", "model", "condition", "effort", "task_id", "class", "correct", "n_steps", "n_failed_steps",
               "first_error_step", "first_error_kind", "first_exception", "first_missing_name", "steps_to_first_ok",
               "recovered", "last_step_failed", "span_s", "wall_after_first_error_s", "failed_step_s", "kinds",
               "exceptions", "missing_names"]
STEP_COLUMNS = ["run_id", "model", "condition", "task_id", "class", "step", "tool", "kind", "exception",
                "missing_name", "exit", "is_error", "step_s", "message"]
EXCEPTION_COLUMNS = ["model", "condition", "kind", "exception", "missing_name", "n_steps", "n_runs"]
GROUP_COLUMNS = ["model", "condition", "n_runs", "n_runs_with_steps", "n_steps", "n_failed_steps",
                 "failed_step_share", "n_runs_with_failure", "n_recovered", "n_last_step_failed",
                 "n_correct_with_failure", "n_runs_without_failure", "n_correct_without_failure",
                 "accuracy_with_failure", "accuracy_without_failure", "median_wall_after_first_error_s",
                 "failed_step_s", "span_s", "failed_time_share"]


def _first_line(text: str) -> str:
    return next((ln.strip() for ln in text.splitlines() if ln.strip()), "")[:MESSAGE_MAX]


def _missing(message: str) -> str:
    for rx, form in _MISSING:
        m = rx.search(message)
        if m:
            return form.format(**m.groupdict())
    return ""


def _mcp_error(text: str) -> str:
    if not text.lstrip().startswith("{"):
        return ""
    try:
        data = json.loads(text)
    except ValueError:
        return ""
    if not isinstance(data, dict):
        return ""
    err = data.get("error")
    if not err and isinstance(data.get("result"), dict):
        err = data["result"].get("error")
    return str(err) if err else ""


def classify(text: str, is_error: bool, exit_code: int | None) -> dict | None:
    """{kind, exception, missing_name, message} of a failing step; None for a step that did not fail."""
    signal = is_error or exit_code not in (None, 0)
    found = None
    if m := _TIMEOUT.search(text):
        found = ("timeout", "", _first_line(text[m.start():]))
    if found is None:
        excs = list(_EXCEPTION.finditer(text))
        if excs and (_TRACEBACK in text or signal):
            last = excs[-1]
            found = ("python", last["type"], last.group(0).strip()[:MESSAGE_MAX])
    if found is None and (m := _SHELL.search(text) or _COMMAND.search(text)):
        found = ("shell", "", m.group(0).strip()[:MESSAGE_MAX])
    if found is None and (m := _TOOL_ERROR.search(text)):
        found = ("tool_error", "", _first_line(m["msg"]) or "tool_use_error")
    if found is None and (err := _mcp_error(text)):
        found = ("mcp_error", "", _first_line(err))
    if found is None and exit_code not in (None, 0):
        found = ("exit", "", _first_line(_EXIT_RE.sub("", text, count=1)) or _first_line(text))
    if found is None and is_error:
        found = ("is_error", "", _first_line(text) or "error flag")
    if found is None:
        return None
    kind, exception, message = found
    return {"kind": kind, "exception": exception, "missing_name": _missing(message) if kind == "python" else "",
            "message": message}


def tool_steps(tr: Transcript) -> list[dict]:
    """The tool steps of a transcript in call order: {step, tool, exit, is_error, failure, step_s, exec_s, done}.
    `failure` is `classify` of the result; the times are in seconds (None without timestamps)."""
    uses, results = scan_tool_calls(tr)
    t = times(tr)
    prev = t.start
    out = []
    for i, use in enumerate(u for u in uses if u.get("name") != STRUCTURED_TOOL):
        res = result_of(results, use) or {}
        text = flatten_text(res.get("content"))
        is_error = bool(res.get("is_error"))
        m = _EXIT_RE.search(text)
        exit_code = int(m.group(1)) if m else (1 if is_error else (0 if res else None))
        uid = use.get("id") if isinstance(use.get("id"), str) else None
        done, began = t.result.get(uid or ""), t.use.get(uid or "")
        out.append({"step": i, "tool": str(use.get("name") or ""), "exit": exit_code, "is_error": is_error,
                    "failure": classify(text, is_error, exit_code),
                    "step_s": done - prev if done is not None and prev is not None else None,
                    "exec_s": done - began if done is not None and began is not None else None, "done": done})
        if done is not None:
            prev = done
    return out


def run_errors(tr: Transcript, steps: list[dict] | None = None) -> tuple[dict, list[dict]]:
    """(summary of one run, its failing steps). `steps` are the run's `tool_steps` when already made."""
    steps = tool_steps(tr) if steps is None else steps
    t = times(tr)
    failing = [{"step": s["step"], "tool": s["tool"], "exit": s["exit"], "is_error": s["is_error"],
                "step_s": s["step_s"], "done": s["done"], **s["failure"]} for s in steps if s["failure"]]
    ok = [s["step"] for s in steps if not s["failure"]]
    first = failing[0] if failing else None
    kinds = Counter(f["kind"] for f in failing)
    summary = {
        "n_steps": len(steps), "n_failed_steps": len(failing),
        "first_error_step": first["step"] if first else None,
        "first_error_kind": first["kind"] if first else "",
        "first_exception": first["exception"] if first else "",
        "first_missing_name": first["missing_name"] if first else "",
        "steps_to_first_ok": ok[0] if ok else None,
        "recovered": bool(first) and any(i > first["step"] for i in ok),
        "last_step_failed": bool(steps) and bool(steps[-1]["failure"]),
        "span_s": t.end - t.start if t.start is not None and t.end is not None else None,
        "wall_after_first_error_s": (t.end - first["done"] if first and first["done"] is not None
                                     and t.end is not None else None),
        "failed_step_s": sum(f["step_s"] for f in failing if f["step_s"] is not None),
        "kinds": " ".join(f"{k}:{n}" for k, n in sorted(kinds.items())),
        "exceptions": " ".join(dict.fromkeys(f["exception"] for f in failing if f["exception"])),
        "missing_names": " ".join(dict.fromkeys(f["missing_name"] for f in failing if f["missing_name"])),
    }
    return summary, failing


def _groups(rows: list[dict]) -> list[dict]:
    cells: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        cells[(r["model"], r["condition"])].append(r)
    out = []
    for (model, cond), rs in sorted(cells.items()):
        with_steps = [r for r in rs if r["n_steps"]]
        failed = [r for r in with_steps if r["n_failed_steps"]]
        clean = [r for r in with_steps if not r["n_failed_steps"]]
        n_steps = sum(r["n_steps"] for r in rs)
        n_failed = sum(r["n_failed_steps"] for r in rs)
        span = sum(r["span_s"] or 0 for r in with_steps)
        failed_s = sum(r["failed_step_s"] or 0 for r in with_steps)
        out.append({
            "model": model, "condition": cond, "n_runs": len(rs), "n_runs_with_steps": len(with_steps),
            "n_steps": n_steps, "n_failed_steps": n_failed,
            "failed_step_share": n_failed / n_steps if n_steps else None,
            "n_runs_with_failure": len(failed), "n_recovered": sum(r["recovered"] for r in failed),
            "n_last_step_failed": sum(r["last_step_failed"] for r in failed),
            "n_correct_with_failure": sum(r["correct"] is True for r in failed),
            "n_runs_without_failure": len(clean), "n_correct_without_failure": sum(r["correct"] is True for r in clean),
            "accuracy_with_failure": accuracy(sum(r["correct"] is True for r in failed), len(failed))["accuracy"],
            "accuracy_without_failure": accuracy(sum(r["correct"] is True for r in clean), len(clean))["accuracy"],
            "median_wall_after_first_error_s": median(r["wall_after_first_error_s"] for r in failed),
            "failed_step_s": failed_s, "span_s": span, "failed_time_share": failed_s / span if span else None,
        })
    return out


def _exceptions(steps: list[dict]) -> list[dict]:
    count: Counter = Counter()
    runs: dict[tuple, set] = defaultdict(set)
    for s in steps:
        key = (s["model"], s["condition"], s["kind"], s["exception"], s["missing_name"])
        count[key] += 1
        runs[key].add(s["run_id"])
    return [dict(zip(EXCEPTION_COLUMNS, (*key, n, len(runs[key])), strict=True))
            for key, n in sorted(count.items(), key=lambda kv: (-kv[1], kv[0]))]


def main(argv: list[str] | None = None) -> int:
    runs, out, split = arguments("tsbench analyze errors", __doc__ or "", argv)
    rows, steps = [], []
    for run in iter_runs(runs, load_tasks(split)):
        summary, failing = run_errors(run.tr)
        base = {"run_id": run.run_id, "model": run.model, "condition": run.condition, "effort": run.effort,
                "task_id": run.task_id, "class": run.cls, "correct": run.correct}
        rows.append({**base, **summary})
        steps += [{**base, **f} for f in failing]
    write_csv(out / "runs.csv", RUN_COLUMNS, rows)
    write_csv(out / "steps.csv", STEP_COLUMNS, steps)
    write_csv(out / "exceptions.csv", EXCEPTION_COLUMNS, _exceptions(steps))
    write_csv(out / "by_group.csv", GROUP_COLUMNS, _groups(rows))
    write_readme(out, README)
    print(f"runs: {len(rows)}, with steps: {sum(1 for r in rows if r['n_steps'])}, failing steps: {len(steps)}, "
          f"out: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
