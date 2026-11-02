from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET

from svg_helpers import root as _root
from svg_helpers import tip as _tip

from tsbench.report.svg import base, bundle
from tsbench.report.svg.bundle import edge_bundling

NS = "{http://www.w3.org/2000/svg}"
MODS = [
    {"module": "tsbench.core.schema", "package": "core", "value": 99.0},
    {"module": "tsbench.core.intervals", "package": "core", "value": 96.0},
    {"module": "tsbench.tasks.oracle", "package": "tasks", "value": 80.0},
    {"module": "tsbench.tasks.verify", "package": "tasks", "value": 40.0},
    {"module": "tsbench.run.runner", "package": "run", "value": None},
    {"module": "tsbench.run.doctor", "package": "run", "value": 92.0},
]
EDGES = [
    ("tsbench.run.runner", "tsbench.core.schema", 2),
    ("tsbench.run.runner", "tsbench.tasks.oracle", 1),
    ("tsbench.tasks.verify", "tsbench.tasks.oracle", 1),
    ("tsbench.tasks.verify", "tsbench.nowhere", 1),  # unknown module: skipped
    ("tsbench.core.schema", "tsbench.core.schema", 1),  # self edge: skipped
]


def _nodes(svg: str) -> list[ET.Element]:
    return [c for c in _root(svg).iter(f"{NS}circle") if c.find(f"{NS}title") is not None]


def _links(svg: str) -> list[ET.Element]:
    return [p for p in _root(svg).iter(f"{NS}path") if "flow" in p.get("class", "").split()]


def test_empty() -> None:
    assert edge_bundling([], []) == ""


def test_one_node_per_module_with_score_class() -> None:
    nodes = _nodes(edge_bundling(MODS, EDGES))
    assert len(nodes) == 6
    cls = {_tip(n).split(":")[0]: n.get("class") for n in nodes}
    assert cls["tsbench.core.schema"] == "g0"
    assert cls["tsbench.core.intervals"] == "g0"
    assert cls["tsbench.tasks.oracle"] == "g2"
    assert cls["tsbench.tasks.verify"] == "g4"
    assert cls["tsbench.run.runner"] == "na"
    assert cls["tsbench.run.doctor"] == "g1"


def test_titles_have_the_value() -> None:
    tips = [_tip(n) for n in _nodes(edge_bundling(MODS, EDGES))]
    assert any("tsbench.core.schema" in t and "99.0" in t for t in tips)
    assert any("tsbench.run.runner" in t and "no value" in t for t in tips)


def test_none_label_is_configurable() -> None:
    tips = [_tip(n) for n in _nodes(edge_bundling(MODS, EDGES, none_label="not mutated"))]
    assert any("tsbench.run.runner" in t and "not mutated" in t for t in tips)


def test_one_link_per_valid_edge() -> None:
    links = _links(edge_bundling(MODS, EDGES))
    assert len(links) == 3
    tips = [_tip(p) for p in links]
    assert any("tsbench.run.runner → tsbench.core.schema" in t and "2" in t for t in tips)


