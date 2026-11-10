#!/usr/bin/env bash
# Run set: qwen3-30b-a3b-instruct-2507 | conditions C,B,A | effort medium | k=3 | confirmatory (55 tasks) | gateway
# Written by `tsbench run` (tsbench 0.1.0, commit e7f956056098acc0f60065eaa88655b586e93a42) at 2026-11-05T10:16:24+00:00.
# plan_id 6768389db61bcdc737ca6ba7fe1f3b8a093ba58e3a9237e6b26ea1247603d045
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
# the invocation (host paths as placeholders): tsbench run --plan <HOME>/tsbench-confirmatory-plans/plan-2b-qwen3-30b.jsonl --out <OUT> --gateway --i-have-preregistered 10.5281/zenodo.23889782

# environment (names only)
export ANTHROPIC_BASE_URL=https://chat-ai.academiccloud.de
export ANTHROPIC_AUTH_TOKEN="${GWDG_API_KEY:?set GWDG_API_KEY (see ${TSBENCH_KEY_FILE:-$HOME/.config/tsbench/env})}"
unset ANTHROPIC_API_KEY TSMCP_ANTHROPIC_API_KEY

# 1. the plan, rebuilt from its header's spec (the run below uses the stored plan.sealed.json anyway)
"$TSBENCH" plan build --split confirmatory --models qwen3-30b-a3b-instruct-2507 --conditions C,B,A --effort medium --k 3 --budget-usd 1000.0 --gateway --i-have-preregistered 10.5281/zenodo.23889782 --out-plan "$OUT/inputs/rebuilt/plan.jsonl"
grep -q '"plan_id": "6768389db61bcdc737ca6ba7fe1f3b8a093ba58e3a9237e6b26ea1247603d045"' "$OUT/inputs/rebuilt/plan.sealed.json" || echo "WARNING: the rebuilt plan has another plan_id (task set or code changed); the run uses the stored plan" >&2

# 2. the run
"$TSBENCH" run --plan "${TSBENCH_CLEAR_PLAN:?path of the clear plan with plan_id 6768389db61bcdc737ca6ba7fe1f3b8a093ba58e3a9237e6b26ea1247603d045 (kept outside the repo)}" --out "$OUT" --gateway --i-have-preregistered 10.5281/zenodo.23889782

# resumed at 2026-11-05T10:16:24+00:00
"$TSBENCH" run --plan "${TSBENCH_CLEAR_PLAN:?path of the clear plan with plan_id 6768389db61bcdc737ca6ba7fe1f3b8a093ba58e3a9237e6b26ea1247603d045 (kept outside the repo)}" --out "$OUT" --gateway --i-have-preregistered 10.5281/zenodo.23889782 --resume

# resumed at 2026-11-05T10:16:24+00:00
"$TSBENCH" run --plan "${TSBENCH_CLEAR_PLAN:?path of the clear plan with plan_id 6768389db61bcdc737ca6ba7fe1f3b8a093ba58e3a9237e6b26ea1247603d045 (kept outside the repo)}" --out "$OUT" --gateway --i-have-preregistered 10.5281/zenodo.23889782 --resume

# resumed at 2026-11-05T10:16:24+00:00
"$TSBENCH" run --plan "${TSBENCH_CLEAR_PLAN:?path of the clear plan with plan_id 6768389db61bcdc737ca6ba7fe1f3b8a093ba58e3a9237e6b26ea1247603d045 (kept outside the repo)}" --out "$OUT" --gateway --i-have-preregistered 10.5281/zenodo.23889782 --resume

# resumed at 2026-11-05T10:16:24+00:00
"$TSBENCH" run --plan "${TSBENCH_CLEAR_PLAN:?path of the clear plan with plan_id 6768389db61bcdc737ca6ba7fe1f3b8a093ba58e3a9237e6b26ea1247603d045 (kept outside the repo)}" --out "$OUT" --gateway --i-have-preregistered 10.5281/zenodo.23889782 --resume

