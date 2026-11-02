"""Unit tests for tsbench.stats.descriptive (synthetic rows only)."""
from __future__ import annotations

import importlib.util
import math
import pathlib
import statistics

import pytest

from tsbench.score.score import score_dir
from tsbench.stats import descriptive as d
from tsbench.stats.hypotheses import clopper_pearson
from tsbench.tasks import load

M = "claude-haiku-5-5"
ACCEPTANCE_TESTS = pathlib.Path(__file__).resolve().parents[1] / "score" / "test_acceptance_metrics.py"


def row(task, cls, correct, dq=1000.0, subtype="d3", cond="A", k=1, model=M, effort="medium"):
    return {"model": model, "condition": cond, "effort": effort, "task_id": task, "k_index": k, "class": cls,
            "subtype": subtype, "correct": correct, "dq": dq}


def csv_form(r):
    """Render a typed row the way scores.csv stores it."""
    return {key: "" if v is None or (isinstance(v, float) and math.isnan(v)) else str(v) for key, v in r.items()}


def test_columns_and_row_keys():
    out = d.per_class_accuracy([row("a", "closed_form", True)])
    assert all(list(r) == d.PER_CLASS_COLUMNS for r in out)
    assert all(list(r) == d.CONSISTENCY_COLUMNS for r in d.consistency([row("a", "closed_form", True)]))


def test_source_group_covers_all_pilot_subtypes():
    seen = {}
    for t in load("pilot"):
        seen.setdefault((t["class"], t["subtype"]), d.source_group({"class": t["class"], "subtype": t["subtype"]}))
    for (cls, sub), grp in seen.items():
        if cls in ("experimental", "literature_all", "literature_new"):
            assert grp == "literature"
        elif cls == "pairing" or (cls == "out_of_scope" and sub != "tetrahedral"):
            assert grp is None
        else:
            assert grp == "synthetic"
    assert d.source_group({"class": "out_of_scope", "subtype": None}) is None


def test_per_class_counts_ci_and_no_empty_groups():
    rows = [row("a", "closed_form", True), row("a", "closed_form", False, k=2), row("e", "experimental", True),
            row("o", "out_of_scope", False, subtype="jahn_teller"), row("a", "closed_form", True, cond="C")]
    idx = {(r["condition"], r["grouping"], r["group"]): r for r in d.per_class_accuracy(rows)}
    cf = idx[("A", "class", "closed_form")]
    assert (cf["n"], cf["n_correct"], cf["accuracy"]) == (2, 1, 0.5)
    assert (cf["ci_lo"], cf["ci_hi"]) == clopper_pearson(1, 2)
    assert ("A", "source", "synthetic") in idx and ("A", "source", "literature") in idx
    assert idx[("A", "class", "out_of_scope")]["n"] == 1
    assert ("C", "source", "literature") not in idx
    # the jahn_teller row is in the class grouping but in no source group
    assert sum(r["n"] for r in idx.values() if r["grouping"] == "source" and r["condition"] == "A") == 3


def test_per_class_edge_cis_and_sorting():
    rows = [row("a", "numerical", True), row("b", "numerical", True)]
    r = d.per_class_accuracy(rows)[0]
    assert r["accuracy"] == 1.0 and r["ci_hi"] == 1.0 and 0 < r["ci_lo"] < 1
    keys = [(r["model"], r["condition"], r["effort"], r["grouping"], r["group"])
            for r in d.per_class_accuracy([row("a", "racah_c", True, cond="C"), row("a", "racah_c", True, cond="A")])]
    assert keys == sorted(keys)


def test_csv_and_typed_forms_agree_and_mix():
    typed = [row("a", "closed_form", True), row("a", "closed_form", False, dq=None, k=2),
             row("b", "experimental", False, dq=float("nan")), row("b", "experimental", True, dq=900, k=2)]
    csv_rows = [csv_form(r) for r in typed]
    assert d.per_class_accuracy(typed) == d.per_class_accuracy(csv_rows)
    assert d.consistency(typed) == d.consistency(csv_rows)
    mixed = [typed[0], csv_rows[1], typed[2], csv_rows[3]]
    assert d.consistency(mixed) == d.consistency(typed)


def test_consistency_values():
    rows = ([row("X", "closed_form", True, dq=100, k=i) for i in (1, 2, 3)]
            + [row("Y", "closed_form", True, dq=100, k=1), row("Y", "closed_form", False, dq=120, k=2)]
            + [row("W", "closed_form", False, dq=100, k=1), row("W", "closed_form", False, dq=None, k=2)]
            + [row("Z", "closed_form", True, dq=999, k=1)])
    (r,) = d.consistency(rows)
    assert (r["n_tasks"], r["n_unanimous"]) == (3, 2)
    assert r["unanimity_rate"] == pytest.approx(2 / 3)
    assert r["mean_pairwise_agreement"] == pytest.approx(2 / 3)
    assert r["n_tasks_cv"] == 2
    cv = statistics.stdev([100, 120]) / statistics.fmean([100, 120])
    assert r["median_cv_dq"] == pytest.approx(statistics.median([0.0, cv]))


def test_consistency_pairwise_agreement_k4():
    # 3 correct of 4: pairs equal = C(3,2) + C(1,2) = 3 of 6
    rows = [row("T", "numerical", c, k=i) for i, c in enumerate((True, True, True, False), 1)]
    assert d.consistency(rows)[0]["mean_pairwise_agreement"] == pytest.approx(0.5)


