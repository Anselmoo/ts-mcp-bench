"""Tests for tsbench.stats.power (simulation-based power; small n_sim, seeded)."""
import csv

from tsbench.stats import power
from tsbench.stats.power import simulate, simulate_difference_in_differences


def test_simulate_did_is_seeded_and_tracks_the_effect():
    big = simulate_difference_in_differences(55, 3, 0.86, 0.96, 0.38, 0.82, n_sim=60)
    assert big == simulate_difference_in_differences(55, 3, 0.86, 0.96, 0.38, 0.82, n_sim=60)   # same seed, same result
    assert big > 0.9
    assert simulate_difference_in_differences(55, 3, 0.8, 0.9, 0.5, 0.6, n_sim=60) < 0.2  # equal gaps in B and C: DiD 0
    # a wrong sign never counts as success
    assert simulate_difference_in_differences(55, 3, 0.86, 0.96, 0.82, 0.38, n_sim=60) == 0.0


def test_simulate_two_condition_power_grows_with_k():
    w3, _ = simulate(55, 3, 0.85, 0.95, alpha=0.0125, n_sim=80)
    w5, _ = simulate(55, 5, 0.85, 0.95, alpha=0.0125, n_sim=80)
    assert w5 >= w3


def test_simulate_without_an_effect_rarely_rejects_and_with_one_often_does():
    none_w, none_m = simulate(40, 3, 0.7, 0.7, n_sim=60)
    big_w, big_m = simulate(40, 3, 0.4, 0.95, n_sim=60)
    assert none_w < 0.2 and none_m < 0.2
    assert big_w > 0.8 and big_m > 0.5
    assert (big_w, big_m) == simulate(40, 3, 0.4, 0.95, n_sim=60)          # same seed, same result


def test_main_writes_one_csv_row_per_n_and_k(tmp_path, capsys):
    out = tmp_path / "sub" / "power.csv"
    code = power.main(["--p-a", "0.5", "--p-b", "0.9", "--n-tasks", "10,12", "--k", "1,2", "--n-sim", "30",
                       "--out", str(out)])
    assert code == 0
    rows = list(csv.DictReader(out.open(encoding="utf-8")))
    assert [(r["n_tasks"], r["k"]) for r in rows] == [("10", "1"), ("10", "2"), ("12", "1"), ("12", "2")]
    assert {r["alpha"] for r in rows} == {"0.0125"}                       # 0.05 / 4: three H2 tests plus H3
    assert {(r["p_a"], r["p_b"], r["kappa"]) for r in rows} == {("0.5", "0.9", "8.0")}
    expected_w, expected_m = power.simulate(12, 2, 0.5, 0.9, 8.0, 0.05 / 4, 30)
    last = rows[-1]
    assert float(last["power_wilcoxon"]) == expected_w and float(last["power_mcnemar"]) == expected_m
    printed = capsys.readouterr().out.splitlines()
    assert len(printed) == 4 and "'power_wilcoxon'" in printed[0]


def test_main_passes_kappa_and_alpha_to_the_simulation(tmp_path):
    out = tmp_path / "power.csv"
    power.main(["--p-a", "0.55", "--p-b", "0.9", "--kappa", "4", "--alpha", "0.01", "--n-tasks", "15", "--k", "3",
                "--n-sim", "25", "--out", str(out)])
    row = next(csv.DictReader(out.open(encoding="utf-8")))
    assert (row["kappa"], row["alpha"]) == ("4.0", "0.01")
    assert float(row["power_wilcoxon"]) == power.simulate(15, 3, 0.55, 0.9, 4.0, 0.01, 25)[0]


# ------------------------------------------------------------------ defaults, boundaries, the copula and the CLI
import builtins  # noqa: E402
import inspect  # noqa: E402
import pathlib  # noqa: E402
import runpy  # noqa: E402
import sys  # noqa: E402
import warnings  # noqa: E402

import numpy as np  # noqa: E402
import pytest  # noqa: E402
from scipy import stats  # noqa: E402

from tsbench.stats.hypotheses import wilcoxon_zero  # noqa: E402


def reference_did_power(n_tasks, k, hi_b, hi_c, lo_b, lo_c, rho, kappa, alpha, n_sim, seed):
    """H3 power written out from its definition (Gaussian copula between the two models, Beta task latents)."""
    rng = np.random.default_rng(seed)
    hits = 0
    for _ in range(n_sim):
        z_hi = rng.standard_normal(n_tasks)
        z_lo = rho * z_hi + np.sqrt(1 - rho ** 2) * rng.standard_normal(n_tasks)
        u_hi, u_lo = stats.norm.cdf(z_hi), stats.norm.cdf(z_lo)
        r = {}
        for name, u, mean in (("hb", u_hi, hi_b), ("hc", u_hi, hi_c), ("lb", u_lo, lo_b), ("lc", u_lo, lo_c)):
            r[name] = rng.binomial(k, stats.beta.ppf(u, mean * kappa, (1 - mean) * kappa)) / k
        d = (r["hb"] - r["lb"]) - (r["hc"] - r["lc"])
        hits += bool(wilcoxon_zero(d) < alpha and d.mean() > 0)
    return hits / n_sim


