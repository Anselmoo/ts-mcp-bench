"""Tests for `tsbench tasks check-oracle` (tsbench.tasks.oracles.check).

Most tests use a stand-in for tanabesugano's fit_spectrum, so that the CSV rows can be checked against numbers
worked out by hand. One test runs the real fit on a synthetic system.
"""
import csv
import math
import re
import runpy
import sys
from types import SimpleNamespace

import pytest

from tsbench.tasks.oracles import check

HEADER = ["config", "system", "band1_cm-1", "band2_cm-1", "band3_cm-1", "Dq_cm-1"]
# Dq = 1000 and B = 800 give nu1 = 10 Dq = 10000 and nu2 + nu3 = 15 B + 30 Dq = 42000,
# nu2 * nu3 = 18 * 42000 * 1000 - 340 * 1000**2 = 416e6, hence nu2 = 16000 and nu3 = 26000.
IDEAL = ["10000", "16000", "26000"]


def band_row(config="d3(Oh)/d7(Td)", system="X", bands=("", "", ""), dq=""):
    return dict(zip(HEADER, [config, system, *bands, dq], strict=True))


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=HEADER)
        w.writeheader()
        w.writerows(rows)
    return path


def read_out(path):
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def test_bands_reads_three_numbers():
    assert check.bands(band_row(bands=("8500", "13500", "25300"))) == [8500.0, 13500.0, 25300.0]


def test_bands_drops_the_approximately_sign_and_blanks():
    assert check.bands(band_row(bands=("≈8500", " 13500 ", "≈ 25300"))) == [8500.0, 13500.0, 25300.0]


@pytest.mark.parametrize("missing", [0, 1, 2])
def test_bands_is_none_when_any_band_is_empty(missing):
    vals = ["8500", "13500", "25300"]
    vals[missing] = "  "
    assert check.bands(band_row(bands=vals)) is None


def test_d_counts_cover_only_octahedral_d3_and_d8():
    assert check.D_COUNT == {"d3(Oh)/d7(Td)": 3, "d8(Oh)/d2(Td)": 8}


def test_out_is_required(capsys):
    with pytest.raises(SystemExit) as exc:
        check.main([])
    assert exc.value.code == 2
    assert "--out" in capsys.readouterr().err


@pytest.fixture
def fits(monkeypatch):
    """Replace fit_spectrum. It returns Dq = nu1 / 10 + 10, B = 790 and rmse 5, and raises a long ValueError when d is 8
    and nu1 is 11111. Every call is logged."""
    from tanabesugano.mcp import _compute

    calls = []

    def fake(d, bands, spin_state):
        calls.append((d, list(bands), spin_state))
        if d == 8 and bands[0] == 11111.0:
            raise ValueError("no fit " + "x" * 200)
        return SimpleNamespace(Dq=bands[0] / 10 + 10, B=790.0, rmse_cm1=5.0)

    monkeypatch.setattr(_compute, "fit_spectrum", fake)
    return calls


def test_rows_hold_the_closed_form_the_fit_and_their_differences(tmp_path, monkeypatch, fits, capsys):
    data = write_csv(tmp_path / "lit.csv", [band_row(system="ideal", bands=IDEAL, dq="1200")])
    monkeypatch.setattr(check, "DATA", data)
    out = tmp_path / "nested" / "dir" / "out.csv"
    assert check.main(["--out", str(out)]) == 0
    (row,) = read_out(out)
    assert list(row) == ["system", "d", "nu1", "nu2", "nu3", "cf_dq_nu1", "cf_dq_quad", "cf_b_quad",
                         "cf_dq_disagreement", "fit_dq", "fit_b", "fit_rmse", "lit_dq", "fit_minus_cf_dq",
                         "fit_minus_lit_dq", "error"]
    assert (row["system"], row["d"]) == ("ideal", "3")
    assert [float(row[k]) for k in ("nu1", "nu2", "nu3")] == [10000.0, 16000.0, 26000.0]
    assert float(row["cf_dq_nu1"]) == 1000.0
    assert float(row["cf_dq_quad"]) == pytest.approx(1000.0, abs=0.05)
    assert float(row["cf_b_quad"]) == pytest.approx(800.0, abs=0.05)
    assert float(row["cf_dq_disagreement"]) == pytest.approx(0.0, abs=0.05)
    assert [float(row[k]) for k in ("fit_dq", "fit_b", "fit_rmse", "lit_dq")] == [1010.0, 790.0, 5.0, 1200.0]
    assert float(row["fit_minus_cf_dq"]) == pytest.approx(10.0, abs=0.05)
    assert float(row["fit_minus_lit_dq"]) == -190.0
    assert row["error"] == ""
    assert fits == [(3, [10000.0, 16000.0, 26000.0], "high")]
    assert capsys.readouterr().out == f"1 systems -> {out}\n"


