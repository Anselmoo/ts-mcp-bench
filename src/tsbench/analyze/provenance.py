"""Provenance of the answer numbers: for every number of an answer, the tool step it came from, a script it was typed
into, or no tool output at all; in condition C also whether the fitted value of the MCP server was copied or changed.

    tsbench analyze provenance --runs RUNS --out DIR [--split confirmatory --i-have-preregistered DOI]

writes `DIR/numbers.csv` (one row per answer number), `DIR/runs.csv` (one row per run) and `DIR/by_group.csv` (per
model, condition, parameter and origin). The links come from the solution path (`score.solution_path`); `traced` is
the scorer's traced-number test (`score.numeric.trace`) applied to one number. Nothing is executed.
"""
from __future__ import annotations

import json
import pathlib
import re
from collections import defaultdict

from tsbench.analyze.common import arguments, iter_runs, load_tasks, write_csv, write_readme
from tsbench.score.artifacts import result_of, scan_tool_calls
from tsbench.score.extract import Transcript, flatten_text
from tsbench.score.numeric import PARAMS, TRACE_RTOL, numbers_in, trace
from tsbench.score.solution_path import solution_path

__all__ = ["FIT_TOOLS", "fits", "in_prompt", "main", "numbers_of", "origin"]

FIT_TOOLS = ("ts_fit_spectrum",)
_FITTED = {"Dq": "fitted_Dq", "B": "fitted_B", "C": "fitted_C"}
# "3 509" in a prompt is one number: a space (also a thin or no-break space) between digit groups is dropped
_GROUP_SPACE = re.compile(r"(?<=\d)[    ](?=\d{3}(?!\d))")

README = """
# Provenance of the answer numbers

Inputs: the transcripts of one scored run folder, the task records of its split (the prompt) and its `scores.csv`
(for `correct`, `class`, `n_reported` and `n_traced`).

Every finite number of the answer the scorer used is one row of `numbers.csv` (`path` names it: `Dq`, `B`, `C`,
`points[3].e_over_b`, ...). `source` says where it came from, by the links of the solution path (a number matches a
number of a tool result within 0.5 % relative, by absolute value): `tool` (a step printed it whose own input does not
hold it; `source_step` and `source_tool` name the step: the last such step that ran a script, else the last such
step), `typed` (every step that printed it holds it in its own input, a literal of the command or its heredocs or an
argument of the MCP call that the tool echoes back: the model chose the number), `weak` (an integer below 50, which
turns up by chance, linked to some step) and `none` (no tool result holds it: the model's own number). `traced` is
the scorer's test (`n_traced` of `scores.csv`): the number appears in some tool result; it can differ from `source`
because the solution path keeps only the first 20 000 characters of a result. `in_prompt` says that the number is
written in the task prompt.

In condition C each Dq, B and C is compared with the fitted values of the `ts_fit_spectrum` calls of the run
(`fitted_Dq`, `fitted_B`, `fitted_C`): `copied` (within 0.5 % of a fitted value of any call), `changed` (a fit
returned that parameter but the answer differs; `fit_value` and `fit_rel_diff` refer to the last fit that returned
it), `no_fit` (no call returned it). Outside condition C the field is empty.

`runs.csv`: per run the counts per source, `n_traced` (Dq, B, C traced here) next to `n_traced_scores` (the scorer's
column) and the origin of Dq, B and C. After a fit in condition C: `fit_copied`, `fit_other_tool` (not the fitted
value, but another tool step printed it, such as `ts_ratio_fit_app`) or `fit_changed` (not the fitted value and no
tool step computed it); otherwise the source (`tool`, `typed`, `weak`, `none`); `null` when the answer leaves the
parameter out. `by_group.csv`: per model, condition, parameter and origin
the runs, the correct runs and the wrong runs.
"""

NUMBER_COLUMNS = ["run_id", "model", "condition", "task_id", "class", "correct", "path", "value", "source",
                  "source_step", "source_tool", "n_linked_steps", "weak", "traced", "in_prompt", "fit_value",
                  "fit_relation", "fit_rel_diff"]
RUN_COLUMNS = ["run_id", "model", "condition", "effort", "task_id", "class", "correct", "n_numbers", "n_tool",
               "n_typed", "n_weak", "n_none", "n_in_prompt", "n_traced", "n_traced_scores", "n_reported_scores",
               "dq_origin", "b_origin", "c_origin"]
GROUP_COLUMNS = ["model", "condition", "parameter", "origin", "n_runs", "n_correct", "n_wrong"]


def _matches(x: float, v: float) -> bool:
    """The match of the traced-number metric: |x| within TRACE_RTOL of |v| (an exact match for 0)."""
    return x == 0 if v == 0 else abs(abs(x) - abs(v)) <= TRACE_RTOL * abs(v)


def in_prompt(value: float, task: dict | None) -> bool:
    """The number is written in the task prompt (thousands groups split by a space or a comma count as one)."""
    prompt = (task or {}).get("prompt")
    if not isinstance(prompt, str):
        return False
    return any(_matches(x, value) for x in numbers_in(_GROUP_SPACE.sub("", prompt)))


def fits(tr: Transcript) -> list[dict]:
    """The fitted parameters of every `ts_fit_spectrum` result, in call order: [{"Dq": .., "B": .., "C": ..}] with
    only the parameters the call returned."""
    uses, results = scan_tool_calls(tr)
    out = []
    for use in uses:
        if str(use.get("name") or "").split("__", 2)[-1] not in FIT_TOOLS:
            continue
        try:
            data = json.loads(flatten_text((result_of(results, use) or {}).get("content")))
        except ValueError:
            continue
        body = data.get("result", data) if isinstance(data, dict) else None
        if not isinstance(body, dict):
            continue
        got = {p: float(body[k]) for p, k in _FITTED.items()
               if isinstance(body.get(k), (int, float)) and not isinstance(body.get(k), bool)}
        if got:
            out.append(got)
    return out


