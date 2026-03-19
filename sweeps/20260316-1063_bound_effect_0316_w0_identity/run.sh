#!/usr/bin/env bash
set -u

ROOT_DIR=$(cd "$(dirname "$0")/../.." && pwd)
cd "$ROOT_DIR"

OUT_DIR="tmp/1063_bound_effect_0316_w0_identity"
RESULTS_CSV="$OUT_DIR/results.csv"
RUNNER_LOG="$OUT_DIR/runner.log"
DOC_PATH="docs/20260317-FULL_EXPERIMENT_RESULTS.md"
PARALLEL=8
TRACE_NAME="1063"
TRACE_PATH="data/TencentCBS/1063.oracleGeneral.zst"
CACHE_SIZE=0.1

mkdir -p "$OUT_DIR"

# 先固定为 hit/miss features 关闭，确保本批次维度一致。
echo "[prebuild] force hitmiss=0 debug" | tee -a "$RUNNER_LOG"
LOH_INCLUDE_HIT_MISS_FEATURES=0 bash scripts/debug.sh -c >> "$OUT_DIR/prebuild_dbg.log" 2>&1

echo "[prebuild] force hitmiss=0 release" | tee -a "$RUNNER_LOG"
LOH_INCLUDE_HIT_MISS_FEATURES=0 bash scripts/debug.sh -r -c >> "$OUT_DIR/prebuild_rel.log" 2>&1

if [ ! -f "$RESULTS_CSV" ]; then
cat > "$RESULTS_CSV" <<'CSV'
trace,config,identity,status,rc,mr24,imr24,mr48,imr48,mr72,imr72,mr96,imr96,final_mr,final_bmr,final_mqps,log_path
CSV
fi

echo "[start] 1063 quantile bound effect identity sweep (parallel=${PARALLEL}, warmup=0, hitmiss=0)" >> "$RUNNER_LOG"

COMMON_ENV=(
  "CACHESIM_NUM_REQ=0"
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
  "LOH_MISS_RATIO_WEIGHT=1.0"
  "LOH_INCLUDE_WEIGHTS_IN_OBS=1"
  "LOH_ADAPTIVE_BUDGET=1"
  "LOH_USE_SCORE_REBALANCE=0"
  "LOH_FEATURE_UNIFIED_FORMULA=0"
  "LOH_FEATURE_LOG1P=1"
  "LOH_FEATURE_LOG1P_RECIPROCAL=0"
  "LOH_ENABLE_FEATURE_NORMALIZATION=0"
  "LOH_ENABLE_ADAPTIVE_FEATURE_NORMALIZATION=1"
  "LOH_ADAPTIVE_NORM_WARMUP=0"
  "LOH_INCLUDE_HIT_MISS_FEATURES=0"
)

TASKS=(
  "lo01_hi0995|LOH_ADAPTIVE_NORM_LO_Q=0.01 LOH_ADAPTIVE_NORM_HI_Q=0.995"
  "lo05_hi099|LOH_ADAPTIVE_NORM_LO_Q=0.05 LOH_ADAPTIVE_NORM_HI_Q=0.99"
  "lo01_hi099|LOH_ADAPTIVE_NORM_LO_Q=0.01 LOH_ADAPTIVE_NORM_HI_Q=0.99"
  "lo005_hi099|LOH_ADAPTIVE_NORM_LO_Q=0.005 LOH_ADAPTIVE_NORM_HI_Q=0.99"
  "lo01_hi095|LOH_ADAPTIVE_NORM_LO_Q=0.01 LOH_ADAPTIVE_NORM_HI_Q=0.95"
  "lo00_hi100|LOH_ADAPTIVE_NORM_LO_Q=0.0 LOH_ADAPTIVE_NORM_HI_Q=1.0"
  "lo01_hi100|LOH_ADAPTIVE_NORM_LO_Q=0.01 LOH_ADAPTIVE_NORM_HI_Q=1.0"
  "lo00_hi099|LOH_ADAPTIVE_NORM_LO_Q=0.0 LOH_ADAPTIVE_NORM_HI_Q=0.99"
)

