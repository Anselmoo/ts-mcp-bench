"""Tests for tools/expected-versions.txt: the file parses, and its comments and blank lines are ignored.

No network, no model call, no key.
"""
from __future__ import annotations

import re

from tsbench.run import doctor, runner

EXPECTED = runner.REPO_ROOT / "tools" / "expected-versions.txt"


def test_expected_versions_file_parses():
    exp = doctor.load_expected(EXPECTED)
    assert set(exp) >= {"claude", "python", "tanabesugano"}
    assert exp["tanabesugano"] == runner.REQUIRED_TANABESUGANO
    assert exp["claude"][0].isdigit() and exp["python"].count(".") == 1
    # a lock, not a hard pin: every entry says when it was recorded
    lines = EXPECTED.read_text(encoding="utf-8").splitlines()
    assert all(re.search(r"# .*recorded \d{4}-\d{2}-\d{2}", line) for line in lines
               if line and not line.startswith("#") and not line.startswith("tanabesugano"))


def test_parse_expected_ignores_comments_and_blanks():
    text = "# header\n\nclaude 1.2.3   # note\npython 3.13\nbroken\n  # only comment\n"
    assert doctor.parse_expected(text) == {"claude": "1.2.3", "python": "3.13"}
