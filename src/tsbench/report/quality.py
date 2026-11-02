"""The quality page: line coverage per module and mutation score per lane, for two measurements (before and after).

    tsbench report quality --coverage-before A.json --coverage-after B.json [--renames R.tsv] [--mutation DIR]
                           --out PAGE.html [--json facts.json]

Inputs: two coverage.py JSON reports (format 3). Files named `test_*.py` or `conftest.py` are left out, so a report
that counts test files inside `src/` compares with one that does not. A module is named by its path
relative to `src/tsbench/`. `--renames` is a TSV file (old<TAB>new, relative to `src/tsbench/`, `#` starts a comment)
that gives a module of the before report its new name; the page never calls git. `--mutation` is a folder with one
folder per lane holding `baseline-survivors.json` (the mutmut summary of the whole lane), `after.json` (the re-run of
the survivors of the before measurement) and optionally `kill.json` (equivalent mutants). The survivors left after are
read from `survivors-after.json` in the lane folder, else from the `survivors_file` that after.json names: as given,
or the one file under the parent of `--mutation` whose last three path parts are the same.

Scores: coverage is covered lines over statements; a package or the total sums its modules. The mutation score is
killed / (killed + survived), timeouts and mutants without tests left out. In the after measurement the killed
are the baseline killed plus the re-run killed; a survivor that the re-run does not kill stays a survivor.

What the page shows: a verdict line and fact tiles; coverage per package and mutation score per lane as dumbbell
figures (before and after joined by a line); a table per module with the change, drops marked with icon and text;
the modules found only before or only after; the survivors left per lane as a collapsible list.
"""
from __future__ import annotations

import argparse
import collections
import datetime
import json
import math
import pathlib
import sys

from tsbench.report import page
from tsbench.report.svg.base import fixed, round_half_up

__all__ = ["compare", "context", "build_html", "facts", "is_test_file", "load_coverage", "load_lane",
           "load_mutation", "main", "module_key", "read_renames"]

TOP = "(top level)"
SURVIVORS = "survivors-after.json"
STATE_TEXT = {"improved": ("improved", "check", "ok"), "dropped": ("dropped", "warning", "bad"),
              "same": ("no change", "equals", "muted"), "only_before": ("only before", "dash", "muted"),
              "only_after": ("only after", "dash", "muted")}


def module_key(path: str) -> str:
    """The path of a measured file relative to `src/tsbench/` (`/`-separated)."""
    parts = pathlib.PurePath(path.replace("\\", "/")).parts
    for i in range(len(parts) - 1, 0, -1):
        if parts[i - 1] == "src" and parts[i] == "tsbench":
            return "/".join(parts[i + 1:])
    if "tsbench" in parts:
        return "/".join(parts[parts.index("tsbench") + 1:])
    return "/".join(parts)


def is_test_file(key: str) -> bool:
    name = key.rsplit("/", 1)[-1]
    return name.startswith("test_") or name == "conftest.py"


def read_renames(path) -> dict[str, str]:
    """{old: new} from a TSV file of two columns; blank lines and lines starting with `#` are skipped."""
    out = {}
    for n, line in enumerate(pathlib.Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        cells = line.split("\t")
        if len(cells) != 2 or not all(c.strip() for c in cells):
            raise ValueError(f"{pathlib.Path(path).name} line {n}: expected old<TAB>new")
        out[cells[0].strip()] = cells[1].strip()
    return out


def _read_report(path) -> dict:
    data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("files"), dict):
        raise ValueError(f"{pathlib.Path(path).name}: not a coverage.py JSON report (no 'files')")
    return data


def load_coverage(path, renames: dict[str, str] | None = None) -> dict[str, tuple[int, int]]:
    """{module: (covered lines, statements)} of a coverage.py JSON report, test files left out, renames applied."""
    out: dict[str, tuple[int, int]] = {}
    for name, rec in _read_report(path)["files"].items():
        key = module_key(name)
        if is_test_file(key):
            continue
        key = (renames or {}).get(key, key)
        s = rec["summary"]
        c0, n0 = out.get(key, (0, 0))
        out[key] = (c0 + int(s["covered_lines"]), n0 + int(s["num_statements"]))
    return out


def _pct(c: int, n: int) -> float:
    return 100.0 * c / n if n else 100.0


