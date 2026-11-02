import copy
import math

from tsbench.score.batch_score import score_batch

TASK = {"tolerance": {"item_rel": 0.02},
        "reference": {"values": [{"input": 3.8, "result": 1000.0}, {"input": 4.0, "result": 2000.0},
                                 {"input": 4.2, "result": 3000.0}, {"input": 4.4, "result": 4000.0}]}}


def answer():
    vals = [dict(v) for v in TASK["reference"]["values"]]
    return {"values": vals, "reason": "r"}


def test_perfect():
    s = score_batch(TASK, answer())
    assert s["correct"] and s["n_correct_items"] == 4 and s["item_accuracy"] == 1.0
    assert s["median_rel_error"] == 0.0 and s["n_missing"] == 0 and s["n_extra"] == 0


def test_within_tolerance_and_input_tolerance():
    a = answer()
    a["values"][0]["result"] = 1015.0
    a["values"][1]["input"] = 4.0 * (1 + 1e-8)
    assert score_batch(TASK, a)["correct"]


def test_one_item_off():
    a = answer()
    a["values"][2]["result"] = 3300.0
    s = score_batch(TASK, a)
    assert not s["correct"] and s["n_correct_items"] == 3 and s["item_accuracy"] == 0.75
    assert math.isclose(s["median_rel_error"], 0.0, abs_tol=1e-12)


def test_median_rel_error():
    a = answer()
    for v, f in zip(a["values"], (1.10, 1.20, 1.0, 1.0), strict=False):
        v["result"] *= f
    s = score_batch(TASK, a)
    assert math.isclose(s["median_rel_error"], 0.05)


def test_missing_item():
    a = answer()
    a["values"].pop(1)
    s = score_batch(TASK, a)
    assert not s["correct"] and s["n_missing"] == 1 and s["n_correct_items"] == 3


def test_extra_item():
    a = answer()
    a["values"].append({"input": 9.9, "result": 1.0})
    s = score_batch(TASK, a)
    assert not s["correct"] and s["n_extra"] == 1 and s["n_correct_items"] == 4
    a2 = answer()
    a2["values"].append(copy.deepcopy(a2["values"][0]))   # duplicate input is extra, too
    assert score_batch(TASK, a2)["n_extra"] == 1


def test_null_result():
    a = answer()
    a["values"][3]["result"] = None
    s = score_batch(TASK, a)
    assert not s["correct"] and s["n_correct_items"] == 3 and s["items"][3]["rel_error"] is None


def test_garbage_output():
    for bad in (None, {}, {"values": "x"}, {"values": [1, None, {"input": "a"}]}):
        s = score_batch(TASK, bad)
        assert not s["correct"] and s["n_correct_items"] == 0 and s["median_rel_error"] is None


def test_order_independent():
    a = answer()
    a["values"].reverse()
    assert score_batch(TASK, a)["correct"]


# ---------- helpers ----------

def test_num_accepts_finite_numbers_only():
    from tsbench.score.batch_score import _num
    assert _num(3) == 3.0 and type(_num(3)) is float and _num(-2.5) == -2.5 and _num(0) == 0.0
    for bad in (True, False, None, "1", [1], float("inf"), float("-inf"), float("nan")):
        assert _num(bad) is None, bad


def test_same_input_is_a_relative_comparison_of_1e_6():
    from tsbench.score.batch_score import INPUT_RTOL, _same_input
    assert INPUT_RTOL == 1e-6
    assert _same_input(0.0, 0.0) is True and _same_input(0, 0) is True
    assert _same_input(0.0, 1e-9) is False and _same_input(1e-9, 0.0) is False   # zero is not close to a small number
    assert _same_input(1e-7, 1.5e-7) is False                                    # relative, not absolute
    assert _same_input(1e6, 1e6 + 0.5) is True and _same_input(1e6, 1e6 + 2.0) is False
    assert _same_input(1e6, 999999.0) is True                                    # exactly 1e-6 relative to the larger
    assert _same_input(-3.8, -3.8000000001) is True and _same_input(-3.8, 3.8) is False
    # the larger of the two magnitudes sets the scale, whichever side it is on
    a, b = 1e6, 1e6 - 0.9999995
    assert _same_input(a, b) is True and _same_input(b, a) is True and _same_input(-a, -b) is True
    assert _same_input(1e-310, 2e-310) is True    # far below any scale: still relative to the numbers themselves


def test_rel_error_is_relative_unless_the_reference_is_zero():
    from tsbench.score.batch_score import _rel_error
    assert _rel_error(110.0, 100.0) == 0.1 and _rel_error(90.0, -100.0) == 1.9
    assert _rel_error(1.5, 1.0) == 0.5 and _rel_error(0.5, 2.0) == 0.75
    assert _rel_error(0.5, 0.0) == 0.5 and _rel_error(-0.5, 0.0) == 0.5 and _rel_error(0.0, 0.0) == 0.0


# ---------- tolerance and result shapes ----------

def _task(values, **kw):
    return {"reference": {"values": values}, **kw}


