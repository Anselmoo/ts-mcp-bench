"""code_listing: one real MCP call sequence (condition C) and one real Bash script (condition B), taken from existing
pilot transcripts and set as a code listing (soft panel, muted line numbers, mono stack).

Selection is deterministic: transcripts sorted by path, first correct run with the wanted shape. Nothing is executed and
nothing is written next to the transcripts (the tool_use blocks are read with the helpers of
tsbench.score.artifacts)."""
from __future__ import annotations

import json
import re

from matplotlib.patches import FancyBboxPatch

from tsbench.figures import data
from tsbench.figures.render import Built, Context, footer_text, reserve, setup

MAX_LINES = 15
MAX_CHARS = 60
_HOME = re.compile(r"/(?:Users|home)/[^/\s\"']+")


def _clean(text: str) -> str:
    text = _HOME.sub("~", text.replace("\t", "    "))
    return text.encode("latin-1", "replace").decode("latin-1")


def _clip(line: str) -> str:
    line = _clean(line.rstrip())
    return line if len(line) <= MAX_CHARS else line[: MAX_CHARS - 3] + "..."


def _compact(v) -> str:
    return json.dumps(v, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def mcp_lines(uses) -> list[str]:
    """One line per MCP call: `tool(arg=value, ...)`, at most MAX_LINES."""
    out = []
    for u in uses:
        name = str(u.get("name", ""))
        if not name.startswith("mcp__"):
            continue
        inp = u.get("input") if isinstance(u.get("input"), dict) else {}
        args = ", ".join(f"{k}={_compact(v)}" for k, v in sorted(inp.items()))
        out.append(_clip(f"{name.split('__')[-1]}({args})"))
        if len(out) == MAX_LINES:
            break
    return out


def bash_script(uses) -> list[str] | None:
    """Lines of the first Python heredoc of the run (None if there is none), cut at MAX_LINES."""
    from tsbench.score.artifacts import split_heredocs
    for u in uses:
        if u.get("name") != "Bash":
            continue
        cmd = str((u.get("input") or {}).get("command") or "")
        heredocs, _skel = split_heredocs(cmd)
        for h in heredocs:
            if h["python"] or str(h["name"] or "").endswith(".py"):
                lines = h["body"].rstrip("\n").split("\n")
                while lines and not lines[0].strip():
                    lines.pop(0)
                if len(lines) < 4:
                    continue
                if len(lines) > MAX_LINES:
                    lines = lines[: MAX_LINES - 1] + ["# ... (cut)"]
                return [_clip(ln) for ln in lines]
    return None


def _correct_transcripts(sets, cond: str):
    """(path, run set, row) of every correct, evaluable transcript of one condition, sorted by path."""
    from tsbench.score.score import find_transcripts
    out = []
    for s in sets:
        ok = {(r["model"], r["condition"], r["effort"], r["task_id"], r["k_index"]): r
              for r in s.rows if r["correct"] and r["evaluable"] and r["condition"] == cond}
        if not ok:
            continue
        for path, model, c, effort, task, k in find_transcripts(s.path):
            row = ok.get((data.model_norm(model), c, effort, task, k))
            if row:
                out.append((path, s, row))
    out.sort(key=lambda t: t[0].as_posix())
    return out


def _pick(sets, cond: str, extract, ok=None):
    """First (lines, path, set, row) of a correct transcript of `cond` with non-empty extracted lines that pass `ok`."""
    from tsbench.score.artifacts import scan_tool_calls as _scan
    for path, s, row in _correct_transcripts(sets, cond):
        try:
            uses, _res = _scan(path)
        except OSError:
            continue
        lines = extract(uses)
        if lines and (ok is None or ok(lines)):
            return lines, path, s, row
    return None


def code_listing(ctx: Context) -> Built:
    plt, jfs = setup(ctx.theme)
    from tsbench.figures.render import footer_line
    mcp = _pick(ctx.sets, "C", mcp_lines, lambda ls: len(ls) >= 2)
    bash = _pick(ctx.sets, "B", bash_script)
    if mcp is None and bash is None:
        raise data.NoDataError("code_listing: no correct transcript with MCP calls (C) or a Python heredoc (B)")
    panels = [("C", "MCP call sequence (TS-MCP)", mcp), ("B", "Bash script (Python stack)", bash)]
    n = MAX_LINES
    h = 12 + n * 6 * 1.25 * 25.4 / 72 + 6
    fig, axs = jfs.figure("double", h, ncols=2)
    source = []
    for ax, (cond, title, pick) in zip(axs, panels, strict=False):
        ax.set_axis_off()
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.add_patch(FancyBboxPatch((0, 0), 1, 0.9, boxstyle="round,pad=0,rounding_size=0.02", transform=ax.transAxes,
                                    fc=jfs.COLORS["fill-soft"], ec=jfs.COLORS["rule"], lw=0.5, zorder=0))
        if pick is None:
            ax.text(0.5, 0.45, "no example found", ha="center", va="center", fontsize=6, color=jfs.COLORS["ink-muted"])
            ax.text(0.0, 0.96, title, fontsize=7, fontweight="bold", va="bottom")
            continue
        lines, path, s, row = pick
        ax.text(0.0, 0.96, f"{title}: {data.model_label(row['model'])}, {data.class_label(row['class'])}", fontsize=6.5,
                fontweight="bold", va="bottom", ha="left")
        step = 0.9 / (n + 1)
        for i, ln in enumerate(lines):
            y = 0.9 - step * (i + 1)
            ax.text(0.02, y, f"{i + 1:>2}", fontsize=5.5, family="monospace", color=jfs.COLORS["ink-muted"],
                    va="center")
            ax.text(0.085, y, ln, fontsize=6, family="monospace", va="center", color=jfs.COLORS["ink"])
            source.append({"panel": cond, "line": i + 1, "text": ln, "run_set": s.name,
                           "transcript": path.relative_to(s.path).as_posix(), "model": row["model"],
                           "task_id": row["task_id"], "k_index": row["k_index"]})
    jfs.panel_labels(list(axs), y=0.96)
    reserve(fig, ctx.footer, top_key=False)
    if ctx.footer:
        footer_text(fig, footer_line(ctx))
    cols = ["panel", "line", "text", "run_set", "transcript", "model", "task_id", "k_index"]
    cap = ("Example code of correct pilot runs, unedited except for clipping long lines and replacing home paths: "
           "(a) the tool calls of a TS-MCP (C) run, (b) the first Python script of a Bash (B) run. "
           "PILOT data, not confirmatory.")
    return Built(fig, cols, source, cap,
                 notes=[f"at most {MAX_LINES} lines per panel, lines clipped at {MAX_CHARS} characters",
                        "first correct run by path order"])
