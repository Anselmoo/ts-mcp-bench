"""Scoring of the diagram task: nine Dq/B points x the lowest six levels (54 values) against `compute_point`.

Rule (rubric.md, "Correctness"): a value is correct within 3 % relative or 0.3 E/B
absolute; the task is `correct` iff item_accuracy (correct values / 54) >= 0.95, i.e. at most two wrong values. Grid
points are matched by `dq_over_b` (1e-6); a point that is missing or listed twice counts as six wrong values; the answer
levels of a point are sorted by energy and compared position by position with the reference (labels are never part of
the correctness; the share of matching labels is reported as `label_accuracy`, where the labels of a run of equal
reference levels count as a set: coincident levels have no defined order). Fewer than six levels: the missing ones
are wrong; more than six: the extra ones are ignored.
"""
from __future__ import annotations

import math
from collections import Counter

X_MATCH = 1e-6
ABS_TOL = 0.3
REL_TOL = 0.03
MIN_ACCURACY = 0.95
_EPS = 1e-12


def _num(v):
    if not isinstance(v, (int, float)) or isinstance(v, bool):
        return None
    try:
        out = float(v)
    except OverflowError:  # an integer of more than 308 digits
        return None
    return out if math.isfinite(out) else None


def _label(t) -> str:
    return str(t).strip().replace(" ", "").rstrip("'′″").lower().rstrip("g") if isinstance(t, str) else ""


def _levels(point) -> list[tuple[float | None, str]]:
    raw = point.get("levels") if isinstance(point, dict) else None
    out = ([(_num(lv.get("e_over_b")), _label(lv.get("term"))) for lv in raw if isinstance(lv, dict)]
           if isinstance(raw, list) else [])
    return sorted(out, key=lambda p: (p[0] is None, p[0] if p[0] is not None else 0.0))


def score_diagram(task: dict, structured_output) -> dict:
    ref = task["reference"]
    tol = task.get("tolerance") or {}
    abs_tol, rel_tol = tol.get("curve_abs", ABS_TOL), tol.get("curve_rel", REL_TOL)
    need = tol.get("item_accuracy_min", MIN_ACCURACY)
    out = structured_output if isinstance(structured_output, dict) else {}
    pts = out.get("points")
    pts = [p for p in pts if isinstance(p, dict)] if isinstance(pts, list) else []
    total = ok = lab_ok = n_cmp = 0
    sq = 0.0
    for x, want, want_lab in zip(ref["grid"], ref["levels"], ref["labels"], strict=False):
        total += len(want)
        px = [p for p in pts if _num(p.get("dq_over_b")) is not None and abs(_num(p["dq_over_b"]) - x) <= X_MATCH]
        got = _levels(px[0]) if len(px) == 1 else []
        have: dict[float, Counter] = {}  # reference level -> answer labels at its positions
        for i, w in enumerate(want):
            if i >= len(got) or got[i][0] is None:
                continue
            g, lab = got[i]
            err = abs(g - w)
            n_cmp += 1
            sq += err * err
            if err <= abs_tol + _EPS or (w != 0 and err / abs(w) <= rel_tol + _EPS):
                ok += 1
            if lab:
                have.setdefault(w, Counter())[lab] += 1
        for w, labs in have.items():  # equal reference levels: labels as a multiset
            lab_ok += sum((labs & Counter(_label(wl) for v, wl in zip(want, want_lab, strict=False)
                                          if v == w)).values())
    acc = ok / total if total else 0.0
    return {
        "item_accuracy": acc, "n_correct_items": ok,
        "rms_e_over_b": math.sqrt(sq / n_cmp) if n_cmp else float("nan"),
        "label_accuracy": lab_ok / total if total else 0.0,
        "correct": bool(total and acc >= need - _EPS),
    }
