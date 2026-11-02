"""The run plan: one frozen JSONL file that says exactly what the runner will execute (docs/methods.md, section 4).

    tsbench plan build --split pilot --models M --conditions A,B,C --effort medium --k 1 \\
        --budget-usd 5 --out-plan runs/x/plan.jsonl
    tsbench plan validate runs/x/plan.jsonl

Line 1 is a header (`"kind":"header"`), every further line one run (`"kind":"run"`) with the full prompt and
system prompt embedded. `plan_id` is the sha256 of the canonical run lines in run_id order, so it does not
depend on file order, timestamps or pins. A confirmatory plan is sealed by default: only a header with counts
and the `plan_id` is written (`plan.sealed.json`), never a prompt.

No model calls happen here. The only validator is the small one below (jsonschema is not a dependency).
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import pathlib
from collections import Counter

from tsbench.core import resource
from tsbench.core.prereg import is_doi
from tsbench.core.schema import validate_instance  # noqa: F401  (re-exported: plan validation and tests use it)
from tsbench.core.util import write_text_atomic
from tsbench.plan.pins import (  # noqa: F401  (re-exported: the runner and the tests use them)
    _git_commit,
    answer_schema_sha256,
    answer_schema_sha256s,
    check_pins,
    claude_version_probe,
    live_pins,
)

HERE = pathlib.Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]  # src/tsbench/plan -> root
SCHEMA_PATH = resource("schemas/plan.schema.json")
SCHEMA_VERSION = 4
# What each schema version holds; plans of versions 2 to 4 load.
# 4: pins.b_stack_sha256 and, on B runs, b_stack_sha256 (the fixed B stack)
# 3: runs carry answer_schema + answer_schema_sha256, pins.answer_schemas
# 2: answer_format is an object (enforced via --json-schema), pins.answer_schema_sha256
ANSWER_FORMATS = {"fit": "contract_answer_v1", "curve": "contract_curve_v1", "batch": "contract_batch_v1",
                  "pairing": "contract_pairing_v1", "diagram": "contract_diagram_v1"}
DEFAULT_SYSTEM_PROMPT = "prompts/neutral.txt"  # a resource id (tsbench.core.resource), never a path
SEALED_NAME = "plan.sealed.json"
PLAN_NAME = "plan.jsonl"

__all__ = ["PlanError", "Plan", "b_stack_digest", "build_from_spec", "build_plan", "canonical", "check_pins",
           "live_pins", "load_plan", "plan_id_of", "render_markdown", "require_preregistration", "serialize",
           "spec_from_flags", "validate_instance", "validate_lines", "write_plan", "write_sealed",
           "write_text_atomic"]


class PlanError(ValueError):
    """The plan (or a request to build one) is invalid."""


# ------------------------------------------------------------------ hashing
def canonical(obj) -> str:
    """Same serialisation as `tsbench.tasks.generate.canonical` (not imported: that module needs numpy/scipy)."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def plan_id_of(runs: list[dict]) -> str:
    """sha256 over the canonical run lines, in run_id order."""
    body = "".join(canonical(r) + "\n" for r in sorted(runs, key=lambda r: r["run_id"]))
    return sha256_text(body)


def tasks_subset_sha256(split: str) -> str | None:
    """The `pilot` / `confirmatory` line of tasks.sha256 (None if the file does not have it)."""
    from tsbench.tasks import HASH_PATH
    for line in HASH_PATH.read_text(encoding="utf-8").splitlines():
        digest, _, name = line.partition("  ")
        if name == split:
            return digest
    return None


# ------------------------------------------------------------------ a tiny JSON Schema validator
def load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def task_answer_schema(task: dict) -> str:
    """The answer schema of a task record; records without the field are `fit`."""
    return task.get("answer_schema") or "fit"


def answer_format(schema: str = "fit") -> dict:
    from tsbench import conditions
    return {"name": ANSWER_FORMATS[schema], "enforced": "json-schema",
            "schema_sha256": conditions.get_answer_schema(schema).sha256}


