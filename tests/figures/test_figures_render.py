"""Unit tests of `tsbench.figures.render`: style, export, source csv, provenance and the golden check."""
from __future__ import annotations

import datetime
import hashlib
import json
import pathlib
import platform
import re
import subprocess
from types import SimpleNamespace
from typing import cast

import matplotlib
import numpy
import pytest
from matplotlib.figure import Figure

from tsbench.core.intervals import RESAMPLES, SEED
from tsbench.figures import data, render
from tsbench.figures.render import Built, Context

EPOCH = "1700000000"  # 2023-11-14T22:13:20Z
JFS = SimpleNamespace(COLORS={"series-1": "#111111", "series-2": "#222222", "series-3": "#333333"})


def _row(model="m", cond="A", task="T1", k=1, ok=True, evaluable=True, set_name="s"):
    return {"set": set_name, "model": model, "condition": cond, "effort": "medium", "task_id": task, "k_index": k,
            "correct": ok, "evaluable": evaluable}


def _set(name="s", rows=None, **kw):
    return data.RunSet(path=pathlib.Path("."), name=name, rows=rows or [], **kw)


def _fig(w_in=4.0, h_in=3.0, **kw):
    return Figure(figsize=(w_in, h_in), **kw)


# ------------------------------------------------------------------------------------------------ constants
def test_constants():
    assert render.STATUS == "pilot"
    assert render.OUTPUT_SUFFIXES == (".pdf", ".svg", ".tif", ".png")
    assert render.VECTOR_SUFFIXES == (".pdf", ".svg")
    assert render.SVG_HASHSALT == "benchmark-figures"
    assert render.VOLATILE_KEYS == ("generated_utc", "git", "versions.python")
    assert (render.FIGURA / "jfs.mplstyle").is_file() and (render.FIGURA / "jfs.py").is_file()


# ------------------------------------------------------------------------------------------------ build_time
@pytest.mark.parametrize("env,expected", [
    (None, "1970-01-01T00:00:00"), (EPOCH, "2023-11-14T22:13:20"), ("0", "1970-01-01T00:00:00"),
    ("86400", "1970-01-02T00:00:00"), ("", "1970-01-01T00:00:00"), ("abc", "1970-01-01T00:00:00"),
    ("1.5", "1970-01-01T00:00:00"), ("-5", "1969-12-31T23:59:55")])
def test_build_time(monkeypatch, env, expected):
    if env is None:
        monkeypatch.delenv("SOURCE_DATE_EPOCH", raising=False)
    else:
        monkeypatch.setenv("SOURCE_DATE_EPOCH", env)
    got = render.build_time()
    assert got.isoformat() == expected + "+00:00"
    assert got.tzinfo is datetime.UTC


# ------------------------------------------------------------------------------------------------ Context / Built
def test_context_pools_the_rows_of_its_sets():
    a = _set("a", [_row(task="T1"), _row(task="T2", evaluable=False)])
    b = _set("b", [_row(task="T1", set_name="b"), _row(task="T3", set_name="b")])
    ctx = Context(sets=[a, b])
    assert [r["task_id"] for r in ctx.rows] == ["T1", "T3"]
    assert ctx.n_repeats == 1
    assert (ctx.theme, ctx.ci, ctx.footer) == ("neutral", "wilson", True)
    other = Context(sets=[], theme="contrast", ci="bootstrap", footer=False)
    assert (other.theme, other.ci, other.footer, other.rows, other.n_repeats) == ("contrast", "bootstrap", False, [], 0)


def test_built_defaults_are_not_shared():
    a, b = Built(None, ["c"], [], "cap"), Built(None, ["c"], [], "cap")
    assert (a.notes, a.ci) == ([], {})
    a.notes.append("x")
    a.ci["k"] = 1
    assert (b.notes, b.ci) == ([], {})
    c = Built("fig", ["x"], [{"x": 1}], "cap", notes=["n"], ci={"method": "m"})
    assert (c.fig, c.columns, c.source, c.caption, c.notes, c.ci) == ("fig", ["x"], [{"x": 1}], "cap", ["n"],
                                                                      {"method": "m"})


