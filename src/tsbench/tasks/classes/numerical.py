"""The `numerical` task class: how one task of the class is drawn (called by tsbench.tasks.generate)."""
from __future__ import annotations

from tsbench.tasks.common import (
    HIGH_SPIN_MARGIN,
    ROUNDING_SAFETY,
    TOL_SYNTHETIC,
    Stats,
    _close,
    _compute,
    _draw,
    allowed_bands,
    invert,
    prompt_allowed,
    record,
    relative_error,
    round_to_10,
)


def make_numerical(rng, d: int, seen, stats: Stats) -> dict:
    comp = _compute()
    key = f"numerical/d{d}"
    while True:
        dq, b, c = _draw(rng, "numerical", d)
        if _close(dq, b, seen):
            stats.reject(key, "near-duplicate")
            continue
        if d == 7:
            strong = comp.ground_term(comp.compute_point(7, comp.STRONG_FIELD_DQ_CM1, b, c))[0]
            if comp.ground_term(comp.compute_point(7, dq, b, c))[0] == strong or \
                    dq > (1 - HIGH_SPIN_MARGIN) * comp.crossover_dq(7, b, c, strong):
                stats.reject(key, "not high-spin with margin")
                continue
        bands = [round_to_10(x) for x in allowed_bands(d, dq, b, c)]
        try:
            fit = comp.fit_spectrum(d, bands, C=c, spin_state="high")
        except ValueError:
            stats.reject(key, "fit_spectrum failed")
            continue
        if relative_error(fit.Dq, dq) > TOL_SYNTHETIC["Dq"] or relative_error(fit.B, b) > TOL_SYNTHETIC["B"]:
            stats.reject(key, "fit_spectrum does not recover")
            continue
        x = invert(d, bands, c, (dq, b))
        if (relative_error(x[0], dq) > ROUNDING_SAFETY * TOL_SYNTHETIC["Dq"]
                or relative_error(x[1], b) > ROUNDING_SAFETY * TOL_SYNTHETIC["B"]):
            stats.reject(key, "rounding moves answer")
            continue
        seen.append((dq, b))
        stats.accept(key)
        return record(
            cls="numerical", subtype=f"d{d}", d_count=d, geometry="Oh", system=None, bands=bands,
            prompt=prompt_allowed(rng, d, bands), required=["Dq", "B"],
            reference={"Dq": dq, "B": b, "C": None}, oracle="forward_model",
        ), (dq, b, c)
