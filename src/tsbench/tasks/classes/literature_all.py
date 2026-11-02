"""Task class ``literature_all``: all systems of the literature table, reference computed by a forward-model fit.

Source table: ``src/tsbench/data/literature/literature-spectra.csv`` (Garcia Rojas & Perez Torres, J. Chem. Educ.
2023, 100, 251, d2-d8).

The reference is never typed. For every system the band energies of the table are fitted with a
forward-model least-squares over (Dq, B, C) using ``tanabesugano.mcp._compute.compute_point``.
The paper's own values are stored as ``paper`` for a secondary comparison only; they never enter the scoring.

Term labels (``band*_term``)
----------------------------
A label reads ``<n><2S+1><symmetry>``: ``13T2`` is the first (lowest) triplet T2, ``24T1`` the second quartet T1
and ``12E`` the first doublet E. ``compute_point`` returns ``{TermKey: [eigenvalues]}`` with one eigenvalue per
level of that term (sorted ascending, cm-1). The label maps to the solver key ``"<2S+1>_<sym>"`` (``13T2`` ->
``"3_T_2"``, ``24T1`` -> ``"4_T_1"``, ``11E`` -> ``"1_E"``, ``14T2`` -> ``"4_T_2"``) and the ordinal ``n`` picks the
n-th lowest eigenvalue of that key. Labels without an ordinal (``3E``, ``3A1`` of [Mn(CN)6]3-) are ambiguous in
the table; for those the level of the key nearest to the observed band is taken (listed in ``ordinal_free``).
A band energy is the distance of the level to the lowest level of the pinned ground term (see below).

Ground term: the fit is pinned to the high-spin ground term (``reference_ground_term(..., "high")``) except for
d4 and d6 systems that only report bands below the high-spin multiplicity (every d6 system of the table,
[Mn(CN)6]3-); these are pinned to the strong-field ground term. A fit whose overall lowest level is another term
is not accepted (it counts as "no valid fit").

Model rules
-----------
* bounds: Dq 200-4000, B 300-1300, C/B 3-6 (cm-1); several starts, the global best wins;
* identifiability: fewer than three bands, or bands that do not constrain C (Jacobian rank < 3 at the free fit:
  quartet-only d3/d7 and triplet-only d2/d8 bands are C-independent) -> C/B fixed at 4.5
  (``params_fitted == ["Dq", "B"]``, the prompt states the assumption); otherwise ``["Dq", "B", "C"]``;
* ambiguity: Dq profile (36 log-spaced Dq values, B and C/B optimised at each) plus all local minima of the
  multi-start. A second minimum whose cost is within 1 % of the best (plus a 1 cm-1 rmse floor, below the table's
  precision) at a Dq more than 5 % away flags the system ``ambiguous``;
* mismatch: best rmse above 3 % of the mean band energy -> "model does not fit". Reported, never repaired.
* bound: a best fit with Dq, B or (when fitted) C/B within 0.5 % of its bound (``BOUND_REL``) is a fit that ran into
  the box, not a determined value -> excluded with the reason "fit at bound".
Ambiguous, non-fitting and at-bound systems are listed in the report and are not turned into tasks.
"""
from __future__ import annotations

import csv
import functools
import math
import pathlib
import re

import numpy as np
from scipy.optimize import least_squares

from tsbench.core import resource

DATA = resource("literature/literature-spectra.csv")

NBSP = " "
DQ_BOUNDS = (200.0, 4000.0)
B_BOUNDS = (300.0, 1300.0)
CB_BOUNDS = (3.0, 6.0)
CB_FIXED = 4.5
MIN_BANDS_FOR_C = 3
AMBIG_COST_REL = 0.01
AMBIG_DQ_REL = 0.05
RMSE_FLOOR_CM1 = 1.0
MISMATCH_REL = 0.03
BOUND_REL = 0.005       # a parameter within this fraction of one of its bounds counts as "at the bound"
PILOT_FRACTION = 1 / 3
TOLERANCE = {"Dq": 0.05, "B": 0.10, "C": 0.15}
# the one row of the table that is a tetrahedral d8 ion; it is modelled as octahedral d2 with the same |Dq|
# (hole formalism, as in the ``tetrahedral`` class of generate.py)
TETRAHEDRAL_SYSTEMS = {"ZnO:Ni2+", "ZnS:Mn nanophosphor (zinc blende)"}  # the second one is in literature-spectra-2.csv

