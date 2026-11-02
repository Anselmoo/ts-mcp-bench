"""Tests for the `curve` answer schema, its scorer, and the scorer's guard against foreign task sets.

Curve tasks come from the pilot split (which may be printed); the synthetic task below is used for the boundary cases.
No network, no API.
"""
from __future__ import annotations

import csv
import json
import math
import pathlib

import pytest

from tsbench.score import extract, numeric, sensitivity, taxonomy
from tsbench.score import score as score_cli
from tsbench.tasks import load

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
FIX = REPO_ROOT / "src" / "tsbench" / "run" / "fake_cli_fixtures"
NAN = float("nan")


def pts(rows):
    """[(x, [e1, e2, e3]), ...] -> list of reference/answer points."""
    return [{"dq_over_b": x, "term": f"t{i}", "e_over_b": e} for x, es in rows for i, e in enumerate(es)]


REF = pts([(1.0, [10.0, 20.0, 50.0]), (2.5, [5.0, 25.0, 30.0]), (3.5, [8.0, 16.0, 40.0])])
TASK = {"id": "S-curve", "class": "curve", "answer_schema": "curve", "required": [], "expect_out_of_scope": False,
        "reference": {"Dq": None, "B": None, "C": None}, "reference_curve": REF,
        "tolerance": {"Dq": None, "B": None, "C": None, "curve_abs": 0.3, "curve_rel": 0.03}}


def answer(points):
    return {"points": points, "reason": "r"}


def shifted(delta_by_index):
    out = [dict(p) for p in REF]
    for i, d in delta_by_index.items():
        out[i]["e_over_b"] = REF[i]["e_over_b"] + d
    return out


# ---------------------------------------------------------------------------------- the rule
def test_exact_answer_is_correct_and_has_zero_error():
    row = numeric.score_curve(TASK, answer(REF))
    assert row["correct"] is True and row["unparseable"] is False and row["curve_max_rel_err"] == 0.0
    assert all(math.isnan(row[f"rel_err_{p}"]) and math.isnan(row[f"abs_err_{p}"]) for p in "dq b c".split())
    assert row["dq"] is None and row["answer_out_of_scope"] is None


def test_near_boundary_values_follow_the_or_rule():
    # absolute 0.3 passes where the relative error is large (ref 5.0: 0.3 is 6 %),
    # with the float slack of the fit scorer
    assert numeric.score_curve(TASK, answer(shifted({3: 0.3})))["correct"]
    assert numeric.score_curve(TASK, answer(shifted({3: -0.3})))["correct"]
    # just beyond 0.3 with 6.2 % relative: wrong
    assert not numeric.score_curve(TASK, answer(shifted({3: 0.31})))["correct"]
    # relative 3 % passes where the absolute error is large (ref 50: 1.5)
    assert numeric.score_curve(TASK, answer(shifted({2: 1.5})))["correct"]
    # 3.2 % of 50 is 1.6: beyond both
    row = numeric.score_curve(TASK, answer(shifted({2: 1.6})))
    assert not row["correct"] and row["curve_max_rel_err"] == pytest.approx(0.032)
    # one bad value in nine is enough
    assert not numeric.score_curve(TASK, answer(shifted({0: 0.0, 4: 0.0, 8: 2.0})))["correct"]
    # all nine at the edge
    assert numeric.score_curve(TASK, answer(shifted({i: 0.3 for i in range(9) if REF[i]["e_over_b"] <= 10})))["correct"]


def test_wrong_answer_reports_the_largest_relative_error():
    row = numeric.score_curve(TASK, answer(shifted({1: 10.0})))  # 20 -> 30
    assert row["correct"] is False and row["unparseable"] is False and row["curve_max_rel_err"] == pytest.approx(0.5)


def test_order_inside_a_dq_over_b_group_is_free_labels_are_not_scored():
    shuffled = [REF[2], REF[0], REF[1], REF[5], REF[3], REF[4], REF[8], REF[7], REF[6]]
    for p in shuffled:
        p["term"] = "anything"
    assert numeric.score_curve(TASK, answer(shuffled))["correct"]


