"""tools/functional_test.sh traces every step: it sets TSBENCH_TRACE to OUT/trace/<step> for the step, renders
OUT/provenance.html with `tsbench report provenance`, and the summary links it. A traced and an untraced fake run write
the same scores (scores.csv except wall_time_s, rates.csv) and the same files apart from the trace output.

Only `--fake` runs here: no network, no key. The integration tests run the script twice (about half a minute)."""
from __future__ import annotations

import csv
import importlib
import json
import os
import re
import subprocess
from pathlib import Path

import pytest

from tsbench.conditions.sandbox import KEY_VARS

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "tools" / "functional_test.sh"
STEPS = ("tasks-verify", "sandbox-probe", "plan-build", "run", "score", "figures", "report-views", "report-gallery",
         "report-dashboard")
TRACE_ONLY = ("trace", "provenance.html", "provenance.prov.json", "OVERVIEW.html")
SECRET = "ENV-SENTINEL-FT-5be1"  # gitleaks:allow (made-up marker)
DROPPED_ENV = ("TSBENCH_TRACE", "ANTHROPIC_BASE_URL", *KEY_VARS)
HOME_SEGMENT = re.compile(r"/(?:home|Users)/[^/\s\"']+/")


# ---------------------------------------------------------------- the script, read as text
def test_the_fake_mode_unsets_every_key_variable_the_sandbox_denies():
    text = SCRIPT.read_text(encoding="utf-8")
    unset = re.search(r"\( unset ([A-Z_ ]+);", text)
    assert unset is not None
    assert set(KEY_VARS) <= set(unset.group(1).split())


def test_the_script_sets_the_trace_folder_per_step_and_renders_the_provenance_page():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "TSBENCH_TRACE" in text and "/trace/" in text
    assert "--no-trace" in text
    assert "report provenance" in text
    assert text.index("report provenance") < text.index("report summary"), "the summary links a page that exists"
    assert text.index("report functional") < text.index("report summary"), "the summary links the overview too"


def test_the_gateway_mode_takes_the_key_file_from_tsbench_key_file():
    """The key file is configurable (TSBENCH_KEY_FILE) with a neutral default; the script never prints it."""
    text = SCRIPT.read_text(encoding="utf-8")
    assert 'KEY_FILE="${TSBENCH_KEY_FILE:-$HOME/.config/tsbench/env}"' in text
    assert not re.search(r"(echo|printf|cat)[^\n]*KEY_FILE", text)


# ---------------------------------------------------------------- two fake runs: traced and untraced
def _run(out: Path, *extra: str) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k not in DROPPED_ENV and not k.startswith("FAKE_")}
    env["TSBENCH_TEST_SECRET"] = SECRET
    return subprocess.run(["bash", str(SCRIPT), "--fake", "--out", str(out), *extra], cwd=REPO, env=env,
                          capture_output=True, text=True, timeout=900, encoding="utf-8")


@pytest.fixture(scope="module")
def pair(tmp_path_factory):
    if not (REPO / ".venv" / "bin" / "tsbench").exists():
        pytest.skip("the functional test needs the repository .venv")
    base = tmp_path_factory.mktemp("functional")
    traced, plain = base / "traced", base / "plain"
    return {"traced": traced, "plain": plain, "traced_proc": _run(traced), "plain_proc": _run(plain, "--no-trace")}


def _steps(out: Path) -> list[tuple[str, int]]:
    lines = (out / "steps.jsonl").read_text(encoding="utf-8").splitlines()
    return [(s["name"], s["rc"]) for s in map(json.loads, lines)]


def _rows(path: Path, drop: tuple[str, ...] = ()) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as f:
        return [{k: v for k, v in r.items() if k not in drop} for r in csv.DictReader(f)]


def _files(out: Path) -> set[str]:
    return {p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file()
            and p.relative_to(out).parts[0] not in TRACE_ONLY}


