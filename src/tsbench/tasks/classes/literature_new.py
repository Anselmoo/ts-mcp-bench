"""Task class ``literature_new`` (pilot only): systems of the second literature table ``literature-spectra-2.csv``.

Same machinery as ``literature_all`` (forward-model least-squares oracle, identifiability rule for C, exclusion of
ambiguous, at-bound and non-fitting systems, same prompt text); only the table differs. The table holds 8 systems
curated from open-access papers. Extra provenance columns (location, quote, assignment confidence, original units) are
carried into ``params``. All usable systems go to the pilot; the class has no confirmatory records.
"""
from __future__ import annotations

import csv

from tsbench.tasks.classes import literature_all as L

DATA = L.DATA.parent / "literature-spectra-2.csv"  # literature/ of the package data
CLASS = "literature_new"
EXTRA_COLUMNS = ("location", "quote", "assignment_confidence", "original_units")


def _extra() -> dict[str, dict]:
    with DATA.open(newline="", encoding="utf-8") as fh:
        return {r["system"]: r for r in csv.DictReader(fh)}


def fit_all() -> tuple[dict, ...]:
    return L._fit_all(DATA)


def make_literature_new() -> tuple[list[dict], dict]:
    """Return (pilot, report). Deterministic (no random stream): every usable system is a pilot task, in file order."""
    items = list(fit_all())
    extra = _extra()
    used = [it for it in items if L._status(it)[0] == "used"]
    pilot = [L._record(it, CLASS, dict({k: extra[it["system"]][k] for k in EXTRA_COLUMNS}, source=it["source"]))
             for it in used]
    report = {
        "n_table_systems": len(items), "n_used": len(used), "n_pilot": len(pilot),
        "n_excluded": sum(L._status(it)[0] == "excluded" for it in items),
        "n_ambiguous": sum(L._status(it)[0] == "ambiguous" for it in items),
        "used": [it["system"] for it in used],
        "excluded": [{"system": it["system"], "d": it["d"], "reason": L._status(it)[1],
                      "rmse_cm1": round(it["fit"].get("rmse", float("nan")), 1)}
                     for it in items if L._status(it)[0] == "excluded"],
        "ambiguous": [{"system": it["system"], "d": it["d"], "reason": L._status(it)[1]}
                      for it in items if L._status(it)[0] == "ambiguous"],
        "sources": {it["system"]: it["source"] for it in items},
        "rmse_cm1": {it["system"]: round(it["fit"]["rmse"], 2) for it in items if it["fit"]["valid"]},
        "deviation_from_paper": {it["system"]: dict(it["deviation_from_paper"]) for it in items if it["fit"]["valid"]},
        "paper": {it["system"]: dict(it["paper"]) for it in items},
        "fitted": {it["system"]: {"Dq": round(it["fit"]["Dq"], 1), "B": round(it["fit"]["B"], 1),
                                  "C_over_B": round(it["fit"]["C"] / it["fit"]["B"], 3), "d": it["d"],
                                  "rmse": round(it["fit"]["rmse"], 1),
                                  "params_fitted": list(it["fit"]["params_fitted"])}
                   for it in items if it["fit"]["valid"]},
    }
    return pilot, report
