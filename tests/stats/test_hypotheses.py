"""Tests for tsbench.stats.hypotheses (no network, no LLM)."""
import json
import math

import numpy as np
import pytest
from scipy import stats

from tsbench.stats.analysis import paired_rates
from tsbench.stats.hypotheses import (
    _paired_row,
    clopper_pearson,
    cohen_kappa,
    cost_per_correct,
    difference_in_differences,
    load_rates,
    main,
    median_abs_error_ci,
    paired,
    primary,
    rank_biserial,
    secondary,
    wilcoxon_zero,
)

H, S, OPUS = "claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5"


def synth(n=20, seed=0, models=(H, S, OPUS), conds="ABC", efforts=("medium",), c_boost=0.4):
    rng = np.random.default_rng(seed)
    base = rng.uniform(0.2, 0.5, n)
    table = {}
    for m_i, m in enumerate(models):
        for c in conds:
            for e in efforts:
                bump = {"A": 0.0, "B": 0.05 * m_i, "C": c_boost}[c]
                r = np.clip(np.round((base + bump + 0.02 * m_i) * 5) / 5, 0, 1)
                table[(m, c, e)] = {f"t{i:02d}": float(r[i]) for i in range(n)}
    return table


def test_rank_biserial_hand_example():
    # d = [1, 2, -3, 4, 0]: zero dropped, ranks 1..4, W+ = 7, W- = 3 -> r = 0.4
    assert rank_biserial(np.zeros(5), np.array([1, 2, -3, 4, 0])) == pytest.approx(0.4)
    # sign convention: swapping the arguments flips the sign
    assert rank_biserial(np.array([1, 2, -3, 4, 0]), np.zeros(5)) == pytest.approx(-0.4)


def test_rank_biserial_ties_and_extremes():
    x = np.array([0.2, 0.5, 1.0])
    assert rank_biserial(x, x) == 0.0
    assert rank_biserial(x, x + 0.1) == 1.0
    assert rank_biserial(x + 0.1, x) == -1.0
    # tied |d| get average ranks: d = [1, -1, 2] -> ranks 1.5,1.5,3 -> (4.5-1.5)/6
    assert rank_biserial(np.zeros(3), np.array([1.0, -1.0, 2.0])) == pytest.approx(0.5)


def test_difference_in_differences_arithmetic():
    t = {("m", "x", "hi"): {"a": 0.8, "b": 1.0}, ("m", "x", "lo"): {"a": 0.2, "b": 0.4},
         ("m", "y", "hi"): {"a": 0.5, "b": 0.5, "c": 0.0}, ("m", "y", "lo"): {"a": 0.4, "b": 0.5}}
    ids, d = difference_in_differences(t, ("m", "x", "hi"), ("m", "x", "lo"), ("m", "y", "hi"), ("m", "y", "lo"))
    assert ids == ["a", "b"]  # common tasks only
    # a: (0.8-0.2)-(0.5-0.4)=0.5 ; b: (1.0-0.4)-(0.5-0.5)=0.6
    assert d == pytest.approx([0.5, 0.6])


def test_paired_row_builds_one_comparison():
    t = {("m", "A", "e"): {"a": 1.0, "b": 0.5}, ("m", "C", "e"): {"a": 0.2, "b": 0.5}}
    row = _paired_row(t, "H1_m", ("m", "A", "e"), ("m", "C", "e"))
    assert row is not None and row["name"] == "H1_m" and row["n"] == 2
    assert row["mean_diff"] == pytest.approx(-0.4)   # second minus first: (0.2-1.0, 0.5-0.5) -> mean -0.4
    assert _paired_row(t, "H1_m", ("m", "A", "e"), ("zz", "C", "e")) is None   # a missing cell gives no row


def test_paired_aligns_sorted_common_ids():
    t = {("m", "A", "e"): {"z": 0.0, "a": 1.0, "q": 0.5}, ("m", "C", "e"): {"a": 0.2, "z": 0.4}}
    ids, a, b = paired(t, ("m", "A", "e"), ("m", "C", "e"))
    assert ids == ["a", "z"] and a.tolist() == [1.0, 0.0] and b.tolist() == [0.2, 0.4]


def test_wilcoxon_zero():
    assert wilcoxon_zero(np.zeros(6)) == 1.0
    assert wilcoxon_zero([]) == 1.0
    d = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, -0.05, 0.0])
    assert wilcoxon_zero(d) == pytest.approx(stats.wilcoxon(d, zero_method="pratt").pvalue)
    # mirrors paired_rates on (a, b) with d = b - a
    a = np.array([0.0, 0.2, 0.4, 0.6, 0.8, 1.0, 0.1])
    b = a + np.array([.3, .1, .2, -.1, .4, 0, .2])
    assert wilcoxon_zero(b - a) == pytest.approx(paired_rates(a, b))


def k3_tables(n_tables=12, n=30, k=3, seed=7):
    """Random count vectors (0..k) over n tasks: [(a, b, a_hi, a_lo, b_hi, b_lo)] as integer counts."""
    rng = np.random.default_rng(seed)
    return [tuple(rng.integers(0, k + 1, n) for _ in range(6)) for _ in range(n_tables)]


def test_k3_rates_are_tested_on_a_grid_like_integer_counts():
    # k = 3: rates are c/3; equal differences differ in the last bit, so the float zero/tie structure is noise
    assert (1.0 - 2 / 3) - (2 / 3 - 1 / 3) != 0.0
    t = {("m", "x", "hi"): {"a": 1.0}, ("m", "x", "lo"): {"a": 2 / 3},
         ("m", "y", "hi"): {"a": 2 / 3}, ("m", "y", "lo"): {"a": 1 / 3}}
    _, d = difference_in_differences(t, ("m", "x", "hi"), ("m", "x", "lo"), ("m", "y", "hi"), ("m", "y", "lo"))
    assert d.tolist() == [0.0]
    for a, b, ah, al, bh, bl in k3_tables():
        d_counts = (ah - al) - (bh - bl)
        cells = {("m", "ah", "e"): ah, ("m", "al", "e"): al, ("m", "bh", "e"): bh, ("m", "bl", "e"): bl}
        t = {key: {f"t{i:02d}": c / 3 for i, c in enumerate(v)} for key, v in cells.items()}
        _, d = difference_in_differences(t, ("m", "ah", "e"), ("m", "al", "e"), ("m", "bh", "e"), ("m", "bl", "e"))
        assert np.array_equal(d, np.round(d_counts / 3, 9))
        if np.any(d_counts):
            assert wilcoxon_zero(d) == pytest.approx(stats.wilcoxon(d_counts, zero_method="pratt").pvalue)
        else:
            assert wilcoxon_zero(d) == 1.0
        diff = b - a
        expect = 0.0
        if np.any(diff):
            nz = diff[diff != 0]
            r = stats.rankdata(np.abs(nz))
            expect = (r[nz > 0].sum() - r[nz < 0].sum()) / r.sum()
        assert rank_biserial(a / 3, b / 3) == pytest.approx(expect)
        if np.any(diff):
            assert wilcoxon_zero(b / 3 - a / 3) == pytest.approx(stats.wilcoxon(diff, zero_method="pratt").pvalue)


def test_primary_family_of_four_and_holm():
    res = primary(synth())
    assert [r["name"] for r in res] == [f"H2_{m}" for m in (H, S, OPUS)] + ["H3"]
    assert all(r["p_holm"] >= r["p"] and r["p_holm"] <= 1 for r in res)
    assert all(r["n"] == 20 and r["family"] == "primary" for r in res)
    r = res[0]
    assert r["ci"][0] <= r["mean_diff"] <= r["ci"][1]


def test_c_much_better_than_b_gives_small_h2():
    res = primary(synth(n=30, c_boost=0.45))
    for r in res[:3]:
        assert r["p"] < 1e-4 and r["mean_diff"] > 0.2 and r["rank_biserial"] > 0.9


