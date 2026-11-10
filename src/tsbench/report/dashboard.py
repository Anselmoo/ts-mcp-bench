"""The dashboard: one self-contained HTML page over one or more run sets.

    tsbench report dashboard --runs DIR [--runs DIR2 ...] [--out report.html] [--title T]
                             [--split pilot|confirmatory] [--i-have-preregistered DOI]

Inputs per run set (tsbench.score.run_sets, found under each `--runs` folder): scores.csv (scored on demand with
tsbench.score.score.score_dir when missing), MANIFEST.json, plan.jsonl, metrics/*.csv and views/ (linked when present).
What it shows: share correct per condition and the paired differences between conditions with their intervals, share
correct and efficiency per model and condition, an outcome grid per task, the tasks that were asked, every run in a
sortable table, the images the models saved and the facts of each manifest. Task text comes only from the split of the
page (`--split`, default pilot); rows whose task id is not a task of that split are shown by id and never looked up. A
run set of the confirmatory split is refused without `--i-have-preregistered <DOI>`; its page names the DOI and shows
the preregistered tests of each run set that holds hypotheses.json (report/prereg.py). The page is the template
templates/dashboard.html.j2 (macros in dashboard_macros.html.j2); `context()` builds its data as plain strings, numbers,
lists and dicts. The template escapes every datum; the page has inline CSS and JS, a strict Content-Security-Policy and
no external resource.

Design: Figura design system (d3 7.9.0 and `window.JFS` inlined, see src/tsbench/report/page.py). No pie or
donut charts: shares are dots with a 95 % task-clustered bootstrap interval plus stacked horizontal bars of run
outcomes, every status with icon and text. Rows with `evaluable` = False in scores.csv (HTTP 429 / API error) stay
visible as their own category and are left out of every rate.
"""
from __future__ import annotations

import argparse
import csv
import json
import pathlib
import sys

import numpy as np

from tsbench.report import page, prereg
from tsbench.report.base import (
    HARNESS,
    SPLITS,
    as_bool,
    as_number,
    as_run_sets,
    median,
    model_key,
    share,
    solved,
    split_refusal,
    split_tasks,
)
from tsbench.report.page import href
from tsbench.report.svg.base import round_half_up
from tsbench.score.run_sets import run_sets_in
from tsbench.stats import analysis

__all__ = ["build_html", "collect", "context", "design", "load_pilot_tasks", "load_tasks", "main"]

# The tools of each condition (src/tsbench/conditions; docs/methods.md, section 3).
TOOLS = {"A": "none", "B": "Bash with Python (numpy, scipy, sympy, matplotlib)",
         "C": "the TS-MCP server (Tanabe\u2013Sugano tools)"}

COLORS = {"A": page.THEME["series-1"], "B": page.THEME["series-2"], "C": page.THEME["series-3"]}  # Figura series-1..3
_EXTRA = [page.THEME["series-4"], page.THEME["series-5"], page.THEME["series-6"], page.THEME["rule"]]


# ---------------------------------------------------------------- helpers

def _fmt(v, nd=0):
    f = as_number(v)
    if f is None:
        return ""
    r = round_half_up(f, nd)
    return f"{abs(r) if r == 0 else r:,.{nd}f}"


def load_pilot_tasks() -> dict:
    """Pilot tasks by id."""
    return split_tasks("pilot")


def load_tasks(split: str = "pilot") -> dict:
    """The tasks of `split` by id (`load_pilot_tasks` for the pilot)."""
    return load_pilot_tasks() if split == "pilot" else split_tasks(split)


