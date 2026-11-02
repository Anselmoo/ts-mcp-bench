"""Shared helpers of the report figures: escaping, number format, scales, axes, legend, markers and the colour scale.

A figure is `figure(w, h, title, body)`: an <svg> of natural width `w` (CSS caps it at the text column), with a <title>
for screen readers. Elements carry classes, never colours: `c-A`, `c-B`, `c-C` fill with the colour of a condition,
`k-A`, `k-B`, `k-C` stroke with it, `g0` to `g4` fill with a step of the green–orange scale. templates/svg.css maps the
classes to the page tokens, so light and dark mode need no second drawing. Text is `TEXT_PX` pixels, as the body text.
"""
from __future__ import annotations

import html
import math
from collections.abc import Callable, Iterable, Sequence
from decimal import ROUND_HALF_UP, Context, Decimal

__all__ = ["CONDS", "ERROR_CLASSES", "FULL_W", "HALF_W", "SCORE_STEPS", "SMALL_PX", "TEXT_PX", "Linear",
           "Log", "axis_bottom", "axis_left", "circle", "coord", "diamond", "error_classes", "escape", "fit", "figure",
           "fixed", "group", "ink", "legend", "legend_rows", "line", "link", "marker", "module_name", "nice_ticks",
           "number", "path", "pct", "percent", "plural", "polar", "polygon", "rect", "round_half_up", "score_class",
           "score_legend", "signed_pp", "significant", "text", "text_width", "wrap"]

CONDS = ("A", "B", "C")
FULL_W = 960  # the width of a full figure: the content column
HALF_W = 464  # the width of a half figure: two halves and a 32 px gap fill the column
TEXT_PX = 12.5  # the size of the body text of the figure: labels, ticks, legend
SMALL_PX = 11  # dense labels only (a matrix header, a tile name)
GLYPH_EM = 0.56  # the mean advance of one character of the figure font (Arial and its metric twins), in em
_TICK_GAP = 3.0  # the least space between two tick labels of an axis, in px
# The five steps of coverage and mutation score, best first (classes g0 .. g4; svg.css gives each its colour).
# SCORE_STEPS are the lower bounds in percent: 95 and above is g0, 90 to 95 g1, 75 to 90 g2, 50 to 75 g3, below 50 g4.
# `score_class` and `score_legend` both read this one table.
SCORE_STEPS = (95.0, 90.0, 75.0, 50.0)


def escape(s) -> str:
    """Text for an SVG text node or attribute."""
    return html.escape(str(s), quote=True)


def coord(v: float) -> str:
    """A coordinate with at most two decimals."""
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


_WIDE = Context(prec=400)  # a float has at most 309 integer digits; the default 28 digits fail for 1e28 and above


def _half_up(x: float, nd: int = 0) -> Decimal:
    """`x` rounded to `nd` decimals, a half away from zero (2.5 is 3, -2.5 is -3), as an exact Decimal. Floating
    point noise below the ninth decimal is dropped first, so 100 * 0.145 = 14.499999999999998 counts as the 14.5 it
    stands for.
    Python's own round() and the format `.0f` take a half to the even neighbour, which prints equal halves in opposite
    directions (2.5 as 2 but 3.5 as 4)."""
    return Decimal(repr(round(float(x), 9))).quantize(Decimal(1).scaleb(-nd), rounding=ROUND_HALF_UP, context=_WIDE)


def round_half_up(x: float, nd: int = 0) -> int | float:
    """`x` rounded to `nd` decimals with a half away from zero: an int for `nd` 0, else a float. Every rounding of a
    number shown on a page goes through this (or through `number`), so equal halves print in the same direction."""
    if not math.isfinite(x):
        return float(x)  # inf and nan have no neighbour to round to
    d = _half_up(x, nd)
    return int(d) if nd == 0 else float(d)


