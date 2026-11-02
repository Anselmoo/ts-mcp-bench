"""Read stream-json transcripts and pull the final JSON answer out of the result text (docs/methods.md, sections 2
and 3)."""
from __future__ import annotations

import functools
import hashlib
import io
import json
import math
import re
from dataclasses import dataclass, field

from tsbench.core import resource

__all__ = ["NUMBER", "RESCUE_SUBTYPES", "STRUCTURED_TOOL", "Transcript", "curve_answer", "final_answer",
           "is_progress_line", "read_transcript", "rescue_stop_reason", "rescue_structured_output"]

NUMBER = re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?")
_PROGRESS = re.compile(r'"subtype"\s*:\s*"thinking_tokens"')
_PROGRESS_MAX = 2000  # characters; a longer line is never a progress line
_REQUIRED_KEYS = ("Dq", "B", "out_of_scope")
STRUCTURED_TOOL = "StructuredOutput"  # same as tsbench.conditions.STRUCTURED_TOOL (scoring does not import run)


@dataclass
class Transcript:
    """Parsed stream-json transcript. Missing pieces are None or empty, never an exception."""

    init: dict | None = None
    result: dict | None = None
    assistant_texts: list[str] = field(default_factory=list)
    tool_uses: list[dict] = field(default_factory=list)  # {"name", "input", "id"}
    tool_results: list[dict] = field(default_factory=list)  # {"tool_use_id", "content"} (content flattened to text)
    events: list[dict] = field(default_factory=list)
    n_bad_lines: int = 0
    sha256: str = ""  # of the file bytes, taken in the same read

    @property
    def result_text(self) -> str:
        text = (self.result or {}).get("result")
        return text if isinstance(text, str) else ""


