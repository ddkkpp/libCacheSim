#!/usr/bin/env bash
# Rerun TencentCBS/1063 @ 3Mreq with a matrix of penalty configs,
# and generate a clear summary (configs + missratio + reward/penalty stats).
set -euo pipefail

TRACE_FILE=${TRACE_FILE:-data/TencentCBS/1063.oracleGeneral.zst}
CACHE_RATIO=${CACHE_RATIO:-0.1}

# A sweep id is embedded into RUN_TIMESTAMP so we can glob logs reliably.
SWEEP_ID=${SWEEP_ID:-"1063_penalty_3m_$(date +%Y%m%d_%H%M%S)"}
OUT_DIR=${SWEEP_OUTDIR:-"sweeps/${SWEEP_ID}"}
CONFIGS_FILE="${OUT_DIR}/configs.txt"

# Speed/safety defaults
export LOH_PARALLEL_SAFE=${LOH_PARALLEL_SAFE:-1}
export LOH_SKIP_PIP_INSTALL=${LOH_SKIP_PIP_INSTALL:-1}
export LOH_DEBUG_LEVEL=${LOH_DEBUG_LEVEL:-1}
export CACHESIM_NUM_REQ=${CACHESIM_NUM_REQ:-3000000}
export CACHESIM_VERBOSE=${CACHESIM_VERBOSE:-0}
export LOH_USE_HEURISTIC_SIGNS=${LOH_USE_HEURISTIC_SIGNS:-0}

mkdir -p "${OUT_DIR}"

if [[ ! -f "${TRACE_FILE}" ]]; then
  echo "Error: TRACE_FILE not found: ${TRACE_FILE}" >&2
  exit 1
fi

echo "[run] sweep_id=${SWEEP_ID}"
echo "[run] trace=${TRACE_FILE} cache_ratio=${CACHE_RATIO} num_req=${CACHESIM_NUM_REQ}"
echo "[run] out_dir=${OUT_DIR}"

# Build once with penalty compiled in.
# (LOH_ENABLE_PENALTY is a compile-time flag in this repo's build script.)
if [[ "${SKIP_BUILD:-0}" != "1" ]]; then
  echo "[build] building cachesim with LOH_ENABLE_PENALTY=1 (once)"
  LOH_ENABLE_PENALTY=1 bash scripts/debug.sh -c
else
  echo "[build] SKIP_BUILD=1; assume cachesim already built with LOH_ENABLE_PENALTY=1"
fi

# In per-run configs we set LOH_SKIP_BUILD=1 to avoid rebuilding for each line.
# Penalty scale/formula/weights are runtime env vars (Python-side) and do not require rebuild.

echo "[run] writing configs: ${CONFIGS_FILE}"
{
  echo "# Auto-generated: ${SWEEP_ID}"
  echo "# Common per-run flags"
  echo "# NOTE: Keep LOH_ENABLE_PENALTY=1 in all runs so logs are comparable"
  echo ""

  common="LOH_PARALLEL_SAFE=1 LOH_SKIP_PIP_INSTALL=1 LOH_SKIP_BUILD=1 LOH_DEBUG_LEVEL=${LOH_DEBUG_LEVEL} CACHESIM_VERBOSE=${CACHESIM_VERBOSE} CACHESIM_NUM_REQ=${CACHESIM_NUM_REQ} LOH_USE_HEURISTIC_SIGNS=${LOH_USE_HEURISTIC_SIGNS} LOH_RL_ALGO=SAC"

  # Baseline: penalty compiled in, but reward does NOT use penalty.
  echo "${common} LOH_ENABLE_PENALTY=1 LOH_REWARD_USE_PENALTY=0"

  # Core penalty matrix (tunable via env):
  # - scales: reciprocal/log/survival
  # - formulas: relative/centered/one_minus/neg/net/net2
  # - weights: smaller set for classic formulas; larger for net/net2
  scales=(reciprocal log survival)
  formulas_basic=(relative centered one_minus neg)
  formulas_net=(net net2)
  w_basic=(0.1 0.2 0.5 1.0)
  w_net=(1.0 2.0 3.0)

  # Keep these fixed unless you explicitly change them.
  # (They materially affect the penalty semantics; we pin them for clarity.)
  fixed_penalty="LOH_PENALTY_CUTOFF=0 LOH_PENALTY_DMAX=400000 LOH_PENALTY_EMPTY_AS_GOOD=1 LOH_PENALTY_REFINE_ON_LATE=1"
  fixed_survival="LOH_SURVIVAL_BINS=64 LOH_SURVIVAL_QUANTILE=0.99 LOH_SURVIVAL_MINCOUNT=1000"

  for scale in "${scales[@]}"; do
    for form in "${formulas_basic[@]}"; do
      for w in "${w_basic[@]}"; do
        echo "${common} LOH_ENABLE_PENALTY=1 LOH_PENALTY_SCALE=${scale} LOH_PENALTY_REWARD_FORMULA=${form} LOH_REWARD_USE_PENALTY=1 LOH_REWARD_W_PENALTY=${w} ${fixed_penalty} ${fixed_survival}"
      done
    done
    for form in "${formulas_net[@]}"; do
      for w in "${w_net[@]}"; do
        echo "${common} LOH_ENABLE_PENALTY=1 LOH_PENALTY_SCALE=${scale} LOH_PENALTY_REWARD_FORMULA=${form} LOH_REWARD_USE_PENALTY=1 LOH_REWARD_W_PENALTY=${w} ${fixed_penalty} ${fixed_survival}"
      done
    done
  done
} > "${CONFIGS_FILE}"

echo "[run] starting sweep via scripts/sweep_loh_rl_sb3.sh"
SWEEP_ID="${SWEEP_ID}" SWEEP_OUTDIR="${OUT_DIR}" \
  bash scripts/sweep_loh_rl_sb3.sh "${CONFIGS_FILE}" "${TRACE_FILE}" "${CACHE_RATIO}"

echo "[analyze] generating AC reward/penalty report for this sweep"
python3 scripts/analyze_ac_reward_signal.py \
  "ac_sb3_${SWEEP_ID}_*.log" \
  --report-md "${OUT_DIR}/ac_reward_penalty_report.md" \
  --progress-every 1

echo "[summarize] writing merged summary (results.csv + AC stats)"
python3 scripts/summarize_penalty_sweep_results.py \
  --results "${OUT_DIR}/results.csv" \
  --ac-report "${OUT_DIR}/ac_reward_penalty_report.md" \
  --out-csv "${OUT_DIR}/penalty_sweep_summary.csv" \
  --out-md "${OUT_DIR}/penalty_sweep_summary.md"

echo "[done] outputs:"
echo "  - ${OUT_DIR}/results.csv"
echo "  - ${OUT_DIR}/ac_reward_penalty_report.md"
echo "  - ${OUT_DIR}/penalty_sweep_summary.csv"
echo "  - ${OUT_DIR}/penalty_sweep_summary.md"
