#!/usr/bin/env bash
# The motion contract and the drill-down of the report pages in headless Chrome (tests/report/test_motion.py).
# Chrome: $TSBENCH_CHROME, else the first of google-chrome, chromium (and their other names) on PATH (the GitHub runner
# has google-chrome); without one, Debian's chromium is installed when apt-get runs as root (the GitLab image).
# TSBENCH_REQUIRE_CHROME=1 turns the test's skip without Chrome into a failure. JUnit XML to $TSCI_REPORT_DIR.
set -euo pipefail
# shellcheck source=tools/ci/common.sh
. "$(dirname "$0")/common.sh"
ci_guard_keys
ci_need_venv
REPORTS="${TSCI_REPORT_DIR:-$TSCI_ROOT/build/ci/reports}"
mkdir -p "$REPORTS"

chrome=""
for name in "${TSBENCH_CHROME:-}" google-chrome google-chrome-stable chromium chromium-browser chrome; do
  if [ -n "$name" ] && command -v "$name" >/dev/null 2>&1; then chrome="$(command -v "$name")"; break; fi
done
if [ -z "$chrome" ]; then
  if command -v apt-get >/dev/null 2>&1 && [ "$(id -u)" = 0 ]; then
    ci_log "apt-get install chromium"
    apt-get update -qq && apt-get install -y -qq --no-install-recommends chromium >/dev/null
    chrome="$(command -v chromium)" || ci_die "chromium missing after apt-get install"
  else
    ci_die "no Chrome or Chromium on PATH; set TSBENCH_CHROME to its executable"
  fi
fi
ci_log "chrome: $chrome ($("$chrome" --version 2>/dev/null || echo "version unknown"))"
export TSBENCH_CHROME="$chrome" TSBENCH_REQUIRE_CHROME=1

ci_log "pytest tests/report/test_motion.py"
"$TSCI_PY" -m pytest tests/report/test_motion.py -q -p no:cacheprovider "--junitxml=$REPORTS/junit-browser.xml"
