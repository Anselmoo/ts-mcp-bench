"""Tests for src/tsbench/score/artifacts.py: heredoc splitting, MCP calls and images, idempotence."""
from __future__ import annotations

import base64
import hashlib
import json
import os
import pathlib

import pytest

from tsbench.score import artifacts as art

PNG = base64.b64encode(b"\x89PNG\r\n\x1a\nfake").decode()


def _use(i, name, inp):
    return {"type": "assistant", "message": {"role": "assistant", "content": [
        {"type": "tool_use", "id": i, "name": name, "input": inp}]}}


def _res(i, content, err=False):
    return {"type": "user", "message": {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": i, "content": content, "is_error": err}]}}


def _write(path, events):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(x) for x in events) + "\nnot json{\n", encoding="utf-8")
    return path


def test_split_heredocs_variants():
    cmd = ("cat > a.py <<'EOF'\nprint(1)\nEOF\n"
           "cat << 'END' > sub/b.py\nx = 2\nEND\n"
           "python3 - <<'PY'\nprint('hi')\nPY\n"
           "tee c.txt <<EOF2\nline\nEOF2\npython a.py")
    hs, skel = art.split_heredocs(cmd)
    assert [h["name"] for h in hs] == ["a.py", "sub/b.py", None, "c.txt"]
    assert hs[0]["body"] == "print(1)\n" and hs[1]["body"] == "x = 2\n"
    assert hs[2]["python"] is True and hs[2]["body"] == "print('hi')\n"
    assert "print(1)" not in skel and "python a.py" in skel


def test_split_heredoc_unterminated_and_none():
    hs, _ = art.split_heredocs("cat > z.py <<'EOF'\na\nb")
    assert hs[0]["body"] == "a\nb\n"
    assert art.split_heredocs("echo hi")[0] == []


