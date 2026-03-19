#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

QUEUE_TAG="${1:-phase_ab_$(date +%m%d_%H%M%S)}"
QUEUE_ROOT="tmp/${QUEUE_TAG}"
LOG_DIR="${QUEUE_ROOT}/logs"
STATUS_DIR="${QUEUE_ROOT}/status"
mkdir -p "$LOG_DIR" "$STATUS_DIR"

ln -sfn "$QUEUE_TAG" tmp/phase_ab_latest

QUEUE_LOG="${QUEUE_ROOT}/queue.log"
RESULTS_CSV="${QUEUE_ROOT}/results.csv"
TASKS_TSV="${QUEUE_ROOT}/tasks.tsv"
CURRENT_TASK_FILE="${QUEUE_ROOT}/current_task.txt"
SUMMARY_FILE="${QUEUE_ROOT}/summary.txt"
LOCK_FILE="${QUEUE_ROOT}/queue.lock"

PHASE_AB_SIZE_LIST="${PHASE_AB_SIZE_LIST:-0.1,0.001}"
IFS=',' read -r -a PHASE_AB_SIZES <<< "$PHASE_AB_SIZE_LIST"
PHASE_AB_ORIGINAL_BASELINE_SIZE="${PHASE_AB_ORIGINAL_BASELINE_SIZE:-${PHASE_AB_SIZES[$((${#PHASE_AB_SIZES[@]} - 1))]}}"

TOTAL_CPUS="${PHASE_AB_TOTAL_CPUS_OVERRIDE:-$(nproc 2>/dev/null || echo 8)}"
CPU_RESERVE="${PHASE_AB_CPU_RESERVE:-4}"
MAX_PARALLEL_JOBS="${PHASE_AB_MAX_PARALLEL:-2}"
PYTHON_THREADS_PER_JOB="${PHASE_AB_PYTHON_THREADS:-1}"

AVAILABLE_CPUS=$(( TOTAL_CPUS - CPU_RESERVE ))
if [ "$AVAILABLE_CPUS" -lt 1 ]; then
  AVAILABLE_CPUS=1
fi
if [ "$MAX_PARALLEL_JOBS" -lt 1 ]; then
  MAX_PARALLEL_JOBS=1
fi
if [ "$MAX_PARALLEL_JOBS" -gt "$AVAILABLE_CPUS" ]; then
  MAX_PARALLEL_JOBS="$AVAILABLE_CPUS"
fi

DEFAULT_CACHESIM_THREADS=$(( AVAILABLE_CPUS / MAX_PARALLEL_JOBS ))
if [ "$DEFAULT_CACHESIM_THREADS" -lt 1 ]; then
  DEFAULT_CACHESIM_THREADS=1
fi
CACHESIM_THREADS_PER_JOB="${PHASE_AB_CACHESIM_THREADS_PER_JOB:-$DEFAULT_CACHESIM_THREADS}"

declare -a ACTIVE_PIDS=()

touch "$QUEUE_LOG"
touch "$LOCK_FILE"
if [ ! -f "$RESULTS_CSV" ]; then
  echo "task_id,phase,kind,trace,size,mode,weights_obs,algo,rc,result_line,log_file" > "$RESULTS_CSV"
fi
if [ ! -f "$TASKS_TSV" ]; then
  echo "task_id,phase,kind,trace,size,mode,weights_obs,algo" > "$TASKS_TSV"
fi

log() {
  local line
  line="[$(date '+%F %T')] $*"
  {
    flock 9
    printf '%s\n' "$line" >> "$QUEUE_LOG"
  } 9>>"$LOCK_FILE"
  printf '%s\n' "$line"
}

csv_escape() {
  local value="$1"
  value="${value//\"/\"\"}"
  printf '"%s"' "$value"
}

record_result() {
  local task_id="$1"
  local phase="$2"
  local kind="$3"
  local trace_name="$4"
  local size="$5"
  local mode="$6"
  local weights_obs="$7"
  local algo="$8"
  local rc="$9"
  local result_line="${10}"
  local log_file="${11}"
  {
    flock 9
    {
      csv_escape "$task_id"
      printf ','
      csv_escape "$phase"
      printf ','
      csv_escape "$kind"
      printf ','
      csv_escape "$trace_name"
      printf ','
      csv_escape "$size"
      printf ','
      csv_escape "$mode"
      printf ','
      csv_escape "$weights_obs"
      printf ','
      csv_escape "$algo"
      printf ','
      csv_escape "$rc"
      printf ','
      csv_escape "$result_line"
      printf ','
      csv_escape "$log_file"
      printf '\n'
    } >> "$RESULTS_CSV"
  } 9>>"$LOCK_FILE"
}