def test_h3_sign_gap_shrinks_with_mcp():
    # B: Opus beats Haiku by 0.4; C: no gap -> DiD = +0.4 on every task
    n = 15
    t = {}
    for c, gap in (("B", 0.4), ("C", 0.0)):
        t[(H, c, "medium")] = {f"t{i}": 0.3 + 0.01 * i for i in range(n)}
        t[(OPUS, c, "medium")] = {f"t{i}": 0.3 + 0.01 * i + gap for i in range(n)}
    h3 = [r for r in primary(t, models=(H, OPUS)) if r["name"] == "H3"][0]
    assert h3["mean_diff"] == pytest.approx(0.4) and h3["p"] < 0.01 and h3["rank_biserial"] == 1.0


def test_missing_cells_are_handled():
    t = synth()
    del t[(S, "C", "medium")]
    with pytest.raises(ValueError, match="incomplete"):
        primary(t)
    res = primary(t, allow_incomplete=True)
    # family size stays 4: the missing test enters Holm as p = 1, never shrinks the family
    assert [r["name"] for r in res] == [f"H2_{H}", f"H2_{S}", f"H2_{OPUS}", "H3"]
    assert [r.get("missing", False) for r in res] == [False, True, False, False]
    assert all(r["p_holm"] >= r["p"] for r in res)
    assert all(r.get("missing") for r in primary({}, allow_incomplete=True))
    assert secondary({}) == []
    # H4 cells absent -> no H4 row, no error
    assert not [r for r in secondary(t) if r["name"].startswith("H4")]


def test_secondary_contents():
    t = synth(efforts=("low", "medium", "max"))
    res = secondary(t)
    names = [r["name"] for r in res]
    assert {f"H1_{m}" for m in (H, S, OPUS)} <= set(names)
    assert {f"H4_{H}", f"H4_{OPUS}"} <= set(names) and f"H4_{S}" not in names
    assert f"H2_{OPUS}_mcnemar" in names and f"H1_{H}_mcnemar" in names
    assert all(r["family"] == "secondary" and "p_holm" not in r for r in res)
    mc = [r for r in res if r["name"] == f"H2_{OPUS}_mcnemar"][0]
    assert mc["b"] + mc["c"] > 0 and 0 <= mc["p"] <= 1
    # synth has no effort effect: H4 DiD is zero everywhere -> p = 1
    assert [r for r in res if r["name"] == f"H4_{H}"][0]["p"] == 1.0


def _two_arm_table(model, cells):
    """{(model, cond, effort): {task: rate}} from {(cond, effort): [rate per task]}."""
    return {(model, c, e): {f"t{i:02d}": r for i, r in enumerate(rates)} for (c, e), rates in cells.items()}


def test_h1_compares_c_with_a_so_a_gain_has_a_positive_sign():
    # C beats A by 0.2 on every task: the row is C - A, so mean_diff and rank_biserial are positive
    a = [0.0, 0.2, 0.4, 0.6, 0.1, 0.3, 0.5, 0.7]
    t = _two_arm_table(H, {("A", "medium"): a, ("C", "medium"): [x + 0.2 for x in a]})
    h1 = [r for r in secondary(t, models=(H,), h4_models=()) if r["name"] == f"H1_{H}"][0]
    assert h1["mean_diff"] == pytest.approx(0.2) and h1["rank_biserial"] == 1.0
    assert 0 < h1["ci"][0] <= h1["mean_diff"] <= h1["ci"][1]


def test_h4_is_the_effort_effect_of_c_minus_the_effort_effect_of_a():
    # C gains 0.4 from low to max effort, A gains 0.1: the difference in differences is +0.3 on every task
    base = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.15, 0.25]
    t = _two_arm_table(H, {("C", "low"): base, ("C", "max"): [x + 0.4 for x in base],
                           ("A", "low"): base, ("A", "max"): [x + 0.1 for x in base]})
    h4 = [r for r in secondary(t, models=(), h4_models=(H,)) if r["name"] == f"H4_{H}"][0]
    assert h4["mean_diff"] == pytest.approx(0.3) and h4["rank_biserial"] == 1.0
    # the effort axis runs low -> max (a swapped pair flips the sign), the arms C - A (a swapped arm flips it too)
    assert h4["ci"][0] > 0


def test_clopper_pearson_bounds():
    lo, hi = clopper_pearson(0, 10)
    assert lo == 0.0 and hi == pytest.approx(1 - 0.025 ** (1 / 10))
    lo, hi = clopper_pearson(10, 10)
    assert hi == 1.0 and lo == pytest.approx(0.025 ** (1 / 10))
    # textbook: 5/10 -> (0.1871, 0.8129)
    lo, hi = clopper_pearson(5, 10)
    assert (lo, hi) == pytest.approx((0.1871, 0.8129), abs=1e-4)


def test_cohen_kappa():
    assert cohen_kappa([1, 0, 1, 1, 0], [1, 0, 1, 1, 0]) == 1.0
    # classic 2x2: 20 yes/yes, 5 yes/no, 10 no/yes, 15 no/no -> po=.7, pe=.5, kappa=.4
    r1 = [1] * 20 + [1] * 5 + [0] * 10 + [0] * 15
    r2 = [1] * 20 + [0] * 5 + [1] * 10 + [0] * 15
    assert cohen_kappa(r1, r2) == pytest.approx(0.4)
    assert cohen_kappa([1, 0, 1, 0], [0, 1, 0, 1]) == pytest.approx(-1.0)


def test_median_abs_error_ci():
    v = np.array([-0.5, 0.1, 0.2, -0.3, 0.4, 0.0, 0.25])
    med, lo, hi = median_abs_error_ci(v)
    assert med == pytest.approx(np.median(np.abs(v))) and lo <= med <= hi
    assert median_abs_error_ci(v) == (med, lo, hi)  # seeded
    assert all(math.isnan(x) for x in median_abs_error_ci([]))


def test_cost_per_correct():
    assert cost_per_correct(3.0, 4) == 0.75
    assert cost_per_correct(3.0, 0) == math.inf


