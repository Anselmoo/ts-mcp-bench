"""The provenance page of a functional test (tsbench report provenance): per step the command, a collapsible call tree,
inputs and outputs with sha256, links from an input to the step that wrote it, and the hash-chain verdict. The trace
records are written by hand in the format of tsbench.core.trace."""
from __future__ import annotations

import importlib
import json
import re
from pathlib import Path

import pytest

from tsbench import cli
from tsbench.report import page, summary

HOSTILE = '<img src=x onerror=alert(1)>"\'&'
CSP_META = f'<meta http-equiv="Content-Security-Policy" content="{page.CSP}">'
H_PLAN, H_TRANSCRIPT, H_SCORES, H_TASKS = ("a1" * 32, "b2" * 32, "c3" * 32, "d4" * 32)


@pytest.fixture
def provenance():
    return importlib.import_module("tsbench.report.provenance")


def _open(path: Path | str, mode: str, sha: str | None, caller: str = "tsbench.x:f") -> dict:
    reading = mode.startswith("r")
    return {"event": "open", "path": str(path), "mode": mode, "caller": caller,
            "sha256_at_read": sha if reading else None, "sha256_at_end": sha}


def _record(pid: int, start: float, command: str, files: list[dict], calls: list[dict]) -> dict:
    return {"schema": "tsbench.trace/1", "pid": pid, "ppid": 1, "argv": command.split(), "command": command,
            "cwd": "/w", "start": start, "end": start + 0.5, "exit_code": 0, "calls": calls, "files": files}


def _edge(function: str, caller: str | None, count: int = 1) -> dict:
    return {"function": function, "caller": caller, "count": count}


def functional_test_folder(root: Path, *, transcript_read: str = H_TRANSCRIPT, extra_steps=()) -> Path:
    """A functional-test folder with steps.jsonl and trace/<step>/ records for plan-build, run and score."""
    plan, transcript, scores = root / "plan" / "plan.jsonl", root / "runs" / "t-k1.jsonl", root / "runs" / "scores.csv"
    tasks = "~/repo/src/tsbench/data/tasks/tasks.jsonl"
    steps = {
        "plan-build": _record(10, 0.0, "tsbench plan build", [_open(tasks, "r", H_TASKS), _open(plan, "w", H_PLAN)],
                              [_edge("tsbench.plan.__main__:main", None),
                               _edge("tsbench.plan.build:build", "tsbench.plan.__main__:main")]),
        "run": _record(20, 2.0, f"tsbench run {HOSTILE}",
                       [_open(plan, "r", H_PLAN), _open(transcript, "w", H_TRANSCRIPT)],
                       [_edge("tsbench.run.runner:main", None), _edge(HOSTILE, "tsbench.run.runner:main")]),
        "score": _record(30, 4.0, f"tsbench score --runs {root / 'runs'}", [_open(transcript, "r", transcript_read),
                                                     _open(scores, "w", H_SCORES)],
                         [_edge("tsbench.score.score:main", None),
                          _edge("tsbench.score.score:score_runs", "tsbench.score.score:main", 1),
                          _edge("tsbench.score.score:wall_time", "tsbench.score.score:score_runs", 9)]),
    }
    lines = []
    for name, rec in steps.items():
        d = root / "trace" / name
        d.mkdir(parents=True)
        (d / f"{rec['pid']}.trace.json").write_text(json.dumps(rec), encoding="utf-8")
        lines.append({"name": name, "command": rec["command"], "rc": 0, "log": f"logs/{name}.log", "outputs": []})
    lines += [{"name": n, "command": f"tsbench {n}", "rc": 0, "log": f"logs/{n}.log", "outputs": []}
              for n in extra_steps]
    (root / "steps.jsonl").write_text("".join(json.dumps(x) + "\n" for x in lines), encoding="utf-8")
    return root


def build(provenance, root: Path) -> tuple[int, str]:
    out = root / "provenance.html"
    rc = provenance.main(["--steps", str(root / "steps.jsonl"), "--trace", str(root / "trace"), "--out", str(out)])
    return rc, out.read_text(encoding="utf-8")


