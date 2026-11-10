"""Shared building blocks of the report pages: page frame, figures, status vocabulary, links.

Every page is one self-contained HTML file in the "Figura" design system (theme `neutral`): d3 7.9.0 and the Figura
bundle (`window.JFS`) are inlined from `src/tsbench/_vendor/figura/js/` (read as text, never imported), and a small
drawing runtime (`templates/runtime.js`, inlined like `page.css`) draws the figures from JSON specs. Every page carries
a Content-Security-Policy that allows no external resource at all (`CSP`). There are no pie or donut charts: shares are
dots with a 95 % task-clustered bootstrap interval and stacked horizontal bars; every status has an icon and a
text, never colour alone.

The pages are Jinja templates in `templates/`: `base.html.j2` is the frame of every page (`page.css` once, the CSP,
the Figura code), `_macros.html.j2` holds the shared parts, `render()` fills a template. The environment (`ENV`)
escapes every value and fails on an unknown name.

The status words of all pages and of `tsbench explain` live here (`STATUS`, `CATEGORY_TEXT`, `COND_NAMES`), so one
outcome has one name everywhere.
"""
from __future__ import annotations

import functools
import html
import json
import math
import os
import pathlib
import re
import typing
import urllib.parse
from collections.abc import Iterable, Sequence

import jinja2
from markupsafe import Markup

from tsbench.core import intervals
from tsbench.report.svg.base import fixed, plural, round_half_up

__all__ = ["CATEGORY_TEXT", "COND_LABEL", "COND_NAMES", "CSP", "ENV", "FLAG_TEXT", "MIN_SHARE_RUNS",
           "RUNTIME_JS", "SEG_KEYS", "STATUS", "STATUS_TEXT", "change_text", "color_ramp", "doi_href",
           "escape_html", "few_text", "figura_js", "find_js", "flag_notes", "href", "icon",
           "json_for_script", "local_links", "plural", "rate_row", "render", "run_flags", "share_interval", "signed",
           "task_pairs", "THEME"]

# the colours of the Figura theme `neutral` that the pages also use outside the figures
THEME = {
    "series-1": "#0039a6",
    "series-2": "#b07800",
    "series-3": "#b8336a",
    "series-4": "#2f8ac4",
    "series-5": "#008060",
    "series-6": "#8c2d19",
    "ink": "#1a1a1a",
    "ink-muted": "#4d4d4d",
    "rule": "#7a7a7a",
    "grid": "#d9d9d9",
    "house-deep": "#081b33",
    "house-tint": "#e6ebf6",
    "house-signal": "#3361b8",
    "paper": "#ffffff",
}

# Content-Security-Policy of every page: nothing may be loaded from anywhere; images only as data: URIs; inline CSS and
# inline scripts (the page's own drawing code) only.
CSP = "default-src 'none'; img-src data:; style-src 'unsafe-inline'; script-src 'unsafe-inline'; font-src data:"
CSP_META = f'<meta http-equiv="Content-Security-Policy" content="{CSP}">'

# The three conditions of the benchmark.
COND_NAMES = {"A": "no tools", "B": "code", "C": "TS-MCP"}
COND_LABEL = {c: f"{c} · {name}" for c, name in COND_NAMES.items()}

#   key: (text, icon). Colour is only an extra cue; icon and text carry the meaning.
STATUS = {
    "correct": ("correct", "check"), "wrong": ("wrong", "cross"), "harness": ("harness limit", "bang"),
    "na429": ("not evaluable: rate limit or API error", "pause"),
    "notrun": ("not run", "dash"), "unscored": ("not scored", "dash"),
}
STATUS_TEXT = {k: v[0] for k, v in STATUS.items()}
SEG_KEYS = ("correct", "wrong", "harness", "na429", "notrun")