def flatten_text(content) -> str:
    """Tool-result content is a string or a list of blocks; return the text of all of it. An image block is
    "[image]"."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(flatten_text(c) for c in content)
    if isinstance(content, dict):
        if content.get("type") == "image":  # base64 payload: not text the tool printed (as artifacts._result_text)
            return "[image]"
        if isinstance(content.get("text"), str):
            return content["text"]
        if "content" in content:
            return flatten_text(content["content"])
        return json.dumps(content, ensure_ascii=False)
    return str(content)


def is_progress_line(line: str) -> bool:
    """True for a complete `system` / `thinking_tokens` progress line of a stream. Such lines are 99.9 % of the
    events of a gateway transcript and no reader uses them, so they are dropped before `json.loads`. A line cut off
    in the middle (a killed run) does not end in `}`: it is not dropped, so it is counted as a bad line."""
    line = line.rstrip()
    return len(line) <= _PROGRESS_MAX and line.endswith("}") and _PROGRESS.search(line) is not None


def _blocks(event: dict) -> list:
    message = event.get("message")
    content = message.get("content") if isinstance(message, dict) else None
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    return content if isinstance(content, list) else []


def read_transcript(path) -> Transcript:
    """Read a transcript; lines that are not JSON objects (e.g. a truncated last line) are skipped and counted."""
    tr = Transcript()
    seen_ids: set[str] = set()
    with open(path, encoding="utf-8", errors="replace") as fh:
        data = bytes(fh.buffer.read())  # the raw bytes, for the hash; decoded below the way the text mode would
    tr.sha256 = hashlib.sha256(data).hexdigest()
    # StringIO splits on \n, \r and \r\n only, as a text-mode file does (str.splitlines would also split on U+2028)
    with io.StringIO(data.decode("utf-8", errors="replace"), newline=None) as fh:
        for line in fh:
            line = line.strip()
            if not line or is_progress_line(line):
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                tr.n_bad_lines += 1
                continue
            if not isinstance(event, dict):
                tr.n_bad_lines += 1
                continue
            tr.events.append(event)
            etype = event.get("type")
            if etype == "system" and event.get("subtype") == "init" and tr.init is None:
                tr.init = event
            elif etype == "result":
                tr.result = event
            elif etype == "assistant":
                for block in _blocks(event):
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") == "text" and isinstance(block.get("text"), str):
                        tr.assistant_texts.append(block["text"])
                    elif block.get("type") == "tool_use":
                        uid = block.get("id")
                        if isinstance(uid, str) and uid:  # a repeated event is one call; no id: never merged
                            if uid in seen_ids:
                                continue
                            seen_ids.add(uid)
                        tr.tool_uses.append(
                            {"name": block.get("name", ""), "input": block.get("input"), "id": block.get("id")}
                        )
            elif etype == "user":
                for block in _blocks(event):
                    if isinstance(block, dict) and block.get("type") == "tool_result":
                        tr.tool_results.append(
                            {"tool_use_id": block.get("tool_use_id"), "content": flatten_text(block.get("content"))}
                        )
    return tr


def _strip_decor(line: str) -> str:
    line = line.strip()
    if line.startswith("```"):
        line = line[3:]
        if line[:4].lower() == "json":
            line = line[4:]
    line = line.strip()
    if line.endswith("```"):
        line = line[:-3]
    return line.strip().strip("`").strip()


def _coerce_number(value):
    """None for null; a finite float for a number or numeric string; raises ValueError otherwise."""
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError("bool is not a number")
    if isinstance(value, (int, float)):
        try:
            out = float(value)
        except OverflowError:  # an integer of more than 308 digits
            raise ValueError("non-finite") from None
    elif isinstance(value, str) and NUMBER.fullmatch(value.strip()):
        out = float(value.strip())
    else:
        raise ValueError(f"not a number: {value!r}")
    if not math.isfinite(out):
        raise ValueError("non-finite")
    return out


def final_answer(text: str | None, structured=None) -> dict | None:
    """`structured` (the result event's `structured_output`) when it is a dict with the required keys and valid
    numbers; otherwise the fallback below.

    The last line of `text` that is a JSON object with the keys Dq, B and out_of_scope, else None.

    Code fences, backticks and surrounding whitespace are stripped. Dq, B and C become float or None
    (numeric strings are accepted). A candidate line whose Dq/B/C is neither null nor numeric is skipped
    rather than read as null, so garbage can never turn into an out-of-scope answer.
    """
    if isinstance(structured, dict) and all(k in structured for k in _REQUIRED_KEYS):
        try:
            nums = {k: _coerce_number(structured.get(k)) for k in ("Dq", "B", "C")}
            return {**nums, "out_of_scope": structured["out_of_scope"], "reason": structured.get("reason")}
        except ValueError:
            pass
    if not isinstance(text, str):
        return None
    for line in reversed(text.splitlines()):
        line = _strip_decor(line)
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict) or any(k not in obj for k in _REQUIRED_KEYS):
            continue
        try:
            nums = {k: _coerce_number(obj.get(k)) for k in ("Dq", "B", "C")}
        except ValueError:
            continue
        return {**nums, "out_of_scope": obj["out_of_scope"], "reason": obj.get("reason")}
    return None



def curve_answer(structured) -> dict | None:
    """The `curve` answer (`{"points": [{"dq_over_b", "term", "e_over_b"}, ...], "reason"}`) from the result event's
    `structured_output`, or None when it is not that shape. No text fallback: curve answers are structured only.

    Numbers become floats (numeric strings are accepted, as for the fit answer); a point whose numbers are not
    numbers makes the whole answer None. The number of points is NOT checked here (the scorer does that).
    """
    if not isinstance(structured, dict) or not isinstance(structured.get("points"), list):
        return None
    points = []
    for p in structured["points"]:
        if not isinstance(p, dict):
            return None
        try:
            x, e = _coerce_number(p.get("dq_over_b")), _coerce_number(p.get("e_over_b"))
        except ValueError:
            return None
        if x is None or e is None:
            return None
        term = p.get("term")
        points.append({"dq_over_b": x, "term": term if isinstance(term, str) else "", "e_over_b": e})
    return {"points": points, "reason": structured.get("reason")}


# ---------------------------------------------------------------- rescue of an answer given before a harness stop
RESCUE_SUBTYPES = ("error_max_turns", "error_max_budget_usd")
SCHEMAS_DIR = resource("schemas")  # package data, read through tsbench.core


def rescue_stop_reason(tr: Transcript) -> str | None:
    """Why the run has no usable `structured_output` and may be rescued: `error_max_turns`, `error_max_budget_usd` or
    `no_result` (no result event at all); None when the result event carries a `structured_output` or the run ended
    in some other way (an API error, a normal result without one)."""
    if tr.result is None:
        return "no_result"
    if isinstance(tr.result.get("structured_output"), dict):
        return None
    sub = tr.result.get("subtype")
    return sub if sub in RESCUE_SUBTYPES else None


@functools.cache
def _schema(schema_name: str) -> dict:
    """The answer schema, read once per process (rescue runs for every transcript that a limit stopped)."""
    return json.loads((SCHEMAS_DIR / f"{schema_name}.schema.json").read_text(encoding="utf-8"))


def rescue_structured_output(tr: Transcript, schema_name: str = "fit") -> dict | None:
    """The input of the LAST `StructuredOutput` tool call of the transcript that validates against the answer schema
    `src/tsbench/data/schemas/<schema_name>.schema.json`, else None. The CLI checks this schema itself when the
    call is accepted, but a run stopped by a limit has no result event to say so, so the check is repeated here.
    A call with an invalid input is skipped and an earlier valid one is taken."""
    from tsbench.core.schema import validate_instance

    schema = _schema(schema_name)
    for use in reversed(tr.tool_uses):
        inp = use.get("input")
        if use.get("name") == STRUCTURED_TOOL and isinstance(inp, dict) and not validate_instance(schema, inp):
            return inp
    return None
