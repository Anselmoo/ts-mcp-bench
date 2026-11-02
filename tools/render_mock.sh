#!/usr/bin/env bash
# Every figure and every report page of a run-set folder in one command. By default the demo run set (fake claude):
# tests/demo_runs.py builds small run sets with `tsbench run --dry-run` into OUT/runs (no key, no network, no cost).
# See docs/pipeline.md.
#
#   tools/render_mock.sh [--runs DIR] [--out DIR]          (default: the demo run set, --out mock-site)
#
# Writes OUT/figures/ (accuracy_by_model ... code_listing, PDF/SVG/PNG/TIFF + .source.csv + .json; a figure without
# data in the run sets is skipped) and OUT/pages/ (dashboard, comparison, gallery, literature, coverage, and all of
# them in report.html). With --runs the pages are made from a copy (OUT/runs): the report commands write derived files
# (scores.csv, per-run figures) next to the transcripts, and the source folder stays untouched.
set -euo pipefail
cd "$(dirname "$0")/.." || exit 1

RUNS="" OUT=mock-site
while [ $# -gt 0 ]; do
  case "$1" in
    --runs) RUNS="$2"; shift 2 ;;
    --out) OUT="$2"; shift 2 ;;
    -h|--help) sed -n 2,11p "$0"; exit 0 ;;
    *) echo "render_mock: unknown option $1" >&2; exit 2 ;;
  esac
done
TSBENCH="$PWD/.venv/bin/tsbench"
export SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-0}"  # same bytes on every machine
mkdir -p "$OUT/pages"
rm -rf "$OUT/runs" "$OUT/runs.plans" "$OUT/figures"
TITLE=()  # the demo run set is named as such; any other folder gets the default title (the models it holds)
if [ -z "$RUNS" ]; then
  echo "== demo run set (fake claude)"
  "$PWD/.venv/bin/python" tests/demo_runs.py "$OUT/runs"
  SRC="$OUT/runs"
  TITLE=(--title "Demo run set (fake claude)")
else
  SRC="$RUNS"
  cp -R "$SRC" "$OUT/runs"
fi
RUNS="$OUT/runs"

echo "== figures";    "$TSBENCH" figures all --runs "$SRC" --out "$OUT/figures"
echo "== dashboard";  "$TSBENCH" report dashboard --runs "$RUNS" --out "$OUT/pages/dashboard.html" ${TITLE[@]+"${TITLE[@]}"}
echo "== comparison"; "$TSBENCH" report comparison --runs "$RUNS" --out "$OUT/pages/comparison.html"
echo "== gallery";    "$TSBENCH" report gallery --runs "$RUNS" --out "$OUT/pages/gallery.html"
echo "== literature"; "$TSBENCH" report literature --runs "$RUNS" --out "$OUT/pages/literature.html"
echo "== coverage";   "$TSBENCH" report coverage --runs "$RUNS" --out "$OUT/pages/coverage.html"
echo "== full";       "$TSBENCH" report full --runs "$RUNS" --out "$OUT/pages/report.html" --no-figures ${TITLE[@]+"${TITLE[@]}"}
echo "done: $OUT/figures/ and $OUT/pages/"
