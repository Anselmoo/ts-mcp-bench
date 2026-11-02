"""Tests for tsbench.run.sandbox_probe with a stub session and a stub model call: what run_probe hands to the runner,
the record it writes, the API error verdict, and the command line. No model call, no key, no subprocess.

The end-to-end probe tests against the fake claude are in test_runner.py.
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
from types import SimpleNamespace

import pytest

from tsbench import conditions
from tsbench.conditions import sandbox
from tsbench.run import runner, sandbox_probe

HOME = {"HOMECACHE": [".fake-cache"], "HOMESECRETS": [".fake-secret"]}  # not a real home: its script hash differs
API_ERROR = {"type": "result", "is_error": True, "api_error_status": 429, "result": "API Error: Request rejected (429)"}
OK_RESULT = {"type": "result", "is_error": False, "result": "done"}
PREFIX = "the probe call ended in an API error, so the sandbox was not tested: "


def ev(passed=True, markers=None, reasons=(), init_mismatches=(), escape_requested=False):
    return {"passed": passed, "markers": {"CTRL1": [0]} if markers is None else markers, "reasons": list(reasons),
            "init_mismatches": list(init_mismatches), "escape_requested": escape_requested}


def session(tmp_path, *, dry_run=False, full=True, gateway=True):
    """A stub session. `full=False` leaves out the optional parts: real_home, recorded_child_path and the B stack."""
    s = SimpleNamespace(claude_argv=["claude-bin"], settings_path=tmp_path / "settings.json", repo=tmp_path / "repo",
                        dry_run=dry_run, claude_version="9.9.9", gateway=gateway, settings_sha256="s" * 64,
                        b_stack={"digest": "d" * 64} if full else None,
                        child_env=lambda key: {"PATH": f"<{key}_VENV>/bin:/usr/bin", "CHILD": key})
    if full:
        s.real_home = tmp_path / "real-home"
        s.recorded_child_path = lambda key: f"<recorded {key}>"
    return s


@pytest.fixture
def calls(monkeypatch):
    """Replace the model call and the host checks; `calls` holds what run_probe passed and sets what comes back."""
    got = SimpleNamespace(ev=ev(), result=OK_RESULT, cost=0.03, not_tested=(), home_args=[], target_args=[])

    def build_argv(*args, **kwargs):
        got.build_argv = (args, kwargs)
        return ["claude-bin", "--argv"]

    def execute_with_retries(*args, **kwargs):
        got.execute = (args, kwargs)
        outcome = SimpleNamespace(events=[{"type": "system"}], result=got.result, cost_usd=got.cost, exit_code=7)
        return outcome, [{"wait_s": 1}]

    def evaluate_transcript(events, model, not_tested=()):
        got.evaluated = (events, model, not_tested)
        return got.ev

    monkeypatch.setattr(runner, "build_argv", build_argv)
    monkeypatch.setattr(runner, "execute_with_retries", execute_with_retries)
    monkeypatch.setattr(sandbox_probe, "evaluate_transcript", evaluate_transcript)
    monkeypatch.setattr(sandbox_probe, "existing_home_paths", lambda rh: got.home_args.append(rh) or HOME)
    monkeypatch.setattr(sandbox_probe, "missing_probe_targets", lambda repo: got.target_args.append(repo) or
                        got.not_tested)
    monkeypatch.setattr(sandbox_probe, "localhost_listening", lambda: True)
    return got


# ------------------------------------------------------------------ run_probe: what goes to the runner
def test_run_probe_hands_the_b_call_to_the_runner(tmp_path, calls):
    s = session(tmp_path, gateway=False)
    out = tmp_path / "out"
    sandbox_probe.run_probe(s, out, model="m-x")
    args, kwargs = calls.build_argv
    assert args == (["claude-bin"], conditions.get("B"), "m-x", sandbox.PROBE_EFFORT, sandbox.PROBE_BUDGET_USD)
    assert kwargs == {"system_prompt_file": runner.NEUTRAL_PROMPT, "settings_path": str(tmp_path / "settings.json"),
                      "mcp_config_path": None, "max_turns": sandbox.PROBE_MAX_TURNS}
    args, kwargs = calls.execute
    env = {"PATH": "<B_VENV>/bin:/usr/bin", "CHILD": "B", sandbox.PROBE_ENV_REPO: str(tmp_path / "repo"),
           sandbox.PROBE_ENV_HOME: str(tmp_path / "real-home")}
    assert args == (["claude-bin", "--argv"], sandbox.probe_prompt(HOME, ()), env, out / sandbox.PROBE_TRANSCRIPT,
                    conditions.get("B"), "m-x")
    assert kwargs == {"timeout_s": runner.WALL_TIMEOUT_S}
    assert calls.home_args == [tmp_path / "real-home"] and calls.target_args == [tmp_path / "repo"]
    assert calls.evaluated == ([{"type": "system"}], "m-x", ())


def test_run_probe_marks_a_dry_session_for_the_fake(tmp_path, calls):
    sandbox_probe.run_probe(session(tmp_path, dry_run=True), tmp_path / "out")
    assert calls.execute[0][2]["FAKE_SEED"] == "sandbox-probe"
    assert calls.build_argv[0][2] == sandbox.PROBE_MODEL


def test_run_probe_without_a_real_home_uses_the_default(tmp_path, calls):
    sandbox_probe.run_probe(session(tmp_path, full=False), tmp_path / "out")
    assert calls.home_args == [None]
    assert calls.execute[0][2][sandbox.PROBE_ENV_HOME] == str(pathlib.Path("~").expanduser())
    assert "FAKE_SEED" not in calls.execute[0][2]


@pytest.mark.parametrize("remaining,cap", [(None, sandbox.PROBE_BUDGET_USD), (0.04, 0.04), (-1.0, 0.0),
                                           (5.0, sandbox.PROBE_BUDGET_USD)])
def test_run_probe_caps_the_call_at_the_remaining_budget(tmp_path, calls, remaining, cap):
    calls.cost = None  # no cost reported: the record counts the whole cap
    rec = sandbox_probe.run_probe(session(tmp_path, gateway=False), tmp_path / "out", remaining_usd=remaining)
    assert calls.build_argv[0][4] == cap
    assert rec["cost_usd"] == cap and rec["cost_unknown"] is True


@pytest.mark.parametrize("remaining", [None, 0.04, 5.0])
def test_run_probe_on_a_gateway_gives_the_call_no_cap(tmp_path, calls, remaining):
    """A gateway call is not counted in USD; a cap would cut it at Claude Code's price estimate and make B not
    evaluable."""
    sandbox_probe.run_probe(session(tmp_path, gateway=True), tmp_path / "out", remaining_usd=remaining)
    assert calls.build_argv[0][4] is None


# ------------------------------------------------------------------ run_probe: the record
def test_run_probe_writes_the_whole_record(tmp_path, calls):
    out = tmp_path / "out"
    calls.ev = ev(markers={"PIP": [1], "CTRL1": [0]})
    rec = sandbox_probe.run_probe(session(tmp_path), out, model="m-x")
    stamp = rec.pop("timestamp_utc")
    assert rec == {
        "method": "builtin", "passed": True, "not_evaluable": None, "retries": 1, "reasons": [],
        "markers": {"PIP": [1], "CTRL1": [0]}, "init_mismatches": [], "escape_requested": False,
        "cost_usd": 0.03, "cost_unknown": False, "claude_version": "9.9.9", "model": "m-x", "auth_mode": "gateway",
        "settings_sha256": "s" * 64, "probe_script_sha256": sandbox.probe_script_sha256(HOME, ()),
        "targets_not_tested": [], "probe_script_template_sha256": sandbox.probe_script_template_sha256(),
        "home_paths_tested": HOME, "localhost_listening": True, "child_path": "<recorded B>",
        "b_stack_sha256": "d" * 64, "transcript": "_sandbox_probe/transcript.jsonl", "exit_code": 7, "fake": False,
    }
    when = dt.datetime.fromisoformat(stamp)
    assert when.utcoffset() == dt.timedelta(0) and when.microsecond == 0
    rec["timestamp_utc"] = stamp
    text = (out / sandbox.PROBE_FILENAME).read_text(encoding="utf-8")
    assert text == json.dumps(rec, indent=2, sort_keys=True) + "\n"


def test_run_probe_record_without_the_optional_session_parts(tmp_path, calls):
    rec = sandbox_probe.run_probe(session(tmp_path, dry_run=True, full=False), tmp_path / "out")
    assert rec["child_path"] is None and rec["b_stack_sha256"] is None and rec["fake"] is True


def test_run_probe_with_an_api_error_and_a_missing_target_fails(tmp_path, calls):
    calls.result, calls.not_tested = API_ERROR, ("VENV",)
    calls.ev = ev(passed=False, reasons=["VENV not tested"])
    rec = sandbox_probe.run_probe(session(tmp_path), tmp_path / "out")
    assert rec["passed"] is False and rec["not_evaluable"] is None and rec["reasons"] == ["VENV not tested"]
    assert rec["targets_not_tested"] == ["VENV"]


def test_run_probe_with_only_an_api_error_is_not_evaluable(tmp_path, calls):
    calls.result = API_ERROR
    calls.ev = ev(passed=False, markers={}, reasons=["CTRL1 missing"])
    rec = sandbox_probe.run_probe(session(tmp_path), tmp_path / "out")
    assert rec["passed"] is None and rec["not_evaluable"] == "api_error"
    assert rec["reasons"] == [PREFIX + "API Error: Request rejected (429)"]


# ------------------------------------------------------------------ the API error verdict and reason
def test_api_error_verdict_without_an_api_error_is_the_evaluation():
    assert sandbox_probe.api_error_verdict(ev(passed=False), OK_RESULT) == (False, None)
    assert sandbox_probe.api_error_verdict(ev(passed=True), None) == (True, None)


def test_api_error_with_no_markers_is_not_evaluable():
    assert sandbox_probe.api_error_verdict(ev(passed=False, markers={}), API_ERROR) == (None, "api_error")


@pytest.mark.parametrize("kw,not_tested", [
    ({"escape_requested": True}, ()), ({"init_mismatches": ["model"]}, ()), ({}, ("VENV",)),
    ({"markers": {"NET": [0]}}, ()), ({"markers": {"KEYENV": [1]}}, ()),
])
def test_api_error_does_not_hide_a_failure_that_arrived(kw, not_tested):
    assert sandbox_probe.api_error_verdict(ev(passed=False, **kw), API_ERROR, not_tested) == (False, None)


def test_a_probe_model_that_never_ran_the_script_is_not_evaluable():
    # no marker at all and nothing wrong that arrived: the model did not run the script, the sandbox was not tested
    assert sandbox_probe.api_error_verdict(ev(passed=False, markers={}), OK_RESULT) == (None, "no_markers")
    assert sandbox_probe.api_error_verdict(ev(passed=False, markers={}), None) == (None, "no_markers")


@pytest.mark.parametrize("kw,not_tested", [
    ({"escape_requested": True}, ()), ({"init_mismatches": ["model"]}, ()), ({}, ("VENV",)),
    ({"markers": {"CTRL1": [0]}}, ()), ({"markers": {"KEYENV": [1]}}, ()),
])
def test_missing_markers_do_not_hide_a_failure_that_arrived(kw, not_tested):
    assert sandbox_probe.api_error_verdict(ev(passed=False, **{"markers": {}, **kw}), OK_RESULT, not_tested) == (
        False, None)


def test_run_probe_with_a_model_that_ran_nothing_is_not_evaluable_and_says_why(tmp_path, calls):
    calls.ev = ev(passed=False, markers={}, reasons=["CTRL1 missing: Bash did not run the script"])
    rec = sandbox_probe.run_probe(session(tmp_path), tmp_path / "out", model="small-model")
    assert rec["passed"] is None and rec["not_evaluable"] == "no_markers" and rec["model"] == "small-model"
    assert rec["reasons"] == [sandbox_probe.NO_MARKERS_TEXT.format(model="small-model")]


@pytest.mark.parametrize("result", [None, {"result": ""}, {"is_error": True}])
def test_api_error_reason_without_a_message(result):
    assert sandbox_probe.api_error_reason(result, {}) == PREFIX + "no message"


# ------------------------------------------------------------------ the command line
@pytest.fixture
def cli(monkeypatch):
    """Stub Session.create and run_probe; `cli.rec` is the record run_probe returns."""
    got = SimpleNamespace(rec={"passed": True, "cost_usd": 0.0123, "reasons": ["first", "second"],
                               "markers": {"b": [1], "a": [0]}}, closed=False)

    def create(**kwargs):
        got.create = kwargs
        return SimpleNamespace(close=lambda: setattr(got, "closed", True))

    def run_probe(s, out, **kwargs):
        got.run = (out, kwargs)
        return got.rec

    monkeypatch.setattr(runner.Session, "create", create)
    monkeypatch.setattr(sandbox_probe, "run_probe", run_probe)
    return got


def test_cli_passes_every_option_on(tmp_path, cli):
    out = tmp_path / "p"
    assert sandbox_probe.main(["--probe", "--out", str(out), "--gateway", "--b-venv", "/venv-b", "--model", "m-x",
                               "--fake"]) == 0
    assert cli.create == {"dry_run": True, "gateway": True, "b_venv": "/venv-b"}
    assert cli.run == (out.resolve(), {"model": "m-x"}) and cli.closed


def test_cli_defaults(tmp_path, cli):
    sandbox_probe.main(["--probe", "--out", str(tmp_path / "p")])
    assert cli.create == {"dry_run": False, "gateway": False, "b_venv": None}
    assert cli.run[1] == {"model": sandbox.PROBE_MODEL}


@pytest.mark.parametrize("passed,verdict,rc", [(True, "PASS", 0), (False, "FAIL", 1), (None, "NOT EVALUABLE", 75)])
def test_cli_prints_the_verdict_reasons_markers_and_record(tmp_path, cli, capsys, passed, verdict, rc):
    cli.rec["passed"] = passed
    out = tmp_path / "p"
    assert sandbox_probe.main(["--probe", "--out", str(out)]) == rc
    assert capsys.readouterr().out.splitlines() == [
        f"sandbox probe: {verdict} (cost USD 0.0123)", "  - first", "  - second",
        'markers: {"a": [0], "b": [1]}', f"record: {out / sandbox.PROBE_FILENAME}"]


@pytest.mark.parametrize("argv,message", [([], "error: give --probe or --settings-only"),
                                          (["--probe"], "error: --probe needs --out <dir>")])
def test_cli_usage_errors(cli, capsys, argv, message):
    with pytest.raises(SystemExit) as e:
        sandbox_probe.main(argv)
    assert e.value.code == 2
    assert capsys.readouterr().err.splitlines()[-1] == "tsbench env sandbox: " + message


def test_cli_help_names_the_command_and_every_option(monkeypatch, capsys):
    monkeypatch.setenv("COLUMNS", "200")  # one line per option
    with pytest.raises(SystemExit) as e:
        sandbox_probe.main(["--help"])
    assert e.value.code == 0
    text = capsys.readouterr().out
    doc = sandbox_probe.__doc__
    assert doc and text.startswith("usage: tsbench env sandbox ")
    assert "\n" + doc.splitlines()[0] + "\n" in text
    # option -> its help column, exactly
    columns = dict((line.strip() + "  ").split("  ", 1) for line in text.splitlines() if line.startswith("  --"))
    assert {k: v.strip() for k, v in columns.items()} == {
        "--probe": "run the sandbox probe (one real model call)",
        "--settings-only": "print the rendered sandbox settings and exit",
        "--out OUT": "directory for sandbox_probe.json (required with --probe)",
        "--model MODEL": "",
        "--gateway": "",
        "--b-venv B_VENV": "venv of condition B (default: see b_stack)",
        "--fake": "use the fake claude (tests; no network)",
    }
