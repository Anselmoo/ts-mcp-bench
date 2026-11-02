"""Tests for the inputs a run set stores next to its outputs (src/tsbench/run/inputs.py).

Dry runs only (the fake claude): no network, no key. A sentinel stands in for every key variable and must never appear
in a written file.
Run: python -m pytest tests/run/test_inputs.py -q
"""
from __future__ import annotations

import json
import pathlib
import stat
import subprocess
import sys

import pytest

from tsbench import plan as P
from tsbench.conditions.sandbox import KEY_VARS
from tsbench.run import inputs, runner
from tsbench.score.run_sets import discover_run_sets
from tsbench.tasks import load

HAIKU = "claude-haiku-5-5"
GATEWAY_MODEL = "gwdg-qwen3.5-397b"
SENTINEL = "sk-SENTINEL-never-written-0123456789"
FIXED_TIME = "2026-10-24T00:00:00+00:00"


@pytest.fixture(autouse=True)
def sentinel_keys(monkeypatch, tmp_path_factory):
    d = tmp_path_factory.getbasetemp() / "fake-venv-B-inputs"
    (d / "bin").mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("TSBENCH_B_VENV", str(d))  # never the real venv-B
    for name in KEY_VARS:
        monkeypatch.setenv(name, SENTINEL)


def dry(out, *extra, models=(HAIKU,), conds="A,B,C", k=1, limit=2):
    return runner.main(["--split", "pilot", "--models", ",".join(models), "--conditions", conds, "--effort", "medium",
                        "--k", str(k), "--budget-usd", "5", "--limit", str(limit), "--out", str(out), "--dry-run",
                        *extra])


def written(out: pathlib.Path) -> list[pathlib.Path]:
    return [p for p in pathlib.Path(out).rglob("*") if p.is_file()]


def assert_no_key(out: pathlib.Path) -> None:
    for p in written(out):
        assert SENTINEL not in p.read_text(encoding="utf-8", errors="replace"), p


