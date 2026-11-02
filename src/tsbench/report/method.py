"""Method and traceability of the full report: what was measured, how, with which interval, from which files, and what
was left out, as tables. Every value is read from a file (the task-set hash, the manifests, the prompt files, the
scores tables, `tsbench.core.intervals`) or from the facts it is given, never typed in.

    facts(run_sets, benches, checks, platform, version=...)   the tables of the tab "Method and platform"

Keys: `identity`, `protocol`, `statistics`, `class_intervals`, `provenance`, `exclusions`, `limits`
(each a list of row dicts, except `protocol`: a dict with the lists `conditions` and `settings`).
`benches` holds the facts of every model (`facts.benchmarks`):
`class_intervals` and `exclusions` have one block per model, the other tables are those of the whole run set.
A table row that the records do not hold says "not recorded" and has the source "–".

A source file of `SOURCES` is named by a token: `run:<path or glob>` in every run set, `pkg:<resource id or glob>` in
the package data, `ext:<name>` for a file the caller of the report names (the coverage report and the mutation shards,
hashed by `facts.checks` under `inputs`; the test and source trees are named only). `run:transcripts` is every
transcript of a run set, checked against the hashes of its manifest.
The sha256 of a glob is the sha256 of its listing, one `<sha256>  <path>` line per file in path order.
"""
from __future__ import annotations

import csv
import datetime
import hashlib
import inspect
import json
import pathlib
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from tsbench.core import intervals, resource
from tsbench.plan import DEFAULT_SYSTEM_PROMPT
from tsbench.report import facts as facts_mod
from tsbench.report import science
from tsbench.report.base import as_bool, as_run_sets, is_true, pilot_hash
from tsbench.score.run_sets import RunSet
from tsbench.stats import analysis

__all__ = ["SMALL_CLASS", "SOURCES", "facts"]

NOT_RECORDED = facts_mod.NOT_RECORDED
ALL_MODELS = "all models"  # the model of an exclusion that belongs to the run set, not to one model
SMALL_CLASS = 5  # a class with fewer tasks than this is counted in the limits
TRANSCRIPTS = "*/*/*/*.jsonl"
TRANSCRIPT_NAME = re.compile(r"-k\d+\.jsonl$")  # a run's transcript, not an earlier attempt (`-k1.attempt1.jsonl`)
SKIP_PARTS = {"views", "_sandbox_probe"}  # folders beside the transcripts that hold no transcript

_SCORED = ["model", "condition", "task_id", "k_index", "evaluable", "correct"]
_COST = ["num_turns", "n_mcp_calls", "n_bash_calls", "output_tokens", "thinking_tokens", "duration_s",
         "api_duration_s", "cost_usd"]
_ERR = ["rel_err_dq", "rel_err_b", "rel_err_c", "curve_max_rel_err", "item_accuracy", "edge_f1", "node_precision",
        "node_recall", "median_rel_error", "answer_out_of_scope", "unparseable", "ground_correct"]
# what makes a run without an answer a category
_STOP = ["has_result", "result_subtype", "is_error", "context_overflow", "rescued"]
_CALLS = ["tool_use blocks (name)", "tool_result blocks (content)", "init event (tools)"]
_TESTS = ["tests/ (test functions per folder)"]
_COV = ["files.*.summary", "files.*.functions", "totals.percent_covered"]
_MUT = ["name", "total", "counts", "modules", "survivors"]

