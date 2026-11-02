"""Shared helpers for the score tests."""
from __future__ import annotations

import builtins
import importlib
import pathlib
import pkgutil

import pytest

import tsbench.score as score_pkg


class IoSpy:
    """Records how files are opened: every text read and write must pass encoding="utf-8"."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def kinds(self, kind: str) -> list[dict]:
        return [kw for k, kw in self.calls if k == kind]


@pytest.fixture
def io_spy(monkeypatch):
    """Spy on Path.read_text, Path.write_text and open (also as a module global of the score modules)."""
    spy = IoSpy()
    real_read, real_write, real_open = pathlib.Path.read_text, pathlib.Path.write_text, builtins.open

    def read_text(self, *a, **kw):
        spy.calls.append(("read_text", kw))
        return real_read(self, *a, **kw)

    def write_text(self, *a, **kw):
        spy.calls.append(("write_text", kw))
        return real_write(self, *a, **kw)

    def spy_open(*a, **kw):
        spy.calls.append(("open", kw))
        return real_open(*a, **kw)

    monkeypatch.setattr(pathlib.Path, "read_text", read_text)
    monkeypatch.setattr(pathlib.Path, "write_text", write_text)
    for info in pkgutil.iter_modules(score_pkg.__path__):
        mod = importlib.import_module(f"tsbench.score.{info.name}")
        monkeypatch.setattr(mod, "open", spy_open, raising=False)
    return spy
