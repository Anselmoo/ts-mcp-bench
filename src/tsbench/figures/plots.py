"""accuracy_by_model, accuracy_by_class, literature_parity and efficiency: the data figures. Every builder returns a
`Built` (figure, source rows, caption); the source rows hold the exact numbers drawn, and the drawn data artists carry
the gid `data:<condition>` so a test can read the plotted values back."""
from __future__ import annotations

import math

from matplotlib.ticker import AutoMinorLocator, FixedLocator, FuncFormatter, NullLocator

from tsbench.core.intervals import cluster_bootstrap, wilson
from tsbench.figures import data
from tsbench.figures.render import Built, Context, condition_key, condition_style, footer_text, reserve, setup

MM_PER_ROW = 2.5
LIT_CLASSES = ("literature_all", "literature_new", "experimental")
PARAMS = (("Dq", "dq"), ("B", "b"), ("C", "c"))
MIN_BOOTSTRAP_TASKS = 5  # a task bootstrap over fewer clusters is degenerate (one task: zero width); Wilson instead


# ------------------------------------------------------------------------------------------------ statistics of a cell
def interval_method(rows, method: str) -> str:
    """The interval `share` uses for these rows: the bootstrap only from `MIN_BOOTSTRAP_TASKS` tasks on."""
    if method == "bootstrap" and len(data.per_task(rows)) >= MIN_BOOTSTRAP_TASKS:
        return "bootstrap"
    return "wilson"


def _fallback_notes(source, ci: str) -> list[str]:
    """One note when `--ci bootstrap` left cells on the Wilson interval for want of tasks."""
    n = sum(r["ci_method"] == "wilson" for r in source)
    if ci != "bootstrap" or n == 0:
        return []
    return [f"{n} of {len(source)} cells have fewer than {MIN_BOOTSTRAP_TASKS} tasks: their bar is the Wilson "
            f"interval (ci_method wilson), not the bootstrap"]


def effective_ci(source, ci: str) -> tuple[dict, str]:
    """(ci meta, caption label) of what the cells of `source` really drew: the bootstrap only if one cell used it, and
    a mixed figure names both intervals and how many cells fell back to Wilson."""
    wilson_n = sum(r["ci_method"] == "wilson" for r in source)
    if ci != "bootstrap" or wilson_n == len(source):
        return ci_meta("wilson"), ci_meta("wilson")["method"].split(",")[0]
    boot = ci_meta("bootstrap")
    label = boot["method"].split(",")[0]
    if wilson_n == 0:
        return boot, label
    why = f"Wilson score interval for the {wilson_n} of {len(source)} cells with fewer than {MIN_BOOTSTRAP_TASKS} tasks"
    return ({"method": f"{boot['method']} ({why})", "unit": f"{boot['unit']}; run for the Wilson cells"},
            f"{label}; {why}")


def share(rows, method: str):
    """(share %, lo %, hi %) of correct runs; Wilson over runs or a bootstrap over tasks (k repetitions together) from
    `MIN_BOOTSTRAP_TASKS` tasks on."""
    n = len(rows)
    k = sum(r["correct"] for r in rows)
    if interval_method(rows, method) == "bootstrap":
        tasks = data.per_task(rows)
        lo, hi = cluster_bootstrap([sum(r["correct"] for r in rs) for _t, rs in tasks], [len(rs) for _t, rs in tasks])
    else:
        lo, hi = wilson(k, n)
    return 100.0 * k / n, 100.0 * lo, 100.0 * hi


def ci_meta(method: str) -> dict:
    if method == "bootstrap":
        return {"method": "task-clustered percentile bootstrap, 95 %", "unit": "task, k repetitions kept together"}
    return {"method": "Wilson score interval, 95 %", "unit": "run"}


def _sets_of(rows) -> str:
    return ";".join(sorted({r["set"] for r in rows}))


def _efforts_of(rows) -> str:
    return ";".join(sorted({r["effort"] for r in rows}))


def _require(rows, what: str):
    if not rows:
        raise data.NoDataError(f"no evaluable runs for {what}")


def _style_x(ax, pct: bool = True):
    ax.xaxis.set_minor_locator(AutoMinorLocator(2))
    ax.yaxis.set_minor_locator(NullLocator())
    if pct:
        ax.set_xlim(-2, 102)
        ax.set_xticks([0, 25, 50, 75, 100])


