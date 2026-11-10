"""The full report: one self-contained fact page about the run sets and the benchmark code.

    tsbench report full --runs DIR [--runs DIR2 ...] --out REPORT.html [--title T] [--no-gallery] [--no-figures]
                        [--coverage COVERAGE.json [--mutation DIR [DIR ...]]]
                        [--split pilot|confirmatory] [--i-have-preregistered DOI]
                        [--page-budget MB] [--publication] [--images DIR] [--redactions FILE]

The page has six tabs (`TABS`): the models, the tasks, the published spectra, the checks of the benchmark code (with
`--coverage`, a coverage.py JSON with `pytest.log` beside it, and `--mutation`, one or more folders of
`<shard>/<shard>.json`), the gallery and code of the runs, and the method and platform. Each tab has a table of
contents of three levels (`context()["toc"]`). Where each figure sits, at which width and with which question as its
caption is data (`PLACEMENT`); the last section of a tab with figures lists them all. Every number comes from
report/facts.py and report/method.py; every figure is a static SVG of report/svg/. The page states no interpretation.
Every model of the run sets stands on the same pages, in the order of `base.model_key`: there is one layout and one
table of contents. A table has one row per model where its rows differ by model, a task or a system has one row with
the answers of every model, and each figure of a page of several models is its all-models version (`ALL_MODELS`,
`_all_models_figures`) on one scale. With one model the tables have no model column and the figures are those of one
run set (`_models_figures`).
The page is one file. It holds every image and every code block of the runs, whole, and the per-run figures, so it may
reach 100 MB; `--page-budget MB` limits what images and figures may take, the rest being only a link to a file beside
the page (`gallery.ImagePool`). `--publication`, implied by the confirmatory split, refuses to write a page with such a
link (`page.local_links`). `--images DIR` adds the images a run left outside its folder, from the index
`<DIR>/<run set>.index.csv` (`gallery.image_index`). `--redactions FILE` is for a page built from a published copy
whose machine paths were replaced: a transcript logged in the file counts as matching the hash of its manifest, and the
page says how many did (`method.read_redactions`).
The page reads the tasks of one split (`--split`, default pilot). A run set of the confirmatory split is refused
without `--i-have-preregistered <DOI>`, and every run set must record the split asked for. A confirmatory page names
the DOI in its header and opens the tab Models with the preregistered tests of each run set that holds
hypotheses.json (`PREREG`, report/prereg.py).
Like the gallery, the report writes scores.csv and per-run figures into the run folders when they are missing; build
it from a copy of runs you want untouched. The page is templates/full.html.j2.
"""
from __future__ import annotations

import argparse
import datetime
import pathlib
import re
import sys
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from tsbench.report import comparison, facts, gallery, method, page, prereg, taskview
from tsbench.report.base import SPLITS, display_model, model_key, split_hash, split_refusal
from tsbench.report.svg import (
    bars,
    base,
    bundle,
    dashboard,
    dots,
    errors,
    flows,
    ledger,
    maps,
    marimekko,
    matrix,
    models,
    outcome,
    pack,
    platform,
    runs,
    scatter,
    toolout,
    treemap,
)
from tsbench.score.artifacts import TranscriptCache
from tsbench.score.run_sets import run_sets_in

__all__ = ["ALL", "ALL_MODELS", "PLACEMENT", "PREREG", "REPORT_VERSION", "TABS", "build_html", "context", "main",
           "run_sets_in"]

REPORT_VERSION = "4"
_ROOT = pathlib.Path(__file__).resolve().parents[3]
TESTS = _ROOT / "tests"  # the test suite of a checkout, counted by folder
SRC = pathlib.Path(__file__).resolve().parents[1]  # the tsbench package: the import graph of the code checks

# The tabs in order: (id, label). A tab is <section class="tab" id="tab-<id>">; the address #<id> shows it.
TABS = [("models", "Models"), ("tasks", "Tasks"), ("spectra", "Published spectra"), ("checks", "Code checks"),
        ("gallery", "Gallery and code"), ("platform", "Method and platform")]
