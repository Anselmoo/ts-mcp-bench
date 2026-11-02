"""Tests for the comparison page (tsbench.report.comparison)."""
from __future__ import annotations

import json
import re

import pytest

from tsbench.core import intervals
from tsbench.release.gate import GERMAN
from tsbench.report import comparison as cmp
from tsbench.report import page


def run(model="claude-haiku-5-5", cond="A", cls="numerical", outcome="correct", set_="first", tok=1000.0, sec=10.0,
        cost=0.01, task_id=None):
    return {"set": set_, "model": model, "cond": cond, "task_id": task_id or f"P-{cls}-01", "cls": cls,
            "outcome": outcome, "has_result": outcome != "na429", "out_tok": tok, "api_s": sec, "cost": cost}


def _own(page: str) -> str:
    """The page without the inlined libraries (d3 and the Figura bundle contain URLs, `url(#...)`, arcs and pies)."""
    page = re.sub(r'<script id="jfs-lib">.*?</script>', "", page, flags=re.S)
    return re.sub(r'<script id="fig-draw">.*?</script>', "", page, flags=re.S)


def _part(macro: str, ctx) -> str:
    """One section of the page, drawn by its macro in templates/comparison_parts.html.j2 from the module data."""
    return str(getattr(page.ENV.get_template("comparison_parts.html.j2").module, macro)(ctx))


def _specs(page: str, kind: str) -> list:
    out = []
    for m in re.finditer(r'<figure class="jfs[^"]*" data-kind="(\w+)".*?'
                         r'<script type="application/json" class="spec">(.*?)</script>',
                         page, flags=re.S):
        if m.group(1) == kind:
            out.append(json.loads(m.group(2)))
    return out


def data_of(runs, planned=None):
    return {"runs": runs, "planned": planned or {}, "costs": {"first": 1.5}, "notes": [], "date": "2026-10-24"}


def many(n_ok, n_all, **kw):
    return [run(outcome="correct" if i < n_ok else "wrong", **kw) for i in range(n_all)]


# ---- 429 exclusion
# the runs the scorer leaves out of every rate (score.not_evaluable_reason): the page must agree with it
NOT_EVALUABLE_RESULTS = [
    ({"api_error_status": 429, "result": "x"}, "rate_limited"),
    ({"api_error_status": "429", "result": "x"}, "rate_limited"),
    ({"result": "API rate limit exceeded"}, "rate_limited"),
    ({"result": "API Error: Request rejected (429)"}, "rate_limited"),
    ({"api_error_status": 502, "result": "Bad Gateway"}, "api_error"),
    ({"api_error_status": 503, "result": "API Error: 503 service unavailable"}, "api_error"),
    ({"terminal_reason": "api_error", "result": "x"}, "api_error"),
    ({"result": "API Error: connection reset"}, "api_error"),
]


def _set_with_result(tmp_path, over: dict):
    """A fake run set whose first transcript ends in a result event `over` (an error result, no answer)."""
    folder = _fake_run_set(tmp_path / "set")
    first = sorted(folder.glob("*/*/*/*.jsonl"))[0]
    lines = first.read_text(encoding="utf-8").splitlines()
    res = {k: v for k, v in json.loads(lines[-1]).items() if k != "structured_output"}
    res.update({"is_error": True, "subtype": "success", "api_error_status": None, **over})
    lines[-1] = json.dumps(res)
    first.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return folder, (first.parts[-3], first.name.removesuffix("-k1.jsonl"))  # (condition, task id)


@pytest.mark.parametrize(("over", "why"), NOT_EVALUABLE_RESULTS)
def test_collect_leaves_out_the_runs_the_scorer_leaves_out(tmp_path, over, why):
    folder, key = _set_with_result(tmp_path, over)
    runs = cmp.collect([folder])["runs"]
    bad = next(r for r in runs if (r["cond"], r["task_id"]) == key)
    assert (bad["outcome"], bad["evaluable"]) == ("na429", False)
    assert bad["reason"] == {"rate_limited": "429", "api_error": "api_error"}[why]
    assert all(r["evaluable"] for r in runs if (r["cond"], r["task_id"]) != key)


