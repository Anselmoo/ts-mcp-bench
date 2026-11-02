"""Tests for tsbench.stats.metrics against the interfaces in docs/methods.md, section 5, with stand-in metric modules.

The four metric modules are replaced by recording stand-ins, and tasks come from a fake `load`, so these tests
need no other module and no confirmatory task. No API call, no `claude`.
"""
from __future__ import annotations

import csv
from types import SimpleNamespace

import pytest

from tsbench.stats import metrics as report

SCORE_ROWS = [
    {"model": "m1", "condition": c, "effort": "medium", "task_id": f"T{i}", "k_index": "1", "class": "closed_form",
     "subtype": "x", "correct": ok}
    for c in "ABC" for i, ok in ((1, "True"), (2, "False"))
]


class Standins:
    """Recording stand-ins for sensitivity, taxonomy, tool_use and descriptive."""

    def __init__(self):
        self.calls = {}
        self.versions = {}
        self.sens = SimpleNamespace(SENSITIVITY_COLUMNS=["model", "condition", "effort", "scale", "n", "n_correct",
                                                         "accuracy"], tolerance_curve=self.tolerance_curve)
        self.tax = SimpleNamespace(
            SCOPE_COLUMNS=["model", "condition", "effort", "n_expected_oos", "limit_naming_rate", "false_refusal_rate"],
            FAILURE_COLUMNS=["model", "condition", "effort", "category", "n", "share"],
            scope_confusion=self.scope_confusion, failure_table=self.failure_table)
        self.tool = SimpleNamespace(TOOL_USE_COLUMNS=["model", "condition", "effort", "task_id", "expected_tool_used",
                                                      "tool_error_rate"], tool_use_rows=self.tool_use_rows)
        self.desc = SimpleNamespace(PER_CLASS_COLUMNS=["model", "condition", "effort", "grouping", "group", "n"],
                                    CONSISTENCY_COLUMNS=["model", "condition", "effort", "n_tasks", "median_cv_dq"],
                                    per_class_accuracy=self.per_class, consistency=self.consistency)

    def tolerance_curve(self, runs, split="pilot", **kw):
        self.calls["tolerance_curve"] = (runs, split)
        self.calls["tolerance_curve_kw"] = kw
        self.versions["tolerance_curve"] = kw.get("version")
        return [{"model": "m1", "condition": "A", "effort": "medium", "scale": 0.25, "n": 2, "n_correct": 1,
                 "accuracy": 0.5}]

    def scope_confusion(self, rows, tasks):
        self.calls["scope_confusion"] = (rows, tasks)
        return [{"model": "m1", "condition": c, "effort": "medium", "n_expected_oos": 3,
                 "limit_naming_rate": 2 / 3 if c == "A" else None, "false_refusal_rate": float("nan")} for c in "ABC"]

    def failure_table(self, rows, tasks):
        self.calls["failure_table"] = (rows, tasks)
        return [{"model": "m1", "condition": c, "effort": "medium", "category": cat, "n": n, "share": n / 2}
                for c in "ABC" for cat, n in (("correct", 1), ("gross_error", 1), ("budget", 0))]

    def tool_use_rows(self, runs, split="pilot", version="v2", transcripts=None):
        self.calls["tool_use_rows"] = (runs, split)
        self.calls["tool_use_rows_cache"] = transcripts
        self.versions["tool_use_rows"] = version
        return [{"model": "m1", "condition": "C", "effort": "medium", "task_id": "T1", "expected_tool_used": ok,
                 "tool_error_rate": 0.0} for ok in (True, True, False)] + [
            {"model": "m1", "condition": "A", "effort": "medium", "task_id": "T1", "expected_tool_used": None,
             "tool_error_rate": None}]

    def per_class(self, rows):
        self.calls["per_class"] = rows
        return [{"model": "m1", "condition": "A", "effort": "medium", "grouping": "class", "group": "closed_form",
                 "n": 2}]

    def consistency(self, rows):
        self.calls["consistency"] = rows
        return [{"model": "m1", "condition": "A", "effort": "medium", "n_tasks": 0, "median_cv_dq": None}]

    def modules(self):
        return self.sens, self.tax, self.tool, self.desc