def _change(before: float | None, after: float | None) -> float | None:
    return None if before is None or after is None else round_half_up(after - before, 1)


def _state(change: float | None, before, after) -> str:
    if before is None:
        return "only_after"
    if after is None:
        return "only_before"
    return "improved" if change and change > 0 else "dropped" if change and change < 0 else "same"


def _package(key: str) -> str:
    return key.split("/", 1)[0] if "/" in key else TOP


def compare(before: dict[str, tuple[int, int]], after: dict[str, tuple[int, int]]) -> dict:
    """Per module, per package and in total: covered, statements, percent before and after, change in points."""
    modules = []
    for key in sorted(set(before) | set(after)):
        b, a = before.get(key), after.get(key)
        pb, pa = (_pct(*b) if b else None), (_pct(*a) if a else None)
        ch = _change(pb, pa)
        modules.append({"module": key, "package": _package(key), "statements_before": b[1] if b else None,
                        "statements_after": a[1] if a else None, "before": pb, "after": pa, "change": ch,
                        "state": _state(ch, pb, pa)})
    sums: dict = collections.defaultdict(lambda: [0, 0, 0, 0, 0])
    for key in set(before) | set(after):
        s = sums[_package(key)]
        s[4] += 1
        if key in before:
            s[0] += before[key][0]
            s[1] += before[key][1]
        if key in after:
            s[2] += after[key][0]
            s[3] += after[key][1]
    packages = []
    for name in sorted(sums, key=lambda p: (p == TOP, p)):
        cb, nb, ca, na, k = sums[name]
        pb, pa = (_pct(cb, nb) if nb else None), (_pct(ca, na) if na else None)
        packages.append({"package": name, "modules": k, "statements_before": nb, "statements_after": na,
                         "before": pb, "after": pa, "change": _change(pb, pa)})
    cb, nb = sum(v[0] for v in before.values()), sum(v[1] for v in before.values())
    ca, na = sum(v[0] for v in after.values()), sum(v[1] for v in after.values())
    pick = collections.defaultdict(list)
    for m in modules:
        pick[m["state"]].append(m["module"])
    return {"modules": modules, "packages": packages,
            "total": {"covered_before": cb, "statements_before": nb, "covered_after": ca, "statements_after": na,
                      "before": _pct(cb, nb), "after": _pct(ca, na), "change": _change(_pct(cb, nb), _pct(ca, na))},
            "improved": pick["improved"], "dropped": pick["dropped"], "same": pick["same"],
            "only_before": pick["only_before"], "only_after": pick["only_after"]}


def _report_meta(path) -> dict:
    """What coverage.py itself says about a report: its time stamp and its total over every measured file."""
    data = _read_report(path)
    keys = [module_key(k) for k in data["files"]]
    tests = [k for k in keys if is_test_file(k)]
    test_statements = sum(int(data["files"][k]["summary"]["num_statements"])
                          for k in data["files"] if is_test_file(module_key(k)))
    return {"file": pathlib.Path(path).name, "timestamp": (data.get("meta") or {}).get("timestamp"),
            "reported_total": (data.get("totals") or {}).get("percent_covered"), "files": len(keys),
            "test_files": len(tests), "test_statements": test_statements}


