"""Tests for the run plan: build, hash, schema, the flags form against the plan, --plan round trip, sealing.

No network, no key, no real `claude`; execution is the fake (dry run). Output goes to tmp_path only.
"""
from __future__ import annotations

import copy
import hashlib
import json
import pathlib
import random
import re
import tempfile

import pytest

from tsbench import plan as P
from tsbench.plan import __main__ as plan_cli
from tsbench.run import runner
from tsbench.tasks import load

HAIKU, OPUS = "claude-haiku-5-5", "claude-opus-5-5"
FIXED_TIME = "2026-10-24T00:00:00+00:00"


@pytest.fixture(autouse=True)
def clean_env(monkeypatch, tmp_path_factory):
    fake_venv = tmp_path_factory.getbasetemp() / "fake-venv-B-plan"
    fake_venv.mkdir(exist_ok=True)
    monkeypatch.setenv("TSBENCH_B_VENV", str(fake_venv))  # never the real venv-B
    monkeypatch.setattr(P, "claude_version_probe", lambda: None)


def spec(**kw):
    base = {"split": "pilot", "models": [HAIKU, OPUS], "conditions": ["A", "B", "C"], "efforts": ["medium"],
            "k": 1, "budget_usd": 1.0, "limit": 2}
    base.update(kw)
    return base


def build(**kw):
    s = spec(**kw)
    return P.build_plan(load("pilot")[: s["limit"]], s, created_utc=FIXED_TIME)


def dry_args(out, *extra, limit=2, conds="A,B,C", k=1):
    return ["--split", "pilot", "--models", HAIKU, "--conditions", conds, "--effort", "medium", "--k", str(k),
            "--budget-usd", "10", "--out", str(out), "--dry-run", "--limit", str(limit), *extra]


def manifest(out):
    return json.loads((pathlib.Path(out) / "MANIFEST.json").read_text(encoding="utf-8"))


# ------------------------------------------------------------------ determinism and hash
def test_build_is_deterministic_and_complete():
    a, b = build(), build()
    assert a.text() == b.text()
    assert a.header["n_runs"] == len(a.runs) == 2 * 2 * 3
    assert a.runs[0]["run_id"] == runner.run_id_of(HAIKU, "A", "medium", load("pilot")[0]["id"], 1)
    for r in a.runs:
        assert r["prompt_sha256"] == hashlib.sha256(r["prompt"].encode()).hexdigest()
        assert r["system_prompt_text"].startswith("You answer questions")
        assert "{SETTINGS}" in r["argv_template"] or r["condition"] != "B"
        assert r["argv_template"][0] == "{CLAUDE}" and "--max-budget-usd" not in r["argv_template"]
        assert r["max_turns"] == {"A": 15, "B": 40, "C": 25}[r["condition"]]
        assert r["argv_template"][r["argv_template"].index("--max-turns") + 1] == str(r["max_turns"])
        assert r["disallowed_tools"] == []
    assert a.header["per_call_cap"] is None


def test_plan_id_ignores_time_order_and_pins_but_not_content():
    a = build()
    other = P.build_plan(load("pilot")[:2], spec(), created_utc="2030-01-01T00:00:00+00:00",
                         pins={**a.header["pins"], "python": "9.9"})
    assert other.plan_id == a.plan_id and other.text() != a.text()
    shuffled = list(a.runs)
    random.Random(1).shuffle(shuffled)
    assert P.plan_id_of(shuffled) == a.plan_id
    edited = copy.deepcopy(a.runs)
    edited[0]["prompt"] += " "
    assert P.plan_id_of(edited) != a.plan_id
    assert P.plan_id_of(a.runs) == hashlib.sha256(
        "".join(P.canonical(r) + "\n" for r in sorted(a.runs, key=lambda r: r["run_id"])).encode()).hexdigest()


def test_write_plan_writes_hash_and_markdown(tmp_path):
    plan = build()
    digest = P.write_plan(plan, tmp_path / "plan.jsonl")
    assert digest == hashlib.sha256((tmp_path / "plan.jsonl").read_bytes()).hexdigest()
    assert (tmp_path / "plan.sha256").read_text(encoding="utf-8") == f"{digest}  plan.jsonl\n"
    md = (tmp_path / "plan.md").read_text(encoding="utf-8")
    first_prompt = load("pilot")[0]["prompt"].rstrip("\n")
    assert md.count(first_prompt) == 1  # each prompt once, not once per run
    loaded = P.load_plan(tmp_path / "plan.jsonl")
    assert loaded.plan_id == plan.plan_id and loaded.sha256 == digest


# ------------------------------------------------------------------ schema
def lines_of(plan):
    return [P.canonical(plan.header)] + [P.canonical(r) for r in plan.runs]


def test_valid_plan_validates():
    assert P.validate_lines(lines_of(build())) == []


def mutate_run(plan, fn):
    lines = lines_of(plan)
    rec = json.loads(lines[1])
    fn(rec)
    lines[1] = json.dumps(rec)
    return lines


@pytest.mark.parametrize("name,fn,needle", [
    ("extra field", lambda r: r.update(typo=1), "unexpected field 'typo'"),
    ("missing field", lambda r: r.pop("prompt"), "missing required field 'prompt'"),
    ("bad effort", lambda r: r.update(effort="extreme"), "not in"),
    ("bad condition", lambda r: r.update(condition="D"), "not in"),
    ("k as string", lambda r: r.update(k="1"), "expected integer"),
    ("k as bool", lambda r: r.update(k=True), "expected integer"),
    ("short hash", lambda r: r.update(prompt_sha256="abc"), "does not match"),
    ("bad kind", lambda r: r.update(kind="row"), "kind must be"),
])
def test_schema_rejects(name, fn, needle):
    errs = P.validate_lines(mutate_run(build(), fn))
    assert errs and any(needle in e for e in errs), errs