@pytest.fixture
def env(tmp_path, monkeypatch):
    """Stand-in modules, a fake `load` that records its split, and a recording `score_dir` that writes scores.csv."""
    st = Standins()
    monkeypatch.setattr(report, "_modules", st.modules)
    loads, scored = [], []

    def fake_load(split, version="v2"):
        loads.append(split)
        st.versions["load"] = version
        return [{"id": "T1", "class": "closed_form", "secret": "do-not-print"},
                {"id": "T2", "class": "closed_form", "secret": "do-not-print"}]

    def fake_score_dir(runs, split="pilot", **kw):
        scored.append((runs, split))
        st.versions["score_dir"] = kw.get("version")
        env.scores_writer(runs / "scores.csv")
        return {"rows": [], "unknown": [], "n_blind": 0}

    monkeypatch.setattr("tsbench.tasks.load", fake_load)
    monkeypatch.setattr("tsbench.score.score.score_dir", fake_score_dir)
    runs = tmp_path / "runs"
    runs.mkdir()
    env = SimpleNamespace(st=st, loads=loads, scored=scored, runs=runs, scores_writer=write_scores)
    return env


def write_scores(path, rows=SCORE_ROWS):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def read(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.reader(fh))


def test_report_metric_files_order():
    assert report.METRIC_FILES == ("tolerance_curve", "scope_confusion", "failure_taxonomy", "tool_use", "per_class",
                                   "consistency")


def test_report_scores_when_missing_then_writes_all(env):
    paths = report.write_metrics(env.runs, "pilot")
    assert env.scored == [(env.runs, "pilot")]
    assert tuple(paths) == report.METRIC_FILES
    cols = {"tolerance_curve": env.st.sens.SENSITIVITY_COLUMNS, "scope_confusion": env.st.tax.SCOPE_COLUMNS,
            "failure_taxonomy": env.st.tax.FAILURE_COLUMNS, "tool_use": env.st.tool.TOOL_USE_COLUMNS,
            "per_class": env.st.desc.PER_CLASS_COLUMNS, "consistency": env.st.desc.CONSISTENCY_COLUMNS}
    for name, path in paths.items():
        assert path == env.runs / "metrics" / f"{name}.csv"
        assert read(path)[0] == cols[name]
        assert len(read(path)) > 1


def test_report_passes_csv_rows_tasks_and_runs(env):
    report.write_metrics(env.runs, "pilot")
    rows, tasks = env.st.calls["scope_confusion"]
    assert rows == [dict(r) for r in SCORE_ROWS] and all(isinstance(v, str) for v in rows[0].values())
    assert set(tasks) == {"T1", "T2"} and env.loads == ["pilot"]
    assert env.st.calls["failure_table"][0] == rows and env.st.calls["failure_table"][1] is tasks
    assert env.st.calls["per_class"] == rows
    assert env.st.calls["consistency"] == rows
    assert env.st.calls["tolerance_curve"] == (env.runs, "pilot")
    assert env.st.calls["tool_use_rows"] == (env.runs, "pilot")


def test_report_scores_again_even_when_scores_csv_exists(env):
    """scores.csv may be older than the transcripts (a resumed run): the metrics always describe one run set."""
    write_scores(env.runs / "scores.csv", SCORE_ROWS[:1])  # stale: from an earlier `tsbench score`
    report.write_metrics(env.runs)
    assert env.scored == [(env.runs, "pilot")]
    assert env.st.calls["per_class"] == [dict(r) for r in SCORE_ROWS]  # the fresh scores.csv, not the stale one


