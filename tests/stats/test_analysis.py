"""Tests for the frozen primitives in tsbench.stats.analysis, against hand-computed values (no network, no LLM)."""
from __future__ import annotations

import warnings

import numpy as np
import pytest
from scipy import stats

from tsbench.stats.analysis import bootstrap_ci, holm, mcnemar_exact, paired_majority, paired_rates


def test_mcnemar_exact_hand_values():
    # b=1, c=5: n=6, k=1, tail = (C(6,0) + C(6,1)) / 64 = 7/64, p = 14/64
    assert mcnemar_exact(1, 5) == pytest.approx(14 / 64)
    assert mcnemar_exact(5, 1) == pytest.approx(14 / 64)          # symmetric in b and c
    # b=0, c=10: tail = 1/1024
    assert mcnemar_exact(0, 10) == pytest.approx(2 / 1024)
    # b=2, c=3: n=5, tail = (1 + 5 + 10) / 32 = 0.5, doubled = 1.0
    assert mcnemar_exact(2, 3) == 1.0


def test_mcnemar_exact_is_capped_at_one_and_empty_is_one():
    assert mcnemar_exact(0, 0) == 1.0
    # equal counts: the doubled tail is 1.3125 and must be capped
    assert mcnemar_exact(3, 3) == 1.0
    assert mcnemar_exact(1, 0) == 1.0


def test_paired_majority_counts_discordant_pairs_with_a_strict_threshold():
    # a>0.5: [F, T, T, F], b>0.5: [T, F, T, F]; a rate of exactly 0.5 is not a majority
    a = np.array([0.5, 1.0, 0.75, 0.0])
    b = np.array([1.0, 0.5, 0.75, 0.25])
    nb, nc, p = paired_majority(a, b)
    assert (nb, nc) == (1, 1) and p == 1.0
    assert all(isinstance(v, int) for v in (nb, nc))
    # A right and B wrong (b) versus A wrong and B right (c)
    nb, nc, p = paired_majority(np.array([0.9, 0.9, 0.9, 0.1]), np.array([0.1, 0.1, 0.1, 0.9]))
    assert (nb, nc) == (3, 1) and p == pytest.approx(mcnemar_exact(3, 1))


def test_paired_rates_is_one_when_nothing_differs():
    x = np.array([0.2, 0.4, 0.6, 1.0])
    with warnings.catch_warnings():
        warnings.simplefilter("error")      # the all-zero case is answered here, scipy's 0/0 warning must not appear
        assert paired_rates(x, x) == 1.0
        assert paired_rates(np.zeros(3), np.zeros(3)) == 1.0


def test_paired_rates_uses_the_pratt_zero_method():
    rng = np.random.default_rng(5)
    a = np.round(rng.uniform(0, 1, 12), 2)
    b = np.round(np.clip(a + rng.normal(0.1, 0.2, 12), 0, 1), 2)
    b[3] = a[3]                                                  # one tied pair
    d = np.round(b - a, 9)                                       # two-decimal rates: ties are decided on the grid
    pratt = stats.wilcoxon(d, zero_method="pratt").pvalue
    assert paired_rates(a, b) == pytest.approx(float(pratt))
    assert pratt != pytest.approx(stats.wilcoxon(d, zero_method="wilcox").pvalue, abs=0.05)   # the choice matters


def test_paired_rates_k3_ties_are_decided_on_a_grid_not_by_the_last_bit():
    # k = 3: the rate differences are exact multiples of 1/3 in real arithmetic, but 1/3 - 0 and 1.0 - 2/3 differ in
    # the last bit, so the float ranking breaks ties (and zeros) by rounding noise
    ca = np.array([0, 0, 0, 0, 2, 2, 2, 2, 1, 1, 3, 3])
    cb = np.array([1, 1, 1, 1, 3, 3, 3, 3, 0, 0, 2, 2])
    on_counts = float(stats.wilcoxon(cb - ca, zero_method="pratt").pvalue)
    assert on_counts == pytest.approx(0.3877, abs=1e-4)
    assert paired_rates(ca / 3, cb / 3) == pytest.approx(on_counts)
    # a zero difference computed from different rate pairs is a zero: (2/3 - 1/3) - 1/3 style noise must not count
    a, b = np.array([1 / 3, 2 / 3, 0.0, 1.0, 1 / 3, 0.0]), np.array([2 / 3, 1.0, 1 / 3, 1.0, 1 / 3, 2 / 3])
    on_counts = float(stats.wilcoxon(np.array([1, 1, 1, 0, 0, 2]), zero_method="pratt").pvalue)
    assert paired_rates(a, b) == pytest.approx(on_counts)


