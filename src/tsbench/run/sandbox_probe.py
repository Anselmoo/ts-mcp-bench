"""The sandbox probe of condition B: one real (or fake) model call that runs the probe script inside the sandbox.

    tsbench env sandbox --settings-only          # print the rendered sandbox settings
    tsbench env sandbox --probe --out DIR        # run the probe (one small paid call; needs a key)

The settings, the probe script and its evaluation are data in tsbench.conditions.sandbox; this module executes.

A probe whose call ended in an API error (HTTP 429, a server error) did not test the sandbox. Its record has
`passed: null` and `not_evaluable: "api_error"`, and the CLI exits with NOT_EVALUABLE_EXIT instead of 1. The same holds
for a probe model that never ran the script (no marker at all, `not_evaluable: "no_markers"`): a small model that does
not call Bash with the script verbatim says nothing about the sandbox.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys

from tsbench import conditions
from tsbench.conditions.sandbox import *  # noqa: F401,F403  (the probe's constants and helpers)
from tsbench.conditions.sandbox import (
    MUST_BE_ZERO,
    MUST_FAIL,
    PROBE_BUDGET_USD,
    PROBE_EFFORT,
    PROBE_FILENAME,
    PROBE_MAX_TURNS,
    PROBE_MODEL,
    PROBE_TRANSCRIPT,
    auth_mode,
    evaluate_transcript,
    existing_home_paths,
    localhost_listening,
    missing_probe_targets,
    probe_env,
    probe_prompt,
    probe_script_sha256,
    probe_script_template_sha256,
    session_settings_sha256,
    settings_text,
)
from tsbench.core.util import use_utf8_streams

NOT_EVALUABLE_EXIT = 75  # EX_TEMPFAIL: try again later; tools/functional_test.sh and `report summary` read it


API_ERROR_TEXT_CHARS = 500  # how much of the API error message the record keeps
NO_MARKERS_TEXT = ("the probe model {model} did not run the probe script (no marker in the transcript), so the sandbox "
                   "was not tested; probe with a model that calls Bash with the script verbatim")


def api_error_verdict(ev: dict, result: dict | None,
                      not_tested: tuple[str, ...] = ()) -> tuple[bool | None, str | None]:
    """(passed, not_evaluable) of the record. An API error leaves the probe not evaluable (None, "api_error") when its
    only effect is that markers are missing; so does a call that printed no marker at all and went wrong in no other
    way (None, "no_markers": the model did not run the script). Anything that arrived and is wrong stays a failure: a
    forbidden action succeeded, a must-be-zero check did not return 0 (KEYENV: the key was visible), an escape was
    requested, the init event did not match, or a probe target does not exist."""
    from tsbench.run import runner  # late: runner imports this module

    markers = ev["markers"]
    failed = (any(rc == 0 for name in MUST_FAIL for rc in markers.get(name, []))
              or any(rc != 0 for name in MUST_BE_ZERO for rc in markers.get(name, []))
              or ev["escape_requested"] or bool(ev["init_mismatches"]) or bool(not_tested))
    if result is not None and runner.is_api_error(result):
        return (False, None) if failed else (None, "api_error")
    if not ev["passed"] and not markers and not failed:
        return None, "no_markers"
    return bool(ev["passed"]), None


def api_error_reason(result: dict | None, env: dict[str, str]) -> str:
    """The reason of a not evaluable record: the API error message, the model credentials replaced, cut short."""
    from tsbench.run import runner  # late: runner imports this module

    text = runner._redact_keys(str((result or {}).get("result") or "no message"), env)[:API_ERROR_TEXT_CHARS]
    return "the probe call ended in an API error, so the sandbox was not tested: " + text


def run_probe(session, out_dir: pathlib.Path, *, model: str = PROBE_MODEL, remaining_usd: float | None = None) -> dict:
    """One real model call (a fake one in dry/fake sessions). Writes <out>/sandbox_probe.json. Every path in the record
    is relative to `out_dir` or a placeholder."""
    from tsbench.run import runner  # late: runner imports this module

    out_dir = pathlib.Path(out_dir)
    cap = PROBE_BUDGET_USD if remaining_usd is None else max(0.0, min(PROBE_BUDGET_USD, remaining_usd))
    transcript = out_dir / PROBE_TRANSCRIPT
    transcript.parent.mkdir(parents=True, exist_ok=True)
    argv = runner.build_argv(
        session.claude_argv, conditions.get("B"), model, PROBE_EFFORT,
        # a gateway run is not counted in USD: no cap at Claude Code's estimate
        None if getattr(session, "gateway", False) else cap,
        system_prompt_file=runner.NEUTRAL_PROMPT, settings_path=str(session.settings_path),
        mcp_config_path=None, max_turns=PROBE_MAX_TURNS,
    )
    real_home = getattr(session, "real_home", None)
    home_paths = existing_home_paths(real_home)
    env = session.child_env("B")  # the probe tests B: venv-B first on PATH
    env.update(probe_env(session.repo, real_home))
    if session.dry_run:
        env["FAKE_SEED"] = "sandbox-probe"
    listening = localhost_listening()
    not_tested = missing_probe_targets(session.repo)
    outcome, retries = runner.execute_with_retries(
        argv, probe_prompt(home_paths, not_tested), env, transcript, conditions.get("B"), model,
        timeout_s=runner.WALL_TIMEOUT_S)
    ev = evaluate_transcript(outcome.events, model, not_tested)
    passed, not_evaluable = api_error_verdict(ev, outcome.result, not_tested)
    reasons = ev["reasons"]
    if not_evaluable == "api_error":
        reasons = [api_error_reason(outcome.result, env)]
    elif not_evaluable == "no_markers":
        reasons = [NO_MARKERS_TEXT.format(model=model)]
    cost = outcome.cost_usd if outcome.cost_usd is not None else cap
    record = {
        "method": "builtin",
        "passed": passed,
        "not_evaluable": not_evaluable,
        "retries": len(retries),
        "reasons": reasons,
        "markers": ev["markers"],
        "init_mismatches": ev["init_mismatches"],
        "escape_requested": ev["escape_requested"],
        "cost_usd": cost,
        "cost_unknown": outcome.cost_usd is None,
        "claude_version": session.claude_version,
        "model": model,
        "auth_mode": auth_mode(session),
        "settings_sha256": session_settings_sha256(session),
        "probe_script_sha256": probe_script_sha256(home_paths, not_tested),
        "targets_not_tested": list(not_tested),
        "probe_script_template_sha256": probe_script_template_sha256(),
        "home_paths_tested": home_paths,
        "localhost_listening": listening,
        "child_path": session.recorded_child_path("B") if hasattr(session, "recorded_child_path") else None,
        "b_stack_sha256": (session.b_stack or {}).get("digest"),
        "transcript": PROBE_TRANSCRIPT.as_posix(),
        "exit_code": outcome.exit_code,
        "fake": bool(session.dry_run),
        "timestamp_utc": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
    }
    (out_dir / PROBE_FILENAME).write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return record


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="tsbench env sandbox", description=__doc__.splitlines()[0])
    ap.add_argument("--probe", action="store_true", help="run the sandbox probe (one real model call)")
    ap.add_argument("--settings-only", action="store_true", help="print the rendered sandbox settings and exit")
    ap.add_argument("--out", help="directory for sandbox_probe.json (required with --probe)")
    ap.add_argument("--model", default=PROBE_MODEL)
    ap.add_argument("--gateway", action="store_true")
    ap.add_argument("--b-venv", dest="b_venv", default=None, help="venv of condition B (default: see b_stack)")
    ap.add_argument("--fake", action="store_true", help="use the fake claude (tests; no network)")
    args = ap.parse_args(argv)

    if args.settings_only:
        use_utf8_streams()
        sys.stdout.write(settings_text())
        return 0
    if not args.probe:
        ap.error("give --probe or --settings-only")
    if not args.out:
        ap.error("--probe needs --out <dir>")

    from tsbench.run import runner

    session = runner.Session.create(dry_run=args.fake, gateway=args.gateway, b_venv=args.b_venv)
    try:
        rec = run_probe(session, pathlib.Path(args.out).resolve(), model=args.model)
    finally:
        session.close()
    verdict = "NOT EVALUABLE" if rec["passed"] is None else "PASS" if rec["passed"] else "FAIL"
    print(f"sandbox probe: {verdict} (cost USD {rec['cost_usd']:.4f})")
    for r in rec["reasons"]:
        print("  -", r)
    print("markers:", json.dumps(rec["markers"], sort_keys=True))
    print("record:", pathlib.Path(args.out) / PROBE_FILENAME)
    return NOT_EVALUABLE_EXIT if rec["passed"] is None else 0 if rec["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
