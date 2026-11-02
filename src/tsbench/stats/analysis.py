"""Paired tests and intervals of the MCP benchmark.

Unit of analysis: the task. Each (model, condition, task) has k repeated runs. Per task:
  rate     = share of correct runs (k runs)           -> Wilcoxon signed-rank, paired by task
  majority = rate > 0.5                               -> exact McNemar, paired by task
Multiple comparisons: Holm over the family of primary tests (see hypotheses.py).
"""
from __future__ import annotations

from math import comb

import numpy as np
from scipy import stats


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar p-value from the discordant counts b (A right, B wrong)
    and c (A wrong, B right)."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(comb(n, i) for i in range(k + 1)) / 2**n
    return min(1.0, 2 * tail)


def paired_majority(rates_a: np.ndarray, rates_b: np.ndarray) -> tuple[int, int, float]:
    ma, mb = rates_a > 0.5, rates_b > 0.5
    b = int(np.sum(ma & ~mb))
    c = int(np.sum(~ma & mb))
    return b, c, mcnemar_exact(b, c)


def paired_rates(rates_a: np.ndarray, rates_b: np.ndarray) -> float:
    # rates are counts / k: equal differences can differ in the last bit (k = 3, 5, 6, ...), so ties and zeros are
    # decided on a fixed grid of 1e-9, not by floating-point noise
    d = np.round(np.asarray(rates_b, dtype=float) - np.asarray(rates_a, dtype=float), 9)
    if np.all(d == 0):
        return 1.0
    return float(stats.wilcoxon(d, zero_method="pratt").pvalue)


def holm(pvalues: list[float]) -> list[float]:
    m = len(pvalues)
    order = np.argsort(pvalues)
    adj = np.empty(m)
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, (m - rank) * pvalues[i])
        adj[i] = min(1.0, running)
    return adj.tolist()


def bootstrap_ci(rates_a, rates_b, n_boot=5000, alpha=0.05, seed=0):
    """Percentile CI of the mean paired difference in per-task success rate."""
    rng = np.random.default_rng(seed)
    d = np.asarray(rates_b) - np.asarray(rates_a)
    idx = rng.integers(0, len(d), size=(n_boot, len(d)))
    means = d[idx].mean(axis=1)
    return float(np.quantile(means, alpha / 2)), float(np.quantile(means, 1 - alpha / 2))