def _finish(fig, ctx: Context, jfs, key: bool = True):
    from tsbench.figures.render import footer_line
    reserve(fig, ctx.footer, key)
    if key:
        condition_key(fig, jfs)
    if ctx.footer:
        footer_text(fig, footer_line(ctx))


def _model_rows_y(models, n_cond: int = 3):
    """y position per (model index, condition index): first model and condition at the top."""
    pitch = n_cond + 1
    return {(i, j): (len(models) - 1 - i) * pitch + (n_cond - 1 - j) for i in range(len(models)) for j in range(n_cond)}


def _dot_rows(ax, jfs, cells: dict, models: list, xcol: str, lo: str, hi: str, ylab=True):
    """Dots with caps-free error bars, one errorbar call per condition. `cells[(model, cond)]` is a dict with the
    columns."""
    sty = condition_style(jfs)
    ypos = _model_rows_y(models)
    for j, c in enumerate(data.CONDITIONS):
        xs, ys, los, his = [], [], [], []
        for i, m in enumerate(models):
            cell = cells.get((m, c))
            if cell is None or cell[xcol] is None:
                continue
            xs.append(cell[xcol])
            ys.append(ypos[(i, j)])
            los.append(max(0.0, cell[xcol] - cell[lo]))
            his.append(max(0.0, cell[hi] - cell[xcol]))
        if not xs:
            continue
        col, mk = sty[c]
        eb = ax.errorbar(xs, ys, xerr=[los, his], fmt=mk, color=col, ms=3, mew=0.5, mfc=col, elinewidth=0.75, capsize=0,
                         linestyle="none")
        eb[0].set_gid(f"data:{c}")
    if ylab:
        ax.set_yticks([(len(models) - 1 - i) * 4 + 1 for i in range(len(models))])
        ax.set_yticklabels([data.model_label(m) for m in models])
        ax.tick_params(axis="y", length=0)
    ax.set_ylim(-1, len(models) * 4 - 1)
    return ypos


# ------------------------------------------------------------------------------------------------ accuracy_by_model
CAP1 = ("Share of correct answers per model and condition (dot: share, bar: 95 % {ci}). "
        "PILOT data, not confirmatory; cells pool the pilot task classes available per model and condition "
        "(different task mixes and k), so compare conditions within a model.")


def accuracy_by_model(ctx: Context) -> Built:
    plt, jfs = setup(ctx.theme)
    _require(ctx.rows, "accuracy_by_model")
    cell_rows = data.group_by(ctx.rows, "model", "condition")
    models = sorted({m for m, _c in cell_rows}, key=data.model_key)
    cells, source = {}, []
    for (m, c), rows in sorted(cell_rows.items(), key=lambda kv: (data.model_key(kv[0][0]), kv[0][1])):
        s, lo, hi = share(rows, ctx.ci)
        cells[(m, c)] = {"share": s, "lo": lo, "hi": hi}
        source.append({"model": m, "model_label": data.model_label(m), "condition": c, "n_runs": len(rows),
                       "n_tasks": len({r["task_id"] for r in rows}), "n_correct": sum(r["correct"] for r in rows),
                       "share_pct": s, "ci_lo_pct": lo, "ci_hi_pct": hi,
                       "ci_method": interval_method(rows, ctx.ci), "efforts": _efforts_of(rows),
                       "sets": _sets_of(rows)})
    h = 24 + MM_PER_ROW * 4 * len(models)
    fig, ax = jfs.figure("single", h)
    _dot_rows(ax, jfs, cells, models, "share", "lo", "hi")
    _style_x(ax)
    ax.set_xlabel("Share correct (%)")
    # direct labels on the first model's three rows
    sty = condition_style(jfs)
    ypos = _model_rows_y(models)
    for j, c in enumerate(data.CONDITIONS):
        cell = cells.get((models[0], c))
        if cell is None:
            continue
        right = cell["hi"] < 72
        ax.text(cell["hi"] + 2.5 if right else cell["lo"] - 2.5, ypos[(0, j)], f"{c}  {data.COND_NAME[c]}",
                color=sty[c][0], fontsize=6, va="center", ha="left" if right else "right")
    _finish(fig, ctx, jfs, key=False)
    cols = ["model", "model_label", "condition", "n_runs", "n_tasks", "n_correct", "share_pct",
            "ci_lo_pct", "ci_hi_pct", "ci_method", "efforts", "sets"]
    ci, label = effective_ci(source, ctx.ci)
    return Built(fig, cols, source, CAP1.format(ci=label), ci=ci,
                 notes=["models with HTTP 429 / API-error runs: those runs are excluded, not counted wrong",
                        *_fallback_notes(source, ctx.ci)])


