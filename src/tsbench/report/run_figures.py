"""Per-run figures of the run gallery in the "Figura" style (matplotlib + the vendored jfs helpers).

    from tsbench.report import run_figures
    ev = run_figures.evaluate(task, transcript)                   # row, answer, category, verdict, reason, metrics
    made = run_figures.make_figures(transcript_path, task, ev)    # [{"file", "title", "kind"}], SVGs in <stem>.figs/

The SVGs are written next to the transcript (`<task>-k<i>.figs/*.svg`), pilot runs only; an `index.json` there
records a key per figure (a hash of the task record and the scored run; the metrics figure also of the class medians),
so a figure is drawn again only when its own inputs change. The gallery embeds them as data URIs. Which figure a run
gets follows the task's `answer_schema`:

  fit, in scope        fit_error.svg    signed relative error per parameter, tolerance band per row, pass/fail marks
  fit, out of scope    metrics.svg      status marks + tokens/turns/cost/seconds relative to the class median
  curve                curve.svg        answer against reference points with a residual axis
  diagram              diagram.svg      the six lowest levels at nine Dq/B points with a residual axis
  batch                batch.svg        input -> result against reference with a relative-error residual axis
  pairing              pairing.svg      node and edge precision / recall as a dot plot
  no answer            no_result.svg    "no evaluable result" with the reason from scorer and taxonomy
  no task              metrics.svg

Not drawn: predicted against reference *band positions* of the fit classes (needs a forward model per run; the gallery
does not execute anything). Any failure in one figure is logged to stderr and skipped, it never stops the gallery.
matplotlib is imported lazily; without it `make_figures` returns [] (no figure).
"""
from __future__ import annotations

import hashlib
import json
import math
import pathlib
import statistics
import sys
import textwrap

from tsbench.core.api_errors import is_context_overflow
from tsbench.report import page
from tsbench.report.base import HARNESS
from tsbench.report.svg.base import fixed, significant

FIG_VERSION = 4               # cache version of the figures: raise it when a figure changes
PARAMS = ("Dq", "B", "C")
WIDTH = "single"               # 84.6 mm, single column
THEME = "neutral"
INDEX = "index.json"

VERDICTS = ("correct", "wrong", "harness", "na429", "unscored")     # the verdict of one run, words from page.STATUS
VERDICT_LABEL = {k: page.STATUS_TEXT[k] for k in VERDICTS}
VERDICT_ICON = {"correct": "✓", "wrong": "✗", "harness": "!", "na429": "⏸", "unscored": "–"}


def log(msg: str) -> None:
    print(f"figures: {msg}", file=sys.stderr)


# ------------------------------------------------------------------ scoring (same functions as scores.csv)
def _num(v):
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) else None


def run_metrics(tr) -> dict:
    """tokens, turns, cost and seconds of a transcript's result event (None where it has none)."""
    res = tr.result if isinstance(getattr(tr, "result", None), dict) else {}
    out: dict = {}
    try:
        from tsbench.score.score import usage_detail
        out["tokens"] = usage_detail(res.get("usage"))["total_tokens"] if res else None
    except Exception:
        out["tokens"] = None
    out["turns"] = _num(res.get("num_turns"))
    out["cost"] = _num(res.get("total_cost_usd"))
    ms = _num(res.get("duration_ms"))
    out["seconds"] = ms / 1000.0 if ms is not None else None
    return out