def system_prompt_for(spec_file: str, schema: str) -> str:
    """The system-prompt file for a schema: the spec's own for `fit`, else its sibling `<stem>_<schema>.txt`
    (its last paragraph names that schema's answer, which the `fit` one cannot)."""
    if schema == "fit":
        return spec_file
    path = pathlib.Path(spec_file)
    sibling = str(path.with_name(f"{path.stem}_{schema}{path.suffix}"))
    try:
        found = resource(sibling).is_file()
    except FileNotFoundError:
        found = False
    if not found:
        raise PlanError(f"system prompt file {sibling} for answer schema {schema!r} not found")
    return sibling


def tools_expected(cond_key: str) -> dict:
    """What `conditions.check_init` demands per condition, as data (`conditions.tools_expected`, the one statement of
    the rule). The plan stores it per run; the runner checks the stored record still equals it."""
    from tsbench import conditions
    try:
        return conditions.tools_expected(cond_key)
    except ValueError:
        raise PlanError(f"unknown condition {cond_key!r}") from None


EXPECTED_FLAGS = {"A": [], "B": ["b_no_tool_use"], "C": ["c_no_mcp_call"]}


def argv_template(cond_key: str, model: str, effort: str, max_turns: int, schema: str = "fit",
                  disallowed: list[str] | tuple[str, ...] = ()) -> list[str]:
    """`argv_mod.build_argv` with the per-machine parts as placeholders; the prompt is on stdin and not in it.
    There is no per-call cap in it (no `--max-budget-usd`): only `runner --per-call-usd X` adds one."""
    from tsbench import conditions
    from tsbench.conditions import argv as argv_mod
    return argv_mod.build_argv(["{CLAUDE}"], conditions.get(cond_key), model, effort, None,
                             system_prompt_file="{SYSTEM_PROMPT_FILE}", settings_path="{SETTINGS}",
                             mcp_config_path="{MCP_CONFIG}", max_turns=max_turns, answer_schema=schema,
                             disallowed_tools=disallowed)


class Plan:
    """Header, run records in execution order, and the exact text that is (or would be) the file."""

    def __init__(self, header: dict, runs: list[dict], raw: str | None = None):
        self.header, self.runs, self.raw = header, runs, raw  # raw: the file's own text when loaded from disk

    @property
    def plan_id(self) -> str:
        return self.header["plan_id"]

    def text(self) -> str:
        return self.raw if self.raw is not None else serialize(self.header, self.runs)

    @property
    def sha256(self) -> str:
        return sha256_text(self.text())

    def sealed_header(self) -> dict:
        return {**self.header, "sealed": True}


def serialize(header: dict, runs: list[dict]) -> str:
    """The plan file text: the header line, then one run record per line, each in canonical JSON."""
    return "".join(canonical(rec) + "\n" for rec in [header, *runs])


