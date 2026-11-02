"""The platform figures (src/tsbench/report/svg/platform.py): the run schedule and the file tree of a run set.

The tests read the numbers the SVG carries: one bar per run with its task id, start, seconds and cost in the title,
positions ordered as the data, the cumulative cost, one row per file with its size, one arrow per recorded hash.
"""
from __future__ import annotations

import re

import pytest
from svg_helpers import NS, attr_float, texts
from svg_helpers import classes as _classes
from svg_helpers import match as _match
from svg_helpers import root as _root
from svg_helpers import tip as _tip

from tsbench.report.svg import base, platform

RUNS = [
    {"cond": "A", "task": "P-x-01", "start": "2026-10-30T22:00:00+00:00", "seconds": 60.0, "cost": 0.10},
    {"cond": "B", "task": "P-x-02", "start": "2026-10-30T22:00:30+00:00", "seconds": 120.0, "cost": 0.20},
    {"cond": "C", "task": "P-x-03", "start": "2026-10-30T22:05:00+00:00", "seconds": 30.0, "cost": 0.40},
    {"cond": "C", "task": "P-x-04", "start": "2026-10-30T22:05:10+00:00", "seconds": 30.0, "cost": 0.30},
]
MANIFEST = {"start": "2026-10-30T22:00:00+00:00", "end": "2026-10-30T22:06:00+00:00", "planned": 4, "done": 3,
            "skipped": 1, "total_cost": 1.0}


THIN = "\u2009"  # the thin space between thousands (base.number)


def _width(svg: str) -> float:
    """The width attribute of the figure."""
    return attr_float(_root(svg), "width")


def _bars(svg: str) -> dict[str, dict]:
    """The run bars by task id: condition class, x, y, width and the title."""
    out = {}
    for el in _root(svg).iter(f"{NS}rect"):
        cls = _classes(el)
        if len(cls) == 1 and re.fullmatch(r"c-[ABC]", cls[0]) and _tip(el):
            task = re.search(r"P-x-\d\d|[^ ·]*<[^ ·]*", _tip(el))
            out[task[0] if task else _tip(el)] = {"cond": cls[0][2], "x": attr_float(el, "x"),
                                                  "y": attr_float(el, "y"), "w": attr_float(el, "width"),
                                                  "tip": _tip(el)}
    return out


def test_schedule_draws_one_bar_per_run_with_task_start_seconds_and_cost():
    svg = platform.schedule(RUNS, MANIFEST)
    bars = _bars(svg)
    assert set(bars) == {"P-x-01", "P-x-02", "P-x-03", "P-x-04"}
    assert [bars[t]["cond"] for t in sorted(bars)] == ["A", "B", "C", "C"]
    tip = bars["P-x-02"]["tip"]
    assert "P-x-02" in tip and "2026-10-30 22:00:30" in tip and "120 s" in tip and "$0.20" in tip


def test_schedule_places_bars_on_the_time_axis_in_proportion_to_start_and_seconds():
    bars = _bars(platform.schedule(RUNS, MANIFEST))
    assert bars["P-x-01"]["x"] < bars["P-x-02"]["x"] < bars["P-x-03"]["x"] < bars["P-x-04"]["x"]
    assert abs(bars["P-x-02"]["w"] / bars["P-x-01"]["w"] - 2.0) < 0.05
    assert abs(bars["P-x-03"]["w"] - bars["P-x-04"]["w"]) < 1e-6
    # 30 s after the start of A is where B starts: half a minute of a five-minute-forty window
    scale = (bars["P-x-04"]["x"] - bars["P-x-01"]["x"]) / 310.0
    assert abs((bars["P-x-02"]["x"] - bars["P-x-01"]["x"]) - 30 * scale) < 0.2


def test_schedule_has_one_lane_per_condition_and_stacks_overlapping_runs_of_a_lane():
    bars = _bars(platform.schedule(RUNS, MANIFEST))
    assert bars["P-x-01"]["y"] < bars["P-x-02"]["y"] < bars["P-x-03"]["y"]
    assert bars["P-x-04"]["y"] > bars["P-x-03"]["y"]  # starts while P-x-03 runs: its own row in the lane
    labels = texts(platform.schedule(RUNS, MANIFEST))
    assert [t.split(" · ")[0] for t in labels if re.fullmatch(r"[ABC] · \d+ runs?", t)] == ["A", "B", "C"]


