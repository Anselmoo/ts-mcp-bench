"""The fake claude's event stream compared event for event, with numbered uuids. Called in this process."""

from __future__ import annotations

import io
import json
import os

import pytest

from tsbench.run import fake_cli
from tsbench.tasks import load

SCRIPT_PROMPT = "Run this:\n```bash\necho PROBE_CTRL1 rc=$?\necho PROBE_NET rc=$?\n```\nThen say done."
USAGE = {"input_tokens": 100, "output_tokens": 50, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0}


def uid(i: int) -> str:
    return f"{i:012d}-aaaa-bbbb-cccc-dddddddddddd"


def stream(monkeypatch, capsys, argv, prompt, *, correct=True, no_json=False):
    ids = iter(range(1, 100))
    monkeypatch.setattr(fake_cli, "_new_uuid", lambda: uid(next(ids)))
    monkeypatch.setattr(fake_cli, "decide", lambda p, m, c: (correct, no_json))
    monkeypatch.setattr("sys.stdin", io.StringIO(prompt))
    assert fake_cli.main(argv) == 0
    return [json.loads(line) for line in capsys.readouterr().out.splitlines()]


def head(model="m", tools=(), servers=()):
    return [{"type": "system", "subtype": "ui_invalidate", "event": "ui.render", "uuid": uid(2), "session_id": uid(1)},
            {"type": "system", "subtype": "init", "cwd": os.getcwd(), "session_id": uid(1), "tools": list(tools),
             "mcp_servers": list(servers), "model": model, "permissionMode": "default", "apiKeySource": "none",
             "claude_code_version": "fake-0", "uuid": uid(3)}]


def assistant(n: int, content: list) -> dict:
    return {"type": "assistant", "session_id": uid(1), "uuid": uid(n),
            "message": {"id": "msg_" + uid(n + 1)[:12], "type": "message", "role": "assistant", "content": content}}


def user(n: int, tool_use_id: str, text: str) -> dict:
    return {"type": "user", "session_id": uid(1), "uuid": uid(n),
            "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": tool_use_id,
                                                     "content": text}]}}


def success(n: int, text: str, turns: int, cost=0.0, **extra) -> dict:
    return {"type": "result", "subtype": "success", **extra, "is_error": False, "result": text,
            "session_id": uid(1), "total_cost_usd": cost, "num_turns": turns, "duration_ms": 1,
            "duration_api_ms": 0, "usage": USAGE, "permission_denials": [], "terminal_reason": "completed",
            "uuid": uid(n)}


def tool_id(n: int) -> str:
    return "toolu_" + uid(n)[:12]


# ------------------------------------------------------------------ the sandbox script
def test_sandbox_script_in_condition_b(monkeypatch, capsys):
    events = stream(monkeypatch, capsys, ["--model", "m", "--tools", "Bash"], SCRIPT_PROMPT)
    use = {"type": "tool_use", "id": tool_id(4), "name": "Bash",
           "input": {"command": "echo PROBE_CTRL1 rc=$?\necho PROBE_NET rc=$?", "description": "run the probe script"}}
    assert events == [*head(tools=["Bash"]), assistant(5, [use]),
                      user(7, tool_id(4), "PROBE_CTRL1 rc=0\nPROBE_NET rc=1"),
                      assistant(8, [{"type": "text", "text": "done"}]), success(10, "done", 2)]


def test_sandbox_script_with_the_escape_switch(monkeypatch, capsys):
    monkeypatch.setenv("FAKE_PROBE_ESCAPE", "1")
    events = stream(monkeypatch, capsys, ["--model", "m", "--tools", "Bash"], SCRIPT_PROMPT)
    assert events[2]["message"]["content"][0]["input"] == {
        "command": "echo PROBE_CTRL1 rc=$?\necho PROBE_NET rc=$?", "description": "run the probe script",
        "dangerouslyDisableSandbox": True}


def test_sandbox_script_escape_switch_needs_the_value_1(monkeypatch, capsys):
    monkeypatch.setenv("FAKE_PROBE_ESCAPE", "yes")
    events = stream(monkeypatch, capsys, ["--model", "m", "--tools", "Bash"], SCRIPT_PROMPT)
    assert "dangerouslyDisableSandbox" not in events[2]["message"]["content"][0]["input"]


def test_a_script_without_the_control_marker_is_an_ordinary_prompt(monkeypatch, capsys):
    prompt = "Run this:\n```bash\necho hello\n```"
    events = stream(monkeypatch, capsys, ["--model", "m", "--tools", "Bash"], prompt)
    text = "I could not work this out; here is a prose answer without a parseable line."
    assert events == [*head(tools=["Bash"]), assistant(4, [{"type": "text", "text": text}]), success(6, text, 1)]


