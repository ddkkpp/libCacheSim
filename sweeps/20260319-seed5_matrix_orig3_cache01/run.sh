#!/usr/bin/env bash
set -u

ROOT_DIR=$(cd "$(dirname "$0")/../.." && pwd)
cd "$ROOT_DIR"

OUT_DIR="${OUT_DIR:-tmp/20260319-seed5_matrix_orig3_cache01}"
RESULTS_CSV="$OUT_DIR/results.csv"
RUNNER_LOG="$OUT_DIR/runner.log"
DOC_PATH="docs/20260317-FULL_EXPERIMENT_RESULTS.md"
SUMMARY_PY="sweeps/20260319-seed5_matrix_orig3_cache01/summarize_to_doc.py"
PARALLEL="${PARALLEL:-24}"
CACHE_SIZE="0.1"

# 某些环境下 cachesim 依赖 libxgboost.so.3 位于 /usr/local/lib，默认补到运行时搜索路径。
LOH_EXTRA_LD_LIBRARY_PATH="${LOH_EXTRA_LD_LIBRARY_PATH:-/usr/local/lib}"

mkdir -p "$OUT_DIR"

if [ ! -f "$RESULTS_CSV" ]; then
cat > "$RESULTS_CSV" <<'CSV'
scenario,variant,seed,trace,status,rc,final_mr,final_bmr,final_mqps,overrides,log_path
CSV
fi

echo "[start] seed5 matrix sweep on orig3 cache=0.1 parallel=${PARALLEL}" >> "$RUNNER_LOG"

if [ "${SKIP_PREBUILD:-1}" = "1" ]; then
  echo "[prebuild] skipped by SKIP_PREBUILD=1" >> "$RUNNER_LOG"
else
  echo "[prebuild] force release + LOH_INCLUDE_HIT_MISS_FEATURES=0" >> "$RUNNER_LOG"
  (
    export LOH_BUILD_RELEASE=1
    export LOH_INCLUDE_HIT_MISS_FEATURES=0
    export LOH_SKIP_BUILD=0
    bash scripts/debug.sh -r -c
  ) >> "$OUT_DIR/prebuild.log" 2>&1 || {
    echo "[prebuild] failed, see $OUT_DIR/prebuild.log" >> "$RUNNER_LOG"
    exit 1
  }
  echo "[prebuild] done" >> "$RUNNER_LOG"
fi

COMMON_ENV=(
  "CACHESIM_NUM_REQ=0"
  "LOH_PARALLEL_SAFE=1"
  "LOH_ENABLE_SEMAPHORE=1"
  "LOH_SEM_TIMEOUT_S=1.0"
  "LOH_WAIT_NEWSTATE_MAX_CONSEC_TIMEOUTS=1800"
  "LOH_WAIT_NEWSTATE_IDLE_S=1800"
  "LOH_BUILD_RELEASE=1"
  "LOH_SKIP_BUILD=1"
  "LOH_SKIP_PIP_INSTALL=1"
  "LOH_PERF_PROFILING=0"
  "LOH_DEBUG_LEVEL=0"
  "LOH_ENABLE_RL=1"
  "LOH_SCORE_USE_COMPOUND=1"
  "LOH_SCORE_USE_IRT=0"
  "LOH_RANDOM_CANDIDATES=96"
  "LOH_STRUCTURED_CANDIDATES=96"
  "LOH_WAIT_MODE=nonblocked"
  "LOH_ASYNC_TRAIN=1"
  "LOH_MISS_RATIO_WEIGHT=1.0"
  "LOH_INCLUDE_WEIGHTS_IN_OBS=0"
  "LOH_ADAPTIVE_BUDGET=1"
  "LOH_USE_SCORE_REBALANCE=0"
  "LOH_FEATURE_UNIFIED_FORMULA=0"
  "LOH_FEATURE_IDENTITY=0"
  "LOH_FEATURE_LOG1P=1"
  "LOH_FEATURE_LOG1P_RECIPROCAL=0"
  "LOH_ENABLE_FEATURE_NORMALIZATION=0"
  "LOH_ENABLE_ADAPTIVE_FEATURE_NORMALIZATION=1"
  "LOH_ADAPTIVE_NORM_LO_Q=0.0"
  "LOH_ADAPTIVE_NORM_HI_Q=1.0"
  "LOH_ADAPTIVE_NORM_WARMUP=0"
  "LOH_ADAPTIVE_NORM_TRANSFORM_QUANTILE=0"
  "LOH_INCLUDE_HIT_MISS_FEATURES=0"
)