def test_load_rates_and_cli(tmp_path):
    t = synth(n=8, efforts=("medium",))
    p = tmp_path / "rates.csv"
    rows = ["model,condition,effort,task_id,rate,k"]
    rows += [f"{m},{c},{e},{i},{r},5" for (m, c, e), cell in t.items() for i, r in cell.items()]
    p.write_text("\n".join(rows) + "\n", encoding="utf-8")
    assert load_rates(p) == t
    out = tmp_path / "o" / "h.json"
    main(["--rates", str(p), "--out", str(out)])
    res = json.loads(out.read_text(encoding="utf-8"))
    assert len(res["primary"]) == 4 and res["secondary"]
    assert set(res["environment"]) == {"python", "numpy", "scipy"} and all(res["environment"].values())
    p.write_text("\n".join(rows + [rows[1]]) + "\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_rates(p)


# ------------------------------------------------------------------ staged design: complete k layers only
from tsbench.stats import hypotheses as hy  # noqa: E402


def score_rows(n=12, layers=None, seed=1, models=(H, S, OPUS), efforts=("medium",), wrong_layer=None):
    """Synthetic scores rows: `layers` maps condition -> number of complete k layers; C is right more often.
    `wrong_layer` = (condition, k): every run of that layer is wrong (to see whether it enters the rates)."""
    layers = layers or {"A": 3, "B": 3, "C": 3}
    rng = np.random.default_rng(seed)
    p = {"A": 0.3, "B": 0.45, "C": 0.85}
    rows = []
    for m in models:
        for c, n_k in layers.items():
            for e in efforts:
                for t in range(n):
                    for k in range(1, n_k + 1):
                        ok = bool(rng.random() < p[c]) and (c, k) != wrong_layer
                        rows.append({"model": m, "condition": c, "effort": e, "task_id": f"t{t:02d}", "k": k,
                                     "evaluable": True, "correct": ok})
    return rows


def test_complete_layers_stops_at_the_first_incomplete_layer():
    rows = score_rows(layers={"B": 3, "C": 4})
    cells = [(m, c, "medium") for m in (H, S, OPUS) for c in "BC"]
    assert hy.complete_layers(rows, cells) == 3                      # layer 4 exists for C only
    rows.pop(next(i for i, r in enumerate(rows) if r["condition"] == "B" and r["k"] == 2))
    assert hy.complete_layers(rows, cells) == 1                      # one missing run breaks layer 2
    assert hy.complete_layers(rows, cells, expect_tasks=13) == 0     # a task never run: no complete layer
    assert hy.complete_layers(rows, [(H, "A", "medium")]) == 0       # a cell without runs


def test_not_evaluable_runs_count_as_present_but_not_in_the_rate():
    rows = score_rows(n=3, layers={"C": 2}, models=(H,))
    for r in rows:
        if r["task_id"] == "t00" and r["k"] == 2:
            r["evaluable"], r["correct"] = False, False
    assert hy.complete_layers(rows, [(H, "C", "medium")]) == 2
    first = next(r["correct"] for r in rows if r["task_id"] == "t00" and r["k"] == 1)
    assert hy.rates_upto(rows, [(H, "C", "medium")], 2)[(H, "C", "medium")]["t00"] == float(first)


def test_rates_use_complete_layers_only():
    rows = score_rows(layers={"B": 3, "C": 4}, wrong_layer=("C", 4))
    lay = hy.layered(rows)
    assert lay["layers"] == {"primary": 3, "h1": 0, "h4": 0}
    full = hy.rates_upto(rows, [(OPUS, "C", "medium")], 4)[(OPUS, "C", "medium")]
    used = hy.rates_upto(rows, [(OPUS, "C", "medium")], 3)[(OPUS, "C", "medium")]
    assert any(full[t] < used[t] for t in used)                      # layer 4 (all wrong) would lower the rates
    expect = primary(hy.rates_upto(rows, [(m, c, "medium") for m in (H, S, OPUS) for c in "BC"], 3))
    assert [r["p"] for r in lay["primary"]] == [r["p"] for r in expect]
    assert all(r["k_layers"] == 3 for r in lay["primary"])


def test_families_get_their_own_layers_and_untested_families_give_no_rows():
    rows = score_rows(layers={"B": 3, "C": 3})                       # stage 1 only: B and C, k = 1-3
    lay = hy.layered(rows)
    assert lay["layers"]["primary"] == 3 and len(lay["primary"]) == 4
    names = {r["name"] for r in lay["secondary"]}
    assert not any(n.startswith(("H1_", "H4_")) for n in names)      # no A runs, no effort sweep yet
    assert {f"H2_{m}_mcnemar" for m in (H, S, OPUS)} <= names
    rows += score_rows(layers={"A": 2}, seed=2)                      # stage 2 partly done: A at k = 1-2
    lay = hy.layered(rows)
    assert lay["layers"]["h1"] == 2 and lay["layers"]["primary"] == 3
    assert all(r["k_layers"] == 2 for r in lay["secondary"] if r["name"].startswith("H1_"))


def test_h4_family_uses_the_sweep_cells():
    rows = score_rows(layers={"A": 3, "C": 3}, models=(H, OPUS), efforts=("low", "max"))
    lay = hy.layered(rows)
    assert lay["layers"]["h4"] == 3 and lay["primary"] == []
    assert {r["name"] for r in lay["secondary"]} == {f"H4_{H}", f"H4_{OPUS}"}


def test_cli_with_scores_files(tmp_path):
    rows = score_rows(layers={"A": 3, "B": 3, "C": 3})
    p = tmp_path / "scores.csv"
    lines = ["model,condition,effort,task_id,k_index,correct,evaluable"]
    lines += [f"{r['model']},{r['condition']},{r['effort']},{r['task_id']},{r['k']},{r['correct']},{r['evaluable']}"
              for r in rows]
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    out = tmp_path / "h.json"
    main(["--scores", str(p), "--expect-tasks", "12", "--out", str(out)])
    res = json.loads(out.read_text(encoding="utf-8"))
    assert res["k_layers"] == {"primary": 3, "h1": 3, "h4": 0} and len(res["primary"]) == 4
    assert res["efficiency"] == [] and res["environment"]["scipy"]


def test_k_min_leaves_families_with_too_few_layers_untested():
    rows = score_rows(layers={"B": 3, "C": 3}) + score_rows(layers={"A": 2}, seed=2)
    lay = hy.layered(rows, k_min=3)
    assert lay["layers"] == {"primary": 3, "h1": 0, "h4": 0}       # A has 2 complete layers < k_min
    assert len(lay["primary"]) == 4 and not any(r["name"].startswith("H1_") for r in lay["secondary"])
    assert hy.layered(score_rows(layers={"B": 2, "C": 2}), k_min=3)["primary"] == []


# ------------------------------------------------------------------ pinned values, inputs, CLI and efficiency
import builtins  # noqa: E402
import pathlib  # noqa: E402
import runpy  # noqa: E402
import sys  # noqa: E402
import warnings  # noqa: E402


@pytest.fixture
def open_calls(monkeypatch):
    """Record the keyword arguments of every `open(...)` the hypotheses module makes (it still opens for real)."""
    calls = []

    def spy(*args, **kwargs):
        calls.append(kwargs)
        return builtins.open(*args, **kwargs)

    monkeypatch.setattr(hy, "open", spy, raising=False)
    return calls


def write_csv(path, header, rows):
    path.write_text("\n".join([",".join(header)] + [",".join(str(v) for v in r) for r in rows]) + "\n",
                    encoding="utf-8")
    return path


def test_paired_arrays_are_float_even_for_integer_rates():
    t: dict[tuple[str, str, str], dict[str, float]] = {
        ("m", "A", "e"): {"a": 1, "b": 0}, ("m", "C", "e"): {"a": 1, "b": 1},
        ("m", "x", "e"): {"a": 2, "b": 2}, ("m", "y", "e"): {"a": 1, "b": 0}}
    _, a, b = paired(t, ("m", "A", "e"), ("m", "C", "e"))
    assert a.dtype == np.float64 and b.dtype == np.float64
    _, d = difference_in_differences(t, ("m", "x", "e"), ("m", "y", "e"), ("m", "A", "e"), ("m", "C", "e"))
    assert d.dtype == np.float64 and d.tolist() == [1.0, 3.0]


def test_rank_biserial_and_wilcoxon_zero_read_text_and_bool_inputs_as_numbers():
    assert rank_biserial(["0", "0", "0", "0", "0"], ["1", "2", "-3", "4", "0"]) == pytest.approx(0.4)
    assert rank_biserial([False, True, False], [True, True, True]) == 1.0
    assert wilcoxon_zero(["0.1", "0.2", "0.3", "-0.4", "0.5", "0.6", "0.7", "0.8"]) == pytest.approx(
        stats.wilcoxon([0.1, 0.2, 0.3, -0.4, 0.5, 0.6, 0.7, 0.8], zero_method="pratt").pvalue)
    assert wilcoxon_zero([0.0, False, "0"]) == 1.0


def test_wilcoxon_zero_uses_the_pratt_zero_method():
    rng = np.random.default_rng(5)
    a = np.round(rng.uniform(0, 1, 12), 2)
    b = np.round(np.clip(a + rng.normal(0.1, 0.2, 12), 0, 1), 2)
    b[3] = a[3]                                                  # one zero difference
    d = np.round(b - a, 9)                                       # two-decimal rates: ties are decided on the grid
    pratt = stats.wilcoxon(d, zero_method="pratt").pvalue
    assert wilcoxon_zero(b - a) == pytest.approx(float(pratt))
    assert pratt != pytest.approx(stats.wilcoxon(d, zero_method="wilcox").pvalue, abs=0.05)


def test_cohen_kappa_with_unequal_marginals_and_a_single_shared_label():
    # rater 1 says yes 8 of 10 times, rater 2 says yes 3 of 10 times; both yes on 3 items
    r1 = [1] * 8 + [0] * 2
    r2 = [1] * 3 + [0] * 5 + [0] * 2
    po, pe = 0.5, 0.8 * 0.3 + 0.2 * 0.7
    assert cohen_kappa(r1, r2) == pytest.approx((po - pe) / (1 - pe))
    assert cohen_kappa(["a", "a", "b", "b"], ["a", "b", "b", "b"]) == pytest.approx((0.75 - 0.5 * 0.25 - 0.5 * 0.75) /
                                                                                    (1 - 0.5))
    assert cohen_kappa([1, 1, 1], [1, 1, 1]) == 1.0
    assert cohen_kappa(["x", "x"], ["x", "x"]) == 1.0


def test_median_abs_error_ci_on_a_two_point_sample():
    # |values| = [0, 1]: a resample median is 0, 0.5 or 1 with probabilities 1/4, 1/2, 1/4
    assert median_abs_error_ci([0.0, -1.0]) == (0.5, 0.0, 1.0)
    assert median_abs_error_ci([0.0, -1.0], alpha=0.6) == (0.5, 0.5, 0.5)
    assert median_abs_error_ci([-0.3]) == (0.3, 0.3, 0.3)     # one value is a valid sample
    assert median_abs_error_ci(["0", "-1"]) == (0.5, 0.0, 1.0)


def test_median_abs_error_ci_defaults_seed_and_the_first_value():
    # a sample for which the 5000-draw and the 5001-draw interval differ (the resample medians are discrete)
    v = [0.51, -0.73, 0.54, 0.68, -0.39, 0.45, 0.26, -0.54, 0.43, 0.13]
    assert median_abs_error_ci(v) == median_abs_error_ci(v, n_boot=5000, alpha=0.05, seed=0)
    assert median_abs_error_ci(v) != median_abs_error_ci(v, n_boot=5001)
    assert median_abs_error_ci(v) != median_abs_error_ci(v, alpha=0.5)
    w = [0.06, 0.54, -0.52, 0.84, 0.62, 0.18, -0.18, 0.03, 0.6, 0.97]
    assert median_abs_error_ci(w, n_boot=30) == median_abs_error_ci(w, n_boot=30, seed=0)
    assert median_abs_error_ci(w, n_boot=30) != median_abs_error_ci(w, n_boot=30, seed=1)
    # only the first value is large: without it among the draws the upper bound could not rise above 0
    assert median_abs_error_ci([1.0, 0.0, 0.0])[2] == 1.0


def test_efficiency_defaults_name_the_metrics():
    assert hy.EFFICIENCY_METRICS == ("total_tokens", "output_tokens", "thinking_tokens", "duration_s", "cost_usd")


def ratio(a, b, **kwargs) -> dict:
    summ = hy.ratio_summary(a, b, **kwargs)
    assert summ is not None
    return summ


def test_ratio_summary_two_point_sample_and_filters():
    # log ratios are [0, 1]: resample medians 0, 0.5, 1 with probabilities 1/4, 1/2, 1/4
    summ = ratio([1.0, 1.0], [1.0, math.e])
    assert summ["n"] == 2 and summ["median_base"] == 1.0
    assert summ["median_other"] == pytest.approx((1 + math.e) / 2)
    assert summ["median_ratio"] == pytest.approx(math.exp(0.5))
    assert summ["ratio_ci"] == pytest.approx([1.0, math.e])
    assert summ["p"] == wilcoxon_zero(np.log([1.0, math.e]))
    assert ratio([1.0, 1.0], [1.0, math.e], alpha=0.6)["ratio_ci"] == pytest.approx([math.exp(0.5)] * 2)
    # only pairs with both values above zero are used
    summ = ratio([0.0, 2.0, 4.0, 5.0], [3.0, 1.0, 0.0, 10.0])
    assert summ["n"] == 2 and summ["median_base"] == 3.5 and summ["median_other"] == 5.5
    assert summ["median_ratio"] == pytest.approx(math.exp(np.median(np.log([0.5, 2.0]))))
    assert hy.ratio_summary([0.0, 1.0], [1.0, 0.0]) is None and hy.ratio_summary([], []) is None
    assert set(ratio([1.0], [2.0])) == {"n", "median_base", "median_other", "median_ratio", "ratio_ci", "p"}


def test_ratio_summary_defaults_seed_and_the_first_pair():
    # a sample for which the 5000-draw and the 5001-draw interval differ (the resample medians are discrete)
    a = [1.7, 3.4, 2.9, 4.7, 2.5, 3.1, 3.4, 2.6, 4.8, 1.5]
    b = [1.2, 2.8, 4.4, 4.3, 4.9, 5.3, 1.3, 0.9, 2.1, 2.9]
    assert hy.ratio_summary(a, b) == hy.ratio_summary(a, b, n_boot=5000, alpha=0.05, seed=0)
    assert hy.ratio_summary(a, b) != hy.ratio_summary(a, b, n_boot=5001)
    assert hy.ratio_summary(a, b) != hy.ratio_summary(a, b, alpha=0.5)
    assert hy.ratio_summary(a, b, n_boot=30) == hy.ratio_summary(a, b, n_boot=30, seed=0)
    assert hy.ratio_summary(a, b, n_boot=30) != hy.ratio_summary(a, b, n_boot=30, seed=1)
    # only the first ratio differs from 1: draws that never pick it cannot reach the upper bound e
    assert ratio([1.0, 1.0, 1.0], [math.e, 1.0, 1.0])["ratio_ci"][1] == pytest.approx(math.e)
    assert isinstance(ratio(a, b)["n"], int)


def test_ratio_summary_reads_text_numbers():
    assert ratio(["1", "2", "0"], ["2", "4", "5"]) == ratio([1.0, 2.0, 0.0], [2.0, 4.0, 5.0])
    assert ratio([True, True], [2, 4])["median_base"] == 1.0


EFF_HEADER = ["model", "condition", "effort", "task_id", "rate", "k", "mean_total_tokens", "mean_total_tokens_correct"]
EFF_ROWS = [
    # model, cond, effort, task, rate, k, tokens, tokens (correct runs only)
    (H, "A", "medium", "t1", 1.0, 3, 100, 100), (H, "A", "medium", "t2", 0.5, 3, 200, ""),
    (H, "A", "medium", "t3", 1.0, 3, 400, 400),
    (H, "C", "medium", "t1", 1.0, 3, 50, 60), (H, "C", "medium", "t2", 1.0, 3, 200, 150),
    (H, "C", "medium", "t3", 0.0, 3, 100, ""),
    (H, "B", "medium", "t1", 1.0, 3, 80, ""), (H, "B", "medium", "t2", 1.0, 3, 0, ""),
    (H, "C", "high", "t1", 1.0, 3, 10, 10), (H, "A", "high", "t1", 1.0, 3, 20, 20),
]


def test_load_metric_reads_the_mean_columns_and_skips_empty_cells(tmp_path, open_calls):
    p = write_csv(tmp_path / "rates.csv", EFF_HEADER, EFF_ROWS)
    t = hy.load_metric(p, "total_tokens")
    assert t[(H, "A", "medium")] == {"t1": 100.0, "t2": 200.0, "t3": 400.0}
    assert t[(H, "B", "medium")] == {"t1": 80.0, "t2": 0.0}             # a zero is a value, an empty cell is not
    assert all(isinstance(v, float) for v in t[(H, "A", "medium")].values())
    assert t[(H, "C", "high")] == {"t1": 10.0}
    c = hy.load_metric(p, "total_tokens", correct_only=True)
    assert c[(H, "A", "medium")] == {"t1": 100.0, "t3": 400.0}
    assert c[(H, "C", "medium")] == {"t1": 60.0, "t2": 150.0} and (H, "B", "medium") not in c
    assert hy.load_metric(p, "cost_usd") == {}                           # no such column: nothing, no error
    assert open_calls and all(kw == {"newline": "", "encoding": "utf-8"} for kw in open_calls)


def test_load_metric_default_is_all_runs(tmp_path):
    p = write_csv(tmp_path / "rates.csv", EFF_HEADER, EFF_ROWS)
    assert hy.load_metric(p, "total_tokens") == hy.load_metric(p, "total_tokens", False)
    assert hy.load_metric(p, "total_tokens") != hy.load_metric(p, "total_tokens", True)


def test_load_metric_keeps_text_with_line_breaks_and_non_ascii(tmp_path):
    p = tmp_path / "rates.csv"
    with open(p, "w", newline="", encoding="utf-8") as fh:
        fh.write("model,condition,effort,task_id,mean_total_tokens\r\n")
        fh.write('mé,A,e,"t\r\n1",5\r\n')
    assert hy.load_metric(p, "total_tokens") == {("mé", "A", "e"): {"t\r\n1": 5.0}}


def test_load_rates_reads_utf8_and_raw_line_breaks(tmp_path, open_calls):
    p = tmp_path / "rates.csv"
    with open(p, "w", newline="", encoding="utf-8") as fh:
        fh.write("model,condition,effort,task_id,rate,k\r\n")
        fh.write('mé,A,e,"t\r\n1",0.5,3\r\n')
    assert load_rates(p) == {("mé", "A", "e"): {"t\r\n1": 0.5}}
    assert open_calls == [{"newline": "", "encoding": "utf-8"}]


def test_load_rates_duplicate_message_names_the_row(tmp_path):
    p = write_csv(tmp_path / "rates.csv", ["model", "condition", "effort", "task_id", "rate", "k"],
                  [("m", "A", "e", "t1", 0.5, 3), ("m", "A", "e", "t1", 0.7, 3)])
    with pytest.raises(ValueError, match=r"duplicate row for \('m', 'A', 'e', 't1'\)"):
        load_rates(p)


def test_efficiency_rows(tmp_path):
    p = write_csv(tmp_path / "rates.csv", EFF_HEADER, EFF_ROWS)
    rows = hy.efficiency(p, models=(H,), metrics=("total_tokens",))
    assert [r["name"] for r in rows] == [f"EFF_total_tokens_CvsA_{H}", f"EFF_total_tokens_CvsB_{H}",
                                         f"EFF_total_tokens_CvsA_{H}_correct"]
    a_all, b_all, a_ok = rows
    assert (a_all["metric"], a_all["model"], a_all["base"], a_all["other"]) == ("total_tokens", H, "A", "C")
    assert a_all["correct_only"] is False and a_ok["correct_only"] is True
    assert all(r["family"] == "descriptive" for r in rows)
    # C vs A over all runs: ratios 0.5, 1, 0.25
    assert (a_all["n"], a_all["median_base"], a_all["median_other"]) == (3, 200.0, 100.0)
    assert a_all["median_ratio"] == pytest.approx(0.5)
    assert a_all["p"] == wilcoxon_zero(np.log([0.5, 1.0, 0.25]))
    lo, hi = a_all["ratio_ci"]
    assert 0.25 <= lo <= 0.5 <= hi <= 1.0
    # C vs B: only t1 counts, t2 has a zero in B
    assert (b_all["n"], b_all["median_ratio"]) == (1, pytest.approx(50 / 80))
    # correct runs only: A and C share only t1 (100 vs 60)
    assert (a_ok["n"], a_ok["median_base"], a_ok["median_other"]) == (1, 100.0, 60.0)
    assert a_ok["median_ratio"] == pytest.approx(0.6) and a_ok["ratio_ci"] == pytest.approx([0.6, 0.6])
    assert hy.efficiency(p, models=(H,), metrics=("total_tokens",), effort="high")[0]["median_ratio"] == 0.5


def test_efficiency_default_effort_models_and_metrics(tmp_path):
    p = write_csv(tmp_path / "rates.csv", EFF_HEADER, EFF_ROWS)
    rows = hy.efficiency(p)                                  # medium effort, all models, all metrics; only one column
    assert [r["name"] for r in rows] == [f"EFF_total_tokens_CvsA_{H}", f"EFF_total_tokens_CvsB_{H}",
                                         f"EFF_total_tokens_CvsA_{H}_correct"]
    assert hy.efficiency(p, effort="max") == [] and hy.efficiency(p, models=("nobody",)) == []
    assert hy.efficiency(p, models=(H,), pairs=(("A", "B"),), metrics=("total_tokens",))[0]["name"] == (
        f"EFF_total_tokens_BvsA_{H}")


def test_load_score_rows_reads_flags_and_k(tmp_path, open_calls):
    header = ["model", "condition", "effort", "task_id", "k_index", "correct", "evaluable"]
    p1 = write_csv(tmp_path / "s1.csv", header, [
        (H, "A", "medium", "t1", 1, "True", "True"), (H, "A", "medium", "t1", 2, "false", "FALSE"),
        (H, "A", "medium", "t2", 3, "1", "1"), (H, "C", "low", "t2", 4, "0", "0"),
        (H, "C", "low", "t3", 5, "", ""), (H, "C", "low", "t4", 6, "yes", "no")])
    p2 = write_csv(tmp_path / "s2.csv", header, [(S, "B", "max", "t9", 10, "TRUE", "true")])
    rows = hy.load_score_rows([p1, p2])
    assert [r["task_id"] for r in rows] == ["t1", "t1", "t2", "t2", "t3", "t4", "t9"]
    assert [r["k"] for r in rows] == [1, 2, 3, 4, 5, 6, 10] and all(isinstance(r["k"], int) for r in rows)
    assert [r["correct"] for r in rows] == [True, False, True, False, False, False, True]
    assert [r["evaluable"] for r in rows] == [True, False, True, False, False, False, True]
    assert rows[0] == {"model": H, "condition": "A", "effort": "medium", "task_id": "t1", "k": 1, "evaluable": True,
                       "correct": True}
    assert rows[-1]["model"] == S and rows[-1]["condition"] == "B" and rows[-1]["effort"] == "max"
    assert open_calls == [{"newline": "", "encoding": "utf-8"}] * 2


def test_load_score_rows_without_the_optional_columns(tmp_path):
    p = write_csv(tmp_path / "s.csv", ["model", "condition", "effort", "task_id", "k_index"],
                  [(H, "A", "medium", "t1", 1)])
    (r,) = hy.load_score_rows([p])
    # no evaluable column means evaluable; no verdict means wrong
    assert r["evaluable"] is True and r["correct"] is False


def test_load_score_rows_reads_utf8_and_raw_line_breaks(tmp_path):
    p = tmp_path / "s.csv"
    with open(p, "w", newline="", encoding="utf-8") as fh:
        fh.write("model,condition,effort,task_id,k_index,correct\r\n")
        fh.write('mé,A,e,"t\r\n1",1,True\r\n')
    (r,) = hy.load_score_rows([p])
    assert r["model"] == "mé" and r["task_id"] == "t\r\n1"


def test_rates_upto_counts_the_boundary_layer_and_sums_correct_runs():
    cell = (H, "C", "medium")

    def run(t, k, ok, ev=True):
        return {"model": H, "condition": "C", "effort": "medium", "task_id": t, "k": k, "evaluable": ev, "correct": ok}

    rows = [run("t", 1, True), run("t", 2, True), run("t", 3, False), run("t", 4, True), run("u", 1, False),
            run("u", 2, False, ev=False)]
    assert hy.rates_upto(rows, [cell], 1) == {cell: {"t": 1.0, "u": 0.0}}
    assert hy.rates_upto(rows, [cell], 2) == {cell: {"t": 1.0, "u": 0.0}}
    assert hy.rates_upto(rows, [cell], 3)[cell]["t"] == pytest.approx(2 / 3)
    assert hy.rates_upto(rows, [cell], 4)[cell]["t"] == pytest.approx(3 / 4)
    assert hy.rates_upto(rows, [cell], 0) == {}
    assert hy.rates_upto(rows, [(S, "C", "medium")], 4) == {}


def test_primary_missing_rows_have_n_zero_and_p_one():
    t = synth()
    del t[(S, "C", "medium")]
    missing = [r for r in primary(t, allow_incomplete=True) if r.get("missing")]
    assert [r["name"] for r in missing] == [f"H2_{S}"]
    assert missing[0]["n"] == 0 and missing[0]["p"] == 1.0 and missing[0]["family"] == "primary"
    assert set(missing[0]) == {"name", "n", "p", "missing", "p_holm", "family"}


def test_primary_h3_row_is_the_did_against_zero():
    n = 12
    t = {}
    for c, gap in (("B", 0.3), ("C", 0.1)):
        t[(H, c, "medium")] = {f"t{i}": 0.2 + 0.01 * i for i in range(n)}
        bump = (lambda i: 0.01 if i % 3 == 0 else 0.0) if c == "B" else (lambda i: 0.0)
        t[(OPUS, c, "medium")] = {f"t{i}": 0.2 + 0.01 * i + gap + bump(i) for i in range(n)}
    h3 = [r for r in primary(t, models=(H, OPUS)) if r["name"] == "H3"][0]
    # per task (Opus - Haiku)_B - (Opus - Haiku)_C = 0.2, plus 0.01 on every third task
    assert h3["n"] == n and h3["mean_diff"] == pytest.approx(0.2 + 0.01 * 4 / 12)
    assert 0.2 <= h3["ci"][0] <= h3["mean_diff"] <= h3["ci"][1] <= 0.21
    assert h3["rank_biserial"] == pytest.approx(1.0)


def test_secondary_rows_carry_n_and_the_mcnemar_counts():
    t = synth(n=10, efforts=("low", "medium", "max"))
    res = {r["name"]: r for r in secondary(t)}
    assert res[f"H4_{H}"]["n"] == 10 and res[f"H4_{OPUS}"]["n"] == 10
    mc = res[f"H2_{H}_mcnemar"]
    assert set(mc) == {"name", "n", "p", "b", "c", "family"} and mc["n"] == 10
    b, c, p = hy.paired_majority(*paired(t, (H, "B", "medium"), (H, "C", "medium"))[1:])
    assert (mc["b"], mc["c"], mc["p"]) == (b, c, p)
    assert res[f"H1_{S}_mcnemar"]["n"] == 10


# layered(): families get their own layers; every parameter reaches the right family
def test_layered_effort_reaches_every_family():
    rows = score_rows(layers={"A": 2, "B": 2, "C": 2}, efforts=("high",))
    assert hy.layered(rows)["layers"] == {"primary": 0, "h1": 0, "h4": 0}          # nothing at the default effort
    lay = hy.layered(rows, effort="high")
    assert lay["layers"] == {"primary": 2, "h1": 2, "h4": 0} and len(lay["primary"]) == 4
    assert {r["name"] for r in lay["secondary"]} == (
        {f"H2_{m}_mcnemar" for m in (H, S, OPUS)} | {f"H1_{m}_mcnemar" for m in (H, S, OPUS)}
        | {f"H1_{m}" for m in (H, S, OPUS)})


def test_layered_effort_sweep_names_and_per_family_layers():
    rows = (score_rows(layers={"B": 3, "C": 3}) + score_rows(layers={"A": 2}, seed=2)
            + score_rows(layers={"A": 1, "C": 1}, models=(H, OPUS), efforts=("e1", "e2"), seed=3))
    lay = hy.layered(rows, effort_lo="e1", effort_hi="e2")
    assert lay["layers"] == {"primary": 3, "h1": 2, "h4": 1}
    layers_by_name = {r["name"]: r["k_layers"] for r in lay["secondary"]}
    assert layers_by_name[f"H4_{H}"] == 1 and layers_by_name[f"H4_{OPUS}"] == 1
    assert all(v == 3 for k, v in layers_by_name.items() if k.startswith("H2_"))
    assert all(v == 2 for k, v in layers_by_name.items() if k.startswith("H1_"))
    assert {k for k in layers_by_name if k.startswith("H4_")} == {f"H4_{H}", f"H4_{OPUS}"}
    assert layered_h4_means(rows, "e1", "e2") == {r["name"]: r["mean_diff"] for r in lay["secondary"]
                                                  if r["name"].startswith("H4_")}
    assert not [r for r in hy.layered(rows)["secondary"] if r["name"].startswith("H4_")]   # default sweep: low and max


def layered_h4_means(rows, lo, hi):
    cells = [(m, c, e) for m in (H, OPUS) for c in ("A", "C") for e in (lo, hi)]
    tab = hy.rates_upto(rows, cells, hy.complete_layers(rows, cells))
    return {r["name"]: r["mean_diff"] for r in secondary(tab, (), "medium", (H, OPUS), hi, lo)
            if r["name"].startswith("H4_")}


def test_layered_h4_uses_the_high_and_low_effort_cells():
    rows = score_rows(layers={"A": 3, "C": 3}, models=(H, OPUS), efforts=("low", "max"), seed=4)
    lay = hy.layered(rows)
    assert {r["name"]: r["mean_diff"] for r in lay["secondary"]} == layered_h4_means(rows, "low", "max")
    assert any(v != 0 for v in layered_h4_means(rows, "low", "max").values())


def test_layered_expect_tasks_allow_incomplete_and_k_min_reach_the_checks():
    rows = score_rows(layers={"A": 3, "B": 3, "C": 3})
    assert hy.layered(rows, expect_tasks=13)["layers"] == {"primary": 0, "h1": 0, "h4": 0}
    assert hy.layered(rows, expect_tasks=12)["layers"]["primary"] == 3
    assert hy.layered(rows, k_min=4)["layers"] == {"primary": 0, "h1": 0, "h4": 0}
    assert hy.layered(rows)["layers"]["primary"] == 3
    assert len(hy.layered(score_rows(layers={"B": 1, "C": 1}))["primary"]) == 4         # k_min defaults to one layer
    # a cell without one evaluable run is present but empty: the family is incomplete
    for r in rows:
        if (r["model"], r["condition"]) == (S, "C"):
            r["evaluable"] = False
    with pytest.raises(ValueError, match="incomplete"):
        hy.layered(rows)
    lay = hy.layered(rows, allow_incomplete=True)
    assert [r["name"] for r in lay["primary"] if r.get("missing")] == [f"H2_{S}"]


def test_main_rates_mode_passes_effort_and_flags(tmp_path, capsys):
    t = synth(n=8, efforts=("high",))
    header = ["model", "condition", "effort", "task_id", "rate", "k", "mean_total_tokens"]
    rows = [(m, c, e, i, r, 5, 100 + 10 * int(i[1:]) * (2 if c == "C" else 1)) for (m, c, e), cell in t.items()
            for i, r in cell.items()]
    p = write_csv(tmp_path / "rates.csv", header, rows)
    out = tmp_path / "out.json"
    assert main(["--rates", str(p), "--out", str(out)]) == 1                  # default effort: medium has no cells
    assert "primary family incomplete" in capsys.readouterr().err
    assert main(["--rates", str(p), "--effort", "high", "--out", str(out)]) == 0
    res = json.loads(out.read_text(encoding="utf-8"))
    assert len(res["primary"]) == 4 and not any(r.get("missing") for r in res["primary"])
    assert {r["name"] for r in res["efficiency"]} >= {f"EFF_total_tokens_CvsA_{H}", f"EFF_total_tokens_CvsB_{S}"}
    assert all(r["n"] == 8 for r in res["efficiency"])
    assert {r["name"] for r in res["secondary"]} >= {f"H1_{H}", f"H2_{OPUS}_mcnemar"}
    # --allow-incomplete takes no value: the next option still parses
    out.unlink()
    assert main(["--rates", str(p), "--allow-incomplete", "--out", str(out)]) == 1     # medium: every row missing
    assert not out.exists() and "no test ran" in capsys.readouterr().err
    no_sonnet = write_csv(tmp_path / "rates2.csv", header, [r for r in rows if r[0] != S])
    assert main(["--rates", str(no_sonnet), "--effort", "high", "--allow-incomplete", "--out", str(out)]) == 0
    res = json.loads(out.read_text(encoding="utf-8"))
    assert [r["name"] for r in res["primary"] if r.get("missing")] == [f"H2_{S}"]
    printed = capsys.readouterr().out.splitlines()
    assert printed[-len(res["primary"]) - len(res["secondary"]) - len(res["efficiency"]):][0] == str(res["primary"][0])


def test_main_prints_every_row_and_writes_indented_json(tmp_path, capsys):
    t = synth(n=8)
    p = write_csv(tmp_path / "rates.csv", ["model", "condition", "effort", "task_id", "rate", "k"],
                  [(m, c, e, i, r, 5) for (m, c, e), cell in t.items() for i, r in cell.items()])
    out = tmp_path / "deep" / "er" / "h.json"
    assert main(["--rates", str(p), "--out", str(out)]) == 0
    res = json.loads(out.read_text(encoding="utf-8"))
    lines = capsys.readouterr().out.splitlines()
    assert lines == [str(r) for r in res["primary"] + res["secondary"] + res["efficiency"]]
    text = out.read_text(encoding="utf-8")
    assert text.splitlines()[1].startswith('  "') and not text.splitlines()[1].startswith("   ")
    assert main(["--rates", str(p), "--out", str(out)]) == 0                 # the folder exists already: still fine


def test_main_writes_the_json_as_utf8(tmp_path, monkeypatch):
    t = synth(n=8)
    p = write_csv(tmp_path / "rates.csv", ["model", "condition", "effort", "task_id", "rate", "k"],
                  [(m, c, e, i, r, 5) for (m, c, e), cell in t.items() for i, r in cell.items()])
    seen = []
    real = pathlib.Path.write_text

    def spy(self, data, *args, **kwargs):
        seen.append(kwargs)
        return real(self, data, *args, **kwargs)

    monkeypatch.setattr(pathlib.Path, "write_text", spy)
    main(["--rates", str(p), "--out", str(tmp_path / "h.json")])
    assert seen == [{"encoding": "utf-8"}]


def test_main_default_out_is_hypotheses_json_in_the_current_directory(tmp_path, monkeypatch):
    t = synth(n=8)
    p = write_csv(tmp_path / "rates.csv", ["model", "condition", "effort", "task_id", "rate", "k"],
                  [(m, c, e, i, r, 5) for (m, c, e), cell in t.items() for i, r in cell.items()])
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(work)
    assert main(["--rates", str(p)]) == 0
    assert json.loads((work / "hypotheses.json").read_text(encoding="utf-8"))["primary"]


def test_main_needs_rates_or_scores(capsys):
    with pytest.raises(SystemExit) as exc:
        main([])
    assert exc.value.code == 2
    assert capsys.readouterr().err.endswith("error: give --rates and/or --scores\n")


def write_scores_csv(path, rows):
    return write_csv(path, ["model", "condition", "effort", "task_id", "k_index", "correct", "evaluable"],
                     [(r["model"], r["condition"], r["effort"], r["task_id"], r["k"], r["correct"], r["evaluable"])
                      for r in rows])


def test_main_scores_mode_passes_every_option(tmp_path):
    rows = score_rows(layers={"A": 3, "B": 3, "C": 3}, efforts=("high",))
    sp = write_scores_csv(tmp_path / "s.csv", rows)
    out = tmp_path / "h.json"

    def run(*extra):
        main(["--scores", str(sp), "--out", str(out), *extra])
        return json.loads(out.read_text(encoding="utf-8"))

    assert run("--effort", "high")["k_layers"] == {"primary": 3, "h1": 3, "h4": 0}
    assert run("--effort", "high", "--expect-tasks", "12")["k_layers"]["primary"] == 3
    assert run("--effort", "high", "--k-min", "3")["k_layers"]["primary"] == 3
    assert run("--effort", "high")["efficiency"] == []                         # no --rates: no efficiency rows
    # a family left empty (too many expected tasks, too high k-min, no cell of the default effort) is an error
    for extra in (("--effort", "high", "--expect-tasks", "13"), ("--effort", "high", "--k-min", "4"), ()):
        out.unlink(missing_ok=True)
        assert main(["--scores", str(sp), "--out", str(out), *extra]) == 1
        assert not out.exists()


def test_main_scores_mode_default_k_min_is_one_layer(tmp_path):
    sp = write_scores_csv(tmp_path / "s.csv", score_rows(layers={"B": 1, "C": 1}))
    out = tmp_path / "h.json"
    main(["--scores", str(sp), "--out", str(out)])
    assert json.loads(out.read_text(encoding="utf-8"))["k_layers"]["primary"] == 1


def test_main_scores_mode_allow_incomplete_and_efficiency(tmp_path):
    rows = score_rows(layers={"A": 3, "B": 3, "C": 3}, efforts=("high",))
    for r in rows:
        if (r["model"], r["condition"]) == (S, "C"):
            r["evaluable"], r["correct"] = False, False
    sp = write_scores_csv(tmp_path / "s.csv", rows)
    rp = write_csv(tmp_path / "rates.csv", ["model", "condition", "effort", "task_id", "rate", "k", "mean_cost_usd"],
                   [(m, c, "high", f"t{i:02d}", 0.5, 3, 1.0 + i * (0.5 if c == "C" else 1.0))
                    for m in (H, OPUS) for c in "ABC" for i in range(12)])
    out = tmp_path / "h.json"
    with pytest.raises(ValueError, match="incomplete"):
        main(["--scores", str(sp), "--effort", "high", "--out", str(out)])
    main(["--scores", str(sp), "--effort", "high", "--allow-incomplete", "--rates", str(rp), "--out", str(out)])
    res = json.loads(out.read_text(encoding="utf-8"))
    assert [r["name"] for r in res["primary"] if r.get("missing")] == [f"H2_{S}"]
    names = {r["name"] for r in res["efficiency"]}
    assert f"EFF_cost_usd_CvsA_{H}" in names and f"EFF_cost_usd_CvsB_{OPUS}_correct" not in names
    assert not [n for n in names if S in n]                                      # sonnet has no rates rows
    assert all(r["n"] == 12 for r in res["efficiency"])                          # every cost is above zero


def test_running_the_module_as_a_script_exits_with_main_status(tmp_path, monkeypatch):
    t = synth(n=8)
    p = write_csv(tmp_path / "rates.csv", ["model", "condition", "effort", "task_id", "rate", "k"],
                  [(m, c, e, i, r, 5) for (m, c, e), cell in t.items() for i, r in cell.items()])
    out = tmp_path / "h.json"
    monkeypatch.setattr(sys, "argv", ["hypotheses", "--rates", str(p), "--out", str(out)])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)       # runpy: the module is already imported
        with pytest.raises(SystemExit) as exc:
            runpy.run_module("tsbench.stats.hypotheses", run_name="__main__")
    assert exc.value.code == 0 and out.exists()


