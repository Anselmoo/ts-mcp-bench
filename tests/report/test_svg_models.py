from __future__ import annotations

import inspect
import math
import re
import xml.etree.ElementTree as ET

import pytest
from svg_helpers import attr_or_zero as _num
from svg_helpers import classes as _cls
from svg_helpers import root as _root

from tsbench.report.svg import base, models

NS = "{http://www.w3.org/2000/svg}"
LONG = "llama-4-maverick-17b-128e-instruct-fp8"


def _cell(k: int, n: int, lo: float, hi: float) -> dict:
    return {"k": k, "n": n, "tasks": n, "share": k / n, "lo": lo, "hi": hi}


def _pair(diff: float, lo: float, hi: float) -> dict:
    return {"diff": diff, "lo": lo, "hi": hi, "p": 0.01, "n": 50}


def _row(model: str, a: dict | None, b: dict | None, c: dict | None, **paired: dict) -> dict:
    cells = {k: v for k, v in (("A", a), ("B", b), ("C", c)) if v is not None}
    return {"model": model, "endpoint": "gateway", "n_runs": 3, "n_evaluable": 3, "k": 1, "k_planned": 3,
            "conds": list(cells), "cells": cells, "paired": {k.replace("_", " − "): v for k, v in paired.items()}}


ROWS = [
    _row("qwen3.5-397b-a17b", _cell(10, 50, 0.11, 0.33), _cell(9, 50, 0.10, 0.31), _cell(41, 50, 0.69, 0.91),
         C_A=_pair(0.62, 0.46, 0.76), C_B=_pair(0.64, 0.50, 0.78), B_A=_pair(-0.02, -0.16, 0.12)),
    _row(LONG, _cell(6, 40, 0.07, 0.29), _cell(8, 40, 0.10, 0.35), _cell(30, 40, 0.60, 0.86),
         C_A=_pair(0.62, 0.45, 0.75), C_B=_pair(0.55, 0.40, 0.70), B_A=_pair(0.08, -0.05, 0.21)),
    _row("gemma-4-31b-it", _cell(0, 10, 0.0, 0.28), None, _cell(7, 10, 0.40, 0.89), C_A=_pair(0.7, 0.3, 0.9)),
]


def _texts(root: ET.Element) -> list[tuple[str, float, float]]:
    return [("".join(t.itertext()).replace("\u00a0", " "), _num(t, "x"), _num(t, "y")) for t in root.iter(f"{NS}text")]


def _x_of(root: ET.Element, label: str) -> float:
    return next(x for s, x, _ in _texts(root) if s == label)


def _ribbons(root: ET.Element) -> list[ET.Element]:
    return [e for e in root.iter(f"{NS}rect") if "ribbon" in _cls(e)]


def _marks(root: ET.Element, cond: str) -> list[ET.Element]:
    """The markers of the plot (the legend row at the top has its own)."""
    return [e for e in root.iter() if f"c-{cond}" in _cls(e) and "ribbon" not in _cls(e) and _center_y(e) > 20]


def _center(el: ET.Element) -> float:
    if el.tag == f"{NS}circle":
        return _num(el, "cx")
    if el.tag == f"{NS}rect":
        return _num(el, "x") + _num(el, "width") / 2
    xs = [float(p.split(",")[0]) for p in (el.get("points") or "").split()]
    return sum(xs) / len(xs)


def _center_y(el: ET.Element) -> float:
    if el.tag == f"{NS}circle":
        return _num(el, "cy")
    if el.tag == f"{NS}rect":
        return _num(el, "y") + _num(el, "height") / 2
    ys = [float(p.split(",")[1]) for p in (el.get("points") or "").split()]
    return (min(ys) + max(ys)) / 2


def _name_texts(root: ET.Element) -> list[ET.Element]:
    """The lines of the model names: bold texts at x = 0, top down."""
    return [t for t in root.iter(f"{NS}text") if _num(t, "x") == 0 and "b" in _cls(t)]


def _box(t: ET.Element) -> tuple[float, float, float, float]:
    s = "".join(t.itertext())
    w = len(s) * base.TEXT_PX * (0.6 if "b" in _cls(t) else 0.55)
    x, y = _num(t, "x"), _num(t, "y")
    anchor = t.get("text-anchor")
    x0 = x - w if anchor == "end" else x - w / 2 if anchor == "middle" else x
    return x0, y - base.TEXT_PX * 0.8, x0 + w, y + base.TEXT_PX * 0.25


