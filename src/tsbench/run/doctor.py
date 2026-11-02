#!/usr/bin/env python3
"""Preflight for the benchmark: environment, versions, MCP server, sandbox.

    tsbench doctor [--gateway] [--probe --out DIR [--model ID]]

Environment variables are checked by NAME only; a value is never printed. The key file (TSBENCH_KEY_FILE) is checked
with a stat only, never read. The doctor makes no model call and installs nothing. With `--probe` (and an explicit
--out) the sandbox check runs the paid probe (one small call, USD <= 0.10) unless a passing record for this claude
version and these sandbox settings is already in --out; the B stack is only validated, never created. With
`--gateway --probe` give `--model` (a model the gateway serves). A probe that ended in an API error is a WARN (not
evaluable), not a FAIL.

Exit code: 0 if no check is FAIL, 1 otherwise.
"""
from __future__ import annotations

import argparse
import asyncio
import importlib.metadata
import os
import pathlib

from tsbench.conditions import b_stack, sandbox
from tsbench.core import keys
from tsbench.core.util import claude_version
from tsbench.run import runner, sandbox_probe

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]

EXPECTED_FILE = REPO_ROOT / "tools" / "expected-versions.txt"
REQUIRED_TOOLS = ("ts_fit_spectrum", "ts_terms_table_data", "ts_supported_configs")
MCP_TIMEOUT_S = 60
GWDG_NAMES = ("GWDG_API_KEY", "GWDG_AI_API_KEY")

Row = tuple[str, str, str]  # status, check, detail


# ---------------------------------------------------------------- helpers
def parse_expected(text: str) -> dict[str, str]:
    """`key value   # comment` lines -> {key: value}."""
    out: dict[str, str] = {}
    for line in text.splitlines():
        parts = line.split("#", 1)[0].split()
        if len(parts) >= 2:
            out[parts[0]] = parts[1]
    return out


def load_expected(path: pathlib.Path = EXPECTED_FILE) -> dict[str, str]:
    try:
        return parse_expected(path.read_text(encoding="utf-8"))
    except OSError:
        return {}


def claude_version_string(env=None) -> str | None:
    """Same string the runner records (`claude --version`, stripped); None if unavailable."""
    import shutil

    env = os.environ if env is None else env
    real = shutil.which("claude", path=env.get("PATH"))
    if not real:
        return None
    return claude_version(real, env=env)


# ---------------------------------------------------------------- checks
def check_env(env, gateway: bool) -> list[Row]:
    rows: list[Row] = []
    if gateway:
        for name in ("ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN"):
            rows.append(("OK", f"env {name}", "set") if env.get(name)
                        else ("FAIL", f"env {name}", "NOT set (required with --gateway)"))
        if env.get("ANTHROPIC_API_KEY"):
            rows.append(("WARN", "env ANTHROPIC_API_KEY",
                         "set; unset it (the runner drops it in gateway mode anyway)"))
    else:
        if runner.api_key_of(env):
            which = "TSMCP_ANTHROPIC_API_KEY" if env.get("TSMCP_ANTHROPIC_API_KEY") else "ANTHROPIC_API_KEY"
            rows.append(("OK", "env API key", f"{which} is set"))
        else:
            rows.append(("FAIL", "env API key", "neither TSMCP_ANTHROPIC_API_KEY nor ANTHROPIC_API_KEY is set"))
        if env.get("ANTHROPIC_BASE_URL"):
            rows.append(("WARN", "env ANTHROPIC_BASE_URL",
                         "set; the runner drops it in direct mode (use --gateway to route through it)"))
    set_names = [n for n in GWDG_NAMES if env.get(n)]
    rows.append(("INFO", "env GWDG key (optional)",
                 f"{set_names[0]} is set" if set_names else "neither GWDG_API_KEY nor GWDG_AI_API_KEY set (only needed "
                 "for gateway smoke tests)"))
    return rows