def test_the_sandbox_script_outside_condition_b_is_an_ordinary_prompt(monkeypatch, capsys):
    events = stream(monkeypatch, capsys, ["--model", "m"], SCRIPT_PROMPT)
    text = "I could not work this out; here is a prose answer without a parseable line."
    assert events == [*head(), assistant(4, [{"type": "text", "text": text}]), success(6, text, 1)]


# ------------------------------------------------------------------ a fit task in each condition
def fit_task() -> dict:
    return next(t for t in load("pilot") if t.get("answer_schema", "fit") == "fit" and not t["expect_out_of_scope"])


def test_fit_task_in_condition_a(monkeypatch, capsys):
    t = fit_task()
    events = stream(monkeypatch, capsys, ["--model", "m"], t["prompt"])
    ans = fake_cli.answer_for(t, True, "fit")
    text = f"Working it out: Dq = {ans['Dq']} cm^-1, B = {ans['B']} cm^-1.\n" + json.dumps(ans)
    assert events == [*head(), assistant(4, [{"type": "text", "text": text}]), success(6, text, 1)]


def test_fit_task_in_condition_b(monkeypatch, capsys):
    t = fit_task()
    events = stream(monkeypatch, capsys, ["--model", "m", "--tools", "Bash"], t["prompt"])
    ans = fake_cli.answer_for(t, True, "fit")
    summary = f"Dq = {ans['Dq']} cm^-1, B = {ans['B']} cm^-1"
    use = {"type": "tool_use", "id": tool_id(4), "name": "Bash",
           "input": {"command": f"python3 -c \"print('{summary}')\"", "description": "compute"}}
    text = f"Working it out: {summary}.\n" + json.dumps(ans)
    assert events == [*head(tools=["Bash"]), assistant(5, [use]), user(7, tool_id(4), summary),
                      assistant(8, [{"type": "text", "text": text}]), success(10, text, 2)]


def test_fit_task_in_condition_c_structured(monkeypatch, capsys):
    t = fit_task()
    argv = ["--model", "m", "--mcp-config", "x", "--json-schema", "{}", "--disallowedTools", "mcp__tanabesugano__x"]
    events = stream(monkeypatch, capsys, argv, t["prompt"])
    ans = fake_cli.answer_for(t, True, "fit")
    summary = f"Dq = {ans['Dq']} cm^-1, B = {ans['B']} cm^-1"
    use = {"type": "tool_use", "id": tool_id(4), "name": "mcp__tanabesugano__ts_fit_spectrum",
           "input": {"bands_cm1": t["bands_cm1"], "d_count": t["d_count"], "geometry": t["geometry"]}}
    so = {"type": "tool_use", "id": tool_id(8), "name": "StructuredOutput", "input": ans}
    tools = json.loads((fake_cli.FIXTURES / "init_C.json").read_text(encoding="utf-8"))["tools"]
    servers = [{"name": "tanabesugano", "status": "connected", "source": "dynamic"}]
    assert events == [*head(tools=[*tools, "StructuredOutput"], servers=servers), assistant(5, [use]),
                      user(7, tool_id(4), summary), assistant(9, [so]),
                      user(11, tool_id(8), "Structured output provided successfully"),
                      assistant(12, [{"type": "text", "text": json.dumps(ans)}]),
                      success(14, json.dumps(ans), 3, structured_output=ans)]


def test_structured_run_without_the_answer(monkeypatch, capsys):
    t = fit_task()
    events = stream(monkeypatch, capsys, ["--model", "m", "--json-schema", "{}"], t["prompt"], no_json=True)
    ans = fake_cli.answer_for(t, True, "fit")
    text = f"Working it out: Dq = {ans['Dq']} cm^-1, B = {ans['B']} cm^-1."
    assert events == [*head(tools=["StructuredOutput"]), assistant(4, [{"type": "text", "text": text}]),
                      success(6, text, 1)]


def test_the_cost_comes_from_the_environment(monkeypatch, capsys):
    monkeypatch.setenv("FAKE_COST_USD", "0.125")
    assert stream(monkeypatch, capsys, ["--model", "m"], "q")[-1]["total_cost_usd"] == 0.125
    monkeypatch.setenv("FAKE_COST_USD", "")
    assert stream(monkeypatch, capsys, ["--model", "m"], "q")[-1]["total_cost_usd"] == 0.0


def test_without_the_cost_variable_the_cost_is_zero(monkeypatch, capsys):
    monkeypatch.delenv("FAKE_COST_USD", raising=False)
    assert stream(monkeypatch, capsys, ["--model", "m"], "q")[-1]["total_cost_usd"] == 0.0


