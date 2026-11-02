"""The `experimental` task class: how one task of the class is drawn (called by tsbench.tasks.generate)."""
from __future__ import annotations

import csv
import math

from tsbench.tasks.common import (
    COUNTS,
    TOL_EXPERIMENTAL,
    Stats,
    _fixed_pilot_systems,
    group_thousands,
    record,
    relative_error,
)
from tsbench.tasks.oracles.check import D_COUNT, DATA
from tsbench.tasks.oracles.check import bands as csv_bands
from tsbench.tasks.oracles.closed_form import dq_b, dq_b_two_band


def _experimental_rows():
    """All octahedral d3/d8 rows of the literature table, classified. Reference values are computed here."""
    usable, excluded = [], []
    with DATA.open(newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            d = D_COUNT.get(r["config"])
            if d is None:
                continue
            name = r["system"]
            n1, n2 = (float(r[k].strip().lstrip("≈")) for k in ("band1_cm-1", "band2_cm-1"))
            b3 = csv_bands(r)
            if b3 is None:
                dq, b = dq_b_two_band(n1, n2)
                usable.append(dict(system=name, d=d, bands=[n1, n2], dq=dq, b=b, kind="two_band"))
                continue
            cf = dq_b(*b3)
            if math.isnan(cf.dq_from_quadratic):
                # No real root: the third band is inconsistent with the first two. The first two bands
                # are still a valid input to the two-band relations.
                dq, b = dq_b_two_band(n1, n2)
                usable.append(dict(system=name, d=d, bands=[n1, n2], dq=dq, b=b, kind="two_band_from_nan",
                                   note=f"three-band closed form has no real root (nu3 = {group_thousands(b3[2])} "
                                        "is inconsistent with nu1, nu2)"))
                continue
            ddq = relative_error(cf.dq_from_nu1, cf.dq_from_quadratic)
            db = relative_error(cf.b_from_nu1, cf.b_from_quadratic)
            if ddq > TOL_EXPERIMENTAL["Dq"] or db > TOL_EXPERIMENTAL["B"]:
                excluded.append((name, d, "oracle ambiguous: Dq from nu1 and Dq from the quadratic differ by "
                                          f"{100 * ddq:.1f} % (B by {100 * db:.1f} %), beyond the tolerance; "
                                          "a standard estimator would be marked wrong"))
                continue
            usable.append(dict(system=name, d=d, bands=b3, dq=cf.dq_from_quadratic, b=cf.b_from_quadratic,
                               kind="three_band"))
    return usable, excluded


def make_experimental(rng, stats: Stats, other_pilot: frozenset = frozenset(), lit_conf_all: frozenset = frozenset()):
    """Pilot: the two rows drawn first (one d3, one d8). Confirmatory (separation rule, rubric.md): a usable row that
    is neither a pilot system of ANY class (``other_pilot`` plus the two drawn here) nor a confirmatory
    ``literature_all`` system (``lit_conf_all`` minus those pilot systems: a system belongs to exactly one class, and
    ``literature_all`` keeps it) nor a fixed pilot system. The count is ``COUNTS``; if fewer rows qualify the assert
    fails and COUNTS must be lowered (a system is never reused)."""
    usable, excluded = _experimental_rows()
    d3 = [u for u in usable if u["d"] == 3]
    d8 = [u for u in usable if u["d"] == 8]
    p3, p8 = int(rng.integers(len(d3))), int(rng.integers(len(d8)))
    pilot = [d3[p3], d8[p8]]
    # The fixed pilot systems never become confirmatory.
    seen = _fixed_pilot_systems()
    all_pilot = set(other_pilot) | {u["system"] for u in pilot}
    lit_final = set(lit_conf_all) - all_pilot
    rest = [u for u in usable if u not in pilot and u["system"] not in seen
            and u["system"] not in all_pilot and u["system"] not in lit_final]
    order = rng.permutation(len(rest))
    n_conf = COUNTS['experimental'][1]
    assert len(rest) >= n_conf, f"experimental: {len(rest)} free rows for {n_conf} confirmatory tasks"
    conf = [rest[i] for i in order[:n_conf]]
    reserve = [rest[i] for i in order[n_conf:]]
    stats.experimental = dict(usable=len(usable), excluded=excluded, pilot=len(pilot), confirmatory=len(conf),
                              reserve=len(reserve),
                              not_pilot=sum(u["system"] not in all_pilot for u in usable),
                              also_literature_all_confirmatory=sum(u["system"] in lit_final for u in usable),
                              n_two_band=sum(u["kind"] != "three_band" for u in usable),
                              n_two_band_from_nan=sum(u["kind"] == "two_band_from_nan" for u in usable))

    def build(u):
        n = len(u["bands"])
        what = "three spin-allowed d–d absorption bands" if n == 3 else \
            "two spin-allowed d–d absorption bands (the two lowest in energy)"
        listed = ", ".join(group_thousands(x) for x in u["bands"][:-1]) + f" and {group_thousands(u['bands'][-1])}"
        prompt = (f"The octahedral d{u['d']} system {u['system']} shows {what} at {listed} cm⁻¹. "
                  "Determine the ligand-field splitting parameter Dq and the Racah parameter B (in cm⁻¹).")
        return record(
            cls="experimental", subtype=f"d{u['d']}", d_count=u["d"], geometry="Oh", system=u["system"],
            bands=u["bands"], prompt=prompt, required=["Dq", "B"],
            reference={"Dq": u["dq"], "B": u["b"], "C": None}, oracle="closed_form", experimental=True)

    return [build(u) for u in pilot], [build(u) for u in conf]
