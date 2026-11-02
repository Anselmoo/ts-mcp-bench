"""Unit tests for tools/ci/readme_smoke.py (run with: pytest tests/tools)."""
import importlib.util
import json
import pathlib
import sys
import textwrap

from tsbench.conditions.sandbox import KEY_VARS

CI_DIR = pathlib.Path(__file__).resolve().parents[2] / "tools" / "ci"
spec = importlib.util.spec_from_file_location("readme_smoke", CI_DIR / "readme_smoke.py")
rs = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = rs
spec.loader.exec_module(rs)

README = textwrap.dedent("""\
    # Title

    ```bash
    # ci: dry
    echo first > out1.txt
    ```

    Prose.

    ```bash
    pip install something-real
    ```

    ```python
    # ci: dry
    print("not shell")
    ```

    ```sh
    # ci: dry
    echo second > out2.txt
    ```

    ~~~bash
    # ci: dry
    echo tilde > out3.txt
    ~~~

    ```bash
    # ci: dry
    exit 3
    ```
""")


def test_extract_blocks_finds_shell_blocks_only():
    blocks = rs.extract_blocks(README)
    assert [b.lang for b in blocks] == ["bash", "bash", "sh", "bash", "bash"]
    assert [b.safe for b in blocks] == [True, False, True, True, True]


def test_marker_must_be_first_line():
    text = "```bash\necho hi\n# ci: dry\n```\n"
    (b,) = rs.extract_blocks(text)
    assert not b.safe


def test_block_records_line_number_and_body_without_fence():
    blocks = rs.extract_blocks(README)
    assert blocks[0].line == 3
    assert blocks[0].body.splitlines()[1] == "echo first > out1.txt"


def test_unterminated_fence_is_ignored():
    assert rs.extract_blocks("```bash\n# ci: dry\necho x\n") == []


def _repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "README.md").write_text(README, encoding="utf-8")
    (repo / "keep.txt").write_text("x", encoding="utf-8")
    return repo


def test_run_executes_marked_blocks_in_a_copy_and_reports_skips(tmp_path):
    repo = _repo(tmp_path)
    report = rs.run(repo, repo / "README.md", timeout=30)
    st = [(r["status"], r.get("returncode")) for r in report["blocks"]]
    assert st == [("passed", 0), ("skipped", None), ("passed", 0), ("passed", 0), ("failed", 3)]
    assert report["counts"] == {"passed": 3, "failed": 1, "skipped": 1}
    # the original tree is untouched: blocks ran in a temp copy
    assert not (repo / "out1.txt").exists()


def test_main_exit_code_and_json(tmp_path, capsys):
    repo = _repo(tmp_path)
    code = rs.main(["--repo", str(repo), "--json"])
    assert code == 1  # one block exits 3
    data = json.loads(capsys.readouterr().out)
    assert data["counts"]["failed"] == 1


def test_main_passes_when_nothing_fails(tmp_path, capsys):
    repo = tmp_path / "r"
    repo.mkdir()
    (repo / "README.md").write_text("```bash\n# ci: dry\ntest -f README.md\n```\n```bash\nrm -rf /\n```\n",
        encoding="utf-8")
    assert rs.main(["--repo", str(repo)]) == 0
    out = capsys.readouterr().out
    assert "skipped" in out and "1 passed" in out


def test_blocks_do_not_see_api_keys(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-should-not-leak")
    repo = tmp_path / "r"
    repo.mkdir()
    (repo / "README.md").write_text('```bash\n# ci: dry\ntest -z "${ANTHROPIC_API_KEY:-}"\n```\n', encoding="utf-8")
    assert rs.main(["--repo", str(repo)]) == 0


def test_timeout_is_a_failure(tmp_path):
    repo = tmp_path / "r"
    repo.mkdir()
    (repo / "README.md").write_text("```bash\n# ci: dry\nsleep 5\n```\n", encoding="utf-8")
    report = rs.run(repo, repo / "README.md", timeout=1)
    assert report["counts"]["failed"] == 1
    assert report["blocks"][0]["status"] == "failed"


def test_no_readme_is_an_error(tmp_path):
    assert rs.main(["--repo", str(tmp_path)]) == 2


def test_the_child_env_drops_every_key_variable_the_sandbox_denies():
    assert set(KEY_VARS) <= set(rs.KEY_VARS)
