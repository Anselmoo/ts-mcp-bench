from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET

from svg_helpers import classes as _classes
from svg_helpers import root as _root
from svg_helpers import texts as _texts
from svg_helpers import tip as _tip

from tsbench.report.svg.base import number
from tsbench.report.svg.ledger import task_ledger

NS = "{http://www.w3.org/2000/svg}"


def _ratio(v: float | None, ok: bool) -> dict:
    return {"kind": "ratio", "value": v, "ok": ok, "need": None, "text": None}


def _share(v: float | None, need: float, ok: bool) -> dict:
    return {"kind": "share", "value": v, "ok": ok, "need": need, "text": None}


def _scope(text: str, ok: bool) -> dict:
    return {"kind": "scope", "value": None, "ok": ok, "need": None, "text": text}


CLASSES = [
    {"class": "closed_form", "k": {"A": 1, "B": 2, "C": 2}, "n": 2, "tasks": [
        {"task": "P-closed_form-01", "cells": {"A": _ratio(3.6, False), "B": _ratio(0.05, True),
                                               "C": _ratio(1.0, True)}},
        {"task": "P-closed_form-02", "cells": {"A": _ratio(0.8, True), "B": _ratio(24.0, False),
                                               "C": _ratio(None, False)}},
    ]},
    {"class": "diagram", "k": {"A": 0, "B": 1, "C": 1}, "n": 2, "tasks": [
        {"task": "P-diagram-01", "cells": {"A": _share(0.38, 0.95, False), "B": _share(1.0, 0.95, True),
                                           "C": _share(0.0, 0.95, False)}},
        {"task": "P-diagram-02", "cells": {"A": _share(0.5, 0.95, False), "B": _share(0.96, 0.95, True),
                                           "C": _share(None, 0.95, False)}},
    ]},
    {"class": "out_of_scope", "k": {"A": 1, "B": 0, "C": 1}, "n": 3, "tasks": [
        {"task": "P-out_of_scope-01", "cells": {"A": _scope("named", True), "B": _scope("missed", False),
                                                 "C": _scope("refused", False)}},
    ]},
]


def _cells(svg: str) -> dict[tuple[str, str], ET.Element]:
    """The group of every cell, keyed by (task, condition), read from its tooltip `task · cond · ...`."""
    out: dict[tuple[str, str], ET.Element] = {}
    for g in _root(svg).iter(f"{NS}g"):
        parts = _tip(g).split(" · ")
        if len(parts) >= 3 and parts[0].startswith("P-"):
            out[(parts[0], parts[1])] = g
    return out


def _fl(el: ET.Element, key: str) -> float:
    return float(el.get(key, "0"))


def _bar_and_track(g: ET.Element) -> tuple[ET.Element, ET.Element]:
    rects = list(g.iter(f"{NS}rect"))
    track = next(r for r in rects if "band" in _classes(r))
    bar = next(r for r in rects if "ok" in _classes(r) or "bad" in _classes(r) or "na" in _classes(r))
    return bar, track


def test_ledger_header_uses_the_tasks_with_an_evaluable_run_per_condition():
    blocks = [{**CLASSES[0], "n_by": {"A": 1, "B": 2, "C": 2}}]
    root = _root(task_ledger(blocks))
    texts = ["".join(t.itertext()) for t in root.iter(f"{NS}text")]
    assert "1/1" in texts and texts.count("2/2") == 2
    titles = ["".join(t.itertext()) for t in root.iter(f"{NS}title")]
    assert "closed_form · A: 1 of 1 task correct" in titles


def test_empty() -> None:
    assert task_ledger([]) == ""
    assert task_ledger([], width=464) == ""


def test_deterministic() -> None:
    assert task_ledger(CLASSES) == task_ledger(CLASSES)
    assert task_ledger(CLASSES, width=464) == task_ledger(CLASSES, width=464)


def test_one_cell_per_task_and_condition() -> None:
    cells = _cells(task_ledger(CLASSES))
    assert len(cells) == 3 * 5
    assert ("P-closed_form-02", "B") in cells


def test_order_as_given_in_one_column_at_half_width() -> None:
    svg = task_ledger(CLASSES, width=464)
    texts = [t for t in _root(svg).iter(f"{NS}text")]
    ys = {t.text: _fl(t, "y") for t in texts if t.text in ("closed_form", "diagram", "out_of_scope")}
    assert ys["closed_form"] < ys["diagram"] < ys["out_of_scope"]
    row_y = {key: _fl(next(g.iter(f"{NS}rect")), "y") for key, g in _cells(svg).items() if key[1] == "A"}
    order = ["P-closed_form-01", "P-closed_form-02", "P-diagram-01", "P-diagram-02", "P-out_of_scope-01"]
    assert [row_y[(t, "A")] for t in order] == sorted(row_y.values())
    assert ys["diagram"] < row_y[("P-diagram-01", "A")]


