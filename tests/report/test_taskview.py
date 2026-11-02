"""What each pilot task asked (src/tsbench/report/taskview.py), as `facts.benchmark` keeps it in
`bench["tasks_view"]`: one block per class, one row per task, every field read from the task record, the literature
tables or the scored runs. The runs are the made-up runs of tests/report/test_facts.py on the real pilot records."""
from __future__ import annotations

import re

import pytest
from test_facts import SOLVES, TASKS, _data, _row  # the helpers of the facts tests

from tsbench.report import facts, literature, taskview

CLASSES = list(dict.fromkeys(t["class"] for t in TASKS.values()))


def _digits(text: str) -> str:
    """The text without any kind of space, so that "13 760" (thin or no-break spaces) reads "13760"."""
    return re.sub(r"[\s   ]", "", text)


def _view(data: dict | None = None) -> list[dict]:
    return facts._benchmark(data or _data(), {}, None).get("tasks_view") or []


@pytest.fixture(scope="module")
def bench() -> dict:
    return facts._benchmark(_data(), {}, None)


@pytest.fixture()
def view(bench) -> list[dict]:
    return bench.get("tasks_view") or []


def _rows(view: list[dict]) -> dict[str, dict]:
    rows = {r["id"]: r for b in view for r in b["tasks"]}
    assert rows, "no tasks_view in the bench"
    return rows


def test_class_definitions_are_one_line_for_each_of_the_fourteen_pilot_classes():
    assert set(taskview.CLASS_DEFINITIONS) == set(CLASSES) and len(CLASSES) == 14
    for cls, text in taskview.CLASS_DEFINITIONS.items():
        assert text and "\n" not in text and len(text) < 120, cls


def test_every_pilot_task_appears_exactly_once_in_task_file_order(view):
    assert [b["class"] for b in view] == CLASSES
    ids = [r["id"] for b in view for r in b["tasks"]]
    assert sorted(ids) == sorted(TASKS) and len(ids) == len(set(ids)) == 50
    for b in view:  # the file interleaves the classes, so a block lists its own tasks in file order
        assert [r["id"] for r in b["tasks"]] == [t for t in TASKS if TASKS[t]["class"] == b["class"]]
        assert b["n"] == len(b["tasks"]) and all(r["class"] == b["class"] for r in b["tasks"])
        assert b["definition"] == taskview.CLASS_DEFINITIONS[b["class"]]
        assert all(r["anchor"] == "task-" + r["id"] for r in b["tasks"])


def test_class_blocks_count_the_tasks_each_condition_solves(view):
    assert view
    for b in view:
        want = {c: (b["n"] if b["class"] in SOLVES[c] else 0) for c in "ABC"}
        assert b["k"] == want, b["class"]


def test_given_of_a_closed_form_task_lists_its_three_bands():
    row = _rows(_view())["P-closed_form-01"]
    given = _digits(" ".join(text for _, text in row["given"]))
    for band in TASKS["P-closed_form-01"]["bands_cm1"]:
        assert str(int(band)) in given
    assert "d3" in given and "Oh" in given


def test_given_of_a_curve_task_lists_its_parameters_and_grid(view):
    t = next(t for t in TASKS.values() if t["class"] == "curve")
    given = _digits(" ".join(text for _, text in _rows(view)[t["id"]]["given"]))
    assert str(int(t["params"]["B"])) in given and str(int(t["params"]["C"])) in given
    for x in t["params"]["dq_over_b"]:
        assert f"{x:g}" in given


def test_asked_names_the_required_parameters_or_the_answer_of_the_schema(view):
    rows = _rows(view)
    racah = next(t for t in TASKS.values() if t["class"] == "racah_c")
    assert "C" in re.split(r"[,\s]+", rows[racah["id"]]["asked"])
    assert rows["P-closed_form-01"]["asked"] == "Dq, B"
    crossover = next(t for t in TASKS.values() if t["class"] == "crossover")
    assert rows[crossover["id"]]["asked"] == "Dq"
    oos = next(t for t in TASKS.values() if t["class"] == "out_of_scope")
    assert rows[oos["id"]]["asked"].startswith("decline")
    diagram = next(t for t in TASKS.values() if t["class"] == "diagram")
    assert "54" in rows[diagram["id"]]["asked"]


