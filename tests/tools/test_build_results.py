"""Unit tests for tools/build_results.py: the published copy of one plan, its log, images, checks and checksums."""
from __future__ import annotations

import base64
import csv
import hashlib
import importlib.util
import json
import pathlib
import shutil
import sys

import pytest

from tsbench.release import gate

TOOL = pathlib.Path(__file__).resolve().parents[2] / "tools" / "build_results.py"
spec = importlib.util.spec_from_file_location("build_results", TOOL)
br = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = br
spec.loader.exec_module(br)

PLAN = "plan-9"
HOME = "/home/alice"
RULES = [{"name": "b_venv", "pattern": HOME + "/\\.cache/tsbench/venv-B", "replacement": "<B_VENV>"},
         {"name": "home", "pattern": HOME, "replacement": "<HOME>"},
         {"name": "session_folder", "pattern": "-home-alice-[A-Za-z0-9._-]*",
          "replacement": "<operator-session-folder>"}]
DOI = "10.5281/zenodo.1"
PNG = b"\x89PNG\r\n\x1a\nfake"
SCORES = ["model", "condition", "effort", "task_id", "k_index", "correct", "transcript_sha256"]


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _line(content: list[dict]) -> str:
    return json.dumps({"type": "assistant", "message": {"content": content}}) + "\n"


