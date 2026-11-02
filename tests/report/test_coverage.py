"""Tests for tsbench.report.coverage (pilot matrix coverage). Pilot tasks only."""
from __future__ import annotations

import json
import pathlib

from tsbench.report import coverage as cv
from tsbench.report import page


def _cov(cells):
    return {"k": 3, "effort": "medium", "models": ["m"], "conds": ["A"], "skipped_run_sets": [],
            "tasks": [{"id": c["task"], "class": c["class"]} for c in cells], "cells": cells}


def test_zero_cells_name_the_not_evaluable_classes_or_no_runs():
    cov = _cov([{"task": "P-a-01", "class": "a", "model": "m", "cond": "A", "ok": 0, "bad": {"rate_limited": 2}},
                {"task": "P-a-02", "class": "a", "model": "m", "cond": "A", "ok": 0, "bad": {}},
                {"task": "P-a-03", "class": "a", "model": "m", "cond": "A", "ok": 3, "bad": {}}])
    z = cv.zero_cells(cov)
    assert [x["task"] for x in z] == ["P-a-01", "P-a-02"]
    assert z[0]["why"] == "HTTP 429 × 2" and z[1]["why"] == "no runs"


def test_page_counts_and_escapes():
    cov = _cov([{"task": "P-a-01", "class": "<a>", "model": "m", "cond": "A", "ok": 3, "bad": {}},
                {"task": "P-a-02", "class": "<a>", "model": "m", "cond": "A", "ok": 1, "bad": {"api_error": 1}}])
    h = cv.build_html(cov)
    assert "1/2" in h and "&lt;a&gt;" in h and "<a>" not in h.split("<body>", 1)[1].split("<script", 1)[0]
    assert "4 of 6 evaluable runs for k = 3 (67 %): cells have 1 to 3 evaluable runs." in h


def test_coverage_without_runs_names_the_given_models(tmp_path):
    cov = cv.coverage([], models=["m1", "m2"])
    assert cov["cells"] and all(c["ok"] == 0 for c in cov["cells"]) and not cov["skipped_run_sets"]
    assert len(cov["cells"]) == len(cov["tasks"]) * 2 * len(cv.CONDS)
    assert cv.coverage([])["cells"] == []                                    # no runs, no models: no cells


def test_cli_counts_runs_of_two_run_sets_found_by_discovery(tmp_path, capsys):
    from tsbench.run import runner
    root = tmp_path / "results"
    for name, model in (("one", "claude-haiku-5-5"), ("two", "claude-opus-5-5")):
        runner.main(["--split", "pilot", "--models", model, "--conditions", "A", "--effort", "medium", "--k", "1",
                     "--budget-usd", "10", "--out", str(root / name), "--dry-run", "--limit", "2"])
    out, js = tmp_path / "site" / "coverage.html", tmp_path / "site" / "coverage.json"
    assert cv.main(["--runs", str(root), "--out", str(out), "--json", str(js), "--k", "1"]) == 0
    cov = json.loads(js.read_text(encoding="utf-8"))
    assert cov["models"] == ["claude-haiku-5-5", "claude-opus-5-5"]
    assert sum(c["ok"] for c in cov["cells"]) + sum(sum(c["bad"].values()) for c in cov["cells"]) == 4
    markup = out.read_text(encoding="utf-8")
    assert "Coverage of the pilot matrix" in markup and page.CSP in markup and str(tmp_path) not in markup


def _one_run_set(folder):
    from tsbench.run import runner
    runner.main(["--split", "pilot", "--models", "claude-haiku-5-5", "--conditions", "A", "--effort", "medium",
                 "--k", "1", "--budget-usd", "10", "--out", str(folder), "--dry-run", "--limit", "2"])
    return folder


def _cells(cov):
    return {(c["task"], c["cond"]): c for c in cov["cells"] if c["model"] == "claude-haiku-5-5"}


def test_a_repetition_found_in_two_run_sets_counts_once(tmp_path):
    """A run set and a copy of it hold the same (task, model, condition, k): the cell has one run, not two."""
    import shutil
    one = _one_run_set(tmp_path / "one")
    shutil.copytree(one, tmp_path / "copy")
    cov = cv.coverage([one, tmp_path / "copy"], k=3, conds=("A",))
    cells = _cells(cov)
    assert [c["ok"] for c in cells.values() if c["ok"]] == [1, 1]
    assert cv.coverage([one], k=3, conds=("A",))["cells"] == cov["cells"]


