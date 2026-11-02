"""Tests for the closed-form oracle (tsbench.tasks.oracles.closed_form), with numbers worked out by hand.

Dq = 1000 and B = 800 give nu1 = 10 Dq = 10000 and nu2 + nu3 = 15 B + 30 Dq = 42000. The product follows from
340 Dq^2 - 18 s Dq + nu2 nu3 = 0, so nu2 nu3 = 18 * 42000 * 1000 - 340 * 1000**2 = 416e6, hence nu2 = 16000 and
nu3 = 26000.
"""
import math

import pytest

from tsbench.tasks.oracles.closed_form import dq_b, dq_b_two_band


def disc(nu2: float, nu3: float) -> float:
    """The discriminant of the quadratic in Dq, as dq_b forms it."""
    return (18 * (nu2 + nu3)) ** 2 - 4 * 340 * (nu2 * nu3)


# ----------------------------------------------------------------------------- three bands

def test_three_bands_of_a_consistent_system_give_dq_and_b():
    got = dq_b(10000.0, 16000.0, 26000.0)
    assert got.dq_from_nu1 == 1000.0
    assert got.b_from_nu1 == pytest.approx(800.0)
    assert got.dq_from_quadratic == pytest.approx(1000.0)
    assert got.b_from_quadratic == pytest.approx(800.0)
    assert got.dq_disagreement == pytest.approx(0.0, abs=1e-9)


def test_the_disagreement_is_the_quadratic_dq_minus_the_dq_of_nu1():
    got = dq_b(10500.0, 16000.0, 26000.0)
    assert got.dq_from_nu1 == 1050.0
    assert got.dq_disagreement == pytest.approx(got.dq_from_quadratic - 1050.0)
    assert got.dq_disagreement == pytest.approx(-50.0, abs=0.01)
    assert got.b_from_nu1 == pytest.approx((42000 - 30 * 1050.0) / 15)
    assert got.b_from_quadratic == pytest.approx((42000 - 30 * got.dq_from_quadratic) / 15)


def test_small_positive_bands_are_accepted():
    got = dq_b(0.5, 1.0, 2.0)
    assert got.dq_from_nu1 == 0.05


@pytest.mark.parametrize(
    ("bands", "shown"),
    [
        ((0.0, 1.0, 2.0), "0.0, 1.0, 2.0"),      # nu1 must be above zero
        ((-5.0, 1.0, 2.0), "-5.0, 1.0, 2.0"),
        ((5.0, 5.0, 6.0), "5.0, 5.0, 6.0"),      # strictly ascending
        ((5.0, 6.0, 6.0), "5.0, 6.0, 6.0"),
        ((7.0, 6.0, 8.0), "7.0, 6.0, 8.0"),
    ],
)
def test_bands_that_are_not_strictly_ascending_and_positive_are_refused(bands, shown):
    with pytest.raises(ValueError, match=f"^need 0 < nu1 < nu2 < nu3, got {shown}$"):
        dq_b(*bands)


def test_bands_without_a_real_quadratic_root_report_nan_for_the_quadratic_values():
    # nu2 and nu3 so close that no (Dq, B) reproduces both: the discriminant is negative
    got = dq_b(10000.0, 20000.0, 20100.0)
    assert disc(20000.0, 20100.0) < 0
    assert got.dq_from_nu1 == 1000.0
    assert got.b_from_nu1 == pytest.approx((40100.0 - 30000.0) / 15)
    assert math.isnan(got.dq_from_quadratic)
    assert math.isnan(got.b_from_quadratic)
    assert math.isnan(got.dq_disagreement)


def test_a_double_root_is_still_solved():
    # nu3 chosen so that the discriminant is exactly 0.0: the two roots are the same, 18 s / 680
    nu2, nu3 = 1000.0, 1554.0515781379204
    assert disc(nu2, nu3) == 0.0
    got = dq_b(400.0, nu2, nu3)
    assert got.dq_from_quadratic == pytest.approx(18 * (nu2 + nu3) / 680)
    assert got.b_from_quadratic == pytest.approx((nu2 + nu3 - 30 * got.dq_from_quadratic) / 15)
    assert got.dq_disagreement == pytest.approx(got.dq_from_quadratic - 40.0)


