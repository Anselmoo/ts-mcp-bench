"""Exact checks of the sandbox settings, the check script and its prompt, the method record and the reuse rule of an
earlier check record. Nothing here runs claude; git is only used to build a throwaway linked checkout."""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import site
import subprocess
import sys
from types import SimpleNamespace

import pytest

from tsbench.conditions import b_stack, sandbox

KEY_DENY = [{"name": v, "mode": "deny"} for v in sandbox.KEY_VARS]


@pytest.fixture
def layout(tmp_path, monkeypatch):
    """A repo, a real home, venv-B with a base interpreter, the matplotlib cache and a harness install, all in tmp."""
    d = SimpleNamespace(repo=tmp_path / "repo", home=tmp_path / "home", venv=tmp_path / "venv", base=tmp_path / "base",
                        mpl=tmp_path / "mpl", prefix=tmp_path / "prefix")
    for p in (d.repo, d.home, d.venv, d.mpl, d.prefix / "site"):
        p.mkdir(parents=True)
    d.base_site = d.base / "lib" / "python3.14" / "site-packages"
    d.base_site.mkdir(parents=True)
    monkeypatch.setattr(b_stack, "base_dirs", lambda venv: [d.base] if pathlib.Path(venv) == d.venv else [])
    monkeypatch.delenv("TSBENCH_KEY_FILE", raising=False)
    return d


def render(d, **kw):
    args = {"b_venv": d.venv, "mpl_dir": d.mpl, "harness": [str(d.prefix), str(d.prefix / "site")], **kw}
    return sandbox.render_settings(d.repo, d.home, **args)


def test_settings_whole_structure(layout):
    d = layout
    assert render(d) == {"sandbox": {
        "enabled": True, "failIfUnavailable": True, "autoAllowBashIfSandboxed": True,
        "allowUnsandboxedCommands": False, "network": {"allowedDomains": []},
        "filesystem": {
            "denyRead": [str(d.repo), str(d.home), "~/.config/tsbench", str(d.home / ".config/tsbench"),
                         "~/.cache/pip", str(d.home / ".cache/pip"), str(d.prefix), str(d.prefix / "site"),
                         str(d.base_site)],
            "allowRead": [str(d.venv), str(d.base), str(d.mpl)]},
        "credentials": {"envVars": KEY_DENY}}}


def test_settings_deny_the_folder_of_a_configured_key_file(layout, monkeypatch):
    d = layout
    monkeypatch.setenv("TSBENCH_KEY_FILE", "/srv/keys/model.env")
    deny = render(d)["sandbox"]["filesystem"]["denyRead"]
    assert deny[:4] == [str(d.repo), str(d.home), "/srv/keys", "~/.cache/pip"]
    assert "~/.config/tsbench" not in deny
    env = {"TSBENCH_KEY_FILE": str(d.home / "sec" / "model.env")}
    deny = render(d, parent_env=env)["sandbox"]["filesystem"]["denyRead"]
    assert deny[2:4] == ["~/sec", str(d.home / "sec")]


def test_settings_leave_the_template_alone(layout):
    before = json.dumps(sandbox.SETTINGS_TEMPLATE, sort_keys=True)
    render(layout)
    render(layout)
    assert json.dumps(sandbox.SETTINGS_TEMPLATE, sort_keys=True) == before
    assert sandbox.SETTINGS_TEMPLATE["sandbox"]["filesystem"]["denyRead"][:2] == ["<REPO>", "<REAL_HOME>"]


def test_settings_with_the_harness_in_the_base_interpreter(layout):
    """An allowed dir inside the harness prefix: the prefix itself is not denied, only its site-packages."""
    d = layout
    s = render(d, harness=[str(d.base), str(d.base_site)])["sandbox"]["filesystem"]
    assert s["denyRead"][-1:] == [str(d.base_site)] and str(d.base) not in s["denyRead"]
    assert s["denyRead"].count(str(d.base_site)) == 1


