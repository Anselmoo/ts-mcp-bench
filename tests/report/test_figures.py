"""Tests for src/tsbench/report/run_figures.py: scoring routes, the per-class SVGs, robustness.

Synthetic transcripts only.
"""
from __future__ import annotations

import json
import xml.etree.ElementTree as ET

import pytest

from tsbench.report import run_figures as F
from tsbench.score.extract import read_transcript
from tsbench.tasks import load

pytest.importorskip("matplotlib")
TASKS = {t["id"]: t for t in load("pilot")}


def _result(structured=None, **kw):
    ev = {"type": "result", "subtype": "success", "is_error": False, "result": "ok", "num_turns": 3,
          "total_cost_usd": 0.02, "duration_ms": 4000, "usage": {"input_tokens": 100, "output_tokens": 50}}
    if structured is not None:
        ev["structured_output"] = structured
    ev.update(kw)
    return ev


def _tr(tmp_path, name, result=None, events=()):
    p = tmp_path / "m" / "A" / "medium" / name
    p.parent.mkdir(parents=True, exist_ok=True)
    evs = [{"type": "system", "subtype": "init"}, *events] + ([result] if result is not None else [])
    p.write_text("\n".join(json.dumps(x) for x in evs) + "\n", encoding="utf-8")
    return p


def _eval(task_id, tmp_path, structured=None, result_kw=None, no_result=False):
    task = TASKS[task_id]
    res = None if no_result else _result(structured, **(result_kw or {}))
    p = _tr(tmp_path, f"{task_id}-k1.jsonl", res)
    return p, task, F.evaluate(task, read_transcript(p))


def _fit_answer(task, factor=1.0):
    ref = task["reference"]
    return {"Dq": ref["Dq"] * factor, "B": ref["B"], "C": ref["C"], "out_of_scope": False}


def test_evaluate_verdicts(tmp_path):
    task = TASKS["P-closed_form-01"]
    _, _, ev = _eval("P-closed_form-01", tmp_path, _fit_answer(task))
    assert ev["verdict"] == "correct" and ev["correct"] and ev["category"] == "correct"
    _, _, ev = _eval("P-closed_form-01", tmp_path, _fit_answer(task, 1.2))
    assert ev["verdict"] == "wrong" and "Dq" in ev["reason"] and not ev["correct"]
    _, _, ev = _eval("P-closed_form-01", tmp_path, no_result=True)
    assert ev["verdict"] == "harness" and ev["category"] == "no_result"
    _, _, ev = _eval("P-closed_form-01", tmp_path,
                     result_kw={"is_error": True, "api_error_status": 429, "result": "rate limit"})
    assert ev["verdict"] == "na429" and "429" in ev["reason"]
    p = _tr(tmp_path, "x-k1.jsonl", _result())
    ev = F.evaluate(None, read_transcript(p))
    assert ev["verdict"] == "unscored" and ev["metrics"]["tokens"] == 150 and ev["metrics"]["seconds"] == 4.0


@pytest.mark.parametrize("result_kw", [
    {"is_error": True, "api_error_status": 502, "result": "Bad Gateway"},
    {"is_error": True, "terminal_reason": "api_error", "result": "x"},
    {"is_error": True, "result": "API Error: connection reset"},
    {"is_error": True, "api_error_status": "429", "result": "x"},
    {"is_error": True, "result": "HTTP error (429) from the API"},
])
def test_evaluate_gives_na429_for_every_not_evaluable_run(tmp_path, result_kw):
    """page.STATUS['na429'] is 'not evaluable: rate limit or API error': an API error is no harness verdict."""
    _, _, ev = _eval("P-closed_form-01", tmp_path, result_kw=result_kw)
    assert ev["verdict"] == "na429" and "says nothing about the model" in ev["reason"]


def test_figure_kinds_route_by_schema_and_scope(tmp_path):
    _, t, ev = _eval("P-closed_form-01", tmp_path, _fit_answer(TASKS["P-closed_form-01"]))
    assert F.figure_kinds(t, ev) == ["fit_error", "metrics"]
    _, t, ev = _eval("P-out_of_scope-01", tmp_path, {"Dq": None, "B": None, "C": None, "out_of_scope": True})
    assert ev["verdict"] == "correct" and F.figure_kinds(t, ev) == ["metrics"]
    _, t, ev = _eval("P-closed_form-01", tmp_path, "not json at all")
    assert F.figure_kinds(t, ev)[0] == "no_result"
    assert F.figure_kinds(None, {"has_result": True}) == ["metrics"] and F.figure_kinds(None, {}) == ["no_result"]
    for tid, kind in (("P-curve-01", "curve"), ("P-batch-01", "batch"), ("P-pairing-01", "pairing"),
                      ("P-diagram-01", "diagram")):
        assert F.figure_kinds(TASKS[tid], {"answer": {"x": 1}}) == [kind]