def test_extract_code_bash_heredoc_mcp_image(tmp_path):
    t = _write(tmp_path / "m" / "B" / "medium" / "P-x-01-k1.jsonl", [
        _use("t1", "Bash", {"command": "cat > ../evil.py <<'EOF'\nimport os\nEOF\npython evil.py"}),
        _res("t1", "Exit code 2\nTraceback", err=True),
        _use("t2", "mcp__tanabesugano__ts_plot_png", {"B": 700, "d_count": 3}),
        _res("t2", [{"type": "text", "text": "ok"},
                    {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": PNG}}]),
        _use("t2", "mcp__tanabesugano__ts_plot_png", {"B": 700, "d_count": 3}),  # streamed duplicate
        _use("t3", "StructuredOutput", {"a": 1}),
    ])
    calls = art.extract_code(t)
    kinds = [c["kind"] for c in calls]
    assert (kinds == ["image", "bash", "heredoc", "mcp"] or kinds == ["bash", "heredoc", "image", "mcp"]
            or sorted(kinds) == sorted(["bash", "heredoc", "mcp", "image"]))
    d = t.with_name("P-x-01-k1.code")
    bash = next(c for c in calls if c["kind"] == "bash")
    assert bash["exit"] == 2 and bash["is_error"] is True and "Traceback" in bash["result_excerpt"]
    here = next(c for c in calls if c["kind"] == "heredoc")
    assert (here["name"] == "evil.py" and "/" not in here["path"]
        and (d / here["path"]).read_text(encoding="utf-8") == "import os\n")
    mcp = next(c for c in calls if c["kind"] == "mcp")
    assert json.loads((d / mcp["path"]).read_text(encoding="utf-8")) == {"B": 700, "d_count": 3}
    img = next(c for c in calls if c["kind"] == "image")
    assert img["name"] == "mcp_image_1.png" and (d / "mcp_image_1.png").read_bytes().startswith(b"\x89PNG")
    assert len([c for c in calls if c["kind"] == "mcp"]) == 1  # duplicate id skipped
    assert json.loads((d / "calls.json").read_text(encoding="utf-8")) == calls
    assert (d / "00_cmd.sh").read_text(encoding="utf-8").startswith("cat > ../evil")
    for c in calls:  # sha256 is of the stored file
        import hashlib
        assert hashlib.sha256((d / c["path"]).read_bytes()).hexdigest() == c["sha256"]


def test_extract_code_idempotent_and_refreshes(tmp_path):
    t = _write(tmp_path / "k-k1.jsonl", [_use("a", "Bash", {"command": "ls"}), _res("a", "x")])
    first = art.extract_code(t)
    cj = t.with_name("k-k1.code") / "calls.json"
    os.utime(cj, ns=(4 * 10**18, 4 * 10**18))  # far future: must count as up to date
    before = cj.stat().st_mtime_ns
    assert art.extract_code(t) == first and cj.stat().st_mtime_ns == before
    t.write_text(t.read_text(encoding="utf-8") + json.dumps(_use("b", "Bash", {"command": "pwd"})) + "\n",
        encoding="utf-8")
    os.utime(t, ns=(4 * 10**18 + 5, 4 * 10**18 + 5))  # transcript newer: redo
    assert len(art.extract_code(t)) == 2


def _count_reads(monkeypatch, path):
    """Count the text opens of `path` through builtins.open (every reader of a transcript uses it)."""
    import builtins
    real, seen = builtins.open, []

    def counting(file, *a, **kw):
        if str(file) == str(path):
            seen.append(file)
        return real(file, *a, **kw)

    monkeypatch.setattr(builtins, "open", counting)
    return seen


def test_no_code_writes_an_empty_calls_json_so_the_next_call_hits_the_cache(tmp_path, monkeypatch):
    t = _write(tmp_path / "n-k1.jsonl", [_use("a", "StructuredOutput", {})])
    assert art.extract_code(t) == []
    d = t.with_name("n-k1.code")
    assert [p.name for p in d.iterdir()] == ["calls.json"]
    assert json.loads((d / "calls.json").read_text(encoding="utf-8")) == []
    reads = _count_reads(monkeypatch, t)
    assert art.extract_code(t) == [] and reads == []   # fresh: the transcript is not parsed again


def test_an_unhashable_tool_use_id_does_not_stop_extract_code(tmp_path):
    t = _write(tmp_path / "u-k1.jsonl", [
        _use(["x"], "Bash", {"command": "ls"}), _res(["x"], "out"), _use("b", "Bash", {"command": "pwd"}),
        _res("b", "/w")])
    got = art.extract_code(t)
    assert [e["call"] for e in got] == [0, 1] and got[1]["result_excerpt"] == "/w"


def test_scan_and_answer_texts_take_a_parsed_transcript(tmp_path):
    from tsbench.score.extract import read_transcript
    t = _write(tmp_path / "p-k1.jsonl", [
        _use("a", "Bash", {"command": "ls"}), _res("a", "x"), _use("a", "Bash", {"command": "ls"}),
        {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "hello"}]}},
        {"type": "result", "result": "final"}])
    tr = read_transcript(t)
    assert art.scan_tool_calls(tr) == art.scan_tool_calls(t)
    assert art.answer_texts(tr) == art.answer_texts(t) == ["hello", "final"]


def test_a_parsed_transcript_is_the_only_read(tmp_path, monkeypatch):
    from tsbench.score.extract import read_transcript
    t = _write(tmp_path / "q-k1.jsonl", [
        _use("a", "Bash", {"command": "ls"}), _res("a", "x"), _use("b", "mcp__ts__ts_plot_png", {"B": 1}),
        _res("b", [{"type": "image", "source": {"media_type": "image/png", "data": PNG}}]),
        {"type": "result", "result": "final"}])
    reads = _count_reads(monkeypatch, t)
    tr = read_transcript(t)
    calls = art.extract_code(t, tr=tr)
    assert art.answer_texts(tr) == ["final"] and len(reads) == 1
    monkeypatch.undo()
    assert calls == art.extract_code(t, write=False)
    assert sorted(c["kind"] for c in calls) == ["bash", "image", "mcp"]


def test_write_false_writes_nothing(tmp_path):
    t2 = _write(tmp_path / "w-k1.jsonl", [_use("a", "Bash", {"command": "ls"})])
    assert len(art.extract_code(t2, write=False)) == 1 and not t2.with_name("w-k1.code").exists()


def test_never_executes(tmp_path):
    marker = tmp_path / "executed"
    t = _write(tmp_path / "e-k1.jsonl", [_use("a", "Bash", {"command": f"touch {marker}"}), _res("a", "")])
    art.extract_code(t)
    assert not marker.exists()


