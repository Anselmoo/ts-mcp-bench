"""Tests for the runner when the quota is gone, and when a run set stops on an error: an exhausted cap, repeated 429
results, retired attempts, a crash, a binary that does not start.

Dry runs only (the fake claude). The backoff sleep is replaced, so no test waits.
Run: python -m pytest tests/run/test_runner_quota.py -q
"""
from __future__ import annotations

import itertools
import json
import pathlib
import tempfile

import pytest

from tsbench import conditions
from tsbench.run import runner

HAIKU = "claude-haiku-5-5"
# the sentence a gateway with a daily request cap sends when the cap is used up
GATEWAY_429 = ("API Error: Request rejected (429) · Rate limit exceeded: user daily request limit reached "
               "(7 of 7). Retry after 86400 seconds.")
# another wording of the same stop
GATEWAY_429_EXHAUSTED = "API Error: Request rejected (429) · User daily request rate limit exhausted (7 of 7)."
GENERIC_429 = "API Error: Request rejected (429) · API rate limit exceeded"


@pytest.fixture(autouse=True)
def quiet_clock(monkeypatch, tmp_path_factory):
    """Nothing sleeps, nothing retries unless a test asks, and condition B never touches the real venv."""
    slept: list[float] = []
    monkeypatch.setattr(runner, "sleep", slept.append)
    monkeypatch.setenv("TSBENCH_429_MAX_RETRIES", "0")
    d = tmp_path_factory.getbasetemp() / "fake-venv-B-quota"
    (d / "bin").mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("TSBENCH_B_VENV", str(d))
    return slept


def run_a(tmp_path, *, limit, extra=(), out=None):
    out = out or tmp_path / "runs"
    rc = runner.main(["--split", "pilot", "--models", HAIKU, "--conditions", "A", "--effort", "medium", "--k", "1",
                      "--budget-usd", "10", "--out", str(out), "--dry-run", "--limit", str(limit), *extra])
    return rc, pathlib.Path(out)


def manifest(out: pathlib.Path) -> dict:
    return json.loads((out / "MANIFEST.json").read_text(encoding="utf-8"))


def calls(tmp_path) -> int:
    p = tmp_path / "count"
    return int(p.read_text(encoding="utf-8")) if p.exists() else 0


def all_rate_limited(monkeypatch, tmp_path, text=None):
    monkeypatch.setenv("FAKE_429_FIRST", "99")
    monkeypatch.setenv("FAKE_429_STATE", str(tmp_path / "count"))
    if text:
        monkeypatch.setenv("FAKE_429_TEXT", text)


def limited_outcome(transcript: pathlib.Path) -> runner.Outcome:
    res = {"type": "result", "subtype": "success", "is_error": True, "api_error_status": 429, "result": GENERIC_429,
           "total_cost_usd": 0, "permission_denials": []}
    transcript.parent.mkdir(parents=True, exist_ok=True)
    transcript.write_text(json.dumps(res) + "\n", encoding="utf-8")
    return runner.Outcome(events=[res], init=None, mismatches=[], result=res, exit_code=0, wall_s=0.0,
                          stderr_tail="", timed_out=False, init_aborted=False)


def follow_pattern(monkeypatch, pattern):
    """The n-th call to `execute` is rate limited when pattern[n] is true; the others run the fake claude."""
    real = runner.execute
    n = itertools.count()

    def execute(argv, prompt, env, transcript, *a, **kw):
        if pattern[next(n)]:
            return limited_outcome(pathlib.Path(transcript))
        return real(argv, prompt, env, transcript, *a, **kw)

    monkeypatch.setattr(runner, "execute", execute)