def number(x: float | None, nd: int = 0, dash: str = "–") -> str:
    """A number with `nd` decimals, a thin space between thousands and the minus sign; None is `dash`."""
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return dash
    d = x if not math.isfinite(x) else _half_up(x, nd)
    s = f"{abs(d) if d == 0 else d:,.{nd}f}".replace(",", " ")
    return s.replace("-", "−")


def fixed(x: float, nd: int = 0, *, sign: bool = False) -> str:
    """`x` with `nd` decimals, a half away from zero, in plain form: no separator between thousands, an ASCII minus.
    For values that are not shown in a figure (a CSV-like text, a fixed-width label); a rounded zero has no sign. With
    `sign` a positive value carries "+"."""
    if not math.isfinite(x):
        return str(float(x))
    d = _half_up(x, nd)
    s = f"{abs(d) if d == 0 else d:.{nd}f}"
    return f"+{s}" if sign and d > 0 else s


def significant(x: float, n: int = 4) -> str:
    """`x` with `n` significant digits, a half away from zero, in the short form of `g` (no trailing zeros, an exponent
    for large and small values), a thin space between thousands and the minus sign. `f"{x:.4g}"` takes a half to the
    even neighbour (3466.5 as 3466 but 3467.5 as 3468)."""
    if not math.isfinite(x):
        return str(float(x))
    if x == 0:
        return "0"
    d = Decimal(repr(float(x)))
    q = d.quantize(Decimal(1).scaleb(d.adjusted() - n + 1), rounding=ROUND_HALF_UP, context=_WIDE)
    s = f"{abs(float(q)):,.{n}g}".replace(",", " ")  # q has at most n digits: the float format does not round it again
    return f"−{s}" if q < 0 else s


def signed_pp(v: float) -> str:
    """A fraction as signed whole percentage points: 0.62 is "+62", -0.02 is "\u22122", a rounded zero is "0"."""
    r = round_half_up(100 * v)
    return "0" if r == 0 else f"+{r}" if r > 0 else f"\u2212{-r}"


def pct(x: float | None, nd: int = 0) -> str:
    """A share in [0, 1] as a percentage with its unit: 0.2 is "20 %"."""
    return "–" if x is None else f"{number(100 * x, nd)} %"


def percent(p: float | None, none_label: str = "no value") -> str:
    """A value in percent with one decimal and its unit: 87.3 is "87.3 %"; None is `none_label`."""
    return none_label if p is None else f"{number(p, 1)} %"


def plural(n: int, word: str, words: str | None = None, *, shown: str | None = None) -> str:
    """The count with its noun in the right number: "1 run", "2 runs", "0 tasks", "3 families". `words` is an
    irregular plural ("classes"); `shown` is the text printed for the count when it is not `str(n)` (`number(n)`:
    "1 234 runs"). The report pages use this one function (`page.plural`)."""
    count = str(n) if shown is None else shown
    if n == 1:
        return f"{count} {word}"
    return f"{count} {words or (word[:-1] + 'ies' if word.endswith('y') else word + 's')}"


def text_width(s: str, px: float = TEXT_PX) -> float:
    """A rough width of `s` in pixels at the font size `px`: every figure sizes its text with this one estimate."""
    return len(s) * px * GLYPH_EM


def fit(s: str, room: float, px: float = TEXT_PX, *, blank: bool = False) -> str:
    """`s` cut with "…" to what fits in `room` pixels at `px`, at least four characters; with `blank` it is "" when
    fewer than four fit."""
    per = int(room / (px * GLYPH_EM))
    if not blank:
        per = max(per, 4)
    if len(s) <= per:
        return s
    return s[:per - 1] + "…" if per >= 4 else ""


