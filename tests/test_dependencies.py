"""pyproject.toml and uv.lock: the lint, mutation and trace tools are optional extras, never runtime dependencies."""
from __future__ import annotations

import pathlib
import re
import tomllib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"
LOCK = ROOT / "uv.lock"

# extra -> requirement strings that must be listed there, with the lower bound a spec must keep
EXTRAS = {
    "test": {"websockets": None},  # tests/report/test_motion.py drives Chrome over its WebSocket
    "lint": {"ruff": None, "ty": None},
    "mutation": {"mutmut": ">=3.8"},
    "trace": {"viztracer": ">=1.1"},
}
DEV_TOOLS = ("ruff", "ty", "mutmut", "viztracer")


def requirement_name(spec: str) -> str:
    """The distribution name of a PEP 508 requirement string, lower case."""
    return re.split(r"[<>=!~\[; ]", spec.strip(), maxsplit=1)[0].lower()


@pytest.fixture(scope="module")
def project() -> dict:
    with PYPROJECT.open("rb") as handle:
        return tomllib.load(handle)["project"]


@pytest.mark.parametrize("extra", sorted(EXTRAS))
def test_extra_exists(project, extra):
    assert extra in project.get("optional-dependencies", {}), f"no extra {extra!r}"


@pytest.mark.parametrize("extra", sorted(EXTRAS))
def test_extra_lists_its_tools(project, extra):
    specs = project["optional-dependencies"].get(extra, [])
    by_name = {requirement_name(spec): spec for spec in specs}
    for name, bound in EXTRAS[extra].items():
        assert name in by_name, f"{name!r} missing from extra {extra!r}"
        if bound is not None:
            assert bound in by_name[name], f"{by_name[name]!r} does not keep the lower bound {bound!r}"


def test_runtime_dependencies_have_no_dev_tools(project):
    names = {requirement_name(spec) for spec in project.get("dependencies", [])}
    leaked = sorted(names & set(DEV_TOOLS))
    assert not leaked, f"dev tools in [project] dependencies: {leaked}"


def test_lock_file_resolves_the_dev_tool_extras():
    with LOCK.open("rb") as handle:
        packages = {pkg["name"] for pkg in tomllib.load(handle)["package"]}
    missing = sorted(set(DEV_TOOLS) - packages)
    assert not missing, f"not in uv.lock: {missing}"
