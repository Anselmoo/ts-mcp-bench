"""Effort and time per run: thinking and output tokens, turns, wall and API time, the time in tools and in failing
tool steps, and the runs that hit the wall limit.

    tsbench analyze effort --runs RUNS --out DIR [--split confirmatory --i-have-preregistered DOI]

writes `DIR/runs.csv` (one row per run), `DIR/by_group.csv` (per model, condition and effort, joined with the
run folder's `metrics/consistency.csv` when it exists), `DIR/timeouts.csv` (the runs the runner stopped at the wall
limit) and `DIR/tasks.csv` (per model, condition, effort and task: the k repetitions). Tokens come from the result
event (`score.score.usage_detail`), flags and wall time from the sidecar. Nothing is executed.
"""
from __future__ import annotations

import re
import statistics
from collections import defaultdict

from tsbench.analyze.common import arguments, iter_runs, load_tasks, median, read_csv, times, write_csv, write_readme
from tsbench.analyze.errors import run_errors, tool_steps
from tsbench.score.extract import Transcript, is_progress_line
from tsbench.score.score import read_sidecar, seconds_of, tokens_of, usage_detail

__all__ = ["effort_of", "estimated_thinking", "main"]

README = """
# Effort and time

Inputs: the transcripts and sidecars (`<task>-k<i>.meta.json`) of one scored run folder, its `scores.csv` (for
`correct`, `class` and `evaluable`) and, when it exists, its `metrics/consistency.csv`.

`runs.csv`: per run the thinking tokens (`output_tokens_details.thinking_tokens` of the result event's usage; empty
when the event does not report them), the thinking tokens the progress lines estimate (`estimated_thinking_tokens`:
the estimate restarts with every turn, so this sums the last estimate of each turn; it is the only count for a run
stopped before its result event), the output tokens, the turns, the tool steps and the failing tool steps (as in
the error analysis), the wall time measured by the runner (`wall_time_s` of the sidecar, with the start of the CLI),
the duration and API duration of the result event, `thinking_s` (the summed `thinking_duration_ms` of the
transcript's events), `tool_s` (the summed time from each tool call to its result), `failed_step_s` (the summed step
times of the failing steps, see the error analysis), the sidecar flags (`timeout`: the runner stopped the run at the
wall limit; `cost_unknown`: no cost was reported) and the cost. A run stopped at the wall limit has no result event,
so its reported tokens, turns and durations are empty.

`by_group.csv`: per model, condition and effort the runs, the correct runs, the runs with a timeout and with an
unknown cost, the medians of thinking tokens, output tokens, turns and wall time (over all runs and split by correct
and wrong), the rank correlation between thinking tokens and correctness (Spearman, over the runs that report
thinking tokens), and the shares of wall time spent thinking, in tools and in failing steps (sums over the runs that
have both numbers). The last columns are those of `metrics/consistency.csv` for the same cell: agreement of the k
repetitions per task.

`timeouts.csv`: the runs with the `timeout` flag. `tasks.csv`: per model, condition, effort and task the k runs, the
correct ones, whether they agree (`unanimous`), the timeouts, the median thinking tokens with their coefficient of
variation across the k runs, and the median wall time.
"""

RUN_COLUMNS = ["run_id", "model", "condition", "effort", "task_id", "class", "correct", "evaluable", "has_result",
               "result_subtype", "thinking_tokens", "estimated_thinking_tokens", "output_tokens", "num_turns",
               "n_tool_steps", "n_failed_steps", "wall_time_s", "duration_s", "api_duration_s", "thinking_s", "tool_s",
               "failed_step_s", "timed_out", "cost_unknown", "flags", "cost_usd"]
CONSISTENCY = ["n_tasks", "n_unanimous", "unanimity_rate", "mean_pairwise_agreement", "median_cv_dq"]
GROUP_COLUMNS = ["model", "condition", "effort", "n_runs", "n_correct", "n_timeout", "n_cost_unknown",
                 "median_thinking_tokens", "median_thinking_tokens_correct", "median_thinking_tokens_wrong",
                 "median_output_tokens", "median_output_tokens_correct", "median_output_tokens_wrong",
                 "median_num_turns", "median_wall_time_s", "median_wall_time_s_correct", "median_wall_time_s_wrong",
                 "rank_corr_thinking_correct", "thinking_share_of_wall", "tool_share_of_wall",
                 "failed_step_share_of_wall", *CONSISTENCY]
TIMEOUT_COLUMNS = ["run_id", "model", "condition", "effort", "task_id", "class", "correct", "wall_time_s",
                   "estimated_thinking_tokens", "n_tool_steps", "n_failed_steps", "thinking_s", "flags"]
TASK_COLUMNS = ["model", "condition", "effort", "task_id", "class", "k", "n_correct", "unanimous", "n_timeout",
                "median_thinking_tokens", "cv_thinking_tokens", "median_wall_time_s"]


_ESTIMATE = re.compile(r'"estimated_tokens"\s*:\s*(\d+)')


def estimated_thinking(path) -> int | None:
    """The thinking tokens the progress lines of a transcript estimate: the estimate restarts with every turn, so this
    is the sum of the last estimate of each turn. None without progress lines. It is the only count of a run that
    the runner stopped before the result event."""
    total, last, seen = 0, 0, False
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if not is_progress_line(line):
                continue
            m = _ESTIMATE.search(line)
            if m is None:
                continue
            seen = True
            n = int(m.group(1))
            if n < last:
                total += last
            last = n
    return total + last if seen else None


