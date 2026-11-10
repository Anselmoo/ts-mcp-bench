"""Tests for src/tsbench/analyze/common.py: the guards of the commands, the runs of a folder, times and tables."""
from __future__ import annotations

import json
import types
from typing import cast

import pytest
from analyze_runs import T0, bash, read_csv, result, use, write_run, write_scores

from tsbench.analyze import common
from tsbench.score.extract import Transcript

ANSWER = {"Dq": 2044.0, "B": 702.0, "C": None, "out_of_scope": False, "reason": "fit"}


def test_out_inside_runs_is_refused(tmp_path, capsys):
    with pytest.raises(SystemExit) as e:
        common.arguments("tsbench analyze x", "doc", ["--runs", str(tmp_path), "--out", str(tmp_path / "o")])
    assert e.value.code == 2 and "must not be inside --runs" in capsys.readouterr().err


def test_the_confirmatory_split_needs_a_doi(tmp_path, capsys):
    runs = tmp_path / "runs"
    runs.mkdir()
    argv = ["--runs", str(runs), "--out", str(tmp_path / "o"), "--split", "confirmatory"]
    with pytest.raises(SystemExit) as e:
        common.arguments("tsbench analyze x", "doc", argv)
    assert e.value.code == 2 and "--i-have-preregistered" in capsys.readouterr().err
    got = common.arguments("tsbench analyze x", "doc", [*argv, "--i-have-preregistered", "10.5281/zenodo.1"])
    assert got == (runs.resolve(), (tmp_path / "o").resolve(), "confirmatory")