def test_paired_rates_sign_does_not_matter_for_a_two_sided_test():
    a = np.array([0.1, 0.3, 0.2, 0.6, 0.5, 0.9])
    b = np.array([0.4, 0.3, 0.7, 0.9, 0.8, 0.95])
    assert paired_rates(a, b) == pytest.approx(paired_rates(b, a))
    assert 0 < paired_rates(a, b) < 0.1


def test_holm_hand_values_and_input_order():
    # sorted: 0.01 -> 3*0.01, 0.03 -> 2*0.03, 0.04 -> max(0.06, 1*0.04)
    assert holm([0.01, 0.04, 0.03]) == pytest.approx([0.03, 0.06, 0.06])
    assert holm([0.5, 0.01]) == pytest.approx([0.5, 0.02])
    assert holm([0.01]) == pytest.approx([0.01])             # a single test is not inflated
    assert holm([]) == []


def test_holm_caps_at_one_and_is_monotone():
    assert holm([0.6, 0.7]) == [1.0, 1.0]
    adj = holm([0.001, 0.2, 0.01, 0.03])
    order = np.argsort([0.001, 0.2, 0.01, 0.03])
    assert [adj[i] for i in order] == sorted(adj)
    assert adj == pytest.approx([0.004, 0.2, 0.03, 0.06])


def test_bootstrap_ci_defaults_and_seed():
    a = np.array([0.1, 0.4, 0.2, 0.9, 0.5, 0.7, 0.31, 0.12, 0.66, 0.05, 0.83, 0.47, 0.58, 0.29, 0.91])
    b = a + np.array([0.37, 0.05, 0.61, 0.043, 0.093, 0.21, 0.031, 0.117, 0.019, 0.2713, 0.08, -0.037, 0.151, 0.0123,
                      -0.07])
    default = bootstrap_ci(a, b)
    assert default == bootstrap_ci(a, b, n_boot=5000, alpha=0.05, seed=0)
    assert default == bootstrap_ci(a, b)                                  # seeded: repeatable
    assert default != bootstrap_ci(a, b, seed=1)
    assert default != bootstrap_ci(a, b, n_boot=5001)
    lo, hi = default
    assert isinstance(lo, float) and isinstance(hi, float)
    assert lo < float(np.mean(b - a)) < hi


def test_bootstrap_ci_quantile_levels_on_a_two_point_sample():
    # d = [0, 1]: a resample mean is 0, 0.5 or 1 with probabilities 1/4, 1/2, 1/4
    a, b = np.array([0.0, 0.0]), np.array([0.0, 1.0])
    assert bootstrap_ci(a, b) == (0.0, 1.0)                               # alpha 0.05: the 2.5 % and 97.5 % points
    # alpha 0.6: the 30 % point is 0.5 (P(mean = 0) is only 25 %) and the 70 % point is 0.5 (P(mean <= 0.5) = 75 %)
    assert bootstrap_ci(a, b, alpha=0.6) == (0.5, 0.5)


def test_bootstrap_ci_can_draw_every_task_including_the_first():
    # only the first task differs: resamples without it would have mean 0 and the upper bound could not be positive
    a = np.zeros(4)
    b = np.array([1.0, 0.0, 0.0, 0.0])
    lo, hi = bootstrap_ci(a, b)
    assert lo == 0.0 and hi >= 0.5
    # the last task is drawn as well
    lo, hi = bootstrap_ci(a, b[::-1])
    assert lo == 0.0 and hi >= 0.5
    # a constant difference has a degenerate interval
    assert bootstrap_ci(np.zeros(5), np.full(5, 0.25)) == (0.25, 0.25)
