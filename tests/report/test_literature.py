"""Tests for the literature page (tsbench.report.literature)."""
from __future__ import annotations

import html
import pathlib
import re

import pytest
from markupsafe import Markup

from tsbench.release.gate import GERMAN
from tsbench.report import literature as ld
from tsbench.report import page


def _own(page: str) -> str:
    page = re.sub(r'<script id="jfs-lib">.*?</script>', "", page, flags=re.S)
    return re.sub(r'<script id="fig-draw">.*?</script>', "", page, flags=re.S)


@pytest.fixture(scope="module")
def empty_data(tmp_path_factory):
    d = tmp_path_factory.mktemp("pilot")
    return ld.collect([], d / "LITERATURE.html")


def _fake_run(data, ent, outcome="correct", dq=None, model="claude-haiku-5-5", cond="A", k=1):
    ref = ent["ref"]
    dq = ref["Dq"] if dq is None else dq
    vals = {"Dq": dq, "B": ref["B"], "C": ref["C"]}
    rel = {p: ld._relative_error(vals[p], ref[p]) for p in ld.PARAMS}
    path = pathlib.Path("/nonexistent/run/m/A/medium") / f"{ent['id']}-k{k}.jsonl"
    return {"key": ent["key"], "set": "x", "root": pathlib.Path("/nonexistent/run"), "model": model,
            "cond": cond, "effort": "medium", "k": k, "task": ent["id"], "outcome": outcome,
            "evaluable": outcome != "na429", "rescued": False,
            "vals": vals, "rel": rel, "path": path, "manifest": {},
            "pass": {p: ld._tol_ok(rel[p], ent["tol"].get(p)) for p in ent["required"]}}


def _render_macro(call: str, **ctx) -> str:
    env = page.ENV
    src = '{% from "literature_macros.html.j2" import doi_text %}' + call
    return str(env.from_string(src).render(**ctx))


def test_doi_link():
    parts = ld._doi_parts("Garcia Rojas, J. Chem. Educ. 2023, doi:10.1021/acs.jchemed.2c00885, Tables 1-2")
    assert [p["text"] for p in parts] == ["Garcia Rojas, J. Chem. Educ. 2023, doi:", "10.1021/acs.jchemed.2c00885",
                                          ", Tables 1-2"]
    assert [p["href"] for p in parts] == [None, "https://doi.org/10.1021/acs.jchemed.2c00885", None]
    h = _render_macro("{{ doi_text(parts) }}", parts=parts)
    assert '<a href="https://doi.org/10.1021/acs.jchemed.2c00885"' in h and ">10.1021/acs.jchemed.2c00885</a>" in h
    assert _render_macro("{{ doi_text(parts) }}", parts=ld._doi_parts("<b>x</b>")) == "&lt;b&gt;x&lt;/b&gt;"


def test_context_holds_data_not_markup(empty_data):
    ents = [e for e in empty_data["entries"].values() if e["cls"] == "literature_all"]
    data = dict(empty_data)
    data["runs"], data["shown"] = [_fake_run(data, ents[0])], {ents[0]["key"]}
    ctx = ld.context(data)
    seen = []

    def walk(x):
        if isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, (list, tuple)):
            for v in x:
                walk(v)
        elif isinstance(x, str):
            seen.append(x)
            assert not isinstance(x, Markup)
    walk(ctx)
    assert seen and not [t for t in seen if re.search(r"<(td|tr|div|table|a|span|b)\b", t)]


def test_names_from_data_are_escaped(empty_data):
    ents = [e for e in empty_data["entries"].values() if e["cls"] == "literature_all"]
    ent = dict(ents[0], system="<script>alert(1)</script>")
    data = dict(empty_data)
    data["entries"] = {ent["key"]: ent}
    data["runs"], data["shown"] = [_fake_run(data, ent, model="<i>m</i>")], {ent["key"]}
    data["notes"] = ["<b>note</b>"]
    own = _own(ld.build_html(data))
    assert "<script>alert(1)</script>" not in own and "&lt;script&gt;alert(1)&lt;/script&gt;" in own
    assert "<b>note</b>" not in own and "&lt;b&gt;note&lt;/b&gt;" in own
    assert "<i>m</i>" not in own


def test_paper_values_derivation():
    p = ld.paper_values({"Dq_cm-1": "1860", "DqB_reported": "2.8", "CB_reported": "",
                         "DqB_aux_diagram": "2.80", "CB_aux_diagram": ""})
    assert p["B"] == pytest.approx(1860 / 2.8) and p["C"] is None


