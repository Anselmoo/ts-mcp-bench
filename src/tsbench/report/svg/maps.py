"""Result map: every run of the benchmark as one tile, nested by condition and class, coloured by outcome.

`run_map` is a treemap of the runs, nested condition > class > task, tile area = a measured value of the run (cost,
tokens, time) and tile colour = outcome. Pure: plain data in, one SVG string out, no randomness.

Outcome colours: the first category of `categories` (correct) is `ok`, the others their error class `e1` .. `e8`
(`base.error_classes`).
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from . import base
from .treemap import equalise

__all__ = ["run_map"]

_CAP = 3.0  # height of the condition cap on a strip


def _category_classes(categories: Sequence[tuple[str, str]]) -> dict[str, str]:
    """The fill class of each category key: the first (correct) is `ok`, the others their error class."""
    errors = base.error_classes(k for k, _ in categories[1:])
    return {k: "ok" if i == 0 else errors[k] for i, (k, _) in enumerate(categories)}


# ---------------------------------------------------------------- run map


@dataclass
class _Node:
    key: str
    value: float
    depth: int
    kids: list[_Node] = field(default_factory=list)
    run: dict | None = None


_Rect = tuple[float, float, float, float]
# (header, padding) of the containers by depth: the condition (1) and the class (2); the root (0) has none.
_SPECS = {0: (0.0, 0.0), 1: (20.0, 1.0), 2: (13.0, 1.0)}


def _lay(node: _Node, rect: _Rect) -> tuple[list[tuple[_Node, _Rect]], list[tuple[_Node, _Rect]]]:
    """Leaves and containers of `node` laid out in `rect`; the leaf area is proportional to the value."""
    if not node.kids:
        return [(node, rect)], []
    x, y, w, h = rect
    head, pad = _SPECS[node.depth]
    box = (x + pad, y + head, max(w - 2 * pad, 0.0), max(h - head - pad, 0.0))
    kids = sorted(node.kids, key=lambda k: (-k.value, k.key))

    def area(i: int, cell: _Rect) -> float:
        return sum(r[2] * r[3] for _, r in _lay(kids[i], cell)[0])

    cells = equalise([k.value for k in kids], box, area)
    leaves: list[tuple[_Node, _Rect]] = []
    boxes: list[tuple[_Node, _Rect]] = [] if node.depth == 0 else [(node, rect)]
    for k, cell in zip(kids, cells, strict=True):
        lv, bx = _lay(k, cell)
        leaves += lv
        boxes += bx
    return leaves, boxes


def _build(runs: Sequence[dict]) -> _Node:
    root = _Node("", 0.0, 0)
    conds: dict[str, _Node] = {}
    classes: dict[tuple[str, str], _Node] = {}
    for r in runs:
        cond, cls = str(r["cond"]), str(r["class"])
        cn = conds.get(cond)
        if cn is None:
            cn = conds[cond] = _Node(cond, 0.0, 1)
            root.kids.append(cn)
        kn = classes.get((cond, cls))
        if kn is None:
            kn = classes[(cond, cls)] = _Node(cls, 0.0, 2)
            cn.kids.append(kn)
        kn.kids.append(_Node(str(r["task"]), float(r["value"]), 3, run=r))
        kn.value += float(r["value"])
        cn.value += float(r["value"])
        root.value += float(r["value"])
    return root


def run_map(runs: Sequence[dict], categories: Sequence[tuple[str, str]], unit: str, nd: int = 2, *,
            width: float = base.FULL_W) -> str:
    """Treemap of runs nested condition > class > task; tile area = value, tile colour = outcome.

    runs: `[{"cond": "A", "class": "closed_form", "task": "P-closed_form-01", "value": 0.034, "outcome": key}]`;
    `value` is a measured number of the run in `unit` (cost in USD, output tokens, seconds); a run with a value of
    zero or less has no area and is counted in the note under the figure. categories: `[(key, label)]`, the first is
    "correct" (class `ok`), the others take `e1` .. `e8` by kind. `nd` is the
    number of decimals printed. Each condition has a header with its total and the part of it spent on correct runs.
    Empty input returns ""."""
    if not runs or not categories:
        return ""
    drawn = [r for r in runs if float(r["value"]) > 0]
    if not drawn:
        return ""
    cls_of = _category_classes(categories)
    label_of = dict(categories)
    correct_key = categories[0][0]
    w_total = float(width)
    h_total = 520.0 if w_total >= 900 else 440.0
    root = _build(drawn)
    leaves, boxes = _lay(root, (0.0, 0.0, w_total, h_total))
    tiles: list[str] = []
    for node, (x, y, w, h) in leaves:
        run = node.run or {}
        key = run.get("outcome")
        label = label_of.get(key, "no outcome")
        tip = f"{node.key} · {run.get('cond')}: {label} · {base.number(node.value, nd)} {unit}"
        tiles.append(base.rect(x, y, w, h, f"tile {cls_of.get(key, 'na')}", tip))
    frames: list[str] = []  # drawn after the tiles so the borders of the conditions and classes stay visible
    for node, (x, y, w, h) in boxes:
        count = len(_iter_leaves(node))
        if node.depth == 1:
            right = [n.run for n in _iter_leaves(node) if n.run is not None and n.run["outcome"] == correct_key]
            spent = sum(float(r["value"]) for r in right)
            tip = (f"{node.key}: {base.plural(count, 'run')} · {base.number(node.value, nd)} {unit} · "
                   f"{base.number(spent, nd)} {unit} on {base.plural(len(right), 'correct run')}")
            frames += [base.rect(x, y, w, h, "frame", tip), base.rect(x, y, w, _CAP + 1, f"c-{node.key}")]
            total, on_ok = base.number(node.value, nd), base.number(spent, nd)
            variants = [f"{node.key} · {total} {unit} · {on_ok} on correct ({base.number(100 * spent / node.value)} %)",
                        f"{node.key} · {total} {unit} · {on_ok} on correct", f"{node.key} · {total} {unit}", node.key]
            fit = next((v for v in variants if base.text_width(v) + 8 <= w), "")
            if fit:
                frames.append(base.text(x + 4, y + _CAP + 1 + base.TEXT_PX, fit, "start", "b"))
        else:
            tip = f"{node.key}: {base.plural(count, 'run')} · {base.number(node.value, nd)} {unit}"
            frames.append(base.rect(x, y, w, h, "frame", tip))
            name = base.fit(node.key, w - 8, base.SMALL_PX, blank=True)
            if name and h > _SPECS[2][0]:
                frames.append(base.text(x + 3, y + base.SMALL_PX, name, "start", "mut", size=base.SMALL_PX))
    out = tiles + frames
    leg, y = base.legend_rows([(cls_of[k], lab) for k, lab in categories], w_total, 0, h_total + 8 + base.TEXT_PX)
    skipped = len(runs) - len(drawn)
    parts = [base.plural(len(drawn), "run"), f"{base.number(root.value, nd)} {unit}",
             f"tile area proportional to {unit}"]
    if skipped:
        parts.append(f"{base.plural(skipped, 'run')} without a value, not drawn")
    lines = _note_lines(parts, w_total)
    out += [leg] + [base.text(0, y + 4 + i * (base.TEXT_PX + 2), ln, "start", "mut") for i, ln in enumerate(lines)]
    return base.figure(w_total, y + 12 + (len(lines) - 1) * (base.TEXT_PX + 2),
                       f"{unit} of every run by condition, class and task, colour = outcome", out)


def _note_lines(parts: Sequence[str], width: float) -> list[str]:
    """The parts joined by " · " into lines no wider than `width` pixels."""
    lines: list[str] = []
    for part in parts:
        if lines and base.text_width(f"{lines[-1]} · {part}") <= width:
            lines[-1] += f" · {part}"
        else:
            lines.append(part)
    return lines


def _iter_leaves(node: _Node) -> list[_Node]:
    return [node] if not node.kids else [lf for k in node.kids for lf in _iter_leaves(k)]
