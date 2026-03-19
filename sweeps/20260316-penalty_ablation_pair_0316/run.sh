#!/usr/bin/env bash
set -u

ROOT_DIR=$(cd "$(dirname "$0")/../.." && pwd)
cd "$ROOT_DIR"

OUT_DIR="tmp/penalty_ablation_pair_0316"
RESULTS_CSV="$OUT_DIR/results.csv"
RUNNER_LOG="$OUT_DIR/runner.log"
DOC_PATH="docs/20260317-FULL_EXPERIMENT_RESULTS.md"
TRACE_PATH="data/TencentCBS/1063.oracleGeneral.zst"
CACHE_SIZE="0.1"

mkdir -p "$OUT_DIR"

echo "[start] no-penalty pair (LOG1P vs LOG1P+blocked)" >> "$RUNNER_LOG"

cat > "$RESULTS_CSV" <<'CSV'
variant,wait_mode,status,rc,mr,bmr,mqps,log_path
CSV

update_doc_section() {
  (
    flock 9
    python3 "$OUT_DIR/update_doc_section.py" "$RESULTS_CSV" "$DOC_PATH" >> "$OUT_DIR/doc_update.log" 2>&1 || true
  ) 9>"$OUT_DIR/doc_update.lock"
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

run_one() {
  local variant="$1"
  local wait_mode="$2"
  local case_name="${variant}"
  local log_path="$OUT_DIR/${case_name}.log"
  local rc=0
  local shm_key

  shm_key=$(printf "%s|%s" "$case_name" "$(date +%s%N)" | cksum | awk '{print $1}')
  rm -f "/dev/shm/loh_ac_${shm_key}" "/dev/shm/sem.loh_ac_ready_${shm_key}" "/dev/shm/sem.loh_ac_ack_${shm_key}" || true

  echo "[case-start] ${case_name}" >> "$RUNNER_LOG"

  (
    export LOH_SHM_KEY="$shm_key"
    export RUN_TIMESTAMP="$(date +%m%d_%H%M%S)_${case_name}_$$"
    export LOH_PARALLEL_SAFE=1
    export LOH_BUILD_RELEASE=1
    export LOH_SKIP_BUILD=1
    export LOH_SKIP_PIP_INSTALL=1
    export CACHESIM_NUM_REQ=3000000
    export LOH_ENABLE_RL=1
    export LOH_ENABLE_SEMAPHORE=1
    export LOH_SCORE_USE_COMPOUND=1
    export LOH_SCORE_USE_IRT=0
    export LOH_FEATURE_LOG1P=1
    export LOH_FEATURE_LOG1P_RECIPROCAL=0
    # Unified formula forces reciprocal mode in LOH.c; disable it so LOG1P flags are honored.
    export LOH_FEATURE_UNIFIED_FORMULA=0
    unset LOH_UNIFIED_VARIANT LOH_UNIFIED_BETA LOH_UNIFIED_GAMMA LOH_UNIFIED_METHOD LOH_UNIFIED_ALPHA LOH_UNIFIED_FREQ_CAP
    export LOH_DUAL_CHANNEL=0
    export LOH_RANDOM_CANDIDATES=96
    export LOH_STRUCTURED_CANDIDATES=96
    export LOH_MISS_RATIO_WEIGHT=1.0
    export LOH_INCLUDE_HIT_MISS_FEATURES=0
    export LOH_ENABLE_PENALTY=0
    export LOH_WAIT_MODE="$wait_mode"
    export CACHESIM_VERBOSE=0
    bash scripts/test_loh_rl_sb3.sh "$TRACE_PATH" "$CACHE_SIZE"
  ) > "$log_path" 2>&1 || rc=$?

  local status="ok" mr="NA" bmr="NA" mqps="NA" fin
  fin=$(extract_final "$log_path" || true)
  if [ -n "$fin" ]; then
    mr="$(echo "$fin" | cut -d',' -f1)"
    bmr="$(echo "$fin" | cut -d',' -f2)"
    mqps="$(echo "$fin" | cut -d',' -f3)"
  fi
  [ "$rc" -ne 0 ] && status="failed"

  echo "${variant},${wait_mode},${status},${rc},${mr},${bmr},${mqps},${log_path}" >> "$RESULTS_CSV"
  echo "[case-done] ${case_name} status=${status} rc=${rc} mr=${mr} bmr=${bmr} mqps=${mqps}" >> "$RUNNER_LOG"
  update_doc_section
}

# Ensure a fresh release build with hitmiss disabled before pair run.
LOH_INCLUDE_HIT_MISS_FEATURES=0 LOH_BUILD_RELEASE=1 bash scripts/debug.sh -r -c >> "$OUT_DIR/prebuild_rel_no_hitmiss.log" 2>&1

run_one "log1p" "nonblocked"
run_one "log1p_blocked" "blocked"

echo "[finished] ${RESULTS_CSV}" >> "$RUNNER_LOG"