TRACE_1063_PATH="${TRACE_1063_PATH:-/mnt/serverpool/dingkp_trace/tencentBlock/v2/else/tencentBlock_1063.oracleGeneral.zst}"
TRACE_WIKI_PATH="${TRACE_WIKI_PATH:-/mnt/serverpool/dingkp_trace/wiki/wiki_2019t.oracleGeneral.zst}"
TRACE_META_PATH="${TRACE_META_PATH:-/mnt/serverpool/dingkp_trace/metaCDN/meta_reag.oracleGeneral.zst}"

TASKS=(
  "1063|${TRACE_1063_PATH}"
  "wiki|${TRACE_WIKI_PATH}"
  "meta|${TRACE_META_PATH}"
)

verify_traces_exist() {
  local ok=1
  for t in "${TASKS[@]}"; do
    IFS='|' read -r trace_name trace_path <<< "$t"
    if [ ! -f "$trace_path" ]; then
      echo "[trace-missing] trace=${trace_name} path=${trace_path}" >> "$RUNNER_LOG"
      ok=0
    fi
  done

  if [ "$ok" -ne 1 ]; then
    echo "[trace-check] missing trace files; set TRACE_1063_PATH/TRACE_WIKI_PATH/TRACE_META_PATH and rerun" >> "$RUNNER_LOG"
    return 1
  fi

  return 0
}

SEEDS=(42 3407 114514 20260318 20260319)
RAND_GRID=(64 96 128)
STRUCT_GRID=(64 96 128)
MISS_WEIGHTS=(0.0 0.1 0.2 0.3 0.4 0.5 0.6 0.7 0.8 0.9 1.0)
RL_ALGOS=(TD3 DDPG DQN TQC A2C PPO_LSTM)

# path|reward_mode|use_miss|miss_mode|use_trend|trend_mode
REWARD_PATHS=(
  "abs_miss_neg|absolute|1|neg|0|slope"
  "abs_miss_improve|absolute|1|improve|0|slope"
  "abs_trend_slope|absolute|0|neg|1|slope"
  "abs_trend_delta|absolute|0|neg|1|delta"
  "abs_miss_neg_trend_slope|absolute|1|neg|1|slope"
  "abs_miss_neg_trend_delta|absolute|1|neg|1|delta"
  "abs_miss_improve_trend_slope|absolute|1|improve|1|slope"
  "abs_miss_improve_trend_delta|absolute|1|improve|1|delta"
  "delta_only|delta|0|neg|0|slope"
)

# 每个条目格式: scenario|variant|overrides(以 ; 分隔 key=value)
CASES=()

add_case() {
  local scenario="$1"
  local variant="$2"
  local overrides="$3"
  CASES+=("${scenario}|${variant}|${overrides}")
}

get_override_value() {
  local overrides="$1"
  local key="$2"
  local default_val="$3"

  if [ -z "$overrides" ]; then
    echo "$default_val"
    return 0
  fi

  IFS=';' read -ra kvs <<< "$overrides"
  for kv in "${kvs[@]}"; do
    [ -z "$kv" ] && continue
    local k="${kv%%=*}"
    local v="${kv#*=}"
    if [ "$k" = "$key" ]; then
      echo "$v"
      return 0
    fi
  done

  echo "$default_val"
}