def test_a_harness_limit_or_a_plain_error_stays_evaluable(tmp_path):
    folder, key = _set_with_result(tmp_path, {"subtype": "error_max_turns", "terminal_reason": "max_turns"})
    bad = next(r for r in cmp.collect([folder])["runs"] if (r["cond"], r["task_id"]) == key)
    assert (bad["evaluable"], bad["reason"]) == (True, "harness") and bad["outcome"] != "na429"


def test_score_in_memory_rows_are_the_rows_score_dir_writes(tmp_path):
    from tsbench.score import score as sc
    folder = _fake_run_set(tmp_path / "set")
    rows, results = cmp.score_in_memory(sc.find_transcripts(folder), cmp.load_tasks())
    written = {(r["model"], r["condition"], r["effort"], r["task_id"], r["k_index"]): r
               for r in sc.score_dir(folder, "pilot")["rows"]}
    assert len(rows) == len(written) == len(results) == 6
    for r in rows:
        want = written[(r["model"], r["condition"], r["effort"], r["task_id"], r["k_index"])]
        assert {c: sc._cell(r.get(c)) for c in sc.SCORE_COLUMNS} == {c: sc._cell(want.get(c)) for c in sc.SCORE_COLUMNS}
        assert r["_path"].endswith(f"{r['task_id']}-k{r['k_index']}.jsonl")


def test_429_excluded_from_accuracy_and_counted():
    rows = many(2, 4, cond="C") + [run(cond="C", outcome="na429") for _ in range(6)]
    assert cmp.accuracy_of(rows) == 50.0
    c = cmp.cell_counts(rows, planned=12)
    assert c["n429"] == 6 and c["n_eval"] == 4 and c["grey"] == 8 and c["n"] == 12


def test_open_model_runs_show_429_and_no_cost():
    runs = [run(model="gemma", cond="C", set_="open", outcome="na429") for _ in range(3)] \
        + [run(model="gemma", cond="C", set_="open") for _ in range(2)]
    page = cmp.build_html(data_of(runs))
    assert "not evaluable (429 or API error)" in page and "Cost: not shown" in page


def test_outcome_of_429_wins_over_error():
    assert cmp.outcome_of({"correct": "False", "has_result": "True", "is_error": "True"}, None, True) == "na429"
    assert cmp.outcome_of({"correct": "True"}, None, False) == "correct"


# ---- sentences
def test_sentences_empty():
    s = cmp.sentences([])
    assert len(s) == 3 and all(isinstance(x, str) and x for x in s)
    assert not re.search(r"\d+ %", " ".join(s))


def test_sentences_single_model_computed():
    runs = []
    for c, ok in (("A", 1), ("B", 2), ("C", 4)):
        runs += many(ok, 4, cond=c, tok={"A": 4000., "B": 3000., "C": 1000.}[c], sec={"A": 40., "B": 30., "C": 10.}[c])
    s = cmp.sentences(runs)
    assert len(s) == 3
    assert "Haiku 100 %" in s[0] and "A 25 %" in s[0] and "B 50 %" in s[0]
    assert "\u201cnumerical\u201d" in s[1] and "+50" in s[1]
    assert "67 % fewer output tokens" in s[2] and "75 % fewer output tokens" in s[2] and "67 % less API time" in s[2]
    assert "Opus" not in " ".join(s)


def test_sentence_numbers_follow_data():
    a = cmp.sentences(many(1, 4, cond="C"))
    b = cmp.sentences(many(3, 4, cond="C"))
    assert a[0] != b[0]


# ---- heatmap
def test_heatmap_class_order_a_accuracy_desc():
    runs = (many(4, 4, cond="A", cls="easy") + many(1, 4, cond="A", cls="mid") + many(0, 4, cond="A", cls="hard")
            + many(4, 4, cond="C", cls="easy") + many(4, 4, cond="C", cls="mid") + many(4, 4, cond="C", cls="hard"))
    assert cmp.heatmap_classes(runs) == ["easy", "mid", "hard"]
    page = cmp.build_html(data_of(runs))
    assert page.index(">easy<") < page.index(">mid<") < page.index(">hard<")
    assert "n=4" in page and "100 %" in page


