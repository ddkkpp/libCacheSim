#!/usr/bin/env bash
# For each trace, take its best base config (by miss_ratio) from a matrix summary CSV,
# then sweep compile-time LOH_INCLUDE_* state combinations (incl. request history),
# and write a combined summary CSV.
set -euo pipefail

MATRIX_CSV=${1:-"sweeps/modes_cpd_soft_sign_3m_20260206_145822/combined_matrix_summary.csv"}
CACHE_RATIO=${CACHE_RATIO:-0.1}
CACHESIM_NUM_REQ=${CACHESIM_NUM_REQ:-3000000}

TS=${TS:-"bestcfg_statecombo_$(date +%Y%m%d_%H%M%S)"}
OUT_ROOT=${OUT_ROOT:-"sweeps/${TS}"}
mkdir -p "${OUT_ROOT}"

# If the sweep gets interrupted, rerunning this script should resume work rather than
# duplicating rows in the combined CSV.
SWEEP_RESUME=${SWEEP_RESUME:-1}

BEST_CFGS_CSV="${OUT_ROOT}/best_cfgs.csv"
STATE_COMBOS_CSV="${OUT_ROOT}/state_combos.csv"
COMBINED_CSV="${OUT_ROOT}/combined_state_combo_summary.csv"

log() { echo "[$(date +%H:%M:%S)] $*"; }

log "matrix_csv=${MATRIX_CSV}"
log "out_root=${OUT_ROOT}"
log "cache_ratio=${CACHE_RATIO} num_req=${CACHESIM_NUM_REQ}"

/bin/python3 scripts/extract_best_cfgs_from_matrix.py "${MATRIX_CSV}" --metric miss_ratio --out "${BEST_CFGS_CSV}"
/bin/python3 scripts/generate_state_combos.py --include-request --out "${STATE_COMBOS_CSV}"

# header
if [[ ! -f "${COMBINED_CSV}" ]]; then
  echo "trace,mode,include_hit_miss,include_cache,include_candidate,include_topk,include_avgtopk,include_request,rl_state_use_missratio,miss_ratio,byte_miss_ratio,throughput_mqps,exit_code,run_timestamp,base_config" > "${COMBINED_CSV}"
fi

trace_path() {
  case "$1" in
    1063) echo "data/TencentCBS/1063.oracleGeneral.zst";;
    meta_reag) echo "data/MetaCDN/meta_reag.oracleGeneral.zst";;
    wiki_2019t) echo "data/WikiCDN/wiki_2019t.oracleGeneral.zst";;
    *) echo "";;
  esac
}

# Iterate traces from BEST_CFGS_CSV
/bin/python3 - "${BEST_CFGS_CSV}" <<'PY' | while IFS= read -r trace; do
import csv, sys
p=sys.argv[1]
with open(p, newline='') as f:
    r=csv.DictReader(f)
    for row in r:
        print(row['trace'])
PY
  [[ -z "${trace}" ]] && continue
  tf=$(trace_path "${trace}")
  if [[ -z "${tf}" || ! -f "${tf}" ]]; then
    log "skip trace=${trace} (unknown or missing file: ${tf})"
    continue
  fi

  # Load base cfg vars for this trace
  read -r base_mode base_comp base_irt base_soft base_signs < <(
    /bin/python3 -c 'import pandas as pd,sys
p=sys.argv[1]; t=sys.argv[2]
df=pd.read_csv(p)
row=df[df["trace"]==t].iloc[0]
print(row["mode"], int(row["LOH_SCORE_USE_COMPOUND"]), int(row["LOH_SCORE_USE_IRT"]), int(row["LOH_USE_SOFTMAX"]), int(row["LOH_USE_HEURISTIC_SIGNS"]))
' "${BEST_CFGS_CSV}" "${trace}"
  )

  log "===== TRACE=${trace} file=${tf} base=${base_mode} softmax=${base_soft} signs=${base_signs} ====="

  trace_out="${OUT_ROOT}/${trace}"
  mkdir -p "${trace_out}"

  combo_idx=0
  # Iterate state combos
  /bin/python3 - "${STATE_COMBOS_CSV}" <<'PY' | while read -r hm cache cand topk avgtopk req; do
import csv, sys
p=sys.argv[1]
with open(p, newline='') as f:
    r=csv.DictReader(f)
    for row in r:
        print(
            row['include_hit_miss'],
            row['include_cache'],
            row['include_candidate'],
            row['include_topk'],
            row['include_avgtopk'],
            row['include_request'],
        )
