"""Scoring of the pairing task: node and edge sets against the microstate-count reference."""
from __future__ import annotations


def _precision_recall_f1(pred: set, ref: set) -> tuple[float, float, float]:
    tp = len(pred & ref)
    p = tp / len(pred) if pred else (1.0 if not ref else 0.0)
    r = tp / len(ref) if ref else (1.0 if not pred else 0.0)
    f = 2 * p * r / (p + r) if p + r else 0.0
    return p, r, f


def _norm_term(t) -> str:
    # tanabesugano.free_ion lists repeated terms as 2D, 2D', 2D'' (one row each); strip the primes
    return str(t).strip().replace(" ", "").rstrip("'′″")


def _nodes(items) -> set:
    """(config, term, count) with repeated rows of one term summed, so '2D, 2D′, 2D″' equals '2D x 3'."""
    counts: dict[tuple[str, str], int] = {}
    for n in items:
        if isinstance(n, dict) and type(n.get("count")) is int:
            key = (str(n.get("config")).strip().lower(), _norm_term(n.get("term")))
            counts[key] = counts.get(key, 0) + n["count"]
    return {(c, t, k) for (c, t), k in counts.items()}


def _edges(items) -> set:
    out = set()
    for e in items:
        if isinstance(e, dict):
            a, b = str(e.get("a")).strip().lower(), str(e.get("b")).strip().lower()
            out.add((*sorted((a, b)), _norm_term(e.get("term"))))
    return out


def _ground(items, configs) -> dict:
    g: dict[str, set] = {c: set() for c in configs}
    for n in items:
        if isinstance(n, dict) and n.get("ground") is True and str(n.get("config")).strip().lower() in g:
            g[str(n["config"]).strip().lower()].add(_norm_term(n.get("term")))
    return g


def score_pairing(task: dict, structured_output) -> dict:
    ref = task["reference"]
    out = structured_output if isinstance(structured_output, dict) else {}
    pn, pe = out.get("nodes"), out.get("edges")
    pn = pn if isinstance(pn, list) else []
    pe = pe if isinstance(pe, list) else []
    configs = sorted({n["config"] for n in ref["nodes"]})
    np_, nr, _ = _precision_recall_f1(_nodes(pn), _nodes(ref["nodes"]))
    ep, er, ef = _precision_recall_f1(_edges(pe), _edges(ref["edges"]))
    want = {c: {n["term"] for n in ref["nodes"] if n["config"] == c and n["ground"]} for c in configs}
    ground_ok = _ground(pn, configs) == want
    return {
        "node_precision": np_, "node_recall": nr,
        "edge_precision": ep, "edge_recall": er, "edge_f1": ef,
        "ground_correct": ground_ok,
        "correct": bool(nr == 1.0 and np_ == 1.0 and ef == 1.0 and ground_ok),
    }