_LABEL = re.compile(r"^(?:(\d)(?=\d))?(\d)(A1|A2|T1|T2|E)$")
_SUP = "⁰¹²³⁴⁵⁶⁷⁸⁹"
_SUB = "₀₁₂₃₄₅₆₇₈₉"


# ----------------------------------------------------------------------------- labels

def parse_label(label: str) -> tuple[str, int | None]:
    """``'24T1'`` -> ``('4_T_1', 2)``; ``'3E'`` -> ``('3_E', None)`` (ordinal not given in the table)."""
    m = _LABEL.match(label.strip())
    if m is None:
        raise ValueError(f"unreadable term label {label!r}")
    ordinal, mult, sym = m.groups()
    key = f"{mult}_{sym[0]}_{sym[1]}" if len(sym) == 2 else f"{mult}_{sym}"
    return key, (int(ordinal) if ordinal else None)


def _pretty(label: str) -> str:
    key, ordinal = parse_label(label)
    mult, *sym = key.split("_")
    text = _SUP[int(mult)] + "".join(_SUB[int(s)] if s.isdigit() else s for s in "".join(sym))
    return text + (f"({ordinal})" if ordinal and ordinal > 1 else "")


def _levels(d: int, dq: float, b: float, c: float) -> dict[str, list[float]]:
    from tanabesugano.mcp._compute import compute_point  # imported late: optional dependency

    return {getattr(k, "value", str(k)): sorted(v) for k, v in compute_point(d, dq, b, c).items()}


def ground_key(d: int, regime: str, b: float = 700.0, c: float = 3150.0) -> str:
    from tanabesugano.mcp._compute import reference_ground_term

    g = reference_ground_term(d, b, c, regime)
    return str(getattr(g, "value", g))


def predicted(d: int, parsed: list[tuple[str, int | None]], gkey: str, dq: float, b: float, c: float,
              observed: np.ndarray | None = None) -> np.ndarray:
    """Band energies from the ground term's lowest level. Ordinal-free labels take the level nearest ``observed``."""
    lv = _levels(d, dq, b, c)
    g = lv[gkey][0]
    out = []
    for i, (key, ordinal) in enumerate(parsed):
        e = np.array(lv[key]) - g
        if ordinal is None:
            out.append(e[np.argmin(np.abs(e - observed[i]))] if observed is not None else e[0])
        else:
            out.append(e[ordinal - 1])
    return np.array(out)


def lowest_term(d: int, dq: float, b: float, c: float) -> str:
    lv = _levels(d, dq, b, c)
    return min(lv, key=lambda k: lv[k][0])


# ----------------------------------------------------------------------------- fitting

def _unpack(x, fit_c: bool):
    return (x[0], x[1], x[2] * x[1]) if fit_c else (x[0], x[1], CB_FIXED * x[1])


def _least_squares_fit(d, parsed, gkey, obs, x0, fit_c: bool, fixed_dq: float | None = None):
    """One bounded local fit. With ``fixed_dq`` the parameters are (B[, C/B]) only (profile point)."""
    lo = [DQ_BOUNDS[0], B_BOUNDS[0]] + ([CB_BOUNDS[0]] if fit_c else [])
    hi = [DQ_BOUNDS[1], B_BOUNDS[1]] + ([CB_BOUNDS[1]] if fit_c else [])
    scale = np.array([1000.0, 500.0, 1.0][: len(lo)])
    if fixed_dq is not None:
        lo, hi, scale = lo[1:], hi[1:], scale[1:]

    def resid(x):
        full = np.concatenate(([fixed_dq], x)) if fixed_dq is not None else x
        dq, b, c = _unpack(full, fit_c)
        try:
            r = predicted(d, parsed, gkey, dq, b, c, obs) - obs
        except Exception:  # noqa: BLE001 - a solver failure at a trial point is a bad point, not a crash
            return np.full(len(obs), 1e6)
        return r if np.all(np.isfinite(r)) else np.full(len(obs), 1e6)

    x0 = np.clip(np.array(x0, dtype=float), np.array(lo) + 1e-9, np.array(hi) - 1e-9)
    sol = least_squares(resid, x0, bounds=(lo, hi), x_scale=scale, diff_step=1e-6, max_nfev=200)
    full = np.concatenate(([fixed_dq], sol.x)) if fixed_dq is not None else sol.x
    dq, b, c = _unpack(full, fit_c)
    r = resid(sol.x)
    return {"Dq": float(dq), "B": float(b), "C": float(c), "sse": float(np.sum(r ** 2)), "x": full}


