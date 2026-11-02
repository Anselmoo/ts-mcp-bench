"""Unit tests for tsbench.score.taxonomy: synthetic rows and tasks only, no transcripts, no API."""
from __future__ import annotations

import math

import pytest

from tsbench.score.taxonomy import (
    CATEGORIES,
    FAILURE_COLUMNS,
    SCOPE_COLUMNS,
    failure_category,
    failure_table,
    scope_confusion,
)
from tsbench.stats.hypotheses import clopper_pearson
from tsbench.tasks import load

NAN = float("nan")


def task(**kw) -> dict:
    base = {"id": "T", "class": "closed_form", "required": ["Dq", "B"], "expect_out_of_scope": False,
            "tolerance": {"Dq": 0.02, "B": 0.05, "C": 0.10}}
    base.update(kw)
    return base


def row(**kw) -> dict:
    """A typed row (bool, NaN, None), as score_dir returns it."""
    base = {"model": "m", "condition": "A", "effort": "medium", "task_id": "T", "correct": False,
            "unparseable": False, "answer_out_of_scope": False, "rel_err_dq": 0.0, "rel_err_b": 0.0,
            "rel_err_c": NAN, "is_error": False, "result_subtype": "success", "has_result": True}
    base.update(kw)
    return base


def csv_form(r: dict) -> dict:
    return {k: "" if v is None or (isinstance(v, float) and math.isnan(v)) else str(v) for k, v in r.items()}


OOS = task(id="O", expect_out_of_scope=True, required=[])


@pytest.mark.parametrize("expected,r,t", [
    ("correct", row(correct=True, is_error=True), task()),  # correct wins over everything
    ("no_result", row(has_result=False, is_error=None, result_subtype=None), task()),
    ("max_turns", row(is_error=True, result_subtype="error_max_turns"), task()),
    ("budget", row(is_error=True, result_subtype="error_max_budget_usd"), task()),
    ("api_error", row(is_error=True), task()),
    ("context_overflow", row(is_error=True, context_overflow=True), task()),
    ("context_overflow", row(is_error=True, context_overflow=True, unparseable=True), task()),
    ("unparseable", row(unparseable=True, answer_out_of_scope=None), task()),
    ("false_refusal", row(answer_out_of_scope=True), task()),
    ("missed_limit", row(task_id="O"), OOS),
    ("missed_limit", row(task_id="O", answer_out_of_scope=None), OOS),
    ("missed_limit", row(task_id="O", answer_out_of_scope=True), OOS),  # flag right, but Dq/B given
    ("gross_error", row(rel_err_dq=0.51), task()),
    ("gross_error", row(rel_err_b=math.inf), task()),
    ("wrong_dq", row(rel_err_dq=0.03), task()),
    ("wrong_dq", row(rel_err_dq=NAN), task()),  # missing value is off, not gross
    ("wrong_b", row(rel_err_b=0.06), task()),
    ("wrong_c", row(rel_err_c=0.2), task(required=["Dq", "B", "C"])),
    ("wrong_multiple", row(rel_err_dq=0.03, rel_err_b=0.06), task()),
    ("wrong_multiple", row(rel_err_dq=NAN, rel_err_b=NAN), task()),
    ("unparseable", row(answer_out_of_scope=None), task()),  # nothing off, flag not boolean
])
def test_failure_category_both_row_forms(expected, r, t):
    assert failure_category(r, t) == expected
    assert failure_category(csv_form(r), t) == expected


def test_boundaries_and_ignored_parameters():
    # exactly 0.5 is not gross; exactly on tolerance is not off
    assert failure_category(row(rel_err_dq=0.02, rel_err_b=0.5), task()) == "wrong_b"
    # C is not required: neither gross nor off, even when huge
    assert failure_category(row(rel_err_dq=0.03, rel_err_c=9.0), task()) == "wrong_dq"
    # a required parameter without a tolerance can never pass
    assert failure_category(row(), task(tolerance={"Dq": 0.02, "B": None})) == "wrong_b"


