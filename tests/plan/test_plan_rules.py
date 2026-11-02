"""Tests for the rules of tsbench.plan: the spec checks of build_plan, the header facts, the argv template, the
answer and condition helpers, and the line checks of validate_lines. Output goes to memory only; no model call."""
from __future__ import annotations

import datetime as dt

import pytest

from tsbench import conditions
from tsbench import plan as P
from tsbench.tasks import load

HAIKU, OPUS = "claude-haiku-5-5", "claude-opus-5-5"
FIXED = "2026-10-24T00:00:00+00:00"


def spec(**kw):
    base = {"split": "pilot", "models": [HAIKU], "conditions": ["A"], "efforts": ["medium"], "k": 1,
            "budget_usd": 1.0, "limit": 1}
    base.update(kw)
    return base


def build(**kw):
    s = spec(**kw)
    return P.build_plan(load("pilot")[: s["limit"]], s, pins=P.live_pins(None), created_utc=FIXED)


# ------------------------------------------------------------------ the spec checks
@pytest.mark.parametrize("bad", [
    {"models": [HAIKU, HAIKU]},              # duplicate model
    {"models": []},                          # no model
    {"conditions": ["A", "A"]},              # duplicate condition
    {"conditions": []},                      # no condition
    {"k": 0},                                # no repetition
    {"budget_usd": 0.0},                     # no budget
    {"budget_usd": -1.0},
    {"k": 0, "budget_usd": 2.0},             # k alone is enough to refuse
])
def test_build_refuses_a_bad_spec(bad):
    with pytest.raises(P.PlanError):
        build(**bad)


def test_build_refuses_a_bad_k_from_and_an_unknown_effort():
    with pytest.raises(P.PlanError):
        build(k=2, k_from=3)
    with pytest.raises(P.PlanError):
        build(efforts=["nope"])


def test_build_defaults_fill_the_spec():
    plan = build()
    assert plan.header["spec"]["gateway"] is False
    assert plan.header["spec"]["system_prompt_file"] == "prompts/neutral.txt"
    assert plan.header["per_call_cap"] is None
    assert plan.header["budget_usd_total"] == 1.0


def test_build_takes_its_time_and_commit_and_hash_from_the_arguments(monkeypatch):
    monkeypatch.setattr(P, "_git_commit", lambda: "from-git")
    plan = P.build_plan(load("pilot")[:1], spec(), pins=P.live_pins(None))
    assert plan.header["generator_git_commit"] == "from-git"
    assert plan.header["tasks_sha256"] == P.tasks_subset_sha256("pilot")
    assert plan.header["created_utc"].endswith("+00:00")
    assert dt.datetime.fromisoformat(plan.header["created_utc"]).tzinfo is not None
    given = P.build_plan(load("pilot")[:1], spec(), pins=P.live_pins(None), created_utc=FIXED,
                         git_commit="given", tasks_sha256="ff" * 32)
    assert given.header["generator_git_commit"] == "given"
    assert given.header["tasks_sha256"] == "ff" * 32 and given.header["created_utc"] == FIXED


def test_header_counts_say_what_the_runs_contain():
    plan = P.build_plan(load("pilot")[:2], spec(models=[HAIKU, OPUS], conditions=["A", "B"], efforts=["medium"], k=2,
                                                 limit=2),
                        pins=P.live_pins(None), created_utc=FIXED)
    counts = plan.header["counts"]
    assert counts["by_condition"] == {"A": 8, "B": 8}
    assert counts["by_model"] == {HAIKU: 8, OPUS: 8}
    assert counts["by_effort"] == {"medium": 16}
    assert sum(counts["by_class"].values()) == 16


def test_build_self_check_reports_the_first_five_problems(monkeypatch):
    monkeypatch.setattr(P, "validate_lines", lambda lines, **kw: ["p1", "p2", "p3", "p4", "p5", "p6", "p7"])
    with pytest.raises(P.PlanError) as err:
        build()
    assert str(err.value) == "built plan fails its own schema: p1; p2; p3; p4; p5"


def test_a_clean_build_passes_its_own_check(monkeypatch):
    seen = []

    def spy(lines, **kw):
        seen.append(len(lines))
        return []

    monkeypatch.setattr(P, "validate_lines", spy)
    build()
    assert seen == [2]