def test_settings_without_venv_b(layout, monkeypatch):
    d = layout

    def no_venv(env, override, repo):
        raise b_stack.BStackError("x")
    monkeypatch.setattr(b_stack, "b_venv_dir", no_venv)
    s = sandbox.render_settings(d.repo, d.home, mpl_dir=d.mpl, harness=[])["sandbox"]["filesystem"]
    assert s["allowRead"] == [str(d.mpl)]
    assert s["denyRead"] == [str(d.repo), str(d.home), "~/.config/tsbench", str(d.home / ".config/tsbench"),
                             "~/.cache/pip", str(d.home / ".cache/pip")]


def test_settings_take_venv_b_and_the_cache_from_the_environment(layout):
    d = layout
    env = {"TSBENCH_B_VENV": str(d.venv), "TSBENCH_MPLCONFIGDIR": str(d.mpl)}
    s = sandbox.render_settings(d.repo, d.home, harness=[], parent_env=env)["sandbox"]["filesystem"]
    assert s["allowRead"] == [str(d.venv), str(d.base), str(d.mpl)]


def test_settings_default_to_the_real_home(layout, monkeypatch):
    d = layout
    monkeypatch.setenv("HOME", str(d.home))
    s = sandbox.render_settings(d.repo, b_venv=d.venv, mpl_dir=d.mpl, harness=[])["sandbox"]["filesystem"]
    assert s["denyRead"][1] == str(d.home)


def test_settings_refuse_an_allowed_dir_in_the_repo(layout):
    d = layout
    inside = d.repo / "venv"
    with pytest.raises(ValueError, match=f"^allowRead entry {inside} lies inside the repo$"):
        render(d, b_venv=inside)


def test_settings_refuse_an_allowed_dir_in_the_harness_site_packages(layout):
    d = layout
    with pytest.raises(ValueError) as e:
        render(d, harness=[str(d.prefix), str(d.mpl.parent)])
    assert str(e.value) == f"allowRead entry {d.venv} lies inside the harness site-packages {d.mpl.parent}"


def test_settings_text_and_hash(layout):
    d = layout
    kw = {"b_venv": d.venv, "mpl_dir": d.mpl, "harness": []}
    text = sandbox.settings_text(d.repo, d.home, **kw)
    assert text == json.dumps(sandbox.render_settings(d.repo, d.home, **kw), indent=2, sort_keys=True) + "\n"
    assert text.startswith('{\n  "sandbox": {\n    "allowUnsandboxedCommands": false,\n')
    assert sandbox.settings_sha256(d.repo, d.home, **kw) == hashlib.sha256(text.encode("utf-8")).hexdigest()


def git(*args, cwd):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=cwd, check=True,
                   capture_output=True)


def test_main_checkouts_of_a_linked_checkout(tmp_path):
    main = tmp_path / "main"
    main.mkdir()
    git("init", "-q", cwd=main)
    git("commit", "-q", "--allow-empty", "-m", "x", cwd=main)
    git("worktree", "add", "-q", str(tmp_path / "wt"), cwd=main)
    assert sandbox.main_checkouts(tmp_path / "wt") == [str(main)]
    assert sandbox.main_checkouts(main) == []
    assert sandbox.main_checkouts(tmp_path) == []


def test_harness_prefixes_are_the_prefix_and_site_packages():
    assert sandbox.harness_prefixes() == list(dict.fromkeys([sys.prefix, *site.getsitepackages()]))


# ------------------------------------------------------------------ the check script
def test_existing_home_paths(tmp_path, monkeypatch):
    (tmp_path / ".cache" / "uv").mkdir(parents=True)
    (tmp_path / ".ssh").mkdir()
    (tmp_path / ".bash_history").symlink_to(tmp_path / "gone")  # a dangling link still counts (lexists)
    assert sandbox.existing_home_paths(tmp_path) == {"HOMECACHE": [".cache/uv"],
                                                     "HOMESECRETS": [".ssh", ".bash_history"]}
    monkeypatch.setenv("HOME", str(tmp_path))
    assert sandbox.existing_home_paths() == {"HOMECACHE": [".cache/uv"], "HOMESECRETS": [".ssh", ".bash_history"]}


