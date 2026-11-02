#!/usr/bin/env bash
# Release gate (tsbench release gate): no private material (pilot/, seed/, analysis/, .claude/, .env, ...) tracked by git
# or in the release archive.
set -euo pipefail
# shellcheck source=tools/ci/common.sh
. "$(dirname "$0")/common.sh"
ci_guard_keys
if [ -x "$TSCI_PY" ]; then exec "$TSCI_PY" -m tsbench release gate; fi
exec python3 -m tsbench release gate
