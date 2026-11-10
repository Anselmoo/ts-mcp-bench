"""Tests for src/tsbench/analyze/errors.py: which tool steps failed, how, and what the run did after the first one."""
from __future__ import annotations

import pytest
from analyze_runs import bash, mcp, read_csv, res, result, use, write_run, write_scores

from tsbench.analyze import errors
from tsbench.score.extract import read_transcript

ANSWER = {"Dq": 2044.0, "B": 702.0, "C": None, "out_of_scope": False, "reason": "fit"}
SPH = ("Exit code 1\nTraceback (most recent call last):\n  File \"/tmp/run/a.py\", line 2, in <module>\n"
       "    from scipy.special import sph_harm\n"
       "ImportError: cannot import name 'sph_harm' from 'scipy.special' (<B_VENV>/lib/python3.14/site.py)")


@pytest.mark.parametrize("text,err,exit_code,want", [
    (SPH, True, 1, ("python", "ImportError", "scipy.special.sph_harm")),
    ("Traceback (most recent call last):\nAttributeError: module 'scipy.special' has no attribute 'sph_harm'",
     True, 1, ("python", "AttributeError", "scipy.special.sph_harm")),
    ("Traceback (most recent call last):\nModuleNotFoundError: No module named 'd3'", True, 1,
     ("python", "ModuleNotFoundError", "d3")),
    ("Traceback (most recent call last):\nNameError: name 'np' is not defined", True, 1,
     ("python", "NameError", "np")),
    ("Traceback (most recent call last):\nAttributeError: 'list' object has no attribute 'shape'", True, 1,
     ("python", "AttributeError", "list.shape")),
    ("Traceback (most recent call last):\nnumpy.linalg.LinAlgError: Singular matrix", True, 1,
     ("python", "numpy.linalg.LinAlgError", "")),
    ("  File \"a.py\", line 3\n    x = (\nSyntaxError: '(' was never closed", True, 1, ("python", "SyntaxError", "")),
    ("/bin/bash: line 34: /tmp/a.py: Read-only file system", False, 0, ("shell", "", "")),
    ("/bin/bash: line 1: pip: command not found\nok", False, 0, ("shell", "", "")),
    ("Exit code 1\nmkdir: cannot create directory '/tmp/w': Read-only file system", True, 1, ("shell", "", "")),
    ("Exit code 2\npython3: can't open file '/tmp/a.py': [Errno 2] No such file or directory", True, 2,
     ("shell", "", "")),
    ("Command timed out after 2m 0s\npartial", True, None, ("timeout", "", "")),
    ("<tool_use_error>Error: No such tool available: bash.</tool_use_error>", True, None, ("tool_error", "", "")),
    ('{"result":{"error":"Fitting failed: Eigenvalues did not converge"}}', False, 0, ("mcp_error", "", "")),
    ('{"title": "No fit", "series": [], "error": "Could not converge"}', False, 0, ("mcp_error", "", "")),
    ("Exit code 2\nusage: x", True, 2, ("exit", "", "")),
    ("validation error for call[ts_terms_table_data]", True, None, ("is_error", "", "")),
])
def test_a_failing_step_is_classified(text, err, exit_code, want):
    got = errors.classify(text, err, exit_code)
    assert (got["kind"], got["exception"], got["missing_name"]) == want
    assert got["message"] and len(got["message"]) <= errors.MESSAGE_MAX


@pytest.mark.parametrize("text,exit_code", [
    ("Dq = 2044.0\n", 0),
    ("ValueError: this text is printed, nothing was raised\n", 0),  # no traceback and no failure: printed text
    ('{"result": {"fitted_Dq": 2044.0, "error_cm1": 1.2}}', 0),
    ("", None),
])
def test_a_clean_step_is_no_failure(text, exit_code):
    assert errors.classify(text, False, exit_code) is None


def test_the_message_of_a_bare_exit_is_the_line_after_the_exit_code():
    assert errors.classify("Exit code 1\n\n/tmp/home\n", True, 1)["message"] == "/tmp/home"
    assert errors.classify("Exit code 3", True, 3)["message"] == "Exit code 3"
    assert errors.classify("Exit code 1\nmkdir: cannot create directory 'w'", True, 1)["message"].startswith("mkdir")


def test_the_last_exception_of_a_chained_traceback_is_the_one_raised():
    text = ("Traceback (most recent call last):\nKeyError: 3\n\nDuring handling of the above exception, another "
            "exception occurred:\n\nTraceback (most recent call last):\nValueError: bad value")
    assert errors.classify(text, True, 1)["exception"] == "ValueError"


