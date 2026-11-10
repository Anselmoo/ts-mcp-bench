#!/usr/bin/env python3
"""Build the publishable results folder of one finished confirmatory plan from its verified copy.

    uv run python tools/build_results.py --repo REPO --plan NAME --rules FILE --doi DOI [--source DIR]

`--source` holds `<plan>/` (the scored run folder), `preregistration/` and `plans/`; default
`REPO/results-basic/confirmatory`. The result goes to `REPO/results`. Without `TSBENCH_GATE_DENY` in the environment
the tool refuses to start, because the gate at its end would not know the names it has to refuse.

`--rules` is a JSON file outside the repository, so that no user name or machine path enters tracked text. It lists the
replacements in the order they apply, the most specific first; each `name` is a column `n_<name>` of the log:

    [{"name": "b_venv", "pattern": "/home/you/\\.cache/tsbench/venv-B", "replacement": "<B_VENV>"},
     {"name": "home", "pattern": "/home/you", "replacement": "<HOME>"}]

The steps, in order. A plan that did not finish is refused before anything is written. What an earlier build wrote for
the plan is removed. The run folder is copied without the files of the operation, with the published preregistration
files and the clear plan. Every copied text file gets the replacements, keeps its modification time and, when it
changed, a row in `REDACTIONS.csv` (file, sha256 before and after, count per rule). The images of the runs go to
`images/<plan>/` with an index; a row of an earlier index whose origin starts with `recovered` stays with its file,
since no transcript holds that image. The analyses run on a temporary copy and land in `code-snippets/<plan>/` and
`analysis/<plan>/`. The temporary copy is scored again: only `transcript_sha256` may differ from the scores of the
source. Answers that name an image no run left are listed. The gate of `tsbench release gate` reads `results/`, and
`SHA256SUMS` is written last, so a build that failed a check has none. Nothing is sent to a model.

Exit 0: built. Exit 1: refused or a check failed; the message says why.
"""
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from collections.abc import Callable, Iterable
from typing import NamedTuple

OPERATIONS = frozenset({"resume_after_budget.sh", "set_budget_after_layer1.sh", "resume.log", "set_budget.log",
                        "run.pid", "run.sh", "run.sh.pid", ".run.lock"})
PREREGISTERED = re.compile(r"\.sealed\.json$|^preregistration\.md$|^zenodo-record-\d+\.json$")
TEXT_SUFFIXES = frozenset({".jsonl", ".json", ".csv", ".log", ".md", ".txt", ".sh", ".py", ".html"})
ANALYSES = ("snippets", "strategy", "errors", "provenance", "effort")
IMAGE_COLUMNS = ["run_id", "file", "origin", "sha256"]
HARVESTED = "harvested from the run's working folder"
RETURNED = "returned by a tool (base64 in the transcript)"
RECOVERED = "recovered"  # the origin of an image that came from outside the run folder
IMAGE_EXT = {"image/png": ".png", "image/svg+xml": ".svg", "image/jpeg": ".jpg"}
RUN_TRANSCRIPT = re.compile(r"-k\d+\.jsonl$")
SCORE_KEY = ("model", "condition", "effort", "task_id", "k_index")
LOG, SUMS = "REDACTIONS.csv", "SHA256SUMS"
DENY_VAR = "TSBENCH_GATE_DENY"


class BuildError(Exception):
    """The plan is refused or a check failed."""


class Rule(NamedTuple):
    name: str
    pattern: re.Pattern[str]
    replacement: str

    @classmethod
    def parse(cls, entries: object) -> list[Rule]:
        """The rules of the entries of a rules file, in their order; BuildError when they are not a list of rules."""
        if not isinstance(entries, list) or not entries:
            raise BuildError("rules: a non-empty list of {name, pattern, replacement} is needed")
        try:
            return [cls(str(e["name"]), re.compile(e["pattern"]), str(e["replacement"])) for e in entries]
        except (KeyError, TypeError, re.error) as e:
            raise BuildError(f"rules: {e!r}") from e


def load_rules(path: pathlib.Path, repo: pathlib.Path) -> list[Rule]:
    """The rules of a file outside the repository."""
    if path.resolve().is_relative_to(repo.resolve()):
        raise BuildError(f"the rules file must lie outside the repository: {path.name}")
    try:
        return Rule.parse(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError) as e:
        raise BuildError(f"rules: {path.name}: {e}") from e


def sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tsbench(args: list[str]) -> None:
    """Run one tsbench command; its output goes to the log of this tool."""
    subprocess.run([sys.executable, "-m", "tsbench", *args], check=True, stdout=subprocess.DEVNULL)


def check_finished(run: pathlib.Path) -> None:
    """Refuse a plan whose last manifest is missing, stopped, or leaves runs open."""
    try:
        m = json.loads((run / "MANIFEST.json").read_text(encoding="utf-8"))
        c = m["counts"]
        done = c["done"] + c["skipped"] >= c["planned"]
    except (OSError, ValueError, KeyError, TypeError) as e:
        raise BuildError(f"plan not finished: no readable manifest in {run.name} ({e!r})") from e
    if not (m.get("finished") and not m.get("stop") and done):
        raise BuildError(f"plan not finished: {run.name}")


def copy_tree(src: pathlib.Path, dst: pathlib.Path, skip: frozenset[str] = frozenset()) -> None:
    for p in sorted(src.rglob("*")):
        if p.name in skip:
            continue
        q = dst / p.relative_to(src)
        if p.is_dir():
            q.mkdir(parents=True, exist_ok=True)
        elif p.is_file():
            q.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, q)


def copy_inputs(source: pathlib.Path, conf: pathlib.Path, plan: str) -> list[pathlib.Path]:
    """Copy the run folder, the published preregistration files and the clear plan; the folders and files copied."""
    copy_tree(source / plan, conf / plan, OPERATIONS)
    prereg = conf / "preregistration"
    prereg.mkdir(parents=True, exist_ok=True)
    for p in sorted((source / "preregistration").glob("*")):
        if p.is_file() and PREREGISTERED.search(p.name):
            shutil.copy2(p, prereg / p.name)
    (conf / "plans").mkdir(parents=True, exist_ok=True)
    shutil.copy2(source / "plans" / f"{plan}.jsonl", conf / "plans" / f"{plan}.jsonl")
    return [conf / plan, prereg, conf / "plans" / f"{plan}.jsonl"]


def _files(roots: Iterable[pathlib.Path]) -> list[pathlib.Path]:
    found = [p for r in roots for p in ([r] if r.is_file() else r.rglob("*")) if p.is_file()]
    return sorted(p for p in found if p.suffix in TEXT_SUFFIXES)


def replace_paths(roots: Iterable[pathlib.Path], out: pathlib.Path, rules: list[Rule]) -> list[list]:
    """Apply the rules to the text files below `roots`; one log row per changed file. The modification time stays."""
    rows = []
    for p in _files(roots):
        raw = p.read_bytes()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        new, counts = text, []
        for rule in rules:
            new, n = rule.pattern.subn(rule.replacement, new)
            counts.append(n)
        if new != text:
            st = p.stat()
            p.write_text(new, encoding="utf-8", newline="")
            os.utime(p, ns=(st.st_atime_ns, st.st_mtime_ns))
            rows.append([p.relative_to(out).as_posix(), hashlib.sha256(raw).hexdigest(), sha(p), *counts])
    return rows


def _of_plan(file: str, plan: str) -> bool:
    return f"/{plan}/" in file or file.endswith(f"/{plan}.jsonl")


def _read_log(path: pathlib.Path, header: list[str]) -> list[list[str]]:
    """The rows of the log without its header; [] without a log. A log with other columns is refused."""
    if not path.is_file():
        return []
    with path.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.reader(fh))
    if rows and rows[0] != header:
        raise BuildError(f"{LOG}: its columns differ from those of the rules ({', '.join(header)})")
    return rows[1:]


def write_log(path: pathlib.Path, header: list[str], rows: list[list]) -> None:
    """Write the log; a file logged twice keeps its place and its last row, so a file copied again has one row."""
    last = {r[0]: r for r in rows}
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(last.values())


def _recovered(out: pathlib.Path, plan: str) -> list[tuple[list[str], bytes]]:
    """The rows of the image index that no transcript can give back, each with the bytes of its file."""
    index = out / "images" / f"{plan}.index.csv"
    if not index.is_file():
        return []
    with index.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    return [([r[c] for c in IMAGE_COLUMNS], (out / r["file"]).read_bytes()) for r in rows
            if r["origin"].startswith(RECOVERED)]


def clear_plan(out: pathlib.Path, plan: str) -> None:
    """Remove the folders and the image index an earlier build wrote for the plan."""
    for path in (out / "confirmatory" / plan, out / "images" / plan, out / "code-snippets" / plan,
                 out / "analysis" / plan):
        shutil.rmtree(path, ignore_errors=True)
    (out / "images" / f"{plan}.index.csv").unlink(missing_ok=True)


