"""Circle packing of the text that tool calls returned to the model: condition > tool > run.

A leaf is one run's calls of one tool; its area is the number of characters of text those calls returned. Its colour is
the outcome of the run (`ok` correct, `bad` not correct). Each tool has a label outside the root circle, in a left or
right column, joined by a straight leader that crosses no other tool circle and no other leader. Tools whose calls
returned no text (image only) are not drawn; a note under the figure lists them.

The packing is the one of `pack.py` (a port of d3-hierarchy's `pack`), so the same input gives the same drawing.

`tool_rows` is the figure of several models: one line per model and tool on one axis.
"""
from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from . import base
from .pack import _absolute, _lcg, _Node, _pack_children

__all__ = ["tool_output", "tool_rows"]

_SIDE = 230.0  # room for the labels at each side of a full figure (the root circle then has a diameter of 500 px)
_SIDE_HALF = 120.0  # the same in a half figure
_TOP = 24.0
_PAD = 3.0  # padding between circles, in pixels
_RING = 16.0  # distance of the label anchors from the root circle
_MIN_COS = 0.35  # label anchors lie within about 70° of the horizontal
_LABEL_H = 28.0  # height of a two-line label
_STEP_DEG = 2
_MARGIN = 1.0  # clearance of a leader from a circle it passes


@dataclass
class _Tool:
    cond: str
    name: str
    node: _Node
    chars: int
    calls: int
    runs: int


def _kchars(n: int) -> str:
    """A count of characters: 845, 5.2k, 753k, 1.4M."""
    if n < 1000:
        return str(n)
    if n < 10_000:
        return f"{base.fixed(n / 1000, 1)}k"
    if base.round_half_up(n / 1000) < 1000:
        return f"{base.round_half_up(n / 1000)}k"
    return f"{base.fixed(n / 1_000_000, 1)}M"


def _seg_dist(px: float, py: float, seg: tuple[float, float, float, float]) -> float:
    x1, y1, x2, y2 = seg
    dx, dy = x2 - x1, y2 - y1
    t = 0.0 if dx == 0 and dy == 0 else max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


def _ccw(p: tuple[float, float], q: tuple[float, float], r: tuple[float, float]) -> float:
    return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])


