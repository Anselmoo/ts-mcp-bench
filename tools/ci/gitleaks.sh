#!/usr/bin/env bash
# Secret scan of the git history with gitleaks (>= 8.19: `gitleaks git`; older: `gitleaks detect`).
# Findings are redacted in the log. Needs the full history (GIT_DEPTH=0 on GitLab, fetch-depth: 0 on GitHub).
set -uo pipefail
# shellcheck source=tools/ci/common.sh
. "$(dirname "$0")/common.sh"
ci_guard_keys || exit 1
command -v gitleaks >/dev/null 2>&1 || ci_die "gitleaks not found (use the zricethezav/gitleaks image)"
if gitleaks git --help >/dev/null 2>&1; then
  gitleaks git --no-banner --redact --verbose .
else
  gitleaks detect --no-banner --redact --verbose --source .
fi
