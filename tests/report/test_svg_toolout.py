from __future__ import annotations

import math
import random
import xml.etree.ElementTree as ET

import pytest
from svg_helpers import classes as _classes
from svg_helpers import root as _root
from svg_helpers import texts as _texts
from svg_helpers import tip as _tip

from tsbench.report.svg.base import number
from tsbench.report.svg.toolout import tool_output, tool_rows

NS = "{http://www.w3.org/2000/svg}"


def _run(cond: str, task: str, correct: bool, *calls: tuple[str, int]) -> dict:
    return {"cond": cond, "task": task, "correct": correct, "calls": [{"tool": t, "chars": n} for t, n in calls]}


RUNS = [
    _run("A", "P-a-01", True),
    _run("B", "P-a-01", False, ("Bash", 1000), ("Bash", 500)),
    _run("B", "P-a-02", True, ("Bash", 2500)),
    _run("C", "P-a-01", True, ("ts_terms_table_data", 300_000), ("ts_terms_table_data", 453_000),
         ("ts_plot_png", 0), ("StructuredOutput_like", 10)),
    _run("C", "P-a-02", False, ("ts_terms_table_data", 20_000), ("ts_fit_spectrum", 1234), ("ts_plot_png", 0)),
    _run("C", "P-a-03", True, ("ts_fit_spectrum", 845), ("ts_fit_spectrum", 0)),
]


def _fl(el: ET.Element, key: str) -> float:
    return float(el.get(key, "0"))


def _leaves(svg: str) -> list[ET.Element]:
    return [c for c in _root(svg).iter(f"{NS}circle") if "ok" in _classes(c) or "bad" in _classes(c)]


def _tools(svg: str) -> list[ET.Element]:
    return [c for c in _root(svg).iter(f"{NS}circle") if "ax" in _classes(c)]


def _titles(svg: str) -> list[str]:
    return [_tip(e) for e in _root(svg).iter() if e.tag != f"{NS}svg" and _tip(e)]


def test_empty() -> None:
    assert tool_output([]) == ""
    assert tool_output([_run("A", "P-a-01", True)]) == ""
    assert tool_output([_run("C", "P-a-01", True, ("ts_plot_png", 0))]) == ""


def test_deterministic() -> None:
    assert tool_output(RUNS) == tool_output(RUNS)
    assert tool_output(RUNS) == tool_output(list(RUNS))


def test_one_leaf_per_condition_tool_and_run_with_text() -> None:
    leaves = _leaves(tool_output(RUNS))
    # B: Bash x 2 runs; C: ts_terms_table_data x 2, ts_fit_spectrum x 2, StructuredOutput_like x 1
    assert len(leaves) == 2 + 2 + 2 + 1


def test_leaf_area_is_proportional_to_characters() -> None:
    svg = tool_output(RUNS)
    by_chars = {}
    for c in _leaves(svg):
        tip = _tip(c)
        chars = int(tip.split(": ")[1].split(" characters")[0].replace(" ", "").replace(" ", ""))
        by_chars[tip] = (chars, _fl(c, "r") ** 2)
    ratios = [r2 / n for n, r2 in by_chars.values() if r2 >= 1]  # coordinates are rounded to 0.01 px
    assert max(ratios) / min(ratios) < 1.01
    assert len(by_chars) == 7


def test_leaf_titles_carry_condition_tool_task_numbers_and_outcome() -> None:
    svg = tool_output(RUNS)
    tips = [_tip(c) for c in _leaves(svg)]
    want = f"C · ts_terms_table_data · P-a-01: {number(753_000)} characters returned in 2 calls · run correct"
    assert want in tips
    want = f"C · ts_terms_table_data · P-a-02: {number(20_000)} characters returned in 1 call · run not correct"
    assert want in tips
    # a call of 0 characters is counted as a call, not drawn as text
    assert f"C · ts_fit_spectrum · P-a-03: {number(845)} characters returned in 2 calls · run correct" in tips


def test_ok_and_bad_follow_the_run() -> None:
    for c in _leaves(tool_output(RUNS)):
        tip = _tip(c)
        assert ("ok" in _classes(c)) is tip.endswith("run correct")
        assert ("bad" in _classes(c)) is tip.endswith("run not correct")


