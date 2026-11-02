#!/usr/bin/env python3
"""Run the README's shell blocks that are marked safe, in a temporary copy of the repo.

A fenced block (```bash, ```sh or ```shell) is safe when its FIRST line is exactly `# ci: dry`.
Unmarked blocks are listed as skipped and never executed. No block ever sees an API key.

    python tools/ci/readme_smoke.py [--repo DIR] [--readme FILE] [--timeout SEC] [--json]

Exit 0: no marked block failed. Exit 1: at least one failed. Exit 2: README not found.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import os
import pathlib
import re
import shutil
import signal
import subprocess
import sys
import tempfile

MARKER = "# ci: dry"
SHELLS = {"bash", "sh", "shell"}
# the names of conditions.sandbox.KEY_VARS (a test compares them) and the gateway URL
KEY_VARS = ("ANTHROPIC_API_KEY", "TSMCP_ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "GWDG_API_KEY", "GWDG_AI_API_KEY",
            "LITELLM_MASTER_KEY", "ANTHROPIC_BASE_URL")
# version control, the venv, local output and private material stay out of the copy
COPY_IGNORE = (".git", ".venv", "build", "pilot", "seed", "analysis", ".claude", "private", "__pycache__",
               ".pytest_cache")
FENCE = re.compile(r"^(`{3,}|~{3,})\s*([A-Za-z0-9_+-]*)\s*$")


@dataclasses.dataclass
class Block:
    lang: str
    line: int  # 1-based line of the opening fence
    body: str

    @property
    def safe(self) -> bool:
        first = self.body.splitlines()[0].strip() if self.body.strip() else ""
        return first == MARKER


def extract_blocks(text: str) -> list[Block]:
    """Fenced shell blocks, in order. An unterminated fence yields nothing."""
    lines = text.splitlines()
    out: list[Block] = []
    i = 0
    while i < len(lines):
        m = FENCE.match(lines[i])
        if not m:
            i += 1
            continue
        fence, lang = m.group(1), m.group(2).lower()
        j = i + 1
        while j < len(lines) and not (lines[j].startswith(fence[0] * len(fence)) and lines[j].strip() == fence):
            j += 1
        if j >= len(lines):
            break  # unterminated
        if lang in SHELLS:
            out.append(Block(lang, i + 1, "\n".join(lines[i + 1:j])))
        i = j + 1
    return out


def _clean_env(workdir: pathlib.Path) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k not in KEY_VARS}
    venv_bin = workdir / ".venv" / "bin"
    env["PATH"] = f"{venv_bin}{os.pathsep}{env.get('PATH', '')}"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def _copy_repo(repo: pathlib.Path, dest: pathlib.Path) -> None:
    shutil.copytree(repo, dest, ignore=shutil.ignore_patterns(*COPY_IGNORE), symlinks=True)
    venv = repo / ".venv"
    if venv.is_dir():  # the runner looks for <repo>/.venv/bin/...; a symlink keeps the shebangs valid
        (dest / ".venv").symlink_to(venv.resolve())


def _run_block(block: Block, cwd: pathlib.Path, timeout: float) -> dict:
    proc = subprocess.Popen(["bash", "-euo", "pipefail", "-c", block.body], cwd=cwd, env=_clean_env(cwd),
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True,
                            encoding="utf-8")
    try:
        out, _ = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        out, _ = proc.communicate()
        return {"status": "failed", "returncode": None, "reason": f"timeout after {timeout}s", "tail": out[-2000:]}
    return {"status": "passed" if proc.returncode == 0 else "failed", "returncode": proc.returncode,
            "tail": out[-2000:]}


def run(repo: pathlib.Path, readme: pathlib.Path, timeout: float = 300) -> dict:
    blocks = extract_blocks(readme.read_text(encoding="utf-8"))
    results = []
    with tempfile.TemporaryDirectory(prefix="readme-smoke-") as tmp:
        work = pathlib.Path(tmp) / "repo"
        if any(b.safe for b in blocks):
            _copy_repo(repo, work)
        for b in blocks:
            rec = {"line": b.line, "lang": b.lang, "first_line": (b.body.splitlines() or [""])[0][:80]}
            rec.update(_run_block(b, work, timeout) if b.safe else {"status": "skipped"})
            results.append(rec)
    counts = {s: sum(1 for r in results if r["status"] == s) for s in ("passed", "failed", "skipped")}
    return {"readme": str(readme), "counts": counts, "blocks": results}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", default=str(pathlib.Path(__file__).resolve().parents[2]))
    ap.add_argument("--readme", default=None, help="default <repo>/README.md")
    ap.add_argument("--timeout", type=float, default=300)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    repo = pathlib.Path(a.repo).resolve()
    readme = pathlib.Path(a.readme) if a.readme else repo / "README.md"
    if not readme.is_file():
        print(f"README not found: {readme}", file=sys.stderr)
        return 2
    report = run(repo, readme, a.timeout)
    if a.json:
        print(json.dumps(report, indent=2))
    else:
        for r in report["blocks"]:
            extra = f" (rc={r['returncode']})" if r["status"] == "failed" else ""
            print(f"{r['status']:8} line {r['line']:>4}  {r['first_line']}{extra}")
            if r["status"] == "failed":
                print("    " + r.get("tail", "").strip().replace("\n", "\n    "))
        c = report["counts"]
        print(f"{c['passed']} passed, {c['failed']} failed, {c['skipped']} skipped (unmarked)")
    return 1 if report["counts"]["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
