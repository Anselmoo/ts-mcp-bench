"""Tests for the fake `claude` (tsbench.run.fake_cli), called in this process.

The runner starts the fake as a subprocess, so a coverage run of the runner tests does not see it. These tests call
`main` and the helpers directly, with the prompt on a replaced stdin and the events read back from stdout.
No network, no key, no real `claude`.
"""
from __future__ import annotations

import io
import json

import pytest

from tsbench.run import fake_cli
from tsbench.tasks import load

PILOT = load("pilot")


def task_of(schema: str, **match) -> dict:
    for t in PILOT:
        if t.get("answer_schema", "fit") == schema and all(t.get(k) == v for k, v in match.items()):
            return t
    raise LookupError(schema)


def fit_task() -> dict:
    return task_of("fit", expect_out_of_scope=False)


def call(monkeypatch, capsys, argv, prompt, *, correct=True, no_json=False):
    """Run `main` once. `decide` is fixed so that a test does not depend on the hash of the prompt."""
    monkeypatch.setattr(fake_cli, "decide", lambda p, m, c: (correct, no_json))
    monkeypatch.setattr("sys.stdin", io.StringIO(prompt))
    assert fake_cli.main(argv) == 0
    return [json.loads(line) for line in capsys.readouterr().out.splitlines()]


def of_type(events, kind):
    return [e for e in events if e["type"] == kind]


def tool_uses(events):
    return [b for e in of_type(events, "assistant") for b in e["message"]["content"] if b["type"] == "tool_use"]


def work_uses(events):
    """The tool calls other than the final StructuredOutput one."""
    return [b for b in tool_uses(events) if b["name"] != "StructuredOutput"]


def tool_results(events):
    return [e["message"]["content"][0]["content"] for e in of_type(events, "user")]


# ---------------------------------------------------------------- argv
def test_parse_argv_reads_values_flags_and_variadic_lists():
    argv = ["-p", "--model", "claude-x", "--tools", "Bash", "--disallowedTools", "A", "B", "--max-turns", "3",
            "--verbose", "--json-schema", "{}"]
    assert fake_cli.parse_argv(argv) == {
        "--model": "claude-x", "--tools": "Bash", "--disallowedTools": "A B", "--max-turns": "3",
        "--json-schema": "{}"}


def test_parse_argv_takes_the_next_argument_as_the_value_even_if_it_looks_like_an_option():
    assert fake_cli.parse_argv(["--model", "--tools", "Bash"]) == {"--model": "--tools"}


def test_parse_argv_ignores_a_value_option_without_a_value():
    assert fake_cli.parse_argv(["--model"]) == {}


def test_condition_of_follows_the_flags():
    assert fake_cli.condition_of({"--mcp-config": "x.json", "--tools": "Bash"}) == "C"
    assert fake_cli.condition_of({"--tools": "Bash"}) == "B"
    assert fake_cli.condition_of({"--tools": ""}) == "A"
    assert fake_cli.condition_of({}) == "A"


# ---------------------------------------------------------------- decide, find_task
def test_decide_is_deterministic_and_follows_the_seed(monkeypatch):
    first = fake_cli.decide("prompt", "m", "A")
    assert fake_cli.decide("prompt", "m", "A") == first
    outcomes = set()
    for seed in range(40):
        monkeypatch.setenv("FAKE_SEED", str(seed))
        outcomes.add(fake_cli.decide("prompt", "m", "A")[0])
    assert outcomes == {True, False}


def test_decide_correct_rate_rises_from_a_to_c():
    n = 400
    hits = {c: sum(fake_cli.decide(f"p{i}", "m", c)[0] for i in range(n)) for c in "ABC"}
    assert hits["A"] < hits["B"] < hits["C"]
    assert abs(hits["C"] / n - fake_cli.RATES["C"]) < 0.08


def test_find_task_matches_the_exact_prompt_and_a_prompt_inside_a_longer_text():
    t = fit_task()
    assert fake_cli.find_task("  " + t["prompt"] + "\n")["id"] == t["id"]
    assert fake_cli.find_task("Preamble.\n" + t["prompt"] + "\nPostscript.")["id"] == t["id"]
    assert fake_cli.find_task("a question about something else") is None