# resumed at 2026-11-05T10:16:24+00:00
"$TSBENCH" run --plan "${TSBENCH_CLEAR_PLAN:?path of the clear plan with plan_id 6768389db61bcdc737ca6ba7fe1f3b8a093ba58e3a9237e6b26ea1247603d045 (kept outside the repo)}" --out "$OUT" --gateway --i-have-preregistered 10.5281/zenodo.23889782 --resume

# resumed at 2026-11-05T10:16:24+00:00
"$TSBENCH" run --plan "${TSBENCH_CLEAR_PLAN:?path of the clear plan with plan_id 6768389db61bcdc737ca6ba7fe1f3b8a093ba58e3a9237e6b26ea1247603d045 (kept outside the repo)}" --out "$OUT" --gateway --i-have-preregistered 10.5281/zenodo.23889782 --resume

# resumed at 2026-11-05T10:16:24+00:00
"$TSBENCH" run --plan "${TSBENCH_CLEAR_PLAN:?path of the clear plan with plan_id 6768389db61bcdc737ca6ba7fe1f3b8a093ba58e3a9237e6b26ea1247603d045 (kept outside the repo)}" --out "$OUT" --gateway --i-have-preregistered 10.5281/zenodo.23889782 --resume

# resumed at 2026-11-05T10:16:24+00:00
"$TSBENCH" run --plan "${TSBENCH_CLEAR_PLAN:?path of the clear plan with plan_id 6768389db61bcdc737ca6ba7fe1f3b8a093ba58e3a9237e6b26ea1247603d045 (kept outside the repo)}" --out "$OUT" --gateway --i-have-preregistered 10.5281/zenodo.23889782 --resume

# resumed at 2026-11-05T10:16:24+00:00
"$TSBENCH" run --plan "${TSBENCH_CLEAR_PLAN:?path of the clear plan with plan_id 6768389db61bcdc737ca6ba7fe1f3b8a093ba58e3a9237e6b26ea1247603d045 (kept outside the repo)}" --out "$OUT" --gateway --i-have-preregistered 10.5281/zenodo.23889782 --resume

# resumed at 2026-11-05T10:16:24+00:00
"$TSBENCH" run --plan "${TSBENCH_CLEAR_PLAN:?path of the clear plan with plan_id 6768389db61bcdc737ca6ba7fe1f3b8a093ba58e3a9237e6b26ea1247603d045 (kept outside the repo)}" --out "$OUT" --gateway --i-have-preregistered 10.5281/zenodo.23889782 --resume

# resumed at 2026-11-05T10:16:24+00:00
"$TSBENCH" run --plan "${TSBENCH_CLEAR_PLAN:?path of the clear plan with plan_id 6768389db61bcdc737ca6ba7fe1f3b8a093ba58e3a9237e6b26ea1247603d045 (kept outside the repo)}" --out "$OUT" --gateway --i-have-preregistered 10.5281/zenodo.23889782 --resume

# resumed at 2026-11-05T10:16:24+00:00
"$TSBENCH" run --plan "${TSBENCH_CLEAR_PLAN:?path of the clear plan with plan_id 6768389db61bcdc737ca6ba7fe1f3b8a093ba58e3a9237e6b26ea1247603d045 (kept outside the repo)}" --out "$OUT" --gateway --i-have-preregistered 10.5281/zenodo.23889782 --resume

# resumed at 2026-11-05T10:16:24+00:00
"$TSBENCH" run --plan "${TSBENCH_CLEAR_PLAN:?path of the clear plan with plan_id 6768389db61bcdc737ca6ba7fe1f3b8a093ba58e3a9237e6b26ea1247603d045 (kept outside the repo)}" --out "$OUT" --gateway --i-have-preregistered 10.5281/zenodo.23889782 --resume

