"""The shared facts of the full report (src/tsbench/report/science.py): runs, shares, paired differences, error in
units of the tolerance, the tolerance text and the test count. The runs are made up on the real pilot task records."""
from __future__ import annotations

import pytest

from tsbench.report import science
from tsbench.report.base import share
from tsbench.score.taxonomy import failure_category
from tsbench.tasks import load

TASKS = {t["id"]: t for t in load("pilot")}
NUMERIC = {"numerical", "numerical_hard", "crossover", "curve", "diagram"}


def _row(model: str, cond: str, task: dict, correct: bool, *, k: int = 1, bash: int = 0, mcp: int = 0,
         ratio: float | None = None, tokens: int = 1000, seconds: float = 10.0) -> dict:
    """A scored run as dashboard.collect leaves it. A wrong fit answer is off by a factor `ratio` (default 2) in every
    required parameter; a correct one is off by 0.1 % of the reference."""
    ref = task.get("reference") or {}
    r = {"model": model, "condition": cond, "_cond": cond, "task_id": task["id"], "k_index": str(k),
         "correct": str(correct), "evaluable": "True", "_na": "", "_task": task, "has_result": "True",
         "is_error": "False", "rescued": "False", "unparseable": "False", "result_subtype": "success",
         "n_bash_calls": str(bash), "n_mcp_calls": str(mcp), "output_tokens": str(tokens), "num_turns": "2",
         "duration_s": str(seconds), "answer_out_of_scope": "False"}
    for p in ("Dq", "B", "C"):
        v = ref.get(p) if isinstance(ref, dict) else None
        f = 1.001 if correct else (ratio or 2.0)
        r[p.lower()] = "" if v is None else str(v * f)
        r[f"rel_err_{p.lower()}"] = "" if v is None else str(abs(f - 1))
    if task["answer_schema"] == "curve":
        r["curve_max_rel_err"] = "0.001" if correct else "0.9"
    if task["answer_schema"] in ("batch", "pairing"):
        r["median_rel_error"] = "0.0" if correct else "0.9"
    if task["answer_schema"] == "diagram":
        r["item_accuracy"] = "1.0" if correct else "0.1"
    if task.get("expect_out_of_scope"):
        r["answer_out_of_scope"] = str(correct)
    r["_category"] = failure_category(r, task)
    return r


def _data(rule, models=("m1",), **kw) -> dict:
    """Every pilot task under A, B and C for each model; `rule(model, cond, task)` -> correct, or a dict of _row
    keywords with `correct`."""
    rows = []
    for m in models:
        for cond in ("A", "B", "C"):
            for t in TASKS.values():
                got = rule(m, cond, t)
                opts = got if isinstance(got, dict) else {"correct": got}
                if cond == "C":
                    opts.setdefault("mcp", 3)
                rows.append(_row(m, cond, t, **opts))
    return {"rows": rows, "tasks": TASKS, "sets": [], "notes": []}


def _runs(rule) -> science._Runs:
    return science._Runs(_data(rule))


def test_share_counts_correct_runs_over_runs_with_a_task_bootstrap_interval():
    runs = _runs(lambda m, cond, t: cond == "C" or t["class"] == "closed_form")
    c = share(runs.cell("m1", "C"))
    a = share(runs.cell("m1", "A"))
    assert c is not None and a is not None
    assert (c["k"], c["n"], c["tasks"]) == (len(TASKS), len(TASKS), len(TASKS)) and c["p"] == 1.0
    closed = sum(t["class"] == "closed_form" for t in TASKS.values())
    assert (a["k"], a["n"]) == (closed, len(TASKS)) and a["lo"] <= a["p"] <= a["hi"]
    assert share([]) is None


def test_contrasts_count_the_tasks_solved_by_one_condition_only():
    runs = _runs(lambda m, cond, t: cond == "C" or t["class"] == "closed_form")
    got = science._contrasts(runs, "m1")
    ca = next(x for x in got.values() if x["label"] == "C − A")
    closed = sum(t["class"] == "closed_form" for t in TASKS.values())
    assert ca["only_x"] == len(TASKS) - closed and ca["only_y"] == 0 and ca["state"] == "higher"


def test_error_over_tolerance_is_the_worst_required_parameter():
    t = next(t for t in TASKS.values() if t["class"] == "racah_c")
    r = _row("m1", "A", t, False, ratio=1.5)
    worst = max(0.5 / t["tolerance"][p] for p in t["required"])
    assert science._err_over_tol(r) == pytest.approx(worst)
    assert science._is_fit(t) and not science._is_fit(next(x for x in TASKS.values() if x["class"] == "curve"))


def test_test_functions_are_counted_per_folder(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "test_x.py").write_text("def test_one():\n    pass\n\ndef test_two():\n    pass\n",
                                              encoding="utf-8")
    (tmp_path / "test_top.py").write_text("def test_t():\n    pass\n\ndef helper():\n    pass\n", encoding="utf-8")
    assert science._test_counts(tmp_path) == [("a", 2), ("(top level)", 1)]


def test_tolerance_is_stated_as_the_task_records_state_it():
    by: dict[str, list[dict]] = {}
    for t in TASKS.values():
        by.setdefault(t["class"], []).append(t)
    assert science.tolerance_text(by["closed_form"]) == "Dq 2 %, B 5 %"
    assert science.tolerance_text(by["racah_c"]) == "Dq 2 %, B 5 %, C 10 %"
    assert science.tolerance_text(by["curve"]) == "3 % relative or 0.3 E/B absolute"