# Page key -> {"files": [token], "fields": [field names]}: the files and fields each figure and table of the page reads.
SOURCES: dict[str, dict[str, list[str]]] = {
    "share": {"files": ["run:scores.csv", "pkg:tasks/tasks.jsonl"], "fields": _SCORED},
    "paired": {"files": ["run:scores.csv", "pkg:tasks/tasks.jsonl"], "fields": _SCORED},
    "outcome": {"files": ["run:scores.csv", "pkg:tasks/tasks.jsonl"], "fields": [*_SCORED, *_ERR, *_STOP]},
    "swarm": {"files": ["run:scores.csv", "pkg:tasks/tasks.jsonl"], "fields": [*_SCORED, *_ERR[:3], "tolerance"]},
    "sunburst": {"files": ["run:transcripts"], "fields": _CALLS},
    "tool_output": {"files": ["run:transcripts"], "fields": _CALLS},
    "matrix": {"files": ["run:transcripts"], "fields": _CALLS},
    "cost": {"files": ["run:scores.csv"], "fields": [*_SCORED, *_COST]},
    "cost_map": {"files": ["run:scores.csv"], "fields": [*_SCORED, "cost_usd"]},
    "upset": {"files": ["run:scores.csv", "pkg:tasks/tasks.jsonl"], "fields": _SCORED},
    "classes": {"files": ["run:scores.csv", "pkg:tasks/tasks.jsonl"], "fields": [*_SCORED, "class", "tolerance"]},
    "ledger": {"files": ["run:scores.csv", "pkg:tasks/tasks.jsonl"], "fields": [*_SCORED, *_ERR, "required"]},
    "literature": {"files": ["run:scores.csv", "pkg:tasks/tasks.jsonl", "pkg:literature/*.csv"],
                   "fields": [*_SCORED, "dq", "b", "c", "system", "source", "location", "Dq_cm-1", "DqB_reported",
                              "CB_reported", "DqB_aux_diagram", "CB_aux_diagram"]},
    "header": {"files": ["run:MANIFEST.json", "run:scores.csv"],
               "fields": ["start_time_utc", "end_time_utc", "git_commit", "tanabesugano_version", "effort", "k",
                          "args", *_SCORED]},
    "tasks": {"files": ["pkg:tasks/tasks.jsonl", "run:scores.csv", "run:transcripts"],
              "fields": ["id", "class", "params", "reference", "required", "tolerance", "prompt", *_SCORED]},
    "per_folder": {"files": ["ext:tests"], "fields": _TESTS},
    "packages": {"files": ["ext:coverage.json"], "fields": _COV},
    "treemap": {"files": ["ext:coverage.json"], "fields": _COV},
    "shards": {"files": ["ext:mutation"], "fields": _MUT},
    "mutants": {"files": ["ext:mutation"], "fields": _MUT},
    "scatter": {"files": ["ext:coverage.json", "ext:mutation"], "fields": [*_COV, *_MUT]},
    "bundle": {"files": ["ext:src"], "fields": ["import statements"]},
    "schedule": {"files": ["run:*/*/*/*.meta.json", "run:MANIFEST.json"],
                 "fields": ["condition", "task_id", "started_utc", "wall_time_s", "cost_usd", "counts"]},
    "tree": {"files": ["run:MANIFEST.json", "run:inputs/hashes.json", "run:inputs/plan.jsonl", "run:plan.sha256",
                       "run:transcripts"],
             "fields": ["plan_sha256", "plan_id", "plan_file_sha256", "transcripts"]},
    "platform": {"files": ["run:MANIFEST.json"],
                 "fields": ["host", "platform", "python_version", "claude_version", "args", "b_stack",
                            "tanabesugano_version"]},
    "notes": {"files": ["run:scores.csv", "run:transcripts", "ext:mutation"], "fields": ["notes"]},
    "identity": {"files": ["pkg:tasks/tasks.sha256", "run:MANIFEST.json"],
                 "fields": ["git_commit", "git_dirty", "plan_id", "plan_sha256", "tasks_sha256"]},
    "protocol": {"files": ["pkg:prompts/*.txt", "pkg:conditions/ts.json", "pkg:conditions/b-stack.txt",
                           "run:MANIFEST.json"],
                 "fields": ["models_requested", "reported_models", "effort", "k", "budget_usd", "args",
                            "sandbox_settings_sha256", "b_stack"]},
    "statistics": {"files": ["run:scores.csv"], "fields": ["correct", "evaluable", "task_id", "condition"]},
    "class_intervals": {"files": ["run:scores.csv", "pkg:tasks/tasks.jsonl"], "fields": [*_SCORED, "class"]},
    "provenance": {"files": ["run:MANIFEST.json", "run:scores.csv", "run:transcripts"], "fields": ["transcripts"]},
    "exclusions": {"files": ["run:scores.csv"], "fields": ["evaluable", "not_evaluable_reason", "model"]},
    "limits": {"files": ["run:MANIFEST.json", "run:scores.csv"],
               "fields": ["models_requested", "k", "start_time_utc", "end_time_utc", "is_error"]},
}


