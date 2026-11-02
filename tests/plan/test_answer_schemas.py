"""The answer schema is a property of the task record: plan, argv, runner and a dry run over a mix of schemas.

No network, no key, no real `claude` (the fake from tsbench.run). Only pilot tasks are used.
"""
from __future__ import annotations

import copy
import hashlib
import json
import pathlib

import pytest

from tsbench import conditions
from tsbench import plan as P
from tsbench.core import resource
from tsbench.run import runner
from tsbench.score import score as score_cli
from tsbench.tasks import load

HAIKU, OPUS = "claude-haiku-5-5", "claude-opus-5-5"
FIXED_TIME = "2026-10-24T00:00:00+00:00"
REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
CURVE_PROMPT = resource("prompts/neutral_curve.txt").read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def no_claude_version_probe(monkeypatch):
    monkeypatch.setattr(P, "claude_version_probe", lambda: None)


def mix(n_curve=3, n_fit=2):
    pilot = load("pilot")
    return [t for t in pilot if t["class"] == "curve"][:n_curve] + [t for t in pilot if t["class"] != "curve"][:n_fit]


def spec(**kw):
    base = {"split": "pilot", "models": [HAIKU, OPUS], "conditions": ["A", "B", "C"], "efforts": ["medium"],
            "k": 1, "budget_usd": 10.0, "limit": None}
    base.update(kw)
    return base


def manifest(out):
    return json.loads((pathlib.Path(out) / "MANIFEST.json").read_text(encoding="utf-8"))


# ------------------------------------------------------------------ the schemas themselves
def test_schema_files_and_hashes():
    fit, curve = conditions.ANSWER_SCHEMAS["fit"], conditions.ANSWER_SCHEMAS["curve"]
    # fit.schema.json has the bytes of answer.schema.json, so the answer_schema_sha256 pin of a plan stays valid
    schemas_dir = REPO_ROOT / "src/tsbench/data/schemas"
    assert (schemas_dir / "fit.schema.json").read_bytes() == (schemas_dir / "answer.schema.json").read_bytes()
    assert fit.sha256 == conditions.ANSWER_SCHEMA_SHA256
    assert fit.sha256 == hashlib.sha256(conditions.ANSWER_SCHEMAS["fit"].compact.encode()).hexdigest()
    assert fit.sha256 != curve.sha256 and " " not in curve.compact
    assert (json.loads(curve.compact)
        == json.loads((REPO_ROOT / "src/tsbench/data/schemas/curve.schema.json").read_text(encoding="utf-8")))
    s = curve.schema
    assert s["required"] == ["points", "reason"] and s["additionalProperties"] is False
    item = s["properties"]["points"]["items"]
    assert item["required"] == ["dq_over_b", "term", "e_over_b"] and item["additionalProperties"] is False
    assert {k: v["type"] for k, v in item["properties"].items()} == {
        "dq_over_b": "number", "term": "string", "e_over_b": "number"}
    assert conditions.get_answer_schema(None) is fit and conditions.get_answer_schema("curve") is curve
    with pytest.raises(ValueError):
        conditions.get_answer_schema("nope")


@pytest.mark.parametrize("key", ["A", "B", "C"])
def test_argv_takes_the_schema_of_the_record(key):
    cond = conditions.get(key)
    kw = dict(settings_path="/cfg/settings.json", mcp_config_path="/cfg/ts.json")
    fit = runner.build_argv(["claude"], cond, HAIKU, "medium", 1.5, **kw)
    curve = runner.build_argv(["claude"], cond, HAIKU, "medium", 1.5, answer_schema="curve", **kw)
    assert fit[-2:] == ["--json-schema", conditions.ANSWER_SCHEMAS["fit"].compact]
    assert curve[-2:] == ["--json-schema", conditions.ANSWER_SCHEMAS["curve"].compact]
    assert fit[:-2] == curve[:-2]  # nothing else differs
    with pytest.raises(ValueError):
        runner.build_argv(["claude"], cond, HAIKU, "medium", 1.5, answer_schema="nope", **kw)


# ------------------------------------------------------------------ the plan
def test_plan_records_carry_name_and_hash_of_their_schema():
    plan = P.build_plan(mix(), spec(), created_utc=FIXED_TIME)
    by_task = {t["id"]: t["answer_schema"] for t in mix()}
    assert {"fit", "curve"} == set(by_task.values())
    for r in plan.runs:
        name = by_task[r["task_id"]]
        sch = conditions.ANSWER_SCHEMAS[name]
        assert r["answer_schema"] == name and r["answer_schema_sha256"] == sch.sha256
        assert r["answer_format"]["schema_sha256"] == sch.sha256 and r["answer_format"]["enforced"] == "json-schema"
        assert r["argv_template"][-2:] == ["--json-schema", sch.compact]
        assert r["system_prompt_file"] == ("prompts/neutral_curve.txt" if name == "curve"
                                           else "prompts/neutral.txt")  # resource ids, never paths
        assert hashlib.sha256(r["system_prompt_text"].encode()).hexdigest() == r["system_prompt_sha256"]
    assert {r["answer_format"]["name"] for r in plan.runs} == {"contract_answer_v1", "contract_curve_v1"}
    assert plan.header["schema_version"] == 4 == P.SCHEMA_VERSION