# Failure categories of tsbench.score.taxonomy in plain words.
CATEGORY_TEXT = {
    "correct": "correct: every rule of the task class is met",
    "no_result": "no result: the run ended without a final result event",
    "max_turns": "harness limit: the allowed number of turns was used up",
    "budget": "harness limit: the cost budget of the run was used up",
    "context_overflow": "context overflow: the run's request outgrew the model's context window (a model failure)",
    "api_error": "API error (not a model error), e.g. a server error",
    "unparseable": "the answer could not be read as the required JSON",
    "false_refusal": "a solvable task was declined as out of scope",
    "missed_limit": "the task was out of scope, but numbers were given anyway",
    "gross_error": "gross error: relative deviation above 50 % (diagram: fewer than half of the values right)",
    "wrong_dq": "only Dq is outside the tolerance",
    "wrong_b": "only B is outside the tolerance",
    "wrong_c": "only C is outside the tolerance",
    "wrong_multiple": "two or more required parameters are outside the tolerance",
    "wrong_items": "items of a curve, batch, pairing or diagram answer are outside the tolerance",
}

# Flags of a run: a B run that ran no code, a C run that made no TS-MCP call. The runner records them in MANIFEST.json
# (flagged_runs); the pages read them from the score table (`run_flags`), so every run of every run set has them.
FLAG_TEXT = {"b_no_tool_use": "ran no code", "c_no_mcp_call": "made no TS-MCP call"}
# Tool use as a finding about the model: the prompt is the same in every condition, and whether a B run runs code or a C
# run calls the TS-MCP server is the model's choice.
TOOL_USED = {"b_no_tool_use": ("ran code", "code"), "c_no_mcp_call": ("called the TS-MCP server", "TS-MCP")}


def _count(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def run_flags(row: dict) -> list[str]:
    """The flags of one score row (scores.csv or tsbench.score.score): `b_no_tool_use` for a B run without any tool
    call, `c_no_mcp_call` for a C run without a TS-MCP call; [] when the score table has no counts."""
    cond = str(row.get("condition") or row.get("cond") or "")
    if cond == "B" and _count(row.get("n_tool_uses")) == 0:
        return ["b_no_tool_use"]
    if cond == "C" and _count(row.get("n_mcp_calls")) == 0:
        return ["c_no_mcp_call"]
    return []


def _n_correct(rows) -> int:
    return sum(r.get("outcome") == "correct" or str(r.get("correct")).strip().lower() in ("true", "1") for r in rows)


def flag_notes(rows: list[dict], key=lambda r: r.get("_flags") or []) -> list[dict]:
    """Per flag that occurs in `rows` (the runs of one rate) the tool use of the model: {flag, n, of, used, text,
    detail}. `detail` splits the share correct by tool use, so a reader sees what the rate is made of: "correct with
    code 0 of 7, without 9 of 43"."""
    out = []
    for flag, (verb, tool) in TOOL_USED.items():
        hit = [r for r in rows if flag in key(r)]
        if not hit:
            continue
        rest = [r for r in rows if flag not in key(r)]
        detail = f"correct with {tool} {_n_correct(rest)} of {len(rest)}, without {_n_correct(hit)} of {len(hit)}"
        out.append({"flag": flag, "n": len(hit), "of": len(rows), "used": len(rest),
                    "text": f"Tool use: {len(rest)} of {len(rows)} runs {verb}", "detail": detail})
    return out


def signed(x: float) -> str:
    """A difference in percentage points as '+12', '\u221216' (a true minus sign) or '0'."""
    r = round_half_up(x)
    return "0" if r == 0 else f"+{r}" if r > 0 else f"\u2212{-r}"


def change_text(c, other, what: str, fewer: str = "fewer") -> str | None:
    """C against another condition in one format on every page: 'N % fewer output tokens', 'N % more time',
    'about as many output tokens'; None when a value is missing or zero."""
    if not c or not other:
        return None
    change = 100.0 * (c - other) / other
    if abs(change) < 1:
        return f"about as much {what}" if fewer == "less" else f"about as many {what}"
    return f"{round_half_up(abs(change))} % {fewer if change < 0 else 'more'} {what}"


_ICONS = {
    "check": '<path d="M3 8.5l3.2 3.2L13 4.5"/>', "cross": '<path d="M4 4l8 8M12 4l-8 8"/>',
    "equals": '<path d="M3.5 6h9M3.5 10h9"/>', "bolt": '<path d="M9 1.5L3.5 9H8l-1 5.5L12.5 7H8z"/>',
    "warning": '<path d="M8 2l6.5 11.5h-13zM8 6.5v3M8 11.5v.2"/>', "bang": '<path d="M8 3v6.5M8 12.5v.2"/>',
    "pause": '<path d="M6 3.5v9M10 3.5v9"/>',
    "dash": '<path d="M4 8h8"/>',
}


def escape_html(value) -> str:
    """HTML-escape any value (None becomes the empty string); quotes too, so the result is safe in attributes."""
    return html.escape("" if value is None else str(value), quote=True)


def href(target, out_dir) -> str | None:
    """A link from a page in `out_dir` to `target`: relative, `/`-separated and quoted. None when no relative link
    exists (another drive): a page never carries a `file:` URI or an absolute path."""
    try:
        rel = pathlib.PurePath(os.path.relpath(target, out_dir)).as_posix()
    except ValueError:
        return None
    if rel.startswith("/") or ":" in rel.split("/", 1)[0]:
        return None
    return urllib.parse.quote(rel)


_SCRIPTED = re.compile(r"<(script|style)\b[^>]*>.*?</\1\s*>", re.S | re.I)
_LINK_ATTR = re.compile(r"""\s(?:xlink:)?(?:href|src)\s*=\s*(?:"([^"]*)"|'([^']*)')""", re.I)
_SELF_CONTAINED = ("#", "data:", "https:", "http:", "mailto:")


def local_links(markup: str) -> list[str]:
    """Every `src` and `href` of a page that points to a file beside it: what stops working when the page is copied on
    its own. An anchor, a data URI and a web address (http, https, mailto) stay valid; scripts and styles are not
    read."""
    found = (a or b for a, b in _LINK_ATTR.findall(_SCRIPTED.sub("", markup)))
    return sorted({f for f in found if not f.strip().lower().startswith(_SELF_CONTAINED)})


def svg(figure: str) -> Markup:
    """A figure of report/svg as Markup: the code built it and escaped every value in it."""
    return Markup(figure)


def icon(name: str, tone: str = "ink") -> Markup:
    return Markup(f'<svg class="ic t-{escape_html(tone)}" viewBox="0 0 16 16" aria-hidden="true" focusable="false">'
                  f"{_ICONS[name]}</svg>")


def color_ramp(p: float) -> tuple[str, str]:
    """(background, text colour) for p in [0, 1]: from the Figura tint (#e6ebf6) to the Figura blue (#0039a6)."""
    lo, hi = (0xE6, 0xEB, 0xF6), (0x00, 0x39, 0xA6)
    p = min(max(p, 0.0), 1.0)
    rgb = tuple(round(a + (b - a) * p) for a, b in zip(lo, hi, strict=False))
    lum = (0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]) / 255
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}", ("#ffffff" if lum < 0.5 else THEME["ink"])