def test_heat_color_scale_light_to_dark():
    lo, hi = cmp.heat_color(0.0), cmp.heat_color(1.0)
    lum = lambda h: sum(int(h[i:i + 2], 16) for i in (1, 3, 5))  # noqa: E731
    assert lum(lo[0]) > lum(hi[0])
    assert lo[1] == page.THEME["ink"] and hi[1] == "#ffffff"
    assert lo[0] == "#e6ebf6" and hi[0] == "#0039a6"  # Figura tint to Figura blue


def test_heatmap_excludes_429_from_cells():
    runs = many(1, 2, cond="A") + [run(cond="A", outcome="na429")] * 5
    page = cmp.build_html(data_of(runs))
    assert "50 %<small>n=2</small>" in page


# ---- differences, no verdict
def test_card_states_differences_not_a_verdict():
    """A model card says by how many points C's share differs from B's and A's, never "better" or "worse"."""
    runs = many(1, 5, cond="A") + many(1, 5, cond="B") + many(4, 5, cond="C")
    ctx = cmp.context(data_of(runs))
    card = ctx["verdict"]["sets"][0]["cards"][0]
    assert card["differences"] == "C \u2212 B +60 pp, C \u2212 A +60 pp (shares of the evaluable runs)"
    few = cmp.context(data_of(many(1, 2, cond="A") + many(1, 5, cond="C")))["verdict"]["sets"][0]["cards"][0]
    assert few["differences"] == "Too few evaluable runs for a difference"
    page = _own(cmp.build_html(data_of(runs)))
    assert "better" not in page.lower() and "worse" not in page.lower()


# ---- escaping, externals, no task text
def test_escaping():
    runs = [run(model="m<script>alert(1)</script>", cond="C", cls="<b>x</b>", set_="<i>set</i>")]
    page = cmp.build_html(data_of(runs))
    assert "<script>alert(1)" not in page and "<script>alert(1)" not in _own(page)
    assert "<b>x</b>" not in page and "<i>set</i>" not in page
    assert "&lt;script&gt;" in page or "&lt;b&gt;" in page


def test_no_external_urls():
    runs = many(2, 4, cond="C") + many(1, 4, cond="A")
    page = _own(cmp.build_html(data_of(runs)))  # d3 and the Figura bundle are inlined; their own URLs are not ours
    assert not re.findall(r"https?://[^\"'\s<)]+", page)
    assert not re.search(r"url\(", page) and "<script src" not in page and "@import" not in page


def test_only_pilot_tasks_loaded(monkeypatch):
    import tsbench.tasks as tasks
    seen = []
    real = tasks.load

    def spy(split, *a, **k):
        seen.append(split)
        return real(split, *a, **k)
    monkeypatch.setattr(tasks, "load", spy)
    t = cmp.load_tasks()
    assert seen == ["pilot"] and t
    secret = [x["prompt"] for x in real("pilot") if x.get("prompt")][:1]
    page = cmp.build_html(data_of(many(1, 2, cond="C")))
    assert all(p not in page for p in secret)


def test_page_is_english_and_has_sections():
    page = cmp.build_html(data_of(many(2, 4, cond="C")))
    for h in ("comparison of the conditions", "Summary", "Accuracy per run set and model",
              "Where the difference lies", "Cost and time", "Method in brief", "Pilot runs, not preregistered",
              "Run set first"):
        assert h in page
    assert 'lang="en"' in page and "share correct" in page
    # the page text is English: no umlaut and none of these common German words
    assert not GERMAN.search(_own(page))


@pytest.mark.parametrize("n", [0, 1])
def test_build_html_robust_on_tiny_input(n):
    page = cmp.build_html(data_of(many(n, n, cond="C")))
    assert page.startswith("<!doctype html>")


# ---- box plot statistics against numpy
@pytest.mark.parametrize("xs", [[1.0], [3.0, 1.0], [1, 2, 3, 4, 100], [0.5, 0.7, 0.71, 0.9, 1.1, 1.2, 9.0, 0.01],
                                list(range(1, 21)) + [500, 900]])
