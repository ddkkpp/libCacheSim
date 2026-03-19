#!/usr/bin/env bash
set -u
LOG_DIR="tmp/phase_ab_0312_223925/logs"
RUN_LOG="$LOG_DIR/manual_s3fifo_original3_0p1_runner.log"
: > "$RUN_LOG"
log(){ printf '[%s] %s\n' "$(date '+%F %T')" "$*" | tee -a "$RUN_LOG"; }
run_case(){
  local name="$1"
  local trace="$2"
  local log_file="$LOG_DIR/manual_s3fifo_${name}_0p1.log"
  log "start ${name} trace=${trace}"
  _build_rel/bin/cachesim "$trace" oracleGeneral S3FIFO 0.1 -v 0 > "$log_file" 2>&1
  local rc=$?
  local result_line
  result_line=$(grep -E 'miss ratio .*byte miss ratio|cache size' "$log_file" | tail -1 || true)
  if [ "$rc" -eq 0 ]; then
    log "done ${name} :: ${result_line}"
  else
    log "fail ${name} rc=${rc} :: ${result_line}"
  fi
  return "$rc"
}
run_case 1063 data/TencentCBS/1063.oracleGeneral.zst &
pid1=$!
run_case meta data/MetaCDN/meta_reag.oracleGeneral.zst &
pid2=$!
wait "$pid1"
rc1=$?
wait "$pid2"
rc2=$?
run_case wiki data/WikiCDN/wiki_2019t.oracleGeneral.zst
rc3=$?
log "finished rc_1063=${rc1} rc_meta=${rc2} rc_wiki=${rc3}"
