"""Repository hygiene: no empty folders in the code tree, and a .gitignore that lists the caches and the default output
the tools leave behind and guards the private folders.

Test data under tests/fixtures is not checked for these names.
"""
from __future__ import annotations

import ast
import os
import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
CODE_DIRS = ("src", "tests", "tools", "contrib")
DATA_PREFIXES = ("tests/fixtures/",)
THIS_FILE = pathlib.Path(__file__).resolve().relative_to(ROOT).as_posix()
REQUIRED_IGNORES = (".import_linter_cache/", "*.egg-info/", ".pytest_cache/", "build/")
# the default output of `tsbench doctor` and `tsbench run` (runs/) and of the stats commands, in the top folder
OUTPUT_IGNORES = ("/runs/", "/hypotheses.json", "/power.csv")
# folders of private material: git ignores them, and `tsbench release gate` refuses them when tracked
PRIVATE_IGNORES = ("pilot/", "seed/", "analysis/", ".claude/", ".env")


def _empty_dirs(top: pathlib.Path) -> list[str]:
    """Folders with no entries, where a __pycache__ folder does not count as an entry."""
    found = []
    for dirpath, dirnames, _ in os.walk(top):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        entries = [name for name in os.listdir(dirpath) if name != "__pycache__"]
        if not entries:
            found.append(pathlib.Path(dirpath).relative_to(ROOT).as_posix())
    return found


def _tracked_files() -> list[str]:
    listing = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, text=True, check=True,
                             encoding="utf-8")
    return [name for name in listing.stdout.split("\0") if name]


def test_no_empty_directories():
    found = []
    for name in CODE_DIRS:
        found.extend(_empty_dirs(ROOT / name))
    assert found == []


# Text that points a reader to something a clone does not have: a file name of the form `NN-name.md`, a requirement id
# (`R12` in a comment, `test_rNN_` in a test name), or the literature tables outside their folder. The comment test of
# the report names the file name shape as a marker it scans for.
SPEC_MARKER_TEST = "tests/report/test_comments.py"
UNREACHABLE = (
    re.compile(r"\b\d{2}-[a-z][a-z-]*\.md\b"),
    re.compile(r"\btest_r\d{1,2}_"),
    re.compile(r"(?:#|\()\s*R\d{1,2}\b|\bR\d{1,2} to R\d{1,2}\b|\bR\d{1,2}, R\d{1,2}\b"),
    re.compile(r"data/literature-spectra"),
)


def test_no_tracked_code_or_test_cites_a_spec_a_clone_does_not_have():
    found = []
    for name in _tracked_files():
        if name in (THIS_FILE, SPEC_MARKER_TEST) or name.startswith(DATA_PREFIXES):
            continue
        if not name.startswith(("src/", "tests/")):
            continue
        if not name.endswith((".py", ".j2", ".js", ".css", ".md")) or "/_vendor/" in name or "/data/" in name:
            continue
        path = ROOT / name
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        found.extend(f"{name}: {m.group(0)}" for rx in UNREACHABLE for m in rx.finditer(text))
    assert found == []


def _gitignore_lines() -> set[str]:
    return {line.strip() for line in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()}


def test_gitignore_lists_tool_caches():
    missing = [pattern for pattern in REQUIRED_IGNORES if pattern not in _gitignore_lines()]
    assert missing == []


def test_gitignore_lists_the_default_output_of_the_tools():
    missing = [pattern for pattern in OUTPUT_IGNORES if pattern not in _gitignore_lines()]
    assert missing == []


def test_gitignore_guards_the_private_folders():
    missing = [pattern for pattern in PRIVATE_IGNORES if pattern not in _gitignore_lines()]
    assert missing == []


def _export_ignore(*paths: str) -> dict[str, str]:
    out = subprocess.run(["git", "check-attr", "export-ignore", "--", *paths], cwd=ROOT, capture_output=True, text=True,
                         check=True, encoding="utf-8").stdout
    return {line.split(": ")[0]: line.split(": ")[-1] for line in out.splitlines()}


def test_release_archive_leaves_out_the_gitleaks_fingerprints():
    """`git archive` builds the release copy: the commit-bound fingerprints of .gitleaksignore stay out of it."""
    attrs = _export_ignore(".gitleaksignore", "README.md", "docs/.gitleaksignore")
    assert attrs == {".gitleaksignore": "set", "README.md": "unspecified", "docs/.gitleaksignore": "unspecified"}


