#!/usr/bin/env bash
set -euo pipefail

# Runs 2 LOH score modes across multiple traces (3M req each), with miss_ratio_weight=0.
# Modes are defined in scripts/sweep_configs_modes2_signlog1psoftmax1_mrw0.txt

CACHE_RATIO=${1:-0.1}
SWEEP_REPEATS=${SWEEP_REPEATS:-1}
SEED_BASE=${SEED_BASE:-0}

CONFIGS_FILE="scripts/sweep_configs_modes2_signlog1psoftmax1_mrw0.txt"

if [[ ! -f "${CONFIGS_FILE}" ]]; then
  echo "Error: configs file not found: ${CONFIGS_FILE}" >&2
  exit 1
fi

TRACES=(
  "data/MetaCDN/meta_reag.oracleGeneral.zst"
  "data/WikiCDN/wiki_2019t.oracleGeneral.zst"
  "data/TencentCBS/1063.oracleGeneral.zst"
  "data/Alibaba/4.oracleGeneral.zst"
  "data/MetaKV/202401_kv_traces_all_sort.csv.oracleGeneral.zst"
  "data/TencentPhoto/tencent_photo1.oracleGeneral.zst"
  "data/WikiCDN/wiki_2016u.oracleGeneral.zst"
)

TS=${TS:-"modes2_mrw0_$(date +%Y%m%d_%H%M%S)"}
OUT_ROOT="sweeps/${TS}"
mkdir -p "${OUT_ROOT}"

COMBINED_CSV="${OUT_ROOT}/combined_summary.csv"
if [[ ! -f "${COMBINED_CSV}" ]]; then
  echo "trace_file,sweep_id,idx,n,miss_ratio_mean,byte_miss_ratio_mean,throughput_mqps_mean,config" > "${COMBINED_CSV}"
fi

# Global knobs (same for all runs)
export CACHESIM_NUM_REQ=3000000
export LOH_ENABLE_SEMAPHORE=1
unset LOH_DISABLE_SEMAPHORE || true
# Serial mode: allow test script to clean up previous processes
export LOH_PARALLEL_SAFE=0

# Make sure sweep uses our desired repeats and seed base unless caller overrides.
export SWEEP_REPEATS
export SEED_BASE

log() { echo "[$(date +%H:%M:%S)] $*"; }

log "Batch ID: ${TS}"
log "Output: ${OUT_ROOT}"
log "Cache ratio: ${CACHE_RATIO}"
log "Repeats: ${SWEEP_REPEATS} seed_base: ${SEED_BASE}"
log "CACHESIM_NUM_REQ=${CACHESIM_NUM_REQ}"
log "LOH_ENABLE_SEMAPHORE=${LOH_ENABLE_SEMAPHORE}"
log "Configs: ${CONFIGS_FILE}"

missing=0
for t in "${TRACES[@]}"; do
  if [[ ! -f "${t}" ]]; then
    log "MISSING trace: ${t}"
    missing=$((missing+1))
  fi
done
if [[ ${missing} -gt 0 ]]; then
  log "Missing ${missing} trace(s). Will skip missing ones and continue."
fi

for t in "${TRACES[@]}"; do
  if [[ ! -f "${t}" ]]; then
    continue
  fi

  base=$(basename "${t}")
  safe=${base//[^A-Za-z0-9._-]/_}
  sweep_id="${TS}__${safe}"
  out_dir="${OUT_ROOT}/${sweep_id}"

  log "===== TRACE: ${t} ====="
  log "SWEEP_ID=${sweep_id}"

  # Run sweep for this trace (no resume: always re-run)
  SWEEP_ID="${sweep_id}" SWEEP_OUTDIR="${out_dir}" bash scripts/sweep_loh_rl_sb3.sh "${CONFIGS_FILE}" "${t}" "${CACHE_RATIO}"

  summary_csv="${out_dir}/summary.csv"
  if [[ ! -f "${summary_csv}" ]]; then
    log "WARN: summary not found: ${summary_csv}"
    continue
  fi

  # Append per-trace summary rows into combined csv
  python3 - <<'PY' "${t}" "${sweep_id}" "${summary_csv}" "${COMBINED_CSV}"
import csv
import sys

trace_file, sweep_id, summary_csv, combined_csv = sys.argv[1:5]

rows = []
with open(summary_csv, newline='') as f:
    r = csv.DictReader(f)
    for row in r:
        rows.append(row)

with open(combined_csv, 'a', newline='') as f:
    w = csv.writer(f)
    for row in rows:
        w.writerow([
            trace_file,
            sweep_id,
            (row.get('idx') or '').strip(),
            (row.get('n') or '').strip(),
            (row.get('miss_ratio_mean') or '').strip(),
            (row.get('byte_miss_ratio_mean') or '').strip(),
            (row.get('throughput_mqps_mean') or '').strip(),
            (row.get('config') or '').strip().replace('\n', ' '),
        ])
PY

  log "Appended summary to ${COMBINED_CSV}"
done

log "All done. Combined summary: ${COMBINED_CSV}"
