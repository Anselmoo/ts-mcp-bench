"""The three benchmark conditions and the init-event check that guards them.

A: no tools at all.
(In every condition `StructuredOutput` is also present: see STRUCTURED_TOOL.)
B: the Bash tool only, inside Claude Code's sandbox (see `sandbox.py`).
C: no built-in tools, only the tanabesugano MCP server.

`check_init` compares the first stream-json event of a run (the `system`/`init` event)
with what the condition promises. Any mismatch aborts the cell: a run that silently had
the wrong tools would measure the wrong thing.
"""
from __future__ import annotations

import copy
import hashlib
import json
import pathlib
import urllib.parse
from dataclasses import dataclass

from tsbench.core import resource

MCP_SERVER_NAME = "tanabesugano"
MCP_TOOL_PREFIX = f"mcp__{MCP_SERVER_NAME}__"

# The answer is enforced with `--json-schema`; Claude Code then adds a built-in output tool to every condition.
# It is an output channel, not a capability, so check_init requires it and the A/B/C rules ignore it.
STRUCTURED_TOOL = "StructuredOutput"

# Turn limit per condition (`--max-turns`): the single source of truth; the plan records it per run.
# A answers in one turn; B has to write and debug code, so it gets the largest limit;
# C may need several tool calls for a diagram or a batch.
MAX_TURNS: dict[str, int] = {"A": 15, "B": 40, "C": 25}

# Tools whose result is an image. A model that takes text only makes the gateway answer HTTP 500 "is not a
# multimodal model" after such a result.
IMAGE_TOOLS = (f"{MCP_TOOL_PREFIX}ts_plot_png", f"{MCP_TOOL_PREFIX}ts_emit_png")
GATEWAY_URL = "https://chat-ai.academiccloud.de"  # the default gateway endpoint (Anthropic-compatible)


def gateway_base_url(value: str | None) -> str:
    """`scheme://host[:port]` of an `ANTHROPIC_BASE_URL`, or `GATEWAY_URL` when it is unset or not a URL. User,
    password, path and query are dropped, so that nothing secret is recorded."""
    try:
        parsed = urllib.parse.urlsplit(str(value or "").strip())
        host, port = parsed.hostname, parsed.port
    except ValueError:
        return GATEWAY_URL
    if parsed.scheme not in ("http", "https") or not host:
        return GATEWAY_URL
    host = f"[{host}]" if ":" in host else host
    return f"{parsed.scheme}://{host}" + (f":{port}" if port else "")


def gateway_label(url: str | None) -> str:
    """How a page names the endpoint of a gateway run: `gateway` for the default endpoint `GATEWAY_URL` (also when
    nothing was recorded), else `gateway <host[:port]>`, for example the local LiteLLM proxy of contrib/gateway."""
    base = gateway_base_url(url) if url else GATEWAY_URL
    if base == GATEWAY_URL:
        return "gateway"
    return "gateway " + base.split("://", 1)[1]


# Gateway models whose /v1/models `input` is ["text"] only.
TEXT_ONLY_GATEWAY_MODELS = frozenset({
    "deepseek-v4-flash-0731", "meta-llama-3.1-8b-instruct", "qwen3-coder-next", "qwen3-30b-a3b-instruct-2507",
    "qwen3.8-27b",
})
# The `gwdg-*` names that `contrib/gateway/litellm.yaml` exposes (what the operator passes as --model through the
# proxy) -> the native gateway id behind each one, for the text-only models of the set above.
GATEWAY_ALIASES: dict[str, str] = {
    "gwdg-llama-3.1-8b": "meta-llama-3.1-8b-instruct",
    "gwdg-qwen3-coder-next": "qwen3-coder-next",
    "gwdg-qwen3-30b-a3b-instruct": "qwen3-30b-a3b-instruct-2507",
    "gwdg-qwen3.8-27b": "qwen3.8-27b",
}