def _overlaps(svg: str) -> list[tuple[str, str]]:
    boxes = [("".join(t.itertext()), _box(t)) for t in _root(svg).iter(f"{NS}text")]
    bad = []
    for i, (sa, a) in enumerate(boxes):
        for sb, b in boxes[i + 1:]:
            if a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]:
                bad.append((sa, sb))
    return bad


# ---------------------------------------------------------------- model_shares


def test_shares_empty() -> None:
    assert models.model_shares([]) == ""


def test_shares_width_is_the_width_given(fig_width, fits) -> None:
    svg = models.model_shares(ROWS, width=fig_width)
    fits(svg, fig_width)
    root = _root(svg)
    assert root.get("width") == base.coord(fig_width)
    assert root.get("viewBox", "").split()[2] == base.coord(fig_width)


def test_shares_default_width_is_full() -> None:
    assert _root(models.model_shares(ROWS)).get("width") == "960"


def test_shares_names_wrap_and_are_never_cut(fig_width) -> None:
    svg = models.model_shares(ROWS, width=fig_width)
    assert "…" not in svg and "..." not in svg
    names = _name_texts(_root(svg))
    joined = "".join("".join(t.itertext()) for t in names)
    for model in (r["model"] for r in ROWS):
        assert model in joined
    if fig_width == base.HALF_W:
        assert len(names) > len(ROWS)  # the long names took more than one line
        assert all(_box(t)[2] <= fig_width * 0.4 for t in names)


def test_shares_models_stand_top_down_in_input_order() -> None:
    root = _root(models.model_shares(ROWS))
    ys = {s: y for s, x, y in _texts(root) if x == 0}
    assert ys["qwen3.5-397b-a17b"] < ys["llama-4-maverick-17b-128e-"] < ys["gemma-4-31b-it"]


def test_shares_values_text() -> None:
    strings = [s for s, _, _ in _texts(_root(models.model_shares(ROWS)))]
    for want in ("20 % · 10/50", "18 % · 9/50", "82 % · 41/50", "15 % · 6/40", "75 % · 30/40", "0 % · 0/10",
                 "70 % · 7/10"):
        assert want in strings


def test_shares_values_sit_right_of_the_plot(fig_width) -> None:
    root = _root(models.model_shares(ROWS, width=fig_width))
    x100 = _x_of(root, "100")
    values = [t for t in root.iter(f"{NS}text") if " · " in "".join(t.itertext())]
    assert len({_num(t, "x") for t in values}) == 1  # one right-aligned column
    assert all(_box(t)[0] > x100 + 8 for t in values)
    assert all(_box(t)[2] <= fig_width for t in values)


def test_shares_points_sit_on_a_zero_to_hundred_axis(fig_width) -> None:
    root = _root(models.model_shares(ROWS, width=fig_width))
    x0, x100 = _x_of(root, "0"), _x_of(root, "100")
    a = sorted(_marks(root, "A"), key=_center_y)
    assert [_center(m) for m in a] == pytest.approx([x0 + s * (x100 - x0) for s in (0.2, 0.15, 0.0)], abs=0.1)
    c = sorted(_marks(root, "C"), key=_center_y)
    assert [_center(m) for m in c] == pytest.approx([x0 + s * (x100 - x0) for s in (0.82, 0.75, 0.7)], abs=0.1)


def test_shares_interval_bar_runs_from_lo_to_hi(fig_width) -> None:
    root = _root(models.model_shares(ROWS, width=fig_width))
    x0, x100 = _x_of(root, "0"), _x_of(root, "100")
    c = sorted((r for r in _ribbons(root) if "c-C" in _cls(r)), key=lambda r: _num(r, "y"))
    assert len(c) == 3
    assert _num(c[0], "x") == pytest.approx(x0 + 0.69 * (x100 - x0), abs=0.1)
    assert _num(c[0], "width") == pytest.approx(0.22 * (x100 - x0), abs=0.1)
    assert _num(c[2], "x") == pytest.approx(x0 + 0.40 * (x100 - x0), abs=0.1)
    m = sorted(_marks(root, "A"), key=_center_y)[0]  # the bar is centred on the row of its marker
    a = sorted((r for r in _ribbons(root) if "c-A" in _cls(r)), key=lambda r: _num(r, "y"))[0]
    assert _num(a, "y") + _num(a, "height") / 2 == pytest.approx(_center_y(m), abs=0.1)


def test_shares_a_missing_condition_draws_nothing() -> None:
    root = _root(models.model_shares(ROWS))
    assert len(_marks(root, "B")) == 2  # gemma has no B
    assert len([r for r in _ribbons(root) if "c-B" in _cls(r)]) == 2
    assert len(_marks(root, "A")) == 3 and len(_marks(root, "C")) == 3
    # the conditions of one model keep their lines: A above B above C
    ys = [_center_y(sorted(_marks(root, c), key=_center_y)[0]) for c in "ABC"]
    assert ys == sorted(ys)


