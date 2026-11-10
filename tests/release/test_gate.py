"""Tests for the release gate: it must refuse a tree that tracks or archives private material or forbidden text.

Every test builds a throwaway git repository in a temp directory. Nothing here tags, pushes or releases.
Run: python -m pytest tests/release/test_gate.py -q
"""
from __future__ import annotations

import pathlib
import re
import subprocess

import pytest

from tsbench.release import gate


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """An empty git repository (no commit yet) that the gate sees as the working directory."""
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/dev/null")
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", "/dev/null")
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    for who in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{who}_NAME", "Test")
        monkeypatch.setenv(f"GIT_{who}_EMAIL", "test@example.invalid")
    monkeypatch.chdir(work)
    git(work, "init", "-q")
    return work


def git(work: pathlib.Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=work, check=True, capture_output=True)


def add(work: pathlib.Path, *names: str, commit: bool = True) -> None:
    for name in names:
        path = work / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x\n", encoding="utf-8")
    git(work, "add", "--", *names)
    if commit:
        git(work, "commit", "-q", "-m", "files")


def put(work: pathlib.Path, name: str, text: str | bytes) -> None:
    """Track one file with the given content (staged, not committed: the gate reads the work tree)."""
    path = work / name
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(text, bytes):
        path.write_bytes(text)
    else:
        path.write_text(text, encoding="utf-8")
    git(work, "add", "--", name)


def hits(capsys) -> list[str]:
    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == "forbidden text in tracked files:", lines
    return [line.strip() for line in lines[1:]]


def test_clean_repo_passes(repo, capsys):
    add(repo, "README.md", "src/app.py")
    assert gate.main([]) == 0
    assert capsys.readouterr().out == "clean: no private material or forbidden text tracked or archived\n"


def test_top_level_pilot_directory_fails_and_is_listed_twice(repo, capsys):
    add(repo, "README.md", "pilot/run1.json")
    assert gate.main([]) == 1
    lines = capsys.readouterr().out.splitlines()
    assert lines == ["private material would be published:", "  pilot/run1.json", "  archive: pilot/run1.json"]


def test_nested_pilot_directory_fails(repo, capsys):
    add(repo, "data/pilot/run1.json", "README.md")
    assert gate.main([]) == 1
    out = capsys.readouterr().out
    assert "  data/pilot/run1.json" in out
    assert "  archive: data/pilot/run1.json" in out
    assert "README.md" not in out


def test_names_that_only_look_like_pilot_pass(repo, capsys):
    add(repo, "pilotage/notes.txt", "docs/pilot.md", "docs/copilot/x.md")
    assert gate.main([]) == 0
    assert capsys.readouterr().out.startswith("clean:")


def test_untracked_pilot_file_is_not_a_problem(repo, capsys):
    add(repo, "README.md")
    (repo / "pilot").mkdir()
    (repo / "pilot" / "local.json").write_text("{}", encoding="utf-8")
    assert gate.main([]) == 0
    assert capsys.readouterr().out.startswith("clean:")


def test_repo_without_commit_and_nothing_tracked_passes(repo, capsys):
    assert gate.main([]) == 0
    assert capsys.readouterr().out.startswith("clean:")


def test_staged_pilot_file_without_commit_fails_without_archive_lines(repo, capsys):
    add(repo, "pilot/run1.json", commit=False)
    assert gate.main([]) == 1
    lines = capsys.readouterr().out.splitlines()
    assert lines == ["private material would be published:", "  pilot/run1.json"]


def test_not_a_git_repository_returns_2(tmp_path, monkeypatch, capsys):
    plain = tmp_path / "plain"
    plain.mkdir()
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    monkeypatch.chdir(plain)
    assert gate.main([]) == 2
    captured = capsys.readouterr()
    assert captured.err == "not a git repository\n"
    assert captured.out == ""


