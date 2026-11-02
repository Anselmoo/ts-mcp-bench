from __future__ import annotations

import copy
import math

from tsbench.run import fake_cli
from tsbench.score.diagram_score import score_diagram
from tsbench.score.score import score_transcript

GRID = [0.5 * i for i in range(9)]


def task():
    levels = [[0.0, 1.0 + i, 5.0 + i, 10.0 + i, 20.0 + i, 40.0 + i] for i in range(9)]
    labels = [["a", "b", "c", "d", "e", "f"]] * 9
    return {"reference": {"grid": GRID, "levels": levels, "labels": labels},
            "tolerance": {"curve_abs": 0.3, "curve_rel": 0.03, "item_accuracy_min": 0.95}, "answer_schema": "diagram"}


def answer(t, scale=None, drop=None, shuffle=False):
    pts = []
    for i, (x, lv) in enumerate(zip(t["reference"]["grid"], t["reference"]["levels"], strict=False)):
        if drop is not None and i == drop:
            continue
        items = [{"term": f"t{j}", "e_over_b": e * (scale(i, j) if scale else 1.0)} for j, e in enumerate(lv)]
        pts.append({"dq_over_b": x, "levels": items[::-1] if shuffle else items})
    return {"points": pts, "image_path": None, "image_sha256": None, "reason": "r"}


def test_exact_answer_is_correct_and_order_does_not_matter():
    t = task()
    for shuffle in (False, True):
        s = score_diagram(t, answer(t, shuffle=shuffle))
        assert s["correct"] and s["item_accuracy"] == 1.0 and s["n_correct_items"] == 54 and s["rms_e_over_b"] == 0.0


def test_tolerance_is_three_percent_or_point_three():
    t = task()
    assert score_diagram(t, answer(t, scale=lambda i, j: 1.029))["item_accuracy"] == 1.0
    s = score_diagram(t, answer(t, scale=lambda i, j: 1.05 if j == 5 else 1.0))   # 40+ * 5 % off: wrong on 9 values
    assert s["n_correct_items"] == 45 and not s["correct"]
    near = answer(t)
    near["points"][0]["levels"][1]["e_over_b"] += 0.29   # absolute rule on a small value
    assert score_diagram(t, near)["item_accuracy"] == 1.0


def test_threshold_is_two_wrong_values_of_54():
    t = task()
    a = answer(t)
    for i in range(2):
        a["points"][i]["levels"][5]["e_over_b"] *= 2
    assert score_diagram(t, a)["n_correct_items"] == 52 and score_diagram(t, a)["correct"]
    a["points"][2]["levels"][5]["e_over_b"] *= 2
    assert not score_diagram(t, a)["correct"]


def test_missing_or_duplicated_point_and_short_levels_count_as_wrong():
    t = task()
    assert score_diagram(t, answer(t, drop=3))["n_correct_items"] == 48
    dup = answer(t)
    dup["points"].append(copy.deepcopy(dup["points"][0]))
    assert score_diagram(t, dup)["n_correct_items"] == 48
    short = answer(t)
    short["points"][4]["levels"] = short["points"][4]["levels"][:4]
    assert score_diagram(t, short)["n_correct_items"] == 52
    extra = answer(t)
    extra["points"][4]["levels"].append({"term": "x", "e_over_b": 99.0})
    assert score_diagram(t, extra)["item_accuracy"] == 1.0
    assert abs(score_diagram(t, answer(t, drop=3))["rms_e_over_b"]) == 0.0


def test_garbage_does_not_raise():
    t = task()
    for bad in (None, {}, {"points": "x"}, {"points": [None, 3, {"levels": 1}]},
                {"points": [{"dq_over_b": "0", "levels": [{"e_over_b": "1", "term": 3}]}]},
                {"points": [{"dq_over_b": 0.0, "levels": [{"e_over_b": True, "term": None}, 5]}]}):
        s = score_diagram(t, bad)
        assert s["correct"] is False and s["n_correct_items"] <= 9
    assert math.isnan(score_diagram(t, None)["rms_e_over_b"])


