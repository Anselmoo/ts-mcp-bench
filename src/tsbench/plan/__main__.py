"""CLI: tsbench plan build|validate (see src/tsbench/plan/__init__.py)."""
from __future__ import annotations

import argparse
import pathlib
import sys

from tsbench import plan as P


def _fail(msg: str, code: int = 2) -> int:
    print(f"plan: {msg}", file=sys.stderr)
    return code


def cmd_build(a) -> int:
    """`build`: select the tasks, expand the spec and write the plan (sealed for confirmatory); returns the exit
    code."""
    from tsbench.conditions import argv as argv_mod
    from tsbench.conditions import b_stack
    try:
        P.require_preregistration(a.split, a.preregistered)
        spec = P.spec_from_flags(split=a.split, models=a.models, conditions=a.conditions, efforts=a.effort, k=a.k,
                                 budget_usd=a.budget_usd, limit=a.limit, system_prompt_file=a.system_prompt_file,
                                 gateway=a.gateway, k_from=a.k_from, stage=a.stage)
        plan = P.build_from_spec(
            spec, b_venv=a.b_venv, claude_cli_version=P.claude_version_probe(),
            task_classes=[c.strip() for c in (a.task_class or "").split(",") if c.strip()],
            task_ids=[i.strip() for i in (a.task_ids or "").split(",") if i.strip()],
            warn=lambda msg: print(f"WARNING: {msg}", file=sys.stderr))
    except (P.PlanError, b_stack.BStackError) as e:
        return _fail(str(e))
    out = pathlib.Path(a.out_plan)
    if a.split == "pilot":
        digest = P.write_plan(plan, out)
        print(f"plan written: {out} runs={plan.header['n_runs']} plan_id={plan.plan_id} sha256={digest}")
        return 0
    sealed = out.with_name(P.SEALED_NAME)
    P.write_sealed(plan, sealed)
    print(f"sealed plan written: {sealed} runs={plan.header['n_runs']} plan_id={plan.plan_id}")
    if a.unseal_to:
        target = pathlib.Path(a.unseal_to).resolve()
        if target.is_relative_to(argv_mod.REPO_ROOT.resolve()):
            return _fail("--unseal-to must lie outside the repository")
        P.write_plan(plan, target, markdown=False)
        print(f"clear plan written outside the repo: {target}")
    return 0


def cmd_validate(a) -> int:
    """`validate`: check a plan file against the schema and its own hashes; 0 valid, 1 invalid, 2 unreadable."""
    path = pathlib.Path(a.plan)
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as e:
        return _fail(f"cannot read {path}: {e}")
    errs = P.validate_lines(lines)
    if errs:
        for e in errs[:30]:
            print(f"INVALID {e}", file=sys.stderr)
        return 1
    import json
    h = json.loads(lines[0])
    print(f"OK {'sealed ' if h['sealed'] else ''}plan_id={h['plan_id']} runs={h['n_runs']} "
          f"schema_version={h['schema_version']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point of `tsbench plan`; returns the exit code."""
    ap = argparse.ArgumentParser(prog="tsbench plan", description="Build and validate run plans.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="expand a selection to plan.jsonl (pilot) or plan.sealed.json (confirmatory)")
    b.add_argument("--split", required=True, choices=["pilot", "confirmatory"])
    b.add_argument("--models", required=True)
    b.add_argument("--conditions", required=True)
    b.add_argument("--effort", required=True, help="one effort or a comma list")
    b.add_argument("--k", required=True, type=int, help="last repetition (k layer) of the plan")
    b.add_argument("--k-from", type=int, default=None, dest="k_from",
                   help="first repetition (default 1): a stage of the staged design holds the layers k-from..k")
    b.add_argument("--stage", default=None, help="label of the stage, written into the plan's spec")
    b.add_argument("--budget-usd", required=True, type=float, dest="budget_usd")
    b.add_argument("--out-plan", required=True, dest="out_plan")
    b.add_argument("--limit", type=int, default=None)
    b.add_argument("--task-class", default=None, dest="task_class",
                   help="comma list: keep only the tasks of these classes (applied before --limit)")
    b.add_argument("--task-ids", default=None, dest="task_ids",
                   help="comma list of task ids: keep only these (applied after --task-class, before --limit)")
    b.add_argument("--gateway", action="store_true")
    b.add_argument("--b-venv", dest="b_venv", default=None, metavar="DIR",
                   help="venv of condition B whose digest the plan pins "
                        "(default: $TSBENCH_B_VENV or ~/.cache/tsbench/venv-B)")
    b.add_argument("--system-prompt-file", default=P.DEFAULT_SYSTEM_PROMPT, dest="system_prompt_file")
    b.add_argument("--i-have-preregistered", dest="preregistered", metavar="DOI", default=None)
    b.add_argument("--unseal-to", dest="unseal_to", default=None,
                   help="confirmatory only: also write the clear plan to this path outside the repo")
    b.set_defaults(fn=cmd_build)
    v = sub.add_parser("validate", help="check a plan against plan.schema.json and its own hashes")
    v.add_argument("plan")
    v.set_defaults(fn=cmd_validate)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":  # pragma: no cover - entry-point guard; the tests call main() directly
    raise SystemExit(main())
