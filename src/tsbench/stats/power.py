"""Simulation-based power for choosing N (tasks) and k (repeats).

Task difficulty varies: each task's success probability under a condition is drawn from a
Beta distribution with the assumed mean and a concentration kappa (lower kappa = more
heterogeneous tasks). Conditions are paired through a shared task latent.

Assumed effect sizes are inputs. A value estimated from the pilot is an estimate, and the pilot tasks never reappear
in the confirmatory set.

    tsbench stats power --p-a 0.55 --p-b 0.90 [--out power.csv]
"""
from __future__ import annotations

import argparse
import csv
import pathlib

import numpy as np
from scipy import stats

from tsbench.stats.analysis import paired_majority, paired_rates


def simulate(n_tasks, k, p_a, p_b, kappa=8.0, alpha=0.05, n_sim=1000, seed=1):
    rng = np.random.default_rng(seed)
    hits_w = hits_m = 0
    for _ in range(n_sim):
        u = rng.uniform(size=n_tasks)  # shared task latent -> pairing
        pa = stats.beta.ppf(u, p_a * kappa, (1 - p_a) * kappa)
        pb = stats.beta.ppf(u, p_b * kappa, (1 - p_b) * kappa)
        ra = rng.binomial(k, pa) / k
        rb = rng.binomial(k, pb) / k
        hits_w += paired_rates(ra, rb) < alpha
        hits_m += paired_majority(ra, rb)[2] < alpha
    return hits_w / n_sim, hits_m / n_sim


def simulate_difference_in_differences(n_tasks, k, hi_b, hi_c, lo_b, lo_c, rho=0.5, kappa=8.0, alpha=0.0125,
                                       n_sim=1000, seed=1):
    """Power of H3: one-sample Wilcoxon (Pratt) of the per-task DiD (hi_B - lo_B) - (hi_C - lo_C), success iff p < alpha
    and mean DiD > 0. Per model the B and C probabilities share a task latent (Beta with the given means, kappa); the
    two models' latents are correlated by `rho` (Gaussian copula). `hi` is the larger model (Opus), `lo` the smaller."""
    from tsbench.stats.hypotheses import wilcoxon_zero
    rng = np.random.default_rng(seed)
    hits = 0
    for _ in range(n_sim):
        z_hi = rng.standard_normal(n_tasks)
        z_lo = rho * z_hi + np.sqrt(1 - rho ** 2) * rng.standard_normal(n_tasks)
        u_hi, u_lo = stats.norm.cdf(z_hi), stats.norm.cdf(z_lo)
        r = {}
        for name, u, mean in (("hb", u_hi, hi_b), ("hc", u_hi, hi_c), ("lb", u_lo, lo_b), ("lc", u_lo, lo_c)):
            r[name] = rng.binomial(k, stats.beta.ppf(u, mean * kappa, (1 - mean) * kappa)) / k
        d = (r["hb"] - r["lb"]) - (r["hc"] - r["lc"])
        hits += wilcoxon_zero(d) < alpha and d.mean() > 0
    return hits / n_sim


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--p-a", type=float, required=True, help="mean success, baseline condition")
    ap.add_argument("--p-b", type=float, required=True, help="mean success, MCP condition")
    ap.add_argument("--kappa", type=float, default=8.0)
    ap.add_argument("--alpha", type=float, default=None,
                    help="per-test alpha; default 0.05 / (models + 1) = 0.0125, the Holm worst case of the four "
                         "primary tests (three H2 tests and H3)")
    ap.add_argument("--n-sim", type=int, default=1000)
    ap.add_argument("--n-tasks", default="20,30,40,60", dest="n_tasks", help="comma list of N")
    ap.add_argument("--k", default="1,3,5", help="comma list of k")
    ap.add_argument("--out", default="power.csv", help="output CSV file (default: power.csv)")
    a = ap.parse_args(argv)
    if a.alpha is None:
        from tsbench.stats.hypotheses import MODELS
        a.alpha = 0.05 / (len(MODELS) + 1)
    rows = []
    for n in (int(x) for x in a.n_tasks.split(",")):
        for k in (int(x) for x in a.k.split(",")):
            pw, pm = simulate(n, k, a.p_a, a.p_b, a.kappa, a.alpha, a.n_sim)
            rows.append({"n_tasks": n, "k": k, "p_a": a.p_a, "p_b": a.p_b, "kappa": a.kappa,
                         "alpha": round(a.alpha, 4), "power_wilcoxon": pw, "power_mcnemar": pm})
            print(rows[-1])
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