def section(html: str, step: str) -> str:
    """The part of the page from `<section id="step-STEP">` to the next `<section`. Steps are sibling sections."""
    start = html.index(f'<section id="step-{step}"')
    nxt = html.find("<section", start + 1)
    return html[start: nxt if nxt != -1 else len(html)]


def own(html: str) -> str:
    return re.sub(r"<script\b[^>]*>.*?</script>", "", html, flags=re.S)


# ---------------------------------------------------------------- content
def test_every_step_shows_its_command_and_its_call_tree(provenance, tmp_path):
    root = functional_test_folder(tmp_path)
    rc, html = build(provenance, root)
    assert rc == 0
    for step in ("plan-build", "run", "score"):
        assert f'<section id="step-{step}"' in html
    score = section(html, "score")
    assert "tsbench score" in score and "<details" in score
    i_main, i_runs = score.index("tsbench.score.score:main"), score.index("tsbench.score.score:score_runs")
    i_wall = score.index("tsbench.score.score:wall_time")
    assert i_main < i_runs < i_wall, "a callee is listed under its caller"


def test_inputs_and_outputs_show_relative_paths_and_their_sha256(provenance, tmp_path):
    root = functional_test_folder(tmp_path)
    _, html = build(provenance, root)
    run = section(html, "run")
    assert "plan/plan.jsonl" in run and "runs/t-k1.jsonl" in run
    assert H_PLAN[:12] in run and H_TRANSCRIPT[:12] in run
    assert H_TASKS[:12] in section(html, "plan-build") and "data/tasks/tasks.jsonl" in html
    assert H_SCORES[:12] in section(html, "score")
    assert str(tmp_path) not in html, "paths inside the run folder, also in commands, are shown relative to it"
    assert "--runs runs" in section(html, "score")


def test_an_input_links_to_the_output_of_the_step_that_wrote_it(provenance, tmp_path):
    root = functional_test_folder(tmp_path)
    _, html = build(provenance, root)
    plan_ids = set(re.findall(r'id="([^"]+)"', section(html, "plan-build")))
    run_links = set(re.findall(r'href="#([^"]+)"', section(html, "run")))
    assert run_links & plan_ids, "run's input plan/plan.jsonl links to plan-build's output"
    run_ids = set(re.findall(r'id="([^"]+)"', section(html, "run")))
    assert set(re.findall(r'href="#([^"]+)"', section(html, "score"))) & run_ids
    all_ids = set(re.findall(r'id="([^"]+)"', html))
    assert set(re.findall(r'href="#([^"]+)"', html)) <= all_ids, "no dangling anchor"


def test_a_writer_outside_the_listed_steps_gets_no_link(provenance, tmp_path):
    """A trace folder that steps.jsonl does not list is not shown, so an input it wrote has no link to it."""
    root = functional_test_folder(tmp_path)
    stray = _record(15, 1.0, "tsbench stray", [_open(root / "plan" / "plan.jsonl", "w", H_PLAN)], [])
    (root / "trace" / "stray").mkdir()
    (root / "trace" / "stray" / "15.trace.json").write_text(json.dumps(stray), encoding="utf-8")
    rc, html = build(provenance, root)
    assert rc == 0
    all_ids = set(re.findall(r'id="([^"]+)"', html))
    assert set(re.findall(r'href="#([^"]+)"', html)) <= all_ids, "no dangling anchor"


def test_an_intact_chain_says_so_and_exits_zero(provenance, tmp_path):
    rc, html = build(provenance, functional_test_folder(tmp_path))
    assert rc == 0 and "Hash chain intact" in html and "Hash chain broken" not in html


def test_a_broken_chain_names_the_file_and_exits_one(provenance, tmp_path):
    rc, html = build(provenance, functional_test_folder(tmp_path, transcript_read=H_SCORES))
    assert rc == 1 and "Hash chain broken" in html and "Hash chain intact" not in html
    assert "runs/t-k1.jsonl" in html[: html.index('<section id="step-')], "the verdict above the steps names the file"


