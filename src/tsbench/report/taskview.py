"""What each pilot task asked, read from its task record, the literature tables and the scored runs: one block per
task class (definition, oracle, tolerance, tasks solved per condition) with one row per task (given, asked, reference,
source, tolerance, prompt and the answer of each condition).

    tasks_view(order, tasks, by_task, conds, oracle)   the blocks, in task-file order; facts.benchmark keeps them as
                                                       `bench["tasks_view"]`
    class_tolerance(tasks)                             the tolerance of a class as one line

A block is `{class, definition, n, oracle, tolerance, k, n_by, tasks}`; a row of `tasks` is `{id, anchor, class, given,
asked, reference, reference_more, source, tolerance, prompt, answers}`. Only pilot tasks are read.
"""
from __future__ import annotations

import collections
import re
from collections.abc import Callable, Collection, Sequence

from tsbench.report import literature, science
from tsbench.report.base import as_number, is_true
from tsbench.report.svg.base import fixed, round_half_up

__all__ = ["CLASS_DEFINITIONS", "class_tolerance", "run_anchor", "shown_run", "tasks_view"]

# One line per pilot task class, written from the tables "Task set" and "Oracle per class" of
# src/tsbench/data/tasks/rubric.md.
CLASS_DEFINITIONS: dict[str, str] = {
    "closed_form": "three synthetic bands of an Oh d3 or d8 ion; Dq and B from the closed-form relations",
    "experimental": "two or three published band maxima of an Oh d3 or d8 system; Dq and B from the closed form",
    "numerical": "three synthetic bands of an Oh d2 or d7 ion; Dq and B from the forward model",
    "numerical_hard": "three low-spin bands of an Oh d4 to d6 ion, C/B stated; Dq and B from the forward model",
    "racah_c": "three spin-allowed and one spin-forbidden band of an Oh d3 ion; Dq, B and C from the forward model",
    "tetrahedral": "three synthetic bands of a Td d7 or d8 ion; Dq and B from the forward model (hole formalism)",
    "out_of_scope": "charge-transfer or Jahn-Teller bands outside the ligand-field model; no Dq and B exist",
    "crossover": "B and C of an Oh d4 to d7 ion; Dq of its spin crossover from the forward model",
    "curve": "B, C and three Dq/B values of an Oh ion; E/B of the three lowest excited terms at each value",
    "literature_all": "published bands of an Oh or Td system; Dq and B (C if the bands fix it) by least squares",
    "batch": "B and C of an Oh ion; one result for each value of a series (spin crossover or first absorption band)",
    "pairing": "free-ion configurations d2, d4, d6, d8; LS terms with counts, ground terms and shared-term edges",
    "diagram": "B and C of an Oh ion; E/B of the lowest six levels at nine Dq/B values (a Tanabe–Sugano diagram)",
    "literature_new": "published bands of recent papers (pilot only); Dq, B and C from a least-squares fit",
}

# The oracle of a task record in words. The tanabesugano version is added where the package computes the reference.
ORACLE_TEXT = {"closed_form": "closed form (Underhill–Billing)", "forward_model": "forward model",
               "forward_model_lsq": "least-squares fit, forward model", "microstate_count": "microstate count",
               "none": "no Dq/B exists"}
_PACKAGE_ORACLES = ("forward_model", "forward_model_lsq")
FOLD_AFTER = 6  # a reference list with more items than this keeps the rest in `reference_more`
PAIRING_TOLERANCE = "exact nodes, edges and ground terms"
MUST_DECLINE = "must decline"
LITERATURE = science.LITERATURE
_NUMBER_WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six"}


# ---------------------------------------------------------------- small helpers


def _grouped(x: float, nd: int = 0) -> str:
    """A number with a narrow no-break space between the thousands: 13760 is `13 760`, never broken across lines."""
    return f"{round_half_up(x, nd):,.{nd}f}".replace(",", "\u202f")


def _plain(x: float) -> str:
    """A grid value or ratio as `4`, `1.05` or `3 488`."""
    return _grouped(x) if float(x).is_integer() and abs(x) >= 1000 else f"{x:g}"


def _list(values: Sequence[float]) -> str:
    return " · ".join(_plain(v) for v in values)


