"""Tests for the ``literature_all`` task class. Failures assert counts and hashes only, never task contents."""
from __future__ import annotations

import hashlib
import json
import re

import numpy as np
import pytest

from tsbench.tasks.classes import literature_all as L

KEYS = {"answer_schema", "bands_cm1", "class", "d_count", "expect_out_of_scope", "geometry", "oracle", "params",
        "prompt", "reference", "reference_curve", "required", "subtype", "system", "tolerance"}


def _digest(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


@pytest.fixture(scope="module")
def built():
    return L.make_literature_all(np.random.default_rng(7), set())


# ----------------------------------------------------------------------------- label mapping

def test_parse_label():
    assert L.parse_label("13T2") == ("3_T_2", 1)
    assert L.parse_label("24T1") == ("4_T_1", 2)
    assert L.parse_label("11E") == ("1_E", 1)
    assert L.parse_label("12E") == ("2_E", 1)
    assert L.parse_label("14A2") == ("4_A_2", 1)
    assert L.parse_label("3A1") == ("3_A_1", None)
    assert L.parse_label("3E") == ("3_E", None)
    with pytest.raises(ValueError):
        L.parse_label("T2")


@pytest.mark.parametrize("d", range(2, 9))
def test_every_table_label_resolves_in_the_solver(d):
    rows = [r for r in L.read_table() if r["d"] == d]
    assert len(rows) > 0
    lv = L._levels(d, 1000.0, 800.0, 3500.0)
    unresolved = 0
    for r in rows:
        for lab in r["labels"]:
            key, ordinal = L.parse_label(lab)
            if key not in lv or (ordinal or 1) > len(lv[key]):
                unresolved += 1
    assert unresolved == 0


def test_mapping_anchor_energies():
    # d8: 3A2 -> first 3T2 is exactly 10 Dq; d3: 4A2 -> first 4T2 likewise; d5 ground is the sextet
    for d, label, gk in ((8, "13T2", "3_A_2"), (3, "14T2", "4_A_2")):
        parsed = [L.parse_label(label)]
        e = L.predicted(d, parsed, gk, 1000.0, 800.0, 3500.0)
        assert abs(e[0] - 10000.0) < 1.0
    assert L.ground_key(5, "high") == "6_A_1"
    assert L.ground_key(6, "low") == "1_A_1"
    assert L.ground_key(4, "low") == "3_T_1"
    assert L.ground_key(7, "high") == "4_T_1"
    assert L.ground_key(2, "high") == "3_T_1"
    # the second 4T1 lies above the first
    e = L.predicted(3, [L.parse_label("14T1"), L.parse_label("24T1")], "4_A_2", 1700.0, 700.0, 3200.0)
    assert e[0] < e[1]


def test_regimes():
    by_name = {r["system"]: r for r in L.read_table()}
    assert L.regime_of(6, by_name["[Co(H2O)6]3+"]["labels"]) == "low"
    assert L.regime_of(4, by_name["[Mn(CN)6]3−"]["labels"]) == "low"
    assert L.regime_of(5, by_name["MnF2"]["labels"]) == "high"
    assert L.regime_of(8, by_name["MgO:Ni2+"]["labels"]) == "high"


def test_table_has_33_distinct_systems():
    rows = L.read_table()
    assert len(rows) == 33
    assert len({r["system"] for r in rows}) == 33


# ----------------------------------------------------------------------------- closed loop

def _synth(d, labels, dq, b, c, regime):
    gk = L.ground_key(d, regime)
    assert L.lowest_term(d, dq, b, c) == gk
    parsed = [L.parse_label(lab) for lab in labels]
    return [float(x) for x in L.predicted(d, parsed, gk, dq, b, c)]


CLOSED_LOOP = (
    (4, "low", ["13T2", "23T1", "11A1", "11T2"], (3300.0, 600.0, 2700.0)),
    (5, "high", ["14T1", "14T2", "14E", "24T2"], (900.0, 750.0, 3300.0)),
    (6, "low", ["11T1", "11T2", "13T1", "13T2"], (2300.0, 650.0, 2900.0)),
)


@pytest.mark.parametrize("d,regime,labels,truth", CLOSED_LOOP, ids=[f"d{c[0]}" for c in CLOSED_LOOP])
def test_fit_reproduces_synthetic_bands(d, regime, labels, truth):
    energies = _synth(d, labels, *truth, regime)
    fit = L.fit_labelled(d, labels, energies, regime)
    assert fit["valid"]
    assert fit["params_fitted"] == ["Dq", "B", "C"]
    assert fit["rmse"] < 1.0
    errs = [abs(fit[k] - t) / t for k, t in zip(("Dq", "B", "C"), truth, strict=False)]
    assert max(errs) < 0.01
    assert fit["ambiguous"] is False


def test_c_is_fixed_when_bands_do_not_constrain_it():
    # quartet-only d3 bands do not depend on C: C/B is fixed at 4.5 and the record says so
    labels = ["14T2", "14T1", "24T1"]
    energies = _synth(3, labels, 1700.0, 700.0, 3200.0, "high")
    fit = L.fit_labelled(3, labels, energies, "high")
    assert fit["params_fitted"] == ["Dq", "B"] and fit["cb_fixed"] == 4.5
    assert abs(fit["Dq"] - 1700.0) < 1.0 and abs(fit["B"] - 700.0) < 1.0
    assert abs(fit["C"] / fit["B"] - 4.5) < 1e-9


# ----------------------------------------------------------------------------- records and split

def test_counts_and_report_are_consistent(built):
    pilot, conf, report = built
    assert report["n_table_systems"] == 33
    assert report["n_used"] + report["n_excluded"] + report["n_ambiguous"] == 33
    assert report["n_used"] == len(pilot) + len(conf)
    assert sum(v["used"] + v["excluded"] + v["ambiguous"] for v in report["per_d"].values()) == 33
    assert set(report["per_d"]) == {f"d{d}" for d in range(2, 9)}
    assert report["n_used"] > 0 and len(report["rmse_cm1"]) >= report["n_used"]
    assert 0.2 <= len(pilot) / report["n_used"] <= 0.5


def test_record_schema(built):
    pilot, conf, _ = built
    bad = 0
    for r in pilot + conf:
        fitted_c = "C" in r["required"]
        ok = (set(r) == KEYS and r["class"] == "literature_all" and r["oracle"] == "forward_model_lsq"
              and r["answer_schema"] == "fit" and r["required"] == r["params"]["params_fitted"]
              and r["tolerance"]["Dq"] == 0.05 and r["tolerance"]["B"] == 0.10
              and r["tolerance"]["C"] == (0.15 if fitted_c else None)
              and (r["reference"]["C"] is not None) == fitted_c
              and r["reference"]["Dq"] > 0 and r["reference"]["B"] > 0
              and not r["params"]["ambiguous"] and "paper" in r["params"] and "deviation_from_paper" in r["params"])
        bad += not ok
    assert bad == 0


def test_stratified_by_d_count(built):
    pilot, conf, report = built
    for d in range(2, 9):
        n = report["per_d"][f"d{d}"]["used"]
        n_pilot = sum(r["params"]["model_d"] == d for r in pilot)
        assert n_pilot == int(np.floor(n / 3 + 0.5)), (d, n, n_pilot)


def test_deterministic_under_seed():
    a = L.make_literature_all(np.random.default_rng(11), set())
    b = L.make_literature_all(np.random.default_rng(11), set())
    assert _digest(a) == _digest(b)
    c = L.make_literature_all(np.random.default_rng(12), set())
    assert len(c[0]) == len(a[0]) and len(c[1]) == len(a[1])  # same stratified counts under another seed


def test_forced_pilot_systems_are_never_confirmatory(built):
    _, _, report = built
    used = [n for n in report["rmse_cm1"] if n not in {e["system"] for e in report["excluded"] + report["ambiguous"]}]
    forced = set(used[:: max(1, len(used) // 8)])          # a spread of systems over all d-counts
    assert len(forced) >= 4
    for seed in range(5):
        pilot, conf, _ = L.make_literature_all(np.random.default_rng(seed), forced)
        pilot_names = {r["system"] for r in pilot}
        conf_names = {r["system"] for r in conf}
        assert len(forced - pilot_names) == 0
        assert len(forced & conf_names) == 0
        assert len(pilot_names & conf_names) == 0


def test_no_reference_value_in_any_prompt(built):
    pilot, conf, _ = built
    leaks = 0
    for r in pilot + conf:
        numbers = {int(x.replace(" ", "")) for x in re.findall(r"\d[\d ]*", r["prompt"])
                   if len(x.replace(" ", "")) >= 3}
        refs = {round(v) for v in r["reference"].values() if v is not None}
        leaks += len(numbers & refs)
        for tool in ("tanabesugano", "tanabe", "compute_point", "fit_spectrum", "least_squares", "mcp"):
            leaks += tool in r["prompt"].lower()
        leaks += "rmse" in r["prompt"].lower()
    assert leaks == 0


def test_prompt_states_c_assumption_only_when_c_is_fixed(built):
    pilot, conf, _ = built
    bad = 0
    for r in pilot + conf:
        fixed = "C" not in r["required"]
        bad += ("C/B = 4.5" in r["prompt"]) != fixed
        bad += not r["prompt"].startswith("The ")
        bad += "Determine" not in r["prompt"]
    assert bad == 0


def test_fit_all_keeps_one_result_per_table(monkeypatch, tmp_path):
    """literature_all and literature_new fit different tables in one process: neither may evict the other."""
    reads = []

    def fake_read(path):
        reads.append(path)
        return [{"system": "x", "d": 3, "labels": ["a"], "bands": [1.0], "paper": {}}]

    monkeypatch.setattr(L, "read_table", fake_read)
    monkeypatch.setattr(L, "regime_of", lambda d, labels: "high")
    monkeypatch.setattr(L, "fit_labelled", lambda d, labels, bands, regime: {"valid": False})
    L._fit_all.cache_clear()
    try:
        first, second = tmp_path / "one.csv", tmp_path / "two.csv"
        for path in (first, second, first, second, first):
            L._fit_all(path)
        assert reads == [first, second]
    finally:
        L._fit_all.cache_clear()
