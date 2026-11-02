"""Built-in provenance tracer: one JSON record per traced process.

The record holds the command, the call edges of tsbench functions and the file events with sha256. It never holds an
environment value, a file content or a hostname, and every path is shown with the home folder replaced by ``~``.

Tracing is off unless ``TSBENCH_TRACE`` names a folder. ``start_if_requested()`` switches it on; the record is written
atomically into that folder when ``stop()`` runs or the process exits. Calls come from ``sys.monitoring`` (PY_START)
and file events from an audit hook. The audit hook cannot be removed again, so after ``stop()`` it stays installed but
does nothing.
"""

from __future__ import annotations

import atexit
import collections
import hashlib
import json
import os
import pathlib
import re
import shlex
import sys
import threading
import time
from types import CodeType, FrameType
from typing import Any

from tsbench.core.keys import DEFAULT_KEY_FILE, KEY_FILE_VAR

ENV_VAR = "TSBENCH_TRACE"
SCHEMA = "tsbench.trace/1"

_SELF = os.path.abspath(__file__)
_PACKAGE = os.path.dirname(os.path.dirname(_SELF))  # .../src/tsbench
_SOURCE = os.path.dirname(_PACKAGE)  # .../src
_AUDIT_EVENTS = {
    "open": "open",
    "os.rename": "rename",  # os.replace raises this event, too
    "os.remove": "remove",
    "os.mkdir": "mkdir",
    "subprocess.Popen": "popen",
}
_NOISE_PREFIXES = ("/proc/", "/dev/", "/sys/")
_NOISE_SUFFIXES = (".pyc", ".so", ".py")
_TOOL_NAME = "tsbench-trace"
# A user home that is not our own: /home/<name> or /Users/<name>, not in the middle of another path. A slash before it
# is allowed: `//home/x` and `file:///home/x` name the same folder.
_OTHER_HOME = re.compile(r"(?<![\w.~-])/(?:home|Users)/[^/\s\"']+")
# Files whose hash would fingerprint a secret: key files (the default one, see tsbench.core.keys), .env files and
# anything in a seed/ folder. Their path is recorded, their hash never is. The key file named by TSBENCH_KEY_FILE is
# matched by its path (`_is_secret`).
_SECRET = re.compile(r"(?:^|/)(?:\.env(?:\.[^/]*)?|\.netrc|" + re.escape(DEFAULT_KEY_FILE[2:])
                     + r"|seed/.*|[^/]*\.(?:pem|key))$")

_local = threading.local()
_names: dict[CodeType, str | None] = {}
_state: dict[str, Any] | None = None
_hooked = False


def redact(text: str) -> str:
    """Replace the own home (HOME, read now) and every /home/<name> or /Users/<name> with ``~``."""
    home = os.environ.get("HOME", "").rstrip("/")
    if home:
        text = re.sub(r"(?<![\w.~-])" + re.escape(home) + r"(?=/|$|[\s\"'])", "~", text)
    return _OTHER_HOME.sub("~", text)


def _qualified_name(code: CodeType) -> str | None:
    """'tsbench.mod.path:qualname' for code under src/tsbench, else None. The tracer itself is skipped."""
    try:
        return _names[code]
    except KeyError:
        pass
    filename = code.co_filename
    name = None
    if filename.startswith(_PACKAGE + os.sep) and filename != _SELF and filename.endswith(".py"):
        module = os.path.relpath(filename, _SOURCE)[: -len(".py")].replace(os.sep, ".")
        name = f"{module.removesuffix('.__init__')}:{code.co_qualname}"
    _names[code] = name
    return name


def _nearest(frame: FrameType | None) -> str | None:
    """The name of the nearest tsbench function at or above this frame."""
    while frame is not None:
        name = _qualified_name(frame.f_code)
        if name is not None:
            return name
        frame = frame.f_back
    return None


def _on_start(code: CodeType, _offset: int) -> object:
    name = _qualified_name(code)
    if name is None:
        return sys.monitoring.DISABLE
    state = _state
    if state is not None:
        # Frame 0 is this callback, frame 1 the function that starts, frame 2 its caller.
        state["calls"][(name, _nearest(sys._getframe(2)))] += 1
    return None


def _is_secret(path: str) -> bool:
    """A secret-like file (`_SECRET`) or the key file named by TSBENCH_KEY_FILE (read from the environment now)."""
    if _SECRET.search(path):
        return True
    configured = os.environ.get(KEY_FILE_VAR, "").strip()
    return bool(configured) and os.path.abspath(path) == os.path.abspath(os.path.expanduser(configured))


def _sha256(path: str) -> str | None:
    """sha256 of a regular file, None for anything else and for a secret-like file (see `_is_secret`)."""
    if _is_secret(path):
        return None
    try:
        if not os.path.isfile(path):
            return None
        digest = hashlib.sha256()
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return None


def _is_noise(path: str, trace_dir: str) -> bool:
    prefixes = (sys.prefix, sys.base_prefix, trace_dir, *_NOISE_PREFIXES)
    return path.startswith(prefixes) or "__pycache__" in path or path.endswith(_NOISE_SUFFIXES)


