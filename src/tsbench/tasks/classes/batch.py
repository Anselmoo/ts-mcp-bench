"""The "batch" task class: many independent calculations per task.

One calculation is within reach of a strong model by hand; errors and cost accumulate over eight. Two subtypes, each
with a reference computed by the tanabesugano forward model (``tanabesugano.mcp._compute``):

  * ``crossover_series``: Dq of the high-spin -> low-spin ground-state change for eight C/B values at fixed B.
    Oracle: ``crossover_dq(n, B, C, reference)`` where ``reference`` is the *strong-field* ground term (the ground
    term at STRONG_FIELD_DQ_CM1, exactly as the single-value crossover class does), never the weak-field one.
  * ``band_series``: energy of the lowest spin-allowed band for eight Dq values at fixed B and C. Oracle:
    ``transition_candidates(compute_point(n, Dq, B, C))``; the ground term is re-derived at every Dq, so for d4-d7
    the series can straddle the spin crossover. d5 is kept on the low-spin side (the high-spin d5 sextet has no
    spin-allowed band).

``make_batch(rng) -> (pilot, confirmatory)`` returns lists of records with the same keys as ``record(...)`` in
generate.py. Prompts name no tool and contain no results. This module prints nothing.
"""
from __future__ import annotations

from tsbench.tasks.common import group_thousands

CLS = "batch"
N_PILOT, N_CONF = 3, 4
N_VALUES = 8
TOLERANCE = {"Dq": None, "B": None, "C": None, "item_rel": 0.02}
NBSP = " "

B_RANGE = {2: (560, 780), 3: (580, 900), 4: (550, 850), 5: (550, 900), 6: (500, 850), 7: (700, 950), 8: (780, 990)}
DQ_RANGE_FIXED = {2: (1500, 2300), 3: (1200, 2300), 8: (750, 1250)}   # d2, d3, d8: no spin crossover
CB_GRID = [round(3.8 + 0.05 * i, 2) for i in range(25)]              # 3.80 ... 5.00
CROSSOVER_D = (4, 5, 6, 7)
BAND_D = (2, 3, 4, 5, 6, 7, 8)
CB_BAND = (4.0, 4.8)
CROSSOVER_TOL = 0.05
MIN_BAND_CM1 = 200.0          # reject draws whose answer is so small that 2 % is meaningless
CROSSOVER_GUARD = 0.03        # band Dq values keep this relative distance from the crossover


def _compute():
    from tanabesugano.mcp import _compute as comp  # late import: optional dependency
    return comp


def _strong_term(d: int, b: float, c: float):
    comp = _compute()
    return comp.ground_term(comp.compute_point(d, comp.STRONG_FIELD_DQ_CM1, b, c))[0]


# ----------------------------------------------------------------------------- oracles

def crossover_value(d: int, b: float, c: float) -> float | None:
    """Clean high->low spin crossover Dq at (B, C), or None if there is no clean one below the strong-field Dq."""
    comp = _compute()
    strong = _strong_term(d, b, c)
    weak = comp.reference_ground_term(d, b, c, "high")
    if weak == strong:
        return None
    x = comp.crossover_dq(d, b, c, strong, tol=CROSSOVER_TOL)
    if not (300 < x < comp.STRONG_FIELD_DQ_CM1 - 100):
        return None
    if comp.ground_term(comp.compute_point(d, 0.98 * x, b, c))[0] != weak \
            or comp.ground_term(comp.compute_point(d, 1.02 * x, b, c))[0] != strong:
        return None
    return float(x)


def first_allowed_band(d: int, dq: float, b: float, c: float) -> float | None:
    """Lowest spin-allowed transition energy from the ground term at this Dq, or None if there is none."""
    comp = _compute()
    _ground, cands = comp.transition_candidates(comp.compute_point(d, dq, b, c))
    return float(cands[0][0]) if cands else None


# ----------------------------------------------------------------------------- subtypes