def test_cross_record_checks():
    plan = build()
    # prompt edited without refreshing its hash
    assert any("prompt_sha256" in e for e in P.validate_lines(mutate_run(plan, lambda r: r.update(prompt="x"))))
    # run edited consistently, header plan_id not refreshed
    def tweak(r):
        r["prompt"] = "x"
        r["prompt_sha256"] = hashlib.sha256(b"x").hexdigest()
    assert any("plan_id" in e for e in P.validate_lines(mutate_run(plan, tweak)))
    lines = lines_of(plan)
    assert any("duplicate" in e for e in P.validate_lines(lines + [lines[1]]))
    hdr = json.loads(lines[0])
    hdr["n_runs"] += 1
    assert any("n_runs" in e for e in P.validate_lines([json.dumps(hdr)] + lines[1:]))
    assert P.validate_lines(lines[1:])  # first line must be the header
    assert P.validate_lines(["{not json"])
    hdr = json.loads(lines[0])
    hdr["schema_version"] = 5
    assert P.validate_lines([json.dumps(hdr)] + lines[1:])


def test_mini_validator_basics():
    schema = {"type": "object", "required": ["a"], "additionalProperties": False,
              "properties": {"a": {"type": ["integer", "null"], "minimum": 1}, "b": {"enum": ["x"]}}}
    assert P.validate_instance(schema, {"a": 1, "b": "x"}) == []
    assert P.validate_instance(schema, {"a": None}) == []
    assert P.validate_instance(schema, {"a": 0})
    assert P.validate_instance(schema, {"a": 1.5})
    assert P.validate_instance(schema, {"a": 1, "c": 1})
    assert P.validate_instance(schema, [])


def test_committed_schema_is_valid_json_with_version():
    schema = P.load_schema()
    assert schema["$schema"].endswith("2020-12/schema") and "$defs" in schema
    assert P.build_plan  # versioned together with SCHEMA_VERSION
    assert P.SCHEMA_VERSION in schema["$defs"]["header"]["properties"]["schema_version"]["enum"]  # 2 still loads


def test_cli_build_and_validate(tmp_path, capsys):
    out = tmp_path / "p" / "plan.jsonl"
    rc = plan_cli.main(["build", "--split", "pilot", "--models", f"{HAIKU},{OPUS}", "--conditions", "A,C",
                        "--effort", "low,medium", "--k", "2", "--budget-usd", "3", "--limit", "1",
                        "--out-plan", str(out)])
    assert rc == 0 and out.exists()
    plan = P.load_plan(out)
    assert plan.header["n_runs"] == 2 * 2 * 2 * 2 * 1  # k x models x efforts x conditions x tasks
    assert plan_cli.main(["validate", str(out)]) == 0
    assert "OK plan_id=" in capsys.readouterr().out
    out.write_text(out.read_text(encoding="utf-8").replace('"condition": "A"', '"condition": "Z"', 1), encoding="utf-8")
    assert plan_cli.main(["validate", str(out)]) == 1


def test_cli_build_rejects_bad_model(tmp_path):
    rc = plan_cli.main(["build", "--split", "pilot", "--models", "haiku", "--conditions", "A", "--effort", "medium",
                        "--k", "1", "--budget-usd", "1", "--out-plan", str(tmp_path / "plan.jsonl")])
    assert rc == 2 and not (tmp_path / "plan.jsonl").exists()


# ------------------------------------------------------------------ run order
def test_plan_order_is_k_task_model_effort_condition():
    """The documented order: repetition outermost, then task, model, effort, condition. A budget or quota stop then
    leaves a balanced partial matrix, never whole models unrun."""
    tasks = load("pilot")[:2]
    models, efforts, conds = ["claude-haiku-5-5", "claude-sonnet-5-5"], ["low", "high"], ["C", "B"]
    plan = P.build_plan(tasks, spec(models=models, efforts=efforts, conditions=conds, k=2), created_utc=FIXED_TIME)
    want = [(k, t["id"], m, e, c) for k in (1, 2) for t in tasks for m in models for e in efforts for c in conds]
    assert [(r["k"], r["task_id"], r["model"], r["effort"], r["condition"]) for r in plan.runs] == want
    assert len(want) == 32


# ------------------------------------------------------------------ flags form == plan path
def test_the_flags_form_writes_the_plan_and_the_planned_transcripts(tmp_path):
    out = tmp_path / "runs"
    assert runner.main(dry_args(out, k=2)) == 0
    tasks = load("pilot")[:2]
    order = [(k, t["id"], c) for k in (1, 2) for t in tasks for c in ("A", "B", "C")]
    expected = [runner.transcript_path(out, HAIKU, c, "medium", tid, k) for k, tid, c in order]
    assert all(p.exists() for p in expected)
    assert sorted(p.relative_to(out).as_posix() for p in out.glob("*/*/*/*.jsonl")) == sorted(
        p.relative_to(out).as_posix() for p in expected)
    plan = P.load_plan(out / "plan.jsonl")
    assert [r["run_id"] for r in plan.runs] == [runner.run_id_of(HAIKU, c, "medium", tid, k) for k, tid, c in order]
    assert (out / "plan.md").exists() and (out / "plan.sha256").exists()
    m = manifest(out)
    assert m["schema"] == 2 and m["plan_id"] == plan.plan_id and m["plan_sha256"] == plan.sha256
    assert m["pin_drift"] == [] and m["tasks_sha256"] == plan.header["tasks_sha256"]
    assert set(m["transcripts"]) == {r["run_id"] for r in plan.runs}
    meta = json.loads(next(out.glob("*/A/medium/*.meta.json")).read_text(encoding="utf-8"))
    assert meta["plan_id"] == plan.plan_id and "prompt_sha256" in meta
    assert meta["argv"][-4:-2] == ["--tools", ""] and meta["argv"][-2] == "--json-schema"
    prompt = meta["argv"][meta["argv"].index("--system-prompt-file") + 1]
    assert re.fullmatch(r"<OUT>/system-prompts/system-prompt-[0-9a-f]{16}\.txt", prompt)
    assert runner.NEUTRAL_PROMPT not in meta["argv"]


