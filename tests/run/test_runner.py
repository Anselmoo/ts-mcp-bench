"""Tests for the runner, conditions, sandbox probe and the fake claude.

No network, no key, no real `claude`: every model call is the fake (src/tsbench/run/fake_cli.py).
Run: python -m pytest tests -q
"""
from __future__ import annotations

import copy
import json
import os
import pathlib
import re
import signal
import subprocess
import sys
from types import SimpleNamespace
from typing import Any

import pytest

from tsbench import conditions
from tsbench.conditions import b_stack, sandbox
from tsbench.run import fake_cli, runner, sandbox_probe
from tsbench.score import batch_score, diagram_score, pairing_score
from tsbench.tasks import load

FIX = runner.REPO_ROOT / "src" / "tsbench" / "run" / "fake_cli_fixtures"
REPO_ROOT = runner.REPO_ROOT
HAIKU, SONNET, OPUS = "claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5"



def drop_pre_init(events):
    """Real claude (and the fake) may emit system/<other> events before init; tests look past them."""
    return [e for e in events if not (e.get("type") == "system" and e.get("subtype") != "init")]

def fixture(name: str, structured: bool = True) -> dict:
    """A real init sample (captured without the flag). By default `StructuredOutput` is appended, as claude adds it
    when `--json-schema` is passed; `structured=False` gives the raw sample."""
    ev = json.loads((FIX / name).read_text(encoding="utf-8"))
    if structured and name.startswith("init_"):
        ev["tools"] = list(ev["tools"]) + [conditions.STRUCTURED_TOOL]
    return ev


def fake_b_venv(base: pathlib.Path) -> pathlib.Path:
    """A directory that is not a valid B stack: dry runs and tests must not need the real venv."""
    d = base / "fake-venv-B"
    (d / "bin").mkdir(parents=True, exist_ok=True)
    return d


@pytest.fixture(autouse=True)
def clean_fake_env(monkeypatch, tmp_path_factory):
    monkeypatch.setenv("TSBENCH_B_VENV", str(fake_b_venv(tmp_path_factory.getbasetemp())))  # never the real venv-B


def run_dry(tmp_path, *, models=(HAIKU,), conds="A,B,C", k=1, limit=2, budget=10.0, extra=(), out=None):
    out = out or tmp_path / "runs"
    argv = ["--split", "pilot", "--models", ",".join(models), "--conditions", conds, "--effort", "medium",
            "--k", str(k), "--budget-usd", str(budget), "--out", str(out), "--dry-run", "--limit", str(limit), *extra]
    rc = runner.main(argv)
    return rc, pathlib.Path(out)


def manifest(out: pathlib.Path) -> dict:
    return json.loads((out / "MANIFEST.json").read_text(encoding="utf-8"))


# ------------------------------------------------------------------ argv per condition
def argv_for(key, **kw):
    cond = conditions.get(key)
    return runner.build_argv(["claude"], cond, HAIKU, "medium", 1.5, settings_path="/cfg/settings.json",
                             mcp_config_path="/cfg/ts.json", **kw)


def base_tail(turns):
    return ["-p", "--bare", "--strict-mcp-config", "--no-session-persistence", "--output-format", "stream-json",
            "--verbose", "--system-prompt-file", runner.NEUTRAL_PROMPT, "--max-turns", str(turns),
            "--max-budget-usd", "1.5000", "--effort", "medium", "--model", HAIKU]


BASE_TAIL = base_tail(15)
SCHEMA_TAIL = ["--json-schema", conditions.ANSWER_SCHEMAS["fit"].compact]


def test_argv_condition_a():
    assert argv_for("A") == ["claude"] + BASE_TAIL + ["--tools", ""] + SCHEMA_TAIL


def test_argv_condition_b_has_settings():
    a = argv_for("B")
    assert a == ["claude"] + base_tail(40) + ["--tools", "Bash", "--settings", "/cfg/settings.json",
                                          "--allowedTools", "Bash"] + SCHEMA_TAIL
    assert "--mcp-config" not in a


def test_argv_condition_c_has_mcp_and_allowed_tools():
    a = argv_for("C")
    assert a == ["claude"] + base_tail(25) + ["--tools", "", "--mcp-config", "/cfg/ts.json",
                                          "--allowedTools", "mcp__tanabesugano__*"] + SCHEMA_TAIL
    assert "--settings" not in a


def test_argv_has_no_prompt_and_neutral_prompt_exists():
    assert pathlib.Path(runner.NEUTRAL_PROMPT).is_absolute() and pathlib.Path(runner.NEUTRAL_PROMPT).exists()
    for k in "ABC":
        assert not any(t["prompt"] in " ".join(argv_for(k)) for t in load("pilot"))


def test_condition_flags_need_their_files():
    with pytest.raises(ValueError):
        conditions.get("B").flags()
    with pytest.raises(ValueError):
        conditions.get("C").flags()


def test_rendered_ts_json_and_settings(monkeypatch):
    monkeypatch.delenv("TSBENCH_KEY_FILE", raising=False)
    cfg = runner.render_ts_json("/abs/tanabesugano-mcp")
    assert cfg["mcpServers"]["tanabesugano"]["command"] == "/abs/tanabesugano-mcp"
    assert "${" not in json.dumps(cfg)
    s = sandbox.render_settings("/some/repo", home="/real/home", b_venv="/state/venv-B", mpl_dir="/state/mpl",
                                harness=["/h/prefix", "/h/prefix/lib/site-packages"])["sandbox"]
    assert s["enabled"] and s["failIfUnavailable"] and s["autoAllowBashIfSandboxed"]
    assert s["allowUnsandboxedCommands"] is False and s["network"] == {"allowedDomains": []}
    # the whole real home is denied; the "~" entries stay, and are also spelled out in the real home (the child runs
    # with another HOME); the harness install is denied wherever it lives
    assert s["filesystem"]["denyRead"] == ["/some/repo", "/real/home", "~/.config/tsbench",
                                           "/real/home/.config/tsbench", "~/.cache/pip", "/real/home/.cache/pip",
                                           "/h/prefix", "/h/prefix/lib/site-packages"]
    # the narrower allowRead re-opens only venv-B (no pyvenv.cfg here, so no base interpreter) and the MPL cache
    assert s["filesystem"]["allowRead"] == ["/state/venv-B", "/state/mpl"]
    real_home = str(pathlib.Path("~").expanduser())
    default = sandbox.render_settings()["sandbox"]["filesystem"]
    assert real_home in default["denyRead"] and f"{real_home}/.config/tsbench" in default["denyRead"]
    assert sys.prefix in default["denyRead"]
    assert sandbox.SETTINGS_TEMPLATE["sandbox"]["filesystem"]["denyRead"][2:] == ["<KEY_DIR>", "~/.cache/pip"]
    assert sandbox.SETTINGS_TEMPLATE["sandbox"]["filesystem"]["denyRead"][:2] == ["<REPO>", "<REAL_HOME>"]


def test_settings_allow_venv_b_base_interpreter_and_deny_its_site_packages(tmp_path):
    """B's python3 links to a base interpreter in the denied home: allowRead re-opens it (as written and resolved), and
    its own site-packages stay denied (narrower)."""
    base_real = tmp_path / "home" / ".local" / "uv" / "cpython-3.14.7"
    (base_real / "bin").mkdir(parents=True)
    (base_real / "lib" / "python3.14" / "site-packages").mkdir(parents=True)
    link = tmp_path / "home" / ".local" / "uv" / "cpython-3.14"
    link.symlink_to(base_real)
    venv = tmp_path / "home" / ".cache" / "tsbench" / "venv-B"
    venv.mkdir(parents=True)
    (venv / "pyvenv.cfg").write_text(f"home = {link}/bin\ninclude-system-site-packages = false\n", encoding="utf-8")
    fs = sandbox.render_settings("/some/repo", home=tmp_path / "home", b_venv=venv, mpl_dir=tmp_path / "home" / "mpl",
                                 harness=["/h/prefix"])["sandbox"]["filesystem"]
    assert fs["allowRead"] == [str(venv), str(link), str(base_real.resolve()), str(tmp_path / "home" / "mpl")]
    assert str(tmp_path / "home") in fs["denyRead"]
    assert str(link / "lib" / "python3.14" / "site-packages") in fs["denyRead"]
    assert str(base_real.resolve() / "lib" / "python3.14" / "site-packages") in fs["denyRead"]


def test_settings_refuse_an_allow_entry_inside_the_repo_or_harness():
    with pytest.raises(ValueError):
        sandbox.render_settings("/some/repo", home="/real/home", b_venv="/some/repo/venv-B", mpl_dir="/m", harness=[])
    with pytest.raises(ValueError):
        sandbox.render_settings("/some/repo", home="/real/home", b_venv="/v", mpl_dir="/h/sp/mpl",
                                harness=["/h", "/h/sp"])


def test_settings_harness_in_the_base_interpreter_denies_only_its_site_packages():
    fs = sandbox.render_settings("/some/repo", home="/real/home", b_venv="/v", mpl_dir="/h/mpl",
                                 harness=["/h", "/h/lib/site-packages"])["sandbox"]["filesystem"]
    assert "/h" not in fs["denyRead"] and "/h/lib/site-packages" in fs["denyRead"]


# ------------------------------------------------------------------ child environment
def make_env(parent, *, dry_run=False, gateway=False, repo=None, runtime=()):
    return runner.build_child_env(parent, home="/iso/home", config_dir="/iso/home/.claude", tmpdir="/iso/tmp",
                                  repo=pathlib.Path(repo or REPO_ROOT), dry_run=dry_run, gateway=gateway,
                                  runtime_dirs=list(runtime))


def test_env_direct_mode_drops_base_url_and_maps_key():
    parent = {"PATH": "/usr/bin", "ANTHROPIC_BASE_URL": "http://stray", "ANTHROPIC_AUTH_TOKEN": "tok-secret",
              "TSMCP_ANTHROPIC_API_KEY": "sk-tsmcp", "ANTHROPIC_API_KEY": "sk-other", "GWDG_API_KEY": "g",
              "LANG": "en_US.UTF-8", "HOME": "/real/home", "AWS_SECRET_ACCESS_KEY": "x", "USER": "operator",
              "LOGNAME": "operator"}
    env = make_env(parent)
    assert env["ANTHROPIC_API_KEY"] == "sk-tsmcp"
    assert "ANTHROPIC_BASE_URL" not in env and "ANTHROPIC_AUTH_TOKEN" not in env
    assert env["HOME"] == "/iso/home" and env["CLAUDE_CONFIG_DIR"] == "/iso/home/.claude"
    assert env["TMPDIR"] == "/iso/tmp" and env["LANG"] == "en_US.UTF-8" and "LC_ALL" not in env
    assert env["DISABLE_AUTOUPDATER"] == "1" and env["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"] == "1"
    assert env["USER"] == env["LOGNAME"] == runner.RUN_USER == "tsbench"  # never the operator's login
    assert set(env) == {"PATH", "HOME", "CLAUDE_CONFIG_DIR", "TMPDIR", "LANG", "DISABLE_AUTOUPDATER", "USER", "LOGNAME",
                        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC", "ANTHROPIC_API_KEY",
                        "MCP_CONNECTION_NONBLOCKING", "MCP_CONNECT_TIMEOUT_MS"}


def test_env_key_falls_back_to_anthropic_api_key():
    assert make_env({"PATH": "", "ANTHROPIC_API_KEY": "sk-plain"})["ANTHROPIC_API_KEY"] == "sk-plain"
    assert "ANTHROPIC_API_KEY" not in make_env({"PATH": ""})


def test_env_gateway_mode():
    parent = {"PATH": "/usr/bin", "ANTHROPIC_BASE_URL": "http://localhost:4000", "ANTHROPIC_AUTH_TOKEN": "tok",
              "ANTHROPIC_API_KEY": "sk-should-not-pass", "TSMCP_ANTHROPIC_API_KEY": "sk-nor-this"}
    env = make_env(parent, gateway=True)
    assert env["ANTHROPIC_BASE_URL"] == "http://localhost:4000" and env["ANTHROPIC_AUTH_TOKEN"] == "tok"
    assert "ANTHROPIC_API_KEY" not in env


def test_missing_env_names_the_variable():
    assert "TSMCP_ANTHROPIC_API_KEY" in runner.missing_env({}, gateway=False)[0]
    assert runner.missing_env({"ANTHROPIC_API_KEY": "k"}, gateway=False) == []
    assert runner.missing_env({"ANTHROPIC_API_KEY": "k"}, gateway=True) == ["ANTHROPIC_BASE_URL",
                                                                              "ANTHROPIC_AUTH_TOKEN"]
    assert runner.missing_env({"ANTHROPIC_BASE_URL": "u", "ANTHROPIC_AUTH_TOKEN": "t"}, gateway=True) == []


def test_child_path_is_built_from_scratch_per_condition(tmp_path):
    """The parent's PATH is never inherited. A and C: /usr/bin:/bin plus claude's runtime dirs; B: venv-B/bin
    first, then the same."""
    parent = {"PATH": os.pathsep.join(["/home/op/.local/bin", "/usr/local/bin", str(REPO_ROOT / ".venv" / "bin"),
                                       "/usr/bin"])}
    env = make_env(parent, runtime=["/opt/claude/2.1.308"])
    assert env["PATH"] == "/usr/bin:/bin:/opt/claude/2.1.308"
    assert make_env(parent)["PATH"] == "/usr/bin:/bin"
    path = runner.child_path(["/opt/claude/2.1.308"], "/state/venv-B/bin")
    assert path == "/state/venv-B/bin:/usr/bin:/bin:/opt/claude/2.1.308"
    assert runner.child_path(["/usr/bin"]) == "/usr/bin:/bin"  # no duplicates


def test_claude_runtime_dirs_resolve_the_binary_and_a_script_interpreter(tmp_path):
    native_dir = tmp_path / "Caskroom" / "claude-code" / "9.9"
    native_dir.mkdir(parents=True)
    native = native_dir / "claude"
    native.write_bytes(b"\xcf\xfa\xed\xfe binary")
    shim_dir = tmp_path / "brew" / "bin"
    shim_dir.mkdir(parents=True)
    (shim_dir / "claude").symlink_to(native)
    # the symlink's dir is full of other tools: never on the child PATH
    (shim_dir / "python3").write_text("x", encoding="utf-8")
    assert runner.claude_runtime_dirs(str(shim_dir / "claude")) == [str(native_dir.resolve())]
    # an npm install: `#!/usr/bin/env node`; node's resolved dir is added
    node_dir = tmp_path / "node" / "bin"
    node_dir.mkdir(parents=True)
    (node_dir / "node").write_text("#!/bin/sh\n", encoding="utf-8")
    (node_dir / "node").chmod(0o755)
    cli = tmp_path / "npm" / "cli.js"
    cli.parent.mkdir()
    cli.write_text("#!/usr/bin/env node\nconsole.log(1)\n", encoding="utf-8")
    which = lambda name, path: str(pathlib.Path(path) / name) if (pathlib.Path(path) / name).exists() else None  # noqa: E731
    assert runner.claude_runtime_dirs(str(cli), str(node_dir), which=which) == [str(cli.parent.resolve()),
                                                                                 str(node_dir.resolve())]
    assert runner.claude_runtime_dirs(None) == []


def test_path_offenders_find_tanabesugano_on_the_child_path(tmp_path):
    d = tmp_path / "bin"
    d.mkdir()
    (d / "tanabesugano-mcp").write_text("x", encoding="utf-8")
    assert runner.path_offenders(f"/usr/bin:{d}") == [str(d / "tanabesugano-mcp")]
    assert runner.path_offenders(f"/usr/bin:{d}", skip=(str(d),)) == []


def test_session_records_the_child_path_with_placeholders(tmp_path):
    venv = fake_b_venv(tmp_path)
    s = runner.Session.create(dry_run=True, gateway=False, b_venv=venv)
    try:
        b = s.recorded_child_path("B").split(os.pathsep)
        assert b[0] == "<B_VENV>/bin" and b[1:3] == ["/usr/bin", "/bin"]
        assert s.recorded_child_path("A").split(os.pathsep)[:2] == ["/usr/bin", "/bin"]
        assert "<B_VENV>" not in s.recorded_child_path("A")
        assert s.env["USER"] == "tsbench" and s.env["LOGNAME"] == "tsbench"
    finally:
        s.close()


def test_dry_run_env_passes_only_fake_hooks():
    env = make_env({"PATH": "/usr/bin", "FAKE_COST_USD": "0.2", "FAKE_SEED": "x", "OTHER": "1"}, dry_run=True)
    assert env["FAKE_COST_USD"] == "0.2" and "FAKE_SEED" not in env and "OTHER" not in env
    assert "FAKE_COST_USD" not in make_env({"PATH": "", "FAKE_COST_USD": "1"}, dry_run=False)
    assert make_env({"PATH": "/usr/bin", "FAKE_429_TEXT": "t"}, dry_run=True)["FAKE_429_TEXT"] == "t"


def test_execute_isolation_cwd_env_and_cleanup(tmp_path):
    """The child sees an empty temp cwd outside the repo and exactly the allow-listed env."""
    spy = ("import os, json; print(json.dumps({'type':'system','subtype':'init','tools':['StructuredOutput'],"
           "'mcp_servers':[],'model':'m','cwd':os.getcwd(),'listing':os.listdir('.'),'env':sorted(os.environ)}))")
    env = make_env({"PATH": "/usr/bin", "ANTHROPIC_API_KEY": "sk-abcdefgh", "SECRET": "x"})
    out = runner.execute([sys.executable, "-c", spy], "prompt", env, tmp_path / "t.jsonl",
                         conditions.get("A"), "m", timeout_s=30)
    assert out.mismatches == [] and out.exit_code == 0
    cwd = pathlib.Path(out.init["cwd"]).resolve()
    assert not cwd.is_relative_to(REPO_ROOT) and not cwd.exists()  # outside the repo, removed afterwards
    assert out.init["listing"] == []
    assert "SECRET" not in out.init["env"] and "ANTHROPIC_API_KEY" in out.init["env"]
    assert (tmp_path / "t.jsonl").read_bytes().count(b"\n") == 1  # raw stdout, unmodified


def test_execute_timeout_kills_the_group(tmp_path):
    import time

    t0 = time.monotonic()
    out = runner.execute([sys.executable, "-c", "import time; time.sleep(60)"], "", {"PATH": "/usr/bin"},
                         tmp_path / "t.jsonl", conditions.get("A"), "m", timeout_s=0.5)
    assert out.timed_out and out.result is None and time.monotonic() - t0 < 20


def test_stderr_tail_is_limited_and_redacted(tmp_path):
    # stderr first: the init event aborts the run and kills the child; the stderr text must still be complete
    code = ("import sys,json; sys.stderr.write('x'*5000 + 'sk-abcdefgh'); sys.stderr.flush(); "
            "print(json.dumps({'type':'system','subtype':'init','tools':[],'mcp_servers':[],'model':'m'}))")
    env = make_env({"PATH": "/usr/bin", "ANTHROPIC_API_KEY": "sk-abcdefgh"})
    out = runner.execute([sys.executable, "-c", code], "", env, tmp_path / "t.jsonl", conditions.get("A"), "m",
                         timeout_s=30)
    assert len(out.stderr_tail) <= runner.STDERR_TAIL_CHARS and "sk-abcdefgh" not in out.stderr_tail
    assert "[REDACTED]" in out.stderr_tail


# ------------------------------------------------------------------ check_init
@pytest.mark.parametrize("key", "ABC")
def test_check_init_accepts_real_fixtures(key):
    assert conditions.check_init(conditions.get(key), fixture(f"init_{key}.json"), HAIKU) == []


def test_check_init_rejects_wrong_condition_fixture():
    for key, other in [("A", "B"), ("A", "C"), ("B", "A"), ("B", "C"), ("C", "A"), ("C", "B")]:
        assert conditions.check_init(conditions.get(key), fixture(f"init_{other}.json"), HAIKU), (key, other)


def test_check_init_model_mismatch_everywhere():
    for key in "ABC":
        probs = conditions.check_init(conditions.get(key), fixture(f"init_{key}.json"), SONNET)
        assert len(probs) == 1 and "model" in probs[0]


def test_check_init_mutations():
    c = conditions.get("C")
    ok = fixture("init_C.json")

    def mutate(fn):
        ev = copy.deepcopy(ok)
        fn(ev)
        return conditions.check_init(c, ev, HAIKU)

    assert mutate(lambda e: e["tools"].append("Bash"))
    assert mutate(lambda e: e.update(tools=[]))
    assert mutate(lambda e: e["mcp_servers"][0].update(status="failed"))
    assert mutate(lambda e: e["mcp_servers"][0].update(name="other"))
    assert mutate(lambda e: e["mcp_servers"].append({"name": "x", "status": "connected"}))
    assert mutate(lambda e: e.update(mcp_servers=[]))
    assert mutate(lambda e: e.update(type="result"))
    b = copy.deepcopy(fixture("init_B.json"))
    b["tools"] = ["Bash", "Read"]
    assert conditions.check_init(conditions.get("B"), b, HAIKU)
    a = copy.deepcopy(fixture("init_A.json"))
    a["mcp_servers"] = [{"name": "tanabesugano", "status": "connected"}]
    assert conditions.check_init(conditions.get("A"), a, HAIKU)


# ------------------------------------------------------------------ plan, flags, validation
@pytest.mark.parametrize("model,ok", [(HAIKU, True), (SONNET, True), ("claude-haiku-4-5-20251001", True),
                                      ("claude-haiku", False), ("claude-haiku-5", False), ("haiku", False),
                                      ("opus", False), ("gpt-5", False), ("claude-haiku-5-5 ", False)])
def test_model_id_validation(model, ok):
    assert (runner.validate_model_id(model) is None) is ok


def test_gateway_model_names_are_accepted_but_aliases_are_not():
    assert runner.validate_model_id("gwdg-qwen3.5-397b", gateway=True) is None
    assert runner.validate_model_id("sonnet", gateway=True)


def tool_use(name, **inp):
    return {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "t", "name": name, "input": inp}]}}


def result(denials=()):
    return {"type": "result", "is_error": False, "total_cost_usd": 0, "permission_denials": list(denials)}


def test_flags_b():
    assert runner.compute_flags("B", [tool_use("Bash", command="ls")], result())[0] == []
    assert runner.compute_flags("B", [], result())[0] == ["b_no_tool_use"]
    assert runner.compute_flags("B", [tool_use("Bash", command="ls")], result([{"tool_name": "Bash"}]))[0] == [
        "permission_denials", "b_no_tool_use"]
    assert "sandbox_escape_requested" in runner.compute_flags(
        "B", [tool_use("Bash", command="ls", dangerouslyDisableSandbox=True)], result())[0]
    assert runner.compute_flags(
        "B", [tool_use("Bash", command="ls", dangerouslyDisableSandbox=False)], result())[0] == []


def test_flags_c_and_a():
    assert runner.compute_flags("C", [], result())[0] == ["c_no_mcp_call"]
    assert runner.compute_flags("C", [tool_use("mcp__tanabesugano__ts_fit_spectrum")], result())[0] == []
    assert runner.compute_flags("C", [tool_use("mcp__other__x")], result())[0] == ["c_no_mcp_call"]
    assert runner.compute_flags("A", [], result())[0] == []


