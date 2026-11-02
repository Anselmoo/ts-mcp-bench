"""The facts of the full report: every number and every data series of the page, read from the run sets, the coverage
report and the mutation shards, as plain data (no markup, no prose).

    benchmark(run_sets, out, model=None)   the benchmark of one model
    benchmarks(run_sets, out)              the benchmark of every model, most evaluable runs first
    models_overview(benches)               one row per model for the comparison of the models
    checks(coverage, mutation_dirs, src_root, tests_dir)   tests, coverage, mutation, imports
    platform(run_sets, keep=None)          where the runs ran, their schedule, the files of a run set

The shapes are the inputs of the figure functions of `tsbench.report.svg` (see `report/full.py`). `benchmark` reads
the scored runs of the pilot tasks (`dashboard.collect`, which scores a run set that has no scores.csv) and the
transcripts of conditions B and C; it chooses one model (the one with the most evaluable runs, or the one asked for).
`benchmarks` gives the same facts for every model of the run sets from one `dashboard.collect`.
Runs that are not evaluable stay out of every count. Several runs of one task and condition (k > 1) are counted as
runs in the shares and the outcome table, and as one verdict per task (more than half of the runs correct) in the
class marks, the paired differences, the solved-set intersections, the ledger, the literature rows and the task view.
A mark that says "within the tolerance" is the `correct` flag of the scores table, never a ratio decided again. A
record that no figure reads (a run of another condition, a task outside the pilot set, a scoring failure, a missing
transcript) is counted in `notes`. Only pilot tasks are read; no file is written except the scores.csv that
`dashboard.collect` writes into a run set that lacks it.
"""
from __future__ import annotations

import ast
import collections
import hashlib
import json
import pathlib
import re
import time
from collections.abc import Collection, Iterable, Sequence
from typing import Any

from tsbench.conditions import gateway_label
from tsbench.report import dashboard, literature, quality, science, taskview
from tsbench.report.base import as_number, as_run_sets, is_true, median, share
from tsbench.report.svg.base import fixed, round_half_up
from tsbench.score.artifacts import TranscriptCache
from tsbench.score.extract import read_transcript
from tsbench.score.run_sets import RunSet
from tsbench.score.solution_path import solution_path

__all__ = ["benchmark", "benchmarks", "checks", "models_overview", "platform"]

CONDS = science.CONDS
TOP = quality.TOP
TOP_MODULES = 15  # rows of the module table of the Checks tab; the rest is one remainder row
NOT_RECORDED = "not recorded"
TOOL_PREFIX = "mcp__tanabesugano__"
STRUCTURED = "StructuredOutput"
COLLAPSE_AFTER = 12  # a folder with more files than this is one row of the file tree

# The outcome categories of the report: the fifteen of `score.taxonomy` folded into seven, in the order of the table.
CATEGORIES = [("correct", "correct"), ("gross", "gross error"), ("several", "several parameters wrong"),
              ("items", "items wrong"), ("dq", "Dq wrong"), ("bc", "B or C wrong"),
              ("limit", "limit missed / false refusal")]
OVERFLOW = ("overflow", "context overflow")
OTHER = ("other", "no valid answer")
EXTRA = [OVERFLOW, OTHER]  # more categories, each only when a run has one
FOLD = {"correct": "correct", "gross_error": "gross", "wrong_multiple": "several", "wrong_items": "items",
        "wrong_dq": "dq", "wrong_b": "bc", "wrong_c": "bc", "missed_limit": "limit", "false_refusal": "limit",
        "context_overflow": "overflow"}

COST_AXES = [("num_turns", "turns"), ("n_mcp_calls", "server calls"), ("n_bash_calls", "Bash calls"),
             ("output_tokens", "output tokens"), ("thinking_tokens", "thinking tokens"), ("duration_s", "time (s)"),
             ("api_duration_s", "API time (s)"), ("cost_usd", "cost (USD)")]
MEDIAN_KEYS = ["output_tokens", "num_turns", "api_duration_s", "cost_usd"]


# ---------------------------------------------------------------- small helpers


def _k(r: dict) -> int:
    x = as_number(r.get("k_index"))
    return int(x) if x is not None else 1


def _number(v: float | None, scale: float = 1, nd: int = 0) -> str:
    return "–" if v is None else fixed(scale * v, nd)


def _text(x: float | None, nd: int = 1) -> str:
    return "–" if x is None else fixed(x, nd)


