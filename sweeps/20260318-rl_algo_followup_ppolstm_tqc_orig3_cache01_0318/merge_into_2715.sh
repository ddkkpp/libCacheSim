#!/usr/bin/env bash
set -u

ROOT_DIR=$(cd "$(dirname "$0")/../.." && pwd)
cd "$ROOT_DIR"

BASE_CSV="tmp/rl_algo_exclude_sweep_orig3_cache01_0318/results.csv"
FOLLOW_CSV="tmp/rl_algo_followup_ppolstm_tqc_orig3_cache01_0318/results.csv"
DOC_PATH="docs/20260317-FULL_EXPERIMENT_RESULTS.md"
UPDATER="tmp/rl_algo_exclude_sweep_orig3_cache01_0318/update_doc_section.py"

if [ ! -f "$BASE_CSV" ] || [ ! -f "$FOLLOW_CSV" ]; then
  echo "missing csv: base or follow" >&2
  exit 1
fi

TMP_KEYS=$(mktemp)
TMP_APPEND=$(mktemp)

# 现有key: algo,exclude_recent_steps,exclude_applied,trace
awk -F, 'NR>1 {print $1"|"$2"|"$3"|"$4}' "$BASE_CSV" | sort -u > "$TMP_KEYS"

# 挑选follow中尚未出现的行
awk -F, 'NR>1 {print $0}' "$FOLLOW_CSV" | while IFS= read -r line; do
  algo=$(echo "$line" | cut -d, -f1)
  ex=$(echo "$line" | cut -d, -f2)
  ap=$(echo "$line" | cut -d, -f3)
  tr=$(echo "$line" | cut -d, -f4)
  key="${algo}|${ex}|${ap}|${tr}"
  if ! grep -Fxq "$key" "$TMP_KEYS"; then
    echo "$line" >> "$TMP_APPEND"
    echo "$key" >> "$TMP_KEYS"
  fi
done

if [ -s "$TMP_APPEND" ]; then
  cat "$TMP_APPEND" >> "$BASE_CSV"
fi

rm -f "$TMP_APPEND" "$TMP_KEYS"

if [ -f "$UPDATER" ]; then
  python3 "$UPDATER" "$BASE_CSV" "$DOC_PATH"
fi

echo "merge_done"