def test_schedule_cumulative_cost_steps_by_run_end_and_ends_at_the_total():
    svg = platform.schedule(RUNS, MANIFEST)
    steps = [_tip(c) for c in _root(svg).iter(f"{NS}circle") if "cumulative" in _tip(c)]
    assert len(steps) == 4
    assert [_match(r"\$([\d.]+)", s)[1] for s in steps] == ["0.10", "0.30", "0.70", "1.00"]
    assert "P-x-01" in steps[0] and "P-x-04" in steps[-1]
    assert any("1.00" in t for t in texts(svg))


def _estimated(runs):
    return [{**r, "cost_is_estimate": True} for r in runs]


def test_schedule_of_estimated_costs_shows_no_cost_at_all():
    """Runs whose cost is a list-price estimate (a gateway model): no cost line, axis, total or tip cost."""
    svg = platform.schedule(_estimated(RUNS), MANIFEST)
    text = " ".join(texts(svg))
    assert "$" not in svg and "USD" not in text and "cost" not in text.replace("no real cost", "")
    assert "total cost" not in text and "cumulative" not in svg
    assert "no real cost (gateway model)" in text
    assert all("$" not in bar["tip"] and "cost" not in bar["tip"] for bar in _bars(svg).values())
    assert len(_bars(svg)) == 4  # the bars stay


def test_schedule_with_estimated_and_real_runs_sums_the_real_ones_and_drops_the_total():
    runs = [dict(RUNS[0], cost_is_estimate=True)] + RUNS[1:]
    svg = platform.schedule(runs, MANIFEST)
    text = " ".join(texts(svg))
    assert "total cost" not in text and "cost not recorded" not in text
    assert "$0.90" in svg  # B, C, C: 0.20 + 0.40 + 0.30
    assert "$0.10" not in svg and "$1.00" not in svg


def test_schedule_prints_the_manifest_counts():
    text = " ".join(texts(platform.schedule(RUNS, MANIFEST)))
    assert "planned 4" in text and "done 3" in text and "skipped 1" in text
    assert "total cost $1.00" in text
    assert "2026-10-30 22:00" in text and "2026-10-30 22:06" in text


def test_schedule_time_axis_counts_the_time_since_the_first_start():
    """The axis starts at 0 at the first run and counts minutes; the UTC start stands in the line above."""
    labels = texts(platform.schedule(RUNS, MANIFEST))
    assert "0" in labels and "5 min" in labels and "time since the first start" in labels
    assert any("UTC" in t for t in labels)


@pytest.mark.parametrize(("sec", "text"), [(0, "0"), (90, "1.5 min"), (300, "5 min"), (3600, "1 h"),
                                           (5400, "1 h 30 min"), (86400, "1 d"), (93600, "1 d 2 h")])
def test_elapsed_time_text(sec, text):
    assert platform._elapsed(sec) == text


@pytest.mark.parametrize(("sec", "text"), [(3630, "1 h 1 min"), (3690, "1 h 2 min"), (3750, "1 h 3 min"),
                                           (90 * 60 + 30, "1 h 31 min")])
def test_elapsed_minutes_round_a_half_up(sec, text):
    """3630 s is 60.5 min and 3690 s 61.5 min: both go up (61, 62), not to the even neighbour."""
    assert platform._elapsed(sec) == text


def test_schedule_rows_name_the_condition_and_its_run_count_on_one_line():
    labels = texts(platform.schedule(RUNS, MANIFEST))
    assert "A · 1 run" in labels and "C · 2 runs" in labels


def test_schedule_empty_escaped_deterministic_and_within_the_width_range():
    assert platform.schedule([], MANIFEST) == ""
    odd = [dict(RUNS[0], task="P-<b>&")]
    svg = platform.schedule(odd, MANIFEST)
    assert "P-<b>&" not in svg and "P-&lt;b&gt;&amp;" in svg
    assert platform.schedule(RUNS, MANIFEST) == platform.schedule(RUNS, MANIFEST)
    assert 320 <= _width(platform.schedule(RUNS, MANIFEST)) <= 960


def test_schedule_without_manifest_totals_still_draws_the_runs():
    svg = platform.schedule(RUNS, {})
    assert len(_bars(svg)) == 4
    assert "planned" not in " ".join(texts(svg))


ENTRIES = [
    {"path": "MANIFEST.json", "bytes": 28185, "is_dir": False, "hash": "ab" * 32},
    {"path": "inputs", "bytes": 401500, "is_dir": True, "hash": None},
    {"path": "inputs/hashes.json", "bytes": 3657, "is_dir": False, "hash": "cd" * 32},
    {"path": "inputs/plan.jsonl", "bytes": 397766, "is_dir": False, "hash": "4cdc5dec" + "0" * 56},
    {"path": "m/A/medium", "bytes": 2_000_000, "is_dir": True, "hash": None, "n_files": 100},
]
CHAIN = [{"from": "inputs/plan.jsonl", "to": "MANIFEST.json", "field": "plan_sha256", "ok": True},
         {"from": "inputs/plan.jsonl", "to": "inputs/hashes.json", "field": "plan_file_sha256", "ok": True},
         {"from": "not/listed", "to": "MANIFEST.json", "field": "ignored", "ok": True}]