# ---------------------------------------------------------------- schema_of
def test_schema_of_reads_the_requested_shape():
    def schema(props):
        return fake_cli.schema_of({"--json-schema": json.dumps({"properties": {k: {} for k in props}})})

    assert fake_cli.schema_of({}) is None
    assert schema(["image_path", "points"]) == "diagram"
    assert schema(["points"]) == "curve"
    assert schema(["values"]) == "batch"
    assert schema(["nodes", "edges"]) == "pairing"
    assert schema(["Dq", "B"]) == "fit"


@pytest.mark.parametrize("raw", ["not json", "[1, 2]"])
def test_schema_of_falls_back_to_fit_for_an_unreadable_schema(raw):
    assert fake_cli.schema_of({"--json-schema": raw}) == "fit"


# ---------------------------------------------------------------- answers
def test_curve_answer_scales_a_wrong_answer_by_a_quarter():
    task = {"reference_curve": [{"dq_over_b": 1.0, "term": "T1", "e_over_b": 10.0},
                                {"dq_over_b": 2.0, "term": "T2", "e_over_b": 20.0}]}
    good = fake_cli.curve_answer_for(task, True)
    bad = fake_cli.curve_answer_for(task, False)
    assert good == {"points": [{"dq_over_b": 1.0, "term": "T1", "e_over_b": 10.0},
                               {"dq_over_b": 2.0, "term": "T2", "e_over_b": 20.0}], "reason": "fake answer"}
    assert [p["e_over_b"] for p in bad["points"]] == [12.5, 25.0]
    assert fake_cli.curve_answer_for({}, True)["points"] == []


def test_batch_answer_spoils_every_second_item_of_a_wrong_answer():
    task = {"reference": {"values": [{"input": 1, "result": 10.0}, {"input": 2, "result": 20.0},
                                     {"input": 3, "result": None}, {"input": 4, "result": 40.0},
                                     {"input": 5, "result": 50.0}]}}
    good = fake_cli.batch_answer_for(task, True)["values"]
    bad = fake_cli.batch_answer_for(task, False)["values"]
    assert [v["result"] for v in good] == [10.0, 20.0, None, 40.0, 50.0]
    assert [v["result"] for v in bad] == [11.0, 20.0, None, 40.0, 55.0]  # items 0 and 4 change; item 2 has no result
    assert fake_cli.batch_answer_for({}, True) == {"values": [], "reason": "fake answer"}


def test_pairing_answer_drops_the_last_edge_and_miscounts_the_first_node():
    task = {"reference": {"nodes": [{"term": "a", "count": 2}, {"term": "b", "count": 1}],
                          "edges": [{"x": 1}, {"x": 2}]}}
    good = fake_cli.pairing_answer_for(task, True)
    bad = fake_cli.pairing_answer_for(task, False)
    assert good["nodes"] == task["reference"]["nodes"] and good["edges"] == task["reference"]["edges"]
    assert bad["nodes"] == [{"term": "a", "count": 3}, {"term": "b", "count": 1}]
    assert bad["edges"] == [{"x": 1}]
    assert task["reference"]["nodes"][0]["count"] == 2  # the reference itself is not changed
    assert fake_cli.pairing_answer_for({"reference": {"nodes": [], "edges": []}}, False)["nodes"] == []


def test_diagram_answer_scales_the_levels_above_the_ground_level():
    task = {"reference": {"grid": [0.5, 1.5], "levels": [[0.0, 8.0], [0.0, 16.0]], "labels": [["A", "B"], ["A", "B"]]}}
    good = fake_cli.diagram_answer_for(task, True)
    bad = fake_cli.diagram_answer_for(task, False)
    assert good["points"] == [
        {"dq_over_b": 0.5, "levels": [{"term": "A", "e_over_b": 0.0}, {"term": "B", "e_over_b": 8.0}]},
        {"dq_over_b": 1.5, "levels": [{"term": "A", "e_over_b": 0.0}, {"term": "B", "e_over_b": 16.0}]}]
    assert [lv["e_over_b"] for lv in bad["points"][1]["levels"]] == [0.0, 20.0]
    assert good["image_path"] is None and good["image_sha256"] is None


def test_save_diagram_image_writes_a_png_and_reports_its_hash(tmp_path, monkeypatch):
    import hashlib

    monkeypatch.chdir(tmp_path)
    ans = {"image_path": None, "image_sha256": None}
    fake_cli.save_diagram_image(ans)
    png = tmp_path / "diagram.png"
    assert png.read_bytes() == fake_cli.TINY_PNG
    assert png.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    assert ans == {"image_path": str(png), "image_sha256": hashlib.sha256(fake_cli.TINY_PNG).hexdigest()}


