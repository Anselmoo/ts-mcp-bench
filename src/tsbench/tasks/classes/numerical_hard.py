"""The `numerical_hard` task class: how one task of the class is drawn (called by tsbench.tasks.generate)."""
from __future__ import annotations

import numpy as np
from scipy.optimize import least_squares

from tsbench.tasks.common import (
    B_RANGE,
    CB_RANGE,
    FREE_ION_B,
    GROUND_TERM_LABEL,
    ROUNDING_SAFETY,
    TOL_SYNTHETIC,
    Stats,
    _close,
    _compute,
    group_thousands,
    record,
    relative_error,
    round_to_10,
)

# numerical_hard
HARD_NEAR = (1.02, 1.10)       # Dq / crossover Dq, "near the spin crossover" (low-spin side: see rubric)


HARD_LOW = (1.25, 1.80)        # Dq / crossover Dq, clearly low-spin


HARD_MIN_SPACING = 250.0       # cm-1 between the three bands


HARD_RESIDUAL = 25.0           # cm-1: a fit this close to the printed bands counts as reproducing them


def _hard_residuals(d: int, ratio: float, obs, dq: float, b: float):
    """Three lowest spin-allowed bands from the ground term at (dq, b, C = ratio * b), minus the observed bands."""
    comp = _compute()
    try:
        _, cands = comp.transition_candidates(comp.compute_point(d, dq, b, ratio * b))
    except Exception:  # noqa: BLE001 - an unphysical corner of the search space is a bad fit, not an error
        return np.full(3, 1e5)
    es = [e for e, _a, _s in cands]
    if len(es) < 3:
        return np.full(3, 1e5)
    return np.array(es[:3]) - np.asarray(obs, dtype=float)


def _hard_fit(d: int, ratio: float, obs, x0):
    sol = least_squares(lambda x: _hard_residuals(d, ratio, obs, x[0], x[1]), np.array(x0, dtype=float),
                        x_scale=np.array([1000.0, 1000.0]), bounds=([100.0, 200.0], [6000.0, 1500.0]), method="trf")
    return sol.x, float(np.max(np.abs(sol.fun)))


def hard_solutions(d: int, ratio: float, bands, *, n_start: int = 12) -> list[tuple[float, float, float]]:
    """All distinct (Dq, B, max residual) with max residual <= HARD_RESIDUAL that a multi-start fit of the three
    printed bands finds anywhere in Dq 400-4800, B 400-1100 (both spin regimes), with C = ratio * B.

    Starts: the local minima of a 45 x 29 grid of the sum of squared residuals (lowest n_start of them).
    """
    dqs, bs = np.linspace(400.0, 4800.0, 45), np.linspace(400.0, 1100.0, 29)
    rss = np.array([[float(np.sum(_hard_residuals(d, ratio, bands, q, b) ** 2)) for b in bs] for q in dqs])
    starts = []
    for i in range(len(dqs)):
        for j in range(len(bs)):
            nb = rss[max(i - 1, 0): i + 2, max(j - 1, 0): j + 2]
            if rss[i, j] <= nb.min():
                starts.append((rss[i, j], dqs[i], bs[j]))
    starts.sort()
    found: list[tuple[float, float, float]] = []
    for _r, q0, b0 in starts[:n_start]:
        x, worst = _hard_fit(d, ratio, bands, (q0, b0))
        if worst <= HARD_RESIDUAL and not any(abs(x[0] - f[0]) / f[0] < 0.005 and abs(x[1] - f[1]) / f[1] < 0.005
                                              for f in found):
            found.append((float(x[0]), float(x[1]), worst))
    return found


def hard_ambiguous(d: int, ratio: float, bands, dq: float, b: float) -> list[tuple[float, float, float]]:
    """The solutions of `hard_solutions` that lie outside half the tolerance of the generating (dq, b), plus
    the one fit started at (dq, b) if it does. Empty = the printed bands identify (Dq, B)."""
    sols = hard_solutions(d, ratio, bands)
    x, worst = _hard_fit(d, ratio, bands, (dq, b))
    sols.append((float(x[0]), float(x[1]), worst))
    return [s for s in sols if s[2] <= HARD_RESIDUAL
            and (relative_error(s[0], dq) > ROUNDING_SAFETY * TOL_SYNTHETIC["Dq"]
                 or relative_error(s[1], b) > ROUNDING_SAFETY * TOL_SYNTHETIC["B"])]


