"""The preregistered tests of a confirmatory run set (src/tsbench/report/prereg.py): the rows of hypotheses.json, as
`tsbench stats hypotheses` writes it, put into the tables of the report."""
from __future__ import annotations

import json

import pytest

from tsbench.report import prereg
from tsbench.score.run_sets import RunSet

M = ("claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5")
HYP = {
    "k_layers": {"primary": 3, "h1": 3, "h4": 0},
    "primary": [
        {"name": f"H2_{M[0]}", "n": 55, "p": 0.9354779797316861, "mean_diff": -0.012121212121212114,
         "ci": [-0.10303030303030304, 0.07878787878787878], "p_holm": 0.9354779797316861, "family": "primary"},
        {"name": f"H2_{M[1]}", "n": 55, "p": 4.578375246917267e-06, "mean_diff": 0.2484848484848485,
         "ci": [0.1636363636363636, 0.3393939393939394], "p_holm": 1.8313500987669067e-05, "family": "primary"},
        {"name": f"H2_{M[2]}", "n": 55, "p": 0.008193125393090878, "mean_diff": 0.09090909090909091,
         "ci": [0.030303030303030304, 0.16363636363636364], "p_holm": 0.024579376179272635, "family": "primary"},
        {"name": "H3", "n": 55, "p": 0.10135092286703201, "mean_diff": -0.10303030303636362,
         "ci": [-0.2060606061272727, 3.68181846626665e-11], "p_holm": 0.20270184573406402, "family": "primary"},
    ],
    "secondary": [
        {"name": f"H2_{M[0]}_mcnemar", "n": 55, "p": 0.3876953125, "b": 8, "c": 4, "family": "secondary"},
        {"name": f"H1_{M[0]}", "n": 55, "p": 1.5519562309209897e-10, "mean_diff": 0.6848484848484849,
         "ci": [0.5818181818181818, 0.781818181818182], "family": "secondary"},
        {"name": f"H1_{M[2]}_mcnemar", "n": 55, "p": 1.9073486328125e-06, "b": 0, "c": 20, "family": "secondary"},
        {"name": f"H4_{M[0]}", "n": 55, "p": 0.5, "mean_diff": 0.1, "ci": [0.0, 0.2], "family": "secondary"},
    ],
    "efficiency": [],
}


def _set(tmp_path, name="plan-1", hyp=HYP) -> RunSet:
    d = tmp_path / name
    d.mkdir(parents=True)
    if hyp is not None:
        (d / "hypotheses.json").write_text(json.dumps(hyp), encoding="utf-8")
    return RunSet(name, name, d)


@pytest.mark.parametrize(("p", "text"), [
    (None, "–"), (0.9354779797316861, "0.935"), (0.024579376179272635, "0.025"), (0.20270184573406402, "0.203"),
    (0.001, "0.001"), (1.8313500987669067e-05, "1.8 × 10⁻⁵"), (1.5519562309209897e-10, "1.6 × 10⁻¹⁰"),
    (0.0009996, "1.0 × 10⁻³"),
])
def test_a_p_value_keeps_its_size_below_one_in_a_thousand(p, text):
    assert prereg.p_text(p) == text


def test_the_primary_family_has_one_row_per_test_in_the_order_of_the_file(tmp_path):
    (block,) = prereg.hypotheses([_set(tmp_path)])
    assert block["set"] == "plan-1" and block["k_layers"] == {"primary": 3, "h1": 3, "h4": 0}
    rows = block["primary"]
    assert [r["test"] for r in rows] == ["H2", "H2", "H2", "H3"]
    assert [r["model"] for r in rows[:3]] == list(M)
    haiku, sonnet, opus, h3 = rows
    assert (haiku["n"], haiku["diff"], haiku["ci"], haiku["p"], haiku["p_holm"]) == \
        (55, "−1.2 pp", "−10.3 to +7.9 pp", "0.935", "0.935")
    assert sonnet["diff"] == "+24.8 pp" and sonnet["p_holm"] == "1.8 × 10⁻⁵" and sonnet["p"] == "4.6 × 10⁻⁶"
    assert opus["p_holm"] == "0.025" and opus["comparison"] == "C − B"
    assert h3["model"] == "" and h3["p_holm"] == "0.203" and h3["ci"] == "−20.6 to 0.0 pp"
    assert h3["comparison"] == f"({M[2]} − {M[0]}) under B minus under C"


def test_the_secondary_tests_are_the_h1_rows_and_the_mcnemar_rows(tmp_path):
    (block,) = prereg.hypotheses([_set(tmp_path)])
    (h1,) = block["secondary"]
    assert (h1["test"], h1["model"], h1["comparison"], h1["diff"], h1["p"]) == \
        ("H1", M[0], "C − A", "+68.5 pp", "1.6 × 10⁻¹⁰")
    assert [(r["test"], r["model"], r["base"], r["only_base"], r["only_c"], r["p"]) for r in block["mcnemar"]] == \
        [("H2", M[0], "B", 8, 4, "0.388"), ("H1", M[2], "A", 0, 20, "1.9 × 10⁻⁶")]
    assert block["other"] == 1  # the H4 row is not shown, but counted