# ------------------------------------------------------------------ dry runs
def test_dry_run_matrix_writes_transcripts_and_manifest(tmp_path):
    rc, out = run_dry(tmp_path, models=(HAIKU, SONNET, OPUS), conds="A,B,C", k=2, limit=2)
    assert rc == 0
    tasks = [t["id"] for t in load("pilot")[:2]]
    expected = {out / m / c / "medium" / f"{t}-k{i}.jsonl"
                for m in (HAIKU, SONNET, OPUS) for c in "ABC" for t in tasks for i in (1, 2)}
    assert len(expected) == 36
    assert set(out.glob("*/*/*/*.jsonl")) == expected
    assert len(list(out.glob("*/*/*/*.meta.json"))) == 36
    m = manifest(out)
    assert m["counts"] == {"planned": 36, "done": 36, "rate_limited": 0, "skipped": 0, "aborted": 0,
                           "not_run_sandbox": 0, "not_run_probe_not_evaluable": 0, "not_run_budget": 0,
                           "not_run_quota": 0} and m["stop"] is None
    assert m["finished"] is True and m["stopped_by_budget"] is False and m["total_cost_usd"] == 0
    assert m["sandbox"]["method"] == "dry-run (not probed)"
    assert m["tanabesugano_version"] == "2.0.0" and m["git_commit"] and m["git_dirty"] in ("yes", "no")
    assert m["claude_version"]["fake"] == "fake-0" and m["python_version"] and m["host"] and m["platform"]
    assert m["start_time_utc"] and m["end_time_utc"] and m["models_requested"] == [HAIKU, SONNET, OPUS]
    assert m["reported_models"][SONNET]["C"] == [SONNET]
    assert all("=" not in n for n in m["env_var_names"])  # names only, never values
    assert "FAKE_SEED" in m["env_var_names"] and "ANTHROPIC_BASE_URL" not in m["env_var_names"]


def test_dry_run_sidecar_and_transcript_shape(tmp_path):
    _, out = run_dry(tmp_path, models=(HAIKU,), conds="B,C", k=1, limit=1)
    tid = load("pilot")[0]["id"]
    meta = json.loads((out / HAIKU / "B" / "medium" / f"{tid}-k1.meta.json").read_text(encoding="utf-8"))
    assert meta["exit_code"] == 0 and meta["wall_time_s"] >= 0 and meta["sandbox_method"].startswith("dry-run")
    assert meta["prompt_via"] == "stdin" and "--settings" in meta["argv"] and meta["flags"] == []
    assert "--tools" in meta["argv"] and meta["argv"][meta["argv"].index("--tools") + 1] == "Bash"
    assert load("pilot")[0]["prompt"] not in json.dumps(meta)
    events = drop_pre_init([json.loads(ln)
        for ln in (out / HAIKU / "B" / "medium" / f"{tid}-k1.jsonl").read_text(encoding="utf-8").splitlines()])
    # with --json-schema the answer is one more assistant/user pair (1 run in 20 has none)
    types = [e["type"] for e in events]
    assert types in (["system", "assistant", "user", "assistant", "result"],
                     ["system", "assistant", "user", "assistant", "user", "assistant", "result"])
    c_events = drop_pre_init([json.loads(ln)
        for ln in (out / HAIKU / "C" / "medium" / f"{tid}-k1.jsonl").read_text(encoding="utf-8").splitlines()])
    assert c_events[0]["tools"] == fixture("init_C.json")["tools"]
    assert c_events[1]["message"]["content"][0]["name"] == "mcp__tanabesugano__ts_fit_spectrum"


def test_bad_init_aborts_the_cell(tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_BAD_INIT", "1")
    rc, out = run_dry(tmp_path, models=(HAIKU,), conds="A,B", k=2, limit=2)
    m = manifest(out)
    assert rc == 1
    assert m["counts"]["planned"] == 8 and m["counts"]["done"] == 0 and m["counts"]["aborted"] == 8
    assert {(c["model"], c["condition"]) for c in m["aborted_cells"]} == {(HAIKU, "A"), (HAIKU, "B")}
    assert "claude-fake-9-9" in m["aborted_cells"][0]["reasons"][0]
    # only the first run of each cell ever started; its partial transcript (pre-init event and init) is kept aside
    # as an attempt file, so that the scorer does not take it for an answer
    assert [f for f in out.glob("*/*/*/*.jsonl") if ".attempt" not in f.name] == []
    files = sorted(out.glob("*/*/*/*.attempt1.jsonl"))
    assert len(files) == 2 and all(len(f.read_text(encoding="utf-8").splitlines()) == 2 for f in files)
    from tsbench.score.score import find_transcripts

    assert find_transcripts(out) == []
    meta = json.loads(next(out.glob("*/A/*/*.meta.json")).read_text(encoding="utf-8"))
    assert meta["cell_aborted"] and meta["init_mismatches"]


def test_budget_stop_leaves_balanced_matrix(tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_COST_USD", "0.5")
    rc, out = run_dry(tmp_path, models=(HAIKU,), conds="A", k=2, limit=2, budget=1.0)
    m = manifest(out)
    assert rc == runner.EX_TEMPFAIL and m["stopped_by_budget"] is True and m["finished"] is True
    assert m["counts"]["done"] == 2 and m["counts"]["not_run_budget"] == 2 and m["counts"]["planned"] == 4
    assert m["total_cost_usd"] == pytest.approx(1.0)
    assert sorted(p.name for p in out.glob("*/*/*/*.jsonl")) == sorted(
        f"{t['id']}-k1.jsonl" for t in load("pilot")[:2])  # k=1 complete before any k=2


def max_budget_in(argv):
    return argv[argv.index("--max-budget-usd") + 1] if "--max-budget-usd" in argv else None


def test_no_per_call_cap_by_default(tmp_path):
    _, out = run_dry(tmp_path, models=(HAIKU,), conds="A,B,C", k=1, limit=2, budget=2.0)
    for meta_file in out.glob("*/*/*/*.meta.json"):
        assert "--max-budget-usd" not in json.loads(meta_file.read_text(encoding="utf-8"))["argv"]
    assert "--max-budget-usd" not in build_argv_default("A")


def build_argv_default(key):
    return runner.build_argv(["claude"], conditions.get(key), HAIKU, "medium", settings_path="/s", mcp_config_path="/m")


def test_per_call_usd_adds_the_cap_and_is_limited_by_the_rest(tmp_path):
    _, out = run_dry(tmp_path, models=(HAIKU,), conds="A", k=1, limit=2, budget=2.0, extra=("--per-call-usd", "0.75"))
    metas = sorted(out.glob("*/A/*/*.meta.json"))
    assert [max_budget_in(json.loads(f.read_text(encoding="utf-8"))["argv"]) for f in metas] == ["0.7500", "0.7500"]
    _, out2 = run_dry(tmp_path, models=(HAIKU,), conds="A", k=1, limit=1, budget=0.5, extra=("--per-call-usd", "3"),
                      out=tmp_path / "r2")
    meta = json.loads(next(out2.glob("*/A/*/*.meta.json")).read_text(encoding="utf-8"))
    assert max_budget_in(meta["argv"]) == "0.5000"  # min(rest of the budget, cap)
    with pytest.raises(SystemExit):
        run_dry(tmp_path, models=(HAIKU,), conds="A", extra=("--per-call-usd", "0"), out=tmp_path / "r3")


def test_budget_is_a_guard_for_starting_runs_not_a_cap(tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_COST_USD", "0.7")
    rc, out = run_dry(tmp_path, models=(HAIKU,), conds="A", k=1, limit=3, budget=1.0)
    m = manifest(out)
    # the second run starts at 0.7 < 1.0 and is not cut (it ends at 1.4); the third is never started
    assert m["counts"]["done"] == 2 and m["counts"]["not_run_budget"] == 1 and m["stopped_by_budget"] is True
    assert m["total_cost_usd"] == pytest.approx(1.4)


def test_max_turns_per_condition_in_conditions_and_argv(tmp_path):
    assert conditions.MAX_TURNS == {"A": 15, "B": 40, "C": 25}
    for key, n in conditions.MAX_TURNS.items():
        argv = build_argv_default(key)
        assert argv[argv.index("--max-turns") + 1] == str(n)
    _, out = run_dry(tmp_path, models=(HAIKU,), conds="A,B,C", k=1, limit=1)
    for key, n in conditions.MAX_TURNS.items():
        argv = json.loads(next(out.glob(f"*/{key}/*/*.meta.json")).read_text(encoding="utf-8"))["argv"]
        assert argv[argv.index("--max-turns") + 1] == str(n)


def test_missing_result_event_is_flagged_and_books_nothing_without_a_cap(tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_NO_RESULT", "1")
    rc, out = run_dry(tmp_path, models=(HAIKU,), conds="A", k=1, limit=2, budget=2.0)
    m = manifest(out)
    assert rc == runner.EX_TEMPFAIL and m["counts"]["done"] == 2 and m["total_cost_usd"] == 0  # nothing answered
    assert [f["flags"] for f in m["flagged_runs"]] == [["cost_unknown", "no_result_event"]] * 2
    # with a per-call cap, the cap is what an unknown run is charged
    _, out2 = run_dry(tmp_path, models=(HAIKU,), conds="A", k=1, limit=2, budget=2.0,
                      extra=("--per-call-usd", "1.5"), out=tmp_path / "r2")
    meta = json.loads(sorted(out2.glob("*/A/*/*.meta.json"))[0].read_text(encoding="utf-8"))
    assert meta["cost_unknown"] is True and meta["cost_usd"] == pytest.approx(1.5)


def test_resume_skips_finished_and_reruns_zero_cost_error(tmp_path):
    rc, out = run_dry(tmp_path, models=(HAIKU,), conds="A", k=1, limit=2)
    t1, t2 = (t["id"] for t in load("pilot")[:2])
    first = out / HAIKU / "A" / "medium" / f"{t1}-k1.jsonl"
    before = first.read_bytes()
    # second transcript becomes the zero-cost infrastructure error from the real fixture
    second = out / HAIKU / "A" / "medium" / f"{t2}-k1.jsonl"
    err = json.dumps(fixture("result_error_not_logged_in.json"))
    second.write_text(json.dumps(fixture("init_A.json")) + "\n" + err + "\n", encoding="utf-8")

    rc, _ = run_dry(tmp_path, models=(HAIKU,), conds="A", k=1, limit=2, extra=("--resume",))
    m = manifest(out)
    assert rc == 0 and m["counts"]["skipped"] == 1 and m["counts"]["done"] == 1
    assert first.read_bytes() == before  # untouched
    assert json.loads(second.read_text(encoding="utf-8").splitlines()[-1])["is_error"] is False  # re-run
    assert list(out.glob("MANIFEST.prev-*.json"))  # the earlier manifest was kept

    rc, _ = run_dry(tmp_path, models=(HAIKU,), conds="A", k=1, limit=2, extra=("--resume",))
    assert manifest(out)["counts"]["skipped"] == 2 and manifest(out)["counts"]["done"] == 0


def test_resume_reruns_truncated_transcript(tmp_path):
    _, out = run_dry(tmp_path, models=(HAIKU,), conds="A", k=1, limit=1)
    f = next(out.glob("*/*/*/*.jsonl"))
    lines = f.read_text(encoding="utf-8").splitlines()
    f.write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")  # drop the result event
    run_dry(tmp_path, models=(HAIKU,), conds="A", k=1, limit=1, extra=("--resume",))
    assert json.loads(f.read_text(encoding="utf-8").splitlines()[-1])["type"] == "result"


def _result_line(**kw) -> str:
    return json.dumps({"type": "result", "subtype": "success", "is_error": True, **kw}) + "\n"


def test_transcript_status_reruns_paid_api_errors_but_not_harness_limits(tmp_path):
    p = tmp_path / "x.jsonl"
    for ev, done in (({"api_error_status": 500, "terminal_reason": "api_error", "total_cost_usd": 0.4,
                       "result": "API Error: 500 Internal server error"}, False),
                     ({"terminal_reason": "api_error", "total_cost_usd": 0.4,
                       "result": "API Error: overloaded"}, False),
                     ({"subtype": "error_max_turns", "terminal_reason": "max_turns", "total_cost_usd": 0.4}, True),
                     ({"subtype": "error_max_budget_usd", "terminal_reason": "budget_exhausted",
                       "total_cost_usd": 0.4}, True),
                     # a context overflow is the model's failure: scored wrong, never sampled again, also at cost 0
                     ({"api_error_status": 400, "terminal_reason": "api_error", "total_cost_usd": 0.4,
                       "result": "API Error: 400 litellm.ContextWindowExceededError: maximum context length"}, True),
                     ({"api_error_status": 413, "total_cost_usd": 0, "result": "API Error: 413 Request too large"},
                      True),
                     ({"api_error_status": 400, "total_cost_usd": 0.4, "result": "API Error: 400 bad schema"}, False)):
        p.write_text(_result_line(**ev), encoding="utf-8")
        assert runner.transcript_status(p)[0] is done, ev


def test_is_api_error_agrees_with_the_scorers_not_evaluable_rule():
    from types import SimpleNamespace

    from tsbench.score.score import not_evaluable_reason
    cases = [{"is_error": True, "api_error_status": 429}, {"is_error": True, "api_error_status": "500"},
             {"is_error": True, "terminal_reason": "api_error"}, {"is_error": True, "result": "API Error: x"},
             {"is_error": True, "subtype": "error_max_turns"}, {"is_error": False, "api_error_status": 500},
             {"is_error": True, "result": "wrong Dq"},
             {"is_error": True, "api_error_status": 400, "result": "API Error: 400 prompt is too long"},
             {"is_error": True, "api_error_status": 400, "result": "API Error: 400 bad schema"}]
    for ev in cases:
        assert runner.is_api_error(ev) is (not_evaluable_reason(SimpleNamespace(result=ev)) is not None), ev


def test_next_attempt_path_is_the_first_free_attempt_number(tmp_path):
    f = tmp_path / "run.jsonl"
    assert runner.next_attempt_path(f) == (1, tmp_path / "run.attempt1.jsonl")
    runner.attempt_path(f, 1).write_text("{}\n", encoding="utf-8")
    runner.attempt_path(f, 2).write_text("{}\n", encoding="utf-8")
    assert runner.next_attempt_path(f) == (3, tmp_path / "run.attempt3.jsonl")
    runner.attempt_path(f, 2).unlink()  # a gap is filled first
    assert runner.next_attempt_path(f) == (2, tmp_path / "run.attempt2.jsonl")


def test_resume_reruns_a_paid_5xx_keeps_the_attempt_and_books_its_cost(tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_COST_USD", "0.3")
    _, out = run_dry(tmp_path, models=(HAIKU,), conds="A", k=1, limit=1)
    f = next(p for p in out.glob("*/*/*/*.jsonl") if ".attempt" not in p.name)
    f.write_text(_result_line(api_error_status=500, terminal_reason="api_error", total_cost_usd=0.25,
                              result="API Error: 500"), encoding="utf-8")
    run_dry(tmp_path, models=(HAIKU,), conds="A", k=1, limit=1, extra=("--resume",))
    assert json.loads(f.read_text(encoding="utf-8").splitlines()[-1])["is_error"] is False  # re-run
    kept = runner.attempt_path(f, 1)
    assert json.loads(kept.read_text(encoding="utf-8"))["api_error_status"] == 500  # the paid error is kept
    meta = json.loads(runner.meta_path(f).read_text(encoding="utf-8"))
    assert meta["earlier_attempt"] == {"attempt": 1, "reason": "api_error", "cost_usd": 0.25}
    assert manifest(out)["total_cost_usd"] == pytest.approx(0.55)  # 0.25 of the error + 0.3 of the re-run


def test_resume_counts_earlier_cost_toward_budget(tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_COST_USD", "0.3")
    _, out = run_dry(tmp_path, models=(HAIKU,), conds="A", k=1, limit=2, budget=10)
    assert manifest(out)["total_cost_usd"] == pytest.approx(0.6)
    _, out = run_dry(tmp_path, models=(HAIKU,), conds="A", k=2, limit=2, budget=0.7, extra=("--resume",))
    m = manifest(out)
    assert m["counts"]["skipped"] == 2 and m["counts"]["done"] == 1 and m["stopped_by_budget"] is True
    assert m["total_cost_usd"] == pytest.approx(0.9)


def test_transcript_status(tmp_path):
    p = tmp_path / "x.jsonl"
    assert runner.transcript_status(p) == (False, 0.0)
    p.write_text(json.dumps({"type": "result", "is_error": False, "total_cost_usd": 0.25}) + "\n", encoding="utf-8")
    assert runner.transcript_status(p) == (True, 0.25)
    p.write_text(json.dumps({"type": "result", "is_error": True, "total_cost_usd": 0.25}) + "\n", encoding="utf-8")
    assert runner.transcript_status(p) == (True, 0.25)  # a paid error is done
    p.write_text(json.dumps({"type": "result", "is_error": True, "total_cost_usd": 0}) + "\n", encoding="utf-8")
    assert runner.transcript_status(p) == (False, 0.0)
    p.write_text('{"type": "resu', encoding="utf-8")
    assert runner.transcript_status(p) == (False, 0.0)


def _sidecar(transcript: pathlib.Path, **fields) -> None:
    """A sidecar written after the transcript, as the runner writes it."""
    meta = runner.meta_path(transcript)
    meta.write_text(json.dumps(fields), encoding="utf-8")
    stamp = transcript.stat().st_mtime + 5
    os.utime(meta, (stamp, stamp))


def test_transcript_status_counts_a_wall_timeout_as_done_and_an_interrupted_run_as_not_done(tmp_path):
    p = tmp_path / "x.jsonl"
    p.write_text(json.dumps({"type": "assistant"}) + "\n", encoding="utf-8")  # no result event
    assert runner.transcript_status(p) == (False, 0.0)  # killed: no sidecar
    _sidecar(p, timed_out=False, cost_usd=0.0)
    assert runner.transcript_status(p) == (False, 0.0)  # crashed: the sidecar says it did not time out
    _sidecar(p, timed_out=True, cost_usd=1.5)
    assert runner.transcript_status(p) == (True, 1.5)  # a deliberate harness limit is an outcome; its booked cost
    runner.meta_path(p).write_text("not json", encoding="utf-8")
    assert runner.transcript_status(p) == (False, 0.0)
    _sidecar(p, timed_out=True, cost_usd=0.0)
    os.utime(p, (p.stat().st_mtime + 60, p.stat().st_mtime + 60))  # a newer transcript: the sidecar is an older run's
    assert runner.transcript_status(p) == (False, 0.0)


# ------------------------------------------------------------------ startup guards
def test_confirmatory_without_preregistration_exits_2_before_anything(tmp_path, monkeypatch, capsys):
    import tsbench.tasks as tasks_mod

    def boom(*a, **k):
        raise AssertionError("tasks were loaded before the guard")

    monkeypatch.setattr(tasks_mod, "load", boom)
    out = tmp_path / "runs"
    with pytest.raises(SystemExit) as e:
        runner.main(["--split", "confirmatory", "--models", HAIKU, "--conditions", "A", "--effort", "medium",
                     "--k", "1", "--budget-usd", "1", "--out", str(out), "--dry-run"])
    assert e.value.code == 2 and not out.exists()
    assert "preregistered" in capsys.readouterr().err
    with pytest.raises(SystemExit) as e:  # a bare string is not a DOI
        runner.main(["--split", "confirmatory", "--models", HAIKU, "--conditions", "A", "--effort", "medium",
                     "--k", "1", "--budget-usd", "1", "--out", str(out), "--dry-run",
                     "--i-have-preregistered", "yes"])
    assert e.value.code == 2


@pytest.mark.parametrize("bad", ["claude-haiku", "haiku", "claude-haiku-5"])
def test_short_model_ids_exit_2(tmp_path, bad):
    with pytest.raises(SystemExit) as e:
        run_dry(tmp_path, models=(bad,))
    assert e.value.code == 2


def test_missing_key_in_real_mode_exits_2_naming_the_variable(tmp_path, monkeypatch, capsys):
    for v in ("TSMCP_ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN"):
        monkeypatch.delenv(v, raising=False)
    argv = ["--split", "pilot", "--models", HAIKU, "--conditions", "A", "--effort", "medium", "--k", "1",
            "--budget-usd", "1", "--out", str(tmp_path / "r")]
    with pytest.raises(SystemExit) as e:
        runner.main(argv)
    assert e.value.code == 2 and "TSMCP_ANTHROPIC_API_KEY" in capsys.readouterr().err
    with pytest.raises(SystemExit) as e:
        runner.main(argv + ["--gateway"])
    assert e.value.code == 2 and "ANTHROPIC_BASE_URL" in capsys.readouterr().err
    assert not (tmp_path / "r").exists()


# ------------------------------------------------------------------ sandbox probe
def tr(text):
    return {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t", "content": text}]}}


GOOD = ("PROBE_CTRL1 rc=0\n5\nPROBE_CTRL2 rc=0\nPROBE_PATHS rc=0\nPROBE_KEYENV rc=0\nPROBE_IMPORT rc=1\n"
        "PROBE_PIP rc=1\nPROBE_NET rc=6\nPROBE_VENV rc=126\nPROBE_READ rc=1\nPROBE_TSBIN rc=1\nPROBE_TSBIN rc=1\n"
        "PROBE_HOMECACHE rc=1\nPROBE_HOMECACHE rc=1\nPROBE_HOMESECRETS rc=1\nPROBE_HOMESECRETS rc=1\n"
        "PROBE_LOCALHOST rc=7\nPROBE_APIHOST rc=56\nPROBE_APIHOST rc=56\nPROBE_DNS rc=1\nPROBE_NUMPY rc=0\n"
        "PROBE_HEREDOC rc=0")


def probe_events(text=GOOD, init=None, extra=()):
    return [init or fixture("init_B.json"), tool_use("Bash", command="x"), tr(text), *extra]


def test_probe_pass():
    ev = sandbox.evaluate_transcript(probe_events(), HAIKU)
    assert ev["passed"] and ev["reasons"] == []
    assert ev["markers"]["NET"] == [6] and ev["markers"]["CTRL1"] == [0]


@pytest.mark.parametrize("leak", ["IMPORT", "PIP", "NET", "VENV", "READ"])
def test_probe_fails_when_a_forbidden_action_succeeds(leak):
    text = re.sub(rf"PROBE_{leak} rc=\d+", f"PROBE_{leak} rc=0", GOOD)
    ev = sandbox.evaluate_transcript(probe_events(text), HAIKU)
    assert not ev["passed"] and any(leak in r for r in ev["reasons"])


def test_probe_fails_when_bash_did_not_really_run():
    for text in ("", "I could not run that", GOOD.replace("PROBE_CTRL1 rc=0", ""), GOOD.replace("PROBE_CTRL2 rc=0",
                                                                                              "PROBE_CTRL2 rc=127")):
        assert not sandbox.evaluate_transcript(probe_events(text), HAIKU)["passed"]


def test_probe_fails_when_a_marker_is_missing():
    assert not sandbox.evaluate_transcript(probe_events(GOOD.replace("PROBE_READ rc=1", "")), HAIKU)["passed"]


def test_probe_ignores_markers_in_prose_and_tool_input():
    prose = {"type": "assistant", "message": {"content": [{"type": "text", "text": GOOD}]}}
    echo_in_input = tool_use("Bash", command=GOOD)
    ev = sandbox.evaluate_transcript([fixture("init_B.json"), echo_in_input, prose,
                                      {"type": "result", "result": GOOD}], HAIKU)
    assert not ev["passed"] and ev["markers"] == {}


def test_probe_reads_list_shaped_tool_result_content():
    events = [fixture("init_B.json"), {"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": "t", "content": [{"type": "text", "text": GOOD}]}]}}]
    assert sandbox.evaluate_transcript(events, HAIKU)["passed"]


def test_probe_fails_on_escape_request_or_bad_init():
    esc = tool_use("Bash", command="x", dangerouslyDisableSandbox=True)
    assert not sandbox.evaluate_transcript([fixture("init_B.json"), esc, tr(GOOD)], HAIKU)["passed"]
    assert not sandbox.evaluate_transcript(probe_events(init=fixture("init_A.json")), HAIKU)["passed"]
    assert not sandbox.evaluate_transcript(probe_events(), SONNET)["passed"]  # wrong model
    assert not sandbox.evaluate_transcript([], HAIKU)["passed"]


def test_probe_prompt_carries_the_script_verbatim():
    hp = {"HOMECACHE": [".local"], "HOMESECRETS": [".ssh", ".zsh_history"]}
    p = sandbox.probe_prompt(hp)
    for line in sandbox.probe_script_lines(hp):
        assert line in p
    assert '"$TSPROBE_REPO"/.venv/bin/python' in p and '"$TSPROBE_REPO"/src/tsbench/data/tasks/tasks.jsonl' in p
    assert "dangerouslyDisableSandbox" not in p
    # the script names no host path; the repo and real home come from the probe's environment
    assert str(REPO_ROOT) not in p and str(pathlib.Path("~").expanduser()) not in p


def fake_session(real_mode=False):
    s = runner.Session.create(dry_run=True, gateway=False)
    if real_mode:  # behaves like a real session for the probe record (it is still the fake process)
        s.dry_run = False
    return s


def test_run_probe_against_the_fake_passes(tmp_path):
    s = fake_session()
    try:
        rec = sandbox_probe.run_probe(s, tmp_path)
    finally:
        s.close()
    assert rec["passed"] and rec["method"] == "builtin" and rec["fake"] is True and rec["cost_usd"] == 0
    assert rec["settings_sha256"] == s.settings_sha256 and rec["claude_version"] == "fake-0"
    assert json.loads((tmp_path / "sandbox_probe.json").read_text(encoding="utf-8")) == rec
    # the transcript is recorded relative to --out
    assert rec["transcript"] == "_sandbox_probe/transcript.jsonl" and (tmp_path / rec["transcript"]).exists()
    assert rec["markers"]["CTRL2"] == [0] and rec["markers"]["KEYENV"] == [0]
    assert rec["probe_script_sha256"] == sandbox.probe_script_sha256(rec["home_paths_tested"])
    assert rec["auth_mode"] == "direct" and rec["child_path"].startswith("<B_VENV>/bin:/usr/bin:/bin")
    assert sandbox.load_reusable_probe(tmp_path, "fake-0", rec["settings_sha256"]) is None  # fake never reused


@pytest.mark.parametrize("env,reason", [
    ({"FAKE_PROBE_LEAK": "NET"}, "NET"), ({"FAKE_PROBE_LEAK": "IMPORT,VENV"}, "IMPORT"),
    ({"FAKE_PROBE_LEAK": "KEYENV"}, "KEYENV"), ({"FAKE_PROBE_LEAK": "TSBIN"}, "TSBIN"),
    ({"FAKE_PROBE_LEAK": "HOMESECRETS"}, "HOMESECRETS"), ({"FAKE_PROBE_LEAK": "PATHS"}, "PATHS"),
    ({"FAKE_PROBE_BASH_FAIL": "1"}, "CTRL1"), ({"FAKE_PROBE_ESCAPE": "1"}, "dangerously"),
])
def test_run_probe_against_the_fake_fails(tmp_path, monkeypatch, env, reason):
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    s = fake_session()
    try:
        rec = sandbox_probe.run_probe(s, tmp_path)
    finally:
        s.close()
    assert not rec["passed"] and any(reason in r for r in rec["reasons"])


def test_sandbox_cli_settings_only_and_fake_probe(tmp_path, capsys, monkeypatch):
    assert sandbox_probe.main(["--settings-only"]) == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["sandbox"]["filesystem"]["denyRead"][0] == str(REPO_ROOT)
    assert sandbox_probe.main(["--probe", "--fake", "--out", str(tmp_path / "p")]) == 0
    assert (tmp_path / "p" / "sandbox_probe.json").exists()
    monkeypatch.setenv("FAKE_PROBE_LEAK", "PIP")
    assert sandbox_probe.main(["--probe", "--fake", "--out", str(tmp_path / "p2")]) == 1
    with pytest.raises(SystemExit):
        sandbox_probe.main(["--probe"])  # --out missing


def test_method_info_records_the_choice(monkeypatch):
    assert sandbox.method_info(None, True)["method"] == "dry-run (not probed)"
    assert sandbox.method_info({"passed": True}, False)["method"] == "builtin"
    monkeypatch.setattr(sandbox, "detect_container", lambda: "podman")
    info = sandbox.method_info({"passed": False, "reasons": ["NET rc=[0]"]}, False)
    assert info["method"] == "skipped" and "NET" in info["reason"] and "not built" in info["container"]


# ----------------------------------------------------------- runner + probe gating (fake process, real-mode flow)
@pytest.fixture
def real_mode_fake(monkeypatch):
    """Make Session.create hand out a fake-backed session that the runner treats as non-dry."""
    orig = runner.Session.create.__func__

    def create(cls, *, dry_run, gateway, parent_env=None, repo=runner.REPO_ROOT, **kw):
        s = orig(cls, dry_run=True, gateway=gateway, parent_env=parent_env, repo=repo, **kw)
        s.dry_run = False
        return s

    monkeypatch.setattr(runner.Session, "create", classmethod(create))


def real_args(tmp_path, conds="A,B,C", extra=()):
    return ["--split", "pilot", "--models", HAIKU, "--conditions", conds, "--effort", "medium", "--k", "1",
            "--limit", "1", "--budget-usd", "5", "--out", str(tmp_path / "runs"), *extra]


def test_probe_pass_runs_b_and_is_reused(tmp_path, real_mode_fake, monkeypatch):
    assert runner.main(real_args(tmp_path)) == 0
    out = tmp_path / "runs"
    m = manifest(out)
    assert m["sandbox"]["method"] == "builtin" and m["sandbox"]["probe"]["passed"] is True
    assert m["counts"]["done"] == 3 and m["counts"]["not_run_sandbox"] == 0
    # second invocation: same version and settings hash -> reused, no second probe call
    calls = []
    orig = sandbox_probe.run_probe
    monkeypatch.setattr(sandbox_probe, "run_probe", lambda *a, **k: calls.append(1) or orig(*a, **k))
    assert runner.main(real_args(tmp_path, extra=("--resume",))) == 0
    assert calls == [] and manifest(out)["sandbox"]["method"] == "builtin"
    # a changed claude version invalidates the record
    rec = json.loads((out / "sandbox_probe.json").read_text(encoding="utf-8"))
    rec["claude_version"] = "other"
    (out / "sandbox_probe.json").write_text(json.dumps(rec), encoding="utf-8")
    (out / HAIKU / "B").joinpath("medium").mkdir(parents=True, exist_ok=True)
    for f in (out / HAIKU / "B" / "medium").glob("*"):
        f.unlink()
    assert runner.main(real_args(tmp_path, conds="B", extra=("--resume",))) == 0
    assert calls == [1]


def test_probe_fail_skips_b_but_a_and_c_continue(tmp_path, real_mode_fake, monkeypatch):
    monkeypatch.setenv("FAKE_PROBE_LEAK", "NET")
    assert runner.main(real_args(tmp_path)) == 0
    out = tmp_path / "runs"
    m = manifest(out)
    assert m["sandbox"]["method"] == "skipped" and "NET" in m["sandbox"]["reason"]
    assert m["counts"]["done"] == 2 and m["counts"]["not_run_sandbox"] == 1
    assert not list(out.glob("*/B/*/*.jsonl")) and len(list(out.glob("*/[AC]/*/*.jsonl"))) == 2


# ------------------------------------------------------------------ the fake itself
def test_fake_is_deterministic_and_rates_are_about_right():
    assert fake_cli.decide("p", HAIKU, "A") == fake_cli.decide("p", HAIKU, "A")
    n = 3000
    for cond, rate in fake_cli.RATES.items():
        hits = sum(fake_cli.decide(f"prompt {i}", HAIKU, cond)[0] for i in range(n))
        assert abs(hits / n - rate) < 0.04
    no_json = sum(fake_cli.decide(f"prompt {i}", HAIKU, "A")[1] for i in range(n))
    assert abs(no_json / n - 0.05) < 0.02


def test_fake_answers_follow_the_reference():
    for t in load("pilot"):
        if t["answer_schema"] == "curve":
            good, bad = (fake_cli.answer_for(t, ok, "curve") for ok in (True, False))
            assert [p["e_over_b"] for p in good["points"]] == [p["e_over_b"] for p in t["reference_curve"]]
            assert len(bad["points"]) == len(good["points"]) == 9
            assert all(b["e_over_b"] != g["e_over_b"] for b, g in zip(bad["points"], good["points"], strict=False))
            continue
        if t["answer_schema"] in ("batch", "pairing", "diagram"):
            good, bad = (fake_cli.answer_for(t, ok, t["answer_schema"]) for ok in (True, False))
            score = {"batch": batch_score.score_batch, "pairing": pairing_score.score_pairing,
                     "diagram": diagram_score.score_diagram}[t["answer_schema"]]
            assert score(t, good)["correct"] and not score(t, bad)["correct"]
            wrong_shape = fake_cli.answer_for(t, True)  # a fit-shaped answer to a batch/pairing task is wrong
            assert "Dq" in wrong_shape and not score(t, wrong_shape)["correct"]
            continue
        good = fake_cli.answer_for(t, True)
        bad = fake_cli.answer_for(t, False)
        if t["expect_out_of_scope"]:
            assert good == {"Dq": None, "B": None, "C": None, "out_of_scope": True, "reason": good["reason"]}
            assert bad["out_of_scope"] is False and bad["Dq"] is not None
        else:
            assert good["Dq"] == t["reference"]["Dq"] and good["B"] == t["reference"]["B"]
            assert bad["Dq"] == pytest.approx(t["reference"]["Dq"] * 1.15, abs=0.01)
            assert (good["C"] is not None) == ("C" in t["required"])


def run_fake(args, prompt, **env):
    e = {**os.environ, **env}
    p = subprocess.run([sys.executable, "-m", "tsbench.run.fake_cli", *args], input=prompt, text=True,
                       capture_output=True, env=e, cwd=str(REPO_ROOT), timeout=60, encoding="utf-8")
    assert p.returncode == 0, p.stderr
    raw = [json.loads(ln) for ln in p.stdout.splitlines()]
    assert raw[0]["subtype"] == "ui_invalidate"  # shaped like real claude 2.1.308
    return drop_pre_init(raw)


def test_fake_stream_shape_and_unmatched_prompt():
    task = load("pilot")[0]
    args = ["-p", "--model", HAIKU, "--tools", "Bash", "--settings", "x"]
    ev = run_fake(args, task["prompt"], FAKE_SEED="s", FAKE_COST_USD="0.25")
    assert [e["type"] for e in ev] == ["system", "assistant", "user", "assistant", "result"]
    assert ev[0]["model"] == HAIKU and ev[0]["tools"] == ["Bash"] and ev[0]["claude_code_version"] == "fake-0"
    res = ev[-1]
    assert res["subtype"] == "success" and res["is_error"] is False and res["total_cost_usd"] == 0.25
    assert res["permission_denials"] == [] and "usage" in res and "num_turns" in res
    last = res["result"].splitlines()[-1]
    if last.startswith("{"):
        assert {"Dq", "B", "out_of_scope"} <= set(json.loads(last))
    odd = run_fake(["-p", "--model", HAIKU, "--tools", ""], "Some unrelated question.")
    assert odd[0]["tools"] == [] and odd[0]["mcp_servers"] == [] and len(odd) == 3
    assert not odd[-1]["result"].splitlines()[-1].startswith("{")


def test_fake_reads_its_prompt_and_writes_its_events_as_utf_8_in_any_locale():
    """The runner encodes the prompt as UTF-8; the fake decodes it as UTF-8 even when the locale says ASCII."""
    task = load("pilot")[0]
    env = {k: v for k, v in os.environ.items() if not k.startswith(("LC_", "LANG", "PYTHON"))}
    env.update(LC_ALL="C", PYTHONUTF8="0", PYTHONCOERCECLOCALE="0")
    p = subprocess.run([sys.executable, "-m", "tsbench.run.fake_cli", "-p", "--model", HAIKU, "--tools", "Bash",
                        "--settings", "x"], input=("café é\n" + task["prompt"]).encode("utf-8"),
                       capture_output=True, env=env, cwd=str(REPO_ROOT), timeout=60)
    assert p.returncode == 0, p.stderr
    result = json.loads(p.stdout.decode("utf-8").splitlines()[-1])
    assert result["type"] == "result" and result["result"].startswith("Working it out: Dq = ")


def test_fake_hooks():
    args = ["-p", "--model", HAIKU, "--mcp-config", "x", "--allowedTools", "mcp__tanabesugano__*"]
    assert run_fake(args, "q", FAKE_BAD_INIT="1")[0]["model"] == "claude-fake-9-9"
    ev = run_fake(args, "q", FAKE_NO_RESULT="1")
    assert ev[-1]["type"] == "assistant"
    ev = run_fake(args, load("pilot")[0]["prompt"])
    assert ev[0]["mcp_servers"][0]["status"] == "connected"
    assert ev[0]["tools"] == fixture("init_C.json", structured=False)["tools"]


def test_main_checkout_denied_from_a_linked_checkout(tmp_path):
    import subprocess as sp
    main = tmp_path / "main"
    main.mkdir()
    sp.run(["git", "init", "-q", str(main)], check=True)
    sp.run(["git", "-C", str(main), "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q",
            "--allow-empty", "-m", "init"], check=True)
    wt = tmp_path / "wt"
    sp.run(["git", "-C", str(main), "worktree", "add", "-q", str(wt)], check=True)
    assert sandbox.main_checkouts(wt) == [str(main.resolve())]
    assert sandbox.main_checkouts(main) == []
    deny = sandbox.render_settings(wt)["sandbox"]["filesystem"]["denyRead"]
    assert str(wt) in deny and str(main.resolve()) in deny


def test_permission_denials_flagged_in_every_condition():
    from tsbench.run.runner import compute_flags
    res = {"type": "result", "permission_denials": [{"tool_name": "mcp__tanabesugano__ts_fit_spectrum"}]}
    for cond in "ABC":
        flags, details = compute_flags(cond, [], res)
        assert "permission_denials" in flags and details["permission_denials"] == 1


def test_c_all_mcp_errors_flagged():
    from tsbench.run.runner import compute_flags
    use = {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": "t1", "name": "mcp__tanabesugano__ts_fit_spectrum", "input": {}}]}}
    err = {"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": "t1", "is_error": True, "content": "denied"}]}}
    ok = {"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": "t1", "content": "Dq=850"}]}}
    assert "c_all_mcp_errors" in compute_flags("C", [use, err], {"type": "result"})[0]
    assert "c_all_mcp_errors" not in compute_flags("C", [use, ok], {"type": "result"})[0]


