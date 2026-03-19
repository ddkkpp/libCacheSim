#!/usr/bin/env bash
set -uo pipefail

ROOT_DIR=$(cd "$(dirname "$0")/../.." && pwd)
cd "$ROOT_DIR"

OUT_DIR="tmp/unified_method_compare_0315"
RESULTS_CSV="$OUT_DIR/results.csv"
RUNNER_LOG="$OUT_DIR/runner.log"
PARALLEL=6
NUM_REQ=0
CACHE_SIZE=0.1

mkdir -p "$OUT_DIR"

echo "phase,trace,method,status,rc,mr,bmr,log_path" > "$RESULTS_CSV"
echo "[start] unified method compare (parallel=${PARALLEL}, num_req=${NUM_REQ})" | tee "$RUNNER_LOG"

extract_metric_pair() {
  local log_path="$1"
  local mr=""
  local bmr=""

  mr=$(grep -E '^\[RESULT\] Obj Miss Ratio:' "$log_path" | tail -n 1 | awk '{print $5}' || true)
  bmr=$(grep -E '^\[RESULT\] Byte Miss Ratio:' "$log_path" | tail -n 1 | awk '{print $5}' || true)

  if [ -z "${mr}" ] || [ -z "${bmr}" ]; then
    local last_line
    last_line=$(grep -E 'miss ratio [0-9]+\.[0-9]+, byte miss ratio [0-9]+\.[0-9]+' "$log_path" | tail -n 1 || true)
    if [ -n "$last_line" ]; then
      mr=$(echo "$last_line" | sed -n 's/.*miss ratio \([0-9][0-9]*\.[0-9][0-9]*\), byte miss ratio.*/\1/p')
      bmr=$(echo "$last_line" | sed -n 's/.*byte miss ratio \([0-9][0-9]*\.[0-9][0-9]*\).*/\1/p')
    fi
  fi

  [ -z "${mr}" ] && mr="NA"
  [ -z "${bmr}" ] && bmr="NA"
  echo "${mr},${bmr}"
}

# 沿用上一轮通用配置（固定单模式，不扫 4x3）
COMMON_ENV=(
  "CACHESIM_NUM_REQ=${NUM_REQ}"
  "LOH_PARALLEL_SAFE=1"
  "LOH_ENABLE_SEMAPHORE=1"
  "LOH_BUILD_RELEASE=1"
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
  "LOH_ENABLE_PENALTY=0"
  "LOH_MISS_RATIO_WEIGHT=1.0"
  "LOH_INCLUDE_REQUEST=0"
  "LOH_INCLUDE_WEIGHTS_IN_OBS=1"
  "LOH_ADAPTIVE_BUDGET=1"
  "LOH_USE_SCORE_REBALANCE=0"
  "LOH_DISABLE_NEWSTATE_EARLY_EXIT=1"
  "LOH_WAIT_NEWSTATE_MAX_CONSEC_TIMEOUTS=1800"
  "LOH_WAIT_NEWSTATE_IDLE_S=1800"
  "LOH_FEATURE_UNIFIED_FORMULA=1"
  "LOH_UNIFIED_VARIANT=1"
)

TRACES=(
  "meta|data/MetaCDN/meta_reag.oracleGeneral.zst"
  "1063|data/TencentCBS/1063.oracleGeneral.zst"
  "wiki|data/WikiCDN/wiki_2019t.oracleGeneral.zst"
)

METHODS=(
  "asym|LOH_UNIFIED_METHOD=2 LOH_UNIFIED_FREQ_CAP=4096"
  "alpha_mix|LOH_UNIFIED_METHOD=3 LOH_UNIFIED_ALPHA=0.60 LOH_UNIFIED_FREQ_CAP=4096"
)

