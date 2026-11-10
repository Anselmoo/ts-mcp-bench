"""Tests for src/tsbench/analyze/effort.py: thinking, output, turns and time per run, and the runs at the wall limit."""
from __future__ import annotations

import pytest
from analyze_runs import bash, read_csv, result, use, write_run, write_scores

from tsbench.analyze import effort
from tsbench.score.extract import read_transcript

ANSWER = {"Dq": 2044.0, "B": 702.0, "C": None, "out_of_scope": False, "reason": "fit"}


def _finished(root, name="m/B/medium/P-numerical-01-k1", thinking=900, ok_out="Dq = 2044.0"):
    events = [use("a", "Bash", {"command": "python3 a.py"}, at=10, thinking_ms=4000),
              *bash("a", "", "Exit code 1\nTraceback (most recent call last):\nKeyError: 1", err=True,
                    done=14)[1:],
              use("b", "Bash", {"command": "python3 b.py"}, at=20, thinking_ms=2500),
              *bash("b", "", ok_out, done=26)[1:],
              *result(ANSWER, thinking=thinking, output=1500, turns=4, duration_ms=60_000, api_ms=50_000)]
    return write_run(root, name, events, meta={"wall_time_s": 61.5})


def test_effort_of_a_finished_run(tmp_path):
    path = _finished(tmp_path)
    row = effort.effort_of(path, read_transcript(path))
    assert (row["thinking_tokens"], row["output_tokens"], row["num_turns"]) == (900, 1500, 4)
    assert (row["duration_s"], row["api_duration_s"], row["wall_time_s"]) == (60.0, 50.0, 61.5)
    assert row["thinking_s"] == pytest.approx(6.5) and row["tool_s"] == pytest.approx(4 + 6)
    assert row["n_tool_steps"] == 2 and row["n_failed_steps"] == 1 and row["failed_step_s"] == pytest.approx(4)
    assert row["timed_out"] is False and row["cost_unknown"] is False and row["flags"] == ""
    assert row["has_result"] is True


def test_a_run_stopped_at_the_wall_limit(tmp_path):
    path = write_run(tmp_path, "m/A/medium/P-numerical-01-k1", [use("a", "Bash", {"command": "x"}, at=1)],
                     meta={"timed_out": True, "flags": ["timeout", "cost_unknown"], "cost_unknown": True,
                           "wall_time_s": 900.4})
    row = effort.effort_of(path, read_transcript(path))
    assert row["timed_out"] is True and row["cost_unknown"] is True and row["flags"] == "timeout cost_unknown"
    assert row["has_result"] is False and row["thinking_tokens"] is None and row["num_turns"] is None
    assert row["wall_time_s"] == 900.4


def _progress(n):
    return {"type": "system", "subtype": "thinking_tokens", "estimated_tokens": n, "estimated_tokens_delta": 50}


def test_the_thinking_estimate_sums_the_last_estimate_of_each_turn(tmp_path):
    # the estimate restarts with every turn; a run stopped mid-thought has only these lines
    path = write_run(tmp_path, "m/A/medium/P-numerical-01-k1",
                     [_progress(50), _progress(400), use("a", "Bash", {"command": "x"}, at=1), _progress(50),
                      _progress(120), _progress(70000)], meta={"timed_out": True, "flags": ["timeout"]})
    assert effort.estimated_thinking(path) == 400 + 70000
    row = effort.effort_of(path, read_transcript(path))
    assert row["estimated_thinking_tokens"] == 70400 and row["thinking_tokens"] is None


def test_no_progress_lines_no_estimate(tmp_path):
    path = write_run(tmp_path, "m/A/medium/P-numerical-01-k1", result(ANSWER))
    assert effort.estimated_thinking(path) is None


def test_a_run_without_a_sidecar_has_no_flags(tmp_path):
    path = write_run(tmp_path, "m/A/medium/P-numerical-01-k1", result(ANSWER))
    row = effort.effort_of(path, read_transcript(path))
    assert row["timed_out"] is None and row["wall_time_s"] is None and row["flags"] == ""