def _rows(svg: str) -> dict[str, dict]:
    """Name text by label: x of the label and the bar width of its row (bars carry the path in their title)."""
    out = {}
    for el in _root(svg).iter(f"{NS}rect"):
        if _classes(el) == ["muted"] and _tip(el):
            out[_tip(el).split(":")[0]] = {"x": attr_float(el, "x"), "y": attr_float(el, "y"),
                                           "w": attr_float(el, "width"), "tip": _tip(el)}
    return out


def test_tree_has_one_row_per_entry_with_the_size_in_bytes():
    svg = platform.file_tree(ENTRIES, CHAIN)
    rows = _rows(svg)
    assert list(rows) == [e["path"] for e in ENTRIES]
    assert f"{THIN.join(['397', '766'])} bytes" in rows["inputs/plan.jsonl"]["tip"]
    labels = texts(svg)
    for n in (397_766, 28_185, 3_657, 2_000_000):
        assert f"{n:,}".replace(",", THIN) + " B" in labels
    assert "100 files" in " ".join(labels)


def test_tree_rows_run_top_to_bottom_in_the_order_of_the_entries():
    ys = [r["y"] for r in _rows(platform.file_tree(ENTRIES, CHAIN)).values()]
    assert ys == sorted(ys) and len(set(ys)) == len(ys)


def test_tree_bar_widths_follow_the_byte_order_on_a_log_axis():
    rows = _rows(platform.file_tree(ENTRIES, CHAIN))
    assert rows["inputs/hashes.json"]["w"] < rows["MANIFEST.json"]["w"] < rows["inputs/plan.jsonl"]["w"]
    assert rows["inputs/plan.jsonl"]["w"] < rows["m/A/medium"]["w"]
    assert "log" in " ".join(texts(platform.file_tree(ENTRIES, CHAIN)))


def _text_x(svg: str, label: str) -> float:
    xs = [attr_float(t, "x") for t in _root(svg).iter(f"{NS}text") if "".join(t.itertext()) == label]
    assert xs, label
    return xs[0]


def test_tree_indents_children_under_their_folder():
    svg = platform.file_tree(ENTRIES, CHAIN)
    assert _text_x(svg, "plan.jsonl") > _text_x(svg, "inputs/") > 0
    assert _text_x(svg, "MANIFEST.json") == _text_x(svg, "inputs/")


def test_tree_shows_the_start_of_each_hash_and_one_arrow_per_listed_chain_link():
    svg = platform.file_tree(ENTRIES, CHAIN)
    assert "4cdc5dec" in " ".join(texts(svg))
    arrows = [t.text for t in _root(svg).iter(f"{NS}title") if (t.text or "").startswith("hash of ")]
    assert arrows == ["hash of inputs/plan.jsonl is recorded in plan_sha256 of MANIFEST.json",
                      "hash of inputs/plan.jsonl is recorded in plan_file_sha256 of inputs/hashes.json"]
    notes = " ".join(texts(svg))
    assert "plan_sha256" in notes and "plan_file_sha256" in notes and "ignored" not in notes


def test_tree_empty_escaped_deterministic():
    assert platform.file_tree([], CHAIN) == ""
    odd = [{"path": "a<b>&.txt", "bytes": 5, "is_dir": False, "hash": None}]
    svg = platform.file_tree(odd, [])
    assert "a<b>" not in svg and "a&lt;b&gt;&amp;.txt" in svg
    assert platform.file_tree(ENTRIES, CHAIN) == platform.file_tree(ENTRIES, CHAIN)
    assert 320 <= _width(platform.file_tree(ENTRIES, CHAIN)) <= 960


# ---------------------------------------------------------------- two widths


def test_schedule_is_drawn_at_the_width_it_is_given(fig_width, fits):
    fits(platform.schedule(RUNS, MANIFEST, width=fig_width), fig_width)


def test_tree_is_drawn_at_the_width_it_is_given(fig_width, fits):
    fits(platform.file_tree(ENTRIES, CHAIN, width=fig_width), fig_width)