def test_reference_holds_the_values_the_scorer_compares_and_folds_long_lists(view):
    rows = _rows(view)
    ref = TASKS["P-closed_form-01"]["reference"]
    text = _digits(" ".join(v for _, v in rows["P-closed_form-01"]["reference"]))
    assert str(round(ref["Dq"])) in text and str(round(ref["B"])) in text
    assert rows["P-closed_form-01"]["reference_more"] is None
    diagram = next(t for t in TASKS.values() if t["class"] == "diagram")
    d = rows[diagram["id"]]
    assert len(d["reference"]) <= 6 and d["reference_more"]


def test_curve_reference_values_round_a_half_up():
    task = {"answer_schema": "curve", "reference_curve": [{"dq_over_b": 1.0, "e_over_b": 0.125},
                                                          {"dq_over_b": 1.0, "e_over_b": 0.375}]}
    assert taskview._reference(task)[0] == [("Dq/B 1", "0.13 · 0.38")]


def test_literature_tolerance_names_only_the_required_parameters(view):
    rows = _rows(view)
    assert TASKS["P-literature_all-01"]["required"] == ["Dq", "B"]
    tol = rows["P-literature_all-01"]["tolerance"]
    assert "Dq 5 %" in tol and "B 10 %" in tol and not re.search(r"\bC\b", tol)
    assert rows["P-closed_form-01"]["tolerance"] == "Dq 2 %, B 5 %"


def test_tolerance_of_the_other_schemas_is_read_from_the_record(view):
    rows = _rows(view)
    curve = next(t for t in TASKS.values() if t["class"] == "curve")
    tol = rows[curve["id"]]["tolerance"]
    assert f"{100 * curve['tolerance']['curve_rel']:g} %" in tol and f"{curve['tolerance']['curve_abs']:g}" in tol
    batch = next(t for t in TASKS.values() if t["class"] == "batch")
    assert f"{100 * batch['tolerance']['item_rel']:g} %" in rows[batch["id"]]["tolerance"]
    assert "ground terms" in rows["P-pairing-01"]["tolerance"]
    oos = next(t for t in TASKS.values() if t["class"] == "out_of_scope")
    assert rows[oos["id"]]["tolerance"] == "must decline"


def test_source_of_a_literature_task_carries_its_doi_and_locator(view):
    rows = _rows(view)
    src = rows["P-experimental-01"]["source"]
    assert src["doi"] == "10.1021/acs.jchemed.2c00885" and src["locator"] == "Tables 1-2"
    assert "doi" not in src["text"] and src["text"].startswith("Garcia Rojas & Perez Torres")
    table = literature.read_csv_rows()
    assert table[literature._norm_name(TASKS["P-literature_new-03"]["system"])]  # the row the source is read from
    assert rows["P-literature_new-03"]["source"]["locator"] == "Table 3"


def test_source_of_a_synthetic_task_is_its_oracle(view):
    rows = _rows(view)
    assert rows["P-closed_form-01"]["source"]["text"].startswith("closed form (Underhill–Billing)")
    assert rows["P-closed_form-01"]["source"]["doi"] is None
    num = next(t for t in TASKS.values() if t["oracle"] == "forward_model")
    assert rows[num["id"]]["source"]["text"].startswith("forward model")


def test_the_prompt_is_the_one_of_the_task_record(view):
    rows = _rows(view)
    assert all(rows[t]["prompt"] == TASKS[t]["prompt"] for t in TASKS)


