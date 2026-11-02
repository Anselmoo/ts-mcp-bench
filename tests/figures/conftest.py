"""Shared fixtures of the figure tests."""
from __future__ import annotations

import pathlib
import sys

import pytest


def _caller_is_figures(depth: int = 2) -> bool:
    return sys._getframe(depth).f_globals.get("__name__", "").startswith("tsbench.figures")


@pytest.fixture(autouse=True)
def text_io_is_utf8(monkeypatch):
    """Every text read and write of `tsbench.figures` passes `encoding="utf-8"` (a run folder may be read on a machine
    whose locale is not UTF-8). The wrappers see the call as the module made it, before pathlib fills in a default."""
    seen: list[tuple[str, object]] = []
    real_open, real_read, real_write = pathlib.Path.open, pathlib.Path.read_text, pathlib.Path.write_text

    def spy_open(self, mode="r", buffering=-1, encoding=None, errors=None, newline=None):
        if "b" not in mode and _caller_is_figures():
            seen.append((f"open({self.name})", encoding))
        return real_open(self, mode, buffering, encoding, errors, newline)

    def spy_read(self, encoding=None, errors=None):
        if _caller_is_figures():
            seen.append((f"read_text({self.name})", encoding))
        return real_read(self, encoding, errors)

    def spy_write(self, data, encoding=None, errors=None, newline=None):
        if _caller_is_figures():
            seen.append((f"write_text({self.name})", encoding))
        return real_write(self, data, encoding, errors, newline)

    monkeypatch.setattr(pathlib.Path, "open", spy_open)
    monkeypatch.setattr(pathlib.Path, "read_text", spy_read)
    monkeypatch.setattr(pathlib.Path, "write_text", spy_write)
    yield seen
    wrong = [(call, enc) for call, enc in seen if enc != "utf-8"]
    assert not wrong, f"text I/O without encoding='utf-8': {wrong}"


# a second colour theme for the tests that check that the theme of the context is applied
CONTRAST = {"ink": "#222222", "fill-soft": "#eeeeee", "series-1": "#006699", "series-2": "#b74616",
            "series-3": "#1f8a4c", "series-4": "#4b4ba8", "series-5": "#946f00", "series-6": "#8c2d19"}


@pytest.fixture
def contrast_theme(monkeypatch):
    """Registers the theme `contrast` (CONTRAST) in the vendored jfs helpers for one test; returns its name."""
    from tsbench._vendor.figura import jfs
    monkeypatch.setitem(jfs.THEMES, "contrast", CONTRAST)
    return "contrast"