def _cross(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> bool:
    p1, p2, p3, p4 = (a[0], a[1]), (a[2], a[3]), (b[0], b[1]), (b[2], b[3])
    return _ccw(p1, p2, p3) * _ccw(p1, p2, p4) < 0 and _ccw(p3, p4, p1) * _ccw(p3, p4, p2) < 0


def _sorted_tree(root: _Node) -> None:
    """Largest first, ties by name: the same order for the same input."""
    stack = [root]
    while stack:
        nd = stack.pop()
        nd.kids.sort(key=lambda k: (-k.value, k.name))
        stack.extend(nd.kids)


@dataclass
class _Label:
    tool: _Tool
    seg: tuple[float, float, float, float]
    qx: float
    qy: float
    left: bool


def _place_labels(tools: Sequence[_Tool], conds: Sequence[_Node], cx: float, cy: float, radius: float,
                  label_room: float) -> list[_Label]:
    """One label anchor on the ring outside the root circle per tool.

    The leader runs straight from the edge of the tool circle to the anchor. Among the anchors, the choice is the one
    that crosses the fewest other tool circles and leaders, then the fewest other condition circles, then lies closest
    to the direction of the tool seen from the centre. Labels of one side keep `_LABEL_H` apart and stay outside the
    root circle. Two orders are tried (fewest free directions first, biggest first), each followed by two passes in
    which every tool chooses again with all others in place; the arrangement with the fewest crossings is kept."""
    ring = radius + _RING
    phis = [math.radians(d) for d in range(0, 360, _STEP_DEG) if abs(math.cos(math.radians(d))) >= _MIN_COS]
    options: dict[int, list[tuple[float, float, _Label, bool]]] = {}  # per tool: (circle hits, other-cond hits, ...)
    for i, t in enumerate(tools):
        nd = t.node
        ideal = math.atan2(nd.ay - cy, nd.ax - cx) if math.hypot(nd.ax - cx, nd.ay - cy) > 1 else 0.0
        opts = []
        for phi in phis:
            qx, qy = cx + ring * math.cos(phi), cy + ring * math.sin(phi)
            d = math.hypot(qx - nd.ax, qy - nd.ay)
            seg = (nd.ax + (qx - nd.ax) / d * nd.ar, nd.ay + (qy - nd.ay) / d * nd.ar, qx, qy)
            hits = sum(1 for o in tools if o is not t and _seg_dist(o.node.ax, o.node.ay, seg) < o.node.ar + _MARGIN)
            other = sum(1 for cn in conds if cn.name != t.cond and _seg_dist(cn.ax, cn.ay, seg) < cn.ar + _MARGIN)
            dev = abs(math.atan2(math.sin(phi - ideal), math.cos(phi - ideal)))
            left = math.cos(phi) < 0
            sx = -1 if left else 1
            x_far = qx + sx * (5 + label_room)
            corners = [(qx + sx * 5, qy - 11), (qx + sx * 5, qy + 14), (x_far, qy - 11), (x_far, qy + 14)]
            room = all(math.hypot(px - cx, py - cy) > radius + 1 for px, py in corners)
            opts.append((hits + other * 0.01, dev, _Label(t, seg, qx, qy, left), room))
        options[i] = opts

    def choose(i: int, others: dict[int, _Label]) -> _Label:
        best_key, best, fallback = None, None, None
        for hits, dev, lab, room in options[i]:
            crossed = sum(1 for p in others.values() if _cross(p.seg, lab.seg))
            key = (hits + crossed, dev)
            if fallback is None or key < fallback[0]:
                fallback = (key, lab)
            apart = all(abs(p.qy - lab.qy) >= _LABEL_H for p in others.values() if p.left == lab.left)
            if room and apart and (best_key is None or key < best_key):
                best_key, best = key, lab
        if best is None:
            assert fallback is not None
            return fallback[1]
        return best

    def cost(placed: dict[int, _Label]) -> tuple[float, float]:
        hits = 0.0
        dev = 0.0
        for i, lab in placed.items():
            opt = next(o for o in options[i] if o[2] is lab)
            hits += opt[0] + sum(1 for j, p in placed.items() if j < i and _cross(p.seg, lab.seg))
            dev += opt[1]
        return hits, dev

    def arrange(order: list[int]) -> dict[int, _Label]:
        placed: dict[int, _Label] = {}
        for i in order:
            placed[i] = choose(i, placed)
        for _ in range(2):
            for i in order:
                placed[i] = choose(i, {j: p for j, p in placed.items() if j != i})
        for _ in range(3):  # pairs: move two tools together while a leader still crosses something
            before = cost(placed)
            if before[0] < 1:
                break
            for i in order:
                for j in order:
                    if i == j:
                        continue
                    trial = {k: p for k, p in placed.items() if k not in (i, j)}
                    trial[i] = choose(i, trial)
                    trial[j] = choose(j, trial)
                    if cost(trial) < cost(placed):
                        placed = trial
            if cost(placed) >= before:
                break
        return placed

    free = {i: sum(1 for hits, _, _, room in opts if hits < 1 and room) for i, opts in options.items()}
    names = [(t.cond, t.name) for t in tools]
    orders = [sorted(range(len(tools)), key=lambda i: (free[i], -tools[i].chars, names[i])),
              sorted(range(len(tools)), key=lambda i: (-tools[i].chars, names[i]))]
    best = min((arrange(o) for o in orders), key=cost)
    return [best[i] for i in range(len(tools))]


def tool_output(runs: Sequence[dict], *, width: float = base.FULL_W) -> str:
    """Circle packing condition > tool > run of the text that tool calls returned to the model.

    runs: `[{"cond": "C", "task": "P-numerical-02", "k": 1, "correct": True, "calls": [{"tool": "ts_fit_spectrum",
    "chars": 1234}]}]`, one entry per run (`k` is the repetition, 1 when absent); `calls` has one entry per tool call
    with the number of characters of text it returned (0 for an image only). A leaf is one run's calls of one tool, its
    area is the sum of their characters; the runs of one task with k > 1 are separate leaves, named "task · k2" when the
    run set has more than one repetition.
    A tool whose calls all returned 0 characters is not drawn; the note under the figure lists it with its calls.
    Each tool has a two-line label "C · tool" / "753k chars · 184 calls" outside the root circle, and the same text as
    one tooltip. Conditions are ordered A, B, C. The figure is `width` px wide: the root circle fills what the two label
    columns leave. Returns "" when no call returned text."""
    calls_of: dict[tuple[str, str], int] = {}
    leaf: dict[tuple[str, str, str, int], list] = {}  # (cond, tool, task, k) -> chars, calls, correct
    many_k = len({int(r.get("k", 1)) for r in runs}) > 1
    for r in runs:
        cond, task, k = str(r["cond"]), str(r["task"]), int(r.get("k", 1))
        for c in r["calls"]:
            tool = str(c["tool"])
            calls_of[(cond, tool)] = calls_of.get((cond, tool), 0) + 1
            rec = leaf.setdefault((cond, tool, task, k), [0, 0, bool(r["correct"])])
            rec[0] += int(c["chars"])
            rec[1] += 1
    drawn_tools = {(cd, tl) for (cd, tl, _, _), rec in leaf.items() if rec[0] > 0}
    if not drawn_tools:
        return ""
    rank = {c: i for i, c in enumerate(base.CONDS)}
    root = _Node("")
    cond_nodes: list[_Node] = []
    tools: list[_Tool] = []
    for cond in sorted({cd for cd, _ in drawn_tools}, key=lambda c: (rank.get(c, len(rank)), c)):
        cn = _Node(cond)
        for tool in sorted(tl for cd, tl in drawn_tools if cd == cond):
            tn = _Node(tool)
            tn.kids = [_Node(f"{task} · k{k}" if many_k else task, rec[0])
                       for (cd, tl, task, k), rec in leaf.items() if cd == cond and tl == tool and rec[0] > 0]
            cn.kids.append(tn)
        cond_nodes.append(cn)
    root.kids = cond_nodes
    root.total()
    _sorted_tree(root)
    w = float(width)
    side = _SIDE if w >= base.FULL_W else _SIDE_HALF
    size = w - 2 * side  # diameter of the root circle
    _pack_children(root, 0.0, _lcg())
    k = root.c.r / (size / 2)
    _pack_children(root, _PAD * k, _lcg())
    cx, cy = w / 2, _TOP + size / 2
    _absolute(root, (size / 2) / root.c.r, cx, cy)
    for cn in root.kids:
        for tn in cn.kids:
            tools.append(_Tool(cn.name, tn.name, tn, tn.value, calls_of[(cn.name, tn.name)], len(tn.kids)))
    by_name = {(cd, tl, f"{task} · k{k}" if many_k else task): rec for (cd, tl, task, k), rec in leaf.items()}
    n_calls = sum(calls_of.values())
    n_runs = len({(cd, task, k) for (cd, _, task, k), rec in leaf.items() if rec[0] > 0})

    body: list[str] = [base.circle(cx, cy, size / 2, "grid", (
        f"{base.number(root.value)} characters returned in {base.plural(n_calls, 'call')}, "
        f"{base.plural(n_runs, 'run')}"))]
    for cn in root.kids:
        cond_calls = sum(v for (cd, _), v in calls_of.items() if cd == cn.name)
        cond_runs = len({(task, k) for (cd, _, task, k), rec in leaf.items() if cd == cn.name and rec[0] > 0})
        parts = [base.circle(cn.ax, cn.ay, cn.ar, "frame", (
            f"{cn.name}: {base.number(cn.value)} characters returned in {base.plural(cond_calls, 'call')}, "
            f"{base.plural(len(cn.kids), 'tool')}, {base.plural(cond_runs, 'run')}"))]
        for tn in cn.kids:
            tool = next(t for t in tools if t.node is tn)
            tp = [base.circle(tn.ax, tn.ay, tn.ar, "ax", (
                f"{cn.name} · {tn.name}: {base.number(tn.value)} characters returned in "
                f"{base.plural(tool.calls, 'call')}, {base.plural(tool.runs, 'run')}"))]
            for ln in tn.kids:
                rec = by_name[(cn.name, tn.name, ln.name)]
                tp.append(base.circle(ln.ax, ln.ay, ln.ar, "ok" if rec[2] else "bad", (
                    f"{cn.name} · {tn.name} · {ln.name}: {base.number(ln.value)} characters returned in "
                    f"{base.plural(rec[1], 'call')} · run {'correct' if rec[2] else 'not correct'}")))
            parts.append(base.group(tp))
        body.append(base.group(parts))

    label_room = side - _RING - 5
    for lab in _place_labels(tools, root.kids, cx, cy, size / 2, label_room):
        t = lab.tool
        full = f"{t.cond} · {t.name} · {base.plural(t.chars, 'char', shown=_kchars(t.chars))} · " \
               f"{base.plural(t.calls, 'call')}"
        stats = f"{base.plural(t.chars, 'char', shown=_kchars(t.chars))} · {base.plural(t.calls, 'call')}"
        x = lab.qx + (-5 if lab.left else 5)
        anchor = "end" if lab.left else "start"
        sx1, sy1, sx2, sy2 = lab.seg
        body.append(base.group([
            base.line(sx1, sy1, sx2, sy2, "ax"),
            base.text(x, lab.qy - 2, base.fit(f"{t.cond} · {t.name}", label_room, base.SMALL_PX), anchor, "",
                      base.SMALL_PX),
            base.text(x, lab.qy + 11, base.fit(stats, label_room, base.SMALL_PX), anchor, "mut",
                      base.SMALL_PX)], tip=full))

    ly = _TOP + size + 2 * _RING + 14
    leg, _ = base.legend([("ok", "run correct"), ("bad", "run not correct")], 8, ly)
    body.append(leg)
    area = "area = characters of text returned, per run and tool"
    if w >= base.FULL_W:
        body.append(base.text(w - 8, ly, area, "end", "mut"))
        h = ly + 8
    else:
        body.append(base.text(8, ly + 16, area, "start", "mut"))
        h = ly + 24
    image_only = sorted((cd, tl) for (cd, tl) in calls_of if (cd, tl) not in drawn_tools)
    if image_only:
        note = "No text returned, not drawn: " + ", ".join(
            f"{cd} {tl} ({base.plural(calls_of[(cd, tl)], 'call')})" for cd, tl in image_only)
        for ln in base.wrap(note, w - 16, base.SMALL_PX):
            h += 15
            body.append(base.text(8, h, ln, "start", "mut", base.SMALL_PX))
        h += 4
    return base.figure(w, math.ceil(h), "Characters of text returned by tool calls, by condition, tool and run", body)


_ROW = 20.0  # one tool of one model
_BAR = 11.0
_ROWS_TOP = 22.0


def tool_rows(models: Sequence[tuple[str, Sequence[dict]]], *, width: float = base.FULL_W) -> str:
    """Characters of text the tools returned, one line per model and tool on one linear axis: a bar in the colour of the
    condition, then "753k chars · 184 calls". `models` `[(name, runs)]`, `runs` as for `tool_output`. Every model has
    the line of every tool that any model called; a tool it did not call says `no call`. Returns "" without a call."""
    totals: dict[tuple[str, str, str], list[int]] = {}
    for name, runs in models:
        for r in runs:
            for c in r["calls"]:
                rec = totals.setdefault((name, str(r["cond"]), str(c["tool"])), [0, 0])
                rec[0] += int(c["chars"])
                rec[1] += 1
    if not totals:
        return ""
    rank = {c: i for i, c in enumerate(base.CONDS)}
    tools = sorted({(cd, tl) for _, cd, tl in totals}, key=lambda t: (rank.get(t[0], len(rank)), t[1]))
    w = float(width)
    names = [n for n, _ in models]
    name_col = min(max(base.text_width(n) for n in names) + 12, w * 0.3)
    tool_col = max(base.text_width(f"{cd} · {tl}", base.SMALL_PX) for cd, tl in tools) + 12
    x0 = name_col + tool_col
    x1 = w - base.text_width("1.4M chars · 1000 calls", base.SMALL_PX) - 12
    peak = max(v[0] for v in totals.values()) or 1
    sx = base.Linear(0.0, float(peak), x0, x1)
    band = len(tools) * _ROW
    axis_y = _ROWS_TOP + len(names) * band
    out = [base.legend([(c, c) for c in base.CONDS if any(cd == c for cd, _ in tools)], x0, 14)[0],
           base.axis_bottom(sx, base.nice_ticks(0, peak, 5), axis_y, x0, x1, "characters of text returned",
                            lambda v: _kchars(int(v)), grid_to=_ROWS_TOP)]
    for i, name in enumerate(names):
        y0 = _ROWS_TOP + i * band
        if i:
            out.append(base.line(0, y0, w, y0, "grid"))
        out.append(base.text(0, y0 + band / 2 + base.TEXT_PX * 0.35, base.fit(name, name_col - 6), "start", "b"))
        for j, (cd, tl) in enumerate(tools):
            cy = y0 + (j + 0.5) * _ROW
            ty = cy + base.SMALL_PX * 0.35
            out.append(base.text(name_col, ty, f"{cd} · {tl}", "start", "", base.SMALL_PX))
            rec = totals.get((name, cd, tl))
            if rec is None:
                out.append(base.text(x0 + 4, ty, "no call", "start", "mut", base.SMALL_PX))
                continue
            stats = f"{base.plural(rec[0], 'char', shown=_kchars(rec[0]))} · {base.plural(rec[1], 'call')}"
            tip = f"{name} · {cd} · {tl}: {base.number(rec[0])} characters returned in {base.plural(rec[1], 'call')}"
            out.append(base.rect(x0, cy - _BAR / 2, sx(rec[0]) - x0, _BAR, f"c-{cd}", tip))
            out.append(base.text(sx(rec[0]) + 6, ty, stats, "start", "mut", base.SMALL_PX))
    return base.figure(w, axis_y + 12 + 2 * base.TEXT_PX + 8, "Characters of text returned per model and tool", out)
