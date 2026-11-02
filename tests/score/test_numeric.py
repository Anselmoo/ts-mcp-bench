"""Tests for src/tsbench/score/numeric.py: correctness of one answer, curve scoring and the traced-number metric."""
from __future__ import annotations

import math

import pytest

from tsbench.score import numeric
from tsbench.score.extract import Transcript


def _task(**kw) -> dict:
    base = {"id": "S-1", "class": "closed_form", "geometry": "Oh", "required": ["Dq", "B"],
            "reference": {"Dq": 1000.0, "B": 800.0, "C": None},
            "tolerance": {"Dq": 0.02, "B": 0.05, "C": 0.10}, "expect_out_of_scope": False}
    base.update(kw)
    return base


def _ans(**kw) -> dict:
    return {**{"Dq": 1000.0, "B": 800.0, "C": None, "out_of_scope": False, "reason": ""}, **kw}


def _on_the_edge(base: float) -> tuple[float, float]:
    """(tol, t): tol close to `base` with tol + _EPS == t exactly, and 1.0 + t - 1.0 == t, so that an answer of 1 + t
    against a reference of 1 has a relative error of exactly tol + _EPS."""
    q = 2.0 ** -52
    for m in range(int((base + numeric._EPS) / q) - 4, int((base + numeric._EPS) / q) + 5):
        t = m * q
        tol = t - numeric._EPS
        if tol + numeric._EPS == t and (1.0 + t) - 1.0 == t:
            return tol, t
    raise AssertionError("no exact edge found")


# ---------- _errors ----------

def test_errors_per_parameter():
    errs = numeric._errors(_task(), _ans(Dq=1010.0, B=760.0, C=5.0))
    assert errs["Dq"] == pytest.approx((10.0, 0.01))
    assert errs["B"] == pytest.approx((40.0, 0.05))
    assert all(math.isnan(x) for x in errs["C"])  # the reference C is null


def test_errors_a_null_answer_does_not_stop_the_later_parameters():
    errs = numeric._errors(_task(), _ans(Dq=None, B=720.0))
    assert all(math.isnan(x) for x in errs["Dq"])
    assert errs["B"] == pytest.approx((80.0, 0.1))
    errs = numeric._errors(_task(reference={"Dq": 1000.0, "B": None, "C": 10.0}), _ans(Dq=1100.0, B=1.0, C=11.0))
    assert errs["Dq"] == pytest.approx((100.0, 0.1)) and math.isnan(errs["B"][0])
    assert errs["C"] == pytest.approx((1.0, 0.1))  # reached after a null reference


def test_errors_zero_reference_gives_zero_or_infinity():
    t = _task(reference={"Dq": 0.0, "B": 0.0, "C": 0.0})
    exact = numeric._errors(t, _ans(Dq=0.0, B=0.0, C=0.0))
    assert exact["Dq"] == (0.0, 0.0) and exact["B"] == (0.0, 0.0) and exact["C"] == (0.0, 0.0)
    off = numeric._errors(t, _ans(Dq=2.0, B=-3.0, C=0.5))
    assert off["Dq"] == (2.0, math.inf) and off["B"] == (3.0, math.inf) and off["C"] == (0.5, math.inf)


def test_errors_reference_one_is_divided_like_any_other():
    errs = numeric._errors(_task(reference={"Dq": 1.0, "B": 1.0, "C": 1.0}), _ans(Dq=1.5, B=1.0, C=0.25))
    assert errs["Dq"] == pytest.approx((0.5, 0.5)) and errs["B"] == (0.0, 0.0)
    assert errs["C"] == pytest.approx((0.75, 0.75))


def test_errors_td_dq_by_absolute_value_only_for_dq():
    t = _task(geometry="Td", reference={"Dq": -500.0, "B": -800.0, "C": None})
    errs = numeric._errors(t, _ans(Dq=500.0, B=800.0))
    assert errs["Dq"] == (0.0, 0.0)
    assert errs["B"] == (1600.0, 2.0)  # B keeps its sign
    assert numeric._errors(_task(reference={"Dq": -500.0, "B": 1.0, "C": None}), _ans(Dq=500.0))["Dq"] == (1000.0, 2.0)


# ---------- score ----------