def test_consistency_abs_dq_zero_mean_nonfinite_and_empty():
    r = d.consistency([row("T", "out_of_scope", True, dq=-500, subtype="tetrahedral", k=1),
                       row("T", "out_of_scope", True, dq=500, subtype="tetrahedral", k=2)])[0]
    assert r["median_cv_dq"] == 0.0
    r = d.consistency([row("T", "numerical", True, dq=0, k=1), row("T", "numerical", True, dq=0, k=2),
                       row("U", "numerical", True, dq=float("inf"), k=1), row("U", "numerical", True, dq=5, k=2)])[0]
    assert r["n_tasks"] == 2 and r["n_tasks_cv"] == 0 and r["median_cv_dq"] is None
    (e,) = d.consistency([row("Z", "closed_form", True)])
    assert e["n_tasks"] == 0 and e["unanimity_rate"] is None and e["mean_pairwise_agreement"] is None
    assert e["median_cv_dq"] is None and d.consistency([]) == []


def test_consistency_cells_are_separate_and_sorted():
    rows = [row("T", "numerical", True, cond=c, k=k) for c in ("C", "A") for k in (1, 2)]
    out = d.consistency(rows)
    assert [r["condition"] for r in out] == ["A", "C"]


def test_consistency_on_score_dir_rows(tmp_path):
    spec = importlib.util.spec_from_file_location("acceptance_metrics_runs", ACCEPTANCE_TESTS)
    acceptance = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(acceptance)
    rows = score_dir(acceptance.synthetic_runs(tmp_path), "pilot")["rows"]
    assert {r["condition"] for r in d.consistency(rows)} == {"A", "B", "C"}
    assert sum(r["n"] for r in d.per_class_accuracy(rows) if r["grouping"] == "class") == len(rows)


def test_coefficient_of_variation_of_the_absolute_dq():
    assert d._coefficient_of_variation([-1.0, 1.0, float("nan")]) == pytest.approx(0.0)   # |Dq| = 1, 1; nan dropped
    assert d._coefficient_of_variation([1.0, 3.0]) == pytest.approx(statistics.stdev([1.0, 3.0]) / 2.0)
    assert d._coefficient_of_variation([0.5]) is None          # fewer than two values
    assert d._coefficient_of_variation([0.0, 0.0]) is None     # mean is not positive


def test_bool_reads_strings_numbers_and_missing_values():
    for text in ("true", "True", " TRUE ", "1"):
        assert d._bool(text) is True
    for text in ("false", "False", " FALSE ", "0"):
        assert d._bool(text) is False
    for text in ("", "  ", "maybe", "nan", "2"):
        assert d._bool(text) is None
    assert d._bool(None) is None and d._bool(float("nan")) is None
    assert d._bool(True) is True and d._bool(False) is False
    assert d._bool(1) is True and d._bool(0) is False
    assert d._bool(2.5) is True and d._bool(0.0) is False     # a finite float is read by its truth value


def test_float_reads_strings_and_keeps_infinity():
    assert d._float("3.5") == 3.5 and d._float(2) == 2.0 and d._float(" 7 ") == 7.0
    assert d._float(None) is None and d._float("") is None and d._float("  ") is None
    assert d._float(float("nan")) is None and d._float("nan") is None
    assert d._float("inf") == math.inf and d._float(-math.inf) == -math.inf


def test_text_and_cell_turn_missing_values_into_empty_strings():
    assert d._text(None) == "" and d._text(float("nan")) == ""
    assert d._text("abc") == "abc" and d._text(3) == "3" and d._text(2.5) == "2.5" and d._text(0) == "0"
    assert d._cell({"model": "m", "condition": "C", "effort": "high"}) == ("m", "C", "high")
    assert d._cell({"model": None, "condition": "C", "effort": float("nan")}) == ("", "C", "")
    assert d._cell({"model": "m", "condition": None, "effort": "e"}) == ("m", "", "e")


def test_cells_of_different_model_and_effort_stay_apart():
    rows = [row("T", "numerical", True, model=m, effort=e, k=k)
            for m in ("m1", "m2") for e in ("low", "max") for k in (1, 2)]
    out = d.consistency(rows)
    assert [(r["model"], r["effort"], r["n_tasks"]) for r in out] == [
        ("m1", "low", 1), ("m1", "max", 1), ("m2", "low", 1), ("m2", "max", 1)]
    acc = d.per_class_accuracy(rows)
    assert {(r["model"], r["effort"], r["n"]) for r in acc if r["grouping"] == "class"} == {
        ("m1", "low", 2), ("m1", "max", 2), ("m2", "low", 2), ("m2", "max", 2)}


def test_a_null_correct_flag_counts_as_not_correct():
    # one run right, one run without a verdict: they disagree, so the task is not unanimous
    r = d.consistency([row("T", "numerical", "True", k=1), row("T", "numerical", "", k=2)])[0]
    assert (r["n_tasks"], r["n_unanimous"]) == (1, 0) and r["mean_pairwise_agreement"] == 0.0
    # two runs without a verdict agree with each other
    r = d.consistency([row("T", "numerical", "", k=1), row("T", "numerical", None, k=2)])[0]
    assert r["n_unanimous"] == 1 and r["mean_pairwise_agreement"] == 1.0
    pc = {x["group"]: x for x in d.per_class_accuracy([row("T", "numerical", ""), row("T", "numerical", "True")])
          if x["grouping"] == "class"}
    assert (pc["numerical"]["n"], pc["numerical"]["n_correct"], pc["numerical"]["accuracy"]) == (2, 1, 0.5)
