"""The exact commands, keyword arguments and messages of the B stack setup, plus the exact argv of each condition.
Nothing runs a real python, uv or claude: every call goes to a recorder."""

from __future__ import annotations

import json
import os
import subprocess

import pytest

from tsbench import conditions
from tsbench.conditions import argv as argv_mod
from tsbench.conditions import b_stack
from tsbench.conditions.b_stack import BStackError

PINS = "# python-minor: 3.14\nnumpy==2.3.1\nscipy==1.16.0\nsympy==1.14.0\nmatplotlib==3.10.3\n"
INSTALLED = {"numpy": "2.3.1", "scipy": "1.16.0", "sympy": "1.14.0", "matplotlib": "3.10.3"}
VERSION_CODE = "import platform; print(platform.python_version())"


def done(cmd, rc=0, out="", err=""):
    return subprocess.CompletedProcess(cmd, rc, out, err)


class Recorder:
    """Answers the commands of validate(); records (cmd, kw)."""

    def __init__(self, *, tanabesugano_rc=1, imports_rc=0, err=""):
        self.calls: list = []
        self.tanabesugano_rc, self.imports_rc, self.err = tanabesugano_rc, imports_rc, err

    def __call__(self, cmd, **kw):
        self.calls.append((cmd, kw))
        code = cmd[-1]
        if code == b_stack._LIST_PACKAGES:
            return done(cmd, out=json.dumps(INSTALLED))
        if code == VERSION_CODE:
            return done(cmd, out="3.14.2\n")
        if code == "import tanabesugano":
            return done(cmd, rc=self.tanabesugano_rc)
        return done(cmd, rc=self.imports_rc, err=self.err)


@pytest.fixture
def pin_file(tmp_path):
    p = tmp_path / "b-stack.txt"
    p.write_text(PINS, encoding="utf-8")
    return p


@pytest.fixture
def venv(tmp_path):
    v = tmp_path / "venv-B"
    (v / "bin").mkdir(parents=True)
    (v / "bin" / "python").write_text("", encoding="utf-8")
    return v


def test_validate_calls_in_order(venv, pin_file):
    run = Recorder()
    info = b_stack.validate(venv, pin_file, run)
    py = str(venv / "bin" / "python")
    assert run.calls == [
        ([py, "-I", "-c", VERSION_CODE], {"timeout": 60}),
        ([py, "-I", "-c", b_stack._LIST_PACKAGES], {"timeout": 120}),
        ([py, "-I", "-c", "import tanabesugano"], {"timeout": 120}),
        ([py, "-I", "-c", "import numpy, scipy, sympy, matplotlib"], {"timeout": 300}),
    ]
    assert info == {"path": str(venv), "bin": str(venv / "bin"), "python": "3.14.2",
                    "packages": dict(sorted(INSTALLED.items())), "digest": b_stack.stack_digest(PINS, INSTALLED)}


def test_validate_messages(venv, pin_file):
    with pytest.raises(BStackError) as e:
        b_stack.validate(venv, pin_file, Recorder(imports_rc=1, err="x" * 50 + "E" * 200))
    assert str(e.value) == (f"importing numpy, scipy, sympy, matplotlib fails in {venv}: " + "E" * 200)
    with pytest.raises(b_stack.ForbiddenPackageError) as e:
        b_stack.validate(venv, pin_file, Recorder(tanabesugano_rc=0))
    assert str(e.value) == f"`import tanabesugano` succeeds in {venv}; B must not have it"


def test_failing_python_messages_keep_the_tail(venv):
    tail = "y" * 10 + "Z" * 200
    with pytest.raises(BStackError) as e:
        b_stack.python_version(venv, lambda cmd, **kw: done(cmd, rc=1, err=tail))
    assert str(e.value) == f"cannot run {venv / 'bin' / 'python'}: " + "Z" * 200
    with pytest.raises(BStackError) as e:
        b_stack.installed_packages(venv, lambda cmd, **kw: done(cmd, rc=1, err=tail))
    assert str(e.value) == f"cannot list packages of {venv}: " + "Z" * 200


def test_describe_asks_the_venv_for_what_it_is_not_given(venv, pin_file, monkeypatch):
    seen = []
    monkeypatch.setattr(b_stack, "installed_packages", lambda v: seen.append(("pk", v)) or INSTALLED)
    monkeypatch.setattr(b_stack, "python_version", lambda v: seen.append(("py", v)) or "3.14.9")
    info = b_stack.describe(venv, pin_file)
    assert seen == [("pk", venv), ("py", venv)] and info["python"] == "3.14.9"
    assert b_stack.describe(venv, pin_file, "3.14.1", {})["python"] == "3.14.1"


def test_run_passes_its_keywords_on(monkeypatch):
    seen = {}
    monkeypatch.setattr(b_stack.subprocess, "run", lambda cmd, **kw: seen.update(kw) or done(cmd))
    b_stack._run(["x"], timeout=5, env={"A": "1"})
    assert seen == {"capture_output": True, "text": True, "encoding": "utf-8", "timeout": 5, "env": {"A": "1"}}