def wrap(s: str, room: float, px: float = TEXT_PX, *, least: int = 8, split_words: bool = False) -> list[str]:
    """`s` broken at spaces into lines of at most `room` pixels at `px` (at least `least` characters a line). A word
    longer than a line stays whole, or is split at the line end with `split_words`."""
    per = max(int(room / (px * GLYPH_EM)), least)
    lines: list[str] = []
    cur = ""
    for word in s.split():
        while split_words and len(word) > per:
            if cur:
                lines.append(cur)
                cur = ""
            lines.append(word[:per])
            word = word[per:]
        if cur and len(cur) + 1 + len(word) > per:
            lines.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}".strip()
    return [*lines, cur] if cur else lines


def polar(cx: float, cy: float, r: float, a: float) -> tuple[float, float]:
    """The point at radius `r` and angle `a` (radians, 0 at twelve o'clock, clockwise) about (cx, cy)."""
    return cx + r * math.sin(a), cy - r * math.cos(a)


def module_name(module: str) -> str:
    """A module name without the leading `tsbench.`: "tsbench.score.numeric" is "score.numeric"."""
    return module.removeprefix("tsbench.")


# The fill classes of the error kinds (svg.css), one per kind of the report: report.facts.CATEGORIES after "correct",
# then OTHER and OVERFLOW. The first outcome category ("correct") is `ok`.
ERROR_CLASSES = ("e1", "e2", "e3", "e4", "e5", "e6", "e7", "e8")
_ERROR_OF = dict(zip(("gross", "several", "items", "dq", "bc", "limit", "other", "overflow"), ERROR_CLASSES,
                     strict=True))
_INKED = frozenset({"g0", "g1", "g2", "g3", "g4", "ok", "bad", "warn", "muted", *ERROR_CLASSES, "c-A", "c-B", "c-C"})


def error_classes(keys: Iterable[str]) -> dict[str, str]:
    """The fill class of each error kind in `keys`: a kind of the report keeps its own class whatever the others are;
    any other key takes the next class no kind uses. More kinds than classes raise ValueError (no colour is reused)."""
    keys = list(keys)
    out = {k: _ERROR_OF[k] for k in keys if k in _ERROR_OF}
    free = iter(c for c in ERROR_CLASSES if c not in out.values())
    for k in keys:
        if k not in out:
            try:
                out[k] = next(free)
            except StopIteration:
                raise ValueError(f"{len(keys)} error kinds, only {len(ERROR_CLASSES)} colours") from None
    return {k: out[k] for k in keys}


def ink(fill_cls: str) -> str:
    """The class of text printed on a tile of the fill class `fill_cls` (`g2`, `bad`, `c-A`): `on-g2` and so on, the
    ink that reaches 4.5 : 1 on that fill in both themes (svg.css). The fill classes without one give the page ink."""
    cls = fill_cls.split()[0] if fill_cls else ""
    return f"on-{cls.removeprefix('c-')}" if cls in _INKED else ""


def score_class(p: float | None) -> str:
    """The class of a coverage or mutation score in percent: g0 (best) to g4; `na` without a value."""
    if p is None:
        return "na"
    for i, lo in enumerate(SCORE_STEPS):
        if p >= lo:
            return f"g{i}"
    return "g4"


def score_legend() -> list[tuple[str, str]]:
    """The legend entries `(class, label)` of the five score steps, best first: ("g0", "95 % and above"),
    ("g1", "90 to 95 %") ... ("g4", "below 50 %"). They are written from `SCORE_STEPS`, as `score_class` is."""
    steps = [f"{lo:g}" for lo in SCORE_STEPS]
    labels = [f"{steps[0]} % and above", *(f"{lo} to {hi} %" for lo, hi in zip(steps[1:], steps, strict=False)),
              f"below {steps[-1]} %"]
    return [(f"g{i}", label) for i, label in enumerate(labels)]


# ---------------------------------------------------------------- scales


class Linear:
    """A linear map from the domain [d0, d1] to the range [r0, r1]."""

    def __init__(self, d0: float, d1: float, r0: float, r1: float):
        self.d0, self.d1, self.r0, self.r1 = d0, d1, r0, r1

    def __call__(self, v: float) -> float:
        if self.d1 == self.d0:
            return (self.r0 + self.r1) / 2
        return self.r0 + (v - self.d0) / (self.d1 - self.d0) * (self.r1 - self.r0)

    def ticks(self, n: int = 5) -> list[float]:
        return nice_ticks(self.d0, self.d1, n)


