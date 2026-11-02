"""Where tests live: all of them under tests/, none in the package, and the wheel carries none.

tests/ mirrors src/tsbench/ (tests/tools/ mirrors tools/ci/). The layer rule scans the package, not the tests.
"""
from __future__ import annotations

import importlib.util
import pathlib
import shutil
import subprocess
import zipfile

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "tsbench"
TESTS = ROOT / "tests"
# tests/<name>/ whose counterpart is not a folder of the package
COUNTERPART = {"tools": ROOT / "tools" / "ci"}
NOT_MIRRORS = {"fixtures", "__pycache__"}


def _without_caches(paths):
    return sorted(p for p in paths if "__pycache__" not in p.parts)


def test_no_test_module_or_conftest_under_src():
    found = _without_caches(p.relative_to(ROOT) for pattern in ("test_*.py", "conftest.py")
                            for p in (ROOT / "src").rglob(pattern))
    assert found == []


def test_every_test_folder_mirrors_a_source_folder():
    missing = []
    for path in _without_caches(TESTS.rglob("test_*.py")):
        rel = path.relative_to(TESTS)
        if rel.parts[0] in NOT_MIRRORS or len(rel.parts) == 1:
            continue  # tests/fixtures is data; tests/test_*.py are repository-wide checks
        top, *below = rel.parts[:-1]
        mirror = (COUNTERPART[top] if top in COUNTERPART else PACKAGE / top).joinpath(*below)
        if not mirror.is_dir():
            missing.append(f"{rel.as_posix()}: no folder {mirror.relative_to(ROOT).as_posix()}")
    assert missing == []


def test_the_tests_folder_has_tests_for_the_tools_and_the_package():
    assert _without_caches((TESTS / "tools").glob("test_*.py"))
    assert _without_caches((TESTS / "run").glob("test_*.py"))


def _layers():
    spec = importlib.util.spec_from_file_location("layers_under_test", TESTS / "test_layers.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_layer_rule_scans_the_package_and_not_the_tests():
    layers = _layers()
    assert layers.ROOT == PACKAGE
    names = [name for name, _ in layers.modules()]
    assert len(names) > 40 and "tsbench.run.runner" in names
    assert not [n for n in names if n.split(".")[1:2] == ["tests"] or ".test_" in n or n.endswith(".conftest")]


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv is not installed")
def test_the_wheel_contains_no_test_module(tmp_path):
    project = tmp_path / "project"  # a copy, so that no build/ folder left from an earlier build leaks in
    project.mkdir()
    for name in ("pyproject.toml", "README.md", "LICENSE"):
        shutil.copy(ROOT / name, project / name)
    shutil.copytree(ROOT / "src", project / "src", ignore=shutil.ignore_patterns("__pycache__", "*.egg-info"))
    out = subprocess.run(["uv", "build", "--wheel", "-o", str(tmp_path / "wheel")], cwd=project, capture_output=True,
                         text=True, timeout=300, encoding="utf-8")
    assert out.returncode == 0, out.stderr[-2000:]
    (wheel,) = (tmp_path / "wheel").glob("*.whl")
    names = zipfile.ZipFile(wheel).namelist()
    assert any(n == "tsbench/run/runner.py" for n in names)  # the wheel is the real package
    bad = [n for n in names if pathlib.PurePosixPath(n).name.startswith("test_")
           or pathlib.PurePosixPath(n).name == "conftest.py"]
    assert bad == []
