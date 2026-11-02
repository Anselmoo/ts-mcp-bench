"""Confidence intervals for the figures: Wilson score interval and a task-clustered bootstrap.

The bootstrap resamples *tasks* with replacement and keeps the k repetitions of a task together; the statistic is a
ratio of sums over the resampled tasks (share correct = sum correct / sum runs; cost per correct = sum cost / sum
correct).
Seed and number of resamples are fixed, so the output is deterministic.
"""
from __future__ import annotations

import math

import numpy as np

Z95 = 1.959963984540054
SEED = 20261024
RESAMPLES = 2000


def wilson(k: int, n: int, z: float = Z95) -> tuple[float, float]:
    """95 % Wilson score interval of k successes in n trials, as fractions."""
    if n <= 0:
        return (math.nan, math.nan)
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, centre - half), min(1.0, centre + half))


def cluster_bootstrap(num, den, seed: int = SEED, resamples: int = RESAMPLES) -> tuple[float, float]:
    """Percentile 95 % interval of sum(num)/sum(den) over tasks resampled with replacement.

    `num` and `den` hold one entry per task (in a fixed order). Draws with a zero denominator are skipped."""
    num = np.asarray(num, dtype=float)
    den = np.asarray(den, dtype=float)
    t = len(num)
    if t == 0:
        return (math.nan, math.nan)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, t, size=(resamples, t))
    n_ = num[idx].sum(axis=1)
    d_ = den[idx].sum(axis=1)
    ok = d_ > 0
    if not ok.any():
        return (math.nan, math.nan)
    vals = n_[ok] / d_[ok]
    lo, hi = np.percentile(vals, [2.5, 97.5])
    return (float(lo), float(hi))


def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Exact two-sided binomial CI for k successes in n trials."""
    from scipy import stats  # late: scipy only where an exact interval is asked for

    lo = 0.0 if k == 0 else float(stats.beta.ppf(alpha / 2, k, n - k + 1))
    hi = 1.0 if k == n else float(stats.beta.ppf(1 - alpha / 2, k + 1, n - k))
    return lo, hi
