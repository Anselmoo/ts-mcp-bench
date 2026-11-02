"""Circle packing and the survivors by module.

The packing is a port of d3-hierarchy's `pack` (front-chain sibling packing and the enclosing circle), with d3's own
deterministic shuffle, so the same input gives the same drawing. `toolout` draws with it. `by_module` groups the
surviving mutants for the text list of the code checks.
"""
from __future__ import annotations

import math
from collections.abc import Callable, Sequence

__all__ = ["by_module"]


class _Circle:
    __slots__ = ("r", "x", "y")

    def __init__(self, r: float = 0.0, x: float = 0.0, y: float = 0.0):
        self.r, self.x, self.y = r, x, y


class _Link:
    __slots__ = ("c", "next", "prev")

    def __init__(self, c: _Circle):
        self.c = c
        self.next: _Link = self
        self.prev: _Link = self


def _lcg() -> Callable[[], float]:
    s = 1

    def rnd() -> float:
        nonlocal s
        s = (1664525 * s + 1013904223) % 4294967296
        return s / 4294967296

    return rnd


def _place(b: _Circle, a: _Circle, c: _Circle) -> None:
    dx, dy = b.x - a.x, b.y - a.y
    d2 = dx * dx + dy * dy
    if d2:
        a2 = (a.r + c.r) ** 2
        b2 = (b.r + c.r) ** 2
        if a2 > b2:
            x = (d2 + b2 - a2) / (2 * d2)
            y = math.sqrt(max(0.0, b2 / d2 - x * x))
            c.x = b.x - x * dx - y * dy
            c.y = b.y - x * dy + y * dx
        else:
            x = (d2 + a2 - b2) / (2 * d2)
            y = math.sqrt(max(0.0, a2 / d2 - x * x))
            c.x = a.x + x * dx - y * dy
            c.y = a.y + x * dy + y * dx
    else:
        c.x, c.y = a.x + c.r, a.y


def _intersects(a: _Circle, b: _Circle) -> bool:
    dr = a.r + b.r - 1e-6
    dx, dy = b.x - a.x, b.y - a.y
    return dr > 0 and dr * dr > dx * dx + dy * dy


def _score(n: _Link) -> float:
    a, b = n.c, n.next.c
    ab = a.r + b.r
    dx = (a.x * b.r + b.x * a.r) / ab
    dy = (a.y * b.r + b.y * a.r) / ab
    return dx * dx + dy * dy


# ---- smallest enclosing circle (d3-hierarchy/src/pack/enclose.js)


def _encloses_not(a: _Circle, b: _Circle) -> bool:
    dr = a.r - b.r
    dx, dy = b.x - a.x, b.y - a.y
    return dr < 0 or dr * dr < dx * dx + dy * dy


def _encloses_weak(a: _Circle, b: _Circle) -> bool:
    dr = a.r - b.r + max(a.r, b.r, 1.0) * 1e-9
    dx, dy = b.x - a.x, b.y - a.y
    return dr > 0 and dr * dr > dx * dx + dy * dy


def _encloses_weak_all(a: _Circle, bs: list[_Circle]) -> bool:
    return all(_encloses_weak(a, b) for b in bs)


def _basis2(a: _Circle, b: _Circle) -> _Circle:
    x21, y21, r21 = b.x - a.x, b.y - a.y, b.r - a.r
    ln = math.sqrt(x21 * x21 + y21 * y21)
    return _Circle((ln + a.r + b.r) / 2, (a.x + b.x + x21 / ln * r21) / 2, (a.y + b.y + y21 / ln * r21) / 2)


def _basis3(a: _Circle, b: _Circle, c: _Circle) -> _Circle:
    x1, y1, r1 = a.x, a.y, a.r
    a2, a3 = x1 - b.x, x1 - c.x
    b2, b3 = y1 - b.y, y1 - c.y
    c2, c3 = b.r - r1, c.r - r1
    d1 = x1 * x1 + y1 * y1 - r1 * r1
    d2 = d1 - b.x * b.x - b.y * b.y + b.r * b.r
    d3 = d1 - c.x * c.x - c.y * c.y + c.r * c.r
    ab = a3 * b2 - a2 * b3
    xa = (b2 * d3 - b3 * d2) / (ab * 2) - x1
    xb = (b3 * c2 - b2 * c3) / ab
    ya = (a3 * d2 - a2 * d3) / (ab * 2) - y1
    yb = (a2 * c3 - a3 * c2) / ab
    qa = xb * xb + yb * yb - 1
    qb = 2 * (r1 + xa * xb + ya * yb)
    qc = xa * xa + ya * ya - r1 * r1
    r = -((qb + math.sqrt(qb * qb - 4 * qa * qc)) / (2 * qa) if abs(qa) > 1e-6 else qc / qb)
    return _Circle(r, x1 + xa + xb * r, y1 + ya + yb * r)


def _basis(bs: list[_Circle]) -> _Circle:
    if len(bs) == 1:
        return _Circle(bs[0].r, bs[0].x, bs[0].y)
    return _basis2(bs[0], bs[1]) if len(bs) == 2 else _basis3(bs[0], bs[1], bs[2])