def test_box_stats_matches_numpy(xs):
    np = pytest.importorskip("numpy")
    st = cmp.box_stats(xs)
    a = np.asarray(xs, dtype=float)
    q1, med, q3 = np.percentile(a, [25, 50, 75])
    iqr = q3 - q1
    inside = a[(a >= q1 - 1.5 * iqr) & (a <= q3 + 1.5 * iqr)]
    assert st["n"] == len(a)
    assert st["q1"] == pytest.approx(q1) and st["median"] == pytest.approx(med) and st["q3"] == pytest.approx(q3)
    assert st["lo"] == pytest.approx(inside.min()) and st["hi"] == pytest.approx(inside.max())
    assert sorted(st["outliers"]) == sorted(a[(a < q1 - 1.5 * iqr) | (a > q3 + 1.5 * iqr)].tolist())


def test_box_stats_empty_and_nan():
    assert cmp.box_stats([]) is None
    assert cmp.box_stats([None, float("nan")]) is None
    assert cmp.box_stats([1, None, 3])["n"] == 2


def test_use_log_threshold():
    assert cmp.use_log([0.001, 0.05]) and not cmp.use_log([1, 30]) and cmp.use_log([1, 30.5])
    assert not cmp.use_log([]) and not cmp.use_log([0, 0])


def test_boxplot_figures_one_axis_log_label_and_hatch():
    rows = [run(cond=c, outcome=o, cost=v) for c in "ABC" for o in ("correct", "wrong")
            for v in (0.001, 0.002, 0.003, 0.004, 0.5)]
    out = _part("boxplots", cmp._boxplots(rows))
    assert out.count('data-kind="box"') == 3  # cost, tokens, seconds: one model
    first = _specs(out, "box")[0]
    assert first["log"] and first["xLabel"].endswith(", log")  # cost: log, because the ratio is > 30
    assert [r["label"] for r in first["rows"]] == [f"{c} · {k}" for c in "ABC" for k in ("correct", "wrong")]
    # filled = correct, hatched = wrong (text in the label)
    assert [r["ok"] for r in first["rows"]] == [True, False] * 3
    assert "<title>" in page.RUNTIME_JS or ".append(\"title\")" in page.RUNTIME_JS
    assert "svg class=\"chart box\"" not in out and "whiskers (the most extreme value within 1.5 IQR" in out
    assert first["rows"][0]["st"]["n"] == 5 and first["rows"][0]["tip"].startswith("A · correct: n = 5")
    lo, hi = first["domain"]
    assert 0 < lo < 0.001 < 0.5 < hi


# ---- cost per correct answer
def test_split_stats_cost_per_correct():
    rows = [run(outcome="correct", cost=0.1), run(outcome="correct", cost=0.3), run(outcome="wrong", cost=0.6),
            run(outcome="na429", cost=9.0)]
    s = cmp.split_stats(rows, "cost")
    assert s["n_ok"] == 2 and s["n_bad"] == 1
    assert s["median_ok"] == pytest.approx(0.2) and s["median_bad"] == pytest.approx(0.6)
    assert s["total"] == pytest.approx(1.0) and s["per_correct"] == pytest.approx(0.5)


def test_split_stats_zero_correct_is_none():
    s = cmp.split_stats([run(outcome="wrong", cost=0.2), run(outcome="harness", cost=0.1)], "cost")
    assert s["n_ok"] == 0 and s["per_correct"] is None and s["median_ok"] is None
    assert s["total"] == pytest.approx(0.3) and s["median_bad"] == pytest.approx(0.15)
    assert cmp.split_stats([], "cost")["per_correct"] is None


def test_cost_split_page_zero_correct_and_chart():
    runs = [run(cond="A", outcome="wrong", cost=0.2), run(cond="C", outcome="correct", cost=0.1)]
    page = cmp.build_html(data_of(runs))
    assert "no correct answer" in page and "Cost per correct answer" in page