def test_main_writes_runs_groups_timeouts_and_tasks(tmp_path, capsys):
    runs, out = tmp_path / "runs", tmp_path / "out"
    _finished(runs, "m/B/medium/P-numerical-01-k1", thinking=900)
    _finished(runs, "m/B/medium/P-numerical-01-k2", thinking=3000)
    _finished(runs, "m/B/medium/P-numerical-01-k3", thinking=1000)
    write_run(runs, "m/B/medium/P-crossover-01-k1", [use("a", "Bash", {"command": "x"}, at=1)],
              meta={"timed_out": True, "flags": ["timeout"], "wall_time_s": 900.0})
    write_scores(runs, [{"run_id": "m/B/medium/P-numerical-01-k1", "correct": "True"},
                        {"run_id": "m/B/medium/P-numerical-01-k2", "correct": "False"},
                        {"run_id": "m/B/medium/P-numerical-01-k3", "correct": "True"},
                        {"run_id": "m/B/medium/P-crossover-01-k1", "correct": "False"}])
    (runs / "metrics").mkdir()
    (runs / "metrics" / "consistency.csv").write_text(
        "model,condition,effort,n_tasks,n_unanimous,unanimity_rate,mean_pairwise_agreement,n_tasks_cv,median_cv_dq\n"
        "m,B,medium,2,1,0.5,0.6666666666666666,1,0.01\n", encoding="utf-8")
    assert effort.main(["--runs", str(runs), "--out", str(out)]) == 0
    rows = read_csv(out / "runs.csv")
    assert len(rows) == 4 and rows[0]["correct"] == "False" and rows[0]["timed_out"] == "True"
    (group,) = read_csv(out / "by_group.csv")
    assert (group["n_runs"], group["n_timeout"], group["n_correct"]) == ("4", "1", "2")
    assert group["median_thinking_tokens_correct"] == "950" and group["median_thinking_tokens_wrong"] == "3000"
    assert group["unanimity_rate"] == "0.5" and group["mean_pairwise_agreement"] == "0.666667"
    (timeout,) = read_csv(out / "timeouts.csv")
    assert timeout["run_id"] == "m/B/medium/P-crossover-01-k1" and timeout["class"] == "crossover"
    tasks = read_csv(out / "tasks.csv")
    num = [t for t in tasks if t["task_id"] == "P-numerical-01"][0]
    assert (num["k"], num["n_correct"], num["unanimous"], num["median_thinking_tokens"]) == ("3", "2", "False",
                                                                                            "1000")
    assert "wall" in (out / "README.md").read_text(encoding="utf-8")
    assert "timeouts: 1" in capsys.readouterr().out


def test_without_consistency_csv_the_columns_stay_empty(tmp_path):
    runs, out = tmp_path / "runs", tmp_path / "out"
    _finished(runs)
    assert effort.main(["--runs", str(runs), "--out", str(out)]) == 0
    (group,) = read_csv(out / "by_group.csv")
    assert group["unanimity_rate"] == "" and group["n_runs"] == "1"


def test_the_result_columns_of_a_finished_run(tmp_path):
    path = _finished(tmp_path)
    row = effort.effort_of(path, read_transcript(path))
    assert row["result_subtype"] == "success" and row["cost_usd"] == 0.01


def test_a_run_without_a_result_has_empty_result_columns(tmp_path):
    path = write_run(tmp_path, "m/A/medium/P-numerical-01-k1", [use("a", "Bash", {"command": "x"}, at=1)])
    row = effort.effort_of(path, read_transcript(path))
    assert row["output_tokens"] is None and row["result_subtype"] == "" and row["cost_usd"] is None


def test_a_flag_of_the_sidecar_that_is_no_boolean_is_dropped(tmp_path):
    path = write_run(tmp_path, "m/A/medium/P-numerical-01-k1", result(ANSWER),
                     meta={"timed_out": "yes", "cost_unknown": 1})
    row = effort.effort_of(path, read_transcript(path))
    assert row["timed_out"] is None and row["cost_unknown"] is None