sanitize_size() {
  echo "$1" | tr '.' 'p'
}

register_task() {
  local task_id="$1"
  local phase="$2"
  local kind="$3"
  local trace_name="$4"
  local size="$5"
  local mode="$6"
  local weights_obs="$7"
  local algo="$8"
  if ! grep -q "^${task_id}," "$TASKS_TSV" 2>/dev/null; then
    printf '%s,%s,%s,%s,%s,%s,%s,%s\n' \
      "$task_id" "$phase" "$kind" "$trace_name" "$size" "$mode" "$weights_obs" "$algo" >> "$TASKS_TSV"
  fi
}

write_summary() {
  {
    flock 9
    write_summary_locked
  } 9>>"$LOCK_FILE"
}

write_summary_locked() {
  local total done failed running pending
  local current_tasks
  total=$(( $(wc -l < "$TASKS_TSV") - 1 ))
  done=$(find "$STATUS_DIR" -maxdepth 1 -name '*.done' | wc -l)
  failed=$(find "$STATUS_DIR" -maxdepth 1 -name '*.fail' | wc -l)
  running=$(find "$STATUS_DIR" -maxdepth 1 -name '*.running' | wc -l)
  pending=$(( total - done - failed - running ))
  current_tasks="$(find "$STATUS_DIR" -maxdepth 1 -name '*.running' -printf '%f\n' | sed 's/\.running$//' | sort | paste -sd',' -)"

  if [ -n "$current_tasks" ]; then
    printf '%s\n' "$current_tasks" > "$CURRENT_TASK_FILE"
  else
    rm -f "$CURRENT_TASK_FILE"
  fi

  {
    echo "queue_root=${QUEUE_ROOT}"
    echo "total=${total}"
    echo "done=${done}"
    echo "failed=${failed}"
    echo "running=${running}"
    echo "pending=${pending}"
    echo "updated_at=$(date '+%F %T')"
    echo "current=${current_tasks}"
  } > "$SUMMARY_FILE"
}

task_shm_key() {
  local task_id="$1"
  cksum <<< "${QUEUE_TAG}:${task_id}" | awk '{print $1}'
}

mark_task_running() {
  local task_id="$1"
  {
    flock 9
    rm -f "${STATUS_DIR}/${task_id}.fail"
    touch "${STATUS_DIR}/${task_id}.running"
    write_summary_locked
  } 9>>"$LOCK_FILE"
}

common_rl_env() {
  export LOH_WAIT_MODE=nonblocked
  export LOH_ENABLE_SEMAPHORE=1
  export LOH_SCORE_USE_COMPOUND=1
  export LOH_SCORE_USE_IRT=0
  export LOH_BUILD_RELEASE=1
  export LOH_SKIP_BUILD=1
  export LOH_SKIP_PIP_INSTALL=1
  export LOH_CACHESIM_BIN=_build_rel/bin/cachesim
  export LOH_ADAPTIVE_BUDGET=1
  export LOH_ASYNC_TRAIN=1
  export LOH_RANDOM_CANDIDATES=64
  export LOH_TAIL_SAMPLE=1
  export LOH_TAIL_SAMPLE_DECAY=0.99
  export LOH_ENABLE_PROFILING=0
  export LOH_DEBUG_LEVEL=0
  export CACHESIM_VERBOSE=0
  export CACHESIM_NUM_REQ=0
}

set_feature_mode() {
  local mode="$1"
  unset LOH_FEATURE_LOG1P LOH_FEATURE_LOG1P_RECIPROCAL
  case "$mode" in
    log1p)
      export LOH_FEATURE_LOG1P=1
      export LOH_FEATURE_LOG1P_RECIPROCAL=0
      ;;
    reciprocal)
      export LOH_FEATURE_LOG1P=0
      export LOH_FEATURE_LOG1P_RECIPROCAL=1
      ;;
    *)
      echo "unknown feature mode: $mode" >&2
      return 1
      ;;
  esac
}

latest_metric_line() {
  local log_file="$1"
  grep -E 'miss ratio .*byte miss ratio|MQPS|cache size' "$log_file" | tail -1 || true
}