def test_rubric_exclusions_published():
    ex = ld.read_rubric_exclusions()
    assert len(ex) >= 1 and all(x["reason"] for x in ex)
    assert any(x.get("fit") for x in ex)


def test_entries_are_pilot_and_paper_matches_task(empty_data):
    ents = empty_data["entries"]
    assert any(e["cls"] == "literature_all" for e in ents.values())
    assert all(e["id"].startswith("P-") for e in ents.values())
    n = 0
    for e in ents.values():
        dev = (e["dev_task"] or {}).get("Dq_rel")
        if e["cls"] == "literature_all" and dev is not None and e["paper"].get("Dq"):
            assert e["ref"]["Dq"] / e["paper"]["Dq"] - 1 == pytest.approx(dev, abs=2e-3)
            n += 1
    assert n >= 1


def test_page_without_runs_and_with_runs(empty_data):
    data = dict(empty_data)
    ents = [e for e in data["entries"].values() if e["cls"] == "literature_all"]
    e0 = ents[0]
    limited = _fake_run(data, e0, outcome="na429", dq=e0["ref"]["Dq"] * 3)
    runs = [_fake_run(data, e0), _fake_run(data, e0, outcome="wrong", dq=e0["ref"]["Dq"] * 1.4, cond="C", k=2), limited,
            _fake_run(data, e0, outcome="na429", k=3)]
    data["runs"] = runs
    data["shown"] = {e0["key"]}
    markup = ld.build_html(data)
    own = _own(markup)
    assert "Fit results against the literature" in own and 'lang="en"' in own
    assert "<h2>Methods: where the numbers come from</h2>" in own and "not preregistered" in own
    assert own.index('id="lit-accuracy"') < own.index('id="lit-methods"')  # the accuracy before the method box
    assert 'class="na"' in own  # HTTP 429 or API error: grey
    assert "Reproduce" in own and ">transcript</a>" in own
    assert "correct" in own and "wrong" in own          # status with text
    assert "k repetitions" in own and "not independent" in own
    # the page text is English: no umlaut and none of these common German words
    assert not GERMAN.search(own)
    assert "file:" not in own and 'href="/' not in own
    assert "<canvas" not in own and "donut" not in own.lower()
    assert "pie" not in re.sub(r"[a-z]pie|pie[a-z]", "", own.lower())
    # 429 and API errors do not enter the rate: 1 correct + 1 wrong evaluable
    assert "1 of 2" in own
    assert "Excluded systems" in own and "https://doi.org/10.1021/acs.jchemed.2c00885" in own


def test_accuracy_interval_is_the_task_bootstrap_for_k_3(empty_data):
    """Four tasks x k = 3 runs of one cell: the interval resamples tasks and keeps their runs together."""
    from tsbench.core import intervals
    data = dict(empty_data)
    ents = [e for e in data["entries"].values() if e["cls"] == "literature_all"][:4]
    assert len(ents) == 4
    data["runs"] = [_fake_run(data, e, outcome="correct" if i < 2 else "wrong", k=k)
                    for i, e in enumerate(ents) for k in (1, 2, 3)]
    data["shown"] = {e["key"] for e in ents}
    row = ld._accuracy(data)[0]["rows"][0]
    lo, hi = intervals.cluster_bootstrap([3, 3, 0, 0], [3, 3, 3, 3])
    assert row["n_eval"] == 12 and row["lo"] == pytest.approx(100 * lo) and row["hi"] == pytest.approx(100 * hi)
    w_lo, w_hi = (100 * v for v in intervals.wilson(6, 12))
    assert row["hi"] - row["lo"] > w_hi - w_lo
    own = _own(ld.build_html(data))
    assert "Wilson" not in own and "task-clustered" in own