@pytest.mark.parametrize("v,want", [(3, 3), (1.5, 1.5), ("x", None), (None, None), (True, None)])
def test_only_numbers_are_kept(v, want):
    assert effort._num(v) == want and type(effort._num(v)) is type(want)


@pytest.mark.parametrize("estimates,want", [
    ([0, 5], 5),  # the first estimate of 0 is no restart
    ([100, 100], 100),  # an equal estimate is no restart
    ([10, 5, 20, 7], 37),  # three turns: 10, 20 and 7
])
def test_the_estimate_at_the_turn_boundaries(tmp_path, estimates, want):
    path = write_run(tmp_path, "m/A/medium/P-numerical-01-k1", [_progress(n) for n in estimates])
    assert effort.estimated_thinking(path) == want


def test_a_progress_line_without_an_estimate_is_passed_over(tmp_path):
    path = write_run(tmp_path, "m/A/medium/P-numerical-01-k1",
                     [_progress(10), {"type": "system", "subtype": "thinking_tokens"}, _progress(30)])
    assert effort.estimated_thinking(path) == 30


def test_a_transcript_with_bytes_that_are_no_utf8_is_read(tmp_path):
    path = tmp_path / "run.jsonl"
    path.write_bytes(b'{"subtype": "thinking_tokens", "note": "\xff", "estimated_tokens": 7}\n')
    assert effort.estimated_thinking(path) == 7


def _r(thinking, correct, **kw):
    return {"thinking_tokens": thinking, "correct": correct, **kw}


def test_the_rank_correlation_is_spearman_over_the_runs_with_thinking_tokens():
    rows = [_r(1, False), _r(2, None), _r(3, True), _r(100, True), _r(None, False)]
    assert effort._rank_corr(rows) == pytest.approx(0.8944271909999159)


def test_the_rank_correlation_is_negative_when_long_thinking_is_wrong():
    rows = [_r(1, True), _r(2, True), _r(3, False), _r(4, None)]
    assert effort._rank_corr(rows) == pytest.approx(-0.8944271909999159)


def test_the_rank_correlation_needs_three_runs_and_two_outcomes():
    assert effort._rank_corr([_r(1, False), _r(2, True), _r(3, True)]) == pytest.approx(0.8660254037844386)
    assert effort._rank_corr([_r(1, False), _r(2, True), _r(None, True)]) is None
    assert effort._rank_corr([_r(1, True), _r(2, True), _r(3, True)]) is None
    assert effort._rank_corr([_r(1, False), _r(2, False), _r(3, None)]) is None


def test_the_share_of_wall_time_uses_the_runs_with_both_numbers():
    rows = [{"wall_time_s": 80.0, "k": 20.0}, {"wall_time_s": 40.0, "k": 10.0}, {"wall_time_s": 0, "k": 5.0},
            {"wall_time_s": None, "k": 1.0}, {"wall_time_s": 50.0, "k": None}]
    assert effort._share(rows, "k") == pytest.approx(30.0 / 120.0)
    assert effort._share([{"wall_time_s": None, "k": 1.0}], "k") is None
    assert effort._share([], "k") is None


@pytest.mark.parametrize("values,want", [
    ([1, 3], 2 ** 0.5 / 2),  # two values are enough
    ([1, None, 3], 2 ** 0.5 / 2),
    ([0.5, 1.5], 2 ** 0.5 / 2),  # a mean of 1 is positive
    ([1], None), ([None, None], None), ([0, 0], None), ([-1, 1], None), ([-3, 1], None),
])
def test_the_coefficient_of_variation(values, want):
    assert effort._cv(values) == (want if want is None else pytest.approx(want))


def _run_row(model="m", condition="B", level="medium", task="P-numerical-01", cls="numerical", **kw):
    return {"model": model, "condition": condition, "effort": level, "task_id": task, "class": cls, "correct": None,
            "timed_out": None, "cost_unknown": None, "thinking_tokens": None, "output_tokens": None,
            "wall_time_s": None, "num_turns": None, "thinking_s": None, "tool_s": None, "failed_step_s": None, **kw}