def _starts(fit_c: bool):
    for dq in (400, 800, 1200, 1700, 2300, 3000, 3700):
        for b in (450, 700, 950):
            for cb in ((3.8, 4.5, 5.3) if fit_c else (None,)):
                yield [dq, b] + ([cb] if fit_c else [])


def _valid(d, gkey, sol) -> bool:
    try:
        return lowest_term(d, sol["Dq"], sol["B"], sol["C"]) == gkey
    except Exception:  # noqa: BLE001
        return False


def _search(d, parsed, gkey, obs, fit_c: bool):
    """Multi-start fit plus Dq profile. Returns (best, candidates) or (None, [])."""
    cands = []
    for x0 in _starts(fit_c):
        sol = _least_squares_fit(d, parsed, gkey, obs, x0, fit_c)
        if _valid(d, gkey, sol):
            cands.append(sol)

    # Dq profile: optimise (B[, C/B]) on a fixed Dq grid; the profile's local minima are refined globally
    grid = np.geomspace(DQ_BOUNDS[0] * 1.05, DQ_BOUNDS[1] * 0.95, 36)
    prof = []
    for dq in grid:
        best = None
        for b0 in (500, 800, 1100):
            sol = _least_squares_fit(d, parsed, gkey, obs, [b0] + ([4.5] if fit_c else []), fit_c, fixed_dq=float(dq))
            if _valid(d, gkey, sol) and (best is None or sol["sse"] < best["sse"]):
                best = sol
        prof.append(best)
    for i, p in enumerate(prof):
        if p is None:
            continue
        nb = [prof[j]["sse"] for j in (i - 1, i + 1) if 0 <= j < len(prof) and prof[j] is not None]
        if all(p["sse"] <= s for s in nb):
            sol = _least_squares_fit(d, parsed, gkey, obs, list(p["x"]), fit_c)
            if _valid(d, gkey, sol):
                cands.append(sol)
    return (min(cands, key=lambda s: s["sse"]) if cands else None), cands


JAC_SCALE = np.array([1000.0, 500.0, 2500.0])   # typical size of Dq, B, C (cm-1): puts the columns on one scale
IDENTIFIABLE_SV = 10.0                           # cm-1 per scaled unit; below it a parameter direction is unconstrained


def band_rank(d, parsed, gkey, obs, sol) -> int:
    """Number of parameter directions (of Dq, B, C) the bands constrain at ``sol`` (Jacobian rank)."""
    x = np.array([sol["Dq"], sol["B"], sol["C"]])
    cols = []
    for j in range(3):
        h = 1e-4 * JAC_SCALE[j]
        up, dn = x.copy(), x.copy()
        up[j] += h
        dn[j] -= h
        cols.append((predicted(d, parsed, gkey, *up, obs) - predicted(d, parsed, gkey, *dn, obs))
                    / (2 * h) * JAC_SCALE[j])
    sv = np.linalg.svd(np.array(cols).T, compute_uv=False)
    return int(np.sum(sv > IDENTIFIABLE_SV))