# ------------------------------------------------------------------ the helpers
def test_tasks_subset_hash_is_the_line_of_the_split():
    pilot, confirmatory = P.tasks_subset_sha256("pilot"), P.tasks_subset_sha256("confirmatory")
    assert pilot is not None and pilot.startswith("77ca71ea")
    assert confirmatory is not None and confirmatory.startswith("6aa12d6a")
    assert P.tasks_subset_sha256("nope") is None


def test_task_answer_schema_defaults_to_fit_for_v1_records():
    assert P.task_answer_schema({"answer_schema": "curve"}) == "curve"
    assert P.task_answer_schema({}) == "fit"
    assert P.task_answer_schema({"answer_schema": ""}) == "fit"


def test_answer_format_default_is_the_fit_schema():
    fmt = P.answer_format()
    assert fmt == {"name": P.ANSWER_FORMATS["fit"], "enforced": "json-schema",
                   "schema_sha256": conditions.ANSWER_SCHEMAS["fit"].sha256}


def test_tools_expected_per_condition_is_the_contract():
    assert P.tools_expected("A") == {"tools": [], "mcp_servers": []}
    assert P.tools_expected("B") == {"tools": ["Bash"], "mcp_servers": []}
    assert P.tools_expected("C") == {"mcp_prefix": conditions.MCP_TOOL_PREFIX,
                                     "mcp_servers": [conditions.MCP_SERVER_NAME]}
    with pytest.raises(P.PlanError):
        P.tools_expected("Z")


def test_argv_template_carries_turns_schema_and_disallowed_tools():
    argv = P.argv_template("B", HAIKU, "medium", 7, "curve", ("Bash",))
    assert argv[argv.index("--max-turns") + 1] == "7"
    assert argv[argv.index("--disallowedTools") + 1] == "Bash"
    assert argv[argv.index("--system-prompt-file") + 1] == "{SYSTEM_PROMPT_FILE}"
    assert argv[argv.index("--settings") + 1] == "{SETTINGS}"
    assert argv[-2:] == ["--json-schema", conditions.ANSWER_SCHEMAS["curve"].compact]
    c = P.argv_template("C", HAIKU, "medium", 7)
    assert c[c.index("--mcp-config") + 1] == "{MCP_CONFIG}"
    assert c[c.index("--json-schema") + 1] == conditions.ANSWER_SCHEMAS["fit"].compact
    assert "--disallowedTools" not in c


def test_system_prompt_for_fit_is_the_spec_file_and_others_take_the_sibling():
    assert P.system_prompt_for("prompts/neutral.txt", "fit") == "prompts/neutral.txt"
    assert P.system_prompt_for("prompts/neutral.txt", "curve") == "prompts/neutral_curve.txt"
    with pytest.raises(P.PlanError, match="not found"):
        P.system_prompt_for("prompts/neutral.txt", "no_such_schema")


def test_the_plan_text_is_the_loaded_text(tmp_path):
    plan = build()
    path = tmp_path / "plan.jsonl"
    P.write_plan(plan, path, markdown=False)
    loaded = P.load_plan(path)
    assert loaded.text() == path.read_text(encoding="utf-8")
    assert loaded.raw == loaded.text()


def test_load_plan_refuses_a_missing_file(tmp_path):
    with pytest.raises(P.PlanError, match="cannot read"):
        P.load_plan(tmp_path / "missing.jsonl")


# ------------------------------------------------------------------ the line checks
def _lines(plan):
    return [P.canonical(plan.header)] + [P.canonical(r) for r in plan.runs]


def test_validate_lines_numbers_from_line_one_and_keeps_going_after_bad_json():
    plan = build()
    lines = _lines(plan)
    bad = [lines[0], "not json", "also not json", lines[1]]
    errs = P.validate_lines(bad)
    assert errs[0].startswith("line 2: not JSON") and errs[1].startswith("line 3: not JSON")
    assert len([e for e in errs if e.startswith("line ")]) == 2


def test_validate_lines_requires_runs_by_default():
    plan = build()
    header_only = [P.canonical(plan.header)]
    assert "plan has no run records" in P.validate_lines(header_only)
    assert "plan has no run records" not in P.validate_lines(header_only, require_runs=False)


