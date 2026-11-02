"""Tests for the `numerical` task class (tsbench.tasks.classes.numerical).

The draws use a seeded generator of the test's own, not the seeds of the committed task set. The rejection tests
swap one step of the draw for a stand-in that fails once, and check that the draw is repeated and counted.
"""
import numpy as np
import pytest

from tsbench.tasks import common
from tsbench.tasks.classes import numerical
from tsbench.tasks.common import Stats, _compute, _draw, allowed_bands, round_to_10

SEED = 7


class Comp:
    """The real tanabesugano compute module, except for the attributes given as keyword arguments."""

    def __init__(self, **override):
        self.__dict__.update(override)

    def __getattr__(self, name):
        return getattr(_compute(), name)


def first_draw(d):
    return _draw(np.random.default_rng(SEED), "numerical", d)


def fails_once(real, bad):
    """A function that gives bad(*args) on its first call and real(*args) afterwards."""
    state = {"n": 0}

    def fn(*args, **kwargs):
        state["n"] += 1
        return bad(*args, **kwargs) if state["n"] == 1 else real(*args, **kwargs)
    return fn


def assert_redrawn_once(stats, d, reason):
    assert dict(stats.redraws) == {(f"numerical/d{d}", reason): 1}
    assert dict(stats.draws) == {f"numerical/d{d}": 1}


@pytest.mark.parametrize("d", [2, 7])
def test_record_and_draw(d):
    seen, stats = [], Stats()
    rec, (dq, b, c) = numerical.make_numerical(np.random.default_rng(SEED), d, seen, stats)
    assert (rec["class"], rec["subtype"], rec["d_count"], rec["geometry"]) == ("numerical", f"d{d}", d, "Oh")
    assert (rec["system"], rec["oracle"], rec["required"], rec["expect_out_of_scope"]) == (
        None, "forward_model", ["Dq", "B"], False)
    assert rec["reference"] == {"Dq": dq, "B": b, "C": None}
    assert rec["tolerance"] == {"Dq": 0.02, "B": 0.05, "C": 0.10}
    assert rec["answer_schema"] == "fit"
    # the bands are the three allowed bands of the drawn point, rounded to 10 cm-1
    assert rec["bands_cm1"] == [round_to_10(x) for x in allowed_bands(d, dq, b, c)]
    assert len(rec["bands_cm1"]) == 3 and all(x % 10 == 0 for x in rec["bands_cm1"])
    # the draw lies in the class range and C/B in the textbook range
    (dq_lo, dq_hi), (b_lo, b_hi) = common.RANGES[("numerical", d)]
    assert dq_lo <= dq <= dq_hi and b_lo <= b <= b_hi
    assert common.CB_RANGE[0] * b - 0.5 <= c <= common.CB_RANGE[1] * b + 0.5
    # the prompt names the d count and every band
    assert f"d{d}" in rec["prompt"]
    assert all(common.group_thousands(x) in rec["prompt"] for x in rec["bands_cm1"])
    assert seen == [(dq, b)]
    assert dict(stats.draws) == {f"numerical/d{d}": 1}


@pytest.mark.parametrize("d", [2, 7])
def test_same_seed_gives_the_same_record(d):
    a = numerical.make_numerical(np.random.default_rng(SEED), d, [], Stats())
    b = numerical.make_numerical(np.random.default_rng(SEED), d, [], Stats())
    assert a == b


def test_d7_draw_is_high_spin_with_margin():
    comp = _compute()
    _, (dq, b, c) = numerical.make_numerical(np.random.default_rng(SEED), 7, [], Stats())
    strong = comp.ground_term(comp.compute_point(7, comp.STRONG_FIELD_DQ_CM1, b, c))[0]
    assert comp.ground_term(comp.compute_point(7, dq, b, c))[0] != strong
    assert dq <= (1 - common.HIGH_SPIN_MARGIN) * comp.crossover_dq(7, b, c, strong)


