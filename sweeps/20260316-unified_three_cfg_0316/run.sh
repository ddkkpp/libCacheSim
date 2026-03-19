#!/usr/bin/env bash
set -u

ROOT_DIR=$(cd "$(dirname "$0")/../.." && pwd)
cd "$ROOT_DIR"

OUT_DIR="tmp/unified_three_cfg_0316"
RESULTS_CSV="$OUT_DIR/results.csv"
RUNNER_LOG="$OUT_DIR/runner.log"
PARALLEL=6
CACHE_SIZE=0.1
NUM_REQ=0
DOC_PATH="docs/20260317-FULL_EXPERIMENT_RESULTS.md"

mkdir -p "$OUT_DIR"

# 先统一构建，避免并发 case 在 test_loh_rl_sb3.sh 内重复触发构建。
echo "[prebuild] build debug" | tee -a "$RUNNER_LOG"
bash scripts/debug.sh -c >> "$OUT_DIR/prebuild_dbg.log" 2>&1
echo "[prebuild] build release" | tee -a "$RUNNER_LOG"
bash scripts/debug.sh -r -c >> "$OUT_DIR/prebuild_rel.log" 2>&1

if [ ! -f "$RESULTS_CSV" ]; then
cat > "$RESULTS_CSV" <<'CSV'
trace,config,method,status,rc,mr24,imr24,mr48,imr48,mr72,imr72,mr96,imr96,final_mr,final_bmr,final_mqps,log_path
CSV
fi

echo "[start] unified cfg test (method4/5/6 + sec21 + sec23, parallel=${PARALLEL})" >> "$RUNNER_LOG"

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
  "LOH_MISS_RATIO_WEIGHT=1.0"
  "LOH_INCLUDE_WEIGHTS_IN_OBS=1"
  "LOH_ADAPTIVE_BUDGET=1"
  "LOH_USE_SCORE_REBALANCE=0"
)

TRACES=(
  "meta|data/MetaCDN/meta_reag.oracleGeneral.zst"
  "1063|data/TencentCBS/1063.oracleGeneral.zst"
  "wiki|data/WikiCDN/wiki_2019t.oracleGeneral.zst"
)