get_target_hitmiss() {
  local overrides="$1"
  get_override_value "$overrides" "LOH_INCLUDE_HIT_MISS_FEATURES" "0"
}

ensure_build_for_hitmiss() {
  local hitmiss="$1"
  local marker="$OUT_DIR/build_hitmiss_${hitmiss}.ok"
  local build_log="$OUT_DIR/rebuild_hitmiss_${hitmiss}.log"

  [ -f "$marker" ] && return 0

  (
    flock 9

    [ -f "$marker" ] && exit 0

    echo "[rebuild] start LOH_INCLUDE_HIT_MISS_FEATURES=${hitmiss}" >> "$RUNNER_LOG"
    (
      export LOH_BUILD_RELEASE=1
      export LOH_INCLUDE_HIT_MISS_FEATURES="$hitmiss"
      export LOH_SKIP_BUILD=0
      bash scripts/debug.sh -r
    ) >> "$build_log" 2>&1 || {
      echo "[rebuild] failed LOH_INCLUDE_HIT_MISS_FEATURES=${hitmiss}, see $build_log" >> "$RUNNER_LOG"
      exit 1
    }

    touch "$marker"
    echo "[rebuild] done LOH_INCLUDE_HIT_MISS_FEATURES=${hitmiss}" >> "$RUNNER_LOG"
  ) 9>"$OUT_DIR/rebuild.lock"
}

validate_config_matches_log() {
  local overrides="$1"
  local target_hitmiss="$2"
  local log_path="$3"
  local mismatch=0

  if ! grep -Fq "[config] LOH_INCLUDE_HIT_MISS_FEATURES=${target_hitmiss}" "$log_path"; then
    echo "[config-mismatch] key=LOH_INCLUDE_HIT_MISS_FEATURES planned=${target_hitmiss} log=${log_path}" >> "$RUNNER_LOG"
    mismatch=1
  fi

  if [ -n "$overrides" ]; then
    IFS=';' read -ra kvs <<< "$overrides"
    for kv in "${kvs[@]}"; do
      [ -z "$kv" ] && continue
      local k="${kv%%=*}"
      local v="${kv#*=}"

      case "$k" in
        LOH_RL_ALGO|LOH_MISS_RATIO_WEIGHT|LOH_RANDOM_CANDIDATES|LOH_STRUCTURED_CANDIDATES|LOH_INCLUDE_WEIGHTS_IN_OBS|LOH_ADAPTIVE_BUDGET|LOH_FEATURE_IDENTITY|LOH_FEATURE_LOG1P|LOH_ENABLE_FEATURE_NORMALIZATION|LOH_ENABLE_ADAPTIVE_FEATURE_NORMALIZATION|LOH_ADAPTIVE_NORM_TRANSFORM_QUANTILE)
          if ! grep -Fq "[config] ${k}=${v}" "$log_path"; then
            echo "[config-mismatch] key=${k} planned=${v} log=${log_path}" >> "$RUNNER_LOG"
            mismatch=1
          fi
          ;;
      esac
    done
  fi

  return "$mismatch"
}

# 1) 不改变配置
add_case "S1_BASELINE" "default" ""

# 2) LOH_ADAPTIVE_BUDGET=0
add_case "S2_ADAPTIVE_BUDGET" "ab0" "LOH_ADAPTIVE_BUDGET=0"

# 3) 候选网格（96,96 邻域）
for r in "${RAND_GRID[@]}"; do
  for s in "${STRUCT_GRID[@]}"; do
    add_case "S3_CAND_GRID" "r${r}_s${s}" "LOH_RANDOM_CANDIDATES=${r};LOH_STRUCTURED_CANDIDATES=${s}"
  done
done

# 4) LOH_MISS_RATIO_WEIGHT 阶梯 0.1
for w in "${MISS_WEIGHTS[@]}"; do
  wtag=$(echo "$w" | tr '.' 'p')
  add_case "S4_MRW_SWEEP" "mrw${wtag}" "LOH_MISS_RATIO_WEIGHT=${w}"
