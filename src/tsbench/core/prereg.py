"""The preregistration guard shared by every command that touches the confirmatory split.

`--i-have-preregistered` must hold a DOI-shaped value (`10.<4-9 digits>/<suffix>`); any other string is refused.
"""
from __future__ import annotations

import re

__all__ = ["DOI_RE", "is_doi"]

DOI_RE = re.compile(r"10\.\d{4,9}/\S+")


def is_doi(value: str | None) -> bool:
    """True when `value` holds a DOI-shaped string."""
    return bool(value) and DOI_RE.search(value) is not None
