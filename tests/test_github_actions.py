"""Structure and safety checks for the GitHub Actions workflows (.github/workflows/*.yml).

The workflows mirror .gitlab-ci.yml: every job calls tools/ci/*.sh, starts with the key guard and holds no model
secret. Mutation testing runs on a schedule or on request only, split into one job per shard so that no job reaches
the 6-hour limit of GitHub-hosted runners.
"""
import json
import pathlib
import re
import subprocess
import sys

import pytest

from tsbench.conditions.sandbox import KEY_VARS

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
CI_DIR = REPO_ROOT / "tools" / "ci"
HOSTED_LIMIT_MINUTES = 360  # GitHub-hosted runners stop a job after 6 hours


def _load(name):
    yaml = pytest.importorskip("yaml")
    return yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))


def _triggers(cfg):
    return cfg.get("on", cfg.get(True))  # PyYAML reads the bare key `on` as True


def _run_steps(job):
    return [s["run"] for s in job.get("steps", []) if "run" in s]


@pytest.mark.parametrize("name", ["ci.yml", "mutation.yml"])
def test_workflow_is_thin_safe_and_read_only(name):
    text = (WORKFLOWS / name).read_text(encoding="utf-8")
    cfg = _load(name)
    assert cfg["permissions"] == {"contents": "read"}
    refs = set(re.findall(r"tools/ci/([\w.]+)", text))
    assert refs, "no scripts referenced"
    for ref in refs:
        assert (CI_DIR / ref).is_file(), f"{ref} referenced but missing"
    # no credential reaches a job; the one secret is the release gate's list of names to refuse
    assert set(re.findall(r"secrets\.(\w+)", text)) <= {"TSBENCH_GATE_DENY"}
    for var in KEY_VARS:
        assert var not in text
    assert "pytest" not in text and "mutmut" not in text  # logic stays in the scripts
    for job_id, job in cfg["jobs"].items():
        runs = _run_steps(job)
        assert runs and runs[0].strip() == "bash tools/ci/guard_no_keys.sh", f"{job_id}: guard must run first"
        assert "timeout-minutes" in job, f"{job_id}: no timeout"


def test_ci_mirrors_the_gitlab_jobs():
    gitlab = pytest.importorskip("yaml").safe_load((REPO_ROOT / ".gitlab-ci.yml").read_text(encoding="utf-8"))
    gitlab_jobs = {k for k, v in gitlab.items() if isinstance(v, dict) and "stage" in v}
    cfg = _load("ci.yml")
    assert set(cfg["jobs"]) == gitlab_jobs
    assert {"push", "pull_request"} <= set(_triggers(cfg))
    assert cfg["jobs"]["lint"]["continue-on-error"] is True  # report-only, as allow_failure in GitLab
    assert all(int(j["timeout-minutes"]) <= 60 for j in cfg["jobs"].values())
    checkout = [s for s in cfg["jobs"]["gitleaks"]["steps"] if str(s.get("uses", "")).startswith("actions/checkout")]
    assert checkout[0]["with"]["fetch-depth"] == 0  # gitleaks scans the whole history


def test_mutation_runs_only_on_schedule_or_request():
    cfg = _load("mutation.yml")
    assert set(_triggers(cfg)) == {"schedule", "workflow_dispatch"}  # never on push or pull_request


def test_mutation_shards_fit_the_hosted_job_limit():
    cfg = _load("mutation.yml")
    shard_job = cfg["jobs"]["shard"]
    timeout = str(shard_job["timeout-minutes"])
    default = int(re.search(r"'(\d+)'", timeout).group(1)) if "${{" in timeout else int(timeout)
    assert default < HOSTED_LIMIT_MINUTES
    assert "matrix" in shard_job["strategy"] and shard_job["strategy"]["fail-fast"] is False
    report = cfg["jobs"]["report"]
    assert report["needs"] == "shard" and report["if"] == "always()"


def test_shard_matrix_comes_from_the_shard_file():
    shards = json.loads((CI_DIR / "mutation_shards.json").read_text(encoding="utf-8"))
    names = [s["name"] for s in shards]
    assert len(names) == len(set(names)) and names
    for s in shards:
        assert s["source_paths"] and s["test_paths"]
        for path in s["source_paths"] + s["test_paths"]:
            assert (REPO_ROOT / path).exists(), path
        assert not any("stats/analysis.py" == p.removeprefix("src/tsbench/") for p in s["source_paths"])
    out = subprocess.run([sys.executable, str(CI_DIR / "mutation_report.py"), "matrix"], capture_output=True,
                         text=True, check=True, encoding="utf-8").stdout
    assert [m["name"] for m in json.loads(out)["include"]] == names
    one = subprocess.run([sys.executable, str(CI_DIR / "mutation_report.py"), "matrix", "--only", names[0]],
                         capture_output=True, text=True, check=True, encoding="utf-8").stdout
    assert [m["name"] for m in json.loads(one)["include"]] == [names[0]]