def _check_svg(path):
    text = path.read_text(encoding="utf-8")
    root = ET.fromstring(text)                      # well-formed
    assert root.tag.endswith("svg")
    low = text.lower()
    assert "<script" not in low and "onload" not in low and "http://evil" not in low
    assert "#0039a6" in low or "#8c2d19" in low or "#e6ebf6" in low   # theme colours
    return text


def test_fit_error_figure_has_band_pass_and_fail_marks(tmp_path):
    answer = {**_fit_answer(TASKS["P-racah_c-01"]), "B": TASKS["P-racah_c-01"]["reference"]["B"] * 1.3, "C": None}
    p, task, ev = _eval("P-racah_c-01", tmp_path, answer)
    made = F.make_figures(p, task, ev, {"tokens": 100, "turns": 2, "cost": 0.01, "seconds": 3})
    assert [m["kind"] for m in made] == ["fit_error", "metrics"]
    figs = F.figures_dir_of(p)
    text = _check_svg(figs / "fit_error.svg")
    assert "Relative error (%)" in text and "no value" in text and "ok" in text      # missing C and a pass
    assert (figs / "metrics.svg").is_file() and (figs / F.INDEX).is_file()
    # sits next to the transcript, never elsewhere
    assert figs.parent == p.parent and figs.name == "P-racah_c-01-k1.figs"


def test_curve_diagram_batch_pairing_figures(tmp_path):
    t = TASKS["P-curve-01"]
    pts = [{"dq_over_b": p["dq_over_b"], "e_over_b": p["e_over_b"] * 1.001, "term": p["term"]}
           for p in t["reference_curve"]]
    p, task, ev = _eval("P-curve-01", tmp_path, {"points": pts})
    assert ev["verdict"] == "correct"
    assert [m["kind"] for m in F.make_figures(p, task, ev)] == ["curve"]
    _check_svg(F.figures_dir_of(p) / "curve.svg")

    t = TASKS["P-diagram-01"]
    ref = t["reference"]
    pts = [{"dq_over_b": x, "levels": [{"e_over_b": e, "term": "x"} for e in lv]}
           for x, lv in zip(ref["grid"], ref["levels"], strict=False)][:-1]
    p, task, ev = _eval("P-diagram-01", tmp_path, {"points": pts})
    assert [m["kind"] for m in F.make_figures(p, task, ev)] == ["diagram"]
    text = _check_svg(F.figures_dir_of(p) / "diagram.svg")
    assert "values missing" in text                                  # the dropped grid point is reported

    t = TASKS["P-batch-01"]
    vals = [{"input": v["input"], "result": v["result"] * (1.1 if i == 0 else 1.0)}
            for i, v in enumerate(t["reference"]["values"])]
    p, task, ev = _eval("P-batch-01", tmp_path, {"values": vals})
    assert ev["verdict"] == "wrong"
    assert [m["kind"] for m in F.make_figures(p, task, ev)] == ["batch"]
    _check_svg(F.figures_dir_of(p) / "batch.svg")

    t = TASKS["P-pairing-01"]
    p, task, ev = _eval("P-pairing-01", tmp_path, {"nodes": [], "edges": []})
    assert ev["answer"] is not None and ev["verdict"] == "wrong"
    assert [m["kind"] for m in F.make_figures(p, task, ev)] == ["pairing"]
    text = _check_svg(F.figures_dir_of(p) / "pairing.svg")
    assert "Edge F1" in text and "Score (fraction)" in text


def test_no_result_card_and_metrics_for_out_of_scope(tmp_path):
    p, task, ev = _eval("P-closed_form-01", tmp_path, no_result=True)
    made = F.make_figures(p, task, ev)
    assert [m["kind"] for m in made] == ["no_result"]
    assert "no evaluable result" in (F.figures_dir_of(p) / "no_result.svg").read_text(encoding="utf-8")
    # numbers instead of a refusal
    p, task, ev = _eval("P-out_of_scope-01", tmp_path, _fit_answer(TASKS["P-closed_form-01"]))
    assert ev["verdict"] == "wrong"
    made = F.make_figures(p, task, ev, {"tokens": 100, "turns": 2, "cost": 0.01, "seconds": 3})
    assert [m["kind"] for m in made] == ["metrics"]
    text = (F.figures_dir_of(p) / "metrics.svg").read_text(encoding="utf-8")
    assert "Refusal correct" in text and "Relative to class median" in text


