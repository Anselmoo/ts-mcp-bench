"""Tests for src/tsbench/report/svg/pack.py: the surviving mutants grouped by module and function for the text list."""
from __future__ import annotations

from tsbench.report.svg.pack import by_module


def _s(shard: str, module: str, function: str, i: int) -> dict:
    return {"shard": shard, "module": module, "function": function,
            "mutant": f"{module}.x_{function}__mutmut_{i}", "diff": f"--- {i}\n+++ {i}\n"}


SURV = (
    [_s("run", "tsbench.run.doctor", "handshake", i) for i in range(5)]
    + [_s("run", "tsbench.run.doctor", "_probe", i) for i in range(5, 7)]
    + [_s("run", "tsbench.run.env", "load", i) for i in range(3)]
    + [_s("score", "tsbench.score.numeric", "Parser.parse", i) for i in range(4)]
    + [_s("score", "tsbench.score.numeric", "number", 9)]
    + [_s("stats", "tsbench.stats.x", "f", 1)]
)


def test_by_module_structure_and_order() -> None:
    out = by_module(SURV)
    assert [m["module"] for m in out] == ["tsbench.run.doctor", "tsbench.score.numeric", "tsbench.run.env",
                                          "tsbench.stats.x"]
    doctor = out[0]
    assert [f["function"] for f in doctor["functions"]] == ["handshake", "_probe"]
    assert len(doctor["functions"][0]["mutants"]) == 5
    assert set(doctor["functions"][0]["mutants"][0]) == {"mutant", "diff"}


def test_by_module_empty() -> None:
    assert by_module([]) == []