def scrub(node):
    """Drop what the fake draws at random (ids, session, temp cwd); everything else must match."""
    if isinstance(node, dict):
        return {k: scrub(v) for k, v in node.items() if k not in ("session_id", "uuid", "cwd", "id", "tool_use_id")}
    return [scrub(v) for v in node] if isinstance(node, list) else node


def test_plan_round_trip_gives_same_runs_and_bytes(tmp_path):
    first, second = tmp_path / "one", tmp_path / "two"
    assert runner.main(dry_args(first, limit=3, k=2)) == 0
    assert runner.main(["--plan", str(first / "plan.jsonl"), "--out", str(second), "--dry-run"]) == 0
    names = lambda d: sorted(p.relative_to(d).as_posix() for p in d.glob("*/*/*/*.jsonl"))  # noqa: E731
    assert names(first) == names(second) and len(names(first)) == 3 * 2 * 3
    for rel in names(first):
        a = [json.loads(x) for x in (first / rel).read_text(encoding="utf-8").splitlines()]
        b = [json.loads(x) for x in (second / rel).read_text(encoding="utf-8").splitlines()]
        assert scrub(a) == scrub(b), rel
    assert (first / "plan.jsonl").read_bytes() == (second / "plan.jsonl").read_bytes()
    assert manifest(first)["plan_id"] == manifest(second)["plan_id"]
    assert manifest(first)["plan_sha256"] == manifest(second)["plan_sha256"]
    # recorded as a placeholder path, never the absolute temp path
    assert manifest(second)["args"]["plan"] == "<TMP>/" + (first / "plan.jsonl").resolve().relative_to(
        pathlib.Path(tempfile.gettempdir()).resolve()).as_posix()


def test_plan_mode_reads_prompt_from_the_plan_only(tmp_path):
    """Edit a prompt in the plan (and its hashes): the transcript sees the plan's prompt, not tasks.jsonl."""
    plan = build(models=[HAIKU], conditions=["A"], limit=1)
    run = copy.deepcopy(plan.runs[0])
    run["prompt"] = "A prompt that exists only in this plan."
    run["prompt_sha256"] = hashlib.sha256(run["prompt"].encode()).hexdigest()
    edited = P.Plan({**plan.header, "plan_id": P.plan_id_of([run]), "n_runs": 1,
                     "counts": plan.header["counts"]}, [run])
    path = tmp_path / "plan.jsonl"
    P.write_plan(edited, path, markdown=False)
    out = tmp_path / "out"
    assert runner.main(["--plan", str(path), "--out", str(out), "--dry-run"]) == 0
    assert manifest(out)["plan_id"] == edited.plan_id


def test_plan_flag_excludes_selection_flags_and_the_flags_form_needs_them(tmp_path, capsys):
    with pytest.raises(SystemExit) as e:
        runner.main(["--plan", "x.jsonl", "--models", HAIKU, "--out", str(tmp_path)])
    assert e.value.code == 2
    with pytest.raises(SystemExit) as e:
        runner.main(["--split", "pilot", "--out", str(tmp_path)])
    assert e.value.code == 2


def test_resume_with_another_plan_exits_2(tmp_path):
    first = tmp_path / "one"
    assert runner.main(dry_args(first, limit=1)) == 0
    other = tmp_path / "other.jsonl"
    P.write_plan(build(models=[HAIKU], conditions=["A"], limit=2), other, markdown=False)
    with pytest.raises(SystemExit) as e:
        runner.main(["--plan", str(other), "--out", str(first), "--dry-run", "--resume"])
    assert e.value.code == 2
    # the same plan resumes and skips everything that is done
    assert runner.main(["--plan", str(first / "plan.jsonl"), "--out", str(first), "--dry-run", "--resume"]) == 0
    assert manifest(first)["counts"]["skipped"] == 3


def test_a_flags_form_resume_may_extend_the_matrix_and_keeps_the_previous_plan(tmp_path):
    out = tmp_path / "runs"
    assert runner.main(dry_args(out, limit=1, conds="A")) == 0
    old = P.load_plan(out / "plan.jsonl").plan_id
    assert runner.main(dry_args(out, "--resume", limit=1, conds="A", k=2)) == 0
    assert P.load_plan(out / "plan.jsonl").plan_id != old
    assert list(out.glob(f"plan.prev-{old[:16]}.jsonl"))
    assert manifest(out)["counts"]["skipped"] == 1


