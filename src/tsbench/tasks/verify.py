"""`tsbench tasks verify`: check the committed task set against its hash file; print counts and hashes, never content.

Exit code 0 if the file hash and both split hashes match `tasks.sha256`, 1 otherwise.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter

from tsbench.tasks import HASH_PATH, SPLITS, TASKS_PATH


def split_hashes() -> dict[str, str]:
    """sha256 of every split as `tasks.sha256` defines it: `json.dumps(rec, sort_keys=True, ensure_ascii=False)` of each
    record of the split, joined with newlines plus a trailing newline, in file order."""
    records = [json.loads(ln) for ln in TASKS_PATH.read_text(encoding="utf-8").splitlines()]
    out = {}
    for split in SPLITS:
        text = "\n".join(json.dumps(r, sort_keys=True, ensure_ascii=False) for r in records if r["split"] == split)
        out[split] = hashlib.sha256((text + "\n").encode("utf-8")).hexdigest()
    return out


def main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(prog="tsbench tasks verify", description=__doc__.splitlines()[0]).parse_args(argv)
    want = {name: digest
            for digest, name in (ln.split("  ") for ln in HASH_PATH.read_text(encoding="utf-8").splitlines())}
    got = {"tasks.jsonl": hashlib.sha256(TASKS_PATH.read_bytes()).hexdigest(), **split_hashes()}
    counts = Counter(json.loads(ln)["split"] for ln in TASKS_PATH.read_text(encoding="utf-8").splitlines())
    ok = True
    for name in ("tasks.jsonl", *SPLITS):
        same = got[name] == want.get(name)
        ok &= same
        n = sum(counts.values()) if name == "tasks.jsonl" else counts[name]
        print(f"{'OK  ' if same else 'FAIL'} {name:13s} {n:4d} records  sha256 {got[name]}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