def check_key_file(env) -> list[Row]:
    """Whether the key file named by TSBENCH_KEY_FILE (or the default) exists: a stat, never a read. Optional: the keys
    can come from the shell as well, so a missing file is INFO."""
    name = keys.display_name(env)
    if keys.key_file_exists(env):
        return [("OK", "key file", f"{name} exists (named by {keys.KEY_FILE_VAR} or the default; never read)")]
    return [("INFO", "key file", f"{name} not found (optional: the keys can also come from the shell; "
             f"{keys.KEY_FILE_VAR} names another file)")]


def check_versions(env, expected: dict[str, str]) -> list[Row]:
    rows: list[Row] = []
    want_ts = expected.get("tanabesugano", runner.REQUIRED_TANABESUGANO)
    try:
        have_ts = importlib.metadata.version("tanabesugano")
    except importlib.metadata.PackageNotFoundError:
        have_ts = None
    if have_ts is None:
        rows.append(("FAIL", "tanabesugano", "not installed"))
    elif have_ts != want_ts:
        rows.append(("FAIL", "tanabesugano", f"{have_ts}, required {want_ts}"))
    else:
        rows.append(("OK", "tanabesugano", have_ts))

    cv = claude_version_string(env)
    want_cv = expected.get("claude")
    if cv is None:
        rows.append(("WARN", "claude CLI", "not found on PATH (real runs need it; --dry-run does not)"))
    elif want_cv and cv.split()[0] != want_cv:
        rows.append(("WARN", "claude CLI", f"{cv}; differs from expected {want_cv} (tools/expected-versions.txt)"))
    else:
        rows.append(("OK", "claude CLI", f"{cv} (expected {want_cv or 'unset'})"))
    return rows


async def _handshake(command: str, args: list[str], errlog) -> list[str]:
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client

    params = StdioServerParameters(command=command, args=args)
    async with stdio_client(params, errlog=errlog) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            listed = await session.list_tools()
            return sorted(t.name for t in listed.tools)


def list_server_tools(command: str, args: list[str], timeout_s: float = MCP_TIMEOUT_S) -> list[str]:
    """Start the MCP server over stdio, initialize, list_tools. Raises on failure or timeout."""
    import tempfile

    with tempfile.TemporaryFile("w+", encoding="utf-8", errors="replace") as errlog:  # the server's banner goes here
        try:
            return asyncio.run(asyncio.wait_for(_handshake(command, args, errlog), timeout=timeout_s))
        except BaseException as e:
            if isinstance(e, (KeyboardInterrupt, SystemExit)):
                raise
            errlog.seek(0)
            tail = errlog.read()[-300:].strip().replace("\n", " | ")
            if tail:
                e.add_note("server stderr: " + tail)
            raise


def check_mcp(timeout_s: float = MCP_TIMEOUT_S) -> list[Row]:
    command = runner.find_mcp_command(REPO_ROOT)
    if command is None:
        return [("FAIL", "MCP server", "tanabesugano-mcp not found in <repo>/.venv/bin or next to this Python")]
    try:
        cfg = runner.render_ts_json(command)["mcpServers"]["tanabesugano"]
        args = list(cfg.get("args", []))
        command = cfg["command"]
    except (OSError, ValueError, KeyError) as e:
        return [("FAIL", "ts.json", f"cannot render: {type(e).__name__}: {e}")]
    rows: list[Row] = [("OK", "ts.json", f"rendered, command {command}")]
    try:
        names = list_server_tools(command, args, timeout_s)
    except TimeoutError:
        rows.append(("FAIL", "MCP handshake", f"no answer within {timeout_s:g} s"))
        return rows
    except BaseException as e:  # anyio/ExceptionGroup, OSError, McpError ...
        if isinstance(e, (KeyboardInterrupt, SystemExit)):
            raise
        notes = " ".join(getattr(e, "__notes__", []))
        rows.append(("FAIL", "MCP handshake", f"{type(e).__name__}: {str(e)[:160]} {notes}".strip()))
        return rows
    missing = [t for t in REQUIRED_TOOLS if t not in names]
    if missing:
        rows.append(("FAIL", "MCP tools", f"{len(names)} tools; missing {', '.join(missing)}"))
    else:
        rows.append(("OK", "MCP tools", f"{len(names)} tools; {', '.join(REQUIRED_TOOLS)} present"))
    return rows