def test_labels_are_informational():
    t = task()
    t["reference"]["labels"] = [["5T2g", "5Eg", "3T1g", "3T1g'", "1A1g", "2Eg"]] * 9
    a = answer(t)
    for p in a["points"]:
        for lv, name in zip(p["levels"], ["5T2", "5Eg", "3T1", "3T1g", "1A1g", "wrong"], strict=False):
            lv["term"] = name
    s = score_diagram(t, a)
    assert s["correct"] and math.isclose(s["label_accuracy"], 45 / 54)


def test_labels_of_coincident_levels_count_as_a_set():
    t = task()
    t["reference"]["levels"] = [[0.0, 0.0, 5.0, 5.0, 5.0, 9.0]] * 9
    t["reference"]["labels"] = [["5Eg", "5T2g", "3T1g", "3Eg", "3T2g", "3A2g"]] * 9
    a = answer(t)
    for p in a["points"]:  # each coincident run in another order; the last label is wrong
        for lv, name in zip(p["levels"], ["5T2g", "5Eg", "3T2g", "3T1g", "3Eg", "3T1g"], strict=False):
            lv["term"] = name
    s = score_diagram(t, a)
    assert s["correct"] and math.isclose(s["label_accuracy"], 45 / 54)


def test_a_label_repeated_in_a_coincident_run_counts_once_per_reference_member():
    t = task()
    t["reference"]["levels"] = [[0.0, 0.0, 5.0, 5.0, 5.0, 9.0]] * 9
    t["reference"]["labels"] = [["5Eg", "5T2g", "3T1g", "3T1g", "3T2g", "3A2g"]] * 9
    a = answer(t)
    for p in a["points"]:  # three times 3T1g where the reference has it twice
        for lv, name in zip(p["levels"], ["5Eg", "5T2g", "3T1g", "3T1g", "3T1g", "3A2g"], strict=False):
            lv["term"] = name
    assert math.isclose(score_diagram(t, a)["label_accuracy"], 45 / 54)


def test_router_and_fake_answers_on_real_tasks():
    from types import SimpleNamespace

    from tsbench.tasks import load
    t = next(r for r in load("pilot") if r["class"] == "diagram")
    for ok in (True, False):
        ans = fake_cli.answer_for(t, ok, "diagram")
        tr = SimpleNamespace(result={"structured_output": ans}, result_text="")
        row, parsed = score_transcript(t, tr)
        assert row["correct"] is ok and parsed is not None
        assert "rms_e_over_b" in row and "label_accuracy" in row and not math.isnan(row["item_accuracy"])
    wrong_shape = fake_cli.answer_for(t, True)   # no schema given: a fit-shaped answer
    row, parsed = score_transcript(t, SimpleNamespace(result={"structured_output": wrong_shape}, result_text=""))
    assert row["correct"] is False and parsed is None


# ---------- helpers: labels, level order ----------

def test_label_is_normalised_for_comparison():
    from tsbench.score.diagram_score import _label
    assert _label(" 3T1g' ") == "3t1" and _label("5 E g") == "5e" and _label("1A1g″") == "1a1"
    assert _label("3T1g′") == "3t1"
    assert _label("Gg") == "" and _label("") == "" and _label("5X") == "5x"
    assert _label(None) == "" and _label(3) == "" and _label(["g"]) == ""


def test_levels_are_sorted_by_energy_and_unreadable_energies_come_last():
    from tsbench.score.diagram_score import _levels
    point = {"levels": [{"e_over_b": 5.0, "term": "B"}, {"e_over_b": "x", "term": "n1"},
                        {"e_over_b": -1.0, "term": "A"}, "junk", {"e_over_b": None, "term": "n2"},
                        {"e_over_b": 0.0, "term": "Z"}, {"e_over_b": True, "term": "n3"},
                        {"e_over_b": -1.0, "term": "A2"}]}
    got = _levels(point)
    assert got[:4] == [(-1.0, "a"), (-1.0, "a2"), (0.0, "z"), (5.0, "b")]
    assert sorted(lab for e, lab in got[4:]) == ["n1", "n2", "n3"] and all(e is None for e, _ in got[4:])
    assert _levels({"levels": [{"e_over_b": 2.0}, {"e_over_b": 1.0, "term": 4}]}) == [(1.0, ""), (2.0, "")]


