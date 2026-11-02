"""The coverage page: evaluable runs per pilot task x model x condition (one effort) against a target k.

    tsbench report coverage --runs DIR [--runs DIR2 ...] --out COVERAGE.html [--json coverage.json] [--k 3]
                            [--models m1,m2] [--effort medium]

Inputs: the run sets under each `--runs` folder (tsbench.score.run_sets) and their transcripts, read through the scorer
in memory; nothing is written into the run folders. A run set made with another task set is skipped and counted. A run
counts when it is evaluable: no HTTP 429 and no other API error (`score.not_evaluable_reason`). A
run without a result (time limit) is evaluable (it counts as wrong). A repetition k counts once per cell, however many
run sets hold it. The models are those found in the runs unless `--models` names them. Only the pilot split is loaded.

What the page shows: one sentence on how complete the matrix is; per task class and model x condition the evaluable
runs against the target (tasks x k, shaded by that share) and how many tasks reached k; every cell without an
evaluable run with the reason.
"""
from __future__ import annotations

import argparse
import collections
import datetime
import json
import pathlib
import sys

from tsbench.report import page
from tsbench.report.base import as_run_sets
from tsbench.report.svg.base import fixed
from tsbench.score.run_sets import run_sets_in

__all__ = ["CONDS", "coverage", "zero_cells", "context", "build_html", "main"]

CONDS = ("A", "B", "C")
REASON_LABEL = {"rate_limited": "HTTP 429", "api_error": "API error"}


def coverage(run_sets, k: int = 3, models=None, conds=CONDS, effort: str = "medium") -> dict:
    """{k, effort, models, conds, tasks: [{id, class}], cells: [{task, class, model, cond, ok, bad: {reason: n}}],
    skipped_run_sets: [name]}. `run_sets`: RunSet objects or plain folders; `models` None = the models found."""
    from tsbench.score import score as S
    from tsbench.tasks import load

    tasks = {t["id"]: t for t in load("pilot")}
    ok: dict = collections.defaultdict(set)           # (task, model, cond) -> the k of its evaluable runs
    bad: dict = collections.defaultdict(dict)         # (task, model, cond) -> {k: reason of its not evaluable run}
    skipped, seen_models = [], set()
    for rs in as_run_sets(run_sets):
        try:
            S.check_runs_match(rs.path, tasks, "v2", "pilot")
        except Exception:  # noqa: BLE001 - run sets of another task set
            skipped.append(rs.name)
            continue
        for path, model, cond, eff, tid, k_index in S.find_transcripts(rs.path):
            if tid not in tasks or eff != effort:
                continue
            seen_models.add(model)
            why = S.not_evaluable_reason(S.read_transcript(path))
            if why:
                bad[(tid, model, cond)].setdefault(k_index, why)
            else:
                ok[(tid, model, cond)].add(k_index)
    models = list(models) if models else sorted(seen_models)
    # a repetition counts once, however many run sets hold it, and an evaluable copy wins over a not-evaluable one
    cells = [{"task": t, "class": tasks[t]["class"], "model": m, "cond": c, "ok": len(ok[(t, m, c)]),
              "bad": dict(collections.Counter(w for k, w in sorted(bad[(t, m, c)].items()) if k not in ok[(t, m, c)]))}
             for t in tasks for m in models for c in conds]
    return {"k": k, "effort": effort, "models": models, "conds": list(conds), "skipped_run_sets": skipped,
            "tasks": [{"id": t, "class": tasks[t]["class"]} for t in tasks], "cells": cells}


def zero_cells(cov: dict) -> list[dict]:
    """Cells without an evaluable run, each with the reason: the not-evaluable classes of its runs, or `no runs`."""
    out = []
    for c in cov["cells"]:
        if c["ok"] == 0:
            out.append({**c, "why": ", ".join(f"{REASON_LABEL.get(r, r)} × {n}" for r, n in sorted(c["bad"].items()))
                        or "no runs"})
    return out


def context(cov: dict, generated: str | None = None) -> dict:
    """The data of the page from the result of `coverage`, as plain values for coverage.html.j2; `generated` is the
    time stamp shown (default: now)."""
    k, models, conds = cov["k"], cov["models"], cov["conds"]
    by_class: dict = collections.defaultdict(lambda: collections.defaultdict(list))
    for c in cov["cells"]:
        by_class[c["class"]][(c["model"], c["cond"])].append(c["ok"])
    rows = []
    for cl in dict.fromkeys(t["class"] for t in cov["tasks"]):
        cells = []
        for m in models:
            for c in conds:
                v = by_class[cl][(m, c)]
                full = sum(1 for x in v if x >= k)
                have, want = sum(min(x, k) for x in v), len(v) * k
                p = have / want if want else 0.0
                cells.append({"full": full, "n": len(v), "have": have, "want": want, "p": round(p, 3), "dark": p >= .5})
        rows.append({"class": cl, "cells": cells})
    zeros = zero_cells(cov)
    have = sum(min(c["ok"], k) for c in cov["cells"])
    want = len(cov["cells"]) * k
    runs_per_cell = sorted({min(c["ok"], k) for c in cov["cells"]})
    even = (f"every cell has {page.plural(runs_per_cell[0], 'evaluable run')}" if len(runs_per_cell) == 1
            else f"cells have {runs_per_cell[0]} to {runs_per_cell[-1]} evaluable runs")
    summary = (f"{have} of {want} evaluable runs for k = {k} ({fixed(100 * have / want)} %): {even}." if want
               else "No cells.")
    return {"summary": summary, "have": have, "want": want,
        "title": "Coverage of the pilot matrix", "k": k, "effort": cov["effort"], "models": models, "conds": conds,
        "stamp": generated or datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "n_tasks": len(cov["tasks"]),
        "n_cells": len(cov["cells"]), "need": sum(max(0, k - c["ok"]) for c in cov["cells"]), "n_zeros": len(zeros),
        "rows": rows, "zeros": zeros, "per_model": list(collections.Counter(z["model"] for z in zeros).items()),
        "skipped": list(cov.get("skipped_run_sets") or []),
    }


def build_html(cov: dict, generated: str | None = None) -> str:
    """The page from the result of `coverage`; `generated` is the time stamp shown (default: now)."""
    ctx = context(cov, generated)
    return page.render("coverage.html.j2", **ctx, ctx=ctx)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="tsbench report coverage", description=__doc__.splitlines()[0])
    ap.add_argument("--runs", action="append", required=True, metavar="DIR",
                    help="a run set, or a folder holding run sets (repeatable)")
    ap.add_argument("--out", required=True, metavar="FILE")
    ap.add_argument("--json", default=None, metavar="FILE", help="also write the cells to this file")
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--models", default=None, help="comma-separated model ids (default: the models found in the runs)")
    ap.add_argument("--effort", default="medium")
    a = ap.parse_args(argv)
    models = [m for m in (a.models or "").split(",") if m] or None
    cov = coverage(run_sets_in(a.runs), k=a.k, models=models, effort=a.effort)
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build_html(cov), encoding="utf-8")
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps(cov), encoding="utf-8")
    zeros = zero_cells(cov)
    print(f"wrote {out}: {len(cov['cells'])} cells, {len(zeros)} without an evaluable run, "
          f"{sum(max(0, a.k - c['ok']) for c in cov['cells'])} runs missing to k = {a.k}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
