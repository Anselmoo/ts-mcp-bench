"""Score a runs directory: scores.csv, rates.csv and an optional blinded grading set.

    tsbench score --runs <dir> [--split pilot] [--i-have-preregistered DOI] [--blind]

Runs are scored against task set v2. A directory made with another task set (or with prompts that differ from v2) is
refused, see `check_runs_match`.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import pathlib
import re
import sys
from collections import Counter, defaultdict
from typing import NamedTuple

from tsbench.core.api_errors import is_context_overflow
from tsbench.core.prereg import is_doi
from tsbench.score.batch_score import score_batch
from tsbench.score.blind import write_packets
from tsbench.score.diagram_score import score_diagram
from tsbench.score.extract import (
    STRUCTURED_TOOL,
    curve_answer,
    final_answer,
    read_transcript,
    rescue_stop_reason,
    rescue_structured_output,
)
from tsbench.score.numeric import _blank_row, score, score_curve, trace
from tsbench.score.pairing_score import score_pairing

SCORE_COLUMNS = [
    "model", "condition", "effort", "task_id", "k_index", "class", "subtype", "correct", "unparseable",
    "answer_out_of_scope", "dq", "b", "c", "abs_err_dq", "abs_err_b", "abs_err_c", "rel_err_dq", "rel_err_b",
    "rel_err_c", "curve_max_rel_err", "curve_tol_ratio",
    # batch / pairing classes (empty for every other class)
    "item_accuracy", "n_correct_items", "median_rel_error", "node_precision", "node_recall", "edge_precision",
    "edge_recall", "edge_f1", "ground_correct", "rms_e_over_b", "label_accuracy",
    "n_tool_uses", "n_mcp_calls", "n_bash_calls", "n_reported", "n_traced", "cost_usd",
    "input_tokens", "output_tokens", "num_turns", "is_error", "result_subtype", "has_result",
    # efficiency: a model may be right without tools but spend more (or fewer) tokens and seconds
    "uncached_input_tokens", "cache_creation_tokens", "cache_read_tokens", "thinking_tokens", "total_tokens",
    "duration_s", "api_duration_s", "wall_time_s",
    # where the answer came from (structured_output | rescued_tool_call | text_json | none); a rescued answer is the
    # last valid StructuredOutput call of a run that a turn or budget limit stopped, scored like any answer
    "answer_source", "rescued", "rescue_stop_reason",
    # HTTP 429 and other API errors with no model output are not evaluable: out of rates.csv, not wrong. A context
    # overflow (HTTP 400/413 with context-window text) is evaluable and wrong
    "evaluable", "not_evaluable_reason", "context_overflow",
    # the join keys of the run: run_id and the sidecar's plan_id / prompt_sha256 (empty without a sidecar), and the
    # sha256 of the transcript that was scored, to compare with MANIFEST.transcripts (see `scores_drift`)
    "run_id", "plan_id", "prompt_sha256", "transcript_sha256",
]
# per-task means of these over the k runs with a result event; *_correct over the correct runs only
EFFICIENCY_METRICS = ("total_tokens", "output_tokens", "thinking_tokens", "duration_s", "cost_usd")
RATE_COLUMNS = (["model", "condition", "effort", "task_id", "class", "k", "n_correct", "rate"]
                + [f"mean_{m}" for m in EFFICIENCY_METRICS] + [f"mean_{m}_correct" for m in EFFICIENCY_METRICS])
_NAME = re.compile(r"^(?P<task>.+)-k(?P<k>\d+)\.jsonl$")


def find_transcripts(runs: pathlib.Path) -> list[tuple[pathlib.Path, str, str, str, str, int]]:
    """(path, model, condition, effort, task_id, k) for every <model>/<cond>/<effort>/<task>-k<i>.jsonl."""
    found = []
    for path in sorted(runs.glob("*/*/*/*.jsonl")):
        m = _NAME.match(path.name)
        if m and path.is_file():
            model, cond, effort = path.relative_to(runs).parts[:3]
            found.append((path, model, cond, effort, m["task"], int(m["k"])))
    return found


# columns that only the batch and pairing scorers fill; NaN (written as an empty cell) everywhere else
EXTRA_SCORE_COLUMNS = ("item_accuracy", "n_correct_items", "median_rel_error", "node_precision", "node_recall",
                       "edge_precision", "edge_recall", "edge_f1", "ground_correct", "rms_e_over_b", "label_accuracy")
NAN = float("nan")


def _structured_answer(schema: str, structured):
    """The `batch` / `pairing` answer from `structured_output`, or None if it does not have the shape of the schema.
    No text fallback: these answers are structured only (as for `curve`)."""
    if not isinstance(structured, dict):
        return None
    if schema == "batch":
        return structured if isinstance(structured.get("values"), list) else None
    if schema == "pairing":
        return (structured if isinstance(structured.get("nodes"), list) and isinstance(structured.get("edges"), list)
                else None)
    if schema == "diagram":
        return structured if isinstance(structured.get("points"), list) else None
    return None


def not_evaluable_reason(tr) -> str | None:
    """`rate_limited` for an HTTP 429 result, `api_error` for another API error that ended the run (a 5xx, or Claude
    Code's `terminal_reason: api_error`); None for everything else, including limits the harness set (turns, budget,
    timeout), wrong answers and a context overflow (`core.api_errors.is_context_overflow`: the model's request outgrew
    its context window, a wrong answer). A not evaluable run says nothing about the model."""
    res = tr.result
    if not isinstance(res, dict) or not res.get("is_error"):
        return None
    status = res.get("api_error_status")
    text = str(res.get("result") or "").lower()
    if status == 429 or str(status) == "429" or "rate limit" in text or "(429)" in text:
        return "rate_limited"
    if is_context_overflow(res):
        return None
    if isinstance(status, int) and status >= 400 or res.get("terminal_reason") == "api_error" \
            or str(res.get("result") or "").startswith("API Error:"):
        return "api_error"
    return None


def read_cached(path, cache: dict | None):
    """The transcript at `path`; with a `cache` (path -> Transcript) it is read once and kept there for the next
    reader. Without a cache it is read every time."""
    if cache is None:
        return read_transcript(path)
    if path not in cache:
        cache[path] = read_transcript(path)
    return cache[path]


class Extracted(NamedTuple):
    """The answer of one transcript and where it came from. It does not depend on the task's tolerance."""
    answer: dict | None
    source: str
    rescued: bool
    stop: str


