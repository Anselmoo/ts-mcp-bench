"""Method and traceability of the full report (src/tsbench/report/method.py): identity, protocol, statistics, class
intervals, provenance, exclusions and limits as tables, every value read from a file. The run set is the small one of
tests/report/test_facts.py with a manifest and a scores table that carry values found nowhere else, so that a value
typed into the code cannot pass. The facts are those of two models, m1 and m2, as `facts.benchmarks` gives them."""
from __future__ import annotations

import csv
import hashlib
import json
import pathlib
import re
from types import SimpleNamespace

import pytest
from test_facts import SOLVES, SOLVES_2, TASKS, _data, _run_set  # the helpers of the facts tests

from tsbench.core import intervals, resource
from tsbench.report import facts, method
from tsbench.score.run_sets import run_sets_in

KEYS = {"identity", "protocol", "statistics", "class_intervals", "provenance", "exclusions", "limits"}
VERSION = "4-under-test"


def _sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _pilot_hash() -> str:
    for line in resource("tasks/tasks.sha256").read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if parts[-1:] == ["pilot"]:
            return parts[0]
    raise AssertionError("no pilot line in tasks.sha256")


SCORES = [
    {"model": "m1", "condition": "A", "effort": "medium", "task_id": "P-closed_form-01", "k_index": "1",
     "evaluable": "True", "not_evaluable_reason": "", "correct": "True"},
    {"model": "m1", "condition": "B", "effort": "medium", "task_id": "P-closed_form-02", "k_index": "1",
     "evaluable": "False", "not_evaluable_reason": "rate_limited", "correct": "False"},
    {"model": "m1", "condition": "C", "effort": "medium", "task_id": "P-closed_form-01", "k_index": "1",
     "evaluable": "True", "not_evaluable_reason": "", "correct": "True"},
    {"model": "m2", "condition": "A", "effort": "medium", "task_id": "P-closed_form-01", "k_index": "1",
     "evaluable": "False", "not_evaluable_reason": "rate_limited", "correct": "False"},
    {"model": "m2", "condition": "C", "effort": "medium", "task_id": "P-closed_form-01", "k_index": "1",
     "evaluable": "False", "not_evaluable_reason": "timeout", "correct": "False"},
    {"model": "m2", "condition": "C", "effort": "medium", "task_id": "P-closed_form-02", "k_index": "1",
     "evaluable": "False", "not_evaluable_reason": "timeout", "correct": "False"},
]


PLAN_SHA = "a1" * 32  # the prompt hash the plan pins for neutral.txt; no package file has it
CURVE_SHA = "c2" * 32
RUNS = [("A", "neutral.txt", PLAN_SHA, 15)] * 2 + [("B", "neutral.txt", PLAN_SHA, 40)] * 2 + [
    ("C", "neutral.txt", PLAN_SHA, 25), ("C", "neutral_curve.txt", CURVE_SHA, 25)]


def _plan(d: pathlib.Path, runs=RUNS, **header) -> str:
    """Write the plan of a run set (header and run records as `tsbench.plan` writes them) and return its sha256."""
    lines = [{"kind": "header", "plan_id": "pid", "per_call_cap": 0.75, **header}]
    lines += [{"kind": "run", "run_id": f"r{i}", "condition": c, "system_prompt_file": f"prompts/{f}",
               "system_prompt_sha256": sha, "max_turns": turns} for i, (c, f, sha, turns) in enumerate(runs)]
    data = "".join(json.dumps(x) + "\n" for x in lines).encode("utf-8")
    sha = hashlib.sha256(data).hexdigest()
    for name in ("plan.jsonl", "inputs/plan.jsonl"):
        (d / name).write_bytes(data)
    (d / "plan.sha256").write_text(f"{sha}  plan.jsonl\n", encoding="utf-8")
    hashes = json.loads((d / "inputs" / "hashes.json").read_text(encoding="utf-8"))
    (d / "inputs" / "hashes.json").write_text(json.dumps({**hashes, "plan_file_sha256": sha}), encoding="utf-8")
    return sha