ALL = "All figures"
# Per tab its h2 sections in order, per section its figures: (key, width "full" | "half", question). The figures
# under ALL are drawn there, below the list of every figure of the tab.
PLACEMENT: dict[str, list[tuple[str, list[tuple[str, str, str]]]]] = {
    "models": [
        ("Overview", [("share", "half", "How often is each condition correct?"),
                      ("paired", "half", "How much does C change the share against A and B on the same tasks?")]),
        ("Outcomes", [("outcome", "half", "Which kind of error does each condition make?")]),
        ("Error size", [("swarm", "full", "How far outside the tolerance do the wrong answers lie?")]),
        ("Tool use", [("sunburst", "half", "Which call paths do B and C take, and how do they end?"),
                      ("tool_output", "full", "How much text does each tool return to the model?")]),
        ("Cost", [("cost", "full", "How do the runs differ in turns, tokens, time and cost?")]),
        (ALL, [("upset", "half", "Which combination of conditions solves each task?"),
               ("matrix", "full", "Which server tool follows which in C?"),
               ("cost_map", "full", "Where does the cost go, by class and task?")]),
    ],
    "tasks": [
        ("Classes", [("classes", "half", "Which classes does each condition solve?")]),
        ("Task ledger", [("ledger", "full", "How far from passing is each answer, task by task?")]),
        ("Tasks", []),
        (ALL, []),
    ],
    "spectra": [
        ("Systems", []),
        ("Agreement", [("literature", "full",
                        "How far do the paper value and each answer lie from the oracle fit?")]),
        (ALL, []),
    ],
    "checks": [
        ("Overview", []),
        ("Tests", [("per_folder", "half", "Where are the tests?")]),
        ("Coverage", [("packages", "half", "Which packages are covered least?"),
                      ("treemap", "full", "Which modules have uncovered statements?")]),
        ("Mutation", [("shards", "half", "How many mutants does each shard kill?"),
                      ("mutants", "full", "Which modules leave mutants alive?"),
                      ("scatter", "half", "Does line coverage go with the mutation score per module?")]),
        (ALL, [("bundle", "full", "Which modules import which?")]),
    ],
    "gallery": [("Diagrams", []), ("Run gallery", []), ("Code", []), ("Solution path B", [])],
    "platform": [
        ("Identity", []), ("Protocol", []), ("Statistics", []), ("Provenance", []), ("Exclusions and limits", []),
        ("Where the runs ran", []),
        ("Schedule", [("schedule", "full", "When did each run start and how long did it take?")]),
        ("Files and hashes", [("tree", "full", "Which file's hash is recorded where?")]),
        ("Data notes", []),
        (ALL, []),
    ],
}
WIDTH = {"full": base.FULL_W, "half": base.HALF_W}
# The figures of the tabs Models, Tasks and Published spectra on a page of several models: per key its question. They
# take the place of their one-model figure and are drawn at the full width.
ALL_MODELS = {
    "share": "How often does each model answer correctly under A, B and C?",
    "paired": "How much does C change the share, model by model?",
    "outcome": "Which kind of error does each model make under each condition?",
    "swarm": "How far outside the tolerance do the wrong answers of each model lie?",
    "sunburst": "Which call paths does each model take, and how do they end?",
    "tool_output": "How much text does each tool return to each model?",
    "cost": "How do tokens and the share correct differ by model and condition?",
    "upset": "Which combination of conditions solves each task, model by model?",
    "matrix": "Which server tool follows which in C, model by model?",
    "cost_map": "Where does the cost of each model go, by class and task?",
    "classes": "Which classes does each model solve under each condition?",
    "ledger": "How far from passing is each answer of each model, task by task?",
    "literature": "How far do the paper value and the answers of each model lie from the oracle fit?",
}
MAP_HEIGHT = 360.0, 96.0  # the map of the model that cost most, and the lowest map that still holds its headers
COMPARE_PAIRS = ("C − A", "C − B")  # the paired differences of the comparison table
# The section that opens the tab Models of a confirmatory page whose run sets hold hypotheses.json, and its tables.
PREREG = "Preregistered tests"
PREREG_TABLES = (("primary", "Primary family"), ("secondary", "Secondary tests"), ("mcnemar", "McNemar tests"),
                 ("efficiency", "Efficiency ratios"))
# The tables a table-of-contents entry points to: per tab and section (id, title). The template gives each the id.
TABLES = {
    "models": {"Overview": [("tbl-models", "Models"), ("tbl-shares", "Share correct"),
                            ("tbl-paired", "Paired differences")],
               "Outcomes": [("tbl-outcome", "Runs per category")],
               "Tool use": [("tbl-tools", "Runs with and without a call"), ("tbl-paths", "Call paths")],
               "Cost": [("tbl-medians", "Median per run"), ("tbl-usd", "Cost in USD")]},
    "tasks": {"Classes": [("tbl-classes", "Classes")]},
    "spectra": {"Systems": [("tbl-systems", "Systems")]},
    "checks": {"Tests": [("tbl-folders", "Test functions per folder")],
               "Coverage": [("tbl-packages", "Coverage per package")],
               "Mutation": [("tbl-shards", "Mutation per shard")]},
    "platform": {"Protocol": [("tbl-conditions", "Conditions"), ("tbl-settings", "Run settings")],
                 "Statistics": [("tbl-methods", "Methods"), ("tbl-intervals", "Class intervals")],
                 "Exclusions and limits": [("tbl-exclusions", "Exclusions"), ("tbl-limits", "Limits")]},
}
MUTANT_SEGMENTS = [("killed", "killed", "g0"), ("survived", "survived", "g4"), ("timeout", "timed out", "muted")]
NOT_RECORDED = facts.NOT_RECORDED
NO_REAL_COST = "no real cost (gateway)"


def section_id(tab: str, title: str) -> str:
    """The html id of a section (h2) of a tab: `models-error-size`."""
    return f"{tab}-" + re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def _prefixes(names: list[str]) -> dict[str, str]:
    """The id prefix of what each model repeats (its solution paths): "" for a single model, else the slug of its
    name and "-", unique."""
    if len(names) <= 1:
        return dict.fromkeys(names, "")
    out: dict[str, str] = {}
    for name in names:
        slug = base_slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "model"
        n = 1
        while f"{slug}-" in out.values():
            n += 1
            slug = f"{base_slug}-{n}"
        out[name] = f"{slug}-"
    return out


def _html_id(prefix: str, text: str) -> str:
    return prefix + re.sub(r"[^A-Za-z0-9_-]", "-", str(text))


def task_href(task: str) -> str:
    """The link of a task mark or label to the row of its task in the tab Tasks."""
    return f"#task-{task}"


def _stamp(iso: str | None, day: bool = True) -> str:
    """"2026-10-30 22:01" from an ISO-8601 UTC time; without `day` "10-31 01:27"."""
    if not iso:
        return "–"
    t = datetime.datetime.fromisoformat(iso).astimezone(datetime.UTC)
    return t.strftime("%Y-%m-%d %H:%M" if day else "%m-%d %H:%M")


def _spread(runs_: list[dict], key: str) -> bool:
    vals = {r["values"].get(key) for r in runs_} - {None}
    return len(vals) > 1


