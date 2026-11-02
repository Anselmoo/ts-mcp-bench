"""diagram task class: oracle, records, and the rule that the records before the diagram class match the committed
task file byte for byte."""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import subprocess

import numpy as np
import pytest

from tsbench.core import resource
from tsbench.tasks import load
from tsbench.tasks.classes import diagram as D

HERE = pathlib.Path(__file__).resolve().parents[1]
FIELDS = {"id", "split", "class", "subtype", "d_count", "geometry", "system", "bands_cm1", "prompt", "required",
          "reference", "tolerance", "oracle", "expect_out_of_scope", "answer_schema", "params", "reference_curve"}


def _head_lines() -> list[bytes] | None:
    try:
        out = subprocess.run(["git", "show", "HEAD:src/tsbench/data/tasks/tasks.jsonl"],
                             capture_output=True, cwd=HERE, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.splitlines(keepends=True) if out.returncode == 0 else None


def test_records_before_diagram_match_the_committed_file_and_diagram_is_last():
    head = _head_lines()
    if head is None:
        pytest.skip("git history not available")
    new = resource("tasks/tasks.jsonl").read_bytes().splitlines(keepends=True)
    # The confirmatory `experimental` and `literature_all` records follow the separation of systems (rubric.md), so
    # they are left out, and so are the confirmatory records of the pilot-only classes. Compare by id and digest, never
    # printing a record: every other line before the tail classes is byte-identical and keeps its relative order. The
    # numerical_hard records are compared by test_numerical_hard_prompts_state_spin_state_and_ground_term instead.
    sep = {"experimental", "literature_all", "closed_form", "batch", "pairing"}

    def keyed(lines):
        out = {}
        for ln in lines:
            r = json.loads(ln)
            if (r["class"] != "diagram" and r["class"] != "literature_new"
                    and not (r["split"] == "confirmatory" and r["class"] in sep)):
                out[r["id"]] = hashlib.sha256(ln).digest()
        return out
    old_k, new_k = keyed(head), keyed(new)
    hard = {json.loads(ln)["id"] for ln in head if json.loads(ln)["class"] == "numerical_hard"}
    bad = [i for i in old_k if i not in hard and new_k.get(i) != old_k[i]]
    assert not bad, f"{len(bad)} records before the diagram class differ in bytes or are missing (first {bad[0]})"
    assert list(old_k) == [i for i in new_k if i in old_k], "order of the records before the diagram class differs"
    ids = [json.loads(ln)["id"] for ln in new]
    assert len(new) == 105 and ids[89:99] == [f"{p}-diagram-0{i}" for p in "PC" for i in range(1, 6)]
    assert ids[99:] == [f"P-literature_new-0{i}" for i in range(1, 7)]  # after diagram
    assert all(json.loads(ln)["class"] != "diagram" for ln in new[:89])


def test_counts_and_record_shape():
    for split in ("pilot", "confirmatory"):
        recs = [r for r in load(split) if r["class"] == "diagram"]
        assert [r["d_count"] for r in recs] == [3, 4, 5, 6, 7]
        for r in recs:
            assert set(r) == FIELDS
            assert (r["answer_schema"], r["oracle"], r["geometry"], r["expect_out_of_scope"]) == (
                "diagram", "forward_model", "Oh", False)
            assert r["reference_curve"] is None and r["required"] == [] and r["bands_cm1"] == []
            ref = r["reference"]
            assert ref["grid"] == [0.5 * i for i in range(9)]
            assert len(ref["levels"]) == len(ref["labels"]) == 9
            for lv, lab in zip(ref["levels"], ref["labels"], strict=False):
                assert len(lv) == len(lab) == 6 and lv[0] == 0.0 and lv == sorted(lv)
            b, c = r["params"]["B"], r["params"]["C"]
            assert 4.0 <= c / b <= 4.8 + 1e-3 and D.B_RANGE[r["d_count"]][0] <= b <= D.B_RANGE[r["d_count"]][1]
    p = {r["d_count"]: r["params"] for r in load("pilot") if r["class"] == "diagram"}
    c = {r["d_count"]: r["params"] for r in load("confirmatory") if r["class"] == "diagram"}
    assert all(abs(p[d]["B"] - c[d]["B"]) / p[d]["B"] >= D.MIN_B_DIFFERENCE for d in p)


def test_prompt_names_no_tool_and_states_the_convention():
    for r in load("pilot"):
        if r["class"] != "diagram":
            continue
        text = r["prompt"]
        assert "diagram.png" in text and "lowest 6 levels" in text and "regardless of its orbital degeneracy" in text
        assert not re.search(r"\b(ts_|mcp|tanabesugano|python|tool|bash|script|matplotlib)", text, re.I)


def test_oracle_matches_compute_point_and_dq0_needs_no_substitute():
    from tanabesugano.mcp import _compute
    rng = np.random.default_rng([20261025, 12])
    for r in D.make_diagram(rng)[0]:
        d, b, c = r["d_count"], r["params"]["B"], r["params"]["C"]
        for x, lv in zip(r["reference"]["grid"], r["reference"]["levels"], strict=False):
            vals = sorted(float(e) for v in _compute.compute_point(d, x * b, b, c).values() for e in v)
            assert lv == pytest.approx([(e - vals[0]) / b for e in vals[:6]], abs=1e-3)
        tiny = sorted(float(e) for v in _compute.compute_point(d, 1e-6 * b, b, c).values() for e in v)
        zero = sorted(float(e) for v in _compute.compute_point(d, 0.0, b, c).values() for e in v)
        assert zero[:6] == pytest.approx(tiny[:6], abs=1e-4 * b)


def test_level_convention_counts_coincident_components_separately():
    e, labels = D.levels_at(6, 0.0, 700.0, 3100.0)
    assert e[:2] == [0.0, 0.0] and len(set(e[2:])) == 1 and e[2] > 0 and len(labels) == 6
    e5, _ = D.levels_at(5, 0.0, 700.0, 3100.0)
    assert e5[0] == 0.0 and e5[1] > 0   # d5: a single ground level (6A1)


def test_generation_is_deterministic():
    a = D.make_diagram(np.random.default_rng([20261025, 12]))
    b = D.make_diagram(np.random.default_rng([20261025, 12]))
    assert a == b
