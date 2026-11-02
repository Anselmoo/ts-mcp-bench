"""The key file: one setting names the file that exports the model keys for the operator's shell.

`TSBENCH_KEY_FILE` names it (default `~/.config/tsbench/env`). tsbench never reads it. The B sandbox denies reading its
folder, the tracer never hashes it, `tsbench doctor` reports whether it exists (stat only), and the commands.sh of a
run set names it in its shell form.
"""
from __future__ import annotations

import os
import pathlib
import posixpath
from collections.abc import Mapping

KEY_FILE_VAR = "TSBENCH_KEY_FILE"
DEFAULT_KEY_FILE = "~/.config/tsbench/env"
SHELL_KEY_FILE = f"${{{KEY_FILE_VAR}:-$HOME/{DEFAULT_KEY_FILE[2:]}}}"


def key_file_setting(env: Mapping[str, str] | None = None) -> str:
    """The key file as configured, `~` kept: `$TSBENCH_KEY_FILE`, or the default when it is unset or blank."""
    env = os.environ if env is None else env
    return (env.get(KEY_FILE_VAR) or "").strip() or DEFAULT_KEY_FILE


def _home(env: Mapping[str, str]) -> pathlib.Path:
    return pathlib.Path(env.get("HOME") or pathlib.Path("~").expanduser())


def _expand(path: str, home: pathlib.Path) -> pathlib.Path:
    """`~` and `~/...` resolved in `home`; a relative path made absolute against the working directory."""
    if path == "~":
        return home
    if path.startswith("~/"):
        return home / path[2:]
    return pathlib.Path(os.path.abspath(os.path.expanduser(path)))


def key_file_path(env: Mapping[str, str] | None = None) -> pathlib.Path:
    """The configured key file as an absolute path (`~` is the HOME of `env`)."""
    env = os.environ if env is None else env
    return _expand(key_file_setting(env), _home(env))


def key_file_exists(env: Mapping[str, str] | None = None) -> bool:
    """Whether the configured key file exists. A stat, never a read."""
    return key_file_path(env).is_file()


def display_name(env: Mapping[str, str] | None = None) -> str:
    """The configured key file for a person to read, with the home folder shown as `~`."""
    env = os.environ if env is None else env
    path, home = key_file_path(env), _home(env)
    return "~/" + path.relative_to(home).as_posix() if path.is_relative_to(home) else str(path)


def key_dir_entries(env: Mapping[str, str], real_home: pathlib.Path | str) -> list[str]:
    """The key file's folder for the B sandbox's denyRead: as `~/...` and spelled out in the real home, or only the
    absolute path when the folder lies outside the real home. A key file straight in the home gives the real home
    alone (a bare `~` would be the child's own isolated home). When the folder or the key file is a symlink, the real
    folder behind it is added as well, so that the target cannot be read through its own path."""
    real_home = pathlib.Path(real_home)
    setting = key_file_setting(env)
    absolute = _expand(posixpath.dirname(setting) or ".", real_home)
    if absolute == real_home:
        entries = [str(real_home)]
    elif absolute.is_relative_to(real_home):
        entries = ["~/" + absolute.relative_to(real_home).as_posix(), str(absolute)]
    else:
        entries = [str(absolute)]
    for real in (os.path.realpath(absolute), os.path.dirname(os.path.realpath(_expand(setting, real_home)))):
        if real not in entries:
            entries.append(real)
    return entries