def build_plan(tasks: list[dict], spec: dict, *, pins: dict | None = None, created_utc: str | None = None,
               git_commit: str | None = None, tasks_sha256: str | None = None) -> Plan:
    """Expand the spec to the cross product. Order: k, task (file order), model, effort, condition, so a run stopped
    by the budget leaves a balanced partial matrix. The optional `k_from` (default 1) starts the repetitions there: a
    stage plan of the staged design holds the layers k_from..k only; the optional `stage` is a label."""
    from tsbench import conditions
    from tsbench.conditions import argv as argv_mod
    for key in ("split", "models", "conditions", "efforts", "k", "budget_usd"):
        if key not in spec:
            raise PlanError(f"spec lacks {key!r}")
    spec = {"limit": None, "system_prompt_file": DEFAULT_SYSTEM_PROMPT, "gateway": False, **spec}
    if not tasks:
        raise PlanError("no tasks")
    if len(set(spec["models"])) != len(spec["models"]) or not spec["models"]:
        raise PlanError("models must be non-empty and without duplicates")
    for m in spec["models"]:
        why = argv_mod.validate_model_id(m, spec["gateway"])
        if why:
            raise PlanError(why)
    for c in spec["conditions"]:
        try:
            conditions.get(c)
        except ValueError as e:
            raise PlanError(str(e)) from None
    if not spec["conditions"] or len(set(spec["conditions"])) != len(spec["conditions"]):
        raise PlanError("conditions must be non-empty and without duplicates")
    for e in spec["efforts"]:
        if e not in argv_mod.EFFORTS:
            raise PlanError(f"effort {e!r} not in {argv_mod.EFFORTS}")
    if spec["k"] < 1 or spec["budget_usd"] <= 0:
        raise PlanError("k must be >= 1 and budget_usd > 0")
    k_from = spec.get("k_from", 1)
    if not isinstance(k_from, int) or not 1 <= k_from <= spec["k"]:
        raise PlanError(f"k_from must be an integer in 1..k, got {k_from!r}")
    sp_cache: dict[str, tuple[str, str]] = {}  # file -> (text, sha256)

    def system_prompt(schema: str) -> tuple[str, str, str]:
        rel = system_prompt_for(spec["system_prompt_file"], schema)
        if rel not in sp_cache:
            try:
                text = resource(rel).read_text(encoding="utf-8")  # rel is a resource id (tsbench.core)
            except (FileNotFoundError, IsADirectoryError) as e:
                raise PlanError(f"system prompt file {rel} not found") from e
            sp_cache[rel] = (text, sha256_text(text))
        return rel, *sp_cache[rel]

    for t in tasks:
        schema = task_answer_schema(t)
        if schema not in ANSWER_FORMATS:
            raise PlanError(f"{t['id']}: unknown answer schema {schema!r}")
        system_prompt(schema)

    b_digest = (pins or {}).get("b_stack_sha256")
    runs: list[dict] = []
    for i in range(k_from, spec["k"] + 1):
        for t in tasks:
            for m in spec["models"]:
                for e in spec["efforts"]:
                    for c in spec["conditions"]:
                        schema = task_answer_schema(t)
                        sp_rel, sp_text, sp_sha = system_prompt(schema)
                        turns = conditions.max_turns(c)
                        blocked = conditions.disallowed_tools(c, m, bool(spec["gateway"]))
                        runs.append({
                            "kind": "run",
                            "run_id": argv_mod.run_id_of(m, c, e, t["id"], i),
                            "task_id": t["id"], "task_class": t["class"], "split": t["split"],
                            "task_sha256": sha256_text(canonical(t)),
                            "prompt": t["prompt"], "prompt_sha256": sha256_text(t["prompt"]),
                            "system_prompt_file": sp_rel,
                            "system_prompt_sha256": sp_sha, "system_prompt_text": sp_text,
                            "model": m, "effort": e, "condition": c, "k": i, "max_turns": turns,
                            "tools_expected": tools_expected(c),
                            "argv_template": argv_template(c, m, e, turns, schema, blocked),
                            "disallowed_tools": blocked,
                            "expected_flags": list(EXPECTED_FLAGS[c]),
                            "answer_schema": schema,
                            "answer_schema_sha256": conditions.get_answer_schema(schema).sha256,
                            "answer_format": answer_format(schema),
                        })
                        if c == "B" and b_digest:
                            runs[-1]["b_stack_sha256"] = b_digest
    ids = [r["run_id"] for r in runs]
    if len(set(ids)) != len(ids):
        raise PlanError("duplicate run_id (duplicate task ids?)")
    header = {
        "kind": "header", "schema_version": SCHEMA_VERSION, "plan_id": plan_id_of(runs),
        "created_utc": created_utc or dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        "spec": spec,
        "tasks_sha256": tasks_sha256 if tasks_sha256 is not None else tasks_subset_sha256(spec["split"]),
        "generator_git_commit": git_commit if git_commit is not None else _git_commit(),
        "pins": pins if pins is not None else live_pins(None),
        "sealed": False, "n_runs": len(runs), "budget_usd_total": float(spec["budget_usd"]),
        "per_call_cap": None,  # no --max-budget-usd per call; budget_usd_total only stops the STARTING of runs
        "counts": {"by_condition": dict(sorted(Counter(r["condition"] for r in runs).items())),
                   "by_class": dict(sorted(Counter(r["task_class"] for r in runs).items())),
                   "by_model": dict(sorted(Counter(r["model"] for r in runs).items())),
                   "by_effort": dict(sorted(Counter(r["effort"] for r in runs).items()))},
    }
    plan = Plan(header, runs)
    problems = validate_lines([canonical(header)] + [canonical(r) for r in runs])
    if problems:
        raise PlanError("built plan fails its own schema: " + "; ".join(problems[:5]))
    return plan


