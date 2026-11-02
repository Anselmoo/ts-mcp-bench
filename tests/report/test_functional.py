"""The overview page of a functional test (tsbench report functional): the verdict, the steps on a time line, which
step read what another step wrote, the runs and their verdicts, and links to the summary and the provenance page. The
trace records are written by hand in the format of tsbench.core.trace."""
from __future__ import annotations

import csv
import json
from pathlib import Path

from tsbench import cli
from tsbench.report import functional, page
from tsbench.score.score import SCORE_COLUMNS

HOSTILE = '<img src=x onerror=alert(1)>"\'&'
H_TASKS, H_PLAN, H_TRANSCRIPT, H_SCORES = ("d4" * 32, "a1" * 32, "b2" * 32, "c3" * 32)


def _open(path: Path | str, mode: str, sha: str) -> dict:
    reading = mode.startswith("r")
    return {"event": "open", "path": str(path), "mode": mode, "caller": "tsbench.x:f",
            "sha256_at_read": sha if reading else None, "sha256_at_end": sha}


def _record(pid: int, start: float, end: float, files: list[dict], calls: int = 2) -> dict:
    return {"schema": "tsbench.trace/1", "pid": pid, "ppid": 1, "argv": ["tsbench"], "command": "tsbench",
            "cwd": "/w", "start": start, "end": end, "exit_code": 0, "files": files,
            "calls": [{"function": f"tsbench.m:f{i}", "caller": None, "count": 1} for i in range(calls)]}


def write_scores(path: Path, rows: list[dict]) -> None:
    """A scores.csv with the columns the scorer writes (score.SCORE_COLUMNS); a key a row leaves out stays empty."""
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=SCORE_COLUMNS)
        w.writeheader()
        w.writerows(rows)


def folder(root: Path, *, transcript_read: str = H_TRANSCRIPT, score_rc: int = 0) -> Path:
    """steps.jsonl, trace/<step>/ for plan-build, run (two processes) and score, runs/scores.csv and a probe."""
    plan, transcript, scores = root / "plan" / "plan.jsonl", root / "runs" / "t-k1.jsonl", root / "runs" / "scores.csv"
    traces = {
        "plan-build": [_record(10, 100.0, 101.0, [_open("~/repo/tasks.jsonl", "r", H_TASKS),
                                                  _open(plan, "w", H_PLAN)])],
        "run": [_record(20, 102.0, 105.0, [_open(plan, "r", H_PLAN), _open(transcript, "w", H_TRANSCRIPT)]),
                _record(21, 103.0, 104.5, [_open(plan, "r", H_PLAN)], calls=3)],
        "score": [_record(30, 106.0, 106.5, [_open(transcript, "r", transcript_read), _open(scores, "w", H_SCORES)])],
    }
    steps = []
    for name, records in traces.items():
        d = root / "trace" / name
        d.mkdir(parents=True)
        for rec in records:
            (d / f"{rec['pid']}.trace.json").write_text(json.dumps(rec), encoding="utf-8")
        steps.append({"name": name, "command": f"tsbench {name}", "rc": score_rc if name == "score" else 0,
                      "log": f"logs/{name}.log", "outputs": []})
    steps.append({"name": "tasks-verify", "command": "tsbench tasks verify", "rc": 0, "log": "logs/t.log",
                  "outputs": []})  # a step without a trace folder
    (root / "steps.jsonl").write_text("".join(json.dumps(s) + "\n" for s in steps), encoding="utf-8")
    scores.parent.mkdir(parents=True, exist_ok=True)
    base = {"model": "m", "task_id": "t1", "correct": True, "evaluable": True, "has_result": True, "is_error": False}
    write_scores(scores, [
        {**base, "condition": "A"},
        {**base, "condition": "B", "correct": False},
        {**base, "condition": "C", "correct": "", "evaluable": False, "has_result": False, "is_error": True,
         "not_evaluable_reason": "rate_limited"},
        {**base, "condition": "A", "task_id": HOSTILE}])
    probe = root / "sandbox-probe" / "sandbox_probe.json"
    probe.parent.mkdir(parents=True)
    probe.write_text(json.dumps({"verdict": "pass"}), encoding="utf-8")
    return root


def ctx(root: Path) -> dict:
    return functional.context(functional.load_steps(root / "steps.jsonl"), root, root / functional.PAGE_NAME,
                              mode="fake claude", when="2026-10-30 12:00 UTC")


def test_timeline_spans_each_step_from_its_first_start_to_its_last_end(tmp_path):
    c = ctx(folder(tmp_path))
    rows = {r["name"]: r for r in c["timeline"]}
    assert rows["plan-build"] == {"name": "plan-build", "start": 0.0, "end": 1.0, "processes": 1, "state": "ok"}
    assert rows["run"]["start"] == 2.0 and rows["run"]["end"] == 5.0 and rows["run"]["processes"] == 2
    assert rows["score"]["start"] == 6.0 and rows["score"]["end"] == 6.5
    assert "tasks-verify" not in rows  # not traced: no bar
    assert [r["name"] for r in c["timeline"]] == ["plan-build", "run", "score"]  # in step order
    assert c["facts"]["wall_seconds"] == 6.5


