"""Exact behaviour of the helpers in src/tsbench/conditions/sandbox.py that the probe tests do not reach."""
from __future__ import annotations

import pathlib
import socket
from typing import Any

import pytest

from tsbench.conditions import sandbox


def test_within_compares_resolved_paths_and_says_no_on_an_error(tmp_path, monkeypatch):
    inner = tmp_path / "a" / "b"
    inner.mkdir(parents=True)
    assert sandbox._within(str(inner), str(tmp_path)) is True
    assert sandbox._within(str(tmp_path), str(inner)) is False
    assert sandbox._within(str(inner / ".." / ".."), str(tmp_path)) is True

    def broken(self, *a, **k):
        raise OSError("loop")

    monkeypatch.setattr(pathlib.Path, "resolve", broken)
    assert sandbox._within(str(inner), str(tmp_path)) is False

    def bad_value(self, *a, **k):
        raise ValueError("embedded null")

    monkeypatch.setattr(pathlib.Path, "resolve", bad_value)
    assert sandbox._within(str(inner), str(tmp_path)) is False


def test_localhost_listening_sees_an_open_and_a_closed_port():
    with socket.socket() as srv:
        srv.bind(("127.0.0.1", 0))
        srv.listen(1)
        port = srv.getsockname()[1]
        assert sandbox.localhost_listening(f"http://127.0.0.1:{port}/") is True
    assert sandbox.localhost_listening(f"http://127.0.0.1:{port}/", timeout_s=0.5) is False  # closed again


def test_localhost_listening_passes_host_port_and_timeout_on(monkeypatch):
    seen = []

    class Conn:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(sandbox.socket, "create_connection",
                        lambda addr, timeout: seen.append((addr, timeout)) or Conn())
    assert sandbox.localhost_listening("http://example.test:8123/x", 2.5) is True
    assert sandbox.localhost_listening("http://example.test/x") is True  # no port: 80
    assert seen == [(("example.test", 8123), 2.5), (("example.test", 80), 1.0)]


def result_event(content, kind="user"):
    return {"type": kind, "message": {"content": content}}


def test_tool_result_texts_reads_strings_and_text_blocks_of_user_events_only():
    events: list[Any] = [
        "not an event",
        None,
        result_event([{"type": "tool_result", "content": "PROBE_Z rc=9"}], kind="assistant"),
        {"type": "user"},
        result_event("not a list"),
        result_event(None),
        result_event([{"type": "text", "text": "prose PROBE_P rc=7"}, "str", 5,
                      {"type": "tool_result", "content": "PROBE_A rc=0"}]),
        result_event([{"type": "tool_result", "content": [{"type": "text", "text": "PROBE_B rc=1"},
                                                           {"type": "image"}, "str", {"type": "text"}]}]),
        result_event([{"type": "tool_result", "content": 5}, {"type": "tool_result"}]),
        result_event([{"type": "tool_result", "content": "PROBE_C rc=2"}]),
    ]
    assert sandbox._tool_result_texts(events) == ["PROBE_A rc=0", "PROBE_B rc=1", "", "PROBE_C rc=2"]
    assert sandbox.parse_markers(events) == {"A": [0], "B": [1], "C": [2]}


def test_detect_container_prefers_docker_then_podman(monkeypatch):
    present = {"docker": "/usr/bin/docker", "podman": "/usr/bin/podman"}
    monkeypatch.setattr(sandbox.shutil, "which", lambda tool: present.get(tool))
    assert sandbox.detect_container() == "docker"
    del present["docker"]
    assert sandbox.detect_container() == "podman"
    del present["podman"]
    assert sandbox.detect_container() is None


def test_escape_requested_looks_only_at_tool_use_input_of_assistant_events():
    def use(**inp):
        blocks = [{"type": "text", "text": "dangerouslyDisableSandbox"}, "str",
                  {"type": "tool_use", "name": "Bash", "input": inp}]
        return {"type": "assistant", "message": {"content": blocks}}

    assert sandbox.escape_requested([use(command="ls")]) is False
    assert sandbox.escape_requested([use(command="ls", dangerouslyDisableSandbox=True)]) is True
    assert sandbox.escape_requested([use(command="echo dangerouslyDisableSandbox")]) is True
    others: list[Any] = ["junk", {"type": "user", "message": {"content": [
        {"type": "tool_use", "input": {"dangerouslyDisableSandbox": True}}]}}, {"type": "assistant"},
        {"type": "assistant", "message": {"content": None}}, use(command="ls"),
        {"type": "assistant", "message": {"content": [{"type": "tool_use"}]}}]
    assert sandbox.escape_requested(others) is False
    assert sandbox.escape_requested([{"type": "assistant", "message": {"content": [
        {"type": "tool_use", "input": {"dangerouslyDisableSandbox": True}}]}}]) is True
    assert sandbox.escape_requested([]) is False


@pytest.mark.parametrize("value", [False, None, "false", "False", 0, ""])
def test_an_escape_flag_set_to_false_asks_for_nothing(value):
    # qwen3-30b-a3b-instruct-2507 sends dangerouslyDisableSandbox: false with every Bash call
    use = {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "name": "Bash", "input": {"command": "ls", "dangerouslyDisableSandbox": value}}]}}
    assert sandbox.escape_requested([use]) is False