def test_missing_targets(tmp_path):
    assert sandbox.missing_probe_targets(tmp_path) == ("VENV", "READ")
    (tmp_path / ".venv" / "bin").mkdir(parents=True)
    (tmp_path / ".venv" / "bin" / "python").write_text("", encoding="utf-8")
    assert sandbox.missing_probe_targets(tmp_path) == ("READ",)


Q = "> /dev/null 2>&1"
KEYS = "".join(f"${{{v}-}}" for v in sandbox.KEY_VARS)
HEREDOC = ("cat > ./probe_heredoc.py <<'EOF'\nfrom math import factorial\n\ndef tri(a, b, c):\n"
           "    return factorial(a + b - c) * factorial(a - b + c) / factorial(a + b + c + 1)\n\n"
           "print(tri(3, 2, 1))\nEOF\npython3 ./probe_heredoc.py; echo PROBE_HEREDOC rc=$?")


def script(venv_line, read_line, home_lines):
    return [
        'echo PROBE_CTRL1 rc=0; python3 -c "print(2+3)"; echo PROBE_CTRL2 rc=$?',
        '[ -n "${TSPROBE_REPO-}" ] && [ -n "${TSPROBE_RH-}" ] && [ "$TSPROBE_RH" != "$HOME" ]; echo PROBE_PATHS rc=$?',
        f'[ -z "{KEYS}" ]; echo PROBE_KEYENV rc=$?',
        f'python3 -c "import tanabesugano" {Q}; echo PROBE_IMPORT rc=$?',
        f"python3 -m pip download --no-deps -d ./dl tanabesugano==2.0.0 {Q}; echo PROBE_PIP rc=$?",
        f"curl -sS -m 10 https://pypi.org/simple/tanabesugano/ -o /dev/null {Q}; echo PROBE_NET rc=$?",
        venv_line, read_line,
        f"command -v tanabesugano {Q}; echo PROBE_TSBIN rc=$?",
        f"command -v tanabesugano-mcp {Q}; echo PROBE_TSBIN rc=$?",
        *home_lines,
        f"curl -sS -m 5 http://127.0.0.1:4000/ -o /dev/null {Q}; echo PROBE_LOCALHOST rc=$?",
        f"curl -sS -m 5 https://api.anthropic.com -o /dev/null {Q}; echo PROBE_APIHOST rc=$?",
        f"curl -sS -m 5 {sandbox.API_HOSTS[1]} -o /dev/null {Q}; echo PROBE_APIHOST rc=$?",
        f"python3 -c \"import socket; socket.gethostbyname('example.org')\" {Q}; echo PROBE_DNS rc=$?",
        'python3 -c "import numpy, scipy, sympy, matplotlib"; echo PROBE_NUMPY rc=$?',
        HEREDOC,
    ]


VENV_LINE = f'"$TSPROBE_REPO"/.venv/bin/python -c "import tanabesugano" {Q}; echo PROBE_VENV rc=$?'
READ_LINE = f'cat "$TSPROBE_REPO"/src/tsbench/data/tasks/tasks.jsonl {Q}; echo PROBE_READ rc=$?'


def test_script_lines_with_every_home_path():
    home = {"HOMECACHE": [".cache/uv", ".local"], "HOMESECRETS": [".ssh", ".zsh_history"]}
    assert sandbox.probe_script_lines(home, ()) == script(VENV_LINE, READ_LINE, [
        f'ls "$TSPROBE_RH"/.cache/uv {Q}; echo PROBE_HOMECACHE rc=$?',
        f'ls "$TSPROBE_RH"/.local {Q}; echo PROBE_HOMECACHE rc=$?',
        f'ls "$TSPROBE_RH"/.ssh {Q}; echo PROBE_HOMESECRETS rc=$?',
        f'cat "$TSPROBE_RH"/.zsh_history {Q}; echo PROBE_HOMESECRETS rc=$?'])


