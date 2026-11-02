"""Tests for tsbench.score.tool_use. Tasks are pilot tasks or synthetic dicts; transcripts are fixture-shaped events."""
from __future__ import annotations

import json
import pathlib

import pytest

from tsbench.score import tool_use as tu
from tsbench.score.extract import read_transcript
from tsbench.tasks import load

P = tu.MCP_PREFIX


def task(**kw) -> dict:
    base = {"id": "S-1", "class": "closed_form", "subtype": "d3", "geometry": "Oh", "d_count": 3,
            "required": ["Dq", "B"], "expect_out_of_scope": False}
    base.update(kw)
    return base


def write(path, events) -> pathlib.Path:
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(e) + "\n" for e in events), encoding="utf-8")
    return path


def call(i, name, inp):
    return {"type": "assistant",
            "message": {"content": [{"type": "tool_use", "id": f"t{i}", "name": name, "input": inp}]}}


def result(i, content="ok", **flags):
    block = {"type": "tool_result", "tool_use_id": f"t{i}", "content": content, **flags}
    return {"type": "user", "message": {"content": [block]}}


def run(tmp_path, events, tk=None, cond="C"):
    return tu.tool_use(tk or task(), read_transcript(write(tmp_path / "t.jsonl", events)), cond)


def test_strip_prefix_and_lookup_fallbacks():
    assert tu.strip_prefix(P + "ts_explain") == "ts_explain" and tu.strip_prefix("Bash") == "Bash"
    assert tu.strip_prefix(None) == "" and tu.strip_prefix(P) == ""
    assert tu.expected_tools(task(**{"class": "racah_c"})) == {"ts_terms_table_data", "ts_fit_spectrum"}
    assert tu.expected_tools(task(**{"class": "out_of_scope"}, subtype="jahn_teller")) == frozenset()
    assert tu.expected_tools(task(**{"class": "out_of_scope"}, subtype="new_thing")) == frozenset()  # unknown: empty
    assert tu.expected_tools(task(**{"class": "mystery"})) == frozenset()
    assert tu.expected_tools(task(subtype="anything")) == {"ts_fit_spectrum"}  # class fallback


def test_columns_and_every_pilot_task_has_a_defined_expectation():
    assert tu.TOOL_USE_COLUMNS[-8:] == ["n_calls", "n_distinct", "n_tool_errors", "tool_error_rate",
                                        "expected_tool_used", "first_expected_index", "d_count_matches", "n_bash_calls"]
    assert tu.FIT_TOOLS >= {"ts_fit_spectrum"}
    for t in load("pilot"):
        assert isinstance(tu.expected_tools(t), frozenset)
        # a task that expects out of scope must expect no fit tool; the rest must expect one
        assert (not tu.expected_tools(t)) == bool(t["expect_out_of_scope"]), t["id"]


def test_errors_only_from_user_tool_results_with_true_flag(tmp_path):
    ev = [call(0, "Bash", {}), result(0, is_error=True),
          call(1, "Bash", {}), result(1, is_error=False),
          call(2, "Bash", {}), result(2),
          call(3, "Bash", {}), result(3, content="plain string", is_error="true"),  # not literally True
          {"type": "assistant", "message": {"content": [{"type": "tool_result", "is_error": True}]}}]  # wrong role
    r = run(tmp_path, ev, cond="B")
    assert r["n_calls"] == 4 and r["n_tool_errors"] == 1 and r["tool_error_rate"] == 0.25


def test_user_message_with_string_content_is_ignored(tmp_path):
    ev = [call(0, "Bash", {}), {"type": "user", "message": {"content": "hello"}}, {"type": "user"}]
    assert run(tmp_path, ev, cond="B")["n_tool_errors"] == 0


