"""Tests for the task generator. No network, no LLM.

Confirmatory tasks are checked in bulk. Assertions report ids, counts and booleans only, never the
content of a record, so that a failure cannot print a confirmatory task.
"""
import csv
import hashlib
import json
import math
import pathlib
import re

import pytest

from tsbench.core import resource
from tsbench.tasks import HASH_PATH, TASKS_PATH, common, load
from tsbench.tasks import generate as gen
from tsbench.tasks.classes import experimental
from tsbench.tasks.classes import numerical_hard as numhard
from tsbench.tasks.oracles import check
from tsbench.tasks.oracles.closed_form import dq_b, dq_b_two_band

HERE = pathlib.Path(__file__).resolve().parent
TASK_DATA = resource("tasks")  # tasks.jsonl, tasks.sha256, rubric.md
CLASSES = gen.CLASSES
BASE = gen.BASE_CLASSES
FIELDS = {"id", "split", "class", "subtype", "d_count", "geometry", "system", "bands_cm1", "prompt", "required",
          "reference", "tolerance", "oracle", "expect_out_of_scope", "answer_schema", "params", "reference_curve"}


class Record(dict):
    """A task record whose repr is its id, so that a failing assertion cannot print task content."""

    def __repr__(self):
        return f"<task {self.get('id')}>"


class Records(list):
    def __repr__(self):
        return f"<{len(self)} task records>"


@pytest.fixture(scope="module")
def all_records():
    return Records(Record(json.loads(line)) for line in TASKS_PATH.read_text(encoding="utf-8").splitlines())


@pytest.fixture(scope="module")
def records(all_records):
    """The nine classes of BASE_CLASSES. The class-specific tests below are written for them; the other classes
    have their own tests at the end of the file."""
    return Records(r for r in all_records if r["class"] in BASE)


@pytest.fixture(scope="module")
def regenerated(tmp_path_factory):
    out = tmp_path_factory.mktemp("regen")
    gen.generate(out)
    return out


def failing(records, predicate):
    return [r["id"] for r in records if not predicate(r)]


def split(records, name):
    return Records(r for r in records if r["split"] == name)


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


# ----------------------------------------------------------------------------- reproducibility and hashes

