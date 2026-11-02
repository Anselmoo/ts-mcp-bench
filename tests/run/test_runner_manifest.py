"""Exact checks of what one invocation of the runner writes and prints: the manifest, the sidecar, the console lines,
the sandbox check in real mode (with a stubbed check), interrupts and crashes. All runs use the fake claude."""

from __future__ import annotations

import datetime
import hashlib
import json
import pathlib
import re
import sys
from types import SimpleNamespace

import pytest

from tsbench import conditions
from tsbench import plan as plan_mod
from tsbench.conditions import sandbox
from tsbench.run import inputs, runner, sandbox_probe
from tsbench.tasks import load

HAIKU = "claude-haiku-5-5"
STAMP = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\+00:00$")
NOT_REQUESTED = {"method": "n/a (condition B not requested)", "reason": None, "container": None, "probe": None}


@pytest.fixture(autouse=True)
def fake_venv(monkeypatch, tmp_path_factory):
    d = tmp_path_factory.getbasetemp() / "fake-venv-B-manifest"
    (d / "bin").mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("TSBENCH_B_VENV", str(d))  # never the real venv-B
    return d


def dry(out, *, conds="A", k=1, limit=1, budget=10.0, extra=()):
    argv = ["--split", "pilot", "--models", HAIKU, "--conditions", conds, "--effort", "medium", "--k", str(k),
            "--budget-usd", str(budget), "--out", str(out), "--dry-run", "--limit", str(limit), *extra]
    return runner.main(argv)


