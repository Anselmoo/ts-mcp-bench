"""Benchmark task set. `load(split)` is the only sanctioned reader of tasks.jsonl.

    from tsbench.tasks import load
    tasks = load("pilot")                  # task set v2

`version` names the task set the caller expects; anything but "v2" is refused.

Loading checks the file against its tasks.sha256, so a hand-edited or stale task file fails
loudly instead of being scored. Nothing here prints task contents.
"""
from __future__ import annotations

import hashlib
import json
import pathlib

from tsbench.core import resource

TASKS_PATH = resource("tasks/tasks.jsonl")
HASH_PATH = resource("tasks/tasks.sha256")
SPLITS = ("pilot", "confirmatory")
VERSIONS = ("v2",)
DEFAULT_VERSION = "v2"

__all__ = ["DEFAULT_VERSION", "HASH_PATH", "SPLITS", "TASKS_PATH", "VERSIONS", "hash_path", "load", "tasks_path"]


def _check_version(version: str) -> None:
    if version not in VERSIONS:
        raise ValueError(f"version must be one of {VERSIONS}, got {version!r}")


def tasks_path(version: str = DEFAULT_VERSION) -> pathlib.Path:
    """tasks.jsonl of a task-set version (v2)."""
    _check_version(version)
    return TASKS_PATH


def hash_path(version: str = DEFAULT_VERSION) -> pathlib.Path:
    """tasks.sha256 of a task-set version (v2)."""
    _check_version(version)
    return HASH_PATH


def _expected_file_hash(version: str) -> str:
    path, tasks = hash_path(version), tasks_path(version)
    for line in path.read_text(encoding="utf-8").splitlines():
        digest, _, name = line.partition("  ")
        if name == tasks.name:
            return digest
    raise ValueError(f"{path} has no entry for {tasks.name}")


def load(split: str, version: str = DEFAULT_VERSION) -> list[dict]:
    """Return the records of one split of task set v2, in file order."""
    if split not in SPLITS:
        raise ValueError(f"split must be one of {SPLITS}, got {split!r}")
    path = tasks_path(version)
    raw = path.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    expected = _expected_file_hash(version)
    if actual != expected:
        raise ValueError(f"{path.name} ({version}) does not match its {hash_path(version).name}; "
                         "regenerate or restore it")
    records = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    return [r for r in records if r["split"] == split]