# ------------------------------------------------------------------ pins
def test_pin_drift_is_recorded_for_pilot_and_aborts_confirmatory(tmp_path, capsys):
    plan = build(models=[HAIKU], conditions=["A"], limit=1)
    drifted = P.Plan({**plan.header, "pins": {**plan.header["pins"], "tanabesugano": "1.0.0"}}, plan.runs)
    path = tmp_path / "plan.jsonl"
    P.write_plan(drifted, path, markdown=False)
    out = tmp_path / "pilot-out"
    assert runner.main(["--plan", str(path), "--out", str(out), "--dry-run"]) == 0
    assert [d["pin"] for d in manifest(out)["pin_drift"]] == ["tanabesugano"]
    assert "pin drift" in capsys.readouterr().err

    # the same drift in a confirmatory plan (pilot tasks relabelled; no confirmatory task is read) aborts
    tasks = [dict(t, split="confirmatory") for t in load("pilot")[:1]]
    conf = P.build_plan(tasks, spec(split="confirmatory", models=[HAIKU], conditions=["A"], limit=1),
                        created_utc=FIXED_TIME, tasks_sha256=None)
    conf = P.Plan({**conf.header, "pins": {**conf.header["pins"], "tanabesugano": "1.0.0"}}, conf.runs)
    cpath = tmp_path / "conf" / "plan.jsonl"
    P.write_plan(conf, cpath, markdown=False)
    cout = tmp_path / "conf-out"
    with pytest.raises(SystemExit) as e:
        runner.main(["--plan", str(cpath), "--out", str(cout), "--dry-run", "--i-have-preregistered", "10.1234/x"])
    assert e.value.code == 2 and not list(cout.glob("*/*/*/*.jsonl"))


def test_edited_system_prompt_file_counts_as_drift():
    plan = build(models=[HAIKU], conditions=["A"], limit=1)
    stale = [{**r, "system_prompt_sha256": "0" * 64} for r in plan.runs]
    assert P.validate_lines([P.canonical(plan.header)] + [P.canonical(r) for r in stale])  # hash vs text mismatch


def test_tools_expected_in_plan_must_match_conditions(tmp_path):
    plan = build(models=[HAIKU], conditions=["B"], limit=1)
    bad = copy.deepcopy(plan.runs)
    bad[0]["tools_expected"] = {"tools": [], "mcp_servers": []}
    path = tmp_path / "plan.jsonl"
    P.write_plan(P.Plan({**plan.header, "plan_id": P.plan_id_of(bad)}, bad), path, markdown=False)
    with pytest.raises(SystemExit) as e:
        runner.main(["--plan", str(path), "--out", str(tmp_path / "o"), "--dry-run"])
    assert e.value.code == 2


# ------------------------------------------------------------------ sealing
def confirmatory_plan():
    tasks = [dict(t, split="confirmatory") for t in load("pilot")[:2]]
    return P.build_plan(tasks, spec(split="confirmatory", models=[HAIKU], conditions=["A"], limit=2),
                        created_utc=FIXED_TIME)


def test_sealed_file_has_hash_and_counts_but_no_prompt(tmp_path):
    plan = confirmatory_plan()
    path = tmp_path / P.SEALED_NAME
    P.write_sealed(plan, path)
    text = path.read_text(encoding="utf-8")
    rec = json.loads(text)
    assert rec["sealed"] is True and rec["plan_id"] == plan.plan_id and rec["n_runs"] == 2
    assert rec["counts"]["by_condition"] == {"A": 2}
    for r in plan.runs:
        assert r["prompt"] not in text and r["task_id"] not in text and r["system_prompt_text"] not in text
    assert "prompt" not in rec and '"kind": "run"' not in text
    assert P.validate_lines(text.splitlines()) == []
    assert P.load_plan(path).runs == []


def test_runner_refuses_a_sealed_plan(tmp_path):
    path = tmp_path / P.SEALED_NAME
    P.write_sealed(confirmatory_plan(), path)
    with pytest.raises(SystemExit) as e:
        runner.main(["--plan", str(path), "--out", str(tmp_path / "o"), "--dry-run",
                     "--i-have-preregistered", "10.1234/x"])
    assert e.value.code == 2 and not (tmp_path / "o").exists()


def test_confirmatory_run_writes_only_a_sealed_header(tmp_path):
    plan = confirmatory_plan()
    path = tmp_path / "clear" / "plan.jsonl"
    P.write_plan(plan, path, markdown=False)
    out = tmp_path / "out"
    assert runner.main(["--plan", str(path), "--out", str(out), "--dry-run",
                        "--i-have-preregistered", "10.1234/x"]) == 0
    assert not (out / "plan.jsonl").exists() and not (out / "plan.md").exists()
    sealed = (out / P.SEALED_NAME).read_text(encoding="utf-8")
    assert all(r["prompt"] not in sealed for r in plan.runs)
    m = manifest(out)
    assert m["plan_sealed"] is True and m["plan_file"] is None and m["plan_id"] == plan.plan_id


def test_confirmatory_plan_needs_the_doi_before_anything_is_read(tmp_path, capsys):
    rc = plan_cli.main(["build", "--split", "confirmatory", "--models", HAIKU, "--conditions", "A",
                        "--effort", "medium", "--k", "1", "--budget-usd", "1", "--out-plan",
                        str(tmp_path / "plan.jsonl")])
    assert rc == 2 and not list(tmp_path.iterdir())
    with pytest.raises(SystemExit):
        runner.main(["--plan", str(tmp_path / "missing.jsonl"), "--out", str(tmp_path / "o")])


def test_confirmatory_build_with_b_needs_the_b_stack(tmp_path, capsys):
    base = ["build", "--split", "confirmatory", "--models", HAIKU, "--conditions", "A,B", "--effort", "medium",
            "--k", "1", "--budget-usd", "1", "--i-have-preregistered", "10.1234/abc",
            "--out-plan", str(tmp_path / "p.jsonl")]
    assert plan_cli.main(base) == 2 and "B stack" in capsys.readouterr().err
    assert not (tmp_path / "plan.sealed.json").exists()


