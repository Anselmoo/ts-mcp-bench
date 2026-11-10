"""Tests for src/tsbench/analyze/strategy.py: the solution strategy of a run, read from its tool calls and code."""
from __future__ import annotations

import pytest
from analyze_runs import bash, mcp, read_csv, result, write_run, write_scores

from tsbench.analyze import strategy
from tsbench.analyze.common import accuracy
from tsbench.score.solution_path import solution_path

ANSWER = {"Dq": 2044.0, "B": 702.0, "C": None, "out_of_scope": False, "reason": "fit"}


def _tags(tmp_path, events):
    path = write_run(tmp_path, "m/B/medium/P-numerical-01-k1", [*events, *result(ANSWER)])
    return strategy.strategies(solution_path(path))


@pytest.mark.parametrize("code,tags", [
    ("import numpy as np\nw = np.linalg.eigvalsh(H)", ["diagonalisation"]),
    ("from scipy.optimize import least_squares\nr = least_squares(f, x0)", ["least_squares"]),
    ("from scipy.optimize import curve_fit", ["least_squares"]),
    ("from scipy.optimize import brentq\nx = brentq(g, 1, 2)", ["root_find"]),
    ("import sympy as sp\nsp.solve(eq)", ["symbolic"]),
    ("from scipy.interpolate import interp1d", ["interpolation"]),
    ("w = np.linalg.eigh(H)\nfrom scipy.optimize import minimize", ["diagonalisation", "least_squares"]),
    ("dq = 18980 / 10\nprint(dq)", ["closed_form"]),
])
def test_tags_of_bash_code(tmp_path, code, tags):
    assert _tags(tmp_path, bash("a", f"python3 - <<'EOF'\n{code}\nEOF", "ok")) == tags


def test_tags_of_mcp_calls(tmp_path):
    events = [*mcp("a", "ts_terms_table_data", {"d_count": 2}, "{}"),
              *mcp("b", "ts_fit_spectrum", {"d_count": 2}, "{}"),
              *mcp("c", "ts_ratio_fit_app", {"d_count": 2}, "{}")]
    assert _tags(tmp_path, events) == ["mcp_fit", "mcp_other", "mcp_table"]


def test_a_run_without_tool_calls_has_no_strategy(tmp_path):
    assert _tags(tmp_path, []) == ["none"]


@pytest.mark.parametrize("tags,primary", [
    (["diagonalisation", "least_squares"], "diagonalisation"),
    (["least_squares", "symbolic"], "least_squares"),
    (["mcp_fit", "mcp_table"], "mcp_fit"),
    (["mcp_table"], "mcp_table"),
    (["closed_form"], "closed_form"),
    (["none"], "none"),
])
def test_the_primary_strategy_follows_a_fixed_order(tags, primary):
    assert strategy.primary(tags) == primary


def test_main_writes_runs_and_shares_per_group(tmp_path, capsys):
    runs, out = tmp_path / "runs", tmp_path / "out"
    eig = bash("a", "python3 - <<'EOF'\nimport numpy as np\nprint(np.linalg.eigvalsh(H))\nEOF", "Dq = 2044.0")
    write_run(runs, "m/B/medium/P-numerical-01-k1", [*eig, *result(ANSWER)])
    write_run(runs, "m/B/medium/P-numerical-01-k2", [*eig, *result(ANSWER)])
    write_run(runs, "m/B/medium/P-numerical-01-k3", [*bash("a", "echo 1", "1"), *result(ANSWER)])
    write_scores(runs, [{"run_id": "m/B/medium/P-numerical-01-k1", "correct": "True"},
                        {"run_id": "m/B/medium/P-numerical-01-k2", "correct": "False"},
                        {"run_id": "m/B/medium/P-numerical-01-k3", "correct": "True"}])
    assert strategy.main(["--runs", str(runs), "--out", str(out)]) == 0
    rows = read_csv(out / "runs.csv")
    assert [r["primary"] for r in rows] == ["diagonalisation", "diagonalisation", "closed_form"]
    assert rows[0]["methods"] == "eigen_solver" and rows[0]["n_linked"] == "1"
    groups = read_csv(out / "by_group.csv")
    diag = [g for g in groups if g["grouping"] == "primary" and g["strategy"] == "diagonalisation"
            and g["class"] == "all"]
    assert len(diag) == 1
    assert (diag[0]["n_runs"], diag[0]["n_correct"], diag[0]["share"], diag[0]["accuracy"]) == ("2", "1",
                                                                                               "0.666667", "0.5")
    assert {g["class"] for g in groups} == {"all", "numerical"}
    assert "strategy" in (out / "README.md").read_text(encoding="utf-8")
    assert "runs: 3" in capsys.readouterr().out


@pytest.mark.parametrize("tool,tags", [
    ("mcp__tanabesugano__ts_terms_table_data", ["mcp_table"]),
    ("mcp__tanabesugano__ts_ratio_fit_app", ["mcp_other"]),
    ("mcp__tanabesugano__ts_fit_plot_app", ["mcp_fit"]),
    ("mcp__a__b__ts_fit_spectrum", ["mcp_other"]),  # all after the second `__` is the tool name
])
def test_the_tag_of_one_mcp_tool(tool, tags):
    assert strategy.strategies({"steps": [{"tool": tool, "command": ""}]}) == tags


def test_no_tags_have_the_primary_strategy_none():
    assert strategy.primary([]) == "none"
    assert strategy.primary(["no such tag"]) == "none"


def test_the_groups_of_strategies_are_exact():
    rows = [{"model": "m", "condition": "B", "class": "numerical", "primary": "diagonalisation",
             "strategies": "diagonalisation least_squares", "correct": True},
            {"model": "m", "condition": "B", "class": "numerical", "primary": "least_squares",
             "strategies": "least_squares", "correct": None}]

    def row(cls, grouping, strat, n, k):
        acc = accuracy(k, n)
        return {"model": "m", "condition": "B", "class": cls, "grouping": grouping, "strategy": strat, "n_runs": n,
                "share": n / 2, "n_correct": k, "accuracy": k / n, "ci_lo": acc["ci_lo"], "ci_hi": acc["ci_hi"]}

    assert strategy._groups(rows) == [
        row(cls, grouping, strat, n, k) for cls in ("all", "numerical")
        for grouping, strat, n, k in (("primary", "diagonalisation", 1, 1), ("primary", "least_squares", 1, 0),
                                      ("tag", "diagonalisation", 1, 1), ("tag", "least_squares", 2, 1))]