# ------------------------------------------------------------------ repeats, empty families, --models
def test_load_score_rows_drops_a_repeated_evaluable_cell_and_reports_the_count(tmp_path, capsys):
    header = ["model", "condition", "effort", "task_id", "k_index", "correct", "evaluable"]
    a = write_csv(tmp_path / "a.csv", header,
                  [(H, "C", "medium", "t1", 1, True, True), (H, "C", "medium", "t2", 1, False, True)])
    b = write_csv(tmp_path / "b.csv", header,
                  [(H, "C", "medium", "t1", 1, False, True), (H, "C", "medium", "t3", 1, True, True)])
    rows = hy.load_score_rows([a, b])
    assert [(r["task_id"], r["correct"]) for r in rows] == [("t1", True), ("t2", False), ("t3", True)]   # first wins
    assert "1 repeated" in capsys.readouterr().err
    # a one-run layer stays 0 or 1 per task, never 0.5
    assert hy.rates_upto(rows, [(H, "C", "medium")], 1)[(H, "C", "medium")] == {"t1": 1.0, "t2": 0.0, "t3": 1.0}
    # no repeat: nothing is said
    hy.load_score_rows([a])
    assert capsys.readouterr().err == ""


def test_load_score_rows_keeps_a_rerun_after_a_not_evaluable_run(tmp_path, capsys):
    header = ["model", "condition", "effort", "task_id", "k_index", "correct", "evaluable"]
    a = write_csv(tmp_path / "a.csv", header, [(H, "C", "medium", "t1", 1, False, False)])
    b = write_csv(tmp_path / "b.csv", header, [(H, "C", "medium", "t1", 1, True, True)])
    rows = hy.load_score_rows([a, b])
    assert hy.rates_upto(rows, [(H, "C", "medium")], 1)[(H, "C", "medium")] == {"t1": 1.0}
    assert capsys.readouterr().err == ""


