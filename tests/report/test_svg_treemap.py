from __future__ import annotations

import xml.etree.ElementTree as ET

from svg_helpers import root as _root
from svg_helpers import tip as _tip

from tsbench.report.svg import treemap as treemap_module
from tsbench.report.svg.treemap import treemap

NS = "{http://www.w3.org/2000/svg}"


def _f(module: str, package: str, statements: int, pct: float | None, functions: list[dict] | None = None) -> dict:
    return {"module": module, "package": package, "statements": statements,
            "covered": round(statements * (pct or 0) / 100), "pct": pct, "functions": functions or []}


FILES = [
    _f("tsbench.core.schema", "core", 200, 99.0),
    _f("tsbench.core.intervals", "core", 100, 96.0),
    _f("tsbench.run.runner", "run", 300, 80.0),
    _f("tsbench.run.doctor", "run", 100, 40.0),
    _f("tsbench.score.numeric", "score", 100, 92.0),
    _f("tsbench.core.__init__", "core", 0, None),
]


def _tiles(svg: str) -> list[ET.Element]:
    return [r for r in _root(svg).iter(f"{NS}rect") if "tile" in r.get("class", "").split()]


def _box(r: ET.Element) -> tuple[float, float, float, float]:
    x, y = float(r.get("x", "0")), float(r.get("y", "0"))
    return x, y, x + float(r.get("width", "0")), y + float(r.get("height", "0"))


def _area(r: ET.Element) -> float:
    return float(r.get("width", "0")) * float(r.get("height", "0"))


def test_empty() -> None:
    assert treemap([]) == ""
    assert treemap([_f("m", "p", 0, None)]) == ""


def test_one_tile_per_file_with_statements() -> None:
    assert len(_tiles(treemap(FILES))) == 5


def test_area_is_proportional_to_statements() -> None:
    area = {_tip(r).split(":")[0]: _area(r) for r in _tiles(treemap(FILES))}
    assert abs(area["tsbench.run.runner"] / area["tsbench.run.doctor"] - 3) < 0.05
    assert abs(area["tsbench.core.schema"] / area["tsbench.score.numeric"] - 2) < 0.05


def test_class_by_coverage() -> None:
    cls = {_tip(r).split(":")[0]: r.get("class", "").split() for r in _tiles(treemap(FILES))}
    assert "g0" in cls["tsbench.core.schema"]
    assert "g0" in cls["tsbench.core.intervals"]
    assert "g2" in cls["tsbench.run.runner"]
    assert "g4" in cls["tsbench.run.doctor"]
    assert "g1" in cls["tsbench.score.numeric"]


def test_titles_carry_numbers() -> None:
    tips = [_tip(r) for r in _tiles(treemap(FILES))]
    assert any("tsbench.run.runner" in t and "300" in t and "80.0" in t for t in tips)


def test_tiles_do_not_overlap_and_stay_in_the_figure() -> None:
    svg = treemap(FILES)
    root = _root(svg)
    w, h = float(root.get("width", "0")), float(root.get("height", "0"))
    rs = [(float(r.get("x", "0")), float(r.get("y", "0")), float(r.get("width", "0")), float(r.get("height", "0")))
          for r in _tiles(svg)]
    for i, a in enumerate(rs):
        assert a[0] >= -1e-6 and a[1] >= -1e-6 and a[0] + a[2] <= w + 1e-6 and a[1] + a[3] <= h + 1e-6
        for b in rs[i + 1:]:
            ox = min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0])
            oy = min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1])
            assert ox <= 1e-6 or oy <= 1e-6


def test_package_frames_and_labels() -> None:
    svg = treemap(FILES)
    frames = [r for r in _root(svg).iter(f"{NS}rect") if "frame" in r.get("class", "").split()]
    assert len(frames) == 3
    texts = [t.text or "" for t in _root(svg).iter(f"{NS}text")]
    assert any(t.startswith("core") for t in texts)
    assert any(t.startswith("run") for t in texts)