def test_confirmatory_build_is_sealed_by_default_and_unseal_stays_outside_the_repo(tmp_path, capsys, monkeypatch):
    from tsbench.conditions import b_stack
    monkeypatch.setattr(b_stack, "digest_if_present", lambda venv, *a, **k: "cd" * 32)
    base = ["build", "--split", "confirmatory", "--models", HAIKU, "--conditions", "A,B,C", "--effort", "medium",
            "--k", "1", "--budget-usd", "1", "--i-have-preregistered", "10.1234/abc"]
    out = tmp_path / "plan.jsonl"
    assert plan_cli.main(base + ["--out-plan", str(out)]) == 0
    sealed = tmp_path / P.SEALED_NAME
    rec = json.loads(sealed.read_text(encoding="utf-8"))
    assert rec["sealed"] is True and not out.exists()
    assert ('"prompt":' not in sealed.read_text(encoding="utf-8")
        and "system_prompt_text" not in sealed.read_text(encoding="utf-8"))
    printed = capsys.readouterr().out
    assert "plan_id=" in printed and len(printed) < 400  # hash and counts only, never task text
    inside = P.REPO_ROOT / "build" / "never-written" / "plan.jsonl"
    assert plan_cli.main(base + ["--out-plan", str(out), "--unseal-to", str(inside)]) == 2
    assert not inside.exists()
    clear = tmp_path / "elsewhere" / "plan.jsonl"
    assert plan_cli.main(base + ["--out-plan", str(out), "--unseal-to", str(clear)]) == 0
    assert P.load_plan(clear).plan_id == rec["plan_id"]


def test_plan_carries_answer_schema_hash():
    from tsbench import conditions
    plan = build()
    sha = hashlib.sha256(conditions.ANSWER_SCHEMAS["fit"].compact.encode()).hexdigest()
    assert plan.header["pins"]["answer_schema_sha256"] == sha == P.answer_schema_sha256()
    for r in plan.runs:
        assert r["answer_format"]["enforced"] == "json-schema" and r["answer_format"]["schema_sha256"] == sha
        assert r["argv_template"][-2:] == ["--json-schema", conditions.ANSWER_SCHEMAS["fit"].compact]
    assert P.validate_lines(lines_of(plan)) == []
    bad = json.loads(lines_of(plan)[0])
    bad["pins"]["answer_schema_sha256"] = "zz"
    assert P.validate_lines([json.dumps(bad)] + lines_of(plan)[1:])
    assert P.check_pins(plan.header["pins"], {**plan.header["pins"], "answer_schema_sha256": "0" * 64})


def test_cli_build_selects_by_class_and_by_task_id(tmp_path):
    from tsbench.plan import __main__ as cli
    base = ["build", "--split", "pilot", "--models", "claude-haiku-5-5", "--conditions", "A", "--effort", "medium",
            "--k", "2", "--budget-usd", "1"]
    out = tmp_path / "a" / "plan.jsonl"
    assert cli.main(base + ["--task-class", "diagram", "--out-plan", str(out)]) == 0
    runs = [json.loads(ln) for ln in out.read_text(encoding="utf-8").splitlines()[1:]]
    assert sorted({r["task_id"] for r in runs}) == [f"P-diagram-0{i}" for i in range(1, 6)] and len(runs) == 10
    out2 = tmp_path / "b" / "plan.jsonl"
    assert cli.main(base + ["--task-class", "diagram", "--task-ids", "P-diagram-02,P-diagram-04",
                            "--out-plan", str(out2)]) == 0
    assert ({json.loads(ln)["task_id"] for ln in out2.read_text(encoding="utf-8").splitlines()[1:]}
        == {"P-diagram-02", "P-diagram-04"})
    assert cli.main(base + ["--task-ids", "P-nope-01", "--out-plan", str(tmp_path / "c.jsonl")]) == 2


# ------------------------------------------------------------------ the B stack digest
DIGEST = "cd" * 32


def pinned_plan(**kw):
    s = spec(**kw)
    pins = {**P.live_pins(None, b_stack_sha256=DIGEST)}
    return P.build_plan(load("pilot")[: s["limit"]], s, pins=pins, created_utc=FIXED_TIME)


def test_plan_pins_the_b_stack_digest_on_the_header_and_on_b_runs_only():
    plan = pinned_plan()
    assert plan.header["pins"]["b_stack_sha256"] == DIGEST
    assert {r["condition"] for r in plan.runs if r.get("b_stack_sha256") == DIGEST} == {"B"}
    assert all("b_stack_sha256" not in r for r in plan.runs if r["condition"] != "B")
    assert P.validate_lines(plan.text().splitlines()) == []
    # without a digest nothing is added: the run records (and the plan_id) stay as without a B stack
    assert all("b_stack_sha256" not in r for r in build().runs)


def test_validate_rejects_a_b_run_whose_digest_differs_from_the_header_or_is_missing():
    plan = pinned_plan()
    bad = copy.deepcopy(plan.runs)
    b = next(r for r in bad if r["condition"] == "B")
    b["b_stack_sha256"] = "00" * 32
    errs = P.validate_lines([P.canonical(plan.header)] + [P.canonical(r) for r in bad])
    assert any("b_stack_sha256 differs" in e for e in errs)
    bad = copy.deepcopy(plan.runs)
    next(r for r in bad if r["condition"] == "B").pop("b_stack_sha256")
    lines = [P.canonical(plan.header)] + [P.canonical(r) for r in bad]
    assert any("b_stack_sha256" in e for e in P.validate_lines(lines))
    bad = copy.deepcopy(plan.runs)
    next(r for r in bad if r["condition"] == "A")["b_stack_sha256"] = DIGEST
    lines = [P.canonical(plan.header)] + [P.canonical(r) for r in bad]
    assert any("only condition B" in e for e in P.validate_lines(lines))


