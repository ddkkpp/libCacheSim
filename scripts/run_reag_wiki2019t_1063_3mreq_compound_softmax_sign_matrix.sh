#!/usr/bin/env bash
# Run 3Mreq sweeps on: meta_reag, wiki_2019t, 1063.
# For each trace, test:
#   (1) compound=1
#   (2) compound=0, irt=0
# and for each mode, test 4 combos: softmax∈{0,1} × signs∈{0,1}.
set -euo pipefail

MASTER_ID=${MASTER_ID:-"modes_cpd_soft_sign_3m_$(date +%Y%m%d_%H%M%S)"}
OUT_BASE=${OUT_BASE:-"sweeps/${MASTER_ID}"}

CACHE_RATIO=${CACHE_RATIO:-0.1}

# Hard-pin to 3Mreq. Do NOT inherit any previously-exported CACHESIM_NUM_REQ.
if [[ $# -ne 0 ]]; then
  echo "Error: this script is hard-pinned to 3Mreq and does not accept args." >&2
  echo "  If you need a different num-req, use a separate runner or edit the script." >&2
  exit 2
fi
export CACHESIM_NUM_REQ=3000000

# Keep logs manageable by default (override if needed)
export LOH_SKIP_PIP_INSTALL=${LOH_SKIP_PIP_INSTALL:-1}
export LOH_SKIP_BUILD=${LOH_SKIP_BUILD:-1}
export LOH_PARALLEL_SAFE=${LOH_PARALLEL_SAFE:-1}
export CACHESIM_VERBOSE=${CACHESIM_VERBOSE:-0}
export LOH_DEBUG_LEVEL=${LOH_DEBUG_LEVEL:-0}

# Default traces (space-separated). Override via TRACE_LIST.
TRACE_LIST_DEFAULT="data/MetaCDN/meta_reag.oracleGeneral.zst data/WikiCDN/wiki_2019t.oracleGeneral.zst data/TencentCBS/1063.oracleGeneral.zst"
TRACE_LIST=${TRACE_LIST:-"${TRACE_LIST_DEFAULT}"}

mkdir -p "${OUT_BASE}"

echo "[run] MASTER_ID=${MASTER_ID}"
echo "[run] out_base=${OUT_BASE}"
echo "[run] num_req=${CACHESIM_NUM_REQ} cache_ratio=${CACHE_RATIO}"
echo "[run] traces=${TRACE_LIST}"

_trace_label() {
  local path=$1
  case "${path}" in
    data/MetaCDN/meta_reag.oracleGeneral.zst) echo "meta_reag" ;;
    data/WikiCDN/wiki_2019t.oracleGeneral.zst) echo "wiki_2019t" ;;
    data/TencentCBS/1063.oracleGeneral.zst) echo "1063" ;;
    *)
      # fallback: basename without suffixes
      b=$(basename "${path}")
      b=${b%.zst}
      echo "${b}"
      ;;
  esac
}

_write_configs() {
  local cfg_path=$1
  {
    echo "# Auto-generated: ${MASTER_ID}"
    echo "# 8 runs: 2 modes × (softmax 0/1) × (signs 0/1)"
    echo "# CACHESIM_NUM_REQ=${CACHESIM_NUM_REQ}"
    echo ""

    common="LOH_SKIP_PIP_INSTALL=1 LOH_SKIP_BUILD=1 LOH_PARALLEL_SAFE=1 CACHESIM_VERBOSE=${CACHESIM_VERBOSE} CACHESIM_NUM_REQ=${CACHESIM_NUM_REQ} LOH_RL_ALGO=SAC LOH_ACTION_SCALE=1.0"

    # Mode 1) compound=1 (note: in this mode, heuristic signs do not affect score in LOH.c)
    for soft in 0 1; do
      for signs in 0 1; do
        echo "${common} LOH_SCORE_USE_COMPOUND=1 LOH_USE_SOFTMAX=${soft} LOH_USE_HEURISTIC_SIGNS=${signs}"
      done
    done

    # Mode 2) compound=0, irt=0
    for soft in 0 1; do
      for signs in 0 1; do
        echo "${common} LOH_SCORE_USE_COMPOUND=0 LOH_SCORE_USE_IRT=0 LOH_USE_SOFTMAX=${soft} LOH_USE_HEURISTIC_SIGNS=${signs}"
      done
    done
  } > "${cfg_path}"
}

for trace in ${TRACE_LIST}; do
  if [[ ! -f "${trace}" ]]; then
    echo "Error: trace not found: ${trace}" >&2
    exit 1
  fi

  label=$(_trace_label "${trace}")
  out_dir="${OUT_BASE}/${label}"
  cfg_file="${out_dir}/configs.txt"
  mkdir -p "${out_dir}"

  echo ""
  echo "[trace] ${label}: ${trace}"
  echo "[trace] writing configs: ${cfg_file}"
  _write_configs "${cfg_file}"

  echo "[trace] running sweep..."
  SWEEP_ID="${MASTER_ID}_${label}" \
    SWEEP_OUTDIR="${out_dir}" \
    bash scripts/sweep_loh_rl_sb3.sh "${cfg_file}" "${trace}" "${CACHE_RATIO}"

  echo "[trace] summarizing results"
  python3 scripts/summarize_compound_softmax_sign_matrix.py \
    --results "${out_dir}/results.csv" \
    --out-csv "${out_dir}/matrix_summary.csv" \
    --out-md "${out_dir}/matrix_summary.md"
done

echo "[final] writing combined summary"
python3 scripts/summarize_compound_softmax_sign_matrix.py \
  --results-glob "${OUT_BASE}/*/results.csv" \
  --out-csv "${OUT_BASE}/combined_matrix_summary.csv" \
  --out-md "${OUT_BASE}/combined_matrix_summary.md"

echo "[done] outputs under: ${OUT_BASE}"
echo "  - per-trace: <trace>/results.csv, <trace>/matrix_summary.md"
echo "  - combined: combined_matrix_summary.md"
