"""Unit tests of `tsbench.figures.listing` (the code_listing figure): the line helpers, the transcript picker and the
drawn listing."""
from __future__ import annotations

import json
import pathlib
from typing import Any, cast

import matplotlib.pyplot as plt
import pytest
from matplotlib.figure import Figure

from tsbench.figures import data, listing
from tsbench.figures.render import Context

STEP = 0.9 / (listing.MAX_LINES + 1)


@pytest.fixture(autouse=True)
def _close_figures():
    yield
    plt.close("all")


def _fig(built) -> Figure:
    """The figure of a `Built` (typed `object` there, as the builders may return any backend's figure)."""
    return cast(Figure, built.fig)


# ------------------------------------------------------------------------------------------------ line helpers
def test_constants():
    assert (listing.MAX_LINES, listing.MAX_CHARS) == (15, 60)


@pytest.mark.parametrize("text,expected", [
    ("a\tb", "a    b"), ("\tx", "    x"), ("plain", "plain"), ("", ""),
    ("cd /home/alice/proj && ls", "cd ~/proj && ls"), ("/Users/bob/data.csv", "~/data.csv"),
    ("open('/home/carol/x.txt')", "open('~/x.txt')"), ('"/home/dave/a b"', '"~/a b"'),
    ("/home/erin", "~"), ("/homes/frank/x", "/homes/frank/x"), ("/root/x", "/root/x"), ("/home/", "/home/"),
    ("/home/a/b /Users/c/d", "~/b ~/d"), ("café", "café"), ("→ x", "? x"), ("a±b", "a±b"),
    ("中文", "??"), ("x€y", "x?y"),
])
def test_clean(text, expected):
    assert listing._clean(text) == expected


@pytest.mark.parametrize("text,expected", [
    ("abc   ", "abc"), ("  abc", "  abc"), ("a" * 60, "a" * 60), ("a" * 61, "a" * 57 + "..."),
    ("a" * 200, "a" * 57 + "..."), ("b" * 59, "b" * 59), ("x" * 60 + "   ", "x" * 60), ("", ""),
    ("\tx", "    x"), ("→" * 70, "?" * 57 + "..."), ("/home/zed/" + "q" * 70, "~/" + "q" * 55 + "..."),
])
def test_clip(text, expected):
    assert listing._clip(text) == expected
    assert len(listing._clip(text)) <= 60


def test_compact_json():
    got = listing._compact({"b": 1, "a": [1, 2], "c": {"z": None, "y": "s"}})
    assert got == '{"a":[1,2],"b":1,"c":{"y":"s","z":null}}'
    assert listing._compact("café ±") == '"café ±"'
    assert listing._compact(None) == "null"
    assert listing._compact([1, "a", True]) == '[1,"a",true]'
    assert listing._compact(1.5) == "1.5"


def _use(name, **inp):
    return {"type": "tool_use", "name": name, "input": inp}


def test_mcp_lines_one_line_per_mcp_call_with_sorted_arguments():
    uses = [_use("Bash", command="ls"), {"name": "Read"}, {"input": {"a": 1}},
            _use("mcp__ts__fit", geometry="Oh", bands=[1, 2]), _use("mcp__ts__energies"),
            _use("mcp__a__b__deep", z=None, a="x")]
    assert listing.mcp_lines(uses) == ['fit(bands=[1,2], geometry="Oh")', "energies()", 'deep(a="x", z=null)']


def test_mcp_lines_edge_cases():
    assert listing.mcp_lines([]) == []
    assert listing.mcp_lines([_use("Bash"), _use("mcp_single__x")]) == []
    assert listing.mcp_lines([{"name": "mcp__s__t", "input": ["not", "a", "dict"]}]) == ["t()"]
    assert listing.mcp_lines([{"name": "mcp__s__t", "input": None}]) == ["t()"]
    assert listing.mcp_lines([{"name": "mcp__s__t"}]) == ["t()"]
    assert listing.mcp_lines([{"name": "mcp__"}]) == ["()"]
    assert listing.mcp_lines([{"name": "MCP__s__t"}]) == []
    assert listing.mcp_lines([{"name": 7}]) == []
    long = listing.mcp_lines([_use("mcp__s__tool", text="w" * 100)])
    assert len(long) == 1 and len(long[0]) == 60 and long[0].startswith('tool(text="www') and long[0].endswith("...")