# ------------------------------------------------------------------------------------------------ style
def test_setup_returns_pyplot_and_jfs_with_the_theme_applied(contrast_theme):
    plt, jfs = render.setup()
    assert plt.__name__ == "matplotlib.pyplot" and jfs.__name__ == "tsbench._vendor.figura.jfs"
    assert jfs.COLORS["series-1"] == "#0039a6"  # the default theme is neutral
    assert plt.rcParams["text.color"] == "#1a1a1a"
    assert matplotlib.get_backend().lower() == "agg"
    assert plt.rcParams["svg.hashsalt"] == "benchmark-figures"
    assert plt.rcParams["font.size"] == 7 and plt.rcParams["axes.linewidth"] == 0.5  # the jfs.mplstyle values
    assert plt.rcParams["font.family"] == ["sans-serif"] and plt.rcParams["mathtext.fontset"] == "custom"
    _plt, jfs = render.setup(contrast_theme)
    assert jfs.COLORS["series-1"] == "#006699" and plt.rcParams["text.color"] == "#222222"
    assert plt.rcParams["axes.prop_cycle"].by_key()["color"][0] == "#006699"
    render.setup()
    assert plt.rcParams["axes.prop_cycle"].by_key()["color"][:2] == ["#0039a6", "#b07800"]


def test_condition_style_pairs_a_series_colour_with_a_marker():
    assert render.condition_style(JFS) == {"A": ("#111111", "o"), "B": ("#222222", "s"), "C": ("#333333", "^")}


def test_condition_key_writes_three_coloured_labels_in_one_line():
    fig = _fig(4.0, 3.0)  # 288 x 216 pt
    assert render.condition_key(fig, JFS) is fig
    texts = fig.texts
    assert [t.get_text() for t in texts] == ["A  no tools", "B  Bash", "C  TS-MCP"]
    assert [t.get_gid() for t in texts] == ["key:A", "key:B", "key:C"]
    assert [t.get_color() for t in texts] == ["#111111", "#222222", "#333333"]
    assert all(t.get_fontsize() == 6 and t.get_fontweight() == "bold" for t in texts)
    assert all(t.get_va() == "center" and t.get_ha() == "left" for t in texts)
    assert [t.get_position()[1] for t in texts] == pytest.approx([1 - 5.0 / 216] * 3)
    x1 = 0.02 + (len("A  no tools") * 3.6 + 14) / 288
    x2 = x1 + (len("B  Bash") * 3.6 + 14) / 288
    assert [t.get_position()[0] for t in texts] == pytest.approx([0.02, x1, x2])


def test_condition_key_honours_its_start_and_height():
    fig = _fig(2.0, 1.0)  # 144 x 72 pt
    render.condition_key(fig, JFS, 0.1, 0.5)
    assert [t.get_position() for t in fig.texts][0] == (0.1, 0.5)
    assert fig.texts[1].get_position()[0] == pytest.approx(0.1 + (11 * 3.6 + 14) / 144)
    assert {t.get_position()[1] for t in fig.texts} == {0.5}
    fig = _fig(2.0, 1.0)
    render.condition_key(fig, JFS, y=0.0)  # an explicit zero is a position, not "unset"
    assert {t.get_position()[1] for t in fig.texts} == {0.0}


def test_reserve_leaves_room_for_footer_and_key():
    for footer, key, bottom_pt, top_pt in [(True, True, 9.0, 10.0), (True, False, 9.0, 0.0),
                                           (False, True, 0.0, 10.0), (False, False, 0.0, 0.0)]:
        fig = _fig(3.0, 2.0, layout="constrained")  # 144 pt high
        render.reserve(fig, footer, key)
        bottom, top = bottom_pt / 144, 1 - top_pt / 144
        assert fig.get_layout_engine().get()["rect"] == pytest.approx((0, bottom, 1, top - bottom))
    fig = _fig(3.0, 2.0, layout="constrained")
    render.reserve(fig, True)  # the key is on by default
    assert fig.get_layout_engine().get()["rect"] == pytest.approx((0, 9 / 144, 1, 1 - 10 / 144 - 9 / 144))


def test_footer_text_sits_at_the_bottom_left():
    fig = _fig(4.0, 3.0)
    t = render.footer_text(fig, "Pilot data")
    assert t in fig.texts and t.get_text() == "Pilot data" and t.get_gid() == "footer"
    assert t.get_position() == pytest.approx((0.005, 2.0 / 216))
    assert (t.get_fontsize(), t.get_color(), t.get_ha(), t.get_va()) == (5, "#4d4d4d", "left", "bottom")


