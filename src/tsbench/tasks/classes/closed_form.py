"""The `closed_form` task class: how one task of the class is drawn (called by tsbench.tasks.generate)."""
from __future__ import annotations

import math

from tsbench.tasks.common import (
    ROUNDING_SAFETY,
    TOL_SYNTHETIC,
    Stats,
    _close,
    _draw,
    allowed_bands,
    prompt_allowed,
    record,
    relative_error,
    round_to_10,
)
from tsbench.tasks.oracles.closed_form import dq_b


def make_closed_form(rng, d: int, seen, stats: Stats) -> dict:
    key = f"closed_form/d{d}"
    while True:
        dq, b, c = _draw(rng, "closed_form", d)
        if _close(dq, b, seen):
            stats.reject(key, "near-duplicate")
            continue
        raw = allowed_bands(d, dq, b, c)
        cf0 = dq_b(*raw)
        assert abs(cf0.dq_from_quadratic - dq) < 0.5 and abs(cf0.b_from_quadratic - b) < 0.5, (d, dq, b, cf0)
        bands = [round_to_10(x) for x in raw]
        try:
            cf = dq_b(*bands)
        except ValueError:
            stats.reject(key, "rounded bands inconsistent")
            continue
        if math.isnan(cf.dq_from_quadratic):
            stats.reject(key, "rounded bands inconsistent")
            continue
        if (relative_error(cf.dq_from_quadratic, dq) > ROUNDING_SAFETY * TOL_SYNTHETIC["Dq"]
                or relative_error(cf.b_from_quadratic, b) > ROUNDING_SAFETY * TOL_SYNTHETIC["B"]
                or relative_error(cf.dq_from_nu1, cf.dq_from_quadratic) > ROUNDING_SAFETY * TOL_SYNTHETIC["Dq"]):
            stats.reject(key, "rounding moves answer")
            continue
        seen.append((dq, b))
        stats.accept(key)
        return record(
            cls="closed_form", subtype=f"d{d}", d_count=d, geometry="Oh", system=None, bands=bands,
            prompt=prompt_allowed(rng, d, bands), required=["Dq", "B"],
            reference={"Dq": cf.dq_from_quadratic, "B": cf.b_from_quadratic, "C": None}, oracle="closed_form",
        ), (dq, b, c)