def test_both_runs_pass_every_step(pair):
    for key in ("traced", "plain"):
        proc = pair[f"{key}_proc"]
        assert proc.returncode == 0, proc.stdout[-2000:] + proc.stderr[-2000:]
        assert _steps(pair[key]) == [(s, 0) for s in STEPS]


def test_tracing_does_not_change_the_scores(pair):
    traced, plain = pair["traced"] / "runs", pair["plain"] / "runs"
    drop = ("wall_time_s", "transcript_sha256")  # the time and the stream's own timestamps differ from run to run
    assert _rows(traced / "scores.csv", drop) == _rows(plain / "scores.csv", drop)
    assert _rows(traced / "rates.csv") == _rows(plain / "rates.csv")
    assert len(_rows(plain / "scores.csv")) == 9


def test_tracing_adds_only_the_trace_output(pair):
    assert _files(pair["traced"]) == _files(pair["plain"])
    assert not (pair["plain"] / "trace").exists() and not (pair["plain"] / "provenance.html").exists()


def test_every_step_has_a_trace_and_the_children_are_traced(pair):
    root = pair["traced"] / "trace"
    counts = {s: len(list((root / s).glob("*.trace.json"))) for s in STEPS}
    assert all(n >= 1 for n in counts.values()), counts
    assert counts["run"] >= 10, "the run step and its nine fake claudes"
    assert counts["sandbox-probe"] >= 2, "the probe and its fake claude"


def test_no_trace_record_holds_an_environment_value_or_a_home_path(pair):
    assert list((pair["traced"] / "trace").rglob("*.trace.json")), "the check is not vacuous"
    for p in (pair["traced"] / "trace").rglob("*.trace.json"):
        text = p.read_text(encoding="utf-8")
        assert SECRET not in text, p
        assert str(Path.home()) not in text, p
        assert not HOME_SEGMENT.search(text), p


def test_the_provenance_page_shows_an_intact_chain_and_the_summary_links_it(pair):
    out = pair["traced"]
    html = (out / "provenance.html").read_text(encoding="utf-8")
    assert "Hash chain intact" in html
    for step in STEPS:
        assert f'<section id="step-{step}"' in html
    assert 'href="provenance.html"' in (out / "SUMMARY.html").read_text(encoding="utf-8")
    assert 'href="provenance.html"' not in (pair["plain"] / "SUMMARY.html").read_text(encoding="utf-8")
    assert str(out) not in html


def test_the_overview_shows_every_step_and_the_summary_links_it(pair):
    out = pair["traced"]
    html = (out / "OVERVIEW.html").read_text(encoding="utf-8")
    assert "All 9 steps passed." in html and "intact" in html
    assert html.count('<figure class="ftd') == 2
    assert 'href="OVERVIEW.html"' in (out / "SUMMARY.html").read_text(encoding="utf-8")
    assert not (pair["plain"] / "OVERVIEW.html").exists()
    assert not HOME_SEGMENT.search(html)


def test_the_chain_links_the_steps_through_real_files(pair):
    trace_prov = importlib.import_module("tsbench.core.trace_prov")
    records = trace_prov.load_records(pair["traced"] / "trace")
    assert trace_prov.hash_chain(records) == []
    doc = trace_prov.to_prov(records)
    step_of = {trace_prov.activity_id(r): r["step"] for r in records}
    made = {(g["prov:entity"], step_of[g["prov:activity"]]) for g in doc["wasGeneratedBy"].values()}
    used = {(u["prov:entity"], step_of[u["prov:activity"]]) for u in doc["used"].values()}
    flows = {(a, b) for e, a in made for f, b in used if e == f and a != b}
    for link in (("plan-build", "run"), ("run", "score"), ("score", "figures")):
        assert link in flows, f"no file written by {link[0]} and read by {link[1]}"
    assert json.loads((pair["traced"] / "provenance.prov.json").read_text(encoding="utf-8"))["activity"]