def test_tool_circles_carry_totals() -> None:
    tips = [_tip(c) for c in _tools(tool_output(RUNS))]
    assert f"C · ts_terms_table_data: {number(773_000)} characters returned in 3 calls, 2 runs" in tips
    assert f"B · Bash: {number(4000)} characters returned in 3 calls, 2 runs" in tips
    assert f"C · ts_fit_spectrum: {number(2079)} characters returned in 3 calls, 2 runs" in tips


def test_labels_have_condition_tool_characters_and_calls() -> None:
    svg = tool_output(RUNS)
    titles = _titles(svg)
    assert "C · ts_terms_table_data · 773k chars · 3 calls" in titles
    assert "B · Bash · 4.0k chars · 3 calls" in titles
    assert "C · ts_fit_spectrum · 2.1k chars · 3 calls" in titles
    assert "C · StructuredOutput_like · 10 chars · 1 call" in titles
    texts = _texts(svg)
    assert "C · ts_terms_table_data" in texts and "773k chars · 3 calls" in texts


def test_character_format() -> None:
    runs = [_run("C", "P-a-01", True, ("t1", 845), ("t2", 5_200), ("t3", 1_400_000), ("t4", 1))]
    titles = _titles(tool_output(runs))
    assert "C · t1 · 845 chars · 1 call" in titles
    assert "C · t2 · 5.2k chars · 1 call" in titles
    assert "C · t3 · 1.4M chars · 1 call" in titles
    assert "C · t4 · 1 char · 1 call" in titles


def test_image_only_tools_are_listed_not_drawn() -> None:
    svg = tool_output(RUNS)
    assert "No text returned, not drawn: C ts_plot_png (2 calls)" in _texts(svg)
    assert not any("ts_plot_png" in t for t in _titles(svg))
    assert not any("ts_plot_png" in t for t in _texts(svg) if not t.startswith("No text"))


def test_no_note_without_image_only_tools() -> None:
    assert not any(t.startswith("No text") for t in _texts(tool_output(RUNS[:3])))


def test_conditions_without_text_are_absent() -> None:
    tips = [_tip(c) for c in _tools(tool_output(RUNS))]
    assert not any(t.startswith("A") for t in tips)


def test_root_and_condition_circles_carry_totals() -> None:
    svg = tool_output(RUNS)
    titles = _titles(svg)
    assert f"B: {number(4000)} characters returned in 3 calls, 1 tool, 2 runs" in titles
    total = 4000 + 753_000 + 20_000 + 2079 + 10
    assert any(t.startswith(f"{number(total)} characters returned") for t in titles)


def test_width_within_the_limits() -> None:
    root = _root(tool_output(RUNS))
    assert 320 <= _fl(root, "width") <= 960


def _many_runs() -> list[dict]:
    rnd = random.Random(7)
    tools = [f"ts_tool_{i:02d}_long_name" for i in range(12)]
    runs = []
    for i in range(40):
        calls = [(rnd.choice(tools), rnd.choice([30, 400, 3_000, 12_000, 60_000])) for _ in range(rnd.randint(1, 4))]
        runs.append(_run("C", f"P-m-{i:02d}", rnd.random() < 0.6, *calls))
    for i in range(7):
        runs.append(_run("B", f"P-m-{i:02d}", rnd.random() < 0.3, ("Bash", rnd.choice([500, 4_000, 20_000]))))
    return runs


def _seg_dist(px: float, py: float, x1: float, y1: float, x2: float, y2: float) -> float:
    dx, dy = x2 - x1, y2 - y1
    t = 0.0 if dx == dy == 0 else max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


def _segments(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> bool:
    def ccw(p: tuple[float, float], q: tuple[float, float], r: tuple[float, float]) -> float:
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])

    p1, p2, p3, p4 = (a[0], a[1]), (a[2], a[3]), (b[0], b[1]), (b[2], b[3])
    return ccw(p1, p2, p3) * ccw(p1, p2, p4) < 0 and ccw(p3, p4, p1) * ccw(p3, p4, p2) < 0