# ------------------------------------------------------------------------------------------------ csv
@pytest.mark.parametrize("value,text", [
    (None, ""), (True, "True"), (False, "False"), (0.5, "0.5"), (float("nan"), ""), (1 / 3, "0.3333333333"),
    (2 / 3, "0.6666666667"), (1e-12, "1e-12"), (123456789012.0, "1.23456789e+11"), (0.1 + 0.2, "0.3"),
    (float("inf"), "inf"), (-0.0, "-0"), (5, "5"), (0, "0"), ("text", "text"), ("", ""), (1.0, "1"),
    (12345.678901234, "12345.6789"), (1e20, "1e+20"), (1e-5, "1e-05")])
def test_format_float(value, text):
    assert render.format_float(value) == text


def test_write_source_writes_columns_in_order_and_returns_the_sha(tmp_path):
    p = tmp_path / "x.source.csv"
    rows = [{"a": 1, "b": 0.25, "c": True, "z": "ignored"}, {"a": "x,y", "b": None, "c": False},
            {"a": "café", "b": float("nan")}]
    sha = render.write_source(p, ["c", "a", "b"], rows)
    raw = p.read_bytes()
    assert raw == 'c,a,b\nTrue,1,0.25\nFalse,"x,y",\n,café,\n'.encode()
    assert sha == hashlib.sha256(raw).hexdigest()
    assert b"\r" not in raw
    assert render.write_source(p, ["a"], []) == hashlib.sha256(b"a\n").hexdigest()
    assert p.read_bytes() == b"a\n"


def test_write_source_keeps_a_line_break_in_a_cell(tmp_path, text_io_is_utf8):
    p = tmp_path / "x.csv"
    render.write_source(p, ["t"], [{"t": "a\r\nb"}])
    assert p.read_bytes() == b't\n"a\r\nb"\n'
    assert ("open(x.csv)", "utf-8") in text_io_is_utf8


# ------------------------------------------------------------------------------------------------ git and hashes
def test_git_info_asks_git_for_head_and_for_tracked_changes(monkeypatch):
    calls = []

    def fake_run(cmd, **kw):
        calls.append((cmd, kw))
        out = "abc123\n" if cmd[1] == "rev-parse" else " M file.py\n"
        return SimpleNamespace(stdout=out)

    monkeypatch.setattr(render.subprocess, "run", fake_run)
    assert render.git_info() == {"commit": "abc123", "dirty": True}
    assert [c for c, _kw in calls] == [["git", "rev-parse", "HEAD"], ["git", "status", "--porcelain",
                                                                        "--untracked-files=no"]]
    for _cmd, kw in calls:
        assert kw == {"cwd": data.REPO_ROOT, "capture_output": True, "encoding": "utf-8", "timeout": 30}


def test_git_info_clean_tree_and_no_commit(monkeypatch):
    monkeypatch.setattr(render.subprocess, "run", lambda cmd, **kw: SimpleNamespace(stdout="  \n"))
    assert render.git_info() == {"commit": None, "dirty": False}
    outs = iter(["deadbeef\n", ""])
    monkeypatch.setattr(render.subprocess, "run", lambda cmd, **kw: SimpleNamespace(stdout=next(outs)))
    assert render.git_info() == {"commit": "deadbeef", "dirty": False}


@pytest.mark.parametrize("exc", [FileNotFoundError("no git"), subprocess.TimeoutExpired("git", 30),
                                 subprocess.CalledProcessError(1, "git")])
def test_git_info_without_git(monkeypatch, exc):
    def boom(*_a, **_k):
        raise exc

    monkeypatch.setattr(render.subprocess, "run", boom)
    assert render.git_info() == {"commit": None, "dirty": None}


def test_git_info_of_this_checkout():
    info = render.git_info()
    assert set(info) == {"commit", "dirty"}
    assert re.fullmatch(r"[0-9a-f]{40}", info["commit"]) and isinstance(info["dirty"], bool)