def test_conditions_run_left_to_right() -> None:
    cells = _cells(task_ledger(CLASSES))
    xs = [_fl(_bar_and_track(cells[("P-closed_form-01", c)])[1], "x") for c in "ABC"]
    assert xs == sorted(xs) and len(set(xs)) == 3


def test_ratio_titles_carry_the_numbers() -> None:
    cells = _cells(task_ledger(CLASSES))
    assert "error ÷ tolerance 3.60" in _tip(cells[("P-closed_form-01", "A")])
    assert "error ÷ tolerance 24.00" in _tip(cells[("P-closed_form-02", "B")])
    assert "error ÷ tolerance 0.05" in _tip(cells[("P-closed_form-01", "B")])
    assert "no value" in _tip(cells[("P-closed_form-02", "C")])


def test_share_titles_carry_share_and_required_share() -> None:
    cells = _cells(task_ledger(CLASSES))
    tip = _tip(cells[("P-diagram-01", "A")])
    assert "items correct 38.0 %" in tip and "required 95 %" in tip
    assert "items correct 96.0 %" in _tip(cells[("P-diagram-02", "B")])


def test_ok_and_bad_classes_follow_the_flag() -> None:
    cells = _cells(task_ledger(CLASSES))
    for key, ok in [(("P-closed_form-01", "A"), False), (("P-closed_form-01", "B"), True),
                    (("P-diagram-01", "B"), True), (("P-diagram-01", "A"), False),
                    (("P-out_of_scope-01", "A"), True), (("P-out_of_scope-01", "B"), False)]:
        bar, _ = _bar_and_track(cells[key])
        assert ("ok" in _classes(bar)) is ok and ("bad" in _classes(bar)) is not ok, key


def test_missing_value_is_drawn_as_no_value_and_a_dash() -> None:
    svg = task_ledger(CLASSES)
    cells = _cells(svg)
    bar, _ = _bar_and_track(cells[("P-closed_form-02", "C")])
    assert "na" in _classes(bar)
    assert "–" in [t.text for t in cells[("P-closed_form-02", "C")].iter(f"{NS}text")]
    bar, _ = _bar_and_track(cells[("P-diagram-02", "C")])
    assert "na" in _classes(bar)


def test_scope_cells_print_their_word() -> None:
    cells = _cells(task_ledger(CLASSES))
    for cond, word in [("A", "named"), ("B", "missed"), ("C", "refused")]:
        g = cells[("P-out_of_scope-01", cond)]
        assert word in [t.text for t in g.iter(f"{NS}text")]
        assert word in _tip(g)


def test_ratio_bar_is_on_a_log_axis_with_the_line_at_one() -> None:
    cells = _cells(task_ledger(CLASSES))
    bar, track = _bar_and_track(cells[("P-closed_form-01", "C")])  # ratio 1.0
    width = _fl(track, "width")
    assert abs(_fl(bar, "width") - width / 2) < 0.02
    tick = next(ln for ln in cells[("P-closed_form-01", "C")].iter(f"{NS}line"))
    assert abs(_fl(tick, "x1") - (_fl(track, "x") + width / 2)) < 0.02
    bar, track = _bar_and_track(cells[("P-closed_form-02", "B")])  # ratio 24: (log10 24 + 2) / 4 of the track
    assert abs(_fl(bar, "width") - width * (math.log10(24) + 2) / 4) < 0.02


def test_ratio_bar_is_clamped_to_the_axis() -> None:
    big = [{"class": "c", "k": {"A": 0, "B": 0, "C": 0}, "n": 1, "tasks": [
        {"task": "P-c-01", "cells": {"A": _ratio(5000.0, False), "B": _ratio(0.0001, True), "C": _ratio(1.0, True)}}]}]
    cells = _cells(task_ledger(big))
    bar, track = _bar_and_track(cells[("P-c-01", "A")])
    assert abs(_fl(bar, "width") - _fl(track, "width")) < 0.02
    bar, _ = _bar_and_track(cells[("P-c-01", "B")])
    assert 0 < _fl(bar, "width") <= 1.01  # a hairline, never an empty bar
    assert f"error ÷ tolerance {number(5000.0, 2)}" in _tip(cells[("P-c-01", "A")])


def test_share_bar_has_the_line_at_the_required_share() -> None:
    cells = _cells(task_ledger(CLASSES))
    g = cells[("P-diagram-01", "A")]
    bar, track = _bar_and_track(g)
    assert abs(_fl(bar, "width") - 0.38 * _fl(track, "width")) < 0.02
    tick = next(ln for ln in g.iter(f"{NS}line"))
    assert abs(_fl(tick, "x1") - (_fl(track, "x") + 0.95 * _fl(track, "width"))) < 0.02


