#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "$0")/../.." && pwd)
cd "$ROOT_DIR"

OUT_DIR="tmp/sec20_matrix_0314_run"
RESULTS_CSV="$OUT_DIR/results.csv"
RUNNER_LOG="$OUT_DIR/runner.log"

echo "trace,formula,mode,mr,bmr,log_path" > "$RESULTS_CSV"

COMMON_ENV=(
  "CACHESIM_NUM_REQ=3000000"
  "LOH_ENABLE_SEMAPHORE=1"
  "LOH_BUILD_RELEASE=1"
  "LOH_PERF_PROFILING=0"
  "LOH_DEBUG_LEVEL=0"
  "LOH_SCORE_USE_COMPOUND=1"
  "LOH_SCORE_USE_IRT=0"
  "LOH_RANDOM_CANDIDATES=96"
  "LOH_STRUCTURED_CANDIDATES=96"
  "LOH_WAIT_MODE=nonblocked"
  "LOH_ASYNC_TRAIN=1"
  "LOH_ENABLE_PENALTY=0"
  "LOH_MISS_RATIO_WEIGHT=1.0"
  "LOH_INCLUDE_WEIGHTS_IN_OBS=1"
  "LOH_ADAPTIVE_BUDGET=1"
  "LOH_USE_SCORE_REBALANCE=0"
  "LOH_ENABLE_RL=1"
  "LOH_SKIP_BUILD=0"
  "LOH_SKIP_PIP_INSTALL=1"
  "LOH_DISABLE_NEWSTATE_EARLY_EXIT=1"
  "LOH_WAIT_NEWSTATE_MAX_CONSEC_TIMEOUTS=1800"
  "LOH_WAIT_NEWSTATE_IDLE_S=1800"
)

CASES=(
  "1063|data/TencentCBS/1063.oracleGeneral.zst|log1p|LOH_FEATURE_LOG1P=1 LOH_FEATURE_LOG1P_RECIPROCAL=0"
  "wiki|data/WikiCDN/wiki_2019t.oracleGeneral.zst|log1p|LOH_FEATURE_LOG1P=1 LOH_FEATURE_LOG1P_RECIPROCAL=0"
  "wiki|data/WikiCDN/wiki_2019t.oracleGeneral.zst|reciprocal|LOH_FEATURE_LOG1P=0 LOH_FEATURE_LOG1P_RECIPROCAL=1"
  "meta|data/MetaCDN/meta_reag.oracleGeneral.zst|log1p|LOH_FEATURE_LOG1P=1 LOH_FEATURE_LOG1P_RECIPROCAL=0"
)

MODES=(
  "baseline|LOH_ENABLE_FEATURE_NORMALIZATION=0 LOH_ENABLE_ADAPTIVE_FEATURE_NORMALIZATION=0"
  "fixed_norm|LOH_ENABLE_FEATURE_NORMALIZATION=1 LOH_ENABLE_ADAPTIVE_FEATURE_NORMALIZATION=0"
  "adaptive_norm|LOH_ENABLE_FEATURE_NORMALIZATION=0 LOH_ENABLE_ADAPTIVE_FEATURE_NORMALIZATION=1 LOH_ADAPTIVE_NORM_LO_Q=0.01 LOH_ADAPTIVE_NORM_HI_Q=0.99 LOH_ADAPTIVE_NORM_WARMUP=4096"
)

run_one() {
  local trace_name="$1"
  local trace_path="$2"
  local formula_name="$3"
  local formula_envs="$4"
  local mode_name="$5"
  local mode_envs="$6"
  local case_name="${trace_name}_${formula_name}_${mode_name}"
  local log_path="$OUT_DIR/${case_name}.log"
  local shm_key
  shm_key=$(printf "%s|sec20m|0314" "$case_name" | cksum | awk '{print $1}')

  rm -f "/dev/shm/loh_ac_${shm_key}" || true
  rm -f "/dev/shm/sem.loh_ac_ready_${shm_key}" || true
  rm -f "/dev/shm/sem.loh_ac_ack_${shm_key}" || true

  {
    echo "===== ${case_name} ====="
    echo "trace=${trace_path}"
    echo "shm_key=${shm_key}"
    echo
  } | tee "$log_path"

  (
    set -euo pipefail
    export LOH_SHM_KEY="$shm_key"
    for kv in "${COMMON_ENV[@]}"; do export "$kv"; done
    for kv in $formula_envs; do export "$kv"; done
    for kv in $mode_envs; do export "$kv"; done
    bash scripts/test_loh_rl_sb3.sh "$trace_path" 0.1
  ) >> "$log_path" 2>&1

  local mr=""
  local bmr=""
  mr=$(grep -E '^\[RESULT\] Obj Miss Ratio:' "$log_path" | tail -n 1 | awk '{print $5}')
  bmr=$(grep -E '^\[RESULT\] Byte Miss Ratio:' "$log_path" | tail -n 1 | awk '{print $5}')
  echo "${trace_name},${formula_name},${mode_name},${mr},${bmr},${log_path}" >> "$RESULTS_CSV"
  echo "[done] ${case_name} mr=${mr} bmr=${bmr}" | tee -a "$RUNNER_LOG"
}

echo "[start] sec20 matrix run" | tee "$RUNNER_LOG"
for case_def in "${CASES[@]}"; do
  IFS='|' read -r trace_name trace_path formula_name formula_envs <<< "$case_def"
  for mode_def in "${MODES[@]}"; do
    IFS='|' read -r mode_name mode_envs <<< "$mode_def"
    run_one "$trace_name" "$trace_path" "$formula_name" "$formula_envs" "$mode_name" "$mode_envs"
  done
done

echo "[finished] results at ${RESULTS_CSV}" | tee -a "$RUNNER_LOG"
