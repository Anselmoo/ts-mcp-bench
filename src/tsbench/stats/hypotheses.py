"""Hypothesis tests (H1-H4) of the MCP benchmark. Reuses the primitives in ``analysis.py``.

Conditions: A = no tools, B = code interpreter (Bash), C = MCP.
A RateTable maps (model, condition, effort) -> {task_id: per-task success rate}.
Every comparison is paired by task id on the common tasks; a missing cell yields no row.
All differences read "second minus first" (e.g. C - B), so a positive value favours the second.

Primary (Holm over 4):  H2_<model> (C vs B, Wilcoxon on rates) for three models, and
  H3: Wilcoxon on the per-task DiD (Opus - Haiku)_B - (Opus - Haiku)_C; DiD > 0 means the
  size gap shrinks with MCP.
Secondary (no multiplicity correction): H1_<model> (C vs A), H4_<model> effort sweep
  (C_max - C_low) - (A_max - A_low), and exact McNemar on majorities for each H1/H2 pair.
Descriptive efficiency: per model, metric (tokens, thinking tokens, seconds, cost) and pair
  (C vs A, C vs B), the median per-task ratio C/base with a bootstrap CI and a Wilcoxon p on
  the log ratio, over all runs and over correct runs only. A model can be right without the
  MCP server and still pay for it in tokens or time; accuracy alone does not show that.

    tsbench stats hypotheses --rates <rates.csv> [--out <json>]
    tsbench stats hypotheses --scores <scores.csv> ... [--rates <rates.csv>] --expect-tasks 55 [--models <m1,m2,...>]
      [--out <json>]

Staged design: with --scores the tests use complete k layers only. Per family (primary: B and
C; H1: A and C; H4: the effort sweep) L is the largest layer such that every task x cell of the family has a run at
every layer 1..L (evaluable or not); the rates use the evaluable runs with k <= L. A family with L = 0 is not tested.
A run that leaves no test row at all (an empty family: wrong --models, --effort, --expect-tasks or --k-min) is an
error: a message on stderr and exit status 1, no output file.

--models lists the model ids of the family, default the three Claude ids in MODELS; H3 compares the last with the
first and needs two distinct models (with one model the primary family is H2 alone), H4 is run for the first and the
last. A primary family with a missing cell is an error naming the cells and pointing to --models.
"""
from __future__ import annotations

import argparse
import csv
import json
import pathlib
import platform
import sys

import numpy as np
import scipy
from scipy import stats

from tsbench.core.intervals import clopper_pearson  # noqa: F401  (re-exported)
from tsbench.stats.analysis import bootstrap_ci, holm, paired_majority, paired_rates

GRID = 9          # differences of per-task rates are rounded to this many decimals before any zero test or ranking
MODELS = ("claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5")
H4_MODELS = ("claude-haiku-5-5", "claude-opus-5-5")

RateTable = dict[tuple[str, str, str], dict[str, float]]


def load_rates(path) -> RateTable:
    """Read rates.csv (model, condition, effort, task_id, rate, k) into a RateTable."""
    table: RateTable = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            cell = table.setdefault((row["model"], row["condition"], row["effort"]), {})
            if row["task_id"] in cell:
                raise ValueError(f"duplicate row for {(row['model'], row['condition'], row['effort'], row['task_id'])}")
            cell[row["task_id"]] = float(row["rate"])
    return table


def _common(table: RateTable, *keys) -> tuple[list[str], list[np.ndarray]]:
    cells = [table.get(k, {}) for k in keys]
    ids = sorted(set.intersection(*(set(c) for c in cells)))
    return ids, [np.array([c[i] for i in ids], dtype=float) for c in cells]


def paired(table: RateTable, key_a, key_b) -> tuple[list[str], np.ndarray, np.ndarray]:
    """Task ids (sorted) common to both cells, with the aligned rate arrays; empty if a cell is missing."""
    ids, (a, b) = _common(table, key_a, key_b)
    return ids, a, b


