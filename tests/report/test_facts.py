"""The facts of the full report (src/tsbench/report/facts.py): every number of the page, read from the run set, the
coverage report and the mutation shards.

Three kinds of data: (1) made-up runs on the real pilot task records, so that each number has a known answer
(`benchmark`); (2) a copy of the demo run set (fake claude), whose transcripts give the call paths (`benchmark`,
`platform`); (3) small coverage, mutation and source trees written into tmp_path (`checks`). The demo run set itself
is never written to.
"""
from __future__ import annotations

import collections
import csv
import json
import pathlib
import shutil
import statistics

import demo_runs
import pytest

from tsbench.core import intervals
from tsbench.report import dashboard, facts, full, literature, science
from tsbench.report.base import as_run_sets
from tsbench.score.run_sets import run_sets_in
from tsbench.score.taxonomy import failure_category
from tsbench.tasks import load

TASKS = {t["id"]: t for t in load("pilot") if t.get("split") == "pilot"}
ORDER = list(TASKS)
FIT = [t for t in TASKS.values() if science._is_fit(t)]


# ---------------------------------------------------------------- made-up runs on the pilot task records


def _n_items(task: dict) -> int:
    """The number of values an answer to a curve, diagram or batch task holds, from its reference (0 otherwise)."""
    ref = task.get("reference") or {}
    if task["answer_schema"] == "curve":
        return len(task.get("reference_curve") or [])
    if task["answer_schema"] == "diagram":
        return len(ref["grid"]) * int(task["params"]["n_levels"])
    if task["answer_schema"] == "batch":
        return len(ref["values"])
    return 0


def _row(model: str, cond: str, task: dict, correct: bool, *, k: int = 1, bash: int = 0, mcp: int = 0,
         tokens: float = 1000, seconds: float = 10.0, cost: float = 0.1, turns: int = 2, na: str = "") -> dict:
    """A scored run as dashboard.collect leaves it: a wrong fit answer is off by a factor 2 (relative error 1.0) in
    every required parameter, a correct one by 0.1 %. A correct diagram or batch answer has every item right, a wrong
    one a single item; a wrong pairing answer fewer than half of its nodes and edges and the wrong ground terms."""
    ref = task.get("reference") or {}
    r = {"model": model, "condition": cond, "_cond": cond, "task_id": task["id"], "k_index": str(k),
         "correct": str(correct), "evaluable": "True", "_na": na, "_task": task, "has_result": "True",
         "is_error": "False", "rescued": "False", "unparseable": "False", "result_subtype": "success",
         "n_bash_calls": str(bash), "n_mcp_calls": str(mcp), "output_tokens": str(tokens), "num_turns": str(turns),
         "duration_s": str(seconds), "api_duration_s": str(seconds), "cost_usd": str(cost),
         "answer_out_of_scope": "False", "_set": "set", "effort": "medium", "thinking_tokens": "5"}
    for p in ("Dq", "B", "C"):
        v = ref.get(p) if isinstance(ref, dict) else None
        f = 1.001 if correct else 2.0
        r[p.lower()] = "" if v is None else str(v * f)
        r[f"rel_err_{p.lower()}"] = "" if v is None else str(abs(f - 1))
    if task["answer_schema"] == "curve":
        r["curve_max_rel_err"] = "0.001" if correct else "0.9"
        r["curve_tol_ratio"] = "0.03333333333333333" if correct else "30.0"
    if task["answer_schema"] in ("batch", "pairing"):
        r["median_rel_error"] = "0.0" if correct else "0.9"
        r["item_accuracy"] = "1.0" if correct else "0.4"
        r["edge_f1"] = "1.0" if correct else "0.5"
    if task["answer_schema"] == "pairing":
        r["node_precision"] = r["node_recall"] = r["edge_precision"] = r["edge_recall"] = "1.0" if correct else "0.4"
        r["ground_correct"] = str(correct)
    if task["answer_schema"] == "diagram":
        r["item_accuracy"] = "1.0" if correct else "0.1"
    if task["answer_schema"] in ("diagram", "batch"):
        r["n_correct_items"] = str(_n_items(task) if correct else 1)
    if task.get("expect_out_of_scope"):
        r["answer_out_of_scope"] = str(correct)
    r["_category"] = failure_category(r, task)
    return r


SOLVES = {"A": {"closed_form", "experimental"},
          "B": {"experimental", "numerical"},
          "C": {"experimental", "numerical", "tetrahedral", "crossover", "curve"}}


def _data(models=("m1",), solves=SOLVES) -> dict:
    """Every pilot task under A, B and C for each model. A run is correct when its class is in `solves[cond]`; B
    calls Bash on numerical and numerical_hard tasks, C calls the server except on closed_form tasks; the cost of a
    run grows with the position of its task in the task file."""
    rows = []
    for m in models:
        for cond in "ABC":
            for i, t in enumerate(TASKS.values()):
                bash = 1 if cond == "B" and t["class"] in ("numerical", "numerical_hard") else 0
                mcp = 2 if cond == "C" and t["class"] != "closed_form" else 0
                rows.append(_row(m, cond, t, t["class"] in solves[cond], bash=bash, mcp=mcp,
                                 tokens=100 + i + {"A": 0, "B": 1000, "C": 2000}[cond], seconds=10 + i,
                                 cost=0.01 * (i + 1)))
    return {"rows": rows, "tasks": TASKS, "sets": [], "notes": []}


SOLVES_2 = {"A": {"closed_form"},
            "B": {"numerical"},
            "C": {"experimental", "numerical", "curve"}}


def _two_models() -> dict:
    """Every pilot task under A, B and C for two models: "zeta" solves `SOLVES`, "alpha" `SOLVES_2`. The first A run of
    alpha is not evaluable, so zeta has the most evaluable runs although its name sorts last."""
    data = _data(("zeta",))
    data["rows"] += _data(("alpha",), SOLVES_2)["rows"]
    next(r for r in data["rows"] if r["model"] == "alpha")["_na"] = "na429"
    return data


@pytest.fixture(scope="module")
def made():
    return facts._benchmark(_data(), {}, None)


@pytest.fixture(scope="module")
def two():
    data = _two_models()
    return data, facts._benchmarks(data, {})


def _solved(cond: str) -> set[str]:
    return {t["id"] for t in TASKS.values() if t["class"] in SOLVES[cond]}


def test_header_names_the_model_the_split_and_the_counts(made):
    h = made["header"]
    assert h["model"] == "m1" and h["models"] == ["m1"]
    assert h["split"] == "pilot" and h["n_tasks"] == 50 and h["n_classes"] == 14
    assert h["conds"] == ["A", "B", "C"] and h["k"] == 1 and h["n_runs"] == 150 and h["n_evaluable"] == 150
    # no manifest in the made-up data set: nothing is invented
    assert h["endpoint"] == "not recorded" and h["oracle"] is None and h["commit"] is None
    assert h["start"] is None and h["end"] is None
    assert h["effort"] == "medium" and h["k_planned"] is None


def test_shares_count_correct_runs_per_condition_with_the_task_bootstrap_interval(made):
    by = {r["cond"]: r for r in made["shares"]}
    assert list(by) == ["A", "B", "C"]
    for cond, k in (("A", 4), ("B", 5), ("C", 14)):
        r = by[cond]
        assert (r["k"], r["n"]) == (k, 50) and r["share"] == k / 50
        ids = sorted(TASKS)
        num = [int(t in _solved(cond)) for t in ids]
        lo, hi = intervals.cluster_bootstrap(num, [1] * 50)
        assert (r["lo"], r["hi"]) == (lo, hi) and r["lo"] <= r["share"] <= r["hi"]


def test_paired_differences_count_the_tasks_solved_by_one_condition_only(made):
    by = {r["pair"]: r for r in made["paired"]}
    assert list(by) == ["C − A", "C − B", "B − A"]
    assert (by["C − A"]["only_first"], by["C − A"]["only_second"]) == (
        len(_solved("C") - _solved("A")), len(_solved("A") - _solved("C"))) == (12, 2)
    assert (by["C − B"]["only_first"], by["C − B"]["only_second"]) == (9, 0)
    assert (by["B − A"]["only_first"], by["B − A"]["only_second"]) == (3, 2)
    assert by["C − A"]["diff"] == pytest.approx((14 - 4) / 50)
    assert by["C − B"]["diff"] == pytest.approx((14 - 5) / 50)
    assert by["B − A"]["diff"] == pytest.approx((5 - 4) / 50)
    assert all(r["lo"] <= r["diff"] <= r["hi"] for r in by.values())


def test_classes_list_tasks_per_class_in_task_file_order_with_marks_and_counts(made):
    cls = made["classes"]
    assert [c["class"] for c in cls] == list(dict.fromkeys(t["class"] for t in TASKS.values()))
    assert sum(c["n"] for c in cls) == 50
    cf = next(c for c in cls if c["class"] == "closed_form")
    assert cf["n"] == 2 and cf["marks"] == {"A": [True, True], "B": [False, False], "C": [False, False]}
    assert cf["k"] == {"A": 2, "B": 0, "C": 0}
    assert cf["tolerance"] == "Dq 2 %, B 5 %" and cf["tasks"] == ["P-closed_form-01", "P-closed_form-02"]
    lit = next(c for c in cls if c["class"] == "literature_all")
    assert lit["n"] == 10 and lit["k"] == {"A": 0, "B": 0, "C": 0} and lit["marks"]["C"] == [False] * 10
    assert {c["class"]: c["k"]["C"] for c in cls if c["k"]["C"]} == {
        "experimental": 2, "numerical": 3, "tetrahedral": 3, "crossover": 3, "curve": 3}
    assert next(c for c in cls if c["class"] == "out_of_scope")["tolerance"] == "must decline"


def _without_evaluable_run(data: dict, cond: str, task_id: str) -> None:
    """The runs of one cell all ended in HTTP 429: the task keeps its rows but has no evaluable run under `cond`."""
    for r in data["rows"]:
        if r["_cond"] == cond and r["task_id"] == task_id:
            r["_na"] = "na429"


def test_a_task_without_an_evaluable_run_is_left_out_of_the_marks_not_counted_as_unsolved():
    data = _data()
    _without_evaluable_run(data, "A", "P-closed_form-02")
    out = facts._benchmark(data, {}, None)
    cf = next(c for c in out["classes"] if c["class"] == "closed_form")
    assert cf["marks"]["A"] == [True, None] and cf["marks"]["B"] == [False, False]
    assert cf["k"] == {"A": 1, "B": 0, "C": 0}
    assert cf["n"] == 2 and cf["n_by"] == {"A": 1, "B": 2, "C": 2}
    row = next(b for b in out["tasks_view"] if b["class"] == "closed_form")
    assert row["k"]["A"] == 1 and row["n_by"] == {"A": 1, "B": 2, "C": 2}
    ledger = next(b for b in out["ledger"] if b["class"] == "closed_form")
    assert ledger["k"]["A"] == 1 and ledger["n_by"] == {"A": 1, "B": 2, "C": 2}


def test_the_solved_sets_leave_out_a_task_that_a_condition_never_answered():
    data = _data()
    _without_evaluable_run(data, "C", "P-closed_form-01")  # A solves it, B does not: it would fall into the set "A"
    out = facts._benchmark(data, {}, None)
    sets = {s["key"]: s["tasks"] for s in out["upset"]}
    assert "P-closed_form-01" not in [t for ts in sets.values() for t in ts]
    assert out["upset_excluded"] == ["P-closed_form-01"]
    assert "P-closed_form-02" in sets["A"]
    ok = facts._benchmark(_data(), {}, None)
    assert ok["upset_excluded"] == [] and sum(len(s["tasks"]) for s in ok["upset"]) == 50


def test_the_task_view_and_the_class_marks_cover_the_same_tasks_when_the_model_ran_part_of_the_split():
    data = _data()
    keep = set(ORDER[:10])
    data["rows"] = [r for r in data["rows"] if r["task_id"] in keep]
    out = facts._benchmark(data, {}, None)
    n_view = {b["class"]: b["n"] for b in out["tasks_view"]}
    n_marks = {c["class"]: c["n"] for c in out["classes"]}
    assert {c: n for c, n in n_view.items() if n} == n_marks and sum(n_view.values()) == 10
    assert {t["id"] for b in out["tasks_view"] for t in b["tasks"]} == set(ORDER)  # the unrun tasks keep a row
    assert all(not t["answers"] for b in out["tasks_view"] for t in b["tasks"] if t["id"] not in keep)
    assert {t["task"] for b in out["ledger"] for t in b["tasks"]} == keep


def test_outcome_folds_the_taxonomy_into_the_seven_report_categories(made):
    assert [k for k, _ in made["categories"]] == ["correct", "gross", "several", "items", "dq", "bc", "limit"]
    assert [lab for _, lab in made["categories"]] == [
        "correct", "gross error", "several parameters wrong", "items wrong", "Dq wrong", "B or C wrong",
        "limit missed / false refusal"]
    from tsbench.score.taxonomy import CATEGORIES as TAXONOMY

    rows = _data()["rows"]  # the rows carry the category of the taxonomy that the report folds
    raw = {c: {k: sum(r["_category"] == k for r in rows if r["_cond"] == c) for k in TAXONOMY} for c in "ABC"}
    assert "outcome_raw" not in made  # nothing reads the unfolded counts
    folded = {o["cond"]: o["counts"] for o in made["outcome"]}
    fold = {"correct": "correct", "gross_error": "gross", "wrong_multiple": "several", "wrong_items": "items",
            "wrong_dq": "dq", "wrong_b": "bc", "wrong_c": "bc", "missed_limit": "limit", "false_refusal": "limit"}
    assert facts.FOLD["wrong_items"] == "items"  # the scorer's category for curve, diagram, batch and pairing
    for cond in "ABC":
        assert sum(folded[cond].values()) == 50 and sum(raw[cond].values()) == 50
        assert folded[cond]["correct"] == len(_solved(cond)) == raw[cond]["correct"]
        want = collections.Counter()
        for k, n in raw[cond].items():
            want[fold.get(k, "other")] += n
        assert {k: v for k, v in folded[cond].items() if v} == {k: v for k, v in want.items() if v}
    # the three out_of_scope tasks A, B and C answer wrongly are counted as limits missed
    assert folded["C"]["limit"] == raw["C"]["missed_limit"] == 3
    assert folded["A"]["gross"] == raw["A"]["gross_error"] > 0