def test_points_are_matched_by_dq_over_b():
    moved = [dict(p, dq_over_b=p["dq_over_b"] + 0.009) for p in REF]  # within 0.01: the same Dq/B
    assert numeric.score_curve(TASK, answer(moved))["correct"]
    moved = [dict(p, dq_over_b=p["dq_over_b"] + 0.02) for p in REF]
    row = numeric.score_curve(TASK, answer(moved))
    assert not row["correct"] and math.isnan(row["curve_max_rel_err"]) and not row["unparseable"]
    swapped = [dict(p, dq_over_b={1.0: 2.5, 2.5: 1.0, 3.5: 3.5}[p["dq_over_b"]])
               for p in REF]  # values of the wrong Dq/B
    assert not numeric.score_curve(TASK, answer(swapped))["correct"]


@pytest.mark.parametrize("bad", [REF[:8], REF + [REF[0]], REF[:3] * 3, [], REF[:6] + REF[:3]])
def test_wrong_number_of_points_per_group_or_in_total_is_incorrect(bad):
    row = numeric.score_curve(TASK, answer(bad))
    assert row["correct"] is False and math.isnan(row["curve_max_rel_err"]) and row["unparseable"] is False


def test_no_answer_is_unparseable_and_a_task_without_reference_is_never_correct():
    row = numeric.score_curve(TASK, None)
    assert row["unparseable"] is True and row["correct"] is False and math.isnan(row["curve_max_rel_err"])
    assert not numeric.score_curve({**TASK, "reference_curve": None}, answer(REF))["correct"]


def test_fit_rows_carry_a_nan_curve_column():
    task = {"class": "closed_form", "required": ["Dq", "B"], "reference": {"Dq": 1000.0, "B": 800.0, "C": None},
            "tolerance": {"Dq": 0.02, "B": 0.05, "C": 0.10}, "expect_out_of_scope": False}
    row = numeric.score(task, {"Dq": 1000.0, "B": 800.0, "C": None, "out_of_scope": False})
    assert row["correct"] and math.isnan(row["curve_max_rel_err"])
    assert "curve_max_rel_err" in score_cli.SCORE_COLUMNS


# ---------------------------------------------------------------------------------- extraction
def test_curve_answer_extraction():
    ok = extract.curve_answer({"points": [{"dq_over_b": "1.5", "term": "3T1g", "e_over_b": 12}], "reason": "x"})
    assert ok == {"points": [{"dq_over_b": 1.5, "term": "3T1g", "e_over_b": 12.0}], "reason": "x"}
    assert extract.curve_answer({"points": []}) == {"points": [], "reason": None}
    for bad in (None, "x", [], {"points": "x"}, {"points": [1]}, {"points": [{"dq_over_b": 1, "e_over_b": None}]},
                {"points": [{"dq_over_b": 1, "e_over_b": "abc"}]}, {"points": [{"dq_over_b": True, "e_over_b": 1}]},
                {"Dq": 1, "B": 2, "out_of_scope": False}):
        assert extract.curve_answer(bad) is None
    # a missing term label is tolerated: labels are informational
    assert extract.curve_answer({"points": [{"dq_over_b": 1, "e_over_b": 2}]})["points"][0]["term"] == ""


