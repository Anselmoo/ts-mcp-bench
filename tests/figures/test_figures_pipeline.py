"""Tests of the figure pipeline on a synthetic run set (scores.csv fixtures plus two tiny transcripts)."""
from __future__ import annotations

import csv
import json
import pathlib
import re
import shutil
import subprocess

import pytest

from tsbench.figures import cli, data
from tsbench.figures.render import Context

NAMES = ["accuracy_by_model", "accuracy_by_class", "literature_parity", "efficiency", "code_listing"]
MODELS = ["claude-haiku-5-5", "claude-sonnet-5-5"]
FAKE_CONFIRMATORY_ID = "C-fixture-99"
COLS = ["model", "condition", "effort", "task_id", "k_index", "class", "correct", "evaluable", "has_result", "dq", "b",
        "c", "cost_usd", "output_tokens", "wall_time_s", "duration_s", "n_mcp_calls", "n_bash_calls"]


def _tool_use(name, inp, i):
    block = {"type": "tool_use", "id": f"t{i}", "name": name, "input": inp}
    return {"type": "assistant", "message": {"content": [block]}}


def _write_transcript(path: pathlib.Path, events):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")


@pytest.fixture(scope="module")
def run_dir(tmp_path_factory):
    from tsbench.tasks import load
    root = tmp_path_factory.mktemp("figrun") / "run"
    root.mkdir()
    tasks = load("pilot")
    by_class: dict = {}
    for t in tasks:
        by_class.setdefault(t["class"], []).append(t)
    chosen = [t for ts in by_class.values() for t in ts[:2]]
    rows = []
    for mi, m in enumerate(MODELS):
        for ci, c in enumerate("ABC"):
            for ti, t in enumerate(chosen):
                for k in (1, 2):
                    ok = (ti + k + ci + mi) % 3 != 0 or c == "C"
                    ref = t.get("reference") or {}
                    err = 0.0 if ok else 0.2
                    vals = {p: (ref[p] * (1 + err) if isinstance(ref.get(p), (int, float)) else "")
                            for p in ("Dq", "B", "C")}
                    rows.append({"model": m, "condition": c, "effort": "medium", "task_id": t["id"], "k_index": k,
                                 "class": t["class"], "correct": ok, "evaluable": True, "has_result": True,
                                 "dq": vals["Dq"], "b": vals["B"], "c": vals["C"],
                                 "cost_usd": 0.01 * (1 + ci) * (1 + mi), "output_tokens": 1000 * (1 + ci),
                                 "wall_time_s": 20.0 + 10 * ci, "duration_s": 19.0, "n_mcp_calls": 2 if c == "C" else 0,
                                 "n_bash_calls": 1 if c == "B" else 0})
    rows.append({**rows[0], "task_id": chosen[0]["id"], "k_index": 9, "evaluable": False, "correct": False})
    rows.append({**rows[0], "task_id": FAKE_CONFIRMATORY_ID, "k_index": 1})
    with (root / "scores.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    t0 = chosen[0]["id"]
    mcp = [_tool_use("mcp__ts__fit", {"bands": [1, 2], "geometry": "Oh"}, 1),
           _tool_use("mcp__ts__energies", {"Dq": 1000, "B": 700}, 2)]
    _write_transcript(root / MODELS[0] / "C" / "medium" / f"{t0}-k1.jsonl", mcp)
    script = "import numpy as np\nx = np.arange(5)\ny = x ** 2\nprint(y.sum())\nprint('done')\n"
    bash = [_tool_use("Bash", {"command": f"python - <<'EOF'\n{script}EOF"}, 1)]
    _write_transcript(root / MODELS[0] / "B" / "medium" / f"{t0}-k1.jsonl", bash)
    return root


def _ctx(run_dir, **kw):
    return Context(sets=data.load_all([run_dir]), **kw)


@pytest.fixture(scope="module")
def built(run_dir, tmp_path_factory):
    out = tmp_path_factory.mktemp("figout")
    ctx = _ctx(run_dir)
    prov = cli.build_all(NAMES, ctx, out)
    return out, ctx, prov


def _csv(path):
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def test_all_files_exist(built):
    out, _ctx_, _prov = built
    for n in NAMES:
        for suf in (".pdf", ".svg", ".tif", ".png", ".source.csv", ".json"):
            assert (out / f"{n}{suf}").stat().st_size > 0, (n, suf)


def test_raster_resolution(built):
    from PIL import Image
    out, _c, _p = built
    with Image.open(out / "accuracy_by_model.tif") as im:
        assert round(im.info["dpi"][0]) == 600 and im.info["compression"] == "tiff_lzw"
    with Image.open(out / "accuracy_by_model.png") as im:
        assert round(im.info["dpi"][0]) == 300


def _mediabox_mm(pdf: pathlib.Path):
    m = re.search(rb"/MediaBox\s*\[\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*\]", pdf.read_bytes())
    return (float(m[3]) - float(m[1])) * 25.4 / 72


@pytest.mark.parametrize("name,width", [("accuracy_by_model", 84.6), ("accuracy_by_class", 177.8),
                                        ("literature_parity", 177.8), ("efficiency", 177.8),
                                        ("code_listing", 177.8)])
def test_pdf_width_is_the_set_width(built, name, width):
    assert abs(_mediabox_mm(built[0] / f"{name}.pdf") - width) <= 0.5


def _has_arial_like():
    from matplotlib import font_manager
    have = {f.name for f in font_manager.fontManager.ttflist}
    return bool(have & {"Arial", "Liberation Sans", "Arimo"})


@pytest.mark.skipif(not _has_arial_like(), reason="no Arial-compatible font installed")
@pytest.mark.parametrize("name", NAMES)
def test_fonts_embedded(built, name):
    pdf = built[0] / f"{name}.pdf"
    pdf_bytes = pdf.read_bytes()
    assert b"DejaVu" not in pdf_bytes
    assert b"/FontFile2" in pdf_bytes
    if shutil.which("pdffonts"):
        lines = subprocess.run(["pdffonts", str(pdf)], capture_output=True, encoding="utf-8").stdout.splitlines()[2:]
        assert lines and all(re.split(r"\s{2,}|\s+", ln.strip())[-5] == "yes" for ln in lines if ln.strip())
        assert not any("DejaVu" in ln for ln in lines)


def _plotted(fig):
    out = []
    for ax in fig.axes:
        for ln in ax.lines:
            if str(ln.get_gid()).startswith("data:"):
                out.append((ax, str(ln.get_gid())[5:], list(ln.get_xdata()), list(ln.get_ydata())))
    return out


def _rebuild(run_dir, name, **kw):
    ctx = _ctx(run_dir, **kw)
    return cli.builders()[name](ctx)


def test_accuracy_by_model_source_equals_plotted(run_dir):
    b = _rebuild(run_dir, "accuracy_by_model")
    src = {(r["model"], r["condition"]): float(r["share_pct"]) for r in b.source}
    drawn = sorted(x for _ax, _c, xs, _y in _plotted(b.fig) for x in xs)
    assert drawn == pytest.approx(sorted(src.values()), rel=1e-9)
    assert len(src) == 6
    for r in b.source:
        assert float(r["ci_lo_pct"]) <= float(r["share_pct"]) <= float(r["ci_hi_pct"])


def test_accuracy_by_model_csv_roundtrip(built):
    out, ctx, _p = built
    rows = _csv(out / "accuracy_by_model.source.csv")
    plotted = sorted(float(r["share_pct"]) for r in rows)
    ref = sorted(100 * sum(r["correct"] for r in g) / len(g)
                 for g in data.group_by(ctx.rows, "model", "condition").values())
    assert plotted == pytest.approx(ref, rel=1e-6)


def test_accuracy_by_model_bootstrap_option(run_dir):
    b = _rebuild(run_dir, "accuracy_by_model", ci="bootstrap")
    assert {r["ci_method"] for r in b.source} == {"bootstrap"}


def test_the_other_data_figures_source_equals_plotted(run_dir):
    b2 = _rebuild(run_dir, "accuracy_by_class")
    assert sorted(x for *_a, xs, _y in _plotted(b2.fig) for x in xs) == pytest.approx(
        sorted(float(r["share_pct"]) for r in b2.source), rel=1e-9)
    b3 = _rebuild(run_dir, "literature_parity")
    assert sorted(y for *_a, _x, ys in _plotted(b3.fig) for y in ys) == pytest.approx(
        sorted(float(r["deviation_pct"]) for r in b3.source), rel=1e-9, abs=1e-9)
    b4 = _rebuild(run_dir, "efficiency")
    ok = [float(r["value"]) for r in b4.source if r["status"] == "ok"]
    assert sorted(x for *_a, xs, _y in _plotted(b4.fig) for x in xs) == pytest.approx(sorted(ok), rel=1e-9)


def test_excluded_and_nonpilot_rows(run_dir, built):
    sets = data.load_all([run_dir])
    assert sets[0].dropped_non_pilot == 1
    assert sum(not r["evaluable"] for r in sets[0].rows) == 1
    assert all(r["evaluable"] for r in built[1].rows)


def test_no_confirmatory_id_in_outputs(built):
    out, _c, _p = built
    pat = re.compile(r"\bC-[A-Za-z_]+-\d+\b|" + re.escape(FAKE_CONFIRMATORY_ID))
    hits = 0
    for f in out.iterdir():
        if f.suffix in (".csv", ".json", ".svg"):
            hits += len(pat.findall(f.read_text(encoding="utf-8")))
    assert hits == 0


def test_confirmatory_run_dir_refused(tmp_path, run_dir):
    d = tmp_path / "confirmatory-run"
    shutil.copytree(run_dir, d)
    with pytest.raises(ValueError):
        data.find_run_sets([d])
    m = tmp_path / "sets" / "some-set"
    shutil.copytree(run_dir, m)
    (m / "MANIFEST.json").write_text(json.dumps({"split": "confirmatory"}), encoding="utf-8")
    with pytest.raises(ValueError):
        data.find_run_sets([tmp_path / "sets"])
    assert cli.main(["accuracy_by_model", "--runs", str(tmp_path / "sets"), "--out", str(tmp_path / "o")]) == 2
    assert [n for _p, n, _t in data.find_run_sets([tmp_path / "sets"], "10.5281/zenodo.1")] == ["some-set"]


def test_discovery_of_a_nested_run_set(run_dir, tmp_path):
    root = tmp_path / "root"
    shutil.copytree(run_dir, root / "group" / "set-a")
    (root / "group" / "set-a" / "MANIFEST.json").write_text(json.dumps({"split": "pilot", "finished": True}),
                                                            encoding="utf-8")
    (root / "group" / "set-a" / "run_set.json").write_text(json.dumps({"title": "Set A"}), encoding="utf-8")
    found = data.find_run_sets([root])
    assert [(n, t) for _p, n, t in found] == [("group/set-a", "Set A")]
    assert set(cli.builders()) == set(NAMES)
    assert cli.main(["accuracy_by_model", "--runs", str(root), "--out", str(tmp_path / "o"), "--no-raster"]) == 0
    prov = json.loads((tmp_path / "o" / "accuracy_by_model.json").read_text(encoding="utf-8"))
    assert prov["run_sets"][0]["name"] == "group/set-a" and prov["run_sets"][0]["title"] == "Set A"
    assert str(tmp_path) not in (tmp_path / "o" / "accuracy_by_model.json").read_text(encoding="utf-8")


def test_check_detects_a_difference(run_dir, tmp_path):
    golden = tmp_path / "golden"
    assert cli.main(["accuracy_by_model", "--runs", str(run_dir), "--out", str(golden), "--no-raster"]) == 0
    assert cli.main(["accuracy_by_model", "--runs", str(run_dir), "--check", str(golden), "--no-raster"]) == 0
    p = golden / "accuracy_by_model.source.csv"
    p.write_bytes(p.read_bytes().replace(b"Haiku", b"Haiku!", 1))
    assert cli.main(["accuracy_by_model", "--runs", str(run_dir), "--check", str(golden), "--no-raster"]) == 1


def test_pinned_dates(run_dir, tmp_path, monkeypatch):
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "1700000000")
    for d in ("a", "b"):
        assert cli.main(["accuracy_by_model", "--runs", str(run_dir), "--out", str(tmp_path / d), "--no-raster"]) == 0
    for suf in (".pdf", ".svg", ".source.csv", ".json"):
        a = (tmp_path / "a" / f"accuracy_by_model{suf}").read_bytes()
        b = (tmp_path / "b" / f"accuracy_by_model{suf}").read_bytes()
        if suf == ".json":
            a, b = (json.loads(x)["generated_utc"] for x in (a, b))
            assert a == b == "2023-11-14T22:13:20Z"
        elif suf != ".pdf":  # the PDF embeds a font subset id that may vary; its dates are checked below
            assert a == b, suf
    assert b"D:20231114221320" in (tmp_path / "a" / "accuracy_by_model.pdf").read_bytes()