def test_a_run_without_a_valid_answer_gets_a_seventh_category_only_when_there_is_one():
    data = _data()
    r = data["rows"][0]
    r["has_result"], r["correct"] = "False", "False"
    r["_category"] = failure_category(r, r["_task"])
    out = facts._benchmark(data, {}, None)
    assert out["categories"][-1] == ("other", "no valid answer")
    assert {o["cond"]: o["counts"]["other"] for o in out["outcome"]} == {"A": 1, "B": 0, "C": 0}


def test_swarm_holds_the_error_in_units_of_the_tolerance_of_the_fit_tasks(made):
    groups = {g["cond"]: g for g in made["swarm"]}
    assert list(groups) == ["A", "B", "C"] and len(FIT) == 35
    for cond in "ABC":
        got = {v["task"]: v["ratio"] for v in groups[cond]["values"]}
        assert set(got) == {t["id"] for t in FIT}
        for t in FIT:
            err = 0.001 if t["class"] in SOLVES[cond] else 1.0
            assert got[t["id"]] == pytest.approx(max(err / t["tolerance"][p] for p in t["required"]))
    assert all(v["ratio"] <= 1 for v in groups["C"]["values"] if TASKS[v["task"]]["class"] in SOLVES["C"])


def test_upset_lists_the_tasks_of_each_of_the_eight_subsets(made):
    by = {s["key"]: s["tasks"] for s in made["upset"]}
    assert list(by) == ["", "A", "B", "C", "AB", "AC", "BC", "ABC"]
    assert sorted(sum(by.values(), [])) == sorted(TASKS)
    assert set(by["A"]) == {t for t in _solved("A") - _solved("C") - _solved("B")}
    assert len(by["A"]) == 2 and by["B"] == [] and by["AB"] == [] and by["AC"] == []
    assert len(by["ABC"]) == 2 and len(by["BC"]) == 3 and len(by["C"]) == 9 and len(by[""]) == 34
    assert by["ABC"] == [t for t in ORDER if TASKS[t]["class"] == "experimental"]


def test_runs_carry_task_class_outcome_key_and_the_measured_values(made):
    """One record per evaluable run for the result maps: task, class, outcome category key and the cost values."""
    runs = made["runs"]
    assert len(runs) == 150
    keys = {k for k, _ in made["categories"]}
    assert {r["outcome"] for r in runs} <= keys
    assert sum(r["outcome"] == "correct" for r in runs) == 4 + 5 + 14
    curve = next(t for t in ORDER if TASKS[t]["class"] == "curve")
    one = next(r for r in runs if r["cond"] == "C" and r["task"] == curve)
    assert one["class"] == "curve" and one["outcome"] == "correct"
    cost = {(r["cond"], r["task"]): r["values"] for r in made["cost"]["runs"]}
    assert all(r["values"] == cost[(r["cond"], r["task"])] for r in runs)


def test_ledger_holds_one_cell_per_task_and_condition_with_the_rule_of_its_class(made):
    led = made["ledger"]
    assert [c["class"] for c in led] == list(dict.fromkeys(TASKS[t]["class"] for t in ORDER))
    assert sum(len(c["tasks"]) for c in led) == len(TASKS)
    by = {x["task"]: x["cells"] for c in led for x in c["tasks"]}
    for t in TASKS.values():
        for cond in "ABC":
            cell = by[t["id"]][cond]
            assert cell["ok"] == (t["class"] in SOLVES[cond])
            if t["class"] == "out_of_scope":
                assert cell["kind"] == "scope" and cell["text"] in ("named", "missed", "refused")
            elif t["answer_schema"] == "fit":
                worst = max(1.0 / t["tolerance"][p] for p in t["required"]) if not cell["ok"] else None
                assert cell["kind"] == "ratio"
                if worst is not None:
                    assert cell["value"] == pytest.approx(worst)
            elif t["answer_schema"] == "curve":
                assert cell["kind"] == "ratio" and cell["value"] == pytest.approx(
                    (0.001 if cell["ok"] else 0.9) / t["tolerance"]["curve_rel"])
            elif t["answer_schema"] == "diagram":
                assert cell["kind"] == "share" and cell["need"] == t["tolerance"]["item_accuracy_min"]
            elif t["answer_schema"] == "batch":
                assert cell["kind"] == "share" and cell["need"] == 1.0
    for c in led:
        assert c["k"] == {cond: sum(by[x["task"]][cond]["ok"] for x in c["tasks"]) for cond in "ABC"}


def test_literature_lists_the_published_systems_with_oracle_tolerance_and_reported_values(made):
    lit = made["literature"]
    assert len(lit) == 18
    sys0 = next(s for s in lit if s["system"] == "[Cr(H2O)6]3+")
    t = TASKS["P-experimental-01"]
    assert sys0["dn"] == 3 and sys0["geometry"] == "Oh" and sys0["bands"] == t["bands_cm1"]
    # P-experimental-01 requires Dq and B: no C column
    assert sys0["required"] == ["Dq", "B"]
    assert sys0["oracle"] == {"Dq": t["reference"]["Dq"], "B": t["reference"]["B"]}
    assert sys0["tol"] == {"Dq": 0.05, "B": 0.1}
    # the source text, its DOI and its table locator, each kept
    assert sys0["source"] == "Garcia Rojas & Perez Torres, J. Chem. Educ. 2023, 100, 251"
    assert sys0["doi"] == "10.1021/acs.jchemed.2c00885" and "doi" not in sys0["source"]
    assert sys0["locator"] == "Tables 1-2"
    new1 = next(s for s in lit if s["task"] == "P-literature_new-01")
    assert new1["doi"] is None and new1["source"].startswith("Yang et al., Al2(WO4)3:Cr3+, arXiv:2403.15148")
    assert new1["locator"] == "Table 2"
    new3 = next(s for s in lit if s["task"] == "P-literature_new-03")
    assert new3["source"].endswith("Molecules 2024, 29, 2141") and new3["locator"] == "Table 3"
    assert new3["doi"] == "10.3390/molecules29092141"
    a = sys0["reported"]["A"]
    assert a["Dq"] == pytest.approx(t["reference"]["Dq"] * 1.001) and a["B"] == pytest.approx(
        t["reference"]["B"] * 1.001) and a["ok"] is True
    new = next(s for s in lit if s["task"] == "P-literature_new-01")
    assert new["reported"]["C"]["ok"] is False and new["reported"]["C"]["Dq"] == pytest.approx(
        TASKS["P-literature_new-01"]["reference"]["Dq"] * 2)
    assert {c: sum(s["reported"][c]["ok"] for s in lit) for c in "ABC"} == {"A": 2, "B": 2, "C": 2}


def test_literature_rows_carry_the_paper_values_beside_the_oracle(made):
    """The systems table puts the paper's Dq, B (and C) beside the oracle's."""
    rows = literature.read_csv_rows()
    for s in made["literature"]:
        paper = literature.paper_values(rows.get(literature._norm_name(s["system"])))
        want = {p: paper.get(p) for p in s["required"]}
        assert {p: s["paper"].get(p) for p in s["required"]} == want, s["task"]
        assert isinstance(s["paper_text"], str)


def test_tool_use_counts_runs_with_and_without_a_call_of_the_condition_tool(made):
    by = {r["cond"]: r for r in made["tool_use"]}
    assert list(by) == ["B", "C"]
    # B calls Bash on the six numerical tasks; B solves the three numerical ones
    assert (by["B"]["with"], by["B"]["with_correct"], by["B"]["without"], by["B"]["without_correct"]) == (6, 3, 44, 2)
    # C calls the server on all tasks but the two closed_form ones, and solves 14 of the 48
    assert (by["C"]["with"], by["C"]["with_correct"], by["C"]["without"], by["C"]["without_correct"]) == (48, 14, 2, 0)
    assert by["B"]["tool"] == "Bash" and by["C"]["tool"] == "TS-MCP"


def test_cost_medians_and_one_record_per_run(made):
    med = {m["cond"]: m for m in made["cost"]["medians"]}
    idx = list(range(50))
    assert med["A"]["output_tokens"] == statistics.median(100 + i for i in idx) == 124.5
    assert med["B"]["output_tokens"] == 1124.5 and med["C"]["output_tokens"] == 2124.5
    assert med["A"]["num_turns"] == 2 and med["A"]["api_duration_s"] == statistics.median(10 + i for i in idx)
    assert med["A"]["cost_usd"] == pytest.approx(statistics.median(0.01 * (i + 1) for i in idx))
    keys = [k for k, _ in made["cost"]["axes"]]
    assert keys == ["num_turns", "n_mcp_calls", "n_bash_calls", "output_tokens", "thinking_tokens", "duration_s",
                    "api_duration_s", "cost_usd"]
    runs = made["cost"]["runs"]
    assert len(runs) == 150
    r = next(r for r in runs if r["cond"] == "C" and r["task"] == ORDER[3])
    assert r["correct"] is (TASKS[ORDER[3]]["class"] in SOLVES["C"])
    assert r["values"]["output_tokens"] == 2103 and r["values"]["n_mcp_calls"] == 2 and r["values"]["num_turns"] == 2
    assert r["values"]["cost_usd"] == pytest.approx(0.04) and r["values"]["api_duration_s"] == 13.0
    assert r["values"]["thinking_tokens"] == 5


def test_without_transcripts_the_call_facts_are_empty(made):
    assert made["calls"] == [] and made["tools"] == [] and made["transitions"] == {}
    assert made["solution_paths"] == []


def test_the_model_with_the_most_evaluable_runs_is_shown_and_another_can_be_asked_for():
    data = _data(("m1",))
    extra = [_row("m2", "A", TASKS[ORDER[0]], True), _row("m2", "C", TASKS[ORDER[0]], False)]
    data["rows"] += extra
    out = facts._benchmark(data, {}, None)
    assert out["header"]["model"] == "m1" and out["header"]["models"] == ["m1", "m2"]
    other = facts._benchmark(data, {}, "m2")
    assert other["header"]["model"] == "m2" and other["header"]["n_runs"] == 2
    assert {r["cond"]: (r["k"], r["n"]) for r in other["shares"]} == {"A": (1, 1), "C": (0, 1)}
    assert [p["pair"] for p in other["paired"]] == ["C − A"]
    assert (other["paired"][0]["only_first"], other["paired"][0]["only_second"]) == (0, 1)


def test_benchmarks_analyse_every_model_with_the_most_evaluable_runs_first(two):
    data, benches = two
    assert list(benches) == ["zeta", "alpha"]
    assert {m: b["header"]["model"] for m, b in benches.items()} == {"zeta": "zeta", "alpha": "alpha"}
    assert (benches["zeta"]["header"]["n_evaluable"], benches["alpha"]["header"]["n_evaluable"]) == (150, 149)
    assert all(b["header"]["models"] == ["alpha", "zeta"] for b in benches.values())
    for m, b in benches.items():
        one = facts._benchmark(data, {}, m)
        for key in ("header", "shares", "paired", "classes", "outcome", "runs", "ledger", "notes"):
            assert b[key] == one[key], (m, key)
    # alpha: closed_form under A (the first of its two A runs is not evaluable), numerical under B
    assert {r["cond"]: (r["k"], r["n"]) for r in benches["alpha"]["shares"]} == {"A": (1, 49), "B": (3, 50),
                                                                                 "C": (8, 50)}
    assert {r["cond"]: (r["k"], r["n"]) for r in benches["zeta"]["shares"]} == {"A": (4, 50), "B": (5, 50),
                                                                                "C": (14, 50)}


def test_benchmarks_of_models_with_as_many_evaluable_runs_follow_the_name():
    assert list(facts._benchmarks(_data(("m2", "m1")), {})) == ["m1", "m2"]


def test_benchmarks_of_a_run_set_without_runs_hold_one_empty_model():
    benches = facts._benchmarks({"rows": [], "tasks": TASKS, "sets": [], "notes": []}, {})
    assert list(benches) == [""] and benches[""]["header"]["n_runs"] == 0


def test_models_overview_copies_header_shares_and_paired_differences_of_each_bench(two):
    _, benches = two
    rows = facts.models_overview(benches)
    assert [r["model"] for r in rows] == ["zeta", "alpha"]
    keys = {"model", "endpoint", "n_runs", "n_evaluable", "k", "k_planned", "conds", "cells", "paired"}
    assert all(set(r) == keys for r in rows)
    for row, b in zip(rows, benches.values(), strict=True):
        h = b["header"]
        assert [row[k] for k in ("model", "endpoint", "n_runs", "n_evaluable", "k", "k_planned", "conds")] == [
            h[k] for k in ("model", "endpoint", "n_runs", "n_evaluable", "k", "k_planned", "conds")]
        assert row["cells"] == {s["cond"]: {k: s[k] for k in ("k", "n", "tasks", "share", "lo", "hi")}
                                for s in b["shares"]}
        assert row["paired"] == {p["pair"]: {k: p[k] for k in ("diff", "lo", "hi", "p", "n")} for p in b["paired"]}
    zeta, alpha = rows
    assert (zeta["n_runs"], zeta["n_evaluable"], alpha["n_runs"], alpha["n_evaluable"]) == (150, 150, 150, 149)
    assert zeta["conds"] == ["A", "B", "C"] and zeta["endpoint"] == "not recorded" and zeta["k"] == 1
    assert (zeta["cells"]["C"]["k"], zeta["cells"]["C"]["n"], zeta["cells"]["C"]["tasks"]) == (14, 50, 50)
    assert zeta["cells"]["C"]["share"] == 14 / 50 and alpha["cells"]["A"]["share"] == 1 / 49
    assert list(zeta["paired"]) == ["C − A", "C − B", "B − A"]
    assert zeta["paired"]["C − A"]["diff"] == pytest.approx((14 - 4) / 50)
    assert alpha["paired"]["C − B"]["diff"] == pytest.approx((8 - 3) / 50)
    assert facts.models_overview({}) == []


