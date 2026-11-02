"""Shared plumbing of the figure pipeline: style set-up, export, source csv and provenance json."""
from __future__ import annotations

import csv
import datetime
import hashlib
import json
import os
import pathlib
import platform
import subprocess
from dataclasses import dataclass, field

from tsbench.core.intervals import RESAMPLES, SEED
from tsbench.figures import data

FIGURA = pathlib.Path(__file__).resolve().parents[1] / "_vendor" / "figura"
STATUS = "pilot"
OUTPUT_SUFFIXES = (".pdf", ".svg", ".tif", ".png")
VECTOR_SUFFIXES = (".pdf", ".svg")
SVG_HASHSALT = "benchmark-figures"
# keys of the provenance json that change from machine to machine or run to run; `--check` ignores them
VOLATILE_KEYS = ("generated_utc", "git", "versions.python")


def build_time() -> datetime.datetime:
    """SOURCE_DATE_EPOCH (reproducible builds), else 0: the date written into PDF and SVG metadata."""
    try:
        epoch = int(os.environ.get("SOURCE_DATE_EPOCH", "0"))
    except ValueError:
        epoch = 0
    return datetime.datetime.fromtimestamp(epoch, datetime.UTC)


@dataclass
class Context:
    sets: list
    theme: str = "neutral"
    ci: str = "wilson"            # wilson | bootstrap (accuracy_by_model, accuracy_by_class)
    footer: bool = True
    rows: list = field(default_factory=list)
    n_repeats: int = 0

    def __post_init__(self):
        self.rows, self.n_repeats = data.pooled_rows(self.sets)


@dataclass
class Built:
    fig: object
    columns: list
    source: list                  # list of dicts keyed by `columns`
    caption: str
    notes: list = field(default_factory=list)
    ci: dict = field(default_factory=dict)


