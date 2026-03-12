#!/bin/bash
# 顺序运行 1063 / meta / wiki 三个 trace 的全量 RL 测试
# 使用与 0306 基准完全一致的配置
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

TIMESTAMP=$(date +%m%d_%H%M%S)
SUMMARY_LOG="tmp/rl_sequential_${TIMESTAMP}.log"
mkdir -p tmp

echo "=========================================" | tee "$SUMMARY_LOG"
echo "Sequential 3-trace full RL test" | tee -a "$SUMMARY_LOG"
echo "Started: $(date)" | tee -a "$SUMMARY_LOG"
echo "=========================================" | tee -a "$SUMMARY_LOG"

# 公共环境变量 — 与 0306 基准一致
export LOH_SCORE_USE_COMPOUND=1
export LOH_SCORE_USE_IRT=0
export LOH_FEATURE_LOG1P=1
export LOH_RANDOM_CANDIDATES=64
export LOH_SKIP_PIP_INSTALL=1
export LOH_SKIP_BUILD=1
export LOH_DEBUG_LEVEL=0
export LOH_WAIT_MODE=nonblocked
export LOH_PIN_CPU=0
export LOH_CACHESIM_BIN=_build_rel/bin/cachesim
export LOH_CHECKPOINT_FREQ=50000

# 3 个 trace 定义
TRACES=(
    "data/TencentCBS/1063.oracleGeneral.zst"
    "data/MetaCDN/meta_reag.oracleGeneral.zst"
    "data/WikiCDN/wiki_2019t.oracleGeneral.zst"
)
NAMES=("1063" "meta" "wiki")
CACHE_SIZES=("0.1" "0.1" "0.1")

# 0306 基准值（参考）
BASELINE_MR=("0.027361" "0.269384" "0.176183")
BASELINE_BMR=("0.030195" "0.156423" "0.141579")
BASELINE_MQPS=("0.75" "0.97" "0.15")

TOTAL=${#TRACES[@]}
PASS=0
FAIL=0

for i in "${!TRACES[@]}"; do
    TRACE="${TRACES[$i]}"
    NAME="${NAMES[$i]}"
    CS="${CACHE_SIZES[$i]}"
    RUN_TS=$(date +%m%d_%H%M%S)
    RUN_LOG="tmp/rl_${NAME}_full_${RUN_TS}.log"

    echo "" | tee -a "$SUMMARY_LOG"
    echo "=========================================" | tee -a "$SUMMARY_LOG"
    echo "[$((i+1))/$TOTAL] Running: ${NAME} (cache=${CS})" | tee -a "$SUMMARY_LOG"
    echo "  Trace: ${TRACE}" | tee -a "$SUMMARY_LOG"
    echo "  0306 baseline: MR=${BASELINE_MR[$i]}, byte_MR=${BASELINE_BMR[$i]}, MQPS=${BASELINE_MQPS[$i]}" | tee -a "$SUMMARY_LOG"
    echo "  Start: $(date)" | tee -a "$SUMMARY_LOG"
    echo "=========================================" | tee -a "$SUMMARY_LOG"

    # 清理共享内存和残留进程
    rm -f /dev/shm/loh_ac_* 2>/dev/null || true
    pkill -f "loh_actor_critic_sb3" 2>/dev/null || true
    sleep 1

    # 全量请求（ALL 表示跑完整个 trace）
    export CACHESIM_NUM_REQ=ALL

    # 运行 test_loh_rl_sb3.sh
    START_SEC=$(date +%s)
    if bash scripts/test_loh_rl_sb3.sh "$TRACE" "$CS" > "$RUN_LOG" 2>&1; then
        STATUS="SUCCESS"
    else
        STATUS="FAILED (exit $?)"
    fi
    END_SEC=$(date +%s)
    ELAPSED=$(( END_SEC - START_SEC ))

    # 提取结果
    RESULT_LINE=$(grep "MQPS" "$RUN_LOG" | tail -1 || echo "N/A")
    MR_VAL=$(echo "$RESULT_LINE" | grep -oP 'miss_ratio\s*[\d.]+' | grep -oP '[\d.]+' || echo "?")

    echo "  Status: ${STATUS}" | tee -a "$SUMMARY_LOG"
    echo "  Duration: ${ELAPSED}s" | tee -a "$SUMMARY_LOG"
    echo "  Result: ${RESULT_LINE}" | tee -a "$SUMMARY_LOG"
    echo "  Log: ${RUN_LOG}" | tee -a "$SUMMARY_LOG"

    if [ "$STATUS" = "SUCCESS" ]; then
        PASS=$((PASS+1))
    else
        FAIL=$((FAIL+1))
    fi

    # 清理共享内存
    rm -f /dev/shm/loh_ac_* 2>/dev/null || true
    pkill -f "loh_actor_critic_sb3" 2>/dev/null || true
    sleep 2
done

echo "" | tee -a "$SUMMARY_LOG"
echo "=========================================" | tee -a "$SUMMARY_LOG"
echo "All $TOTAL traces completed: $PASS passed, $FAIL failed" | tee -a "$SUMMARY_LOG"
echo "Finished: $(date)" | tee -a "$SUMMARY_LOG"
echo "Summary log: $SUMMARY_LOG" | tee -a "$SUMMARY_LOG"
echo "=========================================" | tee -a "$SUMMARY_LOG"