def evaluate(task: dict | None, tr) -> dict:
    """Score one transcript in memory, like tsbench.report.comparison.score_in_memory: {row, answer, category, correct,
    verdict (correct|wrong|harness|na429|unscored), reason (plain words), metrics, has_result}. Without a task the
    verdict is `unscored`."""
    from tsbench.score.score import not_evaluable_reason, score_transcript
    from tsbench.score.taxonomy import failure_category
    res = tr.result if isinstance(getattr(tr, "result", None), dict) else {}
    has_result = getattr(tr, "result", None) is not None
    ev = {"row": {}, "answer": None, "category": None, "correct": False, "verdict": "unscored", "reason": "",
          "metrics": run_metrics(tr), "has_result": has_result, "limited": None}
    if task is None:
        ev["reason"] = "no pilot task found for this run"
        return ev
    sc, answer = score_transcript(task, tr)
    row = {**sc, "has_result": has_result, "is_error": res.get("is_error") if has_result else None,
           "result_subtype": res.get("subtype"), "context_overflow": is_context_overflow(res)}
    cat = failure_category(row, task)
    limited = not_evaluable_reason(tr)
    correct = bool(sc.get("correct"))
    if limited:  # rate_limited or api_error: the scorer leaves the run out, page.STATUS['na429'] says so
        verdict = "na429"
        reason = ("HTTP 429 (rate limit)" if limited == "rate_limited" else "API error (not a model error)") \
            + ": says nothing about the model"
    elif correct:
        verdict, reason = "correct", ""
    elif cat in HARNESS:
        verdict, reason = "harness", page.CATEGORY_TEXT.get(cat, cat)
    else:
        verdict, reason = "wrong", page.CATEGORY_TEXT.get(cat, cat)
    if row.get("rescued"):
        reason = (reason + "; " if reason else "") + "answer rescued from the last StructuredOutput call"
    ev.update(row=row, answer=answer, category=cat, correct=correct, verdict=verdict, reason=reason, limited=limited)
    return ev


# ------------------------------------------------------------------ matplotlib plumbing
_MPL: dict = {}


def _matplotlib():
    """(plt, jfs) with the Figura theme set, or None when matplotlib is missing."""
    if "v" in _MPL:
        return _MPL["v"]
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        from tsbench._vendor.figura import jfs
        plt.style.use(str(pathlib.Path(jfs.__file__).with_name("jfs.mplstyle")))
        jfs.use_theme(THEME)
        plt.rcParams.update({"svg.fonttype": "none", "svg.hashsalt": "figura", "axes.unicode_minus": True})
        _MPL["v"] = (plt, jfs)
    except Exception as exc:  # noqa: BLE001
        log(f"matplotlib/jfs not available ({type(exc).__name__}: {exc}): no figures")
        _MPL["v"] = None
    return _MPL["v"]


def figures_dir_of(transcript) -> pathlib.Path:
    t = pathlib.Path(transcript)
    return (
        t.with_name(t.name[: -len(".jsonl")] + ".figs") if t.name.endswith(".jsonl") else t.with_name(t.name + ".figs")
    )


def _save(fig, path: pathlib.Path) -> None:
    plt, _ = _matplotlib()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, format="svg", metadata={"Date": None})
    plt.close(fig)


def _color(jfs, name: str) -> str:
    return jfs.COLORS[name]


def _status_style(jfs, ok: bool) -> dict:
    """Pass: filled circle in series-1. Fail: cross in series-6. Never colour alone."""
    if ok:
        return dict(marker="o", color=_color(jfs, "series-1"), mfc=_color(jfs, "series-1"), ms=3.5, mew=0.5)
    return dict(marker="X", color=_color(jfs, "series-6"), mfc=_color(jfs, "series-6"), ms=4.2, mew=0.5)


def _fmt_pct(v: float) -> str:
    return f"{fixed(v, 1, sign=True)} %" if abs(v) < 1000 else f"{fixed(v, 0, sign=True)} %"