# ------------------------------------------------------------------ building from the flags of a CLI
# `tsbench plan build` and the flags form of `tsbench run` both go through these four functions, so a flag is checked
# in one place and one message.
def require_preregistration(split: str, doi: str | None) -> None:
    """A confirmatory split needs the DOI of the deposited preregistration. Raises PlanError."""
    if split == "confirmatory" and not is_doi(doi):
        raise PlanError("--split confirmatory needs --i-have-preregistered <DOI> (the preregistration must be "
                        "deposited before any model sees the confirmatory tasks)")


def _flag_list(text: str, flag: str, *, upper: bool = False) -> list[str]:
    items = [i.strip().upper() if upper else i.strip() for i in text.split(",") if i.strip()]
    if not items or len(set(items)) != len(items):
        raise PlanError(f"{flag} must be a non-empty list without duplicates")
    return items


def spec_from_flags(*, split: str, models: str, conditions: str, efforts: str, k: int, budget_usd: float,
                    limit: int | None = None, system_prompt_file: str = DEFAULT_SYSTEM_PROMPT,
                    gateway: bool = False, k_from: int | None = None, stage: str | None = None) -> dict:
    """The spec of a plan from the text of the CLI flags (`models`, `conditions` and `efforts` are comma lists),
    checked flag by flag. Raises PlanError naming the flag. Reads nothing: no task, no environment."""
    from tsbench import conditions as cond_mod
    from tsbench.conditions import argv as argv_mod
    model_ids = _flag_list(models, "--models")
    for m in model_ids:
        why = argv_mod.validate_model_id(m, gateway)
        if why:
            raise PlanError(why)
    cond_keys = _flag_list(conditions, "--conditions", upper=True)
    for c in cond_keys:
        try:
            cond_mod.get(c)
        except ValueError as e:
            raise PlanError(str(e)) from None
    effort_names = _flag_list(efforts, "--effort")
    if k < 1:
        raise PlanError("--k must be >= 1")
    if limit is not None and limit < 1:
        raise PlanError("--limit must be >= 1")
    if budget_usd <= 0:
        raise PlanError("--budget-usd must be > 0")
    spec = {"split": split, "models": model_ids, "conditions": cond_keys, "efforts": effort_names, "k": k,
            "budget_usd": float(budget_usd), "limit": limit, "system_prompt_file": system_prompt_file,
            "gateway": bool(gateway)}
    if k_from is not None:
        spec["k_from"] = k_from
    if stage:
        spec["stage"] = stage
    return spec


def b_stack_digest(conds: list[str], split: str, b_venv: str | None, warn=None) -> str | None:
    """The digest of the fixed B stack to pin, or None when B is not requested. A confirmatory plan needs a valid stack
    (PlanError); a pilot plan goes on without the pin and says so through `warn`. Raises `b_stack.BStackError` when the
    venv lies inside the repo."""
    from tsbench.conditions import b_stack
    if "B" not in conds:
        return None
    digest = b_stack.digest_if_present(b_stack.b_venv_dir(None, b_venv))
    if digest is None:
        if split == "confirmatory":
            raise PlanError("condition B needs the fixed B stack: run `tsbench env b-stack` first")
        if warn is not None:
            warn("the B stack is not built or not valid; the plan does not pin it (run `tsbench env b-stack`)")
    return digest