def test_mcp_lines_stop_at_the_line_limit():
    uses = [_use("mcp__s__t", i=i) for i in range(40)]
    got = listing.mcp_lines(uses)
    assert got == [f"t(i={i})" for i in range(15)]
    assert isinstance(listing.mcp_lines(uses[:15]), list) and len(listing.mcp_lines(uses[:15])) == 15
    assert len(listing.mcp_lines(uses[:14])) == 14 and len(listing.mcp_lines(uses[:16])) == 15


def _bash(command, name="Bash"):
    return {"type": "tool_use", "name": name, "input": {"command": command}}


def _heredoc(body_lines, head="python - <<'EOF'"):
    return head + "\n" + "\n".join(body_lines) + "\nEOF"


def test_bash_script_takes_the_first_python_heredoc():
    uses = [_use("mcp__s__t"), _bash("ls -la"), _bash(_heredoc(["import numpy as np", "x = 1", "y = 2", "print(x)"])),
            _bash(_heredoc(["other", "one", "two", "three"]))]
    assert listing.bash_script(uses) == ["import numpy as np", "x = 1", "y = 2", "print(x)"]


def test_bash_script_needs_a_bash_tool_call_with_a_command():
    body = ["a = 1", "b = 2", "c = 3", "d = 4"]
    assert listing.bash_script([]) is None
    assert listing.bash_script([_bash(_heredoc(body), name="bash")]) is None
    assert listing.bash_script([_bash(_heredoc(body), name="BASH")]) is None
    assert listing.bash_script([_bash(_heredoc(body), name="Shell")]) is None
    assert listing.bash_script([{"name": "Bash"}]) is None
    assert listing.bash_script([{"name": "Bash", "input": None}]) is None
    assert listing.bash_script([{"name": "Bash", "input": {"command": None}}]) is None
    assert listing.bash_script([{"name": "Bash", "input": {"other": _heredoc(body)}}]) is None
    assert listing.bash_script([{"name": None}, _bash("echo hi")]) is None
    # a call that is not Bash does not hide the Bash call after it
    assert listing.bash_script([_use("Read", command=_heredoc(body)), _bash(_heredoc(body))]) == body
    assert listing.bash_script([_bash("echo hi"), _bash(_heredoc(body))]) == body


def test_bash_script_accepts_a_python_file_written_by_a_heredoc():
    body = ["a = 1", "b = 2", "c = 3", "d = 4"]
    assert listing.bash_script([_bash(_heredoc(body, "cat > fit.py <<'EOF'"))]) == body
    assert listing.bash_script([_bash(_heredoc(body, "cat > /tmp/run.PY <<'EOF'"))]) is None
    assert listing.bash_script([_bash(_heredoc(body, "cat > notes.txt <<'EOF'"))]) is None
    assert listing.bash_script([_bash(_heredoc(body, "cat <<'EOF'"))]) is None
    assert listing.bash_script([_bash(_heredoc(body, "cat > fit.pyc <<'EOF'"))]) is None
    assert listing.bash_script([_bash(_heredoc(body, "tee out.py <<EOF"))]) == body


def test_bash_script_drops_leading_blank_lines_and_trailing_newlines():
    body = ["", "   ", "", "first", "second", "third", "fourth", "", ""]
    assert listing.bash_script([_bash(_heredoc(body))]) == ["first", "second", "third", "fourth"]
    body = ["", "first", "  indented", "", "fourth"]
    assert listing.bash_script([_bash(_heredoc(body))]) == ["first", "  indented", "", "fourth"]
    body = ["one", "two", "three", "   "]
    assert listing.bash_script([_bash(_heredoc(body))]) == ["one", "two", "three", ""]
    body = ["one", "two", "three", "n = X"]  # only newlines are stripped from the end of the body
    assert listing.bash_script([_bash(_heredoc(body))]) == body


