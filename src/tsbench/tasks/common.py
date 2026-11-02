"""Shared pieces of the task generator: tolerances, parameter ranges, the forward model, the record builder."""
from __future__ import annotations

import math
from collections import Counter

import numpy as np
from scipy.optimize import least_squares

# The fixed pilot systems (drawn with seed 20261024). They are kept by name and never become confirmatory.
FIXED_PILOT_SYSTEMS = ("Al2O3:Cr3+", "MgO:Ni2+")


# The class order is fixed: `rng_for` uses the index in this tuple, so a class appended at the end leaves the stream
# and the records of every class before it unchanged (tests/tasks/test_tasks.py checks this).
BASE_CLASSES = ("closed_form", "experimental", "numerical", "numerical_hard", "racah_c", "tetrahedral",
                "out_of_scope", "crossover", "curve")


EXTRA_CLASSES = ("literature_all", "batch", "pairing")


# Appended to the END of the file (after every record of both splits, pilot then confirmatory): see `assemble`.
TAIL_CLASSES = ("diagram", "literature_new")


CLASSES = BASE_CLASSES + EXTRA_CLASSES + TAIL_CLASSES


# (pilot, confirmatory) tasks per class; closed_form, batch and pairing are pilot-only classes
COUNTS = {"closed_form": (2, 0), "experimental": (2, 0), "numerical": (3, 6), "numerical_hard": (3, 6),
          "racah_c": (3, 5), "tetrahedral": (3, 3), "out_of_scope": (3, 4), "crossover": (3, 4), "curve": (3, 4),
          # literature_all: 33 table systems minus 3 excluded for a fit at a bound, one third (per d-count) to the
          # pilot, minus 2 confirmatory systems that a pilot task of another class uses (no confirmatory system is a
          # pilot system or appears twice); build_tasks asserts the number. experimental: every usable row is a pilot
          # or a confirmatory literature_all system, so it has no confirmatory tasks.
          "literature_all": (10, 18), "batch": (3, 0), "pairing": (1, 0), "diagram": (5, 5),
          # pilot-only class from data/literature/literature-spectra-2.csv: 8 systems minus 2 excluded (fit at the C/B
          # bound)
          "literature_new": (6, 0)}


# drawn like every class (own stream, pilot first), then left out of the confirmatory split
CONF_DROPPED = ("closed_form", "batch", "pairing")


N_PILOT = sum(p for p, _ in COUNTS.values())


N_CONF = sum(c for _, c in COUNTS.values())


ANSWER_SCHEMA_OF = {cls: ("curve" if cls == "curve" else cls if cls in ("batch", "pairing", "diagram") else "fit")
                    for cls in CLASSES}


def _fixed_pilot_systems() -> set:
    return set(FIXED_PILOT_SYSTEMS)


def _overlap_with_fixed_pilot(conf_experimental: list[dict]) -> dict:
    """How many confirmatory experimental systems are fixed pilot systems."""
    return {"checked": True, "fixed_pilot_systems": len(FIXED_PILOT_SYSTEMS),
            "confirmatory_in_fixed_pilot": sum(r["system"] in FIXED_PILOT_SYSTEMS for r in conf_experimental)}


TOL_SYNTHETIC = {"Dq": 0.02, "B": 0.05, "C": 0.10}


TOL_EXPERIMENTAL = {"Dq": 0.05, "B": 0.10, "C": None}


TOL_CURVE = {"Dq": None, "B": None, "C": None, "curve_abs": 0.3, "curve_rel": 0.03}


# A synthetic task is kept only if the answer recovered from the *rounded* bands lies within this
# fraction of the tolerance, so that rounding cannot decide whether an exact answer is accepted.
ROUNDING_SAFETY = 0.5


# Free-ion Racah B (cm-1), used only to keep drawn B below the free-ion value.
FREE_ION_B = {2: 861.0, 3: 1030.0, 4: 1150.0, 5: 1130.0, 6: 1060.0, 7: 1115.0, 8: 1041.0}


