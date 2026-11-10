"""The copyable "reproduce this run" block under every run card of the gallery and the literature page.

`commands(run)` returns plain text with the calls that redo one run: the task, model, condition and effort of its
transcript path `<run set>/<model>/<cond>/<effort>/<task>-k<i>.jsonl`, the gateway and budget of the MANIFEST.json
above it. The block holds `tsbench plan build ...`, `tsbench run --plan ...` and `tsbench explain <transcript>`. The
split is the one the manifest records (pilot when it records none); a confirmatory run is planned with the DOI of
`args.preregistered`, or the placeholder `<DOI>` when the manifest has none. Only
names of environment variables ever appear, never a key value, and no absolute path of the machine that built the page.
Nothing here runs anything.

Facts the text states:
  * every repro run goes to its own `repro/<task>__<model>__<cond>__<effort>__k<i>/` (the runner refuses an out
    directory that holds another plan; `plan build` writes plan.sha256 and plan.md next to the plan, so the plan lives
    in that directory too), and always as `--k 1`: k2 and k3 of a card are repetitions of the same cell;
  * the runner with `--plan` takes no selection flags (the plan is the only source of what runs).
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import shlex

from tsbench.conditions import GATEWAY_URL, gateway_base_url

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
GATEWAY_BUDGET = 1000
DEFAULT_BUDGET = 3.0
REPRO_DIR = "repro"


def read_manifest(transcript: pathlib.Path, root: pathlib.Path | None = None) -> dict:
    """The nearest MANIFEST.json above the transcript (up to `root`, else up to the filesystem root)."""
    t = pathlib.Path(transcript).resolve()
    stop = pathlib.Path(root).resolve() if root is not None else None
    for d in t.parents:
        m = d / "MANIFEST.json"
        if m.is_file():
            try:
                data = json.loads(m.read_text(encoding="utf-8"))
                return data if isinstance(data, dict) else {}
            except (OSError, ValueError):
                return {}
        if stop is not None and d == stop:
            break
    return {}


def slug(*parts) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", "__".join(str(p) for p in parts)).strip("_")


def transcript_path_for_text(path: pathlib.Path, root: pathlib.Path | None = None, run_set: str | None = None) -> str:
    """How the reproduce block names a transcript: relative to this checkout, else to the working directory, else
    `<run set name>/<path inside the run set>`. Never an absolute path."""
    p = pathlib.Path(path).resolve()
    for base in (REPO_ROOT, pathlib.Path.cwd().resolve()):
        if p.is_relative_to(base):
            return p.relative_to(base).as_posix()
    if root is not None and p.is_relative_to(pathlib.Path(root).resolve()):
        return f"{run_set or pathlib.Path(root).name}/{p.relative_to(pathlib.Path(root).resolve()).as_posix()}"
    try:
        rel = os.path.relpath(p)
        return pathlib.PurePath(rel).as_posix()
    except ValueError:
        return p.name


def _manifest_args(manifest: dict) -> dict:
    """`manifest["args"]` when it is a dict, else {}."""
    args = manifest.get("args")
    return args if isinstance(args, dict) else {}


def is_gateway(run: dict, manifest: dict) -> bool:
    args = _manifest_args(manifest)
    if "gateway" in args:
        return bool(args["gateway"])
    return not str(run.get("model", "")).startswith("claude-")


def gateway_url(manifest: dict) -> str:
    """The endpoint a gateway run used (`args.gateway_url`); the default gateway endpoint for a manifest that did not
    record it."""
    url = _manifest_args(manifest).get("gateway_url")
    return gateway_base_url(url) if url else GATEWAY_URL


def _budget(manifest: dict, gateway: bool):
    if gateway:
        return GATEWAY_BUDGET
    for v in (manifest.get("budget_usd"), (manifest.get("args") or {}).get("budget_usd")):
        if isinstance(v, (int, float)) and v > 0:
            return max(
                v, DEFAULT_BUDGET
            )  # the budget of a whole run set would stop a single repro run before it starts
    return DEFAULT_BUDGET


def shell_line(argv: list[str]) -> str:
    return " ".join(shlex.quote(str(w)) for w in argv)


def argvs(run: dict, manifest: dict | None = None) -> dict:
    """The calls as argv lists: {"gateway": bool, "env": [...], "plan": [...], "runner": [...], "explain": [...]}."""
    manifest = manifest if manifest is not None else read_manifest(run["transcript"], run.get("root"))
    gw = is_gateway(run, manifest)
    budget = _budget(manifest, gw)
    out = {"gateway": gw, "env": []}
    if gw:
        out["env"] = [f"ANTHROPIC_BASE_URL={gateway_url(manifest)}", 'ANTHROPIC_AUTH_TOKEN="$GWDG_API_KEY"']
    s = slug(run["task"], run["model"], run["cond"], run["effort"], f"k{run['k']}")
    plan = f"{REPRO_DIR}/{s}/plan.jsonl"   # plan.sha256 / plan.md land beside it: one directory per cell
    args = _manifest_args(manifest)
    split = str(manifest.get("split") or args.get("split") or "pilot")
    prereg = ["--i-have-preregistered", str(args.get("preregistered") or "<DOI>")] if split == "confirmatory" else []
    out["plan"] = ["tsbench", "plan", "build", "--split", split, *prereg, "--task-ids", run["task"],
                   "--models", run["model"], "--conditions", run["cond"], "--effort", str(run["effort"]), "--k", "1",
                   "--budget-usd", str(budget)] + (["--gateway"] if gw else []) + ["--out-plan", plan]
    out["runner"] = ["tsbench", "run", "--plan", plan, "--out", f"{REPRO_DIR}/{s}"] + (["--gateway"] if gw else [])
    out["explain"] = [
        "tsbench",
        "explain",
        transcript_path_for_text(run["transcript"], run.get("root"), run.get("label")),
    ]
    return out


def commands(run: dict, manifest: dict | None = None) -> str:
    """The text of the reproduce block (plain, shell-quoted; escape it before it goes into HTML)."""
    manifest = manifest if manifest is not None else read_manifest(run["transcript"], run.get("root"))
    a = argvs(run, manifest)
    lines = [f"# {run['task']} · {run['model']} · condition {run['cond']} · {run['effort']} · k{run['k']}"]
    if a["env"]:
        lines.append("export " + " ".join(a["env"]))
    if str(run.get("k")) != "1":
        lines.append(f"# k{run['k']} is a repetition of the same cell; the new run is made as k1")
    lines += [shell_line(a["plan"]), shell_line(a["runner"]), shell_line(a["explain"])]
    return "\n".join(lines)
