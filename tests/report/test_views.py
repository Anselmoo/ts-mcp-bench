"""Tests for the per-run HTML views and the index. Dry-run transcripts and hand-made ones only; tmp_path output."""
from __future__ import annotations

import json
import ntpath
import pathlib
import re
import types

from tsbench import report
from tsbench.report import __main__ as report_cli
from tsbench.report import page, views
from tsbench.run import runner
from tsbench.score import score
from tsbench.tasks import load

HAIKU = "claude-haiku-5-5"
EVIL = "<script>alert('x')</script><img src=x onerror=alert(1)>"


def dry_runs(tmp_path, limit=2):
    out = tmp_path / "runs"
    runner.main(["--split", "pilot", "--models", HAIKU, "--conditions", "A,B,C", "--effort", "medium", "--k", "1",
                 "--budget-usd", "10", "--out", str(out), "--dry-run", "--limit", str(limit)])
    return out


def hand_made(tmp_path, *, tool_result=EVIL, answer=EVIL, flags=("x",)):
    """A runs directory with one transcript whose every text field is hostile."""
    task = load("pilot")[0]
    d = tmp_path / "hand" / HAIKU / "B" / "medium"
    d.mkdir(parents=True)
    events = [
        {"type": "system", "subtype": "init", "tools": ["Bash"], "mcp_servers": [], "model": HAIKU},
        {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "t1", "name": "Bash",
                                                       "input": {"command": EVIL}}]}},
        {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t1",
                                                  "content": tool_result}]}},
        {"type": "result", "subtype": "success", "is_error": False, "result": answer, "total_cost_usd": 0.01,
         "num_turns": 2},
    ]
    (d / f"{task['id']}-k1.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events), encoding="utf-8")
    (d / f"{task['id']}-k1.meta.json").write_text(json.dumps({"flags": list(flags), "model": HAIKU,
                                                                 "condition": "B", "effort": "medium",
                                                                 "task_id": task["id"], "k": 1}), encoding="utf-8")
    return tmp_path / "hand", task


def views_of(runs):
    return sorted((pathlib.Path(runs) / "views").glob("*/*/*/*.html"))


# ------------------------------------------------------------------ one page per transcript
def test_one_view_per_transcript_with_all_sections(tmp_path):
    runs = dry_runs(tmp_path)
    score.score_dir(runs)
    res = report.render_dir(runs)
    transcripts = sorted(runs.glob("*/*/*/*.jsonl"))
    assert res["n_views"] == len(transcripts) == len(views_of(runs)) == 6
    for t in transcripts:
        view = runs / "views" / t.relative_to(runs).with_suffix(".html")
        assert view.exists()
    plan = json.loads((runs / "plan.jsonl").read_text(encoding="utf-8").splitlines()[1])
    text = (runs / "views" / f"{HAIKU}/{plan['condition']}/medium/{plan['task_id']}-k1.html").read_text(
        encoding="utf-8")
    for needle in ("User prompt", "System prompt", "argv template", "Final answer", "Tool calls", "Score",
                   plan["model"], plan["condition"], "medium", "rel_err_dq"):
        assert needle in text
    assert report.escape_html(plan["prompt"].strip().splitlines()[0]) in text
    assert plan["system_prompt_text"].splitlines()[0] in text


def test_tool_calls_unhashable_ids_do_not_raise():
    use = {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": ["x"], "name": "Bash", "input": {"command": "a"}},
        {"type": "tool_use", "id": "ok", "name": "Bash", "input": {"command": "b"}}]}}
    res = {"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": ["x"], "content": "bad"},
        {"type": "tool_result", "tool_use_id": "ok", "content": "good"}]}}
    calls = views.tool_calls([use, res])
    assert [c["result"] for c in calls] == [None, "good"]


def test_tool_calls_and_results_are_listed_in_order(tmp_path):
    runs = dry_runs(tmp_path, limit=1)
    report.render_dir(runs)
    c_view = next((runs / "views").glob(f"{HAIKU}/C/medium/*.html")).read_text(encoding="utf-8")
    assert "Tool calls (" in c_view and "mcp__tanabesugano__" in c_view
    a_view = next((runs / "views").glob(f"{HAIKU}/A/medium/*.html")).read_text(encoding="utf-8")
    assert "Tool calls (0)" in a_view


