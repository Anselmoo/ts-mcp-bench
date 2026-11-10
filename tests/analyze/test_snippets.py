"""Tests for src/tsbench/analyze/snippets.py: each Bash command and each heredoc body as its own file, and the index."""
from __future__ import annotations

import hashlib

import pytest
from analyze_runs import bash, read_csv, result, use, write_run

from tsbench.analyze import snippets
from tsbench.score.extract import read_transcript

ANSWER = {"Dq": 2044.0, "B": 702.0, "C": None, "out_of_scope": False, "reason": "fit"}
SCRIPT = "import numpy as np\nprint(np.linalg.eigvalsh([[1.0, 0.0], [0.0, 2.0]]))\n"
FIRST = f"cat > /tmp/w/a.py <<'EOF'\n{SCRIPT}EOF\npython3 /tmp/w/a.py"
SECOND = "python3 - <<'EOF'\nprint(2044)\nEOF\ncat > notes.txt <<EOF\nDq 2044\nEOF"


def _events():
    return [*bash("t1", FIRST, "Exit code 1\nTraceback (most recent call last):\nValueError: x", err=True),
            use("t2", "bash", {"command": "ls"}),  # an unknown tool name: never ran, no snippet
            *bash("t3", SECOND, "2044\n"),
            *bash("t4", "", ""),  # an empty command: no snippet, as `report artifacts`
            *result(ANSWER)]


def test_files_of_one_transcript(tmp_path):
    path = write_run(tmp_path, "m/B/medium/P-numerical-01-k1", _events())
    files = snippets.snippets_of(path, read_transcript(path))
    assert [(f["step"], f["kind"], f["name"]) for f in files] == [
        (1, "bash", "step-01.sh"), (1, "heredoc", "step-01-a.py"),
        (2, "bash", "step-02.sh"), (2, "heredoc", "step-02-heredoc-1.py"), (2, "heredoc", "step-02-notes.txt")]
    assert files[0]["data"] == FIRST and files[1]["data"] == SCRIPT and files[3]["data"] == "print(2044)\n"
    assert files[1]["target"] == "/tmp/w/a.py" and files[3]["target"] == "" and files[0]["target"] == ""
    assert [f["tool_use_id"] for f in files] == ["t1", "t1", "t3", "t3", "t3"]
    assert [(f["exit"], f["is_error"]) for f in files[:3]] == [(1, True), (1, True), (0, False)]
    assert files[0]["lines"] == 5 and files[1]["lines"] == 2
    assert all(f["sha256"] == hashlib.sha256(f["data"].encode("utf-8")).hexdigest() for f in files)


@pytest.mark.parametrize("target,python,j,name", [
    ("x.py", False, 1, "step-03-x.py"), (None, True, 2, "step-03-heredoc-2.py"), ("data.json", False, 1,
                                                                                  "step-03-data.json.txt"),
    ("notes.txt", False, 1, "step-03-notes.txt"), (None, False, 1, "step-03-heredoc-1.txt"),
    ("/tmp/we ird$.py", False, 1, "step-03-we_ird_.py"),
    ("_a.py", False, 1, "step-03-a.py"), (".hidden_", False, 1, "step-03-hidden.txt"),
    ("Xa.pyX", False, 1, "step-03-Xa.pyX.txt"), ("c:\\tmp\\a.py", False, 1, "step-03-a.py"),
    ("d\\a.py", False, 1, "step-03-a.py"), ("x" * 70, False, 1, "step-03-" + "x" * 60 + ".txt"),
    ("n" * 70 + ".py", False, 1, "step-03-" + "n" * 57 + ".py"),
    ("n" * 70 + ".txt", False, 1, "step-03-" + "n" * 56 + ".txt"),
    ("a." + "n" * 70 + ".py", False, 1, "step-03-a." + "n" * 55 + ".py"),
    ("n" * 70 + ".json", False, 1, "step-03-" + "n" * 55 + ".json.txt"),
    ("n" * 57 + ".py", False, 1, "step-03-" + "n" * 57 + ".py"),
    ("n" * 58 + ".py", False, 1, "step-03-" + "n" * 57 + ".py"),
    ("a" * 60, False, 1, "step-03-" + "a" * 60 + ".txt"),
    ("a" * 61, False, 1, "step-03-" + "a" * 60 + ".txt"),
    ("n" * 70 + "." + "s" * 8, False, 1, "step-03-" + "n" * 51 + "." + "s" * 8 + ".txt"),
    ("n" * 70 + "." + "s" * 9, False, 1, "step-03-" + "n" * 60 + ".txt"),
])
def test_heredoc_file_names(target, python, j, name):
    assert snippets.heredoc_name(3, j, target, python) == name