def facts(run_sets: Sequence[RunSet | pathlib.Path | str], benches: Mapping[str, dict], checks: dict | None,
          platform: dict, *, version: str) -> dict:
    """The method tables; `version` is `full.REPORT_VERSION`. `benches` are the benchmark facts per model, in the
    order of `facts.benchmarks`; `checks` and `platform` are the facts of the code checks and the platform (they may be
    None / empty without effect on the tables)."""
    sets = as_run_sets(run_sets)
    mans = [facts_mod._manifest(rs) for rs in sets]
    rows = _scores(sets)
    return {
        "identity": _identity(sets, mans, version),
        "protocol": _protocol(sets, mans, benches),
        "statistics": _statistics(),
        "class_intervals": _class_intervals(benches),
        "provenance": _provenance(sets, (checks or {}).get("inputs") or {}),
        "exclusions": _exclusions(rows, benches, sets, mans),
        "limits": _limits(benches, sets, mans, rows, platform or {}),
    }


# ---------------------------------------------------------------- small helpers


def _yes(v: Any) -> bool:
    return str(v).lower() in ("yes", "true", "1")


def _suffixed(item: str, rs: RunSet, many: bool) -> str:
    return f"{item} · {rs.name}" if many else item


def _scores(sets: list[RunSet]) -> list[dict]:
    """The rows of the scores tables of the run sets, every model."""
    rows: list[dict] = []
    for rs in sets:
        path = rs.path / "scores.csv"
        if path.is_file():
            with path.open(encoding="utf-8", newline="") as fh:
                rows += list(csv.DictReader(fh))
    return rows


# ---------------------------------------------------------------- identity


def _identity(sets: list[RunSet], mans: list[dict], version: str) -> list[dict]:
    """Report version, task-set hash, build time and, per run set, the folder, code commit, plan and task-set hash of
    its manifest (a hash that differs from the task file is marked "differs")."""
    pilot = pilot_hash() or NOT_RECORDED
    built = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d %H:%M UTC")
    rows = [{"item": "Report version", "value": version, "source": "report/full.py (REPORT_VERSION)"},
            {"item": "Task set (pilot) sha256", "value": pilot, "source": "tasks/tasks.sha256"},
            {"item": "Page built", "value": built, "source": "clock"}]
    many = len(sets) > 1
    for rs, m in zip(sets, mans, strict=True):
        commit = str(m["git_commit"])[:7] + (", working tree modified" if _yes(m.get("git_dirty"))
                                             else ", working tree clean") if m.get("git_commit") else None
        recorded = m.get("tasks_sha256")
        check = None if not recorded else \
            f"{recorded} (matches the task file)" if recorded == pilot else f"{recorded} (differs from the task file)"
        rows += [{"item": _suffixed("Run set", rs, many), "value": rs.name, "source": "folder name"},
                 facts_mod.distinct_row(_suffixed("Code commit", rs, many), [commit]),
                 facts_mod.distinct_row(_suffixed("Plan id", rs, many), [m.get("plan_id")]),
                 facts_mod.distinct_row(_suffixed("Plan sha256", rs, many), [m.get("plan_sha256")]),
                 facts_mod.distinct_row(_suffixed("Task set of the run", rs, many), [check])]
    return rows


# ---------------------------------------------------------------- protocol


PLAN_FILES = ("inputs/plan.jsonl", "plan.jsonl")  # the plan of a run set: the copy the run took its input from first


def _plan(rs: RunSet) -> tuple[dict, list[dict]]:
    """The header and the run records of the plan of a run set; ({}, []) when it has none. A line that is no JSON
    object is skipped."""
    for name in PLAN_FILES:
        path = rs.path / name
        if not path.is_file():
            continue
        header: dict = {}
        runs: list[dict] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if isinstance(rec, dict) and rec.get("kind") == "header":
                header = rec
            elif isinstance(rec, dict) and rec.get("kind") == "run":
                runs.append(rec)
        return header, runs
    return {}, []


def _package_prompt() -> tuple[str, str]:
    """(file name, sha256) of the default prompt of the package data."""
    name = pathlib.PurePosixPath(DEFAULT_SYSTEM_PROMPT).name
    return name, next((facts_mod._sha256(f) for f in resource("prompts").glob("*.txt") if f.name == name),
                      NOT_RECORDED)


