#!/usr/bin/env bash
set -u

ROOT_DIR=$(cd "$(dirname "$0")/../.." && pwd)
cd "$ROOT_DIR"

OUT_DIR="tmp/log1p_adaptive_tune_0316"
RESULTS_CSV="$OUT_DIR/results.csv"
RUNNER_LOG="$OUT_DIR/runner.log"
OLD_RUNNER_LOG="tmp/unified_three_cfg_0316/runner.log"
DOC_PATH="docs/20260317-FULL_EXPERIMENT_RESULTS.md"
PARALLEL=6
CACHE_SIZE=0.1
NUM_REQ=0

mkdir -p "$OUT_DIR"

# Build once, then reuse release binary for all cases.
echo "[prebuild] build debug" | tee -a "$RUNNER_LOG"
bash scripts/debug.sh -c >> "$OUT_DIR/prebuild_dbg.log" 2>&1
echo "[prebuild] build release" | tee -a "$RUNNER_LOG"
bash scripts/debug.sh -r -c >> "$OUT_DIR/prebuild_rel.log" 2>&1

if [ ! -f "$RESULTS_CSV" ]; then
cat > "$RESULTS_CSV" <<'CSV'
trace,config,status,rc,mr24,imr24,mr48,imr48,mr72,imr72,mr96,imr96,final_mr,final_bmr,final_mqps,log_path
CSV
fi

echo "[start] log1p adaptive tune (q-range + warmup, parallel=${PARALLEL})" >> "$RUNNER_LOG"

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
  "LOH_FEATURE_UNIFIED_FORMULA=0"
  "LOH_FEATURE_LOG1P=1"
  "LOH_FEATURE_LOG1P_RECIPROCAL=0"
  "LOH_ENABLE_FEATURE_NORMALIZATION=0"
  "LOH_ENABLE_ADAPTIVE_FEATURE_NORMALIZATION=1"
)

TRACES=(
  "meta|data/MetaCDN/meta_reag.oracleGeneral.zst"
  "1063|data/TencentCBS/1063.oracleGeneral.zst"
  "wiki|data/WikiCDN/wiki_2019t.oracleGeneral.zst"
)

TASKS=(
  "adapt_q05_q95_w16384|LOH_ADAPTIVE_NORM_LO_Q=0.05 LOH_ADAPTIVE_NORM_HI_Q=0.95 LOH_ADAPTIVE_NORM_WARMUP=16384"
  "adapt_q05_q95_w32768|LOH_ADAPTIVE_NORM_LO_Q=0.05 LOH_ADAPTIVE_NORM_HI_Q=0.95 LOH_ADAPTIVE_NORM_WARMUP=32768"
  "adapt_q10_q90_w16384|LOH_ADAPTIVE_NORM_LO_Q=0.10 LOH_ADAPTIVE_NORM_HI_Q=0.90 LOH_ADAPTIVE_NORM_WARMUP=16384"
  "adapt_q10_q90_w32768|LOH_ADAPTIVE_NORM_LO_Q=0.10 LOH_ADAPTIVE_NORM_HI_Q=0.90 LOH_ADAPTIVE_NORM_WARMUP=32768"
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
  awk -F',' -v t="$trace_name" -v c="$cfg_name" 'NR>1 && $1==t && $2==c && $3=="ok" {found=1} END{exit found?0:1}' "$RESULTS_CSV"
}

update_doc_section() {
  if [ -f "$OUT_DIR/update_doc_section.py" ]; then
    (
      flock 9
      python3 "$OUT_DIR/update_doc_section.py" "$RESULTS_CSV" "$DOC_PATH" >> "$OUT_DIR/doc_update.log" 2>&1 || true
    ) 9>"$OUT_DIR/doc_update.lock"
  fi
}

get_old_active() {
  local old_count line active
  old_count=$(ps -eo pid=,args= | awk '$1 ~ /^[0-9]+$/ && $2=="bash" && $3=="tmp/unified_three_cfg_0316/run.sh" {c++} END{print c+0}')
  if [ "${old_count}" -eq 0 ]; then
    echo 0
    return
  fi
  if [ ! -f "$OLD_RUNNER_LOG" ]; then
    echo 0
    return
  fi
  line=$(grep -E "\\[queue\\] active=[0-9]+/6" "$OLD_RUNNER_LOG" | tail -n 1 || true)
  active=$(printf "%s" "$line" | sed -nE 's/.*active=([0-9]+)\/6.*/\1/p')
  [ -z "$active" ] && active=0
  echo "$active"
}

run_one() {
  local trace_name="$1"
  local trace_path="$2"
  local cfg_name="$3"
  local extra_envs="$4"

  local case_name="${trace_name}_${cfg_name}"
  local log_path="$OUT_DIR/${case_name}.log"
  local shm_key
  shm_key=$(printf "%s|%s|%s" "$trace_name" "$cfg_name" "$(date +%s%N)" | cksum | awk '{print $1}')

  rm -f "/dev/shm/loh_ac_${shm_key}" "/dev/shm/sem.loh_ac_ready_${shm_key}" "/dev/shm/sem.loh_ac_ack_${shm_key}" || true

  echo "[case-start] ${case_name}" >> "$RUNNER_LOG"
  {
    echo "===== ${case_name} ====="
    echo "trace=${trace_path}"
    echo "shm_key=${shm_key}"
    echo "extra_envs=${extra_envs}"
    echo
  } > "$log_path"

  local rc=0
  (
    export LOH_SHM_KEY="$shm_key"
    export RUN_TIMESTAMP="$(date +%m%d_%H%M%S)_${case_name}_$$"
    for kv in "${COMMON_ENV[@]}"; do export "$kv"; done
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

  echo "${trace_name},${cfg_name},${status},${rc},${mr24},${imr24},${mr48},${imr48},${mr72},${imr72},${mr96},${imr96},${fmr},${fbmr},${fmqps},${log_path}" >> "$RESULTS_CSV"
  echo "[case-done] ${case_name} status=${status} rc=${rc} final_mr=${fmr} final_bmr=${fbmr} final_mqps=${fmqps}" >> "$RUNNER_LOG"
  update_doc_section
}

running_jobs=0
start_case() {
  local trace_name="$1"; local trace_path="$2"; local cfg_name="$3"; local extra_envs="$4"
  run_one "$trace_name" "$trace_path" "$cfg_name" "$extra_envs" &
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
    IFS='|' read -r cfg_name extra_envs <<< "$c"
    if is_done "$trace_name" "$cfg_name"; then
      echo "[skip-done] ${trace_name}_${cfg_name}" >> "$RUNNER_LOG"
      continue
    fi
    while :; do
      old_active=$(get_old_active)
      total_active=$((running_jobs + old_active))
      if [ "$running_jobs" -lt "$PARALLEL" ] && [ "$total_active" -lt 6 ]; then
        break
      fi
      if [ "$running_jobs" -gt 0 ]; then
        wait_one
      else
        echo "[queue] waiting_for_slot old_active=${old_active} new_active=${running_jobs} total=${total_active}/6" >> "$RUNNER_LOG"
        sleep 5
      fi
    done
    start_case "$trace_name" "$trace_path" "$cfg_name" "$extra_envs"
  done
done

while [ "$running_jobs" -gt 0 ]; do
  wait_one
done

echo "[finished] ${RESULTS_CSV}" >> "$RUNNER_LOG"