def test_every_category_is_reachable_and_in_precedence_order():
    assert len(set(CATEGORIES)) == len(CATEGORIES) == 15
    # the order is the row order of failure_taxonomy.csv; wrong_items (curve, diagram, batch and pairing
    # answers outside the tolerance) is category 15, last
    assert CATEGORIES == (
        "correct", "no_result", "max_turns", "budget", "context_overflow", "api_error", "unparseable",
        "false_refusal", "missed_limit", "gross_error", "wrong_dq", "wrong_b", "wrong_c", "wrong_multiple",
        "wrong_items")
    assert FAILURE_COLUMNS[-3:] == ["category", "n", "share"]


def test_failure_table_is_rectangular_and_skips_unknown_tasks():
    rows = [row(correct=True), row(rel_err_dq=0.03), row(rel_err_dq=0.03), row(condition="B", has_result=False),
            row(task_id="unknown")]
    table = failure_table(rows, {"T": task()})
    assert len(table) == 2 * len(CATEGORIES)
    a = [r for r in table if r["condition"] == "A"]
    assert [r["category"] for r in a] == list(CATEGORIES)
    assert all(list(r) == FAILURE_COLUMNS for r in table)
    assert sum(r["n"] for r in a) == 3
    by = {r["category"]: r for r in a}
    assert by["wrong_dq"]["n"] == 2 and math.isclose(by["wrong_dq"]["share"], 2 / 3)
    assert math.isclose(sum(r["share"] for r in a), 1.0)


def test_scope_confusion_counts_rates_and_identity():
    rows = [
        row(task_id="O", answer_out_of_scope=True), row(task_id="O", answer_out_of_scope=False),
        row(task_id="O", answer_out_of_scope=None), row(answer_out_of_scope=True),
        row(answer_out_of_scope=False), row(answer_out_of_scope=False), row(answer_out_of_scope=None),
        row(task_id="gone"),
    ]
    for form in (rows, [csv_form(r) for r in rows]):
        (r,) = scope_confusion(form, {"T": task(), "O": OOS})
        assert list(r) == SCOPE_COLUMNS
        assert (r["n_expected_oos"], r["n_in_scope"]) == (3, 4)
        assert (r["true_limit"], r["missed_limit"], r["false_refusal"], r["no_scope_answer"]) == (1, 1, 1, 2)
        assert r["correct_scope"] == 3
        assert r["n_expected_oos"] + r["n_in_scope"] == (
            r["correct_scope"] + r["missed_limit"] + r["false_refusal"] + r["no_scope_answer"])
        assert math.isclose(r["limit_naming_rate"], 1 / 3)
        assert (r["limit_naming_ci_lo"], r["limit_naming_ci_hi"]) == clopper_pearson(1, 3)
        assert math.isclose(r["false_refusal_rate"], 1 / 4)
        assert (r["false_refusal_ci_lo"], r["false_refusal_ci_hi"]) == clopper_pearson(1, 4)


def test_scope_confusion_empty_denominators_and_cell_order():
    out = scope_confusion([row(condition="B", task_id="O", answer_out_of_scope=True), row(condition="A")],
                          {"T": task(), "O": OOS})
    assert [r["condition"] for r in out] == ["A", "B"]
    a, b = out
    assert a["limit_naming_rate"] is None and a["limit_naming_ci_lo"] is None and a["limit_naming_ci_hi"] is None
    assert b["false_refusal_rate"] is None and b["false_refusal_ci_hi"] is None
    assert b["limit_naming_rate"] == 1.0