def test_base_dirs_reads_the_first_equals_sign(tmp_path):
    base = tmp_path / "a=b"
    (base / "bin").mkdir(parents=True)
    (tmp_path / "pyvenv.cfg").write_text(f"home = {base / 'bin'}\n", encoding="utf-8")
    assert base in b_stack.base_dirs(tmp_path)


# ------------------------------------------------------------------ creating the venv
def test_ensure_creates_with_exact_commands(tmp_path, pin_file, monkeypatch):
    venv = tmp_path / "a" / "b" / "venv-B"
    inner = Recorder()
    calls = []

    def run(cmd, **kw):
        if "-m" in cmd and "venv" in cmd or "pip" in cmd:
            calls.append((cmd, kw))
            if "venv" in cmd:
                (venv / "bin").mkdir(parents=True)
                (venv / "bin" / "python").write_text("", encoding="utf-8")
            return done(cmd)
        return inner(cmd, **kw)

    names = []
    monkeypatch.setattr(b_stack.shutil, "which", lambda name: names.append(name) or "/usr/bin/uv")
    monkeypatch.setattr(b_stack, "_base_python", lambda minor: f"/base/python{minor}")
    b_stack.ensure_b_stack(venv, pin_file, run=run)
    assert names == ["uv"]
    assert calls == [
        (["/base/python3.14", "-m", "venv", "--without-pip", str(venv)], {"timeout": 300}),
        (["/usr/bin/uv", "pip", "install", "--python", str(venv / "bin" / "python"), "-r", str(pin_file)],
         {"timeout": 1800}),
    ]


def test_ensure_messages_keep_the_tail(tmp_path, venv, pin_file, monkeypatch):
    monkeypatch.setattr(b_stack.shutil, "which", lambda name: "/usr/bin/uv")
    monkeypatch.setattr(b_stack, "_base_python", lambda minor: "/base/python")
    with pytest.raises(BStackError) as e:
        b_stack.ensure_b_stack(tmp_path / "v", pin_file, run=lambda cmd, **kw: done(cmd, rc=1, err="q" + "E" * 300))
    assert str(e.value) == "venv creation failed: " + "E" * 300
    bad = Recorder()

    def run(cmd, **kw):
        if "pip" in cmd:
            return done(cmd, rc=1, out="w" + "O" * 400)
        r = bad(cmd, **kw)
        return done(cmd, out=json.dumps({**INSTALLED, "numpy": "1"})) if cmd[-1] == b_stack._LIST_PACKAGES else r

    with pytest.raises(BStackError) as e:
        b_stack.ensure_b_stack(venv, pin_file, run=run)
    assert str(e.value) == "uv pip install failed: " + "O" * 400


class Uv:
    def __init__(self, found, version="3.14", install=(0, "", "")):
        self.found, self.version, self.install, self.calls = found, version, install, []

    def __call__(self, cmd, **kw):
        self.calls.append((cmd, kw))
        if cmd[1:3] == ["python", "install"]:
            return done(cmd, *self.install)
        if cmd[1:3] == ["python", "find"]:
            return done(cmd, out=f"{self.found}\n" if self.found else "")
        return done(cmd, out=self.version + "\n")


@pytest.fixture
def pythons(tmp_path, monkeypatch):
    pydir = tmp_path / "pythons"
    real = pydir / "cpython-3.14.8" / "bin" / "python3.14"
    real.parent.mkdir(parents=True)
    real.write_text("", encoding="utf-8")
    monkeypatch.setenv("TSBENCH_PYTHON_DIR", str(pydir))
    names = []
    monkeypatch.setattr(b_stack.shutil, "which", lambda name: names.append(name) or "/usr/bin/uv")
    return pydir, real, names


def test_base_python_exact_commands(pythons, monkeypatch):
    pydir, real, names = pythons
    uv = Uv(real)
    monkeypatch.setattr(b_stack, "_run", uv)
    assert b_stack._base_python("3.14") == str(real.resolve())
    env = {**os.environ, "UV_PYTHON_INSTALL_DIR": str(pydir)}
    assert names == ["uv"]
    assert uv.calls == [
        (["/usr/bin/uv", "python", "install", "--no-bin", "3.14"], {"timeout": 900, "env": env}),
        (["/usr/bin/uv", "python", "find", "--managed-python", "3.14"], {"timeout": 60, "env": env}),
        ([str(real), "-c", "import sys; print('%d.%d' % sys.version_info[:2])"], {"timeout": 60}),
    ]


