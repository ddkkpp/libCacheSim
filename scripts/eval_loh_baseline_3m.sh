#!/bin/bash
set -euo pipefail

TRACE_FILE="${1:-data/WikiCDN/wiki_2019t.oracleGeneral.zst}"
CACHE_SIZE="${2:-0.1}"

# Optional: apply a known-good LOH config (feature toggles, penalty knobs, etc.)
# Example:
#   LOH_CONFIG_STR='LOH_SCORE_USE_IRT=1 LOH_USE_SOFTMAX=1 LOH_FEATURE_LOG1P=1 LOH_ENABLE_FEATURE_NORMALIZATION=1' \
#     LOH_FIXED_WEIGHTS='0.5,1,1,0,0,0' \
#     bash scripts/eval_loh_baseline_3m.sh data/WikiCDN/wiki_2019t.oracleGeneral.zst 0.1
if [ -n "${LOH_CONFIG_STR:-}" ]; then
  # shellcheck disable=SC1090
  source <(python3 scripts/config_str_to_exports.py --config "${LOH_CONFIG_STR}")
elif [ -n "${LOH_CONFIG_FILE:-}" ]; then
  # shellcheck disable=SC1090
  source <(python3 scripts/config_str_to_exports.py --config-file "${LOH_CONFIG_FILE}")
fi

NUM_REQ="${CACHESIM_NUM_REQ:-3000000}"
MISS_RATIO_WEIGHT="${LOH_MISS_RATIO_WEIGHT:-1.0}"

if [ ! -f "$TRACE_FILE" ]; then
  echo "[error] trace not found: $TRACE_FILE"
  exit 1
fi

TS="$(date +%m%d_%H%M%S)"
RUN_DIR="runs/loh_baseline_cfg_${TS}"
mkdir -p "$RUN_DIR"
EVAL_LOG="$RUN_DIR/baseline_eval.log"
CFG_DUMP="$RUN_DIR/env_dump.txt"

echo "[1/2] build debug binary"
bash scripts/debug.sh -c

TRACE_TYPE="oracleGeneral"
if [[ "$TRACE_FILE" == *.csv ]]; then
  TRACE_TYPE="csv"
  TRACE_TYPE_PARAMS=(--trace-type-params "time-col=1,obj-id-col=2,obj-size-col=3,obj-id-is-num=1,has-header=false,delimiter=")
else
  TRACE_TYPE_PARAMS=()
fi

echo "[2/2] evaluate baseline LOH (no RL; keep LOH_FIXED_WEIGHTS if set)"
export LOH_ENABLE_RL=0
unset LOH_TEACHER_EXPORT_PATH || true
unset LOH_TEACHER_EXPORT_APPEND || true
unset LOH_TEACHER_EXPORT_MAX_ROWS || true

{
  echo "LOH_CONFIG_STR=${LOH_CONFIG_STR:-<unset>}"
  echo "LOH_CONFIG_FILE=${LOH_CONFIG_FILE:-<unset>}"
  echo "LOH_FIXED_WEIGHTS=${LOH_FIXED_WEIGHTS:-<unset>}"
  env | grep -E '^(LOH_|RL_|CACHESIM_)' | sort
} >"$CFG_DUMP" || true

CMD=(
  _build_dbg/bin/cachesim
  "$TRACE_FILE"
  "$TRACE_TYPE"
  "LOH"
  "$CACHE_SIZE"
  "--eviction-params=miss-ratio-weight=$MISS_RATIO_WEIGHT"
  "--num-req=$NUM_REQ"
  -v 1
)
if [ ${#TRACE_TYPE_PARAMS[@]} -ne 0 ]; then
  CMD+=("${TRACE_TYPE_PARAMS[@]}")
fi

printf '  cmd:'; printf ' %q' "${CMD[@]}"; echo
"${CMD[@]}" >"$EVAL_LOG" 2>&1

echo "[done] baseline finished"
echo "  run_dir: $RUN_DIR"
echo "  env_dump: $CFG_DUMP"
echo "  baseline_eval_log: $EVAL_LOG"