def rank_biserial(a, b) -> float:
    """Matched-pairs rank-biserial r = (W+ - W-) / (W+ + W-) for d = b - a; zeros dropped, 0 if none left."""
    d = np.round(np.asarray(b, dtype=float) - np.asarray(a, dtype=float), GRID)
    d = d[d != 0]
    if d.size == 0:
        return 0.0
    ranks = stats.rankdata(np.abs(d))
    w_pos, w_neg = ranks[d > 0].sum(), ranks[d < 0].sum()
    return float((w_pos - w_neg) / (w_pos + w_neg))


def difference_in_differences(table: RateTable, a_hi, a_lo, b_hi, b_lo) -> tuple[list[str], np.ndarray]:
    """Per-task (a_hi - a_lo) - (b_hi - b_lo) over the tasks common to all four cells."""
    ids, (ah, al, bh, bl) = _common(table, a_hi, a_lo, b_hi, b_lo)
    return ids, np.round((ah - al) - (bh - bl), GRID)


def wilcoxon_zero(d) -> float:
    """Two-sided one-sample Wilcoxon p (Pratt zero handling); 1.0 if every difference is zero.
    Differences are rounded to a fixed grid first: rates are counts / k, and equal differences (k = 3, 5, ...) can
    differ in the last bit, which would decide the zeros and ties by rounding noise."""
    d = np.round(np.asarray(d, dtype=float), GRID)
    if d.size == 0 or np.all(d == 0):
        return 1.0
    return float(stats.wilcoxon(d, zero_method="pratt").pvalue)


def _row(name, n, p, a, b, **extra) -> dict:
    lo, hi = bootstrap_ci(a, b)
    return {"name": name, "n": n, "p": p, "mean_diff": float(np.mean(np.asarray(b) - np.asarray(a))),
            "ci": [lo, hi], "rank_biserial": rank_biserial(a, b), **extra}


def _paired_row(table, name, key_a, key_b) -> dict | None:
    ids, a, b = paired(table, key_a, key_b)
    return _row(name, len(ids), paired_rates(a, b), a, b) if ids else None


def primary(table: RateTable, models=MODELS, effort: str = "medium",
            allow_incomplete: bool = False, h3: bool = True) -> list[dict]:
    """Holm family: H2_<model> for each model and H3 (models[-1] vs models[0]).

    h3=False is the secondary family of the preregistration (plans 2a-2c): Holm over the H2 tests only, no H3, rows
    marked family "secondary_h2".

    The family size is fixed by the design, never by the data: a missing cell raises,
    or with allow_incomplete=True (pilot only) enters Holm as p = 1 and is marked missing.
    H3 is a contrast between two models: with fewer than two distinct models it is not part of the family
    (it would compare a model with itself, give p = 1 and inflate the Holm adjustment of the other tests).
    """
    models = tuple(dict.fromkeys(models))
    has_h3 = h3 and len(models) >= 2
    names = [f"H2_{m}" for m in models] + (["H3"] if has_h3 else [])
    found = {}
    for m in models:
        if r := _paired_row(table, f"H2_{m}", (m, "B", effort), (m, "C", effort)):
            found[r["name"]] = r
    lo, hi = models[0], models[-1]
    ids, d = difference_in_differences(table, (hi, "B", effort), (lo, "B", effort),
                                       (hi, "C", effort), (lo, "C", effort))
    if ids and has_h3:
        found["H3"] = _row("H3", len(ids), wilcoxon_zero(d), np.zeros_like(d), d)
    missing = [n for n in names if n not in found]
    if missing and not allow_incomplete:
        raise ValueError(f"primary family incomplete, missing: {missing}")
    rows = [found.get(n, {"name": n, "n": 0, "p": 1.0, "missing": True}) for n in names]
    for r, adj in zip(rows, holm([r["p"] for r in rows]), strict=False):
        r["p_holm"], r["family"] = adj, "primary" if h3 else "secondary_h2"
    return rows


