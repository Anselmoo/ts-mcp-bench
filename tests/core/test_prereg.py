"""The one DOI check behind every `--i-have-preregistered` guard."""
from __future__ import annotations

import pytest

from tsbench.core import prereg


@pytest.mark.parametrize("value", ["10.1234/abc", "10.12345678/x.y-z", "doi:10.5281/zenodo.123"])
def test_is_doi_accepts_doi_shaped_values(value):
    assert prereg.is_doi(value)


@pytest.mark.parametrize("value", [None, "", "x", "10.1/x", "10.123/x", "10.1234/", "yes", "10.1234"])
def test_is_doi_refuses_the_rest(value):
    assert not prereg.is_doi(value)


def test_every_guard_uses_the_shared_pattern():
    """No module keeps its own copy of the DOI pattern."""
    import pathlib
    import re

    root = pathlib.Path(prereg.__file__).resolve().parents[1]
    own = [str(p.relative_to(root)) for p in root.rglob("*.py")
           if p.name != "prereg.py" and re.search(r"10\\\.\\d\{4,9\}/\\S\+", p.read_text(encoding="utf-8"))]
    assert own == []