def test_runs_that_are_not_evaluable_stay_out_of_every_count():
    data = _data()
    data["rows"][0]["_na"] = "na429"  # one A run
    out = facts._benchmark(data, {}, None)
    assert out["header"]["n_runs"] == 150 and out["header"]["n_evaluable"] == 149
    assert {r["cond"]: r["n"] for r in out["shares"]} == {"A": 49, "B": 50, "C": 50}
    assert len(out["runs"]) == 149


def test_repeated_runs_use_the_majority_of_a_task_and_report_every_run():
    data = _data()
    t = TASKS["P-closed_form-01"]
    # two more A runs of one task: 1 of 3 correct runs in A (the first is correct)
    data["rows"] += [_row("m1", "A", t, False, k=2), _row("m1", "A", t, False, k=3)]
    out = facts._benchmark(data, {}, None)
    assert out["header"]["k"] == 3 and out["header"]["n_runs"] == 152
    cf = next(c for c in out["classes"] if c["class"] == "closed_form")
    assert cf["marks"]["A"] == [False, True] and cf["k"]["A"] == 1
    assert {r["cond"]: (r["k"], r["n"]) for r in out["shares"]}["A"] == (4, 52)
    ratios = [v["ratio"] for g in out["swarm"] if g["cond"] == "A" for v in g["values"] if v["task"] == t["id"]]
    assert len(ratios) == 3


def test_parallel_sets_slope_chart_and_class_panels_have_no_facts(made):
    """Parallel sets, slope chart and class panels repeat other figures; the facts hold no keys for them."""
    assert not {"parallel", "slope", "panels"} & set(made)


# ---------------------------------------------------------------- the data thread


def _cell(out: dict, task: str, cond: str) -> dict:
    return next(x["cells"][cond] for c in out["ledger"] for x in c["tasks"] if x["task"] == task)


def _fit_task(cls: str, *, c: bool | None = None) -> dict:
    return next(t for t in FIT if t["class"] == cls and (c is None or ("C" in t["required"]) is c))


def test_swarm_and_ledger_marks_follow_correct_not_the_ratio():
    data = _data()
    t = _fit_task("numerical")
    for r in data["rows"]:
        if r["task_id"] == t["id"] and r["_cond"] == "A":
            r["correct"] = "True"  # off by a factor 2, yet the scorer said correct: the mark is filled
        if r["task_id"] == t["id"] and r["_cond"] == "C":
            r["correct"] = "False"  # off by 0.1 %, yet the scorer said wrong (a wrong scope flag): the mark is open
    curve = next(x for x in TASKS.values() if x["answer_schema"] == "curve")
    for r in data["rows"]:
        if r["task_id"] == curve["id"] and r["_cond"] == "A":
            r["correct"] = "True"  # within curve_abs, outside curve_rel
    out = facts._benchmark(data, {}, None)
    swarm = {(g["cond"], v["task"]): v for g in out["swarm"] for v in g["values"]}
    assert swarm[("A", t["id"])]["ratio"] > 1 and swarm[("A", t["id"])]["ok"] is True
    assert swarm[("C", t["id"])]["ratio"] < 1 and swarm[("C", t["id"])]["ok"] is False
    assert all(isinstance(v["ok"], bool) for v in swarm.values())
    assert _cell(out, t["id"], "A")["ok"] is True and _cell(out, t["id"], "C")["ok"] is False
    assert _cell(out, curve["id"], "A")["ok"] is True


def test_literature_rows_show_c_when_the_task_requires_it():
    data = _data()
    t = next(x for x in TASKS.values() if x["class"] == "literature_new" and "C" in x["required"])
    for r in data["rows"]:
        if r["task_id"] == t["id"] and r["_cond"] == "B":
            ref = t["reference"]
            r.update(correct="False", dq=str(ref["Dq"]), b=str(ref["B"]), c=str(ref["C"] * 1.5), rel_err_dq="0.0",
                     rel_err_b="0.0", rel_err_c="0.5")
    out = facts._benchmark(data, {}, None)
    s = next(x for x in out["literature"] if x["task"] == t["id"])
    assert s["required"] == t["required"]
    assert s["oracle"]["C"] == t["reference"]["C"] and s["tol"]["C"] == t["tolerance"]["C"]
    assert s["reported"]["B"]["C"] == pytest.approx(t["reference"]["C"] * 1.5) and s["reported"]["B"]["ok"] is False
    assert "C" in s["paper"]
    no_c = next(x for x in out["literature"] if "C" not in x["required"])
    assert no_c["oracle"].get("C") is None and no_c["tol"].get("C") is None


def test_an_answer_without_a_required_value_has_no_ratio_in_swarm_and_ledger():
    data = _data()
    t = _fit_task("racah_c", c=True)
    for r in data["rows"]:
        if r["task_id"] == t["id"] and r["_cond"] == "A":
            r.update(c="", rel_err_c="")
    out = facts._benchmark(data, {}, None)
    ratios = [v.get("ratio") for g in out["swarm"] if g["cond"] == "A" for v in g["values"] if v["task"] == t["id"]]
    assert ratios in ([], [None])
    assert _cell(out, t["id"], "A")["value"] is None


def test_the_swarm_says_how_many_answers_it_leaves_out():
    data = _data()
    t = _fit_task("racah_c", c=True)
    for r in data["rows"]:
        if r["task_id"] == t["id"] and r["_cond"] == "A":
            r.update(c="", rel_err_c="")
    out = facts._benchmark(data, {}, None)
    groups = {g["cond"]: g for g in out["swarm"]}
    n_fit = len(FIT)
    assert groups["B"]["n_runs"] == len(groups["B"]["values"]) == n_fit
    assert groups["A"]["n_runs"] == n_fit and len(groups["A"]["values"]) == n_fit - 1
    notes = [n for n in out["notes"] if n["kind"] == "error size"]
    assert [n["count"] for n in notes] == [1] and "required value" in notes[0]["text"]
    assert not [n for n in facts._benchmark(_data(), {}, None)["notes"] if n["kind"] == "error size"]


def test_the_bench_counts_the_cells_below_the_planned_k_and_the_rescued_answers():
    data = _data()
    n = len(TASKS) * 3
    assert facts._benchmark(data, {}, None)["completeness"] == {"k": 1, "cells": n, "short": 0, "missing": 0,
                                                                "rescued": 0}
    t = TASKS["P-experimental-01"]
    data["rows"] += [_row("m1", "A", t, True, k=2), _row("m1", "A", t, True, k=3)]
    data["sets"] = [{"name": "set", "manifest": {"k": 3}}]
    next(r for r in data["rows"] if r["_cond"] == "B")["rescued"] = "True"
    out = facts._benchmark(data, {}, None)["completeness"]
    # only the A cell of t has its three runs; the other cells have one of three
    assert out == {"k": 3, "cells": n, "short": n - 1, "missing": 2 * (n - 1), "rescued": 1}
    # a task without any evaluable run of a condition is a cell with all runs missing
    data["rows"] = [r for r in data["rows"] if not (r["_cond"] == "C" and r["task_id"] == t["id"])]
    out = facts._benchmark(data, {}, None)["completeness"]
    assert out["short"] == n - 1 and out["missing"] == 2 * (n - 1) + 1


def test_a_curve_cell_uses_the_scorers_tolerance_ratio_not_the_relative_error_alone():
    t = next(t for t in TASKS.values() if t["answer_schema"] == "curve")
    row = _row("m1", "A", t, True)
    row.update(curve_max_rel_err="0.072", curve_tol_ratio="0.97")  # passes by curve_abs; 0.072 / curve_rel is 2.4
    assert facts._run_cell(row, t)["value"] == pytest.approx(0.97)
    row.pop("curve_tol_ratio")  # a scores table without the column: the plain relative error
    assert facts._run_cell(row, t)["value"] == pytest.approx(0.072 / t["tolerance"]["curve_rel"])
    row["curve_tol_ratio"] = ""  # a malformed answer: no value
    assert facts._run_cell(row, t)["value"] is None


def test_a_pairing_answer_with_a_wrong_ground_term_is_not_a_full_share():
    t = next(t for t in TASKS.values() if t["answer_schema"] == "pairing")
    row = _row("m1", "A", t, False)
    row.update(edge_f1="1.0", node_precision="1.0", node_recall="1.0", ground_correct="False")
    cell = facts._run_cell(row, t)
    assert (cell["kind"], cell["value"], cell["need"], cell["ok"]) == ("share", 0.0, 1.0, False)
    row.update(ground_correct="True", correct="True")
    assert facts._run_cell(row, t)["value"] == 1.0
    row["ground_correct"] = ""  # a table without the column
    assert facts._run_cell(row, t)["value"] == 1.0


def test_task_verdicts_use_the_majority_of_the_runs_everywhere():
    data = _data()
    t = TASKS["P-experimental-01"]  # A solves experimental: k1 correct, k2 wrong is one of two
    data["rows"].append(_row("m1", "A", t, False, k=2))
    out = facts._benchmark(data, {}, None)
    assert _cell(out, t["id"], "A")["ok"] is False
    lit = next(s for s in out["literature"] if s["task"] == t["id"])
    assert lit["reported"]["A"]["ok"] is False
    cls = next(c for c in out["classes"] if c["class"] == "experimental")
    assert cls["marks"]["A"][0] is False
    row = next(x for b in out["tasks_view"] for x in b["tasks"] if x["id"] == t["id"])
    assert row["answers"]["A"]["ok"] is False
    assert (row["answers"]["A"]["n_runs"], row["answers"]["A"]["n_correct"]) == (2, 1)


def test_a_scoring_failure_of_a_run_set_becomes_a_data_note():
    data = _data()
    data["notes"] = ["set: scoring failed (ValueError)"]
    out = facts._benchmark(data, {}, None)
    hits = [n for n in out["notes"] if "scoring failed" in n["text"]]
    assert len(hits) == 1 and hits[0]["count"] >= 1 and isinstance(hits[0]["kind"], str)
    assert facts._benchmark(_data(), {}, None)["notes"] == []


def test_a_run_key_that_occurs_twice_among_the_evaluable_runs_is_an_error():
    data = _data()
    t = TASKS["P-closed_form-02"]
    twin = _row("m1", "B", t, True)
    twin["_set"] = "another-set"
    data["rows"].append(twin)
    with pytest.raises(ValueError, match="P-closed_form-02"):
        facts._benchmark(data, {}, None)
    # the same key among runs that are not evaluable is no error
    data["rows"][-1]["_na"] = "na429"
    facts._benchmark(data, {}, None)


def test_the_header_names_the_effort_and_the_planned_k_of_the_manifest():
    data = _data()
    data["sets"] = [{"name": "set", "manifest": {"effort": "medium", "k": 2, "args": {"k": 2}}}]
    h = facts._benchmark(data, {}, None)["header"]
    assert h["effort"] == "medium" and h["k_planned"] == 2 and h["k"] == 1


def test_pairing_tolerance_names_the_ground_terms():
    out = facts._benchmark(_data(), {}, None)
    pairing = next(c for c in out["classes"] if c["class"] == "pairing")
    assert "ground terms" in pairing["tolerance"]


def test_rows_of_other_conditions_and_non_pilot_tasks_are_counted_in_the_notes():
    data = _data()
    other = _row("m1", "A", TASKS["P-closed_form-01"], True)
    other.update(condition="D", _cond="D")
    stray = _row("m1", "A", TASKS["P-closed_form-01"], True)
    stray.update(task_id="C-closed_form-99", _task=None)
    data["rows"] += [other, stray]
    out = facts._benchmark(data, {}, None)
    assert sorted(n["count"] for n in out["notes"]) == [1, 1]
    assert len({n["kind"] for n in out["notes"]}) == 2
    assert out["header"]["n_runs"] == 150


def test_a_missing_api_time_and_cost_stay_missing():
    data = _data()
    first = data["rows"][0]
    first.update(api_duration_s="", cost_usd="")
    out = facts._benchmark(data, {}, None)
    run = next(r for r in out["cost"]["runs"] if r["cond"] == first["_cond"] and r["task"] == first["task_id"])
    assert run["values"]["api_duration_s"] is None  # no fall back to the wall time
    assert run["values"]["cost_usd"] is None and run["values"]["duration_s"] == 10.0


def test_cost_sums_say_not_recorded_and_count_the_runs_without_a_cost():
    bench = {"header": {"conds": ["A", "B"]}, "runs": [
        {"cond": "A", "outcome": "correct", "values": {"cost_usd": None}},
        {"cond": "A", "outcome": "gross", "values": {"cost_usd": None}},
        {"cond": "B", "outcome": "correct", "values": {"cost_usd": 0.5}},
        {"cond": "B", "outcome": "gross", "values": {"cost_usd": None}}]}
    rows = {r["cond"]: r for r in full._cost_rows(bench)}
    assert rows["A"]["total"] == "not recorded" and rows["A"]["missing"] == 2
    assert rows["B"]["total"] == "0.50" and rows["B"]["missing"] == 1
    assert "0.00" not in {rows["A"]["total"], rows["A"]["correct_cost"]}


def test_the_header_flags_the_cost_of_a_model_that_is_not_a_claude_model_as_an_estimate():
    assert facts._benchmark(_data(("claude-sonnet-5-5",)), {}, None)["header"]["cost_is_estimate"] is False
    gateway = facts._benchmark(_data(("qwen3.5-397b-a17b",)), {}, None)
    assert gateway["header"]["cost_is_estimate"] is True
    assert facts._benchmark({"rows": [], "tasks": TASKS, "sets": [], "notes": []}, {}, None)["header"][
        "cost_is_estimate"] is False