# What `check_init` demands per condition, as data: the single statement of the rule. The plan records it per run
# (`tools_expected`) and the runner checks the record still equals it.
TOOLS_EXPECTED: dict[str, dict] = {
    "A": {"tools": [], "mcp_servers": []},
    "B": {"tools": ["Bash"], "mcp_servers": []},
    "C": {"mcp_prefix": MCP_TOOL_PREFIX, "mcp_servers": [MCP_SERVER_NAME]},
}


def tools_expected(cond_key: str) -> dict:
    """A copy of what `check_init` demands of condition `cond_key`."""
    try:
        return copy.deepcopy(TOOLS_EXPECTED[cond_key])
    except KeyError:
        raise ValueError(f"unknown condition {cond_key!r}; choose from {sorted(TOOLS_EXPECTED)}") from None


def max_turns(cond_key: str) -> int:
    try:
        return MAX_TURNS[cond_key]
    except KeyError:
        raise ValueError(f"unknown condition {cond_key!r}; choose from {sorted(MAX_TURNS)}") from None


def disallowed_tools(cond_key: str, model: str, gateway: bool) -> list[str]:
    """Tools to pass to `--disallowedTools`: the image tools for condition C with a text-only gateway model, else [].
    The model may be a native gateway id or a `gwdg-*` alias of the LiteLLM proxy (`GATEWAY_ALIASES`)."""
    if cond_key == "C" and gateway and GATEWAY_ALIASES.get(model, model) in TEXT_ONLY_GATEWAY_MODELS:
        return list(IMAGE_TOOLS)
    return []


SCHEMAS_DIR = resource("schemas")


@dataclass(frozen=True)
class AnswerSchema:
    """One answer schema as it is passed to `--json-schema` (compact text) and pinned in the plan (its sha256)."""

    name: str
    path: pathlib.Path
    schema: dict
    compact: str
    sha256: str


def _load_schema(name: str) -> AnswerSchema:
    path = SCHEMAS_DIR / f"{name}.schema.json"
    schema = json.loads(path.read_text(encoding="utf-8"))
    compact = json.dumps(schema, separators=(",", ":"))
    return AnswerSchema(name, path, schema, compact, hashlib.sha256(compact.encode("utf-8")).hexdigest())


# `fit`: Dq / B / C / out_of_scope (the fit classes); `curve`: points on a term diagram (curve class);
# `batch`: one result per input value (batch class); `pairing`: term nodes and shared-term edges (pairing class);
# `diagram`: six levels at each of nine Dq/B points plus an optional image path and sha256 (diagram class).
# `get_answer_schema(record["answer_schema"])` is what reaches `--json-schema` (see Condition.flags).
DEFAULT_ANSWER_SCHEMA = "fit"
ANSWER_SCHEMAS: dict[str, AnswerSchema] = {n: _load_schema(n) for n in ("fit", "curve", "batch", "pairing", "diagram")}


def get_answer_schema(name: str | None = None) -> AnswerSchema:
    """The schema called `name` (None = the default, `fit`)."""
    try:
        return ANSWER_SCHEMAS[name or DEFAULT_ANSWER_SCHEMA]
    except KeyError:
        raise ValueError(f"unknown answer schema {name!r}; choose from {sorted(ANSWER_SCHEMAS)}") from None


# The sha256 of the `fit` schema: the plan pin `answer_schema_sha256`.
ANSWER_SCHEMA_SHA256: str = ANSWER_SCHEMAS["fit"].sha256


