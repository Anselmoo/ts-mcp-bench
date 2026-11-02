"""Unit tests of `tsbench.figures.cli` with the builders, the loader and the exporter replaced by recorders."""
from __future__ import annotations

import pathlib
import sys
from types import SimpleNamespace

import pytest

from tsbench.figures import FIGURE_NAMES, cli, data, render


class Recorder:
    """Stands in for data.find_run_sets, data.load_all, cli.build_all and render.check; remembers each call."""

    def __init__(self, monkeypatch, *, no_data=(), diffs=(), refuse=None):
        self.found_args = self.loaded_args = None
        self.builds = []
        self.check_args = None
        self.no_data = set(no_data)
        self.diffs = list(diffs)
        self.refuse = refuse
        self.sets = [SimpleNamespace(rows=[], name="fake")]
        monkeypatch.setattr(data, "find_run_sets", self.find)
        monkeypatch.setattr(data, "load_all", self.load)
        monkeypatch.setattr(cli, "build_all", self.build)
        monkeypatch.setattr(render, "check", self.check)

    def find(self, roots, prereg=None):
        self.found_args = (list(roots), prereg)
        if self.refuse:
            raise ValueError(self.refuse)
        return ["found"]

    def load(self, found, rescore=False):
        self.loaded_args = (found, rescore)
        return self.sets

    def build(self, names, ctx, out, raster=True):
        self.builds.append((list(names), ctx, pathlib.Path(out), raster))
        if names[0] in self.no_data:
            raise data.NoDataError(f"{names[0]} has nothing")
        return {}

    def check(self, names, out, golden):
        self.check_args = (list(names), pathlib.Path(out), pathlib.Path(golden))
        return self.diffs


def _run(argv, capsys):
    code = cli.main(argv)
    cap = capsys.readouterr()
    return code, cap.out, cap.err


# ------------------------------------------------------------------------------------------------ builders
def test_builders_map_every_name_to_one_function():
    from tsbench.figures import listing, plots
    table = cli.builders()
    assert set(table) == set(FIGURE_NAMES)
    assert table["accuracy_by_model"] is plots.accuracy_by_model
    assert table["accuracy_by_class"] is plots.accuracy_by_class
    assert table["literature_parity"] is plots.literature_parity
    assert table["efficiency"] is plots.efficiency
    assert table["code_listing"] is listing.code_listing
    assert FIGURE_NAMES == ("accuracy_by_model", "accuracy_by_class", "literature_parity", "efficiency",
                            "code_listing")


# ------------------------------------------------------------------------------------------------ build_all
def test_build_all_exports_each_figure_under_its_name(tmp_path, monkeypatch):
    exported = []
    built = {}

    def fake_builder(tag):
        def build(ctx):
            built[tag] = ctx
            return f"built-{tag}"
        return build

    monkeypatch.setattr(cli, "builders", lambda: {"accuracy_by_model": fake_builder("one"),
                                                  "accuracy_by_class": fake_builder("two")})

    def fake_export(name, b, ctx, out, raster=True):
        exported.append((name, b, ctx, out, raster))
        return {"figure": name}

    monkeypatch.setattr(render, "export", fake_export)
    ctx = object()
    made = cli.build_all(["accuracy_by_model", "accuracy_by_class"], ctx, str(tmp_path))
    assert made == {"accuracy_by_model": {"figure": "accuracy_by_model"},
                    "accuracy_by_class": {"figure": "accuracy_by_class"}}
    assert exported == [("accuracy_by_model", "built-one", ctx, tmp_path, True),
                        ("accuracy_by_class", "built-two", ctx, tmp_path, True)]
    assert all(isinstance(e[3], pathlib.Path) for e in exported)
    assert built == {"one": ctx, "two": ctx}
    exported.clear()
    made = cli.build_all(["accuracy_by_class"], ctx, tmp_path, raster=False)
    assert made == {"accuracy_by_class": {"figure": "accuracy_by_class"}}
    assert exported[0][4] is False
    assert cli.build_all([], ctx, tmp_path) == {}


# ------------------------------------------------------------------------------------------------ main: arguments
def test_main_passes_the_options_on(tmp_path, monkeypatch, capsys):
    rec = Recorder(monkeypatch)
    code, out, err = _run(["accuracy_by_model", "--runs", "r1", "--runs", "r2", "--out", str(tmp_path / "o"),
                           "--theme", "contrast", "--ci", "bootstrap", "--rescore", "--no-footer", "--no-raster",
                           "--i-have-preregistered", "10.5281/zenodo.1"], capsys)
    assert (code, err) == (0, "")
    assert out == f"accuracy_by_model: written to {tmp_path / 'o'}\n"
    assert rec.found_args == (["r1", "r2"], "10.5281/zenodo.1")
    assert rec.loaded_args == (["found"], True)
    (names, ctx, out_dir, raster), = rec.builds
    assert (names, out_dir, raster) == (["accuracy_by_model"], tmp_path / "o", False)
    assert (ctx.theme, ctx.ci, ctx.footer, ctx.sets) == ("contrast", "bootstrap", False, rec.sets)