def _word(n: int) -> str:
    return _NUMBER_WORDS.get(n, str(n))


def _n_items(task: dict) -> int:
    """How many values an answer to a curve, diagram or batch task holds, from its reference."""
    ref, params = task.get("reference") or {}, task.get("params") or {}
    schema = task.get("answer_schema")
    if schema == "curve":
        return len(task.get("reference_curve") or [])
    if schema == "diagram":
        return len(ref.get("grid") or []) * int(params.get("n_levels") or 0)
    if schema == "batch":
        return len(ref.get("values") or [])
    return 0


# ---------------------------------------------------------------- tolerance


def task_tolerance(task: dict) -> str:
    """The tolerance of one task as its record states it: `Dq 2 %, B 5 %`; the numbers are read from the record."""
    tol, schema = task.get("tolerance") or {}, task.get("answer_schema")
    if task.get("expect_out_of_scope"):
        return MUST_DECLINE
    if schema == "curve":
        return f"{100 * tol['curve_rel']:g} % or {tol['curve_abs']:g} E/B, all {_n_items(task)}"
    if schema == "diagram":
        return (f"{100 * tol['curve_rel']:g} % or {tol['curve_abs']:g} E/B, "
                f"at least {100 * tol['item_accuracy_min']:g} % of {_n_items(task)}")
    if schema == "batch":
        return f"{100 * tol['item_rel']:g} % per item, all {_n_items(task)}"
    if schema == "pairing":
        return PAIRING_TOLERANCE
    return ", ".join(f"{p} {100 * tol[p]:g} %" for p in task.get("required") or () if tol.get(p)) or "none"


def class_tolerance(tasks: Sequence[dict]) -> str:
    """The tolerance of a class: the one line of its tasks where they agree, else the ranges of the tasks' records
    (`science.tolerance_text`)."""
    if all(t.get("expect_out_of_scope") for t in tasks):
        return MUST_DECLINE
    if tasks[0].get("answer_schema") == "pairing":
        return PAIRING_TOLERANCE
    return science.tolerance_text(list(tasks))


# ---------------------------------------------------------------- given, asked, reference


def _given(task: dict) -> list[tuple[str, str]]:
    """The facts the prompt hands over: bands, ion, system and the parameters of the record."""
    out: list[tuple[str, str]] = []
    params = task.get("params") or {}
    if task.get("bands_cm1"):
        out.append(("Bands", _list(task["bands_cm1"]) + " cm⁻¹"))
    if task.get("d_count") is not None:
        out.append(("Ion", f"d{task['d_count']} {task.get('geometry') or ''}".strip()))
    if task.get("system"):
        out.append(("System", str(task["system"])))
    for key, label, unit in (("B", "B", " cm⁻¹"), ("C", "C", " cm⁻¹"), ("c_over_b", "C/B", "")):
        if params.get(key) is not None:
            out.append((label, _plain(params[key]) + unit))
    for key, label in (("C_over_B", "C/B"), ("dq_over_b", "Dq/B")):
        if params.get(key):
            out.append((label, _list(params[key])))
    if params.get("configs"):
        out.append(("Configurations", " · ".join(params["configs"])))
    if params.get("mode"):
        out.append(("Mode", str(params["mode"])))
    if params.get("n_levels"):
        out.append(("Levels", str(params["n_levels"])))
    if task.get("class") in LITERATURE and params.get("labels"):
        out.append(("Band assignment", " · ".join(params["labels"])))
    return out


def _asked(task: dict) -> str:
    params, schema = task.get("params") or {}, task.get("answer_schema")
    if task.get("expect_out_of_scope"):
        return "decline: the ligand-field model does not apply"
    if schema == "curve":
        n = len(params.get("dq_over_b") or [])
        per = _n_items(task) // n if n else 0
        return f"E/B of the {_word(per)} lowest excited terms at {_word(n)} Dq/B values ({_n_items(task)} values)"
    if schema == "diagram":
        n = int(params.get("n_levels") or 0)
        return (f"E/B of the lowest {n} levels at {len(params.get('dq_over_b') or [])} Dq/B values "
                f"({_n_items(task)} values)")
    if schema == "batch":
        what = "Dq of the spin crossover" if task.get("subtype") == "crossover_series" \
            else "energy of the first spin-allowed band"
        by = "C/B" if task.get("subtype") == "crossover_series" else "Dq"
        return f"{what} for {_n_items(task)} {by} values"
    if schema == "pairing":
        return "LS terms with counts, ground terms, shared-term edges"
    return ", ".join(task.get("required") or ())