def fit_labelled(d: int, labels: list[str], energies: list[float], regime: str = "high") -> dict:
    """Fit (Dq, B[, C]) to labelled band energies. Pure function of its inputs (no randomness).

    C is fitted only if the bands constrain it: fewer than three bands, or a Jacobian of rank < 3 at the
    free fit (e.g. quartet-only d3/d7, triplet-only d2/d8 bands do not depend on C), fix C/B = 4.5.
    """
    parsed = [parse_label(lab) for lab in labels]
    obs = np.array(energies, dtype=float)
    n = len(obs)
    gkey = ground_key(d, regime)
    fit_c, why_fixed = n >= MIN_BANDS_FOR_C, None
    if not fit_c:
        why_fixed = f"only {n} bands for 3 parameters"
    best, cands = _search(d, parsed, gkey, obs, fit_c) if fit_c else (None, [])
    if fit_c and best is not None:
        rank = band_rank(d, parsed, gkey, obs, best)
        if rank < 3:
            fit_c, why_fixed = False, f"bands constrain {rank} of 3 parameters (C-independent terms)"
    if not fit_c:
        best, cands = _search(d, parsed, gkey, obs, False)

    if best is None:
        return {"valid": False, "n_bands": n, "params_fitted": ["Dq", "B", "C"] if fit_c else ["Dq", "B"],
                "reason": "no valid fit (ground term is not the pinned term)", "ground_term": gkey}
    sse_tie = best["sse"] * (1 + AMBIG_COST_REL) + n * RMSE_FLOOR_CM1 ** 2
    far = [s for s in cands if abs(s["Dq"] - best["Dq"]) / best["Dq"] > AMBIG_DQ_REL]
    rivals = [s for s in far if s["sse"] <= sse_tie]
    nxt = min(far, key=lambda s: s["sse"]) if far else None
    rmse = math.sqrt(best["sse"] / n)
    return {
        "valid": True, "Dq": best["Dq"], "B": best["B"], "C": best["C"], "rmse": rmse, "n_bands": n,
        "next_minimum": None if nxt is None
                        else {"Dq": round(nxt["Dq"], 1), "rmse": round(math.sqrt(nxt["sse"] / n), 2)},
        "params_fitted": ["Dq", "B", "C"] if fit_c else ["Dq", "B"],
        "cb_fixed": None if fit_c else CB_FIXED, "c_fixed_because": why_fixed, "ground_term": gkey, "regime": regime,
        "ambiguous": bool(rivals), "rival_dq": sorted({round(s["Dq"], 1) for s in rivals}),
        "mean_band": float(np.mean(obs)), "mismatch": rmse > MISMATCH_REL * float(np.mean(obs)),
    }


# ----------------------------------------------------------------------------- the table

def _val(s: str) -> float | None:
    s = s.strip().lstrip("≈").replace("−", "-")
    return float(s) if s else None


def _num(s: str):
    try:
        return _val(s)
    except ValueError:
        return None


