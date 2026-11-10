"""Small rules that several report pages share, so that the pages cannot drift apart.

One home for: which runs are not evaluable (the rule of the scorer), the harness categories, the number and boolean
cells of `scores.csv`, the verdict of a task, the median, the share correct with its task-clustered bootstrap interval,
the run-set coercion,
the tasks and the `tasks.sha256` line of a split, the split a run set records, the guard of the confirmatory split and
the order and short name of the models.
The pages import these; none keeps a private copy (tests/report/test_base.py fails when one appears).

This module imports no other report module, so every page may import it.
"""
from __future__ import annotations

import json
import math
import pathlib
import re
import statistics
from collections.abc import Iterable
from types import SimpleNamespace

from tsbench import plan as plan_mod
from tsbench.core import intervals, resource
from tsbench.core.prereg import is_doi
from tsbench.score.run_sets import RunSet
from tsbench.score.score import not_evaluable_reason

__all__ = ["HARNESS", "MODEL_ORDER", "SPLITS", "as_bool", "as_number", "as_run_sets", "display_model", "is_claude",
           "is_true", "median", "median_of", "model_key", "not_evaluable", "pilot_hash", "run_split", "share",
           "solved", "split_hash", "split_refusal", "split_tasks"]

SPLITS = ("pilot", "confirmatory")  # the task splits a report reads; the pilot is the default

# failure categories of the taxonomy that the harness (not the model) caused: shown as "harness", not as "wrong"
HARNESS = frozenset({"no_result", "max_turns", "budget", "api_error"})
MODEL_ORDER = ["haiku", "sonnet", "opus"]  # the Claude models in this order on every page, then the others by id


def display_model(model: str) -> str:
    """`claude-haiku-5-5` -> `Haiku`; any other model id stays as it is."""
    m = re.match(r"^claude-([a-z]+)-", model or "")
    return m.group(1).capitalize() if m else (model or "?")


def is_claude(model: str) -> bool:
    return str(model).startswith("claude-")


def model_key(model: str):
    """The sort key of a model: the one order of the models on every page and in every figure."""
    short = display_model(model).lower()
    return (0, MODEL_ORDER.index(short), "") if short in MODEL_ORDER else (1, 0, model)


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


def solved(rows: list[dict]) -> bool:
    """The verdict of a task under one condition: more than half of its evaluable runs (`rows`) are correct."""
    return bool(rows) and sum(is_true(r.get("correct")) for r in rows) * 2 > len(rows)


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


def split_tasks(split: str = "pilot") -> dict:
    """The task records of one split by id; a record whose `split` field names another split is left out."""
    from tsbench.tasks import load
    return {t["id"]: t for t in load(split) if t.get("split", split) == split}


def split_hash(split: str = "pilot") -> str | None:
    """The sha256 of one split, from the task set's hash file (`<hash>  <split>` lines); None when the file has no
    line of that split."""
    for line in resource("tasks/tasks.sha256").read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if parts[-1:] == [split]:
            return parts[0]
    return None


def pilot_hash() -> str | None:
    """`split_hash("pilot")`."""
    return split_hash("pilot")


def run_split(runs: pathlib.Path, default: str) -> str:
    """confirmatory if the plan, a sealed header or the manifest says so, else `default`."""
    for name in (plan_mod.PLAN_NAME, plan_mod.SEALED_NAME):
        try:
            return json.loads((runs / name).read_text(encoding="utf-8").splitlines()[0])["spec"]["split"]
        except (OSError, ValueError, IndexError, KeyError, TypeError):
            continue
    try:
        return json.loads((runs / "MANIFEST.json").read_text(encoding="utf-8"))["split"]
    except (OSError, ValueError, KeyError, TypeError):
        return default


def split_refusal(run_sets: Iterable[RunSet | pathlib.Path | str], split: str, doi: str | None) -> str | None:
    """Why a page of `split` over the run sets is refused, or None: the confirmatory split (asked for, or recorded by
    a run set) needs a DOI in `--i-have-preregistered`, and every run set must record the split asked for (a run set
    that records none takes it)."""
    recorded = {rs.name: run_split(rs.path, split) for rs in as_run_sets(run_sets)}
    if "confirmatory" in (*recorded.values(), split) and not is_doi(doi):
        return "refusing to render the confirmatory split without --i-have-preregistered <DOI>"
    other = sorted(f"{name} ({s})" for name, s in recorded.items() if s != split)
    if other:
        found = sorted(set(recorded.values()) - {split})
        return (f"the run sets {', '.join(other)} were made on another split than {split}; "
                f"pass --split {' or '.join(found)}")
    return None
