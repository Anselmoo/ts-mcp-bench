"""Tests for tsbench.report.quality (line coverage and mutation score of two measurements, before and after). Small
synthetic coverage.py and mutation files in tmp_path only."""
from __future__ import annotations

import json
import re

import pytest

from tsbench import cli
from tsbench.report import page
from tsbench.report import quality as q


def test_shown_percentages_round_a_half_up():
    assert [q._fmt(v) for v in (12.25, 2.25, None)] == ["12.3", "2.3", "–"]
    assert [q._signed(v) for v in (0.25, -0.25, 2.25, None)] == ["+0.3", "−0.3", "+2.3", "–"]
    assert q._change(1.0, 1.25) == 0.3 and q._change(1.25, 1.0) == -0.3

HOSTILE = '<img src=x onerror=alert(1)>"\'&'
HOSTILE_FILE = HOSTILE.replace("/", "_") + ".py"


def _cov(path, files: dict[str, tuple[int, int]], stamp: str = "2026-10-27T22:29:17.5") -> None:
    """A coverage.py JSON report (format 3): file -> (covered lines, statements)."""
    out = {}
    for name, (c, n) in files.items():
        out[name] = {"executed_lines": [], "missing_lines": [], "excluded_lines": [],
                     "summary": {"covered_lines": c, "num_statements": n, "missing_lines": n - c,
                                 "percent_covered": 100.0 * c / n if n else 100.0}}
    c, n = sum(v[0] for v in files.values()), sum(v[1] for v in files.values())
    path.write_text(json.dumps({"meta": {"format": 3, "version": "7.17.0", "timestamp": stamp}, "files": out,
                                "totals": {"covered_lines": c, "num_statements": n,
                                           "percent_covered": 100.0 * c / n}}), encoding="utf-8")


def _lane(root, name, k0, s0, killed, survived, survivors=None, survivors_file="survivors-after.json",
          where=None) -> None:
    """A mutation lane: baseline summary k0 killed / s0 survived; the re-run of the baseline survivors killed
    `killed`."""
    d = root / name
    d.mkdir(parents=True)
    base = {"lane": name, "package": f"src/tsbench/{name}", "tool": "mutmut 3.8.1",
            "summary": {"total_mutants": k0 + s0 + 3, "killed": k0, "survived": s0, "timeout": 1, "no tests": 2,
                        "score_pct_killed_over_checked": round(100 * k0 / (k0 + s0), 2)},
            "survivors": [{"mutant": f"tsbench.{name}.x_f__mutmut_{i}", "module": f"tsbench.{name}", "diff": "-"}
                          for i in range(s0)]}
    (d / "baseline-survivors.json").write_text(json.dumps(base), encoding="utf-8")
    (d / "kill.json").write_text(json.dumps({"killed_now": killed, "equivalent": ["a: same", "b: same"],
                                             "still_alive": []}), encoding="utf-8")
    after = {"package": base["package"], "mutants": killed + survived, "killed": killed, "survived": survived,
             "timeout": 0, "score_pct": round(100 * (k0 + killed) / (k0 + s0), 2), "survivors_file": survivors_file}
    (d / "after.json").write_text(json.dumps(after), encoding="utf-8")
    if survivors is not None:
        target = where or d / "survivors-after.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps({"lane": name, "survivors": [
            {"mutant": m, "module": mod, "diff": "-"} for mod, m in survivors]}), encoding="utf-8")


@pytest.fixture
def evidence(tmp_path):
    """Before: tests inside src/, a renamed module, a module removed later. After: a new module, one drop."""
    ev = tmp_path / "evidence"
    ev.mkdir()
    _cov(ev / "before.json", {
        "src/tsbench/a/x.py": (80, 100), "src/tsbench/a/y.py": (50, 100), "src/tsbench/b/z.py": (10, 10),
        "src/tsbench/gone.py": (5, 10), "src/tsbench/old/m.py": (3, 10),
        "src/tsbench/a/test_x.py": (40, 40), "src/tsbench/conftest.py": (9, 10), "src/tsbench/b/conftest.py": (1, 1),
    })
    _cov(ev / "after.json", {
        "src/tsbench/a/x.py": (69, 100), "src/tsbench/a/y.py": (90, 100), "src/tsbench/b/z.py": (10, 10),
        "src/tsbench/new.py": (1, 2), "src/tsbench/c/m.py": (10, 10),
    }, stamp="2026-10-29T14:01:50.4")
    (ev / "renames.tsv").write_text("# old\tnew\n\nold/m.py\tc/m.py\nnot/there.py\tnowhere.py\n", encoding="utf-8")
    mut = ev / "mutation"
    _lane(mut, "alpha", 75, 25, 20, 5, survivors=[("tsbench.alpha", f"tsbench.alpha.x_f__mutmut_{i}")
                                                     for i in range(5)])
    _lane(mut, "beta", 60, 40, 10, 3, survivors_file=".other/runs/R1/mut-beta/survivors-after.json",
          survivors=[("tsbench.beta.u", "tsbench.beta.u.x_g__mutmut_1"), ("tsbench.beta.v", HOSTILE)],
          where=ev / "other-runs" / "R1" / "mut-beta" / "survivors-after.json")
    return ev


