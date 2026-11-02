"""Run sets: folders with a `MANIFEST.json` written by `tsbench run`. This module only finds folders; it reads no run.
"""
from __future__ import annotations

import dataclasses
import json
import pathlib

__all__ = ["RunSet", "discover_run_sets", "run_sets_in"]


@dataclasses.dataclass(frozen=True)
class RunSet:
    """One run set: a folder written by `tsbench run` (it holds `MANIFEST.json`).

    name   its path relative to the searched root, e.g. `functional-test/qwen3.5-397b-a17b` (a readable folder name is
           the run set's identity on every page and figure)
    title  a one-line description from the optional `run_set.json` ({"title": ...}), else the name
    path   the folder
    """

    name: str
    title: str
    path: pathlib.Path


def discover_run_sets(root: pathlib.Path | str, max_depth: int = 4) -> list[RunSet]:
    """Every run set under `root` (the root itself included), sorted by name. Folders made with the fake claude stay
    in (the e2e test uses them); a caller that wants real runs only checks `MANIFEST.json` itself."""
    root = pathlib.Path(root)
    out = []
    for manifest in sorted(root.rglob("MANIFEST.json")):
        folder = manifest.parent
        rel = folder.relative_to(root)
        if len(rel.parts) > max_depth or any(p.startswith(".") for p in rel.parts):
            continue
        title = str(rel) if rel.parts else root.name
        meta = folder / "run_set.json"
        if meta.is_file():
            try:
                title = str(json.loads(meta.read_text(encoding="utf-8")).get("title") or title)
            except (OSError, ValueError):
                pass
        out.append(RunSet(name=str(rel) if rel.parts else root.name, title=title, path=folder))
    return out


def run_sets_in(dirs) -> list[RunSet]:
    """The run sets of the folders given on a command line (`--runs DIR`, repeatable), in the order given.

    Every folder is searched with `discover_run_sets`. A folder that holds no `MANIFEST.json` at all but has transcripts
    (`<model>/<cond>/<effort>/<task>-k<i>.jsonl`) is taken as one run set itself, named after the folder, so a hand-made
    or copied run folder still shows. A folder found twice is listed once; two run sets with the same name get the name
    of the folder above them in front (`parent/name`)."""
    out: list[RunSet] = []
    seen: set[pathlib.Path] = set()
    names: set[str] = set()
    for d in map(pathlib.Path, dirs):
        found = discover_run_sets(d) if d.is_dir() else []
        if not found and d.is_dir() and any(d.glob("*/*/*/*.jsonl")):
            found = [RunSet(name=d.name, title=d.name, path=d)]
        for rs in found:
            key = rs.path.resolve()
            if key in seen:
                continue
            seen.add(key)
            if rs.name in names:
                name = f"{(d.parent if rs.path == d else d).name}/{rs.name}"
                rs = RunSet(name=name, title=rs.title if rs.title != rs.name else name, path=rs.path)
            names.add(rs.name)
            out.append(rs)
    return out
