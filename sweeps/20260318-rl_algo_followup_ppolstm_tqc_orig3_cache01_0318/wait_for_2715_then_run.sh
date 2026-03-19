#!/usr/bin/env bash
set -u

ROOT_DIR=$(cd "$(dirname "$0")/../.." && pwd)
cd "$ROOT_DIR"

PREV_PID_FILE="tmp/rl_algo_exclude_sweep_orig3_cache01_0318/run.pid"
OUT_DIR="tmp/rl_algo_followup_ppolstm_tqc_orig3_cache01_0318"
WATCH_LOG="$OUT_DIR/watch.log"

mkdir -p "$OUT_DIR"

echo "[watch-start] waiting for 27.15 run to finish" >> "$WATCH_LOG"

if [ ! -f "$PREV_PID_FILE" ]; then
  echo "[watch-error] missing pid file: $PREV_PID_FILE" >> "$WATCH_LOG"
  exit 1
fi

PREV_PID=$(cat "$PREV_PID_FILE")
echo "[watch] 27.15 pid=$PREV_PID" >> "$WATCH_LOG"

while ps -p "$PREV_PID" >/dev/null 2>&1; do
  echo "[watch] 27.15 still running at $(date '+%F %T')" >> "$WATCH_LOG"
  sleep 30
done

echo "[watch] 27.15 finished, launching follow-up at $(date '+%F %T')" >> "$WATCH_LOG"
nohup env SKIP_PREBUILD=1 PARALLEL=3 bash "$OUT_DIR/run.sh" > "$OUT_DIR/launch.log" 2>&1 < /dev/null &
echo $! > "$OUT_DIR/run.pid"
echo "[watch] follow-up pid=$(cat "$OUT_DIR/run.pid")" >> "$WATCH_LOG"
