#!/usr/bin/env python3
"""Release gate: fail if private material or forbidden text is tracked by git or would enter a release archive.

Private material: a pilot/, seed/, analysis/ or .claude/ folder at any depth, and a .env file (not .env.example).
Forbidden text, in the path and the content of every other tracked text file: German words and umlauts, home folders
of real users (/home/<name>/, /Users/<name>/) and /opt/homebrew/, the names listed in $TSBENCH_GATE_DENY, review and
decision ids, and words of the development process (worktree, handoff, subagent, the folder of a planning tool, ...).
$TSBENCH_GATE_DENY holds plain names, separated by commas or whitespace, and is set outside the repository (a local
shell, a masked CI variable). A name matches as a whole token, in any case. Exempt: this file and its tests (they
spell the patterns out), the vendored d3.min.js and binary files.
Run before every tag that Zenodo archives:  tsbench release gate
Exit 0 = clean. Exit 1 = private material or forbidden text found (listed). Exit 2 = not a git repository.
"""
from __future__ import annotations

import argparse
import io
import os
import pathlib
import re
import subprocess
import sys
import tarfile

PRIVATE_DIRS = frozenset({"pilot", "seed", "analysis", ".claude"})
EXEMPT = frozenset({"src/tsbench/release/gate.py", "tests/release/test_gate.py",
                    "src/tsbench/_vendor/figura/js/d3.min.js"})
DENY_VAR = "TSBENCH_GATE_DENY"

GERMAN = re.compile(r"[äöüßÄÖÜ]|\b(?:und|nicht|keine|oder|siehe|datei|zeilen|richtig|falsch|gegen)\b", re.I)
HOME_PATH = re.compile(r"(?<![\w.~-])/(?:home|Users)/(?P<user>[A-Za-z0-9_][\w.-]*)/|/opt/homebrew/")
# made-up user names that examples and tests use; any other name in a home path fails
EXAMPLE_USERS = frozenset({"a", "alice", "b", "bob", "c", "carol", "dave", "jo", "jo_old", "joanna", "me", "op",
                           "runner", "someone", "u", "user", "x", "you", "zed"})
INTERNAL_ID = re.compile(r"\bSEC-\d+|\bT\d+-\d+\b|(?<![\w-])D\d{1,3}(?=\))|\b(?i:decisions?|deviations?)\s+D\d{1,3}\b"
                         r"|\bD\d{1,3}\s+rule\b")
# the quoted git subcommand ("worktree", "add") is code, not prose
AGENT = re.compile(r'(?<!")\bworktrees?\b(?!")|\bhand-?offs?\b|\bsub-?agents?\b|\bclaude code sessions?\b'
                   r"|\.werkplan\b", re.I)


def is_private(path: str) -> bool:
    """A file inside a private folder at any depth, or a .env file other than .env.example."""
    *dirs, name = path.split("/")
    env = name == ".env" or (name.startswith(".env.") and name != ".env.example")
    return env or any(d in PRIVATE_DIRS for d in dirs)


def _deny_pattern(env) -> re.Pattern[str] | None:
    names = [w for w in re.split(r"[,\s]+", env.get(DENY_VAR) or "") if w]
    if not names:
        return None
    return re.compile(r"(?<![A-Za-z0-9])(?:" + "|".join(map(re.escape, names)) + r")(?![A-Za-z0-9])", re.I)


def find_forbidden(text: str, *, deny: re.Pattern[str] | None = None) -> list[tuple[str, str]]:
    """(class, matched text) of every forbidden pattern in one line of text, in class order."""
    found = [("german", m.group(0)) for m in GERMAN.finditer(text)]
    found += [("home path", m.group(0)) for m in HOME_PATH.finditer(text) if m.group("user") not in EXAMPLE_USERS]
    if deny is not None:
        found += [("name", m.group(0)) for m in deny.finditer(text)]
    found += [("id", m.group(0)) for m in INTERNAL_ID.finditer(text)]
    found += [("agent", m.group(0)) for m in AGENT.finditer(text)]
    return found


def _text_of(path: pathlib.Path) -> str | None:
    """The file as UTF-8 text; None for a binary file (a NUL byte or not UTF-8), a symlink or a missing file."""
    try:
        if path.is_symlink():
            return None
        data = path.read_bytes()
    except OSError:
        return None
    if b"\0" in data:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _shown(kind: str, match: str) -> str:
    """The match as printed: a name from $TSBENCH_GATE_DENY is masked, so a CI log never shows it."""
    return repr("***" if kind == "name" else match)


def forbidden_text(top: pathlib.Path, tracked: list[str], env=None) -> list[str]:
    """`path: class: 'match'` for a hit in a path, `path:line: class: 'match'` for a hit in a file. A hit of a name
    from $TSBENCH_GATE_DENY prints as '***'."""
    deny = _deny_pattern(os.environ if env is None else env)
    out: list[str] = []
    for rel in tracked:
        if rel in EXEMPT or is_private(rel):
            continue
        out += [f"{rel}: {kind}: {_shown(kind, match)}" for kind, match in find_forbidden(rel, deny=deny)]
        text = _text_of(top / rel)
        if text is None:
            continue
        for number, line in enumerate(text.splitlines(), 1):
            out += [f"{rel}:{number}: {kind}: {_shown(kind, match)}"
                    for kind, match in find_forbidden(line, deny=deny)]
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="tsbench release gate", description=__doc__.splitlines()[0])
    ap.parse_args(argv)
    try:
        top = subprocess.run(["git", "rev-parse", "--show-toplevel"], check=True, capture_output=True,
                             text=True, encoding="utf-8").stdout.strip()
        # From the top of the work tree, NUL separated: a subdirectory cwd or a quoted non-ASCII name changes nothing.
        listing = subprocess.run(["git", "-C", top, "ls-files", "-z"], check=True, capture_output=True).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("not a git repository", file=sys.stderr)
        return 2
    tracked = [name.decode("utf-8", errors="surrogateescape") for name in listing.split(b"\0") if name]
    bad = [p for p in tracked if is_private(p)]
    try:
        archive = subprocess.run(["git", "-C", top, "archive", "--format=tar", "HEAD"], capture_output=True,
                                 check=True).stdout
        names = [m.name for m in tarfile.open(fileobj=io.BytesIO(archive)).getmembers() if not m.isdir()]
        bad += [f"archive: {n}" for n in names if is_private(n)]
    except subprocess.CalledProcessError:
        pass  # no commit yet
    text_hits = forbidden_text(pathlib.Path(top), tracked)
    if bad:
        print("private material would be published:", *bad, sep="\n  ")
    if text_hits:
        print("forbidden text in tracked files:", *text_hits, sep="\n  ")
    if bad or text_hits:
        return 1
    print("clean: no private material or forbidden text tracked or archived")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
