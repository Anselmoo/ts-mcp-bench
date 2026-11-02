"""Check tanabesugano.fit_spectrum against the independent closed form and against the
values reported in the literature table (data/literature/literature-spectra.csv).

Scope: octahedral d3 and d8 rows with all three spin-allowed bands. Writes one CSV row per
system to the required --out file.

    tsbench tasks check-oracle --out <file.csv>
"""
from __future__ import annotations

import argparse
import csv
import pathlib

from tsbench.core import resource
from tsbench.tasks.oracles.closed_form import dq_b

DATA = resource("literature/literature-spectra.csv")
D_COUNT = {"d3(Oh)/d7(Td)": 3, "d8(Oh)/d2(Td)": 8}


def bands(row: dict) -> list[float] | None:
    vals = []
    for k in ("band1_cm-1", "band2_cm-1", "band3_cm-1"):
        v = row[k].strip().lstrip("≈")
        if not v:
            return None
        vals.append(float(v))
    return vals


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="tsbench tasks check-oracle", description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True, help="CSV file to write (one row per system)")
    args = ap.parse_args(argv)
    from tanabesugano.mcp._compute import fit_spectrum  # imported late: optional dependency

    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    with DATA.open(newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            d = D_COUNT.get(r["config"])
            b = bands(r)
            if d is None or b is None:
                continue
            cf = dq_b(*b)
            try:
                fit = fit_spectrum(d, b, spin_state="high")
                fdq, fb, rmse, err = fit.Dq, fit.B, fit.rmse_cm1, ""
            except ValueError as e:  # report, never drop
                fdq = fb = rmse = float("nan")
                err = str(e)[:120]
            lit = float(r["Dq_cm-1"]) if r["Dq_cm-1"] else float("nan")
            rows.append({
                "system": r["system"], "d": d, "nu1": b[0], "nu2": b[1], "nu3": b[2],
                "cf_dq_nu1": round(cf.dq_from_nu1, 1), "cf_dq_quad": round(cf.dq_from_quadratic, 1),
                "cf_b_quad": round(cf.b_from_quadratic, 1), "cf_dq_disagreement": round(cf.dq_disagreement, 1),
                "fit_dq": round(fdq, 1), "fit_b": round(fb, 1), "fit_rmse": round(rmse, 1),
                "lit_dq": lit, "fit_minus_cf_dq": round(fdq - cf.dq_from_quadratic, 1),
                "fit_minus_lit_dq": round(fdq - lit, 1), "error": err,
            })
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} systems -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
