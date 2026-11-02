"""The "diagram" task class: a whole octahedral Tanabe-Sugano diagram returned as data (plus an optional image).

Oracle: `tanabesugano.mcp._compute.compute_point` at Dq = x * B for every grid point x = 0, 0.5, ..., 4.0, at the
printed B and C. `compute_point` accepts Dq = 0 (checked for d3 to d7: the result equals the one at Dq = 1e-6 * B to
machine precision), so no substitute for Dq = 0 is used.

LEVEL CONVENTION (stated in the prompt, the oracle and `src/tsbench/data/tasks/rubric.md`): `compute_point` returns, for
every irreducible-representation term of the octahedral level scheme (5_E, 3_T_1, ...), a list of eigenvalues, one per
(free-ion parent term, term) pair. A *level* is one such eigenvalue: each is counted once, whatever its orbital
degeneracy (E = 2, T = 3), and levels of the same symmetry that come from different free-ion terms are separate levels.
The ground level is the lowest level at that Dq/B and is itself the first of the six, with E/B = 0; the other five
follow in ascending order. Levels that coincide are listed separately, so at Dq/B = 0, where the components of a
free-ion term coincide, a list can repeat a value (d6: 0, 0, 22, 22, 22, 22). Ties are broken by the label, so the
stored labels are deterministic; the scorer compares values only.
"""
from __future__ import annotations

import math

D_COUNTS = (3, 4, 5, 6, 7)
GRID = [0.5 * i for i in range(9)]   # Dq/B = 0, 0.5, ..., 4.0
N_LEVELS = 6
CB_RANGE = (4.0, 4.8)
# plausible Racah B (cm-1) of an octahedral dn ion; the same ranges as the curve class
B_RANGE = {3: (580, 900), 4: (550, 850), 5: (550, 900), 6: (500, 850), 7: (700, 950)}
MIN_B_DIFFERENCE = 0.05          # a confirmatory B differs from the pilot B of the same ion by at least this fraction
TOLERANCE = {"Dq": None, "B": None, "C": None, "curve_abs": 0.3, "curve_rel": 0.03, "item_accuracy_min": 0.95}

PROMPT = (
    "Compute the Tanabe–Sugano diagram of an octahedral {d} ion with B = {b} cm⁻¹ and C = {c} cm⁻¹. "
    "For each Dq/B in 0, 0.5, 1.0, …, 4.0 (9 points), give the energies E/B of the lowest 6 levels relative to the "
    "ground state (the ground state itself is 0), with their term labels. "
    "Count each term of the octahedral level scheme once, regardless of its orbital degeneracy (so ⁵T₂g and ⁵Eg are "
    "two levels, even where they coincide at Dq/B = 0, and terms of the same symmetry that come from different "
    "free-ion terms are separate levels); the ground state at each Dq/B is the lowest level at that Dq/B and is the "
    "first of the six. "
    "If you can, also save a plot of the diagram as diagram.png in the current directory and report its "
    "path and sha256."
)
NBSP = " "


def _compute():
    from tanabesugano.mcp import _compute  # imported late: optional dependency
    return _compute


def _label(key) -> str:
    """'3_T_1' -> '3T1g', '2_E' -> '2Eg' (informational)."""
    key = str(getattr(key, "value", key))
    mult, *rest = key.split("_")
    return mult + "".join(rest) + "g"


def levels_at(d: int, x: float, b: float, c: float, n: int | None = N_LEVELS) -> tuple[list[float], list[str]]:
    """(E/B, labels) of the lowest `n` levels (all if None) at Dq/B = x, ground level subtracted. E/B is rounded to 4
    decimals (-0.0 -> 0.0) BEFORE sorting by (E/B, label), so coincident levels (Dq = 0: one free-ion term) are ordered
    by label, not by last-bit eigenvalue noise that differs between BLAS builds."""
    pt = _compute().compute_point(d, x * b, b, c)
    raw = [(float(e), _label(k)) for k, vals in pt.items() for e in vals]
    g = min(e for e, _ in raw)
    out = sorted((round((e - g) / b, 4) + 0.0, lab) for e, lab in raw)[:n]
    return [e for e, _ in out], [lab for _, lab in out]


def reference(d: int, b: float, c: float) -> dict:
    grid, levels, labels = [], [], []
    for x in GRID:
        e, lab = levels_at(d, x, b, c)
        grid.append(x)
        levels.append(e)
        labels.append(lab)
    return {"grid": grid, "levels": levels, "labels": labels}


def _sup(d: int) -> str:
    return "d" + str(d).translate(str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹"))


def _num(x: float) -> str:
    return f"{int(round(x)):,}".replace(",", NBSP)


def _record(d: int, b: float, c: float, split: str) -> dict:
    return {
        "answer_schema": "diagram",
        "bands_cm1": [],
        "class": "diagram",
        "d_count": d,
        "expect_out_of_scope": False,
        "geometry": "Oh",
        "oracle": "forward_model",
        "params": {"B": b, "C": c, "dq_over_b": list(GRID), "n_levels": N_LEVELS},
        "prompt": PROMPT.format(d=_sup(d), b=_num(b), c=_num(c)),
        "reference": reference(d, b, c),
        "reference_curve": None,
        "required": [],
        "subtype": f"d{d}",
        "system": None,
        "tolerance": dict(TOLERANCE),
        "split": split,
    }


def _draw(rng, d: int, avoid: float | None) -> tuple[float, float]:
    while True:
        b = float(round(rng.uniform(*B_RANGE[d])))
        if avoid is not None and abs(b - avoid) / avoid < MIN_B_DIFFERENCE:
            continue
        c = float(round(rng.uniform(*CB_RANGE) * b))
        assert math.isfinite(b * c)
        return b, c


def make_diagram(rng) -> tuple[list[dict], list[dict]]:
    """(pilot, confirmatory): one task per d3..d7 in each; the confirmatory B differs from the pilot B of that ion."""
    pilot_p = {d: _draw(rng, d, None) for d in D_COUNTS}
    conf_p = {d: _draw(rng, d, pilot_p[d][0]) for d in D_COUNTS}
    pilot = [_record(d, *pilot_p[d], "pilot") for d in D_COUNTS]
    conf = [_record(d, *conf_p[d], "confirmatory") for d in D_COUNTS]
    return pilot, conf