def _extend_basis(bs: list[_Circle], p: _Circle) -> list[_Circle]:
    if _encloses_weak_all(p, bs):
        return [p]
    for b in bs:
        if _encloses_not(p, b) and _encloses_weak_all(_basis2(b, p), bs):
            return [b, p]
    for i in range(len(bs) - 1):
        for j in range(i + 1, len(bs)):
            if (_encloses_not(_basis2(bs[i], bs[j]), p) and _encloses_not(_basis2(bs[i], p), bs[j])
                    and _encloses_not(_basis2(bs[j], p), bs[i]) and _encloses_weak_all(_basis3(bs[i], bs[j], p), bs)):
                return [bs[i], bs[j], p]
    raise ArithmeticError("no enclosing basis")  # pragma: no cover - unreachable for a consistent set


def _enclose(circles: list[_Circle], rnd: Callable[[], float]) -> _Circle:
    cs = list(circles)
    m = len(cs)
    while m:  # d3's shuffle
        i = int(rnd() * m)
        m -= 1
        cs[m], cs[i] = cs[i], cs[m]
    basis: list[_Circle] = []
    e: _Circle | None = None
    i = 0
    while i < len(cs):
        p = cs[i]
        if e is not None and _encloses_weak(e, p):
            i += 1
        else:
            basis = _extend_basis(basis, p)
            e = _basis(basis)
            i = 0
    assert e is not None
    return e


def _pack_siblings(circles: list[_Circle], rnd: Callable[[], float]) -> float:
    """Place the circles without overlap around the origin, return the radius of the enclosing circle."""
    n = len(circles)
    if not n:
        return 0.0
    a = circles[0]
    a.x = a.y = 0.0
    if n == 1:
        return a.r
    b = circles[1]
    a.x, b.x, b.y = -b.r, a.r, 0.0
    if n == 2:
        return a.r + b.r
    c = circles[2]
    _place(b, a, c)
    na, nb, nc = _Link(a), _Link(b), _Link(c)
    na.next = nc.prev = nb
    nb.next = na.prev = nc
    nc.next = nb.prev = na
    i = 3
    while i < n:
        cc = circles[i]
        _place(na.c, nb.c, cc)
        nn = _Link(cc)
        j, k = nb.next, na.prev
        sj, sk = nb.c.r, na.c.r
        collided = False
        while True:
            if sj <= sk:
                if _intersects(j.c, nn.c):
                    nb = j
                    na.next = nb
                    nb.prev = na
                    collided = True
                    break
                sj += j.c.r
                j = j.next
            else:
                if _intersects(k.c, nn.c):
                    na = k
                    na.next = nb
                    nb.prev = na
                    collided = True
                    break
                sk += k.c.r
                k = k.prev
            if j is k.next:
                break
        if collided:
            continue  # try the same circle again, as d3 does (--i)
        nn.prev, nn.next = na, nb
        na.next = nb.prev = nb = nn
        best, best_s = na, _score(na)
        cur = nn.next
        while cur is not nb:
            s = _score(cur)
            if s < best_s:
                best, best_s = cur, s
            cur = cur.next
        na = best
        nb = na.next
        i += 1
    ring = [nb.c]
    cur = nb.next
    while cur is not nb:
        ring.append(cur.c)
        cur = cur.next
    e = _enclose(ring, rnd)
    for ci in circles:
        ci.x -= e.x
        ci.y -= e.y
    return e.r


class _Node:
    """A node of the survivor hierarchy: name, value (survivors), children, and its circle."""

    def __init__(self, name: str, value: int = 0):
        self.name, self.value = name, value
        self.kids: list[_Node] = []
        self.c = _Circle()
        self.ax = self.ay = self.ar = 0.0  # absolute circle in pixels

    def total(self) -> int:
        if self.kids:
            self.value = sum(k.total() for k in self.kids)
        return self.value


def _pack_children(node: _Node, padding: float, rnd: Callable[[], float]) -> None:
    for k in node.kids:
        _pack_children(k, padding, rnd)
    if not node.kids:
        node.c.r = math.sqrt(node.value)
        return
    for k in node.kids:
        k.c.r += padding
    node.c.r = _pack_siblings([k.c for k in node.kids], rnd) + padding
    for k in node.kids:
        k.c.r -= padding


def _absolute(node: _Node, scale: float, ox: float, oy: float) -> None:
    node.ar = node.c.r * scale
    node.ax, node.ay = ox, oy
    for k in node.kids:
        _absolute(k, scale, ox + k.c.x * scale, oy + k.c.y * scale)


def by_module(survivors: Sequence[dict]) -> list[dict]:
    """Survivors grouped for a text list: `[{"module", "functions": [{"function", "mutants": [{"mutant", "diff"}]}]}]`,
    modules and functions with the most survivors first (ties by name), mutants in the order given."""
    mods: dict[str, dict[str, list[dict]]] = {}
    for s in survivors:
        mods.setdefault(str(s["module"]), {}).setdefault(str(s["function"]), []).append(
            {"mutant": s["mutant"], "diff": s["diff"]})
    rows = []
    for mod, fns in mods.items():
        funcs = sorted(fns.items(), key=lambda kv: (-len(kv[1]), kv[0]))
        rows.append((sum(len(v) for v in fns.values()), mod,
                     [{"function": f, "mutants": ms} for f, ms in funcs]))
    rows.sort(key=lambda r: (-r[0], r[1]))
    return [{"module": mod, "functions": funcs} for _, mod, funcs in rows]