TASKS=(
  # New unified transform methods (user-requested three configs)
  "new_m4_cdf_like|4|LOH_FEATURE_UNIFIED_FORMULA=1 LOH_UNIFIED_VARIANT=1 LOH_UNIFIED_METHOD=4 LOH_UNIFIED_FREQ_CAP=4096 LOH_UNIFIED_BETA=0.7 LOH_UNIFIED_GAMMA=1.0 LOH_ENABLE_FEATURE_NORMALIZATION=0 LOH_ENABLE_ADAPTIVE_FEATURE_NORMALIZATION=0"
  "new_m5_tanh_robust|5|LOH_FEATURE_UNIFIED_FORMULA=1 LOH_UNIFIED_VARIANT=1 LOH_UNIFIED_METHOD=5 LOH_UNIFIED_FREQ_CAP=4096 LOH_UNIFIED_GAMMA=0.20 LOH_ENABLE_FEATURE_NORMALIZATION=0 LOH_ENABLE_ADAPTIVE_FEATURE_NORMALIZATION=0"
  "new_m6_qlog_gamma|6|LOH_FEATURE_UNIFIED_FORMULA=1 LOH_UNIFIED_VARIANT=1 LOH_UNIFIED_METHOD=6 LOH_UNIFIED_FREQ_CAP=4096 LOH_UNIFIED_GAMMA=0.80 LOH_ENABLE_FEATURE_NORMALIZATION=0 LOH_ENABLE_ADAPTIVE_FEATURE_NORMALIZATION=0"

  # Section 21 rerun matrix (6 modes)
  "sec21_log1p_baseline|-|LOH_FEATURE_UNIFIED_FORMULA=0 LOH_FEATURE_LOG1P=1 LOH_FEATURE_LOG1P_RECIPROCAL=0 LOH_ENABLE_FEATURE_NORMALIZATION=0 LOH_ENABLE_ADAPTIVE_FEATURE_NORMALIZATION=0"
  "sec21_log1p_fixed_norm|-|LOH_FEATURE_UNIFIED_FORMULA=0 LOH_FEATURE_LOG1P=1 LOH_FEATURE_LOG1P_RECIPROCAL=0 LOH_ENABLE_FEATURE_NORMALIZATION=1 LOH_ENABLE_ADAPTIVE_FEATURE_NORMALIZATION=0"
  "sec21_log1p_adaptive_norm|-|LOH_FEATURE_UNIFIED_FORMULA=0 LOH_FEATURE_LOG1P=1 LOH_FEATURE_LOG1P_RECIPROCAL=0 LOH_ENABLE_FEATURE_NORMALIZATION=0 LOH_ENABLE_ADAPTIVE_FEATURE_NORMALIZATION=1 LOH_ADAPTIVE_NORM_LO_Q=0.01 LOH_ADAPTIVE_NORM_HI_Q=0.99 LOH_ADAPTIVE_NORM_WARMUP=4096"
  "sec21_recip_baseline|-|LOH_FEATURE_UNIFIED_FORMULA=0 LOH_FEATURE_LOG1P=0 LOH_FEATURE_LOG1P_RECIPROCAL=1 LOH_ENABLE_FEATURE_NORMALIZATION=0 LOH_ENABLE_ADAPTIVE_FEATURE_NORMALIZATION=0"
  "sec21_recip_fixed_norm|-|LOH_FEATURE_UNIFIED_FORMULA=0 LOH_FEATURE_LOG1P=0 LOH_FEATURE_LOG1P_RECIPROCAL=1 LOH_ENABLE_FEATURE_NORMALIZATION=1 LOH_ENABLE_ADAPTIVE_FEATURE_NORMALIZATION=0"
  "sec21_recip_adaptive_norm|-|LOH_FEATURE_UNIFIED_FORMULA=0 LOH_FEATURE_LOG1P=0 LOH_FEATURE_LOG1P_RECIPROCAL=1 LOH_ENABLE_FEATURE_NORMALIZATION=0 LOH_ENABLE_ADAPTIVE_FEATURE_NORMALIZATION=1 LOH_ADAPTIVE_NORM_LO_Q=0.01 LOH_ADAPTIVE_NORM_HI_Q=0.99 LOH_ADAPTIVE_NORM_WARMUP=4096"

  # Section 23 rerun matrix (v1..v4 × 3 norm modes)
  "sec23_v1_baseline|1|LOH_FEATURE_UNIFIED_FORMULA=1 LOH_UNIFIED_VARIANT=1 LOH_UNIFIED_METHOD=1 LOH_ENABLE_FEATURE_NORMALIZATION=0 LOH_ENABLE_ADAPTIVE_FEATURE_NORMALIZATION=0"
  "sec23_v1_fixed_norm|1|LOH_FEATURE_UNIFIED_FORMULA=1 LOH_UNIFIED_VARIANT=1 LOH_UNIFIED_METHOD=1 LOH_ENABLE_FEATURE_NORMALIZATION=1 LOH_ENABLE_ADAPTIVE_FEATURE_NORMALIZATION=0"
  "sec23_v1_adaptive_norm|1|LOH_FEATURE_UNIFIED_FORMULA=1 LOH_UNIFIED_VARIANT=1 LOH_UNIFIED_METHOD=1 LOH_ENABLE_FEATURE_NORMALIZATION=0 LOH_ENABLE_ADAPTIVE_FEATURE_NORMALIZATION=1 LOH_ADAPTIVE_NORM_LO_Q=0.01 LOH_ADAPTIVE_NORM_HI_Q=0.99 LOH_ADAPTIVE_NORM_WARMUP=4096"
  "sec23_v2_baseline|1|LOH_FEATURE_UNIFIED_FORMULA=1 LOH_UNIFIED_VARIANT=2 LOH_UNIFIED_METHOD=1 LOH_UNIFIED_BETA=1.0 LOH_ENABLE_FEATURE_NORMALIZATION=0 LOH_ENABLE_ADAPTIVE_FEATURE_NORMALIZATION=0"
  "sec23_v2_fixed_norm|1|LOH_FEATURE_UNIFIED_FORMULA=1 LOH_UNIFIED_VARIANT=2 LOH_UNIFIED_METHOD=1 LOH_UNIFIED_BETA=1.0 LOH_ENABLE_FEATURE_NORMALIZATION=1 LOH_ENABLE_ADAPTIVE_FEATURE_NORMALIZATION=0"
  "sec23_v2_adaptive_norm|1|LOH_FEATURE_UNIFIED_FORMULA=1 LOH_UNIFIED_VARIANT=2 LOH_UNIFIED_METHOD=1 LOH_UNIFIED_BETA=1.0 LOH_ENABLE_FEATURE_NORMALIZATION=0 LOH_ENABLE_ADAPTIVE_FEATURE_NORMALIZATION=1 LOH_ADAPTIVE_NORM_LO_Q=0.01 LOH_ADAPTIVE_NORM_HI_Q=0.99 LOH_ADAPTIVE_NORM_WARMUP=4096"
  "sec23_v3_baseline|1|LOH_FEATURE_UNIFIED_FORMULA=1 LOH_UNIFIED_VARIANT=3 LOH_UNIFIED_METHOD=1 LOH_UNIFIED_BETA=1.0 LOH_ENABLE_FEATURE_NORMALIZATION=0 LOH_ENABLE_ADAPTIVE_FEATURE_NORMALIZATION=0"
  "sec23_v3_fixed_norm|1|LOH_FEATURE_UNIFIED_FORMULA=1 LOH_UNIFIED_VARIANT=3 LOH_UNIFIED_METHOD=1 LOH_UNIFIED_BETA=1.0 LOH_ENABLE_FEATURE_NORMALIZATION=1 LOH_ENABLE_ADAPTIVE_FEATURE_NORMALIZATION=0"
  "sec23_v3_adaptive_norm|1|LOH_FEATURE_UNIFIED_FORMULA=1 LOH_UNIFIED_VARIANT=3 LOH_UNIFIED_METHOD=1 LOH_UNIFIED_BETA=1.0 LOH_ENABLE_FEATURE_NORMALIZATION=0 LOH_ENABLE_ADAPTIVE_FEATURE_NORMALIZATION=1 LOH_ADAPTIVE_NORM_LO_Q=0.01 LOH_ADAPTIVE_NORM_HI_Q=0.99 LOH_ADAPTIVE_NORM_WARMUP=4096"
  "sec23_v4_baseline|1|LOH_FEATURE_UNIFIED_FORMULA=1 LOH_UNIFIED_VARIANT=4 LOH_UNIFIED_METHOD=1 LOH_UNIFIED_GAMMA=0.8 LOH_ENABLE_FEATURE_NORMALIZATION=0 LOH_ENABLE_ADAPTIVE_FEATURE_NORMALIZATION=0"
  "sec23_v4_fixed_norm|1|LOH_FEATURE_UNIFIED_FORMULA=1 LOH_UNIFIED_VARIANT=4 LOH_UNIFIED_METHOD=1 LOH_UNIFIED_GAMMA=0.8 LOH_ENABLE_FEATURE_NORMALIZATION=1 LOH_ENABLE_ADAPTIVE_FEATURE_NORMALIZATION=0"
  "sec23_v4_adaptive_norm|1|LOH_FEATURE_UNIFIED_FORMULA=1 LOH_UNIFIED_VARIANT=4 LOH_UNIFIED_METHOD=1 LOH_UNIFIED_GAMMA=0.8 LOH_ENABLE_FEATURE_NORMALIZATION=0 LOH_ENABLE_ADAPTIVE_FEATURE_NORMALIZATION=1 LOH_ADAPTIVE_NORM_LO_Q=0.01 LOH_ADAPTIVE_NORM_HI_Q=0.99 LOH_ADAPTIVE_NORM_WARMUP=4096"
)

