"""The full report: one self-contained fact page about the run sets and the benchmark code.

    tsbench report full --runs DIR [--runs DIR2 ...] --out REPORT.html [--title T] [--no-gallery] [--no-figures]
                        [--coverage COVERAGE.json [--mutation DIR [DIR ...]]]

The page has six tabs (`TABS`): the models, the tasks, the published spectra, the checks of the benchmark code (with
`--coverage`, a coverage.py JSON with `pytest.log` beside it, and `--mutation`, one or more folders of
`<shard>/<shard>.json`), the gallery and code of the runs, and the method and platform. Each tab has a table of
contents of three levels (`context()["toc"]`). Where each figure sits, at which width and with which question as its
caption is data (`PLACEMENT`); the last section of a tab with figures lists them all. Every number comes from
report/facts.py and report/method.py; every figure is a static SVG of report/svg/. The page states no interpretation.
Every model of the run sets is analysed: the tabs Models, Tasks and Published spectra hold one view per model
(`context()["views"]`, ids prefixed by the model), the tab Models starts with a comparison of the models (`COMPARE`)
and a switch in the top bar picks the view. With one model there is one view without a prefix, no switch and no
comparison.
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

from tsbench.report import facts, gallery, method, page, taskview
from tsbench.report.base import pilot_hash
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

__all__ = ["ALL", "COMPARE", "MODEL_TABS", "PLACEMENT", "REPORT_VERSION", "TABS", "build_html", "context", "main",
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
# The tabs that hold one view per model, and the section that opens the tab Models when there are several models.
MODEL_TABS = ("models", "tasks", "spectra")
COMPARE = ("Models compared", [("model_shares", "full", "How often does each model answer correctly under A, B and C?"),
                               ("model_paired", "full", "How much does C change the share, model by model?")])
COMPARE_PAIRS = ("C − A", "C − B")  # the paired differences of the comparison table
# The tables a table-of-contents entry points to: per tab and section (id, title). The template gives each the id.
TABLES = {
    "models": {"Overview": [("tbl-shares", "Share correct"), ("tbl-paired", "Paired differences")],
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


def section_id(tab: str, title: str, pfx: str = "") -> str:
    """The html id of a section (h2) of a tab: `models-error-size`; in the view of a model `models-<pfx>error-size`."""
    return f"{tab}-{pfx}" + re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def _prefixes(names: list[str]) -> dict[str, str]:
    """The id prefix of each model's view: "" for a single model, else the slug of its name and "-", unique."""
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
    """Per figure key of the tabs Models, Tasks and Published spectra: the builder at a given width. `href` is the
    link of a task mark to its row in the view of the same model."""
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


def _compare_figures(rows: list[dict]) -> dict[str, Callable[[float], str]]:
    return {"model_shares": lambda w: models.model_shares(rows, width=w),
            "model_paired": lambda w: models.model_paired(rows, width=w)}


def _draw(builders: dict[str, Callable[[float], str]], pfx: str = "",
          placement: dict[str, list[tuple[str, list[tuple[str, str, str]]]]] = PLACEMENT) -> dict[str, dict]:
    """Every placed figure that has a builder, drawn at its width: key -> {tab, section, width, question, id, svg}.
    The id is `fig-<pfx><key>`. A builder that returns nothing (no data) leaves its figure out."""
    out = {}
    for tab, sections in placement.items():
        for section, figs in sections:
            for key, width, question in figs:
                if key not in builders:
                    continue
                svg = builders[key](WIDTH[width])
                if svg:
                    out[key] = {"tab": tab, "section": section, "width": width, "question": question,
                                "id": f"fig-{pfx}{key}", "svg": page.svg(svg)}
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


def _tab_toc(tab: str, figs: dict[str, dict], b: dict | None, c: dict | None, gal: dict | None,
             pfx: str = "") -> list[tuple[int, str, str]]:
    """The entries of the table of contents of a tab (or of one model's view of it) in page order: (level, id, title);
    level 2 a section, 3 a sub-section, 4 a figure, a table or a task."""
    entries: list[tuple[int, str, str]] = []
    for section, placed in PLACEMENT[tab]:
        if tab == "checks" and c is None and section != "Overview":
            continue
        entries.append((2, section_id(tab, section, pfx), section))
        if not (tab == "checks" and c is None):
            entries += [(4, _table_id(i, pfx), title) for i, title in TABLES.get(tab, {}).get(section, [])]
        entries += _sub_entries(tab, section, b, c, gal)
        entries += [(4, figs[k]["id"], q) for k, _, q in placed if k in figs]
    return entries


def _compare_toc(figs: dict[str, dict]) -> list[tuple[int, str, str]]:
    """The entries of the comparison of the models: its section, its table and its figures."""
    title, placed = COMPARE
    return [(2, section_id("models", title), title), (4, "tbl-models", "Models"),
            *[(4, figs[k]["id"], q) for k, _, q in placed if k in figs]]


def _table_id(ident: str, pfx: str) -> str:
    """`tbl-shares` in the view of a model: `tbl-<pfx>shares`."""
    return "tbl-" + pfx + ident.removeprefix("tbl-")