# ------------------------------------------------------------------------------------------------ accuracy_by_class
def accuracy_by_class(ctx: Context) -> Built:
    plt, jfs = setup(ctx.theme)
    _require(ctx.rows, "accuracy_by_class")
    cell_rows = data.group_by(ctx.rows, "model", "class", "condition")
    models = sorted({k[0] for k in cell_rows}, key=data.model_key)
    classes = sorted({k[1] for k in cell_rows})
    cells, source = {}, []
    for (m, cls, c), rows in sorted(cell_rows.items(), key=lambda kv: (data.model_key(kv[0][0]), kv[0][1], kv[0][2])):
        s, lo, hi = share(rows, ctx.ci)
        cells[(m, cls, c)] = (s, lo, hi)
        source.append({"model": m, "model_label": data.model_label(m), "class": cls, "condition": c,
                       "n_runs": len(rows),
                       "n_tasks": len({r["task_id"] for r in rows}), "n_correct": sum(r["correct"] for r in rows),
                       "share_pct": s, "ci_lo_pct": lo, "ci_hi_pct": hi,
                       "ci_method": interval_method(rows, ctx.ci)})
    ncols = min(len(models), 3)
    nrows = math.ceil(len(models) / ncols)
    h = 20 + nrows * (6 + len(classes) * 3.6)
    fig, axs = jfs.figure("double", h, nrows=nrows, ncols=ncols, sharex=True, sharey=True, squeeze=False)
    sty = condition_style(jfs)
    off = {"A": 0.25, "B": 0.0, "C": -0.25}
    ymap = {cls: len(classes) - 1 - i for i, cls in enumerate(classes)}
    used = []
    for idx, m in enumerate(models):
        ax = axs[idx // ncols][idx % ncols]
        used.append(ax)
        for c in data.CONDITIONS:
            pts = [(cells[(m, cls, c)], ymap[cls] + off[c]) for cls in classes if (m, cls, c) in cells]
            if not pts:
                continue
            col, mk = sty[c]
            xs = [p[0][0] for p in pts]
            xerr = [[max(0.0, p[0][0] - p[0][1]) for p in pts], [max(0.0, p[0][2] - p[0][0]) for p in pts]]
            eb = ax.errorbar(xs, [p[1] for p in pts], xerr=xerr,
                             fmt=mk, color=col, ms=2.5, mew=0.4, elinewidth=0.5, capsize=0, linestyle="none")
            eb[0].set_gid(f"data:{c}")
        ax.set_title(data.model_label(m), fontsize=7, loc="center")
        _style_x(ax)
        ax.set_yticks([ymap[cls] for cls in classes])
        ax.set_yticklabels([data.class_label(cls) for cls in classes])
        ax.tick_params(axis="y", length=0)
        ax.set_ylim(-0.7, len(classes) - 0.3)
        ax.grid(True, axis="y", color=jfs.COLORS["grid"], lw=0.4)
        if idx + ncols >= len(models):  # no drawn axes below: the lowest of its column
            ax.set_xlabel("Share correct (%)")
    for idx in range(len(models), nrows * ncols):
        axs[idx // ncols][idx % ncols].set_visible(False)
    jfs.panel_labels(used)
    _finish(fig, ctx, jfs)
    cols = ["model", "model_label", "class", "condition", "n_runs", "n_tasks", "n_correct", "share_pct", "ci_lo_pct",
            "ci_hi_pct", "ci_method"]
    ci, label = effective_ci(source, ctx.ci)
    cap = ("Share correct per task class, condition and model (95 % " + label +
           "). PILOT data, not confirmatory; a class has 1 to 10 pilot tasks, so intervals are wide.")
    return Built(fig, cols, source, cap, ci=ci, notes=_fallback_notes(source, ctx.ci))


# ------------------------------------------------------------------------------------------------ literature_parity
def literature_parity(ctx: Context) -> Built:
    plt, jfs = setup(ctx.theme)
    tasks = data.pilot_tasks()
    pts = {p: [] for p, _ in PARAMS}
    for r in ctx.rows:
        if r["class"] not in LIT_CLASSES:
            continue
        t = tasks[r["task_id"]]
        for p, col in PARAMS:
            ref = (t.get("reference") or {}).get(p)
            tol = (t.get("tolerance") or {}).get(p)
            val = r[col]
            if ref in (None, 0) or tol is None or val is None:
                continue
            dev = 100.0 * (val - ref) / ref
            pts[p].append({"param": p, "model": r["model"], "model_label": data.model_label(r["model"]),
                           "condition": r["condition"], "class": r["class"], "task_id": r["task_id"],
                           "k_index": r["k_index"],
                           "reference": float(ref), "value": float(val), "deviation_pct": dev,
                           "tolerance_pct": 100.0 * tol, "within_tolerance": abs(dev) <= 100.0 * tol + 1e-9})
    source = [row for p, _ in PARAMS
              for row in sorted(pts[p], key=lambda x: (x["condition"], data.model_key(x["model"]),
                                                       x["task_id"], x["k_index"]))]
    _require(source, "literature_parity (literature_all / literature_new / experimental answers)")
    fig, axs = jfs.figure("double", 66, ncols=3, sharey=False)
    sty = condition_style(jfs)
    for ax, (p, _col) in zip(axs, PARAMS, strict=False):
        rows = pts[p]
        tols = {r["tolerance_pct"] for r in rows}
        tol = max(tols) if tols else 0.0
        ax.axhspan(-tol, tol, color=jfs.COLORS["fill-soft"], lw=0, zorder=0)
        ax.axhline(0, color=jfs.COLORS["rule"], lw=0.5, zorder=1)
        for c in data.CONDITIONS:
            sel = [r for r in rows if r["condition"] == c]
            if not sel:
                continue
            col, mk = sty[c]
            (ln,) = ax.plot([r["reference"] for r in sel], [r["deviation_pct"] for r in sel], linestyle="none",
                            marker=mk, ms=2.8, mew=0.4, mfc=col + "99", mec=col)
            ln.set_gid(f"data:{c}")
        big = max([abs(r["deviation_pct"]) for r in rows] + [tol * 2])
        # a deviation beyond 1e9 % (or inf) is clipped to the top of the ladder
        lim = next((v for v in (30, 100, 300, 1000, 3000, 10000, 1e9) if v >= big), 1e9)
        ax.set_yscale("symlog", linthresh=max(tol, 1.0), linscale=1.0)
        ax.set_ylim(-lim, lim)
        ticks = sorted({-lim, -tol, 0, tol, lim} | ({-100, 100} if lim >= 300 and tol < 50 else set()))
        ax.yaxis.set_major_locator(FixedLocator([t for t in ticks if -lim <= t <= lim]))
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _pos: f"{v:g}"))
        ax.yaxis.set_minor_locator(NullLocator())
        ax.xaxis.set_minor_locator(AutoMinorLocator(2))
        ax.text(0.98, tol, f"tolerance ±{tol:g} %", transform=ax.get_yaxis_transform(), ha="right", va="bottom",
                fontsize=5.5, color=jfs.COLORS["ink-muted"])
        ax.set_xlabel(f"Reference {p} (cm$^{{-1}}$)")
        ax.set_ylabel(f"Deviation of {p} (%)")
        if not rows:
            ax.text(0.5, 0.5, "no data", transform=ax.transAxes, ha="center", color=jfs.COLORS["ink-muted"])
    jfs.panel_labels(list(axs))
    _finish(fig, ctx, jfs)
    cols = ["param", "model", "model_label", "condition", "class", "task_id", "k_index", "reference", "value",
            "deviation_pct", "tolerance_pct", "within_tolerance"]
    cap = ("Literature parity: parameter returned by the model against the oracle reference of the task "
           "(forward-model least squares for literature_all / literature_new, closed form for experimental), as signed "
           "deviation in %. Grey band: scoring tolerance. PILOT data, not confirmatory.")
    notes = ["experimental tasks have no C (not required); signed deviation = (model - reference) / reference",
             "classes present: " + ",".join(sorted({r["class"] for r in source}))]
    return Built(fig, cols, source, cap, notes=notes)