def test_a_wrong_curve_answer_inside_the_gross_limit_is_counted_as_items_wrong():
    data = _data()
    curve = next(x for x in TASKS.values() if x["answer_schema"] == "curve")
    r = next(x for x in data["rows"] if x["task_id"] == curve["id"] and x["_cond"] == "A")
    r["curve_max_rel_err"] = "0.2"
    r["_category"] = failure_category(r, curve)
    assert r["_category"] == "wrong_items"
    out = facts._benchmark(data, {}, None)
    assert {o["cond"]: o["counts"]["items"] for o in out["outcome"]}["A"] == 1


# ---------------------------------------------------------------- the demo run set: transcripts


@pytest.fixture(scope="module")
def demo(tmp_path_factory, demo_runs_root):
    """A copy of the demo run set, its run sets and the facts of the model with the most runs (scores the copy)."""
    root = tmp_path_factory.mktemp("demo")
    runs = root / "runs"
    shutil.copytree(demo_runs_root, runs)
    sets = run_sets_in([runs])
    return runs, sets, facts.benchmark(sets, root / "pages" / "report.html")


def _scores(runs: pathlib.Path, model: str) -> list[dict]:
    out = []
    for f in sorted(runs.rglob("scores.csv")):
        with f.open(encoding="utf-8", newline="") as fh:
            out += [r for r in csv.DictReader(fh) if r["model"] == model]
    return out


def _transcripts(runs: pathlib.Path, model: str, cond: str) -> list[pathlib.Path]:
    return sorted(p for p in runs.rglob("*-k*.jsonl") if p.parts[-4] == model and p.parts[-3] == cond)


def _names(path: pathlib.Path) -> list[str]:
    out, seen = [], set()
    for line in path.read_text(encoding="utf-8").splitlines():
        ev = json.loads(line)
        content = (ev.get("message") or {}).get("content")
        if ev.get("type") == "assistant" and isinstance(content, list):
            for b in content:
                if b.get("type") == "tool_use" and b["id"] not in seen:
                    seen.add(b["id"])
                    out.append(b["name"].removeprefix("mcp__tanabesugano__"))
    return out


def test_the_model_with_the_most_runs_is_chosen_and_the_header_reads_its_manifests(demo):
    runs, sets, out = demo
    h = out["header"]
    assert h["models"] == ["claude-haiku-5-5", "claude-sonnet-5-5", "gemma-4-31b-it"]
    assert h["model"] == "claude-sonnet-5-5"
    rows = _scores(runs, h["model"])
    planned = sum(len(rs["tasks"]) for rs in demo_runs.run_sets() if rs["model"] == h["model"])
    assert h["n_runs"] == len(rows) == planned and h["k"] == max(int(r["k_index"]) for r in rows)
    assert h["endpoint"] == "Anthropic API" and h["oracle"] == "tanabesugano 2.0.0"
    mans = {}
    for s in sets:
        m = json.loads((s.path / "MANIFEST.json").read_text(encoding="utf-8"))
        if "claude-sonnet-5-5" in s.name:
            mans[s.name] = m
    assert h["start"] == min(m["start_time_utc"] for m in mans.values())
    assert h["end"] == max(m["end_time_utc"] for m in mans.values())
    assert set(h["commit"].split(", ")) == {m["git_commit"][:7] for m in mans.values()}


def test_shares_of_the_model_equal_the_correct_flags_of_scores_csv(demo):
    runs, _, out = demo
    rows = _scores(runs, "claude-sonnet-5-5")
    for r in out["shares"]:
        mine = [x for x in rows if x["condition"] == r["cond"]]
        assert r["n"] == len(mine) and r["k"] == sum(x["correct"] == "True" for x in mine)


def test_calls_are_the_ordered_tool_names_of_every_b_and_c_transcript(demo):
    runs, _, out = demo
    for cond in "BC":
        want = sorted((p.name.rsplit("-k", 1)[0], tuple(_names(p)))
                      for p in _transcripts(runs, "claude-sonnet-5-5", cond))
        got = sorted((c["task"], tuple(c["calls"])) for c in out["calls"] if c["cond"] == cond)
        assert got == want and len(got) == sum(r["condition"] == cond for r in _scores(runs, "claude-sonnet-5-5"))
    c_runs = [c for c in out["calls"] if c["cond"] == "C"]
    assert len(c_runs) == len(_transcripts(runs, "claude-sonnet-5-5", "C")) == len(demo_runs.SONNET_C)
    assert all(isinstance(c["correct"], bool) for c in c_runs)
    assert max(c["calls"].count("ts_terms_table_data") for c in c_runs) >= 1
    assert not any(n.startswith("mcp__") for c in c_runs for n in c["calls"])
    assert {c["cond"] for c in out["calls"]} == {"B", "C"}


def test_tool_output_counts_the_characters_each_call_returned(demo):
    runs, _, out = demo
    got = {(r["cond"], r["task"], r["k"]): r for r in out["tool_output"]}
    for cond in "BC":
        for path in _transcripts(runs, "claude-sonnet-5-5", cond):
            task, k = path.name.removesuffix(".jsonl").rsplit("-k", 1)
            ids, chars = {}, {}
            for line in path.read_text(encoding="utf-8").splitlines():
                e = json.loads(line)
                content = (e.get("message") or {}).get("content")
                if not isinstance(content, list):
                    continue
                for it in content:
                    if not isinstance(it, dict):
                        continue
                    if it.get("type") == "tool_use" and it.get("name") != "StructuredOutput":
                        ids[it["id"]] = it["name"].removeprefix("mcp__tanabesugano__")
                    elif it.get("type") == "tool_result" and it.get("tool_use_id") in ids:
                        c = it.get("content")
                        n = len(c) if isinstance(c, str) else sum(len(x.get("text", "")) for x in c or []
                                                                     if isinstance(x, dict) and x.get("type") == "text")
                        chars[it["tool_use_id"]] = chars.get(it["tool_use_id"], 0) + n
            assert [(c["tool"], c["chars"]) for c in got[(cond, task, int(k))]["calls"]] == [
                (name, chars.get(i, 0)) for i, name in ids.items()]


def test_transitions_count_each_direct_succession_of_two_calls_in_c(demo):
    runs, _, out = demo
    want = collections.Counter()
    for p in _transcripts(runs, "claude-sonnet-5-5", "C"):
        names = _names(p)
        want.update(zip(names, names[1:], strict=False))
    assert out["transitions"] == dict(want)
    assert out["transitions"][("ts_fit_spectrum", "StructuredOutput")] >= 1


def test_tools_are_the_server_tool_names_of_the_init_event_then_structured_output(demo):
    runs, _, out = demo
    init = set()
    for p in _transcripts(runs, "claude-sonnet-5-5", "C"):
        for line in p.read_text(encoding="utf-8").splitlines():
            ev = json.loads(line)
            if ev.get("type") == "system" and ev.get("subtype") == "init":
                init |= {t.removeprefix("mcp__tanabesugano__") for t in ev["tools"] if t.startswith("mcp__")}
    assert out["tools"][-1] == "StructuredOutput"
    assert out["tools"][:-1] == sorted(init) and len(init) >= 5 and "ts_fit_spectrum" in init


def test_solution_paths_cover_the_b_runs_that_called_bash(demo):
    runs, _, out = demo
    rows = [r for r in _scores(runs, "claude-sonnet-5-5")
            if r["condition"] == "B" and int(float(r["n_bash_calls"])) > 0]
    paths = out["solution_paths"]
    assert len(paths) == len(rows) >= 1
    assert sorted(p["task"] for p in paths) == sorted(r["task_id"] for r in rows)
    p = paths[0]
    assert p["format"] == "tsbench.solution_path/1" and p["steps"] and "values" in p
    assert not pathlib.Path(p["transcript"]).is_absolute() and p["transcript"].endswith(".jsonl")
    assert isinstance(p["correct"], bool) and p["k"] >= 1
    assert all("stdout" in s and "scripts" in s for s in p["steps"])


def test_a_solution_path_is_given_the_task_of_its_run(demo, monkeypatch):
    runs, sets, out = demo
    seen = []
    real = facts.solution_path

    def spy(p, label=None, task=None, tr=None):
        seen.append(task)
        return real(p, label, task, tr)

    monkeypatch.setattr(facts, "solution_path", spy)
    again = facts.benchmark(sets, runs.parent / "x.html")
    assert len(seen) == len(again["solution_paths"]) >= 1
    assert all(isinstance(t, dict) for t in seen)
    assert sorted(t["id"] for t in seen) == sorted(p["task"] for p in again["solution_paths"])


def test_a_benchmark_reads_each_transcript_once(demo, monkeypatch):
    """The calls, the characters a tool returned and the solution path all come from one parse of a transcript."""
    import builtins

    runs, sets, out = demo
    opened = collections.Counter()
    real_open, real_path_open = builtins.open, pathlib.Path.open

    def count(f):
        if str(f).endswith(".jsonl") and "-k" in pathlib.Path(f).name:
            opened[str(pathlib.Path(f).resolve())] += 1

    def spy_open(f, *a, **kw):
        count(f)
        return real_open(f, *a, **kw)

    def spy_path_open(self, *a, **kw):
        count(self)
        return real_path_open(self, *a, **kw)

    data = dashboard.collect(sets, runs.parent / "x.html", dashboard.load_pilot_tasks())  # scores the run sets
    paths = {x["name"]: pathlib.Path(x["path"]) for x in data["sets"]}
    monkeypatch.setattr(builtins, "open", spy_open)
    monkeypatch.setattr(pathlib.Path, "open", spy_path_open)
    again = facts._benchmark(data, paths, None)
    assert again["calls"] == out["calls"] and again["tool_output"] == out["tool_output"]
    assert again["solution_paths"] == out["solution_paths"]
    assert opened and max(opened.values()) == 1, opened.most_common(3)


def test_a_first_render_of_an_unscored_run_set_parses_each_transcript_once(tmp_path, monkeypatch, demo_runs_root):
    """A run set without scores.csv is scored by `dashboard.collect`; it reads through the reader of the facts, so the
    scorer and the facts do not parse a transcript twice."""
    from tsbench.score import extract
    from tsbench.score.artifacts import TranscriptCache

    runs = tmp_path / "runs"
    shutil.copytree(demo_runs_root / "demo-claude", runs)
    for f in runs.rglob("scores.csv"):
        f.unlink()
    parsed = collections.Counter()
    real = extract.read_transcript

    def spy(path):
        parsed[str(pathlib.Path(path).resolve())] += 1
        return real(path)

    monkeypatch.setattr("tsbench.score.artifacts.read_transcript", spy)
    monkeypatch.setattr("tsbench.score.score.read_transcript", spy)
    monkeypatch.setattr(facts, "read_transcript", spy)
    facts.benchmarks(run_sets_in([runs]), tmp_path / "x.html", TranscriptCache())
    assert parsed and max(parsed.values()) == 1, parsed.most_common(3)


def test_a_settled_file_is_hashed_once_and_a_fresh_file_every_time(tmp_path, monkeypatch):
    """The tree and the provenance table hash the same transcripts: the digest of a file that has not changed for a
    while is kept; a file written a moment ago is read again, since two writes may share one timestamp."""
    import hashlib
    import os
    import time

    f = tmp_path / "a.jsonl"
    f.write_bytes(b"one\n")
    opened = []
    real_open = pathlib.Path.open

    def spy(self, mode="r", *a, **kw):
        if mode == "rb":
            opened.append(self)
        return real_open(self, mode, *a, **kw)

    monkeypatch.setattr(pathlib.Path, "open", spy)
    assert facts._sha256(f) == hashlib.sha256(b"one\n").hexdigest()
    f.write_bytes(b"two\n")  # a fresh file: no memory of the first digest
    assert facts._sha256(f) == hashlib.sha256(b"two\n").hexdigest() and len(opened) == 2
    old = time.time() - 3600
    os.utime(f, (old, old))
    opened.clear()
    first = facts._sha256(f)
    assert facts._sha256(f) == first and len(opened) == 1
    f.write_bytes(b"three\n")
    os.utime(f, (old, old))  # same timestamp, other size: the digest is read again
    assert facts._sha256(f) == hashlib.sha256(b"three\n").hexdigest()


def test_an_attempt_transcript_beside_a_run_is_not_a_run(demo):
    runs, sets, out = demo
    made = []
    try:
        for cond in "BC":
            for t in _transcripts(runs, "claude-sonnet-5-5", cond)[:2]:
                extra = t.with_name(t.name[: -len(".jsonl")] + ".attempt1.jsonl")
                extra.write_text(t.read_text(encoding="utf-8"), encoding="utf-8")
                made.append(extra)
        assert len(made) == 4
        again = facts.benchmark(sets, runs.parent / "x.html")
    finally:
        for extra in made:
            extra.unlink()
    assert again["calls"] == out["calls"] and again["transitions"] == out["transitions"]
    assert [p["transcript"] for p in again["solution_paths"]] == [p["transcript"] for p in out["solution_paths"]]
    assert not any(".attempt" in p["transcript"] for p in again["solution_paths"])


def test_a_skipped_run_set_does_not_shift_the_folders_of_the_others(demo, tmp_path):
    runs, sets, out = demo
    gone = tmp_path / "gone"
    again = facts.benchmark([gone, *sets], tmp_path / "x.html")
    assert again["calls"] == out["calls"] and again["transitions"] == out["transitions"]
    assert [p["transcript"] for p in again["solution_paths"]] == [p["transcript"] for p in out["solution_paths"]]
    lost = [n for n in out["notes"] if n["kind"] == "transcript"]
    assert [n for n in again["notes"] if n["kind"] == "transcript"] == lost
    many = facts.benchmarks([gone, *sets], tmp_path / "x.html")
    assert many[out["header"]["model"]]["calls"] == out["calls"]