def _folded(items: list[tuple[str, str]]) -> tuple[list[tuple[str, str]], list[str] | None]:
    """The first items as they are, the rest as `label: text` lines (None when nothing is left)."""
    rest = [f"{label}: {text}" for label, text in items[FOLD_AFTER:]]
    return items[:FOLD_AFTER], rest or None


def _reference(task: dict) -> tuple[list[tuple[str, str]], list[str] | None]:
    ref, schema = task.get("reference") or {}, task.get("answer_schema")
    items: list[tuple[str, str]] = []
    if task.get("expect_out_of_scope"):
        items = [("Answer", "decline")]
    elif schema == "curve":
        by_x: dict[float, list[float]] = collections.defaultdict(list)
        for p in task.get("reference_curve") or []:
            by_x[p["dq_over_b"]].append(p["e_over_b"])
        items = [(f"Dq/B {x:g}", " · ".join(fixed(e, 2) for e in es)) for x, es in by_x.items()]
    elif schema == "diagram":
        items = [(f"Dq/B {x:g}", " · ".join(f"{e:g}" for e in row))
                 for x, row in zip(ref.get("grid") or [], ref.get("levels") or [], strict=False)]
    elif schema == "batch":
        by = "C/B" if task.get("subtype") == "crossover_series" else "Dq"
        items = [(f"{by} {_plain(v['input'])}", _grouped(v["result"])) for v in ref.get("values") or []
                 if v.get("result") is not None]
    elif schema == "pairing":
        terms: dict[str, list[str]] = collections.defaultdict(list)
        ground: dict[str, str] = {}
        for n in ref.get("nodes") or []:
            terms[n["config"]].append(n["term"] + (f"×{n['count']}" if n["count"] > 1 else ""))
            if n.get("ground"):
                ground[n["config"]] = n["term"]
        items = [(cfg, " ".join(ts) + f" · ground {ground.get(cfg, '–')}") for cfg, ts in terms.items()]
        items.append(("Edges", f"{len(ref.get('edges') or [])} shared terms"))
    else:
        items = [(p, _grouped(ref[p])) for p in task.get("required") or () if ref.get(p) is not None]
    return _folded(items)


# ---------------------------------------------------------------- source


def _source(task: dict, table: dict, oracle: str | None) -> dict:
    """Where the reference comes from: the paper of a literature task (text, DOI, table locator), else the oracle."""
    if task.get("class") in LITERATURE:
        return literature.source_parts(table.get(literature._norm_name(task.get("system") or "")))
    name = task.get("oracle") or "none"
    text = ORACLE_TEXT.get(name, name)
    if oracle and name in _PACKAGE_ORACLES:
        text += f" · tanabesugano {oracle}"
    return {"text": text, "doi": None, "locator": None}


# ---------------------------------------------------------------- answers


def _k(r: dict) -> int:
    x = as_number(r.get("k_index"))
    return int(x) if x is not None else 1


def shown_run(rs: list[dict]) -> dict:
    """The run that stands for a cell of k runs: the first run (lowest k) on the side of the verdict, a correct one when
    most runs are correct, else a wrong one. The cell shows the answer of this one run, never a mix or an average of
    runs. `rs` holds at least one run."""
    ordered = sorted(rs, key=_k)
    ok = science._solved(ordered)
    return next(r for r in ordered if is_true(r.get("correct")) == ok)


def run_anchor(model: str, cond: str, effort: str, task: str, k: int | str) -> str:
    """The html id of the gallery card of one run (the gallery adds a suffix only when two cards share all five)."""
    return "run-" + re.sub(r"[^A-Za-z0-9_-]", "-", f"{model}-{cond}-{effort}-{task}-k{k}")


