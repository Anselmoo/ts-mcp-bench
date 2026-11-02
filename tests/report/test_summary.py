"""The one-page functional-test summary (tsbench report summary)."""
from __future__ import annotations

import ast
import csv
import json
import re
from pathlib import Path

from tsbench.report import summary
from tsbench.report.page import CSP
from tsbench.score.score import SCORE_COLUMNS


def _steps(tmp_path, rcs):
    (tmp_path / "logs").mkdir()
    lines = []
    for name, rc in rcs:
        (tmp_path / "logs" / f"{name}.log").write_text("ok\n", encoding="utf-8")
        lines.append(json.dumps({"name": name, "command": f"tsbench {name} --x '<b>'", "rc": rc,
                                 "log": f"logs/{name}.log", "outputs": ["runs/scores.csv"]}))
    p = tmp_path / "steps.jsonl"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def test_all_steps_pass_links_and_escaping(tmp_path, capsys):
    steps = _steps(tmp_path, [("tasks-verify", 0), ("score", 0)])
    (tmp_path / "runs").mkdir()
    (tmp_path / "runs" / "scores.csv").write_text(
        "model,condition,task_id,correct,evaluable\nm<x>,C,P-curve-01,True,True\n", encoding="utf-8")
    out = tmp_path / "SUMMARY.html"
    assert summary.main(["--steps", str(steps), "--mode", "fake <mode>", "--out", str(out)]) == 0
    page = out.read_text(encoding="utf-8")
    assert "All 2 steps passed." in page and CSP in page
    assert 'href="runs/scores.csv"' in page and 'href="logs/score.log"' in page
    assert "m&lt;x&gt;" in page and "fake &lt;mode&gt;" in page and "--x &#39;&lt;b&gt;&#39;" in page  # Jinja escapes
    # no external resource (the inlined d3 names XML namespaces)
    assert not re.search(r"(src|href)=\"(https?:|//)", page)


def test_a_failed_step_fails_the_summary(tmp_path):
    steps = _steps(tmp_path, [("run", 0), ("figures", 1)])
    out = tmp_path / "SUMMARY.html"
    assert summary.main(["--steps", str(steps), "--out", str(out)]) == 1
    page = out.read_text(encoding="utf-8")
    assert "1 of 2 steps failed." in page and "fail (exit 1)" in page
    assert "runs/scores.csv (missing)" in page


def test_the_category_column_reads_the_columns_the_scorer_writes(tmp_path):
    steps = _steps(tmp_path, [("score", 0)])
    (tmp_path / "runs").mkdir()
    with (tmp_path / "runs" / "scores.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=SCORE_COLUMNS)
        w.writeheader()
        base = {"model": "m", "condition": "A", "correct": False, "evaluable": True, "has_result": True}
        w.writerows([
            {**base, "task_id": "t-turns", "result_subtype": "error_max_turns"},
            {**base, "task_id": "t-limited", "evaluable": False, "not_evaluable_reason": "rate_limited"},
            {**base, "task_id": "t-ok", "correct": True},
            {**base, "task_id": "t-plain"},
            {**base, "task_id": "t-format", "unparseable": True},
            {**base, "task_id": "t-retries", "result_subtype": "error_max_structured_output_retries"}])
    out = tmp_path / "SUMMARY.html"
    assert summary.main(["--steps", str(steps), "--out", str(out)]) == 0
    text = out.read_text(encoding="utf-8")
    cells = {m[0]: m[1] for m in re.findall(r"<td>(t-[a-z]+)</td>.*?<td>([^<]*)</td></tr>", text)}
    assert cells == {"t-turns": "max_turns", "t-limited": "rate_limited", "t-ok": "correct", "t-plain": "wrong",
                     "t-format": "unparseable", "t-retries": "unparseable"}


def test_exit_75_is_shown_as_not_evaluable_not_as_a_failure(tmp_path):
    steps = _steps(tmp_path, [("tasks-verify", 0), ("sandbox-probe", 75), ("run", 0)])
    out = tmp_path / "SUMMARY.html"
    assert summary.main(["--steps", str(steps), "--out", str(out)]) == 1  # not all steps passed
    page = out.read_text(encoding="utf-8")
    assert "not evaluable" in page and "fail (exit 75)" not in page
    assert "2 steps passed, 1 not evaluable." in page and "steps failed" not in page
    assert "All 3 steps passed." not in page


def test_a_failure_and_a_not_evaluable_step_are_both_counted(tmp_path):
    steps = _steps(tmp_path, [("sandbox-probe", 75), ("figures", 1)])
    out = tmp_path / "SUMMARY.html"
    summary.main(["--steps", str(steps), "--out", str(out)])
    page = out.read_text(encoding="utf-8")
    assert "1 of 2 steps failed, 1 not evaluable." in page and "fail (exit 1)" in page


def test_this_file_names_utf8_in_every_text_read_and_write():
    """Every text read and write names utf-8, so the tests read the page as summary.main wrote it on any locale."""
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    bare = [n.lineno for n in ast.walk(tree)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and n.func.attr in {"read_text", "write_text"} and not any(k.arg == "encoding" for k in n.keywords)]
    assert not bare, f"read_text/write_text without encoding on lines {bare}"
    assert any(isinstance(n, ast.ImportFrom) and n.module == "__future__" for n in tree.body)
