#!/usr/bin/env bash
set -uo pipefail

ROOT_DIR=$(cd "$(dirname "$0")/../.." && pwd)
cd "$ROOT_DIR"

OUT_DIR="tmp/unified_variants_full_0315"
RESULTS_CSV="$OUT_DIR/results.csv"
RUNNER_LOG="$OUT_DIR/runner.log"
PARALLEL=4
NUM_REQ=0
CACHE_SIZE=0.1

mkdir -p "$OUT_DIR"

echo "trace,combo,status,rc,mr,bmr,log_path" > "$RESULTS_CSV"
echo "[start] unified variants full run (parallel=${PARALLEL}, num_req=${NUM_REQ})" | tee "$RUNNER_LOG"

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

# §21.3.1 通用配置 + 历史矩阵脚本补全项（weights_in_obs 等）
COMMON_ENV=(
  "CACHESIM_NUM_REQ=${NUM_REQ}"
  "LOH_PARALLEL_SAFE=1"
  "LOH_ENABLE_SEMAPHORE=1"
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
)

TRACES=(
  "1063|data/TencentCBS/1063.oracleGeneral.zst"
  "wiki|data/WikiCDN/wiki_2019t.oracleGeneral.zst"
  "meta|data/MetaCDN/meta_reag.oracleGeneral.zst"
)

# 4*3 全矩阵：4 个 unified variant × 3 个 normalization mode
VARIANTS=(
  "v1|LOH_UNIFIED_VARIANT=1"
  "v2|LOH_UNIFIED_VARIANT=2"
  "v3|LOH_UNIFIED_VARIANT=3"
  "v4|LOH_UNIFIED_VARIANT=4"
)

NORM_MODES=(
  "baseline|LOH_ENABLE_FEATURE_NORMALIZATION=0 LOH_ENABLE_ADAPTIVE_FEATURE_NORMALIZATION=0"
  "fixed_norm|LOH_ENABLE_FEATURE_NORMALIZATION=1 LOH_ENABLE_ADAPTIVE_FEATURE_NORMALIZATION=0"
  "adaptive_norm|LOH_ENABLE_FEATURE_NORMALIZATION=0 LOH_ENABLE_ADAPTIVE_FEATURE_NORMALIZATION=1 LOH_ADAPTIVE_NORM_LO_Q=0.01 LOH_ADAPTIVE_NORM_HI_Q=0.99 LOH_ADAPTIVE_NORM_WARMUP=4096"
)

run_one() {
  local trace_name="$1"
  local trace_path="$2"
  local combo_name="$3"
  local combo_envs="$4"

  local case_name="${trace_name}_${combo_name}"
  local log_path="$OUT_DIR/${case_name}.log"
  local shm_key
  shm_key=$(printf "%s|uvfull0315|%s" "$case_name" "$OUT_DIR" | cksum | awk '{print $1}')

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
    for kv in $combo_envs; do export "$kv"; done
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
  echo "${trace_name},${combo_name},${status},${rc},${mr},${bmr},${log_path}" >> "$RESULTS_CSV"
  echo "[case-done] ${case_name} status=${status} rc=${rc} mr=${mr} bmr=${bmr}" >> "$RUNNER_LOG"
  return 0
}

pids=()
start_case() {
  local trace_def="$1"
  local variant_def="$2"
  local mode_def="$3"
  local trace_name trace_path variant_name variant_envs mode_name mode_envs
  IFS='|' read -r trace_name trace_path <<< "$trace_def"
  IFS='|' read -r variant_name variant_envs <<< "$variant_def"
  IFS='|' read -r mode_name mode_envs <<< "$mode_def"

  local combo_name="${variant_name}_${mode_name}"
  local combo_envs="${variant_envs} ${mode_envs}"

  run_one "$trace_name" "$trace_path" "$combo_name" "$combo_envs" &
  pids+=("$!")
}

wait_one() {
  local pid="${pids[0]}"
  wait "$pid" || true
  pids=("${pids[@]:1}")
}

for trace_def in "${TRACES[@]}"; do
  for variant_def in "${VARIANTS[@]}"; do
    for mode_def in "${NORM_MODES[@]}"; do
      while [ "${#pids[@]}" -ge "$PARALLEL" ]; do
        wait_one
      done
      start_case "$trace_def" "$variant_def" "$mode_def"
    done
  done
done

while [ "${#pids[@]}" -gt 0 ]; do
  wait_one
done

echo "[finished] results at ${RESULTS_CSV}" | tee -a "$RUNNER_LOG"
