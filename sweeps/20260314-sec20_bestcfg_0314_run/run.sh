#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "$0")/../.." && pwd)
cd "$ROOT_DIR"

OUT_DIR="tmp/sec20_bestcfg_0314_run"
RESULTS_CSV="$OUT_DIR/results.csv"
RUNNER_LOG="$OUT_DIR/runner.log"

echo "trace,mr,bmr,log_path" > "$RESULTS_CSV"

run_one() {
  local trace_name="$1"
  local trace_path="$2"
  local formula_envs="$3"
  local shm_key
  shm_key=$(printf "%s|sec20|0314" "$trace_name" | cksum | awk '{print $1}')
  local log_path="$OUT_DIR/${trace_name}.log"

  rm -f "/dev/shm/loh_ac_${shm_key}" || true
  rm -f "/dev/shm/sem.loh_ac_ready_${shm_key}" || true
  rm -f "/dev/shm/sem.loh_ac_ack_${shm_key}" || true

  {
    echo "===== ${trace_name} ====="
    echo "trace=${trace_path}"
    echo "shm_key=${shm_key}"
    echo
  } | tee "$log_path"

  (
    set -euo pipefail
    export LOH_SHM_KEY="$shm_key"
    export CACHESIM_NUM_REQ=3000000

    # 20260317-FULL_EXPERIMENT_RESULTS.md §20
    export LOH_ENABLE_SEMAPHORE=1
    export LOH_BUILD_RELEASE=1
    export LOH_PERF_PROFILING=0
    export LOH_DEBUG_LEVEL=0
    export LOH_SCORE_USE_COMPOUND=1
    export LOH_SCORE_USE_IRT=0
    export LOH_RANDOM_CANDIDATES=96
    export LOH_STRUCTURED_CANDIDATES=96
    export LOH_WAIT_MODE=nonblocked
    export LOH_ASYNC_TRAIN=1
    export LOH_ENABLE_PENALTY=0
    export LOH_MISS_RATIO_WEIGHT=1.0
    export LOH_INCLUDE_WEIGHTS_IN_OBS=1
    export LOH_ADAPTIVE_BUDGET=1
    export LOH_USE_SCORE_REBALANCE=0

    # process/stability guard
    export LOH_ENABLE_RL=1
    export LOH_SKIP_BUILD=0
    export LOH_SKIP_PIP_INSTALL=1
    export LOH_DISABLE_NEWSTATE_EARLY_EXIT=1
    export LOH_WAIT_NEWSTATE_MAX_CONSEC_TIMEOUTS=1800
    export LOH_WAIT_NEWSTATE_IDLE_S=1800

    for kv in $formula_envs; do export "$kv"; done

    bash scripts/test_loh_rl_sb3.sh "$trace_path" 0.1
  ) >> "$log_path" 2>&1

  local mr=""
  local bmr=""
  mr=$(grep -E '^\[RESULT\] Obj Miss Ratio:' "$log_path" | tail -n 1 | awk '{print $5}')
  bmr=$(grep -E '^\[RESULT\] Byte Miss Ratio:' "$log_path" | tail -n 1 | awk '{print $5}')
  echo "${trace_name},${mr},${bmr},${log_path}" >> "$RESULTS_CSV"
  echo "[done] ${trace_name} mr=${mr} bmr=${bmr}" | tee -a "$RUNNER_LOG"
}

echo "[start] sec20 best config run" | tee "$RUNNER_LOG"
run_one "1063" "data/TencentCBS/1063.oracleGeneral.zst" "LOH_FEATURE_LOG1P=1 LOH_FEATURE_LOG1P_RECIPROCAL=0"
run_one "wiki" "data/WikiCDN/wiki_2019t.oracleGeneral.zst" "LOH_FEATURE_LOG1P=0 LOH_FEATURE_LOG1P_RECIPROCAL=1"
run_one "meta" "data/MetaCDN/meta_reag.oracleGeneral.zst" "LOH_FEATURE_LOG1P=1 LOH_FEATURE_LOG1P_RECIPROCAL=0"
echo "[finished] results at ${RESULTS_CSV}" | tee -a "$RUNNER_LOG"
