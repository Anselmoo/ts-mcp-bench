"""Tests for `tsbench report` (src/tsbench/report/__main__.py): the words it strips, the one it refuses, and a real run
on a copy of the gateway run sets of the demo run set (fake claude)."""
from __future__ import annotations

import runpy
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tsbench.report import __main__ as report_cli
from tsbench.report import views


@pytest.fixture
def seen(monkeypatch):
    """Replace views.main with a stand-in that records its arguments and returns 7."""
    calls: list[list[str]] = []
    monkeypatch.setattr(views, "main", lambda argv: calls.append(list(argv)) or 7)
    return calls


@pytest.fixture
def demo(tmp_path, demo_runs_root):
    """A copy of the three gateway run sets of the demo run set (the views are written next to the runs, so the
    demo run set itself stays untouched)."""
    dst = tmp_path / "demo"
    shutil.copytree(demo_runs_root / "demo-gateway", dst)
    return dst


def _n_runs(run_set: Path) -> int:
    return len(list(run_set.rglob("*-k[0-9]*.jsonl")))


def test_unknown_subcommand_exits_2_names_it_and_lists_the_others(capsys):
    assert report_cli.main(["gallery", "--runs", "x"]) == 2
    out, err = capsys.readouterr()
    assert out == ""
    assert err.startswith("tsbench report: unknown subcommand 'gallery' (views, full, gallery, comparison, dashboard, ")
    assert err.rstrip().endswith("coverage, artifacts)")


def test_unknown_subcommand_does_not_reach_the_views(seen, capsys):
    assert report_cli.main(["nonsense"]) == 2
    assert seen == []
    assert "unknown subcommand 'nonsense'" in capsys.readouterr().err


@pytest.mark.parametrize("word", ["render", "views"])
def test_render_and_views_words_are_dropped_before_the_views_main(word, seen):
    assert report_cli.main([word, "--runs", "a", "--split", "pilot"]) == 7
    assert seen == [["--runs", "a", "--split", "pilot"]]


@pytest.mark.parametrize("argv", [["--runs", "a"], ["-h"], ["--help"], []])
def test_options_and_help_go_to_the_views_main_unchanged(argv, seen):
    assert report_cli.main(argv) == 7
    assert seen == [argv]


def test_without_arguments_it_reads_sys_argv(monkeypatch, seen):
    monkeypatch.setattr(sys, "argv", ["tsbench", "render", "--runs", "b"])
    assert report_cli.main() == 7
    assert seen == [["--runs", "b"]]
    monkeypatch.setattr(sys, "argv", ["tsbench", "nonsense"])
    assert report_cli.main() == 2


def test_views_writes_one_index_per_run_set_and_an_overview(demo, capsys):
    out = demo / "overview" / "overview.html"
    assert report_cli.main(["views", "--runs", str(demo), "--out", str(out)]) == 0
    lines = capsys.readouterr().out.splitlines()
    names = sorted(p.name for p in demo.iterdir() if (p / "run_set.json").is_file())
    assert names == ["gemma-4-31b-it-condition-A", "gemma-4-31b-it-condition-B", "gemma-4-31b-it-condition-C"]
    for name in names:
        index = demo / name / "views" / "INDEX.html"
        n = _n_runs(demo / name)
        assert index.is_file() and n >= 1
        assert f"{name}: views written: {n}  index: {index}" in lines
        assert len(list((demo / name / "views").rglob("*.html"))) == n + 1  # one view per run and the index
    assert lines[-1] == f"overview: {out}"
    page = out.read_text(encoding="utf-8")
    for name in names:
        assert f'href="../{name}/views/INDEX.html"' in page


def test_render_is_an_alias_of_views(demo, tmp_path, capsys):
    other = tmp_path / "again"
    shutil.copytree(demo, other)
    assert report_cli.main(["render", "--runs", str(demo)]) == 0
    assert report_cli.main(["views", "--runs", str(other)]) == 0
    a = sorted(p.relative_to(demo) for p in demo.rglob("views/**/*.html"))
    b = sorted(p.relative_to(other) for p in other.rglob("views/**/*.html"))
    assert a == b and len(a) == _n_runs(demo) + 3  # a view per run and an index per run set
    for rel in a:
        assert (demo / rel).read_text(encoding="utf-8").replace(str(demo), "R") == \
            (other / rel).read_text(encoding="utf-8").replace(str(other), "R")
    capsys.readouterr()


def test_a_missing_folder_exits_2_before_anything_is_written(tmp_path, capsys):
    assert report_cli.main(["views", "--runs", str(tmp_path / "nope")]) == 2
    assert capsys.readouterr().err == f"not a directory: {tmp_path / 'nope'}\n"
    assert list(tmp_path.iterdir()) == []


def test_module_run_as_main_exits_with_the_return_value(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tsbench", "nonsense"])
    monkeypatch.delitem(sys.modules, "tsbench.report.__main__")  # runpy runs the file afresh, as `python -m` does
    with pytest.raises(SystemExit) as e:
        runpy.run_module("tsbench.report", run_name="__main__", alter_sys=True)
    assert e.value.code == 2
    assert "unknown subcommand 'nonsense'" in capsys.readouterr().err


def test_python_m_tsbench_report_in_a_new_process(demo):
    bad = subprocess.run([sys.executable, "-m", "tsbench.report", "nonsense"], capture_output=True, text=True,
                         encoding="utf-8", timeout=120, check=False)
    assert bad.returncode == 2 and "unknown subcommand 'nonsense'" in bad.stderr and bad.stdout == ""
    good = subprocess.run([sys.executable, "-m", "tsbench.report", "render", "--runs", str(demo)],
                          capture_output=True, text=True, encoding="utf-8", timeout=120, check=False)
    assert good.returncode == 0, good.stderr
    assert good.stdout.count("views written: ") == 3
    for name in ("A", "B", "C"):
        n = _n_runs(demo / f"gemma-4-31b-it-condition-{name}")
        assert f"gemma-4-31b-it-condition-{name}: views written: {n} " in good.stdout
