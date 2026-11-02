"""Closed-form ligand-field parameters for octahedral d3 and d8, written independently of
the tanabesugano package (which uses its own closed form as a fit seed; validating the
package against that code would be circular).

For d3 (4A2g ground) and d8 (3A2g ground) the three spin-allowed bands are
    nu1 = 10 Dq                                  (T2, no configuration interaction)
    nu2 + nu3 = 15 B + 30 Dq                     (trace of the 2x2 T1 block)
    340 Dq^2 - 18 (nu2 + nu3) Dq + nu2 nu3 = 0   (determinant; Underhill-Billing form)
Three bands, two parameters: the system is over-determined, and the disagreement between
Dq from nu1 and Dq from the quadratic is a measured consistency check, not a tuning knob.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class ClosedForm:
    dq_from_nu1: float
    dq_from_quadratic: float
    b_from_nu1: float
    b_from_quadratic: float
    dq_disagreement: float  # dq_from_quadratic - dq_from_nu1, cm-1


def dq_b(nu1: float, nu2: float, nu3: float) -> ClosedForm:
    if not 0 < nu1 < nu2 < nu3:
        raise ValueError(f"need 0 < nu1 < nu2 < nu3, got {nu1}, {nu2}, {nu3}")
    s, p = nu2 + nu3, nu2 * nu3
    disc = (18 * s) ** 2 - 4 * 340 * p
    dq1 = nu1 / 10
    if disc < 0:
        # The bands are mutually inconsistent with the two-parameter model: no (Dq, B)
        # reproduces nu2 and nu3 exactly. Reported, not repaired.
        nan = float("nan")
        return ClosedForm(dq1, nan, (s - 30 * dq1) / 15, nan, nan)
    roots = sorted([((18 * s) - math.sqrt(disc)) / 680, ((18 * s) + math.sqrt(disc)) / 680])
    # physical root: the one whose B is positive and closest to the nu1 estimate
    candidates = [r for r in roots if (s - 30 * r) / 15 > 0]
    if not candidates:  # pragma: no cover  (unreachable: the smaller root is at most 18 s / 680 < s / 30, so B > 0)
        raise ValueError("no root gives positive B")
    dq_q = min(candidates, key=lambda r: abs(r - dq1))
    return ClosedForm(
        dq_from_nu1=dq1,
        dq_from_quadratic=dq_q,
        b_from_nu1=(s - 30 * dq1) / 15,
        b_from_quadratic=(s - 30 * dq_q) / 15,
        dq_disagreement=dq_q - dq1,
    )


def dq_b_two_band(nu1: float, nu2: float) -> tuple[float, float]:
    """Dq and B of octahedral d3 / d8 from the two lowest spin-allowed bands (nu1, nu2).

    Same Underhill-Billing relations as `dq_b`, with nu3 eliminated:
        nu1 = 10 Dq                                   ->  Dq = nu1 / 10
        nu2 + nu3 = 15 B + 30 Dq =: s                 ->  nu3 = s - nu2
        340 Dq^2 - 18 s Dq + nu2 nu3 = 0              ->  340 Dq^2 - 18 s Dq + nu2 (s - nu2) = 0
    Solving the last line for s:
        s = (nu2^2 - 340 Dq^2) / (nu2 - 18 Dq)
    With Dq = nu1 / 10 this is s = (nu2^2 - 3.4 nu1^2) / (nu2 - 1.8 nu1), and
        B = (s - 30 Dq) / 15 = (nu2 - nu1)(nu2 - 2 nu1) / (3 (5 nu2 - 9 nu1)).
    Two bands, two parameters: the system is exactly determined, so unlike `dq_b` there is
    no consistency check between nu1 and the quadratic. nu2 must be the lower of the two
    T1 bands; for real spectra the formula is only as good as the assignment of nu2.
    """
    if not 0 < nu1 < nu2:
        raise ValueError(f"need 0 < nu1 < nu2, got {nu1}, {nu2}")
    denom = 3 * (5 * nu2 - 9 * nu1)
    if denom == 0:
        raise ValueError("nu2 = 1.8 nu1: B undefined")
    b = (nu2 - nu1) * (nu2 - 2 * nu1) / denom
    if b <= 0:
        raise ValueError(f"nu2/nu1 = {nu2 / nu1:.3f}: no positive B")
    return nu1 / 10, b
