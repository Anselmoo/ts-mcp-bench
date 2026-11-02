"""Unit tests for tools/ci/check_e2e.py."""
import importlib.util
import json
import pathlib
import sys

CI_DIR = pathlib.Path(__file__).resolve().parents[2] / "tools" / "ci"
spec = importlib.util.spec_from_file_location("check_e2e", CI_DIR / "check_e2e.py")
ce = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = ce
spec.loader.exec_module(ce)


def _make(tmp_path, aborted=0, drop=()):
    out = tmp_path / "e2e"
    (out / "views").mkdir(parents=True)
    files = ["plan/plan.jsonl", "runs/MANIFEST.json", "runs/rates.csv", "runs/scores.csv", "runs/report.html",
             "runs/views/INDEX.html", "runs/hypotheses.json"]
    for f in files:
        if f in drop:
            continue
        p = out / f
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x", encoding="utf-8")
    if "runs/MANIFEST.json" not in drop:
        (out / "runs/MANIFEST.json").write_text(json.dumps({
            "counts": {"aborted": aborted, "done": 9}, "aborted_cells": [{"c": 1}] * aborted,
            "child_path": {"A": "/usr/bin:/bin"}}), encoding="utf-8")
    return out


def test_ok(tmp_path):
    assert ce.check(_make(tmp_path)) == []


def test_missing_file_reported(tmp_path):
    errs = ce.check(_make(tmp_path, drop=("runs/report.html",)))
    assert any("runs/report.html" in e for e in errs)


def test_aborted_reported(tmp_path):
    errs = ce.check(_make(tmp_path, aborted=2))
    assert any("aborted" in e for e in errs)


def test_zero_done_reported(tmp_path):
    out = _make(tmp_path)
    (out / "runs/MANIFEST.json").write_text(json.dumps({"counts": {"aborted": 0, "done": 0}}), encoding="utf-8")
    assert any("done" in e for e in ce.check(out))


def test_main_exit_codes(tmp_path):
    assert ce.main([str(_make(tmp_path))]) == 0
    assert ce.main([str(tmp_path / "nope")]) == 1


def test_identity_scan_flags_home_paths_and_hostnames(tmp_path):
    """A record with /Users/<name>/ or /home/<name>/ or the hostname fails the e2e check; placeholders pass."""
    out = _make(tmp_path)
    meta = out / "runs" / "m" / "A" / "medium" / "t-k1.meta.json"
    meta.parent.mkdir(parents=True)
    meta.write_text(json.dumps({"argv": ["<CLAUDE>", "--settings", "<CFG>/sandbox-settings.json"]}), encoding="utf-8")
    assert ce.check(out) == []
    meta.write_text(json.dumps({"argv": ["/Users/someone/.local/bin/claude"]}), encoding="utf-8")
    assert any("home path" in e and "t-k1.meta.json" in e for e in ce.check(out))
    meta.write_text(json.dumps({"x": "/home/op/x"}), encoding="utf-8")
    assert any("home path" in e for e in ce.check(out))
    meta.write_text(json.dumps({"host": "build-host-7"}), encoding="utf-8")
    assert ce.identity_findings([meta], ["build-host-7"]) == [f"{meta}: the hostname"]
    assert ce.identity_findings([meta], ["other"]) == []


def test_missing_child_path_reported(tmp_path):
    out = _make(tmp_path)
    (out / "runs/MANIFEST.json").write_text(json.dumps({"counts": {"aborted": 0, "done": 1}}), encoding="utf-8")
    assert any("child_path" in e for e in ce.check(out))
