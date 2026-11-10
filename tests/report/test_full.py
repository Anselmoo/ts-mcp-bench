"""The full report (src/tsbench/report/full.py): a tabbed fact page. Six tabs, a table of contents of three
levels per tab, a light/dark switch, every task identifiable, every figure at one of two widths with one question as
caption, the method tables and a provenance row for every figure (the report contract)."""
from __future__ import annotations

import base64
import copy
import hashlib
import html.parser
import json
import pathlib
import re
import shutil
from collections.abc import Iterator
from typing import Any

import pytest

from tsbench.core import resource
from tsbench.report import base, full, page
from tsbench.stats.analysis import mcnemar_exact
from tsbench.tasks import load

PILOT = [t["id"] for t in load("pilot") if t.get("split") == "pilot"]

TABS = [("models", "Models"), ("tasks", "Tasks"), ("spectra", "Published spectra"), ("checks", "Code checks"),
        ("gallery", "Gallery and code"), ("platform", "Method and platform")]
ALL = "All figures"
# Per tab its h2 sections, per section its figures (key, width, question); the figures under
# "All figures" are the overflow figures of the tab.
PLACEMENT = {
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
WIDTH = {"full": "960", "half": "464"}
METHOD_SECTIONS = ["Identity", "Protocol", "Statistics", "Provenance", "Exclusions and limits"]


def _figures(tab: str) -> list[tuple[str, str, str, str]]:
    """(section, key, width, question) of every figure of a tab, overflow figures included."""
    return [(s, k, w, q) for s, figs in PLACEMENT[tab] for k, w, q in figs]


def _quality(root: pathlib.Path) -> tuple[pathlib.Path, list[pathlib.Path]]:
    """A coverage.json with pytest.log beside it and two mutation folders: shard `core` in the first, `cli` in the
    second; package `report` has coverage but no mutation result."""
    cov = root / "q" / "coverage" / "coverage.json"
    cov.parent.mkdir(parents=True)
    files = {"src/tsbench/core/a.py": (9, 10), "src/tsbench/report/b.py": (3, 4), "src/tsbench/cli.py": (5, 5)}
    cov.write_text(json.dumps({
        "meta": {"format": 3, "timestamp": "2026-10-31T16:47:20"},
        "files": {k: {"summary": {"covered_lines": c, "num_statements": n, "percent_covered": 100 * c / n},
                      "functions": {}} for k, (c, n) in files.items()},
        "totals": {"covered_lines": 17, "num_statements": 19, "percent_covered": 100 * 17 / 19}}), encoding="utf-8")
    (cov.parent / "pytest.log").write_text("1 failed, 41 passed, 2 skipped in 12.50s\n", encoding="utf-8")
    m1, m2 = root / "q" / "mutation", root / "extra"
    # shard `cli` counts 2 survivors and lists 1 (`s` counted, one listed)
    for folder, name, module, k, s in ((m1, "core", "tsbench.core.a", 9, 1), (m2, "cli", "tsbench.cli", 3, 2)):
        (folder / name).mkdir(parents=True)
        (folder / name / f"{name}.json").write_text(json.dumps({
            "name": name, "total": k + s, "counts": {"killed": k, "survived": s, "timeout": 0},
            "per_module": {module: {"killed": k, "survived": s, "timeout": 0}},
            "survivors": [{"mutant": f"{module}.x_run__mutmut_1", "module": module,
                           "diff": ("--- a/m.py\n+++ b/m.py\n@@ -1,3 +1,3 @@\n def run():\n"
                                    "-    return 1\n+    return 2\n     pass\n")}]}), encoding="utf-8")
    return cov, [m1, m2]


ONE = ("claude-sonnet-5-5",)
TWO = ("claude-sonnet-5-5", "claude-haiku-5-5")


def _copy_models(src: pathlib.Path, dst: pathlib.Path, models: tuple[str, ...]) -> pathlib.Path:
    """A copy of the run sets under `src` (the demo run set) whose folder names one of `models`
    (`<group>/<model>...`)."""
    for rs in sorted(src.glob("*/*")):
        if rs.is_dir() and rs.name.startswith(models):
            shutil.copytree(rs, dst / rs.parent.name / rs.name)
    return dst


def _build(src: pathlib.Path, root: pathlib.Path, models: tuple[str, ...]) -> tuple[dict, str]:
    runs = _copy_models(src, root / "runs", models)
    cov, muts = _quality(root)
    out = root / "pages" / "report.html"
    ctx = full.context(full.run_sets_in([runs]), out, coverage=cov, mutation=muts, make_figs=False)
    return ctx, full.build_html(ctx)


@pytest.fixture(scope="module")
def built(tmp_path_factory, demo_runs_root):
    """The report of the runs of one model of the demo run set with the gallery (no per-run figures) and both quality
    inputs: the page of one model."""
    return _build(demo_runs_root, tmp_path_factory.mktemp("full"), ONE)


@pytest.fixture(scope="module")
def built2(tmp_path_factory, demo_runs_root):
    """The same report over the runs of two models: one layout with all models together."""
    return _build(demo_runs_root, tmp_path_factory.mktemp("full2"), TWO)


DOI = "10.5281/zenodo.23889782"
HYP_MODELS = ("claude-haiku-5-5", "claude-sonnet-5-5")
HYP = {"k_layers": {"primary": 3, "h1": 3, "h4": 0},
       "primary": [{"name": f"H2_{m}", "n": 17, "p": p, "mean_diff": d, "ci": [d - 0.1, d + 0.1], "p_holm": q,
                    "family": "primary"} for m, p, d, q in ((HYP_MODELS[0], 0.5, -0.01, 0.9),
                                                            (HYP_MODELS[1], 4e-6, 0.25, 1.8e-5))]
       + [{"name": "H3", "n": 17, "p": 0.1, "mean_diff": -0.1, "ci": [-0.2, 0.0], "p_holm": 0.2, "family": "primary"}],
       "secondary": [{"name": f"H1_{HYP_MODELS[0]}", "n": 17, "p": 1e-10, "mean_diff": 0.68, "ci": [0.58, 0.78],
                      "family": "secondary"},
                     {"name": f"H2_{HYP_MODELS[0]}_mcnemar", "n": 17, "p": 0.39, "b": 8, "c": 4,
                      "family": "secondary"}],
       "efficiency": [{"name": f"EFF_total_tokens_Cvs{base}_{HYP_MODELS[0]}", "metric": "total_tokens",
                       "model": HYP_MODELS[0], "base": base, "other": "C", "correct_only": False, "n": 17,
                       "median_base": 100.0, "median_other": 50.0, "median_ratio": ratio,
                       "ratio_ci": [ratio / 2, 2 * ratio], "p": 0.01, "family": "descriptive"}
                      for base, ratio in (("A", 2.5), ("B", 0.25))]}


def _confirmatory_tasks(mp: pytest.MonkeyPatch) -> None:
    """Let the pilot records of the demo run set stand in for the confirmatory split (the class literature_new, which
    the confirmatory split does not have, left out), so that a report of the confirmatory split has runs to read."""
    import tsbench.tasks as T
    from tsbench.report import gallery
    real = T.load

    def load(split, *a, **k):
        if split == "confirmatory":
            return [{**t, "split": "confirmatory"} for t in real("pilot", *a, **k) if t["class"] != "literature_new"]
        return real(split, *a, **k)

    mp.setattr(T, "load", load)
    mp.setattr(gallery, "_TASKS", {})


@pytest.fixture(scope="module")
def built_conf(tmp_path_factory, demo_runs_root):
    """The report of the demo runs of one model read as the confirmatory split, with a hypotheses.json in the run
    set: the page of a confirmatory run set."""
    root = tmp_path_factory.mktemp("full-conf")
    with pytest.MonkeyPatch.context() as mp:
        _confirmatory_tasks(mp)
        runs = _copy_models(demo_runs_root, root / "runs", ONE)
        for f in sorted(runs.rglob("P-literature_new-*"), reverse=True):  # no run of a task outside the split
            shutil.rmtree(f) if f.is_dir() else f.unlink()
        sets = full.run_sets_in([runs])
        for rs in sets:  # the manifests record the split and the DOI, as those of a confirmatory run do
            path = rs.path / "MANIFEST.json"
            m = json.loads(path.read_text(encoding="utf-8"))
            m["split"], m["args"] = "confirmatory", {**m["args"], "split": "confirmatory", "preregistered": DOI}
            path.write_text(json.dumps(m), encoding="utf-8")
        (sets[0].path / "hypotheses.json").write_text(json.dumps(HYP), encoding="utf-8")
        ctx = full.context(sets, root / "pages" / "report.html", make_figs=False, split="confirmatory", doi=DOI)
        return ctx, full.build_html(ctx)


# ---------------------------------------------------------------- a small DOM of the page


class Node:
    """An element with its attributes and children (elements and text, in document order)."""

    def __init__(self, tag: str, attrs: dict[str, str], parent: Node | None):
        self.tag, self.attrs, self.parent = tag, attrs, parent
        self.kids: list[Node | str] = []

    @property
    def cls(self) -> list[str]:
        return str(self.attrs.get("class") or "").split()

    def iter(self, skip=lambda n: False) -> Iterator[Node]:
        """This element and every element below it in document order; `skip(n)` leaves out the subtree of n."""
        if skip(self):
            return
        yield self
        for k in self.kids:
            if isinstance(k, Node):
                yield from k.iter(skip)

    def text(self) -> str:
        parts = []
        for k in self.kids:
            if isinstance(k, str):
                parts.append(k)
            elif k.tag not in ("script", "style", "title"):
                parts.append(k.text())
        return " ".join(" ".join(parts).split())

    def find(self, tag: str, cls: str | None = None, **attrs) -> list[Node]:
        return [n for n in self.iter() if n.tag == tag and (cls is None or cls in n.cls)
                and all(n.attrs.get(a.replace("_", "-")) == v for a, v in attrs.items())]

    def inside(self, tag: str) -> bool:
        p = self.parent
        while p is not None:
            if p.tag == tag:
                return True
            p = p.parent
        return False


class _Builder(html.parser.HTMLParser):
    VOID = {"meta", "br", "img", "input", "hr", "link", "source", "wbr", "col", "area", "base", "embed", "track"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#root", {}, None)
        self.cur = self.root

    def handle_starttag(self, tag, attrs):
        n = Node(tag, {k: v or "" for k, v in attrs}, self.cur)
        self.cur.kids.append(n)
        if tag not in self.VOID:
            self.cur = n

    def handle_startendtag(self, tag, attrs):
        self.cur.kids.append(Node(tag, {k: v or "" for k, v in attrs}, self.cur))

    def handle_endtag(self, tag):
        n = self.cur
        while n is not None and n.tag != tag:
            n = n.parent
        if n is not None and n.parent is not None:
            self.cur = n.parent

    def handle_data(self, data):
        self.cur.kids.append(data)


def _dom(markup: str) -> Node:
    b = _Builder()
    b.feed(markup)
    return b.root


def _tab(root: Node, tab: str) -> Node:
    found = [n for n in root.iter() if n.tag == "section" and "tab" in n.cls and n.attrs.get("id") == f"tab-{tab}"]
    assert len(found) == 1, tab
    return found[0]


def _toc_nav(n: Node) -> bool:
    return n.tag == "nav" and "toc" in n.cls


def _h2_title(n: Node) -> str:
    return n.text()


def _regions(tab: Node) -> dict[str, list[Node]]:
    """Per h2 of a tab (outside its table of contents) the elements that follow it up to the next h2."""
    out: dict[str, list[Node]] = {}
    cur = None
    for n in tab.iter(skip=_toc_nav):
        if n.tag == "h2":
            cur = _h2_title(n)
            out[cur] = []
        elif cur is not None:
            out[cur].append(n)
    return out


def _fig_nodes(nodes: list[Node]) -> list[Node]:
    return [n for n in nodes if n.tag == "figure" and "fg" in n.cls]


def _hrefs(n: Node) -> list[str]:
    return [x.attrs.get("href") or x.attrs.get("xlink:href") or "" for x in n.iter() if x.tag == "a"]


def _own(markup: str) -> str:
    """The page without its scripts and styles."""
    markup = re.sub(r"<script\b[^>]*>.*?</script>", "", markup, flags=re.S)
    return re.sub(r"<style\b[^>]*>.*?</style>", "", markup, flags=re.S)


def _ids(root: Node) -> list[str]:
    return [n.attrs["id"] for n in root.iter() if "id" in n.attrs]


# ---------------------------------------------------------------- the placement is data in full.py


def test_tabs_and_placement_are_data_of_full_py():
    assert [tuple(t) for t in full.TABS] == TABS
    got = {tab: [(s, [tuple(f) for f in figs]) for s, figs in sections] for tab, sections in full.PLACEMENT.items()}
    assert got == PLACEMENT
    assert full.REPORT_VERSION == "4"


def test_every_question_is_one_line_ending_in_a_question_mark_and_no_question_repeats():
    questions = [q for tab in PLACEMENT for _, _, _, q in _figures(tab)]
    assert all(q.endswith("?") and len(q) < 110 and "\n" not in q for q in questions)
    assert len(set(questions)) == len(questions)
    keys = [k for tab in PLACEMENT for _, k, _, _ in _figures(tab)]
    assert len(set(keys)) == len(keys)
    for tab, sections in PLACEMENT.items():
        for s, figs in sections:
            assert s == ALL or len(figs) <= 3, (tab, s)
        if any(figs for _, figs in sections):
            assert sections[-1][0] == ALL, tab


# ---------------------------------------------------------------- frame: tabs, table of contents, theme


def test_top_bar_has_the_six_tabs_in_order_and_a_theme_switch(built):
    _, markup = built
    root = _dom(_own(markup))
    bars = root.find("nav", "tabs")
    assert len(bars) == 1
    assert [h for h in _hrefs(bars[0])] == [f"#{t}" for t, _ in TABS]
    assert [a.text() for a in bars[0].iter() if a.tag == "a"] == [label for _, label in TABS]
    assert len(root.find("button", id="theme-switch")) == 1


def test_the_dark_tokens_of_the_report_are_those_of_the_frame(built):
    """One list of dark tokens: base.html.j2 writes it, the report takes it for both selectors of its switch."""
    _, markup = built
    frame = page.render("base.html.j2", title="t", dark=True)
    found = re.search(r"prefers-color-scheme:dark\)\{:root\{(.*?)\}\}", frame, flags=re.S)
    assert found
    tokens = found.group(1)
    assert tokens.startswith("--paper:") and tokens.endswith("color-scheme:dark")
    styles = _styles(markup)
    assert styles.count(tokens) == 2
    assert re.search(r":root:not\(\[data-theme=light\]\)\{" + re.escape(tokens) + r"\}", styles)
    assert re.search(r":root\[data-theme=dark\]\{" + re.escape(tokens) + r"\}", styles)
    assert "--plate" not in styles


def test_each_tab_is_one_section_in_order(built):
    _, markup = built
    root = _dom(_own(markup))
    tabs = [n.attrs.get("id") for n in root.iter() if n.tag == "section" and "tab" in n.cls]
    assert tabs == [f"tab-{t}" for t, _ in TABS]


def test_the_theme_has_light_and_dark_tokens_and_a_remembered_switch(built):
    _, markup = built
    styles = " ".join(re.findall(r"<style\b[^>]*>(.*?)</style>", markup, flags=re.S))
    scripts = " ".join(re.findall(r"<script\b[^>]*>(.*?)</script>", markup, flags=re.S))
    assert re.search(r"prefers-color-scheme:\s*dark\)\s*\{\s*:root:not\(\[data-theme=[\"']?light[\"']?\]\)", styles)
    assert re.search(r":root\[data-theme=[\"']?dark[\"']?\]\s*\{", styles)
    assert "color-scheme" in styles
    assert "localStorage" in scripts and "data-theme" in scripts and re.search(r"\btry\s*\{", scripts)
    assert "IntersectionObserver" in scripts  # the current section is marked in the table of contents


def test_the_page_has_no_part_links_and_no_fold_out_topics(built):
    _, markup = built
    own = _own(markup)
    assert 'class="part"' not in own and 'nav class="top"' not in own
    assert not re.search(r'href="#p[123]"', own) and not re.search(r'<details class="f"', own)


def test_every_tab_has_a_table_of_contents_of_three_levels_whose_ids_exist(built):
    ctx, markup = built
    root = _dom(_own(markup))
    toc = ctx["toc"]
    assert list(toc) == [t for t, _ in TABS]
    for tab, entries in toc.items():
        node = _tab(root, tab)
        ids = set(_ids(node))
        assert {lv for lv, _, _ in entries} <= {2, 3, 4}
        assert [title for lv, _, title in entries if lv == 2] == [s for s, _ in PLACEMENT[tab]], tab
        navs = [n for n in node.iter() if _toc_nav(n)]
        assert len(navs) == 1, tab
        links = set(_hrefs(navs[0]))
        for _, i, _ in entries:
            assert i in ids, (tab, i)
            assert f"#{i}" in links, (tab, i)
        figure_ids = {f.attrs.get("id") for f in _fig_nodes(list(node.iter(skip=_toc_nav)))}
        assert figure_ids <= {i for lv, i, _ in entries if lv == 4}, tab


def test_the_tasks_table_of_contents_holds_every_task_at_level_four(built):
    ctx, _ = built
    level4 = {(i, title) for lv, i, title in ctx["toc"]["tasks"] if lv == 4}
    assert {(f"task-{t}", t) for t in PILOT} <= level4


# ---------------------------------------------------------------- figures: widths, captions, sections


def test_every_figure_is_drawn_at_one_of_the_two_widths(built):
    _, markup = built
    root = _dom(_own(markup))
    figs = _fig_nodes(list(root.iter()))
    assert figs
    for f in figs:
        width = [w for w in ("full", "half") if w in f.cls]
        assert len(width) == 1, f.attrs
        svgs = [n for n in f.iter() if n.tag == "svg" and "fig" in n.cls]
        assert svgs, f.attrs
        assert all(s.attrs.get("width") == WIDTH[width[0]] for s in svgs), f.attrs


def test_each_placed_figure_sits_in_its_tab_and_section_with_its_question(built):
    _, markup = built
    root = _dom(_own(markup))
    for tab, _ in TABS:
        regions = _regions(_tab(root, tab))
        assert list(regions) == [s for s, _ in PLACEMENT[tab]], tab
        for section, key, width, question in _figures(tab):
            here = [f for f in _fig_nodes(regions[section]) if f.attrs.get("data-key") == key]
            assert len(here) == 1, (tab, key)
            f = here[0]
            assert width in f.cls and f.attrs.get("id"), (tab, key)
            caps = [n for n in f.iter() if n.tag == "figcaption"]
            assert len(caps) == 1 and caps[0].text() == question, (tab, key)
            assert not [n for n in caps[0].iter() if n.tag == "br"]


def test_no_section_shows_more_than_three_figures_outside_all_figures(built):
    _, markup = built
    root = _dom(_own(markup))
    for tab, _ in TABS:
        for section, nodes in _regions(_tab(root, tab)).items():
            if section != ALL:
                assert len(_fig_nodes(nodes)) <= 3, (tab, section)
        for f in _fig_nodes(list(_tab(root, tab).iter())):
            caps = [n for n in f.iter() if n.tag == "figcaption"]
            assert len(caps) == 1 and caps[0].text().endswith("?") and len(caps[0].text()) < 110


def test_all_figures_lists_every_question_of_the_tab_as_a_link_to_its_figure(built):
    _, markup = built
    root = _dom(_own(markup))
    for tab, _ in TABS:
        if not _figures(tab):
            continue
        node = _tab(root, tab)
        by_id = {f.attrs.get("id"): f for f in _fig_nodes(list(node.iter(skip=_toc_nav)))}
        links = [(a.attrs.get("href", ""), a.text()) for a in _regions(node)[ALL] if a.tag == "a"
                 and a.text().endswith("?")]
        assert sorted(text for _, text in links) == sorted(q for _, _, _, q in _figures(tab)), tab
        for href, text in links:
            f = by_id.get(href.removeprefix("#"))
            assert f is not None, (tab, href)
            assert [n for n in f.iter() if n.tag == "figcaption"][0].text() == text


# ---------------------------------------------------------------- tasks and links


def test_every_pilot_task_has_a_row_with_its_id_and_its_prompt(built):
    _, markup = built
    node = _tab(_dom(_own(markup)), "tasks")
    rows = {n.attrs["id"]: n for n in node.iter() if n.tag == "tr" and n.attrs.get("id", "").startswith("task-")}
    assert set(rows) == {f"task-{t}" for t in PILOT}
    for t in PILOT:
        row = rows[f"task-{t}"]
        assert t in row.text()
        assert [n for n in row.iter() if n.tag == "details"], t  # the prompt, folded


@pytest.mark.parametrize("page", ["built", "built2", "built_conf"])
def test_every_internal_link_of_the_page_resolves(page, request):
    _, markup = request.getfixturevalue(page)
    root = _dom(_own(markup))
    ids = set(_ids(root))
    tabs = {t for t, _ in TABS}
    bad = []
    for href in _hrefs(root):
        if not href.startswith("#"):
            continue
        target = href[1:]
        tab, _, anchor = target.partition("/")
        ok = (tab in tabs and (not anchor or anchor in ids)) if anchor or tab in tabs else target in ids
        if not ok:
            bad.append(href)
    assert not bad, bad[:5]


def test_figures_link_their_task_marks_to_the_task_rows(built):
    _, markup = built
    root = _dom(_own(markup))
    ledger = [f for f in _fig_nodes(list(_tab(root, "tasks").iter())) if f.attrs.get("data-key") == "ledger"]
    assert ledger and any(h.startswith("#task-") for h in _hrefs(ledger[0]))
    swarm = [f for f in _fig_nodes(list(_tab(root, "models").iter())) if f.attrs.get("data-key") == "swarm"]
    assert swarm and any(h.startswith("#task-") for h in _hrefs(swarm[0]))


def test_answers_link_to_a_run_card_of_their_condition_and_task(built):
    ctx, markup = built
    root = _dom(_own(markup))
    gallery_ids = set(_ids(_tab(root, "gallery")))
    cards = {(c["head"]["cond"], c["head"]["task"]) for t in ctx["gal"]["run_tasks"] for c in t["cards"]
             if c["head"]["model"] == ctx["header"]["model"]}
    linked = 0
    for block in ctx["bench"]["tasks_view"]:
        for row in block["tasks"]:
            for cond, a in row["answers"].items():
                if (cond, row["id"]) in cards:
                    assert a["href"] and a["href"][1:] in gallery_ids, (cond, row["id"])
                    linked += 1
    assert linked
    rows = {n.attrs["id"]: n for n in _tab(root, "tasks").iter() if n.tag == "tr" and "id" in n.attrs}
    hrefs = [h for r in rows.values() for h in _hrefs(r)]
    assert any(h[1:] in gallery_ids for h in hrefs)


def test_an_answer_links_to_the_card_of_the_run_it_shows():
    from test_facts import TASKS as FACT_TASKS  # the made-up runs of the facts tests
    from test_facts import _data, _row

    from tsbench.report import facts

    t = FACT_TASKS["P-closed_form-01"]
    data = _data()
    data["rows"] = [r for r in data["rows"] if not (r["task_id"] == t["id"] and r["_cond"] == "A")]
    data["rows"] += [_row("m1", "A", t, ok, k=k) for k, ok in ((1, False), (2, True), (3, True))]
    bench = facts._benchmark(data, {}, None)
    heads = [{"model": "m1", "cond": r["_cond"], "effort": "medium", "task": r["task_id"], "k": str(r["k_index"])}
             for r in data["rows"]]
    gal: dict[str, Any] = {"run_tasks": [{"cards": [{"head": h} for h in heads]}]}
    first = full._gallery_anchors(gal)["m1"]
    cards = {str(c["anchor"]): dict(c["head"]) for tk in gal["run_tasks"] for c in tk["cards"]}
    full._answer_links(bench, first, set(cards))
    answer = next(r for b in bench["tasks_view"] for r in b["tasks"] if r["id"] == t["id"])["answers"]["A"]
    assert answer["ok"] is True
    target = cards[answer["href"][1:]]
    # the first card of (A, task) is run 1, a wrong run left out of the verdict: the link names run 2
    assert (target["cond"], target["task"], target["k"]) == ("A", t["id"], "2")
    assert first[("A", t["id"])] != answer["href"][1:]


def test_the_classes_table_counts_per_condition_only_the_tasks_with_an_evaluable_run(built):
    ctx, markup = built
    root = _dom(_own(markup))
    table = [n for n in root.iter() if n.tag == "table" and n.attrs.get("id") == "tbl-classes"][0]
    rows = [r for r in table.iter() if r.tag == "tr"][1:]
    blocks = ctx["bench"]["tasks_view"]
    assert len(rows) == len(blocks)
    short = 0
    for row, blk in zip(rows, blocks, strict=True):
        cells = [c.text() for c in row.iter() if c.tag == "td"][5:]
        n_by = [blk["n_by"].get(c, blk["n"]) for c in ctx["bench"]["header"]["conds"]]
        want = ["no run" if n == 0 else f"{blk['k'].get(c, 0)} of {n}"
                for c, n in zip(ctx["bench"]["header"]["conds"], n_by, strict=True)]
        assert cells == want, blk["class"]
        short += sum(blk["n_by"][c] < blk["n"] for c in blk["n_by"])
    assert short, "the demo run set has a task without an evaluable run under a condition"
    # the same n as the class marks of the Method tab
    marks = {c["class"]: c["n_by"] for c in ctx["bench"]["classes"]}
    assert all(marks[b["class"]] == b["n_by"] for b in blocks)


def test_the_classes_table_says_no_run_for_a_condition_without_a_run_in_the_class(built):
    """A condition that has runs in other classes but none in this one is `no run`, not `0 of 0`."""
    ctx = copy.deepcopy(built[0])
    blk = ctx["views"][0]["bench"]["tasks_view"][0]
    blk["k"]["B"], blk["n_by"]["B"] = 0, 0
    root = _dom(_own(full.build_html(ctx)))
    table = [n for n in root.iter() if n.tag == "table" and n.attrs.get("id") == "tbl-classes"][0]
    row = [r for r in table.iter() if r.tag == "tr"][1]
    cells = [c.text() for c in row.iter() if c.tag == "td"][5:]
    assert "no run" in cells and not [c for c in cells if c.endswith(" of 0")]


def test_the_cost_of_a_gateway_model_is_no_real_cost(built):
    import copy

    ctx, _ = built
    b = copy.deepcopy(ctx["bench"])
    assert b["header"]["cost_is_estimate"] is False and b["cost"]["table"][0]["total"] != full.NO_REAL_COST
    b["header"]["cost_is_estimate"] = True
    assert all(r["total"] == r["correct_cost"] == full.NO_REAL_COST for r in full._cost_rows(b))
    assert full._models_figures(b)["cost_map"](900) == ""
    full._view(b)
    assert all(m["cost_usd"] == "–" for m in b["cost"]["medians_text"])
    assert all(r["total"] == full.NO_REAL_COST for r in b["cost"]["table"])


def test_the_schedule_of_a_gateway_model_shows_no_cost_and_the_class_dots_no_zero_share(tmp_path, demo_runs_root):
    """Claude Code's cost of a gateway model is a list-price estimate: the schedule draws none of it. A condition
    with no evaluable run in a class is no marker, not a 0 % one."""
    ctx, _ = _build(demo_runs_root, tmp_path, ("gemma-4-31b-it",))
    assert ctx["bench"]["header"]["cost_is_estimate"] is True
    sched = ctx["figs"]["schedule"]["svg"]
    assert "<rect" in sched and "$" not in sched and "cumulative cost" not in sched and "USD" not in sched
    dots_svg = full._models_figures(ctx["bench"])["classes"](900)
    assert "/0 (0 %)" not in dots_svg
    short = [(x["class"], c) for x in ctx["bench"]["tasks_view"] for c, n in x["n_by"].items() if n == 0]
    assert short, "the demo run set has a class without an evaluable run under a condition"
    assert all(f"{cls} · {c}:" not in dots_svg for cls, c in short)


def test_a_condition_without_an_evaluable_run_is_in_no_figure_as_zero(built):
    """The header lists the conditions with an evaluable run; the upset figure draws those only (no `B: 0 tasks`)."""
    b = copy.deepcopy(built[0]["bench"])
    b["header"]["conds"] = ["A", "C"]
    for x in b["tasks_view"]:
        x["k"].pop("B", None)
        x["n_by"].pop("B", None)
    svg = full._models_figures(b)["upset"](464)
    assert "<svg" in svg and "B: " not in svg and "B only" not in svg and "A, B" not in svg and "B, C" not in svg
    assert "A: " in svg and "C: " in svg
    assert "B:" not in full._models_figures(b)["classes"](900)


def _rules_outside_screen(css: str, needle: str) -> list[str]:
    """The text of every rule whose selector holds `needle` and that sits outside an `@media screen` block."""
    out, depth, screen_depth, start = [], 0, None, 0
    for i, ch in enumerate(css):
        if ch == "{":
            head = css[start:i].strip()
            if head.startswith("@media") and re.match(r"@media\s+screen\b", head) and screen_depth is None:
                screen_depth = depth
            elif needle in head and screen_depth is None:
                out.append(head)
            depth, start = depth + 1, i + 1
        elif ch == "}":
            depth -= 1
            if screen_depth is not None and depth == screen_depth:
                screen_depth = None
            start = i + 1
        elif ch == ";":
            start = i + 1
    return out


def test_the_dark_theme_switch_does_not_reach_the_printed_page(built):
    _, markup = built
    styles = " ".join(re.findall(r"<style\b[^>]*>(.*?)</style>", markup, flags=re.S))
    assert "data-theme=dark" in styles
    assert _rules_outside_screen(styles, "data-theme=dark") == []
    bites = _rules_outside_screen("a{x:y}@media print{:root[data-theme=dark]{z:1}}", "data-theme=dark")
    assert bites  # the helper finds a dark rule outside @media screen


def test_the_paired_table_has_the_full_row_not_the_464_px_column(built2):
    ctx, markup = built2
    root = _dom(_own(markup))
    tables = [n for n in root.find("table") if n.attrs.get("id") == "tbl-paired"]
    assert len(tables) == 1
    rows = [n for n in tables[0].iter() if n.tag == "tr" and n.parent is not None and n.parent.tag == "tbody"]
    assert len(rows) == sum(len(v["bench"]["paired"]) for v in ctx["views"])
    for t in tables:
        node, held = t.parent, []
        while node is not None:
            held += [c for c in node.cls if c in ("col", "row2")]
            node = node.parent
        assert held == [], t.attrs["id"]


def test_a_correct_or_wrong_mark_carries_its_word_for_a_screen_reader(built):
    _, markup = built
    root = _dom(_own(markup))
    scopes = [t for t in root.find("table") if t.attrs.get("id", "").endswith("systems")]
    scopes += root.find("details", cls="sp")
    marks = [(svg, svg.parent) for sc in scopes for svg in sc.find("svg") if "ic" in svg.cls]
    assert len(marks) > 10
    for svg, parent in marks:
        assert parent is not None and svg.attrs.get("aria-hidden") == "true"
        after = parent.kids[parent.kids.index(svg) + 1]
        assert isinstance(after, Node) and after.tag == "span" and "sr" in after.cls
        assert after.text() == ("correct" if "t-ok" in svg.cls else "wrong")
    assert re.search(r"\.sr\{[^}]*clip", " ".join(re.findall(r"<style\b[^>]*>(.*?)</style>", markup, flags=re.S)))


def test_the_theme_button_is_named_by_its_visible_text(built):
    _, markup = built
    button = _dom(_own(markup)).find("button", id="theme-switch")[0]
    assert "aria-label" not in button.attrs and "aria-labelledby" not in button.attrs
    assert button.text().startswith("Theme:")  # the accessible name is this text, which the script updates


def test_the_theme_starts_at_the_system_setting(built):
    _, markup = built
    assert not re.search(r"<html[^>]*data-theme", markup)
    assert re.search(r'<button[^>]*id="theme-switch"[^>]*>[^<]*system', markup)


# ---------------------------------------------------------------- tables: header, spectra, checks, method, notes


def test_header_chips_name_model_effort_k_split_dates_runs_and_commit(built):
    ctx, markup = built
    h = ctx["header"]
    chips = re.search(r'<div class="chips">(.*?)</div>', _own(markup), flags=re.S)
    assert chips
    text = re.sub(r"<[^>]+>", " ", chips.group(1))
    assert h["model"] in text and f"k = {h['k']}" in text and "pilot" in text
    assert f"{h['n_runs']} runs" in text and h["start_text"] in text and h["start"][:10] in h["start_text"]
    assert h["effort"] and h["effort"] in text


def test_the_page_prints_every_commit_of_the_run_sets_in_the_ident_line_and_a_chip(tmp_path, demo_runs_root):
    """Run sets of one model made at two code commits: the page names both."""
    runs = _copy_models(demo_runs_root, tmp_path / "runs", ONE)
    manifest = sorted(runs.glob("*/*/MANIFEST.json"))[0]
    m = json.loads(manifest.read_text(encoding="utf-8"))
    m["git_commit"] = "0123456789abcdef0123456789abcdef01234567"
    manifest.write_text(json.dumps(m), encoding="utf-8")
    ctx = full.context(full.run_sets_in([runs]), tmp_path / "pages" / "report.html", with_gallery=False,
                       make_figs=False)
    markup = full.build_html(ctx)
    commits = ctx["header"]["commit"].split(", ")
    assert len(commits) == 2 and "0123456" in commits
    own = _own(markup)
    ident = re.search(r'<div class="ident">(.*?)</div>', own, flags=re.S)
    chips = re.search(r'<div class="chips">(.*?)</div>', own, flags=re.S)
    assert ident and chips
    for commit in commits:
        assert commit in ident.group(1), commit
        assert commit in chips.group(1), commit
    assert ctx["ident"]["commit"] == ctx["header"]["commit"]


def test_the_page_names_its_version_task_set_hash_and_commit_above_the_tabs(built):
    ctx, markup = built
    root = _dom(_own(markup))
    first_tab = _tab(root, "models")
    lines = []
    for n in root.iter():
        if n is first_tab:
            break
        if "ident" in n.cls:
            lines.append(n.text())
    assert len(lines) == 1
    pilot_hash = next(line.split()[0] for line in resource("tasks/tasks.sha256").read_text(encoding="utf-8")
                      .splitlines() if line.split()[-1:] == ["pilot"])
    assert full.REPORT_VERSION in re.split(r"[\s·v]+", lines[0])
    assert pilot_hash[:7] in lines[0]
    assert ctx["header"]["commit"].split(", ")[0][:7] in lines[0]


def test_overview_numbers_of_the_models_tab_come_from_the_runs(built):
    ctx, markup = built
    region = " ".join(n.text() for n in _regions(_tab(_dom(_own(markup)), "models"))["Overview"]
                      if n.tag in ("figure", "table"))
    for s in ctx["bench"]["shares"]:
        assert f"{s['k']}/{s['n']}" in region or f"{s['k']} of {s['n']}" in region
    for p in ctx["bench"]["paired"]:
        assert p["pair"] in region


@pytest.mark.parametrize(("p", "text"), [(None, "–"), (3.67e-8, "< 0.001"), (0.00049, "< 0.001"),
                                          (0.0005, "0.001"), (0.0421, "0.042"), (1.0, "1.000")])
def test_p_values_below_one_in_a_thousand_are_not_printed_as_zero(p, text):
    assert full.p_text(p) == text


def test_p_values_and_cost_sums_round_a_half_up():
    assert [full.p_text(p) for p in (0.0625, 0.0635, 0.0015)] == ["0.063", "0.064", "0.002"]
    bench = {"header": {"conds": ["A"]}, "runs": [
        {"cond": "A", "outcome": "correct", "values": {"cost_usd": 0.125}},
        {"cond": "A", "outcome": "gross", "values": {"cost_usd": 0.25}}]}
    row = full._cost_rows(bench)[0]
    assert (row["total"], row["correct_cost"], row["per_correct"]) == ("0.38", "0.13", "0.38")


def test_coverage_percentages_round_a_half_up():
    c = {"coverage": {"total": {"pct": 12.25, "reported_pct": 2.25},
                      "packages": [{"pct": 12.25}, {"pct": 2.25}, {"pct": 99.95}]}}
    full._checks_view(c)
    assert c["coverage"]["total"]["pct_text"] == "12.3 %" and c["coverage"]["total"]["reported_text"] == "2.3 %"
    assert [p["pct_text"] for p in c["coverage"]["packages"]] == ["12.3", "2.3", "100.0"]


def test_the_paired_table_prints_the_exact_mcnemar_p_of_33_against_2_as_below_a_thousandth(built):
    ctx, _ = built
    bench = copy.deepcopy(ctx["views"][0]["bench"])
    bench["paired"][0]["p"] = mcnemar_exact(33, 2)  # 3.7e-08
    full._view(bench)
    assert bench["paired"][0]["p_text"] == "< 0.001"


def test_the_surviving_mutants_print_the_changed_lines_only_and_the_function_once(built):
    ctx, markup = built
    blocks = re.findall(r'<pre class="diffx">(.*?)</pre>', _own(markup), flags=re.S)
    assert len(blocks) == sum(m["n"] for m in ctx["survivors"]) == 2
    for block in blocks:
        assert block.splitlines() == ["-    return 1", "+    return 2"]
    for m in ctx["survivors"]:
        for fn in m["functions"]:
            assert _own(markup).count(f"<code>{fn['function']}</code>") >= 1


def _survivor(module: str, function: str, n: int) -> dict:
    return {"module": module, "function": function, "mutants": [{"mutant": f"{function}{i}", "diff": "d"}
                                                                for i in range(n)]}


def test_the_surviving_mutants_table_adds_up_to_every_survivor_with_remainder_rows():
    """Modules beyond the first 15 and functions beyond the first 3 of a module are one remainder row each."""
    fns = [[_survivor(f"m{i:02d}", f"f{j}", 1 + (i + j) % 3) for j in range(5 if i == 0 else 1)] for i in range(17)]
    mods: list[dict[str, Any]] = [{"module": f"m{i:02d}", "n": sum(len(f["mutants"]) for f in fns[i]),
                                   "functions": fns[i]} for i in range(17)]
    rows = full.survivor_rows(mods)
    assert sum(r["survived"] for r in rows) == sum(m["n"] for m in mods)
    first = [r for r in rows if r["module"] == "m00"]
    assert [r["function"] for r in first] == ["f0", "f1", "f2", "2 other functions"]
    assert first[-1]["other"] is True
    assert first[-1]["survived"] == sum(len(f["mutants"]) for f in fns[0][3:])
    assert rows[-1] == {"module": "2 other modules", "function": "", "survived": mods[15]["n"] + mods[16]["n"],
                        "other": True}
    assert len([r for r in rows if not r["other"]]) == 3 + 14


def test_the_surviving_mutants_table_has_no_remainder_row_when_everything_is_listed():
    mods = [{"module": "m", "n": 2, "functions": [_survivor("m", "f", 2)]}]
    assert full.survivor_rows(mods) == [{"module": "m", "function": "f", "survived": 2, "other": False}]
    assert full.survivor_rows([]) == []


def test_the_surviving_mutants_table_has_a_row_for_the_survivors_a_shard_counts_but_does_not_list():
    mods = [{"module": "m", "n": 2, "functions": [_survivor("m", "f", 2)]}]
    rows = full.survivor_rows(mods, unlisted=[{"shard": "score", "survived": 5}, {"shard": "cli", "survived": 2}])
    assert sum(r["survived"] for r in rows) == 2 + 5 + 2
    assert rows[-2:] == [{"module": "shard score", "function": "5 survivors not listed", "survived": 5, "other": True},
                         {"module": "shard cli", "function": "2 survivors not listed", "survived": 2, "other": True}]
    assert full.survivor_rows(mods, unlisted=[]) == full.survivor_rows(mods)


def test_the_page_table_of_surviving_mutants_adds_up_to_the_survived_count_of_the_shards(built):
    ctx, markup = built
    checks = ctx["checks"]
    assert checks["mutation"]["unlisted"], "the fixture has a shard that counts a survivor it does not list"
    assert sum(r["survived"] for r in ctx["survivor_rows"]) == checks["mutation"]["survived"]
    assert "survivor not listed" in _tab(_dom(_own(markup)), "checks").text()


def test_the_call_path_table_and_module_table_print_their_remainder_rows(built):
    ctx, _ = built
    ctx = copy.deepcopy(ctx)
    ctx["views"][0]["paths"].append({"cond": "", "path": "7 other paths", "runs": 9, "correct": 4, "other": True})
    ctx["checks"]["points_other"] = {"modules": 4, "mutants": 21, "survived": 6, "score_text": "71.4"}
    ctx["survivor_rows"].append({"module": "3 other modules", "function": "", "survived": 5, "other": True})
    text = _tab(_dom(_own(full.build_html(ctx))), "models").text()
    assert "7 other paths" in text
    checks = _tab(_dom(_own(full.build_html(ctx))), "checks").text()
    assert "4 other modules" in checks and "71.4" in checks and "3 other modules" in checks


def test_published_spectra_show_paper_values_doi_links_and_table_locators(built):
    ctx, markup = built
    node = _tab(_dom(_own(markup)), "spectra")
    text = node.text()
    assert "Paper" in text and "Oracle" in text
    hrefs = set(_hrefs(node))
    for s in ctx["bench"]["literature"]:
        if s["doi"]:
            assert f"https://doi.org/{s['doi']}" in hrefs, s["task"]
        if s["locator"]:
            assert s["locator"] in text, s["task"]
    assert "Table 2" in text  # P-literature_new-01: a source without a DOI


def test_a_doi_with_url_characters_is_percent_encoded_in_both_links(built):
    """'#', '?', '<' and '>' of an old SICI DOI would cut the URL (fragment, query): the href holds them encoded."""
    ctx, _ = built
    ctx = copy.deepcopy(ctx)
    doi = "10.1002/(SICI)1097-4555(199708)28:8<593::AID-JRS157>3.0.CO;2-#"
    ctx["views"][0]["bench"]["tasks_view"][0]["tasks"][0]["source"]["doi"] = doi
    ctx["systems"][0]["doi"] = doi
    hrefs = [h for h in _hrefs(_dom(_own(full.build_html(ctx)))) if "SICI" in h]
    want = "https://doi.org/10.1002/(SICI)1097-4555(199708)28:8%3C593::AID-JRS157%3E3.0.CO;2-%23"
    assert hrefs and set(hrefs) == {want} and len(hrefs) == 2


def test_checks_tab_merges_both_mutation_folders_and_marks_packages_without_a_result(built):
    ctx, markup = built
    shards = [s["name"] for s in ctx["checks"]["mutation"]["shards"]]
    assert sorted(shards) == ["cli", "core"]
    overview = " ".join(n.text() for n in _regions(_tab(_dom(_own(markup)), "checks"))["Overview"])
    assert "41" in overview and "not mutated" in overview
    assert "report" in ctx["checks"]["not_mutated"]
    assert f"{ctx['checks']['coverage']['total']['reported_pct']:.1f}" in overview  # coverage.py's own total


def test_the_coverage_figure_is_named_line_coverage_not_mutation_score(built):
    _, markup = built
    assert markup.count('aria-label="Line coverage per package, 0 to 100 percent"') == 1
    assert markup.count('aria-label="Mutation score per row, 0 to 100 percent"') == 1  # the shard figure only


def test_method_and_platform_tab_holds_the_method_tables(built):
    ctx, markup = built
    assert set(ctx["method"]) == {"identity", "protocol", "statistics", "class_intervals", "provenance",
                                  "exclusions", "limits"}
    regions = _regions(_tab(_dom(_own(markup)), "platform"))
    for section in METHOD_SECTIONS:
        assert [n for n in regions[section] if n.tag == "table"], section
    assert len([n for n in regions["Statistics"] if n.tag == "table"]) >= 2  # methods and class intervals
    assert len([n for n in regions["Exclusions and limits"] if n.tag == "table"]) >= 2


def test_the_limits_table_prints_the_completeness_and_the_rescued_answers(built):
    ctx, markup = built
    items = {r["item"]: r["value"] for r in ctx["method"]["limits"]}
    assert "Cells below the planned k" in items and int(items["Rescued answers"]) >= 1
    table = markup[markup.index('id="tbl-limits"'):]
    table = table[:table.index("</table>")]
    assert "Cells below the planned k" in table and "Rescued answers" in table


def test_the_conditions_table_prints_every_prompt_file_the_plan_pinned_with_its_runs(built):
    ctx, markup = built
    rows = ctx["method"]["protocol"]["conditions"]
    table = next(n for n in _dom(_own(markup)).find("table") if n.attrs.get("id") == "tbl-conditions")
    body = [n for n in table.find("tr") if n.find("td")]
    assert len(body) == len(rows) >= 3
    for node, row in zip(body, rows, strict=True):
        cells = [c.text() for c in node.find("td")]
        assert cells[0] == row["cond"] and cells[2] == row["prompt"]
        assert cells[3] == row["sha256"][:12] and cells[4] == ("–" if row["runs"] is None else str(row["runs"]))


def test_every_placed_figure_has_a_provenance_row(built):
    ctx, _ = built
    keys = {r["key"] for r in ctx["method"]["provenance"]}
    placed = {k for sections in full.PLACEMENT.values() for _, figs in sections for k, _, _ in figs}
    assert placed and placed <= keys


def _provenance_cells(markup: str) -> list[list[str]]:
    plat = _tab(_dom(_own(markup)), "platform")
    table = plat.find("table", id="tbl-provenance")
    assert len(table) == 1
    return [[c.text() for c in tr.find("td")] for tr in table[0].find("tr") if tr.find("td")]


def test_the_provenance_table_prints_the_result_of_each_check(built):
    ctx, markup = built
    cells = _provenance_cells(markup)
    assert len(cells) == len(ctx["method"]["provenance"])
    text = " ".join(" ".join(row) for row in cells)
    assert "recorded hashes match" in text
    broken = copy.deepcopy(ctx)
    files = [f for r in broken["method"]["provenance"] for f in r["files"]]
    files[0].update(sha256=None, verified="not found")
    assert "not found" in " ".join(" ".join(r) for r in _provenance_cells(full.build_html(broken)))


def test_the_page_lists_the_hash_links_of_every_run_set_and_names_the_broken_ones(built2):
    ctx, markup = built2
    plat = _tab(_dom(_own(markup)), "platform")
    table = plat.find("table", id="tbl-chains")
    assert len(table) == 1
    rows = [[c.text() for c in tr.find("td")] for tr in table[0].find("tr") if tr.find("td")]
    assert [r[0] for r in rows] == [c["set"] for c in ctx["platform"]["chains"]] and len(rows) > 1
    broken = copy.deepcopy(ctx)
    broken["platform"]["chains"][-1]["broken"] = [{"from": "m/B/medium", "to": "MANIFEST.json",
                                                   "field": "transcripts", "ok": False}]
    table = _tab(_dom(_own(full.build_html(broken))), "platform").find("table", id="tbl-chains")[0]
    last = [c.text() for c in table.find("tr")[-1].find("td")]
    assert "m/B/medium" in " ".join(last) and "transcripts" in " ".join(last)


def test_platform_tab_names_what_the_run_records_do_not_hold(built):
    _, markup = built
    text = _tab(_dom(_own(markup)), "platform").text()
    assert "not recorded" in text and "CPU" in text


def test_data_notes_list_every_note_or_say_none(built):
    ctx, markup = built
    region = _regions(_tab(_dom(_own(markup)), "platform"))["Data notes"]
    text = " ".join(n.text() for n in region if n.parent is not None and n.parent not in region)
    notes = [*ctx["bench"]["notes"], *ctx["platform"]["notes"], *ctx["checks"]["mutation"]["notes"]]
    if notes:
        assert all(n["text"] in text for n in notes)
    else:
        assert "none" in text


def test_the_gallery_folds_its_run_cards_into_one_closed_block_per_class(built):
    ctx, markup = built
    region = _regions(_tab(_dom(_own(markup)), "gallery"))["Run gallery"]
    blocks = [n for n in region if n.tag == "details" and not n.inside("details")]
    classes = {t["cls"] for t in ctx["gal"]["run_tasks"]}
    assert len(blocks) == len(classes) and all("open" not in b.attrs for b in blocks)


# ---------------------------------------------------------------- what the page never holds


def _prose(root: Node) -> list[str]:
    """Text nodes outside tables, captions, code, pre, figures, lists of the table of contents and scripts."""
    skip = {"table", "figcaption", "caption", "code", "pre", "svg", "title", "script", "style", "nav", "summary"}
    out = []

    def walk(n: Node) -> None:
        if n.tag in skip:
            return
        for k in n.kids:
            if isinstance(k, str):
                if k.strip():
                    out.append(" ".join(k.split()))
            else:
                walk(k)

    walk(root)
    return out


def test_no_paragraphs(built):
    _, markup = built
    root = _dom(_own(markup))
    long = [t for t in _prose(root) if len(t.split()) > 25]
    assert not long, long[:3]
    paras = [p.text() for p in root.iter() if p.tag == "p"]
    assert not [t for t in paras if len(t.split()) > 12 or len(re.findall(r"[.!?](\s|$)", t)) > 1], paras[:3]


def test_no_figure_numbers_and_no_interpretation_words(built):
    _, markup = built
    root = _dom(_own(markup))
    prose = _prose(root)
    assert not [t for t in prose if re.search(r"\b(Figure|Fig\.)\s*\d", t)]
    caps = [n.text() for n in root.iter() if n.tag in ("figcaption", "h2", "h3", "h4")]
    assert not [t for t in caps if re.search(r"\b(Figure|Fig\.|Table)\s*\d", t)]
    words = re.compile(r"\b(therefore|because|suggests?|better|worse)\b", re.I)
    hits = [t for t in prose + caps if words.search(t)]
    assert not hits, hits[:3]


@pytest.mark.parametrize("page", ["built", "built2", "built_conf"])
def test_ids_are_unique_and_no_external_request(page, request):
    _, markup = request.getfixturevalue(page)
    own = _own(markup)
    ids = re.findall(r'\sid="([^"]+)"', own)
    assert len(ids) == len(set(ids))
    assert not re.search(r'src="(https?:)?//', own)
    external = re.findall(r'href="((?:https?:)?//[^"]*)"', own)
    assert all(h.startswith("https://doi.org/") for h in external), external[:3]


# ---------------------------------------------------------------- several models


def _body_rows(table: Node) -> list[Node]:
    return [n for n in table.iter() if n.tag == "tr" and n.parent is not None and n.parent.tag == "tbody"]


def _table(root: Node, ident: str) -> Node:
    found = [n for n in root.iter() if n.tag == "table" and n.attrs.get("id") == ident]
    assert len(found) == 1, ident
    return found[0]


def test_no_page_has_a_model_switch_or_a_view_per_model(built, built2):
    for ctx, markup in (built, built2):
        own = _own(markup)
        root = _dom(own)
        assert not root.find("select")
        assert not [n for n in root.iter() if {"mview", "mtoc", "mline", "mswitch"} & set(n.cls)]
        for needle in ("model-switch", "mview", "mtoc", "setModel", "tsb-model", "data-model=\"claude"):
            assert needle not in _script(markup) + _styles(markup), needle
        assert not [v for v in ctx["views"] if "pfx" in v or "figs" in v or "toc" in v]


def test_one_model_has_no_model_column_and_no_comparison(built):
    ctx, markup = built
    own = _own(markup)
    root = _dom(own)
    assert ctx["compare"] is None and not root.find("table", id="tbl-models")
    chips = re.search(r'<div class="chips">(.*?)</div>', own, flags=re.S)
    assert chips and ONE[0] in chips.group(1)
    for ident in ("tbl-intervals", "tbl-shares", "tbl-paired", "tbl-outcome", "tbl-medians"):
        assert "Model" not in [th.text() for th in _table(root, ident).iter() if th.tag == "th"], ident
    assert not [n for n in root.iter() if "mn" in n.cls]


def test_each_tab_has_one_table_of_contents_whose_ids_exist_on_a_page_of_two_models(built2):
    ctx, markup = built2
    root = _dom(_own(markup))
    for tab, _ in TABS:
        node = _tab(root, tab)
        navs = [n for n in node.iter() if _toc_nav(n)]
        assert len(navs) == 1, tab
        assert len([n for n in navs[0].iter() if n.tag == "ol"]) == 1, tab
        ids = set(_ids(node))
        entries = ctx["toc"][tab]
        assert [t for lv, _, t in entries if lv == 2] == [s for s, _ in PLACEMENT[tab]], tab
        assert {i for _, i, _ in entries} <= ids, tab
        assert {f"#{i}" for _, i, _ in entries} == set(_hrefs(navs[0])), tab
    level4 = {(i, t) for lv, i, t in ctx["toc"]["tasks"] if lv == 4}
    assert {(f"task-{t}", t) for t in PILOT} <= level4


def test_the_models_stand_in_one_order_on_the_page(built2):
    ctx, markup = built2
    want = sorted(TWO, key=base.model_key)
    assert [v["model"] for v in ctx["views"]] == want == ["claude-haiku-5-5", "claude-sonnet-5-5"]
    assert [x["model"] for x in ctx["compare"]] == want
    root = _dom(_own(markup))
    for ident in ("tbl-shares", "tbl-paired", "tbl-outcome", "tbl-medians", "tbl-usd", "tbl-tools"):
        seen = [r.text().split()[0] for r in _body_rows(_table(root, ident))]
        assert list(dict.fromkeys(seen)) == want, ident


def test_every_figure_of_two_models_is_the_all_models_version_at_the_full_width(built2):
    ctx, markup = built2
    assert set(full.ALL_MODELS) == {k for tab in ("models", "tasks", "spectra") for _, k, _, _ in _figures(tab)}
    root = _dom(_own(markup))
    questions = list(full.ALL_MODELS.values())
    assert len(set(questions)) == len(questions) and all(q.endswith("?") and len(q) < 110 for q in questions)
    for tab in ("models", "tasks", "spectra"):
        regions = _regions(_tab(root, tab))
        for section, key, _, _ in _figures(tab):
            if key not in ctx["figs"]:  # no data in the demo run set
                continue
            f = [n for n in _fig_nodes(regions[section]) if n.attrs.get("data-key") == key]
            assert len(f) == 1, key
            assert "full" in f[0].cls and f[0].attrs["id"] == f"fig-{key}", key
            assert [n for n in f[0].iter() if n.tag == "figcaption"][0].text() == full.ALL_MODELS[key], key
            assert [s.attrs.get("width") for s in f[0].iter() if s.tag == "svg"] == ["960"], key


@pytest.mark.parametrize("key", ["share", "paired", "outcome", "swarm", "tool_output", "classes", "sunburst", "upset",
                                 "ledger"])
def test_a_figure_of_two_models_names_both(built2, key):
    fig = built2[0]["figs"][key]["svg"]
    for name in TWO:
        assert name in fig, (key, name)


def test_the_outcome_figure_counts_the_runs_of_both_models(built2):
    ctx, _ = built2
    fig = str(ctx["figs"]["outcome"]["svg"])
    for v in ctx["views"]:
        for o in v["bench"]["outcome"]:
            n = sum(o["counts"].values())
            k = o["counts"].get("correct", 0)
            if k:
                assert f"{v['model']} · {o['cond']}: correct {k} of {n} runs" in fig


def test_the_bubbles_have_the_median_tokens_and_share_of_each_model_and_condition(built2):
    ctx, _ = built2
    fig = str(ctx["figs"]["cost"]["svg"])
    want = 0
    for v in ctx["views"]:
        med = {m["cond"]: m for m in v["bench"]["cost"]["medians"]}
        for s in v["bench"]["shares"]:
            if med[s["cond"]].get("output_tokens"):
                want += 1
                assert f"{v['model']}, {s['cond']}: median" in fig
                assert f"{s['k']}/{s['n']} runs" in fig
    assert want and fig.count('class="bubble ') == want


def test_the_heat_map_shows_the_solved_tasks_of_each_model_with_the_ramp_of_the_comparison_page(built2):
    from tsbench.report import comparison

    ctx, _ = built2
    fig = str(ctx["figs"]["classes"]["svg"])
    for v in ctx["views"]:
        for blk in v["bench"]["tasks_view"]:
            for c in v["bench"]["header"]["conds"]:
                n = blk["n_by"].get(c, blk["n"])
                if n:
                    assert f"{v['model']}, {c}, {blk['class']}: {blk['k'].get(c, 0)} of {n} tasks" in fig
                    assert f"fill:{comparison.heat_color(blk['k'].get(c, 0) / n)[0]}" in fig


def test_panels_of_two_models_share_one_scale(built2):
    ctx, _ = built2
    upset = [b["upset"] for b in (v["bench"] for v in ctx["views"])]
    peak, _ = full.outcome.upset_scale(upset)
    assert peak == max(len(s["tasks"]) for sets in upset for s in sets)
    bench = {v["model"]: v["bench"] for v in ctx["views"]}
    assert full._categories(list(bench.values()))[0] == ("correct", "correct")


def test_cost_maps_have_heights_in_proportion_to_their_totals():
    def bench(cost: float, estimate: bool = False) -> dict:
        return {"header": {"cost_is_estimate": estimate},
                "runs": [{"cond": "A", "class": "x", "task": "t", "outcome": "correct", "values": {"cost_usd": cost}}]}

    cats = [("correct", "correct")]
    got = dict(full._cost_maps({"big": bench(8.0), "small": bench(4.0), "tiny": bench(0.1), "gw": bench(9.0, True)},
                               cats, 960.0))
    tall, low = full.MAP_HEIGHT
    tile = r'class="tile ok"[^>]* height="([0-9.]+)"'
    height = {m: float(re.search(tile, got[m]).group(1)) for m in ("big", "small", "tiny")}  # type: ignore[union-attr]
    head = 35.0  # the headers of condition and class take this much of a map
    assert height["big"] + head == pytest.approx(tall, abs=1)
    assert height["big"] + head == pytest.approx(2 * (height["small"] + head), abs=1)
    assert height["tiny"] + head == pytest.approx(low, abs=1) and got["gw"] == ""
    assert "not to the scale" in got["tiny"] and "not to the scale" not in got["small"]


def test_a_task_has_one_row_with_the_answers_of_every_model(built2):
    ctx, markup = built2
    node = _tab(_dom(_own(markup)), "tasks")
    rows = {n.attrs["id"]: n for n in node.iter() if n.tag == "tr" and n.attrs.get("id", "").startswith("task-")}
    assert set(rows) == {f"task-{t}" for t in PILOT}
    cards = {c["anchor"]: c["head"] for t in ctx["gal"]["run_tasks"] for c in t["cards"]}
    run_links = 0
    for v in ctx["views"]:
        for blk in v["bench"]["tasks_view"]:
            for row in blk["tasks"]:
                text = rows[f"task-{row['id']}"].text()
                for cond, a in row["answers"].items():
                    assert " ".join(str(a["text"]).split()) in text, (v["model"], row["id"], cond)
                    assert v["model"] in text
                    if a["href"]:
                        head = cards[a["href"][1:]]
                        assert (head["model"], head["cond"], head["task"]) == (v["model"], cond, row["id"])
                        assert a["href"] in _hrefs(rows[f"task-{row['id']}"])
                        run_links += 1
    assert run_links


def test_the_classes_and_spectra_tables_hold_a_line_per_model(built2):
    ctx, markup = built2
    root = _dom(_own(markup))
    classes = _table(root, "tbl-classes")
    assert len(_body_rows(classes)) == len(ctx["task_blocks"])
    text = classes.text()
    for v in ctx["views"]:
        for blk in v["bench"]["tasks_view"]:
            for c, k in blk["k"].items():
                n = blk["n_by"].get(c, blk["n"])
                assert (f"{k} of {n}" if n else "no run") in text
    union = {x["task"] for v in ctx["views"] for x in v["bench"]["literature"]}
    assert len(_body_rows(_table(root, "tbl-systems"))) == len(ctx["systems"]) == len(union)
    answers = _table(root, "tbl-system-answers")
    assert len(_body_rows(answers)) == len(union)
    for v in ctx["views"]:
        assert v["model"] in answers.text()


def test_a_task_of_one_model_only_keeps_its_row():
    bench = {"tasks_view": [{"class": "x", "tasks": [{"id": "t1", "answers": {"A": {"ok": True}}}]}]}
    other = {"tasks_view": [{"class": "x", "tasks": [{"id": "t2", "answers": {"A": {"ok": False}}}]},
                            {"class": "y", "tasks": [{"id": "t3", "answers": {}}]}]}
    blocks = full._task_blocks([{"model": "m1", "bench": bench}, {"model": "m2", "bench": other}])
    assert [b["class"] for b in blocks] == ["x", "y"]
    assert [r["id"] for r in blocks[0]["tasks"]] == ["t1", "t2"]
    assert blocks[0]["tasks"][1]["by_cond"] == {"A": [("m2", {"ok": False})]}
    assert [m for m, _ in blocks[0]["by_model"]] == ["m1", "m2"]


def test_two_models_open_the_overview_with_the_table_of_the_models(built2):
    ctx, markup = built2
    root = _dom(_own(markup))
    regions = _regions(_tab(root, "models"))
    assert next(iter(regions)) == "Overview"
    table = [n for n in regions["Overview"] if n.tag == "table" and n.attrs.get("id") == "tbl-models"]
    assert len(table) == 1
    rows = _body_rows(table[0])
    assert [r.text().split()[0] for r in rows] == [x["model"] for x in ctx["compare"]]
    for r, x in zip(rows, ctx["compare"], strict=True):
        text = r.text()
        assert x["endpoint"] in text and str(x["n_runs"]) in text
        for cond, cell in x["cells"].items():
            assert f"{cell['k']} of {cell['n']}" in text, (x["model"], cond)
    assert (4, "tbl-models", "Models") in ctx["toc"]["models"]


def test_solution_paths_of_two_models_keep_apart_and_a_task_link_needs_a_row(built2):
    ctx, _ = built2
    hids = [sp["hid"] for sp in ctx["solution_paths"]]
    assert len(set(hids)) == len(hids)
    task = next(iter(ctx["task_ids"]))
    assert ctx["task_href"](task) == f"#task-{task}" and ctx["task_href"]("nope") is None


def test_two_models_header_counts_every_model_and_every_run(built2):
    ctx, markup = built2
    h = ctx["header"]
    chips = re.search(r'<div class="chips">(.*?)</div>', _own(markup), flags=re.S)
    assert chips
    text = re.sub(r"<[^>]+>", " ", chips.group(1))
    assert "2 models" in text
    total = sum(v["bench"]["header"]["n_runs"] for v in ctx["views"])
    assert h["n_runs"] == total and f"{total} runs" in text


def test_the_class_intervals_table_names_the_model_of_each_row_with_two_models(built2):
    ctx, markup = built2
    root = _dom(_own(markup))
    table = [n for n in root.iter() if n.tag == "table" and n.attrs.get("id") == "tbl-intervals"][0]
    assert [th.text() for th in table.iter() if th.tag == "th"][0] == "Model"
    rows = [n for n in table.iter() if n.tag == "tr" and n.parent is not None and n.parent.tag == "tbody"]
    assert {r.text().split()[0] for r in rows} == set(TWO)
    assert len(rows) == len(ctx["method"]["class_intervals"])


def test_keep_names_model_condition_task_and_k_of_every_model(built2):
    ctx, _ = built2
    keep = full._keep({v["model"]: v["bench"] for v in ctx["views"]})
    assert keep is not None
    assert {m for m, _, _, _ in keep} == set(TWO)
    for v in ctx["views"]:
        assert {(v["model"], r["cond"], r["task"], int(r["k"])) for r in v["bench"]["runs"]} <= keep


def test_the_slug_of_a_model_is_unique_and_safe():
    assert full._prefixes(["Claude Sonnet 5.5", "claude-sonnet-5-5", "a/b"]) == {
        "Claude Sonnet 5.5": "claude-sonnet-5-5-", "claude-sonnet-5-5": "claude-sonnet-5-5-2-", "a/b": "a-b-"}
    assert full._prefixes(["only"]) == {"only": ""}


# ---------------------------------------------------------------- inputs


def test_without_coverage_the_checks_tab_names_the_missing_input(tmp_path, demo_runs_root):
    runs = tmp_path / "runs"
    shutil.copytree(demo_runs_root / "demo-claude", runs)
    ctx = full.context(full.run_sets_in([runs]), tmp_path / "r.html", with_gallery=False)
    node = _tab(_dom(_own(full.build_html(ctx))), "checks")
    assert "--coverage" in node.text()
    assert not _fig_nodes(list(node.iter()))


def test_a_full_render_parses_each_transcript_once(tmp_path, monkeypatch, demo_runs_root):
    """The facts and the gallery read a transcript through one reader: no transcript is opened as text twice in one
    render, whichever function does the reading (`iter_events`, `read_transcript`, a plain `open`)."""
    import builtins
    import collections
    import io

    runs = _copy_models(demo_runs_root, tmp_path / "runs", ONE)
    opened = collections.Counter()
    real_open, real_io_open = builtins.open, io.open

    def count(f, mode):
        if str(f).endswith(".jsonl") and "-k" in pathlib.Path(f).name and "b" not in str(mode):  # a transcript
            opened[str(pathlib.Path(f).resolve())] += 1

    def spy_open(f, mode="r", *a, **kw):
        count(f, mode)
        return real_open(f, mode, *a, **kw)

    def spy_io_open(f, mode="r", *a, **kw):  # pathlib.Path.open goes through io.open
        count(f, mode)
        return real_io_open(f, mode, *a, **kw)

    monkeypatch.setattr(builtins, "open", spy_open)
    monkeypatch.setattr(io, "open", spy_io_open)
    ctx = full.context(full.run_sets_in([runs]), tmp_path / "pages" / "r.html", make_figs=False)
    monkeypatch.undo()
    assert ctx["gal"] and opened
    assert max(opened.values()) == 1, opened.most_common(3)


def test_a_cache_that_evicts_still_returns_the_same_transcripts():
    """A `TranscriptCache` too small to keep a transcript reads it again; the result does not change."""
    import tempfile

    from tsbench.score.artifacts import TranscriptCache
    from tsbench.score.extract import read_transcript

    line = json.dumps({"type": "result", "result": "x", "is_error": False})
    with tempfile.TemporaryDirectory() as d:
        paths = []
        for i in range(3):
            f = pathlib.Path(d) / f"a{i}.jsonl"
            f.write_text(line + "\n", encoding="utf-8")
            paths.append(f)
        tiny = TranscriptCache(max_bytes=len(line) + 1)  # room for one transcript
        got = [tiny(f) for f in paths + paths]
        assert [g.result for g in got] == [read_transcript(f).result for f in paths + paths]
        assert tiny._size <= tiny.max_bytes


def test_main_takes_more_than_one_mutation_folder(tmp_path, monkeypatch, demo_runs_root):
    seen = {}

    def fake_context(run_sets, out, title=None, coverage=None, mutation=(), *rest):
        seen["mutation"] = list(mutation)
        raise SystemExit(0)

    monkeypatch.setattr(full, "context", fake_context)
    runs = tmp_path / "runs"
    shutil.copytree(demo_runs_root / "demo-claude", runs)
    with pytest.raises(SystemExit):
        full.main(["--runs", str(runs), "--out", str(tmp_path / "r.html"), "--coverage", str(tmp_path / "c.json"),
                   "--mutation", str(tmp_path / "m1"), str(tmp_path / "m2")])
    assert [p.name for p in seen["mutation"]] == ["m1", "m2"]


# ---------------------------------------------------------------- one file


def test_the_page_links_no_local_file(built, built2, built_conf):
    for _, markup in (built, built2, built_conf):
        assert page.local_links(markup) == []


def test_a_full_report_embeds_every_figure_and_image_of_its_runs(tmp_path, demo_runs_root):
    runs = _copy_models(demo_runs_root, tmp_path / "runs", TWO)
    t = sorted(runs.rglob("*-k1.jsonl"))[0]
    art = t.with_name(t.name.removesuffix(".jsonl") + ".artifacts")
    art.mkdir(exist_ok=True)
    (art / "made.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * 500_000)
    ctx = full.context(full.run_sets_in([runs]), tmp_path / "pages" / "r.html", with_gallery=True, make_figs=True)
    markup = full.build_html(ctx)
    assert page.local_links(markup) == []
    assert base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"x" * 500_000).decode() in markup
    counts = [c for t in ctx["gal"]["image_tasks"] for c in t["cards"]]
    assert counts and all(c["src"] and c["src"].startswith("data:") for c in counts)
    figs = [f for t in ctx["gal"]["run_tasks"] for c in t["cards"] for f in c["figs"]]
    assert figs and all(f["src"] or f["clone"] for f in figs)


def _links_only(tmp_path: pathlib.Path, demo_runs_root: pathlib.Path) -> list[str]:
    runs = _copy_models(demo_runs_root, tmp_path / "runs", ONE)
    t = sorted(runs.rglob("*-k1.jsonl"))[0]
    art = t.with_name(t.name.removesuffix(".jsonl") + ".artifacts")
    art.mkdir(exist_ok=True)
    (art / "made.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * 5000)
    return ["--runs", str(runs), "--no-figures", "--page-budget", "0"]


def test_the_page_budget_is_an_option_and_links_what_it_leaves_out(tmp_path, demo_runs_root, capsys):
    out = tmp_path / "pages" / "r.html"
    assert full.main([*_links_only(tmp_path, demo_runs_root), "--out", str(out)]) == 0
    assert any(x.endswith("made.png") for x in page.local_links(out.read_text(encoding="utf-8")))


def test_the_images_option_embeds_what_the_image_index_holds(tmp_path, demo_runs_root):
    runs = _copy_models(demo_runs_root, tmp_path / "runs", ONE)
    t = next(p for p in sorted(runs.rglob("*-k1.jsonl")) if ".attempt" not in p.name)
    sets = full.run_sets_in([runs])
    rel = t.relative_to(sets[0].path)
    data = b"\x89PNG\r\n\x1a\n" + b"saved elsewhere"
    images = tmp_path / "images"
    file = images / sets[0].name / "diagram.png"
    file.parent.mkdir(parents=True)
    file.write_bytes(data)
    (images / f"{sets[0].name}.index.csv").write_text(
        "run_id,file,origin,sha256\n"
        f"{rel.with_suffix('').as_posix()},images/{sets[0].name}/diagram.png,recovered,"
        f"{hashlib.sha256(data).hexdigest()}\n", encoding="utf-8")
    out = tmp_path / "pages" / "r.html"
    argv = ["--runs", str(runs), "--no-figures", "--out", str(out), "--images", str(images)]
    assert full.main(argv) == 0
    assert base64.b64encode(data).decode() in out.read_text(encoding="utf-8")
    file.write_bytes(b"changed")
    assert full.main(argv) == 2


def test_a_publication_build_fails_rather_than_link_a_local_file(tmp_path, demo_runs_root, capsys):
    out = tmp_path / "pages" / "r.html"
    assert full.main([*_links_only(tmp_path, demo_runs_root), "--out", str(out), "--publication"]) == 2
    err = capsys.readouterr().err
    assert "made.png" in err and "--page-budget" in err and not out.exists()


def test_a_publication_build_without_a_budget_writes_one_file(tmp_path, demo_runs_root):
    runs = _copy_models(demo_runs_root, tmp_path / "runs", ONE)
    out = tmp_path / "pages" / "r.html"
    assert full.main(["--runs", str(runs), "--no-figures", "--out", str(out), "--publication"]) == 0
    assert page.local_links(out.read_text(encoding="utf-8")) == []


def test_run_cards_copy_their_images_when_their_class_is_opened(built):
    _, markup = built
    script = _script(markup)
    assert re.search(r'addEventListener\("toggle"', script) and "fill(doc)" in script
    assert not re.search(r'^\$\$\("\.clone"\)', script, flags=re.M)


# ---------------------------------------------------------------- print, no script, bad address, resize, copy, theme


def _styles(markup: str) -> str:
    return " ".join(re.findall(r"<style\b[^>]*>(.*?)</style>", markup, flags=re.S))


def _script(markup: str) -> str:
    return " ".join(re.findall(r"<script\b[^>]*>(.*?)</script>", markup, flags=re.S))


def test_print_opens_every_closed_fold_out(built):
    """A closed <details> prints as its summary line only; the print rule and a beforeprint handler show the content."""
    _, markup = built
    printed = "".join(re.findall(r"@media print\s*\{(.*)", _styles(markup), flags=re.S))
    assert re.search(r"details::details-content\s*\{[^}]*content-visibility:\s*visible", printed)
    script = _script(markup)
    assert "beforeprint" in script and "afterprint" in script
    before = script[script.index("beforeprint"):]
    assert re.search(r"\.open\s*=\s*true", before) and "details" in before


def test_controls_that_need_the_script_are_hidden_without_it(built):
    _, markup = built
    styles = _styles(markup)
    for sel in ("#theme-switch", ".copy"):
        rule = re.search(r"html:not\(\.js\)\s*" + re.escape(sel) + r"\b[^{]*\{[^}]*display:\s*none", styles)
        assert rule, sel


def test_a_broken_percent_escape_in_the_address_never_blanks_the_page(built):
    """decodeURIComponent throws on #task-%E0; every call goes through one guarded helper."""
    _, markup = built
    script = _script(markup)
    helper = re.search(r"function\s+(\w+)\s*\(\s*\w+\s*\)\s*\{\s*try\s*\{\s*return\s+decodeURIComponent\([^)]*\)\s*\}"
                       r"\s*catch\s*\([^)]*\)\s*\{\s*return\s+\w+\s*\}", script)
    assert helper, "a decode helper with try/catch and a fallback to the raw text"
    rest = script.replace(helper.group(0), "")
    assert "decodeURIComponent" not in rest
    assert len(re.findall(r"\b" + helper.group(1) + r"\(", rest)) >= 2


def test_the_contents_list_follows_the_window_width(built):
    """Closed below 900 px, open again when the window grows: one media query object with a change listener."""
    _, markup = built
    script = _script(markup)
    assert len(re.findall(r"matchMedia\(", script)) == 1
    assert re.search(r"addEventListener\(\s*[\"']change[\"']", script)
    assert re.search(r"\.open\s*=\s*!\s*\w+\.matches", script)


def test_copy_falls_back_to_the_selection_when_the_clipboard_is_missing_or_refuses(built):
    _, markup = built
    script = _script(markup)
    assert "execCommand" in script and "createElement(\"textarea\")" in script
    assert re.search(r"writeText\(\w+\)\.then\(\s*done\s*,\s*fb\s*\)", script)
    assert re.search(r"else\s*\{?\s*fb\(\)", script)
    # a refused execCommand("copy") is not reported as Copied
    assert re.search(r"if\(\s*doc\.execCommand\(\"copy\"\)\s*\)\s*done\(\)", script)


def test_figures_of_the_run_cards_follow_the_page_theme_not_only_the_system(built):
    _, markup = built
    styles = _styles(markup)
    assert re.search(r"prefers-color-scheme:\s*dark\)\s*\{\s*:root:not\(\[data-theme=[\"']?light[\"']?\]\)\s*\.gallery"
                     r"\s+\.figs\s+img\s*\{[^}]*invert", styles)
    assert re.search(r":root\[data-theme=[\"']?dark[\"']?\]\s*\.gallery\s+\.figs\s+img\s*\{[^}]*invert", styles)


def test_share_and_interval_texts_round_a_half_up():
    """100 * 0.025 and 100 * 0.035 are 2.5 and 3.5: both go up, not to the even neighbour."""
    assert full._interval_text(0.025, 0.035) == "3\u20134 %"


# ---------------------------------------------------------------- the confirmatory split


def test_a_confirmatory_report_reads_the_tasks_of_its_split_and_names_split_and_doi(built_conf):
    ctx, markup = built_conf
    h = ctx["header"]
    assert h["split"] == "confirmatory" and h["preregistration"] == DOI and h["n_runs"] > 0
    assert h["n_evaluable"] > 0 and ctx["views"][0]["task_ids"]
    assert ctx["ident"]["tasks"] == base.split_hash("confirmatory")[:7]
    assert ctx["gal"]["run_tasks"]
    root = _dom(_own(markup))
    chips = [n.text() for n in root.iter() if "chip" in n.cls]
    assert any(c.startswith("confirmatory split ·") for c in chips)
    assert any(DOI in c and "preregistered" in c for c in chips)
    assert f'href="https://doi.org/{DOI}"' in markup


def test_a_confirmatory_report_has_no_pilot_wording(built_conf):
    _, markup = built_conf
    text = _dom(_own(markup)).text().lower()
    assert "not preregistered" not in text and "no hypothesis is tested" not in text
    assert "pilot" not in text, re.findall(r".{60}pilot.{60}", text)[:3]


def test_a_confirmatory_report_shows_the_preregistered_tests_first_in_the_models_tab(built_conf):
    _, markup = built_conf
    root = _dom(_own(markup))
    regions = _regions(_tab(root, "models"))
    assert next(iter(regions)) == "Preregistered tests"
    tables = {t.attrs["id"]: t for t in root.iter() if t.tag == "table" and t.attrs.get("id", "").startswith("tbl-hyp")}
    assert set(tables) == {"tbl-hyp-primary", "tbl-hyp-secondary", "tbl-hyp-mcnemar", "tbl-hyp-efficiency"}
    rows = [[c.text() for c in tr.iter() if c.tag in ("td", "th")] for tr in tables["tbl-hyp-primary"].iter()
            if tr.tag == "tr"][1:]
    assert [r[0] for r in rows] == ["H2", "H2", "H3"]
    assert rows[1][1] == HYP_MODELS[1] and "1.8 × 10⁻⁵" in rows[1] and "+25.0 pp" in rows[1]
    assert "0.200" in rows[2] and f"({HYP_MODELS[1]} − {HYP_MODELS[0]}) under B minus under C" in rows[2]
    mc = tables["tbl-hyp-mcnemar"].text()
    assert "8" in mc and "4" in mc and "0.390" in mc
    toc = [a.attrs["href"] for a in _tab(root, "models").iter() if a.tag == "a" and a.inside("nav")]
    assert toc[:2] == ["#models-preregistered-tests", "#tbl-hyp-primary"]


def test_a_confirmatory_report_shows_the_efficiency_ratios_as_descriptive(built_conf):
    ctx, html = built_conf
    region = html[html.index('id="tbl-hyp-efficiency"'):]
    table = region[:region.index("</table>")]
    assert "2.50 (1.25 to 5.00)" in table and "0.25 (0.13 to 0.50)" in table
    assert "<th" in table and "C/A" in table and "C/B" in table and ">p<" not in table
    before = html[:html.index('id="tbl-hyp-efficiency"')]
    assert "Efficiency ratios (descriptive)" in before[before.rindex("<h"):]
    assert "#tbl-hyp-efficiency" in [f"#{i}" for _, i, _ in ctx["toc"]["models"]]


def test_the_redactions_option_reaches_the_method_tables(tmp_path, demo_runs_root, capsys):
    runs = _copy_models(demo_runs_root, tmp_path / "runs", ONE)
    run_set = full.run_sets_in([runs])[0]
    manifest = json.loads((run_set.path / "MANIFEST.json").read_text(encoding="utf-8"))
    key = next(iter(manifest["transcripts"]))
    t = run_set.path / f"{key}.jsonl"
    old = hashlib.sha256(t.read_bytes()).hexdigest()
    t.write_bytes(t.read_bytes() + b"\n")
    log = tmp_path / "log.csv"
    log.write_text("file,sha256_original,sha256_published\n"
                   f"{key},{old},{hashlib.sha256(t.read_bytes()).hexdigest()}\n", encoding="utf-8")
    out = tmp_path / "pages" / "report.html"
    assert full.main(["--runs", str(runs), "--out", str(out), "--no-gallery", "--redactions", str(log)]) == 0
    assert "through the path replacement of log.csv" in out.read_text(encoding="utf-8")


def test_an_unreadable_redaction_log_stops_the_report(tmp_path, demo_runs_root, capsys):
    runs = _copy_models(demo_runs_root, tmp_path / "runs", ONE)
    out = tmp_path / "pages" / "report.html"
    args = ["--runs", str(runs), "--out", str(out), "--no-gallery", "--redactions"]
    assert full.main([*args, str(tmp_path / "missing.csv")]) == 2
    assert "missing.csv" in capsys.readouterr().err and not out.exists()


def test_a_pilot_report_shows_no_preregistered_tests(built):
    ctx, markup = built
    assert ctx["header"]["split"] == "pilot" and not ctx["header"].get("preregistration") and not ctx["hypotheses"]
    assert "Preregistered tests" not in markup and "tbl-hyp" not in markup


def test_the_cli_refuses_the_confirmatory_split_without_a_doi(tmp_path, demo_runs_root, capsys):
    runs = _copy_models(demo_runs_root, tmp_path / "runs", ONE)
    out = tmp_path / "r.html"
    assert full.main(["--runs", str(runs), "--out", str(out), "--split", "confirmatory"]) == 2
    assert "--i-have-preregistered" in capsys.readouterr().err and not out.exists()
    assert full.main(["--runs", str(runs), "--out", str(out), "--split", "confirmatory",
                      "--i-have-preregistered", "yes"]) == 2


def test_the_cli_refuses_a_split_other_than_that_of_the_run_sets(tmp_path, demo_runs_root, capsys):
    runs = _copy_models(demo_runs_root, tmp_path / "runs", ONE)
    out = tmp_path / "r.html"
    assert full.main(["--runs", str(runs), "--out", str(out), "--split", "confirmatory",
                      "--i-have-preregistered", DOI]) == 2
    assert "--split pilot" in capsys.readouterr().err and not out.exists()


def test_the_cli_passes_the_split_and_the_doi_to_the_page(tmp_path, demo_runs_root, monkeypatch):
    seen = {}

    def fake_context(run_sets, out, title=None, coverage=None, mutation=(), *rest):
        seen["rest"] = rest
        raise SystemExit(0)

    monkeypatch.setattr(full, "context", fake_context)
    runs = _copy_models(demo_runs_root, tmp_path / "runs", ONE)
    for rs in full.run_sets_in([runs]):
        (rs.path / "MANIFEST.json").write_text(json.dumps({"split": "confirmatory"}), encoding="utf-8")
        for name in ("plan.jsonl", "plan.sealed.json"):
            (rs.path / name).unlink(missing_ok=True)
    with pytest.raises(SystemExit):
        full.main(["--runs", str(runs), "--out", str(tmp_path / "r.html"), "--split", "confirmatory",
                   "--i-have-preregistered", DOI])
    assert seen["rest"][-4:-2] == ("confirmatory", DOI)