def test_script_lines_without_home_paths_and_with_missing_targets():
    assert sandbox.probe_script_lines({}, ("VENV", "READ")) == script(
        "# VENV not tested: .venv/bin/python does not exist in the repository",
        "# READ not tested: src/tsbench/data/tasks/tasks.jsonl does not exist in the repository",
        ["false; echo PROBE_HOMECACHE rc=$?", "false; echo PROBE_HOMESECRETS rc=$?"])


def test_script_lines_default_to_this_host(monkeypatch, tmp_path):
    monkeypatch.setattr(sandbox, "existing_home_paths", lambda: {"HOMECACHE": [], "HOMESECRETS": []})
    monkeypatch.setattr(sandbox, "missing_probe_targets", lambda: ("READ",))
    lines = sandbox.probe_script_lines()
    assert lines[6] == VENV_LINE and lines[7].startswith("# READ not tested")


def test_script_hashes():
    home = {"HOMECACHE": [".local"], "HOMESECRETS": []}
    text = "\n".join(sandbox.probe_script_lines(home, ("READ",)))
    assert sandbox.probe_script_sha256(home, ("READ",)) == hashlib.sha256(text.encode("utf-8")).hexdigest()
    full = {"HOMECACHE": [".cache/uv", ".local"],
            "HOMESECRETS": [".ssh", ".config/gh/hosts.yml", ".zsh_history", ".bash_history"]}
    assert sandbox.probe_script_template_sha256() == sandbox.probe_script_sha256(full, ())


def test_script_environment(tmp_path, monkeypatch):
    assert sandbox.probe_env("/r", "/h") == {"TSPROBE_REPO": "/r", "TSPROBE_RH": "/h"}
    monkeypatch.setenv("HOME", str(tmp_path))
    assert sandbox.probe_env(pathlib.Path("/r")) == {"TSPROBE_REPO": "/r", "TSPROBE_RH": str(tmp_path)}


def test_script_prompt():
    home = {"HOMECACHE": [], "HOMESECRETS": []}
    body = "\n".join(sandbox.probe_script_lines(home, ()))
    assert sandbox.probe_prompt(home, ()) == (
        "Use the Bash tool exactly once, in a single call, to run the shell script below verbatim. "
        "Do not modify it, do not split it and do not run anything else. "
        "When it has finished, reply with the single word: done\n\n"
        f"```bash\n{body}\n```\n")


# ------------------------------------------------------------------ the record of the check
@pytest.mark.parametrize("tool,container", [
    ("docker", "docker found; not built: only used if builtin fails"),
    (None, "no docker/podman on PATH; not built: only used if builtin fails"),
])
def test_method_record_of_a_failed_check(monkeypatch, tool, container):
    monkeypatch.setattr(sandbox, "detect_container", lambda: tool)
    rec = {"passed": False, "reasons": ["NET rc=[0]", "DNS missing"]}
    assert sandbox.method_info(rec, False) == {
        "method": "skipped", "reason": "builtin sandbox probe failed: NET rc=[0]; DNS missing",
        "container": container, "probe": rec}


def test_method_record_of_every_other_state():
    assert sandbox.method_info(None, True) == {"method": "dry-run (not probed)", "reason": None, "container": None,
                                               "probe": None}
    assert sandbox.method_info({"passed": True}, True)["method"] == "dry-run (not probed)"
    assert sandbox.method_info(None, False) == {"method": "not yet probed", "reason": None, "container": None,
                                                "probe": None}
    ok = {"passed": True}
    assert sandbox.method_info(ok, False) == {"method": "builtin", "reason": None, "container": None, "probe": ok}
    na = {"passed": None, "reasons": ["api 500", "x"]}
    assert sandbox.method_info(na, False) == {"method": "not evaluable",
                                              "reason": "sandbox probe not evaluable: api 500; x",
                                              "container": None, "probe": na}
    assert sandbox.method_info({"passed": None}, False)["reason"] == "sandbox probe not evaluable: "