def test_pilot_tasks_split_expected_out_of_scope():
    tasks = {t["id"]: t for t in load("pilot")}
    oos = {t["subtype"]: t for t in tasks.values() if t["class"] == "out_of_scope"}
    td = next(t for t in tasks.values() if t["class"] == "tetrahedral")
    assert oos["charge_transfer"]["expect_out_of_scope"] and not td["expect_out_of_scope"]
    r = row(task_id=td["id"], rel_err_dq=0.03, rel_err_b=0.0)
    assert failure_category(r, td) == "wrong_dq"
    r = row(task_id=oos["charge_transfer"]["id"], rel_err_dq=NAN, rel_err_b=NAN)
    assert failure_category(r, oos["charge_transfer"]) == "missed_limit"


def test_parameter_off_is_true_for_a_missing_or_large_error():
    from tsbench.score import taxonomy

    task = {"tolerance": {"Dq": 0.05}}
    assert taxonomy._parameter_off({"rel_err_dq": "0.01"}, task, "Dq") is False
    assert taxonomy._parameter_off({"rel_err_dq": "0.2"}, task, "Dq") is True
    assert taxonomy._parameter_off({}, task, "Dq") is True


# ---------- cell parsing ----------

def test_bool_reads_typed_and_csv_values():
    from tsbench.score.taxonomy import _bool
    for v in (True, "True", " true ", "1", 1, "TRUE"):
        assert _bool(v) is True, v
    for v in (False, "False", "0", 0, " FALSE"):
        assert _bool(v) is False, v
    for v in (None, "", "yes", NAN, 0.5, 1.0, "nan", 2):
        assert _bool(v) is None, v


def test_float_reads_typed_and_csv_values():
    from tsbench.score.taxonomy import _float
    assert _float("0.25") == 0.25 and _float(3) == 3.0 and _float(math.inf) == math.inf
    for v in (None, "", NAN, "nan"):
        assert _float(v) is None


def test_parameter_off_edge_is_not_off():
    from tsbench.score.taxonomy import _EPS, _parameter_off
    t = task(tolerance={"Dq": 0.02})
    assert _parameter_off(row(rel_err_dq=0.02), t, "Dq") is False
    assert _parameter_off(row(rel_err_dq=0.02 + _EPS), t, "Dq") is False   # the slack of the tolerance
    assert _parameter_off(row(rel_err_dq=0.02 + 1e-9), t, "Dq") is True
    assert _parameter_off(row(rel_err_dq=NAN), t, "Dq") is True            # no error to compare: off
    assert _parameter_off(row(rel_err_b=0.0), t, "B") is True              # no tolerance for B: off
    assert _parameter_off(row(rel_err_b=0.0), task(tolerance=None), "B") is True
    # the edge exactly: a relative error equal to tolerance + slack
    q = 2.0 ** -52
    for m in range(int((0.02 + _EPS) / q) - 4, int((0.02 + _EPS) / q) + 5):
        edge = m * q
        if (edge - _EPS) + _EPS == edge:
            break
    assert _parameter_off(row(rel_err_dq=edge), task(tolerance={"Dq": edge - _EPS}), "Dq") is False


# ---------- answers that are not Dq/B ----------

CURVE = task(id="K", answer_schema="curve", required=[])
BATCH = task(id="B", answer_schema="batch", required=[])
PAIRING = task(id="P", answer_schema="pairing", required=[])
DIAGRAM = task(id="D", answer_schema="diagram", required=[])


@pytest.mark.parametrize("err,want", [(0.51, "gross_error"), (0.5, "wrong_items"), (0.49, "wrong_items"),
                                      (math.inf, "gross_error"), (0.0, "wrong_items"),
                                      (None, "unparseable"), (NAN, "unparseable"), ("", "unparseable")])
def test_curve_rows_are_judged_by_the_largest_relative_error(err, want):
    assert failure_category(row(curve_max_rel_err=err), CURVE) == want
    assert failure_category(row(curve_max_rel_err=err, unparseable=False, rel_err_dq=0.9), CURVE) == want


@pytest.mark.parametrize("err,want", [(0.51, "gross_error"), (0.5, "wrong_items"), (0.1, "wrong_items"),
                                      (None, "gross_error"), ("", "gross_error"), (NAN, "gross_error")])
