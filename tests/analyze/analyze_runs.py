"""Synthetic run folders for the tests of `tsbench.analyze`: stream-json transcripts, sidecars and a scores.csv, built
in the test. Pilot task ids, so that the default split judges the answers."""
from __future__ import annotations

import csv
import json
import pathlib

T0 = "2026-11-03T07:00:00.000Z"


def ts(seconds: float) -> str:
    """A timestamp `seconds` after 07:00:00 on the run day, in the form of the transcripts."""
    whole, frac = divmod(round(seconds * 1000), 1000)
    h, rest = divmod(7 * 3600 + whole, 3600)
    m, s = divmod(rest, 60)
    return f"2026-11-03T{h:02d}:{m:02d}:{s:02d}.{frac:03d}Z"


def use(i: object, name: object, inp: object, at: float | None = None, thinking_ms: int | None = None) -> dict:
    ev: dict = {"type": "assistant", "message": {"role": "assistant", "content": [
        {"type": "tool_use", "id": i, "name": name, "input": inp}]}}
    if at is not None:
        ev["timestamp"] = ts(at)
    if thinking_ms is not None:
        ev["thinking_duration_ms"] = thinking_ms
    return ev


def res(i: str, content, err: bool | None = False, at: float | None = None) -> dict:
    block = {"type": "tool_result", "tool_use_id": i, "content": content}
    if err is not None:
        block["is_error"] = err
    ev = {"type": "user", "message": {"role": "user", "content": [block]}}
    if at is not None:
        ev["timestamp"] = ts(at)
    return ev


def bash(i: str, command: str, out: str, err: bool = False, at: float | None = None,
         done: float | None = None) -> list[dict]:
    """A Bash call and its result."""
    return [use(i, "Bash", {"command": command}, at), res(i, out, err, done)]


def mcp(i: str, tool: str, inp: dict, out: str, at: float | None = None, done: float | None = None) -> list[dict]:
    return [use(i, f"mcp__tanabesugano__{tool}", inp, at), res(i, out, False, done)]


def result(answer: dict | None, thinking: int | None = 900, output: int = 1500, turns: int = 4,
           duration_ms: int = 60_000, api_ms: int = 50_000) -> list[dict]:
    """The StructuredOutput call and the result event of a finished run."""
    usage = {"input_tokens": 10, "cache_creation_input_tokens": 100, "cache_read_input_tokens": 1000,
             "output_tokens": output}
    if thinking is not None:
        usage["output_tokens_details"] = {"thinking_tokens": thinking}
    out = []
    if answer is not None:
        out += [use("so", "StructuredOutput", answer), res("so", "Structured output provided successfully")]
    out.append({"type": "result", "subtype": "success", "is_error": False, "result": "done", "num_turns": turns,
                "duration_ms": duration_ms, "duration_api_ms": api_ms, "total_cost_usd": 0.01, "usage": usage,
                "structured_output": answer})
    return out


def write_run(root: pathlib.Path, run_id: str, events: list[dict], meta: dict | None = None) -> pathlib.Path:
    """`root/<run_id>.jsonl` and, with `meta`, its sidecar `<run_id>.meta.json`."""
    path = root / f"{run_id}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    head = [{"type": "system", "subtype": "init", "tools": ["Bash", "StructuredOutput"]}]
    path.write_text("\n".join(json.dumps(e) for e in head + events) + "\n", encoding="utf-8")
    if meta is not None:
        side = {"run_id": run_id, "flags": [], "timed_out": False, "cost_unknown": False, "wall_time_s": 61.0,
                **meta}
        path.with_name(path.name[: -len(".jsonl")] + ".meta.json").write_text(json.dumps(side), encoding="utf-8")
    return path


def write_scores(root: pathlib.Path, rows: list[dict]) -> None:
    """A scores.csv with the columns the analyses read; `rows` give run_id, correct and anything else."""
    cols = ["model", "condition", "effort", "task_id", "k_index", "class", "correct", "evaluable", "n_reported",
            "n_traced", "run_id"]
    with open(root / "scores.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        for r in rows:
            model, cond, effort, name = r["run_id"].split("/")
            task, k = name.rsplit("-k", 1)
            w.writerow({"model": model, "condition": cond, "effort": effort, "task_id": task, "k_index": k,
                        "class": r.get("class", task.split("-")[1]), "evaluable": r.get("evaluable", "True"),
                        "n_reported": r.get("n_reported", ""), "n_traced": r.get("n_traced", ""), **r})


def read_csv(path: pathlib.Path) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))
