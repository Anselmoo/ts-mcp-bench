"""Command lines and identifiers of the three conditions: model id rules, the claude argv, the MCP config, run ids.

Data only: nothing here runs a process. The runner (tsbench.run) and the plan builder (tsbench.plan) both use it.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

from tsbench import conditions as cond_mod
from tsbench.core import resource

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]

NEUTRAL_PROMPT = str(resource("prompts/neutral.txt"))
TS_JSON = resource("conditions/ts.json")
EFFORTS = ("low", "medium", "high", "xhigh", "max")
MODEL_RE = re.compile(r"^claude-(?:[a-z]+-)+\d+-\d+(?:-\d{8})?$|^claude-\d+-\d+-[a-z]+(?:-\d{8})?$")
GATEWAY_MODEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")  # no "/": the id is one run-folder name
BARE_ALIASES = {"haiku", "sonnet", "opus", "default", "best", "opusplan", "fast"}


def validate_model_id(model: str, gateway: bool = False) -> str | None:
    """None if fine, else the reason it is rejected."""
    if model.lower() in BARE_ALIASES:
        return f"{model!r} is an alias; give the full model id (e.g. claude-haiku-5-5)"
    if gateway:
        return None if GATEWAY_MODEL_RE.match(model) else f"{model!r} is not a valid gateway model name"
    if not MODEL_RE.match(model):
        return f"{model!r} is not a full model id (needs a version suffix such as -5-5)"
    return None


def find_mcp_command(repo: pathlib.Path = REPO_ROOT) -> str | None:
    for cand in (pathlib.Path(repo) / ".venv" / "bin" / "tanabesugano-mcp",
                 pathlib.Path(sys.executable).parent / "tanabesugano-mcp"):
        if cand.exists():
            return str(cand.absolute())
    return None


def render_ts_json(command: str, template: pathlib.Path = TS_JSON) -> dict:
    def sub(node):
        if isinstance(node, str):
            return node.replace("${TS_MCP_COMMAND}", command)
        if isinstance(node, list):
            return [sub(x) for x in node]
        if isinstance(node, dict):
            return {k: sub(v) for k, v in node.items()}
        return node

    return sub(json.loads(template.read_text(encoding="utf-8")))


def build_argv(claude_argv: list[str], cond: cond_mod.Condition, model: str, effort: str,
               per_call_usd: float | None = None, *,
               system_prompt_file: str = NEUTRAL_PROMPT, settings_path: str | None = None,
               mcp_config_path: str | None = None, max_turns: int | None = None,
               answer_schema: str = cond_mod.DEFAULT_ANSWER_SCHEMA,
               disallowed_tools: list[str] | tuple[str, ...] = ()) -> list[str]:
    """The full command line. The task prompt is NOT in it: it goes in on stdin. `--json-schema` is the schema
    of the record being run (`answer_schema`), not a global constant.

    `per_call_usd=None` (the default) passes no `--max-budget-usd`, so no call is cut by a cap. `max_turns=None` is
    the condition's limit (`conditions.MAX_TURNS`)."""
    turns = cond_mod.max_turns(cond.key) if max_turns is None else max_turns
    budget = [] if per_call_usd is None else ["--max-budget-usd", f"{per_call_usd:.4f}"]
    return list(claude_argv) + [
        "-p", "--bare", "--strict-mcp-config", "--no-session-persistence",
        "--output-format", "stream-json", "--verbose",
        "--system-prompt-file", system_prompt_file,
        "--max-turns", str(turns),
        *budget,
        "--effort", effort,
        "--model", model,
    ] + cond.flags(settings_path=settings_path, mcp_config_path=mcp_config_path, answer_schema=answer_schema,
                   disallowed=disallowed_tools)


def run_id_of(model: str, cond: str, effort: str, task_id: str, k: int) -> str:
    return f"{model}/{cond}/{effort}/{task_id}-k{k}"