def _b_stack(mans: list[dict]) -> str:
    """The packages the B stack pins first (the ones the benchmark names), from b-stack.txt, each with the version the
    run recorded in its manifest (`b_stack.packages`) when it has one. Run sets with different stacks give one
    text each."""
    pins = [ln.split("==") for ln in resource("conditions/b-stack.txt").read_text(encoding="utf-8").splitlines()
            if "==" in ln and not ln.startswith("#")][:4]
    recorded = [{str(k).lower(): v for k, v in ((m.get("b_stack") or {}).get("packages") or {}).items()}
                for m in mans] or [{}]
    texts = [", ".join(f"{name} {got.get(name.lower(), ver)}" for name, ver in pins) for got in recorded]
    return " | ".join(dict.fromkeys(texts))


def _protocol(sets: list[RunSet], mans: list[dict], benches: Mapping[str, dict]) -> dict:
    """The conditions, each with the prompt files its runs used (file, sha256 and run count from the plan of the run
    sets; the default prompt of the package only when no run set has a plan) and the run settings. The tools of C are
    those the init events of every model announced, each once, in the order first seen."""
    server = next(iter(json.loads(resource("conditions/ts.json").read_text(encoding="utf-8"))["mcpServers"]), "")
    tools = list(dict.fromkeys(t for bench in benches.values() for t in bench.get("tools") or []))
    names = {"A": "none", "B": f"Bash, with the B stack ({_b_stack(mans)})",
             "C": f"server {server}: " + ", ".join(tools) if tools else f"server {server}"}
    used: dict[str, Counter[tuple[str, str]]] = {c: Counter() for c in names}
    planned = False
    for rs in sets:
        runs = _plan(rs)[1]
        planned = planned or bool(runs)
        for r in runs:
            if r.get("condition") in used:
                used[r["condition"]][(pathlib.PurePosixPath(str(r.get("system_prompt_file") or "")).name,
                                      str(r.get("system_prompt_sha256") or NOT_RECORDED))] += 1
    default, sha = _package_prompt()
    conditions = []
    for cond, tools_text in names.items():
        # the package prompt stands in only when no run set has a plan; a condition the plan does not run shows 0 runs
        prompts = sorted(used[cond].items())
        if not prompts:
            prompts = [(("–", None), 0)] if planned else [((default, sha), None)]
        conditions += [{"cond": cond, "tools": tools_text, "prompt": name, "sha256": digest, "runs": n,
                        "source": "plan.jsonl" if n is not None else "package data (no plan)"}
                       for (name, digest), n in prompts]
    return {"conditions": conditions, "settings": _settings(sets, mans)}


def _recorded_max_turns(rs: RunSet) -> tuple[dict[str, set[int]], str]:
    """The turn limit of each condition: from the run records of the plan, else from the sidecars of the runs.
    Returns ({condition: limits}, source)."""
    got: dict[str, set[int]] = {}
    for r in _plan(rs)[1]:
        if r.get("max_turns") is not None and r.get("condition"):
            got.setdefault(r["condition"], set()).add(r["max_turns"])
    if got:
        return got, "plan.jsonl (max_turns)"
    for meta in sorted(rs.path.glob("*/*/*/*.meta.json")):
        side = facts_mod._read_json(meta)
        if side.get("max_turns") is not None and side.get("condition"):
            got.setdefault(side["condition"], set()).add(side["max_turns"])
    return got, "*.meta.json (max_turns)"


