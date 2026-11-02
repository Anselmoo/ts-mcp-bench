"""The shared helpers of the task generator: rounding, number format, draws, near duplicates, bookkeeping, term labels,
level lists and inversion."""
from __future__ import annotations

from collections import Counter
from enum import Enum
from types import SimpleNamespace

import pytest

from tsbench.tasks import common
from tsbench.tasks.classes import batch

NBSP = " "


def test_round_to_10_rounds_half_up_to_tens():
    assert common.round_to_10(14.9) == 10.0
    assert common.round_to_10(15.0) == 20.0
    assert isinstance(common.round_to_10(8514.0), float)


def test_group_thousands_uses_a_no_break_space():
    assert common.group_thousands(8510.4) == f"8{NBSP}510"
    assert common.group_thousands(999) == "999"


def test_relative_error_is_the_absolute_difference_over_the_reference():
    assert common.relative_error(90.0, 100.0) == pytest.approx(0.1)
    assert common.relative_error(110.0, -100.0) == pytest.approx(2.1)


def test_the_batch_class_uses_the_shared_group_thousands():
    assert batch.group_thousands is common.group_thousands


def test_the_pairing_helper_returns_the_electron_count_of_a_configuration():
    from tsbench.tasks.classes import pairing

    assert pairing._d_count_of("d3") == 3


# ----------------------------------------------------------------------------- draws and near duplicates

class MidpointRng:
    """A generator that draws the middle of every range."""

    def uniform(self, lo, hi):
        return (lo + hi) / 2


def test_draw_returns_rounded_dq_and_b_and_c_from_the_ratio():
    # closed_form d3: Dq 1200-2300, B 560-900, C/B 4.0-4.8; the middle is Dq 1750, B 730, C = 4.4 * 730
    assert common._draw(MidpointRng(), "closed_form", 3) == (1750.0, 730.0, 3212.0)


def test_draw_refuses_a_b_that_reaches_the_free_ion_value(monkeypatch):
    monkeypatch.setitem(common.FREE_ION_B, 3, 730.0)
    with pytest.raises(AssertionError, match=r"\('closed_form', 3, 730\.0\)"):
        common._draw(MidpointRng(), "closed_form", 3)
    monkeypatch.setitem(common.FREE_ION_B, 3, 730.5)
    assert common._draw(MidpointRng(), "closed_form", 3)[1] == 730.0


SEEN = [(1000.0, 500.0)]


@pytest.mark.parametrize(
    ("dq", "b", "expected"),
    [
        (1000.0, 500.0, True),
        (1029.0, 519.0, True),
        (971.0, 481.0, True),
        (1030.0, 500.0, False),   # exactly 3 % in Dq is not close
        (1000.0, 520.0, False),   # exactly 4 % in B is not close
        (1035.0, 500.0, False),   # 3.5 % in Dq: inside the 4 % limit of B, outside the 3 % limit of Dq
        (1000.0, 530.0, False),
        (2000.0, 500.0, False),
    ],
)
def test_close_means_within_3_percent_in_dq_and_4_percent_in_b(dq, b, expected):
    assert common._close(dq, b, SEEN) is expected


def test_close_looks_at_every_earlier_draw():
    assert common._close(2000.0, 700.0, [(1000.0, 500.0), (2010.0, 705.0)]) is True
    assert common._close(2000.0, 700.0, []) is False


# ----------------------------------------------------------------------------- bookkeeping

def test_overlap_counts_the_confirmatory_systems_that_are_fixed_pilot_systems():
    rows = [{"system": "Al2O3:Cr3+"}, {"system": "K3[Fe(CN)6]"}, {"system": "NiO"}]
    assert common._overlap_with_fixed_pilot(rows) == {"checked": True, "fixed_pilot_systems": 2,
                                                      "confirmatory_in_fixed_pilot": 1}
    assert common._overlap_with_fixed_pilot([]) == {"checked": True, "fixed_pilot_systems": 2,
                                                    "confirmatory_in_fixed_pilot": 0}


def test_stats_start_empty_and_do_not_share_state():
    a, b = common.Stats(), common.Stats()
    assert (a.draws, a.redraws) == (Counter(), Counter())
    assert a.racah_c_fit == []
    assert (a.experimental, a.fixed_pilot_overlap, a.literature_all, a.literature_new) == ({}, {}, {}, {})
    a.experimental["x"] = 1
    a.racah_c_fit.append({})
    assert b.experimental == {} and b.racah_c_fit == []