def _cost_rows(b: dict) -> list[dict]:
    """Per condition: the summed cost, the cost of the correct runs and the cost per correct run (USD), and the runs
    without a cost. A condition none of whose runs has a cost says "not recorded", never 0.00. For a model that is
    not a Claude model (a gateway run) the figure is a list-price estimate of Claude Code and every cost says
    "no real cost (gateway)"."""
    out = []
    for c in b["header"]["conds"]:
        rs = [r for r in b["runs"] if r["cond"] == c]
        if (b.get("header") or {}).get("cost_is_estimate"):
            # Claude Code prices a model it does not know at a default list price: the figure is no cost of the run
            ok = [r for r in rs if r["outcome"] == "correct"]
            out.append({"cond": c, "correct": len(ok), "missing": len(rs), "total": NO_REAL_COST,
                        "correct_cost": NO_REAL_COST, "per_correct": NO_REAL_COST if ok else "–"})
            continue
        costs = [r["values"].get("cost_usd") for r in rs]
        ok = [r for r in rs if r["outcome"] == "correct"]
        row = {"cond": c, "correct": len(ok), "missing": sum(v is None for v in costs)}
        if all(v is None for v in costs):
            out.append({**row, "total": NOT_RECORDED, "correct_cost": NOT_RECORDED,
                        "per_correct": NOT_RECORDED if ok else "–"})
            continue
        total = sum(v or 0.0 for v in costs)
        spent = sum(r["values"].get("cost_usd") or 0.0 for r in ok)
        out.append({**row, "total": base.fixed(total, 2), "correct_cost": base.fixed(spent, 2),
                    "per_correct": base.fixed(total / len(ok), 2) if ok else "–"})
    return out


_MEDIAN_ND = {"output_tokens": 0, "num_turns": 0, "api_duration_s": 0, "cost_usd": 2}


def p_text(p: float | None) -> str:
    """A p value with three decimals; an exact p below 0.0005 would round to 0.000, so it reads `< 0.001`."""
    if p is None:
        return "–"
    return "< 0.001" if p < 0.0005 else base.fixed(p, 3)


def _changed_lines(diff: str) -> str:
    """The changed lines of one mutant diff (`-` and `+` lines): the file header, the hunk header and the context
    lines repeat from mutant to mutant of one function and are left out."""
    lines = diff.splitlines()
    body = next((i + 1 for i, ln in enumerate(lines) if ln.startswith("@@")), None)
    if body is None:
        body = sum(1 for ln in lines[:2] if ln.startswith(("--- ", "+++ ")))
    return "\n".join(ln for ln in lines[body:] if ln.startswith(("-", "+")))


def _view(b: dict) -> None:
    """Text forms of the numbers the template prints; the numbers themselves stay as facts.py returned them."""
    _header_text(b["header"])
    for s in b["literature"]:
        s["dn_text"] = f"d{s['dn']} {s.get('geometry') or ''}".strip()
    estimate = bool(b["header"].get("cost_is_estimate"))
    b["cost"]["medians_text"] = [
        {"cond": m["cond"], **{k: base.number(None if estimate and k == "cost_usd" else m.get(k), _MEDIAN_ND.get(k, 0))
                               for k in b["cost"]["median_keys"]}}
        for m in b["cost"]["medians"]]
    b["cost"]["table"] = _cost_rows(b)
    for x in b["shares"]:
        x["share_text"] = f"{base.round_half_up(100 * x['share'])} %"
        x["ci_text"] = f"{base.round_half_up(100 * x['lo'])}–{base.round_half_up(100 * x['hi'])} %"
    for x in b["paired"]:
        x["diff_text"] = page.signed(100 * x["diff"]) + " pp"
        x["ci_text"] = f"{page.signed(100 * x['lo'])} to {page.signed(100 * x['hi'])}"
        x["p_text"] = p_text(x["p"])


def _header_text(h: dict) -> None:
    h["start_text"], h["end_text"] = _stamp(h["start"]), _stamp(h["end"], day=False)


def _checks_view(c: dict) -> None:
    total = c["coverage"]["total"]
    total["pct_text"] = f"{base.fixed(total['pct'], 1)} %"
    total["reported_text"] = (f"{base.fixed(total['reported_pct'], 1)} %" if total.get("reported_pct") is not None
                              else None)
    for p in c["coverage"]["packages"]:
        p["pct_text"] = base.fixed(p["pct"], 1)


def _interval_text(lo: float | None, hi: float | None, unit: str = " %") -> str:
    return "–" if lo is None or hi is None else f"{base.round_half_up(100 * lo)}–{base.round_half_up(100 * hi)}{unit}"


def _compare_view(rows: list[dict]) -> list[dict]:
    """Text forms of the comparison rows of `facts.models_overview`: per condition "k of n", the share and its
    interval; per pair of `COMPARE_PAIRS` the difference and its interval in percentage points."""
    for x in rows:
        x["cells_text"] = {c: {"kn": f"{v['k']} of {v['n']}",
                               "share": "–" if v.get("share") is None else f"{base.round_half_up(100 * v['share'])} %",
                               "ci": _interval_text(v.get("lo"), v.get("hi"))} for c, v in x["cells"].items()}
        x["pairs_text"] = {p: {"diff": page.signed(100 * v["diff"]) + " pp",
                               "ci": f"{page.signed(100 * v['lo'])} to {page.signed(100 * v['hi'])}"
                               if v.get("lo") is not None and v.get("hi") is not None else "–"}
                           for p, v in x["paired"].items() if p in COMPARE_PAIRS and v.get("diff") is not None}
    return rows


def _page_header(heads: list[dict]) -> dict:
    """The header of the page: the header of the one model, or of several models merged (the model chip counts the
    models, the run counts add up, the other chips list the distinct values)."""
    if len(heads) == 1:
        return heads[0]

    def distinct(key: str) -> str:
        return ", ".join(dict.fromkeys(str(h[key]) for h in heads if h.get(key)))

    planned = [h["k_planned"] for h in heads if h.get("k_planned") is not None]
    starts, ends = [h["start"] for h in heads if h.get("start")], [h["end"] for h in heads if h.get("end")]
    h = {**heads[0], "model": f"{len(heads)} models", "models": [x["model"] for x in heads],
         "endpoint": distinct("endpoint"), "effort": distinct("effort"),
         "conds": [c for c in base.CONDS if any(c in x["conds"] for x in heads)],
         "n_tasks": max(x["n_tasks"] for x in heads), "n_classes": max(x["n_classes"] for x in heads),
         "k": max(x["k"] for x in heads), "k_planned": max(planned, default=None),
         "n_runs": sum(x["n_runs"] for x in heads), "n_evaluable": sum(x["n_evaluable"] for x in heads),
         "oracle": distinct("oracle") or None, "commit": distinct("commit") or None,
         "start": min(starts, default=None), "end": max(ends, default=None)}
    _header_text(h)
    return h


