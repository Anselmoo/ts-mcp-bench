"""The environment a plan is pinned to: claude CLI, tanabesugano, Python, sandbox settings, MCP config, conditions,
answer schemas, B stack. A confirmatory run aborts on any drift between these pins and the live environment."""
from __future__ import annotations

import importlib.metadata
import pathlib
import sys

from tsbench import conditions
from tsbench.core import resource
from tsbench.core.util import claude_version, git_output, sha256_file

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]


def answer_schema_sha256() -> str:
    """sha256 of the compact answer schema exactly as it is passed to `--json-schema`."""
    return conditions.ANSWER_SCHEMA_SHA256


def answer_schema_sha256s() -> dict:
    """name -> sha256 of every answer schema (the header pins all of them)."""
    return {n: s.sha256 for n, s in sorted(conditions.ANSWER_SCHEMAS.items())}


def live_pins(claude_cli_version: str | None, repo: pathlib.Path = REPO_ROOT, *,
              b_stack_sha256: str | None = None, sandbox_settings_sha256: str | None = None,
              b_venv: pathlib.Path | str | None = None) -> dict:
    """The environment as it is now, in the shape of the header's `pins`. `b_stack_sha256` is the digest of the fixed
    scientific stack of condition B (`tsbench.conditions.b_stack`); None when B is not requested or the stack is not
    built. `b_venv` is the `--b-venv` directory: the sandbox settings a session renders name it, so their pin is
    computed for it (None = the venv of `TSBENCH_B_VENV` or the default). Raises `b_stack.BStackError` when it lies
    inside the repo."""
    from tsbench.conditions import b_stack, sandbox
    if sandbox_settings_sha256 is None:
        kw = {"b_venv": b_stack.b_venv_dir(None, str(b_venv), repo)} if b_venv else {}
        sandbox_settings_sha256 = sandbox.settings_sha256(repo, **kw)
    return {
        "claude_cli_version": claude_cli_version,
        "b_stack_sha256": b_stack_sha256,
        "tanabesugano": importlib.metadata.version("tanabesugano"),
        "python": f"{sys.version_info.major}.{sys.version_info.minor}",
        "sandbox_settings_sha256": sandbox_settings_sha256,
        # the probe script with every candidate home path (machine-independent)
        "sandbox_probe_script_sha256": sandbox.probe_script_template_sha256(),
        "ts_json_sha256": sha256_file(resource("conditions/ts.json")),
        "answer_schema_sha256": answer_schema_sha256(),
        "answer_schemas": answer_schema_sha256s(),
    }


# Pins a plan may carry that are not compared. `conditions_py_sha256` is the sha256 of the bytes of
# conditions/__init__.py, where a comment edit would count as drift and an argv change would not. Instead the runner
# rebuilds the argv, the turn limit, the blocked tools and the flags of every record and refuses a plan that differs.
RETIRED_PINS = frozenset({"conditions_py_sha256"})


def check_pins(planned: dict, live: dict) -> list[dict]:
    """Differences between the planned and the live pins. A claude version that is None on either side is not compared
    (a dry run has no real claude); the pins in RETIRED_PINS are not compared."""
    drift = []
    for name, want in planned.items():
        if name in RETIRED_PINS:
            continue
        have = live.get(name)
        if name == "answer_schemas" and isinstance(want, dict) and isinstance(have, dict):
            # a schema the plan does not pin is not drift; a pinned one that changed is
            have = {k: v for k, v in have.items() if k in want}
        if name == "claude_cli_version" and (want is None or have is None):
            continue
        if name == "b_stack_sha256" and (want is None or have is None):
            continue  # not pinned (no B, or the stack was not built when the plan was) / dry run without the stack
        if want != have:
            drift.append({"pin": name, "planned": want, "live": have})
    return drift


def claude_version_probe() -> str | None:
    """`claude --version`, best effort; None when claude is not installed. No model call."""
    import shutil
    exe = shutil.which("claude")
    if not exe:
        return None
    return claude_version(exe)


def _git_commit() -> str | None:
    return git_output(REPO_ROOT, "rev-parse", "HEAD")


# ------------------------------------------------------------------ building
