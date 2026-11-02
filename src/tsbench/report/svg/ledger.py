"""The task ledger: every task of the benchmark as one row, one cell per condition (A, B, C), grouped by task class.

A cell is a bar. A ratio cell (error ÷ tolerance) is drawn on a log axis from 0.01 to 100 with a line at 1 and the
number beside it. A share cell (batch, diagram, pairing) is a bar of the share of items correct with a line at the
required share. A scope cell (out of scope, refusal) is a full bar with its word beside it. Green (`ok`) is a correct
task, `bad` one that is not. The blocks take as many columns as the width holds; the row label is the full task id.
Pure: plain data in, one SVG string out.
"""
from __future__ import annotations

import math
from collections.abc import Callable, Sequence

from . import base

__all__ = ["task_ledger"]

_PITCH = 17.0  # height of a row
_BAR_H = 9.0
_NUM = 46.0  # room for the number or the scope word at the right of a bar
_GAP = 4.0  # between the number and the next bar
_COL_GAP = 22.0  # between two blocks
_MIN_BLOCK = 440.0  # the narrowest block: a label column and three cells
_LO, _HI = 0.01, 100.0  # the axis of error ÷ tolerance
_NOTES = ("Bar: error ÷ tolerance, log axis 0.01 to 100, line at 1.",
          "Share bar: share of items correct, line at the required share.")


def _names(conds: Sequence[str]) -> str:
    """"A", "A and C", "A, B and C"."""
    return " and ".join([", ".join(conds[:-1]), conds[-1]] if len(conds) > 1 else conds)


def _split(sizes: Sequence[int], columns: int) -> list[list[int]]:
    """Indices of the blocks per column, in order, no block split: the smallest tallest column wins."""
    columns = max(1, min(columns, len(sizes)))

    def fits(cap: int) -> list[list[int]] | None:
        cols: list[list[int]] = [[]]
        used = 0
        for i, n in enumerate(sizes):
            if cols[-1] and used + n > cap:
                cols.append([])
                used = 0
            cols[-1].append(i)
            used += n
        return cols if len(cols) <= columns else None

    lo, hi = max(sizes), sum(sizes)
    while lo < hi:
        mid = (lo + hi) // 2
        if fits(mid):
            hi = mid
        else:
            lo = mid + 1
    return fits(lo) or [list(range(len(sizes)))]


def _num(v: float) -> str:
    """The number beside a ratio bar: "<0.1", one decimal below 10, whole numbers above."""
    if v < 0.1:
        return "<0.1"
    return base.number(v, 1) if v < 9.95 else base.number(v, 0)


def _tick(x: float, y: float) -> str:
    return base.line(x, y - 2, x, y + _BAR_H + 2, "zero")


def _cell(cell: dict, task: str, cond: str, x: float, y: float, bw: float) -> str:
    """One cell: track, bar, line, number or word, all under one tooltip."""
    yy = y + (_PITCH - _BAR_H) / 2 - 1
    state = "correct" if cell.get("ok") else "not correct"
    head = f"{task} · {cond}"
    cls = "ok" if cell.get("ok") else "bad"
    kind, v = cell.get("kind"), cell.get("value")
    parts = [base.rect(x, yy, bw, _BAR_H, "band")]
    if kind == "scope":
        word = cell.get("text")
        if word is None:
            parts.append(base.rect(x, yy, bw, _BAR_H, "na"))
            parts.append(base.text(x + bw + 3, yy + _BAR_H - 0.5, "–", "start", "mut", base.SMALL_PX))
            return base.group(parts, tip=f"{head} · no value · {state}")
        parts.append(base.rect(x, yy, bw, _BAR_H, cls))
        parts.append(base.text(x + bw + 3, yy + _BAR_H - 0.5, str(word), "start", "", base.SMALL_PX))
        return base.group(parts, tip=f"{head} · {word} · {state}")
    if v is None:
        parts.append(base.rect(x, yy, bw, _BAR_H, "na"))
        parts.append(base.text(x + bw + 3, yy + _BAR_H - 0.5, "–", "start", "mut", base.SMALL_PX))
        return base.group(parts, tip=f"{head} · no value · {state}")
    if kind == "share":
        need = cell.get("need")
        parts.append(base.rect(x, yy, max(v * bw, 1.0), _BAR_H, cls))
        if need is not None:
            parts.append(_tick(x + need * bw, yy))
        label = f"{base.number(100 * v, 0)}%"
        parts.append(base.text(x + bw + 3, yy + _BAR_H - 0.5, label, "start", "", base.SMALL_PX))
        req = "" if need is None else f" (required {base.number(100 * need, 0)} %)"
        return base.group(parts, tip=f"{head} · items correct {base.number(100 * v, 1)} %{req} · {state}")
    scale = base.Log(_LO, _HI, 0.0, bw)
    parts.append(base.rect(x, yy, max(scale(max(v, _LO)), 1.0), _BAR_H, cls))
    parts.append(_tick(x + scale(1.0), yy))
    parts.append(base.text(x + bw + 3, yy + _BAR_H - 0.5, _num(v), "start", "", base.SMALL_PX))
    exact = base.number(v, 2) if v >= 0.01 else "<0.01"
    return base.group(parts, tip=f"{head} · error ÷ tolerance {exact} · {state}")


