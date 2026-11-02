"""The provenance page of a functional test: what each step ran, read and wrote, and whether the files fit together.

    tsbench report provenance --steps OUT/steps.jsonl --trace OUT/trace --out OUT/provenance.html [--prov PATH]

Inputs: `steps.jsonl` (the steps of tools/functional_test.sh) and the trace records of `tsbench.core.trace`, one folder
per step (`OUT/trace/<step>/*.trace.json`). The page has a verdict (is the hash chain intact?), then one section per
step: its command, per traced process a collapsible call tree, and the files it read and wrote with their sha256. An
input links to the output that an earlier process wrote. Besides the page the command writes the same facts as
PROV-JSON (default: the page name with `.prov.json`). Exit code 0 when the hash chain is intact, 1 when it is broken.

Paths and commands are shown relative to the page folder when they lie inside it. The page never shows an environment
value or a file content: the records hold none. It is the template templates/provenance.html.j2 on the shared page
frame: every datum is escaped; there is no script and no external resource.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
from collections.abc import Callable
from typing import Any

from tsbench.core import trace_prov
from tsbench.report import page
from tsbench.report.summary import load_steps

__all__ = ["build_html", "context", "main"]

SHA_SHOWN = 12  # hex characters of a sha256 on the page; the whole hash is in the tooltip
_HOME_SEGMENT = re.compile(r"^/(?:home|Users)/[^/]+")


def _relativizer(out_dir: pathlib.Path) -> Callable[[str], str]:
    """A function that shortens every mention of the page folder in a text: `<dir>/x` becomes `x`, `<dir>` alone `.`.

    The folder is known by its path as given, as resolved, as the tracer redacts it (`~/...`) and relative to the
    working directory, so a path from a record and a command line from steps.jsonl are both shortened."""
    bases = {str(out_dir.absolute()), str(out_dir.resolve())}
    bases |= {_HOME_SEGMENT.sub("~", b) for b in bases}
    rel_cwd = os.path.relpath(out_dir.resolve(), pathlib.Path.cwd())
    if rel_cwd != "." and not rel_cwd.startswith(".."):
        bases.add(rel_cwd)
    bases = {b.rstrip("/") for b in bases if b.rstrip("/")}
    pattern = re.compile(r"(?<![\w./~-])(?:" + "|".join(re.escape(b) for b in sorted(bases, key=len, reverse=True))
                         + r")(?:(?P<slash>/)|(?![\w.-]))")

    def shorten(text: str) -> str:
        return pattern.sub(lambda m: "" if m.group("slash") else ".", text)

    return shorten


def _num(value: Any) -> float:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else 0.0


def _anchor(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "-", name)


def _call_tree(calls: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    """The calls of one process as a forest and the number of distinct functions.

    A function is listed under its caller, after it. Each function is expanded once, under its first caller; a later
    mention (another caller, or a cycle) is a leaf marked `again`, so a cycle ends and the page stays small."""
    children: dict[str | None, list[tuple[str, int]]] = {}
    functions: dict[str, int] = {}
    for edge in calls:
        name, caller, count = str(edge.get("function", "")), edge.get("caller"), edge.get("count") or 1
        children.setdefault(caller, []).append((name, count))
        functions[name] = functions.get(name, 0) + count
    expanded: set[str] = set()

    def node(name: str, count: int) -> dict[str, Any]:
        if name in expanded:
            return {"name": name, "count": count, "again": True, "children": []}
        expanded.add(name)
        return {"name": name, "count": count, "again": False,
                "children": [node(n, c) for n, c in children.get(name, [])]}

    roots = [node(n, c) for n, c in children.get(None, [])]
    roots += [node(c, 1) for c in children if c is not None and c not in functions and c not in expanded]
    leftovers = [n for n in functions if n not in expanded]  # reachable only through a cycle
    roots += [node(n, functions[n]) for n in leftovers if n not in expanded]
    return roots, len(functions)


def _producers(records: list[dict[str, Any]]) -> dict[str, list[tuple[tuple[float, float, int], int]]]:
    """path -> [(order, record index)] of the records that wrote it, with the order that picks the latest writer."""
    found: dict[str, list[tuple[tuple[float, float, int], int]]] = {}
    for i, rec in enumerate(records):
        order = (_num(rec.get("end")), _num(rec.get("start")), i)
        for path in trace_prov.outputs(rec):
            found.setdefault(path, []).append((order, i))
    return found


def _sha(value: str) -> dict[str, str]:
    return {"short": value[:SHA_SHOWN], "full": value}


def context(steps: list[dict], trace_root: pathlib.Path, out: pathlib.Path) -> dict[str, Any]:
    """Everything provenance.html.j2 shows, as plain data."""
    shorten = _relativizer(out.parent)
    records = trace_prov.load_records(trace_root)
    breaks = trace_prov.hash_chain(records)
    names = {s["name"] for s in steps}
    step_of = {trace_prov.activity_id(r): str(r.get("step", "")) for r in records}
    producers = _producers(records)
    out_id = {(i, path): f"f{i}-{k}" for i, rec in enumerate(records) for k, path in enumerate(trace_prov.outputs(rec))}

    def producer_link(reader: int, path: str) -> dict[str, str] | None:
        started = _num(records[reader].get("start"))
        best = max(((order, i) for order, i in producers.get(path, []) if i != reader and order[0] <= started),
                   default=None)
        if best is None or str(records[best[1]].get("step", "")) not in names:
            return None  # no writer, or one in a trace folder the page does not show: no dangling link
        return {"href": out_id[(best[1], path)], "step": str(records[best[1]].get("step", ""))}

    by_step: dict[str, list[dict[str, Any]]] = {}
    for i, rec in enumerate(records):
        tree, n_functions = _call_tree(rec.get("calls") or [])
        by_step.setdefault(str(rec.get("step", "")), []).append({
            "command": shorten(str(rec.get("command", ""))), "pid": rec.get("pid"), "exit_code": rec.get("exit_code"),
            "tree": tree, "n_functions": n_functions,
            "inputs": [{"path": shorten(p), "sha": _sha(h), "from": producer_link(i, p)}
                       for p, h in trace_prov.inputs(rec).items()],
            "outputs": [{"id": out_id[(i, p)], "path": shorten(p), "sha": _sha(h)}
                        for p, h in trace_prov.outputs(rec).items()]})
    verdict: dict[str, Any] = {
        "intact": not breaks,
        "breaks": [{"path": shorten(b["path"]), "expected": _sha(b["expected"]), "found": _sha(b["found"]),
                    "producer": step_of.get(b["producer"], ""), "consumer": step_of.get(b["consumer"], ""),
                    "consumer_anchor": _anchor(step_of.get(b["consumer"], "")) if step_of.get(b["consumer"]) in names
                    else None} for b in breaks],
    }
    return {
        "title": "Provenance of the functional test", "verdict": verdict, "sha_chars": SHA_SHOWN,
        "n_records": len(records), "n_steps_traced": len({r.get("step") for r in records}),
        "steps": [{"name": s["name"], "anchor": _anchor(s["name"]), "command": shorten(str(s.get("command", ""))),
                   "rc": s.get("rc"), "records": by_step.get(s["name"], [])} for s in steps],
    }


def build_html(steps: list[dict], trace_root: pathlib.Path, out: pathlib.Path) -> str:
    return page.render("provenance.html.j2", **context(steps, trace_root, out))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="tsbench report provenance", description=__doc__.splitlines()[0])
    ap.add_argument("--steps", required=True, type=pathlib.Path, help="steps.jsonl written by tools/functional_test.sh")
    ap.add_argument("--trace", required=True, type=pathlib.Path, help="folder with one trace folder per step")
    ap.add_argument("--out", required=True, type=pathlib.Path, help="the HTML page")
    ap.add_argument("--prov", type=pathlib.Path, help="the PROV-JSON file (default: the page name with .prov.json)")
    a = ap.parse_args(argv)
    steps = load_steps(a.steps)
    html = build_html(steps, a.trace, a.out)
    prov = a.prov or a.out.with_suffix(".prov.json")
    for path in (a.out, prov):
        path.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(html, encoding="utf-8")
    records = trace_prov.load_records(a.trace)
    prov.write_text(json.dumps(trace_prov.to_prov(records), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    breaks = trace_prov.hash_chain(records)
    print(f"wrote {a.out} and {prov} ({len(records)} process records, hash chain "
          f"{'intact' if not breaks else f'broken at {len(breaks)} file versions'})")
    return 1 if breaks else 0


if __name__ == "__main__":
    raise SystemExit(main())