def test_task_hashes_keep_the_pilot_and_whole_file_digests_only(tmp_path, monkeypatch):
    f = tmp_path / "tasks.sha256"
    f.write_text("aaa  tasks.jsonl\nbbb  pilot\nccc  confirmatory\nddd\neee tasks.jsonl\nfff  other.txt\n"
                 "ggg  pilot  tasks.jsonl\n",
                 encoding="utf-8")
    from tsbench import tasks
    monkeypatch.setattr(tasks, "hash_path", lambda: f)
    assert render.task_hashes() == {"tasks.jsonl": "aaa", "pilot": "bbb"}


def test_task_hashes_of_the_pinned_task_set():
    from tsbench.tasks import hash_path
    got = render.task_hashes()
    assert set(got) == {"tasks.jsonl", "pilot"}
    assert all(re.fullmatch(r"[0-9a-f]{64}", v) for v in got.values())
    lines = hash_path().read_text(encoding="utf-8").splitlines()
    assert f"{got['pilot']}  pilot" in lines and f"{got['tasks.jsonl']}  tasks.jsonl" in lines


# ------------------------------------------------------------------------------------------------ provenance
def _ctx_for_provenance():
    s1 = _set("one", [_row(), _row(task="T2", evaluable=False)], title="First", source="scores.csv",
              scores_sha256="f" * 64, live=True, dropped_non_pilot=3, skipped_incomplete=2, notes=["n1"])
    s2 = _set("two", [_row(task="T3", set_name="two"), _row(task="T1", set_name="two")], title="Second")
    return Context(sets=[s1, s2], theme="contrast")


def test_footer_line_counts_runs_and_sets():
    ctx = SimpleNamespace(rows=[1, 2, 3], sets=[1, 2])
    assert render.footer_line(cast(Context, ctx)) == ("Pilot data, not confirmatory: 3 runs from 2 run sets "
                                       "(HTTP 429 / API errors excluded).")


def test_provenance_records_everything_that_made_the_figure(monkeypatch):
    monkeypatch.setattr(render, "git_info", lambda: {"commit": "c0ffee", "dirty": False})
    monkeypatch.setattr(render, "task_hashes", lambda: {"pilot": "p" * 64})
    ctx = _ctx_for_provenance()
    built = Built(None, ["a"], [], "The caption", notes=["note 1"], ci={"method": "m", "unit": "run"})
    now = datetime.datetime(2024, 2, 29, 13, 5, 9, tzinfo=datetime.UTC)
    prov = render.provenance("figX", ctx, built, ["figX.pdf"], "s" * 64, now)
    assert prov == {
        "figure": "figX", "status": "pilot", "caption": "The caption",
        "footer": "Pilot data, not confirmatory: 2 runs from 2 run sets (HTTP 429 / API errors excluded).",
        "git": {"commit": "c0ffee", "dirty": False},
        "run_sets": [
            {"name": "one", "title": "First", "source": "scores.csv", "scores_csv_sha256": "f" * 64, "n_rows": 2,
             "n_evaluable": 1, "live_run": True, "dropped_non_pilot_rows": 3, "skipped_incomplete_transcripts": 2,
             "notes": ["n1"]},
            {"name": "two", "title": "Second", "source": "rescored", "scores_csv_sha256": None, "n_rows": 2,
             "n_evaluable": 2, "live_run": False, "dropped_non_pilot_rows": 0, "skipped_incomplete_transcripts": 0,
             "notes": []}],
        "task_set": {"pilot": "p" * 64},
        "pooling": {"n_runs_used": 2, "repeated_keys_dropped": 1, "not_evaluable_excluded": 1},
        "ci": {"method": "m", "unit": "run"},
        "notes": ["note 1"], "theme": "contrast", "fonts": "Arial-compatible sans-serif stack; PDF fonttype 42",
        "versions": {"matplotlib": matplotlib.__version__, "numpy": numpy.__version__,
                     "python": platform.python_version()},
        "outputs": ["figX.pdf"], "source_csv_sha256": "s" * 64, "generated_utc": "2024-02-29T13:05:09Z"}