def _read_json(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _find_survivors(lane_dir: pathlib.Path, recorded: str | None, search_root: pathlib.Path) -> pathlib.Path | None:
    """The survivors-after list of a lane: in the lane folder, at the recorded path, or the one file under
    `search_root` whose last three path parts equal those of the recorded path."""
    own = lane_dir / SURVIVORS
    if own.is_file():
        return own
    if not recorded:
        return None
    rec = pathlib.Path(recorded)
    for cand in ((rec,) if rec.is_absolute() else (lane_dir / rec, search_root / rec)):
        if cand.is_file():
            return cand
    tail = rec.parts[-3:]
    hits = [p for p in search_root.rglob(rec.name) if p.parts[-len(tail):] == tail]
    return hits[0] if len(hits) == 1 else None


def _count(value) -> int:
    """The number of entries of a list, or of the leaves of a dict of dicts (kill.json `equivalent`)."""
    if isinstance(value, dict):
        return sum(_count(v) if isinstance(v, dict | list) else 1 for v in value.values())
    return len(value) if isinstance(value, list) else 0


def load_lane(lane_dir, search_root=None) -> dict | None:
    """One mutation lane, or None when its baseline or after file is missing."""
    d = pathlib.Path(lane_dir)
    if not (d / "baseline-survivors.json").is_file() or not (d / "after.json").is_file():
        return None
    base, after = _read_json(d / "baseline-survivors.json"), _read_json(d / "after.json")
    kill = _read_json(d / "kill.json") if (d / "kill.json").is_file() else {}
    s = base["summary"]
    k0, s0 = int(s["killed"]), int(s["survived"])
    k1, s1 = int(after["killed"]), int(after["survived"])
    checked = k0 + s0
    path = _find_survivors(d, after.get("survivors_file"), pathlib.Path(search_root or d.parent))
    groups: dict = collections.defaultdict(list)
    if path:
        for sv in _read_json(path).get("survivors") or []:
            groups[str(sv.get("module") or "")].append(str(sv.get("mutant") or ""))
    return {"lane": base.get("lane") or d.name, "package": base.get("package") or after.get("package") or "",
            "tool": base.get("tool") or "", "killed_before": k0, "survived_before": s0,
            "timeout": int(s.get("timeout") or 0), "no_tests": int(s.get("no tests") or 0),
            "before": _pct(k0, checked), "rerun": k1 + s1, "killed_now": k1, "survived_rerun": s1,
            "not_rerun": max(s0 - k1 - s1, 0), "left": s0 - k1, "after": _pct(k0 + k1, checked),
            "recorded_after": after.get("score_pct"), "equivalent": _count(kill.get("equivalent")),
            "survivors_found": path is not None, "survivors_listed": sum(len(v) for v in groups.values()),
            "survivors": [{"module": m, "mutants": sorted(groups[m])} for m in sorted(groups)]}


def load_mutation(root) -> list[dict]:
    """Every lane folder of `root` (sorted by name) that has a baseline and an after file."""
    root = pathlib.Path(root)
    if not root.is_dir():
        raise FileNotFoundError(f"{root.name}: no such folder")
    lanes = (load_lane(d, root.parent) for d in sorted(root.iterdir()) if d.is_dir())
    return [ln for ln in lanes if ln]


def facts(coverage_before, coverage_after, renames=None, mutation=None) -> dict:
    """Everything the page shows, as plain values (also the `--json` output)."""
    ren = read_renames(renames) if renames else {}
    before = load_coverage(coverage_before, ren)
    return {"coverage": compare(before, load_coverage(coverage_after)),
            "reports": {"before": _report_meta(coverage_before), "after": _report_meta(coverage_after)},
            "renames": len(ren), "renames_used": sum(1 for old in ren if old in load_coverage(coverage_before)),
            "mutation": load_mutation(mutation) if mutation else []}


def _fmt(v: float | None) -> str:
    return "–" if v is None else fixed(v, 1)


def _signed(v: float | None) -> str:
    return "–" if v is None else fixed(v, 1, sign=True).replace("-", "−")


def _domain(values) -> list[float]:
    vals = [v for v in values if v is not None]
    return [max(0.0, math.floor(min(vals, default=0.0) / 10) * 10), 100.0]


def _verb(change: float | None) -> str:
    return "rose" if change and change > 0 else "fell" if change and change < 0 else "stayed"


def _stamp(ts: str | None) -> str:
    return (ts or "no time stamp")[:16].replace("T", " ")


def context(f: dict, generated: str | None = None) -> dict:
    """The data of the page from the result of `facts`, as plain values for quality.html.j2; `generated` is the time
    stamp shown (default: now)."""
    cov, lanes = f["coverage"], f["mutation"]
    t = cov["total"]
    verdict = (f"Line coverage of the module code {_verb(t['change'])} from {_fmt(t['before'])} % to "
               f"{_fmt(t['after'])} %; {len(cov['improved'])} modules improved, {len(cov['dropped'])} dropped.")
    if lanes:
        up = sum(1 for ln in lanes if ln["after"] > ln["before"])
        verdict += f" The mutation score rose in {up} of {len(lanes)} lanes."
    modules = []
    for m in cov["modules"]:
        text, ic, tone = STATE_TEXT[m["state"]]
        st = m["statements_after"] if m["statements_after"] is not None else m["statements_before"]
        was = m["statements_before"] if m["statements_before"] not in (None, st) else None
        modules.append({**m, "b": _fmt(m["before"]), "a": _fmt(m["after"]), "ch": _signed(m["change"]),
                        "statements": st, "was": was, "text": text, "icon": ic, "tone": tone})
    dropped = [m for m in modules if m["state"] == "dropped"]
    pk_rows = [{"label": p["package"], "before": p["before"], "after": p["after"],
                "drop": bool(p["change"] and p["change"] < 0),
                "tip": f"{p['package']}: {_fmt(p['before'])} % → {_fmt(p['after'])} % ({p['modules']} modules)"}
               for p in cov["packages"] if p["before"] is not None or p["after"] is not None]
    ln_rows = [{"label": ln["lane"], "before": ln["before"], "after": ln["after"], "drop": ln["after"] < ln["before"],
                "tip": f"{ln['lane']}: {_fmt(ln['before'])} % → {_fmt(ln['after'])} %, {ln['left']} survivors left"}
               for ln in lanes]
    names = {"before": "before", "after": "after"}
    rb, ra = f["reports"]["before"], f["reports"]["after"]
    return {
        "title": "Test quality before and after", "verdict": verdict, "total": t,
        "tb": _fmt(t["before"]), "ta": _fmt(t["after"]), "tch": _signed(t["change"]),
        "stamp": generated or datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "before_file": rb, "after_file": ra, "before_when": _stamp(rb["timestamp"]),
        "after_when": _stamp(ra["timestamp"]), "reported_before": _fmt(rb["reported_total"]),
        "reported_after": _fmt(ra["reported_total"]), "renames": f["renames"], "renames_used": f["renames_used"],
        "n_modules": len(modules), "n_improved": len(cov["improved"]), "n_dropped": len(cov["dropped"]),
        "n_same": len(cov["same"]), "only_before": cov["only_before"], "only_after": cov["only_after"],
        "modules": modules, "dropped": dropped, "packages": [{**p, "b": _fmt(p["before"]), "a": _fmt(p["after"]),
                                                             "ch": _signed(p["change"])} for p in cov["packages"]],
        "lanes": [{**ln, "b": _fmt(ln["before"]), "a": _fmt(ln["after"]), "ch": _signed(_change(ln["before"],
                                                                                                ln["after"])),
                   "rec": _fmt(ln["recorded_after"])} for ln in lanes],
        "pk_spec": {"rows": pk_rows, "domain": _domain([v for r in pk_rows for v in (r["before"], r["after"])]),
                    "xLabel": "Line coverage (%)", "names": names, "left": 64},
        "ln_spec": {"rows": ln_rows, "domain": _domain([v for r in ln_rows for v in (r["before"], r["after"])]),
                    "xLabel": "Mutation score, killed / (killed + survived) (%)", "names": names, "left": 64},
    }


def build_html(f: dict, generated: str | None = None) -> str:
    """The page from the result of `facts`; `generated` is the time stamp shown (default: now)."""
    ctx = context(f, generated)
    return page.render("quality.html.j2", **ctx, ctx=ctx)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="tsbench report quality", description=__doc__.splitlines()[0])
    ap.add_argument("--coverage-before", required=True, metavar="FILE", help="coverage.py JSON, before")
    ap.add_argument("--coverage-after", required=True, metavar="FILE", help="coverage.py JSON, after")
    ap.add_argument("--renames", default=None, metavar="FILE", help="TSV old<TAB>new, paths relative to src/tsbench/")
    ap.add_argument("--mutation", default=None, metavar="DIR", help="folder with one folder per mutation lane")
    ap.add_argument("--out", required=True, metavar="FILE")
    ap.add_argument("--json", default=None, metavar="FILE", help="also write the facts to this file")
    a = ap.parse_args(argv)
    try:
        f = facts(a.coverage_before, a.coverage_after, a.renames, a.mutation)
    except (OSError, ValueError, KeyError, TypeError) as e:
        print(f"tsbench report quality: {e}", file=sys.stderr)
        return 2
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build_html(f), encoding="utf-8")
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps(f, indent=1), encoding="utf-8")
    t = f["coverage"]["total"]
    print(f"wrote {out}: coverage {_fmt(t['before'])} % -> {_fmt(t['after'])} %, "
          f"{len(f['coverage']['dropped'])} modules dropped, {len(f['mutation'])} mutation lanes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
