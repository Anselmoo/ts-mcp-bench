"""Tests for tsbench.conditions.b_stack (paths, pin parsing, digest, validation, creation, CLI).

Nothing here runs a real python, uv or pip: subprocess calls go through a fake `run` or a patched `_run`.
"""
import hashlib
import json
import pathlib
import subprocess

import pytest

from tsbench.conditions import b_stack
from tsbench.conditions.b_stack import BStackError, ForbiddenPackageError

PINS = "# python-minor: 3.14\nnumpy==2.3.1\nscipy==1.16.0\nsympy==1.14.0\nmatplotlib==3.10.3\nMy_Pkg==1.0\n"
INSTALLED = {"numpy": "2.3.1", "scipy": "1.16.0", "sympy": "1.14.0", "matplotlib": "3.10.3", "my-pkg": "1.0"}


def done(cmd, rc=0, out="", err=""):
    return subprocess.CompletedProcess(cmd, rc, out, err)


def fake_run(packages=None, pyver="3.14.2", tanabesugano=False, imports_ok=True, calls=None):
    """A stand-in for b_stack._run that answers the four probes validate() makes."""
    packages = INSTALLED if packages is None else packages

    def run(cmd, **kw):
        if calls is not None:
            calls.append(cmd)
        code = cmd[-1]
        if "importlib.metadata" in code:
            return done(cmd, out=json.dumps({k.upper(): v for k, v in packages.items()}))
        if "platform" in code:
            return done(cmd, out=pyver + "\n")
        if code == "import tanabesugano":
            return done(cmd, rc=0 if tanabesugano else 1)
        if code.startswith("import numpy"):
            return done(cmd, rc=0 if imports_ok else 1, err="" if imports_ok else "ImportError: no scipy")
        raise AssertionError(f"unexpected command {cmd}")
    return run


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


# ------------------------------------------------------------------ names and locations
def test_normalize_package_name_lowercases_and_folds_separators():
    assert b_stack.normalize_package_name("Foo_Bar.baz--Qux") == "foo-bar-baz-qux"