def test_did_power_matches_the_definition_for_several_correlations():
    args = (6, 3, 0.86, 0.96, 0.38, 0.82)
    got = {}
    for rho in (0.9, 0.0, 0.5):
        got[rho] = simulate_difference_in_differences(*args, rho=rho, alpha=0.2, n_sim=60, seed=7)
        assert got[rho] == reference_did_power(*args, rho, 8.0, 0.2, 60, 7)
        assert 0.1 < got[rho] < 1.0
    assert len(set(got.values())) > 1                          # the correlation changes the answer
    assert simulate_difference_in_differences(*args, rho=0.9, kappa=3.0, alpha=0.2, n_sim=60, seed=7) == (
        reference_did_power(*args, 0.9, 3.0, 0.2, 60, 7))


def test_public_defaults_are_the_preregistered_ones():
    two = inspect.signature(simulate).parameters
    assert {n: two[n].default for n in ("kappa", "alpha", "n_sim", "seed")} == {
        "kappa": 8.0, "alpha": 0.05, "n_sim": 1000, "seed": 1}
    did = inspect.signature(simulate_difference_in_differences).parameters
    assert {n: did[n].default for n in ("rho", "kappa", "alpha", "n_sim", "seed")} == {
        "rho": 0.5, "kappa": 8.0, "alpha": 0.0125, "n_sim": 1000, "seed": 1}


def test_did_power_is_not_random_without_a_seed_argument():
    args = (10, 3, 0.8, 0.9, 0.4, 0.8)
    runs = {simulate_difference_in_differences(*args, alpha=0.2, n_sim=100) for _ in range(3)}
    assert len(runs) == 1 and 0 < next(iter(runs)) < 1


def test_did_power_strict_inequalities_with_one_task():
    # one task: the Wilcoxon p-value is exactly 1, so it is never below alpha = 1
    assert simulate_difference_in_differences(1, 1, 0.9, 0.1, 0.1, 0.9, alpha=1.0, n_sim=200) == 0.0
    # a mean difference of exactly zero is not a success even when p < alpha
    ties = simulate_difference_in_differences(1, 1, 0.5, 0.5, 0.5, 0.5, alpha=2.0, n_sim=400)
    assert 0 < ties < 0.5          # only d > 0 counts; d == 0 (frequent with k = 1) and d < 0 do not


def test_two_condition_power_uses_strict_inequalities_and_starts_from_zero():
    # one task: both p-values are exactly 1
    assert simulate(1, 1, 0.5, 0.9, alpha=1.0, n_sim=50) == (0.0, 0.0)
    # no chance of p < 1e-12 with a handful of tasks: no hits, not one hit
    assert simulate(6, 1, 0.5, 0.5, alpha=1e-12, n_sim=50) == (0.0, 0.0)


def test_two_condition_power_seed_and_dispersion_change_the_result():
    base = simulate(8, 2, 0.5, 0.9, n_sim=100)
    assert base == simulate(8, 2, 0.5, 0.9, kappa=8.0, alpha=0.05, n_sim=100, seed=1)
    assert all(0 < v < 1 and v * 100 == pytest.approx(round(v * 100)) for v in base)
    assert base != simulate(8, 2, 0.5, 0.9, n_sim=100, seed=2)
    assert base != simulate(8, 2, 0.5, 0.9, kappa=9.0, n_sim=100)


def test_defaults_give_a_thousand_repeats_and_seed_one():
    # two tasks, k = 1: cheap enough to run the default 1000 repeats; hits / 1000 is a multiple of 0.001
    w, m = simulate(2, 1, 0.3, 0.8, alpha=0.6)
    assert (w, m) == simulate(2, 1, 0.3, 0.8, alpha=0.6, n_sim=1000, seed=1)
    assert 0 < w < 1 and w * 1000 == pytest.approx(round(w * 1000), abs=1e-9)
    assert (w, m) != simulate(2, 1, 0.3, 0.8, alpha=0.6, seed=2)
    did = simulate_difference_in_differences(2, 1, 0.9, 0.5, 0.4, 0.6, alpha=0.6)
    assert did == simulate_difference_in_differences(2, 1, 0.9, 0.5, 0.4, 0.6, alpha=0.6, n_sim=1000, seed=1)
    assert 0 < did < 1 and did * 1000 == pytest.approx(round(did * 1000), abs=1e-9)
    assert did != simulate_difference_in_differences(2, 1, 0.9, 0.5, 0.4, 0.6, alpha=0.6, seed=2)