def test_leaders_do_not_cross_other_tool_circles() -> None:
    svg = tool_output(_many_runs())
    root = _root(svg)
    tools = _tools(svg)
    lines = list(root.iter(f"{NS}line"))
    assert len(lines) == len(tools) == 13
    for ln in lines:
        x1, y1, x2, y2 = (_fl(ln, k) for k in ("x1", "y1", "x2", "y2"))
        own = [c for c in tools if abs(math.hypot(x1 - _fl(c, "cx"), y1 - _fl(c, "cy")) - _fl(c, "r")) < 0.6]
        assert len(own) == 1, "a leader starts on the edge of its tool circle"
        for c in tools:
            if c is own[0]:
                continue
            assert _seg_dist(_fl(c, "cx"), _fl(c, "cy"), x1, y1, x2, y2) >= _fl(c, "r") - 0.6, _tip(c)


def test_leaders_do_not_cross_each_other() -> None:
    lines = [(_fl(ln, "x1"), _fl(ln, "y1"), _fl(ln, "x2"), _fl(ln, "y2"))
             for ln in _root(tool_output(_many_runs())).iter(f"{NS}line")]
    for i, a in enumerate(lines):
        for b in lines[i + 1:]:
            assert not _segments(a, b)


def test_labels_sit_outside_the_root_circle_and_apart() -> None:
    svg = tool_output(_many_runs())
    root = _root(svg)
    hull = next(c for c in root.iter(f"{NS}circle") if "grid" in _classes(c))
    cx, cy, r = _fl(hull, "cx"), _fl(hull, "cy"), _fl(hull, "r")
    boxes = []
    for t in root.iter(f"{NS}text"):
        if t.text is None or "·" not in t.text and "chars" not in t.text:
            continue
        if t.text.startswith("No text"):
            continue
        w = len(t.text) * 11 * 0.5
        x, y = _fl(t, "x"), _fl(t, "y")
        x0, x1 = (x - w, x) if t.get("text-anchor") == "end" else (x, x + w)
        boxes.append((x0, y - 9, x1, y + 3))
        assert x0 >= 0 and x1 <= _fl(root, "width"), t.text
        for px in (x0, x1):
            for py in (y - 9, y + 3):
                assert math.hypot(px - cx, py - cy) > r, t.text
    assert len(boxes) == 26
    for i, a in enumerate(boxes):
        for b in boxes[i + 1:]:
            assert not (min(a[2], b[2]) - max(a[0], b[0]) > 0.5 and min(a[3], b[3]) - max(a[1], b[1]) > 0.5)


def test_labels_are_on_both_sides() -> None:
    svg = tool_output(_many_runs())
    anchors = {t.get("text-anchor", "start") for t in _root(svg).iter(f"{NS}text") if "chars" in (t.text or "")}
    assert anchors == {"start", "end"}


def test_all_marks_inside_the_view_box() -> None:
    root = _root(tool_output(_many_runs()))
    w, h = _fl(root, "width"), _fl(root, "height")
    for c in root.iter(f"{NS}circle"):
        assert _fl(c, "cx") - _fl(c, "r") >= -0.5 and _fl(c, "cx") + _fl(c, "r") <= w + 0.5
        assert _fl(c, "cy") - _fl(c, "r") >= -0.5 and _fl(c, "cy") + _fl(c, "r") <= h + 0.5
    for t in root.iter(f"{NS}text"):
        assert 0 <= _fl(t, "y") <= h


def test_one_condition_one_tool() -> None:
    svg = tool_output([_run("B", "P-a-01", True, ("Bash", 100))])
    assert len(_leaves(svg)) == 1 and len(_tools(svg)) == 1
    assert "B · Bash · 100 chars · 1 call" in _titles(svg)


def test_escaping() -> None:
    runs = [_run("C", 'P-"a"<1>', True, ("t<b>&", 500)), _run("C", "P-b", False, ("t<b>&", 100))]
    svg = tool_output(runs)
    assert "t<b>" not in svg and 'P-"a"<1>' not in svg
    assert "t&lt;b&gt;&amp;" in svg
    assert any("C · t<b>&" in t for t in _titles(svg))
    assert any('P-"a"<1>' in t for t in _titles(svg))


def test_no_figure_number() -> None:
    assert "Figure" not in tool_output(RUNS)


