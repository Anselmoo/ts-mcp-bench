"""Loading the run sets for the figures. Read-only: nothing is written into a run directory.

A run set is one folder made by the runner (`MANIFEST.json`, `<model>/<cond>/<effort>/<task>-k<i>.jsonl`), found under
the `--runs` roots with `tsbench.score.run_sets.discover_run_sets`; its name is its path relative to the root (a
readable folder name such as `set-1/claude-haiku-5-5-A`). Its rows come from `scores.csv` when
the folder has one (the scorer's output); otherwise (or with `rescore=True`) the transcripts are scored in memory with
the scorer's own functions, exactly like `tsbench.score.score.score_dir` but without writing `scores.csv` /
`rates.csv` (live runs may still be writing). Only task ids of the pilot split of the current task set are kept.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import pathlib
import re
from dataclasses import dataclass, field

from tsbench.core.prereg import is_doi

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
CONDITIONS = ("A", "B", "C")
COND_NAME = {"A": "no tools", "B": "Bash", "C": "TS-MCP"}
MODEL_ORDER = ("haiku", "sonnet", "opus")


class NoDataError(RuntimeError):
    """A figure has nothing to draw from the given run sets."""


@dataclass
class RunSet:
    path: pathlib.Path
    name: str                        # path relative to the --runs root: the run set's identity in every output
    title: str = ""
    source: str = "rescored"         # "scores.csv" | "rescored"
    rows: list = field(default_factory=list)
    scores_sha256: str | None = None
    live: bool = False
    dropped_non_pilot: int = 0
    skipped_incomplete: int = 0
    notes: list = field(default_factory=list)


# ------------------------------------------------------------------------------------------------ names
def model_label(model: str) -> str:
    m = re.match(r"^claude-([a-z]+)-(\d+)-(\d+)$", model or "")
    if m:
        return f"{m[1].capitalize()} {m[2]}.{m[3]}"
    return re.sub(r"^gwdg-", "", model or "?")


def model_norm(model: str) -> str:
    """Model id as used for grouping: the `gwdg-` prefix some directory names carry is dropped."""
    return re.sub(r"^gwdg-", "", model or "")


def model_key(model: str):
    short = model_label(model).split(" ")[0].lower()
    return (0, MODEL_ORDER.index(short), "") if short in MODEL_ORDER and model.startswith("claude-") else (1, 0, model)


def class_label(cls: str) -> str:
    return cls.replace("_", " ")


# ------------------------------------------------------------------------------------------------ discovery
def _has_runs(d: pathlib.Path) -> bool:
    from tsbench.score.score import find_transcripts
    return (d / "scores.csv").is_file() or bool(find_transcripts(d))


def _is_confirmatory(d: pathlib.Path) -> bool:
    if "confirmatory" in d.as_posix().lower():
        return True
    try:
        return json.loads((d / "MANIFEST.json").read_text(encoding="utf-8")).get("split") == "confirmatory"
    except (OSError, ValueError):
        return False


def find_run_sets(roots, preregistered: str | None = None) -> list[tuple[pathlib.Path, str, str]]:
    """(folder, name, title) of the run sets under the `--runs` roots, in root order, then by name.

    A root is searched with `discover_run_sets` (folders with MANIFEST.json); a root without any but with runs of its
    own (scores.csv or transcripts) counts as one set. A confirmatory run set is refused unless `preregistered` holds a
    DOI (even then only pilot task ids are drawn). Two sets with the same name get the name of the folder above them in
    front (`parent/name`), as `score.run_sets.run_sets_in` does."""
    from tsbench.score.run_sets import discover_run_sets

    out, seen, names = [], set(), set()
    for root in roots:
        root = pathlib.Path(root)
        if not root.is_dir():
            raise ValueError(f"not a directory: {root}")
        found = [(rs.path, rs.name, rs.title) for rs in discover_run_sets(root)]
        if not found and _has_runs(root):
            found = [(root, root.name, root.name)]
        if not found:
            raise ValueError(f"no run sets (MANIFEST.json, scores.csv or transcripts) under {root}")
        for path, name, title in found:
            if _is_confirmatory(path) and not is_doi(preregistered):
                raise ValueError(f"refusing a confirmatory run set without --i-have-preregistered <DOI>: {name}")
            if path.resolve() in seen:
                continue
            seen.add(path.resolve())
            if name in names:
                renamed = f"{(root.parent if path == root else root).name}/{name}"
                name, title = renamed, title if title != name else renamed
            names.add(name)
            out.append((path, name, title))
    return out


def pilot_tasks() -> dict:
    """Pilot tasks of the current task set by id. The only task reader used here; the confirmatory split is never
    requested."""
    from tsbench.tasks import load
    return {t["id"]: t for t in load("pilot")}


# ------------------------------------------------------------------------------------------------ rows
def _as_float(v):
    if v is None or v == "":
        return None
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(x) else x


def _as_bool(v):
    return str(v).strip().lower() in ("true", "1")


def _norm_row(r: dict, set_name: str) -> dict:
    ev = r.get("evaluable")
    evaluable = True if ev in (None, "") else _as_bool(ev)
    wall = _as_float(r.get("wall_time_s"))
    return {
        "set": set_name, "model": model_norm(r.get("model", "")), "condition": r.get("condition", ""),
        "effort": r.get("effort", ""), "task_id": r.get("task_id", ""),
        "k_index": int(_as_float(r.get("k_index")) or 0),
        "class": r.get("class", ""), "correct": _as_bool(r.get("correct")), "evaluable": evaluable,
        "has_result": _as_bool(r.get("has_result", "True")),
        "dq": _as_float(r.get("dq")), "b": _as_float(r.get("b")), "c": _as_float(r.get("c")),
        "cost_usd": _as_float(r.get("cost_usd")), "output_tokens": _as_float(r.get("output_tokens")),
        "wall_s": wall if wall is not None else _as_float(r.get("duration_s")),
        "wall_is_measured": wall is not None,
        "n_mcp_calls": _as_float(r.get("n_mcp_calls")), "n_bash_calls": _as_float(r.get("n_bash_calls")),
    }


def _read_scores_csv(path: pathlib.Path, set_name: str) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as fh:
        return [_norm_row(r, set_name) for r in csv.DictReader(fh)]


def _score_in_memory(d: pathlib.Path, tasks: dict, rs: RunSet) -> list[dict]:
    """The rows `score_dir` would write, computed without writing anything: `score_row` builds each one. A transcript
    with no result event and no sidecar is a live run that is still being written; it is skipped and counted."""
    from tsbench.score.extract import read_transcript
    from tsbench.score.score import check_runs_match, find_transcripts, score_row, sidecar_path

    check_runs_match(d, tasks, "v2", "pilot")
    rows = []
    for path, _model, _cond, _effort, task_id, _k in find_transcripts(d):
        task = tasks.get(task_id)
        if task is None:
            rs.dropped_non_pilot += 1
            continue
        try:
            tr = read_transcript(path)
        except Exception as exc:  # a half-written line of a live run
            rs.notes.append(f"{path.name}: unreadable ({type(exc).__name__})")
            continue
        if tr.result is None and not sidecar_path(path).is_file():
            rs.skipped_incomplete += 1  # still being written
            continue
        row, _answer = score_row(task, tr, path)
        rows.append(row)
    return [_norm_row({k: ("" if v is None else v) for k, v in r.items()}, rs.name) for r in rows]


def _is_unfinished(path: pathlib.Path) -> bool:
    """A run set whose MANIFEST.json says it has not finished (it may still be written to)."""
    try:
        return json.loads((path / "MANIFEST.json").read_text(encoding="utf-8")).get("finished") is False
    except (OSError, ValueError):
        return False


def _csv_is_current(path: pathlib.Path, tasks: dict, rs: RunSet) -> bool:
    """False when scores.csv is older than the transcripts (`score.scores_drift`: runs added, removed or overwritten
    since `tsbench score`) and there are transcripts to score instead. Either way the difference is noted."""
    from tsbench.score.score import find_transcripts, scores_drift

    drift = scores_drift(path, set(tasks))
    if not drift:
        return True
    kinds = ", ".join(f"{len(ids)} {kind}" for kind, ids in drift.items())
    can_rescore = bool(find_transcripts(path))
    rs.notes.append(f"scores.csv is older than the transcripts ({kinds})"
                    + (": scored in memory" if can_rescore else ""))
    return not can_rescore


def load_runset(path, name: str | None = None, rescore: bool = False, title: str = "") -> RunSet:
    path = pathlib.Path(path)
    tasks = pilot_tasks()
    rs = RunSet(path=path, name=name or path.name, title=title or name or path.name, live=_is_unfinished(path))
    csv_path = path / "scores.csv"
    use_csv = csv_path.is_file() and not rescore
    if use_csv:
        use_csv = _csv_is_current(path, tasks, rs)
    if use_csv:
        rs.source = "scores.csv"
        rs.scores_sha256 = hashlib.sha256(csv_path.read_bytes()).hexdigest()
        rows = _read_scores_csv(csv_path, rs.name)
    else:
        if csv_path.is_file():
            rs.scores_sha256 = hashlib.sha256(csv_path.read_bytes()).hexdigest()
        try:
            rows = _score_in_memory(path, tasks, rs)
        except ValueError as exc:  # runs made with another task set
            rs.notes.append(f"excluded: {exc}")
            rows = []
    kept = []
    for r in rows:
        if r["task_id"] in tasks:
            kept.append(r)
        else:
            rs.dropped_non_pilot += 1  # not a pilot task id: never used
    rs.rows = kept
    return rs


def load_all(found, rescore: bool = False) -> list[RunSet]:
    """`found`: (folder, name, title) from find_run_sets, or bare folders."""
    out = []
    for item in found:
        path, name, title = item if isinstance(item, tuple) else (pathlib.Path(item), pathlib.Path(item).name, "")
        out.append(load_runset(path, name, rescore, title))
    return out


def pooled_rows(sets: list[RunSet]) -> tuple[list[dict], int]:
    """Evaluable rows of all sets (HTTP 429 and API errors are out), one per
    (model, condition, effort, task, k): a repeat in a later set is dropped. Returns (rows, number of repeats)."""
    seen, out, dups = set(), [], 0
    for s in sets:
        for r in s.rows:
            if not r["evaluable"]:
                continue
            key = (r["model"], r["condition"], r["effort"], r["task_id"], r["k_index"])
            if key in seen:
                dups += 1
                continue
            seen.add(key)
            out.append(r)
    out.sort(key=lambda r: (model_key(r["model"]), r["condition"], r["effort"], r["task_id"], r["k_index"]))
    return out, dups


def group_by(rows, *keys):
    out: dict = {}
    for r in rows:
        out.setdefault(tuple(r[k] for k in keys), []).append(r)
    return out


def per_task(rows):
    """[(task_id, [rows])] in task-id order: the clusters of the bootstrap."""
    g = group_by(rows, "task_id")
    return [(k[0], g[k]) for k in sorted(g)]