def test_bash_script_skips_a_heredoc_shorter_than_four_lines():
    short = ["a = 1", "b = 2", "c = 3"]
    four = ["a = 1", "b = 2", "c = 3", "d = 4"]
    assert listing.bash_script([_bash(_heredoc(short))]) is None
    assert listing.bash_script([_bash(_heredoc(four))]) == four
    assert listing.bash_script([_bash(_heredoc(short)), _bash(_heredoc(four))]) == four
    one = _heredoc(short, "python - <<'ONE'").replace("EOF", "ONE")
    two = _heredoc(four, "python - <<'TWO'").replace("EOF", "TWO")
    both = one + "\n" + two
    assert listing.bash_script([_bash(both)]) == four  # the short heredoc of the same call is passed over
    leading = ["", "", "x = 1", "y = 2", "z = 3"]
    assert listing.bash_script([_bash(_heredoc(leading))]) is None  # blank lines do not count towards the four


def test_bash_script_cuts_a_long_script_to_the_line_limit():
    n15 = [f"line{i}" for i in range(15)]
    assert listing.bash_script([_bash(_heredoc(n15))]) == n15
    n16 = [f"line{i}" for i in range(16)]
    assert listing.bash_script([_bash(_heredoc(n16))]) == n15[:14] + ["# ... (cut)"]
    n40 = [f"line{i}" for i in range(40)]
    got = listing.bash_script([_bash(_heredoc(n40))])
    assert got is not None and len(got) == 15 and got[13] == "line13" and got[14] == "# ... (cut)"
    n14 = n15[:14]
    assert listing.bash_script([_bash(_heredoc(n14))]) == n14


def test_bash_script_clips_each_line():
    body = ["x = '" + "a" * 80 + "'", "y = 1", "z = '/home/me/data'", "\tw = 2"]
    got = listing.bash_script([_bash(_heredoc(body))])
    assert got == ["x = '" + "a" * 52 + "...", "y = 1", "z = '~/data'", "    w = 2"]


# ------------------------------------------------------------------------------------------------ transcripts
def _event_tool(i, name, inp):
    return {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": f"t{i}", "name": name,
                                                          "input": inp}]}}


def _write(path: pathlib.Path, events):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")


def _row(model, cond, effort, task, k, *, ok=True, evaluable=True, cls="literature_all"):
    return data._norm_row({"model": model, "condition": cond, "effort": effort, "task_id": task, "k_index": k,
                           "class": cls, "correct": ok, "evaluable": evaluable}, "set")


def _mcp_events(n=3):
    names = ["mcp__ts__fit", "mcp__ts__energies", "mcp__ts__bands", "mcp__ts__more"]
    return [_event_tool(i, names[i], {"x": i}) for i in range(n)]


def _script_events():
    script = "import numpy as np\nx = np.arange(5)\ny = x ** 2\nprint(y.sum())\n"
    return [_event_tool(1, "Bash", {"command": f"python - <<'EOF'\n{script}EOF"})]


def _runset(root: pathlib.Path, name, rows, files):
    for rel, events in files.items():
        _write(root / rel, events)
    return data.RunSet(path=root, name=name, rows=rows)


def test_correct_transcripts_are_the_correct_evaluable_runs_of_one_condition_sorted_by_path(tmp_path):
    rows = [_row("claude-haiku-5-5", "C", "medium", "T2", 1), _row("claude-haiku-5-5", "C", "medium", "T1", 2),
            _row("claude-haiku-5-5", "C", "medium", "T1", 1, ok=False),
            _row("claude-haiku-5-5", "C", "medium", "T3", 1, evaluable=False),
            _row("claude-haiku-5-5", "B", "medium", "T4", 1),
            _row("claude-haiku-5-5", "C", "high", "T5", 1, ok=False, evaluable=False)]
    files = {f"claude-haiku-5-5/C/medium/{t}-k{k}.jsonl": _mcp_events() for t, k in
             [("T2", 1), ("T1", 2), ("T1", 1), ("T3", 1), ("T9", 1)]}
    files["claude-haiku-5-5/B/medium/T4-k1.jsonl"] = _script_events()
    files["claude-haiku-5-5/C/high/T5-k1.jsonl"] = _mcp_events()
    s = _runset(tmp_path, "set", rows, files)
    got = listing._correct_transcripts([s], "C")
    assert [p.relative_to(tmp_path).as_posix() for p, _s, _r in got] == [
        "claude-haiku-5-5/C/medium/T1-k2.jsonl", "claude-haiku-5-5/C/medium/T2-k1.jsonl"]
    assert all(gs is s for _p, gs, _r in got)
    assert [(r["task_id"], r["k_index"]) for _p, _s, r in got] == [("T1", 2), ("T2", 1)]
    only_b = listing._correct_transcripts([s], "B")
    assert [(r["task_id"], r["condition"]) for _p, _s, r in only_b] == [("T4", "B")]
    assert listing._correct_transcripts([s], "A") == []