def test_rows_without_three_bands_or_outside_d3_d8_are_skipped(tmp_path, monkeypatch, fits, capsys):
    data = write_csv(tmp_path / "lit.csv", [
        band_row(system="two bands", bands=("10000", "16000", "")),
        band_row(config="d2(Oh)/d8(Td)", system="wrong config", bands=IDEAL),
        band_row(config="d8(Oh)/d2(Td)", system="kept", bands=("≈10000", "16000", "26000")),
    ])
    monkeypatch.setattr(check, "DATA", data)
    out = tmp_path / "out.csv"
    assert check.main(["--out", str(out)]) == 0
    rows = read_out(out)
    assert [(r["system"], r["d"], r["nu1"]) for r in rows] == [("kept", "8", "10000.0")]
    assert rows[0]["lit_dq"] == "nan"  # no literature Dq in the table
    assert [c[0] for c in fits] == [8]
    assert capsys.readouterr().out == f"1 systems -> {out}\n"


def test_a_failed_fit_is_reported_with_nan_and_a_shortened_message_never_dropped(tmp_path, monkeypatch, fits):
    data = write_csv(tmp_path / "lit.csv", [
        band_row(config="d8(Oh)/d2(Td)", system="bad", bands=("11111", "17000", "27000"), dq="1111"),
        band_row(config="d8(Oh)/d2(Td)", system="good", bands=IDEAL, dq="1000"),
    ])
    monkeypatch.setattr(check, "DATA", data)
    out = tmp_path / "out.csv"
    assert check.main(["--out", str(out)]) == 0
    bad, good = read_out(out)
    assert bad["system"] == "bad"
    assert [bad[k] for k in ("fit_dq", "fit_b", "fit_rmse", "fit_minus_cf_dq", "fit_minus_lit_dq")] == ["nan"] * 5
    assert bad["error"] == ("no fit " + "x" * 200)[:120] and len(bad["error"]) == 120
    assert float(bad["cf_dq_nu1"]) == 1111.1  # the closed form is still reported
    assert good["error"] == "" and float(good["fit_dq"]) == 1010.0


def test_inconsistent_bands_give_nan_in_the_closed_form_columns(tmp_path, monkeypatch, fits):
    # nu2 and nu3 so close that the quadratic has no real root: dq_b returns nan for the quadratic values
    data = write_csv(tmp_path / "lit.csv", [band_row(bands=("10000", "20000", "20100"), dq="1000")])
    monkeypatch.setattr(check, "DATA", data)
    out = tmp_path / "out.csv"
    check.main(["--out", str(out)])
    (row,) = read_out(out)
    assert row["cf_dq_nu1"] == "1000.0"
    assert [row[k] for k in ("cf_dq_quad", "cf_b_quad", "cf_dq_disagreement", "fit_minus_cf_dq")] == ["nan"] * 4
    assert float(row["fit_dq"]) == 1010.0


def test_real_fit_recovers_the_synthetic_system(tmp_path, monkeypatch):
    data = write_csv(tmp_path / "lit.csv", [band_row(system="ideal", bands=IDEAL, dq="1000")])
    monkeypatch.setattr(check, "DATA", data)
    out = tmp_path / "out.csv"
    assert check.main(["--out", str(out)]) == 0
    (row,) = read_out(out)
    assert row["error"] == ""
    assert float(row["fit_dq"]) == pytest.approx(1000.0, rel=0.02)
    assert float(row["fit_b"]) == pytest.approx(800.0, rel=0.05)
    assert math.isfinite(float(row["fit_rmse"]))


# ----------------------------------------------------------------------------- the command line