def _sub_entries(tab: str, section: str, b: dict | None, c: dict | None,
                 gal: dict | None) -> list[tuple[int, str, str]]:
    """The sub-sections and rows of a section that the table of contents lists."""
    out: list[tuple[int, str, str]] = []
    if (tab, section) == ("tasks", "Tasks") and b:
        for block in b["tasks_view"]:
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
            with_gallery: bool = True, make_figs: bool = True) -> dict:
    """The facts of the six tabs, their figures, the method tables, the table of contents and the gallery.
    `coverage` (coverage.py JSON) and `mutation` (folders of `<shard>/<shard>.json`) give the tab Code checks; without
    `coverage` the tab names the missing input. `views` holds per model, most evaluable runs first, what the tabs of
    `MODEL_TABS` show of it: {model, pfx, bench, figs, paths, task_ids, toc}."""
    out = pathlib.Path(out)
    reader = TranscriptCache()  # the facts and the gallery read each transcript through it
    benches = facts.benchmarks(run_sets, out, reader)
    multi = len(benches) > 1
    checks = None
    if coverage:
        checks = facts.checks(pathlib.Path(coverage), [pathlib.Path(m) for m in mutation], SRC,
                              TESTS if TESTS.is_dir() else None)
    plat = facts.platform(run_sets, keep=_keep(benches))
    meth = method.facts(run_sets, benches, checks, plat, version=REPORT_VERSION)
    if checks:
        _checks_view(checks)
    gal = gallery.context(run_sets, out.parent, make_figs, reader)[0] if with_gallery else None
    first = _gallery_anchors(gal)
    cards = {card["anchor"] for t in gal["run_tasks"] for card in t["cards"]} if gal else set()
    pfx = _prefixes(list(benches))
    views = [_model_view(m, b, pfx[m], first.get(m, {}), cards, checks, gal) for m, b in benches.items()]
    compare = _compare_view(facts.models_overview(benches)) if multi else None
    figs = _draw(_platform_figures(plat) | (_checks_figures(checks) if checks else {}))
    toc = {tab: _tab_toc(tab, figs, None, checks, gal) for tab, _ in TABS if tab not in MODEL_TABS}
    if compare is not None:
        figs |= _draw(_compare_figures(compare), placement={"models": [COMPARE]})
        toc |= {"models": _compare_toc(figs), "tasks": [], "spectra": []}
    else:
        toc |= views[0]["toc"]
    toc = {tab: toc[tab] for tab, _ in TABS}
    header = _page_header([v["bench"]["header"] for v in views])
    task_ids = set().union(*(v["task_ids"] for v in views))
    pilot = pilot_hash()
    survivors = _survivors(checks) if checks else []
    unlisted = checks["mutation"]["unlisted"] if checks else []
    return {"title": title or "TS-MCP benchmark report", "header": header, "bench": views[0]["bench"],
            "views": views, "multi": multi, "compare": compare, "compare_conds": header["conds"],
            "checks": checks, "platform": plat, "method": meth, "gal": gal, "figs": figs,
            "solution_paths": [{**sp, "hid": v["pfx"] + sp["id"], "model": v["model"]}
                               for v in views for sp in v["bench"]["solution_paths"]],
            "survivors": survivors, "survivor_rows": survivor_rows(survivors, unlisted=unlisted),
            "run_classes": _run_classes(gal) if gal else [], "code_conds": _code_conds(gal) if gal else [],
            "task_ids": task_ids, "task_href": _task_linker(pfx, task_ids),
            "notes": _notes(benches, checks, plat), "toc": toc,
            "tabs": TABS, "model_tabs": MODEL_TABS, "placement": PLACEMENT, "ALL": ALL, "COMPARE": COMPARE,
            "compare_pairs": COMPARE_PAIRS, "section_id": section_id,
            "ident": {"version": REPORT_VERSION, "tasks": (pilot or "")[:7],
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


def _model_view(model: str, b: dict, pfx: str, first: dict[tuple[str, str], str], cards: set[str], checks: dict | None,
                gal: dict | None) -> dict:
    """What the tabs of `MODEL_TABS` show of one model: its facts with the ids of its view (task rows `task-<pfx><id>`,
    classes `cls-<pfx><class>`), its figures (`fig-<pfx><key>`, task marks linked into the same view), its call paths
    and its table of contents."""
    _view(b)
    for block in b["tasks_view"]:
        block["anchor"] = _html_id("cls-" + pfx, block["class"])
        for row in block["tasks"]:
            row["anchor"] = f"task-{pfx}{row['id']}"
    _answer_links(b, first, cards)
    figs = _draw(_models_figures(b, lambda task: f"#task-{pfx}{task}"), pfx)
    return {"model": model, "pfx": pfx, "bench": b, "figs": figs, "paths": flows.path_rows(b["calls"]),
            "task_ids": {row["id"] for blk in b["tasks_view"] for row in blk["tasks"]},
            "toc": {tab: _tab_toc(tab, figs, b, checks, gal, pfx) for tab in MODEL_TABS}}


def _task_linker(pfx: dict[str, str], task_ids: set[str]) -> Callable[..., str | None]:
    """The link of a task named outside the views (gallery, solution paths) to its row in the view of `model`; a
    model without a view links to the first view; a task without a row has no link."""
    default = next(iter(pfx.values()), "")

    def href(task: str, model: str | None = None) -> str | None:
        if task not in task_ids:
            return None
        return f"#task-{pfx.get(model, default) if model is not None else default}{task}"

    return href


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
    a = ap.parse_args(argv)
    run_sets = run_sets_in(a.runs)
    if not run_sets:
        ap.error("no run set found under --runs")
    if a.mutation and not a.coverage:
        ap.error("--mutation needs --coverage")
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        ctx = context(run_sets, out, a.title, a.coverage, [pathlib.Path(m) for m in a.mutation],
                      not a.no_gallery, not a.no_figures)
    except (OSError, ValueError) as e:  # an unreadable or malformed coverage or mutation file
        print(f"tsbench report full: {e}", file=sys.stderr)
        return 2
    html = build_html(ctx)
    out.write_text(html, encoding="utf-8")
    print(f"wrote {out} ({len(html) / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
