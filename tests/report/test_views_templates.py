"""The per-run views, their index and the overview are built from templates (templates/views*.html.j2).

views.py keeps the data logic. The templates share one frame, opt into the dark colours of the base page and never
mark user text as safe."""
from __future__ import annotations

import ast
import pathlib
import re

from markupsafe import Markup

from tsbench import report
from tsbench.report import page, views

REPO = pathlib.Path(__file__).resolve().parents[2]
TEMPLATES = REPO / "src" / "tsbench" / "report" / "templates"
TAG = re.compile(r"<(div|style|table|html|section|pre|figure|figcaption|img|span|strong|tr|td|th|h1|h2|p|a|script|main)"
                 r"\b")

HAIKU = "claude-haiku-5-5"
EVIL = "<script>alert('x')</script><img src=x onerror=alert(1)>"


def _views_templates() -> list[pathlib.Path]:
    return sorted(TEMPLATES.glob("views*.html.j2"))


def test_views_py_holds_no_page_markup():
    tree = ast.parse((REPO / "src" / "tsbench" / "report" / "views.py").read_text(encoding="utf-8"))
    docstrings = {id(n.body[0].value) for n in ast.walk(tree)
                  if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef)) and n.body
                  and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant)}
    found = sorted({m.group(0) for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)
                    and id(n) not in docstrings for m in TAG.finditer(n.value)})
    assert not found, f"views.py writes page markup itself: {found}"


def test_the_templates_exist_and_share_one_frame():
    names = {p.name for p in _views_templates()}
    assert {"views_page.html.j2", "views.html.j2", "views_index.html.j2", "views_overview.html.j2",
            "views_macros.html.j2"} <= names
    frame = (TEMPLATES / "views_page.html.j2").read_text(encoding="utf-8")
    assert '{% extends "base.html.j2" %}' in frame and "{% set dark = true %}" in frame
    for name in ("views.html.j2", "views_index.html.j2", "views_overview.html.j2"):
        assert '{% extends "views_page.html.j2" %}' in (TEMPLATES / name).read_text(encoding="utf-8")


def test_user_text_is_never_marked_safe():
    for path in _views_templates():
        assert not re.search(r"\|\s*safe\b|\bMarkup\b", path.read_text(encoding="utf-8")), path.name


def test_images_html_escapes_the_name_and_returns_markup():
    imgs = [{"name": EVIL, "sha256": "ab" * 32, "sha_ok": False, "uri": "data:image/png;base64,AAAA"},
            {"name": "gone.png", "sha256": None, "sha_ok": False, "uri": None}]
    out = report.images_html(imgs, False, 320)
    assert isinstance(out, Markup) and "<script" not in out and "<img src=x" not in out
    assert "&lt;script&gt;" in out and "max-width:min(100%,320px)" in out
    assert "sha256 differs from the record" in out and "gone.png: not embedded" in out
    assert "does not match a harvested file" in out
    assert report.images_html([]) == ""


def test_views_keep_the_dark_block_of_the_base_page(tmp_path):
    index = views.render_index([], None, None, "pilot")
    overview = views.render_overview([], tmp_path)
    for markup in (index, overview):
        assert markup.count("--paper:") == 2 and '<meta name="color-scheme" content="light dark">' in markup
        assert page.CSP in markup and "<script id=" not in markup  # no Figura bundle on these pages
