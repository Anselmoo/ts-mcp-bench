"""Blinded grader packets: the answer text only, with condition and model cues redacted, in shuffled order.

Redacted: MCP and TS-MCP tool names (prefixed or bare), tool-call, Bash and MCP words, the condition B cues (python,
numpy, scipy, sympy, matplotlib, script), the Claude names, and the model ids of the run set with every letter
word of them (llama, qwen, gpt, oss, ...) except generic ones (instruct, flash, meta, ...).
"""
from __future__ import annotations

import json
import pathlib
import random
import re

__all__ = ["REDACTED", "make_packets", "redact", "write_packets"]

REDACTED = "[redacted]"
# the tools of the TS-MCP server without their `ts_` prefix (`run/fake_cli_fixtures/init_C.json` lists them);
# `explain` and `nephelauxetic` are ordinary words and only redacted with their prefix
_BARE_TOOLS = (
    "compare_app",
    "compute_app",
    "compute_point",
    "correlation_diagram_app",
    "dashboard_app",
    "diagram_app",
    "emit_png",
    "fit_plot_app",
    "fit_script",
    "fit_spectrum",
    "orgel_diagram_app",
    "overlay_app",
    "oxidation_landscape_app",
    "plot_png",
    "plot_view",
    "ratio_fit_app",
    "reverse_fit_app",
    "spectrum_app",
    "spin_crossover_app",
    "supported_configs",
    "terms_table_data",
)
_PATTERNS = [
    re.compile(r"mcp__\S+"),
    re.compile(r"\bts_[a-z_]+\b"),
    re.compile(r"\btool[\s_-]*calls?\b", re.I),
    re.compile(r"\b(?:bash|mcp|tanabesugano)\b", re.I),
    re.compile(rf"\b(?:{'|'.join(_BARE_TOOLS)})\b", re.I),
    re.compile(r"\b(?:python|numpy|scipy|sympy|matplotlib|scripts?)\b", re.I),
    re.compile(r"\b(?:claude|anthropic|haiku|sonnet|opus)\b[\w.\-]*", re.I),
]
_LETTERS = re.compile(r"[A-Za-z]{3,}")
# words of model ids that name no family and are ordinary words in an answer
_GENERIC = frozenset({
    "base", "chat", "coder", "flash", "instruct", "large", "latest", "max", "meta", "mini", "next", "plus", "pro",
    "preview", "small", "turbo", "the", "thinking",
})


def _model_patterns(models) -> list[re.Pattern[str]]:
    """Patterns for the model ids and their family names (every letter word of an id: qwen, llama, gpt, oss, ...)."""
    names: set[str] = set()
    for model in models:
        model = str(model).strip()
        if model:
            names.add(model)
            names.update(t for t in _LETTERS.findall(model) if t.lower() not in _GENERIC)
    # longest first, so a full id is replaced as one piece
    return [re.compile(rf"\b{re.escape(n)}[\w.\-]*", re.I) for n in sorted(names, key=lambda n: (-len(n), n))]


def redact(text: str, models=()) -> str:
    """Replace the condition and model cues in `text`; `models` are the model ids of the run set."""
    for pat in [*_PATTERNS, *_model_patterns(models)]:
        text = pat.sub(REDACTED, text)
    return text


def make_packets(entries: list[dict], seed: int = 20261024) -> tuple[list[dict], dict]:
    """entries: dicts with path, model, condition, effort, k, task_id, prompt, answer_text.

    Returns (packets, key). Packets carry packet_id, task_id, prompt, answer_text only; the key maps
    packet_id -> {path, model, condition, effort, k}. Entries are sorted, shuffled with a seeded rng,
    and only then numbered, so a packet id carries no information about the cell.
    """
    entries = sorted(entries, key=lambda e: str(e["path"]))
    random.Random(seed).shuffle(entries)
    models = sorted({str(e["model"]) for e in entries})
    packets, key = [], {}
    for i, e in enumerate(entries, 1):
        pid = f"G{i:04d}"
        packets.append(
            {
                "packet_id": pid,
                "task_id": e["task_id"],
                "prompt": e["prompt"],
                "answer_text": redact(e["answer_text"], models),
            }
        )
        key[pid] = {k: e[k] for k in ("path", "model", "condition", "effort", "k")}
    return packets, key


def write_packets(entries: list[dict], out_dir, seed: int = 20261024) -> tuple[pathlib.Path, pathlib.Path]:
    out_dir = pathlib.Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    packets, key = make_packets(entries, seed)
    pj, kj = out_dir / "packets.jsonl", out_dir / "key.json"
    pj.write_text("".join(json.dumps(p, ensure_ascii=False) + "\n" for p in packets), encoding="utf-8")
    kj.write_text(json.dumps({"seed": seed, "key": key}, indent=1, ensure_ascii=False), encoding="utf-8")
    return pj, kj
