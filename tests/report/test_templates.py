"""The report pages are built from Jinja templates (src/tsbench/report/templates/), not from HTML in Python strings.

Three checks: no report module writes page markup itself, the template environment escapes every value and fails on
an unknown name, and each page built from the demo run set (fake claude) has content (visible text, JSON data blocks,
links) that the same run set reproduces in another folder."""
from __future__ import annotations

import html.parser
import inspect
import json
import pathlib
import re
import shutil

import jinja2
import pytest

from tsbench.report import comparison, coverage, dashboard, gallery, literature, page

REPO = pathlib.Path(__file__).resolve().parents[2]
REPORT = REPO / "src" / "tsbench" / "report"

MARKUP = re.compile(r"<(div|style|table|html)\b")


@pytest.mark.parametrize("path", sorted(REPORT.glob("*.py")), ids=lambda p: p.name)
def test_no_page_markup_in_python(path):
    found = sorted({m.group(0) for m in MARKUP.finditer(path.read_text(encoding="utf-8"))})
    assert not found, f"{path.name} writes page markup itself: {found}"


def test_only_page_py_marks_html_as_safe():
    """Markup() is made in page.py only, for HTML the code itself built; no template turns escaping off."""
    for path in sorted(REPORT.glob("*.py")):
        if path.name != "page.py":
            assert not re.search(r"\bMarkup\(|markupsafe", path.read_text(encoding="utf-8")), path.name
    for path in sorted((REPORT / "templates").glob("*.j2")):
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"\|\s*safe\b|\bautoescape\b|\bMarkup\b", text), path.name


def test_shared_fragments_are_macros_not_python_helpers():
    markup = page.ENV.from_string('{% from "_macros.html.j2" import status_chip, legend_html, fig %}'
                               '{{ status_chip("wrong", "<b>") }}{{ legend_html(["correct"]) }}'
                               '{{ fig("rate", {"rows": []}, "<c>", "<a>") }}').render()
    assert '<span class="st st-wrong">' in markup and "&lt;b&gt;" in markup and "<b>" not in markup
    assert '<i class="sw sw-correct"></i>' in markup
    assert "<figcaption>&lt;c&gt;</figcaption>" in markup and 'data-alt="&lt;a&gt;"' in markup


MACRO = re.compile(r"{%-?\s*macro\s+(\w+)\s*\(")
FROM_IMPORT = re.compile(r'{%-?\s*from\s+"([^"]+)"\s+import\s+([^%]+?)-?%}')


def _macros_without_a_caller(templates: dict[str, str], python: str) -> list[tuple[str, str]]:
    """(file, macro) of every macro that no template imports from its file, its own file does not call, and no
    Python source names."""
    imported = {(src, n.split(" as ")[0].strip()) for t in templates.values()
                for src, names in FROM_IMPORT.findall(t) for n in names.split(",")}
    lonely = []
    for name, text in templates.items():
        for m in MACRO.finditer(text):
            macro, rest = m.group(1), text[:m.start()] + text[m.end():]
            if (name, macro) in imported or re.search(rf"\b{macro}\(", rest):
                continue
            if re.search(rf"[\"']{macro}[\"']|\.{macro}\(", python):
                continue
            lonely.append((name, macro))
    return lonely


def test_every_macro_has_a_caller():
    templates = {p.name: p.read_text(encoding="utf-8") for p in (REPORT / "templates").glob("*.j2")}
    python = " ".join(p.read_text(encoding="utf-8") for p in REPORT.rglob("*.py"))
    assert _macros_without_a_caller(templates, python) == []
    planted = {"a.j2": '{% macro used(x) %}{{ x }}{% endmacro %}{% macro alone(x) %}{{ x }}{% endmacro %}',
               "b.j2": '{% from "a.j2" import used %}{{ used(1) }}'}
    assert _macros_without_a_caller(planted, "") == [("a.j2", "alone")]


