"""Unit tests of `tsbench.figures.plots`: the interval helpers, the row positions and the four data figures, checked
against hand-computed values on small synthetic run sets (no task files, no network, no plotting backend but Agg)."""
from __future__ import annotations

import math
import pathlib
from types import SimpleNamespace
from typing import Any, cast

import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.figure import Figure
from matplotlib.ticker import AutoMinorLocator, FixedLocator, NullLocator

from tsbench.core.intervals import Z95, cluster_bootstrap
from tsbench.figures import data, plots
from tsbench.figures.render import Context

SERIES = {"A": "#0039a6", "B": "#b07800", "C": "#b8336a"}
MARK = {"A": "o", "B": "s", "C": "^"}
NAME = {"A": "A  no tools", "B": "B  Bash", "C": "C  TS-MCP"}
HAIKU, SONNET, OPUS, GATE = "claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-4-7", "qwen3"


@pytest.fixture(autouse=True)
def _close_figures():
    yield
    plt.close("all")


def _fig(built) -> Figure:
    """The figure of a `Built` (typed `object` there, as the builders may return any backend's figure)."""
    return cast(Figure, built.fig)


def wilson(k, n):
    p = k / n
    d = 1 + Z95 * Z95 / n
    centre = (p + Z95 * Z95 / (2 * n)) / d
    half = Z95 * math.sqrt(p * (1 - p) / n + Z95 * Z95 / (4 * n * n)) / d
    return max(0.0, centre - half), min(1.0, centre + half)


def pct(k, n):
    lo, hi = wilson(k, n)
    return 100.0 * k / n, 100.0 * lo, 100.0 * hi


def row(model=HAIKU, cond="A", task="t1", k=1, ok=True, cls="c1", effort="medium", set_name="s1", **kw):
    base = {"set": set_name, "model": model, "condition": cond, "effort": effort, "task_id": task, "k_index": k,
            "class": cls, "correct": ok, "evaluable": True, "has_result": True, "dq": None, "b": None, "c": None,
            "cost_usd": None, "output_tokens": None, "wall_s": None, "wall_is_measured": True, "n_mcp_calls": 0.0,
            "n_bash_calls": 0.0}
    return {**base, **kw}


def ctx_of(rows, **kw):
    names = sorted({r["set"] for r in rows})
    sets = [data.RunSet(path=pathlib.Path("."), name=n, rows=[r for r in rows if r["set"] == n]) for n in names]
    return Context(sets=sets, **kw)


def containers(ax, cond):
    return [c for c in ax.containers if c[0].get_gid() == f"data:{cond}"]


def segments(container):
    return [np.asarray(s).tolist() for s in container[2][0].get_segments()]


def texts_with(obj, text):
    return [t for t in obj.texts if t.get_text() == text]


# ------------------------------------------------------------------------------------------------ cells
def test_constants():
    assert plots.MM_PER_ROW == 2.5
    assert plots.LIT_CLASSES == ("literature_all", "literature_new", "experimental")
    assert plots.PARAMS == (("Dq", "dq"), ("B", "b"), ("C", "c"))
    assert plots.EFF_PANELS == (("cost_usd", "Cost per correct answer (USD)", "usd"),
                                ("output_tokens", "Output tokens per correct answer (1)", "tokens"),
                                ("wall_s", "Wall time per correct answer (s)", "seconds"))


@pytest.mark.parametrize("k,n", [(3, 4), (0, 5), (5, 5), (1, 8), (7, 10)])
def test_share_wilson(k, n):
    rows = [row(task=f"t{i}", ok=i < k) for i in range(n)]
    got = plots.share(rows, "wilson")
    assert got == pytest.approx(pct(k, n), rel=1e-12, abs=1e-12)
    assert plots.share(rows, "anything else") == pytest.approx(pct(k, n), rel=1e-12, abs=1e-12)


def test_share_bootstrap_resamples_tasks_with_their_repeats_together():
    rows = [row(task="t2", k=1, ok=True), row(task="t2", k=2, ok=True), row(task="t1", k=1, ok=False),
            row(task="t1", k=2, ok=True), row(task="t3", k=1, ok=False), row(task="t3", k=2, ok=False),
            row(task="t3", k=3, ok=True), row(task="t4", k=1, ok=True), row(task="t4", k=2, ok=False),
            row(task="t5", k=1, ok=False), row(task="t5", k=2, ok=False)]
    lo, hi = cluster_bootstrap([1, 2, 1, 1, 0], [2, 2, 3, 2, 2])  # tasks in id order: t1 to t5
    s, got_lo, got_hi = plots.share(rows, "bootstrap")
    assert s == pytest.approx(100.0 * 5 / 11)  # the point estimate is over runs
    assert (got_lo, got_hi) == pytest.approx((100.0 * lo, 100.0 * hi), rel=1e-12)
    assert (got_lo, got_hi) != pytest.approx(pct(5, 11)[1:], rel=1e-3)
    wil = plots.share(rows, "wilson")
    assert wil[0] == s and wil[1:] != (got_lo, got_hi)


def test_share_bootstrap_falls_back_to_wilson_below_five_tasks():
    """A bootstrap over 1 to 4 tasks is degenerate (one task: a zero-width interval); such a cell gets Wilson."""
    assert plots.MIN_BOOTSTRAP_TASKS == 5
    one_task = [row(task="t1", k=1, ok=True), row(task="t1", k=2, ok=True), row(task="t1", k=3, ok=False)]
    got = plots.share(one_task, "bootstrap")
    assert got[1] < got[0] < got[2] and got == pytest.approx(pct(2, 3), rel=1e-12)
    assert (got[1], got[2]) == pytest.approx((20.8, 93.9), abs=0.05)
    two_tasks = [row(task="t1", k=i, ok=i > 0) for i in range(3)] + [row(task="t2", k=i, ok=False) for i in range(3)]
    assert plots.share(two_tasks, "bootstrap") == pytest.approx(pct(2, 6), rel=1e-12)
    four = [row(task=f"t{i}", ok=i < 2) for i in range(4)]
    assert plots.share(four, "bootstrap") == pytest.approx(pct(2, 4), rel=1e-12)
    five = [row(task=f"t{i}", ok=i < 2) for i in range(5)]
    assert plots.share(five, "bootstrap")[1:] != pytest.approx(pct(2, 5)[1:], rel=1e-3)
    assert plots.interval_method(one_task, "bootstrap") == "wilson"
    assert plots.interval_method(five, "bootstrap") == "bootstrap"
    assert plots.interval_method(five, "wilson") == "wilson"


def test_ci_meta():
    assert plots.ci_meta("bootstrap") == {"method": "task-clustered percentile bootstrap, 95 %",
                                          "unit": "task, k repetitions kept together"}
    assert plots.ci_meta("wilson") == {"method": "Wilson score interval, 95 %", "unit": "run"}
    assert plots.ci_meta("other") == {"method": "Wilson score interval, 95 %", "unit": "run"}


def test_set_and_effort_labels_are_sorted_and_unique():
    rows = [row(set_name="b", effort="high"), row(set_name="a", effort="medium"), row(set_name="b", effort="high"),
            row(set_name="c", effort="low")]
    assert plots._sets_of(rows) == "a;b;c"
    assert plots._efforts_of(rows) == "high;low;medium"
    assert plots._sets_of([row(set_name="only")]) == "only" and plots._efforts_of([row(effort="x")]) == "x"
    assert plots._sets_of([]) == "" and plots._efforts_of([]) == ""


def test_require():
    plots._require([1], "x")
    with pytest.raises(data.NoDataError, match=r"^no evaluable runs for fig9$"):
        plots._require([], "fig9")


# ------------------------------------------------------------------------------------------------ geometry helpers
def test_model_rows_y_puts_the_first_model_and_condition_on_top():
    assert plots._model_rows_y(["m0", "m1"]) == {(0, 0): 6, (0, 1): 5, (0, 2): 4, (1, 0): 2, (1, 1): 1, (1, 2): 0}
    assert plots._model_rows_y(["m0"]) == {(0, 0): 2, (0, 1): 1, (0, 2): 0}
    assert plots._model_rows_y(["m0", "m1", "m2"])[(0, 0)] == 10
    assert plots._model_rows_y(["m0", "m1"], 2) == {(0, 0): 4, (0, 1): 3, (1, 0): 1, (1, 1): 0}
    assert plots._model_rows_y([]) == {}


def test_style_x():
    fig = Figure()
    ax = fig.subplots()
    plots._style_x(ax)
    assert ax.get_xlim() == (-2, 102) and list(ax.get_xticks()) == [0, 25, 50, 75, 100]
    assert isinstance(ax.xaxis.get_minor_locator(), AutoMinorLocator) and _any(ax.xaxis.get_minor_locator()).ndivs == 2
    assert isinstance(ax.yaxis.get_minor_locator(), NullLocator)
    ax = Figure().subplots()
    plots._style_x(ax, pct=False)
    assert ax.get_xlim() == (0.0, 1.0)
    assert isinstance(ax.xaxis.get_minor_locator(), AutoMinorLocator)
    assert isinstance(ax.yaxis.get_minor_locator(), NullLocator)


