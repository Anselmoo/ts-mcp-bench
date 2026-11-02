"""Benchmark runner. One `claude -p` call per (k, task, model, condition).

    tsbench run --split pilot --models claude-haiku-5-5 --conditions A,B,C \\
        --effort medium --k 2 --budget-usd 10 --out runs [--dry-run] [--resume] [--limit N] \\
        [--gateway] [--i-have-preregistered DOI]
    tsbench run --plan plan.jsonl --out DIR [--dry-run] [--resume] [--gateway] [--budget-usd N]
        [--i-have-preregistered DOI]

Both forms execute a run plan (src/tsbench/plan). The flags form builds it in memory and writes `<out>/plan.jsonl`
(pilot) or `<out>/plan.sealed.json` (confirmatory: header and counts only); `--plan` reads ONLY the plan for task,
prompt, model, effort and condition.

Every run set stores its inputs next to its outputs (src/tsbench/run/inputs.py): `<out>/inputs/` (commands.sh, the plan
copy or the sealed header, hashes.json), `<out>/run_set.json` and `<out>/README.md`.

Isolation (every run): an empty temp cwd outside the repo; an isolated HOME and
CLAUDE_CONFIG_DIR so the user's own plugins and skills cannot leak into the init event; an
allow-listed environment (never `os.environ` as it is); a PATH without the repo or any virtualenv.

Plan order: k outermost, then task (file order), then model, then condition, so that a run
stopped by the budget leaves a balanced partial matrix.
"""
from __future__ import annotations

import argparse
import contextlib
import dataclasses
import datetime as dt
import fcntl
import glob
import importlib.metadata
import json
import os
import pathlib
import platform
import random
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time

