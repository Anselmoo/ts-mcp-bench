"""The "pairing" task class: free-ion LS terms of d^n and the term labels shared between configurations.

The oracle is an independent microstate count: enumerate the (M_L, M_S) microstates of d^n, then peel
off the terms. It uses no Tanabe-Sugano data, so it is a separate derivation from the MCP server's tables.
"""
from __future__ import annotations

import itertools
from collections import Counter
from functools import cache

LETTERS = "SPDFGHIKLMN"  # L = 0, 1, 2, ...
ORBITALS = [(ml, ms2) for ml in (-2, -1, 0, 1, 2) for ms2 in (1, -1)]  # ms2 = 2 * m_s

VARIANTS = {
    "pilot": [("d2", "d4", "d6", "d8")],
    "confirmatory": [("d3", "d7"), ("d2", "d3", "d7", "d8"), ("d4", "d5", "d6")],
}

PROMPT_HEAD = (
    "For the free-ion configurations {configs}, list every LS term with how often it occurs, and list the pairs "
    "of configurations that share the same term (an edge for each shared term label between two configurations). "
    "Mark the ground term of each configuration (Hund's rules)."
)
PROMPT_TAIL = {
    0: " Give the terms as nodes (config, term such as 3F, count, ground) and the shared terms as edges (a, b, term).",
    1: " Report nodes with config, term label, multiplicity count and a ground flag, and edges with the two "
       "configurations and the shared term label.",
}


def _microstate_table(n: int) -> Counter:
    """N(M_L, 2*M_S) over all C(10, n) microstates."""
    table: Counter = Counter()
    for combo in itertools.combinations(ORBITALS, n):
        table[(sum(o[0] for o in combo), sum(o[1] for o in combo))] += 1
    return table


@cache
def terms(n: int) -> dict[str, int]:
    """Term label ('3F') -> number of times it occurs in d^n, by peeling the microstate table."""
    if not 0 <= n <= 10:
        raise ValueError(f"d{n} is not a d^n configuration")
    table = _microstate_table(n)
    out: dict[str, int] = {}
    for ms2 in range(n % 2, n + 1 if n <= 5 else 10 - n + 1, 2):  # M_S >= 0 only
        for ml in range(0, 2 * n + 1):
            def g(m, s):
                return table.get((m, s), 0)
            # number of terms with exactly (L, S): the standard double difference
            k = g(ml, ms2) - g(ml + 1, ms2) - g(ml, ms2 + 2) + g(ml + 1, ms2 + 2)
            if k:
                out[f"{ms2 + 1}{LETTERS[ml]}"] = k
    return out


def n_microstates(n: int) -> int:
    return sum(c * (int(label[0]) * (2 * LETTERS.index(label[1]) + 1)) for label, c in terms(n).items())


def ground_term(n: int) -> str:
    """Hund: maximal S, then maximal L."""
    return max(terms(n), key=lambda t: (int(t[0]), LETTERS.index(t[1])))


def _d_count_of(c: str) -> int:
    return int(c[1:])


def reference(configs) -> dict:
    configs = list(configs)
    nodes = []
    for c in configs:
        g = ground_term(_d_count_of(c))
        nodes += [{"config": c, "term": t, "count": k, "ground": t == g} for t, k in terms(_d_count_of(c)).items()]
    edges = []
    for a, b in itertools.combinations(configs, 2):
        for t in sorted(set(terms(_d_count_of(a))) & set(terms(_d_count_of(b)))):
            edges.append({"a": a, "b": b, "term": t})
    return {"nodes": nodes, "edges": edges}


def _sup(c: str) -> str:
    return "d" + c[1:].translate(str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹"))


def _record(configs, split: str, rng) -> dict:
    ref = reference(configs)
    prompt = (PROMPT_HEAD.format(configs=", ".join(_sup(c) for c in configs))
              + PROMPT_TAIL[int(rng.integers(len(PROMPT_TAIL)))])
    return {
        "answer_schema": "pairing",
        "bands_cm1": [],
        "class": "pairing",
        "d_count": None,
        "expect_out_of_scope": False,
        "geometry": None,
        "oracle": "microstate_count",
        "params": {"configs": list(configs)},
        "prompt": prompt,
        "reference": ref,
        "reference_curve": None,
        "required": [],
        "subtype": "".join(c[1:] for c in configs),
        "system": None,
        "tolerance": {},
        "split": split,
    }


def make_pairing(rng) -> tuple[list[dict], list[dict]]:
    """(pilot, confirmatory): 1 pilot and 3 confirmatory records."""
    pilot = [_record(v, "pilot", rng) for v in VARIANTS["pilot"]]
    conf = [_record(v, "confirmatory", rng) for v in VARIANTS["confirmatory"]]
    return pilot, conf