def _read_csv(path: pathlib.Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _read_json(path: pathlib.Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


SESSION_END = ("interrupted", "stop", "stopped_by_budget")  # the manifest fields that say how a session ended


def read_manifest(d: pathlib.Path) -> dict | None:
    """The manifest of a run set folder over all its sessions, or None when it has none. `--resume` renames the
    manifest of the earlier session to `MANIFEST.prev-<stamp>.json` and starts a new one, so the run set is read from
    `MANIFEST.json` and every `MANIFEST.prev-*.json`: the fields are those of the last session, except the window
    (earliest start, latest end), the counts (summed over the sessions; `planned` the largest; `skipped` that of the
    first session, since the runs a later session skips are the ones an earlier session did), `flagged_runs` and
    `aborted_cells` (joined without repeats). The counts `not_run_*` are those of the last session: a run an earlier
    session left out and a later one ran is no run that was not started. `total_cost_usd` is the last session's: a
    resumed session starts from the cost of the runs already done. `sessions` is the number of manifests read and
    `earlier_sessions` says how each of them but the last ended (`interrupted`, `stop`, `stopped_by_budget`)."""
    sessions = [m for p in [*sorted(d.glob("MANIFEST.prev-*.json")), d / "MANIFEST.json"]
                if p.is_file() and isinstance(m := _read_json(p), dict)]
    if not sessions:
        return None
    if len(sessions) == 1:
        return sessions[0]
    last = sessions[-1]
    starts = [m["start_time_utc"] for m in sessions if m.get("start_time_utc")]
    ends = [m["end_time_utc"] for m in sessions if m.get("end_time_utc")]
    counts: dict = {}
    for m in sessions:
        for key, n in (m.get("counts") or {}).items():
            if isinstance(n, int | float):
                counts[key] = max(counts.get(key, 0), n) if key == "planned" else counts.get(key, 0) + n
    if "skipped" in counts:
        counts["skipped"] = (sessions[0].get("counts") or {}).get("skipped", 0)
    for key in [k for k in counts if k.startswith("not_run_")]:
        counts[key] = (last.get("counts") or {}).get(key, 0)

    def joined(key: str) -> list:
        out: list = []
        for m in sessions:
            for x in m.get(key) or []:
                if x not in out:
                    out.append(x)
        return out

    flagged: dict = {}
    for f in joined("flagged_runs"):
        flagged[f.get("run_id", len(flagged)) if isinstance(f, dict) else len(flagged)] = f
    merged = {**last, "start_time_utc": min(starts, default=None), "end_time_utc": max(ends, default=None),
              "flagged_runs": list(flagged.values()), "aborted_cells": joined("aborted_cells"),
              "sessions": len(sessions), "earlier_sessions": [{k: m.get(k) for k in SESSION_END}
                                                              for m in sessions[:-1]]}
    if counts:
        merged["counts"] = counts
    return merged


class _Reads(dict):
    """The `transcripts` cache of `score_dir` (path -> Transcript) with a reader behind it: every lookup returns what
    `reader(path)` returns, so the scorer parses a transcript through the same memory as the other readers."""

    def __init__(self, reader):
        super().__init__()
        self._reader = reader

    def __contains__(self, path) -> bool:
        return True

    def __getitem__(self, path):
        return self._reader(path)


def collect(run_sets, out_path, tasks: dict, score_missing: bool = True, reader=None) -> dict:
    """Merge the run sets (RunSet objects or plain folders) into one data structure (rows, manifests, plans,
    metrics). `reader` reads a transcript (a `TranscriptCache`); a run set without scores.csv is scored through it, so
    that the readers after it do not parse the transcripts again."""
    out_dir = pathlib.Path(out_path).resolve().parent
    rows, sets, notes = [], [], []
    counts: dict[str, int] = {}
    for rs in as_run_sets(run_sets):
        d = rs.path
        if not d.is_dir():
            notes.append(f"{rs.name}: not a directory")
            continue
        sc = d / "scores.csv"
        if not sc.exists() and score_missing:
            try:
                from tsbench.score.score import score_dir
                score_dir(d, transcripts=_Reads(reader) if reader else None)
            except Exception as exc:  # scoring is best effort here
                notes.append(f"{rs.name}: scoring failed ({type(exc).__name__})")
        manifest = read_manifest(d)
        plan_lines = None
        if (d / "plan.jsonl").exists():
            try:
                plan_lines = [json.loads(x) for x in (d / "plan.jsonl").read_text(encoding="utf-8").splitlines()
                              if x.strip()]
            except (OSError, ValueError):
                notes.append(f"{rs.name}: plan.jsonl unreadable")
        metrics = sorted(p.name for p in (d / "metrics").glob("*.csv")) if (d / "metrics").is_dir() else []
        scored = _read_csv(sc) if sc.exists() else []
        if not scored:
            notes.append(f"{rs.name}: no scores")
        elif unscored := _unscored(d, scored, tasks):
            notes.append(f"{rs.name}: {unscored} transcript{'s' if unscored != 1 else ''} "
                         f"{'have' if unscored != 1 else 'has'} no scores row (run tsbench score)")
            counts[notes[-1]] = unscored
        if scored and (changed := _replaced(d, tasks)):
            notes.append(f"{rs.name}: {changed} transcript{'s' if changed != 1 else ''} "
                         f"{'differ' if changed != 1 else 'differs'} from the scores row (run tsbench score)")
        broken: list[str] = []
        for r in scored:
            r = dict(r)
            r["_set"] = rs.name
            r["_cond"] = r.get("condition", "")
            task = tasks.get(r.get("task_id"))
            r["_task"] = task
            r["_category"], failed = _categorize(r, task)
            if failed:
                broken.append(failed)
            r["_na"] = _not_evaluable(r)
            r["_flags"] = page.run_flags(r)
            r["_view"] = _view_link(d, r, out_dir)
            r["_images"] = _images_of(d, r)
            rows.append(r)
        if broken:
            notes.append(f"{rs.name}: category failed for {len(broken)} runs ({', '.join(sorted(set(broken)))})")
        sets.append({"name": rs.name, "title": rs.title, "path": d, "manifest": manifest, "plan": plan_lines,
                     "metrics": metrics, "n": len(scored)})
    return {"rows": rows, "sets": sets, "notes": notes, "note_counts": counts, "tasks": tasks}


def _unscored(d: pathlib.Path, scored: list[dict], tasks: dict) -> int:
    """How many transcripts of the folder (of a task in `tasks`) have no row in its scores.csv: runs that landed after
    `tsbench score` wrote it (`tsbench run` does not score). Without any transcript the count is 0."""
    from tsbench.score.score import find_transcripts
    by_effort = "effort" in scored[0]            # a table without the column is read by the other four fields
    have = {(r.get("model"), r.get("condition"), r.get("effort") if by_effort else None, r.get("task_id"),
             str(r.get("k_index"))) for r in scored}
    return sum((model, cond, effort if by_effort else None, tid, str(k)) not in have
               for _p, model, cond, effort, tid, k in find_transcripts(d) if tid in tasks)


def _replaced(d: pathlib.Path, tasks: dict) -> int:
    """How many runs have a scores row that does not fit their transcript (overwritten or re-run after
    `tsbench score`, see `score.scores_drift`). The runs that have no row at all are counted by `_unscored`."""
    from tsbench.score.score import scores_drift
    return len(scores_drift(d, set(tasks)).get("changed", []))


def _images_of(d: pathlib.Path, r: dict) -> list:
    """Harvested images of a run (base64 data URIs), from the transcript's sidecar; [] when there are none."""
    from tsbench.report.views import harvested_images

    tp = (
        d
        / r.get("model", "")
        / r.get("condition", "")
        / r.get("effort", "")
        / f"{r.get('task_id', '')}-k{r.get('k_index', '')}.jsonl"
    )
    try:
        meta = json.loads(tp.with_name(tp.name[: -len(".jsonl")] + ".meta.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    imgs = harvested_images(tp, meta) if isinstance(meta, dict) else []
    for im in imgs:
        im["match"] = meta.get("image_sha_match")
    return imgs


def _categorize(row, task) -> tuple[str, str | None]:
    """(category, error): the category of the taxonomy, or a coarse one with the name of the exception that stopped
    the taxonomy."""
    failed = None
    try:
        from tsbench.score.taxonomy import failure_category
        if task is not None:
            return failure_category(row, task), None
    except Exception as exc:
        failed = type(exc).__name__
    if as_bool(row.get("correct")):
        return "correct", failed
    if not as_bool(row.get("has_result")):
        return "no_result", failed
    return "wrong", failed


def _view_link(d: pathlib.Path, r: dict, out_dir: pathlib.Path):
    rel = pathlib.PurePosixPath("views", r.get("model", ""), r.get("condition", ""), r.get("effort", ""),
                                f"{r.get('task_id', '')}-k{r.get('k_index', '')}.html")
    p = d.resolve().joinpath(*rel.parts)
    if not p.is_file():
        return None
    return href(p, out_dir)


def _not_evaluable(r) -> str:
    """`na429` for a scores.csv row with evaluable = False (rate_limited, api_error), else ''. A missing or empty
    column = evaluable."""
    return "na429" if as_bool(r.get("evaluable")) is False else ""


def _evaluable(rows) -> list:
    """The rows that count in rates (evaluable)."""
    return [r for r in rows if not r.get("_na")]


def _outcome(r) -> str:
    if r.get("_na"):
        return r["_na"]
    cat = r["_category"]
    if cat == "correct" or as_bool(r.get("correct")):
        return "correct"
    return "harness" if cat in HARNESS else "wrong"


# ---------------------------------------------------------------- charts
def _colors_for(labels):
    out, extra = {}, iter(_EXTRA)
    for lab in labels:
        out[lab] = COLORS.get(lab) or next(extra, "#8a8a8a")
    return out


def _condition_name(cond: str) -> str:
    return f"{cond} · {COND_NAMES.get(cond, cond)}"


def _dots_chart(groups, series, value, label, title, xlabel, ci=None, domain=None) -> dict:
    """Dots instead of bars: one row per group (model), one dot per series; direct value labels, optional 95 % interval
    (whisker without caps). value(g, s) -> float | None; label(g, s, v) -> str; ci(g, s) -> (lo, hi) | None.
    Returns the figure spec and the table of the <noscript>, for the macro `dots_chart`. The figure draws no legend:
    the page shows one legend for all its dot charts (`_cond_legend`)."""
    rows = []
    for g in groups:
        row = {"label": g, "v": {}, "t": {}, "ci": {}, "tips": {}}
        for k in series:
            v = value(g, k)
            row["v"][k] = v
            if v is not None:
                row["t"][k] = label(g, k, v)
                row["tips"][k] = f"{g} · {k}: {label(g, k, v)}"
                c = ci(g, k) if ci else None
                if c:
                    row["ci"][k] = [c[0], c[1]]
        rows.append(row)
    spec = {"rows": rows, "conds": list(series), "names": {k: _condition_name(k).split(" · ", 1)[-1] for k in series},
            "xLabel": xlabel, "left": 60, "width": "single", "dec": ".", "none": "no values", "legend": False,
            "right": 14}
    if domain:
        spec["domain"] = list(domain)
    return {"spec": spec, "title": title, "alt": f"{title}: dot plot per model and condition", "series": list(series),
            "table": [{"label": r["label"], "cells": [r["t"].get(k, "–") for k in series]} for r in rows]}


# The marker of each condition in the dot charts (runtime.js `shapeOf`); other series take the shapes in turn.
_SHAPES = ("circle", "square", "triangle", "diamond")
_COND_SHAPE = {"A": "circle", "B": "square", "C": "triangle", "B fixed": "diamond"}


def _cond_legend(series) -> list:
    """The legend of the dot charts: name, colour and marker shape of each series."""
    cols = _colors_for(series)
    return [{"name": _condition_name(k), "cond": k, "color": cols[k],
             "shape": _COND_SHAPE.get(k, _SHAPES[i % len(_SHAPES)])}
            for i, k in enumerate(series)]


def _text(v) -> str:
    """Text of a value that may be missing: '' for None (a template would print 'None')."""
    return "" if v is None else str(v)


# ---------------------------------------------------------------- sections
def _facts(data) -> list:
    """The tiles about the runs: {label, value, caption}; the value stays short, the explanation is the caption."""
    sets, rows = data["sets"], data["rows"]
    models = sorted({r.get("model", "") for r in rows}, key=model_key)
    conds = sorted({r["_cond"] for r in rows}, key=lambda c: (c not in BASE, c))
    n_na = sum(r.get("_na") == "na429" for r in rows)
    n_resc = sum(bool(as_bool(r.get("rescued"))) for r in rows)
    items = [
        {"label": "Models", "value": str(len(models)), "caption": ", ".join(models)},
        {"label": "Conditions", "value": ", ".join(conds),
         "caption": ", ".join(COND_NAMES.get(c, c) for c in conds)},
        {"label": "Runs", "value": str(len(rows)), "caption": f"from {len(sets)} run set" + ("" if len(sets) == 1
                                                                                             else "s")},
    ]
    if n_na:
        items.append({"label": "Not evaluable (not in any rate)", "value": str(n_na),
                      "caption": f"{n_na} HTTP 429 / API error"})
    if n_resc:
        items.append({"label": "Rescued answers", "value": str(n_resc),
                      "caption": "last valid answer call before a turn or budget limit"})
    return items


def _stamp(data, period: str, split: str = "pilot", doi: str | None = None) -> str:
    """The line under the title: what the page counts, before any number is read. The split is named when every row
    is a task of it; a confirmatory page names its preregistration."""
    rows = data["rows"]
    models = {r.get("model", "") for r in rows}
    tasks = {r.get("task_id") for r in rows}
    ks = [int(k) for k in (as_number(r.get("k_index")) for r in rows) if k is not None]
    known = bool(rows) and all(r["_task"] is not None for r in rows)
    parts = ([f"{split} split"] if known else []) + ([f"preregistered {doi}"] if split == "confirmatory" and doi
                                                     else []) + [page.plural(len(tasks), "task")] \
        + ([f"k = {max(ks)}"] if ks else []) + [page.plural(len(rows), "run"), page.plural(len(models), "model"),
                                                page.plural(len(data["sets"]), "run set"), period]
    return " · ".join(parts)


def _run_sets(data) -> list:
    """The run sets grouped by family (the folder above the set): {family, about, sets: [{name, title}]}. `about` is
    the part of the titles before the first comma when every set of the family shares it."""
    fams: dict[str, list] = {}
    for s in data["sets"]:
        family, _, name = s["name"].rpartition("/")
        title = s.get("title") or ""
        entry = {"name": name, "title": "" if title == s["name"] else title}
        fams.setdefault(family or "(top level)", []).append(entry)
    out = []
    for family in sorted(fams):
        sets = sorted(fams[family], key=lambda x: x["name"])
        heads = {x["title"].split(", ")[0] for x in sets}
        out.append({"family": family, "about": heads.pop() if len(heads) == 1 else "", "sets": sets})
    return out


def _provenance(data) -> dict:
    """When the runs ran, what they cost, and the git commits and plan ids of the manifests, short (8 characters)
    with the full value kept for the hover."""
    ms = [s["manifest"] or {} for s in data["sets"]]
    starts = sorted(m["start_time_utc"] for m in ms if m.get("start_time_utc"))
    ends = sorted(m["end_time_utc"] for m in ms if m.get("end_time_utc"))
    cost = sum(m.get("total_cost_usd") or 0 for m in ms) or sum(as_number(r.get("cost_usd")) or 0 for r in data["rows"])
    commits = sorted({(str(m["git_commit"]), m.get("git_dirty") == "yes") for m in ms if m.get("git_commit")})
    plans = sorted({str(m["plan_id"]) for m in ms if m.get("plan_id")})
    return {"period": f"{starts[0][:10]} to {ends[-1][:10]}" if starts and ends else "unknown",
            "cost": f"${_fmt(cost, 2)}",
            "commits": [{"short": c[:8], "full": c, "dirty": d} for c, d in commits],
            "plans": [{"short": p[:8], "full": p} for p in plans], "manifests": _manifests(data)}


# ---------------------------------------------------------------- verdict
BASE = ("A", "B", "C")
COND_NAMES = page.COND_NAMES


def _cell_counts(rows, n=None) -> dict:
    """Outcome counts of one model x condition cell; they sum to `n` (rows missing from the plan = not run).
    `na429` = HTTP 429 / API error: outside the rates (`n_eval` leaves them out)."""
    c = {"correct": 0, "wrong": 0, "harness": 0, "na429": 0}
    for r in rows:
        c[_outcome(r)] += 1
    n = len(rows) if n is None else max(n, len(rows))
    c["none"] = n - len(rows)
    c["n"] = n
    c["n_eval"] = len(rows) - c["na429"]
    return c


def efficiency_text(med: dict) -> str | None:
    """med: {'A': (tokens, sec), 'B': ..., 'C': ...}. C against B and A in the one format of every page
    (page.change_text): 'TS-MCP against code: N % fewer output tokens and M % less time; against no tools: N %
    fewer output tokens and M % less time'."""
    c = med.get("C")
    if not c:
        return None
    segs = []
    for k in ("B", "A"):
        o = med.get(k)
        if not o:
            continue
        got = [x for x in (page.change_text(c[0], o[0], "output tokens"), page.change_text(c[1], o[1], "time", "less"))
               if x]
        if got:
            segs.append(f"against {COND_NAMES[k]}: " + " and ".join(got))
    return "TS-MCP " + "; ".join(segs) if segs else None


def _hero(rows) -> list:
    """One tile per condition: the share correct of its evaluable runs and a 95 % interval. A task's k runs are not
    independent, so the interval resamples tasks (core.intervals.cluster_bootstrap), as `report.base.share` does."""
    out = []
    for k in BASE:
        rs = _evaluable([r for r in rows if r["_cond"] == k])
        sh = share(rs)
        if sh is None:
            continue
        lo, hi = 100 * sh["lo"], 100 * sh["hi"]
        c, n = sh["k"], sh["n"]
        p = 100 * sh["p"]
        cnt = _cell_counts([r for r in rows if r["_cond"] == k])
        chips = [{"key": key, "text": f"{cnt[key]} {page.STATUS_TEXT[key]}"}
                 for key in ("harness", "na429") if cnt[key]]
        out.append({"cond": k, "label": page.COND_LABEL[k], "pct": f"{round_half_up(p)}", "p": round(p, 1),
                    "lo": round(lo, 1),
                    "hi": round(hi, 1), "text": f"{c} of {n} correct over {page.plural(sh['tasks'], 'task')}",
                    "ci": f"95 % interval {round_half_up(lo)}–{round_half_up(hi)} %, tasks resampled", "chips": chips,
                    "flags": page.flag_notes(rs)})
    return out


def _shares(cells: dict, model: str, cond: str) -> dict:
    """task -> (correct, evaluable runs) of one model and condition, the tasks sorted by id (the bootstrap of
    `page.share_interval` draws by position, so the row order of the scores must not matter)."""
    out = {}
    for r in _evaluable(cells.get((model, cond), [])):
        c, n = out.get(_text(r.get("task_id")), (0, 0))
        out[_text(r.get("task_id"))] = (c + bool(as_bool(r.get("correct"))), n + 1)
    return dict(sorted(out.items()))


def _ledger(cells: dict, model: str, other: str = "B") -> dict:
    """C against `other` (B by default) task by task, the unit the study tests (B and C are paired by task): on each
    task with evaluable runs under both, is C's share correct higher, the same or lower? Descriptive counts, no test."""
    c_sh, b_sh = _shares(cells, model, "C"), _shares(cells, model, other)
    order = {"higher": 0, "same": 1, "lower": 2}
    tasks = []
    for t in sorted(set(c_sh) & set(b_sh)):
        (cc, cn), (bc, bn) = c_sh[t], b_sh[t]
        d = cc / cn - bc / bn
        mark = "higher" if d > 1e-9 else "lower" if d < -1e-9 else "same"
        tasks.append({"id": t, "mark": mark,
                      "title": f"{t}: TS-MCP {cc}/{cn} correct, {COND_NAMES[other]} {bc}/{bn}"})
    tasks.sort(key=lambda x: (order[x["mark"]], x["id"]))
    counts = {k: sum(x["mark"] == k for x in tasks) for k in order}
    return {**counts, "n": len(tasks), "tasks": tasks}


CONTRASTS = (("C", "A"), ("C", "B"), ("B", "A"))


def _contrasts(cells: dict, model: str) -> list:
    """The paired differences of one model, x minus y for (C, A), (C, B) and (B, A), over the tasks with evaluable runs
    under both: the mean difference in per-task share correct in percentage points, its 95 % percentile bootstrap
    interval with tasks resampled (stats.analysis.bootstrap_ci) and the tasks correct (share > 0.5) under one condition
    only (stats.analysis.paired_majority). Descriptive; the pilot tests no hypothesis."""
    out = []
    for x, y in CONTRASTS:
        sx, sy = _shares(cells, model, x), _shares(cells, model, y)
        tasks = sorted(set(sx) & set(sy))
        if not tasks:
            continue
        rx = np.array([sx[t][0] / sx[t][1] for t in tasks])
        ry = np.array([sy[t][0] / sy[t][1] for t in tasks])
        lo, hi = analysis.bootstrap_ci(ry, rx)
        only_y, only_x, _ = analysis.paired_majority(ry, rx)
        pp = 100 * float(np.mean(rx - ry))
        out.append({"model": model, "x": x, "y": y, "label": f"{x} \u2212 {y}",
                    "name": f"{COND_NAMES[x]} \u2212 {COND_NAMES[y]}", "n": len(tasks),
                    "d": f"{page.signed(pp)} pp",
                    "ci": f"{page.signed(100 * lo)} to {page.signed(100 * hi)}",
                    "only_x": only_x, "only_y": only_y,
                    # what a drawing and a link to the runs need: the values in pp, and the tasks counted above
                    "pp": pp, "lo": 100 * lo, "hi": 100 * hi, "tasks": tasks,
                    "x_only": [t for t, a, b in zip(tasks, rx, ry, strict=True) if a > 0.5 >= b],
                    "y_only": [t for t, a, b in zip(tasks, rx, ry, strict=True) if b > 0.5 >= a]})
    return out


def _pairs(cells: dict, model: str) -> dict | None:
    """The figure "task by task": per comparison condition (B, A) the tasks where C's share correct is higher, the same
    or lower, as one stacked bar each, with the counts as text below. None without a task run under C and B or A."""
    rows, text = [], []
    for other in ("B", "A"):
        led = _ledger(cells, model, other)
        if not led["n"]:
            continue
        name = COND_NAMES[other]
        seg = [["higher", led["higher"], f"C higher on {page.plural(led['higher'], 'task')}", "C higher"],
               ["same", led["same"], f"the same on {page.plural(led['same'], 'task')}", "same"],
               ["lower", led["lower"], f"C lower on {page.plural(led['lower'], 'task')}", "C lower"]]
        rows.append({"label": f"C vs {other} · {name}", "n": led["n"], "seg": seg})
        text.append(f"C against {other} ({page.plural(led['n'], 'task')} run under both): share correct higher on "
                    f"{page.plural(led['higher'], 'task')}, the same on {led['same']}, lower on {led['lower']}.")
    if not rows:
        return None
    alt = f"{model}: per task, is C's share correct higher, the same or lower than B's and A's?"
    return {"spec": {"rows": rows, "left": 70, "model": model},
            "title": "C against B and A, task by task", "alt": alt, "text": text}


def _rate(model: str, cells: dict, n: int, nmax: int) -> dict:
    """Per-model figure: (a) share correct with the task-bootstrap interval, (b) stacked outcome bars; text below."""
    keys = [k for k in sorted({c for m, c in cells if m == model}, key=lambda c: (c not in BASE, c))]
    rows, items = [], []
    for k in keys:
        cnt = _cell_counts(cells[(model, k)], n)
        counts = {"correct": cnt["correct"], "wrong": cnt["wrong"], "harness": cnt["harness"], "na429": cnt["na429"],
                  "notrun": cnt["none"]}
        rr = page.rate_row(_condition_name(k), k, counts, cnt["n_eval"], cnt["n"],
                           list(_shares(cells, model, k).values()))
        rows.append(rr)
        core = (
            "no evaluable runs"
            if rr["p"] is None
            else f"{rr['correct']} of {rr['n_eval']} correct ({page.few_text(rr['n_eval'])})"
            if rr["few"]
            else (
                f"{rr['correct']} of {rr['n_eval']} correct ({round_half_up(rr['p'])} %; "
                f"95 % interval {round_half_up(rr['lo'])} to {round_half_up(rr['hi'])} %)"
            )
        )
        chips = [{"key": sk, "text": f"{v} {name}"} for (sk, v, name) in ((x[0], x[1], x[2]) for x in rr["seg"]) if v]
        items.append({"name": _condition_name(k), "cond": k, "core": core, "chips": chips})
    title = "Share correct (a) and runs by outcome (b)"
    spec = {
        "rows": rows,
        "left": 62,
        "dec": ".",
        "stack": True,
        "nmax": nmax,
        "model": model,
        "labels": {"xa": "Share correct (%), line: 95 % interval", "xb": "Runs (count)", "none": "no runs"},
    }
    alt = f"{model}: share correct with 95 % interval and runs per outcome, per condition"
    return {"spec": spec, "title": title, "alt": alt, "items": items}


def _seconds_of(r):
    s = as_number(r.get("duration_s"))
    return as_number(r.get("wall_time_s")) if s is None else s


def _verdict(data) -> dict | None:
    """The first section: a tile per condition (`hero`), the paired differences of every model (`contrasts`), and with
    several models one card per model (`cards`); with one model its task-by-task figure (`pairs`)."""
    rows = data["rows"]
    if not rows:
        return None
    cells = _by_cell(rows)
    models = sorted({m for m, _ in cells}, key=model_key)
    ns = {m: max([len(cells.get((m, k), [])) for k in BASE] + [0]) for m in models}
    nmax = max([len(rs) for rs in cells.values()] + list(ns.values()) + [1])
    cards = []
    for m in models:
        flags = [dict(f, cond=k) for k in BASE for f in page.flag_notes(_evaluable(cells.get((m, k), [])))]
        cards.append({"model": m, "rate": _rate(m, cells, ns[m], nmax), "ledger": _ledger(cells, m),
                      "pairs": _pairs(cells, m), "flags": flags})
    return {"hero": _hero(rows), "contrasts": [x for m in models for x in _contrasts(cells, m)],
            "models": len(models) > 1, "cards": cards if len(cards) > 1 else [],
            "pairs": cards[0]["pairs"] if len(cards) == 1 else None}


def _tasks(data) -> list:
    """One row per pilot task that was asked (the rows' task ids that are pilot tasks)."""
    seen = sorted({r.get("task_id") for r in data["rows"] if r["_task"] is not None})
    out = []
    for tid in seen:
        t = data["tasks"][tid]
        prompt = str(t.get("prompt", ""))
        short = prompt if len(prompt) <= 90 else prompt[:89] + "…"
        ref = t.get("reference") or {}
        refs = ", ".join(f"{k}={v}" for k, v in ref.items() if v is not None) or "none (out of scope)"
        if t.get("expect_out_of_scope"):
            refs = "out of scope"
        scope = ["out_of_scope"] if t.get("expect_out_of_scope") else []
        schema = " or ".join(x for x in (", ".join(t.get("required") or []), *scope) if x)
        if t.get("answer_schema") == "batch":  # keep long references out of the table
            refs, schema = f"{len(ref.get('values') or [])} computed values", "values (input, result)"
        elif t.get("answer_schema") == "curve":
            curve = t.get("reference_curve") or []
            refs = f"{len(curve)} energies E/B at {len({p['dq_over_b'] for p in curve})} Dq/B points"
            schema = "points (dq_over_b, term, e_over_b)"
        elif t.get("answer_schema") == "pairing":
            refs = f"{len(ref.get('nodes') or [])} term nodes, {len(ref.get('edges') or [])} shared-term edges"
            schema = "nodes, edges"
        elif t.get("answer_schema") == "diagram":
            refs = f"{len(ref.get('grid') or [])} Dq/B points x 6 levels"
            schema = "points (levels), image_path, image_sha256"
        out.append({"id": _text(tid), "class": _text(t.get("class")), "short": short, "prompt": prompt,
                    "schema": schema or "Dq, B, C, out_of_scope", "reference": refs})
    return out


def _answer(r):
    if as_number(r.get("item_accuracy")) is not None:
        return f"{_fmt(as_number(r.get('item_accuracy')), 2)} of items correct"
    if as_number(r.get("edge_f1")) is not None:
        return f"edge F1 {_fmt(as_number(r.get('edge_f1')), 2)}"
    if as_bool(r.get("answer_out_of_scope")):
        return "out of scope"
    parts = [f"{n}={_fmt(r.get(k))}" for n, k in (("Dq", "dq"), ("B", "b"), ("C", "c"))
             if as_number(r.get(k)) is not None]
    return ", ".join(parts) or "–"


def _runs(data) -> list:
    """One row per run for the sortable table; a number is {"text", "v"} (`v` sorts, None when missing)."""
    out = []
    for r in data["rows"]:
        sec = _seconds_of(r)
        tokens = as_number(r.get("output_tokens"))
        cost = as_number(r.get("cost_usd"))
        na = r.get("_na")
        outcome = page.STATUS_TEXT[na] if na else r["_category"]
        correct = ({"icon": "dash", "text": "excluded"} if na
                   else {"icon": "check", "text": "yes"} if as_bool(r.get("correct"))
                   else {"icon": "cross", "text": "no"})
        out.append({"class": f"o-{_outcome(r)}", "model": _text(r.get("model")), "condition": r["_cond"],
                    "task": _text(r.get("task_id")), "answer": _answer(r), "correct": correct, "outcome": outcome,
                    "flags": "; ".join(page.FLAG_TEXT[f] for f in r["_flags"]),
                    "tokens": {"text": _fmt(tokens), "v": tokens}, "seconds": {"text": _fmt(sec, 1), "v": sec},
                    "cost": {"text": _fmt(cost, 4), "v": cost}, "view": r["_view"]})
    return out


def _images(data) -> list:
    """The images the models saved, one entry per image: a label, the image as the `images` macro of
    views_macros.html.j2 takes it (`files`: [{name, sha256, sha_ok, uri}]) and the model's sha256 claim (`match`)."""
    shown = [(r, im) for r in data["rows"] for im in r.get("_images") or [] if im.get("uri")]
    return [{"label": f"{_text(r.get('model'))} · {r['_cond']} · {_text(r.get('task_id'))} k{_text(r.get('k_index'))}",
             "files": [im], "match": im.get("match")} for r, im in shown]


def _by_cell(rows):
    cells = {}
    for r in rows:
        cells.setdefault((r.get("model", ""), r["_cond"]), []).append(r)
    return cells


def _charts(data) -> dict | None:
    rows = data["rows"]
    if not rows:
        return None
    cells = _by_cell(rows)
    models = sorted({m for m, _ in cells}, key=model_key)
    conds = sorted({c for _, c in cells}, key=lambda c: (c not in BASE, c))

    def med(col):
        return lambda m, c: median([as_number(r.get(col)) for r in _evaluable(cells.get((m, c), []))])

    def med_sec(m, c):
        return median([_seconds_of(r) for r in _evaluable(cells.get((m, c), []))])

    plain = []
    for m in models:
        medians = {}
        for k in BASE:
            rs = _evaluable(cells.get((m, k), []))
            medians[k] = (median([as_number(r.get("output_tokens")) for r in rs]),
                          median([_seconds_of(r) for r in rs])) if rs else None
        if text := efficiency_text(medians):
            plain.append({"model": m, "text": text})
    return {"plain": plain, "legend": _cond_legend(conds),
            "tokens": _dots_chart(models, conds, med("output_tokens"), lambda m, c, v: _fmt(v), "Median output tokens",
                                  "Output tokens (median)"),
            "seconds": _dots_chart(models, conds, med_sec, lambda m, c, v: _fmt(v, 1), "Median seconds per run",
                                   "Time (s, median)")}


_GRID_ICON = {
    "correct": "check",
    "wrong": "cross",
    "harness": "bang",
    "na429": "pause",
    "none": "dash",
}


def _grid(data) -> dict | None:
    """Every task by class: one small table per task class, a row per task and a cell per model and condition with
    its outcome (icon and colour) and a mark when the run carries a flag (B ran no code, C made no TS-MCP call); the
    last row counts correct of evaluable runs per column. The outcome of a cell is the verdict of the report
    (`base.solved`); a cell that is not solved is `harness` when one of its runs stopped so, else `wrong`. `heads` are
    the model heads, in the order of the cells. None without runs."""
    rows = data["rows"]
    if not rows:
        return None
    series = sorted({(_text(r.get("model")), r["_cond"]) for r in rows},
                    key=lambda x: (model_key(x[0]), x[1] not in BASE, x[1]))
    idx: dict = {}
    for r in rows:
        idx.setdefault((r.get("task_id"), (_text(r.get("model")), r["_cond"])), []).append(r)
    names = {**{k: page.STATUS_TEXT[k] for k in ("correct", "wrong", "harness", "na429")},
             "none": page.STATUS_TEXT["notrun"]}
    by_cls: dict = {}
    for r in rows:
        by_cls.setdefault(_text(r.get("class")) or (r["_task"] or {}).get("class") or "–", set()).add(r.get("task_id"))
    classes: list[dict] = []
    states: set = set()
    flagged = False
    for cls in sorted(by_cls):
        body: list[dict] = []
        tot = [[0, 0] for _ in series]
        for t in sorted(by_cls[cls], key=_text):
            cells = []
            for j, sr in enumerate(series):
                rs = idx.get((t, sr), [])
                o = [_outcome(r) for r in rs]
                ev = [x for x in o if x != "na429"]
                if not o:
                    k = "none"
                else:
                    k = "na429" if not ev else (
                        "correct" if solved(_evaluable(rs)) else "harness" if "harness" in ev else "wrong")
                tot[j][0] += ev.count("correct")
                tot[j][1] += len(ev)
                flags = sorted({f for r in _evaluable(rs) for f in r["_flags"]})
                lab = f"{ev.count('correct')}/{len(ev)}" if len(o) > 1 and ev else ""
                said = "; ".join(page.FLAG_TEXT[f] for f in flags)
                states.add(k)
                flagged = flagged or bool(flags)
                cells.append({"state": k, "icon": _GRID_ICON[k], "label": lab, "flag": bool(flags),
                              "title": f"{_text(t)} · {sr[0]} · {sr[1]}: {names[k]}" + (f" ({said})" if said else "")})
            body.append({"task": _text(t), "cells": cells})
        classes.append({"cls": cls, "n": len(body), "rows": body,
                        "total": [f"{c}/{n}" if n else "–" for c, n in tot]})
    heads = {m: sum(s[0] == m for s in series) for m, _ in series}  # first seen in `series`, the order of the cells
    legend = [{"swatch": "notrun" if k == "none" else k, "icon": _GRID_ICON[k], "name": names[k]} for k in names
              if k in states]
    return {"series": [{"model": m, "cond": c} for m, c in series],
            "heads": list(heads.items()) if len(heads) > 1 else [],
            "classes": classes, "legend": legend, "flagged": flagged, "min": 120 + 34 * len(series)}


def _manifests(data) -> list:
    """One row per run set: the sandbox, the probe markers, flagged and aborted runs and the metrics files."""
    out = []
    for s in data["sets"]:
        m = s["manifest"]
        if not m:
            out.append({"name": s["name"], "missing": True})
            continue
        sb = m.get("sandbox") or {}
        probe = sb.get("probe") or {}
        markers = ", ".join(f"{k}={'/'.join(map(str, v)) if isinstance(v, list) else v}"
                            for k, v in sorted((probe.get("markers") or {}).items()))
        flagged = m.get("flagged_runs") or []
        fl = {}
        for f in flagged:
            for x in f.get("flags", []):
                fl[x] = fl.get(x, 0) + 1
        aborted = "; ".join(json.dumps(a, sort_keys=True) if not isinstance(a, str) else a
                            for a in m.get("aborted_cells") or []) or "none"
        passed = probe.get("passed")
        out.append({"name": s["name"], "missing": False, "method": _text(sb.get("method")),
                    "probe": "" if passed is None else " (probe " + ("passed" if passed else "FAILED") + ")",
                    "markers": markers or "–", "flagged": len(flagged),
                    "flags": ", ".join(f"{k}: {v}" for k, v in sorted(fl.items())),
                    "aborted": aborted,
                    "metrics": ", ".join(s["metrics"]) or "–"})
    return out


def default_title(data: dict) -> str:
    """'TS-MCP benchmark: qwen3.5-397b-a17b' for up to three models, else 'TS-MCP benchmark'."""
    models = sorted({_text(r.get("model")) for r in data["rows"]}, key=model_key)
    return "TS-MCP benchmark" + (f": {', '.join(models)}" if 0 < len(models) <= 3 else "")


def context(data: dict, title: str | None = None, split: str = "pilot", doi: str | None = None) -> dict:
    """The data of the page as plain strings, numbers, lists and dicts; templates/dashboard.html.j2 turns it into HTML.
    `verdict`, `charts` and `grid` are None when there are no runs. `split` and `doi` are those of the page; the
    preregistered tests (`prereg`) are read only for the confirmatory split."""
    provenance = _provenance(data)
    run_sets = _run_sets(data)
    n_sets = sum(len(f["sets"]) for f in run_sets)
    tests = prereg.hypotheses([pathlib.Path(s["path"]) for s in data["sets"]]) if split == "confirmatory" else []
    return {"title": title or default_title(data), "stamp": _stamp(data, provenance["period"], split, doi),
            "split": split, "doi": doi, "prereg": tests, "facts": _facts(data),
            "run_sets": run_sets, "run_sets_head": f"{page.plural(n_sets, 'run set')} in "
                                                   f"{page.plural(len(run_sets), 'family', 'families')}",
            "notes": list(data["notes"]), "verdict": _verdict(data), "charts": _charts(data), "grid": _grid(data),
            "tasks": _tasks(data), "runs": _runs(data), "images": _images(data), "provenance": provenance}


def design(data: dict, split: str = "pilot", doi: str | None = None) -> dict:
    """The study design as the runs show it: per condition its tools, runs and evaluable runs; tasks, task classes,
    models and the largest repetition index k; the split of the page and, for the confirmatory split, its DOI."""
    rows = data["rows"]
    out = []
    for k in ("A", "B", "C"):
        rs = [r for r in rows if r["_cond"] == k]
        out.append({"cond": k, "label": page.COND_LABEL[k], "tools": TOOLS[k], "runs": len(rs),
                    "evaluable": sum(not r.get("_na") for r in rs)})
    tasks = {r.get("task_id") for r in rows}
    classes = {(r.get("_task") or {}).get("class") or r.get("class") for r in rows}
    ks = [int(float(r["k_index"])) for r in rows if str(r.get("k_index") or "").strip()]
    models = sorted({r.get("model", "") for r in rows}, key=model_key)
    return {"rows": out, "tasks": page.plural(len(tasks), "task"), "classes": page.plural(len(classes), "class",
                                                                                         "classes"),
            "models": ", ".join(models), "n_models": len(models), "k": max(ks) if ks else None,
            "split": split, "doi": doi}


def build_html(data: dict, title: str | None = None, split: str = "pilot", doi: str | None = None) -> str:
    ctx = context(data, title, split, doi)
    return page.render("dashboard.html.j2", **ctx, ctx=ctx, design=design(data, split, doi))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="tsbench report dashboard", description=__doc__.split("\n")[0])
    ap.add_argument("--runs", action="append", required=True, metavar="DIR",
                    help="a run set, or a folder holding run sets (repeatable)")
    ap.add_argument(
        "--out", default=None, metavar="FILE", help="output file (default <first --runs folder>/report.html)"
    )
    ap.add_argument("--title", default=None, help="page title (default: TS-MCP benchmark and the models)")
    ap.add_argument("--split", default="pilot", choices=SPLITS, help="the task split of the run sets (default pilot)")
    ap.add_argument("--i-have-preregistered", dest="preregistered", metavar="DOI", default=None,
                    help="the DOI of the preregistration; needed for the confirmatory split")
    a = ap.parse_args(argv)
    out = pathlib.Path(a.out) if a.out else pathlib.Path(a.runs[0]) / "report.html"
    run_sets = run_sets_in(a.runs)
    if not run_sets:
        ap.error("no run set found under --runs")
    if refused := split_refusal(run_sets, a.split, a.preregistered):
        print(f"tsbench report dashboard: {refused}", file=sys.stderr)
        return 2
    data = collect(run_sets, out, load_tasks(a.split))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build_html(data, a.title, a.split, a.preregistered), encoding="utf-8")
    print(f"wrote {out} ({page.plural(len(data['rows']), 'run')} from {page.plural(len(data['sets']), 'run set')})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

