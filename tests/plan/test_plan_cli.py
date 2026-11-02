"""Tests for the `tsbench plan` command line (tsbench.plan.__main__): options, messages and exit codes.

The file is not called test___main__.py, so that it does not shadow other __main__ tests. No confirmatory task is read:
the confirmatory builds load pilot tasks relabelled as confirmatory.
"""
from __future__ import annotations

import json
import pathlib
import re

import pytest

import tsbench.tasks
from tsbench import plan as P
from tsbench.conditions import b_stack
from tsbench.plan import __main__ as plan_cli
from tsbench.tasks import load

HAIKU = "claude-haiku-5-5"
DOI = "10.1234/abc"


@pytest.fixture(autouse=True)
def clean_env(monkeypatch, tmp_path_factory):
    fake_venv = tmp_path_factory.getbasetemp() / "fake-venv-B-plan-cli"
    fake_venv.mkdir(exist_ok=True)
    monkeypatch.setenv("TSBENCH_B_VENV", str(fake_venv))  # never the real venv-B
    monkeypatch.setenv("COLUMNS", "400")  # argparse help on one line per option
    monkeypatch.setattr(P, "claude_version_probe", lambda: None)


@pytest.fixture
def relabelled(monkeypatch):
    pilot = load("pilot")
    monkeypatch.setattr(tsbench.tasks, "load", lambda split: [dict(t, split=split) for t in pilot])


def build_args(out, *extra, split="pilot", conditions="A"):
    return ["build", "--split", split, "--models", HAIKU, "--conditions", conditions, "--effort", "medium",
            "--k", "1", "--budget-usd", "1", "--limit", "1", "--out-plan", str(out), *extra]


def header(path):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8").splitlines()[0])


# ---------------------------------------------------------------- the parser
def test_help_names_every_command_and_option(capsys):
    with pytest.raises(SystemExit) as e:
        plan_cli.main(["--help"])
    assert e.value.code == 0
    text = capsys.readouterr().out
    assert text.startswith("usage: tsbench plan ")
    assert "\n\nBuild and validate run plans.\n\n" in text
    out = " ".join(text.split())
    assert "build expand a selection to plan.jsonl (pilot) or plan.sealed.json (confirmatory)" in out
    assert "validate check a plan against plan.schema.json and its own hashes" in out


def test_build_help_names_every_option_with_its_text(capsys):
    with pytest.raises(SystemExit):
        plan_cli.main(["build", "--help"])
    out = " ".join(capsys.readouterr().out.split())  # a long option puts its help on the next line
    for text in ("--split {pilot,confirmatory}", "--effort EFFORT one effort or a comma list",
                 "--k K last repetition (k layer) of the plan",
                 "--k-from K_FROM first repetition (default 1): a stage of the staged design holds the layers "
                 "k-from..k",
                 "--stage STAGE label of the stage, written into the plan's spec",
                 "--task-class TASK_CLASS comma list: keep only the tasks of these classes (applied before --limit)",
                 "--task-ids TASK_IDS comma list of task ids: keep only these (applied after --task-class, before "
                 "--limit)",
                 "--b-venv DIR venv of condition B whose digest the plan pins (default: $TSBENCH_B_VENV or "
                 "~/.cache/tsbench/venv-B)",
                 "--i-have-preregistered DOI",
                 "--unseal-to UNSEAL_TO confirmatory only: also write the clear plan to this path outside the repo"):
        assert text in out, text


@pytest.mark.parametrize("option", ["--split", "--models", "--conditions", "--effort", "--k", "--budget-usd",
                                    "--out-plan"])
def test_every_required_build_option_is_required(tmp_path, capsys, option):
    args = build_args(tmp_path / "plan.jsonl")
    i = args.index(option)
    with pytest.raises(SystemExit) as e:
        plan_cli.main(args[:i] + args[i + 2:])
    assert e.value.code == 2
    assert option in capsys.readouterr().err
    assert not list(tmp_path.iterdir())


def test_a_command_and_a_known_split_are_required(tmp_path, capsys):
    with pytest.raises(SystemExit) as e:
        plan_cli.main([])
    assert e.value.code == 2 and "required" in capsys.readouterr().err
    with pytest.raises(SystemExit) as e:
        plan_cli.main(build_args(tmp_path / "plan.jsonl", split="dev"))
    assert e.value.code == 2 and "invalid choice: 'dev'" in capsys.readouterr().err


def test_gateway_is_a_flag_and_reaches_the_spec(tmp_path):
    assert plan_cli.main(build_args(tmp_path / "g" / "plan.jsonl", "--gateway")) == 0
    assert header(tmp_path / "g" / "plan.jsonl")["spec"]["gateway"] is True
    assert plan_cli.main(build_args(tmp_path / "n" / "plan.jsonl")) == 0
    assert header(tmp_path / "n" / "plan.jsonl")["spec"]["gateway"] is False


