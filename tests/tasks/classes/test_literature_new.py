"""Tests for the pilot-only ``literature_new`` task class. Failures assert counts and ids only."""
from __future__ import annotations

import csv
import json

import numpy as np
import pytest

from tsbench.tasks import load
from tsbench.tasks.classes import literature_all as L
from tsbench.tasks.classes import literature_new as N

EXCLUDED = {"Ca3Ga2Sn3O12:Fe3+ (Fe3+ on octahedral Ga site)", "ZnS:Mn nanophosphor (zinc blende)"}


@pytest.fixture(scope="module")
def built():
    return N.make_literature_new()


def _rows():
    with N.DATA.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def test_table_layout_extends_the_first_table_and_has_eight_systems():
    with L.DATA.open(newline="", encoding="utf-8") as fh:
        first = next(csv.reader(fh))
    rows = _rows()
    assert list(rows[0])[:len(first)] == first
    assert len(rows) == 8 and not any(r["system"].startswith("[V(ox)3]") for r in rows)
    assert all(r["source"] and ("doi:" in r["source"] or "arXiv:" in r["source"]) for r in rows)


def test_counts_and_exclusions(built):
    pilot, rep = built
    assert (rep["n_table_systems"], rep["n_used"], rep["n_pilot"], len(pilot)) == (8, 6, 6, 6)
    assert {e["system"] for e in rep["excluded"]} == EXCLUDED and rep["n_ambiguous"] == 0
    assert all("fit at bound" in e["reason"] for e in rep["excluded"])
    assert not ({r["system"] for r in pilot} & EXCLUDED)


def test_deterministic(built):
    again, _ = N.make_literature_new()
    assert json.dumps(again, sort_keys=True) == json.dumps(built[0], sort_keys=True)


def test_the_default_table_is_the_first_table():
    # the default table is literature-spectra.csv with 33 systems; ZnS:Mn is not among them
    assert len(L.read_table()) == 33 and len(L.read_table(N.DATA)) == 8
    pilot, conf, _ = L.make_literature_all(np.random.default_rng(7), set())
    assert len(pilot) + len(conf) == 30 and {r["class"] for r in pilot + conf} == {"literature_all"}


def test_records_pass_the_oracle_check_and_carry_sources(built):
    pilot, _ = built
    for r in pilot:
        assert r["class"] == "literature_new" and r["oracle"] == "forward_model_lsq" and r["answer_schema"] == "fit"
        p = r["params"]
        assert "doi:" in p["source"] or "arXiv:" in p["source"], r["system"]
        assert p["location"] and p["quote"] and p["assignment_confidence"] in {"high", "medium"}
        # the reference reproduces the printed bands with the stated rmse (forward model, same code path as the fit)
        d = p["model_d"]
        parsed = [L.parse_label(x) for x in p["labels"]]
        c = r["reference"]["C"] if r["reference"]["C"] is not None else L.CB_FIXED * r["reference"]["B"]
        pred = L.predicted(d, parsed, p["ground_term"], r["reference"]["Dq"], r["reference"]["B"], c,
                           np.array(r["bands_cm1"]))
        rmse = float(np.sqrt(np.mean((pred - np.array(r["bands_cm1"])) ** 2)))
        assert abs(rmse - p["rmse_cm1"]) < 0.5, r["system"]
        assert rmse <= L.MISMATCH_REL * float(np.mean(r["bands_cm1"])), r["system"]
        assert not L.at_bound({"Dq": r["reference"]["Dq"], "B": r["reference"]["B"], "C": c,
                               "params_fitted": p["params_fitted"]}), r["system"]


def test_tetrahedral_handling_is_declared_for_zns_only():
    assert "ZnS:Mn nanophosphor (zinc blende)" in L.TETRAHEDRAL_SYSTEMS
    names = {r["system"] for r in _rows()}
    assert (L.TETRAHEDRAL_SYSTEMS & names) == {"ZnS:Mn nanophosphor (zinc blende)"}


def test_generated_file_has_the_class_last_pilot_only_and_unique_ids():
    pilot, conf = load("pilot"), load("confirmatory")
    new = [t for t in pilot if t["class"] == "literature_new"]
    assert len(new) == 6 and not [t for t in conf if t["class"] == "literature_new"]
    assert [t["id"] for t in new] == [f"P-literature_new-{i:02d}" for i in range(1, 7)]
    assert pilot[-6:] == new                                       # appended at the end of the pilot sequence
    ids = [t["id"] for t in pilot + conf]
    assert len(ids) == len(set(ids))
    old = {t["system"] for t in pilot + conf if t["class"] != "literature_new" and t["system"]}
    assert not ({t["system"] for t in new} & old)                  # no new system is an old one


def test_rubric_lists_the_systems_and_the_exclusions():
    text = (N.DATA.parents[1] / "tasks" / "rubric.md").read_text(encoding="utf-8")
    assert "## literature_new" in text and "Pilot-only class (no confirmatory records)" in text
    assert all(n in text for n in EXCLUDED) and "fit at bound" in text
    assert all(r["system"] in text for r in _rows())
