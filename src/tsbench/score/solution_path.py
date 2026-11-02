"""The solution path of a transcript: which code ran, in which order, what it printed, and which step printed each
number of the answer. Derived from the transcript alone (schema `data/schemas/solution_path.schema.json`).

    tsbench score path --runs RUNS --out DIR [--split pilot]

writes `DIR/<model>/<cond>/<effort>/<task>-k<i>.path.json` per transcript and `DIR/paths.csv` (one row per
transcript). Nothing is written into RUNS and nothing is executed.

The answer of a path is the answer the scorer used (`score.extract_answer` with the task of the transcript: the
`structured_output`, the JSON line of the text, or the last valid StructuredOutput call of a run stopped by a limit).
Without a task record the answer is read unchecked: `structured_output`, else the last StructuredOutput call.

A number of the answer is linked to every tool step whose output contains it (0.5 % relative, as `numeric.trace`).
An integer below WEAK_BELOW is "weak": such numbers turn up by chance (`ls -l`, line numbers, exit codes), so they are
listed but never name a source step. A linked step whose script holds the number as a literal only retypes it; it is
listed in `typed_in_steps` and never named as the source. The source step of a value is the last other linked step
that ran a script, else the last other linked step. Method tags come from regular expressions over the code; they
say what a script calls, not whether the physics is right.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import pathlib
import re

from tsbench.core.prereg import is_doi
from tsbench.score.artifacts import find_transcripts, result_of, scan_tool_calls, split_heredocs
from tsbench.score.extract import STRUCTURED_TOOL, Transcript, flatten_text, read_transcript
from tsbench.score.numeric import TRACE_RTOL, numbers_in
from tsbench.score.score import extract_answer

FORMAT = "tsbench.solution_path/1"
WEAK_BELOW = 50
STDOUT_MAX = 20_000
KEY_LINES_MAX = 12
_EXIT = re.compile(r"(?:^|\n)\s*(?:Exit code|exit code|exit status|Exit status)[: ]+(-?\d+)")
_TASK_OF = re.compile(r"^(?P<task>.+)-k\d+\.jsonl$")
_RUNS = re.compile(r"\bpython[0-9.]*\s+(?:-[A-Za-z]+\s+)*([\w./-]+\.py)\b")
_EDITS = re.compile(r"\bsed\s+-i\b|>>\s*['\"]?[\w./-]+\.py\b|\bpatch\b")
# tag -> what in the code or command shows it; the order is the order of `methods`
METHODS: dict[str, re.Pattern] = {
    "eigen_solver": re.compile(r"\beig(?:h|vals|valsh)?\s*\(|linalg\.eig"),
    "least_squares": re.compile(r"\b(?:least_squares|curve_fit|minimize|lstsq|leastsq|fsolve|root_scalar)\b"),
    "interpolation": re.compile(r"\binterp(?:1d)?\b|\bCubicSpline\b"),
    "typed_table": re.compile(r"\[\s*-?\d+\.\d+\s*,\s*-?\d+\.\d+\s*,\s*-?\d+\.\d+"),
    "plot": re.compile(r"\bsavefig\b|\bplt\.plot\b"),
    "hash": re.compile(r"\bsha256sum\b|\bhashlib\b"),
}
# lines that build a matrix: shown next to the eigen-solver call so the reader sees what was diagonalised
_MATRIX = re.compile(r"(?:array|matrix)\s*\(\s*\[\s*\[|zeros\s*\(\s*[\[(]\s*\w+\s*,"
                     r"|^\s*\w+\[\s*\w+\s*,\s*\w+\s*\]\s*[+-]?=")

_KEY_METHODS = ("eigen_solver", "least_squares", "interpolation", "typed_table")

__all__ = ["FORMAT", "METHODS", "main", "solution_path"]


def _answer_of(events: list[dict], uses: list[dict]) -> dict | None:
    """`structured_output` of the result event; else the input of the last StructuredOutput call; else None."""
    for ev in reversed(events):
        if ev.get("type") == "result" and isinstance(ev.get("structured_output"), dict):
            return ev["structured_output"]
    for use in reversed(uses):
        if use.get("name") == STRUCTURED_TOOL and isinstance(use.get("input"), dict):
            return use["input"]
    return None


def _answer_numbers(answer) -> list[tuple[str, float]]:
    """(path, value) of every finite number in the answer, in document order; booleans, null and strings are skipped."""
    out: list[tuple[str, float]] = []

    def walk(x, path: str) -> None:
        if isinstance(x, bool) or x is None:
            return
        if isinstance(x, (int, float)):
            try:
                v = float(x)
            except OverflowError:  # an integer of more than 308 digits is no number of the answer
                return
            if math.isfinite(v):  # NaN and the infinities (1e400) are no numbers of the answer either
                out.append((path, v))
        elif isinstance(x, dict):
            for k, v in x.items():
                walk(v, f"{path}.{k}" if path else str(k))
        elif isinstance(x, list):
            for i, v in enumerate(x):
                walk(v, f"{path}[{i}]")

    walk(answer, "")
    return out


def _key_lines(name: str, code: str) -> list[dict]:
    out = []
    for n, line in enumerate(code.splitlines(), 1):
        tag = next((m for m, rx in METHODS.items() if m in _KEY_METHODS and rx.search(line)), None)
        if tag is None and _MATRIX.search(line):
            tag = "matrix"
        if tag is not None:
            out.append({"script": name, "line": n, "method": tag, "text": line.strip()[:200]})
        if len(out) >= KEY_LINES_MAX:
            break
    return out


def _step(index: int, use: dict, res: dict, written: dict[str, int]) -> dict:
    inp: dict = use["input"] if isinstance(use.get("input"), dict) else {}
    command = str(inp.get("command") or "") if use.get("name") == "Bash" else json.dumps(inp, ensure_ascii=False)
    heredocs, skeleton = split_heredocs(command) if use.get("name") == "Bash" else ([], command)
    scripts = []
    for j, h in enumerate(heredocs, 1):
        name = (h["name"] or f"inline_{j}.py").replace("\\", "/").rsplit("/", 1)[-1]
        scripts.append({"name": name, "sha256": hashlib.sha256(h["body"].encode("utf-8")).hexdigest(),
                        "lines": h["lines"], "code": h["body"]})
        if h["name"]:
            written[name] = index
    runs = []
    for m in _RUNS.finditer(skeleton):
        name = m.group(1).rsplit("/", 1)[-1]
        if all(r["name"] != name for r in runs):
            runs.append({"name": name, "written_in_step": written.get(name)})
    text = flatten_text(res.get("content"))
    is_error = bool(res.get("is_error"))
    m = _EXIT.search(text)
    exit_code = int(m.group(1)) if m else (1 if is_error else (0 if res else None))
    code_and_cmd = "\n".join([skeleton, *(s["code"] for s in scripts)])
    return {
        "index": index, "tool": str(use.get("name") or ""), "description": str(inp.get("description") or ""),
        "command": command, "scripts": scripts, "runs": runs, "edits_in_place": bool(_EDITS.search(skeleton)),
        "exit": exit_code, "is_error": is_error,
        "stdout": text[:STDOUT_MAX], "stdout_truncated": len(text) > STDOUT_MAX,
        "methods": [m for m, rx in METHODS.items() if rx.search(code_and_cmd)],
        "key_lines": [k for s in scripts for k in _key_lines(s["name"], s["code"])][:KEY_LINES_MAX],
        "produces": [],
    }


def _matches(x: float, v: float) -> bool:
    return x == 0 if v == 0 else abs(abs(x) - abs(v)) <= TRACE_RTOL * abs(v)


def solution_path(transcript_path, label: str | None = None, task: dict | None = None,
                  tr: Transcript | None = None) -> dict:
    """The solution path of one transcript as a dict that validates against `solution_path.schema.json`.

    With the `task` record the answer is the one the scorer used (`extract_answer`); without it the answer is read
    unchecked (`_answer_of`). `tr` is the already parsed transcript of that path; with it the file is not read
    again."""
    transcript = pathlib.Path(transcript_path)
    if tr is None:
        tr = read_transcript(transcript)  # the one read: events, calls and results all come from it
    events = tr.events
    uses, results = scan_tool_calls(tr)
    answer = extract_answer(task, tr).answer if task is not None else _answer_of(events, uses)
    written: dict[str, int] = {}
    steps = [_step(i, use, result_of(results, use) or {}, written)
             for i, use in enumerate(u for u in uses if u.get("name") != STRUCTURED_TOOL)]
    pools = [numbers_in(s["stdout"]) for s in steps]
    literals = [numbers_in("\n".join(sc["code"] for sc in s["scripts"])) for s in steps]
    values = []
    for path, v in _answer_numbers(answer):
        weak = v == int(v) and abs(v) < WEAK_BELOW
        linked = [s["index"] for s, pool in zip(steps, pools, strict=True) if any(_matches(x, v) for x in pool)]
        typed = [i for i in linked if any(_matches(x, v) for x in literals[i])]
        source = None
        computed = [i for i in linked if i not in typed]
        if computed and not weak:
            ran = [i for i in computed if steps[i]["scripts"] or steps[i]["runs"]]
            source = (ran or computed)[-1]
            steps[source]["produces"].append(path)
        values.append({"path": path, "value": v, "weak": weak, "steps": linked, "typed_in_steps": typed,
                       "source_step": source})
    methods = list(dict.fromkeys(m for s in steps for m in s["methods"]))
    summary = {
        "n_steps": len(steps), "n_scripts": sum(len(s["scripts"]) for s in steps),
        "n_failed_steps": sum(1 for s in steps if s["is_error"] or (s["exit"] or 0) != 0),
        "n_values": len(values), "n_linked": sum(1 for v in values if v["source_step"] is not None),
        "n_weak": sum(1 for v in values if v["weak"]),
        "source_steps": sorted({v["source_step"] for v in values if v["source_step"] is not None}),
        "methods": methods, "edits_in_place": any(s["edits_in_place"] for s in steps),
    }
    return {"format": FORMAT, "transcript": label or str(transcript),
            "transcript_sha256": tr.sha256,
            "answer": answer, "steps": steps, "values": values, "summary": summary}


CSV_COLUMNS = ["transcript", "n_steps", "n_scripts", "n_failed_steps", "n_values", "n_linked", "n_weak",
               "source_steps", "methods", "edits_in_place"]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="tsbench score path", description=(__doc__ or "").splitlines()[0])
    ap.add_argument("--runs", required=True, help="run folder (read only)")
    ap.add_argument("--out", required=True, help="output folder; must not be inside --runs")
    ap.add_argument("--split", default="pilot", choices=("pilot", "confirmatory"),
                    help="task split whose records judge the answers (default pilot)")
    ap.add_argument("--i-have-preregistered", metavar="DOI", default=None)
    args = ap.parse_args(argv)
    runs, out = pathlib.Path(args.runs).resolve(), pathlib.Path(args.out).resolve()
    if out == runs or runs in out.parents:
        ap.error("--out must not be inside --runs (run folders stay append-only)")
    if args.split == "confirmatory" and not is_doi(args.i_have_preregistered):
        ap.error("refusing the confirmatory split without --i-have-preregistered <DOI>")
    from tsbench.tasks import load  # the only sanctioned task reader

    tasks = {t["id"]: t for t in load(args.split)}
    rows = []
    for t in find_transcripts(runs):
        rel = t.relative_to(runs)
        task_id = _TASK_OF.match(t.name)
        path = solution_path(t, label=str(rel), task=tasks.get(task_id["task"]) if task_id else None)
        dest = out / rel.with_name(rel.name[: -len(".jsonl")] + ".path.json")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(path, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        s = path["summary"]
        rows.append({"transcript": str(rel), **{k: s[k] for k in CSV_COLUMNS[1:]},
                     "source_steps": " ".join(map(str, s["source_steps"])), "methods": " ".join(s["methods"])})
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=CSV_COLUMNS, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    out.mkdir(parents=True, exist_ok=True)
    (out / "paths.csv").write_text(buf.getvalue(), encoding="utf-8")
    print(f"transcripts: {len(rows)}, with steps: {sum(1 for r in rows if r['n_steps'])}, out: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