MIN_SHARE_RUNS = 5  # below this many evaluable runs the 95 % interval spans more than half the axis


def task_pairs(runs: Iterable[tuple[str, bool]]) -> list[tuple[int, int]]:
    """(correct runs, evaluable runs) per task from (task id, correct) pairs, one pair per evaluable run, sorted by
    task id as `report.base.share` does: the bootstrap draws by position, so the same runs give the same interval on
    every page. The input of the task-clustered interval of `rate_row`."""
    acc: dict[str, list[int]] = {}
    for task, ok in runs:
        c = acc.setdefault(task, [0, 0])
        c[0] += bool(ok)
        c[1] += 1
    return [(c, n) for _, (c, n) in sorted(acc.items())]


def share_interval(tasks: Sequence[tuple[int, int]]) -> tuple[float, float] | None:
    """The 95 % interval of the share correct in percent: the task-clustered bootstrap (`core.intervals`), tasks
    resampled with their runs kept together. `tasks` holds (correct runs, evaluable runs) per task. None without
    runs."""
    tasks = [(c, n) for c, n in tasks if n > 0]
    if not tasks:
        return None
    lo, hi = intervals.cluster_bootstrap([c for c, _ in tasks], [n for _, n in tasks])
    return None if math.isnan(lo) or math.isnan(hi) else (100 * lo, 100 * hi)


