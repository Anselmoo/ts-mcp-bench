"""Unit tests of `tsbench.figures.data`: labels, keys, discovery, row normalisation and pooling, with real values."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import pathlib

import pytest

from tsbench.core import prereg
from tsbench.figures import data


def _write_csv(path: pathlib.Path, rows: list[dict]) -> None:
    cols = sorted({k for r in rows for k in r})
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


def _manifest(folder: pathlib.Path, **doc) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "MANIFEST.json").write_text(json.dumps(doc), encoding="utf-8")


# ------------------------------------------------------------------------------------------------ names
@pytest.mark.parametrize("model,label", [
    ("claude-haiku-5-5", "Haiku 5.5"), ("claude-sonnet-4-10", "Sonnet 4.10"), ("claude-opus-3-0", "Opus 3.0"),
    ("gwdg-qwen3-coder", "qwen3-coder"), ("qwen3", "qwen3"), ("", "?"), (None, "?"),
    ("claude-haiku-5", "claude-haiku-5"), ("claude-haiku-5-5-extra", "claude-haiku-5-5-extra"),
    ("xclaude-haiku-5-5", "xclaude-haiku-5-5"), ("claude-Haiku-5-5", "claude-Haiku-5-5"),
    ("claude-haiku-5-x", "claude-haiku-5-x"), ("claude-haiku-a-5", "claude-haiku-a-5"),
    ("claude-4-5-5", "claude-4-5-5"), ("gwdg-claude-haiku-5-5", "claude-haiku-5-5"),
])
def test_model_label(model, label):
    assert data.model_label(model) == label


def test_model_label_strips_only_the_leading_gateway_prefix():
    assert data.model_label("gwdg-gwdg-x") == "gwdg-x"
    assert data.model_label("x-gwdg-y") == "x-gwdg-y"


@pytest.mark.parametrize("model,norm", [("gwdg-llama", "llama"), ("llama", "llama"), ("x-gwdg-y", "x-gwdg-y"),
                                        ("gwdg-gwdg-x", "gwdg-x"), ("", ""), (None, ""), ("gwdg-", "")])
def test_model_norm(model, norm):
    assert data.model_norm(model) == norm


def test_model_key_orders_claude_models_by_family_then_the_rest_by_name():
    assert data.model_key("claude-haiku-5-5") == (0, 0, "")
    assert data.model_key("claude-sonnet-5-5") == (0, 1, "")
    assert data.model_key("claude-opus-4-7") == (0, 2, "")
    # a family name without the claude- prefix is not a Claude model
    assert data.model_key("haiku") == (1, 0, "haiku")
    assert data.model_key("opus-4") == (1, 0, "opus-4")
    assert data.model_key("claude-foo-1-2") == (1, 0, "claude-foo-1-2")
    assert data.model_key("zeta") == (1, 0, "zeta")
    models = ["zeta", "claude-opus-4-7", "alpha", "claude-haiku-5-5", "claude-sonnet-5-5"]
    assert sorted(models, key=data.model_key) == ["claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-4-7", "alpha",
                                                  "zeta"]


def test_model_key_of_a_blank_label_does_not_raise():
    assert data.model_key("gwdg- ") == (1, 0, "gwdg- ")


def test_class_label_replaces_every_underscore():
    assert data.class_label("literature_all") == "literature all"
    assert data.class_label("a_b_c") == "a b c"
    assert data.class_label("experimental") == "experimental"


def test_constants():
    assert data.CONDITIONS == ("A", "B", "C")
    assert data.COND_NAME == {"A": "no tools", "B": "Bash", "C": "TS-MCP"}
    assert data.MODEL_ORDER == ("haiku", "sonnet", "opus")
    found = prereg.DOI_RE.search("see 10.5281/zenodo.1234 now")
    assert found is not None and found.group(0) == "10.5281/zenodo.1234"
    assert prereg.DOI_RE.search("10.123/x") is None
    assert data.REPO_ROOT.joinpath("pyproject.toml").is_file()


# ------------------------------------------------------------------------------------------------ discovery
def test_has_runs(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    assert data._has_runs(empty) is False
    with_csv = tmp_path / "with_csv"
    with_csv.mkdir()
    (with_csv / "scores.csv").write_text("model\n", encoding="utf-8")
    assert data._has_runs(with_csv) is True
    with_tr = tmp_path / "with_tr"
    (with_tr / "m" / "A" / "medium").mkdir(parents=True)
    (with_tr / "m" / "A" / "medium" / "T1-k1.jsonl").write_text("{}\n", encoding="utf-8")
    assert data._has_runs(with_tr) is True
    other = tmp_path / "other"
    (other / "m" / "A" / "medium").mkdir(parents=True)
    (other / "m" / "A" / "medium" / "notes.txt").write_text("x", encoding="utf-8")
    assert data._has_runs(other) is False


def test_sealed_split_is_found_by_path_and_by_manifest(tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()
    assert data._is_confirmatory(plain) is False
    _manifest(plain, split="pilot")
    assert data._is_confirmatory(plain) is False
    _manifest(plain, finished=True)
    assert data._is_confirmatory(plain) is False
    _manifest(plain, split="confirmatory")
    assert data._is_confirmatory(plain) is True
    (plain / "MANIFEST.json").write_text("{not json", encoding="utf-8")
    assert data._is_confirmatory(plain) is False
    loud = tmp_path / "Confirmatory-Set"
    loud.mkdir()
    assert data._is_confirmatory(loud) is True
    (tmp_path / "x").mkdir()
    _manifest(tmp_path / "x" / "sub", split="Confirmatory")
    assert data._is_confirmatory(tmp_path / "x" / "sub") is False  # the split value is compared exactly
    # only MANIFEST.json counts, not a file with another case
    (tmp_path / "y").mkdir()
    (tmp_path / "y" / "manifest.json").write_text(json.dumps({"split": "confirmatory"}), encoding="utf-8")
    assert data._is_confirmatory(tmp_path / "y") is False


def test_manifest_reads_pass_utf8(tmp_path, text_io_is_utf8):
    d = tmp_path / "d"
    _manifest(d, split="pilot", finished=False)
    assert data._is_unfinished(d) is True and data._is_confirmatory(d) is False
    assert text_io_is_utf8 == [("read_text(MANIFEST.json)", "utf-8")] * 2


def test_is_unfinished_reads_the_finished_flag(tmp_path):
    d = tmp_path / "d"
    d.mkdir()
    assert data._is_unfinished(d) is False
    _manifest(d, finished=False)
    assert data._is_unfinished(d) is True
    _manifest(d, finished=True)
    assert data._is_unfinished(d) is False
    _manifest(d, split="pilot")
    assert data._is_unfinished(d) is False  # absent is not False
    _manifest(d, finished=None)
    assert data._is_unfinished(d) is False
    (d / "MANIFEST.json").write_text("[", encoding="utf-8")
    assert data._is_unfinished(d) is False
    (d / "MANIFEST.json").unlink()
    (d / "manifest.json").write_text(json.dumps({"finished": False}), encoding="utf-8")
    assert data._is_unfinished(d) is False


def test_find_run_sets_errors_name_the_root(tmp_path):
    with pytest.raises(ValueError, match=r"^not a directory: .*nowhere$"):
        data.find_run_sets([tmp_path / "nowhere"])
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(ValueError, match=r"^no run sets \(MANIFEST.json, scores.csv or transcripts\) under .*empty$"):
        data.find_run_sets([empty])


def test_find_run_sets_a_root_with_scores_counts_as_one_set(tmp_path):
    root = tmp_path / "solo"
    root.mkdir()
    (root / "scores.csv").write_text("model\n", encoding="utf-8")
    assert data.find_run_sets([root]) == [(root, "solo", "solo")]
    assert data.find_run_sets([str(root)]) == [(root, "solo", "solo")]


def test_find_run_sets_lists_manifest_folders_in_root_order_and_dedupes(tmp_path):
    r1, r2 = tmp_path / "r1", tmp_path / "r2"
    _manifest(r1 / "b", split="pilot")
    _manifest(r1 / "a", split="pilot")
    (r1 / "a" / "run_set.json").write_text(json.dumps({"title": "Set A"}), encoding="utf-8")
    _manifest(r2 / "c", split="pilot")
    found = data.find_run_sets([r2, r1, r2])
    assert [(n, t) for _p, n, t in found] == [("c", "c"), ("a", "Set A"), ("b", "b")]
    assert [p for p, _n, _t in found] == [r2 / "c", r1 / "a", r1 / "b"]
    # the same folder reached through two roots is listed once
    again = data.find_run_sets([r1, r1 / "a"])
    assert [n for _p, n, _t in again] == ["a", "b"]
    # a set seen before does not hide the sets after it in the same root
    later = data.find_run_sets([r1 / "a", r1])
    assert [n for _p, n, _t in later] == ["a", "b"]


def test_find_run_sets_gives_equally_named_sets_of_different_roots_distinct_names(tmp_path):
    from tsbench.score.run_sets import run_sets_in
    a, b = tmp_path / "batch1" / "qwen", tmp_path / "batch2" / "qwen"
    _manifest(a, split="pilot")
    _manifest(b, split="pilot")
    found = data.find_run_sets([a, b])
    assert [n for _p, n, _t in found] == ["qwen", "batch2/qwen"]
    assert [t for _p, _n, t in found] == ["qwen", "batch2/qwen"]
    assert [n for _p, n, _t in found] == [rs.name for rs in run_sets_in([a, b])]
    # a set inside a root takes the root's folder name
    c, d = tmp_path / "x1", tmp_path / "x2"
    _manifest(c / "m", split="pilot")
    _manifest(d / "m", split="pilot")
    assert [n for _p, n, _t in data.find_run_sets([c, d])] == ["m", "x2/m"]
    # a root that counts as one set because of its scores.csv is renamed the same way
    e, f = tmp_path / "p" / "solo", tmp_path / "q" / "solo"
    for r in (e, f):
        r.mkdir(parents=True)
        (r / "scores.csv").write_text("model\n", encoding="utf-8")
    assert [n for _p, n, _t in data.find_run_sets([e, f])] == ["solo", "q/solo"]


def test_find_run_sets_refuses_a_sealed_split_unless_a_doi_is_given(tmp_path):
    root = tmp_path / "sets"
    _manifest(root / "open", split="pilot")
    _manifest(root / "sealed", split="confirmatory")
    with pytest.raises(ValueError, match=r"^refusing a confirmatory run set without --i-have-preregistered <DOI>: "
                                         r"sealed$"):
        data.find_run_sets([root])
    for bad in (None, "", "not a doi", "10.12/x"):
        with pytest.raises(ValueError, match="refusing"):
            data.find_run_sets([root], bad)
    found = data.find_run_sets([root], "preregistered at 10.5281/zenodo.1234")
    assert [n for _p, n, _t in found] == ["open", "sealed"]
    found = data.find_run_sets([root], "10.1234/x")
    assert [n for _p, n, _t in found] == ["open", "sealed"]


def test_find_run_sets_refuses_a_sealed_path_name(tmp_path):
    root = tmp_path / "Confirmatory-Runs"
    _manifest(root, split="pilot")
    with pytest.raises(ValueError, match="refusing"):
        data.find_run_sets([root])
    assert [n for _p, n, _t in data.find_run_sets([root], "10.5281/zenodo.9")] == ["Confirmatory-Runs"]


def test_pilot_tasks_is_the_pilot_split_by_id():
    from tsbench.tasks import load
    tasks = data.pilot_tasks()
    pilot = load("pilot")
    assert len(tasks) == len(pilot) > 0
    assert all(tasks[t["id"]] is not None and tasks[t["id"]]["class"] == t["class"] for t in pilot)
    assert set(tasks) == {t["id"] for t in pilot}


# ------------------------------------------------------------------------------------------------ rows
@pytest.mark.parametrize("value,expected", [
    ("2.5", 2.5), (3, 3.0), (0, 0.0), ("0", 0.0), (" 1.5 ", 1.5), ("-4", -4.0), ("1e3", 1000.0), (True, 1.0),
    ("", None), (None, None), ("abc", None), ("nan", None), ("NaN", None), (float("nan"), None), ([], None),
])
def test_as_float(value, expected):
    got = data._as_float(value)
    assert got == expected and (got is None) == (expected is None)
    if expected is not None:
        assert isinstance(got, float)


def test_as_float_keeps_infinity():
    assert data._as_float("inf") == math.inf


@pytest.mark.parametrize("value,expected", [
    ("True", True), ("true", True), (" TRUE ", True), ("1", True), (1, True), (True, True),
    ("False", False), ("0", False), (0, False), (False, False), ("", False), (None, False), ("yes", False),
    ("11", False), ("2", False), ("truee", False),
])
def test_as_bool(value, expected):
    assert data._as_bool(value) is expected


FULL = {"model": "gwdg-qwen3", "condition": "C", "effort": "high", "task_id": "T7", "k_index": "3",
        "class": "literature_all", "correct": "True", "evaluable": "False", "has_result": "False", "dq": "1000.5",
        "b": "700", "c": "3000", "cost_usd": "0.25", "output_tokens": "1200", "wall_time_s": "42.5",
        "duration_s": "40", "n_mcp_calls": "4", "n_bash_calls": "0"}


def test_norm_row_full_row():
    assert data._norm_row(FULL, "set-1") == {
        "set": "set-1", "model": "qwen3", "condition": "C", "effort": "high", "task_id": "T7", "k_index": 3,
        "class": "literature_all", "correct": True, "evaluable": False, "has_result": False, "dq": 1000.5, "b": 700.0,
        "c": 3000.0, "cost_usd": 0.25, "output_tokens": 1200.0, "wall_s": 42.5, "wall_is_measured": True,
        "n_mcp_calls": 4.0, "n_bash_calls": 0.0}


def test_norm_row_empty_row_has_documented_defaults():
    assert data._norm_row({}, "s") == {
        "set": "s", "model": "", "condition": "", "effort": "", "task_id": "", "k_index": 0, "class": "",
        "correct": False, "evaluable": True, "has_result": True, "dq": None, "b": None, "c": None, "cost_usd": None,
        "output_tokens": None, "wall_s": None, "wall_is_measured": False, "n_mcp_calls": None, "n_bash_calls": None}


def test_norm_row_empty_strings_are_missing_values():
    r = data._norm_row({k: "" for k in FULL}, "s")
    assert r["evaluable"] is True and r["has_result"] is False and r["correct"] is False
    assert r["k_index"] == 0 and r["wall_s"] is None and r["wall_is_measured"] is False
    assert r["dq"] is None and r["n_mcp_calls"] is None


@pytest.mark.parametrize("ev,expected", [(None, True), ("", True), ("True", True), ("1", True), ("False", False),
                                         ("0", False), ("no", False), (False, False), (True, True)])
def test_norm_row_evaluable(ev, expected):
    assert data._norm_row({"evaluable": ev}, "s")["evaluable"] is expected


@pytest.mark.parametrize("hr,expected", [(None, False), ("", False), ("True", True), ("1", True), ("False", False)])
def test_norm_row_has_result_when_present(hr, expected):
    assert data._norm_row({"has_result": hr}, "s")["has_result"] is expected


def test_norm_row_wall_time_falls_back_to_the_duration():
    r = data._norm_row({"wall_time_s": "", "duration_s": "19.5"}, "s")
    assert (r["wall_s"], r["wall_is_measured"]) == (19.5, False)
    r = data._norm_row({"duration_s": "19.5"}, "s")
    assert (r["wall_s"], r["wall_is_measured"]) == (19.5, False)
    r = data._norm_row({"wall_time_s": "0", "duration_s": "19.5"}, "s")
    assert (r["wall_s"], r["wall_is_measured"]) == (0.0, True)  # a measured zero is a measurement
    r = data._norm_row({"wall_time_s": "7", "duration_s": "19.5"}, "s")
    assert (r["wall_s"], r["wall_is_measured"]) == (7.0, True)
    r = data._norm_row({"wall_time_s": "nan", "duration_s": "2"}, "s")
    assert (r["wall_s"], r["wall_is_measured"]) == (2.0, False)


@pytest.mark.parametrize("k,expected", [("1", 1), ("3.0", 3), ("", 0), (None, 0), ("x", 0), ("2.9", 2), (5, 5)])
def test_norm_row_k_index(k, expected):
    got = data._norm_row({"k_index": k}, "s")["k_index"]
    assert got == expected and isinstance(got, int)


def test_norm_row_reads_each_column_from_its_own_key():
    r = data._norm_row({"dq": "1", "b": "2", "c": "3", "cost_usd": "4", "output_tokens": "5", "n_mcp_calls": "6",
                        "n_bash_calls": "7", "wall_time_s": "8", "duration_s": "9"}, "s")
    assert (r["dq"], r["b"], r["c"], r["cost_usd"], r["output_tokens"], r["n_mcp_calls"], r["n_bash_calls"],
            r["wall_s"]) == (1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0)


def test_read_scores_csv_normalises_every_row(tmp_path):
    p = tmp_path / "scores.csv"
    rows = [dict(FULL), {**FULL, "task_id": "T8", "model": "claude-haiku-5-5", "correct": "False", "dq": ""}]
    _write_csv(p, rows)
    got = data._read_scores_csv(p, "name")
    assert [r["task_id"] for r in got] == ["T7", "T8"]
    assert got[0] == data._norm_row(FULL, "name")
    assert got[1]["model"] == "claude-haiku-5-5" and got[1]["correct"] is False and got[1]["dq"] is None
    assert {r["set"] for r in got} == {"name"}


def test_read_scores_csv_keeps_a_line_break_inside_a_quoted_cell(tmp_path, text_io_is_utf8):
    p = tmp_path / "scores.csv"
    with p.open("w", newline="", encoding="utf-8") as fh:
        csv.writer(fh, lineterminator="\n").writerows([["task_id", "class"], ["T1", "a\r\nb"], ["T2", "caf\u00e9"]])
    got = data._read_scores_csv(p, "n")
    assert [r["class"] for r in got] == ["a\r\nb", "caf\u00e9"]
    assert ("open(scores.csv)", "utf-8") in text_io_is_utf8


def test_read_scores_csv_header_only(tmp_path):
    p = tmp_path / "scores.csv"
    p.write_text("model,task_id\n", encoding="utf-8")
    assert data._read_scores_csv(p, "n") == []


# ------------------------------------------------------------------------------------------------ run sets
def _pilot_ids(n=2):
    return sorted(data.pilot_tasks())[:n]


def test_load_runset_reads_scores_and_drops_foreign_task_ids(tmp_path):
    t1, t2 = _pilot_ids()
    d = tmp_path / "rs"
    _manifest(d, split="pilot", finished=False)
    rows = [{**FULL, "task_id": t1}, {**FULL, "task_id": t2, "k_index": "4"}, {**FULL, "task_id": "NOT-A-TASK"},
            {**FULL, "task_id": "C-x-1"}]
    _write_csv(d / "scores.csv", rows)
    rs = data.load_runset(d, "my/name", title="My title")
    assert (rs.name, rs.title, rs.source, rs.live) == ("my/name", "My title", "scores.csv", True)
    assert rs.path == d
    assert [r["task_id"] for r in rs.rows] == [t1, t2]
    assert rs.dropped_non_pilot == 2
    assert rs.scores_sha256 == hashlib.sha256((d / "scores.csv").read_bytes()).hexdigest()
    assert rs.notes == [] and rs.skipped_incomplete == 0
    assert {r["set"] for r in rs.rows} == {"my/name"}


def test_load_runset_default_names(tmp_path):
    t1, _t2 = _pilot_ids()
    d = tmp_path / "folder-name"
    d.mkdir()
    _write_csv(d / "scores.csv", [{**FULL, "task_id": t1}])
    rs = data.load_runset(d)
    assert (rs.name, rs.title, rs.live) == ("folder-name", "folder-name", False)
    rs = data.load_runset(str(d), "given")
    assert (rs.name, rs.title) == ("given", "given")
    rs = data.load_runset(d, "given", False, "A title")
    assert (rs.name, rs.title) == ("given", "A title")
    assert rs.rows[0]["set"] == "given"


def test_load_runset_rescore_reads_transcripts_not_the_csv(tmp_path):
    t1, _t2 = _pilot_ids()
    d = tmp_path / "rs"
    d.mkdir()
    _write_csv(d / "scores.csv", [{**FULL, "task_id": t1, "correct": "True"}])
    rs = data.load_runset(d, rescore=True)
    # no transcripts: nothing to score, but the csv hash is still recorded
    assert rs.source == "rescored" and rs.rows == []
    assert rs.scores_sha256 == hashlib.sha256((d / "scores.csv").read_bytes()).hexdigest()
    rs = data.load_runset(d, rescore=False)
    assert rs.source == "scores.csv" and len(rs.rows) == 1


def test_load_runset_without_csv_has_no_hash(tmp_path):
    d = tmp_path / "rs"
    d.mkdir()
    rs = data.load_runset(d)
    assert rs.source == "rescored" and rs.scores_sha256 is None and rs.rows == []


def _event(kind, **kw):
    return {"type": kind, **kw}


def _transcript(path: pathlib.Path, *, result=True, tool_names=()):
    path.parent.mkdir(parents=True, exist_ok=True)
    events = [{"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": f"t{i}", "name": n, "input": {}} for i, n in enumerate(tool_names)]}}]
    if result:
        events.append({"type": "result", "subtype": "success", "is_error": False, "result": "no answer here",
                       "total_cost_usd": 0.125, "duration_ms": 12500,
                       "usage": {"input_tokens": 10, "output_tokens": 321}})
    path.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")


def test_rescore_scores_transcripts_in_memory_and_writes_nothing(tmp_path):
    t1, t2 = _pilot_ids()
    d = tmp_path / "rs"
    base = d / "claude-haiku-5-5" / "C" / "medium"
    _transcript(base / f"{t1}-k1.jsonl", tool_names=("mcp__ts__fit", "Bash", "mcp__ts__energies"))
    _transcript(base / f"{t2}-k2.jsonl", tool_names=("Bash",))
    _transcript(base / "UNKNOWN-TASK-k1.jsonl")
    before = sorted(p.relative_to(d).as_posix() for p in d.rglob("*"))
    rs = data.load_runset(d, rescore=True)
    assert sorted(p.relative_to(d).as_posix() for p in d.rglob("*")) == before
    assert rs.source == "rescored"
    assert [(r["task_id"], r["k_index"]) for r in rs.rows] == [(t1, 1), (t2, 2)]
    first, second = rs.rows
    assert (first["model"], first["condition"], first["effort"]) == ("claude-haiku-5-5", "C", "medium")
    assert first["class"] == data.pilot_tasks()[t1]["class"]
    assert first["correct"] is False and first["has_result"] is True
    assert (first["n_mcp_calls"], first["n_bash_calls"]) == (2.0, 1.0)
    assert (second["n_mcp_calls"], second["n_bash_calls"]) == (0.0, 1.0)
    assert first["cost_usd"] == 0.125 and first["output_tokens"] == 321.0
    assert first["wall_s"] is not None and first["set"] == "rs"
    assert rs.dropped_non_pilot == 1 and rs.skipped_incomplete == 0


def test_rescore_takes_every_column_from_the_scorer(tmp_path, monkeypatch):
    """The score, the parameters, the measured wall time and the evaluable verdict come from the scorer's functions;
    foreign task ids and live runs before and between the pilot runs are counted, one by one, and skipped."""
    t1, t2 = _pilot_ids()
    d = tmp_path / "rs"
    base = d / "claude-haiku-5-5" / "B" / "medium"
    _transcript(base / "000-foreign-k1.jsonl")  # sorts before the pilot ids
    _transcript(base / "001-foreign-k1.jsonl")
    _transcript(base / f"{t1}-k1.jsonl")
    _transcript(base / f"{t1}-k2.jsonl", result=False)  # live: no result event, no .meta.json
    _transcript(base / f"{t1}-k3.jsonl", result=False)
    _transcript(base / f"{t2}-k1.jsonl")
    from tsbench.score import score
    scores = {t1: {"correct": True, "dq": 1234.5, "b": 678.25, "c": 2950.0}, t2: {"correct": False}}
    monkeypatch.setattr(score, "score_transcript", lambda task, tr: (scores[task["id"]], None))
    (base / f"{t1}-k1.meta.json").write_text(json.dumps({"wall_time_s": 42.5}), encoding="utf-8")
    rs = data.load_runset(d, rescore=True)
    assert rs.dropped_non_pilot == 2 and rs.skipped_incomplete == 2
    first, second = rs.rows
    assert (first["task_id"], first["correct"], first["dq"], first["b"], first["c"]) == (t1, True, 1234.5, 678.25,
                                                                                         2950.0)
    assert (first["wall_s"], first["wall_is_measured"]) == (42.5, True)
    assert (second["task_id"], second["correct"], second["dq"], second["b"], second["c"]) == (t2, False, None, None,
                                                                                              None)
    assert (second["wall_s"], second["wall_is_measured"]) == (12.5, False)  # the result event's duration_ms
    assert first["evaluable"] is True and second["evaluable"] is True


def test_rescore_marks_a_run_the_scorer_calls_not_evaluable(tmp_path, monkeypatch):
    t1, t2 = _pilot_ids()
    d = tmp_path / "rs"
    base = d / "claude-haiku-5-5" / "A" / "medium"
    _transcript(base / f"{t1}-k1.jsonl")
    _transcript(base / f"{t2}-k1.jsonl")
    from tsbench.score import score
    monkeypatch.setattr(score, "not_evaluable_reason", lambda tr: "http_429")
    monkeypatch.setattr(score, "check_runs_match", lambda *_a, **_k: None)
    rs = data.load_runset(d, rescore=True)
    assert [r["evaluable"] for r in rs.rows] == [False, False]


def test_rescore_skips_a_run_that_is_still_being_written(tmp_path):
    t1, t2 = _pilot_ids()
    d = tmp_path / "rs"
    base = d / "claude-haiku-5-5" / "A" / "medium"
    _transcript(base / f"{t1}-k1.jsonl", result=False)  # no result event and no .meta.json: live
    _transcript(base / f"{t2}-k1.jsonl", result=False)
    (base / f"{t2}-k1.meta.json").write_text("{}", encoding="utf-8")  # finished run that has no result event
    rs = data.load_runset(d, rescore=True)
    assert rs.skipped_incomplete == 1
    assert [r["task_id"] for r in rs.rows] == [t2]
    assert rs.rows[0]["has_result"] is False and rs.rows[0]["output_tokens"] is None


def test_rescore_notes_an_unreadable_transcript(tmp_path, monkeypatch):
    t1, t2 = _pilot_ids()
    d = tmp_path / "rs"
    base = d / "claude-haiku-5-5" / "A" / "medium"
    _transcript(base / f"{t1}-k1.jsonl")
    _transcript(base / f"{t2}-k1.jsonl")
    from tsbench.score import extract
    real = extract.read_transcript

    def flaky(path):
        if path.name.startswith(t1):
            raise json.JSONDecodeError("half line", "{", 1)
        return real(path)

    monkeypatch.setattr(extract, "read_transcript", flaky)
    rs = data.load_runset(d, rescore=True)
    assert rs.notes == [f"{t1}-k1.jsonl: unreadable (JSONDecodeError)"]
    assert [r["task_id"] for r in rs.rows] == [t2]


def test_rescore_with_runs_of_another_task_set_is_excluded(tmp_path, monkeypatch):
    t1, _t2 = _pilot_ids()
    d = tmp_path / "rs"
    _transcript(d / "claude-haiku-5-5" / "A" / "medium" / f"{t1}-k1.jsonl")
    from tsbench.score import score

    def boom(*_a, **_k):
        raise ValueError("task set differs")

    monkeypatch.setattr(score, "check_runs_match", boom)
    rs = data.load_runset(d, rescore=True)
    assert rs.rows == [] and rs.notes == ["excluded: task set differs"]


def test_rescore_passes_the_pilot_split_to_the_task_set_check(tmp_path, monkeypatch):
    t1, _t2 = _pilot_ids()
    d = tmp_path / "rs"
    _transcript(d / "claude-haiku-5-5" / "A" / "medium" / f"{t1}-k1.jsonl")
    from tsbench.score import score
    seen = []

    def spy(folder, tasks, version, split):
        seen.append((folder, set(tasks) == set(data.pilot_tasks()), version, split))

    monkeypatch.setattr(score, "check_runs_match", spy)
    data.load_runset(d, rescore=True)
    assert seen == [(d, True, "v2", "pilot")]


def _scored_set(tmp_path, ks=(1, 2)):
    t1, _t2 = _pilot_ids()
    d = tmp_path / "rs"
    base = d / "claude-haiku-5-5" / "A" / "medium"
    for k in ks:
        _transcript(base / f"{t1}-k{k}.jsonl")
    from tsbench.score.score import score_dir
    score_dir(d, "pilot")
    return d, base, t1


def test_load_runset_rescores_a_scores_csv_that_is_older_than_the_transcripts(tmp_path):
    d, base, t1 = _scored_set(tmp_path)
    rs = data.load_runset(d)
    assert rs.source == "scores.csv" and len(rs.rows) == 2 and rs.notes == []
    _transcript(base / f"{t1}-k3.jsonl")  # a run that landed after `tsbench score`
    rs = data.load_runset(d)
    assert rs.source == "rescored" and len(rs.rows) == 3
    assert rs.notes == ["scores.csv is older than the transcripts (1 new): scored in memory"]


def test_load_runset_notes_a_transcript_that_changed_after_scoring(tmp_path):
    d, base, t1 = _scored_set(tmp_path)
    _transcript(base / f"{t1}-k1.jsonl", tool_names=("Bash",))  # overwritten by a re-run
    rs = data.load_runset(d)
    assert rs.source == "rescored" and rs.notes == ["scores.csv is older than the transcripts (1 changed): "
                                                    "scored in memory"]


def test_load_runset_keeps_a_scores_csv_without_transcripts_and_notes_the_difference(tmp_path):
    t1, _t2 = _pilot_ids()
    d = tmp_path / "rs"

    def rid(k):
        return f"claude-haiku-5-5/A/medium/{t1}-k{k}"

    _manifest(d, transcripts={rid(1): "a" * 64, rid(2): "b" * 64})
    _write_csv(d / "scores.csv", [{**FULL, "task_id": t1, "run_id": rid(1), "k_index": "1"}])
    rs = data.load_runset(d)
    assert rs.source == "scores.csv" and len(rs.rows) == 1  # nothing to score from: the table stays
    assert rs.notes == ["scores.csv is older than the transcripts (1 new)"]


def test_rescore_rows_equal_the_rows_score_dir_writes(tmp_path):
    t1, t2 = _pilot_ids()
    d = tmp_path / "rs"
    base = d / "claude-haiku-5-5" / "C" / "medium"
    _transcript(base / f"{t1}-k1.jsonl", tool_names=("mcp__ts__fit", "Bash", "StructuredOutput"))
    _transcript(base / f"{t2}-k1.jsonl", result=False)
    (base / f"{t2}-k1.meta.json").write_text(json.dumps({"wall_time_s": 3.5}), encoding="utf-8")
    from tsbench.score.score import score_dir
    score_dir(d, "pilot")
    written = data.load_runset(d)
    rescored = data.load_runset(d, rescore=True)
    assert written.source == "scores.csv" and rescored.source == "rescored"
    assert [{k: v for k, v in r.items() if k != "set"} for r in rescored.rows] == \
        [{k: v for k, v in r.items() if k != "set"} for r in written.rows]


def test_load_all_accepts_tuples_and_bare_folders(tmp_path):
    t1, _t2 = _pilot_ids()
    a, b = tmp_path / "aa", tmp_path / "bb"
    for p in (a, b):
        p.mkdir()
        _write_csv(p / "scores.csv", [{**FULL, "task_id": t1}])
    sets = data.load_all([(a, "named", "Titled"), b])
    assert [(s.name, s.title, s.path) for s in sets] == [("named", "Titled", a), ("bb", "bb", b)]
    assert data.load_all([]) == []
    sets = data.load_all([str(b)], False)
    assert sets[0].name == "bb" and sets[0].source == "scores.csv"
    sets = data.load_all([(b, "n", "t")], True)
    assert sets[0].source == "rescored" and sets[0].rows == []


# ------------------------------------------------------------------------------------------------ pooling
def _row(model="m", cond="A", effort="medium", task="T1", k=1, ok=True, evaluable=True, set_name="s1"):
    return {"set": set_name, "model": model, "condition": cond, "effort": effort, "task_id": task, "k_index": k,
            "correct": ok, "evaluable": evaluable}


def test_pooled_rows_drops_not_evaluable_and_later_repeats_and_sorts():
    s1 = data.RunSet(path=pathlib.Path("."), name="s1", rows=[
        _row("claude-opus-4-7", "B", task="T2"), _row("claude-haiku-5-5", "C", task="T1", k=2),
        _row("claude-haiku-5-5", "A", task="T9", evaluable=False), _row("zeta", "A"),
        _row("claude-haiku-5-5", "C", task="T1", k=1)])
    s2 = data.RunSet(path=pathlib.Path("."), name="s2", rows=[
        _row("claude-haiku-5-5", "C", task="T1", k=1, ok=False, set_name="s2"),  # repeat of a key of s1
        _row("claude-haiku-5-5", "C", task="T1", k=3, set_name="s2"),
        _row("claude-haiku-5-5", "C", task="T1", k=3, effort="high", set_name="s2"),
        _row("claude-sonnet-5-5", "A", task="T1", set_name="s2"),
        _row("claude-sonnet-5-5", "A", task="T1", set_name="s2")])  # repeat inside one set
    rows, dups = data.pooled_rows([s1, s2])
    assert dups == 2
    keys = [(r["model"], r["condition"], r["effort"], r["task_id"], r["k_index"]) for r in rows]
    assert keys == [("claude-haiku-5-5", "C", "high", "T1", 3), ("claude-haiku-5-5", "C", "medium", "T1", 1),
                    ("claude-haiku-5-5", "C", "medium", "T1", 2), ("claude-haiku-5-5", "C", "medium", "T1", 3),
                    ("claude-sonnet-5-5", "A", "medium", "T1", 1), ("claude-opus-4-7", "B", "medium", "T2", 1),
                    ("zeta", "A", "medium", "T1", 1)]
    kept = [r for r in rows if (r["model"], r["task_id"], r["k_index"], r["effort"]) == ("claude-haiku-5-5", "T1", 1,
                                                                                         "medium")]
    assert len(kept) == 1 and kept[0]["correct"] is True and kept[0]["set"] == "s1"  # the earlier set wins


def test_pooled_rows_of_nothing():
    assert data.pooled_rows([]) == ([], 0)
    assert data.pooled_rows([data.RunSet(path=pathlib.Path("."), name="x")]) == ([], 0)


def test_pooled_rows_does_not_count_a_not_evaluable_repeat():
    s = data.RunSet(path=pathlib.Path("."), name="s", rows=[_row(evaluable=False), _row(), _row(evaluable=False)])
    assert data.pooled_rows([s]) == ([s.rows[1]], 0)


def test_group_by_keeps_row_order_inside_a_group():
    rows = [_row("a", "A", task="1"), _row("b", "A", task="2"), _row("a", "A", task="3"), _row("a", "B", task="4")]
    g = data.group_by(rows, "model", "condition")
    assert list(g) == [("a", "A"), ("b", "A"), ("a", "B")]
    assert [r["task_id"] for r in g[("a", "A")]] == ["1", "3"]
    assert list(data.group_by(rows, "condition")) == [("A",), ("B",)]
    assert data.group_by([], "model") == {}


def test_per_task_is_sorted_by_task_id():
    rows = [_row(task="T2", k=1), _row(task="T10", k=1), _row(task="T2", k=2), _row(task="T1")]
    got = data.per_task(rows)
    assert [t for t, _rs in got] == ["T1", "T10", "T2"]
    assert [len(rs) for _t, rs in got] == [1, 1, 2]
    assert [r["k_index"] for r in got[2][1]] == [1, 2]
    assert data.per_task([]) == []


def test_no_data_error_is_a_runtime_error():
    assert issubclass(data.NoDataError, RuntimeError)
