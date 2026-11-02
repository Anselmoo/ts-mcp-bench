"""The context-overflow rule that the scorer and the runner share.

A run whose request outgrew the model's context window (or the gateway's request size) failed by its own doing: its
tool output or its prompt grew too large. That is a wrong answer, not an infrastructure failure, so the scorer counts it
and a resume does not sample it again. Only infrastructure errors stay not evaluable (HTTP 401, 403, 404, 408, 429 and
5xx); an HTTP 400 without overflow text keeps that treatment too.
"""
from __future__ import annotations

import re

__all__ = ["OVERFLOW_STATUSES", "OVERFLOW_TEXT", "is_context_overflow"]

OVERFLOW_STATUSES = (400, 413)
# What Claude Code, the Anthropic API, LiteLLM (contrib/gateway) and OpenAI-style servers write for such a request
OVERFLOW_TEXT = re.compile(
    r"context ?window|context[_ ]length|maximum context|prompt is too long|input is too long"
    r"|request[_ ]too[_ ]large|request entity too large|payload too large", re.IGNORECASE)
_TEXT_STATUS = re.compile(r"API Error:\s*(\d{3})\b")


def is_context_overflow(result_event) -> bool:
    """True for an error result whose text says the context window or the request size was exceeded and whose HTTP
    status is 400 or 413: in `api_error_status`, else at the start of an `API Error: NNN` text. Without any status
    (Claude Code's own "Prompt is too long") the text decides alone."""
    if not isinstance(result_event, dict) or not result_event.get("is_error"):
        return False
    text = str(result_event.get("result") or "")
    if not OVERFLOW_TEXT.search(text):
        return False
    status = result_event.get("api_error_status")
    if status is None:
        found = _TEXT_STATUS.match(text)
        status = int(found.group(1)) if found else None
    return status is None or status in OVERFLOW_STATUSES
