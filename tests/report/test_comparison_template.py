"""The comparison page is templates/comparison.html.j2: the module builds a context of plain data, the template writes
every tag and escapes every value."""
from __future__ import annotations

import re

import markupsafe
from test_comparison import data_of, many, run  # the helpers of the page tests

from tsbench.report import comparison as cmp
from tsbench.report import page

TAG = re.compile(r"</?[a-zA-Z]")


def _strings(value):
    if isinstance(value, dict):
        for k, v in value.items():
            yield from _strings(k)
            yield from _strings(v)
    elif isinstance(value, (list, tuple)):
        for v in value:
            yield from _strings(v)
    elif isinstance(value, str):
        yield value


def _all_sections():
    runs = (many(3, 5, cond="C") + many(1, 4, cond="A") + many(2, 4, cond="B")
            + [run(cond="C", outcome="na429"),
               run(model="gemma", cond="C", set_="open")])
    return data_of(runs, planned={("first", "claude-haiku-5-5", "C"): 12})


def test_context_is_plain_data_without_markup():
    ctx = cmp.context(_all_sections())
    assert ctx["title"] == "TS-MCP benchmark: comparison"
    found = [s for s in _strings(ctx) if TAG.search(s) or isinstance(s, markupsafe.Markup)]
    assert not found, f"the context holds markup: {found[:3]}"


def test_page_is_the_template_filled_with_the_context():
    data = _all_sections()
    assert cmp.build_html(data) == page.render("comparison.html.j2", **cmp.context(data))


def test_user_text_is_escaped_by_the_template():
    evil = "<img src=x onerror=alert(1)>"
    runs = [run(model=f"m{evil}", cond="C", cls=evil, set_=evil, outcome="na429"),
            run(model=f"m{evil}", cond="C", cls=evil, set_=evil)]
    data = dict(data_of(runs), notes=[evil], run_sets=[{"name": evil, "title": evil}])
    page = cmp.build_html(data)
    assert "<img src=x" not in page and "&lt;img src=x" in page
