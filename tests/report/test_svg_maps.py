from __future__ import annotations

import xml.etree.ElementTree as ET

from svg_helpers import classes as _classes
from svg_helpers import root as _root
from svg_helpers import texts as _texts
from svg_helpers import tip as _tip

from tsbench.report.svg import maps
from tsbench.report.svg.maps import run_map

NS = "{http://www.w3.org/2000/svg}"
CATS = [("correct", "correct"), ("gross", "gross error"), ("several", "several parameters wrong"),
        ("dq", "Dq wrong"), ("bc", "B or C wrong"), ("limit", "limit missed")]


def _strips(svg: str) -> list[ET.Element]:
    return [r for r in _root(svg).iter(f"{NS}rect") if "tile" in _classes(r)]


def _box(r: ET.Element) -> tuple[float, float, float, float]:
    x, y = float(r.get("x", "0")), float(r.get("y", "0"))
    return x, y, x + float(r.get("width", "0")), y + float(r.get("height", "0"))


def _overlap(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    w = min(a[2], b[2]) - max(a[0], b[0])
    h = min(a[3], b[3]) - max(a[1], b[1])
    return w * h if w > 0.05 and h > 0.05 else 0.0  # coordinates are rounded to 0.01


# ---------------------------------------------------------------- run_map


def _run(cond: str, cls: str, task: str, value: float, outcome: str) -> dict:
    return {"cond": cond, "class": cls, "task": task, "value": value, "outcome": outcome}


RUNS = [
    _run("A", "closed", "P-closed-01", 0.10, "gross"),
    _run("A", "closed", "P-closed-02", 0.30, "correct"),
    _run("A", "diag", "P-diag-01", 0.05, "several"),
    _run("A", "diag", "P-diag-02", 0.55, "bc"),
    _run("B", "closed", "P-closed-01", 0.40, "gross"),
    _run("B", "closed", "P-closed-02", 0.20, "dq"),
    _run("B", "diag", "P-diag-01", 0.90, "limit"),
    _run("B", "diag", "P-diag-02", 0.10, "correct"),
    _run("C", "closed", "P-closed-01", 1.20, "correct"),
    _run("C", "closed", "P-closed-02", 0.60, "correct"),
    _run("C", "diag", "P-diag-01", 2.00, "correct"),
    _run("C", "diag", "P-diag-02", 0.80, "bc"),
]


def test_run_map_empty() -> None:
    assert run_map([], CATS, "USD") == ""
    assert run_map(RUNS, [], "USD") == ""
    assert run_map([_run("A", "x", "t", 0.0, "correct")], CATS, "USD") == ""


def test_run_map_one_tile_per_run() -> None:
    assert len(_strips(run_map(RUNS, CATS, "USD"))) == len(RUNS)


def test_run_map_tile_area_is_proportional_to_the_value() -> None:
    svg = run_map(RUNS, CATS, "USD", nd=2)
    by_tip = {_tip(r): r for r in _strips(svg)}
    ratios = []
    for run in RUNS:
        tile = next(r for tip, r in by_tip.items() if tip.startswith(f"{run['task']} · {run['cond']}"))
        x0, y0, x1, y1 = _box(tile)
        ratios.append((x1 - x0) * (y1 - y0) / run["value"])
    assert max(ratios) / min(ratios) < 1.06


def test_run_map_colour_and_tooltip() -> None:
    svg = run_map(RUNS, CATS, "USD", nd=2)
    by_tip = {_tip(r): _classes(r) for r in _strips(svg)}
    assert "ok" in by_tip["P-diag-01 · C: correct · 2.00 USD"]
    assert "e1" in by_tip["P-closed-01 · A: gross error · 0.10 USD"]
    assert "e5" in by_tip["P-diag-02 · C: B or C wrong · 0.80 USD"]  # a kind keeps its class (here no "items")


def test_run_map_condition_headers_carry_the_totals() -> None:
    svg = run_map(RUNS, CATS, "USD", nd=2)
    texts = _texts(svg)
    assert any(t.startswith("A · 1.00 USD") and "0.30 on correct" in t for t in texts)
    assert any(t.startswith("B · 1.60 USD") and "0.10 on correct" in t for t in texts)
    assert any(t.startswith("C · 4.60 USD") and "3.80 on correct" in t for t in texts)


def test_run_map_conditions_are_framed_with_their_cap() -> None:
    svg = run_map(RUNS, CATS, "USD")
    frames = [r for r in _root(svg).iter(f"{NS}rect") if "frame" in _classes(r)]
    tips = [_tip(f) for f in frames]
    for cond in "ABC":
        assert any(t.startswith(f"{cond}: ") for t in tips)
    caps = [r for r in _root(svg).iter(f"{NS}rect") if any(c in ("c-A", "c-B", "c-C") for c in _classes(r))
            and r.find(f"{NS}title") is None and float(r.get("height", "0")) < 6]
    assert len(caps) >= 3


def test_run_map_tiles_do_not_overlap_and_stay_inside() -> None:
    svg = run_map(RUNS, CATS, "USD")
    root = _root(svg)
    width, height = float(root.get("width", "0")), float(root.get("height", "0"))
    boxes = [_box(r) for r in _strips(svg)]
    for i, a in enumerate(boxes):
        assert a[0] >= 0 and a[1] >= 0 and a[2] <= width and a[3] <= height
        for b in boxes[i + 1:]:
            assert _overlap(a, b) < 0.5


def test_run_map_condition_area_follows_the_total() -> None:
    svg = run_map(RUNS, CATS, "USD")
    area = {"A": 0.0, "B": 0.0, "C": 0.0}
    for r in _strips(svg):
        x0, y0, x1, y1 = _box(r)
        area[_tip(r).split(" · ")[1][0]] += (x1 - x0) * (y1 - y0)
    assert area["C"] > area["B"] > area["A"]
    assert abs(area["C"] / area["A"] - 4.6) < 0.3


def test_run_map_drops_runs_without_a_value_and_says_so() -> None:
    runs = [*RUNS, _run("A", "diag", "P-diag-09", 0.0, "gross")]
    svg = run_map(runs, CATS, "USD")
    assert len(_strips(svg)) == len(RUNS)
    assert any("1 run without a value" in t for t in _texts(svg))


def test_run_map_writes_one_run_in_the_singular() -> None:
    svg = run_map([_run("A", "closed", "P-closed-01", 0.10, "correct")], CATS, "USD")
    words = " ".join(_texts(svg)) + " ".join(el.text or "" for el in _root(svg).iter(f"{NS}title"))
    assert "1 run" in words and "1 runs" not in words


def test_run_map_escapes_names() -> None:
    odd = [_run("A", "a&b", "P-<1>", 1.0, "correct")]
    svg = run_map(odd, CATS, "U&S")
    assert "a&amp;b" in svg and "U&amp;S" in svg
    ET.fromstring(svg)


def test_run_map_is_deterministic() -> None:
    assert run_map(RUNS, CATS, "USD") == run_map(list(RUNS), list(CATS), "USD")


# ---------------------------------------------------------------- two widths


def test_run_map_is_drawn_at_the_width_it_is_given(fig_width, fits) -> None:
    fits(run_map(RUNS, CATS, "USD", width=fig_width), fig_width)


def test_six_error_kinds_get_six_classes() -> None:
    from tsbench.report.svg import maps
    cats = [("correct", "correct"), *((f"k{i}", f"kind {i}") for i in range(6))]
    assert len(set(maps._category_classes(cats).values())) == 7


def test_the_seven_report_error_kinds_get_seven_classes_in_the_cost_map() -> None:
    from tsbench.report import facts
    cats = [*facts.CATEGORIES, facts.OTHER]
    classes = maps._category_classes(cats)
    assert len(set(classes.values())) == 8
    assert classes["other"] != classes["gross"]
