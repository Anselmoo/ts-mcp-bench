"""The dashboard page is a template (templates/dashboard.html.j2); dashboard.py only builds the context."""
from __future__ import annotations

import csv
import pathlib
import re

import jinja2
from markupsafe import Markup

from tsbench.report import dashboard, page

SRC = pathlib.Path(dashboard.__file__)
COLS = ["model", "condition", "effort", "task_id", "k_index", "class", "correct", "has_result", "answer_out_of_scope",
        "dq", "b", "output_tokens", "duration_s", "cost_usd"]
TASKS = {"P-x-01": {"id": "P-x-01", "split": "pilot", "class": "closed_form", "prompt": "Find Dq", "required": ["Dq"],
                    "reference": {"Dq": 1.0}}}


def _data(tmp_path):
    d = tmp_path / "set-a"
    d.mkdir()
    rows = [dict.fromkeys(COLS, "") | {"model": "m", "condition": c, "effort": "medium", "task_id": "P-x-01",
                                       "k_index": "1", "class": "closed_form", "correct": str(c == "C"),
                                       "has_result": "True", "answer_out_of_scope": "False", "dq": "1000",
                                       "output_tokens": "500", "duration_s": "12.5", "cost_usd": "0.01"}
            for c in "ABC"]
    with open(d / "scores.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, COLS)
        w.writeheader()
        w.writerows(rows)
    return dashboard.collect([d], tmp_path / "out" / "r.html", TASKS, score_missing=False)


def _strings(value):
    if isinstance(value, dict):
        for v in value.values():
            yield from _strings(v)
    elif isinstance(value, (list, tuple)):
        for v in value:
            yield from _strings(v)
    elif isinstance(value, str):
        yield value


def test_dashboard_py_writes_no_page_markup():
    text = SRC.read_text(encoding="utf-8")
    assert not re.search(r"<(div|style|table|html|section|span|script|header|tr|td|th|li|ul|p|h[1-6])\b", text)


def test_context_holds_data_and_no_markup(tmp_path):
    ctx = dashboard.context(_data(tmp_path), "Title")
    assert ctx["title"] == "Title"
    texts = [s for s in _strings(ctx) if not isinstance(s, Markup)]
    assert texts and not [s for s in texts if re.search(r"</?[a-z]", s)]


def test_saved_images_are_data_and_escaped_on_the_page(tmp_path):
    data = _data(tmp_path)
    evil = '<script>alert(1)</script>.png'
    data["rows"][0]["_images"] = [{"name": evil, "sha256": "ab" * 32, "sha_ok": False, "match": False,
                                   "uri": "data:image/png;base64,AAAA"}]
    ctx = dashboard.context(data, "T")
    assert ctx["images"] and not [s for s in _strings(ctx) if isinstance(s, Markup)]
    page = dashboard.build_html(data, "T")
    assert "<script>alert" not in page and "&lt;script&gt;alert(1)&lt;/script&gt;.png" in page
    assert "max-width:min(100%,320px)" in page and "does not match a harvested file" in page


def test_page_extends_the_base_template(tmp_path):
    markup = dashboard.build_html(_data(tmp_path), "T")
    assert markup.startswith("<!doctype html>") and page.CSP_META in markup and markup.count("--paper:") == 2
    assert '<meta name="color-scheme" content="light dark">' in markup  # follows the system colour scheme
    assert markup.count('<script id="jfs-lib">') == 1 and markup.count("<style>") == 1
    for section in ("Accuracy by condition", "Task-level comparison", "Output tokens and runtime",
                    "What was asked", "Individual runs", "Provenance", "Manifest facts"):
        assert section in markup


def test_page_leads_with_the_answer_sheet_of_the_full_report(tmp_path):
    """The dashboard and the full report draw the answer once: three tiles with their tools, the paired differences
    with their drawn intervals, and counts that show the runs they count."""
    data = _data(tmp_path)
    markup = dashboard.build_html(data, "T")
    sheet = markup[markup.index('<section id="verdict"'):markup.index('id="by-task"')]
    assert 'class="slip"' in sheet and sheet.count('class="cand ') == 3 and 'class="rg"' in sheet
    for row in dashboard.design(data)["rows"]:
        assert row["tools"] in sheet
    assert 'class="kpi' not in markup and 'class="hero"' not in markup and markup.count('id="verdict"') == 1
    assert 'href="#run-list" class="dr" data-drill="1"' in sheet
    (c,) = [x for x in dashboard.context(data)["verdict"]["contrasts"] if x["label"] == "C \u2212 A"]
    assert c["d"] in sheet and c["ci"] in sheet


def test_the_drill_script_belongs_to_the_dashboard_page():
    """Both pages load dashboard.js, so a count leads to its runs on either; full.js must not bind it a second time."""
    templates = SRC.parent / "templates"
    assert "[data-drill]" in (templates / "dashboard.js").read_text(encoding="utf-8")
    assert "data-drill" not in (templates / "full.js").read_text(encoding="utf-8")


def test_template_escapes_context_values():
    env = page.ENV
    template = env.get_template("dashboard.html.j2")
    assert template is not None
    try:
        template.render(title="t")
    except jinja2.UndefinedError:
        pass  # strict: a missing context name is an error
    else:
        raise AssertionError("dashboard.html.j2 rendered without its context")