def test_correct_transcripts_sort_by_the_posix_path_text(tmp_path):
    rows = [_row("m", "C", "medium", "T1", 1), _row("m-x", "C", "medium", "T1", 1)]
    files = {"m/C/medium/T1-k1.jsonl": _mcp_events(), "m-x/C/medium/T1-k1.jsonl": _mcp_events()}
    s = _runset(tmp_path, "set", rows, files)
    got = listing._correct_transcripts([s], "C")
    # "m-x/..." sorts before "m/..." as text ('-' < '/'), the reverse of the order of the path parts
    assert [p.relative_to(tmp_path).as_posix() for p, _s, _r in got] == ["m-x/C/medium/T1-k1.jsonl",
                                                                         "m/C/medium/T1-k1.jsonl"]


def test_correct_transcripts_match_gateway_directories_to_normalised_models(tmp_path):
    rows = [_row("qwen3", "C", "medium", "T1", 1)]
    s = _runset(tmp_path, "set", rows, {"gwdg-qwen3/C/medium/T1-k1.jsonl": _mcp_events()})
    got = listing._correct_transcripts([s], "C")
    assert [p.parent.parent.parent.name for p, _s, _r in got] == ["gwdg-qwen3"]


def test_correct_transcripts_span_all_sets_and_sort_across_them(tmp_path):
    empty = data.RunSet(path=tmp_path / "e", name="empty", rows=[_row("m", "B", "medium", "T1", 1)])
    s1 = _runset(tmp_path / "z", "z", [_row("m", "C", "medium", "T1", 1)], {"m/C/medium/T1-k1.jsonl": _mcp_events()})
    s2 = _runset(tmp_path / "a", "a", [_row("m", "C", "medium", "T1", 1)], {"m/C/medium/T1-k1.jsonl": _mcp_events()})
    got = listing._correct_transcripts([empty, s1, s2], "C")
    assert [s.name for _p, s, _r in got] == ["a", "z"]
    assert listing._correct_transcripts([], "C") == []


def test_pick_returns_the_first_transcript_that_passes_both_tests(tmp_path):
    rows = [_row("m", "C", "medium", f"T{i}", 1) for i in (1, 2, 3, 4)]
    files = {"m/C/medium/T1-k1.jsonl": _mcp_events(1), "m/C/medium/T2-k1.jsonl": [],
             "m/C/medium/T3-k1.jsonl": _mcp_events(3), "m/C/medium/T4-k1.jsonl": _mcp_events(4)}
    s = _runset(tmp_path, "set", rows, files)
    lines, path, rs, row = listing._pick([s], "C", listing.mcp_lines, lambda ls: len(ls) >= 2)
    assert lines == ["fit(x=0)", "energies(x=1)", "bands(x=2)"]
    assert path == tmp_path / "m/C/medium/T3-k1.jsonl" and rs is s and row["task_id"] == "T3"


def test_pick_needs_extracted_lines_and_a_passing_check(tmp_path):
    s = _runset(tmp_path, "set", [_row("m", "C", "medium", "T1", 1)], {"m/C/medium/T1-k1.jsonl": []})
    assert listing._pick([s], "C", listing.mcp_lines, lambda ls: True) is None  # nothing extracted: no pick
    assert listing._pick([s], "C", lambda uses: ["x"], lambda ls: False) is None
    assert listing._pick([s], "C", lambda uses: ["x"], lambda ls: True)[0] == ["x"]
    assert listing._pick([s], "B", lambda uses: ["x"], lambda ls: True) is None  # no run of that condition
    assert listing._pick([], "C", lambda uses: ["x"], lambda ls: True) is None


def test_pick_takes_the_first_extraction_when_no_check_is_given(tmp_path):
    s = _runset(tmp_path, "set", [_row("m", "B", "medium", "T1", 1)], {"m/B/medium/T1-k1.jsonl": _script_events()})
    got = listing._pick([s], "B", listing.bash_script)
    assert got is not None and got[0] == ["import numpy as np", "x = np.arange(5)", "y = x ** 2", "print(y.sum())"]


