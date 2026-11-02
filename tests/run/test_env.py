"""Tests for the record helpers in src/tsbench/run/env.py (redact, host_label).

Run: python -m pytest tests/run/test_env.py -q
"""
from __future__ import annotations

import inspect
import os
from typing import Any

import pytest

from tsbench.run import env

HOME_PAIRS = [("/home/jo", "<HOME>")]


def test_redact_does_not_rewrite_a_longer_name_that_starts_with_the_prefix():
    assert env.redact("/home/joanna/x", HOME_PAIRS) == "/home/joanna/x"
    assert env.redact("/home/jo_old/x /home/jo-2 /home/jo9", HOME_PAIRS) == "/home/jo_old/x /home/jo-2 /home/jo9"


def test_redact_rewrites_the_prefix_at_the_end_of_a_path_or_a_text():
    assert env.redact("/home/jo", HOME_PAIRS) == "<HOME>"
    assert env.redact("/home/jo/x/y", HOME_PAIRS) == "<HOME>/x/y"
    assert env.redact("PATH=/usr/bin:/home/jo:/bin", HOME_PAIRS) == "PATH=/usr/bin:<HOME>:/bin"
    assert env.redact('cannot open "/home/jo" (denied). See /home/jo.', HOME_PAIRS) == (
        'cannot open "<HOME>" (denied). See <HOME>.')
    assert env.redact("a /home/joanna and /home/jo/b", HOME_PAIRS) == "a /home/joanna and <HOME>/b"


def test_redact_walks_lists_tuples_and_dicts_and_keeps_other_values():
    obj = {"p": ["/home/jo/a", ("/home/joanna/b",)], "n": 3, "none": None}
    assert env.redact(obj, HOME_PAIRS) == {"p": ["<HOME>/a", ["/home/joanna/b"]], "n": 3, "none": None}


def test_redact_with_a_prefix_that_ends_in_a_slash():
    assert env.redact("/tmp/abc", [("/tmp/", "<TMP>/")]) == "<TMP>/abc"


def test_redact_longest_prefix_first():
    pairs = [("/home/jo/work", "<WORK>"), ("/home/jo", "<HOME>")]
    assert env.redact("/home/jo/work/x /home/jo/y", pairs) == "<WORK>/x <HOME>/y"


def test_host_label_label_salt_and_hash():
    assert env.host_label({"TSBENCH_HOST_LABEL": " box "}, "s") == ("box", "label")
    a, source = env.host_label({}, "plan-1")
    b, _ = env.host_label({"TSBENCH_HOST_SALT": "plan-1"}, "other")
    assert a == b and len(a) == 12 and source == "sha256(hostname+salt)[:12]"
    assert a != env.host_label({}, "plan-2")[0]


def test_host_label_uses_the_module_imports():
    assert "import" not in inspect.getsource(env.host_label)


# ------------------------------------------------------------------ claude_runtime_dirs
def _script(tmp_path, head: bytes) -> str:
    f = tmp_path / "cli.js"
    f.write_bytes(head)
    return str(f)


def _which(seen):
    def which(name, path):
        seen.append((name, path))
        return f"/opt/interp/bin/{name}"

    return which


def test_runtime_dirs_without_a_parent_path_ask_for_an_empty_one(tmp_path):
    seen = []
    env.claude_runtime_dirs(_script(tmp_path, b"#!/usr/bin/env node\n"), which=_which(seen))
    assert seen == [("node", "")]


def test_runtime_dirs_of_an_unreadable_binary_is_just_its_directory(tmp_path):
    assert env.claude_runtime_dirs(str(tmp_path / "gone" / "claude")) == [str((tmp_path / "gone").resolve())]


def test_runtime_dirs_reads_only_the_first_256_bytes_of_the_shebang(tmp_path):
    head = b"#!/usr/bin/env " + b"-" * 100 + b" "
    word = b"n" * (256 - len(head))  # ends at byte 256, followed by one letter that the 256-byte read cuts off
    seen = []
    env.claude_runtime_dirs(_script(tmp_path, head + word + b"X\n"), which=_which(seen))
    assert seen == [(word.decode(), "")]


def test_runtime_dirs_decodes_a_bad_shebang_with_replacement(tmp_path):
    seen = []
    dirs = env.claude_runtime_dirs(_script(tmp_path, b"#!/usr/bin/env node \xff\n"), which=_which(seen))
    assert seen == [("node", "")] and dirs[-1] == "/opt/interp/bin"


def test_runtime_dirs_env_flags_are_skipped_and_only_flags_find_nothing(tmp_path):
    seen = []
    dirs = env.claude_runtime_dirs(_script(tmp_path, b"#!/usr/bin/env -S node --x\n"), which=_which(seen))
    assert seen == [("node", "")] and dirs == [str(tmp_path.resolve()), "/opt/interp/bin"]
    seen.clear()
    assert env.claude_runtime_dirs(_script(tmp_path, b"#!/usr/bin/env -S\n"), which=_which(seen)) == [
        str(tmp_path.resolve())]
    assert seen == []
    assert env.claude_runtime_dirs(_script(tmp_path, b"#!/usr/bin/env\n"), which=_which(seen)) == [
        str(tmp_path.resolve())]


