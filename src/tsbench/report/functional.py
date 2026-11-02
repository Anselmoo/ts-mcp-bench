"""The overview page of a functional test: the verdict, the steps on a time line, which step read what another wrote,
the runs and their verdicts, and links to the summary and the provenance page.

    tsbench report functional --steps OUT/steps.jsonl [--trace OUT/trace] [--mode TEXT] --out OUT/OVERVIEW.html

Inputs: `steps.jsonl` (the steps of tools/functional_test.sh), the trace records of `tsbench.core.trace` (default:
`trace/` next to steps.jsonl; one folder per step), and when they exist `runs/scores.csv` and
`sandbox-probe/sandbox_probe.json`. The page reads what `tsbench report summary` and `tsbench report provenance` read
and shows it as one overview: fact tiles, a time line per step (from the first process start to the last process end),
the files each step read from an earlier step or from outside, and the runs as a task x condition grid. It links
`SUMMARY.html` and `provenance.html` when they lie next to it. A step without a trace folder has no bar. Exit code 0
when every step passed and the hash chain is intact, else 1.

The page is templates/functional.html.j2 on the shared page frame: every datum is escaped, the figures are drawn by the
page's own script with the vendored Figura bundle, and a <noscript> table stands in for each figure.
"""
from __future__ import annotations

import argparse
import pathlib
from typing import Any

from tsbench.core import trace_prov
from tsbench.report import page, provenance, summary
from tsbench.report.base import HARNESS, is_true
from tsbench.report.summary import load_steps

__all__ = ["PAGE_NAME", "build_html", "context", "load_steps", "main"]

PAGE_NAME = "OVERVIEW.html"
DETAIL_PAGES = ("SUMMARY.html", "provenance.html", "provenance.prov.json")
CONDS = ("A", "B", "C")
_NOT_EVALUABLE = {"rate_limited": "na429", "api_error": "na429"}


