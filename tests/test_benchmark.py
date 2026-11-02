"""Tests that need no network and no LLM. Run: python -m pytest tests -q"""
import math

import numpy as np
import pytest

from tsbench.stats.analysis import bootstrap_ci, holm, mcnemar_exact, paired_majority
from tsbench.tasks.oracles.closed_form import dq_b


def test_mcnemar_known_value():
    # b=10, c=2: two-sided exact p = 2 * P(X<=2 | n=12, 0.5) = 0.0386
    assert mcnemar_exact(10, 2) == pytest.approx(0.0386, abs=1e-4)
    assert mcnemar_exact(0, 0) == 1.0
    assert mcnemar_exact(5, 5) == 1.0


def test_holm_monotone_and_bounded():
    adj = holm([0.01, 0.04, 0.03])
    assert adj == pytest.approx([0.03, 0.06, 0.06])


def test_paired_majority_counts():
    a = np.array([0.0, 0.2, 1.0, 1.0])
    b = np.array([1.0, 0.8, 1.0, 0.0])
    assert paired_majority(a, b)[:2] == (1, 2)


def test_bootstrap_ci_contains_mean():
    a = np.zeros(30)
    b = np.full(30, 0.5)
    lo, hi = bootstrap_ci(a, b)
    assert lo <= 0.5 <= hi


@pytest.mark.parametrize("dq,b", [(1700, 700), (860, 940), (1230, 640)])
def test_closed_form_roundtrip_against_solver(dq, b):
    ts = pytest.importorskip("tanabesugano.mcp._compute")
    for d, mult in ((3, "4"), (8, "3")):
        pt = ts.compute_point(d, dq, b, 4000.0)
        ground = min(min(v) for v in pt.values())
        lv = sorted(e - ground for k, v in pt.items() if k.startswith(mult + "_") for e in v)
        nu = [x for x in lv if x > 1e-6][:3]
        cf = dq_b(*nu)
        assert cf.dq_from_quadratic == pytest.approx(dq, abs=0.1)
        assert cf.b_from_quadratic == pytest.approx(b, abs=0.1)


def test_inconsistent_bands_reported_not_repaired():
    cf = dq_b(17400, 24700, 36600)  # [Cr(H2O)6]3+ literature row
    assert math.isnan(cf.dq_from_quadratic)
