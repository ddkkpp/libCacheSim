#!/bin/bash
# ============================================================================
# 全量实验批处理脚本
# 按照 FULL_EXPERIMENT_RESULTS.md §19 配置作为基线
# ============================================================================
set -euo pipefail
PROJECT_ROOT="/home/dingkp/libCacheSim"
cd "$PROJECT_ROOT"

TS=$(date +%m%d_%H%M%S)
RESULT_DIR="$PROJECT_ROOT/tmp/batch_all_${TS}"
mkdir -p "$RESULT_DIR"
SUMMARY="$RESULT_DIR/summary.csv"
echo "task,config,trace,feature_mode,requests,MR,ByteMR,MQPS,wall_time" > "$SUMMARY"

LOH_C="$PROJECT_ROOT/libCacheSim/cache/eviction/LOH.c"
CACHESIM="$PROJECT_ROOT/_build_rel/bin/cachesim"

# ========== Trace 定义 ==========
# 原始三条 trace
TRACES_ORIG=(
  "data/TencentCBS/1063.oracleGeneral.zst"
  "data/WikiCDN/wiki_2019t.oracleGeneral.zst"
  "data/MetaCDN/meta_reag.oracleGeneral.zst"
)
TNAMES_ORIG=("1063" "wiki" "meta")
TLOG1P_ORIG=(1 0 1)    # 1063=LOG1P, wiki=RECIPROCAL, meta=LOG1P
TRECIP_ORIG=(0 1 0)

# 新增 5 条 trace (wiki2016u 不存在于 data 目录，跳过)
TRACES_NEW=(
  "data/Alibaba/alibabaBlock_4.oracleGeneral.zst"
  "data/MetaKV/202401_kv_traces_all_sort.csv.oracleGeneral.zst"
  "data/TencentPhoto/tencent_photo1.oracleGeneral.zst"
  "data/cloudphysics/w01.oracleGeneral.bin.zst"
  "data/twitter/cluster13.oracleGeneral.zst"
)
TNAMES_NEW=("alibaba4" "metakv2401" "tencentPhoto1" "cloudphysicsW01" "twitter13")
# 新 trace 的特征模式需要 auto-detect，先设为空让脚本检测
# 但我们会分别跑 LOG1P 和 RECIPROCAL 两种模式
COMPARISON_ALGOS=("LRU" "LFU" "FIFO" "ARC" "LeCaR" "Cacheus")

