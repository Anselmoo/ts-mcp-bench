"""Flow figures of the report: the sequences sunburst of call paths and the table rows of the same paths.

`sunburst` is static SVG built from counts: one ring per step (the condition, then call 1, call 2, and so on, then the
outcome); an arc is as wide as the runs that took the path up to it. The arcs carry no call names (the path table
holds them); the inner ring carries its condition letter. `path_rows` lists the most frequent complete paths for a
table, a run of one tool folded as `name ×n`.
"""
from __future__ import annotations

import itertools
import math
from collections import Counter
from collections.abc import Mapping, Sequence

from . import base

__all__ = ["path_rows", "sunburst"]

NO_CALL = "(no call)"
MORE = "…"
OUTCOMES = ("correct", "not correct")


def _share(n: int, total: int) -> str:
    x = 100 * n / total if total else 0.0
    return f"{base.number(x, 0 if x >= 10 else 1)} %"


# ---------------------------------------------------------------- sunburst


def _tree(paths: Sequence[Mapping], depth: int) -> dict:
    root: dict = {"name": "", "n": 0, "kids": {}}
    for p in paths:
        calls = [str(c) for c in p.get("calls", [])]
        chain = [str(p.get("cond", ""))] + calls[:depth] + ([MORE] if len(calls) > depth else [])
        chain.append(OUTCOMES[0] if p.get("correct") else OUTCOMES[1])
        cur = root
        cur["n"] += 1
        for name in chain:
            cur = cur["kids"].setdefault(name, {"name": name, "n": 0, "kids": {}})
            cur["n"] += 1
    return root


def _depth(node: dict) -> int:
    return 1 + max((_depth(k) for k in node["kids"].values()), default=0)


def _arc(cx: float, cy: float, a0: float, a1: float, r0: float, r1: float) -> str:
    a1 = min(a1, a0 + 2 * math.pi - 1e-3)
    large = 1 if a1 - a0 > math.pi else 0
    p0, p1 = base.polar(cx, cy, r1, a0), base.polar(cx, cy, r1, a1)
    q1, q0 = base.polar(cx, cy, r0, a1), base.polar(cx, cy, r0, a0)
    c = base.coord
    return (f"M{c(p0[0])},{c(p0[1])} A{c(r1)},{c(r1)} 0 {large} 1 {c(p1[0])},{c(p1[1])} "
            f"L{c(q1[0])},{c(q1[1])} A{c(r0)},{c(r0)} 0 {large} 0 {c(q0[0])},{c(q0[1])} Z")


def sunburst(paths: Sequence[Mapping], depth: int = 4, *, width: float = base.HALF_W) -> str:
    """Sequences sunburst: condition, then the first `depth` calls, then the outcome, one ring each.

    Calls after the `depth`-th are merged in one "…" step. An arc is titled with its path, run count and the share of
    the runs of its condition; the inner ring carries the condition letter, no other arc carries text. The legend has
    a row for the conditions and a row for the outcomes."""
    if not paths:
        return ""
    root = _tree(paths, depth)
    rings = _depth(root) - 1
    radius = width / 2 - 8
    hole = 38.0
    thick = (radius - hole) / rings
    top = 18.0 + 2 * (base.TEXT_PX + 6)
    cx, cy = width / 2, top + radius
    arcs: list[str] = []
    labels: list[str] = []
    cond_total = {name: k["n"] for name, k in root["kids"].items()}
    ends = {"correct": "ok", "not correct": "bad"}

    def walk(nd: dict, ring: int, a0: float, trail: tuple[str, ...]) -> None:
        kids = sorted(nd["kids"].values(), key=lambda k: (k["name"],) if ring == 0 else (-k["n"], k["name"]))
        a = a0
        for kid in kids:
            span = 2 * math.pi * kid["n"] / root["n"]
            path = (*trail, kid["name"])
            leaf = not kid["kids"]
            cond = path[0]
            cls = f"c-{cond}" if cond in base.CONDS else "muted"
            if leaf and kid["name"] in ends:
                cls = ends[kid["name"]]
            total = cond_total[cond] if ring else root["n"]
            tip = f"{' → '.join(path)}: {base.plural(kid['n'], 'run')} ({_share(kid['n'], total)} of " \
                  f"{'all runs' if not ring else 'the runs of ' + cond})"
            r0, r1 = hole + ring * thick, hole + (ring + 1) * thick
            arcs.append(base.path(_arc(cx, cy, a, a + span, r0, r1), f"{cls} tile", tip))
            rmid = (r0 + r1) / 2
            if ring == 0 and span * rmid >= base.text_width(kid["name"]) + 6:
                x, y = base.polar(cx, cy, rmid, a + span / 2)
                labels.append(base.text(x, y + base.TEXT_PX * 0.35, kid["name"], "middle", base.ink(cls)))
            walk(kid, ring + 1, a, path)
            a += span

    walk(root, 0, 0.0, ())
    conds = [(c, c) for c in sorted(cond_total) if c in base.CONDS]
    leg = base.legend(conds, 0, 14)[0] + base.legend([("ok", "correct"), ("bad", "not correct")], 0,
                                                     14 + base.TEXT_PX + 6)[0]
    centre = base.text(cx, cy + base.TEXT_PX * 0.35, base.plural(root["n"], "run"), "middle", "mut")
    title = f"Sunburst of call paths by condition; {base.plural(root['n'], 'run')}"
    return base.figure(width, top + 2 * radius + 8, title, leg + "".join(arcs) + "".join(labels) + centre)


def _fold(calls: Sequence[str]) -> list[str]:
    """`calls` with each run of three or more calls of one tool written once as `name ×n`."""
    out: list[str] = []
    for name, group in itertools.groupby(calls):
        n = len(list(group))
        out.extend([name] * n if n < 3 else [f"{name} ×{n}"])
    return out


def path_rows(paths: Sequence[Mapping], top: int = 12) -> list[dict]:
    """The `top` most frequent complete call paths: `[{"cond", "path", "runs", "correct"}]`, most frequent first. The
    paths beyond them are one last row `{"cond": "", "path": "n other paths", "runs", "correct", "other": True}`, so the
    runs add up to the runs of the sunburst."""
    counts: Counter[tuple[str, tuple[str, ...]]] = Counter()
    right: Counter[tuple[str, tuple[str, ...]]] = Counter()
    for p in paths:
        key = (str(p.get("cond", "")), tuple(str(c) for c in p.get("calls", [])))
        counts[key] += 1
        right[key] += 1 if p.get("correct") else 0
    order = sorted(counts, key=lambda k: (-counts[k], k[0], k[1]))
    rows = [{"cond": c, "path": " → ".join(_fold(calls)) if calls else NO_CALL, "runs": counts[(c, calls)],
             "correct": right[(c, calls)]} for c, calls in order[:top]]
    rest = order[top:]
    if rest:
        rows.append({"cond": "", "path": base.plural(len(rest), "other path"), "runs": sum(counts[k] for k in rest),
                     "correct": sum(right[k] for k in rest), "other": True})
    return rows