def test_the_root_with_a_negative_b_is_not_a_candidate():
    # the roots are 287.8 and 638.1; the larger one would give B = (17500 - 30 * 638.1) / 15 < 0, although it is
    # the one that lies closer to Dq = nu1 / 10 = 480
    got = dq_b(4800.0, 5000.0, 12500.0)
    assert got.dq_from_quadratic == pytest.approx(287.84, abs=0.01)
    assert got.b_from_quadratic == pytest.approx(590.99, abs=0.01)


def test_a_root_with_b_of_exactly_zero_is_not_a_candidate():
    # s = 15000: the larger root is exactly 500 and B = (15000 - 30 * 500) / 15 = 0
    assert disc(5000.0, 10000.0) == 4.9e9
    got = dq_b(4800.0, 5000.0, 10000.0)
    assert got.dq_from_quadratic == pytest.approx(294.1176, abs=1e-3)
    assert got.b_from_quadratic == pytest.approx(411.7647, abs=1e-3)


def test_a_root_with_a_tiny_positive_b_is_a_candidate():
    # the larger root gives B = 0.5 cm-1 and is the one closest to Dq = 450: a threshold of 1 cm-1 or a 31 Dq
    # instead of 30 Dq would throw it out
    got = dq_b(4500.0, 5000.0, 9989.505)
    assert got.dq_from_quadratic == pytest.approx(499.40, abs=0.01)
    assert 0 < got.b_from_quadratic < 1


def test_the_smaller_root_always_has_a_positive_b():
    # why dq_b has no "no root gives positive B" error to raise: the smaller root is at most 18 s / 680 < s / 30
    for bands in ((1.0, 2.0, 3.0), (1.0, 1.5, 100.0), (10.0, 1000.0, 1001.0), (3.0, 4.0, 4000.0)):
        s = bands[1] + bands[2]
        got = dq_b(*bands)
        assert math.isnan(got.dq_from_quadratic) or (s - 30 * got.dq_from_quadratic) / 15 > 0


# ----------------------------------------------------------------------------- two bands

def test_two_bands_give_dq_from_nu1_and_b_from_the_relation():
    dq, b = dq_b_two_band(10000.0, 16000.0)
    assert dq == 1000.0
    assert b == pytest.approx(800.0)


def test_small_positive_bands_are_accepted_for_two_bands():
    dq, b = dq_b_two_band(0.5, 2.0)
    assert dq == 0.05
    assert b == pytest.approx((2.0 - 0.5) * (2.0 - 1.0) / (3 * (10.0 - 4.5)))


@pytest.mark.parametrize(
    ("bands", "message"),
    [
        ((0.0, 1.0), r"need 0 < nu1 < nu2, got 0.0, 1.0"),
        ((-1.0, 1.0), r"need 0 < nu1 < nu2, got -1.0, 1.0"),
        ((5.0, 5.0), r"need 0 < nu1 < nu2, got 5.0, 5.0"),
        ((6.0, 5.0), r"need 0 < nu1 < nu2, got 6.0, 5.0"),
        ((10000.0, 18000.0), r"nu2 = 1.8 nu1: B undefined"),
        ((1000.0, 2000.0), r"nu2/nu1 = 2.000: no positive B"),       # B is exactly 0
        ((1000.0, 1900.0), r"nu2/nu1 = 1.900: no positive B"),       # 1.8 nu1 < nu2 < 2 nu1: B is negative
    ],
)
def test_two_bands_that_cannot_give_a_positive_b_are_refused(bands, message):
    with pytest.raises(ValueError, match=f"^{message}$"):
        dq_b_two_band(*bands)
