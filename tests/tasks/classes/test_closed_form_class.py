"""Tests for the `closed_form` task class (tsbench.tasks.classes.closed_form).

The file name carries `_class`: tests/tasks/oracles/test_closed_form.py holds the oracle, and pytest needs unique
basenames. The draws use a seeded generator of the test's own, not the seeds of the committed task set. The rejection
tests swap the oracle of the rounded bands for a stand-in that fails once, and check that the draw is repeated and
counted.
"""
import dataclasses
import math

import numpy as np
import pytest

from tsbench.tasks import common
from tsbench.tasks.classes import closed_form
from tsbench.tasks.common import Stats, _draw, allowed_bands, round_to_10
from tsbench.tasks.oracles.closed_form import dq_b

SEED = 7


def first_draw(d):
    return _draw(np.random.default_rng(SEED), "closed_form", d)


def rounded_fails_once(bad):
    """dq_b, except that the second call (the rounded bands of the first draw) gives bad(real result, bands)."""
    state = {"n": 0}

    def fn(*bands):
        state["n"] += 1
        return bad(dq_b(*bands), bands) if state["n"] == 2 else dq_b(*bands)
    return fn


def assert_redrawn_once(stats, d, reason):
    assert dict(stats.redraws) == {(f"closed_form/d{d}", reason): 1}
    assert dict(stats.draws) == {f"closed_form/d{d}": 1}


@pytest.mark.parametrize("d", [3, 8])
def test_record_and_draw(d):
    seen, stats = [], Stats()
    rec, (dq, b, c) = closed_form.make_closed_form(np.random.default_rng(SEED), d, seen, stats)
    assert (dq, b, c) == first_draw(d)
    assert (rec["class"], rec["subtype"], rec["d_count"], rec["geometry"]) == ("closed_form", f"d{d}", d, "Oh")
    assert (rec["system"], rec["oracle"], rec["required"], rec["params"]) == (None, "closed_form", ["Dq", "B"], None)
    assert rec["bands_cm1"] == [round_to_10(x) for x in allowed_bands(d, dq, b, c)]
    # the reference is the closed form of the rounded bands, not the drawn point
    cf = dq_b(*rec["bands_cm1"])
    assert rec["reference"] == {"Dq": round(cf.dq_from_quadratic, 2), "B": round(cf.b_from_quadratic, 2), "C": None}
    assert abs(cf.dq_from_quadratic - dq) / dq <= common.ROUNDING_SAFETY * common.TOL_SYNTHETIC["Dq"]
    assert f"d{d}" in rec["prompt"]
    assert all(common.group_thousands(x) in rec["prompt"] for x in rec["bands_cm1"])
    assert seen == [(dq, b)]
    assert dict(stats.draws) == {f"closed_form/d{d}": 1} and not stats.redraws


def test_same_seed_gives_the_same_record():
    a = closed_form.make_closed_form(np.random.default_rng(SEED), 3, [], Stats())
    b = closed_form.make_closed_form(np.random.default_rng(SEED), 3, [], Stats())
    assert a == b


def test_near_duplicate_of_a_seen_draw_is_redrawn():
    dq0, b0, _ = first_draw(3)
    seen, stats = [(dq0, b0)], Stats()
    _, (dq, b, _) = closed_form.make_closed_form(np.random.default_rng(SEED), 3, seen, stats)
    assert not common._close(dq, b, [(dq0, b0)])
    assert seen == [(dq0, b0), (dq, b)]
    assert_redrawn_once(stats, 3, "near-duplicate")


def test_rounded_bands_the_closed_form_rejects_are_redrawn(monkeypatch):
    def raises(_cf, bands):
        raise ValueError(f"need 0 < nu1 < nu2 < nu3, got {bands}")

    monkeypatch.setattr(closed_form, "dq_b", rounded_fails_once(raises))
    stats = Stats()
    _, (dq, b, _) = closed_form.make_closed_form(np.random.default_rng(SEED), 3, [], stats)
    assert_redrawn_once(stats, 3, "rounded bands inconsistent")
    assert (dq, b) != first_draw(3)[:2]


def test_rounded_bands_without_a_real_root_are_redrawn(monkeypatch):
    monkeypatch.setattr(closed_form, "dq_b",
                        rounded_fails_once(lambda cf, _b: dataclasses.replace(cf, dq_from_quadratic=math.nan)))
    stats = Stats()
    closed_form.make_closed_form(np.random.default_rng(SEED), 3, [], stats)
    assert_redrawn_once(stats, 3, "rounded bands inconsistent")


@pytest.mark.parametrize(("field", "factor"), [("dq_from_quadratic", 1.015), ("b_from_quadratic", 1.03),
                                               ("dq_from_nu1", 1.015)])
def test_rounding_that_moves_the_answer_is_redrawn(monkeypatch, field, factor):
    # 1.5 % off in Dq is above ROUNDING_SAFETY * 2 % = 1 %; 3 % off in B is above 0.5 * 5 % = 2.5 %
    monkeypatch.setattr(closed_form, "dq_b", rounded_fails_once(
        lambda cf, _b: dataclasses.replace(cf, **{field: getattr(cf, field) * factor})))
    stats = Stats()
    closed_form.make_closed_form(np.random.default_rng(SEED), 3, [], stats)
    assert_redrawn_once(stats, 3, "rounding moves answer")