def test_report_cell_formatting(env):
    paths = report.write_metrics(env.runs)
    scope = read(paths["scope_confusion"])
    assert scope[1][-2:] == [repr(2 / 3), ""]  # float via repr, NaN as ''
    assert scope[2][-2:] == ["", ""]  # None as ''
    tools = read(paths["tool_use"])
    assert [r[4] for r in tools[1:]] == ["True", "True", "False", ""]
    assert read(paths["tolerance_curve"])[1][3:] == ["0.25", "2", "1", "0.5"]
    assert read(paths["consistency"])[1][-1] == ""


def test_report_main_prints_compact_summary(env, capsys):
    assert report.main(["--runs", str(env.runs), "--split", "pilot"]) == 0
    out = capsys.readouterr().out
    lines = out.splitlines()
    assert 3 < len(lines) <= 40
    assert "do-not-print" not in out
    row_c = next(line for line in lines if line.startswith("m1") and " C " in line)
    assert "2/3" in row_c and "gross_error 1" in row_c and "budget" not in row_c and "correct" not in row_c
    row_a = next(line for line in lines if line.startswith("m1") and " A " in line)
    assert "0.67" in row_a and row_a.count("-") >= 2  # missing rates and tool column print as '-'
    assert all((env.runs / "metrics" / f"{n}.csv").exists() for n in report.METRIC_FILES)


def test_report_summary_is_capped_at_forty_lines():
    rows = [{"model": f"m{i:02d}", "condition": "A", "effort": "medium", "correct": "True"} for i in range(80)]
    tables = {"scope_confusion": [], "failure_taxonomy": [], "tool_use": []}
    lines = report.summary_lines(rows, tables)
    assert len(lines) <= 39 and "more cells" in lines[-1]


def test_report_refuses_confirmatory_without_doi(env, capsys):
    runs = env.runs
    assert report.main(["--runs", str(runs), "--split", "confirmatory"]) == 2
    assert "--i-have-preregistered" in capsys.readouterr().err
    assert env.loads == [] and env.scored == []
    assert not (runs / "metrics").exists() and not (runs / "scores.csv").exists()


def test_report_refuses_confirmatory_with_a_value_that_is_no_doi(env, capsys):
    assert report.main(["--runs", str(env.runs), "--split", "confirmatory", "--i-have-preregistered", "x"]) == 2
    assert "<DOI>" in capsys.readouterr().err
    assert env.loads == [] and env.scored == []
    assert not (env.runs / "metrics").exists()


def test_report_confirmatory_with_doi_uses_that_split(env, capsys):
    assert report.main(["--runs", str(env.runs), "--split", "confirmatory", "--i-have-preregistered", "10.1234/x"]) == 0
    assert env.loads == ["confirmatory"] and env.scored == [(env.runs, "confirmatory")]
    assert env.st.calls["tolerance_curve"][1] == "confirmatory"
    assert "do-not-print" not in capsys.readouterr().out


def test_report_missing_runs_dir(env, tmp_path, capsys):
    assert report.main(["--runs", str(tmp_path / "nope"), "--split", "pilot"]) == 2
    assert "not a directory" in capsys.readouterr().err and env.loads == []


def test_report_rejects_unknown_split(env):
    with pytest.raises(SystemExit) as exc:
        report.main(["--runs", str(env.runs), "--split", "nonsense"])
    assert exc.value.code == 2


def test_report_empty_scores_still_writes_headers(env, capsys):
    env.scores_writer = lambda path: path.write_text(",".join(SCORE_ROWS[0]) + "\n", encoding="utf-8")
    assert report.main(["--runs", str(env.runs)]) == 0
    assert read(env.runs / "metrics" / "per_class.csv")[0] == env.st.desc.PER_CLASS_COLUMNS
    assert env.st.calls["per_class"] == []


# ------------------------------------------------------------------ helpers, version flow, CLI and the summary format
import builtins  # noqa: E402
import importlib  # noqa: E402
import runpy  # noqa: E402
import sys  # noqa: E402
import warnings  # noqa: E402