def test_repeated_tool_use_event_is_one_call():
    use = {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": "toolu_x", "name": "Bash", "input": {"command": "ls"}}]}}
    res = {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "toolu_x", "content": "ok"}]}}
    calls = views.tool_calls([use, dict(use), res])
    assert len(calls) == 1 and calls[0]["result"] == "ok"


def test_view_without_scores_or_plan_still_renders(tmp_path):
    runs, task = hand_made(tmp_path, tool_result="ok", answer="done", flags=())
    report.render_dir(runs)
    text = next((runs / "views").glob("*/*/*/*.html")).read_text(encoding="utf-8")
    assert "no scores.csv row" in text and "User prompt" in text
    assert report.escape_html(task["prompt"])[:60] in text  # no plan: the prompt comes from the task file
    assert "Tool calls (1)" in text


# ------------------------------------------------------------------ escaping, self-containment
def test_hostile_text_is_escaped_everywhere(tmp_path):
    runs, _ = hand_made(tmp_path, flags=(EVIL,))
    report.render_dir(runs)
    view = next((runs / "views").glob("*/*/*/*.html")).read_text(encoding="utf-8")
    index = (runs / "views" / "INDEX.html").read_text(encoding="utf-8")
    for text in (view, index):
        assert "<script>alert" not in text
        assert "<img" not in text
    assert "&lt;script&gt;alert(&#39;x&#39;)&lt;/script&gt;" in view
    assert view.count("&lt;script&gt;") >= 4  # command, result, answer, flag
    assert "<script" not in view  # views carry no script at all


def test_hostile_run_names_cannot_break_the_index(tmp_path):
    runs, task = hand_made(tmp_path)
    nasty = runs / '"><b>x'
    (runs / HAIKU).rename(nasty)
    report.render_dir(runs)
    index = (runs / "views" / "INDEX.html").read_text(encoding="utf-8")
    assert "<b>x" not in index


def test_pages_are_self_contained_and_themed(tmp_path):
    runs = dry_runs(tmp_path, limit=1)
    report.render_dir(runs)
    pages = [*views_of(runs), runs / "views" / "INDEX.html"]
    for p in pages:
        text = p.read_text(encoding="utf-8")
        assert "prefers-color-scheme:dark" in text and "<style>" in text and 'name="color-scheme"' in text
        assert not re.search(r"(src|href)=[\"'](https?:)?//", text)
        assert "<link" not in text and "@import" not in text and "url(" not in text
        assert not re.search(r"<script[^>]*\ssrc=", text)
    assert (runs / "views" / "INDEX.html").read_text(encoding="utf-8").count("<script>") == 1


def test_long_tool_results_are_truncated(tmp_path):
    runs, _ = hand_made(tmp_path, tool_result="Y" * 50000, answer="short")
    report.render_dir(runs)
    view = next((runs / "views").glob("*/*/*/*.html")).read_text(encoding="utf-8")
    assert "truncated, 48000 more characters" in view and len(view) < 20000


def test_render_is_a_pure_function_of_its_inputs(tmp_path):
    runs = dry_runs(tmp_path, limit=1)
    score.score_dir(runs)
    report.render_dir(runs)
    first = {p: p.read_bytes() for p in (runs / "views").rglob("*.html")}
    report.render_dir(runs)
    assert {p: p.read_bytes() for p in (runs / "views").rglob("*.html")} == first


# ------------------------------------------------------------------ index
def test_index_links_every_view_and_resolves(tmp_path):
    runs = dry_runs(tmp_path)
    score.score_dir(runs)
    report.render_dir(runs)
    index = runs / "views" / "INDEX.html"
    text = index.read_text(encoding="utf-8")
    hrefs = re.findall(r'<a href="([^"]+)">', text)
    assert len(hrefs) == len(views_of(runs)) == 6
    for h in hrefs:
        assert (index.parent / h).is_file(), h
    assert set(hrefs) == {v.relative_to(index.parent).as_posix() for v in views_of(runs)}
    plan_id = json.loads((runs / "plan.jsonl").read_text(encoding="utf-8").splitlines()[0])["plan_id"]
    assert plan_id in text and "scores.csv sha256" in text
    for col in ("run_id", "class", "condition", "correct", "cost_usd", "turns", "tool_calls", "flags"):
        assert f">{col}</th>" in text
    for run_id in (str(p.relative_to(runs).with_suffix("")) for p in runs.glob("*/*/*/*.jsonl")):
        assert report.escape_html(run_id) in text