@dataclass(frozen=True)
class Condition:
    key: str
    label: str
    tools: str  # value of --tools ("" = none)
    uses_settings: bool = False  # B: sandbox settings file
    uses_mcp: bool = False  # C: rendered MCP config

    def flags(self, *, settings_path: str | None = None, mcp_config_path: str | None = None,
              answer_schema: str = DEFAULT_ANSWER_SCHEMA, disallowed: list[str] | tuple[str, ...] = ()) -> list[str]:
        """The condition-specific part of argv; `--json-schema <compact schema>` is always last."""
        out = ["--tools", self.tools]
        if self.uses_settings:
            if not settings_path:
                raise ValueError(f"condition {self.key} needs a sandbox settings file")
            # --allowedTools Bash: in -p mode a command Claude Code's permission parser cannot analyse
            # (e.g. a heredoc writing a script) is otherwise denied, so B could not write code.
            # The sandbox, not the prompt, confines B; the tools stay ["Bash"].
            out += ["--settings", settings_path, "--allowedTools", "Bash"]
        if self.uses_mcp:
            if not mcp_config_path:
                raise ValueError(f"condition {self.key} needs an MCP config file")
            out += ["--mcp-config", mcp_config_path, "--allowedTools", f"{MCP_TOOL_PREFIX}*"]
        if disallowed:
            out += ["--disallowedTools", *disallowed]
        return out + ["--json-schema", get_answer_schema(answer_schema).compact]


CONDITIONS: dict[str, Condition] = {
    "A": Condition("A", "no tools", tools=""),
    "B": Condition("B", "Bash in sandbox", tools="Bash", uses_settings=True),
    "C": Condition("C", "tanabesugano MCP", tools="", uses_mcp=True),
}


def get(key: str) -> Condition:
    try:
        return CONDITIONS[key]
    except KeyError:
        raise ValueError(f"unknown condition {key!r}; choose from {sorted(CONDITIONS)}") from None


def check_init(
    cond: Condition, init_event: dict, model: str, disallowed: list[str] | tuple[str, ...] = ()
) -> list[str]:
    """Return the mismatches between an init event and the condition (empty list = fine).

    `disallowed`: tools passed to `--disallowedTools`. They must be absent from the init tool list; the rest of the
    list is judged by the same rules, so a C init without `ts_plot_png` / `ts_emit_png` is fine."""
    problems: list[str] = []
    if not isinstance(init_event, dict) or init_event.get("type") != "system" or init_event.get("subtype") != "init":
        return ["first event is not a system/init event"]

    tools = init_event.get("tools")
    servers = init_event.get("mcp_servers")
    if not isinstance(tools, list):
        problems.append(f"init has no tools list (got {tools!r})")
        tools = []
    if not isinstance(servers, list):
        problems.append(f"init has no mcp_servers list (got {servers!r})")
        servers = []

    if STRUCTURED_TOOL not in tools:
        problems.append(
            f"{STRUCTURED_TOOL} missing from init tools (the --json-schema flag did not take effect): {tools!r}"
        )
    tools = [t for t in tools if t != STRUCTURED_TOOL]
    present = [t for t in disallowed if t in tools]
    if present:
        problems.append(f"{cond.key}: tools that were disallowed are in the init tool list: {present!r}")

    if cond.key not in TOOLS_EXPECTED:  # pragma: no cover - guarded by get()
        problems.append(f"unknown condition {cond.key!r}")
    else:
        exp = tools_expected(cond.key)
        if cond.key in ("A", "B"):
            if tools != exp["tools"]:
                problems.append(f"{cond.key}: tools must be {exp['tools']!r}, got {tools!r}")
            if servers != exp["mcp_servers"]:
                problems.append(f"{cond.key}: mcp_servers must be {exp['mcp_servers']!r}, got {servers!r}")
        else:
            prefix, (server_name,) = exp["mcp_prefix"], exp["mcp_servers"]
            if not tools:
                problems.append("C: tool list is empty")
            stray = [t for t in tools if not (isinstance(t, str) and t.startswith(prefix))]
            if stray:
                problems.append(f"C: tools outside {prefix}*: {stray!r}")
            if len(servers) != 1:
                problems.append(f"C: expected exactly one MCP server, got {len(servers)}")
            else:
                srv = servers[0] if isinstance(servers[0], dict) else {}
                if srv.get("name") != server_name:
                    problems.append(f"C: MCP server name must be {server_name!r}, got {srv.get('name')!r}")
                if srv.get("status") != "connected":
                    problems.append(f"C: MCP server status must be 'connected', got {srv.get('status')!r}")

    if init_event.get("model") != model:
        problems.append(f"model must be {model!r}, init reports {init_event.get('model')!r}")
    return problems