def test_levels_of_something_that_is_no_point():
    from tsbench.score.diagram_score import _levels
    for odd in (None, "levels", 3, [], {}, {"levels": None}, {"levels": "x"}, {"levels": {"e_over_b": 1}}):
        assert _levels(odd) == [], odd


# ---------- tolerances ----------

def _only(t, **tol):
    t["tolerance"] = tol
    return t


def test_tolerances_come_from_the_task_and_default_when_absent():
    t = task()
    a = answer(t, scale=lambda i, j: 1.0)
    a["points"][0]["levels"][0]["e_over_b"] += 0.9    # level 0 of the first point: reference 0, off by 0.9
    assert score_diagram(t, a)["n_correct_items"] == 53
    assert score_diagram(_only(task(), curve_abs=1.0), a)["n_correct_items"] == 54
    notol = task()
    del notol["tolerance"]
    assert score_diagram(notol, a)["n_correct_items"] == 53      # no tolerance key: the defaults
    assert score_diagram(_only(task(), item_accuracy_min=0.5), a)["n_correct_items"] == 53  # curve keys missing
    # relative tolerance given alone: the absolute default stays
    b = answer(t)
    b["points"][8]["levels"][5]["e_over_b"] *= 1.10   # 48 -> 52.8: 10 % off, 4.8 absolute
    assert score_diagram(t, b)["n_correct_items"] == 53
    assert score_diagram(_only(task(), curve_rel=0.2), b)["n_correct_items"] == 54
    assert score_diagram(_only(task(), curve_rel=0.001), b)["n_correct_items"] == 53
    c = answer(t)
    c["points"][0]["levels"][0]["e_over_b"] += 0.2    # absolute default (0.3) covers it
    assert score_diagram(_only(task(), curve_rel=0.001), c)["n_correct_items"] == 54
    assert score_diagram(_only(task(), curve_abs=0.001), c)["n_correct_items"] == 53


def test_acceptance_threshold_comes_from_the_task_and_defaults_to_95_percent():
    t = task()
    a = answer(t)
    for i in range(6):
        a["points"][i]["levels"][5]["e_over_b"] *= 2     # 6 wrong of 54: accuracy 0.889
    assert score_diagram(t, a)["correct"] is False
    assert score_diagram(_only(task(), item_accuracy_min=0.88), a)["correct"] is True
    assert score_diagram(_only(task(), item_accuracy_min=0.89), a)["correct"] is False
    nokey = _only(task(), curve_abs=0.3, curve_rel=0.03)
    assert score_diagram(nokey, a)["correct"] is False
    two = answer(t)
    for i in range(2):
        two["points"][i]["levels"][5]["e_over_b"] *= 2
    assert score_diagram(nokey, two)["correct"] is True      # 52/54 = 0.963 >= 0.95
    assert score_diagram(_only(task(), item_accuracy_min=0.97), two)["correct"] is False


def test_acceptance_threshold_is_met_exactly_by_that_accuracy():
    t = task()
    a = answer(t)
    for i in range(2):
        a["points"][i]["levels"][5]["e_over_b"] *= 2
    exact = 52 / 54
    assert score_diagram(_only(task(), item_accuracy_min=exact), a)["correct"] is True
    assert score_diagram(_only(task(), item_accuracy_min=exact + 1e-9), a)["correct"] is False
    slack = exact + 1e-12   # the float slack of the comparison accepts this
    assert exact >= slack - 1e-12 and not exact > slack - 1e-12
    assert score_diagram(_only(task(), item_accuracy_min=slack), a)["correct"] is True


