"""What a run set was made from, written next to what it produced.

    DIR/inputs/commands.sh   the command lines that made the run set, runnable (`bash inputs/commands.sh [TARGET]`);
                             every --resume appends its line; the environment by variable NAME only
    DIR/inputs/plan.jsonl    the clear plan, byte for byte (a sealed/confirmatory run: inputs/plan.sealed.json, the
                             sealed header only; no prompt ever lands in inputs/)
    DIR/inputs/hashes.json   task set, plan, system prompts, answer schemas, sandbox settings and B stack (B),
                             claude CLI, tanabesugano and tsbench versions, git commit
    DIR/run_set.json         {"title": ...}: one line for `tsbench.score.run_sets.discover_run_sets`
    DIR/README.md            what was run, when, how many runs and why not the rest, cost, how to re-run it, where
                             the outputs are

The texts come from small pure functions; `write_start` and `write_readme` put them on disk (called by the runner at the
start of a run and when it ends). Never a key value: keys appear as variable names, and the key file by its variable
(`tsbench.core.keys`). Host paths are written through the caller's `record` (placeholders).
"""
from __future__ import annotations

import datetime as dt
import hashlib
import importlib.metadata
import json
import pathlib
import shlex

from tsbench import conditions as cond_mod
from tsbench import plan as plan_mod
from tsbench.conditions import GATEWAY_URL
from tsbench.core.keys import SHELL_KEY_FILE
from tsbench.core.util import write_text_atomic

INPUTS_DIR = "inputs"
COMMANDS_NAME = "commands.sh"
HASHES_NAME = "hashes.json"
RUN_SET_NAME = "run_set.json"
README_NAME = "README.md"
CLEAR_PLAN_VAR = "TSBENCH_CLEAR_PLAN"  # a sealed run's clear plan lives outside the repo; the script asks for its path
TRANSCRIPT_LAYOUT = "<model>/<condition>/<effort>/<task_id>-k<k>.jsonl"


class Raw(str):
    """A shell word written as is (a quoted variable such as `"$OUT"`), not quoted again."""


def shell_line(argv) -> str:
    return " ".join(w if isinstance(w, Raw) else shlex.quote(str(w)) for w in argv)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def tsbench_version() -> str:
    try:
        return importlib.metadata.version("tsbench")
    except importlib.metadata.PackageNotFoundError:
        import tsbench
        return getattr(tsbench, "__version__", "unknown")


# ------------------------------------------------------------------ command lines
def run_argv(given: dict, *, out_ref, plan_ref, tsbench="tsbench", resume: bool = False) -> list:
    """`tsbench run ...` with the flags of the invocation `given` (the parsed arguments before the runner filled them
    from the plan). `--out` and `--plan` become `out_ref` / `plan_ref`; `--b-venv` (a host path) is left out."""
    argv: list = [tsbench, "run"]
    if given.get("plan"):
        argv += ["--plan", plan_ref]
    else:
        for name in ("split", "models", "conditions", "effort", "k", "limit"):
            if given.get(name) is not None:
                argv += [f"--{name}", given[name]]
    for name, flag in (("budget_usd", "--budget-usd"), ("per_call_usd", "--per-call-usd")):
        if given.get(name) is not None:
            argv += [flag, given[name]]
    argv += ["--out", out_ref]
    if given.get("dry_run"):
        argv.append("--dry-run")
    if given.get("gateway"):
        argv.append("--gateway")
    if given.get("preregistered"):
        argv += ["--i-have-preregistered", given["preregistered"]]
    if resume:
        argv.append("--resume")
    return argv


def plan_reconstructible(header: dict, plan_task_ids: list[str] | None, split_task_ids: list[str] | None) -> str | None:
    """None when `tsbench plan build` with the header's spec selects the same tasks, else the reason why not. A clear
    plan compares its task ids (in order) with the first `limit` tasks of the split; a sealed one (no task ids) its run
    count. The task-class / task-id selection of `plan build` is not in the spec, so such a plan is not rebuilt."""
    spec = header.get("spec") or {}
    if split_task_ids is None:
        return f"the {spec.get('split')!r} split could not be loaded"
    first = split_task_ids[: spec["limit"]] if spec.get("limit") else split_task_ids
    if plan_task_ids is not None:
        return None if plan_task_ids == first else (
            "its task selection (--task-class / --task-ids) is not recorded in the plan header's spec")
    layers = spec["k"] - spec.get("k_from", 1) + 1
    want = len(first) * len(spec["models"]) * len(spec["efforts"]) * len(spec["conditions"]) * layers
    return None if header.get("n_runs") == want else "its run count does not match the spec over the whole split"