def test_base_python_messages(pythons, monkeypatch):
    pydir, real, _ = pythons
    with pytest.raises(BStackError) as e:
        b_stack._base_python("")
    assert str(e.value) == "the pin file names no python minor; B's base interpreter cannot be chosen"
    monkeypatch.setattr(b_stack, "_run", Uv(None, install=(1, "o" + "U" * 300, "")))
    with pytest.raises(BStackError) as e:
        b_stack._base_python("3.14")
    assert str(e.value) == f"uv python install 3.14 into {pydir} failed: " + "U" * 300
    monkeypatch.setattr(b_stack, "_run", Uv(real, version="3.13"))
    with pytest.raises(BStackError) as e:
        b_stack._base_python("3.14")
    assert str(e.value) == f"no python 3.14 found in {pydir} (tried {real})"


def test_base_python_needs_a_successful_find(pythons, monkeypatch):
    _, real, _ = pythons

    class FindFails(Uv):
        def __call__(self, cmd, **kw):
            r = super().__call__(cmd, **kw)
            return done(cmd, rc=1, out=r.stdout) if cmd[1:3] == ["python", "find"] else r

    monkeypatch.setattr(b_stack, "_run", FindFails(real))
    with pytest.raises(BStackError, match=r"\(tried nothing\)$"):
        b_stack._base_python("3.14")


# ------------------------------------------------------------------ the CLI
def test_cli_help(capsys, monkeypatch):
    monkeypatch.setenv("COLUMNS", "300")
    with pytest.raises(SystemExit):
        b_stack.main(["--help"])
    out = " ".join(capsys.readouterr().out.split())
    assert (b_stack.__doc__ or "").splitlines()[0] in out
    assert "--venv VENV B venv (default: $TSBENCH_B_VENV or ~/.cache/tsbench/venv-B)" in out
    assert "--check validate only; never create or install" in out
    assert "--json print the description as JSON" in out


def test_cli_json_is_indented_and_sorted(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(b_stack, "ensure_b_stack", lambda venv, create: {"path": "/v", "bin": "/v/bin"})
    assert b_stack.main(["--venv", str(tmp_path / "vb"), "--json"]) == 0
    assert capsys.readouterr().out == '{\n  "bin": "/v/bin",\n  "path": "/v"\n}\n'


# ------------------------------------------------------------------ argv of each condition
def test_flags_of_each_condition():
    schema = conditions.get_answer_schema(conditions.DEFAULT_ANSWER_SCHEMA).compact
    assert conditions.get("A").flags() == ["--tools", "", "--json-schema", schema]
    assert conditions.get("B").flags(settings_path="/s") == [
        "--tools", "Bash", "--settings", "/s", "--allowedTools", "Bash", "--json-schema", schema]
    assert conditions.get("C").flags(mcp_config_path="/m", disallowed=["x", "y"]) == [
        "--tools", "", "--mcp-config", "/m", "--allowedTools", "mcp__tanabesugano__*",
        "--disallowedTools", "x", "y", "--json-schema", schema]


def test_flags_use_the_named_answer_schema():
    names = [n for n in conditions.ANSWER_SCHEMAS if n != conditions.DEFAULT_ANSWER_SCHEMA]
    other = names[0]
    assert conditions.get("A").flags(answer_schema=other)[-1] == conditions.get_answer_schema(other).compact
    assert conditions.get_answer_schema(other).compact != conditions.get_answer_schema(
        conditions.DEFAULT_ANSWER_SCHEMA).compact


def test_build_argv_whole_line():
    names = [n for n in conditions.ANSWER_SCHEMAS if n != conditions.DEFAULT_ANSWER_SCHEMA]
    out = argv_mod.build_argv(["claude"], conditions.get("C"), "claude-haiku-5-5", "low", None,
                              system_prompt_file="/p.txt", mcp_config_path="/m.json", answer_schema=names[0],
                              disallowed_tools=["t1"])
    assert out == ["claude", "-p", "--bare", "--strict-mcp-config", "--no-session-persistence",
                   "--output-format", "stream-json", "--verbose", "--system-prompt-file", "/p.txt",
                   "--max-turns", str(conditions.MAX_TURNS["C"]), "--effort", "low", "--model", "claude-haiku-5-5",
                   "--tools", "", "--mcp-config", "/m.json", "--allowedTools", "mcp__tanabesugano__*",
                   "--disallowedTools", "t1", "--json-schema", conditions.get_answer_schema(names[0]).compact]


@pytest.mark.parametrize("cond,model,gateway,expected", [
    ("C", "qwen3.8-27b", True, list(conditions.IMAGE_TOOLS)),
    ("C", "qwen3.8-27b", False, []),
    ("B", "qwen3.8-27b", True, []),
    ("C", "gemma-4-31b-it", True, []),
])
def test_disallowed_tools(cond, model, gateway, expected):
    assert conditions.disallowed_tools(cond, model, gateway) == expected
    assert conditions.IMAGE_TOOLS == ("mcp__tanabesugano__ts_plot_png", "mcp__tanabesugano__ts_emit_png")
