"""The environment of every claude child process: a minimal PATH, an isolated HOME, keys by name, placeholders.

Nothing secret is ever written: records name variables, never values.
"""
from __future__ import annotations

import hashlib
import os
import pathlib
import re
import shutil
import socket
import subprocess
import sys

from tsbench.conditions import b_stack
from tsbench.core.trace import ENV_VAR as TRACE_ENV_VAR

FAKE_PASSTHROUGH = ("FAKE_COST_USD", "FAKE_BAD_INIT", "FAKE_NO_RESULT", "FAKE_PROBE_LEAK",
                    "FAKE_PROBE_BASH_FAIL", "FAKE_PROBE_NO_STACK", "FAKE_PROBE_ESCAPE",
                    "FAKE_429_FIRST", "FAKE_429_STATE", "FAKE_429_TEXT", "FAKE_STOP", TRACE_ENV_VAR)


class Abort(SystemExit):
    """Startup failure: message on stderr, exit code 2."""

    def __init__(self, msg: str):
        print(f"runner: {msg}", file=sys.stderr)
        super().__init__(2)


SYSTEM_PATH = ("/usr/bin", "/bin")
RUN_USER = "tsbench"  # USER / LOGNAME of every child: the operator's login name is never passed on
FORBIDDEN_ON_PATH = ("tanabesugano",)


def claude_runtime_dirs(claude: str | None, parent_path: str = "", which=None) -> list[str]:
    """The directories `claude` needs on the child PATH: the directory of the *resolved* binary (never the
    symlink's directory, e.g. /usr/local/bin, which is full of other tools) and, for a script install
    (`#!/usr/bin/env node`, npm), the resolved directory of its interpreter. A native binary needs nothing else."""
    if not claude:
        return []
    real = pathlib.Path(os.path.realpath(claude))
    dirs = [str(real.parent)]
    try:
        with open(real, "rb") as fh:
            head = fh.read(256)
    except OSError:
        head = b""
    if head.startswith(b"#!"):
        words = head[2:].split(b"\n", 1)[0].decode("utf-8", "replace").split()
        if words and pathlib.Path(words[0]).name == "env":
            words = [w for w in words[1:] if not w.startswith("-")]
            interp = (which or shutil.which)(words[0], path=parent_path) if words else None
        else:
            interp = words[0] if words else None
        if interp:
            dirs.append(str(pathlib.Path(os.path.realpath(interp)).parent))
    return [d for d in dict.fromkeys(dirs) if d not in SYSTEM_PATH]


def child_path(runtime_dirs: list[str] | tuple[str, ...] = (), b_bin: str | None = None) -> str:
    """The child PATH, built from scratch (the parent's PATH is never inherited): `/usr/bin:/bin` plus claude's runtime
    dirs; condition B gets `<venv-B>/bin` first."""
    parts = ([b_bin] if b_bin else []) + list(SYSTEM_PATH) + list(runtime_dirs)
    return os.pathsep.join(dict.fromkeys(parts))


def path_offenders(path: str, skip: tuple[str, ...] = ()) -> list[str]:
    """Executables named tanabesugano* in any PATH directory (except `skip`)."""
    bad = []
    for d in path.split(os.pathsep):
        if not d or d in skip:
            continue
        try:
            names = os.listdir(d)
        except OSError:
            continue
        bad += [str(pathlib.Path(d) / n) for n in sorted(names) if n.lower().startswith(FORBIDDEN_ON_PATH)]
    return bad


def api_key_of(parent_env) -> str | None:
    return parent_env.get("TSMCP_ANTHROPIC_API_KEY") or parent_env.get("ANTHROPIC_API_KEY") or None


def missing_env(parent_env, gateway: bool) -> list[str]:
    if gateway:
        return [v for v in ("ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN") if not parent_env.get(v)]
    return [] if api_key_of(parent_env) else ["TSMCP_ANTHROPIC_API_KEY (or ANTHROPIC_API_KEY)"]


def mpl_cache_dir(parent_env, repo: pathlib.Path) -> str:
    """Persistent matplotlib cache for the MCP server, outside the repo and outside the per-run HOME.

    With an empty HOME every C run would rebuild matplotlib's font cache (over 20 s), close to claude's 30 s MCP
    connect timeout: init then reports the server as 'pending' and C loses its tools. Override with
    TSBENCH_MPLCONFIGDIR. The sandbox re-opens it for B (allowRead).
    """
    d = b_stack.mpl_dir(parent_env)
    if d.resolve().is_relative_to(repo.resolve()):
        raise Abort(f"matplotlib cache {d} lies inside the repo; set TSBENCH_MPLCONFIGDIR elsewhere")
    return str(d)


