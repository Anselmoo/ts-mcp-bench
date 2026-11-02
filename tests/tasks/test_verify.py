"""Tests for `tsbench tasks verify` (tsbench.tasks.verify): the hash check of the committed task set.

The checks run on small task files in tmp_path. Only the last test reads the committed task set, and it
looks at the exit code only.
"""
import hashlib
import json
import runpy
import sys

import pytest

from tsbench.tasks import verify

PILOT_A = {"id": "p1", "split": "pilot", "prompt": "SECRET-PROMPT-1", "note": "Dq·B"}
PILOT_B = {"split": "pilot", "id": "p2", "prompt": "SECRET-PROMPT-2"}
CONF = {"id": "c1", "split": "confirmatory", "prompt": "SECRET-PROMPT-3"}


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# the split text of tasks.sha256 written out by hand: sorted keys, non-ASCII kept, one line per record
PILOT_TEXT = (
    '{"id": "p1", "note": "Dq·B", "prompt": "SECRET-PROMPT-1", "split": "pilot"}\n'
    '{"id": "p2", "prompt": "SECRET-PROMPT-2", "split": "pilot"}\n'
)
CONF_TEXT = '{"id": "c1", "prompt": "SECRET-PROMPT-3", "split": "confirmatory"}\n'


@pytest.fixture
def taskset(tmp_path, monkeypatch):
    """A tiny task set (two pilot records, one confirmatory) with a matching hash file."""
    tasks = tmp_path / "tasks.jsonl"
    tasks.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in (PILOT_A, CONF, PILOT_B)) + "\n",
                     encoding="utf-8")
    hashes = tmp_path / "tasks.sha256"
    write_hashes(hashes, {"tasks.jsonl": hashlib.sha256(tasks.read_bytes()).hexdigest(),
                          "pilot": sha(PILOT_TEXT), "confirmatory": sha(CONF_TEXT)})
    monkeypatch.setattr(verify, "TASKS_PATH", tasks)
    monkeypatch.setattr(verify, "HASH_PATH", hashes)
    return tasks, hashes


def write_hashes(path, digests: dict) -> None:
    path.write_text("".join(f"{d}  {name}\n" for name, d in digests.items()), encoding="utf-8")


def lines(capsys) -> dict:
    """Printed status lines by file or split name: {name: (status, record count, digest)}."""
    out = {}
    for ln in capsys.readouterr().out.splitlines():
        status, name, n, _, _, digest = ln.split()
        out[name] = (status, int(n), digest)
    return out


def test_split_hashes_follow_the_hash_file_definition(taskset):
    got = verify.split_hashes()
    assert list(got) == ["pilot", "confirmatory"]
    assert got["pilot"] == sha(PILOT_TEXT)
    assert got["confirmatory"] == sha(CONF_TEXT)


def test_split_hashes_keep_file_order(taskset):
    tasks, _ = taskset
    tasks.write_text("\n".join(json.dumps(r) for r in (PILOT_B, CONF, PILOT_A)) + "\n", encoding="utf-8")
    swapped = "".join(PILOT_TEXT.splitlines(keepends=True)[::-1])
    assert verify.split_hashes()["pilot"] == sha(swapped)
    assert verify.split_hashes()["pilot"] != sha(PILOT_TEXT)


def test_matching_set_exits_0_and_prints_counts_and_hashes(taskset, capsys):
    tasks, _ = taskset
    assert verify.main([]) == 0
    assert lines(capsys) == {
        "tasks.jsonl": ("OK", 3, hashlib.sha256(tasks.read_bytes()).hexdigest()),
        "pilot": ("OK", 2, sha(PILOT_TEXT)),
        "confirmatory": ("OK", 1, sha(CONF_TEXT)),
    }


def test_output_never_contains_task_content(taskset, capsys):
    verify.main([])
    out = capsys.readouterr().out
    assert "SECRET-PROMPT" not in out and "Dq·B" not in out


def test_wrong_split_hash_fails_only_that_split(taskset, capsys):
    tasks, hashes = taskset
    write_hashes(hashes, {"tasks.jsonl": hashlib.sha256(tasks.read_bytes()).hexdigest(),
                          "pilot": sha("other"), "confirmatory": sha(CONF_TEXT)})
    assert verify.main([]) == 1
    got = lines(capsys)
    assert {k: v[0] for k, v in got.items()} == {"tasks.jsonl": "OK", "pilot": "FAIL", "confirmatory": "OK"}
    assert got["pilot"][2] == sha(PILOT_TEXT)  # the computed hash is printed, not the wanted one