def test_no_confirmatory_leak(empty_data):
    """Never prints names. Forbidden = confirmatory ids/systems, minus every pilot name (a system can sit in the
    pilot of one class and the confirmatory split of another; the page may show it as the pilot task it is)."""
    from tsbench.tasks import load
    conf, pilot_sys = [], set()
    for v in ("v2",):
        for t in load("pilot", version=v):
            pilot_sys.add(t.get("system"))
        try:
            conf += load("confirmatory", version=v)
        except Exception:  # noqa: BLE001
            pass
    forbidden = {t["id"] for t in conf} | {t["system"] for t in conf if t.get("system")}
    forbidden = {f for f in forbidden if f and f not in pilot_sys}
    data = dict(empty_data)
    from tsbench.report import literature as mod
    runs = []
    for e in data["entries"].values():
        runs.append(_fake_run(data, e))
    data["runs"], data["shown"] = runs, {e["key"] for e in data["entries"].values()}
    page = _own(mod.build_html(data))
    hits = sum(1 for f in forbidden if f in page or html.escape(f) in page or html.escape(f, quote=False) in page)
    assert hits == 0, "confirmatory leak"
    assert len(forbidden) > 0, "forbidden set unexpectedly empty"


def test_cli_reads_literature_runs_of_two_run_sets(tmp_path, capsys):
    """Two run sets made with the fake claude, each holding one literature task; the page groups the rows by run set."""
    from tsbench.plan import __main__ as plan_cli
    from tsbench.run import runner
    from tsbench.tasks import load
    lit = next(t["id"] for t in load("pilot") if t["class"] == "literature_all")
    root = tmp_path / "results"
    plan = tmp_path / "plan" / "plan.jsonl"
    assert plan_cli.main(["build", "--split", "pilot", "--task-ids", lit, "--models", "claude-haiku-5-5",
                          "--conditions", "C", "--effort", "medium", "--k", "1", "--budget-usd", "10",
                          "--out-plan", str(plan)]) == 0
    for name in ("one", "two"):
        assert runner.main(["--plan", str(plan), "--out", str(root / name), "--dry-run"]) == 0
    out = tmp_path / "site" / "lit.html"
    capsys.readouterr()
    assert ld.main(["--runs", str(root), "--out", str(out)]) == 0
    assert "2 runs" in capsys.readouterr().out
    page = out.read_text(encoding="utf-8")
    assert "one, two" in page and "file:" not in page and str(tmp_path) not in page


@pytest.mark.parametrize("over", [
    {"api_error_status": 502, "result": "Bad Gateway"},
    {"terminal_reason": "api_error", "result": "x"},
    {"result": "API Error: connection reset"},
    {"api_error_status": "429", "result": "x"},
    {"result": "HTTP error (429) from the API"},
])
def test_collect_leaves_out_the_runs_the_scorer_leaves_out(tmp_path, over):
    """The literature page decides 'not evaluable' like score.not_evaluable_reason: an API error or a 429 given as a
    string or as '(429)' text is no evaluable failed run."""
    import json

    from tsbench.plan import __main__ as plan_cli
    from tsbench.run import runner
    from tsbench.tasks import load
    lit = next(t["id"] for t in load("pilot") if t["class"] == "literature_all")
    plan = tmp_path / "plan" / "plan.jsonl"
    assert plan_cli.main(["build", "--split", "pilot", "--task-ids", lit, "--models", "claude-haiku-5-5",
                          "--conditions", "C", "--effort", "medium", "--k", "1", "--budget-usd", "10",
                          "--out-plan", str(plan)]) == 0
    folder = tmp_path / "set"
    assert runner.main(["--plan", str(plan), "--out", str(folder), "--dry-run"]) == 0
    path = next(folder.glob("*/*/*/*.jsonl"))
    lines = path.read_text(encoding="utf-8").splitlines()
    res = {k: v for k, v in json.loads(lines[-1]).items() if k != "structured_output"}
    res.update({"is_error": True, "subtype": "success", "api_error_status": None, **over})
    path.write_text("\n".join([*lines[:-1], json.dumps(res)]) + "\n", encoding="utf-8")
    runs = ld.collect([folder])["runs"]
    assert [(r["outcome"], r["evaluable"]) for r in runs] == [("na429", False)]


def test_literature_new_entries_read_the_second_table(empty_data):
    ents = [e for e in empty_data["entries"].values() if e["cls"] == "literature_new"]
    assert ents and all(e["id"].startswith("P-literature_new-") for e in ents)
    for e in ents:  # the paper values come from literature-spectra-2.csv and match the task's own copy
        assert e["csv"] and e["csv"].get("location")
        assert e["paper"]["Dq"] == pytest.approx(e["paper_task"]["Dq_cm-1"])
    data = dict(empty_data)
    data["runs"], data["shown"] = [_fake_run(data, ents[0])], {ents[0]["key"]}
    h = _own(ld.build_html(data))
    assert "Location:" in h and "forward model, least squares" in h and ld.CLASS_SHORT["literature_new"] in h
