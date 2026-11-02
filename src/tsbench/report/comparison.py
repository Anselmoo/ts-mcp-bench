"""The comparison page: conditions A (no tools), B (code) and C (TS-MCP) compared across one or more run sets.

    tsbench report comparison --runs DIR [--runs DIR2 ...] --out COMPARISON.html

Inputs: the run sets under each `--runs` folder (tsbench.score.run_sets; a run set's title comes from its optional
`run_set.json`), per run set its transcripts `<model>/<cond>/<effort>/<task>-k<i>.jsonl` and its `MANIFEST.json`
(planned runs, cost), and the pilot task set (class, reference, tolerance). Every transcript is scored in memory with
the functions of tsbench.score.score; nothing is written into the run folders. Task texts are never shown, only class
names, and only the pilot split is ever loaded.

What the page shows: a summary in three computed sentences; the rule that makes an answer correct, per task class,
with two real examples; per run set and model the share correct per condition (dot with 95 % task bootstrap interval)
and every run by outcome (stacked bars); accuracy per task class and model (heat map); cost, output tokens and API time
per run and per correct answer (box plots, dot plots); why runs gave no answer; the runs that are not evaluable; the
method.

Runs that the scorer leaves out (HTTP 429 in any form, or another API error: tsbench.score.score.not_evaluable_reason)
are not part of any rate. Design:
Figura design system (tsbench.report.page); no pie or donut charts.

The module builds the data (`context`); the page is templates/comparison.html.j2 with its sections as macros in
templates/comparison_parts.html.j2. The template escapes every value.
"""
from __future__ import annotations

import argparse
import datetime
import json
import math
import pathlib
import re
import statistics

from tsbench.core.api_errors import is_context_overflow
from tsbench.report import page
from tsbench.report.base import HARNESS, as_bool, as_number, as_run_sets, median, not_evaluable
from tsbench.report.svg.base import round_half_up
from tsbench.score.run_sets import run_sets_in

__all__ = ["build_html", "collect", "context", "main", "sentences", "heatmap_classes", "box_stats",
           "split_stats", "reason_of", "pick_examples", "rule_rows"]

COLORS = {"A": page.THEME["series-1"], "B": page.THEME["series-2"], "C": page.THEME["series-3"]}  # Figura series-1..3
COND_NAMES = page.COND_NAMES
CONDS = ("A", "B", "C")
MODEL_ORDER = ["haiku", "sonnet", "opus"]
NOT_EVAL = ("na429",)  # left out of every rate: HTTP 429 or another API error
CATEGORY_TEXT = page.CATEGORY_TEXT


# ---------------------------------------------------------------- helpers
def _decimal(x: float, nd: int = 1) -> str:
    """`x` with `nd` decimals, a half rounded up (the format `.0f` takes 2.5 to 2 but 3.5 to 4), never "-0"."""
    r = round_half_up(x, nd)
    return f"{abs(r) if r == 0 else r:.{nd}f}"


def _pct(x) -> str:
    return "–" if x is None else f"{round_half_up(x)} %"


def _usd(x) -> str:
    return "–" if x is None else f"{_decimal(x, 2)} USD"


def display_model(model: str) -> str:
    """`claude-haiku-5-5` -> `Haiku`; any other model id stays as it is."""
    m = re.match(r"^claude-([a-z]+)-", model or "")
    return m.group(1).capitalize() if m else (model or "?")


def is_claude(model: str) -> bool:
    return str(model).startswith("claude-")


def model_key(model: str):
    short = display_model(model).lower()
    return (0, MODEL_ORDER.index(short), "") if short in MODEL_ORDER else (1, 0, model)


def outcome_of(row: dict, task: dict | None, limited: bool) -> str:
    """correct | wrong | harness | na429. `limited`: the scorer leaves the run out (429 or another API error:
    `base.not_evaluable`)."""
    if limited:
        return "na429"
    if as_bool(row.get("correct")):
        return "correct"
    cat = None
    if task is not None:
        try:
            from tsbench.score.taxonomy import failure_category
            cat = failure_category(row, task)
        except Exception:
            cat = None
    if cat is None:
        cat = "wrong" if as_bool(row.get("has_result")) else "no_result"
    return "harness" if cat in HARNESS else "wrong"


