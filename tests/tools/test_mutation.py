"""tools/ci/mutation.sh: the mutant runs keep every fast test, the sandbox probe tests included.

mutmut runs the tests inside <copy>/mutants/, which holds no .venv. The sandbox probe checks that
<repo>/.venv/bin/python exists (sandbox.PROBE_TARGETS["VENV"]), so the fake probe tests need the venv there too.
"""
import pathlib
import re

from tsbench.conditions import sandbox

SCRIPT = pathlib.Path(__file__).resolve().parents[2] / "tools" / "ci" / "mutation.sh"


def _text():
    return SCRIPT.read_text(encoding="utf-8")


def test_no_keyword_filter_drops_tests_from_the_mutant_runs():
    found = re.search(r"deselect = \[(.*?)\]\n", _text(), re.S)
    assert found
    pytest_args = found.group(1)
    assert '"-k"' not in pytest_args  # a keyword filter drops every test whose name matches, e.g. all probe tests
    assert all(a.startswith('"--deselect=tests/') for a in re.findall(r'"[^"]*"', pytest_args))


def test_the_mutants_folder_links_the_venv_before_mutmut_runs():
    text = _text()
    link = text.index("ln -s ../.venv mutants/.venv")
    assert link < text.index(".venv/bin/mutmut run")
    assert sandbox.PROBE_TARGETS["VENV"].startswith(".venv/")
