"""The platform figures: the schedule of the runs with the cumulative cost, and the file tree of a run set with the
hashes that link its files. Both are drawn at the width they are given.

`schedule(runs, manifest)`: one lane per condition on a UTC time axis, one bar per run (stacked in rows where the runs
of a condition overlap), the window of the manifest as a band, and under the lanes the cumulative cost as a step line
with a dot per finished run.

`file_tree(entries, chain)`: one row per file or folder, indented by depth, with a bar of its size (log axis), the
start of its sha256 and one arrow per link of the hash chain ("the hash of this file is recorded in that field of that
file"). A link whose recorded hash does not match the file carries a mismatch mark.
"""
from __future__ import annotations

import datetime
import math
from typing import Any

from tsbench.report.svg import base

__all__ = ["file_tree", "schedule"]

_STEPS = (60, 120, 300, 600, 900, 1800, 3600, 7200, 10800, 21600, 43200, 86400, 172800, 345600, 604800, 1209600,
          2592000)  # tick spacing in seconds: a minute to 30 days
_EPOCH = datetime.datetime(1970, 1, 1, tzinfo=datetime.UTC)


def _time(s) -> datetime.datetime | None:
    try:
        t = datetime.datetime.fromisoformat(str(s))
    except ValueError:
        return None
    return t if t.tzinfo else t.replace(tzinfo=datetime.UTC)


def _sec(t: datetime.datetime) -> float:
    return (t - _EPOCH).total_seconds()