def test_score_row_carries_answer_and_errors():
    r = numeric.score(_task(), _ans(Dq=1010.0, B=760.0, C=None))
    assert r["correct"] is True and r["unparseable"] is False and r["answer_out_of_scope"] is False
    assert (r["dq"], r["b"], r["c"]) == (1010.0, 760.0, None)
    assert r["abs_err_dq"] == pytest.approx(10.0) and r["rel_err_dq"] == pytest.approx(0.01)
    assert r["abs_err_b"] == pytest.approx(40.0) and r["rel_err_b"] == pytest.approx(0.05)
    assert math.isnan(r["abs_err_c"]) and math.isnan(r["rel_err_c"]) and math.isnan(r["curve_max_rel_err"])
    for key in ("abs_err_DQ", "rel_err_DQ"):
        assert key not in r


def test_score_out_of_scope_flag_must_be_a_real_boolean():
    for odd in ("yes", 1, 0, None, [True]):
        r = numeric.score(_task(), _ans(out_of_scope=odd))
        assert r["answer_out_of_scope"] is None and r["correct"] is False
    assert numeric.score(_task(), _ans(out_of_scope=True))["answer_out_of_scope"] is True
    assert numeric.score(_task(), _ans(out_of_scope=False))["answer_out_of_scope"] is False
    t = _task(expect_out_of_scope=True, required=[])
    assert numeric.score(t, _ans(Dq=None, B=None, out_of_scope=1))["correct"] is False  # 1 is not True


def test_score_tolerance_edge_is_accepted_and_beyond_is_not():
    tol, t = _on_the_edge(0.02)
    task = _task(reference={"Dq": 1.0, "B": 1.0, "C": None}, tolerance={"Dq": tol, "B": 0.05, "C": 0.1})
    assert numeric.score(task, _ans(Dq=1.0 + t, B=1.0))["correct"]  # error == tol + slack
    assert not numeric.score(task, _ans(Dq=1.0 + t + 1e-9, B=1.0))["correct"]
    r = numeric.score(_task(), _ans(Dq=1020.0))  # exactly the tolerance
    assert r["correct"] and r["rel_err_dq"] == pytest.approx(0.02)
    assert not numeric.score(_task(), _ans(Dq=1020.1))["correct"]


def test_score_required_parameter_needs_a_tolerance_that_is_not_null():
    assert not numeric.score(_task(tolerance={"Dq": 0.02}), _ans())["correct"]  # no tolerance for B
    assert not numeric.score(_task(tolerance={"Dq": 0.02, "B": None}), _ans())["correct"]
    assert not numeric.score(_task(tolerance=None), _ans())["correct"]
    assert numeric.score(_task(required=None), _ans())["correct"]  # nothing required


# ---------- score_curve ----------

REF: list[dict[str, float]] = [
    {"dq_over_b": 0.0, "e_over_b": 0.0}, {"dq_over_b": 0.0, "e_over_b": 1.0}, {"dq_over_b": 0.0, "e_over_b": 100.0},
    {"dq_over_b": 2.0, "e_over_b": -10.0}, {"dq_over_b": 2.0, "e_over_b": 5.0}, {"dq_over_b": 2.0, "e_over_b": 20.0}]


def _curve_task(**kw):
    return {"id": "C-1", "answer_schema": "curve", "reference_curve": REF, **kw}


def _pts(x_shift=0.0, e=lambda x, v: v):  # noqa: E731
    return {"points": [{"dq_over_b": p["dq_over_b"] + x_shift, "term": "", "e_over_b": e(p["dq_over_b"], p["e_over_b"])}
                       for p in REF]}


def test_curve_exact_answer_and_blank_rows():
    r = numeric.score_curve(_curve_task(), _pts())
    assert r["correct"] is True and r["curve_max_rel_err"] == 0.0 and r["unparseable"] is False
    none = numeric.score_curve(_curve_task(), None)
    assert none["unparseable"] is True and none["correct"] is False and math.isnan(none["curve_max_rel_err"])


