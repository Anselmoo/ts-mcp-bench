"""Tests for the `crossover` task class (tsbench.tasks.classes.crossover).

The draws use a seeded generator of the test's own, not the seeds of the committed task set. The rejection tests
swap one step of the draw for a stand-in that fails once, and check that the draw is repeated and counted.
"""
import numpy as np
import pytest

from tsbench.tasks import common
from tsbench.tasks.classes import crossover
from tsbench.tasks.common import Stats, _compute

SEED = 7


class Comp:
    """The real tanabesugano compute module, except for the attributes given as keyword arguments."""

    def __init__(self, **override):
        self.__dict__.update(override)

    def __getattr__(self, name):
        return getattr(_compute(), name)


def fails_once(real, bad):
    """A function that gives bad(*args) on its first call and real(*args) afterwards."""
    state = {"n": 0}

    def fn(*args, **kwargs):
        state["n"] += 1
        return bad(*args, **kwargs) if state["n"] == 1 else real(*args, **kwargs)
    return fn


def first(d=5):
    return crossover.make_crossover(np.random.default_rng(SEED), d, [], Stats())


def assert_redrawn_once(stats, d, reason):
    assert dict(stats.redraws) == {(f"crossover/d{d}", reason): 1}
    assert dict(stats.draws) == {f"crossover/d{d}": 1}


@pytest.mark.parametrize("d", [4, 5, 6, 7])
def test_record_and_draw(d):
    comp = _compute()
    seen, stats = [], Stats()
    rec = crossover.make_crossover(np.random.default_rng(SEED), d, seen, stats)
    b, c = rec["params"]["B"], rec["params"]["C"]
    assert (rec["class"], rec["subtype"], rec["d_count"], rec["geometry"]) == ("crossover", f"d{d}", d, "Oh")
    assert (rec["system"], rec["oracle"], rec["required"], rec["bands_cm1"]) == (None, "forward_model", ["Dq"], [])
    assert rec["reference"]["B"] is None and rec["reference"]["C"] is None
    assert b == round(b) and c == round(c)
    lo, hi = common.B_RANGE[d]
    assert lo <= b <= hi
    assert common.CB_RANGE_CROSSOVER[0] * b - 0.5 <= c <= common.CB_RANGE_CROSSOVER[1] * b + 0.5
    # the ground term changes once, from high to low spin, at the reference Dq
    x = rec["reference"]["Dq"]
    assert 300 < x < 5900
    weak = comp.reference_ground_term(d, b, c, "high")
    strong = comp.ground_term(comp.compute_point(d, comp.STRONG_FIELD_DQ_CM1, b, c))[0]
    assert weak != strong and len(common.ground_sequence(d, b, c)) == 2
    assert comp.ground_term(comp.compute_point(d, 0.98 * x, b, c))[0] == weak
    assert comp.ground_term(comp.compute_point(d, 1.02 * x, b, c))[0] == strong
    assert f"d{d}" in rec["prompt"] and "Dq" in rec["prompt"]
    assert common.group_thousands(b) in rec["prompt"] and common.group_thousands(c) in rec["prompt"]
    assert seen == [(b, c)]
    assert dict(stats.draws) == {f"crossover/d{d}": 1} and not stats.redraws


def test_same_seed_gives_the_same_record():
    assert first() == first()


def test_both_prompt_templates_are_used():
    starts = {crossover.make_crossover(np.random.default_rng(s), 5, [], Stats())["prompt"][:2] for s in range(12)}
    assert starts == {"At", "An"}


def test_near_duplicate_of_a_seen_draw_is_redrawn():
    p = first()["params"]
    seen, stats = [(p["B"], p["C"])], Stats()
    rec = crossover.make_crossover(np.random.default_rng(SEED), 5, seen, stats)
    assert (rec["params"]["B"], rec["params"]["C"]) != (p["B"], p["C"])
    assert seen == [(p["B"], p["C"]), (rec["params"]["B"], rec["params"]["C"])]
    assert_redrawn_once(stats, 5, "near-duplicate")


def test_draw_without_a_spin_crossover_is_redrawn(monkeypatch):
    comp = _compute()
    unpatched = first()["params"]

    def strong_term(d, b, c, _spin):
        return comp.ground_term(comp.compute_point(d, comp.STRONG_FIELD_DQ_CM1, b, c))[0]

    monkeypatch.setattr(crossover, "_compute",
                        lambda: Comp(reference_ground_term=fails_once(comp.reference_ground_term, strong_term)))
    stats = Stats()
    rec = crossover.make_crossover(np.random.default_rng(SEED), 5, [], stats)
    assert_redrawn_once(stats, 5, "no spin crossover")
    assert rec["params"] != unpatched


def test_draw_with_more_than_one_ground_term_change_is_redrawn(monkeypatch):
    monkeypatch.setattr(crossover, "ground_sequence", fails_once(common.ground_sequence, lambda *_: ["a", "b", "a"]))
    stats = Stats()
    crossover.make_crossover(np.random.default_rng(SEED), 5, [], stats)
    assert_redrawn_once(stats, 5, "more than one ground-term change")


@pytest.mark.parametrize("move", [lambda x: 250.0, lambda x: 300.0, lambda x: 5900.0, lambda x: 6200.0,
                                  lambda x: 0.9 * x, lambda x: 1.1 * x],
                         ids=["below", "at-300", "at-5900", "above", "early", "late"])
def test_crossover_that_is_not_clean_is_redrawn(monkeypatch, move):
    real = _compute().crossover_dq
    monkeypatch.setattr(crossover, "_compute",
                        lambda: Comp(crossover_dq=fails_once(real, lambda *a, **k: move(real(*a, **k)))))
    stats = Stats()
    crossover.make_crossover(np.random.default_rng(SEED), 5, [], stats)
    assert_redrawn_once(stats, 5, "crossover not clean")