class Log:
    """A base-10 log map from [d0, d1] (both > 0) to [r0, r1]; values are clamped to the domain."""

    def __init__(self, d0: float, d1: float, r0: float, r1: float):
        self.d0, self.d1, self.r0, self.r1 = d0, d1, r0, r1

    def __call__(self, v: float) -> float:
        v = min(max(v, self.d0), self.d1)
        a, b = math.log10(self.d0), math.log10(self.d1)
        return self.r0 + (math.log10(v) - a) / (b - a) * (self.r1 - self.r0)

    def ticks(self, stride: int = 1) -> list[float]:
        """The powers of ten inside the domain, every `stride`-th one (from the first)."""
        lo, hi = math.ceil(math.log10(self.d0) - 1e-9), math.floor(math.log10(self.d1) + 1e-9)
        return [10.0 ** e for e in range(lo, hi + 1)][::max(stride, 1)]


def nice_ticks(a: float, b: float, n: int = 5) -> list[float]:
    """About `n` round tick values in [a, b] (steps of 1, 2 or 5 times a power of ten)."""
    if b < a:
        a, b = b, a
    if b == a:
        return [a]
    raw = (b - a) / max(n, 1)
    mag = 10 ** math.floor(math.log10(raw))
    step = next(m * mag for m in (1, 2, 5, 10) if m * mag >= raw)
    start = math.ceil(a / step - 1e-9) * step
    out, v = [], start
    while v <= b + step * 1e-9:
        out.append(round(v, 10))
        v += step
    return out


# ---------------------------------------------------------------- elements


def _attrs(cls: str = "", tip: str = "", **kw) -> tuple[str, str]:
    a = "".join(f' {k.rstrip("_").replace("_", "-")}="{coord(v) if isinstance(v, float) else escape(v)}"'
                for k, v in kw.items() if v is not None)
    if cls:
        a = f' class="{escape(cls)}"' + a
    return a, (f"<title>{escape(tip)}</title>" if tip else "")


def _el(tag: str, cls: str, tip: str, **kw) -> str:
    a, t = _attrs(cls, tip, **kw)
    return f"<{tag}{a}>{t}</{tag}>" if t else f"<{tag}{a}/>"


def _width_style(width: float | None) -> str | None:
    """The stroke width as an inline style. A presentation attribute loses against a class rule of svg.css
    (`.ax{stroke-width:1}`), an inline style does not."""
    return None if width is None else f"stroke-width:{coord(float(width))}"


def rect(x: float, y: float, w: float, h: float, cls: str = "", tip: str = "") -> str:
    return _el("rect", cls, tip, x=float(x), y=float(y), width=float(max(w, 0)), height=float(max(h, 0)))


def circle(x: float, y: float, r: float, cls: str = "", tip: str = "") -> str:
    return _el("circle", cls, tip, cx=float(x), cy=float(y), r=float(r))


def line(x1: float, y1: float, x2: float, y2: float, cls: str = "ax", tip: str = "", width: float | None = None,
         dash: str | None = None) -> str:
    """A line; `width` is its stroke width (written as a style), `dash` a stroke-dasharray such as "3 2"."""
    return _el("line", cls, tip, x1=float(x1), y1=float(y1), x2=float(x2), y2=float(y2),
               style=_width_style(width), stroke_dasharray=dash)


def path(d: str, cls: str = "", tip: str = "", width: float | None = None, dash: str | None = None) -> str:
    """A path; `width` is its stroke width (a flow link of n runs), `dash` a stroke-dasharray."""
    return _el("path", cls, tip, d=d, style=_width_style(width), stroke_dasharray=dash)


