"""Tests for the cost estimate: synthetic scores.csv files with known costs. No network, no model call."""
from __future__ import annotations

import csv
import json
from types import SimpleNamespace

import numpy as np
import pytest

from tsbench import plan as P
from tsbench.plan import estimate as E
from tsbench.tasks import load

HAIKU, OPUS = "claude-haiku-5-5", "claude-opus-5-5"
COLS = ["model", "condition", "effort", "task_id", "k_index", "class", "subtype", "cost_usd", "wall_time_s",
        "duration_s"]


def write_scores(path, rows):
    path.mkdir(parents=True, exist_ok=True)
    with open(path / "scores.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in COLS})
    return path


def row(model, cond, cls, cost, wall=10.0, subtype=""):
    return {"model": model, "condition": cond, "effort": "medium", "task_id": "x", "k_index": 1, "class": cls,
            "subtype": subtype, "cost_usd": cost, "wall_time_s": wall}


def make_plan(models=(HAIKU,), conditions=("A",), classes=None, k=1):
    tasks = load("pilot")
    if classes:
        tasks = [t for t in tasks if t["class"] in classes]
    spec = {"split": "pilot", "models": list(models), "conditions": list(conditions), "efforts": ["medium"], "k": k,
            "budget_usd": 10.0, "limit": None}
    return P.build_plan(tasks, spec, pins=P.live_pins(None), created_utc="2026-10-24T00:00:00+00:00")


def test_mean_factor_mapping_and_fallback(tmp_path):
    d = write_scores(tmp_path / "r", [row(HAIKU, "A", "numerical", 0.02), row(HAIKU, "A", "numerical", 0.04),
                                      row(HAIKU, "A", "closed_form", 0.10)])
    samples, source = E.read_samples([d])
    plan = make_plan(classes={"numerical", "numerical_hard", "crossover", "curve", "closed_form", "experimental"})
    res = E.estimate(plan.runs, samples)
    classes = ("numerical", "numerical_hard", "crossover", "curve", "closed_form", "experimental")
    n = {c: sum(1 for r in plan.runs if r["task_class"] == c) for c in classes}
    pooled = (0.02 + 0.04 + 0.10) / 3
    want = (n["numerical"] * 0.03                     # its own class
            + n["numerical_hard"] * 0.03 * 1.5        # mapped to numerical, x1.5
            + n["crossover"] * 0.03 * 1.5
            + n["closed_form"] * 0.10
            + n["curve"] * pooled * 1.5               # racah_c has no sample: pooled mean of the model x condition
            + n["experimental"] * pooled)
    assert res["models"][HAIKU]["expected_cost"] == pytest.approx(want)
    assert res["detail"][(HAIKU, "A", "numerical_hard")]["factor"] == 1.5
    assert res["detail"][(HAIKU, "A", "curve")]["n_samples"] == 0
    assert res["detail"][(HAIKU, "A", "numerical")]["n_samples"] == 2 and not res["warnings"]
    assert res["total"]["expected_cost"] == pytest.approx(want)
    hard = n["numerical_hard"] + n["crossover"] + n["curve"]
    assert res["models"][HAIKU]["expected_wall_s"] == pytest.approx(
        10.0 * (n["numerical"] + 1.5 * hard + n["closed_form"] + n["experimental"]))


def test_a_plan_class_with_its_own_samples_is_priced_from_them_without_a_factor(tmp_path):
    d = write_scores(tmp_path / "r", [row(HAIKU, "A", "batch", 0.20, wall=40.0), row(HAIKU, "A", "batch", 0.30,
                                                                                    wall=60.0),
                                      row(HAIKU, "A", "numerical", 0.01, wall=5.0)])
    samples, _source = E.read_samples([d])
    plan = make_plan(classes={"batch", "pairing"})
    res = E.estimate(plan.runs, samples, overhead=1.2)
    n_batch = sum(1 for r in plan.runs if r["task_class"] == "batch")
    n_pairing = sum(1 for r in plan.runs if r["task_class"] == "pairing")
    assert n_batch and n_pairing
    d_batch = res["detail"][(HAIKU, "A", "batch")]
    assert d_batch["measured_class"] == "batch" and d_batch["n_samples"] == 2 and d_batch["factor"] == 1.2
    assert d_batch["mean_cost"] == pytest.approx(0.25)
    # pairing has no samples of its own: mapped to racah_c (none either), so the pooled mean times its factor
    d_pairing = res["detail"][(HAIKU, "A", "pairing")]
    assert d_pairing["n_samples"] == 0 and d_pairing["factor"] == pytest.approx(1.5 * 1.2)
    pooled = (0.20 + 0.30 + 0.01) / 3
    assert res["models"][HAIKU]["expected_cost"] == pytest.approx(n_batch * 0.25 * 1.2 + n_pairing * pooled * 1.8)


def test_a_class_without_own_samples_still_uses_the_mapped_class_and_its_factor(tmp_path):
    d = write_scores(tmp_path / "r", [row(HAIKU, "A", "numerical", 0.02), row(HAIKU, "A", "numerical", 0.04)])
    samples, _source = E.read_samples([d])
    plan = make_plan(classes={"batch"})
    res = E.estimate(plan.runs, samples)
    d_batch = res["detail"][(HAIKU, "A", "batch")]
    assert d_batch["measured_class"] == "numerical" and d_batch["factor"] == 2.5 and d_batch["n_samples"] == 2
    assert d_batch["mean_cost"] == pytest.approx(0.03)


def test_last_directory_wins_per_model_and_condition(tmp_path):
    a = write_scores(tmp_path / "run1", [row(HAIKU, c, "numerical", 0.01) for c in "ABC"])
    b = write_scores(tmp_path / "run1b", [row(HAIKU, "B", "numerical", 0.50)])
    samples, source = E.read_samples([a, b])
    assert samples[(HAIKU, "B")]["numerical"] == [(0.50, 10.0)] and source[(HAIKU, "B")].endswith("run1b")
    assert samples[(HAIKU, "A")]["numerical"] == [(0.01, 10.0)] and source[(HAIKU, "A")].endswith("run1")
    table = {(r["model"], r["condition"]): r for r in E.pooled_table(samples, source)}
    assert table[(HAIKU, "B")]["mean_cost"] == 0.50 and table[(HAIKU, "B")]["from"] == "run1b"


def test_the_tetrahedral_subtype_is_its_own_class(tmp_path):
    d = write_scores(tmp_path / "r", [row(HAIKU, "A", "out_of_scope", 0.001),
                                      row(HAIKU, "A", "out_of_scope", 0.30, subtype="tetrahedral")])
    samples, _ = E.read_samples([d])
    assert set(samples[(HAIKU, "A")]) == {"out_of_scope", "tetrahedral"}
    assert samples[(HAIKU, "A")]["tetrahedral"] == [(0.30, 10.0)]


def test_unmeasured_model_is_reported_not_guessed(tmp_path):
    d = write_scores(tmp_path / "r", [row(HAIKU, "A", "numerical", 0.02)])
    samples, _ = E.read_samples([d])
    plan = make_plan(models=(HAIKU, OPUS), classes={"numerical"})
    res = E.estimate(plan.runs, samples)
    assert res["models"][OPUS]["expected_cost"] == 0.0 and res["models"][OPUS]["unmeasured_runs"] == len(plan.runs) // 2
    assert any(OPUS in w for w in res["warnings"])


def test_p90_total_is_seeded_and_the_sum_of_p90s_bounds_it(tmp_path):
    costs = [0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.10]
    d = write_scores(tmp_path / "r", [row(HAIKU, "A", "numerical", c) for c in costs])
    samples, _ = E.read_samples([d])
    plan = make_plan(classes={"numerical"}, k=20)
    a, b = E.estimate(plan.runs, samples), E.estimate(plan.runs, samples)
    assert a["total"] == b["total"]  # seeded
    m = a["models"][HAIKU]
    n = m["n_runs"]
    assert m["expected_cost"] == pytest.approx(n * float(np.mean(costs)))
    assert m["expected_cost"] <= m["p90_cost"] and m["expected_cost"] <= m["sum_p90_cost"]
    tail = np.percentile(costs, 90) / np.mean(costs)
    assert m["sum_p90_cost"] == pytest.approx(n * float(np.mean(costs)) * tail)
    doubled = E.estimate(plan.runs, samples, overhead=2.0)
    assert doubled["models"][HAIKU]["expected_cost"] == pytest.approx(2 * m["expected_cost"])


def test_cli_prints_estimate_and_warns_about_the_cap(tmp_path, capsys):
    d = write_scores(tmp_path / "r", [row(HAIKU, c, k, 0.05) for c in "ABC" for k in ("numerical", "closed_form")])
    plan = make_plan(conditions=("A", "B", "C"), classes={"numerical", "curve"})
    path = tmp_path / "plan.jsonl"
    P.write_plan(plan, path, markdown=False)
    assert E.main(["--plan", str(path), "--from-runs", str(d), "--json", str(tmp_path / "out.json")]) == 0
    out = capsys.readouterr().out
    assert "TOTAL" in out and "per_call_cap: none" in out and "WARNING small n per class and cell" in out
    assert json.loads((tmp_path / "out.json").read_text(encoding="utf-8"))["total"]["n_runs"] == len(plan.runs)
    res = E.estimate(plan.runs, E.read_samples([d])[0])
    budget, expected, sum_p90, ok = E.budget_check(plan, res)
    assert budget == 10.0 and expected == pytest.approx(res["total"]["expected_cost"]) and ok == (10.0 >= sum_p90)
    capsys.readouterr()
    assert E.main(["--plan", str(path), "--from-runs", str(d), "--detail"]) == 0
    assert "via numerical" in capsys.readouterr().out


def test_sealed_plan_and_missing_scores_are_refused(tmp_path, capsys):
    plan = make_plan()
    sealed = tmp_path / "plan.sealed.json"
    P.write_sealed(plan, sealed)
    d = write_scores(tmp_path / "r", [row(HAIKU, "A", "numerical", 0.02)])
    assert E.main(["--plan", str(sealed), "--from-runs", str(d)]) == 2
    clear = tmp_path / "plan.jsonl"
    P.write_plan(plan, clear, markdown=False)
    with pytest.raises(SystemExit):
        E.main(["--plan", str(clear), "--from-runs", str(tmp_path / "nowhere")])


# ------------------------------------------------------------------ the numbers, one rule at a time
def _replay_boot(costs, walls, n_runs, factor=1.0, seed=E.BOOTSTRAP_SEED, draws=E.BOOTSTRAP_DRAWS):
    """The seeded bootstrap of estimate(), written out again for n identical runs of one class (in run order)."""
    rng = np.random.default_rng(seed)
    boot_c, boot_w = np.zeros(draws), np.zeros(draws)
    costs, walls = np.asarray(costs, dtype=float), np.asarray(walls, dtype=float)
    for _ in range(n_runs):
        idx = rng.integers(len(costs), size=draws)
        boot_c += factor * costs[idx]
        boot_w += factor * walls[idx]
    return float(np.percentile(boot_c, 90)), float(np.percentile(boot_w, 90))


def test_hours_are_printed_in_hours_with_two_decimals():
    assert E._hours(360000) == "100.00 h" and E._hours(5400) == "1.50 h" and E._hours(0) == "0.00 h"


def test_numeric_helpers_skip_missing_and_nan_values():
    assert E._num("0.5") == 0.5 and E._num(2) == 2.0
    assert E._num("nan") is None and E._num("") is None and E._num(None) is None and E._num("x") is None
    assert E._mean([]) is None and E._mean([None, None]) is None and E._mean([1.0, None, 3.0]) == 2.0
    assert E._p90([]) is None and E._p90([None]) is None
    assert E._p90(list(range(1, 11))) == pytest.approx(9.1)


def test_budget_check_passes_when_the_budget_covers_the_sum_of_p90s():
    plan = SimpleNamespace(header={"budget_usd_total": 10.0})
    assert E.budget_check(plan, {"total": {"expected_cost": 4.0, "sum_p90_cost": 10.0}}) == (10.0, 4.0, 10.0, True)
    assert E.budget_check(plan, {"total": {"expected_cost": 4.0, "sum_p90_cost": 10.01}})[3] is False


def test_missing_wall_time_falls_back_to_duration_and_bad_costs_are_skipped(tmp_path):
    rows = [{**row(HAIKU, "A", "numerical", 0.02, wall=""), "duration_s": "7.5"},
            row(HAIKU, "A", "numerical", "", wall=3.0),
            row(HAIKU, "A", "numerical", 0.03, wall="")]
    d = write_scores(tmp_path / "r", rows)
    samples, _ = E.read_samples([d])
    assert samples[(HAIKU, "A")]["numerical"] == [(0.02, 7.5), (0.03, None)]


def test_missing_scores_file_names_the_path(tmp_path):
    with pytest.raises(SystemExit, match=r"estimate: .*nowhere[/\\]scores\.csv not found"):
        E.read_samples([tmp_path / "nowhere"])


def test_tail_ratio_scales_the_sum_of_p90s_above_one(tmp_path):
    costs = [0.01] * 8 + [0.5, 0.5]
    d = write_scores(tmp_path / "r", [row(HAIKU, "A", "numerical", c) for c in costs])
    samples, _ = E.read_samples([d])
    plan = make_plan(classes={"numerical"}, k=4)
    m = E.estimate(plan.runs, samples)["models"][HAIKU]
    tail = np.percentile(costs, 90) / np.mean(costs)
    assert tail > 4.0
    assert m["sum_p90_cost"] == pytest.approx(m["n_runs"] * float(np.mean(costs)) * tail)


def test_bootstrap_draws_are_the_seeded_replay_for_cost_and_wall(tmp_path):
    costs = [0.01, 0.02, 0.03, 0.05, 0.08, 0.13, 0.21, 0.34, 0.55, 0.9]
    walls = [3.0, 5.0, 8.0, 13.0, 21.0, 34.0, 55.0, 89.0, 144.0, None]
    rows = [row(HAIKU, "A", "numerical", c, wall=("" if w is None else w)) for c, w in zip(costs, walls, strict=True)]
    d = write_scores(tmp_path / "r", rows)
    samples, _ = E.read_samples([d])
    plan = make_plan(classes={"numerical"}, k=3)
    res = E.estimate(plan.runs, samples)
    m = res["models"][HAIKU]
    mean_w = np.mean([w for w in walls if w is not None])
    filled = [w if w is not None else mean_w for w in walls]
    p90_c, p90_w = _replay_boot(costs, filled, m["n_runs"])
    assert m["p90_cost"] == pytest.approx(p90_c, rel=0, abs=1e-12)
    assert m["p90_wall_s"] == pytest.approx(p90_w, rel=0, abs=1e-9)
    assert res["total"]["p90_cost"] == pytest.approx(p90_c, rel=0, abs=1e-12)
    assert res["total"]["p90_wall_s"] == pytest.approx(p90_w, rel=0, abs=1e-9)
    assert m["expected_wall_s"] == pytest.approx(m["n_runs"] * mean_w)


def test_same_runs_have_constant_bootstrap_and_add_up(tmp_path):
    d = write_scores(tmp_path / "r", [row(HAIKU, "A", "numerical", 0.02, wall=4.0)] * 2)
    samples, _ = E.read_samples([d])
    plan = make_plan(classes={"numerical"}, k=3)
    m = E.estimate(plan.runs, samples)["models"][HAIKU]
    assert m["p90_cost"] == pytest.approx(0.02 * m["n_runs"])
    assert m["p90_wall_s"] == pytest.approx(4.0 * m["n_runs"])
    assert m["expected_wall_s"] == pytest.approx(4.0 * m["n_runs"])


def test_detail_counts_every_plan_run_of_a_class(tmp_path):
    d = write_scores(tmp_path / "r", [row(HAIKU, "A", "numerical", 0.02), row(HAIKU, "A", "numerical", 0.04)])
    samples, _ = E.read_samples([d])
    plan = make_plan(classes={"numerical", "curve"}, k=3)
    res = E.estimate(plan.runs, samples)
    n_num = sum(1 for r in plan.runs if r["task_class"] == "numerical")
    assert res["detail"][(HAIKU, "A", "numerical")]["n_plan_runs"] == n_num
    assert res["detail"][(HAIKU, "A", "numerical")]["mean_cost"] == pytest.approx(0.03)


def test_no_wall_times_mean_zero_wall_time(tmp_path):
    d = write_scores(tmp_path / "r", [row(HAIKU, "A", "numerical", 0.02, wall="")])
    samples, _ = E.read_samples([d])
    plan = make_plan(classes={"numerical"})
    res = E.estimate(plan.runs, samples)
    assert res["models"][HAIKU]["expected_wall_s"] == 0.0
    assert res["detail"][(HAIKU, "A", "numerical")]["mean_wall_s"] == 0.0


def test_unmeasured_warning_says_the_runs_are_left_out(tmp_path):
    d = write_scores(tmp_path / "r", [row(HAIKU, "A", "numerical", 0.02)])
    samples, _ = E.read_samples([d])
    plan = make_plan(models=(HAIKU, OPUS), classes={"numerical"})
    res = E.estimate(plan.runs, samples)
    n = res["models"][OPUS]["unmeasured_runs"]
    assert res["warnings"] == [f"{OPUS}: {n} runs have no measured model x condition; they are NOT in the totals"]


def test_cli_refuses_a_file_that_is_not_a_plan(tmp_path, capsys):
    bad = tmp_path / "plan.jsonl"
    bad.write_text("not a plan\n", encoding="utf-8")
    d = write_scores(tmp_path / "r", [row(HAIKU, "A", "numerical", 0.02)])
    assert E.main(["--plan", str(bad), "--from-runs", str(d)]) == 2
    err = capsys.readouterr().err
    assert err.startswith("estimate: ") and "is not a valid plan" in err


def test_cli_sealed_plan_message_is_exact(tmp_path, capsys):
    sealed = tmp_path / "plan.sealed.json"
    P.write_sealed(make_plan(), sealed)
    d = write_scores(tmp_path / "r", [row(HAIKU, "A", "numerical", 0.02)])
    assert E.main(["--plan", str(sealed), "--from-runs", str(d)]) == 2
    assert capsys.readouterr().err == "estimate: a sealed plan has no run records\n"


def test_cli_requires_plan_and_runs(tmp_path):
    clear = tmp_path / "plan.jsonl"
    P.write_plan(make_plan(), clear, markdown=False)
    with pytest.raises(SystemExit) as no_runs:
        E.main(["--plan", str(clear)])
    assert no_runs.value.code == 2
    with pytest.raises(SystemExit) as no_plan:
        E.main(["--from-runs", str(tmp_path)])
    assert no_plan.value.code == 2


def test_cli_overhead_is_a_number_that_defaults_to_one(tmp_path, capsys):
    d = write_scores(tmp_path / "r", [row(HAIKU, "A", "numerical", 0.02)])
    clear = tmp_path / "plan.jsonl"
    P.write_plan(make_plan(classes={"numerical"}), clear, markdown=False)
    out1, out2 = tmp_path / "one.json", tmp_path / "two.json"
    assert E.main(["--plan", str(clear), "--from-runs", str(d), "--json", str(out1)]) == 0
    text1 = capsys.readouterr().out
    assert "overhead" not in text1
    assert E.main(["--plan", str(clear), "--from-runs", str(d), "--overhead", "2", "--json", str(out2)]) == 0
    text2 = capsys.readouterr().out
    assert "overhead x2.0 applied" in text2
    one = json.loads(out1.read_text(encoding="utf-8"))
    two = json.loads(out2.read_text(encoding="utf-8"))
    assert two["models"][HAIKU]["expected_cost"] == pytest.approx(2 * one["models"][HAIKU]["expected_cost"])


def test_json_output_keeps_models_and_total_in_indented_form(tmp_path):
    d = write_scores(tmp_path / "r", [row(HAIKU, "A", "numerical", 0.02)])
    clear = tmp_path / "plan.jsonl"
    P.write_plan(make_plan(classes={"numerical"}), clear, markdown=False)
    out = tmp_path / "out.json"
    assert E.main(["--plan", str(clear), "--from-runs", str(d), "--json", str(out)]) == 0
    text = out.read_text(encoding="utf-8")
    assert text.startswith('{\n "models": {\n  "' + HAIKU + '"')
    assert set(json.loads(text)) == {"models", "total"}


def test_report_lines_show_the_detail_only_when_asked(tmp_path):
    d = write_scores(tmp_path / "r", [row(HAIKU, "A", "numerical", 0.02)])
    plan = make_plan(classes={"numerical"})
    res = E.estimate(plan.runs, E.read_samples([d])[0])
    table = E.pooled_table(*E.read_samples([d]))
    assert not any("class means used" in ln for ln in E.report_lines(plan, res, table, 1.0))
    assert any("class means used" in ln for ln in E.report_lines(plan, res, table, 1.0, detail=True))
    assert not any("overhead" in ln for ln in E.report_lines(plan, res, table, 1.0, detail=True))


def test_zero_costs_have_no_tail_and_no_division(tmp_path):
    d = write_scores(tmp_path / "r", [row(HAIKU, "A", "numerical", 0.0) for _ in range(3)])
    samples, _ = E.read_samples([d])
    plan = make_plan(classes={"numerical"}, k=2)
    m = E.estimate(plan.runs, samples)["models"][HAIKU]
    assert m["sum_p90_cost"] == 0.0 and m["expected_cost"] == 0.0 and m["p90_cost"] == 0.0


def _golden_inputs(tmp_path):
    d = write_scores(tmp_path / "run1", [row(HAIKU, "A", "numerical", 0.02), row(HAIKU, "A", "numerical", 0.04),
                                         row(HAIKU, "A", "closed_form", 0.10),
                                         row(HAIKU, "B", "numerical", 0.03, wall="")])
    samples, source = E.read_samples([d])
    plan = make_plan(models=(HAIKU, OPUS), conditions=("A", "B"), classes={"numerical", "closed_form", "curve"})
    return plan, E.estimate(plan.runs, samples), E.pooled_table(samples, source)


def test_report_text_is_the_printed_estimate(tmp_path):
    plan, res, table = _golden_inputs(tmp_path)
    pid = plan.header["plan_id"][:16]
    got = E.report_lines(plan, res, table, 1.0, detail=True)
    assert got == [
        f"plan {pid}: split pilot, 32 runs, models 2, conditions A,B, efforts medium, k = 1",
        "",
        "measured (model x condition: n runs, mean and p90 USD per run, mean wall s, source directory)",
        "  claude-haiku-5-5    A  n=3   mean=0.0533 p90=0.0880 wall=10.0s  run1  "
        "classes {'closed_form': 1, 'numerical': 2}",
        "  claude-haiku-5-5    B  n=1   mean=0.0300 p90=0.0300 wall=0.0s  run1  classes {'numerical': 1}",
        "",
        "estimate for the plan (USD; wall time is serial)",
        "  model                runs  expected  p90 total  sum p90s  wall exp  wall p90",
        "  claude-haiku-5-5       16      0.82       0.94      1.16    0.03 h    0.03 h",
        "  claude-opus-5-5        16      0.00       0.00      0.00    0.00 h    0.00 h",
        "  TOTAL                  32      0.82       0.94      1.16    0.03 h    0.03 h",
        "  expected = sum of class means x factor; p90 total = 90th percentile of the total over 4000 seeded "
        "resamples; "
        "sum p90s = every run billed at its own p90 (mean x model-x-condition tail ratio)",
        "  factors: {'numerical_hard': 1.5, 'crossover': 1.5, 'curve': 1.5, 'literature_all': 1.2, "
        "'literature_new': 1.2, 'batch': 2.5, 'pairing': 1.5, 'diagram': 1.5} "
        "(only for classes with no measurement of their own); "
        "class mapping: numerical_hard->numerical, crossover->numerical, curve->racah_c, literature_all->experimental, "
        "literature_new->experimental, batch->numerical, pairing->racah_c, diagram->curve",
        "",
        "plan budget USD 10 is the run-set total only (per_call_cap: none; no run is started once it is spent, "
        "a running "
        "call is never cut): expected USD 0.82, sum p90s USD 1.16",
        "",
        "class means used (plan class: n plan runs, n samples behind the mean, factor), per model x condition",
        "  claude-haiku-5-5    A  closed_form    runs=2    n=1  x1.0  mean=0.1000 wall=10.0s via closed_form",
        "  claude-haiku-5-5    A  curve          runs=3    n=0  x1.5  mean=0.0533 wall=10.0s via racah_c",
        "  claude-haiku-5-5    A  numerical      runs=3    n=2  x1.0  mean=0.0300 wall=10.0s via numerical",
        "  claude-haiku-5-5    B  closed_form    runs=2    n=0  x1.0  mean=0.0300 wall=0.0s via closed_form",
        "  claude-haiku-5-5    B  curve          runs=3    n=0  x1.5  mean=0.0300 wall=0.0s via racah_c",
        "  claude-haiku-5-5    B  numerical      runs=3    n=1  x1.0  mean=0.0300 wall=0.0s via numerical",
        "",
        "WARNING claude-opus-5-5: 16 runs have no measured model x condition; they are NOT in the totals",
        "WARNING small n per class and cell: see the n column",
    ]


def test_report_text_warns_on_a_small_budget_and_on_overhead(tmp_path):
    plan, res, table = _golden_inputs(tmp_path)
    plan.header["budget_usd_total"] = 0.001
    got = E.report_lines(plan, res, table, 2.0)
    assert got[-2:] == [
        "WARNING claude-opus-5-5: 16 runs have no measured model x condition; they are NOT in the totals",
        "WARNING small n per class and cell: see the n column; overhead x2.0 applied",
    ]
    assert ("expected USD 0.82, sum p90s USD 1.16  WARNING budget < sum p90s: the last runs may not start; "
            "raise --budget-usd") in got[-4]
    assert not any("class means used" in ln for ln in got)


def test_report_header_lists_conditions_and_efforts_in_order(tmp_path):
    plan, res, table = _golden_inputs(tmp_path)
    plan.header["spec"]["efforts"] = ["low", "medium"]
    head = E.report_lines(plan, res, table, 1.0)[0]
    assert head.endswith("conditions A,B, efforts low,medium, k = 1")


def test_cli_prints_the_report_one_line_per_row(tmp_path, capsys):
    d = write_scores(tmp_path / "r", [row(HAIKU, "A", "numerical", 0.02)])
    clear = tmp_path / "plan.jsonl"
    P.write_plan(make_plan(classes={"numerical"}), clear, markdown=False)
    assert E.main(["--plan", str(clear), "--from-runs", str(d)]) == 0
    out = capsys.readouterr().out
    assert out.startswith("plan ") and "XX" not in out
    assert out.splitlines()[1] == ""


def test_cli_help_names_the_command_and_every_option(capsys, monkeypatch):
    monkeypatch.setenv("COLUMNS", "400")
    with pytest.raises(SystemExit) as e:
        E.main(["--help"])
    assert e.value.code == 0
    text = capsys.readouterr().out
    assert text.startswith("usage: tsbench plan estimate ")
    out = " ".join(text.split())
    assert ("Cost and wall-time estimate of a run plan from the runs already measured. No API call, no model call."
            in out)
    assert "Samples are the rows" not in out, "only the first paragraph of the docstring"
    for help_text in ("--from-runs FROM_RUNS [FROM_RUNS ...] runs directories with scores.csv; the last one wins "
                      "per model x condition",
                      "--detail also list the class mean behind every model x condition x class",
                      "--json JSON also write the numbers to this file"):
        assert help_text in out, help_text