# ------------------------------------------------------------------ the gateway says the cap is used up
def test_exhausted_text_stops_after_one_call_without_backoff(tmp_path, monkeypatch, quiet_clock, capsys):
    all_rate_limited(monkeypatch, tmp_path, GATEWAY_429)
    monkeypatch.setenv("TSBENCH_429_MAX_RETRIES", "4")  # the retries are on: the sentence must still end it at once
    rc, out = run_a(tmp_path, limit=5)
    m = manifest(out)
    assert rc == 75 and calls(tmp_path) == 1 and quiet_clock == []
    assert m["stop"]["reason"] == "quota_exhausted" and m["stop"]["scope"] == "daily"
    assert m["stop"]["after_runs"] == 1 and m["finished"] is True and m["interrupted"] is False
    assert m["counts"]["rate_limited"] == 1 and m["counts"]["done"] == 0 and m["counts"]["not_run_quota"] == 4
    assert not list(out.glob("*/*/*/*.attempt*.jsonl"))  # nothing was retired for a retry
    assert "not_run_quota=4" in capsys.readouterr().out


def test_exhausted_text_names_a_monthly_cap(tmp_path, monkeypatch):
    all_rate_limited(monkeypatch, tmp_path, GATEWAY_429.replace("daily", "monthly"))
    rc, out = run_a(tmp_path, limit=3)
    assert rc == 75 and manifest(out)["stop"]["scope"] == "monthly"


def test_quota_text_reader():
    assert runner.quota_scope({"is_error": True, "api_error_status": 429, "result": GATEWAY_429}) == "daily"
    assert runner.quota_scope({"is_error": True, "result": GATEWAY_429.replace("daily", "monthly")}) == "monthly"
    assert runner.quota_scope({"is_error": True, "api_error_status": 429, "result": GATEWAY_429_EXHAUSTED}) == "daily"
    # a wait the backoff cannot cover is a stop, whatever the wording
    long_wait = "API Error: (429) Rate limit exceeded. Retry after 3600 seconds."
    assert runner.quota_scope({"is_error": True, "api_error_status": 429, "result": long_wait}) == "unknown"
    short_wait = "API Error: (429) Rate limit exceeded. Retry after 30 seconds."
    assert runner.quota_scope({"is_error": True, "api_error_status": 429, "result": short_wait}) is None
    # exhausted, but the text does not say which cap
    assert runner.quota_scope({"is_error": True, "result": "API Error: (429) rate limit exhausted"}) == "unknown"
    # an ordinary 429, a result that is not an error, and a text without the sentence are not a stop
    assert runner.quota_scope({"is_error": True, "api_error_status": 429, "result": GENERIC_429}) is None
    assert runner.quota_scope({"is_error": False, "result": GATEWAY_429}) is None
    assert runner.quota_scope({"is_error": True, "api_error_status": 500, "result": "boom"}) is None


# ------------------------------------------------------------------ N rate-limited runs in a row
def test_three_rate_limited_runs_in_a_row_stop_the_run(tmp_path, monkeypatch, quiet_clock, capsys):
    all_rate_limited(monkeypatch, tmp_path)
    rc, out = run_a(tmp_path, limit=5)
    m = manifest(out)
    assert rc == 75 and calls(tmp_path) == 3 and quiet_clock == []
    assert m["stop"] == {"reason": "quota_exhausted", "scope": None, "after_runs": 3,
                         "run_id": m["stop"]["run_id"]} and m["stop"]["run_id"]
    assert m["counts"]["rate_limited"] == 3 and m["counts"]["done"] == 0 and m["counts"]["not_run_quota"] == 2
    assert "rate_limited=3" in capsys.readouterr().out


def test_stop_after_is_set_by_the_environment(tmp_path, monkeypatch):
    all_rate_limited(monkeypatch, tmp_path)
    monkeypatch.setenv("TSBENCH_429_STOP_AFTER", "2")
    rc, out = run_a(tmp_path, limit=5)
    assert rc == 75 and calls(tmp_path) == 2 and manifest(out)["counts"]["not_run_quota"] == 3
    assert runner.max_429_in_a_row({}) == 3 and runner.max_429_in_a_row({"TSBENCH_429_STOP_AFTER": "x"}) == 3
    assert runner.max_429_in_a_row({"TSBENCH_429_STOP_AFTER": "5"}) == 5


