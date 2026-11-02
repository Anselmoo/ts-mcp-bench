"""Structure and safety checks for the CI pipeline (.gitlab-ci.yml and tools/ci/*.sh).

Nothing here calls a model: the guard is exercised with fake values only.
"""
import os
import pathlib
import re
import subprocess
import sys

import pytest

from tsbench.conditions.sandbox import KEY_VARS

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
CI_DIR = REPO_ROOT / "tools" / "ci"
SCRIPTS = sorted(CI_DIR.glob("*.sh"))


def _env(**extra):
    env = {k: v for k, v in os.environ.items() if k not in KEY_VARS}
    env.update(extra)
    return env


def test_scripts_exist():
    names = {p.name for p in SCRIPTS}
    assert {"common.sh", "guard_no_keys.sh", "setup.sh", "lint.sh", "test.sh", "e2e_dry.sh", "gate_no_pilot.sh",
            "gate_confirmatory.sh", "gitleaks.sh", "readme_smoke.sh", "browser.sh"} <= names


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: p.name)
def test_bash_syntax(script):
    subprocess.run(["bash", "-n", str(script)], check=True)


@pytest.mark.parametrize("script", [p for p in SCRIPTS if p.name != "common.sh"], ids=lambda p: p.name)
def test_scripts_are_executable_bash_without_zshisms(script):
    assert os.access(script, os.X_OK), "chmod +x"
    text = script.read_text(encoding="utf-8")
    assert text.startswith("#!/usr/bin/env bash\n")
    assert "zsh" not in text.replace("zshisms", "")


def test_the_guard_lists_the_variables_the_sandbox_denies():
    text = (CI_DIR / "common.sh").read_text(encoding="utf-8")
    listed = re.search(r'^TSCI_KEY_VARS="([^"]*)"', text, re.MULTILINE)
    assert listed is not None
    assert sorted(listed.group(1).split()) == sorted(KEY_VARS)


def test_guard_passes_without_keys():
    r = subprocess.run(["bash", str(CI_DIR / "guard_no_keys.sh")], env=_env(), capture_output=True, text=True,
                       encoding="utf-8")
    assert r.returncode == 0, r.stderr


@pytest.mark.parametrize("var", KEY_VARS)
def test_guard_fails_for_each_key(var):
    r = subprocess.run(["bash", str(CI_DIR / "guard_no_keys.sh")], env=_env(**{var: "fake-value"}),
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 1
    assert var in r.stderr
    assert "fake-value" not in r.stderr + r.stdout  # never echo the value


def test_guard_fails_even_for_an_empty_key():
    r = subprocess.run(["bash", str(CI_DIR / "guard_no_keys.sh")], env=_env(GWDG_API_KEY=""),
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 1


@pytest.mark.parametrize("script", ["setup.sh", "lint.sh", "test.sh", "e2e_dry.sh", "gate_no_pilot.sh",
                                    "gate_confirmatory.sh", "gitleaks.sh", "readme_smoke.sh", "browser.sh"])
def test_every_entry_script_runs_the_guard_first(script):
    r = subprocess.run(["bash", str(CI_DIR / script)], env=_env(ANTHROPIC_AUTH_TOKEN="fake"),
                       capture_output=True, text=True, timeout=60, encoding="utf-8")
    assert r.returncode == 1
    assert "ANTHROPIC_AUTH_TOKEN" in r.stderr


def test_e2e_refuses_output_outside_build_ci():
    r = subprocess.run(["bash", str(CI_DIR / "e2e_dry.sh")], env=_env(TSCI_E2E_DIR="/tmp/elsewhere"),
                       capture_output=True, text=True, timeout=60, encoding="utf-8")
    assert r.returncode == 1
    assert "build/ci/" in r.stderr


def test_mutation_refuses_output_outside_build_ci():
    r = subprocess.run(["bash", str(CI_DIR / "mutation.sh"), "x", "src", "tests"], env=_env(TSCI_MUT_DIR="elsewhere"),
                       capture_output=True, text=True, timeout=60, encoding="utf-8")
    assert r.returncode == 1
    assert "build/ci/" in r.stderr


@pytest.mark.parametrize("name", ["e2e_dry.sh", "mutation.sh", "test.sh", "browser.sh"])
def test_ci_output_defaults_to_build_ci(name):
    """CI output lands in the git-ignored build/ci/ folder, never in a folder for private material."""
    text = (CI_DIR / name).read_text(encoding="utf-8")
    assert "build/ci/" in text
    assert "pilot/" not in text


def _config():
    yaml = pytest.importorskip("yaml")
    return yaml.safe_load((REPO_ROOT / ".gitlab-ci.yml").read_text(encoding="utf-8"))


def test_gitlab_ci_parses_with_expected_jobs():
    cfg = _config()
    assert cfg["stages"] == ["lint", "test", "e2e", "gate"]
    jobs = {k: v for k, v in cfg.items() if isinstance(v, dict) and "stage" in v}
    assert {"lint", "test", "browser", "e2e-dry", "no-pilot", "confirmatory-guard", "gitleaks"} <= set(jobs)
    assert jobs["lint"]["allow_failure"] is True
    assert jobs["e2e-dry"]["artifacts"]["expire_in"] == "1 week"
    assert "junit" in jobs["test"]["artifacts"]["reports"]
    assert "junit" in jobs["browser"]["artifacts"]["reports"]


def test_gitlab_ci_is_thin_and_references_existing_scripts():
    text = (REPO_ROOT / ".gitlab-ci.yml").read_text(encoding="utf-8")
    refs = set(re.findall(r"tools/ci/([\w.]+)", text))
    assert refs, "no scripts referenced"
    for name in refs:
        assert (CI_DIR / name).is_file(), f"{name} referenced but missing"
    assert "python -m" not in text and "pytest" not in text.replace("pytest-cov", "")  # logic stays in the scripts


def test_gitlab_ci_never_sets_credentials():
    text = (REPO_ROOT / ".gitlab-ci.yml").read_text(encoding="utf-8")
    for var in KEY_VARS:
        assert not re.search(rf"^\s*{var}\s*:", text, re.MULTILINE)


def test_pytest_benchmark_does_not_collect_tools_ci():
    r = subprocess.run([sys.executable, "-m", "pytest", "tests", "--collect-only", "-q", "-p", "no:cacheprovider"],
                       cwd=REPO_ROOT, env=_env(PYTHONDONTWRITEBYTECODE="1"), capture_output=True, text=True,
                       timeout=300, encoding="utf-8")
    assert r.returncode == 0, r.stdout[-500:]
    assert "tools/ci" not in r.stdout  # tools/ci holds scripts only; their tests are in tests/tools
    assert "tests/tools/test_check_e2e.py" in r.stdout


def test_gitlab_jobs_on_the_uv_image_have_git():
    """The uv image has no git; the tests and the gate need it, so the default installs it for every job, and only
    a job with its own image replaces that before_script."""
    cfg = _config()
    assert any("install" in line and " git" in line for line in cfg["default"]["before_script"])
    for name, job in cfg.items():
        if isinstance(job, dict) and "script" in job and "image" not in job:
            assert "before_script" not in job, f"{name} replaces the default before_script"
