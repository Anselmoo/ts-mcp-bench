"""Tests for the tsbench command table (no network, no key)."""
from __future__ import annotations

import importlib
import runpy
import subprocess
import sys

import pytest

from tsbench import cli


def _python_m(*args: str) -> subprocess.CompletedProcess:
    """Run `python -m <args>` in a new process, the way a user runs it."""
    return subprocess.run([sys.executable, "-m", *args], capture_output=True, text=True, encoding="utf-8",
                          timeout=120, check=False)


def test_usage_lists_every_command():
    text = cli.usage()
    assert all(" ".join(words) in text for words in cli.COMMANDS)


def test_resolve_takes_the_longest_command():
    assert cli.resolve(["plan", "estimate", "--plan", "x"]) == ("tsbench.plan.estimate:main", ["--plan", "x"])
    assert cli.resolve(["plan", "build", "--k", "1"]) == ("tsbench.plan.__main__:main", ["build", "--k", "1"])
    assert cli.resolve(["nonsense"]) is None


def test_unknown_command_exits_2(capsys):
    assert cli.main(["nonsense"]) == 2 and "unknown command" in capsys.readouterr().err


def test_no_arguments_prints_the_usage_and_exits_0(capsys):
    assert cli.main([]) == 0
    assert capsys.readouterr().out.rstrip() == cli.usage()


@pytest.mark.parametrize("flag", ["-h", "--help"])
def test_help_flag_prints_the_usage_and_exits_0(flag, capsys):
    assert cli.main([flag]) == 0
    assert capsys.readouterr().out.rstrip() == cli.usage()


@pytest.mark.parametrize("words", list(cli.COMMANDS), ids=lambda w: " ".join(w))
def test_every_command_resolves_to_a_main_and_has_help(words, capsys):
    module, func = cli.COMMANDS[words][0].split(":")
    assert callable(getattr(importlib.import_module(module), func))
    argv = [*words, *(["build"] if words == ("plan",) else ["views"] if words == ("report",) else []), "--help"]
    with pytest.raises(SystemExit) as e:
        cli.main(argv)
    assert e.value.code == 0
    assert "usage:" in capsys.readouterr().out


def _run_module_as_main(module: str, args: list[str], monkeypatch) -> None:
    """Run a package's __main__ in this process, as `python -m` does, so that coverage sees its lines."""
    monkeypatch.setattr(sys, "argv", ["tsbench", *args])
    runpy.run_module(module, run_name="__main__", alter_sys=True)


def test_tsbench_main_module_prints_the_command_table(monkeypatch, capsys):
    with pytest.raises(SystemExit) as e:
        _run_module_as_main("tsbench", ["--help"], monkeypatch)
    assert e.value.code == 0
    assert capsys.readouterr().out.rstrip() == cli.usage()


def test_figures_main_module_prints_its_own_options(monkeypatch, capsys):
    with pytest.raises(SystemExit) as e:
        _run_module_as_main("tsbench.figures", ["--help"], monkeypatch)
    assert e.value.code == 0
    out = capsys.readouterr().out
    assert out.startswith("usage: tsbench figures") and "--runs DIR" in out


def test_python_m_tsbench_help_in_a_new_process():
    done = _python_m("tsbench", "--help")
    assert done.returncode == 0, done.stderr
    assert done.stdout.rstrip() == cli.usage()


def test_python_m_tsbench_figures_help_in_a_new_process():
    done = _python_m("tsbench.figures", "--help")
    assert done.returncode == 0, done.stderr
    assert done.stdout.startswith("usage: tsbench figures") and "--runs DIR" in done.stdout