@pytest.mark.parametrize("header_split, run_split", [("pilot", "confirmatory"), ("confirmatory", "pilot")])
def test_validate_lines_ties_the_run_split_to_the_header_split(header_split, run_split):
    """The header spec.split is not covered by plan_id; a run record's split must agree with it, or editing the header
    would switch the confirmatory guard of the runner on or off."""
    plan = build()
    runs = [{**r, "split": run_split} for r in plan.runs]
    header = {**plan.header, "plan_id": P.plan_id_of(runs), "spec": {**plan.header["spec"], "split": header_split}}
    errs = P.validate_lines([P.canonical(header)] + [P.canonical(r) for r in runs])
    assert errs and f"split {run_split!r}" in errs[0] and f"spec.split is {header_split!r}" in errs[0]
    ok = {**header, "spec": {**header["spec"], "split": run_split}}
    assert P.validate_lines([P.canonical(ok)] + [P.canonical(r) for r in runs]) == []


def test_validate_lines_says_what_a_bad_first_line_must_be():
    plan = build()
    assert P.validate_lines([P.canonical(plan.runs[0])]) == ["line 1 must be the header record"]
    assert P.validate_lines([]) == ["line 1 must be the header record"]


def test_validate_lines_flags_a_second_header_and_a_duplicate_run():
    plan = build()
    lines = _lines(plan)
    assert "duplicate run_id" in P.validate_lines([lines[0], lines[1], lines[1]])



def test_validate_lines_flags_a_prompt_or_system_prompt_that_was_edited():
    plan = build()
    r = dict(plan.runs[0], prompt="changed")
    errs = P.validate_lines([P.canonical(plan.header), P.canonical(r)])
    assert f"{r['run_id']}: prompt_sha256 does not match the prompt" in errs
    s = dict(plan.runs[0], system_prompt_text="changed")
    errs = P.validate_lines([P.canonical(plan.header), P.canonical(s)])
    assert f"{s['run_id']}: system_prompt_sha256 does not match the system prompt text" in errs


def test_validate_lines_checks_a_sealed_header_carries_no_runs():
    plan = build()
    sealed = dict(plan.header, sealed=True)
    assert P.validate_lines([P.canonical(sealed)], require_runs=True) == []
    errs = P.validate_lines([P.canonical(sealed), P.canonical(plan.runs[0])])
    assert "a sealed plan must not carry run records" in errs


def test_validate_lines_reports_a_wrong_run_id():
    plan = build()
    r = dict(plan.runs[0], run_id="wrong")
    errs = P.validate_lines([P.canonical(plan.header), P.canonical(r)])
    assert any(e == f"wrong: run_id should be {HAIKU}/A/medium/{r['task_id']}-k1" for e in errs)


# ------------------------------------------------------------------ the refusals of build and validate
def test_build_names_the_spec_key_it_lacks():
    with pytest.raises(P.PlanError, match="spec lacks 'budget_usd'"):
        P.build_plan(load("pilot")[:1], {"split": "pilot", "models": [HAIKU], "conditions": ["A"],
                                         "efforts": ["medium"], "k": 1})


def test_build_refuses_no_tasks_and_an_unknown_system_prompt():
    with pytest.raises(P.PlanError, match="no tasks"):
        P.build_plan([], spec())
    with pytest.raises(P.PlanError, match="system prompt file .* not found"):
        build(system_prompt_file="prompts/no_such_prompt.txt")


def test_build_refuses_two_tasks_with_one_id():
    task = load("pilot")[0]
    with pytest.raises(P.PlanError, match="duplicate run_id"):
        P.build_plan([task, dict(task)], spec(limit=2), pins=P.live_pins(None), created_utc=FIXED)


def test_validate_lines_skips_blank_lines_and_flags_a_second_header():
    plan = build()
    sealed = dict(plan.header, sealed=True)
    assert P.validate_lines([P.canonical(plan.header), "", "   ", *_lines(plan)[1:]]) == []
    errs = P.validate_lines([P.canonical(sealed), P.canonical(sealed)])
    assert "only the first line may be a header" in errs