# ------------------------------------------------------------------------------------------------ efficiency
EFF_PANELS = (("cost_usd", "Cost per correct answer (USD)", "usd"),
              ("output_tokens", "Output tokens per correct answer (1)", "tokens"),
              ("wall_s", "Wall time per correct answer (s)", "seconds"))


def efficiency(ctx: Context) -> Built:
    plt, jfs = setup(ctx.theme)
    _require(ctx.rows, "efficiency")
    cell_rows = data.group_by(ctx.rows, "model", "condition")
    models = sorted({m for m, _c in cell_rows}, key=data.model_key)
    cells = {name: {} for name, _l, _u in EFF_PANELS}
    source = []
    for name, _label, unit in EFF_PANELS:
        for (m, c), rows in sorted(cell_rows.items(), key=lambda kv: (data.model_key(kv[0][0]), kv[0][1])):
            have = [r for r in rows if r[name] is not None]
            n_ok = sum(r["correct"] for r in have)
            total = sum(r[name] for r in have)
            val = lo = hi = None
            if name == "cost_usd" and not m.startswith("claude-"):
                # gateway run: the cost is the claude CLI's estimate from its default price list;
                # the gateway reports no USD cost
                status = "no real cost (gateway)"
            elif not have:
                status = "not reported"
            elif n_ok == 0:
                status = "0 correct"
            elif total <= 0:
                status = "not reported"
            else:
                status = "ok"
                val = total / n_ok
                tasks = data.per_task(have)
                lo, hi = cluster_bootstrap([sum(r[name] for r in rs) for _t, rs in tasks],
                                           [sum(r["correct"] for r in rs) for _t, rs in tasks])
                lo, hi = (min(lo, val), max(hi, val)) if lo == lo else (val, val)
                cells[name][(m, c)] = {"v": val, "lo": lo, "hi": hi}
            source.append({"metric": name, "unit": unit, "model": m, "model_label": data.model_label(m), "condition": c,
                           "n_runs": len(have), "n_correct": n_ok, "total": total if have else None, "value": val,
                           "ci_lo": lo, "ci_hi": hi, "status": status,
                           "wall_measured": (all(r["wall_is_measured"] for r in have)
                                             if name == "wall_s" and have else None)})
    h = 24 + MM_PER_ROW * 4 * len(models)
    fig, axs = jfs.figure("double", h, ncols=3, sharey=True)
    sty = condition_style(jfs)
    ypos = _model_rows_y(models)
    for ax, (name, label, _unit) in zip(axs, EFF_PANELS, strict=False):
        _dot_rows(ax, jfs, cells[name], models, "v", "lo", "hi", ylab=ax is axs[0])
        ax.set_xscale("log")
        ax.yaxis.set_minor_locator(NullLocator())
        ax.set_xlabel(label)
        for s in source:
            if s["metric"] == name and s["status"] != "ok":
                j = data.CONDITIONS.index(s["condition"])
                i = models.index(s["model"])
                ax.text(0.015, ypos[(i, j)], s["status"], transform=ax.get_yaxis_transform(), fontsize=5,
                        color=sty[s["condition"]][0], va="center", ha="left")
        if not cells[name]:
            ax.text(0.5, 0.5, "no data", transform=ax.transAxes, ha="center", color=jfs.COLORS["ink-muted"])
    jfs.panel_labels(list(axs))
    _finish(fig, ctx, jfs)
    cols = ["metric", "unit", "model", "model_label", "condition", "n_runs", "n_correct", "total", "value", "ci_lo",
            "ci_hi", "status", "wall_measured"]
    cap = ("Efficiency: spend per correct answer = total over the evaluable runs divided by the number of correct runs "
           "(bar: 95 % task-clustered bootstrap). PILOT data, not confirmatory. Cells with no correct answer or no "
           "reported cost carry the label instead of a dot; gateway models have no real cost, the price Claude "
           "Code reports for them is an estimate for an unknown model.")
    return Built(fig, cols, source, cap, ci={"method": "task-clustered percentile bootstrap, 95 %",
                                              "unit": "task, k repetitions kept together"},
                 notes=["wall time: runner-measured wall_time_s where present, else the result event's duration_s",
                        "log x axes"])
