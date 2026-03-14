#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT_DIR"

STAMP=$(date +%m%d_%H%M%S)
OUT_DIR=${OUT_DIR:-"tmp/adaptive_feature_norm_${STAMP}"}
mkdir -p "$OUT_DIR"

NUM_REQ=${CACHESIM_NUM_REQ:-0}
CACHE_SIZE=${CACHE_SIZE:-0.1}

TRACE_NAMES=("1063" "wiki" "meta")
TRACE_PATHS=(
  "data/TencentCBS/1063.oracleGeneral.zst"
  "data/WikiCDN/wiki_2019t.oracleGeneral.zst"
  "data/MetaCDN/meta_reag.oracleGeneral.zst"
)
TRACE_FORMULAS=(
  "LOH_FEATURE_LOG1P=1 LOH_FEATURE_LOG1P_RECIPROCAL=0"
  "LOH_FEATURE_LOG1P=0 LOH_FEATURE_LOG1P_RECIPROCAL=1"
  "LOH_FEATURE_LOG1P=1 LOH_FEATURE_LOG1P_RECIPROCAL=0"
)

MODES=("baseline" "fixed_norm" "adaptive_norm")
MODE_ENVS=(
  "LOH_ENABLE_FEATURE_NORMALIZATION=0 LOH_ENABLE_ADAPTIVE_FEATURE_NORMALIZATION=0"
  "LOH_ENABLE_FEATURE_NORMALIZATION=1 LOH_ENABLE_ADAPTIVE_FEATURE_NORMALIZATION=0"
  "LOH_ENABLE_FEATURE_NORMALIZATION=0 LOH_ENABLE_ADAPTIVE_FEATURE_NORMALIZATION=1 LOH_ADAPTIVE_NORM_LO_Q=0.01 LOH_ADAPTIVE_NORM_HI_Q=0.99 LOH_ADAPTIVE_NORM_WARMUP=4096"
)

COMMON_ENV=${COMMON_ENV:-"LOH_BUILD_RELEASE=1 LOH_SKIP_BUILD=0 LOH_SKIP_PIP_INSTALL=1 LOH_DEBUG_LEVEL=0 LOH_PERF_PROFILING=0 LOH_ENABLE_SEMAPHORE=1 LOH_ENABLE_RL=1 LOH_INCLUDE_REQUEST=1 LOH_SCORE_USE_COMPOUND=0 LOH_SCORE_USE_IRT=1 LOH_INCLUDE_WEIGHTS_IN_OBS=1 LOH_DISABLE_NEWSTATE_EARLY_EXIT=1 LOH_WAIT_NEWSTATE_MAX_CONSEC_TIMEOUTS=1800 LOH_WAIT_NEWSTATE_IDLE_S=1800"}

RESULTS_CSV="$OUT_DIR/results.csv"
echo "trace,mode,mr,bmr,config,log_dir" > "$RESULTS_CSV"

run_one() {
  local trace_name="$1"
  local trace_path="$2"
  local formula_env="$3"
  local mode_name="$4"
  local mode_env="$5"
  local run_dir="$OUT_DIR/${trace_name}_${mode_name}"
  mkdir -p "$run_dir"

  local shm_key
  shm_key=$(printf "%s|%s|%s" "$trace_name" "$mode_name" "$STAMP" | cksum | awk '{print $1}')

  # 清理可能遗留的同 key 共享内存与信号量，避免读到旧状态。
  rm -f "/dev/shm/loh_ac_${shm_key}" || true
  rm -f "/dev/shm/sem.loh_ac_ready_${shm_key}" || true
  rm -f "/dev/shm/sem.loh_ac_ack_${shm_key}" || true

  {
    echo "export CACHESIM_NUM_REQ=${NUM_REQ}"
    echo "export LOH_SHM_KEY=${shm_key}"
    for token in $COMMON_ENV; do
      echo "export ${token}"
    done
    for token in $formula_env; do
      echo "export ${token}"
    done
    for token in $mode_env; do
      echo "export ${token}"
    done
  } > "$run_dir/env.sh"

  {
    echo "===== ${trace_name} / ${mode_name} ====="
    cat "$run_dir/env.sh"
    echo
    set -a
    source "$run_dir/env.sh"
    set +a
    bash scripts/test_loh_rl_sb3.sh "$trace_path" "$CACHE_SIZE"
  } | tee "$run_dir/run.log"

  local mr=""
  local bmr=""
  mr=$(grep -E "^\[RESULT\] Obj Miss Ratio:" "$run_dir/run.log" | tail -n 1 | awk '{print $5}')
  bmr=$(grep -E "^\[RESULT\] Byte Miss Ratio:" "$run_dir/run.log" | tail -n 1 | awk '{print $5}')
  echo "${trace_name},${mode_name},${mr},${bmr},${formula_env} ${mode_env},${run_dir}" >> "$RESULTS_CSV"
}

for i in "${!TRACE_NAMES[@]}"; do
  for j in "${!MODES[@]}"; do
    run_one "${TRACE_NAMES[$i]}" "${TRACE_PATHS[$i]}" "${TRACE_FORMULAS[$i]}" "${MODES[$j]}" "${MODE_ENVS[$j]}"
  done
done

echo "$OUT_DIR"