# ---- rules from the task records
def test_rules_read_from_records_and_cover_classes():
    tasks = list(cmp.load_tasks().values())
    rr = {r["cls"]: r["rule"] for r in cmp.rule_rows(tasks)}
    assert {t["class"] for t in tasks} == set(rr)
    assert "Dq 2 %" in rr["closed_form"] and "B 5 %" in rr["closed_form"] and "C" not in rr["closed_form"]
    assert "C 10 %" in rr["racah_c"] and rr["crossover"].endswith("Dq 2 %")
    assert "out_of_scope = true" in rr["out_of_scope"]
    assert "9 points" in rr["curve"] and "3 %" in rr["curve"] and "0.3 E/B" in rr["curve"]
    assert "8 entries" in rr["batch"] and "2 %" in rr["batch"]
    assert "52 of 54" in rr["diagram"]
    changed = [dict(t, tolerance=dict(t["tolerance"], Dq=0.07)) if t["class"] == "closed_form" else t for t in tasks]
    assert "Dq 7 %" in {r["cls"]: r["rule"] for r in cmp.rule_rows(changed)}["closed_form"]


def test_category_text_covers_taxonomy():
    from tsbench.score.taxonomy import CATEGORIES
    assert set(CATEGORIES) <= set(cmp.CATEGORY_TEXT)
    page = cmp.build_html(data_of(many(1, 2, cond="C")))
    assert all(f"<code>{c}</code>" in page for c in CATEGORIES) and "Scoring: when is an answer correct?" in page


# ---- worked examples: pilot tasks only
def _task(tid, split="pilot", **kw):
    t = {"id": tid, "class": "closed_form", "split": split, "answer_schema": "fit", "expect_out_of_scope": False,
         "required": ["Dq", "B"], "reference": {"Dq": 1000.0, "B": 600.0, "C": None},
         "tolerance": {"Dq": 0.02, "B": 0.05, "C": 0.1}}
    t.update(kw)
    return t


def _ex_run(tid, outcome, k):
    r = run(outcome=outcome, cls="closed_form")
    r.update({"task_id": tid, "path": f"{tid}-{k}"})
    return r


def test_pick_examples_pilot_only_and_recomputed():
    tasks = {"P-1": _task("P-1"), "C-1": _task("C-1", split="confirmatory")}
    answers = {"P-1-ok": {"Dq": 1005.0, "B": 598.0, "C": None, "out_of_scope": False},
               "P-1-bad": {"Dq": 1005.0, "B": 500.0, "C": None, "out_of_scope": False},
               "C-1-ok": {"Dq": 1000.0, "B": 600.0, "C": None, "out_of_scope": False},
               "C-1-bad": {"Dq": 1.0, "B": 600.0, "C": None, "out_of_scope": False}}
    runs = [_ex_run("C-1", "correct", "ok"), _ex_run("C-1", "wrong", "bad"), _ex_run("P-1", "correct", "ok"),
            _ex_run("P-1", "wrong", "bad")]
    for r in runs:
        r["path"] = f"{r['task_id']}-{'ok' if r['outcome'] == 'correct' else 'bad'}"
    ex = cmp.pick_examples(runs, tasks, read=answers.get)
    assert ex["correct"]["task_id"] == "P-1" and ex["wrong"]["task_id"] == "P-1"
    assert ex["wrong"]["check"]["ok"] is False and ex["correct"]["check"]["ok"] is True
    b = [r for r in ex["wrong"]["check"]["rows"] if r["param"] == "B"][0]
    assert b["rel"] == pytest.approx(100 / 600) and not b["ok"]
    # only confirmatory tasks: no example
    assert cmp.pick_examples(runs[:2], tasks, read=answers.get) is None


def test_pick_examples_skips_runs_where_recomputation_disagrees():
    tasks = {"P-1": _task("P-1")}
    runs = [_ex_run("P-1", "correct", "x"), _ex_run("P-1", "wrong", "y")]
    runs[0]["path"], runs[1]["path"] = "x", "y"
    answers = {"x": {"Dq": 1.0, "B": 1.0, "out_of_scope": False},
               "y": {"Dq": 1000.0, "B": 600.0, "out_of_scope": False}}
    assert cmp.pick_examples(runs, tasks, read=answers.get) is None


