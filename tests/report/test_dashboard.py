"""Tests for the static dashboard (src/tsbench/report/dashboard.py)."""
from __future__ import annotations

import csv
import json
import pathlib
import re

import pytest

from tsbench.report import dashboard as dash
from tsbench.report import page

COLS = ["model", "condition", "effort", "task_id", "k_index", "class", "correct", "has_result", "answer_out_of_scope",
        "dq", "b", "c", "output_tokens", "duration_s", "cost_usd", "is_error", "result_subtype", "unparseable",
        "rel_err_dq", "rel_err_b"]

TASKS = {
    "P-x-01": {"id": "P-x-01", "split": "pilot", "class": "closed_form", "prompt": "Find <b>Dq</b> & B now",
               "required": ["Dq", "B"], "tolerance": {"Dq": 0.02, "B": 0.05}, "reference": {"Dq": 1.0, "B": 2.0},
               "expect_out_of_scope": False},
}


def _row(model="m<1>", cond="A", task="P-x-01", correct=True, **kw):
    r = dict.fromkeys(COLS, "")
    r.update(model=model, condition=cond, effort="medium", task_id=task, k_index="1", correct=str(correct),
             has_result="True", answer_out_of_scope="False", dq="1000", b="700", output_tokens="500",
             duration_s="12.5", cost_usd="0.01", is_error="False", result_subtype="success", unparseable="False",
             rel_err_dq="0.0", rel_err_b="0.0")
    r["class"] = "closed_form"
    r.update(kw)
    return r


