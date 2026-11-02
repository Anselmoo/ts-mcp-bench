"""Exact values of src/tsbench/conditions/__init__.py: the answer schemas, the error texts, the init check."""
from __future__ import annotations

import hashlib
import json
import pathlib
import re

import pytest

from tsbench import conditions as cond_mod

MODEL = "claude-haiku-5-5"
PREFIX = cond_mod.MCP_TOOL_PREFIX
SO = cond_mod.STRUCTURED_TOOL


def init(tools, servers=(), model=MODEL, **kw):
    return {"type": "system", "subtype": "init", "tools": list(tools), "mcp_servers": list(servers), "model": model,
            **kw}


def check(key, event, model=MODEL, disallowed=()):
    return cond_mod.check_init(cond_mod.get(key), event, model, disallowed)


@pytest.mark.parametrize("name", ["fit", "curve", "batch", "pairing", "diagram"])
def test_answer_schema_fields_are_computed_from_the_file(name):
    got = cond_mod.get_answer_schema(name)
    path = cond_mod.SCHEMAS_DIR / f"{name}.schema.json"
    schema = json.loads(path.read_text(encoding="utf-8"))
    compact = json.dumps(schema, separators=(",", ":"))
    assert got.name == name and got.path == path and got.schema == schema
    assert got.compact == compact and json.loads(got.compact) == schema
    assert got.sha256 == hashlib.sha256(compact.encode("utf-8")).hexdigest()
    assert "\n" not in got.compact
    assert cond_mod.ANSWER_SCHEMAS[name] is got


def test_default_answer_schema_is_fit_and_its_aliases_agree():
    assert cond_mod.get_answer_schema() is cond_mod.get_answer_schema(None) is cond_mod.ANSWER_SCHEMAS["fit"]
    assert cond_mod.ANSWER_SCHEMA_SHA256 == cond_mod.ANSWER_SCHEMAS["fit"].sha256


def test_unknown_names_say_what_the_choices_are():
    with pytest.raises(ValueError) as e:
        cond_mod.get("D")
    assert str(e.value) == "unknown condition 'D'; choose from ['A', 'B', 'C']"
    with pytest.raises(ValueError) as e:
        cond_mod.max_turns("D")
    assert str(e.value) == "unknown condition 'D'; choose from ['A', 'B', 'C']"
    with pytest.raises(ValueError) as e:
        cond_mod.get_answer_schema("nope")
    assert str(e.value) == "unknown answer schema 'nope'; choose from ['batch', 'curve', 'diagram', 'fit', 'pairing']"


def test_flags_without_their_file_name_the_condition():
    with pytest.raises(ValueError) as e:
        cond_mod.get("B").flags()
    assert str(e.value) == "condition B needs a sandbox settings file"
    with pytest.raises(ValueError) as e:
        cond_mod.get("C").flags()
    assert str(e.value) == "condition C needs an MCP config file"
    assert cond_mod.get("A").flags(disallowed=["X", "Y"])[:4] == ["--tools", "", "--disallowedTools", "X"]


# ------------------------------------------------------------------ check_init: every message
def test_check_init_not_an_init_event():
    expect = ["first event is not a system/init event"]
    assert check("A", {"type": "assistant"}) == expect
    assert check("A", {"type": "system", "subtype": "other"}) == expect
    assert check("A", {"type": "system"}) == expect
    assert check("A", "text") == expect  # type: ignore[arg-type]


def test_check_init_a_good_init_has_no_problems():
    assert check("A", init([SO])) == []
    assert check("B", init(["Bash", SO])) == []
    assert check("C", init([PREFIX + "ts_fit", SO], [{"name": "tanabesugano", "status": "connected"}])) == []


def test_check_init_without_lists_reports_each_and_goes_on():
    ev = {"type": "system", "subtype": "init", "model": MODEL, "tools": None, "mcp_servers": "x"}
    assert check("A", ev) == ["init has no tools list (got None)", "init has no mcp_servers list (got 'x')",
                              f"{SO} missing from init tools (the --json-schema flag did not take effect): []"]


def test_check_init_a_and_b_messages():
    assert check("A", init(["Bash", SO], [{"name": "s"}])) == [
        "A: tools must be [], got ['Bash']", "A: mcp_servers must be [], got [{'name': 's'}]"]
    assert check("B", init(["Read", SO], ["s"])) == ["B: tools must be ['Bash'], got ['Read']",
                                                      "B: mcp_servers must be [], got ['s']"]
    assert check("B", init(["Bash"], model="other")) == [
        f"{SO} missing from init tools (the --json-schema flag did not take effect): ['Bash']",
        f"model must be {MODEL!r}, init reports 'other'"]


def test_check_init_disallowed_tools_must_be_absent():
    ok = [{"name": "tanabesugano", "status": "connected"}]
    t = PREFIX + "ts_plot_png"
    assert check("C", init([PREFIX + "ts_fit", t, SO], ok), disallowed=[t]) == [
        f"C: tools that were disallowed are in the init tool list: [{t!r}]"]
    assert check("C", init([PREFIX + "ts_fit", SO], ok), disallowed=[t]) == []