# ---------------------------------------------------------------- figures


def _models_figures(b: dict, href: Callable[[str], str] = task_href) -> dict[str, Callable[[float], str]]:
    """Per figure key of the tabs Models, Tasks and Published spectra: the builder at a given width, for one model.
    `href` is the link of a task mark to its row."""
    c_calls = bool([r for r in b["calls"] if r["cond"] == "C"])
    estimate = bool(b["header"].get("cost_is_estimate"))
    axes = [a for a in b["cost"]["axes"] if a[0] != "duration_s" and _spread(b["cost"]["runs"], a[0])
            and not (estimate and a[0] == "cost_usd")]
    return {
        "share": lambda w: dashboard.share_intervals(b["shares"], width=w),
        "paired": lambda w: dashboard.paired_diffs(b["paired"], width=w),
        "outcome": lambda w: outcome.outcome_diverging(b["outcome"], b["categories"], width=w),
        "swarm": lambda w: errors.beeswarm(b["swarm"], width=w, task_href=href),
        "sunburst": lambda w: flows.sunburst(b["calls"], width=w) if b["calls"] else "",
        "tool_output": lambda w: toolout.tool_output(b["tool_output"], width=w) if b["tool_output"] else "",
        "cost": lambda w: runs.parallel_coords(b["cost"]["runs"], axes, width=w),
        "upset": lambda w: outcome.upset(b["upset"], width=w, excluded=b.get("upset_excluded") or (),
                                      conds=b["header"]["conds"]),
        "matrix": lambda w: matrix.transition_matrix(b["tools"], b["transitions"], width=w) if c_calls else "",
        "cost_map": lambda w: "" if estimate else maps.run_map(
            [{**r, "value": r["values"].get("cost_usd") or 0.0} for r in b["runs"]], b["categories"], "USD", width=w),
        "classes": lambda w: dots.class_dots(
            [{"class": x["class"], "n": x["n"], "k": x["k"], "n_by": x["n_by"]} for x in b["tasks_view"]], width=w),
        "ledger": lambda w: ledger.task_ledger(b["ledger"], width=w, task_href=href),
        "literature": lambda w: dots.literature_dots(b["literature"], width=w, task_href=href)
        if b["literature"] else "",
    }


def _checks_figures(c: dict) -> dict[str, Callable[[float], str]]:
    mut = c["mutation"]
    mod_cols = [{"label": base.module_name(m["module"]), "group": s["name"],
                 "parts": {"killed": m["killed"], "survived": m["survived"], "timeout": m["timeout"]}}
                for s in mut["shards"] for m in sorted(s["modules"], key=lambda m: -(m["killed"] + m["survived"]))]
    shard_rows = [{"label": s["name"], "pct": s["score"]} for s in mut["shards"]]
    shard_rows += [{"label": p, "pct": None} for p in c["not_mutated"]]
    return {
        "per_folder": lambda w: bars.hbars(c["tests_per_folder"], "test functions", width=w)
        if c["tests_per_folder"] else "",
        "packages": lambda w: bars.score_bars(
            [{"label": p["package"], "pct": p["pct"]} for p in c["coverage"]["packages"]], width=w,
            title="Line coverage per package, 0 to 100 percent", none_text="no coverage"),
        "treemap": lambda w: treemap.treemap(c["coverage"]["files"], width=w),
        "shards": lambda w: bars.score_bars(shard_rows, width=w) if shard_rows else "",
        "mutants": lambda w: marimekko.marimekko(mod_cols, MUTANT_SEGMENTS, unit="mutants", width=w)
        if mod_cols else "",
        "scatter": lambda w: scatter.coverage_mutation(c["points"], c["unmutated"], width=w),
        "bundle": lambda w: bundle.edge_bundling(c["imports"]["modules"], c["imports"]["edges"], width=w),
    }


def _platform_figures(p: dict) -> dict[str, Callable[[float], str]]:
    return {"schedule": lambda w: platform.schedule(p["schedule"]["runs"], p["schedule"]["manifest"], width=w),
            "tree": lambda w: platform.file_tree(p["tree"]["entries"], p["tree"]["chain"], width=w)}


def _categories(benches: Sequence[dict]) -> list[tuple[str, str]]:
    """The outcome categories of several models, in the order of `facts.CATEGORIES` and `facts.EXTRA`."""
    seen = {k: label for b in benches for k, label in b["categories"]}
    rank = {k: i for i, (k, _) in enumerate([*facts.CATEGORIES, *facts.EXTRA])}
    return sorted(seen.items(), key=lambda kv: rank.get(kv[0], len(rank)))


def _bubble_points(benches: Mapping[str, dict]) -> list[dict]:
    """One point per model and condition: the median output tokens of `medians` and the share correct of `shares`."""
    out = []
    for model, b in benches.items():
        medians = {m["cond"]: m for m in b["cost"]["medians"]}
        out += [{"model": model, "label": display_model(model), "cond": s["cond"], "share": s["share"], "k": s["k"],
                 "n": s["n"], "tokens": medians.get(s["cond"], {}).get("output_tokens")} for s in b["shares"]]
    return out


