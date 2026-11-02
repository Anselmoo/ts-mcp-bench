import json
import pathlib
import re

import numpy as np
import pytest

from tsbench.tasks.classes import batch

SCHEMA = pathlib.Path(__file__).resolve().parents[3] / "src" / "tsbench" / "data" / "schemas" / "batch.schema.json"
KEYS = {"answer_schema", "bands_cm1", "class", "d_count", "expect_out_of_scope", "geometry", "oracle", "params",
        "prompt", "reference", "reference_curve", "required", "subtype", "system", "tolerance"}


@pytest.fixture(scope="module")
def tasks():
    return batch.make_batch(np.random.default_rng(20261025))


def test_counts_keys_and_subtypes(tasks):
    pilot, conf = tasks
    assert (len(pilot), len(conf)) == (3, 4)
    for r in pilot + conf:
        assert set(r) == KEYS
        assert r["class"] == "batch" and r["answer_schema"] == "batch" and r["oracle"] == "forward_model"
        assert r["subtype"] in ("crossover_series", "band_series")
        assert len(r["reference"]["values"]) == 8
    assert {r["subtype"] for r in pilot} == {"crossover_series", "band_series"}
    assert {r["subtype"] for r in conf} == {"crossover_series", "band_series"}


def test_determinism():
    a = batch.make_batch(np.random.default_rng(7))
    b = batch.make_batch(np.random.default_rng(7))
    assert a == b
    assert a != batch.make_batch(np.random.default_rng(8))


def test_oracle_matches_compute(tasks):
    from tanabesugano.mcp import _compute as comp
    for r in sum(tasks, []):
        d, p = r["d_count"], r["params"]
        for v in r["reference"]["values"]:
            if r["subtype"] == "crossover_series":
                b, c = p["B"], v["input"] * p["B"]
                strong = comp.ground_term(comp.compute_point(d, comp.STRONG_FIELD_DQ_CM1, b, c))[0]
                want = comp.crossover_dq(d, b, c, strong, tol=0.05)
                assert 3.8 <= v["input"] <= 5.0
            else:
                _, cands = comp.transition_candidates(comp.compute_point(d, v["input"], p["B"], p["C"]))
                want = cands[0][0]
            assert v["result"] == pytest.approx(want, abs=0.01)


def test_band_series_follows_ground_term_change():
    """d6 across the spin crossover: the first band must come from the ground term at that Dq."""
    from tanabesugano.mcp import _compute as comp
    b, c = 700.0, 3100.0
    x = batch.crossover_value(6, b, c)
    lo = batch.first_allowed_band(6, 0.5 * x, b, c)
    hi = batch.first_allowed_band(6, 1.5 * x, b, c)
    g_lo = comp.ground_term(comp.compute_point(6, 0.5 * x, b, c))[0]
    g_hi = comp.ground_term(comp.compute_point(6, 1.5 * x, b, c))[0]
    assert g_lo != g_hi and lo != hi


def test_prompts_do_not_leak(tasks):
    for r in sum(tasks, []):
        prompt = r["prompt"]
        assert not re.search(r"tool|mcp|tanabesugano|compute_point|crossover_dq", prompt, re.I)
        numbers = {int(round(float(n.replace(batch.NBSP, "")))) for n in re.findall(r"\d[\d ]*(?:\.\d+)?", prompt)}
        for v in r["reference"]["values"]:
            assert int(round(v["result"])) not in numbers
            assert f"{v['result']:.1f}" not in prompt
        assert "result" not in json.dumps(r["params"])


def test_schema_is_valid_json_schema():
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    v = jsonschema.Draft202012Validator(schema)
    assert not list(v.iter_errors({"values": [{"input": 1.0, "result": None}, {"input": 2, "result": 3.5}],
                                   "reason": "x"}))
    assert list(v.iter_errors({"values": [{"input": 1.0}], "reason": "x"}))
    assert list(v.iter_errors({"values": [], "reason": "x", "extra": 1}))
    assert list(v.iter_errors({"values": []}))
    assert schema["additionalProperties"] is False and set(schema["required"]) == {"values", "reason"}
