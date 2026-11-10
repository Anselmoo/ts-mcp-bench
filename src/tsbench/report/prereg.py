"""The preregistered tests of a confirmatory run set, as table rows of the report pages.

    hypotheses(run_sets)   one block per run set that holds a readable hypotheses.json

`tsbench stats hypotheses` writes `hypotheses.json` into a run set: the primary family (H2 per model, C − B, and H3,
the difference in differences of the last and the first model under B and C; Holm over the family) and the secondary
tests without a multiplicity correction (H1 per model, C − A, and the exact McNemar test on the task majorities of
each H1 and H2 pair). A block holds `primary` and `secondary` (paired tests: n tasks, mean difference of the per-task
shares in percentage points with its 95 % interval, p, and in `primary` the Holm p), `mcnemar` (the base condition,
the tasks solved under it only, those solved under C only, p), `k_layers` as the file states them and `other`, the
number of rows of other tests (H4) that no table shows, and `efficiency`, the descriptive ratios of the file: one row
per metric and model with the median of the per-task ratios C/A and C/B and their 95 % intervals, over all runs and
over the correct runs (`ratios`: text, `tasks`: the number of tasks, by the keys `A`, `B`, `A_correct`, `B_correct`).
They are no tests and carry no p value. Every value is copied from the file; nothing is computed again.
`family` is "secondary" for a file of the secondary family (`stats hypotheses --family secondary`: Holm over the H2
tests of the open-weight plans, no H3), else "primary". A family of several run sets keeps its file in the folder that
holds them: that folder gives one block, after the blocks of the run sets.
"""
from __future__ import annotations

import json
import pathlib
from collections.abc import Iterable

from tsbench.report.base import as_number, as_run_sets
from tsbench.report.svg.base import fixed
from tsbench.score.run_sets import RunSet

__all__ = ["FILE", "hypotheses", "p_text"]

FILE = "hypotheses.json"
BASE = {"H1": "A", "H2": "B"}  # the condition each test compares C with
_SUP = str.maketrans("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹")
MINUS = "−"
METRICS = {"total_tokens": "Total tokens", "output_tokens": "Output tokens", "thinking_tokens": "Thinking tokens",
           "cost_usd": "Cost", "duration_s": "Duration"}


def p_text(p: float | None) -> str:
    """A p value: three decimals from 0.001 up, below that two significant digits as `1.8 × 10⁻⁵` (a p value of the
    primary family can be far below a thousandth, and its size is the result)."""
    if p is None:
        return "–"
    if p >= 0.001:
        return fixed(p, 3)
    mantissa, exponent = f"{p:.1e}".split("e")
    return f"{mantissa} × 10{str(int(exponent)).translate(_SUP)}"


def _pp(x: float | None, sign: bool = True) -> str:
    """A difference of shares (a fraction) in percentage points with one decimal and a true minus sign."""
    return "–" if x is None else fixed(100 * x, 1, sign=sign).replace("-", MINUS)


def _split_name(name: str) -> tuple[str, str]:
    """`H2_claude-opus-5-5_mcnemar` -> ("H2", "claude-opus-5-5"); `H3` -> ("H3", "")."""
    test, _, model = name.removesuffix("_mcnemar").partition("_")
    return test, model


def _paired(r: dict) -> dict:
    test, model = _split_name(str(r.get("name") or ""))
    ci = r.get("ci")
    lo, hi = (as_number(ci[0]), as_number(ci[1])) if isinstance(ci, list) and len(ci) == 2 else (None, None)
    diff = as_number(r.get("mean_diff"))
    return {"test": test, "model": model, "comparison": f"C {MINUS} {BASE[test]}" if test in BASE else "",
            "n": r.get("n"), "missing": bool(r.get("missing")), "diff": _pp(diff) + (" pp" if diff is not None else ""),
            "ci": f"{_pp(lo)} to {_pp(hi)} pp" if lo is not None and hi is not None else "–",
            "p": p_text(as_number(r.get("p"))), "p_holm": p_text(as_number(r.get("p_holm")))}


def _mcnemar(r: dict) -> dict:
    test, model = _split_name(str(r.get("name") or ""))
    return {"test": test, "model": model, "base": BASE.get(test, ""), "n": r.get("n"), "only_base": r.get("b"),
            "only_c": r.get("c"), "p": p_text(as_number(r.get("p")))}


def _ratio_text(r: dict) -> str:
    ratio, ci = as_number(r.get("median_ratio")), r.get("ratio_ci")
    if ratio is None:
        return "–"
    if isinstance(ci, list) and len(ci) == 2 and None not in (lo := [as_number(x) for x in ci]):
        return f"{fixed(ratio, 2)} ({fixed(lo[0], 2)} to {fixed(lo[1], 2)})"
    return fixed(ratio, 2)


def _efficiency(rows: list) -> list[dict]:
    """One row per metric and model, in the order of the file."""
    out: dict[tuple[str, str], dict] = {}
    for r in rows:
        if not isinstance(r, dict):
            continue
        metric, model = str(r.get("metric") or ""), str(r.get("model") or "")
        row = out.setdefault((metric, model), {"metric": METRICS.get(metric, metric), "model": model, "ratios": {},
                                               "tasks": {}})
        key = f"{r.get('base')}_correct" if r.get("correct_only") else str(r.get("base"))
        row["ratios"][key], row["tasks"][key] = _ratio_text(r), r.get("n")
    return list(out.values())


def _block(set_name: str, data: dict) -> dict:
    primary = [_paired(r) for r in data.get("primary") or [] if isinstance(r, dict)]
    h2 = [r["model"] for r in primary if r["test"] == "H2"]
    for r in primary:
        if r["test"] == "H3":
            r["comparison"] = (f"({h2[-1]} {MINUS} {h2[0]}) under B minus under C" if len(h2) > 1
                               else "difference in differences, B minus C")
    secondary, mcnemar, other = [], [], 0
    for r in data.get("secondary") or []:
        if not isinstance(r, dict):
            continue
        name = str(r.get("name") or "")
        if name.endswith("_mcnemar"):
            mcnemar.append(_mcnemar(r))
        elif name.startswith("H1_"):
            secondary.append(_paired(r))
        else:
            other += 1
    return {"set": set_name, "family": "secondary" if data.get("family") == "secondary" else "primary",
            "primary": primary, "secondary": secondary, "mcnemar": mcnemar,
            "k_layers": data.get("k_layers") or {}, "other": other,
            "efficiency": _efficiency(data.get("efficiency") or [])}


def hypotheses(run_sets: Iterable[RunSet | pathlib.Path | str]) -> list[dict]:
    """One block per run set whose folder holds a readable `hypotheses.json` (a JSON object), in the order given."""
    sets = as_run_sets(run_sets)
    out = [b for rs in sets if (b := _read(rs.path / FILE, rs.name))]
    paths = {rs.path.resolve() for rs in sets}
    parents = dict.fromkeys(rs.path.resolve().parent for rs in sets)
    out += [b for d in parents if d not in paths and (b := _read(d / FILE, d.name))]
    return out


def _read(path: pathlib.Path, name: str) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return _block(name, data) if isinstance(data, dict) else None
