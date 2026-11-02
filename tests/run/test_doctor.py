"""Tests for `tsbench doctor` (tsbench.run.doctor): the env, MCP, sandbox and B stack checks and the whole run.

No network, no model call, no key, no real `claude`: every outside call (a subprocess, the MCP server, the
paid probe) is replaced by a small stand-in, and each test checks the row the check returns. The doctor is only ever
run without --probe (or with the env checks alone). The MCP handshake talks to the local stdio server and is
skipped if the server binary is not installed.
"""
from __future__ import annotations

import argparse
import asyncio
import importlib.metadata
import pathlib
import subprocess
from types import SimpleNamespace

import pytest

from tsbench.conditions import sandbox
from tsbench.core import util
from tsbench.run import doctor, runner

REPO_ROOT = runner.REPO_ROOT
SENTINEL = "SENTINEL-must-never-be-printed-9f3a1c"


@pytest.fixture
def clean_env(monkeypatch):
    # the provider keys are already removed by the autouse fixture in tests/conftest.py; the key file and the B venv
    # of the host must not change the settings the doctor renders
    monkeypatch.delenv("TSBENCH_KEY_FILE", raising=False)
    monkeypatch.delenv("TSBENCH_B_VENV", raising=False)
    return monkeypatch


def statuses(rows):
    return {check: status for status, check, _ in rows}


def by_check(rows):
    return {check: (status, detail) for status, check, detail in rows}


# ---------------------------------------------------------------- expected versions
def test_load_expected_returns_empty_dict_for_a_missing_file(tmp_path):
    assert doctor.load_expected(tmp_path / "no-such-file.txt") == {}


def test_parse_expected_skips_lines_with_one_word():
    assert doctor.parse_expected("lonely\nclaude 2.1.3   # note\n") == {"claude": "2.1.3"}


def test_parse_expected_drops_everything_after_the_first_hash():
    text = "# expected versions # two marks\nclaude 2.1.3  # pinned # twice\nlonely #value\n"
    assert doctor.parse_expected(text) == {"claude": "2.1.3"}


def test_load_expected_reads_the_file_as_utf8(monkeypatch, tmp_path):
    path = tmp_path / "expected-versions.txt"
    path.write_text("claude 2.1.3  # pinned\ntanabesugano 2.0.0\n", encoding="utf-8")
    real, reads = pathlib.Path.read_text, []

    def read_text(self, *a, **kw):
        reads.append((self, a, kw))
        return real(self, *a, **kw)

    monkeypatch.setattr(pathlib.Path, "read_text", read_text)
    assert doctor.load_expected(path) == {"claude": "2.1.3", "tanabesugano": "2.0.0"}
    assert [(a, kw) for p, a, kw in reads if p == path] == [((), {"encoding": "utf-8"})]


# ---------------------------------------------------------------- claude_version_string
class _Done:
    def __init__(self, stdout):
        self.stdout = stdout


def test_claude_version_string_is_none_without_claude_on_path(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda *a, **k: None)
    assert doctor.claude_version_string({"PATH": "/nowhere"}) is None


def test_claude_version_string_strips_the_output(monkeypatch):
    seen = {}

    def fake_run(argv, **kw):
        seen["argv"], seen["env"] = argv, kw["env"]
        return _Done("  2.1.3 (Claude Code)\n")

    monkeypatch.setattr("shutil.which", lambda name, path=None: "/opt/bin/claude")
    monkeypatch.setattr(util.subprocess, "run", fake_run)
    assert doctor.claude_version_string({"PATH": "/opt/bin", "X": "1"}) == "2.1.3 (Claude Code)"
    assert seen["argv"] == ["/opt/bin/claude", "--version"]
    assert seen["env"] == {"PATH": "/opt/bin", "X": "1"}


@pytest.mark.parametrize("failure", [OSError("gone"), subprocess.TimeoutExpired("claude", 30)])
def test_claude_version_string_is_none_when_the_call_fails(monkeypatch, failure):
    def boom(*a, **kw):
        raise failure

    monkeypatch.setattr("shutil.which", lambda name, path=None: "/opt/bin/claude")
    monkeypatch.setattr(util.subprocess, "run", boom)
    assert doctor.claude_version_string({"PATH": "/opt/bin"}) is None


def test_claude_version_string_is_none_for_empty_output(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name, path=None: "/opt/bin/claude")
    monkeypatch.setattr(util.subprocess, "run", lambda *a, **kw: _Done("\n"))
    assert doctor.claude_version_string({"PATH": "/opt/bin"}) is None


def test_claude_version_string_looks_up_claude_on_the_path_of_the_given_env(monkeypatch):
    looked = []

    def which(name, path=None):
        looked.append((name, path))
        return "/opt/bin/claude" if name == "claude" else None

    monkeypatch.setattr("shutil.which", which)
    monkeypatch.setattr(util.subprocess, "run", lambda argv, **kw: _Done("2.1.3 (Claude Code)\n"))
    assert doctor.claude_version_string({"PATH": "/opt/bin", "path": "/lower"}) == "2.1.3 (Claude Code)"
    assert looked == [("claude", "/opt/bin")]


def test_claude_version_string_captures_text_output_with_a_30_s_timeout(monkeypatch):
    seen = {}

    def fake_run(argv, **kw):
        seen.update(kw)
        return _Done("2.1.3\n")

    monkeypatch.setattr("shutil.which", lambda name, path=None: "/opt/bin/claude")
    monkeypatch.setattr(util.subprocess, "run", fake_run)
    assert doctor.claude_version_string({"PATH": "/opt/bin"}) == "2.1.3"
    assert seen == {"capture_output": True, "text": True, "encoding": "utf-8", "timeout": 30,
                    "env": {"PATH": "/opt/bin"}}


def test_claude_version_string_reads_os_environ_without_an_env(monkeypatch):
    monkeypatch.setenv("PATH", "/from/os/environ")
    looked, seen = [], {}

    def fake_run(argv, **kw):
        seen["env"] = kw["env"]
        return _Done("2.1.3\n")

    monkeypatch.setattr("shutil.which", lambda name, path=None: looked.append(path) or "/opt/bin/claude")
    monkeypatch.setattr(util.subprocess, "run", fake_run)
    assert doctor.claude_version_string() == "2.1.3"
    assert looked == ["/from/os/environ"]
    assert seen["env"]["PATH"] == "/from/os/environ"


