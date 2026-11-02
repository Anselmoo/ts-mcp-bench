"""Tolerance sensitivity: re-score existing transcripts with the tolerances scaled (docs/methods.md section 5.1).

    from tsbench.score.sensitivity import tolerance_curve
    rows = tolerance_curve(runs_dir, "pilot")
"""
from __future__ import annotations

import copy
import pathlib
from collections import defaultdict

from tsbench.score.score import extract_answer, find_transcripts, judge_answer, not_evaluable_reason, read_cached

__all__ = ["DEFAULT_SCALES", "SENSITIVITY_COLUMNS", "scale_tolerance", "tolerance_curve"]

UNSCALED = frozenset({"item_accuracy_min"})  # a required share of correct values, not a tolerance
DEFAULT_SCALES: tuple[float, ...] = (0.25, 0.5, 1, 2, 4, 10)
SENSITIVITY_COLUMNS = ["model", "condition", "effort", "scale", "n", "n_correct", "accuracy"]


def scale_tolerance(task: dict, scale: float) -> dict:
    """Deep copy of `task` with every non-null tolerance multiplied by `scale`; null tolerances stay null.

    `item_accuracy_min` (the share of correct diagram values that makes the task correct) is not a tolerance and
    stays as it is."""
    out = copy.deepcopy(task)
    tol = out.get("tolerance")
    if isinstance(tol, dict):
        out["tolerance"] = {p: (v if v is None or p in UNSCALED else v * scale) for p, v in tol.items()}
    return out


def tolerance_curve(runs, split: str = "pilot", scales=DEFAULT_SCALES, version: str = "v2",
                    transcripts: dict | None = None) -> list[dict]:
    """One row per (model, condition, effort, scale): every transcript of a task in `split` re-scored at `scale`.

    A transcript without a result event has no answer and is incorrect at every scale. Transcripts of tasks
    outside the split are skipped, as `score_dir` does, and so are runs that are not evaluable (HTTP 429, API
    error), which `rates.csv` leaves out too. The answer is extracted once per transcript; only the judging
    repeats per scale. `transcripts` is an optional cache (path -> Transcript), see `score.read_cached`.
    """
    from tsbench.tasks import load  # the only sanctioned task reader

    runs = pathlib.Path(runs)
    tasks = {t["id"]: t for t in load(split, version)}
    scales = [float(s) for s in scales]
    scaled = {tid: {s: scale_tolerance(t, s) for s in scales} for tid, t in tasks.items()}
    counts: dict = defaultdict(lambda: [0, [0] * len(scales)])
    for path, model, cond, effort, task_id, _k in find_transcripts(runs):
        if task_id not in tasks:
            continue
        tr = read_cached(path, transcripts)
        if not_evaluable_reason(tr) is not None:
            continue
        extracted = extract_answer(tasks[task_id], tr)
        cell = counts[(model, cond, effort)]
        cell[0] += 1
        for i, s in enumerate(scales):
            cell[1][i] += bool(judge_answer(scaled[task_id][s], extracted)[0]["correct"])
    rows = []
    for (model, cond, effort), (n, n_ok) in sorted(counts.items()):
        for s, ok in zip(scales, n_ok, strict=False):
            rows.append({"model": model, "condition": cond, "effort": effort, "scale": s, "n": n,
                         "n_correct": ok, "accuracy": ok / n})
    return rows
