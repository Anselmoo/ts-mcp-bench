"""The `crossover` task class: how one task of the class is drawn (called by tsbench.tasks.generate)."""
from __future__ import annotations

from tsbench.tasks.common import (
    B_RANGE,
    CB_RANGE_CROSSOVER,
    Stats,
    _close,
    _compute,
    ground_sequence,
    group_thousands,
    record,
)


def make_crossover(rng, d: int, seen, stats: Stats):
    comp = _compute()
    key = f"crossover/d{d}"
    while True:
        b = float(round(rng.uniform(*B_RANGE[d])))
        c = float(round(rng.uniform(*CB_RANGE_CROSSOVER) * b))
        if _close(b, c, seen):
            stats.reject(key, "near-duplicate")
            continue
        weak = comp.reference_ground_term(d, b, c, "high")
        strong = comp.ground_term(comp.compute_point(d, comp.STRONG_FIELD_DQ_CM1, b, c))[0]
        if weak == strong:
            stats.reject(key, "no spin crossover")
            continue
        seq = ground_sequence(d, b, c)
        if len(seq) != 2:
            stats.reject(key, "more than one ground-term change")
            continue
        x = comp.crossover_dq(d, b, c, strong, tol=0.05)
        if not (300 < x < 5900) or comp.ground_term(comp.compute_point(d, 0.98 * x, b, c))[0] != weak \
                or comp.ground_term(comp.compute_point(d, 1.02 * x, b, c))[0] != strong:
            stats.reject(key, "crossover not clean")
            continue
        seen.append((b, c))
        stats.accept(key)
        t = ("At B = {b} cm⁻¹ and C = {c} cm⁻¹, at which value of Dq does the ground state of an octahedral d{d} ion "
             "change from high spin to low spin? Give Dq in cm⁻¹.",
             "An octahedral d{d} ion has the Racah parameters B = {b} cm⁻¹ and C = {c} cm⁻¹. As the ligand-field "
             "splitting grows, its ground state changes from high spin to low spin. At which Dq (in "
             "cm⁻¹) does this happen?"
             )[int(rng.integers(2))]
        prompt = t.format(d=d, b=group_thousands(b), c=group_thousands(c))
        return record(
            cls="crossover", subtype=f"d{d}", d_count=d, geometry="Oh", system=None, bands=[], prompt=prompt,
            required=["Dq"], reference={"Dq": x, "B": None, "C": None}, oracle="forward_model",
            params={"B": b, "C": c},
        )