# resumed at 2026-11-05T10:16:24+00:00
"$TSBENCH" run --plan "${TSBENCH_CLEAR_PLAN:?path of the clear plan with plan_id 6768389db61bcdc737ca6ba7fe1f3b8a093ba58e3a9237e6b26ea1247603d045 (kept outside the repo)}" --out "$OUT" --gateway --i-have-preregistered 10.5281/zenodo.23889782 --resume

# resumed at 2026-11-05T10:16:24+00:00
"$TSBENCH" run --plan "${TSBENCH_CLEAR_PLAN:?path of the clear plan with plan_id 6768389db61bcdc737ca6ba7fe1f3b8a093ba58e3a9237e6b26ea1247603d045 (kept outside the repo)}" --out "$OUT" --gateway --i-have-preregistered 10.5281/zenodo.23889782 --resume

# resumed at 2026-11-05T10:16:24+00:00
"$TSBENCH" run --plan "${TSBENCH_CLEAR_PLAN:?path of the clear plan with plan_id 6768389db61bcdc737ca6ba7fe1f3b8a093ba58e3a9237e6b26ea1247603d045 (kept outside the repo)}" --out "$OUT" --gateway --i-have-preregistered 10.5281/zenodo.23889782 --resume

# resumed at 2026-11-05T10:16:24+00:00
"$TSBENCH" run --plan "${TSBENCH_CLEAR_PLAN:?path of the clear plan with plan_id 6768389db61bcdc737ca6ba7fe1f3b8a093ba58e3a9237e6b26ea1247603d045 (kept outside the repo)}" --out "$OUT" --gateway --i-have-preregistered 10.5281/zenodo.23889782 --resume

# resumed at 2026-11-05T10:16:24+00:00
"$TSBENCH" run --plan "${TSBENCH_CLEAR_PLAN:?path of the clear plan with plan_id 6768389db61bcdc737ca6ba7fe1f3b8a093ba58e3a9237e6b26ea1247603d045 (kept outside the repo)}" --out "$OUT" --gateway --i-have-preregistered 10.5281/zenodo.23889782 --resume

# resumed at 2026-11-05T10:16:24+00:00
"$TSBENCH" run --plan "${TSBENCH_CLEAR_PLAN:?path of the clear plan with plan_id 6768389db61bcdc737ca6ba7fe1f3b8a093ba58e3a9237e6b26ea1247603d045 (kept outside the repo)}" --out "$OUT" --gateway --i-have-preregistered 10.5281/zenodo.23889782 --resume

# resumed at 2026-11-05T10:16:24+00:00
"$TSBENCH" run --plan "${TSBENCH_CLEAR_PLAN:?path of the clear plan with plan_id 6768389db61bcdc737ca6ba7fe1f3b8a093ba58e3a9237e6b26ea1247603d045 (kept outside the repo)}" --out "$OUT" --gateway --i-have-preregistered 10.5281/zenodo.23889782 --resume

# resumed at 2026-11-05T10:16:24+00:00
"$TSBENCH" run --plan "${TSBENCH_CLEAR_PLAN:?path of the clear plan with plan_id 6768389db61bcdc737ca6ba7fe1f3b8a093ba58e3a9237e6b26ea1247603d045 (kept outside the repo)}" --out "$OUT" --gateway --i-have-preregistered 10.5281/zenodo.23889782 --resume

# resumed at 2026-11-05T10:16:24+00:00
"$TSBENCH" run --plan "${TSBENCH_CLEAR_PLAN:?path of the clear plan with plan_id 6768389db61bcdc737ca6ba7fe1f3b8a093ba58e3a9237e6b26ea1247603d045 (kept outside the repo)}" --out "$OUT" --gateway --i-have-preregistered 10.5281/zenodo.23889782 --resume

# resumed at 2026-11-05T10:16:24+00:00
"$TSBENCH" run --plan "${TSBENCH_CLEAR_PLAN:?path of the clear plan with plan_id 6768389db61bcdc737ca6ba7fe1f3b8a093ba58e3a9237e6b26ea1247603d045 (kept outside the repo)}" --out "$OUT" --gateway --i-have-preregistered 10.5281/zenodo.23889782 --resume

