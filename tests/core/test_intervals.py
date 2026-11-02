"""Tests for tsbench.core.intervals: Wilson, the task-clustered bootstrap and the Clopper-Pearson interval.

Expected values are hand-checked against the published formulas and a seeded replay of the bootstrap draws.
"""
from __future__ import annotations

import math

import numpy as np
import pytest
from scipy import stats

from tsbench.core import intervals as I


def _replay(num, den, seed, resamples):
    """The same draws as cluster_bootstrap, written out again: one seeded integer matrix, sums over tasks, ratio."""
    num, den = np.asarray(num, dtype=float), np.asarray(den, dtype=float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(num), size=(resamples, len(num)))
    n_, d_ = num[idx].sum(axis=1), den[idx].sum(axis=1)
    ok = d_ > 0
    lo, hi = np.percentile(n_[ok] / d_[ok], [2.5, 97.5])
    return float(lo), float(hi)


def test_wilson_matches_the_published_values():
    lo, hi = I.wilson(5, 10)
    assert lo == pytest.approx(0.236593, abs=1e-6) and hi == pytest.approx(0.763407, abs=1e-6)
    assert I.wilson(0, 10)[0] == 0.0 and I.wilson(0, 10)[1] == pytest.approx(0.277533, abs=1e-6)
    assert I.wilson(10, 10)[1] == pytest.approx(1.0) and I.wilson(10, 10)[0] == pytest.approx(0.722467, abs=1e-6)


def test_wilson_uses_the_given_z_and_is_centred_at_p_without_it():
    assert I.wilson(5, 10, z=0.0) == (0.5, 0.5)
    lo, hi = I.wilson(1, 2)
    assert 0.0 <= lo < 0.5 < hi <= 1.0


def test_wilson_without_trials_is_nan():
    lo, hi = I.wilson(0, 0)
    assert math.isnan(lo) and math.isnan(hi)
    assert all(math.isnan(v) for v in I.wilson(3, -1))


def test_wilson_interval_widens_with_z():
    narrow = I.wilson(20, 40, z=1.0)
    wide = I.wilson(20, 40, z=2.5)
    assert wide[0] < narrow[0] and narrow[1] < wide[1]


def test_cluster_bootstrap_is_the_seeded_replay():
    num = [3.0, 1.0, 0.0, 4.0, 2.0]
    den = [5.0, 2.0, 1.0, 4.0, 3.0]
    got = I.cluster_bootstrap(num, den, seed=7, resamples=300)
    assert got == pytest.approx(_replay(num, den, 7, 300))
    assert got != I.cluster_bootstrap(num, den, seed=8, resamples=300)


def test_cluster_bootstrap_defaults_to_the_fixed_seed_and_resamples():
    num, den = [1.0, 0.0, 2.0, 3.0], [2.0, 1.0, 2.0, 5.0]
    assert I.cluster_bootstrap(num, den) == pytest.approx(
        _replay(num, den, I.SEED, I.RESAMPLES))


def test_cluster_bootstrap_of_a_constant_ratio_is_that_ratio():
    assert I.cluster_bootstrap([1.0, 1.0, 1.0], [1.0, 1.0, 1.0]) == (1.0, 1.0)
    lo, hi = I.cluster_bootstrap([2.0, 4.0, 6.0], [4.0, 8.0, 12.0], seed=1, resamples=200)
    assert lo == pytest.approx(0.5) and hi == pytest.approx(0.5)


def test_cluster_bootstrap_skips_draws_without_a_denominator():
    num, den = [1.0, 0.0], [0.0, 1.0]
    lo, hi = I.cluster_bootstrap(num, den, seed=3, resamples=400)
    assert lo == pytest.approx(_replay(num, den, 3, 400)[0]) and hi == pytest.approx(_replay(num, den, 3, 400)[1])
    assert 0.0 <= lo <= hi


def test_cluster_bootstrap_without_tasks_or_denominator_is_nan():
    lo, hi = I.cluster_bootstrap([], [])
    assert math.isnan(lo) and math.isnan(hi)
    lo, hi = I.cluster_bootstrap([0.0, 0.0], [0.0, 0.0], seed=1, resamples=10)
    assert math.isnan(lo) and math.isnan(hi)


def test_clopper_pearson_matches_the_exact_binomial_limits():
    assert I.clopper_pearson(0, 10) == (0.0, pytest.approx(1 - 0.025 ** 0.1, abs=1e-9))
    lo, hi = I.clopper_pearson(10, 10)
    assert hi == 1.0 and lo == pytest.approx(0.025 ** 0.1, abs=1e-9)
    lo, hi = I.clopper_pearson(5, 10)
    assert lo == pytest.approx(0.187086, abs=1e-6) and hi == pytest.approx(0.812914, abs=1e-6)


def test_clopper_pearson_takes_alpha():
    lo, hi = I.clopper_pearson(3, 12, alpha=0.1)
    assert lo == pytest.approx(float(stats.beta.ppf(0.05, 3, 10)))
    assert hi == pytest.approx(float(stats.beta.ppf(0.95, 4, 9)))
    wide = I.clopper_pearson(3, 12, alpha=0.05)
    assert wide[0] < lo and hi < wide[1]