def test_three_rate_limited_runs_out_of_three_are_counted_as_rate_limited_not_done(tmp_path, monkeypatch):
    all_rate_limited(monkeypatch, tmp_path)
    rc, out = run_a(tmp_path, limit=3)
    c = manifest(out)["counts"]
    assert rc == 75 and (c["done"], c["rate_limited"], c["not_run_quota"]) == (0, 3, 0)
    readme = (out / "README.md").read_text(encoding="utf-8")
    assert "rate limited (HTTP 429, not answered): 3" in readme and "state: stopped by the quota" in readme


def test_a_429_between_successes_does_not_stop(tmp_path, monkeypatch):
    follow_pattern(monkeypatch, [True, False, True, True, False, True])  # never three in a row
    rc, out = run_a(tmp_path, limit=6)
    m = manifest(out)
    assert rc == 0 and m["stop"] is None
    assert (m["counts"]["done"], m["counts"]["rate_limited"], m["counts"]["not_run_quota"]) == (2, 4, 0)


def test_the_count_starts_again_after_a_success(tmp_path, monkeypatch):
    follow_pattern(monkeypatch, [True, True, False, True, True, True, True])
    rc, out = run_a(tmp_path, limit=7)
    m = manifest(out)
    assert rc == 75 and m["stop"]["after_runs"] == 3 and m["counts"]["not_run_quota"] == 1
    assert (m["counts"]["done"], m["counts"]["rate_limited"]) == (1, 5)


def test_a_run_set_in_which_every_run_was_rate_limited_does_not_exit_0(tmp_path, monkeypatch):
    """Two 429 results are below the stop, but nothing was answered: the exit code must not say success."""
    all_rate_limited(monkeypatch, tmp_path)
    rc, out = run_a(tmp_path, limit=2)
    m = manifest(out)
    assert rc == 75 and m["stop"] is None and m["counts"]["rate_limited"] == 2 and m["counts"]["done"] == 0


def test_stop_after_zero_switches_the_stop_off(tmp_path, monkeypatch):
    all_rate_limited(monkeypatch, tmp_path)
    monkeypatch.setenv("TSBENCH_429_STOP_AFTER", "0")
    rc, out = run_a(tmp_path, limit=5)
    m = manifest(out)
    assert calls(tmp_path) == 5 and m["stop"] is None and m["counts"]["rate_limited"] == 5


def test_resume_after_a_quota_stop_runs_the_rest(tmp_path, monkeypatch):
    all_rate_limited(monkeypatch, tmp_path)
    rc, out = run_a(tmp_path, limit=5)
    assert rc == 75
    monkeypatch.delenv("FAKE_429_FIRST")
    rc, out = run_a(tmp_path, limit=5, extra=("--resume",), out=out)
    c = manifest(out)["counts"]
    assert rc == 0 and c["done"] == 5 and c["rate_limited"] == 0 and c["skipped"] == 0 and manifest(out)["stop"] is None


# ------------------------------------------------------------------ a retired attempt is labelled by the same rule
def write_result(path: pathlib.Path, **kw) -> pathlib.Path:
    ev = {"type": "result", "is_error": False, "total_cost_usd": 0, "result": "", **kw}
    path.write_text(json.dumps(ev) + "\n", encoding="utf-8")
    return path


def test_retire_labels_rate_limited_only_for_an_error_result(tmp_path):
    answer = write_result(tmp_path / "a-k1.jsonl", result="Mind the rate limit (429) of the API in production.")
    assert runner.retire_earlier_attempt(answer)["reason"] == "result"  # an answer that mentions it is an answer
    real = write_result(tmp_path / "b-k1.jsonl", is_error=True, api_error_status=429, result=GENERIC_429)
    assert runner.retire_earlier_attempt(real)["reason"] == "rate_limited"
    plain = write_result(tmp_path / "c-k1.jsonl", is_error=True, result="the tool crashed")
    assert runner.retire_earlier_attempt(plain)["reason"] == "error_zero_cost"