def bash_n(path: pathlib.Path) -> None:
    r = subprocess.run(["bash", "-n", str(path)], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr


def hashes(out) -> dict:
    return json.loads((out / "inputs" / "hashes.json").read_text(encoding="utf-8"))


def assert_hashes_match(out: pathlib.Path, header: dict) -> None:
    h = hashes(out)
    m = json.loads((out / "MANIFEST.json").read_text(encoding="utf-8"))
    for field in ("plan_id", "plan_sha256", "plan_file", "plan_file_sha256", "tasks", "system_prompts",
                  "answer_schemas", "sandbox_settings_sha256", "b_stack_sha256", "claude_cli_version",
                  "tanabesugano_version", "tsbench_version", "git_commit", "pins"):
        assert field in h, field
    assert h["plan_id"] == header["plan_id"] == m["plan_id"] and h["plan_sha256"] == m["plan_sha256"]
    assert h["pins"] == header["pins"] and h["tasks"]["plan_tasks_sha256"] == header["tasks_sha256"]
    assert h["tasks"]["split"] == header["spec"]["split"] and len(h["tasks"]["file_sha256"]) == 64
    assert h["tanabesugano_version"] == "2.0.0" and h["claude_cli_version"]["used"] == "fake"
    assert h["system_prompts"] and all(len(s["sha256"]) == 64 for s in h["system_prompts"])
    assert h["answer_schemas"] and all(len(s["sha256"]) == 64 for s in h["answer_schemas"])


# ------------------------------------------------------------------ pure helpers
def test_shell_line_quotes_words_but_not_raw_variables():
    assert inputs.shell_line(["tsbench", "run", "--out", inputs.Raw('"$OUT"'), "a b"]) == \
        "tsbench run --out \"$OUT\" 'a b'"


def test_env_lines_name_variables_and_never_carry_a_value():
    gw = "\n".join(inputs.env_lines(gateway=True, dry_run=False))
    assert 'export ANTHROPIC_AUTH_TOKEN="${GWDG_API_KEY:?' in gw and "unset ANTHROPIC_API_KEY" in gw
    # never inherited from the parent shell, which may point it at another endpoint
    assert f"export ANTHROPIC_BASE_URL={inputs.GATEWAY_URL}\n" in gw
    direct = "\n".join(inputs.env_lines(gateway=False, dry_run=False))
    assert "${TSMCP_ANTHROPIC_API_KEY:-${ANTHROPIC_API_KEY:?" in direct and "unset ANTHROPIC_BASE_URL" in direct
    assert "TSMCP" not in "\n".join(inputs.env_lines(gateway=False, dry_run=True))  # a dry run needs no key
    assert inputs.env_lines(gateway=False, dry_run=True, fake_env={"FAKE_COST_USD": "0.5"})[-1] == \
        "export FAKE_COST_USD=0.5"


def test_plan_reconstructible_only_from_the_spec():
    header = {"spec": {"split": "pilot", "limit": 2, "k": 2, "k_from": 2, "models": ["m"], "efforts": ["e"],
                       "conditions": ["A", "B"]}, "n_runs": 4}
    split = ["t1", "t2", "t3"]
    assert inputs.plan_reconstructible(header, ["t1", "t2"], split) is None
    assert "task selection" in inputs.plan_reconstructible(header, ["t2", "t3"], split)
    assert inputs.plan_reconstructible(header, None, split) is None  # sealed: 2 tasks x 2 conditions x 1 layer
    assert "run count" in inputs.plan_reconstructible({**header, "n_runs": 3}, None, split)
    assert inputs.plan_reconstructible(header, ["t1"], None)


def test_plan_build_argv_from_the_spec():
    header = {"spec": {"split": "confirmatory", "models": ["a", "b"], "conditions": ["A", "C"], "efforts": ["medium"],
                       "k": 3, "k_from": 2, "stage": "s2", "budget_usd": 7.0, "limit": None, "gateway": True,
                       "system_prompt_file": P.DEFAULT_SYSTEM_PROMPT}}
    argv = inputs.plan_build_argv(header, out_plan="p.jsonl", preregistered="10.1234/x")
    assert argv == ["tsbench", "plan", "build", "--split", "confirmatory", "--models", "a,b", "--conditions", "A,C",
                    "--effort", "medium", "--k", 3, "--k-from", 2, "--stage", "s2", "--budget-usd", 7.0, "--gateway",
                    "--i-have-preregistered", "10.1234/x", "--out-plan", "p.jsonl"]


def test_title_and_cost():
    m = {"models_requested": [GATEWAY_MODEL], "conditions": ["A", "C"], "effort": "high", "k": 2, "split": "pilot",
         "tasks": ["x", "y", "z"], "total_cost_usd": 1.25, "budget_usd": 10}
    assert inputs.title_of(m, gateway=True, dry_run=False) == \
        f"{GATEWAY_MODEL} | conditions A,C | effort high | k=2 | pilot (3 tasks) | gateway"
    assert inputs.cost_text(m, gateway=True, dry_run=False) == "not counted in USD: gateway"
    assert inputs.cost_text(m, gateway=False, dry_run=False).startswith("USD 1.2500")


def test_status_lines_say_why_runs_did_not_run():
    m = {"counts": {"planned": 10, "done": 4, "skipped": 1, "aborted": 2, "not_run_sandbox": 1, "not_run_budget": 1},
         "aborted_cells": [{"model": "m", "condition": "A", "effort": "e", "reasons": ["model mismatch"]}],
         "budget_usd": 3, "finished": False, "interrupted": True, "end_time_utc": "t"}
    text = "\n".join(inputs.status_lines(m))
    assert "model mismatch" in text and "sandbox probe failed" in text and "budget (USD 3)" in text
    assert "interrupted (Ctrl-C) before they started: 1" in text


# ------------------------------------------------------------------ dry runs
def test_pilot_dry_run_writes_its_inputs(tmp_path):
    out = tmp_path / "runs"
    assert dry(out) == 0
    for rel in ("inputs/commands.sh", "inputs/plan.jsonl", "inputs/hashes.json", "run_set.json", "README.md",
                "MANIFEST.json"):
        assert (out / rel).is_file(), rel
    assert (out / "inputs" / "plan.jsonl").read_bytes() == (out / "plan.jsonl").read_bytes()
    plan = P.load_plan(out / "inputs" / "plan.jsonl")
    assert_hashes_match(out, plan.header)
    cmd = out / "inputs" / "commands.sh"
    bash_n(cmd)
    assert cmd.stat().st_mode & stat.S_IXUSR
    text = cmd.read_text(encoding="utf-8")
    assert '"$TSBENCH" plan build --split pilot' in text and "--limit 2" in text and plan.plan_id in text
    assert '"$TSBENCH" run --split pilot' in text and '--out "$OUT" --dry-run' in text
    assert "${TSBENCH_KEY_FILE:-$HOME/.config/tsbench/env}" in text  # the key file by its variable, never read
    assert str(out) not in text  # a host path only as a placeholder
    assert_no_key(out)
    title = json.loads((out / "run_set.json").read_text(encoding="utf-8"))["title"]
    assert title == f"{HAIKU} | conditions A,B,C | effort medium | k=1 | pilot (2 tasks) | dry run"
    assert [rs.title for rs in discover_run_sets(tmp_path)] == [title]
    readme = (out / "README.md").read_text(encoding="utf-8")
    assert "- done in this invocation: 6" in readme and "state: finished" in readme and "(running)" not in readme
    assert "bash inputs/commands.sh" in readme and "tsbench run --plan inputs/plan.jsonl" in readme
    assert "--resume" in readme and "tsbench score --runs" in readme and "MANIFEST.json" in readme


def test_commands_sh_reruns_the_run_set(tmp_path):
    """`bash inputs/commands.sh TARGET` rebuilds the plan (same plan_id) and runs the stored plan into TARGET."""
    plan = P.build_plan(load("pilot")[:1], {"split": "pilot", "models": [HAIKU], "conditions": ["A"],
                                             "efforts": ["medium"], "k": 1, "budget_usd": 1.0, "limit": 1},
                        created_utc=FIXED_TIME)
    src = tmp_path / "plan" / "plan.jsonl"
    P.write_plan(plan, src, markdown=False)
    out = tmp_path / "runs"
    assert runner.main(["--plan", str(src), "--out", str(out), "--dry-run"]) == 0
    assert (out / "inputs" / "plan.jsonl").read_bytes() == src.read_bytes()
    text = (out / "inputs" / "commands.sh").read_text(encoding="utf-8")
    assert '"$TSBENCH" run --plan "$HERE/plan.jsonl" --out "$OUT" --dry-run' in text
    wrapper = tmp_path / "tsbench"
    wrapper.write_text(f'#!/bin/sh\nexec "{sys.executable}" -m tsbench.cli "$@"\n', encoding="utf-8")
    wrapper.chmod(0o755)
    target = tmp_path / "again"
    env = {k: v for k, v in __import__("os").environ.items() if k not in KEY_VARS}
    r = subprocess.run(["bash", str(out / "inputs" / "commands.sh"), str(target)], capture_output=True, text=True,
                       env={**env, "TSBENCH": str(wrapper)}, timeout=300, encoding="utf-8")
    assert r.returncode == 0, r.stderr[-2000:]
    assert "WARNING" not in r.stderr  # the rebuilt plan has the same plan_id
    assert P.load_plan(target / "inputs" / "rebuilt" / "plan.jsonl").plan_id == plan.plan_id
    assert json.loads((target / "MANIFEST.json").read_text(encoding="utf-8"))["counts"]["done"] == 1


def test_gateway_dry_run_sets_the_environment_by_name(tmp_path):
    out = tmp_path / "gw"
    assert dry(out, "--gateway", models=(GATEWAY_MODEL,), conds="A,C", limit=1) == 0
    text = (out / "inputs" / "commands.sh").read_text(encoding="utf-8")
    bash_n(out / "inputs" / "commands.sh")
    assert "export ANTHROPIC_BASE_URL=" in text and 'ANTHROPIC_AUTH_TOKEN="${GWDG_API_KEY' in text
    assert "unset ANTHROPIC_API_KEY" in text and "--gateway" in text
    assert "gateway" in json.loads((out / "run_set.json").read_text(encoding="utf-8"))["title"]
    assert "gateway" in (out / "README.md").read_text(encoding="utf-8")
    assert_hashes_match(out, P.load_plan(out / "plan.jsonl").header)
    assert hashes(out)["sandbox_settings_sha256"] is None and hashes(out)["b_stack_sha256"] is None  # no B
    assert_no_key(out)


def test_resume_appends_to_commands_and_refreshes_the_readme(tmp_path):
    out = tmp_path / "runs"
    assert dry(out, conds="A", limit=2) == 0
    first = (out / "inputs" / "commands.sh").read_text(encoding="utf-8")
    assert dry(out, "--resume", conds="A", limit=2) == 0
    text = (out / "inputs" / "commands.sh").read_text(encoding="utf-8")
    assert text.startswith(first) and text.count("# resumed at") == 1
    assert text.rstrip().endswith("--dry-run --resume")
    bash_n(out / "inputs" / "commands.sh")
    readme = (out / "README.md").read_text(encoding="utf-8")
    assert "- skipped (finished in an earlier invocation, --resume): 2" in readme
    # a larger k changes the plan_id: the earlier plan copy is kept, the resume line says so
    assert dry(out, "--resume", conds="A", limit=2, k=2) == 0
    text = (out / "inputs" / "commands.sh").read_text(encoding="utf-8")
    assert text.count("# resumed at") == 2 and "plan_id changed from" in text
    assert list((out / "inputs").glob("plan.prev-*.jsonl"))
    assert_hashes_match(out, P.load_plan(out / "inputs" / "plan.jsonl").header)
    assert "k=2" in json.loads((out / "run_set.json").read_text(encoding="utf-8"))["title"]
    assert_no_key(out)


def test_resume_of_a_run_set_without_inputs_writes_them(tmp_path):
    out = tmp_path / "runs"
    assert dry(out, conds="A", limit=1) == 0
    for p in (out / "inputs").iterdir():
        p.unlink()
    (out / "inputs").rmdir()
    assert dry(out, "--resume", conds="A", limit=1) == 0
    text = (out / "inputs" / "commands.sh").read_text(encoding="utf-8")
    assert "first written by this --resume" in text and text.count("# resumed at") == 1
    bash_n(out / "inputs" / "commands.sh")


def test_sealed_confirmatory_run_keeps_its_prompts_out_of_inputs(tmp_path):
    tasks = [dict(t, split="confirmatory") for t in load("pilot")[:2]]
    plan = P.build_plan(tasks, {"split": "confirmatory", "models": [HAIKU], "conditions": ["A"], "efforts": ["medium"],
                                "k": 1, "budget_usd": 1.0, "limit": 2}, created_utc=FIXED_TIME)
    clear = tmp_path / "clear" / "plan.jsonl"
    P.write_plan(plan, clear, markdown=False)
    out = tmp_path / "conf"
    assert runner.main(["--plan", str(clear), "--out", str(out), "--dry-run",
                        "--i-have-preregistered", "10.1234/x"]) == 0
    assert not (out / "inputs" / "plan.jsonl").exists()
    sealed = P.load_plan(out / "inputs" / "plan.sealed.json")
    assert sealed.header["sealed"] is True and sealed.runs == []
    assert (out / "inputs" / "plan.sealed.json").read_bytes() == (out / P.SEALED_NAME).read_bytes()
    assert_hashes_match(out, plan.header)
    assert hashes(out)["plan_sealed"] is True and hashes(out)["plan_file"] == "inputs/plan.sealed.json"
    cmd = out / "inputs" / "commands.sh"
    bash_n(cmd)
    text = cmd.read_text(encoding="utf-8")
    assert '--plan "${TSBENCH_CLEAR_PLAN:?' in text and "--i-have-preregistered 10.1234/x" in text
    files = [p for p in written(out / "inputs")] + [out / "README.md", out / "run_set.json"]
    for p in files:
        body = p.read_text(encoding="utf-8")
        for r in plan.runs:
            assert r["prompt"] not in body and r["task_id"] not in body and r["system_prompt_text"] not in body, p
    assert "sealed" in (out / "README.md").read_text(encoding="utf-8")
    assert_no_key(out)


# ------------------------------------------------------------------ README state and counts
def readme_of(**kw) -> str:
    manifest = {"counts": {"planned": 10, "done": 3}, "models_requested": [HAIKU], "conditions": ["A"],
                "effort": "medium", "k": 1, "split": "pilot", "start_time_utc": "t0", "end_time_utc": "t1",
                "finished": True, **kw}
    return inputs.readme_text(manifest, title="t", gateway=False, dry_run=True, sealed=False, resume_cmd="x",
                              running=False)


def test_readme_state_says_when_the_run_set_stopped_by_an_error():
    assert "- state: stopped by an error" in readme_of(finished=False)
    assert "- state: finished" in readme_of()
    assert "- state: finished" in readme_of(finished=None)  # a manifest without the key keeps working
    assert "- state: interrupted" in readme_of(finished=False, interrupted=True)
    assert "- state: stopped by the budget" in readme_of(stopped_by_budget=True)


def test_readme_state_says_when_the_quota_stopped_the_run_set():
    text = readme_of(stop={"reason": "quota_exhausted", "scope": "daily", "after_runs": 1})
    assert "- state: stopped by the quota (daily cap)" in text
    counted = readme_of(stop={"reason": "quota_exhausted", "scope": None, "after_runs": 3})
    assert "- state: stopped by the quota\n" in counted


def test_readme_counts_rate_limited_and_quota_runs_and_leaves_no_rest():
    counts = {"planned": 10, "done": 2, "rate_limited": 3, "not_run_quota": 4, "not_run_probe_not_evaluable": 1}
    text = readme_of(counts=counts, stop={"reason": "quota_exhausted", "scope": "daily", "after_runs": 1})
    assert "- rate limited (HTTP 429, not answered): 3" in text
    assert "- not run, the quota was used up: 4" in text
    assert "not started" not in text and "not reached" not in text  # 2 + 3 + 4 + 1 = 10, nothing is left over


# ------------------------------------------------------------------ exact values of the pure helpers
def test_run_argv_flag_forms():
    given = {"split": "pilot", "models": "m", "conditions": "A,B", "effort": "low", "k": 2, "limit": 5,
             "budget_usd": 3.5, "per_call_usd": 0.25, "dry_run": True, "gateway": True,
             "preregistered": "10.1/x", "b_venv": "/host/venv", "out": "/host/out"}
    assert inputs.run_argv(given, out_ref="OUT", plan_ref="PLAN", tsbench="ts") == [
        "ts", "run", "--split", "pilot", "--models", "m", "--conditions", "A,B", "--effort", "low", "--k", 2,
        "--limit", 5, "--budget-usd", 3.5, "--per-call-usd", 0.25, "--out", "OUT", "--dry-run", "--gateway",
        "--i-have-preregistered", "10.1/x"]
    assert inputs.run_argv({**given, "plan": "p.jsonl", "k": 0}, out_ref="OUT", plan_ref="PLAN", resume=True) == [
        "tsbench", "run", "--plan", "PLAN", "--budget-usd", 3.5, "--per-call-usd", 0.25, "--out", "OUT", "--dry-run",
        "--gateway", "--i-have-preregistered", "10.1/x", "--resume"]
    assert inputs.run_argv({"split": "pilot", "k": 0, "limit": None}, out_ref="O", plan_ref=None) == [
        "tsbench", "run", "--split", "pilot", "--k", 0, "--out", "O"]


def test_plan_build_argv_minimal_and_prompt_file():
    spec = {"split": "pilot", "models": ["a"], "conditions": ["A"], "efforts": ["low", "high"], "k": 1,
            "budget_usd": 2.0, "limit": 0, "gateway": False}
    assert inputs.plan_build_argv({"spec": spec}, out_plan="p", preregistered="10.1/x", tsbench="ts") == [
        "ts", "plan", "build", "--split", "pilot", "--models", "a", "--conditions", "A", "--effort", "low,high",
        "--k", 1, "--budget-usd", 2.0, "--limit", 0, "--out-plan", "p"]  # preregistered only for confirmatory
    other = {**spec, "system_prompt_file": "prompts/other.txt", "split": "confirmatory", "limit": None}
    assert inputs.plan_build_argv({"spec": other}, out_plan="p", preregistered=None, tsbench="ts") == [
        "ts", "plan", "build", "--split", "confirmatory", "--models", "a", "--conditions", "A", "--effort",
        "low,high", "--k", 1, "--budget-usd", 2.0, "--system-prompt-file", "prompts/other.txt", "--out-plan", "p"]
    default_prompt = {**other, "system_prompt_file": P.DEFAULT_SYSTEM_PROMPT}
    assert inputs.plan_build_argv({"spec": default_prompt}, out_plan="p", preregistered="10.1/y", tsbench="ts") == [
        "ts", "plan", "build", "--split", "confirmatory", "--models", "a", "--conditions", "A", "--effort",
        "low,high", "--k", 1, "--budget-usd", 2.0, "--i-have-preregistered", "10.1/y", "--out-plan", "p"]
    no_prompt_key = {k: v for k, v in other.items() if k != "system_prompt_file"}
    assert "--system-prompt-file" not in inputs.plan_build_argv({"spec": no_prompt_key}, out_plan="p",
                                                                preregistered=None)


def test_plan_reconstructible_counts_layers_and_the_limit():
    header = {"spec": {"split": "pilot", "k": 3, "models": ["m", "n"], "efforts": ["e", "f"],
                       "conditions": ["A", "B", "C"]}, "n_runs": 4 * 2 * 2 * 3 * 3}
    split = ["t1", "t2", "t3", "t4", "t5"]
    assert inputs.plan_reconstructible(header, None, split) == (
        "its run count does not match the spec over the whole split")  # 5 tasks, not 4
    assert inputs.plan_reconstructible(header, None, split[:4]) is None  # k_from defaults to 1: three layers
    with_from = {"spec": {**header["spec"], "k_from": 2}, "n_runs": 4 * 2 * 2 * 3 * 2}
    assert inputs.plan_reconstructible(with_from, None, split[:4]) is None
    limited = {"spec": {**header["spec"], "limit": 4}, "n_runs": header["n_runs"]}
    assert inputs.plan_reconstructible(limited, None, split) is None  # the first four of five
    assert inputs.plan_reconstructible(limited, ["t1", "t2", "t3", "t4"], split) is None
    assert inputs.plan_reconstructible(limited, ["t1", "t2", "t3", "t4", "t5"], split) == (
        "its task selection (--task-class / --task-ids) is not recorded in the plan header's spec")
    assert inputs.plan_reconstructible(header, ["t1", "t2", "t3", "t4", "t5"], split) is None  # no limit: all five
    assert inputs.plan_reconstructible({"spec": {"split": "pilot"}}, None, None) == (
        "the 'pilot' split could not be loaded")
    assert inputs.plan_reconstructible({"spec": {**header["spec"]}, "n_runs": 1}, None, split[:4]) == (
        "its run count does not match the spec over the whole split")


def test_env_lines_exact():
    assert inputs.env_lines(gateway=True, dry_run=True) == [
        f'export ANTHROPIC_BASE_URL={inputs.GATEWAY_URL}',
        'export ANTHROPIC_AUTH_TOKEN="${GWDG_API_KEY:-}"  # not needed for a dry run',
        "unset ANTHROPIC_API_KEY TSMCP_ANTHROPIC_API_KEY"]
    assert inputs.env_lines(gateway=True, dry_run=False)[1] == (
        'export ANTHROPIC_AUTH_TOKEN="${GWDG_API_KEY:?set GWDG_API_KEY (see '
        '${TSBENCH_KEY_FILE:-$HOME/.config/tsbench/env})}"')
    assert inputs.env_lines(gateway=False, dry_run=False) == [
        ': "${TSMCP_ANTHROPIC_API_KEY:-${ANTHROPIC_API_KEY:?set TSMCP_ANTHROPIC_API_KEY (see '
        '${TSBENCH_KEY_FILE:-$HOME/.config/tsbench/env})}}"',
        "unset ANTHROPIC_BASE_URL ANTHROPIC_AUTH_TOKEN"]
    assert inputs.env_lines(gateway=False, dry_run=True, fake_env={"B": "x y", "A": 1}) == [
        "unset ANTHROPIC_BASE_URL ANTHROPIC_AUTH_TOKEN", "export A=1", "export B='x y'"]


def test_plan_ref_resume_text_and_resume_cmd():
    assert inputs.plan_ref_for({}, False, "pid") == '"$HERE/plan.jsonl"'
    assert inputs.plan_ref_for({}, True, "pid") == (
        '"${TSBENCH_CLEAR_PLAN:?path of the clear plan with plan_id pid (kept outside the repo)}"')
    given = {"plan": "p", "budget_usd": 2}
    assert inputs.resume_text(given=given, sealed=False, plan_id="p1", at_utc="T", previous_plan_id=None) == (
        '\n# resumed at T\n"$TSBENCH" run --plan "$HERE/plan.jsonl" --budget-usd 2 --out "$OUT" --resume\n')
    assert inputs.resume_text(given=given, sealed=False, plan_id="p1", at_utc="T", previous_plan_id="p1"
                              ).startswith("\n# resumed at T\n")
    assert inputs.resume_text(given=given, sealed=False, plan_id="p2", at_utc="T", previous_plan_id="p1"
                              ).startswith("\n# resumed at T; plan_id changed from p1 to p2\n")
    flags = {"split": "pilot", "k": 1, "budget_usd": 2}
    sealed = inputs.resume_text(given=given, sealed=True, plan_id="p9", at_utc="T", previous_plan_id=None)
    assert sealed == ('\n# resumed at T\n"$TSBENCH" run --plan '
                      '"${TSBENCH_CLEAR_PLAN:?path of the clear plan with plan_id p9 (kept outside the repo)}" '
                      '--budget-usd 2 --out "$OUT" --resume\n')
    assert inputs._resume_cmd(flags, False) == "tsbench run --plan inputs/plan.jsonl --budget-usd 2 --out . --resume"
    assert inputs._resume_cmd(flags, True) == "tsbench run --split pilot --k 1 --budget-usd 2 --out . --resume"
    assert inputs._resume_cmd({**flags, "plan": "x"}, True) == (
        'tsbench run --plan "$TSBENCH_CLEAR_PLAN" --budget-usd 2 --out . --resume')


def test_hashes_take_planned_values_from_the_plan_and_live_ones_from_the_manifest():
    from types import SimpleNamespace

    runs = [{"system_prompt_file": "prompts/a.txt", "system_prompt_sha256": "s1", "answer_schema": "curve",
             "answer_schema_sha256": "c1"},
            {"system_prompt_file": "prompts/a.txt", "system_prompt_sha256": "s1", "answer_schema": None,
             "answer_schema_sha256": "f1"},
            {"system_prompt_file": "prompts/a.txt", "system_prompt_sha256": "s1", "answer_schema_sha256": "f1"}]
    header = {"spec": {"split": "pilot"}, "created_utc": "C", "schema_version": 3, "tasks_sha256": "T",
              "pins": {"a": 1}}
    plan = SimpleNamespace(header=header, runs=runs, plan_id="PID", sha256="PSHA")
    manifest = {"conditions": ["A", "B"], "sandbox_settings_sha256": "SB", "b_stack": {"digest": "BD"},
                "claude_version": "2.1", "tanabesugano_version": "2.0.0", "git_commit": "abc", "git_dirty": False}
    kw = {"plan_obj": plan, "plan_file_sha256": "PF", "tasks_file": "tasks/t.jsonl", "tasks_file_sha256": "TF",
          "split_sha256": "SS"}
    h = inputs.hashes(sealed=False, manifest=manifest, **kw)
    assert h == {"plan_id": "PID", "plan_sha256": "PSHA", "plan_file": "inputs/plan.jsonl", "plan_file_sha256": "PF",
                 "plan_sealed": False, "plan_created_utc": "C", "plan_schema_version": 3,
                 "tasks": {"file": "tasks/t.jsonl", "file_sha256": "TF", "split": "pilot", "split_sha256": "SS",
                           "plan_tasks_sha256": "T"},
                 "system_prompts": [{"resource": "prompts/a.txt", "sha256": "s1"}],
                 "answer_schemas": [{"name": "curve", "sha256": "c1"}, {"name": "fit", "sha256": "f1"}],
                 "sandbox_settings_sha256": "SB", "b_stack_sha256": "BD", "claude_cli_version": "2.1",
                 "tanabesugano_version": "2.0.0", "tsbench_version": inputs.tsbench_version(), "git_commit": "abc",
                 "git_dirty": False, "pins": {"a": 1}}
    sealed = inputs.hashes(sealed=True, manifest={**manifest, "conditions": ["A", "C"]}, **kw)
    assert sealed["plan_file"] == "inputs/plan.sealed.json" and sealed["plan_sealed"] is True
    assert sealed["sandbox_settings_sha256"] is None and sealed["b_stack_sha256"] is None  # no B, no B values
    assert inputs.hashes(sealed=False, manifest={}, **kw)["b_stack_sha256"] is None
    b_only = inputs.hashes(sealed=False, manifest={"conditions": ["B"]}, **kw)
    assert b_only["b_stack_sha256"] is None and b_only["sandbox_settings_sha256"] is None  # B without values


def test_split_line_sha256_and_tsbench_version_and_split_task_ids(monkeypatch):
    text = f"{'a' * 64}  tasks.jsonl\n{'b' * 64}  pilot\n{'c' * 64}  pilot-extra\n"
    assert inputs.split_line_sha256(text, "pilot") == "b" * 64
    assert inputs.split_line_sha256(text, "missing") is None
    assert inputs.split_line_sha256("", "pilot") is None
    assert inputs.split_line_sha256(f"{'d' * 64}  two  words\n", "two  words") == "d" * 64  # split at the first gap

    assert inputs.tsbench_version() == inputs.importlib.metadata.version("tsbench")

    monkeypatch.setattr(inputs.importlib.metadata, "version", lambda name: "9.9.9")
    assert inputs.tsbench_version() == "9.9.9"

    def missing(name):
        raise inputs.importlib.metadata.PackageNotFoundError(name)

    monkeypatch.setattr(inputs.importlib.metadata, "version", missing)
    import tsbench

    assert inputs.tsbench_version() == getattr(tsbench, "__version__", "unknown")
    monkeypatch.setattr(tsbench, "__version__", "1.2.3", raising=False)
    assert inputs.tsbench_version() == "1.2.3"
    monkeypatch.delattr(tsbench, "__version__")
    assert inputs.tsbench_version() == "unknown"

    import tsbench.tasks as tasks_mod

    monkeypatch.setattr(tasks_mod, "load", lambda split: (_ for _ in ()).throw(OSError("gone")))
    assert inputs._split_task_ids("pilot") is None
    monkeypatch.setattr(tasks_mod, "load", lambda split: (_ for _ in ()).throw(ValueError("bad")))
    assert inputs._split_task_ids("pilot") is None
    monkeypatch.setattr(tasks_mod, "load", lambda split: [{"id": "x"}, {"id": "y"}])
    assert inputs._split_task_ids("pilot") == ["x", "y"]


def test_small_text_helpers_and_atomic_write(tmp_path):
    assert inputs._join(["a", "b"]) == "a, b" and inputs._join(("a",)) == "a" and inputs._join("low") == "low"
    assert inputs._n_tasks({"tasks": ["x", "y"]}) == 2 and inputs._n_tasks({"tasks": 7}) == 7
    assert inputs._n_tasks({"tasks": None}) == 0 and inputs._n_tasks({}) == 0
    assert inputs.cost_text({}, gateway=False, dry_run=True) == "none: dry run (the fake claude, no API call)"
    assert inputs.cost_text({"total_cost_usd": None, "budget_usd": 5}, gateway=False, dry_run=False) == (
        "USD 0.0000 (run-set budget USD 5)")
    assert inputs.cost_text({"total_cost_usd": 0.5, "budget_usd": 5}, gateway=False, dry_run=False) == (
        "USD 0.5000 (run-set budget USD 5)")
    target = tmp_path / "deep" / "er" / "f.txt"
    inputs.write_text_atomic(target, "café\n")
    assert target.read_bytes() == "café\n".encode() and not (target.parent / "f.txt.tmp").exists()
    inputs.write_text_atomic(target, "new")
    assert target.read_text(encoding="utf-8") == "new"


def test_atomic_write_goes_through_a_tmp_file_next_to_the_target(tmp_path, monkeypatch):
    moves = []
    real_replace = pathlib.Path.replace

    def spy(self, target):
        moves.append((self.name, pathlib.Path(target).name, self.read_text(encoding="utf-8")))
        return real_replace(self, target)

    monkeypatch.setattr(pathlib.Path, "replace", spy)
    inputs.write_text_atomic(tmp_path / "out.txt", "body")
    inputs.write_text_atomic(tmp_path / "out.txt", "body")
    # a temp name of its own per write: two invocations on one folder cannot take each other's file away
    assert [m[1:] for m in moves] == [("out.txt", "body")] * 2
    names = [m[0] for m in moves]
    assert len(set(names)) == 2 and all(n.startswith("out.txt.") and n.endswith(".tmp") for n in names)
    assert "out.txt.tmp" not in names and sorted(p.name for p in tmp_path.iterdir()) == ["out.txt"]


def test_unreadable_task_hashes_file_leaves_the_task_hashes_empty(tmp_path, monkeypatch):
    """Only the copy of the hash file that inputs.py reads is missing; loading the tasks still works."""
    import tsbench.tasks as tasks_mod

    real = tasks_mod.hash_path

    def hash_path(*a, **k):
        caller = sys._getframe(1).f_code.co_filename
        return tmp_path / "gone-hashes.txt" if caller.endswith("inputs.py") else real(*a, **k)

    monkeypatch.setattr(tasks_mod, "hash_path", hash_path)
    out = tmp_path / "runs"
    assert dry(out, conds="A", limit=1) == 0
    tasks = hashes(out)["tasks"]
    assert tasks["file_sha256"] is None and tasks["split_sha256"] is None
    assert tasks["file"].startswith("tasks/") and tasks["split"] == "pilot"


def test_readme_names_a_stop_on_api_errors_and_counts_the_runs_not_started():
    counts = {"planned": 10, "done": 3, "not_run_api_errors": 7}
    text = readme_of(counts=counts, stop={"reason": "api_errors", "scope": None, "after_runs": 3})
    assert "- state: stopped by API errors\n" in text
    assert "- not run, API errors stopped the run set: 7" in text
    assert "not started" not in text and "not reached" not in text  # 3 + 7 = 10, nothing is left over


def test_env_lines_use_the_recorded_gateway_url():
    assert inputs.env_lines(gateway=True, dry_run=True, gateway_url="http://localhost:4000")[0] == (
        "export ANTHROPIC_BASE_URL=http://localhost:4000")
    assert inputs.env_lines(gateway=True, dry_run=True, gateway_url=None)[0] == (
        f"export ANTHROPIC_BASE_URL={inputs.GATEWAY_URL}")  # a manifest without the field: the default endpoint
    assert "ANTHROPIC_BASE_URL=http" not in "\n".join(inputs.env_lines(gateway=False, dry_run=True,
                                                                      gateway_url="http://localhost:4000"))


def test_title_and_readme_name_the_recorded_gateway(tmp_path):
    manifest = {"models_requested": ["m"], "conditions": ["A"], "effort": "low", "k": 1, "split": "pilot", "tasks": 1,
                "args": {"gateway": True, "gateway_url": "http://localhost:4000"}}
    assert inputs.title_of(manifest, gateway=True, dry_run=False).endswith("gateway localhost:4000")
    assert "GWDG" not in inputs.title_of(manifest, gateway=True, dry_run=False)
    plain = {**manifest, "args": {"gateway": True}}
    assert inputs.title_of(plain, gateway=True, dry_run=False).endswith("gateway")
    assert inputs.cost_text(manifest, gateway=True, dry_run=False) == "not counted in USD: gateway localhost:4000"