def extract_answer(task: dict, tr) -> Extracted:
    """The answer of a transcript, routed by the task's `answer_schema` (default `fit`), with its `answer_source`.
    Only the schema of the task is used, so a re-scoring at other tolerances extracts once (see `judge_answer`).

    Rescue: when the run has no `structured_output` in its result event because a turn or budget limit stopped it (or
    it has no result event at all), the last `StructuredOutput` tool call whose input validates against the answer
    schema is taken as the answer (`answer_source` = `rescued_tool_call`, `rescued` = True, `stop` = the stop)."""
    res = tr.result or {}
    has_result = tr.result is not None
    schema = task.get("answer_schema", "fit")
    structured = res.get("structured_output") if has_result else None
    source, rescued, stop = "none", False, ""
    if isinstance(structured, dict):
        source = "structured_output"
    else:
        stop_reason = rescue_stop_reason(tr)
        if stop_reason is not None:
            saved = rescue_structured_output(tr, schema)
            if saved is not None:
                structured, source, rescued, stop = saved, "rescued_tool_call", True, stop_reason
    have_answer = has_result or rescued
    if schema == "curve":
        answer = curve_answer(structured) if have_answer else None
    elif schema in ("batch", "pairing", "diagram"):
        answer = _structured_answer(schema, structured) if have_answer else None
    else:
        text = tr.result_text if has_result else ""
        answer = final_answer(text, structured) if have_answer else None
        if answer is not None and not (isinstance(structured, dict) and final_answer("", structured) is not None):
            source = "text_json"
    if answer is None:
        source, rescued, stop = "none", False, ""
    return Extracted(answer, source, rescued, stop)


def judge_answer(task: dict, extracted: Extracted) -> tuple[dict, dict | None]:
    """(score row, answer) of an extracted answer against `task`: `fit` -> numeric.score; `curve` ->
    numeric.score_curve; `batch` -> batch_score.score_batch; `pairing` -> pairing_score.score_pairing; `diagram` ->
    diagram_score.score_diagram.
    The score row always carries every EXTRA_SCORE_COLUMNS key and `answer_source`, `rescued`, `rescue_stop_reason`."""
    answer, source, rescued, stop = extracted
    schema = task.get("answer_schema", "fit")
    if schema == "curve":
        sc = score_curve(task, answer)
    elif schema in ("batch", "pairing", "diagram"):
        sc = _blank_row(answer is None)
        if answer is not None:
            sc.update({"batch": score_batch, "pairing": score_pairing, "diagram": score_diagram}[schema](task, answer))
            sc.pop("items", None)
    else:
        sc = score(task, answer)
    sc.update({"answer_source": source, "rescued": rescued, "rescue_stop_reason": stop})
    for col in EXTRA_SCORE_COLUMNS:
        sc.setdefault(col, NAN)
    return sc, answer