done

# 5) reward path 9 组
for p in "${REWARD_PATHS[@]}"; do
  IFS='|' read -r path_name reward_mode use_miss miss_mode use_trend trend_mode <<< "$p"
  add_case "S5_REWARD_PATH" "$path_name" "LOH_REWARD_MODE=${reward_mode};LOH_REWARD_USE_MISSRATIO=${use_miss};LOH_MISS_COMPONENT=${miss_mode};LOH_REWARD_USE_MISSRATIOTREND=${use_trend};LOH_MISSRATIOTREND_MODE=${trend_mode};LOH_ENABLE_PENALTY=0"
done

# 6) RL algo 切换
for algo in "${RL_ALGOS[@]}"; do
  add_case "S6_RL_ALGO" "${algo}" "LOH_RL_ALGO=${algo}"
done

# 7) wobs/hitmiss 三种组合
add_case "S7_OBS_HITMISS" "w1_h0" "LOH_INCLUDE_WEIGHTS_IN_OBS=1;LOH_INCLUDE_HIT_MISS_FEATURES=0"
add_case "S7_OBS_HITMISS" "w0_h1" "LOH_INCLUDE_WEIGHTS_IN_OBS=0;LOH_INCLUDE_HIT_MISS_FEATURES=1"
add_case "S7_OBS_HITMISS" "w1_h1" "LOH_INCLUDE_WEIGHTS_IN_OBS=1;LOH_INCLUDE_HIT_MISS_FEATURES=1"

# 8) 三种特征模式
add_case "S8_FEATURE_MODE" "a_identity_no_norm" "LOH_FEATURE_IDENTITY=1;LOH_FEATURE_LOG1P=0;LOH_ENABLE_FEATURE_NORMALIZATION=0;LOH_ENABLE_ADAPTIVE_FEATURE_NORMALIZATION=0"
add_case "S8_FEATURE_MODE" "b_identity_adaptive" "LOH_FEATURE_IDENTITY=1;LOH_FEATURE_LOG1P=0;LOH_ENABLE_FEATURE_NORMALIZATION=0;LOH_ENABLE_ADAPTIVE_FEATURE_NORMALIZATION=1"
add_case "S8_FEATURE_MODE" "c_log1p_no_adaptive" "LOH_FEATURE_IDENTITY=0;LOH_FEATURE_LOG1P=1;LOH_ENABLE_FEATURE_NORMALIZATION=0;LOH_ENABLE_ADAPTIVE_FEATURE_NORMALIZATION=0"

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

already_done() {
  local scenario="$1"
  local variant="$2"
  local seed="$3"
  local trace_name="$4"
  grep -q "^${scenario},${variant},${seed},${trace_name},ok," "$RESULTS_CSV"
}