def test_check_init_c_messages():
    assert check("C", init([SO])) == ["C: tool list is empty", "C: expected exactly one MCP server, got 0"]
    ok = [{"name": "tanabesugano", "status": "connected"}]
    assert check("C", init(["Bash", PREFIX + "x", SO], ok)) == [f"C: tools outside {PREFIX}*: ['Bash']"]
    assert check("C", init([PREFIX + "x", SO], ok + ok)) == ["C: expected exactly one MCP server, got 2"]
    assert check("C", init([PREFIX + "x", SO], [{"name": "other", "status": "pending"}])) == [
        "C: MCP server name must be 'tanabesugano', got 'other'",
        "C: MCP server status must be 'connected', got 'pending'"]
    assert check("C", init([PREFIX + "x", SO], ["not a dict"])) == [
        "C: MCP server name must be 'tanabesugano', got None", "C: MCP server status must be 'connected', got None"]
    assert check("C", init([PREFIX + "x", SO], [{"name": "tanabesugano"}])) == [
        "C: MCP server status must be 'connected', got None"]
    assert check("C", init([PREFIX + "x", SO], [{"status": "connected"}])) == [
        "C: MCP server name must be 'tanabesugano', got None"]
    assert check("C", init([5, SO], ok)) == [f"C: tools outside {PREFIX}*: [5]"]


@pytest.mark.parametrize("name", ["fit", "curve", "batch", "pairing", "diagram"])
def test_load_schema_gives_the_same_record_as_the_one_loaded_at_import(name):
    assert cond_mod._load_schema(name) == cond_mod.ANSWER_SCHEMAS[name]


LITELLM = pathlib.Path(__file__).resolve().parents[2] / "contrib" / "gateway" / "litellm.yaml"


def _litellm_aliases() -> dict[str, str]:
    """alias (`model_name`) -> native gateway id (`openai/<id>`) of the shipped LiteLLM config."""
    text = LITELLM.read_text(encoding="utf-8")
    return dict(re.findall(r"model_name:\s*(\S+)\s+litellm_params:\s+model:\s*openai/(\S+)", text))


def test_the_litellm_aliases_are_parsed():
    assert _litellm_aliases()["gwdg-llama-3.1-8b"] == "meta-llama-3.1-8b-instruct"
    assert len(_litellm_aliases()) == 8


@pytest.mark.parametrize("alias,native", sorted(_litellm_aliases().items()))
def test_a_litellm_alias_gets_the_rule_of_its_native_model(alias, native):
    """The operator passes the `gwdg-*` alias as --model through the proxy; the text-only rule must still apply."""
    assert cond_mod.disallowed_tools("C", alias, True) == cond_mod.disallowed_tools("C", native, True)
    expected = list(cond_mod.IMAGE_TOOLS) if native in cond_mod.TEXT_ONLY_GATEWAY_MODELS else []
    assert cond_mod.disallowed_tools("C", alias, True) == expected
    assert cond_mod.disallowed_tools("C", alias, False) == [] and cond_mod.disallowed_tools("B", alias, True) == []


def test_every_gateway_alias_names_a_text_only_native_model():
    assert set(cond_mod.GATEWAY_ALIASES.values()) <= cond_mod.TEXT_ONLY_GATEWAY_MODELS
    assert set(cond_mod.GATEWAY_ALIASES) <= set(_litellm_aliases())


def _ok_init(key):
    """An init event that satisfies exactly what `tools_expected(key)` says."""
    exp = cond_mod.tools_expected(key)
    if key == "C":
        tools = [exp["mcp_prefix"] + "ts_fit"]
        servers = [{"name": exp["mcp_servers"][0], "status": "connected"}]
    else:
        tools, servers = list(exp["tools"]), list(exp["mcp_servers"])
    return init([*tools, SO], servers)


@pytest.mark.parametrize("key", ["A", "B", "C"])
def test_check_init_accepts_what_tools_expected_says(key):
    assert check(key, _ok_init(key)) == []


def test_tools_expected_is_the_rule_check_init_enforces(monkeypatch):
    """One statement of the rule: change it and check_init and the plan's record follow."""
    from tsbench import plan

    monkeypatch.setitem(cond_mod.TOOLS_EXPECTED, "B", {"tools": ["Bash", "Read"], "mcp_servers": []})
    assert check("B", init(["Bash", "Read", SO])) == []
    assert check("B", init(["Bash", SO])) == ["B: tools must be ['Bash', 'Read'], got ['Bash']"]
    assert plan.tools_expected("B") == {"tools": ["Bash", "Read"], "mcp_servers": []}


def test_tools_expected_returns_a_copy_and_refuses_an_unknown_condition():
    cond_mod.tools_expected("B")["tools"].append("Read")
    assert cond_mod.tools_expected("B") == {"tools": ["Bash"], "mcp_servers": []}
    with pytest.raises(ValueError, match="unknown condition 'Z'"):
        cond_mod.tools_expected("Z")


def test_only_the_answer_schemas_table_and_the_fit_hash_are_exported():
    """Only the answer schemas table and the fit hash are exported; there are no `ANSWER_SCHEMA*` aliases of the `fit`
    schema."""
    left = sorted(n for n in ("ANSWER_SCHEMA", "ANSWER_SCHEMA_PATH", "ANSWER_SCHEMA_COMPACT") if hasattr(cond_mod, n))
    assert left == [] and cond_mod.ANSWER_SCHEMA_SHA256 == cond_mod.ANSWER_SCHEMAS["fit"].sha256