def test_stats_count_every_accepted_and_every_rejected_draw():
    s = common.Stats()
    for _ in range(3):
        s.accept("numerical:3")
    s.reject("numerical:3", "near duplicate")
    s.reject("numerical:3", "near duplicate")
    s.reject("numerical:3", "rounding")
    assert s.draws == {"numerical:3": 3}
    assert s.redraws == {("numerical:3", "near duplicate"): 2, ("numerical:3", "rounding"): 1}


# ----------------------------------------------------------------------------- term labels and level lists

class Key(Enum):
    T1 = "3_T_1"
    E = "2_E"
    A1 = "1_A_1"


def fake_compute(points=None, ground=None, **extra):
    """A stand-in for tanabesugano.mcp._compute. compute_point and ground_term log their arguments."""
    log = []

    def compute_point(d, dq, b, c):
        log.append((d, dq, b, c))
        return points

    return SimpleNamespace(compute_point=compute_point, ground_term=ground, log=log, **extra)


def patch_compute(monkeypatch, comp):
    monkeypatch.setattr(common, "_compute", lambda: comp)
    return comp.log


@pytest.mark.parametrize(("key", "label"), [(Key.T1, "3T1g"), ("2_E", "2Eg"), (Key.A1, "1A1g"), ("2_T_2", "2T2g")])
def test_term_label_takes_enum_members_and_plain_keys(key, label):
    assert common.term_label(key) == label


def test_excited_levels_are_sorted_labelled_and_divided_by_b(monkeypatch):
    comp = fake_compute({Key.E: [150.0, 130.0], Key.T1: [100.0, 190.0]})
    log = patch_compute(monkeypatch, comp)
    assert common.excited_levels(3, 1000.0, 10.0, 40.0) == [(3.0, "2Eg"), (5.0, "2Eg"), (9.0, "3T1g")]
    assert log == [(3, 1000.0, 10.0, 40.0)]


def test_excited_levels_with_equal_energies_are_ordered_by_their_key_text(monkeypatch):
    patch_compute(monkeypatch, fake_compute({Key.T1: [100.0, 150.0], Key.E: [150.0]}))
    assert common.excited_levels(3, 1.0, 10.0, 1.0) == [(5.0, "2Eg"), (5.0, "3T1g")]


def test_excited_levels_accept_plain_string_keys(monkeypatch):
    patch_compute(monkeypatch, fake_compute({"3_T_1": [100.0, 150.0], "2_E": [150.0]}))
    assert common.excited_levels(3, 1.0, 10.0, 1.0) == [(5.0, "2Eg"), (5.0, "3T1g")]


@pytest.mark.parametrize(
    ("energies", "kept"),
    [
        ([100.0, 100.0, 120.0], [2.0]),           # a copy of the ground level goes, even when the ground is positive
        ([0.0, 1e-6, 5.0], [0.5]),                # exactly 1e-6 above a ground of 0 is a copy
        ([0.0, 1.5e-6, 5.0], [0.15e-6, 0.5]),     # just above the limit is a level
        ([0.0, 0.5, 5.0], [0.05, 0.5]),
        ([1000.0, 1000.00001, 1010.0], [1.0]),    # the limit grows with the size of the ground level: 1e-6 * 1000
        ([1000.0, 1000.002, 1010.0], [0.0002, 1.0]),
    ],
)
def test_excited_levels_drop_copies_of_the_ground_level(monkeypatch, energies, kept):
    patch_compute(monkeypatch, fake_compute({Key.E: energies}))
    got = [e for e, _ in common.excited_levels(3, 1.0, 10.0, 1.0)]
    assert got == pytest.approx(kept, rel=1e-6, abs=0)


def ground_by_dq(split, below, above):
    return lambda pt: (below if pt < split else above, 0.0)


def test_ground_sequence_walks_dq_in_steps_of_20_and_merges_repeats(monkeypatch):
    seen = []
    comp = SimpleNamespace(STRONG_FIELD_DQ_CM1=100.0,
                           compute_point=lambda d, dq, b, c: seen.append((d, dq, b, c)) or dq,
                           ground_term=ground_by_dq(50.0, Key.T1, Key.A1))
    monkeypatch.setattr(common, "_compute", lambda: comp)
    assert common.ground_sequence(6, 800.0, 3500.0) == ["3_T_1", "1_A_1"]
    assert seen == [(6, dq, 800.0, 3500.0) for dq in (20.0, 40.0, 60.0, 80.0)]
    assert all(type(dq) is float for _, dq, _, _ in seen)