# resumed at 2026-11-05T10:16:24+00:00
"$TSBENCH" run --plan "${TSBENCH_CLEAR_PLAN:?path of the clear plan with plan_id 6768389db61bcdc737ca6ba7fe1f3b8a093ba58e3a9237e6b26ea1247603d045 (kept outside the repo)}" --out "$OUT" --gateway --i-have-preregistered 10.5281/zenodo.23889782 --resume

# resumed at 2026-11-05T10:16:24+00:00
"$TSBENCH" run --plan "${TSBENCH_CLEAR_PLAN:?path of the clear plan with plan_id 6768389db61bcdc737ca6ba7fe1f3b8a093ba58e3a9237e6b26ea1247603d045 (kept outside the repo)}" --out "$OUT" --gateway --i-have-preregistered 10.5281/zenodo.23889782 --resume

# resumed at 2026-11-05T10:16:24+00:00
"$TSBENCH" run --plan "${TSBENCH_CLEAR_PLAN:?path of the clear plan with plan_id 6768389db61bcdc737ca6ba7fe1f3b8a093ba58e3a9237e6b26ea1247603d045 (kept outside the repo)}" --out "$OUT" --gateway --i-have-preregistered 10.5281/zenodo.23889782 --resume

# resumed at 2026-11-05T10:16:24+00:00
"$TSBENCH" run --plan "${TSBENCH_CLEAR_PLAN:?path of the clear plan with plan_id 6768389db61bcdc737ca6ba7fe1f3b8a093ba58e3a9237e6b26ea1247603d045 (kept outside the repo)}" --out "$OUT" --gateway --i-have-preregistered 10.5281/zenodo.23889782 --resume

# resumed at 2026-11-05T10:16:24+00:00
"$TSBENCH" run --plan "${TSBENCH_CLEAR_PLAN:?path of the clear plan with plan_id 6768389db61bcdc737ca6ba7fe1f3b8a093ba58e3a9237e6b26ea1247603d045 (kept outside the repo)}" --out "$OUT" --gateway --i-have-preregistered 10.5281/zenodo.23889782 --resume

# resumed at 2026-11-05T10:16:24+00:00
"$TSBENCH" run --plan "${TSBENCH_CLEAR_PLAN:?path of the clear plan with plan_id 6768389db61bcdc737ca6ba7fe1f3b8a093ba58e3a9237e6b26ea1247603d045 (kept outside the repo)}" --out "$OUT" --gateway --i-have-preregistered 10.5281/zenodo.23889782 --resume

# resumed at 2026-11-05T10:16:24+00:00
"$TSBENCH" run --plan "${TSBENCH_CLEAR_PLAN:?path of the clear plan with plan_id 6768389db61bcdc737ca6ba7fe1f3b8a093ba58e3a9237e6b26ea1247603d045 (kept outside the repo)}" --out "$OUT" --gateway --i-have-preregistered 10.5281/zenodo.23889782 --resume

# resumed at 2026-11-05T10:16:24+00:00
"$TSBENCH" run --plan "${TSBENCH_CLEAR_PLAN:?path of the clear plan with plan_id 6768389db61bcdc737ca6ba7fe1f3b8a093ba58e3a9237e6b26ea1247603d045 (kept outside the repo)}" --out "$OUT" --gateway --i-have-preregistered 10.5281/zenodo.23889782 --resume

# resumed at 2026-11-05T10:16:24+00:00
"$TSBENCH" run --plan "${TSBENCH_CLEAR_PLAN:?path of the clear plan with plan_id 6768389db61bcdc737ca6ba7fe1f3b8a093ba58e3a9237e6b26ea1247603d045 (kept outside the repo)}" --out "$OUT" --gateway --i-have-preregistered 10.5281/zenodo.23889782 --resume