# (Dq range, B range) in cm-1; C/B is drawn from 4.0-4.8 everywhere except in the crossover class.
RANGES = {
    ("closed_form", 3): ((1200, 2300), (560, 900)),
    ("closed_form", 8): ((750, 1250), (780, 990)),
    ("numerical", 2): ((1550, 2250), (560, 780)),
    ("numerical", 7): ((850, 1150), (800, 950)),
    ("racah_c", 3): ((1300, 2300), (580, 900)),
    ("tetrahedral", 7): ((300, 500), (700, 880)),   # Td d7, Co(II); Dq is the Td magnitude
    ("tetrahedral", 8): ((300, 500), (750, 950)),   # Td d8, Ni(II)
}


B_RANGE = {3: (580, 900), 4: (550, 850), 5: (550, 900), 6: (500, 850), 7: (700, 950)}  # hard, crossover, curve


CB_RANGE = (4.0, 4.8)


CB_RANGE_CROSSOVER = (3.8, 5.0)   # deliberately wider than the textbook 4.0-4.5


HIGH_SPIN_MARGIN = 0.15      # d7: Dq at least 15 % below the spin crossover


NEAR_DUPLICATE = (0.03, 0.04)  # draws closer than this in (Dq, B) count as the same draw


NBSP = " "


def _compute():
    from tanabesugano.mcp import _compute  # imported late: optional dependency
    return _compute


def round_to_10(x: float) -> float:
    return float(math.floor(x / 10.0 + 0.5) * 10)


def group_thousands(x: float) -> str:
    """Thousands grouped with a no-break space, as in '8 510'."""
    return f"{int(round(x)):,}".replace(",", NBSP)


def _levels(d: int, dq: float, b: float, c: float):
    comp = _compute()
    _, cands = comp.transition_candidates(comp.compute_point(d, dq, b, c), spin_allowed_only=False)
    allowed = [e for e, _a, s in cands if s]
    forbidden = [(e, a) for e, a, s in cands if not s]
    return allowed, forbidden


def allowed_bands(d: int, dq: float, b: float, c: float) -> list[float]:
    allowed, _ = _levels(d, dq, b, c)
    assert len(allowed) == 3, (d, len(allowed))
    return allowed


def invert(d: int, observed_allowed, c: float, x0, *, with_c: bool = False, observed_forbidden=None):
    """Least-squares (Dq, B[, C]) from rounded bands, started at the generating values.

    Answers whether the rounded bands still point at the generating parameters. The start at the
    truth is deliberate: the question is the shift caused by rounding, not global identifiability.
    """
    obs = list(observed_allowed) + (list(observed_forbidden) if with_c else [])

    def resid(x):
        cc = x[2] if with_c else c
        allowed, forb = _levels(d, x[0], x[1], cc)
        pred = allowed[:3] + ([forb[0][0]] if with_c else [])
        return np.array(pred) - np.array(obs)

    x0 = np.array(x0, dtype=float)
    sol = least_squares(resid, x0, x_scale=np.array([1000.0, 1000.0, 4000.0])[: len(x0)], method="lm")
    return sol.x


def relative_error(a: float, ref: float) -> float:
    return abs(a - ref) / abs(ref)


class Stats:
    def __init__(self) -> None:
        self.draws = Counter()      # key -> accepted draws
        self.redraws = Counter()    # (key, reason) -> rejected draws
        self.racah_c_fit: list[dict] = []
        self.experimental: dict = {}
        self.fixed_pilot_overlap: dict = {}
        self.literature_all: dict = {}
        self.literature_new: dict = {}

    def accept(self, key: str) -> None:
        self.draws[key] += 1

    def reject(self, key: str, reason: str) -> None:
        self.redraws[(key, reason)] += 1


