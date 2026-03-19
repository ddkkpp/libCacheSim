#!/usr/bin/env bash
set -u

ROOT_DIR=$(cd "$(dirname "$0")/../.." && pwd)
cd "$ROOT_DIR"

OUT_DIR="tmp/td3_ex0_retest_0318"
mkdir -p "$OUT_DIR"

REQS="${REQS:-3000000}"
CACHE_SIZE="${CACHE_SIZE:-0.1}"
SEED="${SEED:-20260318}"
RUN_TAG="${RUN_TAG:-run1}"

TRACES=(
	"1063|data/TencentCBS/1063.oracleGeneral.zst"
	"wiki|data/WikiCDN/wiki_2019t.oracleGeneral.zst"
	"meta|data/MetaCDN/meta_reag.oracleGeneral.zst"
)

RUNNER_LOG="$OUT_DIR/${RUN_TAG}_runner.log"
CSV_PATH="$OUT_DIR/${RUN_TAG}_results.csv"

if [ ! -f "$CSV_PATH" ]; then
	cat > "$CSV_PATH" <<'CSV'
run_tag,trace,seed,exclude_recent_steps,final_mr,final_bmr,final_mqps,log_path,rc
CSV
fi

extract_final() {
	local log_path="$1"
	awk '
		/LOH-.*cache size/ {
			mr=""; bmr=""; mqps="";
			if (match($0, /miss ratio [0-9]+\.[0-9]+/)) mr = substr($0, RSTART + 11, RLENGTH - 11);
			if (match($0, /byte miss ratio [0-9]+\.[0-9]+/)) bmr = substr($0, RSTART + 16, RLENGTH - 16);
			if (match($0, /throughput [0-9]+\.[0-9]+ MQPS/)) mqps = substr($0, RSTART + 11, RLENGTH - 16);
			if (mr != "" && bmr != "" && mqps != "") last = mr "," bmr "," mqps;
		}
		END { if (last != "") print last; }
	' "$log_path"
}

echo "[start] run_tag=${RUN_TAG} seed=${SEED} reqs=${REQS}" >> "$RUNNER_LOG"

for t in "${TRACES[@]}"; do
	IFS='|' read -r trace_name trace_path <<< "$t"
	stamp="$(date +%m%d_%H%M%S)"
	case_name="${trace_name}_TD3_ex0_cache01_${RUN_TAG}_${stamp}"
	log_path="$OUT_DIR/${case_name}.log"
	rc=0

	shm_key=$(printf "%s|%s|%s|%s|%s" "$trace_name" "TD3" "0" "$CACHE_SIZE" "${SEED}_${RUN_TAG}_${stamp}" | cksum | awk '{print $1}')
	rm -f "/dev/shm/loh_ac_${shm_key}" "/dev/shm/sem.loh_ac_ready_${shm_key}" "/dev/shm/sem.loh_ac_ack_${shm_key}" || true

	echo "[case-start] run_tag=${RUN_TAG} trace=${trace_name} log=${log_path}" >> "$RUNNER_LOG"
	(
		export LOH_SHM_KEY="$shm_key"
		export LOH_RL_ALGO="TD3"
		export LOH_EXCLUDE_RECENT_STEPS="0"
		export LOH_SEED="$SEED"
		export CACHESIM_NUM_REQ="$REQS"
		export LOH_PARALLEL_SAFE=1
		export LOH_ENABLE_SEMAPHORE=1
		export LOH_SEM_TIMEOUT_S=1.0
		export LOH_WAIT_NEWSTATE_MAX_CONSEC_TIMEOUTS=1800
		export LOH_WAIT_NEWSTATE_IDLE_S=1800
		export LOH_BUILD_RELEASE=1
		export LOH_SKIP_BUILD=1
		export LOH_SKIP_PIP_INSTALL=1
		export LOH_PERF_PROFILING=0
		export LOH_DEBUG_LEVEL=1
		export LOH_ENABLE_RL=1
		export LOH_SCORE_USE_COMPOUND=1
		export LOH_SCORE_USE_IRT=0
		export LOH_RANDOM_CANDIDATES=96
		export LOH_STRUCTURED_CANDIDATES=96
		export LOH_WAIT_MODE=nonblocked
		export LOH_ASYNC_TRAIN=1
		export LOH_MISS_RATIO_WEIGHT=1.0
		export LOH_INCLUDE_WEIGHTS_IN_OBS=1
		export LOH_ADAPTIVE_BUDGET=1
		export LOH_USE_SCORE_REBALANCE=0
		export LOH_FEATURE_UNIFIED_FORMULA=0
		export LOH_FEATURE_IDENTITY=0
		export LOH_FEATURE_LOG1P=1
		export LOH_FEATURE_LOG1P_RECIPROCAL=0
		export LOH_ENABLE_FEATURE_NORMALIZATION=0
		export LOH_ENABLE_ADAPTIVE_FEATURE_NORMALIZATION=1
		export LOH_ADAPTIVE_NORM_LO_Q=0.0
		export LOH_ADAPTIVE_NORM_HI_Q=1.0
		export LOH_ADAPTIVE_NORM_WARMUP=0
		export LOH_ADAPTIVE_NORM_TRANSFORM_QUANTILE=0
		export LOH_INCLUDE_HIT_MISS_FEATURES=0
		export RUN_TIMESTAMP="$(date +%m%d_%H%M%S)_${case_name}_$(date +%s)"
		bash scripts/test_loh_rl_sb3.sh "$trace_path" "$CACHE_SIZE"
	) > "$log_path" 2>&1 || rc=$?

	fin=$(extract_final "$log_path" || true)
	fmr="NA"
	fbmr="NA"
	fmqps="NA"
	if [ -n "$fin" ]; then
		fmr="$(echo "$fin" | cut -d',' -f1)"
		fbmr="$(echo "$fin" | cut -d',' -f2)"
		fmqps="$(echo "$fin" | cut -d',' -f3)"
	fi

	echo "${RUN_TAG},${trace_name},${SEED},0,${fmr},${fbmr},${fmqps},${log_path},${rc}" >> "$CSV_PATH"
	echo "[case-done] run_tag=${RUN_TAG} trace=${trace_name} rc=${rc} final_mr=${fmr} final_bmr=${fbmr} final_mqps=${fmqps}" >> "$RUNNER_LOG"
done

echo "[finished] run_tag=${RUN_TAG}" >> "$RUNNER_LOG"
