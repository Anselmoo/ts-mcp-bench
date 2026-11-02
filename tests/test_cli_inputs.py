"""Real-input tests for CLI subcommands that no other test runs through `tsbench.cli.main` with arguments.

`tsbench env b-stack` is the one: it is run here on folders and on a venv whose `bin/python` is a small shell script, so
the real subprocess path of the check runs. Nothing is installed, nothing is downloaded, and `--check` never creates a
stack.
"""
from __future__ import annotations

import hashlib
import json
import stat

import pytest

from tsbench import cli
from tsbench.conditions import b_stack

PIN_TEXT = b_stack.PIN_FILE.read_text(encoding="utf-8")
PINS, MINOR = b_stack.load_pins()

# A python that answers the four probes of `validate`; the package listing and the tanabesugano switch are files.
STUB = """#!/bin/sh
here=$(dirname "$0")
case "$3" in
  *importlib.metadata*) cat "$here/packages.json" ;;
  *platform*) echo "{python}" ;;
  "import tanabesugano") [ -e "$here/tanabesugano" ] ;;
  "import numpy"*) exit 0 ;;
  *) echo "unexpected probe: $3" >&2; exit 9 ;;
esac
"""


def make_venv(root, packages=None, tanabesugano=False):
    """A venv folder with a stub `bin/python`; `packages` default to the pins of the real pin file."""
    venv = root / "venv-B"
    (venv / "bin").mkdir(parents=True)
    py = venv / "bin" / "python"
    py.write_text(STUB.format(python=f"{MINOR}.0"), encoding="utf-8")
    py.chmod(py.stat().st_mode | stat.S_IXUSR)
    (venv / "bin" / "packages.json").write_text(json.dumps(PINS if packages is None else packages), encoding="utf-8")
    if tanabesugano:
        (venv / "bin" / "tanabesugano").write_text("", encoding="utf-8")
    return venv


def digest_of_pins() -> str:
    """The digest the stub venv must give: sha256 over the pin file and the sorted `name==version` listing."""
    listing = "\n".join(f"{name}=={version}" for name, version in sorted(PINS.items()))
    return hashlib.sha256((PIN_TEXT + "\n--installed--\n" + listing + "\n").encode("utf-8")).hexdigest()


def b_stack_cli(*args):
    return cli.main(["env", "b-stack", *args])


def test_check_on_an_empty_folder_fails_and_creates_nothing(tmp_path, capsys):
    venv = tmp_path / "empty"
    venv.mkdir()
    assert b_stack_cli("--check", "--venv", str(venv)) == 1
    out, err = capsys.readouterr()
    assert out == "" and err == f"b_stack: {venv} has no bin/python\n"
    assert list(venv.iterdir()) == []


def test_check_on_a_missing_folder_fails_and_does_not_make_it(tmp_path, capsys):
    venv = tmp_path / "not" / "there"
    assert b_stack_cli("--check", "--venv", str(venv)) == 1
    assert capsys.readouterr().err == f"b_stack: {venv} has no bin/python\n"
    assert not (tmp_path / "not").exists()


def test_a_venv_inside_the_repo_is_refused_before_anything_is_made(capsys):
    venv = b_stack.REPO_ROOT / "tests" / "b-venv-that-must-not-exist"
    assert b_stack_cli("--check", "--venv", str(venv)) == 1
    err = capsys.readouterr().err
    assert err.startswith(f"b_stack: B venv {venv} lies inside the repo;")
    assert not venv.exists()


def test_check_describes_a_venv_with_the_pinned_stack(tmp_path, capsys):
    venv = make_venv(tmp_path)
    assert b_stack_cli("--check", "--venv", str(venv)) == 0
    out, err = capsys.readouterr()
    digest = digest_of_pins()
    listing = ", ".join(f"{name}=={version}" for name, version in sorted(PINS.items()))
    assert err == ""
    assert out == f"B stack OK: {venv}\n  python {MINOR}.0\n  digest {digest}\n  {listing}\n"


def test_check_with_json_prints_the_description(tmp_path, capsys):
    venv = make_venv(tmp_path)
    assert b_stack_cli("--check", "--json", "--venv", str(venv)) == 0
    expected = {"path": str(venv), "bin": str(venv / "bin"), "python": f"{MINOR}.0",
                "packages": dict(sorted(PINS.items())), "digest": digest_of_pins()}
    assert capsys.readouterr().out == json.dumps(expected, indent=2, sort_keys=True) + "\n"


def test_check_names_the_package_that_differs_from_its_pin(tmp_path, capsys):
    venv = make_venv(tmp_path, packages={**PINS, "numpy": "0.0.1"})
    assert b_stack_cli("--check", "--venv", str(venv)) == 1
    err = capsys.readouterr().err
    assert err == (f"b_stack: installed packages differ from the pins: numpy: pinned {PINS['numpy']}, "
                   "installed 0.0.1\n")


def test_the_venv_option_wins_over_the_environment(tmp_path, monkeypatch, capsys):
    good = make_venv(tmp_path)
    monkeypatch.setenv("TSBENCH_B_VENV", str(tmp_path / "other"))
    assert b_stack_cli("--check", "--venv", str(good)) == 0
    assert capsys.readouterr().out.startswith(f"B stack OK: {good}\n")


def test_the_environment_names_the_venv_when_no_option_is_given(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("TSBENCH_B_VENV", str(make_venv(tmp_path)))
    assert b_stack_cli("--check", "--json") == 0
    assert json.loads(capsys.readouterr().out)["path"] == str(tmp_path / "venv-B")


@pytest.mark.parametrize("flags", [["--check"], []])
def test_a_venv_with_tanabesugano_is_never_repaired(tmp_path, flags, monkeypatch, capsys):
    monkeypatch.setattr(b_stack.shutil, "which", lambda *a, **k: None)  # `uv pip install` must never be reached
    venv = make_venv(tmp_path, tanabesugano=True)
    assert b_stack_cli(*flags, "--venv", str(venv)) == 1
    assert capsys.readouterr().err == (f"b_stack: `import tanabesugano` succeeds in {venv}; B must not have it\n")
    assert sorted(p.name for p in (venv / "bin").iterdir()) == ["packages.json", "python", "tanabesugano"]
