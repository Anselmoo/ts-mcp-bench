"""The `tetrahedral` task class: how one task of the class is drawn (called by tsbench.tasks.generate)."""
from __future__ import annotations

from tsbench.tasks.common import (
    ROUNDING_SAFETY,
    TOL_SYNTHETIC,
    Stats,
    _close,
    _draw,
    allowed_bands,
    group_thousands,
    invert,
    record,
    relative_error,
    round_to_10,
)


def make_tetrahedral(rng, d: int, seen, stats: Stats):
    """Td d^n is treated as Oh d^(10-n) with the same |Dq| (hole formalism)."""
    key = f"tetrahedral/d{d}"
    dh = 10 - d
    while True:
        dq, b, c = _draw(rng, "tetrahedral", d)
        if _close(dq, b, seen):
            stats.reject(key, "near-duplicate")
            continue
        bands = [round_to_10(x) for x in allowed_bands(dh, dq, b, c)]
        x = invert(dh, bands, c, (dq, b))
        if (relative_error(x[0], dq) > ROUNDING_SAFETY * TOL_SYNTHETIC["Dq"]
                or relative_error(x[1], b) > ROUNDING_SAFETY * TOL_SYNTHETIC["B"]):
            stats.reject(key, "rounding moves answer")
            continue
        seen.append((dq, b))
        stats.accept(key)
        ion = {7: "Co(II)", 8: "Ni(II)"}[d]
        prompt = (f"A tetrahedral {ion} (d{d}) complex shows three spin-allowed d–d absorption bands at "
                  f"{group_thousands(bands[0])}, "
                  f"{group_thousands(bands[1])} and {group_thousands(bands[2])} cm⁻¹. "
                  "Determine the ligand-field splitting parameter Dq and the Racah parameter B (in cm⁻¹).")
        return record(cls="tetrahedral", subtype=f"d{d}", d_count=d, geometry="Td", system=None, bands=bands,
                      prompt=prompt, required=["Dq", "B"], reference={"Dq": dq, "B": b, "C": None},
                      oracle="forward_model"), (dq, b, c)