# ------------------------------------------------------------------ figures
def fig_fit_error(task: dict, answer: dict | None, row: dict):
    """Signed relative error (answer - reference) / reference per required parameter against its tolerance band."""
    plt, jfs = _matplotlib()
    ref, tol = task.get("reference") or {}, task.get("tolerance") or {}
    params = [p for p in (task.get("required") or []) if ref.get(p) is not None]
    if not params:
        raise ValueError("no reference parameters")
    answer = answer or {}
    vals = {}
    for p in params:
        a, r = _num(answer.get(p)), ref[p]
        if a is not None and p == "Dq" and task.get("geometry") == "Td":
            a, r = abs(a), abs(r)
        vals[p] = None if a is None or r == 0 else (a - r) / abs(r) * 100.0
    tols = {p: (tol.get(p) or 0.0) * 100.0 for p in params}
    shown = [abs(v) for v in vals.values() if v is not None]
    lim = max(1.8 * max(tols.values()), min(1.2 * max(shown, default=0.0), 100.0), 1.0)
    lim = math.ceil(lim / 5.0) * 5.0 if lim > 5 else math.ceil(lim)
    fig, ax = jfs.figure(WIDTH, 16 + 9 * len(params))
    for i, p in enumerate(params):
        ax.add_patch(
            plt.Rectangle((-tols[p], i - 0.36), 2 * tols[p], 0.72, color=_color(jfs, "house-tint"), lw=0, zorder=0)
        )
        v = vals[p]
        if v is None:
            ax.text(0, i, "not given", ha="center", va="center", fontsize=6, color=_color(jfs, "series-6"))
            ax.text(lim * 1.06, i, "x  no value", ha="left", va="center", fontsize=6,
                    color=_color(jfs, "series-6"), clip_on=False)
            continue
        ok = abs(v) <= tols[p] + 1e-9
        clipped = abs(v) > lim
        x = math.copysign(lim, v) if clipped else v
        style = _status_style(jfs, ok)
        ax.plot([x], [i], ls="none", zorder=3, **style)
        label = ("ok  " if ok else "x  ") + _fmt_pct(v) + (" (off scale)" if clipped else "")
        ax.text(lim * 1.06, i, label, ha="left", va="center", fontsize=6,
                color=_color(jfs, "series-1") if ok else _color(jfs, "series-6"), clip_on=False)
    ax.axvline(0, color=_color(jfs, "ink-muted"), lw=0.5, zorder=1)
    ax.set_xlim(-lim, lim)
    ax.set_ylim(len(params) - 0.5, -0.5)
    ax.set_yticks(range(len(params)))
    ax.set_yticklabels(params)
    ax.yaxis.set_minor_locator(plt.NullLocator())
    ax.set_xlabel("Relative error (%)")
    ax.set_ylabel("Parameter")
    ax.text(0.0, 1.02, "shaded: tolerance", transform=ax.transAxes, fontsize=6, color=_color(jfs, "ink-muted"),
            va="bottom")
    return fig


def _pairs_curve(task: dict, answer: dict):
    """(x, ref, got|None) for every reference point, grouped by Dq/B like score_curve (sorted within a group)."""
    ref_pts = task.get("reference_curve") or []
    pts = [p for p in (answer or {}).get("points") or [] if isinstance(p, dict)]
    out = []
    for x in dict.fromkeys(p["dq_over_b"] for p in ref_pts):
        want = sorted(p["e_over_b"] for p in ref_pts if p["dq_over_b"] == x)
        got = sorted(
            g
            for g in (
                _num(p.get("e_over_b"))
                for p in pts
                if _num(p.get("dq_over_b")) is not None and abs(p["dq_over_b"] - x) <= 0.01
            )
            if g is not None
        )
        for i, w in enumerate(want):
            out.append((x, w, got[i] if i < len(got) else None, i))
    return out


def _pairs_diagram(task: dict, answer: dict):
    ref = task["reference"]
    pts = [p for p in (answer or {}).get("points") or [] if isinstance(p, dict)]
    out = []
    for x, want in zip(ref["grid"], ref["levels"], strict=False):
        px = [p for p in pts if _num(p.get("dq_over_b")) is not None and abs(p["dq_over_b"] - x) <= 1e-6]
        got = []
        if len(px) == 1 and isinstance(px[0].get("levels"), list):
            got = sorted(
                g for g in (_num(lv.get("e_over_b")) for lv in px[0]["levels"] if isinstance(lv, dict)) if g is not None
            )
        for i, w in enumerate(want):
            out.append((x, w, got[i] if i < len(got) else None, i))
    return out