def test_a_step_without_a_trace_is_shown_as_such(provenance, tmp_path):
    rc, html = build(provenance, functional_test_folder(tmp_path, extra_steps=("figures",)))
    assert rc == 0
    assert "no trace" in section(html, "figures")


def test_a_call_cycle_does_not_hang_the_tree(provenance, tmp_path):
    root = functional_test_folder(tmp_path)
    rec_path = next((root / "trace" / "score").glob("*.trace.json"))
    rec = json.loads(rec_path.read_text(encoding="utf-8"))
    rec["calls"] += [_edge("tsbench.a:f", "tsbench.score.score:main"), _edge("tsbench.a:g", "tsbench.a:f"),
                     _edge("tsbench.a:f", "tsbench.a:g")]
    rec_path.write_text(json.dumps(rec), encoding="utf-8")
    rc, html = build(provenance, root)
    assert rc == 0 and "tsbench.a:g" in section(html, "score")


def test_the_prov_json_is_written_next_to_the_page(provenance, tmp_path):
    root = functional_test_folder(tmp_path)
    build(provenance, root)
    doc = json.loads((root / "provenance.prov.json").read_text(encoding="utf-8"))
    assert len(doc["activity"]) == 3 and doc["entity"] and doc["used"] and doc["wasGeneratedBy"]


def test_the_prov_json_path_can_be_given(provenance, tmp_path):
    root = functional_test_folder(tmp_path)
    target = tmp_path / "elsewhere" / "p.json"
    rc = provenance.main(["--steps", str(root / "steps.jsonl"), "--trace", str(root / "trace"),
                          "--out", str(root / "provenance.html"), "--prov", str(target)])
    assert rc == 0 and json.loads(target.read_text(encoding="utf-8"))["activity"]


# ---------------------------------------------------------------- security: a static page, nothing from the network
def test_the_page_is_static_escaped_and_carries_the_csp(provenance, tmp_path):
    _, html = build(provenance, functional_test_folder(tmp_path))
    assert CSP_META in html and 'lang="en"' in html
    assert HOSTILE not in html and "<img src=x" not in html
    assert "&lt;img src=x onerror=alert(1)&gt;" in html
    body = own(html)
    assert not re.search(r"<script[^>]+src=|<link\b|@import", html, re.I), "no script or style from elsewhere"
    assert not re.search(r"""(?:src|href)\s*=\s*["']?(?:https?:)?//""", body, re.I), "no external resource"
    assert "file:" not in body


def test_build_html_is_the_page_main_writes(provenance, tmp_path):
    root = functional_test_folder(tmp_path)
    _, written = build(provenance, root)
    steps = summary.load_steps(root / "steps.jsonl")
    again = provenance.build_html(steps, root / "trace", root / "provenance.html")
    assert again == written


# ---------------------------------------------------------------- wiring
def test_the_command_is_registered():
    assert cli.resolve(["report", "provenance", "--out", "x"]) == ("tsbench.report.provenance:main", ["--out", "x"])


def test_the_summary_links_the_provenance_page_when_it_exists(tmp_path):
    (tmp_path / "logs").mkdir()
    (tmp_path / "steps.jsonl").write_text(json.dumps({"name": "score", "command": "tsbench score", "rc": 0,
                                                      "log": "logs/score.log", "outputs": []}) + "\n",
                                          encoding="utf-8")
    out = tmp_path / "SUMMARY.html"
    summary.main(["--steps", str(tmp_path / "steps.jsonl"), "--out", str(out)])
    assert 'href="provenance.html"' not in out.read_text(encoding="utf-8")
    (tmp_path / "provenance.html").write_text("<p>x</p>", encoding="utf-8")
    summary.main(["--steps", str(tmp_path / "steps.jsonl"), "--out", str(out)])
    assert 'href="provenance.html"' in out.read_text(encoding="utf-8")
