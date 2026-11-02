"""Helpers shared by the SVG tests of the report: XML readers and the text-box check behind `assert_fits`.

The width of a text is estimated from the advance widths of Arial (1000 units per em, the table below; Liberation
Sans has the same ones), so the check does not depend on a font being installed. Regular and bold differ.
"""
from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass

NS = "{http://www.w3.org/2000/svg}"
BODY_PX = 12.5  # svg.css: the size of the lettering when a text names no font-size

# Advance widths of the ASCII characters 32 .. 126.
_REGULAR = (
    278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278, 556, 556, 556, 556, 556, 556,
    556, 556, 556, 556, 278, 278, 584, 584, 584, 556, 1015, 667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667,
    556, 833, 722, 778, 667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 278, 278, 278, 469, 556, 333, 556,
    556, 500, 556, 556, 278, 556, 556, 222, 222, 500, 222, 833, 556, 556, 556, 556, 333, 500, 278, 556, 500, 722,
    500, 500, 500, 334, 260, 334, 584
)

_BOLD = (
    278, 333, 474, 556, 556, 889, 722, 238, 333, 333, 389, 584, 278, 333, 278, 278, 556, 556, 556, 556, 556, 556,
    556, 556, 556, 556, 333, 333, 584, 584, 584, 611, 975, 722, 722, 722, 722, 667, 611, 778, 722, 278, 556, 722,
    611, 833, 722, 778, 667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 333, 278, 333, 584, 556, 333, 556,
    611, 556, 611, 556, 333, 611, 611, 278, 278, 556, 278, 889, 611, 611, 611, 611, 389, 556, 333, 611, 556, 778,
    556, 556, 500, 389, 280, 389, 584
)

# The same in both weights.
_OTHER = {
    '\u00a0': 278, '\u2009': 200, '\u202f': 139, '·': 278, '−': 584, '±': 549, '…': 1000, '×': 584, '÷': 584,
    '–': 556, '—': 1000, '°': 400, '≈': 549, '≤': 549, '≥': 549, '→': 1000, '←': 1000, '•': 350,
}
_UNKNOWN = 600  # a character that is in neither table: wide, so an estimate errs towards a collision

ASCENT, DESCENT = 0.72, 0.21  # the box of a line of text above and below its baseline, in em
OVERLAP_PX = 1.0  # two boxes must overlap by more than this in both directions to count as a collision
EDGE_PX = 0.5  # a box may stick out of the figure by this much


# ---------------------------------------------------------------- readers of a parsed figure


def root(svg: str) -> ET.Element:
    return ET.fromstring(svg)


def tip(el: ET.Element) -> str:
    """The text of the <title> child of `el`, or "" when it has none."""
    t = el.find(f"{NS}title")
    return "" if t is None else str(t.text or "")


def classes(el: ET.Element) -> list[str]:
    return str(el.get("class") or "").split()


def attr_or_zero(el: ET.Element, name: str) -> float:
    """A numeric attribute; 0 when it is absent."""
    return float(el.get(name) or 0)


def attr_float(el: ET.Element, name: str) -> float:
    """A numeric attribute that must be there."""
    v = el.get(name)
    assert v is not None, name
    return float(v)


def match(pattern: str, text: str) -> re.Match[str]:
    """`re.search` that fails the test with the text when nothing matches."""
    m = re.search(pattern, text)
    assert m is not None, text
    return m


def texts(svg: str) -> list[str]:
    """The text of every <text> node of the figure in document order."""
    return [t.text or "" for t in root(svg).iter(f"{NS}text")]


# ---------------------------------------------------------------- text boxes

Matrix = tuple[float, float, float, float, float, float]  # SVG matrix(a b c d e f)
IDENTITY: Matrix = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def _mul(m: Matrix, n: Matrix) -> Matrix:
    """The matrix that applies `n` first and then `m`."""
    a, b, c, d, e, f = m
    p, q, r, s, t, u = n
    return (a * p + c * q, b * p + d * q, a * r + c * s, b * r + d * s, a * t + c * u + e, b * t + d * u + f)