def test_runtime_dirs_direct_interpreter_and_only_the_first_line(tmp_path):
    assert env.claude_runtime_dirs(_script(tmp_path, b"#!/opt/py/bin/python3\nprint(1)\n")) == [
        str(tmp_path.resolve()), "/opt/py/bin"]
    assert env.claude_runtime_dirs(_script(tmp_path, b"#!/opt/py/bin/python3 -u\n")) == [
        str(tmp_path.resolve()), "/opt/py/bin"]
    # an empty shebang line: the second line is not an interpreter
    assert env.claude_runtime_dirs(_script(tmp_path, b"#!\n/opt/foo/python\nmore\n")) == [str(tmp_path.resolve())]
    assert env.claude_runtime_dirs(_script(tmp_path, b"#!\n")) == [str(tmp_path.resolve())]
    # system directories are never added
    assert env.claude_runtime_dirs(_script(tmp_path, b"#!/usr/bin/python3\n")) == [str(tmp_path.resolve())]


# ------------------------------------------------------------------ child env, paths, placeholders
def test_build_child_env_passes_locale_and_shell_and_the_dry_run_hooks(tmp_path):
    parent = {"LANG": "de_DE.UTF-8", "LC_ALL": "C", "SHELL": "/bin/zsh", "HOME": "/home/jo", "FAKE_COST_USD": "0.3",
              "OTHER": "x"}
    kw: dict[str, Any] = {"home": "/h", "config_dir": "/c", "tmpdir": "/t", "repo": tmp_path, "gateway": False}
    live = env.build_child_env(parent, dry_run=False, **kw)
    assert live["LANG"] == "de_DE.UTF-8" and live["LC_ALL"] == "C" and live["SHELL"] == "/bin/zsh"
    assert "PYTHONPATH" not in live and "FAKE_COST_USD" not in live and "OTHER" not in live
    dry = env.build_child_env(parent, dry_run=True, **kw)
    assert dry["PYTHONPATH"] == str(tmp_path) and dry["FAKE_COST_USD"] == "0.3"
    assert "pythonpath" not in dry and "XXPYTHONPATHXX" not in dry


def test_missing_env_names_the_key_variable_exactly():
    assert env.missing_env({}, False) == ["TSMCP_ANTHROPIC_API_KEY (or ANTHROPIC_API_KEY)"]
    assert env.missing_env({"ANTHROPIC_API_KEY": "k"}, False) == []
    assert env.missing_env({"ANTHROPIC_BASE_URL": "u"}, True) == ["ANTHROPIC_AUTH_TOKEN"]


def test_mpl_cache_dir_refuses_a_dir_inside_the_repo(tmp_path, capsys):
    with pytest.raises(env.Abort):
        env.mpl_cache_dir({"TSBENCH_MPLCONFIGDIR": str(tmp_path / "cache")}, tmp_path)
    err = capsys.readouterr().err
    assert err == (f"runner: matplotlib cache {tmp_path / 'cache'} lies inside the repo; "
                   "set TSBENCH_MPLCONFIGDIR elsewhere\n")


def test_path_offenders_collects_from_every_directory_and_skips_bad_ones(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    for d in (a, b):
        d.mkdir()
        (d / "Tanabesugano-mcp").write_text("x", encoding="utf-8")
        (d / "other").write_text("x", encoding="utf-8")
    path = os.pathsep.join(["", str(tmp_path / "missing"), str(a), str(tmp_path / "missing2"), "", str(b)])
    assert env.path_offenders(path) == [str(a / "Tanabesugano-mcp"), str(b / "Tanabesugano-mcp")]
    assert env.path_offenders(path, skip=(str(a),)) == [str(b / "Tanabesugano-mcp")]
    assert env.path_offenders(os.pathsep.join([str(a), "", str(b)]), skip=(str(a),)) == [str(b / "Tanabesugano-mcp")]


def test_placeholder_pairs_add_the_resolved_spelling_and_drop_one_character_paths(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real)
    pairs = env.placeholder_pairs([(link, "<L>"), (None, "<N>"), ("", "<E>"), ("/", "<ROOT>"), ("/a", "<A>")])
    assert dict(pairs) == {str(link): "<L>", str(real): "<L>", "/a": "<A>"}
    assert [len(p) for p, _ in pairs] == sorted((len(p) for p, _ in pairs), reverse=True)
    assert env.placeholder_pairs([("/x", "<ONE>"), ("/x", "<TWO>")]) == [("/x", "<ONE>")]  # the first spelling wins


def test_redact_ignores_an_empty_path():
    assert env.redact("abc", [("", "<X>")]) == "abc"


def test_warm_mpl_cache_builds_the_font_cache_with_a_minimal_env(tmp_path, monkeypatch):
    seen = []
    monkeypatch.setattr(env.subprocess, "run", lambda cmd, **kw: seen.append((cmd, kw)))
    cache = tmp_path / "a" / "mpl"
    own = tmp_path / "python"
    own.write_text("", encoding="utf-8")
    env.warm_mpl_cache(str(cache), own)
    env.warm_mpl_cache(str(cache), tmp_path / "no-python")
    assert cache.is_dir()
    assert seen[0][0][0] == str(own) and seen[1][0][0] == env.sys.executable
    cmd, kw = seen[0]
    assert cmd[1] == "-c" and "font_manager.fontManager" in cmd[2] and "matplotlib.use('Agg')" in cmd[2]
    assert kw == {"env": {"PATH": "/usr/bin:/bin", "HOME": str(cache), "MPLCONFIGDIR": str(cache)},
                  "capture_output": True, "timeout": 600, "check": False}
