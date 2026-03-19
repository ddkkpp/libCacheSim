#!/usr/bin/env bash
set -u

ROOT_DIR=$(cd "$(dirname "$0")/../.." && pwd)
cd "$ROOT_DIR"

OUT_DIR="tmp/hitmiss_lo00_hi100_full_0316"
RESULTS_CSV="$OUT_DIR/results.csv"
RUNNER_LOG="$OUT_DIR/runner.log"
DOC_PATH="docs/20260317-FULL_EXPERIMENT_RESULTS.md"
PARALLEL=3
CACHE_SIZE=0.1

mkdir -p "$OUT_DIR"

# Build once with hit/miss state enabled (compile-time macro), then reuse release binary.
LOH_INCLUDE_HIT_MISS_FEATURES=1 LOH_BUILD_RELEASE=1 bash scripts/debug.sh -r -c >> "$OUT_DIR/prebuild_rel_hitmiss.log" 2>&1

echo "[start] hitmiss+lo00_hi100 fullreq parallel=${PARALLEL}" >> "$RUNNER_LOG"

if [ ! -f "$RESULTS_CSV" ]; then
cat > "$RESULTS_CSV" <<'CSV'
trace,status,rc,final_mr,final_bmr,final_mqps,log_path
CSV
fi

COMMON_ENV=(
  "CACHESIM_NUM_REQ=0"
  "LOH_PARALLEL_SAFE=1"
  "LOH_BUILD_RELEASE=1"
  "LOH_SKIP_BUILD=1"
  "LOH_SKIP_PIP_INSTALL=1"
  "LOH_ENABLE_SEMAPHORE=1"
  "LOH_ENABLE_RL=1"
  "LOH_SCORE_USE_COMPOUND=1"
  "LOH_SCORE_USE_IRT=0"
  "LOH_FEATURE_LOG1P=1"
  "LOH_FEATURE_LOG1P_RECIPROCAL=0"
  "LOH_RANDOM_CANDIDATES=96"
  "LOH_STRUCTURED_CANDIDATES=96"
  "LOH_WAIT_MODE=nonblocked"
  "LOH_ASYNC_TRAIN=1"
  "LOH_MISS_RATIO_WEIGHT=1.0"
  "LOH_INCLUDE_WEIGHTS_IN_OBS=1"
  "LOH_ADAPTIVE_BUDGET=1"
  "LOH_USE_SCORE_REBALANCE=0"
  "LOH_ENABLE_FEATURE_NORMALIZATION=0"
  "LOH_ENABLE_ADAPTIVE_FEATURE_NORMALIZATION=1"
  "LOH_ADAPTIVE_NORM_LO_Q=0.0"
  "LOH_ADAPTIVE_NORM_HI_Q=1.0"
  "LOH_ADAPTIVE_NORM_WARMUP=0"
  "LOH_INCLUDE_HIT_MISS_FEATURES=1"
  "CACHESIM_VERBOSE=0"
)

TRACES=(
  "1063|data/TencentCBS/1063.oracleGeneral.zst"
  "wiki|data/WikiCDN/wiki_2019t.oracleGeneral.zst"
  "meta|data/MetaCDN/meta_reag.oracleGeneral.zst"
)

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
  local trace_name="$1"
  local trace_path="$2"
  local case_name="${trace_name}_hitmiss_lo00_hi100"
  local log_path="$OUT_DIR/${case_name}.log"
  local shm_key rc=0

  shm_key=$(printf "%s|%s" "$trace_name" "$(date +%s%N)" | cksum | awk '{print $1}')
  rm -f "/dev/shm/loh_ac_${shm_key}" "/dev/shm/sem.loh_ac_ready_${shm_key}" "/dev/shm/sem.loh_ac_ack_${shm_key}" || true

  echo "[case-start] ${case_name}" >> "$RUNNER_LOG"
  (
    export LOH_SHM_KEY="$shm_key"
    export RUN_TIMESTAMP="$(date +%m%d_%H%M%S)_${case_name}_$$"
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

  echo "${trace_name},${status},${rc},${fmr},${fbmr},${fmqps},${log_path}" >> "$RESULTS_CSV"
  echo "[case-done] ${case_name} status=${status} rc=${rc} final_mr=${fmr} final_bmr=${fbmr} final_mqps=${fmqps}" >> "$RUNNER_LOG"
  update_doc_section
}

running=0
for t in "${TRACES[@]}"; do
  IFS='|' read -r trace_name trace_path <<< "$t"
  while [ "$running" -ge "$PARALLEL" ]; do
    wait -n || true
    running=$((running - 1))
    echo "[queue] active=${running}/${PARALLEL} action=finish_one" >> "$RUNNER_LOG"
  done
  run_one "$trace_name" "$trace_path" &
  running=$((running + 1))
  echo "[queue] active=${running}/${PARALLEL} action=start case=${trace_name}_hitmiss_lo00_hi100" >> "$RUNNER_LOG"
done

while [ "$running" -gt 0 ]; do
  wait -n || true
  running=$((running - 1))
  echo "[queue] active=${running}/${PARALLEL} action=finish_one" >> "$RUNNER_LOG"
done

echo "[finished] ${RESULTS_CSV}" >> "$RUNNER_LOG"
