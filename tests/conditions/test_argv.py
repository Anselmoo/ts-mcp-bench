"""Exact values of src/tsbench/conditions/argv.py."""
from __future__ import annotations

import json

import pytest

from tsbench import conditions as cond_mod
from tsbench.conditions import argv

HAIKU = "claude-haiku-5-5"


def test_validate_model_id_messages():
    assert argv.validate_model_id("claude-haiku-5-5") is None
    assert argv.validate_model_id("Sonnet") == "'Sonnet' is an alias; give the full model id (e.g. claude-haiku-5-5)"
    assert argv.validate_model_id("claude-haiku") == (
        "'claude-haiku' is not a full model id (needs a version suffix such as -5-5)")
    assert argv.validate_model_id("deepseek-v4-flash-0731", gateway=True) is None
    assert argv.validate_model_id("-bad name", gateway=True) == "'-bad name' is not a valid gateway model name"
    refusal = argv.validate_model_id("opus", gateway=True) or ""
    assert refusal.endswith("give the full model id (e.g. claude-haiku-5-5)")


@pytest.mark.parametrize("model", ["openai/gpt-oss-120b", "x/../../y", "../escape", "a\\b"])
def test_gateway_model_id_is_one_path_segment(model):
    """The id names a run folder: a slash would nest the transcript one level deeper and the scorer would skip it."""
    assert argv.validate_model_id(model, gateway=True) == f"{model!r} is not a valid gateway model name"


@pytest.mark.parametrize("model", ["gwdg-qwen3.5-397b", "qwen3.5-397b-a17b", "deepseek-v4-flash-0731", "m:1.5_b"])
def test_gateway_model_id_keeps_the_shipped_names(model):
    assert argv.validate_model_id(model, gateway=True) is None


def test_find_mcp_command_prefers_the_repo_venv_then_the_interpreters_dir(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    py_dir = tmp_path / "py"
    py_dir.mkdir()
    (py_dir / "python").write_text("", encoding="utf-8")
    monkeypatch.setattr(argv.sys, "executable", str(py_dir / "python"))
    assert argv.find_mcp_command(repo) is None
    (py_dir / "tanabesugano-mcp").write_text("", encoding="utf-8")
    assert argv.find_mcp_command(repo) == str(py_dir / "tanabesugano-mcp")
    (repo / ".venv" / "bin").mkdir(parents=True)
    (repo / ".venv" / "bin" / "tanabesugano-mcp").write_text("", encoding="utf-8")
    assert argv.find_mcp_command(repo) == str(repo / ".venv" / "bin" / "tanabesugano-mcp")
    assert argv.find_mcp_command(str(repo)) == str(repo / ".venv" / "bin" / "tanabesugano-mcp")  # ty: ignore[invalid-argument-type]


def test_render_ts_json_replaces_the_command_in_every_string(tmp_path):
    template = tmp_path / "t.json"
    template.write_text(json.dumps({"a": ["${TS_MCP_COMMAND}", {"b": "x ${TS_MCP_COMMAND} y"}, 3, None],
                                    "n": 1.5, "t": True}), encoding="utf-8")
    assert argv.render_ts_json("/bin/mcp", template) == {
        "a": ["/bin/mcp", {"b": "x /bin/mcp y"}, 3, None], "n": 1.5, "t": True}
    shipped = argv.render_ts_json("/abs/mcp")
    assert shipped["mcpServers"]["tanabesugano"]["command"] == "/abs/mcp"


def test_build_argv_takes_an_explicit_turn_limit_and_budget():
    cond = cond_mod.get("A")
    default = argv.build_argv(["claude"], cond, HAIKU, "low")
    assert default[default.index("--max-turns") + 1] == str(cond_mod.MAX_TURNS["A"])
    assert "--max-budget-usd" not in default
    explicit = argv.build_argv(["claude"], cond, HAIKU, "low", 2.5, max_turns=7)
    assert explicit[explicit.index("--max-turns") + 1] == "7"
    assert explicit[explicit.index("--max-budget-usd") + 1] == "2.5000"
    b = argv.build_argv(["claude"], cond_mod.get("B"), HAIKU, "low", settings_path="/s.json", max_turns=3)
    assert b[b.index("--max-turns") + 1] == "3"
    assert argv.run_id_of(HAIKU, "B", "low", "P-x-01", 2) == f"{HAIKU}/B/low/P-x-01-k2"


# ------------------------------------------------------------------ the endpoint of a gateway run
@pytest.mark.parametrize("value, expected", [
    ("http://localhost:4000", "http://localhost:4000"),
    ("http://localhost:4000/", "http://localhost:4000"),
    ("https://chat-ai.academiccloud.de/v1", "https://chat-ai.academiccloud.de"),
    ("http://user:secret@proxy.example:8080/v1?token=abc#x", "http://proxy.example:8080"),  # no secret is recorded
    ("http://[::1]:4000", "http://[::1]:4000"),
    (None, cond_mod.GATEWAY_URL), ("", cond_mod.GATEWAY_URL), ("not a url", cond_mod.GATEWAY_URL),
    ("http://[::1", cond_mod.GATEWAY_URL),  # urlsplit raises on an unclosed bracket
])
def test_gateway_base_url_keeps_scheme_host_and_port_only(value, expected):
    assert cond_mod.gateway_base_url(value) == expected


@pytest.mark.parametrize("url, label", [
    (None, "gateway"), (cond_mod.GATEWAY_URL, "gateway"),
    ("http://localhost:4000", "gateway localhost:4000"), ("https://proxy.example", "gateway proxy.example"),
])
def test_gateway_label_names_the_recorded_endpoint(url, label):
    assert cond_mod.gateway_label(url) == label
