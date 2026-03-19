#!/usr/bin/env bash
set -u

ROOT_DIR=$(cd "$(dirname "$0")/../.." && pwd)
cd "$ROOT_DIR"

OUT_DIR="tmp/rl_algo_followup_ppolstm_tqc_orig3_cache01_0318"
RESULTS_CSV="$OUT_DIR/results.csv"
RUNNER_LOG="$OUT_DIR/runner.log"
PARALLEL="${PARALLEL:-3}"
CACHE_SIZE="0.1"

mkdir -p "$OUT_DIR"

if [ ! -f "$RESULTS_CSV" ]; then
cat > "$RESULTS_CSV" <<'CSV'
algo,exclude_recent_steps,exclude_applied,trace,status,rc,final_mr,final_bmr,final_mqps,log_path
CSV
fi

echo "[start] follow-up PPO_LSTM + TQC sweep on orig3 cache=0.1" >> "$RUNNER_LOG"

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
  "LOH_ADAPTIVE_NORM_TRANSFORM_QUANTILE=0"
  "LOH_INCLUDE_HIT_MISS_FEATURES=0"
)

ALGOS_WITH_EXCLUDE=("TQC")
ALGOS_NO_EXCLUDE=("PPO_LSTM")
EXCLUDES=("0" "2000" "10000")
TASKS=(
  "1063|data/TencentCBS/1063.oracleGeneral.zst"
  "wiki|data/WikiCDN/wiki_2019t.oracleGeneral.zst"
  "meta|data/MetaCDN/meta_reag.oracleGeneral.zst"
)

extract_final() {
  local log_path="$1"
  awk '
    /LOH-(OMR|BMR) cache size/ {
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
  local algo="$1"
  local exclude_recent_steps="$2"
  local exclude_applied="$3"
  local trace_name="$4"
  grep -q "^${algo},${exclude_recent_steps},${exclude_applied},${trace_name},ok," "$RESULTS_CSV"
}

run_one() {
  local algo="$1"
  local exclude_recent_steps="$2"
  local exclude_applied="$3"
  local trace_name="$4"
  local trace_path="$5"

  if already_done "$algo" "$exclude_recent_steps" "$exclude_applied" "$trace_name"; then
    echo "[resume-skip] algo=${algo} exclude=${exclude_recent_steps} trace=${trace_name} already done" >> "$RUNNER_LOG"
    return 0
  fi

  local case_name="${trace_name}_${algo}_ex${exclude_recent_steps}_cache01"
  local case_stamp
  case_stamp="$(date +%m%d_%H%M%S)"
  local log_path="$OUT_DIR/${case_name}_${case_stamp}.log"
  local shm_key rc=0

  shm_key=$(printf "%s|%s|%s|%s|%s" "$trace_name" "$algo" "$exclude_recent_steps" "$CACHE_SIZE" "$(date +%s%N)" | cksum | awk '{print $1}')
  rm -f "/dev/shm/loh_ac_${shm_key}" "/dev/shm/sem.loh_ac_ready_${shm_key}" "/dev/shm/sem.loh_ac_ack_${shm_key}" || true

  echo "[case-start] algo=${algo} exclude=${exclude_recent_steps} trace=${trace_name}" >> "$RUNNER_LOG"
  (
    export LOH_SHM_KEY="$shm_key"
    export LOH_RL_ALGO="$algo"
    if [ "$exclude_applied" = "1" ]; then
      export LOH_EXCLUDE_RECENT_STEPS="$exclude_recent_steps"
    else
      unset LOH_EXCLUDE_RECENT_STEPS || true
    fi
    export RUN_TIMESTAMP="$(date +%m%d_%H%M%S)_${case_name}_$(date +%s)"
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

  echo "${algo},${exclude_recent_steps},${exclude_applied},${trace_name},${status},${rc},${fmr},${fbmr},${fmqps},${log_path}" >> "$RESULTS_CSV"
  echo "[case-done] algo=${algo} exclude=${exclude_recent_steps} trace=${trace_name} status=${status} rc=${rc} final_mr=${fmr} final_bmr=${fbmr} final_mqps=${fmqps}" >> "$RUNNER_LOG"
}

running=0
for algo in "${ALGOS_WITH_EXCLUDE[@]}"; do
  for ex in "${EXCLUDES[@]}"; do
    for t in "${TASKS[@]}"; do
      IFS='|' read -r trace_name trace_path <<< "$t"
      run_one "$algo" "$ex" "1" "$trace_name" "$trace_path" &
      running=$((running + 1))
      echo "[queue] active=${running}/${PARALLEL} action=start algo=${algo} exclude=${ex} trace=${trace_name}" >> "$RUNNER_LOG"
      if [ "$running" -ge "$PARALLEL" ]; then
        wait -n || true
        running=$((running - 1))
        echo "[queue] active=${running}/${PARALLEL} action=finish_one" >> "$RUNNER_LOG"
      fi
    done
  done
done

for algo in "${ALGOS_NO_EXCLUDE[@]}"; do
  for t in "${TASKS[@]}"; do
    IFS='|' read -r trace_name trace_path <<< "$t"
    run_one "$algo" "NA" "0" "$trace_name" "$trace_path" &
    running=$((running + 1))
    echo "[queue] active=${running}/${PARALLEL} action=start algo=${algo} exclude=NA trace=${trace_name}" >> "$RUNNER_LOG"
    if [ "$running" -ge "$PARALLEL" ]; then
      wait -n || true
      running=$((running - 1))
      echo "[queue] active=${running}/${PARALLEL} action=finish_one" >> "$RUNNER_LOG"
    fi
  done
done

while [ "$running" -gt 0 ]; do
  wait -n || true
  running=$((running - 1))
  echo "[queue] active=${running}/${PARALLEL} action=finish_one" >> "$RUNNER_LOG"
done

echo "[finished] ${RESULTS_CSV}" >> "$RUNNER_LOG"
