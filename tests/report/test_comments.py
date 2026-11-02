"""Comments and docstrings of the report code carry no step numbers, no layout part numbers, no version tags and no
paths into a pilot/ folder (the release gate never ships one), and no report test asserts that an attribute is
absent."""
from __future__ import annotations

import ast
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCANNED = (ROOT / "src" / "tsbench" / "report", ROOT / "tests" / "report")
THIS_FILE = pathlib.Path(__file__).resolve()
# markers that do not belong in code comments: step numbers, layout parts, version tags, paths into a pilot/ folder
MARKERS = {
    "step number": re.compile(r"(?<![\w.])\(1\.(?:[1-9]|1[0-3])\)"),
    "part of a layout": re.compile(r"\bParts? [123]\b"),
    "page version": re.compile(r"\breport v\d\b|\bversion \d\b|\(v\d[:)]", re.IGNORECASE),
    "pilot folder path": re.compile(r"\bpilot/"),
}


def _files() -> list[pathlib.Path]:
    return [p for top in SCANNED for p in sorted(top.rglob("*.py")) if p.resolve() != THIS_FILE]


def _texts() -> list[pathlib.Path]:
    """The Python files and the templates, style sheets and scripts of the report."""
    templates = sorted(p for p in (SCANNED[0] / "templates").rglob("*") if p.suffix in {".j2", ".css", ".js"})
    return _files() + templates


def _line_text(path: pathlib.Path):
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if "mutmut" in line:
            continue
        yield n, line


def test_no_step_numbers_version_tags_or_pilot_paths_in_the_report_code():
    found = [f"{p.relative_to(ROOT)}:{n}: {name}" for p in _texts() for n, line in _line_text(p)
             for name, rx in MARKERS.items() if rx.search(line)]
    assert found == []


def _is_hasattr_call(node: ast.expr) -> bool:
    return isinstance(node, ast.Call) and getattr(node.func, "id", "") == "hasattr"


def _gone_checks(tree: ast.AST):
    """Every `not hasattr(...)` inside an assert: such a test checks that a name is absent, not a behaviour."""
    for assertion in (n for n in ast.walk(tree) if isinstance(n, ast.Assert)):
        for node in ast.walk(assertion.test):
            if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not) and _is_hasattr_call(node.operand):
                yield node.lineno


def test_no_report_test_asserts_that_an_attribute_is_absent():
    found = [f"{p.relative_to(ROOT)}:{n}" for p in _files()
             for n in _gone_checks(ast.parse(p.read_text(encoding="utf-8")))]
    assert found == []