def _any(obj: Any) -> Any:
    """`obj` typed as Any: matplotlib's stubs name a getter's result by its base class (Locator, Transform, Patch, Text,
    LayoutEngine), and the tests read the attributes of the concrete class."""
    return obj


JFS = SimpleNamespace(COLORS={"series-1": SERIES["A"], "series-2": SERIES["B"], "series-3": SERIES["C"]})


def test_finish_adds_layout_key_and_footer():
    ctx = SimpleNamespace(rows=[1, 2], sets=[1], footer=True)
    fig = Figure(figsize=(4, 2), layout="constrained")
    plots._finish(fig, _any(ctx), JFS)
    gids = [t.get_gid() for t in fig.texts]
    assert gids == ["key:A", "key:B", "key:C", "footer"]
    assert fig.texts[-1].get_text() == ("Pilot data, not confirmatory: 2 runs from 1 run sets "
                                        "(HTTP 429 / API errors excluded).")
    assert _any(fig.get_layout_engine()).get()["rect"] == pytest.approx((0, 9 / 144, 1, 1 - 10 / 144 - 9 / 144))
    fig = Figure(figsize=(4, 2), layout="constrained")
    plots._finish(fig, _any(SimpleNamespace(rows=[], sets=[], footer=False)), JFS, key=False)
    assert fig.texts == [] and _any(fig.get_layout_engine()).get()["rect"] == pytest.approx((0, 0, 1, 1))
    fig = Figure(figsize=(4, 2), layout="constrained")
    plots._finish(fig, _any(ctx), JFS, key=False)
    assert [t.get_gid() for t in fig.texts] == ["footer"]
    assert _any(fig.get_layout_engine()).get()["rect"] == pytest.approx((0, 9 / 144, 1, 1 - 9 / 144))


def _cells():
    return {("m0", "A"): {"x": 40.0, "lo": 30.0, "hi": 55.0}, ("m0", "C"): {"x": 10.0, "lo": 12.0, "hi": 9.0},
            ("m1", "A"): {"x": None, "lo": 0.0, "hi": 0.0}, ("m1", "B"): {"x": 70.0, "lo": 60.0, "hi": 90.0},
            ("m9", "A"): {"x": 99.0, "lo": 1.0, "hi": 100.0}}


def test_dot_rows_draw_one_errorbar_call_per_condition(monkeypatch):
    monkeypatch.setitem(plt.rcParams, "errorbar.capsize", 4)  # the bars are drawn without caps whatever the style says
    fig = Figure()
    ax = fig.subplots()
    ypos = plots._dot_rows(ax, JFS, _cells(), ["m0", "m1"], "x", "lo", "hi")
    assert ypos == {(0, 0): 6, (0, 1): 5, (0, 2): 4, (1, 0): 2, (1, 1): 1, (1, 2): 0}
    assert [c[0].get_gid() for c in ax.containers] == ["data:A", "data:B", "data:C"]
    a, b, c = (containers(ax, k)[0] for k in "ABC")
    assert (list(a[0].get_xdata()), list(a[0].get_ydata())) == ([40.0], [6])  # m1/A has no value: left out
    assert (list(b[0].get_xdata()), list(b[0].get_ydata())) == ([70.0], [1])
    assert (list(c[0].get_xdata()), list(c[0].get_ydata())) == ([10.0], [4])
    assert segments(a) == [[[30.0, 6.0], [55.0, 6.0]]]
    assert segments(b) == [[[60.0, 1.0], [90.0, 1.0]]]
    assert segments(c) == [[[10.0, 4.0], [10.0, 4.0]]]  # a negative arm is clipped to zero length
    for cond, cont in zip("ABC", (a, b, c), strict=True):
        line = cont[0]
        assert (line.get_marker(), line.get_color(), line.get_markerfacecolor()) == (MARK[cond], SERIES[cond],
                                                                                     SERIES[cond])
        assert (line.get_markersize(), line.get_markeredgewidth(), line.get_linestyle()) == (3, 0.5, "None")
        assert cont[1] == () and list(cont[2][0].get_linewidth()) == [0.75]
    assert list(ax.get_yticks()) == [5, 1]
    assert [t.get_text() for t in ax.get_yticklabels()] == ["m0", "m1"]
    assert ax.get_ylim() == (-1, 7)
    assert ax.yaxis.get_major_ticks()[0].tick1line.get_markersize() == 0
    assert ax.xaxis.get_major_ticks()[0].tick1line.get_markersize() > 0  # only the y ticks are removed


def test_dot_rows_without_labels_and_with_missing_conditions():
    ax = Figure().subplots()
    cells = {("m0", "B"): {"x": 3.0, "lo": 1.0, "hi": 4.0}}
    ypos = plots._dot_rows(ax, JFS, cells, ["m0"], "x", "lo", "hi", ylab=False)
    assert ypos == {(0, 0): 2, (0, 1): 1, (0, 2): 0}
    assert [c[0].get_gid() for c in ax.containers] == ["data:B"]
    assert ax.get_ylim() == (-1, 3)
    assert not isinstance(ax.yaxis.get_major_locator(), FixedLocator)  # the model labels are left to the caller
    ax = Figure().subplots()
    plots._dot_rows(ax, JFS, {}, ["m0", "m1", "m2"], "x", "lo", "hi")
    assert ax.containers == [] and ax.get_ylim() == (-1, 11) and list(ax.get_yticks()) == [9, 5, 1]


def test_dot_rows_state_colour_and_marker_size_whatever_the_style(monkeypatch):
    """Colour, marker size and edge width are given per condition, not taken from the style or the colour cycle: a
    condition drawn first (A missing) still gets its own colour."""
    monkeypatch.setitem(plt.rcParams, "lines.markersize", 9.0)
    monkeypatch.setitem(plt.rcParams, "lines.markeredgewidth", 2.0)
    monkeypatch.setitem(plt.rcParams, "axes.prop_cycle", plt.cycler(color=["#123456"]))
    ax = Figure().subplots()
    cells = {("m0", "B"): {"x": 3.0, "lo": 1.0, "hi": 4.0}, ("m0", "C"): {"x": 5.0, "lo": 4.0, "hi": 6.0}}
    plots._dot_rows(ax, JFS, cells, ["m0"], "x", "lo", "hi")
    for cond in "BC":
        (cont,) = containers(ax, cond)
        line = cont[0]
        assert (line.get_color(), line.get_markeredgecolor(), line.get_markersize(), line.get_markeredgewidth()) == (
            SERIES[cond], SERIES[cond], 3, 0.5)
        assert [tuple(c) for c in cont[2][0].get_colors()] == [plt.matplotlib.colors.to_rgba(SERIES[cond])]


# ------------------------------------------------------------------------ accuracy_by_model / accuracy_by_class data
def rows_two_sets():
    r = []
    # haiku: A 1 of 4, B 4 of 4, C 2 of 3 (the C runs at a second effort and in a second set)
    r += [row(HAIKU, "A", f"t{i}", 1, ok=(i == 1), cls="c1" if i <= 2 else "c2") for i in (1, 2, 3, 4)]
    r += [row(HAIKU, "B", f"t{i}", 1, ok=True, cls="c1" if i <= 2 else "c2") for i in (1, 2, 3, 4)]
    r += [row(HAIKU, "C", f"t{i}", 1, ok=(i != 3), cls="c1" if i <= 2 else "c2", effort="high", set_name="s2")
          for i in (1, 2, 3)]
    # sonnet: A 3 of 4 over two repeats of two tasks, C 1 of 1
    r += [row(SONNET, "A", t, k, ok=ok, cls="c2") for t, k, ok in
          [("t1", 1, True), ("t1", 2, True), ("t2", 1, False), ("t2", 2, True)]]
    r += [row(SONNET, "C", "t1", 1, ok=True, cls="c1")]
    r += [row(OPUS, "A", "t1", 1, ok=True, cls="c1"), row(GATE, "A", "t1", 1, ok=False, cls="c2")]
    r += [row(HAIKU, "A", "tx", 1, ok=True, evaluable=False)]  # never pooled
    return r


def test_accuracy_by_model_source_rows():
    ctx = ctx_of(rows_two_sets())
    b = plots.accuracy_by_model(ctx)
    assert b.columns == ["model", "model_label", "condition", "n_runs", "n_tasks", "n_correct", "share_pct",
                         "ci_lo_pct", "ci_hi_pct", "ci_method", "efforts", "sets"]
    expect = [(HAIKU, "Haiku 5.5", "A", 4, 4, 1, "medium", "s1"), (HAIKU, "Haiku 5.5", "B", 4, 4, 4, "medium", "s1"),
              (HAIKU, "Haiku 5.5", "C", 3, 3, 2, "high", "s2"), (SONNET, "Sonnet 5.5", "A", 4, 2, 3, "medium", "s1"),
              (SONNET, "Sonnet 5.5", "C", 1, 1, 1, "medium", "s1"), (OPUS, "Opus 4.7", "A", 1, 1, 1, "medium", "s1"),
              (GATE, "qwen3", "A", 1, 1, 0, "medium", "s1")]
    assert [(r["model"], r["model_label"], r["condition"], r["n_runs"], r["n_tasks"], r["n_correct"], r["efforts"],
             r["sets"]) for r in b.source] == expect
    for r, (_m, _l, _c, n, _t, k, _e, _s) in zip(b.source, expect, strict=True):
        assert (r["share_pct"], r["ci_lo_pct"], r["ci_hi_pct"]) == pytest.approx(pct(k, n), rel=1e-12, abs=1e-12)
        assert r["ci_method"] == "wilson"
    assert b.ci == {"method": "Wilson score interval, 95 %", "unit": "run"}
    assert b.notes == ["models with HTTP 429 / API-error runs: those runs are excluded, not counted wrong"]
    assert b.caption == (
        "Share of correct answers per model and condition (dot: share, bar: 95 % Wilson score interval). "
        "PILOT data, not confirmatory; cells pool the pilot task classes available per model and condition "
        "(different task mixes and k), so compare conditions within a model.")