def _run(tmp_path, name="m/B/medium/P-numerical-01-k1"):
    events = [*bash("a", "python3 a.py", SPH, err=True, at=10, done=12),
              *bash("b", "cat > /tmp/a.py <<'E'\nx\nE", "/bin/bash: line 1: /tmp/a.py: Read-only file system",
                    at=20, done=21),
              *bash("c", "python3 b.py", "Dq = 2044.0", at=40, done=45),
              *bash("d", "python3 c.py", "Exit code 1\nTraceback (most recent call last):\nKeyError: 3", err=True,
                    at=50, done=52),
              *result(ANSWER)]
    events[-1]["timestamp"] = "2026-11-03T07:01:40.000Z"  # 100 s
    return write_run(tmp_path, name, events)


def test_a_run_with_errors(tmp_path):
    path = _run(tmp_path)
    summary, failing = errors.run_errors(read_transcript(path))
    assert [f["step"] for f in failing] == [0, 1, 3]
    assert [f["kind"] for f in failing] == ["python", "shell", "python"]
    assert summary["n_steps"] == 4 and summary["n_failed_steps"] == 3
    assert summary["first_error_step"] == 0 and summary["steps_to_first_ok"] == 2
    assert summary["recovered"] is True and summary["last_step_failed"] is True
    assert summary["first_exception"] == "ImportError" and summary["first_missing_name"] == "scipy.special.sph_harm"
    assert summary["wall_after_first_error_s"] == pytest.approx(88.0)  # 12 s -> 100 s
    # step time: from the result before it (or the first event) to its own result: 2 + 9 + 7 s
    assert summary["failed_step_s"] == pytest.approx(2 + 9 + 7)
    assert summary["span_s"] == pytest.approx(90.0)
    assert summary["kinds"] == "python:2 shell:1" and summary["exceptions"] == "ImportError KeyError"


def test_a_clean_run_and_a_run_without_tools(tmp_path):
    clean = write_run(tmp_path, "m/B/medium/P-numerical-01-k2", [*bash("a", "ls", "x"), *result(ANSWER)])
    s, failing = errors.run_errors(read_transcript(clean))
    assert failing == [] and s["n_steps"] == 1 and s["steps_to_first_ok"] == 0 and s["recovered"] is False
    assert s["first_error_step"] is None and s["wall_after_first_error_s"] is None
    none = write_run(tmp_path, "m/A/medium/P-numerical-01-k1", result(ANSWER))
    s, failing = errors.run_errors(read_transcript(none))
    assert failing == [] and s["n_steps"] == 0 and s["steps_to_first_ok"] is None


def test_an_mcp_error_in_condition_c(tmp_path):
    path = write_run(tmp_path, "m/C/medium/P-numerical-01-k1", [
        *mcp("a", "ts_fit_spectrum", {"d_count": 2}, '{"result":{"error":"Fitting failed: no"}}'),
        *mcp("b", "ts_fit_spectrum", {"d_count": 2}, '{"result":{"fitted_Dq":2044.0}}'), *result(ANSWER)])
    s, failing = errors.run_errors(read_transcript(path))
    assert [(f["tool"], f["kind"]) for f in failing] == [("mcp__tanabesugano__ts_fit_spectrum", "mcp_error")]
    assert s["recovered"] is True and s["last_step_failed"] is False


def test_main_writes_runs_steps_exceptions_and_groups(tmp_path, capsys):
    runs, out = tmp_path / "runs", tmp_path / "out"
    _run(runs)
    write_run(runs, "m/B/medium/P-numerical-01-k2", [*bash("a", "ls", "x"), *result(ANSWER)])
    write_scores(runs, [{"run_id": "m/B/medium/P-numerical-01-k1", "correct": "True"},
                        {"run_id": "m/B/medium/P-numerical-01-k2", "correct": "False"}])
    assert errors.main(["--runs", str(runs), "--out", str(out)]) == 0
    rows = read_csv(out / "runs.csv")
    assert [r["n_failed_steps"] for r in rows] == ["3", "0"] and rows[0]["correct"] == "True"
    steps = read_csv(out / "steps.csv")
    assert [s["step"] for s in steps] == ["0", "1", "3"] and steps[0]["missing_name"] == "scipy.special.sph_harm"
    exc = read_csv(out / "exceptions.csv")
    sph = [e for e in exc if e["missing_name"] == "scipy.special.sph_harm"]
    assert len(sph) == 1 and sph[0]["n_steps"] == "1" and sph[0]["n_runs"] == "1"
    (group,) = read_csv(out / "by_group.csv")
    assert group["model"] == "m" and group["condition"] == "B" and group["n_runs"] == "2"
    assert group["n_steps"] == "5" and group["n_failed_steps"] == "3" and group["n_runs_with_failure"] == "1"
    assert group["n_recovered"] == "1" and group["n_correct_with_failure"] == "1"
    assert group["n_correct_without_failure"] == "0"
    assert "Traceback" in (out / "README.md").read_text(encoding="utf-8")
    assert "failing steps: 3" in capsys.readouterr().out


