#!/usr/bin/env bash
set -u

ROOT_DIR=$(cd "$(dirname "$0")/../.." && pwd)
cd "$ROOT_DIR"

RUN_PID_FILE="tmp/rl_algo_followup_ppolstm_tqc_orig3_cache01_0318/run.pid"
MERGE_SCRIPT="tmp/rl_algo_followup_ppolstm_tqc_orig3_cache01_0318/merge_into_2715.sh"
SYNC_LOG="tmp/rl_algo_followup_ppolstm_tqc_orig3_cache01_0318/auto_sync.log"

echo "[sync-start] $(date '+%F %T')" >> "$SYNC_LOG"

while true; do
  if [ -f "$MERGE_SCRIPT" ]; then
    bash "$MERGE_SCRIPT" >> "$SYNC_LOG" 2>&1 || true
  fi

  if [ ! -f "$RUN_PID_FILE" ]; then
    echo "[sync-stop] missing run.pid at $(date '+%F %T')" >> "$SYNC_LOG"
    break
  fi

  pid=$(cat "$RUN_PID_FILE")
  if ! ps -p "$pid" >/dev/null 2>&1; then
    echo "[sync-final] run ended, final merge at $(date '+%F %T')" >> "$SYNC_LOG"
    if [ -f "$MERGE_SCRIPT" ]; then
      bash "$MERGE_SCRIPT" >> "$SYNC_LOG" 2>&1 || true
    fi
    break
  fi

  sleep 60
done

echo "[sync-exit] $(date '+%F %T')" >> "$SYNC_LOG"