run_one() {
  local scenario="$1"
  local variant="$2"
  local overrides="$3"
  local seed="$4"
  local trace_name="$5"
  local trace_path="$6"
  local target_hitmiss="$7"

  if already_done "$scenario" "$variant" "$seed" "$trace_name"; then
    echo "[resume-skip] scenario=${scenario} variant=${variant} seed=${seed} trace=${trace_name}" >> "$RUNNER_LOG"
    return 0
  fi

  local case_name="${trace_name}_${scenario}_${variant}_s${seed}_cache01"
  local case_stamp
  case_stamp="$(date +%m%d_%H%M%S)"
  local log_path="$OUT_DIR/${case_name}_${case_stamp}.log"
  local shm_key rc=0

  shm_key=$(printf "%s|%s|%s|%s|%s|%s" "$scenario" "$variant" "$seed" "$trace_name" "$CACHE_SIZE" "$(date +%s%N)" | cksum | awk '{print $1}')
  rm -f "/dev/shm/loh_ac_${shm_key}" "/dev/shm/sem.loh_ac_ready_${shm_key}" "/dev/shm/sem.loh_ac_ack_${shm_key}" || true

  echo "[case-start] scenario=${scenario} variant=${variant} seed=${seed} trace=${trace_name}" >> "$RUNNER_LOG"
  (
    export LOH_SHM_KEY="$shm_key"
    export LOH_SEED="$seed"
    export RUN_TIMESTAMP="$(date +%m%d_%H%M%S)_${case_name}_$(date +%s)"
    export LD_LIBRARY_PATH="${LOH_EXTRA_LD_LIBRARY_PATH}:${LD_LIBRARY_PATH:-}"

    for kv in "${COMMON_ENV[@]}"; do
      export "$kv"
    done

    if [ -n "$overrides" ]; then
      IFS=';' read -ra kvs <<< "$overrides"
      for kv in "${kvs[@]}"; do
        [ -n "$kv" ] && export "$kv"
      done
    fi

    bash scripts/test_loh_rl_sb3.sh "$trace_path" "$CACHE_SIZE"
  ) > "$log_path" 2>&1 || rc=$?

  local fin fmr="NA" fbmr="NA" fmqps="NA" status="ok"
  fin=$(extract_final "$log_path" || true)
  if [ -n "$fin" ]; then
    fmr="$(echo "$fin" | cut -d',' -f1)"
    fbmr="$(echo "$fin" | cut -d',' -f2)"
    fmqps="$(echo "$fin" | cut -d',' -f3)"
  fi

  [ "$rc" -ne 0 ] && status="failed"

  if ! validate_config_matches_log "$overrides" "$target_hitmiss" "$log_path"; then
    status="failed"
    if [ "$rc" -eq 0 ]; then
      rc=97
    fi
  fi

  echo "${scenario},${variant},${seed},${trace_name},${status},${rc},${fmr},${fbmr},${fmqps},${overrides},${log_path}" >> "$RESULTS_CSV"
  echo "[case-done] scenario=${scenario} variant=${variant} seed=${seed} trace=${trace_name} status=${status} rc=${rc} final_mr=${fmr} final_bmr=${fbmr} final_mqps=${fmqps}" >> "$RUNNER_LOG"
}

run_case_group() {
  local target_hitmiss="$1"
  local running=0

  ensure_build_for_hitmiss "$target_hitmiss" || exit 1

  for c in "${CASES[@]}"; do
    IFS='|' read -r scenario variant overrides <<< "$c"
    local case_hitmiss
    case_hitmiss=$(get_target_hitmiss "$overrides")

    [ "$case_hitmiss" != "$target_hitmiss" ] && continue

    for seed in "${SEEDS[@]}"; do
      for t in "${TASKS[@]}"; do
        IFS='|' read -r trace_name trace_path <<< "$t"

        run_one "$scenario" "$variant" "$overrides" "$seed" "$trace_name" "$trace_path" "$target_hitmiss" &
        running=$((running + 1))
        echo "[queue] active=${running}/${PARALLEL} action=start hitmiss=${target_hitmiss} scenario=${scenario} variant=${variant} seed=${seed} trace=${trace_name}" >> "$RUNNER_LOG"

        if [ "$running" -ge "$PARALLEL" ]; then
          wait -n || true
          running=$((running - 1))
          echo "[queue] active=${running}/${PARALLEL} action=finish_one" >> "$RUNNER_LOG"
        fi
      done
    done
  done

  while [ "$running" -gt 0 ]; do
    wait -n || true
    running=$((running - 1))
    echo "[queue] active=${running}/${PARALLEL} action=finish_one" >> "$RUNNER_LOG"
  done
}

verify_traces_exist || exit 1

run_case_group "0"
run_case_group "1"

python3 "$SUMMARY_PY" \
  --results "$RESULTS_CSV" \
  --doc "$DOC_PATH" \
  >> "$OUT_DIR/doc_update.log" 2>&1 || true

echo "[finished] ${RESULTS_CSV}" >> "$RUNNER_LOG"