def plan_build_argv(header: dict, *, out_plan, preregistered: str | None, tsbench="tsbench") -> list:
    """`tsbench plan build ...` from the plan header's spec."""
    spec = header["spec"]
    argv: list = [tsbench, "plan", "build", "--split", spec["split"], "--models", ",".join(spec["models"]),
                  "--conditions", ",".join(spec["conditions"]), "--effort", ",".join(spec["efforts"]),
                  "--k", spec["k"]]
    if spec.get("k_from", 1) != 1:
        argv += ["--k-from", spec["k_from"]]
    if spec.get("stage"):
        argv += ["--stage", spec["stage"]]
    argv += ["--budget-usd", spec["budget_usd"]]
    if spec.get("limit") is not None:
        argv += ["--limit", spec["limit"]]
    if spec.get("gateway"):
        argv.append("--gateway")
    if spec.get("system_prompt_file", plan_mod.DEFAULT_SYSTEM_PROMPT) != plan_mod.DEFAULT_SYSTEM_PROMPT:
        argv += ["--system-prompt-file", spec["system_prompt_file"]]
    if spec["split"] == "confirmatory" and preregistered:
        argv += ["--i-have-preregistered", preregistered]
    return argv + ["--out-plan", out_plan]


def env_lines(*, gateway: bool, dry_run: bool, fake_env: dict | None = None,
              gateway_url: str | None = None) -> list[str]:
    """The environment of the run as shell lines: variable NAMES and fixed settings only, never a key value. A real run
    stops with a message when the key variable is not set; a dry run (the fake claude) needs no key."""
    lines: list[str] = []
    if gateway:
        lines.append(f'export ANTHROPIC_BASE_URL={gateway_url or GATEWAY_URL}')
        if dry_run:
            lines.append('export ANTHROPIC_AUTH_TOKEN="${GWDG_API_KEY:-}"  # not needed for a dry run')
        else:
            lines.append(f'export ANTHROPIC_AUTH_TOKEN="${{GWDG_API_KEY:?set GWDG_API_KEY (see {SHELL_KEY_FILE})}}"')
        lines.append("unset ANTHROPIC_API_KEY TSMCP_ANTHROPIC_API_KEY")
    else:
        if not dry_run:
            lines.append(': "${TSMCP_ANTHROPIC_API_KEY:-${ANTHROPIC_API_KEY:?set TSMCP_ANTHROPIC_API_KEY '
                         f'(see {SHELL_KEY_FILE})}}}}"')
        lines.append("unset ANTHROPIC_BASE_URL ANTHROPIC_AUTH_TOKEN")
    for name, value in sorted((fake_env or {}).items()):  # the fake claude's switches (dry runs; not secrets)
        lines.append(f"export {name}={shlex.quote(str(value))}")
    return lines


def plan_ref_for(given: dict, sealed: bool, plan_id: str):
    """What `--plan` points at in commands.sh: the stored copy, or (sealed) the clear plan kept outside the repo."""
    if sealed:
        return Raw(f'"${{{CLEAR_PLAN_VAR}:?path of the clear plan with plan_id {plan_id} (kept outside the repo)}}"')
    return Raw('"$HERE/plan.jsonl"')


