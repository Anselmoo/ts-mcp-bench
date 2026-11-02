"""Mutation-testing reports for CI.

    mutation_report.py matrix [--only a,b]                  the GitHub Actions matrix from mutation_shards.json
    mutation_report.py shard NAME RESULTS OUT [--copy DIR]  one shard's `mutmut results --all true` as JSON
    mutation_report.py merge OUT_MD SHARD_JSON...           one Markdown table over all shards

The score is killed / (killed + survived); timeouts, mutants without a covering test and unchecked mutants are
counted but not scored. With --copy the diff of every survivor is added (`mutmut show` in that copy).
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import subprocess
import sys

SHARDS = pathlib.Path(__file__).resolve().parent / "mutation_shards.json"


def module_of(mutant: str) -> str:
    """`tsbench.score.numeric.x_parse__mutmut_3` and `...xǁParser.read__mutmut_1` -> the module name."""
    head = mutant.split("__mutmut_")[0]
    return head.rsplit(".x", 1)[0] if ".x" in head else head.rsplit(".", 1)[0]


def score_pct(counts: dict) -> float | None:
    killed, survived = counts.get("killed", 0), counts.get("survived", 0)
    return round(100 * killed / (killed + survived), 2) if killed + survived else None


def shard(name: str, results: pathlib.Path, copy: pathlib.Path | None = None) -> dict:
    status = {}
    for line in results.read_text(encoding="utf-8").splitlines():
        mutant, sep, state = line.strip().rpartition(": ")
        if sep and "__mutmut_" in mutant:
            status[mutant] = state
    counts = dict(collections.Counter(status.values()))
    per_module: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for mutant, state in status.items():
        per_module[module_of(mutant)][state] += 1
    survivors = []
    for mutant in sorted(m for m, s in status.items() if s == "survived"):
        row = {"mutant": mutant, "module": module_of(mutant)}
        if copy is not None:
            row["diff"] = subprocess.run([str(copy / ".venv/bin/mutmut"), "show", mutant], cwd=copy,
                                         capture_output=True, text=True, encoding="utf-8").stdout[-3000:]
        survivors.append(row)
    return {"name": name, "total": len(status), "counts": counts, "score_pct": score_pct(counts),
            "per_module": {m: dict(c) for m, c in sorted(per_module.items())}, "survivors": survivors}


def merge(paths: list[pathlib.Path], expected: list[str]) -> str:
    docs = {d["name"]: d for d in (json.loads(p.read_text(encoding="utf-8")) for p in paths)}
    rows = ["| shard | mutants | killed | survived | no test | score |", "|---|---:|---:|---:|---:|---:|"]
    total = collections.Counter()
    for name in expected:
        d = docs.get(name)
        if d is None:
            rows.append(f"| {name} | no result (job failed or timed out) | | | | |")
            continue
        c = d["counts"]
        total.update(c)
        total["mutants"] += d["total"]
        pct = "–" if d["score_pct"] is None else f"{d['score_pct']:.1f} %"
        rows.append(f"| {name} | {d['total']} | {c.get('killed', 0)} | {c.get('survived', 0)} | "
                    f"{c.get('no tests', 0)} | {pct} |")
    pct = score_pct(total)
    rows.append(f"| **total** | {total['mutants']} | {total['killed']} | {total['survived']} | {total['no tests']} | "
                f"{'–' if pct is None else f'{pct:.1f} %'} |")
    return ("## Mutation testing\n\nScore = killed / (killed + survived). Mutants that no selected test reaches are "
            "listed under *no test*: they are untested code, not a pass.\n\n" + "\n".join(rows) + "\n")


def matrix(shards: list[dict], only: str = "") -> dict:
    wanted = [s.strip() for s in only.split(",") if s.strip()]
    known = {s["name"] for s in shards}
    unknown = [w for w in wanted if w not in known]
    if unknown:
        sys.exit(f"mutation_report: unknown shard(s) {', '.join(unknown)}; known: {', '.join(sorted(known))}")
    chosen = [s for s in shards if not wanted or s["name"] in wanted]
    return {"include": [{"name": s["name"], "source_paths": " ".join(s["source_paths"]),
                         "test_paths": " ".join(s["test_paths"])} for s in chosen]}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("matrix")
    m.add_argument("--only", default="")
    s = sub.add_parser("shard")
    s.add_argument("name")
    s.add_argument("results", type=pathlib.Path)
    s.add_argument("out", type=pathlib.Path)
    s.add_argument("--copy", type=pathlib.Path)
    g = sub.add_parser("merge")
    g.add_argument("out", type=pathlib.Path)
    g.add_argument("shards", nargs="*", type=pathlib.Path)
    args = ap.parse_args(argv)
    shards = json.loads(SHARDS.read_text(encoding="utf-8"))
    if args.cmd == "matrix":
        print(json.dumps(matrix(shards, args.only)))
    elif args.cmd == "shard":
        doc = shard(args.name, args.results, args.copy)
        args.out.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
        print(f"{args.name}: {doc['total']} mutants, {doc['counts']}, score {doc['score_pct']}")
    else:
        md = merge(args.shards, [s["name"] for s in shards])
        args.out.write_text(md, encoding="utf-8")
        print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
