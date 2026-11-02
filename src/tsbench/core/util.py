"""Small helpers that several stages share: atomic text writes, file hashes, the git and `claude --version` probes,
an integer from the environment and UTF-8 standard streams. Standard library only."""
from __future__ import annotations

import hashlib
import os
import pathlib
import secrets
import subprocess
import sys
from collections.abc import Mapping

__all__ = ["claude_version", "env_int", "git_output", "sha256_file", "use_utf8_streams", "write_text_atomic"]

PROBE_TIMEOUT_S = 30


def write_text_atomic(path: pathlib.Path, text: str) -> None:
    """Write `text` (UTF-8) through a temp file next to `path` and rename it. The temp name is unique per write
    (process id and a random part), so two invocations on one folder never take each other's temp file away."""
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.{secrets.token_hex(4)}.tmp")
    try:
        tmp.write_text(text, encoding="utf-8")
        tmp.replace(path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def sha256_file(path: pathlib.Path | str) -> str:
    """Hex sha256 of the bytes of a file. Raises OSError when it cannot be read."""
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def _run_text(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=PROBE_TIMEOUT_S, **kw)


def git_output(repo: pathlib.Path | str, *args: str) -> str | None:
    """Stripped stdout of `git -C <repo> <args>`; None when git is missing, hangs or exits non-zero."""
    try:
        r = _run_text(["git", "-C", str(repo), *args])
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def claude_version(exe: str, *, env: Mapping[str, str] | None = None, cwd: pathlib.Path | str | None = None
                   ) -> str | None:
    """`<exe> --version`, stripped: the one string the plan pin, the runner and `tsbench doctor` compare. None when it
    cannot be run or prints nothing. No model call."""
    kw: dict = {}
    if env is not None:
        kw["env"] = dict(env)
    if cwd is not None:
        kw["cwd"] = cwd
    try:
        r = _run_text([exe, "--version"], **kw)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.strip() or None


def env_int(env: Mapping[str, str], name: str, default: int) -> int:
    """A non-negative integer from `env[name]`; `default` when it is unset, blank or not an integer."""
    raw = env.get(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        return max(0, int(str(raw).strip()))
    except ValueError:
        return default


def use_utf8_streams() -> None:
    """Read stdin and write stdout as UTF-8 whatever the locale says (the runner sends the prompt as UTF-8 bytes)."""
    for stream in (sys.stdin, sys.stdout):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8")
