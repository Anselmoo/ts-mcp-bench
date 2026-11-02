"""The `curve` task class: how one task of the class is drawn (called by tsbench.tasks.generate)."""
from __future__ import annotations

from tsbench.tasks.common import (
    B_RANGE,
    CB_RANGE,
    TOL_CURVE,
    Stats,
    _close,
    _compute,
    excited_levels,
    group_thousands,
    record,
)

# curve
CURVE_DQ_B_WINDOWS = ((0.8, 1.6), (1.8, 2.8), (3.0, 4.0))   # one Dq/B drawn per window, in steps of 0.05


CURVE_X_TO_CROSSOVER = 0.15    # Dq/B at least this far from the ground-state crossover


CURVE_MIN_E1 = 1.0             # E/B of the lowest excited level, at least


CURVE_GAP_34 = 0.4             # E/B between the third and the fourth level, at least


def make_curve(rng, d: int, seen, stats: Stats):
    comp = _compute()
    key = f"curve/d{d}"
    while True:
        b = float(round(rng.uniform(*B_RANGE[d])))
        c = float(round(rng.uniform(*CB_RANGE) * b))
        if _close(b, c, seen):
            stats.reject(key, "near-duplicate")
            continue
        xs = [round(float(rng.uniform(lo, hi)) / 0.05) * 0.05 for lo, hi in CURVE_DQ_B_WINDOWS]
        xs = [round(x, 2) for x in xs]
        if d >= 4:
            strong = comp.ground_term(comp.compute_point(d, comp.STRONG_FIELD_DQ_CM1, b, c))[0]
            x_c = comp.crossover_dq(d, b, c, strong, tol=0.05) / b
            if any(abs(x - x_c) < CURVE_X_TO_CROSSOVER for x in xs):
                stats.reject(key, "Dq/B too close to the spin crossover")
                continue
        pts, ok = [], True
        for x in xs:
            lv = excited_levels(d, x * b, b, c)
            if lv[0][0] < CURVE_MIN_E1 or lv[3][0] - lv[2][0] < CURVE_GAP_34:
                ok = False
                break
            pts += [{"dq_over_b": x, "term": lab, "e_over_b": round(e, 4)} for e, lab in lv[:3]]
        if not ok:
            stats.reject(key, "lowest three levels not well separated")
            continue
        seen.append((b, c))
        stats.accept(key)
        t = ("An octahedral d{d} ion has the Racah parameters B = {b} cm⁻¹ and C = {c} cm⁻¹. On its energy-level "
             "diagram, what is E/B, the energy above the ground term in units of B, of the three lowest excited terms "
             "(spin-allowed or spin-forbidden) at Dq/B = {x1}, {x2} and {x3}? Report nine points: for each Dq/B, the "
             "three terms in order of increasing energy, each with its term label and its E/B.",
             "For an octahedral d{d} ion with B = {b} cm⁻¹ and C = {c} cm⁻¹, give the energies E/B (relative to the "
             "ground term, in units of B) of the three lowest excited terms, whatever their spin multiplicity, at "
             "Dq/B = {x1}, {x2} and {x3}. Answer with nine points: for each Dq/B the three terms in ascending "
             "energy, each with its label and E/B.")[int(rng.integers(2))]
        prompt = t.format(d=d, b=group_thousands(b), c=group_thousands(c),
                          x1=f"{xs[0]:.2f}", x2=f"{xs[1]:.2f}", x3=f"{xs[2]:.2f}")
        return record(
            cls="curve", subtype=f"d{d}", d_count=d, geometry="Oh", system=None, bands=[], prompt=prompt,
            required=[], reference={}, oracle="forward_model", params={"B": b, "C": c, "dq_over_b": xs},
            reference_curve=pts, tolerance=TOL_CURVE,
        )