def secondary(table: RateTable, models=MODELS, effort: str = "medium",
              h4_models=H4_MODELS, effort_hi: str = "max", effort_lo: str = "low") -> list[dict]:
    """H1 (C vs A), H4 effort sweep, and McNemar on majorities for each H1/H2 pair. Uncorrected."""
    rows = []
    for m in models:
        if r := _paired_row(table, f"H1_{m}", (m, "A", effort), (m, "C", effort)):
            rows.append(r)
    for m in h4_models:
        ids, d = difference_in_differences(table, (m, "C", effort_hi), (m, "C", effort_lo),
                                           (m, "A", effort_hi), (m, "A", effort_lo))
        if ids:
            rows.append(_row(f"H4_{m}", len(ids), wilcoxon_zero(d), np.zeros_like(d), d))
    for h, base in (("H2", "B"), ("H1", "A")):
        for m in models:
            ids, a, b = paired(table, (m, base, effort), (m, "C", effort))
            if ids:
                nb, nc, p = paired_majority(a, b)
                rows.append({"name": f"{h}_{m}_mcnemar", "n": len(ids), "p": p, "b": nb, "c": nc})
    for r in rows:
        r["family"] = "secondary"
    return rows


def median_abs_error_ci(values, n_boot=5000, alpha=0.05, seed=0) -> tuple[float, float, float]:
    """Median of |values| with a percentile bootstrap CI: (median, lo, hi)."""
    v = np.abs(np.asarray(values, dtype=float))
    if v.size == 0:
        return float("nan"), float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    meds = np.median(v[rng.integers(0, v.size, size=(n_boot, v.size))], axis=1)
    return float(np.median(v)), float(np.quantile(meds, alpha / 2)), float(np.quantile(meds, 1 - alpha / 2))


def cohen_kappa(labels_1, labels_2) -> float:
    """Cohen's kappa for two raters; 1.0 when chance agreement is already 1 (a single shared label)."""
    x, y = np.asarray(labels_1), np.asarray(labels_2)
    po = float(np.mean(x == y))
    pe = sum(float(np.mean(x == c)) * float(np.mean(y == c)) for c in np.union1d(x, y))
    return 1.0 if pe == 1.0 else (po - pe) / (1 - pe)


EFFICIENCY_METRICS = ("total_tokens", "output_tokens", "thinking_tokens", "duration_s", "cost_usd")


def load_metric(path, metric: str, correct_only: bool = False) -> RateTable:
    """Per-task mean of an efficiency metric from rates.csv (column mean_<metric>[_correct]).
    Cells without a value (no result, or no correct run for _correct) are left out."""
    col = f"mean_{metric}" + ("_correct" if correct_only else "")
    table: RateTable = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            v = row.get(col)
            if v not in (None, ""):
                table.setdefault((row["model"], row["condition"], row["effort"]), {})[row["task_id"]] = float(v)
    return table


def ratio_summary(a, b, n_boot: int = 5000, alpha: float = 0.05, seed: int = 0) -> dict | None:
    """Paired per-task ratio b/a on tasks where both are > 0: median ratio, bootstrap CI, Wilcoxon p on log b/a."""
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    keep = (a > 0) & (b > 0)
    if not keep.any():
        return None
    lr = np.log(b[keep] / a[keep])
    rng = np.random.default_rng(seed)
    meds = np.median(lr[rng.integers(0, lr.size, size=(n_boot, lr.size))], axis=1)
    return {"n": int(lr.size), "median_base": float(np.median(a[keep])), "median_other": float(np.median(b[keep])),
            "median_ratio": float(np.exp(np.median(lr))),
            "ratio_ci": [float(np.exp(np.quantile(meds, alpha / 2))), float(np.exp(np.quantile(meds, 1 - alpha / 2)))],
            "p": wilcoxon_zero(lr)}


def efficiency(rates_path, models=MODELS, effort: str = "medium", metrics=EFFICIENCY_METRICS,
               pairs=(("A", "C"), ("B", "C"))) -> list[dict]:
    """Descriptive rows EFF_<metric>_<other>vs<base>_<model>[_correct]; ratio < 1 means the other
    condition (C, MCP) used less. Missing columns or cells yield no row."""
    rows = []
    for metric in metrics:
        for correct_only in (False, True):
            table = load_metric(rates_path, metric, correct_only)
            for m in models:
                for base, other in pairs:
                    ids, a, b = paired(table, (m, base, effort), (m, other, effort))
                    summ = ratio_summary(a, b) if ids else None
                    if summ:
                        name = f"EFF_{metric}_{other}vs{base}_{m}" + ("_correct" if correct_only else "")
                        rows.append({"name": name, "metric": metric, "model": m, "base": base, "other": other,
                                     "correct_only": correct_only, **summ, "family": "descriptive"})
    return rows