def score_transcript(task: dict, tr) -> tuple[dict, dict | None]:
    """(score row, answer) of one transcript: `extract_answer` and then `judge_answer`. A transcript without a result
    event has no answer, except when it was stopped by a limit (rescue, see `extract_answer`). A transcript with no
    model output at all is incorrect but not a formatting failure: `unparseable` is False for it."""
    sc, answer = judge_answer(task, extract_answer(task, tr))
    if tr.result is None and not sc["rescued"]:
        sc["unparseable"] = False
    return sc, answer


def tokens_of(usage) -> tuple[int, int]:
    usage = usage if isinstance(usage, dict) else {}
    get = lambda k: usage.get(k) if isinstance(usage.get(k), (int, float)) else 0  # noqa: E731
    return (int(get("input_tokens") + get("cache_creation_input_tokens") + get("cache_read_input_tokens")),
            int(get("output_tokens")))


def usage_detail(usage) -> dict:
    """Token split from the result event's usage: cache traffic and thinking kept apart. Thinking tokens are None when
    the event does not report them (a reported 0 stays 0)."""
    usage = usage if isinstance(usage, dict) else {}
    _is_num = lambda v: isinstance(v, (int, float))  # noqa: E731
    num = lambda v: int(v) if _is_num(v) else 0  # noqa: E731
    raw_details = usage.get("output_tokens_details")
    details = raw_details if isinstance(raw_details, dict) else {}
    out = {"uncached_input_tokens": num(usage.get("input_tokens")),
           "cache_creation_tokens": num(usage.get("cache_creation_input_tokens")),
           "cache_read_tokens": num(usage.get("cache_read_input_tokens")),
           "thinking_tokens": num(details.get("thinking_tokens")) if _is_num(details.get("thinking_tokens")) else None}
    out["total_tokens"] = (out["uncached_input_tokens"] + out["cache_creation_tokens"] + out["cache_read_tokens"]
                           + num(usage.get("output_tokens")))
    return out


def seconds_of(ms):
    return ms / 1000.0 if isinstance(ms, (int, float)) else None


def sidecar_path(path: pathlib.Path) -> pathlib.Path:
    return path.with_name(path.name[: -len(".jsonl")] + ".meta.json")


