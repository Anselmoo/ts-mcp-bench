"""The fixed scientific Python stack of condition B.

B's only tool is Bash, so "what python3 is" decides what the code interpreter can do. Instead of whatever the host has,
B gets a dedicated virtualenv outside the repo (default `~/.cache/tsbench/venv-B`, override `--b-venv` or
TSBENCH_B_VENV) holding exactly the packages in `data/conditions/b-stack.txt` (numpy, scipy, sympy, matplotlib and their
pinned dependencies) and NEVER `tanabesugano`. It is created with `python -m venv --without-pip` (no pip inside) and
filled from outside with `uv pip install --python <venv>/bin/python -r b-stack.txt`. Its base interpreter is a
uv-managed Python of the pinned minor installed into `~/.cache/tsbench/python` (override TSBENCH_PYTHON_DIR), not uv's
default `~/.local/share/uv/python`: re-opening a directory under `~/.local` for the sandbox would make `~/.local`
listable inside B on Linux.

    tsbench env b-stack            # create or repair, validate, print path and digest
    tsbench env b-stack --check    # validate only, never creates or installs

`ensure_b_stack()` is idempotent. The digest is sha256 over the pin file and the sorted `name==version` listing of what
is really installed (importlib.metadata run by the venv's own python).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

from tsbench.core import resource

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
PIN_FILE = resource("conditions/b-stack.txt")
FORBIDDEN = ("tanabesugano",)
REQUIRED_IMPORTS = ("numpy", "scipy", "sympy", "matplotlib")
PIN_RE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==([A-Za-z0-9][A-Za-z0-9.!+_-]*)$")
PYTHON_MINOR_RE = re.compile(r"^#\s*python-minor:\s*(\d+\.\d+)\s*$")
_LIST_PACKAGES = ("import importlib.metadata as m, json; "
                  "print(json.dumps({d.metadata['Name']: d.version for d in m.distributions()}))")


class BStackError(RuntimeError):
    """The B stack is missing, wrong, or unsafe."""


class ForbiddenPackageError(BStackError):
    """tanabesugano is importable in the B venv: never repaired automatically."""


def normalize_package_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


# ------------------------------------------------------------------ location
def b_venv_dir(parent_env=None, override: str | None = None, repo: pathlib.Path = REPO_ROOT) -> pathlib.Path:
    """`override` (--b-venv), else TSBENCH_B_VENV, else `<XDG_CACHE_HOME or ~/.cache>/tsbench/venv-B`.
    Never inside the repo."""
    parent_env = os.environ if parent_env is None else parent_env
    if override:
        d = pathlib.Path(override).expanduser()
    elif parent_env.get("TSBENCH_B_VENV"):
        d = pathlib.Path(parent_env["TSBENCH_B_VENV"]).expanduser()
    else:
        base = parent_env.get("XDG_CACHE_HOME") or pathlib.Path(parent_env.get("HOME") or "~").expanduser() / ".cache"
        d = pathlib.Path(base) / "tsbench" / "venv-B"
    d = d.absolute()
    if d.resolve().is_relative_to(pathlib.Path(repo).resolve()):
        raise BStackError(f"B venv {d} lies inside the repo; set TSBENCH_B_VENV / --b-venv elsewhere")
    return d


def bin_dir(venv: pathlib.Path) -> pathlib.Path:
    return pathlib.Path(venv) / "bin"


def mpl_dir(parent_env=None) -> pathlib.Path:
    """The persistent matplotlib cache shared by C's MCP server and B's python: TSBENCH_MPLCONFIGDIR, else
    `<XDG_CACHE_HOME or ~/.cache>/tsbench/matplotlib`. The sandbox re-opens it for reading inside the denied home."""
    parent_env = os.environ if parent_env is None else parent_env
    if parent_env.get("TSBENCH_MPLCONFIGDIR"):
        return pathlib.Path(parent_env["TSBENCH_MPLCONFIGDIR"]).expanduser().absolute()
    base = parent_env.get("XDG_CACHE_HOME") or pathlib.Path(parent_env.get("HOME") or "~").expanduser() / ".cache"
    return (pathlib.Path(base) / "tsbench" / "matplotlib").absolute()


def python_dir(parent_env=None) -> pathlib.Path:
    """Where B's base interpreter is installed: TSBENCH_PYTHON_DIR, else `<XDG_CACHE_HOME or ~/.cache>/tsbench/python`.
    Under the same parent as venv-B and the matplotlib cache, so the sandbox re-opens nothing under `~/.local`."""
    parent_env = os.environ if parent_env is None else parent_env
    if parent_env.get("TSBENCH_PYTHON_DIR"):
        return pathlib.Path(parent_env["TSBENCH_PYTHON_DIR"]).expanduser().absolute()
    base = parent_env.get("XDG_CACHE_HOME") or pathlib.Path(parent_env.get("HOME") or "~").expanduser() / ".cache"
    return (pathlib.Path(base) / "tsbench" / "python").absolute()


def base_dirs(venv: pathlib.Path) -> list[pathlib.Path]:
    """The base interpreter the venv's python links to (the `home =` line of pyvenv.cfg, minus its `bin`), as written
    and resolved. B's python3 must read its stdlib there, so the sandbox re-opens these dirs inside the denied home.
    Read from the file, never by running anything, so that the rendered sandbox settings are deterministic. Empty when
    the venv does not exist yet."""
    try:
        text = (pathlib.Path(venv) / "pyvenv.cfg").read_text(encoding="utf-8")
    except OSError:
        return []
    for line in text.splitlines():
        key, _, value = line.partition("=")
        if key.strip() == "home" and value.strip():
            home_bin = pathlib.Path(value.strip())
            base = home_bin.parent if home_bin.name == "bin" else home_bin
            out = [base]
            real = base.resolve()
            if real != base:
                out.append(real)
            return out
    return []


def python_of(venv: pathlib.Path) -> pathlib.Path:
    return bin_dir(venv) / "python"


# ------------------------------------------------------------------ pins
def parse_pins(text: str) -> tuple[dict[str, str], str | None]:
    """(normalised name -> version, python minor from the `#python-minor:` line). Raises BStackError on anything that is
    not an exact `==` pin, a duplicate, or a forbidden package."""
    pins: dict[str, str] = {}
    minor = None
    for n, line in enumerate(text.splitlines(), 1):
        s = line.strip()
        if not s:
            continue
        m = PYTHON_MINOR_RE.match(s)
        if m:
            minor = m.group(1)
            continue
        if s.startswith("#"):
            continue
        m = PIN_RE.match(s)
        if not m:
            raise BStackError(f"b-stack.txt line {n}: {s!r} is not an exact name==version pin")
        name = normalize_package_name(m.group(1))
        if name in FORBIDDEN:
            raise BStackError(f"b-stack.txt line {n}: {name} must never be in the B stack")
        if name in pins:
            raise BStackError(f"b-stack.txt line {n}: {name} pinned twice")
        pins[name] = m.group(2)
    for req in REQUIRED_IMPORTS:
        if req not in pins:
            raise BStackError(f"b-stack.txt does not pin {req}")
    return pins, minor


def load_pins(pin_file: pathlib.Path = PIN_FILE) -> tuple[dict[str, str], str | None]:
    try:
        return parse_pins(pathlib.Path(pin_file).read_text(encoding="utf-8"))
    except OSError as e:
        raise BStackError(f"cannot read {pin_file}: {e}") from e


# ------------------------------------------------------------------ digest
def stack_digest(pin_text: str, packages: dict[str, str]) -> str:
    """sha256 over the pin file and the `pip freeze`-style listing of the installed packages
    (sorted, normalised names)."""
    normalized = sorted((normalize_package_name(n), v) for n, v in packages.items())
    listing = "\n".join(f"{n}=={v}" for n, v in normalized)
    return hashlib.sha256((pin_text + "\n--installed--\n" + listing + "\n").encode("utf-8")).hexdigest()


def _run(cmd, **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", **kw)


def installed_packages(venv: pathlib.Path, run=_run) -> dict[str, str]:
    r = run([str(python_of(venv)), "-I", "-c", _LIST_PACKAGES], timeout=120)
    if r.returncode != 0:
        raise BStackError(f"cannot list packages of {venv}: {r.stderr.strip()[-200:]}")
    return {normalize_package_name(k): v for k, v in json.loads(r.stdout).items()}


def python_version(venv: pathlib.Path, run=_run) -> str:
    r = run([str(python_of(venv)), "-I", "-c", "import platform; print(platform.python_version())"], timeout=60)
    if r.returncode != 0:
        raise BStackError(f"cannot run {python_of(venv)}: {r.stderr.strip()[-200:]}")
    return r.stdout.strip()


# ------------------------------------------------------------------ validation
def validate(venv: pathlib.Path, pin_file: pathlib.Path = PIN_FILE, run=_run) -> dict:
    """Describe a valid venv or raise BStackError: installed versions equal the pins, python has the pinned minor,
    `import tanabesugano` FAILS, and numpy, scipy, sympy, matplotlib import."""
    venv = pathlib.Path(venv)
    pins, minor = load_pins(pin_file)
    py = python_of(venv)
    if not py.exists():
        raise BStackError(f"{venv} has no bin/python")
    pyver = python_version(venv, run)
    if minor and ".".join(pyver.split(".")[:2]) != minor:
        raise BStackError(f"python {pyver} in {venv}, the pin file wants {minor}")
    have = installed_packages(venv, run)
    for bad in FORBIDDEN:
        if bad in have:
            raise ForbiddenPackageError(
                f"{bad} {have[bad]} is installed in {venv}; B must not have it (delete the venv and re-run)"
            )
    problems = [f"{n}: pinned {v}, installed {have.get(n, 'missing')}" for n, v in pins.items() if have.get(n) != v]
    if problems:
        raise BStackError("installed packages differ from the pins: " + "; ".join(problems))
    r = run([str(py), "-I", "-c", "import tanabesugano"], timeout=120)
    if r.returncode == 0:
        raise ForbiddenPackageError(f"`import tanabesugano` succeeds in {venv}; B must not have it")
    r = run([str(py), "-I", "-c", "import " + ", ".join(REQUIRED_IMPORTS)], timeout=300)
    if r.returncode != 0:
        raise BStackError(f"importing {', '.join(REQUIRED_IMPORTS)} fails in {venv}: {r.stderr.strip()[-200:]}")
    return describe(venv, pin_file, pyver, have)


def describe(venv: pathlib.Path, pin_file: pathlib.Path = PIN_FILE, pyver: str | None = None,
             packages: dict[str, str] | None = None) -> dict:
    """The `b_stack` block of the manifest: path, python, packages, digest (+ the bin dir)."""
    packages = installed_packages(venv) if packages is None else packages
    return {"path": str(venv), "bin": str(bin_dir(venv)), "python": pyver or python_version(venv),
            "packages": dict(sorted(packages.items())),
            "digest": stack_digest(pathlib.Path(pin_file).read_text(encoding="utf-8"), packages)}


def digest_if_present(venv: pathlib.Path, pin_file: pathlib.Path = PIN_FILE) -> str | None:
    """Digest of a valid existing venv, None if there is none or it is not valid. Never creates anything."""
    try:
        return validate(venv, pin_file)["digest"]
    except BStackError:
        return None


# ------------------------------------------------------------------ creation
def _base_python(pin_minor: str | None) -> str:
    """A uv-managed Python `pin_minor` in `python_dir()`, installed there if missing. Nothing else qualifies:
    a host or `~/.local` interpreter would put a re-opened directory outside the tsbench cache."""
    if not pin_minor:
        raise BStackError("the pin file names no python minor; B's base interpreter cannot be chosen")
    uv = shutil.which("uv")
    if uv is None:
        raise BStackError("uv not found on PATH; it installs B's base interpreter")
    env = {**os.environ, "UV_PYTHON_INSTALL_DIR": str(python_dir())}
    cands: list[pathlib.Path] = []
    r = _run([uv, "python", "install", "--no-bin", pin_minor], timeout=900, env=env)  # no shim in ~/.local/bin
    if r.returncode != 0:
        raise BStackError(
            f"uv python install {pin_minor} into {python_dir()} failed: {(r.stderr or r.stdout).strip()[-300:]}"
        )
    r = _run([uv, "python", "find", "--managed-python", pin_minor], timeout=60, env=env)
    if r.returncode == 0 and r.stdout.strip():
        found = pathlib.Path(r.stdout.strip())
        if found.resolve().is_relative_to(python_dir().resolve()):
            cands.append(found)
    for c in cands:
        if not c.exists():
            continue
        r = _run([str(c), "-c", "import sys; print('%d.%d' % sys.version_info[:2])"], timeout=60)
        if r.returncode == 0 and (pin_minor is None or r.stdout.strip() == pin_minor):
            # resolved: uv's `cpython-3.14-…` is a symlink to `cpython-3.14.8-…`; bubblewrap re-opens an allowRead path
            # by its target only, so a venv linked through the minor-version link has a dangling python inside B
            return str(c.resolve())
    raise BStackError(
        f"no python {pin_minor} found in {python_dir()} (tried {', '.join(map(str, cands)) or 'nothing'})"
    )


def ensure_b_stack(venv: pathlib.Path | str | None = None, pin_file: pathlib.Path = PIN_FILE, *, create: bool = True,
                   run=_run) -> dict:
    """Create the venv if needed, install the pins from outside it, validate, and return
    {path, bin, python, packages, digest}. Idempotent: a valid venv is only validated. A venv with `tanabesugano`
    in it is never repaired (BStackError); one with wrong pins is reinstalled once."""
    venv = b_venv_dir() if venv is None else pathlib.Path(venv)
    try:
        return validate(venv, pin_file, run)
    except ForbiddenPackageError:
        raise
    except BStackError:
        if not create:
            raise
    pins, minor = load_pins(pin_file)
    uv = shutil.which("uv")
    if uv is None:
        raise BStackError("uv not found on PATH; it installs the B stack from outside the venv")
    if not python_of(venv).exists():
        venv.parent.mkdir(parents=True, exist_ok=True)
        r = run([_base_python(minor), "-m", "venv", "--without-pip", str(venv)], timeout=300)
        if r.returncode != 0:
            raise BStackError(f"venv creation failed: {r.stderr.strip()[-300:]}")
    r = run([uv, "pip", "install", "--python", str(python_of(venv)), "-r", str(pin_file)], timeout=1800)
    if r.returncode != 0:
        raise BStackError(f"uv pip install failed: {(r.stderr or r.stdout).strip()[-400:]}")
    return validate(venv, pin_file, run)


# ------------------------------------------------------------------ CLI
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="tsbench env b-stack", description=__doc__.splitlines()[0])
    ap.add_argument("--venv", default=None, help="B venv (default: $TSBENCH_B_VENV or ~/.cache/tsbench/venv-B)")
    ap.add_argument("--check", action="store_true", help="validate only; never create or install")
    ap.add_argument("--json", action="store_true", help="print the description as JSON")
    a = ap.parse_args(argv)
    try:
        venv = b_venv_dir(None, a.venv)
        info = ensure_b_stack(venv, create=not a.check)
    except BStackError as e:
        print(f"b_stack: {e}", file=sys.stderr)
        return 1
    if a.json:
        print(json.dumps(info, indent=2, sort_keys=True))
    else:
        print(f"B stack OK: {info['path']}\n  python {info['python']}\n  digest {info['digest']}\n  "
              + ", ".join(f"{k}=={v}" for k, v in info["packages"].items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
