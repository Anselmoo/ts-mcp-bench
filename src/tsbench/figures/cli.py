"""Command line: tsbench figures <name|all> --runs <dir> [--runs <dir> ...] --out <dir> [--check <golden dir>]"""
from __future__ import annotations

import argparse
import pathlib
import sys
import tempfile

from tsbench.figures import FIGURE_NAMES, data


def builders() -> dict:
    """Figure name -> builder."""
    from tsbench.figures import listing, plots
    return {"accuracy_by_model": plots.accuracy_by_model, "accuracy_by_class": plots.accuracy_by_class,
            "literature_parity": plots.literature_parity, "efficiency": plots.efficiency,
            "code_listing": listing.code_listing}


def build_all(names, ctx, out, raster: bool = True) -> dict:
    """Build and export `names`; returns {name: provenance}. A figure without data raises NoDataError."""
    from tsbench.figures.render import export
    table = builders()
    made = {}
    for name in names:
        made[name] = export(name, table[name](ctx), ctx, pathlib.Path(out), raster)
    return made


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="tsbench figures", description=__doc__.splitlines()[0])
    ap.add_argument("figure", choices=[*FIGURE_NAMES, "all"])
    ap.add_argument("--runs", action="append", required=True, metavar="DIR",
                    help="a run set or a folder holding run sets (searched for MANIFEST.json); repeatable")
    ap.add_argument("--out", default=None, help="output directory (with --check only: a temporary one if omitted)")
    ap.add_argument("--check", default=None, metavar="GOLDEN",
                    help="compare <name>.source.csv byte for byte and <name>.json without its volatile keys with the "
                         "files in GOLDEN; exit 1 on a difference")
    ap.add_argument("--theme", default="neutral", help="colour theme of the vendored Figura helpers")
    ap.add_argument("--ci", choices=("wilson", "bootstrap"), default="wilson",
                    help="interval of accuracy_by_model / accuracy_by_class: Wilson over runs, or a task-clustered "
                         "bootstrap")
    ap.add_argument("--rescore", action="store_true",
                    help="score the transcripts in memory instead of reading scores.csv")
    ap.add_argument("--no-footer", action="store_true", help="omit the 'pilot data' footer line inside the figure")
    ap.add_argument("--no-raster", action="store_true", help="write PDF and SVG only (no TIFF / PNG)")
    ap.add_argument("--i-have-preregistered", dest="preregistered", metavar="DOI", default=None,
                    help="needed to read a confirmatory run set (only its pilot task ids are drawn)")
    args = ap.parse_args(argv)
    if args.out is None and args.check is None:
        ap.error("--out is required (it may be omitted with --check)")
    from tsbench.figures.render import Context, check

    try:
        found = data.find_run_sets(args.runs, args.preregistered)
        sets = data.load_all(found, args.rescore)
    except ValueError as exc:
        print(f"refusing: {exc}", file=sys.stderr)
        return 2
    ctx = Context(sets=sets, theme=args.theme, ci=args.ci, footer=not args.no_footer)
    names = list(FIGURE_NAMES) if args.figure == "all" else [args.figure]
    with tempfile.TemporaryDirectory(prefix="tsbench-figures-") as tmp:
        out = pathlib.Path(args.out or tmp)
        status = 0
        for name in names:
            try:
                build_all([name], ctx, out, raster=not args.no_raster)
                print(f"{name}: written to {out}")
            except data.NoDataError as exc:
                print(f"{name}: skipped ({exc})", file=sys.stderr)
                status = status or (1 if args.figure != "all" else 0)
        if args.check:
            diffs = check(names, out, pathlib.Path(args.check))
            for d in diffs:
                print(f"check: {d}", file=sys.stderr)
            bad = {d.split(".")[0] for d in diffs}
            print(f"check: {len(names) - len(bad)} of {len(names)} figures match {args.check}")
            status = 1 if diffs else status
    return status
