#!/usr/bin/env python3
"""Pre-check before any benchmark run: does each model of the endpoint return a real tool call?

Sends one OpenAI-style request with a single tool directly to the endpoint (no gateway).
A model that answers in prose instead of emitting `tool_calls` cannot serve the
MCP condition and is left out before the model list of a plan is fixed.

Usage: GWDG_API_KEY=... python3 smoke_tool_calling.py [model ...]
(GWDG_AI_API_KEY is accepted as an alias; GWDG_API_KEY wins if both are set.)
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request

BASE = "https://chat-ai.academiccloud.de/v1/chat/completions"
# The models of `GET /v1/models` of the endpoint; re-fetch the list before each use.
DEFAULT = ["deepseek-v4-flash-0731", "qwen3.8-27b", "qwen3.6-35b-a3b", "qwen3-omni-30b-a3b-instruct",
           "qwen3-coder-next", "glm-5.3-flash", "qwen3.5-397b-a17b", "gemma-4-31b-it",
           "meta-llama-3.1-8b-instruct", "qwen3-30b-a3b-instruct-2507"]
TOOL = {"type": "function", "function": {
    "name": "ts_terms_table_data",
    "description": "Term energies for a dN configuration at given Dq, B, C (cm-1).",
    "parameters": {"type": "object", "properties": {
        "d_count": {"type": "integer"}, "Dq": {"type": "number"},
        "B": {"type": "number"}, "C": {"type": "number"}},
        "required": ["d_count", "Dq", "B", "C"]}}}
PROMPT = "List the term energies for d8 at Dq=860, B=940, C=3850 cm-1. Use the tool."

def probe(model, key):
    body = {"model": model, "messages": [{"role": "user", "content": PROMPT}],
            "tools": [TOOL], "tool_choice": "auto", "temperature": 0}
    req = urllib.request.Request(BASE, json.dumps(body).encode(),
        {"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            msg = json.load(r)["choices"][0]["message"]
    except Exception as e:  # report, never hide
        return "ERROR", str(e)[:120]
    calls = msg.get("tool_calls") or []
    if calls:
        return "TOOL_CALL", calls[0]["function"]["arguments"][:120]
    return "PROSE_ONLY", (msg.get("content") or "")[:120]

if __name__ == "__main__":
    key = os.environ.get("GWDG_API_KEY") or os.environ.get("GWDG_AI_API_KEY") \
        or sys.exit("set GWDG_API_KEY (or GWDG_AI_API_KEY)")
    for m in sys.argv[1:] or DEFAULT:
        status, detail = probe(m, key)
        print(f"{status:11} {m:40} {detail}")