def _save(data: bytes, path: pathlib.Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _tool_images(transcript: pathlib.Path) -> Iterable[tuple[str, bytes]]:
    """(media type, bytes) of every base64 image in the tool results of a transcript."""
    for line in transcript.read_text(encoding="utf-8").splitlines():
        try:
            message = json.loads(line).get("message")
        except (ValueError, AttributeError):
            continue
        for block in (message.get("content") or []) if isinstance(message, dict) else []:
            if not isinstance(block, dict) or block.get("type") != "tool_result":
                continue
            for item in block["content"] if isinstance(block.get("content"), list) else []:
                source = item.get("source") if isinstance(item, dict) and item.get("type") == "image" else None
                if isinstance(source, dict) and source.get("type") == "base64":
                    yield str(source.get("media_type")), base64.b64decode(source.get("data", ""))


def extract_images(run: pathlib.Path, out: pathlib.Path, plan: str, kept: list[tuple[list[str], bytes]]) -> int:
    """Write the images of the runs and their index; `kept` are rows of `_recovered`. The number of images."""
    root = out / "images" / plan
    rows: list[list[str]] = []

    def add(run_id: str, name: str, data: bytes, origin: str) -> None:
        path = root / run_id / name
        _save(data, path)
        rows.append([run_id, path.relative_to(out).as_posix(), origin, sha(path)])

    for t in sorted(run.glob("*/*/*/*.jsonl")):
        run_id = t.relative_to(run).as_posix().removesuffix(".jsonl")
        art = t.with_suffix(".artifacts")
        for f in sorted(art.iterdir()) if art.is_dir() else []:
            add(run_id, f.name, f.read_bytes(), HARVESTED)
        for i, (media, data) in enumerate(_tool_images(t), 1):
            add(run_id, f"tool-result-{i:02d}{IMAGE_EXT.get(media, '.bin')}", data, RETURNED)
    for row, data in kept:
        if hashlib.sha256(data).hexdigest() != row[3]:
            raise BuildError(f"recovered image {row[1]}: its sha256 differs from the index")
        _save(data, out / row[1])
        rows.append(row)
    with (out / "images" / f"{plan}.index.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(IMAGE_COLUMNS)
        w.writerows(rows)
    return len(rows)


def unharvested(run: pathlib.Path, held: set[str]) -> list[tuple[str, str, str]]:
    """(run id, image path, sha256) of the answers that name an image neither the run folder nor `held` has."""
    out = []
    for t in sorted(run.glob("*/*/*/*.jsonl")):
        run_id = t.relative_to(run).as_posix().removesuffix(".jsonl")
        if not RUN_TRANSCRIPT.search(t.name) or t.with_suffix(".artifacts").is_dir() or run_id in held:
            continue
        results = [json.loads(ln) for ln in t.read_text(encoding="utf-8").splitlines()
                   if '"type":"result"' in ln.replace(" ", "")]
        answer = results[-1].get("structured_output") if results else None
        if isinstance(answer, dict) and answer.get("image_path"):
            out.append((run_id, str(answer["image_path"]), str(answer.get("image_sha256"))))
    return out


def run_analyses(run: pathlib.Path, out: pathlib.Path, plan: str, flags: list[str], work: pathlib.Path,
                 command: Callable[[list[str]], None]) -> pathlib.Path:
    """The analyses of `tsbench analyze` and `tsbench score path` on a copy of the run folder; the copy."""
    copy = work / plan
    shutil.copytree(run, copy)
    for name in ANALYSES:
        command(["analyze", name, "--runs", str(copy), "--out", str(work / "out" / name), *flags])
    command(["score", "path", "--runs", str(copy), "--out", str(work / "out" / "paths"), *flags])
    shutil.copytree(work / "out" / "snippets", out / "code-snippets" / plan)
    for name in (*ANALYSES[1:], "paths"):
        shutil.copytree(work / "out" / name, out / "analysis" / plan / name)
    return copy


def _scores(path: pathlib.Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def rescore_check(copy: pathlib.Path, original: pathlib.Path, flags: list[str],
                  command: Callable[[list[str]], None]) -> None:
    """Score the published copy again: only `transcript_sha256` may differ from the scores of the source."""
    for name in ("scores.csv", "rates.csv"):
        (copy / name).unlink(missing_ok=True)
    command(["score", "--runs", str(copy), *flags])
    again = {tuple(r[k] for k in SCORE_KEY): r for r in _scores(copy / "scores.csv")}
    source = _scores(original)
    differing = Counter(col for r in source for col in r
                        if again.get(tuple(r[k] for k in SCORE_KEY), {}).get(col) != r[col])
    other = {k: v for k, v in differing.items() if k != "transcript_sha256"}
    if other or len(again) != len(source):
        raise BuildError(f"the published copy scores differently: {len(again)} of {len(source)} rows, columns {other}")


def gate_check(repo: pathlib.Path, out: pathlib.Path) -> None:
    """The text gate of `tsbench release gate` over the results."""
    from tsbench.release import gate
    files = sorted(p.relative_to(repo).as_posix() for p in out.rglob("*") if p.is_file())
    hits = gate.forbidden_text(repo, files)
    if hits:
        raise BuildError(f"gate: {len(hits)} hits, for example {hits[0]}")


def write_checksums(out: pathlib.Path) -> None:
    """`SHA256SUMS`: one `<sha256>  ./<path>` line per file, in byte order of the paths."""
    files = [p for p in out.rglob("*") if p.is_file() and p.name not in {SUMS, ".gitkeep"}]
    named = sorted((f"./{p.relative_to(out).as_posix()}", p) for p in files)
    named.sort(key=lambda x: x[0].encode("utf-8"))
    (out / SUMS).write_text("".join(f"{sha(p)}  {name}\n" for name, p in named), encoding="utf-8")


def build(repo: pathlib.Path, plan: str, source: pathlib.Path, rules: list[Rule], doi: str,
          run: Callable[[list[str]], None] | None = None) -> dict:
    """Build `repo/results` for the plan. `run` runs one tsbench command (default: the command of this checkout).
    Returns the counts of the build: {replaced, images, unharvested}."""
    command = run or tsbench
    if not os.environ.get(DENY_VAR):
        raise BuildError(f"set {DENY_VAR}: the gate at the end needs the names it has to refuse")
    check_finished(source / plan)
    out, conf = repo / "results", repo / "results" / "confirmatory"
    flags = ["--split", "confirmatory", "--i-have-preregistered", doi]
    header = ["file", "sha256_original", "sha256_published", *(f"n_{r.name}" for r in rules)]
    logged = [r for r in _read_log(out / LOG, header) if not _of_plan(r[0], plan)]
    kept = _recovered(out, plan)
    clear_plan(out, plan)
    log_rows = replace_paths(copy_inputs(source, conf, plan), out, rules)
    write_log(out / LOG, header, [*logged, *log_rows])
    n_images = extract_images(conf / plan, out, plan, kept)
    with tempfile.TemporaryDirectory(prefix=f"build-{plan}-") as tmp:
        copy = run_analyses(conf / plan, out, plan, flags, pathlib.Path(tmp), command)
        rescore_check(copy, source / plan / "scores.csv", flags, command)
    missing = unharvested(conf / plan, {row[0] for row, _ in kept})
    gate_check(repo, out)
    write_checksums(out)
    return {"replaced": len(log_rows), "images": n_images, "unharvested": missing}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="tools/build_results.py", description=(__doc__ or "").split("\n")[0])
    ap.add_argument("--repo", required=True, type=pathlib.Path, help="the repository; the result goes to its results/")
    ap.add_argument("--plan", required=True, help="name of the plan, a folder of the source")
    ap.add_argument("--source", type=pathlib.Path, default=None,
                    help="the verified copy with <plan>/, preregistration/ and plans/ "
                         "(default REPO/results-basic/confirmatory)")
    ap.add_argument("--rules", required=True, type=pathlib.Path,
                    help="JSON file of replacements, outside the repository")
    ap.add_argument("--doi", required=True, help="the DOI of the preregistration")
    a = ap.parse_args(argv)
    try:
        rules = load_rules(a.rules, a.repo)
        got = build(a.repo, a.plan, a.source or a.repo / "results-basic" / "confirmatory", rules, a.doi)
    except (BuildError, OSError, subprocess.CalledProcessError) as e:
        print(f"tools/build_results.py: {e}", file=sys.stderr)
        return 1
    print(f"{a.plan}: {got['replaced']} files with replacements, {got['images']} images, "
          f"{len(got['unharvested'])} answers naming an image no run left")
    for run_id, image, digest in got["unharvested"]:
        print(f"  {run_id}: {image} ({digest})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