def test_a_run_set_of_another_split_is_refused(tmp_path, capsys):
    runs = tmp_path / "runs"
    runs.mkdir()
    (runs / "plan.jsonl").write_text(json.dumps({"spec": {"split": "confirmatory"}}) + "\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        common.arguments("tsbench analyze x", "doc", ["--runs", str(runs), "--out", str(tmp_path / "o")])
    assert "--i-have-preregistered" in capsys.readouterr().err


def test_a_missing_runs_folder_is_refused(tmp_path, capsys):
    with pytest.raises(SystemExit):
        common.arguments("tsbench analyze x", "doc", ["--runs", str(tmp_path / "no"), "--out", str(tmp_path / "o")])
    assert "no run folder" in capsys.readouterr().err


def test_runs_take_correct_and_class_from_scores_csv(tmp_path):
    write_run(tmp_path, "m/B/medium/P-numerical-01-k1", result(ANSWER))
    write_run(tmp_path, "m/B/medium/P-numerical-01-k2", result(ANSWER))
    write_scores(tmp_path, [{"run_id": "m/B/medium/P-numerical-01-k1", "correct": "False", "class": "numerical"},
                            {"run_id": "m/B/medium/P-numerical-01-k2", "correct": "True", "class": "numerical"}])
    runs = list(common.iter_runs(tmp_path, common.load_tasks("pilot")))
    assert [r.run_id for r in runs] == ["m/B/medium/P-numerical-01-k1", "m/B/medium/P-numerical-01-k2"]
    assert [r.correct for r in runs] == [False, True]  # the stored verdict, not a fresh one
    assert runs[0].model == "m" and runs[0].condition == "B" and runs[0].cls == "numerical"
    assert runs[0].task["id"] == "P-numerical-01" and runs[0].tr.result is not None


def test_without_scores_csv_the_run_is_scored_in_memory(tmp_path):
    write_run(tmp_path, "m/A/medium/P-numerical-01-k1", result(ANSWER))
    (run,) = common.iter_runs(tmp_path, common.load_tasks("pilot"))
    assert run.correct is True and run.cls == "numerical" and run.evaluable is True
    assert not (tmp_path / "scores.csv").exists()  # nothing is written into the run folder


def test_times_of_a_transcript(tmp_path):
    events = [use("a", "Bash", {"command": "ls"}, at=10, thinking_ms=1500)]
    events += bash("b", "ls", "x", at=20, done=23)[1:]
    events += [{"type": "user", "timestamp": "2026-11-03T07:00:12.000Z",
                "message": {"content": [{"type": "tool_result", "tool_use_id": "a", "content": "ok"}]}}]
    path = write_run(tmp_path, "m/B/medium/P-numerical-01-k1", events)
    from tsbench.score.extract import read_transcript
    t, t0 = common.times(read_transcript(path)), common.seconds(T0)
    assert (t.start - t0, t.end - t0, t.thinking_s) == (10, 23, 1.5)
    assert (t.use["a"] - t0, t.result["a"] - t0, t.result["b"] - t0) == (10, 12, 23)


def test_a_bad_timestamp_is_no_time():
    assert common.seconds("not a time") is None and common.seconds(None) is None
    assert common.seconds("2026-11-03T07:00:01.500Z") - common.seconds("2026-11-03T07:00:00Z") == 1.5


def test_tables_are_utf8_csv_with_empty_cells_for_none(tmp_path):
    common.write_csv(tmp_path / "t.csv", ["a", "b", "c"], [{"a": None, "b": True, "c": 0.1234567891}])
    assert (tmp_path / "t.csv").read_text(encoding="utf-8") == "a,b,c\n,True,0.123457\n"
    assert read_csv(tmp_path / "t.csv") == [{"a": "", "b": "True", "c": "0.123457"}]


def test_accuracy_has_an_exact_interval():
    got = common.accuracy(3, 4)
    assert got["n"] == 4 and got["n_correct"] == 3 and got["accuracy"] == 0.75
    assert 0 < got["ci_lo"] < 0.75 < got["ci_hi"] <= 1
    assert common.accuracy(0, 0) == {"n": 0, "n_correct": 0, "accuracy": None, "ci_lo": None, "ci_hi": None}


def test_median_skips_missing_values():
    assert common.median([3, None, 1, 2]) == 2 and common.median([None]) is None


def test_a_run_gives_its_repetition_number(tmp_path):
    write_run(tmp_path, "m/B/medium/P-numerical-01-k3", result(ANSWER))
    (run,) = common.iter_runs(tmp_path, common.load_tasks("pilot"))
    assert run.k == 3 and run.effort == "medium" and run.task_id == "P-numerical-01"


def test_the_class_of_scores_csv_wins_over_the_class_of_the_task(tmp_path):
    write_run(tmp_path, "m/B/medium/P-numerical-01-k1", result(ANSWER))
    write_scores(tmp_path, [{"run_id": "m/B/medium/P-numerical-01-k1", "correct": "True", "class": "stored"}])
    (run,) = common.iter_runs(tmp_path, common.load_tasks("pilot"))
    assert run.cls == "stored"


def test_an_empty_class_in_scores_csv_falls_back_to_the_task(tmp_path):
    write_run(tmp_path, "m/B/medium/P-numerical-01-k1", result(ANSWER))
    write_scores(tmp_path, [{"run_id": "m/B/medium/P-numerical-01-k1", "correct": "True", "class": ""}])
    (run,) = common.iter_runs(tmp_path, common.load_tasks("pilot"))
    assert run.cls == "numerical"


def test_a_run_of_an_unknown_task_without_a_score_row_has_no_verdict(tmp_path):
    write_run(tmp_path, "m/B/medium/P-unknown-99-k1", result(ANSWER))
    (run,) = common.iter_runs(tmp_path, common.load_tasks("pilot"))
    assert run.task is None and run.cls == "" and run.score == {}
    assert run.correct is None and run.evaluable is None


def test_a_row_scored_in_memory_has_empty_cells_for_none(tmp_path):
    write_run(tmp_path, "m/A/medium/P-numerical-01-k1", result(ANSWER))
    (run,) = common.iter_runs(tmp_path, common.load_tasks("pilot"))
    assert run.score["c"] == "" and run.score["wall_time_s"] == ""  # None in the scored row


def test_a_lower_case_z_is_no_timestamp():
    assert common.seconds("2026-11-03T07:00:00z") is None


def test_only_tool_blocks_with_a_string_id_give_times():
    blocks = ["text", {"type": "text", "id": "x"}, {"type": "other", "tool_use_id": "y"},
              {"type": "tool_use", "id": 7}, {"type": "tool_result", "tool_use_id": 8},
              {"type": "tool_use", "id": "a"}, {"type": "tool_result", "tool_use_id": "a"}]
    tr = types.SimpleNamespace(events=[{"timestamp": T0, "message": {"content": blocks}}])
    t = common.times(cast(Transcript, tr))
    assert list(t.use) == ["a"] and list(t.result) == ["a"]


def test_read_csv_keeps_a_line_break_inside_a_cell(tmp_path):
    (tmp_path / "t.csv").write_bytes(b'a\n"x\r\ny"\n')
    assert common.read_csv(tmp_path / "t.csv") == [{"a": "x\r\ny"}]
    assert common.read_csv(tmp_path / "missing.csv") == []


def test_tables_end_lines_with_a_line_feed_only(tmp_path):
    common.write_csv(tmp_path / "t.csv", ["a"], [{"a": 1}])
    assert (tmp_path / "t.csv").read_bytes() == b"a\n1\n"


def test_tables_create_their_folders(tmp_path):
    common.write_csv(tmp_path / "x" / "y" / "t.csv", ["a"], [])
    assert (tmp_path / "x" / "y" / "t.csv").read_bytes() == b"a\n"


def test_nan_is_an_empty_cell(tmp_path):
    common.write_csv(tmp_path / "t.csv", ["a", "b"], [{"a": float("nan"), "b": 2.0}])
    assert (tmp_path / "t.csv").read_bytes() == b"a,b\n,2\n"
