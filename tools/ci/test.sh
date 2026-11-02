#!/usr/bin/env bash
# Unit tests for the benchmark and the CI helpers. JUnit XML to $TSCI_REPORT_DIR (default build/ci/reports); coverage is report-only.
set -euo pipefail
# shellcheck source=tools/ci/common.sh
. "$(dirname "$0")/common.sh"
ci_guard_keys
ci_need_venv
REPORTS="${TSCI_REPORT_DIR:-$TSCI_ROOT/build/ci/reports}"
mkdir -p "$REPORTS"

cov=()
if "$TSCI_PY" -c 'import pytest_cov' >/dev/null 2>&1; then
  cov=(--cov=tsbench --cov-report=term --cov-report="xml:$REPORTS/coverage.xml")
else
  echo "ci: pytest-cov not installed; running without coverage"
fi

ci_log "pytest tests"
# the browser job (browser.sh) runs the Chrome test, with Chrome required
"$TSCI_PY" -m pytest tests -q -p no:cacheprovider --ignore=tests/report/test_motion.py \
  "--junitxml=$REPORTS/junit-tsbench.xml" ${cov[@]+"${cov[@]}"}