def test_every_function_page_exports_has_a_caller():
    """A function in `page.__all__` is called by a report module, a template or page.py itself, not by a test only."""
    own = re.sub(r"__all__ = \[.*?\]", "", (REPORT / "page.py").read_text(encoding="utf-8"), count=1, flags=re.S)
    texts = [own, *(p.read_text(encoding="utf-8") for p in REPORT.rglob("*.py") if p.name != "page.py"),
             *(p.read_text(encoding="utf-8") for p in (REPORT / "templates").glob("*.j2"))]
    for name in page.__all__:
        if inspect.isfunction(getattr(page, name)):
            uses = sum(len(re.findall(rf"\b{name}\b", t)) for t in texts) - 1  # less its own `def`
            assert uses >= 1, name


def test_answer_sheet_sources_do_not_claim_the_full_report_draws_them():
    """Only dashboard.html.j2 imports answer_parts and includes answer.css; full.html.j2 does neither."""
    templates = REPORT / "templates"
    full = (templates / "full.html.j2").read_text(encoding="utf-8")
    assert "answer_parts" not in full and "answer.css" not in full
    for name in ("answer_parts.html.j2", "answer.css"):
        text = (templates / name).read_text(encoding="utf-8")
        assert "full report" not in text, name
        assert "full.css" not in text, name


def test_frame_takes_its_body_and_styles_from_blocks_only():
    """base.html.j2 has no `body`, `css` or `js` fallback from the context: a page fills the blocks."""
    text = (REPORT / "templates" / "base.html.j2").read_text(encoding="utf-8")
    assert 'default("")' not in text
    assert page.render("base.html.j2", title="T").count("<main") == 1


def test_each_dark_value_is_written_once_in_the_sources():
    """The dark tokens live in base.html.j2 and the dark figure tokens in svg.css, each once for all selectors."""
    templates = REPORT / "templates"
    assert "#161a20" not in (templates / "full.html.j2").read_text(encoding="utf-8")
    assert (templates / "svg.css").read_text(encoding="utf-8").count("--g0:#4aa872") == 1
    assert "--on-e1:#10151c" not in (templates / "svg.css").read_text(encoding="utf-8")  # made from the list of names


def test_plate_tokens_are_not_a_second_copy_of_the_page_tokens():
    """The plate is the card, and the ink on it is the page ink: no --plate token remaps them."""
    for path in (REPORT / "templates").iterdir():
        if path.suffix in {".css", ".j2", ".js"}:
            assert "--plate" not in path.read_text(encoding="utf-8"), path.name


def test_environment_escapes_and_is_strict():
    env = page.ENV
    assert env.autoescape is True
    assert env.undefined is jinja2.StrictUndefined
    assert str(env.from_string("{{ x }}").render(x="<b>")) == "&lt;b&gt;"
    with pytest.raises(jinja2.UndefinedError):
        env.from_string("{{ missing }}").render()


def test_figure_runtime_is_a_template_file_not_a_python_string():
    """The drawing runtime lives in templates/runtime.js and is inlined by base.html.j2 like page.css (same CSP)."""
    source = (REPORT / "templates" / "runtime.js").read_text(encoding="utf-8")
    assert "var KINDS={" in source and "window.TSFIG=" in source
    assert "var KINDS={" not in (REPORT / "page.py").read_text(encoding="utf-8")
    assert page.RUNTIME_JS == source
    markup = page.render("base.html.j2", title="t")
    assert f'<script id="fig-draw">{source}</script>' in markup and markup.count("window.TSFIG=") == 1


def test_render_uses_the_package_templates():
    markup = page.render("base.html.j2", title="T <x>")
    assert markup.startswith("<!doctype html>") and page.CSP_META in markup
    assert "<title>T &lt;x&gt;</title>" in markup and markup.count("--paper:") == 1


def test_dark_colours_only_when_a_page_opts_in():
    light = page.render("base.html.j2", title="t")
    assert "prefers-color-scheme:dark" not in light and '<meta name="color-scheme" content="light">' in light
    child = page.ENV.from_string('{% extends "base.html.j2" %}{% set dark = true %}{% block content %}x{% endblock %}')
    for markup in (child.render(title="t"), page.render("base.html.j2", title="t", dark=True)):
        assert "prefers-color-scheme:dark" in markup and '<meta name="color-scheme" content="light dark">' in markup
        assert markup.count("--paper:") == 2  # the light tokens once, the dark block once