def read_sidecar(path: pathlib.Path) -> dict:
    """The sidecar `<task>-k<i>.meta.json` of a transcript; {} when it is missing or not a JSON object."""
    try:
        meta = json.loads(sidecar_path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return meta if isinstance(meta, dict) else {}


def wall_time(path: pathlib.Path):
    """Wall time measured by the runner (sidecar `wall_time_s`), including claude's startup."""
    v = read_sidecar(path).get("wall_time_s")
    return v if isinstance(v, (int, float)) else None


def _mean(values):
    vals = [v for v in values if isinstance(v, (int, float)) and not (isinstance(v, float) and math.isnan(v))]
    return sum(vals) / len(vals) if vals else None


def _cell(v):
    if isinstance(v, float) and math.isnan(v):
        return ""
    return "" if v is None else v


def _prefix_hashes(tasks: dict) -> set[str]:
    """sha256 of the first n records of the split (the `tasks.sha256` form: canonical lines), for every n. A run made
    with the first n records of a split pins the hash of that prefix, and every prefix hash of the split is accepted."""
    out, h = set(), hashlib.sha256()
    for t in tasks.values():
        h.update((json.dumps(t, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8"))
        out.add(h.copy().hexdigest())
    return out


def check_runs_match(runs: pathlib.Path, tasks: dict, version: str, split: str) -> None:
    """Refuse a runs directory that was made with another task set. Task ids are not unique across task sets, so
    scoring foreign transcripts against these tasks would run silently and be wrong. Evidence, when the directory has
    it: the manifest's task hash and task-id order, and the prompts in `plan.jsonl`. A run whose prompts differ from
    the task set is refused like any foreign one (ValueError)."""
    from tsbench.tasks import hash_path

    manifest = runs / "MANIFEST.json"
    if manifest.is_file():
        try:
            m = json.loads(manifest.read_text(encoding="utf-8"))
        except ValueError:
            m = {}
        want = {name: digest for digest, name in (ln.split("  ", 1) for ln in
                                                   hash_path(version).read_text(encoding="utf-8").splitlines())}
        if m.get("tasks_sha256") and m["tasks_sha256"] != want.get(split) \
                and m["tasks_sha256"] not in _prefix_hashes(tasks):
            raise ValueError(f"{manifest} was made with another task set than {version}: tasks_sha256 differs")
        ids = list(tasks)
        listed = m.get("tasks")
        # a manifest without plan_id lists the split in file order; a plan's subset may be in any order
        if isinstance(listed, list) and listed and "plan_id" not in m and listed != ids[: len(listed)]:
            raise ValueError(f"{manifest} lists task ids in an order that is not the {version} {split} order")
    plan = runs / "plan.jsonl"
    if plan.is_file():
        try:
            lines = [json.loads(ln) for ln in plan.read_text(encoding="utf-8").splitlines() if ln.strip()]
        except ValueError:
            return
        bad = sorted({r["task_id"] for r in lines if r.get("kind") == "run" and r.get("task_id") in tasks
                      and r.get("prompt") != tasks[r["task_id"]]["prompt"]})
        if bad:
            raise ValueError(f"{plan} has prompts that differ from task set {version} for {len(bad)} task id(s)")


def _sha256_of(path: pathlib.Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def run_id_of_path(path: pathlib.Path) -> str:
    """The run id `<model>/<cond>/<effort>/<task>-k<i>` of the transcript `<...>/<run id>.jsonl` (the id the plan gives
    the run, see `tsbench.conditions.argv.run_id_of`)."""
    return "/".join((*path.parent.parts[-3:], path.name[: -len(".jsonl")]))


def score_row(task: dict, tr, path: pathlib.Path) -> tuple[dict, dict | None]:
    """(the scores.csv row, the answer) of one transcript. The one place that builds a row: `score_dir`, the figures and
    the report pages (which score in memory) all call it. `path` is `<...>/<model>/<cond>/<effort>/<task>-k<i>.jsonl`;
    the row has every key of SCORE_COLUMNS, typed (bool, NaN, None) as `score_dir` hands it on."""
    path = pathlib.Path(path)
    model, cond, effort = path.parent.parts[-3:]
    named = _NAME.match(path.name)
    if named is None:
        raise ValueError(f"not a transcript name: {path.name}")
    k = int(named["k"])
    res = tr.result or {}
    has_result = tr.result is not None
    sc, answer = score_transcript(task, tr)
    why_not = not_evaluable_reason(tr)
    n_rep, n_tr = trace(answer, tr) if task.get("answer_schema", "fit") == "fit" else (0, 0)
    names = [u["name"] for u in tr.tool_uses if u["name"] != STRUCTURED_TOOL]
    in_tok, out_tok = tokens_of(res.get("usage"))
    detail = usage_detail(res.get("usage")) if has_result else {}
    meta = read_sidecar(path)
    wall = meta.get("wall_time_s")
    return {
        "model": model, "condition": cond, "effort": effort, "task_id": task["id"], "k_index": k,
        "class": task["class"], "subtype": task.get("subtype"), **sc,
        "n_tool_uses": len(names),
        "n_mcp_calls": sum(n.startswith("mcp__") for n in names),
        "n_bash_calls": sum(n == "Bash" for n in names),
        "n_reported": n_rep, "n_traced": n_tr,
        "cost_usd": res.get("total_cost_usd"), "input_tokens": in_tok if has_result else None,
        "output_tokens": out_tok if has_result else None, "num_turns": res.get("num_turns"),
        "is_error": res.get("is_error") if has_result else None,
        "result_subtype": res.get("subtype"), "has_result": has_result,
        **detail,
        "duration_s": seconds_of(res.get("duration_ms")), "api_duration_s": seconds_of(res.get("duration_api_ms")),
        "wall_time_s": wall if isinstance(wall, (int, float)) else None,
        "evaluable": why_not is None, "not_evaluable_reason": why_not or "",
        "context_overflow": is_context_overflow(tr.result),
        "run_id": run_id_of_path(path), "plan_id": meta.get("plan_id") or "",
        "prompt_sha256": meta.get("prompt_sha256") or "", "transcript_sha256": _sha256_of(path) or "",
    }, answer


def planned_run_ids(runs: pathlib.Path) -> list[str] | None:
    """The run ids of the run records in `plan.jsonl`; None without a readable plan (or a sealed one, which has no
    run record)."""
    try:
        lines = [json.loads(ln) for ln in (runs / "plan.jsonl").read_text(encoding="utf-8").splitlines() if ln.strip()]
    except (OSError, ValueError):
        return None
    ids = [r["run_id"] for r in lines if isinstance(r, dict) and r.get("kind") == "run" and r.get("run_id")]
    return ids or None


def _task_of(run_id: str) -> str | None:
    m = _NAME.match(run_id.rsplit("/", 1)[-1] + ".jsonl")
    return m["task"] if m else None


def scores_drift(runs, task_ids=None) -> dict[str, list[str]]:
    """How `<runs>/scores.csv` is older than the transcripts it should describe, as {kind: [run id]} (empty when it
    matches): `new` = a transcript without a row, `changed` = a row whose transcript has another sha256 (overwritten or
    re-run since). A row without a transcript is no drift: a results folder keeps scores.csv without all of them. The
    transcripts are those of `MANIFEST.json` (`transcripts`, run id -> sha256) when it lists any, else the files on
    disk (none there: {}). A table without the id and hash columns is read by the model, condition,
    effort, task and k of its rows and is not checked for `changed`. `task_ids` limits the run ids to those tasks (the
    split that was scored). Without scores.csv: {}."""
    runs = pathlib.Path(runs)
    try:
        with open(runs / "scores.csv", newline="", encoding="utf-8") as fh:
            table = list(csv.DictReader(fh))
    except OSError:
        return {}
    scored: dict[str, str] = {}
    for r in table:
        rid = r.get("run_id") or "/".join(str(r.get(c) or "") for c in ("model", "condition", "effort")) \
            + f"/{r.get('task_id')}-k{r.get('k_index')}"
        scored[rid] = r.get("transcript_sha256") or ""
    try:
        listed = json.loads((runs / "MANIFEST.json").read_text(encoding="utf-8")).get("transcripts")
    except (OSError, ValueError, AttributeError):
        listed = None
    if isinstance(listed, dict) and listed:
        have = {rid: sha for rid, sha in listed.items() if isinstance(rid, str)}
    else:
        have = {run_id_of_path(path): None for path, *_rest in find_transcripts(runs)}
        if not have:
            return {}
    if task_ids is not None:
        have = {rid: sha for rid, sha in have.items() if _task_of(rid) in task_ids}
    changed = []
    for rid, sha in scored.items():
        if sha and rid in have:
            now = have[rid] if have[rid] is not None else _sha256_of(runs / f"{rid}.jsonl")
            if now is not None and now != sha:
                changed.append(rid)
    drift = {"new": sorted(set(have) - set(scored)), "changed": sorted(changed)}
    return {kind: ids for kind, ids in drift.items() if ids}


def score_dir(runs, split: str = "pilot", blind: bool = False, seed: int = 20261024, version: str = "v2",
              transcripts: dict | None = None) -> dict:
    """Score every transcript under `runs`; write scores.csv and rates.csv (and the blind set). Returns a summary:
    `rows`, `unknown` (transcripts of a task not in the split), `n_blind`, and, when `plan.jsonl` lists run records,
    `missing` (planned runs without a transcript) and `unplanned` (transcripts of no planned run); both are [] without
    a plan.

    `version` is the task-set version the runs were made with (`v2`). `transcripts` is an optional
    cache (path -> Transcript) that other readers of the same runs share, see `read_cached`."""
    from tsbench.tasks import load  # the only sanctioned task reader

    runs = pathlib.Path(runs)
    tasks = {t["id"]: t for t in load(split, version)}
    check_runs_match(runs, tasks, version, split)
    rows, unknown, blind_entries = [], [], []
    for path, model, cond, effort, task_id, k in find_transcripts(runs):
        task = tasks.get(task_id)
        if task is None:
            unknown.append(str(path.relative_to(runs)))
            continue
        tr = read_cached(path, transcripts)
        row, _answer = score_row(task, tr, path)
        rows.append(row)
        if row["has_result"] and row["evaluable"]:
            blind_entries.append({"path": str(path.relative_to(runs)), "model": model, "condition": cond,
                                  "effort": effort, "k": k, "task_id": task_id, "prompt": task["prompt"],
                                  "answer_text": tr.result_text})
    planned = planned_run_ids(runs)
    scored_ids = {r["run_id"] for r in rows}
    missing = sorted(set(planned) - {run_id_of_path(p) for p, *_rest in find_transcripts(runs)}) if planned else []
    unplanned = sorted(scored_ids - set(planned)) if planned else []

    with open(runs / "scores.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=SCORE_COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow({c: _cell(r.get(c)) for c in SCORE_COLUMNS})

    cells: dict = defaultdict(list)
    for r in rows:
        if not r["evaluable"]:  # HTTP 429 / API error: neither right nor wrong, not part of k
            continue
        cells[(r["model"], r["condition"], r["effort"], r["task_id"], r["class"])].append(r)
    with open(runs / "rates.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(RATE_COLUMNS)
        for (model, cond, effort, task_id, cls), runs_ in sorted(cells.items()):
            k, n_ok = len(runs_), sum(bool(r["correct"]) for r in runs_)
            done = [r for r in runs_ if r["has_result"]]
            ok = [r for r in done if r["correct"]]
            means = [_mean(r.get(m) for r in done) for m in EFFICIENCY_METRICS]
            means_ok = [_mean(r.get(m) for r in ok) for m in EFFICIENCY_METRICS]
            w.writerow([model, cond, effort, task_id, cls, k, n_ok, repr(n_ok / k)]
                       + [_cell(v) for v in means + means_ok])

    if blind:
        write_packets(blind_entries, runs / "blind", seed)
    return {"rows": rows, "unknown": unknown, "n_blind": len(blind_entries) if blind else 0,
            "missing": missing, "unplanned": unplanned}


def summary_lines(result: dict) -> list[str]:
    rows = result["rows"]
    acc: dict = defaultdict(lambda: [0, 0])
    for r in rows:
        if not r.get("evaluable", True):
            continue
        a = acc[(r["model"], r["condition"], r["effort"])]
        a[0] += 1
        a[1] += bool(r["correct"])
    lines = [f"{'model':<22}{'cond':<6}{'effort':<8}{'correct':>9}{'n':>5}{'acc':>7}"]
    for (m, c, e), (n, ok) in sorted(acc.items()):
        lines.append(f"{m:<22}{c:<6}{e:<8}{ok:>9}{n:>5}{ok / n:>7.2f}")
    lines.append(f"transcripts scored: {len(rows)}")
    lines.append(f"unparseable: {sum(bool(r['unparseable']) for r in rows)}")
    lines.append(f"no result event: {sum(not r['has_result'] for r in rows)}")
    lines.append("rescued answers (last StructuredOutput call after a limit): "
                 f"{sum(bool(r.get('rescued')) for r in rows)}")
    lines.append("not evaluable (excluded from the rates): "
                 + (", ".join(f"{why} {n}" for why, n in sorted(Counter(r["not_evaluable_reason"] for r in rows
                                                                         if not r.get("evaluable", True)).items()))
                    or "0"))
    lines.append(f"unknown (task not in split): {len(result['unknown'])}")
    if result.get("missing"):
        lines.append(f"planned, no transcript: {len(result['missing'])}")
    if result.get("unplanned"):
        lines.append(f"transcript in no plan: {len(result['unplanned'])}")
    return lines


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="tsbench score", description=__doc__.splitlines()[0])
    ap.add_argument("--runs", required=True)
    ap.add_argument("--split", default="pilot", choices=("pilot", "confirmatory"))
    ap.add_argument("--i-have-preregistered", metavar="DOI", default=None)
    ap.add_argument("--blind", action="store_true")
    ap.add_argument("--blind-seed", type=int, default=20261024)
    args = ap.parse_args(argv)
    if args.split == "confirmatory" and not is_doi(args.i_have_preregistered):
        print("refusing to score the confirmatory split without --i-have-preregistered <DOI>", file=sys.stderr)
        return 2
    runs = pathlib.Path(args.runs)
    if not runs.is_dir():
        print(f"not a directory: {runs}", file=sys.stderr)
        return 2
    try:
        result = score_dir(runs, args.split, args.blind, args.blind_seed)
    except ValueError as e:
        print(f"refusing: {e}", file=sys.stderr)
        return 2
    print("\n".join(summary_lines(result)))
    if result["unknown"]:
        print("unknown transcripts (first 5): " + ", ".join(result["unknown"][:5]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