def _overlay_with_residual(pairs, *, xlabel: str, ylabel: str, rlabel: str, band: float, height: float, lines: bool):
    plt, jfs = _matplotlib()
    fig, axs = jfs.figure(WIDTH, height, nrows=2, height_ratios=[3, 1.35], sharex=True)
    a, b = axs
    ink, s1, s6 = _color(jfs, "ink"), _color(jfs, "series-1"), _color(jfs, "series-6")
    if lines:   # reference level k as a thin line through the grid points
        for k in sorted({p[3] for p in pairs}):
            pts = sorted((p[0], p[1]) for p in pairs if p[3] == k)
            a.plot(*zip(*pts, strict=False), color=_color(jfs, "rule"), lw=0.5, zorder=1)
    a.plot([p[0] for p in pairs], [p[1] for p in pairs], ls="none", marker="o", ms=4.2, mfc="none", mec=ink, mew=0.5,
           zorder=2)
    got = [p for p in pairs if p[2] is not None]
    a.plot([p[0] for p in got], [p[2] for p in got], ls="none", marker="o", ms=2.2, mfc=s1, mec=s1, mew=0.5, zorder=3)
    a.set_ylabel(ylabel)
    lo, hi = a.get_xlim()
    a.text(0.02, 0.97, "o reference", transform=a.transAxes, fontsize=6, color=ink, va="top")
    a.text(0.02, 0.86, "• answer", transform=a.transAxes, fontsize=6, color=s1, va="top")
    b.axhspan(-band, band, color=_color(jfs, "house-tint"), lw=0, zorder=0)
    b.axhline(0, color=_color(jfs, "ink-muted"), lw=0.5, zorder=1)
    ok = [p for p in got if abs(p[2] - p[1]) <= band + 1e-9 or (p[1] and abs(p[2] - p[1]) / abs(p[1]) <= 0.03 + 1e-9)]
    bad = [p for p in got if p not in ok]
    if ok:
        b.plot([p[0] for p in ok], [p[2] - p[1] for p in ok], ls="none", **_status_style(jfs, True))
    if bad:
        res = [p[2] - p[1] for p in bad]
        top = max(3 * band, 1.0)
        b.plot([p[0] for p in bad], [max(-top, min(top, r)) for r in res], ls="none", **_status_style(jfs, False))
        if any(abs(r) > top for r in res):
            b.text(
                0.02,
                0.07,
                "marks on the edge: off scale",
                transform=b.transAxes,
                fontsize=6,
                color=_color(jfs, "ink-muted"),
            )
    miss = len(pairs) - len(got)
    if miss:
        b.text(0.98, 0.93, f"{miss} of {len(pairs)} values missing", transform=b.transAxes, fontsize=6, ha="right",
               va="top", color=s6)
    b.set_ylabel(rlabel)
    b.set_xlabel(xlabel)
    a.set_xlim(lo, hi)
    jfs.panel_labels([a, b])
    return fig


def fig_curve(task: dict, answer: dict | None):
    pairs = _pairs_curve(task, answer)
    if not pairs:
        raise ValueError("no reference points")
    return _overlay_with_residual(pairs, xlabel="Dq/B", ylabel="Energy (E/B)", rlabel="Residual (E/B)", band=0.3,
                                  height=62, lines=False)


def fig_diagram(task: dict, answer: dict | None):
    pairs = _pairs_diagram(task, answer)
    if not pairs:
        raise ValueError("no reference points")
    return _overlay_with_residual(pairs, xlabel="Dq/B", ylabel="Energy (E/B)", rlabel="Residual (E/B)", band=0.3,
                                  height=70, lines=True)