def test_accuracy_by_model_bootstrap_option_changes_the_interval_not_the_share():
    rows = rows_two_sets() + [row(SONNET, "A", f"u{i}", 1, ok=i % 2 == 0, cls="c2") for i in range(3)]
    w = plots.accuracy_by_model(ctx_of(rows)).source
    bs = plots.accuracy_by_model(ctx_of(rows, ci="bootstrap"))
    assert [r["share_pct"] for r in bs.source] == [r["share_pct"] for r in w]
    n_wilson = sum(r["ci_method"] == "wilson" for r in bs.source)
    assert 0 < n_wilson < len(bs.source)
    why = f"Wilson score interval for the {n_wilson} of {len(bs.source)} cells with fewer than 5 tasks"
    assert bs.caption.startswith("Share of correct answers per model and condition (dot: share, bar: 95 % "
                                 f"task-clustered percentile bootstrap; {why}).")
    assert bs.ci == {"method": f"task-clustered percentile bootstrap, 95 % ({why})",
                     "unit": "task, k repetitions kept together; run for the Wilson cells"}
    a = next(r for r in bs.source if r["model"] == SONNET and r["condition"] == "A")
    assert a["ci_method"] == "bootstrap"
    lo, hi = cluster_bootstrap([2, 1, 1, 0, 1], [2, 2, 1, 1, 1])
    assert (a["ci_lo_pct"], a["ci_hi_pct"]) == pytest.approx((100 * lo, 100 * hi), rel=1e-12)
    # cells with fewer than five tasks fall back to Wilson and say so
    few = [r for r in bs.source if r["n_tasks"] < plots.MIN_BOOTSTRAP_TASKS]
    assert few and {r["ci_method"] for r in few} == {"wilson"}
    for r in few:
        assert (r["ci_lo_pct"], r["ci_hi_pct"]) == pytest.approx(pct(r["n_correct"], r["n_runs"])[1:])
    assert any("fewer than 5 tasks" in n and "Wilson" in n for n in bs.notes)
    assert not any("fewer than 5 tasks" in n for n in plots.accuracy_by_model(ctx_of(rows)).notes)


def test_accuracy_by_model_draws_the_cells_as_dots_with_bars():
    b = plots.accuracy_by_model(ctx_of(rows_two_sets()))
    fig = _fig(b)
    w, h = fig.get_size_inches()
    assert (w * 25.4, h * 25.4) == pytest.approx((84.6, 24 + 2.5 * 4 * 4))
    (ax,) = fig.axes
    ypos = plots._model_rows_y([HAIKU, SONNET, OPUS, GATE])
    by = {(r["model"], r["condition"]): r for r in b.source}
    for j, cond in enumerate("ABC"):
        (cont,) = containers(ax, cond)
        cells = [(i, m) for i, m in enumerate([HAIKU, SONNET, OPUS, GATE]) if (m, cond) in by]
        assert list(cont[0].get_xdata()) == pytest.approx([by[(m, cond)]["share_pct"] for _i, m in cells])
        assert list(cont[0].get_ydata()) == [ypos[(i, j)] for i, _m in cells]
        want = [[[by[(m, cond)]["ci_lo_pct"], ypos[(i, j)]], [by[(m, cond)]["ci_hi_pct"], ypos[(i, j)]]]
                for i, m in cells]
        assert np.allclose(segments(cont), want)
        assert (cont[0].get_marker(), cont[0].get_color()) == (MARK[cond], SERIES[cond])
    assert ax.get_xlabel() == "Share correct (%)" and ax.get_xlim() == (-2, 102)
    assert list(ax.get_xticks()) == [0, 25, 50, 75, 100]
    assert list(ax.get_yticks()) == [13, 9, 5, 1] and ax.get_ylim() == (-1, 15)
    assert [t.get_text() for t in ax.get_yticklabels()] == ["Haiku 5.5", "Sonnet 5.5", "Opus 4.7", "qwen3"]
    assert [t.get_gid() for t in fig.texts] == ["footer"]  # the conditions are labelled in the plot, no key on top
    assert _any(fig.get_layout_engine()).get()["rect"] == pytest.approx((0, 9 / (h * 72), 1, 1 - 9 / (h * 72)))


def test_accuracy_by_model_labels_the_conditions_beside_the_first_models_dots():
    b = plots.accuracy_by_model(ctx_of(rows_two_sets()))
    (ax,) = _fig(b).axes
    by = {(r["model"], r["condition"]): r for r in b.source}
    for j, cond in enumerate("ABC"):
        (t,) = texts_with(ax, NAME[cond])
        cell = by[(HAIKU, cond)]
        right = cell["ci_hi_pct"] < 72
        assert right is (cond == "A")  # only the 25 % cell leaves room on its right
        x, y = t.get_position()
        assert x == pytest.approx(cell["ci_hi_pct"] + 2.5 if right else cell["ci_lo_pct"] - 2.5)
        assert y == 14 - j  # four models: the first one starts at (4 - 1) * 4 + 2
        assert (t.get_color(), t.get_fontsize(), t.get_va(), t.get_ha()) == (
            SERIES[cond], 6, "center", "left" if right else "right")


def test_accuracy_by_model_label_side_switches_at_72_percent(monkeypatch):
    rows = [row(HAIKU, "A", "t1"), row(HAIKU, "B", "t1"), row(HAIKU, "C", "t1")]
    values = {"A": (50.0, 40.0, 71.999), "B": (50.0, 40.0, 72.0), "C": (50.0, 40.0, 72.001)}
    monkeypatch.setattr(plots, "share", lambda rs, method: values[rs[0]["condition"]])
    (ax,) = _any(plots.accuracy_by_model(ctx_of(rows)).fig).axes
    (a,), (b,), (c,) = (texts_with(ax, NAME[k]) for k in "ABC")
    assert (a.get_ha(), a.get_position()[0]) == ("left", pytest.approx(71.999 + 2.5))
    assert (b.get_ha(), b.get_position()[0]) == ("right", pytest.approx(40.0 - 2.5))
    assert (c.get_ha(), c.get_position()[0]) == ("right", pytest.approx(40.0 - 2.5))


def test_accuracy_by_model_skips_the_label_of_a_condition_the_first_model_lacks():
    rows = [row(HAIKU, "B", "t1"), row(HAIKU, "C", "t1"), row(SONNET, "A", "t1")]
    (ax,) = _any(plots.accuracy_by_model(ctx_of(rows)).fig).axes
    assert [t.get_text() for t in ax.texts] == [NAME["B"], NAME["C"]]
    rows = [row(HAIKU, "A", "t1"), row(SONNET, "B", "t1"), row(SONNET, "C", "t1")]
    (ax,) = _any(plots.accuracy_by_model(ctx_of(rows)).fig).axes
    assert [t.get_text() for t in ax.texts] == [NAME["A"]]


def test_accuracy_by_model_theme_and_footer_options(contrast_theme):
    rows = [row(HAIKU, "A", "t1")]
    b = plots.accuracy_by_model(ctx_of(rows, footer=False, theme=contrast_theme))
    assert _fig(b).texts == []
    (cont,) = containers(_fig(b).axes[0], "A")
    assert cont[0].get_color() == "#006699"
    assert _any(_fig(b).get_layout_engine()).get()["rect"] == pytest.approx((0, 0, 1, 1))


def test_accuracy_by_model_without_runs_raises():
    with pytest.raises(data.NoDataError, match=r"^no evaluable runs for accuracy_by_model$"):
        plots.accuracy_by_model(ctx_of([]))
    with pytest.raises(data.NoDataError):
        plots.accuracy_by_model(ctx_of([row(evaluable=False)]))


def test_accuracy_by_model_passes_the_ci_option_to_share(monkeypatch):
    seen = []

    def spy(rs, method):
        seen.append(method)
        return 50.0, 40.0, 60.0

    monkeypatch.setattr(plots, "share", spy)
    plots.accuracy_by_model(ctx_of([row(HAIKU, "A", "t1")], ci="bootstrap"))
    plots.accuracy_by_model(ctx_of([row(HAIKU, "A", "t1")]))
    assert seen == ["bootstrap", "wilson"]


