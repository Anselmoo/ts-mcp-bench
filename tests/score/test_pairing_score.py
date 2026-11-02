import copy

import numpy as np
import pytest

from tsbench.score.pairing_score import score_pairing
from tsbench.tasks.classes import pairing as p


def _task():
    return p.make_pairing(np.random.default_rng(0))[0][0]


def _perfect(task):
    return {"nodes": copy.deepcopy(task["reference"]["nodes"]), "edges": copy.deepcopy(task["reference"]["edges"]),
            "reason": "r"}


def test_perfect():
    t = _task()
    s = score_pairing(t, _perfect(t))
    assert s["correct"] and s["edge_f1"] == 1.0 and s["ground_correct"]


def test_edge_order_irrelevant():
    t = _task()
    o = _perfect(t)
    for e in o["edges"]:
        e["a"], e["b"] = e["b"], e["a"]
    assert score_pairing(t, o)["correct"]


def test_wrong_count():
    t = _task()
    o = _perfect(t)
    o["nodes"][0]["count"] += 1
    s = score_pairing(t, o)
    assert not s["correct"] and s["node_recall"] < 1 and s["node_precision"] < 1


def test_missing_and_extra_edge():
    t = _task()
    o = _perfect(t)
    o["edges"].pop()
    s = score_pairing(t, o)
    assert s["edge_recall"] < 1 and s["edge_precision"] == 1.0 and not s["correct"]
    o = _perfect(t)
    o["edges"].append({"a": "d2", "b": "d4", "term": "5D"})
    s = score_pairing(t, o)
    assert s["edge_precision"] < 1 and s["edge_recall"] == 1.0 and not s["correct"]


def test_wrong_ground():
    t = _task()
    o = _perfect(t)
    for n in o["nodes"]:
        if n["config"] == "d4":
            n["ground"] = n["term"] == "3H"
    s = score_pairing(t, o)
    assert not s["ground_correct"] and not s["correct"] and s["node_recall"] == 1.0


def test_two_grounds_in_one_config_wrong():
    t = _task()
    o = _perfect(t)
    o["nodes"][0]["ground"] = True
    o["nodes"][1]["ground"] = True
    assert not score_pairing(t, o)["ground_correct"]


def test_empty_and_garbage():
    t = _task()
    for bad in ({}, {"nodes": None, "edges": "x"}, None, {"nodes": [1, "a"], "edges": [None]}):
        s = score_pairing(t, bad)
        assert not s["correct"] and s["node_recall"] == 0.0 and s["edge_f1"] == 0.0


def test_no_edges_reference():
    t = {"reference": {"nodes": [{"config": "d1", "term": "2D", "count": 1, "ground": True}], "edges": []}}
    out = {"nodes": t["reference"]["nodes"], "edges": [], "reason": ""}
    assert score_pairing(t, out)["correct"]
    out["edges"] = [{"a": "d1", "b": "d9", "term": "2D"}]
    assert not score_pairing(t, out)["correct"]


def test_package_style_primed_labels_are_summed():
    """tanabesugano.free_ion lists repeated terms as 2D, 2D', 2D''; that must score like '2D x 3'."""
    from tsbench.score.pairing_score import _nodes
    primed = [{"config": "d5", "term": t, "count": 1, "ground": False} for t in ("2D", "2D'", "2D''")]
    grouped = [{"config": "d5", "term": "2D", "count": 3, "ground": False}]
    assert _nodes(primed) == _nodes(grouped) == {("d5", "2D", 3)}


def test_precision_recall_f1_of_two_sets():
    from tsbench.score import pairing_score

    assert pairing_score._precision_recall_f1({1, 2, 3}, {2, 3, 4}) == pytest.approx((2 / 3, 2 / 3, 2 / 3))
    assert pairing_score._precision_recall_f1(set(), set()) == (1.0, 1.0, 1.0)


def test_precision_recall_f1_with_empty_sets():
    from tsbench.score.pairing_score import _precision_recall_f1 as prf
    assert prf(set(), set()) == (1.0, 1.0, 1.0)          # nothing asked, nothing given: perfect
    assert prf({1}, set()) == (0.0, 0.0, 0.0)            # something given where nothing was asked
    assert prf(set(), {1}) == (0.0, 0.0, 0.0)            # nothing given where something was asked
    assert prf({1}, {2}) == (0.0, 0.0, 0.0)
    assert prf({1, 2}, {2, 3, 4}) == (0.5, 1 / 3, 2 * 0.5 * (1 / 3) / (0.5 + 1 / 3))
    assert prf({1, 2}, {1, 2}) == (1.0, 1.0, 1.0)


def test_norm_term_drops_spaces_and_primes_only():
    from tsbench.score.pairing_score import _norm_term
    assert _norm_term(" 2 D ") == "2D" and _norm_term("2D'") == "2D" and _norm_term("2D′ ″") == "2D"
    assert _norm_term("2D''") == "2D" and _norm_term("3 T 1 g") == "3T1g" and _norm_term("a'b") == "a'b"
    assert _norm_term("3X") == "3X" and _norm_term("X") == "X" and _norm_term(None) == "None"