extract_pair() {
  local log_path="$1"
  local hour="$2"
  awk -v h="$hour" '
    $0 ~ "LOH-OMR " h "\\.00 hour" {
      mr=""; imr="";
      if (match($0, /miss ratio [0-9]+\.[0-9]+/)) mr = substr($0, RSTART + 11, RLENGTH - 11);
      if (match($0, /interval miss ratio [0-9]+\.[0-9]+/)) imr = substr($0, RSTART + 20, RLENGTH - 20);
      if (mr != "" && imr != "") { print mr "," imr; exit; }
    }
  ' "$log_path"
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

update_doc_section() {
  if [ -f "$OUT_DIR/update_doc_section.py" ]; then
    (
      flock 9
      python3 "$OUT_DIR/update_doc_section.py" "$RESULTS_CSV" "$DOC_PATH" >> "$OUT_DIR/doc_update.log" 2>&1 || true
    ) 9>"$OUT_DIR/doc_update.lock"
  fi
}

run_one() {
  local cfg_name="$1"
  local extra_envs="$2"
  local identity="$3"
  local case_name="${TRACE_NAME}_${cfg_name}_id${identity}"
  local log_path="$OUT_DIR/${case_name}.log"
  local shm_key

  shm_key=$(printf "%s|%s|%s|%s" "$TRACE_NAME" "$cfg_name" "$identity" "$(date +%s%N)" | cksum | awk '{print $1}')
  rm -f "/dev/shm/loh_ac_${shm_key}" "/dev/shm/sem.loh_ac_ready_${shm_key}" "/dev/shm/sem.loh_ac_ack_${shm_key}" || true

  echo "[case-start] ${case_name}" >> "$RUNNER_LOG"

  local rc=0
  (
    export LOH_SHM_KEY="$shm_key"
    export RUN_TIMESTAMP="$(date +%m%d_%H%M%S)_${case_name}_$$"
    for kv in "${COMMON_ENV[@]}"; do export "$kv"; done
    for kv in $extra_envs; do export "$kv"; done
    export LOH_FEATURE_IDENTITY="$identity"
    bash scripts/test_loh_rl_sb3.sh "$TRACE_PATH" "$CACHE_SIZE"
  ) > "$log_path" 2>&1 || rc=$?

  local p24 p48 p72 p96 fin
  local mr24="NA" imr24="NA" mr48="NA" imr48="NA" mr72="NA" imr72="NA" mr96="NA" imr96="NA" fmr="NA" fbmr="NA" fmqps="NA"

  p24=$(extract_pair "$log_path" 24 || true)
  p48=$(extract_pair "$log_path" 48 || true)
  p72=$(extract_pair "$log_path" 72 || true)
  p96=$(extract_pair "$log_path" 96 || true)
  fin=$(extract_final "$log_path" || true)

  [ -n "$p24" ] && mr24="${p24%,*}" && imr24="${p24#*,}"
  [ -n "$p48" ] && mr48="${p48%,*}" && imr48="${p48#*,}"
  [ -n "$p72" ] && mr72="${p72%,*}" && imr72="${p72#*,}"
  [ -n "$p96" ] && mr96="${p96%,*}" && imr96="${p96#*,}"
  if [ -n "$fin" ]; then
    fmr="$(echo "$fin" | cut -d',' -f1)"
    fbmr="$(echo "$fin" | cut -d',' -f2)"
    fmqps="$(echo "$fin" | cut -d',' -f3)"
  fi

  local status="ok"
  [ "$rc" -ne 0 ] && status="failed"

  echo "${TRACE_NAME},${cfg_name},${identity},${status},${rc},${mr24},${imr24},${mr48},${imr48},${mr72},${imr72},${mr96},${imr96},${fmr},${fbmr},${fmqps},${log_path}" >> "$RESULTS_CSV"
  echo "[case-done] ${case_name} status=${status} rc=${rc} final_mr=${fmr} final_bmr=${fbmr} final_mqps=${fmqps}" >> "$RUNNER_LOG"
  update_doc_section
}

running=0
for c in "${TASKS[@]}"; do
  IFS='|' read -r cfg_name extra_envs <<< "$c"
  for identity in 0 1; do
    run_one "$cfg_name" "$extra_envs" "$identity" &
    running=$((running + 1))
    echo "[queue] active=${running}/${PARALLEL} action=start case=${TRACE_NAME}_${cfg_name}_id${identity}" >> "$RUNNER_LOG"
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