def test_fit_answers_print_the_reported_values_of_the_required_parameters(view):
    rows = _rows(view)
    t = TASKS["P-closed_form-01"]  # A solves closed_form: reported = reference x 1.001
    a = rows[t["id"]]["answers"]["A"]
    text = _digits(a["text"])
    assert str(round(t["reference"]["Dq"] * 1.001)) in text and str(round(t["reference"]["B"] * 1.001)) in text
    assert "C" not in re.split(r"[^A-Za-z]+", a["text"])
    assert (a["ok"], a["n_runs"], a["n_correct"]) == (True, 1, 1)
    assert a["category"] == "correct"
    b = rows[t["id"]]["answers"]["B"]  # B does not: reported = reference x 2
    assert b["ok"] is False and str(round(t["reference"]["Dq"] * 2)) in _digits(b["text"])
    assert b["category"] == dict(facts.CATEGORIES)[facts.FOLD["gross_error"]]


def test_answers_of_the_other_schemas_print_their_metric(view):
    rows = _rows(view)
    curve = next(t for t in TASKS.values() if t["class"] == "curve")
    assert "%" in rows[curve["id"]]["answers"]["C"]["text"]
    diagram = next(t for t in TASKS.values() if t["class"] == "diagram")
    assert re.search(r"\b1 of 54\b", rows[diagram["id"]]["answers"]["A"]["text"])
    batch = next(t for t in TASKS.values() if t["class"] == "batch")
    assert re.search(r"\b1 of 8\b", rows[batch["id"]]["answers"]["A"]["text"])
    assert "0.5" in rows["P-pairing-01"]["answers"]["A"]["text"]
    oos = next(t for t in TASKS.values() if t["class"] == "out_of_scope")
    assert rows[oos["id"]]["answers"]["A"]["text"] == "answered"


def test_ok_follows_the_majority_of_the_runs_for_k_two():
    data = _data()
    t = TASKS["P-closed_form-02"]
    data["rows"] += [_row("m1", "A", t, False, k=2),  # 1 of 2: not solved
                     _row("m1", "C", t, False, k=2)]  # 0 of 2: not solved
    data["rows"] += [_row("m1", "B", TASKS["P-numerical-01"], True, k=2)]  # 2 of 2: solved
    rows = _rows(_view(data))
    a = rows[t["id"]]["answers"]["A"]
    assert (a["ok"], a["n_runs"], a["n_correct"]) == (False, 2, 1)
    c = rows[t["id"]]["answers"]["C"]
    assert (c["ok"], c["n_runs"], c["n_correct"]) == (False, 2, 0)
    b = rows["P-numerical-01"]["answers"]["B"]
    assert (b["ok"], b["n_runs"], b["n_correct"]) == (True, 2, 2)


def test_run_anchor_is_the_html_id_of_the_run_card(view):
    for r in _rows(view).values():
        for cond, a in r["answers"].items():
            assert re.fullmatch(r"[A-Za-z][\w-]*", a["run_anchor"])
            assert a["run_anchor"] == taskview.run_anchor("m1", cond, "medium", r["id"], a["shown_k"])


def _with_runs(task_id: str, cond: str, flags: list[bool], patch: dict[int, dict] | None = None) -> dict:
    """The made-up data with `len(flags)` runs of one cell (k = 1, 2, ...), correct as `flags` say."""
    data = _data()
    t = TASKS[task_id]
    data["rows"] = [r for r in data["rows"] if not (r["task_id"] == task_id and r["_cond"] == cond)]
    for k, ok in enumerate(flags, 1):
        row = _row("m1", cond, t, ok, k=k)
        row.update((patch or {}).get(k, {}))
        data["rows"].append(row)
    return data


def test_the_answer_is_that_of_one_run_on_the_side_of_the_verdict_not_a_median():
    # k = 2: run 1 correct, run 2 wrong (Dq 1305): not solved, the cell shows run 2, not the mean 1 522 of both
    ref = TASKS["P-experimental-01"]["reference"]["Dq"]
    data = _with_runs("P-experimental-01", "A", [True, False], {2: {"dq": "1305.0"}})
    a = _rows(_view(data))["P-experimental-01"]["answers"]["A"]
    assert "1305" in _digits(a["text"]) and "1522" not in _digits(a["text"]) and "1523" not in _digits(a["text"])
    assert str(round(ref * 1.001)) not in _digits(a["text"])
    assert a["ok"] is False and a["shown_k"] == 2
    # k = 3, solved by runs 2 and 3: the first run on the majority side is run 2
    data = _with_runs("P-experimental-01", "A", [False, True, True], {2: {"dq": "1700.0"}, 3: {"dq": "1800.0"}})
    a = _rows(_view(data))["P-experimental-01"]["answers"]["A"]
    assert "1700" in _digits(a["text"]) and a["ok"] is True and a["shown_k"] == 2