def _stamp(sec: float, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    return (_EPOCH + datetime.timedelta(seconds=sec)).strftime(fmt)


def _ticks(a: float, b: float, most: int = 7) -> list[float]:
    """At most about `most` tick times between a and b (epoch seconds), on multiples of a round step."""
    step = next((s for s in _STEPS if (b - a) / s <= most), _STEPS[-1])
    first = math.ceil(a / step) * step
    return [first + i * step for i in range(int((b - first) // step) + 1)]


def _elapsed(sec: float) -> str:
    """Seconds since the first start as days, hours and minutes: `0`, `1.5 min`, `1 h 30 min`, `1 d 2 h`."""
    if sec <= 0:
        return "0"
    if sec < 3600:
        return f"{sec / 60:g} min"
    d, rest = divmod(base.round_half_up(sec / 60), 1440)
    h, m = divmod(rest, 60)
    if d:
        return f"{d} d" + (f" {h} h" if h else "")
    return f"{h} h" + (f" {m} min" if m else "")


def _money(v: float) -> str:
    return f"${base.number(v, 2)}"


# ---------------------------------------------------------------- the schedule


def schedule(runs: list[dict], manifest: dict, *, width: float = base.FULL_W) -> str:
    """runs `[{"cond", "task", "start": ISO-8601 UTC, "seconds", "cost"}]`, manifest `{"start", "end", "planned",
    "done", "skipped", "total_cost"}` (every key optional). A run without wall time or cost (None) is drawn as a
    point and its title says "not recorded"; the count of such runs is printed. A run with `"cost_is_estimate"` True
    (a gateway model, priced by Claude Code at Claude list prices) has no real cost: it is left out of the cost line
    and its tip names no cost; without a run of real cost there is no cost line, axis or total, and the manifest total
    is left out when any run is an estimate. "" without a run that has a start time."""
    items = []
    for r in runs:
        t = _time(r.get("start"))
        if t is not None and r.get("cond") in base.CONDS:
            items.append({**r, "t0": _sec(t), "t1": _sec(t) + float(r.get("seconds") or 0.0)})
    if not items:
        return ""
    m0, m1 = _time(manifest.get("start")), _time(manifest.get("end"))
    lo = min([i["t0"] for i in items] + ([_sec(m0)] if m0 else []))
    hi = max([i["t1"] for i in items] + ([_sec(m1)] if m1 else []))
    w, left, right = float(width), 74.0, 78.0
    sx = base.Linear(lo, hi if hi > lo else lo + 1, left, w - right)
    sub_h, pad = 7.0, 8.0
    conds = [c for c in base.CONDS if any(i["cond"] == c for i in items)]
    facts = []
    if m0 and m1:
        facts.append(f"manifest {_stamp(_sec(m0), '%Y-%m-%d %H:%M')} – {_stamp(_sec(m1), '%Y-%m-%d %H:%M')} UTC")
    facts += [f"{k} {manifest[k]}" for k in ("planned", "done", "skipped") if manifest.get(k) is not None]
    estimated = [i for i in items if i.get("cost_is_estimate")]
    show_cost = len(estimated) < len(items)
    if manifest.get("total_cost") is not None and not estimated:
        facts.append(f"total cost {_money(float(manifest['total_cost']))}")
    if estimated:
        facts.append(f"no real cost (gateway model) for {base.plural(len(estimated), 'run')}")
    no_time = sum(1 for i in items if i.get("seconds") is None)
    no_cost = sum(1 for i in items if i.get("cost") is None and not i.get("cost_is_estimate"))
    if no_time:
        facts.append(f"wall time not recorded for {base.plural(no_time, 'run')}")
    if no_cost:
        facts.append(f"cost not recorded for {base.plural(no_cost, 'run')}")
    fact_lines = base.wrap(" · ".join(facts), w - left - 8) if facts else []
    head_h = 14.0 * max(len(fact_lines), 1)
    out: list[str] = []
    y = head_h + 12.0
    lanes: list[tuple[str, float, float]] = []
    for c in conds:
        rows_end: list[float] = []  # end time of the last run of each row of the lane
        placed = []
        for i in sorted((i for i in items if i["cond"] == c), key=lambda i: (i["t0"], str(i.get("task")))):
            row = next((k for k, e in enumerate(rows_end) if e <= i["t0"]), None)
            if row is None:
                rows_end.append(i["t1"])
                row = len(rows_end) - 1
            else:
                rows_end[row] = i["t1"]
            placed.append((i, row))
        lane_h = len(rows_end) * sub_h + 2 * pad
        lanes.append((c, y, lane_h))
        for i, row in placed:
            sec = i.get("seconds")
            secs = "wall time not recorded" if sec is None else f"{base.round_half_up(float(sec))} s"
            cost = "cost not recorded" if i.get("cost") is None else _money(float(i["cost"]))
            tip = f"{i.get('task')} · {c}: start {_stamp(i['t0'])} UTC, {secs}" \
                  + ("" if i.get("cost_is_estimate") else f", {cost}")
            out.append(base.rect(sx(i["t0"]), y + pad + row * sub_h, max(sx(i["t1"]) - sx(i["t0"]), 1.5), sub_h - 1.5,
                                 f"c-{c}", tip))
        y += lane_h
    lanes_bottom = y
    cost_top, cost_h = lanes_bottom + (26.0 if show_cost else 0.0), 96.0 if show_cost else 0.0
    cost_bottom = cost_top + cost_h
    steps, cum = [], 0.0
    for i in sorted((i for i in items if not i.get("cost_is_estimate")), key=lambda i: (i["t1"], str(i.get("task")))):
        cum += float(i.get("cost") or 0.0)
        steps.append((i, cum))
    sy = base.Linear(0.0, cum if cum > 0 else 1.0, cost_bottom, cost_top)
    head = []
    if m0 and m1:
        tip = f"manifest window: {_stamp(_sec(m0), '%Y-%m-%d %H:%M')} to {_stamp(_sec(m1), '%Y-%m-%d %H:%M')} UTC"
        head.append(base.rect(sx(_sec(m0)), head_h + 6, sx(_sec(m1)) - sx(_sec(m0)), cost_bottom - head_h - 6, "band",
                              tip))
    for c, ly, lh in lanes:
        n = sum(1 for i in items if i["cond"] == c)
        head.append(base.line(left, ly + lh, w - right, ly + lh, "grid"))
        head.append(base.text(left - 8, ly + lh / 2 + base.TEXT_PX * 0.35, f"{c} · {base.plural(n, 'run')}",
                              "end", "b"))
    out = head + out
    if show_cost:
        d = [f"M{base.coord(left)},{base.coord(sy(0))}"]
        prev = 0.0
        for i, c_sum in steps:
            d.append(f"H{base.coord(sx(i['t1']))}V{base.coord(sy(c_sum))}")
            prev = c_sum
        d.append(f"H{base.coord(w - right)}")
        out.append(base.path("".join(d), "frame", f"cumulative cost over {len(steps)} runs, ending at {_money(prev)}",
                             width=1.4))
        for i, c_sum in steps:
            out.append(base.circle(sx(i["t1"]), sy(c_sum), 1.8, "muted",
                                   f"after {i.get('task')} · {i['cond']}: cumulative cost {_money(c_sum)}, "
                                   f"finished {_stamp(i['t1'])} UTC"))
        out.append(base.text(w - right + 6, sy(prev) + 4, _money(prev), "start", "b"))
        out.append(base.axis_left(sy, base.nice_ticks(0.0, cum if cum > 0 else 1.0, 4), left, cost_top, cost_bottom,
                                  "cumulative cost (USD)", lambda v: f"{v:g}", grid_to=w - right))
    ticks = [lo + t for t in _ticks(0.0, hi - lo, max(int((w - left - right) // 95), 2))]
    out.append(base.axis_bottom(sx, ticks, cost_bottom, left, w - right, "time since the first start",
                                lambda v: _elapsed(v - lo)))
    for k, ln in enumerate(fact_lines):
        out.append(base.text(left, 14 + 14 * k, ln, "start", "mut"))
    h = cost_bottom + 8 + 2 * base.TEXT_PX + 12
    return base.figure(w, h, "Schedule of the runs and cumulative cost" if show_cost else "Schedule of the runs", out)


# ---------------------------------------------------------------- the file tree


def _size(n: int) -> str:
    return f"{base.number(n)} B"


def file_tree(entries: list[dict], chain: list[dict], *, width: float = base.FULL_W) -> str:
    """entries `[{"path", "bytes", "is_dir", "hash": str | None}]` in a depth-first listing (a folder may carry
    "n_files"), chain `[{"from", "to", "field", "ok"}]`: the hash of `from` is recorded in `field` of `to`; `ok` False
    means the recorded hash does not match the file, and the link is drawn with a mismatch mark. A link whose paths
    are not both listed is left out. The bar takes the width the columns leave. "" without entries."""
    if not entries:
        return ""
    w = float(width)
    row_h, top = 20.0, 24.0
    rows: list[dict[str, Any]] = []
    for e in entries:
        path = str(e["path"]).strip("/")
        name = path.rsplit("/", 1)[-1] + ("/" if e.get("is_dir") else "")
        rows.append({**e, "path": path, "depth": path.count("/"), "label": name})
    index = {r["path"]: k for k, r in enumerate(rows)}
    links = [(str(c["from"]).strip("/"), str(c["to"]).strip("/"), str(c["field"]), bool(c.get("ok", True)))
             for c in chain if str(c["from"]).strip("/") in index and str(c["to"]).strip("/") in index]
    n = len(links)
    arrows_w = 14 + 9 * n + 16 if n else 8.0
    size_w, hash_w = 84.0, 108.0 if w >= base.FULL_W else 70.0
    name_room = min(max(10 + r["depth"] * 14 + base.text_width(r["label"]) for r in rows) + 14, w * 0.4)
    bar_w = max(min(w - name_room - 8 - size_w - hash_w - arrows_w, 320.0), 40.0)
    bar_x = name_room
    size_x = bar_x + bar_w + 8
    hash_x = size_x + size_w
    arrow_x = hash_x + hash_w
    top_bytes = 10.0 ** max(math.ceil(math.log10(max([r["bytes"] for r in rows] + [10]))), 1)
    sb = base.Log(1.0, top_bytes, bar_x, bar_x + bar_w)
    out: list[str] = []
    for k, r in enumerate(rows):
        y = top + k * row_h
        mid = y + row_h / 2
        label = base.fit(r["label"], name_room - 8 - 10 - r["depth"] * 14)
        out.append(base.text(10 + r["depth"] * 14, mid + base.TEXT_PX * 0.35, label, "start"))
        tip = f"{r['path']}: {base.number(r['bytes'])} bytes" + (f" · sha256 {r['hash']}" if r.get("hash") else "")
        out.append(base.rect(bar_x, y + 4, max(sb(max(r["bytes"], 1)) - bar_x, 1.0), row_h - 8, "muted", tip))
        out.append(base.text(size_x, mid + base.TEXT_PX * 0.35, _size(r["bytes"]), "start", "mut"))
        if r.get("hash"):
            out.append(base.text(hash_x, mid + base.TEXT_PX * 0.35, str(r["hash"])[:8], "start", "mut"))
        elif r.get("n_files"):
            out.append(base.text(hash_x, mid + base.TEXT_PX * 0.35, f"{r['n_files']} files", "start", "mut"))
    bottom = top + len(rows) * row_h
    for k, (a, b, field, ok) in enumerate(links):
        ya, yb = top + index[a] * row_h + row_h / 2, top + index[b] * row_h + row_h / 2
        xv = arrow_x + 14 + 9 * k
        d = f"M{base.coord(arrow_x)},{base.coord(ya)}H{base.coord(xv)}V{base.coord(yb)}H{base.coord(arrow_x + 5)}"
        out.append(base.path(d, "ax", f"hash of {a} is recorded in {field} of {b}", width=1.4))
        out.append(base.polygon([(arrow_x, yb), (arrow_x + 6, yb - 3.5), (arrow_x + 6, yb + 3.5)], "muted"))
        if not ok:  # the recorded hash is not the hash of the file
            out.append(base.circle(xv, (ya + yb) / 2, 4.5, "bad",
                                   f"hash of {a} recorded in {field} of {b} does not match the file"))
        out.append(base.text(xv + 3, (ya + yb) / 2 + 4 + (9 if not ok else 0), str(k + 1), "start", "mut",
                             base.SMALL_PX))
    out.append(base.text(hash_x, 14, "sha256", "start", "mut"))
    if w >= base.FULL_W:
        out.append(base.text(arrow_x, 14, "hash recorded in", "start", "mut"))
    else:
        out.append(base.text(w - 4, 14, "recorded in", "end", "mut"))
    decades = sb.ticks()
    room = bar_w / max(len(decades) - 1, 1)  # px between two decades; a label needs about its length times 7 px
    every = max(math.ceil((max(base.text_width(base.number(v)) for v in decades) + 6) / room), 1)
    out.append(base.axis_bottom(sb.__call__, sb.ticks(every), bottom + 4, bar_x, bar_x + bar_w, "bytes (log scale)",
                                lambda v: base.number(v)))
    y = bottom + 4 + 8 + 2 * base.TEXT_PX + 14
    for k, (a, b, field, ok) in enumerate(links):
        note = f"{k + 1}  {a} → {b}: {field}" + ("" if ok else " (the hash does not match)")
        for j, ln in enumerate(base.wrap(note, w - 20)):
            out.append(base.text(10 if j == 0 else 24, y, ln, "start", "mut" if ok else "b"))
            y += base.TEXT_PX + 4
    return base.figure(w, y + 4, "Files of the run set and the hashes recorded in them", out)