def test_numpy_marker_is_required_and_probes_the_whole_stack():
    lines = sandbox.probe_script_lines()
    assert any("PROBE_NUMPY" in line and "import numpy, scipy, sympy, matplotlib" in line for line in lines)
    assert "NUMPY" in sandbox.MUST_BE_ZERO and "NUMPY" not in sandbox.MUST_FAIL
    # the forbidden-import and pip checks stay
    assert any("PROBE_IMPORT" in line and "import tanabesugano" in line for line in lines)
    assert any("PROBE_PIP" in line and "pip download" in line for line in lines)


def test_probe_verdict_requires_numpy_ok():
    for text in (GOOD.replace("PROBE_NUMPY rc=0", "PROBE_NUMPY rc=1"), GOOD.replace("PROBE_NUMPY rc=0", ""),
                 GOOD.replace("PROBE_NUMPY rc=0", "PROBE_NUMPY rc=127")):
        ev = sandbox.evaluate_transcript(probe_events(text), HAIKU)
        assert not ev["passed"] and any("NUMPY" in r for r in ev["reasons"])
    assert sandbox.evaluate_transcript(probe_events(), HAIKU)["passed"]


def test_probe_against_the_fake_fails_without_the_stack(tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_PROBE_NO_STACK", "1")
    s = fake_session()
    try:
        rec = sandbox_probe.run_probe(s, tmp_path)
    finally:
        s.close()
    assert not rec["passed"] and any("NUMPY" in r for r in rec["reasons"])


# ------------------------------------------------------------------ the fixed B stack
FAKE_PINS = "#python-minor: 3.14\n" + "".join(f"{n}==1.0\n" for n in ("numpy", "scipy", "sympy", "matplotlib"))


def fake_run(packages, *, tanabesugano_importable=False, imports_ok=True, pyver="3.14.7"):
    """A stand-in for subprocess.run that plays a venv with these installed packages."""
    def run(cmd, **kw):
        code = cmd[-1]
        out, rc = "", 0
        if "platform" in code:
            out = pyver + "\n"
        elif "importlib.metadata" in code:
            out = json.dumps(packages)
        elif code == "import tanabesugano":
            rc = 0 if tanabesugano_importable else 1
        elif code.startswith("import numpy"):
            rc = 0 if imports_ok else 1
        return subprocess.CompletedProcess(cmd, rc, out, "")
    return run


@pytest.fixture
def pin_file(tmp_path):
    p = tmp_path / "b-stack.txt"
    p.write_text(FAKE_PINS, encoding="utf-8")
    (tmp_path / "venv" / "bin").mkdir(parents=True)
    (tmp_path / "venv" / "bin" / "python").write_text("", encoding="utf-8")
    return p


GOOD_PKGS = {"numpy": "1.0", "scipy": "1.0", "sympy": "1.0", "matplotlib": "1.0"}


def test_committed_pin_file_is_exact_and_has_no_tanabesugano():
    pins, minor = b_stack.load_pins()
    assert {"numpy", "scipy", "sympy", "matplotlib"} <= set(pins) and "tanabesugano" not in pins
    assert minor and re.fullmatch(r"\d+\.\d+", minor)
    for line in b_stack.PIN_FILE.read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.startswith("#"):
            assert re.fullmatch(r"[A-Za-z0-9._-]+==[A-Za-z0-9.]+", line), line


@pytest.mark.parametrize("text", ["numpy>=1\nscipy==1\nsympy==1\nmatplotlib==1\n", "numpy==1\nscipy==1\nsympy==1\n",
                                  FAKE_PINS + "tanabesugano==2.0.0\n", FAKE_PINS + "numpy==1.0\n"])
def test_pin_file_parsing_rejects_loose_missing_forbidden_and_duplicate(text):
    with pytest.raises(b_stack.BStackError):
        b_stack.parse_pins(text)


def test_validate_accepts_a_matching_stack_and_digest_is_stable(tmp_path, pin_file):
    venv = tmp_path / "venv"
    info = b_stack.validate(venv, pin_file, fake_run(GOOD_PKGS))
    assert info["packages"] == GOOD_PKGS and info["path"] == str(venv) and info["python"] == "3.14.7"
    assert re.fullmatch(r"[0-9a-f]{64}", info["digest"])
    assert b_stack.validate(venv, pin_file, fake_run(GOOD_PKGS))["digest"] == info["digest"]
    assert b_stack.validate(venv, pin_file, fake_run({**GOOD_PKGS, "six": "1.17.0"}))["digest"] != info["digest"]
    pin_file.write_text(FAKE_PINS + "# edited\n", encoding="utf-8")
    assert b_stack.validate(venv, pin_file, fake_run(GOOD_PKGS))["digest"] != info["digest"]


def test_validate_rejects_a_stack_with_tanabesugano(tmp_path, pin_file):
    with pytest.raises(b_stack.ForbiddenPackageError):
        b_stack.validate(tmp_path / "venv", pin_file, fake_run({**GOOD_PKGS, "tanabesugano": "2.0.0"}))
    with pytest.raises(b_stack.ForbiddenPackageError):
        b_stack.validate(tmp_path / "venv", pin_file, fake_run(GOOD_PKGS, tanabesugano_importable=True))
    # never repaired automatically, even with create=True
    with pytest.raises(b_stack.ForbiddenPackageError):
        b_stack.ensure_b_stack(tmp_path / "venv", pin_file, run=fake_run({**GOOD_PKGS, "tanabesugano": "2.0.0"}))


@pytest.mark.parametrize("packages,pyver", [({**GOOD_PKGS, "numpy": "1.1"}, "3.14.7"), ({"numpy": "1.0"}, "3.14.7"),
                                            (GOOD_PKGS, "3.12.1")])
def test_validate_rejects_a_wrong_pin_a_missing_package_or_a_wrong_python(tmp_path, pin_file, packages, pyver):
    with pytest.raises(b_stack.BStackError):
        b_stack.validate(tmp_path / "venv", pin_file, fake_run(packages, pyver=pyver))
    with pytest.raises(b_stack.BStackError):  # --check never installs
        b_stack.ensure_b_stack(tmp_path / "venv", pin_file, create=False, run=fake_run(packages, pyver=pyver))


def test_validate_rejects_a_stack_that_does_not_import(tmp_path, pin_file):
    with pytest.raises(b_stack.BStackError, match="fails"):
        b_stack.validate(tmp_path / "venv", pin_file, fake_run(GOOD_PKGS, imports_ok=False))


def test_ensure_is_idempotent_and_creates_with_venv_without_pip_and_uv(tmp_path, pin_file, monkeypatch):
    venv = tmp_path / "newvenv"
    state = {"installed": False, "calls": []}

    def run(cmd, **kw):
        state["calls"].append(list(cmd))
        if cmd[1:4] == ["-m", "venv", "--without-pip"]:
            (venv / "bin").mkdir(parents=True)
            (venv / "bin" / "python").write_text("", encoding="utf-8")
            return subprocess.CompletedProcess(cmd, 0, "", "")
        if cmd[1:3] == ["pip", "install"]:
            state["installed"] = True
            return subprocess.CompletedProcess(cmd, 0, "", "")
        pk = GOOD_PKGS if state["installed"] else {}
        return fake_run(pk)(cmd, **kw)

    monkeypatch.setattr(b_stack.shutil, "which", lambda name: "/usr/bin/uv")
    monkeypatch.setattr(b_stack, "_base_python", lambda minor: sys.executable)
    first = b_stack.ensure_b_stack(venv, pin_file, run=run)
    created = [c for c in state["calls"] if c[1:4] == ["-m", "venv", "--without-pip"]]
    installs = [c for c in state["calls"] if c[1:3] == ["pip", "install"]]
    assert len(created) == 1 and len(installs) == 1
    assert installs[0][:5] == ["/usr/bin/uv", "pip", "install", "--python", str(venv / "bin" / "python")]
    assert installs[0][-2:] == ["-r", str(pin_file)]
    again = b_stack.ensure_b_stack(venv, pin_file, run=run)
    assert again == first and len([c for c in state["calls"] if c[1:3] == ["pip", "install"]]) == 1  # no reinstall


def test_b_venv_dir_default_override_and_not_inside_the_repo(tmp_path):
    assert b_stack.b_venv_dir({"HOME": str(tmp_path)}) == tmp_path / ".cache" / "tsbench" / "venv-B"
    assert b_stack.b_venv_dir({"XDG_CACHE_HOME": str(tmp_path / "x")}) == tmp_path / "x" / "tsbench" / "venv-B"
    assert b_stack.b_venv_dir({"TSBENCH_B_VENV": str(tmp_path / "e")}) == tmp_path / "e"
    assert b_stack.b_venv_dir({"TSBENCH_B_VENV": str(tmp_path / "e")}, str(tmp_path / "flag")) == tmp_path / "flag"
    with pytest.raises(b_stack.BStackError):
        b_stack.b_venv_dir({"TSBENCH_B_VENV": str(REPO_ROOT / "venv-B")})


def test_python_dir_default_and_override_beside_venv_b(tmp_path):
    assert b_stack.python_dir({"HOME": str(tmp_path)}) == tmp_path / ".cache" / "tsbench" / "python"
    assert b_stack.python_dir({"XDG_CACHE_HOME": str(tmp_path / "x")}) == tmp_path / "x" / "tsbench" / "python"
    assert b_stack.python_dir({"TSBENCH_PYTHON_DIR": str(tmp_path / "p")}) == tmp_path / "p"
    assert b_stack.python_dir({"HOME": str(tmp_path)}).parent == b_stack.b_venv_dir({"HOME": str(tmp_path)}).parent


def stripped_path_has_no_venv(path: str, venv_bin: str) -> bool:
    return venv_bin not in path.split(os.pathsep)


def test_b_path_starts_with_the_venv_bin_and_a_and_c_have_no_venv(tmp_path):
    venv = fake_b_venv(tmp_path)
    s = runner.Session.create(dry_run=True, gateway=False, b_venv=venv)
    try:
        vbin = str(venv / "bin")
        assert s.b_stack["path"] == str(venv) and s.b_stack["bin"] == vbin
        assert s.child_env("B")["PATH"].split(os.pathsep)[0] == vbin
        for cond in ("A", "C", None):
            assert stripped_path_has_no_venv(s.child_env(cond)["PATH"], vbin)
        assert s.child_env("B")["PATH"].split(os.pathsep)[1:] == s.child_env("A")["PATH"].split(os.pathsep)
    finally:
        s.close()


def test_session_without_b_has_no_venv_on_any_path(tmp_path):
    s = runner.Session.create(dry_run=True, gateway=False, b_venv=fake_b_venv(tmp_path), need_b=False)
    try:
        assert s.b_stack is None and s.child_env("B")["PATH"] == s.child_env("A")["PATH"]
    finally:
        s.close()


def test_b_venv_inside_the_repo_aborts(tmp_path):
    with pytest.raises(SystemExit) as e:
        runner.Session.create(dry_run=True, gateway=False, b_venv=REPO_ROOT / "venv-B")
    assert e.value.code == 2


def test_runner_passes_the_b_path_only_to_b_and_records_the_stack(tmp_path, monkeypatch):
    seen = {}
    orig = runner.execute_with_retries

    def spy(argv, prompt, env, transcript, cond, model, **kw):
        seen[cond.key] = env["PATH"]
        return orig(argv, prompt, env, transcript, cond, model, **kw)

    monkeypatch.setattr(runner, "execute_with_retries", spy)
    venv = fake_b_venv(tmp_path)
    rc, out = run_dry(tmp_path, limit=1, extra=("--b-venv", str(venv)))
    assert rc == 0
    vbin = str(venv / "bin")
    assert seen["B"].split(os.pathsep)[0] == vbin
    assert vbin not in seen["A"].split(os.pathsep) and vbin not in seen["C"].split(os.pathsep)
    m = manifest(out)
    assert m["b_stack"]["path"] == "<B_VENV>" and m["b_stack"]["bin"] == "<B_VENV>/bin"  # placeholder + digest
    assert set(m["b_stack"]) >= {"path", "python", "packages", "digest"}
    assert m["child_path"]["B"].startswith("<B_VENV>/bin" + os.pathsep) and "<B_VENV>" not in m["child_path"]["A"]


def test_manifest_has_no_b_stack_without_b(tmp_path):
    rc, out = run_dry(tmp_path, conds="A,C", limit=1)
    assert rc == 0 and manifest(out)["b_stack"] is None


def test_manifest_and_plan_carry_the_digest_of_a_valid_stack(tmp_path, monkeypatch):
    info = {"path": "/x/venv-B", "bin": "/x/venv-B/bin", "python": "3.14.7", "packages": {"numpy": "1"},
            "digest": "ab" * 32}
    monkeypatch.setattr(b_stack, "validate", lambda venv, *a, **k: info)
    rc, out = run_dry(tmp_path, limit=1)
    assert rc == 0
    assert manifest(out)["b_stack"] == {**info, "path": "<B_VENV>", "bin": "<B_VENV>/bin"}
    plan = json.loads((out / "plan.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert plan["pins"]["b_stack_sha256"] == "ab" * 32
    runs = [json.loads(ln) for ln in (out / "plan.jsonl").read_text(encoding="utf-8").splitlines()[1:]]
    assert {r["condition"]: r.get("b_stack_sha256") for r in runs} == {"A": None, "B": "ab" * 32, "C": None}
    assert manifest(out)["pin_drift"] == []


def test_pre_init_system_event_is_skipped_and_killed_before_init_costs_nothing(tmp_path):
    """A system/ui_invalidate event before init is skipped, and a run killed before init costs nothing."""
    import json as _json

    from tsbench import conditions as _c
    pre = {"type": "system", "subtype": "ui_invalidate", "event": "ui.render"}
    init = fixture("init_A.json")
    res = {"type": "result", "subtype": "success", "is_error": False, "result": "x", "total_cost_usd": 0.01}
    script = tmp_path / "emit.py"
    script.write_text("import sys,json\nfor l in sys.argv[1:]: print(l, flush=True)\n", encoding="utf-8")
    ok = runner.execute([sys.executable, str(script), _json.dumps(pre), _json.dumps(init), _json.dumps(res)],
                        "p", {"PATH": "/usr/bin:/bin"}, tmp_path / "ok.jsonl", _c.get("A"), init["model"],
                        timeout_s=30)
    assert ok.mismatches == [] and ok.init_seen and ok.result is not None
    bad = runner.execute([sys.executable, str(script), _json.dumps(pre), _json.dumps(res)],
                         "p", {"PATH": "/usr/bin:/bin"}, tmp_path / "bad.jsonl", _c.get("A"), init["model"],
                         timeout_s=30)
    assert bad.init_aborted and not bad.init_seen
    assert sandbox.evaluate_transcript([pre, fixture("init_B.json")], "claude-haiku-5-5")[
        "init_mismatches"] == []


def test_child_env_blocks_mcp_startup():
    """The child environment blocks MCP startup, so the init event of C reports the server as connected."""
    env = runner.build_child_env({"PATH": "/usr/bin", "TSMCP_ANTHROPIC_API_KEY": "x"}, home="/h",
                                 config_dir="/h/.claude", tmpdir="/t", repo=runner.REPO_ROOT, dry_run=False,
                                 gateway=False)
    assert env["MCP_CONNECTION_NONBLOCKING"] == "0" and int(env["MCP_CONNECT_TIMEOUT_MS"]) >= 10000


def test_mpl_cache_dir_outside_repo_and_passed_to_child(tmp_path):
    d = runner.mpl_cache_dir({"HOME": str(tmp_path)}, runner.REPO_ROOT)
    assert d == str(tmp_path / ".cache" / "tsbench" / "matplotlib")
    with pytest.raises(runner.Abort):
        runner.mpl_cache_dir({"TSBENCH_MPLCONFIGDIR": str(runner.REPO_ROOT / "x")}, runner.REPO_ROOT)
    env = runner.build_child_env({"PATH": "/usr/bin", "TSMCP_ANTHROPIC_API_KEY": "x"}, home="/h",
                                 config_dir="/h/.claude", tmpdir="/t", repo=runner.REPO_ROOT, dry_run=False,
                                 gateway=False,
                                 mpl_config_dir=d)
    assert env["MPLCONFIGDIR"] == d


def test_b_preapproves_bash_and_probe_requires_heredoc():
    """B pre-approves Bash, so that the permission parser in -p mode does not deny heredoc scripts."""
    from tsbench import conditions as _c
    flags = _c.get("B").flags(settings_path="/s.json")
    assert flags[flags.index("--allowedTools") + 1] == "Bash" and flags[flags.index("--tools") + 1] == "Bash"
    assert "--allowedTools" not in _c.get("A").flags()
    assert any("PROBE_HEREDOC" in line and "<<'EOF'" in line for line in sandbox.probe_script_lines())
    assert not sandbox.evaluate_transcript(probe_events(GOOD.replace("PROBE_HEREDOC rc=0", "PROBE_HEREDOC rc=1")),
                                           HAIKU)["passed"]


# ------------------------------------------------------------------ --json-schema / StructuredOutput
def test_schema_flag_is_last_and_compact_in_every_condition():
    assert " " not in conditions.ANSWER_SCHEMAS["fit"].compact
    assert json.loads(conditions.ANSWER_SCHEMAS["fit"].compact) == json.loads(
        (REPO_ROOT / "src/tsbench/data/schemas/answer.schema.json").read_text(encoding="utf-8"))
    for k in "ABC":
        assert argv_for(k)[-2:] == ["--json-schema", conditions.ANSWER_SCHEMAS["fit"].compact]
        assert "StructuredOutput" not in " ".join(conditions.get(k).flags(settings_path="s", mcp_config_path="m")[:-2])


@pytest.mark.parametrize("key", "ABC")
def test_check_init_requires_structured_output(key):
    cond = conditions.get(key)
    assert conditions.check_init(cond, fixture(f"init_{key}.json"), HAIKU) == []
    probs = conditions.check_init(cond, fixture(f"init_{key}.json", structured=False), HAIKU)
    assert len(probs) == 1 and conditions.STRUCTURED_TOOL in probs[0]


def test_check_init_structured_output_does_not_excuse_other_tools():
    b = fixture("init_B.json")
    b["tools"] = ["Bash", "Read", conditions.STRUCTURED_TOOL]
    assert conditions.check_init(conditions.get("B"), b, HAIKU)
    a = fixture("init_A.json")
    a["tools"] = ["Bash", conditions.STRUCTURED_TOOL]
    assert conditions.check_init(conditions.get("A"), a, HAIKU)


def test_compute_flags_ignores_structured_output():
    so = {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": "s", "name": "StructuredOutput", "input": {}}]}}
    flags, _ = runner.compute_flags("B", [so], {"permission_denials": []})
    assert "b_no_tool_use" in flags
    flags, _ = runner.compute_flags("C", [so], {"permission_denials": []})
    assert "c_no_mcp_call" in flags


def test_fake_structured_mode_and_unparseable_case():
    task = load("pilot")[0]
    args = ["-p", "--model", HAIKU, "--tools", "", "--json-schema", conditions.ANSWER_SCHEMAS["fit"].compact]
    seen_ok = seen_bad = False
    for seed in range(60):
        ev = run_fake(args, task["prompt"], FAKE_SEED=str(seed))
        assert ev[0]["tools"] == ["StructuredOutput"]
        res = ev[-1]
        uses = [b for e in ev if e["type"] == "assistant" for b in e["message"]["content"] if b["type"] == "tool_use"]
        if "structured_output" in res:
            seen_ok = True
            assert [u["name"] for u in uses] == ["StructuredOutput"] and uses[0]["input"] == res["structured_output"]
            assert json.loads(res["result"]) == res["structured_output"]
        else:
            seen_bad = True
            assert uses == [] and "{" not in res["result"]
    assert seen_ok and seen_bad
    plain = run_fake(["-p", "--model", HAIKU, "--tools", ""], task["prompt"])
    assert plain[0]["tools"] == [] and "structured_output" not in plain[-1]


def test_resume_reruns_rate_limited_results_even_with_estimated_cost(tmp_path):
    """A 429 result with an estimated cost is not done: --resume runs it again."""
    import json as _json
    t = tmp_path / "x-k1.jsonl"
    t.write_text(_json.dumps({"type": "result", "is_error": True, "api_error_status": 429, "total_cost_usd": 0.27,
                              "result": "API Error: Request rejected (429) · API rate limit exceeded"}) + "\n",
                                  encoding="utf-8")
    assert runner.transcript_status(t)[0] is False
    assert runner.is_rate_limited({"api_error_status": 429}) and not runner.is_rate_limited({"result": "wrong Dq"})


# ------------------------------------------------------------------ HTTP 429: backoff and retry of the same run
def rate_limit_result(**kw):
    return {"type": "result", "subtype": "success", "is_error": True, "api_error_status": 429,
            "result": "API Error: Request rejected (429) \u00b7 API rate limit exceeded", "total_cost_usd": 0,
            "permission_denials": [], **kw}


@pytest.fixture(autouse=True)
def waits(monkeypatch):
    """The backoff sleep is replaced in every test of this file: none of them waits."""
    got = []
    monkeypatch.setattr(runner, "sleep", got.append)
    return got


def test_429_is_retried_with_backoff_and_every_attempt_is_kept(tmp_path, monkeypatch, waits):
    monkeypatch.setenv("FAKE_429_FIRST", "2")
    monkeypatch.setenv("FAKE_429_STATE", str(tmp_path / "count"))
    rc, out = run_dry(tmp_path, models=(HAIKU,), conds="C", k=1, limit=1)
    run_dir = out / HAIKU / "C" / "medium"
    tid = load("pilot")[0]["id"]
    assert rc == 0 and len(waits) == 2
    assert 60 <= waits[0] <= 60 * 1.25 and 120 <= waits[1] <= 120 * 1.25  # 60, 120 s plus jitter
    last = [json.loads(ln) for ln in (run_dir / f"{tid}-k1.jsonl").read_text(encoding="utf-8").splitlines()][-1]
    assert last["type"] == "result" and not last["is_error"]  # the final transcript is the successful attempt
    for n in (1, 2):
        att = [json.loads(ln)
            for ln in (run_dir / f"{tid}-k1.attempt{n}.jsonl").read_text(encoding="utf-8").splitlines()][-1]
        assert att["is_error"] and att["api_error_status"] == 429
    assert not (run_dir / f"{tid}-k1.attempt3.jsonl").exists()
    meta = json.loads((run_dir / f"{tid}-k1.meta.json").read_text(encoding="utf-8"))
    assert [r["wait_s"] for r in meta["retries"]] == waits and {r["status"] for r in meta["retries"]} == {"429"}
    assert all(r["at"] for r in meta["retries"]) and meta["flags"] == []
    assert manifest(out)["counts"]["done"] == 1


def test_429_backoff_schedule_and_limit(tmp_path, monkeypatch, waits):
    assert runner.RETRY_429_BACKOFF_S == (60, 120, 240, 480)
    assert [runner.backoff_s(n, rng=lambda: 0.0) for n in (1, 2, 3, 4)] == [60, 120, 240, 480]
    assert runner.backoff_s(1, rng=lambda: 1.0) == 75.0
    monkeypatch.setenv("FAKE_429_FIRST", "99")
    monkeypatch.setenv("FAKE_429_STATE", str(tmp_path / "count"))
    rc, out = run_dry(tmp_path, models=(HAIKU,), conds="A", k=1, limit=1)
    assert len(waits) == 4  # at most four retries, then the 429 stays as the result
    tid = load("pilot")[0]["id"]
    meta = json.loads((out / HAIKU / "A" / "medium" / f"{tid}-k1.meta.json").read_text(encoding="utf-8"))
    assert meta["flags"] == ["result_is_error", "rate_limited"] and len(meta["retries"]) == 4
    assert len(list((out / HAIKU / "A" / "medium").glob("*.attempt*.jsonl"))) == 4


def test_429_retries_env_override_and_zero_disables(tmp_path, monkeypatch, waits):
    monkeypatch.setenv("FAKE_429_FIRST", "99")
    monkeypatch.setenv("FAKE_429_STATE", str(tmp_path / "count"))
    monkeypatch.setenv("TSBENCH_429_MAX_RETRIES", "1")
    run_dry(tmp_path, models=(HAIKU,), conds="A", k=1, limit=1)
    assert len(waits) == 1
    waits.clear()
    (tmp_path / "count").unlink()
    monkeypatch.setenv("TSBENCH_429_MAX_RETRIES", "0")
    _, out = run_dry(tmp_path, models=(HAIKU,), conds="A", k=1, limit=1, out=tmp_path / "r0")
    assert waits == [] and not list(out.glob("*/*/*/*.attempt*.jsonl"))
    assert runner.max_429_retries({}) == 4 and runner.max_429_retries({"TSBENCH_429_MAX_RETRIES": "x"}) == 4


def test_rate_limited_result_gets_only_the_rate_limited_flag():
    res = rate_limit_result()
    assert runner.is_rate_limited(res)
    for cond in "ABC":
        assert runner.compute_flags(cond, [], res) == (["rate_limited"], {})
    # an ordinary error keeps the usual flags
    other = {"type": "result", "is_error": True, "result": "API Error: 500 boom", "api_error_status": 500,
             "permission_denials": []}
    assert runner.compute_flags("B", [], other)[0] == ["b_no_tool_use"]
    assert runner.compute_flags("C", [], other)[0] == ["c_no_mcp_call"]


# ------------------------------------------------------------------ text-only gateway models: no image tools
TEXT_ONLY = ["deepseek-v4-flash-0731", "meta-llama-3.1-8b-instruct", "qwen3-coder-next",
             "qwen3-30b-a3b-instruct-2507", "qwen3.8-27b"]
IMAGE_TOOLS = ["mcp__tanabesugano__ts_plot_png", "mcp__tanabesugano__ts_emit_png"]


def test_text_only_gateway_models_in_C_disallow_the_image_tools():
    assert sorted(conditions.TEXT_ONLY_GATEWAY_MODELS) == sorted(TEXT_ONLY)
    for model in TEXT_ONLY:
        assert conditions.disallowed_tools("C", model, True) == IMAGE_TOOLS
        argv = runner.build_argv(["claude"], conditions.get("C"), model, "medium", mcp_config_path="/m",
                                 disallowed_tools=conditions.disallowed_tools("C", model, True))
        i = argv.index("--disallowedTools")
        assert argv[i + 1:i + 3] == IMAGE_TOOLS and argv[i + 3] == "--json-schema"
    # not for A or B, not without the gateway, not for a model that takes images
    assert conditions.disallowed_tools("A", "qwen3.8-27b", True) == []
    assert conditions.disallowed_tools("B", "qwen3.8-27b", True) == []
    assert conditions.disallowed_tools("C", "qwen3.8-27b", False) == []
    assert conditions.disallowed_tools("C", "gemma-4-31b-it", True) == []
    assert "--disallowedTools" not in build_argv_default("C")


def test_check_init_accepts_the_tool_list_without_the_image_tools():
    c = conditions.get("C")
    full = fixture("init_C.json")
    assert set(IMAGE_TOOLS) <= set(full["tools"])
    trimmed = {**full, "tools": [t for t in full["tools"] if t not in IMAGE_TOOLS]}
    assert conditions.check_init(c, trimmed, trimmed["model"], IMAGE_TOOLS) == []
    assert conditions.check_init(c, trimmed, trimmed["model"]) == []  # nothing else is required of the list
    problems = conditions.check_init(c, full, full["model"], IMAGE_TOOLS)  # the block did not take effect
    assert problems and "disallowed" in problems[0]


def test_plan_and_runner_carry_the_blocked_tools(tmp_path):
    from tsbench import plan as P
    spec = {"split": "pilot", "models": ["qwen3.8-27b", "gemma-4-31b-it"], "conditions": ["A", "C"],
            "efforts": ["medium"], "k": 1, "budget_usd": 5.0, "gateway": True}
    plan = P.build_plan(load("pilot")[:1], spec, created_utc="2026-10-25T00:00:00+00:00")
    by = {(r["model"], r["condition"]): r for r in plan.runs}
    blocked = by[("qwen3.8-27b", "C")]
    assert blocked["disallowed_tools"] == IMAGE_TOOLS and "--disallowedTools" in blocked["argv_template"]
    assert by[("gemma-4-31b-it", "C")]["disallowed_tools"] == [] == by[("qwen3.8-27b", "A")]["disallowed_tools"]
    assert P.validate_lines(P.serialize(plan.header, plan.runs).splitlines()) == []
    path = tmp_path / "plan.jsonl"
    P.write_plan(plan, path, markdown=False)
    rc = runner.main(["--plan", str(path), "--out", str(tmp_path / "o"), "--dry-run"])
    assert rc == 0
    meta = json.loads(next((tmp_path / "o").glob("qwen3.8-27b/C/*/*.meta.json")).read_text(encoding="utf-8"))
    assert meta["disallowed_tools"] == IMAGE_TOOLS and "--disallowedTools" in meta["argv"]
    ev = json.loads(next((tmp_path / "o").glob("qwen3.8-27b/C/*/*.jsonl")).read_text(encoding="utf-8").splitlines()[1])
    assert not set(IMAGE_TOOLS) & set(ev["tools"]) and not meta["init_mismatches"]


# ------------------------------------------------------------------ sandbox probe, placeholders and host label
def test_new_markers_have_the_right_polarity():
    assert {"KEYENV", "PATHS"} <= set(sandbox.MUST_BE_ZERO)
    assert {"TSBIN", "HOMECACHE", "HOMESECRETS", "LOCALHOST", "APIHOST", "DNS"} <= set(sandbox.MUST_FAIL)
    assert not set(sandbox.MUST_BE_ZERO) & set(sandbox.MUST_FAIL)


@pytest.mark.parametrize("old,new,reason", [
    ("PROBE_KEYENV rc=0", "PROBE_KEYENV rc=1", "KEYENV"),          # a credential is visible in B's Bash
    ("PROBE_KEYENV rc=0", "", "KEYENV missing"),
    ("PROBE_PATHS rc=0", "PROBE_PATHS rc=1", "PATHS"),            # the path markers would be vacuous
    ("PROBE_DNS rc=1", "PROBE_DNS rc=0", "DNS"),
    ("PROBE_LOCALHOST rc=7", "PROBE_LOCALHOST rc=0", "LOCALHOST"),
    ("PROBE_TSBIN rc=1\nPROBE_TSBIN rc=1", "PROBE_TSBIN rc=1\nPROBE_TSBIN rc=0", "TSBIN"),  # one of two leaks
    ("PROBE_HOMESECRETS rc=1\nPROBE_HOMESECRETS rc=1", "PROBE_HOMESECRETS rc=0\nPROBE_HOMESECRETS rc=1", "HOMESECRETS"),
    ("PROBE_APIHOST rc=56\nPROBE_APIHOST rc=56", "PROBE_APIHOST rc=0\nPROBE_APIHOST rc=56", "APIHOST"),
    ("PROBE_HOMECACHE rc=1\nPROBE_HOMECACHE rc=1", "", "HOMECACHE missing"),
])
def test_probe_verdict_on_the_new_markers(old, new, reason):
    assert old in GOOD
    ev = sandbox.evaluate_transcript(probe_events(GOOD.replace(old, new)), HAIKU)
    assert not ev["passed"] and any(r.startswith(reason) for r in ev["reasons"]), ev["reasons"]


def test_keyenv_reason_names_the_key_variable_check():
    ev = sandbox.evaluate_transcript(probe_events(GOOD.replace("PROBE_KEYENV rc=0", "PROBE_KEYENV rc=1")), HAIKU)
    assert any("a model credential is visible in B's Bash environment" in r for r in ev["reasons"])


def test_probe_script_one_command_per_path_and_no_values_printed():
    hp = {"HOMECACHE": [".cache/uv", ".local"], "HOMESECRETS": [".ssh", ".zsh_history"]}
    lines = sandbox.probe_script_lines(hp)
    assert sum("PROBE_TSBIN" in ln for ln in lines) == 2 and sum("PROBE_HOMECACHE" in ln for ln in lines) == 2
    assert sum("PROBE_HOMESECRETS" in ln for ln in lines) == 2 and sum("PROBE_APIHOST" in ln for ln in lines) == 2
    assert any('ls "$TSPROBE_RH"/.ssh' in ln for ln in lines)
    assert any('cat "$TSPROBE_RH"/.zsh_history' in ln for ln in lines)
    keyline = next(ln for ln in lines if "PROBE_KEYENV" in ln)
    assert all("${" + v + "-}" in keyline for v in sandbox.KEY_VARS)
    assert "echo $" not in keyline
    for ln in lines:  # every forbidden action is silenced; only the marker lines print
        if any(f"PROBE_{n} " in ln for n in sandbox.MUST_FAIL):
            assert "> /dev/null 2>&1" in ln, ln
    # nothing of a kind on the host: the marker still appears (and fails), and the record says so
    none = sandbox.probe_script_lines({"HOMECACHE": [], "HOMESECRETS": []})
    assert "false; echo PROBE_HOMESECRETS rc=$?" in none
    assert sandbox.probe_script_sha256(hp) != sandbox.probe_script_sha256({"HOMECACHE": [], "HOMESECRETS": []})


def test_existing_home_paths_checks_without_reading(tmp_path):
    (tmp_path / ".ssh").mkdir()
    (tmp_path / ".zsh_history").write_text("secret", encoding="utf-8")
    (tmp_path / ".local").mkdir()
    assert sandbox.existing_home_paths(tmp_path) == {"HOMECACHE": [".local"], "HOMESECRETS": [".ssh", ".zsh_history"]}


def test_reusable_probe_needs_the_same_script_and_auth(tmp_path):
    rec = {"passed": True, "fake": False, "claude_version": "v", "settings_sha256": "s", "b_stack_sha256": None,
           "probe_script_sha256": sandbox.probe_script_sha256(), "auth_mode": "direct"}
    (tmp_path / sandbox.PROBE_FILENAME).write_text(json.dumps(rec), encoding="utf-8")
    assert sandbox.load_reusable_probe(tmp_path, "v", "s") is not None
    assert sandbox.load_reusable_probe(tmp_path, "v", "s", auth="direct") is not None
    assert sandbox.load_reusable_probe(tmp_path, "v", "s", auth="gateway") is None
    (tmp_path / sandbox.PROBE_FILENAME).write_text(json.dumps({**rec, "probe_script_sha256": "old"}), encoding="utf-8")
    assert sandbox.load_reusable_probe(tmp_path, "v", "s") is None  # a record of another probe script is never reused


def test_plan_pins_the_probe_script_template():
    from tsbench import plan as P
    pins = P.live_pins(None)
    assert pins["sandbox_probe_script_sha256"] == sandbox.probe_script_template_sha256()
    assert len(pins["sandbox_probe_script_sha256"]) == 64


def test_host_is_a_label_or_a_salted_hash_never_the_hostname():
    import socket
    assert runner.host_label({"TSBENCH_HOST_LABEL": "build-host-7"}, "pid") == ("build-host-7", "label")
    h, src = runner.host_label({}, "pid-1")
    assert len(h) == 12 and src.startswith("sha256") and socket.gethostname() not in h
    assert runner.host_label({}, "pid-2")[0] != h  # per-study salt
    assert runner.host_label({"TSBENCH_HOST_SALT": "s"}, "pid-1") == runner.host_label({"TSBENCH_HOST_SALT": "s"}, "x")


def test_redact_replaces_longest_prefix_first():
    pairs = runner.placeholder_pairs([("/u/op", "<HOME>"), ("/u/op/repo", "<REPO>"), ("/u/op/repo/out", "<OUT>")])
    assert runner.redact({"a": ["/u/op/repo/out/x", "/u/op/repo/y", "/u/op/z", 3]}, pairs) == {
        "a": ["<OUT>/x", "<REPO>/y", "<HOME>/z", 3]}


def test_dry_run_records_hold_no_home_path_and_no_hostname(tmp_path, monkeypatch):
    """MANIFEST, sidecars and plan of a dry run carry placeholders, not host paths; `host` is hashed."""
    import importlib.util
    import socket
    spec = importlib.util.spec_from_file_location("check_e2e", REPO_ROOT / "tools" / "ci" / "check_e2e.py")
    ce = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ce)
    monkeypatch.delenv("TSBENCH_HOST_LABEL", raising=False)
    rc, out = run_dry(tmp_path, limit=1)
    assert rc == 0
    files = ce.record_files(out)
    assert {f.name for f in files} >= {"MANIFEST.json", "plan.jsonl"}
    assert any(f.name.endswith(".meta.json") for f in files)
    assert ce.identity_findings(files) == []
    text = "\n".join(f.read_text(encoding="utf-8") for f in files)
    assert not re.search(r"/(Users|home)/[^/]+/", text) and socket.gethostname() not in text
    assert str(REPO_ROOT) not in text and str(tmp_path) not in text
    m = manifest(out)
    assert m["host_source"].startswith("sha256") and len(m["host"]) == 12
    assert m["args"]["out"].startswith("<TMP>/") and m["args"]["dry_run"] is True
    assert m["child_path"]["A"].split(os.pathsep)[:2] == ["/usr/bin", "/bin"]
    assert m["child_path"]["B"].startswith("<B_VENV>/bin")
    meta = json.loads(next(out.glob("*/B/medium/*.meta.json")).read_text(encoding="utf-8"))
    assert meta["argv"][0] == "<PYTHON>" and "<CFG>/sandbox-settings.json" in meta["argv"]
    system_prompt = meta["argv"][meta["argv"].index("--system-prompt-file") + 1]
    assert re.fullmatch(r"<OUT>/system-prompts/system-prompt-[0-9a-f]{16}\.txt", system_prompt)  # the plan's text
    assert (out / system_prompt[len("<OUT>/"):]).read_text(encoding="utf-8").startswith(
        pathlib.Path(runner.NEUTRAL_PROMPT).read_text(encoding="utf-8").splitlines()[0])
    assert "USER" in m["env_var_names"]  # set, but to the constant run user


def test_report_reads_the_system_prompt_through_the_repo_placeholder():
    from tsbench.report import views
    meta = {"argv": ["<CLAUDE>", "--system-prompt-file", "<REPO>/src/tsbench/data/prompts/neutral.txt"]}
    assert views.system_prompt_from_argv(meta) == pathlib.Path(runner.NEUTRAL_PROMPT).read_text(encoding="utf-8")


def test_report_reads_the_system_prompt_through_the_out_placeholder(tmp_path):
    from tsbench.report import views
    d = tmp_path / "runs" / "system-prompts"
    d.mkdir(parents=True)
    (d / "system-prompt-0123456789abcdef.txt").write_text("THE SYSTEM PROMPT\n", encoding="utf-8")
    meta = {"argv": ["<CLAUDE>", "--system-prompt-file", "<OUT>/system-prompts/system-prompt-0123456789abcdef.txt"]}
    assert views.system_prompt_from_argv(meta, tmp_path / "runs") == "THE SYSTEM PROMPT\n"
    assert views.system_prompt_from_argv(meta, tmp_path / "elsewhere") is None
    assert views.system_prompt_from_argv(meta) is None


def test_a_view_without_plan_records_shows_the_system_prompt_from_the_run_folder(tmp_path):
    """A sealed plan has no run records (report/views.py renders from the sidecar): the prompt must still be there."""
    from tsbench.report import views
    rc, out = run_dry(tmp_path, limit=1)
    assert rc == 0
    r = json.loads((out / "plan.jsonl").read_text(encoding="utf-8").splitlines()[1])
    (out / "plan.jsonl").unlink()
    views.render_dir(out)
    page = (out / "views" / r["run_id"]).with_suffix(".html").read_text(encoding="utf-8")
    assert r["system_prompt_text"].splitlines()[0] in page


def test_fake_probe_record_holds_no_home_path(tmp_path):
    out = tmp_path / "probe"
    assert sandbox_probe.main(["--probe", "--fake", "--out", str(out)]) == 0
    text = (out / sandbox.PROBE_FILENAME).read_text(encoding="utf-8")
    assert not re.search(r"/(Users|home)/[^/]+/", text) and str(tmp_path) not in text
    transcript = (out / "_sandbox_probe" / "transcript.jsonl").read_text(encoding="utf-8")
    assert str(REPO_ROOT) not in transcript and str(pathlib.Path("~").expanduser()) + "/" not in transcript


# ------------------------------------------------------------------ an API error in the probe is not a sandbox failure
def test_probe_retries_a_429_and_passes_on_retry_one(tmp_path, monkeypatch, waits):
    monkeypatch.setenv("FAKE_429_FIRST", "1")
    monkeypatch.setenv("FAKE_429_STATE", str(tmp_path / "count"))
    s = fake_session()
    try:
        rec = sandbox_probe.run_probe(s, tmp_path / "out")
    finally:
        s.close()
    assert rec["passed"] is True and rec["not_evaluable"] is None and rec["reasons"] == []
    assert len(waits) == 1 and rec["retries"] == 1
    assert (tmp_path / "out" / "_sandbox_probe" / "transcript.attempt1.jsonl").exists()


def test_probe_with_only_api_errors_is_not_evaluable(tmp_path, monkeypatch, waits):
    monkeypatch.setenv("FAKE_429_FIRST", "99")
    monkeypatch.setenv("FAKE_429_STATE", str(tmp_path / "count"))
    monkeypatch.setenv("TSBENCH_429_MAX_RETRIES", "2")
    s = fake_session()
    try:
        rec = sandbox_probe.run_probe(s, tmp_path / "out")
    finally:
        s.close()
    assert rec["passed"] is None and rec["not_evaluable"] == "api_error" and len(waits) == 2
    assert any("API" in r for r in rec["reasons"])
    saved = json.loads((tmp_path / "out" / "sandbox_probe.json").read_text(encoding="utf-8"))
    assert saved["passed"] is None and saved["not_evaluable"] == "api_error"
    # a not evaluable record is never reused
    assert sandbox.load_reusable_probe(tmp_path / "out", s.claude_version, s.settings_sha256,
                                       (s.b_stack or {}).get("digest"), auth=sandbox.auth_mode(s)) is None


def test_probe_leak_still_fails_when_the_result_is_an_api_error(tmp_path, monkeypatch, waits):
    monkeypatch.setenv("FAKE_429_FIRST", "99")
    monkeypatch.setenv("FAKE_429_STATE", str(tmp_path / "count"))
    monkeypatch.setenv("TSBENCH_429_MAX_RETRIES", "0")
    monkeypatch.setenv("FAKE_PROBE_LEAK", "NET")
    s = fake_session()
    try:
        rec = sandbox_probe.run_probe(s, tmp_path / "out")
    finally:
        s.close()
    assert rec["passed"] is False and rec["not_evaluable"] is None and any("NET" in r for r in rec["reasons"])


def test_probe_key_leak_still_fails_when_the_result_is_an_api_error(tmp_path, monkeypatch, waits):
    """KEYENV must be 0: rc 1 means the key was visible inside the sandbox. An API error after it does not hide that."""
    monkeypatch.setenv("FAKE_429_FIRST", "99")
    monkeypatch.setenv("FAKE_429_STATE", str(tmp_path / "count"))
    monkeypatch.setenv("TSBENCH_429_MAX_RETRIES", "0")
    monkeypatch.setenv("FAKE_PROBE_LEAK", "KEYENV")
    s = fake_session()
    try:
        rec = sandbox_probe.run_probe(s, tmp_path / "out")
    finally:
        s.close()
    assert rec["passed"] is False and rec["not_evaluable"] is None and any("KEYENV" in r for r in rec["reasons"])


def test_probe_api_error_reason_holds_no_key(tmp_path, monkeypatch):
    key = "sk-probe-secret-123456"  # gitleaks:allow (made-up test key)
    result = {"type": "result", "is_error": True, "api_error_status": 429,
              "result": "API Error: Request rejected (429) for key " + key + " " + "z" * 2000}
    text = sandbox_probe.api_error_reason(result, {"ANTHROPIC_API_KEY": key})
    assert key not in text and "[REDACTED]" in text and "API Error" in text and len(text) < 700


def test_probe_api_error_is_not_a_sandbox_failure_and_b_waits_for_a_real_probe(tmp_path, real_mode_fake, monkeypatch,
                                                                                waits):
    monkeypatch.setenv("FAKE_429_FIRST", "99")
    monkeypatch.setenv("FAKE_429_STATE", str(tmp_path / "count"))
    monkeypatch.setenv("TSBENCH_429_MAX_RETRIES", "0")
    runner.main(real_args(tmp_path))
    out = tmp_path / "runs"
    m = manifest(out)
    assert m["sandbox"]["method"] == "not evaluable" and m["sandbox"]["probe"]["passed"] is None
    assert m["counts"]["not_run_sandbox"] == 0 and m["counts"]["not_run_probe_not_evaluable"] == 1
    assert not list(out.glob("*/B/*/*.jsonl"))  # B never runs in a sandbox that nobody has checked
    # the next invocation probes again (a not evaluable record is never reused) and then runs B
    monkeypatch.setenv("FAKE_429_FIRST", "0")
    runner.main(real_args(tmp_path, extra=("--resume",)))
    m = manifest(out)
    assert m["sandbox"]["method"] == "builtin" and m["counts"]["not_run_probe_not_evaluable"] == 0
    assert list((out / HAIKU / "B" / "medium").glob("*.jsonl"))


def test_probe_leak_still_blocks_b(tmp_path, real_mode_fake, monkeypatch, waits):
    monkeypatch.setenv("FAKE_PROBE_LEAK", "NET")
    monkeypatch.setenv("FAKE_429_FIRST", "99")
    monkeypatch.setenv("FAKE_429_STATE", str(tmp_path / "count"))
    monkeypatch.setenv("TSBENCH_429_MAX_RETRIES", "0")
    runner.main(real_args(tmp_path))
    out = tmp_path / "runs"
    m = manifest(out)
    assert m["sandbox"]["method"] == "skipped" and m["counts"]["not_run_sandbox"] == 1
    assert not list(out.glob("*/B/*/*.jsonl"))


def test_method_info_not_evaluable_is_not_skipped_and_not_builtin():
    info = sandbox.method_info({"passed": None, "not_evaluable": "api_error",
                                "reasons": ["API Error: Request rejected (429)"]}, False)
    assert info["method"] == "not evaluable" and "API Error" in info["reason"] and info["container"] is None
    assert info["probe"]["passed"] is None


def test_probe_cli_exits_75_and_says_not_evaluable(tmp_path, capsys, monkeypatch, waits):
    monkeypatch.setenv("FAKE_429_FIRST", "99")
    monkeypatch.setenv("FAKE_429_STATE", str(tmp_path / "count"))
    monkeypatch.setenv("TSBENCH_429_MAX_RETRIES", "0")
    assert sandbox_probe.main(["--probe", "--fake", "--out", str(tmp_path / "p")]) == 75
    printed = capsys.readouterr().out
    assert "NOT EVALUABLE" in printed and "FAIL" not in printed and "PASS" not in printed


def test_probe_module_has_one_main_guard():
    src = pathlib.Path(sandbox_probe.__file__).read_text(encoding="utf-8")
    assert src.count('if __name__ == "__main__":') == 1


# ------------------------------------------------------------------ redact before the cut
def test_stderr_key_split_by_the_cut_leaves_no_fragment(tmp_path):
    key = "sk-abcdefghij1234"  # gitleaks:allow (made-up test key)
    # the last STDERR_TAIL_CHARS characters start 4 characters into the key: 13 characters of it would survive
    n_after = runner.STDERR_TAIL_CHARS + 4 - len(key)
    code = (f"import sys,json; sys.stderr.write('x'*100 + {key!r} + 'y'*{n_after}); sys.stderr.flush(); "
            "print(json.dumps({'type':'system','subtype':'init','tools':[],'mcp_servers':[],'model':'m'}))")
    env = make_env({"PATH": "/usr/bin", "ANTHROPIC_API_KEY": key})
    out = runner.execute([sys.executable, "-c", code], "", env, tmp_path / "t.jsonl", conditions.get("A"), "m",
                         timeout_s=30)
    assert len(out.stderr_tail) <= runner.STDERR_TAIL_CHARS
    assert not any(key[i:i + 8] in out.stderr_tail for i in range(len(key) - 7))
    assert "[REDACTED]" in out.stderr_tail


# ------------------------------------------------------------------ a missing probe target is "not tested"
def test_missing_probe_targets_are_named(tmp_path):
    assert sandbox.missing_probe_targets(tmp_path) == ("VENV", "READ")
    (tmp_path / ".venv" / "bin").mkdir(parents=True)
    (tmp_path / ".venv" / "bin" / "python").write_text("", encoding="utf-8")
    assert sandbox.missing_probe_targets(tmp_path) == ("READ",)
    target = tmp_path / sandbox.PROBE_TARGETS["READ"]
    target.parent.mkdir(parents=True)
    target.write_text("", encoding="utf-8")
    assert sandbox.missing_probe_targets(tmp_path) == ()


def test_probe_script_without_a_venv_has_no_venv_marker():
    full = sandbox.probe_script_lines(missing_targets=())
    short = sandbox.probe_script_lines(missing_targets=("VENV",))
    assert any("PROBE_VENV" in line for line in full) and not any("PROBE_VENV" in line for line in short)
    assert sum("PROBE_READ" in line for line in short) == 1
    assert sandbox.probe_script_sha256(missing_targets=()) != sandbox.probe_script_sha256(missing_targets=("VENV",))
    # the pinned template is the full script
    assert sandbox.probe_script_template_sha256() == sandbox.probe_script_sha256(
        {"HOMECACHE": list(sandbox.HOMECACHE_PATHS), "HOMESECRETS": list(sandbox.HOMESECRETS_PATHS)}, ())


def test_untested_venv_is_never_counted_as_passed():
    events = probe_events(GOOD.replace("PROBE_VENV rc=126\n", ""))
    ev = sandbox.evaluate_transcript(events, HAIKU, not_tested=("VENV",))
    assert not ev["passed"] and any("VENV not tested" in r for r in ev["reasons"])
    assert not any("VENV missing" in r for r in ev["reasons"])
    # even a marker that happens to be there does not count as a pass
    ev = sandbox.evaluate_transcript(probe_events(), HAIKU, not_tested=("READ",))
    assert not ev["passed"] and any("READ not tested" in r for r in ev["reasons"])


def test_run_probe_for_a_repo_without_a_venv_is_not_a_pass(tmp_path, monkeypatch):
    monkeypatch.setattr(sandbox_probe, "missing_probe_targets", lambda repo: ("VENV",))
    s = fake_session()
    try:
        rec = sandbox_probe.run_probe(s, tmp_path)
    finally:
        s.close()
    assert rec["passed"] is False and rec["targets_not_tested"] == ["VENV"] and "VENV" not in rec["markers"]
    assert any("VENV not tested" in r for r in rec["reasons"])
    assert rec["probe_script_sha256"] == sandbox.probe_script_sha256(rec["home_paths_tested"], ("VENV",))


def test_every_probe_target_exists_in_the_repository():
    """The probe reads the task file by a fixed path. If a rename moves it, "denied" would be vacuous: it is absent."""
    from tsbench.tasks import TASKS_PATH

    assert (REPO_ROOT / sandbox.PROBE_TARGETS["READ"]).resolve() == pathlib.Path(TASKS_PATH).resolve()
    assert (REPO_ROOT / sandbox.PROBE_TARGETS["READ"]).is_file()
    assert set(sandbox.PROBE_TARGETS) == {"VENV", "READ"}  # a new target needs its own existence check here
    # .venv is not tracked: only the shape of its path is fixed
    assert sandbox.PROBE_TARGETS["VENV"].startswith(".venv/")


# ------------------------------------------------------------------ pure helpers: exact values
def test_is_api_error_boundaries_and_keys():
    err = {"is_error": True}
    assert runner.is_api_error({**err, "api_error_status": 400}) is True
    assert runner.is_api_error({**err, "api_error_status": 399}) is False
    assert runner.is_api_error({**err, "api_error_status": 503}) is True  # not a rate limit, still an API error
    assert runner.is_api_error({**err, "api_error_status": "503"}) is False  # a status is an int
    assert runner.is_api_error({**err, "result": "API Error: x"}) is True
    assert runner.is_api_error({**err, "result": "an API Error: x"}) is False
    assert runner.is_api_error({**err}) is False
    assert runner.is_api_error({"is_error": False, "api_error_status": 500}) is False
    assert runner.is_api_error(["not", "a", "dict"]) is False  # ty: ignore[invalid-argument-type]


def test_is_rate_limited_each_signal_alone():
    assert runner.is_rate_limited({"api_error_status": 429}) is True
    assert runner.is_rate_limited({"api_error_status": "429"}) is True
    assert runner.is_rate_limited({"result": "Rate Limit reached"}) is True  # case-insensitive
    assert runner.is_rate_limited({"result": "rate limit"}) is True
    assert runner.is_rate_limited({"result": "Request failed (429)"}) is True
    assert runner.is_rate_limited({"result": "ok", "api_error_status": 500}) is False
    assert runner.is_rate_limited({}) is False


def test_quota_scope_names_the_cap():
    base = {"is_error": True, "api_error_status": 429}
    assert runner.quota_scope({**base, "result": "User daily request rate limit exhausted (7 of 7)."}) == "daily"
    assert runner.quota_scope({**base, "result": "Monthly rate limit exhausted"}) == "monthly"
    assert runner.quota_scope({**base, "result": "rate limit exhausted"}) == "unknown"
    assert runner.quota_scope({**base, "result": "Rate limit exceeded: user daily request limit reached (7 of 7). "
                                                  "Retry after 86400 seconds."}) == "daily"
    assert runner.quota_scope({**base, "result": "rate limit, try later"}) is None
    assert runner.quota_scope({**base, "result": "Rate limit reached for requests, please slow down"}) is None
    assert runner.quota_scope({**base, "is_error": False, "result": "rate limit exhausted"}) is None
    assert runner.quota_scope({"is_error": True, "result": "rate limit exhausted daily"}) == "daily"
    assert runner.quota_scope(None) is None
    assert runner.quota_scope({"is_error": True, "result": "disk exhausted"}) is None


def test_last_event_reads_invalid_bytes_and_returns_only_objects(tmp_path):
    p = tmp_path / "t.jsonl"
    p.write_bytes(b'{"a": 1}\n{"type": "result", "result": "caf\xe9"}\n\n  \n')
    assert runner.last_event(p) == {"type": "result", "result": "caf\ufffd"}
    p.write_bytes(b"")
    assert runner.last_event(p) is None
    p.write_text("   \n\n", encoding="utf-8")
    assert runner.last_event(p) is None
    p.write_text('{"a": 1}\n[1, 2]\n', encoding="utf-8")
    assert runner.last_event(p) is None
    p.write_text('{"a": 1}\n"text"\n', encoding="utf-8")
    assert runner.last_event(p) is None
    p.write_text('{"a": 1}\nnot json\n', encoding="utf-8")
    assert runner.last_event(p) is None
    with pytest.raises(OSError):
        runner.last_event(tmp_path / "missing.jsonl")


@pytest.mark.parametrize("char", ["\u2028", "\u2029", "\u0085"])
def test_a_result_line_with_a_unicode_line_separator_is_still_done(tmp_path, char):
    """str.splitlines() also breaks at U+2028, U+2029 and U+0085, which stream-json leaves unescaped inside strings.
    The transcript is split at the newline only, as the scorer reads it."""
    p = tmp_path / "x.jsonl"
    result = {"type": "result", "is_error": False, "total_cost_usd": 0.5, "result": f"before{char}after"}
    p.write_text('{"type": "assistant"}\n' + json.dumps(result, ensure_ascii=False) + "\n", encoding="utf-8")
    assert runner.last_event(p) == result
    assert runner.transcript_status(p) == (True, 0.5)


def test_last_event_reads_only_the_tail_and_agrees_with_the_full_read(tmp_path, monkeypatch):
    def full_read(path):
        lines = [ln for ln in path.read_text(encoding="utf-8", errors="replace").split("\n") if ln.strip()]
        try:
            ev = json.loads(lines[-1]) if lines else None
        except ValueError:
            return None
        return ev if isinstance(ev, dict) else None

    monkeypatch.setattr(runner, "LAST_EVENT_WINDOW", 16)
    first = json.dumps({"type": "assistant", "text": "x" * 500})
    cases = {
        "short last line": first + "\n" + json.dumps({"type": "result", "n": 1}) + "\n",
        "long last line": first + "\n" + json.dumps({"type": "result", "text": "caf\u00e9 " * 300}, ensure_ascii=False),
        "blank tail": first + "\n" + json.dumps({"type": "result", "n": 2}) + "\n\n  \r\n \n",
        "single long line": json.dumps({"type": "result", "text": "\u00e9" * 200}, ensure_ascii=False),
        "last line not json": first + "\n" + "n" * 100,
        "last line a list": first + "\n[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]\n",
        "empty": "",
        "blank only": "\n \n\n",
    }
    expected = {name: full_read(_write(tmp_path / f"{i}.jsonl", txt)) for i, (name, txt) in enumerate(cases.items())}
    monkeypatch.setattr(pathlib.Path, "read_text", lambda *a, **k: pytest.fail("the whole transcript was read"))
    for i, name in enumerate(cases):
        assert runner.last_event(tmp_path / f"{i}.jsonl") == expected[name], name
    assert expected["long last line"]["type"] == "result" and expected["last line not json"] is None


def _write(path: pathlib.Path, text: str) -> pathlib.Path:
    path.write_bytes(text.encode("utf-8"))
    return path


def test_transcript_status_of_an_api_error_is_never_paid(tmp_path):
    p = tmp_path / "x.jsonl"
    p.write_text(_result_line(api_error_status=500, total_cost_usd=0.4, result="boom"), encoding="utf-8")
    assert runner.transcript_status(p) == (False, 0.0)
    p.write_text(json.dumps({"type": "assistant"}) + "\n", encoding="utf-8")
    assert runner.transcript_status(p) == (False, 0.0)
    p.write_text(json.dumps({"type": "result", "is_error": False}) + "\n", encoding="utf-8")
    assert runner.transcript_status(p) == (True, 0.0)


def test_utcnow_is_utc_seconds():
    stamp = runner.utcnow()
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\+00:00", stamp)


def test_backoff_is_exponential_with_jitter_rounded_to_one_decimal():
    assert runner.backoff_s(1, rng=lambda: 0.0) == 60.0
    assert runner.backoff_s(2, rng=lambda: 0.0) == 120.0
    assert runner.backoff_s(4, rng=lambda: 0.0) == 480.0
    assert runner.backoff_s(9, rng=lambda: 0.0) == 480.0  # the last value repeats
    assert runner.backoff_s(1, rng=lambda: 1.0) == 75.0
    assert runner.backoff_s(1, rng=lambda: 0.123) == 61.8  # one decimal, not an integer
    assert runner.backoff_s(3, rng=lambda: 0.5) == 270.0
    assert 60.0 <= runner.backoff_s(1) <= 75.0


@pytest.mark.parametrize("fn, env_name, default", [(runner.max_429_retries, runner.RETRY_429_ENV, 4),
                                                   (runner.max_429_in_a_row, runner.STOP_429_ENV, 3)])
def test_429_limits_parse_the_environment(fn, env_name, default):
    assert fn({}) == default and fn({env_name: ""}) == default and fn({env_name: "  "}) == default
    assert fn({env_name: "7"}) == 7 and fn({env_name: " 2 "}) == 2 and fn({env_name: "0"}) == 0
    assert fn({env_name: "-3"}) == 0 and fn({env_name: "many"}) == default


def test_429_limits_read_os_environ_when_no_env_is_given(monkeypatch):
    monkeypatch.setenv(runner.RETRY_429_ENV, "9")
    monkeypatch.setenv(runner.STOP_429_ENV, "8")
    assert runner.max_429_retries() == 9 and runner.max_429_in_a_row() == 8


def test_redact_keys_replaces_both_credentials_from_eight_characters():
    env = {"ANTHROPIC_API_KEY": "k" * 8, "ANTHROPIC_AUTH_TOKEN": "t" * 9}
    assert runner._redact_keys("a " + "k" * 8 + " b " + "t" * 9 + " c", env) == "a [REDACTED] b [REDACTED] c"
    assert runner._redact_keys("short " + "s" * 7, {"ANTHROPIC_API_KEY": "s" * 7}) == "short " + "s" * 7
    assert runner._redact_keys("x", {"ANTHROPIC_API_KEY": ""}) == "x"
    assert runner._redact_keys("tok" * 5, {"ANTHROPIC_AUTH_TOKEN": "tok" * 3}) == "[REDACTED]" + "tok" * 2


def test_sealed_refusal_and_plan_error_messages(capsys):
    class P:
        header = {"sealed": True}
        plan_id = "abc123"

    with pytest.raises(runner.Abort) as e:
        runner._sealed_refusal(P())
    assert e.value.code == 2
    assert capsys.readouterr().err == ("runner: this is a sealed plan (header only, no run records); run the clear "
                                       "plan whose plan_id is abc123\n")
    P.header = {"sealed": False}
    assert runner._sealed_refusal(P()) is None

    def boom():
        raise runner.plan_mod.PlanError("bad plan line 3")

    with pytest.raises(runner.Abort) as e:
        runner._as_plan_error(boom)
    assert capsys.readouterr().err == "runner: bad plan line 3\n"
    assert isinstance(e.value.__cause__, runner.plan_mod.PlanError)
    assert runner._as_plan_error(lambda a, b=0: a + b, 1, b=2) == 3


def test_existing_plan_id_reads_the_first_line_of_either_file(tmp_path):
    assert runner._existing_plan_id(tmp_path) is None
    (tmp_path / runner.plan_mod.SEALED_NAME).write_text('{"plan_id": "sealed1"}\n{"plan_id": "other"}\n',
                                                         encoding="utf-8")
    assert runner._existing_plan_id(tmp_path) == "sealed1"  # a missing plan.jsonl is skipped, not the end
    (tmp_path / runner.plan_mod.PLAN_NAME).write_text('{"plan_id": "clear1"}\n{"plan_id": "other"}\n', encoding="utf-8")
    assert runner._existing_plan_id(tmp_path) == "clear1"
    (tmp_path / runner.plan_mod.PLAN_NAME).write_text("not json\n", encoding="utf-8")
    assert runner._existing_plan_id(tmp_path) == "sealed1"
    (tmp_path / runner.plan_mod.PLAN_NAME).write_text("", encoding="utf-8")
    assert runner._existing_plan_id(tmp_path) == "sealed1"


def test_the_flags_form_pins_the_digest_of_the_given_venv_and_refuses_one_inside_the_repo(
        tmp_path, monkeypatch, capsys):
    calls = {}

    def b_venv_dir(env, venv, *a):
        calls["dir"] = (env, venv)
        return "D"

    monkeypatch.setattr(runner.b_stack, "b_venv_dir", b_venv_dir)
    monkeypatch.setattr(runner.b_stack, "digest_if_present", lambda d: f"digest-of-{d}")
    assert runner.plan_mod.b_stack_digest(["A", "B"], "pilot", "/some/venv") == "digest-of-D"
    assert calls["dir"] == (None, "/some/venv")

    def refuse(env, venv, *a):
        raise runner.b_stack.BStackError("inside the repo")

    monkeypatch.setattr(runner.b_stack, "b_venv_dir", refuse)
    err = stderr_of_abort(capsys, runner.main, flags_argv(tmp_path, **{"--conditions": "A,B"}) + ["--b-venv", "/x"])
    assert err == "runner: B stack: inside the repo\n"


def test_retire_earlier_attempt_reasons_and_costs(tmp_path):
    f = tmp_path / "r-k1.jsonl"
    assert runner.retire_earlier_attempt(f) is None
    cases = [("", "no_result", 0.0),
             (json.dumps({"type": "assistant"}) + "\n", "no_result", 0.0),
             (_result_line(api_error_status=429, total_cost_usd=0.5, result="rate limit"), "rate_limited", 0.5),
             (_result_line(api_error_status=500, total_cost_usd=0.25, result="x"), "api_error", 0.25),
             (_result_line(total_cost_usd=0, result="x"), "error_zero_cost", 0.0),
             (_result_line(total_cost_usd=0.75, result="x"), "error_zero_cost", 0.75),
             (json.dumps({"type": "result", "is_error": False, "total_cost_usd": 1.5}) + "\n", "result", 1.5),
             (json.dumps({"type": "result", "is_error": False}) + "\n", "result", 0.0)]
    for text, reason, cost in cases:
        f.write_text(text, encoding="utf-8")
        got = runner.retire_earlier_attempt(f)
        assert got == {"attempt": 1, "reason": reason, "cost_usd": cost}, text
        assert not f.exists() and runner.attempt_path(f, 1).exists()
        runner.attempt_path(f, 1).unlink()


def test_sandbox_probe_needs_a_mode_and_runs_as_a_script(monkeypatch, capsys):
    import runpy

    with pytest.raises(SystemExit) as e:
        sandbox_probe.main([])
    assert e.value.code == 2 and "give --probe or --settings-only" in capsys.readouterr().err
    monkeypatch.setattr(sys, "argv", ["sandbox_probe", "--settings-only"])
    with pytest.warns(RuntimeWarning):
        with pytest.raises(SystemExit) as e:
            runpy.run_module("tsbench.run.sandbox_probe", run_name="__main__")
    assert e.value.code == 0 and json.loads(capsys.readouterr().out)


# ------------------------------------------------------------------ startup guards: the exact refusals
def stderr_of_abort(capsys, fn, *a, **kw):
    with pytest.raises(SystemExit) as e:
        fn(*a, **kw)
    assert e.value.code == 2
    return capsys.readouterr().err


def flags_argv(tmp_path, **over):
    base = {"--split": "pilot", "--models": HAIKU, "--conditions": "A", "--effort": "medium", "--k": "1",
            "--budget-usd": "1", "--out": str(tmp_path / "runs"), "--limit": "1"}
    base.update(over)
    out = []
    for key, val in base.items():
        if val is not None:
            out += [key, val]
    return out + ["--dry-run"]


def test_parse_args_names_the_missing_flags_and_refuses_a_plan_with_selection_flags(capsys):
    err = stderr_of_abort(capsys, runner.parse_args, ["--out", "x"])
    assert "the following arguments are required: --split, --models, --conditions, --effort, --k, --budget-usd" in err
    err = stderr_of_abort(capsys, runner.parse_args, ["--split", "pilot", "--models", "m", "--out", "x"])
    assert "required: --conditions, --effort, --k, --budget-usd" in err
    err = stderr_of_abort(capsys, runner.parse_args,
                          ["--plan", "p.jsonl", "--split", "pilot", "--k", "2", "--out", "x"])
    assert "--plan replaces --split, --k: the plan is the only source of what runs" in err
    ok = runner.parse_args(["--plan", "p.jsonl", "--out", "x", "--budget-usd", "3"])
    assert ok.plan == "p.jsonl" and ok.budget_usd == 3.0 and ok.k is None


@pytest.mark.parametrize("over, message", [
    ({"--models": " , "}, "--models must be a non-empty list without duplicates"),
    ({"--models": f"{HAIKU},{HAIKU}"}, "--models must be a non-empty list without duplicates"),
    ({"--models": "haiku"}, "'haiku' is an alias; give the full model id (e.g. claude-haiku-5-5)"),
    ({"--conditions": ","}, "--conditions must be a non-empty list without duplicates"),
    ({"--conditions": "a,A"}, "--conditions must be a non-empty list without duplicates"),
    ({"--conditions": "D"}, "unknown condition 'D'; choose from ['A', 'B', 'C']"),
    ({"--k": "0"}, "--k must be >= 1"),
    ({"--limit": "0"}, "--limit must be >= 1"),
    ({"--budget-usd": "0"}, "--budget-usd must be > 0"),
])
def test_main_refuses_bad_flags_with_the_exact_message(tmp_path, capsys, over, message):
    assert stderr_of_abort(capsys, runner.main, flags_argv(tmp_path, **over)) == f"runner: {message}\n"
    assert not (tmp_path / "runs").exists()


def test_the_flags_form_refuses_a_confirmatory_b_run_without_the_b_stack_before_loading_tasks(
        tmp_path, capsys, monkeypatch):
    """`plan build` refuses it; the flags form builds the same plan and refuses it, too."""
    import tsbench.tasks as tasks_mod

    def boom(split):
        raise AssertionError("tasks were loaded")

    monkeypatch.setattr(tasks_mod, "load", boom)
    monkeypatch.setattr(b_stack, "digest_if_present", lambda venv, *a, **k: None)
    argv = flags_argv(tmp_path, **{"--split": "confirmatory", "--conditions": "A,B"})
    err = stderr_of_abort(capsys, runner.main, [*argv, "--i-have-preregistered", "10.1234/x"])
    assert err == "runner: condition B needs the fixed B stack: run `tsbench env b-stack` first\n"
    assert not (tmp_path / "runs").exists()


def test_main_refuses_a_per_call_cap_of_zero(tmp_path, capsys):
    argv = flags_argv(tmp_path) + ["--per-call-usd", "0"]
    assert stderr_of_abort(capsys, runner.main, argv) == "runner: --per-call-usd must be > 0\n"


def test_main_refuses_a_missing_or_wrong_tanabesugano(tmp_path, capsys, monkeypatch):
    def not_installed(name):
        raise runner.importlib.metadata.PackageNotFoundError(name)

    monkeypatch.setattr(runner.importlib.metadata, "version", not_installed)
    assert stderr_of_abort(capsys, runner.main, flags_argv(tmp_path)) == "runner: tanabesugano is not installed\n"
    monkeypatch.setattr(runner.importlib.metadata, "version", lambda name: "1.9.0")
    assert stderr_of_abort(capsys, runner.main, flags_argv(tmp_path)) == (
        "runner: tanabesugano==2.0.0 required, found 1.9.0\n")


def test_main_refuses_a_split_without_tasks(tmp_path, capsys, monkeypatch):
    import tsbench.tasks as tasks_mod

    monkeypatch.setattr(tasks_mod, "load", lambda split: [])
    assert stderr_of_abort(capsys, runner.main, flags_argv(tmp_path)) == "runner: no tasks in split 'pilot'\n"


def test_a_keyboard_interrupt_ends_the_run_set_with_130_and_an_unfinished_manifest(tmp_path, monkeypatch, capsys):
    def interrupt(*a, **k):
        raise KeyboardInterrupt

    monkeypatch.setattr(runner, "execute_with_retries", interrupt)
    monkeypatch.setattr(runner, "execute", interrupt)
    rc, out = run_dry(tmp_path, conds="A", limit=1)
    m = manifest(out)
    assert rc == 130 and m["interrupted"] is True and m["finished"] is False
    assert "interrupted; manifest written" in capsys.readouterr().err


HANGING_RUN = """
import pathlib, sys
from tsbench.run import runner

tmp = pathlib.Path(sys.argv[1])


def hang(argv, prompt, env, transcript, cond, model, **kw):
    script = f"echo $$ > {tmp}/pid; sleep 60"
    return runner.execute(["bash", "-c", script], prompt, env, transcript, cond, model, timeout_s=120)


runner.execute_with_retries = hang
sys.exit(runner.main(["--split", "pilot", "--models", "claude-haiku-5-5", "--conditions", "A", "--effort", "medium",
                      "--k", "1", "--budget-usd", "1", "--out", str(tmp / "runs"), "--dry-run", "--limit", "1"]))
"""


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


@pytest.mark.parametrize("sig", [signal.SIGTERM, signal.SIGHUP])
def test_a_termination_signal_ends_the_run_set_like_ctrl_c_and_leaves_no_orphan(tmp_path, sig):
    """`kill`, `timeout` and a dropped ssh session send SIGTERM or SIGHUP: the runner ends the run set like Ctrl-C,
    runs its finally blocks and stops the claude child (its own session)."""
    import time

    (tmp_path / "hang.py").write_text(HANGING_RUN, encoding="utf-8")
    proc = subprocess.Popen([sys.executable, str(tmp_path / "hang.py"), str(tmp_path)], cwd=str(REPO_ROOT),
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
    child = None
    try:
        for _ in range(600):  # up to 60 s for the import, the session and the child to come up
            if (tmp_path / "pid").exists() and (tmp_path / "pid").read_text(encoding="utf-8").strip():
                child = int((tmp_path / "pid").read_text(encoding="utf-8"))
                break
            assert proc.poll() is None, proc.communicate()
            time.sleep(0.1)
        assert child is not None
        proc.send_signal(sig)
        _, err = proc.communicate(timeout=60)
        for _ in range(100):
            if not _alive(child):
                break
            time.sleep(0.1)
        assert proc.returncode == 130 and "interrupted; manifest written" in err, err
        assert not _alive(child)
        m = manifest(tmp_path / "runs")
        assert m["interrupted"] is True and m["finished"] is False
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.communicate()
        if child is not None and _alive(child):
            os.kill(child, signal.SIGKILL)


def test_termination_as_interrupt_restores_the_handlers_and_is_a_no_op_outside_the_main_thread():
    import threading

    before = {s: signal.getsignal(s) for s in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)}
    with runner.termination_as_interrupt():
        assert signal.getsignal(signal.SIGTERM) is signal.default_int_handler
        assert signal.getsignal(signal.SIGHUP) is signal.default_int_handler
        assert signal.getsignal(signal.SIGINT) is before[signal.SIGINT]
    assert {s: signal.getsignal(s) for s in before} == before
    seen = []

    def in_thread():
        with runner.termination_as_interrupt():  # signal.signal works in the main thread only
            seen.append("ran")

    t = threading.Thread(target=in_thread)
    t.start()
    t.join()
    assert seen == ["ran"] and {s: signal.getsignal(s) for s in before} == before


def test_termination_as_interrupt_leaves_a_signal_alone_that_is_ignored_on_purpose(monkeypatch):
    """`nohup` sets SIGHUP to ignore: a run under it must survive the hang-up."""
    old = signal.signal(signal.SIGHUP, signal.SIG_IGN)
    try:
        with runner.termination_as_interrupt():
            assert signal.getsignal(signal.SIGHUP) == signal.SIG_IGN
            assert signal.getsignal(signal.SIGTERM) is signal.default_int_handler
        assert signal.getsignal(signal.SIGHUP) == signal.SIG_IGN
    finally:
        signal.signal(signal.SIGHUP, old)


def test_the_module_runs_as_a_script(monkeypatch, capsys):
    import runpy

    monkeypatch.setattr(sys, "argv", ["runner", "--help"])
    with pytest.warns(RuntimeWarning):
        with pytest.raises(SystemExit) as e:
            runpy.run_module("tsbench.run.runner", run_name="__main__")
    assert e.value.code == 0 and "usage: tsbench run" in capsys.readouterr().out


# ------------------------------------------------------------------ a plan given with --plan
@pytest.fixture
def plan_file(tmp_path):
    """A one-run clear plan built in memory, written to a file; `mutate(plan)` changes it after load."""
    from tsbench import plan as plan_mod

    spec = {"split": "pilot", "models": [HAIKU], "conditions": ["A"], "efforts": ["medium"], "k": 1,
            "budget_usd": 1.0, "limit": 1, "gateway": False}
    plan = plan_mod.build_plan(load("pilot")[:1], spec, pins=plan_mod.live_pins(None))
    path = tmp_path / "plan.jsonl"
    plan_mod.write_plan(plan, path, markdown=False)
    return path, plan


def run_plan(tmp_path, path, *extra, out=None):
    return runner.main(["--plan", str(path), "--out", str(out or tmp_path / "runs"), "--dry-run", *extra])


def test_a_plan_runs_and_a_sealed_plan_is_refused(tmp_path, plan_file, capsys):
    path, plan = plan_file
    assert run_plan(tmp_path, path) == 0
    assert manifest(tmp_path / "runs")["plan_id"] == plan.plan_id
    sealed = tmp_path / "sealed.json"
    runner.plan_mod.write_sealed(plan, sealed)
    err = stderr_of_abort(capsys, run_plan, tmp_path, sealed, out=tmp_path / "other")
    assert err == ("runner: this is a sealed plan (header only, no run records); run the clear plan whose plan_id is "
                   f"{plan.plan_id}\n")


def test_the_confirmatory_guard_follows_the_run_records_not_the_header(tmp_path, plan_file, capsys, monkeypatch):
    """A plan whose run records are confirmatory but whose header says pilot still needs the preregistration DOI, and
    it is sealed like a confirmatory run set."""
    path, plan = plan_file
    plan.runs[0]["split"] = "confirmatory"
    monkeypatch.setattr(runner.plan_mod, "load_plan", lambda p: plan)
    err = stderr_of_abort(capsys, run_plan, tmp_path, path)
    assert "needs --i-have-preregistered" in err and not (tmp_path / "runs").exists()


@pytest.mark.parametrize("change, message", [
    (lambda r: r.update({"tools_expected": {"tools": ["x"]}}),
     "tools_expected in the plan disagrees with conditions.py"),
    (lambda r: r.update({"model": "haiku"}), "'haiku' is an alias; give the full model id (e.g. claude-haiku-5-5)"),
])
def test_a_plan_that_disagrees_with_the_code_is_refused(tmp_path, plan_file, capsys, monkeypatch, change, message):
    path, plan = plan_file
    monkeypatch.setattr(runner.plan_mod, "load_plan", lambda p: plan)
    change(plan.runs[0])
    err = stderr_of_abort(capsys, run_plan, tmp_path, path)
    run_id = plan.runs[0]["run_id"]
    assert err == (f"runner: {run_id}: {message}\n" if "tools_expected" in message else f"runner: {message}\n")


def test_a_plan_whose_argv_template_differs_from_the_live_argv_is_refused(tmp_path, plan_file, capsys, monkeypatch):
    """The plan describes the argv of every run; a build_argv that gained a flag after the plan was written must not
    run under that plan."""
    from tsbench.conditions import argv as argv_mod

    path, plan = plan_file
    monkeypatch.setattr(runner.plan_mod, "load_plan", lambda p: plan)
    real = argv_mod.build_argv
    monkeypatch.setattr(argv_mod, "build_argv", lambda *a, **kw: [*real(*a, **kw), "--new-flag"])
    err = stderr_of_abort(capsys, run_plan, tmp_path, path)
    assert err == f"runner: {plan.runs[0]['run_id']}: argv_template in the plan disagrees with build_argv\n"
    assert not (tmp_path / "runs").exists()


def test_a_plan_whose_expected_flags_differ_from_the_code_is_refused(tmp_path, plan_file, capsys, monkeypatch):
    path, plan = plan_file
    monkeypatch.setattr(runner.plan_mod, "load_plan", lambda p: plan)
    plan.runs[0]["expected_flags"] = ["c_no_mcp_call"]
    err = stderr_of_abort(capsys, run_plan, tmp_path, path)
    assert err == f"runner: {plan.runs[0]['run_id']}: expected_flags in the plan disagrees with conditions.py\n"


def test_a_plan_with_an_unknown_or_changed_answer_schema_is_refused(tmp_path, plan_file, capsys, monkeypatch):
    path, plan = plan_file
    monkeypatch.setattr(runner.plan_mod, "load_plan", lambda p: plan)
    rid = plan.runs[0]["run_id"]
    plan.runs[0]["answer_schema_sha256"] = "0" * 64
    assert stderr_of_abort(capsys, run_plan, tmp_path, path) == (
        f"runner: {rid}: answer schema 'fit' in the plan disagrees with the schema file\n")
    plan.runs[0]["answer_schema"] = "nope"
    assert stderr_of_abort(capsys, run_plan, tmp_path, path).startswith(
        f"runner: {rid}: unknown answer schema 'nope'; choose from ['batch', 'curve'")


def test_resume_of_a_plan_refuses_another_plan_id(tmp_path, plan_file, capsys):
    from tsbench import plan as plan_mod

    path, plan = plan_file
    out = tmp_path / "runs"
    assert run_plan(tmp_path, path, out=out) == 0
    other = plan_mod.build_plan(load("pilot")[:2], {**plan.header["spec"], "limit": 2}, pins=plan_mod.live_pins(None))
    other_path = tmp_path / "other.jsonl"
    plan_mod.write_plan(other, other_path, markdown=False)
    assert other.plan_id != plan.plan_id
    expect = f"runner: --resume: {out} holds plan_id {plan.plan_id}, this invocation has {other.plan_id}\n"
    assert stderr_of_abort(capsys, run_plan, tmp_path, other_path, "--resume", out=out) == expect
    # without the clear plan file the manifest still names the plan
    (out / "plan.jsonl").unlink()
    assert stderr_of_abort(capsys, run_plan, tmp_path, other_path, "--resume", out=out) == expect
    # a manifest that cannot be read does not block the resume
    (out / "MANIFEST.json").write_text("not json", encoding="utf-8")
    assert run_plan(tmp_path, other_path, "--resume", out=out) == 0


# ------------------------------------------------------------------ execute: odd children
INIT_JSON = ("json.dumps({'type':'system','subtype':'init','tools':['StructuredOutput'],'mcp_servers':[],"
             "'model':'m'})")


def execute_code(tmp_path, code, **kw):
    return runner.execute([sys.executable, "-c", code], "", {"PATH": "/usr/bin"}, tmp_path / "t.jsonl",
                          conditions.get("A"), "m", timeout_s=kw.pop("timeout_s", 30), **kw)


def test_execute_without_any_init_event_is_aborted(tmp_path):
    out = execute_code(tmp_path, "import json; print(json.dumps({'type': 'system', 'subtype': 'ui_invalidate'}))")
    assert out.mismatches == ["no init event"] and out.init_aborted is True and out.init_seen is False
    assert out.init is None and out.result is None and len(out.events) == 1
    out = execute_code(tmp_path, "pass")
    assert out.mismatches == ["no init event"] and out.events == []


def test_execute_aborts_when_the_first_line_is_not_a_json_object(tmp_path):
    out = execute_code(tmp_path, "print('hello')")
    assert out.mismatches == ["first non-system line is not a JSON object"] and out.init_aborted is True
    assert out.init is None and out.init_seen is False and out.events == []


def test_execute_skips_blank_and_non_json_lines_after_init_and_reads_the_result(tmp_path):
    code = (f"import json; print(); print({INIT_JSON}); print('not json'); print(); print('trailing junk'); "
            "print(json.dumps({'type':'result','total_cost_usd':0.5}))")
    out = execute_code(tmp_path, code)
    assert out.mismatches == [] and out.init_seen is True and out.init["model"] == "m"
    assert [e["type"] for e in out.events] == ["system", "result"]  # the junk is not an event
    assert out.result == {"type": "result", "total_cost_usd": 0.5} and out.cost_usd == 0.5
    lines = (tmp_path / "t.jsonl").read_text(encoding="utf-8").splitlines()
    assert lines[0] == "" and lines[2:5] == ["not json", "", "trailing junk"]  # the transcript is the raw stdout
    assert lines[-1] == '{"type": "result", "total_cost_usd": 0.5}'


def test_execute_survives_a_child_that_closes_stdin_at_once(tmp_path):
    code = f"import os, json; os.close(0); print({INIT_JSON})"
    out = runner.execute([sys.executable, "-c", code], "x" * 5_000_000, {"PATH": "/usr/bin"}, tmp_path / "t.jsonl",
                         conditions.get("A"), "m", timeout_s=30)
    assert out.mismatches == [] and out.init_seen is True


def test_execute_never_loses_a_run_to_a_failing_harvest(tmp_path, monkeypatch):
    def boom(cwd, dest):
        raise RuntimeError("harvest failed")

    monkeypatch.setattr(runner, "harvest_artifacts", boom)
    out = execute_code(tmp_path, f"import json; print({INIT_JSON})")
    assert out.artifacts == [] and out.mismatches == []


def test_outcome_without_a_result_has_no_cost():
    out = runner.Outcome(events=[], init=None, mismatches=[], result=None, exit_code=0, wall_s=0.0, stderr_tail="",
                         timed_out=False, init_aborted=False)
    assert out.cost_usd is None
    out.result = {"type": "result"}
    assert out.cost_usd == 0.0


def test_kill_group_falls_back_to_killing_the_process():
    calls = []

    class Proc:
        pid = 2 ** 22 + 12345  # no such process group

        def kill(self):
            calls.append("kill")

    runner._kill_group(Proc())  # ty: ignore[invalid-argument-type]
    assert calls == ["kill"]

    class Stubborn(Proc):
        def kill(self):
            raise OSError("gone")

    runner._kill_group(Stubborn())  # ty: ignore[invalid-argument-type]  # neither call raises


def test_sleep_waits_for_the_given_time(monkeypatch):
    monkeypatch.undo()  # this file replaces runner.sleep in every test; here the real one is wanted
    seen = []
    monkeypatch.setattr(runner.time, "sleep", seen.append)
    runner.sleep(2.5)
    assert seen == [2.5]


# ------------------------------------------------------------------ Session.create in real mode (no network)
@pytest.fixture
def real_session_parts(tmp_path, monkeypatch):
    """A fake `claude` script, a fake tanabesugano-mcp and a private TMPDIR: everything a real-mode Session needs."""
    bin_dir = tmp_path / "cbin"
    bin_dir.mkdir()
    claude = bin_dir / "claude"
    claude.write_text("#!/bin/sh\necho '2.1.99 (Claude Code)'\n", encoding="utf-8")
    claude.chmod(0o755)
    mcp = tmp_path / "mcpbin" / "tanabesugano-mcp"
    mcp.parent.mkdir()
    mcp.write_text("", encoding="utf-8")
    tmp_root = tmp_path / "tmp"
    tmp_root.mkdir()
    monkeypatch.setattr(runner.tempfile, "tempdir", str(tmp_root))
    monkeypatch.setattr(runner.shutil, "which", lambda name, path=None: str(claude))
    monkeypatch.setattr(runner, "find_mcp_command", lambda repo: str(mcp))
    warmed = []
    monkeypatch.setattr(runner, "warm_mpl_cache", lambda d, py: warmed.append((d, str(py))))
    parent = {"HOME": str(tmp_path / "home"), "PATH": str(bin_dir), "TSMCP_ANTHROPIC_API_KEY": "sk-abcdefgh",
              "TSBENCH_MPLCONFIGDIR": str(tmp_path / "mpl")}
    (tmp_path / "home").mkdir()
    return SimpleNamespace(claude=claude, mcp=mcp, tmp_root=tmp_root, warmed=warmed, parent=parent, tmp_path=tmp_path)



def create_real(parts, **kw):
    return runner.Session.create(dry_run=False, gateway=False, parent_env=parts.parent, need_b=False, **kw)


def test_real_session_runs_the_found_claude_and_records_its_version(real_session_parts):
    p = real_session_parts
    s = create_real(p)
    try:
        assert s.claude_argv == [str(p.claude)] and s.real_claude == str(p.claude)
        assert s.claude_version == "2.1.99 (Claude Code)" and s.real_claude_version == "2.1.99 (Claude Code)"
        assert s.dry_run is False and s.gateway is False and s.b_stack is None
        assert s.env["ANTHROPIC_API_KEY"] == "sk-abcdefgh" and s.env["MPLCONFIGDIR"] == str(p.tmp_path / "mpl")
        assert s.runtime_dirs == [str(p.claude.parent.resolve())]
        assert pathlib.Path(s.home).parent == p.tmp_root and pathlib.Path(s.home).name.startswith("tsbench-home-")
        assert pathlib.Path(s.cfg_dir).name.startswith("tsbench-cfg-")
        assert (pathlib.Path(s.home) / ".claude").is_dir()
        ts = json.loads(s.ts_json_path.read_text(encoding="utf-8"))
        assert ts["mcpServers"]["tanabesugano"]["command"] == str(p.mcp)
        assert s.settings_path.read_text(encoding="utf-8") and s.settings_sha256 == runner.plan_mod.sha256_text(
            s.settings_path.read_text(encoding="utf-8"))
        assert p.warmed == [(str(p.tmp_path / "mpl"), str(p.mcp.parent / "python"))]
    finally:
        s.close()
    assert not pathlib.Path(s.home).exists() and not pathlib.Path(s.cfg_dir).exists()


def test_real_session_with_a_claude_that_will_not_run_says_unknown(real_session_parts):
    p = real_session_parts
    p.claude.chmod(0o644)
    s = create_real(p)
    try:
        assert s.real_claude_version is None and s.claude_version == "unknown" and s.claude_argv == [str(p.claude)]
    finally:
        s.close()


def test_real_session_warms_the_cache_of_the_b_stack_too(real_session_parts, monkeypatch):
    p = real_session_parts
    info = {"path": str(p.tmp_path / "vB"), "bin": str(p.tmp_path / "vB" / "bin"), "python": "3", "packages": {},
            "digest": "d"}
    monkeypatch.setattr(runner.b_stack, "ensure_b_stack", lambda venv: info)
    s = runner.Session.create(dry_run=False, gateway=False, parent_env=p.parent, b_venv=p.tmp_path / "vB")
    try:
        assert s.b_stack == info and s.b_venv == str(p.tmp_path / "vB")
        assert p.warmed == [(str(p.tmp_path / "mpl"), str(p.mcp.parent / "python")),
                            (str(p.tmp_path / "mpl"), str(p.tmp_path / "vB" / "bin" / "python"))]
    finally:
        s.close()


def test_real_session_can_validate_the_b_stack_without_creating_it(real_session_parts, monkeypatch):
    p = real_session_parts
    info = {"path": str(p.tmp_path / "vB"), "bin": str(p.tmp_path / "vB" / "bin"), "python": "3", "packages": {},
            "digest": "d"}
    seen = []
    monkeypatch.setattr(runner.b_stack, "ensure_b_stack", lambda venv, **kw: seen.append(kw) or info)
    kw = {"b_venv": p.tmp_path / "vB", "parent_env": p.parent}
    runner.Session.create(dry_run=False, gateway=False, create_b=False, **kw).close()
    runner.Session.create(dry_run=False, gateway=False, **kw).close()
    assert seen == [{"create": False}, {}]  # the default still creates the stack


@pytest.mark.parametrize("setup, message", [
    ("no_claude", "`claude` not found on PATH"),
    ("no_mcp", "tanabesugano-mcp not found in <repo>/.venv/bin or next to the Python interpreter"),
    ("offender", "the child PATH would reach /x/tanabesugano-mcp; condition B must not"),
    ("tmp_in_repo", None),
    ("tmp_in_home", None),
    ("bad_settings", "sandbox settings: broken settings"),
    ("no_key", "required environment variable not set: TSMCP_ANTHROPIC_API_KEY (or ANTHROPIC_API_KEY)"),
])
def test_real_session_refusals_leave_no_temp_dirs(real_session_parts, monkeypatch, capsys, setup, message):
    p = real_session_parts
    if setup == "no_claude":
        monkeypatch.setattr(runner.shutil, "which", lambda name, path=None: None)
    elif setup == "no_mcp":
        monkeypatch.setattr(runner, "find_mcp_command", lambda repo: None)
    elif setup == "offender":
        monkeypatch.setattr(runner, "path_offenders", lambda path: ["/x/tanabesugano-mcp"])
    elif setup == "tmp_in_repo":
        monkeypatch.setattr(runner.tempfile, "tempdir", str(runner.REPO_ROOT / "build-tmp"))
        message = f"TMPDIR {runner.REPO_ROOT / 'build-tmp'} lies inside the repo; point TMPDIR elsewhere"
    elif setup == "tmp_in_home":
        inside = p.tmp_path / "home" / "tmp"
        monkeypatch.setattr(runner.tempfile, "tempdir", str(inside))
        message = (f"TMPDIR {inside} lies inside the home directory, which the sandbox denies; point TMPDIR "
                   "elsewhere")
    elif setup == "bad_settings":
        def broken(*a, **k):
            raise ValueError("broken settings")

        monkeypatch.setattr(runner.sandbox_mod, "settings_text", broken)
    elif setup == "no_key":
        del p.parent["TSMCP_ANTHROPIC_API_KEY"]
    err = stderr_of_abort(capsys, create_real, p)
    assert err == f"runner: {message}\n"
    assert list(p.tmp_root.iterdir()) == []  # the isolated HOME and config dir are removed again


def test_dry_session_without_the_mcp_command_uses_the_repo_path(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "find_mcp_command", lambda repo: None)
    s = runner.Session.create(dry_run=True, gateway=False, repo=runner.REPO_ROOT, need_b=False)
    try:
        ts = json.loads(s.ts_json_path.read_text(encoding="utf-8"))
        expected = str(runner.REPO_ROOT / ".venv" / "bin" / "tanabesugano-mcp")
        assert ts["mcpServers"]["tanabesugano"]["command"] == expected
        assert s.claude_argv == runner.FAKE_ARGV and s.claude_version == "fake-0" and s.real_claude is None
    finally:
        s.close()


def test_a_b_stack_error_is_an_abort_in_both_modes(tmp_path, monkeypatch, capsys):
    def refuse(env, venv, *a):
        raise runner.b_stack.BStackError("inside the repo")

    monkeypatch.setattr(runner.b_stack, "b_venv_dir", refuse)
    assert stderr_of_abort(capsys, runner.Session.create, dry_run=True, gateway=False) == (
        "runner: B stack: inside the repo\n")
    s = runner.Session.create(dry_run=True, gateway=False, need_b=False)  # not needed: not an error
    s.close()

    def broken(venv):
        raise runner.b_stack.BStackError("no pip")

    monkeypatch.setattr(runner.b_stack, "b_venv_dir", lambda env, venv, *a: tmp_path / "vB")
    monkeypatch.setattr(runner.b_stack, "ensure_b_stack", broken)
    assert stderr_of_abort(capsys, runner.Session.create, dry_run=False, gateway=False,
                           parent_env={"TSMCP_ANTHROPIC_API_KEY": "k"}) == "runner: B stack: no pip\n"


def test_session_placeholders_name_every_path_longest_first(tmp_path):
    claude = tmp_path / "bin" / "claude"
    s = runner.Session(dry_run=False, gateway=False, home=str(tmp_path / "iso"), cfg_dir=str(tmp_path / "cfg"), env={},
                       claude_argv=[str(claude)], real_claude=str(claude), claude_version="1", real_claude_version="1",
                       repo=tmp_path / "repo", real_home=str(tmp_path / "realhome"), b_venv=str(tmp_path / "vB"))
    pairs = dict(s.placeholders(tmp_path / "out"))
    assert pairs[str(tmp_path / "out")] == "<OUT>" and pairs[str(tmp_path / "cfg")] == "<CFG>"
    assert pairs[str(tmp_path / "iso")] == "<ISO_HOME>" and pairs[str(tmp_path / "repo")] == "<REPO>"
    assert pairs[str(claude)] == "<CLAUDE>" and pairs[str(tmp_path / "vB")] == "<B_VENV>"
    assert pairs[str(tmp_path / "realhome")] == "<HOME>" and pairs[runner.tempfile.gettempdir()] == "<TMP>"
    assert sys.executable not in pairs  # only a dry session records the fake's interpreter
    lengths = [len(p) for p, _ in s.placeholders()]
    assert lengths == sorted(lengths, reverse=True)
    assert s.record({"p": f"{tmp_path}/out/x", "n": 1}, tmp_path / "out") == {"p": "<OUT>/x", "n": 1}


# ------------------------------------------------------------------ the budget and the sandbox probe together
def stub_probe(monkeypatch, passed, cost):
    rec = {"passed": passed, "cost_usd": cost, "reasons": ["stub reason"], "markers": {}}
    monkeypatch.setattr(sandbox_probe, "run_probe", lambda session, out, **kw: dict(rec))
    return rec


def b_then_a(tmp_path, limit, budget, extra=()):
    argv = real_args(tmp_path, conds="B,A", extra=extra)
    argv[argv.index("--limit") + 1] = str(limit)
    argv[argv.index("--budget-usd") + 1] = str(budget)
    return runner.main(argv)


def test_the_probe_can_use_up_the_budget_and_everything_is_counted_as_not_run(tmp_path, real_mode_fake, monkeypatch,
                                                                              capsys):
    stub_probe(monkeypatch, True, 1.0)
    assert b_then_a(tmp_path, limit=2, budget=0.5) == runner.EX_TEMPFAIL
    m = manifest(tmp_path / "runs")
    assert m["stopped_by_budget"] is True and m["counts"]["not_run_budget"] == 4 and m["counts"]["done"] == 0
    assert m["total_cost_usd"] == pytest.approx(1.0)
    assert "budget reached after the sandbox probe; stopping cleanly" in capsys.readouterr().out


@pytest.mark.parametrize("passed, bucket", [(False, "not_run_sandbox"), (None, "not_run_probe_not_evaluable")])
def test_a_budget_stop_sorts_the_unrun_b_runs_by_the_probe_verdict(tmp_path, real_mode_fake, monkeypatch, passed,
                                                                   bucket):
    monkeypatch.setenv("FAKE_COST_USD", "1")
    stub_probe(monkeypatch, passed, 0.0)
    assert b_then_a(tmp_path, limit=3, budget=1.5) == runner.EX_TEMPFAIL
    c = manifest(tmp_path / "runs")["counts"]
    # t1B, t2B and t3B are not run because of the probe (t3B is only reached by the budget stop), t3A by the budget
    assert c[bucket] == 3 and c["done"] == 2 and c["not_run_budget"] == 1 and c["planned"] == 6


def test_a_budget_stop_counts_finished_runs_of_an_earlier_invocation_as_skipped(tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_COST_USD", "1")
    rc, out = run_dry(tmp_path, conds="A", limit=3, budget=10)
    assert rc == 0
    rc, out = run_dry(tmp_path, conds="B,A", limit=3, budget=1, extra=("--resume",))
    c = manifest(out)["counts"]
    assert rc == runner.EX_TEMPFAIL and c["skipped"] == 3 and c["not_run_budget"] == 3 and c["done"] == 0


def test_a_passing_probe_record_is_reused_when_b_has_still_to_run(tmp_path, real_mode_fake, capsys):
    argv = real_args(tmp_path, conds="B")
    assert runner.main(argv) == 0
    out = tmp_path / "runs"
    for f in (out / HAIKU / "B" / "medium").glob("*"):
        f.unlink()
    capsys.readouterr()
    assert runner.main(argv + ["--resume"]) == 0
    assert "sandbox probe: reusing sandbox_probe.json (version and settings hash match)" in capsys.readouterr().out
    assert manifest(out)["counts"]["done"] == 1


def test_resume_keeps_going_when_the_earlier_plan_file_is_unreadable(tmp_path):
    rc, out = run_dry(tmp_path, conds="A", limit=1)
    assert rc == 0
    (out / "plan.jsonl").write_text("not a plan\n", encoding="utf-8")
    rc, out = run_dry(tmp_path, conds="A", limit=1, extra=("--resume",))
    assert rc == 0 and manifest(out)["counts"]["skipped"] == 1
    assert (out / "plan.jsonl").read_text(encoding="utf-8") != "not a plan\n"  # rewritten from the live plan


def test_a_flags_plan_pins_the_claude_version_of_this_very_run(tmp_path, real_mode_fake, monkeypatch):
    orig = runner.Session.create.__func__

    def create(cls, **kw):
        s = orig(cls, **kw)
        s.real_claude_version = "9.9.9 (Claude Code)"
        return s

    monkeypatch.setattr(runner.Session, "create", classmethod(create))
    assert runner.main(real_args(tmp_path, conds="A")) == 0
    header = json.loads((tmp_path / "runs" / "plan.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert header["pins"]["claude_cli_version"] == "9.9.9 (Claude Code)"
    assert manifest(tmp_path / "runs")["pin_drift"] == []


# ------------------------------------------------------------------ compute_flags: flags and details, exactly
def uses(*blocks):
    return {"type": "assistant", "message": {"content": list(blocks)}}


def use_block(name, ident="t1", **inp):
    return {"type": "tool_use", "id": ident, "name": name, "input": inp}


def tool_result_event(*blocks):
    return {"type": "user", "message": {"content": list(blocks)}}


def test_flags_ignore_events_that_are_not_dicts_and_blocks_that_are_not_tool_use():
    events = ["junk", None, {"type": "user", "message": {"content": [use_block("Bash")]}},
              uses("text", {"type": "text", "text": "hi"}), uses(use_block("Bash", command="ls"))]
    assert runner.compute_flags("B", events, result()) == ([], {})  # ty: ignore[invalid-argument-type]
    assert runner.compute_flags("B", events[:4], result()) == (  # ty: ignore[invalid-argument-type]
        ["b_no_tool_use"], {"tool_use_count": 0})


def test_flags_b_details():
    assert runner.compute_flags("B", [], result()) == (["b_no_tool_use"], {"tool_use_count": 0})
    flags, details = runner.compute_flags("B", [uses(use_block("Bash"))], result([{"tool_name": "Bash"}] * 2))
    assert flags == ["permission_denials", "b_no_tool_use"] and details == {"permission_denials": 2}
    flags, details = runner.compute_flags("B", [], result([{"tool_name": "Bash"}]))
    assert flags == ["permission_denials", "b_no_tool_use"] and details == {"permission_denials": 1}  # once, no count
    assert runner.compute_flags("A", [], None) == ([], {})
    assert runner.compute_flags("B", [uses(use_block("Bash"))], None) == ([], {})


def test_flags_b_with_a_denial_next_to_code_that_ran_is_not_no_tool_use():
    """Five Bash calls ran, one was refused: the run used the tool, so only `permission_denials` is set."""
    calls = uses(*(use_block("Bash", f"b{i}", command="ls") for i in range(5)))
    denial = {"tool_name": "Bash", "tool_use_id": "b3"}
    assert runner.compute_flags("B", [calls], result([denial])) == (["permission_denials"], {"permission_denials": 1})
    # a denial without an id: the count of the calls that were not refused decides
    assert runner.compute_flags("B", [calls], result([{"tool_name": "Bash"}])) == (
        ["permission_denials"], {"permission_denials": 1})


def test_flags_b_where_every_call_was_denied_is_no_tool_use():
    calls = uses(use_block("Bash", "b1"), use_block("Bash", "b2"))
    denials = [{"tool_name": "Bash", "tool_use_id": "b1"}, {"tool_name": "Bash", "tool_use_id": "b2"}]
    assert runner.compute_flags("B", [calls], result(denials)) == (
        ["permission_denials", "b_no_tool_use"], {"permission_denials": 2})
    one_ran = [{"tool_name": "Bash", "tool_use_id": "b1"}]
    assert runner.compute_flags("B", [calls], result(one_ran))[0] == ["permission_denials"]


def test_flags_c_details_count_only_error_results_of_the_mcp_calls():
    mcp = conditions.MCP_TOOL_PREFIX + "ts_fit"
    calls = uses(use_block(mcp, "m1"), use_block(mcp, "m2"), use_block("Bash", "b1"))

    def res(ident, is_error, kind="tool_result"):
        return {"type": kind, "tool_use_id": ident, "is_error": is_error}

    all_errors = tool_result_event("junk", res("m1", True), res("m2", True), res("b1", False), res("m1", False, "text"))
    assert runner.compute_flags("C", [calls, "junk", all_errors], result()) == (  # ty: ignore[invalid-argument-type]
        ["c_all_mcp_errors"], {"mcp_error_results": 2})
    mixed = tool_result_event(res("m1", True), res("m2", False))
    assert runner.compute_flags("C", [calls, mixed], result()) == ([], {})
    other_kind = {"type": "assistant", "message": {"content": [res("m1", True)]}}
    assert runner.compute_flags("C", [calls, other_kind], result()) == ([], {})  # no results at all: not "all errors"
    stray_text = tool_result_event(res("m1", True, "text"))
    assert runner.compute_flags("C", [calls, stray_text], result()) == ([], {})
    unnamed = uses({"type": "tool_use", "id": "x", "input": {}})
    assert runner.compute_flags("C", [unnamed], result()) == (["c_no_mcp_call"], {})


def test_flags_sandbox_escape_and_rate_limit():
    esc = uses(use_block("Bash", command="ls", dangerouslyDisableSandbox=True))
    assert runner.compute_flags("A", [esc], result()) == (["sandbox_escape_requested"], {})
    bare = uses({"type": "tool_use", "id": "z", "name": "Bash"})
    assert runner.compute_flags("A", [bare], result()) == ([], {})
    limited = {"type": "result", "is_error": True, "api_error_status": 429, "permission_denials": [{"x": 1}]}
    assert runner.compute_flags("B", [], limited) == (["rate_limited"], {})
    not_error = {"type": "result", "is_error": False, "api_error_status": 429, "permission_denials": []}
    assert runner.compute_flags("B", [], not_error) == (["b_no_tool_use"], {"tool_use_count": 0})


def test_write_json_atomic_sorts_keys_and_goes_through_a_tmp_file(tmp_path, monkeypatch):
    moves = []
    real_replace = pathlib.Path.replace

    def spy(self, target):
        moves.append((self.name, pathlib.Path(target).name))
        return real_replace(self, target)

    monkeypatch.setattr(pathlib.Path, "replace", spy)
    target = tmp_path / "deep" / "m.json"
    runner.write_json_atomic(target, {"b": 1, "a": {"y": pathlib.Path("/p"), "x": "café"}})
    assert [m[1] for m in moves] == ["m.json"]
    assert re.fullmatch(r"m\.json\.\d+\.[0-9a-f]{8}\.tmp", moves[0][0]) and sorted(
        p.name for p in target.parent.iterdir()) == ["m.json"]
    assert target.read_text(encoding="utf-8") == (
        '{\n  "a": {\n    "x": "caf\\u00e9",\n    "y": "/p"\n  },\n  "b": 1\n}\n')


def test_recorded_args_make_paths_relative_or_placeholders(tmp_path):
    repo = tmp_path / "repo"
    inside = repo / "runs" / "x"
    inside.mkdir(parents=True)
    outside = tmp_path / "elsewhere" / "out"
    outside.mkdir(parents=True)
    session = SimpleNamespace(repo=repo.resolve(), placeholders=lambda out=None: [(str(tmp_path), "<T>")] if out is None
                              else [(str(outside), "<OUT>"), (str(tmp_path), "<T>")])
    args = SimpleNamespace(out=str(inside), plan=str(tmp_path / "plan.jsonl"), b_venv=None, k=1, models="m")
    got = runner.recorded_args(args, session, outside)  # ty: ignore[invalid-argument-type]
    assert got == {"out": "runs/x", "plan": "<T>/plan.jsonl", "b_venv": None, "k": 1, "models": "m"}
    args = SimpleNamespace(out=str(outside), plan="", b_venv=str(tmp_path / "vB"))
    got = runner.recorded_args(args, session, outside)  # ty: ignore[invalid-argument-type]
    assert got == {"out": "<T>/elsewhere/out", "plan": "", "b_venv": "<T>/vB"}


# ------------------------------------------------------------------ execute: exact outcomes
def test_execute_keeps_the_whole_stderr_and_replaces_invalid_bytes(tmp_path):
    code = f"import sys, json; sys.stderr.buffer.write(b'caf\\xe9 ok'); sys.stderr.flush(); print({INIT_JSON})"
    out = execute_code(tmp_path, code)
    assert out.mismatches == [] and out.stderr_tail == "caf\N{REPLACEMENT CHARACTER} ok"


def test_execute_runs_the_child_as_a_session_leader_in_a_tsbench_run_dir(tmp_path):
    code = ("import os, json; print(json.dumps({'type':'system','subtype':'init','tools':['StructuredOutput'],"
            "'mcp_servers':[],'model':'m','cwd':os.getcwd(),'leader':os.getsid(0) == os.getpid()}))")
    out = execute_code(tmp_path, code)
    assert out.mismatches == [] and out.init["leader"] is True  # its own session: the kill reaches the whole group
    assert pathlib.Path(out.init["cwd"]).name.startswith("tsbench-run-")


def test_execute_drops_a_first_line_that_is_json_but_not_an_object(tmp_path):
    out = execute_code(tmp_path, "print('[1, 2]')")
    assert out.mismatches == ["first non-system line is not a JSON object"] and out.init_aborted is True
    assert out.init is None and out.init_seen is False and out.events == [[1, 2]]


def test_execute_timeout_before_init_is_not_an_init_abort(tmp_path):
    out = execute_code(tmp_path, "import time; time.sleep(60)", timeout_s=0.5)
    assert out.timed_out is True and out.init_aborted is False and out.mismatches == []
    assert 0.4 <= out.wall_s < 20


def test_execute_of_a_missing_binary_reports_exact_fields(tmp_path):
    out = runner.execute([str(tmp_path / "no-such-claude")], "p", {"PATH": "/usr/bin"}, tmp_path / "t.jsonl",
                         conditions.get("A"), "m", timeout_s=30)
    assert out.spawn_failed is True and out.timed_out is False and out.init_aborted is False
    assert out.mismatches == [] and out.events == [] and 0 <= out.wall_s < 20


def test_execute_checks_the_init_event_against_the_blocked_tools(tmp_path):
    init = fixture("init_C.json")
    script = tmp_path / "emit.py"
    script.write_text("import sys\nfor line in sys.argv[1:]: print(line, flush=True)\n", encoding="utf-8")
    out = runner.execute([sys.executable, str(script), json.dumps(init)], "p", {"PATH": "/usr/bin:/bin"},
                         tmp_path / "t.jsonl", conditions.get("C"), init["model"], timeout_s=30,
                         disallowed=IMAGE_TOOLS)
    assert out.init_aborted is True
    assert out.mismatches[0] == f"C: tools that were disallowed are in the init tool list: {IMAGE_TOOLS!r}"


@pytest.fixture
def locked_run_dir(tmp_path, monkeypatch):
    """`tempfile.mkdtemp` hands out the run dir inside a read-only folder, so the run dir cannot be removed."""
    if os.geteuid() == 0:
        pytest.skip("root removes any directory")
    parent = tmp_path / "locked"
    parent.mkdir()

    def mkdtemp(prefix=None, **kw):
        d = parent / (prefix or "tmp")
        d.mkdir()
        parent.chmod(0o555)
        return str(d)

    monkeypatch.setattr(runner.tempfile, "mkdtemp", mkdtemp)
    yield parent
    parent.chmod(0o755)


def test_execute_goes_on_when_its_run_dir_cannot_be_removed(tmp_path, locked_run_dir):
    out = execute_code(tmp_path, f"import json; print({INIT_JSON})")
    assert out.mismatches == [] and out.init_seen is True
    assert (locked_run_dir / "tsbench-run-").is_dir()  # left behind, not an error


def test_execute_of_a_missing_binary_goes_on_when_its_run_dir_cannot_be_removed(tmp_path, locked_run_dir):
    out = runner.execute([str(tmp_path / "no-such-claude")], "p", {"PATH": "/usr/bin"}, tmp_path / "t.jsonl",
                         conditions.get("A"), "m", timeout_s=30)
    assert out.spawn_failed is True and (locked_run_dir / "tsbench-run-").is_dir()


def test_retries_pass_the_call_through_and_record_each_status(tmp_path, monkeypatch, waits, capsys):
    monkeypatch.setenv(runner.RETRY_429_ENV, "0")  # the process environment says never; the given one says twice
    results = [{"type": "result", "is_error": True, "api_error_status": 503, "result": "rate limit reached"},
               {"type": "result", "is_error": True, "result": "Request failed (429)"},
               {"type": "result", "is_error": False, "total_cost_usd": 0.1}]
    seen: list[tuple] = []

    def execute(argv, prompt, env, transcript, cond, model, *, timeout_s, disallowed):
        seen.append((timeout_s, disallowed))
        res = results[len(seen) - 1]
        transcript.write_text(json.dumps(res) + "\n", encoding="utf-8")
        return runner.Outcome(events=[res], init=None, mismatches=[], result=res, exit_code=0, wall_s=0.0,
                              stderr_tail="", timed_out=False, init_aborted=False)

    flushes: list = []

    def spy(*args, **kw):
        flushes.append(kw.get("flush"))
        print(*args, **kw)

    monkeypatch.setattr(runner, "execute", execute)
    monkeypatch.setattr(runner, "backoff_s", lambda n: 60.0 * n)
    monkeypatch.setattr(runner, "print", spy, raising=False)
    t = tmp_path / "r-k1.jsonl"
    outcome, retries = runner.execute_with_retries(["claude"], "p", {}, t, conditions.get("A"), "m", timeout_s=12.5,
                                                   disallowed=("X",), parent_env={runner.RETRY_429_ENV: "2"})
    assert outcome.result == results[2] and seen == [(12.5, ("X",))] * 3
    assert [(r["wait_s"], r["status"]) for r in retries] == [(60.0, "503"), (120.0, "429")]
    assert waits == [60.0, 120.0] and flushes == [True, True]
    assert capsys.readouterr().out.splitlines() == ["HTTP 429 for r-k1.jsonl: waiting 60 s, then retry 1 of 2",
                                                    "HTTP 429 for r-k1.jsonl: waiting 120 s, then retry 2 of 2"]
    assert json.loads(runner.attempt_path(t, 1).read_text(encoding="utf-8")) == results[0]


# ------------------------------------------------------------------ Session: defaults, placeholders, create
def test_session_falls_back_to_the_home_and_the_stack_path_and_closes_missing_dirs(tmp_path):
    s = runner.Session(dry_run=True, gateway=False, home=str(tmp_path / "gone-home"),
                       cfg_dir=str(tmp_path / "gone-cfg"),
                       env={}, claude_argv=list(runner.FAKE_ARGV), real_claude=None, claude_version="fake-0",
                       real_claude_version=None, repo=tmp_path, b_stack_info={"path": str(tmp_path / "vB")})
    assert s.real_home == str(pathlib.Path("~").expanduser()) and s.b_venv == str(tmp_path / "vB")
    assert s.close() is None  # neither directory exists: nothing to remove and no error


def test_session_placeholders_name_the_base_interpreter_of_venv_b(tmp_path):
    venv = tmp_path / "vB"
    venv.mkdir()
    (venv / "pyvenv.cfg").write_text(f"home = {tmp_path / 'base'}/bin\n", encoding="utf-8")
    common: dict[str, Any] = {
        "dry_run": False, "gateway": False, "home": str(tmp_path / "iso"), "cfg_dir": str(tmp_path / "cfg"),
        "env": {}, "claude_argv": [], "real_claude": None, "claude_version": "1", "real_claude_version": "1",
        "repo": tmp_path / "repo", "real_home": str(tmp_path / "realhome")}
    s = runner.Session(b_venv=str(venv), **common)
    assert dict(s.placeholders())[str(tmp_path / "base")] == "<B_BASE_PYTHON>"
    bare = runner.Session(**common)  # no venv: no base interpreter to name
    assert "<B_BASE_PYTHON>" not in dict(bare.placeholders()).values()


_REAL_WHICH = runner.shutil.which  # captured at import, before a fixture replaces it


def fake_node(d: pathlib.Path) -> pathlib.Path:
    """A folder with the interpreter `tsfakenode`: run as `<script> --version` it prints a version and its cwd."""
    d.mkdir(parents=True, exist_ok=True)
    node = d / "tsfakenode"
    node.write_text('#!/bin/sh\nif [ "$2" = "--version" ]; then echo "2.1.99 (Claude Code) $(pwd -P)"; fi\n',
                    encoding="utf-8")
    node.chmod(0o755)
    return d


def test_real_session_finds_claude_and_its_interpreter_on_the_parent_path(real_session_parts, monkeypatch):
    p = real_session_parts
    node_dir = fake_node(p.tmp_path / "nodebin")
    p.claude.write_text("#!/usr/bin/env tsfakenode\n", encoding="utf-8")
    p.parent["PATH"] = os.pathsep.join([str(p.claude.parent), str(node_dir)])
    (p.tmp_path / "empty").mkdir()
    monkeypatch.setenv("PATH", str(p.tmp_path / "empty"))  # nothing is found through the test's own PATH
    monkeypatch.setattr(runner.shutil, "which", _REAL_WHICH)
    versions: list = []
    real_run = runner.subprocess.run

    def run(cmd, **kw):
        if cmd[0] == str(p.claude):
            versions.append((list(cmd), kw.get("timeout")))
        return real_run(cmd, **kw)

    monkeypatch.setattr(runner.subprocess, "run", run)
    s = create_real(p)
    try:
        cbin, nbin = str(p.claude.parent.resolve()), str(node_dir.resolve())
        assert s.real_claude == str(p.claude) and s.runtime_dirs == [cbin, nbin]
        assert s.env["PATH"] == os.pathsep.join(["/usr/bin", "/bin", cbin, nbin])
        assert s.real_claude_version == f"2.1.99 (Claude Code) {pathlib.Path(s.home).resolve()}"
        assert versions == [([str(p.claude), "--version"], 30)]
    finally:
        s.close()


def test_real_session_without_a_parent_path_looks_up_no_interpreter(real_session_parts, monkeypatch):
    p = real_session_parts
    node_dir = fake_node(p.tmp_path / "nodebin")
    fake_node(p.tmp_path / "XXXX")  # a folder in the working directory is no PATH either
    p.claude.write_text("#!/usr/bin/env tsfakenode\n", encoding="utf-8")
    del p.parent["PATH"]
    monkeypatch.setenv("PATH", os.pathsep.join([str(p.claude.parent), str(node_dir)]))
    monkeypatch.setattr(runner.shutil, "which", _REAL_WHICH)
    monkeypatch.chdir(p.tmp_path)
    s = create_real(p)
    try:
        assert s.real_claude == str(p.claude) and s.runtime_dirs == [str(p.claude.parent.resolve())]
    finally:
        s.close()


def test_real_session_keeps_the_parent_home_and_names_the_given_b_venv(real_session_parts, monkeypatch):
    p = real_session_parts
    venv = p.tmp_path / "vB"

    def ensure(v):
        return {"path": str(v), "bin": str(pathlib.Path(v) / "bin"), "python": "3", "packages": {}, "digest": "d"}

    monkeypatch.setattr(runner.b_stack, "ensure_b_stack", ensure)
    s = runner.Session.create(dry_run=False, gateway=False, parent_env=p.parent, b_venv=venv)
    try:
        assert s.real_home == p.parent["HOME"] and s.b_stack is not None and s.b_stack["path"] == str(venv)
    finally:
        s.close()
    s = create_real(p, b_venv=venv)  # B is not needed: no stack, but the venv is still named for the records
    try:
        assert s.b_stack is None and s.b_venv == str(venv)
    finally:
        s.close()


def test_real_session_writes_its_config_files_exactly(real_session_parts):
    p = real_session_parts
    venv = p.tmp_path / "vB"
    s = create_real(p, b_venv=venv)
    try:
        assert s.ts_json_path.read_text(encoding="utf-8") == json.dumps(runner.render_ts_json(str(p.mcp)),
                                                                        indent=2) + "\n"
        expected = sandbox.settings_text(s.repo, p.parent["HOME"], b_venv=venv, mpl_dir=str(p.tmp_path / "mpl"),
                                         parent_env=p.parent)
        assert s.settings_path.read_text(encoding="utf-8") == expected
        assert s.env["CLAUDE_CONFIG_DIR"] == str(pathlib.Path(s.home) / ".claude")
    finally:
        s.close()


def test_real_gateway_session_passes_the_gateway_variables(real_session_parts):
    p = real_session_parts
    parent = {**p.parent, "ANTHROPIC_BASE_URL": "http://gw.example", "ANTHROPIC_AUTH_TOKEN": "tok-abcdefgh"}
    s = runner.Session.create(dry_run=False, gateway=True, parent_env=parent, need_b=False)
    try:
        assert s.env["ANTHROPIC_BASE_URL"] == "http://gw.example" and s.env["ANTHROPIC_AUTH_TOKEN"] == "tok-abcdefgh"
        assert "ANTHROPIC_API_KEY" not in s.env
    finally:
        s.close()


def test_real_gateway_session_names_every_missing_variable(real_session_parts, capsys):
    err = stderr_of_abort(capsys, runner.Session.create, dry_run=False, gateway=True,
                          parent_env=real_session_parts.parent, need_b=False)
    assert err == "runner: required environment variable not set: ANTHROPIC_BASE_URL, ANTHROPIC_AUTH_TOKEN\n"


def test_real_session_names_every_offender_on_the_child_path(real_session_parts, monkeypatch, capsys):
    monkeypatch.setattr(runner, "path_offenders", lambda path: ["/x/tanabesugano-mcp", "/y/tanabesugano"])
    assert stderr_of_abort(capsys, create_real, real_session_parts) == (
        "runner: the child PATH would reach /x/tanabesugano-mcp, /y/tanabesugano; condition B must not\n")


def test_real_session_cleanup_survives_dirs_that_are_already_gone(real_session_parts, monkeypatch, capsys):
    p = real_session_parts

    def gone(repo):
        for d in p.tmp_root.iterdir():
            runner.shutil.rmtree(d)
        return None

    monkeypatch.setattr(runner, "find_mcp_command", gone)
    assert stderr_of_abort(capsys, create_real, p) == (
        "runner: tanabesugano-mcp not found in <repo>/.venv/bin or next to the Python interpreter\n")


def test_dry_session_from_a_bare_parent_environment(tmp_path):
    (tmp_path / "empty").mkdir()
    parent = {"PATH": str(tmp_path / "empty"), "TSBENCH_B_VENV": str(REPO_ROOT / "venv-inside")}
    s = runner.Session.create(dry_run=True, gateway=False, parent_env=parent, need_b=False)
    try:
        assert s.real_home == str(pathlib.Path("~").expanduser())
        assert s.real_claude is None and s.real_claude_version is None and s.b_venv is None
        assert s.env["PYTHONPATH"] == str(REPO_ROOT.resolve()) and "MPLCONFIGDIR" not in s.env
        expected = sandbox.settings_text(s.repo, s.real_home, b_venv=None,
                                         mpl_dir=runner.mpl_cache_dir(parent, s.repo), parent_env=parent)
        assert s.settings_path.read_text(encoding="utf-8") == expected
    finally:
        s.close()


def test_a_b_venv_inside_the_given_repo_is_refused(tmp_path, capsys):
    repo = tmp_path / "repo"
    repo.mkdir()
    err = stderr_of_abort(capsys, runner.Session.create, dry_run=True, gateway=False, repo=repo, b_venv=repo / "vB")
    assert err == (f"runner: B stack: B venv {repo / 'vB'} lies inside the repo; set TSBENCH_B_VENV / --b-venv "
                   "elsewhere\n")


# ------------------------------------------------------------------ B's sandbox denies reading only some folders
def _b_info(p):
    return {"path": str(p.tmp_path / "vB"), "bin": str(p.tmp_path / "vB" / "bin"), "python": "3", "packages": {},
            "digest": "d"}


def test_a_real_run_with_b_refuses_an_out_folder_the_sandbox_does_not_deny(real_session_parts, monkeypatch, capsys):
    """The sandbox denies the repo, the main checkout and the real home. Any other --out holds the transcripts of the
    earlier runs, which B's Bash could read."""
    p = real_session_parts
    monkeypatch.setattr(runner.b_stack, "ensure_b_stack", lambda venv, **kw: _b_info(p))
    with pytest.raises(SystemExit) as e:
        runner.Session.create(dry_run=False, gateway=False, parent_env=p.parent, b_venv=p.tmp_path / "vB",
                              out=p.tmp_path / "scratch" / "runs")
    assert e.value.code == 2
    err = capsys.readouterr().err
    assert "--out" in err and "sandbox" in err and str(p.tmp_path / "scratch" / "runs") in err


@pytest.mark.parametrize("where", ["home", "repo"])
def test_a_real_run_with_b_accepts_an_out_folder_the_sandbox_denies(real_session_parts, monkeypatch, where):
    p = real_session_parts
    monkeypatch.setattr(runner.b_stack, "ensure_b_stack", lambda venv, **kw: _b_info(p))
    out = (p.tmp_path / "home" if where == "home" else REPO_ROOT) / "runs"
    runner.Session.create(dry_run=False, gateway=False, parent_env=p.parent, b_venv=p.tmp_path / "vB", out=out).close()


def test_the_out_folder_is_only_checked_for_a_real_run_with_condition_b(real_session_parts, monkeypatch):
    p = real_session_parts
    monkeypatch.setattr(runner.b_stack, "ensure_b_stack", lambda venv, **kw: _b_info(p))
    out = p.tmp_path / "scratch" / "runs"
    runner.Session.create(dry_run=False, gateway=False, parent_env=p.parent, need_b=False, out=out).close()  # no B
    runner.Session.create(dry_run=True, gateway=False, parent_env=p.parent, b_venv=p.tmp_path / "vB", out=out).close()


def test_the_runner_defines_no_unused_names_or_re_exports():
    dead = ["BUDGET_FLOOR_USD", "FORBIDDEN_ON_PATH", "SYSTEM_PATH", "ARTIFACT_MAX_BYTES", "ARTIFACT_SUFFIXES",
            "BARE_ALIASES", "GATEWAY_MODEL_RE", "MODEL_RE", "TS_JSON"]
    assert [n for n in dead if hasattr(runner, n)] == []