# ------------------------------------------------------------------------------------------------ accuracy_by_class
def test_accuracy_by_class_source_rows():
    b = plots.accuracy_by_class(ctx_of(rows_two_sets()))
    assert b.columns == ["model", "model_label", "class", "condition", "n_runs", "n_tasks", "n_correct", "share_pct",
                         "ci_lo_pct", "ci_hi_pct", "ci_method"]
    got = [(r["model"], r["class"], r["condition"], r["n_runs"], r["n_tasks"], r["n_correct"]) for r in b.source]
    assert got == [(HAIKU, "c1", "A", 2, 2, 1), (HAIKU, "c1", "B", 2, 2, 2), (HAIKU, "c1", "C", 2, 2, 2),
                   (HAIKU, "c2", "A", 2, 2, 0), (HAIKU, "c2", "B", 2, 2, 2), (HAIKU, "c2", "C", 1, 1, 0),
                   (SONNET, "c1", "C", 1, 1, 1), (SONNET, "c2", "A", 4, 2, 3), (OPUS, "c1", "A", 1, 1, 1),
                   (GATE, "c2", "A", 1, 1, 0)]
    for r in b.source:
        assert (r["share_pct"], r["ci_lo_pct"], r["ci_hi_pct"]) == pytest.approx(pct(r["n_correct"], r["n_runs"]))
        assert r["model_label"] == data.model_label(r["model"]) and r["ci_method"] == "wilson"
    assert b.ci == plots.ci_meta("wilson")
    assert b.caption == ("Share correct per task class, condition and model (95 % Wilson score interval). "
                         "PILOT data, not confirmatory; a class has 1 to 10 pilot tasks, so intervals are wide.")
    boot = plots.accuracy_by_class(ctx_of(rows_two_sets(), ci="bootstrap"))
    # every cell here has fewer than five tasks: Wilson, flagged, with a non-degenerate interval; no bootstrap label
    assert boot.caption == b.caption and boot.ci == plots.ci_meta("wilson")
    assert {r["ci_method"] for r in boot.source} == {"wilson"}
    assert any("fewer than 5 tasks" in n for n in boot.notes)
    sonnet = next(r for r in boot.source if (r["model"], r["class"], r["condition"]) == (SONNET, "c2", "A"))
    assert (sonnet["ci_lo_pct"], sonnet["ci_hi_pct"]) == pytest.approx(pct(3, 4)[1:], rel=1e-12)
    assert sonnet["share_pct"] == 75.0
    # a cell with five tasks keeps the bootstrap
    rows = [row(HAIKU, "A", f"t{i}", 1, ok=i < 3, cls="c1") for i in range(5)]
    cell = plots.accuracy_by_class(ctx_of(rows, ci="bootstrap"))
    assert [r["ci_method"] for r in cell.source] == ["bootstrap"] and cell.notes == []
    assert cell.ci == plots.ci_meta("bootstrap") and "(95 % task-clustered percentile bootstrap)." in cell.caption
    lo, hi = cluster_bootstrap([1, 1, 1, 0, 0], [1] * 5)
    assert (cell.source[0]["ci_lo_pct"], cell.source[0]["ci_hi_pct"]) == pytest.approx((100 * lo, 100 * hi))


def test_accuracy_by_class_bootstrap_caption_names_the_cells_that_fell_back_to_wilson():
    rows = [row(HAIKU, "A", f"t{i}", 1, ok=i < 3, cls="c1") for i in range(5)] + [row(HAIKU, "B", "t0", 1, cls="c1")]
    b = plots.accuracy_by_class(ctx_of(rows, ci="bootstrap"))
    assert sorted(r["ci_method"] for r in b.source) == ["bootstrap", "wilson"]
    assert ("(95 % task-clustered percentile bootstrap; Wilson score interval for the 1 of 2 cells with fewer than "
            "5 tasks).") in b.caption
    assert "bootstrap" in b.ci["method"] and "Wilson" in b.ci["method"]


def test_accuracy_by_class_provenance_of_a_bootstrap_run_with_only_wilson_cells_declares_no_bootstrap(monkeypatch):
    from tsbench.figures import render
    monkeypatch.setattr(render, "git_info", lambda: {})
    monkeypatch.setattr(render, "task_hashes", lambda: {})
    ctx = ctx_of(rows_two_sets(), ci="bootstrap")
    doc = render.provenance("accuracy_by_class", ctx, plots.accuracy_by_class(ctx), [], "x")
    assert "bootstrap" not in doc and doc["ci"] == plots.ci_meta("wilson") and "Wilson" in doc["caption"]
    assert "bootstrap" not in doc["caption"]
    rows = [row(HAIKU, "A", f"t{i}", 1, ok=i < 3, cls="c1") for i in range(5)]
    ctx = ctx_of(rows, ci="bootstrap")
    assert "bootstrap" in render.provenance("accuracy_by_class", ctx, plots.accuracy_by_class(ctx), [], "x")


def test_accuracy_by_class_grid_titles_and_axes(monkeypatch):
    monkeypatch.setitem(plt.rcParams, "axes.titlelocation", "left")  # the titles are centred whatever the style says
    b = plots.accuracy_by_class(ctx_of(rows_two_sets()))
    fig = _fig(b)
    w, h = fig.get_size_inches()
    assert (w * 25.4, h * 25.4) == pytest.approx((177.8, 20 + 2 * (6 + 2 * 3.6)))  # 4 models: 2 rows of up to 3
    axes = fig.axes
    shown = [ax for ax in axes if ax.get_visible()]
    assert len(axes) == 6 and len(shown) == 4
    assert [ax.get_title("center") for ax in shown] == ["Haiku 5.5", "Sonnet 5.5", "Opus 4.7", "qwen3"]
    assert [ax.get_title("left") for ax in shown] == [""] * 4
    assert all(ax.title.get_fontsize() == 7 for ax in shown)
    assert [ax.get_visible() for ax in axes] == [True, True, True, True, False, False]
    grid = [[axes[0], axes[1], axes[2]], [axes[3], axes[4], axes[5]]]
    assert _any(grid[0][0].get_subplotspec()).rowspan.start == 0
    assert _any(grid[1][0].get_subplotspec()).rowspan.start == 1
    # the x label sits on the lowest drawn axes of each column
    assert [ax.get_xlabel() for ax in shown] == ["", "Share correct (%)", "Share correct (%)", "Share correct (%)"]
    for ax in shown:
        assert ax.get_xlim() == (-2, 102) and list(ax.get_xticks()) == [0, 25, 50, 75, 100]
        assert ax.get_ylim() == pytest.approx((-0.7, 1.7)) and list(ax.get_yticks()) == [1, 0]
        assert ax.get_shared_x_axes().joined(ax, shown[0]) and ax.get_shared_y_axes().joined(ax, shown[0])
        assert ax.yaxis.get_major_ticks()[0].tick1line.get_markersize() == 0
        assert ax.xaxis.get_major_ticks()[0].tick1line.get_markersize() > 0
        gl = ax.yaxis.get_gridlines()[0]
        assert gl.get_visible() and gl.get_color() == "#d9d9d9" and gl.get_linewidth() == 0.4
        assert not ax.xaxis.get_gridlines()[0].get_visible()
    assert [[t.get_text() for t in ax.texts] for ax in shown] == [["a"], ["b"], ["c"], ["d"]]
    assert [t.get_gid() for t in fig.texts] == ["key:A", "key:B", "key:C", "footer"]
    assert [t.get_text() for t in shown[0].get_yticklabels()] == ["c1", "c2"]  # the others share them


def test_accuracy_by_class_dots_sit_at_class_rows_offset_by_condition(monkeypatch):
    monkeypatch.setitem(plt.rcParams, "errorbar.capsize", 4)
    b = plots.accuracy_by_class(ctx_of(rows_two_sets()))
    axes = [ax for ax in _fig(b).axes if ax.get_visible()]
    by = {(r["model"], r["class"], r["condition"]): r for r in b.source}
    off = {"A": 0.25, "B": 0.0, "C": -0.25}
    ymap = {"c1": 1, "c2": 0}
    for ax, model in zip(axes, [HAIKU, SONNET, OPUS, GATE], strict=True):
        for cond in "ABC":
            cells = [(cls, by[(model, cls, cond)]) for cls in ("c1", "c2") if (model, cls, cond) in by]
            conts = containers(ax, cond)
            if not cells:
                assert conts == []
                continue
            (cont,) = conts
            assert list(cont[0].get_xdata()) == pytest.approx([r["share_pct"] for _c, r in cells])
            assert list(cont[0].get_ydata()) == pytest.approx([ymap[c] + off[cond] for c, _r in cells])
            want = [[[r["ci_lo_pct"], ymap[cls] + off[cond]], [r["ci_hi_pct"], ymap[cls] + off[cond]]]
                    for cls, r in cells]
            assert np.allclose(segments(cont), want)
            line = cont[0]
            assert (line.get_marker(), line.get_color(), line.get_markersize(), line.get_markeredgewidth()) == (
                MARK[cond], SERIES[cond], 2.5, 0.4)
            assert list(cont[2][0].get_linewidth()) == [0.5] and cont[1] == ()


