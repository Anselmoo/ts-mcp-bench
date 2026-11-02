"""Tests for tsbench.plan.pins: the live environment pins, the drift check and the two probes.

The subprocess and PATH lookups are replaced by stubs, so no real git or claude runs here.
"""
from __future__ import annotations

import importlib.metadata
import subprocess
from types import SimpleNamespace

import pytest

from tsbench.core import util
from tsbench.plan import pins as X


def _stub_run(monkeypatch, stdout="", returncode=0, exc=None):
    calls = []

    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        if exc is not None:
            raise exc
        return SimpleNamespace(stdout=stdout, returncode=returncode)

    monkeypatch.setattr(util.subprocess, "run", fake_run)
    return calls


def test_git_commit_asks_git_for_head_of_the_repo(monkeypatch):
    calls = _stub_run(monkeypatch, stdout="abc123\n")
    assert X._git_commit() == "abc123"
    args, kwargs = calls[0]
    assert args == ["git", "-C", str(X.REPO_ROOT), "rev-parse", "HEAD"]
    assert kwargs == {"capture_output": True, "text": True, "encoding": "utf-8", "timeout": 30}


@pytest.mark.parametrize("returncode", [1, 128])
def test_git_commit_is_none_when_git_fails(monkeypatch, returncode):
    _stub_run(monkeypatch, stdout="fatal\n", returncode=returncode)
    assert X._git_commit() is None


def test_git_commit_is_none_when_git_is_missing(monkeypatch):
    _stub_run(monkeypatch, exc=OSError("no git"))
    assert X._git_commit() is None
    _stub_run(monkeypatch, exc=subprocess.TimeoutExpired("git", 30))
    assert X._git_commit() is None


def test_claude_version_reads_the_version_line(monkeypatch):
    import shutil
    monkeypatch.setattr(shutil, "which", lambda name: "/bin/claude" if name == "claude" else None)
    calls = _stub_run(monkeypatch, stdout="2.1.0 (Claude Code)\n")
    assert X.claude_version_probe() == "2.1.0 (Claude Code)"
    assert calls[0][0] == ["/bin/claude", "--version"]
    assert calls[0][1] == {"capture_output": True, "text": True, "encoding": "utf-8", "timeout": 30}


def test_claude_version_is_none_without_claude_or_output(monkeypatch):
    import shutil
    monkeypatch.setattr(shutil, "which", lambda name: None)
    assert X.claude_version_probe() is None
    monkeypatch.setattr(shutil, "which", lambda name: "/bin/claude")
    _stub_run(monkeypatch, stdout="\n")
    assert X.claude_version_probe() is None
    _stub_run(monkeypatch, exc=OSError("broken"))
    assert X.claude_version_probe() is None
    _stub_run(monkeypatch, exc=subprocess.TimeoutExpired("claude", 30))
    assert X.claude_version_probe() is None


def test_live_pins_look_up_the_package_by_its_name(monkeypatch):
    seen = []
    real = importlib.metadata.version

    def spy(name):
        seen.append(name)
        return real(name)

    monkeypatch.setattr(importlib.metadata, "version", spy)
    pins = X.live_pins(None)
    assert "tanabesugano" in seen and pins["tanabesugano"] == real("tanabesugano")


def test_live_pins_keep_given_digests_and_do_not_compute_them(monkeypatch):
    from tsbench.conditions import sandbox
    monkeypatch.setattr(sandbox, "settings_sha256", lambda repo: (_ for _ in ()).throw(AssertionError("probed")))
    pins = X.live_pins("9.9.9", sandbox_settings_sha256="ab" * 32, b_stack_sha256="cd" * 32)
    assert pins["claude_cli_version"] == "9.9.9"
    assert pins["sandbox_settings_sha256"] == "ab" * 32 and pins["b_stack_sha256"] == "cd" * 32