finalize_task() {
  local task_id="$1"
  local rc="$2"
  {
    flock 9
    rm -f "${STATUS_DIR}/${task_id}.running"
    if [ "$rc" -eq 0 ]; then
      touch "${STATUS_DIR}/${task_id}.done"
    else
      touch "${STATUS_DIR}/${task_id}.fail"
    fi
    write_summary_locked
  } 9>>"$LOCK_FILE"
}

run_rl_case() {
  local phase="$1"
  local trace_name="$2"
  local trace_path="$3"
  local size="$4"
  local mode="$5"
  local weights_obs="$6"
  local size_tag run_tag task_id task_log python_log cachesim_log result_line rc

  size_tag="$(sanitize_size "$size")"
  task_id="${phase}_rl_${trace_name}_${size_tag}_${mode}_w${weights_obs}"
  task_log="${LOG_DIR}/${task_id}.log"
  python_log="${LOG_DIR}/ac_sb3_${task_id}.log"
  cachesim_log="${LOG_DIR}/cachesim_sb3_${task_id}.log"

  register_task "$task_id" "$phase" "rl" "$trace_name" "$size" "$mode" "$weights_obs" "LOH"
  if [ -f "${STATUS_DIR}/${task_id}.done" ]; then
    log "skip done ${task_id}"
    return 0
  fi
  if [ -f "${STATUS_DIR}/${task_id}.running" ]; then
    log "skip running ${task_id}"
    return 0
  fi

  mark_task_running "$task_id"

  log "start ${task_id} trace=${trace_path}"
  set +e
  (
    common_rl_env
    set_feature_mode "$mode"
    export LOH_PARALLEL_SAFE=1
    export LOH_INCLUDE_WEIGHTS_IN_OBS="$weights_obs"
    export RUN_TIMESTAMP="$task_id"
    export LOH_SHM_KEY="$(task_shm_key "$task_id")"
    export CACHESIM_NUM_THREAD="$CACHESIM_THREADS_PER_JOB"
    export OMP_NUM_THREADS="$PYTHON_THREADS_PER_JOB"
    export OPENBLAS_NUM_THREADS="$PYTHON_THREADS_PER_JOB"
    export MKL_NUM_THREADS="$PYTHON_THREADS_PER_JOB"
    export NUMEXPR_NUM_THREADS="$PYTHON_THREADS_PER_JOB"
    export TORCH_NUM_THREADS="$PYTHON_THREADS_PER_JOB"
    bash scripts/test_loh_rl_sb3.sh "$trace_path" "$size"
  ) > "$task_log" 2>&1
  rc=$?
  set -e

  result_line="$(latest_metric_line "$task_log")"
  record_result "$task_id" "$phase" "rl" "$trace_name" "$size" "$mode" "$weights_obs" "LOH" "$rc" "$result_line" "$task_log"
  finalize_task "$task_id" "$rc"

  if [ "$rc" -eq 0 ]; then
    log "done ${task_id} :: ${result_line}"
  else
    log "fail ${task_id} rc=${rc} :: ${result_line}"
  fi
  return 0
}

run_baseline_case() {
  local phase="$1"
  local trace_name="$2"
  local trace_path="$3"
  local size="$4"
  local algo_label="$5"
  local algo_name="$6"
  local evict_params="$7"
  local size_tag task_id task_log result_line rc
  local -a cmd

  size_tag="$(sanitize_size "$size")"
  task_id="${phase}_bl_${trace_name}_${size_tag}_${algo_label}"
  task_log="${LOG_DIR}/${task_id}.log"

  register_task "$task_id" "$phase" "baseline" "$trace_name" "$size" "-" "0" "$algo_label"
  if [ -f "${STATUS_DIR}/${task_id}.done" ]; then
    log "skip done ${task_id}"
    return 0
  fi
  if [ -f "${STATUS_DIR}/${task_id}.running" ]; then
    log "skip running ${task_id}"
    return 0
  fi

  mark_task_running "$task_id"

  cmd=("_build_rel/bin/cachesim" "$trace_path" "oracleGeneral" "$algo_name" "$size" "--num-thread=${CACHESIM_THREADS_PER_JOB}" "-v" "0")
  if [ -n "$evict_params" ]; then
    cmd+=("--eviction-params=${evict_params}")
  fi

  log "start ${task_id} trace=${trace_path}"
  set +e
  "${cmd[@]}" > "$task_log" 2>&1
  rc=$?
  set -e

  result_line="$(latest_metric_line "$task_log")"
  record_result "$task_id" "$phase" "baseline" "$trace_name" "$size" "-" "0" "$algo_label" "$rc" "$result_line" "$task_log"
  finalize_task "$task_id" "$rc"

  if [ "$rc" -eq 0 ]; then
    log "done ${task_id} :: ${result_line}"
  else
    log "fail ${task_id} rc=${rc} :: ${result_line}"
  fi
  return 0
}