@pytest.fixture
def open_calls(monkeypatch):
    """Record the arguments of every `open(...)` the metrics module makes (it still opens for real)."""
    calls = []

    def spy(*args, **kwargs):
        calls.append((args[1:], kwargs))
        return builtins.open(*args, **kwargs)

    monkeypatch.setattr(report, "open", spy, raising=False)
    return calls


def test_cell_is_empty_for_missing_values_and_text_otherwise():
    assert report._cell(None) == "" and report._cell(float("nan")) == ""
    assert report._cell("abc") == "abc" and report._cell(3) == "3" and report._cell(True) == "True"
    assert report._cell(0.1 + 0.2) == "0.30000000000000004" and report._cell(2 / 3) == repr(2 / 3)
    assert report._cell(float("inf")) == "inf"


def test_is_true_accepts_only_true_and_its_csv_spelling():
    assert report._is_true(True) is True and report._is_true("True") is True
    for other in (False, "False", "true", "TRUE", None, "", 1, 0, "1"):
        assert report._is_true(other) is False


def test_pct_formats_two_decimals_and_dashes_for_missing():
    assert report._pct(None) == "-" and report._pct("") == "-" and report._pct(float("nan")) == "-"
    assert report._pct(0.5) == "0.50" and report._pct("0.666") == "0.67" and report._pct(0) == "0.00"
    assert report._pct(1) == "1.00"


def test_modules_are_the_four_metric_modules():
    mods = report._modules()
    assert [m.__name__ for m in mods] == ["tsbench.score.sensitivity", "tsbench.score.taxonomy",
                                          "tsbench.score.tool_use", "tsbench.stats.descriptive"]
    assert mods[3] is importlib.import_module("tsbench.stats.descriptive")


def test_write_writes_header_then_rows_as_utf8_without_line_translation(tmp_path, open_calls):
    path = tmp_path / "t.csv"
    report._write(path, ["a", "b"], [{"a": 1, "b": None}, {"a": "xé", "b": 0.5}])
    assert path.read_bytes() == "a,b\r\n1,\r\nxé,0.5\r\n".encode()
    assert open_calls == [(("w",), {"newline": "", "encoding": "utf-8"})]


def test_scores_csv_is_read_as_utf8_with_raw_line_breaks(env, open_calls):
    rows = [dict(SCORE_ROWS[0], subtype="a\r\nb é")]
    env.scores_writer = lambda path: write_scores(path, rows)
    report.write_metrics(env.runs)
    assert env.st.calls["per_class"][0]["subtype"] == "a\r\nb é"
    assert (("w",), {"newline": "", "encoding": "utf-8"}) in open_calls
    assert open_calls.count(((), {"newline": "", "encoding": "utf-8"})) == 1      # the one read of scores.csv


def test_version_defaults_to_v2_and_reaches_every_reader(env):
    report.write_metrics(env.runs)
    assert env.st.versions == {"score_dir": "v2", "load": "v2", "tolerance_curve": "v2", "tool_use_rows": "v2"}


def test_a_given_version_reaches_every_reader(env):
    report.write_metrics(env.runs, "pilot", "v3")
    assert env.st.versions == {"score_dir": "v3", "load": "v3", "tolerance_curve": "v3", "tool_use_rows": "v3"}
    other = env.runs.parent / "r2"
    other.mkdir()
    report._write_all(other, "pilot", "v4")
    assert set(env.st.versions.values()) == {"v4"}


def test_internal_defaults_are_the_pilot_split_and_v2(env):
    rows, tables, columns = report._compute(env.runs, "pilot")
    assert set(env.st.versions.values()) == {"v2"} and set(tables) == set(columns) == set(report.METRIC_FILES)
    env.st.versions.clear()
    report._write_all(env.runs, "pilot")
    assert set(env.st.versions.values()) == {"v2"} and len(env.st.versions) == 4
    env.st.versions.clear()
    report.write_metrics(env.runs)
    assert env.loads[-1] == "pilot" and set(env.st.versions.values()) == {"v2"} and len(env.st.versions) == 4