def _timeline(steps: list[dict], records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One bar per traced step, in step order; times in seconds from the first process start."""
    t0 = min((float(r.get("start") or 0) for r in records), default=0.0)
    rows = []
    for s in steps:
        mine = [r for r in records if r.get("step") == s["name"]]
        if not mine:
            continue
        rc = s["rc"]
        rows.append({"name": s["name"], "start": round(min(float(r.get("start") or 0) for r in mine) - t0, 3),
                     "end": round(max(float(r.get("end") or r.get("start") or 0) for r in mine) - t0, 3),
                     "processes": len(mine),
                     "state": "ok" if rc == 0 else "na" if rc == summary.NOT_EVALUABLE_RC else "fail"})
    return rows


def _flow(prov: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Per traced step: inputs by the earlier step that wrote them, inputs from outside, outputs; and the step edges."""
    rows, edges = [], {}
    for s in prov["steps"]:
        if not s["records"]:
            continue
        from_steps: dict[str, int] = {}
        outside = written = 0
        for rec in s["records"]:
            written += len(rec["outputs"])
            for item in rec["inputs"]:
                if item["from"] and item["from"]["step"] != s["name"]:
                    src = item["from"]["step"]
                    from_steps[src] = from_steps.get(src, 0) + 1
                    edges[(src, s["name"])] = edges.get((src, s["name"]), 0) + 1
                elif not item["from"]:
                    outside += 1
        rows.append({"name": s["name"], "from_steps": from_steps, "outside": outside, "written": written})
    order = [s["name"] for s in prov["steps"]]
    edge_list = [{"source": a, "target": b, "files": n}
                 for (a, b), n in sorted(edges.items(), key=lambda e: (order.index(e[0][0]), order.index(e[0][1])))]
    return rows, edge_list


def _cell(row: dict) -> str:
    """The status key (page.STATUS) of one row of scores.csv."""
    category = row.get("category") or ""
    if not is_true(row.get("evaluable")):
        return _NOT_EVALUABLE.get(category.partition(":")[0], "unscored")
    if is_true(row.get("correct")):
        return "correct"
    return "harness" if category in HARNESS else "wrong"


def _grid_cell(keys: list[str]) -> dict[str, str]:
    """One cell: the status of its first run, the words of every run (a cell holds several runs when k > 1)."""
    return {"key": keys[0], "text": ", ".join(page.STATUS[k][0] for k in keys)}


def _grid(scores: list[dict]) -> dict[str, Any]:
    """Runs as task x condition; several runs of one cell are listed in the order of scores.csv."""
    conds = [c for c in CONDS if any(r["condition"] == c for r in scores)]
    conds += sorted({r["condition"] for r in scores} - set(conds))
    tasks: dict[str, dict[str, list[str]]] = {}
    for r in scores:
        tasks.setdefault(r["task_id"], {}).setdefault(r["condition"], []).append(_cell(r))
    rows = [{"task": t, "cells": [_grid_cell(by.get(c) or ["notrun"]) for c in conds]} for t, by in tasks.items()]
    return {"conds": conds, "rows": rows}


def context(steps: list[dict], root: pathlib.Path, out: pathlib.Path, mode: str = "", when: str | None = None,
            trace_root: pathlib.Path | None = None) -> dict[str, Any]:
    """Everything functional.html.j2 shows, as plain data."""
    trace_root = trace_root or root / "trace"
    base = summary.context(steps, root, out, mode, when)
    prov = provenance.context(steps, trace_root, out)
    records = trace_prov.load_records(trace_root)
    timeline = _timeline(steps, records)
    flow, edges = _flow(prov)
    scores = base["scores"]
    read = {p for r in records for p in trace_prov.inputs(r)}
    written = {p for r in records for p in trace_prov.outputs(r)}
    facts = {
        "steps": len(steps), "steps_ok": sum(s["rc"] == 0 for s in steps),
        "chain_intact": prov["verdict"]["intact"], "breaks": len(prov["verdict"]["breaks"]),
        "processes": len(records), "functions": sum(r["n_functions"] for s in prov["steps"] for r in s["records"]),
        "files_read": len(read), "files_written": len(written),
        "wall_seconds": max((r["end"] for r in timeline), default=0.0),
        "runs": len(scores), "runs_evaluable": sum(is_true(r["evaluable"]) for r in scores),
        "runs_correct": sum(is_true(r["evaluable"]) and is_true(r["correct"]) for r in scores),
        "probe": base["probe"],
    }
    verdict = dict(base["verdict"])
    if not facts["chain_intact"]:
        verdict = {"cls": "fail", "text": f"{verdict['text']} The hash chain is broken at {facts['breaks']} file "
                                          f"version{'s' if facts['breaks'] != 1 else ''}."}
    details = [{"text": p, "href": p, "exists": (out.parent / p).is_file()} for p in DETAIL_PAGES]
    return {"title": "Functional test overview", "mode": base["mode"], "when": base["when"], "verdict": verdict,
            "facts": facts, "timeline": timeline, "flow": flow, "edges": edges, "grid": _grid(scores),
            "steps": base["steps"], "details": details, "pages": base["pages"], "breaks": prov["verdict"]["breaks"]}


def build_html(steps: list[dict], root: pathlib.Path, out: pathlib.Path, mode: str = "", when: str | None = None,
               trace_root: pathlib.Path | None = None) -> str:
    return page.render("functional.html.j2", **context(steps, root, out, mode, when, trace_root))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="tsbench report functional", description=__doc__.splitlines()[0])
    ap.add_argument("--steps", required=True, type=pathlib.Path, help="steps.jsonl written by tools/functional_test.sh")
    ap.add_argument("--trace", type=pathlib.Path, help="folder with one trace folder per step (default: trace/ next to "
                                                      "steps.jsonl)")
    ap.add_argument("--mode", default="", help="one line: how the model was reached")
    ap.add_argument("--out", required=True, type=pathlib.Path, help="the HTML page")
    a = ap.parse_args(argv)
    steps = load_steps(a.steps)
    root = a.steps.parent
    ctx = context(steps, root, a.out, a.mode, trace_root=a.trace)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(page.render("functional.html.j2", **ctx), encoding="utf-8")
    f = ctx["facts"]
    print(f"wrote {a.out} ({f['steps_ok']}/{f['steps']} steps passed, hash chain "
          f"{'intact' if f['chain_intact'] else 'broken'})")
    return 0 if steps and f["steps_ok"] == f["steps"] and f["chain_intact"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