def test_tiles_of_a_package_lie_inside_its_frame() -> None:
    svg = treemap(FILES)
    root = _root(svg)
    for g in root.iter(f"{NS}g"):
        frame = next((r for r in g.findall(f"{NS}rect") if "frame" in r.get("class", "").split()), None)
        if frame is None:
            continue
        fx, fy = float(frame.get("x", "0")), float(frame.get("y", "0"))
        fw, fh = float(frame.get("width", "0")), float(frame.get("height", "0"))
        for r in g.iter(f"{NS}rect"):
            if "tile" in r.get("class", "").split():
                x, y = float(r.get("x", "0")), float(r.get("y", "0"))
                assert fx - 1e-6 <= x and x + float(r.get("width", "0")) <= fx + fw + 1e-6
                assert fy - 1e-6 <= y and y + float(r.get("height", "0")) <= fy + fh + 1e-6


def test_legend_has_the_five_steps() -> None:
    texts = [t.text or "" for t in _root(treemap(FILES)).iter(f"{NS}text")]
    for s in ("95 %", "90", "75", "50"):
        assert any(s in t for t in texts)


def test_width_within_limits() -> None:
    assert 320 <= float(_root(treemap(FILES)).get("width", "0")) <= 960


def test_treemap_escape_and_determinism() -> None:
    files = [_f("a.<x>&", "p<1>", 10, 50.0), _f("a.y", "p<1>", 5, 60.0)]
    svg = treemap(files)
    assert "<x>" not in svg and "p<1>" not in svg
    _root(svg)
    assert svg == treemap(files)


# ---------------------------------------------------------------- two widths


def test_treemap_is_drawn_at_the_width_it_is_given(fig_width, fits) -> None:
    fits(treemap(FILES, width=fig_width), fig_width)


def test_a_tile_label_is_printed_only_when_it_fits_its_tile() -> None:
    """no label is cut by its tile or laid over another."""
    files = FILES + [_f(f"tsbench.run.tiny_module_with_a_long_name_{i}", "run", 2, 50.0) for i in range(8)]
    root = _root(treemap(files, width=464))
    tiles = [(_box(r), _tip(r)) for r in root.iter(f"{NS}rect") if _tip(r)]
    for t in root.iter(f"{NS}text"):
        name = t.text or ""
        hit = [box for box, tip in tiles if tip.startswith(name) and name]
        if hit:
            x0, y0, x1, y1 = hit[0]
            assert x0 <= float(t.get("x") or 0) and float(t.get("x") or 0) + len(name) * 11 * 0.55 <= x1 + 1, name


def test_one_equal_density_loop_serves_the_coverage_treemap_and_the_run_map() -> None:
    """The weight update that gives every cell the same effective area per value lives next to squarify only."""
    from tsbench.report.svg import maps
    assert hasattr(treemap_module, "equalise")
    assert maps.equalise is treemap_module.equalise


def test_equalise_gives_every_cell_the_same_inner_area_per_value() -> None:
    """Statement counts of a package set like the shipped one, at both figure widths."""
    for values in ([3100.0, 2200.0, 1500.0, 900.0, 600.0, 450.0, 300.0], [2000.0, 1000.0, 500.0], [800.0, 790.0]):
        for w, h in ((960.0, 500.0), (464.0, 380.0)):
            cells = treemap_module.equalise(values, (0.0, 0.0, w, h), treemap_module.package_inner_area)
            inner = [treemap_module.package_inner_area(i, c) for i, c in enumerate(cells)]
            per = [a / v for a, v in zip(inner, values, strict=True)]
            assert max(per) / min(per) < 1.01, (values, w, per)


def test_the_legend_names_the_ranges_of_base_score_steps(monkeypatch) -> None:
    from tsbench.report.svg import base
    monkeypatch.setattr(base, "SCORE_STEPS", (97.5, 90.0, 75.0, 50.0))
    texts = [t.text or "" for t in _root(treemap(FILES)).iter(f"{NS}text")]
    assert "97.5 % and above" in texts and "90 to 97.5 %" in texts and "95 % and above" not in texts