run_one() {
  local phase="$1"
  local trace_name="$2"
  local trace_path="$3"
  local method_name="$4"
  local method_envs="$5"
  local norm_envs="$6"

  local case_name="${phase}_${trace_name}_${method_name}"
  local log_path="$OUT_DIR/${case_name}.log"
  local shm_key
  shm_key=$(printf "%s|umcmp0315|%s" "$case_name" "$OUT_DIR" | cksum | awk '{print $1}')

  rm -f "/dev/shm/loh_ac_${shm_key}" || true
  rm -f "/dev/shm/sem.loh_ac_ready_${shm_key}" || true
  rm -f "/dev/shm/sem.loh_ac_ack_${shm_key}" || true

  {
    echo "===== ${case_name} ====="
    echo "trace=${trace_path}"
    echo "cache=${CACHE_SIZE} num_req=${NUM_REQ}"
    echo "shm_key=${shm_key}"
    echo
  } > "$log_path"

  echo "[case-start] ${case_name}" >> "$RUNNER_LOG"

  local rc=0
  (
    set -uo pipefail
    export LOH_SHM_KEY="$shm_key"
    export RUN_TIMESTAMP="$(date +%m%d_%H%M%S)_${case_name}_$$"
    for kv in "${COMMON_ENV[@]}"; do export "$kv"; done
    for kv in $method_envs; do export "$kv"; done
    for kv in $norm_envs; do export "$kv"; done
    bash scripts/test_loh_rl_sb3.sh "$trace_path" "$CACHE_SIZE"
  ) >> "$log_path" 2>&1 || rc=$?

  local mr bmr metrics status
  metrics=$(extract_metric_pair "$log_path")
  mr="${metrics%,*}"
  bmr="${metrics#*,}"
  if [ "$rc" -eq 0 ]; then
    status="ok"
  else
    status="failed"
  fi

  echo "${phase},${trace_name},${method_name},${status},${rc},${mr},${bmr},${log_path}" >> "$RESULTS_CSV"
  echo "[case-done] ${case_name} status=${status} rc=${rc} mr=${mr} bmr=${bmr}" >> "$RUNNER_LOG"
  return 0
}

pids=()
start_case() {
  local phase="$1"
  local norm_envs="$2"
  local trace_def="$3"
  local method_def="$4"
  local trace_name trace_path method_name method_envs
  IFS='|' read -r trace_name trace_path <<< "$trace_def"
  IFS='|' read -r method_name method_envs <<< "$method_def"

  run_one "$phase" "$trace_name" "$trace_path" "$method_name" "$method_envs" "$norm_envs" &
  pids+=("$!")
}

wait_one() {
  local pid="${pids[0]}"
  wait "$pid" || true
  pids=("${pids[@]:1}")
}

run_phase() {
  local phase="$1"
  local norm_envs="$2"
  echo "[phase-start] ${phase}" | tee -a "$RUNNER_LOG"
  pids=()
  for trace_def in "${TRACES[@]}"; do
    for method_def in "${METHODS[@]}"; do
      while [ "${#pids[@]}" -ge "$PARALLEL" ]; do
        wait_one
      done
      start_case "$phase" "$norm_envs" "$trace_def" "$method_def"
    done
  done
  while [ "${#pids[@]}" -gt 0 ]; do
    wait_one
  done
  echo "[phase-done] ${phase}" | tee -a "$RUNNER_LOG"
}

run_phase "no_norm" "LOH_ENABLE_FEATURE_NORMALIZATION=0 LOH_ENABLE_ADAPTIVE_FEATURE_NORMALIZATION=0"
run_phase "adaptive_norm" "LOH_ENABLE_FEATURE_NORMALIZATION=0 LOH_ENABLE_ADAPTIVE_FEATURE_NORMALIZATION=1 LOH_ADAPTIVE_NORM_LO_Q=0.01 LOH_ADAPTIVE_NORM_HI_Q=0.99 LOH_ADAPTIVE_NORM_WARMUP=4096"

echo "[finished] results at ${RESULTS_CSV}" | tee -a "$RUNNER_LOG"