def test_save_diagram_image_leaves_the_answer_alone_when_the_write_fails(tmp_path, monkeypatch):
    def refuse(self, data):
        raise OSError("read-only")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(fake_cli.pathlib.Path, "write_bytes", refuse)
    ans = {"image_path": None, "image_sha256": None}
    fake_cli.save_diagram_image(ans)
    assert ans == {"image_path": None, "image_sha256": None}


def test_answer_for_a_fit_task_is_the_reference_or_fifteen_percent_off():
    t = fit_task()
    good = fake_cli.answer_for(t, True)
    bad = fake_cli.answer_for(t, False)
    assert (good["Dq"], good["B"]) == (t["reference"]["Dq"], t["reference"]["B"])
    assert good["C"] == (t["reference"]["C"] if "C" in t["required"] else None)
    assert bad["Dq"] == round(t["reference"]["Dq"] * 1.15, 2)
    assert good["out_of_scope"] is False


def test_answer_for_an_out_of_scope_task_declines_when_correct():
    t = task_of("fit", expect_out_of_scope=True)
    good = fake_cli.answer_for(t, True)
    assert good == {"Dq": None, "B": None, "C": None, "out_of_scope": True, "reason": "outside the ligand-field model"}
    bad = fake_cli.answer_for(t, False)
    assert (bad["Dq"], bad["B"], bad["out_of_scope"]) == (1000.0, 700.0, False)


def test_answer_for_a_fit_schema_on_a_non_fit_task_is_wrong_by_construction():
    ans = fake_cli.answer_for(task_of("curve"), True)
    assert ans["Dq"] is None and ans["B"] is None and ans["out_of_scope"] is False
    assert ans["reason"] == "fake answer in the wrong schema"


def test_answer_for_follows_the_schema_argument_over_the_task():
    t = task_of("curve")
    assert fake_cli.answer_for(t, True, "curve") == fake_cli.curve_answer_for(t, True)
    assert fake_cli.answer_for(t, True, "batch") == fake_cli.batch_answer_for(t, True)
    assert fake_cli.answer_for(t, True, "pairing") == fake_cli.pairing_answer_for(t, True)
    assert fake_cli.answer_for(t, True, "diagram") == fake_cli.diagram_answer_for(t, True)


# ---------------------------------------------------------------- events
def test_event_shapes():
    a = fake_cli.assistant_event("s1", [{"type": "text", "text": "hi"}])
    assert a["type"] == "assistant" and a["session_id"] == "s1"
    assert a["message"]["role"] == "assistant" and a["message"]["id"].startswith("msg_")
    assert a["message"]["content"] == [{"type": "text", "text": "hi"}]
    u = fake_cli.user_event("s1", "toolu_1", "out")
    assert u["message"]["content"] == [{"type": "tool_result", "tool_use_id": "toolu_1", "content": "out"}]
    assert a["uuid"] != fake_cli.assistant_event("s1", [])["uuid"]


def test_emit_writes_one_json_line(capsys):
    fake_cli.emit({"a": 1})
    assert capsys.readouterr().out == '{"a": 1}\n'


def test_emit_exits_quietly_when_the_runner_closed_the_pipe(monkeypatch):
    class Closed:
        def write(self, text):
            raise BrokenPipeError

        def flush(self):
            pass

    codes = []

    def fake_exit(code):
        codes.append(code)
        raise SystemExit(code)

    monkeypatch.setattr("sys.stdout", Closed())
    monkeypatch.setattr(fake_cli.os, "_exit", fake_exit)
    with pytest.raises(SystemExit):
        fake_cli.emit({"a": 1})
    assert codes == [0]


# ---------------------------------------------------------------- probe_markers
SCRIPT = "echo PROBE_CTRL1 PROBE_HEREDOC PROBE_NUMPY PROBE_KEYENV PROBE_PATHS PROBE_NET PROBE_PIP PROBE_NET"


def test_probe_markers_pass_by_default_and_keep_each_marker_once():
    assert fake_cli.probe_markers(SCRIPT) == [
        "PROBE_CTRL1 rc=0", "PROBE_HEREDOC rc=0", "PROBE_NUMPY rc=0", "PROBE_KEYENV rc=0", "PROBE_PATHS rc=0",
        "PROBE_NET rc=1", "PROBE_PIP rc=1"]