def test_shares_a_model_without_cells_keeps_its_name_only() -> None:
    root = _root(models.model_shares([_row("only-name", None, None, None)]))
    assert "only-name" in [s for s, _, _ in _texts(root)]
    assert not _ribbons(root) and not _marks(root, "A")


def test_shares_legend_lists_the_conditions() -> None:
    root = _root(models.model_shares(ROWS))
    top = [(s, x) for s, x, y in _texts(root) if y < 20]
    assert [s for s, _ in sorted(top, key=lambda t: t[1])] == ["A", "B", "C"]


def test_shares_axis_label_and_ticks() -> None:
    strings = [s for s, _, _ in _texts(_root(models.model_shares(ROWS)))]
    assert "share correct" in strings
    for t in ("0", "25", "50", "75", "100"):
        assert t in strings


def test_shares_titles_carry_the_exact_numbers() -> None:
    titles = [(t.text or "").replace("\u00a0", " ") for t in _root(models.model_shares(ROWS)).iter(f"{NS}title")]
    assert any("qwen3.5-397b-a17b" in t and "C" in t and "41/50" in t and "82 %" in t and "69–91" in t for t in titles)


def test_shares_long_names_do_not_overlap_other_text(fig_width) -> None:
    assert _overlaps(models.model_shares(ROWS, width=fig_width)) == []


def test_shares_height_grows_with_models() -> None:
    h1 = _num(_root(models.model_shares(ROWS[:1])), "height")
    h3 = _num(_root(models.model_shares(ROWS)), "height")
    assert h3 > h1 + 100


def test_shares_escape_and_determinism() -> None:
    rows = [_row("<i>&model", _cell(1, 2, 0.1, 0.9), None, None)]
    svg = models.model_shares(rows)
    assert "<i>" not in svg
    _root(svg)
    assert svg == models.model_shares(list(rows))


def test_the_builder_names_no_colour() -> None:
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b", inspect.getsource(models))


# ---------------------------------------------------------------- model_paired


def test_paired_empty() -> None:
    assert models.model_paired([]) == ""


def test_paired_width_is_the_width_given(fig_width, fits) -> None:
    svg = models.model_paired(ROWS, width=fig_width)
    fits(svg, fig_width)
    assert _root(svg).get("width") == base.coord(fig_width)


def test_paired_default_width_is_full() -> None:
    assert _root(models.model_paired(ROWS)).get("width") == "960"


def test_paired_names_wrap_and_are_never_cut(fig_width) -> None:
    svg = models.model_paired(ROWS, width=fig_width)
    assert "…" not in svg
    names = _name_texts(_root(svg))
    joined = "".join("".join(t.itertext()) for t in names)
    for model in (r["model"] for r in ROWS):
        assert model in joined
    if fig_width == base.HALF_W:
        assert all(_box(t)[2] <= fig_width * 0.4 for t in names)


def test_paired_values_text() -> None:
    strings = [s for s, _, _ in _texts(_root(models.model_paired(ROWS)))]
    for want in ("+62 pp", "+64 pp", "−2 pp", "+55 pp", "+8 pp", "+70 pp"):
        assert want in strings


def test_paired_axis_is_minus_hundred_to_plus_hundred_with_zero_line(fig_width) -> None:
    root = _root(models.model_paired(ROWS, width=fig_width))
    xm, xz, xp = _x_of(root, "−100"), _x_of(root, "0"), _x_of(root, "+100")
    assert xz == pytest.approx((xm + xp) / 2, abs=0.1)
    zero = [e for e in root.iter(f"{NS}line") if "zero" in _cls(e)]
    assert len(zero) == 1 and _num(zero[0], "x1") == pytest.approx(xz, abs=0.1)
    assert "percentage points" in [s for s, _, _ in _texts(root)]


def test_paired_points_and_bars_sit_on_the_axis(fig_width) -> None:
    root = _root(models.model_paired(ROWS, width=fig_width))
    xm, xz, xp = _x_of(root, "−100"), _x_of(root, "0"), _x_of(root, "+100")

    def at(d: float) -> float:
        return xz + d * (xp - xm) / 2
    cs = sorted(_marks(root, "C"), key=_center_y)  # C − A and C − B of model 1 and 2, C − A of model 3
    assert [_center(m) for m in cs] == pytest.approx([at(d) for d in (0.62, 0.64, 0.62, 0.55, 0.7)], abs=0.1)
    bs = sorted(_marks(root, "B"), key=_center_y)  # B − A has the marker of B
    assert [_center(m) for m in bs] == pytest.approx([at(-0.02), at(0.08)], abs=0.1)
    ba = sorted((r for r in _ribbons(root) if "c-B" in _cls(r)), key=lambda r: _num(r, "y"))[0]
    assert _num(ba, "x") == pytest.approx(at(-0.16), abs=0.1)
    assert _num(ba, "width") == pytest.approx(at(0.12) - at(-0.16), abs=0.1)
    assert _num(ba, "x") < xz < _num(ba, "x") + _num(ba, "width")


