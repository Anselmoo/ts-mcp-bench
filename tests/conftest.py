"""Shared pytest fixtures for the benchmark test suite."""
from __future__ import annotations

import os
import pathlib

import demo_runs
import pytest

from tsbench.run import runner

PROVIDER_KEYS = ("TSMCP_ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN",
                 "GWDG_API_KEY", "GWDG_AI_API_KEY")


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch):
    """No provider keys, no key file setting and no FAKE_* switches leak in; tests never find a real `claude`."""
    for name in (*PROVIDER_KEYS, "TSBENCH_KEY_FILE"):
        monkeypatch.delenv(name, raising=False)
    for name in list(os.environ):
        if name.startswith("FAKE_"):
            monkeypatch.delenv(name)
    monkeypatch.setattr(runner.shutil, "which", lambda *a, **k: None)


@pytest.fixture(scope="session")
def demo_runs_root(tmp_path_factory) -> pathlib.Path:
    """The demo run set (fake claude, see tests/demo_runs.py), built once per test process. Read only: a test that
    writes into run sets (scores, views, pages) works on a copy (`shutil.copytree`)."""
    return demo_runs.build(tmp_path_factory.mktemp("demo") / "runs")