def _earlier_attempt(tmp_path: pathlib.Path) -> pathlib.Path:
    """A killed run: its transcript, its sidecar and one image of the attempt."""
    tp = tmp_path / "t-k1.jsonl"
    tp.write_text('{"type":"system","subtype":"init"}\n', encoding="utf-8")
    tp.with_name("t-k1.meta.json").write_text('{"argv": ["old"], "wall_time_s": 899}\n', encoding="utf-8")
    art = tp.with_name("t-k1.artifacts")
    art.mkdir()
    (art / "fig1.png").write_bytes(b"old image")
    return tp


def test_retire_sets_the_sidecar_and_the_images_of_the_earlier_attempt_aside_too(tmp_path):
    tp = _earlier_attempt(tmp_path)
    assert runner.retire_earlier_attempt(tp)["attempt"] == 1
    assert not any(tp.with_name(n).exists() for n in ("t-k1.jsonl", "t-k1.meta.json", "t-k1.artifacts"))
    assert (tmp_path / "t-k1.attempt1.jsonl").exists()
    assert json.loads((tmp_path / "t-k1.attempt1.meta.json").read_text(encoding="utf-8"))["argv"] == ["old"]
    assert (tmp_path / "t-k1.attempt1.artifacts" / "fig1.png").read_bytes() == b"old image"
    # a second retirement of the same run takes the next number and never overwrites the first
    tp = _earlier_attempt(tmp_path)
    assert runner.retire_earlier_attempt(tp)["attempt"] == 2
    assert (tmp_path / "t-k1.attempt1.artifacts" / "fig1.png").exists()
    assert (tmp_path / "t-k1.attempt2.artifacts" / "fig1.png").exists()


def test_a_429_retry_does_not_leave_the_images_of_the_limited_attempt_in_the_run(tmp_path, monkeypatch):
    monkeypatch.setenv("TSBENCH_429_MAX_RETRIES", "1")
    tp = tmp_path / "t-k1.jsonl"
    seen = []

    def execute(argv, prompt, env, transcript, *a, **kw):
        art = runner.artifacts_dir_of(pathlib.Path(transcript))
        seen.append(sorted(p.name for p in art.iterdir()) if art.exists() else [])
        if len(seen) == 1:
            art.mkdir()
            (art / "fig1.png").write_bytes(b"limited attempt")
            return limited_outcome(pathlib.Path(transcript))
        (art.mkdir(), (art / "diagram.png").write_bytes(b"final"))
        return runner.Outcome(events=[], init=None, mismatches=[], result={"type": "result", "is_error": False},
                              exit_code=0, wall_s=0.0, stderr_tail="", timed_out=False, init_aborted=False)

    monkeypatch.setattr(runner, "execute", execute)
    outcome, retries = runner.execute_with_retries([], "p", {}, tp, conditions.get("A"), "m", timeout_s=1)
    assert len(retries) == 1 and seen == [[], []]  # the second attempt starts with an empty images folder
    assert sorted(p.name for p in runner.artifacts_dir_of(tp).iterdir()) == ["diagram.png"]
    assert (tmp_path / "t-k1.attempt1.artifacts" / "fig1.png").read_bytes() == b"limited attempt"


# ------------------------------------------------------------------ a crash is not a finished run set
def crash_on_second_call(monkeypatch, exc):
    real = runner.execute
    n = itertools.count(1)

    def execute(argv, prompt, env, transcript, *a, **kw):
        if next(n) == 2:
            raise exc
        return real(argv, prompt, env, transcript, *a, **kw)

    monkeypatch.setattr(runner, "execute", execute)