def fig_batch(task: dict, answer: dict | None):
    from tsbench.score.batch_score import DEFAULT_ITEM_REL, score_batch
    plt, jfs = _matplotlib()
    sc = score_batch(task, answer if isinstance(answer, dict) else {})
    items = sc["items"]
    tol = ((task.get("tolerance") or {}).get("item_rel") or DEFAULT_ITEM_REL) * 100.0
    ink, s1 = _color(jfs, "ink"), _color(jfs, "series-1")
    fig, axs = jfs.figure(WIDTH, 62, nrows=2, height_ratios=[3, 1.35], sharex=True)
    a, b = axs
    xs = [float(it["input"]) for it in items]
    a.plot(xs, [it["reference"] for it in items], ls="none", marker="o", ms=4.2, mfc="none", mec=ink, mew=0.5, zorder=2)
    got = [it for it in items if not it["missing"] and _num(it["result"]) is not None]
    a.plot([float(it["input"]) for it in got], [float(it["result"]) for it in got], ls="none", marker="o", ms=2.2,
           mfc=s1, mec=s1, mew=0.5, zorder=3)
    a.set_ylabel("Result (a.u.)")
    a.text(0.02, 0.97, "o reference", transform=a.transAxes, fontsize=6, color=ink, va="top")
    a.text(0.02, 0.86, "• answer", transform=a.transAxes, fontsize=6, color=s1, va="top")
    b.axhspan(-tol, tol, color=_color(jfs, "house-tint"), lw=0, zorder=0)
    b.axhline(0, color=_color(jfs, "ink-muted"), lw=0.5, zorder=1)
    top = max(3 * tol, 1.0)
    for ok in (True, False):
        pts = [(float(it["input"]), (float(it["result"]) - it["reference"]) / abs(it["reference"]) * 100.0
                if it["reference"] else 0.0) for it in got if it["correct"] == ok and it["reference"] is not None]
        if pts:
            b.plot([p[0] for p in pts], [max(-top, min(top, p[1])) for p in pts], ls="none", **_status_style(jfs, ok))
            if any(abs(p[1]) > top for p in pts):
                b.text(0.02, 0.07, "marks on the edge: off scale", transform=b.transAxes, fontsize=6,
                       color=_color(jfs, "ink-muted"))
    miss = sum(1 for it in items if it["missing"])
    if miss:
        b.text(0.98, 0.93, f"{miss} of {len(items)} items missing", transform=b.transAxes, fontsize=6, ha="right",
               va="top", color=_color(jfs, "series-6"))
    b.set_ylabel("Rel. error (%)")
    b.set_xlabel("Input (a.u.)")
    jfs.panel_labels([a, b])
    return fig


def fig_pairing(row: dict):
    plt, jfs = _matplotlib()
    rows = [("Node precision", "node_precision"), ("Node recall", "node_recall"), ("Edge precision", "edge_precision"),
            ("Edge recall", "edge_recall"), ("Edge F1", "edge_f1")]
    vals = [(lab, _num(row.get(k))) for lab, k in rows]
    if all(v is None for _, v in vals):
        raise ValueError("no pairing scores")
    fig, ax = jfs.figure(WIDTH, 16 + 7.5 * (len(vals) + 1))
    ax.axvline(1.0, color=_color(jfs, "ink-muted"), lw=0.5, ls=(0, (3, 2)), zorder=1)
    for i, (_lab, v) in enumerate(vals):
        if v is None:
            ax.text(0.02, i, "not given", fontsize=6, va="center", color=_color(jfs, "series-6"))
            continue
        ok = v >= 1.0 - 1e-9
        ax.plot([v], [i], ls="none", zorder=3, **_status_style(jfs, ok))
        ax.text(1.05, i, ("ok  " if ok else "x  ") + fixed(v, 2), fontsize=6, va="center", clip_on=False,
                color=_color(jfs, "series-1") if ok else _color(jfs, "series-6"))
    g = row.get("ground_correct")
    gi = len(vals)
    gv = g if isinstance(g, bool) else (str(g).lower() == "true" if g not in (None, "") else None)
    if gv is None:
        ax.text(0.02, gi, "not given", fontsize=6, va="center", color=_color(jfs, "series-6"))
    else:
        ax.plot([1.0 if gv else 0.0], [gi], ls="none", zorder=3, **_status_style(jfs, gv))
        ax.text(1.05, gi, ("ok  " if gv else "x  ") + ("yes" if gv else "no"), fontsize=6, va="center", clip_on=False,
                color=_color(jfs, "series-1") if gv else _color(jfs, "series-6"))
    ax.set_yticks(range(len(vals) + 1))
    ax.set_yticklabels([lab for lab, _ in vals] + ["Ground terms right"])
    ax.yaxis.set_minor_locator(plt.NullLocator())
    ax.set_ylim(len(vals) + 0.5, -0.5)
    ax.set_xlim(0, 1.0)
    ax.set_xlabel("Score (fraction)")
    return fig