# ---------------------------------------------------------------- check_versions
def _installed(monkeypatch, version):
    def fake_version(name):
        if version is None:
            raise importlib.metadata.PackageNotFoundError(name)
        return version

    monkeypatch.setattr(doctor.importlib.metadata, "version", fake_version)


def test_check_versions_fails_when_tanabesugano_is_missing(monkeypatch):
    _installed(monkeypatch, None)
    monkeypatch.setattr(doctor, "claude_version_string", lambda env=None: None)
    rows = by_check(doctor.check_versions({}, {"tanabesugano": "1.2.3"}))
    assert rows["tanabesugano"] == ("FAIL", "not installed")
    assert rows["claude CLI"][0] == "WARN" and "not found on PATH" in rows["claude CLI"][1]


def test_check_versions_fails_when_the_version_differs(monkeypatch):
    _installed(monkeypatch, "1.0.0")
    monkeypatch.setattr(doctor, "claude_version_string", lambda env=None: "2.1.3 (Claude Code)")
    rows = by_check(doctor.check_versions({}, {"tanabesugano": "1.2.3", "claude": "2.1.3"}))
    assert rows["tanabesugano"] == ("FAIL", "1.0.0, required 1.2.3")
    assert rows["claude CLI"] == ("OK", "2.1.3 (Claude Code) (expected 2.1.3)")


def test_check_versions_ok_and_claude_mismatch_warns(monkeypatch):
    _installed(monkeypatch, "1.2.3")
    monkeypatch.setattr(doctor, "claude_version_string", lambda env=None: "2.0.0 (Claude Code)")
    rows = by_check(doctor.check_versions({}, {"tanabesugano": "1.2.3", "claude": "2.1.3"}))
    assert rows["tanabesugano"] == ("OK", "1.2.3")
    status, detail = rows["claude CLI"]
    assert status == "WARN"
    assert detail == "2.0.0 (Claude Code); differs from expected 2.1.3 (tools/expected-versions.txt)"


def test_check_versions_without_an_expected_claude_reports_unset(monkeypatch):
    _installed(monkeypatch, "1.2.3")
    monkeypatch.setattr(doctor, "claude_version_string", lambda env=None: "2.0.0 (Claude Code)")
    rows = by_check(doctor.check_versions({}, {"tanabesugano": "1.2.3"}))
    assert rows["claude CLI"] == ("OK", "2.0.0 (Claude Code) (expected unset)")


def test_check_versions_without_an_expected_tanabesugano_uses_the_runner_pin(monkeypatch):
    _installed(monkeypatch, runner.REQUIRED_TANABESUGANO)
    monkeypatch.setattr(doctor, "claude_version_string", lambda env=None: "2.1.3 (Claude Code)")
    rows = by_check(doctor.check_versions({}, {}))
    assert rows["tanabesugano"] == ("OK", runner.REQUIRED_TANABESUGANO)


def test_check_versions_names_the_missing_claude_exactly(monkeypatch):
    _installed(monkeypatch, "1.2.3")
    monkeypatch.setattr(doctor, "claude_version_string", lambda env=None: None)
    assert doctor.check_versions({}, {"tanabesugano": "1.2.3", "claude": "2.1.3"}) == [
        ("OK", "tanabesugano", "1.2.3"),
        ("WARN", "claude CLI", "not found on PATH (real runs need it; --dry-run does not)")]


def test_check_versions_asks_claude_with_the_given_env(monkeypatch):
    _installed(monkeypatch, "1.2.3")
    seen = []
    monkeypatch.setattr(doctor, "claude_version_string", lambda env=None: seen.append(env) or "2.1.3 (Claude Code)")
    env = {"PATH": "/only/here"}
    rows = by_check(doctor.check_versions(env, {"tanabesugano": "1.2.3", "claude": "2.1.3"}))
    assert seen == [env]
    assert rows["claude CLI"] == ("OK", "2.1.3 (Claude Code) (expected 2.1.3)")


def test_check_versions_asks_for_the_tanabesugano_distribution(monkeypatch):
    asked = []

    def version(name):
        asked.append(name)
        if name != "tanabesugano":
            raise importlib.metadata.PackageNotFoundError(name)
        return "1.2.3"

    monkeypatch.setattr(doctor.importlib.metadata, "version", version)
    monkeypatch.setattr(doctor, "claude_version_string", lambda env=None: None)
    rows = by_check(doctor.check_versions({}, {"tanabesugano": "1.2.3"}))
    assert asked == ["tanabesugano"]
    assert rows["tanabesugano"] == ("OK", "1.2.3")


# ---------------------------------------------------------------- list_server_tools
def test_list_server_tools_returns_what_the_handshake_returns(monkeypatch):
    async def handshake(command, args, errlog):
        assert (command, args) == ("srv", ["--x"])
        return ["a", "b"]

    monkeypatch.setattr(doctor, "_handshake", handshake)
    assert doctor.list_server_tools("srv", ["--x"], timeout_s=5) == ["a", "b"]


def test_list_server_tools_adds_the_server_stderr_to_the_error(monkeypatch):
    async def handshake(command, args, errlog):
        errlog.write("line one\nbanner: bad config\n")
        raise RuntimeError("handshake broke")

    monkeypatch.setattr(doctor, "_handshake", handshake)
    with pytest.raises(RuntimeError, match="handshake broke") as info:
        doctor.list_server_tools("srv", [], timeout_s=5)
    assert info.value.__notes__ == ["server stderr: line one | banner: bad config"]


def test_list_server_tools_adds_no_note_when_the_server_said_nothing(monkeypatch):
    async def handshake(command, args, errlog):
        raise RuntimeError("silent failure")

    monkeypatch.setattr(doctor, "_handshake", handshake)
    with pytest.raises(RuntimeError, match="silent failure") as info:
        doctor.list_server_tools("srv", [], timeout_s=5)
    assert not getattr(info.value, "__notes__", [])


def test_list_server_tools_times_out(monkeypatch):
    async def handshake(command, args, errlog):
        await asyncio.sleep(30)

    monkeypatch.setattr(doctor, "_handshake", handshake)
    with pytest.raises(TimeoutError):
        doctor.list_server_tools("srv", [], timeout_s=0.05)


def test_list_server_tools_lets_a_keyboard_interrupt_through_without_a_note(monkeypatch):
    async def handshake(command, args, errlog):
        errlog.write("ignored")
        raise KeyboardInterrupt

    monkeypatch.setattr(doctor, "_handshake", handshake)
    with pytest.raises(KeyboardInterrupt) as info:
        doctor.list_server_tools("srv", [], timeout_s=5)
    assert not getattr(info.value, "__notes__", [])