def test_cli_counts(tmp_path, capsys):
    _write(tmp_path / "m/B/medium/P-x-01-k1.jsonl", [_use("a", "Bash", {"command": "ls"})])
    _write(tmp_path / "_sandbox_probe/transcript.jsonl", [_use("a", "Bash", {"command": "ls"})])
    assert art.main(["--runs", str(tmp_path)]) == 0
    assert "runs with code: 1" in capsys.readouterr().out


# ---------------------------------------------------------------- exact behaviour, one function at a time
def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_iter_events_skips_blank_broken_and_non_object_lines(tmp_path):
    t = tmp_path / "t.jsonl"
    t.write_bytes(b'\n  \n{"a": 1}\n[1, 2]\n7\n"s"\n{broken\n{"b": "\xff"}\n')
    assert list(art.iter_events(t)) == [{"a": 1}, {"b": "�"}]


def test_code_dir_of_replaces_the_jsonl_suffix_or_appends():
    assert art.code_dir_of("/r/m/P-x-01-k2.jsonl") == pathlib.Path("/r/m/P-x-01-k2.code")
    assert art.code_dir_of("/r/transcript.jsonl") == pathlib.Path("/r/transcript.code")
    assert art.code_dir_of("/r/log.txt") == pathlib.Path("/r/log.txt.code")
    assert art.code_dir_of("/r/jsonl") == pathlib.Path("/r/jsonl.code")


def test_split_heredocs_skeleton_and_line_counts():
    hs, skel = art.split_heredocs("echo start\ncat > a.py <<'EOF'\nx = 1\ny = 2\nEOF\necho end")
    assert hs == [{"name": "a.py", "body": "x = 1\ny = 2\n", "lines": 2, "python": False}]
    assert skel == ("echo start\ncat > a.py <<'EOF'\n... [heredoc EOF: 2 lines, see file] ...\nEOF\necho end")


def test_split_heredocs_terminators():
    # <<- strips leading tabs from the terminator line, plain << does not; trailing blanks never matter
    hs, _ = art.split_heredocs("cat > a <<-EOF\nbody\n\t\tEOF\nafter")
    assert hs[0]["body"] == "body\n"
    hs, _ = art.split_heredocs("cat > a <<EOF\nbody\n\tEOF\nEOF  \nafter")
    assert hs[0]["body"] == "body\n\tEOF\n"
    hs, _ = art.split_heredocs("cat > a <<EOF\n  EOF\nEOF")
    assert hs[0]["body"] == "  EOF\n" and hs[0]["lines"] == 1
    hs, _ = art.split_heredocs("cat > a <<\"END\"\nq\nEND")
    assert hs[0]["body"] == "q\n" and hs[0]["name"] == "a"
    hs, _ = art.split_heredocs("cat > a <<EOF\nEOF")
    assert hs == [{"name": "a", "body": "\n", "lines": 0, "python": False}]


def test_split_heredocs_targets():
    def name(cmd):
        return art.split_heredocs(cmd)[0][0]["name"]

    assert name("cat >> log.txt <<EOF\nx\nEOF") == "log.txt"
    assert name("cat > 'q.py' <<EOF\nx\nEOF") == "q.py"
    assert name("tee -a t.txt <<EOF\nx\nEOF") == "t.txt"
    assert name("tee t.txt <<EOF\nx\nEOF") == "t.txt"
    assert name("cat <<EOF\nx\nEOF") is None, "no redirect"
    assert name("python3 - <<EOF > out.txt\nx\nEOF") is None, "only cat and tee write the heredoc to a file"
    assert name("concat > z <<EOF\nx\nEOF") is None, "cat must be a word"


def test_split_heredocs_two_on_one_line_have_no_name():
    hs, skel = art.split_heredocs("cat > a.txt <<A <<B\none\nA\ntwo\nB\nrest")
    assert [(h["name"], h["body"]) for h in hs] == [(None, "one\n"), (None, "two\n")]
    assert skel.splitlines() == ["cat > a.txt <<A <<B", "... [heredoc A: 1 lines, see file] ...", "A",
                                 "... [heredoc B: 1 lines, see file] ...", "B", "rest"]