build_task_plan() {
  local trace_name trace_path size mode

  local -a original_names=("1063" "meta" "wiki")
  local -a original_paths=(
    "data/TencentCBS/1063.oracleGeneral.zst"
    "data/MetaCDN/meta_reag.oracleGeneral.zst"
    "data/WikiCDN/wiki_2019t.oracleGeneral.zst"
  )
  local -a original_modes=("log1p" "log1p" "reciprocal")

  local -a new_names=("Alibaba-4" "MetaKV-202401" "TencentPhoto-1" "CloudPhysics-w01" "Twitter-13")
  local -a new_paths=(
    "data/Alibaba/alibabaBlock_4.oracleGeneral.zst"
    "data/MetaKV/202401_kv_traces_all_sort.csv.oracleGeneral.zst"
    "data/TencentPhoto/tencent_photo1.oracleGeneral.zst"
    "data/cloudphysics/w01.oracleGeneral.bin.zst"
    "data/twitter/cluster13.oracleGeneral.zst"
  )

  local -a baseline_labels=("BeladySize" "Belady" "GDSF" "3LCache-OMR" "3LCache-BMR" "S3FIFO" "LRU" "LFU")
  local -a baseline_algos=("BeladySize" "Belady" "GDSF" "3LCache" "3LCache" "S3FIFO" "LRU" "LFU")
  local -a baseline_params=("" "" "" "objective=object-miss-ratio" "" "" "" "")

  for idx in "${!original_names[@]}"; do
    trace_name="${original_names[$idx]}"
    trace_path="${original_paths[$idx]}"
    mode="${original_modes[$idx]}"
    register_task "phaseA_rl_${trace_name}_0p1_${mode}_w1" "phaseA" "rl" "$trace_name" "0.1" "$mode" "1" "LOH"
  done

  for idx in "${!original_names[@]}"; do
    trace_name="${original_names[$idx]}"
    trace_path="${original_paths[$idx]}"
    mode="${original_modes[$idx]}"
    for size in "${PHASE_AB_SIZES[@]}"; do
      register_task "phaseB_rl_${trace_name}_$(sanitize_size "$size")_${mode}_w0" "phaseB" "rl" "$trace_name" "$size" "$mode" "0" "LOH"
      if [ "$size" = "$PHASE_AB_ORIGINAL_BASELINE_SIZE" ]; then
        for bidx in "${!baseline_labels[@]}"; do
          register_task "phaseB_bl_${trace_name}_$(sanitize_size "$size")_${baseline_labels[$bidx]}" "phaseB" "baseline" "$trace_name" "$size" "-" "0" "${baseline_labels[$bidx]}"
        done
      fi
    done
  done

  for idx in "${!new_names[@]}"; do
    trace_name="${new_names[$idx]}"
    trace_path="${new_paths[$idx]}"
    for size in "${PHASE_AB_SIZES[@]}"; do
      for mode in log1p reciprocal; do
        register_task "phaseB_rl_${trace_name}_$(sanitize_size "$size")_${mode}_w0" "phaseB" "rl" "$trace_name" "$size" "$mode" "0" "LOH"
      done
      for bidx in "${!baseline_labels[@]}"; do
        register_task "phaseB_bl_${trace_name}_$(sanitize_size "$size")_${baseline_labels[$bidx]}" "phaseB" "baseline" "$trace_name" "$size" "-" "0" "${baseline_labels[$bidx]}"
      done
    done
  done
}

reap_finished_jobs() {
  local pid
  local -a remaining=()

  for pid in "${ACTIVE_PIDS[@]}"; do
    if kill -0 "$pid" 2>/dev/null; then
      remaining+=("$pid")
    else
      wait "$pid" || true
    fi
  done

  ACTIVE_PIDS=("${remaining[@]}")
}

wait_for_slot() {
  while true; do
    reap_finished_jobs
    if [ "${#ACTIVE_PIDS[@]}" -lt "$MAX_PARALLEL_JOBS" ]; then
      return 0
    fi
    wait -n || true
  done
}

launch_job() {
  wait_for_slot
  "$@" &
  ACTIVE_PIDS+=("$!")
}

