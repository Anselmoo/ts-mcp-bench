"""Tests for the run gallery (src/tsbench/report/gallery.py)."""
from __future__ import annotations

import base64
import csv
import json
import re

import pytest

from tsbench.report import gallery as gal
from tsbench.report import page

PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")
PNG = base64.b64encode(PNG_BYTES).decode()


RESULT = {"type": "result", "subtype": "success", "is_error": False, "result": "done", "num_turns": 2,
          "total_cost_usd": 0.1, "duration_ms": 1500, "usage": {"input_tokens": 10, "output_tokens": 5}}


def _ev(role, block):
    return {"type": role, "message": {"role": role, "content": [block]}}


def _transcript(path, events):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(x) for x in events) + "\n", encoding="utf-8")


def _run(root, model="m<1>", cond="B", task="P-diagram-01", answer="done", extra=()):
    d = root / model / cond / "medium"
    _transcript(d / f"{task}-k1.jsonl", [
        _ev("assistant", {"type": "tool_use", "id": "t1", "name": "Bash",
                          "input": {"command": "cat > s.py <<'EOF'\nprint('<b>&')\nEOF\npython s.py"}}),
        _ev("user", {"type": "tool_result", "tool_use_id": "t1", "content": "Exit code 1\nboom <script>",
                     "is_error": True}),
        _ev("assistant", {"type": "tool_use", "id": "t2", "name": "mcp__ts__ts_plot_png", "input": {"B": 1}}),
        _ev("user", {"type": "tool_result", "tool_use_id": "t2", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": PNG}}]}),
        _ev("assistant", {"type": "text", "text": answer}),
        *extra,
    ])
    (d / f"{task}-k1.meta.json").write_text(json.dumps(
        {"model": model, "condition": cond, "effort": "medium", "task_id": task, "k": 1, "image_sha_match": True}),
            encoding="utf-8")
    return d


def _scores(root, model, cond, task, correct):
    with open(root / "scores.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["model", "condition", "effort", "task_id", "k_index", "class", "correct"])
        w.writerow([model, cond, "medium", task, 1, "diagram", correct])


def test_sanitize_svg_strips_active_and_external():
    dirty = ('<svg xmlns="http://www.w3.org/2000/svg" onload="x()"><script>alert(1)</script>'
             '<a xlink:href="https://evil.example/x"><rect onclick="y()" width="1"/></a>'
             '<image href="http://evil.example/a.png"/><use href="#ok"/>'
             '<style>@import url(http://evil.example/c.css); .a{fill:url(https://evil.example/g)}</style>'
             '<set attributeName="href" to="javascript:alert(1)"/><circle style="fill:url(#g)"/></svg>')
    clean = gal.sanitize_svg(dirty)
    low = clean.lower()
    assert "<script" not in low and "onload" not in low and "onclick" not in low
    assert "evil.example" not in low and "javascript" not in low and "<set" not in low
    assert 'href="#ok"' in clean and "url(#g)" in clean and "<rect" in clean


def test_find_svgs():
    found = gal.find_svgs('x <svg a="1"><g/></svg> y <svg><rect/></svg>')
    assert found == ['<svg a="1"><g/></svg>', "<svg><rect/></svg>"]
    assert gal.find_svgs("nothing") == []


def test_gallery_collects_all_sources_and_escapes(tmp_path):
    root = tmp_path / "runs" / "run"
    svg = '<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script><rect width="2" height="2"/></svg>'
    d = _run(root, answer=f"Here:\n```svg\n{svg}\n```", extra=[RESULT])
    art = d / "P-diagram-01-k1.artifacts"
    art.mkdir()
    (art / "diagram.png").write_bytes(PNG_BYTES + b"\0")
    _scores(root, "m<1>", "B", "P-diagram-01", "False")
    (root / "views" / "m<1>" / "B" / "medium").mkdir(parents=True)
    (root / "views" / "m<1>" / "B" / "medium" / "P-diagram-01-k1.html").write_text("x", encoding="utf-8")
    page, counts = gal.build_html([root], tmp_path / "runs")
    assert counts["images_by_source"] == {"artifact": 1, "mcp": 1, "svg-answer": 1}
    assert counts["runs_with_code"] == 1 and counts["code_files"] == 2
    assert 'lang="en"' in page and ">Images<" in page and ">Code<" in page
    assert "m<1>" not in page and "m&lt;1&gt;" in page          # model name escaped
    assert "print(&#39;&lt;b&gt;&amp;&#39;)" in page            # code escaped
    assert "boom &lt;script&gt;" in page and "<script>alert" not in page
    assert 'data-ok="wrong"' in page and "run view" in page and "sha256 matches" in page
    # the svg is embedded as data-URI without its script
    m = re.findall(r'src="data:image/svg\+xml;base64,([^"]+)"', page)
    assert m and all(b"<script" not in base64.b64decode(x) for x in m)


def test_collect_runs_reads_through_the_reader_it_is_given(tmp_path):
    root = tmp_path / "runs" / "run"
    d = _run(root)
    t = d / "P-diagram-01-k1.jsonl"
    asked = []

    def reader(path):
        asked.append(path)
        from tsbench.score.extract import read_transcript
        return read_transcript(path)

    runs = gal.collect_runs([root], reader)
    assert len(runs) == 1 and asked == [t]


def test_collect_runs_parses_each_transcript_once(tmp_path, monkeypatch):
    import builtins
    root = tmp_path / "runs" / "run"
    svg = '<svg xmlns="http://www.w3.org/2000/svg"><rect width="2" height="2"/></svg>'
    d = _run(root, answer=f"```svg\n{svg}\n```", extra=[RESULT])
    t = d / "P-diagram-01-k1.jsonl"
    _run(root, model="m2", cond="C")
    real, seen = builtins.open, []

    def counting(file, *a, **kw):
        if str(file).endswith(".jsonl"):
            seen.append(str(file))
        return real(file, *a, **kw)

    monkeypatch.setattr(builtins, "open", counting)
    runs = gal.collect_runs([root])
    assert len(runs) == 2 and any(r["images"] for r in runs)
    assert sorted(seen) == sorted({str(r["transcript"]) for r in runs}) and str(t) in seen


def test_gallery_zero_images_and_zero_code(tmp_path):
    root = tmp_path / "runs" / "empty"
    root.mkdir(parents=True)
    page, counts = gal.build_html([root], tmp_path / "runs")
    assert counts["runs"] == 0 and counts["images"] == 0
    assert "No images found." in page and "No code found." in page
    # a run with a transcript but neither images nor code
    _transcript(root / "m/A/medium/P-x-01-k1.jsonl", [_ev("assistant", {"type": "text", "text": "hi"})])
    page, counts = gal.build_html([root], tmp_path / "runs")
    assert counts["runs"] == 1 and counts["images"] == 0 and "No images found." in page


def test_no_external_resources(tmp_path):
    root = tmp_path / "runs" / "run"
    _run(root, answer='<svg><image href="https://evil.example/a.png"/><rect/></svg>')
    page, _ = gal.build_html([root], tmp_path / "runs")
    assert not re.search(r"""(?:src|href|action)\s*=\s*["']?\s*(?:https?:)?//""", page, re.I)
    assert not re.search(r"<link\b|<script[^>]+src=|@import|url\(\s*['\"]?https?:", page, re.I)
    for m in re.findall(r'src="data:image/svg\+xml;base64,([^"]+)"', page):
        assert b"evil.example" not in base64.b64decode(m)


def test_big_image_is_linked_not_embedded_when_the_page_budget_is_used_up(tmp_path, monkeypatch):
    root = tmp_path / "runs" / "run"
    d = _run(root)
    art = d / "P-diagram-01-k1.artifacts"
    art.mkdir()
    (art / "diagram.png").write_bytes(PNG_BYTES)
    monkeypatch.setattr(gal, "PAGE_BUDGET", 0)
    monkeypatch.setattr(gal, "EMBED_LIMIT", 10)
    page, counts = gal.build_html([root], tmp_path / "runs")
    assert counts["linked"] >= 1
    # the CSP allows images only as data: URIs, so a linked image is a plain link, never an <img src> to a file
    assert 'href="run/m%3C1%3E/B/medium/P-diagram-01-k1.artifacts/diagram.png"' in page
    assert not re.search(r'<img[^>]+src="(?!data:)', page)


def test_cli_writes_file(tmp_path, capsys):
    root = tmp_path / "runs" / "run"
    _run(root)
    out = tmp_path / "runs" / "G.html"
    assert gal.main(["--runs", str(root), "--out", str(out)]) == 0
    assert out.read_text(encoding="utf-8").startswith("<!doctype html>")
    assert "images_by_source" in capsys.readouterr().out


@pytest.mark.parametrize(("cell", "verdict"), [("True", "correct"), ("TRUE", "correct"), ("1", "correct"),
                                                ("False", "wrong"), ("0", "wrong"), ("", "unscored")])
def test_the_verdict_of_a_scores_row_reads_the_correct_cell_like_every_page(cell, verdict):
    assert gal.verdict_from_scores({"correct": cell}) == verdict
    assert gal.verdict_from_scores(None) == "unscored"


def test_mcp_image_shows_computed_hash_not_missing_claim():
    """An MCP-generated image never was a file for the model: show the computed hash, not a missing claim."""
    import hashlib as _h
    data = b"\x89PNG fake"
    txt = gal.sha_text(None, "mcp", data)
    assert "made by the MCP server" in txt and _h.sha256(data).hexdigest()[:16] in txt
    assert gal.sha_text(None, "artifact", None) == "sha256: not reported by the model"


# ---------------------------------------------------------------- cards, figures, reproduce blocks
import pathlib  # noqa: E402
import shlex  # noqa: E402

from tsbench.report import reproduce  # noqa: E402

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


def _fit_run(root, model="claude-opus-5-5", cond="C", task="P-closed_form-01", manifest=None, answer=None):
    from tsbench.tasks import load
    ref = {t["id"]: t for t in load("pilot")}[task]["reference"]
    ans = answer or {"Dq": ref["Dq"], "B": ref["B"], "C": ref["C"], "out_of_scope": False}
    d = root / model / cond / "medium"
    _transcript(d / f"{task}-k2.jsonl",
                [_ev("assistant", {"type": "text", "text": "x"}), {**RESULT, "structured_output": ans}])
    if manifest is not None:
        (root / "MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
    return d / f"{task}-k2.jsonl"


def test_every_run_has_a_card_with_verdict_figure_and_reproduce_block(tmp_path):
    root = tmp_path / "runs" / "run"
    t = _fit_run(root, manifest={"args": {"gateway": False}, "budget_usd": 3.0})
    page, counts = gal.build_html([root], tmp_path / "runs")
    assert counts["cards"] == counts["runs"] == 1 and counts["verdicts"] == {"correct": 1}
    assert counts["figures_by_kind"] == {"fit_error": 1, "metrics": 1} and counts["cards_with_figures"] == 1
    assert 'id="runs"' in page and 'data-ok="correct"' in page and "✓" in page and "Anthropic API" in page
    figdir = t.with_name("P-closed_form-01-k2.figs")
    assert (figdir / "fit_error.svg").is_file()
    # embedded (CSP: data: only)
    uris = re.findall(r'<figure><img id="fg-\d+" src="data:image/svg\+xml,([^"]+)"', page)
    assert len(uris) == 2 and all("%3Cscript" not in u and "<script" not in u for u in uris)
    assert ".figs/fit_error.svg" not in page
    assert "Reproduce" in page and 'class="copy"' in page and "<pre>" in page
    for need in ('id="f-model"', 'id="f-cond"', 'id="f-cls"', 'id="f-ok"', 'id="overview"'):
        assert need in page
    for v in ("correct", "wrong", "harness", "na429", "unscored"):
        assert f'<option value="{v}">' in page


def test_cards_line_up_outcome_first_and_reproduce_at_the_foot(tmp_path):
    """Uniform cards: the outcome badge opens every card at the same place, the reproduce block sits at the foot of
    its card and wraps instead of being cut; the filters share one grid; a filter is called Outcome, not Verdict."""
    root = tmp_path / "runs" / "run"
    _fit_run(root, manifest={"args": {"gateway": False}})
    page, _ = gal.build_html([root], tmp_path / "runs", make_figs=False)
    card = page[page.index('<article class="item run"'):]
    assert card.index('class="badge') < card.index("condition") < card.index("Anthropic API")
    assert ">Outcome<select" in page and ">Verdict<" not in page
    assert ".gallery .item{" in page and "flex-direction:column" in page and ".gallery .repro{margin:auto 0 0" in page
    assert "white-space:pre-wrap" in page and "repeat(auto-fit,minmax(min(100%,300px),1fr))" in page
    assert ".gallery .filters{display:grid" in page


def test_page_inlines_d3_and_jfs_without_external_resources(tmp_path):
    root = tmp_path / "runs" / "run"
    _fit_run(root)
    page, _ = gal.build_html([root], tmp_path / "runs", make_figs=False)
    assert "d3js.org v7.9.0" in page and "useTheme" in page and "window.JFS = {" in page
    assert page.count("</script>") == len(re.findall(r"<script\b", page))  # no stray </script inside the inlined code
    assert not re.search(r"<script[^>]+src=|<link\b", page, re.I)


def test_unreadable_figures_never_break_the_gallery(tmp_path, monkeypatch):
    root = tmp_path / "runs" / "run"
    _fit_run(root)

    def boom(*a, **k):
        raise RuntimeError("no figures today")
    monkeypatch.setattr(gal.run_figures, "make_figures", boom)
    page, counts = gal.build_html([root], tmp_path / "runs")
    assert counts["runs"] == 1 and counts["figures"] == 0 and "Reproduce" in page


def _parse_repro(text):
    """Parse every command of a reproduce block with the real argparse parsers (nothing is executed)."""
    from tsbench.plan import __main__ as plan_main
    from tsbench.report import explain
    from tsbench.run import runner
    seen = {}
    for line in text.splitlines():
        if not line.strip() or line.startswith("#") or line.startswith("export "):
            continue
        argv = shlex.split(line)
        assert argv[0] == "tsbench"
        if argv[:3] == ["tsbench", "plan", "build"]:
            captured = {}
            orig = plan_main.cmd_build
            plan_main.cmd_build = lambda a, captured=captured: captured.setdefault("a", a) and 0
            try:
                assert plan_main.main(argv[2:]) == 0
            finally:
                plan_main.cmd_build = orig
            seen["plan"] = captured["a"]
        elif argv[:2] == ["tsbench", "run"]:
            seen["runner"] = runner.parse_args(argv[2:])
        elif argv[:2] == ["tsbench", "explain"]:
            seen["explain"] = argv[2:]
            # flags parse; file check fails first
            assert explain.main([str(REPO_ROOT / "does-not-exist.jsonl"), *argv[3:]]) == 2
        else:
            pytest.fail(f"unknown command {line}")
    return seen


def test_reproduce_block_parses_with_the_real_parsers_claude(tmp_path):
    root = tmp_path / "runs" / "run"
    t = _fit_run(root, manifest={"args": {"gateway": False}, "budget_usd": 3.0})
    run = {"transcript": t, "root": root, "model": "claude-opus-5-5", "cond": "C", "effort": "medium",
           "task": "P-closed_form-01", "k": "2"}
    text = reproduce.commands(run)
    assert "ANTHROPIC" not in text and "GWDG" not in text
    seen = _parse_repro(text)
    a = seen["plan"]
    assert (a.split, a.task_ids, a.models, a.conditions, a.effort, a.k, a.budget_usd, a.gateway) == (
        "pilot", "P-closed_form-01", "claude-opus-5-5", "C", "medium", 1, 3.0, False)
    r = seen["runner"]
    assert r.plan == a.out_plan and r.out.startswith("repro/") and not r.gateway
    # one dir per cell: plan.sha256/plan.md never shared
    assert a.out_plan == f"{r.out}/plan.jsonl"
    assert "--task-version" not in text and "k2 is a repetition" in text
    assert str(tmp_path) not in text                                             # no absolute path of this machine


def test_reproduce_block_gateway(tmp_path):
    root = tmp_path / "runs" / "gw"
    t = _fit_run(root, model="qwen3.5-397b-a17b", cond="A", manifest={"args": {"gateway": True}, "budget_usd": 3.0})
    run = {"transcript": t, "root": root, "model": "qwen3.5-397b-a17b", "cond": "A", "effort": "medium",
           "task": "P-closed_form-01", "k": "1"}
    text = reproduce.commands(run)
    assert text.count("GWDG_API_KEY") == 1 and 'ANTHROPIC_AUTH_TOKEN="$GWDG_API_KEY"' in text
    assert "ANTHROPIC_BASE_URL=https://chat-ai.academiccloud.de" in text
    assert not re.search(r"(?:\bsk-|Bearer\s|[A-Za-z0-9]{40,})", text)                # names only, never a key value
    seen = _parse_repro(text)
    assert seen["plan"].gateway and seen["plan"].budget_usd == 1000 and seen["runner"].gateway
    assert len(seen["explain"]) == 1 and seen["explain"][0].endswith("P-closed_form-01-k2.jsonl")


def test_reproduce_block_gateway_repeats_the_recorded_endpoint(tmp_path):
    root = tmp_path / "runs" / "gw"
    manifest = {"args": {"gateway": True, "gateway_url": "http://localhost:4000"}, "budget_usd": 3.0}
    t = _fit_run(root, model="qwen3.5-397b-a17b", cond="A", manifest=manifest)
    run = {"transcript": t, "root": root, "model": "qwen3.5-397b-a17b", "cond": "A", "effort": "medium",
           "task": "P-closed_form-01", "k": "1"}
    text = reproduce.commands(run)
    assert "ANTHROPIC_BASE_URL=http://localhost:4000" in text and "academiccloud" not in text


def test_the_card_names_the_recorded_gateway(tmp_path):
    root = tmp_path / "runs" / "gw"
    _fit_run(root, model="qwen3.5-397b-a17b", cond="A",
             manifest={"args": {"gateway": True, "gateway_url": "http://localhost:4000"}, "budget_usd": 3.0})
    page, _ = gal.build_html([root], tmp_path / "runs")
    assert "gateway localhost:4000" in page and "chat-ai" not in page


def test_reproduce_slug_is_unique_per_cell_and_path_safe():
    a = reproduce.slug("P-x-01", "m/odel", "A", "medium", "k1")
    b = reproduce.slug("P-x-01", "m/odel", "B", "medium", "k1")
    assert a != b and "/" not in a and " " not in a


def test_reproduce_block_is_escaped_in_html(tmp_path):
    root = tmp_path / "runs" / "run"
    _fit_run(root, model="m<b>&", cond="B")
    page, _ = gal.build_html([root], tmp_path / "runs", make_figs=False)
    assert "<b>&" not in page and "m&lt;b&gt;&amp;" in page


def _fake_run_set(folder, model="claude-haiku-5-5", title=None):
    """A run set made with the fake claude (dry run of the real runner): MANIFEST.json, plan, transcripts."""
    from tsbench.run import runner
    runner.main(["--split", "pilot", "--models", model, "--conditions", "A,C", "--effort", "medium", "--k", "1",
                 "--budget-usd", "10", "--out", str(folder), "--dry-run", "--limit", "1"])
    if title:
        (folder / "run_set.json").write_text(json.dumps({"title": title}), encoding="utf-8")
    return folder


def test_cli_finds_every_run_set_below_the_runs_folder(tmp_path, capsys):
    """Two run sets made with the fake claude below one folder: --runs takes the folder, every run is a card."""
    root = tmp_path / "results"
    _fake_run_set(root / "first", title="First set <b>")
    _fake_run_set(root / "second" / "haiku")
    out = tmp_path / "site" / "gallery.html"
    capsys.readouterr()
    assert gal.main(["--runs", str(root), "--out", str(out), "--no-figures"]) == 0
    page = out.read_text(encoding="utf-8")
    counts = json.loads(capsys.readouterr().out.split("\n", 1)[1])
    assert counts["runs"] == 4 and "run set first" in page and "run set second/haiku" in page
    assert "from 2 run sets" in page and "file:" not in page and str(tmp_path) not in page


# ---------------------------------------------------------------- the page is a template
def test_page_comes_from_the_shared_base_template(tmp_path):
    root = tmp_path / "runs" / "run"
    _fit_run(root)
    markup, _ = gal.build_html([root], tmp_path / "runs", make_figs=False)
    assert markup.startswith("<!doctype html>") and page.CSP_META in markup
    assert markup.count('<meta http-equiv="Content-Security-Policy"') == 1
    assert "<title>Run gallery</title>" in markup and markup.count('id="jfs-lib"') == 1


def test_missing_vendor_js_raises_like_on_every_other_page(tmp_path, monkeypatch):
    root = tmp_path / "runs" / "run"
    _fit_run(root)

    def missing():
        raise FileNotFoundError("Figura JS not found")
    page.figura_js.cache_clear()
    monkeypatch.setattr(page, "find_js", missing)
    try:
        with pytest.raises(FileNotFoundError):
            gal.build_html([root], tmp_path / "runs", make_figs=False)
    finally:
        page.figura_js.cache_clear()


def test_page_data_is_never_marked_safe():
    template = (pathlib.Path(gal.__file__).parent / "templates").glob("gallery*.html.j2")
    for path in template:
        assert "|safe" not in path.read_text(encoding="utf-8").replace(" ", ""), path.name


def test_run_card_clones_hold_links_to_their_sources_until_the_script_replaces_them(tmp_path):
    """Without the script a run card's images and code are empty: each clone holds links to the cards it copies, and
    the styles hide them once the script runs (class js)."""
    root = tmp_path / "runs" / "run"
    t = _fit_run(root, manifest={"args": {"gateway": False}})
    (t.with_name("P-closed_form-01-k2.artifacts")).mkdir()
    (t.with_name("P-closed_form-01-k2.artifacts") / "plot.png").write_bytes(PNG_BYTES)
    page, _ = gal.build_html([root], tmp_path / "runs")
    clones = re.findall(r'<div class="clone" data-from="([^"]+)">(.*?)</div>', page, flags=re.S)
    assert clones
    for ids, inner in clones:
        for i in ids.split():
            assert f'href="#{i}"' in inner and f'id="{i}"' in page, i
    assert re.search(r"\.js\s+\.gallery\s+\.clone\s*>\s*\.dflt\s*\{[^}]*display:\s*none", page)


def test_gallery_figures_follow_the_page_theme_switch_not_only_the_system():
    css = (pathlib.Path(gal.__file__).parent / "templates" / "gallery.css").read_text(encoding="utf-8")
    assert re.search(r"prefers-color-scheme:\s*dark\)\s*\{\s*:root:not\(\[data-theme=[\"']?light[\"']?\]\)\s*"
                     r"\.gallery\s+\.figs\s+img\s*\{[^}]*invert", css)
    assert re.search(r":root\[data-theme=[\"']?dark[\"']?\]\s*\.gallery\s+\.figs\s+img\s*\{[^}]*invert", css)


# ---------------------------------------------------------------- page budget: figures and images share it
MATPLOTLIB_SVG = (
    '<?xml version="1.0" encoding="utf-8" standalone="no"?>\n'
    '<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN"\n  "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">\n'
    '<svg xmlns:xlink="http://www.w3.org/1999/xlink" width="20pt" height="10pt" viewBox="0 0 20 10"'
    ' xmlns="http://www.w3.org/2000/svg" version="1.1">\n'
    ' <metadata>\n  <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">Matplotlib v3</rdf:RDF>\n'
    ' </metadata>\n <defs>\n  <style type="text/css">*{stroke-linejoin: round}</style>\n </defs>\n'
    ' <g id="figure_1">\n  <path d="M 0 1 \nL 2 3 \nz\n" style="fill: #fff"/>\n'
    '  <text style="font-size: 6px; font-family: \'Arial\', \'Helvetica\', sans-serif; text-anchor: middle"'
    ' x="1" y="2" transform="rotate(-0 1 2)">a b</text>\n'
    '  <text style="font-size: 6px; font-family: \'Arial\', \'Helvetica\', sans-serif" x="3" y="4"'
    ' transform="rotate(-90 3 4)">c</text>\n </g>\n</svg>\n')


def test_minify_svg_drops_the_boilerplate_of_a_matplotlib_figure_and_keeps_the_drawing():
    import xml.etree.ElementTree as ET
    out = gal.minify_svg(MATPLOTLIB_SVG)
    assert len(out) < len(MATPLOTLIB_SVG) * 0.7
    assert "<?xml" not in out and "<metadata" not in out and "rdf" not in out and "Matplotlib" not in out
    assert "rotate(-0" not in out and "rotate(-90 3 4)" in out
    assert out.count("font-family") == 1  # said once for all texts, not once per <text>
    assert ">\n" not in out and "> <" not in out
    root = ET.fromstring(out)
    texts = [e.text for e in root.iter("{http://www.w3.org/2000/svg}text")]
    assert texts == ["a b", "c"]
    assert "font-family: 'Arial'" in out or "font-family:'Arial'" in out.replace(" ", "")


def test_figure_data_uri_is_percent_encoded_not_base64(tmp_path):
    p = tmp_path / "f.svg"
    p.write_text(MATPLOTLIB_SVG, encoding="utf-8")
    uri = gal.figure_data_uri(p)
    assert uri is not None
    assert uri.startswith("data:image/svg+xml,%3Csvg") and ";base64" not in uri
    assert '"' not in uri and "<" not in uri and "#" not in uri.split(",", 1)[1].replace("%23", "")
    assert len(uri) < len(base64.b64encode(MATPLOTLIB_SVG.encode())) * 0.6


def _two_models(root):
    t1 = _fit_run(root, model="claude-opus-5-5")
    t2 = _fit_run(root, model="claude-sonnet-5-5")
    return t1, t2


def test_run_figures_count_against_the_page_budget_and_are_linked_beyond_it(tmp_path, monkeypatch):
    root = tmp_path / "runs" / "run"
    t = _fit_run(root)
    monkeypatch.setattr(gal, "PAGE_BUDGET", 0)
    page, counts = gal.build_html([root], tmp_path / "runs")
    assert counts["figures"] == 2 and counts["figures_embedded"] == 0 and counts["figures_linked"] == 2
    assert not re.search(r'<img[^>]+src="data:image/svg', page)
    figdir = t.with_name("P-closed_form-01-k2.figs").relative_to(tmp_path / "runs").as_posix()
    assert f'href="{figdir}/fit_error.svg"' in page and f'href="{figdir}/metrics.svg"' in page
    assert not re.search(r'<img[^>]+src="(?!data:)', page)


def test_figures_and_images_share_one_budget_smallest_first(tmp_path, monkeypatch):
    root = tmp_path / "runs" / "run"
    _fit_run(root)
    monkeypatch.setattr(gal, "_weight", lambda data: 0)
    _, whole = gal.build_html([root], tmp_path / "runs")
    assert whole["figures_embedded"] == 2
    sizes = {}
    for name in ("fit_error", "metrics"):
        uri = gal.figure_data_uri(next(root.rglob(f"{name}.svg")))
        assert uri is not None
        sizes[name] = len(uri)
    small, big = sorted(sizes.values())
    assert small < big
    monkeypatch.setattr(gal, "PAGE_BUDGET", 900_000 + small + 10)
    page, counts = gal.build_html([root], tmp_path / "runs")
    assert counts["figures_embedded"] == 1 and counts["figures_linked"] == 1
    assert len(re.findall(r'<img[^>]+src="data:image/svg\+xml,', page)) == 1


def test_a_second_model_cannot_push_the_figures_over_the_budget(tmp_path, monkeypatch):
    root = tmp_path / "runs" / "run"
    _two_models(root)
    monkeypatch.setattr(gal, "PAGE_BUDGET", 1)
    _, counts = gal.build_html([root], tmp_path / "runs")
    assert counts["figures"] == 4 and counts["figures_embedded"] == 0 and counts["figures_linked"] == 4


def test_byte_identical_figures_are_embedded_once_and_cloned_by_id(tmp_path):
    root = tmp_path / "runs" / "run"
    _two_models(root)
    page, counts = gal.build_html([root], tmp_path / "runs")
    uris = re.findall(r'<img id="(fg-\d+)"[^>]+src="(data:image/svg\+xml,[^"]+)"', page)
    assert len(uris) == len({u for _, u in uris}) == counts["figures_unique"]
    assert counts["figures"] == 4 and counts["figures_unique"] < 4
    clones = re.findall(r'class="clone" data-from="(fg-\d+)"', page)
    assert len(clones) == 4 - counts["figures_unique"]
    assert set(clones) <= {i for i, _ in uris}
    assert len(re.findall(r'src="data:image/svg\+xml,', page)) == counts["figures_unique"]


def test_a_big_raster_image_is_not_downscaled_when_the_budget_cannot_hold_it(tmp_path, monkeypatch):
    root = tmp_path / "runs" / "run"
    d = _run(root)
    art = d / "P-diagram-01-k1.artifacts"
    art.mkdir()
    (art / "diagram.png").write_bytes(PNG_BYTES)
    calls = []
    monkeypatch.setattr(gal, "_downscale", lambda data, mime: calls.append(len(data)) or (data, mime))
    monkeypatch.setattr(gal, "PAGE_BUDGET", 0)
    monkeypatch.setattr(gal, "EMBED_LIMIT", 10)
    _, counts = gal.build_html([root], tmp_path / "runs")
    assert calls == [] and counts["linked"] >= 1


def test_a_big_raster_image_is_downscaled_when_it_can_still_fit(tmp_path, monkeypatch):
    root = tmp_path / "runs" / "run"
    d = _run(root)
    art = d / "P-diagram-01-k1.artifacts"
    art.mkdir()
    (art / "diagram.png").write_bytes(PNG_BYTES)
    calls = []
    monkeypatch.setattr(gal, "_downscale", lambda data, mime: calls.append(len(data)) or (data[:20], mime))
    monkeypatch.setattr(gal, "EMBED_LIMIT", 10)
    _, counts = gal.build_html([root], tmp_path / "runs")
    assert len(calls) == 1 and counts["embedded"] >= 1