def _settings(sets: list[RunSet], mans: list[dict]) -> list[dict]:
    args = [m.get("args") or {} for m in mans]
    sandbox = [m.get("sandbox_settings_sha256") or ((m.get("sandbox") or {}).get("probe") or {})
               .get("sandbox_settings_sha256") for m in mans]
    reported = [f"{model}: " + "; ".join(f"{c} {', '.join(names)}" for c, names in sorted(by.items()))
                for m in mans for model, by in (m.get("reported_models") or {}).items()]
    stack = [(m.get("b_stack") or {}).get("digest") for m in mans]
    ks = [m.get("k") if m.get("k") is not None else a.get("k") for m, a in zip(mans, args, strict=True)]
    plans = [_plan(rs)[0] for rs in sets]
    # per run set: a cap the arguments record as a number wins (the plan header always writes null); a cap that the
    # plan or the arguments record as null reads "none"; one that neither records stays "not recorded"
    caps: list[Any] = []
    for h, a in zip(plans, args, strict=True):
        if a.get("per_call_usd") is not None:
            caps.append(a["per_call_usd"])
            continue
        caps += ["none" if h[k] is None else h[k] for k in ("per_call_cap",) if k in h]
        caps += ["none" for k in ("per_call_usd",) if k in a]
    turns = [_recorded_max_turns(rs) for rs in sets]
    limits = [", ".join(f"{c} {'/'.join(map(str, sorted(v)))}" for c, v in sorted(got.items()))
              for got, _ in turns if got]
    turns_source = next((src for got, src in turns if got), "–")
    return [
        facts_mod.distinct_row("Models requested", (x for m in mans for x in m.get("models_requested") or [])),
        facts_mod.distinct_row("Models reported by the endpoint", reported),
        facts_mod.distinct_row("Effort", (m.get("effort") for m in mans)),
        facts_mod.distinct_row("Runs per task planned (k)", ks),
        facts_mod.distinct_row("Budget (USD)", (m.get("budget_usd") for m in mans)),
        facts_mod.distinct_row("Per-call cap (USD)", caps,
                               "plan.jsonl (per_call_cap), MANIFEST.json (args.per_call_usd)"),
        facts_mod.distinct_row("Maximum turns", limits, turns_source),
        facts_mod.distinct_row("Sandbox settings sha256", sandbox),
        facts_mod.distinct_row("B stack digest", stack, "MANIFEST.json (b_stack)"),
    ]


# ---------------------------------------------------------------- statistics and class intervals


def _statistics() -> list[dict]:
    """The methods behind every interval and p value; the parameters are read from the code that computes them."""
    paired = inspect.signature(analysis.bootstrap_ci).parameters
    boot = f"{intervals.RESAMPLES} resamples, seed {intervals.SEED}"
    return [
        {"quantity": "Share correct", "definition": "Correct runs divided by evaluable runs of one condition.",
         "parameters": "runs that are not evaluable stay out of numerator and denominator"},
        {"quantity": "95 % interval of a share",
         "definition": "Percentile interval of a task-clustered bootstrap: tasks resampled with replacement, the runs "
                       "of a task kept together; statistic = correct runs ÷ runs over the resampled tasks.",
         "parameters": boot},
        {"quantity": "Task verdict", "definition": "A task is solved under a condition when more than half of its "
         "evaluable runs are correct.", "parameters": "applies to classes, paired differences and solved sets"},
        {"quantity": "Paired difference",
         "definition": "Mean over tasks of the difference in per-task share correct, in percentage points, over the "
                       "tasks with runs under both conditions; percentile interval, tasks resampled.",
         "parameters": f"{paired['n_boot'].default} resamples, seed {paired['seed'].default}, "
                       f"alpha {paired['alpha'].default}"},
        {"quantity": "Exact McNemar p",
         "definition": "Two-sided exact test of the tasks solved by one condition only (b and c): "
                       "p = min(1, 2 · P(X ≤ min(b, c))) with X binomial(b + c, 1/2).",
         "parameters": "descriptive; no hypothesis is tested in the pilot"},
        {"quantity": "Error ratio", "definition": "Relative error of the worst required parameter of a fit answer "
         "divided by its tolerance.", "parameters": "tolerance of the task record"},
        {"quantity": "Class interval",
         "definition": "k of n tasks solved; 95 % interval of the same bootstrap over the 0/1 task verdicts.",
         "parameters": boot},
    ]


