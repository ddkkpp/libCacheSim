#!/usr/bin/env bash
set -u

ROOT_DIR=$(cd "$(dirname "$0")/../.." && pwd)
cd "$ROOT_DIR"

OUT_DIR="tmp/log1p_qinput_276_3trace_0317"
RESULTS_CSV="$OUT_DIR/results.csv"
RUNNER_LOG="$OUT_DIR/runner.log"
DOC_PATH="docs/20260317-FULL_EXPERIMENT_RESULTS.md"
CACHE_SIZE=0.1

mkdir -p "$OUT_DIR"

if [ ! -f "$RESULTS_CSV" ]; then
cat > "$RESULTS_CSV" <<'CSV'
trace,status,rc,final_mr,final_bmr,final_mqps,log_path
CSV
fi

echo "[resume-start] serial pending traces for 27.4" >> "$RUNNER_LOG"

COMMON_ENV=(
  "CACHESIM_NUM_REQ=0"
  "LOH_PARALLEL_SAFE=1"
  "LOH_ENABLE_SEMAPHORE=1"
  "LOH_SEM_TIMEOUT_S=1.0"
  "LOH_WAIT_NEWSTATE_MAX_CONSEC_TIMEOUTS=1800"
  "LOH_WAIT_NEWSTATE_IDLE_S=1800"
  "LOH_BUILD_RELEASE=1"
  "LOH_SKIP_BUILD=1"
  "LOH_SKIP_PIP_INSTALL=1"
  "LOH_PERF_PROFILING=0"
  "LOH_DEBUG_LEVEL=0"
  "LOH_ENABLE_RL=1"
  "LOH_SCORE_USE_COMPOUND=1"
  "LOH_SCORE_USE_IRT=0"
  "LOH_RANDOM_CANDIDATES=96"
  "LOH_STRUCTURED_CANDIDATES=96"
  "LOH_WAIT_MODE=nonblocked"
  "LOH_ASYNC_TRAIN=1"
  "LOH_MISS_RATIO_WEIGHT=1.0"
  "LOH_INCLUDE_WEIGHTS_IN_OBS=1"
  "LOH_ADAPTIVE_BUDGET=1"
  "LOH_USE_SCORE_REBALANCE=0"
  "LOH_FEATURE_UNIFIED_FORMULA=0"
  "LOH_FEATURE_IDENTITY=0"
  "LOH_FEATURE_LOG1P=1"
  "LOH_FEATURE_LOG1P_RECIPROCAL=0"
  "LOH_ENABLE_FEATURE_NORMALIZATION=0"
  "LOH_ENABLE_ADAPTIVE_FEATURE_NORMALIZATION=1"
  "LOH_ADAPTIVE_NORM_LO_Q=0.0"
  "LOH_ADAPTIVE_NORM_HI_Q=1.0"
  "LOH_ADAPTIVE_NORM_WARMUP=0"
  "LOH_ADAPTIVE_NORM_QUANTILE_INPUT=log1p"
  "LOH_INCLUDE_HIT_MISS_FEATURES=0"
)

TASKS=(
  "CloudPhysics-w01|data/cloudphysics/w01.oracleGeneral.bin.zst"
  "Twitter-13|data/twitter/cluster13.oracleGeneral.zst"
)

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

already_done() {
  local trace_name="$1"
  grep -q "^${trace_name},ok," "$RESULTS_CSV"
}

run_one() {
  local trace_name="$1"
  local trace_path="$2"

  if already_done "$trace_name"; then
    echo "[resume-skip] ${trace_name} already done" >> "$RUNNER_LOG"
    return 0
  fi

  local case_name="${trace_name}_log1p_qinput_log1p_hitmiss0"
  local case_stamp
  case_stamp="$(date +%m%d_%H%M%S)"
  local log_path="$OUT_DIR/${case_name}_${case_stamp}.log"
  local shm_key rc=0

  shm_key=$(printf "%s|%s" "$trace_name" "$(date +%s%N)" | cksum | awk '{print $1}')
  rm -f "/dev/shm/loh_ac_${shm_key}" "/dev/shm/sem.loh_ac_ready_${shm_key}" "/dev/shm/sem.loh_ac_ack_${shm_key}" || true

  echo "[case-start] ${case_name}" >> "$RUNNER_LOG"
  (
    export LOH_SHM_KEY="$shm_key"
    export RUN_TIMESTAMP="$(date +%m%d_%H%M%S)_${case_name}_$$"
    for kv in "${COMMON_ENV[@]}"; do export "$kv"; done
    bash scripts/test_loh_rl_sb3.sh "$trace_path" "$CACHE_SIZE"
  ) > "$log_path" 2>&1 || rc=$?

  local fin fmr="NA" fbmr="NA" fmqps="NA" status="ok"
  fin=$(extract_final "$log_path" || true)
  if [ -n "$fin" ]; then
    fmr="$(echo "$fin" | cut -d',' -f1)"
    fbmr="$(echo "$fin" | cut -d',' -f2)"
    fmqps="$(echo "$fin" | cut -d',' -f3)"
  fi
  [ "$rc" -ne 0 ] && status="failed"

  echo "${trace_name},${status},${rc},${fmr},${fbmr},${fmqps},${log_path}" >> "$RESULTS_CSV"
  echo "[case-done] ${case_name} status=${status} rc=${rc} final_mr=${fmr} final_bmr=${fbmr} final_mqps=${fmqps}" >> "$RUNNER_LOG"

  if [ -f "$OUT_DIR/update_doc_section.py" ]; then
    (
      flock 9
      python3 "$OUT_DIR/update_doc_section.py" "$RESULTS_CSV" "$DOC_PATH" >> "$OUT_DIR/doc_update.log" 2>&1 || true
    ) 9>"$OUT_DIR/doc_update.lock"
  fi
}

for t in "${TASKS[@]}"; do
  IFS='|' read -r trace_name trace_path <<< "$t"
  run_one "$trace_name" "$trace_path"
done

echo "[resume-finished] ${RESULTS_CSV}" >> "$RUNNER_LOG"