def test_main_defaults(tmp_path, monkeypatch, capsys):
    rec = Recorder(monkeypatch)
    code, out, _err = _run(["efficiency", "--runs", "r", "--out", str(tmp_path)], capsys)
    assert code == 0 and out == f"efficiency: written to {tmp_path}\n"
    assert rec.found_args == (["r"], None) and rec.loaded_args == (["found"], False)
    (names, ctx, out_dir, raster), = rec.builds
    assert (names, out_dir, raster) == (["efficiency"], tmp_path, True)
    assert (ctx.theme, ctx.ci, ctx.footer) == ("neutral", "wilson", True)


def test_main_all_builds_every_figure_one_by_one(tmp_path, monkeypatch, capsys):
    rec = Recorder(monkeypatch)
    code, out, err = _run(["all", "--runs", "r", "--out", str(tmp_path)], capsys)
    assert (code, err) == (0, "")
    assert [b[0] for b in rec.builds] == [[n] for n in FIGURE_NAMES]
    assert out.splitlines() == [f"{n}: written to {tmp_path}" for n in FIGURE_NAMES]


def test_main_reads_sys_argv_when_called_without_arguments(tmp_path, monkeypatch, capsys):
    rec = Recorder(monkeypatch)
    monkeypatch.setattr(sys, "argv", ["tsbench-figures", "code_listing", "--runs", "x", "--out", str(tmp_path)])
    assert cli.main() == 0
    assert rec.builds[0][0] == ["code_listing"]
    capsys.readouterr()


def test_main_needs_an_output_directory_unless_checking(tmp_path, monkeypatch, capsys):
    Recorder(monkeypatch)
    with pytest.raises(SystemExit) as exc:
        cli.main(["accuracy_by_model", "--runs", "r"])
    assert exc.value.code == 2
    assert capsys.readouterr().err.strip().endswith("error: --out is required (it may be omitted with --check)")


@pytest.mark.parametrize("argv,message", [
    (["accuracy_by_model", "--out", "o"], "the following arguments are required: --runs"),
    (["nope", "--runs", "r", "--out", "o"], "invalid choice: 'nope'"),
    (["accuracy_by_model", "--runs", "r", "--out", "o", "--ci", "exact"], "invalid choice: 'exact'"),
    ([], "the following arguments are required: figure, --runs"),
])
def test_main_rejects_bad_arguments(monkeypatch, capsys, argv, message):
    Recorder(monkeypatch)
    with pytest.raises(SystemExit) as exc:
        cli.main(argv)
    assert exc.value.code == 2
    assert message in capsys.readouterr().err


def test_main_help_documents_every_option(monkeypatch, capsys):
    monkeypatch.setenv("COLUMNS", "400")
    with pytest.raises(SystemExit) as exc:
        cli.main(["--help"])
    assert exc.value.code == 0
    text = " ".join(capsys.readouterr().out.split())
    assert text.startswith("usage: tsbench figures [-h]")
    synopsis = ("Command line: tsbench figures <name|all> --runs <dir> [--runs <dir> ...] --out <dir> "
                "[--check <golden dir>]")
    assert synopsis in text
    for fragment in [
            "{accuracy_by_model,accuracy_by_class,literature_parity,efficiency,code_listing,all}",
            "--runs DIR a run set or a folder holding run sets (searched for MANIFEST.json); repeatable",
            "--out OUT output directory (with --check only: a temporary one if omitted)",
            "--check GOLDEN compare <name>.source.csv byte for byte and <name>.json without its volatile keys with the "
            "files in GOLDEN; exit 1 on a difference",
            "--theme THEME colour theme of the vendored Figura helpers",
            "--ci {wilson,bootstrap} interval of accuracy_by_model / accuracy_by_class: Wilson over runs, or a "
            "task-clustered bootstrap",
            "--rescore score the transcripts in memory instead of reading scores.csv",
            "--no-footer omit the 'pilot data' footer line inside the figure",
            "--no-raster write PDF and SVG only (no TIFF / PNG)",
            "--i-have-preregistered DOI needed to read a confirmatory run set (only its pilot task ids are drawn)"]:
        assert fragment in text, fragment


