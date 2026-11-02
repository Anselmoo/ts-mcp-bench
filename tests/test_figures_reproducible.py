"""The figure pipeline is reproducible: the figures drawn twice from the demo run set (fake claude) have the same
`<name>.source.csv` byte for byte and the same `<name>.json` without its volatile keys, and `tsbench figures all
--check DIR` compares a new build against such a folder.

The fake claude makes one MCP call per C run and writes no Python heredoc in B, so code_listing has no example in the
demo run set and is skipped; its tests use made-up transcripts (tests/figures/test_figures_listing.py)."""
from __future__ import annotations

import csv
import json
import pathlib
import shutil

import pytest

from tsbench.figures import FIGURE_NAMES, cli
from tsbench.figures.render import VOLATILE_KEYS, check

DRAWN = tuple(n for n in FIGURE_NAMES if n != "code_listing")


@pytest.fixture(scope="module")
def runs(tmp_path_factory, demo_runs_root) -> pathlib.Path:
    dst = tmp_path_factory.mktemp("figure-runs") / "runs"
    shutil.copytree(demo_runs_root, dst)
    return dst


@pytest.fixture(scope="module")
def drawn(tmp_path_factory, runs) -> tuple[pathlib.Path, pathlib.Path]:
    """The figures of the same run set drawn twice, into two folders."""
    out = []
    for name in ("first", "second"):
        folder = tmp_path_factory.mktemp(name)
        assert cli.main(["all", "--runs", str(runs), "--out", str(folder), "--no-raster"]) == 0
        out.append(folder)
    return out[0], out[1]


def test_every_figure_with_data_is_drawn_with_its_source_table_and_provenance(drawn):
    first, _ = drawn
    for name in DRAWN:
        assert (first / f"{name}.json").is_file(), name
        with (first / f"{name}.source.csv").open(encoding="utf-8", newline="") as fh:
            assert len(list(csv.reader(fh))) > 1, name  # a header and at least one plotted row
    assert not (first / "code_listing.json").exists()


def test_two_builds_give_the_same_source_tables_and_provenance(drawn):
    first, second = drawn
    for name in DRAWN:
        assert (first / f"{name}.source.csv").read_bytes() == (second / f"{name}.source.csv").read_bytes(), name
    assert check(DRAWN, second, first) == []


def test_check_command_accepts_an_unchanged_build(drawn, runs, tmp_path):
    first, _ = drawn
    for name in DRAWN:
        out = tmp_path / name
        assert cli.main([name, "--runs", str(runs), "--check", str(first), "--no-raster", "--out", str(out)]) == 0
    # `all` checks every figure: one without a reference file is a difference
    assert cli.main(["all", "--runs", str(runs), "--check", str(first), "--no-raster"]) == 1


def test_check_ignores_volatile_keys_and_reports_a_change(drawn, tmp_path):
    first, second = drawn
    reference = tmp_path / "reference"
    shutil.copytree(first, reference)
    target = reference / "efficiency.json"
    prov = json.loads(target.read_text(encoding="utf-8"))
    for key in VOLATILE_KEYS:  # volatile keys may differ
        head, _, rest = key.partition(".")
        if rest:
            prov[head][rest] = "changed"
        else:
            prov[head] = "changed"
    target.write_text(json.dumps(prov), encoding="utf-8")
    assert check(DRAWN, second, reference) == []
    prov["pooling"]["n_runs_used"] += 1
    target.write_text(json.dumps(prov), encoding="utf-8")
    assert check(DRAWN, second, reference) == ["efficiency.json: differs in pooling"]
    (reference / "accuracy_by_model.source.csv").write_text("changed\n", encoding="utf-8")
    assert "accuracy_by_model.source.csv: differs" in check(DRAWN, second, reference)


def test_provenance_names_run_sets_not_paths(drawn, runs):
    first, _ = drawn
    for name in DRAWN:
        text = (first / f"{name}.json").read_text(encoding="utf-8")
        assert str(runs) not in text and "/home/" not in text
        sets = json.loads(text)["run_sets"]
        assert sets and all("/" in s["name"] and s["title"] for s in sets)