# ---------------------------------------------------------------- build
def test_build_prints_the_path_counts_id_and_hash(tmp_path, capsys):
    out = tmp_path / "plan.jsonl"
    assert plan_cli.main(build_args(out)) == 0
    h = header(out)
    digest = (tmp_path / "plan.sha256").read_text(encoding="utf-8").split()[0]
    assert capsys.readouterr().out == f"plan written: {out} runs=1 plan_id={h['plan_id']} sha256={digest}\n"


def test_build_selects_several_classes_from_a_comma_list(tmp_path):
    out = tmp_path / "plan.jsonl"
    args = build_args(out, "--task-class", "diagram,curve")
    i = args.index("--limit")
    assert plan_cli.main(args[:i] + args[i + 2:]) == 0
    classes = {json.loads(ln)["task_id"].split("-")[1] for ln in out.read_text(encoding="utf-8").splitlines()[1:]}
    assert classes == {"diagram", "curve"}


def test_build_names_every_unknown_task_id(tmp_path, capsys):
    assert plan_cli.main(build_args(tmp_path / "plan.jsonl", "--task-ids", "P-zz-02,P-diagram-01,P-aa-01")) == 2
    assert capsys.readouterr().err == "plan: unknown task id(s) in this selection: P-aa-01, P-zz-02\n"


def test_build_reports_the_plan_error(tmp_path, capsys):
    args = build_args(tmp_path / "plan.jsonl")
    args[args.index("--models") + 1] = "haiku"
    assert plan_cli.main(args) == 2
    err = capsys.readouterr().err
    assert err.startswith("plan: ") and "haiku" in err and err != "plan: None\n"


def test_build_pins_the_claude_version(tmp_path, monkeypatch):
    monkeypatch.setattr(P, "claude_version_probe", lambda: "9.9.9 (Claude Code)")
    assert plan_cli.main(build_args(tmp_path / "plan.jsonl")) == 0
    assert "9.9.9" in json.dumps(header(tmp_path / "plan.jsonl")["pins"])


def test_build_looks_for_the_b_stack_in_the_given_venv(tmp_path, monkeypatch, capsys):
    seen = []
    monkeypatch.setattr(b_stack, "digest_if_present", lambda venv, *a, **k: seen.append(venv))
    venv = tmp_path / "my-venv"
    assert plan_cli.main(build_args(tmp_path / "plan.jsonl", "--b-venv", str(venv), conditions="A,B")) == 0
    assert seen == [venv]
    assert capsys.readouterr().err == ("WARNING: the B stack is not built or not valid; the plan does not pin it "
                                       "(run `tsbench env b-stack`)\n")


def test_a_b_venv_inside_the_repo_is_a_clean_plan_error(tmp_path, capsys):
    inside = b_stack.REPO_ROOT / "venv-inside-repo"
    assert plan_cli.main(build_args(tmp_path / "plan.jsonl", "--b-venv", str(inside), conditions="A,B")) == 2
    captured = capsys.readouterr()
    assert captured.err.startswith("plan: B venv ") and "lies inside the repo" in captured.err
    assert "Traceback" not in captured.err and not (tmp_path / "plan.jsonl").exists()


@pytest.mark.parametrize("doi", [None, "not-a-doi"])
def test_confirmatory_needs_a_doi(tmp_path, capsys, doi):
    extra = ["--i-have-preregistered", doi] if doi else []
    assert plan_cli.main(build_args(tmp_path / "plan.jsonl", *extra, split="confirmatory")) == 2
    assert capsys.readouterr().err == (
        "plan: --split confirmatory needs --i-have-preregistered <DOI> (the preregistration must be deposited before "
        "any model sees the confirmatory tasks)\n")


def test_confirmatory_unseal_writes_the_clear_plan_without_markdown(tmp_path, capsys, relabelled):
    clear = tmp_path / "elsewhere" / "plan.jsonl"
    rc = plan_cli.main(build_args(tmp_path / "plan.jsonl", "--i-have-preregistered", DOI, "--unseal-to", str(clear),
                                  split="confirmatory"))
    assert rc == 0
    out = capsys.readouterr().out.splitlines()
    assert re.fullmatch(rf"sealed plan written: {re.escape(str(tmp_path / P.SEALED_NAME))} runs=1 plan_id=\S+",
                        out[0])
    assert out[1] == f"clear plan written outside the repo: {clear.resolve()}"
    assert sorted(p.name for p in clear.parent.iterdir()) == ["plan.jsonl", "plan.sha256"]