def test_accuracy_by_class_states_caps_title_size_and_grid_colour_whatever_the_style(monkeypatch):
    """No caps, 7 pt titles and the theme's grid colour even under a style (set after the builder's own set-up) whose
    defaults differ."""
    real = plots.setup

    def loud_setup(theme="neutral"):
        plt_, jfs = real(theme)
        for key, value in {"errorbar.capsize": 5.0, "axes.titlesize": 12.0, "font.size": 11.0,
                           "grid.color": "#ff0000"}.items():
            monkeypatch.setitem(plt_.rcParams, key, value)
        return plt_, jfs

    monkeypatch.setattr(plots, "setup", loud_setup)
    b = plots.accuracy_by_class(ctx_of(rows_two_sets()))
    shown = [ax for ax in _fig(b).axes if ax.get_visible()]
    assert [ax.title.get_fontsize() for ax in shown] == [7] * 4
    assert {ax.yaxis.get_gridlines()[0].get_color() for ax in shown} == {"#d9d9d9"}
    assert all(cont[1] == () for ax in shown for cont in ax.containers)


def test_accuracy_by_class_single_model_has_one_axes_and_its_x_label():
    b = plots.accuracy_by_class(ctx_of([row(HAIKU, "A", "t1", cls="c1"), row(HAIKU, "C", "t1", cls="c3")]))
    assert len(_fig(b).axes) == 1
    (ax,) = _fig(b).axes
    assert ax.get_xlabel() == "Share correct (%)" and [t.get_text() for t in ax.get_yticklabels()] == ["c1", "c3"]
    assert _fig(b).get_size_inches()[1] * 25.4 == pytest.approx(20 + 1 * (6 + 2 * 3.6))
    assert ax.get_ylim() == pytest.approx((-0.7, 1.7))


@pytest.mark.parametrize("n_models,nrows,ncols,labelled", [
    (2, 1, 2, [0, 1]), (3, 1, 3, [0, 1, 2]), (4, 2, 3, [1, 2, 3]), (5, 2, 3, [2, 3, 4]), (6, 2, 3, [3, 4, 5]),
    (7, 3, 3, [4, 5, 6])])
def test_accuracy_by_class_grid_shape_and_where_the_x_label_is(n_models, nrows, ncols, labelled):
    models = [HAIKU, SONNET, OPUS, "m4", "m5", "m6", "m7"][:n_models]
    b = plots.accuracy_by_class(ctx_of([row(m, "A", "t1") for m in models]))
    axes = _fig(b).axes
    assert len(axes) == nrows * ncols
    assert [ax.get_visible() for ax in axes] == [i < n_models for i in range(nrows * ncols)]
    assert {_any(ax.get_subplotspec()).rowspan.start for ax in axes} == set(range(nrows))
    assert [i for i, ax in enumerate(axes) if ax.get_xlabel()] == labelled
    assert _fig(b).get_size_inches()[1] * 25.4 == pytest.approx(20 + nrows * (6 + 1 * 3.6))
    assert [[t.get_text() for t in ax.texts] for ax in axes[:n_models]] == [["abcdefg"[i]] for i in range(n_models)]


def test_accuracy_by_class_without_runs_raises():
    with pytest.raises(data.NoDataError, match=r"^no evaluable runs for accuracy_by_class$"):
        plots.accuracy_by_class(ctx_of([]))


# ------------------------------------------------------------------------------------------------ literature_parity
def _task(cls, ref, tol):
    return {"class": cls, "reference": dict(zip(("Dq", "B", "C"), ref, strict=True)),
            "tolerance": dict(zip(("Dq", "B", "C"), tol, strict=True))}


TASKS = {
    "L1": _task("literature_all", (1000.0, 500.0, 2000.0), (0.05, 0.10, 0.15)),
    "N1": _task("literature_new", (2000.0, 800.0, 3000.0), (0.05, 0.10, 0.15)),
    "E1": _task("experimental", (1500.0, 600.0, None), (0.05, 0.10, None)),
    "Z1": _task("literature_all", (0.0, 400.0, 1000.0), (0.05, 0.10, 0.15)),
    "T1": _task("literature_all", (1000.0, 500.0, 2000.0), (0.05, None, 0.15)),
    "X1": _task("numerical", (1000.0, 500.0, 2000.0), (0.05, 0.10, 0.15)),
}


@pytest.fixture
def tasks(monkeypatch):
    monkeypatch.setattr(data, "pilot_tasks", lambda: TASKS)
    return TASKS


def lit(model, cond, task, k=1, dq=None, b=None, c=None):
    return row(model, cond, task, k, cls=TASKS[task]["class"], dq=dq, b=b, c=c)


def parity_rows():
    return [lit(HAIKU, "A", "L1", 1, dq=1050.000000005, b=450.0, c=2600.0),
            lit(HAIKU, "A", "L1", 2, dq=1200.0, b=None, c=2000.0),
            lit(HAIKU, "C", "N1", 1, dq=2000.0, b=1600.0, c=None),
            lit(SONNET, "B", "E1", 1, dq=1605.0, b=660.0, c=999.0),
            lit(SONNET, "B", "Z1", 1, dq=500.0, b=800.0, c=1500.0),
            lit(SONNET, "A", "X1", 1, dq=1.0, b=1.0, c=1.0),
            lit(HAIKU, "A", "T1", 1, dq=1100.0, b=1.0, c=2000.0)]


def _src(b, param):
    return [r for r in b.source if r["param"] == param]


def test_literature_parity_source_rows_are_deviations_from_the_reference(tasks):
    b = plots.literature_parity(ctx_of(parity_rows()))
    assert b.columns == ["param", "model", "model_label", "condition", "class", "task_id", "k_index", "reference",
                         "value", "deviation_pct", "tolerance_pct", "within_tolerance"]
    dq = [(r["condition"], r["model"], r["task_id"], r["k_index"], r["reference"], r["value"]) for r in _src(b, "Dq")]
    assert dq == [("A", HAIKU, "L1", 1, 1000.0, 1050.000000005), ("A", HAIKU, "L1", 2, 1000.0, 1200.0),
                  ("A", HAIKU, "T1", 1, 1000.0, 1100.0), ("B", SONNET, "E1", 1, 1500.0, 1605.0),
                  ("C", HAIKU, "N1", 1, 2000.0, 2000.0)]  # Z1 has reference 0, X1 is no literature class
    assert [r["deviation_pct"] for r in _src(b, "Dq")] == pytest.approx([5.0000000005, 20.0, 10.0, 7.0, 0.0])
    assert [r["tolerance_pct"] for r in _src(b, "Dq")] == pytest.approx([5.0] * 5)
    assert [r["within_tolerance"] for r in _src(b, "Dq")] == [True, False, False, False, True]
    bb = [(r["condition"], r["task_id"], r["k_index"], r["deviation_pct"], r["within_tolerance"])
          for r in _src(b, "B")]
    assert bb[0] == ("A", "L1", 1, pytest.approx(-10.0), True)  # a run exactly at the tolerance is inside
    assert [(t[0], t[1], t[2]) for t in bb] == [("A", "L1", 1), ("B", "E1", 1), ("B", "Z1", 1), ("C", "N1", 1)]
    assert [t[3] for t in bb] == pytest.approx([-10.0, 10.0, 100.0, 100.0])
    assert [t[4] for t in bb] == [True, True, False, False]
    cc = [(r["condition"], r["task_id"], r["deviation_pct"], r["tolerance_pct"]) for r in _src(b, "C")]
    assert [c[:2] for c in cc] == [("A", "L1"), ("A", "L1"), ("A", "T1"), ("B", "Z1")]
    assert [c[2] for c in cc] == pytest.approx([30.0, 0.0, 0.0, 50.0]) and {c[3] for c in cc} == {15.0}
    first = _src(b, "Dq")[0]
    assert first["param"] == "Dq" and first["model_label"] == "Haiku 5.5" and first["class"] == "literature_all"
    assert first["tolerance_pct"] == pytest.approx(5.0) and isinstance(first["reference"], float)
    assert b.notes == [
        "experimental tasks have no C (not required); signed deviation = (model - reference) / reference",
        "classes present: experimental,literature_all,literature_new"]
    assert b.caption.startswith("Literature parity: parameter returned by the model against the oracle reference")
    assert b.caption.endswith("Grey band: scoring tolerance. PILOT data, not confirmatory.")
    assert ("(forward-model least squares for literature_all / literature_new, closed form for experimental), as "
            "signed deviation in %.") in b.caption


def test_literature_parity_source_rows_sort_by_model_before_task(tasks):
    """Within a condition the rows follow the model order (Haiku before Opus), then the task id."""
    rows = [lit(OPUS, "A", "L1", 1, dq=1100.0), lit(HAIKU, "A", "N1", 1, dq=2100.0)]
    b = plots.literature_parity(ctx_of(rows))
    assert [(r["model"], r["task_id"]) for r in _src(b, "Dq")] == [(HAIKU, "N1"), (OPUS, "L1")]