def commands_text(*, title: str, given: dict, header: dict, sealed: bool, rebuild_reason: str | None,
                  started_utc: str, version: str, git_commit: str | None, original: str,
                  fake_env: dict | None = None, gateway_url: str | None = None) -> str:
    """The whole commands.sh of a run set (the first invocation; `resume_text` appends the later ones)."""
    plan_id = header["plan_id"]
    gateway = bool(given.get("gateway") or (header.get("spec") or {}).get("gateway"))
    dry = bool(given.get("dry_run"))
    plan_name = plan_mod.SEALED_NAME if sealed else plan_mod.PLAN_NAME
    lines = [
        "#!/usr/bin/env bash",
        f"# Run set: {title}",
        f"# Written by `tsbench run` (tsbench {version}, commit {git_commit or 'unknown'}) at {started_utc}.",
        f"# plan_id {plan_id}",
        "#",
        "# Keys: this file holds no key or token, only variable NAMES. They come from your shell, e.g. from the key "
        "file:",
        f'# `set -a; . "{SHELL_KEY_FILE}"; set +a` (TSMCP_ANTHROPIC_API_KEY: Anthropic API,',
        "# GWDG_API_KEY: gateway). A dry run (--dry-run, the fake claude) needs no key.",
        "#",
        "#   bash inputs/commands.sh [TARGET]   run the whole run set again into TARGET (default: <run set>-rerun)",
        "#   continuing THIS run set instead: see README.md (`tsbench run ... --resume`)",
        "set -euo pipefail",
        'HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"',
        'OUT="${1:-$(dirname "$HERE")-rerun}"',
        'TSBENCH="${TSBENCH:-tsbench}"',
        f"# the invocation (host paths as placeholders): {original}",
        "",
        "# environment (names only)",
        *env_lines(gateway=gateway, dry_run=dry, fake_env=fake_env, gateway_url=gateway_url),
        "",
    ]
    if rebuild_reason is None:
        rebuilt = Raw(f'"$OUT/{INPUTS_DIR}/rebuilt/{plan_mod.PLAN_NAME}"')
        check = Raw(f'"$OUT/{INPUTS_DIR}/rebuilt/{plan_name}"')
        lines += [f"# 1. the plan, rebuilt from its header's spec (the run below uses the stored {plan_name} anyway)",
                  shell_line(plan_build_argv(header, out_plan=rebuilt, preregistered=given.get("preregistered"),
                                             tsbench=Raw('"$TSBENCH"'))),
                  f"grep -q '\"plan_id\": \"{plan_id}\"' {check} || echo \"WARNING: the rebuilt plan has another "
                  "plan_id (task set or code changed); the run uses the stored plan\" >&2",
                  ""]
    else:
        lines += [f"# 1. the plan is not rebuilt here: {rebuild_reason}; inputs/{plan_name} is the input", ""]
    lines += ["# 2. the run",
              shell_line(run_argv(given, out_ref=Raw('"$OUT"'), plan_ref=plan_ref_for(given, sealed, plan_id),
                                  tsbench=Raw('"$TSBENCH"')))]
    return "\n".join(lines) + "\n"


def resume_text(*, given: dict, sealed: bool, plan_id: str, at_utc: str, previous_plan_id: str | None) -> str:
    """The lines a --resume invocation appends to commands.sh."""
    note = "" if previous_plan_id in (None, plan_id) else f"; plan_id changed from {previous_plan_id} to {plan_id}"
    return (f"\n# resumed at {at_utc}{note}\n"
            + shell_line(run_argv(given, out_ref=Raw('"$OUT"'), plan_ref=plan_ref_for(given, sealed, plan_id),
                                  tsbench=Raw('"$TSBENCH"'), resume=True)) + "\n")


# ------------------------------------------------------------------ hashes, title, README
def split_line_sha256(hash_file_text: str, name: str) -> str | None:
    for line in hash_file_text.splitlines():
        digest, _, entry = line.partition("  ")
        if entry == name:
            return digest
    return None


def hashes(*, plan_obj, sealed: bool, plan_file_sha256: str, tasks_file: str, tasks_file_sha256: str | None,
           split_sha256: str | None, manifest: dict) -> dict:
    """hashes.json: what this run set was run against. Planned values from the plan, live ones from the manifest."""
    h = plan_obj.header
    runs = plan_obj.runs
    conds = manifest.get("conditions") or []
    b = "B" in conds
    return {
        "plan_id": plan_obj.plan_id,
        "plan_sha256": plan_obj.sha256,
        "plan_file": f"{INPUTS_DIR}/{plan_mod.SEALED_NAME if sealed else plan_mod.PLAN_NAME}",
        "plan_file_sha256": plan_file_sha256,
        "plan_sealed": sealed,
        "plan_created_utc": h.get("created_utc"),
        "plan_schema_version": h.get("schema_version"),
        "tasks": {"file": tasks_file, "file_sha256": tasks_file_sha256, "split": h["spec"]["split"],
                  "split_sha256": split_sha256, "plan_tasks_sha256": h.get("tasks_sha256")},
        "system_prompts": [{"resource": f, "sha256": s} for f, s in
                           dict.fromkeys((r["system_prompt_file"], r["system_prompt_sha256"]) for r in runs)],
        "answer_schemas": [{"name": n, "sha256": s} for n, s in
                           dict.fromkeys((r.get("answer_schema") or "fit", r.get("answer_schema_sha256"))
                                         for r in runs)],
        "sandbox_settings_sha256": manifest.get("sandbox_settings_sha256") if b else None,
        "b_stack_sha256": ((manifest.get("b_stack") or {}).get("digest") if b else None),
        "claude_cli_version": manifest.get("claude_version"),
        "tanabesugano_version": manifest.get("tanabesugano_version"),
        "tsbench_version": tsbench_version(),
        "git_commit": manifest.get("git_commit"),
        "git_dirty": manifest.get("git_dirty"),
        "pins": h.get("pins"),
    }


