#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

QUEUE_ARG="${1:-tmp/phase_ab_latest}"
QUEUE_ROOT="$QUEUE_ARG"

if [ -L "$QUEUE_ROOT" ]; then
  QUEUE_ROOT="$(readlink -f "$QUEUE_ROOT")"
fi

if [ ! -d "$QUEUE_ROOT" ]; then
  echo "queue directory not found: $QUEUE_ROOT" >&2
  exit 1
fi

SUMMARY_FILE="${QUEUE_ROOT}/summary.txt"
QUEUE_LOG="${QUEUE_ROOT}/queue.log"
CURRENT_TASK_FILE="${QUEUE_ROOT}/current_task.txt"

echo "queue_root=${QUEUE_ROOT}"
if [ -f "$SUMMARY_FILE" ]; then
  cat "$SUMMARY_FILE"
fi

if [ -f "$CURRENT_TASK_FILE" ]; then
  current_task="$(cat "$CURRENT_TASK_FILE")"
  echo
  echo "current_task=${current_task}"
  IFS=',' read -r -a current_tasks <<< "$current_task"
  for task in "${current_tasks[@]}"; do
    current_log="${QUEUE_ROOT}/logs/${task}.log"
    if [ -f "$current_log" ]; then
      echo
      echo "== current log tail: ${task} =="
      tail -n 20 "$current_log"
    fi
  done
fi

echo
echo "== queue log tail =="
tail -n 20 "$QUEUE_LOG"