def test_value_tolerance_edges_are_inclusive():
    from tsbench.score import diagram_score as ds
    t = task()
    a = answer(t)
    a["points"][0]["levels"][0]["e_over_b"] = 0.3                 # reference 0.0: exactly the absolute tolerance
    assert score_diagram(t, a)["n_correct_items"] == 54
    a["points"][0]["levels"][0]["e_over_b"] = 0.3 + ds._EPS       # the slack is part of the tolerance
    assert score_diagram(t, a)["n_correct_items"] == 54
    a["points"][0]["levels"][0]["e_over_b"] = 0.3 + 1e-9
    assert score_diagram(t, a)["n_correct_items"] == 53
    # reference 1.0 (point 0, level 1): the relative rule alone, with a tiny absolute tolerance
    q = 2.0 ** -52
    for m in range(int((0.03 + ds._EPS) / q) - 4, int((0.03 + ds._EPS) / q) + 5):
        edge = m * q
        rel = edge - ds._EPS
        if rel + ds._EPS == edge and (1.0 + edge) - 1.0 == edge:
            break
    narrow = _only(task(), curve_abs=0.001, curve_rel=rel)
    b = answer(t)
    b["points"][0]["levels"][1]["e_over_b"] = 1.0 + edge          # relative error == rel + slack
    assert score_diagram(narrow, b)["n_correct_items"] == 54
    b["points"][0]["levels"][1]["e_over_b"] = 1.0 + edge + 1e-9
    assert score_diagram(narrow, b)["n_correct_items"] == 53


def test_grid_points_are_matched_within_1e_6_inclusive():
    t = task()
    a = answer(t)
    a["points"][0]["dq_over_b"] = 1e-6                   # grid point 0.0 is exactly 1e-6 away
    assert score_diagram(t, a)["n_correct_items"] == 54
    a["points"][0]["dq_over_b"] = 2e-6
    assert score_diagram(t, a)["n_correct_items"] == 48


# ---------- reported numbers ----------

def test_rms_is_the_root_mean_square_over_the_compared_values():
    t = task()
    a = answer(t)
    a["points"][0]["levels"][5]["e_over_b"] += 3.0
    a["points"][1]["levels"][5]["e_over_b"] += 4.0
    s = score_diagram(t, a)
    assert s["rms_e_over_b"] == math.sqrt((9.0 + 16.0) / 54)
    # only the compared values count: a dropped point (6 values) leaves 48
    b = answer(t, drop=8)
    b["points"][0]["levels"][5]["e_over_b"] += 3.0
    b["points"][1]["levels"][5]["e_over_b"] += 4.0
    assert score_diagram(t, b)["rms_e_over_b"] == math.sqrt(25.0 / 48)


def test_label_accuracy_counts_a_label_once_per_reference_member():
    t = task()
    t["reference"]["levels"] = [[0.0, 0.0, 5.0, 6.0, 7.0, 9.0]] * 9
    t["reference"]["labels"] = [["5Eg", "5Eg", "3T1g", "3T2g", "3A2g", "1A1g"]] * 9
    a = answer(t)
    for p in a["points"]:   # one of the two coincident 5Eg answered, the other level labelled wrongly
        for lv, name in zip(p["levels"], ["5Eg", "wrong", "3T1g", "3T2g", "3A2g", "1A1g"], strict=False):
            lv["term"] = name
    assert math.isclose(score_diagram(t, a)["label_accuracy"], 5 * 9 / 54)


def test_an_empty_reference_scores_zero_without_dividing():
    t = task()
    t["reference"] = {"grid": [], "levels": [], "labels": []}
    s = score_diagram(t, answer(task()))
    assert s["item_accuracy"] == 0.0 and s["label_accuracy"] == 0.0 and s["n_correct_items"] == 0
    assert s["correct"] is False and math.isnan(s["rms_e_over_b"])


def test_reference_lists_of_different_length_are_cut_to_the_shortest():
    t = task()
    t["reference"]["labels"] = t["reference"]["labels"][:8]   # no labels for the last grid point
    s = score_diagram(t, answer(task()))
    assert s["n_correct_items"] == 48 and s["item_accuracy"] == 1.0   # 8 points of 6 values compared
    t2 = task()
    t2["reference"]["labels"] = [["a", "b"]] * 9     # labels shorter than the levels
    assert score_diagram(t2, answer(t2))["item_accuracy"] == 1.0


def test_huge_integers_are_not_numbers_and_do_not_raise():
    t = task()
    a = answer(t)
    a["points"][0]["levels"][5]["e_over_b"] = 10**400   # one value lost
    a["points"][1]["dq_over_b"] = 10**400               # a point lost: six values
    s = score_diagram(t, a)
    assert s["n_correct_items"] == 54 - 1 - 6 and not s["correct"]
