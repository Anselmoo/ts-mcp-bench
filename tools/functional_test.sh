#!/usr/bin/env bash
# The functional test of this repository: the whole pipeline once, end to end, with one open model through the gateway
# (`tsbench ... --gateway`), or with the fake claude (--fake: no network, no key). See docs/functional-test.md.
#
#   tools/functional_test.sh --model qwen3.5-397b-a17b [--out functional-test] [--tasks ID,ID,...]
#   tools/functional_test.sh --fake [--out functional-test] [--no-trace]
#
# Every step is one tsbench command. Its command line, exit code and log are recorded in OUT/steps.jsonl. Each step is
# traced (TSBENCH_TRACE=OUT/trace/STEP; --no-trace turns this off) and OUT/provenance.html shows the call tree, the
# files read and written with their sha256, and whether the hash chain is intact. The last step renders
# OUT/SUMMARY.html (flow, pass/fail, links to every input and output). The key is read by NAME from the key file
# ($TSBENCH_KEY_FILE, default ~/.config/tsbench/env) in a subshell; its value is never printed or written.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

MODEL="" FAKE=0 TRACE=1 OUT=functional-test
TASKS="P-closed_form-01,P-tetrahedral-01,P-crossover-01"
while [ $# -gt 0 ]; do
  case "$1" in
    --model) MODEL="$2"; shift 2 ;;
    --fake) FAKE=1; shift ;;
    --out) OUT="$2"; shift 2 ;;
    --tasks) TASKS="$2"; shift 2 ;;
    --no-trace) TRACE=0; shift ;;
    -h|--help) sed -n 2,12p "$0"; exit 0 ;;
    *) echo "functional_test: unknown option $1" >&2; exit 2 ;;
  esac
done
[ "$FAKE" = 1 ] || [ -n "$MODEL" ] || { echo "functional_test: give --model MODEL (gateway) or --fake" >&2; exit 2; }
[ "$FAKE" = 1 ] && MODEL="${MODEL:-claude-haiku-5-5}"

TSBENCH="$PWD/.venv/bin/tsbench"
KEY_FILE="${TSBENCH_KEY_FILE:-$HOME/.config/tsbench/env}"
# the trace folders are absolute: the fake claude runs in another working directory
case "$OUT" in /*) OUT_ABS="$OUT" ;; *) OUT_ABS="$PWD/$OUT" ;; esac
OUT_ABS="${OUT_ABS%/}"
unset TSBENCH_TRACE
rm -rf "$OUT"
mkdir -p "$OUT/logs"
STEPS="$OUT/steps.jsonl"
: > "$STEPS"
# the mode decides the flags: the fake claude, or the gateway with GWDG_API_KEY under the Anthropic variable names
if [ "$FAKE" = 1 ]; then
  RUNFLAG="--dry-run" PROBEFLAG="--fake" GW="" MODE="fake claude (no network, no key)"
else
  RUNFLAG="" PROBEFLAG="" GW="--gateway" MODE="gateway, model $MODEL"
fi

# step NAME OUTPUTS -- COMMAND...: runs the command (in a subshell that loads the key for the gateway mode), appends
# one JSON line {name, command, rc, log, outputs} to steps.jsonl. OUTPUTS is a comma list of paths under OUT.
step() {
  local name="$1" outputs="$2"; shift 3
  local log="logs/$name.log" rc
  [ "$TRACE" = 1 ] && export TSBENCH_TRACE="$OUT_ABS/trace/$name"
  echo "== $name: $*"
  if [ "$FAKE" = 1 ]; then
    ( unset ANTHROPIC_API_KEY TSMCP_ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN GWDG_API_KEY GWDG_AI_API_KEY LITELLM_MASTER_KEY; "$@" ) > "$OUT/$log" 2>&1
  else
    # shellcheck source=/dev/null  # the key file is chosen at run time and never read by shellcheck
    ( set -a; . "$KEY_FILE"; set +a
      unset ANTHROPIC_API_KEY TSMCP_ANTHROPIC_API_KEY
      export ANTHROPIC_BASE_URL=https://chat-ai.academiccloud.de ANTHROPIC_AUTH_TOKEN="$GWDG_API_KEY"
      "$@" ) > "$OUT/$log" 2>&1
  fi
  rc=$?
  echo "   rc=$rc"
  "$PWD/.venv/bin/python" - "$STEPS" "$name" "$rc" "$log" "$outputs" "$@" <<'PY'
import json, shlex, sys
steps, name, rc, log, outputs, *cmd = sys.argv[1:]
cmd[0] = "tsbench" if cmd[0].endswith("/tsbench") else cmd[0]
rec = {"name": name, "command": shlex.join(cmd), "rc": int(rc), "log": log, "outputs": [o for o in outputs.split(",") if o]}
with open(steps, "a", encoding="utf-8") as f:
    f.write(json.dumps(rec) + "\n")
PY
  return "$rc"
}

step tasks-verify "" -- "$TSBENCH" tasks verify
step sandbox-probe "sandbox-probe/sandbox_probe.json" -- \
  "$TSBENCH" env sandbox --probe ${PROBEFLAG:+"$PROBEFLAG"} $GW --model "$MODEL" --out "$OUT/sandbox-probe"
step plan-build "plan/plan.jsonl,plan/plan.md" -- \
  "$TSBENCH" plan build --split pilot --models "$MODEL" --conditions C,B,A --effort medium --k 1 \
  --task-ids "$TASKS" --budget-usd 1000 $GW --out-plan "$OUT/plan/plan.jsonl"
step run "runs/README.md,runs/inputs/commands.sh,runs/inputs/hashes.json,runs/inputs/plan.jsonl,runs/MANIFEST.json" -- \
  "$TSBENCH" run --plan "$OUT/plan/plan.jsonl" --out "$OUT/runs" --budget-usd 1000 ${RUNFLAG:+"$RUNFLAG"} $GW
step score "runs/scores.csv,runs/rates.csv" -- "$TSBENCH" score --runs "$OUT/runs"
step figures "figures/" -- "$TSBENCH" figures all --runs "$OUT/runs" --out "$OUT/figures"
step report-views "pages/views.html" -- "$TSBENCH" report views --runs "$OUT/runs" --out "$OUT/pages/views.html"
step report-gallery "pages/gallery.html" -- "$TSBENCH" report gallery --runs "$OUT/runs" --out "$OUT/pages/gallery.html"
step report-dashboard "pages/dashboard.html" -- \
  "$TSBENCH" report dashboard --runs "$OUT/runs" --out "$OUT/pages/dashboard.html" --title "Functional test"
unset TSBENCH_TRACE
# not steps and not traced; the summary links the pages, so they come first. A broken chain fails the script.
PROV_RC=0
if [ "$TRACE" = 1 ]; then
  "$TSBENCH" report provenance --steps "$STEPS" --trace "$OUT/trace" --out "$OUT/provenance.html" || PROV_RC=$?
  [ "$PROV_RC" = 0 ] || echo "functional_test: provenance page failed or the hash chain is broken (rc=$PROV_RC)" >&2
  # the overview repeats the verdicts of the steps and the chain; its exit code adds nothing
  "$TSBENCH" report functional --steps "$STEPS" --trace "$OUT/trace" --mode "$MODE" --out "$OUT/OVERVIEW.html" || true
fi
"$TSBENCH" report summary --steps "$STEPS" --mode "$MODE" --out "$OUT/SUMMARY.html"
SUMMARY_RC=$?
[ "$SUMMARY_RC" != 0 ] || SUMMARY_RC=$PROV_RC
exit "$SUMMARY_RC"
