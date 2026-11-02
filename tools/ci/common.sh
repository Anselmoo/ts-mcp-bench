# shellcheck shell=bash
# Sourced by the other tools/ci scripts. Plain bash 3.2+ (macOS) and Linux; no GitLab-specific variables.
# Not executable on its own.

TSCI_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
export TSCI_ROOT
cd "$TSCI_ROOT" || exit 1

# the runner looks for <repo>/.venv/bin/tanabesugano-mcp, so the venv must be .venv at the repo root
TSCI_PY="$TSCI_ROOT/.venv/bin/python"
TSBENCH="$TSCI_ROOT/.venv/bin/tsbench"  # the tsbench command of this checkout
export TSBENCH
export PYTHONDONTWRITEBYTECODE=1

# every variable that could make a real model call (or a bill); the same names as conditions.sandbox.KEY_VARS (a test
# compares the two lists)
TSCI_KEY_VARS="ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN TSMCP_ANTHROPIC_API_KEY GWDG_API_KEY GWDG_AI_API_KEY LITELLM_MASTER_KEY"

ci_log() { printf '== %s\n' "$*"; }
ci_die() { printf 'ci: %s\n' "$*" >&2; exit 1; }

ci_need_venv() {
  [ -x "$TSCI_PY" ] || ci_die "no $TSCI_PY; run tools/ci/setup.sh first"
}

# Fails when any key variable is set at all (even empty): CI must not carry model credentials.
ci_guard_keys() {
  local v bad=""
  for v in $TSCI_KEY_VARS; do
    # ${!v+x} is bash indirect expansion: non-empty only when the variable is set
    if [ -n "${!v+x}" ]; then bad="$bad $v"; fi
  done
  if [ -n "$bad" ]; then
    printf 'ci: refusing to run: these variables are set in the CI environment:%s\n' "$bad" >&2
    printf 'ci: CI must never hold model credentials (no real model calls, no bill). Remove them from the CI/CD variables.\n' >&2
    return 1
  fi
}