def test_header_pins_every_schema_hash():
    plan = P.build_plan(mix(), spec(), created_utc=FIXED_TIME)
    pins = plan.header["pins"]
    assert pins["answer_schemas"] == {n: s.sha256 for n, s in conditions.ANSWER_SCHEMAS.items()}
    assert pins["answer_schema_sha256"] == conditions.ANSWER_SCHEMAS["fit"].sha256  # the single-schema pin
    assert P.live_pins(None)["answer_schemas"] == pins["answer_schemas"]
    drift = P.check_pins(pins, {**pins, "answer_schemas": {**pins["answer_schemas"], "curve": "0" * 64}})
    assert [d["pin"] for d in drift] == ["answer_schemas"]


def lines_of(plan):
    return [P.canonical(plan.header)] + [P.canonical(r) for r in plan.runs]


def test_plan_validation_checks_schema_consistency():
    plan = P.build_plan(mix(), spec(models=[HAIKU], conditions=["A"]), created_utc=FIXED_TIME)
    assert P.validate_lines(lines_of(plan)) == []
    lines = lines_of(plan)
    rec = json.loads(lines[1])
    rec["answer_schema_sha256"] = "0" * 64  # differs from the header pin and from answer_format
    errs = P.validate_lines([lines[0], json.dumps(rec)] + lines[2:])
    assert any("header pin" in e for e in errs) and any("answer_format" in e for e in errs)
    rec = json.loads(lines[1])
    rec["answer_schema"] = "other"
    assert P.validate_lines([lines[0], json.dumps(rec)] + lines[2:])  # not in the enum


def test_unknown_schema_in_a_task_is_refused():
    bad = dict(mix(0, 1)[0], answer_schema="nope")
    with pytest.raises(P.PlanError, match="unknown answer schema"):
        P.build_plan([bad], spec(), created_utc=FIXED_TIME)


def test_plans_without_an_answer_schema_load_and_run_as_fit(tmp_path):
    """Version-2 plans have no answer_schema and no pins.answer_schemas: they are `fit`."""
    new = P.build_plan(mix(0, 2), spec(models=[HAIKU], conditions=["A"]), created_utc=FIXED_TIME)
    runs = []
    for r in new.runs:
        r = copy.deepcopy(r)
        for k in ("answer_schema", "answer_schema_sha256"):
            r.pop(k)
        runs.append(r)
    pins = {k: v for k, v in new.header["pins"].items() if k != "answer_schemas"}
    old = P.Plan({**new.header, "schema_version": 2, "pins": pins, "plan_id": P.plan_id_of(runs)}, runs)
    assert P.validate_lines(lines_of(old)) == []
    path = tmp_path / "plan.jsonl"
    P.write_plan(old, path, markdown=False)
    assert P.load_plan(path).plan_id == old.plan_id
    out = tmp_path / "out"
    assert runner.main(["--plan", str(path), "--out", str(out), "--dry-run"]) == 0
    meta = json.loads(next(out.glob("*/A/medium/*.meta.json")).read_text(encoding="utf-8"))
    assert meta["argv"][-1] == conditions.ANSWER_SCHEMAS["fit"].compact


def test_runner_aborts_when_the_planned_schema_hash_is_not_the_live_one(tmp_path, capsys):
    plan = P.build_plan(mix(1, 0), spec(models=[HAIKU], conditions=["A"]), created_utc=FIXED_TIME)
    runs = copy.deepcopy(plan.runs)
    for r in runs:
        r["answer_schema_sha256"] = r["answer_format"]["schema_sha256"] = "1" * 64
    header = {**plan.header, "plan_id": P.plan_id_of(runs), "pins": {**plan.header["pins"], "answer_schemas": {
        **plan.header["pins"]["answer_schemas"], "curve": "1" * 64}}}
    path = tmp_path / "plan.jsonl"
    P.write_plan(P.Plan(header, runs), path, markdown=False)
    assert P.load_plan(path)  # it is a valid plan; only the live schema file disagrees with it
    with pytest.raises(SystemExit) as e:
        runner.main(["--plan", str(path), "--out", str(tmp_path / "out"), "--dry-run"])
    assert e.value.code == 2 and "answer schema" in capsys.readouterr().err
    assert not list((tmp_path / "out").glob("*/*/*/*.jsonl"))


