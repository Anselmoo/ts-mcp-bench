"""Tests for src/tsbench/score/sensitivity.py: synthetic transcripts in tmp_path, pilot tasks via load only."""
from __future__ import annotations

import json
import pathlib

import pytest

from tsbench.score.score import score_dir
from tsbench.score.sensitivity import DEFAULT_SCALES, SENSITIVITY_COLUMNS, scale_tolerance, tolerance_curve
from tsbench.tasks import load

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
FIX = REPO_ROOT / "src" / "tsbench" / "run" / "fake_cli_fixtures"
M = "claude-haiku-5-5"


def _write(path, final_text, result=True, cond="A"):
    path.parent.mkdir(parents=True, exist_ok=True)
    events = [json.loads((FIX / f"init_{cond}.json").read_text(encoding="utf-8")),
              {"type": "assistant", "message": {"content": [{"type": "text", "text": final_text}]}}]
    if result:
        events.append({"type": "result", "subtype": "success", "is_error": False, "result": final_text,
                       "usage": {"input_tokens": 1, "output_tokens": 1}})
    path.write_text("".join(json.dumps(e) + "\n" for e in events), encoding="utf-8")


def _line(dq, b, oos=False):
    return json.dumps({"Dq": dq, "B": b, "C": None, "out_of_scope": oos, "reason": "t"})


def _first(cls, subtype=None):
    return next(t for t in load("pilot") if t["class"] == cls and (subtype is None or t["subtype"] == subtype))


def _runs(root, effort="medium", model=M, cond="A"):
    cf = _first("closed_form")
    ct = _first("out_of_scope", "charge_transfer")
    dq, b = cf["reference"]["Dq"], cf["reference"]["B"]
    base = root / "runs" / model / cond / effort
    tol_dq = cf["tolerance"]["Dq"]
    _write(base / f"{cf['id']}-k1.jsonl", _line(dq, b), cond=cond)                    # exact
    _write(base / f"{cf['id']}-k2.jsonl", _line(dq * (1 + 1.5 * tol_dq), b), cond=cond)  # correct from s=2
    # 90 % off: beyond 10 x the tolerance
    _write(base / f"{cf['id']}-k3.jsonl", _line(dq * 1.9, b), cond=cond)
    _write(base / f"{ct['id']}-k1.jsonl", _line(None, None, oos=True), cond=cond)      # oos, scale-free
    _write(base / f"{ct['id']}-k2.jsonl", _line(1.0, 1.0), cond=cond)                  # missed limit, always wrong
    _write(base / f"{cf['id']}-k4.jsonl", "no json", result=False, cond=cond)          # no result event
    _write(base / "NOT-A-TASK-k1.jsonl", _line(dq, b), cond=cond)                      # outside the split
    return root / "runs"


def test_scale_tolerance_copies_and_keeps_null():
    exp = _first("experimental")
    before = json.dumps(exp, sort_keys=True)
    out = scale_tolerance(exp, 2)
    assert json.dumps(exp, sort_keys=True) == before
    assert out is not exp and out["tolerance"] is not exp["tolerance"]
    assert out["tolerance"]["Dq"] == pytest.approx(exp["tolerance"]["Dq"] * 2)
    assert out["tolerance"]["C"] is None


def test_constants():
    assert tuple(DEFAULT_SCALES) == (0.25, 0.5, 1, 2, 4, 10)
    assert SENSITIVITY_COLUMNS == ["model", "condition", "effort", "scale", "n", "n_correct", "accuracy"]


def test_curve_rows_shape_and_monotone(tmp_path):
    curve = tolerance_curve(_runs(tmp_path), "pilot")
    assert len(curve) == len(DEFAULT_SCALES)
    assert all(list(r) == SENSITIVITY_COLUMNS for r in curve)
    assert all(r["n"] == 6 for r in curve)  # unknown task id skipped, no-result run counted
    ns = [r["n_correct"] for r in curve]
    assert ns == sorted(ns)
    by = {r["scale"]: r for r in curve}
    assert by[0.25]["n_correct"] == by[1]["n_correct"] == 2  # exact + true limit
    assert by[2]["n_correct"] == 3                           # 1.5 * tol is within 2 * tol
    assert by[1]["accuracy"] == pytest.approx(2 / 6)


def test_scale_one_matches_score_dir(tmp_path):
    runs = _runs(tmp_path)
    rows = score_dir(runs, "pilot")["rows"]
    at1 = [r for r in tolerance_curve(runs, "pilot") if r["scale"] == 1]
    assert len(at1) == 1
    assert at1[0]["n"] == len(rows) and at1[0]["n_correct"] == sum(bool(r["correct"]) for r in rows)