def test_an_evaluable_copy_of_a_run_wins_over_a_not_evaluable_one(tmp_path):
    import shutil
    one = _one_run_set(tmp_path / "one")
    copy = tmp_path / "copy"
    shutil.copytree(one, copy)
    for path in copy.glob("*/*/*/*.jsonl"):
        lines = path.read_text(encoding="utf-8").splitlines()
        res = {k: v for k, v in json.loads(lines[-1]).items() if k != "structured_output"}
        res.update({"is_error": True, "api_error_status": 429, "result": "rate limit"})
        path.write_text("\n".join([*lines[:-1], json.dumps(res)]) + "\n", encoding="utf-8")
    for sets in ([one, copy], [copy, one]):
        cells = _cells(cv.coverage(sets, k=3, conds=("A",)))
        assert [c["ok"] for c in cells.values() if c["ok"] or c["bad"]] == [1, 1]
        assert all(not c["bad"] for c in cells.values())
    only_bad = [c for c in _cells(cv.coverage([copy], k=3, conds=("A",))).values() if c["bad"]]
    assert [c["bad"] for c in only_bad] == [{"rate_limited": 1}] * 2 and all(c["ok"] == 0 for c in only_bad)


def test_context_is_plain_data_and_the_module_writes_no_markup():
    cov = _cov([{"task": "P-a-01", "class": "a", "model": "m", "cond": "A", "ok": 3, "bad": {}},
                {"task": "P-a-02", "class": "a", "model": "m", "cond": "A", "ok": 0, "bad": {"rate_limited": 1}}])
    ctx = cv.context(cov, generated="2026-01-01 00:00")
    assert ctx["title"] == "Coverage of the pilot matrix" and ctx["stamp"] == "2026-01-01 00:00"
    assert (ctx["n_tasks"], ctx["n_cells"], ctx["need"], ctx["n_zeros"]) == (2, 2, 3, 1)
    row = ctx["rows"][0]
    assert row["class"] == "a" and [(c["full"], c["n"]) for c in row["cells"]] == [(1, 2)]
    assert ctx["zeros"][0]["why"] == "HTTP 429 × 1" and ctx["per_model"] == [("m", 1)]
    assert "<" not in json.dumps(ctx)
    source = (pathlib.Path(cv.__file__)).read_text(encoding="utf-8")
    assert "<td" not in source and "<tr" not in source and "<h1" not in source


def test_page_shades_a_cell_by_its_share_and_names_it_in_the_title():
    cov = _cov([{"task": "P-a-01", "class": "a", "model": "m", "cond": "A", "ok": 3, "bad": {}},
                {"task": "P-a-02", "class": "a", "model": "m", "cond": "A", "ok": 1, "bad": {}}])
    h = cv.build_html(cov, generated="now")
    assert '<td class="num hm hd" style="--p:0.667" title="4 of 6 runs; 1 of 2 tasks with ≥ 3">4/6' in h
    assert "<small>1/2 tasks ≥ 3</small>" in h and "Generated now." in h and "td.num{text-align:center" in h
    assert "td.hm,span.hm{background:color-mix(" in h  # the shade follows the colour scheme
    assert "Run sets skipped (made with another task set): 0." in h


def test_page_names_skipped_run_sets_and_a_clean_matrix():
    cov = _cov([{"task": "P-a-01", "class": "a", "model": "m", "cond": "A", "ok": 3, "bad": {}}])
    cov["skipped_run_sets"] = ["old<1>", "old2"]
    h = cv.build_html(cov, generated="now")
    assert "(old&lt;1&gt;, old2)" in h and "<p>None: every cell has at least one evaluable run.</p>" in h


def test_summary_share_rounds_a_half_up():
    """1 of 8 evaluable runs is 12.5 %: it reads 13, as 3 of 8 (37.5 %) reads 38."""
    for ok, text in ((1, "(13 %)"), (3, "(38 %)")):
        cov = _cov([{"task": "P-a-01", "class": "a", "model": "m", "cond": "A", "ok": ok, "bad": {}}])
        cov["k"] = 8
        assert text in cv.context(cov, generated="x")["summary"]
