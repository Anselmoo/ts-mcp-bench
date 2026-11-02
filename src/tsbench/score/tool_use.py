"""Tool-use quality per transcript (docs/methods.md, section 5.4): did the model call the right tool, with the right
electron count, and how often did a call fail? Descriptive only; no hypothesis test, no API call.

    rows = tool_use_rows(runs, "pilot")   # one row per transcript of a task in the split
"""
from __future__ import annotations

import math
import pathlib

from tsbench.score.extract import STRUCTURED_TOOL, Transcript
from tsbench.score.score import find_transcripts, not_evaluable_reason, read_cached

MCP_PREFIX = "mcp__tanabesugano__"

# Expected tool per task class: the tool a careful user would reach for. This table and FIT_TOOLS describe tool use;
# they are not a correctness criterion. Lookup is f"{class}/{subtype}", then class, then the empty set (no fit tool
# expected).
EXPECTED_TOOLS: dict[str, frozenset[str]] = {
    "closed_form": frozenset({"ts_fit_spectrum"}),
    "numerical": frozenset({"ts_fit_spectrum"}),
    "racah_c": frozenset({"ts_terms_table_data", "ts_fit_spectrum"}),
    "experimental": frozenset({"ts_fit_spectrum"}),
    "numerical_hard": frozenset({"ts_fit_spectrum"}),
    "tetrahedral": frozenset({"ts_fit_spectrum"}),
    "crossover": frozenset({"ts_spin_crossover_app"}),
    "curve": frozenset({"ts_compute_app", "ts_terms_table_data"}),
    "literature_all": frozenset({"ts_fit_spectrum"}),
    "literature_new": frozenset({"ts_fit_spectrum"}),
    "batch/crossover_series": frozenset({"ts_spin_crossover_app"}),
    "batch/band_series": frozenset({"ts_compute_app", "ts_terms_table_data"}),
    "pairing": frozenset({"ts_terms_table_data"}),
    "diagram": frozenset({"ts_compute_app", "ts_terms_table_data"}),
    "out_of_scope/charge_transfer": frozenset(),
    "out_of_scope/jahn_teller": frozenset(),
}
# Every tool that fits a spectrum. Used only for tasks with an empty expected set.
FIT_TOOLS: frozenset[str] = frozenset(
    {"ts_fit_spectrum", "ts_ratio_fit_app", "ts_reverse_fit_app", "ts_fit_plot_app", "ts_fit_script"}
)

_METRIC_KEYS = ["n_calls", "n_distinct", "n_tool_errors", "tool_error_rate", "expected_tool_used",
                "first_expected_index", "d_count_matches", "n_bash_calls"]
TOOL_USE_COLUMNS = ["model", "condition", "effort", "task_id", "k_index", "class", "subtype"] + _METRIC_KEYS


def strip_prefix(name: str) -> str:
    """`mcp__tanabesugano__ts_fit_spectrum` -> `ts_fit_spectrum`; any other name (e.g. `Bash`) is unchanged."""
    name = name if isinstance(name, str) else ""
    return name[len(MCP_PREFIX):] if name.startswith(MCP_PREFIX) else name


def expected_tools(task: dict) -> frozenset[str]:
    """Tools a competent condition-C run would call for this task (see EXPECTED_TOOLS)."""
    cls = task.get("class")
    for key in (f"{cls}/{task.get('subtype')}", cls):
        if key in EXPECTED_TOOLS:
            return EXPECTED_TOOLS[key]
    return frozenset()


def _count_errors(transcript: Transcript, ids: set[str]) -> int:
    """Counted calls (tool_use ids in `ids`: not StructuredOutput, whose rejected answers are no tool error) that have
    at least one tool_result with is_error true. A call counts once, so the rate stays at most 1 even when a result is
    repeated. Transcript.tool_results drops the flag, so scan the raw events."""
    failed: set[str] = set()
    for event in transcript.events:
        if event.get("type") != "user":
            continue
        message = event.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, list):
            continue
        failed.update(b["tool_use_id"] for b in content if isinstance(b, dict) and b.get("type") == "tool_result"
                      and b.get("is_error") is True and isinstance(b.get("tool_use_id"), str)
                      and b["tool_use_id"] in ids)
    return len(failed)


def _as_int(v):
    """An integer from an int, an integral float or an integer-valued string; None otherwise (bool is not a count)."""
    if isinstance(v, bool) or v is None:
        return None
    try:
        f = float(v.strip() if isinstance(v, str) else v)
    except (TypeError, ValueError):
        return None
    return int(f) if math.isfinite(f) and f == int(f) else None


def _d_count_matches(task: dict, names: list[str], uses: list[dict]):
    """Do the `d_count` arguments of the ts_* calls include the task's electron count? None when undecidable."""
    d = _as_int(task.get("d_count"))
    given = []
    for name, use in zip(names, uses, strict=False):
        inp = use.get("input")
        if name.startswith("ts_") and isinstance(inp, dict) and _as_int(inp.get("d_count")) is not None:
            given.append(_as_int(inp["d_count"]))
    if d is None or not given:
        return None
    accepted = {d, 10 - d} if task.get("geometry") == "Td" else {d}  # Td: the hole count is the same problem
    return any(g in accepted for g in given)


def tool_use(task: dict, transcript: Transcript, condition: str) -> dict:
    """The eight tool-use metrics of one transcript. `expected_tool_used` and `first_expected_index` are for C only."""
    uses = [u for u in transcript.tool_uses if u.get("name") != STRUCTURED_TOOL]
    names = [strip_prefix(u.get("name")) for u in uses]
    n_calls = len(names)
    n_errors = _count_errors(transcript, {u["id"] for u in uses if isinstance(u.get("id"), str)})
    used = first = None
    if condition == "C":
        want = expected_tools(task)
        if want:
            first = next((i for i, n in enumerate(names) if n in want), None)
            used = first is not None
        else:  # nothing to fit (charge transfer, Jahn-Teller): the right move is to call no fit tool
            used = not any(n in FIT_TOOLS for n in names)
    return {
        "n_calls": n_calls, "n_distinct": len(set(names)), "n_tool_errors": n_errors,
        "tool_error_rate": n_errors / n_calls if n_calls else None,
        "expected_tool_used": used, "first_expected_index": first,
        "d_count_matches": _d_count_matches(task, names, uses),
        "n_bash_calls": sum(n == "Bash" for n in names),
    }


def tool_use_rows(runs, split: str = "pilot", version: str = "v2", transcripts: dict | None = None) -> list[dict]:
    """One row per evaluable transcript of a task in `split`, sorted by (model, condition, effort, task_id, k).

    A run that is not evaluable (HTTP 429, API error) never used a tool and has no row. `transcripts` is an optional
    cache (path -> Transcript), see `score.read_cached`."""
    from tsbench.tasks import load  # the only sanctioned task reader

    tasks = {t["id"]: t for t in load(split, version)}
    rows = []
    for path, model, cond, effort, task_id, k in find_transcripts(pathlib.Path(runs)):
        task = tasks.get(task_id)
        if task is None:
            continue
        tr = read_cached(path, transcripts)
        if not_evaluable_reason(tr) is not None:
            continue
        rows.append({"model": model, "condition": cond, "effort": effort, "task_id": task_id, "k_index": k,
                     "class": task["class"], "subtype": task.get("subtype"), **tool_use(task, tr, cond)})
    rows.sort(key=lambda r: (r["model"], r["condition"], r["effort"], r["task_id"], r["k_index"]))
    return rows