def _source(top: pathlib.Path, **manifest) -> pathlib.Path:
    """A verified copy of one plan: the run folder, the preregistration files and the clear plan."""
    src = top / "source"
    run = src / PLAN
    t = run / "m" / "C" / "medium"
    t.mkdir(parents=True)
    tool = {"type": "tool_result", "content": [{"type": "image", "source": {
        "type": "base64", "media_type": "image/png", "data": base64.b64encode(PNG).decode()}}]}
    (t / "T-01-k1.jsonl").write_text(
        _line([{"type": "text", "text": f"cwd {HOME}/w and {HOME}/.cache/tsbench/venv-B -home-alice-x.y"}])
        + _line([tool]), encoding="utf-8")
    (t / "T-01-k1.artifacts").mkdir()
    (t / "T-01-k1.artifacts" / "plot.png").write_bytes(PNG)
    (t / "T-02-k1.jsonl").write_text(
        json.dumps({"type": "result", "structured_output": {"image_path": "d.png", "image_sha256": "ab"}}) + "\n",
        encoding="utf-8")
    state = {"finished": True, "stop": None, "counts": {"planned": 2, "done": 2, "skipped": 0}}
    (run / "MANIFEST.json").write_text(json.dumps({**state, **manifest}), encoding="utf-8")
    with (run / "scores.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(SCORES)
        w.writerows([["m", "C", "medium", "T-01", "1", "True", "aa"], ["m", "C", "medium", "T-02", "1", "False", "bb"]])
    (run / "run.pid").write_text("7\n", encoding="utf-8")
    (src / "preregistration").mkdir()
    (src / "preregistration" / "preregistration.md").write_text("# plan\n", encoding="utf-8")
    (src / "preregistration" / f"{PLAN}.sealed.json").write_text("{}\n", encoding="utf-8")
    (src / "preregistration" / "notes.txt").write_text("private\n", encoding="utf-8")
    (src / "plans").mkdir()
    (src / "plans" / f"{PLAN}.jsonl").write_text(f'{{"cwd": "{HOME}/w"}}\n', encoding="utf-8")
    return src


class Fake:
    """Stands in for the tsbench command: writes what each step writes, and records the calls."""

    def __init__(self, change=""):
        self.calls: list[list[str]] = []
        self.change = change

    def __call__(self, args: list[str]) -> None:
        self.calls.append(args)
        if "--out" in args:
            out = pathlib.Path(args[args.index("--out") + 1])
            out.mkdir(parents=True)
            (out / "README.md").write_text(f"{args[0]} {args[1]}\n", encoding="utf-8")
        elif args[0] == "score":
            runs = pathlib.Path(args[args.index("--runs") + 1])
            with (runs / "scores.csv").open("w", encoding="utf-8", newline="") as fh:
                w = csv.writer(fh)
                w.writerow(SCORES)
                w.writerows([["m", "C", "medium", "T-01", "1", self.change or "True", "other"],
                             ["m", "C", "medium", "T-02", "1", "False", "other"]])


@pytest.fixture()
def built(tmp_path, monkeypatch):
    monkeypatch.setenv("TSBENCH_GATE_DENY", "nobody-listed")
    repo = tmp_path / "repo"
    repo.mkdir()
    src = _source(tmp_path)
    fake = Fake()
    done = br.build(repo, PLAN, src, br.Rule.parse(RULES), DOI, run=fake)
    return repo / "results", done, fake


def test_the_run_folder_is_copied_without_the_files_of_the_operation(built):
    out, _, _ = built
    assert (out / "confirmatory" / PLAN / "m" / "C" / "medium" / "T-01-k1.jsonl").is_file()
    assert not (out / "confirmatory" / PLAN / "run.pid").exists()
    assert sorted(p.name for p in (out / "confirmatory" / "preregistration").iterdir()) == [
        f"{PLAN}.sealed.json", "preregistration.md"]
    assert (out / "confirmatory" / "plans" / f"{PLAN}.jsonl").is_file()


def test_the_rules_replace_the_machine_paths_most_specific_first(built):
    out, _, _ = built
    text = (out / "confirmatory" / PLAN / "m" / "C" / "medium" / "T-01-k1.jsonl").read_text(encoding="utf-8")
    assert "cwd <HOME>/w and <B_VENV> <operator-session-folder>" in text and HOME not in text
    assert "<HOME>" in (out / "confirmatory" / "plans" / f"{PLAN}.jsonl").read_text(encoding="utf-8")


def test_the_log_records_each_changed_file_with_both_hashes_and_the_counts(tmp_path, built):
    out, _, _ = built
    rows = list(csv.DictReader((out / "REDACTIONS.csv").open(encoding="utf-8", newline="")))
    assert list(rows[0]) == ["file", "sha256_original", "sha256_published", "n_b_venv", "n_home", "n_session_folder"]
    assert [r["file"] for r in rows] == [f"confirmatory/{PLAN}/m/C/medium/T-01-k1.jsonl",
                                         f"confirmatory/plans/{PLAN}.jsonl"]
    r = rows[0]
    assert (r["n_b_venv"], r["n_home"], r["n_session_folder"]) == ("1", "1", "1")
    source = tmp_path / "source" / PLAN / "m" / "C" / "medium" / "T-01-k1.jsonl"
    published = out / "confirmatory" / PLAN / "m" / "C" / "medium" / "T-01-k1.jsonl"
    assert r["sha256_original"] == _sha(source.read_bytes()) and r["sha256_published"] == _sha(published.read_bytes())


def test_a_replaced_file_keeps_its_modification_time(tmp_path, built):
    out, _, _ = built
    source = tmp_path / "source" / PLAN / "m" / "C" / "medium" / "T-01-k1.jsonl"
    published = out / "confirmatory" / PLAN / "m" / "C" / "medium" / "T-01-k1.jsonl"
    assert published.stat().st_mtime_ns == source.stat().st_mtime_ns


def test_the_images_of_a_run_are_indexed_harvested_and_returned_by_a_tool(built):
    out, done, _ = built
    with (out / "images" / f"{PLAN}.index.csv").open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert [(r["run_id"], r["file"], r["origin"]) for r in rows] == [
        ("m/C/medium/T-01-k1", f"images/{PLAN}/m/C/medium/T-01-k1/plot.png", br.HARVESTED),
        ("m/C/medium/T-01-k1", f"images/{PLAN}/m/C/medium/T-01-k1/tool-result-01.png", br.RETURNED)]
    assert all(r["sha256"] == _sha(PNG) and (out / r["file"]).read_bytes() == PNG for r in rows)
    assert done["images"] == 2


def test_the_steps_of_the_analyses_land_in_their_folders(built):
    out, _, fake = built
    assert [c[:2] for c in fake.calls] == [["analyze", "snippets"], ["analyze", "strategy"], ["analyze", "errors"],
                                           ["analyze", "provenance"], ["analyze", "effort"], ["score", "path"],
                                           ["score", "--runs"]]
    assert all(c[-4:] == ["--split", "confirmatory", "--i-have-preregistered", DOI] for c in fake.calls)
    assert (out / "code-snippets" / PLAN / "README.md").read_text(encoding="utf-8") == "analyze snippets\n"
    for name in ("strategy", "errors", "provenance", "effort", "paths"):
        assert (out / "analysis" / PLAN / name / "README.md").is_file()


def test_an_answer_that_names_an_image_nothing_harvested_is_listed(built):
    assert built[1]["unharvested"] == [("m/C/medium/T-02-k1", "d.png", "ab")]


def test_the_checksums_list_every_file_but_themselves(built):
    out, _, _ = built
    lines = (out / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
    named = {ln.split("  ", 1)[1]: ln.split("  ", 1)[0] for ln in lines}
    assert lines == sorted(lines, key=lambda ln: ln.split("  ", 1)[1].encode("utf-8"))
    files = {f"./{p.relative_to(out).as_posix()}": p for p in out.rglob("*") if p.is_file() and p.name != "SHA256SUMS"}
    assert set(named) == set(files) and all(named[k] == _sha(p.read_bytes()) for k, p in files.items())
    assert "./REDACTIONS.csv" in named


def test_a_second_build_replaces_the_rows_and_files_of_the_plan(tmp_path, built):
    out, _, _ = built
    before = (out / "REDACTIONS.csv").read_bytes()
    (out / "confirmatory" / PLAN / "stale.txt").write_text("old\n", encoding="utf-8")
    br.build(tmp_path / "repo", PLAN, tmp_path / "source", br.Rule.parse(RULES), DOI, run=Fake())
    assert (out / "REDACTIONS.csv").read_bytes() == before
    assert not (out / "confirmatory" / PLAN / "stale.txt").exists()


def test_the_rows_of_another_plan_stay(tmp_path, built):
    out, _, _ = built
    with (out / "REDACTIONS.csv").open("a", encoding="utf-8", newline="") as fh:
        csv.writer(fh).writerow(["confirmatory/plan-8/x.jsonl", "a", "b", 0, 1, 0])
    br.build(tmp_path / "repo", PLAN, tmp_path / "source", br.Rule.parse(RULES), DOI, run=Fake())
    assert "confirmatory/plan-8/x.jsonl" in (out / "REDACTIONS.csv").read_text(encoding="utf-8")


def test_a_recovered_image_of_the_index_survives_a_second_build(tmp_path, built):
    out, _, _ = built
    file = f"images/{PLAN}/m/C/medium/T-02-k1/d.png"
    (out / file).parent.mkdir(parents=True)
    (out / file).write_bytes(PNG)
    with (out / "images" / f"{PLAN}.index.csv").open("a", encoding="utf-8", newline="") as fh:
        csv.writer(fh).writerow(["m/C/medium/T-02-k1", file, "recovered from a shared folder", _sha(PNG)])
    done = br.build(tmp_path / "repo", PLAN, tmp_path / "source", br.Rule.parse(RULES), DOI, run=Fake())
    assert (out / file).read_bytes() == PNG and done["images"] == 3 and done["unharvested"] == []
    assert "recovered from a shared folder" in (out / "images" / f"{PLAN}.index.csv").read_text(encoding="utf-8")


def test_a_log_with_other_columns_is_refused(tmp_path, built):
    out, _, _ = built
    (out / "REDACTIONS.csv").write_text("file,other\na,b\n", encoding="utf-8")
    with pytest.raises(br.BuildError, match="columns"):
        br.build(tmp_path / "repo", PLAN, tmp_path / "source", br.Rule.parse(RULES), DOI, run=Fake())


@pytest.mark.parametrize("manifest", [{"finished": False}, {"stop": {"reason": "quota_exhausted"}},
                                      {"counts": {"planned": 3, "done": 1, "skipped": 1}}])
def test_a_plan_that_did_not_finish_is_refused_before_anything_is_written(tmp_path, monkeypatch, manifest):
    monkeypatch.setenv("TSBENCH_GATE_DENY", "nobody-listed")
    repo = tmp_path / "repo"
    repo.mkdir()
    with pytest.raises(br.BuildError, match="not finished"):
        br.build(repo, PLAN, _source(tmp_path, **manifest), br.Rule.parse(RULES), DOI, run=Fake())
    assert not (repo / "results").exists()


def test_the_build_needs_the_names_of_the_gate(tmp_path, monkeypatch):
    monkeypatch.delenv("TSBENCH_GATE_DENY", raising=False)
    repo = tmp_path / "repo"
    repo.mkdir()
    with pytest.raises(br.BuildError, match="TSBENCH_GATE_DENY"):
        br.build(repo, PLAN, _source(tmp_path), br.Rule.parse(RULES), DOI, run=Fake())


def test_a_scoring_difference_of_the_published_copy_stops_the_build(tmp_path, monkeypatch):
    monkeypatch.setenv("TSBENCH_GATE_DENY", "nobody-listed")
    repo = tmp_path / "repo"
    repo.mkdir()
    with pytest.raises(br.BuildError, match="correct"):
        br.build(repo, PLAN, _source(tmp_path), br.Rule.parse(RULES), DOI, run=Fake(change="False"))
    assert not (repo / "results" / "SHA256SUMS").exists()


def test_a_machine_path_left_in_the_results_stops_the_build(tmp_path, monkeypatch):
    monkeypatch.setenv("TSBENCH_GATE_DENY", "alice")
    repo = tmp_path / "repo"
    repo.mkdir()
    rules = [r for r in RULES if r["name"] != "home"]
    src = _source(tmp_path)
    with pytest.raises(br.BuildError, match="gate"):
        br.build(repo, PLAN, src, br.Rule.parse(rules), DOI, run=Fake())
    assert not (repo / "results" / "SHA256SUMS").exists()


def _rules_file(path: pathlib.Path) -> pathlib.Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(RULES), encoding="utf-8")
    return path


def test_the_rules_are_read_from_a_file_outside_the_repository(tmp_path):
    repo = tmp_path / "repo"
    (repo / "tools").mkdir(parents=True)
    rules = br.load_rules(_rules_file(tmp_path / "private" / "rules.json"), repo)
    assert [(r.name, r.replacement) for r in rules] == [("b_venv", "<B_VENV>"), ("home", "<HOME>"),
                                                        ("session_folder", "<operator-session-folder>")]
    with pytest.raises(br.BuildError, match="outside the repository"):
        br.load_rules(_rules_file(repo / "tools" / "rules.json"), repo)


@pytest.mark.parametrize("text", ["{}", "[]", '[{"name": "a"}]', '[{"name": "a", "pattern": "(", "replacement": "b"}]',
                                  "no json"])
def test_a_broken_rules_file_is_refused(tmp_path, text):
    path = tmp_path / "rules.json"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(br.BuildError, match="rules"):
        br.load_rules(path, tmp_path / "repo")


def test_the_command_line_takes_repo_plan_source_rules_and_doi(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("TSBENCH_GATE_DENY", "nobody-listed")
    repo = tmp_path / "repo"
    repo.mkdir()
    src = _source(tmp_path)
    rules = _rules_file(tmp_path / "rules.json")
    monkeypatch.setattr(br, "tsbench", Fake())
    args = ["--repo", str(repo), "--plan", PLAN, "--source", str(src), "--rules", str(rules), "--doi", DOI]
    assert br.main(args) == 0
    assert f"{PLAN}: " in capsys.readouterr().out and (repo / "results" / "SHA256SUMS").is_file()
    shutil.rmtree(src / PLAN)
    assert br.main(args) == 1
    assert "tools/build_results.py:" in capsys.readouterr().err


def test_the_source_defaults_to_the_verified_copy_of_the_repository(tmp_path, monkeypatch):
    seen = {}
    monkeypatch.setattr(br, "build", lambda repo, plan, source, rules, doi: seen.update(source=source) or {
        "images": 0, "replaced": 0, "unharvested": []})
    rules = _rules_file(tmp_path / "rules.json")
    assert br.main(["--repo", str(tmp_path / "r"), "--plan", PLAN, "--rules", str(rules), "--doi", DOI]) == 0
    assert seen["source"] == tmp_path / "r" / "results-basic" / "confirmatory"


def test_the_tool_holds_no_machine_path():
    assert [hit for line in TOOL.read_text(encoding="utf-8").splitlines() for hit in gate.find_forbidden(line)] == []