def test_paired_rows_are_c_a_c_b_b_a_per_model() -> None:
    root = _root(models.model_paired(ROWS))
    labels = [(s, y) for s, x, y in _texts(root) if s in ("C − A", "C − B", "B − A")]
    assert [s for s, _ in labels] == ["C − A", "C − B", "B − A"] * 2 + ["C − A"]
    assert [y for _, y in labels] == sorted(y for _, y in labels)


def test_paired_a_missing_pair_draws_nothing() -> None:
    root = _root(models.model_paired(ROWS))
    assert len(_ribbons(root)) == 7  # 3 + 3 + 1
    assert len([s for s, _, _ in _texts(root) if s.endswith(" pp")]) == 7


def test_paired_shows_only_the_pairs_of_the_row() -> None:
    root = _root(models.model_paired([_row("m", None, None, None, B_A=_pair(0.1, 0.0, 0.2))]))
    assert [s for s, _, _ in _texts(root) if s in ("C − A", "C − B", "B − A")] == ["B − A"]


def test_paired_titles_carry_the_exact_numbers() -> None:
    titles = [t.text or "" for t in _root(models.model_paired(ROWS)).iter(f"{NS}title")]
    assert any("qwen3.5-397b-a17b" in t and "C − A" in t and "+62 pp" in t and "+46 to +76" in t for t in titles)
    assert any("B − A" in t and "−2 pp" in t and "−16 to +12" in t for t in titles)


def test_paired_legend_lists_the_conditions() -> None:
    root = _root(models.model_paired(ROWS))
    top = [(s, x) for s, x, y in _texts(root) if y < 20]
    assert [s for s, _ in sorted(top, key=lambda t: t[1])] == ["A", "B", "C"]


def test_paired_long_names_do_not_overlap_other_text(fig_width) -> None:
    assert _overlaps(models.model_paired(ROWS, width=fig_width)) == []


def test_paired_values_sit_right_of_the_plot(fig_width) -> None:
    root = _root(models.model_paired(ROWS, width=fig_width))
    xp = _x_of(root, "+100")
    values = [t for t in root.iter(f"{NS}text") if "".join(t.itertext()).endswith(" pp")]
    assert len({_num(t, "x") for t in values}) == 1
    assert all(_box(t)[0] > xp + 8 and _box(t)[2] <= fig_width for t in values)


def test_paired_escape_and_determinism() -> None:
    rows = [_row("<i>&model", None, None, None, C_A=_pair(0.1, 0.0, 0.2))]
    svg = models.model_paired(rows)
    assert "<i>" not in svg
    _root(svg)
    assert svg == models.model_paired(list(rows))


def test_paired_minus_sign_and_rounded_zero() -> None:
    rows = [_row("m", None, None, None, B_A=_pair(-0.004, -0.1, 0.1), C_A=_pair(-0.25, -0.3, -0.2))]
    strings = [s for s, _, _ in _texts(_root(models.model_paired(rows)))]
    assert "0 pp" in strings and "−25 pp" in strings


def test_interval_ends_and_paired_points_round_a_half_up() -> None:
    rows = [_row("m", _cell(1, 40, 0.025, 0.035), None, _cell(30, 40, 0.6, 0.9), C_A=_pair(0.025, -0.025, 0.045))]
    root = _root(models.model_shares(rows))
    assert any("95 % CI 3–4 %" in (t.text or "") for t in root.iter(f"{NS}title"))
    titles = [t.text or "" for t in _root(models.model_paired(rows)).iter(f"{NS}title")]
    assert any("+3 pp, 95 % CI −3 to +5 pp" in t for t in titles)


# ---------------------------------------------------------------- bubbles


def _point(model: str, cond: str, tokens: float | None, k: int, n: int) -> dict:
    return {"model": model, "label": model.split("-")[-1], "cond": cond, "tokens": tokens, "share": k / n, "k": k,
            "n": n}