def test_an_exception_in_execute_leaves_the_manifest_unfinished_and_is_re_raised(tmp_path, monkeypatch):
    boom = RuntimeError("boom in run 2")
    crash_on_second_call(monkeypatch, boom)
    out = tmp_path / "runs"
    with pytest.raises(RuntimeError) as info:
        run_a(tmp_path, limit=3, out=out)
    assert info.value is boom
    m = manifest(out)
    assert m["finished"] is False and m["interrupted"] is False and m["counts"]["done"] == 1
    readme = (out / "README.md").read_text(encoding="utf-8")
    assert "state: stopped by an error" in readme and "state: finished" not in readme


def test_a_failing_readme_does_not_hide_the_original_exception(tmp_path, monkeypatch):
    crash_on_second_call(monkeypatch, RuntimeError("boom in run 2"))
    real = runner.inputs_mod.write_readme

    def write_readme(*a, running=False, **kw):
        if not running:
            raise OSError("disk full")
        return real(*a, running=running, **kw)

    monkeypatch.setattr(runner.inputs_mod, "write_readme", write_readme)
    with pytest.raises(RuntimeError, match="boom in run 2"):
        run_a(tmp_path, limit=3)
    assert manifest(tmp_path / "runs")["finished"] is False


def test_a_failing_readme_after_a_good_run_is_still_an_error(tmp_path, monkeypatch):
    def write_readme(*a, running=False, **kw):
        if not running:
            raise OSError("disk full")

    monkeypatch.setattr(runner.inputs_mod, "write_readme", write_readme)
    with pytest.raises(OSError, match="disk full"):
        run_a(tmp_path, limit=1)


# ------------------------------------------------------------------ a binary that does not start
def test_a_binary_that_does_not_start_gives_an_outcome_and_leaves_no_temp_dir(tmp_path, monkeypatch):
    tmp = tmp_path / "tmp"
    tmp.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(tmp))
    out = runner.execute([str(tmp_path / "no-such-claude")], "prompt", {"PATH": "/usr/bin"}, tmp_path / "t.jsonl",
                         conditions.get("A"), "m", timeout_s=30)
    assert out.result is None and out.exit_code is None and out.spawn_failed and not out.timed_out
    assert not out.init_aborted and "no-such-claude" in out.stderr_tail
    assert list(tmp.iterdir()) == []  # neither tsbench-run-* nor a stderr file is left


def test_the_runner_records_a_binary_that_does_not_start_and_goes_on(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "FAKE_ARGV", [str(tmp_path / "no-such-claude")])
    rc, out = run_a(tmp_path, limit=2, extra=("--per-call-usd", "1"))
    metas = sorted(out.glob("*/*/*/*.meta.json"))
    assert rc == runner.EX_TEMPFAIL and len(metas) == 2  # it goes on (2 < 3 in a row), but nothing was answered
    meta = json.loads(metas[0].read_text(encoding="utf-8"))
    assert "no_result_event" in meta["flags"] and meta["cost_usd"] == 0 and meta["exit_code"] is None
    assert manifest(out)["total_cost_usd"] == 0  # no process, no API request, so the per-call cap is not booked


# ------------------------------------------------------------------ a quota stop does not hide a failure
def test_an_aborted_cell_wins_over_the_quota_stop(tmp_path, monkeypatch):
    """Waiting for the reset cannot fix an init mismatch: exit 1, not 75, although the quota also stopped the run."""
    def execute(argv, prompt, env, transcript, cond, *a, **kw):
        if cond.key == "A":
            return runner.Outcome(events=[], init=None, mismatches=["wrong model"], result=None, exit_code=None,
                                  wall_s=0.0, stderr_tail="", timed_out=False, init_aborted=True)
        return limited_outcome(pathlib.Path(transcript))

    monkeypatch.setattr(runner, "execute", execute)
    rc, out = run_a(tmp_path, limit=5, extra=("--conditions", "A,C"))
    m = manifest(out)
    assert m["aborted_cells"] and m["stop"]["reason"] == "quota_exhausted"
    assert rc == 1


