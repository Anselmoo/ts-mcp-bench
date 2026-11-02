"""Scope confusion and failure taxonomy over scored runs (docs/methods.md, sections 5.2 and 5.3).

Both functions work on scores.csv rows, either as csv.DictReader gives them (strings, '' for null) or as typed by
score.score_dir (bool, NaN, None). The task records (from tsbench.tasks.load) supply `required`, `tolerance` and
`expect_out_of_scope`, which scores.csv does not carry.
"""
from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Mapping

from tsbench.core.intervals import clopper_pearson

__all__ = ["CATEGORIES", "GROSS_REL_ERR", "FAILURE_COLUMNS", "SCOPE_COLUMNS", "failure_category",
           "failure_table", "scope_confusion"]

CATEGORIES = ("correct", "no_result", "max_turns", "budget", "context_overflow", "api_error", "unparseable",
              "false_refusal", "missed_limit", "gross_error", "wrong_dq", "wrong_b", "wrong_c", "wrong_multiple",
              "wrong_items")
GROSS_REL_ERR = 0.5
RETRIES_SUBTYPE = "error_max_structured_output_retries"
_EPS = 1e-12  # same slack as numeric._EPS: an error exactly on the tolerance is not off
FAILURE_COLUMNS = ["model", "condition", "effort", "category", "n", "share"]
SCOPE_COLUMNS = ["model", "condition", "effort", "n_expected_oos", "n_in_scope", "true_limit", "missed_limit",
                 "false_refusal", "correct_scope", "no_scope_answer",
                 "limit_naming_rate", "limit_naming_ci_lo", "limit_naming_ci_hi",
                 "false_refusal_rate", "false_refusal_ci_lo", "false_refusal_ci_hi"]
_PAIRING_SCORES = ("node_precision", "node_recall", "edge_precision", "edge_recall")
_PARAM_CATEGORY = {"Dq": "wrong_dq", "B": "wrong_b", "C": "wrong_c"}


def _float(v):
    if v is None or v == "":
        return None
    v = float(v)
    return None if math.isnan(v) else v


def _bool(v):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    s = str(v).strip().lower()
    if s in ("true", "1"):
        return True
    if s in ("false", "0"):
        return False
    return None


def _parameter_off(row: dict, task: dict, p: str) -> bool:
    """A required parameter is off when its relative error is missing or beyond its tolerance."""
    rel = _float(row.get(f"rel_err_{p.lower()}"))
    tol = (task.get("tolerance") or {}).get(p)
    return rel is None or tol is None or rel > tol + _EPS


def failure_category(row: dict, task: dict) -> str:
    """Exactly one of CATEGORIES for one scored row; the first matching rule wins (docs/methods.md section 5.3)."""
    if _bool(row.get("correct")):
        return "correct"
    # A rescued answer (the last valid StructuredOutput call of a run stopped by a limit) is judged by its content like
    # any answer: the limit is recorded in `rescue_stop_reason`, and it opens no path to "correct".
    rescued = bool(_bool(row.get("rescued")))
    if not rescued:
        if not _bool(row.get("has_result")):
            return "no_result"
        subtype = row.get("result_subtype")
        if subtype == "error_max_turns":
            return "max_turns"
        if subtype == "error_max_budget_usd":
            return "budget"
        if subtype == RETRIES_SUBTYPE:  # the CLI gave up on schema-invalid answers: a format failure of the model
            return "unparseable"
        if _bool(row.get("context_overflow")):  # the request outgrew the context window: the model's failure
            return "context_overflow"
        if _bool(row.get("is_error")):
            return "api_error"
    if _bool(row.get("unparseable")):
        return "unparseable"
    if task.get("answer_schema") == "curve":  # curve answers: no Dq/B, no scope flag
        err = _float(row.get("curve_max_rel_err"))
        if err is None:  # malformed or mismatched points: no error to measure
            return "unparseable"
        return "gross_error" if err > GROSS_REL_ERR else "wrong_items"
    if task.get("answer_schema") == "batch":  # no Dq/B and no scope flag in this answer
        # the scorer writes no median when it is infinite (half or more of the items missing or null): that is gross
        err = _float(row.get("median_rel_error"))
        return "gross_error" if err is None or err > GROSS_REL_ERR else "wrong_items"
    if task.get("answer_schema") == "pairing":  # no median error here: gross when a precision or recall is below half
        found = [v for v in (_float(row.get(c)) for c in _PAIRING_SCORES) if v is not None]
        return "gross_error" if any(v < 1 - GROSS_REL_ERR for v in found) else "wrong_items"
    if task.get("answer_schema") == "diagram":  # 54 values: gross if fewer than half of them are right
        acc = _float(row.get("item_accuracy"))
        return "gross_error" if acc is not None and acc < 1 - GROSS_REL_ERR else "wrong_items"
    oos = _bool(row.get("answer_out_of_scope"))
    if task.get("expect_out_of_scope"):
        return "missed_limit"
    if oos is True:
        return "false_refusal"
    required = task.get("required") or []
    for p in required:
        rel = _float(row.get(f"rel_err_{p.lower()}"))
        if rel is not None and rel > GROSS_REL_ERR:
            return "gross_error"
    off = [p for p in required if _parameter_off(row, task, p)]
    if len(off) == 1:
        return _PARAM_CATEGORY[off[0]]
    if not off:  # incorrect with nothing off: the out_of_scope flag was not a boolean, a format failure
        return "unparseable"
    return "wrong_multiple"


def _cells(rows, tasks: Mapping[str, dict]) -> dict:
    cells: dict = defaultdict(list)
    for r in rows:
        task = tasks.get(r.get("task_id"))
        if task is not None:
            cells[(str(r["model"]), str(r["condition"]), str(r["effort"]))].append((r, task))
    return cells


def failure_table(rows, tasks: Mapping[str, dict]) -> list[dict]:
    """One row per (cell, category), zero counts included, so the counts of a cell sum to its rows."""
    out = []
    for key, items in sorted(_cells(rows, tasks).items()):
        counts = dict.fromkeys(CATEGORIES, 0)
        for r, task in items:
            counts[failure_category(r, task)] += 1
        for cat in CATEGORIES:
            out.append({"model": key[0], "condition": key[1], "effort": key[2], "category": cat,
                        "n": counts[cat], "share": counts[cat] / len(items)})
    return out


def _rate(k: int, n: int) -> tuple:
    if n == 0:
        return None, None, None
    lo, hi = clopper_pearson(k, n)
    return k / n, lo, hi


def scope_confusion(rows, tasks: Mapping[str, dict]) -> list[dict]:
    """Per cell: does the model name the limits of the model (true_limit), and does it refuse solvable tasks."""
    out = []
    for key, items in sorted(_cells(rows, tasks).items()):
        n_oos = n_in = true_limit = missed = refusal = in_ok = none = 0
        for r, task in items:
            if task.get("answer_schema", "fit") != "fit":  # no scope flag in a curve, batch or pairing answer
                continue
            expected, oos = bool(task.get("expect_out_of_scope")), _bool(r.get("answer_out_of_scope"))
            n_oos, n_in = n_oos + expected, n_in + (not expected)
            if oos is None:
                none += 1
            elif expected:
                true_limit, missed = true_limit + oos, missed + (not oos)
            else:
                refusal, in_ok = refusal + oos, in_ok + (not oos)
        ln, fr = _rate(true_limit, n_oos), _rate(refusal, n_in)
        out.append(dict(zip(SCOPE_COLUMNS, [*key, n_oos, n_in, true_limit, missed, refusal, true_limit + in_ok,
                                            none, *ln, *fr], strict=False)))
    return out