def test_benchmark_writes_no_file_beside_the_scores(demo, tmp_path):
    runs, sets, _ = demo
    before = sorted(p.relative_to(runs) for p in runs.rglob("*") if p.is_file())
    facts.benchmark(sets, tmp_path / "x.html")
    assert sorted(p.relative_to(runs) for p in runs.rglob("*") if p.is_file()) == before
    assert not (tmp_path / "x.html").exists()


def test_the_header_names_the_effort_of_its_runs(demo):
    _, _, out = demo
    assert out["header"]["effort"] == "medium"


def test_a_scored_run_without_its_transcript_is_counted_in_the_notes(tmp_path, demo_runs_root):
    runs = tmp_path / "runs"
    shutil.copytree(demo_runs_root / "demo-claude", runs)
    sets = run_sets_in([runs])
    first = facts.benchmark(sets, tmp_path / "r.html")  # scores the copy: scores.csv now holds every run
    assert not [n for n in first["notes"] if "transcript" in n["text"]]
    _transcripts(runs, first["header"]["model"], "B")[0].unlink()
    again = facts.benchmark(sets, tmp_path / "r.html")
    hits = [n for n in again["notes"] if "transcript" in n["text"]]
    assert len(hits) == 1 and hits[0]["count"] == 1


def _keep(runs: pathlib.Path, *models: str) -> set[tuple[str, str, str, int]]:
    return {(m, r["condition"], r["task_id"], int(r["k_index"])) for m in models for r in _scores(runs, m)
            if r["evaluable"] == "True"}


def test_the_schedule_holds_the_evaluable_runs_it_is_given_by_model(demo, tmp_path):
    runs, sets, out = demo
    model = out["header"]["model"]
    keep = _keep(runs, model)
    plat = facts.platform(sets, keep=keep)  # the run sets hold the (condition, task, k) of every model
    got = plat["schedule"]["runs"]
    assert len(got) == len(keep) and all((r["model"], r["cond"], r["task"], r["k"]) in keep for r in got)
    # a kept run whose .meta.json is lost: the difference is a note, not a silent gap
    lost = tmp_path / "runs"
    shutil.copytree(runs, lost)
    _transcripts(lost, model, "B")[0].with_suffix(".meta.json").unlink()
    plat = facts.platform(run_sets_in([lost]), keep=keep)
    missing = len(keep) - len(plat["schedule"]["runs"])
    assert missing == 1
    assert missing in [n["count"] for n in plat["notes"]]


def test_the_schedule_of_every_model_holds_the_runs_of_each(demo):
    runs, sets, out = demo
    keep = _keep(runs, *out["header"]["models"])
    got = facts.platform(sets, keep=keep)["schedule"]["runs"]
    assert {r["model"] for r in got} == set(out["header"]["models"])
    assert all((r["model"], r["cond"], r["task"], r["k"]) in keep for r in got)
    assert len({(r["model"], r["cond"], r["task"], r["k"]) for r in got}) == len(got)


@pytest.fixture(scope="module")
def demo_benches(demo):
    runs, sets, _ = demo
    return facts.benchmarks(sets, runs.parent / "pages" / "report.html")


def test_benchmarks_hold_every_model_with_the_most_evaluable_runs_first(demo, demo_benches):
    runs, _, out = demo
    models = out["header"]["models"]
    evaluable = {m: sum(r["evaluable"] == "True" for r in _scores(runs, m)) for m in models}
    assert list(demo_benches) == sorted(models, key=lambda m: (-evaluable[m], m))
    assert list(demo_benches)[0] == out["header"]["model"] == "claude-sonnet-5-5"
    assert demo_benches["claude-sonnet-5-5"]["header"] == out["header"]
    assert demo_benches["claude-sonnet-5-5"]["shares"] == out["shares"]
    for m, b in demo_benches.items():
        assert b["header"]["model"] == m and b["header"]["n_evaluable"] == evaluable[m]


# ---------------------------------------------------------------- the platform


def _hash(b: bytes) -> str:
    import hashlib
    return hashlib.sha256(b).hexdigest()