def check_b_stack(env, override: str | None = None) -> list[Row]:
    """Condition B's fixed stack (src/tsbench/data/conditions/b-stack.txt): validate only, never create."""
    try:
        venv = b_stack.b_venv_dir(env, override, REPO_ROOT)
        info = b_stack.ensure_b_stack(venv, create=False)
    except b_stack.BStackError as e:
        return [("FAIL", "B stack", f"{e}; create it with: tsbench env b-stack")]
    pk = info["packages"]
    return [("OK", "B stack", f"{info['path']} python {info['python']}, numpy {pk.get('numpy')}, "
             f"scipy {pk.get('scipy')}, sympy {pk.get('sympy')}, matplotlib {pk.get('matplotlib')}, no tanabesugano, "
             f"no pip; digest {info['digest'][:12]}")]


def check_sandbox(env, args, out: pathlib.Path, key_ok: bool) -> list[Row]:
    rows: list[Row] = []
    venv = None
    try:
        venv = b_stack.b_venv_dir(env, getattr(args, "b_venv", None), REPO_ROOT)
        b_digest = b_stack.digest_if_present(venv)
    except b_stack.BStackError:
        b_digest = None
    # the settings a session renders: the real home of `env`, the --b-venv directory and the key file of `env`
    real_home = str(pathlib.Path(env.get("HOME") or "~").expanduser())
    skw = {"b_venv": venv, "parent_env": env}
    try:
        settings = sandbox.render_settings(REPO_ROOT, real_home, b_venv=venv, parent_env=env)
        sb = settings["sandbox"]
        problems = []
        if sb.get("enabled") is not True:
            problems.append("sandbox.enabled is not true")
        if sb.get("network", {}).get("allowedDomains") != []:
            problems.append("network.allowedDomains is not empty")
        deny = sb.get("filesystem", {}).get("denyRead", [])
        if str(REPO_ROOT) not in deny:
            problems.append("repo path missing from denyRead")
        if real_home not in deny:
            problems.append("the real home is missing from denyRead")
        if any(entry not in deny for entry in keys.key_dir_entries(env, real_home)):
            problems.append("the key file folder is missing from denyRead")
        if problems:
            rows.append(("FAIL", "sandbox settings", "; ".join(problems)))
        else:
            rows.append(("OK", "sandbox settings",
                         f"valid, sha256 {sandbox.settings_sha256(REPO_ROOT, real_home, **skw)[:12]}, "
                         f"{len(sb['filesystem']['denyRead'])} denyRead / "
                         f"{len(sb['filesystem'].get('allowRead', []))} allowRead paths"))
    except Exception as e:  # noqa: BLE001 - report whatever render_settings raised
        return [("FAIL", "sandbox settings", f"render_settings failed: {type(e).__name__}: {e}")]

    cv = claude_version_string(env)
    if cv is None:
        rows.append(("WARN", "sandbox probe", "claude not found; a probe cannot be reused or run"))
        return rows
    reusable = sandbox.load_reusable_probe(out, cv, sandbox.settings_sha256(REPO_ROOT, real_home, **skw), b_digest,
                                           auth="gateway" if args.gateway else "direct")
    if reusable is not None:
        rows.append(("OK", "sandbox probe", f"reusable passing record in {out.name}/{sandbox.PROBE_FILENAME} "
                     f"(claude {reusable.get('claude_version')})"))
        rows += _marker_rows(reusable)
        return rows
    if not args.probe:
        rows.append(("WARN", "sandbox probe",
                     f"no reusable passing {sandbox.PROBE_FILENAME} in {out}; the runner will run the paid probe "
                     "(one small model call) unless you make the record now with: tsbench doctor --probe --out DIR"))
        return rows
    if not key_ok:
        rows.append(("FAIL", "sandbox probe", "needs credentials (see env checks above); not run"))
        return rows
    try:
        session = runner.Session.create(dry_run=False, gateway=args.gateway, parent_env=env, repo=REPO_ROOT,
                                        b_venv=getattr(args, "b_venv", None), create_b=False)
    except SystemExit:
        rows.append(("FAIL", "sandbox probe", "could not create a session (see the runner message above)"))
        return rows
    try:
        model = args.model or sandbox.PROBE_MODEL
        print(f"running the paid sandbox probe (one small call to {model}, cap USD "
              f"{sandbox.PROBE_BUDGET_USD:.2f}) ...", flush=True)
        rec = sandbox_probe.run_probe(session, out, model=model)
    finally:
        session.close()
    record = f"record {out / sandbox.PROBE_FILENAME}"
    if rec["passed"] is None:  # an API error: nothing was tested, nothing failed
        rows.append(("WARN", "sandbox probe", f"NOT EVALUABLE; cost USD {rec['cost_usd']:.4f}; {record}"))
        rows += [("WARN", "sandbox probe reason", r) for r in rec["reasons"]]
        return rows
    rows.append(("OK" if rec["passed"] else "FAIL", "sandbox probe",
                 f"{'PASS' if rec['passed'] else 'FAIL'}; cost USD {rec['cost_usd']:.4f}; {record}"))
    for r in rec["reasons"]:
        rows.append(("FAIL", "sandbox probe reason", r))
    rows += _marker_rows(rec)
    return rows


