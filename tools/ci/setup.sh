#!/usr/bin/env bash
# Create .venv at the repo root and install the package with the test extra.
# Needs `uv` on PATH (the astral-sh/uv image has it; elsewhere: pip install uv).
set -euo pipefail
# shellcheck source=tools/ci/common.sh
. "$(dirname "$0")/common.sh"
ci_guard_keys
command -v uv >/dev/null 2>&1 || ci_die "uv not found (pip install uv)"
ci_log "uv venv + install"
uv venv --allow-existing .venv
# pytest-cov is optional: report-only, so a failed install must not break the job
uv pip install --python .venv/bin/python -e '.[test]'
uv pip install --python .venv/bin/python pytest-cov pyyaml >/dev/null 2>&1 \
  || echo "ci: pytest-cov/pyyaml not installable; coverage will be skipped"
.venv/bin/python - <<'PY'
import importlib.metadata as m
print("python ok; tanabesugano", m.version("tanabesugano"))
PY
test -x .venv/bin/tanabesugano-mcp || ci_die ".venv/bin/tanabesugano-mcp missing after install"