extract_pair() {
  local log_path="$1"
  local hour="$2"
  awk -v h="$hour" '
    $0 ~ "LOH-OMR " h "\\.00 hour" {
      mr=""; imr="";
      if (match($0, /miss ratio [0-9]+\.[0-9]+/)) {
        mr = substr($0, RSTART + 11, RLENGTH - 11);
      }
      if (match($0, /interval miss ratio [0-9]+\.[0-9]+/)) {
        imr = substr($0, RSTART + 20, RLENGTH - 20);
      }
      if (mr != "" && imr != "") {
        printf "%s,%s\n", mr, imr;
        exit;
      }
    }
  ' "$log_path"
}

extract_final() {
  local log_path="$1"
  awk '
    /LOH-OMR cache size/ {
      mr=""; bmr=""; mqps="";
      if (match($0, /miss ratio [0-9]+\.[0-9]+/)) {
        mr = substr($0, RSTART + 11, RLENGTH - 11);
      }
      if (match($0, /byte miss ratio [0-9]+\.[0-9]+/)) {
        bmr = substr($0, RSTART + 16, RLENGTH - 16);
      }
      if (match($0, /throughput [0-9]+\.[0-9]+ MQPS/)) {
        mqps = substr($0, RSTART + 11, RLENGTH - 16);
      }
      if (mr != "" && bmr != "" && mqps != "") {
        last = mr "," bmr "," mqps;
      }
    }
    END { if (last != "") print last; }
  ' "$log_path"
}