def _answer_text(task: dict, r: dict) -> str:
    """What one run answered, in the measure of the task's class."""
    schema = task.get("answer_schema")
    if task.get("expect_out_of_scope"):
        return "declined" if is_true(r.get("answer_out_of_scope")) else "answered"
    if schema == "curve":
        e = as_number(r.get("curve_max_rel_err"))
        return "no answer" if e is None else f"max rel. error {fixed(100 * e, 1)} %"
    if schema in ("diagram", "batch"):
        k = as_number(r.get("n_correct_items"))
        return "no answer" if k is None else f"{round_half_up(k)} of {_n_items(task)} within"
    if schema == "pairing":
        f1 = as_number(r.get("edge_f1"))
        if f1 is None:
            return "no answer"
        return f"edge F1 {fixed(f1, 2)} · ground {'✓' if is_true(r.get('ground_correct')) else '✗'}"
    parts = [f"{p} {_grouped(v)}" for p in task.get("required") or ()
             if (v := as_number(r.get(p.lower()))) is not None]
    return " · ".join(parts) or "no answer"


def _answers(task: dict, by_task: dict, conds: Sequence[str], label_of: Callable[[str | None], str]) -> dict:
    """Per condition the answer of the run `shown_run` picks (`shown_k` is its repetition index), the verdict of all
    runs (`ok`, `n_correct` of `n_runs`), the report category of the runs on the side of the verdict and the html id of
    the gallery card of the shown run (`run_anchor`)."""
    out = {}
    for c in conds:
        rs = sorted(by_task.get((c, task["id"]), []), key=_k)
        if not rs:
            continue
        ok = science._solved(rs)
        shown = shown_run(rs)
        # the category names the runs on the side of the verdict: the wrong runs of a task that is not solved
        side = [r for r in rs if is_true(r.get("correct")) == ok]
        labels = collections.Counter(label_of(r.get("_category")) for r in side)
        out[c] = {"text": _answer_text(task, shown), "ok": ok, "category": labels.most_common(1)[0][0],
                  "n_runs": len(rs), "n_correct": sum(is_true(r.get("correct")) for r in rs), "shown_k": _k(shown),
                  "run_anchor": run_anchor(str(shown.get("model", "")), c, str(shown.get("effort", "")), task["id"],
                                           _k(shown))}
    return out


# ---------------------------------------------------------------- the blocks


def tasks_view(order: Sequence[str], tasks: dict[str, dict], by_task: dict[tuple[str, str], list[dict]],
               conds: Sequence[str], oracle: str | None,
               label_of: Callable[[str | None], str] = lambda category: str(category),
               ran: Collection[str] | None = None) -> list[dict]:
    """One block per class in task-file order:
    `{"class", "definition", "n", "oracle", "tolerance", "k", "n_by", "tasks"}`.
    `n` counts the tasks of `ran` (default all of `order`: the tasks the model ran; the other tasks keep their row,
    without answers), `n_by` per condition the tasks with an evaluable run, `k` those it solves.
    `by_task` maps (condition, task id) to the evaluable scored runs of the chosen model; `oracle` is the
    tanabesugano version of the manifests (None when no manifest records it); `label_of` turns the taxonomy category
    of a run into the label of the report category."""
    table = literature.read_csv_rows()
    blocks: dict[str, dict] = {}
    for t in order:
        task = tasks[t]
        cls = task["class"]
        block = blocks.setdefault(cls, {"class": cls, "definition": CLASS_DEFINITIONS.get(cls, ""), "n": 0,
                                        "oracle": ORACLE_TEXT.get(task.get("oracle") or "none", ""), "tolerance": "",
                                        "k": dict.fromkeys(conds, 0), "n_by": dict.fromkeys(conds, 0),
                                        "tasks": [], "_records": []})
        reference, more = _reference(task)
        answers = _answers(task, by_task, conds, label_of)
        block["tasks"].append({
            "id": t, "anchor": "task-" + t, "class": cls, "given": _given(task), "asked": _asked(task),
            "reference": reference, "reference_more": more, "source": _source(task, table, oracle),
            "tolerance": task_tolerance(task), "prompt": task.get("prompt") or "", "answers": answers})
        block["_records"].append(task)
        block["n"] += ran is None or t in ran
        for c, a in answers.items():
            block["k"][c] += a["ok"]
            block["n_by"][c] += 1
    for block in blocks.values():
        block["tolerance"] = class_tolerance(block.pop("_records"))
    return list(blocks.values())