# ------------------------------------------------------------------ staged design: complete k layers only
def load_score_rows(paths) -> list[dict]:
    """Rows of one or more scores.csv files: {model, condition, effort, task_id, k, evaluable, correct}.
    An evaluable run repeated in a later file (same model, condition, effort, task, k) is dropped, as
    figures.data.pooled_rows does, and the count goes to stderr: it would count twice in the rate of its task."""
    rows, seen, dups = [], set(), 0
    for path in paths:
        with open(path, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if str(r.get("evaluable", "True")).lower() in ("true", "1"):
                    key = (r["model"], r["condition"], r["effort"], r["task_id"], int(r["k_index"]))
                    if key in seen:
                        dups += 1
                        continue
                    seen.add(key)
                rows.append({"model": r["model"], "condition": r["condition"], "effort": r["effort"],
                             "task_id": r["task_id"], "k": int(r["k_index"]),
                             "evaluable": str(r.get("evaluable", "True")).lower() in ("true", "1"),
                             "correct": str(r.get("correct", "")).lower() in ("true", "1")})
    if dups:
        print(f"{dups} repeated evaluable run(s) of the same model, condition, effort, task and k dropped "
              "(first file wins)", file=sys.stderr)
    return rows


def complete_layers(rows: list[dict], cells, expect_tasks: int | None = None) -> int:
    """Largest L such that for every layer 1..L every task x cell has a run (evaluable or not). The tasks are those
    seen in any of the cells; with `expect_tasks`, fewer seen tasks than that means no complete layer (0)."""
    cells = list(cells)
    have = {(r["model"], r["condition"], r["effort"], r["task_id"], r["k"]) for r in rows}
    tasks = {r["task_id"] for r in rows if (r["model"], r["condition"], r["effort"]) in set(cells)}
    if not tasks or (expect_tasks is not None and len(tasks) < expect_tasks):
        return 0
    layer = 0
    while all((*cell, t, layer + 1) in have for cell in cells for t in tasks):
        layer += 1
    return layer


def rates_upto(rows: list[dict], cells, k_max: int) -> RateTable:
    """RateTable of the given cells from the evaluable runs with k <= k_max (rate = correct / evaluable, as rates.csv);
    a task with no evaluable run in a cell is left out of that cell."""
    want, acc = set(cells), {}
    for r in rows:
        cell = (r["model"], r["condition"], r["effort"])
        if cell in want and r["k"] <= k_max and r["evaluable"]:
            n = acc.setdefault(cell, {}).setdefault(r["task_id"], [0, 0])
            n[0] += r["correct"]
            n[1] += 1
    return {cell: {t: c / n for t, (c, n) in d.items()} for cell, d in acc.items()}


def layered(rows: list[dict], models=MODELS, effort: str = "medium", h4_models=H4_MODELS, effort_hi: str = "max",
            effort_lo: str = "low", expect_tasks: int | None = None, allow_incomplete: bool = False,
            k_min: int = 1, h3: bool = True) -> dict:
    """The tests on complete layers: each family on its own RateTable (primary: B, C; H1: A, C; H4: the sweep).
    Returns {"layers": {family: L}, "primary": [...], "secondary": [...]}. A family with fewer than `k_min` complete
    layers (confirmatory: 3) counts as L = 0 and yields no rows."""
    fam = {"primary": [(m, c, effort) for m in models for c in ("B", "C")],
           "h1": [(m, c, effort) for m in models for c in ("A", "C")],
           "h4": [(m, c, e) for m in h4_models for c in ("A", "C") for e in (effort_lo, effort_hi)]}
    layers = {f: complete_layers(rows, cells, expect_tasks) for f, cells in fam.items()}
    layers = {f: (L if L >= k_min else 0) for f, L in layers.items()}
    tab = {f: rates_upto(rows, cells, layers[f]) for f, cells in fam.items()}
    prim = (primary(tab["primary"], models, effort, allow_incomplete=allow_incomplete, h3=h3)
            if layers["primary"] else [])
    sec = [r for r in secondary(tab["primary"], models, effort, h4_models=()) if r["name"].startswith("H2_")]
    sec += [r for r in secondary(tab["h1"], models, effort, h4_models=()) if r["name"].startswith("H1_")]
    sec += [r for r in secondary(tab["h4"], (), effort, h4_models, effort_hi, effort_lo) if r["name"].startswith("H4_")]
    for r in prim:
        r["k_layers"] = layers["primary"]
    for r in sec:
        key = "h4" if r["name"].startswith("H4_") else "h1" if r["name"].startswith("H1_") else "primary"
        r["k_layers"] = layers[key]
    return {"layers": layers, "primary": prim, "secondary": sec}


def cost_per_correct(total_cost_usd: float, n_correct: int) -> float:
    return float("inf") if n_correct == 0 else total_cost_usd / n_correct


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rates",
                    help="rates.csv from the run harness (tests on all runs; with --scores: efficiency only)")
    ap.add_argument("--scores", nargs="+",
                    help="scores.csv files: tests on complete k layers only (staged design)")
    ap.add_argument("--expect-tasks", type=int, default=None, dest="expect_tasks",
                    help="with --scores: tasks a complete layer must cover (confirmatory: 55)")
    ap.add_argument("--k-min", type=int, default=1, dest="k_min",
                    help="with --scores: a family is tested only with at least this many complete layers "
                         "(confirmatory: 3)")
    ap.add_argument("--effort", default="medium")
    ap.add_argument("--models", default=",".join(MODELS),
                    help="comma-separated model ids of the family (default: the three Claude ids in MODELS); "
                         "H3 compares the last with the first, H4 uses the first and the last")
    ap.add_argument("--allow-incomplete", action="store_true",
                    help="pilot only: missing primary cells enter Holm as p = 1 instead of raising")
    ap.add_argument("--family", choices=("primary", "secondary"), default="primary",
                    help="primary: Holm over H2 of each model and H3; secondary (the open-weight plans 2a-2c): Holm "
                         "over the H2 tests only, no H3")
    ap.add_argument("--out", default="hypotheses.json", help="output JSON file (default: hypotheses.json)")
    a = ap.parse_args(argv)
    if not a.rates and not a.scores:
        ap.error("give --rates and/or --scores")
    models = tuple(dict.fromkeys(m.strip() for m in a.models.split(",") if m.strip()))
    if not models:
        ap.error("--models needs at least one model id")
    h4_models = tuple(dict.fromkeys((models[0], models[-1])))
    if a.scores:
        lay = layered(load_score_rows(a.scores), models, a.effort, h4_models, expect_tasks=a.expect_tasks,
                      allow_incomplete=a.allow_incomplete, k_min=a.k_min, h3=a.family == "primary")
        res = {"k_layers": lay["layers"], "primary": lay["primary"], "secondary": lay["secondary"],
               "efficiency": efficiency(a.rates, models, a.effort) if a.rates else []}
    else:
        table = load_rates(a.rates)
        try:
            prim = primary(table, models, a.effort, allow_incomplete=a.allow_incomplete, h3=a.family == "primary")
        except ValueError as exc:
            print(f"{exc}; check --models (now {', '.join(models)}) and --effort {a.effort}", file=sys.stderr)
            return 1
        res = {"primary": prim,
               "secondary": secondary(table, models, a.effort, h4_models),
               "efficiency": efficiency(a.rates, models, a.effort)}
    if not any(not r.get("missing") for r in res["primary"] + res["secondary"]):
        print(f"no test ran: no cell of models {', '.join(models)} at effort {a.effort} gives a complete family"
              + (f" (complete layers {res['k_layers']}; check --expect-tasks {a.expect_tasks} and --k-min {a.k_min})"
                 if a.scores else "") + "; nothing written", file=sys.stderr)
        return 1
    res["family"] = a.family
    # scipy's wilcoxon method selection depends on the version: record what the analysis ran with
    res["environment"] = {"python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__}
    for r in res["primary"] + res["secondary"] + res["efficiency"]:
        print(r)
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
