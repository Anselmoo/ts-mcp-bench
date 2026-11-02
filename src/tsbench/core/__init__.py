"""Helpers every stage shares. `resource()` is the only way code reaches the package data in `src/tsbench/data/`."""
from __future__ import annotations

import importlib.resources
import pathlib

__all__ = ["resource"]

_DATA_DIR = pathlib.Path(str(importlib.resources.files("tsbench") / "data"))


def resource(resource_id: str) -> pathlib.Path:
    """The file or folder of a package resource, named by its id relative to the data folder (e.g.
    `prompts/neutral.txt`, `tasks/tasks.jsonl`). Plans and records name these ids, never a filesystem path, so a layout
    change cannot move a `plan_id`."""
    path = _DATA_DIR / resource_id
    if not path.exists():
        raise FileNotFoundError(f"no package resource {resource_id!r}")
    return path
