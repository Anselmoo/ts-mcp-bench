"""The literature page: fit results against the published values, per literature system of the pilot tasks.

    tsbench report literature --runs DIR [--runs DIR2 ...] --out LITERATURE.html

For every pilot task of the classes `literature_all`, `experimental` (data:
src/tsbench/data/literature/literature-spectra.csv) and `literature_new`
(src/tsbench/data/literature/literature-spectra-2.csv, pilot only) the page puts side by side: (1) the values the
paper reports (never scored), (2) the oracle reference of the task (forward-model least squares, or the closed form),
(3) every model answer of the runs with its relative error against oracle and paper and pass/fail against the
tolerance. Then parity plots, a dot plot of the relative errors per system, the accuracy per model and condition
(task-clustered bootstrap intervals), the systems the rubric excludes and a box on the method.

Inputs: the run sets under each `--runs` folder (tsbench.score.run_sets), the pilot task set, the two literature tables
and the rubric (src/tsbench/data/tasks/rubric.md). The sealed split stays sealed: tasks are only read through
`tsbench.tasks.load("pilot")`; the confirmatory split is never loaded. Only pilot systems and the exclusions published
in the rubric are shown; their oracle fit is read from the rubric, not recomputed (a new fit of every table system would
also touch the confirmatory systems).

Scoring is in memory as on the comparison page (`score_in_memory`, `outcome_of`). Runs with HTTP 429 or another API
error (grey) count in no rate. Design: Figura design system
(tsbench.report.page); no pie charts; every status with icon and text. The page is
templates/literature.html.j2; `context` builds its data and holds no markup.
"""
from __future__ import annotations

import argparse
import csv
import datetime
import math
import pathlib
import re
import sys

from tsbench.core import resource
from tsbench.report import comparison, page, reproduce
from tsbench.report.base import as_bool, as_number, as_run_sets, not_evaluable
from tsbench.report.page import href
from tsbench.score.run_sets import run_sets_in

__all__ = ["collect", "context", "build_html", "main", "read_rubric_exclusions", "paper_values", "source_parts",
           "CLASSES"]

CSV_PATH = resource("literature/literature-spectra.csv")
CSV_PATH_NEW = resource("literature/literature-spectra-2.csv")  # literature_new (same columns + location)
RUBRIC_PATH = resource("tasks/rubric.md")
CLASSES = ("literature_all", "experimental", "literature_new")
FIT_CLASSES = ("literature_all", "literature_new")  # oracle: least-squares fit with the forward model
CLASS_LABEL = {
    "literature_all": "fit (forward model, least squares)",
    "experimental": "closed form (two or three bands)",
    "literature_new": "fit (forward model, least squares; new literature, pilot only)",
}
CLASS_SHORT = {"literature_all": "fit", "experimental": "CF", "literature_new": "fit-new"}
PARAMS = ("Dq", "B", "C")
UNIT = "cm⁻¹"
DOI_RE = re.compile(r"10\.\d{4,9}/[^\s,;]+")
NOT_EVAL = comparison.NOT_EVAL


# ---------------------------------------------------------------------------- number formatting
def _norm_name(s: str) -> str:
    return (s or "").replace("−", "-").strip()


def _number(x, nd: int | None = None) -> str:
    """A number with a decimal point and a true minus sign; without `nd` 0 to 3 decimals by size."""
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return "–"
    if nd is None:
        a = abs(x)
        nd = 0 if a >= 100 else 1 if a >= 10 else 2 if a >= 1 else 3
    return f"{x:.{nd}f}".replace("-", "−")


def _percent_error(x, nd: int = 1) -> str:
    """A signed relative error in percent."""
    if x is None or not math.isfinite(x):
        return "–"
    s = f"{100 * x:+.{nd}f}".replace("-", "−")
    return s + " %"


def _relative_error(a, ref):
    if a is None or ref in (None, 0):
        return None
    return (a - ref) / ref


# ---------------------------------------------------------------------------- literature table (CSV)
def _csv_num(s: str):
    s = (s or "").strip().lstrip("≈").replace("−", "-")
    try:
        return float(s) if s else None
    except ValueError:
        return None