# ------------------------------------------------------------------------------------------------ main: outcomes
def test_main_refuses_a_run_set_it_may_not_read(tmp_path, monkeypatch, capsys):
    rec = Recorder(monkeypatch, refuse="no way")
    code, out, err = _run(["accuracy_by_model", "--runs", "r", "--out", str(tmp_path)], capsys)
    assert (code, out, err) == (2, "", "refusing: no way\n")
    assert rec.builds == [] and rec.loaded_args is None


def test_main_a_figure_without_data_is_skipped_and_fails_a_single_request(tmp_path, monkeypatch, capsys):
    rec = Recorder(monkeypatch, no_data={"literature_parity"})
    code, out, err = _run(["literature_parity", "--runs", "r", "--out", str(tmp_path)], capsys)
    assert code == 1 and out == ""
    assert err == "literature_parity: skipped (literature_parity has nothing)\n"
    assert len(rec.builds) == 1


def test_main_all_goes_on_after_a_figure_without_data_and_still_succeeds(tmp_path, monkeypatch, capsys):
    rec = Recorder(monkeypatch, no_data={"accuracy_by_class", "efficiency"})
    code, out, err = _run(["all", "--runs", "r", "--out", str(tmp_path)], capsys)
    assert code == 0
    assert err.splitlines() == ["accuracy_by_class: skipped (accuracy_by_class has nothing)",
                                "efficiency: skipped (efficiency has nothing)"]
    assert out.splitlines() == [f"{n}: written to {tmp_path}" for n in
                                ("accuracy_by_model", "literature_parity", "code_listing")]
    assert len(rec.builds) == 5


def test_main_other_errors_are_not_swallowed(tmp_path, monkeypatch):
    Recorder(monkeypatch)

    def boom(*_a, **_k):
        raise RuntimeError("real bug")

    monkeypatch.setattr(cli, "build_all", boom)
    with pytest.raises(RuntimeError, match="real bug"):
        cli.main(["accuracy_by_model", "--runs", "r", "--out", str(tmp_path)])


# ------------------------------------------------------------------------------------------------ main: --check
def test_main_check_compares_the_built_files_with_the_golden_folder(tmp_path, monkeypatch, capsys):
    rec = Recorder(monkeypatch)
    code, out, err = _run(["all", "--runs", "r", "--out", str(tmp_path / "o"), "--check", str(tmp_path / "g")],
                          capsys)
    assert (code, err) == (0, "")
    assert rec.check_args == (list(FIGURE_NAMES), tmp_path / "o", tmp_path / "g")
    assert out.splitlines()[-1] == f"check: 5 of 5 figures match {tmp_path / 'g'}"


def test_main_check_reports_each_difference_and_counts_figures(tmp_path, monkeypatch, capsys):
    diffs = ["accuracy_by_model.source.csv: differs", "accuracy_by_model.json: differs in caption",
             "efficiency.json: no golden file"]
    rec = Recorder(monkeypatch, diffs=diffs)
    code, out, err = _run(["all", "--runs", "r", "--out", str(tmp_path), "--check", "gold"], capsys)
    assert code == 1
    assert err.splitlines() == [f"check: {d}" for d in diffs]
    assert out.splitlines()[-1] == "check: 3 of 5 figures match gold"
    assert rec.check_args is not None and rec.check_args[2] == pathlib.Path("gold")


def test_main_check_of_one_figure(tmp_path, monkeypatch, capsys):
    rec = Recorder(monkeypatch, diffs=["accuracy_by_model.source.csv: differs"])
    code, out, err = _run(["accuracy_by_model", "--runs", "r", "--out", str(tmp_path), "--check", "gold"], capsys)
    assert (code, err) == (1, "check: accuracy_by_model.source.csv: differs\n")
    assert out.splitlines()[-1] == "check: 0 of 1 figures match gold"
    assert rec.check_args is not None and rec.check_args[0] == ["accuracy_by_model"]


def test_main_check_keeps_a_failure_of_the_build(tmp_path, monkeypatch, capsys):
    Recorder(monkeypatch, no_data={"accuracy_by_model"})
    code, out, err = _run(["accuracy_by_model", "--runs", "r", "--out", str(tmp_path), "--check", "gold"], capsys)
    assert code == 1 and err == "accuracy_by_model: skipped (accuracy_by_model has nothing)\n"
    assert out == "check: 1 of 1 figures match gold\n"


def test_main_check_without_out_builds_in_a_temporary_folder(tmp_path, monkeypatch, capsys):
    rec = Recorder(monkeypatch)
    code, out, _err = _run(["accuracy_by_class", "--runs", "r", "--check", "gold"], capsys)
    assert code == 0
    out_dir = rec.builds[0][2]
    assert out_dir.name.startswith("tsbench-figures-") and not out_dir.exists()  # removed again
    assert rec.check_args is not None and rec.check_args[1] == out_dir
    assert out.splitlines()[0] == f"accuracy_by_class: written to {out_dir}"