def test_link_runs_from_source_to_target_node() -> None:
    svg = edge_bundling(MODS, EDGES)
    pos = {_tip(n).split(":")[0]: (float(n.get("cx", "0")), float(n.get("cy", "0"))) for n in _nodes(svg)}
    link = next(p for p in _links(svg) if "runner → tsbench.core.schema" in _tip(p))
    nums = [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", link.get("d", ""))]
    assert abs(nums[0] - pos["tsbench.run.runner"][0]) < 0.02 and abs(nums[1] - pos["tsbench.run.runner"][1]) < 0.02
    assert abs(nums[-2] - pos["tsbench.core.schema"][0]) < 0.02 and abs(nums[-1] - pos["tsbench.core.schema"][1]) < 0.02


def test_packages_are_contiguous_in_angle() -> None:
    svg = edge_bundling(MODS, EDGES)
    nodes = _nodes(svg)
    cx = float(_root(svg).get("width", "0")) / 2
    cy = min(float(n.get("cy", "0")) for n in nodes) + (max(float(n.get("cy", "0")) for n in nodes)
                                                         - min(float(n.get("cy", "0")) for n in nodes)) / 2
    ang = {}
    for n in nodes:
        a = math.atan2(float(n.get("cx", "0")) - cx, -(float(n.get("cy", "0")) - cy)) % (2 * math.pi)
        ang[_tip(n).split(":")[0]] = a
    order = sorted(ang, key=ang.__getitem__)
    pk = [m.split(".")[1] for m in order]
    # the sequence of packages around the circle changes package only len(packages) times (cyclic)
    changes = sum(1 for i in range(len(pk)) if pk[i] != pk[(i + 1) % len(pk)])
    assert changes == 3


def test_labels_at_small_size() -> None:
    svg = edge_bundling(MODS, EDGES)
    labels = [t for t in _root(svg).iter(f"{NS}text") if "core.schema" in (t.text or "")]
    assert labels and labels[0].get("font-size") == "11px"


def test_legend_has_the_five_steps() -> None:
    texts = [t.text or "" for t in _root(edge_bundling(MODS, EDGES)).iter(f"{NS}text")]
    assert sum(1 for t in texts if "95" in t) >= 1


def test_94_modules_stay_within_960() -> None:
    pk = ["core", "tasks", "plan", "run", "conditions", "score", "stats", "figures", "report", "release"]
    mods: list[dict] = [{"module": f"tsbench.{pk[i % 10]}.some_long_module_name_{i}", "package": pk[i % 10],
                         "value": (i * 7) % 101 if i % 5 else None} for i in range(94)]
    mods.sort(key=lambda m: m["package"])
    edges = [(str(mods[i]["module"]), str(mods[(i * 3 + 1) % 94]["module"]), 1) for i in range(94)]
    svg = edge_bundling(mods, edges)
    assert float(_root(svg).get("width", "0")) <= 960
    assert len(_nodes(svg)) == 94


def test_escapes_names() -> None:
    mods = [{"module": "a.<x>&", "package": "a", "value": 50.0}, {"module": "a.y", "package": "a", "value": 60.0}]
    svg = edge_bundling(mods, [("a.<x>&", "a.y", 1)])
    assert "<x>" not in svg
    _root(svg)


def test_is_deterministic() -> None:
    assert edge_bundling(MODS, EDGES) == edge_bundling(MODS, EDGES)


# ---------------------------------------------------------------- two widths


def test_bundle_is_drawn_at_the_width_it_is_given(fig_width, fits) -> None:
    fits(edge_bundling(MODS, EDGES, width=fig_width), fig_width)


def test_package_names_near_each_other_do_not_overlap() -> None:
    """Two short arcs side by side at the top: the second name moves outward until the boxes are apart."""
    svg = bundle._package_names({"(top level)": -0.06, "conditions": 0.06}, 480.0, 400.0, 300.0)
    boxes = []
    for m in re.finditer(r'<text[^>]* x="([-\d.]+)" y="([-\d.]+)"[^>]*text-anchor="(\w+)"[^>]*>([^<]+)</text>', svg):
        x, y, anchor, label = float(m[1]), float(m[2]), m[3], m[4]
        w = len(label) * base.TEXT_PX * 0.6
        x0 = {"start": x, "middle": x - w / 2, "end": x - w}[anchor]
        boxes.append((x0, x0 + w, y - base.TEXT_PX, y + 3))
    assert len(boxes) == 2
    (a0, a1, b0, b1), (c0, c1, d0, d1) = boxes
    assert a1 <= c0 or c1 <= a0 or b1 <= d0 or d1 <= b0


def test_a_link_carries_its_width_in_a_style_that_the_ax_rule_of_the_css_cannot_override() -> None:
    """svg.css sets `stroke-width:1` on `.ax`; a presentation attribute loses against it, an inline style wins."""
    edges = [("tsbench.run.runner", "tsbench.core.schema", 5), ("tsbench.run.runner", "tsbench.tasks.oracle", 1)]
    by_tip = {_tip(p).split(":")[0]: p for p in _links(edge_bundling(MODS, edges))}
    wide = by_tip["tsbench.run.runner → tsbench.core.schema"]
    thin = by_tip["tsbench.run.runner → tsbench.tasks.oracle"]
    assert "stroke-width:3.4" in wide.get("style", "") and "stroke-width:1" in thin.get("style", "")
    assert wide.get("stroke-width") is None and thin.get("stroke-width") is None


def test_line_and_path_write_the_width_as_a_style_and_keep_the_dash_as_an_attribute() -> None:
    assert base.line(0, 0, 1, 1, "ax", width=2.8, dash="3 2") == (
        '<line class="ax" x1="0" y1="0" x2="1" y2="1" style="stroke-width:2.8" stroke-dasharray="3 2"/>')
    assert base.path("M0 0", "flow ax", width=4.0) == '<path class="flow ax" d="M0 0" style="stroke-width:4"/>'
    assert "style" not in base.line(0, 0, 1, 1) and "style" not in base.path("M0 0")


def test_the_legend_names_the_ranges_of_base_score_steps(monkeypatch) -> None:
    monkeypatch.setattr(base, "SCORE_STEPS", (97.5, 90.0, 75.0, 50.0))
    texts = [t.text or "" for t in _root(edge_bundling(MODS, EDGES)).iter(f"{NS}text")]
    assert "97.5 % and above" in texts and "90 to 97.5 %" in texts and "95 % and above" not in texts