def test_confirmatory_unseal_inside_the_repo_is_refused(tmp_path, capsys, relabelled):
    inside = P.REPO_ROOT / "build" / "never-written" / "plan.jsonl"
    rc = plan_cli.main(build_args(tmp_path / "plan.jsonl", "--i-have-preregistered", DOI, "--unseal-to", str(inside),
                                  split="confirmatory"))
    assert rc == 2 and not inside.exists()
    assert capsys.readouterr().err == "plan: --unseal-to must lie outside the repository\n"


# ---------------------------------------------------------------- validate
def test_validate_prints_ok_with_the_id_count_and_schema(tmp_path, capsys):
    out = tmp_path / "plan.jsonl"
    assert plan_cli.main(build_args(out)) == 0
    capsys.readouterr()
    h = header(out)
    assert plan_cli.main(["validate", str(out)]) == 0
    assert capsys.readouterr().out == (f"OK plan_id={h['plan_id']} runs=1 schema_version={h['schema_version']}\n")


def test_validate_marks_a_sealed_plan(tmp_path, capsys, relabelled):
    assert plan_cli.main(build_args(tmp_path / "plan.jsonl", "--i-have-preregistered", DOI,
                                    split="confirmatory")) == 0
    capsys.readouterr()
    assert plan_cli.main(["validate", str(tmp_path / P.SEALED_NAME)]) == 0
    assert capsys.readouterr().out.startswith("OK sealed plan_id=")


def test_validate_prints_at_most_30_errors_to_stderr(tmp_path, capsys):
    out = tmp_path / "plan.jsonl"
    args = build_args(out)
    args[args.index("--limit") + 1] = "40"
    assert plan_cli.main(args) == 0
    lines = out.read_text(encoding="utf-8").splitlines()
    out.write_text("\n".join([lines[0]] + [ln.replace('"condition": "A"', '"condition": "Z"') for ln in lines[1:]])
                   + "\n", encoding="utf-8")
    assert len(P.validate_lines(out.read_text(encoding="utf-8").splitlines())) > 30
    capsys.readouterr()
    assert plan_cli.main(["validate", str(out)]) == 1
    captured = capsys.readouterr()
    err = captured.err.splitlines()
    assert len(err) == 30 and all(e.startswith("INVALID ") for e in err) and captured.out == ""


def test_selection_and_limit_messages_are_exact(tmp_path, capsys):
    assert plan_cli.main(build_args(tmp_path / "plan.jsonl", "--task-class", "no_such_class")) == 2
    assert capsys.readouterr().err == "plan: the --task-class / --task-ids selection is empty\n"
    args = build_args(tmp_path / "plan.jsonl")
    args[args.index("--limit") + 1] = "0"
    assert plan_cli.main(args) == 2
    assert capsys.readouterr().err == "plan: --limit must be >= 1\n"


def test_build_pins_the_sandbox_settings_of_the_given_b_venv(tmp_path):
    from tsbench.conditions import sandbox
    venv = tmp_path / "other-venv-B"
    venv.mkdir()
    out = tmp_path / "plan.jsonl"
    assert plan_cli.main(build_args(out, "--b-venv", str(venv))) == 0
    pin = header(out)["pins"]["sandbox_settings_sha256"]
    assert pin == sandbox.settings_sha256(P.REPO_ROOT, b_venv=venv)
    assert pin != sandbox.settings_sha256(P.REPO_ROOT)


def test_confirmatory_with_b_and_no_stack_message_is_exact(tmp_path, capsys, relabelled):
    rc = plan_cli.main(build_args(tmp_path / "plan.jsonl", "--i-have-preregistered", DOI, split="confirmatory",
                                  conditions="A,B"))
    assert rc == 2
    assert capsys.readouterr().err == "plan: condition B needs the fixed B stack: run `tsbench env b-stack` first\n"


def test_an_unknown_condition_is_a_clean_plan_error_not_a_traceback(tmp_path, capsys):
    args = build_args(tmp_path / "plan.jsonl")
    args[args.index("--conditions") + 1] = "A,Z"
    assert plan_cli.main(args) == 2
    assert capsys.readouterr().err == "plan: unknown condition 'Z'; choose from ['A', 'B', 'C']\n"
    assert not (tmp_path / "plan.jsonl").exists()


def test_the_flags_of_build_are_checked_by_name(tmp_path, capsys):
    args = build_args(tmp_path / "plan.jsonl")
    args[args.index("--models") + 1] = f"{HAIKU},{HAIKU}"
    assert plan_cli.main(args) == 2
    assert capsys.readouterr().err == "plan: --models must be a non-empty list without duplicates\n"
