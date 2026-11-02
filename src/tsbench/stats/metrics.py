"""Write the six descriptive metric tables for a runs directory to <runs>/metrics/*.csv.

    tsbench metrics --runs <dir> [--split pilot] [--i-have-preregistered DOI]

Nothing here calls an API or an LLM: it scores the transcripts again and writes the tables (see docs/methods.md,
section 5).
"""
from __future__ import annotations

import argparse
import csv
import importlib
import math
import pathlib
import sys
from collections import defaultdict

from tsbench.core.prereg import is_doi

METRIC_FILES = ("tolerance_curve", "scope_confusion", "failure_taxonomy", "tool_use", "per_class", "consistency")
MAX_SUMMARY_LINES = 40


def _cell(v):
    """CSV form: None and NaN as '', floats via repr, everything else via str."""
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return ""
    return repr(v) if isinstance(v, float) else str(v)


def _write(path: pathlib.Path, columns, rows) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(columns)
        for r in rows:
            w.writerow([_cell(r.get(c)) for c in columns])


def _modules():
    """The four metric modules, imported on use so that argument errors never depend on them."""
    names = ("tsbench.score.sensitivity", "tsbench.score.taxonomy", "tsbench.score.tool_use",
             "tsbench.stats.descriptive")
    return tuple(importlib.import_module(n) for n in names)


def _is_evaluable(row) -> bool:
    """A scores.csv row of a run that says something about the model. Runs of an HTTP 429 or an API error have
    `evaluable` False; a scores.csv without that column has only evaluable rows."""
    return str(row.get("evaluable", "True")) != "False"


def _compute(runs: pathlib.Path, split: str, version: str = "v2"):
    """Score the transcripts, then return (evaluable rows, tables, columns); tables and columns by METRIC_FILES name.

    Scoring always runs, so scores.csv and the transcripts-based tables describe the same run set, and every
    transcript is read once (one cache shared by `score_dir`, the tolerance curve and the tool use rows). Runs that
    are not evaluable stay out of every table except the failure taxonomy, as `rates.csv` leaves them out."""
    from tsbench.score.score import score_dir
    from tsbench.tasks import load

    sens, tax, tool, desc = _modules()
    cache: dict = {}
    score_dir(runs, split, version=version, transcripts=cache)
    with open(runs / "scores.csv", newline="", encoding="utf-8") as fh:
        all_rows = list(csv.DictReader(fh))
    rows = [r for r in all_rows if _is_evaluable(r)]
    tasks = {t["id"]: t for t in load(split, version)}
    tables = {
        "tolerance_curve": sens.tolerance_curve(runs, split, version=version, transcripts=cache),
        "scope_confusion": tax.scope_confusion(rows, tasks),
        "failure_taxonomy": tax.failure_table(all_rows, tasks),
        "tool_use": tool.tool_use_rows(runs, split, version, transcripts=cache),
        "per_class": desc.per_class_accuracy(rows),
        "consistency": desc.consistency(rows),
    }
    columns = {
        "tolerance_curve": sens.SENSITIVITY_COLUMNS,
        "scope_confusion": tax.SCOPE_COLUMNS,
        "failure_taxonomy": tax.FAILURE_COLUMNS,
        "tool_use": tool.TOOL_USE_COLUMNS,
        "per_class": desc.PER_CLASS_COLUMNS,
        "consistency": desc.CONSISTENCY_COLUMNS,
    }
    return rows, tables, columns


def _write_all(runs: pathlib.Path, split: str, version: str = "v2"):
    runs = pathlib.Path(runs)
    rows, tables, columns = _compute(runs, split, version)
    out = runs / "metrics"
    out.mkdir(parents=True, exist_ok=True)
    paths = {}
    for name in METRIC_FILES:
        paths[name] = out / f"{name}.csv"
        _write(paths[name], columns[name], tables[name])
    return rows, tables, paths


def write_metrics(runs, split: str = "pilot", version: str = "v2") -> dict[str, pathlib.Path]:
    """Write the six metric CSVs under <runs>/metrics (scoring the runs first); name -> path."""
    return _write_all(runs, split, version)[2]


def _pct(v) -> str:
    return "-" if v in (None, "") or (isinstance(v, float) and math.isnan(v)) else f"{float(v):.2f}"


def _is_true(v) -> bool:
    return v is True or str(v) == "True"


def summary_lines(rows, tables) -> list[str]:
    """Compact per-cell table: accuracy, limit naming, false refusal, top failures, tool match in C."""
    cells: dict = defaultdict(lambda: [0, 0])
    for r in rows:
        c = cells[(r["model"], r["condition"], r["effort"])]
        c[0] += 1
        c[1] += _is_true(r["correct"])
    scope = {(r["model"], r["condition"], r["effort"]): r for r in tables["scope_confusion"]}
    fails: dict = defaultdict(list)
    for r in tables["failure_taxonomy"]:
        if r["category"] != "correct" and r["n"]:
            fails[(r["model"], r["condition"], r["effort"])].append((-r["n"], r["category"], r["n"]))
    used: dict = defaultdict(lambda: [0, 0])
    for r in tables["tool_use"]:
        if r["condition"] == "C" and r["expected_tool_used"] is not None and r["expected_tool_used"] != "":
            u = used[(r["model"], r["effort"])]
            u[0] += 1
            u[1] += _is_true(r["expected_tool_used"])
    lines = [f"{'model':<22}{'cd':<3}{'effort':<7}{'n':>4}{'acc':>6}{'limit':>6}{'refuse':>7}  {'tool':<6}top failures"]
    for key in sorted(cells):
        n, ok = cells[key]
        sc = scope.get(key, {})
        top = ", ".join(f"{cat} {k}" for _, cat, k in sorted(fails[key])[:3]) or "-"
        u = used.get((key[0], key[2])) if key[1] == "C" else None
        tool = f"{u[1]}/{u[0]}" if u else "-"
        lines.append(f"{key[0]:<22}{key[1]:<3}{key[2]:<7}{n:>4}{ok / n:>6.2f}{_pct(sc.get('limit_naming_rate')):>6}"
                     f"{_pct(sc.get('false_refusal_rate')):>7}  {tool:<6}{top}")
    if len(lines) > MAX_SUMMARY_LINES - 1:
        extra = len(lines) - (MAX_SUMMARY_LINES - 2)
        lines = lines[:MAX_SUMMARY_LINES - 2] + [f"... {extra} more cells; see metrics/*.csv"]
    return lines


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="tsbench metrics", description=__doc__.splitlines()[0])
    ap.add_argument("--runs", required=True)
    ap.add_argument("--split", default="pilot", choices=("pilot", "confirmatory"))
    ap.add_argument("--i-have-preregistered", metavar="DOI", default=None)
    args = ap.parse_args(argv)
    if args.split == "confirmatory" and not is_doi(args.i_have_preregistered):
        print("refusing to report the confirmatory split without --i-have-preregistered <DOI>", file=sys.stderr)
        return 2
    runs = pathlib.Path(args.runs)
    if not runs.is_dir():
        print(f"not a directory: {runs}", file=sys.stderr)
        return 2
    rows, tables, paths = _write_all(runs, args.split)
    print("\n".join(summary_lines(rows, tables)))
    print(f"wrote {len(paths)} files to {runs / 'metrics'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