def test_literature_parity_a_run_exactly_on_the_cushioned_limit_is_inside(monkeypatch):
    monkeypatch.setattr(data, "pilot_tasks", lambda: {"R1": _task("literature_all", (10.0, 10.0, 10.0),
                                                                     (0.05, 0.10, 0.15))})
    limit = 100.0 * 0.05 + 1e-9
    b = plots.literature_parity(ctx_of([row(HAIKU, "A", "R1", cls="literature_all", dq=10.5000000001)]))
    (r,) = b.source
    assert r["deviation_pct"] == limit and r["within_tolerance"] is True


def test_literature_parity_conditions_without_runs_are_left_out_and_the_rest_keep_their_colours(tasks):
    rows = [lit(HAIKU, "B", "L1", 1, dq=1100.0), lit(HAIKU, "C", "L1", 2, dq=900.0)]
    b = plots.literature_parity(ctx_of(rows))
    ax = _fig(b).axes[0]
    lines = [ln for ln in ax.lines if ln.get_gid() is not None]
    assert [ln.get_gid() for ln in lines] == ["data:B", "data:C"]
    assert [(ln.get_marker(), ln.get_markerfacecolor(), ln.get_markeredgecolor()) for ln in lines] == [
        ("s", SERIES["B"] + "99", SERIES["B"]), ("^", SERIES["C"] + "99", SERIES["C"])]
    assert [y for ln in lines for y in _any(ln).get_ydata()] == pytest.approx([10.0, -10.0])


def test_literature_parity_the_tolerance_limit_has_a_small_cushion(tasks):
    rows = [lit(HAIKU, "A", "L1", 1, dq=1050.000000005), lit(HAIKU, "A", "L1", 2, dq=1050.0000002)]
    b = plots.literature_parity(ctx_of(rows))
    assert [r["within_tolerance"] for r in _src(b, "Dq")] == [True, False]


def test_literature_parity_axes_scale_band_and_labels(tasks):
    b = plots.literature_parity(ctx_of(parity_rows()))
    fig = _fig(b)
    w, h = fig.get_size_inches()
    assert (w * 25.4, h * 25.4) == pytest.approx((177.8, 66))
    assert len(fig.axes) == 3
    expect = {"Dq": (5.0, 30, [-30, -5, 0, 5, 30]), "B": (10.0, 100, [-100, -10, 0, 10, 100]),
              "C": (15.0, 100, [-100, -15, 0, 15, 100])}
    for ax, p in zip(fig.axes, ("Dq", "B", "C"), strict=True):
        tol, lim, ticks = expect[p]
        assert ax.get_yscale() == "symlog" and _any(ax.yaxis.get_transform()).linthresh == max(tol, 1.0)
        assert ax.get_ylim() == (-lim, lim)
        assert isinstance(ax.yaxis.get_major_locator(), FixedLocator)
        assert list(_any(ax.yaxis.get_major_locator()).locs) == ticks
        assert [ax.yaxis.get_major_formatter()(v, 0) for v in (0, 5, -100, 0.5)] == ["0", "5", "-100", "0.5"]
        assert isinstance(ax.yaxis.get_minor_locator(), NullLocator)
        assert isinstance(ax.xaxis.get_minor_locator(), AutoMinorLocator)
        assert _any(ax.xaxis.get_minor_locator()).ndivs == 2
        assert ax.get_xlabel() == f"Reference {p} (cm$^{{-1}}$)" and ax.get_ylabel() == f"Deviation of {p} (%)"
        (band,) = ax.patches
        assert (_any(band).get_y(), _any(band).get_height()) == (-tol, 2 * tol) and band.get_zorder() == 0
        assert band.get_facecolor()[:3] == pytest.approx((0xe6 / 255, 0xeb / 255, 0xf6 / 255))
        assert band.get_linewidth() == 0
        (zero,) = [ln for ln in ax.lines if ln.get_gid() is None]
        assert (list(_any(zero).get_ydata()), zero.get_linewidth(), zero.get_zorder()) == ([0, 0], 0.5, 1)
        assert zero.get_color() == "#7a7a7a"
        (label,) = [t for t in ax.texts if t.get_text().startswith("tolerance")]
        assert label.get_text() == f"tolerance ±{tol:g} %" and label.get_position() == (0.98, tol)
        assert (_any(label).get_ha(), _any(label).get_va(), label.get_fontsize(), label.get_color()) == (
            "right", "bottom", 5.5, "#4d4d4d")
        assert label.get_transform() == ax.get_yaxis_transform()  # x in axes units, y in data units
        assert _any(ax.yaxis.get_transform()).linscale == 1.0
        assert not [t for t in ax.texts if t.get_text() == "no data"]
    assert not fig.axes[0].get_shared_y_axes().joined(fig.axes[0], fig.axes[1])
    assert [t.get_text() for ax in fig.axes for t in ax.texts if len(t.get_text()) == 1] == ["a", "b", "c"]
    assert [t.get_gid() for t in fig.texts] == ["key:A", "key:B", "key:C", "footer"]


def test_literature_parity_draws_every_run_as_a_hollow_marker_at_its_reference(tasks):
    b = plots.literature_parity(ctx_of(parity_rows()))
    for ax, p in zip(_fig(b).axes, ("Dq", "B", "C"), strict=True):
        rows = _src(b, p)
        for cond in "ABC":
            sel = [r for r in rows if r["condition"] == cond]
            lines = [ln for ln in ax.lines if ln.get_gid() == f"data:{cond}"]
            assert len(lines) == (1 if sel else 0)
            if not sel:
                continue
            (ln,) = lines
            assert list(_any(ln).get_xdata()) == [r["reference"] for r in sel]
            assert list(_any(ln).get_ydata()) == pytest.approx([r["deviation_pct"] for r in sel])
            assert (ln.get_marker(), ln.get_linestyle(), ln.get_markersize(), ln.get_markeredgewidth()) == (
                MARK[cond], "None", 2.8, 0.4)
            assert (ln.get_markerfacecolor(), ln.get_markeredgecolor()) == (SERIES[cond] + "99", SERIES[cond])


@pytest.mark.parametrize("dev,lim,extra", [
    (20.0, 30, False), (30.0, 30, False), (30.5, 100, False), (100.0, 100, False), (100.5, 300, True),
    (150.0, 300, True), (300.0, 300, True), (301.0, 1000, True), (1000.0, 1000, True), (2500.0, 3000, True),
    (3000.0, 3000, True), (3500.0, 10000, True), (10000.0, 10000, True), (12000.0, 1e9, True), (-250.0, 300, True)])
def test_literature_parity_axis_limit_ladder(tasks, dev, lim, extra):
    b = plots.literature_parity(ctx_of([lit(HAIKU, "A", "L1", dq=1000.0 * (1 + dev / 100.0))]))
    ax = _fig(b).axes[0]
    assert ax.get_ylim() == (-lim, lim)
    want = sorted({-lim, -5, 0, 5, lim} | ({-100, 100} if extra else set()))
    assert list(_any(ax.yaxis.get_major_locator()).locs) == want
    assert [ax.yaxis.get_major_formatter()(v, 0) for v in want] == [f"{v:g}" for v in want]


@pytest.mark.parametrize("dq", [1.854e11, 1e13, float("inf")])
def test_literature_parity_a_deviation_beyond_the_ladder_keeps_the_top_limit(tasks, dq):
    """Hz instead of cm-1 (or an infinite answer) must not abort the figure run: the limit stays at the ladder top."""
    b = plots.literature_parity(ctx_of([lit(HAIKU, "A", "L1", dq=dq), lit(HAIKU, "A", "L1", 2, dq=1100.0)]))
    ax = _fig(b).axes[0]
    assert ax.get_ylim() == (-1e9, 1e9)
    assert len(_src(b, "Dq")) == 2
    _fig(b).canvas.draw()  # the clipped marker does not break drawing


def test_literature_parity_a_wide_tolerance_counts_twice_towards_the_limit_and_drops_the_100_ticks(monkeypatch):
    tasks = {"W1": _task("literature_all", (1000.0, 500.0, 2000.0), (0.6, 0.5, 0.49))}
    monkeypatch.setattr(data, "pilot_tasks", lambda: tasks)
    rows = [row(HAIKU, "A", "W1", cls="literature_all", dq=1100.0, b=500.0 * 5.0, c=2000.0 * 5.0)]
    b = plots.literature_parity(ctx_of(rows))
    dq, bb, cc = _fig(b).axes
    assert dq.get_ylim() == (-300, 300) and list(_any(dq.yaxis.get_major_locator()).locs) == [-300, -60, 0, 60, 300]
    assert bb.get_ylim() == (-1000, 1000) and list(_any(bb.yaxis.get_major_locator()).locs) == [-1000, -50, 0, 50, 1000]
    assert cc.get_ylim() == (-1000, 1000)
    assert list(_any(cc.yaxis.get_major_locator()).locs) == [-1000, -100, -49, 0, 49, 100, 1000]
    assert [_any(ax.yaxis.get_transform()).linthresh for ax in (dq, bb, cc)] == [60.0, 50.0, 49.0]
    assert [t.get_text() for t in dq.texts if t.get_text().startswith("tol")] == ["tolerance ±60 %"]
    mid = {"M1": _task("literature_all", (1000.0, 500.0, 2000.0), (0.12, 0.1, 0.15))}
    monkeypatch.setattr(data, "pilot_tasks", lambda: mid)
    one = plots.literature_parity(ctx_of([row(HAIKU, "A", "M1", cls="literature_all", dq=1010.0)]))
    assert _fig(one).axes[0].get_ylim() == (-30, 30)  # twice the tolerance (24) still fits the first step