def test_a_missing_cell_of_the_primary_family_is_marked(tmp_path):
    hyp = {"primary": [{"name": f"H2_{M[0]}", "n": 0, "p": 1.0, "missing": True, "p_holm": 1.0}], "secondary": []}
    (block,) = prereg.hypotheses([_set(tmp_path, hyp=hyp)])
    (row,) = block["primary"]
    assert row["missing"] and row["diff"] == "–" and row["ci"] == "–" and row["n"] == 0


def test_run_sets_without_the_file_or_with_an_unreadable_one_give_no_block(tmp_path):
    bad = _set(tmp_path, "bad", hyp=None)
    (bad.path / "hypotheses.json").write_text("{not json", encoding="utf-8")
    assert prereg.hypotheses([_set(tmp_path, "none", hyp=None), bad]) == []
    assert prereg.hypotheses([tmp_path / "none"]) == []


def test_every_run_set_with_the_file_gives_its_own_block(tmp_path):
    got = prereg.hypotheses([_set(tmp_path, "a"), _set(tmp_path, "b", hyp=None), _set(tmp_path, "c")])
    assert [b["set"] for b in got] == ["a", "c"]


def _eff(metric, model, base, ratio, ci=(0.5, 2.0), correct=False, n=55):
    tail = "_correct" if correct else ""
    return {"name": f"EFF_{metric}_Cvs{base}_{model}{tail}", "metric": metric, "model": model, "base": base,
            "other": "C", "correct_only": correct, "n": n, "median_base": 100.0, "median_other": 100.0 * ratio,
            "median_ratio": ratio, "ratio_ci": list(ci), "p": 0.01, "family": "descriptive"}


def test_the_efficiency_rows_hold_a_ratio_per_comparison_and_model_in_the_order_of_the_file(tmp_path):
    rows = [_eff("total_tokens", M[0], "A", 2.9213715, (2.2615268, 3.8953586)),
            _eff("total_tokens", M[0], "B", 0.2407714, (0.2071142, 0.2930830)),
            _eff("total_tokens", M[0], "A", 3.0, correct=True, n=20),
            _eff("cost_usd", M[1], "B", 0.5)]
    (block,) = prereg.hypotheses([_set(tmp_path, hyp={**HYP, "efficiency": rows})])
    first, second = block["efficiency"]
    assert (first["metric"], first["model"]) == ("Total tokens", M[0])
    assert first["ratios"] == {"A": "2.92 (2.26 to 3.90)", "B": "0.24 (0.21 to 0.29)",
                               "A_correct": "3.00 (0.50 to 2.00)"}
    assert first["tasks"] == {"A": 55, "B": 55, "A_correct": 20}
    assert (second["metric"], second["ratios"]) == ("Cost", {"B": "0.50 (0.50 to 2.00)"})


def test_a_file_without_efficiency_rows_gives_an_empty_table(tmp_path):
    hyp = {k: v for k, v in HYP.items() if k != "efficiency"}
    assert prereg.hypotheses([_set(tmp_path, hyp=hyp)])[0]["efficiency"] == []


def test_an_efficiency_row_without_an_interval_shows_the_ratio_alone(tmp_path):
    row = {**_eff("duration_s", M[2], "A", 1.5), "ratio_ci": None}
    (block,) = prereg.hypotheses([_set(tmp_path, hyp={**HYP, "efficiency": [row]})])
    assert (block["efficiency"][0]["metric"], block["efficiency"][0]["ratios"]) == ("Duration", {"A": "1.50"})


SEC = {**HYP, "family": "secondary",
       "primary": [{**r, "family": "secondary_h2"} for r in HYP["primary"] if r["name"] != "H3"]}


def test_a_file_of_the_secondary_family_says_so(tmp_path):
    (block,) = prereg.hypotheses([_set(tmp_path, hyp=SEC)])
    assert block["family"] == "secondary" and [r["test"] for r in block["primary"]] == ["H2"] * 3
    (block,) = prereg.hypotheses([_set(tmp_path, "plan-1b")])
    assert block["family"] == "primary"


def test_a_family_file_in_the_folder_above_the_run_sets_gives_one_block_after_theirs(tmp_path):
    """Plans 2a-2c are one family: its hypotheses.json lies in the folder that holds the three run sets."""
    fam = tmp_path / "secondary"
    sets = [_set(fam, name, hyp=None) for name in ("plan-2a", "plan-2b", "plan-2c")]
    (fam / "hypotheses.json").write_text(json.dumps(SEC), encoding="utf-8")
    blocks = prereg.hypotheses([_set(tmp_path, "plan-1"), *sets])
    assert [(b["set"], b["family"]) for b in blocks] == [("plan-1", "primary"), ("secondary", "secondary")]


def test_the_contents_name_the_family_of_each_block(tmp_path):
    from tsbench.report import full
    blocks = prereg.hypotheses([_set(tmp_path, "plan-1"), _set(tmp_path, "plan-2", hyp=SEC)])
    titles = [t for _, _, t in full._prereg_toc(blocks) if "family" in t]
    assert titles == ["Primary family", "Secondary family · plan-2"]
