#!/usr/bin/env bash
set -euo pipefail

SWEEP_DIR=${1:?Usage: wait_and_append_sweep.sh <sweep_dir> [configs_file] [md_file]}
CONFIGS_FILE=${2:-}
MD_FILE=${3:-sweep_results.md}

SUMMARY_CSV="${SWEEP_DIR%/}/summary.csv"

while [ ! -f "${SUMMARY_CSV}" ]; do
  sleep 60
done

ARGS=("--sweep-dir" "${SWEEP_DIR}" "--md" "${MD_FILE}")
if [ -n "${CONFIGS_FILE}" ]; then
  ARGS+=("--configs" "${CONFIGS_FILE}")
fi

python3 scripts/append_sweep_to_results_md.py "${ARGS[@]}"