# ------------------------------------------------------------------ a dry run over a mix that includes curve tasks
def dry_run_mix(tmp_path, monkeypatch=None, force_fit=False):
    tasks = mix(3, 2)
    plan = P.build_plan(tasks, spec(), created_utc=FIXED_TIME)
    path = tmp_path / "plan.jsonl"
    P.write_plan(plan, path, markdown=False)
    out = tmp_path / "out"
    if force_fit:  # a runner that ignores the record's schema
        real = runner.build_argv
        monkeypatch.setattr(runner, "build_argv", lambda *a, **kw: real(*a, **{**kw, "answer_schema": "fit"}))
    assert runner.main(["--plan", str(path), "--out", str(out), "--dry-run"]) == 0
    return plan, out


def read_rows(out):
    import csv
    score_cli.score_dir(out, "pilot")
    with open(out / "scores.csv", newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def test_dry_run_mix_passes_the_schema_of_each_record_and_scores_curve_rows(tmp_path):
    plan, out = dry_run_mix(tmp_path)
    assert manifest(out)["counts"]["done"] == len(plan.runs) == 5 * 2 * 3
    by_task = {t["id"]: t["answer_schema"] for t in mix(3, 2)}
    for meta_path in out.glob("*/*/*/*.meta.json"):
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        name = by_task[meta["task_id"]]
        assert meta["argv"][-2:] == ["--json-schema", conditions.ANSWER_SCHEMAS[name].compact]
        named = meta["argv"][meta["argv"].index("--system-prompt-file") + 1]  # <OUT>/system-prompts/...
        prompt = (out / named.removeprefix("<OUT>/")).read_text(encoding="utf-8")
        assert (prompt == CURVE_PROMPT) == (name == "curve")
    rows = read_rows(out)
    curve = [r for r in rows if by_task[r["task_id"]] == "curve"]
    assert len(curve) == 3 * 2 * 3
    parsed = [r for r in curve if r["unparseable"] == "False"]
    right = [r for r in parsed if r["correct"] == "True"]
    wrong = [r for r in parsed if r["correct"] == "False"]
    # a mix, not all of one kind: the fake answers right or wrong by a hash, 1 run in 20 gives no structured answer
    assert right and wrong
    assert all(r["curve_max_rel_err"] == "0.0" for r in right)
    assert all(float(r["curve_max_rel_err"]) == pytest.approx(0.25, abs=1e-3) for r in wrong)
    assert all(r["rel_err_dq"] == "" and r["dq"] == "" for r in curve)
    fit = [r for r in rows if by_task[r["task_id"]] == "fit"]
    assert fit and all(r["curve_max_rel_err"] == "" for r in fit) and any(r["correct"] == "True" for r in fit)


def test_dry_run_with_the_wrong_schema_is_visible_in_the_scores(tmp_path, monkeypatch):
    """The fake answers by the schema in argv: a runner that passes `fit` for a curve task gets no curve answers."""
    plan, out = dry_run_mix(tmp_path, monkeypatch, force_fit=True)
    by_task = {t["id"]: t["answer_schema"] for t in mix(3, 2)}
    curve = [r for r in read_rows(out) if by_task[r["task_id"]] == "curve"]
    assert len(curve) == 18 and not any(r["correct"] == "True" for r in curve)
    assert all(r["unparseable"] == "True" for r in curve)


# ------------------------------------------------------------------ batch and pairing (all four schemas)
def mix4():
    pilot = load("pilot")

    def pick(cls, n):
        return [t for t in pilot if t["class"] == cls][:n]

    return (pick("curve", 1) + pick("batch", 3) + pick("pairing", 1) + pick("literature_all", 1)
            + pick("closed_form", 1) + pick("diagram", 1))


def test_schema_registry_has_all_four_with_pinned_hashes():
    assert sorted(conditions.ANSWER_SCHEMAS) == ["batch", "curve", "diagram", "fit", "pairing"]
    for name in ("batch", "pairing", "diagram"):
        sch = conditions.get_answer_schema(name)
        assert sch.sha256 == hashlib.sha256(sch.compact.encode()).hexdigest() and " " not in sch.compact
        schema_path = REPO_ROOT / f"src/tsbench/data/schemas/{name}.schema.json"
        assert json.loads(sch.compact) == json.loads(schema_path.read_text(encoding="utf-8"))
    assert len({s.sha256 for s in conditions.ANSWER_SCHEMAS.values()}) == 5
    assert set(P.ANSWER_FORMATS) == set(conditions.ANSWER_SCHEMAS)
    plan = P.build_plan(mix4(), spec(), created_utc=FIXED_TIME)
    assert plan.header["pins"]["answer_schemas"] == {n: s.sha256 for n, s in conditions.ANSWER_SCHEMAS.items()}
    assert {r["answer_schema"] for r in plan.runs} == {"fit", "curve", "batch", "pairing", "diagram"}


def test_json_schema_flag_follows_the_record_for_batch_and_pairing():
    plan = P.build_plan(mix4(), spec(), created_utc=FIXED_TIME)
    for r in plan.runs:
        sch = conditions.ANSWER_SCHEMAS[r["answer_schema"]]
        assert r["argv_template"][-2:] == ["--json-schema", sch.compact] and r["answer_schema_sha256"] == sch.sha256
        want = {"fit": "neutral.txt", "curve": "neutral_curve.txt", "batch": "neutral_batch.txt",
                "pairing": "neutral_pairing.txt", "diagram": "neutral_diagram.txt"}[r["answer_schema"]]
        assert r["system_prompt_file"].endswith("/" + want)
    assert P.validate_lines([P.canonical(plan.header)] + [P.canonical(r) for r in plan.runs]) == []


def test_pins_without_batch_and_pairing_entries_are_not_drift():
    live = P.live_pins(None)
    old = {**live, "answer_schemas": {k: v for k, v in live["answer_schemas"].items() if k in ("fit", "curve")}}
    assert P.check_pins(old, live) == []
    changed = {**old, "answer_schemas": {**old["answer_schemas"], "fit": "0" * 64}}
    assert [d["pin"] for d in P.check_pins(changed, live)] == ["answer_schemas"]


def test_dry_run_scores_batch_and_pairing_rows_with_a_mix_of_right_wrong_and_unparseable(tmp_path):
    import csv
    tasks = mix4()
    plan = P.build_plan(tasks, spec(k=4), created_utc=FIXED_TIME)
    path = tmp_path / "plan.jsonl"
    P.write_plan(plan, path, markdown=False)
    out = tmp_path / "out"
    assert runner.main(["--plan", str(path), "--out", str(out), "--dry-run"]) == 0
    by_task = {t["id"]: t["answer_schema"] for t in tasks}
    for meta_path in out.glob("*/*/*/*.meta.json"):
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        assert meta["argv"][-1] == conditions.ANSWER_SCHEMAS[by_task[meta["task_id"]]].compact
    score_cli.score_dir(out, "pilot")
    with open(out / "scores.csv", newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    batch = [r for r in rows if by_task[r["task_id"]] == "batch"]
    pairing = [r for r in rows if by_task[r["task_id"]] == "pairing"]
    assert len(batch) == 3 * 2 * 3 * 4 and len(pairing) == 1 * 2 * 3 * 4
    for group in (batch, pairing):
        assert any(r["correct"] == "True" for r in group) and any(r["correct"] == "False" for r in group)
    assert any(r["unparseable"] == "True" for r in batch + pairing)  # the designed 1-in-20 without a structured answer
    ok_batch = [r for r in batch if r["correct"] == "True"]
    assert ok_batch and all(r["item_accuracy"] == "1.0" and r["dq"] == "" and r["curve_max_rel_err"] == ""
                            for r in ok_batch)
    bad_batch = [r for r in batch if r["unparseable"] == "False" and r["correct"] == "False"]
    assert bad_batch and all(0 < float(r["item_accuracy"]) < 1 for r in bad_batch)
    ok_pair = [r for r in pairing if r["correct"] == "True"]
    assert ok_pair and all(r["edge_f1"] == "1.0" and r["ground_correct"] == "True" for r in ok_pair)
    bad_pair = [r for r in pairing if r["unparseable"] == "False" and r["correct"] == "False"]
    assert bad_pair and all(float(r["edge_f1"]) < 1 for r in bad_pair)
    fit = [r for r in rows if by_task[r["task_id"]] == "fit"]
    assert fit and all(r["item_accuracy"] == "" and r["edge_f1"] == "" for r in fit)
    assert (out / "rates.csv").read_text(encoding="utf-8").splitlines()[0] == ",".join(score_cli.RATE_COLUMNS)


TOOLS_SENTENCE = "If tools are available in this session, you may use them."


def test_every_system_prompt_offers_tools_in_the_same_neutral_sentence():
    """A, B and C get one system prompt per schema; the only difference between conditions is the tool set."""
    plan = P.build_plan(mix4(), spec(), created_utc=FIXED_TIME)
    for schema in conditions.ANSWER_SCHEMAS:
        text = (REPO_ROOT / "src/tsbench/data/prompts" / P.system_prompt_for("prompts/neutral.txt", schema)
                .removeprefix("prompts/")).read_text(encoding="utf-8")
        assert text.splitlines().count(TOOLS_SENTENCE) == 1, schema
    by_task: dict[str, set[str]] = {}
    for r in plan.runs:
        by_task.setdefault(r["task_id"], set()).add(r["system_prompt_sha256"])
    assert by_task and all(len(shas) == 1 for shas in by_task.values())
    assert {r["condition"] for r in plan.runs} == {"A", "B", "C"}
