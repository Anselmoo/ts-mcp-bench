"""The layer rule of the package: a stage imports only stages below it, never a sibling in its own layer.

    cli > release > figures, report > stats > run, score > plan > tasks, conditions > core

Read from the source of the installed package with `ast` (function-local imports included), so the rule holds for every
import, not only the top-level ones. Failure messages name modules.

`tsbench.run.fake_cli` (the fake `claude` of `--dry-run`) is started by the runner as a subprocess by module name: no
other module imports it.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

import tsbench

ROOT = pathlib.Path(tsbench.__file__).resolve().parent
LAYERS = [["core"], ["tasks", "conditions"], ["plan"], ["run", "score"], ["stats"], ["figures", "report"], ["release"],
          ["cli"]]
LEVEL = {name: i for i, names in enumerate(LAYERS) for name in names}
# outside the pipeline: checked only for not being imported (_vendor: see below)
OUTSIDE = {"_vendor"}
# modules that run as their own process: nothing imports them
STANDALONE = {"tsbench.run.fake_cli"}


def stage_of(module: str) -> str | None:
    """`tsbench.<stage>...` -> stage; the package root modules (`tsbench.cli`) are their own stage."""
    parts = module.split(".")
    return parts[1] if len(parts) > 1 and parts[0] == "tsbench" else None


def modules() -> list[tuple[str, pathlib.Path]]:
    out = []
    for path in sorted(ROOT.rglob("*.py")):
        rel = path.relative_to(ROOT.parent).with_suffix("")
        if "__pycache__" in path.parts:
            continue
        name = ".".join(rel.parts).removesuffix(".__init__")
        out.append((name, path))
    return out


def imported(path: pathlib.Path, module: str) -> set[str]:
    out = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            out |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:  # relative import: resolve against the importing package
                parts = module.split(".")
                pkg = parts[: -node.level] if path.name != "__init__.py" else parts[: len(parts) - node.level + 1]
                base = ".".join(pkg + ([base] if base else []))
            out.add(base)
            out |= {f"{base}.{a.name}" for a in node.names}
    return {m for m in out if m.startswith("tsbench.")}


def violations() -> list[str]:
    bad = []
    for name, path in modules():
        src = stage_of(name)
        if src is None or src in OUTSIDE:
            continue
        for dep in imported(path, name):
            if dep in STANDALONE:
                bad.append(f"{name} imports {dep} (a standalone module: the runner starts it as a subprocess)")
                continue
            dst = stage_of(dep)
            if dst is None or dst == src or dst not in LEVEL and dst not in OUTSIDE:
                continue
            # the vendored Figura design system draws figures and pages
            if dst == "_vendor" and src in ("figures", "report"):
                continue
            if dst in OUTSIDE:
                bad.append(f"{name} imports {dep} (production code never imports {dst})")
            elif dst in LEVEL and src in LEVEL and LEVEL[dst] >= LEVEL[src]:
                bad.append(f"{name} imports {dep} ({src} may import only layers below it)")
    return sorted(set(bad))


def test_every_stage_imports_only_lower_stages():
    assert violations() == []


def test_production_code_never_imports_testing():
    users = sorted(name for name, path in modules() if STANDALONE & imported(path, name))
    assert users == []
    assert (ROOT / "run" / "fake_cli.py").is_file()  # the check looks at the real package, not a missing one


def test_an_import_of_testing_is_reported(tmp_path, monkeypatch):
    fake = tmp_path / "tsbench" / "stats" / "leak.py"
    fake.parent.mkdir(parents=True)
    fake.write_text("from tsbench.run import fake_cli\n", encoding="utf-8")
    assert imported(fake, "tsbench.stats.leak") >= {"tsbench.run", "tsbench.run.fake_cli"}
    monkeypatch.setitem(globals(), "modules", lambda: [("tsbench.stats.leak", fake)])
    assert violations() == [
        "tsbench.stats.leak imports tsbench.run.fake_cli "
        "(a standalone module: the runner starts it as a subprocess)",
    ]


def test_the_rule_is_not_vacuous():
    names = [n for n, _ in modules()]
    assert len(names) > 40 and "tsbench.run.runner" in names
    assert {stage_of(n) for n in names} >= set(LEVEL) - {"cli"} | {"core"}


@pytest.mark.parametrize(
    "src,dst,ok",
    [
        ("plan", "run", False), ("run", "plan", True), ("score", "stats", False),
        ("report", "figures", False), ("stats", "score", True), ("tasks", "conditions", False),
    ],
)
def test_layer_order(src, dst, ok):
    assert (LEVEL[dst] < LEVEL[src]) is ok


def test_outside_names_only_stages_that_exist():
    """Every name in the outside list is a folder of the package; a stale entry would hide an import of a package that
    later appears under that name."""
    assert sorted(n for n in OUTSIDE if not (ROOT / n).is_dir()) == []