def _cost_maps(benches: Mapping[str, dict], categories: list[tuple[str, str]],
               width: float) -> list[tuple[str, str]]:
    """The cost map of each model with a real cost, at a height in proportion to its total (`MAP_HEIGHT`): one area
    scale, except for a map raised to the least height that stays readable, which says so. A gateway model has no real
    cost and no map."""
    rows = {m: [{**r, "value": r["values"].get("cost_usd") or 0.0} for r in b["runs"]] for m, b in benches.items()
            if not b["header"].get("cost_is_estimate")}
    totals = {m: sum(r["value"] for r in rs) for m, rs in rows.items()}
    top = max(totals.values(), default=0.0) or 1.0
    tall, low = MAP_HEIGHT
    return [(m, maps.run_map(rows[m], categories, "USD", width=width, height=max(low, tall * totals[m] / top),
                             raised=tall * totals[m] / top < low) if m in rows else "") for m in benches]


def _all_models_figures(benches: Mapping[str, dict], compare: list[dict],
                        href: Callable[[str], str] = task_href) -> dict[str, Callable[[float], str]]:
    """Per figure key of the tabs Models, Tasks and Published spectra: the builder at a given width, for all models on
    one scale. A model is a row or a band where the figure can hold it; a figure that cannot is drawn once per model,
    as panels of `base.panels`."""
    names, bs = list(benches), list(benches.values())
    categories = _categories(bs)
    tools = sorted({t for b in bs for t in b["tools"]})
    transitions = max((n for b in bs for n in b["transitions"].values()), default=0)
    scale = outcome.upset_scale([b["upset"] for b in bs])

    def small(title: str, draw: Callable[[dict, float], str], w: float, cols: int = 2) -> str:
        pw = base.panel_width(w, cols)
        return base.panels(title, [(m, draw(b, pw)) for m, b in benches.items()], width=w, cols=cols)

    def matrix_of(b: dict, w: float) -> str:
        if not [r for r in b["calls"] if r["cond"] == "C"]:
            return ""
        return matrix.transition_matrix(tools, b["transitions"], width=w, top=transitions)

    return {
        "share": lambda w: models.model_shares(compare, width=w),
        "paired": lambda w: models.model_paired(compare, width=w),
        "outcome": lambda w: outcome.outcome_diverging(
            [{**o, "label": f"{m} · {o['cond']}", "group": m} for m, b in benches.items() for o in b["outcome"]],
            categories, width=w),
        "swarm": lambda w: errors.beeswarm(
            [{**g, "model": m, "label": f"{m} · {g['cond']}"} for m, b in benches.items() for g in b["swarm"]],
            width=w, task_href=href),
        "sunburst": lambda w: small("Sunburst of call paths per model",
                                    lambda b, p: flows.sunburst(b["calls"], width=p) if b["calls"] else "", w),
        "tool_output": lambda w: toolout.tool_rows([(m, b["tool_output"]) for m, b in benches.items()], width=w),
        "cost": lambda w: models.model_bubbles(_bubble_points(benches), width=w),
        "upset": lambda w: small("Tasks per subset of conditions per model", lambda b, p: outcome.upset(
            b["upset"], width=p, excluded=b.get("upset_excluded") or (), conds=b["header"]["conds"], scale=scale), w),
        "matrix": lambda w: small("Tool transitions per model", matrix_of, w, cols=1),
        "cost_map": lambda w: base.panels("USD of every run per model", _cost_maps(benches, categories, w), width=w,
                                          cols=1),
        "classes": lambda w: models.class_heat(
            [{"model": m, "conds": b["header"]["conds"], "classes": b["tasks_view"]} for m, b in benches.items()],
            comparison.heat_color, width=w),
        "ledger": lambda w: small("Task ledger per model",
                                  lambda b, p: ledger.task_ledger(b["ledger"], width=p, task_href=href), w, cols=1),
        "literature": lambda w: small(
            "Reported against oracle values per model",
            lambda b, p: dots.literature_dots(b["literature"], width=p, task_href=href) if b["literature"] else "",
            w, cols=1),
    } if names else {}


def _placement(multi: bool) -> dict[str, list[tuple[str, list[tuple[str, str, str]]]]]:
    """`PLACEMENT`; on a page of several models the figures of `ALL_MODELS` take their question and the full width."""
    if not multi:
        return PLACEMENT
    return {tab: [(section, [(k, "full", ALL_MODELS[k]) if k in ALL_MODELS else (k, w, q) for k, w, q in figs])
                  for section, figs in sections] for tab, sections in PLACEMENT.items()}


def _draw(builders: dict[str, Callable[[float], str]],
          placement: dict[str, list[tuple[str, list[tuple[str, str, str]]]]] = PLACEMENT) -> dict[str, dict]:
    """Every placed figure that has a builder, drawn at its width: key -> {tab, section, width, question, id, svg}.
    The id is `fig-<key>`. A builder that returns nothing (no data) leaves its figure out."""
    out = {}
    for tab, sections in placement.items():
        for section, figs in sections:
            for key, width, question in figs:
                if key not in builders:
                    continue
                svg = builders[key](WIDTH[width])
                if svg:
                    out[key] = {"tab": tab, "section": section, "width": width, "question": question,
                                "id": f"fig-{key}", "svg": page.svg(svg)}
    return out


# ---------------------------------------------------------------- gallery anchors, answers, notes


def _gallery_anchors(gal: dict | None) -> dict[str, dict[tuple[str, str], str]]:
    """Give every run card of the gallery an html id (`card["anchor"]`, `taskview.run_anchor` of its head) and return
    per model the id of the first card of each (condition, task): the target of an answer whose run card is missing."""
    first: dict[str, dict[tuple[str, str], str]] = {}
    if not gal:
        return first
    used: set[str] = set()
    for t in gal["run_tasks"]:
        for card in t["cards"]:
            h = card["head"]
            ident = base_id = taskview.run_anchor(h["model"], h["cond"], h["effort"], h["task"], h["k"])
            n = 1
            while ident in used:
                n += 1
                ident = f"{base_id}-s{n}"
            used.add(ident)
            card["anchor"] = ident
            first.setdefault(h["model"], {}).setdefault((h["cond"], h["task"]), ident)
    return first