def _class_intervals(benches: Mapping[str, dict]) -> list[dict]:
    """Per model, class and condition: tasks solved (k) of the tasks (n) and the bootstrap interval of the task
    verdicts, one block of classes per model in the order of `benches`. The verdicts are the marks of
    `bench["classes"]` (`facts._solved`); a task with no evaluable run under a condition has no mark (None) and is left
    out of that condition's k and n. A class of two tasks says n = 2."""
    out = []
    for model, bench in benches.items():
        conds = (bench.get("header") or {}).get("conds") or list(science.CONDS)
        for c in bench.get("classes") or []:
            cells = {}
            for cond in conds:
                solved = [int(bool(m)) for m in (c.get("marks") or {}).get(cond, []) if m is not None]
                lo, hi = intervals.cluster_bootstrap(solved, [1] * len(solved)) if solved else (None, None)
                cells[cond] = {"k": sum(solved), "n": len(solved), "lo": lo, "hi": hi}
            out.append({"model": model, "class": c["class"], "n": c["n"], "cells": cells})
    return out


# ---------------------------------------------------------------- provenance


def _digest(entries: list[tuple[str, str]]) -> str:
    return hashlib.sha256("".join(f"{sha}  {path}\n" for path, sha in sorted(entries)).encode("utf-8")).hexdigest()


def _file(path: pathlib.Path, shown: str) -> dict:
    if not path.is_file():
        return {"path": shown, "sha256": None, "verified": "not found"}
    return {"path": shown, "sha256": facts_mod._sha256(path), "verified": None}


def _glob(root: pathlib.Path, pattern: str, shown: str, recorded: dict | None = None,
          name: re.Pattern[str] | None = None) -> dict:
    """One entry for the files of a glob: their count, the digest of their listing and, when the manifest records
    hashes, how many of them match. With `name`, only the files whose name it finds are listed."""
    files = sorted(p for p in root.glob(pattern) if p.is_file() and not SKIP_PARTS & set(p.relative_to(root).parts)
                   and (name is None or name.search(p.name)))
    hashes = [(p.relative_to(root).as_posix(), facts_mod._sha256(p)) for p in files]
    entry = {"path": f"{shown}/{pattern}", "sha256": _digest(hashes) if hashes else None, "count": len(hashes),
             "verified": None}
    if recorded is not None:
        names = {p: sha for p, sha in hashes}
        ok = sum(1 for key, sha in recorded.items() if names.get(f"{key}.jsonl") == sha)
        entry["verified"] = f"{ok} of {len(recorded)} recorded hashes match"
    return entry


def _resolve(token: str, sets: list[RunSet], inputs: dict[str, list[dict]]) -> list[dict]:
    kind, _, name = token.partition(":")
    if kind == "ext":
        if inputs.get(name):
            return [{**e, "verified": None} for e in inputs[name]]
        return [{"path": name, "sha256": None, "verified": "named by the caller, not hashed"}]
    if kind == "pkg":
        rel = pathlib.PurePosixPath(name)
        shown = pathlib.PurePosixPath("tsbench", "data")
        try:
            if "*" in name:
                return [_glob(resource(str(rel.parent)), rel.name, str(shown / rel.parent))]
            return [_file(resource(name), str(shown / rel))]
        except FileNotFoundError:
            return [{"path": str(shown / rel), "sha256": None, "verified": "not found"}]
    out = []
    for rs in sets:
        if name == "transcripts":
            recorded = facts_mod._manifest(rs).get("transcripts")
            out.append(_glob(rs.path, TRANSCRIPTS, rs.name, recorded if isinstance(recorded, dict) else None,
                             TRANSCRIPT_NAME))
        elif "*" in name:
            out.append(_glob(rs.path, name, rs.name))
        else:
            out.append(_file(rs.path / name, f"{rs.name}/{name}"))
    return out


def _provenance(sets: list[RunSet], inputs: dict[str, list[dict]]) -> list[dict]:
    """One row per page key of `SOURCES`: the source files with their sha256 (a glob: count and digest), the fields
    read. A token is resolved once."""
    resolved: dict[str, list[dict]] = {}
    out = []
    for key, src in SOURCES.items():
        files = []
        for token in src["files"]:
            if token not in resolved:
                resolved[token] = _resolve(token, sets, inputs)
            files += resolved[token]
        out.append({"key": key, "files": files, "fields": list(src["fields"])})
    return out


# ---------------------------------------------------------------- exclusions and limits


NOT_RUN = {"not_run_quota": "the quota was used up", "not_run_api_errors": "API errors stopped the run set",
           "not_run_budget": "the budget was reached",
           "not_run_sandbox": "the sandbox check failed", "not_run_probe_not_evaluable": "the probe was not evaluable"}