def test_regeneration_reproduces_committed_files(all_records, regenerated):
    """Canonical, not byte-for-byte: another BLAS build can order coincident diagram levels differently and flip the
    sign of a zero. The committed tasks.jsonl and tasks.sha256
    are the sealed set and never change; test_hash_file_format_and_values checks the hashes against them."""
    assert (regenerated / "rubric.md").read_bytes() == (TASK_DATA / "rubric.md").read_bytes(), "rubric.md differs"
    regen = [Record(json.loads(ln)) for ln in (regenerated / "tasks.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [r["id"] for r in regen] == [r["id"] for r in all_records]
    problems = gen.compare_canonical(list(all_records), regen)
    assert not problems, f"canonical comparison: {problems}"
    lines = (regenerated / "tasks.sha256").read_text(encoding="utf-8").splitlines()
    assert lines[0].split("  ")[0] == sha((regenerated / "tasks.jsonl").read_bytes())


def test_hash_file_format_and_values(all_records):
    lines = HASH_PATH.read_text(encoding="utf-8").splitlines()
    assert [ln.split("  ")[1] for ln in lines] == ["tasks.jsonl", "pilot", "confirmatory"]
    assert all(re.fullmatch(r"[0-9a-f]{64}  \S+", ln) for ln in lines)
    got = [ln.split("  ")[0] for ln in lines]
    assert got[0] == sha(TASKS_PATH.read_bytes())
    for i, name in ((1, "pilot"), (2, "confirmatory")):
        text = "\n".join(json.dumps(r, sort_keys=True, ensure_ascii=False) for r in split(all_records, name)) + "\n"
        assert got[i] == sha(text.encode("utf-8"))


def test_file_is_canonical_one_record_per_line(all_records):
    raw = TASKS_PATH.read_text(encoding="utf-8")
    assert raw.endswith("\n")
    lines = raw.splitlines()
    assert len(lines) == len(all_records)
    assert all(ln == json.dumps(r, sort_keys=True, ensure_ascii=False)
               for ln, r in zip(lines, all_records, strict=False))


def test_generator_stdout_contains_no_task_text(tmp_path, capsys):
    gen.main(["--out", str(tmp_path)])
    out = capsys.readouterr().out
    recs = [json.loads(ln) for ln in (tmp_path / "tasks.jsonl").read_text(encoding="utf-8").splitlines()]
    leaked = [r["id"] for r in recs if r["prompt"][:40] in out]
    assert not leaked


# ----------------------------------------------------------------------------- structure

def test_counts_per_split_and_class(all_records):
    assert len(all_records) == 105
    for name, col in (("pilot", 0), ("confirmatory", 1)):
        for cls in CLASSES:
            got = sum(1 for r in split(all_records, name) if r["class"] == cls)
            assert got == gen.COUNTS[cls][col], f"{name}/{cls}: {got}"
    # the diagram class is appended at the end: five pilot lines, then five confirmatory ones, then the six
    # literature_new pilot lines
    assert [r["split"] for r in all_records] == (
        ["pilot"] * 39 + ["confirmatory"] * 50 + ["pilot"] * 5 + ["confirmatory"] * 5 + ["pilot"] * 6)
    assert sum(p for p, _ in gen.COUNTS.values()) == 50 and sum(c for _, c in gen.COUNTS.values()) == 55
    assert {c: gen.COUNTS[c] for c in BASE} == {
        "closed_form": (2, 0), "experimental": (2, 0), "numerical": (3, 6), "numerical_hard": (3, 6),
        "racah_c": (3, 5), "tetrahedral": (3, 3), "out_of_scope": (3, 4), "crossover": (3, 4), "curve": (3, 4)}
    assert sum(p for c, (p, _) in gen.COUNTS.items() if c in BASE) == 25
    assert sum(q for c, (_, q) in gen.COUNTS.items() if c in BASE) == 32
    assert {c: gen.COUNTS[c] for c in gen.EXTRA_CLASSES} == {"literature_all": (10, 18), "batch": (3, 0),
                                                           "pairing": (1, 0)}
    assert set(gen.CONF_DROPPED) == {"closed_form", "batch", "pairing"}  # the pilot-only classes
    # the rng_for indices of 0-8 are fixed
    assert CLASSES == BASE + gen.EXTRA_CLASSES + gen.TAIL_CLASSES and BASE[-1] == "curve"
    assert gen.SEED == 20261025


def test_subtype_counts(records):
    def sub(name, cls):
        return sorted(r["subtype"] for r in split(records, name) if r["class"] == cls)
    assert sub("pilot", "closed_form") == ["d3", "d8"]
    assert sub("confirmatory", "closed_form") == []  # pilot only
    assert sub("pilot", "numerical") == ["d2", "d2", "d7"]
    assert sub("confirmatory", "numerical") == ["d2"] * 3 + ["d7"] * 3
    assert sub("pilot", "racah_c") == ["d3"] * 3 and sub("confirmatory", "racah_c") == ["d3"] * 5
    assert sub("pilot", "experimental") == ["d3", "d8"] and len(sub("confirmatory", "experimental")) == 0
    assert sub("confirmatory", "numerical_hard") == sorted(f"d{d}_{m}" for d in (4, 5, 6)
                                                           for m in ("crossover", "low_spin"))
    assert sub("confirmatory", "crossover") == ["d4", "d5", "d6", "d7"]
    assert len(set(sub("pilot", "crossover"))) == 3 and len(set(sub("pilot", "curve"))) == 3
    assert len(set(sub("confirmatory", "curve"))) == 4
    assert set(sub("confirmatory", "curve")) <= {f"d{d}" for d in range(3, 8)}
    assert sub("pilot", "out_of_scope") == ["charge_transfer", "jahn_teller", "jahn_teller"]
    assert sub("confirmatory", "out_of_scope") == ["charge_transfer"] * 2 + ["jahn_teller"] * 2
    assert sub("pilot", "tetrahedral") == ["d7", "d8", "d8"]
    assert sub("confirmatory", "tetrahedral") == ["d7", "d7", "d8"]


def test_schema_and_ids(records):
    ids = [r["id"] for r in records]
    assert len(set(ids)) == len(ids)
    assert not failing(records, lambda r: set(r) == FIELDS)
    assert not failing(records, lambda r: re.fullmatch(r"[PC]-[a-z_]+-\d\d", r["id"])
                       and r["id"].startswith("P" if r["split"] == "pilot" else "C")
                       and r["id"].split("-")[1] == r["class"])
    def has_bands(r):
        return r["class"] not in ("crossover", "curve")

    assert not failing(records, lambda r: not has_bands(r)
                       or (r["bands_cm1"] == sorted(r["bands_cm1"]) and len(r["bands_cm1"]) >= 2))
    assert not failing(records, lambda r: has_bands(r) or r["bands_cm1"] == [])
    assert not failing(records, lambda r: set(r["reference"]) == {"Dq", "B", "C"})
    def fit_tol(r):
        return r["class"] not in ("experimental", "curve")

    assert not failing(records, lambda r: not fit_tol(r) or r["tolerance"] == {"Dq": 0.02, "B": 0.05, "C": 0.10})
    assert not failing(records, lambda r: r["class"] != "experimental"
                       or r["tolerance"] == {"Dq": 0.05, "B": 0.10, "C": None})
    assert not failing(records, lambda r: r["class"] != "curve" or r["tolerance"] == {
        "Dq": None, "B": None, "C": None, "curve_abs": 0.3, "curve_rel": 0.03})
    assert not failing(records, lambda r: not (has_bands(r) and r["class"] in ("closed_form", "numerical", "racah_c",
                                                                               "numerical_hard", "tetrahedral"))
                       or all(x % 10 == 0 for x in r["bands_cm1"]))
    required = {"closed_form": ["Dq", "B"], "numerical": ["Dq", "B"], "numerical_hard": ["Dq", "B"],
                "racah_c": ["Dq", "B", "C"], "experimental": ["Dq", "B"], "tetrahedral": ["Dq", "B"],
                "out_of_scope": [], "crossover": ["Dq"], "curve": []}
    assert not failing(records, lambda r: r["required"] == required[r["class"]])
    assert not failing(records, lambda r: r["expect_out_of_scope"] == (r["class"] == "out_of_scope"))
    assert not failing(records, lambda r: (r["system"] is not None) == (r["class"] == "experimental"))
    oracle = {"closed_form": "closed_form", "experimental": "closed_form", "out_of_scope": "none"}
    assert not failing(records, lambda r: r["oracle"] == oracle.get(r["class"], "forward_model"))
    assert not failing(records, lambda r: r["answer_schema"] == ("curve" if r["class"] == "curve" else "fit"))
    assert not failing(records, lambda r: (r["params"] is not None)
                       == (r["class"] in ("numerical_hard", "crossover", "curve")))
    assert not failing(records, lambda r: (r["reference_curve"] is not None) == (r["class"] == "curve"))
    assert not failing(records, lambda r: r["geometry"]
                       == {"tetrahedral": "Td", "out_of_scope": r["geometry"]}.get(r["class"], "Oh"))


def test_reference_null_pattern(records):
    def ok(r):
        ref = r["reference"]
        if r["required"] == []:
            return all(v is None for v in ref.values())
        if "C" in r["required"]:
            return all(isinstance(ref[k], float) and ref[k] > 0 for k in ("Dq", "B", "C"))
        if r["required"] == ["Dq"]:  # crossover: B and C are inputs (params), not references
            return ref["B"] is None and ref["C"] is None and isinstance(ref["Dq"], float) and ref["Dq"] > 0
        return ref["C"] is None and all(isinstance(ref[k], float) and ref[k] > 0 for k in ("Dq", "B"))
    assert not failing(records, ok)


# ----------------------------------------------------------------------------- disjointness

def _inputs(r):
    """What defines a task, whatever its reference: (class, d, drawn inputs)."""
    p = r["params"] or {}
    if r["class"] == "crossover":
        return (r["class"], r["d_count"], p["B"], p["C"])
    if r["class"] == "curve":
        return (r["class"], r["d_count"], p["B"], p["C"], tuple(p["dq_over_b"]))
    return (r["class"], r["d_count"], tuple(r["reference"][k] for k in ("Dq", "B", "C")), tuple(r["bands_cm1"]))


def test_pilot_and_confirmatory_are_disjoint(records):
    pilot, conf = split(records, "pilot"), split(records, "confirmatory")
    overlaps = {
        "ids": len({r["id"] for r in pilot} & {r["id"] for r in conf}),
        "systems": len({r["system"] for r in pilot if r["system"]} & {r["system"] for r in conf if r["system"]}),
        "inputs": len({_inputs(r) for r in pilot} & {_inputs(r) for r in conf}),
        "bands": len({(r["class"], tuple(r["bands_cm1"])) for r in pilot if r["bands_cm1"]}
                     & {(r["class"], tuple(r["bands_cm1"])) for r in conf if r["bands_cm1"]}),
        "prompts": len({r["prompt"] for r in pilot} & {r["prompt"] for r in conf}),
    }
    assert overlaps == dict.fromkeys(overlaps, 0)
    # no near-duplicate (Dq, B) across the splits, within a class and subtype, for drawn tasks with a Dq and B reference
    def drawn(r):
        return r["oracle"] == "forward_model" and r["reference"]["B"] is not None

    for p in filter(drawn, pilot):
        for c in filter(drawn, conf):
            if (p["class"], p["subtype"]) != (c["class"], c["subtype"]):
                continue
            near = (abs(p["reference"]["Dq"] - c["reference"]["Dq"]) / c["reference"]["Dq"] < 0.03
                    and abs(p["reference"]["B"] - c["reference"]["B"]) / c["reference"]["B"] < 0.04)
            assert not near, f"{p['id']} and {c['id']} are near-duplicates"
    # crossover and curve: no near-duplicate (B, C) of the same d
    for cls in ("crossover", "curve"):
        for p in (r for r in pilot if r["class"] == cls):
            for c in (r for r in conf if r["class"] == cls and r["d_count"] == p["d_count"]):
                near = (abs(p["params"]["B"] - c["params"]["B"]) / c["params"]["B"] < 0.03
                        and abs(p["params"]["C"] - c["params"]["C"]) / c["params"]["C"] < 0.04)
                assert not near, f"{p['id']} and {c['id']} are near-duplicates"


# ----------------------------------------------------------------------------- oracles

def test_check_oracle_requires_out(capsys):
    from tsbench.tasks.oracles import check
    with pytest.raises(SystemExit):
        check.main([])
    assert "--out" in capsys.readouterr().err


def _forward(d, dq, b, c):
    comp = pytest.importorskip("tanabesugano.mcp._compute")
    _, cands = comp.transition_candidates(comp.compute_point(d, dq, b, c), spin_allowed_only=False)
    allowed = [e for e, _a, s in cands if s]
    forb = [(e, a) for e, a, s in cands if not s]
    return allowed, forb


def test_closed_form_references_pass_oracle(records):
    def ok(r):
        cf = dq_b(*r["bands_cm1"])
        ref = r["reference"]
        if not (abs(cf.dq_from_quadratic - ref["Dq"]) < 0.01 and abs(cf.b_from_quadratic - ref["B"]) < 0.01):
            return False
        # the forward model with the reference parameters reproduces the printed bands. The reference is the closed
        # form of the rounded bands, which may sit up to half the tolerance from the generating parameters, so the
        # bound is 1 % of the band, not the 5 cm-1 of the rounding itself
        allowed, _ = _forward(r["d_count"], ref["Dq"], ref["B"], 4.4 * ref["B"])
        return all(abs(a - b) <= 0.01 * b for a, b in zip(allowed[:3], r["bands_cm1"], strict=False))
    sel = Records(r for r in records if r["class"] == "closed_form")
    assert not failing(sel, ok)


def test_numerical_and_tetrahedral_references_pass_forward_model(records):
    def ok(r):
        ref = r["reference"]
        dh = r["d_count"] if r["class"] == "numerical" else 10 - r["d_count"]
        bands = r["bands_cm1"]
        for cb in (4.0, 4.8):  # the spin-allowed manifold must not depend on C
            allowed, _ = _forward(dh, ref["Dq"], ref["B"], cb * ref["B"])
            if not all(abs(a - b) <= 5.0 + 1e-6 for a, b in zip(allowed[:3], bands, strict=False)):
                return False
        return len(allowed) == 3 and len(bands) == 3
    sel = Records(r for r in records if r["class"] in ("numerical", "tetrahedral"))
    assert not failing(sel, ok)


def test_numerical_d7_is_high_spin_with_margin(records):
    comp = pytest.importorskip("tanabesugano.mcp._compute")

    def ok(r):
        ref = r["reference"]
        c = 4.4 * ref["B"]
        strong = comp.ground_term(comp.compute_point(7, comp.STRONG_FIELD_DQ_CM1, ref["B"], c))[0]
        return ref["Dq"] <= 0.85 * comp.crossover_dq(7, ref["B"], c, strong) and \
            comp.ground_term(comp.compute_point(7, ref["Dq"], ref["B"], c))[0] != strong
    sel = Records(r for r in records if r["class"] == "numerical" and r["subtype"] == "d7")
    assert len(sel) == 4 and not failing(sel, ok)


def test_racah_c_references_pass_forward_model(records):
    def ok(r):
        ref = r["reference"]
        allowed, forb = _forward(3, ref["Dq"], ref["B"], ref["C"])
        expected = sorted(allowed[:3] + [forb[0][0]])
        return "2_E" in forb[0][1] and len(r["bands_cm1"]) == 4 and \
            all(abs(a - b) <= 5.0 + 1e-6 for a, b in zip(expected, r["bands_cm1"], strict=False))
    sel = Records(r for r in records if r["class"] == "racah_c")
    assert not failing(sel, ok)


def test_experimental_references_pass_closed_form_and_match_the_table(records):
    rows = {}
    with check.DATA.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            rows[row["system"]] = row

    def ok(r):
        b = r["bands_cm1"]
        row = rows[r["system"]]
        if check.D_COUNT[row["config"]] != r["d_count"]:
            return False
        if [float(row[k].lstrip("≈")) for k in ("band1_cm-1", "band2_cm-1", "band3_cm-1")[: len(b)]] != b:
            return False
        if len(b) == 3:
            cf = dq_b(*b)
            dq, bb = cf.dq_from_quadratic, cf.b_from_quadratic
        else:
            dq, bb = dq_b_two_band(*b)
        return not math.isnan(dq) and abs(dq - r["reference"]["Dq"]) < 0.01 and abs(bb - r["reference"]["B"]) < 0.01
    sel = Records(r for r in records if r["class"] == "experimental")
    assert len(sel) == 2 and not failing(sel, ok)  # pilot only


def test_out_of_scope_records_have_no_reference(records):
    sel = Records(r for r in records if r["class"] == "out_of_scope")
    assert len(sel) == 7  # 3 in the pilot, 4 in the confirmatory split
    assert not failing(sel, lambda r: r["reference"] == {"Dq": None, "B": None, "C": None} and r["expect_out_of_scope"]
                       and r["oracle"] == "none" and r["required"] == [])


def test_out_of_scope_templates_are_not_shared_between_splits(records):
    """Every template is used once, so a template (the same band positions up to +-4 %) is never in both splits."""
    sel = [r for r in records if r["class"] == "out_of_scope"]
    templates = gen.CT_TEMPLATES + gen.JT_TEMPLATES
    assert len(sel) == len(templates) == 7


# ---- numerical_hard

def test_numerical_hard_spin_state_window_and_bands(records):
    comp = pytest.importorskip("tanabesugano.mcp._compute")
    sel = Records(r for r in records if r["class"] == "numerical_hard")

    def ok(r):
        d, ref, p = r["d_count"], r["reference"], r["params"]
        b, dq, ratio = ref["B"], ref["Dq"], p["c_over_b"]
        c = ratio * b
        if d not in (4, 5, 6) or not (4.0 <= ratio <= 4.8):
            return False
        strong = comp.ground_term(comp.compute_point(d, comp.STRONG_FIELD_DQ_CM1, b, c))[0]
        x = comp.crossover_dq(d, b, c, strong, tol=0.05)
        # spin state: the drawn Dq is low-spin, and (near) within 10 % above the crossover or clearly beyond it
        if comp.ground_term(comp.compute_point(d, dq, b, c))[0] != strong:
            return False
        window = (1.0, 1.10 + 1e-3) if p["mode"] == "crossover" else (1.25 - 1e-3, 1.80 + 1e-3)
        if not (window[0] <= dq / x <= window[1]) or r["subtype"] != f"d{d}_{p['mode']}":
            return False
        # the printed bands are the three lowest spin-allowed transitions from that ground term
        _, cands = comp.transition_candidates(comp.compute_point(d, dq, b, c))
        es = [e for e, _a, _s in cands][:3]
        spacing_ok = min(b2 - b1 for b1, b2 in zip(es, es[1:], strict=False)) >= gen.HARD_MIN_SPACING
        return (len(r["bands_cm1"]) == 3 and spacing_ok
                and all(abs(a - e) <= 5.0 + 1e-6 for a, e in zip(r["bands_cm1"], es, strict=False)))
    assert not failing(sel, ok)
    for name in ("pilot", "confirmatory"):
        modes = [r["params"]["mode"] for r in split(sel, name)]
        assert modes.count("crossover") >= len(modes) // 2 and modes.count("low_spin") >= len(modes) // 3
    conf_modes = [r["params"]["mode"] for r in split(sel, "confirmatory")]
    assert conf_modes.count("crossover") == conf_modes.count("low_spin") == 3


def test_numerical_hard_bands_identify_dq_and_b(records):
    """Forward-model identifiability: a multi-start fit over both spin regimes finds no other (Dq, B)."""
    pytest.importorskip("tanabesugano.mcp._compute")
    sel = Records(r for r in records if r["class"] == "numerical_hard")
    def ambiguous(r):
        return numhard.hard_ambiguous(r["d_count"], r["params"]["c_over_b"], r["bands_cm1"],
                                  r["reference"]["Dq"], r["reference"]["B"])

    assert not failing(sel, lambda r: not ambiguous(r))
    # and the search does find the truth (it is not vacuous): one solution is within half the tolerance of it
    def finds_truth(r):
        sols = numhard.hard_solutions(r["d_count"], r["params"]["c_over_b"], r["bands_cm1"])
        return any(abs(s[0] - r["reference"]["Dq"]) / r["reference"]["Dq"] <= 0.01
                   and abs(s[1] - r["reference"]["B"]) / r["reference"]["B"] <= 0.025 for s in sols)
    assert not failing(sel, finds_truth)


def test_hard_identifiability_check_detects_a_wrong_answer():
    """The check flags a draw whose printed bands are also produced by another (Dq, B): it is not vacuous."""
    pytest.importorskip("tanabesugano.mcp._compute")
    # bands of (Dq, B) = (3000, 700), d6, C/B = 4.4; asked for the truth (2500, 700): it is outside half the tolerance
    comp = pytest.importorskip("tanabesugano.mcp._compute")
    _, cands = comp.transition_candidates(comp.compute_point(6, 3000.0, 700.0, 4.4 * 700.0))
    bands = [round(e / 10) * 10 for e, _a, _s in cands][:3]
    assert numhard.hard_ambiguous(6, 4.4, bands, 2500.0, 700.0)
    assert not numhard.hard_ambiguous(6, 4.4, bands, 3000.0, 700.0)


# ---- crossover

def test_crossover_references_pass_crossover_dq(records):
    comp = pytest.importorskip("tanabesugano.mcp._compute")
    sel = Records(r for r in records if r["class"] == "crossover")

    def ok(r):
        d, b, c = r["d_count"], r["params"]["B"], r["params"]["C"]
        if not (d in (4, 5, 6, 7) and 3.8 <= c / b <= 5.0 and r["bands_cm1"] == []):
            return False
        weak = comp.reference_ground_term(d, b, c, "high")
        strong = comp.ground_term(comp.compute_point(d, comp.STRONG_FIELD_DQ_CM1, b, c))[0]
        x = comp.crossover_dq(d, b, c, strong, tol=0.05)
        if weak == strong or abs(x - r["reference"]["Dq"]) > 0.01:
            return False
        # just below: high-spin ground term; just above: low-spin
        if comp.ground_term(comp.compute_point(d, 0.99 * x, b, c))[0] != weak:
            return False
        if comp.ground_term(comp.compute_point(d, 1.01 * x, b, c))[0] != strong:
            return False
        # exactly one ground-term change over the whole Dq range, at the C/B drawn
        return len(common.ground_sequence(d, b, c)) == 2
    assert not failing(sel, ok)


def test_crossover_prompt_states_b_and_c_and_units(records):
    def ok(r):
        text = r["prompt"].replace(common.NBSP, " ").replace(" ", "")
        b, c = r["params"]["B"], r["params"]["C"]
        return (f"{int(b)}" in text and f"{int(c)}" in text
                and "Dq" in text and "cm⁻¹" in text and f"d{r['d_count']}" in text)
    assert not failing([r for r in records if r["class"] == "crossover"], ok)


def test_crossover_c_over_b_is_drawn_away_from_the_textbook_range(records):
    ratios = [r["params"]["C"] / r["params"]["B"] for r in records if r["class"] == "crossover"]
    assert len(ratios) == 7 and all(3.8 - 1e-3 <= x <= 5.0 + 1e-3 for x in ratios)
    assert any(x < 4.0 or x > 4.5 for x in ratios)


# ---- curve

def test_curve_references_pass_compute_point(records):
    comp = pytest.importorskip("tanabesugano.mcp._compute")
    sel = Records(r for r in records if r["class"] == "curve")

    def ok(r):
        d, p = r["d_count"], r["params"]
        pts = r["reference_curve"]
        xs = p["dq_over_b"]
        if not (3 <= d <= 7 and len(xs) == 3 and len(pts) == 9 and 4.0 <= p["C"] / p["B"] <= 4.8 + 1e-3):
            return False
        if any(b - a < 0.2 for a, b in zip(xs, xs[1:], strict=False)) or xs != sorted(xs):
            return False
        for x in xs:
            pt = comp.compute_point(d, x * p["B"], p["B"], p["C"])
            lv = sorted(e for vals in pt.values() for e in vals)
            rel = [(e - lv[0]) / p["B"] for e in lv[1:] if e - lv[0] > 1e-6]
            mine = [q["e_over_b"] for q in pts if q["dq_over_b"] == x]
            if (len(mine) != 3 or mine != sorted(mine)
                    or any(abs(m - w) > 1e-3 for m, w in zip(mine, rel[:3], strict=False))):
                return False
            if rel[0] < gen.CURVE_MIN_E1 or rel[3] - rel[2] < gen.CURVE_GAP_34:
                return False
            if d >= 4:
                strong = comp.ground_term(comp.compute_point(d, comp.STRONG_FIELD_DQ_CM1, p["B"], p["C"]))[0]
                xc = comp.crossover_dq(d, p["B"], p["C"], strong, tol=0.05) / p["B"]
                if abs(x - xc) < gen.CURVE_X_TO_CROSSOVER:
                    return False
        return all(q["term"] for q in pts)
    assert not failing(sel, ok)


def test_curve_prompt_states_inputs(records):
    def ok(r):
        text = r["prompt"].replace(common.NBSP, " ").replace(" ", "")
        p = r["params"]
        return (f"{int(p['B'])}" in text and f"{int(p['C'])}" in text
                and all(f"{x:.2f}" in text for x in p["dq_over_b"])
                and f"d{r['d_count']}" in text and "E/B" in text)
    assert not failing([r for r in records if r["class"] == "curve"], ok)


def test_curve_reference_is_accepted_by_the_scorer(records):
    from tsbench.score.numeric import score_curve
    sel = Records(r for r in records if r["class"] == "curve")
    assert not failing(sel, lambda r: score_curve(r, {"points": list(r["reference_curve"])})["correct"])


def test_parameter_ranges_are_plausible(records):
    free_ion = common.FREE_ION_B

    def ok(r):
        if r["class"] in ("crossover", "curve"):
            return r["params"]["B"] < free_ion.get(r["d_count"], 1150.0)
        ref = r["reference"]
        if r["oracle"] != "forward_model" and r["class"] != "closed_form":
            return True
        d = r["d_count"]
        if not (ref["B"] < free_ion[d]):
            return False
        if ref["C"] is not None and not (4.0 <= ref["C"] / ref["B"] <= 4.8 + 1e-3):
            return False
        return True
    assert not failing(records, ok)
    tetra = [r for r in records if r["class"] == "tetrahedral"]
    assert not failing(tetra, lambda r: 300 <= r["reference"]["Dq"] <= 500)


# ----------------------------------------------------------------------------- prompts

FORBIDDEN = ("tanabe", "sugano", "mcp", "python", "tool", "solver", "fit_spectrum", "numpy", "scipy", "ts_", "claude")
NUMBER = re.compile(r"(?<![A-Za-z(])\d+(?:[  ]\d{3})*(?:\.\d+)?")


def test_prompts_name_no_tool_and_no_reference(records):
    def numbers(text):
        return [float(re.sub(r"[  ]", "", m)) for m in NUMBER.findall(text)]

    def no_names(r):
        return not any(w in r["prompt"].lower() for w in FORBIDDEN)

    assert not failing(records, no_names)

    def no_ref(r):
        nums = numbers(r["prompt"])
        refs = [v for v in r["reference"].values() if v is not None]
        return not any(abs(n - v) < 0.5 for n in nums for v in refs)
    assert not failing(records, no_ref)

    def has_bands(r):
        nums = numbers(r["prompt"])
        return all(any(abs(n - b) < 0.5 for n in nums) for b in r["bands_cm1"])
    assert not failing(records, has_bands)
    assert not failing(records, lambda r: r["prompt"].rstrip().endswith((".", "?")))
    # the curve answer is not in any prompt either
    def no_curve_values(r):
        nums = numbers(r["prompt"])
        return not any(abs(n - q["e_over_b"]) < 0.005 for n in nums for q in (r["reference_curve"] or []))
    assert not failing(records, no_curve_values)


def test_numerical_hard_prompt_states_c_over_b(records):
    def ok(r):
        return f"C/B = {r['params']['c_over_b']:.1f}" in r["prompt"] and "spin-allowed" in r["prompt"] \
            and "three lowest" in r["prompt"]
    assert not failing([r for r in records if r["class"] == "numerical_hard"], ok)


def test_racah_c_prompt_flags_the_forbidden_band(records):
    def ok(r):
        text = r["prompt"].replace(" ", " ")
        # the band named as weak and sharp is the one that is not among the three broad bands
        weak = re.search(r"weak, sharp absorption band at ([\d ]+) cm", text)
        broad = re.search(r"bands at ([\d ]+), ([\d ]+) and ([\d ]+) cm", text)
        if not (weak and broad):
            return False
        w = float(weak.group(1).replace(" ", ""))
        b3 = [float(broad.group(i).replace(" ", "")) for i in (1, 2, 3)]
        return sorted(b3 + [w]) == r["bands_cm1"] and "spin-forbidden" in text
    assert not failing([r for r in records if r["class"] == "racah_c"], ok)


# ----------------------------------------------------------------------------- loading

def test_load_defaults_to_v2_and_counts():
    assert [len(load(s)) for s in ("pilot", "confirmatory")] == [50, 55]
    recs = load("pilot")
    assert {r["split"] for r in recs} == {"pilot"}
    assert [r["class"] for r in recs[:9]] == list(BASE)  # round-robin: the first nine cover every BASE class
    assert {r["class"] for r in recs[:25]} == set(BASE)
    assert {r["class"] for r in recs[25:]} == set(gen.EXTRA_CLASSES) | set(gen.TAIL_CLASSES)
    assert load("pilot") == load("pilot", version="v2")


def test_load_confirmatory_works_and_is_not_inspected():
    recs = load("confirmatory")
    n, splits = len(recs), {r["split"] for r in recs}
    assert n == 55 and splits == {"confirmatory"}


def test_load_rejects_unknown_split_version_and_tampering(tmp_path, monkeypatch):
    with pytest.raises(ValueError):
        load("all")
    for version in ("v1", "v3"):  # task set v2 is the only version
        with pytest.raises(ValueError):
            load("pilot", version=version)
    import tsbench.tasks as pkg
    tampered = tmp_path / "tasks.jsonl"
    tampered.write_bytes(TASKS_PATH.read_bytes() + b"\n")
    monkeypatch.setattr(pkg, "TASKS_PATH", tampered)
    with pytest.raises(ValueError):
        pkg.load("pilot")


@pytest.fixture
def small_set(tmp_path, monkeypatch):
    """A two-record task set with its hash file, in place of the committed one."""
    import tsbench.tasks as pkg
    tasks, hashes = tmp_path / "tasks.jsonl", tmp_path / "tasks.sha256"
    tasks.write_text('{"id": "a", "split": "pilot"}\n\n{"id": "b", "split": "confirmatory"}\n', encoding="utf-8")
    hashes.write_text(f"{hashlib.sha256(tasks.read_bytes()).hexdigest()}  tasks.jsonl\n", encoding="utf-8")
    monkeypatch.setattr(pkg, "TASKS_PATH", tasks)
    monkeypatch.setattr(pkg, "HASH_PATH", hashes)
    return pkg, tasks, hashes


def test_load_reads_the_records_of_one_split_and_skips_blank_lines(small_set):
    pkg, _, _ = small_set
    assert pkg.load("pilot") == [{"id": "a", "split": "pilot"}]
    assert pkg.load("confirmatory") == [{"id": "b", "split": "confirmatory"}]


def test_the_error_messages_of_load_say_what_is_wrong(small_set):
    pkg, tasks, hashes = small_set
    with pytest.raises(ValueError, match=r"^split must be one of \('pilot', 'confirmatory'\), got 'all'$"):
        pkg.load("all")
    for call in (pkg.tasks_path, pkg.hash_path):
        with pytest.raises(ValueError, match=r"^version must be one of \('v2',\), got 'v1'$"):
            call("v1")
    with pytest.raises(ValueError, match=r"^version must be one of \('v2',\), got 'v3'$"):
        pkg.load("pilot", version="v3")
    tasks.write_bytes(tasks.read_bytes() + b"\n")
    with pytest.raises(ValueError, match=r"^tasks\.jsonl \(v2\) does not match its tasks\.sha256; "
                                         r"regenerate or restore it$"):
        pkg.load("pilot")
    hashes.write_text("abc  other.jsonl\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"^.*tasks\.sha256 has no entry for tasks\.jsonl$"):
        pkg.load("pilot")


def test_the_hash_file_is_split_at_the_first_double_space(small_set):
    pkg, tasks, hashes = small_set
    digest = hashlib.sha256(tasks.read_bytes()).hexdigest()
    # a first line whose name ends in tasks.jsonl, but is "other  tasks.jsonl": it is not the entry
    hashes.write_text(f"{'0' * 64}  other  tasks.jsonl\n{digest}  tasks.jsonl\n", encoding="utf-8")
    assert pkg.load("pilot") == [{"id": "a", "split": "pilot"}]


def test_the_hash_file_is_read_as_utf8_whatever_the_locale(small_set, ascii_python):
    pkg, tasks, hashes = small_set
    digest = hashlib.sha256(tasks.read_bytes()).hexdigest()
    hashes.write_text(f"{'0' * 64}  café.jsonl\n{digest}  tasks.jsonl\n", encoding="utf-8")
    code = (
        "import pathlib, sys\n"
        "import tsbench.tasks as pkg\n"
        "pkg.TASKS_PATH, pkg.HASH_PATH = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])\n"
        "print(len(pkg.load('pilot')))\n"
    )
    done = ascii_python(code, tasks, hashes)
    assert done.returncode == 0, done.stderr[-1500:]
    assert done.stdout.strip() == "1"


def test_fixed_pilot_systems_are_frozen_and_never_confirmatory():
    """The fixed pilot systems are a tuple of names, and none of them is a confirmatory system."""
    from tsbench.tasks.common import FIXED_PILOT_SYSTEMS, _fixed_pilot_systems
    assert len(FIXED_PILOT_SYSTEMS) == len(set(FIXED_PILOT_SYSTEMS)) == 2
    assert _fixed_pilot_systems() == set(FIXED_PILOT_SYSTEMS)
    assert not set(FIXED_PILOT_SYSTEMS) & {r["system"] for r in load("confirmatory")}


def test_rubric_documents_v2(records):
    text = (TASK_DATA / "rubric.md").read_text(encoding="utf-8")
    for needle in ("20261025", "## Pilot-only classes", "## Separation of systems", "curve.schema.json",
                   "numerical_hard", "crossover",
                   "answer_schema", "0.3", "tolerance", "## literature_all", "## batch", "## pairing",
                   "## Known discrepancies", "fit at bound", "batch.schema.json", "pairing.schema.json"):
        assert needle in text, needle
    _, excluded = experimental._experimental_rows()
    assert excluded and all(name in text for name, _d, _why in excluded)
    assert "20261024" in text  # the seed the fixed pilot systems were drawn with
    for word in ("Changes", "calibration run", "2026-10-2", "no longer", "manuscript", "pilot/"):
        assert word not in text, word


# ----------------------------------------------------------------------------- two-band closed form

@pytest.mark.parametrize("dq,b", [(1700, 700), (860, 940), (1230, 640), (2100, 600), (990, 880)])
def test_two_band_closed_form_roundtrip_against_forward_model(dq, b):
    comp = pytest.importorskip("tanabesugano.mcp._compute")
    for d, mult in ((3, "4"), (8, "3")):
        pt = comp.compute_point(d, dq, b, 4.2 * b)
        ground = min(min(v) for v in pt.values())
        lv = sorted(e - ground for k, v in pt.items() if k.startswith(mult + "_") for e in v)
        nu = [x for x in lv if x > 1e-6][:3]
        dq2, b2 = dq_b_two_band(nu[0], nu[1])
        assert dq2 == pytest.approx(dq, abs=0.1)
        assert b2 == pytest.approx(b, abs=0.1)
        # consistent with the three-band relation
        assert b2 == pytest.approx(dq_b(*nu).b_from_quadratic, abs=0.1)


def test_two_band_closed_form_rejects_bad_input():
    with pytest.raises(ValueError):
        dq_b_two_band(10000, 9000)    # not ascending
    with pytest.raises(ValueError):
        dq_b_two_band(10000, 18000)   # nu2 = 1.8 nu1: B undefined
    with pytest.raises(ValueError):
        dq_b_two_band(10000, 19000)   # 1.8 nu1 < nu2 < 2 nu1: B negative


# ----------------------------------------------------------------------------- the BASE_CLASSES records are pinned

# sha256 of the canonical lines of the BASE_CLASSES records (pilot first, then confirmatory, file order), without the
# `numerical_hard` class, whose prompts carry the spin state and ground term (rubric.md, "numerical_hard prompts").
# The other classes must never change them.
FIXED_CLASS = "numerical_hard"
BASE_FILE_SHA256 = "90e83259f854c0d3122900ed94820a0586673163961deaee1d7472b5de34127d"
BASE_PILOT_SHA256 = "f4b31a5bfe18286d351496f277c4b14eb637c98a9f0e7332d39cdf423fe9c7ec"
BASE_CONFIRMATORY_SHA256 = "1d5c4757904a3b5f6064e14aad5529aa53fa03bd1efb3c92d82d4a08ea7e1db0"


def _canon(rec: dict) -> str:
    return json.dumps(rec, sort_keys=True, ensure_ascii=False)


def test_base_records_are_byte_identical_to_the_pinned_digests(all_records):
    base = [r for r in all_records if r["class"] in BASE and r["class"] != FIXED_CLASS]
    assert len(base) == 48
    text = "".join(_canon(r) + "\n" for r in base)
    assert sha(text.encode("utf-8")) == BASE_FILE_SHA256
    for name, want in (("pilot", BASE_PILOT_SHA256), ("confirmatory", BASE_CONFIRMATORY_SHA256)):
        part = "".join(_canon(r) + "\n" for r in base if r["split"] == name)
        assert sha(part.encode("utf-8")) == want
    # and the whole BASE set (fixed class included) is the first 25 / 32 records of its split, in order
    base_all = [r for r in all_records if r["class"] in BASE]
    assert len(base_all) == 57
    assert [r["id"] for r in all_records[:25]] == [r["id"] for r in base_all if r["split"] == "pilot"]
    first_conf = [r["id"] for r in all_records if r["split"] == "confirmatory"][:32]
    assert first_conf == [r["id"] for r in base_all if r["split"] == "confirmatory"]


def _git_head_tasks() -> str | None:
    import subprocess
    try:
        out = subprocess.run(["git", "show", "HEAD:src/tsbench/data/tasks/tasks.jsonl"], capture_output=True, cwd=HERE,
                             timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.decode("utf-8") if out.returncode == 0 else None


def test_pilot_block_is_byte_identical_to_git_head_and_the_other_confirmatory_records_too():
    """Against the committed task file (git HEAD): all pilot lines are byte-identical and in the same order. On the
    confirmatory side only `experimental` and `literature_all` may differ (separation of systems); every other
    confirmatory record is byte-identical. Failure messages carry ids and digests only."""
    head = _git_head_tasks()
    if head is None:
        pytest.skip("git history not available")
    old = [ln for ln in head.splitlines() if ln.strip()]
    new = [ln for ln in (TASK_DATA / "tasks.jsonl").read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(old) >= 105
    def parse(lns):
        return [json.loads(ln) for ln in lns]

    ro, rn = parse(old), parse(new)
    old_pilot = [ln for ln, r in zip(old, ro, strict=False) if r["split"] == "pilot"]
    new_pilot = [ln for ln, r in zip(new, rn, strict=False) if r["split"] == "pilot"]
    assert len(new_pilot) == 50
    assert [json.loads(ln)["id"] for ln in new_pilot[:len(old_pilot)]] == [json.loads(ln)["id"] for ln in old_pilot], \
        "pilot ids or order differ from HEAD"
    bad = [json.loads(o)["id"] for o, n in zip(old_pilot, new_pilot, strict=False) if o != n]
    assert not bad, f"pilot records that differ from HEAD: {bad}"
    sep = {"experimental", "literature_all", *gen.CONF_DROPPED}  # CONF_DROPPED: not in the confirmatory split
    oc = {r["id"]: ln for ln, r in zip(old, ro, strict=False) if r["split"] == "confirmatory" and r["class"] not in sep}
    nc = {r["id"]: ln for ln, r in zip(new, rn, strict=False) if r["split"] == "confirmatory" and r["class"] not in sep}
    assert set(oc) <= set(nc) | set(), "confirmatory records of other classes are missing"
    bad = [i for i in oc if oc[i] != nc[i]]
    assert not bad, f"confirmatory records of other classes that differ from HEAD: {bad}"


def test_confirmatory_split_has_no_pilot_system_and_no_system_twice(all_records):
    """Separation rule: no confirmatory task uses a pilot system, and no system appears twice. Prints nothing but counts
    and ids."""
    pilot_sys = {r["system"] for r in all_records if r["split"] == "pilot" and r["system"]}
    conf = [r for r in all_records if r["split"] == "confirmatory" and r["system"]]
    in_pilot = [r["id"] for r in conf if r["system"] in pilot_sys]
    assert not in_pilot, f"{len(in_pilot)} confirmatory tasks use a pilot system: {in_pilot}"
    twice = [r["id"] for r in conf if sum(q["system"] == r["system"] for q in conf) > 1]
    assert not twice, f"{len(twice)} confirmatory tasks share a system with another confirmatory task: {twice}"
    assert len(pilot_sys) >= 15 and len(conf) == 18  # sanity: the check is not vacuous


def test_separation_rule_and_pilot_only_classes_are_documented_in_the_rubric():
    text = (TASK_DATA / "rubric.md").read_text(encoding="utf-8")
    assert "## Separation of systems" in text and "## Pilot-only classes" in text
    assert all(f"`{c}`" in text.split("## Pilot-only classes", 1)[1].split("##", 1)[0] for c in gen.CONF_DROPPED)


def test_numerical_hard_prompts_state_spin_state_and_ground_term(all_records):
    label = {4: "³T₁g", 5: "²T₂g", 6: "¹A₁g"}
    hard = [r for r in all_records if r["class"] == FIXED_CLASS]
    assert len(hard) == 9
    bad = [r["id"] for r in hard
           if f"The complex is low-spin; its ground term is {label[r['d_count']]}." not in r["prompt"]
           or "high-spin" in r["prompt"]]
    assert not bad, f"prompts without the spin state and ground term: {bad}"


# ----------------------------------------------------------------------------- literature_all, batch, pairing

def of(records, cls):
    return Records(r for r in records if r["class"] == cls)


def test_new_classes_schema_and_ids(all_records):
    new = [r for r in all_records if r["class"] in gen.EXTRA_CLASSES]
    assert len(new) == 32
    assert not failing(new, lambda r: set(r) == FIELDS)
    assert not failing(new, lambda r: re.fullmatch(r"[PC]-[a-z_]+-\d\d", r["id"])
                       and r["id"].split("-")[1] == r["class"]
                       and r["id"].startswith("P" if r["split"] == "pilot" else "C"))
    assert not failing(new, lambda r: r["answer_schema"]
                       == {"literature_all": "fit", "batch": "batch", "pairing": "pairing"}[r["class"]])
    assert not failing(new, lambda r: r["tolerance"] == {"fit": r["tolerance"],
                                                         "batch": {"Dq": None, "B": None, "C": None, "item_rel": 0.02},
                                                      "pairing": {}}[r["answer_schema"]])
    assert not failing(new, lambda r: r["oracle"] == {"literature_all": "forward_model_lsq", "batch": "forward_model",
                                                      "pairing": "microstate_count"}[r["class"]])
    assert not failing(new, lambda r: not r["expect_out_of_scope"] and r["reference_curve"] is None)


def test_new_classes_use_their_own_streams():
    idx = {c: gen.CLASSES.index(c) for c in gen.CLASSES}
    assert [idx[c] for c in gen.BASE_CLASSES] == list(range(9))
    assert [idx[c] for c in gen.EXTRA_CLASSES] == [9, 10, 11]
    assert [idx[c] for c in gen.TAIL_CLASSES] == [12, 13]


def test_literature_all_excludes_fits_at_a_bound(all_records):
    from tsbench.tasks.classes import literature_all as L
    lit = of(all_records, "literature_all")
    assert (len(split(lit, "pilot")), len(split(lit, "confirmatory"))) == (10, 18)
    names = {r["system"] for r in lit}
    assert len(names) == 28 and not any(r["system"] is None for r in lit)

    def at_bound(r):
        ref = r["reference"]
        checks = [(ref["Dq"], L.DQ_BOUNDS), (ref["B"], L.B_BOUNDS)]
        if ref["C"] is not None:
            checks.append((ref["C"] / ref["B"], L.CB_BOUNDS))
        return any(abs(v - b) <= L.BOUND_REL * b for v, bounds in checks for b in bounds)
    assert not failing(lit, lambda r: not at_bound(r))
    excluded = {"[Mn(CN)6]3−", "LiGa5O8:Fe3+", "[Co(NH3)6]3+"}
    assert not (names & excluded)
    text = (TASK_DATA / "rubric.md").read_text(encoding="utf-8")
    assert all(n in text for n in excluded) and "fit at bound" in text


def test_literature_all_rubric_lists_pilot_systems_but_no_confirmatory_system(all_records):
    text = (TASK_DATA / "rubric.md").read_text(encoding="utf-8")
    lit = of(all_records, "literature_all")
    assert all(r["system"] in text for r in split(lit, "pilot"))
    # a confirmatory system may be named only if it is also named for another reason (never in the deviation table)
    table = text.split("| System | d | Status |", 1)[1].split("\n\n", 1)[0]
    assert not any(r["system"] in table for r in split(lit, "confirmatory"))


def test_batch_and_pairing_counts_and_subtypes(all_records):
    batch, pairing = of(all_records, "batch"), of(all_records, "pairing")
    assert (len(split(batch, "pilot")), len(split(batch, "confirmatory"))) == (3, 0)  # pilot only
    assert (len(split(pairing, "pilot")), len(split(pairing, "confirmatory"))) == (1, 0)
    assert {r["subtype"] for r in batch} <= {"crossover_series", "band_series"}
    assert not failing(batch, lambda r: len(r["reference"]["values"]) == 8 and r["required"] == ["values"])
    assert not failing(pairing, lambda r: set(r["reference"]) == {"nodes", "edges"} and r["d_count"] is None)
    assert sorted(r["subtype"] for r in split(pairing, "pilot")) == ["2468"]


def test_new_classes_do_not_overlap_between_splits(all_records):
    for cls in gen.EXTRA_CLASSES:
        recs = of(all_records, cls)
        pil, con = split(recs, "pilot"), split(recs, "confirmatory")
        assert not ({r["prompt"] for r in pil} & {r["prompt"] for r in con}), cls
        assert not ({r["system"] for r in pil if r["system"]} & {r["system"] for r in con if r["system"]}), cls


def test_new_class_prompts_name_no_tool(all_records):
    new = [r for r in all_records if r["class"] in gen.EXTRA_CLASSES]
    assert not failing(new, lambda r: not any(w in r["prompt"].lower() for w in FORBIDDEN))
    assert not failing(new, lambda r: r["prompt"].strip() != "")