def test_flow_counts_what_each_step_read_from_an_earlier_step_and_from_outside(tmp_path):
    c = ctx(folder(tmp_path))
    flow = {r["name"]: r for r in c["flow"]}
    assert flow["plan-build"]["from_steps"] == {} and flow["plan-build"]["outside"] == 1
    assert flow["plan-build"]["written"] == 1
    assert flow["run"]["from_steps"] == {"plan-build": 2} and flow["run"]["outside"] == 0  # two processes read plan
    assert flow["score"]["from_steps"] == {"run": 1} and flow["score"]["written"] == 1
    assert c["edges"] == [{"source": "plan-build", "target": "run", "files": 2},
                          {"source": "run", "target": "score", "files": 1}]


def test_facts_name_steps_chain_processes_files_and_runs(tmp_path):
    f = ctx(folder(tmp_path))["facts"]
    assert f["steps_ok"] == 4 and f["steps"] == 4
    assert f["chain_intact"] is True and f["breaks"] == 0
    assert f["processes"] == 4 and f["functions"] == 9
    assert f["files_read"] == 3 and f["files_written"] == 3  # distinct paths
    assert f["runs"] == 4 and f["runs_evaluable"] == 3 and f["runs_correct"] == 2
    assert f["probe"] == "pass"


def test_runs_grid_is_task_by_condition(tmp_path):
    grid = ctx(folder(tmp_path))["grid"]
    assert grid["conds"] == ["A", "B", "C"]
    row = next(r for r in grid["rows"] if r["task"] == "t1")
    assert [cell["key"] for cell in row["cells"]] == ["correct", "wrong", "na429"]


def test_runs_grid_reads_the_columns_the_scorer_writes(tmp_path):
    root = folder(tmp_path)
    base = {"model": "m", "condition": "A", "correct": False, "evaluable": True, "has_result": True,
            "is_error": False}
    write_scores(root / "runs" / "scores.csv", [
        {**base, "task_id": "turns", "result_subtype": "error_max_turns"},
        {**base, "task_id": "budget", "result_subtype": "error_max_budget_usd"},
        {**base, "task_id": "silent", "has_result": False},
        {**base, "task_id": "limited", "evaluable": False, "is_error": True, "not_evaluable_reason": "api_error"},
        {**base, "task_id": "off", "result_subtype": "success"}])
    keys = {r["task"]: r["cells"][0]["key"] for r in ctx(root)["grid"]["rows"]}
    assert keys == {"turns": "harness", "budget": "harness", "silent": "harness", "limited": "na429",
                    "off": "wrong"}


def test_broken_chain_and_failed_step_make_the_verdict_fail(tmp_path):
    root = folder(tmp_path, transcript_read="ff" * 32, score_rc=1)
    c = ctx(root)
    assert c["facts"]["chain_intact"] is False and c["facts"]["breaks"] == 1
    assert c["verdict"]["cls"] == "fail"
    rc = functional.main(["--steps", str(root / "steps.jsonl"), "--out", str(root / "o.html")])
    assert rc == 1


def test_page_is_escaped_self_contained_and_links_the_detail_pages(tmp_path):
    root = folder(tmp_path)
    (root / "SUMMARY.html").write_text("x", encoding="utf-8")
    (root / "provenance.html").write_text("x", encoding="utf-8")
    out = root / functional.PAGE_NAME
    rc = functional.main(["--steps", str(root / "steps.jsonl"), "--mode", "fake claude", "--out", str(out)])
    html = out.read_text(encoding="utf-8")
    assert rc == 0
    assert HOSTILE not in html and "&lt;img src=x" in html
    assert page.CSP in html and "<link" not in html and 'src="http' not in html
    assert 'href="SUMMARY.html"' in html and 'href="provenance.html"' in html
    assert html.count('<figure class="ftd') == 2  # time line and flow, drawn by the page's own script
    assert "<noscript>" in html


def test_cli_lists_the_command():
    assert ("report", "functional") in cli.COMMANDS


def test_summary_links_the_overview_when_it_lies_next_to_it(tmp_path):
    from tsbench.report import summary

    root = folder(tmp_path)
    steps = summary.load_steps(root / "steps.jsonl")
    assert f'href="{functional.PAGE_NAME}"' not in summary.build_html(steps, root, root / "SUMMARY.html", "m")
    (root / functional.PAGE_NAME).write_text("<p>x</p>", encoding="utf-8")
    assert f'href="{functional.PAGE_NAME}"' in summary.build_html(steps, root, root / "SUMMARY.html", "m")
