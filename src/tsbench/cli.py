"""The `tsbench` command: a table from subcommand to the `main(argv)` of the module that does the work.

    tsbench <command> [<subcommand>] [options]      (also: python -m tsbench ...)

No logic lives here; every command module parses its own options (`tsbench <command> --help`).
"""
from __future__ import annotations

import importlib
import sys

# (words of the command) -> ("module:function", one-line description). Ordered as the pipeline runs.
COMMANDS: dict[tuple[str, ...], tuple[str, str]] = {
    ("tasks", "verify"): (
        "tsbench.tasks.verify:main",
        "check the task set against tasks.sha256 (counts and hashes only)",
    ),
    ("tasks", "generate"): ("tsbench.tasks.generate:main", "regenerate the task set (maintainers; --check compares)"),
    ("tasks", "check-oracle"): ("tsbench.tasks.oracles.check:main", "cross-check the literature oracle"),
    ("env", "b-stack"): ("tsbench.conditions.b_stack:main", "create or check condition B's fixed Python stack"),
    ("env", "sandbox"): (
        "tsbench.run.sandbox_probe:main", "render condition B's sandbox settings or run the sandbox probe",
    ),
    ("doctor",): ("tsbench.run.doctor:main", "check the environment before a paid run (never prints key values)"),
    ("plan",): ("tsbench.plan.__main__:main", "build or validate a run plan (plan build | plan validate)"),
    ("plan", "estimate"): ("tsbench.plan.estimate:main", "estimate the cost and wall time of a plan"),
    ("run",): ("tsbench.run.runner:main", "execute a plan: one claude call per planned run"),
    ("score",): ("tsbench.score.score:main", "score a run folder: scores.csv and rates.csv"),
    ("score", "path"): (
        "tsbench.score.solution_path:main",
        "solution path per transcript: code, output and the step behind each answer number",
    ),
    ("metrics",): ("tsbench.stats.metrics:main", "metrics of a scored run folder"),
    ("stats", "hypotheses"): ("tsbench.stats.hypotheses:main", "the preregistered tests (H1-H3) from scores or rates"),
    ("stats", "power"): ("tsbench.stats.power:main", "simulation-based power"),
    ("figures",): (
        "tsbench.figures.cli:main",
        "draw the figures (PDF, SVG, PNG, TIFF + source CSV; --check)",
    ),
    ("report",): (
        "tsbench.report.__main__:main",
        "per-run HTML views and their index (report views)",
    ),
    ("report", "views"): ("tsbench.report.views:main", "per-run HTML views and an index per run set"),
    ("report", "gallery"): ("tsbench.report.gallery:main", "gallery of runs: figures, images, code, reproduce block"),
    ("report", "comparison"): ("tsbench.report.comparison:main", "conditions A, B, C compared across run sets"),
    ("report", "full"): ("tsbench.report.full:main", "every run-set page in one report, each number once"),
    ("report", "dashboard"): ("tsbench.report.dashboard:main", "one-page dashboard of several run sets"),
    ("report", "literature"): ("tsbench.report.literature:main", "fit results against the literature values"),
    ("report", "coverage"): ("tsbench.report.coverage:main", "evaluable runs per pilot task, model and condition"),
    ("report", "quality"): ("tsbench.report.quality:main", "test coverage and mutation score of the code base"),
    ("report", "summary"): (
        "tsbench.report.summary:main",
        "one-page summary of a functional test (tools/functional_test.sh)",
    ),
    ("report", "provenance"): (
        "tsbench.report.provenance:main",
        "provenance page of a functional test: call tree, files with sha256, hash chain",
    ),
    ("report", "functional"): (
        "tsbench.report.functional:main",
        "overview of a functional test: verdict, time line, data flow between steps, runs",
    ),
    ("report", "artifacts"): ("tsbench.score.artifacts:main", "images and code produced by the runs"),
    ("explain",): ("tsbench.report.explain:main", "explain one run: task, tool calls, answer, verdict"),
    ("analyze", "snippets"): ("tsbench.analyze.snippets:main", "every Bash command and heredoc of the runs as a file"),
    ("analyze", "strategy"): ("tsbench.analyze.strategy:main", "solution strategy per run and its accuracy per group"),
    ("analyze", "errors"): ("tsbench.analyze.errors:main", "failing tool steps per run: kind, exception, recovery"),
    ("analyze", "provenance"): (
        "tsbench.analyze.provenance:main", "origin of each answer number: tool, typed, fit copied or changed, none",
    ),
    ("analyze", "effort"): ("tsbench.analyze.effort:main", "thinking, tokens, turns, time and timeouts per run"),
    ("release", "gate"): (
        "tsbench.release.gate:main", "fail if private material or forbidden text would enter a release",
    ),
}


def usage() -> str:
    width = max(len(" ".join(words)) for words in COMMANDS)
    lines = ["usage: tsbench <command> [<subcommand>] [options]", "", "commands:"]
    lines += [f"  {' '.join(words):{width}s}  {desc}" for words, (_, desc) in COMMANDS.items()]
    lines += ["", "tsbench <command> --help shows the options of one command."]
    return "\n".join(lines)


def resolve(argv: list[str]) -> tuple[str, list[str]] | None:
    """The longest command prefix of argv and the remaining arguments, or None."""
    for n in (2, 1):
        if tuple(argv[:n]) in COMMANDS:
            return COMMANDS[tuple(argv[:n])][0], argv[n:]
    return None


def main(argv: list[str] | None = None) -> int:
    from tsbench.core import trace

    trace.start_if_requested()  # off unless TSBENCH_TRACE names a folder
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help"):
        print(usage())
        return 0
    found = resolve(argv)
    if found is None:
        print(f"tsbench: unknown command {' '.join(argv[:2])!r}\n\n{usage()}", file=sys.stderr)
        return 2
    target, rest = found
    module, func = target.split(":")
    return int(getattr(importlib.import_module(module), func)(rest) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
