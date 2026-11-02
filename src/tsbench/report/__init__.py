"""The report pages of the benchmark: static, self-contained HTML files built from run-set folders.

    tsbench report views       one page per run and an index per run set           (tsbench.report.views)
    tsbench report gallery     every run as a card: figures, images, code, reproduce block   (.gallery)
    tsbench report comparison  conditions A, B, C compared across run sets          (.comparison)
    tsbench report dashboard   one page over several run sets: verdict, charts, runs (.dashboard)
    tsbench report literature  fit results against the published literature values  (.literature)
    tsbench report coverage    evaluable runs per pilot task x model x condition     (.coverage)
    tsbench explain            one run explained in plain text                       (.explain)

Every page command takes `--runs DIR` (repeatable; a run set or a folder holding run sets, see
tsbench.score.run_sets) and `--out FILE`. Shared page parts live in `page`, the per-run figures in `run_figures`, the
reproduce block of a run in `reproduce`. Only pilot tasks are ever shown.
"""
from __future__ import annotations

from tsbench.report.page import escape_html, href
from tsbench.report.views import harvested_images, images_html, render_dir, run_split

__all__ = ["escape_html", "harvested_images", "href", "images_html", "render_dir", "run_split"]