def test_curve_default_tolerances_are_absolute_0_3_or_relative_3_percent():
    t = _curve_task()
    # 100 -> 102.5 is 2.5 % (> 0.3 absolute, within 3 %); a missing tolerance key means the default, not "none"
    assert numeric.score_curve(t, _pts(e=lambda x, v: 102.5 if v == 100.0 else v))["correct"]
    assert not numeric.score_curve(t, _pts(e=lambda x, v: 103.5 if v == 100.0 else v))["correct"]
    # 0 -> 0.25 is within the absolute 0.3; 0 -> 0.35 is not (the reference is 0: no relative test)
    assert numeric.score_curve(t, _pts(e=lambda x, v: 0.25 if v == 0.0 else v))["correct"]
    assert not numeric.score_curve(t, _pts(e=lambda x, v: 0.35 if v == 0.0 else v))["correct"]
    assert (numeric.CURVE_ABS, numeric.CURVE_REL, numeric.CURVE_X_MATCH) == (0.3, 0.03, 0.01)


def test_curve_tolerances_of_the_task_replace_the_defaults():
    wide = _curve_task(tolerance={"curve_abs": 1.0, "curve_rel": 0.2})
    narrow = _curve_task(tolerance={"curve_abs": 0.01, "curve_rel": 0.001})
    pts = _pts(e=lambda x, v: v + 0.5)
    assert numeric.score_curve(wide, pts)["correct"]
    assert not numeric.score_curve(narrow, pts)["correct"]
    # only the absolute tolerance given: the relative default (3 %) still applies; and the other way round
    only_abs = _curve_task(tolerance={"curve_abs": 0.001})
    assert numeric.score_curve(only_abs, _pts(e=lambda x, v: 102.5 if v == 100.0 else v))["correct"]
    assert not numeric.score_curve(only_abs, _pts(e=lambda x, v: 0.25 if v == 0.0 else v))["correct"]
    only_rel = _curve_task(tolerance={"curve_rel": 0.001})
    assert numeric.score_curve(only_rel, _pts(e=lambda x, v: 0.25 if v == 0.0 else v))["correct"]
    assert not numeric.score_curve(only_rel, _pts(e=lambda x, v: 102.5 if v == 100.0 else v))["correct"]


def test_curve_malformed_answers_are_incorrect_with_nan_error():
    t = _curve_task()
    short = {"points": _pts()["points"][:-1]}
    extra = {"points": _pts()["points"] + [{"dq_over_b": 7.0, "term": "", "e_over_b": 1.0}]}  # in no group
    moved = {"points": [dict(p, dq_over_b=p["dq_over_b"] + (0.5 if i == 0 else 0)) for i, p in
                        enumerate(_pts()["points"])]}  # right count, but a group of two and one of four
    for bad in (short, extra, moved, {"points": "x"}, {"points": None}, {}):
        r = numeric.score_curve(t, bad)
        assert r["correct"] is False and r["unparseable"] is False and math.isnan(r["curve_max_rel_err"]), bad


def test_curve_task_without_reference_points_scores_nothing():
    for t in ({"id": "C"}, {"id": "C", "reference_curve": []}, {"id": "C", "reference_curve": None}):
        for pts in ([], [{"dq_over_b": 0.0, "e_over_b": 0.0}]):
            r = numeric.score_curve(t, {"points": pts})
            assert r["correct"] is False and math.isnan(r["curve_max_rel_err"])


def test_curve_points_are_matched_to_a_group_within_one_percent_of_dq_over_b_inclusive():
    t = _curve_task()
    assert numeric.score_curve(t, _pts(x_shift=0.01))["correct"]  # the group at 0 sits exactly on the limit
    assert numeric.score_curve(t, _pts(x_shift=0.0099))["correct"]
    assert not numeric.score_curve(t, _pts(x_shift=0.02))["correct"]


def test_curve_values_are_compared_in_ascending_order_and_term_labels_are_ignored():
    shuffled = {"points": list(reversed(_pts()["points"]))}
    for p in shuffled["points"]:
        p["term"] = "wrong"
    r = numeric.score_curve(_curve_task(), shuffled)
    assert r["correct"] is True and r["curve_max_rel_err"] == 0.0


def test_curve_max_relative_error_cases():
    def err(change):
        return numeric.score_curve(_curve_task(), _pts(e=change))["curve_max_rel_err"]

    assert err(lambda x, v: 1.02 if v == 1.0 else v) == pytest.approx(0.02)       # reference 1: plain division
    assert err(lambda x, v: 105.0 if v == 100.0 else v) == pytest.approx(0.05)
    assert err(lambda x, v: -9.0 if v == -10.0 else v) == pytest.approx(0.1)      # |reference| in the divisor
    assert err(lambda x, v: 0.1 if v == 0.0 else v) == math.inf                    # reference 0, error 0.1
    assert err(lambda x, v: v) == 0.0                                              # reference 0, no error
    assert err(lambda x, v: 0.25 if v == 0.0 else v) == math.inf
    # the largest of all groups wins
    assert err(lambda x, v: {1.0: 1.03, 5.0: 5.5}.get(v, v)) == pytest.approx(0.1)


