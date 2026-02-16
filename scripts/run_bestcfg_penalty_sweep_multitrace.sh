#!/usr/bin/env bash
# For each trace, take its best base config (by miss_ratio) from a matrix summary CSV,
# then run a penalty parameter sweep (two-stage: main grid + one-at-a-time),
# and write per-trace + combined summaries.
set -euo pipefail

MATRIX_CSV=${1:-"sweeps/modes_cpd_soft_sign_3m_20260206_145822/combined_matrix_summary.csv"}
CACHE_RATIO=${CACHE_RATIO:-0.1}
CACHESIM_NUM_REQ=${CACHESIM_NUM_REQ:-3000000}

TS=${TS:-"bestcfg_penalty_$(date +%Y%m%d_%H%M%S)"}
OUT_ROOT=${OUT_ROOT:-"sweeps/${TS}"}
mkdir -p "${OUT_ROOT}"

BEST_CFGS_CSV="${OUT_ROOT}/best_cfgs.csv"

log() { echo "[$(date +%H:%M:%S)] $*"; }

/bin/python3 scripts/extract_best_cfgs_from_matrix.py "${MATRIX_CSV}" --metric miss_ratio --out "${BEST_CFGS_CSV}"

trace_path() {
  case "$1" in
    1063) echo "data/TencentCBS/1063.oracleGeneral.zst";;
    meta_reag) echo "data/MetaCDN/meta_reag.oracleGeneral.zst";;
    wiki_2019t) echo "data/WikiCDN/wiki_2019t.oracleGeneral.zst";;
    *) echo "";;
  esac
}

COMBINED_PENALTY_CSV="${OUT_ROOT}/combined_penalty_sweep_summary.csv"
# Will be generated after per-trace summaries exist.

# Build once with penalty compiled in (and default state macros = all 0).
# We force includes to 0 to match the base best-config runs.
log "[build] building cachesim with LOH_ENABLE_PENALTY=1 (once)"
export LOH_ENABLE_PENALTY=1
export LOH_INCLUDE_HIT_MISS_FEATURES=0
export LOH_INCLUDE_CACHE_FEATURES=0
export LOH_INCLUDE_CANDIDATE_FEATURES=0
export LOH_INCLUDE_TOPK_CANDIDATE_FEATURES=0
export LOH_INCLUDE_AVGTOPK_CANDIDATE_FEATURES=0
export LOH_INCLUDE_REQUEST=0
bash scripts/debug.sh -c >/dev/null