def test_literature_parity_uses_the_largest_tolerance_of_the_parameter(monkeypatch):
    tasks = {"A1": _task("literature_all", (1000.0, 500.0, 2000.0), (0.05, 0.1, 0.15)),
             "A2": _task("literature_all", (1000.0, 500.0, 2000.0), (0.20, 0.1, 0.15))}
    monkeypatch.setattr(data, "pilot_tasks", lambda: tasks)
    rows = [row(HAIKU, "A", t, cls="literature_all", dq=1010.0) for t in ("A1", "A2")]
    b = plots.literature_parity(ctx_of(rows))
    ax = _fig(b).axes[0]
    assert [t.get_text() for t in ax.texts if t.get_text().startswith("tol")] == ["tolerance ±20 %"]
    assert (_any(ax.patches[0]).get_y(), _any(ax.patches[0]).get_height()) == (-20.0, 40.0)
    assert _any(ax.yaxis.get_transform()).linthresh == 20.0
    assert ax.get_ylim() == (-100, 100)  # twice the tolerance, 40, is the larger of the two numbers


def test_literature_parity_a_parameter_without_data_says_so(tasks):
    rows = [lit(HAIKU, "A", "E1", dq=1500.0, b=600.0, c=None)]
    b = plots.literature_parity(ctx_of(rows))
    dq, bb, cc = _fig(b).axes
    assert [t.get_text() for t in cc.texts if t.get_text() != "c"] == ["tolerance ±0 %", "no data"]
    (msg,) = [t for t in cc.texts if t.get_text() == "no data"]
    assert msg.get_position() == (0.5, 0.5) and _any(msg).get_ha() == "center" and msg.get_color() == "#4d4d4d"
    assert msg.get_transform() is cc.transAxes
    assert cc.get_ylim() == (-30, 30) and list(_any(cc.yaxis.get_major_locator()).locs) == [-30, 0, 30]
    assert _any(cc.yaxis.get_transform()).linthresh == 1.0
    assert (_any(cc.patches[0]).get_y(), _any(cc.patches[0]).get_height()) == (0, 0)
    assert not [t for t in dq.texts if t.get_text() == "no data"]
    assert {r["param"] for r in b.source} == {"Dq", "B"}


def test_literature_parity_skips_runs_without_a_value_and_keeps_a_value_of_zero(tasks):
    rows = [lit(HAIKU, "A", "L1", 1, dq=0.0, b=None, c=2000.0), lit(HAIKU, "B", "L1", 1, dq=None, b=500.0)]
    b = plots.literature_parity(ctx_of(rows))
    assert [(r["param"], r["condition"], r["deviation_pct"]) for r in b.source] == [
        ("Dq", "A", -100.0), ("B", "B", 0.0), ("C", "A", 0.0)]


def test_literature_parity_without_literature_answers_raises(tasks):
    with pytest.raises(data.NoDataError, match=r"^no evaluable runs for literature_parity \(literature_all / "
                                               r"literature_new / experimental answers\)$"):
        plots.literature_parity(ctx_of([lit(HAIKU, "A", "X1", dq=1.0)]))
    with pytest.raises(data.NoDataError):
        plots.literature_parity(ctx_of([]))
    with pytest.raises(data.NoDataError):
        plots.literature_parity(ctx_of([lit(HAIKU, "A", "T1", b=3.0)]))  # no tolerance for B: nothing drawn


def test_literature_parity_takes_the_class_from_the_run_row(tasks):
    rows = [row(HAIKU, "A", "L1", cls="curve", dq=1100.0), row(HAIKU, "A", "L1", 2, cls="experimental", dq=1100.0)]
    b = plots.literature_parity(ctx_of(rows))
    assert [(r["k_index"], r["class"]) for r in b.source] == [(2, "experimental")]


# ------------------------------------------------------------------------------------------------ efficiency
def eff(model, cond, task, k, ok, cost=None, tok=None, wall=None, measured=True):
    return row(model, cond, task, k, ok=ok, cost_usd=cost, output_tokens=tok, wall_s=wall, wall_is_measured=measured)


def efficiency_rows():
    return [eff(HAIKU, "A", "t1", 1, True, 0.10, 1000.0, 10.0), eff(HAIKU, "A", "t1", 2, False, 0.30, 3000.0, 30.0),
            eff(HAIKU, "A", "t2", 1, True, 0.20, 2000.0, 20.0, measured=False),
            eff(HAIKU, "B", "t1", 1, False, 0.5, 400.0, 4.0),
            eff(HAIKU, "C", "t1", 1, True),
            eff(SONNET, "A", "t1", 1, True, 0.0, 10.0, 1.0),
            eff(OPUS, "A", "t1", 1, True, 4.0, 40.0, 4.5),
            eff(GATE, "A", "t1", 1, True, 0.0, 500.0, 5.0), eff(GATE, "A", "t2", 1, False, 0.0, 700.0, 7.0)]


def _cell(b, metric, model, cond):
    (r,) = [r for r in b.source if (r["metric"], r["model"], r["condition"]) == (metric, model, cond)]
    return r


def test_efficiency_source_rows_state_the_status_of_every_cell():
    b = plots.efficiency(ctx_of(efficiency_rows()))
    assert b.columns == ["metric", "unit", "model", "model_label", "condition", "n_runs", "n_correct", "total", "value",
                         "ci_lo", "ci_hi", "status", "wall_measured"]
    order = [(HAIKU, "A"), (HAIKU, "B"), (HAIKU, "C"), (SONNET, "A"), (OPUS, "A"), (GATE, "A")]  # not alphabetical
    assert [(r["metric"], r["model"], r["condition"]) for r in b.source] == [
        (m, mo, c) for m in ("cost_usd", "output_tokens", "wall_s") for mo, c in order]
    assert [r["unit"] for r in b.source[::6]] == ["usd", "tokens", "seconds"]
    opus = _cell(b, "cost_usd", OPUS, "A")
    assert (opus["status"], opus["value"], opus["model_label"], opus["n_runs"]) == ("ok", 4.0, "Opus 4.7", 1)
    ok = _cell(b, "cost_usd", HAIKU, "A")
    assert (ok["n_runs"], ok["n_correct"], ok["status"], ok["model_label"]) == (3, 2, "ok", "Haiku 5.5")
    assert (ok["total"], ok["value"]) == (pytest.approx(0.6), pytest.approx(0.3))
    lo, hi = cluster_bootstrap([0.4, 0.2], [1, 1])
    assert (ok["ci_lo"], ok["ci_hi"]) == pytest.approx((min(lo, 0.3), max(hi, 0.3)))
    tok = _cell(b, "output_tokens", HAIKU, "A")
    assert (tok["total"], tok["value"], tok["status"]) == (6000.0, 3000.0, "ok")
    wall = _cell(b, "wall_s", HAIKU, "A")
    assert (wall["total"], wall["value"], wall["wall_measured"]) == (60.0, 30.0, False)
    assert _cell(b, "wall_s", GATE, "A")["wall_measured"] is True
    assert _cell(b, "cost_usd", HAIKU, "A")["wall_measured"] is None and tok["wall_measured"] is None
    zero = _cell(b, "cost_usd", HAIKU, "B")
    assert (zero["status"], zero["n_runs"], zero["n_correct"], zero["total"], zero["value"]) == (
        "0 correct", 1, 0, 0.5, None)
    assert (zero["ci_lo"], zero["ci_hi"]) == (None, None)
    none = _cell(b, "cost_usd", HAIKU, "C")
    assert (none["status"], none["n_runs"], none["n_correct"], none["total"], none["value"],
            none["wall_measured"]) == ("not reported", 0, 0, None, None, None)
    assert _cell(b, "wall_s", HAIKU, "C")["wall_measured"] is None
    free = _cell(b, "cost_usd", SONNET, "A")
    assert (free["status"], free["n_runs"], free["n_correct"], free["total"], free["value"]) == (
        "not reported", 1, 1, 0.0, None)
    gate = _cell(b, "cost_usd", GATE, "A")
    assert (gate["status"], gate["n_runs"], gate["n_correct"], gate["total"], gate["value"]) == (
        "no real cost (gateway)", 2, 1, 0.0, None)
    gt = _cell(b, "output_tokens", GATE, "A")
    assert (gt["status"], gt["n_runs"], gt["n_correct"], gt["total"], gt["value"]) == ("ok", 2, 1, 1200.0, 1200.0)
    glo, ghi = cluster_bootstrap([500.0, 700.0], [1, 0])
    assert (gt["ci_lo"], gt["ci_hi"]) == pytest.approx((min(glo, 1200.0), max(ghi, 1200.0)))
    assert b.ci == {"method": "task-clustered percentile bootstrap, 95 %", "unit": "task, k repetitions kept together"}
    assert b.notes == ["wall time: runner-measured wall_time_s where present, else the result event's duration_s",
                       "log x axes"]
    assert b.caption.startswith("Efficiency: spend per correct answer = total over the evaluable runs divided by the "
                                "number of correct runs (bar: 95 % task-clustered bootstrap). PILOT data, not "
                                "confirmatory. Cells with no correct answer or no reported cost carry the label "
                                "instead of a dot; gateway models have no real cost, the price Claude Code "
                                "reports for them is an estimate for an unknown model.")