def test_pick_skips_an_unreadable_transcript(tmp_path, monkeypatch):
    rows = [_row("m", "C", "medium", f"T{i}", 1) for i in (1, 2)]
    files = {"m/C/medium/T1-k1.jsonl": _mcp_events(), "m/C/medium/T2-k1.jsonl": _mcp_events(2)}
    s = _runset(tmp_path, "set", rows, files)
    from tsbench.score import artifacts
    real = artifacts.scan_tool_calls

    def flaky(path):
        if path.name.startswith("T1"):
            raise OSError("gone")
        return real(path)

    monkeypatch.setattr(artifacts, "scan_tool_calls", flaky)
    lines, path, _s, _row_ = listing._pick([s], "C", listing.mcp_lines, lambda ls: True)
    assert path.name == "T2-k1.jsonl" and lines == ["fit(x=0)", "energies(x=1)"]


def test_pick_does_not_run_the_checks_on_an_empty_extraction(tmp_path):
    s = _runset(tmp_path, "set", [_row("m", "C", "medium", "T1", 1)], {"m/C/medium/T1-k1.jsonl": _mcp_events()})
    calls = []

    def ok(lines):
        calls.append(lines)
        return True

    assert listing._pick([s], "C", lambda uses: [], ok) is None
    assert calls == []


# ------------------------------------------------------------------------------------------------ the figure
def _ctx(tmp_path, with_c=True, with_b=True, **kw):
    rows, files = [], {}
    if with_c:
        rows += [_row("claude-haiku-5-5", "C", "medium", "T2", 1, cls="literature_new"),
                 _row("claude-haiku-5-5", "C", "medium", "T1", 1, cls="literature_all")]
        files["claude-haiku-5-5/C/medium/T1-k1.jsonl"] = _mcp_events(1)  # one call only: not enough
        files["claude-haiku-5-5/C/medium/T2-k1.jsonl"] = _mcp_events(2)  # two calls are enough
    if with_b:
        rows += [_row("claude-haiku-5-5", "B", "medium", "T3", 2, cls="experimental")]
        files["claude-haiku-5-5/B/medium/T3-k2.jsonl"] = _script_events()
    s = _runset(tmp_path, "myset", rows, files)
    return Context(sets=[s], **kw)


def _text_at(ax, x, y, tol=1e-9):
    return [t for t in ax.texts if abs(t.get_position()[0] - x) < tol and abs(t.get_position()[1] - y) < tol]