def build_from_spec(spec: dict, *, b_venv: str | None, claude_cli_version: str | None, task_classes=(), task_ids=(),
                    warn=None) -> Plan:
    """Select the tasks of the spec, pin the environment and expand the plan. `task_classes` and `task_ids` narrow the
    split before `spec["limit"]` is applied. Raises PlanError, or `b_stack.BStackError` for a bad `b_venv`."""
    from tsbench.tasks import load
    digest = b_stack_digest(spec["conditions"], spec["split"], b_venv, warn)  # before any task is read
    tasks = load(spec["split"])
    if task_classes:
        tasks = [t for t in tasks if t["class"] in task_classes]
    if task_ids:
        known = {t["id"] for t in tasks}
        if sorted(set(task_ids) - known):
            raise PlanError(f"unknown task id(s) in this selection: {', '.join(sorted(set(task_ids) - known))}")
        tasks = [t for t in tasks if t["id"] in task_ids]
    if (task_classes or task_ids) and not tasks:
        raise PlanError("the --task-class / --task-ids selection is empty")
    if spec.get("limit") is not None:
        tasks = tasks[: spec["limit"]]
    if not tasks:
        raise PlanError(f"no tasks in split {spec['split']!r}")
    pins = live_pins(claude_cli_version, b_stack_sha256=digest, b_venv=b_venv)
    return build_plan(tasks, spec, pins=pins)


# ------------------------------------------------------------------ validating and loading
def validate_lines(lines: list[str], *, require_runs: bool = True) -> list[str]:
    """Schema errors of a plan given as lines, plus the cross-record checks. Empty list = valid."""
    schema = load_schema()
    errs: list[str] = []
    records = []
    for n, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError as e:
            errs.append(f"line {n}: not JSON ({e.msg})")
            continue
        records.append((n, rec))
        errs += [f"line {n}: {m}" for m in validate_instance(schema, rec)]
    if errs:
        return errs
    if not records or records[0][1].get("kind") != "header":
        return ["line 1 must be the header record"]
    header = records[0][1]
    runs = [r for _, r in records[1:]]
    if any(r.get("kind") != "run" for r in runs):
        errs.append("only the first line may be a header")
    if header["sealed"]:
        if runs:
            errs.append("a sealed plan must not carry run records")
        return errs
    if not runs and require_runs:
        errs.append("plan has no run records")
    if header["n_runs"] != len(runs):
        errs.append(f"header n_runs={header['n_runs']} but {len(runs)} run records")
    ids = [r["run_id"] for r in runs]
    if len(set(ids)) != len(ids):
        errs.append("duplicate run_id")
    header_split = header["spec"]["split"]
    for r in runs:
        if r["split"] != header_split:
            errs.append(f"{r['run_id']}: split {r['split']!r} but the header spec.split is {header_split!r}")
        if r["prompt_sha256"] != sha256_text(r["prompt"]):
            errs.append(f"{r['run_id']}: prompt_sha256 does not match the prompt")
        if r["system_prompt_sha256"] != sha256_text(r["system_prompt_text"]):
            errs.append(f"{r['run_id']}: system_prompt_sha256 does not match the system prompt text")
        pinned = (header["pins"].get("answer_schemas") or {}).get(r.get("answer_schema") or "fit")
        if "answer_schema" in r and pinned is not None and r.get("answer_schema_sha256") != pinned:
            errs.append(f"{r['run_id']}: answer_schema_sha256 differs from the header pin for {r['answer_schema']!r}")
        if "answer_schema" in r and r["answer_format"]["schema_sha256"] != r.get("answer_schema_sha256"):
            errs.append(f"{r['run_id']}: answer_format.schema_sha256 differs from answer_schema_sha256")
        b_pin = header["pins"].get("b_stack_sha256")
        if r["condition"] == "B" and b_pin and r.get("b_stack_sha256") != b_pin:
            errs.append(f"{r['run_id']}: b_stack_sha256 differs from the header pin")
        if r["condition"] != "B" and "b_stack_sha256" in r:
            errs.append(f"{r['run_id']}: only condition B runs carry b_stack_sha256")
        want = f"{r['model']}/{r['condition']}/{r['effort']}/{r['task_id']}-k{r['k']}"
        if r["run_id"] != want:
            errs.append(f"{r['run_id']}: run_id should be {want}")
    if not errs and plan_id_of(runs) != header["plan_id"]:
        errs.append("header plan_id does not match the run records (edited after building?)")
    return errs