@pytest.fixture
def fake_simulate(monkeypatch):
    """Replace the simulation by a recorder, so that the CLI defaults can be read without running 1000 repeats."""
    calls = []

    def fake(n_tasks, k, p_a, p_b, kappa=8.0, alpha=0.05, n_sim=1000, seed=1):
        calls.append((n_tasks, k, p_a, p_b, kappa, alpha, n_sim))
        return 0.5, 0.25

    monkeypatch.setattr(power, "simulate", fake)
    return calls


def test_main_defaults_for_grid_alpha_kappa_and_repeats(tmp_path, fake_simulate):
    out = tmp_path / "p.csv"
    assert power.main(["--p-a", "0.55", "--p-b", "0.9", "--out", str(out)]) == 0
    grid = [(n, k) for n in (20, 30, 40, 60) for k in (1, 3, 5)]
    assert [(c[0], c[1]) for c in fake_simulate] == grid
    assert all(c[2:] == (0.55, 0.9, 8.0, 0.05 / 4, 1000) for c in fake_simulate)
    rows = list(csv.DictReader(out.open(encoding="utf-8")))
    assert [(int(r["n_tasks"]), int(r["k"])) for r in rows] == grid
    assert list(rows[0]) == ["n_tasks", "k", "p_a", "p_b", "kappa", "alpha", "power_wilcoxon", "power_mcnemar"]
    assert (rows[0]["power_wilcoxon"], rows[0]["power_mcnemar"]) == ("0.5", "0.25")


def test_main_n_sim_option_reaches_the_simulation(tmp_path, fake_simulate):
    power.main(["--p-a", "0.5", "--p-b", "0.9", "--n-tasks", "7", "--k", "2", "--n-sim", "123", "--out",
                str(tmp_path / "p.csv")])
    assert fake_simulate == [(7, 2, 0.5, 0.9, 8.0, 0.05 / 4, 123)]


def test_main_requires_both_success_rates(capsys):
    with pytest.raises(SystemExit) as exc:
        power.main(["--p-b", "0.9"])
    assert exc.value.code == 2 and "--p-a" in capsys.readouterr().err
    with pytest.raises(SystemExit) as exc:
        power.main(["--p-a", "0.5"])
    assert exc.value.code == 2 and "--p-b" in capsys.readouterr().err


def test_main_default_out_is_power_csv_in_the_current_directory(tmp_path, monkeypatch, fake_simulate):
    monkeypatch.chdir(tmp_path)
    power.main(["--p-a", "0.5", "--p-b", "0.9", "--n-tasks", "7", "--k", "2"])
    assert (tmp_path / "power.csv").exists()


def test_main_creates_missing_folders_and_writes_utf8_csv_lines(tmp_path, monkeypatch, fake_simulate):
    seen = []
    real = pathlib.Path.open

    def spy(self, *args, **kwargs):
        seen.append((args, kwargs))
        return real(self, *args, **kwargs)

    monkeypatch.setattr(pathlib.Path, "open", spy)
    out = tmp_path / "a" / "b" / "p.csv"
    power.main(["--p-a", "0.5", "--p-b", "0.9", "--n-tasks", "7", "--k", "2", "--out", str(out)])
    assert seen == [(("w",), {"newline": "", "encoding": "utf-8"})]
    assert out.read_bytes().startswith(b"n_tasks,k,p_a,p_b,kappa,alpha,power_wilcoxon,power_mcnemar\r\n7,2,")
    power.main(["--p-a", "0.5", "--p-b", "0.9", "--n-tasks", "7", "--k", "2", "--out", str(out)])   # folder exists


def test_running_the_module_as_a_script_exits_with_main_status(tmp_path, monkeypatch):
    out = tmp_path / "p.csv"
    monkeypatch.setattr(sys, "argv", ["power", "--p-a", "0.5", "--p-b", "0.9", "--n-tasks", "6", "--k", "1",
                                      "--n-sim", "10", "--out", str(out)])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)       # runpy: the module is already imported
        with pytest.raises(SystemExit) as exc:
            runpy.run_module("tsbench.stats.power", run_name="__main__")
    assert exc.value.code == 0 and out.exists()
    assert builtins.open is not None


def test_default_alpha_is_the_holm_worst_case_of_the_four_primary_tests(tmp_path, fake_simulate):
    """The primary Holm family is three H2 tests plus H3: the worst case is 0.05 / (len(MODELS) + 1)."""
    from tsbench.stats.hypotheses import MODELS

    power.main(["--p-a", "0.5", "--p-b", "0.9", "--n-tasks", "7", "--k", "2", "--out", str(tmp_path / "p.csv")])
    assert fake_simulate[0][5] == 0.05 / (len(MODELS) + 1) == 0.0125
    power.main(["--p-a", "0.5", "--p-b", "0.9", "--n-tasks", "7", "--k", "2", "--alpha", "0.05",
                "--out", str(tmp_path / "p.csv")])
    assert fake_simulate[1][5] == 0.05
