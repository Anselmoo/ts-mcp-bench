"""PROV-JSON and the hash chain over trace records (tsbench.core.trace_prov). The records here are written by hand in
the format of tsbench.core.trace, so these tests do not depend on the tracer itself."""
from __future__ import annotations

import importlib
import json

import pytest

H1, H2, H3, H4 = ("1" * 64, "2" * 64, "3" * 64, "4" * 64)


@pytest.fixture
def prov():
    return importlib.import_module("tsbench.core.trace_prov")


def read(path: str, sha: str | None) -> dict:
    return {"event": "open", "path": path, "mode": "r", "caller": "tsbench.x:f", "sha256_at_read": sha,
            "sha256_at_end": sha}


def write(path: str, sha: str | None) -> dict:
    return {"event": "open", "path": path, "mode": "w", "caller": "tsbench.x:f", "sha256_at_read": None,
            "sha256_at_end": sha}


def rename(src: str, dst: str, sha: str | None) -> dict:
    return {"event": "rename", "path": src, "target": dst, "mode": None, "caller": "tsbench.x:f",
            "sha256_at_read": None, "sha256_at_end": sha}


def record(step: str, pid: int, start: float, files: list[dict], calls: list[dict] | None = None) -> dict:
    return {"schema": "tsbench.trace/1", "pid": pid, "ppid": 1, "argv": ["tsbench", step],
            "command": f"tsbench {step}", "cwd": "/w", "start": start, "end": start + 0.5, "exit_code": 0,
            "calls": calls or [], "files": files, "step": step}


def chain() -> list[dict]:
    """plan-build writes plan.jsonl through a .tmp file; run reads it and writes a transcript; score reads that."""
    return [
        record("plan-build", 10, 0.0, [write("/w/plan/plan.jsonl.tmp", None),
                                       rename("/w/plan/plan.jsonl.tmp", "/w/plan/plan.jsonl", H1)]),
        record("run", 20, 2.0, [read("/w/plan/plan.jsonl", H1), write("/w/runs/t.jsonl", H2),
                                read("/w/src/tasks.jsonl", H4)]),
        record("score", 30, 4.0, [read("/w/runs/t.jsonl", H2), write("/w/runs/scores.csv", H3)]),
    ]


# ---------------------------------------------------------------- inputs and outputs of one record
def test_inputs_are_reads_with_their_hash_at_read(prov):
    run = chain()[1]
    assert prov.inputs(run) == {"/w/plan/plan.jsonl": H1, "/w/src/tasks.jsonl": H4}


def test_outputs_are_writes_and_rename_targets_with_their_hash_at_end(prov):
    plan = chain()[0]
    assert prov.outputs(plan) == {"/w/plan/plan.jsonl": H1}, "the .tmp file is gone at the end and is no output"
    assert prov.outputs(chain()[2]) == {"/w/runs/scores.csv": H3}


# ---------------------------------------------------------------- PROV-JSON
def test_prov_json_has_one_activity_per_record_and_one_entity_per_file_version(prov):
    doc = prov.to_prov(chain())
    json.dumps(doc)  # serialisable as it is
    assert {"prefix", "entity", "activity", "used", "wasGeneratedBy"} <= set(doc)
    assert len(doc["activity"]) == 3
    assert {prov.activity_id(r) for r in chain()} == set(doc["activity"])
    shas = sorted(e["tsbench:sha256"] for e in doc["entity"].values())
    assert shas == sorted([H1, H2, H3, H4])
    assert all("tsbench:path" in e for e in doc["entity"].values())
    act = doc["activity"][prov.activity_id(chain()[2])]
    assert act["tsbench:command"] == "tsbench score" and "prov:startTime" in act and "prov:endTime" in act


def test_used_and_generated_share_the_entity_of_the_same_file_version(prov):
    doc = prov.to_prov(chain())
    plan_id, run_id = prov.activity_id(chain()[0]), prov.activity_id(chain()[1])
    generated = {g["prov:entity"] for g in doc["wasGeneratedBy"].values() if g["prov:activity"] == plan_id}
    used = {u["prov:entity"] for u in doc["used"].values() if u["prov:activity"] == run_id}
    assert len(generated) == 1 and generated <= used
    assert len(doc["used"]) == 3 and len(doc["wasGeneratedBy"]) == 3


# ---------------------------------------------------------------- the hash chain
def test_an_intact_chain_has_no_breaks(prov):
    assert prov.hash_chain(chain()) == []


def test_an_input_that_differs_from_its_producer_is_a_break(prov):
    recs = chain()
    recs[2]["files"][0]["sha256_at_read"] = H4  # the transcript changed between run and score
    (brk,) = prov.hash_chain(recs)
    assert brk["path"] == "/w/runs/t.jsonl"
    assert brk["expected"] == H2 and brk["found"] == H4
    assert brk["producer"] == prov.activity_id(recs[1]) and brk["consumer"] == prov.activity_id(recs[2])


def test_the_latest_producer_decides(prov):
    recs = chain()
    recs.insert(2, record("rewrite", 25, 3.0, [write("/w/runs/t.jsonl", H3)]))
    (brk,) = prov.hash_chain(recs)
    assert brk["expected"] == H3 and brk["found"] == H2
    recs[3]["files"][0]["sha256_at_read"] = H3
    assert prov.hash_chain(recs) == []


def test_inputs_without_a_producer_and_a_process_reading_its_own_output_are_no_breaks(prov):
    recs = chain()
    recs[2]["files"].append(read("/w/runs/scores.csv", H1))  # score reads back a file it wrote itself
    assert prov.hash_chain(recs) == []  # /w/src/tasks.jsonl has no producer either


def test_a_producer_that_started_after_the_reader_does_not_count(prov):
    recs = chain()
    late = record("later", 40, 10.0, [write("/w/plan/plan.jsonl", H4)])
    assert prov.hash_chain([*recs, late]) == []


# ---------------------------------------------------------------- loading a trace folder
def test_load_records_reads_one_folder_per_step_sorted_by_start(prov, tmp_path):
    root = tmp_path / "trace"
    for rec in reversed(chain()):
        d = root / rec["step"]
        d.mkdir(parents=True, exist_ok=True)
        body = {k: v for k, v in rec.items() if k != "step"}
        (d / f"{rec['pid']}.trace.json").write_text(json.dumps(body), encoding="utf-8")
    (root / "run" / "broken.trace.json").write_text("{not json", encoding="utf-8")
    (root / "run" / "notes.txt").write_text("x", encoding="utf-8")
    loaded = prov.load_records(root)
    assert [r["step"] for r in loaded] == ["plan-build", "run", "score"]
    assert [r["pid"] for r in loaded] == [10, 20, 30]
    assert prov.hash_chain(loaded) == []


def test_load_records_of_a_missing_folder_is_empty(prov, tmp_path):
    assert prov.load_records(tmp_path / "nope") == []