def test_help_names_the_55_task_confirmatory_split(capsys):
    with pytest.raises(SystemExit):
        main(["--help"])
    out = capsys.readouterr().out
    assert "confirmatory: 55" in out
    assert "--expect-tasks 55" in (hy.__doc__ or "")


def test_main_scores_fails_loudly_when_expect_tasks_leaves_no_family(tmp_path, capsys):
    sp = write_scores_csv(tmp_path / "s.csv", score_rows(layers={"A": 3, "B": 3, "C": 3}))
    out = tmp_path / "h.json"
    assert main(["--scores", str(sp), "--expect-tasks", "66", "--out", str(out)]) == 1
    err = capsys.readouterr().err
    assert "no test ran" in err and "--expect-tasks" in err
    assert not out.exists()
    assert main(["--scores", str(sp), "--expect-tasks", "12", "--out", str(out)]) == 0


def test_main_fails_loudly_for_models_without_cells(tmp_path, capsys):
    gw = ("qwen3.5-397b-a17b", "gpt-oss-120b")
    sp = write_scores_csv(tmp_path / "s.csv", score_rows(layers={"A": 3, "B": 3, "C": 3}, models=gw))
    out = tmp_path / "h.json"
    assert main(["--scores", str(sp), "--out", str(out)]) == 1                  # the default Claude ids: no cell
    assert "no test ran" in capsys.readouterr().err and not out.exists()
    assert main(["--scores", str(sp), "--models", ",".join(gw), "--out", str(out)]) == 0
    res = json.loads(out.read_text(encoding="utf-8"))
    assert [r["name"] for r in res["primary"]] == [f"H2_{gw[0]}", f"H2_{gw[1]}", "H3"]
    assert {r["name"] for r in res["secondary"]} >= {f"H1_{gw[0]}", f"H2_{gw[1]}_mcnemar"}
    assert res["k_layers"] == {"primary": 3, "h1": 3, "h4": 0}


