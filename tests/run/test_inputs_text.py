"""The whole text of commands.sh and README.md, line for line (the files a person reads and runs)."""

from __future__ import annotations

import json
import pathlib
from types import SimpleNamespace

import pytest

from tsbench import plan as plan_mod
from tsbench.run import inputs, runner

HAIKU = "claude-haiku-5-5"


@pytest.fixture(autouse=True)
def fake_venv(monkeypatch, tmp_path_factory):
    d = tmp_path_factory.getbasetemp() / "fake-venv-B-inputs"
    (d / "bin").mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("TSBENCH_B_VENV", str(d))  # never the real venv-B


def dry(out: pathlib.Path) -> None:
    assert runner.main(["--split", "pilot", "--models", HAIKU, "--conditions", "A", "--effort", "medium", "--k", "1",
                        "--budget-usd", "1", "--out", str(out), "--dry-run", "--limit", "1"]) == 0


COMMANDS_SH = """\
#!/usr/bin/env bash
# Run set: claude-haiku-5-5 | conditions A | effort medium | k=1 | pilot (1 tasks) | dry run
# Written by `tsbench run` (tsbench {version}, commit {commit}) at {start}.
# plan_id {plan_id}
#
# Keys: this file holds no key or token, only variable NAMES. They come from your shell, e.g. from the key file:
# `set -a; . "${{TSBENCH_KEY_FILE:-$HOME/.config/tsbench/env}}"; set +a` (TSMCP_ANTHROPIC_API_KEY: Anthropic API,
# GWDG_API_KEY: gateway). A dry run (--dry-run, the fake claude) needs no key.
#
#   bash inputs/commands.sh [TARGET]   run the whole run set again into TARGET (default: <run set>-rerun)
#   continuing THIS run set instead: see README.md (`tsbench run ... --resume`)
set -euo pipefail
HERE="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
OUT="${{1:-$(dirname "$HERE")-rerun}}"
TSBENCH="${{TSBENCH:-tsbench}}"
# the invocation (host paths as placeholders): tsbench run --split pilot --models claude-haiku-5-5 --conditions A \
--effort medium --k 1 --budget-usd 1 --out <OUT> --dry-run --limit 1

# environment (names only)
unset ANTHROPIC_BASE_URL ANTHROPIC_AUTH_TOKEN
export FAKE_COST_USD=0.25

# 1. the plan, rebuilt from its header's spec (the run below uses the stored plan.jsonl anyway)
"$TSBENCH" plan build --split pilot --models claude-haiku-5-5 --conditions A --effort medium --k 1 --budget-usd 1.0 \
--limit 1 --out-plan "$OUT/inputs/rebuilt/plan.jsonl"
grep -q '"plan_id": "{plan_id}"' "$OUT/inputs/rebuilt/plan.jsonl" || echo "WARNING: the rebuilt plan has another \
plan_id (task set or code changed); the run uses the stored plan" >&2

# 2. the run
"$TSBENCH" run --split pilot --models claude-haiku-5-5 --conditions A --effort medium --k 1 --limit 1 --budget-usd 1.0 \
--out "$OUT" --dry-run
"""