# ========== 通用函数 ==========
log() { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$RESULT_DIR/batch.log"; }

set_common_env() {
  export LOH_WAIT_MODE=nonblocked
  export LOH_ENABLE_SEMAPHORE=1
  export LOH_SCORE_USE_COMPOUND=1
  export LOH_SCORE_USE_IRT=0
  export LOH_BUILD_RELEASE=1
  export LOH_SKIP_BUILD=1
  export LOH_SKIP_PIP_INSTALL=1
  export LOH_ADAPTIVE_BUDGET=1
}

cleanup_procs() {
  pkill -f "loh_actor_critic" 2>/dev/null || true
  pkill -f "cachesim.*LOH" 2>/dev/null || true
  rm -f /dev/shm/loh_ac_* 2>/dev/null || true
  sleep 2
}

# Run one LOH RL test with test_loh_rl_sb3.sh
run_loh_test() {
  local task="$1" config="$2" trace="$3" tname="$4" log1p="$5" recip="$6" cache_ratio="$7" num_req="$8"
  local tag="${task}_${config}_${tname}_${cache_ratio}"
  local fmode="LOG1P"
  [[ "$recip" == "1" ]] && fmode="RECIPROCAL"

  log "START LOH $tag (${fmode}, req=${num_req})"
  cleanup_procs

  export LOH_FEATURE_LOG1P="$log1p"
  export LOH_FEATURE_LOG1P_RECIPROCAL="$recip"
  if [[ "$num_req" == "0" ]]; then
    export CACHESIM_NUM_REQ=0
  else
    export CACHESIM_NUM_REQ="$num_req"
  fi

  local start_ts=$(date +%s)
  bash scripts/test_loh_rl_sb3.sh "$trace" "$cache_ratio" \
    > "$RESULT_DIR/${tag}_run.log" 2>&1 || true
  local end_ts=$(date +%s)
  local wall=$((end_ts - start_ts))

  local cslog=$(ls -1t cachesim_sb3_*.log 2>/dev/null | head -1)
  if [[ -n "$cslog" ]]; then
    local line=$(grep "miss ratio" "$cslog" | tail -1)
    local mr=$(echo "$line" | grep -oP 'miss ratio \K[0-9.]+' | head -1)
    local bmr=$(echo "$line" | grep -oP 'byte miss ratio \K[0-9.]+')
    local mqps=$(echo "$line" | grep -oP '[0-9.]+ MQPS' | grep -oP '[0-9.]+')
    local req=$(echo "$line" | grep -oP '[0-9]+ req' | grep -oP '[0-9]+')
    echo "${task},${config},${tname},${fmode},${req:-0},${mr:-N/A},${bmr:-N/A},${mqps:-N/A},${wall}" >> "$SUMMARY"
    log "DONE  $tag -> MR=${mr:-N/A} BMR=${bmr:-N/A} MQPS=${mqps:-N/A} (${wall}s)"
    mv "$cslog" "$RESULT_DIR/${tag}_cachesim.log" 2>/dev/null || true
    local pylog=$(ls -1t ac_sb3_*.log 2>/dev/null | head -1)
    [[ -n "$pylog" ]] && mv "$pylog" "$RESULT_DIR/${tag}_python.log" 2>/dev/null || true
  else
    echo "${task},${config},${tname},${fmode},0,FAIL,FAIL,FAIL,${wall}" >> "$SUMMARY"
    log "FAIL  $tag (${wall}s)"
  fi
  cleanup_procs
}

# Run comparison algorithm (direct cachesim, no RL)
run_comparison() {
  local task="$1" algo="$2" trace="$3" tname="$4" cache_ratio="$5"
  local tag="${task}_${algo}_${tname}_${cache_ratio}"

  log "START $algo $tag"
  local start_ts=$(date +%s)
  local output=$("$CACHESIM" "$trace" oracleGeneral "$algo" "$cache_ratio" -v 1 2>&1 | tail -1)
  local end_ts=$(date +%s)
  local wall=$((end_ts - start_ts))

  local mr=$(echo "$output" | grep -oP 'miss ratio \K[0-9.]+' | head -1)
  local bmr=$(echo "$output" | grep -oP 'byte miss ratio \K[0-9.]+')
  local mqps=$(echo "$output" | grep -oP '[0-9.]+ MQPS' | grep -oP '[0-9.]+')
  local req=$(echo "$output" | grep -oP '[0-9]+ req' | grep -oP '[0-9]+')
  echo "${task},${algo},${tname},N/A,${req:-0},${mr:-N/A},${bmr:-N/A},${mqps:-N/A},${wall}" >> "$SUMMARY"
  log "DONE  $tag -> MR=${mr:-N/A} MQPS=${mqps:-N/A} (${wall}s)"
}

rebuild_release() {
  log "Rebuilding release binary..."
  cd "$PROJECT_ROOT/_build_rel"
  ninja -j$(nproc) 2>&1 | tail -5
  cd "$PROJECT_ROOT"
  log "Rebuild done."
}

# ============================================================================
log "================================================================="
log "  BATCH ALL EXPERIMENTS START"
log "  Results: $RESULT_DIR"
log "================================================================="

########################################
# TASK 1: 重跑1063 + 复现§19.3配置
# random=64, struct=96, LOH_FEATURE_LOG1P=1, nonblocked, async
########################################
log ""
log "===== TASK 1: 1063 §19.3 configs (rand64+struct96) ====="

set_common_env
export LOH_TAIL_SAMPLE=1
export LOH_TAIL_SAMPLE_DECAY=0.99
export LOH_ASYNC_TRAIN=1
export LOH_RANDOM_CANDIDATES=64
export LOH_STRUCTURED_CANDIDATES=96
run_loh_test "T1" "r64s96decay_async" "${TRACES_ORIG[0]}" "1063" 1 0 0.1 0

########################################
# TASK 2: Wiki RL + 复现§19.3配置
########################################
log ""
log "===== TASK 2: Wiki §19.3 config (rand64+struct96) ====="

set_common_env
export LOH_TAIL_SAMPLE=1
export LOH_TAIL_SAMPLE_DECAY=0.99
export LOH_ASYNC_TRAIN=1
export LOH_RANDOM_CANDIDATES=64
export LOH_STRUCTURED_CANDIDATES=96
run_loh_test "T2" "r64s96decay_async" "${TRACES_ORIG[1]}" "wiki" 0 1 0.1 0

########################################
# TASK 3: Penalty 模式测试
# pos0 (仅负面), pos1 (负面+正面)
# 不同 penalty formula: centered, relative, one_minus, neg, net, net2
# 三条 trace
########################################
log ""
log "===== TASK 3: Penalty modes (需重编译) ====="

# 备份原始宏
ORIG_PENALTY=$(grep '#define LOH_ENABLE_PENALTY' "$LOH_C")

# 开启 penalty 并重编译
sed -i 's/#define LOH_ENABLE_PENALTY 0/#define LOH_ENABLE_PENALTY 1/' "$LOH_C"
rebuild_release

PENALTY_FORMULAS=("centered" "relative" "one_minus" "neg" "net" "net2")

for penalty_positive in 0 1; do
  for formula in "${PENALTY_FORMULAS[@]}"; do
    cname="penalty_pos${penalty_positive}_${formula}"
    export LOH_PENALTY_SEND_POSITIVE=$penalty_positive
    export LOH_PENALTY_REWARD_FORMULA=$formula

    set_common_env
    export LOH_TAIL_SAMPLE=1
    export LOH_TAIL_SAMPLE_DECAY=0.99
    export LOH_ASYNC_TRAIN=1
    export LOH_RANDOM_CANDIDATES=64
    export LOH_STRUCTURED_CANDIDATES=96

    for i in 0 1 2; do
      run_loh_test "T3" "$cname" "${TRACES_ORIG[$i]}" "${TNAMES_ORIG[$i]}" "${TLOG1P_ORIG[$i]}" "${TRECIP_ORIG[$i]}" 0.1 0
    done
  done
done

# 恢复 penalty 宏
sed -i 's/#define LOH_ENABLE_PENALTY 1/#define LOH_ENABLE_PENALTY 0/' "$LOH_C"
rebuild_release
unset LOH_PENALTY_SEND_POSITIVE LOH_PENALTY_REWARD_FORMULA

########################################
# TASK 4: 网络层数增大测试
########################################
log ""
log "===== TASK 4: 更深网络 ====="

for net_arch in "256,256,256" "512,256,128"; do
  net_tag=$(echo "$net_arch" | tr ',' 'x')
  export SAC_NET_ARCH="$net_arch"

  set_common_env
  export LOH_TAIL_SAMPLE=1
  export LOH_TAIL_SAMPLE_DECAY=0.99
  export LOH_ASYNC_TRAIN=1
  export LOH_RANDOM_CANDIDATES=64
  export LOH_STRUCTURED_CANDIDATES=96

  for i in 0 1 2; do
    run_loh_test "T4" "net${net_tag}" "${TRACES_ORIG[$i]}" "${TNAMES_ORIG[$i]}" "${TLOG1P_ORIG[$i]}" "${TRECIP_ORIG[$i]}" 0.1 0
  done
done
unset SAC_NET_ARCH

########################################
# TASK 5: 增大 buffer 和 batch size
########################################
log ""
log "===== TASK 5: 大 buffer/batch ====="

for buf_batch in "50000:512" "100000:1024"; do
  IFS=':' read -r buf batch <<< "$buf_batch"
  export SAC_BUFFER_SIZE="$buf"
  export SAC_BATCH_SIZE="$batch"

  set_common_env
  export LOH_TAIL_SAMPLE=1
  export LOH_TAIL_SAMPLE_DECAY=0.99
  export LOH_ASYNC_TRAIN=1
  export LOH_RANDOM_CANDIDATES=64
  export LOH_STRUCTURED_CANDIDATES=96

  for i in 0 1 2; do
    run_loh_test "T5" "buf${buf}_bat${batch}" "${TRACES_ORIG[$i]}" "${TNAMES_ORIG[$i]}" "${TLOG1P_ORIG[$i]}" "${TRECIP_ORIG[$i]}" 0.1 0
  done
done
unset SAC_BUFFER_SIZE SAC_BATCH_SIZE

########################################
# TASK 6: State 加上权重
########################################
log ""
log "===== TASK 6: Weights in observation ====="

export LOH_INCLUDE_WEIGHTS_IN_OBS=1

set_common_env
export LOH_TAIL_SAMPLE=1
export LOH_TAIL_SAMPLE_DECAY=0.99
export LOH_ASYNC_TRAIN=1
export LOH_RANDOM_CANDIDATES=64
export LOH_STRUCTURED_CANDIDATES=96

for i in 0 1 2; do
  run_loh_test "T6" "weights_in_obs" "${TRACES_ORIG[$i]}" "${TNAMES_ORIG[$i]}" "${TLOG1P_ORIG[$i]}" "${TRECIP_ORIG[$i]}" 0.1 0
done
unset LOH_INCLUDE_WEIGHTS_IN_OBS

########################################
# TASK 7: 6 种新 trace (LOG1P + RECIPROCAL)
# + 对比算法 (LRU, LFU, FIFO, ARC, LeCaR, Cacheus)
########################################
log ""
log "===== TASK 7: 6 新 trace × 2 特征模式 + 对比算法 ====="

for idx in "${!TRACES_NEW[@]}"; do
  trace="${TRACES_NEW[$idx]}"
  tname="${TNAMES_NEW[$idx]}"

  # 先跑对比算法
  for algo in "${COMPARISON_ALGOS[@]}"; do
    run_comparison "T7" "$algo" "$trace" "$tname" 0.1
  done

  # LOH + LOG1P
  set_common_env
  export LOH_TAIL_SAMPLE=1
  export LOH_TAIL_SAMPLE_DECAY=0.99
  export LOH_ASYNC_TRAIN=1
  export LOH_RANDOM_CANDIDATES=64
  export LOH_STRUCTURED_CANDIDATES=96
  run_loh_test "T7" "LOH_log1p" "$trace" "$tname" 1 0 0.1 0

  # LOH + RECIPROCAL
  set_common_env
  export LOH_TAIL_SAMPLE=1
  export LOH_TAIL_SAMPLE_DECAY=0.99
  export LOH_ASYNC_TRAIN=1
  export LOH_RANDOM_CANDIDATES=64
  export LOH_STRUCTURED_CANDIDATES=96
  run_loh_test "T7" "LOH_reciprocal" "$trace" "$tname" 0 1 0.1 0
done

########################################
# TASK 8: 原始三条 trace, cache size 0.01
# + 对比算法
########################################
log ""
log "===== TASK 8: 原始 3 trace × cache_size=0.01 + 对比算法 ====="

for i in 0 1 2; do
  trace="${TRACES_ORIG[$i]}"
  tname="${TNAMES_ORIG[$i]}"

  # 对比算法
  for algo in "${COMPARISON_ALGOS[@]}"; do
    run_comparison "T8" "$algo" "$trace" "$tname" 0.01
  done

  # LOH RL
  set_common_env
  export LOH_TAIL_SAMPLE=1
  export LOH_TAIL_SAMPLE_DECAY=0.99
  export LOH_ASYNC_TRAIN=1
  export LOH_RANDOM_CANDIDATES=64
  export LOH_STRUCTURED_CANDIDATES=96
  run_loh_test "T8" "LOH" "${TRACES_ORIG[$i]}" "${TNAMES_ORIG[$i]}" "${TLOG1P_ORIG[$i]}" "${TRECIP_ORIG[$i]}" 0.01 0
done

# ============================================================================
log ""
log "================================================================="
log "  ALL EXPERIMENTS COMPLETE"
log "  Summary: $SUMMARY"
log "================================================================="

echo ""
echo "===== RESULTS SUMMARY ====="
column -t -s',' "$SUMMARY" 2>/dev/null || cat "$SUMMARY"