def test_view_links_back_to_index_and_raw_transcript(tmp_path):
    runs = dry_runs(tmp_path, limit=1)
    report.render_dir(runs)
    view = views_of(runs)[0]
    links = re.findall(r'<a href="([^"]+)">', view.read_text(encoding="utf-8"))
    resolved = [(view.parent / link).resolve() for link in links]
    assert (runs / "views" / "INDEX.html").resolve() in resolved
    raw = view.relative_to(runs / "views").with_suffix(".jsonl")
    assert (runs / raw).resolve() in resolved


# ------------------------------------------------------------------ confirmatory guard
def test_cli_renders_pilot_and_reports_counts(tmp_path, capsys):
    runs = dry_runs(tmp_path, limit=1)
    assert report_cli.main(["render", "--runs", str(runs)]) == 0
    assert "views written: 3" in capsys.readouterr().out
    assert report_cli.main(["render", "--runs", str(tmp_path / "nope")]) == 2


def test_confirmatory_needs_the_doi_by_flag_or_by_what_the_directory_says(tmp_path, capsys):
    runs = dry_runs(tmp_path, limit=1)
    assert report_cli.main(["render", "--runs", str(runs), "--split", "confirmatory"]) == 2
    other = tmp_path / "conf"
    other.mkdir()
    (other / "MANIFEST.json").write_text(json.dumps({"split": "confirmatory"}), encoding="utf-8")
    assert report_cli.main(["render", "--runs", str(other)]) == 2
    assert not (other / "views").exists()
    sealed = tmp_path / "sealed"
    sealed.mkdir()
    (sealed / "plan.sealed.json").write_text(json.dumps({"spec": {"split": "confirmatory"}}) + "\n", encoding="utf-8")
    assert report_cli.main(["render", "--runs", str(sealed)]) == 2
    assert report_cli.main(["render", "--runs", str(other), "--i-have-preregistered", "10.1234/x"]) == 0
    assert (other / "views" / "INDEX.html").exists()


def test_href_is_relative_and_quoted(tmp_path):
    out = tmp_path / "out"
    assert report.href(out / "views" / "a b.html", out) == "views/a%20b.html"
    assert report.href(tmp_path / "x.png", out) == "../x.png"


def test_href_uses_forward_slashes_on_windows_paths(monkeypatch):
    monkeypatch.setattr(page, "os", types.SimpleNamespace(path=ntpath))
    monkeypatch.setattr(page, "pathlib", types.SimpleNamespace(PurePath=pathlib.PureWindowsPath))
    got = report.href(r"C:\runs\views\m\a b.html", r"C:\runs")
    assert got == "views/m/a%20b.html" and "\\" not in got


def test_href_gives_no_link_on_another_drive(tmp_path, monkeypatch):
    """No relative link possible: no link at all, never a file: URI or an absolute path."""
    def other_drive(*a, **k):
        raise ValueError("path is on mount 'D:', start on mount 'C:'")
    monkeypatch.setattr(page.os.path, "relpath", other_drive)
    assert report.href(tmp_path / "x.png", tmp_path / "out") is None


def test_views_and_index_carry_the_csp_and_no_file_uri(tmp_path):
    runs = dry_runs(tmp_path, limit=1)
    report.render_dir(runs)
    for p in [*views_of(runs), runs / "views" / "INDEX.html"]:
        text = p.read_text(encoding="utf-8")
        assert f'<meta http-equiv="Content-Security-Policy" content="{page.CSP}">' in text
        assert "file:" not in text and str(tmp_path) not in text


def test_views_command_takes_several_run_sets_and_writes_an_overview(tmp_path, capsys):
    first = dry_runs(tmp_path / "one", limit=1)
    second = dry_runs(tmp_path / "two", limit=1)
    out = tmp_path / "site" / "RUN-SETS.html"
    assert views.main(["--runs", str(tmp_path / "one"), "--runs", str(second), "--out", str(out)]) == 0
    assert (first / "views" / "INDEX.html").is_file() and (second / "views" / "INDEX.html").is_file()
    markup = out.read_text(encoding="utf-8")
    links = re.findall(r'<a href="([^"]+)">', markup)
    assert len(links) == 2 and all((out.parent / h).resolve().is_file() for h in links)
    assert page.CSP in markup and "file:" not in markup
    assert report_cli.main(["views", "--runs", str(first)]) == 0