def task_ledger(classes: Sequence[dict], *, width: float = base.FULL_W,
                task_href: Callable[[str], str] | None = None) -> str:
    """One row per task, one block per task class, in the order given; one cell per condition in a row.

    classes: `[{"class": "closed_form", "k": {"A": 2, "B": 1, "C": 2}, "n": 2, "tasks": [{"task": "P-closed_form-01",
    "cells": {"A": cell, "B": cell, "C": cell}}]}]`. `k` is the number of correct tasks per condition, `n` the number
    of tasks; the conditions in `k` are the columns (a condition with no evaluable run is absent and not drawn);
    the optional `n_by` gives per condition the tasks with an evaluable run (default `n`); a condition with none in a
    class says `no run` there. A cell is
    `{"kind": "ratio" | "share" | "scope", "value": float | None, "ok": bool, "need": float | None,
    "text": str | None}`:
    - ratio: `value` is error ÷ tolerance (log axis 0.01 to 100, line at 1, the number beside the bar);
    - share: `value` is a share of items in [0, 1], `need` the required share (line at it);
    - scope: `text` is the word printed beside the bar ("named", "missed", "refused");
    - `ok` is the scorer's verdict (class `ok` or `bad`), never derived from the value; a `value` of None is drawn as
      "no value" and a dash.
    The head of a block carries k/n per condition. The figure is `width` px wide; the blocks sit side by side in as
    many columns as fit (two at 960 px, one at 464 px); a class is never split. With `task_href` each row label opens
    the row of its task. Empty input returns ""."""
    if not classes:
        return ""
    w = float(width)
    columns = max(1, int((w + _COL_GAP) // (_MIN_BLOCK + _COL_GAP)))
    block = (w - (columns - 1) * _COL_GAP) / columns
    lab = max((base.text_width(str(t["task"]), base.SMALL_PX) for c in classes for t in c["tasks"]),
              default=4 * base.GLYPH_EM * base.SMALL_PX) + 12
    conds = [c for c in base.CONDS if any(c in b["k"] for b in classes)] or list(base.CONDS)
    cw = (block - lab) / len(conds)
    bw = cw - _NUM - _GAP
    layout = _split([1 + len(c["tasks"]) for c in classes], columns)
    out: list[str] = []
    leg, _ = base.legend([("ok", "correct"), ("bad", "not correct"), ("na", "no value")], 0, 12)
    out.append(leg)
    y = 32.0
    for note in _NOTES:
        for ln in base.wrap(note, w, base.SMALL_PX):
            out.append(base.text(0, y, ln, "start", "mut", base.SMALL_PX))
            y += 14
    top = y + 22
    rows = max(sum(1 + len(classes[i]["tasks"]) for i in col) for col in layout)
    for ci, col in enumerate(layout):
        x0 = ci * (block + _COL_GAP)
        for k, cond in enumerate(conds):
            out.append(base.marker(cond, x0 + lab + k * cw + 5, top - 18, True, 4.5))
            out.append(base.text(x0 + lab + k * cw + 14, top - 14, cond, "start", "b", base.SMALL_PX))
        ry = top
        for i in col:
            blk = classes[i]
            name, n = str(blk["class"]), blk["n"]
            out.append(base.text(x0, ry + _PITCH - 5, name, "start", "b", base.SMALL_PX))
            for k, cond in enumerate(conds):
                kk = blk["k"].get(cond, 0)
                nn = (blk.get("n_by") or {}).get(cond, n)  # tasks with an evaluable run under this condition
                head, tip = (f"{kk}/{nn}", f"{kk} of {base.plural(nn, 'task')} correct") if nn else ("no run", "no run")
                out.append(base.group(
                    base.text(x0 + lab + k * cw + bw + _NUM, ry + _PITCH - 5, head, "end", "b", base.SMALL_PX),
                    tip=f"{name} · {cond}: {tip}"))
            out.append(base.line(x0, ry + _PITCH - 1, x0 + block, ry + _PITCH - 1, "grid"))
            ry += _PITCH
            for t in blk["tasks"]:
                tid = str(t["task"])
                label = base.text(x0 + lab - 8, ry + _PITCH - 5, tid, "end", "mut", base.SMALL_PX)
                out.append(label if task_href is None else base.link(task_href(tid), label))
                for k, cond in enumerate(conds):
                    cx = x0 + lab + k * cw
                    if cond in t["cells"]:
                        out.append(_cell(t["cells"][cond], tid, cond, cx, ry, bw))
                    else:  # the condition has no run of this task
                        out.append(base.rect(cx, ry + (_PITCH - _BAR_H) / 2 - 2, bw, _BAR_H, "na",
                                             f"{tid} · {cond} · not run"))
                ry += _PITCH
    h = top + rows * _PITCH + 6
    n_tasks = sum(len(c["tasks"]) for c in classes)
    return base.figure(w, math.ceil(h), f"Outcome and error size of {n_tasks} tasks under {_names(conds)}", out)
