#!/usr/bin/env bash
# Run set: claude-haiku-5-5, claude-sonnet-5-5, claude-opus-5-5 | conditions C,B,A | effort medium | k=3 | confirmatory (55 tasks)
# Written by `tsbench run` (tsbench 0.1.0, commit e7f956056098acc0f60065eaa88655b586e93a42) at 2026-11-03T06:56:55+00:00.
# plan_id cfd9c463c00a27185bebf057746bda55b5251be8b5764687886f1e11a3a29e3c
#
# Keys: this file holds no key or token, only variable NAMES. They come from your shell, e.g. from the key file:
# `set -a; . "${TSBENCH_KEY_FILE:-$HOME/.config/tsbench/env}"; set +a` (TSMCP_ANTHROPIC_API_KEY: Anthropic API,
# GWDG_API_KEY: gateway). A dry run (--dry-run, the fake claude) needs no key.
#
#   bash inputs/commands.sh [TARGET]   run the whole run set again into TARGET (default: <run set>-rerun)
#   continuing THIS run set instead: see README.md (`tsbench run ... --resume`)
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="${1:-$(dirname "$HERE")-rerun}"
TSBENCH="${TSBENCH:-tsbench}"
# the invocation (host paths as placeholders): tsbench run --plan <HOME>/tsbench-confirmatory-plans/plan-1-claude.jsonl --out pilot/confirmatory-runs/plan-1-claude --i-have-preregistered 10.5281/zenodo.23889782

# environment (names only)
: "${TSMCP_ANTHROPIC_API_KEY:-${ANTHROPIC_API_KEY:?set TSMCP_ANTHROPIC_API_KEY (see ${TSBENCH_KEY_FILE:-$HOME/.config/tsbench/env})}}"
unset ANTHROPIC_BASE_URL ANTHROPIC_AUTH_TOKEN

# 1. the plan, rebuilt from its header's spec (the run below uses the stored plan.sealed.json anyway)
"$TSBENCH" plan build --split confirmatory --models claude-haiku-5-5,claude-sonnet-5-5,claude-opus-5-5 --conditions C,B,A --effort medium --k 3 --budget-usd 125.0 --i-have-preregistered 10.5281/zenodo.23889782 --out-plan "$OUT/inputs/rebuilt/plan.jsonl"
grep -q '"plan_id": "cfd9c463c00a27185bebf057746bda55b5251be8b5764687886f1e11a3a29e3c"' "$OUT/inputs/rebuilt/plan.sealed.json" || echo "WARNING: the rebuilt plan has another plan_id (task set or code changed); the run uses the stored plan" >&2

# 2. the run
"$TSBENCH" run --plan "${TSBENCH_CLEAR_PLAN:?path of the clear plan with plan_id cfd9c463c00a27185bebf057746bda55b5251be8b5764687886f1e11a3a29e3c (kept outside the repo)}" --out "$OUT" --i-have-preregistered 10.5281/zenodo.23889782

# resumed at 2026-11-03T06:56:55+00:00
"$TSBENCH" run --plan "${TSBENCH_CLEAR_PLAN:?path of the clear plan with plan_id cfd9c463c00a27185bebf057746bda55b5251be8b5764687886f1e11a3a29e3c (kept outside the repo)}" --budget-usd 155.0 --out "$OUT" --i-have-preregistered 10.5281/zenodo.23889782 --resume