def _failure(text, err, exit_code) -> dict:
    got = errors.classify(text, err, exit_code)
    assert got is not None
    return got


@pytest.mark.parametrize("text,err,exit_code", [("ValueError: bad", False, 1), ("ValueError: bad", True, None)])
def test_either_the_exit_code_or_the_error_flag_makes_an_exception_line_a_failure(text, err, exit_code):
    assert _failure(text, err, exit_code)["kind"] == "python"


def test_the_exact_message_of_each_fallback():
    assert _failure("<tool_use_error></tool_use_error>", True, None)["message"] == "tool_use_error"
    assert _failure("<tool_use_error>no tool</tool_use_error>", True, None)["message"] == "no tool"
    assert errors.classify("", True, None) == {"kind": "is_error", "exception": "", "missing_name": "",
                                               "message": "error flag"}
    assert _failure("flagged", True, None)["message"] == "flagged"


def test_only_the_first_exit_code_is_cut_from_the_message():
    assert _failure("Exit code 1\nExit code 2", True, 1)["message"] == "Exit code 2"


def test_a_missing_name_is_read_for_python_failures_only():
    got = _failure("/bin/bash: line 1: No module named 'd3'", False, 0)
    assert got == {"kind": "shell", "exception": "", "missing_name": "", "message": got["message"]}
    assert got["message"] == "/bin/bash: line 1: No module named 'd3'"


@pytest.mark.parametrize("text,want", [
    ('  {"error": "boom"}', "boom"),  # leading white space is still JSON
    ('{"error": "top", "result": {"error": "inner"}}', "top"),
    ('{"result": {"error": "inner"}}', "inner"),
    ('{"error": "top", "result": {}}', "top"),
    ('{"error": 7}', "7"),
    ('{"error": ""}', ""),
    ('{"result": 3}', ""),
    ("{not json", ""),
    ("[1, 2]", ""),
    ("", ""),
])
def test_the_error_field_of_an_mcp_result(text, want):
    assert errors._mcp_error(text) == want


def test_tool_steps_read_the_exit_code_and_the_error_flag(tmp_path):
    path = write_run(tmp_path, "m/B/medium/P-numerical-01-k1", [
        *bash("a", "x", "boom", err=True),  # the flag alone: exit 1
        *bash("b", "x", "Exit code 7\nusage", err=True),  # the reported code wins over the flag
        *bash("c", "x", "Exit code 2\nusage"),  # a code without the flag
        *bash("d", "x", "Exit code 0\nwarning", err=True),  # the flag with code 0
        *bash("e", "x", "fine"),
        use("f", "Bash", {"command": "x"}),  # no result
        *result(ANSWER)])
    steps = errors.tool_steps(read_transcript(path))
    assert [(s["step"], s["exit"], s["is_error"], (s["failure"] or {}).get("kind")) for s in steps] == [
        (0, 1, True, "exit"), (1, 7, True, "exit"), (2, 2, False, "exit"), (3, 0, True, "is_error"),
        (4, 0, False, None), (5, None, False, None)]
    assert steps[2]["failure"]["message"] == "usage"
    assert steps[3]["failure"]["message"] == "Exit code 0"


def test_a_tool_step_without_a_name_has_an_empty_tool(tmp_path):
    path = write_run(tmp_path, "m/B/medium/P-numerical-01-k1", [use("a", None, {}), res("a", "ok"), *result(ANSWER)])
    (step,) = errors.tool_steps(read_transcript(path))
    assert step["tool"] == ""


def test_a_tool_step_with_an_empty_id_keeps_its_times(tmp_path):
    path = write_run(tmp_path, "m/B/medium/P-numerical-01-k1", [use("", "Bash", {"command": "x"}, at=1),
                                                                res("", "ok", at=4), *result(ANSWER)])
    (step,) = errors.tool_steps(read_transcript(path))
    assert (step["step_s"], step["exec_s"]) == (pytest.approx(3.0), pytest.approx(3.0))


def test_a_tool_step_with_an_id_that_is_no_string_has_no_times(tmp_path):
    path = write_run(tmp_path, "m/B/medium/P-numerical-01-k1", [use(["x"], "Bash", {"command": "x"}, at=1),
                                                                *result(ANSWER)])
    (step,) = errors.tool_steps(read_transcript(path))
    assert (step["step_s"], step["exec_s"], step["done"], step["exit"]) == (None, None, None, None)