def _draw(rng, cls: str, d: int):
    (dq_lo, dq_hi), (b_lo, b_hi) = RANGES[(cls, d)]
    dq = float(round(rng.uniform(dq_lo, dq_hi)))
    b = float(round(rng.uniform(b_lo, b_hi)))
    c = float(round(rng.uniform(*CB_RANGE) * b))
    assert b < FREE_ION_B[d], (cls, d, b)
    return dq, b, c


def _close(dq: float, b: float, seen: list[tuple[float, float]]) -> bool:
    return any(abs(dq - q) / q < NEAR_DUPLICATE[0] and abs(b - w) / w < NEAR_DUPLICATE[1] for q, w in seen)


PROMPT_ALLOWED = (
    "An octahedral d{d} complex shows three spin-allowed d–d absorption bands at {a}, {b} and {c} cm⁻¹. "
    "Determine the ligand-field splitting parameter Dq and the Racah parameter B (in cm⁻¹).",
    "The electronic spectrum of an octahedral d{d} metal complex contains three spin-allowed ligand-field (d–d) bands "
    "with maxima at {a}, {b} and {c} cm⁻¹. What are the ligand-field splitting parameter Dq and the Racah "
    "parameter B, both in cm⁻¹?",
)


def prompt_allowed(rng, d: int, bands: list[float]) -> str:
    t = PROMPT_ALLOWED[int(rng.integers(len(PROMPT_ALLOWED)))]
    return t.format(d=d, a=group_thousands(bands[0]), b=group_thousands(bands[1]), c=group_thousands(bands[2]))


def record(*, cls, subtype, d_count, geometry, system, bands, prompt, required, reference, oracle,
           expect_oos=False, experimental=False, params=None, reference_curve=None, tolerance=None) -> dict:
    tol = dict(tolerance) if tolerance is not None else dict(TOL_EXPERIMENTAL if experimental else TOL_SYNTHETIC)
    ref = {k: (None if reference.get(k) is None else round(float(reference[k]), 2)) for k in ("Dq", "B", "C")}
    return {
        "answer_schema": ANSWER_SCHEMA_OF[cls],
        "bands_cm1": [float(x) for x in bands],
        "class": cls,
        "d_count": d_count,
        "expect_out_of_scope": expect_oos,
        "geometry": geometry,
        "oracle": oracle,
        "params": params,
        "prompt": prompt,
        "reference": ref,
        "reference_curve": reference_curve,
        "required": list(required),
        "subtype": subtype,
        "system": system,
        "tolerance": tol,
    }


# Low-spin ground terms of octahedral d4-d6 as they are printed in the numerical_hard prompts.
GROUND_TERM_LABEL = {"3_T_1": "³T₁g", "2_T_2": "²T₂g", "1_A_1": "¹A₁g"}


def ground_sequence(d: int, b: float, c: float, step: float = 20.0) -> list[str]:
    """The ground-term keys met on the way from Dq = 20 to 5 990 cm-1, consecutive duplicates merged."""
    comp = _compute()
    seq: list[str] = []
    for dq in np.arange(step, comp.STRONG_FIELD_DQ_CM1, step):
        g = comp.ground_term(comp.compute_point(d, float(dq), b, c))[0]
        g = getattr(g, "value", g)
        if not seq or seq[-1] != g:
            seq.append(g)
    return seq


def term_label(key) -> str:
    """'3_T_1' -> '3T1g', '2_E' -> '2Eg' (informational: labels are not scored)."""
    key = str(getattr(key, "value", key))
    mult, *rest = key.split("_")
    return mult + "".join(rest) + "g"


def excited_levels(d: int, dq: float, b: float, c: float) -> list[tuple[float, str]]:
    """(E/B above the lowest level, term label) of every other level, ascending; levels within 1e-6 of the ground
    level are copies of it and are dropped."""
    comp = _compute()
    pt = comp.compute_point(d, dq, b, c)
    lv = sorted((float(e), getattr(k, "value", k)) for k, vals in pt.items() for e in vals)
    g = lv[0][0]
    return [((e - g) / b, term_label(k)) for e, k in lv[1:] if e - g > 1e-6 * max(1.0, abs(g))]
