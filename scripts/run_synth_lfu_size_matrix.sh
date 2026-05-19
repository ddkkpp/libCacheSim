#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_TAG="${RUN_TAG:-20260508-synth-lfu-size-4x4}"
OUT_DIR="${OUT_DIR:-${ROOT_DIR}/tmp/${RUN_TAG}}"
TRACE_DIR="${OUT_DIR}/traces"
LOG_DIR="${OUT_DIR}/logs"
RESULT_DIR="${OUT_DIR}/results"

CACHESIM_BIN="${CACHESIM_BIN:-${ROOT_DIR}/_build_rel/bin/cachesim}"
CACHE_SIZE="${CACHE_SIZE:-0.1}"
TRACE_TYPE_PARAMS="time-col=1,obj-id-col=2,obj-size-col=3,obj-id-is-num=1,has-header=false,delimiter=,"

# Keep default runtime search paths for libcmaes/xgboost/lightgbm.
LD_LIBRARY_PATH="/home/丁坤鹏/libcmaes/build/src:/usr/local/lib:${LD_LIBRARY_PATH:-}"
export LD_LIBRARY_PATH

mkdir -p "${TRACE_DIR}" "${LOG_DIR}" "${RESULT_DIR}"

if [[ ! -x "${CACHESIM_BIN}" ]]; then
  echo "[error] cachesim binary not found: ${CACHESIM_BIN}" >&2
  exit 1
fi

declare -A TRACE_SCRIPT
declare -A TRACE_PATH

TRACE_SCRIPT[lfu_zipf_heavy]="${ROOT_DIR}/scripts/gen_lfu_trace_zipf_heavy.py"
TRACE_SCRIPT[lfu_hotspot]="${ROOT_DIR}/scripts/gen_lfu_trace_hotspot.py"
TRACE_SCRIPT[size_twotier_extreme]="${ROOT_DIR}/scripts/gen_size_trace_twotier_extreme.py"
TRACE_SCRIPT[size_threetier_extreme]="${ROOT_DIR}/scripts/gen_size_trace_threetier_extreme.py"

TRACE_PATH[lfu_zipf_heavy]="${TRACE_DIR}/lfu_zipf_heavy_10m.csv"
TRACE_PATH[lfu_hotspot]="${TRACE_DIR}/lfu_hotspot_10m.csv"
TRACE_PATH[size_twotier_extreme]="${TRACE_DIR}/size_twotier_extreme_10m.csv"
TRACE_PATH[size_threetier_extreme]="${TRACE_DIR}/size_threetier_extreme_10m.csv"

TRACE_ORDER=(
  lfu_zipf_heavy
  lfu_hotspot
  size_twotier_extreme
  size_threetier_extreme
)

ALGO_ORDER=(LRU LFU Size LOH)

run_generate() {
  local trace_name="$1"
  local script_path="$2"
  local trace_path="$3"
  local log_path="${LOG_DIR}/generate_${trace_name}.log"

  echo "[generate] ${trace_name} -> ${trace_path}"
  python3 "${script_path}" "${trace_path}" >"${log_path}" 2>&1
}

run_eval() {
  local trace_name="$1"
  local trace_path="$2"
  local algo="$3"
  local log_path="${LOG_DIR}/eval_${trace_name}_${algo}.log"
  local result_path="${RESULT_DIR}/${trace_name}_${algo}.txt"
  local cmd=(
    "${CACHESIM_BIN}"
    "${trace_path}"
    csv
    "${algo}"
    "${CACHE_SIZE}"
    "--trace-type-params=${TRACE_TYPE_PARAMS}"
    -v 1
  )

  if [[ "${algo}" == "LOH" ]]; then
    cmd+=("--eviction-params=miss-ratio-weight=1.0")
  fi
  if [[ -n "${CACHESIM_NUM_REQ:-}" ]]; then
    cmd+=("--num-req=${CACHESIM_NUM_REQ}")
  fi

  echo "[eval] ${trace_name} ${algo}"
  "${cmd[@]}" >"${log_path}" 2>&1

  python3 - "${trace_name}" "${algo}" "${log_path}" >"${result_path}" <<'PY'
import re
import sys

trace_name, algo, log_path = sys.argv[1:4]
mr = "nan"
bmr = "nan"
with open(log_path, "r", encoding="utf-8", errors="replace") as handle:
    for line in handle:
        match = re.search(r"miss ratio\s+([0-9.]+), byte miss ratio\s+([0-9.]+)", line)
        if match:
            mr = match.group(1)
            bmr = match.group(2)
print(f"{trace_name}\t{algo}\t{mr}\t{bmr}")
PY
}

echo "[phase] generate traces"
gen_pids=()
for trace_name in "${TRACE_ORDER[@]}"; do
  run_generate "${trace_name}" "${TRACE_SCRIPT[${trace_name}]}" "${TRACE_PATH[${trace_name}]}" &
  gen_pids+=("$!")
done

for pid in "${gen_pids[@]}"; do
  wait "${pid}"
done

echo "[phase] evaluate algorithms"
eval_pids=()
for trace_name in "${TRACE_ORDER[@]}"; do
  for algo in "${ALGO_ORDER[@]}"; do
    run_eval "${trace_name}" "${TRACE_PATH[${trace_name}]}" "${algo}" &
    eval_pids+=("$!")
  done
done

for pid in "${eval_pids[@]}"; do
  wait "${pid}"
done

SUMMARY_PATH="${RESULT_DIR}/summary.tsv"
{
  echo -e "trace\talgo\tmr\tbmr"
  for trace_name in "${TRACE_ORDER[@]}"; do
    for algo in "${ALGO_ORDER[@]}"; do
      cat "${RESULT_DIR}/${trace_name}_${algo}.txt"
    done
  done
} >"${SUMMARY_PATH}"

echo "[done] out_dir=${OUT_DIR}"
echo "[done] summary=${SUMMARY_PATH}"