def test_provenance(built):
    out, _c, prov = built
    for n in NAMES:
        p = json.loads((out / f"{n}.json").read_text(encoding="utf-8"))
        assert "pilot" in p["caption"].lower() and "pilot" in p["footer"].lower() and p["status"] == "pilot"
        assert p["run_sets"][0]["scores_csv_sha256"] and p["task_set"]["pilot"]
        assert p["versions"]["matplotlib"]
        assert "commit" in p["git"] and p["generated_utc"]


def test_deterministic(run_dir, built, tmp_path):
    out1 = built[0]
    cli.build_all(NAMES, _ctx(run_dir), tmp_path)
    for n in NAMES:
        assert (out1 / f"{n}.source.csv").read_bytes() == (tmp_path / f"{n}.source.csv").read_bytes()
        a = json.loads((out1 / f"{n}.json").read_text(encoding="utf-8"))
        b = json.loads((tmp_path / f"{n}.json").read_text(encoding="utf-8"))
        a.pop("generated_utc")
        b.pop("generated_utc")
        assert a == b


def test_listing_has_at_most_15_lines(built):
    rows = _csv(built[0] / "code_listing.source.csv")
    for panel in ("B", "C"):
        lines = [r for r in rows if r["panel"] == panel]
        assert 0 < len(lines) <= 15
    assert any("fit(" in r["text"] for r in rows)


def test_builders_are_named_after_their_figure():
    from tsbench.figures import listing, plots, render

    table = cli.builders()
    assert table["accuracy_by_model"] is plots.accuracy_by_model
    assert table["accuracy_by_class"] is plots.accuracy_by_class
    assert table["literature_parity"] is plots.literature_parity
    assert table["efficiency"] is plots.efficiency
    assert table["code_listing"] is listing.code_listing
    # private helpers of the data loader and the csv writer
    assert data._as_float("2.5") == 2.5 and data._as_float("") is None
    assert data._as_bool("True") is True and data._as_bool("no") is False
    assert render.format_float(0.5) == "0.5" and render.format_float(None) == ""
    # every module of the pipeline reaches the data module under its own name
    for mod in (plots, listing, render, cli):
        assert mod.data is data