def test_d_count_coercion(tmp_path):
    def dc(value, tk=None):
        return run(tmp_path, [call(0, P + "ts_fit_spectrum", {"d_count": value})], tk)["d_count_matches"]

    assert dc(3) is True and dc(3.0) is True and dc(" 3 ") is True and dc("3.0") is True
    assert dc(4) is False
    assert dc(True) is None and dc(3.5) is None and dc("three") is None and dc(None) is None  # no usable value
    assert dc(float("nan")) is None


def test_d_count_ignores_non_ts_calls_and_non_dict_input(tmp_path):
    ev = [call(0, "Bash", {"d_count": 3}), call(1, P + "ts_explain", "d_count=3"), call(2, P + "ts_explain", None)]
    assert run(tmp_path, ev)["d_count_matches"] is None
    ev.append(call(3, P + "ts_explain", {"d_count": 5}))   # any ts_* tool counts, not only the expected one
    assert run(tmp_path, ev)["d_count_matches"] is False
    ev.append(call(4, P + "ts_fit_spectrum", {"d_count": 3}))
    assert run(tmp_path, ev)["d_count_matches"] is True     # any-of over the calls


def test_d_count_td_accepts_hole_count_and_oh_does_not(tmp_path):
    td = task(geometry="Td", d_count=7)
    for d, ok in ((7, True), (3, True), (5, False)):
        assert run(tmp_path, [call(0, P + "ts_fit_spectrum", {"d_count": d})], td)["d_count_matches"] is ok
    assert run(tmp_path, [call(0, P + "ts_fit_spectrum", {"d_count": 7})], task(d_count=3))["d_count_matches"] is False
    assert run(tmp_path, [call(0, P + "ts_fit_spectrum", {"d_count": 7})],
               task(d_count=None))["d_count_matches"] is None


def test_expected_tool_is_c_only_and_first_index_counts_all_tools(tmp_path):
    ev = [call(0, "Bash", {}), call(1, P + "ts_explain", {}), call(2, P + "ts_fit_spectrum", {"d_count": 3}),
          call(3, P + "ts_fit_spectrum", {"d_count": 3})]
    c = run(tmp_path, ev, cond="C")
    assert c["expected_tool_used"] is True and c["first_expected_index"] == 2 and c["n_bash_calls"] == 1
    for cond in ("A", "B"):
        r = run(tmp_path, ev, cond=cond)
        assert r["expected_tool_used"] is None and r["first_expected_index"] is None


def test_empty_expected_set_fit_tool_variants(tmp_path):
    oos = task(**{"class": "out_of_scope"}, subtype="jahn_teller", geometry=None, d_count=None,
               expect_out_of_scope=True)
    for name in sorted(tu.FIT_TOOLS):
        assert run(tmp_path, [call(0, P + name, {})], oos)["expected_tool_used"] is False, name
    ok = run(tmp_path, [call(0, "Bash", {}), call(1, P + "ts_explain", {})], oos)
    assert ok["expected_tool_used"] is True and ok["first_expected_index"] is None


def test_truncated_transcript_without_result_event(tmp_path):
    path = write(tmp_path / "t.jsonl", [call(0, P + "ts_fit_spectrum", {"d_count": 3})])
    with open(path, "a", encoding="utf-8") as fh:
        fh.write('{"type": "user", "mess')  # cut mid-line
    r = tu.tool_use(task(), read_transcript(path), "C")
    assert r["n_calls"] == 1 and r["expected_tool_used"] is True and r["n_tool_errors"] == 0