wait_for_all_jobs() {
  while [ "${#ACTIVE_PIDS[@]}" -gt 0 ]; do
    wait -n || true
    reap_finished_jobs
  done
}

run_phase_a_group() {
  local -a original_names=("1063" "meta" "wiki")
  local -a original_paths=(
    "data/TencentCBS/1063.oracleGeneral.zst"
    "data/MetaCDN/meta_reag.oracleGeneral.zst"
    "data/WikiCDN/wiki_2019t.oracleGeneral.zst"
  )
  local -a original_modes=("log1p" "log1p" "reciprocal")
  local idx

  for idx in "${!original_names[@]}"; do
    launch_job run_rl_case "phaseA" "${original_names[$idx]}" "${original_paths[$idx]}" "0.1" "${original_modes[$idx]}" "1"
  done

  wait_for_all_jobs
}

run_phase_b_size_group() {
  local size="$1"
  local -a original_names=("1063" "meta" "wiki")
  local -a original_paths=(
    "data/TencentCBS/1063.oracleGeneral.zst"
    "data/MetaCDN/meta_reag.oracleGeneral.zst"
    "data/WikiCDN/wiki_2019t.oracleGeneral.zst"
  )
  local -a original_modes=("log1p" "log1p" "reciprocal")
  local -a new_names=("Alibaba-4" "MetaKV-202401" "TencentPhoto-1" "CloudPhysics-w01" "Twitter-13")
  local -a new_paths=(
    "data/Alibaba/alibabaBlock_4.oracleGeneral.zst"
    "data/MetaKV/202401_kv_traces_all_sort.csv.oracleGeneral.zst"
    "data/TencentPhoto/tencent_photo1.oracleGeneral.zst"
    "data/cloudphysics/w01.oracleGeneral.bin.zst"
    "data/twitter/cluster13.oracleGeneral.zst"
  )
  local -a baseline_labels=("BeladySize" "Belady" "GDSF" "3LCache-OMR" "3LCache-BMR" "S3FIFO" "LRU" "LFU")
  local -a baseline_algos=("BeladySize" "Belady" "GDSF" "3LCache" "3LCache" "S3FIFO" "LRU" "LFU")
  local -a baseline_params=("" "" "" "objective=object-miss-ratio" "" "" "" "")
  local idx mode bidx

  for idx in "${!original_names[@]}"; do
    launch_job run_rl_case "phaseB" "${original_names[$idx]}" "${original_paths[$idx]}" "$size" "${original_modes[$idx]}" "0"
    if [ "$size" = "$PHASE_AB_ORIGINAL_BASELINE_SIZE" ]; then
      for bidx in "${!baseline_labels[@]}"; do
        launch_job run_baseline_case "phaseB" "${original_names[$idx]}" "${original_paths[$idx]}" "$size" \
          "${baseline_labels[$bidx]}" "${baseline_algos[$bidx]}" "${baseline_params[$bidx]}"
      done
    fi
  done

  for idx in "${!new_names[@]}"; do
    for mode in log1p reciprocal; do
      launch_job run_rl_case "phaseB" "${new_names[$idx]}" "${new_paths[$idx]}" "$size" "$mode" "0"
    done
    for bidx in "${!baseline_labels[@]}"; do
      launch_job run_baseline_case "phaseB" "${new_names[$idx]}" "${new_paths[$idx]}" "$size" \
        "${baseline_labels[$bidx]}" "${baseline_algos[$bidx]}" "${baseline_params[$bidx]}"
    done
  done

  wait_for_all_jobs
}

run_all() {
  local size

  run_phase_a_group

  for size in "${PHASE_AB_SIZES[@]}"; do
    log "start size_group size=${size} max_parallel=${MAX_PARALLEL_JOBS} cachesim_threads=${CACHESIM_THREADS_PER_JOB}"
    run_phase_b_size_group "$size"
    log "done size_group size=${size}"
  done
}

build_task_plan
write_summary
log "queue_root=${QUEUE_ROOT}"
log "planned_tasks=$(( $(wc -l < "$TASKS_TSV") - 1 ))"
log "parallel_config total_cpus=${TOTAL_CPUS} reserve=${CPU_RESERVE} max_parallel=${MAX_PARALLEL_JOBS} cachesim_threads_per_job=${CACHESIM_THREADS_PER_JOB} sizes=${PHASE_AB_SIZE_LIST} original_baseline_size=${PHASE_AB_ORIGINAL_BASELINE_SIZE}"
run_all
rm -f "$CURRENT_TASK_FILE"
write_summary
log "all tasks finished"
