"""The one-page summary of a functional test (tools/functional_test.sh): what was tested, each step with pass or fail,
and links to every stored input and output.

    tsbench report summary --steps OUT/steps.jsonl --mode "gateway, model M" --out OUT/SUMMARY.html

Inputs: `steps.jsonl` (one JSON line per step: name, command, rc, log, outputs; written by the script) and, when they
exist next to it, `runs/scores.csv` (the verdict of each run) and `sandbox-probe/sandbox_probe.json`. The page links
`provenance.html` (tsbench report provenance) and `OVERVIEW.html` (tsbench report functional) when they lie next to
the page. Links are relative
to the page, so the folder can be moved or zipped as a whole. The page is templates/summary.html.j2: every datum is
HTML-escaped; the page has inline CSS only, the strict Content-Security-Policy of tsbench.report.page and no external
resource.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import pathlib

from tsbench.report import page
from tsbench.report.base import HARNESS
from tsbench.report.page import href
from tsbench.score.taxonomy import RETRIES_SUBTYPE, failure_category

__all__ = ["NOT_EVALUABLE_RC", "build_html", "context", "load_steps", "main"]

# exit code of a step that could not be evaluated (an API error, not a defect): tsbench env sandbox --probe, EX_TEMPFAIL
NOT_EVALUABLE_RC = 75

# What each step of the script shows, in the words of a reader who does not know the code.
PURPOSE = {
    "tasks-verify": "the task set matches its published hashes",
    "sandbox-probe": "condition B runs in an isolated sandbox (no repository, no home, no network beyond the API)",
    "plan-build": "the runs are fixed in advance: model, condition, task, prompt and environment hashes",
    "run": "one model call per planned run; transcripts and the inputs that made them are stored",
    "score": "every answer is checked against the task's reference and tolerance",
    "figures": "the figures are drawn from the score tables, with their source CSV",
    "report-views": "one readable page per run and an index",
    "report-gallery": "every run as a card: figures, images, code, how to re-run it",
    "report-dashboard": "one page over the run set: share correct per condition, every run in a table",
}

# The columns of scores.csv (score.SCORE_COLUMNS) that the rows keep; "category" is worked out from them.
SCORE_COLUMNS = ("model", "condition", "task_id", "correct", "evaluable", "not_evaluable_reason", "has_result",
                 "is_error", "result_subtype", "rescued", "unparseable")
INPUTS = ("runs/inputs/commands.sh", "runs/inputs/plan.jsonl", "runs/inputs/hashes.json", "runs/README.md",
          "runs/MANIFEST.json", "plan/plan.md", "steps.jsonl")
PROVENANCE_PAGE = "provenance.html"  # written next to the summary by `tsbench report provenance`
OVERVIEW_PAGE = "OVERVIEW.html"  # written next to the summary by `tsbench report functional`
PAGES = ("pages/dashboard.html", "pages/gallery.html", "pages/views.html", "figures/")


def load_steps(path: pathlib.Path) -> list[dict]:
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def _link(target: pathlib.Path, out_dir: pathlib.Path, text: str) -> dict:
    """A stored file for the `link` macro: its text, its relative link and whether it exists."""
    exists = target.exists()
    return {"text": text, "href": href(target, out_dir) if exists else None, "exists": exists}


def category(row: dict) -> str:
    """The word of one scores.csv row: the reason when the run is not evaluable (`rate_limited`, `api_error`),
    else `correct`, a harness stop or a format failure of the taxonomy (`no_result`,
    `max_turns`, `budget`, `api_error`, `unparseable`), else `wrong`. The kind of error needs the task, which this
    page does not read."""
    if str(row.get("evaluable") or "").strip().lower() not in ("1", "true"):
        return str(row.get("not_evaluable_reason") or "") or "not scored"
    found = failure_category(row, {})
    if found == "unparseable":  # without the task, the taxonomy's "nothing off" rule also fires for a wrong answer
        flagged = str(row.get("unparseable") or "").strip().lower() in ("1", "true")
        return found if flagged or row.get("result_subtype") == RETRIES_SUBTYPE else "wrong"
    return found if found == "correct" or found in HARNESS else "wrong"


def _scores(path: pathlib.Path) -> list[dict]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        rows = [{k: r.get(k) or "" for k in SCORE_COLUMNS} for r in csv.DictReader(f)]
    return [{**r, "category": category(r)} for r in rows]


def _probe(path: pathlib.Path) -> str:
    """The verdict of the sandbox probe, or "" without one."""
    if not path.is_file():
        return ""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    verdict = data.get("verdict") or data.get("status") or ("pass" if data.get("ok") else "")
    if not verdict and "passed" in data:
        verdict = "pass" if data["passed"] is True else "not evaluable" if data["passed"] is None else "fail"
    return str(verdict)


def _step(s: dict, root: pathlib.Path, out_dir: pathlib.Path) -> dict:
    rc = s["rc"]
    if rc == 0:
        state, word, chip, chip_text = "ok", "pass", "correct", "pass"
    elif rc == NOT_EVALUABLE_RC:
        state, word, chip, chip_text = "na", "not evaluable", "na429", "not evaluable (exit 75)"
    else:
        state, word, chip, chip_text = "fail", f"fail (exit {rc})", "wrong", f"fail (exit {rc})"
    return {"name": s["name"], "purpose": PURPOSE.get(s["name"], ""), "command": s["command"], "state": state,
            "word": word, "chip": chip, "chip_text": chip_text,
            "outputs": [_link(root / o, out_dir, o) for o in s.get("outputs", [])],
            "log": _link(root / s["log"], out_dir, "log")}


def _verdict(steps: list[dict]) -> dict:
    n_ok = sum(s["rc"] == 0 for s in steps)
    n_na = sum(s["rc"] == NOT_EVALUABLE_RC for s in steps)
    n_failed = len(steps) - n_ok - n_na
    if steps and n_ok == len(steps):
        return {"cls": "ok", "text": f"All {len(steps)} steps passed."}
    if not n_failed:
        return {"cls": "na", "text": f"{n_ok} steps passed, {n_na} not evaluable."}
    also = f", {n_na} not evaluable" if n_na else ""
    return {"cls": "fail", "text": f"{n_failed} of {len(steps)} steps failed{also}."}


def context(steps: list[dict], root: pathlib.Path, out: pathlib.Path, mode: str, when: str | None = None) -> dict:
    """Everything summary.html.j2 shows, as plain data."""
    out_dir = out.parent
    provenance = _link(out_dir / PROVENANCE_PAGE, out_dir, PROVENANCE_PAGE)
    overview = _link(out_dir / OVERVIEW_PAGE, out_dir, OVERVIEW_PAGE)
    return {
        "title": "Functional test", "mode": mode,
        "when": when or dt.datetime.now(dt.UTC).strftime("%Y-%m-%d %H:%M UTC"),
        "verdict": _verdict(steps), "probe": _probe(root / "sandbox-probe" / "sandbox_probe.json"),
        "steps": [_step(s, root, out_dir) for s in steps], "scores": _scores(root / "runs" / "scores.csv"),
        "inputs": [_link(root / p, out_dir, p) for p in INPUTS], "pages": [_link(root / p, out_dir, p) for p in PAGES],
        "provenance": provenance if provenance["exists"] else None,
        "overview": overview if overview["exists"] else None,
    }


def build_html(steps: list[dict], root: pathlib.Path, out: pathlib.Path, mode: str, when: str | None = None) -> str:
    return page.render("summary.html.j2", **context(steps, root, out, mode, when))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="tsbench report summary", description=__doc__.splitlines()[0])
    ap.add_argument("--steps", required=True, type=pathlib.Path, help="steps.jsonl written by tools/functional_test.sh")
    ap.add_argument("--mode", default="", help="one line: how the model was reached")
    ap.add_argument("--out", required=True, type=pathlib.Path)
    a = ap.parse_args(argv)
    steps = load_steps(a.steps)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(build_html(steps, a.steps.parent, a.out, a.mode), encoding="utf-8")
    print(f"wrote {a.out} ({sum(s['rc'] == 0 for s in steps)}/{len(steps)} steps passed)")
    return 0 if steps and all(s["rc"] == 0 for s in steps) else 1


if __name__ == "__main__":
    raise SystemExit(main())
