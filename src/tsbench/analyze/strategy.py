"""Solution strategies: what kind of computation each run did, and how often each kind ended correct.

    tsbench analyze strategy --runs RUNS --out DIR [--split confirmatory --i-have-preregistered DOI]

writes `DIR/runs.csv` (one row per run) and `DIR/by_group.csv` (per model, condition and class, and over all classes:
runs and correct runs per strategy). The steps come from the solution path of each transcript
(`score.solution_path.solution_path`, the path of `tsbench score path`); the tags are regular expressions over the
code of the Bash calls and the names of the MCP tools. Nothing is executed.
"""
from __future__ import annotations

import re
from collections import defaultdict

from tsbench.analyze.common import accuracy, arguments, iter_runs, load_tasks, write_csv, write_readme
from tsbench.score.solution_path import METHODS, solution_path

__all__ = ["CODE_TAGS", "ORDER", "main", "primary", "strategies"]

# tag -> what in the code of a Bash call shows it
CODE_TAGS: dict[str, re.Pattern] = {
    "diagonalisation": METHODS["eigen_solver"],
    "least_squares": re.compile(r"\b(?:least_squares|curve_fit|minimize|lstsq|leastsq|differential_evolution"
                                r"|dual_annealing|basinhopping|nnls)\b"),
    "root_find": re.compile(r"\b(?:brentq|brenth|ridder|fsolve|root_scalar)\b|\b(?:bisect|newton|root)\s*\("),
    "interpolation": METHODS["interpolation"],
    "symbolic": re.compile(r"\bsympy\b"),
}
MCP_FIT = ("ts_fit_spectrum", "ts_fit_plot_app")
MCP_TABLE = ("ts_terms_table_data",)
# the order of the tags in a row; the first tag of a run is its primary strategy
ORDER = ("mcp_fit", "mcp_other", "mcp_table", "diagonalisation", "least_squares", "root_find", "interpolation",
         "symbolic", "closed_form", "none")

README = """
# Solution strategies

Inputs: the transcripts of one scored run folder, the task records of its split and its `scores.csv` (for `correct`
and `class`). The steps of a run are those of its solution path (`tsbench score path`).

Tags of a run, read from all its tool steps (also the steps that failed): `mcp_fit` (a call of `ts_fit_spectrum` or
`ts_fit_plot_app`), `mcp_table` (`ts_terms_table_data`), `mcp_other` (any other MCP tool); and over the code of the
Bash calls: `diagonalisation` (an eigenvalue solver: `eig`, `eigh`, `eigvals`, `eigvalsh`), `least_squares`
(`least_squares`, `curve_fit`, `minimize`, `lstsq` and similar), `root_find` (`brentq`, `fsolve`, `root_scalar`,
`bisect(`, `newton(`), `interpolation`, `symbolic` (`sympy`); `closed_form` when the run made Bash calls but none of
these appear; `none` when the run made no tool call. The tags say what the code calls, not whether the physics is
right. The primary strategy is the first tag in the order mcp_fit, mcp_other, mcp_table, diagonalisation,
least_squares, root_find, interpolation, symbolic, closed_form, none.

`runs.csv`: per run the steps, scripts and failing steps of the solution path, the primary strategy, all tags, the
MCP tools called, the method tags of the solution path and how many answer numbers a step produced (`n_linked`).

`by_group.csv`: per model, condition and class (`all` for every class) and per strategy, counted once by the primary
strategy (`grouping` = primary) and once by every tag (`grouping` = tag): the runs, their share of the group's runs,
the correct runs and the accuracy with its exact 95 % interval.
"""

RUN_COLUMNS = ["run_id", "model", "condition", "effort", "task_id", "class", "correct", "n_steps", "n_scripts",
               "n_failed_steps", "primary", "strategies", "mcp_tools", "methods", "n_values", "n_linked"]
GROUP_COLUMNS = ["model", "condition", "class", "grouping", "strategy", "n_runs", "share", "n_correct", "accuracy",
                 "ci_lo", "ci_hi"]


def strategies(path: dict) -> list[str]:
    """The tags of one solution path, in the order ORDER."""
    tags = set()
    for step in path["steps"]:
        tool = step["tool"]
        if tool.startswith("mcp__"):
            short = tool.split("__", 2)[-1]
            tags.add("mcp_fit" if short in MCP_FIT else "mcp_table" if short in MCP_TABLE else "mcp_other")
        elif tool == "Bash":
            tags.add("bash")
            tags |= {tag for tag, rx in CODE_TAGS.items() if rx.search(step["command"])}
    if "bash" in tags and not tags & set(CODE_TAGS):
        tags.add("closed_form")
    if not path["steps"]:
        tags.add("none")
    return [t for t in ORDER if t in tags]


def primary(tags: list[str]) -> str:
    """The first tag in the order ORDER; `none` without tags."""
    return next((t for t in ORDER if t in tags), "none")


def _groups(rows: list[dict]) -> list[dict]:
    cells: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        for cls in (r["class"], "all"):
            cells[(r["model"], r["condition"], cls)].append(r)
    out = []
    for (model, cond, cls), rs in sorted(cells.items()):
        for grouping in ("primary", "tag"):
            for strat in ORDER:
                hit = [r for r in rs if (r["primary"] == strat if grouping == "primary"
                                         else strat in r["strategies"].split())]
                if not hit:
                    continue
                acc = accuracy(sum(r["correct"] is True for r in hit), len(hit))
                out.append({"model": model, "condition": cond, "class": cls, "grouping": grouping,
                            "strategy": strat, "n_runs": len(hit), "share": len(hit) / len(rs),
                            "n_correct": acc["n_correct"], "accuracy": acc["accuracy"], "ci_lo": acc["ci_lo"],
                            "ci_hi": acc["ci_hi"]})
    return out


def main(argv: list[str] | None = None) -> int:
    runs, out, split = arguments("tsbench analyze strategy", __doc__ or "", argv)
    rows = []
    for run in iter_runs(runs, load_tasks(split)):
        path = solution_path(run.path, label=run.run_id, task=run.task, tr=run.tr)
        tags = strategies(path)
        s = path["summary"]
        rows.append({"run_id": run.run_id, "model": run.model, "condition": run.condition, "effort": run.effort,
                     "task_id": run.task_id, "class": run.cls, "correct": run.correct, "n_steps": s["n_steps"],
                     "n_scripts": s["n_scripts"], "n_failed_steps": s["n_failed_steps"], "primary": primary(tags),
                     "strategies": " ".join(tags),
                     "mcp_tools": " ".join(dict.fromkeys(st["tool"].split("__", 2)[-1] for st in path["steps"]
                                                         if st["tool"].startswith("mcp__"))),
                     "methods": " ".join(s["methods"]), "n_values": s["n_values"], "n_linked": s["n_linked"]})
    write_csv(out / "runs.csv", RUN_COLUMNS, rows)
    write_csv(out / "by_group.csv", GROUP_COLUMNS, _groups(rows))
    write_readme(out, README)
    shares = defaultdict(int)
    for r in rows:
        shares[r["primary"]] += 1
    print(f"runs: {len(rows)}, primary strategies: "
          + ", ".join(f"{k} {shares[k]}" for k in ORDER if shares[k]) + f", out: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