def test_curve_tol_ratio_is_the_error_in_units_of_the_nearer_tolerance():
    ref = [{"dq_over_b": 0.0, "e_over_b": e} for e in (4.04, 40.0, 0.0)]
    task = {"id": "C", "reference_curve": ref, "tolerance": {"curve_abs": 0.3, "curve_rel": 0.03}}

    def run(shift):
        pts = [{"dq_over_b": 0.0, "term": "", "e_over_b": p["e_over_b"] + s} for p, s in zip(ref, shift, strict=True)]
        return numeric.score_curve(task, {"points": pts})

    r = run([0.29, 0.0, 0.0])  # passes by the absolute tolerance; relative error 0.072 is 2.4 times curve_rel
    assert r["correct"] is True and r["curve_max_rel_err"] == pytest.approx(0.29 / 4.04)
    assert r["curve_tol_ratio"] == pytest.approx(0.29 / 0.3)
    r = run([0.0, 1.2, 0.0])  # passes by the relative tolerance (3 % of 40 = 1.2)
    assert r["correct"] is True and r["curve_tol_ratio"] == pytest.approx(1.0)
    r = run([0.0, 0.0, 0.6])  # reference 0: only the absolute tolerance counts
    assert r["correct"] is False and r["curve_tol_ratio"] == pytest.approx(2.0)
    r = run([0.4, 0.0, 0.0])  # 0.4 > 0.3 abs, 0.099 > 0.03 rel: the nearer one is the absolute
    assert r["correct"] is False and r["curve_tol_ratio"] == pytest.approx(0.4 / 0.3)
    assert run([0.0, 0.0, 0.0])["curve_tol_ratio"] == 0.0
    assert math.isnan(numeric.score_curve(task, None)["curve_tol_ratio"])
    assert math.isnan(numeric.score_curve(task, {"points": []})["curve_tol_ratio"])


def test_curve_exact_edges_of_both_tolerances():
    # absolute edge, reference 0: no relative test can help
    ref0 = [{"dq_over_b": 0.0, "e_over_b": 0.0}]
    t0 = {"id": "C", "reference_curve": ref0, "tolerance": {"curve_abs": 0.3, "curve_rel": 0.03}}
    edge = 0.3 + numeric._EPS
    assert numeric.score_curve(t0, {"points": [{"dq_over_b": 0.0, "e_over_b": edge}]})["correct"]
    assert not numeric.score_curve(t0, {"points": [{"dq_over_b": 0.0, "e_over_b": edge + 1e-9}]})["correct"]
    # relative edge, reference 1: the absolute tolerance is below the error
    tol, t = _on_the_edge(0.03)
    ref1 = [{"dq_over_b": 0.0, "e_over_b": 1.0}]
    t1 = {"id": "C", "reference_curve": ref1, "tolerance": {"curve_abs": 0.001, "curve_rel": tol}}
    assert numeric.score_curve(t1, {"points": [{"dq_over_b": 0.0, "e_over_b": 1.0 + t}]})["correct"]
    assert not numeric.score_curve(t1, {"points": [{"dq_over_b": 0.0, "e_over_b": 1.0 + t + 1e-9}]})["correct"]
    # reference exactly 1 is a normal reference for the relative test (3 % of 1 is above a tiny absolute tolerance)
    assert numeric.score_curve(t1, {"points": [{"dq_over_b": 0.0, "e_over_b": 1.02}]})["correct"]


# ---------- trace ----------

def _transcript(uses, results):
    return Transcript(tool_uses=[{"name": n, "id": i, "input": {}} for n, i in uses],
                      tool_results=[{"tool_use_id": i, "content": c} for i, c in results])


def test_numbers_in_text():
    assert numeric.numbers_in("a 1,234.5, 8.5e2 -3 +4 .5 7. x") == [1234.5, 850.0, 3.0, 4.0, 0.5, 7.0]
    assert numeric.numbers_in("2,033.6 and 12,34") == [2033.6, 12.0, 34.0]
    assert numeric.numbers_in("1e999 2") == [2.0]  # not finite: dropped
    assert numeric.numbers_in("") == []


