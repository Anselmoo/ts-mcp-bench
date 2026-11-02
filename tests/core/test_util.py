"""Tests for tsbench.core.util: the small helpers that runner, plan and doctor share.

Subprocess calls are replaced by stubs, so no real git or claude runs here.
"""
from __future__ import annotations

import hashlib
import io
import subprocess
from types import SimpleNamespace

import pytest

from tsbench.core import util


def _stub_run(monkeypatch, stdout="", returncode=0, exc=None):
    calls = []

    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        if exc is not None:
            raise exc
        return SimpleNamespace(stdout=stdout, returncode=returncode)

    monkeypatch.setattr(util.subprocess, "run", fake_run)
    return calls


# ---------------------------------------------------------------- write_text_atomic
def test_write_text_atomic_writes_utf_8_and_leaves_no_temp_file(tmp_path):
    target = tmp_path / "a" / "b.txt"
    util.write_text_atomic(target, "café naïve\n")
    assert target.read_bytes() == "café naïve\n".encode()
    assert [p.name for p in target.parent.iterdir()] == ["b.txt"]
    util.write_text_atomic(target, "second")
    assert target.read_text(encoding="utf-8") == "second"


def test_write_text_atomic_keeps_the_old_file_when_the_write_fails(tmp_path, monkeypatch):
    target = tmp_path / "f.txt"
    target.write_text("old", encoding="utf-8")

    def boom(self, target):
        raise OSError("disk full")

    monkeypatch.setattr(util.pathlib.Path, "replace", boom)
    with pytest.raises(OSError, match="disk full"):
        util.write_text_atomic(target, "new")
    assert target.read_text(encoding="utf-8") == "old"
    assert [p.name for p in tmp_path.iterdir()] == ["f.txt"]


def test_two_writes_to_one_path_use_different_temp_names(tmp_path, monkeypatch):
    names = []
    real = util.pathlib.Path.replace
    monkeypatch.setattr(util.pathlib.Path, "replace", lambda self, t: (names.append(self.name), real(self, t))[1])
    util.write_text_atomic(tmp_path / "f.txt", "1")
    util.write_text_atomic(tmp_path / "f.txt", "2")
    assert len(set(names)) == 2


# ---------------------------------------------------------------- sha256_file
def test_sha256_file_hashes_the_bytes(tmp_path):
    f = tmp_path / "f.bin"
    f.write_bytes(b"abc\r\n\xff")
    assert util.sha256_file(f) == hashlib.sha256(b"abc\r\n\xff").hexdigest()
    assert util.sha256_file(str(f)) == util.sha256_file(f)


def test_sha256_file_raises_oserror_for_a_missing_file(tmp_path):
    with pytest.raises(OSError):
        util.sha256_file(tmp_path / "missing")


# ---------------------------------------------------------------- git_output
def test_git_output_asks_git_in_the_given_repo_and_decodes_utf_8(monkeypatch, tmp_path):
    calls = _stub_run(monkeypatch, stdout=" abc123 \n")
    assert util.git_output(tmp_path, "rev-parse", "HEAD") == "abc123"
    args, kwargs = calls[0]
    assert args == ["git", "-C", str(tmp_path), "rev-parse", "HEAD"]
    assert kwargs == {"capture_output": True, "text": True, "encoding": "utf-8", "timeout": 30}


@pytest.mark.parametrize("returncode", [1, 128])
def test_git_output_is_none_when_git_fails(monkeypatch, tmp_path, returncode):
    _stub_run(monkeypatch, stdout="fatal\n", returncode=returncode)
    assert util.git_output(tmp_path, "status") is None


@pytest.mark.parametrize("exc", [OSError("no git"), subprocess.TimeoutExpired("git", 30)])
def test_git_output_is_none_when_git_is_missing_or_hangs(monkeypatch, tmp_path, exc):
    _stub_run(monkeypatch, exc=exc)
    assert util.git_output(tmp_path, "status") is None


def test_git_output_returns_an_empty_answer_as_it_is(monkeypatch, tmp_path):
    _stub_run(monkeypatch, stdout="")
    assert util.git_output(tmp_path, "status", "--porcelain") == ""  # an empty answer is a clean tree, not a failure


# ---------------------------------------------------------------- claude_version
def test_claude_version_reads_the_version_line(monkeypatch):
    calls = _stub_run(monkeypatch, stdout="  2.1.0 (Claude Code)\n")
    assert util.claude_version("/bin/claude") == "2.1.0 (Claude Code)"
    assert calls[0][0] == ["/bin/claude", "--version"]
    assert calls[0][1] == {"capture_output": True, "text": True, "encoding": "utf-8", "timeout": 30}


def test_claude_version_passes_env_and_cwd_when_given(monkeypatch, tmp_path):
    calls = _stub_run(monkeypatch, stdout="2.1.0\n")
    assert util.claude_version("/bin/claude", env={"A": "1"}, cwd=tmp_path) == "2.1.0"
    assert calls[0][1]["env"] == {"A": "1"} and calls[0][1]["cwd"] == tmp_path


def test_claude_version_is_none_for_empty_output_or_a_failing_call(monkeypatch):
    _stub_run(monkeypatch, stdout="\n")
    assert util.claude_version("/bin/claude") is None
    _stub_run(monkeypatch, exc=OSError("broken"))
    assert util.claude_version("/bin/claude") is None
    _stub_run(monkeypatch, exc=subprocess.TimeoutExpired("claude", 30))
    assert util.claude_version("/bin/claude") is None


# ---------------------------------------------------------------- env_int
@pytest.mark.parametrize("raw, want", [(None, 4), ("", 4), ("  ", 4), ("0", 0), (" 2 ", 2), ("-3", 0), ("x", 4),
                                       ("1.5", 4)])
def test_env_int_reads_a_non_negative_integer_or_falls_back(raw, want):
    env = {} if raw is None else {"N": raw}
    assert util.env_int(env, "N", 4) == want


# ---------------------------------------------------------------- use_utf8_streams
def test_use_utf8_streams_reconfigures_the_std_streams(monkeypatch):
    seen = []

    class Stream:
        def __init__(self, name):
            self.name = name

        def reconfigure(self, **kw):
            seen.append((self.name, kw))

    monkeypatch.setattr(util.sys, "stdin", Stream("in"))
    monkeypatch.setattr(util.sys, "stdout", Stream("out"))
    util.use_utf8_streams()
    assert seen == [("in", {"encoding": "utf-8"}), ("out", {"encoding": "utf-8"})]


def test_use_utf8_streams_skips_streams_that_cannot_be_reconfigured(monkeypatch):
    monkeypatch.setattr(util.sys, "stdin", io.StringIO("x"))
    monkeypatch.setattr(util.sys, "stdout", io.StringIO())
    util.use_utf8_streams()  # a StringIO has no reconfigure: nothing happens, nothing raises
