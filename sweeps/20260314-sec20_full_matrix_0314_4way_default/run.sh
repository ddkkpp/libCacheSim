#!/usr/bin/env bash
set -uo pipefail

ROOT_DIR=$(cd "$(dirname "$0")/../.." && pwd)
cd "$ROOT_DIR"

OUT_DIR="tmp/sec20_full_matrix_0314_4way"
RESULTS_CSV="$OUT_DIR/results.csv"
RUNNER_LOG="$OUT_DIR/runner.log"
PARALLEL=4

# full trace
NUM_REQ=0
CACHE_SIZE=0.1

mkdir -p "$OUT_DIR"

echo "trace,formula,mode,status,rc,mr,bmr,log_path" > "$RESULTS_CSV"
echo "[start] sec20 full matrix run (parallel=${PARALLEL}, num_req=${NUM_REQ})" | tee "$RUNNER_LOG"

extract_metric_pair() {
	local log_path="$1"
	local mr=""
	local bmr=""

	mr=$(grep -E '^\[RESULT\] Obj Miss Ratio:' "$log_path" | tail -n 1 | awk '{print $5}' || true)
	bmr=$(grep -E '^\[RESULT\] Byte Miss Ratio:' "$log_path" | tail -n 1 | awk '{print $5}' || true)

	if [ -z "${mr}" ] || [ -z "${bmr}" ]; then
		local last_line
		last_line=$(grep -E 'miss ratio [0-9]+\.[0-9]+, byte miss ratio [0-9]+\.[0-9]+' "$log_path" | tail -n 1 || true)
		if [ -n "$last_line" ]; then
			mr=$(echo "$last_line" | sed -n 's/.*miss ratio \([0-9][0-9]*\.[0-9][0-9]*\), byte miss ratio.*/\1/p')
			bmr=$(echo "$last_line" | sed -n 's/.*byte miss ratio \([0-9][0-9]*\.[0-9][0-9]*\).*/\1/p')
		fi
	fi

	if [ -z "${mr}" ]; then mr="NA"; fi
	if [ -z "${bmr}" ]; then bmr="NA"; fi
	echo "${mr},${bmr}"
}

COMMON_ENV=(
	"CACHESIM_NUM_REQ=${NUM_REQ}"
	"LOH_PARALLEL_SAFE=1"
	"LOH_ENABLE_SEMAPHORE=1"
	"LOH_BUILD_RELEASE=1"
	"LOH_PERF_PROFILING=0"
	"LOH_DEBUG_LEVEL=0"
	"LOH_SCORE_USE_COMPOUND=1"
	"LOH_SCORE_USE_IRT=0"
	"LOH_RANDOM_CANDIDATES=96"
	"LOH_STRUCTURED_CANDIDATES=96"
	"LOH_WAIT_MODE=nonblocked"
	"LOH_ASYNC_TRAIN=1"
	"LOH_ENABLE_PENALTY=0"
	"LOH_MISS_RATIO_WEIGHT=1.0"
	"LOH_INCLUDE_WEIGHTS_IN_OBS=1"
	"LOH_ADAPTIVE_BUDGET=1"
	"LOH_USE_SCORE_REBALANCE=0"
	"LOH_ENABLE_RL=1"
	"LOH_SKIP_BUILD=0"
	"LOH_SKIP_PIP_INSTALL=1"
	"LOH_DISABLE_NEWSTATE_EARLY_EXIT=1"
	"LOH_WAIT_NEWSTATE_MAX_CONSEC_TIMEOUTS=1800"
	"LOH_WAIT_NEWSTATE_IDLE_S=1800"
)

CASES=(
	"1063|data/TencentCBS/1063.oracleGeneral.zst|log1p|LOH_FEATURE_LOG1P=1 LOH_FEATURE_LOG1P_RECIPROCAL=0"
	"wiki|data/WikiCDN/wiki_2019t.oracleGeneral.zst|log1p|LOH_FEATURE_LOG1P=1 LOH_FEATURE_LOG1P_RECIPROCAL=0"
	"wiki|data/WikiCDN/wiki_2019t.oracleGeneral.zst|reciprocal|LOH_FEATURE_LOG1P=0 LOH_FEATURE_LOG1P_RECIPROCAL=1"
	"meta|data/MetaCDN/meta_reag.oracleGeneral.zst|log1p|LOH_FEATURE_LOG1P=1 LOH_FEATURE_LOG1P_RECIPROCAL=0"
)