def test_probe_markers_leak_flips_each_kind_the_right_way(monkeypatch):
    monkeypatch.setenv("FAKE_PROBE_LEAK", "NET,KEYENV,,")
    out = fake_cli.probe_markers(SCRIPT)
    assert "PROBE_NET rc=0" in out  # a must-fail marker leaks: rc 0
    assert "PROBE_KEYENV rc=1" in out  # a must-be-zero marker leaks: rc 1
    assert "PROBE_PIP rc=1" in out and "PROBE_PATHS rc=0" in out


def test_probe_markers_without_the_stack_fail_only_numpy(monkeypatch):
    monkeypatch.setenv("FAKE_PROBE_NO_STACK", "1")
    out = fake_cli.probe_markers(SCRIPT)
    assert "PROBE_NUMPY rc=1" in out and "PROBE_CTRL1 rc=0" in out


def test_probe_markers_with_a_broken_bash_fail_every_positive_control(monkeypatch):
    monkeypatch.setenv("FAKE_PROBE_BASH_FAIL", "1")
    out = fake_cli.probe_markers(SCRIPT)
    for name in ("CTRL1", "HEREDOC", "NUMPY", "KEYENV", "PATHS"):
        assert f"PROBE_{name} rc=1" in out
    assert "PROBE_NET rc=1" in out


# ---------------------------------------------------------------- rate limit
def test_rate_limited_now_counts_calls_in_the_state_file(monkeypatch, tmp_path):
    state = tmp_path / "state"
    monkeypatch.setenv("FAKE_429_FIRST", "2")
    monkeypatch.setenv("FAKE_429_STATE", str(state))
    assert [fake_cli._rate_limited_now() for _ in range(4)] == [True, True, False, False]
    assert state.read_text(encoding="utf-8") == "4"


def test_rate_limited_now_is_off_without_a_count_or_a_state_file(monkeypatch, tmp_path):
    assert fake_cli._rate_limited_now() is False
    monkeypatch.setenv("FAKE_429_FIRST", "3")
    assert fake_cli._rate_limited_now() is False  # no state file named
    monkeypatch.setenv("FAKE_429_STATE", str(tmp_path / "s"))
    monkeypatch.setenv("FAKE_429_FIRST", "0")
    assert fake_cli._rate_limited_now() is False


# ---------------------------------------------------------------- main: the conversation
def test_main_with_an_unknown_prompt_gives_prose_and_a_success_result(monkeypatch, capsys):
    events = call(monkeypatch, capsys, ["-p", "--model", "claude-haiku-5-5"], "nothing the fake knows")
    assert [e["type"] for e in events] == ["system", "system", "assistant", "result"]
    assert events[0]["subtype"] == "ui_invalidate" and events[1]["subtype"] == "init"
    init = events[1]
    assert (init["model"], init["tools"], init["mcp_servers"]) == ("claude-haiku-5-5", [], [])
    assert init["claude_code_version"] == fake_cli.FAKE_VERSION
    assert events[2]["message"]["content"][0]["text"].startswith("I could not work this out")
    res = events[3]
    assert (res["subtype"], res["is_error"], res["num_turns"], res["total_cost_usd"]) == ("success", False, 1, 0.0)
    assert res["result"] == events[2]["message"]["content"][0]["text"]
    assert res["usage"]["input_tokens"] == 100 and "structured_output" not in res


def test_main_condition_a_ends_its_text_with_the_json_answer(monkeypatch, capsys):
    t = fit_task()
    events = call(monkeypatch, capsys, ["--model", "m"], t["prompt"])
    assert tool_uses(events) == []
    text = of_type(events, "assistant")[0]["message"]["content"][0]["text"]
    summary, last_line = text.split("\n")
    assert summary == f"Working it out: Dq = {t['reference']['Dq']} cm^-1, B = {t['reference']['B']} cm^-1."
    assert json.loads(last_line)["Dq"] == t["reference"]["Dq"]


def test_main_condition_a_can_leave_the_json_line_out(monkeypatch, capsys):
    events = call(monkeypatch, capsys, ["--model", "m"], fit_task()["prompt"], no_json=True)
    text = of_type(events, "assistant")[0]["message"]["content"][0]["text"]
    assert "\n" not in text and text.startswith("Working it out: Dq = ")