def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def effort_of(path, tr: Transcript) -> dict:
    """The effort of one run (the columns of RUN_COLUMNS from `has_result` on)."""
    res = tr.result or {}
    has = tr.result is not None
    meta = read_sidecar(path)
    steps = tool_steps(tr)
    summary, _ = run_errors(tr, steps)
    detail = usage_detail(res.get("usage")) if has else {}
    return {
        "has_result": has, "result_subtype": res.get("subtype") or "",
        "thinking_tokens": detail.get("thinking_tokens"), "estimated_thinking_tokens": estimated_thinking(path),
        "output_tokens": tokens_of(res.get("usage"))[1] if has else None,
        "num_turns": _num(res.get("num_turns")), "n_tool_steps": len(steps),
        "n_failed_steps": summary["n_failed_steps"],
        "wall_time_s": _num(meta.get("wall_time_s")), "duration_s": seconds_of(res.get("duration_ms")),
        "api_duration_s": seconds_of(res.get("duration_api_ms")), "thinking_s": times(tr).thinking_s,
        "tool_s": sum(s["exec_s"] for s in steps if s["exec_s"] is not None),
        "failed_step_s": summary["failed_step_s"],
        "timed_out": meta.get("timed_out") if isinstance(meta.get("timed_out"), bool) else None,
        "cost_unknown": meta.get("cost_unknown") if isinstance(meta.get("cost_unknown"), bool) else None,
        "flags": " ".join(str(f) for f in meta.get("flags") or [] if isinstance(f, str)),
        "cost_usd": _num(res.get("total_cost_usd")),
    }


def _rank_corr(rows: list[dict]) -> float | None:
    pairs = [(r["thinking_tokens"], 1.0 if r["correct"] is True else 0.0) for r in rows
             if r["thinking_tokens"] is not None]
    if len(pairs) < 3:
        return None
    try:
        return statistics.correlation([a for a, _ in pairs], [b for _, b in pairs], method="ranked")
    except statistics.StatisticsError:  # constant input: no correlation to report
        return None


def _share(rows: list[dict], key: str) -> float | None:
    both = [r for r in rows if r["wall_time_s"] and r[key] is not None]
    wall = sum(r["wall_time_s"] for r in both)
    return sum(r[key] for r in both) / wall if wall else None


def _groups(rows: list[dict], consistency: list[dict]) -> list[dict]:
    cons = {(c.get("model"), c.get("condition"), c.get("effort")): c for c in consistency}
    cells: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        cells[(r["model"], r["condition"], r["effort"])].append(r)
    out = []
    for key, rs in sorted(cells.items()):
        right = [r for r in rs if r["correct"] is True]
        wrong = [r for r in rs if r["correct"] is not True]
        row = {"model": key[0], "condition": key[1], "effort": key[2], "n_runs": len(rs), "n_correct": len(right),
               "n_timeout": sum(r["timed_out"] is True for r in rs),
               "n_cost_unknown": sum(r["cost_unknown"] is True for r in rs),
               "rank_corr_thinking_correct": _rank_corr(rs),
               "thinking_share_of_wall": _share(rs, "thinking_s"), "tool_share_of_wall": _share(rs, "tool_s"),
               "failed_step_share_of_wall": _share(rs, "failed_step_s")}
        for col in ("thinking_tokens", "output_tokens", "wall_time_s"):
            row[f"median_{col}"] = median(r[col] for r in rs)
            row[f"median_{col}_correct"] = median(r[col] for r in right)
            row[f"median_{col}_wrong"] = median(r[col] for r in wrong)
        row["median_num_turns"] = median(r["num_turns"] for r in rs)
        c = cons.get(key, {})
        row.update({col: _float(c.get(col)) for col in CONSISTENCY})
        out.append(row)
    return out


def _float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _cv(values: list) -> float | None:
    got = [v for v in values if v is not None]
    if len(got) < 2 or statistics.fmean(got) <= 0:
        return None
    return statistics.stdev(got) / statistics.fmean(got)


def _tasks(rows: list[dict]) -> list[dict]:
    cells: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        cells[(r["model"], r["condition"], r["effort"], r["task_id"])].append(r)
    out = []
    for (model, cond, effort, task), rs in sorted(cells.items()):
        flags = [r["correct"] is True for r in rs]
        out.append({"model": model, "condition": cond, "effort": effort, "task_id": task, "class": rs[0]["class"],
                    "k": len(rs), "n_correct": sum(flags), "unanimous": len(set(flags)) == 1,
                    "n_timeout": sum(r["timed_out"] is True for r in rs),
                    "median_thinking_tokens": median(r["thinking_tokens"] for r in rs),
                    "cv_thinking_tokens": _cv([r["thinking_tokens"] for r in rs]),
                    "median_wall_time_s": median(r["wall_time_s"] for r in rs)})
    return out


def main(argv: list[str] | None = None) -> int:
    runs, out, split = arguments("tsbench analyze effort", __doc__ or "", argv)
    rows = []
    for run in iter_runs(runs, load_tasks(split)):
        rows.append({"run_id": run.run_id, "model": run.model, "condition": run.condition, "effort": run.effort,
                     "task_id": run.task_id, "class": run.cls, "correct": run.correct, "evaluable": run.evaluable,
                     **effort_of(run.path, run.tr)})
    write_csv(out / "runs.csv", RUN_COLUMNS, rows)
    write_csv(out / "by_group.csv", GROUP_COLUMNS, _groups(rows, read_csv(runs / "metrics" / "consistency.csv")))
    timeouts = [r for r in rows if r["timed_out"] is True]
    write_csv(out / "timeouts.csv", TIMEOUT_COLUMNS, timeouts)
    write_csv(out / "tasks.csv", TASK_COLUMNS, _tasks(rows))
    write_readme(out, README)
    print(f"runs: {len(rows)}, timeouts: {len(timeouts)}, out: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