def test_commands_sh_whole_text(tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_COST_USD", "0.25")
    out = tmp_path / "runs"
    dry(out)
    m = json.loads((out / "MANIFEST.json").read_text(encoding="utf-8"))
    expected = COMMANDS_SH.format(version=inputs.tsbench_version(), commit=m["git_commit"] or "unknown",
                                  start=m["start_time_utc"], plan_id=m["plan_id"])
    assert (out / "inputs" / "commands.sh").read_text(encoding="utf-8") == expected
    assert json.loads((out / "run_set.json").read_text(encoding="utf-8")) == {
        "title": "claude-haiku-5-5 | conditions A | effort medium | k=1 | pilot (1 tasks) | dry run"}


def test_commands_sh_without_a_commit_says_unknown(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "git_output", lambda repo, *args: None)
    out = tmp_path / "runs"
    dry(out)
    text = (out / "inputs" / "commands.sh").read_text(encoding="utf-8")
    assert f"# Written by `tsbench run` (tsbench {inputs.tsbench_version()}, commit unknown) at " in text


def header(**spec):
    return {"plan_id": "p" * 64, "spec": {"split": "pilot", "models": [HAIKU], "conditions": ["A"],
                                          "efforts": ["low"], "k": 1, "budget_usd": 2.0, **spec}}


def test_commands_text_takes_the_gateway_from_the_plan_spec_and_names_the_rebuild_reason():
    text = inputs.commands_text(title="T", given={"plan": "x.jsonl", "dry_run": False}, header=header(gateway=True),
                                sealed=True, rebuild_reason="R", started_utc="S", version="V", git_commit="C",
                                original="tsbench run --plan x.jsonl")
    lines = text.splitlines()
    assert lines[1] == "# Run set: T" and lines[2] == "# Written by `tsbench run` (tsbench V, commit C) at S."
    assert lines[3] == "# plan_id " + "p" * 64
    assert lines[15] == "# the invocation (host paths as placeholders): tsbench run --plan x.jsonl"
    env = lines[lines.index("# environment (names only)") + 1: lines.index("# environment (names only)") + 4]
    assert env == ["export ANTHROPIC_BASE_URL=" + inputs.GATEWAY_URL,
                   'export ANTHROPIC_AUTH_TOKEN="${GWDG_API_KEY:?set GWDG_API_KEY (see '
                   '${TSBENCH_KEY_FILE:-$HOME/.config/tsbench/env})}"',
                   "unset ANTHROPIC_API_KEY TSMCP_ANTHROPIC_API_KEY"]
    assert "# 1. the plan is not rebuilt here: R; inputs/plan.sealed.json is the input" in lines
    assert lines[-1] == ('"$TSBENCH" run --plan "${TSBENCH_CLEAR_PLAN:?path of the clear plan with plan_id '
                         + "p" * 64 + ' (kept outside the repo)}" --out "$OUT"')
    assert text.endswith("\n") and not text.endswith("\n\n")


def test_commands_text_dry_run_without_gateway_has_no_key_line():
    text = inputs.commands_text(title="T", given={"split": "pilot", "dry_run": True}, header=header(), sealed=False,
                                rebuild_reason="R", started_utc="S", version="V", git_commit=None, original="o",
                                fake_env={"FAKE_SEED": "a b"})
    lines = text.splitlines()
    i = lines.index("# environment (names only)")
    assert lines[i + 1: i + 4] == ["unset ANTHROPIC_BASE_URL ANTHROPIC_AUTH_TOKEN", "export FAKE_SEED='a b'", ""]
    assert "# 1. the plan is not rebuilt here: R; inputs/plan.jsonl is the input" in lines


def test_commands_text_rebuilt_sealed_plan_checks_the_sealed_name():
    text = inputs.commands_text(title="T", given={"plan": "x"}, header=header(), sealed=True, rebuild_reason=None,
                                started_utc="S", version="V", git_commit="C", original="o")
    assert ("# 1. the plan, rebuilt from its header's spec (the run below uses the stored plan.sealed.json anyway)"
            in text.splitlines())
    assert "--out-plan \"$OUT/inputs/rebuilt/plan.jsonl\"" in text
    assert "grep -q '\"plan_id\": \"" + "p" * 64 + "\"' \"$OUT/inputs/rebuilt/plan.sealed.json\" ||" in text


# ------------------------------------------------------------------ README.md
README = """\
# Run set: TITLE

## What was run

- models: m1, m2
- conditions: A, C (A no tools, B Bash in a sandbox, C MCP server)
- effort: low, high; k = 3
- tasks: 2 of the pilot split
- plan_id: `PID`
- Anthropic API

## When

- start (UTC): T0
- end (UTC): T1
- state: finished

## Runs

- planned: 4
- done in this invocation: 3
- skipped (finished in an earlier invocation, --resume): 1

Total cost: USD 1.2346 (run-set budget USD 5.0)

## Inputs (next to the outputs)

- `inputs/commands.sh`: the command lines that made this run set (keys by name only)
- `inputs/plan.jsonl`: the plan (byte for byte)
- `inputs/hashes.json`: task set, plan, system prompts, answer schemas, sandbox settings, B stack, versions

## Re-run

Run the whole run set again (into `<this folder>-rerun`, or a folder you name):

    bash inputs/commands.sh [TARGET]

Continue this run set (finished runs are skipped), from inside this folder:

    RESUME

## Outputs

- transcripts: `<model>/<condition>/<effort>/<task_id>-k<k>.jsonl` (the raw stream-json of `claude -p`), each with a \
`.meta.json` sidecar (argv, cost, flags); earlier attempts as `.attempt<N>.jsonl`; harvested images in `.artifacts/`
- `MANIFEST.json`: counts, cost, versions, pins and the sha256 of every transcript
- scores: `tsbench score --runs <this folder>` writes `scores.csv` here
"""


def manifest(**kw) -> dict:
    m = {"models_requested": ["m1", "m2"], "conditions": ["A", "C"], "effort": ["low", "high"], "k": 3,
         "tasks": ["t1", "t2"], "split": "pilot", "plan_id": "PID", "start_time_utc": "T0", "end_time_utc": "T1",
         "finished": True, "total_cost_usd": 1.23456, "budget_usd": 5.0,
         "counts": {"planned": 4, "done": 3, "skipped": 1}}
    return {**m, **kw}


def readme(m, **kw) -> str:
    args = {"title": "TITLE", "gateway": False, "dry_run": False, "sealed": False, "resume_cmd": "RESUME",
            "running": False, **kw}
    return inputs.readme_text(m, **args)


def test_readme_whole_text():
    assert readme(manifest()) == README


def test_readme_sealed_gateway_running():
    lines = readme(manifest(tasks=7), gateway=True, sealed=True, running=True).splitlines()
    assert "- tasks: 7 of the pilot split" in lines
    assert "- plan_id: `PID` (sealed: the prompts are not stored here)" in lines
    assert "- gateway" in lines and "- end (UTC): (running)" in lines and "- state: running" in lines
    assert "Total cost: not counted in USD: gateway" in lines
    assert "- `inputs/plan.sealed.json`: the plan (sealed header only)" in lines


def test_readme_dry_run_line():
    lines = readme(manifest(), dry_run=True).splitlines()
    assert "- Anthropic API; dry run with the fake claude" in lines
    assert "Total cost: none: dry run (the fake claude, no API call)" in lines


@pytest.mark.parametrize("extra,state", [
    ({"interrupted": True}, "interrupted"),
    ({"finished": False}, "stopped by an error"),
    ({"stop": {"reason": "quota_exhausted", "scope": "daily"}}, "stopped by the quota (daily cap)"),
    ({"stop": {"reason": "quota_exhausted", "scope": "monthly"}}, "stopped by the quota (monthly cap)"),
    ({"stop": {"reason": "quota_exhausted", "scope": None}}, "stopped by the quota"),
    ({"stop": {"reason": "other", "scope": "daily"}}, "finished"),
    ({"stopped_by_budget": True}, "stopped by the budget"),
])
def test_readme_state(extra, state):
    assert f"- state: {state}" in readme(manifest(**extra)).splitlines()


def test_status_lines_every_count_and_the_rest():
    m = {"counts": {"planned": 20, "done": 1, "skipped": 2, "rate_limited": 3, "aborted": 1, "not_run_sandbox": 4,
                    "not_run_probe_not_evaluable": 5, "not_run_quota": 1, "not_run_budget": 1},
         "aborted_cells": [{"model": "m", "condition": "A", "effort": "low", "reasons": ["r1", "r2"]}],
         "budget_usd": 3.0, "end_time_utc": "T", "finished": True}
    assert inputs.status_lines(m) == [
        "- planned: 20", "- done in this invocation: 1",
        "- skipped (finished in an earlier invocation, --resume): 2",
        "- rate limited (HTTP 429, not answered): 3",
        "- not run, cell aborted (the init event did not match the condition): 1 (m/A/low: r1; r2)",
        "- not run, the sandbox probe failed so condition B was skipped: 4",
        "- not run, the sandbox probe could not be evaluated so condition B was skipped: 5",
        "- not run, the quota was used up: 1",
        "- not run, the run-set budget (USD 3.0) was reached: 1",
        "- not started: 2",
    ]


@pytest.mark.parametrize("extra,why", [
    ({"interrupted": True}, "interrupted (Ctrl-C) before they started"),
    ({"end_time_utc": None}, "not reached yet (the run is still going)"),
    ({"finished": False}, "not reached yet (the run is still going)"),
])
def test_status_lines_say_why_the_rest_did_not_run(extra, why):
    m = {"counts": {"planned": 3, "done": 1}, "end_time_utc": "T", "finished": True, **extra}
    assert inputs.status_lines(m)[-1] == f"- {why}: 2"


def test_status_lines_of_an_empty_manifest():
    assert inputs.status_lines({}) == ["- planned: 0", "- done in this invocation: 0",
                                       "- skipped (finished in an earlier invocation, --resume): 0"]


def test_write_readme_takes_the_gateway_from_the_plan_spec(tmp_path):
    plan_obj = SimpleNamespace(header=header(gateway=True))
    inputs.write_readme(tmp_path, given={"plan": "x", "dry_run": True}, plan_obj=plan_obj, sealed=False,
                        manifest=manifest())
    lines = (tmp_path / "README.md").read_text(encoding="utf-8").splitlines()
    assert lines[0] == ("# Run set: m1, m2 | conditions A,C | effort low, high | k=3 | pilot (2 tasks) | gateway"
                        " | dry run")
    assert "- gateway; dry run with the fake claude" in lines and "- state: finished" in lines
    assert "    tsbench run --plan inputs/plan.jsonl --out . --dry-run --resume" in lines


def test_write_readme_without_gateway(tmp_path):
    inputs.write_readme(tmp_path, given={"split": "pilot"}, plan_obj=SimpleNamespace(header=header()), sealed=False,
                        manifest=manifest(), running=True)
    lines = (tmp_path / "README.md").read_text(encoding="utf-8").splitlines()
    assert "- Anthropic API" in lines and "- state: running" in lines
    assert lines[0] == "# Run set: m1, m2 | conditions A,C | effort low, high | k=3 | pilot (2 tasks)"


def test_plan_name_constants():
    assert (plan_mod.PLAN_NAME, plan_mod.SEALED_NAME) == ("plan.jsonl", "plan.sealed.json")