def _marker_rows(rec: dict) -> list[Row]:
    markers = rec.get("markers") or {}
    rows: list[Row] = []
    for name in (*sandbox.MUST_BE_ZERO, *sandbox.MUST_FAIL):
        rcs = markers.get(name)
        if not rcs:
            rows.append(("FAIL", f"  marker {name}", "missing"))
            continue
        want_zero = name in sandbox.MUST_BE_ZERO
        good = all((rc == 0) == want_zero for rc in rcs)
        rows.append(("OK" if good else "FAIL", f"  marker {name}",
                     f"rc={','.join(map(str, rcs))} ({'must be 0' if want_zero else 'must be non-zero'})"))
    return rows


# ---------------------------------------------------------------- driver
def run_checks(args, env=None) -> list[Row]:
    env = os.environ if env is None else env
    rows = check_env(env, args.gateway)
    rows += check_key_file(env)
    key_ok = not runner.missing_env(env, args.gateway)
    rows += check_versions(env, load_expected())
    rows += check_mcp()
    rows += check_b_stack(env, getattr(args, "b_venv", None))
    rows += check_sandbox(env, args, pathlib.Path(args.out).resolve(), key_ok)
    return rows


def render_table(rows: list[Row]) -> str:
    w = max([len(r[1]) for r in rows] + [5])
    lines = [f"{'STATUS':<6}  {'CHECK':<{w}}  DETAIL", f"{'-' * 6}  {'-' * w}  {'-' * 6}"]
    lines += [f"{s:<6}  {c:<{w}}  {d}" for s, c, d in rows]
    return "\n".join(lines)


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Preflight for the TS-MCP benchmark (never prints secret values).")
    ap.add_argument("--gateway", action="store_true", help="check the gateway variables instead of the API key")
    ap.add_argument("--probe", action="store_true",
                    help="make the paid sandbox probe call (one small model call) when no passing record can be "
                    "reused; needs --out")
    ap.add_argument("--model", default=None,
                    help="model id of the probe call (needed with --gateway --probe; default: the Haiku probe model)")
    ap.add_argument("--b-venv", dest="b_venv", default=None, metavar="DIR",
                    help="venv of condition B (default: $TSBENCH_B_VENV or ~/.cache/tsbench/venv-B)")
    ap.add_argument("--out", default=None,
                    help="runner output dir holding sandbox_probe.json (default: runs, read only; --probe "
                    "needs it explicit)")
    args = ap.parse_args(argv)
    if args.probe and args.out is None:
        ap.error("--probe writes sandbox_probe.json into --out; give --out DIR")
    if args.probe and args.gateway and not args.model:
        ap.error("--gateway --probe needs --model <gateway model id>; the default Haiku id is not served there")
    if args.out is None:
        args.out = "runs"
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    rows = run_checks(args)
    print(render_table(rows))
    n_fail = sum(1 for r in rows if r[0] == "FAIL")
    n_warn = sum(1 for r in rows if r[0] == "WARN")
    print(f"\nsummary: {n_fail} FAIL, {n_warn} WARN")
    return 1 if n_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