def test_two_correct_tetrahedral_runs_with_opposite_signs_do_not_cancel():
    ref = TASKS["P-tetrahedral-01"]["reference"]["Dq"]
    data = _with_runs("P-tetrahedral-01", "C", [True, True], {1: {"dq": str(ref)}, 2: {"dq": str(-ref)}})
    a = _rows(_view(data))["P-tetrahedral-01"]["answers"]["C"]
    assert "Dq0" not in _digits(a["text"]) and f"Dq{round(ref)}" in _digits(a["text"])
    assert a["ok"] is True and a["shown_k"] == 1


def test_the_run_anchor_names_the_first_run_on_the_side_of_the_verdict():
    data = _with_runs("P-closed_form-01", "A", [False, True, True])
    a = _rows(_view(data))["P-closed_form-01"]["answers"]["A"]
    assert a["ok"] is True and a["shown_k"] == 2
    assert a["run_anchor"] == taskview.run_anchor("m1", "A", "medium", "P-closed_form-01", 2)
    assert a["run_anchor"].endswith("-k2")
    data = _with_runs("P-closed_form-01", "A", [True, False, False])  # not solved: the first wrong run
    a = _rows(_view(data))["P-closed_form-01"]["answers"]["A"]
    assert a["ok"] is False and a["run_anchor"].endswith("-k2")


@pytest.mark.parametrize(("source", "want"), [
    ("Garcia Rojas & Perez Torres, J. Chem. Educ. 2023, 100, 251, doi:10.1021/acs.jchemed.2c00885, Tables 1-2",
     ("Garcia Rojas & Perez Torres, J. Chem. Educ. 2023, 100, 251", "10.1021/acs.jchemed.2c00885", "Tables 1-2")),
    ("Yang et al., Al2(WO4)3:Cr3+, arXiv:2403.15148 (no DOI), Table 2",
     ("Yang et al., Al2(WO4)3:Cr3+, arXiv:2403.15148", None, "Table 2")),
    ("[Co(en)3]3+ ROA study, Chirality 2026, doi:10.1002/chir.70128, UV-vis section",
     ("[Co(en)3]3+ ROA study, Chirality 2026", "10.1002/chir.70128", "UV-vis section")),
    ("Somebody, Journal 2020, doi:10.1000/x.1", ("Somebody, Journal 2020", "10.1000/x.1", None)),
    ("Somebody, Journal 2020", ("Somebody, Journal 2020", None, None)),
])
def test_source_parts_cut_the_table_source_into_text_doi_and_locator(source, want):
    got = literature.source_parts({"source": source})
    assert (got["text"], got["doi"], got["locator"]) == want


def test_source_parts_of_no_row_are_empty():
    assert literature.source_parts(None) == {"text": "", "doi": None, "locator": None}


def test_the_location_column_stands_in_for_a_source_without_a_locator():
    got = literature.source_parts({"source": "Somebody, Journal 2020, doi:10.1000/x.1", "location": "Table 5"})
    assert got["locator"] == "Table 5"


def test_a_class_with_tasks_that_differ_in_what_they_require_says_how_many_need_the_parameter():
    lit = [t for t in TASKS.values() if t["class"] == "literature_new"]
    needs_c = [t for t in lit if "C" in t["required"]]
    assert 0 < len(needs_c) < len(lit)
    text = taskview.class_tolerance(lit)
    assert f"C {100 * needs_c[0]['tolerance']['C']:g} % ({len(needs_c)} of {len(lit)} tasks)" in text
    assert "(" not in taskview.class_tolerance([t for t in TASKS.values() if t["class"] == "racah_c"])


