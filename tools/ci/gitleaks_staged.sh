#!/usr/bin/env bash
# Secret scan of the staged changes with gitleaks, for the pre-commit hook (>= 8.19: `gitleaks git --staged`;
# older: `gitleaks protect --staged`). gitleaks is a Go binary and not in uv.lock: without it the scan is skipped.
set -uo pipefail
# shellcheck source=tools/ci/common.sh
. "$(dirname "$0")/common.sh"
ci_guard_keys || exit 1
if ! command -v gitleaks >/dev/null 2>&1; then
  echo "gitleaks not on PATH; staged secret scan skipped (CI runs tools/ci/gitleaks.sh)"
  exit 0
fi
if gitleaks git --help >/dev/null 2>&1; then
  gitleaks git --pre-commit --staged --no-banner --redact --verbose .
else
  gitleaks protect --staged --no-banner --redact --verbose --source .
fi