def test_batch_rows_are_judged_by_the_median_relative_error(err, want):
    # the batch scorer writes None when the median is infinite (half or more of the items missing or null): gross
    assert failure_category(row(median_rel_error=err, curve_max_rel_err=0.9, item_accuracy=0.0), BATCH) == want
    assert failure_category(row(median_rel_error=err, answer_out_of_scope=True), BATCH) == want  # no scope flag here


@pytest.mark.parametrize("acc,want", [(0.0, "gross_error"), (0.49, "gross_error"), (0.5, "wrong_items"),
                                      (0.9, "wrong_items"), (None, "wrong_items"), ("", "wrong_items"),
                                      (NAN, "wrong_items")])
def test_diagram_rows_are_gross_when_fewer_than_half_the_values_are_right(acc, want):
    assert failure_category(row(item_accuracy=acc, median_rel_error=0.9, curve_max_rel_err=0.9), DIAGRAM) == want
    assert failure_category(row(item_accuracy=acc, answer_out_of_scope=True), DIAGRAM) == want


def test_other_schemas_do_not_borrow_the_rules_of_those_schemas():
    fit = task(answer_schema="fit")
    r = row(median_rel_error=0.9, curve_max_rel_err=0.9, item_accuracy=0.0, rel_err_dq=0.03)
    assert failure_category(r, fit) == "wrong_dq"
    assert failure_category(r, task()) == "wrong_dq"          # no schema key at all
    odd_case = task(answer_schema="Diagram")
    assert failure_category(csv_form(row(item_accuracy=0.2, rel_err_dq=0.03)), odd_case) == "wrong_dq"
    assert failure_category(row(median_rel_error=0.9, rel_err_dq=0.03), task(answer_schema="Pairing")) == "wrong_dq"


def test_scope_confusion_skips_non_fit_rows_and_keeps_going():
    tasks = {"B": BATCH, "K": CURVE, "T": task(), "O": OOS}
    rows = [row(task_id="B"), row(task_id="K"), row(task_id="T", answer_out_of_scope=True),
            row(task_id="O", answer_out_of_scope=True), row(task_id="T", answer_out_of_scope=False)]
    [out] = scope_confusion(rows, tasks)
    assert (out["n_expected_oos"], out["n_in_scope"], out["true_limit"], out["false_refusal"]) == (1, 2, 1, 1)
    assert out["correct_scope"] == 2 and out["no_scope_answer"] == 0 and out["missed_limit"] == 0
    assert out["limit_naming_rate"] == 1.0 and out["false_refusal_rate"] == 0.5


# ---------- items outside the tolerance ----------


@pytest.mark.parametrize(("t", "r"), [
    (CURVE, row(curve_max_rel_err=0.2)),
    (BATCH, row(median_rel_error=0.1)),
    (PAIRING, row(median_rel_error=0.0)),
    (DIAGRAM, row(item_accuracy=0.8)),
], ids=["curve", "batch", "pairing", "diagram"])
def test_a_wrong_answer_of_a_non_fit_schema_has_items_outside_the_tolerance(t, r):
    assert failure_category(r, t) == "wrong_items"
    assert failure_category(csv_form(r), t) == "wrong_items"


def test_a_fit_answer_with_two_parameters_off_stays_several_parameters_wrong():
    assert failure_category(row(rel_err_dq=0.03, rel_err_b=0.06), task()) == "wrong_multiple"
    assert failure_category(row(curve_max_rel_err=0.7), CURVE) == "gross_error"  # gross stays gross


def test_the_failure_table_has_a_row_for_items_wrong():
    table = failure_table([row(task_id="K", curve_max_rel_err=0.2)], {"K": CURVE})
    by = {r["category"]: r["n"] for r in table}
    assert by["wrong_items"] == 1 and by["wrong_multiple"] == 0


# ---------- rows as the batch and pairing scorers write them ----------