def test_efficiency_only_rows_with_a_value_count_for_the_cell():
    rows = [eff(HAIKU, "A", "t1", 1, True, 1.0, 10.0, 5.0), eff(HAIKU, "A", "t1", 2, True, None, 30.0, None),
            eff(HAIKU, "A", "t2", 1, False, 3.0, 20.0, 9.0)]
    b = plots.efficiency(ctx_of(rows))
    cost = _cell(b, "cost_usd", HAIKU, "A")
    assert (cost["n_runs"], cost["n_correct"], cost["total"], cost["value"]) == (2, 1, 4.0, 4.0)
    tok = _cell(b, "output_tokens", HAIKU, "A")
    assert (tok["n_runs"], tok["n_correct"], tok["total"], tok["value"]) == (3, 2, 60.0, 30.0)
    wall = _cell(b, "wall_s", HAIKU, "A")
    assert (wall["n_runs"], wall["n_correct"], wall["total"], wall["value"]) == (2, 1, 14.0, 14.0)


def test_efficiency_interval_is_widened_to_hold_the_estimate_and_collapses_without_one(monkeypatch):
    calls = []
    answers = iter([(5.0, 6.0), (-1.0, 1.0), (math.nan, math.nan)] * 3)

    def fake(num, den):
        calls.append((list(num), list(den)))
        return next(answers)

    monkeypatch.setattr(plots, "cluster_bootstrap", fake)
    rows = [eff(HAIKU, "A", "b", 1, True, 2.0, 2.0, 2.0), eff(HAIKU, "A", "a", 1, False, 1.0, 1.0, 1.0),
            eff(HAIKU, "A", "a", 2, True, 3.0, 3.0, 3.0)]
    b = plots.efficiency(ctx_of(rows))
    cost, tok, wall = (_cell(b, m, HAIKU, "A") for m in ("cost_usd", "output_tokens", "wall_s"))
    assert cost["value"] == 3.0  # 6 USD over two correct runs
    assert calls[0] == ([4.0, 2.0], [1, 1])  # tasks in id order: a (1 + 3 USD, one correct), b (2 USD, one correct)
    assert (cost["ci_lo"], cost["ci_hi"]) == (3.0, 6.0)  # a bar that lies above the dot is pulled down to it
    assert (tok["ci_lo"], tok["ci_hi"]) == (-1.0, 3.0)  # and one that lies below is pulled up
    assert (wall["ci_lo"], wall["ci_hi"]) == (3.0, 3.0)  # no interval: the bar has no length
    assert [c[0] for c in calls[1:3]] == [[4.0, 2.0], [4.0, 2.0]] and len(calls) == 3


def test_efficiency_draws_three_log_panels_of_dots_with_bars():
    b = plots.efficiency(ctx_of(efficiency_rows()))
    fig = _fig(b)
    w, h = fig.get_size_inches()
    assert (w * 25.4, h * 25.4) == pytest.approx((177.8, 24 + 2.5 * 4 * 4))
    assert len(fig.axes) == 3
    models = [HAIKU, SONNET, OPUS, GATE]
    ypos = plots._model_rows_y(models)
    labels = ["Cost per correct answer (USD)", "Output tokens per correct answer (1)",
              "Wall time per correct answer (s)"]
    for ax, metric, label in zip(fig.axes, ("cost_usd", "output_tokens", "wall_s"), labels, strict=True):
        assert ax.get_xscale() == "log" and ax.get_xlabel() == label
        assert isinstance(ax.yaxis.get_minor_locator(), NullLocator)
        assert ax.get_shared_y_axes().joined(ax, fig.axes[0])
        assert ax.get_ylim() == (-1, 15)
        ok = {(r["model"], r["condition"]): r for r in b.source if r["metric"] == metric and r["status"] == "ok"}
        for j, cond in enumerate("ABC"):
            cells = [(i, m) for i, m in enumerate(models) if (m, cond) in ok]
            conts = containers(ax, cond)
            assert len(conts) == (1 if cells else 0)
            if not cells:
                continue
            cont = conts[0]
            assert list(cont[0].get_xdata()) == pytest.approx([ok[(m, cond)]["value"] for _i, m in cells])
            assert list(cont[0].get_ydata()) == [ypos[(i, j)] for i, _m in cells]
            want = [[[ok[(m, cond)]["ci_lo"], ypos[(i, j)]], [ok[(m, cond)]["ci_hi"], ypos[(i, j)]]] for i, m in cells]
            assert np.allclose(segments(cont), want)
            assert (cont[0].get_marker(), cont[0].get_color()) == (MARK[cond], SERIES[cond])
    assert list(fig.axes[0].get_yticks()) == [13, 9, 5, 1]
    assert [t.get_text() for t in fig.axes[0].get_yticklabels()] == ["Haiku 5.5", "Sonnet 5.5", "Opus 4.7", "qwen3"]
    # only the first panel carries the model labels (and so has its y ticks removed)
    assert fig.axes[0].yaxis.get_major_ticks()[0].tick1line.get_markersize() == 0
    assert all(ax.yaxis.get_major_ticks()[0].tick1line.get_markersize() > 0 for ax in fig.axes[1:])
    assert [t.get_text() for ax in fig.axes for t in ax.texts if len(t.get_text()) == 1] == ["a", "b", "c"]
    assert [t.get_gid() for t in fig.texts] == ["key:A", "key:B", "key:C", "footer"]


def test_efficiency_labels_cells_that_have_no_dot():
    b = plots.efficiency(ctx_of(efficiency_rows()))
    models = [HAIKU, SONNET, OPUS, GATE]
    ypos = plots._model_rows_y(models)
    for ax, metric in zip(_fig(b).axes, ("cost_usd", "output_tokens", "wall_s"), strict=True):
        shown = {(t.get_text(), round(t.get_position()[1])): t for t in ax.texts if t.get_gid() is None
                 and len(t.get_text()) > 1}
        want = {}
        for r in b.source:
            if r["metric"] == metric and r["status"] != "ok":
                want[(r["status"], ypos[(models.index(r["model"]), "ABC".index(r["condition"]))])] = r["condition"]
        assert set(shown) == set(want)
        for key, cond in want.items():
            t = shown[key]
            assert t.get_position()[0] == 0.015 and t.get_color() == SERIES[cond]
            assert (t.get_fontsize(), _any(t).get_va(), _any(t).get_ha()) == (5, "center", "left")
            assert t.get_transform() == ax.get_yaxis_transform()
    cost_labels = sorted(t.get_text() for t in _fig(b).axes[0].texts if len(t.get_text()) > 1)
    assert cost_labels == ["0 correct", "no real cost (gateway)", "not reported", "not reported"]
    assert sorted(t.get_text() for t in _fig(b).axes[1].texts if len(t.get_text()) > 1) == ["0 correct", "not reported"]


def test_efficiency_a_panel_without_any_dot_says_no_data():
    rows = [eff(GATE, "A", "t1", 1, True, 0.0, 500.0, 5.0)]
    b = plots.efficiency(ctx_of(rows))
    cost, tok, wall = _fig(b).axes
    (msg,) = [t for t in cost.texts if t.get_text() == "no data"]
    assert msg.get_position() == (0.5, 0.5) and _any(msg).get_ha() == "center" and msg.get_color() == "#4d4d4d"
    assert msg.get_transform() is cost.transAxes
    assert [t.get_text() for t in tok.texts if t.get_text() == "no data"] == []
    assert [t.get_text() for t in wall.texts if t.get_text() == "no data"] == []
    assert cost.get_ylim() == (-1, 3)
    only_cost = plots.efficiency(ctx_of([eff(HAIKU, "A", "t1", 1, True, cost=1.0)]))
    has_msg = [bool([t for t in ax.texts if t.get_text() == "no data"]) for ax in _fig(only_cost).axes]
    assert has_msg == [False, True, True]


def test_efficiency_footer_and_options():
    rows = [eff(HAIKU, "A", "t1", 1, True, 1.0, 2.0, 3.0)]
    b = plots.efficiency(ctx_of(rows, footer=False))
    assert [t.get_gid() for t in _fig(b).texts] == ["key:A", "key:B", "key:C"]
    assert _fig(b).get_size_inches()[1] * 25.4 == pytest.approx(24 + 2.5 * 4)
    with pytest.raises(data.NoDataError, match=r"^no evaluable runs for efficiency$"):
        plots.efficiency(ctx_of([]))