def test_ground_sequence_takes_another_step(monkeypatch):
    seen = []
    comp = SimpleNamespace(STRONG_FIELD_DQ_CM1=100.0,
                           compute_point=lambda d, dq, b, c: seen.append(dq) or dq,
                           ground_term=ground_by_dq(60.0, Key.T1, Key.A1))
    monkeypatch.setattr(common, "_compute", lambda: comp)
    assert common.ground_sequence(6, 800.0, 3500.0, step=25.0) == ["3_T_1", "1_A_1"]
    assert seen == [25.0, 50.0, 75.0]


def test_ground_sequence_keeps_a_term_that_comes_back(monkeypatch):
    order = {20.0: Key.T1, 40.0: Key.E, 60.0: Key.E, 80.0: Key.T1}
    comp = SimpleNamespace(STRONG_FIELD_DQ_CM1=100.0, compute_point=lambda d, dq, b, c: dq,
                           ground_term=lambda dq: (order[dq],))
    monkeypatch.setattr(common, "_compute", lambda: comp)
    assert common.ground_sequence(6, 800.0, 3500.0) == ["3_T_1", "2_E", "3_T_1"]


def test_ground_sequence_accepts_plain_string_keys(monkeypatch):
    comp = SimpleNamespace(STRONG_FIELD_DQ_CM1=100.0, compute_point=lambda d, dq, b, c: dq,
                           ground_term=lambda dq: ("3_T_1" if dq < 50 else "1_A_1", 0.0))
    monkeypatch.setattr(common, "_compute", lambda: comp)
    assert common.ground_sequence(6, 800.0, 3500.0) == ["3_T_1", "1_A_1"]


# ----------------------------------------------------------------------------- inversion

def linear_levels(d, dq, b, c):
    """Levels that are linear in the parameters, with more than three allowed bands and more than one forbidden one."""
    return [10 * dq, 20 * dq + b, 30 * dq + 2 * b, 1e9, 2e9], [(3 * c + dq, "x"), (9e9, "y")]


TRUTH = (1000.0, 800.0, 3500.0)
OBSERVED_ALLOWED = [10000.0, 20800.0, 31600.0]   # 10 Dq, 20 Dq + B, 30 Dq + 2 B
OBSERVED_FORBIDDEN = [11500.0]                   # 3 C + Dq


@pytest.fixture
def spy(monkeypatch):
    """Log every call of least_squares (x0 and keyword arguments) and pass it on."""
    calls = []
    real = common.least_squares

    def wrapper(fun, x0, **kw):
        calls.append((x0, kw))
        return real(fun, x0, **kw)

    monkeypatch.setattr(common, "least_squares", wrapper)
    monkeypatch.setattr(common, "_levels", linear_levels)
    return calls


def test_invert_finds_dq_and_b_from_the_first_three_allowed_bands(spy):
    got = common.invert(3, OBSERVED_ALLOWED, 3500.0, [900, 700])
    assert got == pytest.approx(TRUTH[:2], rel=1e-6)
    ((x0, kw),) = spy
    assert x0.dtype == float and list(x0) == [900.0, 700.0]
    assert kw["method"] == "lm"
    assert list(kw["x_scale"]) == [1000.0, 1000.0]


def test_invert_with_c_also_fits_c_from_the_first_forbidden_band(spy):
    # the fixed C of 3000 is wrong on purpose: only a fitted C reaches the truth
    got = common.invert(3, OBSERVED_ALLOWED, 3000.0, [900, 700, 3000], with_c=True,
                        observed_forbidden=OBSERVED_FORBIDDEN)
    assert got == pytest.approx(TRUTH, rel=1e-6)
    ((x0, kw),) = spy
    assert kw["method"] == "lm" and list(kw["x_scale"]) == [1000.0, 1000.0, 4000.0]


def test_invert_without_c_keeps_c_fixed_and_ignores_the_forbidden_bands(spy):
    got = common.invert(3, OBSERVED_ALLOWED, 3500.0, [900, 700], observed_forbidden=[0.0])
    assert got == pytest.approx(TRUTH[:2], rel=1e-6)
    assert len(got) == 2


def test_relative_error_of_a_negative_reference_uses_its_size():
    assert common.relative_error(-90.0, -100.0) == pytest.approx(0.1)