def _join(v) -> str:
    return ", ".join(v) if isinstance(v, (list, tuple)) else str(v)


def _n_tasks(manifest: dict) -> int:
    t = manifest.get("tasks")
    return len(t) if isinstance(t, list) else int(t or 0)


def gateway_label_of(manifest: dict) -> str:
    """`gateway` (the default endpoint), or the endpoint that the manifest recorded for a gateway run
    (`args.gateway_url`)."""
    return cond_mod.gateway_label((manifest.get("args") or {}).get("gateway_url"))


def title_of(manifest: dict, *, gateway: bool, dry_run: bool) -> str:
    """One line: models; conditions; effort; k; split and task count; gateway; dry run."""
    parts = [_join(manifest.get("models_requested") or []), "conditions " + ",".join(manifest.get("conditions") or []),
             "effort " + _join(manifest.get("effort")), f"k={manifest.get('k')}",
             f"{manifest.get('split')} ({_n_tasks(manifest)} tasks)"]
    if gateway:
        parts.append(gateway_label_of(manifest))
    if dry_run:
        parts.append("dry run")
    return " | ".join(parts)


def cost_text(manifest: dict, *, gateway: bool, dry_run: bool) -> str:
    if dry_run:
        return "none: dry run (the fake claude, no API call)"
    if gateway:
        return "not counted in USD: " + gateway_label_of(manifest)
    return f"USD {float(manifest.get('total_cost_usd') or 0):.4f} (run-set budget USD {manifest.get('budget_usd')})"


def status_lines(manifest: dict) -> list[str]:
    """How many runs were done, skipped or not run, and why."""
    c = manifest.get("counts") or {}
    planned = int(c.get("planned") or 0)
    accounted = sum(int(c.get(k) or 0) for k in ("done", "rate_limited", "skipped", "aborted", "not_run_sandbox",
                                                  "not_run_probe_not_evaluable", "not_run_budget", "not_run_quota",
                                                  "not_run_api_errors"))
    out = [f"- planned: {planned}",
           f"- done in this invocation: {c.get('done', 0)}",
           f"- skipped (finished in an earlier invocation, --resume): {c.get('skipped', 0)}"]
    if c.get("rate_limited"):
        out.append(f"- rate limited (HTTP 429, not answered): {c['rate_limited']}")
    if c.get("aborted"):
        reasons = "; ".join(f"{a['model']}/{a['condition']}/{a['effort']}: {'; '.join(a.get('reasons') or [])}"
                            for a in manifest.get("aborted_cells") or [])
        out.append(f"- not run, cell aborted (the init event did not match the condition): {c['aborted']} ({reasons})")
    if c.get("not_run_sandbox"):
        out.append(f"- not run, the sandbox probe failed so condition B was skipped: {c['not_run_sandbox']}")
    if c.get("not_run_probe_not_evaluable"):
        out.append(f"- not run, the sandbox probe could not be evaluated so condition B was skipped: "
                   f"{c['not_run_probe_not_evaluable']}")
    if c.get("not_run_quota"):
        out.append(f"- not run, the quota was used up: {c['not_run_quota']}")
    if c.get("not_run_api_errors"):
        out.append(f"- not run, API errors stopped the run set: {c['not_run_api_errors']}")
    if c.get("not_run_budget"):
        out.append(f"- not run, the run-set budget (USD {manifest.get('budget_usd')}) was reached: "
                   f"{c['not_run_budget']}")
    rest = planned - accounted
    if rest > 0:
        why = ("interrupted (Ctrl-C) before they started" if manifest.get("interrupted")
               else "not reached yet (the run is still going)" if not manifest.get("end_time_utc")
               or not manifest.get("finished") else "not started")
        out.append(f"- {why}: {rest}")
    if manifest.get("flagged_runs"):
        out.append(f"- flagged runs (see MANIFEST.json `flagged_runs`): {len(manifest['flagged_runs'])}")
    return out