POINTS = [_point("m-a", "A", 800, 10, 40), _point("m-a", "B", 9000, 20, 40), _point("m-a", "C", 3000, 30, 40),
          _point("m-b", "A", 1500, 5, 10), _point("m-b", "B", None, 5, 10), _point("m-b", "C", 40000, 9, 10)]


def _bubbles(root: ET.Element) -> list[ET.Element]:
    return [e for e in root.iter(f"{NS}circle") if "bubble" in _cls(e)]


def test_a_bubble_stands_at_its_tokens_and_share_and_has_the_colour_of_its_condition():
    root = _root(models.model_bubbles(POINTS))
    bubbles = _bubbles(root)
    assert len(bubbles) == 5  # the point without tokens has no bubble
    by_tip = {"".join(b.itertext()).replace("\u00a0", " ").replace("\u2009", " "): b for b in bubbles}
    half = by_tip["m-a, B: median 9 000 output tokens, 50 % correct, 20/40 runs"]
    quarter = by_tip["m-a, A: median 800 output tokens, 25 % correct, 10/40 runs"]
    high = by_tip["m-b, C: median 40 000 output tokens, 90 % correct, 9/10 runs"]
    assert {"c-B", "k-B"} <= set(_cls(half))
    assert _num(high, "cy") < _num(half, "cy") < _num(quarter, "cy")
    assert _num(quarter, "cx") < _num(half, "cx") < _num(high, "cx")
    # log axis: the distances go with the ratios of the tokens
    along = (_num(half, "cx") - _num(quarter, "cx")) / (_num(high, "cx") - _num(quarter, "cx"))
    assert along == pytest.approx(math.log(9000 / 800) / math.log(40000 / 800), abs=0.002)


def test_bubble_area_is_proportional_to_the_runs():
    bubbles = _bubbles(_root(models.model_bubbles(POINTS)))
    big = max(_num(b, "r") for b in bubbles)
    small = min(_num(b, "r") for b in bubbles)
    assert (big / small) ** 2 == pytest.approx(4, rel=0.01)  # 40 runs against 10


def test_the_bubbles_name_each_model_once_and_say_what_the_area_is():
    svg = models.model_bubbles(POINTS)
    labels = [s for s, _, _ in _texts(_root(svg))]
    assert labels.count("a") == 1 and labels.count("b") == 1
    assert "area = runs, largest 40" in labels
    assert "median output tokens per run, log scale" in labels


def test_bubbles_without_a_point_draw_nothing():
    assert models.model_bubbles([]) == ""
    assert models.model_bubbles([_point("m", "A", None, 1, 2)]) == ""


# ---------------------------------------------------------------- heat map


def _heat_row(model: str, conds: list[str], k: dict, n_by: dict | None = None) -> dict:
    return {"model": model, "conds": conds,
            "classes": [{"class": c, "k": v, "n": 4, "n_by": (n_by or {}).get(c, {})} for c, v in k.items()]}


HEAT = [_heat_row("m-a", ["A", "C"], {"x": {"A": 1, "C": 4}, "y": {"A": 0, "C": 2}}, {"y": {"A": 0}}),
        _heat_row("m-b", ["A", "B", "C"], {"x": {"A": 2, "B": 3, "C": 4}})]


def _ramp(p: float) -> tuple[str, str]:
    return f"#{int(p * 255):02x}0000", "#ffffff"


def test_the_heat_map_has_one_panel_per_condition_and_one_cell_per_model_and_class():
    svg = models.class_heat(HEAT, _ramp)
    labels = [s for s, _, _ in _texts(_root(svg))]
    assert [s for s in labels if s.startswith("Condition")] == ["Condition A", "Condition B", "Condition C"]
    cells = [e for e in _root(svg).iter(f"{NS}rect")]
    assert len(cells) == 3 * 2 * 2
    assert "4/4" in labels and "1/4" in labels


def test_a_heat_cell_is_shaded_by_its_share_and_a_cell_without_a_run_says_so():
    svg = models.class_heat(HEAT, _ramp)
    assert 'style="fill:#ff0000"' in svg  # 4 of 4
    assert 'style="fill:#3f0000"' in svg  # 1 of 4
    labels = [s for s, _, _ in _texts(_root(svg))]
    # m-a: y under A (n_by 0), x and y under B; m-b: y under A, B and C
    assert labels.count("no run") == 3 + 3
    assert "0/" not in " ".join(s for s in labels if s != "no run")


def test_the_heat_map_tip_names_model_condition_class_and_counts():
    assert "m-b, B, x: 3 of 4 tasks (75\u00a0%)" in models.class_heat(HEAT, _ramp)


def test_a_heat_map_without_classes_is_empty():
    assert models.class_heat([], _ramp) == ""