def make_crossover_series(rng, d: int) -> dict:
    while True:
        b = float(round(rng.uniform(*B_RANGE[d])))
        ratios = sorted(float(r) for r in rng.choice(CB_GRID, size=N_VALUES, replace=False))
        xs = []
        ok = True
        for r in ratios:
            x = crossover_value(d, b, r * b)
            if x is None:
                ok = False
                break
            xs.append(x)
        if ok:
            break
    values = [{"input": r, "result": round(x, 2)} for r, x in zip(ratios, xs, strict=False)]
    listing = ", ".join(f"{r:.2f}" for r in ratios)
    templates = (
        "For an octahedral d{d} ion with the Racah parameter B = {b} cm⁻¹, find the ligand-field splitting Dq (in "
        "cm⁻¹) at which the ground state changes from high spin to low spin, for each of these C/B values: {lst}. "
        "Report the Dq for every C/B value, next to that value.",
        "An octahedral d{d} ion has B = {b} cm⁻¹. As Dq grows, its ground state changes from high spin to low spin. "
        "Give the Dq (in cm⁻¹) of this change for each of the following ratios C/B: {lst}. "
        "Give one result per C/B value, labelled by that value.",
    )
    prompt = templates[int(rng.integers(len(templates)))].format(d=d, b=group_thousands(b), lst=listing)
    return _record("crossover_series", d, prompt, values, {"B": b, "C_over_B": ratios})


def make_band_series(rng, d: int) -> dict:
    comp = _compute()
    while True:
        b = float(round(rng.uniform(*B_RANGE[d])))
        c = float(round(float(rng.uniform(*CB_BAND)) * b))
        if d in DQ_RANGE_FIXED:
            lo, hi = DQ_RANGE_FIXED[d]
            x = None
        else:
            x = crossover_value(d, b, c)
            if x is None:
                continue
            lo, hi = (1.05 * x if d == 5 else 0.5 * x), min(1.8 * x, comp.STRONG_FIELD_DQ_CM1 - 100)
        dqs: list[float] = []
        for _ in range(500):
            if len(dqs) == N_VALUES:
                break
            dq = float(round(rng.uniform(lo, hi) / 10.0) * 10)
            if x is not None and abs(dq - x) < CROSSOVER_GUARD * x:
                continue
            if any(abs(dq - e) < 0.04 * e for e in dqs):
                continue
            dqs.append(dq)
        if len(dqs) < N_VALUES:
            continue
        dqs.sort()
        bands = [first_allowed_band(d, dq, b, c) for dq in dqs]
        if any(e is None or e < MIN_BAND_CM1 for e in bands):
            continue
        break
    values = [{"input": dq, "result": round(e, 2)} for dq, e in zip(dqs, bands, strict=False)]
    listing = ", ".join(group_thousands(dq) for dq in dqs)
    templates = (
        "For an octahedral d{d} complex with B = {b} cm⁻¹ and C = {c} cm⁻¹, give the energy (in cm⁻¹) of the lowest "
        "spin-allowed d–d absorption band at each of these Dq values (in cm⁻¹): {lst}. "
        "Report one energy per Dq value, labelled by that Dq.",
        "Take an octahedral d{d} ion with B = {b} cm⁻¹ and C = {c} cm⁻¹. For each Dq in {lst} (cm⁻¹), what is the "
        "energy of its first spin-allowed absorption band, in cm⁻¹? Give one result per Dq value, labelled by it.",
    )
    prompt = templates[int(rng.integers(len(templates)))].format(
        d=d, b=group_thousands(b), c=group_thousands(c), lst=listing)
    return _record("band_series", d, prompt, values, {"B": b, "C": c})


def _record(subtype: str, d: int, prompt: str, values: list[dict], params: dict) -> dict:
    return {
        "answer_schema": "batch",
        "bands_cm1": [],
        "class": CLS,
        "d_count": d,
        "expect_out_of_scope": False,
        "geometry": "Oh",
        "oracle": "forward_model",
        "params": params,
        "prompt": prompt,
        "reference": {"values": values},
        "reference_curve": None,
        "required": ["values"],
        "subtype": subtype,
        "system": None,
        "tolerance": dict(TOLERANCE),
    }


def make_batch(rng) -> tuple[list[dict], list[dict]]:
    """(pilot, confirmatory) lists of batch records, deterministic in ``rng``."""
    plans = {
        "pilot": [("crossover_series", CROSSOVER_D), ("band_series", BAND_D), ("band_series", BAND_D)],
        "confirmatory": [("crossover_series", CROSSOVER_D), ("band_series", BAND_D),
                         ("crossover_series", CROSSOVER_D), ("band_series", BAND_D)],
    }
    out: dict[str, list[dict]] = {}
    for split, plan in plans.items():
        recs = []
        for subtype, ds in plan:
            d = int(ds[int(rng.integers(len(ds)))])
            recs.append(make_crossover_series(rng, d) if subtype == "crossover_series" else make_band_series(rng, d))
        out[split] = recs
    assert len(out["pilot"]) == N_PILOT and len(out["confirmatory"]) == N_CONF
    return out["pilot"], out["confirmatory"]