def test_cli_build_refuses_an_empty_selection_and_a_bad_limit(tmp_path, capsys):
    from tsbench.plan import __main__ as plan_cli
    base = ["build", "--split", "pilot", "--models", HAIKU, "--conditions", "A", "--effort", "medium", "--k", "1",
            "--budget-usd", "10", "--out", str(tmp_path / "plan.jsonl")]
    assert plan_cli.main(base + ["--task-class", "no_such_class"]) == 2
    assert "selection is empty" in capsys.readouterr().err
    assert plan_cli.main(base + ["--limit", "0"]) == 2
    assert "--limit must be >= 1" in capsys.readouterr().err


def test_cli_validate_reports_an_unreadable_file(tmp_path, capsys):
    from tsbench.plan import __main__ as plan_cli
    assert plan_cli.main(["validate", str(tmp_path / "missing.jsonl")]) == 2
    assert "cannot read" in capsys.readouterr().err


# ------------------------------------------------------------------ exact messages and outputs
@pytest.mark.parametrize(("bad", "message"), [
    ({"models": [HAIKU, HAIKU]}, "models must be non-empty and without duplicates"),
    ({"models": []}, "models must be non-empty and without duplicates"),
    ({"models": ["haiku"]}, "'haiku' is an alias; give the full model id (e.g. claude-haiku-5-5)"),
    ({"conditions": ["A", "A"]}, "conditions must be non-empty and without duplicates"),
    ({"conditions": []}, "conditions must be non-empty and without duplicates"),
    ({"efforts": ["huge"]}, "effort 'huge' not in "),
    ({"k": 0}, "k must be >= 1 and budget_usd > 0"),
    ({"k": 2, "k_from": 3}, "k_from must be an integer in 1..k, got 3"),
])
def test_build_names_the_reason(bad, message):
    with pytest.raises(P.PlanError) as e:
        build(**bad)
    assert str(e.value).startswith(message), str(e.value)


def test_no_tasks_and_duplicate_task_ids_are_refused():
    with pytest.raises(P.PlanError, match="^no tasks$"):
        P.build_plan([], spec(), pins=P.live_pins(None), created_utc=FIXED)
    task = load("pilot")[0]
    with pytest.raises(P.PlanError, match=r"^duplicate run_id \(duplicate task ids\?\)$"):
        P.build_plan([task, task], spec(), pins=P.live_pins(None), created_utc=FIXED)


def test_gateway_model_ids_need_the_gateway_flag():
    assert build(models=["qwen3.8-27b"], gateway=True).runs[0]["model"] == "qwen3.8-27b"
    with pytest.raises(P.PlanError, match="is not a full model id"):
        build(models=["qwen3.8-27b"])


def test_a_text_only_gateway_model_has_the_image_tools_blocked_in_c():
    plan = build(models=["qwen3.8-27b"], gateway=True, conditions=["A", "C"])
    by_cond = {r["condition"]: r for r in plan.runs}
    blocked = list(conditions.IMAGE_TOOLS)
    assert by_cond["C"]["disallowed_tools"] == blocked and by_cond["A"]["disallowed_tools"] == []
    for r in plan.runs:
        assert r["argv_template"] == P.argv_template(r["condition"], r["model"], r["effort"], r["max_turns"],
                                                     r["answer_schema"], r["disallowed_tools"])
    assert build(models=[HAIKU], conditions=["C"]).runs[0]["disallowed_tools"] == []


def test_run_records_carry_the_hash_of_their_task_and_their_turn_cap():
    task = load("pilot")[0]
    (run,) = build().runs
    assert run["task_sha256"] == P.sha256_text(P.canonical(task))
    assert run["max_turns"] == conditions.max_turns("A")
    assert str(run["max_turns"]) in run["argv_template"]


def test_argv_template_has_no_per_call_budget():
    argv = P.argv_template("A", HAIKU, "medium", 3)
    assert "--max-budget-usd" not in argv and argv[0] == "{CLAUDE}"


def test_unknown_condition_in_tools_expected():
    with pytest.raises(P.PlanError, match=r"^unknown condition 'Z'$"):
        P.tools_expected("Z")


def test_canonical_sorts_keys_and_keeps_non_ascii():
    assert P.canonical({"b": 1, "a": "é"}) == '{"a": "é", "b": 1}'


