#!/usr/bin/env bash
# The confirmatory guard must refuse without a preregistration DOI: runner --split confirmatory exits 2 and writes nothing.
set -uo pipefail
# shellcheck source=tools/ci/common.sh
. "$(dirname "$0")/common.sh"
ci_guard_keys || exit 1
ci_need_venv
OUT="$(mktemp -d "${TMPDIR:-/tmp}/ci-confirmatory.XXXXXX")"
trap 'rm -rf "$OUT"' EXIT
"$TSBENCH" run --split confirmatory --models claude-haiku-5-5 --conditions A \
  --effort medium --k 1 --budget-usd 1 --limit 1 --dry-run --out "$OUT/runs" >"$OUT/stdout" 2>"$OUT/stderr"
rc=$?
if [ "$rc" -ne 2 ]; then
  echo "ci: expected exit 2 from the confirmatory guard, got $rc"; cat "$OUT/stdout" "$OUT/stderr"; exit 1
fi
if [ -e "$OUT/runs/MANIFEST.json" ]; then
  echo "ci: the guard refused but a MANIFEST was written"; exit 1
fi
ci_log "confirmatory guard refused with exit 2: $(tail -n 1 "$OUT/stderr")"
