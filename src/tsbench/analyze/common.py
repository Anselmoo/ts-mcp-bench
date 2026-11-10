"""What the offline analyses share: the guard of their options, the runs of a folder with their verdicts, the times
of a transcript and the writing of tables.

Every analysis reads a scored run folder (`--runs`) and writes into a folder outside it (`--out`). The verdict of a
run (`correct`, `class`, `evaluable`) is the row of the folder's `scores.csv`; a run without a row there is scored in
memory with `score.score_row`. Nothing is executed and nothing is written into the run folder.
"""
from __future__ import annotations

import argparse
import csv
import io
import math
import pathlib
import statistics
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from datetime import datetime

from tsbench.report.base import SPLITS, as_bool, split_refusal, split_tasks
from tsbench.score.extract import Transcript, read_transcript
from tsbench.score.score import find_transcripts, run_id_of_path, score_row
from tsbench.stats.hypotheses import clopper_pearson

__all__ = ["Run", "Times", "accuracy", "arguments", "iter_runs", "load_tasks", "median", "read_csv", "seconds",
           "times", "write_csv", "write_readme"]


def arguments(prog: str, doc: str, argv: list[str] | None) -> tuple[pathlib.Path, pathlib.Path, str]:
    """(runs, out, split) of an analysis command. Refused: an `--out` inside `--runs` (run folders stay
    append-only), a missing run folder, and the confirmatory split without `--i-have-preregistered <DOI>` (asked for,
    or recorded by the run folder)."""
    ap = argparse.ArgumentParser(prog=prog, description=doc.strip().splitlines()[0])
    ap.add_argument("--runs", required=True, help="scored run folder (read only)")
    ap.add_argument("--out", required=True, help="output folder; must not be inside --runs")
    ap.add_argument("--split", default="pilot", choices=SPLITS, help="task split of the runs (default pilot)")
    ap.add_argument("--i-have-preregistered", metavar="DOI", default=None)
    args = ap.parse_args(argv)
    runs, out = pathlib.Path(args.runs).resolve(), pathlib.Path(args.out).resolve()
    if out == runs or runs in out.parents:
        ap.error("--out must not be inside --runs (run folders stay append-only)")
    if not runs.is_dir():
        ap.error(f"no run folder: {args.runs}")
    why = split_refusal([runs], args.split, args.i_have_preregistered)
    if why:
        ap.error(why)
    return runs, out, args.split


def load_tasks(split: str) -> dict:
    """The task records of the split by id."""
    return split_tasks(split)


def read_csv(path: pathlib.Path) -> list[dict]:
    """The rows of a CSV file; [] when it does not exist."""
    try:
        with open(path, encoding="utf-8", newline="") as fh:
            return list(csv.DictReader(fh))
    except FileNotFoundError:
        return []


@dataclass
class Run:
    """One transcript of a run folder with its verdict. `correct`, `evaluable` are None when neither scores.csv nor
    the task record can say."""

    path: pathlib.Path
    run_id: str
    model: str
    condition: str
    effort: str
    task_id: str
    k: int
    tr: Transcript
    task: dict | None
    cls: str = ""
    correct: bool | None = None
    evaluable: bool | None = None
    score: dict = field(default_factory=dict)


def iter_runs(runs: pathlib.Path, tasks: dict) -> Iterator[Run]:
    """The runs of `<model>/<cond>/<effort>/<task>-k<i>.jsonl` below `runs`, in path order, one transcript read at a
    time."""
    stored = {r.get("run_id", ""): r for r in read_csv(runs / "scores.csv")}
    for path, model, cond, effort, task_id, k in find_transcripts(runs):
        tr = read_transcript(path)
        task = tasks.get(task_id)
        run_id = run_id_of_path(path)
        row = stored.get(run_id)
        if row is None and task is not None:
            row = {key: ("" if v is None else str(v)) for key, v in score_row(task, tr, path)[0].items()}
        row = row or {}
        yield Run(path=path, run_id=run_id, model=model, condition=cond, effort=effort, task_id=task_id, k=k, tr=tr,
                  task=task, cls=row.get("class") or (task or {}).get("class", ""),
                  correct=as_bool(row.get("correct")), evaluable=as_bool(row.get("evaluable")), score=row)


def seconds(stamp) -> float | None:
    """An ISO timestamp of a transcript event as seconds since the epoch; None for anything else."""
    if not isinstance(stamp, str):
        return None
    try:
        return datetime.fromisoformat(stamp.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


@dataclass
class Times:
    """Times of one transcript in seconds since the epoch. `use` and `result` map a tool_use id to the time of the
    event that holds the call or its result. `start` and `end` are the first and the last time of any event (None
    without timestamps); `thinking_s` is the sum of the events' `thinking_duration_ms`."""

    start: float | None = None
    end: float | None = None
    use: dict[str, float] = field(default_factory=dict)
    result: dict[str, float] = field(default_factory=dict)
    thinking_s: float = 0.0


def times(tr: Transcript) -> Times:
    out = Times()
    stamps = []
    for ev in tr.events:
        t = seconds(ev.get("timestamp"))
        ms = ev.get("thinking_duration_ms")
        if isinstance(ms, (int, float)) and not isinstance(ms, bool):
            out.thinking_s += ms / 1000.0
        if t is None:
            continue
        stamps.append(t)
        msg = ev.get("message")
        content = msg.get("content") if isinstance(msg, dict) else None
        for b in content if isinstance(content, list) else []:
            if not isinstance(b, dict):
                continue
            if b.get("type") == "tool_use" and isinstance(b.get("id"), str):
                out.use.setdefault(b["id"], t)
            elif b.get("type") == "tool_result" and isinstance(b.get("tool_use_id"), str):
                out.result.setdefault(b["tool_use_id"], t)
    if stamps:
        out.start, out.end = min(stamps), max(stamps)
    return out


def median(values: Iterable) -> float | None:
    """The median of the values that are numbers; None when there are none."""
    got = [v for v in values if isinstance(v, (int, float)) and not isinstance(v, bool) and not math.isnan(v)]
    return statistics.median(got) if got else None


def accuracy(k: int, n: int) -> dict:
    """{n, n_correct, accuracy, ci_lo, ci_hi}: the share correct with its exact (Clopper-Pearson) 95 % interval."""
    if n == 0:
        return {"n": 0, "n_correct": 0, "accuracy": None, "ci_lo": None, "ci_hi": None}
    lo, hi = clopper_pearson(k, n)
    return {"n": n, "n_correct": k, "accuracy": k / n, "ci_lo": lo, "ci_hi": hi}


def _cell(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float):
        if math.isnan(v):
            return ""
        return str(int(v)) if v.is_integer() else str(round(v, 6))
    return str(v)


def write_csv(path: pathlib.Path, columns: list[str], rows: Iterable[dict]) -> None:
    """A UTF-8 CSV with the given columns; None and NaN are empty cells, floats keep six decimals."""
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(columns)
    for r in rows:
        w.writerow([_cell(r.get(c)) for c in columns])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(buf.getvalue(), encoding="utf-8")


def write_readme(out: pathlib.Path, text: str) -> None:
    out.mkdir(parents=True, exist_ok=True)
    (out / "README.md").write_text(text.strip() + "\n", encoding="utf-8")
