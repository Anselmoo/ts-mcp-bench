"""`tsbench tasks generate --check` compares a fresh task set with the committed one and never overwrites it."""
from __future__ import annotations

import ast
import pathlib

import pytest

from tsbench.tasks import generate


@pytest.fixture
def committed(tmp_path, monkeypatch):
    """A stand-in for the package task data, so the test never touches the real task set."""
    data = tmp_path / "data"
    data.mkdir()
    (data / "tasks.jsonl").write_text('{"id": "P-a-01", "class": "closed_form"}\n', encoding="utf-8")
    (data / "rubric.md").write_text("rubric\n", encoding="utf-8")
    monkeypatch.setattr(generate, "TASK_DATA", data)
    return data


def fake_generate(written):
    def run(out_dir: pathlib.Path) -> dict:
        written.append(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "tasks.jsonl").write_text('{"id": "P-b-01", "class": "closed_form"}\n', encoding="utf-8")
        (out_dir / "rubric.md").write_text("rubric\n", encoding="utf-8")
        return {}
    return run


def test_check_writes_to_a_temporary_folder_and_reports_the_difference(committed, monkeypatch):
    written = []
    monkeypatch.setattr(generate, "generate", fake_generate(written))
    assert generate.main(["--check"]) == 1
    assert written and written[0].resolve() != committed.resolve()
    assert (committed / "tasks.jsonl").read_text(encoding="utf-8") == '{"id": "P-a-01", "class": "closed_form"}\n'


def test_check_refuses_the_package_data_as_output(committed, monkeypatch):
    monkeypatch.setattr(generate, "generate", fake_generate([]))
    with pytest.raises(SystemExit):
        generate.main(["--check", "--out", str(committed)])
    assert (committed / "tasks.jsonl").read_text(encoding="utf-8") == '{"id": "P-a-01", "class": "closed_form"}\n'


def _unused_imports(path: pathlib.Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported = {(a.asname or a.name).split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom | ast.Import)
                for a in n.names if a.name != "annotations"}
    used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    return sorted(imported - used)


def test_generate_imports_only_what_it_uses():
    assert _unused_imports(pathlib.Path(generate.__file__)) == []


def test_generate_has_no_empty_section_banners():
    text = pathlib.Path(generate.__file__).read_text(encoding="utf-8")
    assert "# noqa: F401" not in text
    banners = [i for i, ln in enumerate(text.splitlines()) if ln.startswith("# ------")]
    lines = text.splitlines()
    for i in banners:
        following = next((ln for ln in lines[i + 1:] if ln.strip()), "")
        assert not following.startswith("# ------"), f"empty banner at line {i + 1}"