def _mk(path, rows, manifest=None, views=()):
    path.mkdir(parents=True, exist_ok=True)
    with open(path / "scores.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, COLS)
        w.writeheader()
        w.writerows(rows)
    if manifest is not None:
        (path / "MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
    for v in views:
        p = path / v
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("<html></html>", encoding="utf-8")
    return path


def _own(page: str) -> str:
    """The page without the inlined libraries (d3 and the Figura bundle contain URLs, `url(#...)`, arcs and pies)."""
    page = re.sub(r'<script id="jfs-lib">.*?</script>', "", page, flags=re.S)
    return re.sub(r'<script id="fig-draw">.*?</script>', "", page, flags=re.S)


def _spec_scripts(page: str) -> list:
    specs = re.findall(r'<script type="application/json" class="spec">(.*?)</script>', page, flags=re.S)
    return [json.loads(m) for m in specs]


def _render(dirs, tmp_path, tasks=TASKS):
    out = tmp_path / "out" / "report.html"
    out.parent.mkdir(exist_ok=True)
    return dash.build_html(dash.collect(dirs, out, tasks, score_missing=False), "T")


MAN = {"git_commit": "abcdef0123456789", "plan_id": "plan-1", "start_time_utc": "2026-10-24T10:00:00+00:00",
       "end_time_utc": "2026-10-24T11:00:00+00:00", "total_cost_usd": 1.5,
       "sandbox": {"method": "builtin", "probe": {"passed": True, "markers": {"NET": [56]}}},
       "flagged_runs": [{"run_id": "r", "flags": ["b_no_tool_use"]}], "aborted_cells": ["cellX"]}


def _resumed(path):
    """A run set whose first session was cut short (done 2 of 4) and continued with --resume (done 2, skipped 2)."""
    first = {**MAN, "start_time_utc": "2026-10-24T10:00:00+00:00", "end_time_utc": "2026-10-24T11:00:00+00:00",
             "counts": {"planned": 4, "done": 2, "skipped": 0, "aborted": 0}, "total_cost_usd": 0.5,
             "flagged_runs": [{"run_id": "r1", "flags": ["b_no_tool_use"]}], "aborted_cells": ["cellX"]}
    second = {**MAN, "start_time_utc": "2026-10-25T08:00:00+00:00", "end_time_utc": "2026-10-25T09:30:00+00:00",
              "counts": {"planned": 4, "done": 2, "skipped": 2, "aborted": 1}, "total_cost_usd": 1.25,
              "flagged_runs": [{"run_id": "r2", "flags": ["c_no_mcp_call"]}], "aborted_cells": ["cellY"]}
    d = _mk(path, [_row()], second)
    (d / "MANIFEST.prev-20261024T110000000000Z.json").write_text(json.dumps(first), encoding="utf-8")
    return d


def test_a_resumed_run_set_reads_the_earlier_sessions_too(tmp_path):
    m = dash.read_manifest(_resumed(tmp_path / "set-r"))
    assert m is not None
    assert m["start_time_utc"] == "2026-10-24T10:00:00+00:00" and m["end_time_utc"] == "2026-10-25T09:30:00+00:00"
    assert m["counts"] == {"planned": 4, "done": 4, "skipped": 0, "aborted": 1}  # the skipped runs are the done ones
    assert m["total_cost_usd"] == 1.25  # the resumed manifest already holds the cost of the earlier sessions
    assert [f["run_id"] for f in m["flagged_runs"]] == ["r1", "r2"] and m["aborted_cells"] == ["cellX", "cellY"]
    assert m["sessions"] == 2


def test_a_run_set_without_a_prev_manifest_has_the_plain_manifest(tmp_path):
    d = _mk(tmp_path / "set-p", [_row()], MAN)
    assert dash.read_manifest(d) == MAN
    assert dash.read_manifest(_mk(tmp_path / "set-q", [_row()])) is None


def test_every_set_entry_carries_its_own_folder(tmp_path):
    d = _mk(tmp_path / "set-a", [_row()], MAN)
    data = dash.collect([tmp_path / "gone", d], tmp_path / "out" / "r.html", TASKS, score_missing=False)
    assert [(s["name"], s["path"]) for s in data["sets"]] == [("set-a", d)]


def test_the_dashboard_counts_the_flagged_runs_of_every_session(tmp_path):
    data = dash.collect([_resumed(tmp_path / "set-r")], tmp_path / "out" / "r.html", TASKS, score_missing=False)
    (row,) = dash._manifests(data)
    assert row["flagged"] == 2 and "b_no_tool_use: 1" in row["flags"] and "c_no_mcp_call: 1" in row["flags"]
    assert "cellX" in row["aborted"] and "cellY" in row["aborted"]


def _scored_fake_set(folder):
    from tsbench.run import runner
    from tsbench.score.score import score_dir
    runner.main(["--split", "pilot", "--models", "claude-haiku-5-5", "--conditions", "A,B,C", "--effort", "medium",
                 "--k", "1", "--budget-usd", "10", "--out", str(folder), "--dry-run", "--limit", "2"])
    score_dir(folder)
    return folder


def _drop_score_rows(folder, n):
    rows = list(csv.DictReader((folder / "scores.csv").open(encoding="utf-8", newline="")))
    with (folder / "scores.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, list(rows[0]))
        w.writeheader()
        w.writerows(rows[:-n])


def test_transcripts_without_a_scores_row_are_named_in_a_note(tmp_path):
    """A scores.csv written before the last runs finished leaves those runs out of every number: say so."""
    folder = _scored_fake_set(tmp_path / "set")
    out = tmp_path / "out" / "report.html"
    out.parent.mkdir()
    tasks = dash.load_pilot_tasks()
    assert dash.collect([folder], out, tasks, score_missing=False)["notes"] == []      # complete scores.csv: no note
    _drop_score_rows(folder, 4)
    data = dash.collect([folder], out, tasks, score_missing=False)
    assert len(data["rows"]) == 2 and data["sets"][0]["n"] == 2
    assert data["notes"] == ["set: 4 transcripts have no scores row (run tsbench score)"]
    _drop_score_rows(folder, 1)
    assert dash.collect([folder], out, tasks, score_missing=False)["notes"] == [
        "set: 5 transcripts have no scores row (run tsbench score)"]
    # the count travels with the note, so the exclusions table says 5 runs, not one note
    got = dash.collect([folder], out, tasks, score_missing=False)
    assert got["note_counts"] == {got["notes"][0]: 5}


def test_a_run_that_was_replaced_after_scoring_is_named_in_a_note(tmp_path):
    """The manifest holds the sha256 of the transcript of a re-run; scores.csv holds the one it was made from."""
    folder = _scored_fake_set(tmp_path / "set")
    out = tmp_path / "out" / "report.html"
    out.parent.mkdir()
    tasks = dash.load_pilot_tasks()
    manifest = json.loads((folder / "MANIFEST.json").read_text(encoding="utf-8"))
    rid = sorted(manifest["transcripts"])[0]
    manifest["transcripts"][rid] = "0" * 64                                  # the runner re-ran it after the scoring
    (folder / "MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
    notes = dash.collect([folder], out, tasks, score_missing=False)["notes"]
    assert notes == ["set: 1 transcript differs from the scores row (run tsbench score)"]


def test_escaping(tmp_path):
    d = _mk(tmp_path / "set-a", [_row(model="<script>alert(1)</script>")], {**MAN, "plan_id": "<i>p</i>"})
    page = _render([d], tmp_path)
    assert "<script>alert(1)</script>" not in page and "<script>alert(1)" not in _own(page)
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page
    assert "<b>Dq</b>" not in page and "&lt;b&gt;Dq&lt;/b&gt;" in page
    assert "<i>p</i>" not in page


def test_merge_two_dirs(tmp_path):
    a = _mk(tmp_path / "set-a", [_row(model="alpha"), _row(model="alpha", cond="B", correct=False)], MAN)
    b = _mk(tmp_path / "set-b", [_row(model="alpha", cond="B")], MAN)
    data = dash.collect([a, b], tmp_path / "r.html", TASKS, score_missing=False)
    assert len(data["rows"]) == 3
    assert {r["_cond"] for r in data["rows"]} == {"A", "B"} and {r["_set"] for r in data["rows"]} == {"set-a", "set-b"}
    page = dash.build_html(data)
    assert '">set-a</code>' in page and '">set-b</code>' in page and "fixed" not in _own(page)
    assert "$3.00" in page  # two manifests of 1.5


def test_run_sets_found_below_one_folder_with_titles(tmp_path, monkeypatch):
    """--runs takes a folder holding run sets; each is grouped by its name, its run_set.json title is shown escaped."""
    root = tmp_path / "results"
    _mk(root / "set-a", [_row(model="alpha")], MAN)
    _mk(root / "deep" / "set-b", [_row(model="beta", cond="C")], MAN)
    (root / "set-a" / "run_set.json").write_text(json.dumps({"title": "Alpha <b>run</b>"}), encoding="utf-8")
    monkeypatch.setattr(dash, "load_pilot_tasks", lambda: TASKS)
    out = tmp_path / "site" / "dash.html"
    assert dash.main(["--runs", str(root), "--out", str(out)]) == 0
    markup = out.read_text(encoding="utf-8")
    assert "Alpha &lt;b&gt;run&lt;/b&gt;" in markup and "<b>run</b>" not in markup
    assert "<code>deep</code>" in markup and '">set-b</code>' in markup  # family deep, set set-b
    assert page.CSP in markup and "file:" not in markup


def test_missing_optional_files(tmp_path):
    d = _mk(tmp_path / "run9", [_row()])  # no manifest, plan, metrics, views
    page = _render([d], tmp_path)
    assert "no MANIFEST.json" in page and "unknown" in page
    empty = tmp_path / "empty"
    empty.mkdir()
    page2 = _render([empty], tmp_path)  # no scores at all
    assert "no scores" in page2


def test_no_network_references(tmp_path):
    d = _mk(tmp_path / "set-a", [_row()], MAN,
            views=["views/m<1>/A/medium/P-x-01-k1.html"])
    page = _own(_render([d], tmp_path))
    links = re.findall(r'(?:src|href)="([^"]*)"', page)
    assert links, "expected the relative view link"
    assert all(not re.match(r"(?i)(https?:)?//", u) for u in links)
    assert not re.search(r"<(?:link|img|iframe)\b|@import|url\(", page)
    assert "../set-a/views/" in page.replace("%3C", "<") or "set-a/views/" in page


def test_confirmatory_text_never_rendered(tmp_path):
    secret = "CONFIRMATORY-SECRET-PROMPT"
    d = _mk(tmp_path / "set-a", [_row(), _row(task="C-closed_form-01")], MAN)
    page_tasks = dict(TASKS)  # pilot split only, as load_pilot_tasks returns
    page = _render([d], tmp_path, page_tasks)
    assert secret not in page
    # even if a confirmatory record leaked into the mapping, its split is not pilot and it is not looked up
    leaked = {**TASKS, "C-closed_form-01": {"id": "C-closed_form-01", "split": "confirmatory", "prompt": secret}}
    kept = {k: v for k, v in leaked.items() if v["split"] == "pilot"}
    assert secret not in _render([d], tmp_path, kept)
    assert "C-closed_form-01" in page  # the row itself is listed by id


def test_load_pilot_tasks_filters_split(monkeypatch):
    import tsbench.tasks as T
    seen = []
    monkeypatch.setattr(T, "load", lambda split: seen.append(split) or [{"id": "a", "split": "pilot"},
                                                                       {"id": "b", "split": "confirmatory"}])
    assert set(dash.load_pilot_tasks()) == {"a"} and seen == ["pilot"]


def test_cli_default_out(tmp_path, monkeypatch):
    d = _mk(tmp_path / "set-a", [_row()], MAN)
    monkeypatch.setattr(dash, "load_pilot_tasks", lambda: TASKS)
    assert dash.main(["--runs", str(d)]) == 0
    assert (d / "report.html").read_text(encoding="utf-8").startswith("<!doctype html>")


# ---------------------------------------------------------------- verdict
def test_contrasts_are_paired_differences_with_bootstrap_intervals(tmp_path):
    """No verdict words: a contrast is the mean paired difference in per-task share correct, its 95 % percentile
    bootstrap interval (stats.analysis.bootstrap_ci) and the tasks correct under one condition only."""
    import numpy as np

    from tsbench.stats import analysis
    tasks = ["P-a-01", "P-b-01", "P-c-01", "P-d-01"]
    ok = {"A": [0, 0, 1, 0], "B": [1, 0, 1, 0], "C": [1, 1, 1, 0]}
    rows = [_row(model="m1", cond=k, task=t, correct=bool(v))
            for k, vs in ok.items() for t, v in zip(tasks, vs, strict=True)]
    data = dash.collect([_mk(tmp_path / "set-a", rows, MAN)], tmp_path / "r.html", TASKS, score_missing=False)
    con = dash.context(data)["verdict"]["contrasts"]
    assert [x["label"] for x in con] == ["C − A", "C − B", "B − A"]
    lo, hi = analysis.bootstrap_ci(np.array(ok["A"], float), np.array(ok["C"], float))
    ca = con[0]
    assert (ca["d"], ca["n"], ca["only_x"], ca["only_y"]) == ("+50 pp", 4, 2, 0)
    assert ca["ci"] == f"{page.signed(100 * lo)} to {page.signed(100 * hi)}"
    assert (con[2]["d"], con[2]["only_x"], con[2]["only_y"]) == ("+25 pp", 1, 0)
    assert page.signed(-2.4) == "\u22122" and page.signed(0.3) == "0" and page.signed(12) == "+12"
    markup = dash.build_html(data)
    assert '<table class="contrasts diffs">' in markup
    assert "TS-MCP better" not in markup and "No clear difference" not in markup


def test_contrasts_carry_the_numbers_to_draw_and_the_tasks_they_count(tmp_path):
    """The range of a contrast is drawn from the same values as its text; the tasks correct under one condition only
    are named, so the count leads to its runs (the lists have the length of `only_x` and `only_y`)."""
    tasks = ["P-a-01", "P-b-01", "P-c-01", "P-d-01"]
    ok = {"A": [0, 0, 1, 0], "B": [1, 0, 1, 0], "C": [1, 1, 1, 0]}
    rows = [_row(model="m1", cond=k, task=t, correct=bool(v))
            for k, vs in ok.items() for t, v in zip(tasks, vs, strict=True)]
    data = dash.collect([_mk(tmp_path / "set-a", rows, MAN)], tmp_path / "r.html", TASKS, score_missing=False)
    con = dash.context(data)["verdict"]["contrasts"]
    ca, cb, ba = con
    assert ca["pp"] == 50.0 and ca["lo"] <= ca["pp"] <= ca["hi"] and ca["tasks"] == tasks
    assert (ca["x_only"], ca["y_only"]) == (["P-a-01", "P-b-01"], [])
    assert (ba["x_only"], ba["y_only"]) == (["P-a-01"], []) and cb["x_only"] == ["P-b-01"]
    for x in con:
        assert len(x["x_only"]) == x["only_x"] and len(x["y_only"]) == x["only_y"]
        assert page.signed(x["pp"]) + " pp" == x["d"]


def test_cell_counts_sum_to_n():
    rows = [_row(correct=True), _row(correct=False), _row(correct=False, result_subtype="error_max_turns"),
            _row(correct=False)]
    for r in rows:
        r["_category"] = "correct" if r["correct"] == "True" else "wrong"
        r["_na"] = ""
    rows[2]["_category"] = "max_turns"
    rows[3]["_na"] = "na429"
    c = dash._cell_counts(rows, 6)
    assert (c["correct"], c["wrong"], c["harness"], c["na429"], c["none"], c["n"]) == (1, 1, 1, 1, 2, 6)
    assert c["correct"] + c["wrong"] + c["harness"] + c["na429"] + c["none"] == c["n"]
    assert c["n_eval"] == 3  # 429 runs are outside the rates


def test_efficiency_text_has_the_one_format_of_every_page():
    """The same fact in the same words on every page: a relative change in percent (page.change_text)."""
    t = dash.efficiency_text({"A": (400, 10), "B": (1000, 30), "C": (500, 10)})
    assert t == ("TS-MCP against code: 50 % fewer output tokens and 67 % less time; against no tools: 25 % more "
                 "output tokens and about as much time")
    assert "×" not in t
    more = dash.efficiency_text({"B": (500, 10), "C": (1000, 25)})
    assert more == "TS-MCP against code: 100 % more output tokens and 150 % more time"
    assert dash.efficiency_text({"B": (500, 10), "C": None}) is None

def test_hero_gives_each_condition_its_share_with_a_task_resampled_interval(tmp_path):
    """The page opens with the answer: A, B and C as large numbers. The k runs of a task are not independent, so the
    interval resamples tasks (core.intervals.cluster_bootstrap), and the sentence is descriptive, not a test."""
    from tsbench.core import intervals
    rows = [_row(model=m, cond="C", task=t, correct=(t == "P-x-01"))
            for m in ("m1", "m2") for t in ("P-x-01", "P-y-01")]
    rows += [_row(model="m1", cond="A", correct=False), _row(model="m1", cond="B", correct=False)]
    data = dash.collect([_mk(tmp_path / "set-a", rows, MAN)], tmp_path / "r.html", TASKS, score_missing=False)
    verdict = dash.context(data)["verdict"]
    assert [h["cond"] for h in verdict["hero"]] == ["A", "B", "C"]
    c = verdict["hero"][2]
    lo, hi = intervals.cluster_bootstrap([2, 0], [2, 2])
    assert (c["pct"], c["text"]) == ("50", "2 of 4 correct over 2 tasks")
    assert c["ci"] == f"95 % interval {100 * lo:.0f}–{100 * hi:.0f} %, tasks resampled"
    assert (c["lo"], c["hi"]) == (round(100 * lo, 1), round(100 * hi, 1))
    assert [(x["model"], x["label"]) for x in verdict["contrasts"]] == [("m1", "C − A"), ("m1", "C − B"),
                                                                         ("m1", "B − A")]
    assert "headline" not in verdict
    page_ = dash.build_html(data)
    assert page_.index('id="verdict"') < page_.index('class="facts"') < page_.index("Run sets")


def test_model_cards_share_scales_and_state_no_verdict(tmp_path):
    """Small multiples: one card per model, panels stacked, the same run axis everywhere; the differences stand once,
    in the table of the first section, not as a verdict on the card."""
    rows = [_row(model="m1", cond=c, correct=(c == "C")) for c in "ABC"] + [_row(model="m2", cond="A")] * 3
    data = dash.collect([_mk(tmp_path / "set-a", rows, MAN)], tmp_path / "r.html", TASKS, score_missing=False)
    cards = dash.context(data)["verdict"]["cards"]
    specs = [c["rate"]["spec"] for c in cards]
    assert all(sp["stack"] for sp in specs) and {sp["nmax"] for sp in specs} == {3}
    assert "verdict" not in cards[0]
    markup = dash.build_html(data)
    assert markup.count('class="mcard"') == 2 and "mverdict" not in markup
    assert "efficiency" not in cards[0] and '<p class="eff">' not in markup  # efficiency lives in its own section


def test_one_model_says_its_answer_once_and_efficiency_sits_with_its_charts(tmp_path):
    """One model: the differences are said once, in the table; no per-model card repeats them."""
    rows = [_row(model="m1", cond=c) for c in "ABC"]
    data = dash.collect([_mk(tmp_path / "set-a", rows, MAN)], tmp_path / "r.html", TASKS, score_missing=False)
    ctx = dash.context(data)
    assert [x["d"] for x in ctx["verdict"]["contrasts"]] == ["0 pp", "0 pp", "0 pp"]
    assert ctx["verdict"]["cards"] == []
    assert ctx["charts"]["plain"] == [{"model": "m1", "text": "TS-MCP against code: about as many output tokens and "
                                                              "about as much time; against no tools: about as many "
                                                              "output tokens and about as much time"}]
    markup = dash.build_html(data)
    assert markup.count('<table class="contrasts diffs">') == 1 and 'class="mcard"' not in markup
    assert markup.index('id="by-task"') < markup.index('id="efficiency"') < markup.index("about as many output")
    assert '<details class="asked"><summary>What was asked' in markup

def test_a_figure_leads_to_its_runs(tmp_path):
    """The run table opens from the figure: a bar segment (or a status tag of the text version) shows exactly the runs
    it counts."""
    rows = [_row(model="m1", cond="A", correct=False), _row(model="m1", cond="C"), _row(model="m2", cond="C")]
    data = dash.collect([_mk(tmp_path / "set-a", rows, MAN)], tmp_path / "r.html", TASKS, score_missing=False)
    card = dash.context(data)["verdict"]["cards"][0]
    assert card["rate"]["spec"]["model"] == "m1" and [it["cond"] for it in card["rate"]["items"]] == ["A", "C"]
    markup = dash.build_html(data)
    assert '<tr class="o-wrong" data-model="m1" data-cond="A">' in markup
    assert '<article class="mcard" data-model="m1">' in markup and '<li data-cond="A">' in markup
    assert '<div id="drill" class="drill" hidden role="status" tabindex="-1">' in markup
    assert 'addEventListener("tsb:segment"' in markup
    assert 'new CustomEvent("tsb:segment"' in page.RUNTIME_JS


def test_first_screen_says_what_was_measured_and_how_to_dig(tmp_path):
    """First screen: under the title one line of context; the hero intervals open from their estimate as the figures
    do; the cards say that a segment leads to its runs."""
    rows = [_row(model="m1", cond="A", correct=False), _row(model="m1", cond="C"), _row(model="m2", cond="C")]
    data = dash.collect([_mk(tmp_path / "set-a", rows, MAN)], tmp_path / "r.html", TASKS, score_missing=False)
    stamp = "pilot split · 1 task · k = 1 · 3 runs · 2 models · 1 run set · 2026-10-24 to 2026-10-24"
    assert dash.context(data)["stamp"] == stamp
    markup = dash.build_html(data)
    assert markup.index(f'<p class="stamp">{stamp}') < markup.index('id="verdict"')
    assert 'transform-origin:' in markup and "@keyframes ci-open" in markup
    assert "Click a bar segment to see its runs" in markup


def test_each_card_counts_the_tasks_where_c_is_higher_than_code(tmp_path):
    """The unit of the study is the task: per model, on the tasks run under both B and C, is C's share correct higher,
    the same or lower than B's? The counts are text; one mark per task carries the same in shape."""
    rows = ([_row(model="m1", cond="C", task="P-x-01"), _row(model="m1", cond="B", task="P-x-01", correct=False)]
            + [_row(model="m1", cond="C", task="P-y-01"), _row(model="m1", cond="B", task="P-y-01")]
            + [_row(model="m1", cond="C", task="P-z-01", correct=False), _row(model="m1", cond="B", task="P-z-01")]
            + [_row(model="m1", cond="C", task="P-only-c"), _row(model="m2", cond="C")])
    data = dash.collect([_mk(tmp_path / "set-a", rows, MAN)], tmp_path / "r.html", TASKS, score_missing=False)
    led = dash.context(data)["verdict"]["cards"][0]["ledger"]
    assert (led["higher"], led["same"], led["lower"], led["n"]) == (1, 1, 1, 3)
    assert [(t["id"], t["mark"]) for t in led["tasks"]] == [("P-x-01", "higher"), ("P-y-01", "same"),
                                                            ("P-z-01", "lower")]
    assert led["tasks"][0]["title"] == "P-x-01: TS-MCP 1/1 correct, code 0/1"
    pairs = dash.context(data)["verdict"]["cards"][0]["pairs"]
    assert [(s[0], s[1]) for s in pairs["spec"]["rows"][0]["seg"]] == [("higher", 1), ("same", 1), ("lower", 1)]
    markup = dash.build_html(data)
    assert ("C against B (3 tasks run under both): share correct higher on 1 task, the same on 1, lower on 1."
            in markup)
    assert 'data-kind="pairs"' in markup and "+ + +" not in markup


def test_tiles_have_short_values_and_a_caption(tmp_path):
    rows = [_row(model="alpha"), _row(model="beta", cond="C")]
    data = dash.collect([_mk(tmp_path / "set-a", rows, MAN)], tmp_path / "r.html", TASKS, score_missing=False)
    tiles = {t["label"]: t for t in dash.context(data)["facts"]}
    assert (tiles["Models"]["value"], tiles["Models"]["caption"]) == ("2", "alpha, beta")
    assert set(tiles) == {"Models", "Conditions", "Runs"}  # period and cost are provenance, not the answer
    assert all(len(t["value"]) <= 12 for t in tiles.values())
    prov = dash.context(data)["provenance"]
    assert (prov["period"], prov["cost"]) == ("2026-10-24 to 2026-10-24", "$1.50")


def test_run_sets_grouped_by_family_and_collapsed(tmp_path):
    sets = {"fam-x/one": "Calibration run, m, condition A", "fam-x/two": "Calibration run, m, condition B",
            "fam-y/three": "Gap fill, m, condition C"}
    for name, title in sets.items():
        d = _mk(tmp_path / "res" / name, [_row()], MAN)
        (d / "run_set.json").write_text(json.dumps({"title": title}), encoding="utf-8")
    data = dash.collect(dash.run_sets_in([tmp_path / "res"]), tmp_path / "r.html", TASKS, score_missing=False)
    fams = dash.context(data)["run_sets"]
    assert [(f["family"], f["about"], [x["name"] for x in f["sets"]]) for f in fams] == [
        ("fam-x", "Calibration run", ["one", "two"]), ("fam-y", "Gap fill", ["three"])]
    assert fams[0]["sets"][0]["title"] == "Calibration run, m, condition A"
    markup = dash.build_html(data)
    assert '<details class="sets">' in markup and "3 run sets in 2 families" in markup


def test_provenance_comes_last_collapsed_with_short_hashes(tmp_path):
    page_ = _render([_mk(tmp_path / "set-a", [_row()], {**MAN, "plan_id": "f" * 64})], tmp_path)
    prov = page_[page_.index('id="provenance"'):]
    assert '<details class="prov">' in prov and "Manifest facts" in prov
    assert '<code title="abcdef0123456789">abcdef01</code>' in prov
    assert f'<code title="{"f" * 64}">ffffffff</code>' in prov
    head = page_[:page_.index('id="provenance"')]
    assert "abcdef01" not in head and "f" * 64 not in head.replace(f'title="{"f" * 64}"', "")


def test_verdict_section_first_and_single_model(tmp_path):
    rows = [_row(model="solo", cond=c, correct=(c == "C")) for c in "ABC"]
    page = _render([_mk(tmp_path / "set-a", rows, MAN)], tmp_path)
    assert 'class="mcard"' not in page and _own(page).count('<table class="contrasts diffs">') == 1
    assert "never in a rate" in page
    order = ['id="verdict"', 'id="by-task"', 'id="efficiency"', "What was asked", "Individual runs", 'id="provenance"']
    assert [page.index(s) for s in order] == sorted(page.index(s) for s in order)
    assert _own(page).count('data-kind="rate"') == 0 and _own(page).count('data-kind="pairs"') == 1
    assert not re.search(r"[\U0001F300-\U0001FAFF]", page)

# ---------------------------------------------------------------- Figura design
def test_figura_design_inlined_and_no_pie(tmp_path):
    rows = [_row(model="solo", cond=c, correct=(c == "C")) for c in "ABC"]
    markup = _render([_mk(tmp_path / "set-a", rows, MAN)], tmp_path)
    assert "d3js.org v7.9.0" in markup and "window.JFS" in markup            # d3 and the Figura bundle are inlined
    assert 'J.useTheme(darkPage()?"neutral-dark":"neutral")' in markup and "#0039a6" in markup.lower()  # series-1
    own = _own(markup)
    assert "donut" not in own.lower() and "d3.pie" not in own and "d3.arc" not in own
    assert "stroke-dasharray" not in own and "rotate(-90" not in own  # no circle-slice donuts
    assert not re.search(r"<script[^>]*\ssrc=", markup) and "@import" not in markup and "<link" not in own
    assert not re.search(r"https?://", own)                              # still no external resource
    specs = _spec_scripts(markup)
    assert [x for x in specs if x["rows"] and x["rows"][0].get("seg")]   # stacked segments, task by task


def test_model_card_interval_is_the_task_bootstrap_for_k_3(tmp_path):
    """The card's dot carries the interval of the task-clustered bootstrap, like the hero tile of the same cell."""
    from tsbench.core import intervals
    tasks = {f"P-x-0{i}": dict(TASKS["P-x-01"], id=f"P-x-0{i}") for i in range(1, 7)}
    rows = [_row(model=m, cond="C", task=t, correct=(i < 3), k_index=str(k))
            for m in ("m1", "m2") for i, t in enumerate(tasks) for k in (1, 2, 3)]
    data = dash.collect([_mk(tmp_path / "set-a", rows, MAN)], tmp_path / "r.html", tasks, score_missing=False)
    card = dash.context(data)["verdict"]["cards"][0]
    row = card["rate"]["spec"]["rows"][0]
    lo, hi = intervals.cluster_bootstrap([3, 3, 3, 0, 0, 0], [3] * 6)
    assert row["n_eval"] == 18 and row["lo"] == pytest.approx(100 * lo) and row["hi"] == pytest.approx(100 * hi)
    w_lo, w_hi = (100 * v for v in intervals.wilson(9, 18))
    assert row["hi"] - row["lo"] > w_hi - w_lo
    assert "Wilson" not in dash.build_html(data)


def test_model_card_interval_does_not_depend_on_the_row_order(tmp_path):
    """The bootstrap draws by position: rows out of task order give the interval of the tasks sorted by id."""
    from tsbench.core import intervals
    ids = [f"P-x-{i:02d}" for i in range(1, 13)]
    tasks = {t: dict(TASKS["P-x-01"], id=t) for t in ids}
    hits = dict(zip(ids, [3, 0, 2, 1, 3, 0, 2, 3, 1, 0, 3, 2], strict=True))
    order = ["P-x-08", "P-x-12", "P-x-04", "P-x-11", "P-x-09", "P-x-05",
             "P-x-10", "P-x-02", "P-x-01", "P-x-07", "P-x-03", "P-x-06"]
    rows = [_row(model=m, cond="C", task=t, correct=(k < hits[t]), k_index=str(k))
            for m in ("m1", "m2") for t in order for k in range(3)]
    data = dash.collect([_mk(tmp_path / "set-a", rows, MAN)], tmp_path / "r.html", tasks, score_missing=False)
    row = dash.context(data)["verdict"]["cards"][0]["rate"]["spec"]["rows"][0]
    lo, hi = intervals.cluster_bootstrap([hits[t] for t in sorted(hits)], [3] * 12)
    first = intervals.cluster_bootstrap([hits[t] for t in order], [3] * 12)
    assert (lo, hi) != first                                              # the order would matter here
    assert row["lo"] == pytest.approx(100 * lo) and row["hi"] == pytest.approx(100 * hi)


def test_not_evaluable_runs_are_their_own_category_and_not_in_rates(tmp_path):
    cols = [*COLS, "evaluable", "not_evaluable_reason"]
    rows = [_row(cond="C", correct=True) for _ in range(2)] \
        + [_row(cond="C", correct=False, evaluable="False", not_evaluable_reason="api_error") for _ in range(3)] \
        + [_row(cond="C", correct=False, evaluable="False", not_evaluable_reason="rate_limited")]
    for r in rows:
        r.setdefault("evaluable", "True")
        r.setdefault("not_evaluable_reason", "")
    d = tmp_path / "set-a"
    d.mkdir()
    with open(d / "scores.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, cols)
        w.writeheader()
        w.writerows(rows)
    page = _render([d], tmp_path)
    own = _own(page)
    assert "4 not evaluable: rate limit or API error" in own and "Not evaluable (not in any rate)" in own
    assert "2 of 2 correct over 1 task" in own                           # 4 excluded runs are not in the denominator


def test_scores_without_an_evaluable_column_count_as_evaluable(tmp_path):
    page = _render([_mk(tmp_path / "set-a", [_row(cond="C"), _row(cond="C", correct=False)], MAN)], tmp_path)
    assert "1 of 2 correct over 1 task" in _own(page)


def test_status_has_icon_and_text(tmp_path):
    page = _render([_mk(tmp_path / "set-a", [_row(), _row(model="m2")], MAN)], tmp_path)
    own = _own(page)
    for text in ("correct", "wrong", "harness limit", "not evaluable: rate limit or API error", "not run"):
        legend = r'<span class="lg"[^>]*><i class="sw sw-\w+"></i><svg class="ic[^>]*>.*?</svg>'
        assert re.search(legend + re.escape(text), own)


def _section(page: str, sid: str) -> str:
    m = re.search(rf'<section id="{sid}">.*?</section>', page, flags=re.S)
    assert m is not None, sid
    return m.group(0)


def test_efficiency_has_one_legend_with_shapes(tmp_path):
    """One legend for both efficiency charts, with the marker shape and colour of each condition; the charts draw
    none."""
    page = _render([_mk(tmp_path / "set-a", [_row(cond=c) for c in "ABC"], MAN)], tmp_path)
    eff = _section(page, "efficiency")
    assert eff.count('class="legend') == 1
    assert eff.index('class="legend') < eff.index('data-kind="dots"')
    mark = (r'<span class="lg"><svg class="mk" viewBox="0 0 10 10"[^>]*>'
            r'<(\w+)[^>]*fill="(#[0-9a-f]{6})" style="fill:(.*?)"')
    items = re.findall(mark, eff)
    assert [shape for shape, _, _ in items] == ["circle", "rect", "path"] and len({c for _, c, _ in items}) == 3
    assert [v for _, _, v in items] == ["var(--s1)", "var(--s2)", "var(--s3)"]  # the dark scheme recolours them
    assert "A · no tools" in eff and "C · TS-MCP" in eff
    dots = [s for s in _spec_scripts(page) if "conds" in s]
    assert len(dots) == 2 and all(s["legend"] is False for s in dots)
    assert "if(s.legend!==false)legend(ax," in page.replace(" ", "")


def test_efficiency_charts_sit_side_by_side_at_full_width(tmp_path):
    """The two efficiency charts share one grid and each plot fills its column, not a third of the card."""
    page = _render([_mk(tmp_path / "set-a", [_row(cond=c) for c in "ABC"], MAN)], tmp_path)
    eff = _section(page, "efficiency")
    grid = re.search(r'<div class="effgrid">(.*?)</div>\s*(?:<ul|</section>)', eff, flags=re.S)
    assert grid and grid.group(1).count('data-kind="dots"') == 2
    assert ".effgrid{display:grid" in page and ".effgrid figure .plot svg{width:100%" in page
    dots = [s for s in _spec_scripts(page) if "conds" in s]
    assert all(s["right"] == 14 for s in dots)                        # the value labels sit inside the axis already
    assert "T=s.legend===false?8:20" in page and "R=s.right!=null?s.right:40" in page


def test_save_svg_looks_the_same_everywhere(tmp_path):
    """Every "Save SVG" of the dashboard is the one quiet control of page.css; the page restyles it nowhere."""
    markup = _render([_mk(tmp_path / "set-a", [_row(cond=c) for c in "ABC"], MAN)], tmp_path)
    page_css = (pathlib.Path(page.__file__).parent / "templates" / "page.css").read_text(encoding="utf-8")
    rules = re.findall(r"[^{}]*\.dl\b[^{}]*\{", _own(markup))
    assert rules and sorted(rules) == sorted(re.findall(r"[^{}]*\.dl\b[^{}]*\{", page_css))


def _flag_rows():
    cols = [*COLS, "n_tool_uses", "n_mcp_calls"]
    rows = [_row(cond="A", correct=False, task=f"P-{i}") for i in range(3)]
    rows += [_row(cond="B", correct=(i == 0), task=f"P-{i}", n_tool_uses="0", n_mcp_calls="0") for i in range(2)]
    rows += [_row(cond="B", correct=False, task="P-2", n_tool_uses="3", n_mcp_calls="0")]
    rows += [_row(cond="C", correct=True, task=f"P-{i}", n_tool_uses="2", n_mcp_calls="2") for i in range(3)]
    return cols, rows


def test_tool_use_sits_next_to_the_rate_as_a_model_finding(tmp_path):
    """Whether a B run runs code is the model's choice (the prompt is the same in every condition): the B tile states
    the tool use beside its share correct, split by it, in neutral words, not as a warning; the run table and the
    task tables mark the runs without tool use."""
    cols, rows = _flag_rows()
    d = tmp_path / "set-a"
    d.mkdir()
    with open(d / "scores.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, cols)
        w.writeheader()
        w.writerows(rows)
    data = dash.collect([d], tmp_path / "r.html", TASKS, score_missing=False)
    hero = {h["cond"]: h for h in dash.context(data)["verdict"]["hero"]}
    assert hero["A"]["flags"] == [] and hero["C"]["flags"] == []
    (f,) = hero["B"]["flags"]
    assert (f["flag"], f["text"]) == ("b_no_tool_use", "Tool use: 1 of 3 runs ran code")
    assert f["detail"] == "correct with code 0 of 1, without 1 of 2" and "consequence" not in f
    markup = dash.build_html(data)
    b_tile = markup[markup.index('<div class="cand c-B">'):markup.index('<div class="cand c-C">')]
    assert '<p class="tooluse" data-flag="b_no_tool_use">' in b_tile and "1 of 3 runs ran code" in b_tile
    assert "warning" not in b_tile and "as planned" not in markup
    assert markup.count('<td class="fl">ran no code</td>') == 2
    assert markup.count(" flagged\"") == 2


def test_plurals_and_default_title(tmp_path):
    data = dash.collect([_mk(tmp_path / "set-a", [_row(model="m1")], MAN)], tmp_path / "r.html", TASKS,
                        score_missing=False)
    ctx = dash.context(data)
    assert ctx["run_sets_head"] == "1 run set in 1 family" and ctx["title"] == "TS-MCP benchmark: m1"
    assert page.plural(3, "family", "families") == "3 families" and page.plural(1, "task") == "1 task"


def test_task_tables_group_tasks_by_class_with_a_count_row(tmp_path):
    rows = [_row(cond=c, correct=(c == "C")) for c in "ABC"]
    data = dash.collect([_mk(tmp_path / "set-a", rows, MAN)], tmp_path / "r.html", TASKS, score_missing=False)
    grid = dash.context(data)["grid"]
    (cls,) = grid["classes"]
    assert (cls["cls"], cls["n"], cls["total"]) == ("closed_form", 1, ["0/1", "0/1", "1/1"])
    assert [c["state"] for c in cls["rows"][0]["cells"]] == ["wrong", "wrong", "correct"]


def test_hero_percentages_round_a_half_up(tmp_path, monkeypatch):
    rows = [_row(model="m1", cond="A", correct=True)]
    data = dash.collect([_mk(tmp_path / "set-a", rows, MAN)], tmp_path / "r.html", TASKS, score_missing=False)
    monkeypatch.setattr(dash, "share", lambda rs: {"k": 1, "n": 40, "tasks": 40, "p": 0.025, "lo": 0.025, "hi": 0.035})
    a = dash.context(data)["verdict"]["hero"][0]
    assert a["pct"] == "3" and a["ci"] == "95 % interval 3–4 %, tasks resampled"


def test_dashboard_numbers_round_a_half_up():
    """_fmt labels the median charts; a half rounds up (3466.5 gives 3,467, 3325.5 gives 3,326)."""
    assert [dash._fmt(x) for x in (3466.5, 3325.5, 26.5, 27.5, 2.5, 3.5)] == [
        "3,467", "3,326", "27", "28", "3", "4"]
    assert dash._fmt(0.125, 2) == "0.13" and dash._fmt(1234.5, 0) == "1,235" and dash._fmt(None) == ""