def test_second_call_reuses_files_and_output_is_deterministic(tmp_path):
    p, task, ev = _eval("P-closed_form-01", tmp_path, _fit_answer(TASKS["P-closed_form-01"]))
    a = F.make_figures(p, task, ev)
    svg = F.figures_dir_of(p) / "fit_error.svg"
    first = svg.read_bytes()
    mtime = svg.stat().st_mtime_ns
    assert F.make_figures(p, task, ev) == a and svg.stat().st_mtime_ns == mtime     # fresh: not drawn again
    F.make_figures(p, task, ev, force=True)
    assert svg.read_bytes() == first                                                # same bytes (no date, fixed salt)


def test_one_failing_figure_does_not_stop_the_others(tmp_path, monkeypatch, capsys):
    p, task, ev = _eval("P-closed_form-01", tmp_path, _fit_answer(TASKS["P-closed_form-01"]))

    def boom(*a, **k):
        raise RuntimeError("broken")
    monkeypatch.setattr(F, "fig_fit_error", boom)
    made = F.make_figures(p, task, ev, force=True)
    assert [m["kind"] for m in made] == ["metrics"]
    assert "fit_error skipped" in capsys.readouterr().err


def test_without_matplotlib_no_figures_and_no_crash(tmp_path, monkeypatch):
    monkeypatch.setitem(F._MPL, "v", None)
    p, task, ev = _eval("P-closed_form-01", tmp_path, _fit_answer(TASKS["P-closed_form-01"]))
    assert F.make_figures(p, task, ev, force=True) == []


def test_class_medians():
    m = F.class_medians([("a", {"tokens": 10, "turns": 2}), ("a", {"tokens": 30, "turns": None}), ("b", {"tokens": 5})])
    assert m == {"a": {"tokens": 20, "turns": 2}, "b": {"tokens": 5}}


def _mtimes(p, *names):
    figs = F.figures_dir_of(p)
    return [(figs / n).stat().st_mtime_ns for n in names]


def test_a_changed_answer_with_the_same_verdict_redraws_the_figures(tmp_path):
    task = TASKS["P-closed_form-01"]
    medians = {"tokens": 100, "turns": 2, "cost": 0.01, "seconds": 3}
    p, task, ev = _eval("P-closed_form-01", tmp_path, _fit_answer(task, 1.5))
    F.make_figures(p, task, ev, medians)
    svg = F.figures_dir_of(p) / "fit_error.svg"
    first = svg.read_bytes()
    answer = {**ev["answer"], "Dq": ev["answer"]["Dq"] * 1.2}          # another answer, the verdict stays "wrong"
    changed = {**ev, "answer": answer, "row": {**ev["row"], "rel_err_dq": 0.9}}
    assert changed["verdict"] == ev["verdict"] == "wrong"
    F.make_figures(p, task, changed, medians)
    assert svg.read_bytes() != first


def test_a_shifted_class_median_redraws_only_the_metrics_figure(tmp_path):
    p, task, ev = _eval("P-closed_form-01", tmp_path, _fit_answer(TASKS["P-closed_form-01"]))
    F.make_figures(p, task, ev, {"tokens": 100, "turns": 2, "cost": 0.01, "seconds": 3})
    fit, metrics = _mtimes(p, "fit_error.svg", "metrics.svg")
    made = F.make_figures(p, task, ev, {"tokens": 100.5, "turns": 2, "cost": 0.01, "seconds": 3})
    assert [m["kind"] for m in made] == ["fit_error", "metrics"]
    assert _mtimes(p, "fit_error.svg") == [fit]                          # uses no median: kept
    assert _mtimes(p, "metrics.svg") != [metrics]                        # uses the medians: drawn again
    again = _mtimes(p, "fit_error.svg", "metrics.svg")
    F.make_figures(p, task, ev, {"tokens": 100.5, "turns": 2, "cost": 0.01, "seconds": 3})
    assert _mtimes(p, "fit_error.svg", "metrics.svg") == again           # nothing changed: nothing drawn
