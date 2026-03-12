#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 [trace_file] [cache_size]"
  echo "  trace_file: optional, default data/TencentCBS/1063.oracleGeneral.zst"
  echo "  cache_size: optional, default 0.1"
  echo
  echo "Environment variables:"
  echo "  LOH_CONFIG_STR / LOH_CONFIG_FILE   Optional LOH config injection"
  echo "  CACHESIM_NUM_REQ                   Optional, default 3000000 for MetaCDN/TencentCBS"
  echo "  LOH_MISS_RATIO_WEIGHT              Optional, default 1.0"
  echo "  LOH_FIXED_WEIGHTS                  Optional; if unset, auto-predict"
  echo "  LOH_PREDICT_TOPK                   Optional, predictor top-k (default 1)"
  echo "  LOH_RUN_TIMEOUT_SEC                Optional, watchdog timeout in seconds (default 0 = no timeout)"
  exit 1
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
fi

TRACE_FILE="${1:-data/TencentCBS/1063.oracleGeneral.zst}"
CACHE_SIZE="${2:-0.1}"

if [ ! -f "$TRACE_FILE" ]; then
  echo "[error] trace not found: $TRACE_FILE"
  exit 1
fi

if [ -n "${LOH_CONFIG_STR:-}" ]; then
  # shellcheck disable=SC1090
  source <(python3 scripts/config_str_to_exports.py --config "${LOH_CONFIG_STR}")
elif [ -n "${LOH_CONFIG_FILE:-}" ]; then
  # shellcheck disable=SC1090
  source <(python3 scripts/config_str_to_exports.py --config-file "${LOH_CONFIG_FILE}")
fi

if [ ! -x "_build_dbg/bin/cachesim" ]; then
  echo "[error] missing _build_dbg/bin/cachesim; run: bash scripts/debug.sh -c"
  exit 1
fi

TRACE_TYPE="oracleGeneral"
TRACE_TYPE_ARGS=()
if [[ "$TRACE_FILE" == *.csv ]]; then
  TRACE_TYPE="csv"
  TRACE_TYPE_ARGS+=("--trace-type-params" "time-col=1,obj-id-col=2,obj-size-col=3,obj-id-is-num=1,has-header=false,delimiter=")
fi