def _answer_links(b: dict, first: dict[tuple[str, str], str], cards: set[str]) -> None:
    """The link of each answer of the task view to the card of the run it shows (`run_anchor`) when the gallery holds
    it, else the first card of the condition and task, else none."""
    for block in b["tasks_view"]:
        for row in block["tasks"]:
            for cond, a in row["answers"].items():
                anchor = a.get("run_anchor")
                a["href"] = f"#{anchor}" if anchor in cards else \
                    f"#{first[(cond, row['id'])]}" if (cond, row["id"]) in first else None


def _notes(benches: Mapping[str, dict], c: dict | None, p: dict) -> list[dict]:
    """The data notes of the page: of the benchmark, the platform and the mutation shards, each with its source. A note
    of one model's benchmark names the model unless every model has the same note."""
    per = {m: [{**n} for n in b.get("notes") or []] for m, b in benches.items()}
    out = []
    for m, notes in per.items():
        for n in notes:
            common = all(n in other for other in per.values())
            if common and m != next(iter(per)):
                continue
            out.append({**n, "source": "scores" if common else f"scores · {m}"})
    out += [{**n, "source": "platform"} for n in p.get("notes") or []]
    if c:
        out += [{**n, "source": "mutation"} for n in c["mutation"].get("notes") or []]
    return out


def _keep(benches: Mapping[str, dict]) -> set[tuple[str, str, str, int]] | None:
    """The (model, condition, task, k) of the evaluable runs of every model, for the schedule; None when there are no
    runs or a run carries no repetition index."""
    rows = [(m, r) for m, b in benches.items() for r in b["runs"]]
    if not rows or any("k" not in r for _, r in rows):
        return None
    return {(m, r["cond"], r["task"], int(r["k"])) for m, r in rows}


# ---------------------------------------------------------------- table of contents


def _tab_toc(tab: str, figs: dict[str, dict], blocks: list[dict], c: dict | None, gal: dict | None,
             placement: dict = PLACEMENT, multi: bool = False) -> list[tuple[int, str, str]]:
    """The entries of the table of contents of a tab in page order: (level, id, title); level 2 a section, 3 a
    sub-section, 4 a figure, a table or a task."""
    entries: list[tuple[int, str, str]] = []
    for section, placed in placement[tab]:
        if tab == "checks" and c is None and section != "Overview":
            continue
        entries.append((2, section_id(tab, section), section))
        if not (tab == "checks" and c is None):
            entries += [(4, i, title) for i, title in TABLES.get(tab, {}).get(section, [])
                        if multi or i != "tbl-models"]
        entries += _sub_entries(tab, section, blocks, c, gal)
        entries += [(4, figs[k]["id"], q) for k, _, q in placed if k in figs]
    return entries


def _family_title(block: dict, kind: str, title: str) -> str:
    """The title of the Holm table names the family of its block (primary, or the secondary family of plans 2a-2c)."""
    return "Secondary family" if kind == "primary" and block.get("family") == "secondary" else title


def _prereg_toc(blocks: list[dict]) -> list[tuple[int, str, str]]:
    """The entries of the preregistered tests: their section and per block its tables (ids as the macro
    `prereg_tables` of _macros.html.j2 gives them); [] without a block."""
    if not blocks:
        return []
    out = [(2, section_id("models", PREREG), PREREG)]
    for i, b in enumerate(blocks, 1):
        sfx, of = ("", "") if i == 1 else (f"-{i}", f" · {b['set']}")
        out += [(4, f"tbl-hyp-{kind}{sfx}", _family_title(b, kind, title) + of) for kind, title in PREREG_TABLES
                if b[kind]]
    return out


def _sub_entries(tab: str, section: str, blocks: list[dict], c: dict | None,
                 gal: dict | None) -> list[tuple[int, str, str]]:
    """The sub-sections and rows of a section that the table of contents lists."""
    out: list[tuple[int, str, str]] = []
    if (tab, section) == ("tasks", "Tasks"):
        for block in blocks:
            out.append((3, block["anchor"], block["class"]))
            out += [(4, row["anchor"], row["id"]) for row in block["tasks"]]
    elif (tab, section) == ("checks", "Coverage") and c:
        out.append((3, "checks-per-function", "Per function"))
    elif (tab, section) == ("checks", "Mutation") and c:
        out.append((3, "checks-survivors", "Surviving mutants"))
    elif (tab, section) == ("gallery", "Run gallery") and gal:
        out += [(3, _html_id("gal-", cls), cls) for cls in dict.fromkeys(t["cls"] for t in gal["run_tasks"])]
    elif (tab, section) == ("gallery", "Code") and gal:
        out += [(3, f"code-{cond}", f"Condition {cond}") for cond in _code_conds(gal)]
    return out


def _code_conds(gal: dict) -> list[str]:
    return sorted({x["head"]["cond"] for x in gal["code_cards"]})


def _run_classes(gal: dict) -> list[dict]:
    """The run cards of the gallery per class: {class, id, n, tasks}."""
    out: dict[str, dict] = {}
    for t in gal["run_tasks"]:
        block = out.setdefault(t["cls"], {"class": t["cls"], "id": _html_id("gal-", t["cls"]), "n": 0, "tasks": []})
        block["n"] += len(t["cards"])
        block["tasks"].append(t)
    return list(out.values())


# ---------------------------------------------------------------- the page


