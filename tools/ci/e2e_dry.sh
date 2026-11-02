#!/usr/bin/env bash
# The whole benchmark pipeline against the fake claude (runner --dry-run). Zero cost, no network, no keys.
# Output directory: $TSCI_E2E_DIR (default build/ci/e2e), recreated on every run. Must lie under build/ci/.
set -euo pipefail
# shellcheck source=tools/ci/common.sh
. "$(dirname "$0")/common.sh"
ci_guard_keys
ci_need_venv

OUT="${TSCI_E2E_DIR:-build/ci/e2e}"
case "$OUT" in build/ci/*|"$TSCI_ROOT"/build/ci/*) ;; *) ci_die "TSCI_E2E_DIR must be under build/ci/ (got $OUT)" ;; esac
case "$OUT" in *..*) ci_die "TSCI_E2E_DIR must not contain .." ;; esac
rm -rf "$OUT"
mkdir -p "$OUT/plan" "$OUT/runs" "$OUT/tasks"

MODELS="claude-haiku-5-5,claude-sonnet-5-5"
PY="$TSCI_PY"

ci_log "1/8 regenerate tasks and compare with the committed set (canonical comparison)"
"$TSBENCH" tasks generate --out "$OUT/tasks" --check >"$OUT/tasks/generate.log" \
  || ci_die "the regenerated task set differs from tsbench/tasks/tasks.jsonl beyond diagram labels and the sign of zero"

ci_log "2/8 build the plan (pilot, 2 models, A,B,C, 3 tasks, k=1)"
"$TSBENCH" plan build --split pilot --models "$MODELS" --conditions A,B,C --effort medium \
  --k 1 --budget-usd 10 --limit 3 --out-plan "$OUT/plan/plan.jsonl"
"$TSBENCH" plan validate "$OUT/plan/plan.jsonl"

ci_log "3/8 run the plan with the fake claude"
"$TSBENCH" run --plan "$OUT/plan/plan.jsonl" --dry-run --out "$OUT/runs"

ci_log "4/8 score"
"$TSBENCH" score --runs "$OUT/runs"

ci_log "5/8 score report"
"$TSBENCH" metrics --runs "$OUT/runs"

ci_log "6/8 render per-run views"
"$TSBENCH" report views --runs "$OUT/runs"

ci_log "7/8 dashboard"
"$TSBENCH" report dashboard --runs "$OUT/runs" --out "$OUT/runs/report.html"

ci_log "8/8 hypotheses (pilot: incomplete cells allowed)"
"$TSBENCH" stats hypotheses --rates "$OUT/runs/rates.csv" --allow-incomplete --out "$OUT/runs/hypotheses.json" >"$OUT/runs/hypotheses.log"

ci_log "assert outputs"
"$PY" tools/ci/check_e2e.py "$OUT"