def _bool_rows(task: dict | None, ev: dict) -> list[tuple[str, str, bool | None]]:
    """(label, "yes"/"no", good?) per status row; good is None where it does not apply."""
    ans = ev.get("answer")
    row = ev.get("row") or {}
    oos_task = task is not None and bool(task.get("expect_out_of_scope"))
    given = isinstance(ans, dict) and any(ans.get(p) is not None for p in PARAMS)
    yn = lambda v: "yes" if v else "no"  # noqa: E731
    rows: list[tuple[str, str, bool | None]] = [("Answer parseable", yn(ans is not None), ans is not None)]
    if ans is not None and not isinstance(ans.get("points"), list) and not isinstance(ans.get("values"), list):
        rows.append(("Numbers given", yn(given), (not given) if oos_task else given))
    if oos_task:
        rows.append(("Limit named (out of scope)", yn(row.get("answer_out_of_scope") is True),
                     row.get("answer_out_of_scope") is True))
        rows.append(("Refusal correct", yn(bool(ev.get("correct"))), bool(ev.get("correct"))))
    elif task is not None:
        rows.append(("Answer correct", yn(bool(ev.get("correct"))), bool(ev.get("correct"))))
    return rows


def fig_metrics(task: dict | None, ev: dict, medians: dict | None):
    """Status marks (a) and tokens / turns / cost / seconds relative to the class median on a log axis (b)."""
    plt, jfs = _matplotlib()
    medians = medians or {}
    m = ev.get("metrics") or {}
    names = [("tokens", "Tokens"), ("turns", "Turns"), ("cost", "Cost (USD)"), ("seconds", "Duration (s)")]
    have = [(k, lab) for k, lab in names if m.get(k) is not None]
    nb = len(_bool_rows(task, ev))
    fig, axs = jfs.figure(
        WIDTH, 14 + 4.5 * nb + 6.5 * max(len(have), 1), nrows=2, height_ratios=[nb, max(len(have), 1) * 1.2]
    )
    a, b = axs
    rows = _bool_rows(task, ev)
    a.set_xlim(0, 1)
    a.set_ylim(len(rows) - 0.5, -0.5)
    a.set_xticks([])
    a.set_yticks([])
    for s in a.spines.values():
        s.set_visible(False)
    for i, (lab, txt, good) in enumerate(rows):
        a.text(0.0, i, lab, fontsize=6, va="center", ha="left")
        if good is None:
            a.text(0.62, i, "–  n/a", fontsize=6, va="center", color=_color(jfs, "ink-muted"))
        else:
            a.plot([0.64], [i], ls="none", **_status_style(jfs, bool(good)))
            a.text(0.7, i, txt, fontsize=6, va="center",
                   color=_color(jfs, "series-1") if good else _color(jfs, "series-6"))
    a.xaxis.set_minor_locator(plt.NullLocator())
    a.yaxis.set_minor_locator(plt.NullLocator())
    if not have:
        b.axis("off")
        b.text(0.0, 0.5, "no result event: no usage data", fontsize=6, color=_color(jfs, "ink-muted"), va="center")
        return fig
    b.set_xscale("log")
    ratios = []
    for i, (k, _lab) in enumerate(have):
        med = medians.get(k)
        v = m[k]
        if med and v and v > 0:
            r = v / med
            ratios.append(r)
            x = min(max(r, 0.05), 20)
            b.plot([x], [i], ls="none", marker="o", ms=3.5, color=_color(jfs, "series-1"),
                   mfc=_color(jfs, "series-1"), mew=0.5, zorder=3)
            b.text(
                1.04,
                i,
                significant(v) if k != "cost" else fixed(v, 3),
                transform=b.get_yaxis_transform(),
                fontsize=6,
                va="center",
                clip_on=False,
            )
        else:
            b.text(0.5, i, f"{significant(v)}  (no class median)", transform=b.get_yaxis_transform(), fontsize=6,
                   va="center", color=_color(jfs, "ink-muted"))
    b.axvline(1.0, color=_color(jfs, "ink-muted"), lw=0.5, ls=(0, (3, 2)), zorder=1)
    b.set_xlim(0.05, 20)
    b.set_ylim(len(have) - 0.5, -0.5)
    b.set_yticks(range(len(have)))
    b.set_yticklabels([lab for _, lab in have])
    b.yaxis.set_minor_locator(plt.NullLocator())
    b.set_xlabel("Relative to class median (×)")
    jfs.panel_labels([a, b])
    return fig