def context(run_sets, out: pathlib.Path, title: str | None = None, coverage=None, mutation=(),
            with_gallery: bool = True, make_figs: bool = True, budget: int | None = None, split: str = "pilot",
            doi: str | None = None, images: pathlib.Path | None = None,
            redactions: pathlib.Path | None = None) -> dict:
    """The facts of the six tabs, their figures, the method tables, the table of contents and the gallery.
    `coverage` (coverage.py JSON) and `mutation` (folders of `<shard>/<shard>.json`) give the tab Code checks; without
    `coverage` the tab names the missing input. `views` holds per model, in the order of `model_key`, its facts and
    call paths: {model, bench, paths, task_ids}; `task_blocks` and `systems` hold the rows of the tasks and the
    published systems with the answers of every model. `budget` is the size in bytes that the images and figures of the
    gallery may fill the page to, None: no limit. `split` names the tasks that are read; a confirmatory page carries
    `doi` in its header and the preregistered tests in `hypotheses`. `images`: see `gallery.collect_runs`. `redactions`:
    the log of a published copy (`method.read_redactions`)."""
    out = pathlib.Path(out)
    confirmatory = split == "confirmatory"
    reader = TranscriptCache()  # the facts and the gallery read each transcript through it
    benches = facts.benchmarks(run_sets, out, reader, split=split)
    benches = {m: benches[m] for m in sorted(benches, key=model_key)}
    multi = len(benches) > 1
    checks = None
    if coverage:
        checks = facts.checks(pathlib.Path(coverage), [pathlib.Path(m) for m in mutation], SRC,
                              TESTS if TESTS.is_dir() else None)
    plat = facts.platform(run_sets, keep=_keep(benches), split=split)
    log = method.read_redactions(pathlib.Path(redactions)) if redactions else None
    meth = method.facts(run_sets, benches, checks, plat, version=REPORT_VERSION, split=split, doi=doi, redactions=log)
    if checks:
        _checks_view(checks)
    gal = gallery.context(run_sets, out.parent, make_figs, reader, split, budget, images)[0] if with_gallery else None
    first = _gallery_anchors(gal)
    cards = {card["anchor"] for t in gal["run_tasks"] for card in t["cards"]} if gal else set()
    pfx = _prefixes(list(benches))
    views = [_model_view(m, b, first.get(m, {}), cards) for m, b in benches.items()]
    compare = _compare_view(facts.models_overview(benches)) if multi else None
    placement = _placement(multi)
    builders = _platform_figures(plat) | (_checks_figures(checks) if checks else {})
    builders |= _all_models_figures(benches, compare) if compare is not None else _models_figures(views[0]["bench"])
    figs = _draw(builders, placement)
    task_blocks = _task_blocks(views)
    tests = prereg.hypotheses(run_sets) if confirmatory else []
    toc = {tab: _tab_toc(tab, figs, task_blocks, checks, gal, placement, multi) for tab, _ in TABS}
    toc["models"] = _prereg_toc(tests) + toc["models"]
    header = {**_page_header([v["bench"]["header"] for v in views]), "split": split,
              "preregistration": doi if confirmatory else None}
    task_ids = set().union(*(v["task_ids"] for v in views))
    tasks_sha = split_hash(split)
    survivors = _survivors(checks) if checks else []
    unlisted = checks["mutation"]["unlisted"] if checks else []
    return {"title": title or "TS-MCP benchmark report", "header": header, "bench": views[0]["bench"],
            "views": views, "multi": multi, "compare": compare, "compare_conds": header["conds"],
            "task_blocks": task_blocks, "systems": _systems(views),
            "hypotheses": tests, "PREREG": PREREG,
            "checks": checks, "platform": plat, "method": meth, "gal": gal, "figs": figs,
            "solution_paths": [{**sp, "hid": pfx[v["model"]] + sp["id"], "model": v["model"]}
                               for v in views for sp in v["bench"]["solution_paths"]],
            "survivors": survivors, "survivor_rows": survivor_rows(survivors, unlisted=unlisted),
            "run_classes": _run_classes(gal) if gal else [], "code_conds": _code_conds(gal) if gal else [],
            "task_ids": task_ids, "task_href": _task_linker(task_ids),
            "notes": _notes(benches, checks, plat), "toc": toc,
            "tabs": TABS, "placement": placement, "ALL": ALL,
            "compare_pairs": COMPARE_PAIRS, "section_id": section_id,
            "ident": {"version": REPORT_VERSION, "tasks": (tasks_sha or "")[:7],
                      "commit": header["commit"] or ""}}


def _survivors(checks: dict) -> list[dict]:
    """Surviving mutants per module and function; each diff is cut to its changed lines."""
    out = pack.by_module(checks["survivors"])
    for m in out:
        for fn in m["functions"]:
            fn["mutants"] = [{**x, "diff": _changed_lines(x["diff"])} for x in fn["mutants"]]
    return [{**m, "n": sum(len(f["mutants"]) for f in m["functions"])} for m in out]


def survivor_rows(survivors: list[dict], modules: int = 15, functions: int = 3,
                  unlisted: Sequence[Mapping[str, Any]] = ()) -> list[dict]:
    """The rows of the table of surviving mutants: the first `modules` modules with their first `functions` functions
    each, then one row for the functions left out of a module, one for the modules left out and one per shard for the
    survivors it counts but does not list (`unlisted`: `{"shard", "survived"}`), so the column adds up to every
    survivor the shards count. A row is `{"module", "function", "survived", "other"}`."""
    rows = []
    for m in survivors[:modules]:
        fns = m["functions"]
        rows += [{"module": m["module"], "function": f["function"], "survived": len(f["mutants"]), "other": False}
                 for f in fns[:functions]]
        if len(fns) > functions:
            rows.append({"module": m["module"], "function": f"{len(fns) - functions} other functions",
                         "survived": sum(len(f["mutants"]) for f in fns[functions:]), "other": True})
    if len(survivors) > modules:
        rest = survivors[modules:]
        rows.append({"module": f"{len(rest)} other modules", "function": "", "other": True,
                     "survived": sum(len(f["mutants"]) for m in rest for f in m["functions"])})
    rows += [{"module": f"shard {u['shard']}", "function": f"{page.plural(u['survived'], 'survivor')} not listed",
              "survived": u["survived"], "other": True} for u in unlisted]
    return rows