# The pages that follow the system colour scheme (light and dark), and the stylesheet every page shares.
DARK_PAGES = ("comparison", "coverage", "dashboard", "functional", "gallery", "literature", "quality", "summary")
PAGE_CSS = (REPORT / "templates" / "page.css").read_text(encoding="utf-8")
HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")


@pytest.mark.parametrize("name", DARK_PAGES)
def test_dashboard_pages_follow_the_system_colour_scheme(name):
    text = (REPORT / "templates" / f"{name}.html.j2").read_text(encoding="utf-8")
    assert "{% set dark = true %}" in text


@pytest.mark.parametrize("name", DARK_PAGES)
def test_dashboard_pages_take_their_colours_from_the_tokens(name):
    """A colour written as a hex value in a page's own CSS stays the same in dark mode; the pages use tokens."""
    text = (REPORT / "templates" / f"{name}.html.j2").read_text(encoding="utf-8")
    css = re.search(r"{% block css %}(.*?){% endblock %}", text, re.S)
    assert not (css and HEX.findall(css.group(1)))


def test_shared_css_keeps_hex_colours_in_the_token_block():
    rules = re.sub(r"^:root\{[^}]*\}", "", PAGE_CSS, count=1, flags=re.M)
    assert HEX.findall(PAGE_CSS) and not HEX.findall(rules)


def test_frame_has_a_main_landmark_and_visible_focus():
    markup = page.render("base.html.j2", title="t")
    assert '<main id="main">' in markup and "</main>" in markup
    assert ":focus-visible{" in PAGE_CSS


def test_frame_respects_reduced_motion_and_print():
    assert "@media (prefers-reduced-motion:reduce)" in PAGE_CSS
    printed = PAGE_CSS[PAGE_CSS.index("@media print"):]
    assert "break-inside:avoid" in printed and ".dl" in printed


def test_frame_follows_the_figura_type_stacks():
    """The page sets text in the Figura `sans` stack and code in its `mono` stack (tokens.json of the Figura system)."""
    assert '--font:Arial,Helvetica,Arimo,"Liberation Sans","Nimbus Sans",sans-serif;' in PAGE_CSS
    mono = '"Courier New",Courier,Cousine,"Liberation Mono","Nimbus Mono PS","TeX Gyre Cursor",monospace'
    assert f"--mono:{mono};" in PAGE_CSS


def test_frame_has_no_shadows_gradients_or_free_radii():
    """Figura: no drop shadows, no gradients; frames square, callouts radius-callout, pills only for state tags."""
    assert not re.search(r"box-shadow:(?!none)", PAGE_CSS)
    assert not re.search(r"(?<!repeating-)linear-gradient|radial-gradient", PAGE_CSS)
    radii = set(re.findall(r"border-radius:([^;}]+)", PAGE_CSS))
    assert radii <= {"var(--radius-callout)", "var(--radius-pill)", "0", "50%"}, radii


def test_motion_is_one_script_every_page_loads_and_it_honours_reduced_motion():
    motion = (REPORT / "templates" / "motion.js").read_text(encoding="utf-8")
    assert "prefers-reduced-motion: reduce" in motion and "IntersectionObserver" in motion
    assert "beforeprint" in motion  # a printed page shows every mark at its final value
    assert "function reveal" not in motion and ".rv{" not in PAGE_CSS  # no fade-in: every block is there on load
    markup = page.render("base.html.j2", title="t")
    assert markup.index('<script id="tsb-motion">') < markup.index('<script id="fig-draw">')
    runtime = (REPORT / "templates" / "runtime.js").read_text(encoding="utf-8")
    assert "TSMOTION.finish()" in runtime  # Save SVG writes the final drawing, never a frame of the transition
    assert "@media print" in PAGE_CSS


def test_status_legend_items_name_their_status_for_the_emphasis():
    legend = page.ENV.from_string('{% from "_macros.html.j2" import legend_html %}{{ legend_html(["wrong"]) }}')
    markup = legend.render()
    assert '<span class="lg" role="listitem" data-k="wrong" tabindex="0">' in markup


def test_every_figure_class_shrinks_to_the_page_width():
    """The runtime figures (jfs) and the figures a page draws itself (ftd, qfig, litfig) never widen the page."""
    assert "figure .plot svg{max-width:100%" in PAGE_CSS