def make_hard(rng, d: int, mode: str, seen, stats: Stats):
    """Octahedral d4/d5/d6, three lowest spin-allowed bands from the actual ground term, C/B stated.

    mode "crossover": Dq within 2-10 % above the spin-crossover Dq. Below it the high-spin ground term has one
    spin-allowed band (d4, d6) or none (d5), which cannot determine B, so every such draw would be rejected anyway.
    mode "low_spin": Dq 1.25-1.8 times the crossover Dq.
    """
    comp = _compute()
    key = f"numerical_hard/d{d}/{mode}"
    lo, hi = HARD_NEAR if mode == "crossover" else HARD_LOW
    while True:
        b = float(round(rng.uniform(*B_RANGE[d])))
        ratio = round(float(rng.uniform(*CB_RANGE)), 1)
        c = ratio * b
        assert b < FREE_ION_B[d], (d, b)
        strong = comp.ground_term(comp.compute_point(d, comp.STRONG_FIELD_DQ_CM1, b, c))[0]
        x = comp.crossover_dq(d, b, c, strong, tol=0.05)
        if x >= comp.STRONG_FIELD_DQ_CM1 - 1:
            stats.reject(key, "no spin crossover below the strong-field Dq")
            continue
        dq = float(round(x * rng.uniform(lo, hi)))
        if _close(dq, b, seen):
            stats.reject(key, "near-duplicate")
            continue
        if comp.ground_term(comp.compute_point(d, dq, b, c))[0] != strong:
            stats.reject(key, "not low-spin")
            continue
        _, cands = comp.transition_candidates(comp.compute_point(d, dq, b, c))
        es = [e for e, _a, _s in cands]
        if len(es) < 3 or min(np.diff(es[:3])) < HARD_MIN_SPACING:
            stats.reject(key, "bands too close together")
            continue
        bands = [round_to_10(e) for e in es[:3]]
        if len(set(bands)) < 3:
            stats.reject(key, "bands too close together")
            continue
        x_fit, _w = _hard_fit(d, ratio, bands, (dq, b))
        if (relative_error(x_fit[0], dq) > ROUNDING_SAFETY * TOL_SYNTHETIC["Dq"]
                or relative_error(x_fit[1], b) > ROUNDING_SAFETY * TOL_SYNTHETIC["B"]):
            stats.reject(key, "rounding moves answer")
            continue
        if hard_ambiguous(d, ratio, bands, dq, b):
            stats.reject(key, "bands do not identify (Dq, B)")
            continue
        seen.append((dq, b))
        stats.accept(key)
        t = ("An octahedral d{d} complex shows its three lowest-energy spin-allowed d–d absorption bands at {a}, {b} "
             "and {c} cm⁻¹. Take C/B = {r}. {spin} Determine the ligand-field splitting parameter Dq and the Racah "
             "parameter B (in cm⁻¹).",
             "The three lowest-energy spin-allowed ligand-field (d–d) bands of an octahedral d{d} metal complex have "
             "their maxima at {a}, {b} and {c} cm⁻¹. Assume C/B = {r}. {spin} What are the ligand-field splitting "
             "parameter Dq and the Racah parameter B, both in cm⁻¹?")[int(rng.integers(2))]
        # Spin state and ground term at the drawn Dq (oracle: the ground term of the forward model). Every draw is
        # low-spin (checked above: its ground term is that of the strong-field limit).
        ground = GROUND_TERM_LABEL[str(getattr(strong, "value", strong))]
        spin = f"The complex is low-spin; its ground term is {ground}."
        prompt = t.format(d=d, a=group_thousands(bands[0]), b=group_thousands(bands[1]), c=group_thousands(bands[2]),
                          r=f"{ratio:.1f}", spin=spin)
        return record(
            cls="numerical_hard", subtype=f"d{d}_{mode}", d_count=d, geometry="Oh", system=None, bands=bands,
            prompt=prompt, required=["Dq", "B"], reference={"Dq": dq, "B": b, "C": None}, oracle="forward_model",
            params={"c_over_b": ratio, "mode": mode},
        )