def test_missing_git_binary_returns_2(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("PATH", str(tmp_path))
    assert gate.main([]) == 2
    assert capsys.readouterr().err == "not a git repository\n"


def test_unknown_argument_is_rejected(capsys):
    with pytest.raises(SystemExit) as exc:
        gate.main(["--publish"])
    assert exc.value.code == 2
    assert "unrecognized arguments: --publish" in capsys.readouterr().err


def test_help_names_the_program(capsys):
    with pytest.raises(SystemExit) as exc:
        gate.main(["--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "tsbench release gate" in out
    assert "Release gate: fail if private material or forbidden text is tracked by git" in out


@pytest.mark.parametrize("name", ["seed/private/key.json", "analysis/out.csv", ".claude/settings.json",
                                  "src/seed/x.txt", ".env", "contrib/.env",
                                  "contrib/.env.local"])
def test_other_private_material_fails(repo, capsys, name):
    add(repo, "README.md", name)
    assert gate.main([]) == 1
    assert capsys.readouterr().out.splitlines() == ["private material would be published:", f"  {name}",
                                                    f"  archive: {name}"]


def test_names_that_only_look_private_pass(repo, capsys):
    add(repo, "contrib/.env.example", "src/stats/analysis.py", "docs/seed.md", "tests/test_seeds/x.py")
    assert gate.main([]) == 0
    assert capsys.readouterr().out.startswith("clean:")


def test_a_handoff_file_fails_even_when_the_archive_leaves_it_out(repo, capsys):
    add(repo, "HANDOFF-next.md", commit=False)
    (repo / ".gitattributes").write_text("/HANDOFF-*.md export-ignore\n", encoding="utf-8")
    git(repo, "add", ".gitattributes")
    git(repo, "commit", "-q", "-m", "files")
    assert gate.main([]) == 1
    assert hits(capsys) == [".gitattributes:1: agent: 'HANDOFF'", "HANDOFF-next.md: agent: 'HANDOFF'"]


def test_non_ascii_private_path_is_found_before_the_first_commit(repo, capsys):
    add(repo, "pilot/notes-é.md", commit=False)
    assert gate.main([]) == 1
    assert capsys.readouterr().out.splitlines() == ["private material would be published:", "  pilot/notes-é.md"]


def test_non_ascii_private_path_is_found_when_the_archive_leaves_it_out(repo, capsys):
    add(repo, "README.md", "pilot/notes-é.md", commit=False)
    (repo / ".gitattributes").write_text("/pilot export-ignore\n", encoding="utf-8")
    git(repo, "add", ".gitattributes")
    git(repo, "commit", "-q", "-m", "files")
    assert gate.main([]) == 1
    assert capsys.readouterr().out.splitlines() == ["private material would be published:", "  pilot/notes-é.md"]


def test_a_path_with_a_space_is_one_path(repo, capsys):
    add(repo, "docs/my notes.md", "src/a b/pilot/x.json", commit=False)
    assert gate.main([]) == 1
    assert capsys.readouterr().out.splitlines() == ["private material would be published:",
                                                    "  src/a b/pilot/x.json"]


def test_gate_run_from_a_subdirectory_checks_the_whole_repository(repo, monkeypatch, capsys):
    add(repo, "docs/guide.md", "pilot/run1.json")
    monkeypatch.chdir(repo / "docs")
    assert gate.main([]) == 1
    assert capsys.readouterr().out.splitlines() == ["private material would be published:", "  pilot/run1.json",
                                                    "  archive: pilot/run1.json"]


def test_gate_run_from_a_clean_subdirectory_passes(repo, monkeypatch, capsys):
    add(repo, "docs/guide.md", "README.md")
    monkeypatch.chdir(repo / "docs")
    assert gate.main([]) == 0
    assert capsys.readouterr().out.startswith("clean:")


# ------------------------------------------------------------------ forbidden text
@pytest.mark.parametrize("text, found", [
    ("Die Zahl und das Wort\n", ["german: 'und'"]),
    ("siehe Datei\n", ["german: 'siehe'", "german: 'Datei'"]),
    ("UND auch NICHT\n", ["german: 'UND'", "german: 'NICHT'"]),
    ("oder keine gegen richtig falsch Zeilen\n", ["german: 'oder'", "german: 'keine'", "german: 'gegen'",
                                                   "german: 'richtig'", "german: 'falsch'", "german: 'Zeilen'"]),
    ("the Gr\u00f6\u00dfe\n", ["german: '\u00f6'", "german: '\u00df'"]),
])
def test_german_words_and_umlauts_fail(repo, capsys, text, found):
    put(repo, "docs/a.md", text)
    assert gate.main([]) == 1
    assert hits(capsys) == [f"docs/a.md:1: {f}" for f in found]


def test_english_words_that_contain_german_ones_pass(repo, capsys):
    put(repo, "docs/a.md", "fundamental: undo, under, understand, ordered, unique, nichts_here_x, bundle\n"
                           "caf\u00e9 na\u00efve \u00e9t\u00e9; [Ni(H2O)6]2+, d8, Dq/B = 2.1, D4h, Oh, Td, 4T1g\n")
    assert gate.main([]) == 0
    assert capsys.readouterr().out.startswith("clean:")


@pytest.mark.parametrize("text, found", [
    ("see /home/jdoe/x\n", "home path: '/home/jdoe/'"),
    ("cd /Users/jdoe/data\n", "home path: '/Users/jdoe/'"),
    ("PATH=/opt/homebrew/bin\n", "home path: '/opt/homebrew/'"),
])
def test_home_paths_fail(repo, capsys, text, found):
    put(repo, "src/a.py", text)
    assert gate.main([]) == 1
    assert hits(capsys) == [f"src/a.py:1: {found}"]


def test_made_up_home_paths_and_deeper_home_folders_pass(repo, capsys):
    put(repo, "tests/a.py", "'/home/alice/x' '/Users/bob/z' '/home/me/bin' '/real/home/.config/x' '/data/home/x/y'\n"
                            "'/home/u/a' '/Users/c/d' '~/x' '/usr/local/bin' '/home/jo/a' '/home/joanna/b'\n")
    assert gate.main([]) == 0
    assert capsys.readouterr().out.startswith("clean:")


def test_names_from_the_environment_fail_as_whole_tokens(repo, capsys, monkeypatch):
    monkeypatch.setenv("TSBENCH_GATE_DENY", "build-host-7, Lab-Box ,")
    put(repo, "docs/a.md", "ssh build-host-7\nrebuild-host-70 and lab-boxes\nlab-box\n")
    assert gate.main([]) == 1
    assert hits(capsys) == ["docs/a.md:1: name: '***'", "docs/a.md:3: name: '***'"]


def test_environment_names_may_be_separated_by_whitespace(repo, capsys, monkeypatch):
    monkeypatch.setenv("TSBENCH_GATE_DENY", " zorblax\tquux-box\n plim ")
    put(repo, "docs/a.md", "push to git.zorblax.example\nZORBLAX and quux-boxes\nPlim, quux-box\n")
    assert gate.main([]) == 1
    assert hits(capsys) == ["docs/a.md:1: name: '***'", "docs/a.md:2: name: '***'",
                            "docs/a.md:3: name: '***'", "docs/a.md:3: name: '***'"]


def test_a_name_hit_does_not_print_the_name(repo, capsys, monkeypatch):
    monkeypatch.setenv("TSBENCH_GATE_DENY", "zorblax")
    put(repo, "zorblax/a.md", "zorblax\n")
    assert gate.main([]) == 1
    assert "zorblax" not in capsys.readouterr().out.replace("zorblax/a.md", "")


def test_a_planted_name_passes_without_the_environment_variable(repo, capsys, monkeypatch):
    monkeypatch.delenv("TSBENCH_GATE_DENY", raising=False)
    put(repo, "docs/a.md", "push to git.zorblax.example\nZorblax-7\n")
    assert gate.main([]) == 0
    assert capsys.readouterr().out.startswith("clean:")


def test_an_empty_environment_variable_adds_no_names(repo, capsys, monkeypatch):
    monkeypatch.setenv("TSBENCH_GATE_DENY", " , \t")
    put(repo, "docs/a.md", "plain text\n")
    assert gate.main([]) == 0
    assert capsys.readouterr().out.startswith("clean:")


def test_the_generic_patterns_work_without_the_environment_variable(repo, capsys, monkeypatch):
    monkeypatch.delenv("TSBENCH_GATE_DENY", raising=False)
    put(repo, "docs/a.md", "und\n/home/jdoe/x\nSEC-4\na worktree\n")
    assert gate.main([]) == 1
    assert hits(capsys) == ["docs/a.md:1: german: 'und'", "docs/a.md:2: home path: '/home/jdoe/'",
                            "docs/a.md:3: id: 'SEC-4'", "docs/a.md:4: agent: 'worktree'"]


def test_the_gate_source_holds_no_list_of_names():
    assert not hasattr(gate, "DENY_TOKEN_SHA256")
    source = pathlib.Path(gate.__file__).read_text(encoding="utf-8")
    assert not re.search(r"\b[0-9a-f]{64}\b", source)


def test_there_is_no_hash_option(capsys):
    with pytest.raises(SystemExit) as exc:
        gate.main(["--hash", "Zorblax"])
    assert exc.value.code == 2
    assert "unrecognized arguments: --hash" in capsys.readouterr().err


@pytest.mark.parametrize("text, found", [
    ("fixed in SEC-013\n", "id: 'SEC-013'"),
    ("see T1-22 here\n", "id: 'T1-22'"),
    ("the stage plans (D16)\n", "id: 'D16'"),
    ("labels as a multiset (order, D14)\n", "id: 'D14'"),
    ("listable inside B (deviation D13).\n", "id: 'deviation D13'"),
    ("as decision D7 says\n", "id: 'decision D7'"),
    ("under the D14 rule\n", "id: 'D14 rule'"),
])
def test_internal_ids_fail(repo, capsys, text, found):
    put(repo, "src/a.py", text)
    assert gate.main([]) == 1
    assert hits(capsys) == [f"src/a.py:1: {found}"]


def test_chemistry_that_looks_like_an_id_passes(repo, capsys):
    put(repo, "docs/a.md", "a d8 ion (D4h), point group D3, d-electron count D5 or d5, 4T1-4A2, T2g, SECTION-2\n"
                           "the D3 axis; Dq/B; [Co(en)3]3+ D3 symmetry; 10Dq\n")
    assert gate.main([]) == 0
    assert capsys.readouterr().out.startswith("clean:")


@pytest.mark.parametrize("text, found", [
    ("Work in a worktree.\n", "agent: 'worktree'"),
    ("Read the handoff first.\n", "agent: 'handoff'"),
    ("a subagent does it\n", "agent: 'subagent'"),
    ("in a Claude Code session\n", "agent: 'Claude Code session'"),
    ("runs/.werkplan/x\n", "agent: '.werkplan'"),
])
def test_agent_process_words_fail(repo, capsys, text, found):
    put(repo, "docs/a.md", text)
    assert gate.main([]) == 1
    assert hits(capsys) == [f"docs/a.md:1: {found}"]


def test_a_tracked_planning_tool_folder_fails_by_its_path(repo, capsys):
    put(repo, ".werkplan/runs/r1.json", "{}\n")
    assert gate.main([]) == 1
    assert hits(capsys) == [".werkplan/runs/r1.json: agent: '.werkplan'"]


def test_the_git_subcommand_and_cli_field_names_pass(repo, capsys):
    put(repo, "tests/a.py", 'git("worktree", "add", "-q", "wt")\n{"spawned_by_subagents": 0}\nhand off the file\n')
    assert gate.main([]) == 0
    assert capsys.readouterr().out.startswith("clean:")


def test_the_gate_files_the_vendored_d3_and_binary_files_are_exempt(repo, capsys):
    spelled = "und /home/jdoe/ SEC-1 worktree \u00fc\n"
    for name in sorted(gate.EXEMPT):
        put(repo, name, spelled)
    assert gate.EXEMPT == {"src/tsbench/release/gate.py", "tests/release/test_gate.py",
                           "src/tsbench/_vendor/figura/js/d3.min.js"}
    put(repo, "docs/img.png", b"\x89PNG\x00 und worktree")
    put(repo, "docs/latin1.txt", "und \u00fc".encode("latin-1"))
    assert gate.main([]) == 0
    assert capsys.readouterr().out.startswith("clean:")


def test_the_same_file_elsewhere_is_not_exempt(repo, capsys):
    put(repo, "docs/gate.py", "a worktree\n")
    assert gate.main([]) == 1
    assert hits(capsys) == ["docs/gate.py:1: agent: 'worktree'"]


def test_a_path_is_checked_like_its_content(repo, capsys):
    put(repo, "docs/Notizen und Ideen.md", "plain\n")
    assert gate.main([]) == 1
    assert hits(capsys) == ["docs/Notizen und Ideen.md: german: 'und'"]


def test_private_material_and_forbidden_text_are_both_listed(repo, capsys):
    put(repo, "pilot/notes.md", "und\n")
    put(repo, "docs/a.md", "line one\nsee SEC-2\n")
    assert gate.main([]) == 1
    assert capsys.readouterr().out.splitlines() == ["private material would be published:", "  pilot/notes.md",
                                                    "forbidden text in tracked files:", "  docs/a.md:2: id: 'SEC-2'"]


def test_a_tracked_file_missing_from_the_work_tree_is_skipped(repo, capsys):
    put(repo, "docs/a.md", "und\n")
    (repo / "docs" / "a.md").unlink()
    assert gate.main([]) == 0
    assert capsys.readouterr().out.startswith("clean:")


def test_run_data_under_results_skips_the_text_rules(repo, capsys):
    """Model output under results/ may hold symbols like D2, umlauts and process words: they are run data."""
    put(repo, "results/confirmatory/p/m/B/medium/t-k1.jsonl",
        '{"text": "point group D2 (D2), 3T2-8100, Schrödinger, a worktree"}\n')
    put(repo, "results/code-snippets/p/m/B/medium/t-k1/step-01.sh", "echo D5 und T2-7400\n")
    assert gate.main([]) == 0
    assert capsys.readouterr().out.startswith("clean:")


def test_run_data_under_results_still_fails_on_home_paths_and_names(repo, capsys, monkeypatch):
    monkeypatch.setenv("TSBENCH_GATE_DENY", "zorblax")
    put(repo, "results/confirmatory/p/run.log", "File \"/home/jdoe/venv/x.py\"\nhost zorblax\n")
    assert gate.main([]) == 1
    assert hits(capsys) == ["results/confirmatory/p/run.log:1: home path: '/home/jdoe/'",
                            "results/confirmatory/p/run.log:2: name: '***'"]


def test_the_published_analysis_under_results_is_not_private(repo, capsys):
    add(repo, "results/analysis/plan-1/effort/README.md", "results/analysis/plan-1/strategy/runs.csv")
    assert gate.main([]) == 0
    assert capsys.readouterr().out.startswith("clean:")


@pytest.mark.parametrize("name", ["analysis/out.csv", "src/results/analysis/out.csv", "results/pilot/x.csv",
                                  "results/analysis/pilot/x.csv", "results/analysis/plan-1/.claude/x.json",
                                  "results/analysis/.env"])
def test_only_the_analysis_folder_of_results_leaves_the_private_rule(repo, capsys, name):
    add(repo, name)
    assert gate.main([]) == 1
    out = capsys.readouterr().out
    assert f"  {name}\n" in out and f"  archive: {name}\n" in out


def test_the_same_text_outside_results_still_fails(repo, capsys):
    put(repo, "docs/a.md", "point group (D2)\n")
    assert gate.main([]) == 1
    assert hits(capsys) == ["docs/a.md:1: id: 'D2'"]