if [ -z "${CACHESIM_NUM_REQ:-}" ]; then
  case "$TRACE_FILE" in
    data/MetaCDN/*|data/TencentCBS/*)
      export CACHESIM_NUM_REQ=3000000
      ;;
  esac
fi

MISS_RATIO_WEIGHT="${LOH_MISS_RATIO_WEIGHT:-1.0}"
RUN_TIMEOUT_SEC="${LOH_RUN_TIMEOUT_SEC:-0}"
RUN_TIMESTAMP="${RUN_TIMESTAMP:-$(date +%m%d_%H%M%S)}"
LOG_FILE="cachesim_fixed_pred_${RUN_TIMESTAMP}.log"

# fixed-mode defaults aligned with 1063 best-known setting; can still be overridden by env/config
export LOH_ENABLE_RL=0
export LOH_SCORE_USE_IRT="${LOH_SCORE_USE_IRT:-1}"
export LOH_SCORE_USE_COMPOUND="${LOH_SCORE_USE_COMPOUND:-1}"
export LOH_USE_HEURISTIC_SIGNS="${LOH_USE_HEURISTIC_SIGNS:-1}"
export LOH_USE_SOFTMAX="${LOH_USE_SOFTMAX:-1}"
export LOH_FEATURE_LOG1P="${LOH_FEATURE_LOG1P:-1}"
export LOH_FEATURE_LOG1P_RECIPROCAL="${LOH_FEATURE_LOG1P_RECIPROCAL:-0}"
export LOH_ENABLE_FEATURE_NORMALIZATION="${LOH_ENABLE_FEATURE_NORMALIZATION:-1}"
export LOH_SCORE_MODEL="${LOH_SCORE_MODEL:-linear}"

if [ -z "${LOH_FIXED_WEIGHTS:-}" ]; then
  echo "[predict] LOH_FIXED_WEIGHTS unset, predicting from trace profile..."
  if ! PRED_OUT=$(python3 scripts/loh_weight_predictor.py \
    --trace "$TRACE_FILE" \
    --trace-type "$TRACE_TYPE" \
    --cache-ratio "$CACHE_SIZE" \
    --num-req "${CACHESIM_NUM_REQ:-3000000}" \
    --eviction-params "miss-ratio-weight=${MISS_RATIO_WEIGHT}" \
    --top-k "${LOH_PREDICT_TOPK:-1}" \
    --min-entries "${LOH_PREDICT_MIN_ENTRIES:-5}" \
    --max-nearest-dist "${LOH_PREDICT_MAX_NEAREST_DIST:-0.25}"); then
    echo "[error] predictor refused to output weights (insufficient or low-confidence profile mapping)."
    echo "[hint] provide LOH_FIXED_WEIGHTS explicitly, or expand configs/loh_weight_profiles.json with trustworthy entries."
    exit 2
  fi
  echo "$PRED_OUT"
  PRED_W=$(echo "$PRED_OUT" | awk '/^Predicted LOH_FIXED_WEIGHTS=/{getline; print; exit}')
  if [ -z "$PRED_W" ]; then
    echo "[error] predictor did not output weights"
    exit 1
  fi
  export LOH_FIXED_WEIGHTS="$PRED_W"
fi

echo "[run] trace=$TRACE_FILE"
echo "[run] trace_type=$TRACE_TYPE"
echo "[run] cache_size=$CACHE_SIZE"
echo "[run] num_req=${CACHESIM_NUM_REQ:-ALL}"
echo "[run] LOH_FIXED_WEIGHTS=$LOH_FIXED_WEIGHTS"
echo "[run] log=$LOG_FILE"

CMD=("_build_dbg/bin/cachesim" "$TRACE_FILE" "$TRACE_TYPE" "LOH" "$CACHE_SIZE")
if [ ${#TRACE_TYPE_ARGS[@]} -ne 0 ]; then
  CMD+=("${TRACE_TYPE_ARGS[@]}")
fi
CMD+=("--eviction-params=miss-ratio-weight=${MISS_RATIO_WEIGHT}")
if [ -n "${CACHESIM_NUM_REQ:-}" ]; then
  CMD+=("--num-req=${CACHESIM_NUM_REQ}")
fi
CMD+=("-v" "0")

printf '[run] cmd:'; printf ' %q' "${CMD[@]}"; echo
"${CMD[@]}" > "$LOG_FILE" 2>&1 &
PID=$!

echo "[watch] cachesim pid=$PID"
START_TS=$(date +%s)
LAST_SIZE=0
while kill -0 "$PID" 2>/dev/null; do
  sleep 10
  NOW_TS=$(date +%s)
  ELAPSED=$((NOW_TS - START_TS))
  if [ -f "$LOG_FILE" ]; then
    SIZE=$(wc -c < "$LOG_FILE" | tr -d ' ')
    if [ "$SIZE" -gt "$LAST_SIZE" ]; then
      LAST_SIZE="$SIZE"
      echo "[watch ${ELAPSED}s] log grew to ${SIZE} bytes"
      tail -n 2 "$LOG_FILE" || true
    else
      echo "[watch ${ELAPSED}s] running... (no new log bytes)"
    fi
  fi

  if [ "$RUN_TIMEOUT_SEC" -gt 0 ] && [ "$ELAPSED" -ge "$RUN_TIMEOUT_SEC" ]; then
    echo "[watch] timeout ${RUN_TIMEOUT_SEC}s reached, terminating pid=$PID"
    kill -INT "$PID" 2>/dev/null || true
    sleep 1
    kill -TERM "$PID" 2>/dev/null || true
    sleep 1
    kill -KILL "$PID" 2>/dev/null || true
    wait "$PID" || true
    echo "[error] timed out"
    exit 124
  fi
done

wait "$PID"

echo "[done] finished. result summary:"
if grep -q 'miss ratio' "$LOG_FILE"; then
  grep 'miss ratio' "$LOG_FILE" | tail -n 1
else
  echo "[warn] no miss ratio line found in log"
fi