def test_plan_text_is_the_raw_text_when_loaded():
    plan = build()
    assert P.Plan(plan.header, plan.runs, raw="RAW").text() == "RAW"
    assert P.Plan(plan.header, plan.runs).text() == P.serialize(plan.header, plan.runs)


def test_tasks_subset_sha256_splits_at_the_first_double_blank(tmp_path, monkeypatch):
    import tsbench.tasks
    path = tmp_path / "tasks.sha256"
    path.write_text("aaa  pilot\nbbb  odd  name\n", encoding="utf-8")
    monkeypatch.setattr(tsbench.tasks, "HASH_PATH", path)
    assert P.tasks_subset_sha256("pilot") == "aaa"
    assert P.tasks_subset_sha256("odd  name") == "bbb"
    assert P.tasks_subset_sha256("name") is None


@pytest.mark.parametrize(("n", "suffix"), [(6, ""), (7, " ...")])
def test_load_plan_lists_six_errors_and_marks_more(tmp_path, monkeypatch, n, suffix):
    path = tmp_path / "plan.jsonl"
    path.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(P, "validate_lines", lambda lines: [f"e{i}" for i in range(1, n + 1)])
    with pytest.raises(P.PlanError) as e:
        P.load_plan(path)
    assert str(e.value) == f"{path} is not a valid plan: e1; e2; e3; e4; e5; e6{suffix}"


def test_write_plan_creates_missing_folders_through_a_tmp_file(tmp_path, monkeypatch):
    import pathlib
    moved = []
    real = pathlib.Path.replace
    monkeypatch.setattr(pathlib.Path, "replace", lambda self, target: moved.append(self.name) or real(self, target))
    path = tmp_path / "a" / "b" / "plan.jsonl"
    P.write_plan(build(), path)
    # a temp name of its own per write (process id and a random part), then the rename
    assert [n.split(".")[0] + "." + n.split(".")[1] for n in moved] == ["plan.jsonl", "plan.sha256", "plan.md"]
    assert all(n.endswith(".tmp") and n not in ("plan.jsonl.tmp", "plan.sha256.tmp", "plan.md.tmp") for n in moved)
    assert sorted(p.name for p in path.parent.iterdir()) == ["plan.jsonl", "plan.md", "plan.sha256"]


def test_render_markdown_exact():
    header = {"plan_id": "0123456789abcdef0123", "n_runs": 3, "budget_usd_total": 1.5, "tasks_sha256": "abc",
              "spec": {"split": "pilot", "models": ["m1", "m2"], "conditions": ["A", "B"],
                       "efforts": ["low", "medium"], "k": 2},
              "pins": {"claude_cli_version": "9", "other": "x", "tanabesugano": "1.2", "python": "3.14"},
              "counts": {"by_condition": {"A": 2, "B": 1}}}
    runs = [{"system_prompt_sha256": "s" * 64, "system_prompt_text": "\n  sys one  \n\n", "task_id": "T1",
             "task_class": "c1", "prompt": "\n p1 \n"},
            {"system_prompt_sha256": "s" * 64, "system_prompt_text": "other", "task_id": "T1", "task_class": "c1",
             "prompt": "second copy"},
            {"system_prompt_sha256": "t" * 64, "system_prompt_text": "sys two", "task_id": "T2", "task_class": "c2",
             "prompt": "p2"}]
    expected = "\n".join([
        "# Run plan `0123456789abcdef`", "",
        "- split: pilot, runs: 3, budget: USD 1.5",
        "- models: m1, m2",
        "- conditions: A, B; efforts: low, medium; k = 2",
        "- tasks sha256 (pilot): `abc`",
        "- pins: claude_cli_version=9, tanabesugano=1.2, python=3.14",
        "", "## Runs per cell", "", "| condition | runs |", "|---|---|", "| A | 2 |", "| B | 1 |",
        "", "## System prompts", "",
        "`ssssssssssss`", "", "```text", "\n  sys one  ", "```", "",
        "`tttttttttttt`", "", "```text", "sys two", "```", "",
        "## Prompts (each once)", "",
        "### T1 (c1)", "", "```text", "\n p1 ", "```", "",
        "### T2 (c2)", "", "```text", "p2", "```", ""])
    assert P.render_markdown(P.Plan(header, runs)) == expected
