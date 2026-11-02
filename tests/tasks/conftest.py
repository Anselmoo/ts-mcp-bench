"""A Python started in a locale whose default text encoding is not UTF-8.

The package passes `encoding="utf-8"` on every text read and write. Only a child process in a plain ASCII locale can
show that a call without it would break, because the default encoding of a running interpreter cannot be changed.
"""
from __future__ import annotations

import functools
import os
import subprocess
import sys

import pytest

ENV = {"LC_ALL": "C", "LANG": "C", "PYTHONUTF8": "0", "PYTHONCOERCECLOCALE": "0"}


def _env() -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONIOENCODING", "LC_CTYPE", "LANGUAGE")}
    env.update(ENV)
    return env


@functools.cache
def _default_encoding() -> str:
    out = subprocess.run([sys.executable, "-c", "import locale; print(locale.getencoding())"], env=_env(),
                         capture_output=True, text=True, timeout=60, encoding="utf-8")
    return out.stdout.strip().lower()


@pytest.fixture
def ascii_python():
    """`run(code, *args)` runs `python -c code args` with an ASCII default encoding; it returns the finished process."""
    if "utf" in _default_encoding():
        pytest.skip(f"the default encoding of the child process is {_default_encoding()}, not a non-UTF-8 one")

    def run(code: str, *args: object) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, "-c", code, *map(str, args)], env=_env(), capture_output=True,
                              text=True, encoding="utf-8", timeout=300)

    return run
