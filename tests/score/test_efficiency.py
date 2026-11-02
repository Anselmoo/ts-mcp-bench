"""Tokens and time per run, and the paired efficiency comparison built on them."""
import csv
import json
import math

import numpy as np
import pytest

from tsbench.score.score import score_dir, usage_detail, wall_time
from tsbench.stats.hypotheses import efficiency, ratio_summary
from tsbench.tasks import load

USAGE = {"input_tokens": 6, "cache_creation_input_tokens": 14324, "cache_read_input_tokens": 7773,
         "output_tokens": 2233, "output_tokens_details": {"thinking_tokens": 1396}}


def test_usage_detail_splits_cache_and_thinking():
    d = usage_detail(USAGE)  # values from a real condition C transcript
    assert d == {"uncached_input_tokens": 6, "cache_creation_tokens": 14324, "cache_read_tokens": 7773,
                 "thinking_tokens": 1396, "total_tokens": 6 + 14324 + 7773 + 2233}
    assert usage_detail(None)["total_tokens"] == 0


def test_wall_time_from_sidecar(tmp_path):
    t = tmp_path / "P-x-k1.jsonl"
    t.write_text("", encoding="utf-8")
    assert wall_time(t) is None
    (tmp_path / "P-x-k1.meta.json").write_text(json.dumps({"wall_time_s": 12.5}), encoding="utf-8")
    assert wall_time(t) == 12.5


def _write_run(runs, model, cond, task, k, correct_answer, out_tokens, ms, wall):
    d = runs / model / cond / "medium"
    d.mkdir(parents=True, exist_ok=True)
    ref = task["reference"]
    if correct_answer:
        ans = {"Dq": ref["Dq"], "B": ref["B"], "C": ref["C"], "out_of_scope": False, "reason": "x"}
    else:
        ans = {"Dq": (ref["Dq"] or 1000) * 1.5, "B": ref["B"], "C": None, "out_of_scope": False, "reason": "x"}
    events = [{"type": "system", "subtype": "init", "tools": [], "mcp_servers": [], "model": model},
              {"type": "result", "subtype": "success", "is_error": False, "result": "ok\n" + json.dumps(ans),
               "total_cost_usd": out_tokens * 1e-6, "num_turns": 1, "duration_ms": ms, "duration_api_ms": ms - 100,
               "usage": {"input_tokens": 10, "output_tokens": out_tokens,
                         "output_tokens_details": {"thinking_tokens": out_tokens // 2}}}]
    (d / f"{task['id']}-k{k}.jsonl").write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")
    (d / f"{task['id']}-k{k}.meta.json").write_text(json.dumps({"wall_time_s": wall}), encoding="utf-8")


def test_scores_and_rates_carry_efficiency(tmp_path):
    task = next(t for t in load("pilot") if not t["expect_out_of_scope"])
    m = "claude-opus-5-5"
    _write_run(tmp_path, m, "A", task, 1, True, 8000, 40000, 41.0)
    _write_run(tmp_path, m, "A", task, 2, False, 6000, 30000, 31.0)
    _write_run(tmp_path, m, "C", task, 1, True, 2000, 10000, 12.0)
    _write_run(tmp_path, m, "C", task, 2, True, 3000, 14000, 16.0)
    score_dir(tmp_path, "pilot")
    with open(tmp_path / "scores.csv", newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    a1 = next(r for r in rows if r["condition"] == "A" and r["k_index"] == "1")
    assert a1["thinking_tokens"] == "4000" and a1["duration_s"] == "40.0" and a1["wall_time_s"] == "41.0"
    with open(tmp_path / "rates.csv", newline="", encoding="utf-8") as fh:
        rates = {r["condition"]: r for r in csv.DictReader(fh)}
    assert float(rates["A"]["mean_output_tokens"]) == 7000            # both runs
    assert float(rates["A"]["mean_output_tokens_correct"]) == 8000    # the correct run only
    assert float(rates["C"]["mean_duration_s"]) == pytest.approx(12.0)
    eff = {r["name"]: r for r in efficiency(tmp_path / "rates.csv", models=(m,))}
    row = eff[f"EFF_output_tokens_CvsA_{m}"]
    assert row["median_ratio"] == pytest.approx(2500 / 7000) and row["n"] == 1
    assert eff[f"EFF_output_tokens_CvsA_{m}_correct"]["median_ratio"] == pytest.approx(2500 / 8000)
    assert not any(r["base"] == "B" for r in eff.values())            # no B cell -> no B rows


def test_ratio_summary_paired_and_robust():
    a = np.array([100.0, 200.0, 400.0, 0.0])
    b = np.array([50.0, 100.0, 200.0, 10.0])  # half the tokens on every usable task; a=0 dropped
    s = ratio_summary(a, b)
    assert s["n"] == 3 and s["median_ratio"] == pytest.approx(0.5)
    assert s["ratio_ci"][0] == pytest.approx(0.5) and s["ratio_ci"][1] == pytest.approx(0.5)
    assert ratio_summary(np.zeros(3), np.ones(3)) is None
    assert not math.isnan(s["p"])