is_done() {
  local trace_name="$1"
  local cfg_name="$2"
  awk -F',' -v t="$trace_name" -v c="$cfg_name" 'NR>1 && $1==t && $2==c && $4=="ok" {found=1} END{exit found?0:1}' "$RESULTS_CSV"
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
  local trace_name="$1"
  local trace_path="$2"
  local cfg_name="$3"
  local method="$4"
  local extra_envs="$5"

  local case_name="${trace_name}_${cfg_name}"
  local log_path="$OUT_DIR/${case_name}.log"
  local shm_key
  shm_key=$(printf "%s|%s|%s" "$trace_name" "$cfg_name" "$(date +%s%N)" | cksum | awk '{print $1}')

  rm -f "/dev/shm/loh_ac_${shm_key}" "/dev/shm/sem.loh_ac_ready_${shm_key}" "/dev/shm/sem.loh_ac_ack_${shm_key}" || true

  echo "[case-start] ${case_name}" >> "$RUNNER_LOG"
  {
    echo "===== ${case_name} ====="
    echo "trace=${trace_path}"
    echo "method=${method}"
    echo "shm_key=${shm_key}"
    echo
  } > "$log_path"

  local rc=0
  (
    export LOH_SHM_KEY="$shm_key"
    export RUN_TIMESTAMP="$(date +%m%d_%H%M%S)_${case_name}_$$"
    for kv in "${COMMON_ENV[@]}"; do export "$kv"; done
    if [ "$method" != "-" ]; then
      export LOH_UNIFIED_METHOD="$method"
    fi
    for kv in $extra_envs; do export "$kv"; done
    bash scripts/test_loh_rl_sb3.sh "$trace_path" "$CACHE_SIZE"
  ) >> "$log_path" 2>&1 || rc=$?

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

  echo "${trace_name},${cfg_name},${method},${status},${rc},${mr24},${imr24},${mr48},${imr48},${mr72},${imr72},${mr96},${imr96},${fmr},${fbmr},${fmqps},${log_path}" >> "$RESULTS_CSV"
  echo "[case-done] ${case_name} status=${status} rc=${rc} final_mr=${fmr} final_bmr=${fbmr} final_mqps=${fmqps}" >> "$RUNNER_LOG"
  update_doc_section
}

running_jobs=0
start_case() {
  local trace_name="$1"; local trace_path="$2"; local cfg_name="$3"; local method="$4"; local extra_envs="$5"
  run_one "$trace_name" "$trace_path" "$cfg_name" "$method" "$extra_envs" &
  running_jobs=$((running_jobs + 1))
  echo "[queue] active=${running_jobs}/${PARALLEL} action=start case=${trace_name}_${cfg_name}" >> "$RUNNER_LOG"
}
wait_one() {
  if [ "$running_jobs" -gt 0 ]; then
    wait -n || true
    running_jobs=$((running_jobs - 1))
    echo "[queue] active=${running_jobs}/${PARALLEL} action=finish_one" >> "$RUNNER_LOG"
  fi
}

for t in "${TRACES[@]}"; do
  IFS='|' read -r trace_name trace_path <<< "$t"
  for c in "${TASKS[@]}"; do
    IFS='|' read -r cfg_name method extra_envs <<< "$c"
    if is_done "$trace_name" "$cfg_name"; then
      echo "[skip-done] ${trace_name}_${cfg_name}" >> "$RUNNER_LOG"
      continue
    fi
    while [ "$running_jobs" -ge "$PARALLEL" ]; do
      wait_one
    done
    start_case "$trace_name" "$trace_path" "$cfg_name" "$method" "$extra_envs"
  done
done

while [ "$running_jobs" -gt 0 ]; do
  wait_one
done

echo "[finished] ${RESULTS_CSV}" >> "$RUNNER_LOG"