def test_the_tests_read_the_figures_whatever_order_the_attributes_come_in(monkeypatch):
    """A harmless reorder in base._attrs (class last) changes nothing the tests read."""
    wanted = (_bars(platform.schedule(RUNS, MANIFEST)), _rows(platform.file_tree(ENTRIES, CHAIN)))
    original = base._attrs

    def class_last(cls="", tip="", **kw):
        attrs, title = original(cls, tip, **kw)
        return re.sub(r'^( class="[^"]*")(.*)$', r"\2\1", attrs), title

    monkeypatch.setattr(base, "_attrs", class_last)
    assert re.search(r'height="[\d.]+" class="c-A">', platform.schedule(RUNS, MANIFEST))  # the patch took effect
    assert (_bars(platform.schedule(RUNS, MANIFEST)), _rows(platform.file_tree(ENTRIES, CHAIN))) == wanted


def test_a_link_whose_hash_does_not_match_gets_a_mismatch_mark():
    chain = [dict(CHAIN[0], ok=False), CHAIN[1]]
    svg = platform.file_tree(ENTRIES, chain)
    marks = [_tip(el) for el in _root(svg).iter() if "bad" in _classes(el)]
    assert any("plan_sha256" in t and "does not match" in t for t in marks)
    assert "does not match" not in platform.file_tree(ENTRIES, CHAIN)


def test_a_run_without_wall_time_or_cost_is_drawn_and_says_not_recorded():
    runs = [dict(RUNS[0], seconds=None, cost=None), *RUNS[1:]]
    svg = platform.schedule(runs, MANIFEST)
    assert "not recorded" in svg and "P-x-01" in svg


def test_tree_axis_ticks_lie_on_the_axis_line_under_the_bars():
    """The bytes axis starts at the bars (bar_x), not at 0: every tick and label sits on the baseline, and a bar of
    1 000 000 bytes ends at the tick labelled 1 000 000."""
    entries = [*ENTRIES, {"path": "one_mb.bin", "bytes": 1_000_000, "is_dir": False, "hash": None}]
    root = _root(platform.file_tree(entries, CHAIN))
    base_line = [e for e in root.iter(f"{NS}line") if _classes(e) == ["ax"]
                 and attr_float(e, "y1") == attr_float(e, "y2") and attr_float(e, "x2") - attr_float(e, "x1") > 40]
    assert len(base_line) == 1
    lo, hi = attr_float(base_line[0], "x1"), attr_float(base_line[0], "x2")
    bar_x = min(attr_float(e, "x") for e in root.iter(f"{NS}rect") if _classes(e) == ["muted"])
    assert lo == bar_x
    ticks = [e for e in root.iter(f"{NS}line")
             if _classes(e) == ["ax"] and attr_float(e, "y2") - attr_float(e, "y1") == 4]
    assert ticks
    assert all(lo - 0.01 <= attr_float(t, "x1") <= hi + 0.01 for t in ticks)
    labels = {re.sub(r"\D", "", "".join(t.itertext())): attr_float(t, "x") for t in root.iter(f"{NS}text")
              if _classes(t) == ["mut"] and re.fullmatch(r"[\d   ]+", "".join(t.itertext()).strip() or "x")}
    bar = next(e for e in root.iter(f"{NS}rect") if _tip(e).startswith("one_mb.bin"))
    assert abs(attr_float(bar, "x") + attr_float(bar, "width") - labels["1000000"]) < 0.01


def _spread_runs(days: float, n: int = 30) -> list[dict]:
    """`n` runs spread evenly over `days` days (a resumed run set after a long pause)."""
    import datetime
    t0 = datetime.datetime(2026, 10, 1, 8, 0, tzinfo=datetime.UTC)
    return [{"cond": "ABC"[i % 3], "task": f"P-x-{i:02d}", "seconds": 60.0, "cost": 0.1,
             "start": (t0 + datetime.timedelta(seconds=days * 86400 * i / (n - 1))).isoformat()} for i in range(n)]


@pytest.mark.parametrize("days", [3, 12, 20, 45, 120])
def test_the_time_axis_labels_never_overlap_however_long_the_run_set_ran(days, fig_width, fits):
    fits(platform.schedule(_spread_runs(days), {}, width=fig_width), fig_width)


def test_ticks_of_a_span_of_weeks_step_by_days_not_by_hours():
    ticks = platform._ticks(0.0, 20 * 86400.0, 8)
    assert 2 <= len(ticks) <= 8 and {round(b - a) for a, b in zip(ticks, ticks[1:], strict=False)} <= {
        2 * 86400, 4 * 86400, 7 * 86400}


def test_the_bytes_axis_of_a_huge_file_keeps_its_labels_apart(fig_width, fits):
    entries = [*ENTRIES, {"path": "big.bin", "bytes": 900_000_000, "is_dir": False, "hash": None}]
    fits(platform.file_tree(entries, CHAIN, width=fig_width), fig_width)