@pytest.mark.parametrize("value", [True, "true", 1, "yes"])
def test_an_escape_flag_set_to_anything_else_asks_to_escape(value):
    assert sandbox.asks_to_escape({"command": "ls", "dangerouslyDisableSandbox": value}) is True


def test_the_flag_name_elsewhere_in_the_input_still_counts_when_the_flag_is_false():
    assert sandbox.asks_to_escape({"command": "echo dangerouslyDisableSandbox",
                                   "dangerouslyDisableSandbox": False}) is True


def test_evaluate_reports_each_reason_in_order():
    ok = {n: [0] for n in sandbox.MUST_BE_ZERO} | {n: [1] for n in sandbox.MUST_FAIL}
    assert sandbox.evaluate(ok, [], False) == (True, [])
    bad = dict(ok)
    bad.pop("CTRL1")
    bad["NUMPY"] = [0, 3]
    bad["READ"] = [0]
    del bad["VENV"]
    passed, reasons = sandbox.evaluate(bad, ["wrong tools"], True)
    assert passed is False
    assert reasons == [
        "CTRL1 missing: Bash did not run the script",
        f"NUMPY rc=[0, 3], expected 0 ({sandbox.ZERO_HINTS['NUMPY']})",
        "VENV missing",
        "READ rc=[0]: the forbidden action succeeded",
        "a tool_use asked for dangerouslyDisableSandbox",
        "init check failed: wrong tools"]
    assert sandbox.evaluate({**ok, "CTRL1": [2]}, [], False)[1] == [
        f"CTRL1 rc=[2], expected 0 ({sandbox.ZERO_HINTS['CTRL1']})"]
    assert sandbox.evaluate(ok, ["a", "b"], False)[1] == ["init check failed: a; b"]
    passed, reasons = sandbox.evaluate(ok, [], False, not_tested=("VENV",))
    assert passed is False and reasons == ["VENV not tested: " + sandbox.PROBE_TARGETS["VENV"]
                                           + " does not exist in the repository"]
    assert sandbox.evaluate({k: v for k, v in ok.items() if k != "VENV"}, [], False, not_tested=("VENV",))[1] == [
        "VENV not tested: " + sandbox.PROBE_TARGETS["VENV"] + " does not exist in the repository"]


def test_method_info_for_every_state_of_the_probe(monkeypatch):
    monkeypatch.setattr(sandbox, "detect_container", lambda: None)
    assert sandbox.method_info(None, True) == {"method": "dry-run (not probed)", "reason": None, "container": None,
                                               "probe": None}
    assert sandbox.method_info({"passed": True}, True)["method"] == "dry-run (not probed)"
    assert sandbox.method_info(None, False) == {"method": "not yet probed", "reason": None, "container": None,
                                                "probe": None}
    ok = {"passed": True, "reasons": []}
    assert sandbox.method_info(ok, False) == {"method": "builtin", "reason": None, "container": None, "probe": ok}
    unclear = {"passed": None, "reasons": ["API Error: 500", "again"]}
    assert sandbox.method_info(unclear, False) == {
        "method": "not evaluable", "reason": "sandbox probe not evaluable: API Error: 500; again", "container": None,
        "probe": unclear}
    failed = {"passed": False, "reasons": ["READ rc=[0]", "VENV missing"]}
    assert sandbox.method_info(failed, False) == {
        "method": "skipped", "reason": "builtin sandbox probe failed: READ rc=[0]; VENV missing",
        "container": "no docker/podman on PATH; not built: only used if builtin fails", "probe": failed}
    monkeypatch.setattr(sandbox, "detect_container", lambda: "podman")
    assert sandbox.method_info({}, False)["container"] == "podman found; not built: only used if builtin fails"
    assert sandbox.method_info({}, False)["reason"] == "builtin sandbox probe failed: "


def test_load_reusable_probe_needs_every_field_to_match(tmp_path):
    import json

    def write(**kw):
        rec = {"passed": True, "claude_version": "2.1", "settings_sha256": "S", "b_stack_sha256": "B",
               "probe_script_sha256": "P", "auth_mode": "direct", **kw}
        (tmp_path / sandbox.PROBE_FILENAME).write_text(json.dumps(rec), encoding="utf-8")
        return rec

    def load(**kw):
        args = {"claude_version": "2.1", "settings_hash": "S", "b_stack_sha256": "B", "script_sha256": "P", **kw}
        return sandbox.load_reusable_probe(tmp_path, args.pop("claude_version"), args.pop("settings_hash"), **args)

    assert load() is None  # no file
    rec = write()
    assert load() == rec and load(auth="direct") == rec
    assert load(auth="gateway") is None
    assert load(claude_version="2.2") is None and load(settings_hash="T") is None
    assert load(b_stack_sha256=None) is None and load(script_sha256="Q") is None
    write(passed=False)
    assert load() is None
    write(passed=None)
    assert load() is None
    write(fake=True)
    assert load() is None
    (tmp_path / sandbox.PROBE_FILENAME).write_text("[1]", encoding="utf-8")
    assert load() is None
    (tmp_path / sandbox.PROBE_FILENAME).write_text("not json", encoding="utf-8")
    assert load() is None
    write(b_stack_sha256=None)
    assert load(b_stack_sha256=None) is not None
    write()
    assert sandbox.load_reusable_probe(tmp_path, "2.1", "S", "B", script_sha256=None) is None  # default: this host's