def test_item_tolerance_comes_from_the_task_default_two_percent():
    vals = [{"input": 1.0, "result": 100.0}]
    off5 = {"values": [{"input": 1.0, "result": 105.0}]}
    assert score_batch(_task(vals, tolerance={"item_rel": 0.1}), off5)["correct"] is True
    assert score_batch(_task(vals, tolerance={"item_rel": 0.01}), off5)["correct"] is False
    for tol in ({}, None, {"item_rel": None}, {"item_rel": 0}, {"other": 0.5}):
        kw = {} if tol is None else {"tolerance": tol}
        assert score_batch(_task(vals, **kw), off5)["correct"] is False, tol
        assert score_batch(_task(vals, **kw), {"values": [{"input": 1.0, "result": 101.9}]})["correct"] is True, tol
        assert score_batch(_task(vals, **kw), {"values": [{"input": 1.0, "result": 102.1}]})["correct"] is False, tol


def test_item_tolerance_edge_is_inclusive():
    vals = [{"input": 1.0, "result": 100.0}]
    s = score_batch(_task(vals), {"values": [{"input": 1.0, "result": 102.0}]})
    assert s["correct"] is True and s["items"][0]["rel_error"] == 0.02


def test_item_tolerance_edge_has_float_slack():
    # 1998.5574 / 1959.37 - 1 is 2 % up to one rounding step: the division gives 0.020000000000000014
    vals = [{"input": 4.0, "result": 1959.37}]
    s = score_batch(_task(vals), {"values": [{"input": 4.0, "result": 1998.5574}]})
    assert s["items"][0]["rel_error"] > 0.02
    assert s["correct"] is True
    over = score_batch(_task(vals), {"values": [{"input": 4.0, "result": 1998.5575}]})
    assert over["correct"] is False


def test_item_rows_of_every_kind():
    vals = [{"input": 1.0, "result": 100.0}, {"input": 2.0, "result": 200.0}, {"input": 3.0, "result": None},
            {"input": 4.0, "result": None}, {"input": 5.0, "result": 50.0}]
    ans = {"values": [{"input": 1.0, "result": 101.0}, {"input": 2.0, "result": "x"}, {"input": 3.0, "result": None},
                      {"input": 4.0, "result": 7.0}]}
    s = score_batch(_task(vals), ans)
    assert s["items"] == [
        {"input": 1.0, "reference": 100.0, "result": 101.0, "rel_error": 0.01, "correct": True, "missing": False},
        {"input": 2.0, "reference": 200.0, "result": "x", "rel_error": None, "correct": False, "missing": False},
        {"input": 3.0, "reference": None, "result": None, "rel_error": 0.0, "correct": True, "missing": False},
        {"input": 4.0, "reference": None, "result": 7.0, "rel_error": None, "correct": False, "missing": False},
        {"input": 5.0, "reference": 50.0, "result": None, "rel_error": None, "correct": False, "missing": True}]
    assert (s["n_items"], s["n_correct_items"], s["n_missing"], s["n_extra"]) == (5, 2, 1, 0)
    assert s["item_accuracy"] == 0.4 and s["correct"] is False
    assert s["median_rel_error"] is None    # at least half of the errors are infinite


def test_one_answer_entry_serves_one_reference_item_only():
    vals = [{"input": 1.0, "result": 10.0}, {"input": 1.0, "result": 10.0}]
    s = score_batch(_task(vals), {"values": [{"input": 1.0, "result": 10.0}]})
    assert s["n_missing"] == 1 and s["n_correct_items"] == 1 and s["n_extra"] == 0 and s["correct"] is False
    s = score_batch(_task(vals), {"values": [{"input": 1.0, "result": 10.0}, {"input": 1.0, "result": 10.0}]})
    assert s["correct"] is True and s["n_extra"] == 0
    # a reference item with a null input never matches (inputs that are no numbers are skipped)
    s = score_batch(_task([{"input": 1.0, "result": 10.0}]), {"values": [{"input": True, "result": 10.0},
                                                                       {"input": 1.0, "result": 10.0}]})
    assert s["n_extra"] == 1 and s["n_correct_items"] == 1


def test_empty_reference_scores_zero_without_dividing():
    s = score_batch(_task([]), {"values": [{"input": 1.0, "result": 1.0}]})
    assert s["n_items"] == 0 and s["item_accuracy"] == 0.0 and s["median_rel_error"] is None
    assert s["correct"] is False and s["n_extra"] == 1 and s["items"] == []


def test_median_of_finite_errors_is_reported():
    vals = [{"input": float(i), "result": 100.0} for i in (1, 2, 3)]
    ans = {"values": [{"input": 1.0, "result": 101.0}, {"input": 2.0, "result": 103.0},
                      {"input": 3.0, "result": 110.0}]}
    s = score_batch(_task(vals), ans)
    assert math.isclose(s["median_rel_error"], 0.03) and s["n_correct_items"] == 1


def test_huge_integers_are_not_numbers_and_do_not_raise():
    a = answer()
    a["values"][0]["result"] = 10**400
    a["values"][1]["input"] = 10**400
    s = score_batch(TASK, a)
    assert not s["correct"] and s["n_correct_items"] == 2 and s["n_missing"] == 1 and s["n_extra"] == 1
    assert s["items"][0]["result"] == 10**400 and s["items"][0]["rel_error"] is None