def test_real_examples_from_pilot_tasks_only():
    from tsbench.tasks import load
    pilot_ids = {t["id"] for t in load("pilot")}
    runs = [dict(_ex_run("P-closed_form-01", "correct", "a"), path="a"),
            dict(_ex_run("P-closed_form-01", "wrong", "b"), path="b")]
    answers = {"a": {"Dq": 1376, "B": 608, "C": None, "out_of_scope": False},
               "b": {"Dq": 1376, "B": 530, "C": None, "out_of_scope": False}}
    ex = cmp.pick_examples(runs, cmp.load_tasks(), read=answers.get)
    assert ex["correct"]["task_id"] in pilot_ids and ex["wrong"]["task_id"] in pilot_ids
    page = cmp.build_html(dict(data_of(runs), examples=ex))
    assert "Example correct" in page and "Example wrong" in page and "12.93 %" in page and "Verdict: wrong" in page


# ---- reasons for missing answers
def test_reason_of_variants():
    assert cmp.reason_of({"is_error": True, "api_error_status": 429, "result": "x"}) == "429"
    assert cmp.reason_of({"is_error": True, "result": "API rate limit exceeded"}) == "429"
    assert cmp.reason_of({"is_error": True, "api_error_status": 500, "result": "boom"}) == "api_error"
    overflow = {"is_error": True, "api_error_status": 400, "result": "API Error: 400 prompt is too long"}
    assert cmp.reason_of(overflow) == "context_overflow"
    assert "context_overflow" in dict(cmp.REASON_COLUMNS)
    assert cmp.reason_of({"is_error": True, "subtype": "error_max_turns"}) == "harness"
    assert cmp.reason_of({"is_error": True, "subtype": "error_max_budget_usd"}) == "harness"
    assert cmp.reason_of(None) == "harness"
    assert cmp.reason_of({"is_error": False, "subtype": "success", "structured_output": None}) == "no_structured"
    assert cmp.reason_of({"is_error": False, "subtype": "success", "structured_output": {"Dq": 1}}) is None
    assert cmp.reason_of({"is_error": False, "structured_output": None}, correct=True) is None
    # the CLI gave up after repeated schema-invalid StructuredOutput calls: a missing structured_output, no API error
    retries = {"is_error": True, "subtype": "error_max_structured_output_retries", "result": ""}
    assert cmp.reason_of(retries) == "no_structured"
    assert cmp.reason_of(retries, correct=True) is None


def test_reason_breakdown_table():
    reasons = ["429"] * 3 + ["api_error"] + ["harness"] * 2 + ["no_structured"] + [None]
    runs = []
    for rs in reasons:
        r = run(model="gemma", cond="C", outcome="na429" if rs == "429" else "wrong")
        r["reason"] = rs
        runs.append(r)
    page = _part("section_reasons", cmp._reasons(data_of(runs)))
    cells = re.findall(r"<td class=\"num\">(\d+)</td>", page)
    assert cells == ["8", "3", "1", "0", "2", "1", "0"]  # runs, 429, API error, overflow, harness, missing, correct
    assert "structured_output missing" in page and "429 (rate limit)" in page
    assert cmp._reasons(data_of(many(2, 2, cond="C"))) is None   # no run without an answer: no section


def test_header_shows_how_many_answers_were_rescued():
    runs = many(2, 4, cond="C") + [{**run(cond="C"), "rescued": True} for _ in range(3)]
    page = cmp.build_html(data_of(runs))
    assert "of which 3 rescued" in page
    assert "rescued:" not in cmp.build_html(data_of(many(2, 4, cond="C")))


# ---- Figura design, no pie charts
def test_figura_design_inlined_and_no_pie_or_donut():
    runs = many(3, 5, cond="C") + many(1, 4, cond="A") + many(2, 4, cond="B")
    page = cmp.build_html(data_of(runs))
    assert "d3js.org v7.9.0" in page and "window.JFS" in page
    assert 'useTheme(darkPage()?"neutral-dark":"neutral")' in page
    own = _own(page)
    for c in ("#0039a6", "#b07800", "#b8336a"):  # series colours 1..3 for A, B, C
        assert c in own
    assert cmp.COLORS == {"A": "#0039a6", "B": "#b07800", "C": "#b8336a"}
    assert "donut" not in own.lower() and "d3.pie" not in own and "d3.arc" not in own
    assert "stroke-dasharray" not in own and "rotate(-90" not in own and "<svg class=\"donut\"" not in own
    assert own.count('data-kind="rate"') == 1


