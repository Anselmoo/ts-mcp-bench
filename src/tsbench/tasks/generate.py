"""Deterministic generator for the benchmark task set, version 2 (docs/methods.md section 1, rubric.md).

    tsbench tasks generate [--out DIR]

Writes tasks.jsonl, tasks.sha256 and rubric.md. Seed: 20261025. The pilot systems in `common.FIXED_PILOT_SYSTEMS`
(drawn with seed 20261024) are kept by name and never become confirmatory. Every reference is computed:
  * closed_form / experimental: tsbench.tasks.oracles.closed_form (written independently of the package)
  * numerical / numerical_hard / racah_c / tetrahedral: the tanabesugano 2.0.0 forward model, i.e. the reference
    is the parameter set that generated the bands. Bands are rounded to 10 cm-1 and each task is rejected unless
    the answer survives the rounding well inside the tolerance (numerical_hard: unless a global multi-start fit
    of the rounded bands finds no other solution).
  * crossover: tanabesugano `crossover_dq` on the printed B and C.
  * curve: tanabesugano `compute_point` at the printed B, C and Dq/B, the ground level subtracted.
Reference values are never read from the Dq/B columns of the literature table.

The classes `literature_all`, `batch` and `pairing` (code in src/tsbench/tasks/classes/) have their own random streams
and come after the nine classes of `BASE_CLASSES` in `CLASSES` and in the file.
  * literature_all: forward-model least-squares fit (Dq, B[, C]) of the band energies of every usable table system.
  * batch: eight calculations per task (crossover series, band series), `tanabesugano` forward model.
  * pairing: free-ion LS terms of d^n and the shared term labels, independent microstate count.
The classes `diagram` (a whole Tanabe-Sugano diagram as data) and `literature_new` (pilot only) are written after
every other record (`TAIL_CLASSES`).
  * diagram: `compute_point` at nine Dq/B values, the lowest six levels (see src/tsbench/tasks/classes/diagram.py).
  * literature_new: the `literature_all` fit on the second literature table (literature-spectra-2.csv).

Output of this module is limited to counts and hashes; it never prints task contents.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
import tempfile
from collections import Counter

import numpy as np

from tsbench.core import resource
from tsbench.tasks.classes.closed_form import make_closed_form
from tsbench.tasks.classes.crossover import make_crossover
from tsbench.tasks.classes.curve import CURVE_GAP_34, CURVE_MIN_E1, CURVE_X_TO_CROSSOVER, make_curve
from tsbench.tasks.classes.experimental import make_experimental
from tsbench.tasks.classes.numerical import make_numerical
from tsbench.tasks.classes.numerical_hard import (
    HARD_MIN_SPACING,
    HARD_RESIDUAL,
    make_hard,
)
from tsbench.tasks.classes.out_of_scope import CT_TEMPLATES, JT_TEMPLATES, make_charge_transfer, make_jahn_teller
from tsbench.tasks.classes.racah_c import make_racah_c
from tsbench.tasks.classes.tetrahedral import make_tetrahedral
from tsbench.tasks.common import (
    BASE_CLASSES,
    CLASSES,
    CONF_DROPPED,
    COUNTS,
    EXTRA_CLASSES,
    FIXED_PILOT_SYSTEMS,
    N_CONF,
    N_PILOT,
    TAIL_CLASSES,
    Stats,
    _fixed_pilot_systems,
    _overlap_with_fixed_pilot,
)

SEED = 20261025
TASK_DATA = resource("tasks")  # tasks.jsonl, tasks.sha256, rubric.md


# ----------------------------------------------------------------------------- assembly


def build_tasks(stats: Stats):
    """Return (pilot, confirmatory): dict class -> list of records, in per-class order."""
    pilot: dict[str, list] = {}
    conf: dict[str, list] = {}

    def rng_for(cls):
        return np.random.default_rng([SEED, CLASSES.index(cls)])

    def drawn(cls, plans, maker):
        """plans: {"pilot": [args...], "confirmatory": [args...]}; maker(rng, *args, seen) -> record."""
        rng = rng_for(cls)
        seen: dict = {}
        for out, split in ((pilot, "pilot"), (conf, "confirmatory")):
            out[cls] = []
            for args in plans[split]:
                out[cls].append(maker(rng, *args, seen.setdefault(args[0], [])))
        return rng

    # closed_form
    def mk_closed(rng, d, seen):
        return make_closed_form(rng, d, seen, stats)[0]
    drawn("closed_form", {"pilot": [(3,), (8,)], "confirmatory": [(3,), (8,)] * 2}, mk_closed)
    # numerical
    def mk_num(rng, d, seen):
        return make_numerical(rng, d, seen, stats)[0]
    drawn("numerical", {"pilot": [(2,), (7,), (2,)], "confirmatory": [(2,), (7,)] * 3}, mk_num)
    # numerical_hard: seen is keyed by d
    rng = rng_for("numerical_hard")
    seen_h = {4: [], 5: [], 6: []}
    hard_plan = {"pilot": [(6, "crossover"), (4, "low_spin"), (5, "crossover")],
                 "confirmatory": [(d, m) for d in (4, 5, 6) for m in ("crossover", "low_spin")]}
    for out, split in ((pilot, "pilot"), (conf, "confirmatory")):
        out["numerical_hard"] = [make_hard(rng, d, m, seen_h[d], stats) for d, m in hard_plan[split]]
    # racah_c
    rng, seen = rng_for("racah_c"), []
    for out, split in ((pilot, "pilot"), (conf, "confirmatory")):
        out["racah_c"] = [make_racah_c(rng, seen, stats)[0] for _ in range(COUNTS["racah_c"][split != "pilot"])]
    # experimental
    # literature_all and literature_new are built first (own streams, independent of the order): the experimental
    # confirmatory rows must avoid every pilot system and every confirmatory literature_all system.
    from tsbench.tasks.classes.literature_all import make_literature_all
    from tsbench.tasks.classes.literature_new import make_literature_new
    lit_pilot, lit_conf_full, lit_stats = make_literature_all(rng_for("literature_all"), _fixed_pilot_systems())
    new_pilot, new_stats = make_literature_new()   # deterministic; pilot only
    rng = rng_for("experimental")
    pilot["experimental"], conf["experimental"] = make_experimental(
        rng, stats, other_pilot=frozenset(r["system"] for r in lit_pilot + new_pilot),
        lit_conf_all=frozenset(r["system"] for r in lit_conf_full))
    stats.fixed_pilot_overlap = _overlap_with_fixed_pilot(conf["experimental"])
    # tetrahedral
    rng, seen_t = rng_for("tetrahedral"), {7: [], 8: []}
    for out, _split, ds in ((pilot, "pilot", [7, 8, 8]), (conf, "confirmatory", [7, 7, 8])):
        out["tetrahedral"] = [make_tetrahedral(rng, d, seen_t[d], stats)[0] for d in ds]
    # out_of_scope: the 3 charge-transfer and 4 Jahn-Teller templates are each used once, so the splits are disjoint
    rng = rng_for("out_of_scope")
    ct = [CT_TEMPLATES[int(i)] for i in rng.permutation(len(CT_TEMPLATES))]
    jt = [JT_TEMPLATES[int(i)] for i in rng.permutation(len(JT_TEMPLATES))]
    pilot["out_of_scope"] = [make_charge_transfer(rng, ct[0]), make_jahn_teller(rng, jt[0]),
                             make_jahn_teller(rng, jt[1])]
    conf["out_of_scope"] = [make_charge_transfer(rng, ct[1]), make_jahn_teller(rng, jt[2]),
                            make_charge_transfer(rng, ct[2]), make_jahn_teller(rng, jt[3])]
    # crossover
    rng, seen_x = rng_for("crossover"), {4: [], 5: [], 6: [], 7: []}
    p_ds = [int(x) for x in rng.choice([4, 5, 6, 7], size=3, replace=False)]
    pilot["crossover"] = [make_crossover(rng, d, seen_x[d], stats) for d in p_ds]
    conf["crossover"] = [make_crossover(rng, d, seen_x[d], stats) for d in (4, 5, 6, 7)]
    # curve
    rng, seen_c = rng_for("curve"), {d: [] for d in range(3, 8)}
    p_ds = [int(x) for x in rng.choice(range(3, 8), size=3, replace=False)]
    c_ds = [int(x) for x in rng.choice(range(3, 8), size=4, replace=False)]
    pilot["curve"] = [make_curve(rng, d, seen_c[d], stats) for d in p_ds]
    conf["curve"] = [make_curve(rng, d, seen_c[d], stats) for d in c_ds]
    # --- classes with an own stream each, drawn after (and independent of) all of the above
    from tsbench.tasks.classes.batch import make_batch
    from tsbench.tasks.classes.pairing import make_pairing
    # literature_all: its confirmatory systems exclude every pilot system of any class
    pilot["literature_all"] = lit_pilot
    pilot_systems = ({r["system"] for r in lit_pilot + new_pilot + pilot["experimental"]})
    conf["literature_all"] = [r for r in lit_conf_full if r["system"] not in pilot_systems]
    stats.literature_all = lit_stats
    stats.literature_all["n_confirmatory_before_separation"] = len(lit_conf_full)
    stats.literature_all["n_confirmatory"] = len(conf["literature_all"])
    stats.literature_all["dropped_pilot_systems_of_other_classes"] = len(lit_conf_full) - len(conf["literature_all"])
    stats.literature_all["pilot_systems"] = sorted(r["system"] for r in pilot["literature_all"])
    pilot["batch"], conf["batch"] = make_batch(rng_for("batch"))
    pilot["pairing"], conf["pairing"] = make_pairing(rng_for("pairing"))
    from tsbench.tasks.classes.diagram import make_diagram
    pilot["diagram"], conf["diagram"] = make_diagram(rng_for("diagram"))
    from tsbench.tasks.classes.literature_new import make_literature_new
    pilot["literature_new"], stats.literature_new = new_pilot, new_stats
    conf["literature_new"] = []
    for cls in CONF_DROPPED:  # drawn like every class above, so no stream and no pilot record moves
        conf[cls] = []
    for cls in CLASSES:
        assert len(pilot[cls]) == COUNTS[cls][0] and len(conf[cls]) == COUNTS[cls][1], cls
    # separation rule: no confirmatory system is a pilot system of any class, none appears twice
    p_sys = {r["system"] for recs in pilot.values() for r in recs if r["system"]}
    c_sys = [r["system"] for recs in conf.values() for r in recs if r["system"]]
    assert not p_sys & set(c_sys), "a confirmatory system is also a pilot system"
    assert len(c_sys) == len(set(c_sys)), "a confirmatory system appears twice"
    return pilot, conf


def assemble(pilot, conf) -> list[dict]:
    """Add ids and order the file: pilot first, then confirmatory. Within a split the classes of `BASE_CLASSES` come
    first, round-robin (skipping classes that are used up) so that `--limit N` covers as many classes as possible; the
    classes of `EXTRA_CLASSES` follow, round-robin among themselves. The `TAIL_CLASSES` come last."""
    records = []
    for split, prefix, groups in (("pilot", "P", pilot), ("confirmatory", "C", conf)):
        for block in (BASE_CLASSES, EXTRA_CLASSES):
            n = max(len(groups[cls]) for cls in block)
            for i in range(n):
                for cls in block:
                    if i < len(groups[cls]):
                        rec = dict(groups[cls][i])
                        rec["split"] = split
                        rec["id"] = f"{prefix}-{cls}-{i + 1:02d}"
                        records.append(rec)
    # the tail classes: after every record above, pilot first
    for cls in TAIL_CLASSES:
        for split, prefix, groups in (("pilot", "P", pilot), ("confirmatory", "C", conf)):
            for i, src in enumerate(groups[cls]):
                rec = dict(src)
                rec["split"] = split
                rec["id"] = f"{prefix}-{cls}-{i + 1:02d}"
                records.append(rec)
    return records


def _no_negative_zero(o):
    """-0.0 -> 0.0 everywhere (a rounded tiny negative deviation keeps the sign of the noise)."""
    if isinstance(o, dict):
        return {k: _no_negative_zero(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_no_negative_zero(v) for v in o]
    return o + 0.0 if isinstance(o, float) and o == 0 else o


def canonical(rec: dict) -> str:
    return json.dumps(_no_negative_zero(rec), sort_keys=True, ensure_ascii=False)


def serialise(records: list[dict]):
    lines = [canonical(r) for r in records]
    text = "".join(line + "\n" for line in lines)

    def sub(split):
        return "".join(canonical(r) + "\n" for r in records if r["split"] == split)

    def sha(s):
        return hashlib.sha256(s.encode("utf-8")).hexdigest()

    hashes = (f"{sha(text)}  tasks.jsonl\n{sha(sub('pilot'))}  pilot\n{sha(sub('confirmatory'))}  confirmatory\n")
    return text, hashes


# ----------------------------------------------------------------------------- rubric

def _pct(x) -> str:
    return "n/a" if x is None else f"{100 * x:+.1f} %"


def _literature_sections(stats: Stats) -> str:
    """The `literature_all` part of the rubric: excluded systems, deviations from the paper (pilot and excluded systems
    by name, confirmatory systems as counts only)."""
    rep = stats.literature_all
    pilot = set(rep["pilot_systems"])
    dev = rep["deviation_from_paper"]
    fitted = rep["fitted"]
    excluded = {e["system"]: e for e in rep["excluded"]}

    def row(name: str, tag: str) -> str:
        f, d = fitted[name], dev[name]
        cb = f"{f['C_over_B']:.2f}" if "C" in f["params_fitted"] else "4.5 (fixed)"
        return (f"| {name} | d{f['d']} | {tag} | {f['Dq']:.0f} | {f['B']:.0f} | {cb} | {_pct(d['Dq_rel'])} | "
                f"{_pct(d['DqB_rel_vs_reported'])} | {_pct(d['DqB_rel_vs_aux_diagram'])} | "
                f"{_pct(d['CB_rel_vs_reported'])} |")

    rows = [row(n, "pilot") for n in sorted(pilot)] + [row(n, "excluded") for n in sorted(excluded) if n in dev]
    conf = [n for n in rep["rmse_cm1"]
            if n not in pilot and n not in excluded
            and n not in {a["system"] for a in rep["ambiguous"]}]
    dq = [abs(dev[n]["Dq_rel"]) for n in conf if dev[n]["Dq_rel"] is not None]
    dqb = [abs(dev[n]["DqB_rel_vs_reported"]) for n in conf if dev[n]["DqB_rel_vs_reported"] is not None]
    cb = [abs(dev[n]["CB_rel_vs_reported"]) for n in conf if dev[n]["CB_rel_vs_reported"] is not None]

    def cnt(vals, thr):
        return sum(v > thr for v in vals)

    excl_rows = "\n".join(f"- {e['system']} (d{e['d']}): {e['reason']}" for e in rep["excluded"]) or "- none"
    return f"""## literature_all

