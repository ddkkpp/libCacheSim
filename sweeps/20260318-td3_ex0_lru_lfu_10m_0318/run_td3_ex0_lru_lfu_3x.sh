#!/usr/bin/env bash
set -u

ROOT_DIR=$(cd "$(dirname "$0")/../.." && pwd)
cd "$ROOT_DIR"

OUT_DIR="tmp/td3_ex0_lru_lfu_10m_0318"
mkdir -p "$OUT_DIR"

REQS="${REQS:-0}"
CACHE_SIZE="${CACHE_SIZE:-0.1}"
MAX_PARALLEL="${MAX_PARALLEL:-3}"

RUNNER_LOG="$OUT_DIR/runner.log"
CSV_PATH="$OUT_DIR/results.csv"

if [ ! -f "$CSV_PATH" ]; then
  cat > "$CSV_PATH" <<'CSV'
run_tag,trace,seed,exclude_recent_steps,final_mr,final_bmr,final_mqps,log_path,rc
CSV
fi

extract_final() {
  local log_path="$1"
  awk '
    /LOH-.*cache size/ {
      mr=""; bmr=""; mqps="";
      if (match($0, /miss ratio [0-9]+\.[0-9]+/)) mr = substr($0, RSTART + 11, RLENGTH - 11);
      if (match($0, /byte miss ratio [0-9]+\.[0-9]+/)) bmr = substr($0, RSTART + 16, RLENGTH - 16);
      if (match($0, /throughput [0-9]+\.[0-9]+ MQPS/)) mqps = substr($0, RSTART + 11, RLENGTH - 16);
      if (mr != "" && bmr != "" && mqps != "") last = mr "," bmr "," mqps;
    }
    END { if (last != "") print last; }
  ' "$log_path"
}

run_case() {
  local run_tag="$1"
  local seed="$2"
  local trace_name="$3"
  local trace_path="$4"

  local stamp="$(date +%m%d_%H%M%S)"
  local case_name="${trace_name}_TD3_ex0_${run_tag}_${stamp}"
  local log_path="$OUT_DIR/${case_name}.log"
  local rc=0

  local shm_key
  shm_key=$(printf "%s|%s|%s|%s|%s" "$trace_name" "TD3" "0" "$CACHE_SIZE" "${seed}_${run_tag}_${stamp}" | cksum | awk '{print $1}')
  rm -f "/dev/shm/loh_ac_${shm_key}" "/dev/shm/sem.loh_ac_ready_${shm_key}" "/dev/shm/sem.loh_ac_ack_${shm_key}" || true

  echo "[case-start] run_tag=${run_tag} trace=${trace_name} seed=${seed}" >> "$RUNNER_LOG"
  (
    export LOH_SHM_KEY="$shm_key"
    export LOH_RL_ALGO="TD3"
    export LOH_EXCLUDE_RECENT_STEPS="0"
    export LOH_SEED="$seed"
    export CACHESIM_NUM_REQ="$REQS"
    export LOH_PARALLEL_SAFE=1
    export LOH_ENABLE_SEMAPHORE=1
    export LOH_SEM_TIMEOUT_S=1.0
    export LOH_WAIT_NEWSTATE_MAX_CONSEC_TIMEOUTS=1800
    export LOH_WAIT_NEWSTATE_IDLE_S=1800
    export LOH_BUILD_RELEASE=1
    export LOH_SKIP_BUILD=1
    export LOH_SKIP_PIP_INSTALL=1
    export LOH_PERF_PROFILING=0
    export LOH_DEBUG_LEVEL=1
    export LOH_ENABLE_RL=1
    export LOH_SCORE_USE_COMPOUND=1
    export LOH_SCORE_USE_IRT=0
    export LOH_RANDOM_CANDIDATES=96
    export LOH_STRUCTURED_CANDIDATES=96
    export LOH_WAIT_MODE=nonblocked
    export LOH_ASYNC_TRAIN=1
    export LOH_MISS_RATIO_WEIGHT=1.0
    export LOH_INCLUDE_WEIGHTS_IN_OBS=1
    export LOH_ADAPTIVE_BUDGET=1
    export LOH_USE_SCORE_REBALANCE=0
    export LOH_FEATURE_UNIFIED_FORMULA=0
    export LOH_FEATURE_IDENTITY=0
    export LOH_FEATURE_LOG1P=1
    export LOH_FEATURE_LOG1P_RECIPROCAL=0
    export LOH_ENABLE_FEATURE_NORMALIZATION=0
    export LOH_ENABLE_ADAPTIVE_FEATURE_NORMALIZATION=1
    export LOH_ADAPTIVE_NORM_LO_Q=0.0
    export LOH_ADAPTIVE_NORM_HI_Q=1.0
    export LOH_ADAPTIVE_NORM_WARMUP=0
    export LOH_ADAPTIVE_NORM_TRANSFORM_QUANTILE=0
    export LOH_INCLUDE_HIT_MISS_FEATURES=0
    export RUN_TIMESTAMP="$(date +%m%d_%H%M%S)_${case_name}_$(date +%s)"
    bash scripts/test_loh_rl_sb3.sh "$trace_path" "$CACHE_SIZE"
  ) > "$log_path" 2>&1 || rc=$?

  local fin
  local fmr="NA"
  local fbmr="NA"
  local fmqps="NA"
  fin=$(extract_final "$log_path" || true)
  if [ -n "$fin" ]; then
    fmr="$(echo "$fin" | cut -d',' -f1)"
    fbmr="$(echo "$fin" | cut -d',' -f2)"
    fmqps="$(echo "$fin" | cut -d',' -f3)"
  fi

  echo "${run_tag},${trace_name},${seed},0,${fmr},${fbmr},${fmqps},${log_path},${rc}" >> "$CSV_PATH"
  echo "[case-done] run_tag=${run_tag} trace=${trace_name} seed=${seed} rc=${rc} final_mr=${fmr} final_bmr=${fbmr} final_mqps=${fmqps}" >> "$RUNNER_LOG"
}

TRACES=(
  "lru10m|data/lrutest_10m.csv"
  "lfu10m|data/lfutest_10m.csv"
)

SEED1="${SEED1:-$((RANDOM + 20280000))}"
SEED2="${SEED2:-$((RANDOM + 20290000))}"
SEED3="${SEED3:-$((RANDOM + 20300000))}"
RUNS=(
  "run1|$SEED1"
  "run2|$SEED2"
  "run3|$SEED3"
)

echo "[start] td3 ex0 lru+lfu 3x reqs=${REQS} cache=${CACHE_SIZE} seeds=${SEED1},${SEED2},${SEED3}" >> "$RUNNER_LOG"

running=0
for r in "${RUNS[@]}"; do
  IFS='|' read -r run_tag run_seed <<< "$r"
  for t in "${TRACES[@]}"; do
    IFS='|' read -r trace_name trace_path <<< "$t"
    run_case "$run_tag" "$run_seed" "$trace_name" "$trace_path" &
    running=$((running + 1))
    if [ "$running" -ge "$MAX_PARALLEL" ]; then
      wait -n || true
      running=$((running - 1))
    fi
  done
done

while [ "$running" -gt 0 ]; do
  wait -n || true
  running=$((running - 1))
done

echo "[finished] td3 ex0 lru+lfu 3x" >> "$RUNNER_LOG"