def test_cells_and_custom_scales(tmp_path):
    runs = _runs(tmp_path)
    _runs(tmp_path, effort="high", cond="B")
    curve = tolerance_curve(runs, "pilot", scales=(1, 1.6))
    assert len(curve) == 2 * 2
    assert {(r["condition"], r["effort"]) for r in curve} == {("A", "medium"), ("B", "high")}
    assert {r["scale"] for r in curve} == {1.0, 1.6}


def test_empty_runs_dir(tmp_path):
    (tmp_path / "runs").mkdir()
    assert tolerance_curve(tmp_path / "runs", "pilot") == []


def test_scale_tolerance_copies_everything_deeply():
    exp = _first("experimental")
    out = scale_tolerance(exp, 3)
    assert out["reference"] is not exp["reference"]
    out["reference"]["Dq"] = -1.0
    assert exp["reference"]["Dq"] != -1.0
    assert scale_tolerance({"id": "x"}, 2) == {"id": "x"}                     # no tolerance: nothing to scale
    assert scale_tolerance({"tolerance": None}, 2) == {"tolerance": None}


def test_curve_default_split_and_arguments(tmp_path, monkeypatch):
    import tsbench.tasks
    runs = _runs(tmp_path)
    assert tolerance_curve(runs) == tolerance_curve(runs, "pilot")
    seen = []
    real = tsbench.tasks.load

    def spy(split, version):
        seen.append((split, version))
        return real(split, version)

    monkeypatch.setattr(tsbench.tasks, "load", spy)
    tolerance_curve(runs)
    tolerance_curve(runs, "pilot", (1,), "v2")
    assert seen == [("pilot", "v2"), ("pilot", "v2")]


def test_scale_tolerance_leaves_the_diagram_pass_share_alone():
    """item_accuracy_min is a required share of correct values, not a tolerance: it must not move with the scale."""
    from tsbench.run import fake_cli
    from tsbench.score.diagram_score import score_diagram

    t = _first("diagram")
    share = t["tolerance"]["item_accuracy_min"]
    exact = fake_cli.answer_for(t, True, "diagram")
    for s in DEFAULT_SCALES:
        scaled = scale_tolerance(t, s)
        assert scaled["tolerance"]["item_accuracy_min"] == share
        assert scaled["tolerance"]["curve_abs"] == pytest.approx(t["tolerance"]["curve_abs"] * s)
        assert scaled["tolerance"]["curve_rel"] == pytest.approx(t["tolerance"]["curve_rel"] * s)
        res = score_diagram(scaled, exact)
        assert res["item_accuracy"] == 1.0 and res["correct"], s


def _write_429(path, cond="A"):
    path.parent.mkdir(parents=True, exist_ok=True)
    events = [json.loads((FIX / f"init_{cond}.json").read_text(encoding="utf-8")),
              {"type": "result", "subtype": "success", "is_error": True, "api_error_status": 429,
               "result": "API Error: Request rejected (429)", "usage": {"input_tokens": 0, "output_tokens": 0}}]
    path.write_text("".join(json.dumps(e) + "\n" for e in events), encoding="utf-8")


def test_curve_skips_runs_that_are_not_evaluable(tmp_path):
    """An HTTP 429 run is neither right nor wrong: it is not part of n, as in rates.csv."""
    runs = _runs(tmp_path)
    cf = _first("closed_form")
    _write_429(runs / M / "A" / "medium" / f"{cf['id']}-k5.jsonl")
    curve = tolerance_curve(runs, "pilot")
    assert all(r["n"] == 6 for r in curve)
    assert {r["scale"]: r["n_correct"] for r in curve}[1.0] == 2


def test_curve_extracts_each_answer_once_not_once_per_scale(tmp_path, monkeypatch):
    """The answer does not depend on the scale: extraction runs once per transcript, only the judging repeats."""
    import tsbench.score.score as score_mod

    runs = _runs(tmp_path)
    expected = tolerance_curve(runs, "pilot")
    calls = []
    real = score_mod.rescue_stop_reason
    monkeypatch.setattr(score_mod, "rescue_stop_reason", lambda tr: calls.append(1) or real(tr))
    assert tolerance_curve(runs, "pilot") == expected
    assert len(calls) == 6  # six transcripts of tasks in the split, six scales


def test_curve_reads_a_transcript_only_when_it_is_not_in_the_cache(tmp_path, monkeypatch):
    import builtins

    from tsbench.score import extract

    runs = _runs(tmp_path)
    cache = {}
    expected = tolerance_curve(runs, "pilot", transcripts=cache)
    assert len(cache) == 6  # six transcripts of tasks in the split
    opened = []

    def spy(*args, **kwargs):
        opened.append(str(args[0]))
        return builtins.open(*args, **kwargs)

    monkeypatch.setattr(extract, "open", spy, raising=False)
    assert tolerance_curve(runs, "pilot", transcripts=cache) == expected
    assert [p for p in opened if p.endswith(".jsonl")] == []