def test_main_out_of_scope_summary_says_there_is_no_reliable_fit(monkeypatch, capsys):
    t = task_of("fit", expect_out_of_scope=True)
    events = call(monkeypatch, capsys, ["--model", "m"], t["prompt"])
    text = of_type(events, "assistant")[0]["message"]["content"][0]["text"]
    assert text.startswith("Working it out: no reliable Dq/B within the model.")


def test_main_condition_b_runs_a_bash_call_and_takes_two_turns(monkeypatch, capsys):
    t = fit_task()
    events = call(monkeypatch, capsys, ["--model", "m", "--tools", "Bash"], t["prompt"])
    assert events[1]["tools"] == ["Bash"] and events[1]["mcp_servers"] == []
    (use,) = tool_uses(events)
    assert use["name"] == "Bash" and use["input"]["description"] == "compute"
    assert f"Dq = {t['reference']['Dq']} cm^-1" in use["input"]["command"]
    result = of_type(events, "user")[0]["message"]["content"][0]
    assert result["tool_use_id"] == use["id"] and result["content"].startswith("Dq = ")
    assert of_type(events, "result")[0]["num_turns"] == 2


def test_main_condition_c_calls_the_fit_tool_and_hides_blocked_tools(monkeypatch, capsys):
    t = fit_task()
    argv = ["--model", "m", "--mcp-config", "x.json", "--disallowedTools", "ts_supported_configs"]
    events = call(monkeypatch, capsys, argv, t["prompt"])
    init = events[1]
    assert init["mcp_servers"] == [{"name": "tanabesugano", "status": "connected", "source": "dynamic"}]
    assert init["tools"] and "ts_supported_configs" not in init["tools"]
    (use,) = tool_uses(events)
    assert use["name"] == "mcp__tanabesugano__ts_fit_spectrum"
    assert use["input"] == {"bands_cm1": t["bands_cm1"], "d_count": t["d_count"], "geometry": t["geometry"]}


def schema_arg(*props):
    return json.dumps({"type": "object", "properties": {p: {} for p in props}})


def test_main_condition_c_curve_and_diagram_use_the_terms_table_tool(monkeypatch, capsys, tmp_path):
    monkeypatch.chdir(tmp_path)
    for _schema, task, props in (("curve", task_of("curve"), ("points",)),
                                 ("diagram", task_of("diagram"), ("points", "image_path"))):
        argv = ["--model", "m", "--mcp-config", "x.json", "--json-schema", schema_arg(*props)]
        events = call(monkeypatch, capsys, argv, task["prompt"])
        (use,) = work_uses(events)
        assert use["name"] == "mcp__tanabesugano__ts_terms_table_data"
        assert use["input"] == {"d_count": task["d_count"]}


def test_main_condition_c_batch_picks_the_app_by_subtype(monkeypatch, capsys):
    for subtype, name in (("crossover_series", "ts_spin_crossover_app"), ("band_series", "ts_compute_app")):
        task = task_of("batch", subtype=subtype)
        argv = ["--model", "m", "--mcp-config", "x.json", "--json-schema", schema_arg("values")]
        (use,) = work_uses(call(monkeypatch, capsys, argv, task["prompt"]))
        assert use["name"] == f"mcp__tanabesugano__{name}"
        assert use["input"]["d_count"] == task["d_count"]
        assert all(use["input"][k] == v for k, v in (task.get("params") or {}).items())


def test_main_condition_c_pairing_asks_for_d5_terms(monkeypatch, capsys):
    task = task_of("pairing")
    argv = ["--model", "m", "--mcp-config", "x.json", "--json-schema", schema_arg("nodes", "edges")]
    events = call(monkeypatch, capsys, argv, task["prompt"])
    (use,) = work_uses(events)
    assert (use["name"], use["input"]) == ("mcp__tanabesugano__ts_terms_table_data", {"d_count": 5})
    ref = task["reference"]
    assert tool_results(events)[0] == f"{len(ref['nodes'])} term nodes, {len(ref['edges'])} shared-term edges"