def test_module_key_is_relative_to_the_package():
    assert q.module_key("src/tsbench/a/x.py") == "a/x.py"
    assert q.module_key("/data/checkout/src/tsbench/cli.py") == "cli.py"
    assert q.module_key("tsbench/b.py") == "b.py"


def test_test_files_are_left_out(evidence):
    before = q.load_coverage(evidence / "before.json")
    assert sorted(before) == ["a/x.py", "a/y.py", "b/z.py", "gone.py", "old/m.py"]
    assert before["a/x.py"] == (80, 100)


def test_renames_map_old_names_to_new_ones(evidence):
    renames = q.read_renames(evidence / "renames.tsv")
    assert renames == {"old/m.py": "c/m.py", "not/there.py": "nowhere.py"}
    before = q.load_coverage(evidence / "before.json", renames)
    assert "old/m.py" not in before and before["c/m.py"] == (3, 10) and "nowhere.py" not in before


def test_a_bad_renames_line_is_an_error(tmp_path):
    (tmp_path / "r.tsv").write_text("only-one-column\n", encoding="utf-8")
    with pytest.raises(ValueError, match="line 1"):
        q.read_renames(tmp_path / "r.tsv")


def test_coverage_numbers_per_module_package_and_total(evidence):
    cov = q.compare(q.load_coverage(evidence / "before.json", q.read_renames(evidence / "renames.tsv")),
                    q.load_coverage(evidence / "after.json"))
    mods = {m["module"]: m for m in cov["modules"]}
    assert mods["a/x.py"]["before"] == 80.0 and mods["a/x.py"]["after"] == 69.0
    assert mods["a/x.py"]["change"] == -11.0 and mods["a/x.py"]["state"] == "dropped"
    assert mods["a/y.py"]["state"] == "improved" and mods["b/z.py"]["state"] == "same"
    assert mods["c/m.py"]["before"] == 30.0 and mods["c/m.py"]["after"] == 100.0
    assert mods["gone.py"]["state"] == "only_before" and mods["gone.py"]["after"] is None
    assert mods["new.py"]["state"] == "only_after" and mods["new.py"]["before"] is None
    assert cov["only_before"] == ["gone.py"] and cov["only_after"] == ["new.py"]
    assert cov["improved"] == ["a/y.py", "c/m.py"] and cov["dropped"] == ["a/x.py"]
    t = cov["total"]
    assert (t["covered_before"], t["statements_before"]) == (148, 230)
    assert (t["covered_after"], t["statements_after"]) == (180, 222)
    assert t["before"] == pytest.approx(100 * 148 / 230) and t["after"] == pytest.approx(100 * 180 / 222)
    pk = {p["package"]: p for p in cov["packages"]}
    assert pk["a"]["before"] == 65.0 and pk["a"]["after"] == 79.5
    assert pk["c"]["before"] == 30.0 and pk["(top level)"]["before"] == 50.0 and pk["(top level)"]["after"] == 50.0


def test_mutation_score_before_and_after_per_lane(evidence):
    lanes = {ln["lane"]: ln for ln in q.load_mutation(evidence / "mutation")}
    a, b = lanes["alpha"], lanes["beta"]
    assert a["before"] == 75.0 and a["after"] == 95.0 and a["left"] == 5 and a["rerun"] == 25
    assert b["before"] == 60.0 and b["after"] == 70.0 and b["left"] == 30 and b["not_rerun"] == 27
    assert a["equivalent"] == 2 and a["recorded_after"] == 95.0
    assert [s["module"] for s in a["survivors"]] == ["tsbench.alpha"] and len(a["survivors"][0]["mutants"]) == 5
    assert b["survivors_found"] and {s["module"] for s in b["survivors"]} == {"tsbench.beta.u", "tsbench.beta.v"}


def test_a_lane_without_its_survivors_list_still_has_its_scores(tmp_path):
    _lane(tmp_path / "m", "gamma", 50, 50, 25, 25)
    (ln,) = q.load_mutation(tmp_path / "m")
    assert ln["after"] == 75.0 and not ln["survivors_found"] and ln["survivors"] == []