def test_the_groups_of_runs_are_exact():
    rows = [_run_row(correct=True, timed_out=False, cost_unknown=True, thinking_tokens=100, output_tokens=10,
                     wall_time_s=100.0, num_turns=3, thinking_s=10.0, tool_s=20.0, failed_step_s=5.0),
            _run_row(correct=False, cost_unknown=False, thinking_tokens=300, output_tokens=30, wall_time_s=300.0,
                     num_turns=7, thinking_s=30.0, tool_s=60.0, failed_step_s=15.0),
            _run_row(timed_out=True, cost_unknown=False, thinking_tokens=200, output_tokens=20, wall_time_s=200.0,
                     num_turns=5),
            _run_row(correct=True, thinking_tokens=400, output_tokens=40, wall_time_s=400.0, num_turns=9),
            _run_row(model="a", condition="C", level="high")]
    consistency = [{"model": "m", "condition": "B", "effort": "medium", "n_tasks": "2", "n_unanimous": "1",
                    "unanimity_rate": "0.5", "mean_pairwise_agreement": "0.75", "median_cv_dq": ""}]
    empty = dict.fromkeys(("median_thinking_tokens", "median_thinking_tokens_correct",
                           "median_thinking_tokens_wrong", "median_output_tokens", "median_output_tokens_correct",
                           "median_output_tokens_wrong", "median_wall_time_s", "median_wall_time_s_correct",
                           "median_wall_time_s_wrong", "median_num_turns", "rank_corr_thinking_correct",
                           "thinking_share_of_wall", "tool_share_of_wall", "failed_step_share_of_wall",
                           "n_tasks", "n_unanimous", "unanimity_rate", "mean_pairwise_agreement", "median_cv_dq"))
    assert effort._groups(rows, consistency) == [
        {**empty, "model": "a", "condition": "C", "effort": "high", "n_runs": 1, "n_correct": 0, "n_timeout": 0,
         "n_cost_unknown": 0},
        {"model": "m", "condition": "B", "effort": "medium", "n_runs": 4, "n_correct": 2, "n_timeout": 1,
         "n_cost_unknown": 1,
         "rank_corr_thinking_correct": pytest.approx(effort._rank_corr(rows[:4])),
         "thinking_share_of_wall": pytest.approx(0.1), "tool_share_of_wall": pytest.approx(0.2),
         "failed_step_share_of_wall": pytest.approx(0.05),
         "median_thinking_tokens": 250.0, "median_thinking_tokens_correct": 250.0,
         "median_thinking_tokens_wrong": 250.0,
         "median_output_tokens": 25.0, "median_output_tokens_correct": 25.0, "median_output_tokens_wrong": 25.0,
         "median_wall_time_s": 250.0, "median_wall_time_s_correct": 250.0, "median_wall_time_s_wrong": 250.0,
         "median_num_turns": 6.0, "n_tasks": 2.0, "n_unanimous": 1.0, "unanimity_rate": 0.5,
         "mean_pairwise_agreement": 0.75, "median_cv_dq": None}]


def test_the_rows_per_task_are_exact():
    rows = [_run_row(correct=True, timed_out=True, thinking_tokens=100, wall_time_s=10.0),
            _run_row(correct=False, timed_out=False, thinking_tokens=300, wall_time_s=30.0),
            _run_row(timed_out=False, thinking_tokens=None, wall_time_s=20.0),
            _run_row(model="a", condition="C", level="high", task="P-crossover-01", cls="crossover", correct=True)]
    assert effort._tasks(rows) == [
        {"model": "a", "condition": "C", "effort": "high", "task_id": "P-crossover-01", "class": "crossover", "k": 1,
         "n_correct": 1, "unanimous": True, "n_timeout": 0, "median_thinking_tokens": None,
         "cv_thinking_tokens": None, "median_wall_time_s": None},
        {"model": "m", "condition": "B", "effort": "medium", "task_id": "P-numerical-01", "class": "numerical",
         "k": 3, "n_correct": 1, "unanimous": False, "n_timeout": 1, "median_thinking_tokens": 200.0,
         "cv_thinking_tokens": pytest.approx(2 ** 0.5 * 100 / 200), "median_wall_time_s": 20.0}]