def test_main_rates_mode_takes_models_and_fails_loudly_on_an_empty_family(tmp_path, capsys):
    gw = ("qwen3.5-397b-a17b", "gpt-oss-120b")
    t = synth(n=8, models=gw)
    p = write_csv(tmp_path / "rates.csv", ["model", "condition", "effort", "task_id", "rate", "k"],
                  [(m, c, e, i, r, 5) for (m, c, e), cell in t.items() for i, r in cell.items()])
    out = tmp_path / "h.json"
    assert main(["--rates", str(p), "--allow-incomplete", "--out", str(out)]) == 1   # every row would be missing
    assert "no test ran" in capsys.readouterr().err and not out.exists()
    assert main(["--rates", str(p), "--models", ",".join(gw), "--out", str(out)]) == 0
    res = json.loads(out.read_text(encoding="utf-8"))
    assert [r["name"] for r in res["primary"]] == [f"H2_{gw[0]}", f"H2_{gw[1]}", "H3"]
    assert not any(r.get("missing") for r in res["primary"])


def test_main_models_option_rejects_an_empty_list(tmp_path):
    p = write_csv(tmp_path / "rates.csv", ["model", "condition", "effort", "task_id", "rate", "k"], [])
    with pytest.raises(SystemExit) as exc:
        main(["--rates", str(p), "--models", " , "])
    assert exc.value.code == 2


