"""Cost and wall-time estimate of a run plan from the runs already measured. No API call, no model call.

    tsbench plan estimate --plan PLAN.jsonl --from-runs RUNS_1 RUNS_2 ...

How the numbers are made:
  * Samples are the rows of `scores.csv` in the `--from-runs` directories (`cost_usd`, `wall_time_s`), grouped by
    model x condition x measured class. When several directories hold runs of the same model x condition, the LAST
    directory named wins and the earlier samples of that model x condition are dropped (name a re-run after the run
    it replaces).
  * A run of the plan costs the mean of the samples of its model x condition x measured class. When the measured runs
    hold samples of the plan class itself, those are used and the factor is 1. Otherwise the measured
    class is MEASURED_CLASS[plan class] and the mean is multiplied by CLASS_FACTOR. A class without samples falls back
    to the pooled mean of its model x condition, times the factor (shown as n=0 in the table).
  * "expected" is the sum of those means. Two p90 figures are printed and they are different things:
    "p90 total" is the 90th percentile of the TOTAL over BOOTSTRAP_DRAWS seeded resamples, each run drawing one of its
    class samples (it only sees the spread of the samples, so it is narrow when the runs are many);
    "sum p90s" bills every run at its own p90: the run's mean times the tail ratio (p90 / mean) of its model x condition
    (never below 1), summed. Budget with the second, expect the first. Wall time is the same, summed over the runs
    of a model (serial execution).
  * `--overhead` multiplies the cost and time of every run (default 1.0), for example to add a turn that the measured
    runs lack.
Small n: with few runs per class and cell the means are rough and the p90 of a class is not measurable; the n behind
every number is printed.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import pathlib
import sys
from collections import defaultdict

import numpy as np

from tsbench import plan as P

BOOTSTRAP_DRAWS = 4000
BOOTSTRAP_SEED = 20261025
# plan class -> class of the measured runs that is closest in what the model has to do; used only when
# the measured runs hold no samples of the plan class itself
MEASURED_CLASS = {
    "closed_form": "closed_form",
    "experimental": "experimental",
    "numerical": "numerical",
    "numerical_hard": "numerical",     # same task shape as numerical, more bands to fit and a harder ground state
    "racah_c": "racah_c",
    "tetrahedral": "tetrahedral",      # its own class; measured_class() also maps out_of_scope/tetrahedral rows here
    "out_of_scope": "out_of_scope",
    "crossover": "numerical",          # one number from a model call, like the numerical fits
    "curve": "racah_c",                # a table read-out (terms table) with several values to report
    "literature_all": "experimental",  # a fit of printed literature bands, more bands and C
    "literature_new": "experimental",  # same task type as literature_all, newer sources
    "batch": "numerical",              # eight model calls or calculations in one task
    "pairing": "racah_c",              # a terms-table read-out over several configurations
    "diagram": "curve",                # 9 points x 6 levels: the same kind of answer as a curve task,
}                                      # three times as long
# diagram: 54 values instead of 9, so more output than a curve task
# applied only to a mapped class (a plan class priced from another class)
CLASS_FACTOR = {"numerical_hard": 1.5, "crossover": 1.5, "curve": 1.5, "literature_all": 1.2, "literature_new": 1.2,
                "batch": 2.5, "pairing": 1.5, "diagram": 1.5}


def measured_class(row: dict) -> str:
    """Tetrahedral tasks stored as class out_of_scope, subtype tetrahedral, count as their own class."""
    return "tetrahedral" if row.get("subtype") == "tetrahedral" else row["class"]


def _num(v):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(x) else x


def read_samples(dirs) -> tuple[dict, dict]:
    """({(model, cond): {class: [(cost, wall), ...]}}, {(model, cond): directory it came from}); the last directory
    that has a model x condition wins."""
    per_dir = []
    for d in dirs:
        path = pathlib.Path(d) / "scores.csv"
        if not path.is_file():
            raise SystemExit(f"estimate: {path} not found")
        cells: dict = defaultdict(lambda: defaultdict(list))
        with open(path, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                cost = _num(row.get("cost_usd"))
                if cost is None:
                    continue
                wall = _num(row.get("wall_time_s"))
                wall = wall if wall is not None else _num(row.get("duration_s"))
                cells[(row["model"], row["condition"])][measured_class(row)].append((cost, wall))
        per_dir.append((str(d), cells))
    out: dict = {}
    source: dict = {}
    for name, cells in per_dir:
        for key, classes in cells.items():
            out[key] = classes
            source[key] = name
    return out, source


def _pooled(classes: dict) -> list[tuple[float, float | None]]:
    return [s for samples in classes.values() for s in samples]


def _mean(values):
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else None


def _p90(values):
    values = [v for v in values if v is not None]
    return float(np.percentile(values, 90)) if values else None


def estimate(runs: list[dict], samples: dict, *, overhead: float = 1.0, draws: int = BOOTSTRAP_DRAWS,
             seed: int = BOOTSTRAP_SEED) -> dict:
    """Totals per model and overall. `runs` are the run records of a plan."""
    rng = np.random.default_rng(seed)
    per_model: dict = defaultdict(lambda: {"n_runs": 0, "mean_cost": 0.0, "sum_p90_cost": 0.0, "mean_wall": 0.0,
                                           "boot_cost": np.zeros(draws), "boot_wall": np.zeros(draws),
                                           "unmeasured": 0})
    detail: dict = {}
    warnings: list[str] = []
    for r in runs:
        key = (r["model"], r["condition"])
        m = per_model[r["model"]]
        m["n_runs"] += 1
        classes = samples.get(key)
        if not classes:
            m["unmeasured"] += 1
            continue
        # the plan class's own samples first (no factor: they are that class); else the mapped class times its factor
        own_class = classes.get(r["task_class"])
        want = r["task_class"] if own_class else MEASURED_CLASS[r["task_class"]]
        factor = (1.0 if own_class else CLASS_FACTOR.get(r["task_class"], 1.0)) * overhead
        pooled = _pooled(classes)
        own = own_class or classes.get(want) or []
        use = own or pooled
        costs, walls = [c for c, _w in use], [w for _c, w in use]
        pooled_costs = [c for c, _w in pooled]
        mean_c, mean_w = _mean(costs), _mean(walls) or 0.0
        tail = (_p90(pooled_costs) / _mean(pooled_costs)) if _mean(pooled_costs) else 1.0
        m["mean_cost"] += factor * mean_c
        m["sum_p90_cost"] += factor * mean_c * max(tail, 1.0)
        m["mean_wall"] += factor * mean_w
        idx = rng.integers(len(use), size=draws)
        m["boot_cost"] += factor * np.asarray(costs)[idx]
        wl = np.asarray([w if w is not None else mean_w for w in walls])
        m["boot_wall"] += factor * wl[idx]
        d = detail.setdefault((r["model"], r["condition"], r["task_class"]), {
            "n_plan_runs": 0, "measured_class": want, "n_samples": len(own), "factor": factor, "mean_cost": mean_c,
            "mean_wall_s": mean_w})
        d["n_plan_runs"] += 1
    for model, m in per_model.items():
        if m["unmeasured"]:
            warnings.append(f"{model}: {m['unmeasured']} runs have no measured model x condition; "
                            "they are NOT in the totals")
    models = {}
    for model, m in sorted(per_model.items()):
        models[model] = {"n_runs": m["n_runs"], "unmeasured_runs": m["unmeasured"], "expected_cost": m["mean_cost"],
                         "p90_cost": float(np.percentile(m["boot_cost"], 90)), "sum_p90_cost": m["sum_p90_cost"],
                         "expected_wall_s": m["mean_wall"], "p90_wall_s": float(np.percentile(m["boot_wall"], 90))}
    # the total over models: bootstrap draws are independent per model, so add the draws, not the percentiles
    total_cost = sum(per_model[m]["boot_cost"] for m in per_model)
    total_wall = sum(per_model[m]["boot_wall"] for m in per_model)
    total = {"n_runs": sum(m["n_runs"] for m in models.values()),
             "expected_cost": sum(m["expected_cost"] for m in models.values()),
             "p90_cost": float(np.percentile(total_cost, 90)),
             "sum_p90_cost": sum(m["sum_p90_cost"] for m in models.values()),
             "expected_wall_s": sum(m["expected_wall_s"] for m in models.values()),
             "p90_wall_s": float(np.percentile(total_wall, 90))}
    return {"models": models, "total": total, "detail": detail, "warnings": warnings}


def pooled_table(samples: dict, source: dict) -> list[dict]:
    """One row per model x condition: the measured runs pooled over classes (n, mean and p90 cost, mean wall time)."""
    rows = []
    for (model, cond), classes in sorted(samples.items()):
        pooled = _pooled(classes)
        costs, walls = [c for c, _w in pooled], [w for _c, w in pooled]
        rows.append({"model": model, "condition": cond, "n": len(pooled), "mean_cost": _mean(costs),
                     "p90_cost": _p90(costs), "mean_wall_s": _mean(walls),
                     "from": pathlib.Path(source[(model, cond)]).name,
                     "per_class_n": {c: len(v) for c, v in sorted(classes.items())}})
    return rows


def _hours(s: float) -> str:
    return f"{s / 3600:.2f} h"


def budget_check(plan, result: dict) -> tuple[float, float, float, bool]:
    """(plan budget, expected total, sum of p90s, budget >= sum of p90s).

    There is no per-call cap: `budget_usd_total` is only the run-set guard (the runner never STARTS a run once
    the spent total reaches it and never cuts a running call). A budget below the expected total leaves the last runs
    of the plan (the late k) unstarted; `--per-call-usd X` on the runner is the only way to cap one call."""
    t = result["total"]
    budget = float(plan.header["budget_usd_total"])
    return budget, t["expected_cost"], t["sum_p90_cost"], budget >= t["sum_p90_cost"]


def report_lines(plan, result: dict, table: list[dict], overhead: float, detail: bool = False) -> list[str]:
    """The printed estimate: measured table, per-model estimate, budget check and warnings, as lines of text."""
    h = plan.header
    spec = h["spec"]
    lines = [f"plan {h['plan_id'][:16]}: split {spec['split']}, {h['n_runs']} runs, models {len(spec['models'])}, "
             f"conditions {','.join(spec['conditions'])}, efforts {','.join(spec['efforts'])}, k = {spec['k']}",
             "", "measured (model x condition: n runs, mean and p90 USD per run, mean wall s, source directory)"]
    for r in table:
        lines.append(f"  {r['model']:<20}{r['condition']:<3}n={r['n']:<3} mean={r['mean_cost']:.4f} "
                     f"p90={r['p90_cost']:.4f} "
                     f"wall={r['mean_wall_s'] or 0:.1f}s  {r['from']}  classes {r['per_class_n']}")
    lines += ["", "estimate for the plan (USD; wall time is serial)",
              f"  {'model':<20}{'runs':>5}{'expected':>10}{'p90 total':>11}{'sum p90s':>10}"
              f"{'wall exp':>10}{'wall p90':>10}"]
    for model, m in result["models"].items():
        lines.append(f"  {model:<20}{m['n_runs']:>5}{m['expected_cost']:>10.2f}{m['p90_cost']:>11.2f}"
                     f"{m['sum_p90_cost']:>10.2f}"
                     f"{_hours(m['expected_wall_s']):>10}{_hours(m['p90_wall_s']):>10}")
    t = result["total"]
    lines.append(f"  {'TOTAL':<20}{t['n_runs']:>5}{t['expected_cost']:>10.2f}{t['p90_cost']:>11.2f}"
                 f"{t['sum_p90_cost']:>10.2f}"
                 f"{_hours(t['expected_wall_s']):>10}{_hours(t['p90_wall_s']):>10}")
    lines += ["  expected = sum of class means x factor; p90 total = 90th percentile of the total over "
              f"{BOOTSTRAP_DRAWS} seeded resamples; sum p90s = every run billed at its own p90 "
              "(mean x model-x-condition tail ratio)",
              f"  factors: {CLASS_FACTOR} (only for classes with no measurement of their own); class mapping: "
              + ", ".join(f"{k}->{v}" for k, v in MEASURED_CLASS.items() if k != v),
              ""]
    budget, expected, sum_p90, ok = budget_check(plan, result)
    lines.append(f"plan budget USD {budget:g} is the run-set total only (per_call_cap: none; no run is started once "
                 f"it is spent, a running call is never cut): expected USD {expected:.2f}, sum p90s USD {sum_p90:.2f}"
                 + ("" if ok else "  WARNING budget < sum p90s: the last runs may not start; raise --budget-usd"))
    if detail:
        lines += ["", "class means used (plan class: n plan runs, n samples behind the mean, factor), "
                      "per model x condition"]
        for (model, cond, cls), d in sorted(result["detail"].items()):
            lines.append(f"  {model:<20}{cond:<3}{cls:<15}runs={d['n_plan_runs']:<4} n={d['n_samples']:<2} "
                         f"x{d['factor']:<4} "
                         f"mean={d['mean_cost']:.4f} wall={d['mean_wall_s']:.1f}s via {d['measured_class']}")
    lines += [""] + [f"WARNING {w}" for w in result["warnings"]]
    lines.append("WARNING small n per class and cell: see the n column"
                 + ("" if overhead == 1.0 else f"; overhead x{overhead} applied"))
    return lines


def main(argv: list[str] | None = None) -> int:
    """Entry point of `tsbench plan estimate`; returns the exit code."""
    ap = argparse.ArgumentParser(prog="tsbench plan estimate", description=__doc__.split("\n\n")[0])
    ap.add_argument("--plan", required=True)
    ap.add_argument("--from-runs", nargs="+", required=True, dest="from_runs",
                    help="runs directories with scores.csv; the last one wins per model x condition")
    ap.add_argument("--overhead", type=float, default=1.0)
    ap.add_argument("--detail", action="store_true",
                    help="also list the class mean behind every model x condition x class")
    ap.add_argument("--json", default=None, help="also write the numbers to this file")
    a = ap.parse_args(argv)
    try:
        plan = P.load_plan(a.plan)
    except P.PlanError as e:
        print(f"estimate: {e}", file=sys.stderr)
        return 2
    if not plan.runs:
        print("estimate: a sealed plan has no run records", file=sys.stderr)
        return 2
    samples, source = read_samples(a.from_runs)
    result = estimate(plan.runs, samples, overhead=a.overhead)
    table = pooled_table(samples, source)
    print("\n".join(report_lines(plan, result, table, a.overhead, a.detail)))
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps({"models": result["models"], "total": result["total"]}, indent=1),
            encoding="utf-8")
    return 0


if __name__ == "__main__":  # pragma: no cover - entry-point guard; the tests call main() directly
    raise SystemExit(main())