def test_method_record_without_a_passed_field(monkeypatch):
    monkeypatch.setattr(sandbox, "detect_container", lambda: None)
    assert sandbox.method_info({}, False)["reason"] == "builtin sandbox probe failed: "


def test_auth_mode_and_settings_hash_of_a_session(tmp_path):
    assert sandbox.auth_mode(SimpleNamespace(gateway=True)) == "gateway"
    assert sandbox.auth_mode(SimpleNamespace(gateway=False)) == "direct"
    assert sandbox.auth_mode(SimpleNamespace()) == "direct"
    assert sandbox.session_settings_sha256(SimpleNamespace(settings_sha256="abc", repo=tmp_path)) == "abc"
    s = SimpleNamespace(settings_sha256=None, repo=sandbox.REPO_ROOT)
    assert sandbox.session_settings_sha256(s) == sandbox.settings_sha256(sandbox.REPO_ROOT)
    assert sandbox.session_settings_sha256(SimpleNamespace(repo=sandbox.REPO_ROOT)) == sandbox.settings_sha256()


GOOD = {"passed": True, "claude_version": "1.0", "settings_sha256": "s", "b_stack_sha256": "b",
        "probe_script_sha256": "p", "auth_mode": "direct"}


def write_record(tmp_path, rec) -> None:
    (tmp_path / "sandbox_probe.json").write_text(json.dumps(rec), encoding="utf-8")


def test_reusable_record_matches_every_field(tmp_path):
    write_record(tmp_path, GOOD)
    assert sandbox.load_reusable_probe(tmp_path, "1.0", "s", "b", script_sha256="p", auth="direct") == GOOD
    assert sandbox.load_reusable_probe(tmp_path, "1.0", "s", "b", script_sha256="p") == GOOD


@pytest.mark.parametrize("field,value", [
    ("passed", 1), ("passed", None), ("fake", True), ("claude_version", "2.0"), ("settings_sha256", "x"),
    ("b_stack_sha256", None), ("probe_script_sha256", "x"), ("auth_mode", "gateway"),
], ids=["passed-1", "passed-none", "fake", "claude", "settings", "b-stack", "script", "auth"])
def test_reusable_record_refuses_a_difference(tmp_path, field, value):
    write_record(tmp_path, {**GOOD, field: value})
    assert sandbox.load_reusable_probe(tmp_path, "1.0", "s", "b", script_sha256="p", auth="direct") is None


def test_reusable_record_defaults_to_this_hosts_script(tmp_path):
    write_record(tmp_path, {**GOOD, "probe_script_sha256": sandbox.probe_script_sha256(), "b_stack_sha256": None})
    assert sandbox.load_reusable_probe(tmp_path, "1.0", "s") is not None


@pytest.mark.parametrize("text", ["not json", "[1, 2]"])
def test_reusable_record_that_is_unreadable(tmp_path, text):
    (tmp_path / "sandbox_probe.json").write_text(text, encoding="utf-8")
    assert sandbox.load_reusable_probe(tmp_path, "1.0", "s", "b", script_sha256="p") is None
    assert sandbox.load_reusable_probe(tmp_path / "none", "1.0", "s", "b", script_sha256="p") is None