def test_split_heredocs_python_flag():
    def py(line):
        return art.split_heredocs(line + "\nx\nEOF")[0][0]["python"]

    assert py("python - <<EOF") and py("python3 - <<'EOF'") and py("python3.12 - <<EOF")
    assert not py("mypython - <<EOF") and not py("pythonx - <<EOF") and not py("bash <<EOF")
    assert not py("python - <<EOF | cat > f.py"), "a named heredoc is a file, not inline Python"


def test_safe_name():
    assert art._safe_name(None, "fb") == "fb"
    assert art._safe_name("", "fb") == "fb"
    assert art._safe_name("a/b/c.py", "fb") == "c.py"
    assert art._safe_name("a\\b\\d.py", "fb") == "d.py"
    assert art._safe_name("x y$z.py", "fb") == "x_y_z.py"
    assert art._safe_name("..hidden.", "fb") == "hidden"
    assert art._safe_name("_x-1_", "fb") == "x-1"
    assert art._safe_name("dir/", "fb") == "fb"
    assert art._safe_name("$$$", "fb") == "fb"
    assert art._safe_name("n" * 70 + ".py", "fb") == "n" * 60


def test_result_text():
    assert art._result_text("plain") == "plain"
    assert art._result_text(None) == ""
    assert art._result_text({"type": "text", "text": "x"}) == ""
    content = [{"type": "text", "text": "a"}, {"type": "image"}, "b", 5, {"type": "other", "text": "no"},
               {"type": "text"}, {"type": "text", "text": 3}]
    assert art._result_text(content) == "a\n[image]\nb\n\n3"


def test_scan_tool_calls_takes_uses_from_assistant_and_results_from_user(tmp_path):
    t = _write(tmp_path / "s-k1.jsonl", [
        {"type": "system"},
        {"type": "assistant", "message": "text"},
        {"type": "assistant", "message": {"content": "text"}},
        {"type": "assistant", "message": {"content": ["x", {"type": "text", "text": "t"}]}},
        _use("u1", "Bash", {"command": "ls"}),
        {"type": "user", "message": {"content": [{"type": "tool_use", "id": "u9", "name": "X", "input": {}}]}},
        {"type": "assistant", "message": {"content": [{"type": "tool_result", "tool_use_id": "u1", "content": "no"}]}},
        _res("u1", "yes"),
        _use("u1", "Bash", {"command": "again"}),
        _use("u2", "Read", {}),
    ])
    uses, results = art.scan_tool_calls(t)
    assert [(u["id"], u["input"]) for u in uses] == [("u1", {"command": "ls"}), ("u2", {})]
    assert list(results) == ["u1"] and results["u1"]["content"] == "yes"


def test_answer_texts(tmp_path):
    t = _write(tmp_path / "a-k1.jsonl", [
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "one"}, {"type": "tool_use"},
                                                      {"type": "text", "text": 5}, "raw"]}},
        {"type": "user", "message": {"content": [{"type": "text", "text": "not mine"}]}},
        {"type": "assistant", "message": {"content": "flat"}},
        {"type": "assistant", "message": "flat"},
        {"type": "result", "result": "<svg/>"},
        {"type": "result", "result": {"x": 1}},
        {"type": "system", "result": "not a result event"},
    ])
    assert art.answer_texts(t) == ["one", "<svg/>"]


def test_fresh_needs_calls_json_at_least_as_new_as_the_transcript(tmp_path):
    t = tmp_path / "t.jsonl"
    t.write_text("", encoding="utf-8")
    d = tmp_path / "t.code"
    assert art._fresh(d, t) is False
    d.mkdir()
    (d / "calls.json").write_text("[]", encoding="utf-8")
    os.utime(t, ns=(10**18, 10**18))
    os.utime(d / "calls.json", ns=(10**18, 10**18))
    assert art._fresh(d, t) is True
    os.utime(d / "calls.json", ns=(10**18 - 1, 10**18 - 1))
    assert art._fresh(d, t) is False
    assert art._fresh(d, tmp_path / "missing.jsonl") is False


def test_write_if_changed_leaves_equal_files_alone(tmp_path):
    p = tmp_path / "f"
    art._write_if_changed(p, b"one")
    assert p.read_bytes() == b"one"
    os.utime(p, ns=(10**18, 10**18))
    art._write_if_changed(p, b"one")
    assert p.stat().st_mtime_ns == 10**18
    art._write_if_changed(p, b"two")
    assert p.read_bytes() == b"two"