def test_reformatted_file_fails_the_file_hash_but_not_the_split_hashes(taskset, capsys):
    tasks, _ = taskset
    tasks.write_text(tasks.read_text(encoding="utf-8").replace('"split": "confirmatory"', '"split":"confirmatory"'),
                     encoding="utf-8")
    assert verify.main([]) == 1
    assert {k: v[0] for k, v in lines(capsys).items()} == {"tasks.jsonl": "FAIL", "pilot": "OK",
                                                           "confirmatory": "OK"}


def test_name_missing_from_the_hash_file_fails(taskset, capsys):
    tasks, hashes = taskset
    write_hashes(hashes, {"tasks.jsonl": hashlib.sha256(tasks.read_bytes()).hexdigest(), "pilot": sha(PILOT_TEXT)})
    assert verify.main([]) == 1
    assert lines(capsys)["confirmatory"][0] == "FAIL"


def test_unknown_argument_is_refused(taskset, capsys):
    with pytest.raises(SystemExit) as exc:
        verify.main(["--bogus"])
    assert exc.value.code == 2
    assert "--bogus" in capsys.readouterr().err


def test_committed_task_set_verifies(capsys):
    assert verify.main([]) == 0
    assert [v[0] for v in lines(capsys).values()] == ["OK", "OK", "OK"]


# ----------------------------------------------------------------------------- the command line and the file formats

def test_help_names_the_command_and_describes_it(capsys, monkeypatch):
    monkeypatch.setenv("COLUMNS", "200")
    with pytest.raises(SystemExit) as exc:
        verify.main(["--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert out.startswith("usage: tsbench tasks verify [-h]")
    assert ("`tsbench tasks verify`: check the committed task set against its hash file; print counts and hashes, "
            "never content.\n") in out


def test_a_name_with_a_single_space_is_one_name(taskset, capsys):
    # tasks.sha256 separates digest and name by two spaces; one space belongs to the name
    tasks, hashes = taskset
    write_hashes(hashes, {"my notes.txt": sha("x"), "tasks.jsonl": hashlib.sha256(tasks.read_bytes()).hexdigest(),
                          "pilot": sha(PILOT_TEXT), "confirmatory": sha(CONF_TEXT)})
    assert verify.main([]) == 0
    assert [v[0] for v in lines(capsys).values()] == ["OK", "OK", "OK"]


def test_non_ascii_text_is_hashed_as_utf8_whatever_the_locale(taskset, ascii_python, tmp_path):
    tasks, hashes = taskset
    # a name with an accent in the hash file, and "Dq·B" in a task record: both must be read as UTF-8
    write_hashes(hashes, {"café.jsonl": sha("x"), "tasks.jsonl": hashlib.sha256(tasks.read_bytes()).hexdigest(),
                          "pilot": sha(PILOT_TEXT), "confirmatory": sha(CONF_TEXT)})
    code = (
        "import pathlib, sys\n"
        "from tsbench.tasks import verify\n"
        "verify.TASKS_PATH, verify.HASH_PATH = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])\n"
        "sys.exit(verify.main([]))\n"
    )
    done = ascii_python(code, tasks, hashes)
    assert done.returncode == 0, done.stderr[-1500:]
    assert [ln.split()[0] for ln in done.stdout.splitlines()] == ["OK", "OK", "OK"]


def test_running_the_module_as_a_script_exits_with_the_result_of_main(taskset, capsys, monkeypatch):
    tasks, hashes = taskset
    monkeypatch.delitem(sys.modules, "tsbench.tasks.verify")  # runpy re-executes the module as __main__
    monkeypatch.setattr(sys, "argv", ["verify"])
    import tsbench.tasks as pkg
    monkeypatch.setattr(pkg, "TASKS_PATH", tasks)
    monkeypatch.setattr(pkg, "HASH_PATH", hashes)
    with pytest.raises(SystemExit) as exc:
        runpy.run_module("tsbench.tasks.verify", run_name="__main__")
    assert exc.value.code == 0
    assert [v[0] for v in lines(capsys).values()] == ["OK", "OK", "OK"]
    write_hashes(hashes, {"tasks.jsonl": sha("wrong"), "pilot": sha(PILOT_TEXT), "confirmatory": sha(CONF_TEXT)})
    with pytest.raises(SystemExit) as exc:
        runpy.run_module("tsbench.tasks.verify", run_name="__main__")
    assert exc.value.code == 1