def _set(root: pathlib.Path, **manifest) -> pathlib.Path:
    d = _run_set(root)
    m = json.loads((d / "MANIFEST.json").read_text(encoding="utf-8"))
    m.update({"tasks_sha256": _pilot_hash(), "git_commit": "feedc0ffee1234567890", "git_dirty": "no",
              "models_requested": ["m1"], "reported_models": {"m1": {"A": ["m1-build-0417"]}}, "k": 1,
              "budget_usd": 7.25, "sandbox_settings_sha256": "5a" * 32,
              "claude_version": {"real": "9.9.9 (Claude Code)"}, "plan_sha256": _plan(d),
              # the args of an argparse namespace: the runner has no --max-turns
              "args": {"gateway": False, "k": 1, "per_call_usd": 0.75}})
    m.update(manifest)
    (d / "MANIFEST.json").write_text(json.dumps(m), encoding="utf-8")
    with (d / "scores.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(SCORES[0]))
        w.writeheader()
        w.writerows(SCORES)
    return d


def _benches() -> dict[str, dict]:
    """The benches of m1 (solves `SOLVES`) and m2 (solves `SOLVES_2`), as many evaluable runs each: m1 first."""
    data = _data(("m1",))
    data["rows"] += _data(("m2",), SOLVES_2)["rows"]
    benches = facts._benchmarks(data, {})
    benches["m1"]["tools"] = ["ts_fit_spectrum", "ts_terms_table_data", "StructuredOutput"]
    benches["m2"]["tools"] = ["ts_fit_spectrum", "ts_energy_levels", "StructuredOutput"]
    return benches


def _facts(d: pathlib.Path, benches: dict[str, dict] | None = None) -> dict:
    sets = run_sets_in([d])
    return method.facts(sets, benches or _benches(), None, facts.platform(sets), version=VERSION)


@pytest.fixture()
def run_set(tmp_path) -> pathlib.Path:
    return _set(tmp_path)


def _text(x) -> str:
    return json.dumps(x, ensure_ascii=False)


def test_the_method_has_its_seven_tables(run_set):
    m = _facts(run_set)
    assert set(m) == KEYS


def test_identity_reads_the_version_the_task_set_hash_and_the_manifest(run_set):
    d, m = run_set, _facts(run_set)
    rows = m["identity"]
    assert rows and all({"item", "value", "source"} <= set(r) for r in rows)
    text = _text(rows)
    assert VERSION in text and _pilot_hash() in text
    assert "feedc0f" in text and "pid" in text
    assert _sha(d / "inputs" / "plan.jsonl") in text  # the manifest's plan_sha256
    assert d.name in text  # the run-set folder
    assert re.search(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}", text) and "UTC" in text  # the build time
    assert "differs" not in text


def test_identity_marks_a_manifest_task_hash_that_differs_from_the_task_file(tmp_path):
    d = _set(tmp_path, tasks_sha256="0" * 64)
    rows = _facts(d)["identity"]
    assert any("differs" in str(r["value"]) for r in rows)


def test_protocol_names_the_tools_prompts_and_run_settings(run_set):
    m = _facts(run_set)
    p = m["protocol"]
    conds = {r["cond"]: r for r in p["conditions"]}
    assert list(conds) == ["A", "B", "C"]
    assert conds["A"]["tools"] == "none"
    assert "Bash" in conds["B"]["tools"]
    assert "ts_fit_spectrum" in conds["C"]["tools"] and "ts_terms_table_data" in conds["C"]["tools"]
    assert conds["C"]["tools"].count("ts_fit_spectrum") == 1 and "ts_energy_levels" in conds["C"]["tools"]
    settings = _text(p["settings"])
    for value in ("m1", "m1-build-0417", "medium", "7.25", "0.75", "5a" * 6):
        assert value in settings, value


def _stated(d: pathlib.Path) -> dict[str, list[dict]]:
    """Every row of the settings, the limits and the platform table that states the endpoint, effort or client."""
    sets = run_sets_in([d])
    plat = facts.platform(sets)
    m = method.facts(sets, _benches(), None, plat, version=VERSION)
    rows = [*m["protocol"]["settings"], *m["limits"], *plat["rows"]]
    out: dict[str, list[dict]] = {}
    for r in rows:
        if r["item"] in ("Endpoint", "Model endpoint", "Effort", "Claude Code client"):
            out.setdefault(r["item"].split()[-1].lower(), []).append(r)
    return out


def test_the_endpoint_the_effort_and_the_client_are_stated_in_one_table_each(run_set):
    got = _stated(run_set)
    assert {k: [r["item"] for r in v] for k, v in got.items()} == {
        "endpoint": ["Model endpoint"], "effort": ["Effort"], "client": ["Claude Code client"]}
    assert got["effort"][0]["value"] == "medium" and got["client"][0]["value"] == "9.9.9"
    assert got["endpoint"][0]["value"] == "Anthropic API"


def test_a_missing_effort_reads_not_recorded_without_a_source(tmp_path):
    got = _stated(_set(tmp_path, effort=None))
    assert len(got["effort"]) == 1
    assert got["effort"][0]["value"] == "not recorded" and got["effort"][0]["source"] == "–"


def test_the_conditions_name_the_prompt_files_and_hashes_the_plan_pins(run_set):
    rows = _facts(run_set)["protocol"]["conditions"]
    got = [(r["cond"], r["prompt"], r["sha256"], r["runs"]) for r in rows]
    assert got == [("A", "neutral.txt", PLAN_SHA, 2), ("B", "neutral.txt", PLAN_SHA, 2),
                   ("C", "neutral.txt", PLAN_SHA, 1), ("C", "neutral_curve.txt", CURVE_SHA, 1)]
    assert all(r["tools"] for r in rows)
    assert _sha(resource("prompts/neutral.txt")) not in _text(rows)  # not the hash of today's package file


def test_the_conditions_fall_back_to_the_package_prompt_without_a_plan(run_set):
    for name in ("plan.jsonl", "inputs/plan.jsonl"):
        (run_set / name).unlink()
    rows = _facts(run_set)["protocol"]["conditions"]
    assert [r["cond"] for r in rows] == ["A", "B", "C"]
    assert {(r["prompt"], r["sha256"], r["runs"]) for r in rows} == {
        ("neutral.txt", _sha(resource("prompts/neutral.txt")), None)}


def test_a_condition_the_plan_does_not_run_gets_no_package_prompt(tmp_path):
    d = _set(tmp_path)
    _plan(d, runs=[("A", "neutral.txt", PLAN_SHA, 15)] * 2)
    rows = {r["cond"]: r for r in _facts(d)["protocol"]["conditions"]}
    assert (rows["A"]["prompt"], rows["A"]["sha256"], rows["A"]["runs"]) == ("neutral.txt", PLAN_SHA, 2)
    for cond in ("B", "C"):
        assert rows[cond]["runs"] == 0 and rows[cond]["sha256"] is None, cond
        assert "package" not in rows[cond]["source"]
    assert _sha(resource("prompts/neutral.txt")) not in _text(list(rows.values()))


def test_the_per_call_cap_of_the_arguments_beats_the_null_of_the_plan_header(tmp_path):
    d = _set(tmp_path, args={"gateway": False, "k": 1, "per_call_usd": 0.5})
    _plan(d, per_call_cap=None)  # the plan builder always writes null here
    settings = {r["item"]: r for r in _facts(d)["protocol"]["settings"]}
    assert settings["Per-call cap (USD)"]["value"] == "0.5"


def test_the_b_stack_row_names_the_versions_the_run_recorded(tmp_path):
    stack = {"digest": "bs" * 32, "packages": {"numpy": "9.9.1", "scipy": "8.8.2"}}
    rows = _facts(_set(tmp_path, b_stack=stack))["protocol"]["conditions"]
    b = next(r for r in rows if r["cond"] == "B")["tools"]
    assert "numpy 9.9.1" in b and "scipy 8.8.2" in b and "sympy" in b  # sympy: not recorded, so the pin of the file


def test_the_maximum_turns_come_from_the_plan_per_condition(run_set):
    settings = {r["item"]: r for r in _facts(run_set)["protocol"]["settings"]}
    assert settings["Maximum turns"]["value"] == "A 15, B 40, C 25"
    assert "plan.jsonl" in settings["Maximum turns"]["source"]


def test_the_maximum_turns_fall_back_to_the_sidecars_without_a_plan(run_set):
    for name in ("plan.jsonl", "inputs/plan.jsonl"):
        (run_set / name).unlink()
    for meta in run_set.glob("*/*/*/*.meta.json"):
        data = json.loads(meta.read_text(encoding="utf-8"))
        meta.write_text(json.dumps({**data, "max_turns": {"A": 15, "B": 40, "C": 25}[data["condition"]]}),
                        encoding="utf-8")
    settings = {r["item"]: r for r in _facts(run_set)["protocol"]["settings"]}
    assert settings["Maximum turns"]["value"] == "A 15, B 40, C 25"
    assert "meta.json" in settings["Maximum turns"]["source"]


def test_an_unset_per_call_cap_says_none(tmp_path):
    d = _set(tmp_path, args={"gateway": False, "k": 1, "per_call_usd": None})
    _plan(d, per_call_cap=None)
    settings = {r["item"]: r for r in _facts(d)["protocol"]["settings"]}
    assert settings["Per-call cap (USD)"]["value"] == "none"
    assert settings["Per-call cap (USD)"]["source"] != "–"


def test_a_run_set_without_plan_or_args_says_not_recorded_for_cap_and_turns(tmp_path):
    d = _set(tmp_path, args={})
    for name in ("plan.jsonl", "inputs/plan.jsonl"):
        (d / name).unlink()
    for meta in d.glob("*/*/*/*.meta.json"):
        meta.unlink()
    settings = {r["item"]: r["value"] for r in _facts(d)["protocol"]["settings"]}
    assert settings["Per-call cap (USD)"] == settings["Maximum turns"] == "not recorded"


def test_statistics_name_the_methods_and_read_their_parameters(run_set):
    m = _facts(run_set)
    rows = m["statistics"]
    assert rows and all({"quantity", "definition", "parameters"} <= set(r) for r in rows)
    text = _text(rows)
    assert str(intervals.RESAMPLES) in text and str(intervals.SEED) in text
    assert "bootstrap" in text and "McNemar" in text


def test_class_intervals_give_k_of_n_and_the_task_bootstrap_interval_per_model(run_set):
    m = _facts(run_set)
    rows = m["class_intervals"]
    classes = list(dict.fromkeys(t["class"] for t in TASKS.values()))
    assert [(r["model"], r["class"]) for r in rows] == [(x, c) for x in ("m1", "m2") for c in classes]
    for model, solves in (("m1", SOLVES), ("m2", SOLVES_2)):
        cf = next(r for r in rows if r["class"] == "closed_form" and r["model"] == model)
        assert cf["n"] == 2  # a class of two tasks says so
        for cond in "ABC":
            solved = [int("closed_form" in solves[cond])] * 2
            cell = cf["cells"][cond]
            assert (cell["k"], cell["n"]) == (sum(solved), 2)
            assert (cell["lo"], cell["hi"]) == intervals.cluster_bootstrap(solved, [1, 1])
    num = {r["model"]: r["cells"]["B"]["k"] for r in rows if r["class"] == "numerical"}
    assert num == {"m1": 3, "m2": 3}
    exp = {r["model"]: r["cells"]["B"]["k"] for r in rows if r["class"] == "experimental"}
    assert exp == {"m1": 2, "m2": 0}


def test_provenance_has_a_row_with_files_fields_and_hashes_for_every_source(run_set):
    d, m = run_set, _facts(run_set)
    rows = {r["key"]: r for r in m["provenance"]}
    assert set(rows) == set(method.SOURCES) and rows
    for key, r in rows.items():
        assert r["files"] and r["fields"], key
    hashed = {f["path"]: f.get("sha256") for r in rows.values() for f in r["files"]}
    for name in ("MANIFEST.json", "scores.csv"):
        hits = [sha for path, sha in hashed.items() if path.endswith(name)]
        assert hits and all(sha == _sha(d / name) for sha in hits), name


def test_exclusions_count_the_runs_left_out_by_model_and_reason(run_set, tmp_path):
    m = _facts(run_set)
    assert all({"model", "reason", "count", "source"} <= set(r) for r in m["exclusions"])
    by = {(r["model"], r["reason"]): r["count"] for r in m["exclusions"]}
    assert by == {("m1", "rate_limited"): 1, ("m2", "rate_limited"): 1, ("m2", "timeout"): 2}
    assert [r["model"] for r in m["exclusions"]] == ["m1", "m2", "m2"]  # in the order of the benches
    benches = _benches()
    benches["m2"]["notes"] = [{"kind": "transcript", "text": "runs without a transcript", "count": 4}]
    rows = _facts(_set(tmp_path / "again"), benches)["exclusions"]
    hit = [r for r in rows if "transcript" in r["reason"]]
    assert [(r["model"], r["count"]) for r in hit] == [("m2", 4)]


def test_limits_state_the_scope_of_the_run(run_set):
    m = _facts(run_set)
    rows = m["limits"]
    small = sum(1 for c in set(t["class"] for t in TASKS.values())
                if sum(t["class"] == c for t in TASKS.values()) < 5)
    assert small == 11
    hit = next(r for r in rows if "fewer than 5" in r["item"])
    assert str(hit["value"]) == str(small)
    text = _text(rows)
    assert "pilot" in text and "50" in text and "14" in text
    by = {r["item"]: r["value"] for r in rows}
    assert by["Models"] == "2: m1, m2"
    assert (by["Tasks"], by["Classes"], by["Runs scored"], by["Runs evaluable"]) == ("50", "14", "300", "300")


def test_provenance_counts_the_transcripts_and_checks_them_against_the_manifest(run_set):
    rows = {r["key"]: r for r in _facts(run_set)["provenance"]}
    files = next(f for r in rows.values() for f in r["files"] if f["path"].endswith("/*/*/*.jsonl"))
    assert files["count"] == 3 and files["verified"] == "3 of 3 recorded hashes match"
    assert re.fullmatch(r"[0-9a-f]{64}", files["sha256"])  # the digest of the listing of the files and their hashes
    (run_set / "m" / "A" / "medium" / "P-closed_form-01-k1.jsonl").write_bytes(b"changed\n")
    again = {r["key"]: r for r in _facts(run_set)["provenance"]}
    changed = next(f for r in again.values() for f in r["files"] if f["path"].endswith("/*/*/*.jsonl"))
    assert changed["verified"] == "2 of 3 recorded hashes match" and changed["sha256"] != files["sha256"]


def _resume(d: pathlib.Path, *stops: dict) -> None:
    """Earlier sessions of a run set: one `MANIFEST.prev-*.json` per stop."""
    now = json.loads((d / "MANIFEST.json").read_text(encoding="utf-8"))
    (d / "MANIFEST.json").write_text(json.dumps({**now, "finished": True, "stop": None, "stopped_by_budget": False,
                                                 "counts": {"planned": 5, "done": 2, "skipped": 3}}), encoding="utf-8")
    for i, stop in enumerate(stops):
        side = {**now, "finished": True, "stop": None, "stopped_by_budget": False,
                "counts": {"planned": 5, "done": 3, "not_run_budget": 2}, **stop}
        (d / f"MANIFEST.prev-2026110{i}T000000000000Z.json").write_text(json.dumps(side), encoding="utf-8")


def test_a_budget_stop_that_a_resume_made_good_counts_no_run_as_not_started(run_set):
    _resume(run_set, {"stopped_by_budget": True})
    m = _facts(run_set)
    by = {r["item"]: r["value"] for r in m["limits"]}
    assert by["Run state"] == "finished" and "Runs not started" not in by
    assert not [r for r in m["exclusions"] if "not started" in r["reason"]]
    assert by["Stops and resumes"] == "1 stop, 1 resume: the budget 1"


def test_the_stops_count_each_reason_of_the_earlier_sessions(run_set):
    quota = {"reason": "quota_exhausted", "scope": "daily", "after_runs": 1}
    _resume(run_set, {"stop": quota}, {"stop": quota}, {"stopped_by_budget": True}, {"interrupted": True}, {})
    row = next(r for r in _facts(run_set)["limits"] if r["item"] == "Stops and resumes")
    assert row["value"] == "4 stops, 5 resumes: quota exhausted, daily cap 2; the budget 1; interrupted 1"
    assert row["source"] == "MANIFEST.prev-*.json (stop, stopped_by_budget, interrupted)"


def test_a_run_set_of_one_session_has_no_row_of_stops(run_set):
    assert "Stops and resumes" not in {r["item"] for r in _facts(run_set)["limits"]}


def _transcript_row(rows: list[dict]) -> dict:
    return next(f for r in rows for f in r["files"] if f["path"].endswith("/*/*/*.jsonl"))


def _redacted(run_set: pathlib.Path) -> tuple[pathlib.Path, str, str]:
    """Replace a path in one transcript of the run set as a published copy does. (log file, old sha, new sha)."""
    t = run_set / "m" / "A" / "medium" / "P-closed_form-01-k1.jsonl"
    old = _sha(t)
    t.write_bytes(t.read_bytes() + b'{"cwd": "<HOME>"}\n')
    return t, old, _sha(t)


def _log(path: pathlib.Path, *rows: tuple[str, str]) -> pathlib.Path:
    lines = ["file,sha256_original,sha256_published,n_b_venv,n_home,n_session_folder"]
    lines += [f"confirmatory/plan/m/A/medium/x-k{i}.jsonl,{a},{b},0,1,0" for i, (a, b) in enumerate(rows)]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _with_log(d: pathlib.Path, log: pathlib.Path) -> list[dict]:
    sets = run_sets_in([d])
    return method.facts(sets, _benches(), None, facts.platform(sets), version=VERSION,
                        redactions=method.read_redactions(log))["provenance"]


def test_a_documented_path_replacement_counts_as_a_match_and_is_stated(run_set, tmp_path):
    _, old, new = _redacted(run_set)
    assert _transcript_row(_facts(run_set)["provenance"])["verified"] == "2 of 3 recorded hashes match"
    row = _transcript_row(_with_log(run_set, _log(tmp_path / "REDACTIONS.csv", (old, new))))
    assert row["verified"] == "3 of 3 recorded hashes match, 1 through the path replacement of REDACTIONS.csv"


def test_a_replacement_needs_both_hashes(run_set, tmp_path):
    _, old, new = _redacted(run_set)
    log = _log(tmp_path / "REDACTIONS.csv", ("0" * 64, new), (old, "1" * 64))
    assert _transcript_row(_with_log(run_set, log))["verified"] == "2 of 3 recorded hashes match"


def test_a_log_without_a_hit_changes_nothing_on_the_page(run_set, tmp_path):
    row = _transcript_row(_with_log(run_set, _log(tmp_path / "REDACTIONS.csv", ("0" * 64, "1" * 64))))
    assert row["verified"] == "3 of 3 recorded hashes match"


def test_a_redaction_log_without_its_columns_is_refused(tmp_path):
    path = tmp_path / "log.csv"
    path.write_text("file,sha256\na,b\n", encoding="utf-8")
    with pytest.raises(ValueError, match="sha256_original"):
        method.read_redactions(path)


def test_provenance_reads_the_package_files_with_their_own_hashes(run_set):
    rows = {r["key"]: r for r in _facts(run_set)["provenance"]}
    paths = {f["path"]: f["sha256"] for r in rows.values() for f in r["files"]}
    tasks = next(p for p in paths if p.endswith("tasks.jsonl"))
    assert paths[tasks] == _sha(resource("tasks/tasks.jsonl"))
    assert any(p.endswith("literature/*.csv") for p in paths)


def test_provenance_marks_a_source_file_that_is_missing(run_set):
    (run_set / "inputs" / "hashes.json").unlink()
    rows = _facts(run_set)["provenance"]
    gone = [f for r in rows for f in r["files"] if f["path"].endswith("hashes.json")]
    assert gone and all(f["sha256"] is None and f["verified"] == "not found" for f in gone)


def test_exclusions_count_every_model_and_have_no_row_for_other_models(tmp_path):
    d = _set(tmp_path)
    with (d / "scores.csv").open("a", encoding="utf-8", newline="") as fh:
        fh.write("other,A,medium,P-closed_form-01,1,False,no_answer,False\n")
    rows = _facts(d)["exclusions"]
    by = {(r["model"], r["reason"]): r["count"] for r in rows}
    assert by[("m1", "rate_limited")] == 1 and by[("other", "no_answer")] == 1
    assert not any("other models" in r["reason"] for r in rows)


def test_a_note_of_the_run_set_is_counted_once_for_all_models(run_set):
    benches = _benches()
    note = {"kind": "run set", "text": "rs: category failed for 2 runs (ValueError)", "count": 1}
    for b in benches.values():
        b["notes"] = [note]
    rows = [r for r in _facts(run_set, benches)["exclusions"] if r["reason"] == note["text"]]
    assert [(r["model"], r["count"]) for r in rows] == [("all models", 1)]


def test_a_run_set_without_a_manifest_says_not_recorded(tmp_path):
    d = _set(tmp_path)
    (d / "MANIFEST.json").unlink()
    m = _facts(d)
    ident = {r["item"]: r for r in m["identity"]}
    assert ident["Code commit"]["value"] == "not recorded" and ident["Code commit"]["source"] == "–"
    settings = {r["item"]: r["value"] for r in m["protocol"]["settings"]}
    assert settings["Sandbox settings sha256"] == "not recorded"
    assert m["limits"]


def test_several_run_sets_get_one_identity_row_each(tmp_path):
    a, b = _set(tmp_path / "a"), _set(tmp_path / "b")
    sets = run_sets_in([a, b])
    m = method.facts(sets, _benches(), None, facts.platform(sets), version=VERSION)
    text = _text(m["identity"])
    assert all(s.name in text for s in sets) and len({s.name for s in sets}) == 2
    assert sum(r["item"].startswith("Code commit") for r in m["identity"]) == 2


def test_the_statistics_read_the_paired_bootstrap_from_the_analysis_defaults(run_set):
    import inspect

    from tsbench.stats import analysis

    defaults = inspect.signature(analysis.bootstrap_ci).parameters
    paired = next(r for r in _facts(run_set)["statistics"] if "paired" in r["quantity"].lower())
    assert str(defaults["n_boot"].default) in paired["parameters"]
    assert f"seed {defaults['seed'].default}" in paired["parameters"]


def test_a_class_cell_leaves_out_the_tasks_without_a_mark(run_set):
    benches = _benches()
    cf = next(c for c in benches["m1"]["classes"] if c["class"] == "closed_form")
    cf["marks"]["A"] = [True, None]
    rows = _facts(run_set, benches)["class_intervals"]
    cell = next(r for r in rows if r["model"] == "m1" and r["class"] == "closed_form")["cells"]["A"]
    assert (cell["k"], cell["n"]) == (1, 1)
    assert (cell["lo"], cell["hi"]) == intervals.cluster_bootstrap([1], [1])


def test_an_empty_class_cell_has_no_interval(run_set):
    benches = _benches()
    benches["m1"]["classes"][0]["marks"]["A"] = []
    cell = next(r for r in _facts(run_set, benches)["class_intervals"])["cells"]["A"]
    assert (cell["k"], cell["n"], cell["lo"], cell["hi"]) == (0, 0, None, None)


def test_provenance_hashes_the_files_the_caller_names(run_set):
    sets = run_sets_in([run_set])
    inputs = {"coverage.json": [{"path": "coverage/coverage.json", "sha256": "a" * 64}],
              "mutation": [{"path": "mutation/report/report.json", "sha256": "b" * 64}]}
    m = method.facts(sets, _benches(), {"inputs": inputs}, facts.platform(sets), version=VERSION)
    rows = {r["key"]: r for r in m["provenance"]}
    assert rows["packages"]["files"] == [{"path": "coverage/coverage.json", "sha256": "a" * 64, "verified": None}]
    assert rows["scatter"]["files"][1] == {"path": "mutation/report/report.json", "sha256": "b" * 64, "verified": None}
    assert rows["bundle"]["files"][0]["sha256"] is None  # a tree stays named only


# ---------------------------------------------------------------- exclusions: the evaluable column


def test_a_missing_empty_or_loosely_spelled_evaluable_cell_is_not_an_exclusion(tmp_path):
    d = _set(tmp_path)
    head = "model,condition,effort,task_id,k_index,evaluable,not_evaluable_reason,correct\n"
    (d / "scores.csv").write_text(head + "m1,A,medium,P-closed_form-01,1,,,True\n"
                                  "m1,B,medium,P-closed_form-01,1,TRUE,,True\n"
                                  "m1,C,medium,P-closed_form-01,1,False,,False\n", encoding="utf-8")
    by = {(r["model"], r["reason"]): r["count"] for r in _facts(d)["exclusions"]}
    assert by == {("m1", "no reason recorded"): 1}


def test_a_scores_table_without_an_evaluable_column_excludes_nothing(tmp_path):
    d = _set(tmp_path)
    (d / "scores.csv").write_text("model,condition,effort,task_id,k_index,correct\n"
                                  "m1,A,medium,P-closed_form-01,1,True\n", encoding="utf-8")
    assert _facts(d)["exclusions"] == []


# ---------------------------------------------------------------- an unfinished run set


STOPPED = {"finished": False, "interrupted": False, "stopped_by_budget": False,
           "stop": {"reason": "quota_exhausted", "scope": "daily", "after_runs": 5, "run_id": "r9"},
           "counts": {"planned": 30, "done": 20, "rate_limited": 2, "skipped": 0, "aborted": 1, "not_run_sandbox": 0,
                      "not_run_probe_not_evaluable": 0, "not_run_budget": 3, "not_run_quota": 4},
           "aborted_cells": [{"model": "m1", "condition": "C", "effort": "medium", "first_run": "r3",
                              "reasons": ["tools differ from the plan"]}]}


def test_the_limits_say_that_a_run_set_stopped_and_why(tmp_path):
    by = {r["item"]: r for r in _facts(_set(tmp_path, **STOPPED))["limits"]}
    state = by["Run state"]["value"]
    assert "not finished" in state and "quota" in state and "daily" in state and "5 runs" in state
    assert by["Runs not started"]["value"].startswith("7") and "quota 4" in by["Runs not started"]["value"]
    assert "budget 3" in by["Runs not started"]["value"]
    assert by["Rate-limited runs"]["value"] == "2"
    assert "m1" in by["Aborted cells"]["value"] and "C" in by["Aborted cells"]["value"]
    assert all(by[k]["source"].startswith("MANIFEST.json") for k in
               ("Run state", "Runs not started", "Rate-limited runs", "Aborted cells"))


def test_the_exclusions_list_the_runs_never_started_and_the_aborted_cells(tmp_path):
    rows = _facts(_set(tmp_path, **STOPPED))["exclusions"]
    started = {r["reason"]: r["count"] for r in rows if r["model"] == "all models"}
    assert sorted(started.values()) == [3, 4]
    assert any("quota" in k for k in started) and any("budget" in k for k in started)
    cell = [r for r in rows if r["model"] == "m1" and "aborted" in r["reason"]]
    assert len(cell) == 1 and "C" in cell[0]["reason"] and "tools differ from the plan" in cell[0]["reason"]


def test_the_limits_count_the_cells_below_the_planned_k_and_the_rescued_answers(tmp_path):
    benches = _benches()
    by = {r["item"]: r["value"] for r in _facts(_set(tmp_path / "first"), benches)["limits"]}
    assert by["Cells below the planned k"] == "0 of 300 (k = 1)" and by["Rescued answers"] == "0"
    benches["m1"]["completeness"] = {"k": 3, "cells": 150, "short": 40, "missing": 75, "rescued": 2}
    benches["m2"]["completeness"] = {"k": 3, "cells": 150, "short": 0, "missing": 0, "rescued": 1}
    rows = {r["item"]: r for r in _facts(_set(tmp_path / "again"), benches)["limits"]}
    assert rows["Cells below the planned k"]["value"] == "40 of 300 (k = 3)"
    assert rows["Runs missing for the planned k"]["value"] == "75"
    assert rows["Rescued answers"]["value"] == "3" and "rescued" in rows["Rescued answers"]["source"]


def test_a_finished_run_set_has_a_run_state_and_no_stop_rows(tmp_path):
    d = _set(tmp_path, finished=True, interrupted=False, stop=None,
             counts={"planned": 3, "done": 3, "rate_limited": 0, "aborted": 0, "not_run_quota": 0},
             aborted_cells=[])
    by = {r["item"]: r["value"] for r in _facts(d)["limits"]}
    assert by["Run state"] == "finished"
    assert not {"Runs not started", "Rate-limited runs", "Aborted cells"} & set(by)


def test_an_interrupted_run_set_says_so(tmp_path):
    by = {r["item"]: r["value"] for r in _facts(_set(tmp_path, finished=False, interrupted=True))["limits"]}
    assert "interrupted" in by["Run state"]


def test_a_budget_stop_is_named_in_the_run_state(tmp_path):
    by = {r["item"]: r["value"] for r in _facts(_set(tmp_path, finished=False, stopped_by_budget=True))["limits"]}
    assert "budget" in by["Run state"]


# ---------------------------------------------------------------- provenance: what the figures read


class _Spy(dict):
    """A row that records the keys read from it."""

    def __init__(self, data, seen):
        super().__init__(data)
        self.seen = seen

    def get(self, key, default=None):
        self.seen.add(key)
        return super().get(key, default)

    def __getitem__(self, key):
        self.seen.add(key)
        return super().__getitem__(key)


def _read_columns(seen: set[str]) -> set[str]:
    return {k for k in seen if not k.startswith("_")}


def test_the_transcript_glob_leaves_out_the_attempt_files(run_set):
    folder = run_set / "m" / "A" / "medium"
    (folder / "P-closed_form-01-k1.attempt1.jsonl").write_bytes(b'{"type": "system"}\n')
    rows = {r["key"]: r for r in _facts(run_set)["provenance"]}
    files = next(f for r in rows.values() for f in r["files"] if f["path"].endswith("/*/*/*.jsonl"))
    assert files["count"] == 3 and files["verified"] == "3 of 3 recorded hashes match"


def test_the_ledger_sources_name_every_column_a_cell_reads():
    from tsbench.report import facts as facts_mod

    seen: set[str] = set()
    full = {"correct": "False", "_category": "x", "curve_max_rel_err": "0.1", "item_accuracy": "0.5", "edge_f1": "0.5",
            "node_precision": "0.5", "node_recall": "0.5", "rel_err_dq": "0.1", "rel_err_b": "0.1", "rel_err_c": "0.1"}
    for schema in ("fit", "curve", "diagram", "batch", "pairing"):
        task = {"answer_schema": schema, "required": ["Dq", "B", "C"], "tolerance": {"Dq": 0.1, "B": 0.1, "C": 0.1,
                                                                                     "curve_rel": 0.1}}
        facts_mod._run_cell(_Spy({**full, "_task": task}, seen), task)
    assert _read_columns(seen) <= set(method.SOURCES["ledger"]["fields"]), _read_columns(seen) - set(
        method.SOURCES["ledger"]["fields"])


def test_the_outcome_sources_name_every_column_the_failure_category_reads():
    from tsbench.score import taxonomy

    seen: set[str] = set()
    base = {"correct": "False", "rescued": "False", "has_result": "True", "result_subtype": "success",
            "is_error": "False", "unparseable": "False", "curve_max_rel_err": "0.1", "median_rel_error": "0.1",
            "item_accuracy": "0.5", "answer_out_of_scope": "False", "rel_err_dq": "0.1", "rel_err_b": "0.1",
            "rel_err_c": "0.1"}
    for task in ({"answer_schema": s, "required": ["Dq", "B", "C"], "tolerance": {"Dq": 0.1, "B": 0.1, "C": 0.1}}
                 for s in ("fit", "curve", "batch", "diagram")):
        taxonomy.failure_category(_Spy(base, seen), task)
    assert _read_columns(seen) <= set(method.SOURCES["outcome"]["fields"]), _read_columns(seen) - set(
        method.SOURCES["outcome"]["fields"])


def test_the_literature_sources_name_the_answered_values_and_the_table_columns(monkeypatch):
    from tsbench.report import facts as facts_mod
    from tsbench.report import literature, science

    tasks = {t["id"]: t for t in map(json.loads, resource("tasks/tasks.jsonl").read_text(encoding="utf-8")
                                     .splitlines()) if t["class"] in science.LITERATURE and t.get("split") == "pilot"}
    tid = next(iter(tasks))
    seen: set[str] = set()
    table = {k: _Spy(v, seen) for k, v in literature.read_csv_rows().items()}
    monkeypatch.setattr(literature, "read_csv_rows", lambda path=None: table)
    row = {"correct": "True", "dq": "1000", "b": "800", "c": "3000", "rel_err_dq": "0.1"}
    by_task = {(c, tid): [_Spy(row, seen)] for c in "ABC"}
    runs = SimpleNamespace(tasks=tasks)
    facts_mod._literature(runs, [tid], by_task)  # ty: ignore[invalid-argument-type]
    fields = set(method.SOURCES["literature"]["fields"])
    assert _read_columns(seen) <= fields, _read_columns(seen) - fields
    assert not {"rel_err_dq", "rel_err_b", "rel_err_c"} & fields  # the figure takes the answers, not their errors


def test_package_sources_are_resolved_through_the_resource_function(monkeypatch):
    seen = []
    real = method.resource

    def spy(resource_id):
        seen.append(resource_id)
        return real(resource_id)

    monkeypatch.setattr(method, "resource", spy)
    [entry] = method._resolve("pkg:tasks/tasks.jsonl", [], {})
    assert seen == ["tasks/tasks.jsonl"]
    assert entry["path"] == "tsbench/data/tasks/tasks.jsonl" and entry["sha256"] == _sha(resource("tasks/tasks.jsonl"))


def test_an_unknown_package_source_is_marked_not_found():
    [entry] = method._resolve("pkg:tasks/no_such_file.jsonl", [], {})
    assert entry == {"path": "tsbench/data/tasks/no_such_file.jsonl", "sha256": None, "verified": "not found"}


def test_a_stop_on_api_errors_is_named_and_its_unstarted_runs_are_listed(tmp_path):
    d = _set(tmp_path, finished=True, interrupted=False, stopped_by_budget=False,
             stop={"reason": "api_errors", "scope": None, "after_runs": 3, "run_id": "r3"},
             counts={"planned": 10, "done": 3, "rate_limited": 0, "aborted": 0, "not_run_api_errors": 7},
             aborted_cells=[])
    facts = _facts(d)
    by = {r["item"]: r["value"] for r in facts["limits"]}
    assert "api errors" in by["Run state"] and "3 runs" in by["Run state"]
    assert by["Runs not started"].startswith("7") and "api errors 7" in by["Runs not started"]
    started = {r["reason"]: r["count"] for r in facts["exclusions"] if r["model"] == "all models"}
    assert started == {"not started: API errors stopped the run set": 7}