def test_numbers_printed_beside_the_bars() -> None:
    cells = _cells(task_ledger(CLASSES))

    def printed(key: tuple[str, str]) -> list[str]:
        return [t.text or "" for t in cells[key].iter(f"{NS}text")]

    assert printed(("P-closed_form-01", "A")) == ["3.6"]
    assert printed(("P-closed_form-02", "B")) == ["24"]
    assert printed(("P-closed_form-01", "B")) == ["<0.1"]
    assert printed(("P-diagram-01", "A")) == ["38%"]
    assert printed(("P-diagram-01", "B")) == ["100%"]


def test_class_headers_carry_k_of_n_per_condition() -> None:
    svg = task_ledger(CLASSES, width=464)
    counts = [t for t in _root(svg).iter(f"{NS}text") if re.fullmatch(r"\d+/\d+", t.text or "")]
    counts.sort(key=lambda t: (_fl(t, "y"), _fl(t, "x")))
    assert [t.text for t in counts] == ["1/2", "2/2", "2/2", "0/2", "1/2", "1/2", "1/3", "0/3", "1/3"]
    tips = [_tip(g) for g in _root(svg).iter(f"{NS}g")]
    assert "closed_form · A: 1 of 2 tasks correct" in tips
    assert "out_of_scope · C: 1 of 3 tasks correct" in tips


def test_condition_markers_head_each_column() -> None:
    svg = task_ledger(CLASSES, width=464)
    heads = [t.text for t in _root(svg).iter(f"{NS}text") if t.text in ("A", "B", "C")]
    assert heads == ["A", "B", "C"]


def test_full_size_ledger_fits_the_limits() -> None:
    many = [{"class": f"class_{i:02d}", "k": {"A": 0, "B": 0, "C": 0}, "n": 4, "tasks": [
        {"task": f"P-class_{i:02d}-{j + 1:02d}", "cells": {c: _ratio(2.0, False) for c in "ABC"}} for j in range(4)]}
        for i in range(14)]
    for w in (960, 464):
        root = _root(task_ledger(many, width=w))
        assert _fl(root, "width") == w
        assert len(_cells(task_ledger(many, width=w))) == 14 * 4 * 3


def test_a_class_stays_in_one_column() -> None:
    many = [{"class": f"class_{i:02d}", "k": {"A": 0, "B": 0, "C": 0}, "n": 3, "tasks": [
        {"task": f"P-class_{i:02d}-{j + 1:02d}", "cells": {c: _ratio(2.0, False) for c in "ABC"}} for j in range(3)]}
        for i in range(6)]
    svg = task_ledger(many, width=960)
    cells = _cells(svg)
    for i in range(6):
        xs = {_fl(_bar_and_track(cells[(f"P-class_{i:02d}-{j + 1:02d}", "A")])[1], "x") for j in range(3)}
        assert len(xs) == 1


def test_notes_fit_the_width() -> None:
    for w in (960, 464):
        svg = task_ledger(CLASSES, width=w)
        w = _fl(_root(svg), "width")
        for t in _root(svg).iter(f"{NS}text"):
            if "mut" in _classes(t):
                assert _fl(t, "x") + len(t.text or "") * 11 * 0.5 <= w + 1, t.text


def test_escaping() -> None:
    bad = [{"class": "a<b&c", "k": {"A": 0, "B": 0, "C": 0}, "n": 1, "tasks": [
        {"task": 'P-"x"<1>-01', "cells": {c: _ratio(2.0, False) for c in "ABC"}}]}]
    svg = task_ledger(bad)
    assert "a<b" not in svg and 'P-"x"<1>' not in svg
    assert "a&lt;b&amp;c" in svg
    assert 'a<b&c' in _texts(svg)
    assert any(key[0] == 'P-"x"<1>-01' for key in _cells(svg))


def test_title_names_no_figure_number() -> None:
    svg = task_ledger(CLASSES)
    assert "Figure" not in svg


def test_a_condition_without_a_run_of_the_task_is_drawn_as_not_run():
    classes = [{"class": "curve", "k": {"A": 1, "B": 0, "C": 0}, "n": 1, "n_by": {"A": 1, "B": 0, "C": 0},
                "tasks": [{"task": "P-curve-01", "cells": {"A": {"kind": "ratio", "value": 0.5, "ok": True,
                                                                 "need": None, "text": None}}}]}]
    svg = task_ledger(classes)
    assert "P-curve-01 · B · not run" in svg and "P-curve-01 · C · not run" in svg