def test_list_server_tools_keeps_the_server_stderr_in_a_utf8_text_file(monkeypatch):
    import tempfile

    real, opened = tempfile.TemporaryFile, []

    def recording(*a, **kw):
        opened.append((a, kw))
        return real(*a, **kw)

    async def handshake(command, args, errlog):
        return ["a"]

    monkeypatch.setattr(tempfile, "TemporaryFile", recording)
    monkeypatch.setattr(doctor, "_handshake", handshake)
    assert doctor.list_server_tools("srv", [], timeout_s=5) == ["a"]
    assert opened == [(("w+",), {"encoding": "utf-8", "errors": "replace"})]


def test_list_server_tools_keeps_only_the_last_300_characters_of_the_server_stderr(monkeypatch):
    async def handshake(command, args, errlog):
        errlog.write("X" + "y" * 300)
        raise RuntimeError("handshake broke")

    monkeypatch.setattr(doctor, "_handshake", handshake)
    with pytest.raises(RuntimeError) as info:
        doctor.list_server_tools("srv", [], timeout_s=5)
    assert info.value.__notes__ == ["server stderr: " + "y" * 300]


# ---------------------------------------------------------------- _handshake
def test_handshake_starts_the_server_with_its_args_and_the_errlog(monkeypatch):
    import contextlib

    import mcp
    import mcp.client.stdio as mcp_stdio

    seen = {}

    class Params:
        def __init__(self, **kw):
            seen["params"] = kw

    @contextlib.asynccontextmanager
    async def client(params, errlog=None):
        seen["errlog"] = errlog
        yield "read", "write"

    class FakeSession:
        def __init__(self, read, write):
            seen["streams"] = (read, write)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def initialize(self):
            seen["initialized"] = True

        async def list_tools(self):
            return SimpleNamespace(tools=[SimpleNamespace(name="ts_b"), SimpleNamespace(name="ts_a")])

    monkeypatch.setattr(mcp_stdio, "StdioServerParameters", Params)
    monkeypatch.setattr(mcp_stdio, "stdio_client", client)
    monkeypatch.setattr(mcp, "ClientSession", FakeSession)
    errlog = object()
    assert asyncio.run(doctor._handshake("srv", ["--stdio"], errlog)) == ["ts_a", "ts_b"]
    assert seen == {"params": {"command": "srv", "args": ["--stdio"]}, "errlog": errlog,
                    "streams": ("read", "write"), "initialized": True}


# ---------------------------------------------------------------- check_mcp
def _server(monkeypatch, cfg=None):
    monkeypatch.setattr(doctor.runner, "find_mcp_command", lambda repo=None: "/bin/tsmcp")
    cfg = cfg or {"command": "/bin/tsmcp", "args": ["--stdio"]}
    monkeypatch.setattr(doctor.runner, "render_ts_json", lambda command: {"mcpServers": {"tanabesugano": cfg}})


def test_check_mcp_fails_when_the_server_binary_is_not_found(monkeypatch):
    monkeypatch.setattr(doctor.runner, "find_mcp_command", lambda repo=None: None)
    assert doctor.check_mcp() == [("FAIL", "MCP server",
                                   "tanabesugano-mcp not found in <repo>/.venv/bin or next to this Python")]


def test_check_mcp_fails_when_ts_json_cannot_be_rendered(monkeypatch):
    monkeypatch.setattr(doctor.runner, "find_mcp_command", lambda repo=None: "/bin/tsmcp")

    def broken(command):
        raise KeyError("tanabesugano")

    monkeypatch.setattr(doctor.runner, "render_ts_json", broken)
    assert doctor.check_mcp() == [("FAIL", "ts.json", "cannot render: KeyError: 'tanabesugano'")]


def test_check_mcp_reports_a_timeout(monkeypatch):
    _server(monkeypatch)

    def slow(command, args, timeout_s):
        raise TimeoutError

    monkeypatch.setattr(doctor, "list_server_tools", slow)
    rows = by_check(doctor.check_mcp(timeout_s=7))
    assert rows["ts.json"] == ("OK", "rendered, command /bin/tsmcp")
    assert rows["MCP handshake"] == ("FAIL", "no answer within 7 s")


def test_check_mcp_reports_a_failed_handshake_with_the_server_notes(monkeypatch):
    _server(monkeypatch)

    def broken(command, args, timeout_s):
        err = OSError("pipe closed")
        err.add_note("server stderr: traceback")
        raise err

    monkeypatch.setattr(doctor, "list_server_tools", broken)
    status, detail = by_check(doctor.check_mcp())["MCP handshake"]
    assert status == "FAIL"
    assert detail == "OSError: pipe closed server stderr: traceback"


def test_check_mcp_lets_a_keyboard_interrupt_through(monkeypatch):
    _server(monkeypatch)

    def interrupted(command, args, timeout_s):
        raise KeyboardInterrupt

    monkeypatch.setattr(doctor, "list_server_tools", interrupted)
    with pytest.raises(KeyboardInterrupt):
        doctor.check_mcp()


def test_check_mcp_names_the_missing_tools(monkeypatch):
    _server(monkeypatch)
    monkeypatch.setattr(doctor, "list_server_tools", lambda command, args, timeout_s: ["ts_fit_spectrum", "other"])
    assert by_check(doctor.check_mcp())["MCP tools"] == (
        "FAIL", "2 tools; missing ts_terms_table_data, ts_supported_configs")


def test_check_mcp_passes_the_args_from_the_rendered_config(monkeypatch):
    _server(monkeypatch, {"command": "/bin/other", "args": ["-m", "srv"]})
    seen = {}

    def lister(command, args, timeout_s):
        seen.update(command=command, args=args, timeout=timeout_s)
        return list(doctor.REQUIRED_TOOLS)

    monkeypatch.setattr(doctor, "list_server_tools", lister)
    rows = by_check(doctor.check_mcp(timeout_s=3))
    assert seen == {"command": "/bin/other", "args": ["-m", "srv"], "timeout": 3}
    assert rows["ts.json"] == ("OK", "rendered, command /bin/other")
    assert rows["MCP tools"] == ("OK", "3 tools; ts_fit_spectrum, ts_terms_table_data, ts_supported_configs present")