def test_the_stop_after_runs_in_a_row_names_no_cap_and_every_line_is_flushed(tmp_path, monkeypatch, capsys):
    all_rate_limited(monkeypatch, tmp_path)
    flushes: list = []

    def spy(*args, **kw):
        flushes.append(kw.get("flush"))
        print(*args, **kw)

    monkeypatch.setattr(runner, "print", spy, raising=False)
    rc, _ = run_a(tmp_path, limit=4)
    assert rc == 75 and flushes and all(f is True for f in flushes)
    assert ("quota used up (3 run(s) in a row ended in HTTP 429); stopping. Wait for the reset, then continue with "
            "--resume\n") in capsys.readouterr().err


# ------------------------------------------------------------------ a stop on other API errors than HTTP 429
def api_error_outcome(transcript: pathlib.Path, status=401) -> runner.Outcome:
    """A run that ended in an API error that is not a rate limit: an expired token, an unserved model, a 5xx."""
    res = {"type": "result", "subtype": "success", "is_error": True, "api_error_status": status,
           "result": f"API Error: {status} Unauthorized", "total_cost_usd": 0, "permission_denials": [],
           "terminal_reason": "api_error"}
    transcript.parent.mkdir(parents=True, exist_ok=True)
    transcript.write_text(json.dumps(res) + "\n", encoding="utf-8")
    return runner.Outcome(events=[res], init=None, mismatches=[], result=res, exit_code=0, wall_s=0.0,
                          stderr_tail="", timed_out=False, init_aborted=False)


def no_result_outcome(transcript: pathlib.Path) -> runner.Outcome:
    transcript.parent.mkdir(parents=True, exist_ok=True)
    transcript.write_text("", encoding="utf-8")
    return runner.Outcome(events=[], init=None, mismatches=[], result=None, exit_code=None, wall_s=900.0,
                          stderr_tail="", timed_out=True, init_aborted=False)


def follow_failures(monkeypatch, pattern, failure=api_error_outcome):
    """The n-th call to `execute` fails with `failure` when pattern[n] is true; the others run the fake claude."""
    real = runner.execute
    n = itertools.count()
    seen: list[int] = []

    def execute(argv, prompt, env, transcript, *a, **kw):
        i = next(n)
        seen.append(i)
        if pattern[i]:
            return failure(pathlib.Path(transcript))
        return real(argv, prompt, env, transcript, *a, **kw)

    monkeypatch.setattr(runner, "execute", execute)
    return seen


def test_three_api_errors_in_a_row_stop_the_run_and_the_exit_code_says_so(tmp_path, monkeypatch, capsys):
    """An expired token or a 5xx outage makes every remaining run end in an API error: do not run the whole plan."""
    calls_made = follow_failures(monkeypatch, [True] * 10)
    rc, out = run_a(tmp_path, limit=10)
    m = manifest(out)
    assert rc == runner.EX_TEMPFAIL and len(calls_made) == 3
    assert m["stop"] == {"reason": "api_errors", "scope": None, "after_runs": 3, "run_id": m["stop"]["run_id"]}
    assert m["counts"]["not_run_api_errors"] == 7 and m["finished"] is True
    err = capsys.readouterr().err
    assert "3 run(s) in a row ended in an API error or without a result" in err and "--resume" in err


def test_runs_without_a_result_stop_the_run_too(tmp_path, monkeypatch):
    """Hung calls: each burns the wall limit and ends without a result event."""
    calls_made = follow_failures(monkeypatch, [True] * 10, failure=no_result_outcome)
    rc, out = run_a(tmp_path, limit=10)
    assert rc == runner.EX_TEMPFAIL and len(calls_made) == 3
    assert manifest(out)["stop"]["reason"] == "api_errors"


def test_an_answer_between_api_errors_starts_the_count_again(tmp_path, monkeypatch):
    calls_made = follow_failures(monkeypatch, [True, True, False, True, True, False])
    rc, out = run_a(tmp_path, limit=6)
    m = manifest(out)
    assert rc == 0 and len(calls_made) == 6 and m["stop"] is None and "not_run_api_errors" not in m["counts"]