def _unguarded_empty_array_expansions(text: str) -> list[str]:
    """Names of arrays declared empty (`NAME=()`) and later expanded as a bare `"${NAME[@]}"`. Under `set -u` that is an
    "unbound variable" error in bash before 4.4 (macOS /bin/bash 3.2); the safe form is `${NAME[@]+"${NAME[@]}"}`."""
    names = re.findall(r"^\s*(\w+)=\(\s*\)", text, re.MULTILINE)
    return [n for n in names if re.search(rf'(?<![+\w])"\${{{n}\[@\]}}"', text)]


def test_shell_tools_expand_empty_arrays_in_the_bash_3_2_safe_form():
    bad = {}
    for path in sorted((ROOT / "tools").rglob("*.sh")):
        names = _unguarded_empty_array_expansions(path.read_text(encoding="utf-8"))
        if names:
            bad[path.relative_to(ROOT).as_posix()] = names
    assert bad == {}


def test_the_empty_array_scan_tells_the_guarded_form_from_the_bare_one():
    assert _unguarded_empty_array_expansions('A=()\necho "${A[@]}"\n') == ["A"]
    assert _unguarded_empty_array_expansions('A=()\necho ${A[@]+"${A[@]}"}\n') == []
    assert _unguarded_empty_array_expansions('A=(x)\necho "${A[@]}"\n') == []


# ------------------------------------------------------------------ text I/O names its encoding
def _call_name(call: ast.Call) -> str | None:
    f = call.func
    return f.attr if isinstance(f, ast.Attribute) else f.id if isinstance(f, ast.Name) else None


def _text_io_without_encoding(source: str) -> list[int]:
    """Lines of calls that read or write text and leave the encoding to the locale: `read_text`/`write_text`, the
    builtin `open` in text mode, and `subprocess` calls in text mode. Ruff's PLW1514 does not see most of these (the
    receiver type of `.write_text` is unknown to it, and it ignores `subprocess`)."""
    lines = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call) or any(k.arg == "encoding" or k.arg is None for k in node.keywords):
            continue
        name, kws = _call_name(node), {k.arg: k.value for k in node.keywords}
        if name in ("read_text", "write_text"):
            lines.append(node.lineno)
        elif name == "open" and isinstance(node.func, ast.Name):
            mode = node.args[1] if len(node.args) > 1 else kws.get("mode")
            if not (isinstance(mode, ast.Constant) and "b" in str(mode.value)):
                lines.append(node.lineno)
        elif isinstance(node.func, ast.Attribute) and getattr(node.func.value, "id", "") == "subprocess":
            text_mode = "text" in kws or "universal_newlines" in kws
            if name in ("run", "Popen", "check_output", "check_call") and text_mode:
                lines.append(node.lineno)
    return sorted(lines)


def test_the_text_io_scan_tells_a_named_encoding_from_a_missing_one():
    src = (
        "import subprocess\n"
        "p.write_text('x')\n"                                                   # 2: missing
        "p.read_text(encoding='utf-8')\n"
        "open('f')\n"                                                          # 4: text mode
        "open('f', 'rb')\n"
        "open('f', 'w', encoding='utf-8')\n"
        "subprocess.run(['x'], capture_output=True, text=True)\n"              # 7: text mode
        "subprocess.run(['x'], capture_output=True, text=True, encoding='utf-8')\n"
        "subprocess.run(['x'], capture_output=True)\n"
        "subprocess.run(['x'], **kw)\n"
    )
    assert _text_io_without_encoding(src) == [2, 4, 7]


def test_every_text_read_and_write_names_its_encoding():
    found = []
    for name in CODE_DIRS:
        for path in sorted((ROOT / name).rglob("*.py")):
            if "__pycache__" in path.parts or "_vendor" in path.parts:
                continue
            found.extend(f"{path.relative_to(ROOT).as_posix()}:{n}"
                         for n in _text_io_without_encoding(path.read_text(encoding="utf-8")))
    assert found == []


def test_a_module_that_uses_the_std_streams_sets_them_to_utf_8():
    """`sys.stdin.read()` and `sys.stdout.write()` decode with the locale unless the module reconfigures them."""
    bad = []
    for path in sorted((ROOT / "src").rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        if re.search(r"sys\.stdin\.read|sys\.stdout\.write", text) and "use_utf8_streams" not in text:
            bad.append(path.relative_to(ROOT).as_posix())
    assert bad == []