# ---------------------------------------------------------------- loading
def _read_json(path: pathlib.Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def load_tasks() -> dict:
    """Pilot tasks by id (only the pilot split is ever loaded)."""
    from tsbench.tasks import load
    return {t["id"]: t for t in load("pilot")}


def reason_of(result: dict | None, correct: bool = False) -> str | None:
    """Why a run gave no answer: 429 | api_error | context_overflow | harness | no_structured, else None.

    429 and api_error are the two reasons of `base.not_evaluable` (HTTP 429 in any form; a 5xx, terminal_reason
    api_error or `API Error:` text); harness = the harness stopped the run (max_turns,
    budget, no result event); no_structured = a run without error but without `structured_output` and not correct, or
    one that the CLI ended after repeated schema-invalid StructuredOutput calls."""
    if not isinstance(result, dict):
        return "harness"
    why = not_evaluable(result)
    if why:
        return "429" if why == "rate_limited" else why
    if is_context_overflow(result):  # the model's request outgrew its context window: counted, and not correct
        return "context_overflow"
    if result.get("subtype") in ("error_max_turns", "error_max_budget_usd") \
            or result.get("terminal_reason") in ("max_turns", "max_budget_usd"):
        return "harness"
    if result.get("subtype") == "error_max_structured_output_retries":  # the model failed the answer schema
        return None if correct else "no_structured"
    if result.get("is_error"):
        return "api_error"
    if not correct and result.get("structured_output") is None:
        return "no_structured"
    return None


def score_in_memory(files, tasks: dict):
    """Score transcripts in memory (writes nothing: the runs may still be writing).
    Returns (rows, result events) in the same order; a row is the row `score_dir` writes (`score.score_row`, typed)
    and `_path`, the transcript's path."""
    from tsbench.score.extract import read_transcript
    from tsbench.score.score import score_row
    rows, results = [], []
    for p, _model, _cond, _effort, task_id, _k in files:
        task = tasks.get(task_id)
        if task is None:
            continue
        tr = read_transcript(p)
        row, _answer = score_row(task, tr, p)
        rows.append({**row, "_path": str(p)})
        results.append(tr.result)
    return rows, results


def check_task_set(run_set_path: pathlib.Path, tasks: dict) -> None:
    """Raises ValueError for a run set made with another task set (tsbench.score.score.check_runs_match)."""
    from tsbench.score.score import check_runs_match
    check_runs_match(run_set_path, tasks, "v2", "pilot")


def collect(run_sets, out_path=None) -> dict:
    """Read and score (in memory) every run of the run sets. `run_sets`: RunSet objects or plain folders."""
    from tsbench.score.score import find_transcripts
    notes: list[str] = []
    runs: list[dict] = []
    planned: dict = {}
    costs: dict = {}
    recorded: dict = {}
    sets = as_run_sets(run_sets)
    tasks = load_tasks()
    for rs in sets:
        d = rs.path
        try:
            check_task_set(d, tasks)
        except Exception as exc:  # noqa: BLE001 - a run set of another task set is not shown
            notes.append(f"{rs.name}: not shown, made with another task set ({type(exc).__name__})")
            continue
        try:
            rows, results = score_in_memory(find_transcripts(d), tasks)
        except Exception as exc:  # noqa: BLE001
            notes.append(f"{rs.name}: scoring failed ({type(exc).__name__}: {exc})")
            rows, results = [], []
        for r, res in zip(rows, results, strict=False):
            oc = outcome_of(r, tasks.get(r.get("task_id")), not_evaluable(res) is not None)
            runs.append({
                "set": rs.name, "model": r.get("model", ""), "cond": r.get("condition", ""),
                "task_id": r.get("task_id", ""), "cls": r.get("class", ""), "outcome": oc,
                "reason": reason_of(res, oc == "correct"), "path": r.get("_path"),
                "rescued": bool(as_bool(r.get("rescued"))),
                "evaluable": oc not in NOT_EVAL, "has_result": bool(as_bool(r.get("has_result"))),
                "out_tok": as_number(r.get("output_tokens")),
                "api_s": as_number(r.get("api_duration_s")) or as_number(r.get("duration_s")),
                "cost": as_number(r.get("cost_usd")), "flags": page.run_flags(r),
            })
        man = _read_json(d / "MANIFEST.json") or {}
        args = man.get("args") or {}
        models = [m for m in str(args.get("models") or "").split(",") if m] or sorted(
            {x.get("model", "") for x in rows}
        )
        conds = (
            man["conditions"]
            if isinstance(man.get("conditions"), list)
            else (
                [c for c in str(args.get("conditions") or "").split(",") if c]
                or sorted({x.get("condition", "") for x in rows})
            )
        )
        n_plan = (man.get("counts") or {}).get("planned")
        if n_plan is not None and len(models) == 1 and len(conds) == 1:
            planned[(rs.name, models[0], conds[0])] = planned.get((rs.name, models[0], conds[0]), 0) + int(n_plan)
        if models and is_claude(models[0]) and man.get("total_cost_usd") is not None:
            costs[rs.name] = costs.get(rs.name, 0.0) + float(man["total_cost_usd"])
        if man.get("total_cost_usd") is not None:  # every run set, Anthropic or not, as its manifest records it
            recorded[rs.name] = (float(man["total_cost_usd"]), not all(is_claude(m) for m in models))
    return {"run_sets": [{"name": rs.name, "title": rs.title} for rs in sets], "runs": runs, "planned": planned,
            "costs": costs, "recorded": recorded, "notes": notes, "date": datetime.date.today().isoformat(),
            "tasks": list(tasks.values()), "examples": pick_examples(runs, tasks)}


def run_sets_of(data: dict) -> list[dict]:
    """[{name, title}] of the page, in order; derived from the runs when the data has no list."""
    if data.get("run_sets"):
        return data["run_sets"]
    return [{"name": n, "title": n} for n in sorted({r["set"] for r in data["runs"]})]


# ---------------------------------------------------------------- aggregation
def _evaluable(rows):
    return [r for r in rows if r["outcome"] not in NOT_EVAL]


def accuracy_of(rows):
    ev = _evaluable(rows)
    return None if not ev else 100.0 * sum(r["outcome"] == "correct" for r in ev) / len(ev)


def cell_counts(rows, planned=None) -> dict:
    """Counts of one cell. `grey` = not evaluable (429) + not run; all parts sum to `n`."""
    c = {"correct": 0, "wrong": 0, "harness": 0, "grey": 0}
    for r in rows:
        c["grey" if r["outcome"] == "na429" else r["outcome"]] += 1
    n = max(len(rows), planned or 0)
    c["grey"] += n - len(rows)
    c["n"] = n
    c["n429"] = sum(r["outcome"] == "na429" for r in rows)
    c["n_notrun"] = n - len(rows)
    c["n_eval"] = len(rows) - c["n429"]
    return c


def _models(runs):
    return sorted({r["model"] for r in runs}, key=model_key)


def per_model_accuracy(runs) -> dict:
    return {
        m: {c: accuracy_of([r for r in runs if r["model"] == m and r["cond"] == c]) for c in CONDS}
        for m in _models(runs)
    }


def heatmap_classes(runs) -> list[str]:
    """Classes from 'every condition can do it' (high accuracy without tools) to 'only with MCP' (low A, big lead of
    C)."""
    classes = sorted({r["cls"] for r in runs})

    def key(cl):
        a = accuracy_of([r for r in runs if r["cls"] == cl and r["cond"] == "A"])
        c = accuracy_of([r for r in runs if r["cls"] == cl and r["cond"] == "C"])
        gap = 0.0 if (a is None or c is None) else c - a
        return (-(-1.0 if a is None else a), gap, cl)
    return sorted(classes, key=key)


def class_gaps(runs) -> list[dict]:
    """Per class, C against the higher of A and B (all models, all run sets)."""
    out = []
    for cl in sorted({r["cls"] for r in runs}):
        acc = {c: accuracy_of([r for r in runs if r["cls"] == cl and r["cond"] == c]) for c in CONDS}
        n = {c: len(_evaluable([r for r in runs if r["cls"] == cl and r["cond"] == c])) for c in CONDS}
        if acc["C"] is None or (acc["A"] is None and acc["B"] is None):
            continue
        best_k = max((k for k in ("A", "B") if acc[k] is not None), key=lambda k: acc[k])
        out.append({"cls": cl, "c": acc["C"], "best": acc[best_k], "best_k": best_k, "gap": acc["C"] - acc[best_k],
                    "n_c": n["C"]})
    return out


def efficiency(runs) -> dict:
    """Per model and condition the medians (output tokens, API seconds) of the evaluable runs with a result."""
    out = {}
    for m in _models(runs):
        out[m] = {}
        for c in CONDS:
            sub = [
                r
                for r in runs
                if r["model"] == m and r["cond"] == c and r["outcome"] not in NOT_EVAL and r["has_result"]
            ]
            out[m][c] = (median([r["out_tok"] for r in sub]), median([r["api_s"] for r in sub])) if sub else None
    return out


def _change(c, other):
    """Relative change of C against `other` in percent (negative = less)."""
    if not c or not other:
        return None
    return 100.0 * (c - other) / other


def _direction(change: float, what: str, fewer: str = "fewer", than: str | None = None) -> str:
    """'N % fewer output tokens [than B]', 'N % more API time', 'about as many output tokens [as B]'."""
    if abs(change) < 1:
        return (f"about as much {what}" if fewer == "less" else f"about as many {what}") + (
            f" as {than}" if than else ""
        )
    shown = f"{round_half_up(abs(change))} % {fewer if change < 0 else 'more'} {what}"
    return shown + (f" than {than}" if than else "")


def sentences(runs) -> list[str]:
    """Three sentences computed from the runs (no fixed numbers)."""
    out = []
    parts = []
    for m, a in per_model_accuracy(runs).items():
        if a["C"] is None:
            continue
        others = ", ".join(f"{k} {_pct(a[k])}" for k in ("A", "B") if a[k] is not None)
        parts.append(f"{display_model(m)} {_pct(a['C'])}" + (f" against {others}" if others else ""))
    if parts:
        out.append("Share of evaluable runs answered correctly with TS-MCP (C): " + "; ".join(parts) + ".")
    else:
        out.append("There are no evaluable runs of condition C yet.")

    gaps = class_gaps(runs)
    if gaps:
        g = max(gaps, key=lambda x: (x["gap"], x["cls"]))
        out.append(f"The largest difference between C and the higher of A and B is in the class “{g['cls']}”: C "
                   f"{_pct(g['c'])} against {_pct(g['best'])} for {g['best_k']} ({page.signed(g['gap'])} pp, "
                   f"n = {g['n_c']} runs with C).")
    else:
        out.append("A comparison per task class is not possible yet: there are no evaluable runs.")

    eff = {m: e for m, e in efficiency(runs).items() if e.get("C")}
    seg = []
    for ref in ("B", "A"):
        tok = [x for x in (_change(e["C"][0], (e.get(ref) or (None, None))[0]) for e in eff.values()) if x is not None]
        sec = [x for x in (_change(e["C"][1], (e.get(ref) or (None, None))[1]) for e in eff.values()) if x is not None]
        if tok and sec:
            t, s = statistics.median(tok), statistics.median(sec)
            seg.append(f"against {page.COND_LABEL[ref]}: {_direction(t, 'output tokens')} and "
                       f"{_direction(s, 'API time', 'less')}")
    if seg:
        out.append("In the median over the models, C needs " + "; ".join(seg) + ".")
    else:
        out.append("Tokens and time cannot be compared yet: runs of a comparison condition are missing.")
    return out


# ---------------------------------------------------------------- distributions, cost per correct answer
def _quantile(xs: list[float], q: float) -> float:
    """Quantile with linear interpolation (as numpy.percentile by default); xs sorted and not empty."""
    pos = (len(xs) - 1) * q
    lo = math.floor(pos)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


def box_stats(values) -> dict | None:
    """Box-plot figures: quartiles (linear interpolation), whiskers = most extreme value within 1.5 IQR, outliers."""
    xs = sorted(float(v) for v in values if v is not None and not (isinstance(v, float) and math.isnan(v)))
    if not xs:
        return None
    q1, med, q3 = _quantile(xs, .25), _quantile(xs, .5), _quantile(xs, .75)
    iqr = q3 - q1
    lo_f, hi_f = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    inside = [x for x in xs if lo_f <= x <= hi_f]
    return {"n": len(xs), "q1": q1, "median": med, "q3": q3, "lo": min(inside), "hi": max(inside),
            "outliers": [x for x in xs if x < lo_f or x > hi_f]}


def use_log(values, ratio: float = 30.0) -> bool:
    """A logarithmic axis when the largest value is more than `ratio` times the smallest positive one."""
    pos = [v for v in values if v is not None and v > 0]
    return bool(pos) and max(pos) / min(pos) > ratio


def split_stats(rows, key: str) -> dict:
    """Median of `key` for correct and for wrong runs, the sum, and the sum per correct answer.

    wrong = answered wrongly or stopped by a harness limit; not-evaluable runs do not count. Without a correct answer
    `per_correct` is None (not 0 and not infinite)."""
    ev = [r for r in rows if r["outcome"] not in NOT_EVAL]
    ok = [r for r in ev if r["outcome"] == "correct"]
    bad = [r for r in ev if r["outcome"] != "correct"]
    val = lambda rs: [r.get(key) for r in rs if r.get(key) is not None]  # noqa: E731
    total = sum(val(ev))
    return {"n_ok": len(ok), "n_bad": len(bad), "median_ok": median(val(ok)), "median_bad": median(val(bad)),
            "total": total if val(ev) else None, "per_correct": total / len(ok) if ok and val(ev) else None}


# ---------------------------------------------------------------- rules and examples
SCHEMA_NAME = {"fit": "fit (Dq, B, C)", "curve": "curve", "batch": "batch", "pairing": "pairing", "diagram": "diagram"}


def _percent_rounded(x) -> str:
    return f"{_decimal(100 * x, 0 if abs(100 * x - round(100 * x)) < 1e-9 else 1)} %"


def rule_rows(tasks) -> list[dict]:
    """Per task class the rule in plain words, read from the task records (no fixed numbers)."""
    by_cls: dict = {}
    for t in tasks:
        by_cls.setdefault(t["class"], []).append(t)
    out = []
    for cls in sorted(by_cls):
        ts = by_cls[cls]
        schema = ts[0].get("answer_schema", "fit")
        variants = []
        for t in ts:
            tol = t.get("tolerance") or {}
            if schema == "fit":
                if t.get("expect_out_of_scope"):
                    v = "out_of_scope = true and Dq, B = null"
                else:
                    v = ", ".join(
                        f"{p} {_percent_rounded(tol[p])}" for p in t.get("required") or [] if tol.get(p) is not None
                    ) or "no quantity required"
            elif schema == "curve":
                n = len(t.get("reference_curve") or [])
                v = (f"all {n} points" if n else "all points") \
                    + f" within {_percent_rounded(tol.get('curve_rel', 0.03))} or " \
                    f"{_decimal(tol.get('curve_abs', 0.3), 1)} E/B"
            elif schema == "batch":
                n = len((t.get("reference") or {}).get("values") or [])
                v = (f"all {n} entries" if n else "all entries") \
                    + f" within {_percent_rounded(tol.get('item_rel', 0.02))}"
            elif schema == "pairing":
                v = "nodes and edges exactly right, ground terms right"
            elif schema == "diagram":
                ref = t.get("reference") or {}
                total = sum(len(x) for x in ref.get("levels") or [])
                need = math.ceil(tol.get("item_accuracy_min", 0.95) * total - 1e-9) if total else None
                v = (f"at least {need} of {total} values" if need else "share of right values") + \
                    f" within {_percent_rounded(tol.get('curve_rel', 0.03))} or " \
                    f"{_decimal(tol.get('curve_abs', 0.3), 1)} E/B"
            else:
                v = "see the task record"
            if v not in variants:
                variants.append(v)
        rule = " / ".join(variants)
        if schema == "fit" and not ts[0].get("expect_out_of_scope"):
            rule = "relative error per required parameter at most: " + rule
        out.append({"cls": cls, "schema": schema, "rule": rule, "n": len(ts)})
    return out


def _structured_of(path) -> dict | None:
    from tsbench.score.extract import read_transcript
    so = (read_transcript(path).result or {}).get("structured_output")
    return so if isinstance(so, dict) else None


def example_check(task: dict, answer: dict) -> dict | None:
    """Recompute the example: per parameter answer, reference, relative error, tolerance. None when not readable."""
    rows = []
    for p in task.get("required") or []:
        ref, tol, got = (task.get("reference") or {}).get(p), (task.get("tolerance") or {}).get(p), answer.get(p)
        if not isinstance(got, (int, float)) or isinstance(got, bool) or not ref or tol is None:
            return None
        rel = abs(got - ref) / abs(ref)
        rows.append({"param": p, "got": got, "ref": ref, "rel": rel, "tol": tol, "ok": rel <= tol + 1e-12})
    if not rows:
        return None
    oos = answer.get("out_of_scope")
    return {"rows": rows, "oos": oos, "ok": all(r["ok"] for r in rows) and oos is False}


def pick_examples(runs, tasks: dict, read=_structured_of) -> dict | None:
    """Two real runs: one correct and one wrong (fit tasks, pilot split only, Claude, recomputed to the same verdict as
    the scorer). The choice is deterministic; it prefers the same task and a wrong answer with a single wrong
    parameter."""
    def usable(r):
        t = tasks.get(r.get("task_id"))
        return (t is not None and t.get("split") == "pilot" and t.get("answer_schema", "fit") == "fit"
                and not t.get("expect_out_of_scope") and r.get("path") and r["outcome"] in ("correct", "wrong")
                and is_claude(r["model"]))
    cands = sorted((r for r in runs if usable(r)),
                   key=lambda r: (r["cls"] != "closed_form", model_key(r["model"]), r["task_id"], r["cond"], r["set"]))
    found: dict = {"correct": [], "wrong": []}
    for r in cands:
        if len(found["correct"]) >= 6 and len(found["wrong"]) >= 6:
            break
        if len(found[r["outcome"]]) >= 6:
            continue
        task = tasks[r["task_id"]]
        ans = read(r["path"])
        chk = example_check(task, ans) if ans else None
        if chk is None or chk["ok"] != (r["outcome"] == "correct"):
            continue
        found[r["outcome"]].append({"run": r, "task": task, "answer": ans, "check": chk})
    if not found["wrong"] or not found["correct"]:
        return None
    wrong = sorted(found["wrong"], key=lambda e: (sum(not x["ok"] for x in e["check"]["rows"]) != 1,))[0]
    same = [e for e in found["correct"] if e["task"]["id"] == wrong["task"]["id"]] or \
           [e for e in found["correct"] if e["task"]["class"] == wrong["task"]["class"]] or found["correct"]
    return {"correct": _slim(same[0]), "wrong": _slim(wrong)}


def _slim(e: dict) -> dict:
    r = e["run"]
    return {"task_id": r["task_id"], "cls": r["cls"], "model": r["model"], "cond": r["cond"], "outcome": r["outcome"],
            "answer": {k: (v if not isinstance(v, str) else v[:160]) for k, v in e["answer"].items()},
            "check": e["check"], "required": list(e["task"].get("required") or [])}


# ---------------------------------------------------------------- figure parts (Figura, drawn by page.RUNTIME_JS)
def heat_color(p: float) -> tuple[str, str]:
    """(background, text colour) for p in [0, 1]: from the Figura tint (light) to the Figura blue (dark)."""
    return page.color_ramp(p)


def _segment_counts(cnt: dict) -> list[int]:
    return [cnt["correct"], cnt["wrong"], cnt["harness"], cnt["n429"], cnt["n_notrun"]]


def rate_row(cond: str, cnt: dict, tasks: list[tuple[int, int]]) -> dict:
    """One row of the share chart: share correct (evaluable runs only) with the 95 % task-clustered bootstrap interval
    (`tasks`: correct and evaluable runs per task) and the stacked counts. Without evaluable runs there is no dot
    (p = None)."""
    segments = dict(zip(page.SEG_KEYS, _segment_counts(cnt), strict=False))
    return page.rate_row(page.COND_LABEL[cond], cond, segments, cnt["n_eval"], cnt["n"], tasks)


def _status_chips(cnt: dict) -> list[dict]:
    """Key and text per status that occurs; the template draws icon and text (never colour alone)."""
    return [
        {"key": k, "text": f"{v} {page.STATUS_TEXT[k]}"}
        for k, v in zip(page.SEG_KEYS, _segment_counts(cnt), strict=False)
        if v
    ]


def _rate_figure(cnts: dict, title: str, tasks: dict) -> dict:
    """cnts: condition -> counts, tasks: condition -> (correct, evaluable runs) per task. The data of the dot chart (a)
    and the stacked bars (b), with a text version below."""
    rows = [rate_row(c, cnts[c], tasks.get(c, [])) for c in CONDS if c in cnts]
    entries = []
    for r in rows:
        if r["p"] is None:
            core = "no evaluable runs"
        elif r["few"]:
            core = f"{r['correct']} of {r['n_eval']} correct ({page.few_text(r['n_eval'])})"
        else:
            core = (
                f"{r['correct']} of {r['n_eval']} correct ({_decimal(r['p'], 0)} %; "
                f"95 % interval {_decimal(r['lo'], 0)} to {_decimal(r['hi'], 0)} %)"
            )
        entries.append({"label": page.COND_LABEL[r["cond"]], "core": core, "chips": _status_chips(cnts[r["cond"]])})
    alt = f"{title}: share of correct answers with 95 % interval and number of runs per outcome, conditions A, B, C"
    return {"title": title, "alt": alt, "spec": {"rows": rows, "left": 80}, "entries": entries}


def _dots_figure(models, series, value, fmt, title: str, xlabel: str, note: str = "", na=None) -> dict:
    """Dots instead of bars: one row per model, one dot per condition with a direct label; axis from 0."""
    rows = [{"label": display_model(m), "v": {c: value(m, c) for c in series},
             "na": {c: (na(m, c) if na else None) for c in series}} for m in models]
    spec = {"rows": rows, "conds": list(series), "names": {c: COND_NAMES[c] for c in series}, "xLabel": xlabel,
            "left": 52, "width": "single"}
    table = [{"label": r["label"], "cells": [fmt(r["v"][c]) if r["v"][c] is not None else "–" for c in series]}
             for r in rows]
    return {"title": title, "alt": f"{title}: dot plot per model and condition", "spec": spec,
            "heads": [page.COND_LABEL[c] for c in series], "rows": table, "note": note}


# ---------------------------------------------------------------- sections
def _header(data) -> dict:
    runs = data["runs"]
    sets = []
    for s in run_sets_of(data):
        rs = [r for r in runs if r["set"] == s["name"]]
        n429 = sum(r["outcome"] == "na429" for r in rs)
        n_rescued = sum(bool(r.get("rescued")) for r in rs)
        extra = f" (of which {n429} not evaluable, 429)" if n429 else ""
        if n_rescued:
            extra += f" (of which {n_rescued} rescued: last answer before a turn or budget limit)"
        label = s["name"] if s["title"] == s["name"] else f"{s['title']} ({s['name']})"
        sets.append({"label": label, "text": f"{len(rs)} runs{extra}"})
    return {"date": data["date"], "cost": recorded_cost(data), "sets": sets, "notes": list(data["notes"])}


def recorded_cost(data) -> dict | None:
    """The cost the manifests record ({"text", "estimate"}), summed over the run sets; None when no manifest records
    one. For a model outside Anthropic the figure is the Claude CLI's estimate at Anthropic prices, not a bill, and
    `estimate` says so."""
    rec = data.get("recorded")
    if rec is None:  # data made by hand (tests): the Anthropic costs only
        rec = {k: (v, False) for k, v in (data.get("costs") or {}).items()}
    if not rec:
        return None
    return {"text": _usd(sum(v for v, _ in rec.values())), "estimate": any(e for _, e in rec.values())}


def _differences(acc: dict) -> str:
    """'C \u2212 B +60 pp, C \u2212 A +60 pp (shares of the evaluable runs)': C's share minus each other share."""
    if acc.get("C") is None or all(acc.get(k) is None for k in ("A", "B")):
        return "Too few evaluable runs for a difference"
    parts = [f"C \u2212 {k} {page.signed(acc['C'] - acc[k])} pp" for k in ("B", "A") if acc.get(k) is not None]
    return ", ".join(parts) + " (shares of the evaluable runs)"


def _efficiency_line(med: dict) -> str | None:
    c = med.get("C")
    if not c:
        return None
    segs = []
    for ref in ("B", "A"):
        o = med.get(ref)
        if not o:
            continue
        t, s = _change(c[0], o[0]), _change(c[1], o[1])
        got = [x for x in (_direction(t, "output tokens") if t is not None else None,
                           _direction(s, "API time", "less") if s is not None else None) if x]
        if got:
            segs.append(f"against {page.COND_LABEL[ref]}: " + " and ".join(got))
    if not segs:
        return None
    med_txt = (f"Median of C: {_decimal(c[0], 0) if c[0] is not None else '–'} output tokens, "
               f"{_decimal(c[1], 1) if c[1] is not None else '–'} s API time")
    return med_txt + ". C needs " + "; ".join(segs) + "."


def _model_card(data, model: str, set_name: str) -> dict:
    rs = [r for r in data["runs"] if r["model"] == model and r["set"] == set_name]
    eff = efficiency(rs).get(model, {})
    cnts, acc, pairs = {}, {}, {}
    for c in CONDS:
        sub = [r for r in rs if r["cond"] == c]
        cnt = cell_counts(sub, data["planned"].get((set_name, model, c), 0))
        if not cnt["n"]:
            continue
        cnts[c] = cnt
        pairs[c] = page.task_pairs((r["task_id"], r["outcome"] == "correct") for r in _evaluable(sub))
        acc[c] = accuracy_of(sub) if cnt["n_eval"] >= 3 else None
    return {
        "model": display_model(model),
        "figure": _rate_figure(cnts, f"{display_model(model)}: share correct per condition and outcome of the runs",
                               pairs),
        "differences": _differences(acc),
        "efficiency": _efficiency_line(eff),
        "cost_note": not is_claude(model),
        "flags": [dict(f, cond=c) for c in CONDS
                  for f in page.flag_notes(_evaluable([r for r in rs if r["cond"] == c]),
                                           key=lambda r: r.get("flags") or [])],
    }


def _verdict(data) -> dict:
    sets = []
    for s in run_sets_of(data):
        models = _models([r for r in data["runs"] if r["set"] == s["name"]])
        if models:
            sets.append({"title": s["title"], "cards": [_model_card(data, m, s["name"]) for m in models]})
    return {"sets": sets}


def _heatmap(data) -> dict | None:
    """The heat map; None without runs."""
    rs = data["runs"]
    if not rs:
        return None
    cols = [(m, c) for m in _models(rs) for c in CONDS]
    rows = []
    for cl in heatmap_classes(rs):
        cells = []
        for m, c in cols:
            sub = _evaluable([r for r in rs if r["cls"] == cl and r["model"] == m and r["cond"] == c])
            if not sub:
                cells.append(None)
                continue
            p = sum(r["outcome"] == "correct" for r in sub) / len(sub)
            bg, fg = heat_color(p)
            cells.append({"bg": bg, "fg": fg, "p": round(p, 3), "dark": p >= .5, "pct": round_half_up(p * 100),
                          "n": len(sub),
                          "title": f"{cl} · {display_model(m)} {c}: {round_half_up(p * 100)} % of n = {len(sub)}"})
        rows.append({"cls": cl, "cells": cells})
    return {"cols": [{"model": display_model(m), "cond": c, "color": COLORS[c]} for m, c in cols], "rows": rows,
            "scale": [{"bg": heat_color(p)[0], "fg": heat_color(p)[1], "p": p, "dark": p >= .5, "pct": int(p * 100)}
                      for p in (0, .25, .5, .75, 1)]}


def _costs(data) -> dict | None:
    """Cost and time; None without runs."""
    rs = [r for r in data["runs"] if r["outcome"] not in NOT_EVAL and r["has_result"]]
    if not rs:
        return None
    return {"per_correct": _cost_split(data), "boxplots": _boxplots(rs),
            "sets": [{"title": s["title"], "total": _usd(data["costs"][s["name"]])}
                     for s in run_sets_of(data) if s["name"] in data["costs"]],
            "total": _usd(sum(data["costs"].values()))}


def _not_evaluable(data) -> dict | None:
    """Not-evaluable runs of all run sets (HTTP 429 or another API error) per model and condition, left out of every
    rate. None without such runs."""
    if not any(r["outcome"] in NOT_EVAL for r in data["runs"]):
        return None
    body = []
    for s in run_sets_of(data):
        sub_set = [r for r in data["runs"] if r["set"] == s["name"]]
        for m in _models(sub_set):
            for c in CONDS:
                sub = [r for r in sub_set if r["model"] == m and r["cond"] == c]
                n429 = sum(r["outcome"] == "na429" for r in sub)
                if n429:
                    body.append({"title": s["title"], "model": display_model(m), "cond": c, "n": len(sub),
                                 "n_eval": len(sub) - n429, "n429": n429})
    return {"rows": body}


# ---------------------------------------------------------------- box plots
_METRICS = [("cost", "Cost per run (USD)", "USD", lambda v: _decimal(v, 3)),
            ("out_tok", "Output tokens per run", "tokens", lambda v: _decimal(v, 0)),
            ("api_s", "API seconds per run", "s", lambda v: _decimal(v, 1))]


def _boxplot(title: str, unit: str, fmt, groups: dict, lo: float, hi: float, log: bool) -> dict:
    """One horizontal box plot (Figura) with one value axis. groups: condition -> {'ok': [..], 'bad': [..]}.
    Filled = correct runs, hatched = wrong runs; whiskers without caps, circles = outliers."""
    rows, table = [], []
    for c in CONDS:
        for kind, name in (("ok", "correct"), ("bad", "wrong")):
            vals = groups.get(c, {}).get(kind, [])
            vals = [v for v in vals if v > 0] if log else list(vals)
            st = box_stats(vals)
            label = f"{c} · {name}"
            tip = None if st is None else (
                f"{label}: n = {st['n']}, median {fmt(st['median'])}, Q1 {fmt(st['q1'])}, Q3 {fmt(st['q3'])}, "
                f"whiskers {fmt(st['lo'])} to {fmt(st['hi'])}, outliers {len(st['outliers'])} ({unit})")
            rows.append(
                {
                    "label": label,
                    "cond": c,
                    "ok": kind == "ok",
                    "tip": tip,
                    "st": None
                    if st is None
                    else {
                        "n": st["n"],
                        "q1": st["q1"],
                        "median": st["median"],
                        "q3": st["q3"],
                        "lo": st["lo"],
                        "hi": st["hi"],
                        "out": st["outliers"],
                    },
                }
            )
            table.append({"label": label, "n": st["n"] if st else 0, "median": fmt(st["median"]) if st else "–"})
    domain = [lo / 1.6, hi * 1.6] if log else [0.0, (hi * 1.06) or 1.0]
    spec = {"rows": rows, "log": log, "domain": domain, "xLabel": f"{unit}{', log' if log else ''}", "left": 52}
    return {"title": title, "alt": f"{title}: box plots per condition, correct and wrong", "spec": spec, "rows": table}


def _boxplots(rows) -> dict | None:
    """Per measure and model one box plot with the conditions A, B, C; correct and wrong one below the other. None
    when no run has a measure."""
    metrics = []
    for key, label, unit, fmt in _METRICS:
        use = [r for r in rows if r.get(key) is not None and (key != "cost" or is_claude(r["model"]))]
        vals = [r[key] for r in use]
        if not vals:
            continue
        pos = [v for v in vals if v > 0]
        log = use_log(vals)
        lo, hi = (min(pos), max(pos)) if log else (0.0, max(vals))
        figs = []
        for m in _models(use):
            groups = {
                c: {
                    "ok": [r[key] for r in use if r["model"] == m and r["cond"] == c and r["outcome"] == "correct"],
                    "bad": [r[key] for r in use if r["model"] == m and r["cond"] == c and r["outcome"] != "correct"],
                }
                for c in CONDS
            }
            figs.append(_boxplot(f"{display_model(m)}: {label}", unit, fmt, groups, lo, hi, log))
        note = ("Logarithmic axis (“log”) because the largest value is more than 30 times the smallest."
                if log else "Linear axis from 0.")
        metrics.append({"label": label, "note": note, "figures": figs})
    if not metrics:
        return None
    return {"metrics": metrics, "legend": [{"color": COLORS[c], "cond": c, "label": page.COND_LABEL[c]} for c in CONDS]}


# ---------------------------------------------------------------- sections: rules, cost split
def _rules(data) -> dict:
    tasks = data.get("tasks")
    if tasks is None:
        try:
            tasks = list(load_tasks().values())
        except Exception:  # noqa: BLE001
            tasks = []
    return {
        "rows": [
            {"cls": r["cls"], "schema": SCHEMA_NAME.get(r["schema"], r["schema"]), "rule": r["rule"]}
            for r in rule_rows(tasks)
        ],
        "categories": [{"code": k, "text": v} for k, v in _category_items()],
        "examples": _examples(data.get("examples")),
    }


def _category_items():
    try:
        from tsbench.score.taxonomy import CATEGORIES
    except Exception:  # pragma: no cover
        CATEGORIES = tuple(CATEGORY_TEXT)
    return [(c, CATEGORY_TEXT.get(c, c)) for c in CATEGORIES]


def _example(kind: str, e: dict) -> dict:
    chk = e["check"]
    rows = [{"param": r["param"], "got": _decimal(r["got"], 2), "ref": _decimal(r["ref"], 2),
             "rel": _decimal(100 * r["rel"], 2), "tol": _percent_rounded(r["tol"]), "ok": r["ok"],
             "ok_text": "yes" if r["ok"] else "no"} for r in chk["rows"]]
    oos_ok = chk["oos"] is False
    return {"kind": kind, "task_id": e["task_id"], "model": display_model(e["model"]), "cond": e["cond"],
            "answer": json.dumps(e["answer"], ensure_ascii=False, indent=1), "rows": rows,
            "oos": {"text": str(chk["oos"]).lower(), "ok": oos_ok, "ok_text": "yes" if oos_ok else "no"},
            "verdict": "correct" if chk["ok"] else "wrong"}


def _examples(ex) -> dict | None:
    if not ex:
        return None
    return {"correct": _example("correct", ex["correct"]), "wrong": _example("wrong", ex["wrong"])}


def _fmt_money(x) -> str:
    return "–" if x is None else _decimal(x, 3)


def _cost_split(data) -> dict | None:
    """Cost, tokens and time per correct answer; None without evaluable runs."""
    rs = _evaluable(data["runs"])
    if not rs:
        return None
    models = _models(rs)
    body, per_correct = [], {}
    for m in models:
        for c in CONDS:
            sub = [r for r in rs if r["model"] == m and r["cond"] == c]
            if not sub:
                continue
            cells = {k: split_stats(sub, k) for k in ("cost", "out_tok", "api_s")}
            if not is_claude(m):
                cells["cost"] = {"n_ok": cells["cost"]["n_ok"], "n_bad": cells["cost"]["n_bad"], "median_ok": None,
                                 "median_bad": None, "total": None, "per_correct": None}
            per_correct[(m, c)] = {k: v["per_correct"] for k, v in cells.items()}
            st = cells["out_tok"]
            shown = []
            for k, f in (
                ("cost", _fmt_money), ("out_tok", lambda v: _decimal(v, 0)), ("api_s", lambda v: _decimal(v, 1))
            ):
                s_ = cells[k]
                pc = f(s_["per_correct"]) if s_["per_correct"] is not None else (
                    "no correct answer" if s_["n_ok"] == 0 and (s_["total"] is not None or k != "cost") else "–")
                shown.append({"ok": "–" if s_["median_ok"] is None else f(s_["median_ok"]),
                              "bad": "–" if s_["median_bad"] is None else f(s_["median_bad"]), "per": pc})
            body.append({"model": display_model(m), "cond": c, "color": COLORS[c], "n_ok": st["n_ok"],
                         "n_bad": st["n_bad"], "cells": shown})
    claude_models = [m for m in models if is_claude(m)]
    charts = []

    def no_correct(m, c):
        return (
            "no correct answer"
            if (per_correct.get((m, c)) is not None and (per_correct.get((m, c)) or {}).get("cost") is None)
            else None
        )

    if claude_models:
        charts.append(_dots_figure(claude_models, CONDS, lambda m, c: (per_correct.get((m, c)) or {}).get("cost"),
                                   lambda v: _decimal(v, 3),
                                   "Cost per correct answer: total cost divided by the number of correct runs",
                                   "Cost per correct answer (USD)",
                                   "No dot: no correct answer; the measure is not defined then.", na=no_correct))
    charts.append(_dots_figure(models, CONDS, lambda m, c: (per_correct.get((m, c)) or {}).get("api_s"),
                               lambda v: _decimal(v, 0),
                               "API seconds per correct answer: total time divided by the number of correct runs",
                               "API time per correct answer (s)", na=lambda m, c: None))
    return {"rows": body, "charts": charts}


REASON_COLUMNS = [("429", "429 (rate limit)"), ("api_error", "other API error"),
                  ("context_overflow", "context overflow"), ("harness", "harness limit"),
                  ("no_structured", "structured_output missing")]


def _reasons(data) -> dict | None:
    """Why runs gave no answer, per run set, model and condition (only cells with at least one such run). None when
    every run gave an answer."""
    body = []
    for s in run_sets_of(data):
        sub_set = [r for r in data["runs"] if r["set"] == s["name"]]
        for m in _models(sub_set):
            for c in CONDS:
                sub = [r for r in sub_set if r["model"] == m and r["cond"] == c]
                counts = [sum(r.get("reason") == k for r in sub) for k, _ in REASON_COLUMNS]
                if not sub or not any(counts):
                    continue
                body.append({"title": s["title"], "model": display_model(m), "cond": c, "n": len(sub), "counts": counts,
                             "correct": sum(r["outcome"] == "correct" for r in sub)})
    if not body:
        return None
    return {"columns": [label for _, label in REASON_COLUMNS], "rows": body}


# ---------------------------------------------------------------- the page
TITLE = "TS-MCP benchmark: comparison"


def context(data: dict) -> dict:
    """What templates/comparison.html.j2 needs, from the data of `collect` (or hand-made data with the same keys):
    strings, numbers, lists and dicts only, no HTML. A section without content is None."""
    return {"title": TITLE, "header": _header(data), "sentences": sentences(data["runs"]), "rules": _rules(data),
            "verdict": _verdict(data), "heatmap": _heatmap(data), "costs": _costs(data), "reasons": _reasons(data),
            "not_evaluable": _not_evaluable(data)}


def build_html(data: dict) -> str:
    """The whole page from the data of `collect` (or hand-made data with the same keys)."""
    return str(page.render("comparison.html.j2", **context(data)))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="tsbench report comparison", description=__doc__.split("\n")[0])
    ap.add_argument("--runs", action="append", required=True, metavar="DIR",
                    help="a run set, or a folder holding run sets (repeatable)")
    ap.add_argument("--out", required=True, metavar="FILE")
    a = ap.parse_args(argv)
    run_sets = run_sets_in(a.runs)
    if not run_sets:
        ap.error("no run set found under --runs")
    out = pathlib.Path(a.out)
    data = collect(run_sets, out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build_html(data), encoding="utf-8")
    print(f"wrote {out} ({page.plural(len(data['runs']), 'run')} from {page.plural(len(data['run_sets']), 'run set')})")
    for s in sentences(data["runs"]):
        print("-", s)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