def per_task(outcomes, **kw):
    """k runs of every task: `outcomes` maps a task to its outcomes, one run each."""
    return [run(task_id=t, outcome=o, **kw) for t, os_ in outcomes.items() for o in os_]


def test_rate_rows_have_task_bootstrap_interval_and_every_status_icon_and_text():
    runs = per_task({"P-a-01": ["correct"], "P-b-01": ["correct"], "P-c-01": ["correct", "wrong"],
                     "P-d-01": ["wrong"]}, cond="C") + many(1, 4, cond="A")
    markup = cmp.build_html(data_of(runs))
    rows = _specs(markup, "rate")[0]["rows"]
    by = {r["cond"]: r for r in rows}
    assert by["C"]["correct"] == 3 and by["C"]["n_eval"] == 5 and by["C"]["p"] == pytest.approx(60.0)
    lo, hi = intervals.cluster_bootstrap([1, 1, 1, 0], [1, 1, 2, 1])
    assert by["C"]["lo"] == pytest.approx(100 * lo) and by["C"]["hi"] == pytest.approx(100 * hi)
    assert by["C"]["lo"] < 60 < by["C"]["hi"]
    own = _own(markup)
    for text in (page.STATUS_TEXT[k] for k in page.SEG_KEYS):
        legend = r'<span class="lg"[^>]*><i class="sw sw-\w+"></i><svg class="ic[^>]*>.*?</svg>'
        assert re.search(legend + re.escape(text), own)
    assert "3 of 5 correct (60 %" in own  # the text version beside the chart
    assert "Wilson" not in own


def test_the_interval_of_a_share_with_k_3_is_the_task_bootstrap_not_wilson():
    """25 tasks x k = 3: a task's three runs agree, so the interval over 75 runs would be about half as wide."""
    outcomes = {f"P-t{i:02d}-01": ["correct" if i < 12 else "wrong"] * 3 for i in range(25)}
    runs = per_task(outcomes, cond="C")
    markup = cmp.build_html(data_of(runs))
    row = _specs(markup, "rate")[0]["rows"][0]
    lo, hi = intervals.cluster_bootstrap([3] * 12 + [0] * 13, [3] * 25)
    assert row["lo"] == pytest.approx(100 * lo) and row["hi"] == pytest.approx(100 * hi)
    w_lo, w_hi = (100 * v for v in intervals.wilson(36, 75))
    assert row["hi"] - row["lo"] > 1.3 * (w_hi - w_lo)


def test_a_share_needs_five_evaluable_runs():
    """With 2 runs the 95 % interval spans 34 to 100 %: below five evaluable runs the chart shows counts, no share."""
    runs = many(2, 2, cond="C") + many(3, 5, cond="A")
    markup = cmp.build_html(data_of(runs))
    by = {r["cond"]: r for r in _specs(markup, "rate")[0]["rows"]}
    assert by["C"]["few"] and not by["A"]["few"] and page.MIN_SHARE_RUNS == 5
    own = _own(markup)
    assert "2 of 2 correct (fewer than 5 evaluable runs, no share)" in own and "2 of 2 correct (100 %" not in own
    assert "3 of 5 correct (60 %" in own
    assert "r.few" in page.RUNTIME_JS and "too few runs for a share" in page.RUNTIME_JS
    assert "Share correct (%), line: 95 % interval" in page.RUNTIME_JS
    assert "fitLabels(a,L-8)" in page.RUNTIME_JS  # narrow figures cut long labels and keep the condition