# ------------------------------------------------------------------ results that end a run early
def test_a_429_result(monkeypatch, capsys, tmp_path):
    state = tmp_path / "n"
    monkeypatch.setenv("FAKE_429_FIRST", "1")
    monkeypatch.setenv("FAKE_429_STATE", str(state))
    events = stream(monkeypatch, capsys, ["--model", "m"], "q")
    assert events[-1] == {"type": "result", "subtype": "success", "is_error": True, "api_error_status": 429,
                          "result": fake_cli.RATE_LIMIT_TEXT, "session_id": uid(1), "total_cost_usd": 0,
                          "num_turns": 1, "duration_ms": 1, "duration_api_ms": 0, "permission_denials": [],
                          "terminal_reason": "api_error", "uuid": uid(6)}
    assert state.read_text(encoding="utf-8") == "1"


def test_an_empty_429_state_file_counts_as_zero(monkeypatch, capsys, tmp_path):
    state = tmp_path / "n"
    state.write_text("", encoding="utf-8")
    monkeypatch.setenv("FAKE_429_FIRST", "1")
    monkeypatch.setenv("FAKE_429_STATE", str(state))
    assert stream(monkeypatch, capsys, ["--model", "m"], "q")[-1]["api_error_status"] == 429
    assert state.read_text(encoding="utf-8") == "1"


@pytest.mark.parametrize("first", ["", "0"])
def test_no_429_without_a_positive_count(monkeypatch, capsys, tmp_path, first):
    state = tmp_path / "n"
    monkeypatch.setenv("FAKE_429_FIRST", first)
    monkeypatch.setenv("FAKE_429_STATE", str(state))
    assert stream(monkeypatch, capsys, ["--model", "m"], "q")[-1]["is_error"] is False
    assert not state.exists()


def test_no_429_without_the_count_variable(monkeypatch, capsys, tmp_path):
    monkeypatch.delenv("FAKE_429_FIRST", raising=False)
    monkeypatch.setenv("FAKE_429_STATE", str(tmp_path / "n"))
    assert stream(monkeypatch, capsys, ["--model", "m"], "q")[-1]["is_error"] is False


@pytest.mark.parametrize("stop,reason", [("error_max_turns", "max_turns"),
                                         ("error_max_budget_usd", "budget_exhausted")])
def test_a_limit_result(monkeypatch, capsys, stop, reason):
    monkeypatch.setenv("FAKE_STOP", stop)
    monkeypatch.setenv("FAKE_COST_USD", "0.5")
    events = stream(monkeypatch, capsys, ["--model", "m"], "q")
    assert events[-1] == {"type": "result", "subtype": stop, "is_error": True, "session_id": uid(1),
                          "total_cost_usd": 0.5, "num_turns": 1, "duration_ms": 1, "duration_api_ms": 0,
                          "permission_denials": [], "terminal_reason": reason, "errors": ["stopped by a limit"],
                          "uuid": uid(6)}


# ------------------------------------------------------------------ the deterministic decision
def test_decide_follows_the_digest_bytes():
    seen = set()
    for i in range(400):
        prompt = f"prompt {i}"
        for cond in ("A", "B", "C"):
            d = fake_cli._digest(prompt, "m", cond)
            u = int.from_bytes(d[:8], "big") / 2**64
            no_json = int.from_bytes(d[8:12], "big") % 20 == 0
            assert fake_cli.decide(prompt, "m", cond) == (u < fake_cli.RATES[cond], no_json)
            seen.add(no_json)
    assert seen == {True, False}


# ------------------------------------------------------------------ answers
def test_answer_for_the_fit_schema_on_another_task_is_empty():
    t = next(t for t in load("pilot") if t.get("answer_schema", "fit") != "fit")
    assert fake_cli.answer_for(t, True) == {"Dq": None, "B": None, "C": None, "out_of_scope": False,
                                            "reason": "fake answer in the wrong schema"}


def test_answer_for_a_task_without_a_schema_is_a_fit_answer():
    t = dict(fit_task())
    t.pop("answer_schema", None)
    assert fake_cli.answer_for(t, True)["reason"] == "fake answer"


def test_wrong_out_of_scope_answer():
    t = next(t for t in load("pilot") if t.get("answer_schema", "fit") == "fit" and t["expect_out_of_scope"])
    assert fake_cli.answer_for(t, False) == {"Dq": 1000.0, "B": 700.0, "C": None, "out_of_scope": False,
                                             "reason": "fake wrong answer"}


def test_fit_answer_keeps_c_only_when_required():
    for t in load("pilot"):
        if t.get("answer_schema", "fit") == "fit" and not t["expect_out_of_scope"]:
            ans = fake_cli.answer_for(t, True)
            assert ans["C"] == (t["reference"]["C"] if "C" in t["required"] else None)