def test_two_heredocs_with_one_name_stay_apart(tmp_path):
    cmd = "cat > a.py <<'A'\nx = 1\nA\ncat > a.py <<'B'\nx = 2\nB"
    path = write_run(tmp_path, "m/B/medium/P-numerical-01-k1", [*bash("t1", cmd, ""), *result(ANSWER)])
    names = [f["name"] for f in snippets.snippets_of(path, read_transcript(path))]
    assert names == ["step-01.sh", "step-01-a.py", "step-01-a-2.py"]


def test_main_writes_the_files_and_the_index(tmp_path, capsys):
    runs, out = tmp_path / "runs", tmp_path / "out"
    write_run(runs, "m/B/medium/P-numerical-01-k1", _events())
    write_run(runs, "m/A/medium/P-numerical-01-k1", result(ANSWER))
    assert snippets.main(["--runs", str(runs), "--out", str(out)]) == 0
    rows = read_csv(out / "index.csv")
    assert list(rows[0]) == snippets.INDEX_COLUMNS
    assert [r["file"] for r in rows] == [f"m/B/medium/P-numerical-01-k1/{n}" for n in
                                         ("step-01.sh", "step-01-a.py", "step-02.sh", "step-02-heredoc-1.py",
                                          "step-02-notes.txt")]
    for r in rows:  # the file holds exactly the bytes whose hash the index gives
        assert hashlib.sha256((out / r["file"]).read_bytes()).hexdigest() == r["sha256"]
    assert (out / rows[0]["file"]).read_text(encoding="utf-8") == FIRST
    assert rows[0]["run_id"] == "m/B/medium/P-numerical-01-k1" and rows[0]["step"] == "1"
    assert rows[1]["target"] == "/tmp/w/a.py" and rows[1]["is_error"] == "True"
    assert "Bash commands" in (out / "README.md").read_text(encoding="utf-8")
    assert "runs with Bash: 1, commands: 2, heredocs: 3" in capsys.readouterr().out
    assert not any(p.name.endswith(".code") for p in runs.rglob("*"))  # nothing is written into the run folder


def test_three_heredocs_with_one_name_are_numbered_in_order(tmp_path):
    cmd = "\n".join(f"cat > a.py <<'E'\nx = {i}\nE" for i in range(3))
    path = write_run(tmp_path, "m/B/medium/P-numerical-01-k1", [*bash("t1", cmd, ""), *result(ANSWER)])
    files = snippets.snippets_of(path, read_transcript(path))
    assert [f["name"] for f in files] == ["step-01.sh", "step-01-a.py", "step-01-a-2.py", "step-01-a-3.py"]


def test_the_number_of_a_repeated_name_goes_before_the_last_suffix(tmp_path):
    cmd = "cat > a.b.py <<'E'\nx = 1\nE\ncat > a.b.py <<'E'\nx = 2\nE"
    path = write_run(tmp_path, "m/B/medium/P-numerical-01-k1", [*bash("t1", cmd, ""), *result(ANSWER)])
    assert snippets.snippets_of(path, read_transcript(path))[2]["name"] == "step-01-a.b-2.py"


def test_the_given_transcript_is_read_not_the_file(tmp_path):
    path = write_run(tmp_path, "m/B/medium/P-numerical-01-k1", [*bash("t1", "ls", ""), *result(ANSWER)])
    tr = read_transcript(path)
    path.unlink()
    assert [f["name"] for f in snippets.snippets_of(path, tr)] == ["step-01.sh"]


def test_a_bash_call_without_a_command_gives_no_snippet_and_no_shift(tmp_path):
    path = write_run(tmp_path, "m/B/medium/P-numerical-01-k1", [
        *bash("t0", "", ""), use("t1", "Bash", "not a mapping"), use(7, "Bash", {"command": "pwd"}),
        *bash("t2", "ls", ""), *result(ANSWER)])
    tr = read_transcript(path)
    assert snippets._commands(tr) == [("", "pwd"), ("t2", "ls")]
    assert [(f["tool_use_id"], f["data"]) for f in snippets.snippets_of(path, tr)] == [("", "pwd"), ("t2", "ls")]


def test_a_snippet_that_differs_from_its_extracted_entry_is_an_error(tmp_path, monkeypatch):
    path = write_run(tmp_path, "m/B/medium/P-numerical-01-k1", [*bash("t1", "ls", ""), *result(ANSWER)])
    tr = read_transcript(path)
    monkeypatch.setattr(snippets, "_sha", lambda text: "other")
    with pytest.raises(RuntimeError, match=r"step 1 does not match its extracted entry") as e:
        snippets.snippets_of(path, tr)
    assert str(path) in str(e.value)