def test_the_blocks_carry_the_oracle_and_the_tolerance_of_the_class(view):
    by = {b["class"]: b for b in view}
    assert by["closed_form"]["oracle"] == "closed form (Underhill–Billing)"
    assert by["closed_form"]["tolerance"] == "Dq 2 %, B 5 %"
    assert by["literature_all"]["oracle"] == "least-squares fit, forward model"
    assert by["out_of_scope"]["tolerance"] == "must decline"
    assert "ground terms" in by["pairing"]["tolerance"]


def test_a_task_without_runs_has_a_row_without_answers():
    data = _data()
    gone = "P-closed_form-02"
    for r in data["rows"]:  # every run of the task ended in HTTP 429: it has rows, none evaluable
        if r["task_id"] == gone:
            r["_na"] = "na429"
    row = _rows(_view(data))[gone]
    assert row["answers"] == {} and row["id"] == gone
    block = next(b for b in _view(data) if b["class"] == "closed_form")
    assert block["n"] == 2 and block["n_by"] == {"A": 1, "B": 1, "C": 1} and block["k"]["A"] == 1


def test_a_task_the_model_never_ran_keeps_its_row_but_is_not_counted():
    data = _data()
    gone = "P-closed_form-02"
    data["rows"] = [r for r in data["rows"] if r["task_id"] != gone]
    view = _view(data)
    assert _rows(view)[gone]["answers"] == {}
    block = next(b for b in view if b["class"] == "closed_form")
    assert block["n"] == 1 and block["n_by"] == {"A": 1, "B": 1, "C": 1} and len(block["tasks"]) == 2


def test_the_report_category_label_is_that_of_the_most_frequent_category_of_the_runs():
    data = _data()
    t = TASKS["P-closed_form-02"]
    data["rows"] += [_row("m1", "B", t, False, k=2), _row("m1", "B", t, False, k=3)]
    a = _rows(_view(data))[t["id"]]["answers"]["B"]
    assert (a["n_runs"], a["n_correct"], a["category"]) == (3, 0, "gross error")


def test_the_category_of_a_task_that_is_not_solved_names_its_wrong_runs():
    data = _data()
    t = TASKS["P-experimental-01"]  # A solves it with k1; a second, wrong run makes it 1 of 2
    data["rows"].append(_row("m1", "A", t, False, k=2))
    a = _rows(_view(data))[t["id"]]["answers"]["A"]
    assert (a["ok"], a["n_runs"], a["n_correct"]) == (False, 2, 1)
    assert a["category"] == "gross error"


def test_a_grouped_number_does_not_break_across_lines():
    assert taskview._grouped(13760) == "13 760" and taskview._plain(3488.0) == "3 488"


def test_the_item_count_of_a_batch_answer_is_that_of_the_run_shown():
    """k = 2: the cell shows the 26 or the 27 correct items of one run, never their mean 26.5 rounded up."""
    task = {"answer_schema": "batch", "reference": {"values": list(range(54))}}
    assert taskview._answer_text(task, {"n_correct_items": 26}) == "26 of 54 within"
    assert taskview._answer_text(task, {"n_correct_items": 27}) == "27 of 54 within"
    assert taskview._answer_text(task, {"n_correct_items": 28}) == "28 of 54 within"


def test_curve_and_pairing_answers_round_a_half_up():
    curve = {"answer_schema": "curve"}
    assert taskview._answer_text(curve, {"curve_max_rel_err": 0.1225}) == "max rel. error 12.3 %"
    assert taskview._answer_text(curve, {"curve_max_rel_err": 0.0225}) == "max rel. error 2.3 %"
    pairing = {"answer_schema": "pairing"}
    assert taskview._answer_text(pairing, {"edge_f1": 0.125, "ground_correct": True}) == "edge F1 0.13 · ground ✓"
    assert taskview._answer_text(pairing, {"edge_f1": 0.375, "ground_correct": False}) == "edge F1 0.38 · ground ✗"
