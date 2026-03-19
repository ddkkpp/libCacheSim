#!/usr/bin/env bash
set -u

while pgrep -f 'tmp/transformq0_hitmiss1_orig3_cache01_0317/run.sh' >/dev/null; do
  python3 tmp/transformq0_hitmiss1_orig3_cache01_0317/update_doc_section.py \
    tmp/transformq0_hitmiss1_orig3_cache01_0317/results.csv \
    docs/20260317-FULL_EXPERIMENT_RESULTS.md >> tmp/transformq0_hitmiss1_orig3_cache01_0317/doc_update_watch.log 2>&1
  sleep 20
done

python3 tmp/transformq0_hitmiss1_orig3_cache01_0317/update_doc_section.py \
  tmp/transformq0_hitmiss1_orig3_cache01_0317/results.csv \
  docs/20260317-FULL_EXPERIMENT_RESULTS.md >> tmp/transformq0_hitmiss1_orig3_cache01_0317/doc_update_watch.log 2>&1