def transform_matrix(spec: str | None) -> Matrix:
    """The matrix of an SVG transform list: translate, scale, rotate and matrix."""
    m = IDENTITY
    for name, args in re.findall(r"(\w+)\s*\(([^)]*)\)", spec or ""):
        v = [float(x) for x in re.split(r"[\s,]+", args.strip()) if x]
        if name == "translate":
            n: Matrix = (1.0, 0.0, 0.0, 1.0, v[0], v[1] if len(v) > 1 else 0.0)
        elif name == "scale":
            n = (v[0], 0.0, 0.0, v[-1], 0.0, 0.0)
        elif name == "rotate":
            c, s = math.cos(math.radians(v[0])), math.sin(math.radians(v[0]))
            n = (c, s, -s, c, 0.0, 0.0)
            if len(v) == 3:
                n = _mul(_mul((1.0, 0.0, 0.0, 1.0, v[1], v[2]), n), (1.0, 0.0, 0.0, 1.0, -v[1], -v[2]))
        elif name == "matrix":
            n = (v[0], v[1], v[2], v[3], v[4], v[5])
        else:
            raise AssertionError(f"transform {name!r} is not read by the figure check")
        m = _mul(m, n)
    return m


def text_width(s: str, size: float, bold: bool = False) -> float:
    """The estimated advance width of `s` in px at font size `size`."""
    table = _BOLD if bold else _REGULAR
    return size / 1000 * sum(table[ord(ch) - 32] if " " <= ch <= "~" else _OTHER.get(ch, _UNKNOWN) for ch in s)


@dataclass(frozen=True)
class TextBox:
    """The box a text covers, as four corners in the figure's own coordinates (it may be turned)."""

    label: str
    corners: tuple[tuple[float, float], ...]

    @property
    def xs(self) -> list[float]:
        return [p[0] for p in self.corners]

    @property
    def width(self) -> float:
        """The length of the text along its baseline."""
        (x0, y0), (x1, y1) = self.corners[0], self.corners[1]
        return math.hypot(x1 - x0, y1 - y0)

    @property
    def centre(self) -> tuple[float, float]:
        return sum(p[0] for p in self.corners) / 4, sum(p[1] for p in self.corners) / 4


def _box(t: ET.Element, matrix: Matrix) -> TextBox | None:
    label = "".join(t.itertext())
    if not label.strip():
        return None
    m = _mul(matrix, transform_matrix(t.get("transform")))
    size = float((t.get("font-size") or str(BODY_PX)).removesuffix("px"))
    w = text_width(label, size, "b" in classes(t))
    x, y = attr_or_zero(t, "x"), attr_or_zero(t, "y")
    left = {"middle": x - w / 2, "end": x - w}.get(t.get("text-anchor") or "start", x)
    if t.get("dominant-baseline") in ("central", "middle"):
        top, bottom = y - (ASCENT + DESCENT) * size / 2, y + (ASCENT + DESCENT) * size / 2
    else:
        top, bottom = y - ASCENT * size, y + DESCENT * size
    a, b, c, d, e, f = m
    pts = ((left, top), (left + w, top), (left + w, bottom), (left, bottom))
    return TextBox(label, tuple((a * px + c * py + e, b * px + d * py + f) for px, py in pts))


def text_boxes(el: ET.Element, matrix: Matrix = IDENTITY) -> list[TextBox]:
    """The box of every non-empty <text> below `el`, with the transforms of its groups applied."""
    out: list[TextBox] = []
    for child in el:
        if child.tag == f"{NS}text":
            if (box := _box(child, matrix)) is not None:
                out.append(box)
        else:
            out.extend(text_boxes(child, _mul(matrix, transform_matrix(child.get("transform")))))
    return out


def overlap_depth(p: TextBox, q: TextBox) -> float:
    """How far two boxes sink into each other (the smallest overlap over the edge directions); <= 0 when apart."""
    depth = math.inf
    for box in (p, q):
        for i in range(4):
            (x0, y0), (x1, y1) = box.corners[i], box.corners[(i + 1) % 4]
            n = math.hypot(x1 - x0, y1 - y0) or 1.0
            ax, ay = (y0 - y1) / n, (x1 - x0) / n
            pa = [ax * px + ay * py for px, py in p.corners]
            pb = [ax * px + ay * py for px, py in q.corners]
            depth = min(depth, min(max(pa), max(pb)) - max(min(pa), min(pb)))
    return depth


def assert_text_boxes_fit(svg_root: ET.Element, width: float) -> None:
    """Every text lies inside [0, width] and no two texts overlap."""
    boxes = text_boxes(svg_root)
    for b in boxes:
        lo, hi = min(b.xs), max(b.xs)
        assert -EDGE_PX <= lo and hi <= width + EDGE_PX, f"text outside the figure: {b.label!r} at {lo:.1f} .. {hi:.1f}"
    for i, p in enumerate(boxes):
        for q in boxes[i + 1:]:
            assert overlap_depth(p, q) <= OVERLAP_PX, f"texts overlap: {p.label!r} and {q.label!r}"