def test_listing_draws_two_panels_with_the_lines_of_the_picked_runs(tmp_path):
    ctx = _ctx(tmp_path)
    built = listing.code_listing(ctx)
    fig = _fig(built)
    assert len(fig.axes) == 2
    ax_c, ax_b = fig.axes
    w, h = fig.get_size_inches()
    assert w == pytest.approx(177.8 / 25.4)
    assert h * 25.4 == pytest.approx(12 + 15 * 6 * 1.25 * 25.4 / 72 + 6)
    for ax in (ax_c, ax_b):
        assert not ax.axison
        assert (ax.get_xlim(), ax.get_ylim()) == ((0.0, 1.0), (0.0, 1.0))
        (box,) = ax.patches
        bb = cast(Any, box).get_bbox()
        assert (bb.x0, bb.y0, bb.width, bb.height) == (0, 0, 1, 0.9)
        assert box.get_linewidth() == 0.5 and box.get_zorder() == 0
        assert box.get_facecolor()[:3] == pytest.approx((0xe6 / 255, 0xeb / 255, 0xf6 / 255))
        assert box.get_edgecolor()[:3] == pytest.approx((0x7a / 255,) * 3)
        assert box.get_transform() == ax.transAxes
        style = cast(Any, box).get_boxstyle()
        assert (type(style).__name__, style.pad, style.rounding_size) == ("Round", 0, 0.02)

    (title_c,) = _text_at(ax_c, 0.0, 0.96)
    assert title_c.get_text() == "MCP call sequence (TS-MCP): Haiku 5.5, literature new"
    assert (title_c.get_fontsize(), title_c.get_fontweight(), title_c.get_va(), title_c.get_ha()) == (
        6.5, "bold", "bottom", "left")
    (title_b,) = _text_at(ax_b, 0.0, 0.96)
    assert title_b.get_text() == "Bash script (Python stack): Haiku 5.5, experimental"

    mcp = ["fit(x=0)", "energies(x=1)"]
    for i, line in enumerate(mcp):
        y = 0.9 - STEP * (i + 1)
        (num,) = _text_at(ax_c, 0.02, y)
        assert num.get_text() == f"{i + 1:>2}" and num.get_fontsize() == 5.5 and num.get_va() == "center"
        assert num.get_family() == ["monospace"] and num.get_color() == "#4d4d4d"
        (code,) = _text_at(ax_c, 0.085, y)
        assert code.get_text() == line and code.get_fontsize() == 6 and code.get_va() == "center"
        assert code.get_family() == ["monospace"] and code.get_color() == "#1a1a1a"
    assert len(ax_c.texts) == 1 + 2 * 2 + 1  # title, numbers and code, the panel letter
    script = ["import numpy as np", "x = np.arange(5)", "y = x ** 2", "print(y.sum())"]
    assert [t.get_text() for t in ax_b.texts if abs(t.get_position()[0] - 0.085) < 1e-9] == script
    assert [t.get_text() for t in ax_b.texts if abs(t.get_position()[0] - 0.02) < 1e-9] == [" 1", " 2", " 3", " 4"]
    assert [t.get_text() for t in ax_c.texts if t.get_position()[0] < 0] == ["a"]
    assert [t.get_text() for t in ax_b.texts if t.get_position()[0] < 0] == ["b"]
    (letter,) = [t for t in ax_c.texts if t.get_position()[0] < 0]
    assert letter.get_position() == (-0.02, 0.96) and letter.get_fontsize() == 8


def test_listing_source_rows_name_the_transcript_of_every_line(tmp_path):
    built = listing.code_listing(_ctx(tmp_path))
    assert built.columns == ["panel", "line", "text", "run_set", "transcript", "model", "task_id", "k_index"]
    assert [(r["panel"], r["line"], r["text"]) for r in built.source] == [
        ("C", 1, "fit(x=0)"), ("C", 2, "energies(x=1)"),
        ("B", 1, "import numpy as np"), ("B", 2, "x = np.arange(5)"), ("B", 3, "y = x ** 2"),
        ("B", 4, "print(y.sum())")]
    first, last = built.source[0], built.source[-1]
    assert first == {"panel": "C", "line": 1, "text": "fit(x=0)", "run_set": "myset",
                     "transcript": "claude-haiku-5-5/C/medium/T2-k1.jsonl", "model": "claude-haiku-5-5",
                     "task_id": "T2", "k_index": 1}
    assert last["transcript"] == "claude-haiku-5-5/B/medium/T3-k2.jsonl" and last["task_id"] == "T3"
    assert last["k_index"] == 2 and last["model"] == "claude-haiku-5-5" and last["run_set"] == "myset"
    assert built.caption == (
        "Example code of correct pilot runs, unedited except for clipping long lines and replacing home paths: "
        "(a) the tool calls of a TS-MCP (C) run, (b) the first Python script of a Bash (B) run. "
        "PILOT data, not confirmatory.")
    assert built.notes == ["at most 15 lines per panel, lines clipped at 60 characters",
                           "first correct run by path order"]


def test_listing_footer_and_layout(tmp_path):
    built = listing.code_listing(_ctx(tmp_path))
    fig = _fig(built)
    (footer,) = [t for t in fig.texts if t.get_gid() == "footer"]
    assert footer.get_text() == "Pilot data, not confirmatory: 3 runs from 1 run sets (HTTP 429 / API errors excluded)."
    h_pt = fig.get_figheight() * 72
    assert cast(Any, fig.get_layout_engine()).get()["rect"] == pytest.approx((0, 9 / h_pt, 1, 1 - 9 / h_pt))
    assert not [t for t in fig.texts if (t.get_gid() or "").startswith("key:")]  # no condition key here
    plt.close("all")
    built = listing.code_listing(_ctx(tmp_path, footer=False))
    assert not [t for t in _fig(built).texts if t.get_gid() == "footer"]
    assert cast(Any, _fig(built).get_layout_engine()).get()["rect"] == pytest.approx((0, 0, 1, 1))