def _fit_relation(param: str, value: float, fitted: list[dict]) -> tuple[str, float | None, float | None]:
    have = [f[param] for f in fitted if param in f]
    if not have:
        return "no_fit", None, None
    last = have[-1]
    rel = abs(abs(value) - abs(last)) / abs(last) if last else None
    return ("copied" if any(_matches(f, value) for f in have) else "changed"), last, rel


def _source(value: dict, steps: list[dict]) -> int | None:
    """The step an answer value came from: the rule of the solution path (the last linked step that ran a script,
    else the last linked step; none for a weak number), where a step whose own input holds the number (its whole
    command with the heredocs, or the arguments of an MCP call) only echoes it and is never the source."""
    echoed = [i for i in value["steps"] if any(_matches(x, value["value"]) for x in numbers_in(steps[i]["command"]))]
    computed = [i for i in value["steps"] if i not in echoed]
    if not computed or value["weak"]:
        return None
    ran = [i for i in computed if steps[i]["scripts"] or steps[i]["runs"]]
    return (ran or computed)[-1]


def numbers_of(path, tr: Transcript, task: dict | None, condition: str | None = None) -> list[dict]:
    """One row per number of the answer: {path, value, source, source_step, source_tool, n_linked_steps, weak,
    traced, in_prompt, fit_value, fit_relation, fit_rel_diff}. `condition` defaults to the folder name of the
    transcript (`<model>/<cond>/<effort>/<task>-k<i>.jsonl`)."""
    sp = solution_path(path, task=task, tr=tr)
    cond = condition or pathlib.Path(path).parent.parent.name
    fitted = fits(tr) if cond == "C" else []
    out = []
    for v in sp["values"]:
        step = _source(v, sp["steps"])
        source = ("tool" if step is not None else "weak" if v["weak"] and v["steps"]
                  else "typed" if v["steps"] else "none")
        row = {"path": v["path"], "value": v["value"], "source": source, "source_step": step,
               "source_tool": sp["steps"][step]["tool"] if step is not None else "",
               "n_linked_steps": len(v["steps"]), "weak": v["weak"], "traced": None,
               "in_prompt": in_prompt(v["value"], task), "fit_value": None, "fit_relation": "", "fit_rel_diff": None}
        if v["path"] in PARAMS:
            row["traced"] = trace({v["path"]: v["value"]}, tr)[1] == 1
            if cond == "C":
                row["fit_relation"], row["fit_value"], row["fit_rel_diff"] = _fit_relation(v["path"], v["value"],
                                                                                         fitted)
        out.append(row)
    return out


def origin(row: dict | None) -> str:
    """The origin of one answer parameter. In condition C after a fit: `fit_copied`, `fit_other_tool` (differs from
    the fit, but another tool step printed it) or `fit_changed` (differs from the fit and no tool step computed it);
    else the source. `null` when the answer has no number for it."""
    if row is None:
        return "null"
    if row.get("fit_relation") == "copied":
        return "fit_copied"
    if row.get("fit_relation") == "changed":
        return "fit_other_tool" if row["source"] == "tool" else "fit_changed"
    return row["source"]


def _groups(rows: list[dict]) -> list[dict]:
    cells: dict[tuple, list[int]] = defaultdict(lambda: [0, 0])
    for r in rows:
        if not r["fit_schema"]:
            continue
        for p in PARAMS:
            c = cells[(r["model"], r["condition"], p, r[f"{p.lower()}_origin"])]
            c[0] += 1
            c[1] += r["correct"] is True
    return [{"model": m, "condition": cond, "parameter": p, "origin": o, "n_runs": n, "n_correct": k,
             "n_wrong": n - k} for (m, cond, p, o), (n, k) in sorted(cells.items())]


def main(argv: list[str] | None = None) -> int:
    runs, out, split = arguments("tsbench analyze provenance", __doc__ or "", argv)
    numbers, rows = [], []
    for run in iter_runs(runs, load_tasks(split)):
        nums = numbers_of(run.path, run.tr, run.task, run.condition)
        base = {"run_id": run.run_id, "model": run.model, "condition": run.condition, "task_id": run.task_id,
                "class": run.cls, "correct": run.correct}
        numbers += [{**base, **n} for n in nums]
        top = {n["path"]: n for n in nums if n["path"] in PARAMS}
        count = defaultdict(int)
        for n in nums:
            count[n["source"]] += 1
        fit_schema = (run.task or {}).get("answer_schema", "fit") == "fit"
        rows.append({**base, "effort": run.effort, "n_numbers": len(nums), "n_tool": count["tool"],
                     "n_typed": count["typed"], "n_weak": count["weak"], "n_none": count["none"],
                     "n_in_prompt": sum(n["in_prompt"] for n in nums),
                     "n_traced": sum(n["traced"] is True for n in top.values()) if fit_schema else 0,
                     "n_traced_scores": run.score.get("n_traced", ""),
                     "n_reported_scores": run.score.get("n_reported", ""),
                     "fit_schema": fit_schema,
                     **{f"{p.lower()}_origin": origin(top.get(p)) for p in PARAMS}})
    write_csv(out / "numbers.csv", NUMBER_COLUMNS, numbers)
    write_csv(out / "runs.csv", RUN_COLUMNS, rows)
    write_csv(out / "by_group.csv", GROUP_COLUMNS, _groups(rows))
    write_readme(out, README)
    print(f"runs: {len(rows)}, numbers: {len(numbers)}, traced Dq/B/C: {sum(r['n_traced'] for r in rows)}, "
          f"out: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