def polygon(points: Iterable[tuple[float, float]], cls: str = "", tip: str = "") -> str:
    return _el("polygon", cls, tip, points=" ".join(f"{coord(x)},{coord(y)}" for x, y in points))


def text(x: float, y: float, s, anchor: str = "start", cls: str = "", size: float | None = None,
         rotate: bool = False, baseline: str | None = None, angle: float = 0.0) -> str:
    """A text node; `cls` "mut" is the muted ink, "b" bold; `rotate` turns it by −90° about (x, y), `angle` by
    −`angle` degrees (a head set at 45°)."""
    turn = 90.0 if rotate else angle
    a, _ = _attrs(cls, "", x=float(x), y=float(y), text_anchor=None if anchor == "start" else anchor,
                  font_size=None if size is None else f"{coord(size)}px", dominant_baseline=baseline,
                  transform=f"rotate(-{coord(turn)} {coord(x)} {coord(y)})" if turn else None)
    return f"<text{a}>{escape(s)}</text>"


def group(body: Iterable[str] | str, cls: str = "", tip: str = "", transform: str = "") -> str:
    a, t = _attrs(cls, tip, transform=transform or None)
    return f"<g{a}>{t}{body if isinstance(body, str) else ''.join(body)}</g>"


def diamond(x: float, y: float, r: float, tip: str = "") -> str:
    """The mark of a paper value: a diamond in the ink colour, no condition."""
    return polygon([(x, y - r), (x + r, y), (x, y + r), (x - r, y)], "paper", tip)


def link(href: str, body: Iterable[str] | str) -> str:
    """`body` inside an <a> to `href`: a task mark or a task label that opens the row of its task. The link is no tab
    stop (`tabindex="-1"`): the Tasks and Systems tables hold the same link, and a figure of 100 marks would cost a
    keyboard user 100 stops without a name."""
    return f'<a href="{escape(href)}" tabindex="-1">{body if isinstance(body, str) else "".join(body)}</a>'


def marker(cond: str, x: float, y: float, filled: bool = True, r: float = 4.0, tip: str = "") -> str:
    """The mark of a condition: circle A, square B, triangle C; filled or open, in the colour of the condition."""
    cls = f"{'c' if filled else 'o'}-{cond} k-{cond}"
    if cond == "B":
        s = r * 0.9
        return rect(x - s, y - s, 2 * s, 2 * s, cls, tip)
    if cond == "C":
        h = r * 1.15
        return polygon([(x, y - h), (x + h, y + h * 0.8), (x - h, y + h * 0.8)], cls, tip)
    return circle(x, y, r, cls, tip)


def figure(w: float, h: float, title: str, body: Iterable[str] | str, cls: str = "") -> str:
    """The <svg> of one figure: natural width `w` (the CSS caps it at the column), a <title> for screen readers. A
    figure is `role="img"`; one that holds task links is `role="group"` with the same label."""
    inner = body if isinstance(body, str) else "".join(body)
    c = f"fig {cls}".strip()
    role = "group" if "<a " in inner else "img"  # the children of an image are presentational: no links in it
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {coord(w)} {coord(h)}" width="{coord(w)}"'
            f' height="{coord(h)}" class="{escape(c)}" role="{role}" aria-label="{escape(title)}">'
            f"<title>{escape(title)}</title>{inner}</svg>")


# ---------------------------------------------------------------- axes and legend