def warm_mpl_cache(mpl_dir: str, python: pathlib.Path) -> None:
    """Build the font cache once, locally and at no API cost, before any C run can wait on it."""
    pathlib.Path(mpl_dir).mkdir(parents=True, exist_ok=True)
    py = str(python) if python.exists() else sys.executable
    subprocess.run([py, "-c", "import matplotlib; matplotlib.use('Agg'); "
                    "from matplotlib import font_manager; font_manager.fontManager"],
                   env={"PATH": "/usr/bin:/bin", "HOME": mpl_dir, "MPLCONFIGDIR": mpl_dir},
                   capture_output=True, timeout=600, check=False)


def build_child_env(parent_env, *, home: str, config_dir: str, tmpdir: str, repo: pathlib.Path,
                    dry_run: bool, gateway: bool, mpl_config_dir: str | None = None,
                    runtime_dirs: list[str] | tuple[str, ...] = ()) -> dict[str, str]:
    """The allow-listed environment of the child process. PATH is `child_path(runtime_dirs)`, never the parent's."""
    env: dict[str, str] = {
        "PATH": child_path(runtime_dirs),
        "HOME": home,
        "CLAUDE_CONFIG_DIR": config_dir,
        "TMPDIR": tmpdir,
        "USER": RUN_USER,
        "LOGNAME": RUN_USER,
        "DISABLE_AUTOUPDATER": "1",
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
        # MCP startup of claude is non-blocking by default: init (and the first prompt) can be built before the
        # server connects, so C would race between "connected" and "pending". Blocking startup makes the tool list
        # deterministic for the first prompt.
        "MCP_CONNECTION_NONBLOCKING": "0",
        "MCP_CONNECT_TIMEOUT_MS": "30000",
    }
    if mpl_config_dir:
        env["MPLCONFIGDIR"] = mpl_config_dir
    for name in ("LANG", "LC_ALL", "SHELL"):
        if parent_env.get(name):
            env[name] = parent_env[name]
    if gateway:
        for name in ("ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN"):
            if parent_env.get(name):
                env[name] = parent_env[name]
    else:
        key = api_key_of(parent_env)
        if key:
            env["ANTHROPIC_API_KEY"] = key
    if dry_run:
        env["PYTHONPATH"] = str(repo)  # the fake imports tsbench.tasks from an empty cwd
        for name in FAKE_PASSTHROUGH:
            if name in parent_env:
                env[name] = parent_env[name]
    return env


# ------------------------------------------------------------------ what records may contain
def host_label(parent_env, salt: str) -> tuple[str, str]:
    """(value, source) for the manifest's `host`: the declared TSBENCH_HOST_LABEL, else sha256(hostname + salt)[:12]
    with salt TSBENCH_HOST_SALT (else `salt`, the plan_id). The hostname itself is never written."""
    label = (parent_env.get("TSBENCH_HOST_LABEL") or "").strip()
    if label:
        return label, "label"
    salt = parent_env.get("TSBENCH_HOST_SALT") or salt
    return hashlib.sha256((socket.gethostname() + salt).encode("utf-8")).hexdigest()[:12], "sha256(hostname+salt)[:12]"


def _prefix_re(path: str) -> re.Pattern:
    """`path`, not followed by a letter, digit, `_` or `-` (unless the path itself ends in a slash)."""
    return re.compile(re.escape(path) + ("" if path.endswith("/") else r"(?![\w-])"))


def redact(obj, pairs: list[tuple[str, str]]):
    """Replace every absolute prefix in `pairs` ((path, placeholder), longest first) in every string of `obj`. A prefix
    only matches a whole path name: `/home/jo` is not found in `/home/joanna`."""
    if isinstance(obj, str):
        for path, ph in pairs:
            if path and path in obj:
                obj = _prefix_re(path).sub(lambda _m, ph=ph: ph, obj)
        return obj
    if isinstance(obj, list):
        return [redact(x, pairs) for x in obj]
    if isinstance(obj, tuple):
        return [redact(x, pairs) for x in obj]
    if isinstance(obj, dict):
        return {k: redact(v, pairs) for k, v in obj.items()}
    return obj


def placeholder_pairs(entries: list[tuple[str | os.PathLike | None, str]]) -> list[tuple[str, str]]:
    """(path, placeholder) for each entry and its resolved spelling (/var vs /private/var), longest path first."""
    pairs: dict[str, str] = {}
    for path, ph in entries:
        if not path:
            continue
        for spelling in (str(path), os.path.realpath(str(path))):
            if len(spelling) > 1 and spelling not in pairs:
                pairs[spelling] = ph
    return sorted(pairs.items(), key=lambda kv: -len(kv[0]))