PY
    combo_idx=$((combo_idx+1))

    sweep_id="${TS}__${trace}__c$(printf '%03d' "${combo_idx}")"
    out_dir="${trace_out}/${sweep_id}"
    mkdir -p "${out_dir}"

    log "[${trace}] combo ${combo_idx}: hm=${hm} cache=${cache} cand=${cand} topk=${topk} avgtopk=${avgtopk} req=${req}"

    # Build cachesim once for this compile-time layout
    export LOH_INCLUDE_HIT_MISS_FEATURES="${hm}"
    export LOH_INCLUDE_CACHE_FEATURES="${cache}"
    export LOH_INCLUDE_CANDIDATE_FEATURES="${cand}"
    export LOH_INCLUDE_TOPK_CANDIDATE_FEATURES="${topk}"
    export LOH_INCLUDE_AVGTOPK_CANDIDATE_FEATURES="${avgtopk}"
    export LOH_INCLUDE_REQUEST="${req}"

    bash scripts/debug.sh >/dev/null

    configs_file="${out_dir}/configs.txt"
    {
      common="LOH_PARALLEL_SAFE=1 LOH_SKIP_PIP_INSTALL=1 LOH_SKIP_BUILD=1 CACHESIM_VERBOSE=0 CACHESIM_NUM_REQ=${CACHESIM_NUM_REQ} LOH_RL_ALGO=SAC"
      common+=" LOH_SCORE_USE_COMPOUND=${base_comp} LOH_SCORE_USE_IRT=${base_irt} LOH_USE_SOFTMAX=${base_soft} LOH_USE_HEURISTIC_SIGNS=${base_signs}"
      common+=" LOH_INCLUDE_HIT_MISS_FEATURES=${hm} LOH_INCLUDE_CACHE_FEATURES=${cache} LOH_INCLUDE_CANDIDATE_FEATURES=${cand}"
      common+=" LOH_INCLUDE_TOPK_CANDIDATE_FEATURES=${topk} LOH_INCLUDE_AVGTOPK_CANDIDATE_FEATURES=${avgtopk} LOH_INCLUDE_REQUEST=${req}"

      echo "${common} RL_STATE_USE_MISSRATIO=1"
      echo "${common} RL_STATE_USE_MISSRATIO=0"
    } > "${configs_file}"

    SWEEP_ID="${sweep_id}" SWEEP_OUTDIR="${out_dir}" \
      SWEEP_REPEATS=1 SEED_BASE=0 \
      SWEEP_RESUME="${SWEEP_RESUME}" \
      bash scripts/sweep_loh_rl_sb3.sh "${configs_file}" "${tf}" "${CACHE_RATIO}" >/dev/null

    # Append to combined CSV (use results.csv to preserve run_timestamp)
    appended_marker="${out_dir}/.combined_appended"
    if [[ -f "${appended_marker}" ]]; then
      log "[${trace}] combo ${combo_idx}: combined already appended; skip"
      continue
    fi

    /bin/python3 - <<'PY' "${out_dir}/results.csv" "${COMBINED_CSV}" "${trace}" "${base_mode}" "${hm}" "${cache}" "${cand}" "${topk}" "${avgtopk}" "${req}" "${base_comp}" "${base_irt}" "${base_soft}" "${base_signs}"
import csv, sys
res_path, combined_path, trace, mode, hm, cache, cand, topk, avgtopk, req, bc, bi, bs, bsign = sys.argv[1:15]

def _extract(line: str, key: str):
    for part in line.split():
        if part.startswith(key+'='):
            return part.split('=',1)[1]
    return ''

rows=[]
with open(res_path, newline='') as f:
    r=csv.DictReader(f)
    for row in r:
        cfg=(row.get('config') or '').strip()
        rows.append({
            'trace': trace,
            'mode': mode,
            'include_hit_miss': hm,
            'include_cache': cache,
            'include_candidate': cand,
            'include_topk': topk,
            'include_avgtopk': avgtopk,
            'include_request': req,
            'rl_state_use_missratio': _extract(cfg, 'RL_STATE_USE_MISSRATIO') or '1',
            'miss_ratio': (row.get('miss_ratio') or '').strip(),
            'byte_miss_ratio': (row.get('byte_miss_ratio') or '').strip(),
            'throughput_mqps': (row.get('throughput_mqps') or '').strip(),
            'exit_code': (row.get('exit_code') or '').strip(),
            'run_timestamp': (row.get('run_timestamp') or '').strip(),
            'base_config': f"LOH_SCORE_USE_COMPOUND={bc} LOH_SCORE_USE_IRT={bi} LOH_USE_SOFTMAX={bs} LOH_USE_HEURISTIC_SIGNS={bsign}",
        })

with open(combined_path, 'a', newline='') as f:
    w=csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    for rr in rows:
        w.writerow(rr)
PY

  touch "${appended_marker}"

  done

done

log "Done. Combined summary: ${COMBINED_CSV}"

# Post-summarize into smaller tables (best RL_STATE_USE_MISSRATIO per layout, and best layout per trace)
if [[ -f "${COMBINED_CSV}" ]]; then
  /bin/python3 scripts/summarize_state_combo_sweep.py "${COMBINED_CSV}" --metric miss_ratio --out-dir "${OUT_ROOT}" >/dev/null || true
  log "Wrote: ${OUT_ROOT}/best_per_layout.csv and best_overall_per_trace.csv"
fi