def test_provenance_declares_the_bootstrap_only_for_a_figure_that_used_it(monkeypatch):
    monkeypatch.setattr(render, "git_info", lambda: {})
    monkeypatch.setattr(render, "task_hashes", lambda: {})
    ctx = Context(sets=[])
    boot = {"method": "task-clustered percentile bootstrap, 95 %", "unit": "task, k repetitions kept together"}
    used = render.provenance("f", ctx, Built(None, [], [], "c", ci=boot), [], "x")
    assert used["bootstrap"] == {"seed": SEED, "resamples": RESAMPLES, "unit": "task (k repetitions kept together)"}
    for ci in ({}, {"method": "Wilson score interval, 95 %", "unit": "run"}):
        assert "bootstrap" not in render.provenance("f", ctx, Built(None, [], [], "c", ci=ci), [], "x")


def test_provenance_date_follows_source_date_epoch_else_the_clock(monkeypatch):
    monkeypatch.setattr(render, "git_info", lambda: {})
    monkeypatch.setattr(render, "task_hashes", lambda: {})
    ctx, built = Context(sets=[]), Built(None, [], [], "c")
    monkeypatch.setenv("SOURCE_DATE_EPOCH", EPOCH)
    assert render.provenance("f", ctx, built, [], "x")["generated_utc"] == "2023-11-14T22:13:20Z"
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "0")
    assert render.provenance("f", ctx, built, [], "x")["generated_utc"] == "1970-01-01T00:00:00Z"
    monkeypatch.delenv("SOURCE_DATE_EPOCH")
    before = datetime.datetime.now(datetime.UTC).replace(microsecond=0)
    stamp = render.provenance("f", ctx, built, [], "x")["generated_utc"]
    got = datetime.datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.UTC)
    assert before <= got <= before + datetime.timedelta(seconds=30)


# ------------------------------------------------------------------------------------------------ save / export
def test_save_writes_pdf_svg_tif_png_with_pinned_metadata(tmp_path, monkeypatch):
    import matplotlib.pyplot as plt
    from PIL import Image
    monkeypatch.setenv("SOURCE_DATE_EPOCH", EPOCH)
    monkeypatch.setitem(plt.rcParams, "savefig.dpi", 123)  # the resolutions are set by the call, not by the style
    fig = _fig(2.0, 1.0)
    fig.text(0.5, 0.5, "x")
    stem = str(tmp_path / "f")
    assert render.save(fig, stem) == [".pdf", ".svg", ".tif", ".png"]
    assert sorted(p.name for p in tmp_path.iterdir()) == ["f.pdf", "f.png", "f.svg", "f.tif"]
    pdf = (tmp_path / "f.pdf").read_bytes()
    assert re.search(rb"/CreationDate \(D:20231114221320", pdf) and re.search(rb"/ModDate \(D:20231114221320", pdf)
    assert "<dc:date>2023-11-14T22:13:20Z</dc:date>" in (tmp_path / "f.svg").read_text(encoding="utf-8")
    with Image.open(tmp_path / "f.tif") as im:
        assert im.size == (1200, 600) and round(im.info["dpi"][0]) == 600 and im.info["compression"] == "tiff_lzw"
    with Image.open(tmp_path / "f.png") as im:
        assert im.size == (600, 300) and round(im.info["dpi"][0]) == 300
        assert "Software" not in im.info and not getattr(im, "text", {})
    mediabox = re.search(rb"/MediaBox\s*\[\s*0\s+0\s+([\d.]+)\s+([\d.]+)\s*\]", pdf)
    assert mediabox is not None
    assert (float(mediabox[1]), float(mediabox[2])) == (144.0, 72.0)  # the page is the figure, never cropped


def test_save_vector_only_and_default_raster(tmp_path):
    fig = _fig(2.0, 1.0)
    assert render.save(fig, str(tmp_path / "v"), raster=False) == [".pdf", ".svg"]
    assert sorted(p.name for p in tmp_path.iterdir()) == ["v.pdf", "v.svg"]
    assert render.save(fig, str(tmp_path / "r"), True) == [".pdf", ".svg", ".tif", ".png"]
    assert (tmp_path / "r.tif").is_file() and (tmp_path / "r.png").is_file()


