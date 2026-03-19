#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
PROJ="$(cd "$ROOT/../.." && pwd)"
cd "$PROJ"

OUT_DIR="$ROOT"
LOG_DIR="$OUT_DIR/logs"
RES="$OUT_DIR/results.csv"
RUN_LOG="$OUT_DIR/runner.log"
STATE="$OUT_DIR/state.txt"
: > "$RUN_LOG"
echo "task,trace,mode,adaptive,score_rebalance,rc,result_line,log_file" > "$RES"

log(){ printf '[%s] %s\n' "$(date '+%F %T')" "$*" | tee -a "$RUN_LOG"; }

csv_escape(){
  local v="$1"
  v="${v//\"/\"\"}"
  printf '%s' "$v"
}

mk_key(){
  local s="$1"
  cksum <<< "$s" | awk '{print $1}'
}

run_one(){
  local trace_name="$1" trace_path="$2" log1p="$3" recp="$4" adaptive="$5" score_rb="$6"
  local task="${trace_name}_a${adaptive}_s${score_rb}"
  local lf="$LOG_DIR/${task}.log"
  local pyf="ac_sb3_${task}.log"
  local cf="cachesim_sb3_${task}.log"
  local key
  key="$(mk_key "$task")"
  log "start $task trace=$trace_path"
  set +e
  (
    export LOH_PARALLEL_SAFE=1
    export LOH_SKIP_PIP_INSTALL=1
    export LOH_SKIP_BUILD=1
    export LOH_DEBUG_LEVEL=0
    export LOH_WAIT_MODE=nonblocked
    export LOH_ASYNC_TRAIN=1
    export LOH_SCORE_USE_COMPOUND=1
    export LOH_SCORE_USE_IRT=0
    export LOH_RANDOM_CANDIDATES=96
    export LOH_STRUCTURED_CANDIDATES=96
    export LOH_TAIL_SAMPLE=0
    export LOH_ADAPTIVE_BUDGET="$adaptive"
    export LOH_USE_SCORE_REBALANCE="$score_rb"
    export LOH_MISS_RATIO_WEIGHT=1.0
    export LOH_ENABLE_PENALTY=0
    export CACHESIM_NUM_REQ=0
    export LOH_BUILD_RELEASE=1
    export LOH_CACHESIM_BIN=_build_rel/bin/cachesim
    export LOH_FEATURE_LOG1P="$log1p"
    export LOH_FEATURE_LOG1P_RECIPROCAL="$recp"
    export RUN_TIMESTAMP="$task"
    export LOH_SHM_KEY="$key"
    bash scripts/test_loh_rl_sb3.sh "$trace_path" 0.1
  ) > "$lf" 2>&1
  rc=$?
  set -e
  [[ -f "$pyf" ]] && mv -f "$pyf" "$LOG_DIR/"
  [[ -f "$cf" ]] && mv -f "$cf" "$LOG_DIR/"
  line=$(grep -E 'miss ratio .*byte miss ratio|cache size' "$lf" | tail -1 || true)
  printf '"%s","%s","%s",%s,%s,%s,"%s","%s"\n' \
    "$task" "$trace_name" "log1p=${log1p},recp=${recp}" "$adaptive" "$score_rb" "$rc" \
    "$(csv_escape "$line")" "$lf" >> "$RES"
  if [[ "$rc" -eq 0 ]]; then
    log "done $task :: $line"
  else
    log "fail $task rc=$rc :: $line"
  fi
}

launch(){
  run_one "$@" &
  pids+=("$!")
}
wait_slot(){
  while [[ ${#pids[@]} -ge 2 ]]; do
    wait -n || true
    np=()
    for p in "${pids[@]}"; do kill -0 "$p" 2>/dev/null && np+=("$p"); done
    pids=("${np[@]}")
  done
}
wait_all(){
  while [[ ${#pids[@]} -gt 0 ]]; do
    wait -n || true
    np=()
    for p in "${pids[@]}"; do kill -0 "$p" 2>/dev/null && np+=("$p"); done
    pids=("${np[@]}")
  done
}

pids=()
# trace definitions
# 1063/meta => log1p=1,recp=0 ; wiki => log1p=0,recp=1
for cfg in "0 0" "1 0" "1 1"; do
  read -r adaptive score_rb <<< "$cfg"
  wait_slot; launch "1063" "data/TencentCBS/1063.oracleGeneral.zst" 1 0 "$adaptive" "$score_rb"
  wait_slot; launch "meta" "data/MetaCDN/meta_reag.oracleGeneral.zst" 1 0 "$adaptive" "$score_rb"
  wait_slot; launch "wiki" "data/WikiCDN/wiki_2019t.oracleGeneral.zst" 0 1 "$adaptive" "$score_rb"
done
wait_all
log "all done"