def test_help_names_the_command_and_the_output_file(capsys, monkeypatch):
    monkeypatch.setenv("COLUMNS", "200")
    with pytest.raises(SystemExit) as exc:
        check.main(["--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert out.startswith("usage: tsbench tasks check-oracle [-h] --out OUT")
    assert "Check tanabesugano.fit_spectrum against the independent closed form and against the\n" in out
    assert "values reported in the literature table" not in out
    assert re.search(r"--out OUT +CSV file to write \(one row per system\)\n", out)


def decimals(text: str) -> int:
    return len(text.partition(".")[2])


@pytest.fixture
def precise_fit(monkeypatch):
    """A fit with long decimals, so that the rounding of every column shows."""
    from tanabesugano.mcp import _compute

    monkeypatch.setattr(_compute, "fit_spectrum",
                        lambda d, bands, spin_state: SimpleNamespace(Dq=1010.123456, B=790.456789, rmse_cm1=5.678901))


def test_every_number_column_is_rounded_to_one_decimal(tmp_path, monkeypatch, precise_fit):
    bands = ("10001.2", "16003.7", "26011.9")
    data = write_csv(tmp_path / "lit.csv", [band_row(system="x", bands=bands, dq="1000.04")])
    monkeypatch.setattr(check, "DATA", data)
    out = tmp_path / "out.csv"
    check.main(["--out", str(out)])
    (row,) = read_out(out)
    assert [row[k] for k in ("cf_dq_nu1", "fit_dq", "fit_b", "fit_rmse", "fit_minus_lit_dq")] == [
        "1000.1", "1010.1", "790.5", "5.7", "10.1"]
    for k in ("cf_dq_quad", "cf_b_quad", "cf_dq_disagreement", "fit_minus_cf_dq"):
        assert decimals(row[k]) == 1, (k, row[k])
    assert row["lit_dq"] == "1000.04"  # the literature value is copied, not rounded
    cf = check.dq_b(10001.2, 16003.7, 26011.9)
    assert float(row["cf_dq_quad"]) == pytest.approx(cf.dq_from_quadratic, abs=0.05)
    assert float(row["cf_b_quad"]) == pytest.approx(cf.b_from_quadratic, abs=0.05)
    assert float(row["cf_dq_disagreement"]) == pytest.approx(cf.dq_disagreement, abs=0.05)
    assert float(row["fit_minus_cf_dq"]) == pytest.approx(1010.123456 - cf.dq_from_quadratic, abs=0.05)


def test_a_failed_fit_gives_nan_for_every_fit_column(tmp_path, monkeypatch, fits):
    data = write_csv(tmp_path / "lit.csv", [band_row(config="d8(Oh)/d2(Td)", bands=("11111", "17000", "27000"))])
    monkeypatch.setattr(check, "DATA", data)
    out = tmp_path / "out.csv"
    check.main(["--out", str(out)])
    (row,) = read_out(out)
    assert row["fit_dq"] == row["fit_b"] == row["fit_rmse"] == "nan"
    assert row["lit_dq"] == "nan"


def test_a_quoted_line_break_in_the_table_is_kept_and_rows_end_with_crlf(tmp_path, monkeypatch, fits):
    name = "two\r\nlines"
    data = write_csv(tmp_path / "lit.csv", [band_row(system=name, bands=IDEAL, dq="1000")])
    monkeypatch.setattr(check, "DATA", data)
    out = tmp_path / "out.csv"
    check.main(["--out", str(out)])
    assert [r["system"] for r in read_out(out)] == [name]
    raw = out.read_bytes()
    assert raw.count(b"\r\n") == 3 and b"\r\r\n" not in raw  # header, the line break of the name, one row


def test_only_the_approximately_sign_is_dropped_from_a_band():
    with pytest.raises(ValueError):
        check.bands(band_row(bands=("X8500", "13500", "25300")))


def test_the_table_and_the_output_are_read_and_written_as_utf8_in_any_locale(tmp_path, ascii_python):
    data = write_csv(tmp_path / "lit.csv", [band_row(system="Cr³⁺ in Al₂O₃", bands=("≈10000", "16000", "26000"))])
    out = tmp_path / "out.csv"
    code = (
        "import pathlib, sys\n"
        "from types import SimpleNamespace\n"
        "from tanabesugano.mcp import _compute\n"
        "from tsbench.tasks.oracles import check\n"
        "_compute.fit_spectrum = lambda d, bands, spin_state: SimpleNamespace(Dq=1000.0, B=800.0, rmse_cm1=1.0)\n"
        "check.DATA = pathlib.Path(sys.argv[1])\n"
        "sys.exit(check.main(['--out', sys.argv[2]]))\n"
    )
    done = ascii_python(code, data, out)
    assert done.returncode == 0, done.stderr[-1500:]
    assert read_out(out)[0]["system"] == "Cr³⁺ in Al₂O₃"


def test_running_the_module_as_a_script_exits_with_the_result_of_main(tmp_path, monkeypatch, fits, capsys):
    out = tmp_path / "out.csv"
    monkeypatch.delitem(sys.modules, "tsbench.tasks.oracles.check")  # runpy re-executes the module as __main__
    monkeypatch.setattr(sys, "argv", ["check", "--out", str(out)])
    with pytest.raises(SystemExit) as exc:
        runpy.run_module("tsbench.tasks.oracles.check", run_name="__main__")
    assert exc.value.code == 0
    assert capsys.readouterr().out == f"{len(read_out(out))} systems -> {out}\n"
    assert len(fits) == len(read_out(out)) > 0
