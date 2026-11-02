"""Small rules that several report pages share, so that the pages cannot drift apart.

One home for: which runs are not evaluable (the rule of the scorer), the harness categories, the number and boolean
cells of `scores.csv`, the median, the share correct with its task-clustered bootstrap interval, the run-set coercion
and the pilot line of `tasks.sha256`. The pages import these; none keeps a private copy (tests/report/test_base.py
fails when one appears).

This module imports no other report module, so every page may import it.
"""
from __future__ import annotations

import math
import pathlib
import statistics
from collections.abc import Iterable
from types import SimpleNamespace

from tsbench.core import intervals, resource
from tsbench.score.run_sets import RunSet
from tsbench.score.score import not_evaluable_reason

__all__ = ["HARNESS", "as_bool", "as_number", "as_run_sets", "is_true", "median", "median_of", "not_evaluable",
           "pilot_hash", "share"]

# failure categories of the taxonomy that the harness (not the model) caused: shown as "harness", not as "wrong"
HARNESS = frozenset({"no_result", "max_turns", "budget", "api_error"})


def not_evaluable(result: dict | None) -> str | None:
    """`rate_limited` or `api_error` for a result event the scorer leaves out of every rate (an HTTP 429 in any form, a
    5xx, `terminal_reason: api_error`, `API Error:` text); None for anything else. This is
    `tsbench.score.score.not_evaluable_reason`, called on a bare result event."""
    return not_evaluable_reason(SimpleNamespace(result=result))


def as_number(v) -> float | None:
    """A numeric cell of `scores.csv` as a float; None for an empty cell, text that is no number, and NaN."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) else f


def as_bool(v) -> bool | None:
    """A boolean cell of `scores.csv`: True for `True`, `true`, `TRUE`, `1`; False for the same spellings of false and
    `0`; None for anything else (an empty cell, a column the table does not have)."""
    s = str(v).strip().lower()
    return True if s in ("true", "1") else False if s in ("false", "0") else None


def is_true(v) -> bool:
    """`as_bool(v) is True`: an empty or unknown cell is not true."""
    return as_bool(v) is True


def median(values: Iterable[float | None]) -> float | None:
    """The median of the values that are not None; None when there are none."""
    got = [v for v in values if v is not None]
    return statistics.median(got) if got else None


def median_of(rows: Iterable[dict], key: str) -> float | None:
    """The median of the numeric cells `key` of the rows (empty and non-numeric cells are left out)."""
    return median(as_number(r.get(key)) for r in rows)


def share(rows: list[dict]) -> dict | None:
    """Correct runs over the given (evaluable) runs, with the 95 % interval of the task-clustered bootstrap
    (`core.intervals.cluster_bootstrap`): {k, n, tasks, p, lo, hi, ids}; None without runs. The runs of one task are not
    independent, so the interval resamples tasks. `p`, `lo` and `hi` are fractions."""
    if not rows:
        return None
    ids = sorted({str(r.get("task_id") or "") for r in rows})
    num = [sum(is_true(r.get("correct")) for r in rows if str(r.get("task_id") or "") == t) for t in ids]
    den = [sum(1 for r in rows if str(r.get("task_id") or "") == t) for t in ids]
    lo, hi = intervals.cluster_bootstrap(num, den)
    k, n = sum(num), sum(den)
    return {"k": k, "n": n, "tasks": len(ids), "p": k / n, "lo": lo, "hi": hi, "ids": ids}


def as_run_sets(items: Iterable[RunSet | pathlib.Path | str]) -> list[RunSet]:
    """RunSet objects as they are; a plain folder becomes a run set named after it."""
    return [it if isinstance(it, RunSet) else RunSet(pathlib.Path(it).name, pathlib.Path(it).name, pathlib.Path(it))
            for it in items]


def pilot_hash() -> str | None:
    """The sha256 of the pilot split, from the task set's hash file (`<hash>  <split>` lines); None when the file has
    no pilot line."""
    for line in resource("tasks/tasks.sha256").read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if parts[-1:] == ["pilot"]:
            return parts[0]
    return None
