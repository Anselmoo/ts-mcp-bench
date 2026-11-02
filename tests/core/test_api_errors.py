"""The context-overflow rule shared by the scorer and the runner."""
from __future__ import annotations

import pytest

from tsbench.core import api_errors

LITELLM = ("API Error: 400 litellm.ContextWindowExceededError: This model's maximum context length is 131072 "
           "tokens. However, you requested 140000 tokens.")


@pytest.mark.parametrize("event,want", [
    ({"is_error": True, "api_error_status": 400, "result": LITELLM}, True),
    ({"is_error": True, "api_error_status": 400, "result": "prompt is too long: 215000 tokens > 200000 maximum"}, True),
    ({"is_error": True, "api_error_status": 413, "result": "Request too large"}, True),
    ({"is_error": True, "api_error_status": 413, "result": '{"type":"request_too_large"}'}, True),
    ({"is_error": True, "result": LITELLM}, True),  # the status only in the text
    ({"is_error": True, "result": "Prompt is too long"}, True),  # Claude Code's own message, no status
    ({"is_error": True, "api_error_status": 400, "result": "API Error: 400 invalid tool schema"}, False),
    ({"is_error": True, "api_error_status": 413, "result": "API Error: 413"}, False),  # no overflow text
    ({"is_error": True, "api_error_status": 500, "result": "context window of the worker is full"}, False),
    ({"is_error": True, "api_error_status": 429, "result": "too many tokens per minute"}, False),
    ({"is_error": True, "result": "API Error: 503 maximum context length"}, False),
    ({"is_error": False, "api_error_status": 400, "result": LITELLM}, False),
    ({"is_error": True}, False), (None, False), ("not a dict", False),
])
def test_is_context_overflow(event, want):
    assert api_errors.is_context_overflow(event) is want
