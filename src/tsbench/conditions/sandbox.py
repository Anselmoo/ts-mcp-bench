"""Sandbox for condition B: Claude's Bash tool must not reach PyPI, the model APIs or loopback, must not import or run
`tanabesugano`, must not read the repository, the operator's home or the folder of the key file (only venv-B, its base
interpreter and the matplotlib cache are re-opened), and must not see a model credential (docs/methods.md, sandbox
section).

Methods, tried in this order, the choice recorded in the manifest:
  (a) "builtin"   Claude Code's own Bash sandbox with an empty network allow-list.
  (b) "container" docker/podman with egress only to the API host. NOT BUILT: detection only,
                  and only relevant if (a) fails.
  (c) "skipped"   B does not run; A and C continue.
  (d) "not evaluable"  the probe ended in an API error, so it proved nothing either way. B is not marked failed,
                  but its runs wait: they are not started in this invocation, and --resume probes again.

The decision is made by a probe: one real model call (cheap model, 3 turns, USD 0.10 cap) in
which Claude's Bash tool runs one script that prints a marker line per check. The markers are
read from the `tool_result` events of the transcript, never from the model's prose.

    tsbench env sandbox --settings-only          # print the rendered settings
    tsbench env sandbox --probe --out runs       # run the probe (needs a key)
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import pathlib
import re
import shutil
import site
import socket
import sys

from tsbench import conditions
from tsbench.conditions import b_stack
from tsbench.core import keys
from tsbench.core.util import git_output

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PROBE_MODEL = "claude-haiku-5-5"
PROBE_MAX_TURNS = 3
PROBE_BUDGET_USD = 0.10
PROBE_EFFORT = "low"
PROBE_FILENAME = "sandbox_probe.json"
PROBE_TRANSCRIPT = pathlib.Path("_sandbox_probe") / "transcript.jsonl"

REPO_PLACEHOLDER = "<REPO>"
REAL_HOME_PLACEHOLDER = "<REAL_HOME>"
KEY_DIR_PLACEHOLDER = "<KEY_DIR>"  # the folder of the key file (tsbench.core.keys)
SETTINGS_TEMPLATE: dict = {
    "sandbox": {
        "enabled": True,
        "failIfUnavailable": True,
        "autoAllowBashIfSandboxed": True,
        "allowUnsandboxedCommands": False,
        "network": {"allowedDomains": []},
        # The whole real home is denied; `allowRead` re-opens only venv-B, its base interpreter and the
        # matplotlib cache (Claude Code: "When read rules overlap, the rule with the narrower path applies",
        # code.claude.com/docs/en/sandboxing#configure-sandboxing). The repo, the main checkout and the harness's own
        # install prefix are denied explicitly as well, so that they stay unreadable wherever they live, and so is the
        # folder of the key file.
        "filesystem": {"denyRead": [REPO_PLACEHOLDER, REAL_HOME_PLACEHOLDER, KEY_DIR_PLACEHOLDER, "~/.cache/pip"],
                       "allowRead": []},
        # Without this the model credential is visible in B's Bash; "deny" unsets these variables
        # before each sandboxed command (code.claude.com/docs/en/settings-reference#sandbox-credentials-envvars).
        # Filled from KEY_VARS below.
        "credentials": {"envVars": []},
    }
}

# NUMPY: B's python3 is the fixed venv-B stack (src/tsbench/conditions/b_stack.py); numpy, scipy, sympy and
# matplotlib must import
# KEYENV: none of the credential variables is set in B's Bash (prints rc only, never a value)
# PATHS: the probe's own inputs ($TSPROBE_REPO, $TSPROBE_RH) reached the Bash tool; without them the path markers
# below would test "/..." and fail vacuously
MUST_BE_ZERO = ("CTRL1", "CTRL2", "HEREDOC", "NUMPY", "KEYENV", "PATHS")
MUST_FAIL = ("IMPORT", "PIP", "NET", "VENV", "READ",
             # no tanabesugano on PATH, the real home's caches and secrets unreadable,
             # no loopback, no model API host, no DNS
             "TSBIN", "HOMECACHE", "HOMESECRETS", "LOCALHOST", "APIHOST", "DNS")
# what KEYENV checks; the names only ever appear in the script, a value never does
KEY_VARS = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "TSMCP_ANTHROPIC_API_KEY", "GWDG_API_KEY", "GWDG_AI_API_KEY",
            "LITELLM_MASTER_KEY")
SETTINGS_TEMPLATE["sandbox"]["credentials"]["envVars"] = [{"name": v, "mode": "deny"} for v in KEY_VARS]
# real-home paths tested by HOMECACHE / HOMESECRETS (relative to the real home); only those that exist on the host are
# put in the script, one command each, so that one missing file cannot make the marker fail for the wrong reason
HOMECACHE_PATHS = (".cache/uv", ".local")
HOMESECRETS_PATHS = (".ssh", ".config/gh/hosts.yml", ".zsh_history", ".bash_history")
LOCALHOST_URL = "http://127.0.0.1:4000/"  # the LiteLLM proxy port of the gateway route
API_HOSTS = ("https://api.anthropic.com", conditions.GATEWAY_URL)
DNS_NAME = "example.org"
# What VENV and READ try to reach, relative to the repo. A target that does not exist cannot be "denied": the command
# fails because the file is absent. `missing_probe_targets` finds such targets in the parent, and the probe counts them
# as "not tested". The data path must stay the path of tsbench.tasks.TASKS_PATH (a test checks it).
PROBE_TARGETS = {"VENV": ".venv/bin/python", "READ": "src/tsbench/data/tasks/tasks.jsonl"}
PROBE_ENV_REPO = "TSPROBE_REPO"
PROBE_ENV_HOME = "TSPROBE_RH"
MARKER_RE = re.compile(r"^PROBE_([A-Z0-9]+) rc=(-?\d+)\s*$", re.M)


# ---------------------------------------------------------------- settings
def main_checkouts(repo: pathlib.Path | str) -> list[str]:
    """When `repo` is a linked checkout, the main checkout (with its own .venv and the task file) is a different
    directory: deny it too. Empty for a plain checkout or no git."""
    common = git_output(repo, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if not common:
        return []
    common_dir = pathlib.Path(common)
    main = common_dir.parent if common_dir.name == ".git" else None
    if main is None or main.resolve() == pathlib.Path(repo).resolve():
        return []
    return [str(main)]


def harness_prefixes() -> list[str]:
    """The harness's own install: `sys.prefix` and its site-packages (where tanabesugano and the task data with
    references can live). Denied for B wherever they are installed."""
    out = [sys.prefix]
    try:
        out += list(site.getsitepackages())
    except AttributeError:  # pragma: no cover - site without getsitepackages
        pass
    return list(dict.fromkeys(out))


def _within(p: str, root: str) -> bool:
    try:
        return pathlib.Path(p).resolve().is_relative_to(pathlib.Path(root).resolve())
    except (OSError, ValueError):
        return False


def render_settings(repo: pathlib.Path | str = REPO_ROOT, home: pathlib.Path | str | None = None, *,
                    b_venv: pathlib.Path | str | None = None, mpl_dir: pathlib.Path | str | None = None,
                    harness: list[str] | None = None, parent_env=None) -> dict:
    """Fill in the repo and the real home. Every `~/...` entry is kept AND also listed with its absolute path in the
    *parent's* real home: the child runs with an isolated HOME, so a bare `~` resolves into the empty temp home.

    denyRead: repo, main checkout, the real home, the folder of the key file named by `parent_env`
    (`tsbench.core.keys`), the harness install (`harness_prefixes()`), and the site-packages of venv-B's base
    interpreter. allowRead (narrower, so it wins): venv-B, its base interpreter, the matplotlib cache.
    `b_venv`/`mpl_dir` default to the locations `b_stack` would use for `parent_env` (os.environ)."""
    parent_env = os.environ if parent_env is None else parent_env
    real_home = pathlib.Path(home) if home is not None else pathlib.Path("~").expanduser()
    if b_venv is None:
        try:
            b_venv = b_stack.b_venv_dir(parent_env, None, pathlib.Path(repo))
        except b_stack.BStackError:
            b_venv = None
    mpl = pathlib.Path(mpl_dir) if mpl_dir is not None else b_stack.mpl_dir(parent_env)
    harness = harness_prefixes() if harness is None else list(harness)

    allow: list[str] = []
    base_site: list[str] = []
    if b_venv is not None:
        allow.append(str(b_venv))
        for base in b_stack.base_dirs(pathlib.Path(b_venv)):
            allow.append(str(base))
            base_site += sorted(str(d) for d in base.glob("lib/python3*/site-packages"))
    allow.append(str(mpl))
    allow = list(dict.fromkeys(allow))
    for a in allow:
        if _within(a, str(repo)):
            raise ValueError(f"allowRead entry {a} lies inside the repo")
        for h in harness[1:]:  # the harness's site-packages: tanabesugano (and possibly the task data)
            if h and _within(a, h):
                raise ValueError(f"allowRead entry {a} lies inside the harness site-packages {h}")

    out = copy.deepcopy(SETTINGS_TEMPLATE)
    deny: list[str] = []
    for d in out["sandbox"]["filesystem"]["denyRead"]:
        if d == REPO_PLACEHOLDER:
            entries = [str(repo), *main_checkouts(repo)]
        elif d == REAL_HOME_PLACEHOLDER:
            entries = [str(real_home)]
        elif d == KEY_DIR_PLACEHOLDER:
            entries = keys.key_dir_entries(parent_env, real_home)
        else:
            entries = [d]
        if d.startswith("~/"):
            entries.append(str(real_home / d[2:]))
        deny += [e for e in entries if e not in deny]
    # the harness prefix itself is denied unless an allowed dir lies inside it (a harness installed straight into the
    # base interpreter): then only its site-packages are, which are narrower than that allow entry
    for h in harness:
        if h and h not in deny and not any(_within(a, h) for a in allow):
            deny.append(h)
    for h in harness[1:] + base_site:
        if h and h not in deny:
            deny.append(h)
    out["sandbox"]["filesystem"]["denyRead"] = deny
    out["sandbox"]["filesystem"]["allowRead"] = allow
    return out


def settings_text(repo: pathlib.Path | str = REPO_ROOT, home: pathlib.Path | str | None = None, **kw) -> str:
    return json.dumps(render_settings(repo, home, **kw), indent=2, sort_keys=True) + "\n"


def settings_sha256(repo: pathlib.Path | str = REPO_ROOT, home: pathlib.Path | str | None = None, **kw) -> str:
    return hashlib.sha256(settings_text(repo, home, **kw).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------- probe script and prompt
def existing_home_paths(real_home: pathlib.Path | str | None = None) -> dict[str, list[str]]:
    """Which of HOMECACHE_PATHS / HOMESECRETS_PATHS exist in the real home (checked with lstat in the parent, nothing is
    read). Relative names only: they go into the script and the probe record."""
    rh = pathlib.Path(real_home) if real_home is not None else pathlib.Path("~").expanduser()
    return {name: [p for p in paths if os.path.lexists(rh / p)]
            for name, paths in (("HOMECACHE", HOMECACHE_PATHS), ("HOMESECRETS", HOMESECRETS_PATHS))}


def missing_probe_targets(repo: pathlib.Path | str = REPO_ROOT) -> tuple[str, ...]:
    """Names of the PROBE_TARGETS that do not exist under `repo` (checked with stat in the parent, nothing is read)."""
    return tuple(name for name, rel in PROBE_TARGETS.items() if not (pathlib.Path(repo) / rel).exists())


def probe_script_lines(home_paths: dict[str, list[str]] | None = None,
                       missing_targets: tuple[str, ...] | None = None) -> list[str]:
    """The probe script. It holds no absolute host path: the repo and the real home reach it as $TSPROBE_REPO and
    $TSPROBE_RH in the probe's environment (PROBE_PATHS checks they arrived), so the transcript names neither. Every
    forbidden command has its output sent to /dev/null; only `PROBE_<NAME> rc=<n>` lines are printed."""
    home_paths = existing_home_paths() if home_paths is None else home_paths
    missing_targets = missing_probe_targets() if missing_targets is None else missing_targets
    q = "> /dev/null 2>&1"
    venv_py, task_file = PROBE_TARGETS["VENV"], PROBE_TARGETS["READ"]
    R, H = f'"${PROBE_ENV_REPO}"', f'"${PROBE_ENV_HOME}"'
    keys = "".join(f"${{{v}-}}" for v in KEY_VARS)
    lines = [
        'echo PROBE_CTRL1 rc=0; python3 -c "print(2+3)"; echo PROBE_CTRL2 rc=$?',
        f'[ -n "${{{PROBE_ENV_REPO}-}}" ] && [ -n "${{{PROBE_ENV_HOME}-}}" ] && [ "${PROBE_ENV_HOME}" != "$HOME" ]; '
        "echo PROBE_PATHS rc=$?",
        f'[ -z "{keys}" ]; echo PROBE_KEYENV rc=$?',
        f'python3 -c "import tanabesugano" {q}; echo PROBE_IMPORT rc=$?',
        f"python3 -m pip download --no-deps -d ./dl tanabesugano==2.0.0 {q}; echo PROBE_PIP rc=$?",
        f"curl -sS -m 10 https://pypi.org/simple/tanabesugano/ -o /dev/null {q}; echo PROBE_NET rc=$?",
        f'{R}/{venv_py} -c "import tanabesugano" {q}; echo PROBE_VENV rc=$?',
        f"cat {R}/{task_file} {q}; echo PROBE_READ rc=$?",
        f"command -v tanabesugano {q}; echo PROBE_TSBIN rc=$?",
        f"command -v tanabesugano-mcp {q}; echo PROBE_TSBIN rc=$?",
    ]
    for name in missing_targets:  # no marker: a command on a missing target would "fail" for the wrong reason
        lines = [f"# {name} not tested: {PROBE_TARGETS[name]} does not exist in the repository" if ln.endswith(
            f"echo PROBE_{name} rc=$?") else ln for ln in lines]
    for name, verb in (("HOMECACHE", "ls"), ("HOMESECRETS", None)):
        paths = home_paths.get(name) or []
        if not paths:  # nothing of the kind on this host; recorded as such in the probe record
            lines.append(f"false; echo PROBE_{name} rc=$?")
        for rel in paths:
            cmd = verb or ("ls" if rel == ".ssh" else "cat")
            lines.append(f'{cmd} {H}/{rel} {q}; echo PROBE_{name} rc=$?')
    lines += [
        f"curl -sS -m 5 {LOCALHOST_URL} -o /dev/null {q}; echo PROBE_LOCALHOST rc=$?",
        *[f"curl -sS -m 5 {h} -o /dev/null {q}; echo PROBE_APIHOST rc=$?" for h in API_HOSTS],
        f'python3 -c "import socket; socket.gethostbyname(\'{DNS_NAME}\')" {q}; echo PROBE_DNS rc=$?',
        # gating: B's python3 (first on PATH: the venv-B stack) must have the fixed scientific stack (H2 confound).
        # IMPORT above must still fail and PIP above must still fail: tanabesugano is not in venv-B and pip is absent
        'python3 -c "import numpy, scipy, sympy, matplotlib"; echo PROBE_NUMPY rc=$?',
        # B must be able to write a script with a heredoc and run it
        "cat > ./probe_heredoc.py <<'EOF'\n"
        "from math import factorial\n\n"
        "def tri(a, b, c):\n"
        "    return factorial(a + b - c) * factorial(a - b + c) / factorial(a + b + c + 1)\n\n"
        "print(tri(3, 2, 1))\n"
        "EOF\n"
        "python3 ./probe_heredoc.py; echo PROBE_HEREDOC rc=$?",
    ]
    return lines


def probe_script_sha256(home_paths: dict[str, list[str]] | None = None,
                        missing_targets: tuple[str, ...] | None = None) -> str:
    """sha256 of the probe script text (machine-independent apart from which home paths and targets exist)."""
    return hashlib.sha256("\n".join(probe_script_lines(home_paths, missing_targets)).encode("utf-8")).hexdigest()


def probe_script_template_sha256() -> str:
    """sha256 of the script with every candidate home path in it: the same on every host, so it can be a plan pin."""
    return probe_script_sha256({"HOMECACHE": list(HOMECACHE_PATHS), "HOMESECRETS": list(HOMESECRETS_PATHS)}, ())


def probe_env(repo: pathlib.Path | str, real_home: pathlib.Path | str | None = None) -> dict[str, str]:
    """The extra environment of the probe call (and only of it)."""
    rh = pathlib.Path(real_home) if real_home is not None else pathlib.Path("~").expanduser()
    return {PROBE_ENV_REPO: str(repo), PROBE_ENV_HOME: str(rh)}


def localhost_listening(url: str = LOCALHOST_URL, timeout_s: float = 1.0) -> bool:
    """Whether something accepts TCP on the LOCALHOST probe's port, seen from the parent (LOCALHOST proves a closed
    loopback only while something listens there)."""
    from urllib.parse import urlparse

    u = urlparse(url)
    try:
        with socket.create_connection((u.hostname, u.port or 80), timeout=timeout_s):
            return True
    except OSError:
        return False


def probe_prompt(home_paths: dict[str, list[str]] | None = None, missing_targets: tuple[str, ...] | None = None) -> str:
    script = "\n".join(probe_script_lines(home_paths, missing_targets))
    return (
        "Use the Bash tool exactly once, in a single call, to run the shell script below verbatim. "
        "Do not modify it, do not split it and do not run anything else. "
        "When it has finished, reply with the single word: done\n\n"
        f"```bash\n{script}\n```\n"
    )


# ---------------------------------------------------------------- transcript evaluation
def _tool_result_texts(events: list[dict]) -> list[str]:
    texts: list[str] = []
    for ev in events:
        if not isinstance(ev, dict) or ev.get("type") != "user":
            continue
        content = (ev.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_result":
                continue
            c = block.get("content")
            if isinstance(c, str):
                texts.append(c)
            elif isinstance(c, list):
                texts.extend(b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text")
    return texts


def parse_markers(events: list[dict]) -> dict[str, list[int]]:
    """Marker name -> every rc printed, taken from tool_result content only."""
    found: dict[str, list[int]] = {}
    for text in _tool_result_texts(events):
        for name, rc in MARKER_RE.findall(text):
            found.setdefault(name, []).append(int(rc))
    return found


ESCAPE_KEY = "dangerouslyDisableSandbox"


def asks_to_escape(tool_input: object) -> bool:
    """True when a tool_use input asks to leave the sandbox: the escape flag set to anything but false, or the flag's
    name anywhere else in the input. Some models send the flag as false with every Bash call; that asks for nothing."""
    if not isinstance(tool_input, dict):
        return ESCAPE_KEY in json.dumps(tool_input)
    rest = {k: v for k, v in tool_input.items() if k != ESCAPE_KEY}
    if ESCAPE_KEY in json.dumps(rest):
        return True
    if ESCAPE_KEY not in tool_input:
        return False
    value = tool_input[ESCAPE_KEY]
    return value is not None and str(value).strip().lower() not in ("false", "0", "")


def escape_requested(events: list[dict]) -> bool:
    for ev in events:
        if isinstance(ev, dict) and ev.get("type") == "assistant":
            for block in (ev.get("message") or {}).get("content") or []:
                if isinstance(block, dict) and block.get("type") == "tool_use" \
                        and asks_to_escape(block.get("input", {})):
                    return True
    return False


ZERO_HINTS = {
    "CTRL1": "Bash or python3 unusable inside the sandbox",
    "NUMPY": "the venv-B stack is not readable inside the sandbox or not first on PATH",
    "KEYENV": "a model credential is visible in B's Bash environment; see docs/methods.md (sandbox) for the "
              "documented mitigations",
    "PATHS": "the probe's TSPROBE_* variables did not reach the Bash tool; the path markers would be vacuous",
}


def evaluate(markers: dict[str, list[int]], init_problems: list[str], escaped: bool,
             not_tested: tuple[str, ...] = ()) -> tuple[bool, list[str]]:
    """`not_tested`: markers whose target is missing (`missing_probe_targets`). They are never counted as passed, and a
    probe with one is not a pass."""
    reasons: list[str] = [f"{name} not tested: {PROBE_TARGETS[name]} does not exist in the repository"
                          for name in not_tested]
    for name in MUST_BE_ZERO:
        rcs = markers.get(name)
        if not rcs:
            reasons.append(f"{name} missing: Bash did not run the script")
        elif any(rc != 0 for rc in rcs):
            reasons.append(f"{name} rc={rcs}, expected 0 ({ZERO_HINTS.get(name, ZERO_HINTS['CTRL1'])})")
    for name in MUST_FAIL:
        if name in not_tested:
            continue
        rcs = markers.get(name)
        if not rcs:
            reasons.append(f"{name} missing")
        elif any(rc == 0 for rc in rcs):
            reasons.append(f"{name} rc={rcs}: the forbidden action succeeded")
    if escaped:
        reasons.append("a tool_use asked for dangerouslyDisableSandbox")
    if init_problems:
        reasons.append("init check failed: " + "; ".join(init_problems))
    return (not reasons), reasons


def evaluate_transcript(events: list[dict], model: str, not_tested: tuple[str, ...] = ()) -> dict:
    # the first non-"system/<other>" event; claude may emit e.g. system/ui_invalidate before init
    init = next((e for e in events if isinstance(e, dict)
                 and not (e.get("type") == "system" and e.get("subtype") != "init")), {})
    init_problems = conditions.check_init(conditions.get("B"), init, model)
    markers = parse_markers(events)
    escaped = escape_requested(events)
    passed, reasons = evaluate(markers, init_problems, escaped, not_tested)
    return {"passed": passed, "reasons": reasons, "markers": markers, "init_mismatches": init_problems,
            "escape_requested": escaped}


# ---------------------------------------------------------------- method choice
def detect_container() -> str | None:
    for tool in ("docker", "podman"):
        if shutil.which(tool):
            return tool
    return None


def method_info(probe: dict | None, dry_run: bool) -> dict:
    """The sandbox block of the manifest."""
    if dry_run:
        return {"method": "dry-run (not probed)", "reason": None, "container": None, "probe": None}
    if probe is None:
        return {"method": "not yet probed", "reason": None, "container": None, "probe": None}
    passed = probe.get("passed", False)
    if passed is None:  # the probe could not be evaluated (an API error), which says nothing about the sandbox
        return {"method": "not evaluable",
                "reason": "sandbox probe not evaluable: " + "; ".join(probe.get("reasons", [])),
                "container": None, "probe": probe}
    if passed:
        return {"method": "builtin", "reason": None, "container": None, "probe": probe}
    tool = detect_container()
    container = (f"{tool} found; not built: only used if builtin fails" if tool
                 else "no docker/podman on PATH; not built: only used if builtin fails")
    return {"method": "skipped", "reason": "builtin sandbox probe failed: " + "; ".join(probe.get("reasons", [])),
            "container": container, "probe": probe}


# ---------------------------------------------------------------- running the probe
def auth_mode(session) -> str:
    return "gateway" if getattr(session, "gateway", False) else "direct"


def session_settings_sha256(session) -> str:
    """The hash of the settings file the session really wrote (falls back to the default rendering)."""
    sha = getattr(session, "settings_sha256", None)
    return sha if isinstance(sha, str) else settings_sha256(session.repo)


def load_reusable_probe(out_dir: pathlib.Path, claude_version: str, settings_hash: str,
                        b_stack_sha256: str | None = None, *, script_sha256: str | None = None,
                        auth: str | None = None) -> dict | None:
    """A passing, non-fake probe record for this claude version, these settings, this B stack digest, this probe script
    (default: the one this host would run) and, when given, this auth mode (KEYENV tests a different variable each)."""
    path = pathlib.Path(out_dir) / PROBE_FILENAME
    try:
        rec = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    script_sha256 = probe_script_sha256() if script_sha256 is None else script_sha256
    if (isinstance(rec, dict) and rec.get("passed") is True and not rec.get("fake")
            and rec.get("claude_version") == claude_version and rec.get("settings_sha256") == settings_hash
            and rec.get("b_stack_sha256") == b_stack_sha256 and rec.get("probe_script_sha256") == script_sha256
            and (auth is None or rec.get("auth_mode") == auth)):
        return rec
    return None


# ---------------------------------------------------------------- CLI