# ------------------------------------------------------------------ a single model: no H3
def test_primary_with_one_model_has_no_h3_and_holm_counts_only_h2():
    gw = "qwen3.5-397b-a17b"
    t = synth(n=30, models=(gw,))
    res = primary(t, models=(gw,))
    assert [r["name"] for r in res] == [f"H2_{gw}"]
    assert res[0]["p_holm"] == res[0]["p"]                                  # family of one: no Holm inflation
    # a repeated id is one model, not two
    assert [r["name"] for r in primary(t, models=(gw, gw))] == [f"H2_{gw}"]
    # two distinct models keep H3
    assert [r["name"] for r in primary(synth(n=30, models=(H, S)), models=(H, S))][-1] == "H3"


def test_main_one_model_runs_without_h3_from_rates_and_scores(tmp_path):
    gw = "qwen3.5-397b-a17b"
    t = synth(n=20, models=(gw,))
    p = write_csv(tmp_path / "rates.csv", ["model", "condition", "effort", "task_id", "rate", "k"],
                  [(m, c, e, i, r, 5) for (m, c, e), cell in t.items() for i, r in cell.items()])
    out = tmp_path / "h.json"
    assert main(["--rates", str(p), "--models", gw, "--out", str(out)]) == 0
    res = json.loads(out.read_text(encoding="utf-8"))
    assert [r["name"] for r in res["primary"]] == [f"H2_{gw}"] and res["primary"][0]["p_holm"] == res["primary"][0]["p"]
    sp = write_scores_csv(tmp_path / "s.csv", score_rows(layers={"A": 3, "B": 3, "C": 3}, models=(gw,)))
    assert main(["--scores", str(sp), "--models", gw, "--out", str(out)]) == 0
    res = json.loads(out.read_text(encoding="utf-8"))
    assert "H3" not in {r["name"] for r in res["primary"] + res["secondary"]}


def test_main_rates_with_default_models_on_other_data_names_models_option(tmp_path, capsys):
    gw = "qwen3.5-397b-a17b"
    t = synth(n=8, models=(gw,))
    p = write_csv(tmp_path / "rates.csv", ["model", "condition", "effort", "task_id", "rate", "k"],
                  [(m, c, e, i, r, 5) for (m, c, e), cell in t.items() for i, r in cell.items()])
    out = tmp_path / "h.json"
    assert main(["--rates", str(p), "--out", str(out)]) == 1                # no traceback
    err = capsys.readouterr().err
    assert "--models" in err and "primary family incomplete" in err and not out.exists()