from tsbench import conditions as cond_mod
from tsbench import plan as plan_mod
from tsbench.conditions import b_stack
from tsbench.conditions import sandbox as sandbox_mod
from tsbench.core.api_errors import is_context_overflow
from tsbench.core.util import claude_version, env_int, git_output, sha256_file, write_text_atomic
from tsbench.run import inputs as inputs_mod
from tsbench.run import sandbox_probe
from tsbench.run.env import (  # noqa: F401  (re-exported for callers of the runner)
    FAKE_PASSTHROUGH,
    RUN_USER,
    Abort,
    api_key_of,
    build_child_env,
    child_path,
    claude_runtime_dirs,
    host_label,
    missing_env,
    mpl_cache_dir,
    path_offenders,
    placeholder_pairs,
    redact,
    warm_mpl_cache,
)
from tsbench.run.harvest import (  # noqa: F401
    ARTIFACT_MAX_FILES,
    artifacts_dir_of,
    harvest_artifacts,
    image_sha_match,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
from tsbench.conditions.argv import (  # noqa: E402,F401  (re-exported for the runner's callers)
    EFFORTS,
    NEUTRAL_PROMPT,
    build_argv,
    find_mcp_command,
    render_ts_json,
    run_id_of,
    validate_model_id,
)

FAKE_ARGV = [sys.executable, "-m", "tsbench.run.fake_cli"]

WALL_TIMEOUT_S = 900
# HTTP 429 (rate limit): wait and run the SAME run again. Seconds before retry 1..4; plus up to JITTER of the wait.
# TSBENCH_429_MAX_RETRIES overrides the number of retries (0 = never retry).
RETRY_429_BACKOFF_S = (60, 120, 240, 480)
RETRY_429_JITTER = 0.25
RETRY_429_ENV = "TSBENCH_429_MAX_RETRIES"
# The quota is gone when the gateway says so (`limit exhausted`, `daily limit reached`), or when this many runs in a
# row end in HTTP 429 after their retries. TSBENCH_429_STOP_AFTER overrides the number (0 = never stop on the count).
STOP_429_AFTER = 3
STOP_429_ENV = "TSBENCH_429_STOP_AFTER"
# An expired token, an unserved model id or a 5xx outage ends every run in an API error (or, for a hung call, without a
# result after WALL_TIMEOUT_S). The run set stops after this many such runs in a row; HTTP 429 has its own rule above.
# TSBENCH_API_ERROR_STOP_AFTER overrides the number (0 = never stop on the count).
STOP_API_ERROR_AFTER = 3
STOP_API_ERROR_ENV = "TSBENCH_API_ERROR_STOP_AFTER"
EX_TEMPFAIL = 75  # exit code of an invocation that stopped because of the quota: wait for the reset, then --resume
RUN_LOCK_NAME = ".run.lock"  # in the run folder; held by the one invocation that writes there
STDERR_TAIL_CHARS = 2000
LAST_EVENT_WINDOW = 64 * 1024  # bytes: the first tail window `last_event` reads from the end of a transcript
REQUIRED_TANABESUGANO = "2.0.0"

# what a gateway says when a cap is used up; a plain "rate limit reached" is an ordinary 429 that a retry can clear
QUOTA_GONE_RE = re.compile(r"limit exhausted|\b(?:daily|monthly)\b[^.]*\blimit reached")


def utcnow() -> str:
    return dt.datetime.now(dt.UTC).isoformat(timespec="seconds")


# ------------------------------------------------------------------ small pure helpers
def transcript_path(out: pathlib.Path, model: str, cond: str, effort: str, task_id: str, k: int) -> pathlib.Path:
    return pathlib.Path(out) / model / cond / effort / f"{task_id}-k{k}.jsonl"


def meta_path(tp: pathlib.Path) -> pathlib.Path:
    return tp.with_name(tp.name[: -len(".jsonl")] + ".meta.json")


def last_event(path: pathlib.Path) -> dict | None:
    """The last non-blank line of a transcript as an event dict, or None when it is empty, not JSON or not an object.
    Raises OSError when the file cannot be read. The transcript is split at the newline only (U+2028, U+2029 and U+0085
    may stand unescaped inside a JSON string, as `score.extract.read_transcript` reads it), and only the tail is read:
    the window from the end doubles until it holds one whole non-blank line."""
    with pathlib.Path(path).open("rb") as f:
        size = f.seek(0, os.SEEK_END)
        window = LAST_EVENT_WINDOW
        while True:
            start = max(0, size - window)
            f.seek(start)
            pieces = f.read(size - start).decode("utf-8", errors="replace").split("\n")
            if start > 0:
                pieces = pieces[1:]  # the first piece may begin inside a line
            lines = [ln for ln in pieces if ln.strip()]
            if lines or start == 0:
                break
            window *= 2
    try:
        ev = json.loads(lines[-1]) if lines else None
    except ValueError:
        return None
    return ev if isinstance(ev, dict) else None


def timed_out_cost(path: pathlib.Path) -> float | None:
    """The cost the runner booked for a run that hit the wall limit (`WALL_TIMEOUT_S`), read from its sidecar; None when
    the sidecar is missing, unreadable, older than the transcript (it belongs to an earlier attempt) or does not say
    `timed_out`. Such a run has no result event, but it is an outcome, not an interrupted run."""
    sidecar = meta_path(path)
    try:
        if sidecar.stat().st_mtime < pathlib.Path(path).stat().st_mtime:
            return None
        rec = json.loads(sidecar.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(rec, dict) or rec.get("timed_out") is not True:
        return None
    try:
        return float(rec.get("cost_usd") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def transcript_status(path: pathlib.Path) -> tuple[bool, float]:
    """(done, cost). Done = the last event is a result, unless it is a zero-cost error or an API error (any cost); or
    the sidecar says the run hit the wall limit (a deliberate harness limit, so --resume does not sample it again).
    A run killed or crashed before its sidecar was written is not done."""
    try:
        ev = last_event(path)
    except OSError:
        return False, 0.0
    if ev is None or ev.get("type") != "result":
        timed_out = timed_out_cost(path)
        return (False, 0.0) if timed_out is None else (True, timed_out)
    cost = float(ev.get("total_cost_usd") or 0.0)
    if is_context_overflow(ev) and not is_api_error(ev):  # a wrong answer, also when the gateway reports no cost
        return True, cost
    if ev.get("is_error") and cost == 0:
        return False, 0.0
    if is_api_error(ev):
        # An API error (HTTP 429, a 5xx, ...) is infrastructure, never an answer: rerun it whatever cost it reports.
        # Through a gateway Claude Code also prints an estimated price for unknown models.
        return False, 0.0
    return True, cost


# fields that a sidecar and a plan record share by name
RESUME_COMPARED = ("prompt_sha256", "system_prompt_sha256", "max_turns", "disallowed_tools")


def resume_conflict(out: pathlib.Path, plan_runs: list[dict]) -> str | None:
    """--resume: None, or the first finished run whose sidecar says it was made with another prompt, system prompt,
    turn limit or tool block than the plan record now asks for (the folder would mix two configurations). A run that is
    not done, has no readable sidecar, or a sidecar without the field is not compared."""
    for r in plan_runs:
        tp = transcript_path(out, r["model"], r["condition"], r["effort"], r["task_id"], r["k"])
        if not transcript_status(tp)[0]:
            continue
        try:
            rec = json.loads(meta_path(tp).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(rec, dict):
            continue
        for field in RESUME_COMPARED:
            if field in rec and field in r and rec[field] != r[field]:
                return f"{r['run_id']}: finished with {field} {rec[field]!r}, the plan has {r[field]!r}"
    return None


def is_api_error(result_event: dict) -> bool:
    """True when a result event ended in an API error: HTTP 429, another status >= 400, Claude Code's
    `terminal_reason: api_error`, or a result text starting `API Error:`. The same rule as
    `score.not_evaluable_reason`. The harness limits (`error_max_turns`, `error_max_budget_usd`) are not API errors:
    they are the run's outcome and stay done; so is a context overflow (`core.api_errors.is_context_overflow`), which
    the scorer counts as a wrong answer."""
    if not isinstance(result_event, dict) or not result_event.get("is_error"):
        return False
    if is_context_overflow(result_event) and not is_rate_limited(result_event):
        return False
    status = result_event.get("api_error_status")
    return (is_rate_limited(result_event) or (isinstance(status, int) and status >= 400)
            or result_event.get("terminal_reason") == "api_error"
            or str(result_event.get("result") or "").startswith("API Error:"))


def is_rate_limited(result_event: dict) -> bool:
    """True when a result event reports an API rate limit (HTTP 429)."""
    status = str(result_event.get("api_error_status") or "")
    text = str(result_event.get("result") or "").lower()
    return status == "429" or "rate limit" in text or "(429)" in text


def quota_scope(result_event: dict | None) -> str | None:
    """None, or the cap that is used up when a result is an HTTP 429 whose text says the quota is gone: `daily` or
    `monthly` as the text names it, else `unknown`. A gateway with a request cap says, for example, "Rate limit
    exceeded: user daily request limit reached (N of N). Retry after S seconds." or "... rate limit exhausted (N of
    N)."; waiting a few minutes cannot help against that, and every retry costs one more request. A 429 that asks for
    a wait longer than the longest backoff step is treated the same way, whatever its wording."""
    if not isinstance(result_event, dict) or not (result_event.get("is_error") and is_rate_limited(result_event)):
        return None
    text = str(result_event.get("result") or "").lower()
    waits = [int(n) for n in re.findall(r"retry after (\d+)", text)]
    if not (QUOTA_GONE_RE.search(text) or any(n > max(RETRY_429_BACKOFF_S) for n in waits)):
        return None
    named = re.search(r"\b(daily|monthly)\b", text)
    return named.group(1) if named else "unknown"


def compute_flags(cond: str, events: list[dict], result: dict | None) -> tuple[list[str], dict]:
    """Flags (not aborts) for one run, with details. A run that ended in HTTP 429 gets only `rate_limited`: no model
    answered, so "no tool use" would be an artefact of the infrastructure."""
    if isinstance(result, dict) and result.get("is_error") and is_rate_limited(result):
        return ["rate_limited"], {}
    tool_uses = []
    for ev in events:
        if isinstance(ev, dict) and ev.get("type") == "assistant":
            for block in (ev.get("message") or {}).get("content") or []:
                if (isinstance(block, dict) and block.get("type") == "tool_use"
                        and block.get("name") != cond_mod.STRUCTURED_TOOL):
                    tool_uses.append(block)
    flags: list[str] = []
    details: dict = {}
    denials = (result or {}).get("permission_denials") or []
    if denials:
        # In any condition: a denied tool call means the condition was not the one we meant to run
        # (e.g. --allowedTools not matching under -p --bare turns C into "C with every call refused").
        flags.append("permission_denials")
        details["permission_denials"] = len(denials)
    if cond == "B":
        # `b_no_tool_use` means no code ran: a call that a denial names (by tool_use_id) did not run; a denial without
        # an id takes one call away
        ids = {d.get("tool_use_id") for d in denials if isinstance(d, dict) and d.get("tool_use_id")}
        by_count = sum(1 for d in denials if not (isinstance(d, dict) and d.get("tool_use_id")))
        ran = sum(1 for b in tool_uses if b.get("id") not in ids) - by_count
        if ran <= 0:
            flags.append("b_no_tool_use")
            if not tool_uses and not denials:
                details["tool_use_count"] = 0
    if cond == "C":
        mcp_ids = {b.get("id") for b in tool_uses
                   if str(b.get("name", "")).startswith(cond_mod.MCP_TOOL_PREFIX)}
        if not mcp_ids:
            flags.append("c_no_mcp_call")
        else:
            mcp_results = [blk for ev in events if isinstance(ev, dict) and ev.get("type") == "user"
                           for blk in ((ev.get("message") or {}).get("content") or [])
                           if isinstance(blk, dict) and blk.get("type") == "tool_result"
                           and blk.get("tool_use_id") in mcp_ids]
            if mcp_results and all(blk.get("is_error") for blk in mcp_results):
                flags.append("c_all_mcp_errors")
                details["mcp_error_results"] = len(mcp_results)
    if any(sandbox_mod.asks_to_escape(b.get("input", {})) for b in tool_uses):
        flags.append("sandbox_escape_requested")
    return flags, details


# ------------------------------------------------------------------ session (isolated dirs and env)
def check_out_is_denied(out: pathlib.Path, repo: pathlib.Path, real_home: str) -> None:
    """Abort unless the run folder lies inside a folder that B's sandbox denies for reading: the repo, the main checkout
    (when the repo is a linked checkout) or the real home. The sandbox reads by deny-list, so a run folder anywhere
    else is readable by B's Bash: it holds the transcripts of the other conditions, of other models and of the earlier
    repetitions."""
    target = pathlib.Path(out).resolve()
    denied = [repo, pathlib.Path(real_home).resolve(), *(pathlib.Path(d).resolve()
                                                         for d in sandbox_mod.main_checkouts(repo))]
    if not any(target.is_relative_to(d) for d in denied):
        raise Abort(f"--out {target} lies outside the folders that the sandbox of condition B denies ({repo}, the main "
                    f"checkout and {real_home}), so B's Bash could read the transcripts of earlier runs; use a folder "
                    "inside one of them")


class Session:
    """Everything one invocation shares: isolated HOME, rendered config files, child env."""

    def __init__(self, *, dry_run: bool, gateway: bool, home: str, cfg_dir: str, env: dict[str, str],
                 claude_argv: list[str], real_claude: str | None, claude_version: str,
                 real_claude_version: str | None, repo: pathlib.Path, b_stack_info: dict | None = None,
                 real_home: str | None = None, settings_sha256: str | None = None,
                 runtime_dirs: list[str] | None = None, b_venv: str | None = None):
        self.b_stack = b_stack_info  # {path, bin, python, packages, digest} of the venv condition B runs in; None: no B
        self.dry_run, self.gateway, self.home, self.cfg_dir, self.env = dry_run, gateway, home, cfg_dir, env
        self.claude_argv, self.real_claude = claude_argv, real_claude
        self.claude_version, self.real_claude_version = claude_version, real_claude_version
        self.repo = repo
        self.real_home = real_home or str(pathlib.Path("~").expanduser())
        self.runtime_dirs = list(runtime_dirs or [])
        self.b_venv = b_venv or (b_stack_info or {}).get("path")
        self.settings_path = pathlib.Path(cfg_dir) / "sandbox-settings.json"
        self.ts_json_path = pathlib.Path(cfg_dir) / "ts.json"
        self.settings_sha256 = settings_sha256

    @classmethod
    def create(cls, *, dry_run: bool, gateway: bool, parent_env=None, repo: pathlib.Path = REPO_ROOT,
               b_venv: str | pathlib.Path | None = None, need_b: bool = True, create_b: bool = True,
               out: pathlib.Path | str | None = None) -> Session:
        """`b_venv`: the venv of condition B (default: TSBENCH_B_VENV, else ~/.cache/tsbench/venv-B). A real session
        creates/validates it when `need_b`, or only validates it when `create_b` is false; a dry run never creates it
        (it only describes it if it is already valid). `out`: the run folder; a real session with condition B refuses
        a folder that the sandbox does not deny (see `check_out_is_denied`)."""
        parent_env = os.environ if parent_env is None else parent_env
        repo = pathlib.Path(repo).resolve()
        real_home = str(pathlib.Path(parent_env.get("HOME") or "~").expanduser())
        if out is not None and need_b and not dry_run:
            check_out_is_denied(pathlib.Path(out), repo, real_home)
        b_info = None
        venv = None
        try:
            venv = b_stack.b_venv_dir(parent_env, str(b_venv) if b_venv else None, repo)
        except b_stack.BStackError as e:
            if need_b:
                raise Abort(f"B stack: {e}") from e
        if need_b:
            try:
                if dry_run:
                    try:
                        b_info = b_stack.validate(venv)
                    except b_stack.BStackError:
                        b_info = {"path": str(venv), "bin": str(b_stack.bin_dir(venv)), "python": None,
                                  "packages": {}, "digest": None}
                else:
                    b_info = b_stack.ensure_b_stack(venv) if create_b else b_stack.ensure_b_stack(venv, create=False)
            except b_stack.BStackError as e:
                raise Abort(f"B stack: {e}") from e
        if not dry_run:
            miss = missing_env(parent_env, gateway)
            if miss:
                raise Abort("required environment variable not set: " + ", ".join(miss))
        real = shutil.which("claude", path=parent_env.get("PATH"))
        real = os.path.abspath(real) if real else None
        if not dry_run and not real:
            raise Abort("`claude` not found on PATH")
        runtime = claude_runtime_dirs(real, parent_env.get("PATH", ""))
        offenders = path_offenders(child_path(runtime))
        if offenders:
            raise Abort("the child PATH would reach " + ", ".join(offenders) + "; condition B must not")

        tmp_root = tempfile.gettempdir()
        if pathlib.Path(tmp_root).resolve().is_relative_to(repo):
            raise Abort(f"TMPDIR {tmp_root} lies inside the repo; point TMPDIR elsewhere")
        if pathlib.Path(tmp_root).resolve().is_relative_to(pathlib.Path(real_home).resolve()):
            raise Abort(f"TMPDIR {tmp_root} lies inside the home directory, which the sandbox denies; point TMPDIR "
                        "elsewhere")
        home = tempfile.mkdtemp(prefix="tsbench-home-")
        cfg_dir = tempfile.mkdtemp(prefix="tsbench-cfg-")
        try:
            (pathlib.Path(home) / ".claude").mkdir(parents=True, exist_ok=True)
            cmd = find_mcp_command(repo)
            if cmd is None:
                if not dry_run:
                    raise Abort("tanabesugano-mcp not found in <repo>/.venv/bin or next to the Python interpreter")
                cmd = str(repo / ".venv" / "bin" / "tanabesugano-mcp")
            mpl_dir = mpl_cache_dir(parent_env, repo)
            if not dry_run:
                warm_mpl_cache(mpl_dir, pathlib.Path(cmd).parent / "python")
                if b_info:  # B's matplotlib is another install: its font cache is warmed too
                    warm_mpl_cache(mpl_dir, pathlib.Path(b_info["bin"]) / "python")
            env = build_child_env(parent_env, home=home, config_dir=str(pathlib.Path(home) / ".claude"),
                                  tmpdir=tmp_root, repo=repo, dry_run=dry_run, gateway=gateway,
                                  mpl_config_dir=None if dry_run else mpl_dir, runtime_dirs=runtime)
            (pathlib.Path(cfg_dir) / "ts.json").write_text(json.dumps(render_ts_json(cmd), indent=2) + "\n",
                encoding="utf-8")
            try:
                settings = sandbox_mod.settings_text(repo, real_home, b_venv=venv, mpl_dir=mpl_dir,
                                                     parent_env=parent_env)
            except ValueError as e:
                raise Abort(f"sandbox settings: {e}") from e
            (pathlib.Path(cfg_dir) / "sandbox-settings.json").write_text(settings, encoding="utf-8")
            settings_sha = plan_mod.sha256_text(settings)
            real_version = None
            if real:
                real_version = claude_version(real, env=env, cwd=home)
            if dry_run:
                argv, version = list(FAKE_ARGV), "fake-0"
            else:
                argv, version = [real], (real_version or "unknown")
        except BaseException:
            shutil.rmtree(home, ignore_errors=True)
            shutil.rmtree(cfg_dir, ignore_errors=True)
            raise
        return cls(dry_run=dry_run, gateway=gateway, home=home, cfg_dir=cfg_dir, env=env, claude_argv=argv,
                   real_claude=real, claude_version=version, real_claude_version=real_version, repo=repo,
                   b_stack_info=b_info, real_home=real_home, settings_sha256=settings_sha, runtime_dirs=runtime,
                   b_venv=str(venv) if venv else None)

    def child_env(self, cond_key: str | None = None) -> dict[str, str]:
        """The child environment. Condition B (only) gets the B venv's bin dir first on PATH; everything else gets
        `/usr/bin:/bin` plus claude's runtime dirs (built from scratch, see `child_path`)."""
        env = dict(self.env)
        if cond_key == "B" and self.b_stack:
            env["PATH"] = child_path(self.runtime_dirs, self.b_stack["bin"])
        return env

    # ---- what goes into records
    def placeholders(self, out: pathlib.Path | str | None = None) -> list[tuple[str, str]]:
        """(absolute path, placeholder) pairs, longest first: what a written record says instead of host paths."""
        entries: list = [(out, "<OUT>"), (self.cfg_dir, "<CFG>"), (self.home, "<ISO_HOME>"),
                         (self.b_venv, "<B_VENV>"), ((self.b_stack or {}).get("path"), "<B_VENV>"),
                         (self.repo, "<REPO>")]
        if self.real_claude:
            entries.append((self.real_claude, "<CLAUDE>"))
            entries.append((os.path.realpath(self.real_claude), "<CLAUDE>"))
        # claude's runtime dirs stay literal in child_path (e.g. /usr/local/lib/claude-code/<v>); one under the
        # real home is caught by <HOME> below
        if self.dry_run:
            entries.append((sys.executable, "<PYTHON>"))
        for base in b_stack.base_dirs(pathlib.Path(self.b_venv)) if self.b_venv else []:
            entries.append((base, "<B_BASE_PYTHON>"))
        entries.append((tempfile.gettempdir(), "<TMP>"))
        entries.append((self.real_home, "<HOME>"))
        return placeholder_pairs(entries)

    def record(self, obj, out: pathlib.Path | str | None = None):
        """A copy of `obj` with every host path replaced by its placeholder."""
        return redact(obj, self.placeholders(out))

    def recorded_child_path(self, cond_key: str | None = None) -> str:
        return redact(self.child_env(cond_key)["PATH"], self.placeholders())

    def close(self) -> None:
        shutil.rmtree(self.home, ignore_errors=True)
        shutil.rmtree(self.cfg_dir, ignore_errors=True)


# ------------------------------------------------------------------ image harvest
@dataclasses.dataclass
class Outcome:
    events: list
    init: dict | None
    mismatches: list
    result: dict | None
    exit_code: int | None
    wall_s: float
    stderr_tail: str
    timed_out: bool
    init_aborted: bool
    init_seen: bool = False  # claude emits init before its first API request
    spawn_failed: bool = False  # the process could not be started (a missing binary): no API request was sent
    artifacts: list = dataclasses.field(default_factory=list)  # [{name, sha256}] of the images harvested from the cwd

    @property
    def cost_usd(self) -> float | None:
        if self.result is None:
            return None
        return float(self.result.get("total_cost_usd") or 0.0)


def _kill_group(proc: subprocess.Popen) -> None:
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        try:
            proc.kill()
        except OSError:
            pass


def _redact_keys(text: str, env: dict[str, str]) -> str:
    """Replace the model credentials of `env` in `text`. Done on the whole text, before the tail is cut: a key that the
    cut splits would otherwise leave its second part behind."""
    for name in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"):
        secret = env.get(name)
        if secret and len(secret) >= 8:
            text = text.replace(secret, "[REDACTED]")
    return text


def execute(argv: list[str], prompt: str, env: dict[str, str], transcript: pathlib.Path,
            cond: cond_mod.Condition, model: str, *, timeout_s: float,
            disallowed: list[str] | tuple[str, ...] = ()) -> Outcome:
    """Run one call in a fresh empty temp cwd; stream stdout raw into `transcript`."""
    transcript = pathlib.Path(transcript)
    transcript.parent.mkdir(parents=True, exist_ok=True)
    cwd = tempfile.mkdtemp(prefix="tsbench-run-")
    stderr_f = tempfile.TemporaryFile()
    events: list = []
    init = None
    mismatches: list[str] = []
    artifacts: list[dict] = []
    state = {"timed_out": False}
    init_aborted = False
    t0 = time.monotonic()
    try:
        proc = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=stderr_f, cwd=cwd, env=env,
                                start_new_session=True)
    except OSError as e:  # a missing or not executable binary: the run has no result, the invocation goes on
        stderr_f.close()
        shutil.rmtree(cwd, ignore_errors=True)
        return Outcome(events=[], init=None, mismatches=[], result=None, exit_code=None,
                       wall_s=time.monotonic() - t0, stderr_tail=f"could not start {argv[0]}: {e}", timed_out=False,
                       init_aborted=False, spawn_failed=True)

    def on_timeout() -> None:
        state["timed_out"] = True
        _kill_group(proc)

    timer = threading.Timer(timeout_s, on_timeout)
    timer.daemon = True
    timer.start()
    try:
        try:
            proc.stdin.write(prompt.encode("utf-8"))
            proc.stdin.close()
        except (BrokenPipeError, OSError):
            pass
        awaiting_init = True
        with open(transcript, "wb") as tf:
            for raw in proc.stdout:
                tf.write(raw)
                tf.flush()
                line = raw.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                except ValueError:
                    ev = None
                if ev is not None:
                    events.append(ev)
                if awaiting_init:
                    # With a key set, claude can emit other system events (e.g. ui_invalidate)
                    # before init; they carry no model or tool information. Anything else first is wrong.
                    if isinstance(ev, dict) and ev.get("type") == "system" and ev.get("subtype") != "init":
                        continue
                    awaiting_init = False
                    init = ev
                    mismatches = (cond_mod.check_init(cond, ev, model, disallowed) if isinstance(ev, dict)
                                  else ["first non-system line is not a JSON object"])
                    if mismatches:
                        init_aborted = True
                        _kill_group(proc)
                        break
        if awaiting_init and not state["timed_out"]:  # the process ended before any init event
            mismatches = ["no init event"]
            init_aborted = True
    finally:
        timer.cancel()
        _kill_group(proc)  # also reaps stray grandchildren (MCP server, shells)
        try:
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:  # pragma: no cover
            pass
        try:
            stderr_f.seek(0)
            tail = _redact_keys(stderr_f.read().decode("utf-8", errors="replace"), env)[-STDERR_TAIL_CHARS:]
        finally:
            stderr_f.close()
        try:
            artifacts = harvest_artifacts(cwd, artifacts_dir_of(transcript))  # before the cwd is removed
        except Exception:  # noqa: BLE001 - never lose a run to the harvest
            artifacts = []
        shutil.rmtree(cwd, ignore_errors=True)
    wall = time.monotonic() - t0
    result = events[-1] if events and isinstance(events[-1], dict) and events[-1].get("type") == "result" else None
    return Outcome(events=events, init=init if isinstance(init, dict) else None, mismatches=mismatches,
                   result=result, exit_code=proc.returncode, wall_s=wall, stderr_tail=tail,
                   timed_out=state["timed_out"], init_aborted=init_aborted,
                   init_seen=isinstance(init, dict) and init.get("subtype") == "init", artifacts=artifacts)


# ------------------------------------------------------------------ HTTP 429: wait and run the same run again
def sleep(seconds: float) -> None:
    time.sleep(seconds)


def max_429_retries(parent_env=None) -> int:
    """Retries after an HTTP 429: 4 by default (len(RETRY_429_BACKOFF_S)), `TSBENCH_429_MAX_RETRIES` overrides,
    0 = off."""
    return env_int(os.environ if parent_env is None else parent_env, RETRY_429_ENV, len(RETRY_429_BACKOFF_S))


def max_429_in_a_row(parent_env=None) -> int:
    """How many runs in a row may end in HTTP 429 before the run set stops: 3 by default, `TSBENCH_429_STOP_AFTER`
    overrides, 0 = never stop on the count."""
    return env_int(os.environ if parent_env is None else parent_env, STOP_429_ENV, STOP_429_AFTER)


def max_api_errors_in_a_row(parent_env=None) -> int:
    """How many runs in a row may end in an API error other than HTTP 429, or without a result, before the run set
    stops: 3 by default, `TSBENCH_API_ERROR_STOP_AFTER` overrides, 0 = never stop on the count."""
    return env_int(os.environ if parent_env is None else parent_env, STOP_API_ERROR_ENV, STOP_API_ERROR_AFTER)


def backoff_s(retry_no: int, rng=random.random) -> float:
    """Seconds to wait before retry `retry_no` (1-based): 60, 120, 240, 480 (the last value repeats), plus jitter."""
    base = RETRY_429_BACKOFF_S[min(retry_no, len(RETRY_429_BACKOFF_S)) - 1]
    return round(base * (1 + RETRY_429_JITTER * rng()), 1)


def attempt_path(transcript: pathlib.Path, n: int) -> pathlib.Path:
    """`<stem>.attempt<N>.jsonl` next to the transcript (`find_transcripts` does not read these)."""
    return transcript.with_name(transcript.name[: -len(".jsonl")] + f".attempt{n}.jsonl")


def next_attempt_path(transcript: pathlib.Path) -> tuple[int, pathlib.Path]:
    """(N, path) of the first `<stem>.attempt<N>.jsonl` next to the transcript that does not exist yet."""
    n = 1
    while attempt_path(transcript, n).exists():
        n += 1
    return n, attempt_path(transcript, n)


def set_attempt_aside(transcript: pathlib.Path) -> int:
    """Keep an attempt that is not the final one: its transcript becomes `<stem>.attempt<N>.jsonl`, its images folder
    `<stem>.attempt<N>.artifacts/` and its sidecar `<stem>.attempt<N>.meta.json` (those two only if they exist), so
    that the next attempt starts clean and the report does not show an old image as the image of the final run.
    Returns N."""
    transcript = pathlib.Path(transcript)
    n, kept = next_attempt_path(transcript)
    stem = kept.name[: -len(".jsonl")]
    transcript.replace(kept)
    for old, new in ((artifacts_dir_of(transcript), kept.with_name(stem + ".artifacts")),
                     (meta_path(transcript), kept.with_name(stem + ".meta.json"))):
        if old.exists():
            old.replace(new)
    return n


def retire_earlier_attempt(transcript: pathlib.Path) -> dict | None:
    """--resume: move an unfinished transcript of this run aside as `<stem>.attempt<N>.jsonl` (with its images folder
    and sidecar, see `set_attempt_aside`) before the run is executed again, so that no earlier attempt is overwritten.
    Returns {attempt, reason, cost_usd} for the sidecar, or None when there is no earlier transcript.
    `cost_usd` is the cost that attempt reported (0 without a result)."""
    transcript = pathlib.Path(transcript)
    drop_stale_aborted_sidecar(transcript)
    if not transcript.exists():
        return None
    reason, cost = "no_result", 0.0
    ev = last_event(transcript)
    if ev is not None and ev.get("type") == "result":
        cost = float(ev.get("total_cost_usd") or 0.0)
        reason = ("rate_limited" if ev.get("is_error") and is_rate_limited(ev) else "api_error" if is_api_error(ev)
                  else "error_zero_cost" if ev.get("is_error") else "result")
    return {"attempt": set_attempt_aside(transcript), "reason": reason, "cost_usd": cost}


def drop_stale_aborted_sidecar(transcript: pathlib.Path) -> None:
    """An init-aborted attempt leaves its sidecar at the normal path and a copy beside `<stem>.attempt<N>.jsonl`. Before
    the run is executed again that sidecar is stale: drop it when it is the same as a copy, so that neither a rerun
    that is killed before it writes its own sidecar nor an HTTP 429 attempt of the rerun carries the aborted charge
    along a second time."""
    if is_stale_aborted_sidecar(transcript):
        meta_path(transcript).unlink()


def is_stale_aborted_sidecar(transcript: pathlib.Path) -> bool:
    """The sidecar at the normal path says `cell_aborted` and is the same as the copy beside a set-aside attempt."""
    try:
        text = meta_path(transcript).read_bytes()
        rec = json.loads(text)
    except (OSError, ValueError):
        return False
    if not isinstance(rec, dict) or rec.get("cell_aborted") is not True:
        return False
    stem = transcript.name[: -len(".jsonl")]
    return any(p.read_bytes() == text for p in transcript.parent.glob(f"{glob.escape(stem)}.attempt*.meta.json"))


def unfinished_cost(attempt: pathlib.Path) -> float:
    """The money an attempt that is not a finished run spent: the reported cost of a paid API error other than HTTP
    429, or, for an attempt without a result event, the charge the runner booked for it (the per-call cap, also for an
    attempt that aborted its cell on the init event), read from the sidecar that belongs to it. 0 for an HTTP 429
    (its price, if any, is an estimate), a zero-cost error, a missing transcript, a missing sidecar, or a sidecar
    that only repeats an aborted attempt's copy (`is_stale_aborted_sidecar`, its charge counts with that copy)."""
    try:
        ev = last_event(attempt)
    except OSError:
        return 0.0
    if ev is not None and ev.get("type") == "result":
        if (ev.get("is_error") and is_rate_limited(ev)) or not is_api_error(ev):
            return 0.0
        return float(ev.get("total_cost_usd") or 0.0)
    if is_stale_aborted_sidecar(attempt):
        return 0.0
    try:
        rec = json.loads(meta_path(attempt).read_text(encoding="utf-8"))
        return float(rec.get("cost_usd") or 0.0) if isinstance(rec, dict) else 0.0
    except (OSError, ValueError, TypeError):
        return 0.0


def paid_attempts_cost(transcript: pathlib.Path) -> float:
    """The money of the attempts of this run that an earlier --resume or an HTTP 429 retry set aside
    (`<stem>.attemptN.jsonl`, see `unfinished_cost`), which the transcript at the normal path does not show."""
    transcript = pathlib.Path(transcript)
    stem = transcript.name[: -len(".jsonl")]
    total = 0.0
    for attempt in sorted(transcript.parent.glob(f"{glob.escape(stem)}.attempt*.jsonl")):
        if re.fullmatch(r"\d+", attempt.name[len(stem) + len(".attempt"): -len(".jsonl")]):
            total += unfinished_cost(attempt)
    return total


def execute_with_retries(argv, prompt, env, transcript, cond, model, *, timeout_s, disallowed=(), parent_env=None):
    """`execute`, and while the run ended in HTTP 429: keep that attempt's transcript as `<stem>.attempt<N>.jsonl`, wait
    (exponential backoff with jitter) and run the same run again, at most `max_429_retries()` times. The last attempt
    stays at the normal path. A 429 that says the quota is used up (`quota_scope`) is not retried: waiting minutes
    cannot help, and each retry would spend one more request. Returns (outcome, retries) where retries is
    [{at, wait_s, status}], one per wait."""
    limit = max_429_retries(parent_env)
    retries: list[dict] = []
    while True:
        outcome = execute(argv, prompt, env, transcript, cond, model, timeout_s=timeout_s, disallowed=disallowed)
        limited = (outcome.result is not None and bool(outcome.result.get("is_error"))
                   and is_rate_limited(outcome.result))
        if not limited or len(retries) >= limit or quota_scope(outcome.result):
            return outcome, retries
        set_attempt_aside(transcript)
        wait = backoff_s(len(retries) + 1)
        retries.append({"at": utcnow(), "wait_s": wait, "status": str(outcome.result.get("api_error_status") or 429)})
        print(f"HTTP 429 for {transcript.name}: waiting {wait:.0f} s, then retry {len(retries)} of {limit}",
              flush=True)
        sleep(wait)


# ------------------------------------------------------------------ manifest
def write_json_atomic(path: pathlib.Path, obj) -> None:
    write_text_atomic(pathlib.Path(path), json.dumps(obj, indent=2, sort_keys=True, default=str) + "\n")


# ------------------------------------------------------------------ CLI
SELECTION_FLAGS = ("split", "models", "conditions", "effort", "k", "limit")


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(prog="tsbench run", description="Run the benchmark.")
    ap.add_argument("--plan", default=None, metavar="PLAN.JSONL",
                    help="execute this run plan; it replaces --split/--models/--conditions/--effort/--k/--limit")
    ap.add_argument("--split", choices=["pilot", "confirmatory"])
    ap.add_argument("--models", help="comma list of full model ids")
    ap.add_argument("--conditions", help="comma list from A,B,C")
    ap.add_argument("--effort", choices=EFFORTS)
    ap.add_argument("--k", type=int, help="repetitions per task x model x condition")
    ap.add_argument("--budget-usd", type=float, dest="budget_usd", default=None,
                    help="run-set guard: no run is STARTED once the spent total reaches it; "
                         "a running call is never cut")
    ap.add_argument("--per-call-usd", type=float, dest="per_call_usd", default=None,
                    help="optional cap for one call (--max-budget-usd); off by default")
    ap.add_argument("--out", required=True)
    ap.add_argument("--dry-run", action="store_true", dest="dry_run", help="use the fake claude; no cost")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--limit", type=int, default=None, help="first N tasks of the split")
    ap.add_argument("--gateway", action="store_true", help="use ANTHROPIC_BASE_URL/ANTHROPIC_AUTH_TOKEN")
    ap.add_argument("--i-have-preregistered", dest="preregistered", metavar="DOI", default=None)
    ap.add_argument("--b-venv", dest="b_venv", default=None, metavar="DIR",
                    help="venv of condition B (default: $TSBENCH_B_VENV, else ~/.cache/tsbench/venv-B); "
                         "created from data/conditions/b-stack.txt if missing")
    args = ap.parse_args(argv)
    if args.plan is None:
        missing = [f"--{n.replace('_', '-')}" for n in (*SELECTION_FLAGS[:5], "budget_usd")
                   if getattr(args, n) is None]
        if missing:
            ap.error("the following arguments are required: " + ", ".join(missing))
    else:
        given = [f"--{n}" for n in SELECTION_FLAGS if getattr(args, n) is not None]
        if given:
            ap.error(f"--plan replaces {', '.join(given)}: the plan is the only source of what runs")
    return args


def _sealed_refusal(plan) -> None:
    if plan.header["sealed"]:
        raise Abort("this is a sealed plan (header only, no run records); run the clear plan whose plan_id is "
                    f"{plan.plan_id}")


def _as_plan_error(fn, *a, **kw):
    try:
        return fn(*a, **kw)
    except plan_mod.PlanError as e:
        raise Abort(str(e)) from e


def _existing_plan_id(out: pathlib.Path) -> str | None:
    for name in (plan_mod.PLAN_NAME, plan_mod.SEALED_NAME):
        try:
            return json.loads((out / name).read_text(encoding="utf-8").splitlines()[0])["plan_id"]
        except (OSError, ValueError, IndexError, KeyError, TypeError):
            continue
    return None


def _first_claude_pin(out: pathlib.Path) -> str | None:
    """The claude version that the plan file of the run set (clear or sealed) pins, or None."""
    for name in (plan_mod.PLAN_NAME, plan_mod.SEALED_NAME):
        try:
            pin = json.loads((out / name).read_text(encoding="utf-8").splitlines()[0])["pins"]["claude_cli_version"]
        except (OSError, ValueError, IndexError, KeyError, TypeError):
            continue
        return pin if isinstance(pin, str) and pin else None
    return None


@contextlib.contextmanager
def termination_as_interrupt():
    """SIGTERM (`kill`, `timeout`, a scheduler's wall-time limit) and SIGHUP (a dropped ssh session) take the path of
    Ctrl-C: KeyboardInterrupt, so the claude process group is killed, the manifest and README are written and the
    session is closed. Without it the runner dies at once and the claude child (its own session) runs on. The old
    handlers come back on exit; a signal that is ignored on purpose (`nohup`) stays ignored; outside the main
    thread (no handler can be set there) nothing changes."""
    old = {}
    for sig in (signal.SIGTERM, signal.SIGHUP):
        if signal.getsignal(sig) == signal.SIG_IGN:  # ignored on purpose (`nohup`): stays ignored
            continue
        try:
            old[sig] = signal.signal(sig, signal.default_int_handler)
        except ValueError:  # not the main thread
            break
    try:
        yield
    finally:
        for sig, handler in old.items():
            signal.signal(sig, handler)


def main(argv: list[str] | None = None) -> int:
    with termination_as_interrupt():
        return _main(argv)


def _main(argv: list[str] | None) -> int:
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    args = parse_args(raw_argv)
    given = dict(vars(args))  # the flags as given, before the plan fills them in (inputs/commands.sh repeats these)
    out = pathlib.Path(args.out).resolve()
    plan = None
    if args.plan:
        plan = _as_plan_error(plan_mod.load_plan, args.plan)
        _sealed_refusal(plan)
        spec = plan.header["spec"]
        # the namespace carries the values the manifest records
        args.split, args.k, args.models = spec["split"], spec["k"], ",".join(spec["models"])
        if any(r["split"] == "confirmatory" for r in plan.runs):  # the guard follows the run records, not the header
            args.split = "confirmatory"
        args.conditions, args.effort = ",".join(spec["conditions"]), ",".join(spec["efforts"])
        args.gateway = bool(args.gateway or spec["gateway"])
        if args.budget_usd is None:
            args.budget_usd = plan.header["budget_usd_total"]

    # 1. the confirmatory guard comes before anything else
    _as_plan_error(plan_mod.require_preregistration, args.split, args.preregistered)

    # 2. argument checks (the flags form shares them with `tsbench plan build`)
    if args.plan is None:
        spec = _as_plan_error(plan_mod.spec_from_flags, split=args.split, models=args.models,
                              conditions=args.conditions, efforts=args.effort, k=args.k, budget_usd=args.budget_usd,
                              limit=args.limit, gateway=args.gateway)
    if args.budget_usd <= 0:
        raise Abort("--budget-usd must be > 0")
    if args.per_call_usd is not None and args.per_call_usd <= 0:
        raise Abort("--per-call-usd must be > 0")

    # 3. pinned library
    try:
        ts_version = importlib.metadata.version("tanabesugano")
    except importlib.metadata.PackageNotFoundError as e:
        raise Abort("tanabesugano is not installed") from e
    if ts_version != REQUIRED_TANABESUGANO:
        raise Abort(f"tanabesugano=={REQUIRED_TANABESUGANO} required, found {ts_version}")

    # 4. the plan: given, or built in memory from the flags
    stored_plan = False  # the flags form took the plan file of the first invocation, with the pins it wrote
    if plan is None:
        try:
            # the claude version is pinned below from the live session; B is built by the session when it is missing
            plan = _as_plan_error(plan_mod.build_from_spec, spec, b_venv=args.b_venv, claude_cli_version=None)
        except b_stack.BStackError as e:
            raise Abort(f"B stack: {e}") from e
        if args.resume and args.split == "pilot":  # keep the file (and its timestamp) that the first invocation wrote
            try:
                earlier = plan_mod.load_plan(out / plan_mod.PLAN_NAME)
                if earlier.plan_id == plan.plan_id:
                    plan, stored_plan = earlier, True
            except plan_mod.PlanError:
                pass
        # a --resume that extends the matrix has a new plan_id, but the CLI is still held to the version of the first
        # invocation: an update in between is recorded as pin drift (confirmatory: abort)
        first_claude = _first_claude_pin(out) if args.resume and not stored_plan else None
        if first_claude:
            plan.header["pins"]["claude_cli_version"], stored_plan = first_claude, True
    else:
        for m in dict.fromkeys(r["model"] for r in plan.runs):
            why = validate_model_id(m, args.gateway)
            if why:
                raise Abort(why)
    for r in plan.runs:
        if plan_mod.tools_expected(r["condition"]) != r["tools_expected"]:
            raise Abort(f"{r['run_id']}: tools_expected in the plan disagrees with conditions.py")
        # a record without answer_schema is `fit`
        try:
            live_schema = cond_mod.get_answer_schema(r.get("answer_schema"))
        except ValueError as e:
            raise Abort(f"{r['run_id']}: {e}") from e
        if r.get("answer_schema_sha256", live_schema.sha256) != live_schema.sha256:
            raise Abort(f"{r['run_id']}: answer schema {live_schema.name!r} in the plan disagrees with the schema file")
        # the plan describes the argv and the flags of every run (the record decides the turn limit and the blocked
        # tools): what it stores must be what the code builds now
        if "expected_flags" in r and list(r["expected_flags"]) != plan_mod.EXPECTED_FLAGS[r["condition"]]:
            raise Abort(f"{r['run_id']}: expected_flags in the plan disagrees with conditions.py")
        if "argv_template" in r and r["argv_template"] != plan_mod.argv_template(
                r["condition"], r["model"], r["effort"], r["max_turns"], live_schema.name,
                disallowed_of(r, bool(args.gateway))):
            raise Abort(f"{r['run_id']}: argv_template in the plan disagrees with build_argv")

    session = Session.create(dry_run=args.dry_run, gateway=args.gateway, b_venv=args.b_venv,
                             need_b=any(r["condition"] == "B" for r in plan.runs), out=out)
    try:
        live_claude = None if args.dry_run else session.real_claude_version
        if args.plan is None and live_claude and not stored_plan:
            plan.header["pins"]["claude_cli_version"] = live_claude  # the flags form: the plan describes this very run
        drift = plan_mod.check_pins(plan.header["pins"], plan_mod.live_pins(
            live_claude, session.repo, b_stack_sha256=(session.b_stack or {}).get("digest"),
            sandbox_settings_sha256=session.settings_sha256))
        if drift and args.split == "confirmatory":
            raise Abort("pinned environment drifted from the plan (confirmatory aborts): "
                        + "; ".join(f"{d['pin']}: planned {d['planned']!r}, live {d['live']!r}" for d in drift))
        for d in drift:
            print(f"WARNING pin drift (pilot, recorded in the manifest): {d['pin']}: planned {d['planned']!r}, "
                  f"live {d['live']!r}", file=sys.stderr, flush=True)
        with run_set_lock(out):
            return _run(args, session, out, plan, ts_version, drift, given=given, raw_argv=raw_argv)
    finally:
        session.close()


@contextlib.contextmanager
def run_set_lock(out: pathlib.Path):
    """Hold an exclusive lock on `<out>/.run.lock` while one invocation writes into the run folder. A second
    invocation on the same folder (a `--resume` of a run that is still going, one invocation per model) would retire
    the transcript the first one is writing and overwrite its manifest, plan and inputs: it stops with a message. The
    lock goes with the process, so a crash leaves nothing to clean up."""
    out = pathlib.Path(out)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / RUN_LOCK_NAME, "a", encoding="utf-8") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as e:
            raise Abort(f"another tsbench run is writing to {out} ({RUN_LOCK_NAME} is locked); wait until it has "
                        "ended, or use another --out") from e
        yield


# Gateway models that call Bash with the probe script verbatim; the first one in the plan runs the sandbox probe.
GATEWAY_PROBE_MODELS = ("gwdg-qwen3.5-397b", "gwdg-qwen3-coder-next")


def probe_model_for(models: list[str], gateway: bool) -> str:
    """The model of the sandbox probe. Direct: `sandbox_mod.PROBE_MODEL`. Gateway: the first of `GATEWAY_PROBE_MODELS`
    that the plan has, else the first plan model by name. The order of `--models` never decides it: a small model
    that mangles tool arguments would not run the script, and that says nothing about the sandbox."""
    if not gateway:
        return sandbox_mod.PROBE_MODEL
    return next((m for m in GATEWAY_PROBE_MODELS if m in models), None) or min(models)


SYSTEM_PROMPTS_DIR = "system-prompts"


def system_prompt_path(out: pathlib.Path, record: dict) -> str:
    """The system prompt of a plan record as a file in the run folder: the plan decides the prompt, so an edit of the
    package file after the plan was built changes nothing. The sidecar names it as `<OUT>/system-prompts/...`, which
    the report resolves against the run folder (also for a sealed plan, which has no run records). The name holds the
    hash of the text, so a file that is there already is the same text."""
    path = pathlib.Path(out) / SYSTEM_PROMPTS_DIR / f"system-prompt-{record['system_prompt_sha256'][:16]}.txt"
    try:
        same = path.read_text(encoding="utf-8") == record["system_prompt_text"]
    except OSError:
        same = False
    if not same:
        write_text_atomic(path, record["system_prompt_text"])
    return str(path)


def _sha256_file(path: pathlib.Path) -> str | None:
    try:
        return sha256_file(path)
    except OSError:
        return None


def recorded_args(args, session: Session, out: pathlib.Path) -> dict:
    """The CLI arguments as the manifest records them: every path relative to the repo or a placeholder;
    `--out` relative to the repo when it is inside it. reproduce.py / compare.py read gateway, budget_usd, models,
    conditions, dry_run and plan from here."""
    d = dict(vars(args))
    if d.get("gateway"):  # the endpoint the run really used: scheme, host and port of ANTHROPIC_BASE_URL, no token
        d["gateway_url"] = cond_mod.gateway_base_url(session.env.get("ANTHROPIC_BASE_URL"))
    for key in ("out", "plan", "b_venv"):
        v = d.get(key)
        if not v:
            continue
        pth = pathlib.Path(v).absolute()
        try:
            d[key] = pth.resolve().relative_to(session.repo).as_posix()
        except ValueError:
            d[key] = redact(str(pth), session.placeholders(out if key != "out" else None))
    return d


_RUN_FILE = re.compile(r"-k\d+(\.attempt\d+)?\.jsonl$")  # a transcript or a kept earlier attempt of one


def holds_run_set(out: pathlib.Path) -> bool:
    """True when `out` holds a run set: a MANIFEST.json or a transcript (`<model>/<cond>/<effort>/<task>-k<i>`)."""
    out = pathlib.Path(out)
    return (out / "MANIFEST.json").exists() or any(
        p.is_file() and _RUN_FILE.search(p.name) for p in out.glob("*/*/*/*.jsonl"))


def disallowed_of(r: dict, gateway: bool) -> list[str]:
    """The tools a run blocks: the plan record decides; a record without the field gets the live rule."""
    if "disallowed_tools" in r:
        return list(r["disallowed_tools"])
    return cond_mod.disallowed_tools(r["condition"], r["model"], gateway)


def argv_of(session: Session, out: pathlib.Path, r: dict, per_call: float | None, disallowed: list[str]) -> list[str]:
    """The claude argv of one plan record."""
    cond = cond_mod.get(r["condition"])
    return build_argv(session.claude_argv, cond, r["model"], r["effort"], per_call,
                      system_prompt_file=system_prompt_path(out, r),
                      settings_path=str(session.settings_path) if cond.uses_settings else None,
                      mcp_config_path=str(session.ts_json_path) if cond.uses_mcp else None,
                      max_turns=r["max_turns"],
                      answer_schema=r.get("answer_schema") or cond_mod.DEFAULT_ANSWER_SCHEMA,
                      disallowed_tools=disallowed)


def manifest_view(meta: dict) -> dict:
    """What one run sidecar contributes to the manifest lists (`flagged_runs`, `reported_models`, `aborted_cells`)."""
    return {"flags": list(meta.get("flags") or []), "reported_model": meta.get("reported_model"),
            "aborted": bool(meta.get("cell_aborted")), "mismatches": list(meta.get("init_mismatches") or [])}


def sidecar_facts_from_transcript(tp: pathlib.Path, r: dict, disallowed: list[str]) -> dict:
    """The sidecar fields that the events of a finished transcript decide: flags, cost, init check, reported model and
    the harvested images. `--resume` uses it for a run that ended in a result but has no sidecar (the invocation was
    interrupted between the two writes). Raises OSError when the transcript cannot be read."""
    events: list[dict] = []
    for line in pathlib.Path(tp).read_text(encoding="utf-8", errors="replace").split("\n"):
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if isinstance(ev, dict):
            events.append(ev)
    result = events[-1] if events and events[-1].get("type") == "result" else None
    init = next((e for e in events if e.get("type") == "system" and e.get("subtype") == "init"), None)
    cond = cond_mod.get(r["condition"])
    flags: list[str] = []
    if result is None:
        flags += ["cost_unknown", "no_result_event"]
    elif result.get("is_error"):
        flags.append("result_is_error")
    f2, details = compute_flags(r["condition"], events, result)
    adir = artifacts_dir_of(pathlib.Path(tp))
    artifacts = []
    for f in sorted(adir.iterdir()) if adir.is_dir() else []:
        sha = _sha256_file(f)
        if f.is_file() and sha:
            artifacts.append({"name": f.name, "sha256": sha})
    return {
        "flags": flags + f2, "flag_details": details,
        "init_mismatches": (cond_mod.check_init(cond, init, r["model"], disallowed) if init
                            else ["no init event in the transcript"]),
        "reported_model": (init or {}).get("model"),
        "cost_usd": float((result or {}).get("total_cost_usd") or 0.0), "cost_unknown": result is None,
        "artifacts": artifacts,
        "image_sha_match": image_sha_match((result or {}).get("structured_output"), artifacts),
    }


def manifest_lists(plan: list[dict], views: dict[str, dict]) -> dict:
    """`flagged_runs`, `reported_models` and `aborted_cells` of the manifest from the views of every planned run that
    has a sidecar (this invocation's runs and those of earlier invocations), in plan order."""
    flagged, reported, cells = [], {}, {}
    for r in plan:
        view = views.get(r["run_id"])
        if view is None:
            continue
        if view["flags"]:
            flagged.append({"run_id": r["run_id"], "flags": view["flags"]})
        if view["reported_model"]:
            reported.setdefault(r["model"], {}).setdefault(r["condition"], set()).add(view["reported_model"])
        cell = (r["model"], r["condition"], r["effort"])
        if view["aborted"] and cell not in cells:
            cells[cell] = {"model": cell[0], "condition": cell[1], "effort": cell[2], "first_run": r["run_id"],
                           "reasons": view["mismatches"]}
    return {"flagged_runs": flagged, "aborted_cells": list(cells.values()),
            "reported_models": {mm: {cc: sorted(v) for cc, v in d.items()} for mm, d in reported.items()}}


def _earlier_start(manifest_path: pathlib.Path) -> str | None:
    """`start_time_utc` of the manifest an earlier invocation left (the start of the run set), or None."""
    try:
        start = json.loads(manifest_path.read_text(encoding="utf-8")).get("start_time_utc")
    except (OSError, ValueError, AttributeError):
        return None
    return start if isinstance(start, str) else None


def _run(args, session: Session, out: pathlib.Path, plan_obj, ts_version, drift, *, given: dict | None = None,
         raw_argv: list[str] | None = None) -> int:
    out.mkdir(parents=True, exist_ok=True)
    manifest_path = out / "MANIFEST.json"
    sealed_split = args.split == "confirmatory"
    # --plan --resume continues that plan or nothing: another plan_id would mix two experiments in one directory.
    # The flags form may extend the matrix on resume (e.g. a larger --k), so its plan_id legitimately changes.
    if args.resume and args.plan:
        prior = _existing_plan_id(out)
        if prior is None and manifest_path.exists():
            try:
                prior = json.loads(manifest_path.read_text(encoding="utf-8")).get("plan_id")
            except (OSError, ValueError):
                prior = None
        if prior and prior != plan_obj.plan_id:
            raise Abort(f"--resume: {out} holds plan_id {prior}, this invocation has {plan_obj.plan_id}")
    if args.resume:
        # the flags form builds its plan_id from the live files, so finished runs are compared one by one
        conflict = resume_conflict(out, plan_obj.runs)
        if conflict:
            raise Abort(f"--resume: {conflict}. Finished runs of another configuration cannot be continued; "
                        "use a new --out folder")
    elif holds_run_set(out):  # a second run would truncate finished, paid transcripts and break the hash chain
        raise Abort(f"{out} already holds a run set (MANIFEST.json or transcripts); continue it with --resume, or use "
                    "a new --out folder")
    first_start = _earlier_start(manifest_path) if args.resume else None  # the run set began with the first invocation
    if manifest_path.exists():
        stamp = dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%S%fZ")
        manifest_path.rename(out / f"MANIFEST.prev-{stamp}.json")

    # the plan is written before the first call: pilot in clear, confirmatory as a sealed header only
    if sealed_split:
        plan_mod.write_sealed(plan_obj, out / plan_mod.SEALED_NAME)
        plan_file = None
    else:
        plan_file = out / plan_mod.PLAN_NAME
        earlier_id = _existing_plan_id(out)
        if earlier_id != plan_obj.plan_id:
            if plan_file.exists():
                plan_file.rename(out / f"plan.prev-{earlier_id[:16] if earlier_id else 'unknown'}.jsonl")
            plan_mod.write_plan(plan_obj, plan_file)
    plan_sha = plan_obj.sha256

    plan = plan_obj.runs
    planned = len(plan)
    efforts = list(dict.fromkeys(r["effort"] for r in plan))
    models = list(dict.fromkeys(r["model"] for r in plan))
    conds = list(dict.fromkeys(r["condition"] for r in plan))
    budget = float(args.budget_usd)
    env_names = sorted(set(session.env) | ({"FAKE_SEED"} if args.dry_run else set()))
    git_commit = git_output(REPO_ROOT, "rev-parse", "HEAD")
    git_dirty = git_output(REPO_ROOT, "status", "--porcelain")
    claude_ver = ({"used": "fake", "fake": "fake-0", "real": session.real_claude_version} if args.dry_run
                  else {"used": "real", "real": session.claude_version})
    task_ids = list(dict.fromkeys(r["task_id"] for r in plan))
    host, host_source = host_label(os.environ, plan_obj.plan_id)

    m: dict = {
        "schema": 2, "finished": False, "interrupted": False,
        "git_commit": git_commit, "git_dirty": None if git_dirty is None else ("yes" if git_dirty else "no"),
        "claude_version": claude_ver,
        "python_version": sys.version, "tanabesugano_version": ts_version,
        "host": host, "host_source": host_source, "platform": platform.platform(),
        "sandbox": sandbox_mod.method_info(None, args.dry_run),
        "start_time_utc": first_start or utcnow(), "end_time_utc": None,
        "args": recorded_args(args, session, out),
        # the literal child PATH per condition (host paths as placeholders, see `placeholders`)
        "child_path": {c: session.recorded_child_path(c) for c in conds},
        "sandbox_settings_sha256": session.settings_sha256,
        "split": args.split, "models_requested": models, "conditions": conds,
        "effort": efforts[0] if len(efforts) == 1 else efforts, "k": max(r["k"] for r in plan),
        "tasks": task_ids if args.split == "pilot" else len(task_ids),
        "reported_models": {},
        "env_var_names": env_names,
        "counts": {"planned": planned, "done": 0, "rate_limited": 0, "skipped": 0, "aborted": 0, "not_run_sandbox": 0,
                   "not_run_probe_not_evaluable": 0, "not_run_budget": 0, "not_run_quota": 0},
        "aborted_cells": [], "flagged_runs": [],
        "total_cost_usd": 0.0, "estimated_cost_usd": 0.0, "budget_usd": budget, "stopped_by_budget": False,
        # set when the quota ended the run:
        # {reason: quota_exhausted, scope: daily|monthly|unknown|None, after_runs, run_id}
        "stop": None,
        # where the exact input is, and what was run against it
        "plan_id": plan_obj.plan_id, "plan_sha256": plan_sha,
        "plan_file": None if plan_file is None else plan_file.name,
        "plan_sealed": sealed_split, "tasks_sha256": plan_obj.header["tasks_sha256"],
        "pin_drift": drift, "transcripts": {},
    }
    counts = m["counts"]

    views: dict[str, dict] = {}  # run_id -> manifest_view of its sidecar: earlier invocations' runs and this one's

    def save() -> None:
        m["end_time_utc"] = utcnow()
        m["total_cost_usd"] = round(spent, 6)
        m["estimated_cost_usd"] = round(estimated, 6)
        m.update(manifest_lists(plan, views))
        write_json_atomic(manifest_path, session.record(m, out))

    # already-spent cost of finished runs (resume). `estimated` is what Claude Code reported in total; `spent` is what
    # counts against the budget. A gateway run is not counted in USD: the price Claude Code prints for its models is an
    # estimate, so it is kept apart and never reaches the budget guard, `total_cost_usd` or a per-call cap.
    spent = 0.0
    estimated = 0.0

    def book(cost: float) -> None:
        nonlocal spent, estimated
        estimated += cost
        if not args.gateway:
            spent += cost

    done_before: dict[int, bool] = {}
    if args.resume:
        for idx, r in enumerate(plan):
            done_tp = transcript_path(out, r["model"], r["condition"], r["effort"], r["task_id"], r["k"])
            ok, cost = transcript_status(done_tp)
            book(paid_attempts_cost(done_tp))  # the paid errors that earlier invocations set aside
            if ok:
                done_before[idx] = True
                book(cost)
                # every finished transcript is listed, also when a budget or quota stop ends this invocation early
                m["transcripts"][r["run_id"]] = _sha256_file(done_tp)
            else:  # an unfinished attempt at the normal path is money on disk before the guard lets the run start
                book(unfinished_cost(done_tp))
            try:  # what an earlier invocation recorded about this run stays in the manifest until the run is redone
                views[r["run_id"]] = manifest_view(json.loads(meta_path(done_tp).read_text(encoding="utf-8")))
            except (OSError, ValueError, AttributeError):
                pass
    m["b_stack"] = session.b_stack if "B" in conds else None
    if "B" not in conds:
        m["sandbox"] = {"method": "n/a (condition B not requested)", "reason": None, "container": None, "probe": None}
    elif not args.dry_run:  # a still valid probe from an earlier invocation
        earlier = sandbox_mod.load_reusable_probe(out, session.claude_version, session.settings_sha256,
                                                  (session.b_stack or {}).get("digest"),
                                                  auth=sandbox_mod.auth_mode(session))
        if earlier is not None:
            m["sandbox"] = sandbox_mod.method_info(earlier, False)
    save()
    # the inputs next to the outputs (inputs/, run_set.json, README.md); README again when the run ends
    given = dict(vars(args)) if given is None else given
    inputs_mod.write_start(out, given=given, plan_obj=plan_obj, sealed=sealed_split, manifest=m,
                           record=lambda obj: session.record(obj, out),
                           original=inputs_mod.shell_line(["tsbench", "run", *(raw_argv or [])]),
                           fake_env={k: v for k, v in os.environ.items() if k in FAKE_PASSTHROUGH} if args.dry_run
                           else None, resume=bool(args.resume))

    aborted: dict[tuple, str] = {}
    # blocked: the probe failed, B is skipped. not_evaluable: the probe ended in an API error, so nothing was checked;
    # B does not run in this invocation either (no B run in an unchecked sandbox) and --resume probes again.
    sandbox_state = {"checked": False, "blocked": False, "not_evaluable": False}
    probe_model = probe_model_for(models, bool(args.gateway))

    def ensure_sandbox() -> None:
        sandbox_state["checked"] = True
        if args.dry_run:
            return
        rec = sandbox_mod.load_reusable_probe(out, session.claude_version, session.settings_sha256,
                                              (session.b_stack or {}).get("digest"),
                                              auth=sandbox_mod.auth_mode(session))
        if rec is None:
            print("sandbox probe: running (one real call, cost counts toward the budget)", flush=True)
            rec = sandbox_probe.run_probe(session, out, model=probe_model, remaining_usd=budget - spent)
            book(rec["cost_usd"])
        else:
            print("sandbox probe: reusing sandbox_probe.json (version and settings hash match)", flush=True)
        m["sandbox"] = sandbox_mod.method_info(rec, False)
        if rec["passed"] is None:  # an API error: nothing was tested, nothing failed. The next invocation probes again
            sandbox_state["not_evaluable"] = True
            print("sandbox probe NOT EVALUABLE: condition B is not run now and not marked failed; "
                  "--resume probes again. " + m["sandbox"]["reason"], file=sys.stderr, flush=True)
        elif not rec["passed"]:
            sandbox_state["blocked"] = True
            print("sandbox probe FAILED: condition B is skipped. " + m["sandbox"]["reason"],
                  file=sys.stderr, flush=True)

    def tally_rest(start: int, bucket: str = "not_run_budget") -> None:
        """The budget (or the quota) stopped the run at plan index `start`: classify everything not executed; what is
        left over goes into `bucket`."""
        for j in range(start, planned):
            rr = plan[j]
            if j in done_before:  # finished in an earlier invocation, whatever happened to its cell since
                counts["skipped"] += 1
            elif (rr["model"], rr["condition"], rr["effort"]) in aborted:
                counts["aborted"] += 1
            elif rr["condition"] == "B" and sandbox_state["blocked"]:
                counts["not_run_sandbox"] += 1
            elif rr["condition"] == "B" and sandbox_state["not_evaluable"]:
                counts["not_run_probe_not_evaluable"] += 1
            else:
                counts[bucket] = counts.get(bucket, 0) + 1  # `not_run_api_errors` exists only after such a stop

    per_call_cap = getattr(args, "per_call_usd", None)  # None: no per-call cap (the default)
    interrupted = False
    crashed = False
    stop_after = max_429_in_a_row()
    in_a_row = 0  # runs in a row that ended in HTTP 429 after their retries
    stop_after_errors = max_api_errors_in_a_row()
    errors_in_a_row = 0  # runs in a row that ended in another API error or without a result (a 429 is neither)
    failed_runs = answered_runs = 0  # runs of this invocation without an answer (not a 429), and with one
    try:
        for idx, r in enumerate(plan):
            tid, effort = r["task_id"], r["effort"]
            cell = (r["model"], r["condition"], effort)
            rid = r["run_id"]
            tp = transcript_path(out, r["model"], r["condition"], effort, tid, r["k"])
            if idx in done_before:  # finished in an earlier invocation: skipped, also when its cell aborts now
                counts["skipped"] += 1
                if not meta_path(tp).exists():  # interrupted between the result and the sidecar: rebuild the sidecar
                    disallowed = disallowed_of(r, bool(args.gateway))
                    try:
                        meta = {
                            "run_id": rid, "model": r["model"], "condition": r["condition"], "effort": effort,
                            "task_id": tid, "k": r["k"], "argv": argv_of(session, out, r, None, disallowed),
                            "prompt_via": "stdin", "exit_code": None, "wall_time_s": None, "stderr_tail": "",
                            "env_var_names": env_names,
                            "sandbox_method": (m.get("sandbox") or {}).get("method") if r["condition"] == "B"
                            else "n/a",
                            "retries": [], "earlier_attempt": None, "disallowed_tools": disallowed,
                            "max_turns": r["max_turns"], "timed_out": False, "cell_aborted": False,
                            "claude_version": session.claude_version, "started_utc": None,
                            "plan_id": plan_obj.plan_id, "prompt_sha256": r["prompt_sha256"],
                            "system_prompt_sha256": r["system_prompt_sha256"],
                            **sidecar_facts_from_transcript(tp, r, disallowed), "sidecar_rebuilt": True,
                        }
                        write_json_atomic(meta_path(tp), session.record(meta, out))
                    except OSError as e:
                        print(f"WARNING {rid}: its sidecar is missing and could not be rebuilt: {e}",
                              file=sys.stderr, flush=True)
                    else:
                        views[rid] = manifest_view(meta)
                        save()
                continue
            if cell in aborted:
                counts["aborted"] += 1
                continue
            if spent >= budget:  # run-set guard: never START a run once the total is reached
                m["stopped_by_budget"] = True
                tally_rest(idx)
                print(f"budget reached (spent USD {spent:.4f} of {budget:.2f}); stopping cleanly", flush=True)
                break
            if r["condition"] == "B":
                if not sandbox_state["checked"]:
                    ensure_sandbox()
                    save()
                if sandbox_state["blocked"]:
                    counts["not_run_sandbox"] += 1
                    continue
                if sandbox_state["not_evaluable"]:
                    counts["not_run_probe_not_evaluable"] += 1
                    continue
                if spent >= budget:  # the probe may have used the rest
                    m["stopped_by_budget"] = True
                    tally_rest(idx)
                    print("budget reached after the sandbox probe; stopping cleanly", flush=True)
                    break

            # no cap on a gateway: Claude Code would cut the call at its own price estimate (error_max_budget_usd)
            per_call = None if per_call_cap is None or args.gateway else min(budget - spent, per_call_cap)
            cond = cond_mod.get(r["condition"])
            disallowed = disallowed_of(r, bool(args.gateway))
            argv = argv_of(session, out, r, per_call, disallowed)
            env = session.child_env(r["condition"])
            if args.dry_run:
                env["FAKE_SEED"] = rid
            earlier = retire_earlier_attempt(tp) if args.resume else None  # its money was booked before the loop
            started = utcnow()
            outcome, retries = execute_with_retries(argv, r["prompt"], env, tp, cond, r["model"],
                                                    timeout_s=WALL_TIMEOUT_S, disallowed=disallowed)

            flags: list[str] = []
            details: dict = {}
            reported = (outcome.init or {}).get("model")

            cost_unknown = outcome.result is None
            # No result event: charge the per-call cap if there is one (else nothing is known and 0 is booked; the
            # run carries `cost_unknown`), and nothing if the run was killed before init, when no API request can
            # have been sent yet (init precedes the first request).
            if not cost_unknown:
                cost = outcome.cost_usd
            elif outcome.spawn_failed or (outcome.init_aborted and not outcome.init_seen):
                cost = 0.0
            else:
                cost = per_call or 0.0
            book(cost)
            aborted_aside = None
            if cost_unknown:
                flags.append("cost_unknown")
                flags.append("timeout" if outcome.timed_out else "no_result_event")
            elif outcome.result.get("is_error"):
                flags.append("result_is_error")
            if outcome.init_aborted:
                if tp.exists():  # a partial transcript is not an answer: keep it aside, the scorer does not read it
                    aborted_aside = next_attempt_path(tp)[1]
                    tp.replace(aborted_aside)
                aborted[cell] = "; ".join(outcome.mismatches)
                counts["aborted"] += 1
                print(f"ABORT CELL {r['model']}/{r['condition']}/{effort}: {aborted[cell]}",
                      file=sys.stderr, flush=True)
            else:
                f2, details = compute_flags(r["condition"], outcome.events, outcome.result)
                flags += f2
                counts["rate_limited" if "rate_limited" in f2 else "done"] += 1
                if "rate_limited" not in f2:
                    if cost_unknown or is_api_error(outcome.result):
                        failed_runs += 1
                        errors_in_a_row += 1
                    else:
                        answered_runs += 1
                        errors_in_a_row = 0

            meta = {
                "run_id": rid, "model": r["model"], "condition": r["condition"], "effort": effort, "task_id": tid,
                "k": r["k"],
                "argv": argv, "prompt_via": "stdin", "exit_code": outcome.exit_code,
                "wall_time_s": round(outcome.wall_s, 3), "stderr_tail": outcome.stderr_tail,
                "env_var_names": env_names,
                "sandbox_method": (m["sandbox"]["method"] if r["condition"] == "B" else "n/a"),
                "retries": retries, "earlier_attempt": earlier, "disallowed_tools": disallowed,
                "max_turns": r["max_turns"],
                "flags": flags, "flag_details": details, "init_mismatches": outcome.mismatches,
                "reported_model": reported, "cost_usd": cost, "cost_unknown": cost_unknown,
                "timed_out": outcome.timed_out, "cell_aborted": outcome.init_aborted,
                "claude_version": session.claude_version, "started_utc": started,
                "plan_id": plan_obj.plan_id, "prompt_sha256": r["prompt_sha256"],
                "system_prompt_sha256": r["system_prompt_sha256"],
                "artifacts": outcome.artifacts,
                "image_sha_match": image_sha_match((outcome.result or {}).get("structured_output"), outcome.artifacts),
            }
            write_json_atomic(meta_path(tp), session.record(meta, out))
            if aborted_aside is not None:  # the charge stays beside the set-aside transcript
                write_json_atomic(aborted_aside.with_name(aborted_aside.name[: -len(".jsonl")] + ".meta.json"),
                                  session.record(meta, out))
            if tp.exists():  # an init-aborted attempt was set aside: it is no transcript of the run
                m["transcripts"][rid] = _sha256_file(tp)
            else:
                m["transcripts"].pop(rid, None)
            views[rid] = manifest_view(meta)
            save()
            n = counts["done"] + counts["rate_limited"] + counts["aborted"] + counts["skipped"]
            print(f"[{n}/{planned}] {rid} cost={cost:.4f} spent={spent:.4f}"
                  + (f" flags={','.join(flags)}" if flags else ""), flush=True)

            # The quota: the gateway says it is used up, or `stop_after` runs in a row ended in HTTP 429
            in_a_row = in_a_row + 1 if "rate_limited" in flags else 0
            scope = quota_scope(outcome.result)
            if scope or (stop_after and in_a_row >= stop_after):
                m["stop"] = {"reason": "quota_exhausted", "scope": scope, "after_runs": in_a_row,
                             "run_id": rid}
                tally_rest(idx + 1, "not_run_quota")
                save()
                cap = f", {scope} cap" if scope else ""
                print(f"quota used up ({in_a_row} run(s) in a row ended in HTTP 429{cap}); stopping. "
                      "Wait for the reset, then continue with --resume", file=sys.stderr, flush=True)
                break
            # The same for any other API error (an expired token, an unserved model, a 5xx) and for runs without a
            # result (hung calls): the rest of the plan would end the same way
            if stop_after_errors and errors_in_a_row >= stop_after_errors:
                m["stop"] = {"reason": "api_errors", "scope": None, "after_runs": errors_in_a_row, "run_id": rid}
                tally_rest(idx + 1, "not_run_api_errors")
                save()
                print(f"{errors_in_a_row} run(s) in a row ended in an API error or without a result ({rid}); "
                      "stopping. Check the token, the model id and the gateway, then continue with --resume",
                      file=sys.stderr, flush=True)
                break
    except KeyboardInterrupt:
        interrupted = True
        m["interrupted"] = True
        print("interrupted; manifest written", file=sys.stderr, flush=True)
    except BaseException:
        crashed = True  # the manifest says `finished: false`; the exception goes on
        raise
    finally:
        m["finished"] = not (interrupted or crashed)
        try:
            save()
            inputs_mod.write_readme(out, given=given, plan_obj=plan_obj, sealed=sealed_split,
                                    manifest=session.record(m, out))
        except Exception as e:  # noqa: BLE001 - while a crash propagates, its exception must not be replaced
            if not crashed:
                raise
            print(f"could not write the final manifest or README: {e}", file=sys.stderr, flush=True)

    print(f"done={counts['done']} rate_limited={counts['rate_limited']} skipped={counts['skipped']} "
          f"aborted={counts['aborted']} "
          f"not_run_sandbox={counts['not_run_sandbox']} "
          f"not_run_probe_not_evaluable={counts['not_run_probe_not_evaluable']} "
          f"not_run_budget={counts['not_run_budget']} not_run_quota={counts['not_run_quota']} "
          + (f"not_run_api_errors={counts['not_run_api_errors']} " if "not_run_api_errors" in counts else "")
          + f"planned={planned} cost=USD {spent:.4f} manifest={manifest_path}", flush=True)
    if interrupted:
        return 130
    if aborted:  # the cells this invocation aborted (the manifest also lists those of earlier invocations)
        return 1  # a failure wins: waiting for the quota reset cannot fix an init mismatch
    if (m["stop"] or m["stopped_by_budget"] or (counts["rate_limited"] and not counts["done"])
            or (failed_runs and not answered_runs)):
        # the quota, the budget or repeated API errors cut the matrix, or nothing was answered: not a success, not a
        # failure of the code. `--resume` (with a larger budget, a new token) runs the rest
        return EX_TEMPFAIL
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