def _page(evidence, tmp_path):
    hostile_before = tmp_path / "hb.json"
    _cov(hostile_before, {"src/tsbench/a/x.py": (80, 100), f"src/tsbench/{HOSTILE_FILE}": (9, 10)})
    hostile_after = tmp_path / "ha.json"
    _cov(hostile_after, {"src/tsbench/a/x.py": (69, 100), f"src/tsbench/{HOSTILE_FILE}": (1, 10)})
    facts = q.facts(hostile_before, hostile_after, mutation=evidence / "mutation")
    return facts, q.build_html(facts, generated="2026-10-30 12:00")


def test_page_escapes_and_has_both_figures(evidence, tmp_path):
    facts, html = _page(evidence, tmp_path)
    assert page.CSP_META in html and HOSTILE not in html and "&lt;img src=x onerror=alert(1)&gt;" in html
    assert "<img src=x" not in html
    assert str(tmp_path) not in html and "file:" not in re.sub(r'<script id="jfs-lib">.*?</script>', "", html,
                                                               flags=re.S)
    figs = re.findall(r'<figure class="jfs[^"]*" data-kind="dumbbell"', html)  # drawn by runtime.js
    assert len(figs) == 2
    assert html.count("<noscript>") == 2 and html.count("</noscript>") == 2
    for cap in re.findall(r"<figcaption>(.*?)</figcaption>", html, flags=re.S):
        assert "<" not in cap
    assert "dumbbell:function(root,s)" in html and "J.axes" in html and 'id="jfs-lib"' in html


def test_page_marks_drops_with_icon_and_text(evidence, tmp_path):
    _facts, html = _page(evidence, tmp_path)
    row = re.search(r"<tr[^>]*>\s*<td><code>a/x\.py</code>.*?</tr>", html, flags=re.S)
    assert row and "dropped" in row.group(0) and '<svg class="ic' in row.group(0)
    assert "<details" in html and "alpha" in html and "beta" in html


def test_page_names_modules_only_before_or_after(evidence):
    facts = q.facts(evidence / "before.json", evidence / "after.json", evidence / "renames.tsv",
                    evidence / "mutation")
    html = q.build_html(facts, generated="t")
    assert "gone.py" in html and "new.py" in html and "Only before" in html and "Only after" in html


def test_cli_writes_the_page_and_the_facts(evidence, tmp_path, capsys):
    out, js = tmp_path / "site" / "quality.html", tmp_path / "facts.json"
    rc = q.main(["--coverage-before", str(evidence / "before.json"), "--coverage-after", str(evidence / "after.json"),
                 "--renames", str(evidence / "renames.tsv"), "--mutation", str(evidence / "mutation"),
                 "--out", str(out), "--json", str(js)])
    assert rc == 0 and out.is_file()
    data = json.loads(js.read_text(encoding="utf-8"))
    assert {"coverage", "mutation"} <= set(data) and len(data["mutation"]) == 2
    assert "wrote" in capsys.readouterr().out


def test_cli_is_registered_after_report_coverage(evidence, tmp_path):
    words = list(cli.COMMANDS)
    assert words.index(("report", "quality")) == words.index(("report", "coverage")) + 1
    rc = cli.main(["report", "quality", "--coverage-before", str(evidence / "before.json"),
                   "--coverage-after", str(evidence / "after.json"), "--out", str(tmp_path / "p.html")])
    assert rc == 0 and (tmp_path / "p.html").is_file()


@pytest.mark.parametrize("problem", ["missing", "not_json", "not_coverage", "bad_renames", "no_mutation_dir"])
def test_cli_bad_input_exits_2(problem, evidence, tmp_path, capsys):
    before, renames, mutation = evidence / "before.json", None, None
    if problem == "missing":
        before = tmp_path / "nope.json"
    elif problem == "not_json":
        before = tmp_path / "x.json"
        before.write_text("{", encoding="utf-8")
    elif problem == "not_coverage":
        before = tmp_path / "x.json"
        before.write_text('{"a": 1}', encoding="utf-8")
    elif problem == "bad_renames":
        renames = tmp_path / "r.tsv"
        renames.write_text("a\tb\tc\n", encoding="utf-8")
    else:
        mutation = tmp_path / "no-such-dir"
    argv = ["--coverage-before", str(before), "--coverage-after", str(evidence / "after.json"),
            "--out", str(tmp_path / "p.html")]
    argv += ["--renames", str(renames)] if renames else []
    argv += ["--mutation", str(mutation)] if mutation else []
    assert q.main(argv) == 2
    assert "tsbench report quality:" in capsys.readouterr().err and not (tmp_path / "p.html").exists()


def test_cli_without_out_is_a_usage_error(evidence):
    with pytest.raises(SystemExit) as e:
        q.main(["--coverage-before", str(evidence / "before.json"), "--coverage-after", str(evidence / "after.json")])
    assert e.value.code == 2