def _scored(name, answer):
    from tsbench.score.score import Extracted, judge_answer
    t = next(t for t in load("pilot") if t["id"] == name)
    sc, _ = judge_answer(t, Extracted(answer, "structured_output", False, ""))
    return {**row(task_id=name), **sc}, t  # the result columns of score_dir around the scorer's columns


def _batch_answer(t, fn):
    return {"values": [{"input": v["input"], "result": fn(i, v["result"])}
                       for i, v in enumerate(t["reference"]["values"])]}


def test_a_batch_answer_with_every_result_null_is_a_gross_error():
    t = next(t for t in load("pilot") if t["id"] == "P-batch-01")
    sc, t = _scored("P-batch-01", _batch_answer(t, lambda i, r: None))
    assert sc["median_rel_error"] is None and not sc["unparseable"]  # the scorer writes no median
    assert failure_category(sc, t) == "gross_error"


def test_a_batch_answer_with_only_a_third_of_the_values_is_a_gross_error():
    t = next(t for t in load("pilot") if t["id"] == "P-batch-01")
    sc, t = _scored("P-batch-01", _batch_answer(t, lambda i, r: r if i < len(t["reference"]["values"]) // 3 else None))
    assert failure_category(sc, t) == "gross_error"


def test_a_batch_answer_that_is_a_little_off_is_wrong_items():
    t = next(t for t in load("pilot") if t["id"] == "P-batch-01")
    sc, t = _scored("P-batch-01", _batch_answer(t, lambda i, r: r * 1.1))
    assert failure_category(sc, t) == "wrong_items"


def test_an_empty_pairing_answer_is_a_gross_error():
    sc, t = _scored("P-pairing-01", {"nodes": [], "edges": []})
    assert failure_category(sc, t) == "gross_error"
    assert failure_category(csv_form(sc), t) == "gross_error"


def test_a_pairing_answer_with_the_right_nodes_and_edges_but_no_ground_state_is_wrong_items():
    t = next(t for t in load("pilot") if t["id"] == "P-pairing-01")
    ref = t["reference"]
    nodes = [{**n, "ground": False} for n in ref["nodes"]]
    sc, t = _scored("P-pairing-01", {"nodes": nodes, "edges": ref["edges"]})
    assert sc["correct"] is False and sc["ground_correct"] is False
    assert failure_category(sc, t) == "wrong_items"


def test_a_pairing_answer_with_half_of_the_edges_missing_is_a_gross_error():
    t = next(t for t in load("pilot") if t["id"] == "P-pairing-01")
    ref = t["reference"]
    sc, t = _scored("P-pairing-01", {"nodes": ref["nodes"], "edges": ref["edges"][: len(ref["edges"]) // 3]})
    assert failure_category(sc, t) == "gross_error"


def test_a_pairing_row_without_the_columns_is_not_gross():
    assert failure_category(row(), PAIRING) == "wrong_items"


# ---------- the CLI ends a run that failed the answer schema again and again ----------

RETRIES = "error_max_structured_output_retries"


def test_a_run_that_failed_the_answer_schema_repeatedly_is_unparseable_not_an_api_error():
    r = row(is_error=True, result_subtype=RETRIES, unparseable=True, answer_out_of_scope=None)
    assert failure_category(r, task()) == "unparseable"
    assert failure_category(csv_form(r), task()) == "unparseable"
    # a limit or a missing result event still comes first, and so does a correct answer
    assert failure_category(row(has_result=False, is_error=None, result_subtype=None), task()) == "no_result"
    assert failure_category(row(correct=True, is_error=True, result_subtype=RETRIES), task()) == "correct"


@pytest.mark.parametrize("t", [CURVE, BATCH, PAIRING, DIAGRAM, OOS],
                         ids=["curve", "batch", "pairing", "diagram", "oos"])
def test_the_retries_subtype_is_unparseable_for_every_schema(t):
    r = row(is_error=True, result_subtype=RETRIES, unparseable=False, median_rel_error=0.9)
    assert failure_category(r, t) == "unparseable"