def _calls(tmp_path, events, name="c-k1.jsonl", **kw):
    t = _write(tmp_path / name, events)
    return art.extract_code(t, **kw), t.with_name(name[: -len(".jsonl")] + ".code")


def test_extract_code_exit_codes(tmp_path):
    results = ["ok", "x\nExit code 3", "x\n  exit status: 4", "Exit status -1", "exit code 5 at start",
               "mid Exit code 6"]
    events = []
    for i, text in enumerate(results):
        events += [_use(f"u{i}", "Bash", {"command": f"c{i}"}), _res(f"u{i}", text)]
    events += [_use("e", "Bash", {"command": "err"}), _res("e", "boom", err=True),
               _use("n", "Bash", {"command": "none"})]
    calls, _ = _calls(tmp_path, events, write=False)
    assert [c["exit"] for c in calls] == [0, 3, 4, -1, 5, 0, 1, None]
    assert [c["is_error"] for c in calls] == [False] * 6 + [True, False]


def test_extract_code_bash_entries_and_numbering(tmp_path):
    cmd = "cat > a.py <<'EOF'\nprint(1)\nEOF\npython3 - <<'PY'\nprint(2)\nPY\ncat <<X\nz\nX"
    calls, d = _calls(tmp_path, [
        _use("u1", "Bash", {"command": cmd, "description": "d" * 300}), _res("u1", "  " + "r" * 500 + "  "),
        _use("u2", "Bash", {"command": ""}),
        _use("u3", "Bash", "not a dict"),
        _use("u4", "Bash", {"command": "ls"}),
    ])
    bash, h1, h2, h3, ls = calls
    assert bash == {"kind": "bash", "name": "cmd.sh", "path": "00_cmd.sh", "sha256": _sha(cmd.encode()), "call": 0,
                    "exit": 0, "is_error": False, "result_excerpt": "r" * 400,
                    "skeleton": art.split_heredocs(cmd)[1], "description": "d" * 200}
    assert h1 == {"kind": "heredoc", "name": "a.py", "path": "01_a.py", "sha256": _sha(b"print(1)\n"), "call": 0,
                  "target": "a.py", "lines": 1, "exit": 0, "is_error": False, "result_excerpt": "r" * 400}
    assert (h2["name"], h2["path"], h2["target"], h2["call"]) == ("inline_2.py", "02_inline_2.py", None, 1)
    assert (h3["name"], h3["path"]) == ("heredoc_3.txt", "03_heredoc_3.txt")
    assert (ls["path"], ls["call"], ls["exit"], ls["description"]) == ("04_cmd.sh", 4, None, "")
    assert sorted(p.name for p in d.iterdir()) == ["00_cmd.sh", "01_a.py", "02_inline_2.py", "03_heredoc_3.txt",
                                                    "04_cmd.sh", "calls.json"]
    assert (d / "02_inline_2.py").read_text(encoding="utf-8") == "print(2)\n"


def test_extract_code_mcp_entries(tmp_path):
    calls, d = _calls(tmp_path, [
        _use("m1", "mcp__tanabesugano__ts_fit__v2", {"z": "é", "a": [1]}), _res("m1", "Exit status: 0\nfine"),
        _use("m2", "mcp__x", {}),
        _use("o", "Read", {"file_path": "/x"}), _res("o", "contents"),
        {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "nn", "input": {"command": "ls"}}]}},
    ])
    m1, m2 = calls
    body = '{\n "a": [\n  1\n ],\n "z": "é"\n}\n'
    assert m1 == {"kind": "mcp", "name": "mcp__tanabesugano__ts_fit__v2", "path": "00_mcp_ts_fit__v2.json",
                  "sha256": _sha(body.encode()), "call": 0, "exit": 0, "is_error": False,
                  "result_excerpt": "Exit status: 0\nfine"}
    assert (d / m1["path"]).read_text(encoding="utf-8") == body
    assert (m2["name"], m2["path"], m2["call"], m2["exit"]) == ("mcp__x", "01_mcp_x.json", 1, None)