def test_a_429_between_api_errors_neither_counts_nor_resets(tmp_path, monkeypatch):
    real = runner.execute
    n = itertools.count()

    def execute(argv, prompt, env, transcript, *a, **kw):
        i = next(n)
        if i == 1:
            return limited_outcome(pathlib.Path(transcript))
        if i in (0, 2, 3):
            return api_error_outcome(pathlib.Path(transcript))
        return real(argv, prompt, env, transcript, *a, **kw)

    monkeypatch.setattr(runner, "execute", execute)
    rc, out = run_a(tmp_path, limit=6)
    m = manifest(out)
    assert rc == runner.EX_TEMPFAIL and m["stop"]["reason"] == "api_errors" and m["stop"]["after_runs"] == 3
    assert m["counts"]["rate_limited"] == 1


def test_a_run_set_in_which_every_run_ended_in_an_api_error_does_not_exit_0(tmp_path, monkeypatch):
    """Two failures are below the stop, but nothing was answered: the exit code must not say success."""
    follow_failures(monkeypatch, [True, True])
    rc, out = run_a(tmp_path, limit=2)
    m = manifest(out)
    assert rc == runner.EX_TEMPFAIL and m["stop"] is None and m["counts"]["done"] == 2


def test_the_api_error_stop_is_set_by_the_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("TSBENCH_API_ERROR_STOP_AFTER", "2")
    calls_made = follow_failures(monkeypatch, [True] * 10)
    rc, out = run_a(tmp_path, limit=10)
    assert rc == runner.EX_TEMPFAIL and len(calls_made) == 2 and manifest(out)["stop"]["after_runs"] == 2
    monkeypatch.setenv("TSBENCH_API_ERROR_STOP_AFTER", "0")  # 0 switches the stop off
    calls_made = follow_failures(monkeypatch, [True] * 5)
    rc, out = run_a(tmp_path, limit=5, out=tmp_path / "runs-off")
    assert rc == runner.EX_TEMPFAIL and len(calls_made) == 5 and manifest(out)["stop"] is None


def test_resume_after_an_api_error_stop_runs_the_rest(tmp_path, monkeypatch):
    follow_failures(monkeypatch, [True, True, True] + [False] * 7)
    rc, out = run_a(tmp_path, limit=5)
    assert rc == runner.EX_TEMPFAIL
    monkeypatch.undo()
    monkeypatch.setenv("TSBENCH_429_MAX_RETRIES", "0")
    rc, out = run_a(tmp_path, limit=5, extra=("--resume",))
    m = manifest(out)
    assert rc == 0 and m["stop"] is None and m["counts"]["done"] == 5


def test_resume_after_a_hung_call_stop_keeps_the_timed_out_runs_and_runs_the_rest(tmp_path, monkeypatch):
    """A run that hit the wall limit is an outcome: `--resume` does not sample it again, only the unrun ones."""
    follow_failures(monkeypatch, [True, True, True] + [False] * 7, failure=no_result_outcome)
    rc, out = run_a(tmp_path, limit=5)
    assert rc == runner.EX_TEMPFAIL and manifest(out)["stop"]["reason"] == "api_errors"
    hung = sorted(out.glob("*/A/medium/*.jsonl"))
    assert len(hung) == 3 and all(runner.transcript_status(h) == (True, 0.0) for h in hung)
    monkeypatch.undo()
    monkeypatch.setenv("TSBENCH_429_MAX_RETRIES", "0")
    rc, out = run_a(tmp_path, limit=5, extra=("--resume",))
    m = manifest(out)
    assert rc == 0 and m["stop"] is None and m["counts"]["done"] == 2
    assert all(h.read_text(encoding="utf-8") == "" for h in hung) and not list(out.glob("*/A/medium/*.attempt*"))