def test_check_pins_reports_a_changed_b_stack_digest():
    live = P.live_pins(None, b_stack_sha256="ef" * 32)
    drift = P.check_pins(P.live_pins(None, b_stack_sha256=DIGEST), live)
    assert [d["pin"] for d in drift] == ["b_stack_sha256"]
    assert P.check_pins(P.live_pins(None, b_stack_sha256=None), live) == []  # not pinned: not compared


def test_a_changed_stack_is_pin_drift_for_pilot_and_aborts_confirmatory(tmp_path, monkeypatch, capsys):
    from tsbench.conditions import b_stack
    live = {"path": "/x", "bin": "/x/bin", "python": "3.14.7", "packages": {}, "digest": "ef" * 32}
    monkeypatch.setattr(b_stack, "validate", lambda venv, *a, **k: live)
    plan = pinned_plan(models=[HAIKU], limit=1)
    path = tmp_path / "plan.jsonl"
    P.write_plan(plan, path, markdown=False)
    out = tmp_path / "out"
    assert runner.main(["--plan", str(path), "--out", str(out), "--dry-run"]) == 0
    assert [d["pin"] for d in manifest(out)["pin_drift"]] == ["b_stack_sha256"]
    assert "pin drift" in capsys.readouterr().err
    tasks = [dict(t, split="confirmatory") for t in load("pilot")[:1]]
    conf = P.build_plan(tasks, spec(split="confirmatory", models=[HAIKU], limit=1),
                        pins=P.live_pins(None, b_stack_sha256=DIGEST), created_utc=FIXED_TIME, tasks_sha256=None)
    cpath = tmp_path / "conf" / "plan.jsonl"
    P.write_plan(conf, cpath, markdown=False)
    with pytest.raises(SystemExit) as e:
        runner.main(["--plan", str(cpath), "--out", str(tmp_path / "cout"), "--dry-run",
                     "--i-have-preregistered", "10.1234/x"])
    assert e.value.code == 2
    assert "b_stack_sha256" in capsys.readouterr().err


def test_plan_build_cli_pins_the_digest_when_the_stack_is_valid(tmp_path, monkeypatch):
    from tsbench.conditions import b_stack
    monkeypatch.setattr(b_stack, "digest_if_present", lambda venv, *a, **k: DIGEST)
    out = tmp_path / "plan.jsonl"
    assert plan_cli.main(["build", "--split", "pilot", "--models", HAIKU, "--conditions", "A,B", "--effort", "medium",
                          "--k", "1", "--budget-usd", "1", "--limit", "1", "--out-plan", str(out)]) == 0
    header = json.loads(out.read_text(encoding="utf-8").splitlines()[0])
    assert header["pins"]["b_stack_sha256"] == DIGEST and plan_cli.main(["validate", str(out)]) == 0
    out2 = tmp_path / "plan2.jsonl"  # no B requested: no pin
    assert plan_cli.main(["build", "--split", "pilot", "--models", HAIKU, "--conditions", "A", "--effort", "medium",
                          "--k", "1", "--budget-usd", "1", "--limit", "1", "--out-plan", str(out2)]) == 0
    assert json.loads(out2.read_text(encoding="utf-8").splitlines()[0])["pins"]["b_stack_sha256"] is None


# ------------------------------------------------------------------ staged design: stage plans with k_from
def test_k_from_builds_only_the_later_layers():
    s = spec(k=3, k_from=2, stage="3")
    plan = P.build_plan(load("pilot")[:2], s, created_utc=FIXED_TIME)
    assert sorted({r["k"] for r in plan.runs}) == [2, 3] and plan.header["n_runs"] == 2 * 2 * 3 * 2
    assert plan.header["spec"]["k_from"] == 2 and plan.header["spec"]["stage"] == "3"
    assert not P.validate_lines(plan.text().splitlines())
    full = build(k=3)
    assert plan.plan_id != full.plan_id
    assert {r["run_id"] for r in plan.runs} == {r["run_id"] for r in full.runs if r["k"] >= 2}
    assert "k_from" not in build(k=3).header["spec"] and "stage" not in build(k=3).header["spec"]


@pytest.mark.parametrize("k_from", [0, 4, "2"])
def test_k_from_outside_1_to_k_is_refused(k_from):
    with pytest.raises(P.PlanError):
        build(k=3, k_from=k_from)


