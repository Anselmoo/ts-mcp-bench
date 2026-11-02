"""The demo run set (fake claude): a small folder of run sets made at test time with `tsbench run --dry-run`.

    python tests/demo_runs.py OUT        # build the run sets into OUT (OUT must not exist)

Nothing of it is stored in the repository. Each run set is one (model, condition) cell, named
`<group>/<model>-condition-<c>`, built from its own plan as tools/ci/e2e_dry.sh builds one:

- `demo-claude/`: claude-sonnet-5-5 on one pilot task per class plus some more published-spectra tasks (condition C
  leaves out the pairing and crossover tasks, so that a class has no run under a condition), and claude-haiku-5-5 on
  seven of those tasks. `demo-claude/claude-sonnet-5-5-stopped-B` holds one B run whose call stopped before the
  result event: a run that is not evaluable and has no .meta.json.
- `demo-gateway/`: gemma-4-31b-it through the gateway, on fewer tasks under B and C than under A.

The fake answers each task correctly or wrongly by a hash of prompt, model and condition, and one answer in twenty
carries no JSON line, so the pages have correct, wrong and unparseable answers to show. Each call reports a fixed
cost per model (FAKE_COST_USD); through the gateway that cost is Claude Code's estimate, not a real cost. The runs
are not scored: `tsbench score` and the report commands write scores.csv beside them.
"""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

ONE_PER_CLASS = ("P-closed_form-01", "P-experimental-01", "P-numerical-01", "P-numerical_hard-01", "P-racah_c-01",
                 "P-tetrahedral-01", "P-out_of_scope-01", "P-crossover-01", "P-curve-01", "P-batch-01",
                 "P-pairing-01", "P-literature_all-01", "P-diagram-01", "P-literature_new-01")
SONNET = (*ONE_PER_CLASS, "P-literature_all-02", "P-literature_all-03", "P-literature_new-02")
SONNET_C = tuple(t for t in SONNET if t not in ("P-pairing-01", "P-crossover-01"))
HAIKU = ("P-closed_form-01", "P-numerical-01", "P-out_of_scope-01", "P-curve-01", "P-batch-01",
         "P-literature_all-01", "P-diagram-01")
GEMMA = {"A": ("P-closed_form-01", "P-numerical-01", "P-tetrahedral-01", "P-curve-01", "P-literature_all-01"),
         "B": ("P-closed_form-01", "P-numerical-01", "P-literature_all-01"),
         "C": ("P-closed_form-01", "P-numerical-01")}

SONNET_MODEL, HAIKU_MODEL, GATEWAY_MODEL = "claude-sonnet-5-5", "claude-haiku-5-5", "gemma-4-31b-it"
HOST_LABEL = "demo"


def run_sets() -> list[dict]:
    """Every run set of the demo: its folder (relative to the root), model, condition, task ids, gateway flag, the
    FAKE_* switches of its fake claude and the exit codes of `tsbench run` that count as built."""
    out = []
    for cond in "ABC":
        out.append({"name": f"demo-claude/{SONNET_MODEL}-condition-{cond}", "model": SONNET_MODEL, "cond": cond,
                    "tasks": SONNET_C if cond == "C" else SONNET, "gateway": False, "fake": {"FAKE_COST_USD": "0.03"},
                    "exit": (0,)})
        out.append({"name": f"demo-claude/{HAIKU_MODEL}-condition-{cond}", "model": HAIKU_MODEL, "cond": cond,
                    "tasks": HAIKU, "gateway": False, "fake": {"FAKE_COST_USD": "0.01"}, "exit": (0,)})
        out.append({"name": f"demo-gateway/{GATEWAY_MODEL}-condition-{cond}", "model": GATEWAY_MODEL, "cond": cond,
                    "tasks": GEMMA[cond], "gateway": True, "fake": {"FAKE_COST_USD": "0.02"}, "exit": (0,)})
    out.append({"name": f"demo-claude/{SONNET_MODEL}-stopped-B", "model": SONNET_MODEL, "cond": "B",
                "tasks": ("P-numerical_hard-02",), "gateway": False, "fake": {"FAKE_NO_RESULT": "1"},
                # 75: a run set in which no run was answered stops as if the quota were used up
                "exit": (0, 75)})
    return out


def _env(fake: dict[str, str]) -> dict[str, str]:
    """The environment of a build step: no provider key, no FAKE_* switch except those of the run set, a fixed host
    label."""
    drop = ("TSMCP_ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN",
            "GWDG_API_KEY", "GWDG_AI_API_KEY", "TSBENCH_HOST_SALT")
    env = {k: v for k, v in os.environ.items() if k not in drop and not k.startswith("FAKE_")}
    env.update(fake, TSBENCH_HOST_LABEL=HOST_LABEL)
    return env


def _tsbench(args: list[str], env: dict[str, str], ok: tuple[int, ...] = (0,)) -> None:
    done = subprocess.run([sys.executable, "-m", "tsbench", *args], env=env, capture_output=True, text=True,
                          encoding="utf-8", timeout=600, check=False)
    if done.returncode not in ok:
        raise RuntimeError(f"tsbench {' '.join(args[:1])} failed ({done.returncode}):\n{done.stdout}\n{done.stderr}")


def _build_one(root: pathlib.Path, plans: pathlib.Path, rs: dict) -> None:
    plan = plans / (rs["name"].replace("/", "__") + ".jsonl")
    env = _env(rs["fake"])
    gateway = ["--gateway"] if rs["gateway"] else []
    _tsbench(["plan", "build", "--split", "pilot", "--models", rs["model"], "--conditions", rs["cond"],
              "--effort", "medium", "--k", "1", "--budget-usd", "10", "--task-ids", ",".join(rs["tasks"]),
              "--out-plan", str(plan), *gateway], env)
    _tsbench(["run", "--plan", str(plan), "--dry-run", "--out", str(root / rs["name"]), *gateway], env,
             rs["exit"])


def build(root: pathlib.Path) -> pathlib.Path:
    """Build every run set of the demo into `root` (which must not exist yet) and return `root`. The plans are
    written to a folder beside it, `<root>.plans`."""
    root = pathlib.Path(root)
    if root.exists():
        raise FileExistsError(root)
    plans = root.with_name(root.name + ".plans")
    plans.mkdir(parents=True)
    root.mkdir(parents=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        for f in [pool.submit(_build_one, root, plans, rs) for rs in run_sets()]:
            f.result()
    return root


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python tests/demo_runs.py OUT")
    print(f"demo run set: {build(pathlib.Path(sys.argv[1]))}")