def test_b_venv_dir_prefers_override_then_env_then_xdg_then_home(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    env = {"TSBENCH_B_VENV": str(tmp_path / "from-env"), "XDG_CACHE_HOME": str(tmp_path / "xdg"),
           "HOME": str(tmp_path / "h")}
    assert b_stack.b_venv_dir(env, str(tmp_path / "flag"), repo) == tmp_path / "flag"
    assert b_stack.b_venv_dir(env, None, repo) == tmp_path / "from-env"
    del env["TSBENCH_B_VENV"]
    assert b_stack.b_venv_dir(env, None, repo) == tmp_path / "xdg" / "tsbench" / "venv-B"
    del env["XDG_CACHE_HOME"]
    assert b_stack.b_venv_dir(env, None, repo) == tmp_path / "h" / ".cache" / "tsbench" / "venv-B"


def test_b_venv_dir_refuses_a_path_inside_the_repo(tmp_path):
    with pytest.raises(BStackError, match="lies inside the repo"):
        b_stack.b_venv_dir({}, str(tmp_path / "repo" / "venv"), tmp_path / "repo")


def test_b_venv_dir_default_uses_the_process_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("TSBENCH_B_VENV", str(tmp_path / "envvenv"))
    assert b_stack.b_venv_dir(repo=tmp_path / "repo") == tmp_path / "envvenv"


def test_bin_and_python_of_are_under_the_venv(tmp_path):
    assert b_stack.bin_dir(tmp_path / "v") == tmp_path / "v" / "bin"
    assert b_stack.python_of(tmp_path / "v") == tmp_path / "v" / "bin" / "python"


def test_mpl_dir_and_python_dir_follow_their_env_vars_then_the_cache(tmp_path):
    assert b_stack.mpl_dir({"TSBENCH_MPLCONFIGDIR": str(tmp_path / "m")}) == tmp_path / "m"
    assert b_stack.mpl_dir({"XDG_CACHE_HOME": str(tmp_path / "x")}) == tmp_path / "x" / "tsbench" / "matplotlib"
    assert b_stack.mpl_dir({"HOME": str(tmp_path / "h")}) == tmp_path / "h" / ".cache" / "tsbench" / "matplotlib"
    assert b_stack.python_dir({"TSBENCH_PYTHON_DIR": str(tmp_path / "p")}) == tmp_path / "p"
    assert b_stack.python_dir({"XDG_CACHE_HOME": str(tmp_path / "x")}) == tmp_path / "x" / "tsbench" / "python"
    assert b_stack.python_dir({"HOME": str(tmp_path / "h")}) == tmp_path / "h" / ".cache" / "tsbench" / "python"


def test_mpl_dir_and_python_dir_default_to_the_process_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("TSBENCH_MPLCONFIGDIR", str(tmp_path / "m"))
    monkeypatch.setenv("TSBENCH_PYTHON_DIR", str(tmp_path / "p"))
    assert b_stack.mpl_dir() == tmp_path / "m"
    assert b_stack.python_dir() == tmp_path / "p"


def test_base_dirs_reads_home_from_pyvenv_cfg(tmp_path):
    real = tmp_path / "cpython-3.14.8"
    (real / "bin").mkdir(parents=True)
    link = tmp_path / "cpython-3.14"
    link.symlink_to(real)
    v = tmp_path / "v"
    v.mkdir()
    (v / "pyvenv.cfg").write_text(f"version = 3.14.8\nhome = {link}/bin\n", encoding="utf-8")
    assert b_stack.base_dirs(v) == [link, real]                       # as written, then resolved
    (v / "pyvenv.cfg").write_text(f"home = {real}\n", encoding="utf-8")
    assert b_stack.base_dirs(v) == [real]                             # no `bin` suffix, nothing to resolve


def test_base_dirs_is_empty_without_a_cfg_or_a_home_line(tmp_path):
    assert b_stack.base_dirs(tmp_path / "missing") == []
    (tmp_path / "pyvenv.cfg").write_text("version = 3.14\nhome =\n", encoding="utf-8")
    assert b_stack.base_dirs(tmp_path) == []


# ------------------------------------------------------------------ pins
def test_parse_pins_normalises_names_and_reads_the_python_minor():
    pins, minor = b_stack.parse_pins(PINS)
    assert minor == "3.14"
    assert pins == {"numpy": "2.3.1", "scipy": "1.16.0", "sympy": "1.14.0", "matplotlib": "3.10.3", "my-pkg": "1.0"}


def test_parse_pins_without_a_minor_returns_none():
    _, minor = b_stack.parse_pins("# only a comment\n\nnumpy==1\nscipy==1\nsympy==1\nmatplotlib==1\n")
    assert minor is None


@pytest.mark.parametrize("text, message", [
    ("numpy>=2\n", r"line 1: 'numpy>=2' is not an exact name==version pin"),
    ("numpy==1\nnumpy==2\n", "line 2: numpy pinned twice"),
    ("numpy==1\nTanabeSugano==0.1\n", "line 2: tanabesugano must never be in the B stack"),
    ("numpy==1\nscipy==1\nsympy==1\n", "does not pin matplotlib"),
])
def test_parse_pins_rejects_bad_files(text, message):
    with pytest.raises(BStackError, match=message):
        b_stack.parse_pins(text)


def test_load_pins_reads_the_file_and_reports_a_missing_one(pin_file, tmp_path):
    assert b_stack.load_pins(pin_file)[1] == "3.14"
    with pytest.raises(BStackError, match="cannot read"):
        b_stack.load_pins(tmp_path / "nope.txt")


def test_the_real_pin_file_is_valid_and_has_no_tanabesugano():
    pins, minor = b_stack.load_pins()
    assert set(b_stack.REQUIRED_IMPORTS) <= set(pins) and "tanabesugano" not in pins
    assert minor and minor.count(".") == 1


# ------------------------------------------------------------------ digest
def test_stack_digest_is_sha256_over_pins_and_the_sorted_normalised_listing():
    pkgs = {"Zeta_Pkg": "2", "alpha": "1"}
    expected = hashlib.sha256(b"pins\n--installed--\nalpha==1\nzeta-pkg==2\n").hexdigest()
    assert b_stack.stack_digest("pins", pkgs) == expected
    assert b_stack.stack_digest("pins", {"alpha": "1", "zeta-pkg": "2"}) == expected      # order does not matter
    assert b_stack.stack_digest("pins!", pkgs) != expected
    assert b_stack.stack_digest("pins", {**pkgs, "alpha": "1.1"}) != expected


# ------------------------------------------------------------------ probes
def test_installed_packages_normalises_names(venv):
    run = fake_run({"My_Pkg": "1.0", "numpy": "2"})
    assert b_stack.installed_packages(venv, run) == {"my-pkg": "1.0", "numpy": "2"}


def test_installed_packages_reports_a_failing_python(venv):
    run = lambda cmd, **kw: done(cmd, rc=1, err="boom")      # noqa: E731
    with pytest.raises(BStackError, match=r"cannot list packages of .*: boom"):
        b_stack.installed_packages(venv, run)


def test_python_version_strips_and_reports_failure(venv):
    assert b_stack.python_version(venv, fake_run(pyver="3.14.8")) == "3.14.8"
    with pytest.raises(BStackError, match="cannot run .*bin/python: dead"):
        b_stack.python_version(venv, lambda cmd, **kw: done(cmd, rc=2, err="dead"))


def test_run_helper_captures_text_output():
    r = b_stack._run([b_stack.sys.executable, "-c", "print('hi')"])
    assert (r.returncode, r.stdout) == (0, "hi\n")


# ------------------------------------------------------------------ validate
def test_validate_describes_a_matching_venv(venv, pin_file):
    info = b_stack.validate(venv, pin_file, fake_run())
    assert info["path"] == str(venv) and info["bin"] == str(venv / "bin") and info["python"] == "3.14.2"
    assert info["packages"] == dict(sorted(INSTALLED.items()))
    assert info["digest"] == b_stack.stack_digest(PINS, INSTALLED)


def test_validate_runs_every_probe_with_isolated_python(venv, pin_file):
    calls = []
    b_stack.validate(venv, pin_file, fake_run(calls=calls))
    assert all(c[:2] == [str(venv / "bin" / "python"), "-I"] for c in calls)
    assert calls[-1][-1] == "import numpy, scipy, sympy, matplotlib"


def test_validate_needs_a_python_in_the_venv(tmp_path, pin_file):
    with pytest.raises(BStackError, match="has no bin/python"):
        b_stack.validate(tmp_path / "empty", pin_file, fake_run())


def test_validate_rejects_the_wrong_python_minor(venv, pin_file):
    with pytest.raises(BStackError, match=r"python 3\.13\.1 in .*, the pin file wants 3\.14"):
        b_stack.validate(venv, pin_file, fake_run(pyver="3.13.1"))


def test_validate_names_every_package_that_differs_from_its_pin(venv, pin_file):
    have = {**INSTALLED, "numpy": "2.0.0"}
    del have["sympy"]
    with pytest.raises(BStackError) as e:
        b_stack.validate(venv, pin_file, fake_run(have))
    assert "numpy: pinned 2.3.1, installed 2.0.0" in str(e.value)
    assert "sympy: pinned 1.14.0, installed missing" in str(e.value)
    assert "scipy" not in str(e.value)


def test_validate_flags_an_installed_tanabesugano_before_anything_else(venv, pin_file):
    with pytest.raises(ForbiddenPackageError, match="tanabesugano 0.1 is installed"):
        b_stack.validate(venv, pin_file, fake_run({**INSTALLED, "tanabesugano": "0.1"}))


def test_validate_flags_a_tanabesugano_that_imports(venv, pin_file):
    with pytest.raises(ForbiddenPackageError, match="`import tanabesugano` succeeds"):
        b_stack.validate(venv, pin_file, fake_run(tanabesugano=True))


def test_validate_reports_a_failing_required_import(venv, pin_file):
    with pytest.raises(BStackError, match="importing numpy, scipy, sympy, matplotlib fails .*no scipy"):
        b_stack.validate(venv, pin_file, fake_run(imports_ok=False))


def test_describe_computes_missing_parts_itself(venv, pin_file, monkeypatch):
    monkeypatch.setattr(b_stack, "installed_packages", lambda v, run=None: {"numpy": "1"})
    monkeypatch.setattr(b_stack, "python_version", lambda v, run=None: "3.14.0")
    info = b_stack.describe(venv, pin_file)
    assert info["python"] == "3.14.0" and info["packages"] == {"numpy": "1"}
    assert info["digest"] == b_stack.stack_digest(PINS, {"numpy": "1"})


def test_digest_if_present_returns_the_digest_or_none(venv, pin_file, monkeypatch):
    monkeypatch.setattr(b_stack, "validate", lambda v, pf: {"digest": "feed"})
    assert b_stack.digest_if_present(venv, pin_file) == "feed"

    def invalid(v, pf):
        raise BStackError("wrong pins")

    monkeypatch.setattr(b_stack, "validate", invalid)
    assert b_stack.digest_if_present(venv, pin_file) is None


def test_digest_if_present_is_none_for_a_missing_venv(tmp_path, pin_file):
    assert b_stack.digest_if_present(tmp_path / "none", pin_file) is None       # no bin/python: nothing is run


# ------------------------------------------------------------------ _base_python
class FakeUv:
    """Answers `uv python install` and `uv python find` for _base_python."""

    def __init__(self, found, install_rc=0, version="3.14"):
        self.found, self.install_rc, self.version, self.calls = found, install_rc, version, []

    def __call__(self, cmd, **kw):
        self.calls.append((cmd, kw))
        if cmd[:3] == ["/usr/bin/uv", "python", "install"]:
            return done(cmd, rc=self.install_rc, err="no network")
        if cmd[:3] == ["/usr/bin/uv", "python", "find"]:
            return done(cmd, out=f"{self.found}\n" if self.found else "")
        return done(cmd, out=self.version + "\n")                    # the candidate's own `sys.version_info` probe


@pytest.fixture
def uv_env(tmp_path, monkeypatch):
    pydir = tmp_path / "pythons"
    real = pydir / "cpython-3.14.8" / "bin"
    real.mkdir(parents=True)
    (real / "python3.14").write_text("", encoding="utf-8")
    link = pydir / "cpython-3.14"
    link.symlink_to(pydir / "cpython-3.14.8")
    monkeypatch.setenv("TSBENCH_PYTHON_DIR", str(pydir))
    monkeypatch.setattr(b_stack.shutil, "which", lambda name: "/usr/bin/uv")
    return pydir, link / "bin" / "python3.14", real / "python3.14"


def test_base_python_returns_the_resolved_uv_managed_interpreter(uv_env, monkeypatch):
    pydir, via_link, real = uv_env
    uv = FakeUv(via_link)
    monkeypatch.setattr(b_stack, "_run", uv)
    assert b_stack._base_python("3.14") == str(real)                  # the minor-version link is resolved away
    install_cmd, install_kw = uv.calls[0]
    assert install_cmd == ["/usr/bin/uv", "python", "install", "--no-bin", "3.14"]
    assert install_kw["env"]["UV_PYTHON_INSTALL_DIR"] == str(pydir)


def test_base_python_needs_a_pinned_minor_and_uv(uv_env, monkeypatch):
    with pytest.raises(BStackError, match="names no python minor"):
        b_stack._base_python(None)
    monkeypatch.setattr(b_stack.shutil, "which", lambda name: None)
    with pytest.raises(BStackError, match="uv not found on PATH"):
        b_stack._base_python("3.14")


def test_base_python_reports_a_failed_install(uv_env, monkeypatch):
    monkeypatch.setattr(b_stack, "_run", FakeUv(None, install_rc=1))
    with pytest.raises(BStackError, match=r"uv python install 3\.14 into .* failed: no network"):
        b_stack._base_python("3.14")


def test_base_python_ignores_an_interpreter_outside_the_cache(uv_env, tmp_path, monkeypatch):
    outside = tmp_path / "elsewhere" / "python3.14"
    outside.parent.mkdir()
    outside.write_text("", encoding="utf-8")
    monkeypatch.setattr(b_stack, "_run", FakeUv(outside))
    with pytest.raises(BStackError, match=r"no python 3\.14 found in .* \(tried nothing\)"):
        b_stack._base_python("3.14")


def test_base_python_rejects_an_interpreter_of_another_minor(uv_env, monkeypatch):
    _, via_link, _ = uv_env
    monkeypatch.setattr(b_stack, "_run", FakeUv(via_link, version="3.13"))
    with pytest.raises(BStackError, match=r"no python 3\.14 found .*cpython-3\.14/bin/python3\.14"):
        b_stack._base_python("3.14")


def test_base_python_skips_a_candidate_that_vanished(uv_env, monkeypatch):
    pydir, _, _ = uv_env
    gone = pydir / "cpython-3.14.8" / "bin" / "gone"
    monkeypatch.setattr(b_stack, "_run", FakeUv(gone))
    with pytest.raises(BStackError, match="no python 3.14 found"):
        b_stack._base_python("3.14")


# ------------------------------------------------------------------ ensure_b_stack
def test_ensure_returns_a_valid_venv_without_creating_anything(venv, pin_file):
    calls = []
    info = b_stack.ensure_b_stack(venv, pin_file, run=fake_run(calls=calls))
    assert info["digest"] == b_stack.stack_digest(PINS, INSTALLED)
    assert not any("install" in c or "venv" in c for c in calls)


def test_ensure_never_repairs_a_forbidden_package(venv, pin_file):
    with pytest.raises(ForbiddenPackageError):
        b_stack.ensure_b_stack(venv, pin_file, run=fake_run(tanabesugano=True))


def test_ensure_with_create_false_raises_the_validation_error(tmp_path, pin_file):
    with pytest.raises(BStackError, match="has no bin/python"):
        b_stack.ensure_b_stack(tmp_path / "none", pin_file, create=False, run=fake_run())


def test_ensure_creates_the_venv_and_installs_the_pins_from_outside(tmp_path, pin_file, monkeypatch):
    venv = tmp_path / "cache" / "venv-B"
    calls = []
    inner = fake_run()

    def run(cmd, **kw):
        if "venv" in cmd:
            calls.append(cmd)
            (venv / "bin").mkdir(parents=True)
            (venv / "bin" / "python").write_text("", encoding="utf-8")
            return done(cmd)
        if "pip" in cmd:
            calls.append(cmd)
            return done(cmd)
        return inner(cmd, **kw)

    monkeypatch.setattr(b_stack.shutil, "which", lambda name: "/usr/bin/uv")
    monkeypatch.setattr(b_stack, "_base_python", lambda minor: f"/base/python{minor}")
    info = b_stack.ensure_b_stack(venv, pin_file, run=run)
    assert calls[0] == ["/base/python3.14", "-m", "venv", "--without-pip", str(venv)]
    assert calls[1] == ["/usr/bin/uv", "pip", "install", "--python", str(venv / "bin" / "python"), "-r", str(pin_file)]
    assert info["path"] == str(venv) and info["digest"] == b_stack.stack_digest(PINS, INSTALLED)


def test_ensure_reinstalls_into_an_existing_venv_with_wrong_pins(venv, pin_file, monkeypatch):
    state = {"installed": False}
    old = {**INSTALLED, "numpy": "1.0"}

    def run(cmd, **kw):
        if "pip" in cmd:
            state["installed"] = True
            return done(cmd)
        return fake_run(INSTALLED if state["installed"] else old)(cmd, **kw)

    monkeypatch.setattr(b_stack.shutil, "which", lambda name: "/usr/bin/uv")
    monkeypatch.setattr(b_stack, "_base_python", lambda minor: pytest.fail("the venv exists; no base python needed"))
    info = b_stack.ensure_b_stack(venv, pin_file, run=run)
    assert state["installed"] and info["packages"]["numpy"] == "2.3.1"


def test_ensure_needs_uv_to_repair(venv, pin_file, monkeypatch):
    monkeypatch.setattr(b_stack.shutil, "which", lambda name: None)
    with pytest.raises(BStackError, match="uv not found on PATH; it installs the B stack"):
        b_stack.ensure_b_stack(venv, pin_file, run=fake_run({**INSTALLED, "numpy": "1"}))


def test_ensure_reports_a_failed_venv_creation(tmp_path, pin_file, monkeypatch):
    monkeypatch.setattr(b_stack.shutil, "which", lambda name: "/usr/bin/uv")
    monkeypatch.setattr(b_stack, "_base_python", lambda minor: "/base/python")
    run = lambda cmd, **kw: done(cmd, rc=1, err="no ensurepip")      # noqa: E731
    with pytest.raises(BStackError, match="venv creation failed: no ensurepip"):
        b_stack.ensure_b_stack(tmp_path / "v", pin_file, run=run)


def test_ensure_reports_a_failed_install(venv, pin_file, monkeypatch):
    monkeypatch.setattr(b_stack.shutil, "which", lambda name: "/usr/bin/uv")
    inner = fake_run({**INSTALLED, "numpy": "1"})

    def run(cmd, **kw):
        return done(cmd, rc=1, err="resolver says no") if "pip" in cmd else inner(cmd, **kw)

    with pytest.raises(BStackError, match="uv pip install failed: resolver says no"):
        b_stack.ensure_b_stack(venv, pin_file, run=run)


def test_ensure_defaults_to_the_configured_venv_location(tmp_path, pin_file, monkeypatch):
    monkeypatch.setenv("TSBENCH_B_VENV", str(tmp_path / "configured"))
    with pytest.raises(BStackError, match=r"configured has no bin/python"):
        b_stack.ensure_b_stack(None, pin_file, create=False, run=fake_run())


# ------------------------------------------------------------------ CLI
def test_main_prints_a_summary_and_passes_the_check_flag(tmp_path, capsys, monkeypatch):
    seen = {}
    info = {"path": "/v", "python": "3.14.2", "digest": "ab" * 32, "packages": {"numpy": "2.3.1", "scipy": "1.16.0"}}

    def ensure(venv, create):
        seen.update(venv=venv, create=create)
        return info

    monkeypatch.setattr(b_stack, "ensure_b_stack", ensure)
    assert b_stack.main(["--venv", str(tmp_path / "vb"), "--check"]) == 0
    assert seen == {"venv": tmp_path / "vb", "create": False}
    out = capsys.readouterr().out
    assert out == f"B stack OK: /v\n  python 3.14.2\n  digest {'ab' * 32}\n  numpy==2.3.1, scipy==1.16.0\n"
    b_stack.main(["--venv", str(tmp_path / "vb")])
    assert seen["create"] is True


def test_main_json_prints_sorted_keys(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(b_stack, "ensure_b_stack", lambda venv, create: {"path": "/v", "bin": "/v/bin"})
    assert b_stack.main(["--venv", str(tmp_path / "vb"), "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == {"bin": "/v/bin", "path": "/v"}


def test_main_returns_one_and_names_the_problem_on_stderr(tmp_path, capsys, monkeypatch):
    def ensure(venv, create):
        raise BStackError("uv not found")

    monkeypatch.setattr(b_stack, "ensure_b_stack", ensure)
    assert b_stack.main(["--venv", str(tmp_path / "vb")]) == 1
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "b_stack: uv not found\n"


def test_main_rejects_a_venv_inside_the_repo(capsys):
    inside = pathlib.Path(b_stack.REPO_ROOT) / "venv-B-test"
    assert b_stack.main(["--venv", str(inside)]) == 1
    assert "lies inside the repo" in capsys.readouterr().err


def test_module_runs_as_a_script_and_exits_with_the_code_of_main(tmp_path, monkeypatch, capsys):
    import runpy
    import sys

    monkeypatch.setattr(sys, "argv", ["b_stack", "--check", "--venv", str(tmp_path / "no-venv")])
    with pytest.warns(RuntimeWarning):
        with pytest.raises(SystemExit) as e:
            runpy.run_module("tsbench.conditions.b_stack", run_name="__main__")
    assert e.value.code == 1 and capsys.readouterr().err.startswith("b_stack: ")