# ---------------------------------------------------------------------------------- score_dir and the task-set version
def transcript(path, cond, text, structured=None, model="claude-haiku-5-5"):
    path.parent.mkdir(parents=True, exist_ok=True)
    init = json.loads((FIX / f"init_{cond}.json").read_text(encoding="utf-8"))
    init["model"] = model
    result = {"type": "result", "subtype": "success", "is_error": False, "result": text, "total_cost_usd": 0.01,
              "num_turns": 1, "usage": {"input_tokens": 1, "output_tokens": 1}}
    if structured is not None:
        result["structured_output"] = structured
    events = [init, {"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}, result]
    path.write_text("".join(json.dumps(e) + "\n" for e in events), encoding="utf-8")


def read_csv(p):
    with open(p, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def curve_runs(tmp_path):
    tasks = [t for t in load("pilot") if t["class"] == "curve"]
    t1, t2, t3 = tasks
    m = "claude-haiku-5-5"
    runs = tmp_path / "runs"
    good = {"points": t1["reference_curve"], "reason": "r"}
    bad = {"points": [dict(p, e_over_b=p["e_over_b"] * 1.2) for p in t2["reference_curve"]], "reason": "r"}
    transcript(runs / m / "C" / "medium" / f"{t1['id']}-k1.jsonl", "C", json.dumps(good), good)
    transcript(runs / m / "C" / "medium" / f"{t2['id']}-k1.jsonl", "C", json.dumps(bad), bad)
    # text only, no structured_output: curve answers are read from structured_output alone
    transcript(runs / m / "C" / "medium" / f"{t3['id']}-k1.jsonl", "C", json.dumps(good))
    # a fit-shaped answer to a curve task
    fit = {"Dq": 1000.0, "B": 800.0, "C": None, "out_of_scope": False, "reason": "r"}
    transcript(runs / m / "A" / "medium" / f"{t1['id']}-k1.jsonl", "A", json.dumps(fit), fit)
    # and an ordinary fit task next to them
    t4 = next(t for t in load("pilot") if t["class"] == "closed_form")
    ok = {"Dq": t4["reference"]["Dq"], "B": t4["reference"]["B"], "C": None, "out_of_scope": False, "reason": "r"}
    transcript(runs / m / "A" / "medium" / f"{t4['id']}-k1.jsonl", "A", json.dumps(ok), ok)
    return runs, (t1, t2, t3, t4)


def test_score_dir_routes_curve_tasks_by_answer_schema(tmp_path):
    runs, (t1, t2, t3, t4) = curve_runs(tmp_path)
    result = score_cli.score_dir(runs, "pilot")
    rows = {(r["condition"], r["task_id"]): r for r in read_csv(runs / "scores.csv")}
    good, bad, none_ = rows[("C", t1["id"])], rows[("C", t2["id"])], rows[("C", t3["id"])]
    assert (good["correct"], bad["correct"], none_["correct"]) == ("True", "False", "False")
    assert good["curve_max_rel_err"] == "0.0" and float(bad["curve_max_rel_err"]) == pytest.approx(0.2, abs=1e-3)
    assert none_["unparseable"] == "True" and none_["curve_max_rel_err"] == ""
    assert all(good[c] == "" for c in ("dq", "b", "c", "rel_err_dq", "rel_err_b", "rel_err_c", "abs_err_dq"))
    assert good["class"] == "curve" and good["n_reported"] == "0"
    wrong_schema = rows[("A", t1["id"])]
    assert wrong_schema["correct"] == "False" and wrong_schema["unparseable"] == "True"
    fit = rows[("A", t4["id"])]
    assert fit["correct"] == "True" and fit["curve_max_rel_err"] == "" and fit["rel_err_dq"] != ""
    assert len(result["rows"]) == 5 and list(read_csv(runs / "scores.csv")[0]) == score_cli.SCORE_COLUMNS
    rates = {(r["condition"], r["task_id"]): r for r in read_csv(runs / "rates.csv")}
    assert rates[("C", t1["id"])]["rate"] == "1.0" and rates[("C", t2["id"])]["rate"] == "0.0"


def test_downstream_metrics_handle_curve_rows(tmp_path):
    runs, (t1, t2, t3, t4) = curve_runs(tmp_path)
    result = score_cli.score_dir(runs, "pilot")
    tasks = {t["id"]: t for t in load("pilot")}
    cats = {r["task_id"]: taxonomy.failure_category(r, tasks[r["task_id"]])
            for r in result["rows"] if r["condition"] == "C"}
    assert cats == {t1["id"]: "correct", t2["id"]: "wrong_items", t3["id"]: "unparseable"}
    gross = dict(next(r for r in result["rows"] if r["task_id"] == t2["id"]), curve_max_rel_err=0.7)
    assert taxonomy.failure_category(gross, tasks[t2["id"]]) == "gross_error"
    scope = taxonomy.scope_confusion(result["rows"], tasks)
    assert {r["condition"]: r["n_in_scope"] for r in scope} == {"A": 1, "C": 0}  # curve rows are not scope questions
    curve = sensitivity.tolerance_curve(runs, "pilot", scales=(1, 10))
    at = {(r["condition"], r["scale"]): r for r in curve}
    assert (at[("C", 1)]["n_correct"], at[("C", 1)]["n"]) == (1, 3)
    assert at[("C", 10)]["n_correct"] == 2  # a 20 % error passes at ten times the tolerance (30 % relative)


def test_scorer_takes_only_v2_and_refuses_foreign_runs(tmp_path, capsys):
    v2 = load("pilot")
    t = next(x for x in v2 if x["class"] == "closed_form")
    runs = tmp_path / "runs"
    ans = {"Dq": t["reference"]["Dq"], "B": t["reference"]["B"], "C": None, "out_of_scope": False, "reason": "r"}
    transcript(runs / "claude-haiku-5-5" / "A" / "medium" / f"{t['id']}-k1.jsonl", "A", json.dumps(ans), ans)
    assert score_cli.score_dir(runs, "pilot")["rows"][0]["correct"] is True
    with pytest.raises(ValueError, match="version"):  # an unknown task set version is refused
        score_cli.score_dir(runs, "pilot", version="v1")
    with pytest.raises(SystemExit):  # and there is no flag that chooses a version
        score_cli.main(["--runs", str(runs), "--task-version", "v1"])
    capsys.readouterr()
    # a manifest that lists task ids in another order, or carries another task hash, is refused
    (runs / "MANIFEST.json").write_text(json.dumps({"tasks": [x["id"] for x in reversed(v2)]}), encoding="utf-8")
    with pytest.raises(ValueError, match="order"):
        score_cli.score_dir(runs, "pilot")
    assert score_cli.main(["--runs", str(runs)]) == 2 and "refusing" in capsys.readouterr().err
    (runs / "MANIFEST.json").write_text(json.dumps({"tasks_sha256": "0" * 64}), encoding="utf-8")
    with pytest.raises(ValueError, match="tasks_sha256"):
        score_cli.score_dir(runs, "pilot")
    # a v2 manifest passes
    h2 = (REPO_ROOT / "src/tsbench/data/tasks/tasks.sha256").read_text(encoding="utf-8").splitlines()[1].split("  ")[0]
    (runs / "MANIFEST.json").write_text(json.dumps({"tasks_sha256": h2, "tasks": [x["id"] for x in v2][:4]}),
        encoding="utf-8")
    assert score_cli.score_dir(runs, "pilot")["rows"]
    # plan.jsonl prompts that differ from the tasks
    (runs / "MANIFEST.json").unlink()
    plan = [{"kind": "header"}, {"kind": "run", "task_id": t["id"], "prompt": "another prompt"}]
    (runs / "plan.jsonl").write_text("".join(json.dumps(x) + "\n" for x in plan), encoding="utf-8")
    with pytest.raises(ValueError, match="prompts"):
        score_cli.score_dir(runs, "pilot")


# manifest hash of a 25-record pilot prefix whose numerical_hard prompts differ from the committed ones: a run with this
# hash was made with a foreign task set.
FOREIGN_PILOT_SHA256 = "7b6caaf01f5bb0f6e0ae6f1dc2b4322dbdb282b050eb130af6afe85dbe232e5f"


def test_runs_on_a_prefix_of_the_split_score_and_runs_with_other_prompts_are_refused(tmp_path):
    """A manifest that pins the hash of the first records of the split scores. A run made with other prompts than the
    committed ones is refused."""
    import hashlib
    pilot = load("pilot")
    t = next(x for x in pilot if x["class"] == "closed_form")
    runs = tmp_path / "prefix"
    ans = {"Dq": t["reference"]["Dq"], "B": t["reference"]["B"], "C": None, "out_of_scope": False, "reason": "r"}
    transcript(runs / "claude-haiku-5-5" / "A" / "medium" / f"{t['id']}-k1.jsonl", "A", json.dumps(ans), ans)
    h = hashlib.sha256()
    for x in pilot[:25]:
        h.update((json.dumps(x, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8"))
    manifest = {"tasks_sha256": h.hexdigest(), "tasks": [x["id"] for x in pilot][:25]}
    (runs / "MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
    assert score_cli.score_dir(runs, "pilot")["rows"][0]["correct"] is True
    (runs / "MANIFEST.json").write_text(json.dumps({"tasks_sha256": FOREIGN_PILOT_SHA256}), encoding="utf-8")
    with pytest.raises(ValueError, match="tasks_sha256"):
        score_cli.score_dir(runs, "pilot")