def test_listing_uses_the_theme_of_the_context(tmp_path, contrast_theme):
    built = listing.code_listing(_ctx(tmp_path, theme=contrast_theme))
    (box,) = _fig(built).axes[0].patches
    assert box.get_facecolor()[:3] == pytest.approx((0xee / 255,) * 3)


def test_listing_marks_a_missing_panel(tmp_path):
    built = listing.code_listing(_ctx(tmp_path, with_c=False))
    ax_c, ax_b = _fig(built).axes
    assert {t.get_text() for t in ax_c.texts} == {"MCP call sequence (TS-MCP)", "no example found", "a"}
    (msg,) = _text_at(ax_c, 0.5, 0.45)
    assert (msg.get_text(), msg.get_fontsize(), msg.get_ha(), msg.get_va(), msg.get_color()) == (
        "no example found", 6, "center", "center", "#4d4d4d")
    (title,) = _text_at(ax_c, 0.0, 0.96)
    assert (title.get_text(), title.get_fontsize(), title.get_fontweight(), title.get_va()) == (
        "MCP call sequence (TS-MCP)", 7, "bold", "bottom")
    assert {r["panel"] for r in built.source} == {"B"}
    assert len(ax_b.texts) == 1 + 2 * 4 + 1
    plt.close("all")
    built = listing.code_listing(_ctx(tmp_path, with_b=False))
    ax_c, ax_b = _fig(built).axes
    assert {t.get_text() for t in ax_b.texts} == {"Bash script (Python stack)", "no example found", "b"}
    assert {r["panel"] for r in built.source} == {"C"}


def test_listing_without_any_example_raises(tmp_path):
    with pytest.raises(data.NoDataError, match=r"^code_listing: no correct transcript with MCP calls \(C\) or a Python "
                                               r"heredoc \(B\)$"):
        listing.code_listing(_ctx(tmp_path, with_c=False, with_b=False))


def test_listing_lines_are_capped_and_clipped(tmp_path):
    uses = [_event_tool(i, "mcp__ts__tool", {"payload": "v" * 90 + str(i)}) for i in range(20)]
    rows = [_row("claude-sonnet-5-5", "C", "high", "T1", 1)]
    s = _runset(tmp_path, "s", rows, {"claude-sonnet-5-5/C/high/T1-k1.jsonl": uses})
    built = listing.code_listing(Context(sets=[s]))
    assert len(built.source) == 15
    assert all(len(r["text"]) == 60 and r["text"].endswith("...") for r in built.source)
    assert [r["line"] for r in built.source] == list(range(1, 16))
    ax_c = _fig(built).axes[0]
    numbers = [t.get_text() for t in ax_c.texts if abs(t.get_position()[0] - 0.02) < 1e-9]
    assert numbers == [f"{i:>2}" for i in range(1, 16)]
    last_y = 0.9 - STEP * 15
    assert last_y == pytest.approx(0.9 / 16)
    assert _text_at(ax_c, 0.02, last_y)[0].get_text() == "15"


LOUD = {"patch.linewidth": 3.0, "font.size": 11.0, "text.color": "#ff0000"}


def test_listing_states_its_sizes_and_colours_whatever_the_style(tmp_path, monkeypatch):
    """The panel frame, the titles and the code lines carry their own line width, size and colour: a style whose
    defaults differ (set after the builder's own set-up) changes none of them."""
    real = listing.setup

    def loud_setup(theme="neutral"):
        plt_, jfs = real(theme)
        for key, value in LOUD.items():
            monkeypatch.setitem(plt_.rcParams, key, value)
        return plt_, jfs

    monkeypatch.setattr(listing, "setup", loud_setup)
    built = listing.code_listing(_ctx(tmp_path, with_c=False))
    ax_c, ax_b = _fig(built).axes
    assert [p.get_linewidth() for ax in (ax_c, ax_b) for p in ax.patches] == [0.5, 0.5]
    (title,) = _text_at(ax_c, 0.0, 0.96)
    assert title.get_fontsize() == 7
    code = _text_at(ax_b, 0.085, 0.9 - STEP)
    assert [(t.get_fontsize(), t.get_color()) for t in code] == [(6, "#1a1a1a")]