def test_stage_plans_run_score_and_analyse_complete_layers_only(tmp_path):
    from tsbench.score.score import score_dir
    from tsbench.stats import hypotheses as hy
    models = "claude-haiku-5-5,claude-sonnet-5-5,claude-opus-5-5"
    stages = {"s1": ("B,C", 1, 2), "s3": ("A,B,C", 3, 3)}  # stage 1: B and C, k 1-2; stage 3: A, B, C, k 3
    for name, (conds, k_from, k) in stages.items():
        plan = tmp_path / name / "plan.jsonl"
        assert plan_cli.main(["build", "--split", "pilot", "--models", models, "--conditions", conds,
                              "--effort", "medium", "--k", str(k), "--k-from", str(k_from), "--stage", name,
                              "--budget-usd", "10", "--limit", "3", "--out-plan", str(plan)]) == 0
        assert runner.main(["--plan", str(plan), "--out", str(tmp_path / name / "runs"), "--dry-run"]) == 0
        score_dir(tmp_path / name / "runs", "pilot")
    rows = hy.load_score_rows([tmp_path / n / "runs" / "scores.csv" for n in stages])
    assert sorted({r["k"] for r in rows if r["condition"] == "A"}) == [3]
    lay = hy.layered(rows, expect_tasks=3)
    assert lay["layers"] == {"primary": 3, "h1": 0, "h4": 0}  # A lacks layers 1-2: H1 is not tested yet
    assert len(lay["primary"]) == 4 and not any(r["name"].startswith("H1_") for r in lay["secondary"])