def test_main_structured_run_answers_through_structured_output(monkeypatch, capsys):
    t = fit_task()
    events = call(monkeypatch, capsys, ["--model", "m", "--json-schema", schema_arg("Dq", "B")], t["prompt"])
    assert events[1]["tools"] == ["StructuredOutput"]
    (use,) = tool_uses(events)
    assert use["name"] == "StructuredOutput" and use["input"]["Dq"] == t["reference"]["Dq"]
    res = of_type(events, "result")[0]
    assert res["structured_output"] == use["input"]
    assert res["num_turns"] == 2
    assert json.loads(res["result"]) == use["input"]


def test_main_structured_run_can_fail_by_design_without_structured_output(monkeypatch, capsys):
    events = call(monkeypatch, capsys, ["--model", "m", "--json-schema", schema_arg("Dq")], fit_task()["prompt"],
                  no_json=True)
    assert tool_uses(events) == []
    res = of_type(events, "result")[0]
    assert "structured_output" not in res and res["num_turns"] == 1
    assert res["result"].startswith("Working it out:")


def test_main_diagram_answer_writes_the_image_next_to_the_cwd(monkeypatch, capsys, tmp_path):
    monkeypatch.chdir(tmp_path)
    task = task_of("diagram")
    events = call(monkeypatch, capsys, ["--model", "m", "--json-schema", schema_arg("points", "image_path")],
                  task["prompt"])
    ans = of_type(events, "result")[0]["structured_output"]
    assert ans["image_path"] == str(tmp_path / "diagram.png")
    assert (tmp_path / "diagram.png").read_bytes() == fake_cli.TINY_PNG
    summary = of_type(events, "assistant")[-1]["message"]["content"][0]["text"]
    assert summary == json.dumps(ans)
    assert len(ans["points"]) == len(task["reference"]["grid"])


def test_main_curve_and_batch_summaries_count_their_items(monkeypatch, capsys):
    curve = task_of("curve")
    events = call(monkeypatch, capsys, ["--model", "m", "--tools", "Bash", "--json-schema", schema_arg("points")],
                  curve["prompt"])
    assert tool_results(events)[0] == f"{len(curve['reference_curve'])} points on the term diagram"
    batch = task_of("batch", subtype="band_series")
    events = call(monkeypatch, capsys, ["--model", "m", "--tools", "Bash", "--json-schema", schema_arg("values")],
                  batch["prompt"])
    assert tool_results(events)[0] == f"{len(batch['reference']['values'])} results"


# ---------------------------------------------------------------- main: the sandbox probe
PROBE_PROMPT = "Run this:\n```bash\necho PROBE_CTRL1 rc=$?\necho PROBE_NET rc=$?\n```\nThen say done."


def test_main_answers_the_sandbox_probe_with_the_simulated_markers(monkeypatch, capsys):
    events = call(monkeypatch, capsys, ["--model", "m", "--tools", "Bash"], PROBE_PROMPT)
    (use,) = tool_uses(events)
    assert use["name"] == "Bash" and "dangerouslyDisableSandbox" not in use["input"]
    assert use["input"]["command"] == "echo PROBE_CTRL1 rc=$?\necho PROBE_NET rc=$?"
    out = of_type(events, "user")[0]["message"]["content"][0]["content"]
    assert out == "PROBE_CTRL1 rc=0\nPROBE_NET rc=1"
    assert of_type(events, "assistant")[-1]["message"]["content"][0]["text"] == "done"
    assert of_type(events, "result")[0]["num_turns"] == 2


def test_main_probe_can_ask_to_leave_the_sandbox(monkeypatch, capsys):
    monkeypatch.setenv("FAKE_PROBE_ESCAPE", "1")
    (use,) = tool_uses(call(monkeypatch, capsys, ["--model", "m", "--tools", "Bash"], PROBE_PROMPT))
    assert use["input"]["dangerouslyDisableSandbox"] is True


def test_main_ignores_the_probe_script_outside_condition_b(monkeypatch, capsys):
    events = call(monkeypatch, capsys, ["--model", "m"], PROBE_PROMPT)
    assert tool_uses(events) == []
    assert of_type(events, "assistant")[0]["message"]["content"][0]["text"].startswith("I could not work")


# ---------------------------------------------------------------- main: the environment switches
def test_main_reports_the_cost_from_fake_cost_usd(monkeypatch, capsys):
    monkeypatch.setenv("FAKE_COST_USD", "0.25")
    events = call(monkeypatch, capsys, ["--model", "m"], "unknown")
    assert of_type(events, "result")[0]["total_cost_usd"] == 0.25


