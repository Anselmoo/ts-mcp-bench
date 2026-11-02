"""Descriptive metrics from scores.csv rows: per-class accuracy and consistency over k.

Definitions are in docs/methods.md (sections 5.5 and 5.6). Nothing here is a hypothesis test; the
hypothesis tests stay in ``hypotheses.py``. Rows may be CSV rows (all strings, '' for null) or the
typed rows of ``score.score_dir(...)["rows"]`` (bool, NaN, None), or a mix.

    from tsbench.stats.descriptive import per_class_accuracy, consistency
"""
from __future__ import annotations

import math
import statistics
from collections import defaultdict

from tsbench.stats.hypotheses import clopper_pearson

PER_CLASS_COLUMNS = ["model", "condition", "effort", "grouping", "group", "n", "n_correct", "accuracy", "ci_lo",
                     "ci_hi"]
CONSISTENCY_COLUMNS = ["model", "condition", "effort", "n_tasks", "n_unanimous", "unanimity_rate",
                       "mean_pairwise_agreement", "n_tasks_cv", "median_cv_dq"]

SYNTHETIC_CLASSES = ("closed_form", "numerical", "numerical_hard", "racah_c", "tetrahedral", "crossover", "curve",
                     "batch", "diagram")


def _bool(v):
    """True/False for bool-like values; None for None, '' or NaN."""
    if isinstance(v, str):
        s = v.strip().lower()
        return True if s in ("true", "1") else False if s in ("false", "0") else None
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    return bool(v)


def _float(v):
    """float(v); None for None, '' or NaN. inf stays inf."""
    if v is None or (isinstance(v, str) and not v.strip()):
        return None
    x = float(v)
    return None if math.isnan(x) else x


def _text(v) -> str:
    return "" if v is None or (isinstance(v, float) and math.isnan(v)) else str(v)


def _cell(row: dict) -> tuple[str, str, str]:
    return _text(row["model"]), _text(row["condition"]), _text(row["effort"])


def source_group(row: dict) -> str | None:
    """'literature' for experimental spectra, 'synthetic' for generated ones, None for the rest.

    Expected out-of-scope subtypes (charge_transfer, jahn_teller) belong to neither group.
    """
    cls = _text(row.get("class"))
    # literature_all: the bands are the table's published maxima
    if cls in ("experimental", "literature_all", "literature_new"):
        return "literature"
    if cls in SYNTHETIC_CLASSES:
        return "synthetic"
    return None


def per_class_accuracy(rows) -> list[dict]:
    """Per (model, condition, effort) cell: accuracy with a Clopper-Pearson CI by class and by source group."""
    counts: dict[tuple, list[int]] = defaultdict(lambda: [0, 0])
    for row in rows:
        ok = _bool(row["correct"]) is True
        groups = [("class", _text(row["class"]))]
        src = source_group(row)
        if src is not None:
            groups.append(("source", src))
        for grouping, group in groups:
            c = counts[(*_cell(row), grouping, group)]
            c[0] += 1
            c[1] += ok
    out = []
    for key in sorted(counts):
        n, k = counts[key]
        lo, hi = clopper_pearson(k, n)
        out.append(dict(zip(PER_CLASS_COLUMNS, (*key, n, k, k / n, lo, hi), strict=False)))
    return out


def _agreement(flags: list[bool]) -> float:
    """Fraction of unordered run pairs with equal correctness."""
    k, c = len(flags), sum(flags)
    return (math.comb(c, 2) + math.comb(k - c, 2)) / math.comb(k, 2)


def _coefficient_of_variation(dqs: list[float]) -> float | None:
    """Sample stdev over mean of |Dq|; None with fewer than two values or a non-positive mean."""
    v = [abs(x) for x in dqs if x is not None and math.isfinite(x)]
    if len(v) < 2 or statistics.fmean(v) <= 0:
        return None
    return statistics.stdev(v) / statistics.fmean(v)


def consistency(rows) -> list[dict]:
    """Per cell, over the tasks with k >= 2 runs: unanimity, pairwise agreement, median CV of the reported Dq."""
    cells: dict[tuple, dict[str, list[tuple[bool, float | None]]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        cells[_cell(row)][_text(row["task_id"])].append((_bool(row["correct"]) is True, _float(row.get("dq"))))
    out = []
    for cell in sorted(cells):
        tasks = [runs for runs in cells[cell].values() if len(runs) >= 2]
        flags = [[ok for ok, _ in runs] for runs in tasks]
        unanimous = sum(len(set(f)) == 1 for f in flags)
        cvs = [cv for cv in (_coefficient_of_variation([dq for _, dq in runs]) for runs in tasks) if cv is not None]
        n = len(tasks)
        out.append(dict(zip(CONSISTENCY_COLUMNS, (
            *cell, n, unanimous,
            unanimous / n if n else None,
            statistics.fmean(_agreement(f) for f in flags) if n else None,
            len(cvs), statistics.median(cvs) if cvs else None), strict=False)))
    return out