# ---------------------------------------------------------------- two widths


def test_tool_output_is_drawn_at_the_width_it_is_given(fig_width, fits) -> None:
    fits(tool_output(RUNS, width=fig_width), fig_width)
    fits(tool_output(_many_runs(), width=fig_width), fig_width)


def _kruns() -> list[dict]:
    """Three runs (k = 1, 2, 3) of one task that each call ts_fit_spectrum; only k = 1 is correct."""
    return [{**_run("C", "P-a-01", ok, ("ts_fit_spectrum", 1000)), "k": k}
            for k, ok in ((1, True), (2, False), (3, False))]


def test_repetitions_of_a_task_are_separate_leaves_with_their_own_outcome() -> None:
    svg = tool_output(_kruns())
    leaves = _leaves(svg)
    assert len(leaves) == 3
    assert sorted(("ok" in _classes(c), "bad" in _classes(c)) for c in leaves) == [(False, True), (False, True),
                                                                                  (True, False)]
    tips = [_tip(c) for c in leaves]
    assert len(set(tips)) == 3 and all("1 call ·" in t for t in tips)
    assert any("P-a-01 · k2:" in t and t.endswith("run not correct") for t in tips)


def test_runs_are_counted_per_repetition() -> None:
    svg = tool_output(_kruns())
    assert f"{number(3000)} characters returned in 3 calls, 3 runs" in _titles(svg)
    assert any(t.startswith("C · ts_fit_spectrum:") and t.endswith("3 calls, 3 runs") for t in _titles(svg))


def test_a_run_set_with_one_repetition_keeps_the_plain_task_name() -> None:
    runs = [{**r, "k": 1} for r in RUNS]
    assert [_tip(c) for c in _leaves(tool_output(runs))] == [_tip(c) for c in _leaves(tool_output(RUNS))]


def test_kchars_round_a_half_up_in_both_ranges():
    from tsbench.report.svg.toolout import _kchars
    assert [_kchars(n) for n in (5250, 5350, 12500, 13500, 999_499, 999_500)] == [
        "5.3k", "5.4k", "13k", "14k", "999k", "1.0M"]
    assert [_kchars(n) for n in (845, 1_250_000, 1_350_000)] == ["845", "1.3M", "1.4M"]


# ---------------------------------------------------------------- several models


TOOL_MODELS = [("m-a", [{"cond": "C", "task": "t", "k": 1, "correct": True,
                         "calls": [{"tool": "ts_fit", "chars": 1200}, {"tool": "ts_fit", "chars": 800},
                                   {"tool": "ts_plot", "chars": 0}]}]),
               ("m-b", [{"cond": "B", "task": "t", "k": 1, "correct": False, "calls": [{"tool": "Bash", "chars": 500}]},
                        {"cond": "C", "task": "t", "k": 1, "correct": True,
                         "calls": [{"tool": "ts_fit", "chars": 4000}]}])]


def test_tool_rows_have_a_line_per_model_and_tool_on_one_axis():
    svg = tool_rows(TOOL_MODELS)
    words = _texts(svg)
    assert words.count("C · ts_fit") == 2 and words.count("B · Bash") == 2 and words.count("C · ts_plot") == 2
    assert "2.0k chars · 2 calls" in words and "4.0k chars · 1 call" in words
    assert words.count("no call") == 2  # m-a has no Bash, m-b no ts_plot
    assert "m-a · C · ts_fit: " + number(2000) + " characters returned in 2 calls" in svg


def test_a_tool_bar_is_as_long_as_its_characters():
    svg_root = _root(tool_rows(TOOL_MODELS))
    bars = {_tip(e): float(e.attrib["width"]) for e in svg_root.iter("{http://www.w3.org/2000/svg}rect") if _tip(e)}
    a = next(v for k, v in bars.items() if k.startswith("m-a · C · ts_fit"))
    b = next(v for k, v in bars.items() if k.startswith("m-b · C · ts_fit"))
    assert b / a == pytest.approx(2.0, rel=0.01)


def test_tool_rows_without_a_call_are_empty():
    assert tool_rows([("m", [{"cond": "A", "task": "t", "calls": []}])]) == ""
