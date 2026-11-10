"""The markdown files of the repository: which exist, what they may say, and whether their links resolve."""
from __future__ import annotations

import pathlib
import re
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]

# prose pages that are written by hand
DOCS = {"README.md", "CONTRIBUTING.md", "docs/pipeline.md", "docs/functional-test.md", "docs/methods.md",
        "contrib/gateway/README.md"}
# markdown that is data or belongs to a vendored copy
DATA = {"src/tsbench/data/tasks/rubric.md", "src/tsbench/_vendor/figura/README.md"}

FENCE = re.compile(r"^(```|~~~).*?^\1[ \t]*$", re.S | re.M)
INLINE_CODE = re.compile(r"`[^`\n]*`")
LINK = re.compile(r"(?<!!)\[[^\]\n]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
IMAGE = re.compile(r"!\[[^\]\n]*\]\(([^)\s]+)\)")
AVAILABILITY = ("The benchmark, its task set, run plans and results follow the FAIR principles: they are findable, "
                "accessible, interoperable and reusable through this repository and its archived releases. Further "
                "material is available on written request to the maintainer.")


def repository_markdown() -> set[str]:
    """The markdown files git sees in the working tree: tracked and not deleted, or new and not ignored. Those under
    results/ are written with the run data, and the release gate checks them."""
    out = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "*.md"], cwd=ROOT,
                         check=True, capture_output=True, text=True, encoding="utf-8").stdout
    return {p for p in out.split() if (ROOT / p).is_file() and not p.startswith("results/")}


def present_docs() -> list[str]:
    return sorted(DOCS)


def prose(text: str) -> str:
    """The text without fenced blocks and inline code."""
    return INLINE_CODE.sub("", FENCE.sub("", text))


def test_repository_markdown_is_the_allowlist():
    found = repository_markdown()
    expected = DOCS | DATA
    assert found == expected, {"unexpected": sorted(found - expected), "missing": sorted(expected - found)}


def test_markdown_under_results_is_run_data_and_stays_out_of_the_allowlist():
    assert not [p for p in repository_markdown() if p.startswith("results/")]


def test_readme_states_the_availability_in_two_sentences():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    section = text.split("\n## Availability\n", 1)[1].split("\n## ", 1)[0]
    assert " ".join(section.split()) == AVAILABILITY


def test_readme_title_is_a_statement():
    """The README opens with what the repository is, not with a question."""
    head = (ROOT / "README.md").read_text(encoding="utf-8").split("\n## ", 1)[0]
    assert "?" not in head
    assert "Benchmark of language models on Tanabe-Sugano ligand-field tasks" in " ".join(head.split())


@pytest.mark.parametrize("name", [*present_docs(), "pyproject.toml", "CITATION.cff"])
def test_no_page_states_the_benchmark_as_a_question(name):
    text = " ".join((ROOT / name).read_text(encoding="utf-8").split())
    assert not re.search(r"(?i)\bdoes an? (domain )?MCP server\b", text)


@pytest.mark.parametrize("name", present_docs())
def test_no_phase_session_or_date_in_prose(name):
    text = (ROOT / name).read_text(encoding="utf-8")
    assert not re.search(r"\bphase\s+\d", text, re.I), "a numbered phase"
    assert not re.search(r"\b20\d\d-\d\d-\d\d\b", text), "a date"
    assert not re.search(r"\bsessions?\b", prose(text), re.I), "the word session"


@pytest.mark.parametrize("name", present_docs())
def test_relative_links_resolve(name):
    path = ROOT / name
    text = FENCE.sub("", path.read_text(encoding="utf-8"))
    for target in LINK.findall(text) + IMAGE.findall(text):
        if re.match(r"^([a-z][a-z0-9+.-]*:|#)", target, re.I):
            continue
        assert (path.parent / target.split("#", 1)[0]).exists(), f"{name}: broken link {target}"
