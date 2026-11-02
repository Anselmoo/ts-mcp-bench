#!/usr/bin/env bash
# Fail if any model credential is present in the environment. Run first in every job.
set -euo pipefail
# shellcheck source=tools/ci/common.sh
. "$(dirname "$0")/common.sh"
ci_guard_keys
ci_log "guard: no model credentials in the environment"