def test_dark_tokens_cover_the_surfaces_of_the_frame():
    dark = page.render("base.html.j2", title="t", dark=True)
    block = dark[dark.index("prefers-color-scheme:dark"):]
    for token in ("--paper:", "--ink:", "--surface:", "--card:", "--line:", "--ok-bg:", "--bad-bg:", "--warn-bg:"):
        assert token in block, token


# ------------------------------------------------------------------ content of the pages of the demo run set
ISO = re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:?\d{2})?")


class _Dump(html.parser.HTMLParser):
    """Visible text, JSON data blocks and links of a page; styles and scripts other than JSON are left out."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.text, self.data, self.links, self.stack = [], [], [], []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.stack.append((tag, a))
        for k in ("href", "src"):
            if a.get(k) and not a[k].startswith("data:"):
                self.links.append(a[k])

    def handle_endtag(self, tag):
        while self.stack:
            if self.stack.pop()[0] == tag:
                break

    def handle_data(self, data):
        tag, a = self.stack[-1] if self.stack else ("", {})
        if tag == "script":
            if a.get("type") == "application/json":
                self.data.append(json.loads(data))
            return
        if tag == "style":
            return
        text = " ".join(data.split())
        if text:
            self.text.append(text)


def page_content(path: pathlib.Path, root: str) -> dict:
    """The content of a page, with timestamps and the output root (`root`, as the pages name it) replaced by
    placeholders."""
    d = _Dump()
    d.feed(path.read_text(encoding="utf-8"))
    raw = json.dumps({"text": d.text, "data": d.data, "links": d.links})
    return json.loads(ISO.sub("<TIME>", raw.replace(root, "<ROOT>")))


PAGES = ("comparison", "coverage", "dashboard", "gallery", "literature")
DEMO_TITLE = "Demo run set (fake claude)"


def _site(cwd: pathlib.Path, root: str, runs: pathlib.Path) -> pathlib.Path:
    """The five run-set pages of tools/render_mock.sh, built in the same order from a copy of `runs` into
    `cwd/root/site/pages`. The pages name the runs relative to the working directory (`root/site/runs/...`)."""
    site = cwd / root / "site"
    shutil.copytree(runs, site / "runs")
    (site / "pages").mkdir()
    mp = pytest.MonkeyPatch()
    mp.setenv("SOURCE_DATE_EPOCH", "0")
    mp.chdir(cwd)
    try:
        for name, mod, extra in (("dashboard", dashboard, ["--title", DEMO_TITLE]), ("comparison", comparison, []),
                                 ("gallery", gallery, []), ("literature", literature, []),
                                 ("coverage", coverage, [])):
            assert not mod.main(["--runs", f"{root}/site/runs", "--out", f"{root}/site/pages/{name}.html", *extra])
    finally:
        mp.undo()
    return site


@pytest.fixture(scope="module")
def demo_sites(tmp_path_factory, demo_runs_root):
    """The pages of the demo run set, built twice under two folder names. The first build draws the per-run figures
    beside its copy of the runs; the second starts from a copy of those runs, so it does not draw them again."""
    cwd = tmp_path_factory.mktemp("cwd")
    first = _site(cwd, "first-root", demo_runs_root)
    second = _site(cwd, "second-root", first / "runs")
    return {"first-root": first / "pages", "second-root": second / "pages"}


def test_each_page_has_the_same_content_when_built_again_elsewhere(demo_sites):
    for name in PAGES:
        first, second = (page_content(pages / f"{name}.html", root) for root, pages in demo_sites.items())
        for part in ("text", "data", "links"):
            assert first[part] == second[part], f"{name}: {part} differs between two builds"


def test_each_page_of_the_demo_run_set_names_its_models_and_tasks(demo_sites):
    for name in PAGES:
        content = page_content(demo_sites["first-root"] / f"{name}.html", "first-root")
        assert content["text"], name
        assert "claude-sonnet-5-5" in json.dumps(content), name
        assert re.search(r"\bP-[a-z_]+-\d\d\b", json.dumps(content)), name
    assert DEMO_TITLE in " ".join(page_content(demo_sites["first-root"] / "dashboard.html", "first-root")["text"])