def test_write_all_creates_the_whole_metrics_path(env, monkeypatch):
    tables = {name: [] for name in report.METRIC_FILES}
    monkeypatch.setattr(report, "_compute", lambda runs, split, version: (
        [], tables, {name: ["a"] for name in report.METRIC_FILES}))
    runs = env.runs.parent / "not" / "yet" / "there"
    _, _, paths = report._write_all(runs, "pilot", "v2")
    assert paths["per_class"] == runs / "metrics" / "per_class.csv"
    assert paths["per_class"].read_bytes() == b"a\r\n"


def test_write_metrics_twice_reuses_the_metrics_folder(env):
    first = report.write_metrics(env.runs)
    second = report.write_metrics(env.runs)
    assert first == second and all(p.exists() for p in second.values())


def test_main_default_split_is_pilot_and_runs_is_required(env, capsys):
    assert report.main(["--runs", str(env.runs)]) == 0
    assert env.loads == ["pilot"]
    with pytest.raises(SystemExit) as exc:
        report.main([])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "usage: tsbench metrics" in err and "--runs" in err


def test_main_help_names_the_program_and_the_doi_argument(capsys):
    with pytest.raises(SystemExit) as exc:
        report.main(["--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert out.startswith("usage: tsbench metrics")
    description = "Write the six descriptive metric tables for a runs directory to <runs>/metrics/*.csv."
    assert description in " ".join(out.split())
    assert "--i-have-preregistered DOI" in out


def test_main_confirmatory_refusal_message_is_exact(env, capsys):
    assert report.main(["--runs", str(env.runs), "--split", "confirmatory"]) == 2
    captured = capsys.readouterr()
    assert captured.err == "refusing to report the confirmatory split without --i-have-preregistered <DOI>\n"
    assert captured.out == ""


def test_main_last_line_names_the_metrics_folder(env, capsys):
    assert report.main(["--runs", str(env.runs)]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[-1] == f"wrote 6 files to {env.runs / 'metrics'}"
    assert lines[0].startswith("model") and lines[0].rstrip().endswith("top failures")


def test_running_the_module_as_a_script_exits_with_main_status(env, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["metrics", "--runs", str(env.runs / "missing")])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)       # runpy: the module is already imported
        with pytest.raises(SystemExit) as exc:
            runpy.run_module("tsbench.stats.metrics", run_name="__main__")
    assert exc.value.code == 2


def srow(model, cond, effort, ok):
    return {"model": model, "condition": cond, "effort": effort, "correct": ok}


def test_summary_lines_exact_table():
    rows = ([srow("m1", "A", "medium", x) for x in ("True", "False", "True", True)]
            + [srow("m1", "C", "medium", x) for x in ("True", "True", "False", False, "False")]
            + [srow("m2", "C", "low", "True")])
    fail = [{"model": "m1", "condition": "C", "effort": "medium", "category": c, "n": n}
            for c, n in (("correct", 3), ("gross", 2), ("budget", 5), ("unit", 1), ("zero", 0), ("alpha", 2))]
    fail.append({"model": "m1", "condition": "A", "effort": "medium", "category": "gross", "n": 1})
    tables = {
        "scope_confusion": [
            {"model": "m1", "condition": "A", "effort": "medium", "limit_naming_rate": 0.5,
             "false_refusal_rate": None},
            {"model": "m1", "condition": "C", "effort": "medium", "limit_naming_rate": "",
             "false_refusal_rate": 0.123}],
        "failure_taxonomy": fail,
        "tool_use": ([{"model": "m1", "condition": "C", "effort": "medium", "expected_tool_used": v}
                      for v in (True, "True", False, None, "")]
                     + [{"model": "m1", "condition": "A", "effort": "medium", "expected_tool_used": True},
                        {"model": "m2", "condition": "C", "effort": "low", "expected_tool_used": "False"}]),
    }
    assert report.summary_lines(rows, tables) == [
        "model                 cd effort    n   acc limit refuse  tool  top failures",
        "m1                    A  medium    4  0.75  0.50      -  -     gross 1",
        "m1                    C  medium    5  0.40     -   0.12  2/3   budget 5, alpha 2, gross 2",
        "m2                    C  low       1  1.00     -      -  0/1   -",
    ]


def test_summary_lines_keep_a_table_of_exactly_thirty_nine_lines():
    rows = [srow(f"m{i:02d}", "A", "medium", "True") for i in range(38)]          # header + 38 cells = 39 lines
    lines = report.summary_lines(rows, {"scope_confusion": [], "failure_taxonomy": [], "tool_use": []})
    assert len(lines) == 39 and "more cells" not in lines[-1] and lines[-1].startswith("m37")


def test_summary_lines_cut_longer_tables_and_count_the_hidden_cells():
    rows = [srow(f"m{i:02d}", "A", "medium", "True") for i in range(39)]          # header + 39 cells = 40 lines
    lines = report.summary_lines(rows, {"scope_confusion": [], "failure_taxonomy": [], "tool_use": []})
    assert len(lines) == 39 and lines[-2].startswith("m36")
    assert lines[-1] == "... 2 more cells; see metrics/*.csv"
    rows = [srow(f"m{i:02d}", "A", "medium", "True") for i in range(80)]
    lines = report.summary_lines(rows, {"scope_confusion": [], "failure_taxonomy": [], "tool_use": []})
    assert len(lines) == 39 and lines[-1] == "... 43 more cells; see metrics/*.csv"


def test_not_evaluable_rows_stay_out_of_every_table_but_the_failure_taxonomy(env, monkeypatch):
    """HTTP 429 / API-error runs are in scores.csv with evaluable False; rates.csv and the hypotheses leave them out."""
    rows = [dict(r, evaluable="True", not_evaluable_reason="") for r in SCORE_ROWS]
    rows.append(dict(SCORE_ROWS[0], k_index="2", correct="False", evaluable="False",
                     not_evaluable_reason="rate_limited"))

    def fake_score_dir(runs, split="pilot", **kw):
        write_scores(runs / "scores.csv", rows)

    monkeypatch.setattr("tsbench.score.score.score_dir", fake_score_dir)
    out_rows, tables, _ = report._compute(env.runs, "pilot")
    assert len(env.st.calls["scope_confusion"][0]) == len(env.st.calls["per_class"]) == len(SCORE_ROWS)
    assert len(env.st.calls["consistency"]) == len(SCORE_ROWS) and len(out_rows) == len(SCORE_ROWS)
    assert len(env.st.calls["failure_table"][0]) == len(SCORE_ROWS) + 1
    assert all(r["evaluable"] == "True" for r in out_rows)


def test_a_scores_csv_without_an_evaluable_column_counts_every_row(env):
    report.write_metrics(env.runs)
    assert len(env.st.calls["per_class"]) == len(SCORE_ROWS)


def test_the_transcript_cache_is_shared_by_the_readers(env):
    report.write_metrics(env.runs)
    cache = env.st.calls["tool_use_rows_cache"]
    assert isinstance(cache, dict) and env.st.calls["tolerance_curve_kw"]["transcripts"] is cache


# ----------------------------------------------------- the real metric modules on a small run set (no stand-ins)

import json  # noqa: E402
import pathlib  # noqa: E402

FIX = pathlib.Path(__file__).resolve().parents[2] / "src" / "tsbench" / "run" / "fake_cli_fixtures"
MODEL = "claude-haiku-5-5"


def _transcript(path, text=None, status=None):
    """A condition A transcript: a result with `text`, or an API error with HTTP `status`."""
    path.parent.mkdir(parents=True, exist_ok=True)
    events = [json.loads((FIX / "init_A.json").read_text(encoding="utf-8"))]
    if status is None:
        events.append({"type": "result", "subtype": "success", "is_error": False, "result": text,
                       "usage": {"input_tokens": 1, "output_tokens": 1}})
    else:
        events.append({"type": "result", "subtype": "success", "is_error": True, "api_error_status": status,
                       "result": f"API Error: ({status})", "usage": {"input_tokens": 0, "output_tokens": 0}})
    path.write_text("".join(json.dumps(e) + "\n" for e in events), encoding="utf-8")


def _real_runs(tmp_path, ks=(1, 3), error_ks=(2,)):
    from tsbench.tasks import load

    t = next(x for x in load("pilot") if x["class"] == "closed_form")
    good = json.dumps({"Dq": t["reference"]["Dq"], "B": t["reference"]["B"], "C": None, "out_of_scope": False,
                       "reason": "t"})
    base = tmp_path / "runs" / MODEL / "A" / "medium"
    for k in ks:
        _transcript(base / f"{t['id']}-k{k}.jsonl", good)
    for k in error_ks:
        _transcript(base / f"{t['id']}-k{k}.jsonl", status=429)
    return tmp_path / "runs", t, good


def _table(runs, name):
    return list(csv.DictReader((runs / "metrics" / f"{name}.csv").open(encoding="utf-8", newline="")))


def test_http_429_runs_are_not_wrong_answers_in_any_metric(tmp_path):
    """k = 3 with run 2 rate limited: rates.csv has k = 2; every metrics table must agree with it."""
    runs, _, _ = _real_runs(tmp_path)
    report.write_metrics(runs, "pilot")
    row = next(r for r in _table(runs, "per_class") if r["grouping"] == "class")
    assert (row["n"], row["n_correct"], row["accuracy"]) == ("2", "2", "1.0")
    cons = _table(runs, "consistency")[0]
    assert (cons["n_tasks"], cons["n_unanimous"], cons["unanimity_rate"]) == ("1", "1", "1.0")
    assert {r["n"] for r in _table(runs, "tolerance_curve")} == {"2"}
    assert len(_table(runs, "tool_use")) == 2
    taxonomy = {r["category"]: r["n"] for r in _table(runs, "failure_taxonomy")}
    assert taxonomy["correct"] == "2" and sum(int(n) for n in taxonomy.values()) == 3  # kept: the run happened


def test_the_summary_accuracy_matches_the_score_summary(tmp_path, capsys):
    runs, _, _ = _real_runs(tmp_path)
    assert report.main(["--runs", str(runs)]) == 0
    line = next(ln for ln in capsys.readouterr().out.splitlines() if ln.startswith(MODEL))
    assert line.split()[3:5] == ["2", "1.00"]


def test_metrics_after_new_transcripts_describe_the_new_run_set(tmp_path):
    """A first run added two transcripts, a resumed run two more: the second metrics call sees all four."""
    runs, t, good = _real_runs(tmp_path, ks=(1, 2), error_ks=())
    report.write_metrics(runs, "pilot")
    for k in (3, 4):
        _transcript(runs / MODEL / "A" / "medium" / f"{t['id']}-k{k}.jsonl", good)
    report.write_metrics(runs, "pilot")
    row = next(r for r in _table(runs, "per_class") if r["grouping"] == "class")
    assert row["n"] == "4" and {r["n"] for r in _table(runs, "tolerance_curve")} == {"4"}
    assert len(_table(runs, "tool_use")) == 4


def test_every_transcript_is_opened_once(tmp_path, monkeypatch):
    from tsbench.score import extract

    runs, _, _ = _real_runs(tmp_path, ks=(1, 2, 3), error_ks=(4,))
    opened = []

    def spy(*args, **kwargs):
        opened.append(str(args[0]))
        return builtins.open(*args, **kwargs)

    monkeypatch.setattr(extract, "open", spy, raising=False)
    report.write_metrics(runs, "pilot")
    assert len([p for p in opened if p.endswith(".jsonl")]) == 4
