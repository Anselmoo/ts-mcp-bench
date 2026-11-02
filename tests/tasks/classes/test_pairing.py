"""Tests for the pairing oracle (microstate count). No network, no LLM."""
import json
import math
import pathlib

import jsonschema
import numpy as np
import pytest

from tsbench.tasks.classes import pairing as p

SCHEMA_FILE = pathlib.Path(__file__).resolve().parents[3] / "src/tsbench/data/schemas/pairing.schema.json"
SCHEMA = json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))

TEXTBOOK = {
    2: {"3F": 1, "3P": 1, "1G": 1, "1D": 1, "1S": 1},
    3: {"4F": 1, "4P": 1, "2H": 1, "2G": 1, "2F": 1, "2D": 2, "2P": 1},
    4: {"5D": 1, "3H": 1, "3G": 1, "3F": 2, "3D": 1, "3P": 2, "1I": 1, "1G": 2, "1F": 1, "1D": 2, "1S": 2},
}


@pytest.mark.parametrize("n", range(1, 10))
def test_total_microstates(n):
    assert p.n_microstates(n) == math.comb(10, n)


@pytest.mark.parametrize("n", sorted(TEXTBOOK))
def test_textbook_terms(n):
    assert p.terms(n) == TEXTBOOK[n]


def test_term_counts():
    assert [sum(p.terms(n).values()) for n in (1, 2, 3, 4, 5)] == [1, 5, 8, 16, 16]


@pytest.mark.parametrize("n", range(1, 6))
def test_particle_hole(n):
    assert p.terms(n) == p.terms(10 - n)


def test_d4_multiplicities():
    t = p.terms(4)
    assert all(t[k] == 2 for k in ("3P", "3F", "1G", "1D", "1S"))


def test_d2_terms_in_d4_d6():
    assert set(p.terms(2)) <= set(p.terms(4)) == set(p.terms(6))


@pytest.mark.parametrize("n,g", [(1, "2D"), (2, "3F"), (3, "4F"), (4, "5D"), (5, "6S"),
                                 (6, "5D"), (7, "4F"), (8, "3F"), (9, "2D")])
def test_hund_ground(n, g):
    assert p.ground_term(n) == g


def test_matches_tanabesugano_free_ion():
    fi = pytest.importorskip("tanabesugano.free_ion")
    for n in range(2, 9):
        got = {}
        for lv in fi.free_ion_levels(n, 800.0, 3600.0):
            key = f"{lv.multiplicity}{lv.orbital.value}"
            got[key] = got.get(key, 0) + 1
        if n == 5:
            continue  # the package's d5 table is not a full term list; the others must agree exactly
        assert got == p.terms(n), n


def test_reference_edges_main_task():
    ref = p.reference(["d2", "d4", "d6", "d8"])
    assert len(ref["edges"]) == 5 + 5 + 5 + 11 + 5 + 5
    assert {"a": "d2", "b": "d8", "term": "3F"} in ref["edges"]
    assert sum(n["ground"] for n in ref["nodes"]) == 4


def test_d5_shares_nothing_with_d4_d6():
    ref = p.reference(["d4", "d5", "d6"])
    assert {e["a"] + e["b"] for e in ref["edges"]} == {"d4d6"}


def test_make_pairing_shape():
    pilot, conf = p.make_pairing(np.random.default_rng(1))
    assert (len(pilot), len(conf)) == (1, 3)
    for r in pilot + conf:
        assert r["class"] == "pairing" and r["answer_schema"] == "pairing" and r["oracle"] == "microstate_count"
        assert r["prompt"] and r["reference"]["nodes"]
        jsonschema.validate({"nodes": r["reference"]["nodes"], "edges": r["reference"]["edges"], "reason": "x"}, SCHEMA)


def test_schema_rejects_extras():
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({"nodes": [], "edges": [], "reason": "", "x": 1}, SCHEMA)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({"nodes": [], "edges": []}, SCHEMA)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({"nodes": [{"config": "d2", "term": "3F", "count": 1}], "edges": [], "reason": ""}, SCHEMA)