def axis_bottom(scale: Callable[[float], float], ticks: Iterable[float], y: float, x0: float, x1: float,
                label: str = "", fmt_tick: Callable[[float], str] = lambda v: number(v, 0), grid_to: float | None = None
                ) -> str:
    """A horizontal axis at `y` from x0 to x1: base line, ticks with labels below, an optional label under them;
    `grid_to` draws a light grid line from each tick up to that y. Every tick is drawn; a label closer than
    `_TICK_GAP` pixels to the last label drawn (left to right) is left out, and the first and the last label stay
    where they fit, so no figure needs its own tick density."""
    out = [line(x0, y, x1, y, "ax")]
    marks = sorted(((scale(v), fmt_tick(v)) for v in ticks), key=lambda m: m[0])
    last_left = marks[-1][0] - text_width(marks[-1][1]) / 2 if marks else math.inf
    right = -math.inf  # the right end of the last label drawn
    for i, (x, shown) in enumerate(marks):
        if grid_to is not None:
            out.append(line(x, grid_to, x, y, "grid"))
        out.append(line(x, y, x, y + 4, "ax"))
        half = text_width(shown) / 2
        # a label that would touch the last one drawn, or (but the last itself) the final label, is left out
        if x - half >= right + _TICK_GAP and (i == len(marks) - 1 or x + half + _TICK_GAP <= last_left):
            out.append(text(x, y + 4 + TEXT_PX, shown, "middle", "mut"))
            right = x + half
    if label:
        out.append(text((x0 + x1) / 2, y + 8 + 2 * TEXT_PX, label, "middle", "mut"))
    return "".join(out)


def axis_left(scale: Callable[[float], float], ticks: Iterable[float], x: float, y0: float, y1: float,
              label: str = "", fmt_tick: Callable[[float], str] = lambda v: number(v, 0), grid_to: float | None = None
              ) -> str:
    """A vertical axis at `x` from y0 to y1: base line, ticks with labels left of it, an optional rotated label;
    `grid_to` draws a light grid line from each tick right to that x."""
    out = [line(x, y0, x, y1, "ax")]
    for v in ticks:
        y = scale(v)
        if grid_to is not None:
            out.append(line(x, y, grid_to, y, "grid"))
        out.append(line(x - 4, y, x, y, "ax"))
        out.append(text(x - 7, y + TEXT_PX * 0.35, fmt_tick(v), "end", "mut"))
    if label:
        out.append(text(x - 10 - 3.2 * TEXT_PX, (y0 + y1) / 2, label, "middle", "mut", rotate=True))
    return "".join(out)


def legend(items: Sequence[tuple[str, str]], x: float, y: float, gap: float = 18.0) -> tuple[str, float]:
    """One row of legend entries `(kind, label)` from (x, y); returns the SVG and the x after the last entry.
    `kind` is a condition ("A", "B", "C": its marker), "open-A" etc. (the open marker), or a class name for a swatch
    (e.g. "g0", "ok", "bad"). "open" is the open mark in the neutral ink, "paper" the diamond of a paper value."""
    out, cx = [], x
    for kind, label in items:
        if kind in CONDS:
            out.append(marker(kind, cx + 5, y - TEXT_PX * 0.35, True))
        elif kind == "open":
            out.append(circle(cx + 5, y - TEXT_PX * 0.35, 4.0, "o-N k-N"))
        elif kind == "paper":
            out.append(diamond(cx + 5, y - TEXT_PX * 0.35, 4.5))
        elif kind.startswith("open-") and kind[5:] in CONDS:
            out.append(marker(kind[5:], cx + 5, y - TEXT_PX * 0.35, False))
        else:
            out.append(rect(cx, y - TEXT_PX * 0.8, 10, 10, kind))
        out.append(text(cx + 15, y, label))
        cx += 15 + text_width(label) + gap
    return "".join(out), cx


def legend_rows(items: Sequence[tuple[str, str]], width: float, x: float, y: float, pitch: float = 18.0
                ) -> tuple[str, float]:
    """The legend `items` wrapped into rows of at most `width` pixels from (x, y); returns the SVG and the y of the
    next free line."""
    rows: list[list[tuple[str, str]]] = [[]]
    used = 0.0
    for item in items:
        need = 15 + text_width(item[1]) + 18
        if rows[-1] and used + need > width:
            rows.append([])
            used = 0.0
        rows[-1].append(item)
        used += need
    return "".join(legend(row, x, y + i * pitch)[0] for i, row in enumerate(rows)), y + len(rows) * pitch
