#!/usr/bin/env python3
"""Assert that the mocked end-to-end pipeline produced what it should.

    python tools/ci/check_e2e.py <e2e-dir>

<e2e-dir> is the directory written by tools/ci/e2e_dry.sh. Exit 0 when complete, 1 otherwise.

It also runs an identity scan over the records (MANIFEST, sidecars, plan, probe record): no absolute home
path (`/Users/<name>/`, `/home/<name>/`) and no hostname may appear in them; host paths are placeholders.
"""
from __future__ import annotations

import json
import pathlib
import re
import socket
import sys

EXPECTED = (
    "plan/plan.jsonl",
    "runs/MANIFEST.json",
    "runs/rates.csv",
    "runs/scores.csv",
    "runs/report.html",
    "runs/views/INDEX.html",
    "runs/hypotheses.json",
)


HOME_PATH_RE = re.compile(r"/(Users|home)/[^/]+/")
RECORD_GLOBS = ("**/MANIFEST.json", "**/*.meta.json", "**/plan.jsonl", "**/sandbox_probe.json")


def record_files(root: pathlib.Path) -> list[pathlib.Path]:
    out: set[pathlib.Path] = set()
    for g in RECORD_GLOBS:
        out.update(p for p in pathlib.Path(root).glob(g) if p.is_file())
    return sorted(out)


def hostnames() -> list[str]:
    """The full hostname and its short form (when at least 3 characters): neither may be in a record."""
    full = socket.gethostname()
    names = [full]
    short = full.split(".")[0]
    if short != full and len(short) >= 3:
        names.append(short)
    return [n for n in names if len(n) >= 3]


def identity_findings(files: list[pathlib.Path], names: list[str] | None = None) -> list[str]:
    """`<file>: <what>` for every record that carries a home path or a hostname (the match itself is not printed)."""
    names = hostnames() if names is None else names
    errs = []
    for f in files:
        text = f.read_text(encoding="utf-8", errors="replace")
        n = len(HOME_PATH_RE.findall(text))
        if n:
            errs.append(f"{f}: {n} absolute home path(s)")
        if any(h in text for h in names):
            errs.append(f"{f}: the hostname")
    return errs


def check(root: pathlib.Path) -> list[str]:
    root = pathlib.Path(root)
    errs = [f"missing file: {rel}" for rel in EXPECTED if not (root / rel).is_file()]
    mf = root / "runs/MANIFEST.json"
    if mf.is_file():
        try:
            data = json.loads(mf.read_text(encoding="utf-8"))
        except ValueError as e:
            return errs + [f"MANIFEST.json is not JSON: {e}"]
        counts = data.get("counts", {})
        if counts.get("aborted", 0) != 0 or data.get("aborted_cells"):
            errs.append(f"MANIFEST shows aborted runs: counts.aborted={counts.get('aborted')}, "
                        f"aborted_cells={len(data.get('aborted_cells') or [])}")
        if not counts.get("done"):
            errs.append("MANIFEST shows no completed runs (counts.done == 0)")
        if not data.get("child_path"):
            errs.append("MANIFEST has no child_path")
    errs += identity_findings(record_files(root))
    return errs


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    root = pathlib.Path(argv[0])
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 1
    errs = check(root)
    for e in errs:
        print(f"FAIL {e}", file=sys.stderr)
    if not errs:
        print(f"ok: {len(EXPECTED)} expected files present, 0 aborted, identity scan clean "
              f"({len(record_files(root))} records)")
    return 1 if errs else 0


if __name__ == "__main__":
    raise SystemExit(main())
