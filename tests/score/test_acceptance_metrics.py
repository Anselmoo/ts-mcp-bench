"""Tests for the descriptive, tool-use, taxonomy and sensitivity metrics (docs/methods.md, section 5).

Each test imports the module it checks inside the test body. Transcripts are synthetic, fixture-shaped and written
into tmp_path; tasks are pilot tasks (via load) or synthetic dicts. No API call, no `claude`.
"""
from __future__ import annotations

import csv
import importlib
import json
import pathlib
import statistics
import subprocess
import sys

import pytest

from tsbench.score.extract import read_transcript
from tsbench.score.score import score_dir
from tsbench.stats.hypotheses import clopper_pearson
from tsbench.tasks import load

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
FIX = REPO_ROOT / "src" / "tsbench" / "run" / "fake_cli_fixtures"
M = "claude-haiku-5-5"
P = "mcp__tanabesugano__"


def mod(name: str):
    return importlib.import_module(name)


# ---------------------------------------------------------------- builders

def jline(dq=1000.0, b=800.0, c=None, oos=False, reason="ok") -> str:
    return json.dumps({"Dq": dq, "B": b, "C": c, "out_of_scope": oos, "reason": reason})


def make_transcript(path, cond, final_text, tools=(), model=M, result=True, subtype="success", is_error=False):
    """init (fixture), per tool: assistant tool_use + user tool_result (optionally is_error), final text, result.
    tools: (name, input_dict, output_text, is_error) tuples."""
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    init = json.loads((FIX / f"init_{cond}.json").read_text(encoding="utf-8"))
    init["model"] = model
    events = [init]
    for i, (name, inp, out, err) in enumerate(tools):
        tid = f"toolu_{i}"
        events.append({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": tid, "name": name, "input": inp}]}})
        block = {"type": "tool_result", "tool_use_id": tid, "content": [{"type": "text", "text": out}]}
        if err is not None:
            block["is_error"] = err
        events.append({"type": "user", "message": {"content": [block]}})
    events.append({"type": "assistant", "message": {"content": [{"type": "text", "text": final_text}]}})
    if result:
        events.append({"type": "result", "subtype": subtype, "is_error": is_error, "result": final_text,
                       "total_cost_usd": 0.01, "num_turns": len(tools) + 1, "duration_ms": 1000,
                       "usage": {"input_tokens": 10, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0,
                                 "output_tokens": 5}})
    path.write_text("".join(json.dumps(e) + "\n" for e in events), encoding="utf-8")
    return path


def pilot_tasks() -> dict:
    return {t["id"]: t for t in load("pilot")}


def first(cls, subtype=None):
    return next(t for t in load("pilot") if t["class"] == cls and (subtype is None or t["subtype"] == subtype))


def tp(runs, cond, task_id, k, effort="medium", model=M):
    return runs / model / cond / effort / f"{task_id}-k{k}.jsonl"


def synthetic_runs(root: pathlib.Path) -> pathlib.Path:
    """Pilot-id runs covering: exact, 3 % Dq off, gross, out-of-scope right/wrong, false refusal, no result,
    unparseable, max_turns, tetrahedral, a failing MCP call."""
    cf = first("closed_form")
    rc = first("racah_c")
    ct = first("out_of_scope", "charge_transfer")
    td = first("tetrahedral")
    dq, b = cf["reference"]["Dq"], cf["reference"]["B"]
    runs = root / "runs"
    fit = (P + "ts_fit_spectrum", {"d_count": cf["d_count"], "observed_peaks_cm1": cf["bands_cm1"]},
           f"Dq={dq} B={b}", None)
    # A
    make_transcript(tp(runs, "A", cf["id"], 1), "A", "x\n" + jline(dq, b))
    make_transcript(tp(runs, "A", cf["id"], 2), "A", "x\n" + jline(dq * 1.03, b))           # wrong_dq at s=1
    make_transcript(tp(runs, "A", cf["id"], 3), "A", "x\n" + jline(dq * 1.9, b * 1.9))      # gross_error
    make_transcript(tp(runs, "A", ct["id"], 1), "A", jline(None, None, oos=True))           # true limit
    make_transcript(tp(runs, "A", ct["id"], 2), "A", jline(1500.0, 700.0, oos=False))       # missed limit
    make_transcript(tp(runs, "A", rc["id"], 1), "A", jline(None, None, oos=True))           # false refusal
    # B
    make_transcript(tp(runs, "B", cf["id"], 1), "B", jline(dq, b), tools=[("Bash", {"command": "py"}, "ok", None)])
    make_transcript(tp(runs, "B", cf["id"], 2), "B", "no json here", tools=[("Bash", {"command": "py"}, "ok", None)])
    make_transcript(tp(runs, "B", ct["id"], 1), "B", jline(None, None, oos=True), result=False)  # no_result
    make_transcript(tp(runs, "B", td["id"], 1), "B", "...", subtype="error_max_turns", is_error=True)
    # C
    make_transcript(tp(runs, "C", cf["id"], 1), "C", jline(dq, b),
                    tools=[(P + "ts_explain", {"topic": "x"}, "boom", True), fit])
    make_transcript(tp(runs, "C", cf["id"], 2), "C", jline(dq, b), tools=[fit])
    tdr = td["reference"]
    make_transcript(tp(runs, "C", td["id"], 1), "C", jline(tdr["Dq"], tdr["B"]),
                    tools=[(P + "ts_fit_spectrum", {"d_count": 10 - td["d_count"]}, "fit", False)])
    make_transcript(tp(runs, "C", ct["id"], 1), "C", jline(None, None, oos=True),
                    tools=[(P + "ts_explain", {"topic": "charge transfer"}, "text", None)])
    return runs


def csv_rows(path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def header(path) -> list[str]:
    with open(path, newline="", encoding="utf-8") as fh:
        return next(csv.reader(fh))


def by_cell(rows, cond, effort="medium", model=M):
    return [r for r in rows if r["model"] == model and r["condition"] == cond and r["effort"] == effort]


def approx(a, b, tol=1e-9):
    return a is not None and b is not None and abs(float(a) - float(b)) <= tol


# ---------------------------------------------------------------- 1. tolerance sensitivity

def test_sensitivity_scale_tolerance_copies_and_keeps_null():
    s = mod("tsbench.score.sensitivity")
    exp = first("experimental")
    before = json.dumps(exp, sort_keys=True)
    out = s.scale_tolerance(exp, 2)
    assert json.dumps(exp, sort_keys=True) == before  # input not mutated
    assert out is not exp and out["tolerance"] is not exp["tolerance"]
    assert approx(out["tolerance"]["Dq"], exp["tolerance"]["Dq"] * 2)
    assert approx(out["tolerance"]["B"], exp["tolerance"]["B"] * 2)
    assert out["tolerance"]["C"] is None
    assert tuple(s.DEFAULT_SCALES) == (0.25, 0.5, 1, 2, 4, 10)
    assert s.SENSITIVITY_COLUMNS == ["model", "condition", "effort", "scale", "n", "n_correct", "accuracy"]


def test_sensitivity_scale_one_reproduces_score_dir(tmp_path):
    s = mod("tsbench.score.sensitivity")
    runs = synthetic_runs(tmp_path)
    scored = score_dir(runs, "pilot")["rows"]
    curve = s.tolerance_curve(runs, "pilot")
    assert {r["scale"] for r in curve} == {0.25, 0.5, 1, 2, 4, 10}
    for cond in "ABC":
        cell = by_cell(scored, cond)
        at1 = [r for r in by_cell(curve, cond) if r["scale"] == 1]
        assert len(at1) == 1
        assert at1[0]["n"] == len(cell)
        assert at1[0]["n_correct"] == sum(bool(r["correct"]) for r in cell)
        assert approx(at1[0]["accuracy"], at1[0]["n_correct"] / at1[0]["n"])


def test_sensitivity_monotone_and_oos_unaffected(tmp_path):
    s = mod("tsbench.score.sensitivity")
    runs = synthetic_runs(tmp_path)
    curve = {(r["condition"], r["scale"]): r for r in s.tolerance_curve(runs, "pilot")}
    for cond in "ABC":
        ns = [curve[(cond, sc)]["n_correct"] for sc in (0.25, 0.5, 1, 2, 4, 10)]
        assert ns == sorted(ns), (cond, ns)
    # A: exact cf and CT true (all scales), cf 3 % Dq off (correct from s=2: 0.04), gross 90 % (never)
    a = {sc: curve[("A", sc)]["n_correct"] for sc in (0.25, 1, 2, 10)}
    assert a == {0.25: 2, 1: 2, 2: 3, 10: 3}
    assert all(curve[("A", sc)]["n"] == 6 for sc in (0.25, 0.5, 1, 2, 4, 10))


def test_sensitivity_custom_scales(tmp_path):
    s = mod("tsbench.score.sensitivity")
    runs = synthetic_runs(tmp_path)
    curve = s.tolerance_curve(runs, "pilot", scales=(1, 1.6))
    assert {r["scale"] for r in curve} == {1, 1.6}
    a16 = [r for r in by_cell(curve, "A") if r["scale"] == 1.6][0]
    assert a16["n_correct"] == 3  # 3 % Dq is within 1.6 * 2 %


# ---------------------------------------------------------------- 2/3. taxonomy

def T(**kw) -> dict:
    base = {"id": "S-1", "class": "closed_form", "subtype": "d3", "geometry": "Oh", "d_count": 3,
            "required": ["Dq", "B"], "reference": {"Dq": 1000.0, "B": 800.0, "C": None},
            "tolerance": {"Dq": 0.02, "B": 0.05, "C": 0.10}, "expect_out_of_scope": False}
    base.update(kw)
    return base


T_OOS = dict(id="S-oos", **{"class": "out_of_scope"}, subtype="charge_transfer", geometry=None, d_count=None,
             required=[], reference={"Dq": None, "B": None, "C": None}, expect_out_of_scope=True)
T_RC = dict(id="S-rc", **{"class": "racah_c"}, required=["Dq", "B", "C"],
            reference={"Dq": 1000.0, "B": 800.0, "C": 3200.0})


def R(**kw) -> dict:
    """A scores.csv row as csv.DictReader gives it: all strings, '' for null."""
    base = {"model": M, "condition": "A", "effort": "medium", "task_id": "S-1", "k_index": "1",
            "class": "closed_form", "subtype": "d3", "correct": "False", "unparseable": "False",
            "answer_out_of_scope": "False", "dq": "1000.0", "b": "800.0", "c": "",
            "rel_err_dq": "0.0", "rel_err_b": "0.0", "rel_err_c": "", "is_error": "False",
            "result_subtype": "success", "has_result": "True"}
    base.update({k: ("" if v is None else str(v)) for k, v in kw.items()})
    return base


CASES = [
    ("correct", R(correct=True), T()),
    ("no_result", R(has_result=False, is_error=None, result_subtype=None, answer_out_of_scope=None,
                    rel_err_dq=None, rel_err_b=None), T()),
    ("max_turns", R(is_error=True, result_subtype="error_max_turns", unparseable=True), T()),
    ("budget", R(is_error=True, result_subtype="error_max_budget_usd", unparseable=True), T()),
    ("api_error", R(is_error=True, result_subtype="success", unparseable=True), T()),  # fixture: not logged in
    ("unparseable", R(unparseable=True, answer_out_of_scope=None, rel_err_dq=None, rel_err_b=None), T()),
    ("false_refusal", R(answer_out_of_scope=True, dq=None, b=None, rel_err_dq=None, rel_err_b=None), T()),
    ("missed_limit", R(task_id="S-oos", **{"class": "out_of_scope"}, subtype="charge_transfer",
                       rel_err_dq=None, rel_err_b=None), T(**T_OOS)),
    ("missed_limit", R(task_id="S-oos", answer_out_of_scope=True, rel_err_dq=None, rel_err_b=None), T(**T_OOS)),
    ("gross_error", R(rel_err_dq=0.8), T()),
    ("gross_error", R(rel_err_dq=0.03, rel_err_b="inf"), T()),
    ("wrong_dq", R(rel_err_dq=0.03), T()),
    ("wrong_dq", R(dq=None, rel_err_dq=None), T()),  # a missing required value is off
    ("wrong_b", R(rel_err_b=0.07), T()),
    ("wrong_c", R(c=3700, rel_err_c=0.15), T(**T_RC)),
    ("wrong_dq", R(rel_err_dq=0.03, c=9000, rel_err_c=0.9), T()),  # C not required: ignored, not gross
    ("wrong_multiple", R(rel_err_dq=0.03, rel_err_b=0.07), T()),
    ("unparseable", R(answer_out_of_scope=None), T()),  # parsed, non-boolean flag, nothing off: format failure
]


def test_taxonomy_categories_and_constants():
    t = mod("tsbench.score.taxonomy")
    assert len(t.CATEGORIES) == 15 and "wrong_items" in t.CATEGORIES
    assert tuple(c for c in t.CATEGORIES if c != "wrong_items") == ("correct", "no_result", "max_turns", "budget",
                                                                    "context_overflow", "api_error", "unparseable",
                                                                    "false_refusal", "missed_limit", "gross_error",
                                                                    "wrong_dq", "wrong_b", "wrong_c", "wrong_multiple")
    assert t.GROSS_REL_ERR == 0.5
    assert t.FAILURE_COLUMNS == ["model", "condition", "effort", "category", "n", "share"]


@pytest.mark.parametrize("expected,row,task", CASES, ids=[f"{i}-{c[0]}" for i, c in enumerate(CASES)])
def test_taxonomy_failure_category_csv_rows(expected, row, task):
    t = mod("tsbench.score.taxonomy")
    assert t.failure_category(row, task) == expected


def test_taxonomy_tolerance_boundary_is_not_off():
    t = mod("tsbench.score.taxonomy")
    # incorrect only because of B; Dq exactly on its tolerance does not count as off
    assert t.failure_category(R(rel_err_dq=0.02, rel_err_b=0.06), T()) == "wrong_b"


def test_taxonomy_typed_rows_from_score_dir(tmp_path):
    t = mod("tsbench.score.taxonomy")
    runs = synthetic_runs(tmp_path)
    tasks = pilot_tasks()
    typed = score_dir(runs, "pilot")["rows"]
    from_csv = csv_rows(runs / "scores.csv")
    key = lambda r: (r["condition"], r["task_id"], int(r["k_index"]))  # noqa: E731
    cat_typed = {key(r): t.failure_category(r, tasks[r["task_id"]]) for r in typed}
    cat_csv = {key(r): t.failure_category(r, tasks[r["task_id"]]) for r in from_csv}
    assert cat_typed == cat_csv
    cf, ct, rc, td = (first("closed_form")["id"], first("out_of_scope", "charge_transfer")["id"],
                      first("racah_c")["id"], first("tetrahedral")["id"])
    assert cat_csv[("A", cf, 1)] == "correct"
    assert cat_csv[("A", cf, 2)] == "wrong_dq"
    assert cat_csv[("A", cf, 3)] == "gross_error"
    assert cat_csv[("A", ct, 1)] == "correct"
    assert cat_csv[("A", ct, 2)] == "missed_limit"
    assert cat_csv[("A", rc, 1)] == "false_refusal"
    assert cat_csv[("B", cf, 2)] == "unparseable"
    assert cat_csv[("B", ct, 1)] == "no_result"
    assert cat_csv[("B", td, 1)] == "max_turns"
    assert cat_csv[("C", td, 1)] == "correct"


def test_taxonomy_failure_table_is_rectangular(tmp_path):
    t = mod("tsbench.score.taxonomy")
    runs = synthetic_runs(tmp_path)
    score_dir(runs, "pilot")
    rows = csv_rows(runs / "scores.csv")
    table = t.failure_table(rows, pilot_tasks())
    assert len(table) == 3 * len(t.CATEGORIES)
    for cond in "ABC":
        cell = by_cell(table, cond)
        assert [r["category"] for r in cell] == list(t.CATEGORIES)
        n_rows = len(by_cell(rows, cond))
        assert sum(int(r["n"]) for r in cell) == n_rows
        assert approx(sum(float(r["share"]) for r in cell), 1.0)
    a = {r["category"]: int(r["n"]) for r in by_cell(table, "A")}
    assert a["correct"] == 2 and a["wrong_dq"] == 1 and a["gross_error"] == 1
    assert a["missed_limit"] == 1 and a["false_refusal"] == 1


def test_taxonomy_scope_confusion_counts_and_ci(tmp_path):
    t = mod("tsbench.score.taxonomy")
    runs = synthetic_runs(tmp_path)
    tasks = pilot_tasks()
    typed = score_dir(runs, "pilot")["rows"]
    for rows in (typed, csv_rows(runs / "scores.csv")):
        out = {r["condition"]: r for r in t.scope_confusion(rows, tasks)}
        assert set(out) == {"A", "B", "C"}
        assert list(out["A"]) == t.SCOPE_COLUMNS
        a = out["A"]
        # A: cf x3 (oos False), CT true + CT missed, racah refused
        assert (a["n_expected_oos"], a["n_in_scope"]) == (2, 4)
        assert (a["true_limit"], a["missed_limit"], a["false_refusal"], a["no_scope_answer"]) == (1, 1, 1, 0)
        assert a["correct_scope"] == 1 + 3
        assert approx(a["limit_naming_rate"], 0.5)
        assert approx(a["false_refusal_rate"], 0.25)
        lo, hi = clopper_pearson(1, 4)
        assert approx(a["false_refusal_ci_lo"], lo) and approx(a["false_refusal_ci_hi"], hi)
        lo, hi = clopper_pearson(1, 2)
        assert approx(a["limit_naming_ci_lo"], lo) and approx(a["limit_naming_ci_hi"], hi)
        b = out["B"]
        # B: cf ok, cf unparseable, CT no result, Td max_turns (no answer)
        assert (b["n_expected_oos"], b["n_in_scope"]) == (1, 3)
        assert b["true_limit"] == 0 and b["no_scope_answer"] == 3 and b["correct_scope"] == 1
        assert approx(b["limit_naming_rate"], 0.0)
        for r in out.values():
            assert (r["n_expected_oos"] + r["n_in_scope"]
                    == r["correct_scope"] + r["missed_limit"] + r["false_refusal"] + r["no_scope_answer"])


def test_taxonomy_scope_confusion_empty_denominator_is_none():
    t = mod("tsbench.score.taxonomy")
    out = t.scope_confusion([R(correct=True)], {"S-1": T()})
    assert len(out) == 1
    r = out[0]
    assert r["n_expected_oos"] == 0 and r["limit_naming_rate"] is None
    assert r["limit_naming_ci_lo"] is None and r["limit_naming_ci_hi"] is None
    assert approx(r["false_refusal_rate"], 0.0)


# ---------------------------------------------------------------- 4. tool use

def test_tooluse_constants():
    u = mod("tsbench.score.tool_use")
    E = u.EXPECTED_TOOLS
    assert E["closed_form"] == E["numerical"] == E["experimental"] == {"ts_fit_spectrum"}
    assert E["racah_c"] == {"ts_terms_table_data", "ts_fit_spectrum"}
    # the level energies of curve, diagram and band-series tasks come from the terms table or the compute app
    assert E["curve"] == E["diagram"] == E["batch/band_series"] == {"ts_compute_app", "ts_terms_table_data"}
    assert E["tetrahedral"] == {"ts_fit_spectrum"} and "out_of_scope/tetrahedral" not in E
    assert E["out_of_scope/charge_transfer"] == set() and E["out_of_scope/jahn_teller"] == set()
    assert u.FIT_TOOLS == {"ts_fit_spectrum", "ts_ratio_fit_app", "ts_reverse_fit_app", "ts_fit_plot_app",
                           "ts_fit_script"}
    assert u.MCP_PREFIX == P
    assert u.strip_prefix(P + "ts_fit_spectrum") == "ts_fit_spectrum" and u.strip_prefix("Bash") == "Bash"
    assert u.expected_tools(T()) == {"ts_fit_spectrum"}
    assert u.expected_tools(T(**T_OOS)) == frozenset()
    assert u.expected_tools(T(**{"class": "tetrahedral"}, subtype=None)) == {"ts_fit_spectrum"}
    assert u.TOOL_USE_COLUMNS[:7] == ["model", "condition", "effort", "task_id", "k_index", "class", "subtype"]


def _tu(tmp_path, task, cond, tools, name="t.jsonl"):
    u = mod("tsbench.score.tool_use")
    tr = read_transcript(make_transcript(tmp_path / name, cond, jline(), tools=tools))
    return u.tool_use(task, tr, cond)


def test_tooluse_c_closed_form_with_failing_call(tmp_path):
    r = _tu(tmp_path, T(), "C", [(P + "ts_explain", {"topic": "x"}, "boom", True),
                                 (P + "ts_fit_spectrum", {"d_count": 3}, "ok", False),
                                 (P + "ts_fit_spectrum", {"d_count": 3}, "ok", None)])
    assert r["n_calls"] == 3 and r["n_distinct"] == 2 and r["n_bash_calls"] == 0
    assert r["n_tool_errors"] == 1 and approx(r["tool_error_rate"], 1 / 3)
    assert r["expected_tool_used"] is True and r["first_expected_index"] == 1
    assert r["d_count_matches"] is True


def test_tooluse_d_count_rules(tmp_path):
    wrong = _tu(tmp_path, T(), "C", [(P + "ts_fit_spectrum", {"d_count": 8}, "ok", None)], "a.jsonl")
    assert wrong["d_count_matches"] is False
    as_str = _tu(tmp_path, T(), "C", [(P + "ts_fit_spectrum", {"d_count": "3"}, "ok", None)], "b.jsonl")
    assert as_str["d_count_matches"] is True
    no_arg = _tu(tmp_path, T(), "C", [(P + "ts_supported_configs", {}, "ok", None)], "c.jsonl")
    assert no_arg["d_count_matches"] is None and no_arg["expected_tool_used"] is False
    assert no_arg["first_expected_index"] is None
    td = T(**{"class": "tetrahedral"}, subtype=None, geometry="Td", d_count=7)
    for i, (d, ok) in enumerate(((7, True), (3, True), (5, False))):
        r = _tu(tmp_path, td, "C", [(P + "ts_fit_spectrum", {"d_count": d}, "ok", None)], f"td{i}.jsonl")
        assert r["d_count_matches"] is ok, d
    oos = _tu(tmp_path, T(**T_OOS), "C", [(P + "ts_fit_spectrum", {"d_count": 3}, "ok", None)], "d.jsonl")
    assert oos["d_count_matches"] is None  # task has no d_count


def test_tooluse_empty_expected_set_means_no_fit_tool(tmp_path):
    ok = _tu(tmp_path, T(**T_OOS), "C", [(P + "ts_explain", {"topic": "ct"}, "text", None)], "a.jsonl")
    assert ok["expected_tool_used"] is True and ok["first_expected_index"] is None
    none = _tu(tmp_path, T(**T_OOS), "C", [], "b.jsonl")
    assert none["expected_tool_used"] is True and none["n_calls"] == 0 and none["tool_error_rate"] is None
    bad = _tu(tmp_path, T(**T_OOS), "C", [(P + "ts_ratio_fit_app", {"d_count": 3}, "fit", None)], "c.jsonl")
    assert bad["expected_tool_used"] is False


def test_tooluse_racah_any_of(tmp_path):
    rc = T(**T_RC)
    r = _tu(tmp_path, rc, "C", [(P + "ts_explain", {}, "x", None),
                                (P + "ts_terms_table_data", {"d_count": 3}, "x", None)])
    assert r["expected_tool_used"] is True and r["first_expected_index"] == 1


def test_tooluse_a_and_b_have_no_expected_tool(tmp_path):
    a = _tu(tmp_path, T(), "A", [], "a.jsonl")
    assert a["n_calls"] == 0 and a["n_distinct"] == 0 and a["n_tool_errors"] == 0
    assert a["tool_error_rate"] is None and a["expected_tool_used"] is None
    assert a["first_expected_index"] is None and a["d_count_matches"] is None and a["n_bash_calls"] == 0
    b = _tu(tmp_path, T(), "B", [("Bash", {"command": "py a"}, "ok", None),
                                 ("Bash", {"command": "py b"}, "Traceback", True)], "b.jsonl")
    assert b["n_calls"] == 2 and b["n_bash_calls"] == 2 and b["n_distinct"] == 1
    assert b["n_tool_errors"] == 1 and approx(b["tool_error_rate"], 0.5)
    assert b["expected_tool_used"] is None and b["first_expected_index"] is None and b["d_count_matches"] is None


def test_tooluse_rows_over_runs(tmp_path):
    u = mod("tsbench.score.tool_use")
    runs = synthetic_runs(tmp_path)
    rows = u.tool_use_rows(runs, "pilot")
    assert len(rows) == 14
    assert all(list(r) == u.TOOL_USE_COLUMNS for r in rows)
    cf = first("closed_form")["id"]
    c1 = next(r for r in rows if r["condition"] == "C" and r["task_id"] == cf and int(r["k_index"]) == 1)
    assert c1["n_calls"] == 2 and c1["n_tool_errors"] == 1 and c1["first_expected_index"] == 1
    td = first("tetrahedral")["id"]
    ctd = next(r for r in rows if r["condition"] == "C" and r["task_id"] == td)
    assert ctd["d_count_matches"] is True and ctd["expected_tool_used"] is True


# ---------------------------------------------------------------- 5/6. descriptive

def D(task_id, cls, correct, dq="1000.0", subtype="d3", cond="A", k=1) -> dict:
    return R(task_id=task_id, **{"class": cls}, subtype=subtype, correct=correct, dq=dq, condition=cond, k_index=k)


def test_descriptive_source_group():
    d = mod("tsbench.stats.descriptive")
    assert d.source_group(D("x", "experimental", True)) == "literature"
    for cls in ("closed_form", "numerical", "racah_c"):
        assert d.source_group(D("x", cls, True)) == "synthetic"
    assert d.source_group(D("x", "tetrahedral", True)) == "synthetic"
    assert d.source_group(D("x", "out_of_scope", True, subtype="charge_transfer")) is None
    assert d.source_group(D("x", "out_of_scope", True, subtype="jahn_teller")) is None


def test_descriptive_per_class_accuracy():
    d = mod("tsbench.stats.descriptive")
    rows = ([D("a", "closed_form", True), D("a", "closed_form", False, k=2), D("b", "numerical", True),
             D("e", "experimental", False), D("e", "experimental", True, k=2), D("e", "experimental", True, k=3),
             D("t", "tetrahedral", True), D("o", "out_of_scope", False, subtype="charge_transfer"),
             D("a", "closed_form", True, cond="C")])
    out = d.per_class_accuracy(rows)
    assert all(list(r) == d.PER_CLASS_COLUMNS for r in out)
    idx = {(r["condition"], r["grouping"], r["group"]): r for r in out}
    cf = idx[("A", "class", "closed_form")]
    assert (cf["n"], cf["n_correct"]) == (2, 1) and approx(cf["accuracy"], 0.5)
    lo, hi = clopper_pearson(1, 2)
    assert approx(cf["ci_lo"], lo) and approx(cf["ci_hi"], hi)
    oos = idx[("A", "class", "out_of_scope")]
    assert (oos["n"], oos["n_correct"]) == (1, 0)
    syn = idx[("A", "source", "synthetic")]   # cf x2, numerical, tetrahedral; CT excluded
    assert (syn["n"], syn["n_correct"]) == (4, 3)
    lit = idx[("A", "source", "literature")]
    assert (lit["n"], lit["n_correct"]) == (3, 2)
    assert ("C", "source", "literature") not in idx  # no empty groups
    assert idx[("C", "class", "closed_form")]["n"] == 1


def test_descriptive_per_class_typed_equals_csv(tmp_path):
    d = mod("tsbench.stats.descriptive")
    runs = synthetic_runs(tmp_path)
    typed = score_dir(runs, "pilot")["rows"]
    from_csv = csv_rows(runs / "scores.csv")
    norm = lambda out: sorted((r["condition"], r["grouping"], r["group"], int(r["n"]), int(r["n_correct"]))  # noqa: E731
                              for r in out)
    assert norm(d.per_class_accuracy(typed)) == norm(d.per_class_accuracy(from_csv))


def test_descriptive_consistency():
    d = mod("tsbench.stats.descriptive")
    rows = ([D("X", "closed_form", True, dq=100, k=i) for i in (1, 2, 3)]
            + [D("Y", "closed_form", True, dq=100, k=1), D("Y", "closed_form", False, dq=120, k=2)]
            + [D("W", "closed_form", False, dq=100, k=1), D("W", "closed_form", False, dq=None, k=2)]
            + [D("Z", "closed_form", True, dq=999, k=1)])  # k = 1: excluded everywhere
    out = d.consistency(rows)
    assert len(out) == 1 and list(out[0]) == d.CONSISTENCY_COLUMNS
    r = out[0]
    assert r["n_tasks"] == 3 and r["n_unanimous"] == 2
    assert approx(r["unanimity_rate"], 2 / 3)
    assert approx(r["mean_pairwise_agreement"], (1 + 0 + 1) / 3)
    assert r["n_tasks_cv"] == 2  # W has one non-null Dq
    cv_y = statistics.stdev([100, 120]) / statistics.fmean([100, 120])
    assert approx(r["median_cv_dq"], statistics.median([0.0, cv_y]))


def test_descriptive_consistency_abs_dq_and_empty():
    d = mod("tsbench.stats.descriptive")
    r = d.consistency([D("T", "out_of_scope", True, dq=-500, subtype="tetrahedral", k=1),
                       D("T", "out_of_scope", True, dq=500, subtype="tetrahedral", k=2)])[0]
    assert approx(r["median_cv_dq"], 0.0)  # sign convention is not spread
    e = d.consistency([D("Z", "closed_form", True, k=1)])[0]
    assert e["n_tasks"] == 0 and e["unanimity_rate"] is None and e["mean_pairwise_agreement"] is None
    assert e["median_cv_dq"] is None


def test_descriptive_consistency_on_runs(tmp_path):
    d = mod("tsbench.stats.descriptive")
    runs = synthetic_runs(tmp_path)
    score_dir(runs, "pilot")
    out = {r["condition"]: r for r in d.consistency(csv_rows(runs / "scores.csv"))}
    # A: cf k=3 [T,F,F] -> not unanimous; pairs (T,F),(T,F),(F,F) -> 1/3. CT k=2 [T,F] -> 0
    assert out["A"]["n_tasks"] == 2 and out["A"]["n_unanimous"] == 0
    assert approx(out["A"]["mean_pairwise_agreement"], (1 / 3 + 0) / 2)
    assert out["C"]["n_tasks"] == 1 and out["C"]["n_unanimous"] == 1
    assert approx(out["C"]["median_cv_dq"], 0.0)


# ---------------------------------------------------------------- report

FILES = ("tolerance_curve", "scope_confusion", "failure_taxonomy", "tool_use", "per_class", "consistency")


def _columns():
    return {"tolerance_curve": mod("tsbench.score.sensitivity").SENSITIVITY_COLUMNS,
            "scope_confusion": mod("tsbench.score.taxonomy").SCOPE_COLUMNS,
            "failure_taxonomy": mod("tsbench.score.taxonomy").FAILURE_COLUMNS,
            "tool_use": mod("tsbench.score.tool_use").TOOL_USE_COLUMNS,
            "per_class": mod("tsbench.stats.descriptive").PER_CLASS_COLUMNS,
            "consistency": mod("tsbench.stats.descriptive").CONSISTENCY_COLUMNS}


def test_report_end_to_end_cli(tmp_path):
    rep = mod("tsbench.stats.metrics")
    assert tuple(rep.METRIC_FILES) == FILES
    runs = synthetic_runs(tmp_path)
    assert not (runs / "scores.csv").exists()
    proc = subprocess.run([sys.executable, "-m", "tsbench.stats.metrics", "--runs", str(runs), "--split", "pilot"],
                          cwd=REPO_ROOT, capture_output=True, text=True, timeout=300, encoding="utf-8")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip()
    assert (runs / "scores.csv").exists()  # scored first because it was missing
    cols = _columns()
    for name in FILES:
        path = runs / "metrics" / f"{name}.csv"
        assert path.exists(), name
        assert header(path) == cols[name], name
        assert csv_rows(path), name
    assert len(csv_rows(runs / "metrics" / "tool_use.csv")) == 14
    assert len(csv_rows(runs / "metrics" / "tolerance_curve.csv")) == 3 * 6


def test_report_refuses_confirmatory_without_doi(tmp_path, capsys):
    rep = mod("tsbench.stats.metrics")
    runs = tmp_path / "runs"
    runs.mkdir()
    assert rep.main(["--runs", str(runs), "--split", "confirmatory"]) == 2
    assert not (runs / "metrics").exists() and not (runs / "scores.csv").exists()
    assert "preregister" in capsys.readouterr().err.lower()


def test_report_missing_runs_dir(tmp_path):
    rep = mod("tsbench.stats.metrics")
    assert rep.main(["--runs", str(tmp_path / "nope"), "--split", "pilot"]) == 2


def test_report_scores_again_and_write_metrics(tmp_path):
    rep = mod("tsbench.stats.metrics")
    runs = synthetic_runs(tmp_path)
    score_dir(runs, "pilot")
    stamp = (runs / "scores.csv").stat().st_mtime_ns
    paths = rep.write_metrics(runs, "pilot")
    assert set(paths) == set(FILES) and all(pathlib.Path(p).exists() for p in paths.values())
    assert (runs / "scores.csv").stat().st_mtime_ns >= stamp  # scored again: the tables never use a stale scores.csv
