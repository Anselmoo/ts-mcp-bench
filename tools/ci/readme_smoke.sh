#!/usr/bin/env bash
# Run the README blocks marked `# ci: dry` in a temp copy of the repo; unmarked blocks are reported as skipped.
set -euo pipefail
# shellcheck source=tools/ci/common.sh
. "$(dirname "$0")/common.sh"
ci_guard_keys
ci_need_venv
exec "$TSCI_PY" tools/ci/readme_smoke.py "$@"