def rate_row(label: str, cond: str, counts: dict, n_eval: int, n_total: int,
             tasks: Sequence[tuple[int, int]]) -> dict:
    """One row of the share chart (`rate`): share correct among the evaluable runs with its 95 % task-clustered
    bootstrap interval (`tasks`: (correct runs, evaluable runs) per task, see `task_pairs`), and the stacked counts per
    status (`counts`: keys from SEG_KEYS). Without evaluable runs p is None (no dot). With fewer than MIN_SHARE_RUNS
    evaluable runs `few` is true: the chart and the texts give counts only, no share."""
    c = counts.get("correct", 0)
    ci = share_interval(tasks) if n_eval else None
    p = 100.0 * c / n_eval if n_eval else None
    few = 0 < n_eval < MIN_SHARE_RUNS
    if p is None:
        tip = f"{label}: no evaluable runs"
    elif few or ci is None:
        tip = f"{label}: {c} of {n_eval} correct; {few_text(n_eval)}"
    else:
        tip = (f"{label}: {c} of {n_eval} correct ({round_half_up(p)} %), 95 % interval "
               f"{round_half_up(ci[0])} to {round_half_up(ci[1])} %, tasks resampled")
    return {"label": label, "cond": cond, "correct": c, "n_eval": n_eval, "total": n_total, "p": p, "few": few,
            "lo": ci[0] if ci else None, "hi": ci[1] if ci else None, "tip": tip,
            "seg": [[k, counts.get(k, 0), STATUS_TEXT[k]] for k in SEG_KEYS]}


def doi_href(doi: str) -> str:
    """The doi.org link of a DOI. A DOI may hold '#', '?', '%' or '<>' (the old SICI DOIs): they are percent-encoded so
    that the URL names the whole DOI, not a fragment or a query. Autoescape alone only escapes HTML."""
    return "https://doi.org/" + urllib.parse.quote(doi, safe="/()-._~:;")


def few_text(n_eval: int) -> str:
    """Why a row with fewer than MIN_SHARE_RUNS evaluable runs has no share."""
    return f"fewer than {MIN_SHARE_RUNS} evaluable runs, no share"


def json_for_script(obj) -> str:
    """JSON for a <script type="application/json">: <, > and & are written as \\u escapes."""
    s = json.dumps(obj, ensure_ascii=False, separators=(",", ":"), default=str)
    return s.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def find_js() -> tuple[pathlib.Path, pathlib.Path]:
    """(d3, bundle) of the vendored Figura design system in src/tsbench/_vendor/figura/js/."""
    vendor = pathlib.Path(__file__).resolve().parent.parent / "_vendor" / "figura" / "js"
    d3, bundle = vendor / "d3.min.js", vendor / "bundle.js"
    if d3.is_file() and bundle.is_file():
        return d3, bundle
    raise FileNotFoundError("Figura JS not found in src/tsbench/_vendor/figura/js/")


@functools.cache
def figura_js() -> Markup:
    """d3 7.9.0 and the Figura bundle as the text of one <script>; no </script> inside."""
    d3, bundle = find_js()
    src = "\n".join(p.read_text(encoding="utf-8") for p in (d3, bundle)).replace("</script", "<\\/script")
    return Markup(src)


def _script_json(obj) -> Markup:
    return Markup(json_for_script(obj))


# The template environment of every page: every value is escaped, an unknown name is an error. HTML that the code
# built itself reaches a template only as Markup: the constants below, a macro's output or render().
_LOADER = jinja2.PackageLoader("tsbench.report", "templates")
ENV = jinja2.Environment(loader=_LOADER, autoescape=True,
                         undefined=jinja2.StrictUndefined, trim_blocks=True, lstrip_blocks=True,
                         keep_trailing_newline=True)
typing.cast("dict[str, object]", ENV.globals).update(
    csp_meta=Markup(CSP_META), figura_js=figura_js, icon=icon, STATUS=STATUS,
    STATUS_TEXT=STATUS_TEXT, SEG_KEYS=SEG_KEYS, COND_NAMES=COND_NAMES, COND_LABEL=COND_LABEL, FLAG_TEXT=FLAG_TEXT,
    plural=plural, doi_href=doi_href)
ENV.filters["script_json"] = _script_json
ENV.filters["fixed"] = fixed  # "%.0f"|format would take a half to the even neighbour


# The drawing runtime of the "jfs" figures: templates/runtime.js, inlined by base.html.j2 as page.css is.
RUNTIME_JS = _LOADER.get_source(ENV, "runtime.js")[0]


def render(name: str, **ctx) -> str:
    """Fill the template `name` of templates/ with `ctx`; the result is Markup, so another template takes it as is."""
    return Markup(ENV.get_template(name).render(**ctx))