def setup(theme: str = "neutral"):
    """Agg backend, Figura style (7 / 6 pt, minor ticks in, no caps), colour theme, Arial-compatible font stack."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from tsbench._vendor.figura import jfs

    plt.style.use(str(FIGURA / "jfs.mplstyle"))
    jfs.use_theme(theme)
    jfs.use_font("sans-serif")  # mathtext follows the first installed face of the stack (no DejaVu fallback)
    plt.rcParams["svg.hashsalt"] = SVG_HASHSALT
    return plt, jfs


def condition_style(jfs) -> dict:
    """Colour and marker per condition (the marker repeats the colour, so a greyscale copy stays readable)."""
    return {"A": (jfs.COLORS["series-1"], "o"), "B": (jfs.COLORS["series-2"], "s"), "C": (jfs.COLORS["series-3"], "^")}


def condition_key(fig, jfs, x0: float = 0.02, y: float = None):
    """Direct labels of the three conditions as coloured bold text in one line at the top of the figure."""
    sty = condition_style(jfs)
    w_pt = fig.get_figwidth() * 72
    h_pt = fig.get_figheight() * 72
    y = 1 - 5.0 / h_pt if y is None else y
    x = x0
    for c in data.CONDITIONS:
        label = f"{c}  {data.COND_NAME[c]}"
        t = fig.text(x, y, label, color=sty[c][0], fontsize=6, va="center", ha="left", fontweight="bold")
        t.set_gid(f"key:{c}")
        x += (len(label) * 3.6 + 14) / w_pt
    return fig


def reserve(fig, footer: bool, top_key: bool = True):
    """Leave room for the footer (bottom) and the condition key (top) in the constrained layout."""
    h_pt = fig.get_figheight() * 72
    bottom = 9.0 / h_pt if footer else 0.0
    top = 1 - (10.0 / h_pt if top_key else 0.0)
    fig.get_layout_engine().set(rect=(0, bottom, 1, top - bottom))


def footer_text(fig, text: str):
    h_pt = fig.get_figheight() * 72
    t = fig.text(0.005, 2.0 / h_pt, text, fontsize=5, color="#4d4d4d", ha="left", va="bottom")
    t.set_gid("footer")
    return t


def format_float(v) -> str:
    """One fixed float format for the csv files."""
    if v is None:
        return ""
    if isinstance(v, bool):
        return "True" if v else "False"
    if isinstance(v, float):
        if v != v:
            return ""
        return format(v, ".10g")
    return str(v)


def write_source(path: pathlib.Path, columns: list, rows: list) -> str:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(columns)
        for r in rows:
            w.writerow([format_float(r.get(c)) for c in columns])
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_info() -> dict:
    def run(*args):
        return subprocess.run(["git", *args], cwd=data.REPO_ROOT, capture_output=True, encoding="utf-8", timeout=30)
    try:
        commit = run("rev-parse", "HEAD").stdout.strip() or None
        dirty = bool(run("status", "--porcelain", "--untracked-files=no").stdout.strip())
    except (OSError, subprocess.SubprocessError):
        return {"commit": None, "dirty": None}
    return {"commit": commit, "dirty": dirty}


def task_hashes() -> dict:
    """sha256 of the task file as pinned in src/tsbench/data/tasks/tasks.sha256 (pilot split and whole file; the hash of
    the sealed split is not copied)."""
    from tsbench.tasks import hash_path
    entries = {}
    for line in hash_path().read_text(encoding="utf-8").splitlines():
        digest, _, name = line.partition("  ")
        if name in ("tasks.jsonl", "pilot"):
            entries[name] = digest
    return entries


def provenance(name: str, ctx: Context, built: Built, files: list, source_sha: str, now=None) -> dict:
    import matplotlib
    import numpy
    if now is None:
        now = build_time() if "SOURCE_DATE_EPOCH" in os.environ else datetime.datetime.now(datetime.UTC)
    sets = [{
        "name": s.name, "title": s.title, "source": s.source, "scores_csv_sha256": s.scores_sha256,
        "n_rows": len(s.rows), "n_evaluable": sum(r["evaluable"] for r in s.rows), "live_run": s.live,
        "dropped_non_pilot_rows": s.dropped_non_pilot, "skipped_incomplete_transcripts": s.skipped_incomplete,
        "notes": s.notes,
    } for s in ctx.sets]
    doc = {
        "figure": name,
        "status": STATUS,
        "caption": built.caption,
        "footer": footer_line(ctx),
        "git": git_info(),
        "run_sets": sets,
        "task_set": task_hashes(),
        "pooling": {"n_runs_used": len(ctx.rows), "repeated_keys_dropped": ctx.n_repeats,
                    "not_evaluable_excluded": sum(not r["evaluable"] for s in ctx.sets for r in s.rows)},
        "ci": built.ci,
        "notes": built.notes,
        "theme": ctx.theme,
        "fonts": "Arial-compatible sans-serif stack; PDF fonttype 42",
        "versions": {"matplotlib": matplotlib.__version__, "numpy": numpy.__version__,
                     "python": platform.python_version()},
        "outputs": files,
        "source_csv_sha256": source_sha,
        "generated_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if "bootstrap" in built.ci.get("method", ""):  # only a figure with a bootstrap interval declares its settings
        doc["bootstrap"] = {"seed": SEED, "resamples": RESAMPLES, "unit": "task (k repetitions kept together)"}
    return doc


def footer_line(ctx: Context) -> str:
    return (f"Pilot data, not confirmatory: {len(ctx.rows)} runs from {len(ctx.sets)} run sets "
            f"(HTTP 429 / API errors excluded).")


def save(fig, stem: str, raster: bool = True) -> list[str]:
    """PDF and SVG with pinned dates (fonts embedded / as text), and unless `raster` is False the 600 dpi LZW TIFF and
    the 300 dpi PNG; never bbox_inches="tight" (the figure keeps its set width). Returns the suffixes written."""
    when = build_time()
    fig.savefig(stem + ".pdf", metadata={"CreationDate": when, "ModDate": when})
    fig.savefig(stem + ".svg", metadata={"Date": when.strftime("%Y-%m-%dT%H:%M:%SZ")})
    if not raster:
        return list(VECTOR_SUFFIXES)
    fig.savefig(stem + ".tif", dpi=600, pil_kwargs={"compression": "tiff_lzw"})
    fig.savefig(stem + ".png", dpi=300, metadata={"Software": None})
    return list(OUTPUT_SUFFIXES)


def export(name: str, built: Built, ctx: Context, out: pathlib.Path, raster: bool = True) -> dict:
    """Write pdf, svg, tif (600 dpi, LZW), png (300 dpi), `<name>.source.csv` and `<name>.json`; return the provenance.
    The provenance lists every format of a full build (`raster=False` skips writing the two raster files only)."""
    plt, _jfs = setup(ctx.theme)
    out.mkdir(parents=True, exist_ok=True)
    stem = str(out / name)
    save(built.fig, stem, raster)
    plt.close(built.fig)
    source_sha = write_source(out / f"{name}.source.csv", built.columns, built.source)
    prov = provenance(name, ctx, built, [name + s for s in OUTPUT_SUFFIXES] + [f"{name}.source.csv"], source_sha)
    (out / f"{name}.json").write_text(json.dumps(prov, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
                                      encoding="utf-8")
    return prov


# ------------------------------------------------------------------------------------------------ golden check
def _drop(d: dict, dotted: str) -> None:
    head, _, rest = dotted.partition(".")
    if rest:
        if isinstance(d.get(head), dict):
            _drop(d[head], rest)
    else:
        d.pop(head, None)


def stable_provenance(path: pathlib.Path) -> dict:
    doc = json.loads(path.read_text(encoding="utf-8"))
    for key in VOLATILE_KEYS:
        _drop(doc, key)
    return doc


def check(names, out: pathlib.Path, golden: pathlib.Path) -> list[str]:
    """Differences of the built figures `names` in `out` against `golden`: `<name>.source.csv` byte for byte and
    `<name>.json` without VOLATILE_KEYS. Empty list: identical."""
    diffs = []
    for name in names:
        a, b = out / f"{name}.source.csv", golden / f"{name}.source.csv"
        if not b.is_file():
            diffs.append(f"{name}.source.csv: no golden file")
        elif not a.is_file() or a.read_bytes() != b.read_bytes():
            diffs.append(f"{name}.source.csv: differs")
        a, b = out / f"{name}.json", golden / f"{name}.json"
        if not b.is_file():
            diffs.append(f"{name}.json: no golden file")
            continue
        pa, pb = stable_provenance(a), stable_provenance(b)
        if pa != pb:
            keys = sorted(k for k in set(pa) | set(pb) if pa.get(k) != pb.get(k))
            diffs.append(f"{name}.json: differs in {', '.join(keys)}")
    return diffs
