from __future__ import annotations

import xml.etree.ElementTree as ET

from svg_helpers import root as _root
from svg_helpers import tip as _tip

from tsbench.report.svg.scatter import _place_labels, coverage_mutation

NS = "{http://www.w3.org/2000/svg}"
PTS = [
    {"module": "tsbench.run.doctor", "coverage": 91.0, "score": 89.2, "mutants": 816},
    {"module": "tsbench.score.numeric", "coverage": 99.0, "score": 98.0, "mutants": 400},
    {"module": "tsbench.figures.plot", "coverage": 85.0, "score": 46.3, "mutants": 100},
    {"module": "tsbench.core.schema", "coverage": 100.0, "score": 100.0, "mutants": 25},
]
UNMUT = [{"module": "tsbench.a", "coverage": 100.0}, {"module": "tsbench.b", "coverage": 100.0},
         {"module": "tsbench.c", "coverage": 70.0}]


def _points(svg: str) -> dict[str, ET.Element]:
    return {_tip(c).split(":")[0]: c for c in _root(svg).iter(f"{NS}circle") if c.find(f"{NS}title") is not None}


def test_empty() -> None:
    assert coverage_mutation([], []) == ""


def test_one_point_per_mutated_module() -> None:
    assert len(_points(coverage_mutation(PTS, UNMUT))) == 4


def test_position_follows_the_data() -> None:
    p = _points(coverage_mutation(PTS, UNMUT))
    xs = {k: float(v.get("cx", "0")) for k, v in p.items()}
    ys = {k: float(v.get("cy", "0")) for k, v in p.items()}
    by_cov = ["tsbench.figures.plot", "tsbench.run.doctor", "tsbench.score.numeric", "tsbench.core.schema"]
    assert [xs[k] for k in by_cov] == sorted(xs[k] for k in by_cov)
    assert [ys[k] for k in by_cov[::-1]] == sorted(ys[k] for k in by_cov)


def test_area_is_proportional_to_mutants() -> None:
    p = _points(coverage_mutation(PTS, UNMUT))
    r = {k: float(v.get("r", "0")) for k, v in p.items()}
    # the radius grows with the square root of the mutants (plus a fixed minimum), so it is monotone
    assert r["tsbench.run.doctor"] > r["tsbench.score.numeric"] > r["tsbench.figures.plot"] > r["tsbench.core.schema"]


def test_class_by_score() -> None:
    p = _points(coverage_mutation(PTS, UNMUT))
    assert "g0" in p["tsbench.core.schema"].get("class", "").split()
    assert "g2" in p["tsbench.run.doctor"].get("class", "").split()
    assert "g4" in p["tsbench.figures.plot"].get("class", "").split()


def test_titles_carry_the_numbers() -> None:
    p = _points(coverage_mutation(PTS, UNMUT))
    tip = _tip(p["tsbench.run.doctor"])
    assert "91.0" in tip and "89.2" in tip and "816" in tip


def test_rug_for_unmutated_files() -> None:
    svg = coverage_mutation(PTS, UNMUT)
    texts = [t.text or "" for t in _root(svg).iter(f"{NS}text")]
    assert any("not mutated" in t for t in texts)
    ticks = [ln for ln in _root(svg).iter(f"{NS}line") if "not mutated" in _tip(ln)]
    assert len(ticks) == 2  # coverage 100 (two files) and 70
    both = next(t for t in ticks if "tsbench.a" in _tip(t))
    assert "tsbench.b" in _tip(both)
    # the unmutated files are not points
    assert not any(k in ("tsbench.a", "tsbench.b", "tsbench.c") for k in _points(svg))


def test_axes_labelled() -> None:
    texts = [t.text or "" for t in _root(coverage_mutation(PTS, UNMUT)).iter(f"{NS}text")]
    assert any("line coverage" in t for t in texts)
    assert any("mutation score" in t for t in texts)


def test_labels_do_not_overlap() -> None:
    svg = coverage_mutation(PTS, UNMUT)
    prefixes = ("run.", "score.", "figures.", "core.")
    labels = [t for t in _root(svg).iter(f"{NS}text") if (t.text or "").startswith(prefixes)]
    assert labels
    boxes = []
    for t in labels:
        x, y = float(t.get("x", "0")), float(t.get("y", "0"))
        w = len(t.text or "") * 11 * 0.55
        x0 = x - w if t.get("text-anchor") == "end" else x - w / 2 if t.get("text-anchor") == "middle" else x
        boxes.append((x0, y - 11, w, 11))
    for i, a in enumerate(boxes):
        for b in boxes[i + 1:]:
            assert a[0] + a[2] <= b[0] or b[0] + b[2] <= a[0] or a[1] + a[3] <= b[1] or b[1] + b[3] <= a[1]


def test_place_labels_avoids_collisions_and_is_deterministic() -> None:
    items = [("a", 100.0, 100.0, 5.0, 40.0), ("b", 104.0, 100.0, 5.0, 40.0), ("c", 108.0, 100.0, 5.0, 40.0)]
    first = _place_labels(items, (0.0, 0.0, 300.0, 200.0))
    assert first == _place_labels(items, (0.0, 0.0, 300.0, 200.0))
    boxes = [(x, y, w, h) for _, x, y, _, w, h in first]
    for i, a in enumerate(boxes):
        for b in boxes[i + 1:]:
            assert a[0] + a[2] <= b[0] or b[0] + b[2] <= a[0] or a[1] + a[3] <= b[1] or b[1] + b[3] <= a[1]


def test_width_within_limits() -> None:
    assert 320 <= float(_root(coverage_mutation(PTS, UNMUT)).get("width", "0")) <= 960


def test_only_unmutated_still_draws() -> None:
    svg = coverage_mutation([], UNMUT)
    assert svg and "not mutated" in svg


def test_escapes_names() -> None:
    pts = [{"module": "a.<x>&", "coverage": 90.0, "score": 80.0, "mutants": 5}]
    svg = coverage_mutation(pts, [{"module": "u<1>", "coverage": 50.0}])
    assert "<x>" not in svg and "u<1>" not in svg
    _root(svg)


def test_is_deterministic() -> None:
    assert coverage_mutation(PTS, UNMUT) == coverage_mutation(PTS, UNMUT)


# ---------------------------------------------------------------- two widths


def test_scatter_is_drawn_at_the_width_it_is_given(fig_width, fits) -> None:
    fits(coverage_mutation(PTS, UNMUT, width=fig_width), fig_width)


def test_the_legend_names_the_ranges_of_base_score_steps(monkeypatch) -> None:
    from tsbench.report.svg import base
    monkeypatch.setattr(base, "SCORE_STEPS", (97.5, 90.0, 75.0, 50.0))
    texts = [t.text or "" for t in _root(coverage_mutation(PTS, UNMUT)).iter(f"{NS}text")]
    assert "97.5 % and above" in texts and "90 to 97.5 %" in texts and "95 % and above" not in texts