def read_csv_rows(path: pathlib.Path | None = None) -> dict:
    """System -> row of the table (name with an ASCII minus as key); without `path` both literature tables. Only read,
    nothing is fitted."""
    out = {}
    for pth in ([path] if path is not None else [CSV_PATH, CSV_PATH_NEW]):
        if path is None and not pth.is_file():
            continue
        with pth.open(newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                out.setdefault(_norm_name(r["system"]), r)
    return out


def paper_values(row: dict | None) -> dict:
    """The values the paper reports: Dq, Dq/B, C/B (and the values read from its auxiliary
    diagram). B and C are derived: B = Dq / (reported Dq/B), C = (reported C/B) * B. The paper does not give B and C
    directly."""
    if not row:
        return {}
    dq, dqb, cb = _csv_num(row["Dq_cm-1"]), _csv_num(row["DqB_reported"]), _csv_num(row["CB_reported"])
    b = dq / dqb if dq is not None and dqb else None
    return {
        "Dq": dq,
        "DqB": dqb,
        "CB": cb,
        "DqB_aux": _csv_num(row["DqB_aux_diagram"]),
        "CB_aux": _csv_num(row["CB_aux_diagram"]),
        "B": b,
        "C": cb * b if cb is not None and b is not None else None,
    }


def source_parts(row: dict | None) -> dict:
    """The source of a table row cut into `{"text", "doi", "locator"}`: the citation without its DOI, the DOI, and the
    place in the paper that follows it (`Tables 1-2`; the `location` column when the source names none). A source
    without a DOI marks it `(no DOI)`; the marker is dropped."""
    source = ((row or {}).get("source") or "").strip()
    m = DOI_RE.search(source)
    if m:
        head, tail = source[:m.start()], source[m.end():]
        doi = m.group(0).rstrip(".")
        head = re.sub(r"(,\s*)?doi:\s*$", "", head)
    else:
        doi, head, tail = None, source, ""
        if (cut := re.search(r"\s*\(no DOI\)", source)):
            head, tail = source[:cut.start()], source[cut.end():]
    locator = tail.strip(" ,;") or ((row or {}).get("location") or "").strip() or None
    return {"text": head.strip(" ,"), "doi": doi, "locator": locator}


def terms_of(row: dict | None, bands: list[float]) -> list[str]:
    """The term label of the table for every band energy of the task (matched by energy)."""
    if not row:
        return ["" for _ in bands]
    tab = [(row[f"band{i}_term"].strip(), _csv_num(row[f"band{i}_cm-1"])) for i in (1, 2, 3, 4)]
    out = []
    for b in bands:
        hit = next((t for t, v in tab if v is not None and abs(v - b) < 0.5), "")
        out.append(hit)
    return out


# ---------------------------------------------------------------------------- rubric (published exclusions)
def read_rubric_exclusions(path: pathlib.Path = RUBRIC_PATH) -> list[dict]:
    """The systems of `literature_all` that the rubric publishes as not turned into tasks, with the reason and, when the
    rubric's table gives it, the oracle fit (Dq, B, C/B). Reads only the rubric; nothing is fitted again."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    m = re.search(r"Systems that are not turned into tasks[^\n]*\n(.*?)\n\n", text, flags=re.S)
    out = []
    if m:
        for ln in m.group(1).splitlines():
            mm = re.match(r"^- (.+?) \(d(\d)\): (.+)$", ln.strip())
            if mm:
                out.append({"system": mm.group(1), "d": int(mm.group(2)), "reason": mm.group(3).strip()})
    fits = {}
    for ln in text.splitlines():
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if len(cells) >= 6 and cells[2] == "excluded":
            fits[_norm_name(cells[0])] = {
                "Dq": _csv_num(cells[3]),
                "B": _csv_num(cells[4]),
                "CB": _csv_num(cells[5].split()[0]),
            }
    for x in out:
        x["fit"] = fits.get(_norm_name(x["system"]))
    return out


# ---------------------------------------------------------------------------- collection
def _tol_ok(rel, tol) -> bool | None:
    if rel is None or tol is None:
        return None
    return abs(rel) <= tol + 1e-12


def _task_entries(tasks: dict, csv_rows: dict) -> dict:
    """One entry per literature task of the pilot split: system, bands, reference, tolerance and the paper's values."""
    out = {}
    for tid, t in tasks.items():
        if t.get("class") not in CLASSES:
            continue
        row = csv_rows.get(_norm_name(t.get("system", "")))
        bands = [float(b) for b in (t.get("bands_cm1") or [])]
        labels = list((t.get("params") or {}).get("labels") or []) or terms_of(row, bands)
        ref = t.get("reference") or {}
        out[tid] = {
            "key": tid, "id": tid, "cls": t["class"], "system": t["system"], "d": t.get("d_count"),
            "geometry": t.get("geometry"), "bands": bands, "labels": labels,
            "ref": {p: ref.get(p) for p in PARAMS}, "tol": {p: (t.get("tolerance") or {}).get(p) for p in PARAMS},
            "oracle": t.get("oracle"), "required": list(t.get("required") or []),
            "cb_fixed": (t.get("params") or {}).get("cb_fixed"), "paper": paper_values(row), "csv": row,
            "paper_task": ((t.get("params") or {}).get("paper") or None),
            "dev_task": ((t.get("params") or {}).get("deviation_from_paper") or None),
        }
    return out


def collect(run_sets, out_path=None) -> dict:
    """Read the pilot tasks, the literature tables, the rubric's exclusions and every run of the literature classes in
    the run sets (RunSet objects or plain folders); score them in memory."""
    from tsbench.score.score import find_transcripts
    notes: list[str] = []
    csv_rows = read_csv_rows()
    try:
        tasks = comparison.load_tasks()
    except Exception as exc:  # noqa: BLE001
        notes.append(f"pilot task set not loadable ({type(exc).__name__})")
        tasks = {}
    entries = _task_entries(tasks, csv_rows)
    runs: list[dict] = []
    manifests: dict = {}
    for rs in as_run_sets(run_sets):
        d = rs.path
        files = [f for f in find_transcripts(d) if (tasks.get(f[4]) or {}).get("class") in CLASSES]
        if not files:
            continue
        try:
            comparison.check_task_set(d, tasks)
        except Exception as exc:  # noqa: BLE001 - a run set of another task set does not belong on the page
            notes.append(f"{rs.name}: not shown, made with another task set ({type(exc).__name__})")
            continue
        try:
            rows, results = comparison.score_in_memory(files, tasks)
        except Exception as exc:  # noqa: BLE001
            notes.append(f"{rs.name}: scoring failed ({type(exc).__name__})")
            continue
        for r, res in zip(rows, results, strict=False):
            tid = r["task_id"]
            ent = entries.get(tid)
            if ent is None:
                continue
            oc = comparison.outcome_of(r, tasks.get(tid), not_evaluable(res) is not None)
            vals = {p: as_number(r.get(p.lower())) for p in PARAMS}
            rel = {p: _relative_error(vals[p], ent["ref"].get(p)) for p in PARAMS}
            runs.append(
                {
                    "key": tid,
                    "set": rs.name,
                    "root": d,
                    "model": r["model"],
                    "cond": r["condition"],
                    "effort": r["effort"],
                    "k": r["k_index"],
                    "task": tid,
                    "outcome": oc,
                    "evaluable": oc not in NOT_EVAL,
                    "rescued": bool(as_bool(r.get("rescued"))),
                    "vals": vals,
                    "rel": rel,
                    "path": pathlib.Path(r["_path"]),
                    "pass": {p: _tol_ok(rel[p], ent["tol"].get(p)) for p in ent["required"]},
                }
            )
            manifests.setdefault(d, reproduce.read_manifest(pathlib.Path(r["_path"]), d))
    for r in runs:
        r["manifest"] = manifests.get(r["root"], {})
    runs.sort(
        key=lambda r: (r["key"], comparison.model_key(r["model"]), r["cond"], str(r["effort"]), int(r["k"]), r["set"])
    )
    return {"entries": entries, "runs": runs, "csv": csv_rows, "exclusions": read_rubric_exclusions(), "notes": notes,
            "date": datetime.date.today().isoformat(),
            "out_dir": pathlib.Path(out_path).resolve().parent if out_path else pathlib.Path.cwd(),
            "shown": {r["key"] for r in runs}}


# ---------------------------------------------------------------------------- page data
# The page is templates/literature.html.j2 (parts in literature_macros.html.j2). The functions below turn the data of
# `collect` into strings, numbers, lists and dicts; every tag is in the templates.
def _text(x) -> str:
    return "" if x is None else str(x)


def _doi_parts(source: str) -> list[dict]:
    """The source text of the table cut into text and DOI parts: {"text", "href"}, `href` None for plain text."""
    out, pos = [], 0
    source = source or ""
    for m in DOI_RE.finditer(source):
        doi = m.group(0).rstrip(".")
        if m.start() > pos:
            out.append({"text": source[pos:m.start()], "href": None})
        out.append({"text": doi, "href": page.doi_href(doi)})
        pos = m.start() + len(doi)
    if pos < len(source):
        out.append({"text": source[pos:], "href": None})
    return out


def _model_label(model: str) -> str:
    return comparison.display_model(model)


def _order(runs):
    return sorted(
        runs, key=lambda r: (comparison.model_key(r["model"]), r["cond"], str(r["effort"]), int(r["k"]), r["set"])
    )


# ---------------------------------------------------------------------------- table cells
def _value_cell(x, nd=None) -> dict:
    return {"text": _number(x, nd)}


def _dash(n: int = 1) -> list[dict]:
    return [{"text": "–", "muted": True} for _ in range(n)]


def _gap(n: int = 1) -> list[dict]:
    return [{"empty": True} for _ in range(n)]


def _checked_value(ok, text: str, tol) -> dict:
    """A value cell: with a tolerance check (within or outside) the template adds the icon and the word."""
    if ok is None:
        return {"text": text}
    return {"text": text, "ok": bool(ok), "tol": _number(100 * tol, 0)}


# ---------------------------------------------------------------------------- run rows and system cards
def _run_row(ent: dict, r: dict, out_dir: pathlib.Path) -> dict:
    v, rel, tol, paper = r["vals"], r["rel"], ent["tol"], ent["paper"]
    dq, b, c = v["Dq"], v["B"], v["C"]
    dqb = dq / b if dq is not None and b else None
    cb = c / b if c is not None and b else None
    show_c = "C" in ent["required"]
    cells = [_value_cell(dq), _value_cell(b), _value_cell(c) if show_c else _dash()[0], _value_cell(dqb, 2),
             _value_cell(cb, 2) if show_c else _dash()[0]]
    for p in PARAMS:
        if (p == "C" and not show_c) or p not in ent["required"] or rel[p] is None:
            cells.append(_dash()[0])
        else:
            cells.append(_checked_value(r["pass"].get(p), _percent_error(rel[p]), tol[p]))
    for val, ref in ((dq, paper.get("Dq")), (dqb, paper.get("DqB")), (cb if show_c else None, paper.get("CB"))):
        cells.append({"text": _percent_error(_relative_error(val, ref))})
    run = {"task": r["task"], "model": r["model"], "cond": r["cond"], "effort": r["effort"], "k": r["k"],
           "transcript": r["path"], "root": r["root"], "label": r["set"]}
    view = r["root"] / "views" / str(r["model"]) / str(r["cond"]) / str(r["effort"]) / (r["path"].stem + ".html")
    return {
        "cls": "na" if r["outcome"] == "na429" else "",
        "model": _model_label(r["model"]),
        "cond": _text(r["cond"]),
        "effort": _text(r["effort"]),
        "k": _text(r["k"]),
        "outcome": r["outcome"],
        "rescued": bool(r["rescued"]),
        "cells": cells,
        "transcript": href(r["path"], out_dir),
        "view": href(view, out_dir) if view.is_file() else None,
        "cmd": reproduce.commands(run, r["manifest"]),
    }


def _ref_rows(ent: dict) -> list[dict]:
    """The reference rows of a system: paper (two rows and its deviation from the oracle), oracle and tolerance."""
    p, ref, tol = ent["paper"], ent["ref"], ent["tol"]
    show_c = "C" in ent["required"]
    ref_dqb = ref["Dq"] / ref["B"] if ref["Dq"] and ref["B"] else None
    ref_cb = ref["C"] / ref["B"] if show_c and ref["C"] and ref["B"] else None

    def maybe(x, nd=None) -> dict:
        return _value_cell(x, nd) if x is not None else _dash()[0]

    def row(cls, bold, rest, cells) -> dict:
        return {"cls": f"ref {cls}".strip(), "bold": bold, "rest": rest, "cells": cells}

    def paper_row(label, vals, dqb, cb) -> dict:
        return row(
            "paper", label, "", [maybe(x) for x in vals] + [maybe(dqb, 2), maybe(cb, 2)] + _gap(3) + _dash(3) + _gap()
        )

    rows = []
    if p:
        dev = [{"text": _percent_error(_relative_error(p.get(k), ref.get(k)))}
               if (k != "C" or show_c) and p.get(k) is not None and ref.get(k) is not None else _dash()[0]
               for k in PARAMS]
        rows.append(
            paper_row(
                "paper, reported (B and C derived)",
                [p.get("Dq"), p.get("B"), p.get("C") if show_c else None],
                p.get("DqB"),
                p.get("CB") if show_c else None,
            )
        )
        rows.append(paper_row("paper, auxiliary diagram (Dq/B and C/B only)", [None, None, None], p.get("DqB_aux"),
                              p.get("CB_aux") if show_c else None))
        rows.append(
            row("paper", "paper against oracle", "(paper − oracle, relative)", _dash(5) + dev + _dash(3) + _gap())
        )
    if ref_cb is not None:
        cb_cell = _value_cell(ref_cb, 2)
    elif ent.get("cb_fixed"):
        cb_cell = {"text": f"{_number(ent['cb_fixed'], 1)} (fixed)"}
    else:
        cb_cell = _dash()[0]
    oracle = "forward model, least squares" if ent["cls"] in FIT_CLASSES else "closed form"
    rows.append(
        row(
            "oracle",
            "oracle",
            f"({oracle})",
            [_value_cell(ref[k]) if (k != "C" or ref[k] is not None) else _dash()[0] for k in PARAMS]
            + [_value_cell(ref_dqb, 2) if ref_dqb is not None else _dash()[0], cb_cell]
            + _dash(3)
            + _dash(3)
            + _gap(),
        )
    )
    rows.append(row("", "tolerance", "(relative to the oracle)", _dash(5)
                    + [{"text": f"±{_number(100 * tol[k], 0)} %"} if tol.get(k) and k in ent["required"] else _dash()[0]
                       for k in PARAMS] + _dash(3) + _gap()))
    return rows


def _system_card(ent: dict, runs: list[dict], out_dir: pathlib.Path) -> dict:
    row = ent["csv"] or {}
    ev = [r for r in runs if r["evaluable"]]
    ok = sum(r["outcome"] == "correct" for r in ev)
    n429 = sum(r["outcome"] == "na429" for r in runs)
    refs = " · ".join(x for x in (row.get("ref_table1"), row.get("ref_table2")) if x)
    summary = (f"{ok} of {len(ev)} evaluable runs correct" if ev else "no evaluable runs") \
        + (f"; {n429} HTTP 429" if n429 else "")
    labels = ent["labels"] + [""] * len(ent["bands"])
    return {"ident": f"s-{ent['id']}", "id": ent["id"], "system": ent["system"], "d": _text(ent["d"]),
            "geometry": {"Oh": "octahedral", "Td": "tetrahedral"}.get(ent["geometry"], ent["geometry"] or ""),
            "short": CLASS_SHORT[ent["cls"]], "bands": [{"label": lab or "–", "band": _number(b, 0)}
                                                        for lab, b in zip(labels, ent["bands"], strict=False)],
            "source": _doi_parts(row.get("source", "")), "refs": refs or "–", "location": row.get("location") or "",
            "assignment": row.get("assignment_confidence") or "–", "oracle": CLASS_LABEL[ent["cls"]],
            "cb_fixed": _number(ent["cb_fixed"], 1) if ent.get("cb_fixed") else "", "summary": summary,
            "ref_rows": _ref_rows(ent), "runs": [_run_row(ent, r, out_dir) for r in _order(runs)]}


# ---------------------------------------------------------------------------- figures
COND_ORDER = ("A", "B", "C")
COND_SHAPE = {"A": "circle", "B": "square", "C": "triangle"}


def _plot_runs(runs):
    """The runs that count in figures and rates: evaluable (no 429 or other API error)."""
    return [r for r in runs if r["evaluable"]]


def _label(ent: dict) -> str:
    return f"{ent['system']} ({CLASS_SHORT[ent['cls']]})"


def _axis_domain(values: list[float], pad: float = 0.25) -> list[float]:
    lo, hi = min(values), max(values)
    span = hi - lo or hi
    return [max(0.0, math.floor((lo - pad * span) / 50) * 50), math.ceil((hi + pad * span) / 50) * 50]


def _parity_spec(p: str, data: dict) -> dict | None:
    ents = [e for e in data["entries"].values() if e["key"] in data["shown"] and p in e["required"] and e["ref"].get(p)]
    if not ents:
        return None
    refs = [e["ref"][p] for e in ents]
    dom = _axis_domain(refs, 0.3)
    pts, n_out = [], 0
    for e in ents:
        pv = e["paper"].get(p)
        if pv is not None:
            out = not (dom[0] <= pv <= dom[1])
            n_out += out
            pts.append({"x": e["ref"][p], "y": pv, "kind": "paper", "out": out,
                        "tip": f"{e['system']}: paper {_number(pv)} against oracle {_number(e['ref'][p])} {UNIT}"})
        for r in _plot_runs(data["runs"]):
            if r["key"] != e["key"] or r["vals"][p] is None:
                continue
            y = r["vals"][p]
            out = not (dom[0] <= y <= dom[1])
            n_out += out
            pts.append({"x": e["ref"][p], "y": y, "kind": "model", "cond": r["cond"], "out": out,
                        "tip": f"{e['system']} · {_model_label(r['model'])} {r['cond']} k{r['k']}: {_number(y)} {UNIT} "
                               f"({_percent_error(r['rel'][p])})"})
    tol = next(e["tol"][p] for e in ents)
    unit = UNIT
    return {"param": p, "dom": dom, "tol": tol, "pts": pts, "n_out": n_out, "width": 88,
            "xLabel": f"{p} oracle ({unit})", "yLabel": f"{p} model or paper ({unit})",
            "conds": [c for c in COND_ORDER if any(q.get("cond") == c for q in pts)]}


def _relative_error_spec(p: str, data: dict) -> dict | None:
    ents = [e for e in data["entries"].values() if e["key"] in data["shown"] and p in e["required"] and e["ref"].get(p)]
    ents.sort(key=lambda e: (e["cls"], e["d"] or 0, e["system"]))
    if not ents:
        return None
    X = {"Dq": 25.0, "B": 40.0, "C": 50.0}[p]
    pts, n_out, rows = [], 0, []
    for e in ents:
        lab = _label(e)
        rows.append(lab)
        pv = e["paper"].get(p)
        if pv is not None:
            x = 100 * _relative_error(pv, e["ref"][p])
            out = abs(x) > X
            n_out += out
            pts.append({"row": lab, "x": max(-X, min(X, x)), "kind": "paper", "out": out,
                        "tip": f"{e['system']}: paper against oracle {_percent_error(x / 100)}"})
        for i, r in enumerate(x for x in _plot_runs(data["runs"]) if x["key"] == e["key"]):
            if r["rel"][p] is None:
                continue
            x = 100 * r["rel"][p]
            out = abs(x) > X
            n_out += out
            pts.append({"row": lab, "x": max(-X, min(X, x)), "kind": "model", "cond": r["cond"], "out": out, "j": i,
                        "tip": f"{e['system']} · {_model_label(r['model'])} {r['cond']} k{r['k']}: "
                               f"{_percent_error(r['rel'][p])} ({_number(r['vals'][p])} {UNIT})"})
    tol = 100 * next(e["tol"][p] for e in ents)
    return {"param": p, "rows": rows, "pts": pts, "dom": [-X, X], "tol": tol, "n_out": n_out, "left": 112, "width": 120,
            "xLabel": f"Relative error of {p} against the oracle (%)",
            "conds": [c for c in COND_ORDER if any(q.get("cond") == c for q in pts)]}


def _figure(kind: str, spec: dict, caption: str, alt: str) -> dict:
    """A figure of this page's own drawing code: the data, the texts and the points in words for the <noscript>."""
    return {"kind": kind, "spec": spec, "caption": caption, "alt": alt, "tips": [q["tip"] for q in spec["pts"][:200]]}


def _figures(data: dict) -> tuple[list[dict], list[dict]]:
    par, rel = [], []
    for p in PARAMS:
        s = _parity_spec(p, data)
        if s:
            note = (f" {page.plural(s['n_out'], 'point')} {'lies' if s['n_out'] == 1 else 'lie'} outside the range and "
                    f"{'is drawn as an open symbol' if s['n_out'] == 1 else 'are drawn as open symbols'} at the edge."
                    if s["n_out"] else "")
            par.append(
                _figure(
                    "parity",
                    s,
                    f"Parity {p}: model and paper against the oracle, band ±{_number(100 * s['tol'], 0)} %.{note}",
                    f"Parity plot {p}: model value against oracle value with tolerance band",
                )
            )
        s = _relative_error_spec(p, data)
        if s:
            note = (f" {s['n_out']} points beyond ±{_number(s['dom'][1], 0)} % stand as open symbols at the edge."
                    if s["n_out"] else "")
            rel.append(_figure("relerr", s, f"Relative error of {p} per system, band ±{_number(s['tol'], 0)} %.{note}",
                               f"Dot plot of the relative error of {p} per system, a marker per condition"))
    return par, rel


def _group_label(cls: str) -> str:
    return f"{CLASS_SHORT[cls]} · {CLASS_LABEL[cls]}"


def _accuracy(data: dict) -> list[dict]:
    """Per class of task: the rows of the share chart and of the table beside it."""
    groups: dict = {}
    for r in data["runs"]:
        groups.setdefault(data["entries"][r["key"]]["cls"], []).append(r)
    out = []
    for cls, rs in sorted(groups.items()):
        cells: dict = {}
        for r in rs:
            cells.setdefault((r["model"], r["cond"], str(r["effort"])), []).append(r)
        efforts: dict = {}
        for m, _c, ef in cells:
            efforts.setdefault(m, set()).add(ef)
        rows, tab = [], []
        for (m, c, ef), items in sorted(
            cells.items(), key=lambda kv: (comparison.model_key(kv[0][0]), kv[0][1], kv[0][2])
        ):
            cnt = {k: sum(1 for r in items if r["outcome"] == k) for k in page.SEG_KEYS}
            n_eval = sum(cnt[k] for k in ("correct", "wrong", "harness"))
            lab = f"{_model_label(m)} · {c}" + (f" · {ef}" if len(efforts[m]) > 1 else "")
            pairs = page.task_pairs((r["key"], r["outcome"] == "correct") for r in items if r["evaluable"])
            row = page.rate_row(lab, c, cnt, n_eval, len(items), pairs)
            rows.append(row)
            shown = row["p"] is not None and not row["few"]
            tab.append({"label": lab, "correct": row["correct"], "n_eval": row["n_eval"],
                        "share": _number(row["p"], 0) + " %" if shown else "–",
                        "ci": f"{_number(row['lo'], 0)} to {_number(row['hi'], 0)} %" if shown
                        else page.few_text(row["n_eval"]) if row["few"] else "–",
                        "harness": cnt["harness"], "na429": cnt["na429"]})
        title = _group_label(cls)
        out.append(
            {
                "title": title,
                "alt": f"{title}: share of correct answers with 95 % interval per model and condition",
                "rows": rows,
                "table": tab,
            }
        )
    return out


def _facts(data: dict) -> list[dict]:
    """The tiles: a short value and a caption that says what it counts."""
    runs = data["runs"]
    n_ev = sum(r["evaluable"] for r in runs)
    models = [_model_label(m) for m in sorted({r["model"] for r in runs}, key=comparison.model_key)]
    n429 = sum(r["outcome"] == "na429" for r in runs)
    facts = [
        ("Systems", str(len(data["shown"])),
         f"with runs, of {page.plural(len(data['entries']), 'pilot task')} in literature_all, experimental and "
         "literature_new"),
        ("Runs", str(len(runs)), f"{n_ev} evaluable; run sets: {', '.join(sorted({r['set'] for r in runs})) or '–'}"),
        ("Not evaluable", str(n429), "HTTP 429 or another API error"),
        ("Models", str(len(models)), ", ".join(models) or "–"),
    ]
    return [{"name": k, "value": v, "caption": c} for k, v, c in facts]


def _tolerance(data: dict) -> dict:
    """The tolerances of the fit classes in percent, for the box on the method."""
    tol = next(
        (e["tol"] for e in data["entries"].values() if e["cls"] in FIT_CLASSES), {"Dq": 0.05, "B": 0.10, "C": 0.15}
    )
    return {"Dq": _number(100 * (tol.get("Dq") or 0.05), 0), "B": _number(100 * (tol.get("B") or 0.1), 0),
            "C": _number(100 * (tol.get("C") or 0.15), 0)}


def _exclusions(data: dict) -> list[dict]:
    out = []
    for x in data["exclusions"]:
        p = paper_values(data["csv"].get(_norm_name(x["system"])))
        fit = x.get("fit") or {}
        fit_txt = (
            f"Dq {_number(fit.get('Dq'), 0)}, B {_number(fit.get('B'), 0)}, C/B {_number(fit.get('CB'), 2)}"
            if fit.get("Dq") else "–"
        )
        out.append({"system": x["system"], "d": _text(x["d"]), "reason": x["reason"], "fit": fit_txt,
                    "dq": _number(p.get("Dq"), 0), "dqb": _number(p.get("DqB"), 2), "cb": _number(p.get("CB"), 2)})
    return out


def _systems(data: dict) -> list[dict]:
    by_key: dict = {}
    for r in data["runs"]:
        by_key.setdefault(r["key"], []).append(r)
    ents = sorted(
        (e for e in data["entries"].values() if e["key"] in by_key), key=lambda e: (e["cls"], e["d"] or 0, e["system"])
    )
    return [_system_card(e, by_key[e["key"]], data["out_dir"]) for e in ents]


def context(data: dict) -> dict:
    """What the page template needs, from the data of `collect`: text, numbers, lists and dicts, no markup."""
    parity, relerr = _figures(data)
    return {
        "title": "Fit results against the literature",
        "date": data["date"],
        "facts": _facts(data),
        "notes": list(data["notes"]),
        "tolerance": _tolerance(data),
        "groups": _accuracy(data),
        "parity": parity,
        "relerr": relerr,
        "cond_items": [{"cond": c, "name": page.COND_NAMES[c], "shape": COND_SHAPE[c]} for c in COND_ORDER],
        "card_keys": ("correct", "wrong", "harness", "na429"),
        "systems": _systems(data),
        "exclusions": _exclusions(data),
        "unit": UNIT,
    }


def build_html(data: dict) -> str:
    """The whole page from the data of `collect`."""
    ctx = context(data)
    return page.render("literature.html.j2", **ctx, ctx=ctx)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="tsbench report literature", description=__doc__.split("\n")[0])
    ap.add_argument("--runs", action="append", required=True, metavar="DIR",
                    help="a run set, or a folder holding run sets (repeatable)")
    ap.add_argument("--out", required=True, metavar="FILE")
    a = ap.parse_args(argv)
    out = pathlib.Path(a.out)
    data = collect(run_sets_in(a.runs), out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build_html(data), encoding="utf-8")
    ev = sum(r["evaluable"] for r in data["runs"])
    print(f"wrote {out}: {len(data['shown'])} systems/tasks with runs, {len(data['runs'])} runs ({ev} evaluable), "
          f"{len(data['exclusions'])} excluded systems")
    for n in data["notes"]:
        print("note:", n, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