def test_main_bad_init_reports_another_model(monkeypatch, capsys):
    monkeypatch.setenv("FAKE_BAD_INIT", "1")
    events = call(monkeypatch, capsys, ["--model", "claude-haiku-5-5"], "unknown")
    assert events[1]["model"] == "claude-fake-9-9"


def test_main_defaults_the_model_name_without_the_flag(monkeypatch, capsys):
    assert call(monkeypatch, capsys, [], "unknown")[1]["model"] == "claude-fake-0-0"


def test_main_can_stop_before_the_result_event(monkeypatch, capsys):
    monkeypatch.setenv("FAKE_NO_RESULT", "1")
    events = call(monkeypatch, capsys, ["--model", "m"], "unknown")
    assert of_type(events, "result") == []
    assert events[-1]["type"] == "assistant"


def test_main_answers_with_a_429_for_the_first_calls_only(monkeypatch, capsys, tmp_path):
    monkeypatch.setenv("FAKE_429_FIRST", "1")
    monkeypatch.setenv("FAKE_429_STATE", str(tmp_path / "n"))
    first = of_type(call(monkeypatch, capsys, ["--model", "m"], "unknown"), "result")[0]
    assert (first["is_error"], first["api_error_status"], first["terminal_reason"]) == (True, 429, "api_error")
    assert first["result"] == fake_cli.RATE_LIMIT_TEXT
    second = of_type(call(monkeypatch, capsys, ["--model", "m"], "unknown"), "result")[0]
    assert second["is_error"] is False and second["terminal_reason"] == "completed"


def test_main_429_text_can_be_replaced(monkeypatch, capsys, tmp_path):
    monkeypatch.setenv("FAKE_429_FIRST", "1")
    monkeypatch.setenv("FAKE_429_STATE", str(tmp_path / "n"))
    monkeypatch.setenv("FAKE_429_TEXT", "Rate limit exceeded: user daily request limit reached (7 of 7).")
    res = of_type(call(monkeypatch, capsys, ["--model", "m"], "unknown"), "result")[0]
    assert res["result"] == "Rate limit exceeded: user daily request limit reached (7 of 7)."


@pytest.mark.parametrize(("stop", "reason"), [("error_max_turns", "max_turns"),
                                              ("error_max_budget_usd", "budget_exhausted")])
def test_main_stops_with_the_requested_limit(monkeypatch, capsys, stop, reason):
    monkeypatch.setenv("FAKE_STOP", stop)
    monkeypatch.setenv("FAKE_COST_USD", "0.5")
    t = fit_task()
    events = call(monkeypatch, capsys, ["--model", "m", "--json-schema", schema_arg("Dq")], t["prompt"])
    assert tool_uses(events)[0]["input"]["Dq"] == t["reference"]["Dq"]  # the answer was given first
    res = of_type(events, "result")[0]
    assert (res["subtype"], res["terminal_reason"], res["is_error"]) == (stop, reason, True)
    assert res["errors"] == ["stopped by a limit"] and res["total_cost_usd"] == 0.5
    assert "structured_output" not in res and res["num_turns"] == 2


def test_main_reads_argv_and_stdin_when_called_without_arguments(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["fake_cli", "--model", "claude-haiku-5-5"])
    monkeypatch.setattr("sys.stdin", io.StringIO("unknown"))
    assert fake_cli.main() == 0
    assert json.loads(capsys.readouterr().out.splitlines()[1])["model"] == "claude-haiku-5-5"


def test_new_uuid_is_a_fresh_uuid_string():
    import uuid

    first, second = fake_cli._new_uuid(), fake_cli._new_uuid()
    assert first != second
    assert str(uuid.UUID(first)) == first


def test_module_runs_as_a_script_and_exits_with_the_code_of_main(monkeypatch, capsys):
    import runpy
    import sys

    monkeypatch.setattr(sys, "argv", ["fake_cli", "-p", "--model", "claude-haiku-5-5", "--tools", ""])
    monkeypatch.setattr(sys, "stdin", io.StringIO("no known task in this prompt"))
    with pytest.warns(RuntimeWarning):
        with pytest.raises(SystemExit) as e:
            runpy.run_module("tsbench.run.fake_cli", run_name="__main__")
    assert e.value.code == 0
    events = [json.loads(ln) for ln in capsys.readouterr().out.splitlines() if ln.strip()]
    assert "init" in [e.get("subtype") for e in events] and events[-1]["type"] == "result"