def test_near_duplicate_of_a_seen_draw_is_redrawn():
    dq0, b0, _ = first_draw(2)
    seen, stats = [(dq0, b0)], Stats()
    rec, (dq, b, _) = numerical.make_numerical(np.random.default_rng(SEED), 2, seen, stats)
    assert (dq, b) != (dq0, b0)
    assert not common._close(dq, b, [(dq0, b0)])
    assert rec["reference"]["Dq"] == dq
    assert seen == [(dq0, b0), (dq, b)]
    assert_redrawn_once(stats, 2, "near-duplicate")


def test_d7_draw_with_the_strong_field_ground_term_is_redrawn(monkeypatch):
    real = _compute().ground_term
    calls = {"n": 0}

    def same_twice(*args):
        # a draw checks two ground terms (strong field, then its own): make them equal for the first draw
        calls["n"] += 1
        return ("same",) if calls["n"] <= 2 else real(*args)

    monkeypatch.setattr(numerical, "_compute", lambda: Comp(ground_term=same_twice))
    seen, stats = [], Stats()
    rec, (dq, b, _) = numerical.make_numerical(np.random.default_rng(SEED), 7, seen, stats)
    assert_redrawn_once(stats, 7, "not high-spin with margin")
    assert (dq, b) != first_draw(7)[:2]
    assert seen == [(dq, b)]


def test_d7_draw_too_close_to_the_crossover_is_redrawn(monkeypatch):
    real = _compute().crossover_dq
    # crossover 10 % above the first draw: Dq is below it, but not by the required 15 %
    close = first_draw(7)[0] / 0.9
    monkeypatch.setattr(numerical, "_compute", lambda: Comp(crossover_dq=fails_once(real, lambda *_: close)))
    stats = Stats()
    numerical.make_numerical(np.random.default_rng(SEED), 7, [], stats)
    assert_redrawn_once(stats, 7, "not high-spin with margin")


def test_failed_fit_is_redrawn(monkeypatch):
    real = _compute().fit_spectrum

    def raises(*_a, **_k):
        raise ValueError("no fit")

    monkeypatch.setattr(numerical, "_compute", lambda: Comp(fit_spectrum=fails_once(real, raises)))
    stats = Stats()
    rec, (dq, b, _) = numerical.make_numerical(np.random.default_rng(SEED), 2, [], stats)
    assert_redrawn_once(stats, 2, "fit_spectrum failed")
    assert rec["reference"]["Dq"] == dq


@pytest.mark.parametrize("wrong", [{"Dq": 1.5, "B": 1.0}, {"Dq": 1.0, "B": 1.5}], ids=["Dq", "B"])
def test_fit_that_does_not_recover_the_draw_is_redrawn(monkeypatch, wrong):
    real = _compute().fit_spectrum

    def off(d, bands, C, spin_state):
        fit = real(d, bands, C=C, spin_state=spin_state)
        return type("Fit", (), {"Dq": fit.Dq * wrong["Dq"], "B": fit.B * wrong["B"]})()

    monkeypatch.setattr(numerical, "_compute", lambda: Comp(fit_spectrum=fails_once(real, off)))
    stats = Stats()
    numerical.make_numerical(np.random.default_rng(SEED), 2, [], stats)
    assert_redrawn_once(stats, 2, "fit_spectrum does not recover")


@pytest.mark.parametrize("wrong", [(1.015, 1.0), (1.0, 1.03)], ids=["Dq", "B"])
def test_rounding_that_moves_the_answer_is_redrawn(monkeypatch, wrong):
    real = numerical.invert
    # 1.5 % off in Dq is above ROUNDING_SAFETY * 2 % = 1 % (and below the 2 % tolerance itself);
    # 3 % off in B is above 0.5 * 5 % = 2.5 % (and below 5 %)
    monkeypatch.setattr(numerical, "invert",
                        fails_once(real, lambda d, bands, c, x0: (x0[0] * wrong[0], x0[1] * wrong[1])))
    stats = Stats()
    numerical.make_numerical(np.random.default_rng(SEED), 2, [], stats)
    assert_redrawn_once(stats, 2, "rounding moves answer")