def fig_no_result(ev: dict, task: dict | None):
    """The card for a run without an evaluable answer: marker, headline and the reason from scorer and taxonomy."""
    plt, jfs = _matplotlib()
    fig, ax = jfs.figure(WIDTH, 24)
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.plot([0.03], [0.82], ls="none", transform=ax.transAxes, **_status_style(jfs, False))
    ax.text(0.08, 0.82, "no evaluable result", fontsize=8, fontweight="bold", va="center",
            color=_color(jfs, "house-deep"), transform=ax.transAxes)
    why = ev.get("reason") or page.CATEGORY_TEXT.get(ev.get("category") or "", "") or "no answer in the expected format"
    why += f"  [{ev['category']}]" if ev.get("category") else ""
    ax.text(0.03, 0.55, "\n".join(textwrap.wrap(why, 62)), fontsize=6.5, va="top", color=_color(jfs, "ink"),
            transform=ax.transAxes)
    return fig


# ------------------------------------------------------------------ routing
def figure_kinds(task: dict | None, ev: dict) -> list[str]:
    """Which figures a run gets (see the module docstring)."""
    if task is None:
        return ["metrics"] if ev.get("has_result") else ["no_result"]
    schema = task.get("answer_schema", "fit")
    if ev.get("answer") is None:
        return ["no_result"] + (["metrics"] if ev.get("has_result") else [])
    if schema == "fit":
        return ["metrics"] if task.get("expect_out_of_scope") else ["fit_error", "metrics"]
    return {"curve": ["curve"], "diagram": ["diagram"], "batch": ["batch"], "pairing": ["pairing"]}.get(
        schema, ["metrics"]
    )


TITLES = {
    "fit_error": "Error per parameter (tolerance band shaded)",
    "curve": "Answer against reference, with residuals",
    "diagram": "Diagram levels against reference, with residuals",
    "batch": "Batch results against reference, with residuals",
    "pairing": "Nodes and edges: precision and recall",
    "metrics": "Key figures of the run",
    "no_result": "no evaluable result",
}