def test_not_evaluable_runs_are_their_own_outcome_excluded_from_rates():
    runs = many(2, 4, cond="C") + [run(cond="C", outcome="na429") for _ in range(2)]
    assert cmp.NOT_EVAL == ("na429",)
    assert cmp.accuracy_of(runs) == 50.0
    c = cmp.cell_counts(runs, planned=8)
    assert c["n429"] == 2 and c["n_eval"] == 4 and c["n"] == 8 and c["n_notrun"] == 2
    assert c["correct"] + c["wrong"] + c["harness"] + c["grey"] == c["n"]
    assert cmp.split_stats(runs, "cost")["n_ok"] == 2 and cmp.split_stats(runs, "cost")["n_bad"] == 2
    page_html = cmp.build_html(data_of(runs))
    own = _own(page_html)
    assert "Runs that are not evaluable" in own
    row = [r for r in _specs(page_html, "rate")[0]["rows"] if r["cond"] == "C"][0]
    assert [k for k, _v, _t in row["seg"]] == ["correct", "wrong", "harness", "na429", "notrun"] and row["n_eval"] == 4
    assert cmp.outcome_of({"correct": "False", "has_result": "True"}, None, False) == "wrong"
    assert cmp.outcome_of({"correct": "False"}, None, True) == "na429"
    heat = _part("section_heatmap", cmp._heatmap(data_of(runs)))
    assert "50 %<small>n=4</small>" in heat  # 429 runs are not in the heat map either


def _fake_run_set(folder, model="claude-haiku-5-5", title=None):
    """A run set made with the fake claude (dry run of the real runner): MANIFEST.json, plan, transcripts."""
    from tsbench.run import runner
    runner.main(["--split", "pilot", "--models", model, "--conditions", "A,B,C", "--effort", "medium", "--k", "1",
                 "--budget-usd", "10", "--out", str(folder), "--dry-run", "--limit", "2"])
    if title:
        (folder / "run_set.json").write_text(json.dumps({"title": title}), encoding="utf-8")
    return folder


def test_two_run_sets_found_by_discovery_are_grouped_by_title(tmp_path, capsys):
    root = tmp_path / "results"
    _fake_run_set(root / "set-a", title="First set <script>")
    _fake_run_set(root / "nested" / "set-b")
    out = tmp_path / "site" / "comparison.html"
    assert cmp.main(["--runs", str(root), "--out", str(out)]) == 0
    page = out.read_text(encoding="utf-8")
    # set-b keeps the title `tsbench run` wrote into its run_set.json (model, conditions, effort, k, split)
    assert "Run set First set &lt;script&gt;" in page and "Run set claude-haiku-5-5 | conditions A,B,C" in page
    assert "<script>" not in _own(page).replace('<script type="application/json" class="spec">', "")
    data = cmp.collect(cmp.run_sets_in([root]), out)
    assert {r["set"] for r in data["runs"]} == {"set-a", "nested/set-b"} and len(data["runs"]) == 12
    assert "file:" not in page and str(tmp_path) not in page


def test_shown_percentages_round_a_half_up_in_both_directions():
    assert [cmp._pct(x) for x in (2.5, 3.5, 4.5)] == ["3 %", "4 %", "5 %"]
    assert [page.signed(x) for x in (2.5, 3.5, -2.5, -3.5, 0.4)] == ["+3", "+4", "−3", "−4", "0"]
    assert cmp._direction(-2.5, "time") == "3 % fewer time"
    assert cmp._direction(3.5, "time") == "4 % more time"
    assert page.change_text(102.5, 100, "time") == "3 % more time"
    assert page.change_text(103.5, 100, "time") == "4 % more time"


def test_every_decimal_text_of_the_page_rounds_a_half_up() -> None:
    """_decimal feeds the median sentence, the metric rows and the rate rows; a half rounds up (2.5 gives 3, 3.5 gives
    4)."""
    assert [cmp._decimal(x, 0) for x in (2.5, 3.5, 3466.5, 3325.5)] == ["3", "4", "3467", "3326"]
    assert [cmp._decimal(x, 1) for x in (0.25, 0.35, 1.05)] == ["0.3", "0.4", "1.1"]
    assert cmp._decimal(0.0004, 3) == "0.000" and cmp._decimal(-0.0004, 3) == "0.000"
    assert cmp._decimal(float("inf")) == "inf"