def test_save_dates_default_to_the_epoch(tmp_path, monkeypatch):
    monkeypatch.delenv("SOURCE_DATE_EPOCH", raising=False)
    render.save(_fig(2.0, 1.0), str(tmp_path / "e"), raster=False)
    pdf = (tmp_path / "e.pdf").read_bytes()
    assert re.search(rb"/CreationDate \(D:19700101000000", pdf) and re.search(rb"/ModDate \(D:19700101000000", pdf)
    assert "<dc:date>1970-01-01T00:00:00Z</dc:date>" in (tmp_path / "e.svg").read_text(encoding="utf-8")


def _built():
    fig = _fig(2.0, 1.0)
    fig.text(0.5, 0.5, "x")
    return Built(fig, ["k", "v"], [{"k": "a", "v": 1.5}, {"k": "b", "v": None}], "Caption ± text",
                 notes=["n"], ci={"method": "m"})


def test_export_writes_every_file_and_returns_the_provenance(tmp_path, monkeypatch):
    import matplotlib.pyplot as plt
    monkeypatch.setenv("SOURCE_DATE_EPOCH", EPOCH)
    monkeypatch.setattr(render, "git_info", lambda: {"commit": None, "dirty": None})
    out = tmp_path / "deep" / "out"
    ctx = Context(sets=[_set("s", [_row()])])
    prov = render.export("figX", _built(), ctx, out)
    assert sorted(p.name for p in out.iterdir()) == ["figX.json", "figX.pdf", "figX.png", "figX.source.csv",
                                                     "figX.svg", "figX.tif"]
    assert (out / "figX.source.csv").read_text(encoding="utf-8") == "k,v\na,1.5\nb,\n"
    sha = hashlib.sha256((out / "figX.source.csv").read_bytes()).hexdigest()
    assert prov["source_csv_sha256"] == sha
    assert prov["outputs"] == ["figX.pdf", "figX.svg", "figX.tif", "figX.png", "figX.source.csv"]
    assert prov["generated_utc"] == "2023-11-14T22:13:20Z" and prov["figure"] == "figX"
    text = (out / "figX.json").read_text(encoding="utf-8")
    assert json.loads(text) == prov
    assert text == json.dumps(prov, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    assert "Caption ± text" in text
    assert plt.get_fignums() == []  # the figure is closed after saving


def test_export_closes_the_figure_it_drew_and_no_other(tmp_path, monkeypatch):
    import matplotlib.pyplot as plt
    monkeypatch.setattr(render, "git_info", lambda: {})
    plt.close("all")
    drawn, other = plt.figure(), plt.figure()  # `other` is the current figure
    built = Built(drawn, ["k"], [], "cap")
    render.export("figZ", built, Context(sets=[]), tmp_path / "o", raster=False)
    assert plt.get_fignums() == [other.number]
    plt.close("all")


def test_export_without_raster_still_lists_the_full_set(tmp_path, monkeypatch):
    monkeypatch.setattr(render, "git_info", lambda: {})
    out = tmp_path / "o"
    prov = render.export("figY", _built(), Context(sets=[]), out, raster=False)
    assert sorted(p.name for p in out.iterdir()) == ["figY.json", "figY.pdf", "figY.source.csv", "figY.svg"]
    assert prov["outputs"] == ["figY.pdf", "figY.svg", "figY.tif", "figY.png", "figY.source.csv"]
    assert prov["theme"] == "neutral"


def test_export_draws_with_the_theme_of_the_context(tmp_path, monkeypatch, contrast_theme):
    monkeypatch.setattr(render, "git_info", lambda: {})
    import matplotlib.pyplot as plt
    _plt, jfs = render.setup("neutral")
    render.export("figT", _built(), Context(sets=[], theme=contrast_theme), tmp_path / "o", raster=False)
    assert jfs.COLORS["series-1"] == "#006699"
    assert plt.rcParams["text.color"] == "#222222"


# ------------------------------------------------------------------------------------------------ golden check
def test_drop_removes_a_dotted_key():
    d = {"a": 1, "b": {"c": 2, "d": {"e": 3, "f": 4}}, "g.h": 5}
    render._drop(d, "a")
    assert d == {"b": {"c": 2, "d": {"e": 3, "f": 4}}, "g.h": 5}
    render._drop(d, "b.d.e")
    assert d == {"b": {"c": 2, "d": {"f": 4}}, "g.h": 5}
    render._drop(d, "b.c")
    assert d == {"b": {"d": {"f": 4}}, "g.h": 5}
    render._drop(d, "x.y")  # absent branch
    render._drop(d, "b.d.f.z")  # a leaf is not descended into
    render._drop(d, "nothing")
    assert d == {"b": {"d": {"f": 4}}, "g.h": 5}
    render._drop(d, "b.d.f.z.y")
    assert d == {"b": {"d": {"f": 4}}, "g.h": 5}
    render._drop(d, "b.d")
    assert d == {"b": {}, "g.h": 5}
    e = {"x": {"y": {"z": 1}}, "y": 7}
    render._drop(e, "x.y.z")
    assert e == {"x": {"y": {}}, "y": 7}
    assert render._drop({"a": 1}, "a") is None


def _provenance_file(path: pathlib.Path, **over):
    doc = {"generated_utc": "t", "git": {"commit": "c"}, "versions": {"python": "3.12", "numpy": "2"}, "figure": "f",
           "caption": "cap", **over}
    path.write_text(json.dumps(doc), encoding="utf-8")


def test_stable_provenance_drops_the_volatile_keys_only(tmp_path):
    p = tmp_path / "x.json"
    _provenance_file(p)
    assert render.stable_provenance(p) == {"versions": {"numpy": "2"}, "figure": "f", "caption": "cap"}
    _provenance_file(p, versions={"python": "3.13"})
    assert render.stable_provenance(p) == {"versions": {}, "figure": "f", "caption": "cap"}


def _golden_pair(tmp_path, names=("f1",)):
    out, gold = tmp_path / "out", tmp_path / "gold"
    for d in (out, gold):
        d.mkdir()
        for n in names:
            (d / f"{n}.source.csv").write_text("a,b\n1,2\n", encoding="utf-8")
            _provenance_file(d / f"{n}.json")
    return out, gold


def test_check_of_identical_outputs_is_empty(tmp_path):
    out, gold = _golden_pair(tmp_path, ("f1", "f2"))
    _provenance_file(out / "f1.json", generated_utc="other", git={"commit": "d"}, versions={"python": "3.9",
                                                                                           "numpy": "2"})
    assert render.check(["f1", "f2"], out, gold) == []
    assert render.check([], out, gold) == []


def test_check_reports_each_difference_by_file(tmp_path):
    out, gold = _golden_pair(tmp_path, ("f1", "f2", "f3"))
    (out / "f1.source.csv").write_text("a,b\n1,3\n", encoding="utf-8")
    _provenance_file(out / "f2.json", caption="changed", extra=1)
    (gold / "f3.source.csv").unlink()
    (out / "f3.source.csv").unlink()
    assert render.check(["f1", "f2", "f3"], out, gold) == [
        "f1.source.csv: differs", "f2.json: differs in caption, extra", "f3.source.csv: no golden file"]


def test_check_a_missing_output_csv_differs(tmp_path):
    out, gold = _golden_pair(tmp_path)
    (out / "f1.source.csv").unlink()
    assert render.check(["f1"], out, gold) == ["f1.source.csv: differs"]


def test_check_without_a_golden_json_goes_on_with_the_next_figure(tmp_path):
    out, gold = _golden_pair(tmp_path, ("f1", "f2"))
    (gold / "f1.json").unlink()
    _provenance_file(out / "f2.json", caption="changed")
    (out / "f2.source.csv").write_text("x\n", encoding="utf-8")
    assert render.check(["f1", "f2"], out, gold) == [
        "f1.json: no golden file", "f2.source.csv: differs", "f2.json: differs in caption"]


def test_check_names_keys_that_one_side_lacks(tmp_path):
    out, gold = _golden_pair(tmp_path)
    _provenance_file(gold / "f1.json", only_gold=1)
    _provenance_file(out / "f1.json", only_out=1)
    assert render.check(["f1"], out, gold) == ["f1.json: differs in only_gold, only_out"]
    d = json.loads((out / "f1.json").read_text(encoding="utf-8"))
    assert "only_out" in d


def test_check_compares_the_csv_bytes_not_the_text(tmp_path):
    out, gold = _golden_pair(tmp_path)
    (out / "f1.source.csv").write_bytes(b"a,b\r\n1,2\r\n")
    assert render.check(["f1"], out, gold) == ["f1.source.csv: differs"]