def _draw_kind(kind: str, task, ev, medians):
    row, ans = ev.get("row") or {}, ev.get("answer")
    if kind == "fit_error":
        return fig_fit_error(task, ans, row)
    if kind == "curve":
        return fig_curve(task, ans)
    if kind == "diagram":
        return fig_diagram(task, ans)
    if kind == "batch":
        return fig_batch(task, ans)
    if kind == "pairing":
        return fig_pairing(row)
    if kind == "no_result":
        return fig_no_result(ev, task)
    return fig_metrics(task, ev, medians)


def _figure_key(kind: str, task: dict | None, ev: dict, medians: dict | None) -> str:
    """The cache key of one figure: a hash of everything the figure draws from (the figure version, the kind, the task
    record with reference and tolerance, the scored run). Only the metrics figure reads the class medians."""
    inputs = {"version": FIG_VERSION, "kind": kind, "task": task, "ev": ev}
    if kind == "metrics":
        inputs["medians"] = {k: round(v, 6) for k, v in (medians or {}).items() if isinstance(v, (int, float))}
    return hashlib.sha256(json.dumps(inputs, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def make_figures(
    transcript, task: dict | None, ev: dict, medians: dict | None = None, force: bool = False
) -> list[dict]:
    """Write the figures of one run next to its transcript; returns [{"file", "title", "kind"}] (file relative to the
    figs directory). A figure that fails is logged and left out; the others are still made. A figure is drawn again
    when its key changes (see `_figure_key`), when the transcript is newer than the index or with `force`."""
    t = pathlib.Path(transcript)
    out = figures_dir_of(t)
    kinds = figure_kinds(task, ev)
    keys = {kind: _figure_key(kind, task, ev, medians) for kind in kinds}
    idx = out / INDEX
    old_keys: dict = {}
    old_figs: dict = {}
    old_failed: list = []
    try:
        if not force and idx.is_file() and idx.stat().st_mtime >= t.stat().st_mtime:
            old = json.loads(idx.read_text(encoding="utf-8"))
            old_keys, old_failed = old.get("keys") or {}, old.get("failed") or []
            old_figs = {f["kind"]: f for f in old.get("figures", []) if (out / f["file"]).is_file()}
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        old_keys, old_figs, old_failed = {}, {}, []
    # a kind whose key is unchanged keeps its file; one that failed before (key kept, no file) stays left out
    fresh = {k for k in kinds if old_keys.get(k) == keys[k] and (k in old_figs or k in old_failed)}
    todo = [k for k in kinds if k not in fresh]
    if todo and _matplotlib() is None:
        return []
    made = []
    for kind in kinds:
        if kind in fresh:
            if kind in old_figs:
                made.append(old_figs[kind])
            continue
        try:
            fig = _draw_kind(kind, task, ev, medians)
            _save(fig, out / f"{kind}.svg")
            made.append({"file": f"{kind}.svg", "title": TITLES.get(kind, kind), "kind": kind})
        except Exception as exc:  # noqa: BLE001 - one broken figure never stops the gallery
            log(f"{t.name}: {kind} skipped ({type(exc).__name__}: {exc})")
            try:
                _matplotlib()[0].close("all")
            except Exception:  # noqa: BLE001
                pass
    if todo:
        failed = [k for k in kinds if k not in {m["kind"] for m in made}]
        try:
            out.mkdir(parents=True, exist_ok=True)
            idx.write_text(json.dumps({"keys": keys, "failed": failed, "figures": made}, ensure_ascii=False) + "\n",
                           encoding="utf-8")
        except OSError as exc:
            log(f"{t.name}: index not written ({exc})")
    return made


def class_medians(items) -> dict:
    """{class: {tokens, turns, cost, seconds}} medians over (class, metrics) pairs with a value."""
    acc: dict = {}
    for cls, m in items:
        for k, v in (m or {}).items():
            if isinstance(v, (int, float)) and v > 0:
                acc.setdefault(cls, {}).setdefault(k, []).append(v)
    return {c: {k: statistics.median(v) for k, v in d.items()} for c, d in acc.items()}
