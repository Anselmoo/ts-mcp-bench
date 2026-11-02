"""The `racah_c` task class: how one task of the class is drawn (called by tsbench.tasks.generate)."""
from __future__ import annotations

from tsbench.tasks.common import (
    ROUNDING_SAFETY,
    TOL_SYNTHETIC,
    Stats,
    _close,
    _compute,
    _draw,
    _levels,
    group_thousands,
    invert,
    record,
    relative_error,
    round_to_10,
)


def make_racah_c(rng, seen, stats: Stats) -> dict:
    comp = _compute()
    key = "racah_c/d3"
    d = 3
    while True:
        dq, b, c = _draw(rng, "racah_c", d)
        if _close(dq, b, seen):
            stats.reject(key, "near-duplicate")
            continue
        allowed, forb = _levels(d, dq, b, c)
        if "2_E" not in forb[0][1]:
            stats.reject(key, "lowest doublet is not 2E")
            continue
        e2 = round_to_10(forb[0][0])
        bands3 = [round_to_10(x) for x in allowed[:3]]
        x = invert(d, bands3, c, (dq, b, c), with_c=True, observed_forbidden=[e2])
        if (relative_error(x[0], dq) > ROUNDING_SAFETY * TOL_SYNTHETIC["Dq"]
                or relative_error(x[1], b) > ROUNDING_SAFETY * TOL_SYNTHETIC["B"]
                or relative_error(x[2], c) > ROUNDING_SAFETY * TOL_SYNTHETIC["C"]):
            stats.reject(key, "rounding moves answer")
            continue
        # Diagnostic only: can the package recover C from these four bands?
        diag = {"fit_error": None}
        try:
            fit = comp.fit_spectrum(d, sorted(bands3 + [e2]), None, spin_state="high", include_spin_forbidden=True)
            diag.update(dq_ok=relative_error(fit.Dq, dq) <= TOL_SYNTHETIC["Dq"],
                        b_ok=relative_error(fit.B, b) <= TOL_SYNTHETIC["B"],
                        c_ok=relative_error(fit.C, c) <= TOL_SYNTHETIC["C"], c_constrained=bool(fit.c_constrained),
                        c_is_default=bool(fit.c_is_default))
        except ValueError as exc:
            diag.update(fit_error=str(exc)[:80], dq_ok=False, b_ok=False, c_ok=False, c_constrained=False,
                        c_is_default=True)
        stats.racah_c_fit.append(diag)
        seen.append((dq, b))
        stats.accept(key)
        bands = sorted(bands3 + [e2])
        prompt = (
            f"An octahedral d3 complex shows three broad, spin-allowed d–d absorption bands at "
            f"{group_thousands(bands3[0])}, {group_thousands(bands3[1])} and {group_thousands(bands3[2])} cm⁻¹ and, "
            f"in addition, a weak, sharp absorption band at "
            f"{group_thousands(e2)} cm⁻¹. The weak, sharp band is the lowest-energy spin-forbidden transition. "
            "Determine the ligand-field splitting parameter Dq, the Racah parameter B and the Racah parameter C "
            "(all in cm⁻¹)."
        )
        return record(
            cls="racah_c", subtype="d3", d_count=3, geometry="Oh", system=None, bands=bands, prompt=prompt,
            required=["Dq", "B", "C"], reference={"Dq": dq, "B": b, "C": c}, oracle="forward_model",
        ), (dq, b, c)