def _run_set(root: pathlib.Path) -> pathlib.Path:
    """A small run set of one model: three transcripts, manifest, inputs (`_second_model` adds a second model)."""
    d = root / "rs"
    (d / "inputs").mkdir(parents=True)
    plan = b'{"run": 1}\n{"run": 2}\n'
    (d / "inputs" / "plan.jsonl").write_bytes(plan)
    (d / "plan.jsonl").write_bytes(plan)
    (d / "plan.sha256").write_text(f"{_hash(plan)}  plan.jsonl\n", encoding="utf-8")
    (d / "inputs" / "hashes.json").write_text(json.dumps(
        {"plan_file_sha256": _hash(plan), "plan_id": "pid", "b_stack_sha256": "bs" * 32}), encoding="utf-8")
    runs = [("A", "P-closed_form-01", "2026-10-30T22:00:00+00:00", 30.0, 0.5),
            ("B", "P-closed_form-02", "2026-10-30T22:00:10+00:00", 60.0, 1.5),
            ("C", "P-closed_form-01", "2026-10-30T22:01:00+00:00", 90.0, 2.0)]
    transcripts = {}
    for cond, task, start, secs, cost in runs:
        f = d / "m" / cond / "medium"
        f.mkdir(parents=True, exist_ok=True)
        body = b'{"type": "system"}\n'
        (f / f"{task}-k1.jsonl").write_bytes(body)
        transcripts[f"m/{cond}/medium/{task}-k1"] = _hash(body)
        (f / f"{task}-k1.meta.json").write_text(json.dumps(
            {"condition": cond, "task_id": task, "started_utc": start, "wall_time_s": secs, "cost_usd": cost,
             "plan_id": "pid"}), encoding="utf-8")
    (d / "m" / "outside.meta.json").write_text(json.dumps(
        {"condition": "A", "task_id": "P-not-a-task-01", "started_utc": "2026-10-30T23:00:00+00:00",
         "wall_time_s": 5.0, "cost_usd": 9.0}), encoding="utf-8")
    manifest = {"host": "host-1", "platform": "Linux-5.15-x86_64", "python_version": "3.14.8 (main)",
                "claude_version": {"real": "2.1.312 (Claude Code)"}, "effort": "medium",
                "args": {"gateway": True}, "tanabesugano_version": "2.0.0",
                "b_stack": {"python": "3.14.9", "digest": "bs" * 32,
                            "packages": {"numpy": "2.5.4", "scipy": "1.18.1"}},
                "start_time_utc": "2026-10-30T22:00:00+00:00", "end_time_utc": "2026-10-30T22:03:00+00:00",
                "counts": {"planned": 3, "done": 2, "skipped": 1}, "total_cost_usd": 4.0,
                "plan_sha256": _hash(plan), "plan_id": "pid", "transcripts": transcripts, "git_commit": "abc1234def"}
    (d / "MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
    (d / "scores.csv").write_text("model\nm\n", encoding="utf-8")
    return d


def _second_model(d: pathlib.Path, model: str = "m2") -> None:
    """Sidecars of a second model that name it, with the (condition, task, k) of the first model's runs."""
    for cond, task, start in (("A", "P-closed_form-01", "2026-10-30T22:02:00+00:00"),
                              ("C", "P-closed_form-01", "2026-10-30T22:02:30+00:00")):
        f = d / model / cond / "medium"
        f.mkdir(parents=True, exist_ok=True)
        (f / f"{task}-k1.meta.json").write_text(json.dumps(
            {"model": model, "condition": cond, "task_id": task, "k": 1, "started_utc": start, "wall_time_s": 20.0,
             "cost_usd": 0.25}), encoding="utf-8")


def test_a_resumed_run_set_gives_one_window_and_the_done_runs_of_every_session(tmp_path):
    d = _run_set(tmp_path)
    first = {"start_time_utc": "2026-10-30T17:19:28+00:00", "end_time_utc": "2026-10-30T19:14:25+00:00",
             "counts": {"planned": 3, "done": 1, "skipped": 0}, "total_cost_usd": 1.0}
    (d / "MANIFEST.prev-20261030T220127960661Z.json").write_text(json.dumps(first), encoding="utf-8")
    out = facts.platform([d])
    assert out["schedule"]["manifest"] == {"start": "2026-10-30T17:19:28+00:00", "end": "2026-10-30T22:03:00+00:00",
                                           "planned": 3, "done": 3, "skipped": 0, "total_cost": 4.0}
    assert facts._manifest(as_run_sets([d])[0])["start_time_utc"] == "2026-10-30T17:19:28+00:00"


def test_platform_rows_state_host_system_versions_and_what_was_not_recorded(tmp_path):
    d = _run_set(tmp_path)
    out = facts.platform(run_sets_in([d]))
    rows = {r["item"]: r for r in out["rows"]}
    assert rows["Host"] == {"item": "Host", "value": "host-1", "source": "MANIFEST.json"}
    assert rows["Operating system"]["value"] == "Linux-5.15-x86_64"
    assert rows["Python"]["value"] == "3.14.8"
    assert rows["Claude Code client"]["value"] == "2.1.312"
    assert "Effort" not in rows  # the run settings state it
    assert rows["Model endpoint"]["value"] == "gateway"
    assert rows["Oracle and server"]["value"] == "tanabesugano 2.0.0"
    assert rows["B stack · Python"]["value"] == "3.14.9" and rows["B stack · numpy"]["value"] == "2.5.4"
    assert rows["B stack · scipy"]["value"] == "1.18.1"
    assert rows["B stack · numpy"]["source"].startswith("MANIFEST.json")
    assert rows["CPU cores, memory"] == {"item": "CPU cores, memory", "value": "not recorded", "source": "–"}
    assert rows["CPU steal time"]["value"] == "not recorded"
    items = [r["item"] for r in out["rows"]]
    assert items.index("Host") < items.index("B stack · Python") < items.index("CPU cores, memory")


def test_platform_schedule_lists_the_runs_of_pilot_tasks_and_the_manifest_totals(tmp_path):
    d = _run_set(tmp_path)
    sch = facts.platform(run_sets_in([d]))["schedule"]
    assert sch["runs"] == [
        {"model": None, "cond": "A", "task": "P-closed_form-01", "k": 1, "start": "2026-10-30T22:00:00+00:00",
         "seconds": 30.0, "cost": 0.5, "cost_is_estimate": False},
        {"model": None, "cond": "B", "task": "P-closed_form-02", "k": 1, "start": "2026-10-30T22:00:10+00:00",
         "seconds": 60.0, "cost": 1.5, "cost_is_estimate": False},
        {"model": None, "cond": "C", "task": "P-closed_form-01", "k": 1, "start": "2026-10-30T22:01:00+00:00",
         "seconds": 90.0, "cost": 2.0, "cost_is_estimate": False}]
    assert sch["manifest"] == {"start": "2026-10-30T22:00:00+00:00", "end": "2026-10-30T22:03:00+00:00",
                               "planned": 3, "done": 2, "skipped": 1, "total_cost": 4.0}


def test_platform_tree_lists_files_and_folders_with_sizes_hashes_and_the_recorded_links(tmp_path):
    d = _run_set(tmp_path)
    tree = facts.platform(run_sets_in([d]))["tree"]
    by = {e["path"]: e for e in tree["entries"]}
    assert by["MANIFEST.json"]["bytes"] == (d / "MANIFEST.json").stat().st_size and not by["MANIFEST.json"]["is_dir"]
    plan = (d / "inputs" / "plan.jsonl").read_bytes()
    assert by["inputs/plan.jsonl"]["hash"] == _hash(plan) and by["inputs/plan.jsonl"]["bytes"] == len(plan)
    assert by["inputs"]["is_dir"] and by["inputs"]["hash"] is None
    assert by["inputs"]["bytes"] == sum((d / "inputs" / f).stat().st_size for f in ("plan.jsonl", "hashes.json"))
    # folders first, then files, each in order of the lower-case name; depth first
    assert [e["path"] for e in tree["entries"]] == [
        "inputs", "inputs/hashes.json", "inputs/plan.jsonl",
        "m", "m/A", "m/A/medium", "m/A/medium/P-closed_form-01-k1.jsonl", "m/A/medium/P-closed_form-01-k1.meta.json",
        "m/B", "m/B/medium", "m/B/medium/P-closed_form-02-k1.jsonl", "m/B/medium/P-closed_form-02-k1.meta.json",
        "m/C", "m/C/medium", "m/C/medium/P-closed_form-01-k1.jsonl", "m/C/medium/P-closed_form-01-k1.meta.json",
        "m/outside.meta.json", "MANIFEST.json", "plan.jsonl", "plan.sha256", "scores.csv"]
    assert by["m"]["bytes"] == sum(f.stat().st_size for f in (d / "m").rglob("*") if f.is_file())
    links = {(x["from"], x["to"], x["field"]): x["ok"] for x in tree["chain"]}
    assert links[("inputs/plan.jsonl", "MANIFEST.json", "plan_sha256")] is True
    assert links[("inputs/plan.jsonl", "inputs/hashes.json", "plan_file_sha256")] is True
    assert links[("plan.jsonl", "plan.sha256", "plan.sha256")] is True
    assert links[("inputs/plan.jsonl", "MANIFEST.json", "plan_id")] is True
    assert links[("inputs/plan.jsonl", "inputs/hashes.json", "plan_id")] is True
    assert links[("m/A/medium", "MANIFEST.json", "transcripts")] is True
    assert all(x["from"] in by and x["to"] in by for x in tree["chain"])
    assert all(set(x) == {"from", "to", "field", "ok"} for x in tree["chain"])
    assert tree["hashes"]["plan_id"] == "pid" and tree["hashes"]["b_stack_sha256"] == "bs" * 32


def test_a_hash_that_does_not_match_stays_in_the_chain_marked_not_ok(tmp_path):
    d = _run_set(tmp_path)
    (d / "inputs" / "plan.jsonl").write_bytes(b'{"run": 1}\n{"run": 3}\n')  # edited after the manifest was written
    body = d / "m" / "B" / "medium" / "P-closed_form-02-k1.jsonl"
    body.write_bytes(b'{"type": "edited"}\n')
    links = {(x["from"], x["to"], x["field"]): x["ok"] for x in facts.platform(run_sets_in([d]))["tree"]["chain"]}
    assert links[("inputs/plan.jsonl", "MANIFEST.json", "plan_sha256")] is False
    assert links[("inputs/plan.jsonl", "inputs/hashes.json", "plan_file_sha256")] is False
    assert links[("plan.jsonl", "plan.sha256", "plan.sha256")] is True  # the copy at the top was not edited
    assert links[("m/B/medium", "MANIFEST.json", "transcripts")] is False
    assert links[("m/A/medium", "MANIFEST.json", "transcripts")] is True


def test_platform_checks_the_hash_chain_of_every_run_set_not_only_the_first(tmp_path):
    first, second = _run_set(tmp_path / "a"), _run_set(tmp_path / "b")
    (second / "m" / "B" / "medium" / "P-closed_form-02-k1.jsonl").write_bytes(b'{"type": "edited"}\n')
    out = facts.platform(run_sets_in([first, second]))
    assert [c["set"] for c in out["chains"]] == [rs.name for rs in run_sets_in([first, second])]
    ok, bad = out["chains"]
    assert ok["broken"] == [] and ok["links"] > 0
    assert bad["links"] == ok["links"]
    assert [(x["from"], x["to"], x["field"]) for x in bad["broken"]] == [("m/B/medium", "MANIFEST.json", "transcripts")]
    assert out["tree"] == facts.platform(run_sets_in([first]))["tree"]  # the figure still draws the first set


def test_platform_keeps_only_the_runs_it_is_given(tmp_path):
    d = _run_set(tmp_path)
    out = facts.platform(run_sets_in([d]), keep={("m", "A", "P-closed_form-01", 1), ("m", "C", "P-closed_form-01", 1)})
    assert [(r["model"], r["cond"], r["task"]) for r in out["schedule"]["runs"]] == [("m", "A", "P-closed_form-01"),
                                                                                     ("m", "C", "P-closed_form-01")]
    assert out["notes"] == []
    assert len(facts.platform(run_sets_in([d]))["schedule"]["runs"]) == 3  # keep=None: every run of a pilot task


def test_a_missing_wall_time_or_cost_stays_missing_in_the_schedule(tmp_path):
    d = _run_set(tmp_path)
    meta = d / "m" / "B" / "medium" / "P-closed_form-02-k1.meta.json"
    rec = json.loads(meta.read_text(encoding="utf-8"))
    del rec["cost_usd"], rec["wall_time_s"]
    meta.write_text(json.dumps(rec), encoding="utf-8")
    runs = {r["cond"]: r for r in facts.platform(run_sets_in([d]))["schedule"]["runs"]}
    assert runs["B"]["cost"] is None and runs["B"]["seconds"] is None
    assert runs["A"]["cost"] == 0.5


def test_a_cost_the_sidecar_calls_unknown_is_not_a_recorded_cost(tmp_path):
    """A run without a result event books 0.0 (or the per-call cap) with cost_unknown: the schedule says "not
    recorded", like the cost table of the scores."""
    d = _run_set(tmp_path)
    meta = d / "m" / "B" / "medium" / "P-closed_form-02-k1.meta.json"
    rec = json.loads(meta.read_text(encoding="utf-8"))
    rec.update(cost_usd=0.0, cost_unknown=True)
    meta.write_text(json.dumps(rec), encoding="utf-8")
    runs = {r["cond"]: r for r in facts.platform(run_sets_in([d]))["schedule"]["runs"]}
    assert runs["B"]["cost"] is None and runs["B"]["seconds"] == 60.0
    assert runs["A"]["cost"] == 0.5


def test_the_schedule_marks_the_cost_of_a_non_claude_model_as_an_estimate(tmp_path):
    """Claude Code prices every model at Claude list prices: for a gateway model that is no real cost."""
    d = _run_set(tmp_path)
    for model, flag in (("gemma-4-31b-it", True), ("claude-sonnet-5-5", False)):
        keep = {(model, c, t, 1) for c, t in (("A", "P-closed_form-01"), ("B", "P-closed_form-02"))}
        runs = facts.platform(run_sets_in([d]), keep=keep)["schedule"]["runs"]
        assert runs and {r["cost_is_estimate"] for r in runs} == {flag}
        assert runs[0]["cost"] == 0.5  # the figure leaves the estimate out, the facts keep the record


def _chain(path: str) -> list[str]:
    parts = path.split("/")
    return ["/".join(parts[: i + 1]) for i in range(len(parts))]


def test_platform_tree_collapses_a_folder_with_many_files(tmp_path):
    d = _run_set(tmp_path)
    big = d / "m" / "A" / "medium"
    for i in range(20):
        (big / f"extra-{i:02d}.txt").write_text("x" * i, encoding="utf-8")
    tree = facts.platform(run_sets_in([d]))["tree"]
    by = {e["path"]: e for e in tree["entries"]}
    assert by["m/A/medium"]["n_files"] == 22 and not any(p.startswith("m/A/medium/") for p in by)
    assert by["m/A/medium"]["bytes"] == sum(f.stat().st_size for f in big.iterdir())
    # a small folder is listed
    assert "n_files" not in by["m/B/medium"] and "m/B/medium/P-closed_form-02-k1.jsonl" in by


def test_platform_tree_leaves_out_the_figures_the_report_writes_beside_a_transcript(tmp_path):
    """The `<task>-k<i>.figs` and `.code` folders are output of the report and the scorer, not records of the run: a
    second render lists the same tree as the first."""
    d = _run_set(tmp_path)
    before = facts.platform(run_sets_in([d]))["tree"]["entries"]
    for ext, name in ((".figs", "a.svg"), (".code", "01.py")):
        out = d / "m" / "B" / "medium" / f"P-closed_form-02-k1{ext}"
        out.mkdir()
        (out / name).write_text("x", encoding="utf-8")
    assert facts.platform(run_sets_in([d]))["tree"]["entries"] == before


def test_platform_of_a_run_set_without_manifest_says_not_recorded(tmp_path):
    d = tmp_path / "bare" / "m" / "A" / "medium"
    d.mkdir(parents=True)
    (d / "P-closed_form-01-k1.jsonl").write_text("{}\n", encoding="utf-8")
    out = facts.platform(run_sets_in([tmp_path / "bare"]))
    rows = {r["item"]: r["value"] for r in out["rows"]}
    assert rows["Host"] == "not recorded" and rows["Claude Code client"] == "not recorded"
    assert out["schedule"]["runs"] == [] and out["schedule"]["manifest"]["planned"] is None
    assert out["tree"]["chain"] == []


def test_platform_of_several_run_sets_joins_their_values(demo):
    _, sets, _ = demo
    out = facts.platform(sets)
    rows = {r["item"]: r["value"] for r in out["rows"]}
    assert rows["Host"] == demo_runs.HOST_LABEL
    gateway, api = rows["Model endpoint"].split(" and ")  # the gateway run sets and the Claude run sets
    assert "gateway" in gateway and api == "Anthropic API"
    assert rows["Oracle and server"].startswith("tanabesugano ")
    assert {r["cond"] for r in out["schedule"]["runs"]} == {"A", "B", "C"}
    assert all(r["task"] in TASKS for r in out["schedule"]["runs"])


# ---------------------------------------------------------------- checks: coverage, mutation, tests, imports


def _cov_file(statements: int, covered: int, funcs: dict | None = None) -> dict:
    return {"summary": {"covered_lines": covered, "num_statements": statements,
                        "percent_covered": 100 * covered / statements if statements else 100.0},
            "functions": funcs or {}}


def _fn(statements: int, covered: int) -> dict:
    return {"summary": {"covered_lines": covered, "num_statements": statements,
                        "percent_covered": 100 * covered / statements if statements else 100.0}}


@pytest.fixture()
def tree(tmp_path):
    """A coverage report, a pytest log, two mutation folders, a source tree and a tests folder, all made up."""
    base = tmp_path / "ci"
    cov = base / "coverage"
    cov.mkdir(parents=True)
    files = {
        "/w/src/tsbench/__init__.py": _cov_file(0, 0),
        "/w/src/tsbench/cli.py": _cov_file(40, 30, {"": _fn(10, 10), "main": _fn(30, 20)}),
        "/w/src/tsbench/score/__init__.py": _cov_file(0, 0),
        "/w/src/tsbench/score/numeric.py": _cov_file(100, 99, {"": _fn(20, 20), "match": _fn(80, 79)}),
        "/w/src/tsbench/score/taxonomy.py": _cov_file(60, 30, {"failure": _fn(60, 30)}),
        "/w/src/tsbench/report/page.py": _cov_file(200, 150, {"Page.render": _fn(120, 100), "": _fn(80, 50)}),
        "/w/src/tsbench/report/facts.py": _cov_file(300, 297),
        "/w/src/tsbench/run/runner.py": _cov_file(50, 50),
        "/w/src/tsbench/_vendor/figura/__init__.py": _cov_file(10, 10),
    }
    (cov / "coverage.json").write_text(json.dumps({"meta": {"timestamp": "2026-10-31T16:47:20.8"}, "files": files}),
                                       encoding="utf-8")
    (cov / "pytest.log").write_text(
        "collected 12 items\n=========================== short test summary info ============================\n"
        "FAILED tests/test_a.py::test_x - AssertionError\n"
        "======= 2 failed, 2447 passed, 2 skipped in 848.34s (0:14:08) =======\n", encoding="utf-8")

    def shard(root: pathlib.Path, name: str, counts: dict, per_module: dict, survivors: list, total: int | None = None):
        d = root / name
        d.mkdir(parents=True)
        (d / f"{name}.json").write_text(json.dumps(
            {"name": name, "total": total if total is not None else sum(counts.values()), "counts": counts,
             "score_pct": 0.0, "per_module": per_module, "survivors": survivors}), encoding="utf-8")

    m1, m2 = base / "mutation", base / "extra"
    surv = [{"mutant": "tsbench.score.numeric.x__safe_name__mutmut_16", "module": "tsbench.score.numeric",
             "diff": "--- a\n+++ b\n"},
            {"mutant": "tsbench.score.numeric.xǁMatcherǁmatch__mutmut_3", "module": "tsbench.score.numeric",
             "diff": "d2"},
            {"mutant": "tsbench.score.taxonomy.xǁShapeǁ__init____mutmut_1", "module": "tsbench.score.taxonomy",
             "diff": "d3"}]
    shard(m1, "score", {"killed": 90, "survived": 3, "timeout": 2},
          {"tsbench.score.numeric": {"killed": 60, "survived": 2, "timeout": 1},
           "tsbench.score.taxonomy": {"killed": 30, "survived": 1, "timeout": 1}}, surv)
    shard(m1, "pending", {}, {}, [])
    (m1 / "pending" / "pending.json").unlink()  # a shard folder without its json: not a result
    shard(m2, "cli-release", {"killed": 38, "survived": 2, "no tests": 1},
          {"tsbench.cli": {"killed": 38, "survived": 2, "no tests": 1}},
          [{"mutant": "tsbench.cli.x_main__mutmut_5", "module": "tsbench.cli", "diff": "d4"}])
    shard(m2, "timeonly", {"timeout": 4}, {"tsbench.run.runner": {"timeout": 4}}, [])

    src = tmp_path / "w" / "src" / "tsbench"
    (src / "score").mkdir(parents=True)
    (src / "run").mkdir()
    (src / "report").mkdir()
    (src / "_vendor").mkdir()
    (src / "__init__.py").write_text("", encoding="utf-8")
    (src / "cli.py").write_text("from tsbench.score import numeric\nfrom tsbench.run.runner import go\n"
                                "import tsbench.report.page\n", encoding="utf-8")
    (src / "score" / "__init__.py").write_text("", encoding="utf-8")
    (src / "score" / "numeric.py").write_text("import math\nfrom tsbench.score.taxonomy import failure, other\n"
                                              "from . import taxonomy\nfrom tsbench._vendor import figura\n",
                                              encoding="utf-8")
    (src / "score" / "taxonomy.py").write_text("def failure():\n    from tsbench.score import numeric\n"
                                               "    from tsbench.score import numeric\n", encoding="utf-8")
    (src / "run" / "runner.py").write_text("from tsbench import score\nfrom tsbench.score.numeric import a\n"
                                           "from ..score.numeric import b\n", encoding="utf-8")
    (src / "report" / "page.py").write_text("x = 1\n", encoding="utf-8")
    (src / "_vendor" / "figura.py").write_text("import tsbench.cli\n", encoding="utf-8")
    t = tmp_path / "w" / "tests"
    (t / "score").mkdir(parents=True)
    (t / "report").mkdir()
    (t / "test_top.py").write_text("def test_a():\n    pass\n\n\ndef helper():\n    pass\n", encoding="utf-8")
    (t / "score" / "test_n.py").write_text("def test_a():\n    pass\n\n\ndef test_b():\n    pass\n", encoding="utf-8")
    (t / "report" / "test_p.py").write_text("class T:\n    def test_c(self):\n        pass\n", encoding="utf-8")
    return base, src, t


def test_checks_reads_the_result_line_of_the_pytest_log(tree):
    base, src, t = tree
    out = facts.checks(base / "coverage" / "coverage.json", [base / "mutation"], src, t)
    assert out["tests"] == {"passed": 2447, "failed": 2, "skipped": 2, "seconds": 848.34,
                            "line": "2 failed, 2447 passed, 2 skipped in 848.34s (0:14:08)"}


def test_checks_counts_test_functions_per_folder_of_tests(tree):
    base, src, t = tree
    out = facts.checks(base / "coverage" / "coverage.json", [base / "mutation"], src, t)
    assert out["tests_per_folder"] == [{"label": "score", "value": 2}, {"label": "(top level)", "value": 1},
                                       {"label": "report", "value": 1}]


def test_checks_coverage_total_packages_and_files_with_functions(tree):
    base, src, t = tree
    cov = facts.checks(base / "coverage" / "coverage.json", [base / "mutation"], src, t)["coverage"]
    assert cov["total"] == {"covered": 666, "statements": 760, "pct": pytest.approx(100 * 666 / 760),
                            "reported_pct": None}  # the report of the fixture has no totals
    assert cov["timestamp"] == "2026-10-31T16:47:20.8"
    pk = {p["package"]: p for p in cov["packages"]}
    assert pk["score"] == {"package": "score", "covered": 129, "statements": 160, "pct": pytest.approx(80.625),
                           "modules": 3}
    assert pk["report"]["statements"] == 500 and pk["report"]["covered"] == 447
    assert pk["(top level)"]["modules"] == 2 and pk["_vendor"]["statements"] == 10
    assert [p["package"] for p in cov["packages"]][-1] == "(top level)"
    files = {f["module"]: f for f in cov["files"]}
    n = files["tsbench.score.numeric"]
    assert (n["package"], n["statements"], n["covered"], n["pct"]) == ("score", 100, 99, 99.0)
    assert n["functions"] == [{"name": "(module)", "statements": 20, "pct": 100.0},
                              {"name": "match", "statements": 80, "pct": pytest.approx(98.75)}]
    assert files["tsbench.report.page"]["functions"][0] == {"name": "Page.render", "statements": 120,
                                                            "pct": pytest.approx(100 * 100 / 120)}
    assert files["tsbench.cli"]["package"] == "(top level)"
    assert files["tsbench.score"]["statements"] == 0 and files["tsbench.score"]["pct"] == 100.0
    assert files["tsbench"]["package"] == "(top level)"
    assert files["tsbench._vendor.figura"]["package"] == "_vendor"
    assert files["tsbench.report.facts"]["functions"] == []


def test_every_coverage_percentage_is_lines_covered_over_statements(tmp_path):
    """coverage.py's `percent_covered` counts branches when branch coverage is on; the page uses lines everywhere and
    shows coverage.py's own total beside it."""
    cov = tmp_path / "coverage.json"
    def rec(covered: int, statements: int, branch_pct: float) -> dict:
        return {"summary": {"covered_lines": covered, "num_statements": statements, "percent_covered": branch_pct},
                "functions": {}}

    files = {"/w/src/tsbench/core/a.py": rec(9, 10, 70.0), "/w/src/tsbench/core/b.py": rec(1, 4, 10.0),
             "/w/src/tsbench/cli.py": rec(5, 6, 50.0)}
    cov.write_text(json.dumps({"meta": {}, "files": files, "totals": {"covered_lines": 15, "num_statements": 20,
                                                                       "percent_covered": 42.5}}), encoding="utf-8")
    src = tmp_path / "src" / "tsbench"
    src.mkdir(parents=True)
    out = facts.checks(cov, [], src, None)["coverage"]
    pct = {f["module"]: f["pct"] for f in out["files"]}
    assert pct == {"tsbench.cli": pytest.approx(100 * 5 / 6), "tsbench.core.a": pytest.approx(90.0),
                   "tsbench.core.b": pytest.approx(25.0)}
    assert sum(p["statements"] for p in out["packages"]) == out["total"]["statements"] == 20
    assert sum(p["covered"] for p in out["packages"]) == out["total"]["covered"] == 15
    assert out["total"]["pct"] == pytest.approx(75.0) and out["total"]["reported_pct"] == 42.5
    core = next(p for p in out["packages"] if p["package"] == "core")
    assert core["pct"] == pytest.approx(100 * 10 / 14)


def test_a_shard_whose_counts_differ_from_its_modules_gives_a_note(tree):
    base, src, t = tree
    pending_note = facts.checks(base / "coverage" / "coverage.json", [base / "mutation"], src, t)["mutation"][
        "notes"][0]["text"]
    cov = base / "coverage" / "coverage.json"
    # the fixture's "pending" shard folder has no json: its note is the only one
    assert [n["text"] for n in facts.checks(cov, [base / "mutation", base / "extra"], src, t)["mutation"]["notes"]
            ] == [pending_note]
    odd = base / "odd"
    (odd / "odd").mkdir(parents=True)
    (odd / "odd" / "odd.json").write_text(json.dumps(
        {"name": "odd", "total": 12, "counts": {"killed": 10, "survived": 2},
         "per_module": {"tsbench.score.numeric": {"killed": 7, "survived": 2}}, "survivors": []}), encoding="utf-8")
    notes = facts.checks(cov, [base / "mutation", odd], src, t)["mutation"]["notes"]
    odds = [n for n in notes if "odd" in n["text"]]
    assert len(notes) == 2 and len(odds) == 1 and odds[0]["count"] == 3


def test_a_shard_folder_without_its_json_gives_a_note_and_no_shard(tree):
    base, src, t = tree
    cov = base / "coverage" / "coverage.json"
    mut = facts.checks(cov, [base / "mutation", base / "extra"], src, t)["mutation"]
    assert "pending" not in [s["name"] for s in mut["shards"]]
    assert [(n["kind"], n["count"]) for n in mut["notes"]] == [("mutation", 1)]
    assert "pending" in mut["notes"][0]["text"] and "pending.json" in mut["notes"][0]["text"]
    # another directory that holds the result of that shard removes the note
    done = base / "done" / "pending"
    done.mkdir(parents=True)
    (done / "pending.json").write_text(json.dumps({"name": "pending", "total": 1, "counts": {"killed": 1},
                                                   "per_module": {"tsbench.cli": {"killed": 1}}, "survivors": []}),
                                  encoding="utf-8")
    again = facts.checks(cov, [base / "mutation", base / "done"], src, t)["mutation"]
    assert "pending" in [s["name"] for s in again["shards"]] and not again["notes"]


def test_checks_mutation_merges_the_shard_folders_and_scores_killed_over_decided(tree):
    base, src, t = tree
    mut = facts.checks(base / "coverage" / "coverage.json", [base / "mutation", base / "extra"], src, t)["mutation"]
    assert [s["name"] for s in mut["shards"]] == ["cli-release", "score", "timeonly"]
    score = next(s for s in mut["shards"] if s["name"] == "score")
    assert (score["total"], score["killed"], score["survived"], score["timeout"], score["no_tests"]) == (
        95, 90, 3, 2, 0)
    assert score["score"] == pytest.approx(100 * 90 / 93)
    cli = next(s for s in mut["shards"] if s["name"] == "cli-release")
    assert (cli["total"], cli["killed"], cli["survived"], cli["no_tests"]) == (41, 38, 2, 1)
    assert cli["score"] == pytest.approx(95.0)
    assert {k: mut[k] for k in ("killed", "survived", "timeout", "total")} == {
        "killed": 128, "survived": 5, "timeout": 6, "total": 140}
    assert mut["score"] == pytest.approx(100 * 128 / 133)
    assert score["modules"] == [
        {"module": "tsbench.score.numeric", "killed": 60, "survived": 2, "timeout": 1,
         "score": pytest.approx(100 * 60 / 62)},
        {"module": "tsbench.score.taxonomy", "killed": 30, "survived": 1, "timeout": 1,
         "score": pytest.approx(100 * 30 / 31)}]
    only_timeouts = next(s for s in mut["shards"] if s["name"] == "timeonly")
    assert only_timeouts["score"] is None and only_timeouts["modules"][0]["score"] is None


def test_checks_a_later_folder_adds_shards_and_a_shard_of_the_same_name_replaces(tree):
    base, src, t = tree
    cov = base / "coverage" / "coverage.json"
    one = facts.checks(cov, [base / "mutation"], src, t)["mutation"]
    assert [s["name"] for s in one["shards"]] == ["score"]  # the folder without its json is no shard
    other = base / "other"
    (other / "score").mkdir(parents=True)
    (other / "score" / "score.json").write_text(json.dumps(
        {"name": "score", "total": 10, "counts": {"killed": 10},
         "per_module": {"tsbench.score.numeric": {"killed": 10}}, "survivors": []}), encoding="utf-8")
    two = facts.checks(cov, [base / "mutation", other], src, t)["mutation"]
    assert [(s["name"], s["total"]) for s in two["shards"]] == [("score", 10)]
    assert two["score"] == 100.0


def test_checks_packages_and_files_without_a_mutation_result_are_listed_not_scored(tree):
    base, src, t = tree
    out = facts.checks(base / "coverage" / "coverage.json", [base / "mutation"], src, t)
    assert out["not_mutated"] == ["_vendor", "report", "run", "(top level)"]
    assert out["unmutated"] == [
        {"module": "tsbench._vendor.figura", "coverage": 100.0}, {"module": "tsbench.cli", "coverage": 75.0},
        {"module": "tsbench.report.facts", "coverage": 99.0}, {"module": "tsbench.report.page", "coverage": 75.0},
        {"module": "tsbench.run.runner", "coverage": 100.0}]  # modules without statements have nothing to mutate
    both = facts.checks(base / "coverage" / "coverage.json", [base / "mutation", base / "extra"], src, t)
    assert both["not_mutated"] == ["_vendor", "report"]  # a shard of only timeouts is still a result
    assert [u["module"] for u in both["unmutated"]] == ["tsbench._vendor.figura", "tsbench.report.facts",
                                                       "tsbench.report.page"]


def test_checks_points_join_coverage_to_the_mutation_result_by_dotted_module_name(tree):
    base, src, t = tree
    out = facts.checks(base / "coverage" / "coverage.json", [base / "mutation", base / "extra"], src, t)
    pts = {p["module"]: p for p in out["points"]}
    # run.runner has no decided mutant
    assert set(pts) == {"tsbench.score.numeric", "tsbench.score.taxonomy", "tsbench.cli"}
    p = pts["tsbench.score.numeric"]
    assert p["coverage"] == 99.0 and p["score"] == pytest.approx(100 * 60 / 62) and p["mutants"] == 63
    assert pts["tsbench.cli"]["mutants"] == 41 and pts["tsbench.cli"]["coverage"] == 75.0
    assert pts["tsbench.score.taxonomy"]["coverage"] == 50.0


def test_checks_survivors_carry_shard_module_function_mutant_and_diff(tree):
    base, src, t = tree
    sv = facts.checks(base / "coverage" / "coverage.json", [base / "mutation", base / "extra"], src, t)["survivors"]
    assert [(s["shard"], s["module"], s["function"]) for s in sv] == [
        ("cli-release", "tsbench.cli", "main"),
        ("score", "tsbench.score.numeric", "_safe_name"),
        ("score", "tsbench.score.numeric", "Matcher.match"),
        ("score", "tsbench.score.taxonomy", "Shape.__init__")]
    assert sv[1]["mutant"] == "tsbench.score.numeric.x__safe_name__mutmut_16" and sv[1]["diff"] == "--- a\n+++ b\n"


def test_checks_name_the_survivors_a_shard_counts_but_does_not_list(tree):
    """cli-release counts 2 survived and lists 1: the missing one is named per shard, so the survivor table can
    add up to the survived total."""
    base, src, t = tree
    out = facts.checks(base / "coverage" / "coverage.json", [base / "mutation", base / "extra"], src, t)
    assert out["mutation"]["unlisted"] == [{"shard": "cli-release", "survived": 1}]
    assert out["mutation"]["survived"] == len(out["survivors"]) + 1


@pytest.mark.parametrize(("module", "mutant", "want"), [
    ("tsbench.score.artifacts", "tsbench.score.artifacts.x__safe_name__mutmut_16", "_safe_name"),
    ("tsbench.run.doctor", "tsbench.run.doctor.x__handshake__mutmut_5", "_handshake"),
    ("tsbench.report.x", "tsbench.report.x.x_main__mutmut_259", "main"),
    ("tsbench.run.s", "tsbench.run.s.xǁSessionǁcreate__mutmut_61", "Session.create"),
    ("tsbench.run.s", "tsbench.run.s.xǁSessionǁ__init____mutmut_18", "Session.__init__"),
    ("tsbench.a", "tsbench.a.x_f1_literature_parity__mutmut_275", "f1_literature_parity"),
])
def test_function_name_is_parsed_from_the_mutant_name(module, mutant, want):
    assert facts._function_of(module, mutant) == want


def test_checks_imports_lists_modules_with_coverage_and_counts_import_statements(tree):
    base, src, t = tree
    imp = facts.checks(base / "coverage" / "coverage.json", [base / "mutation"], src, t)["imports"]
    mods = {m["module"]: m for m in imp["modules"]}
    assert set(mods) == {"tsbench.cli", "tsbench.score", "tsbench.score.numeric", "tsbench.score.taxonomy",
                         "tsbench.run.runner", "tsbench.report.page"}
    assert mods["tsbench.score"]["value"] == 100.0 and mods["tsbench.report.page"]["value"] == 75.0
    assert mods["tsbench.score.numeric"] == {"module": "tsbench.score.numeric", "package": "score", "value": 99.0}
    assert mods["tsbench.cli"]["package"] == "(top level)"
    assert not any("_vendor" in m for m in mods)
    edges = {(a, b): n for a, b, n in imp["edges"]}
    # cli: `from tsbench.score import numeric` is an edge to the module numeric, not to the package
    assert edges[("tsbench.cli", "tsbench.score.numeric")] == 1
    assert edges[("tsbench.cli", "tsbench.run.runner")] == 1 and edges[("tsbench.cli", "tsbench.report.page")] == 1
    # numeric: a name that is not a module resolves to the module it is imported from; a relative import is resolved;
    # the vendored package and the standard library are not edges
    assert edges[("tsbench.score.numeric", "tsbench.score.taxonomy")] == 2
    assert not any(b.startswith("tsbench._vendor") or a.startswith("tsbench._vendor") for a, b in edges)
    # taxonomy imports numeric twice inside a function: two statements
    assert edges[("tsbench.score.taxonomy", "tsbench.score.numeric")] == 2
    # runner: `from tsbench import score` is an edge to the package; the absolute and the relative form are two
    # statements
    assert edges[("tsbench.run.runner", "tsbench.score")] == 1
    assert edges[("tsbench.run.runner", "tsbench.score.numeric")] == 2
    assert all(a != b for a, b in edges) and imp["edges"] == sorted(imp["edges"])


def test_a_run_whose_category_cannot_be_computed_is_counted_in_a_note(tmp_path, monkeypatch):
    from tsbench.score import taxonomy

    d = _run_set(tmp_path)
    (d / "scores.csv").write_text("model,condition,task_id,k_index,correct,has_result\n"
                                  "m,A,P-closed_form-01,1,False,True\nm,B,P-closed_form-02,1,True,True\n",
                                  encoding="utf-8")
    monkeypatch.setattr(taxonomy, "failure_category", lambda row, task: 1 / 0)
    data = facts.dashboard.collect(run_sets_in([d]), tmp_path / "r.html", TASKS, score_missing=False)
    assert [r["_category"] for r in data["rows"]] == ["wrong", "correct"]
    assert "rs: category failed for 2 runs (ZeroDivisionError)" in data["notes"]
    assert "rs: 1 transcript has no scores row (run tsbench score)" in data["notes"]  # the hand-made table is partial


def test_a_run_set_note_with_a_count_enters_the_notes_with_that_count():
    from types import SimpleNamespace

    text = "rs: 4 transcripts have no scores row (run tsbench score)"
    data = {"notes": [text, "rs: no scores"], "note_counts": {text: 4}}
    got = facts._notes(data, [], SimpleNamespace(rows=[]), {})
    assert [(n["text"], n["count"]) for n in got] == [(text, 4), ("rs: no scores", 1)]


def test_platform_keeps_the_sidecars_of_the_models_in_keep_only(tmp_path):
    d = _run_set(tmp_path)
    meta = d / "m" / "A" / "medium" / "P-closed_form-01-k1.meta.json"
    rec = json.loads(meta.read_text(encoding="utf-8"))
    meta.write_text(json.dumps({**rec, "model": "m", "k": 1}), encoding="utf-8")
    assert len(facts.platform(run_sets_in([d]), keep={("m", "A", "P-closed_form-01", 1)})["schedule"]["runs"]) == 1
    other = facts.platform(run_sets_in([d]), keep={("another", "A", "P-closed_form-01", 1)})
    assert other["schedule"]["runs"] == []
    assert [n["count"] for n in other["notes"]] == [1]  # the run of keep that the schedule lacks


def test_platform_of_two_models_matches_a_sidecar_without_a_model_only_when_keep_names_one_model(tmp_path):
    d = _run_set(tmp_path)  # the sidecars of model m carry no model field
    _second_model(d)
    sets = run_sets_in([d])
    both = {("m", "A", "P-closed_form-01", 1), ("m2", "A", "P-closed_form-01", 1), ("m2", "C", "P-closed_form-01", 1)}
    out = facts.platform(sets, keep=both)
    assert [(r["model"], r["cond"], r["start"]) for r in out["schedule"]["runs"]] == [
        ("m2", "A", "2026-10-30T22:02:00+00:00"), ("m2", "C", "2026-10-30T22:02:30+00:00")]
    assert [n["count"] for n in out["notes"]] == [1]  # the run of m: no sidecar names it
    only = facts.platform(sets, keep={("m", "A", "P-closed_form-01", 1), ("m", "B", "P-closed_form-02", 1)})
    assert [(r["model"], r["cond"], r["start"]) for r in only["schedule"]["runs"]] == [
        ("m", "A", "2026-10-30T22:00:00+00:00"), ("m", "B", "2026-10-30T22:00:10+00:00")]
    assert only["notes"] == []
    every = facts.platform(sets)["schedule"]["runs"]  # keep=None: every sidecar of a pilot task
    assert [(r["model"], r["cond"]) for r in every] == [(None, "A"), (None, "B"), (None, "C"), ("m2", "A"),
                                                        ("m2", "C")]


def test_the_run_records_of_the_bench_carry_their_k(made):
    assert {r["k"] for r in made["runs"]} == {1}
    data = _data()
    t = TASKS["P-closed_form-01"]
    data["rows"].append(_row("m1", "A", t, False, k=2))
    out = facts._benchmark(data, {}, None)
    assert sorted(r["k"] for r in out["runs"] if r["cond"] == "A" and r["task"] == t["id"]) == [1, 2]


def test_a_ledger_cell_says_how_many_runs_stand_behind_it():
    data = _data()
    t = TASKS["P-experimental-01"]
    data["rows"].append(_row("m1", "A", t, False, k=2))
    cell = _cell(facts._benchmark(data, {}, None), t["id"], "A")
    assert (cell["n_runs"], cell["n_correct"], cell["ok"]) == (2, 1, False)
    # not solved: the value is that of the wrong run, relative error 1.0 over the tighter tolerance (Dq 5 %)
    assert cell["value"] == pytest.approx(1.0 / t["tolerance"]["Dq"])


def test_the_value_of_a_cell_comes_only_from_the_runs_on_the_side_of_its_verdict():
    t = TASKS["P-experimental-01"]
    # k = 2, one correct and one wrong run: not solved, the bar is the wrong run's, not the median of both
    data = _data()
    data["rows"].append(_row("m1", "A", t, False, k=2))
    cell = _cell(facts._benchmark(data, {}, None), t["id"], "A")
    assert cell["ok"] is False and cell["value"] > 1
    # k = 3, one correct run and two wrong runs without a value: not solved, no value (the dash), not the correct run's
    data = _data()
    for k in (2, 3):
        bad = _row("m1", "A", t, False, k=k)
        for p in ("dq", "b", "c"):
            bad[f"rel_err_{p}"] = ""
        data["rows"].append(bad)
    cell = _cell(facts._benchmark(data, {}, None), t["id"], "A")
    assert (cell["ok"], cell["value"], cell["n_runs"], cell["n_correct"]) == (False, None, 3, 1)
    # a solved cell takes the value of its correct runs only
    data = _data()
    data["rows"] += [_row("m1", "A", t, True, k=2), _row("m1", "A", t, False, k=3)]
    cell = _cell(facts._benchmark(data, {}, None), t["id"], "A")
    assert cell["ok"] is True and cell["value"] == pytest.approx(0.001 / t["tolerance"]["Dq"])


def test_a_published_spectra_answer_is_that_of_one_run_not_the_median_of_the_runs():
    t = next(x for x in TASKS.values() if x["class"] == "literature_new")
    data = _data()
    data["rows"] = [r for r in data["rows"] if not (r["task_id"] == t["id"] and r["_cond"] == "A")]
    ref = t["reference"]["Dq"]
    good, bad = _row("m1", "A", t, True, k=1), _row("m1", "A", t, False, k=2)
    bad["dq"] = str(ref * 0.75)
    data["rows"] += [good, bad]
    s = next(x for x in facts._benchmark(data, {}, None)["literature"] if x["task"] == t["id"])
    got = s["reported"]["A"]
    # k = 2, not solved: the wrong run 2 is shown whole, not the mean of both runs (a value no run gave)
    assert got["Dq"] == pytest.approx(ref * 0.75) and got["ok"] is False and got["shown_k"] == 2


def test_the_value_of_a_cell_is_that_of_its_first_run_on_the_side_of_the_verdict():
    t = TASKS["P-experimental-01"]
    data = _data()
    data["rows"] = [r for r in data["rows"] if not (r["task_id"] == t["id"] and r["_cond"] == "A")]
    runs = [_row("m1", "A", t, False, k=k) for k in (1, 2)]
    for r, e in zip(runs, ("0.5", "1.5"), strict=True):
        r["rel_err_dq"] = r["rel_err_b"] = e
    data["rows"] += runs
    cell = _cell(facts._benchmark(data, {}, None), t["id"], "A")
    # two wrong runs: the median would be 1.0 / tolerance, a bar no run has; the cell is run 1's bar
    assert cell["ok"] is False and cell["value"] == pytest.approx(science._err_over_tol(runs[0]))
    assert cell["value"] != pytest.approx(science._err_over_tol({**runs[0], "rel_err_dq": "1.0", "rel_err_b": "1.0"}))


def test_the_header_reads_the_effort_of_the_manifest_when_the_rows_name_none():
    data = _data()
    for r in data["rows"]:
        r["effort"] = ""
    data["sets"] = [{"name": "set", "manifest": {"effort": "high"}}]
    assert facts._benchmark(data, {}, None)["header"]["effort"] == "high"
    assert facts._benchmark(_data(), {}, None)["header"]["effort"] == "medium"


def test_checks_names_its_input_files_with_their_hashes(tree):
    import hashlib
    base, src, t = tree
    out = facts.checks(base / "coverage" / "coverage.json", [base / "mutation"], src, t)["inputs"]
    sha = hashlib.sha256((base / "coverage" / "coverage.json").read_bytes()).hexdigest()
    assert out["coverage.json"] == [{"path": "coverage/coverage.json", "sha256": sha}]
    assert [e["path"] for e in out["pytest.log"]] == ["coverage/pytest.log"]
    shards = sorted(p for p in (base / "mutation").glob("*/*.json") if p.stem == p.parent.name)
    assert [e["path"] for e in out["mutation"]] == [f"mutation/{p.parent.name}/{p.name}" for p in shards] and shards
    assert all(len(e["sha256"]) == 64 for e in out["mutation"])


def test_checks_names_the_modules_beyond_the_top_fifteen_as_one_remainder(tmp_path):
    """The module table lists 15 modules; the rest is one remainder (count, mutants, score) so the columns add up."""
    cov = tmp_path / "ci" / "coverage"
    cov.mkdir(parents=True)
    mods = [f"m{i:02d}" for i in range(18)]
    (cov / "coverage.json").write_text(json.dumps({
        "meta": {"timestamp": "2026-10-31T16:47:20.8"},
        "files": {f"/w/src/tsbench/{m}.py": _cov_file(10, 9) for m in mods}}), encoding="utf-8")
    per = {f"tsbench.{m}": {"killed": 10, "survived": 1 + i} for i, m in enumerate(mods)}
    shard = tmp_path / "ci" / "mutation" / "all"
    shard.mkdir(parents=True)
    (shard / "all.json").write_text(json.dumps({
        "name": "all", "total": sum(11 + i for i in range(18)), "counts": {"killed": 180, "survived": 171},
        "per_module": per, "survivors": []}), encoding="utf-8")
    src = tmp_path / "w" / "src" / "tsbench"
    src.mkdir(parents=True)
    out = facts.checks(cov / "coverage.json", [tmp_path / "ci" / "mutation"], src, None)
    assert len(out["points"]) == 18 and len(out["points_top"]) == 15
    rest = out["points_other"]
    assert rest["modules"] == 3
    assert rest["mutants"] == sum(p["mutants"] for p in out["points"]) - sum(p["mutants"] for p in out["points_top"])
    assert rest["survived"] == sum(p["survived"] for p in out["points"]) - sum(p["survived"] for p in out["points_top"])
    assert rest["score_text"] != "–"
    assert facts.checks(cov / "coverage.json", [tmp_path / "ci" / "mutation"], src, None)["points_other"] == rest


def test_checks_has_no_remainder_when_every_module_is_listed(tree):
    base, src, t = tree
    out = facts.checks(base / "coverage" / "coverage.json", [base / "mutation", base / "extra"], src, t)
    assert out["points_other"] is None


def _use_event(i, name):
    return {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": i, "name": name, "input": {}}]}}


def test_tool_names_dedupe_only_on_non_empty_string_ids():
    ids = [["x"], {"a": 1}, "", "", None, None, "a", "a"]
    names, _ = facts._tool_names([_use_event(i, f"t{n}") for n, i in enumerate(ids)])
    assert names == [f"t{n}" for n in range(7)]


def test_tool_output_keeps_calls_without_a_usable_id_apart():
    ids = [["x"], "", "", None, None, "a"]
    events = [_use_event(i, f"t{n}") for n, i in enumerate(ids)]
    events.append({"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": "a", "content": "four"},
        {"type": "tool_result", "tool_use_id": ["x"], "content": "bad"}]}})
    out = facts._tool_output_of(events)
    assert [c["tool"] for c in out] == [f"t{n}" for n in range(6)]
    assert [c["chars"] for c in out] == [0, 0, 0, 0, 0, 4]