def test_numbers_in_json_lists_are_not_thousands_groups():
    f = numeric.numbers_in
    assert f('{"residuals_cm1":[-47.46219244517488,109.47128400050133,-61.86]}') == [
        1.0, 47.46219244517488, 109.47128400050133, 61.86]
    assert f('{"fit":[1850,761,3402]}') == [1850.0, 761.0, 3402.0]
    assert f("[850,761,402]") == [850.0, 761.0, 402.0] and f("[0.5,850,761]") == [0.5, 850.0, 761.0]
    assert f("Dq = 2,033.6 and 1,234,567") == [2033.6, 1234567.0]
    assert f("-2,033.6") == [2033.6]


def test_trace_compact_json_list_elements_are_found_separately():
    tr = _transcript([("mcp__x", "m")], [("m", '{"residuals_cm1":[-47.46219244517488,109.47128400050133,-61.86]}'),
                                         ("m", '{"fit":[1850,761,3402]}')])
    assert numeric.trace(_ans(Dq=1850.0, B=761.0, C=109.47), tr) == (3, 3)


def test_trace_unhashable_ids_do_not_raise():
    tr = _transcript([("StructuredOutput", ["x"]), ("Bash", "b")], [(["x"], "Dq = 1000.0"), ({"a": 1}, "B = 800.0")])
    assert numeric.trace(_ans(Dq=1000.0, B=800.0), tr) == (2, 2)


def test_trace_without_a_transcript_reports_only():
    assert numeric.trace(_ans(), None) == (2, 0)
    assert numeric.trace(_ans(C=3.0), None) == (3, 0)
    assert numeric.trace(None, None) == (0, 0)


def test_trace_skips_the_answer_channel_but_nothing_else():
    tr = _transcript([("StructuredOutput", "s"), ("Bash", "b"), ("mcp__x", "m")],
                     [("s", "Dq = 1000.0"),            # the answer channel comes first
                      ("b", "B = 800.0"),
                      (None, "C = 5.5"),               # no id: still a source of numbers
                      ("m", "unrelated 3")])
    assert numeric.trace(_ans(Dq=1000.0, B=800.0, C=5.5), tr) == (3, 2)
    # one source at a time: the answer channel is no source, a result without an id is one
    only_channel = _transcript([("StructuredOutput", "s")], [("s", "Dq = 1000.0")])
    assert numeric.trace(_ans(Dq=1000.0, B=None), only_channel) == (1, 0)
    no_id = _transcript([("StructuredOutput", "s")], [(None, "Dq = 1000.0")])
    assert numeric.trace(_ans(Dq=1000.0, B=None), no_id) == (1, 1)
    # the same numbers in a result of a tool that is not StructuredOutput do count
    tr2 = _transcript([("Structured", "s"), ("structuredoutput", "t"), ("STRUCTUREDOUTPUT", "u")],
                      [("s", "Dq = 1000.0"), ("t", "B = 800.0"), ("u", "C = 5.5")])
    assert numeric.trace(_ans(Dq=1000.0, B=800.0, C=5.5), tr2) == (3, 3)


def test_trace_a_null_parameter_does_not_stop_the_later_ones():
    tr = _transcript([("Bash", "b")], [("b", "B = 800.0 C = 2.5")])
    assert numeric.trace(_ans(Dq=None, B=800.0, C=2.5), tr) == (2, 2)
    assert numeric.trace(_ans(Dq=1000.0, B=None, C=2.5), tr) == (2, 1)


def test_trace_half_percent_edge_is_inclusive():
    assert 0.005 * 200 == 1.0
    tr = _transcript([("Bash", "b")], [("b", "value 201 and 0.0")])
    assert numeric.trace(_ans(Dq=200.0, B=None), tr) == (1, 1)   # exactly 0.5 % away
    assert numeric.trace(_ans(Dq=199.0, B=None), tr) == (1, 0)
    assert numeric.trace(_ans(Dq=0.0, B=None), tr) == (1, 1)     # zero is traced by a zero
    assert numeric.TRACE_RTOL == 0.005


def test_trace_tool_results_without_content():
    tr = Transcript(tool_results=[{"tool_use_id": "b", "content": None}, {"tool_use_id": "c"}])
    assert numeric.trace(_ans(), tr) == (2, 0)