MODES=(
	"baseline|LOH_ENABLE_FEATURE_NORMALIZATION=0 LOH_ENABLE_ADAPTIVE_FEATURE_NORMALIZATION=0"
	"fixed_norm|LOH_ENABLE_FEATURE_NORMALIZATION=1 LOH_ENABLE_ADAPTIVE_FEATURE_NORMALIZATION=0"
	"adaptive_norm|LOH_ENABLE_FEATURE_NORMALIZATION=0 LOH_ENABLE_ADAPTIVE_FEATURE_NORMALIZATION=1 LOH_ADAPTIVE_NORM_LO_Q=0.01 LOH_ADAPTIVE_NORM_HI_Q=0.99 LOH_ADAPTIVE_NORM_WARMUP=4096"
)

run_one() {
	local trace_name="$1"
	local trace_path="$2"
	local formula_name="$3"
	local formula_envs="$4"
	local mode_name="$5"
	local mode_envs="$6"

	local case_name="${trace_name}_${formula_name}_${mode_name}"
	local log_path="$OUT_DIR/${case_name}.log"
	local shm_key
	shm_key=$(printf "%s|sec20full4|%s" "$case_name" "$OUT_DIR" | cksum | awk '{print $1}')

	rm -f "/dev/shm/loh_ac_${shm_key}" || true
	rm -f "/dev/shm/sem.loh_ac_ready_${shm_key}" || true
	rm -f "/dev/shm/sem.loh_ac_ack_${shm_key}" || true

	{
		echo "===== ${case_name} ====="
		echo "trace=${trace_path}"
		echo "cache=${CACHE_SIZE} num_req=${NUM_REQ}"
		echo "shm_key=${shm_key}"
		echo
	} > "$log_path"

	echo "[case-start] ${case_name}" >> "$RUNNER_LOG"

	local rc=0
	(
		set -uo pipefail
		export LOH_SHM_KEY="$shm_key"
		# Ensure per-case unique log names in test_loh_rl_sb3.sh (ac_sb3/cachesim_sb3).
		export RUN_TIMESTAMP="$(date +%m%d_%H%M%S)_${trace_name}_${formula_name}_${mode_name}_$$"
		for kv in "${COMMON_ENV[@]}"; do export "$kv"; done
		for kv in $formula_envs; do export "$kv"; done
		for kv in $mode_envs; do export "$kv"; done
		bash scripts/test_loh_rl_sb3.sh "$trace_path" "$CACHE_SIZE"
	) >> "$log_path" 2>&1 || rc=$?

	local mr bmr metrics status
	metrics=$(extract_metric_pair "$log_path")
	mr="${metrics%,*}"
	bmr="${metrics#*,}"
	if [ "$rc" -eq 0 ]; then
		status="ok"
	else
		status="failed"
	fi
	echo "${trace_name},${formula_name},${mode_name},${status},${rc},${mr},${bmr},${log_path}" >> "$RESULTS_CSV"
	echo "[case-done] ${case_name} status=${status} rc=${rc} mr=${mr} bmr=${bmr}" >> "$RUNNER_LOG"
	return 0
}

pids=()
case_recorded() {
	local trace_name="$1"
	local formula_name="$2"
	local mode_name="$3"
	grep -q "^${trace_name},${formula_name},${mode_name},ok," "$RESULTS_CSV" 2>/dev/null
}

start_case() {
	local case_def="$1"
	local mode_def="$2"
	IFS='|' read -r trace_name trace_path formula_name formula_envs <<< "$case_def"
	IFS='|' read -r mode_name mode_envs <<< "$mode_def"

	if case_recorded "$trace_name" "$formula_name" "$mode_name"; then
		echo "[case-skip] ${trace_name}_${formula_name}_${mode_name} already recorded" >> "$RUNNER_LOG"
		return 0
	fi

	run_one "$trace_name" "$trace_path" "$formula_name" "$formula_envs" "$mode_name" "$mode_envs" &
	pids+=("$!")
}

wait_one() {
	local pid="${pids[0]}"
	wait "$pid" || true
	pids=("${pids[@]:1}")
}

for case_def in "${CASES[@]}"; do
	for mode_def in "${MODES[@]}"; do
		while [ "${#pids[@]}" -ge "$PARALLEL" ]; do
			wait_one
		done
		start_case "$case_def" "$mode_def"
	done
done

while [ "${#pids[@]}" -gt 0 ]; do
	wait_one
done

echo "[finished] results at ${RESULTS_CSV}" >> "$RUNNER_LOG"
