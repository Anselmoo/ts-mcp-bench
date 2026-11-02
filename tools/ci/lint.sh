#!/usr/bin/env bash
# Report-only lint: ruff (via uvx), bash -n and shellcheck on the shell scripts.
# Exit status: 0 clean, 1 findings (the CI lint job is report-only). A missing tool is skipped, not a failure.
set -uo pipefail
# shellcheck source=tools/ci/common.sh
. "$(dirname "$0")/common.sh"
ci_guard_keys || exit 1
rc=0

ci_log "ruff check"
if command -v uvx >/dev/null 2>&1; then
  uvx ruff check . || rc=1
elif command -v ruff >/dev/null 2>&1; then
  ruff check . || rc=1
else
  echo "ci: ruff/uvx not available; skipped"
fi

ci_log "bash -n"
shopt -s nullglob
scripts=(tools/*.sh tools/ci/*.sh)
for f in "${scripts[@]}"; do
  bash -n "$f" || { echo "syntax error: $f"; rc=1; }
done
echo "checked ${#scripts[@]} scripts"

ci_log "shellcheck"
if command -v shellcheck >/dev/null 2>&1; then
  shellcheck -x -P SCRIPTDIR "${scripts[@]}" || rc=1
else
  echo "ci: shellcheck not available; skipped"
fi
exit "$rc"
