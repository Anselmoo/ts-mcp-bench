"""CITATION.cff: present for a public repository, and in step with pyproject.toml (title, version, licence, authors)."""
from __future__ import annotations

import pathlib
import tomllib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def cff():
    yaml = pytest.importorskip("yaml")
    return yaml.safe_load((ROOT / "CITATION.cff").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def project():
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]


def test_citation_has_the_required_cff_keys(cff):
    assert cff["cff-version"] == "1.2.0"
    assert cff["type"] == "software"
    assert cff["message"].strip()
    assert cff["title"].strip() and cff["authors"]


def test_citation_matches_pyproject(cff, project):
    assert str(cff["version"]) == project["version"]
    assert cff["license"] == project["license"]
    names = [f"{a['given-names']} {a['family-names']}" for a in cff["authors"]]
    assert names == [a["name"] for a in project["authors"]]
    assert "tsbench" in cff["title"]