def test_tool_use_rows_filter_and_order(tmp_path):
    tasks = load("pilot")
    a, b = tasks[0], tasks[1]
    root = tmp_path / "runs"
    for model, cond, tid, k in (("m2", "B", a["id"], 1), ("m1", "C", b["id"], 2), ("m1", "C", b["id"], 1),
                                ("m1", "A", a["id"], 1), ("m1", "A", "NOT-A-TASK", 1)):
        calls = [call(0, P + "ts_fit_spectrum", {"d_count": b["d_count"]}), result(0)] if cond == "C" else []
        write(root / model / cond / "medium" / f"{tid}-k{k}.jsonl", calls)
    rows = tu.tool_use_rows(root, "pilot")
    assert [(r["model"], r["condition"], r["task_id"], r["k_index"]) for r in rows] == [
        ("m1", "A", a["id"], 1), ("m1", "C", b["id"], 1), ("m1", "C", b["id"], 2), ("m2", "B", a["id"], 1)]
    assert all(list(r) == tu.TOOL_USE_COLUMNS for r in rows)
    assert rows[1]["class"] == b["class"] and rows[1]["subtype"] == b["subtype"] and rows[1]["k_index"] == 1
    assert rows[1]["expected_tool_used"] is True and rows[1]["d_count_matches"] is True
    assert tu.tool_use_rows(tmp_path / "empty", "pilot") == []


def test_structured_output_is_not_a_tool_call(tmp_path):
    m = run(tmp_path, [call(1, "StructuredOutput", {"Dq": 1}), result(1)], cond="A")
    assert m["n_calls"] == 0 and m["n_distinct"] == 0 and m["tool_error_rate"] is None and m["n_bash_calls"] == 0
    m = run(tmp_path, [call(1, "mcp__tanabesugano__ts_fit_spectrum", {"d_count": 3}), result(1),
                       call(2, "StructuredOutput", {"Dq": 1}), result(2)])
    assert m["n_calls"] == 1 and m["n_distinct"] == 1


# ---------- raw events, defaults ----------

def test_count_errors_goes_through_all_events():
    from tsbench.score.extract import Transcript
    from tsbench.score.tool_use import _count_errors

    def result(**kw):
        return {"type": "tool_result", "tool_use_id": "u", "content": "x", **kw}

    events = [
        {"type": "assistant", "message": {"content": [result(is_error=True)]}},     # not a user event
        {"type": "user", "message": {"content": "plain text"}},                      # content is no list
        {"type": "user", "message": "no dict"},
        {"type": "user"},
        {"type": "user", "message": {"content": [result(is_error=True), result(is_error=False), result(),
                                                 "bare", {"type": "text", "is_error": True},
                                                 result(is_error="true"), result(is_error=True)]}},
        {"type": "user", "message": {"content": [result(is_error=True)]}},
    ]
    assert _count_errors(Transcript(events=events), {"u"}) == 1  # one call counts once, however many error results
    assert _count_errors(Transcript(events=events), {"other"}) == 0  # only the results of the counted calls
    assert _count_errors(Transcript(), {"u"}) == 0


def test_tool_use_rows_defaults_and_arguments(tmp_path, monkeypatch):
    import tsbench.tasks
    from tsbench.score.tool_use import tool_use_rows
    seen = []
    real = tsbench.tasks.load

    def spy(split, version):
        seen.append((split, version))
        return real(split, version)

    monkeypatch.setattr(tsbench.tasks, "load", spy)
    (tmp_path / "runs").mkdir()
    assert tool_use_rows(tmp_path / "runs") == [] and tool_use_rows(str(tmp_path / "runs"), "pilot", "v2") == []
    assert seen == [("pilot", "v2"), ("pilot", "v2")]


def _rows_runs(tmp_path):
    t = load("pilot")[0]
    root = tmp_path / "runs"
    ok = [call(0, P + "ts_fit_spectrum", {"d_count": 3}), result(0)]
    write(root / "m1" / "C" / "medium" / f"{t['id']}-k1.jsonl", ok)
    write(root / "m1" / "C" / "medium" / f"{t['id']}-k2.jsonl",
          [{"type": "result", "subtype": "success", "is_error": True, "api_error_status": 429,
            "result": "API Error: Request rejected (429)"}])
    return root, t


def test_tool_use_rows_skip_runs_that_are_not_evaluable(tmp_path):
    """An HTTP 429 run never started: it must not count as a C run that skipped the expected tool."""
    root, t = _rows_runs(tmp_path)
    rows = tu.tool_use_rows(root, "pilot")
    assert [(r["task_id"], r["k_index"]) for r in rows] == [(t["id"], 1)]