def test_extract_code_images(tmp_path):
    def img(data, media=None):
        src = {"type": "base64", "data": data}
        if media:
            src["media_type"] = media
        return {"type": "image", "source": src}

    raw = b"\x89PNG-data"
    good = base64.b64encode(raw).decode()
    content = [img(good, "image/jpeg"), img(good), img(good, "image/x-new"), img("", "image/png"), img("abc"),
               {"type": "image", "source": "inline"}, {"type": "image"}, "text"]
    calls, d = _calls(tmp_path, [_use("r", "Read", {}), _res("r", content), _use("b", "Bash", {"command": "ls"}),
                                 _res("b", [img(good, "image/svg+xml")])])
    assert [c["path"] for c in calls] == ["mcp_image_1.jpg", "mcp_image_2.png", "mcp_image_3.bin", "mcp_image_4.svg",
                                          "00_cmd.sh"]
    first = calls[0]
    assert first == {"kind": "image", "name": "mcp_image_1.jpg", "path": "mcp_image_1.jpg", "sha256": _sha(raw),
                     "media_type": "image/jpeg", "tool": "Read", "bytes": len(raw), "is_error": False, "exit": None,
                     "result_excerpt": ""}
    assert calls[1]["media_type"] == "image/png" and calls[3]["tool"] == "Bash"
    assert (d / "mcp_image_3.bin").read_bytes() == raw
    assert calls[4]["result_excerpt"] == "[image]"


def test_extract_code_writes_calls_json_last_and_removes_stale_files(tmp_path):
    t = _write(tmp_path / "w-k1.jsonl", [_use("a", "Bash", {"command": "echo é"}), _res("a", "é")])
    d = t.with_name("w-k1.code")
    d.mkdir()
    (d / "07_cmd.sh").write_text("old", encoding="utf-8")
    (d / "sub").mkdir()
    (d / "link").symlink_to(d / "sub")
    calls = art.extract_code(t)
    assert sorted(p.name for p in d.iterdir()) == ["00_cmd.sh", "calls.json", "link", "sub"]
    text = (d / "calls.json").read_text(encoding="utf-8")
    assert text == json.dumps(calls, indent=1, ensure_ascii=False) + "\n" and "é" in text
    assert all((d / f).stat().st_mtime_ns <= (d / "calls.json").stat().st_mtime_ns for f in ("00_cmd.sh",))


def test_extract_code_uses_a_fresh_cache_only_when_it_is_a_list(tmp_path):
    t = _write(tmp_path / "f-k1.jsonl", [_use("a", "Bash", {"command": "ls"})])
    d = t.with_name("f-k1.code")
    d.mkdir()
    for cached, expected in (('[{"kind": "cached"}]', [{"kind": "cached"}]), ('{"kind": "dict"}', None),
                             ("not json", None)):
        (d / "calls.json").write_text(cached, encoding="utf-8")
        os.utime(d / "calls.json", ns=(4 * 10**18, 4 * 10**18))
        got = art.extract_code(t)
        assert got == expected if expected else got[0]["kind"] == "bash"
    os.utime(d / "calls.json", ns=(4 * 10**18, 4 * 10**18))
    (d / "calls.json").write_text('[{"kind": "cached"}]', encoding="utf-8")
    os.utime(d / "calls.json", ns=(4 * 10**18, 4 * 10**18))
    assert art.extract_code(t, write=False)[0]["kind"] == "bash", "write=False never reads the cache"


def test_find_transcripts(tmp_path):
    for rel in ("m/B/medium/P-a-01-k1.jsonl", "m/B/medium/P-a-01-k12.jsonl", "draw/transcript.jsonl",
                "_sandbox_probe/x-k1.jsonl", "views/y-k1.jsonl", "plan-k1.jsonl", "notes.jsonl", "a-k1.jsonl.bak",
                "a-kx.jsonl"):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text("", encoding="utf-8")
    got = [p.relative_to(tmp_path).as_posix() for p in art.find_transcripts(tmp_path)]
    assert got == ["draw/transcript.jsonl", "m/B/medium/P-a-01-k1.jsonl", "m/B/medium/P-a-01-k12.jsonl"]


