#!/usr/bin/env bash
set -u

ROOT_DIR=$(cd "$(dirname "$0")/../.." && pwd)
cd "$ROOT_DIR"

OUT_DIR="tmp/penalty_no_penalty_0316"
RESULTS_CSV="$OUT_DIR/results.csv"
RUNNER_LOG="$OUT_DIR/runner.log"
DOC_PATH="docs/20260317-FULL_EXPERIMENT_RESULTS.md"
TRACE_PATH="data/TencentCBS/1063.oracleGeneral.zst"
CACHE_SIZE="0.1"
CASE_NAME="no_penalty_baseline"
LOG_PATH="$OUT_DIR/${CASE_NAME}.log"

mkdir -p "$OUT_DIR"

echo "[start] single-case no-penalty baseline (1063,3M)" >> "$RUNNER_LOG"

cat > "$RESULTS_CSV" <<'CSV'
scale,formula,pos,status,rc,mr,bmr,mqps,log_path
CSV

update_doc_section() {
  if [ -f "$OUT_DIR/update_doc_section.py" ]; then
    (
      flock 9
      python3 "$OUT_DIR/update_doc_section.py" "$RESULTS_CSV" "$DOC_PATH" >> "$OUT_DIR/doc_update.log" 2>&1 || true
    ) 9>"$OUT_DIR/doc_update.lock"
  fi
}

extract_final() {
  local log_path="$1"
  awk '
    /LOH-OMR cache size/ {
      mr=""; bmr=""; mqps="";
      if (match($0, /miss ratio [0-9]+\.[0-9]+/)) mr = substr($0, RSTART + 11, RLENGTH - 11);
      if (match($0, /byte miss ratio [0-9]+\.[0-9]+/)) bmr = substr($0, RSTART + 16, RLENGTH - 16);
      if (match($0, /throughput [0-9]+\.[0-9]+ MQPS/)) mqps = substr($0, RSTART + 11, RLENGTH - 16);
      if (mr != "" && bmr != "" && mqps != "") last = mr "," bmr "," mqps;
    }
    END { if (last != "") print last; }
  ' "$log_path"
}

# User requested disabling hitmiss first; rebuild release with LOH_INCLUDE_HIT_MISS_FEATURES=0.
LOH_INCLUDE_HIT_MISS_FEATURES=0 LOH_BUILD_RELEASE=1 bash scripts/debug.sh -r -c >> "$OUT_DIR/prebuild_rel_no_hitmiss.log" 2>&1

echo "[case-start] ${CASE_NAME}" >> "$RUNNER_LOG"
rc=0
(
  export LOH_SHM_KEY="$(printf "%s|%s" "$CASE_NAME" "$(date +%s%N)" | cksum | awk '{print $1}')"
  export RUN_TIMESTAMP="$(date +%m%d_%H%M%S)_${CASE_NAME}_$$"
  export LOH_PARALLEL_SAFE=1
  export LOH_BUILD_RELEASE=1
  export LOH_SKIP_BUILD=1
  export LOH_SKIP_PIP_INSTALL=1
  export CACHESIM_NUM_REQ=3000000
  export LOH_ENABLE_RL=1
  export LOH_ENABLE_SEMAPHORE=1
  export LOH_SCORE_USE_COMPOUND=1
  export LOH_SCORE_USE_IRT=0
  export LOH_FEATURE_LOG1P=1
  export LOH_FEATURE_LOG1P_RECIPROCAL=0
  export LOH_DUAL_CHANNEL=0
  export LOH_RANDOM_CANDIDATES=96
  export LOH_MISS_RATIO_WEIGHT=1.0
  export LOH_ENABLE_PENALTY=0
  export LOH_INCLUDE_HIT_MISS_FEATURES=0
  export CACHESIM_VERBOSE=0
  bash scripts/test_loh_rl_sb3.sh "$TRACE_PATH" "$CACHE_SIZE"
) > "$LOG_PATH" 2>&1 || rc=$?

status="ok"
[ "$rc" -ne 0 ] && status="failed"

mr="NA"; bmr="NA"; mqps="NA"
fin=$(extract_final "$LOG_PATH" || true)
if [ -n "$fin" ]; then
  mr="$(echo "$fin" | cut -d',' -f1)"
  bmr="$(echo "$fin" | cut -d',' -f2)"
  mqps="$(echo "$fin" | cut -d',' -f3)"
fi

echo "baseline,none,0,${status},${rc},${mr},${bmr},${mqps},${LOG_PATH}" >> "$RESULTS_CSV"
echo "[case-done] ${CASE_NAME} status=${status} rc=${rc} mr=${mr} bmr=${bmr} mqps=${mqps}" >> "$RUNNER_LOG"
update_doc_section

echo "[finished] ${RESULTS_CSV}" >> "$RUNNER_LOG"