def test_check_mcp_passes_no_args_when_the_config_has_none(monkeypatch):
    _server(monkeypatch, {"command": "/bin/other"})
    seen = {}

    def lister(command, args, timeout_s):
        seen.update(command=command, args=args)
        return list(doctor.REQUIRED_TOOLS)

    monkeypatch.setattr(doctor, "list_server_tools", lister)
    assert doctor.check_mcp() == [
        ("OK", "ts.json", "rendered, command /bin/other"),
        ("OK", "MCP tools", "3 tools; ts_fit_spectrum, ts_terms_table_data, ts_supported_configs present")]
    assert seen == {"command": "/bin/other", "args": []}


def test_check_mcp_joins_every_server_note_with_one_space(monkeypatch):
    _server(monkeypatch)

    def broken(command, args, timeout_s):
        err = OSError("pipe closed")
        err.add_note("first")
        err.add_note("second")
        raise err

    monkeypatch.setattr(doctor, "list_server_tools", broken)
    assert by_check(doctor.check_mcp())["MCP handshake"] == ("FAIL", "OSError: pipe closed first second")


def test_check_mcp_cuts_a_long_error_message_at_160_characters(monkeypatch):
    _server(monkeypatch)

    def broken(command, args, timeout_s):
        raise RuntimeError("m" * 200)

    monkeypatch.setattr(doctor, "list_server_tools", broken)
    assert by_check(doctor.check_mcp())["MCP handshake"] == ("FAIL", "RuntimeError: " + "m" * 160)


# ---------------------------------------------------------------- check_sandbox
def _args(tmp_path, *flags):
    return doctor.parse_args([*flags, "--out", str(tmp_path)])


def test_check_sandbox_reports_a_failed_render(monkeypatch, tmp_path):
    def broken(repo, home=None, **kw):
        raise ValueError("template broke")

    monkeypatch.setattr(doctor.sandbox, "render_settings", broken)
    rows = doctor.check_sandbox({}, _args(tmp_path), tmp_path, key_ok=True)
    assert rows == [("FAIL", "sandbox settings", "render_settings failed: ValueError: template broke")]


def test_check_sandbox_lists_every_problem_in_the_settings(monkeypatch, tmp_path):
    monkeypatch.setattr(doctor.sandbox, "render_settings",
                        lambda repo, home=None, **kw: {"sandbox": {"enabled": False,
                                                                   "network": {"allowedDomains": ["x.org"]},
                                                                   "filesystem": {"denyRead": []}}})
    monkeypatch.setattr(doctor, "claude_version_string", lambda env=None: None)
    rows = doctor.check_sandbox({"HOME": str(tmp_path / "home")}, _args(tmp_path), tmp_path, key_ok=True)
    first = rows[0]
    assert first[:2] == ("FAIL", "sandbox settings")
    assert first[2] == ("sandbox.enabled is not true; network.allowedDomains is not empty; "
                        "repo path missing from denyRead; the real home is missing from denyRead; "
                        "the key file folder is missing from denyRead")
    assert by_check(rows)["sandbox probe"][0] == "WARN"


def test_check_sandbox_renders_the_settings_with_the_environment_it_checks(monkeypatch, tmp_path):
    home = tmp_path / "home"
    env = {"HOME": str(home), "TSBENCH_KEY_FILE": "/srv/keys/model.env"}
    seen = []
    real_render = doctor.sandbox.render_settings

    def render(repo, home=None, **kw):
        seen.append((repo, home, kw.get("parent_env")))
        return real_render(repo, home, **kw)

    monkeypatch.setattr(doctor.sandbox, "render_settings", render)
    monkeypatch.setattr(doctor, "claude_version_string", lambda env=None: None)
    rows = doctor.check_sandbox(env, _args(tmp_path), tmp_path, key_ok=True)
    assert seen[0] == (doctor.REPO_ROOT, str(home), env)
    assert by_check(rows)["sandbox settings"][0] == "OK"


def test_check_sandbox_fails_when_the_key_file_folder_is_not_denied(monkeypatch, tmp_path):
    home = tmp_path / "home"
    env = {"HOME": str(home), "TSBENCH_KEY_FILE": "/srv/keys/model.env"}
    settings = {"sandbox": {"enabled": True, "network": {"allowedDomains": []},
                            "filesystem": {"denyRead": [str(doctor.REPO_ROOT), str(home)]}}}
    monkeypatch.setattr(doctor.sandbox, "render_settings", lambda repo, home=None, **kw: settings)
    monkeypatch.setattr(doctor, "claude_version_string", lambda env=None: None)
    rows = doctor.check_sandbox(env, _args(tmp_path), tmp_path, key_ok=True)
    assert by_check(rows)["sandbox settings"] == ("FAIL", "the key file folder is missing from denyRead")


def test_check_sandbox_warns_when_claude_is_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(doctor, "claude_version_string", lambda env=None: None)
    rows = doctor.check_sandbox({}, _args(tmp_path), tmp_path, key_ok=True)
    assert by_check(rows)["sandbox probe"] == ("WARN", "claude not found; a probe cannot be reused or run")


def test_check_sandbox_without_credentials_does_not_run_the_probe(monkeypatch, tmp_path):
    monkeypatch.setattr(doctor, "claude_version_string", lambda env=None: "9.9.9 (Claude Code)")

    def must_not_run(*a, **kw):
        raise AssertionError("the probe must not start without credentials")

    monkeypatch.setattr(doctor.sandbox_probe, "run_probe", must_not_run)
    rows = doctor.check_sandbox({}, _args(tmp_path, "--probe"), tmp_path, key_ok=False)
    assert by_check(rows)["sandbox probe"] == ("FAIL", "needs credentials (see env checks above); not run")


def test_check_sandbox_reports_a_session_that_cannot_be_created(monkeypatch, tmp_path):
    monkeypatch.setattr(doctor, "claude_version_string", lambda env=None: "9.9.9 (Claude Code)")

    def refuse(**kw):
        raise SystemExit(2)

    monkeypatch.setattr(doctor.runner.Session, "create", refuse)
    rows = doctor.check_sandbox({}, _args(tmp_path, "--probe"), tmp_path, key_ok=True)
    assert by_check(rows)["sandbox probe"] == (
        "FAIL", "could not create a session (see the runner message above)")


class _Session:
    closed = False

    def close(self):
        self.closed = True


def _marker_record(passed, reasons=(), markers=None):
    return {"passed": passed, "cost_usd": 0.0123, "reasons": list(reasons), "markers": markers or {}}