def test_cli_prints_every_count_over_several_runs(tmp_path, capsys):
    good = base64.b64encode(b"img").decode()
    _write(tmp_path / "r1/P-x-01-k1.jsonl", [
        _use("a", "Bash", {"command": "cat > f.py <<EOF\nx\nEOF"}),
        _res("a", [{"type": "image", "source": {"data": good}}])])
    _write(tmp_path / "r2/P-y-01-k1.jsonl", [_use("m", "mcp__s__t", {})])
    _write(tmp_path / "r2/P-z-01-k1.jsonl", [_use("r", "Read", {})])
    assert art.main(["--runs", str(tmp_path / "r1"), "--runs", str(tmp_path / "r2")]) == 0
    assert capsys.readouterr().out == "runs with code: 2, code entries: 3, images: 1, files: 4\n"
    with pytest.raises(SystemExit):
        art.main([])


# ---------------------------------------------------------------- edge cases
def test_safe_name_strips_only_dots_and_underscores_at_the_ends():
    assert art._safe_name("X.pyX", "fb") == "X.pyX"


def test_answer_texts_keeps_the_result_before_later_assistant_texts(tmp_path):
    t = _write(tmp_path / "o-k1.jsonl", [
        {"type": "result", "result": "first"},
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "a"}]}},
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "b"}]}},
    ])
    assert art.answer_texts(t) == ["first", "a", "b"]


def test_scan_tool_calls_reads_on_after_a_plain_block_and_a_duplicate(tmp_path):
    use = {"type": "tool_use", "id": "a", "name": "Bash", "input": {}}
    t = _write(tmp_path / "d-k1.jsonl", [
        {"type": "assistant", "message": {"content": ["plain", use]}},
        {"type": "assistant", "message": {"content": [use, {"type": "tool_use", "id": "b", "name": "Read",
                                                             "input": {}}]}},
    ])
    uses, _ = art.scan_tool_calls(t)
    assert [u["id"] for u in uses] == ["a", "b"]
    only = _write(tmp_path / "p-k1.jsonl", [{"type": "assistant", "message": {"content": ["plain", use]}}])
    assert [u["id"] for u in art.scan_tool_calls(only)[0]] == ["a"]


def test_scan_tool_calls_dedupes_only_on_non_empty_string_ids(tmp_path):
    def use(i, n):
        return {"type": "tool_use", "id": i, "name": "Bash", "input": {"command": f"echo {n}"}}

    ids = [["x"], {"a": 1}, "", "", None, None, "a", "a"]
    t = _write(tmp_path / "d-k1.jsonl", [{"type": "assistant", "message": {"content": [use(i, n)]}}
                                         for n, i in enumerate(ids)])
    uses, _ = art.scan_tool_calls(t)
    assert [u["input"]["command"] for u in uses] == [f"echo {n}" for n in range(7)]


def test_scan_tool_calls_unhashable_ids_in_uses_and_results_do_not_raise(tmp_path):
    use = {"type": "tool_use", "id": ["x"], "name": "Bash", "input": {"command": "echo 0"}}
    ok = {"type": "tool_use", "id": "a", "name": "Bash", "input": {"command": "echo 1"}}
    t = _write(tmp_path / "e-k1.jsonl", [
        {"type": "assistant", "message": {"content": [use, ok]}},
        {"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": ["x"], "content": "bad"},
            {"type": "tool_result", "tool_use_id": {"k": 1}, "content": "bad"},
            {"type": "tool_result", "tool_use_id": "a", "content": "good"}]}}])
    uses, results = art.scan_tool_calls(t)
    assert [u["input"]["command"] for u in uses] == ["echo 0", "echo 1"]
    assert results == {"a": {"type": "tool_result", "tool_use_id": "a", "content": "good"}}


def test_extract_code_with_a_list_or_dict_tool_use_id_does_not_raise(tmp_path):
    uses = [{"type": "tool_use", "id": i, "name": "Bash", "input": {"command": f"echo {n}"}}
            for n, i in enumerate([["x"], {"a": 1}, "a"])]
    t = _write(tmp_path / "f-k1.jsonl", [
        {"type": "assistant", "message": {"content": uses}},
        {"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": "a", "content": "good"}]}}])
    calls = art.extract_code(t, write=False)
    assert [c["exit"] for c in calls if c["kind"] == "bash"] == [None, None, 0]


def test_iter_events_counts_nothing_but_keeps_a_truncated_progress_line_out_of_the_events(tmp_path):
    t = tmp_path / "t.jsonl"
    prog = json.dumps({"type": "system", "subtype": "thinking_tokens", "uuid": "abc"})
    t.write_text('{"a": 1}\n' + prog[:-5], encoding="utf-8")
    assert list(art.iter_events(t)) == [{"a": 1}]