def _exclusions(rows: list[dict], benches: Mapping[str, dict], sets: list[RunSet], mans: list[dict]) -> list[dict]:
    """Runs left out, per model and reason: the not evaluable runs (scores table; a missing or empty `evaluable` cell
    counts as evaluable, as on the dashboard), the notes of each bench (missing transcripts, rows of other conditions
    or non-pilot tasks), the models in the order of `benches`, then any other model of the scores tables by name. A
    note of the run set (`kind` "run set", a scoring failure) stands in every bench; it is one row with the model "all
    models". The manifests add the runs that were never started (counts `not_run_*`, "all models") and the cells that
    were aborted (one row per cell, with its model)."""
    reasons = Counter((r.get("model", ""), r.get("not_evaluable_reason") or "no reason recorded") for r in rows
                      if as_bool(r.get("evaluable")) is False)
    models = list(benches) + sorted({m for m, _ in reasons} - set(benches))
    out = []
    for model in models:
        out += [{"model": model, "reason": reason, "count": n, "source": "scores.csv (not_evaluable_reason)"}
                for (m, reason), n in sorted(reasons.items()) if m == model]
        out += [{"model": model, "reason": n["text"], "count": n.get("count", 1),
                 "source": f"report notes ({n['kind']})"}
                for n in (benches.get(model) or {}).get("notes") or [] if n.get("kind") != "run set"]
    shared = {n["text"]: n for bench in benches.values() for n in bench.get("notes") or []
              if n.get("kind") == "run set"}
    out += [{"model": ALL_MODELS, "reason": n["text"], "count": n.get("count", 1), "source": "report notes (run set)"}
            for n in shared.values()]
    many = len(sets) > 1
    for rs, m in zip(sets, mans, strict=True):
        for key, why in NOT_RUN.items():
            if (n := (m.get("counts") or {}).get(key)):
                out.append({"model": ALL_MODELS, "reason": _suffixed(f"not started: {why}", rs, many), "count": n,
                            "source": f"MANIFEST.json (counts.{key})"})
        out += [{"model": str(c.get("model", ALL_MODELS)),
                 "reason": _suffixed(f"cell {c.get('condition', '?')} aborted: "
                                     + "; ".join(map(str, c.get("reasons") or [])), rs, many),
                 "count": 1, "source": "MANIFEST.json (aborted_cells)"}
                for c in m.get("aborted_cells") or [] if isinstance(c, dict)]
    return out


def _run_state(m: dict) -> str | None:
    """How the run set ended, from `finished`, `interrupted`, `stop` and `stopped_by_budget` of its manifest; None
    when the manifest records none of them."""
    if not {"finished", "interrupted", "stop", "stopped_by_budget"} & set(m):
        return None
    parts = ["interrupted"] if m.get("interrupted") else []
    stop = m.get("stop")
    if isinstance(stop, dict):
        scope = f", {stop['scope']} cap" if stop.get("scope") else ""
        after = f" after {stop['after_runs']} runs in a row" if stop.get("after_runs") else ""
        parts.append(f"stopped: {str(stop.get('reason', 'unknown')).replace('_', ' ')}{scope}{after}")
    if m.get("stopped_by_budget"):
        parts.append("stopped by the budget")
    if m.get("finished") and not parts:
        return "finished"
    return "; ".join(["not finished", *parts])


def _stop_rows(sets: list[RunSet], mans: list[dict]) -> list[dict]:
    """The limits that the manifests record: how each run set ended, the runs never started, the rate-limited runs and
    the aborted cells. A row appears only when its manifest holds the field (and, but for the state, a count above
    0)."""
    many = len(sets) > 1
    out = []
    for rs, m in zip(sets, mans, strict=True):
        counts = m.get("counts") or {}
        not_run = {k: counts[k] for k in NOT_RUN if counts.get(k)}
        cells = [c for c in m.get("aborted_cells") or [] if isinstance(c, dict)]
        rows = [("Run state", _run_state(m), "MANIFEST.json (finished, interrupted, stop, stopped_by_budget)"),
                ("Runs not started", f"{sum(not_run.values())} ("
                 + ", ".join(f"{k.removeprefix('not_run_').replace('_', ' ')} {n}" for k, n in not_run.items()) + ")"
                 if not_run else None, "MANIFEST.json (counts.not_run_*)"),
                ("Rate-limited runs", counts.get("rate_limited") or None, "MANIFEST.json (counts.rate_limited)"),
                ("Aborted cells", ", ".join(f"{c.get('model', '?')} {c.get('condition', '?')} ({c.get('effort', '?')})"
                                            for c in cells) or None, "MANIFEST.json (aborted_cells)")]
        out += [{"item": _suffixed(item, rs, many), "value": str(value), "source": source}
                for item, value, source in rows if value is not None]
    return out