def _read_json(path: pathlib.Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _manifest(rs: RunSet) -> dict:
    """The manifest of the run set over all its sessions (`dashboard.read_manifest`), {} when it has none."""
    return dashboard.read_manifest(rs.path) or {}


def _endpoint(manifests: Iterable[dict]) -> str:
    """The endpoints of the manifests, joined with `and`: `gateway` (the default endpoint; `gateway <host>` for the
    endpoint that `args.gateway_url` recorded), `Anthropic API`, or `not recorded` when there is no manifest."""
    args = [m.get("args") or {} for m in manifests if m]
    if not args:
        return NOT_RECORDED
    labels = sorted({gateway_label(a.get("gateway_url")) for a in args if a.get("gateway")},
                    key=lambda s: (s != "gateway", s))  # the default endpoint first
    return " and ".join([*labels, *(["Anthropic API"] if any(not a.get("gateway") for a in args) else [])])


def _distinct(values: Iterable[Any]) -> list[str]:
    return sorted({str(v) for v in values if v not in (None, "")})


def _solved(rs: list[dict]) -> bool:
    return science._solved(rs)


# ---------------------------------------------------------------- the benchmark of the models


def benchmark(run_sets: Sequence[RunSet | pathlib.Path | str], out: pathlib.Path | str,
              model: str | None = None, reader: TranscriptCache | None = None) -> dict:
    """The benchmark facts for `model` (default: the model with the most evaluable runs) over the run sets. `out` is
    the path of the page that will be written; it only fixes the relative links of `dashboard.collect`. `reader`
    reads the transcripts (default `read_transcript`); the gallery can share one with it."""
    data = dashboard.collect(run_sets, out, dashboard.load_pilot_tasks(), reader=reader)
    paths = {s["name"]: pathlib.Path(s["path"]) for s in data["sets"]}
    return _benchmark(data, paths, model, reader)


def benchmarks(run_sets: Sequence[RunSet | pathlib.Path | str], out: pathlib.Path | str,
               reader: TranscriptCache | None = None) -> dict[str, dict]:
    """The benchmark facts for every model of the run sets, keyed by model: the model with the most evaluable runs
    first, then by name. One `dashboard.collect` serves every model. A run set without runs gives one bench under the
    model name "" (as `benchmark` does)."""
    data = dashboard.collect(run_sets, out, dashboard.load_pilot_tasks(), reader=reader)
    paths = {s["name"]: pathlib.Path(s["path"]) for s in data["sets"]}
    return _benchmarks(data, paths, reader)


def _benchmarks(data: dict, paths: dict[str, pathlib.Path], reader: TranscriptCache | None = None) -> dict[str, dict]:
    return {m: _benchmark(data, paths, m, reader) for m in _models(data) or [""]}


def _models(data: dict) -> list[str]:
    """The models of the scored rows: the most evaluable runs first, then by name."""
    everyone = science._Runs(data)
    evaluable = collections.Counter(r.get("model", "") for r in everyone.rows)
    return sorted({r.get("model", "") for r in everyone.all}, key=lambda m: (-evaluable[m], m))


def models_overview(benches: dict[str, dict]) -> list[dict]:
    """One row per model in the order of `benches` (as `benchmarks` gives them): the header counts, the share correct
    of each condition with its interval (`cells`) and the paired differences as fractions (`paired`). Every value is
    copied from the bench, none is computed again."""
    out = []
    for bench in benches.values():
        h = bench["header"]
        out.append({
            **{k: h[k] for k in ("model", "endpoint", "n_runs", "n_evaluable", "k", "k_planned")},
            "conds": list(h["conds"]),
            "cells": {s["cond"]: {k: s[k] for k in ("k", "n", "tasks", "share", "lo", "hi")}
                      for s in bench["shares"]},
            "paired": {p["pair"]: {k: p[k] for k in ("diff", "lo", "hi", "p", "n")} for p in bench["paired"]},
        })
    return out


def _benchmark(data: dict, paths: dict[str, pathlib.Path], model: str | None,
               reader: TranscriptCache | None = None) -> dict:
    """`data` as `dashboard.collect` returns it; `paths` maps a run set name to its folder (the transcripts of B and C
    are read from there; with `{}` the call facts are empty)."""
    ranked = _models(data)
    models = sorted(ranked)
    if model is None:
        model = ranked[0] if ranked else ""
    mine = [r for r in data["rows"] if r.get("model", "") == model]
    runs = science._Runs({**data, "rows": mine})
    _check_run_keys(runs.rows)
    conds = [c for c in CONDS if runs.cell(model, c)]
    order = [t for t in data.get("tasks") or runs.tasks if t in runs.tasks]
    by_task = collections.defaultdict(list)
    for r in runs.rows:
        by_task[(r["_cond"], r["task_id"])].append(r)
    fit = [t for t in order if science._is_fit(runs.tasks[t])]

    classes = _classes(runs, model, conds, order, by_task)
    categories, outcome = _outcome(runs, model, conds)
    labels = dict([*categories, *EXTRA])
    reads = _transcript_facts(runs, paths, order, reader)
    cost = _cost(runs, model, conds)
    literature_rows = _literature(runs, order, by_task)
    header = _header(data, runs, model, models, conds, order)
    pilot = data.get("tasks") or runs.tasks
    upset, upset_excluded = _upset(order, by_task, conds)
    swarm = _errors(runs, model, conds, fit)
    return {
        "header": header,
        "shares": _shares(runs, model, conds),
        "paired": _paired(runs, model),
        "classes": classes,
        "categories": categories, "outcome": outcome,
        "upset": upset, "upset_excluded": upset_excluded,
        "runs": [{"cond": r["_cond"], "task": r["task_id"], "k": _k(r), "class": r["_task"]["class"],
                  "outcome": _fold(r.get("_category")), "values": {k: _measure(r, k) for k, _ in COST_AXES}}
                 for r in runs.rows],
        "completeness": _completeness(runs, by_task, conds, order, header),
        "swarm": swarm,
        "literature": literature_rows,
        "tool_use": _tool_use(runs, model),
        "cost": cost,
        "calls": reads["calls"], "tools": reads["tools"], "transitions": reads["transitions"],
        "solution_paths": reads["solution_paths"],
        "ledger": _ledger(order, by_task, runs.tasks, conds),
        "tool_output": reads["tool_output"],
        "tasks_view": taskview.tasks_view(list(pilot), pilot, by_task, conds,
                                          (header["oracle"] or "").removeprefix("tanabesugano ") or None,
                                          lambda category: labels[_fold(category)], ran=set(order)),
        "notes": [*_notes(data, mine, runs, paths), *_swarm_notes(swarm)],
    }


def _check_run_keys(rows: list[dict]) -> None:
    """A run is named by (model, condition, effort, task, k); two evaluable runs with one name are two files of one
    run (run sets of one plan read twice, or of several efforts pooled), and every count would take them for two."""
    names = collections.Counter((r.get("model", ""), r["_cond"], str(r.get("effort", "")), r["task_id"], _k(r))
                                for r in rows)
    for key, n in names.items():
        if n > 1:
            raise ValueError(f"{key[3]}: the run (model, condition, effort, task, k) = {key} occurs {n} times among "
                             "the evaluable runs of the model")


def _notes(data: dict, rows: list[dict], runs: science._Runs, paths: dict[str, pathlib.Path]) -> list[dict]:
    """The records the page does not show, as `{kind, text, count}`: the notes of `dashboard.collect` (a run set that
    failed to score, an unreadable plan; a note with a run count in `note_counts` carries that count), the runs of the
    model that no figure reads (another condition, a task outside the pilot set) and the scored B and C runs whose
    transcript is missing from a run set folder that is known."""
    counts = data.get("note_counts") or {}
    notes = [{"kind": "run set", "text": str(text), "count": counts.get(text, 1)} for text in data.get("notes") or []]
    other = sum(1 for r in rows if r.get("_cond") not in CONDS)
    outside = sum(1 for r in rows if r.get("_cond") in CONDS and not r.get("_task"))
    if other:
        notes.append({"kind": "condition", "text": "runs of a condition other than A, B and C are not counted",
                      "count": other})
    if outside:
        notes.append({"kind": "task", "text": "runs of a task outside the pilot set are not counted",
                      "count": outside})
    lost = sum(1 for r in runs.rows if r["_cond"] in ("B", "C") and r.get("_set", "") in paths
               and _transcript(paths, r) is None)
    if lost:
        notes.append({"kind": "transcript", "text": "scored B and C runs have no transcript file", "count": lost})
    return notes


def _completeness(runs: science._Runs, by_task: dict, conds: list[str], order: list[str], header: dict) -> dict:
    """How complete the run matrix is: `cells` (task x condition of the model), `short` of them with fewer evaluable
    runs than the target `k` (the planned k of the manifests, else the largest k found), `missing` runs in total, and
    the evaluable runs that were `rescued` (the answer was scored from the last StructuredOutput call after the run
    stopped on an error)."""
    k = max(header["k"], header["k_planned"] or 0)
    have = [len(by_task.get((c, t), [])) for c in conds for t in order]
    return {"k": k, "cells": len(have), "short": sum(n < k for n in have), "missing": sum(max(0, k - n) for n in have),
            "rescued": sum(is_true(r.get("rescued")) for r in runs.rows)}


def _swarm_notes(swarm: list[dict]) -> list[dict]:
    """The fit answers the error-size figure leaves out: those with a required value missing have no ratio."""
    left = sum(g["n_runs"] - len(g["values"]) for g in swarm)
    if not left:
        return []
    return [{"kind": "error size", "text": "fit answers with a required value missing are not in the error-size figure",
             "count": left}]


def _fold(category: str | None) -> str:
    return FOLD.get(str(category), "other")


def _header(data: dict, runs: science._Runs, model: str, models: list[str], conds: list[str], order: list[str]) -> dict:
    names = {r.get("_set") for r in runs.all}
    mans = [s["manifest"] for s in data.get("sets") or [] if s.get("name") in names and s.get("manifest")]
    ks = [_k(r) for r in runs.all]
    planned = [int(k) for m in mans if (k := m.get("k") or (m.get("args") or {}).get("k")) is not None]
    efforts = _distinct(r.get("effort") for r in runs.all) or _distinct(m.get("effort") for m in mans)
    starts = [m["start_time_utc"] for m in mans if m.get("start_time_utc")]
    ends = [m["end_time_utc"] for m in mans if m.get("end_time_utc")]
    commits = _distinct(str(m["git_commit"])[:7] for m in mans if m.get("git_commit"))
    oracle = _distinct(m.get("tanabesugano_version") for m in mans)
    return {"model": model, "models": models, "split": "pilot", "n_tasks": len(order),
            "n_classes": len({runs.tasks[t]["class"] for t in order}), "conds": conds, "k": max(ks, default=1),
            "k_planned": max(planned, default=None),
            "cost_is_estimate": bool(model) and not str(model).startswith("claude-"),
            "effort": ", ".join(efforts) or NOT_RECORDED,
            "n_runs": len(runs.all), "n_evaluable": len(runs.rows), "endpoint": _endpoint(mans),
            "oracle": "tanabesugano " + ", ".join(oracle) if oracle else None,
            "commit": ", ".join(commits) or None, "start": min(starts, default=None), "end": max(ends, default=None)}


def _shares(runs: science._Runs, model: str, conds: list[str]) -> list[dict]:
    """Per condition: correct runs over evaluable runs and the 95 % interval of the bootstrap over tasks."""
    out = []
    for c in conds:
        s = share(runs.cell(model, c))
        if s:
            out.append({"cond": c, "k": s["k"], "n": s["n"], "tasks": s["tasks"], "share": s["p"], "lo": s["lo"],
                        "hi": s["hi"]})
    return out


def _paired(runs: science._Runs, model: str) -> list[dict]:
    """C − A, C − B and B − A: difference in share correct per task (fractions), its 95 % interval, the tasks solved
    under one condition only, the exact McNemar p."""
    out = []
    for x in science._contrasts(runs, model).values():
        out.append({"pair": x["label"], "diff": x["pp"] / 100, "lo": x["lo"] / 100, "hi": x["hi"] / 100,
                    "only_first": x["only_x"], "only_second": x["only_y"], "n": x["n"], "p": x["p"],
                    "first_tasks": x["x_only"], "second_tasks": x["y_only"]})
    return out


def _mark(rs: list[dict]) -> bool | None:
    """The verdict of a task under one condition; None when the condition has no evaluable run of it (the task is
    then left out of that condition, not counted as unsolved)."""
    return _solved(rs) if rs else None


def _classes(runs: science._Runs, model: str, conds: list[str], order: list[str], by_task: dict) -> list[dict]:
    """One row per class in task-file order: the tolerance, and per condition one mark per task (solved, not solved,
    or None when the condition has no evaluable run of it). `k` counts the solved tasks, `n_by` the tasks with a
    mark; `n` is the number of tasks of the class."""
    names = list(dict.fromkeys(runs.tasks[t]["class"] for t in order))
    out = []
    for cls in names:
        ids = [t for t in order if runs.tasks[t]["class"] == cls]
        marks = {c: [_mark(by_task.get((c, t), [])) for t in ids] for c in conds}
        out.append({"class": cls, "n": len(ids), "tolerance": taskview.class_tolerance([runs.tasks[t] for t in ids]),
                    "tasks": ids, "marks": marks, "k": {c: sum(m is True for m in ms) for c, ms in marks.items()},
                    "n_by": {c: sum(m is not None for m in ms) for c, ms in marks.items()}})
    return out


def _outcome(runs: science._Runs, model: str, conds: list[str]) -> tuple[list[tuple[str, str]], list[dict]]:
    """The seven report categories (plus each of `EXTRA` that some run has) and the counts per condition folded into
    them."""
    folded: list[dict] = []
    for c in conds:
        rs = runs.cell(model, c)
        f = collections.Counter(_fold(r.get("_category")) for r in rs)
        folded.append({"cond": c, "counts": {k: f.get(k, 0) for k, _ in [*CATEGORIES, *EXTRA]}})
    categories = [*CATEGORIES, *(x for x in EXTRA if any(o["counts"][x[0]] for o in folded))]
    for o in folded:
        o["counts"] = {k: o["counts"][k] for k, _ in categories}
    return categories, folded


def _upset(order: list[str], by_task: dict, conds: Sequence[str] = CONDS) -> tuple[list[dict], list[str]]:
    """The tasks solved by exactly the conditions of each subset of A, B, C (all eight subsets, none first), and the
    tasks left out because a condition of `conds` has no evaluable run of them."""
    sets: dict[str, list[str]] = {k: [] for k in ("", "A", "B", "C", "AB", "AC", "BC", "ABC")}
    left_out = []
    for t in order:
        if any(not by_task.get((c, t)) for c in conds):
            left_out.append(t)
            continue
        sets["".join(c for c in CONDS if _solved(by_task.get((c, t), [])))].append(t)
    return [{"key": k, "tasks": v} for k, v in sets.items()], left_out


def _errors(runs: science._Runs, model: str, conds: list[str], fit: list[str]) -> list[dict]:
    """The error of every answer to a fit task in units of its tolerance (worst required parameter), per condition,
    with the `correct` flag of the run: the mark is filled by the flag, the ratio only places it. An answer with a
    required value missing has no ratio and no mark; `n_runs` counts the answers of the condition, with and without a
    ratio, so the figure can say how many it leaves out."""
    rank = {t: i for i, t in enumerate(fit)}
    swarm = []
    for c in conds:
        rs = sorted((r for r in runs.cell(model, c) if r["task_id"] in rank), key=lambda r: (rank[r["task_id"]], _k(r)))
        values = [{"task": r["task_id"], "ratio": v, "ok": is_true(r.get("correct"))}
                  for r in rs if (v := science._err_over_tol(r)) is not None]
        swarm.append({"cond": c, "values": values, "n_runs": len(rs)})
    return swarm


# ---- published spectra


def _literature(runs: science._Runs, order: list[str], by_task: dict) -> list[dict]:
    """One row per published system: bands, source (text, DOI, table locator), the oracle, the paper's values and the
    tolerance of the parameters the task requires, and what each condition reported (the values of one run, the first
    on the side of the verdict, `shown_k`; `ok` is the majority of the runs)."""
    table = literature.read_csv_rows()
    out = []
    for t in order:
        task = runs.tasks[t]
        if task["class"] not in science.LITERATURE:
            continue
        row = table.get(literature._norm_name(task.get("system", "")))
        source = literature.source_parts(row)
        required = [p for p in task.get("required") or () if p in literature.PARAMS]
        ref, tol = task.get("reference") or {}, task.get("tolerance") or {}
        oracle, tolerance = {p: ref.get(p) for p in required}, {p: tol.get(p) for p in required}
        paper = literature.paper_values(row)
        paper = {p: paper.get(p) for p in required}
        reported, texts = {}, {}
        for c in CONDS:
            rs = sorted(by_task.get((c, t), []), key=_k)
            if not rs:
                reported[c] = None
                continue
            shown = taskview.shown_run(rs)
            reported[c] = {**{p: as_number(shown.get(p.lower())) for p in required}, "ok": _solved(rs),
                           "n_runs": len(rs), "n_correct": sum(is_true(r.get("correct")) for r in rs),
                           "shown_k": _k(shown)}
            texts[c] = " / ".join(_number(reported[c][p]) for p in required)
        bands = list(task.get("bands_cm1") or [])
        out.append({"task": t, "class": task["class"], "system": task.get("system", ""), "dn": task.get("d_count"),
                    "geometry": task.get("geometry"), "bands": bands,
                    "bands_text": " · ".join(f"{round_half_up(b):,}".replace(",", " ") for b in bands),
                    "required": required,
                    "source": source["text"], "doi": source["doi"], "locator": source["locator"],
                    "oracle": oracle, "oracle_text": " / ".join(_number(v) for v in oracle.values()),
                    "paper": paper, "paper_text": " / ".join(_number(v) for v in paper.values()),
                    "tol": tolerance,
                    "tol_text": " / ".join("–" if v is None else format(100 * v, "g")
                                           for v in tolerance.values()) + " %",
                    "reported": reported, "reported_text": texts})
    return out


# ---- tool use, cost, calls


def _tool_use(runs: science._Runs, model: str) -> list[dict]:
    out = []
    for c in ("B", "C"):
        rs = runs.cell(model, c)
        if not rs:
            continue
        used = [r for r in rs if (as_number(r.get(science.TOOL_COL[c])) or 0) > 0]
        free = [r for r in rs if (as_number(r.get(science.TOOL_COL[c])) or 0) <= 0]
        out.append({"cond": c, "tool": "Bash" if c == "B" else "TS-MCP", "with": len(used),
                    "with_correct": sum(is_true(r.get("correct")) for r in used), "without": len(free),
                    "without_correct": sum(is_true(r.get("correct")) for r in free)})
    return out


def _measure(r: dict, key: str) -> float | None:
    """One measure of a run, None when the scores table has none (a missing API time stays missing); the wall time
    falls back to the other time column."""
    if key == "duration_s":
        return dashboard._seconds_of(r)
    return as_number(r.get(key))


def _cost(runs: science._Runs, model: str, conds: list[str]) -> dict:
    """Per run the eight measures of tokens, turns and time; the median per condition."""
    run_rows = [{"cond": r["_cond"], "task": r["task_id"], "correct": is_true(r.get("correct")),
                 "values": {k: _measure(r, k) for k, _ in COST_AXES}} for r in runs.rows]
    medians = []
    for c in conds:
        row: dict[str, Any] = {"cond": c, "n": len(runs.cell(model, c))}
        for k in MEDIAN_KEYS:
            row[k] = median(_measure(r, k) for r in runs.cell(model, c))
        medians.append(row)
    return {"axes": COST_AXES, "median_keys": MEDIAN_KEYS, "medians": medians, "runs": run_rows}


def _transcript(paths: dict[str, pathlib.Path], r: dict) -> pathlib.Path | None:
    root = paths.get(r.get("_set", ""))
    if root is None:
        return None
    p = root / r.get("model", "") / r["_cond"] / str(r.get("effort", "")) / f"{r['task_id']}-k{_k(r)}.jsonl"
    return p if p.is_file() else None


def _tool_names(events: Iterable[dict]) -> tuple[list[str], set[str]]:
    """The ordered names of the tool calls of a transcript (the prefix of the server removed) and the tools the server
    announced in the init event."""
    names, seen, init = [], set(), set()
    for ev in events:
        if ev.get("type") == "system" and ev.get("subtype") == "init":
            init |= {str(t).removeprefix(TOOL_PREFIX) for t in ev.get("tools") or [] if str(t).startswith("mcp__")}
        content = (ev.get("message") or {}).get("content")
        if ev.get("type") == "assistant" and isinstance(content, list):
            for b in content:
                if isinstance(b, dict) and b.get("type") == "tool_use":
                    uid = b.get("id")
                    if isinstance(uid, str) and uid:  # a repeated event is one call; no usable id: never merged
                        if uid in seen:
                            continue
                        seen.add(uid)
                    names.append(str(b.get("name")).removeprefix(TOOL_PREFIX))
    return names, init


def _transcript_facts(runs: science._Runs, paths: dict[str, pathlib.Path], order: list[str],
                      reader: TranscriptCache | None = None) -> dict:
    """What the transcripts of the B and C runs give, each parsed once: `calls` (the tool calls of every run in order),
    `tools` (the server tools), `transitions` (how often one call follows another in C), `tool_output` (the tool calls
    of every run with the characters each result returned) and `solution_paths` (of the B runs that called Bash)."""
    rank = {t: i for i, t in enumerate(order)}
    calls, outputs, found, transitions, init = [], [], [], collections.Counter(), set()
    for r in sorted(runs.rows, key=lambda r: (r["_cond"], r["task_id"], _k(r), r.get("_set", ""))):
        if r["_cond"] not in ("B", "C"):
            continue
        p = _transcript(paths, r)
        if p is None:
            continue
        tr = (reader or read_transcript)(p)
        names, tools = _tool_names(tr.events)
        correct = is_true(r.get("correct"))
        calls.append({"cond": r["_cond"], "task": r["task_id"], "k": _k(r), "correct": correct, "calls": names})
        outputs.append({"cond": r["_cond"], "task": r["task_id"], "k": _k(r), "correct": correct,
                        "calls": _tool_output_of(tr.events)})
        if r["_cond"] == "C":
            init |= tools
            transitions.update(zip(names, names[1:], strict=False))
        elif (as_number(r.get("n_bash_calls")) or 0) > 0:
            label = p.relative_to(paths[r["_set"]]).as_posix()
            found.append((r, solution_path(p, label=label, task=runs.tasks.get(r["task_id"]), tr=tr)))
    c_names = {n for c in calls if c["cond"] == "C" for n in c["calls"]} - {STRUCTURED}
    tools = sorted(init or c_names) + [STRUCTURED] if any(c["cond"] == "C" for c in calls) else []
    return {"calls": calls, "tools": tools, "transitions": dict(transitions), "tool_output": outputs,
            "solution_paths": _solution_paths(found, rank)}


def _run_cell(r: dict, t: dict) -> dict:
    """How far one answer is from passing, in the measure of its class: error ÷ tolerance of the worst required
    parameter (fit, `science._err_over_tol`: None when a required value is missing) or of the curve (the scorer's
    `curve_tol_ratio`); the share of correct items against the share required (diagram, batch, pairing: the lowest of
    edge F1, node precision and node recall, 0 when the ground term is wrong); for out_of_scope tasks and false
    refusals the text. `ok` is the `correct` flag of the run."""
    ok = is_true(r.get("correct"))
    cell: dict[str, Any] = {"kind": "ratio", "value": None, "ok": ok, "need": None, "text": None}
    tol, schema = t.get("tolerance") or {}, t.get("answer_schema")
    if t.get("expect_out_of_scope"):
        cell.update(kind="scope", text="named" if ok else "missed")
    elif r.get("_category") == "false_refusal":
        cell.update(kind="scope", text="refused")
    elif schema == "fit":
        cell["value"] = science._err_over_tol(r)
    elif schema == "curve":
        if "curve_tol_ratio" in r:
            cell["value"] = as_number(r["curve_tol_ratio"])
        else:  # no curve_tol_ratio column: the relative error alone
            e = as_number(r.get("curve_max_rel_err"))
            cell["value"] = None if e is None or not tol.get("curve_rel") else e / tol["curve_rel"]
    elif schema == "diagram":
        cell.update(kind="share", value=as_number(r.get("item_accuracy")), need=tol.get("item_accuracy_min"))
    elif schema == "batch":
        cell.update(kind="share", value=as_number(r.get("item_accuracy")), need=1.0)
    elif schema == "pairing":
        vals = [as_number(r.get(k)) for k in ("edge_f1", "node_precision", "node_recall")]
        have = [v for v in vals if v is not None]
        if have and r.get("ground_correct") not in (None, "") and not is_true(r["ground_correct"]):
            have.append(0.0)  # a wrong ground term fails the answer whatever its graph
        cell.update(kind="share", value=min(have) if have else None, need=1.0)
    return cell


def _ledger_cell(rs: list[dict], t: dict) -> dict:
    """The cell of a task under one condition from all its runs: `ok` is the majority of the runs. Text, kind and
    value are those of one run, the first on the side of that verdict (a run without a value leaves the value empty),
    so the mark and the verdict agree and the value is one that a run gave."""
    cells = [_run_cell(r, t) for r in rs]
    ok = _solved(rs)
    side = [c for c in cells if c["ok"] == ok] or cells
    first = side[0]
    return {**first, "ok": ok, "n_runs": len(rs),
            "n_correct": sum(c["ok"] for c in cells)}


def _ledger(order: list[str], by_task: dict, tasks: dict[str, dict], conds: list[str]) -> list[dict]:
    """The task ledger: per class (in task-file order) its tasks with one cell per condition (all runs of the task,
    by the majority rule) and the count of solved tasks per condition."""
    out: dict[str, dict] = {}
    for t in order:
        cls = tasks[t]["class"]
        cells = {}
        for c in conds:
            rs = sorted(by_task.get((c, t), []), key=_k)
            if rs:
                cells[c] = _ledger_cell(rs, tasks[t])
        block = out.setdefault(cls, {"class": cls, "k": dict.fromkeys(conds, 0), "n": 0,
                                     "n_by": dict.fromkeys(conds, 0), "tasks": []})
        block["n"] += 1
        block["tasks"].append({"task": t, "cells": cells})
        for c, cell in cells.items():
            block["k"][c] += cell["ok"]
            block["n_by"][c] += 1
    return list(out.values())


def _result_chars(content) -> int:
    """Characters of text a tool result returned: the string, or the text blocks of a list (an image counts 0)."""
    if isinstance(content, str):
        return len(content)
    return sum(len(str(x.get("text") or "")) for x in content or [] if isinstance(x, dict) and x.get("type") == "text")


def _tool_output_of(events: Iterable[dict]) -> list[dict]:
    """The tool calls of one transcript in order (without the structured answer), each with the characters of text its
    result returned to the model."""
    calls: dict[object, dict] = {}
    for e in events:
        content = (e.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        for it in content:
            if not isinstance(it, dict):
                continue
            if it.get("type") == "tool_use" and it.get("name") != STRUCTURED:
                uid = it.get("id")
                key = uid if isinstance(uid, str) and uid else object()  # no usable id: a call of its own
                calls[key] = {"tool": str(it.get("name") or "").removeprefix(TOOL_PREFIX), "chars": 0}
            elif it.get("type") == "tool_result" and isinstance(it.get("tool_use_id"), str) \
                    and it["tool_use_id"] in calls:
                calls[it["tool_use_id"]]["chars"] += _result_chars(it.get("content"))
    return list(calls.values())


def _solution_paths(found: list[tuple[dict, dict]], rank: dict[str, int]) -> list[dict]:
    """The solution path of every B run that called Bash, by task: the dict of `score.solution_path` with the task, the
    outcome and a short html id of the run beside it (and the same dict again under `path`). `found` holds the
    score row of each run with its path."""
    out, used = [], set()
    for r, path in sorted(found, key=lambda x: (rank[x[0]["task_id"]], _k(x[0]), x[0].get("_set", ""))):
        base = re.sub(r"[^A-Za-z0-9_-]", "-", f"{r['task_id']}-k{_k(r)}")
        rid, n = base, 1
        while rid in used:
            n += 1
            rid = f"{base}-s{n}"
        used.add(rid)
        out.append({**path, "id": rid, "task": r["task_id"], "correct": is_true(r.get("correct")), "k": _k(r),
                    "path": path})
    return out


# ---------------------------------------------------------------- checks of the benchmark code


def checks(coverage: pathlib.Path | str, mutation: Sequence[pathlib.Path | str], src_root: pathlib.Path | str,
           tests_dir: pathlib.Path | str | None) -> dict:
    """The facts of the code checks: the pytest result line beside the coverage report, the test functions per folder of
    `tests_dir`, line coverage per module and package, mutation per shard and module (the shard folders of every
    directory of `mutation`; a shard of the same name in a later directory replaces the earlier one), the packages and
    modules without a mutation result, coverage against mutation score, the surviving mutants, and the import graph of
    `src_root`."""
    cov_path = pathlib.Path(coverage)
    cov = _coverage(cov_path)
    mut = _mutation([pathlib.Path(d) for d in mutation])
    mutated = {m for s in mut["shards"] for m in s["_modules"]}
    module_package = {f["module"]: f["package"] for f in cov["files"]}
    covered_pkgs = {_package_of(m, module_package) for m in mutated}
    files = {f["module"]: f for f in cov["files"]}
    points: list[dict[str, Any]] = []
    for module, n in sorted(mut["_by_module"].items()):
        decided = n["killed"] + n["survived"]
        if decided and module in files:
            points.append({"module": module, "coverage": files[module]["pct"], "score": 100 * n["killed"] / decided,
                           "mutants": n["all"], "killed": n["killed"], "survived": n["survived"],
                           "score_text": _text(100 * n["killed"] / decided),
                           "coverage_text": _text(files[module]["pct"])})
    for s in mut["shards"]:
        s.pop("_modules")
    ranked = sorted(points, key=lambda p: (-p["survived"], -p["mutants"], p["module"]))
    top, rest = ranked[:TOP_MODULES], ranked[TOP_MODULES:]
    tdir = pathlib.Path(tests_dir) if tests_dir else None
    unmutated = [{"module": f["module"], "coverage": f["pct"]} for f in cov["files"]
                 if f["statements"] and f["module"] not in mutated]
    return {
        "tests": _pytest(cov_path.with_name("pytest.log")),
        "tests_per_folder": [{"label": k, "value": v} for k, v in science._test_counts(tdir)]
        if tdir and tdir.is_dir() else [],
        "coverage": cov,
        "mutation": {k: mut[k] for k in ("shards", "killed", "survived", "timeout", "no_tests", "total", "score",
                                         "score_text", "unlisted", "notes")},
        "not_mutated": [p["package"] for p in cov["packages"] if p["package"] not in covered_pkgs],
        "unmutated": unmutated,
        "points": points,
        "points_top": top,
        "points_other": _remainder(rest),
        "survivors": mut["survivors"],
        "imports": _imports(pathlib.Path(src_root), files),
        "inputs": _inputs(cov_path, [pathlib.Path(d) for d in mutation]),
    }


def _remainder(rest: list[dict]) -> dict | None:
    """The modules of the module table beyond its top rows as one row: their count, mutants, survivors and score."""
    if not rest:
        return None
    killed, survived = sum(p["killed"] for p in rest), sum(p["survived"] for p in rest)
    return {"modules": len(rest), "mutants": sum(p["mutants"] for p in rest), "survived": survived,
            "score_text": _text(100 * killed / (killed + survived)) if killed + survived else "–"}


def _inputs(cov_path: pathlib.Path, dirs: list[pathlib.Path]) -> dict[str, list[dict]]:
    """The files the code checks read, each as `<folder>/<file>` with its sha256: the coverage report, the pytest log
    beside it (when present) and the shard JSON that `_mutation` keeps for each shard name."""
    def entry(f: pathlib.Path, root: pathlib.Path) -> dict:
        return {"path": f.relative_to(root).as_posix(), "sha256": _sha256(f)}

    log = cov_path.with_name("pytest.log")
    shards: dict[str, dict] = {}
    for d in dirs:
        for sub in sorted(p for p in d.iterdir() if p.is_dir()):
            f = sub / f"{sub.name}.json"
            if f.is_file():
                shards[sub.name] = entry(f, d.parent)
    return {"coverage.json": [entry(cov_path, cov_path.parent.parent)],
            "pytest.log": [entry(log, cov_path.parent.parent)] if log.is_file() else [],
            "mutation": [shards[k] for k in sorted(shards)]}


def _pytest(path: pathlib.Path) -> dict | None:
    """The last result line of a pytest log (`2 failed, 2447 passed, 2 skipped in 848.34s (0:14:08)`), or None."""
    if not path.is_file():
        return None
    for line in reversed(path.read_text(encoding="utf-8", errors="replace").splitlines()):
        line = line.strip().strip("=").strip()
        m = re.search(r"\bin ([\d.]+)s\b", line)
        if m and re.search(r"\d+ (passed|failed|skipped|error)", line):
            n = {w: int(c) for c, w in re.findall(r"(\d+) (passed|failed|skipped|errors?)", line)}
            return {"passed": n.get("passed", 0), "failed": n.get("failed", 0) + n.get("error", 0) + n.get("errors", 0),
                    "skipped": n.get("skipped", 0), "seconds": float(m[1]), "line": line}
    return None


def _pct(covered: int, statements: int) -> float:
    return 100.0 * covered / statements if statements else 100.0


def _module_of(key: str) -> tuple[str, str]:
    """(dotted module, package) of a path relative to src/tsbench: `score/numeric.py`, `score/__init__.py`."""
    parts = key.removesuffix(".py").split("/")
    package = parts[0] if len(parts) > 1 else TOP
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(["tsbench", *parts]), package


def _package_of(module: str, known: dict[str, str]) -> str:
    if module in known:
        return known[module]
    parts = module.split(".")
    return parts[1] if len(parts) > 2 else TOP


def _coverage(path: pathlib.Path) -> dict:
    report = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(report, dict) or not isinstance(report.get("files"), dict):
        raise ValueError(f"{path.name}: not a coverage.py JSON report (no 'files')")
    files: list[dict[str, Any]] = []
    for name, rec in report["files"].items():
        key = quality.module_key(name)
        if quality.is_test_file(key):
            continue
        module, package = _module_of(key)
        s = rec["summary"]
        n, c = int(s["num_statements"]), int(s["covered_lines"])
        funcs = []
        for fn, f in (rec.get("functions") or {}).items():
            fs = int(f["summary"]["num_statements"])
            if fs:
                funcs.append({"name": fn or "(module)", "statements": fs,
                              "pct": _pct(int(f["summary"]["covered_lines"]), fs)})
        files.append({"module": module, "package": package, "statements": n, "covered": c, "pct": _pct(c, n),
                      "functions": funcs})
    files.sort(key=lambda f: f["module"])
    sums: dict[str, list[int]] = collections.defaultdict(lambda: [0, 0, 0])
    for f in files:
        x = sums[f["package"]]
        x[0], x[1], x[2] = x[0] + f["covered"], x[1] + f["statements"], x[2] + 1
    packages = [{"package": p, "covered": c, "statements": n, "pct": _pct(c, n), "modules": m}
                for p, (c, n, m) in sorted(sums.items(), key=lambda kv: (kv[0] == TOP, kv[0]))]
    c, n = sum(f["covered"] for f in files), sum(f["statements"] for f in files)
    reported = (report.get("totals") or {}).get("percent_covered")
    return {"total": {"covered": c, "statements": n, "pct": _pct(c, n),
                      "reported_pct": float(reported) if reported is not None else None},
            "timestamp": (report.get("meta") or {}).get("timestamp"), "packages": packages, "files": files}


def _function_of(module: str, mutant: str) -> str:
    """The function a mutmut mutant name stands for: `x_main__mutmut_5` is `main`, `xǁSessionǁcreate__mutmut_61` is
    `Session.create`."""
    name = mutant.removeprefix(module + ".") if mutant.startswith(module + ".") else mutant.rsplit(".", 1)[-1]
    name = re.sub(r"__mutmut_\d+$", "", name)
    if name.startswith("xǁ"):
        _, cls, method = (name.split("ǁ", 2) + ["", ""])[:3]
        return f"{cls}.{method}" if method else cls
    return name[2:] if name.startswith("x_") else name


def _mutation(dirs: list[pathlib.Path]) -> dict:
    """Merge the shard folders (`<dir>/<shard>/<shard>.json`) of the directories; a later shard replaces an earlier.
    A shard folder without its json (still running, crashed, timed out) gives a note, unless another directory holds
    the result of that shard."""
    found: dict[str, dict] = {}
    missing: set[str] = set()
    for d in dirs:
        if not d.is_dir():
            raise FileNotFoundError(f"{d.name}: no such folder")
        for sub in sorted(p for p in d.iterdir() if p.is_dir()):
            f = sub / f"{sub.name}.json"
            if f.is_file():
                rec = json.loads(f.read_text(encoding="utf-8"))
                found[str(rec.get("name") or sub.name)] = rec
            else:
                missing.add(sub.name)
    shards, survivors, unlisted = [], [], []
    notes = [{"kind": "mutation", "count": 1,
              "text": f"shard {name}: no {name}.json (still running, crashed or timed out); it is not in the results"}
             for name in sorted(missing - found.keys())]
    by_module: dict[str, dict[str, int]] = {}
    for name in sorted(found):
        rec = found[name]
        counts = rec.get("counts") or {}
        k, s = int(counts.get("killed", 0)), int(counts.get("survived", 0))
        modules = []
        summed: collections.Counter[str] = collections.Counter()
        for module, c in sorted((rec.get("per_module") or {}).items()):
            summed.update({str(key): int(v) for key, v in c.items()})
            mk, ms = int(c.get("killed", 0)), int(c.get("survived", 0))
            modules.append({"module": module, "killed": mk, "survived": ms, "timeout": int(c.get("timeout", 0)),
                            "score": 100 * mk / (mk + ms) if mk + ms else None})
            agg = by_module.setdefault(module, {"killed": 0, "survived": 0, "all": 0})
            agg["killed"] += mk
            agg["survived"] += ms
            agg["all"] += sum(int(v) for v in c.values())
        score = 100 * k / (k + s) if k + s else None
        gap = {key: int(counts.get(key, 0)) - summed.get(key, 0) for key in {*counts, *summed}}
        gap = {key: d for key, d in sorted(gap.items()) if d}
        if gap:
            notes.append({"kind": "mutation", "count": sum(abs(d) for d in gap.values()),
                          "text": f"shard {name}: the counts differ from the sum of its modules ("
                                  + ", ".join(f"{key} {int(counts.get(key, 0))} against {summed.get(key, 0)}"
                                              for key in gap) + ")"})
        shards.append({"name": name, "total": int(rec.get("total") or sum(int(v) for v in counts.values())),
                       "killed": k, "survived": s, "timeout": int(counts.get("timeout", 0)),
                       "no_tests": int(counts.get("no tests", 0)), "score": score, "score_text": _text(score),
                       "modules": modules, "_modules": {m["module"] for m in modules}})
        listed = rec.get("survivors") or []
        if s > len(listed):  # the shard counts survivors its `survivors` array does not list
            unlisted.append({"shard": name, "survived": s - len(listed)})
        for sv in listed:
            module = str(sv.get("module") or "")
            mutant = str(sv.get("mutant") or "")
            survivors.append({"shard": name, "module": module, "function": _function_of(module, mutant),
                              "mutant": mutant, "diff": str(sv.get("diff") or "")})
    k, s = sum(x["killed"] for x in shards), sum(x["survived"] for x in shards)
    score = 100 * k / (k + s) if k + s else None
    return {"shards": shards, "killed": k, "survived": s, "timeout": sum(x["timeout"] for x in shards),
            "no_tests": sum(x["no_tests"] for x in shards), "total": sum(x["total"] for x in shards), "score": score,
            "score_text": _text(score), "survivors": survivors, "unlisted": unlisted, "notes": notes,
            "_by_module": by_module}


def _imports(src_root: pathlib.Path, files: dict[str, dict]) -> dict:
    """The modules of `src_root` (the vendored package and the root `__init__` left out) with their line coverage, and
    how many import statements of one module name another: `from tsbench.score import numeric` is an edge to the module
    numeric, `from x import name` where `name` is no module an edge to x; a relative import is resolved."""
    root = src_root.name
    nodes: dict[str, dict] = {}
    parsed = []
    for f in sorted(src_root.rglob("*.py")):
        rel = f.relative_to(src_root)
        if rel.parts[0] == "_vendor" or "__pycache__" in rel.parts or rel == pathlib.Path("__init__.py"):
            continue
        parts = list(rel.with_suffix("").parts)
        is_pkg = parts[-1] == "__init__"
        if is_pkg:
            parts = parts[:-1]
        name = ".".join([root, *parts])
        nodes[name] = {"module": name, "package": rel.parts[0] if len(rel.parts) > 1 else TOP,
                       "value": files[name]["pct"] if name in files else None}
        parsed.append((name, parts if is_pkg else parts[:-1], f))
    edges: collections.Counter[tuple[str, str]] = collections.Counter()
    for name, pkg, f in parsed:
        try:
            tree = ast.parse(f.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            targets: set[str] = set()
            if isinstance(node, ast.Import):
                for a in node.names:
                    bits = a.name.split(".")
                    prefixes = (".".join(bits[:i]) for i in range(len(bits), 0, -1))
                    hit = next((x for x in prefixes if x in nodes), None)
                    if hit:
                        targets.add(hit)
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    keep = len(pkg) - (node.level - 1)
                    if keep < 0:
                        continue
                    base = [root, *pkg[:keep], *(node.module.split(".") if node.module else [])]
                else:
                    base = (node.module or "").split(".")
                full = ".".join(base)
                for a in node.names:
                    if f"{full}.{a.name}" in nodes:
                        targets.add(f"{full}.{a.name}")
                    elif full in nodes:
                        targets.add(full)
            for t in targets:
                if t != name:
                    edges[(name, t)] += 1
    return {"modules": sorted(nodes.values(), key=lambda m: m["module"]),
            "edges": sorted((a, b, n) for (a, b), n in edges.items())}


# ---------------------------------------------------------------- the platform


def platform(run_sets: Sequence[RunSet | pathlib.Path | str],
             keep: Collection[tuple[str, str, str, int]] | None = None) -> dict:
    """The facts of the platform from the manifests, the run sidecars and the files of the run sets: a table of where
    the runs ran (what the records do not hold says "not recorded"), the schedule of the runs, and the file tree of the
    first run set with the hash links between its files, and per run set the count of its hash links and the links
    that do not match (`chains`: {set, links, broken}). `keep` is the set of (model, condition, task, k) of the
    evaluable runs of the analysed models: the schedule holds those runs only, and `notes` counts the runs of `keep`
    that have no sidecar. A sidecar without a model field matches when `keep` names exactly one model. Without `keep`
    the schedule holds every run of a pilot task."""
    sets = as_run_sets(run_sets)
    mans = [m for m in (_manifest(rs) for rs in sets) if m]
    schedule = _schedule(sets, mans, keep)
    trees = [_tree(rs.path) for rs in sets]
    chains = [{"set": rs.name, "links": len(t["chain"]), "broken": [x for x in t["chain"] if not x["ok"]]}
              for rs, t in zip(sets, trees, strict=True)]
    return {"rows": _platform_rows(mans), "schedule": schedule, "notes": _schedule_notes(schedule, keep),
            "tree": trees[0] if trees else {"entries": [], "chain": [], "hashes": {}}, "chains": chains}


def _schedule_notes(schedule: dict, keep: Collection[tuple[str, str, str, int]] | None) -> list[dict]:
    """The runs that the schedule lacks against `keep`, as one note with their count."""
    if keep is None:
        return []
    seen = {(r["model"], r["cond"], r["task"], r["k"]) for r in schedule["runs"]}
    lost = len(set(keep) - seen)
    return [{"kind": "schedule", "text": "evaluable runs have no sidecar with a start time and are not in the schedule",
             "count": lost}] if lost else []


def distinct_row(item: str, values: Iterable[Any], source: str = "MANIFEST.json") -> dict:
    """A table row `{item, value, source}`: the distinct values joined with a comma, or "not recorded" with the source
    "–" when there are none. The platform table and the method page both build their rows with it."""
    got = _distinct(values)
    return {"item": item, "value": ", ".join(got) if got else NOT_RECORDED, "source": source if got else "–"}


def _platform_rows(mans: list[dict]) -> list[dict]:
    rows = [distinct_row("Host", (m.get("host") for m in mans)),
            distinct_row("Operating system", (m.get("platform") for m in mans)),
            distinct_row("Python", (str(m.get("python_version", "")).split(" ")[0] for m in mans)),
            distinct_row("Claude Code client", (str((m.get("claude_version") or {}).get("real", "")).split(" ")[0]
                                                 for m in mans)),
            {"item": "Model endpoint", "value": _endpoint(mans), "source": "MANIFEST.json" if mans else "–"},
            distinct_row("Oracle and server", ("tanabesugano " + str(m["tanabesugano_version"]) for m in mans
                                      if m.get("tanabesugano_version")))]
    stacks = [m["b_stack"] for m in mans if isinstance(m.get("b_stack"), dict)]
    if stacks:
        rows.append(distinct_row("B stack · Python", (s.get("python") for s in stacks), "MANIFEST.json (b_stack)"))
        for pkg in sorted({p for s in stacks for p in (s.get("packages") or {})}):
            rows.append(distinct_row(f"B stack · {pkg}", ((s.get("packages") or {}).get(pkg) for s in stacks),
                            "MANIFEST.json (b_stack)"))
    else:
        rows.append(distinct_row("B stack", []))
    rows.append(distinct_row("CPU cores, memory", []))
    rows.append(distinct_row("CPU steal time", []))
    return rows


def _schedule(sets: list[RunSet], mans: list[dict], keep: Collection[tuple[str, str, str, int]] | None = None) -> dict:
    """Model, start, length and cost of every run of a pilot task (from the `.meta.json` beside each transcript; a
    length or cost the sidecar lacks is None, and so is a cost it calls `cost_unknown`), and the totals of the
    manifests. `cost_is_estimate` is True for a model that is not a Claude model: Claude Code prices it at Claude
    list prices, so its cost is no real cost. With `keep` only the runs of that set; a sidecar without a model field
    takes the model of `keep` when it names one model, and is left out otherwise. Without `keep` the model of such a
    sidecar is None."""
    pilot = dashboard.load_pilot_tasks()
    named = {key[0] for key in keep} if keep is not None else set()
    only = next(iter(named)) if len(named) == 1 else None
    runs = []
    for rs in sets:
        for f in sorted(rs.path.rglob("*.meta.json")):
            if "_sandbox_probe" in f.parts or "views" in f.parts or ".attempt" in f.name:
                continue
            m = _read_json(f)
            model = m.get("model") or only
            if m.get("task_id") in pilot and m.get("condition") in CONDS and m.get("started_utc"):
                k = as_number(m.get("k"))
                if k is None:
                    found = re.search(r"-k(\d+)\.meta\.json$", f.name)
                    k = int(found[1]) if found else 1
                if keep is not None and (model, m["condition"], m["task_id"], int(k)) not in keep:
                    continue
                runs.append({"model": model, "cond": m["condition"], "task": m["task_id"], "k": int(k),
                             "start": str(m["started_utc"]), "seconds": as_number(m.get("wall_time_s")),
                             "cost": None if m.get("cost_unknown") else as_number(m.get("cost_usd")),
                             "cost_is_estimate": bool(model) and not str(model).startswith("claude-")})
    runs.sort(key=lambda r: (r["start"], r["cond"], r["task"]))
    counts = [m["counts"] for m in mans if isinstance(m.get("counts"), dict)]
    starts = [m["start_time_utc"] for m in mans if m.get("start_time_utc")]
    ends = [m["end_time_utc"] for m in mans if m.get("end_time_utc")]
    costs = [m["total_cost_usd"] for m in mans if m.get("total_cost_usd") is not None]

    def total(key: str) -> int | None:
        got = [c[key] for c in counts if c.get(key) is not None]
        return sum(got) if got else None

    return {"runs": runs, "manifest": {"start": min(starts, default=None), "end": max(ends, default=None),
                                       "planned": total("planned"), "done": total("done"),
                                       "skipped": total("skipped"), "total_cost": sum(costs) if costs else None}}


SETTLED_S = 60  # a file not written for this long keeps its digest in `_DIGESTS`
_DIGESTS: dict[tuple[str, int, int], str] = {}


def _sha256(path: pathlib.Path) -> str:
    """The sha256 of a file. One render hashes the same transcripts for the file tree and for the provenance table:
    the digest of a file that has not been written for `SETTLED_S` seconds is kept by path, size and time stamp. A
    file written a moment ago is read every time, since two writes may share one time stamp."""
    st = path.stat()
    key = (str(path), st.st_size, st.st_mtime_ns)
    if key in _DIGESTS:
        return _DIGESTS[key]
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    if time.time_ns() - st.st_mtime_ns > SETTLED_S * 1_000_000_000:
        _DIGESTS[key] = h.hexdigest()
    return h.hexdigest()


def _tree(root: pathlib.Path) -> dict:
    """The files of a run set as a depth-first listing (folders first, each level by lower-case name), with bytes and
    sha256, and the links of the hash chain that its records state: the hash of `from` is recorded in `field` of `to`.
    A folder with many files is one row with `n_files`. The `<task>-k<i>.figs` and `.code` folders that the report and
    the scorer write beside a transcript are left out."""
    entries: list[dict] = []

    def ours(p: pathlib.Path) -> bool:
        return any(part.endswith((".figs", ".code")) for part in p.relative_to(root).parts)

    def walk(d: pathlib.Path) -> None:
        kids = sorted((p for p in d.iterdir() if not ours(p)), key=lambda p: p.name.lower())
        folders, files = [p for p in kids if p.is_dir()], [p for p in kids if not p.is_dir()]
        for p in folders:
            rel = p.relative_to(root).as_posix()
            own = [f for f in p.iterdir() if f.is_file()]
            e = {"path": rel, "bytes": sum(f.stat().st_size for f in p.rglob("*") if f.is_file() and not ours(f)),
                 "is_dir": True, "hash": None}
            if len(own) > COLLAPSE_AFTER:
                e["n_files"] = len(own)
            entries.append(e)
            walk(p)
        if d != root and len([f for f in files]) > COLLAPSE_AFTER:
            return
        for p in files:
            entries.append({"path": p.relative_to(root).as_posix(), "bytes": p.stat().st_size, "is_dir": False,
                            "hash": _sha256(p)})

    walk(root)
    by = {e["path"]: e for e in entries}
    manifest, hashes = _read_json(root / "MANIFEST.json"), _read_json(root / "inputs" / "hashes.json")
    chain: list[dict[str, Any]] = []

    def link(src: str, dst: str, field: str, ok: bool) -> None:
        chain.append({"from": src, "to": dst, "field": field, "ok": ok})

    plan = "inputs/plan.jsonl" if "inputs/plan.jsonl" in by else "plan.jsonl"
    plan_hash = by.get(plan, {}).get("hash")
    if plan_hash:
        if manifest.get("plan_sha256"):
            link(plan, "MANIFEST.json", "plan_sha256", manifest["plan_sha256"] == plan_hash)
        if hashes.get("plan_file_sha256"):
            link(plan, "inputs/hashes.json", "plan_file_sha256", hashes["plan_file_sha256"] == plan_hash)
    recorded = root / "plan.sha256"
    if "plan.jsonl" in by and recorded.is_file() and by["plan.jsonl"]["hash"]:
        link("plan.jsonl", "plan.sha256", "plan.sha256",
             recorded.read_text(encoding="utf-8").split()[:1] == [by["plan.jsonl"]["hash"]])
    if plan_hash:
        # the plan id is no hash of the file: it is a link when both records that name it agree
        agree = not (manifest.get("plan_id") and hashes.get("plan_id")) or manifest["plan_id"] == hashes["plan_id"]
        if manifest.get("plan_id"):
            link(plan, "MANIFEST.json", "plan_id", agree)
        if hashes.get("plan_id"):
            link(plan, "inputs/hashes.json", "plan_id", agree)
    folders: dict[str, list[bool]] = collections.defaultdict(list)
    for key, sha in (manifest.get("transcripts") or {}).items():
        f = root / f"{key}.jsonl"
        folders[key.rsplit("/", 1)[0] if "/" in key else ""].append(f.is_file() and _sha256(f) == sha)
    for folder, ok in sorted(folders.items()):
        if folder in by:
            link(folder, "MANIFEST.json", "transcripts", all(ok))
    return {"entries": entries, "chain": chain,
            "hashes": {k: v for k, v in hashes.items() if isinstance(v, str | int | bool)}}