def readme_text(manifest: dict, *, title: str, gateway: bool, dry_run: bool, sealed: bool, resume_cmd: str,
                running: bool) -> str:
    """README.md of a run set (short, for a person)."""
    tasks = _n_tasks(manifest)
    stop = manifest.get("stop") or {}
    quota = "stopped by the quota" + (f" ({stop['scope']} cap)" if stop.get("scope") in ("daily", "monthly") else "")
    state = ("running" if running else "interrupted" if manifest.get("interrupted")
             else "stopped by an error" if manifest.get("finished") is False
             else quota if stop.get("reason") == "quota_exhausted"
             else "stopped by API errors" if stop.get("reason") == "api_errors"
             else "stopped by the budget" if manifest.get("stopped_by_budget") else "finished")
    plan_name = plan_mod.SEALED_NAME if sealed else plan_mod.PLAN_NAME
    lines = [
        f"# Run set: {title}", "",
        "## What was run", "",
        f"- models: {_join(manifest.get('models_requested') or [])}",
        f"- conditions: {', '.join(manifest.get('conditions') or [])} (A no tools, B Bash in a sandbox, C MCP server)",
        f"- effort: {_join(manifest.get('effort'))}; k = {manifest.get('k')}",
        f"- tasks: {tasks} of the {manifest.get('split')} split",
        f"- plan_id: `{manifest.get('plan_id')}`" + (" (sealed: the prompts are not stored here)" if sealed else ""),
        f"- {gateway_label_of(manifest) if gateway else 'Anthropic API'}"
        + ("; dry run with the fake claude" if dry_run else ""),
        "",
        "## When", "",
        f"- start (UTC): {manifest.get('start_time_utc')}",
        f"- end (UTC): {'(running)' if running else manifest.get('end_time_utc')}",
        f"- state: {state}",
        "",
        "## Runs", "",
        *status_lines(manifest),
        "",
        f"Total cost: {cost_text(manifest, gateway=gateway, dry_run=dry_run)}", "",
        "## Inputs (next to the outputs)", "",
        "- `inputs/commands.sh`: the command lines that made this run set (keys by name only)",
        f"- `inputs/{plan_name}`: the plan" + (" (sealed header only)" if sealed else " (byte for byte)"),
        "- `inputs/hashes.json`: task set, plan, system prompts, answer schemas, sandbox settings, B stack, versions",
        "",
        "## Re-run", "",
        "Run the whole run set again (into `<this folder>-rerun`, or a folder you name):", "",
        "    bash inputs/commands.sh [TARGET]", "",
        "Continue this run set (finished runs are skipped), from inside this folder:", "",
        f"    {resume_cmd}", "",
        "## Outputs", "",
        f"- transcripts: `{TRANSCRIPT_LAYOUT}` (the raw stream-json of `claude -p`), each with a `.meta.json`"
        " sidecar (argv, cost, flags); earlier attempts as `.attempt<N>.jsonl`; harvested images in `.artifacts/`",
        "- `MANIFEST.json`: counts, cost, versions, pins and the sha256 of every transcript",
        "- scores: `tsbench score --runs <this folder>` writes `scores.csv` here",
        "",
    ]
    return "\n".join(lines)


# ------------------------------------------------------------------ writing
def _split_task_ids(split: str) -> list[str] | None:
    from tsbench.tasks import load
    try:
        return [t["id"] for t in load(split)]
    except (OSError, ValueError):
        return None


def _resume_cmd(given: dict, sealed: bool) -> str:
    """The README's line to continue this run set from inside its folder: the plan copy (a clear plan), the clear plan
    kept outside the repo (a sealed --plan run) or the same flags (a sealed flags run)."""
    if sealed and not given.get("plan"):
        return shell_line(run_argv(given, out_ref=".", plan_ref=None, resume=True))
    plan_ref = Raw(f'"${CLEAR_PLAN_VAR}"') if sealed else f"{INPUTS_DIR}/{plan_mod.PLAN_NAME}"
    return shell_line(run_argv({**given, "plan": True}, out_ref=".", plan_ref=plan_ref, resume=True))


def _readme_flags(given: dict, header: dict) -> tuple[bool, bool]:
    return bool(given.get("gateway") or (header.get("spec") or {}).get("gateway")), bool(given.get("dry_run"))