def test_the_two_stage_design_runs_and_tests_every_family_at_k3(tmp_path):
    """The two-stage design on the pilot split with the fake claude: stage 1 = B, C at k 1-3, stage 2 = A at k 1-3,
    all three models; after both stages the primary family and H1 have 3 complete layers."""
    from tsbench.score.score import score_dir
    from tsbench.stats import hypotheses as hy
    models = "claude-haiku-5-5,claude-sonnet-5-5,claude-opus-5-5"
    dirs = []
    for name, conds in (("1", "C,B"), ("2", "A")):  # run order of the design: C, then B, then A
        plan = tmp_path / f"stage{name}" / "plan.jsonl"
        assert plan_cli.main(["build", "--split", "pilot", "--stage", name, "--models", models, "--conditions", conds,
                              "--effort", "medium", "--k-from", "1", "--k", "3", "--budget-usd", "105",
                              "--limit", "2", "--out-plan", str(plan)]) == 0
        runs = P.load_plan(plan).runs
        assert len(runs) == 2 * 3 * len(conds.split(",")) * 3
        assert [r["k"] for r in runs] == sorted(r["k"] for r in runs)  # layer by layer
        if name == "1":  # inside every layer and task: C directly before B, so C and B are not separated in time
            assert [r["condition"] for r in runs] == ["C", "B"] * (len(runs) // 2)
        out = tmp_path / f"stage{name}" / "runs"
        assert runner.main(["--plan", str(plan), "--out", str(out), "--dry-run"]) == 0
        score_dir(out, "pilot")
        dirs.append(out / "scores.csv")
        if name == "1":  # after stage 1 only: the primary family is testable, H1 is not
            lay = hy.layered(hy.load_score_rows(dirs), expect_tasks=2, k_min=3)
            assert lay["layers"] == {"primary": 3, "h1": 0, "h4": 0} and len(lay["primary"]) == 4
    lay = hy.layered(hy.load_score_rows(dirs), expect_tasks=2, k_min=3)
    assert lay["layers"] == {"primary": 3, "h1": 3, "h4": 0}
    assert {f"H1_{m}" for m in models.split(",")} <= {r["name"] for r in lay["secondary"]}


# ------------------------------------------------------------------ system prompts come through resource()
def test_the_system_prompt_files_are_read_through_the_resource_function(monkeypatch):
    seen = []
    real = P.resource

    def spy(resource_id):
        seen.append(resource_id)
        return real(resource_id)

    monkeypatch.setattr(P, "resource", spy)
    build(system_prompt_file="prompts/neutral.txt")
    assert "prompts/neutral.txt" in seen


def test_a_resource_the_function_refuses_is_a_plan_error_not_a_file_read(monkeypatch):
    def refuse(resource_id):
        raise FileNotFoundError(f"no package resource {resource_id!r}")

    monkeypatch.setattr(P, "resource", refuse)
    with pytest.raises(P.PlanError, match="system prompt file prompts/neutral.txt not found"):
        build()
    with pytest.raises(P.PlanError, match=r"system prompt file prompts/neutral_curve.txt for answer schema 'curve'"):
        P.system_prompt_for("prompts/neutral.txt", "curve")


def test_the_data_folder_constant_is_not_part_of_the_core_interface():
    import tsbench.core as core
    assert "DATA_DIR" not in core.__all__
    assert not hasattr(P, "DATA_DIR")


def test_a_plan_file_is_written_through_a_temp_name_of_its_own(tmp_path, monkeypatch):
    """Two invocations on one folder must not share `plan.jsonl.tmp`: the second rename would find it gone."""
    names = []
    real_replace = pathlib.Path.replace

    def spy(self, target):
        names.append(self.name)
        return real_replace(self, target)

    monkeypatch.setattr(pathlib.Path, "replace", spy)
    plan = build(models=[HAIKU], conditions=["A"], limit=1)
    P.write_plan(plan, tmp_path / "plan.jsonl", markdown=False)
    P.write_plan(plan, tmp_path / "plan.jsonl", markdown=False)
    jsonl = [n for n in names if n.startswith("plan.jsonl.")]
    assert len(jsonl) == 2 and len(set(jsonl)) == 2 and "plan.jsonl.tmp" not in names
    assert sorted(p.name for p in tmp_path.iterdir()) == ["plan.jsonl", "plan.sha256"]


# ------------------------------------------------------------------ the one spec builder of both CLIs
def flags(**kw):
    base = {"split": "pilot", "models": HAIKU, "conditions": "a, B", "efforts": "medium", "k": 2, "budget_usd": 3.0,
            "limit": 1}
    base.update(kw)
    return base


def test_build_plan_raises_a_plan_error_for_an_unknown_condition():
    with pytest.raises(P.PlanError, match=r"^unknown condition 'Z'; choose from \['A', 'B', 'C'\]$"):
        P.build_plan(load("pilot")[:1], spec(conditions=["A", "Z"]))


def test_spec_from_flags_parses_the_comma_lists_into_the_spec():
    got = P.spec_from_flags(**flags(models=f" {HAIKU} ,{OPUS},", efforts="low,medium", gateway=True, stage="s1"))
    assert got == {"split": "pilot", "models": [HAIKU, OPUS], "conditions": ["A", "B"], "efforts": ["low", "medium"],
                   "k": 2, "budget_usd": 3.0, "limit": 1, "system_prompt_file": P.DEFAULT_SYSTEM_PROMPT,
                   "gateway": True, "stage": "s1"}
    assert "k_from" not in P.spec_from_flags(**flags()) and P.spec_from_flags(**flags(k_from=2))["k_from"] == 2


@pytest.mark.parametrize("over, message", [
    ({"models": " , "}, "--models must be a non-empty list without duplicates"),
    ({"models": f"{HAIKU},{HAIKU}"}, "--models must be a non-empty list without duplicates"),
    ({"models": "haiku"}, "'haiku' is an alias; give the full model id (e.g. claude-haiku-5-5)"),
    ({"conditions": ","}, "--conditions must be a non-empty list without duplicates"),
    ({"conditions": "a,A"}, "--conditions must be a non-empty list without duplicates"),
    ({"conditions": "A,Z"}, "unknown condition 'Z'; choose from ['A', 'B', 'C']"),
    ({"efforts": " "}, "--effort must be a non-empty list without duplicates"),
    ({"k": 0}, "--k must be >= 1"),
    ({"limit": 0}, "--limit must be >= 1"),
    ({"budget_usd": 0}, "--budget-usd must be > 0"),
])
def test_spec_from_flags_refuses_a_bad_flag_with_its_name(over, message):
    with pytest.raises(P.PlanError) as e:
        P.spec_from_flags(**flags(**over))
    assert str(e.value) == message


def test_the_preregistration_guard_is_one_message_for_both_clis():
    P.require_preregistration("pilot", None)
    P.require_preregistration("confirmatory", "10.1234/x")
    for doi in (None, "", "not-a-doi"):
        with pytest.raises(P.PlanError, match=r"^--split confirmatory needs --i-have-preregistered <DOI> \(the "
                                              r"preregistration must be deposited before any model sees the "
                                              r"confirmatory tasks\)$"):
            P.require_preregistration("confirmatory", doi)


def test_b_stack_digest_needs_the_stack_for_a_confirmatory_plan_and_warns_for_a_pilot(monkeypatch):
    from tsbench.conditions import b_stack
    asked, warned = [], []
    monkeypatch.setattr(b_stack, "digest_if_present", lambda venv, *a, **k: asked.append(venv))
    assert P.b_stack_digest(["A", "C"], "pilot", None) is None and asked == []  # B not requested: nothing is looked up
    assert P.b_stack_digest(["A", "B"], "pilot", None, warn=warned.append) is None
    assert len(asked) == 1 and warned == ["the B stack is not built or not valid; the plan does not pin it "
                                           "(run `tsbench env b-stack`)"]
    with pytest.raises(P.PlanError, match="^condition B needs the fixed B stack: run `tsbench env b-stack` first$"):
        P.b_stack_digest(["B"], "confirmatory", None)
    monkeypatch.setattr(b_stack, "digest_if_present", lambda venv, *a, **k: "cd" * 32)
    assert P.b_stack_digest(["B"], "confirmatory", None) == "cd" * 32


def test_build_from_spec_refuses_a_confirmatory_b_plan_without_the_stack_before_loading_tasks(monkeypatch):
    import tsbench.tasks as tasks_mod
    from tsbench.conditions import b_stack

    def boom(split):
        raise AssertionError("tasks were loaded")

    monkeypatch.setattr(tasks_mod, "load", boom)
    monkeypatch.setattr(b_stack, "digest_if_present", lambda venv, *a, **k: None)
    s = P.spec_from_flags(**flags(split="confirmatory", conditions="B"))
    with pytest.raises(P.PlanError, match="condition B needs the fixed B stack"):
        P.build_from_spec(s, b_venv=None, claude_cli_version=None)


def test_build_from_spec_selects_the_tasks_and_names_what_is_wrong(monkeypatch):
    s = P.spec_from_flags(**flags(conditions="A", limit=None))
    plan = P.build_from_spec(s, b_venv=None, claude_cli_version="9.9.9", task_ids=["P-diagram-01"])
    assert {r["task_id"] for r in plan.runs} == {"P-diagram-01"}
    assert plan.header["pins"]["claude_cli_version"] == "9.9.9"
    with pytest.raises(P.PlanError, match="^unknown task id\\(s\\) in this selection: P-zz-02$"):
        P.build_from_spec(s, b_venv=None, claude_cli_version=None, task_ids=["P-zz-02"])
    with pytest.raises(P.PlanError, match="^the --task-class / --task-ids selection is empty$"):
        P.build_from_spec(s, b_venv=None, claude_cli_version=None, task_classes=["no_such_class"])
    import tsbench.tasks as tasks_mod
    monkeypatch.setattr(tasks_mod, "load", lambda split: [])
    with pytest.raises(P.PlanError, match="^no tasks in split 'pilot'$"):
        P.build_from_spec(s, b_venv=None, claude_cli_version=None)


def test_the_answer_formats_table_names_the_fit_format():
    assert P.ANSWER_FORMATS["fit"] == "contract_answer_v1"