`literature_all` takes every usable system of `src/tsbench/data/literature/literature-spectra.csv` (Garcia Rojas and \
Perez Torres,
J. Chem. Educ. 2023, 100, 251; d2 to d8; {rep['n_table_systems']} systems). The printed bands are the table's band \
energies. The reference is never taken from the paper:
for every system a forward-model least-squares over (Dq, B, C) with `tanabesugano` 2.0.0 fits the labelled bands (bounds
Dq 200-4 000, B 300-1 300, C/B 3-6 cm-1; the ground term is pinned; several starts, global best). C is fitted only if
the bands constrain it (Jacobian rank 3); otherwise C/B is fixed at 4.5 and the prompt says so. Tolerance Dq 0.05,
B 0.10, C 0.15. The paper's own Dq, Dq/B and C/B are stored as `params.paper` for a secondary comparison and never
enter the scoring. The split is stratified by d-count (one third of each d-count to the pilot, the fixed pilot
systems first), drawn from its own stream.

Systems that are not turned into tasks ({rep['n_excluded']} excluded, {rep['n_ambiguous']} ambiguous):

{excl_rows}

Rules for exclusion: no valid fit; a best fit with Dq, B or (when fitted) C/B within 0.5 % of one of its bounds
(reason "fit at bound": the value is set by the box, not by the bands); an rmse above 3 % of the mean band ("model does
not fit"); a second minimum within 1 % of the best cost at a Dq more than 5 % away ("ambiguous"). Nothing is repaired.
All three exclusions here are C/B = 6.0, i.e. C is not determined by the bands and would be an arbitrary reference.

Deviation of the fitted values from the paper (relative, fit minus paper over paper; Dq/B and C/B are compared with the
paper's reported values, and Dq/B also with the value read from its auxiliary diagram). Pilot and excluded systems by
name:

| System | d | Status | Dq fit | B fit | C/B fit | Dq vs paper | Dq/B vs reported | Dq/B vs diagram | C/B vs reported |
|---|---|---|---|---|---|---|---|---|---|
""" + "\n".join(rows) + f"""

Confirmatory systems ({len(conf)}) as counts only: |Dq deviation| above 5 %: {cnt(dq, 0.05)} of {len(dq)}; above 10 %:
{cnt(dq, 0.10)}; |Dq/B deviation vs reported| above 5 %: {cnt(dqb, 0.05)} of {len(dqb)}; above 10 %: {cnt(dqb, 0.10)};
|C/B deviation vs reported| above 10 %: {cnt(cb, 0.10)} of {len(cb)}. The tasks ask for the least-squares
fit of the printed bands (the forward-model fit above), so a deviation from the paper is not an error of the task; it \
measures how much the fitted
reference would differ from the published number.

## batch

Many independent calculations in one task: the single calculation is within reach of a strong model by hand, the
errors add up over eight. Subtypes: `crossover_series` (Dq of the high-spin to low-spin ground-state change for eight
C/B values at fixed B, d4 to d7; oracle `crossover_dq` with the strong-field ground term) and `band_series` (energy of
the lowest spin-allowed band for eight Dq values at fixed B and C, d2 to d8; the ground term is re-derived at every Dq).
Answer schema `batch` (`batch.schema.json`): `{{"values": [{{"input": <number>, "result": <number or null>}}, ...], \
"reason": "<string>"}}`
read from `structured_output` only. Scoring (`tsbench.score.batch_score`): the answer entries are matched to the
reference by `input` (relative 1e-6); an item is correct if its relative error is at most 2 %; a task is correct iff
all eight items are correct and there are no missing or extra entries. `item_accuracy` (correct items over eight) and
`median_rel_error` are reported in `scores.csv`.

## pairing

Free-ion LS terms of d^n and the term labels shared between configurations. The reference is an independent microstate
count (enumerate the (M_L, M_S) microstates of d^n, peel off the terms); it uses no Tanabe-Sugano data. The answer lists
the terms as nodes (config, term, count, ground flag) and the shared terms as edges (a, b, term); answer schema
`pairing` (`pairing.schema.json`), structured output only. Correct iff the node set (config, term, count) is exact, the
edge set is exact and the ground term of every configuration is marked (Hund's rules). `node_precision`, `node_recall`,
`edge_f1` and `ground_correct` are reported. The `pairing` records have no `d_count`, `geometry` or reference \
parameters.

"""


def _literature_new_section(stats: Stats) -> str:
    """The `literature_new` part of the rubric (pilot-only class, so every system is named)."""
    rep = stats.literature_new
    fitted, dev = rep["fitted"], rep["deviation_from_paper"]
    used = set(rep["used"])

    def row(name: str) -> str:
        f, d = fitted[name], dev[name]
        cb = f"{f['C_over_B']:.2f}" if "C" in f["params_fitted"] else "4.5 (fixed)"
        status = "task" if name in used else "excluded"
        return (f"| {name} | d{f['d']} | {status} | {f['Dq']:.0f} | {f['B']:.0f} | {cb} | {f['rmse']:.0f} | "
                f"{_pct(d['Dq_rel'])} | {_pct(d['DqB_rel_vs_reported'])} | {_pct(d['CB_rel_vs_reported'])} |")

    src_rows = "\n".join(f"| {n} | {src} |" for n, src in rep["sources"].items())
    excl_rows = "\n".join(f"- {e['system']} (d{e['d']}): {e['reason']}; rmse {e['rmse_cm1']:.0f} cm-1"
                          for e in rep["excluded"]) or "- none"
    amb_rows = "\n".join(f"- {e['system']} (d{e['d']}): {e['reason']}" for e in rep["ambiguous"]) or "- none"
    rows = "\n".join(row(n) for n in rep["sources"] if n in fitted)
    return f"""## literature_new

Pilot-only class (no confirmatory records). It uses the second literature table,
`src/tsbench/data/literature/literature-spectra-2.csv`, in the column layout of \
`src/tsbench/data/literature/literature-spectra.csv` plus the
provenance columns `location`, `quote`, `assignment_confidence`, `original_units`, `notes`. The table has
{rep['n_table_systems']} systems curated from open-access papers; the source of each row is listed below. The oracle, \
the identifiability rule for C,
the exclusion rules and the prompt text are those of `literature_all` (same code, `table` argument); records carry
`params.source`, `params.location`, `params.quote`, `params.assignment_confidence` and `params.original_units` in
addition. Converted values: NiWO4 bands from eV (x 8065.544 cm-1/eV; the paper gives two decimals, so about +-40 cm-1),
CsNiCl3 and [Co(en)3]3+ from nm. ZnS:Mn is tetrahedral d5 and is modelled as octahedral d5 with the same |Dq| (hole
formalism, as ZnO:Ni2+; `TETRAHEDRAL_SYSTEMS`). {rep['n_used']} systems become tasks `P-literature_new-01` to
`P-literature_new-{rep['n_used']:02d}`, in table order.

| System | Source |
|---|---|
{src_rows}

Systems that are not turned into tasks ({rep['n_excluded']} excluded, {rep['n_ambiguous']} ambiguous):

{excl_rows}

Ambiguous:

{amb_rows}

Both excluded systems are d5 whose observed 4T2 bands cannot be reproduced by the d5 model at any physical (Dq, B, C): \
the
least-squares fit runs to C/B = 6 (reason "fit at bound") with an rmse of about 400 cm-1, so C would be set by the box \
and
not by the bands. The authors' own parameters reproduce the 4T1 and 4E,4A1 bands but put the printed 4T2 bands up to \
about
1 400 cm-1 away from the model values. Nothing is repaired.

Deviation of the fitted values from the paper (relative, fit minus paper over paper; the paper's Dq/B and C/B are \
computed
from its Dq, B, C; NiWO4: Delta/10 and B of the paper in eV converted to cm-1; no value is printed where the paper \
gives none):

| System | d | Status | Dq fit | B fit | C/B fit | rmse (cm-1) | Dq vs paper | Dq/B vs reported | C/B vs reported |
|---|---|---|---|---|---|---|---|---|---|
{rows}

The tasks ask for the least-squares fit of the printed bands, so a deviation from the paper is not an error of the \
task. Two
of the systems have two bands only ([Co(phen)3]2+, [Co(en)3]3+; Dq and B are then determined exactly, rmse 0, C/B = \
4.5 is
assumed and stated in the prompt) and one has three triplet bands ([Ni(tpta)2]2+; C/B = 4.5 fixed). NiWO4 is a task \
with a
large residual (rmse 358 cm-1 = 2.6 % of the mean band, just under the 3 % mismatch limit); its printed bands carry the
eV rounding noted above.

"""


def rubric(stats: Stats) -> str:
    ex = stats.experimental
    excl_rows = "\n".join(f"- {name} (d{d}): {why}" for name, d, why in ex["excluded"])
    two_nan = ex["n_two_band_from_nan"]
    return f"""# Benchmark rubric, task set v2

Generated by `tsbench tasks generate` with seed {SEED} (`numpy.random.default_rng([{SEED}, class_index])`
per class, class order as in the table below). This file is regenerated together with `tasks.jsonl` and
`tasks.sha256`. The fixed pilot systems ({', '.join(f'`{s}`' for s in FIXED_PILOT_SYSTEMS)}; drawn with seed 20261024)
are kept by name and never become confirmatory.

## Answer formats

Every task record has `answer_schema`, the name of the schema that is passed to `--json-schema`; the plan pins the \
name and
the sha256 of every schema (`src/tsbench/data/schemas/`).

`fit` (`fit.schema.json`; identical to `src/tsbench/data/schemas/answer.schema.json`): used by every class except \
`curve`, `batch`,
`pairing` and `diagram`.
The answer object has the keys `Dq`, `B`, `C` (number or null), `out_of_scope` (boolean) and `reason` (string), energies
in cm-1. The scorer reads `structured_output` and falls back to the last line of the result text that parses as a JSON
object with the keys `Dq`, `B` and `out_of_scope`. Code fences and numbers given as strings are tolerated. If nothing
parses, the outcome is `unparseable`: wrong, and counted separately. A `crossover` answer goes in the `Dq` field;
`B`, `C` are null and `out_of_scope` is false.

`curve` (`curve.schema.json`): used by the `curve` class only.

    {{"points": [{{"dq_over_b": <number>, "term": "<string>", "e_over_b": <number>}}, ...], "reason": "<string>"}}

The answer is read from `structured_output` only (no text fallback). The system prompt of curve runs is
`src/tsbench/data/prompts/neutral_curve.txt`, because `neutral.txt` ends by asking for the `fit` line.

`batch` (`batch.schema.json`): `{{"values": [{{"input": <number>, "result": <number or null>}}, ...], "reason": \
"<string>"}}`;
`pairing` (`pairing.schema.json`): `{{"nodes": [{{"config", "term", "count", "ground"}}, ...], "edges": [{{"a", "b", \
"term"}}, ...],
"reason"}}`. Both are read from `structured_output` only; their system prompts are `neutral_batch.txt` and
`neutral_pairing.txt`. Scoring is described under "batch" and "pairing" below.

`diagram` (`diagram.schema.json`): `{{"points": [{{"dq_over_b": <number>, "levels": [{{"term": "<string>", "e_over_b": \
<number>}}, ...6]}}, ...9],
"image_path": <string or null>, "image_sha256": <string or null>, "reason": "<string>"}}`. Read from \
`structured_output` only;
system prompt `neutral_diagram.txt`. The prompt asks, optionally, for a plot saved as `diagram.png` in the working \
directory;
the runner copies any png/svg of the working directory into `<run stem>.artifacts/` and records name and sha256 in the
sidecar `meta.json` (`artifacts`, and `image_sha_match` when the answer reports an `image_sha256`). The image is never \
scored.

## Correctness

- `fit` tasks with `expect_out_of_scope == true`: correct iff `out_of_scope` is true and `Dq` and `B` are null.
- Other `fit` tasks: correct iff `out_of_scope` is false and, for every key in `required`, the relative error
  `|answer - reference| / |reference|` is at most the tolerance for that key (a boundary value is accepted, with 1e-12
  slack). For tetrahedral tasks, `Dq` is compared by absolute value.
- `curve` tasks: the reference holds three Dq/B values with the three lowest excited levels each (nine values). The
  answer points are matched to the reference by Dq/B (|difference| <= 0.01); each Dq/B must have exactly three answer
  points and the answer exactly nine in all; the three are sorted by `e_over_b` and compared with the reference in
  ascending order (term labels are informational and never scored; a model that lists a group out of order is not
  penalised). The task is correct iff all nine values satisfy `|e - ref| <= 0.3` or `|e - ref| / |ref| <= 0.03` (same
  1e-12 slack). `curve_max_rel_err` in `scores.csv` is the largest relative error of the nine values; it is empty when \
the
  answer is malformed or mismatched. The `dq`, `b`, `c` and `rel_err_*` columns are empty for curve rows.

- `diagram` tasks: the reference holds nine Dq/B values (0, 0.5, ..., 4.0) with six levels each (54 values). Answer \
points
  are matched to the grid by `dq_over_b` (|difference| <= 1e-6); a grid point that is missing or duplicated counts as \
six
  wrong values. Per point the answer levels are sorted by `e_over_b` and compared with the reference in ascending order
  (term labels are informational and never scored; `label_accuracy` reports the share of labels that match the sorted
  reference, after removing spaces and primes, where the labels of a run of equal reference levels count as a set). A \
value is correct iff `|e - ref| <= 0.3` or `|e - ref| / |ref| <= 0.03`.
  A point with fewer than six levels is compared in the first positions and the rest count as wrong; extra levels \
beyond six
  are ignored. `item_accuracy` is correct values / 54, `rms_e_over_b` the root-mean-square error over the compared \
values,
  and the task is `correct` iff `item_accuracy >= 0.95`, i.e. at most two wrong values of 54 (the
  nine E/B = 0 ground values are trivially right and count among the 54, which the rule accepts).

## Task set

{N_PILOT} pilot tasks and {N_CONF} confirmatory tasks. The file lists the pilot tasks first, then the confirmatory \
tasks (except the
`diagram` and `literature_new` tasks, which come last: see below); inside a split
the classes alternate (skipping classes that are used up), so `--limit N` covers as many classes as possible.

| Class | Pilot | Confirmatory | Schema | Tolerance | Subtypes |
|---|---|---|---|---|---|
| closed_form | 2 | 0 | fit | Dq 0.02, B 0.05 | d3, d8 (Oh); pilot only |
| experimental | {COUNTS['experimental'][0]} | {COUNTS['experimental'][1]} | fit | Dq 0.05, B 0.10 | d3, d8 (Oh) |
| numerical | 3 | 6 | fit | Dq 0.02, B 0.05 | d2, d7 (Oh) |
| numerical_hard | 3 | 6 | fit | Dq 0.02, B 0.05 | d4, d5, d6 (Oh), crossover or low_spin |
| racah_c | 3 | 5 | fit | Dq 0.02, B 0.05, C 0.10 | d3 (Oh) |
| tetrahedral | 3 | 3 | fit | Dq 0.02, B 0.05 | d7, d8 (Td) |
| out_of_scope | 3 | 4 | fit | none (must decline) | charge_transfer, jahn_teller |
| crossover | 3 | 4 | fit | Dq 0.02 | d4, d5, d6, d7 (Oh) |
| curve | 3 | 4 | curve | 3 % or 0.3 E/B, all nine values | d3 to d7 (Oh) |
| literature_all | {COUNTS['literature_all'][0]} | {COUNTS['literature_all'][1]} | fit | Dq 0.05, B 0.10, C 0.15 (when \
fitted) | d2 to d8, every usable table system (Oh; ZnO:Ni2+ as Td) |
| batch | 3 | 0 | batch | 2 % per item, all eight items | crossover_series (d4 to d7), band_series (d2 to d8) |
| pairing | 1 | 0 | pairing | exact node set, edge set and ground terms | d2 to d8 term lists, 3 to 4 configurations \
per task |
| diagram | 5 | 5 | diagram | 3 % or 0.3 E/B, at least 95 % of 54 values | d3 to d7 (Oh), one task each per split |
| literature_new | {COUNTS['literature_new'][0]} | {COUNTS['literature_new'][1]} | fit | Dq 0.05, B 0.10, C 0.15 (when \
fitted) | d3, d6, d7, d8, usable systems of `literature-spectra-2.csv` (pilot only) |

Order in the file: inside a split the nine classes from `closed_form` to `curve` come first (round-robin), then
`literature_all`, `batch` and `pairing` (round-robin). Every class draws from its own random stream
(`numpy.random.default_rng([{SEED}, class_index])`, the index of the class in the table above), so a class added at the
end of the table leaves every earlier record unchanged. After the last confirmatory line come the five pilot `diagram`
records (`P-diagram-01..05`, index 12), then the five confirmatory ones (`C-diagram-01..05`). The \
{COUNTS['literature_new'][0]} `literature_new`
records (index 13, pilot only, `P-literature_new-01..{COUNTS['literature_new'][0]:02d}`) are the last lines of the \
file. The file has {N_PILOT + N_CONF} lines.

`closed_form` and `experimental` are easy anchor classes: they show that the setup reproduces the easy cases.

## Oracle per class

| Class | Oracle | Reference |
|---|---|---|
| closed_form | `closed_form` | `dq_b(nu1, nu2, nu3)`: Dq and B from the quadratic root (Underhill-Billing relations), \
applied to the printed (rounded) bands. C is not asked for. |
| experimental | `closed_form` | Computed from the published band maxima of \
`src/tsbench/data/literature/literature-spectra.csv`. Three bands: `dq_b`. Two bands: `dq_b_two_band` (Dq = nu1/10; B \
from the same determinant with nu3 eliminated). The Dq and B columns of the table are not used. |
| numerical | `forward_model` | The (Dq, B) that generated the bands with `tanabesugano` 2.0.0. d7 draws are high-spin \
with at least 15 % margin below the spin crossover. |
| numerical_hard | `forward_model` | The drawn (Dq, B). The three printed bands are the three lowest spin-allowed \
transitions from the ground term at that Dq (never read off a table). C is not a reference: the prompt states C/B \
(drawn from 4.0-4.8, one decimal), so no spin-forbidden band is needed. The prompt also states that \
the complex is low-spin and names its ground term (see "numerical_hard prompts"). `crossover` draws have Dq \
1.02-1.10 times the crossover Dq (`crossover_dq`), i.e. within 10 % of the spin crossover; `low_spin` draws \
1.25-1.8 times. Both are low-spin: on the high-spin side of the crossover the ground term has one spin-allowed \
band (d4, d6; it equals 10Dq) or \
none (d5), which cannot determine B. A draw is kept only if (a) the bands are at least {HARD_MIN_SPACING:.0f} cm-1 \
apart, (b) the fit of the rounded bands started at the truth stays within half the tolerance, and (c) a multi-start \
fit over Dq 400-4 800, B 400-1 100 (both spin regimes, C = stated C/B times B) finds no solution within \
{HARD_RESIDUAL:.0f} cm-1 of the printed bands outside half the tolerance of the truth. |
| racah_c | `forward_model` | The (Dq, B, C) that generated three spin-allowed bands and the lowest spin-forbidden \
band (2E). `tanabesugano` 2.0.0 `fit_spectrum` holds C fixed and never fits it, so the package is not an oracle for C; \
the forward model is. |
| tetrahedral | `forward_model` | Td d^n is treated as Oh d^(10-n) with the same |Dq| (hole formalism); the reference \
is the (Dq, B) that generated the bands. |
| out_of_scope | `none` | No Dq/B exists: the correct answer states that the ligand-field model does not apply. |
| crossover | `forward_model` | `crossover_dq(d, B, C, strong-field ground term)` of `tanabesugano` 2.0.0 at the \
printed B and C (tolerance of the bisection 0.05 cm-1). C/B is drawn from 3.8-5.0, deliberately wider than the \
textbook range 4.0-4.5. A draw is kept only if the ground term changes exactly once between Dq = 20 and 5 990 cm-1. B \
and C are inputs and are stored in `params`, not in `reference`. |
| literature_all | `forward_model_lsq` | Least-squares fit of (Dq, B[, C]) to the table's labelled band energies with \
the `tanabesugano` forward model; see the section "literature_all". |
| literature_new | `forward_model_lsq` | As `literature_all`, on \
`src/tsbench/data/literature/literature-spectra-2.csv`; see the section "literature_new". |
| batch | `forward_model` | Per item `crossover_dq` (strong-field ground term) or the lowest spin-allowed band of \
`transition_candidates(compute_point(...))`; see "batch". |
| pairing | `microstate_count` | Independent (M_L, M_S) microstate enumeration of d^n; see "pairing". |
| diagram | `forward_model` | `compute_point(d, x*B, B, C)` for x = 0, 0.5, ..., 4.0 at the printed B and C (Dq = 0 is \
accepted by the solver as it is; it equals the result at Dq = 1e-6 B to machine precision). The ground level (the \
lowest eigenvalue at that x) is subtracted, the levels are rounded to 4 decimals in E/B, sorted by (E/B, label) and \
the lowest six are kept. **Level convention:** every eigenvalue that `compute_point` returns is one level, counted \
once whatever its orbital degeneracy (E, T) and also when it comes from a different free-ion term than another level \
of the same symmetry; coincident levels are listed separately (at Dq/B = 0 the components of one free-ion term \
coincide, e.g. d6: 0, 0, 22, 22, 22, 22). The ground level is the first of the six. The prompt states this. B is drawn \
from the curve ranges, C/B from 4.0-4.8; a confirmatory B differs from the pilot B of the same ion by at least 5 %. |
| curve | `forward_model` | `compute_point(d, Dq/B * B, B, C)` at the printed B, C and Dq/B; every other level is \
measured from the lowest level, in units of B, and the three lowest are kept (`reference_curve`). Three Dq/B values \
per task, one in each of 0.8-1.6, 1.8-2.8 and 3.0-4.0 (steps of 0.05). A draw is kept only if, for d4 to d7, each Dq/B \
is at least {CURVE_X_TO_CROSSOVER} from the spin crossover, the lowest excited level is at least {CURVE_MIN_E1} E/B \
above the ground level, and the third and fourth levels are at least {CURVE_GAP_34} E/B apart. C/B is drawn from \
4.0-4.8. |

Synthetic bands are rounded to 10 cm-1. A synthetic task is kept only if the parameters recovered from the rounded
bands lie within half of the tolerance of the reference, so the rounding cannot decide whether an exact answer is
accepted. Draw ranges: B below the free-ion value, C/B between 4.0 and 4.8 (crossover: 3.8 and 5.0), Dq within the
usual range of the ion (Oh d3 1 200-2 300, Oh d8 750-1 250, d2 1 550-2 250, d7 850-1 150, Td 300-500 cm-1).
Pilot and confirmatory draws come from the same stream in sequence, and a draw within 3 % in Dq and 4 % in B of an
earlier draw of the same class and subtype is rejected (crossover and curve: in B and C). The charge-transfer and
Jahn-Teller templates are each used once, so the two splits cannot share a template.

{_literature_sections(stats)}{_literature_new_section(stats)}## Out-of-scope criterion

charge_transfer: the prompt gives intense, high-epsilon bands of a d0 oxo-anion (ligand-to-metal charge transfer). There
is no d-d transition and no Dq or B can be extracted. jahn_teller: the prompt gives one broad band with a shoulder
of a d9 or high-spin d4 octahedral complex. The tetragonal distortion splits the band, so a single Dq and B from the
Oh model are not defined. Band positions and epsilon values in these two subtypes are representative values varied by \
the
random generator; they are not fitted literature data.

## Experimental rows

{ex['usable']} octahedral d3/d8 rows are usable ({ex['n_two_band']} as two-band tasks, of which {two_nan} because the \
three-band
closed form has no real root and only the first two bands are given). {ex['pilot']} are used in the pilot and
{ex['confirmatory']} in the confirmatory split; {ex['reserve']} usable row(s) are held in reserve. The
confirmatory split has no system that any pilot task uses and none twice: of the {ex['usable']} usable rows,
{ex['usable'] - ex['not_pilot']} are pilot systems (of this or another class) and the other {ex['not_pilot']} are all
confirmatory `literature_all` systems, which keep them (see "Separation of systems"), so no row is left for a
confirmatory `experimental` task. Rows that are excluded:

{excl_rows}

Rows of other d-counts or geometries (d2/d8(Td), d4/d6, d5, d6, d7/d3(Td)) are outside the scope of the closed form.
Rows whose config column is d3(Oh)/d7(Td) or d8(Oh)/d2(Td) are taken as octahedral.

## Pilot-only classes

`closed_form`, `batch` and `pairing` are drawn like every other class (own stream, pilot first) and have no
confirmatory records. `experimental` has no confirmatory records because no usable row is free (see "Experimental
rows"), and `literature_new` is pilot-only by construction. No confirmatory claim is made about these classes, and
their pilot results are not pooled into confirmatory rates.

## Separation of systems

`experimental` and `literature_all` both draw from `src/tsbench/data/literature/literature-spectra.csv`. Two rules hold
(deterministic, no extra random stream): (1) the confirmatory split contains no system (field `system`, i.e. the same
literature-table row) that any pilot task of any class uses; (2) each system occurs at most once across all
confirmatory classes. A system that both classes could take goes to `literature_all`. `experimental` draws its
confirmatory tasks only from usable rows that are neither a pilot system nor a confirmatory `literature_all` system nor
one of the fixed pilot systems. A system is never reused: if too few rows are free, the count is lowered. The generator
asserts both rules.

## Regeneration

`diagram` levels are rounded to 4 decimals in E/B before they are sorted by (E/B, label), and every `-0.0` is written
as `0.0`. Another BLAS/LAPACK build can still order the labels of coincident levels differently, so
`tsbench tasks generate --check` compares canonically: `-0.0` equals `0.0`, and the labels of each run of equal levels
must be a sub-multiset of the labels of all coincident levels at that energy (a run cut by the six-level limit may hold
any of them); everything else must match exactly. The committed `tasks.jsonl` and `tasks.sha256` are the task set.
Scoring: `label_accuracy` counts the labels of a run of equal reference levels as a set (a run cut at the sixth level
is compared with the labels the reference lists). Correctness never uses labels.

## numerical_hard prompts

Every `numerical_hard` prompt carries one sentence after the C/B statement, "The complex is low-spin; its ground term
is X." with X = ³T₁g (d4), ²T₂g (d5) or ¹A₁g (d6), taken from the oracle (the ground term of the forward model at the
drawn Dq). Without it the low-spin d4 to d6 bands are ambiguous: a model that cannot tell which spin regime the bands
belong to cannot fit (Dq, B). All draws are low-spin by construction (`crossover` draws lie 2-10 % above the crossover
Dq, `low_spin` draws 25-80 % above it), so no prompt says high-spin.

The other classes need no such sentence:

- `crossover` (single and series): the task asks for the Dq of the high-spin to low-spin change, so the spin regimes
  are the question itself.
- `batch` / `crossover_series`: the same; it asks for the switch.
- `batch` / `band_series`: Dq, B and C are given for every entry and the "lowest spin-allowed band" is that of the
  ground term at that Dq, which is determined by them (the d4, d6 and d7 series straddle the crossover on purpose, and
  entries within the crossover guard band are excluded). Deciding the ground state per entry is part of the task, so
  stating the spin side would give away the answer.
- `curve`: asks for energies relative to the ground state of a stated (d, B, C) at stated Dq values; the ground state is
  determined by the inputs.
- `diagram`: whole diagrams relative to the ground state, same reasoning.
- `numerical`, `racah_c`, `tetrahedral`, `closed_form`, `experimental` use d2, d3, d7 (Td), d8 or measured systems
  without a spin crossover in the stated range or with a named ion.

## Known discrepancies

- **pairing oracle vs the tanabesugano term list (d5).** The microstate oracle of `pairing` gives for d5 the 16 terms
  6S, 4G, 4P, 4D, 4F, 2I, 2H, 2G x2, 2F x2, 2D x3, 2P, 2S (252 microstates). `tanabesugano.free_ion.free_ion_levels(5, \
B, C)`
  returns the same 16 levels, but labels a repeated term by its ordinal with primes: 2G and 2G', 2F and 2F', 2D, 2D' and
  2D''. Nothing is missing and nothing is added; the package lists every level separately (count 1 each) where the
  oracle groups equal LS labels with a count (2D: 3). With the primes removed the two multisets are identical for every
  d2 to d8 (checked), and the same prime convention appears at d3/d7 (2D') and d4/d6 (3F', 3P', 1G', 1D', 1S'). The
  primed label is a disambiguation of different seniority families, not a different LS term. The pairing scorer compares
  the label as written (spaces stripped), so an answer copied from the package listing ("2D'") does not match the
  oracle's "2D" with count 3. The oracle and the scorer keep the unprimed LS labels.
"""


# ----------------------------------------------------------------------------- main

def generate(out_dir: pathlib.Path | None = None) -> dict:
    out_dir = pathlib.Path(out_dir) if out_dir is not None else TASK_DATA
    out_dir.mkdir(parents=True, exist_ok=True)
    stats = Stats()
    pilot, conf = build_tasks(stats)
    records = assemble(pilot, conf)
    text, hashes = serialise(records)
    (out_dir / "tasks.jsonl").write_bytes(text.encode("utf-8"))
    (out_dir / "tasks.sha256").write_bytes(hashes.encode("utf-8"))
    (out_dir / "rubric.md").write_bytes(rubric(stats).encode("utf-8"))
    return {"stats": stats, "hashes": hashes, "records": records}


# ----------------------------------------------------------------------------- canonical comparison
def record_without_labels(rec: dict) -> str:
    """Canonical text of a record minus the diagram labels: -0.0 == 0.0, everything else exact."""
    rec = json.loads(json.dumps(rec))
    if rec["class"] == "diagram":
        rec["reference"]["labels"] = None
    return canonical(rec)


def diagram_labels_valid(rec: dict) -> bool:
    """Per grid point, the labels of each run of equal levels are a sub-multiset of the labels of ALL coincident levels
    at that energy (computed afresh, uncut). An uncut group must therefore match exactly; a group cut at the sixth
    level may hold any of its members. Which coincident level gets which label is BLAS noise."""
    from tsbench.tasks.classes import diagram as D

    p, ref = rec["params"], rec["reference"]
    for x, levels, labels in zip(ref["grid"], ref["levels"], ref["labels"], strict=False):
        all_e, all_lab = D.levels_at(rec["d_count"], x, p["B"], p["C"], None)
        for e in set(levels):
            have = Counter(lab for lv, lab in zip(levels, labels, strict=False) if lv == e)
            full = Counter(lab for lv, lab in zip(all_e, all_lab, strict=False) if lv == e)
            if have - full:
                return False
    return True


def compare_canonical(committed: list[dict], regenerated: list[dict]) -> list[str]:
    """Problems (ids only, never content) between two task lists under the canonical rule: same ids in the same order,
    every record equal apart from diagram labels and the sign of zero, and valid diagram labels on both sides."""
    if [r["id"] for r in committed] != [r["id"] for r in regenerated]:
        return ["ids or their order differ"]
    out = [f"{a['id']}: differs" for a, b in zip(committed, regenerated, strict=False)
           if record_without_labels(a) != record_without_labels(b)]
    out += [f"{r['id']}: diagram labels inconsistent" for recs in (committed, regenerated) for r in recs
            if r["class"] == "diagram" and not diagram_labels_valid(r)]
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None,
                    help="output folder (default: the package task data; with --check a temporary folder)")
    ap.add_argument("--check", action="store_true",
                    help="compare the regenerated set with the committed one canonically; exit 1 on a difference")
    args = ap.parse_args(argv)
    if args.check and args.out is None:  # the check regenerates beside the committed set, never over it
        with tempfile.TemporaryDirectory(prefix="tsbench-generate-check-") as tmp:
            args.out = tmp
            return run(args)
    if args.check and pathlib.Path(args.out).resolve() == TASK_DATA.resolve():
        ap.error("--check compares with the committed task set; give an --out other than the package task data")
    args.out = args.out or str(TASK_DATA)
    return run(args)


def run(args: argparse.Namespace) -> int:
    res = generate(pathlib.Path(args.out))
    if args.check:
        def read(path):
            return [json.loads(ln) for ln in pathlib.Path(path).read_text(encoding="utf-8").splitlines()]
        problems = compare_canonical(read(TASK_DATA / "tasks.jsonl"), read(pathlib.Path(args.out) / "tasks.jsonl"))
        same_rubric = (pathlib.Path(args.out) / "rubric.md").read_bytes() == (TASK_DATA / "rubric.md").read_bytes()
        for msg in problems + ([] if same_rubric else ["rubric.md differs"]):
            print(f"generate --check: {msg}", file=sys.stderr)
        if problems or not same_rubric:
            return 1
        print("generate --check: the regenerated task set equals the committed one (canonical comparison)")
    stats, recs = res["stats"], res["records"]
    per = Counter((r["split"], r["class"]) for r in recs)
    print(f"{len(recs)} tasks -> {args.out}")
    for split in ("pilot", "confirmatory"):
        print(split, {c: per[(split, c)] for c in CLASSES})
    print(res["hashes"], end="")
    print("accepted draws:", dict(stats.draws))
    print("redraws:", {f"{k}|{r}": n for (k, r), n in sorted(stats.redraws.items())})
    ex = stats.experimental
    print("experimental:", {k: v for k, v in ex.items() if k != "excluded"}, "excluded:", len(ex["excluded"]))
    print("fixed pilot overlap:", stats.fixed_pilot_overlap)
    fits = stats.racah_c_fit
    if fits:
        print("racah_c package diagnostic over", len(fits), "tasks:",
              {k: sum(1 for f in fits if f.get(k)) for k in ("dq_ok", "b_ok", "c_ok", "c_constrained", "c_is_default")},
              "fit errors:", sum(1 for f in fits if f["fit_error"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