def test_tool_use_rows_take_transcripts_from_the_cache(tmp_path, monkeypatch):
    import builtins

    from tsbench.score import extract

    root, _ = _rows_runs(tmp_path)
    cache = {}
    expected = tu.tool_use_rows(root, "pilot", transcripts=cache)
    assert len(cache) == 2
    opened = []

    def spy(*args, **kwargs):
        opened.append(str(args[0]))
        return builtins.open(*args, **kwargs)

    monkeypatch.setattr(extract, "open", spy, raising=False)
    assert tu.tool_use_rows(root, "pilot", transcripts=cache) == expected
    assert [p for p in opened if p.endswith(".jsonl")] == []


def test_a_rejected_structured_output_is_no_tool_error(tmp_path):
    # one Bash call, three StructuredOutput answers the schema rejected: 0 of 1 calls failed, not 3 of 1
    ev = [call(0, "Bash", {}), result(0),
          call(1, "StructuredOutput", {"Dq": "x"}), result(1, "Output does not match required schema", is_error=True),
          call(2, "StructuredOutput", {"Dq": "y"}), result(2, "Output does not match required schema", is_error=True),
          call(3, "StructuredOutput", {"Dq": "z"}), result(3, "Output does not match required schema", is_error=True)]
    r = run(tmp_path, ev, cond="B")
    assert r["n_calls"] == 1 and r["n_tool_errors"] == 0 and r["tool_error_rate"] == 0.0


def test_condition_a_has_no_tool_errors_and_the_rate_never_exceeds_one(tmp_path):
    ev = [call(0, "StructuredOutput", {"Dq": "x"}), result(0, "bad", is_error=True),
          call(1, "StructuredOutput", {"Dq": "y"}), result(1, "bad", is_error=True)]
    a = run(tmp_path, ev, cond="A")
    assert a["n_calls"] == 0 and a["n_tool_errors"] == 0 and a["tool_error_rate"] is None
    mixed = [call(0, "Bash", {}), result(0, is_error=True), call(1, "StructuredOutput", {}), result(1, is_error=True),
             call(2, "StructuredOutput", {}), result(2, is_error=True)]
    b = run(tmp_path, mixed, cond="B")
    assert b["n_tool_errors"] == 1 and b["tool_error_rate"] == 1.0


def test_two_error_results_of_one_call_count_once(tmp_path):
    # a duplicated user event: two is_error results for the same counted call must not push the rate above 1
    ev = [call(0, "Bash", {}), result(0, is_error=True), result(0, is_error=True)]
    r = run(tmp_path, ev, cond="B")
    assert r["n_calls"] == 1 and r["n_tool_errors"] == 1 and r["tool_error_rate"] == 1.0


def test_an_error_result_of_no_known_call_is_not_counted(tmp_path):
    ev = [call(0, "Bash", {}), result(0), result(9, is_error=True)]
    assert run(tmp_path, ev, cond="B")["n_tool_errors"] == 0


@pytest.mark.parametrize("tk", [
    task(**{"class": "curve"}, subtype=None),
    task(**{"class": "diagram"}, subtype=None),
    task(**{"class": "batch"}, subtype="band_series"),
])
def test_the_terms_table_tool_counts_as_the_expected_tool_for_curve_diagram_and_band_series(tmp_path, tk):
    ev = [call(0, P + "ts_terms_table_data", {"d_count": 3}), result(0)]
    r = run(tmp_path, ev, tk)
    assert r["expected_tool_used"] is True and r["first_expected_index"] == 0
    other = run(tmp_path, [call(0, P + "ts_compute_app", {}), result(0)], tk)
    assert other["expected_tool_used"] is True  # the compute app stays an expected tool
    assert run(tmp_path, [call(0, "Bash", {}), result(0)], tk)["expected_tool_used"] is False
