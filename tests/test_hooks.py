"""The local git hooks in .pre-commit-config.yaml: every tool comes from uv.lock, and no hook tags or releases."""
from __future__ import annotations

import pathlib
import re
import shutil
import subprocess
import tomllib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONFIG = ROOT / ".pre-commit-config.yaml"
PYPROJECT = ROOT / "pyproject.toml"
LOCK = ROOT / "uv.lock"

# a hook runs a tool pinned in uv.lock, or a script of tools/ci
ENTRY_PREFIXES = ("uv run --frozen ", "bash tools/ci/")
# extra -> distributions the hooks call, so one `uv sync --extra lint` installs all of them
HOOK_EXTRAS = {"lint": ("pre-commit", "ruff", "ty", "repo-release-tools")}
# rrt subcommands that tag, release or bump: never in a hook, apart from a dry run
RRT_WRITE = re.compile(r"\brrt\s+(tag|release|bump)\b")


def requirement_name(spec: str) -> str:
    """The distribution name of a PEP 508 requirement string, lower case."""
    return re.split(r"[<>=!~\[; ]", spec.strip(), maxsplit=1)[0].lower()


@pytest.fixture(scope="module")
def config() -> dict:
    yaml = pytest.importorskip("yaml")
    assert CONFIG.is_file(), ".pre-commit-config.yaml is missing"
    return yaml.safe_load(CONFIG.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def hooks(config) -> list[dict]:
    found = [hook for repo in config["repos"] for hook in repo.get("hooks", [])]
    assert found, "no hooks"
    return found


def hook_ids(hooks: list[dict], stage: str) -> set[str]:
    return {hook["id"] for hook in hooks if stage in hook.get("stages", [])}


def test_every_repo_is_local(config):
    repos = [repo["repo"] for repo in config["repos"]]
    assert repos and all(repo == "local" for repo in repos), repos
    assert not any("rev" in repo for repo in config["repos"]), "a local repo carries no rev pin"


def test_every_hook_is_a_system_hook(hooks):
    """language: system runs the entry as it is; pre-commit builds no hook environment of its own."""
    other = sorted(hook["id"] for hook in hooks if hook.get("language") != "system")
    assert not other, other


def test_every_entry_uses_the_lock_file_or_a_ci_script(hooks):
    bad = sorted(f"{hook['id']}: {hook['entry']}" for hook in hooks if not hook["entry"].startswith(ENTRY_PREFIXES))
    assert not bad, bad


def test_no_hook_tags_releases_or_bumps(hooks):
    bad = sorted(hook["id"] for hook in hooks
                 if RRT_WRITE.search(hook["entry"]) and "--dry-run" not in hook["entry"])
    assert not bad, bad


def test_every_hook_names_its_stage(hooks):
    missing = sorted(hook["id"] for hook in hooks if not hook.get("stages"))
    assert not missing, missing


@pytest.mark.parametrize("hook_id", ["guard-no-keys", "ruff", "ty", "gitleaks", "tasks-verify"])
def test_pre_commit_stage_hooks(hooks, hook_id):
    assert hook_id in hook_ids(hooks, "pre-commit")


@pytest.mark.parametrize("hook_id", ["rrt-doctor", "rrt-eol"])
def test_pre_push_stage_hooks(hooks, hook_id):
    assert hook_id in hook_ids(hooks, "pre-push")


def test_the_guard_runs_first(hooks):
    assert hooks[0]["id"] == "guard-no-keys"
    assert hooks[0]["entry"] == "bash tools/ci/guard_no_keys.sh"


def test_ty_reports_only_new_findings(hooks):
    """ty checks the staged files against a committed baseline, so the hook fails on new findings only."""
    entry = next(hook["entry"] for hook in hooks if hook["id"] == "ty").split()
    assert "--baseline" in entry
    assert (ROOT / entry[entry.index("--baseline") + 1]).is_file()
    assert "--update-baseline" not in entry


# the test files that the ty hook must pass on, with the committed baseline
TY_TEST_FILES = ["tests/run/test_runner.py", "tests/plan/test_plan_rules.py"]


def test_ty_hook_passes_on_the_test_files_it_is_given(hooks):
    """A finding that is not in the baseline fails the hook, so these test files must carry no new findings."""
    ty = shutil.which("ty") or str(ROOT / ".venv" / "bin" / "ty")
    if not pathlib.Path(ty).is_file():
        pytest.skip("ty is not installed")
    entry = next(hook["entry"] for hook in hooks if hook["id"] == "ty").split()
    baseline = entry[entry.index("--baseline") + 1]
    done = subprocess.run([ty, "check", "--output-format", "concise", "--baseline", baseline, *TY_TEST_FILES],
                          cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=False)
    assert done.returncode == 0, done.stdout[-3000:]


def test_install_covers_both_stages(config):
    assert set(config.get("default_install_hook_types", [])) == {"pre-commit", "pre-push"}


def test_every_ci_script_named_exists(hooks):
    for hook in hooks:
        if hook["entry"].startswith("bash tools/ci/"):
            assert (ROOT / hook["entry"].split()[1]).is_file(), hook["entry"]


@pytest.mark.parametrize("extra", sorted(HOOK_EXTRAS))
def test_extras_list_the_hook_tools(extra):
    with PYPROJECT.open("rb") as handle:
        project = tomllib.load(handle)["project"]
    names = {requirement_name(spec) for spec in project.get("optional-dependencies", {}).get(extra, [])}
    missing = sorted(set(HOOK_EXTRAS[extra]) - names)
    assert not missing, f"missing from extra {extra!r}: {missing}"
    runtime = {requirement_name(spec) for spec in project.get("dependencies", [])}
    assert not runtime & set(HOOK_EXTRAS[extra]), "hook tools are not runtime dependencies"


def test_lock_file_pins_the_hook_tools():
    with LOCK.open("rb") as handle:
        packages = {pkg["name"] for pkg in tomllib.load(handle)["package"]}
    missing = sorted({name for names in HOOK_EXTRAS.values() for name in names} - packages)
    assert not missing, f"not in uv.lock: {missing}"
