#!/usr/bin/env bash
set -u

ROOT_DIR=$(cd "$(dirname "$0")/../.." && pwd)
cd "$ROOT_DIR"

OUT_DIR="tmp/transformq0_mrw_sweep_orig3_cache01_0318"
RESULTS_CSV="$OUT_DIR/results.csv"
RUNNER_LOG="$OUT_DIR/runner_rerun_na.log"
DOC_PATH="docs/20260317-FULL_EXPERIMENT_RESULTS.md"
PARALLEL="${PARALLEL:-3}"
CACHE_SIZE="0.1"

if [ ! -f "$RESULTS_CSV" ]; then
  echo "missing $RESULTS_CSV" >&2
  exit 1
fi

echo "[start] rerun NA cases for 27.13" >> "$RUNNER_LOG"

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

trace_path_of() {
  case "$1" in
    1063) echo "data/TencentCBS/1063.oracleGeneral.zst" ;;
    wiki) echo "data/WikiCDN/wiki_2019t.oracleGeneral.zst" ;;
    meta) echo "data/MetaCDN/meta_reag.oracleGeneral.zst" ;;
    *) echo "" ;;
  esac
}

extract_final() {
  local log_path="$1"
  awk '
    /LOH-.*cache size/ {
      mr=""; bmr=""; mqps="";
      if (match($0, /miss ratio [0-9]+\.[0-9]+/)) mr = substr($0, RSTART + 11, RLENGTH - 11);
      if (match($0, /byte miss ratio [0-9]+\.[0-9]+/)) bmr = substr($0, RSTART + 16, RLENGTH - 16);
      if (match($0, /throughput [0-9]+\.[0-9]+ MQPS/)) mqps = substr($0, RSTART + 11, RLENGTH - 16);
      if (mr != "" && bmr != "" && mqps != "") last = mr "," bmr "," mqps;
    }
    END { if (last != "") print last; }
  ' "$log_path"
}

update_csv_row() {
  local w="$1"
  local tr="$2"
  local fmr="$3"
  local fbmr="$4"
  local fmqps="$5"
  local logp="$6"

  awk -F, -v OFS=, -v w="$w" -v tr="$tr" -v fmr="$fmr" -v fbmr="$fbmr" -v fmqps="$fmqps" -v logp="$logp" '
    NR==1 {print; next}
    {
      if ($1==w && $2==tr) {
        $3="ok"; $4="0"; $5=fmr; $6=fbmr; $7=fmqps; $8=logp;
      }
      print
    }
  ' "$RESULTS_CSV" > "$RESULTS_CSV.tmp" && mv -f "$RESULTS_CSV.tmp" "$RESULTS_CSV"
}

run_one() {
  local w="$1"
  local tr="$2"

  local trace_path
  trace_path=$(trace_path_of "$tr")
  if [ -z "$trace_path" ]; then
    echo "[skip] unknown trace=$tr" >> "$RUNNER_LOG"
    return 0
  fi

  local w_tag
  w_tag=$(echo "$w" | tr '.' 'p')
  local case_name="${tr}_transformq0_mrw${w_tag}_cache01_rerun"
  local case_stamp
  case_stamp="$(date +%m%d_%H%M%S)"
  local log_path="$OUT_DIR/${case_name}_${case_stamp}.log"
  local shm_key rc=0

  shm_key=$(printf "%s|%s|%s|rerun|%s" "$tr" "$CACHE_SIZE" "$w" "$(date +%s%N)" | cksum | awk '{print $1}')
  rm -f "/dev/shm/loh_ac_${shm_key}" "/dev/shm/sem.loh_ac_ready_${shm_key}" "/dev/shm/sem.loh_ac_ack_${shm_key}" || true

  echo "[case-start] weight=${w} trace=${tr}" >> "$RUNNER_LOG"
  (
    export LOH_SHM_KEY="$shm_key"
    export LOH_MISS_RATIO_WEIGHT="$w"
    export RUN_TIMESTAMP="$(date +%m%d_%H%M%S)_${case_name}_$(date +%s)"
    for kv in "${COMMON_ENV[@]}"; do export "$kv"; done
    bash scripts/test_loh_rl_sb3.sh "$trace_path" "$CACHE_SIZE"
  ) > "$log_path" 2>&1 || rc=$?

  local fin
  fin=$(extract_final "$log_path" || true)
  if [ "$rc" -eq 0 ] && [ -n "$fin" ]; then
    IFS=, read -r fmr fbmr fmqps <<< "$fin"
    update_csv_row "$w" "$tr" "$fmr" "$fbmr" "$fmqps" "$log_path"
    echo "[case-done] weight=${w} trace=${tr} ok mr=${fmr} bmr=${fbmr} mqps=${fmqps}" >> "$RUNNER_LOG"
  else
    echo "[case-done] weight=${w} trace=${tr} failed_or_empty rc=${rc}" >> "$RUNNER_LOG"
  fi

  if [ -f "$OUT_DIR/update_doc_section.py" ]; then
    (
      flock 9
      python3 "$OUT_DIR/update_doc_section.py" "$RESULTS_CSV" "$DOC_PATH" >> "$OUT_DIR/doc_update.log" 2>&1 || true
    ) 9>"$OUT_DIR/doc_update.lock"
  fi
}

NA_LIST=$(mktemp)
awk -F, 'NR>1 && ($5=="NA" || $6=="NA" || $7=="NA") {print $1","$2}' "$RESULTS_CSV" > "$NA_LIST"

if [ ! -s "$NA_LIST" ]; then
  echo "[done] no NA rows" >> "$RUNNER_LOG"
  rm -f "$NA_LIST"
  exit 0
fi

running=0
while IFS=, read -r w tr; do
  run_one "$w" "$tr" &
  running=$((running + 1))
  echo "[queue] active=${running}/${PARALLEL} action=start weight=${w} trace=${tr}" >> "$RUNNER_LOG"
  if [ "$running" -ge "$PARALLEL" ]; then
    wait -n || true
    running=$((running - 1))
    echo "[queue] active=${running}/${PARALLEL} action=finish_one" >> "$RUNNER_LOG"
  fi
done < "$NA_LIST"

while [ "$running" -gt 0 ]; do
  wait -n || true
  running=$((running - 1))
  echo "[queue] active=${running}/${PARALLEL} action=finish_one" >> "$RUNNER_LOG"
done

rm -f "$NA_LIST"

echo "[finished] rerun NA completed" >> "$RUNNER_LOG"