def test_given_steps_are_used_instead_of_the_transcript(tmp_path):
    path = _run(tmp_path)
    summary, failing = errors.run_errors(read_transcript(path), [])
    assert failing == [] and summary["n_steps"] == 0 and summary["last_step_failed"] is False


def test_the_failing_rows_and_the_exact_summary_columns(tmp_path):
    path = write_run(tmp_path, "m/B/medium/P-numerical-01-k1", [
        *bash("a", "x", "Traceback (most recent call last):\nModuleNotFoundError: No module named 'd3'", err=True),
        *bash("b", "x", "Traceback (most recent call last):\nNameError: name 'np' is not defined", err=True),
        *bash("c", "x", "Traceback (most recent call last):\nNameError: name 'np' is not defined", err=True),
        *result(ANSWER)])
    summary, failing = errors.run_errors(read_transcript(path))
    assert summary["first_error_kind"] == "python" and summary["missing_names"] == "d3 np"
    assert summary["exceptions"] == "ModuleNotFoundError NameError"
    assert summary["recovered"] is False and summary["steps_to_first_ok"] is None
    assert [(f["exit"], f["is_error"]) for f in failing] == [(1, True)] * 3


def test_a_clean_run_leaves_the_first_error_columns_empty(tmp_path):
    path = write_run(tmp_path, "m/B/medium/P-numerical-01-k1", [*bash("a", "ls", "x"), *result(ANSWER)])
    summary, _ = errors.run_errors(read_transcript(path))
    assert (summary["first_error_kind"], summary["first_exception"], summary["first_missing_name"]) == ("", "", "")
    assert summary["kinds"] == "" and summary["exceptions"] == "" and summary["missing_names"] == ""


def _row(condition="B", n_steps=1, n_failed=0, span=None, failed_s=None, recovered=False, last=False, correct=None,
         wall=None):
    return {"model": "m", "condition": condition, "n_steps": n_steps, "n_failed_steps": n_failed, "span_s": span,
            "failed_step_s": failed_s, "recovered": recovered, "last_step_failed": last, "correct": correct,
            "wall_after_first_error_s": wall}


def test_the_groups_are_exact():
    rows = [_row(n_steps=4, n_failed=2, span=10.0, failed_s=3.0, recovered=True, correct=True, wall=6.0),
            _row(n_steps=2, n_failed=1, last=True),
            _row(n_steps=3, n_failed=1, span=20.0, failed_s=1.0, recovered=True, last=True, wall=8.0),
            _row(n_steps=2, span=5.0, failed_s=0, correct=True),
            _row(correct=True),
            _row(span=5.0),
            _row(n_steps=0, span=100.0, failed_s=50.0, correct=True),  # no steps: left out of the time sums
            _row("A", n_steps=0)]
    assert errors._groups(rows) == [
        {"model": "m", "condition": "A", "n_runs": 1, "n_runs_with_steps": 0, "n_steps": 0, "n_failed_steps": 0,
         "failed_step_share": None, "n_runs_with_failure": 0, "n_recovered": 0, "n_last_step_failed": 0,
         "n_correct_with_failure": 0, "n_runs_without_failure": 0, "n_correct_without_failure": 0,
         "accuracy_with_failure": None, "accuracy_without_failure": None, "median_wall_after_first_error_s": None,
         "failed_step_s": 0, "span_s": 0, "failed_time_share": None},
        {"model": "m", "condition": "B", "n_runs": 7, "n_runs_with_steps": 6, "n_steps": 13, "n_failed_steps": 4,
         "failed_step_share": 4 / 13, "n_runs_with_failure": 3, "n_recovered": 2, "n_last_step_failed": 2,
         "n_correct_with_failure": 1, "n_runs_without_failure": 3, "n_correct_without_failure": 2,
         "accuracy_with_failure": 1 / 3, "accuracy_without_failure": 2 / 3, "median_wall_after_first_error_s": 7.0,
         "failed_step_s": 4.0, "span_s": 40.0, "failed_time_share": 0.1}]


def test_the_exceptions_are_sorted_by_count_then_by_key():
    def step(run, kind, exception):
        return {"run_id": run, "model": "m", "condition": "B", "kind": kind, "exception": exception,
                "missing_name": ""}

    rows = errors._exceptions([step("r1", "python", "ValueError"), step("r1", "python", "KeyError"),
                               step("r2", "shell", ""), step("r2", "shell", ""), step("r3", "shell", "")])
    assert [(r["kind"], r["exception"], r["n_steps"], r["n_runs"]) for r in rows] == [
        ("shell", "", 3, 2), ("python", "KeyError", 1, 1), ("python", "ValueError", 1, 1)]
    assert rows[0] == {"model": "m", "condition": "B", "kind": "shell", "exception": "", "missing_name": "",
                       "n_steps": 3, "n_runs": 2}