def _model_view(model: str, b: dict, first: dict[tuple[str, str], str], cards: set[str]) -> dict:
    """The facts of one model: with their text forms, the ids of the classes (`cls-<class>`) and tasks (`task-<id>`),
    the links of its answers to their run cards, and its call paths."""
    _view(b)
    for block in b["tasks_view"]:
        block["anchor"] = _html_id("cls-", block["class"])
        for row in block["tasks"]:
            row["anchor"] = f"task-{row['id']}"
    _answer_links(b, first, cards)
    return {"model": model, "bench": b, "paths": flows.path_rows(b["calls"]),
            "task_ids": {row["id"] for blk in b["tasks_view"] for row in blk["tasks"]}}


def _task_blocks(views: list[dict]) -> list[dict]:
    """The task view of all models: one block per class and one row per task, in the order of their first appearance,
    each what the task view of its first model says. `by_model` of a block lists `(model, block)`, `by_cond` of a row
    lists per condition `(model, answer)`."""
    blocks: dict[str, dict] = {}
    rows: dict[str, dict] = {}
    for v in views:
        for blk in v["bench"]["tasks_view"]:
            block = blocks.setdefault(blk["class"], {**blk, "tasks": [], "by_model": []})
            block["by_model"].append((v["model"], blk))
            for row in blk["tasks"]:
                if row["id"] not in rows:
                    rows[row["id"]] = {**row, "by_cond": {}}
                    block["tasks"].append(rows[row["id"]])
                for cond, answer in row["answers"].items():
                    rows[row["id"]]["by_cond"].setdefault(cond, []).append((v["model"], answer))
    return list(blocks.values())


def _systems(views: list[dict]) -> list[dict]:
    """The published systems of all models: one row per task, what `literature` of its first model says, and `by_cond`
    per condition `(model, reported, text)`."""
    out: dict[str, dict] = {}
    for v in views:
        for s in v["bench"]["literature"]:
            row = out.setdefault(s["task"], {**s, "by_cond": {}})
            for cond, reported in s["reported"].items():
                if reported:
                    row["by_cond"].setdefault(cond, []).append((v["model"], reported, s["reported_text"][cond]))
    return list(out.values())


def _task_linker(task_ids: set[str]) -> Callable[[str], str | None]:
    """The link of a task named in the gallery or a solution path to its row; a task without a row has no link."""
    return lambda task: f"#task-{task}" if task in task_ids else None


def build_html(ctx: dict) -> str:
    return page.render("full.html.j2", **ctx)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="tsbench report full", description=(__doc__ or "").split("\n")[0])
    ap.add_argument("--runs", action="append", required=True, metavar="DIR",
                    help="a run set, or a folder holding run sets (repeatable)")
    ap.add_argument("--out", required=True, metavar="FILE")
    ap.add_argument("--title", default=None, help="report title (default: TS-MCP benchmark report)")
    ap.add_argument("--coverage", default=None, metavar="FILE",
                    help="coverage.py JSON of one measurement, pytest.log beside it: the tab Code checks")
    ap.add_argument("--mutation", nargs="+", default=[], metavar="DIR",
                    help="with --coverage: folders of <shard>/<shard>.json mutation results, merged")
    ap.add_argument("--no-gallery", action="store_true", help="leave out the run gallery (the largest part)")
    ap.add_argument("--no-figures", action="store_true", help="do not (re)draw the per-run figures of the gallery")
    ap.add_argument("--split", default="pilot", choices=SPLITS, help="the task split of the run sets (default pilot)")
    ap.add_argument("--i-have-preregistered", dest="preregistered", metavar="DOI", default=None,
                    help="the DOI of the preregistration; needed for the confirmatory split")
    ap.add_argument("--page-budget", type=float, default=None, metavar="MB",
                    help="the page size that images and per-run figures may fill; beyond it they are only linked "
                         "(default: no limit, everything is embedded and the page is one file)")
    ap.add_argument("--images", default=None, metavar="DIR",
                    help="folder of <run set>.index.csv: images a run left outside its folder are added from it")
    ap.add_argument("--redactions", default=None, metavar="FILE",
                    help="the log of a published copy (columns sha256_original, sha256_published): a transcript whose "
                         "machine paths it records as replaced counts as matching its manifest")
    ap.add_argument("--publication", action="store_true",
                    help="fail rather than write a page that links a local file (always so for the confirmatory split)")
    a = ap.parse_args(argv)
    run_sets = run_sets_in(a.runs)
    if not run_sets:
        ap.error("no run set found under --runs")
    if a.mutation and not a.coverage:
        ap.error("--mutation needs --coverage")
    if refused := split_refusal(run_sets, a.split, a.preregistered):
        print(f"tsbench report full: {refused}", file=sys.stderr)
        return 2
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        ctx = context(run_sets, out, a.title, a.coverage, [pathlib.Path(m) for m in a.mutation],
                      not a.no_gallery, not a.no_figures,
                      None if a.page_budget is None else int(a.page_budget * 1024 * 1024), a.split, a.preregistered,
                      pathlib.Path(a.images) if a.images else None, a.redactions)
    except (OSError, ValueError) as e:  # an unreadable or malformed coverage, mutation or redaction file
        print(f"tsbench report full: {e}", file=sys.stderr)
        return 2
    html = build_html(ctx)
    local = page.local_links(html)
    if local and (a.publication or a.split == "confirmatory"):
        print(f"tsbench report full: {page.plural(len(local), 'link')} to a local file, for example {local[0]}; a "
              "published page holds everything itself: leave out --page-budget", file=sys.stderr)
        return 2
    out.write_text(html, encoding="utf-8")
    print(f"wrote {out} ({len(html) / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
