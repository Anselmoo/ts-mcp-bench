"""Correctness of one answer against one task (docs/methods.md, section 2) and the traced-number metric."""
from __future__ import annotations

import math
import re
from collections.abc import Hashable

from tsbench.score.extract import NUMBER, Transcript

__all__ = ["CURVE_ABS", "CURVE_REL", "CURVE_X_MATCH", "TRACE_RTOL", "numbers_in", "score", "score_curve", "trace"]

NAN = float("nan")
PARAMS = ("Dq", "B", "C")
_EPS = 1e-12  # float slack so an answer exactly on the tolerance boundary is accepted
# a thousands-grouped number ("2,033.6"). It never starts inside a number, after a "[" or after a ",", so the
# elements of a compact JSON list ("[1850,761,3402]", "[-47.46,109.47]") stay separate numbers
_GROUPED = re.compile(r"(?<![\d.,\[])\d{1,3}(?:,\d{3})+(?!\d|,\d)")
TRACE_RTOL = 0.005
# curve tasks: all nine E/B values within CURVE_REL relative or CURVE_ABS absolute; points matched by Dq/B
CURVE_REL = 0.03
CURVE_ABS = 0.3
CURVE_X_MATCH = 0.01


def _errors(task: dict, answer: dict) -> dict:
    """abs/rel error per parameter; NaN where answer or reference is null. Td Dq is compared by absolute value."""
    out = {}
    for p in PARAMS:
        a, ref = answer.get(p), (task.get("reference") or {}).get(p)
        if a is None or ref is None:
            out[p] = (NAN, NAN)
            continue
        if p == "Dq" and task.get("geometry") == "Td":
            a, ref = abs(a), abs(ref)
        abs_err = abs(a - ref)
        out[p] = (abs_err, abs_err / abs(ref) if ref != 0 else (0.0 if abs_err == 0 else math.inf))
    return out


def _blank_row(unparseable: bool) -> dict:
    row = {"correct": False, "unparseable": unparseable, "answer_out_of_scope": None, "curve_max_rel_err": NAN,
           "curve_tol_ratio": NAN}
    for p in PARAMS:
        row[p.lower()] = None
        row[f"abs_err_{p.lower()}"] = NAN
        row[f"rel_err_{p.lower()}"] = NAN
    return row


def _in_units(err: float, tol: float) -> float:
    """`err` in units of the tolerance `tol`: 0 for no error, infinite for an error against a tolerance of 0."""
    return 0.0 if err <= 0 else err / tol if tol > 0 else math.inf


def score_curve(task: dict, answer: dict | None) -> dict:
    """Correctness of a `curve` answer (rubric.md): the answer points are grouped by the task's Dq/B values
    (|difference| <= CURVE_X_MATCH), each group must hold exactly three points and the answer exactly as many points
    as the reference, each group is sorted by e_over_b and compared with the reference in ascending order; term
    labels are not scored. Correct iff every value is within CURVE_ABS absolute or CURVE_REL relative.
    `curve_max_rel_err` is the largest relative error (NaN if the answer is malformed or mismatched).
    `curve_tol_ratio` is the pass criterion as a number: the largest over the points of the error in units of the
    nearer of the two tolerances, so the answer is correct iff it is at most 1 (NaN as `curve_max_rel_err`)."""
    row = _blank_row(answer is None)
    if answer is None:
        return row
    tol = task.get("tolerance") or {}
    rel_tol, abs_tol = tol.get("curve_rel", CURVE_REL), tol.get("curve_abs", CURVE_ABS)
    ref_pts = task.get("reference_curve") or []
    pts = answer.get("points")
    if not ref_pts or not isinstance(pts, list) or len(pts) != len(ref_pts):
        return row
    worst, ok, ratio = 0.0, True, 0.0
    for x in dict.fromkeys(p["dq_over_b"] for p in ref_pts):
        want = sorted(p["e_over_b"] for p in ref_pts if p["dq_over_b"] == x)
        got = sorted(p["e_over_b"] for p in pts if abs(p["dq_over_b"] - x) <= CURVE_X_MATCH)
        if len(got) != len(want):
            return row
        for g, w in zip(got, want, strict=False):
            err = abs(g - w)
            rel = err / abs(w) if w != 0 else (0.0 if err == 0 else math.inf)
            worst = max(worst, rel)
            ratio = max(ratio, min(_in_units(err, abs_tol), _in_units(rel, rel_tol)))
            ok = ok and (err <= abs_tol + _EPS or (w != 0 and err / abs(w) <= rel_tol + _EPS))
    row["curve_max_rel_err"] = worst
    row["curve_tol_ratio"] = ratio
    row["correct"] = ok
    return row


def score(task: dict, answer: dict | None) -> dict:
    """Correctness record. `unparseable` (answer None) is always incorrect."""
    row = _blank_row(answer is None)
    if answer is None:
        return row

    oos = answer.get("out_of_scope")
    row["answer_out_of_scope"] = oos if isinstance(oos, bool) else None
    for p in PARAMS:
        row[p.lower()] = answer.get(p)
    for p, (abs_err, rel_err) in _errors(task, answer).items():
        row[f"abs_err_{p.lower()}"], row[f"rel_err_{p.lower()}"] = abs_err, rel_err

    if task.get("expect_out_of_scope"):
        row["correct"] = oos is True and answer.get("Dq") is None and answer.get("B") is None
        return row

    if oos is not False:  # True, or anything that is not a real boolean
        return row
    errs = _errors(task, answer)
    tol = task.get("tolerance") or {}
    ok = True
    for p in task.get("required") or []:
        rel = errs[p][1]
        ok = ok and not math.isnan(rel) and p in tol and tol[p] is not None and rel <= tol[p] + _EPS
    row["correct"] = ok
    return row


def numbers_in(text: str) -> list[float]:
    """Every finite number in `text` as an absolute value. The one scanner of the traced-number metric and of the
    solution path."""
    text = _GROUPED.sub(lambda m: m.group().replace(",", ""), text)
    vals = []
    for m in NUMBER.findall(text):
        try:
            v = float(m)
        # the pattern only matches text that float() accepts, so this guard cannot be reached
        except ValueError:  # pragma: no cover
            continue
        if math.isfinite(v):
            vals.append(abs(v))
    return vals


def trace(answer: dict | None, transcript: Transcript | None) -> tuple[int, int]:
    """(n_reported, n_traced): non-null Dq/B/C in the answer, and how many match a number (|.|, 0.5 % relative)
    appearing in some tool_result text. n_reported - n_traced counts numbers with no tool provenance."""
    if answer is None:
        return 0, 0
    pool: list[float] = []
    skip = {u.get("id") for u in (transcript.tool_uses if transcript else [])
            if u.get("name") == "StructuredOutput" and isinstance(u.get("id"), Hashable)}
    for tr in (transcript.tool_results if transcript else []):
        tid = tr.get("tool_use_id")
        if isinstance(tid, Hashable) and tid in skip:  # the answer channel is not a source of numbers
            continue
        pool.extend(numbers_in(tr.get("content") or ""))
    reported = traced = 0
    for p in PARAMS:
        v = answer.get(p)
        if v is None:
            continue
        reported += 1
        v = abs(v)
        if any(abs(x - v) <= TRACE_RTOL * v for x in pool):
            traced += 1
    return reported, traced
