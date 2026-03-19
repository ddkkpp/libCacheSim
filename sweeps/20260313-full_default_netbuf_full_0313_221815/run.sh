#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT_DIR"

OUT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$OUT_DIR/logs"
RUN_LOG="$OUT_DIR/runner.log"
RESULTS="$OUT_DIR/results.csv"

mkdir -p "$LOG_DIR"

csv_escape() {
  local v="$1"
  v="${v//\"/\"\"}"
  printf '"%s"' "$v"
}

log() {
  local line="[$(date '+%F %T')] $*"
  printf '%s\n' "$line" | tee -a "$RUN_LOG"
}

echo "group,config_id,trace,mode,sac_net_arch,sac_buffer_size,sac_batch_size,rc,result_line,log_file" > "$RESULTS"

run_one() {
  local group="$1"
  local config_id="$2"
  local trace_name="$3"
  local trace_path="$4"
  local mode="$5"
  local net_arch="$6"
  local buffer_size="$7"
  local batch_size="$8"

  local task_id="${group}_${config_id}_${trace_name}"
  local task_log="$LOG_DIR/${task_id}.log"
  local result_line rc

  log "start ${task_id}"
  set +e
  (
    export LOH_ENABLE_SEMAPHORE=1
    export LOH_BUILD_RELEASE=1
    export LOH_SKIP_BUILD=1
    export LOH_SKIP_PIP_INSTALL=1
    export LOH_PERF_PROFILING=0
    export LOH_DEBUG_LEVEL=0

    export LOH_WAIT_MODE=nonblocked
    export LOH_ASYNC_TRAIN=1
    export LOH_SCORE_USE_COMPOUND=1
    export LOH_SCORE_USE_IRT=0
    export LOH_RANDOM_CANDIDATES=96
    export LOH_STRUCTURED_CANDIDATES=96
    export LOH_ENABLE_PENALTY=0
    export LOH_MISS_RATIO_WEIGHT=1.0
    export LOH_INCLUDE_WEIGHTS_IN_OBS=1
    export LOH_ADAPTIVE_BUDGET=1
    export LOH_USE_SCORE_REBALANCE=0
    export CACHESIM_NUM_REQ=0

    if [[ "$mode" == "log1p" ]]; then
      export LOH_FEATURE_LOG1P=1
      export LOH_FEATURE_LOG1P_RECIPROCAL=0
    else
      export LOH_FEATURE_LOG1P=0
      export LOH_FEATURE_LOG1P_RECIPROCAL=1
    fi

    export LOH_RL_ALGO=SAC
    export SAC_NET_ARCH="$net_arch"
    export SAC_BUFFER_SIZE="$buffer_size"
    export SAC_BATCH_SIZE="$batch_size"

    export LOH_PARALLEL_SAFE=1
    export RUN_TIMESTAMP="$task_id"
    export LOH_SHM_KEY="$(cksum <<< "$task_id" | awk '{print $1}')"

    bash scripts/test_loh_rl_sb3.sh "$trace_path" 0.1
  ) > "$task_log" 2>&1
  rc=$?
  set -e

  result_line="$(grep -E 'miss ratio .*byte miss ratio|cache size' "$task_log" | tail -1 || true)"
  {
    csv_escape "$group"; printf ','
    csv_escape "$config_id"; printf ','
    csv_escape "$trace_name"; printf ','
    csv_escape "$mode"; printf ','
    csv_escape "$net_arch"; printf ','
    csv_escape "$buffer_size"; printf ','
    csv_escape "$batch_size"; printf ','
    csv_escape "$rc"; printf ','
    csv_escape "$result_line"; printf ','
    csv_escape "$task_log"; printf '\n'
  } >> "$RESULTS"

  if [[ "$rc" -eq 0 ]]; then
    log "done ${task_id} :: ${result_line}"
  else
    log "fail ${task_id} rc=${rc} :: ${result_line}"
  fi
}

# trace,mode
TRACE_NAMES=("1063" "meta" "wiki")
TRACE_PATHS=("data/TencentCBS/1063.oracleGeneral.zst" "data/MetaCDN/meta_reag.oracleGeneral.zst" "data/WikiCDN/wiki_2019t.oracleGeneral.zst")
TRACE_MODES=("log1p" "log1p" "reciprocal")

# Group 1: net depth sweep (1/3/4 layers)
NET_CFG_IDS=("net1" "net3" "net4")
NET_ARCHS=("256" "512,512,256" "512,512,256,256")
for i in "${!NET_CFG_IDS[@]}"; do
  for t in "${!TRACE_NAMES[@]}"; do
    run_one "net" "${NET_CFG_IDS[$i]}" "${TRACE_NAMES[$t]}" "${TRACE_PATHS[$t]}" "${TRACE_MODES[$t]}" "${NET_ARCHS[$i]}" "10000" "256"
  done
done

# Group 2: buffer/batch sweep (all requested combinations)
BB_CFG_IDS=("bb_50k_512" "bb_100k_512" "bb_50k_1024")
BB_BUFFERS=("50000" "100000" "50000")
BB_BATCHES=("512" "512" "1024")
for i in "${!BB_CFG_IDS[@]}"; do
  for t in "${!TRACE_NAMES[@]}"; do
    run_one "bb" "${BB_CFG_IDS[$i]}" "${TRACE_NAMES[$t]}" "${TRACE_PATHS[$t]}" "${TRACE_MODES[$t]}" "256,256" "${BB_BUFFERS[$i]}" "${BB_BATCHES[$i]}"
  done
done

log "all done"