def test_shown_numbers_of_the_facts_round_a_half_up():
    assert [facts._number(v) for v in (2.5, 3.5, 12500.5, None)] == ["3", "4", "12501", "–"]
    assert facts._number(0.125, 100, 1) == "12.5" and facts._number(0.0225, 100, 1) == "2.3"
    assert [facts._text(v) for v in (12.25, 2.25, None)] == ["12.3", "2.3", "–"]


def test_the_endpoint_names_the_recorded_gateway_url():
    local = {"args": {"gateway": True, "gateway_url": "http://localhost:4000"}}
    default = {"args": {"gateway": True, "gateway_url": "https://chat-ai.academiccloud.de"}}
    unrecorded = {"args": {"gateway": True}}  # no gateway_url recorded: the default gateway
    api = {"args": {"gateway": False}}
    assert facts._endpoint([local]) == "gateway localhost:4000"
    assert facts._endpoint([default]) == facts._endpoint([unrecorded]) == "gateway"
    assert facts._endpoint([local, api]) == "gateway localhost:4000 and Anthropic API"
    assert facts._endpoint([unrecorded, local, api]) == "gateway and gateway localhost:4000 and Anthropic API"
    assert facts._endpoint([]) == "not recorded"


def test_a_context_overflow_has_its_own_outcome_category():
    assert facts._fold("context_overflow") == "overflow"
    assert dict([*facts.CATEGORIES, *facts.EXTRA])["overflow"] == "context overflow"