def write_start(out: pathlib.Path, *, given: dict, plan_obj, sealed: bool, manifest: dict, record, original: str,
                fake_env: dict | None = None, resume: bool = False) -> None:
    """At the start of a run: inputs/ (plan copy, hashes.json, commands.sh or its resume line), run_set.json, README.
    `manifest` is the runner's manifest (unredacted); `record` redacts host paths in what is written."""
    out = pathlib.Path(out)
    inp = out / INPUTS_DIR
    inp.mkdir(parents=True, exist_ok=True)
    header = plan_obj.header
    gateway, dry = _readme_flags(given, header)
    title = title_of(manifest, gateway=gateway, dry_run=dry)
    # the plan: a clear copy byte for byte, or only the sealed header
    previous_id = None
    try:
        previous_id = json.loads(next(p for p in (inp / plan_mod.PLAN_NAME, inp / plan_mod.SEALED_NAME)
                                      if p.exists()).read_text(encoding="utf-8").splitlines()[0])["plan_id"]
    except (StopIteration, OSError, ValueError, IndexError, KeyError, TypeError):
        previous_id = None
    if sealed:
        plan_text = plan_mod.canonical(plan_obj.sealed_header()) + "\n"
        plan_path = inp / plan_mod.SEALED_NAME
    else:
        plan_text = plan_obj.text()
        plan_path = inp / plan_mod.PLAN_NAME
        if plan_path.exists() and previous_id and previous_id != plan_obj.plan_id:
            plan_path.rename(inp / f"plan.prev-{previous_id[:16]}.jsonl")
    write_text_atomic(plan_path, plan_text)
    # hashes
    from tsbench.tasks import hash_path, tasks_path
    try:
        tasks_sha = sha256_bytes(tasks_path().read_bytes())
        split_sha = split_line_sha256(hash_path().read_text(encoding="utf-8"), header["spec"]["split"])
    except OSError:
        tasks_sha = split_sha = None
    h = hashes(plan_obj=plan_obj, sealed=sealed, plan_file_sha256=sha256_bytes(plan_text.encode("utf-8")),
               tasks_file=f"tasks/{tasks_path().name}", tasks_file_sha256=tasks_sha, split_sha256=split_sha,
               manifest=manifest)
    write_text_atomic(inp / HASHES_NAME, json.dumps(record(h), indent=2, sort_keys=True) + "\n")
    # commands.sh: written by the first invocation; a --resume appends its line
    cmd_path = inp / COMMANDS_NAME
    started = manifest.get("start_time_utc") or dt.datetime.now(dt.UTC).isoformat(timespec="seconds")
    if not (resume and cmd_path.exists()):
        plan_task_ids = None if sealed else list(dict.fromkeys(r["task_id"] for r in plan_obj.runs))
        reason = plan_reconstructible(header, plan_task_ids, _split_task_ids(header["spec"]["split"]))
        text = commands_text(title=title, given=given, header=header, sealed=sealed, rebuild_reason=reason,
                             started_utc=started, version=tsbench_version(), git_commit=manifest.get("git_commit"),
                             original=record(original), fake_env=record(dict(fake_env or {})),
                             gateway_url=(manifest.get("args") or {}).get("gateway_url"))
        if resume:
            text += ("\n# (inputs/ was first written by this --resume; the line above is reconstructed from its "
                     "arguments)\n")
        write_text_atomic(cmd_path, text)
    if resume:
        text = cmd_path.read_text(encoding="utf-8") + resume_text(given=given, sealed=sealed, plan_id=plan_obj.plan_id,
                                                                  at_utc=started, previous_plan_id=previous_id)
        write_text_atomic(cmd_path, text)
    cmd_path.chmod(0o755)
    write_text_atomic(out / RUN_SET_NAME, json.dumps({"title": title}, indent=2, ensure_ascii=False) + "\n")
    write_readme(out, given=given, plan_obj=plan_obj, sealed=sealed, manifest=record(manifest), running=True)


def write_readme(out: pathlib.Path, *, given: dict, plan_obj, sealed: bool, manifest: dict,
                 running: bool = False) -> None:
    """README.md from the manifest as it is now (at the start: `running`; at the end: the final counts)."""
    gateway, dry = _readme_flags(given, plan_obj.header)
    text = readme_text(manifest, title=title_of(manifest, gateway=gateway, dry_run=dry), gateway=gateway,
                       dry_run=dry, sealed=sealed, resume_cmd=_resume_cmd(given, sealed), running=running)
    write_text_atomic(pathlib.Path(out) / README_NAME, text)