def read(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def plan_runs(out: pathlib.Path) -> list[dict]:
    return plan_mod.load_plan(out / plan_mod.PLAN_NAME).runs


def lines(text: str) -> list[str]:
    return [ln for ln in text.splitlines() if ln.strip()]


# ------------------------------------------------------------------ one dry run, every field
MANIFEST_KEYS = {
    "schema", "finished", "interrupted", "git_commit", "git_dirty", "claude_version", "python_version",
    "tanabesugano_version", "host", "host_source", "platform", "sandbox", "start_time_utc", "end_time_utc", "args",
    "child_path", "sandbox_settings_sha256", "split", "models_requested", "conditions", "effort", "k", "tasks",
    "reported_models", "env_var_names", "counts", "aborted_cells", "flagged_runs", "total_cost_usd",
    "estimated_cost_usd", "budget_usd", "stopped_by_budget", "stop", "plan_id", "plan_sha256", "plan_file",
    "plan_sealed", "tasks_sha256", "pin_drift", "transcripts", "b_stack",
}
META_KEYS = {
    "run_id", "model", "condition", "effort", "task_id", "k", "argv", "prompt_via", "exit_code", "wall_time_s",
    "stderr_tail", "env_var_names", "sandbox_method", "retries", "earlier_attempt", "disallowed_tools", "max_turns",
    "flags", "flag_details", "init_mismatches", "reported_model", "cost_usd", "cost_unknown", "timed_out",
    "cell_aborted", "claude_version", "started_utc", "plan_id", "prompt_sha256", "system_prompt_sha256", "artifacts",
    "image_sha_match",
}


def test_dry_run_manifest_fields(tmp_path, capsys):
    out = tmp_path / "runs"
    assert dry(out, budget=7.5) == 0
    m = read(out / "MANIFEST.json")
    plan = plan_mod.load_plan(out / plan_mod.PLAN_NAME)
    (r,) = plan.runs
    tp = out / HAIKU / "A" / "medium" / f"{r['task_id']}-k1.jsonl"
    assert set(m) == MANIFEST_KEYS
    assert m["schema"] == 2 and m["finished"] is True and m["interrupted"] is False
    assert set(m["claude_version"]) == {"used", "fake", "real"}
    assert m["claude_version"]["used"] == "fake" and m["claude_version"]["fake"] == "fake-0"
    assert m["sandbox"] == NOT_REQUESTED and m["b_stack"] is None
    assert STAMP.match(m["start_time_utc"]) and STAMP.match(m["end_time_utc"])
    assert m["split"] == "pilot" and m["models_requested"] == [HAIKU] and m["conditions"] == ["A"]
    assert m["effort"] == "medium" and m["k"] == 1 and m["tasks"] == [r["task_id"]]
    assert m["reported_models"] == {HAIKU: {"A": [HAIKU]}}
    assert "FAKE_SEED" in m["env_var_names"] and m["env_var_names"] == sorted(m["env_var_names"])
    assert m["counts"] == {"planned": 1, "done": 1, "rate_limited": 0, "skipped": 0, "aborted": 0,
                           "not_run_sandbox": 0, "not_run_probe_not_evaluable": 0, "not_run_budget": 0,
                           "not_run_quota": 0}
    assert m["aborted_cells"] == [] and m["flagged_runs"] == [] and m["stop"] is None
    assert m["total_cost_usd"] == 0.0 and m["budget_usd"] == 7.5 and m["stopped_by_budget"] is False
    assert m["plan_id"] == plan.plan_id and m["plan_sha256"] == plan.sha256
    assert m["plan_file"] == "plan.jsonl" and m["plan_sealed"] is False
    assert m["tasks_sha256"] == plan.header["tasks_sha256"]
    assert m["transcripts"] == {r["run_id"]: hashlib.sha256(tp.read_bytes()).hexdigest()}
    assert m["args"]["out"] and m["args"]["dry_run"] is True and list(m["child_path"]) == ["A"]
    # the console: one line per run and the summary
    printed = lines(capsys.readouterr().out)
    assert printed[-2] == f"[1/1] {r['run_id']} cost=0.0000 spent=0.0000"
    assert printed[-1] == ("done=1 rate_limited=0 skipped=0 aborted=0 not_run_sandbox=0 "
                           "not_run_probe_not_evaluable=0 not_run_budget=0 not_run_quota=0 "
                           f"planned=1 cost=USD 0.0000 manifest={out / 'MANIFEST.json'}")


def test_dry_run_sidecar_fields(tmp_path):
    out = tmp_path / "runs"
    dry(out)
    (r,) = plan_runs(out)
    m = read(out / "MANIFEST.json")
    meta = read(out / HAIKU / "A" / "medium" / f"{r['task_id']}-k1.meta.json")
    assert set(meta) == META_KEYS
    assert (meta["run_id"], meta["model"], meta["condition"], meta["effort"], meta["task_id"], meta["k"]) == (
        r["run_id"], HAIKU, "A", "medium", r["task_id"], 1)
    assert meta["prompt_via"] == "stdin" and meta["exit_code"] == 0 and meta["stderr_tail"] == ""
    assert isinstance(meta["wall_time_s"], float) and meta["wall_time_s"] == round(meta["wall_time_s"], 3)
    assert meta["env_var_names"] == m["env_var_names"] and meta["sandbox_method"] == "n/a"
    assert meta["retries"] == [] and meta["earlier_attempt"] is None
    assert meta["disallowed_tools"] == r["disallowed_tools"] and meta["max_turns"] == r["max_turns"]
    assert meta["argv"][meta["argv"].index("--max-turns") + 1] == str(r["max_turns"])
    assert meta["flags"] == [] and meta["init_mismatches"] == [] and meta["reported_model"] == HAIKU
    assert meta["cost_usd"] == 0.0 and meta["cost_unknown"] is False and meta["timed_out"] is False
    assert meta["cell_aborted"] is False and STAMP.match(meta["started_utc"])
    assert meta["plan_id"] == m["plan_id"] and meta["prompt_sha256"] == r["prompt_sha256"]


def test_sidecar_flag_details_and_flag_line(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("FAKE_NO_RESULT", "1")
    out = tmp_path / "runs"
    dry(out)
    (r,) = plan_runs(out)
    meta = read(out / HAIKU / "A" / "medium" / f"{r['task_id']}-k1.meta.json")
    assert meta["flags"] == ["cost_unknown", "no_result_event"] and meta["cost_unknown"] is True
    assert isinstance(meta["flag_details"], dict)
    assert read(out / "MANIFEST.json")["flagged_runs"] == [{"run_id": r["run_id"],
                                                            "flags": ["cost_unknown", "no_result_event"]}]
    assert f"[1/1] {r['run_id']} cost=0.0000 spent=0.0000 flags=cost_unknown,no_result_event" in lines(
        capsys.readouterr().out)


def test_effort_and_counts_over_several_runs(tmp_path, capsys):
    out = tmp_path / "runs"
    assert dry(out, conds="A,C", k=2, limit=1) == 0
    m = read(out / "MANIFEST.json")
    assert m["k"] == 2 and m["conditions"] == ["A", "C"] and m["counts"]["done"] == 4
    assert len(m["transcripts"]) == 4
    progress = [ln for ln in lines(capsys.readouterr().out) if ln.startswith("[")]
    assert [p.split()[0] for p in progress] == ["[1/4]", "[2/4]", "[3/4]", "[4/4]"]


@pytest.mark.parametrize("status,expected", [("", "no"), (" M x.py", "yes"), (None, None)])
def test_git_dirty_is_recorded(tmp_path, monkeypatch, status, expected):
    monkeypatch.setattr(runner, "git_output", lambda repo, *args: "abc123" if args[0] == "rev-parse" else status)
    out = tmp_path / "runs"
    dry(out)
    m = read(out / "MANIFEST.json")
    assert m["git_commit"] == "abc123" and m["git_dirty"] == expected


# ------------------------------------------------------------------ earlier files in --out
def test_an_earlier_manifest_is_kept_under_a_stamped_name(tmp_path):
    out = tmp_path / "runs"
    dry(out)
    first = (out / "MANIFEST.json").read_text(encoding="utf-8")
    dry(out, extra=("--resume",))
    (prev,) = out.glob("MANIFEST.prev-*.json")
    assert re.fullmatch(r"MANIFEST\.prev-\d{8}T\d{12}Z\.json", prev.name)
    assert prev.read_text(encoding="utf-8") == first


def test_an_earlier_plan_is_kept_under_its_id(tmp_path):
    out = tmp_path / "runs"
    dry(out, limit=1)
    old_id = plan_mod.load_plan(out / plan_mod.PLAN_NAME).plan_id
    dry(out, limit=2, extra=("--resume",))  # the flags form may extend the matrix of a run set it resumes
    assert [p.name for p in out.glob("plan.prev-*.jsonl")] == [f"plan.prev-{old_id[:16]}.jsonl"]
    assert len(plan_runs(out)) == 2


def test_an_unreadable_earlier_plan_is_kept_as_unknown(tmp_path):
    out = tmp_path / "runs"
    out.mkdir(parents=True)
    (out / plan_mod.PLAN_NAME).write_text("not json\n", encoding="utf-8")
    dry(out)
    assert (out / "plan.prev-unknown.jsonl").read_text(encoding="utf-8") == "not json\n"


def test_a_nested_out_folder_is_created(tmp_path):
    out = tmp_path / "a" / "b" / "runs"
    assert dry(out) == 0 and (out / "MANIFEST.json").exists()


def plan_resume_setup(tmp_path, manifest_text):
    """A finished run whose plan file is gone, so --plan --resume reads the plan_id from the manifest."""
    out = tmp_path / "runs"
    dry(out)
    plan_file = tmp_path / "plan.jsonl"
    plan_file.write_bytes((out / plan_mod.PLAN_NAME).read_bytes())
    (out / plan_mod.PLAN_NAME).unlink()
    (out / "MANIFEST.json").write_text(manifest_text(read(out / "MANIFEST.json")), encoding="utf-8")
    return out, ["--plan", str(plan_file), "--out", str(out), "--resume", "--dry-run", "--budget-usd", "1"]


def test_plan_resume_compares_the_manifest_plan_id(tmp_path, capsys):
    out, argv = plan_resume_setup(tmp_path, lambda m: json.dumps(dict(m, plan_id="f" * 64)))
    plan_id = plan_mod.load_plan(argv[1]).plan_id
    capsys.readouterr()
    with pytest.raises(SystemExit) as e:
        runner.main(argv)
    assert e.value.code == 2
    expected = f"runner: --resume: {out} holds plan_id {'f' * 64}, this invocation has {plan_id}\n"
    assert capsys.readouterr().err == expected


def test_plan_resume_with_an_unreadable_manifest_goes_on(tmp_path):
    out, argv = plan_resume_setup(tmp_path, lambda m: "not json")
    assert runner.main(argv) == 0 and read(out / "MANIFEST.json")["counts"]["skipped"] == 1


# ------------------------------------------------------------------ stops and messages
def test_budget_message(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("FAKE_COST_USD", "0.7")
    dry(tmp_path / "runs", limit=3, budget=1.0)
    assert "budget reached (spent USD 1.4000 of 1.00); stopping cleanly" in lines(capsys.readouterr().out)


def test_quota_scope_stops_with_the_message(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(runner, "quota_scope", lambda result: "daily")
    out = tmp_path / "runs"
    rc = dry(out, limit=3)
    m = read(out / "MANIFEST.json")
    first = plan_runs(out)[0]["run_id"]
    assert rc == runner.EX_TEMPFAIL
    assert m["stop"] == {"reason": "quota_exhausted", "scope": "daily", "after_runs": 0, "run_id": first}
    assert m["counts"]["done"] == 1 and m["counts"]["not_run_quota"] == 2
    err = capsys.readouterr().err
    assert ("quota used up (0 run(s) in a row ended in HTTP 429, daily cap); stopping. "
            "Wait for the reset, then continue with --resume\n") in err


def test_abort_cell_message(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("FAKE_BAD_INIT", "1")
    out = tmp_path / "runs"
    assert dry(out, k=1, limit=2) == 1
    m = read(out / "MANIFEST.json")
    (cell,) = m["aborted_cells"]
    assert set(cell) == {"model", "condition", "effort", "first_run", "reasons"}
    assert cell["first_run"] == plan_runs(out)[0]["run_id"] and m["counts"]["aborted"] == 2
    err = capsys.readouterr().err
    assert f"ABORT CELL {HAIKU}/A/medium: {'; '.join(cell['reasons'])}\n" in err


def test_interrupt_writes_the_manifest_and_returns_130(tmp_path, monkeypatch, capsys):
    def interrupt(*a, **k):
        raise KeyboardInterrupt
    monkeypatch.setattr(runner, "execute_with_retries", interrupt)
    out = tmp_path / "runs"
    assert dry(out) == 130
    m = read(out / "MANIFEST.json")
    assert m["interrupted"] is True and m["finished"] is False
    assert capsys.readouterr().err.endswith("interrupted; manifest written\n")


def no_readme(*a, **k):
    raise OSError("disk full")


def test_a_crash_keeps_its_exception_when_the_readme_fails(tmp_path, monkeypatch, capsys):
    def crash(*a, **k):
        monkeypatch.setattr(inputs, "write_readme", no_readme)  # only the final README fails
        raise RuntimeError("boom")
    monkeypatch.setattr(runner, "execute_with_retries", crash)
    out = tmp_path / "runs"
    with pytest.raises(RuntimeError, match="boom"):
        dry(out)
    assert read(out / "MANIFEST.json")["finished"] is False
    assert capsys.readouterr().err.endswith("could not write the final manifest or README: disk full\n")


def test_a_readme_failure_without_a_crash_is_raised(tmp_path, monkeypatch):
    orig = runner.execute_with_retries

    def run_then_break_readme(*a, **k):
        monkeypatch.setattr(inputs, "write_readme", no_readme)
        return orig(*a, **k)
    monkeypatch.setattr(runner, "execute_with_retries", run_then_break_readme)
    with pytest.raises(OSError, match="disk full"):
        dry(tmp_path / "runs")


# ------------------------------------------------------------------ the sandbox check in real mode (stubbed)
DIGEST = "d" * 64


@pytest.fixture
def real_mode(monkeypatch, fake_venv):
    """Session.create hands out a fake-backed session the runner treats as real, with a known B stack digest."""
    orig = runner.Session.create.__func__
    sessions = []

    def create(cls, *, dry_run, gateway, parent_env=None, repo=runner.REPO_ROOT, **kw):
        s = orig(cls, dry_run=True, gateway=gateway, parent_env=parent_env, repo=repo, **kw)
        s.dry_run = False
        s.b_stack = {"digest": DIGEST, "bin": str(fake_venv / "bin")}
        sessions.append(s)
        return s

    monkeypatch.setattr(runner.Session, "create", classmethod(create))
    monkeypatch.setattr(sandbox, "detect_container", lambda: None)
    return sessions


def real(tmp_path, conds="A,B", limit=1, budget=5.0):
    return runner.main(["--split", "pilot", "--models", HAIKU, "--conditions", conds, "--effort", "medium",
                        "--k", "1", "--limit", str(limit), "--budget-usd", str(budget),
                        "--out", str(tmp_path / "runs")])


def stub_check(monkeypatch, rec, *, reusable=None):
    """run_probe returns `rec`; load_reusable_probe returns `reusable`. Both record their arguments."""
    calls: dict[str, list] = {"run": [], "load": []}

    def run_probe(session, out, *, model, remaining_usd):
        calls["run"].append((session, out, model, remaining_usd))
        return rec

    def load(out, version, settings_hash, digest, *, auth):
        calls["load"].append((out, version, settings_hash, digest, auth))
        return reusable

    monkeypatch.setattr(sandbox_probe, "run_probe", run_probe)
    monkeypatch.setattr(sandbox, "load_reusable_probe", load)
    return calls


def test_sandbox_check_runs_once_with_the_rest_of_the_budget(tmp_path, real_mode, monkeypatch, capsys):
    monkeypatch.setenv("FAKE_COST_USD", "0.5")
    rec = {"passed": True, "reasons": [], "cost_usd": 0.25}
    calls = stub_check(monkeypatch, rec)
    assert real(tmp_path, limit=2) == 0
    out = tmp_path / "runs"
    (s,) = real_mode
    assert [(c[0], c[1], c[2], c[3]) for c in calls["run"]] == [(s, out, sandbox.PROBE_MODEL, 4.5)]
    expected_load = (out, s.claude_version, s.settings_sha256, DIGEST, "direct")
    assert calls["load"] == [expected_load, expected_load]  # at the start and before the first B run
    m = read(out / "MANIFEST.json")
    assert m["sandbox"] == {"method": "builtin", "reason": None, "container": None, "probe": rec}
    assert m["b_stack"]["digest"] == DIGEST
    assert m["counts"]["done"] == 4 and m["total_cost_usd"] == pytest.approx(2.25)
    b_meta = read(next(out.glob(f"{HAIKU}/B/medium/*.meta.json")))
    assert b_meta["sandbox_method"] == "builtin"
    assert "sandbox probe: running (one real call, cost counts toward the budget)" in lines(capsys.readouterr().out)


def test_sandbox_check_reuses_an_earlier_record(tmp_path, real_mode, monkeypatch, capsys):
    rec = {"passed": True, "reasons": [], "cost_usd": 0.0}
    calls = stub_check(monkeypatch, None, reusable=rec)
    assert real(tmp_path) == 0
    assert calls["run"] == []
    m = read(tmp_path / "runs" / "MANIFEST.json")
    assert m["sandbox"]["method"] == "builtin" and m["sandbox"]["probe"] == rec
    assert ("sandbox probe: reusing sandbox_probe.json (version and settings hash match)"
            in lines(capsys.readouterr().out))


def test_no_sandbox_check_without_condition_b(tmp_path, real_mode, monkeypatch):
    calls = stub_check(monkeypatch, None)
    assert real(tmp_path, conds="A") == 0
    m = read(tmp_path / "runs" / "MANIFEST.json")
    assert calls == {"run": [], "load": []} and m["sandbox"] == NOT_REQUESTED and m["b_stack"] is None


def test_a_failed_sandbox_check_skips_every_b_run(tmp_path, real_mode, monkeypatch, capsys):
    rec = {"passed": False, "reasons": ["NET rc=[0]"], "cost_usd": 0.0}
    stub_check(monkeypatch, rec)
    assert real(tmp_path, limit=2) == 0
    m = read(tmp_path / "runs" / "MANIFEST.json")
    assert m["counts"]["done"] == 2 and m["counts"]["not_run_sandbox"] == 2
    assert m["sandbox"]["method"] == "skipped"
    assert ("sandbox probe FAILED: condition B is skipped. builtin sandbox probe failed: NET rc=[0]\n"
            in capsys.readouterr().err)


def test_a_sandbox_check_that_is_not_evaluable_holds_b_back(tmp_path, real_mode, monkeypatch, capsys):
    rec = {"passed": None, "reasons": ["api error 500"], "cost_usd": 0.0}
    stub_check(monkeypatch, rec)
    assert real(tmp_path, limit=2) == 0
    m = read(tmp_path / "runs" / "MANIFEST.json")
    assert m["counts"]["done"] == 2 and m["counts"]["not_run_probe_not_evaluable"] == 2
    assert m["counts"]["not_run_sandbox"] == 0 and m["sandbox"]["method"] == "not evaluable"
    assert ("sandbox probe NOT EVALUABLE: condition B is not run now and not marked failed; --resume probes again. "
            "sandbox probe not evaluable: api error 500\n") in capsys.readouterr().err


@pytest.mark.parametrize("passed,bucket", [(False, "not_run_sandbox"), (None, "not_run_probe_not_evaluable")],
                         ids=["blocked", "not-evaluable"])
def test_budget_stop_sorts_the_rest_by_the_sandbox_state(tmp_path, real_mode, monkeypatch, passed, bucket):
    monkeypatch.setenv("FAKE_COST_USD", "1")
    stub_check(monkeypatch, {"passed": passed, "reasons": ["x"], "cost_usd": 0.0})
    real(tmp_path, limit=3, budget=1.5)
    c = read(tmp_path / "runs" / "MANIFEST.json")["counts"]
    # t1 A runs, t1 B is held back, t2 A runs, then the budget stops t2 B, t3 A and t3 B
    assert c["done"] == 2 and c[bucket] == 3 and c["not_run_budget"] == 1


def test_budget_used_up_by_the_sandbox_check(tmp_path, real_mode, monkeypatch, capsys):
    stub_check(monkeypatch, {"passed": True, "reasons": [], "cost_usd": 5.0})
    assert real(tmp_path, limit=2, budget=5.0) == runner.EX_TEMPFAIL
    m = read(tmp_path / "runs" / "MANIFEST.json")
    assert m["stopped_by_budget"] is True and m["counts"]["done"] == 1 and m["counts"]["not_run_budget"] == 3
    assert "budget reached after the sandbox probe; stopping cleanly" in lines(capsys.readouterr().out)


# ------------------------------------------------------------------ the command line
HELP_LINES = [
    "usage: tsbench run [-h] [--plan PLAN.JSONL] [--split {pilot,confirmatory}] [--models MODELS] "
    "[--conditions CONDITIONS] [--effort {low,medium,high,xhigh,max}] [--k K] [--budget-usd BUDGET_USD] "
    "[--per-call-usd PER_CALL_USD] --out OUT [--dry-run] [--resume] [--limit LIMIT] [--gateway] "
    "[--i-have-preregistered DOI] [--b-venv DIR]",
    "Run the benchmark.",
    "--plan PLAN.JSONL execute this run plan; it replaces --split/--models/--conditions/--effort/--k/--limit",
    "--models MODELS comma list of full model ids",
    "--conditions CONDITIONS comma list from A,B,C",
    "--k K repetitions per task x model x condition",
    "--budget-usd BUDGET_USD run-set guard: no run is STARTED once the spent total reaches it; a running call is "
    "never cut",
    "--per-call-usd PER_CALL_USD optional cap for one call (--max-budget-usd); off by default",
    "--dry-run use the fake claude; no cost",
    "--limit LIMIT first N tasks of the split",
    "--gateway use ANTHROPIC_BASE_URL/ANTHROPIC_AUTH_TOKEN",
    "--i-have-preregistered DOI",
    "--b-venv DIR venv of condition B (default: $TSBENCH_B_VENV, else ~/.cache/tsbench/venv-B); created from "
    "data/conditions/b-stack.txt if missing",
]


def test_help_text(monkeypatch, capsys):
    monkeypatch.setenv("COLUMNS", "400")
    with pytest.raises(SystemExit):
        runner.main(["--help"])
    text = " ".join(capsys.readouterr().out.split())
    for line in HELP_LINES:
        assert line in text


@pytest.mark.parametrize("argv,message", [
    (["--split", "pilot"], "the following arguments are required: --out"),
    (["--split", "other", "--out", "x"], "argument --split: invalid choice: 'other'"),
    (["--effort", "huge", "--out", "x"], "argument --effort: invalid choice: 'huge'"),
])
def test_bad_arguments(argv, message, capsys):
    with pytest.raises(SystemExit) as e:
        runner.parse_args(argv)
    assert e.value.code == 2 and message in capsys.readouterr().err


def test_the_options_land_in_their_fields():
    a = runner.parse_args(["--split", "pilot", "--models", HAIKU, "--conditions", "A", "--effort", "low",
                           "--out", "o", "--budget-usd", "2.5", "--per-call-usd", "0.5", "--limit", "3", "--k", "2",
                           "--i-have-preregistered", "10.1/x", "--b-venv", "v", "--dry-run", "--gateway", "--resume"])
    assert (a.out, a.budget_usd, a.per_call_usd, a.limit, a.k, a.preregistered, a.b_venv) == (
        "o", 2.5, 0.5, 3, 2, "10.1/x", "v")
    assert a.dry_run is True and a.gateway is True and a.resume is True


def test_commands_sh_repeats_the_invocation(tmp_path):
    out = tmp_path / "runs"
    dry(out, budget=1.0)
    text = (out / "inputs" / "commands.sh").read_text(encoding="utf-8")
    assert ("# the invocation (host paths as placeholders): tsbench run --split pilot --models claude-haiku-5-5 "
            "--conditions A --effort medium --k 1 --budget-usd 1.0 --out <OUT> --dry-run --limit 1\n") in text
    assert ('"$TSBENCH" run --split pilot --models claude-haiku-5-5 --conditions A --effort medium --k 1 --limit 1 '
            '--budget-usd 1.0 --out "$OUT" --dry-run\n') in text


def test_main_reads_sys_argv(tmp_path, monkeypatch):
    out = tmp_path / "runs"
    monkeypatch.setattr("sys.argv", ["tsbench-run", "--split", "pilot", "--models", HAIKU, "--conditions", "A",
                                     "--effort", "medium", "--k", "1", "--budget-usd", "1", "--out", str(out),
                                     "--dry-run", "--limit", "1"])
    assert runner.main() == 0
    assert "--split pilot --models claude-haiku-5-5" in (out / "inputs" / "commands.sh").read_text(encoding="utf-8")


def test_help_shows_the_description_on_its_own_line(monkeypatch, capsys):
    monkeypatch.setenv("COLUMNS", "400")
    with pytest.raises(SystemExit):
        runner.main(["--help"])
    assert "Run the benchmark." in [ln.strip() for ln in capsys.readouterr().out.splitlines()]


# ------------------------------------------------------------------ helpers of the exact-value tests below
IMAGE_TOOLS = ["mcp__tanabesugano__ts_plot_png", "mcp__tanabesugano__ts_emit_png"]
SONNET = "claude-sonnet-5-5"


def make_plan(path, *, models=(HAIKU,), conds=("A",), efforts=("medium",), limit=1, gateway=False, pins=None):
    """A clear plan built in memory and written to `path`."""
    spec = {"split": "pilot", "models": list(models), "conditions": list(conds), "efforts": list(efforts), "k": 1,
            "budget_usd": 1.0, "limit": limit, "gateway": gateway}
    plan = plan_mod.build_plan(load("pilot")[:limit], spec, pins=plan_mod.live_pins(None) if pins is None else pins)
    plan_mod.write_plan(plan, path, markdown=False)
    return plan


def meta_of(out: pathlib.Path, r: dict) -> dict:
    tp = runner.transcript_path(out, r["model"], r["condition"], r["effort"], r["task_id"], r["k"])
    return read(runner.meta_path(tp))


def answered(call: dict, **result) -> runner.Outcome:
    """An outcome with an init event and a result (`result` overrides fields of the result event)."""
    init = {"type": "system", "subtype": "init", "model": call["model"]}
    res = {"type": "result", "is_error": False, "total_cost_usd": 0.0, **result}
    return runner.Outcome(events=[init, res], init=init, mismatches=[], result=res, exit_code=0, wall_s=0.0,
                          stderr_tail="", timed_out=False, init_aborted=False, init_seen=True)


def stub_runs(monkeypatch, outcome_for) -> list[dict]:
    """`execute_with_retries` returns `outcome_for(call)`; each call is recorded with the manifest as it is on disk."""
    calls: list[dict] = []

    def fake(argv, prompt, env, transcript, cond, model, *, timeout_s, disallowed):
        transcript = pathlib.Path(transcript)
        transcript.parent.mkdir(parents=True, exist_ok=True)
        transcript.write_text("{}\n", encoding="utf-8")
        call = {"argv": list(argv), "env": dict(env), "model": model, "timeout_s": timeout_s,
                "disallowed": list(disallowed), "manifest": read(transcript.parents[3] / "MANIFEST.json")}
        calls.append(call)
        return outcome_for(call), []

    monkeypatch.setattr(runner, "execute_with_retries", fake)
    return calls


@pytest.fixture
def console(monkeypatch):
    """Every print of the runner as (text, keyword arguments); the line still reaches stdout or stderr."""
    calls: list[tuple[str, dict]] = []

    def spy(*args, **kw):
        calls.append((" ".join(str(a) for a in args), kw))
        print(*args, **kw)

    monkeypatch.setattr(runner, "print", spy, raising=False)
    return calls


def flushed(calls: list[tuple[str, dict]]) -> list[str]:
    """The printed texts, after checking that each one was flushed at once (a run set is watched live)."""
    assert [text for text, kw in calls if kw.get("flush") is not True] == []
    return [text for text, _ in calls]


def _caller_is_runner(depth: int = 2) -> bool:
    return sys._getframe(depth).f_globals.get("__name__") == "tsbench.run.runner"


@pytest.fixture
def runner_text_io(monkeypatch):
    """Every text read and write the runner itself makes, as (call, encoding) the way the runner passed it."""
    seen: list[tuple[str, object]] = []
    real_read, real_write = pathlib.Path.read_text, pathlib.Path.write_text

    def spy_read(self, encoding=None, errors=None):
        if _caller_is_runner():
            seen.append((f"read_text({self.name})", encoding))
        return real_read(self, encoding, errors)

    def spy_write(self, data, encoding=None, errors=None, newline=None):
        if _caller_is_runner():
            seen.append((f"write_text({self.name})", encoding))
        return real_write(self, data, encoding, errors, newline)

    monkeypatch.setattr(pathlib.Path, "read_text", spy_read)
    monkeypatch.setattr(pathlib.Path, "write_text", spy_write)
    return seen


# ------------------------------------------------------------------ text, clock and git
def test_every_text_read_and_write_of_the_runner_names_utf8(tmp_path, runner_text_io):
    out = tmp_path / "runs"
    assert dry(out) == 0
    assert dry(out, extra=("--resume",)) == 0  # reads the finished transcript
    plan_file = tmp_path / "plan.jsonl"
    plan_file.write_bytes((out / plan_mod.PLAN_NAME).read_bytes())
    (out / plan_mod.PLAN_NAME).unlink()  # --plan --resume then reads the plan_id from the manifest
    assert runner.main(["--plan", str(plan_file), "--out", str(out), "--resume", "--dry-run"]) == 0
    (r,) = plan_runs(out)
    calls = {call for call, _ in runner_text_io}
    # the manifest, the sidecar and the system prompt file are written by plan.write_text_atomic (utf-8, checked in the
    # test of the temp names)
    assert {"write_text(ts.json)", "write_text(sandbox-settings.json)",
            f"read_text(system-prompt-{r['system_prompt_sha256'][:16]}.txt)",
            f"read_text({plan_mod.PLAN_NAME})", f"read_text({plan_mod.SEALED_NAME})",
            "read_text(MANIFEST.json)"} <= calls  # a transcript is read in binary from its tail and decoded as utf-8
    assert [(call, enc) for call, enc in runner_text_io if enc != "utf-8"] == []


def test_the_runner_reads_the_clock_in_utc(tmp_path, monkeypatch):
    zones = []

    class Clock(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            zones.append(tz)
            return datetime.datetime.now(tz)

    monkeypatch.setattr(runner, "dt", SimpleNamespace(datetime=Clock, UTC=datetime.UTC))
    out = tmp_path / "runs"
    assert dry(out) == 0
    assert dry(out, extra=("--resume",)) == 0
    assert len(list(out.glob("MANIFEST.prev-*.json"))) == 1  # the stamp of the kept manifest is read too
    assert zones and all(z is datetime.UTC for z in zones)


def test_git_is_asked_for_the_commit_and_the_porcelain_status(tmp_path, monkeypatch):
    asked = []

    def git(repo, *args):
        asked.append((repo, *args))
        return "abc123" if args[0] == "rev-parse" else ""

    monkeypatch.setattr(runner, "git_output", git)
    assert dry(tmp_path / "runs") == 0
    assert asked == [(runner.REPO_ROOT, "rev-parse", "HEAD"), (runner.REPO_ROOT, "status", "--porcelain")]


# ------------------------------------------------------------------ what a real run records
def test_a_real_run_records_the_real_claude_and_no_fake_switches(tmp_path, real_mode, monkeypatch):
    monkeypatch.setenv("FAKE_COST_USD", "0")
    assert real(tmp_path, conds="A") == 0
    out = tmp_path / "runs"
    m = read(out / "MANIFEST.json")
    assert m["claude_version"] == {"used": "real", "real": "fake-0"}
    assert "FAKE_SEED" not in m["env_var_names"]
    assert "FAKE_COST_USD" not in (out / "inputs" / "commands.sh").read_text(encoding="utf-8")


def test_a_real_plan_run_compares_its_pins_with_the_live_session(tmp_path, real_mode, monkeypatch):
    orig = runner.Session.create.__func__

    def create(cls, **kw):
        s = orig(cls, **kw)
        s.real_claude_version = "9.9.9 (Claude Code)"
        s.settings_sha256 = "c" * 64
        return s

    monkeypatch.setattr(runner.Session, "create", classmethod(create))
    pins = {**plan_mod.live_pins(None), "claude_cli_version": "0.0.1", "b_stack_sha256": "e" * 64,
            "sandbox_settings_sha256": "c" * 64}
    make_plan(tmp_path / "plan.jsonl", pins=pins)
    assert runner.main(["--plan", str(tmp_path / "plan.jsonl"), "--out", str(tmp_path / "runs")]) == 0
    drift = read(tmp_path / "runs" / "MANIFEST.json")["pin_drift"]
    assert {"pin": "claude_cli_version", "planned": "0.0.1", "live": "9.9.9 (Claude Code)"} in drift
    assert {"pin": "b_stack_sha256", "planned": "e" * 64, "live": DIGEST} in drift
    assert [d for d in drift if d["pin"] == "sandbox_settings_sha256"] == []


@pytest.mark.parametrize("extra, model, auth", [(("--gateway",), SONNET, "gateway"),
                                                ((), sandbox.PROBE_MODEL, "direct")], ids=["gateway", "direct"])
def test_the_probe_model_and_auth_follow_the_gateway(tmp_path, real_mode, monkeypatch, extra, model, auth):
    calls = stub_check(monkeypatch, {"passed": True, "reasons": [], "cost_usd": 0.0})
    argv = ["--split", "pilot", "--models", SONNET, "--conditions", "A,B", "--effort", "medium", "--k", "1",
            "--limit", "1", "--budget-usd", "5", "--out", str(tmp_path / "runs"), *extra]
    assert runner.main(argv) == 0
    assert [c[2] for c in calls["run"]] == [model] and sandbox.PROBE_MODEL != SONNET
    assert [c[4] for c in calls["load"]] == [auth, auth]


SMALL, CAPABLE = "gwdg-llama-3.1-8b", "gwdg-qwen3.5-397b"


@pytest.mark.parametrize("models", [(SMALL, CAPABLE), (CAPABLE, SMALL)], ids=["small-first", "capable-first"])
def test_the_gateway_probe_does_not_depend_on_the_order_of_the_models(tmp_path, real_mode, monkeypatch, models):
    calls = stub_check(monkeypatch, {"passed": True, "reasons": [], "cost_usd": 0.0})
    argv = ["--split", "pilot", "--models", ",".join(models), "--conditions", "A,B", "--effort", "medium", "--k", "1",
            "--limit", "1", "--budget-usd", "5", "--out", str(tmp_path / "runs"), "--gateway"]
    assert runner.main(argv) == 0
    assert [c[2] for c in calls["run"]] == [CAPABLE]


def test_the_gateway_probe_of_models_that_are_not_known_as_capable_is_the_first_by_name(tmp_path, real_mode,
                                                                                         monkeypatch):
    calls = stub_check(monkeypatch, {"passed": True, "reasons": [], "cost_usd": 0.0})
    argv = ["--split", "pilot", "--models", "zz-model,aa-model", "--conditions", "A,B", "--effort", "medium",
            "--k", "1", "--limit", "1", "--budget-usd", "5", "--out", str(tmp_path / "runs"), "--gateway"]
    assert runner.main(argv) == 0
    assert [c[2] for c in calls["run"]] == ["aa-model"]


# ------------------------------------------------------------------ one run, its call and its records
def test_a_run_gets_the_wall_timeout_and_its_seed_while_the_manifest_says_unfinished(tmp_path, monkeypatch):
    calls = stub_runs(monkeypatch, answered)
    out = tmp_path / "runs"
    assert dry(out) == 0
    (call,) = calls
    (r,) = plan_runs(out)
    assert call["timeout_s"] == runner.WALL_TIMEOUT_S == 900
    assert call["env"]["FAKE_SEED"] == r["run_id"]
    assert call["manifest"]["finished"] is False and read(out / "MANIFEST.json")["finished"] is True


def test_an_aborted_run_records_every_reason_with_placeholders(tmp_path, monkeypatch, console, capsys):
    out = tmp_path / "runs"

    def aborted(call):
        return runner.Outcome(events=[], init=None, mismatches=[f"init names {out}/x", "the model differs"],
                              result=None, exit_code=None, wall_s=0.0, stderr_tail="", timed_out=False,
                              init_aborted=True)

    stub_runs(monkeypatch, aborted)
    assert dry(out) == 1
    (r,) = plan_runs(out)
    recorded = ["init names <OUT>/x", "the model differs"]
    meta = meta_of(out, r)
    assert meta["init_mismatches"] == recorded and meta["flag_details"] == {} and meta["cost_usd"] == 0.0
    assert read(out / "MANIFEST.json")["aborted_cells"][0]["reasons"] == recorded
    readme = (out / "README.md").read_text(encoding="utf-8")
    assert f"({HAIKU}/A/medium: init names <OUT>/x; the model differs)" in readme
    std = capsys.readouterr()
    assert f"ABORT CELL {HAIKU}/A/medium: init names {out}/x; the model differs\n" in std.err
    assert f"[1/1] {r['run_id']} cost=0.0000 spent=0.0000 flags=cost_unknown,no_result_event" in lines(std.out)
    assert f"ABORT CELL {HAIKU}/A/medium: init names {out}/x; the model differs" in flushed(console)


def test_a_run_that_timed_out_is_flagged_timeout(tmp_path, monkeypatch):
    def timed_out(call):
        return runner.Outcome(events=[], init=None, mismatches=[], result=None, exit_code=-9, wall_s=900.0,
                              stderr_tail="", timed_out=True, init_aborted=False)

    stub_runs(monkeypatch, timed_out)
    out = tmp_path / "runs"
    assert dry(out) == runner.EX_TEMPFAIL  # it is recorded, but no run of this invocation produced an answer
    (r,) = plan_runs(out)
    meta = meta_of(out, r)
    assert meta["flags"] == ["cost_unknown", "timeout"] and meta["timed_out"] is True


def test_condition_c_gets_its_mcp_config_and_its_flags(tmp_path, monkeypatch):
    stub_runs(monkeypatch, answered)
    out = tmp_path / "runs"
    assert dry(out, conds="C") == 0
    (r,) = plan_runs(out)
    meta = meta_of(out, r)
    assert meta["flags"] == ["c_no_mcp_call"]
    assert meta["argv"][meta["argv"].index("--mcp-config") + 1] == "<CFG>/ts.json"


def test_a_rate_limited_run_is_counted_in_the_progress_line(tmp_path, monkeypatch, capsys):
    stub_runs(monkeypatch, lambda call: answered(call, is_error=True, api_error_status=429,
                                                  result="API Error: rate limit"))
    out = tmp_path / "runs"
    assert dry(out) == runner.EX_TEMPFAIL
    (r,) = plan_runs(out)
    progress = f"[1/1] {r['run_id']} cost=0.0000 spent=0.0000 flags=result_is_error,rate_limited"
    assert progress in lines(capsys.readouterr().out)


def test_the_plan_record_decides_the_blocked_tools_and_the_turns(tmp_path, monkeypatch):
    path = tmp_path / "plan.jsonl"
    plan = make_plan(path)
    plan.runs[0]["disallowed_tools"] = [IMAGE_TOOLS[0]]
    plan.runs[0]["max_turns"] = 7
    r = plan.runs[0]  # the record decides: its argv_template says the same
    r["argv_template"] = plan_mod.argv_template(r["condition"], r["model"], r["effort"], 7, "fit", [IMAGE_TOOLS[0]])
    monkeypatch.setattr(plan_mod, "load_plan", lambda p: plan)
    calls = stub_runs(monkeypatch, answered)
    out = tmp_path / "runs"
    assert runner.main(["--plan", str(path), "--out", str(out), "--dry-run"]) == 0
    (call,) = calls
    argv = call["argv"]
    assert call["disallowed"] == [IMAGE_TOOLS[0]] and argv[argv.index("--disallowedTools") + 1] == IMAGE_TOOLS[0]
    assert argv[argv.index("--max-turns") + 1] == "7"
    assert meta_of(out, plan.runs[0])["disallowed_tools"] == [IMAGE_TOOLS[0]]


def test_a_plan_record_without_the_optional_fields_gets_the_live_rules(tmp_path, monkeypatch):
    """A record without `disallowed_tools` and `answer_schema_sha256`: the live rule blocks the image tools of a
    text-only gateway model in C, and the missing schema hash is not a mismatch."""
    path = tmp_path / "plan.jsonl"
    plan = make_plan(path, models=("qwen3.8-27b",), conds=("C",), gateway=True)
    for key in ("disallowed_tools", "answer_schema_sha256"):
        del plan.runs[0][key]
    monkeypatch.setattr(plan_mod, "load_plan", lambda p: plan)
    calls = stub_runs(monkeypatch, answered)
    assert runner.main(["--plan", str(path), "--out", str(tmp_path / "runs"), "--dry-run"]) == 0
    (call,) = calls
    assert call["disallowed"] == IMAGE_TOOLS


def test_a_plan_with_two_of_everything_is_recorded_as_given(tmp_path, monkeypatch):
    out = tmp_path / "runs"
    out.mkdir()
    make_plan(out / "in.jsonl", models=(HAIKU, SONNET), conds=("A", "C"), efforts=("low", "medium"))
    stub_runs(monkeypatch, answered)
    assert runner.main(["--plan", str(out / "in.jsonl"), "--out", str(out), "--dry-run"]) == 0
    m = read(out / "MANIFEST.json")
    assert (m["args"]["models"], m["args"]["conditions"], m["args"]["effort"]) == (
        f"{HAIKU},{SONNET}", "A,C", "low,medium")
    assert m["effort"] == ["low", "medium"] and m["counts"]["done"] == 8
    assert m["args"]["plan"] == "<OUT>/in.jsonl"
    # commands.sh repeats the invocation as given: no --budget-usd, which only the plan header held
    commands = (out / "inputs" / "commands.sh").read_text(encoding="utf-8").splitlines()
    assert '"$TSBENCH" run --plan "$HERE/plan.jsonl" --out "$OUT" --dry-run' in commands


def test_the_inputs_fall_back_to_the_parsed_flags_without_a_given_invocation(tmp_path, monkeypatch):
    """A caller of `_run` that passes neither `given` nor `raw_argv`, with arguments that have no per-call option."""
    real_run = runner._run

    def bare(args, session, out, plan, ts, drift, **kw):
        trimmed = SimpleNamespace(**{k: v for k, v in vars(args).items() if k != "per_call_usd"})
        return real_run(trimmed, session, out, plan, ts, drift)

    monkeypatch.setattr(runner, "_run", bare)
    out = tmp_path / "runs"
    assert dry(out, budget=1.0) == 0
    text = (out / "inputs" / "commands.sh").read_text(encoding="utf-8")
    assert "# the invocation (host paths as placeholders): tsbench run\n" in text
    assert ('"$TSBENCH" run --split pilot --models claude-haiku-5-5 --conditions A --effort medium --k 1 --limit 1 '
            '--budget-usd 1.0 --out "$OUT" --dry-run\n') in text


# ------------------------------------------------------------------ resume, plan ids and spending
def test_plan_resume_takes_the_plan_id_from_the_plan_file_before_the_manifest(tmp_path, capsys):
    out = tmp_path / "runs"
    assert dry(out) == 0
    first_id = plan_mod.load_plan(out / plan_mod.PLAN_NAME).plan_id
    other = make_plan(tmp_path / "other.jsonl", limit=2)
    argv = ["--plan", str(tmp_path / "other.jsonl"), "--out", str(out), "--resume", "--dry-run"]
    expected = f"runner: --resume: {out} holds plan_id {first_id}, this invocation has {other.plan_id}\n"
    (out / "MANIFEST.json").write_text(json.dumps(dict(read(out / "MANIFEST.json"), plan_id=other.plan_id)),
                                       encoding="utf-8")
    capsys.readouterr()
    with pytest.raises(SystemExit) as e:
        runner.main(argv)
    assert e.value.code == 2 and capsys.readouterr().err == expected  # the plan file wins over the manifest
    (out / "MANIFEST.json").unlink()
    with pytest.raises(SystemExit) as e:
        runner.main(argv)
    assert e.value.code == 2 and capsys.readouterr().err == expected  # and it is read without a manifest


def test_resume_records_the_hash_of_a_skipped_transcript_and_counts_it(tmp_path, capsys):
    out = tmp_path / "runs"
    assert dry(out, limit=1) == 0
    capsys.readouterr()
    assert dry(out, limit=2, extra=("--resume",)) == 0
    first, second = plan_runs(out)
    tp = out / HAIKU / "A" / "medium" / f"{first['task_id']}-k1.jsonl"
    m = read(out / "MANIFEST.json")
    assert m["counts"]["skipped"] == 1 and m["counts"]["done"] == 1
    assert m["transcripts"][first["run_id"]] == hashlib.sha256(tp.read_bytes()).hexdigest()
    assert any(ln.startswith(f"[2/2] {second['run_id']} ") for ln in lines(capsys.readouterr().out))


def test_a_resume_that_stops_early_still_records_the_hash_of_every_finished_transcript(tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_COST_USD", "1")
    out = tmp_path / "runs"
    assert dry(out, limit=4) == 0
    runs = plan_runs(out)
    tps = [out / HAIKU / "A" / "medium" / f"{r['task_id']}-k1.jsonl" for r in runs]
    tps[1].unlink()  # run 1 must run again; runs 0, 2 and 3 are finished
    # runs 0, 2 and 3 have cost 3.0: the budget stops the resume at run 1, before the later finished runs are reached
    assert dry(out, limit=4, budget=3.0, extra=("--resume",)) == runner.EX_TEMPFAIL
    m = read(out / "MANIFEST.json")
    assert m["stopped_by_budget"] is True and m["counts"]["skipped"] == 3
    assert m["transcripts"] == {runs[i]["run_id"]: hashlib.sha256(tps[i].read_bytes()).hexdigest() for i in (0, 2, 3)}


def _resume_refused(out, capsys, **kw) -> str:
    """The message of a flags-form --resume that exits 2; the folder is left as it was."""
    before = sorted(p.name for p in out.iterdir())
    capsys.readouterr()
    with pytest.raises(SystemExit) as e:
        dry(out, extra=("--resume",), **kw)
    assert e.value.code == 2
    assert sorted(p.name for p in out.iterdir()) == before  # no MANIFEST.prev-*, no plan.prev-*
    return capsys.readouterr().err


def test_resume_refuses_finished_runs_made_with_another_turn_limit(tmp_path, monkeypatch, capsys):
    out = tmp_path / "runs"
    assert dry(out) == 0
    (r,) = plan_runs(out)
    monkeypatch.setitem(conditions.MAX_TURNS, "A", 7)
    err = _resume_refused(out, capsys)
    assert f"--resume: {r['run_id']}: finished with max_turns 15, the plan has 7" in err
    assert meta_of(out, r)["max_turns"] == 15  # nothing was sampled again


@pytest.mark.parametrize("field", ["prompt_sha256", "system_prompt_sha256"])
def test_resume_refuses_finished_runs_made_with_another_prompt(tmp_path, capsys, field):
    out = tmp_path / "runs"
    assert dry(out) == 0
    (r,) = plan_runs(out)
    sidecar = runner.meta_path(out / HAIKU / "A" / "medium" / f"{r['task_id']}-k1.jsonl")
    rec = read(sidecar)
    assert rec[field] == r[field]  # the sidecar names the prompt it was made with
    sidecar.write_text(json.dumps(dict(rec, **{field: "0" * 64})), encoding="utf-8")
    assert f"--resume: {r['run_id']}: finished with {field} {'0' * 64!r}" in _resume_refused(out, capsys)


def test_resume_does_not_compare_a_run_that_is_not_finished_or_has_no_sidecar(tmp_path, monkeypatch):
    out = tmp_path / "runs"
    assert dry(out, limit=2) == 0
    first, second = plan_runs(out)
    tps = [out / HAIKU / "A" / "medium" / f"{r['task_id']}-k1.jsonl" for r in (first, second)]
    runner.meta_path(tps[0]).unlink()  # a crash between transcript and sidecar
    tps[1].write_text("", encoding="utf-8")  # an interrupted run, whatever its sidecar says
    monkeypatch.setitem(conditions.MAX_TURNS, "A", 7)
    assert dry(out, limit=2, extra=("--resume",)) == 0
    assert meta_of(out, second)["max_turns"] == 7


def test_resume_of_the_flags_form_keeps_the_claude_version_the_plan_pinned(tmp_path, real_mode, monkeypatch):
    stub_check(monkeypatch, None)
    real_mode_create = runner.Session.create.__func__
    version = ["1.0.0 (Claude Code)"]

    def create(cls, **kw):
        s = real_mode_create(cls, **kw)
        s.real_claude_version = version[0]
        return s

    monkeypatch.setattr(runner.Session, "create", classmethod(create))
    assert real(tmp_path, conds="A") == 0
    version[0] = "2.0.0 (Claude Code)"  # claude was updated between the invocations
    assert runner.main(["--split", "pilot", "--models", HAIKU, "--conditions", "A", "--effort", "medium", "--k", "1",
                        "--limit", "1", "--budget-usd", "5", "--out", str(tmp_path / "runs"), "--resume"]) == 0
    drift = read(tmp_path / "runs" / "MANIFEST.json")["pin_drift"]
    assert {"pin": "claude_cli_version", "planned": "1.0.0 (Claude Code)", "live": "2.0.0 (Claude Code)"} in drift


def test_resume_that_extends_the_matrix_still_records_the_claude_update(tmp_path, real_mode, monkeypatch):
    """A larger --k changes the plan_id; the pin of the first invocation is still the one the live claude is held to."""
    stub_check(monkeypatch, None)
    real_mode_create = runner.Session.create.__func__
    version = ["1.0.0 (Claude Code)"]

    def create(cls, **kw):
        s = real_mode_create(cls, **kw)
        s.real_claude_version = version[0]
        return s

    monkeypatch.setattr(runner.Session, "create", classmethod(create))
    assert real(tmp_path, conds="A") == 0
    first_id = read(tmp_path / "runs" / "MANIFEST.json")["plan_id"]
    version[0] = "2.0.0 (Claude Code)"
    assert runner.main(["--split", "pilot", "--models", HAIKU, "--conditions", "A", "--effort", "medium", "--k", "2",
                        "--limit", "1", "--budget-usd", "5", "--out", str(tmp_path / "runs"), "--resume"]) == 0
    m = read(tmp_path / "runs" / "MANIFEST.json")
    assert m["plan_id"] != first_id  # the matrix grew
    assert {"pin": "claude_cli_version", "planned": "1.0.0 (Claude Code)", "live": "2.0.0 (Claude Code)"} in m[
        "pin_drift"]
    assert plan_mod.load_plan(tmp_path / "runs" / plan_mod.PLAN_NAME).header["pins"]["claude_cli_version"] == (
        "1.0.0 (Claude Code)")


def test_resume_keeps_a_run_that_hit_the_wall_limit_and_runs_a_crashed_one_again(tmp_path, monkeypatch):
    def timed_out(call):
        return runner.Outcome(events=[], init=None, mismatches=[], result=None, exit_code=-9, wall_s=900.0,
                              stderr_tail="", timed_out=True, init_aborted=False)

    calls = stub_runs(monkeypatch, timed_out)
    out = tmp_path / "runs"
    dry(out, limit=2)  # nothing was answered: the exit code is not the point here
    first, second = plan_runs(out)
    tp = lambda r: out / HAIKU / "A" / "medium" / f"{r['task_id']}-k1.jsonl"  # noqa: E731
    # the second run was killed before its sidecar was written: only that one is interrupted
    runner.meta_path(tp(second)).unlink()
    assert len(calls) == 2
    dry(out, limit=2, extra=("--resume",))
    assert len(calls) == 3  # the timed out run is an outcome and is not sampled again
    assert [p.name for p in out.glob("*/*/*/*.attempt*.jsonl")] == [f"{second['task_id']}-k1.attempt1.jsonl"]
    c = read(out / "MANIFEST.json")["counts"]
    assert c["skipped"] == 1 and c["done"] == 1
    assert meta_of(out, first)["timed_out"] is True


def _snapshot(out: pathlib.Path) -> dict[str, bytes]:
    return {str(p.relative_to(out)): p.read_bytes() for p in sorted(out.rglob("*")) if p.is_file()}


def test_a_second_run_without_resume_is_refused_and_touches_nothing(tmp_path, capsys):
    out = tmp_path / "runs"
    assert dry(out) == 0
    before = _snapshot(out)
    capsys.readouterr()
    with pytest.raises(SystemExit) as e:
        dry(out)
    assert e.value.code == 2
    err = capsys.readouterr().err
    assert str(out) in err and "already holds a run set" in err and "--resume" in err
    assert _snapshot(out) == before  # no transcript truncated, no plan or manifest rewritten, no MANIFEST.prev


def test_a_run_folder_with_transcripts_but_no_manifest_is_refused_too(tmp_path, capsys):
    out = tmp_path / "runs"
    assert dry(out) == 0
    (out / "MANIFEST.json").unlink()
    before = _snapshot(out)
    with pytest.raises(SystemExit) as e:
        dry(out, limit=2)  # another plan_id over the leftovers of the first
    assert e.value.code == 2 and "already holds a run set" in capsys.readouterr().err
    assert _snapshot(out) == before


def test_a_run_folder_that_holds_only_the_sandbox_probe_is_not_a_run_set(tmp_path):
    out = tmp_path / "runs"
    (out / "_sandbox_probe").mkdir(parents=True)
    (out / "_sandbox_probe" / "transcript.jsonl").write_text("{}\n", encoding="utf-8")
    (out / "sandbox_probe.json").write_text("{}\n", encoding="utf-8")
    assert dry(out) == 0


def test_resume_may_continue_a_run_folder(tmp_path):
    out = tmp_path / "runs"
    assert dry(out) == 0
    assert dry(out, extra=("--resume",)) == 0


def _fake_earlier_history(out: pathlib.Path, run: dict, *, flags, reported) -> None:
    """Write into the sidecar of `run` and the manifest what an earlier invocation of the same run set recorded."""
    meta = out / HAIKU / "A" / "medium" / f"{run['task_id']}-k1.meta.json"
    d = read(meta)
    d.update(flags=flags, reported_model=reported, started_utc="2020-01-01T00:00:00+00:00")
    meta.write_text(json.dumps(d), encoding="utf-8")
    man = read(out / "MANIFEST.json")
    man["start_time_utc"] = "2020-01-01T00:00:00+00:00"
    (out / "MANIFEST.json").write_text(json.dumps(man), encoding="utf-8")


def test_a_resumed_manifest_describes_the_whole_run_set(tmp_path):
    out = tmp_path / "runs"
    assert dry(out, limit=1) == 0
    (first,) = plan_runs(out)
    _fake_earlier_history(out, first, flags=["b_no_tool_use"], reported="claude-old-9-9")
    assert dry(out, limit=2, extra=("--resume",)) == 0
    m = read(out / "MANIFEST.json")
    assert m["counts"]["skipped"] == 1 and m["counts"]["done"] == 1
    assert m["flagged_runs"] == [{"run_id": first["run_id"], "flags": ["b_no_tool_use"]}]
    assert m["reported_models"] == {HAIKU: {"A": sorted({"claude-old-9-9", HAIKU})}}
    assert m["start_time_utc"] == "2020-01-01T00:00:00+00:00"  # the first invocation's start, not the last one's


def test_a_resumed_manifest_keeps_the_aborted_cell_of_a_run_that_is_not_reached(tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_COST_USD", "1")
    out = tmp_path / "runs"
    assert dry(out, limit=2) == 0
    first, second = plan_runs(out)
    meta = out / HAIKU / "A" / "medium" / f"{second['task_id']}-k1.meta.json"
    d = read(meta)
    d.update(cell_aborted=True, init_mismatches=["model differs"])
    meta.write_text(json.dumps(d), encoding="utf-8")
    tp = out / HAIKU / "A" / "medium" / f"{second['task_id']}-k1.jsonl"
    tp.write_text('{"type":"system","subtype":"init"}\n', encoding="utf-8")  # unfinished: --resume would run it again
    # the first run is finished (cost 1.0): the budget stops this resume before the unfinished second run starts
    assert dry(out, limit=2, budget=1.0, extra=("--resume",)) in (0, runner.EX_TEMPFAIL)  # a budget stop, not a failure
    m = read(out / "MANIFEST.json")
    assert m["stopped_by_budget"] is True
    assert m["aborted_cells"] == [{"model": HAIKU, "condition": "A", "effort": "medium", "first_run": second["run_id"],
                                   "reasons": ["model differs"]}]


def test_a_rerun_run_replaces_what_the_earlier_sidecar_said(tmp_path):
    out = tmp_path / "runs"
    assert dry(out, limit=2) == 0
    first, second = plan_runs(out)
    _fake_earlier_history(out, second, flags=["no_result_event"], reported="claude-old-9-9")
    tp = out / HAIKU / "A" / "medium" / f"{second['task_id']}-k1.jsonl"
    tp.write_text('{"type":"system","subtype":"init"}\n', encoding="utf-8")  # unfinished: run again
    assert dry(out, limit=2, extra=("--resume",)) == 0
    m = read(out / "MANIFEST.json")
    assert m["flagged_runs"] == [] and m["reported_models"] == {HAIKU: {"A": [HAIKU]}}


def test_resume_adds_a_paid_api_error_to_what_is_already_spent(tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_COST_USD", "0.3")
    out = tmp_path / "runs"
    assert dry(out, limit=2) == 0
    second = plan_runs(out)[1]
    tp = out / HAIKU / "A" / "medium" / f"{second['task_id']}-k1.jsonl"
    tp.write_text(json.dumps({"type": "result", "subtype": "success", "is_error": True, "api_error_status": 500,
                              "terminal_reason": "api_error", "total_cost_usd": 0.25, "result": "API Error: 500"})
                  + "\n", encoding="utf-8")
    assert dry(out, limit=2, extra=("--resume",)) == 0
    # 0.3 of the finished first run + 0.25 of the paid error + 0.3 of its re-run
    assert read(out / "MANIFEST.json")["total_cost_usd"] == pytest.approx(0.85)


def test_resume_keeps_counting_the_paid_errors_of_earlier_invocations(tmp_path, monkeypatch):
    """A paid 5xx that an earlier resume set aside as `.attemptN.jsonl` stays part of the spent total in every later
    invocation, also in one that has nothing left to run, so the budget guard never starts below the money spent."""
    monkeypatch.setenv("FAKE_COST_USD", "0.3")
    out = tmp_path / "runs"
    assert dry(out, limit=2) == 0
    second = plan_runs(out)[1]
    tp = out / HAIKU / "A" / "medium" / f"{second['task_id']}-k1.jsonl"

    def paid_error(cost: float) -> None:
        tp.write_text(json.dumps({"type": "result", "subtype": "success", "is_error": True, "api_error_status": 500,
                                  "terminal_reason": "api_error", "total_cost_usd": cost, "result": "API Error: 500"})
                      + "\n", encoding="utf-8")

    def spent() -> float:
        return read(out / "MANIFEST.json")["total_cost_usd"]

    paid_error(0.25)
    assert dry(out, limit=2, extra=("--resume",)) == 0
    assert spent() == pytest.approx(0.85)  # 0.3 first run + 0.25 paid error (attempt1) + 0.3 re-run
    assert dry(out, limit=2, extra=("--resume",)) == 0  # nothing to run: the total must not shrink
    assert spent() == pytest.approx(0.85)
    paid_error(0.2)  # the re-run failed again
    assert dry(out, limit=2, extra=("--resume",)) == 0
    assert spent() == pytest.approx(1.05)  # + 0.2 paid error (attempt2) + 0.3 re-run; attempt1 is still counted


def test_the_per_call_cap_is_limited_by_what_is_left_of_the_budget(tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_COST_USD", "0.4")
    out = tmp_path / "runs"
    dry(out, limit=2, budget=1.0, extra=("--per-call-usd", "3"))
    argvs = [meta_of(out, r)["argv"] for r in plan_runs(out)]
    assert [a[a.index("--max-budget-usd") + 1] for a in argvs] == ["1.0000", "0.6000"]


def test_a_run_aborted_after_its_init_is_charged_the_per_call_cap(tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_BAD_INIT", "1")  # init arrives (an API request may have been sent), then the cell aborts
    out = tmp_path / "runs"
    assert dry(out, extra=("--per-call-usd", "1.5")) == 1
    (r,) = plan_runs(out)
    meta = meta_of(out, r)
    assert meta["cell_aborted"] is True and meta["cost_unknown"] is True and meta["cost_usd"] == 1.5
    assert read(out / "MANIFEST.json")["total_cost_usd"] == 1.5


def test_resume_keeps_counting_the_per_call_charge_of_an_init_aborted_attempt(tmp_path, monkeypatch):
    """An init-aborted run is charged the per-call cap and its transcript is set aside without a result event. A
    later --resume that finishes the cell must still count that charge, in this and in every later invocation."""
    out = tmp_path / "runs"
    with monkeypatch.context() as mp:
        mp.setenv("FAKE_BAD_INIT", "1")
        assert dry(out, extra=("--per-call-usd", "1.5")) == 1
    monkeypatch.setenv("FAKE_COST_USD", "0.3")
    assert dry(out, extra=("--resume", "--per-call-usd", "1.5")) == 0
    assert read(out / "MANIFEST.json")["total_cost_usd"] == pytest.approx(1.8)  # 1.5 aborted attempt + 0.3 re-run
    assert dry(out, extra=("--resume", "--per-call-usd", "1.5")) == 0  # nothing to run: the total must not shrink
    assert read(out / "MANIFEST.json")["total_cost_usd"] == pytest.approx(1.8)


def test_a_killed_rerun_of_an_init_aborted_cell_does_not_book_the_aborted_charge_twice(tmp_path, monkeypatch):
    """The init-aborted attempt keeps its charge beside `<stem>.attempt1.jsonl`; its sidecar also stays at the normal
    path. A rerun killed after it wrote its transcript but before its sidecar leaves that sidecar stale. The next
    --resume sets the killed rerun aside and must not carry the stale charge along as a second aborted attempt."""
    out = tmp_path / "runs"
    with monkeypatch.context() as mp:
        mp.setenv("FAKE_BAD_INIT", "1")
        assert dry(out, extra=("--per-call-usd", "1.5")) == 1
    (r,) = plan_runs(out)
    tp = out / HAIKU / "A" / "medium" / f"{r['task_id']}-k1.jsonl"
    tp.write_text(json.dumps({"type": "system", "subtype": "init"}) + "\n", encoding="utf-8")  # the killed rerun
    monkeypatch.setenv("FAKE_COST_USD", "0.3")
    assert dry(out, extra=("--resume", "--per-call-usd", "1.5")) == 0
    assert read(out / "MANIFEST.json")["total_cost_usd"] == pytest.approx(1.8)  # 1.5 aborted attempt + 0.3 re-run
    assert dry(out, extra=("--resume", "--per-call-usd", "1.5")) == 0  # nothing to run: the total stays
    assert read(out / "MANIFEST.json")["total_cost_usd"] == pytest.approx(1.8)

def test_a_429_on_the_rerun_of_an_init_aborted_cell_does_not_book_the_aborted_charge_twice(tmp_path, monkeypatch):
    """The rerun of an aborted cell that meets HTTP 429 sets its limited attempt aside with its sidecar; the stale
    sidecar of the aborted attempt must not travel along as a second aborted charge."""
    out = tmp_path / "runs"
    monkeypatch.setattr(runner, "sleep", lambda s: None)
    with monkeypatch.context() as mp:
        mp.setenv("FAKE_BAD_INIT", "1")
        assert dry(out, extra=("--per-call-usd", "1.5")) == 1
    monkeypatch.setenv("FAKE_COST_USD", "0.3")
    with monkeypatch.context() as mp:
        mp.setenv("FAKE_429_FIRST", "1")
        mp.setenv("FAKE_429_STATE", str(tmp_path / "count"))
        assert dry(out, extra=("--resume", "--per-call-usd", "1.5")) == 0
    assert read(out / "MANIFEST.json")["total_cost_usd"] == pytest.approx(1.8)
    assert dry(out, extra=("--resume", "--per-call-usd", "1.5")) == 0  # nothing to run: the total stays
    assert read(out / "MANIFEST.json")["total_cost_usd"] == pytest.approx(1.8)


def test_a_paid_error_left_at_the_normal_path_counts_before_the_budget_guard(tmp_path, monkeypatch):
    """A paid 5xx of an earlier invocation that no resume has set aside yet is money on disk too: a resume whose
    budget it already exceeds starts no run."""
    monkeypatch.setenv("FAKE_COST_USD", "0.3")
    out = tmp_path / "runs"
    assert dry(out, limit=2) == 0
    second = plan_runs(out)[1]
    tp = out / HAIKU / "A" / "medium" / f"{second['task_id']}-k1.jsonl"
    tp.write_text(json.dumps({"type": "result", "subtype": "success", "is_error": True, "api_error_status": 500,
                              "result": "API Error: 500", "total_cost_usd": 2.0}) + "\n", encoding="utf-8")
    dry(out, limit=2, budget=1.0, extra=("--resume",))
    m = read(out / "MANIFEST.json")
    assert m["stopped_by_budget"] is True and m["counts"]["not_run_budget"] == 1
    assert m["total_cost_usd"] == pytest.approx(2.3)
    assert tp.exists()  # not started, so not set aside either


def test_resume_keeps_counting_the_per_call_charge_of_a_run_without_a_result(tmp_path, monkeypatch):
    """A run that ended without a result event is charged the per-call cap; set aside by a resume, that charge stays
    in the total of this and every later invocation."""
    out = tmp_path / "runs"
    with monkeypatch.context() as mp:
        mp.setenv("FAKE_NO_RESULT", "1")
        dry(out, extra=("--per-call-usd", "1.5"))
    assert read(out / "MANIFEST.json")["total_cost_usd"] == pytest.approx(1.5)
    monkeypatch.setenv("FAKE_COST_USD", "0.3")
    assert dry(out, extra=("--resume", "--per-call-usd", "1.5")) == 0
    assert read(out / "MANIFEST.json")["total_cost_usd"] == pytest.approx(1.8)
    assert dry(out, extra=("--resume", "--per-call-usd", "1.5")) == 0
    assert read(out / "MANIFEST.json")["total_cost_usd"] == pytest.approx(1.8)


def test_an_init_aborted_run_is_not_listed_as_a_transcript(tmp_path, monkeypatch):
    """The aborted attempt is set aside, so the manifest lists no transcript (and no null hash) for it, and the score
    table of the folder is not older than its transcripts."""
    from tsbench.score import score as score_mod
    monkeypatch.setenv("FAKE_BAD_INIT", "1")
    out = tmp_path / "runs"
    assert dry(out) == 1
    assert read(out / "MANIFEST.json")["transcripts"] == {}
    score_mod.score_dir(out)
    assert score_mod.scores_drift(out) == {}

def test_a_context_overflow_is_scored_wrong_and_not_run_again(tmp_path, monkeypatch):
    """HTTP 400 with a context-window text is the model's failure: a resume keeps it, the scorer counts it as an
    evaluable wrong answer in the category `context_overflow`."""
    from tsbench.score import score as score_mod
    from tsbench.score import taxonomy
    monkeypatch.setenv("FAKE_COST_USD", "0.3")
    out = tmp_path / "runs"
    assert dry(out) == 0
    (r,) = plan_runs(out)
    tp = out / HAIKU / "A" / "medium" / f"{r['task_id']}-k1.jsonl"
    overflow = {"type": "result", "subtype": "success", "is_error": True, "api_error_status": 400,
                "terminal_reason": "api_error", "total_cost_usd": 0.2,
                "result": "API Error: 400 litellm.ContextWindowExceededError: maximum context length is 131072"}
    tp.write_text(json.dumps(overflow) + "\n", encoding="utf-8")
    assert dry(out, extra=("--resume",)) == 0
    assert read(out / "MANIFEST.json")["counts"]["skipped"] == 1
    assert json.loads(tp.read_text(encoding="utf-8").splitlines()[-1]) == overflow
    score_mod.score_dir(out)
    import csv
    with open(out / "scores.csv", newline="", encoding="utf-8") as fh:
        (row,) = list(csv.DictReader(fh))
    assert (row["evaluable"], row["correct"], row["context_overflow"]) == ("True", "False", "True")
    task = {t["id"]: t for t in load("pilot")}[r["task_id"]]
    assert taxonomy.failure_category(row, task) == "context_overflow"

def test_a_budget_stop_counts_the_runs_of_an_aborted_cell_as_aborted(tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_BAD_INIT", "1")
    out = tmp_path / "runs"
    # t1/A aborts its cell and is charged the cap (1.0): the budget stops before t1/C; t2/A and t3/A are aborted
    assert dry(out, conds="A,C", limit=3, budget=1.0, extra=("--per-call-usd", "1")) == 1
    c = read(out / "MANIFEST.json")["counts"]
    assert (c["aborted"], c["not_run_budget"], c["done"]) == (3, 3, 0)


def test_the_total_cost_is_rounded_to_six_decimals(tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_COST_USD", "0.1234567")
    out = tmp_path / "runs"
    assert dry(out) == 0
    assert read(out / "MANIFEST.json")["total_cost_usd"] == 0.123457


def test_resume_keeps_the_plan_of_the_first_invocation_and_a_new_run_builds_its_own(tmp_path, monkeypatch):
    stamps = iter(f"2026-0{n}-01T00:00:00+00:00" for n in range(1, 10))
    real_build = plan_mod.build_plan
    monkeypatch.setattr(plan_mod, "build_plan", lambda *a, **kw: real_build(*a, created_utc=next(stamps), **kw))
    out = tmp_path / "runs"
    assert dry(out) == 0
    first = hashlib.sha256((out / plan_mod.PLAN_NAME).read_bytes()).hexdigest()
    assert dry(out, extra=("--resume",)) == 0
    assert read(out / "MANIFEST.json")["plan_sha256"] == first  # --resume runs the stored plan, not a rebuilt one
    assert dry(tmp_path / "other") == 0
    assert read(tmp_path / "other" / "MANIFEST.json")["plan_sha256"] != first  # a new run set runs the plan it built


def test_resume_rebuilds_the_sidecar_of_a_run_that_ended_in_a_result_without_one(tmp_path):
    """Ctrl-C after the result event, before the sidecar was written: --resume must not skip the run for good."""
    out = tmp_path / "runs"
    assert dry(out, conds="A,C", limit=2) == 0
    sidecars = sorted(out.glob("*/*/*/*.meta.json"))
    assert len(sidecars) == 4
    before = {sc: read(sc) for sc in sidecars}
    flagged = read(out / "MANIFEST.json")["flagged_runs"]
    transcripts = {tp: tp.read_bytes() for tp in out.glob("*/*/*/*.jsonl")}
    for sc in sidecars:
        sc.unlink()
    assert dry(out, conds="A,C", limit=2, extra=("--resume",)) == 0
    m = read(out / "MANIFEST.json")
    assert m["counts"]["skipped"] == 4 and m["counts"]["done"] == 0
    assert sorted(out.glob("*/*/*/*.meta.json")) == sidecars
    for sc in sidecars:
        now, old = read(sc), before[sc]
        assert now["sidecar_rebuilt"] is True
        for key in ("run_id", "model", "condition", "effort", "task_id", "k", "argv", "flags", "flag_details",
                    "init_mismatches", "reported_model", "cost_usd", "cost_unknown", "disallowed_tools", "max_turns",
                    "plan_id", "prompt_sha256", "system_prompt_sha256", "artifacts", "image_sha_match",
                    "env_var_names", "claude_version"):
            assert now[key] == old[key], key
    assert m["flagged_runs"] == flagged
    assert {tp: tp.read_bytes() for tp in out.glob("*/*/*/*.jsonl")} == transcripts  # transcripts stay as they were
    assert dry(out, conds="A,C", limit=2, extra=("--resume",)) == 0  # a third pass has nothing left to rebuild
    assert all("sidecar_rebuilt" in read(sc) for sc in sidecars)


def test_resume_rebuilds_the_flags_of_the_events(tmp_path):
    """The rebuilt sidecar carries the flags of the events: an empty C run has `c_no_mcp_call`."""
    out = tmp_path / "runs"
    assert dry(out, conds="C") == 0
    (sidecar,) = out.glob("*/*/*/*.meta.json")
    (tp,) = out.glob("*/*/*/*.jsonl")
    events = [json.loads(ln) for ln in tp.read_text(encoding="utf-8").splitlines() if ln.strip()]
    keep = [e for e in events if e.get("type") in ("system", "result")]
    tp.write_text("".join(json.dumps(e) + "\n" for e in keep), encoding="utf-8")
    sidecar.unlink()
    assert dry(out, conds="C", extra=("--resume",)) == 0
    assert read(sidecar)["flags"] == ["c_no_mcp_call"]
    assert read(out / "MANIFEST.json")["flagged_runs"] == [{"run_id": read(sidecar)["run_id"],
                                                            "flags": ["c_no_mcp_call"]}]


def test_a_dry_run_does_not_pin_the_version_of_an_installed_claude(tmp_path, monkeypatch):
    orig = runner.Session.create.__func__

    def create(cls, **kw):
        s = orig(cls, **kw)
        s.real_claude_version = "9.9.9 (Claude Code)"
        return s

    monkeypatch.setattr(runner.Session, "create", classmethod(create))
    out = tmp_path / "runs"
    assert dry(out) == 0
    header = json.loads((out / plan_mod.PLAN_NAME).read_text(encoding="utf-8").splitlines()[0])
    assert header["pins"]["claude_cli_version"] is None


def test_the_flags_plan_pins_the_digest_of_the_given_b_venv(tmp_path, monkeypatch):
    given = tmp_path / "given-venv-B"
    (given / "bin").mkdir(parents=True)

    def digest(venv):
        return hashlib.sha256(pathlib.Path(venv).name.encode("utf-8")).hexdigest()

    monkeypatch.setattr(runner.b_stack, "digest_if_present", digest)
    out = tmp_path / "runs"
    assert dry(out, conds="B", extra=("--b-venv", str(given))) == 0
    header = json.loads((out / plan_mod.PLAN_NAME).read_text(encoding="utf-8").splitlines()[0])
    assert header["pins"]["b_stack_sha256"] == hashlib.sha256(b"given-venv-B").hexdigest()


def test_the_flags_form_with_a_b_venv_records_no_settings_drift(tmp_path, capsys):
    given = tmp_path / "given-venv-B"
    (given / "bin").mkdir(parents=True)
    out = tmp_path / "runs"
    assert dry(out, extra=("--b-venv", str(given))) == 0
    assert read(out / "MANIFEST.json")["pin_drift"] == [] and "WARNING pin drift" not in capsys.readouterr().err
    header = json.loads((out / plan_mod.PLAN_NAME).read_text(encoding="utf-8").splitlines()[0])
    assert header["pins"]["sandbox_settings_sha256"] == sandbox.settings_sha256(runner.REPO_ROOT, b_venv=given)


def test_a_plan_built_with_a_b_venv_runs_with_it_without_settings_drift(tmp_path, capsys):
    from tsbench.plan import __main__ as plan_cli
    given = tmp_path / "given-venv-B"
    (given / "bin").mkdir(parents=True)
    plan_file = tmp_path / "plan.jsonl"
    assert plan_cli.main(["build", "--split", "pilot", "--models", HAIKU, "--conditions", "A", "--effort", "medium",
                          "--k", "1", "--budget-usd", "1", "--limit", "1", "--out-plan", str(plan_file),
                          "--b-venv", str(given)]) == 0
    out = tmp_path / "runs"
    assert runner.main(["--plan", str(plan_file), "--out", str(out), "--dry-run", "--b-venv", str(given)]) == 0
    assert read(out / "MANIFEST.json")["pin_drift"] == [] and "WARNING pin drift" not in capsys.readouterr().err


# ------------------------------------------------------------------ refusals with their exact message
def test_the_confirmatory_guard_names_what_is_missing(tmp_path, capsys):
    argv = ["--split", "confirmatory", "--models", HAIKU, "--conditions", "A", "--effort", "medium", "--k", "1",
            "--budget-usd", "1", "--out", str(tmp_path / "runs"), "--dry-run"]
    with pytest.raises(SystemExit) as e:
        runner.main(argv)
    assert e.value.code == 2
    assert capsys.readouterr().err == ("runner: --split confirmatory needs --i-have-preregistered <DOI> (the "
                                       "preregistration must be deposited before any model sees the confirmatory "
                                       "tasks)\n")


def test_model_ids_are_refused_before_the_tasks_are_loaded(tmp_path, capsys, monkeypatch):
    import tsbench.tasks as tasks_mod

    def boom(*a, **k):
        raise AssertionError("tasks were loaded before the model check")

    monkeypatch.setattr(tasks_mod, "load", boom)
    argv = ["--split", "pilot", "--models", "haiku", "--conditions", "A", "--effort", "medium", "--k", "1",
            "--budget-usd", "1", "--out", str(tmp_path / "runs"), "--dry-run"]
    with pytest.raises(SystemExit) as e:
        runner.main(argv)
    assert e.value.code == 2
    assert capsys.readouterr().err == "runner: 'haiku' is an alias; give the full model id (e.g. claude-haiku-5-5)\n"


def confirmatory_plan(tmp_path, monkeypatch):
    """A one-run plan of pilot tasks whose header says confirmatory (no confirmatory task is read)."""
    path = tmp_path / "plan.jsonl"
    plan = make_plan(path)
    plan.header["spec"]["split"] = "confirmatory"
    monkeypatch.setattr(plan_mod, "load_plan", lambda p: plan)
    monkeypatch.setattr(inputs, "_split_task_ids", lambda split: None)
    return ["--plan", str(path), "--out", str(tmp_path / "runs"), "--dry-run", "--i-have-preregistered", "10.1234/abc"]


def test_confirmatory_drift_names_every_pin(tmp_path, monkeypatch, capsys):
    argv = confirmatory_plan(tmp_path, monkeypatch)
    monkeypatch.setattr(plan_mod, "check_pins", lambda planned, live: [
        {"pin": "python", "planned": "3.11", "live": "3.12"},
        {"pin": "tanabesugano", "planned": "1.9.0", "live": "2.0.0"}])
    with pytest.raises(SystemExit) as e:
        runner.main(argv)
    assert e.value.code == 2
    assert capsys.readouterr().err == ("runner: pinned environment drifted from the plan (confirmatory aborts): "
                                       "python: planned '3.11', live '3.12'; tanabesugano: planned '1.9.0', "
                                       "live '2.0.0'\n")


def test_a_confirmatory_manifest_records_only_the_number_of_tasks(tmp_path, monkeypatch):
    argv = confirmatory_plan(tmp_path, monkeypatch)
    monkeypatch.setattr(plan_mod, "check_pins", lambda planned, live: [])
    stub_runs(monkeypatch, answered)
    assert runner.main(argv) == 0
    m = read(tmp_path / "runs" / "MANIFEST.json")
    assert m["tasks"] == 1 and m["plan_sealed"] is True and m["plan_file"] is None


def run_plan_recording_the_system_prompt(tmp_path, monkeypatch, plan, extra=()):
    """Run `plan` (a written plan file); returns the system prompt text the model got, per call."""
    seen: list[str] = []

    def fake(argv, prompt, env, transcript, cond, model, *, timeout_s, disallowed):
        seen.append(pathlib.Path(argv[argv.index("--system-prompt-file") + 1]).read_text(encoding="utf-8"))
        transcript = pathlib.Path(transcript)
        transcript.parent.mkdir(parents=True, exist_ok=True)
        transcript.write_text("{}\n", encoding="utf-8")
        return answered({"model": model}), []

    monkeypatch.setattr(runner, "execute_with_retries", fake)
    argv = ["--plan", str(tmp_path / "plan.jsonl"), "--out", str(tmp_path / "runs"), "--dry-run", *extra]
    assert runner.main(argv) == 0
    return seen


def test_the_model_gets_the_system_prompt_of_the_plan_not_the_live_file(tmp_path, monkeypatch, capsys):
    plan = make_plan(tmp_path / "plan.jsonl")
    live = (pathlib.Path(plan_mod.__file__).parent.parent / "data" / plan.runs[0]["system_prompt_file"]).read_text(
        encoding="utf-8")
    for r in plan.runs:  # the package file is edited after the plan was built: the plan keeps the earlier text
        r["system_prompt_text"] = "THE TEXT OF THE PLAN\n" + live
        r["system_prompt_sha256"] = plan_mod.sha256_text(r["system_prompt_text"])
    monkeypatch.setattr(plan_mod, "load_plan", lambda p: plan)
    seen = run_plan_recording_the_system_prompt(tmp_path, monkeypatch, plan)
    assert seen == ["THE TEXT OF THE PLAN\n" + live]
    m = read(tmp_path / "runs" / "MANIFEST.json")
    assert m["pin_drift"] == [] and "WARNING pin drift" not in capsys.readouterr().err
    argv = meta_of(tmp_path / "runs", plan.runs[0])["argv"]
    assert argv[argv.index("--system-prompt-file") + 1] == (
        f"<OUT>/system-prompts/system-prompt-{plan.runs[0]['system_prompt_sha256'][:16]}.txt")
    kept = tmp_path / "runs" / "system-prompts" / f"system-prompt-{plan.runs[0]['system_prompt_sha256'][:16]}.txt"
    assert kept.read_text(encoding="utf-8") == "THE TEXT OF THE PLAN\n" + live  # the run folder keeps what was sent


def test_a_prompt_file_that_is_gone_does_not_matter_the_plan_holds_the_text(tmp_path, monkeypatch, capsys):
    plan = make_plan(tmp_path / "plan.jsonl")
    plan.runs[0]["system_prompt_file"] = "prompts/does-not-exist.txt"
    monkeypatch.setattr(plan_mod, "load_plan", lambda p: plan)
    seen = run_plan_recording_the_system_prompt(tmp_path, monkeypatch, plan)
    assert seen == [plan.runs[0]["system_prompt_text"]]
    assert "WARNING pin drift" not in capsys.readouterr().err


# ------------------------------------------------------------------ every console line is flushed
def test_every_line_of_a_dry_run_is_flushed(tmp_path, console):
    assert dry(tmp_path / "runs") == 0
    printed = flushed(console)
    assert printed[-2].startswith("[1/1] ") and printed[-1].startswith("done=1 rate_limited=0 skipped=0 ")


def test_the_budget_line_is_flushed(tmp_path, monkeypatch, console):
    monkeypatch.setenv("FAKE_COST_USD", "0.7")
    dry(tmp_path / "runs", limit=3, budget=1.0)
    assert "budget reached (spent USD 1.4000 of 1.00); stopping cleanly" in flushed(console)


def test_the_interrupt_line_is_flushed(tmp_path, monkeypatch, console):
    def interrupt(*a, **k):
        raise KeyboardInterrupt

    monkeypatch.setattr(runner, "execute_with_retries", interrupt)
    assert dry(tmp_path / "runs") == 130
    assert "interrupted; manifest written" in flushed(console)


def test_the_line_about_a_lost_readme_is_flushed(tmp_path, monkeypatch, console):
    def crash(*a, **k):
        monkeypatch.setattr(inputs, "write_readme", no_readme)  # only the final README fails
        raise RuntimeError("boom")

    monkeypatch.setattr(runner, "execute_with_retries", crash)
    with pytest.raises(RuntimeError, match="boom"):
        dry(tmp_path / "runs")
    assert "could not write the final manifest or README: disk full" in flushed(console)


@pytest.mark.parametrize("rec, reusable, line", [
    ({"passed": True, "reasons": [], "cost_usd": 0.0}, None,
     "sandbox probe: running (one real call, cost counts toward the budget)"),
    (None, {"passed": True, "reasons": [], "cost_usd": 0.0},
     "sandbox probe: reusing sandbox_probe.json (version and settings hash match)"),
    ({"passed": None, "reasons": ["x"], "cost_usd": 0.0}, None,
     "sandbox probe NOT EVALUABLE: condition B is not run now and not marked failed; --resume probes again. "
     "sandbox probe not evaluable: x"),
    ({"passed": False, "reasons": ["x"], "cost_usd": 0.0}, None,
     "sandbox probe FAILED: condition B is skipped. builtin sandbox probe failed: x"),
    ({"passed": True, "reasons": [], "cost_usd": 5.0}, None,
     "budget reached after the sandbox probe; stopping cleanly"),
], ids=["probe", "reuse", "not-evaluable", "failed", "budget"])
def test_the_sandbox_lines_are_flushed(tmp_path, real_mode, monkeypatch, console, rec, reusable, line):
    stub_check(monkeypatch, rec, reusable=reusable)
    real(tmp_path, budget=5.0)
    assert line in flushed(console)


# ------------------------------------------------------------------ a resumed cell that aborts keeps its finished runs
def _finished_run_set_with_one_open_run(tmp_path):
    """Three tasks of cell A are finished; the transcript of the second one is removed again (an open run)."""
    out = tmp_path / "runs"
    assert dry(out, limit=3) == 0
    runs = plan_runs(out)
    (out / HAIKU / "A" / "medium" / f"{runs[1]['task_id']}-k1.jsonl").unlink()
    return out, runs


def test_resume_counts_finished_runs_after_an_aborted_run_as_skipped_and_keeps_their_hash(tmp_path, monkeypatch):
    out, runs = _finished_run_set_with_one_open_run(tmp_path)
    monkeypatch.setenv("FAKE_BAD_INIT", "1")  # the open run gets an init mismatch: its cell aborts
    assert dry(out, limit=3, extra=("--resume",)) == 1
    m = read(out / "MANIFEST.json")
    assert (m["counts"]["skipped"], m["counts"]["aborted"]) == (2, 1)
    third = out / HAIKU / "A" / "medium" / f"{runs[2]['task_id']}-k1.jsonl"
    assert m["transcripts"][runs[2]["run_id"]] == hashlib.sha256(third.read_bytes()).hexdigest()


def test_a_budget_stop_after_an_aborted_run_counts_the_finished_runs_as_skipped(tmp_path, monkeypatch):
    out = tmp_path / "runs"
    assert dry(out, conds="A,C", limit=2) == 0  # plan order: t1/A, t1/C, t2/A, t2/C
    first, second, *_ = plan_runs(out)
    for r in (first, second):  # t1/A and t1/C are open again; t2/A and t2/C stay finished
        (out / HAIKU / r["condition"] / "medium" / f"{r['task_id']}-k1.jsonl").unlink()
    monkeypatch.setenv("FAKE_BAD_INIT", "1")
    # t1/A aborts its cell and is charged the cap (1.0): the budget stops before t1/C. The finished t2/A is skipped,
    # not "aborted", although its cell aborted in this invocation
    assert dry(out, conds="A,C", limit=2, budget=1.0, extra=("--resume", "--per-call-usd", "1")) == 1
    c = read(out / "MANIFEST.json")["counts"]
    assert (c["skipped"], c["aborted"], c["not_run_budget"]) == (2, 1, 1)


# ------------------------------------------------------------------ two invocations on one run folder
def test_write_json_atomic_uses_a_temp_name_of_its_own_per_write(tmp_path, monkeypatch):
    names = []
    real_replace = pathlib.Path.replace

    def spy(self, target):
        names.append(self.name)
        return real_replace(self, target)

    encodings = []
    real_write = pathlib.Path.write_text

    def spy_write(self, data, encoding=None, errors=None, newline=None):
        encodings.append(encoding)
        return real_write(self, data, encoding, errors, newline)

    monkeypatch.setattr(pathlib.Path, "replace", spy)
    monkeypatch.setattr(pathlib.Path, "write_text", spy_write)
    path = tmp_path / "MANIFEST.json"
    runner.write_json_atomic(path, {"a": 1})
    runner.write_json_atomic(path, {"a": 2})
    assert encodings == ["utf-8", "utf-8"]
    assert len(set(names)) == 2 and "MANIFEST.json.tmp" not in names
    assert read(path) == {"a": 2} and sorted(p.name for p in tmp_path.iterdir()) == ["MANIFEST.json"]


def test_a_second_invocation_on_a_locked_run_folder_is_refused(tmp_path, capsys):
    import fcntl

    out = tmp_path / "runs"
    assert dry(out) == 0
    with open(out / ".run.lock", "a", encoding="utf-8") as held:  # the first invocation, still running
        fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
        before = sorted(p.name for p in out.iterdir())
        with pytest.raises(SystemExit) as e:
            dry(out, extra=("--resume",))
        assert e.value.code == 2
        assert "another tsbench run is writing to" in capsys.readouterr().err
        assert sorted(p.name for p in out.iterdir()) == before  # it wrote nothing
    assert dry(out, extra=("--resume",)) == 0  # the lock is gone with the first invocation


def test_the_lock_is_released_when_the_invocation_ends(tmp_path):
    import fcntl

    out = tmp_path / "runs"
    assert dry(out) == 0
    with open(out / ".run.lock", "a", encoding="utf-8") as probe:
        fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)  # raises BlockingIOError when the runner kept it


# ------------------------------------------------------ a gateway run is not counted in USD: the estimate is not spent
QWEN = "qwen3.5-397b-a17b"


def gateway_run(out, *, k=3, budget=2.0, limit=1, extra=()):
    return runner.main(["--split", "pilot", "--models", QWEN, "--conditions", "A", "--effort", "medium", "--k", str(k),
                        "--budget-usd", str(budget), "--out", str(out), "--dry-run", "--limit", str(limit),
                        "--gateway", *extra])


def test_a_gateway_run_books_the_estimate_of_claude_code_apart_from_the_spent_total(tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_COST_USD", "1")  # Claude Code's price estimate for an unknown model
    out = tmp_path / "runs"
    assert gateway_run(out) == 0
    m = read(out / "MANIFEST.json")
    assert (m["counts"]["done"], m["counts"]["not_run_budget"], m["stopped_by_budget"]) == (3, 0, False)
    assert m["total_cost_usd"] == 0 and m["estimated_cost_usd"] == 3.0


def test_a_gateway_run_gives_no_per_call_cap_to_claude(tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_COST_USD", "1")
    out = tmp_path / "runs"
    assert gateway_run(out, k=1, extra=("--per-call-usd", "0.5")) == 0
    (r,) = plan_runs(out)
    argv = read(out / QWEN / "A" / "medium" / f"{r['task_id']}-k1.meta.json")["argv"]
    assert "--max-budget-usd" not in argv


def test_a_resumed_gateway_run_does_not_spend_the_estimate_of_the_finished_runs(tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_COST_USD", "1")
    out = tmp_path / "runs"
    assert gateway_run(out, k=2) == 0
    assert gateway_run(out, k=3, extra=("--resume",)) == 0
    m = read(out / "MANIFEST.json")
    assert m["counts"]["skipped"] == 2 and m["counts"]["done"] == 1 and m["stopped_by_budget"] is False
    assert m["total_cost_usd"] == 0 and m["estimated_cost_usd"] == 3.0


def test_a_run_stopped_by_the_budget_does_not_exit_0(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("FAKE_COST_USD", "0.7")
    out = tmp_path / "runs"
    assert dry(out, limit=3, budget=1.0) == runner.EX_TEMPFAIL  # the matrix is cut: --resume with a larger budget
    m = read(out / "MANIFEST.json")
    assert m["stopped_by_budget"] is True and m["counts"]["not_run_budget"] == 1
    assert "budget reached" in capsys.readouterr().out


# ------------------------------------------------------------------ the endpoint of a gateway run is recorded
def test_a_gateway_run_records_and_repeats_the_endpoint_it_used(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://user:secret@localhost:4000/v1")  # LiteLLM, contrib/gateway
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "sk-never-recorded")
    out = tmp_path / "runs"
    assert gateway_run(out, k=1) == 0
    assert read(out / "MANIFEST.json")["args"]["gateway_url"] == "http://localhost:4000"
    commands = (out / "inputs" / "commands.sh").read_text(encoding="utf-8")
    assert "export ANTHROPIC_BASE_URL=http://localhost:4000\n" in commands
    assert "academiccloud" not in commands and "secret" not in commands and "sk-never-recorded" not in commands
    readme = (out / "README.md").read_text(encoding="utf-8")
    assert "gateway localhost:4000" in readme and "GWDG" not in readme


def test_a_gateway_run_without_a_base_url_in_the_environment_records_the_default_endpoint(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
    out = tmp_path / "runs"
    assert gateway_run(out, k=1) == 0
    assert read(out / "MANIFEST.json")["args"]["gateway_url"] == "https://chat-ai.academiccloud.de"
    assert "export ANTHROPIC_BASE_URL=https://chat-ai.academiccloud.de\n" in (
        out / "inputs" / "commands.sh").read_text(encoding="utf-8")
    assert "gateway" in (out / "README.md").read_text(encoding="utf-8")


def test_a_run_without_a_gateway_records_no_gateway_url(tmp_path):
    out = tmp_path / "runs"
    assert dry(out) == 0
    assert "gateway_url" not in read(out / "MANIFEST.json")["args"]