def load_plan(path) -> Plan:
    """Read, validate and return a plan; PlanError with the reasons otherwise. A sealed header loads with no runs."""
    path = pathlib.Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        raise PlanError(f"cannot read {path}: {e}") from e
    lines = text.splitlines()
    errs = validate_lines(lines)
    if errs:
        raise PlanError(f"{path} is not a valid plan: " + "; ".join(errs[:6]) + (" ..." if len(errs) > 6 else ""))
    records = [json.loads(ln) for ln in lines if ln.strip()]
    return Plan(records[0], records[1:], raw=text)


# ------------------------------------------------------------------ writing
def write_plan(plan: Plan, path, *, markdown: bool = True) -> str:
    """plan.jsonl, plan.sha256 and (optionally) plan.md next to it. Returns the file's sha256."""
    path = pathlib.Path(path)
    text = plan.text()
    write_text_atomic(path, text)
    digest = sha256_text(text)
    write_text_atomic(path.with_name("plan.sha256"), f"{digest}  {path.name}\n")
    if markdown:
        write_text_atomic(path.with_name("plan.md"), render_markdown(plan))
    return digest


def write_sealed(plan: Plan, path) -> str:
    """Header only: plan_id, counts, tasks hash, spec. No prompt, no task id, no run record."""
    path = pathlib.Path(path)
    text = canonical(plan.sealed_header()) + "\n"
    write_text_atomic(path, text)
    return sha256_text(text)


def render_markdown(plan: Plan) -> str:
    """plan.md: the matrix, and each distinct prompt and system prompt once (pilot plans only)."""
    h, runs = plan.header, plan.runs
    spec = h["spec"]
    out = [f"# Run plan `{h['plan_id'][:16]}`", "",
           f"- split: {spec['split']}, runs: {h['n_runs']}, budget: USD {h['budget_usd_total']}",
           f"- models: {', '.join(spec['models'])}",
           f"- conditions: {', '.join(spec['conditions'])}; efforts: {', '.join(spec['efforts'])}; k = {spec['k']}",
           f"- tasks sha256 ({spec['split']}): `{h['tasks_sha256']}`",
           "- pins: " + ", ".join(f"{k}={v}" for k, v in h["pins"].items() if k in ("claude_cli_version",
                                                                                      "tanabesugano", "python")),
           "", "## Runs per cell", "", "| condition | runs |", "|---|---|"]
    out += [f"| {c} | {n} |" for c, n in h["counts"]["by_condition"].items()]
    out += ["", "## System prompts", ""]
    seen_sp: dict[str, str] = {}
    for r in runs:
        seen_sp.setdefault(r["system_prompt_sha256"], r["system_prompt_text"])
    for sha, txt in seen_sp.items():
        out += [f"`{sha[:12]}`", "", "```text", txt.rstrip("\n"), "```", ""]
    out += ["## Prompts (each once)", ""]
    seen_p: set[str] = set()
    for r in runs:
        if r["task_id"] in seen_p:
            continue
        seen_p.add(r["task_id"])
        out += [f"### {r['task_id']} ({r['task_class']})", "", "```text", r["prompt"].rstrip("\n"), "```", ""]
    return "\n".join(out)
