"""Figure pipeline for the pilot data.

    tsbench figures <name|all> --runs <dir> [--runs <dir> ...] --out <dir> [--theme neutral] [--check <golden dir>]

Names: accuracy_by_model, accuracy_by_class, literature_parity, efficiency, code_listing. Per figure `<name>`: `.pdf`,
`.svg`, `.tif` (600 dpi, LZW), `.png` (300 dpi), `<name>.source.csv` (the numbers plotted) and `<name>.json`
(provenance). The export is deterministic: SOURCE_DATE_EPOCH (default 0) pins the PDF and SVG dates, the SVG hash salt
is fixed, the source csv carries no timestamp. Drawn with the vendored Figura helpers
(`src/tsbench/_vendor/figura/jfs.py`, theme `neutral`). Only the pilot split is ever loaded
(`tsbench.tasks.load("pilot")`); rows of any other task id are dropped.
"""
from __future__ import annotations

__all__ = ["FIGURE_NAMES"]

FIGURE_NAMES = ("accuracy_by_model", "accuracy_by_class", "literature_parity", "efficiency", "code_listing")
