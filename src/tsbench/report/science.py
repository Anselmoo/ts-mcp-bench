"""The facts the full report shares with its single pages: the evaluable runs grouped by model and condition, the
paired differences, the error of a fit answer in units of its
tolerance, the tolerance of a task class as its records state it, and the test functions per folder of tests/.

report/facts.py builds every number of the page from these; nothing here writes text for the reader.
"""
from __future__ import annotations

import ast
import pathlib

from tsbench.report import dashboard
from tsbench.report.base import as_number, is_true
from tsbench.stats.analysis import mcnemar_exact

__all__ = ["CONDS", "LITERATURE", "TOOL_COL", "tolerance_text"]

CONDS = ("A", "B", "C")
LITERATURE = ("experimental", "literature_all", "literature_new")
TOOL_COL = {"B": "n_bash_calls", "C": "n_mcp_calls"}
_FIT = ("Dq", "B", "C")


def _solved(rs: list[dict]) -> bool:
    """A task counts as solved under a condition when more than half of its evaluable runs are correct."""
    return bool(rs) and sum(is_true(r.get("correct")) for r in rs) * 2 > len(rs)


def tolerance_text(tasks: list[dict]) -> str:
    """The tolerance of a task class as its task records state it: `Dq 2 %, B 5 %`. A fit parameter counts only when
    the class requires it; where only some tasks of the class require it the text says how many (`C 15 % (3 of 10
    tasks)`). The other keys (curve, item, ...) are named as the record names them."""
    values: dict[str, set[float]] = {}
    needs = {p: sum(p in (t.get("required") or ()) for t in tasks) for p in _FIT}
    for t in tasks:
        tol = t.get("tolerance") or {}
        required = set(t.get("required") or [])
        for key, v in tol.items():
            if v is None or (key in _FIT and key not in required):
                continue
            values.setdefault(key, set()).add(v)
    def one(key: str) -> str:
        lo, hi = min(values[key]), max(values[key])
        fmt = (lambda x: f"{x:g}") if key.endswith("_abs") else (lambda x: f"{100 * x:g} %")
        return fmt(lo) if lo == hi else fmt(lo) + " to " + fmt(hi)
    def some(key: str) -> str:
        return f" ({needs[key]} of {len(tasks)} tasks)" if 0 < needs[key] < len(tasks) else ""
    parts = [f"{p} {one(p)}{some(p)}" for p in _FIT if p in values]
    if "curve_rel" in values or "curve_abs" in values:
        parts.append(" or ".join(x for x in (f"{one('curve_rel')} relative" if "curve_rel" in values else "",
                                             f"{one('curve_abs')} E/B absolute" if "curve_abs" in values else "")
                                 if x))
    if "item_rel" in values:
        parts.append(f"{one('item_rel')} per item")
    if "item_accuracy_min" in values:
        parts.append(f"at least {one('item_accuracy_min')} of the values")
    known = set(_FIT) | {"curve_rel", "curve_abs", "item_rel", "item_accuracy_min"}
    parts += [f"{k} {one(k)}" for k in values if k not in known]
    return "; ".join(parts) if any(k not in _FIT for k in values) else ", ".join(parts) or "none"


class _Runs:
    """The evaluable runs of conditions A, B and C that have a task record, grouped by model and condition."""

    def __init__(self, data: dict):
        self.all = [r for r in data["rows"] if r.get("_cond") in CONDS and r.get("_task")]
        self.rows = dashboard._evaluable(self.all)
        self.models = sorted({r.get("model", "") for r in self.rows})
        self.cells: dict[tuple[str, str], list[dict]] = {}
        for r in self.rows:
            self.cells.setdefault((r.get("model", ""), r["_cond"]), []).append(r)
        self.tasks = {r["task_id"]: r["_task"] for r in self.all}

    def cell(self, model: str, cond: str, pred=None) -> list[dict]:
        rs = self.cells.get((model, cond), [])
        return [r for r in rs if pred(r)] if pred else rs

    def conds(self, model: str) -> list[str]:
        return [c for c in CONDS if self.cells.get((model, c))]


def _state(lo: float, hi: float) -> str:
    return "higher" if lo > 0 else "lower" if hi < 0 else "zero"


def _contrasts(runs: _Runs, model: str) -> dict[str, dict]:
    """C − A, C − B and B − A of one model (dashboard._contrasts), with the exact McNemar p and the interval state."""
    out = {}
    for x in dashboard._contrasts(runs.cells, model):
        x = dict(x, p=mcnemar_exact(x["only_y"], x["only_x"]), state=_state(x["lo"], x["hi"]))
        out[f"{x['x']}-{x['y']}"] = x
    return out


def _err_over_tol(r: dict) -> float | None:
    """The relative error of the worst required parameter of a fit answer, in units of its tolerance."""
    t = r["_task"]
    worst = None
    for p in t.get("required") or ():
        e = as_number(r.get(f"rel_err_{p.lower()}"))
        tol = (t.get("tolerance") or {}).get(p)
        if e is None or not tol:
            return None
        worst = e / tol if worst is None else max(worst, e / tol)
    return worst


def _is_fit(t: dict) -> bool:
    return t.get("answer_schema") == "fit" and not t.get("expect_out_of_scope") and bool(t.get("required"))


def _test_counts(tests_dir: pathlib.Path) -> list[tuple[str, int]]:
    """Test functions per folder of tests/ (a static count of `def test_...`; parametrised cases count once)."""
    counts: dict[str, int] = {}
    for f in sorted(tests_dir.rglob("test_*.py")):
        rel = f.relative_to(tests_dir)
        folder = rel.parts[0] if len(rel.parts) > 1 else "(top level)"
        try:
            tree = ast.parse(f.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            continue
        n = sum(isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef)) and x.name.startswith("test")
                for x in ast.walk(tree))
        counts[folder] = counts.get(folder, 0) + n
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