# ------------------------------------------------------------------ judging a transcript
def test_transcript_judgement_is_one_record():
    init = {"type": "system", "subtype": "init", "tools": ["Bash"], "mcp_servers": [], "model": "m"}
    text = "\n".join(f"PROBE_{n} rc=0" for n in sandbox.MUST_BE_ZERO) + "\n" + "\n".join(
        f"PROBE_{n} rc=1" for n in sandbox.MUST_FAIL)
    events = [{"type": "system", "subtype": "ui_invalidate"}, init,
              {"type": "user", "message": {"content": [{"type": "tool_result", "content": text}]}}]
    rec = sandbox.evaluate_transcript(events, "m")
    problems = sandbox.conditions.check_init(sandbox.conditions.get("B"), init, "m")
    assert rec == {"passed": not problems, "reasons": ([] if not problems else
                                                       ["init check failed: " + "; ".join(problems)]),
                   "markers": {**{n: [0] for n in sandbox.MUST_BE_ZERO}, **{n: [1] for n in sandbox.MUST_FAIL}},
                   "init_mismatches": problems, "escape_requested": False}
    assert sandbox.evaluate_transcript(events, "m", ("READ",))["reasons"][0] == (
        "READ not tested: src/tsbench/data/tasks/tasks.jsonl does not exist in the repository")


def test_transcript_judgement_without_an_init_event():
    rec = sandbox.evaluate_transcript([{"type": "system", "subtype": "other"}], "m")
    assert rec["init_mismatches"] == sandbox.conditions.check_init(sandbox.conditions.get("B"), {}, "m")
    assert rec["passed"] is False and rec["markers"] == {}


def test_paths_are_not_relative_here():
    assert os.path.isabs(str(sandbox.REPO_ROOT))


def test_a_failing_zero_marker_without_its_own_hint_gets_the_bash_hint():
    markers = {**{n: [0] for n in sandbox.MUST_BE_ZERO}, **{n: [1] for n in sandbox.MUST_FAIL}, "CTRL2": [0, 2]}
    assert sandbox.evaluate(markers, [], False) == (
        False, ["CTRL2 rc=[0, 2], expected 0 (Bash or python3 unusable inside the sandbox)"])


def test_an_untested_target_skips_only_its_own_marker():
    zero = {n: [0] for n in sandbox.MUST_BE_ZERO}
    passed, reasons = sandbox.evaluate(zero, [], False, ("VENV",))
    assert not passed
    assert reasons == ["VENV not tested: .venv/bin/python does not exist in the repository",
                       *[f"{n} missing" for n in sandbox.MUST_FAIL if n != "VENV"]]


def test_transcript_judgement_sees_an_escape_request():
    events = [{"type": "assistant", "message": {"content": [
        {"type": "tool_use", "input": {"command": "ls", "dangerouslyDisableSandbox": True}}]}}]
    rec = sandbox.evaluate_transcript(events, "m")
    assert rec["escape_requested"] is True and "a tool_use asked for dangerouslyDisableSandbox" in rec["reasons"]


def test_settings_deny_the_site_packages_of_every_base_dir(layout, monkeypatch):
    d = layout
    other = d.base.parent / "base2"
    other_site = other / "lib" / "python3.14" / "site-packages"
    other_site.mkdir(parents=True)
    monkeypatch.setattr(b_stack, "base_dirs", lambda venv: [d.base, other])
    s = render(d)["sandbox"]["filesystem"]
    assert s["denyRead"][-2:] == [str(d.base_site), str(other_site)]
    assert s["allowRead"] == [str(d.venv), str(d.base), str(other), str(d.mpl)]


def test_settings_of_a_linked_checkout_deny_its_main_checkout(tmp_path, monkeypatch):
    main = tmp_path / "main"
    main.mkdir()
    git("init", "-q", cwd=main)
    git("commit", "-q", "--allow-empty", "-m", "x", cwd=main)
    git("worktree", "add", "-q", str(tmp_path / "wt"), cwd=main)
    monkeypatch.setattr(b_stack, "base_dirs", lambda venv: [])
    s = sandbox.render_settings(tmp_path / "wt", tmp_path / "home", b_venv=tmp_path / "venv", mpl_dir=tmp_path / "m",
                                harness=[])["sandbox"]["filesystem"]
    assert s["denyRead"][:3] == [str(tmp_path / "wt"), str(main), str(tmp_path / "home")]