def _limits(benches: Mapping[str, dict], sets: list[RunSet], mans: list[dict], rows: list[dict],
            platform: dict) -> list[dict]:
    """The scope of the run set as facts, over every model: models, tasks, classes, small classes, k, split, run
    window, runs and runs with an error, then how each run set ended (`_stop_rows`). Tasks and classes are those with
    runs of any model. The endpoint, effort and client are run settings and platform facts: they are not repeated."""
    heads = [b.get("header") or {} for b in benches.values()]
    tasks: dict[str, set[str]] = {}
    for bench in benches.values():
        for c in bench.get("classes") or []:
            tasks.setdefault(c["class"], set()).update(c.get("tasks") or [])
    sizes = [len(ids) for ids in tasks.values()]
    small = sum(1 for n in sizes if n < SMALL_CLASS)
    models = list(benches) if any(benches) else []
    window = platform.get("schedule", {}).get("manifest", {}) if isinstance(platform, dict) else {}
    start = min((h["start"] for h in heads if h.get("start")), default=None) or window.get("start")
    end = max((h["end"] for h in heads if h.get("end")), default=None) or window.get("end")
    errors = sum(1 for r in rows if is_true(r.get("is_error"))) if rows and "is_error" in rows[0] else None
    ks = [h["k"] for h in heads if "k" in h]
    planned = [h["k_planned"] for h in heads if h.get("k_planned") is not None]
    k = f"{max(ks)}" + (f" (planned {max(planned)})" if planned else "") if ks else None
    splits = facts_mod._distinct(h.get("split") for h in heads)
    done = [b["completeness"] for b in benches.values() if b.get("completeness")]
    cells = sum(c["cells"] for c in done)
    target = max((c["k"] for c in done), default=1)

    def total(key: str) -> int | None:
        got = [h[key] for h in heads if h.get(key) is not None]
        return sum(got) if got else None

    def row(item: str, value: Any, source: str) -> dict:
        got = value not in (None, "", [])
        return {"item": item, "value": str(value) if got else NOT_RECORDED, "source": source if got else "–"}

    return [
        row("Models", f"{len(models)}: {', '.join(models)}" if models else None, "scores.csv (model)"),
        row("Tasks", sum(len(ids) for ids in tasks.values()) if tasks else None, "tasks/tasks.jsonl"),
        row("Classes", len(tasks) if tasks else None, "tasks/tasks.jsonl"),
        row(f"Classes with fewer than {SMALL_CLASS} tasks", small if sizes else None, "tasks/tasks.jsonl"),
        row("Smallest class (tasks)", min(sizes) if sizes else None, "tasks/tasks.jsonl"),
        row("Runs per task (k)", k, "scores.csv (k_index), MANIFEST.json (k)"),
        row("Task split", f"{', '.join(splits)} only" if splits else None, "tasks/tasks.jsonl (split)"),
        row("Run window (UTC)", f"{start} to {end}" if start and end else None, "MANIFEST.json"),
        row("Runs scored", total("n_runs"), "scores.csv"),
        row("Runs evaluable", total("n_evaluable"), "scores.csv (evaluable)"),
        row("Runs with an error", errors, "scores.csv (is_error)"),
        row("Cells below the planned k", f"{sum(c['short'] for c in done)} of {cells} (k = {target})" if done else None,
            "scores.csv (k_index), MANIFEST.json (k)"),
        row("Runs missing for the planned k", sum(c["missing"] for c in done) if done else None,
            "scores.csv (k_index), MANIFEST.json (k)"),
        row("Rescued answers", sum(c["rescued"] for c in done) if done else None, "scores.csv (rescued)"),
        *_stop_rows(sets, mans),
    ]
