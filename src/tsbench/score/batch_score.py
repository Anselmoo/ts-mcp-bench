"""Scoring for the "batch" task class (many calculations per task).

``score_batch(task, structured_output)`` matches the answered ``values`` entries to the reference entries by
``input`` (relative tolerance 1e-6), computes the per-item relative error of ``result`` and counts the items inside the
task tolerance (``task["tolerance"]["item_rel"]``, default 2 %). The task is correct iff every item is correct and
there are no missing or extra items. Missing items, null results, non-numeric results and extra entries count as wrong.
"""
from __future__ import annotations

import math
import statistics

from tsbench.score.numeric import _EPS

INPUT_RTOL = 1e-6
DEFAULT_ITEM_REL = 0.02


def _num(x) -> float | None:
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        return None
    try:
        out = float(x)
    except OverflowError:  # an integer of more than 308 digits
        return None
    return out if math.isfinite(out) else None


def _same_input(a: float, b: float) -> bool:
    return abs(a - b) <= INPUT_RTOL * max(abs(a), abs(b), 1e-300) if (a or b) else True


def _rel_error(got: float, ref: float) -> float:
    return abs(got - ref) / abs(ref) if ref != 0 else abs(got - ref)


def score_batch(task: dict, structured_output) -> dict:
    """Return n_items, n_correct_items, item_accuracy, median_rel_error (None if not finite), correct, n_missing,
    n_extra, items (per reference item: input, reference, result, rel_error, correct)."""
    tol = (task.get("tolerance") or {}).get("item_rel") or DEFAULT_ITEM_REL
    ref_values = task["reference"]["values"]
    answer = structured_output.get("values") if isinstance(structured_output, dict) else None
    entries = []
    for e in answer if isinstance(answer, list) else []:
        inp = _num(e.get("input")) if isinstance(e, dict) else None
        entries.append({"input": inp, "result": e.get("result") if isinstance(e, dict) else None})
    used = [False] * len(entries)

    items, errors = [], []
    for ref in ref_values:
        match = next((i for i, e in enumerate(entries)
                      if not used[i] and e["input"] is not None and _same_input(e["input"], float(ref["input"]))), None)
        if match is None:
            items.append({"input": ref["input"], "reference": ref["result"], "result": None, "rel_error": None,
                          "correct": False, "missing": True})
            errors.append(math.inf)
            continue
        used[match] = True
        got, want = entries[match]["result"], ref["result"]
        if want is None:
            ok, err = got is None, (0.0 if got is None else math.inf)
        else:
            g = _num(got)
            err = math.inf if g is None else _rel_error(g, float(want))
            ok = err <= tol + _EPS  # float slack, as in the other scorers
        items.append({"input": ref["input"], "reference": want, "result": got,
                      "rel_error": err if math.isfinite(err) else None, "correct": ok, "missing": False})
        errors.append(err)

    n_items = len(ref_values)
    n_correct = sum(it["correct"] for it in items)
    n_extra = used.count(False)
    median = statistics.median(errors) if errors else math.inf
    return {
        "n_items": n_items,
        "n_correct_items": n_correct,
        "item_accuracy": n_correct / n_items if n_items else 0.0,
        "median_rel_error": median if math.isfinite(median) else None,
        "n_missing": sum(it["missing"] for it in items),
        "n_extra": n_extra,
        "correct": bool(n_items) and n_correct == n_items and n_extra == 0,
        "items": items,
    }