def test_iter_events_drops_thinking_token_progress_lines(tmp_path):
    t = tmp_path / "t.jsonl"
    prog = json.dumps({"type": "system", "subtype": "thinking_tokens", "estimated_tokens": 3})
    t.write_text(prog + '\n{"a": 1}\n' + prog + '\n{"type": "system", "subtype": "init"}\n', encoding="utf-8")
    assert list(art.iter_events(t)) == [{"a": 1}, {"type": "system", "subtype": "init"}]


def test_heredoc_terminator_with_leading_tabs_only_for_the_dash_form():
    hs, _ = art.split_heredocs("cat > a <<-EOF\n  EOF\nXEOF\n\tEOF")
    assert hs[0]["body"] == "  EOF\nXEOF\n", "<<- strips tabs only, not blanks or other characters"


def test_extract_code_numbers_files_across_calls(tmp_path):
    calls, _ = _calls(tmp_path, [
        _use("b1", "Bash", {"command": "cat > a.py <<E\nx\nE"}),
        _use("b2", "Bash", {"command": "cat > b.py <<E\ny\nE"}),
        _use("m1", "mcp__s__one", {}),
        _use("m2", "mcp__s__two", {}),
        _use("m3", "mcp__", {}),
    ], write=False)
    assert [c["path"] for c in calls] == ["00_cmd.sh", "01_a.py", "02_cmd.sh", "03_b.py", "04_mcp_one.json",
                                          "05_mcp_two.json", "06_mcp_tool.json"]


def test_extract_code_images_after_a_bad_one_and_of_a_nameless_tool(tmp_path):
    raw = b"picture-bytes"
    good = base64.b64encode(raw).decode()
    wrapped = good[:8] + "\n" + good[8:]  # wrapped base64 is accepted, as by `base64 -d`
    content = [{"type": "image", "source": {"data": "abc"}}, {"type": "image", "source": {"data": ""}},
               {"type": "image", "source": {"data": wrapped}}]
    nameless = {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "x", "input": {}}]}}
    calls, _ = _calls(tmp_path, [nameless, _res("x", content)], write=False)
    assert [(c["path"], c["tool"], c["sha256"]) for c in calls] == [("mcp_image_1.png", "", _sha(raw))]


def test_cli_help_names_the_command_and_the_option(capsys):
    with pytest.raises(SystemExit):
        art.main(["--help"])
    out = capsys.readouterr().out
    assert "Save the code the solver models wrote, next to the transcript." in out
    assert "RUNS  run directory (repeatable)" in out


def test_the_transcript_cache_parses_a_file_once_and_again_when_it_changes(tmp_path, monkeypatch):
    f = tmp_path / "t-k1.jsonl"
    f.write_text(json.dumps(_use("a", "Bash", {"command": "ls"})) + "\n", encoding="utf-8")
    parsed = []
    real = art.read_transcript
    monkeypatch.setattr(art, "read_transcript", lambda p: parsed.append(p) or real(p))
    cache = art.TranscriptCache()
    first = cache(f)
    assert cache(f) is first and cache(str(f)) is first and len(parsed) == 1
    f.write_text(f.read_text(encoding="utf-8") * 2, encoding="utf-8")  # another size: read again
    assert cache(f) is not first and len(parsed) == 2


def test_the_transcript_cache_keeps_at_most_its_budget(tmp_path, monkeypatch):
    files = []
    for n in range(3):
        f = tmp_path / f"t{n}-k1.jsonl"
        f.write_text(json.dumps(_use("a", "Bash", {"command": "ls"})) + "\n", encoding="utf-8")
        files.append(f)
    size = files[0].stat().st_size
    cache = art.TranscriptCache(max_bytes=2 * size)
    kept = [cache(f) for f in files]
    assert cache(files[2]) is kept[2] and cache(files[1]) is kept[1]  # the two newest stay
    assert cache(files[0]) is not kept[0]  # the oldest was dropped
    assert cache._size <= 2 * size
    tiny = art.TranscriptCache(max_bytes=size - 1)  # a file over the budget is never kept
    assert tiny(files[0]) is not tiny(files[0]) and tiny._size == 0