def test_check_sandbox_runs_the_probe_and_reports_a_pass(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(doctor, "claude_version_string", lambda env=None: "9.9.9 (Claude Code)")
    session, seen = _Session(), {}

    def create(**kw):
        seen.update(kw)
        return session

    def run_probe(sess, out, **kw):
        seen["probe_args"] = (sess, out)
        seen["probe_kw"] = kw
        return _marker_record(True, markers={"CTRL1": [0]})

    monkeypatch.setattr(doctor.runner.Session, "create", create)
    monkeypatch.setattr(doctor.sandbox_probe, "run_probe", run_probe)
    args = _args(tmp_path, "--probe", "--gateway", "--model", "gw-model", "--b-venv", "/some/venv")
    rows = doctor.check_sandbox({"X": "1"}, args, tmp_path, key_ok=True)
    assert seen["dry_run"] is False and seen["gateway"] is True and seen["b_venv"] == "/some/venv"
    assert seen["create_b"] is False  # the doctor validates the B stack, it never installs it
    assert seen["probe_args"] == (session, tmp_path)
    assert seen["probe_kw"] == {"model": "gw-model"}  # the gateway does not serve the default Haiku id
    assert session.closed
    by = by_check(rows)
    assert by["sandbox probe"] == ("OK", f"PASS; cost USD 0.0123; record {tmp_path / sandbox.PROBE_FILENAME}")
    assert by["  marker CTRL1"] == ("OK", "rc=0 (must be 0)")
    assert by["  marker CTRL2"] == ("FAIL", "missing")
    assert "running the paid sandbox probe" in capsys.readouterr().out


def test_check_sandbox_reports_probe_reasons_and_closes_the_session(monkeypatch, tmp_path):
    monkeypatch.setattr(doctor, "claude_version_string", lambda env=None: "9.9.9 (Claude Code)")
    session = _Session()
    monkeypatch.setattr(doctor.runner.Session, "create", lambda **kw: session)
    monkeypatch.setattr(doctor.sandbox_probe, "run_probe",
                        lambda sess, out, **kw: _marker_record(False, reasons=["NET escaped", "no tool_use"]))
    rows = doctor.check_sandbox({}, _args(tmp_path, "--probe"), tmp_path, key_ok=True)
    assert session.closed
    assert [r for r in rows if r[1] == "sandbox probe reason"] == [
        ("FAIL", "sandbox probe reason", "NET escaped"), ("FAIL", "sandbox probe reason", "no tool_use")]
    assert by_check(rows)["sandbox probe"][0] == "FAIL"


def test_check_sandbox_closes_the_session_when_the_probe_raises(monkeypatch, tmp_path):
    monkeypatch.setattr(doctor, "claude_version_string", lambda env=None: "9.9.9 (Claude Code)")
    session = _Session()
    monkeypatch.setattr(doctor.runner.Session, "create", lambda **kw: session)

    def boom(sess, out, **kw):
        raise RuntimeError("probe crashed")

    monkeypatch.setattr(doctor.sandbox_probe, "run_probe", boom)
    with pytest.raises(RuntimeError, match="probe crashed"):
        doctor.check_sandbox({}, _args(tmp_path, "--probe"), tmp_path, key_ok=True)
    assert session.closed


def test_check_sandbox_without_probe_never_makes_a_session_or_a_call(monkeypatch, tmp_path):
    monkeypatch.setattr(doctor, "claude_version_string", lambda env=None: "9.9.9 (Claude Code)")

    def must_not_run(*a, **kw):
        raise AssertionError("no --probe: no session, no paid call")

    monkeypatch.setattr(doctor.runner.Session, "create", must_not_run)
    monkeypatch.setattr(doctor.sandbox_probe, "run_probe", must_not_run)
    rows = doctor.check_sandbox({}, _args(tmp_path), tmp_path, key_ok=True)
    status, detail = by_check(rows)["sandbox probe"]
    assert status == "WARN" and "tsbench doctor --probe --out" in detail
    assert not list(tmp_path.iterdir())


def test_check_sandbox_reports_a_not_evaluable_probe_as_a_warning_not_a_failure(monkeypatch, tmp_path):
    monkeypatch.setattr(doctor, "claude_version_string", lambda env=None: "9.9.9 (Claude Code)")
    session = _Session()
    monkeypatch.setattr(doctor.runner.Session, "create", lambda **kw: session)
    rec = {**_marker_record(None, reasons=["the probe call ended in an API error, so the sandbox was not tested: x"]),
           "not_evaluable": "api_error"}
    monkeypatch.setattr(doctor.sandbox_probe, "run_probe", lambda sess, out, **kw: rec)
    rows = doctor.check_sandbox({}, _args(tmp_path, "--probe"), tmp_path, key_ok=True)
    status, detail = by_check(rows)["sandbox probe"]
    assert status == "WARN" and detail.startswith("NOT EVALUABLE") and "FAIL" not in detail
    assert [r[0] for r in rows if r[1] == "sandbox probe reason"] == ["WARN"]
    assert not [r for r in rows if r[0] == "FAIL"]  # no marker was measured, so none is reported missing
    assert session.closed


def test_check_sandbox_treats_a_broken_b_venv_path_as_no_digest(monkeypatch, tmp_path):
    def broken(env, override, repo):
        raise doctor.b_stack.BStackError("bad path")

    monkeypatch.setattr(doctor.b_stack, "b_venv_dir", broken)
    monkeypatch.setattr(doctor, "claude_version_string", lambda env=None: None)
    rows = doctor.check_sandbox({}, _args(tmp_path), tmp_path, key_ok=True)
    assert by_check(rows)["sandbox settings"][0] == "OK"


# ---------------------------------------------------------------- _marker_rows
def test_marker_rows_judge_each_marker_against_what_it_must_be():
    rec = {"markers": {"CTRL1": [0, 0], "CTRL2": [1], "NET": [6], "PIP": [0], "DNS": [1, 0]}}
    by = by_check(doctor._marker_rows(rec))
    assert by["  marker CTRL1"] == ("OK", "rc=0,0 (must be 0)")
    assert by["  marker CTRL2"] == ("FAIL", "rc=1 (must be 0)")
    assert by["  marker NET"] == ("OK", "rc=6 (must be non-zero)")
    assert by["  marker PIP"] == ("FAIL", "rc=0 (must be non-zero)")
    assert by["  marker DNS"] == ("FAIL", "rc=1,0 (must be non-zero)")
    assert by["  marker HEREDOC"] == ("FAIL", "missing")
    assert len(by) == len(sandbox.MUST_BE_ZERO) + len(sandbox.MUST_FAIL)


def test_marker_rows_without_markers_report_every_marker_missing():
    rows = doctor._marker_rows({})
    assert {status for status, _, _ in rows} == {"FAIL"}
    assert {detail for _, _, detail in rows} == {"missing"}


# ---------------------------------------------------------------- key file
def test_key_file_row_reports_an_existing_key_file_without_reading_it(tmp_path, monkeypatch):
    key = tmp_path / "home" / ".config" / "tsbench" / "env"
    key.parent.mkdir(parents=True)
    key.write_text("TEST_ONLY_KEY=" + SENTINEL + "\n", encoding="utf-8")
    opened = []
    real_open = open
    monkeypatch.setattr("builtins.open", lambda f, *a, **k: opened.append(str(f)) or real_open(f, *a, **k))
    rows = doctor.check_key_file({"HOME": str(tmp_path / "home")})
    assert rows == [("OK", "key file", "~/.config/tsbench/env exists (named by TSBENCH_KEY_FILE or the default; "
                     "never read)")]
    assert str(key) not in opened and SENTINEL not in repr(rows)


def test_key_file_row_is_info_without_a_key_file(tmp_path):
    rows = doctor.check_key_file({"HOME": str(tmp_path), "TSBENCH_KEY_FILE": str(tmp_path / "keys" / "env")})
    assert rows == [("INFO", "key file", "~/keys/env not found (optional: the keys can also come from the shell; "
                     "TSBENCH_KEY_FILE names another file)")]


# ---------------------------------------------------------------- driver
def test_run_checks_collects_every_check_in_order(monkeypatch, tmp_path):
    calls = []

    def stub(name, rows):
        def check(*a, **kw):
            calls.append((name, a, kw))
            return rows

        return check

    monkeypatch.setattr(doctor, "check_env", stub("env", [("OK", "env", "a")]))
    monkeypatch.setattr(doctor, "check_key_file", stub("key", [("INFO", "key", "k")]))
    monkeypatch.setattr(doctor, "load_expected", lambda: {"claude": "1"})
    monkeypatch.setattr(doctor, "check_versions", stub("versions", [("OK", "versions", "b")]))
    monkeypatch.setattr(doctor, "check_mcp", stub("mcp", [("WARN", "mcp", "c")]))
    monkeypatch.setattr(doctor, "check_b_stack", stub("b", [("OK", "b", "d")]))
    monkeypatch.setattr(doctor, "check_sandbox", stub("sandbox", [("FAIL", "sandbox", "e")]))
    monkeypatch.setattr(doctor.runner, "missing_env", lambda env, gateway: ["KEY"])
    args = argparse.Namespace(gateway=False, b_venv="/v", out=str(tmp_path))
    env = {"HOME": "/h"}
    rows = doctor.run_checks(args, env)
    assert [r[1] for r in rows] == ["env", "key", "versions", "mcp", "b", "sandbox"]
    names = [c[0] for c in calls]
    assert names == ["env", "key", "versions", "mcp", "b", "sandbox"]
    assert calls[0][1] == (env, False)
    assert calls[1][1] == (env,)
    assert calls[2][1] == (env, {"claude": "1"})
    assert calls[4][1] == (env, "/v")
    assert calls[5][1] == (env, args, tmp_path.resolve(), False)  # missing_env was non-empty: key_ok False


def _stub_checks(monkeypatch, calls):
    for name in ("check_env", "check_key_file", "check_versions", "check_mcp", "check_b_stack", "check_sandbox"):
        monkeypatch.setattr(doctor, name, lambda *a, _name=name, **kw: calls.append((_name, a)) or [])
    monkeypatch.setattr(doctor, "load_expected", lambda: {})


def test_run_checks_asks_for_the_keys_of_the_gateway_mode(monkeypatch, tmp_path):
    calls, asked = [], []
    _stub_checks(monkeypatch, calls)
    monkeypatch.setattr(doctor.runner, "missing_env", lambda env, gateway: asked.append(gateway) or [])
    args = argparse.Namespace(gateway=True, b_venv=None, out=str(tmp_path))
    env = {"A": "1"}
    doctor.run_checks(args, env)
    assert asked == [True]
    assert calls[-1] == ("check_sandbox", (env, args, tmp_path.resolve(), True))


def test_run_checks_accepts_a_namespace_without_b_venv(monkeypatch, tmp_path):
    calls = []
    _stub_checks(monkeypatch, calls)
    monkeypatch.setattr(doctor.runner, "missing_env", lambda env, gateway: [])
    args = argparse.Namespace(gateway=False, out=str(tmp_path))
    env = {"A": "1"}
    assert doctor.run_checks(args, env) == []
    assert calls == [("check_env", (env, False)), ("check_key_file", (env,)), ("check_versions", (env, {})),
                     ("check_mcp", ()),
                     ("check_b_stack", (env, None)), ("check_sandbox", (env, args, tmp_path.resolve(), True))]


def test_render_table_pads_the_check_column_to_the_longest_name():
    table = doctor.render_table([("OK", "short", "fine"), ("FAIL", "a much longer check", "bad")])
    lines = table.splitlines()
    assert lines[0] == "STATUS  CHECK" + " " * 16 + "DETAIL"
    assert lines[1] == "------  " + "-" * 19 + "  ------"
    assert lines[2] == "OK      short" + " " * 16 + "fine"
    assert lines[3] == "FAIL    a much longer check  bad"


def test_render_table_keeps_the_check_column_at_least_as_wide_as_its_heading():
    lines = doctor.render_table([("OK", "ab", "fine")]).splitlines()
    assert lines == ["STATUS  CHECK  DETAIL", "------  -----  ------", "OK      ab     fine"]


def test_main_prints_the_summary_and_returns_one_on_a_failure(monkeypatch, capsys):
    monkeypatch.setattr(doctor, "run_checks", lambda args, env=None: [
        ("OK", "a", "x"), ("WARN", "b", "y"), ("FAIL", "c", "z"), ("FAIL", "d", "w")])
    assert doctor.main([]) == 1
    out = capsys.readouterr().out
    assert "summary: 2 FAIL, 1 WARN" in out


def test_main_returns_zero_without_a_failure(monkeypatch, capsys):
    monkeypatch.setattr(doctor, "run_checks", lambda args, env=None: [("WARN", "b", "y")])
    assert doctor.main(["--gateway"]) == 0
    assert "summary: 0 FAIL, 1 WARN" in capsys.readouterr().out


def test_parse_args_defaults_and_flags():
    default = doctor.parse_args([])
    assert (default.gateway, default.probe, default.model, default.b_venv, default.out) == (
        False, False, None, None, "runs")
    given = doctor.parse_args(["--gateway", "--probe", "--model", "m", "--b-venv", "/v", "--out", "o"])
    assert (given.gateway, given.probe, given.model, given.b_venv, given.out) == (True, True, "m", "/v", "o")


def test_parse_args_probe_needs_an_explicit_out(capsys):
    with pytest.raises(SystemExit) as info:
        doctor.parse_args(["--probe"])
    assert info.value.code == 2
    assert "--probe writes sandbox_probe.json into --out" in capsys.readouterr().err


def test_parse_args_gateway_probe_needs_a_model(capsys):
    with pytest.raises(SystemExit) as info:
        doctor.parse_args(["--gateway", "--probe", "--out", "o"])
    assert info.value.code == 2
    assert "--gateway --probe needs --model" in capsys.readouterr().err
    assert doctor.parse_args(["--probe", "--out", "o"]).model is None  # direct mode: the probe default model


def test_the_paid_probe_is_opt_in_and_has_no_opt_out_flag():
    with pytest.raises(SystemExit) as info:
        doctor.parse_args(["--no-model-probe"])
    assert info.value.code == 2


def test_main_prints_the_table_then_the_summary(monkeypatch, capsys):
    rows = [("OK", "a", "x"), ("FAIL", "c", "z")]
    monkeypatch.setattr(doctor, "run_checks", lambda args, env=None: rows)
    assert doctor.main([]) == 1
    assert capsys.readouterr().out == doctor.render_table(rows) + "\n\nsummary: 1 FAIL, 0 WARN\n"


@pytest.mark.parametrize("fragment", [
    "Preflight for the TS-MCP benchmark (never prints secret values).",
    "--gateway check the gateway variables instead of the API key",
    "--probe make the paid sandbox probe call (one small model call) when no passing record can be reused; "
    "needs --out",
    "--model MODEL model id of the probe call (needed with --gateway --probe; default: the Haiku probe model)",
    "--b-venv DIR venv of condition B (default: $TSBENCH_B_VENV or ~/.cache/tsbench/venv-B)",
    "--out OUT runner output dir holding sandbox_probe.json (default: runs, read only; --probe needs it "
    "explicit)",
])
def test_parse_args_help_describes_the_tool_and_every_option(monkeypatch, capsys, fragment):
    monkeypatch.setenv("COLUMNS", "200")  # wide enough that no help line wraps
    monkeypatch.setenv("PYTHON_COLORS", "0")
    monkeypatch.setenv("NO_COLOR", "1")
    with pytest.raises(SystemExit) as info:
        doctor.parse_args(["--help"])
    assert info.value.code == 0
    assert f" {fragment} " in f" {' '.join(capsys.readouterr().out.split())} "  # whole words only


# ---------------------------------------------------------------- doctor: env checks
def test_env_direct_missing_key_fails(clean_env):
    rows = doctor.check_env({}, gateway=False)
    assert statuses(rows)["env API key"] == "FAIL"


@pytest.mark.parametrize("name", ["TSMCP_ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY"])
def test_env_direct_key_set_ok_and_value_not_printed(name, capsys):
    env = {name: SENTINEL}
    rows = doctor.check_env(env, gateway=False)
    assert statuses(rows)["env API key"] == "OK"
    table = doctor.render_table(rows)
    print(table)
    assert SENTINEL not in table and SENTINEL not in capsys.readouterr().out


def test_env_direct_base_url_warns_without_value():
    env = {"ANTHROPIC_API_KEY": SENTINEL, "ANTHROPIC_BASE_URL": SENTINEL + "-url"}
    rows = doctor.check_env(env, gateway=False)
    assert statuses(rows)["env ANTHROPIC_BASE_URL"] == "WARN"
    assert SENTINEL not in doctor.render_table(rows)


def test_env_gateway_requires_base_url_and_token():
    rows = statuses(doctor.check_env({}, gateway=True))
    assert rows["env ANTHROPIC_BASE_URL"] == "FAIL" and rows["env ANTHROPIC_AUTH_TOKEN"] == "FAIL"
    ok = {"ANTHROPIC_BASE_URL": SENTINEL, "ANTHROPIC_AUTH_TOKEN": SENTINEL}
    rows_ok = doctor.check_env(ok, gateway=True)
    assert statuses(rows_ok)["env ANTHROPIC_BASE_URL"] == "OK"
    assert statuses(rows_ok)["env ANTHROPIC_AUTH_TOKEN"] == "OK"
    assert SENTINEL not in doctor.render_table(rows_ok)


def test_env_gateway_warns_when_anthropic_api_key_is_set():
    env = {"ANTHROPIC_BASE_URL": "x", "ANTHROPIC_AUTH_TOKEN": "y", "ANTHROPIC_API_KEY": SENTINEL}
    rows = doctor.check_env(env, gateway=True)
    assert statuses(rows)["env ANTHROPIC_API_KEY"] == "WARN"
    detail = [d for s, c, d in rows if c == "env ANTHROPIC_API_KEY"][0]
    assert "unset it" in detail
    assert SENTINEL not in doctor.render_table(rows)


@pytest.mark.parametrize("name", ["GWDG_API_KEY", "GWDG_AI_API_KEY"])
def test_env_gwdg_is_info_only(name):
    rows = doctor.check_env({"TSMCP_ANTHROPIC_API_KEY": "k", name: SENTINEL}, gateway=False)
    st = statuses(rows)["env GWDG key (optional)"]
    assert st == "INFO"
    assert SENTINEL not in doctor.render_table(rows)
    assert statuses(doctor.check_env({"TSMCP_ANTHROPIC_API_KEY": "k"}, gateway=False))[
        "env GWDG key (optional)"] == "INFO"


# ---------------------------------------------------------------- doctor: MCP handshake (local stdio)
@pytest.mark.skipif(runner.find_mcp_command(REPO_ROOT) is None, reason="tanabesugano-mcp binary not installed")
def test_mcp_handshake_lists_required_tools():
    command = runner.find_mcp_command(REPO_ROOT)
    assert command is not None
    names = doctor.list_server_tools(command, [], timeout_s=60)
    for tool in doctor.REQUIRED_TOOLS:
        assert tool in names
    rows = doctor.check_mcp()
    assert statuses(rows)["MCP tools"] == "OK"
    assert statuses(rows)["ts.json"] == "OK"


def test_mcp_check_reports_failure_for_broken_server(monkeypatch, tmp_path):
    bad = tmp_path / "not-a-server"
    bad.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    bad.chmod(0o755)
    monkeypatch.setattr(doctor.runner, "find_mcp_command", lambda repo=None: str(bad))
    rows = doctor.check_mcp(timeout_s=20)
    assert statuses(rows)["MCP handshake"] == "FAIL"


# ---------------------------------------------------------------- doctor: whole run, no model call
def test_sandbox_without_probe_record_warns(clean_env, tmp_path, monkeypatch):
    monkeypatch.setattr(doctor, "claude_version_string", lambda env=None: "9.9.9 (Claude Code)")
    args = doctor.parse_args(["--out", str(tmp_path)])
    rows = doctor.check_sandbox({}, args, tmp_path, key_ok=True)
    st = statuses(rows)
    assert st["sandbox settings"] == "OK"
    assert st["sandbox probe"] == "WARN"  # absent record: reported, never an automatic paid call


def test_sandbox_reuses_matching_passing_record(clean_env, tmp_path, monkeypatch):
    import json

    monkeypatch.setattr(doctor, "claude_version_string", lambda env=None: "9.9.9 (Claude Code)")
    monkeypatch.setattr(doctor.b_stack, "digest_if_present", lambda venv, *a, **k: "ab" * 32)
    rec = {"passed": True, "fake": False, "claude_version": "9.9.9 (Claude Code)",
           "settings_sha256": sandbox.settings_sha256(REPO_ROOT), "b_stack_sha256": "ab" * 32,
           "probe_script_sha256": sandbox.probe_script_sha256(), "auth_mode": "direct",
           "markers": {"CTRL1": [0], "CTRL2": [0], "IMPORT": [1], "PIP": [1], "NET": [6], "VENV": [126], "READ": [1],
                       "NUMPY": [0], "HEREDOC": [0], "KEYENV": [0], "PATHS": [0], "TSBIN": [1, 1],
                       "HOMECACHE": [1], "HOMESECRETS": [1, 1], "LOCALHOST": [7], "APIHOST": [56, 56], "DNS": [1]}}
    (tmp_path / sandbox.PROBE_FILENAME).write_text(json.dumps(rec), encoding="utf-8")
    args = doctor.parse_args(["--out", str(tmp_path)])
    rows = doctor.check_sandbox({}, args, tmp_path, key_ok=False)
    assert statuses(rows)["sandbox probe"] == "OK"
    assert statuses(rows)["  marker PIP"] == "OK" and statuses(rows)["  marker CTRL1"] == "OK"
    assert statuses(rows)["  marker NUMPY"] == "OK" and statuses(rows)["  marker KEYENV"] == "OK"
    assert statuses(rows)["  marker TSBIN"] == "OK" and statuses(rows)["sandbox settings"] == "OK"
    # a record made with another probe script is not reused
    (tmp_path / sandbox.PROBE_FILENAME).write_text(json.dumps({**rec, "probe_script_sha256": "00" * 32}),
                                                   encoding="utf-8")
    assert statuses(doctor.check_sandbox({}, args, tmp_path, key_ok=False))["sandbox probe"] == "WARN"
    (tmp_path / sandbox.PROBE_FILENAME).write_text(json.dumps(rec), encoding="utf-8")
    # a record made for another B stack digest is not reused
    monkeypatch.setattr(doctor.b_stack, "digest_if_present", lambda venv, *a, **k: "cd" * 32)
    assert statuses(doctor.check_sandbox({}, args, tmp_path, key_ok=False))["sandbox probe"] == "WARN"


def test_check_b_stack_reports_a_missing_and_a_valid_stack(clean_env, tmp_path, monkeypatch):
    rows = doctor.check_b_stack({"TSBENCH_B_VENV": str(tmp_path / "nope")})
    assert statuses(rows)["B stack"] == "FAIL" and "tsbench env b-stack" in rows[0][2]
    info = {"path": "/v", "bin": "/v/bin", "python": "3.14.7", "digest": "ab" * 32,
            "packages": {"numpy": "1", "scipy": "2", "sympy": "3", "matplotlib": "4"}}
    seen = {}
    monkeypatch.setattr(doctor.b_stack, "ensure_b_stack", lambda venv, **kw: seen.update(kw) or info)
    rows = doctor.check_b_stack({"TSBENCH_B_VENV": str(tmp_path / "v")})
    assert statuses(rows)["B stack"] == "OK" and seen == {"create": False}  # the doctor never installs


@pytest.mark.skipif(runner.find_mcp_command(REPO_ROOT) is None, reason="tanabesugano-mcp binary not installed")
def test_doctor_without_probe_exits_zero_and_hides_values(clean_env, tmp_path, capsys):
    clean_env.setenv("TSMCP_ANTHROPIC_API_KEY", SENTINEL)
    clean_env.setenv("GWDG_AI_API_KEY", SENTINEL + "-gwdg")
    # the B stack check has its own tests; here it stands in for a host with a valid venv-B (a CI runner has none)
    clean_env.setattr(doctor, "check_b_stack", lambda env, override=None: [("OK", "B stack", "stand-in")])
    rc = doctor.main(["--out", str(tmp_path)])
    out = capsys.readouterr()
    assert rc == 0, out.out
    assert "summary: 0 FAIL" in out.out
    assert SENTINEL not in out.out and SENTINEL not in out.err
    assert not list(tmp_path.iterdir())  # no probe record was written: no model call happened


def test_doctor_exit_one_when_key_missing(clean_env, tmp_path, capsys):
    rc = doctor.main(["--out", str(tmp_path)])
    assert rc == 1
    assert "FAIL" in capsys.readouterr().out


def test_module_runs_as_a_script_and_exits_with_the_code_of_main(monkeypatch, capsys):
    import runpy
    import sys

    monkeypatch.setattr(sys, "argv", ["doctor", "--help"])
    with pytest.warns(RuntimeWarning):
        with pytest.raises(SystemExit) as e:
            runpy.run_module("tsbench.run.doctor", run_name="__main__")
    assert e.value.code == 0 and "usage:" in capsys.readouterr().out
