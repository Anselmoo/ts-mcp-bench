"""The code of the runs as files: every Bash command and every heredoc body, with an index.

    tsbench analyze snippets --runs RUNS --out DIR [--split confirmatory --i-have-preregistered DOI]

For every run with Bash calls this writes `DIR/<run id>/step-NN.sh` (the command exactly as the model sent it) and,
for each heredoc of that command, `step-NN-<target>.py` or `step-NN-heredoc-<i>.py` with its body (`.txt` when the
body is not Python). `DIR/index.csv` has one row per file. The calls are read with `score.artifacts.extract_code`
(write=False) and `split_heredocs`, the parser of `tsbench report artifacts`; nothing is executed.
"""
from __future__ import annotations

import hashlib
import pathlib
import re

from tsbench.analyze.common import arguments, iter_runs, load_tasks, write_csv, write_readme
from tsbench.score.artifacts import extract_code, scan_tool_calls, split_heredocs
from tsbench.score.extract import Transcript

__all__ = ["INDEX_COLUMNS", "heredoc_name", "main", "snippets_of"]

INDEX_COLUMNS = ["run_id", "step", "kind", "file", "lines", "sha256", "tool_use_id", "exit", "is_error", "target"]

README = """
# Code snippets

Inputs: the transcripts of one scored run folder. Only Bash commands are read; MCP calls are not code.

Files: `<run id>/step-NN.sh` is the NN-th Bash command of the run, byte for byte as the model sent it. Each heredoc
of that command is also written on its own: `step-NN-<target>.py` when it is redirected to a file (`cat > a.py
<<'EOF'`), `step-NN-heredoc-<i>.py` when it is fed to Python directly (`python3 - <<'EOF'`), and `.txt` instead of
`.py` when the body is not Python. A call to an unknown tool name (such as `bash`) never ran and is left out, as is
an empty command.

`index.csv` has one row per file: `run_id`, `step` (the number NN), `kind` (`bash` or `heredoc`), `file` (relative to
this folder), `lines`, `sha256` (of the file bytes), `tool_use_id` (of the Bash call), `exit` (the exit code the
result reports; 0 for a result without one; empty without a result), `is_error` (the result's flag), `target` (the
file a heredoc is redirected to).

Method: the commands are parsed by the parser of `tsbench report artifacts` (`score/artifacts.py`); nothing is
executed.
"""

_SAFE = re.compile(r"[^\w.\-]+")
MAX_NAME = 60  # characters of a target kept in a file name
MAX_SUFFIX = 8


def _cut(name: str) -> str:
    """`name` cut to `MAX_NAME` characters; a suffix of up to `MAX_SUFFIX` characters stays."""
    if len(name) <= MAX_NAME:
        return name
    stem, dot, suffix = name.rpartition(".")
    if dot and len(suffix) <= MAX_SUFFIX:
        return stem[:MAX_NAME - len(suffix) - 1] + dot + suffix
    return name[:MAX_NAME]


def heredoc_name(step: int, j: int, target: str | None, python: bool) -> str:
    """The file name of the j-th heredoc of Bash call `step`: the base name of its target, else `heredoc-<j>`;
    `.py` for Python (a `.py` target or a body fed to Python), `.txt` added otherwise."""
    base = _cut(_SAFE.sub("_", (target or "").replace("\\", "/").rsplit("/", 1)[-1]).strip("._"))
    label = base or f"heredoc-{j}"
    if label.endswith(".py") or (python and not base):
        return f"step-{step:02d}-{label if label.endswith('.py') else label + '.py'}"
    return f"step-{step:02d}-{label if label.endswith('.txt') else label + '.txt'}"


def _commands(tr: Transcript) -> list[tuple[str, str]]:
    """(tool_use id, command) of every Bash call with a command, in the order of `extract_code`."""
    uses, _ = scan_tool_calls(tr)
    out: list[tuple[str, str]] = []
    for u in uses:
        inp = u.get("input")
        cmd = str(inp.get("command") or "") if isinstance(inp, dict) else ""
        uid = u.get("id")
        if u.get("name") == "Bash" and cmd:
            out.append((uid if isinstance(uid, str) else "", cmd))
    return out


def snippets_of(path, tr: Transcript) -> list[dict]:
    """The files of one transcript: {step, kind, name, data, lines, sha256, tool_use_id, exit, is_error, target}."""
    entries = [e for e in extract_code(path, write=False, tr=tr) if e["kind"] in ("bash", "heredoc")]
    commands = iter(_commands(tr))
    out: list[dict] = []
    step, bodies, uid, used = 0, [], "", set()
    for e in entries:
        if e["kind"] == "bash":
            uid, cmd = next(commands)
            step += 1
            bodies, used = split_heredocs(cmd)[0], set()
            data, name, target, lines = cmd, f"step-{step:02d}.sh", "", len(cmd.splitlines())
        else:
            j = len([o for o in out if o["step"] == step and o["kind"] == "heredoc"]) + 1
            h = bodies[j - 1]
            data, target, lines = h["body"], h["name"] or "", h["lines"]
            name = heredoc_name(step, j, h["name"], h["python"] or e["name"].endswith(".py"))
            stem, dot, ext = name.rpartition(".")
            n = 2
            while name in used:
                name = f"{stem}-{n}{dot}{ext}"
                n += 1
        used.add(name)
        if e["sha256"] is not None and e["sha256"] != _sha(data):  # the same parser on the same text
            raise RuntimeError(f"{path}: step {step} does not match its extracted entry")
        out.append({"step": step, "kind": e["kind"], "name": name, "data": data, "lines": lines,
                    "sha256": e["sha256"], "tool_use_id": uid, "exit": e["exit"], "is_error": e["is_error"],
                    "target": target})
    return out


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main(argv: list[str] | None = None) -> int:
    runs, out, split = arguments("tsbench analyze snippets", __doc__ or "", argv)
    rows, n_runs = [], 0
    for run in iter_runs(runs, load_tasks(split)):
        files = snippets_of(run.path, run.tr)
        if not files:
            continue
        n_runs += 1
        for f in files:
            rel = pathlib.PurePosixPath(run.run_id) / f["name"]
            dest = out / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(f["data"].encode("utf-8"))
            rows.append({"run_id": run.run_id, "file": str(rel), **{k: f[k] for k in INDEX_COLUMNS if k in f}})
    write_csv(out / "index.csv", INDEX_COLUMNS, rows)
    write_readme(out, README)
    n_bash = sum(r["kind"] == "bash" for r in rows)
    print(f"runs with Bash: {n_runs}, commands: {n_bash}, heredocs: {len(rows) - n_bash}, out: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