def _open_mode(mode: object, flags: object) -> str:
    """The text mode of open(), or r / w / a / r+ worked out from the os.open flags."""
    if isinstance(mode, str):
        return mode
    if not isinstance(flags, int):
        return "r"
    access = flags & os.O_ACCMODE
    if access == os.O_RDWR:
        return "r+"
    if access == os.O_WRONLY:
        return "a" if flags & os.O_APPEND else "w"
    return "r"


def _path_of(raw: object) -> str | None:
    if not isinstance(raw, str | bytes | os.PathLike):
        return None  # a file descriptor
    return os.path.abspath(os.fsdecode(raw))


def _on_audit(event: str, args: tuple[Any, ...]) -> None:
    state = _state
    kind = _AUDIT_EVENTS.get(event)
    if state is None or kind is None or getattr(_local, "busy", False):
        return
    _local.busy = True
    try:
        caller = _nearest(sys._getframe(1))
        if kind == "popen":
            argv = args[1] if isinstance(args[1], list | tuple) else [args[1]]
            state["files"].append(
                {
                    "event": "popen",
                    "path": redact(os.fsdecode(args[0])) if isinstance(args[0], str | bytes | os.PathLike) else None,
                    "argv": [redact(os.fsdecode(a)) for a in argv if isinstance(a, str | bytes | os.PathLike)],
                    "caller": caller,
                }
            )
            return
        path = _path_of(args[0])
        if path is None or _is_noise(path, state["dir"]):
            return
        entry: dict[str, Any] = {"event": kind, "path": path, "caller": caller, "sha256_at_read": None}
        if kind == "open":
            mode = _open_mode(args[1], args[2] if len(args) > 2 else None)
            entry["mode"] = mode
            if not any(flag in mode for flag in "wax"):
                entry["sha256_at_read"] = _sha256(path)
        elif kind == "rename":
            target = _path_of(args[1])
            if target is None:
                return
            entry["target"] = target
        state["files"].append(entry)
    except Exception:  # noqa: BLE001 - a tracer must never break the traced program
        return
    finally:
        _local.busy = False


def _free_tool_id() -> int | None:
    for tool in (3, 4, sys.monitoring.PROFILER_ID, sys.monitoring.OPTIMIZER_ID):
        if sys.monitoring.get_tool(tool) is None:
            return tool
    return None


def start(directory: str | os.PathLike[str]) -> pathlib.Path:
    """Start tracing this process and return the path of the record. A second start keeps the running tracer."""
    global _state, _hooked
    if _state is not None:
        return _state["path"]
    trace_dir = os.path.abspath(os.fspath(directory))
    path = pathlib.Path(trace_dir) / f"{time.time_ns()}-{os.getpid()}.trace.json"
    tool = _free_tool_id()
    _state = {
        "dir": trace_dir,
        "path": path,
        "tool": tool,
        "start": time.time(),
        "calls": collections.Counter(),
        "files": [],
    }
    if not _hooked:
        sys.addaudithook(_on_audit)
        _hooked = True
    if tool is not None:
        sys.monitoring.use_tool_id(tool, _TOOL_NAME)
        sys.monitoring.register_callback(tool, sys.monitoring.events.PY_START, _on_start)
        sys.monitoring.set_events(tool, sys.monitoring.events.PY_START)
    atexit.register(stop)
    return path


def start_if_requested() -> pathlib.Path | None:
    """Start tracing into the folder named by TSBENCH_TRACE. Without the variable nothing is installed."""
    directory = os.environ.get(ENV_VAR, "").strip()
    return start(directory) if directory else None


def _release(tool: int | None) -> None:
    if tool is None:
        return
    sys.monitoring.set_events(tool, 0)
    sys.monitoring.register_callback(tool, sys.monitoring.events.PY_START, None)
    sys.monitoring.free_tool_id(tool)


def _finish(files: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Add sha256_at_end to every path event and redact the paths."""
    hashes: dict[str, str | None] = {}
    for entry in files:
        if entry["event"] == "popen":
            continue
        final = entry.get("target") or entry["path"]
        if final not in hashes:
            hashes[final] = _sha256(final)
        entry["sha256_at_end"] = hashes[final]
        entry["path"] = redact(entry["path"])
        if "target" in entry:
            entry["target"] = redact(entry["target"])
    return files


def stop(exit_code: int | None = None) -> pathlib.Path | None:
    """Write the record and free the monitoring slot. None when no tracer is running."""
    global _state
    state = _state
    if state is None:
        return None
    _state = None
    _release(state["tool"])
    atexit.unregister(stop)
    _local.busy = True  # the writes below are not part of the trace
    try:
        argv = [redact(arg) for arg in sys.argv]
        if argv and argv[0].endswith("/tsbench"):
            argv[0] = "tsbench"
        calls = sorted(state["calls"].items(), key=lambda item: (item[0][0], item[0][1] or ""))
        record = {
            "schema": SCHEMA,
            "pid": os.getpid(),
            "ppid": os.getppid(),
            "argv": argv,
            "command": shlex.join(argv),
            "cwd": redact(os.getcwd()),
            "start": state["start"],
            "end": time.time(),
            "exit_code": exit_code,
            "calls": [{"function": func, "caller": caller, "count": count} for (func, caller), count in calls],
            "files": _finish(state["files"]),
        }
        path: pathlib.Path = state["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        partial = path.with_name(path.name + ".tmp")
        partial.write_text(json.dumps(record, indent=1), encoding="utf-8")
        os.replace(partial, path)
    finally:
        _local.busy = False
    return path