def test_live_pins_hash_the_settings_of_the_given_b_venv(tmp_path):
    from tsbench.conditions import sandbox
    venv = tmp_path / "other-venv-B"
    venv.mkdir()
    got = X.live_pins(None, b_venv=venv)["sandbox_settings_sha256"]
    assert got == sandbox.settings_sha256(X.REPO_ROOT, b_venv=venv.absolute())
    assert got != X.live_pins(None)["sandbox_settings_sha256"]


def test_live_pins_refuse_a_b_venv_inside_the_repo():
    from tsbench.conditions import b_stack
    with pytest.raises(b_stack.BStackError, match="lies inside the repo"):
        X.live_pins(None, b_venv=X.REPO_ROOT / "venv-B")


def test_check_pins_reports_a_changed_claude_version():
    drift = X.check_pins({"claude_cli_version": "1.0"}, {"claude_cli_version": "2.0"})
    assert drift == [{"pin": "claude_cli_version", "planned": "1.0", "live": "2.0"}]


def test_check_pins_skips_claude_version_only_when_one_side_is_unknown():
    assert X.check_pins({"claude_cli_version": None}, {"claude_cli_version": "2.0"}) == []
    assert X.check_pins({"claude_cli_version": "1.0"}, {"claude_cli_version": None}) == []


def test_check_pins_skips_the_b_stack_only_when_one_side_is_unknown():
    assert X.check_pins({"b_stack_sha256": None}, {"b_stack_sha256": "a"}) == []
    assert X.check_pins({"b_stack_sha256": "a"}, {"b_stack_sha256": None}) == []
    assert X.check_pins({"b_stack_sha256": "a"}, {"b_stack_sha256": "b"}) == [
        {"pin": "b_stack_sha256", "planned": "a", "live": "b"}]


def test_check_pins_compares_other_pins_exactly():
    assert X.check_pins({"python": "3.12"}, {"python": "3.12"}) == []
    assert X.check_pins({"python": None}, {"python": "3.12"}) == [
        {"pin": "python", "planned": None, "live": "3.12"}]


def test_check_pins_ignores_answer_schemas_added_later_but_not_changed_ones():
    planned = {"answer_schemas": {"fit": "a"}}
    assert X.check_pins(planned, {"answer_schemas": {"fit": "a", "curve": "b"}}) == []
    assert X.check_pins(planned, {"answer_schemas": {"fit": "z", "curve": "b"}}) == [
        {"pin": "answer_schemas", "planned": {"fit": "a"}, "live": {"fit": "z"}}]


def test_check_pins_keeps_the_live_value_of_a_non_schema_pin_unfiltered():
    drift = X.check_pins({"python": "3.12"}, {"python": {"x": 1}})
    assert drift == [{"pin": "python", "planned": "3.12", "live": {"x": 1}}]


def test_check_pins_reports_a_missing_answer_schemas_pin():
    drift = X.check_pins({"answer_schemas": {"fit": "a"}}, {})
    assert drift == [{"pin": "answer_schemas", "planned": {"fit": "a"}, "live": None}]


def test_live_pins_do_not_hash_the_conditions_source():
    # the argv is verified against the plan per run; a comment edit in conditions/__init__.py must not be drift
    assert "conditions_py_sha256" not in X.live_pins(None)


def test_check_pins_ignores_a_conditions_source_hash_in_the_plan():
    assert X.check_pins({"conditions_py_sha256": "a" * 64, "python": "3.12"}, {"python": "3.12"}) == []


def _pins_node(node):
    """The `pins` object schema inside the plan schema."""
    if isinstance(node, dict):
        if "conditions_py_sha256" in node.get("properties", {}):
            return node
        node = list(node.values())
    for v in node if isinstance(node, list) else []:
        found = _pins_node(v)
        if found:
            return found
    return None


def test_the_plan_schema_does_not_require_the_conditions_source_hash():
    import json

    from tsbench.core import resource
    node = _pins_node(json.loads(resource("schemas/plan.schema.json").read_text(encoding="utf-8")))
    assert "conditions_py_sha256" not in node["required"]
    assert "conditions_py_sha256" in node["properties"]  # a plan may still carry it