# Generate penalty configs (two-stage) into each trace out_dir/configs.txt

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

  read -r base_mode base_comp base_irt base_soft base_signs < <(
    /bin/python3 -c 'import pandas as pd,sys
p=sys.argv[1]; t=sys.argv[2]
df=pd.read_csv(p)
row=df[df["trace"]==t].iloc[0]
print(row["mode"], int(row["LOH_SCORE_USE_COMPOUND"]), int(row["LOH_SCORE_USE_IRT"]), int(row["LOH_USE_SOFTMAX"]), int(row["LOH_USE_HEURISTIC_SIGNS"]))
' "${BEST_CFGS_CSV}" "${trace}"
  )

  sweep_id="${TS}__${trace}"
  out_dir="${OUT_ROOT}/${trace}"
  mkdir -p "${out_dir}"
  configs_file="${out_dir}/configs.txt"

  log "===== TRACE=${trace} base=${base_mode} softmax=${base_soft} signs=${base_signs} ====="

  # Common per-run flags: keep LOH_ENABLE_PENALTY=1 always (compiled in and enabled).
  common="LOH_PARALLEL_SAFE=1 LOH_SKIP_PIP_INSTALL=1 LOH_SKIP_BUILD=1 LOH_DEBUG_LEVEL=1 CACHESIM_VERBOSE=0 CACHESIM_NUM_REQ=${CACHESIM_NUM_REQ}"
  common+=" LOH_RL_ALGO=SAC LOH_ACTION_SCALE=1.0"
  common+=" LOH_SCORE_USE_COMPOUND=${base_comp} LOH_SCORE_USE_IRT=${base_irt} LOH_USE_SOFTMAX=${base_soft} LOH_USE_HEURISTIC_SIGNS=${base_signs}"
  # Pin state macros to 0 to match the build above and avoid accidental mismatch.
  common+=" LOH_INCLUDE_HIT_MISS_FEATURES=0 LOH_INCLUDE_CACHE_FEATURES=0 LOH_INCLUDE_CANDIDATE_FEATURES=0"
  common+=" LOH_INCLUDE_TOPK_CANDIDATE_FEATURES=0 LOH_INCLUDE_AVGTOPK_CANDIDATE_FEATURES=0 LOH_INCLUDE_REQUEST=0"

  {
    echo "# Auto-generated: ${sweep_id}"
    echo "# Two-stage penalty sweep: (A) main grid, (B) one-at-a-time secondary knobs"
    echo ""

    # Baseline: penalty compiled+enabled, but reward does NOT use penalty.
    echo "${common} LOH_ENABLE_PENALTY=1 LOH_REWARD_USE_PENALTY=0"

    # Stage A: main grid
    scales=(reciprocal log survival binary)
    formulas_basic=(relative centered one_minus neg)
    formulas_net=(net net2)
    w_basic=(0.1 0.2 0.5 1.0)
    w_net=(1.0 2.0 3.0)

    fixed_secondary="LOH_PENALTY_CUTOFF=0 LOH_PENALTY_DMAX=400000 LOH_PENALTY_EMPTY_AS_GOOD=1 LOH_PENALTY_REFINE_ON_LATE=1 LOH_PENALTY_NO_EVICT_REWARD=keep LOH_PENALTY_BASELINE_DECAY=0.99"
    fixed_survival="LOH_SURVIVAL_BINS=64 LOH_SURVIVAL_QUANTILE=0.99 LOH_SURVIVAL_MINCOUNT=1000"
    fixed_net="LOH_PENALTY_NET_GOOD_SCALE=1.0 LOH_PENALTY_NET_PENALTY_SCALE=1.0"

    for scale in "${scales[@]}"; do
      for form in "${formulas_basic[@]}"; do
        for w in "${w_basic[@]}"; do
          echo "${common} LOH_ENABLE_PENALTY=1 LOH_REWARD_USE_PENALTY=1 LOH_PENALTY_SCALE=${scale} LOH_PENALTY_REWARD_FORMULA=${form} LOH_REWARD_W_PENALTY=${w} ${fixed_secondary} ${fixed_survival} ${fixed_net}"
        done
      done
      for form in "${formulas_net[@]}"; do
        for w in "${w_net[@]}"; do
          echo "${common} LOH_ENABLE_PENALTY=1 LOH_REWARD_USE_PENALTY=1 LOH_PENALTY_SCALE=${scale} LOH_PENALTY_REWARD_FORMULA=${form} LOH_REWARD_W_PENALTY=${w} ${fixed_secondary} ${fixed_survival} ${fixed_net}"
        done
      done
    done

    # Stage B: one-at-a-time secondary knobs (cover all penalty params without exploding)
    base_pen="${common} LOH_ENABLE_PENALTY=1 LOH_REWARD_USE_PENALTY=1 LOH_PENALTY_SCALE=log LOH_PENALTY_REWARD_FORMULA=centered LOH_REWARD_W_PENALTY=1.0 ${fixed_secondary} ${fixed_survival} ${fixed_net}"

    # cutoff
    for cutoff in 0 500 2000 10000; do
      echo "${base_pen} LOH_PENALTY_CUTOFF=${cutoff}"
    done
    # dmax
    for dmax in 50000 200000 400000; do
      echo "${base_pen} LOH_PENALTY_DMAX=${dmax}"
    done
    # empty_as_good / refine_on_late / no_evict_reward / baseline_decay
    for v in 0 1; do echo "${base_pen} LOH_PENALTY_EMPTY_AS_GOOD=${v}"; done
    for v in 0 1; do echo "${base_pen} LOH_PENALTY_REFINE_ON_LATE=${v}"; done
    for p in keep zero; do echo "${base_pen} LOH_PENALTY_NO_EVICT_REWARD=${p}"; done
    for d in 0.95 0.99 0.995; do echo "${base_pen} LOH_PENALTY_BASELINE_DECAY=${d}"; done

    # survival parameters (only meaningful if scale=survival)
    base_surv="${base_pen} LOH_PENALTY_SCALE=survival"
    for q in 0.95 0.99; do echo "${base_surv} LOH_SURVIVAL_QUANTILE=${q}"; done
    for b in 32 64; do echo "${base_surv} LOH_SURVIVAL_BINS=${b}"; done
    for m in 500 1000; do echo "${base_surv} LOH_SURVIVAL_MINCOUNT=${m}"; done

    # net scales (only meaningful for net/net2)
    for form in net net2; do
      base_net="${base_pen} LOH_PENALTY_REWARD_FORMULA=${form}"
      for s in 0.5 1.0 2.0; do echo "${base_net} LOH_PENALTY_NET_GOOD_SCALE=${s}"; done
      for s in 0.5 1.0 2.0; do echo "${base_net} LOH_PENALTY_NET_PENALTY_SCALE=${s}"; done
    done

  } > "${configs_file}"

  log "[run] sweep_id=${sweep_id} configs=$(wc -l < "${configs_file}")"

  SWEEP_ID="${sweep_id}" SWEEP_OUTDIR="${out_dir}" \
    SWEEP_REPEATS=1 SEED_BASE=0 \
    bash scripts/sweep_loh_rl_sb3.sh "${configs_file}" "${tf}" "${CACHE_RATIO}" >/dev/null

  log "[analyze] AC report"
  /bin/python3 scripts/analyze_ac_reward_signal.py \
    "ac_sb3_${sweep_id}_*.log" \
    --report-md "${out_dir}/ac_reward_penalty_report.md" \
    --progress-every 5 >/dev/null

  log "[summarize] merged summary"
  /bin/python3 scripts/summarize_penalty_sweep_results.py \
    --results "${out_dir}/results.csv" \
    --ac-report "${out_dir}/ac_reward_penalty_report.md" \
    --out-csv "${out_dir}/penalty_sweep_summary.csv" \
    --out-md "${out_dir}/penalty_sweep_summary.md" >/dev/null

done

# Merge per-trace summaries into one combined CSV (only for traces we ran)
inputs=()
for tdir in "${OUT_ROOT}"/*; do
  [[ -d "${tdir}" ]] || continue
  t=$(basename "${tdir}")
  if [[ -f "${tdir}/penalty_sweep_summary.csv" ]]; then
    inputs+=("--input" "${t}" "${tdir}/penalty_sweep_summary.csv")
  fi
done

if [[ ${#inputs[@]} -gt 0 ]]; then
  /bin/python3 scripts/merge_csv_with_trace_column.py --out "${COMBINED_PENALTY_CSV}" "${inputs[@]}" >/dev/null
  log "Done. Combined penalty summary: ${COMBINED_PENALTY_CSV}"
else
  log "No per-trace penalty summaries found under ${OUT_ROOT}"
fi
