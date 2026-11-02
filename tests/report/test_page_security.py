"""Security properties every report page builder must have: the Content-Security-Policy meta, escaped figure captions
and data values, no `file:` URI and no absolute path of the machine that built the page, no external resource."""
from __future__ import annotations

import csv
import json
import re

import pytest

from tsbench.report import comparison, coverage, dashboard, gallery, literature, page, views

HOSTILE = '<img src=x onerror=alert(1)>"\'&'
CSP_META = f'<meta http-equiv="Content-Security-Policy" content="{page.CSP}">'


def _own(page: str) -> str:
    """The page without the inlined libraries (d3 and the Figura bundle contain URLs of their own)."""
    page = re.sub(r'<script id="jfs-lib">.*?</script>', "", page, flags=re.S)
    page = re.sub(r'<script id="fig-draw">.*?</script>', "", page, flags=re.S)
    return re.sub(r"<script>(?:!function|// https://d3js).*?</script>", "", page, flags=re.S)


def _check(page: str, tmp_path) -> None:
    own = _own(page)
    assert CSP_META in page, "every page carries the CSP"
    assert HOSTILE not in page and "<img src=x" not in page, "data values are escaped"
    for cap in re.findall(r"<figcaption>(.*?)</figcaption>", page, flags=re.S):
        assert "<" not in cap, f"caption not escaped: {cap[:80]}"
    assert "file:" not in own and str(tmp_path) not in page, "no file: URI and no absolute path"
    assert not re.search(r"""src\s*=\s*["']?(?:https?:)?//""", own, re.I), "no external resource"
    for link in re.findall(r"""href\s*=\s*["']?((?:https?:)?//[^"'\s>]*)""", own, re.I):
        assert link.startswith("https://doi.org/"), f"only DOI links leave the page: {link}"
    assert not re.search(r"<link\b|@import|<script[^>]+src=", own, re.I)


def test_fig_macro_escapes_caption_and_alt():
    call = '{% from "_macros.html.j2" import fig %}{{ fig("rate", {"rows": []}, c, c) }}'
    out = page.ENV.from_string(call).render(c=HOSTILE)
    assert HOSTILE not in out and "&lt;img src=x onerror=alert(1)&gt;" in out


def test_the_frame_has_the_csp_and_english():
    markup = page.render("base.html.j2", title="T")
    assert CSP_META in markup and 'lang="en"' in markup and "default-src 'none'" in page.CSP


def test_href_never_absolute(tmp_path):
    assert page.href(tmp_path / "a" / "b.html", tmp_path / "c") == "../a/b.html"


def _hostile_runs_folder(tmp_path):
    """A run folder (no MANIFEST.json) whose model name, task class and answer are hostile."""
    from tsbench.tasks import load
    task = load("pilot")[0]
    d = tmp_path / "runs" / HOSTILE.replace("/", "_") / "C" / "medium"
    d.mkdir(parents=True)
    events = [{"type": "assistant", "message": {"content": [{"type": "text", "text": HOSTILE}]}},
              {"type": "result", "subtype": "success", "is_error": False, "result": HOSTILE, "num_turns": 1}]
    (d / f"{task['id']}-k1.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events), encoding="utf-8")
    return tmp_path / "runs"


def test_views_pages(tmp_path):
    runs = _hostile_runs_folder(tmp_path)
    views.render_dir(runs)
    pages = list((runs / "views").rglob("*.html"))
    assert len(pages) == 2
    for p in pages:
        _check(p.read_text(encoding="utf-8"), tmp_path)


def test_gallery_page(tmp_path):
    runs = _hostile_runs_folder(tmp_path)
    page, counts = gallery.build_html([runs], tmp_path / "site", make_figs=False)
    assert counts["runs"] == 1
    _check(page, tmp_path)


def _run(**kw):
    r = {"set": HOSTILE, "model": HOSTILE, "cond": "C", "task_id": "P-x-01", "cls": HOSTILE, "outcome": "correct",
         "has_result": True, "out_tok": 10.0, "api_s": 1.0, "cost": 0.01, "reason": None}
    r.update(kw)
    return r


def test_comparison_page(tmp_path):
    runs = [_run(), _run(cond="A", outcome="wrong", reason="no_structured"),
            _run(cond="B", outcome="na429")]
    data = {"runs": runs, "planned": {}, "costs": {HOSTILE: 1.0}, "notes": [HOSTILE], "date": HOSTILE,
            "run_sets": [{"name": HOSTILE, "title": HOSTILE}]}
    _check(comparison.build_html(data), tmp_path)


def test_dashboard_page(tmp_path):
    d = tmp_path / "set"
    d.mkdir()
    cols = ["model", "condition", "effort", "task_id", "k_index", "class", "correct", "has_result"]
    with open(d / "scores.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, cols)
        w.writeheader()
        w.writerow({"model": HOSTILE, "condition": "C", "effort": "medium", "task_id": HOSTILE, "k_index": "1",
                    "class": HOSTILE, "correct": "True", "has_result": "True"})
    (d / "MANIFEST.json").write_text(json.dumps({"plan_id": HOSTILE, "git_commit": HOSTILE}), encoding="utf-8")
    data = dashboard.collect([d], tmp_path / "out" / "r.html", {}, score_missing=False)
    _check(dashboard.build_html(data, HOSTILE), tmp_path)


def test_literature_page(tmp_path):
    data = literature.collect([], tmp_path / "out" / "lit.html")
    ent = next(e for e in data["entries"].values() if e["cls"] == "literature_all")
    path = tmp_path / "set" / HOSTILE / "C" / "medium" / f"{ent['id']}-k1.jsonl"
    vals = {p: ent["ref"][p] for p in literature.PARAMS}
    data["runs"] = [{"key": ent["key"], "set": HOSTILE, "root": tmp_path / "set", "model": HOSTILE, "cond": "C",
                     "effort": "medium", "k": 1, "task": ent["id"], "outcome": "correct",
                     "evaluable": True, "rescued": False, "vals": vals,
                     "rel": {p: 0.0 for p in literature.PARAMS},
                     "path": path, "manifest": {}, "pass": {p: True for p in ent["required"]}}]
    data["shown"] = {ent["key"]}
    data["notes"] = [HOSTILE]
    _check(literature.build_html(data), tmp_path)


def test_coverage_page(tmp_path):
    cov = {"k": 3, "effort": HOSTILE, "models": [HOSTILE], "conds": ["A"], "skipped_run_sets": [HOSTILE],
           "tasks": [{"id": HOSTILE, "class": HOSTILE}],
           "cells": [{"task": HOSTILE, "class": HOSTILE, "model": HOSTILE, "cond": "A", "ok": 0, "bad": {HOSTILE: 1}}]}
    _check(coverage.build_html(cov, generated=HOSTILE), tmp_path)


@pytest.mark.parametrize("module", [views, gallery, comparison, dashboard, literature, coverage])
def test_every_page_command_takes_repeatable_runs_and_out(module, capsys):
    with pytest.raises(SystemExit):
        module.main(["--help"])
    text = capsys.readouterr().out
    assert "--runs DIR" in text and "--out FILE" in text and "--task-version" not in text and "--pilot" not in text