def test_a_condition_without_any_evaluable_run_has_no_column_head_or_cell():
    """`k` carries the conditions with an evaluable run: here A and C. B is neither headed nor drawn as 0 of n."""
    classes = [{"class": "curve", "k": {"A": 1, "C": 0}, "n": 1,
                "tasks": [{"task": "P-curve-01", "cells": {"A": _ratio(0.5, True), "C": _ratio(3.0, False)}}]}]
    svg = task_ledger(classes)
    root = _root(svg)
    titles = ["".join(t.itertext()) for t in root.iter(f"{NS}title")]
    assert "curve · A: 1 of 1 task correct" in titles and "curve · C: 0 of 1 task correct" in titles
    assert not [t for t in titles if "· B" in t or " B " in t or t.endswith(" B")]
    assert "Outcome and error size of 1 tasks under A and C" in titles
    assert "B" not in _texts(svg)
    assert " B: " not in svg


def test_a_condition_without_a_run_in_a_class_says_no_run_not_0_of_0():
    """The condition has runs in other classes (it is a column), none in this class: `no run`, as in class_dots."""
    classes = [{"class": "curve", "k": {"A": 1, "B": 0, "C": 1}, "n": 1, "n_by": {"A": 1, "B": 0, "C": 1},
                "tasks": [{"task": "P-curve-01", "cells": {"A": _ratio(0.5, True), "C": _ratio(0.5, True)}}]},
               {"class": "diagram", "k": {"A": 0, "B": 1, "C": 0}, "n": 1, "n_by": {"A": 1, "B": 1, "C": 1},
                "tasks": [{"task": "P-diagram-01", "cells": {"A": _ratio(3.0, False), "B": _ratio(0.5, True),
                                                             "C": _ratio(3.0, False)}}]}]
    svg = task_ledger(classes)
    root = _root(svg)
    texts = ["".join(t.itertext()) for t in root.iter(f"{NS}text")]
    titles = ["".join(t.itertext()) for t in root.iter(f"{NS}title")]
    assert "0/0" not in texts and "no run" in texts
    assert "curve · B: no run" in titles
    assert not [t for t in titles if "0 of 0" in t]
    assert "diagram · B: 1 of 1 task correct" in titles


# ---------------------------------------------------------------- two widths


def test_ledger_is_drawn_at_the_width_it_is_given(fig_width, fits) -> None:
    fits(task_ledger(CLASSES, width=fig_width), fig_width)


def test_a_half_width_ledger_has_fewer_columns() -> None:
    many = [{"class": f"class_{i:02d}", "k": {"A": 0, "B": 0, "C": 0}, "n": 4, "tasks": [
        {"task": f"P-class_{i:02d}-{j + 1:02d}", "cells": {c: _ratio(2.0, False) for c in "ABC"}} for j in range(4)]}
        for i in range(14)]

    def columns(svg: str) -> int:
        return len({_fl(_bar_and_track(g)[1], "x") for (task, cond), g in _cells(svg).items() if cond == "A"})

    full, half = task_ledger(many, width=960), task_ledger(many, width=464)
    assert columns(half) < columns(full)
    assert len(_cells(full)) == len(_cells(half)) == 14 * 4 * 3


def test_the_bar_class_follows_ok_never_the_ratio() -> None:
    classes = [{"class": "numerical", "k": {"A": 1, "B": 0, "C": 0}, "n": 1, "tasks": [
        {"task": "P-numerical-01", "cells": {"A": _ratio(4.0, True), "B": _ratio(0.2, False),
                                             "C": _ratio(None, False)}}]}]
    cells = _cells(task_ledger(classes))
    assert "ok" in _classes(_bar_and_track(cells[("P-numerical-01", "A")])[0])
    assert "bad" in _classes(_bar_and_track(cells[("P-numerical-01", "B")])[0])


def test_rows_are_labelled_with_the_full_task_id_and_link_to_the_task_row() -> None:
    """the row label is the task id (not "01"), linked to `#task-<id>`."""
    svg = task_ledger(CLASSES, task_href=lambda t: f"#task-{t}")
    texts = _texts(svg)
    assert "P-closed_form-01" in texts and "P-diagram-02" in texts and "01" not in texts
    links = [a.get("href") for a in _root(svg).iter(f"{NS}a")]
    assert {"#task-P-closed_form-01", "#task-P-diagram-01", "#task-P-out_of_scope-01"} <= set(links)


def test_a_scope_word_sits_beside_its_bar_not_inside() -> None:
    cells = _cells(task_ledger(CLASSES))
    g = cells[("P-out_of_scope-01", "C")]
    bar, track = _bar_and_track(g)
    word = next(t for t in g.iter(f"{NS}text") if t.text == "refused")
    assert _fl(word, "x") >= _fl(track, "x") + _fl(track, "width")