def read_table(path: pathlib.Path = DATA) -> list[dict]:
    """All rows of a table in the layout of ``literature-spectra.csv``, in file order. Columns that a table does not
    have (the auxiliary-diagram values) read as ``None``."""
    rows = []
    with pathlib.Path(path).open(newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            d = int(re.search(r"d(\d)", r["config"]).group(1))
            labels, energies, approx = [], [], []
            for i in (1, 2, 3, 4):
                raw = r[f"band{i}_cm-1"].strip()
                if raw:
                    labels.append(r[f"band{i}_term"].strip())
                    energies.append(_val(raw))
                    approx.append(raw.startswith("≈"))
            rows.append({
                "system": r["system"], "d": d, "source": r.get("source", ""), "labels": labels, "bands": energies,
                "approx": approx,
                "paper": {
                    "Dq_cm-1": _num(r["Dq_cm-1"]), "DqB_reported": _num(r["DqB_reported"]),
                    "DqB_aux_diagram": _num(r.get("DqB_aux_diagram", "")), "CB_reported": _num(r["CB_reported"]),
                    "CB_aux_diagram": _num(r.get("CB_aux_diagram", "")),
                },
            })
    return rows


def regime_of(d: int, labels: list[str]) -> str:
    """Strong-field ground term for d4/d6 systems that only report bands below the high-spin multiplicity."""
    if d in (4, 6) and max(int(parse_label(lab)[0][0]) for lab in labels) < 5:
        return "low"
    return "high"


def _deviation(fit: dict, paper: dict) -> dict:
    def rel(a, ref):
        return None if ref in (None, 0) or a is None else round((a - ref) / ref, 4)

    c_b = fit["C"] / fit["B"] if "params_fitted" in fit and "C" in fit["params_fitted"] else None
    return {
        "Dq_rel": rel(fit["Dq"], paper["Dq_cm-1"]),
        "DqB_rel_vs_reported": rel(fit["Dq"] / fit["B"], paper["DqB_reported"]),
        "DqB_rel_vs_aux_diagram": rel(fit["Dq"] / fit["B"], paper["DqB_aux_diagram"]),
        "CB_rel_vs_reported": rel(c_b, paper["CB_reported"]),
        "CB_rel_vs_aux_diagram": rel(c_b, paper["CB_aux_diagram"]),
    }


@functools.cache
def _fit_all(path: pathlib.Path = DATA) -> tuple[dict, ...]:
    out = []
    for row in read_table(path):
        regime = regime_of(row["d"], row["labels"])
        fit = fit_labelled(row["d"], row["labels"], row["bands"], regime)
        rec = dict(row, fit=fit)
        if fit["valid"]:
            rec["deviation_from_paper"] = _deviation(fit, row["paper"])
        out.append(rec)
    return tuple(out)


def at_bound(fit: dict) -> list[str]:
    """Names of the fitted parameters that sit within ``BOUND_REL`` of a bound (C/B only when C was fitted)."""
    checks = [("Dq", fit["Dq"], DQ_BOUNDS), ("B", fit["B"], B_BOUNDS)]
    if "C" in fit["params_fitted"]:
        checks.append(("C/B", fit["C"] / fit["B"], CB_BOUNDS))
    out = []
    for name, value, (lo, hi) in checks:
        if abs(value - lo) <= BOUND_REL * lo:
            out.append(f"{name} = {value:.3g} at the lower bound {lo:g}")
        elif abs(value - hi) <= BOUND_REL * hi:
            out.append(f"{name} = {value:.3g} at the upper bound {hi:g}")
    return out


def _status(item: dict) -> tuple[str, str]:
    f = item["fit"]
    if not f["valid"]:
        return "excluded", f["reason"]
    bound = at_bound(f)
    if bound:
        return "excluded", "fit at bound (" + "; ".join(bound) + ")"
    if f["mismatch"]:
        return "excluded", (f"model does not fit (rmse {f['rmse']:.0f} cm-1 = "
                            f"{100 * f['rmse'] / f['mean_band']:.1f} % of the mean band)")
    if f["ambiguous"]:
        return "ambiguous", f"second minimum at Dq = {', '.join(str(x) for x in f['rival_dq'])} cm-1"
    return "used", ""


# ----------------------------------------------------------------------------- records

def _num_fmt(x: float) -> str:
    return f"{int(round(x)):,}".replace(",", NBSP)


def _prompt(item: dict) -> str:
    name, d, f = item["system"], item["d"], item["fit"]
    td = name in TETRAHEDRAL_SYSTEMS
    d_ion = 10 - d if td else d
    ion = f"d{''.join(_SUP[int(c)] for c in str(d_ion))}"
    bands = [_num_fmt(x) for x in item["bands"]]
    listed = ", ".join(bands[:-1]) + f" and {bands[-1]}" if len(bands) > 1 else bands[0]
    assigned = ", ".join(_pretty(lab) for lab in item["labels"])
    note = ""
    if any((parse_label(lab)[1] or 1) > 1 for lab in item["labels"]):
        note = "; a number in parentheses counts the terms of the same symbol upwards in energy"
    geometry = "tetrahedral" if td else "octahedral"
    if "C" in f["params_fitted"]:
        ask = "Determine the ligand-field splitting parameter Dq and the Racah parameters B and C (in cm⁻¹)."
    else:
        ask = (f"Assume C/B = {CB_FIXED}. Determine the ligand-field splitting parameter Dq and the Racah "
               "parameter B (in cm⁻¹).")
    return (f"The {geometry} {ion} system {name} shows absorption bands at {listed} cm⁻¹ "
            f"(assigned {assigned}, respectively{note}). {ask}")


def _record(item: dict, cls: str = "literature_all", extra_params: dict | None = None) -> dict:
    f = item["fit"]
    td = item["system"] in TETRAHEDRAL_SYSTEMS
    fitted_c = "C" in f["params_fitted"]
    d_count = 10 - item["d"] if td else item["d"]
    ref = {"Dq": round(f["Dq"], 2), "B": round(f["B"], 2), "C": round(f["C"], 2) if fitted_c else None}
    return {
        "answer_schema": "fit",
        "bands_cm1": [float(x) for x in item["bands"]],
        "class": cls,
        "d_count": d_count,
        "expect_out_of_scope": False,
        "geometry": "Td" if td else "Oh",
        "oracle": "forward_model_lsq",
        "params": {
            "params_fitted": list(f["params_fitted"]), "cb_fixed": f["cb_fixed"],
            "c_fixed_because": f["c_fixed_because"], "ambiguous": f["ambiguous"],
            "rmse_cm1": round(f["rmse"], 2), "labels": list(item["labels"]), "model_d": item["d"],
            "ground_term": f["ground_term"],
            "ordinal_free": [lab for lab in item["labels"] if parse_label(lab)[1] is None],
            "approximate_bands": [lab for lab, a in zip(item["labels"], item["approx"], strict=False) if a],
            "paper": dict(item["paper"]), "deviation_from_paper": dict(item["deviation_from_paper"]),
            **(extra_params or {}),
        },
        "prompt": _prompt(item),
        "reference": ref,
        "reference_curve": None,
        "required": list(f["params_fitted"]),
        "subtype": f"d{d_count}",
        "system": item["system"],
        "tolerance": {"Dq": TOLERANCE["Dq"], "B": TOLERANCE["B"], "C": TOLERANCE["C"] if fitted_c else None},
    }


def make_literature_all(rng, fixed_pilot_systems: set) -> tuple[list[dict], list[dict], dict]:
    """Return (pilot, confirmatory, report). The fit is deterministic; ``rng`` only drives the split."""
    items = list(_fit_all())
    used = [it for it in items if _status(it)[0] == "used"]
    by_d: dict[int, list[dict]] = {}
    for it in used:
        by_d.setdefault(it["d"], []).append(it)

    pilot_items: list[dict] = []
    for d in sorted(by_d):
        group = by_d[d]
        forced = [it for it in group if it["system"] in fixed_pilot_systems]
        rest = [it for it in group if it["system"] not in fixed_pilot_systems]
        n_pilot = max(len(forced), int(math.floor(len(group) * PILOT_FRACTION + 0.5)))
        order = rng.permutation(len(rest))
        pilot_items += forced + [rest[i] for i in order[: n_pilot - len(forced)]]
    pilot_names = {it["system"] for it in pilot_items}
    pilot = [_record(it) for it in used if it["system"] in pilot_names]
    conf = [_record(it) for it in used if it["system"] not in pilot_names]

    per_d: dict[str, dict] = {}
    for it in items:
        status, _ = _status(it)
        row = per_d.setdefault(f"d{it['d']}", {"used": 0, "excluded": 0, "ambiguous": 0})
        row[status] += 1
    report = {
        "n_table_systems": len(items),
        "n_used": len(used), "n_pilot": len(pilot), "n_confirmatory": len(conf),
        "n_excluded": sum(_status(it)[0] == "excluded" for it in items),
        "n_ambiguous": sum(_status(it)[0] == "ambiguous" for it in items),
        "per_d": per_d,
        "excluded": [{"system": it["system"], "d": it["d"], "reason": _status(it)[1],
                      "rmse_cm1": round(it["fit"].get("rmse", float("nan")), 1)}
                     for it in items if _status(it)[0] == "excluded"],
        "ambiguous": [{"system": it["system"], "d": it["d"], "reason": _status(it)[1]}
                      for it in items if _status(it)[0] == "ambiguous"],
        "rmse_cm1": {it["system"]: round(it["fit"]["rmse"], 2) for it in items if it["fit"]["valid"]},
        "deviation_from_paper": {it["system"]: dict(it["deviation_from_paper"]) for it in items if it["fit"]["valid"]},
        "fitted": {it["system"]: {"Dq": round(it["fit"]["Dq"], 1), "B": round(it["fit"]["B"], 1),
                                  "C_over_B": round(it["fit"]["C"] / it["fit"]["B"], 3), "d": it["d"],
                                  "params_fitted": list(it["fit"]["params_fitted"])}
                   for it in items if it["fit"]["valid"]},
        "fixed_pilot_forced": sorted(pilot_names & set(fixed_pilot_systems)),
    }
    return pilot, conf, report
