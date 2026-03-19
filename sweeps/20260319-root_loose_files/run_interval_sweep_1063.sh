#!/bin/bash
# ====================================================================
# Blocked 模式同步间隔 sweep — 1063 trace (full-req)
# 测试不同 LOH_RL_UPDATE_INTERVAL 对 blocked 模式吞吐量和 MR 的影响
# ====================================================================
set -e
cd "$(dirname "$0")/.."

TRACE="data/TencentCBS/1063.oracleGeneral.zst"

# baseline 配置 (baseline state = GLOBAL only)
COMMON="LOH_INCLUDE_HIT_MISS_FEATURES=0 LOH_INCLUDE_CACHE_FEATURES=0"
COMMON+=" LOH_INCLUDE_CANDIDATE_FEATURES=0 LOH_INCLUDE_TOPK_CANDIDATE_FEATURES=0"
COMMON+=" LOH_INCLUDE_AVGTOPK_CANDIDATE_FEATURES=0 LOH_INCLUDE_REQUEST=0"
COMMON+=" LOH_SCORE_USE_COMPOUND=1 LOH_SCORE_USE_IRT=0 LOH_FEATURE_LOG1P=1"
COMMON+=" LOH_STRUCTURED_CANDIDATES=96 LOH_RANDOM_CANDIDATES=64"
COMMON+=" LOH_SKIP_PIP_INSTALL=1 LOH_BUILD_RELEASE=1"
COMMON+=" LOH_DEBUG_LEVEL=0 CACHESIM_NUM_REQ=ALL"

# 同步间隔值（从小到大）
INTERVALS=(500 2000 5000 10000 50000)

echo "########################################################################"
echo "# Blocked mode sync interval sweep — 1063 full-req"
echo "# Intervals: ${INTERVALS[*]}"
echo "# Also testing: nonblocked with interval=500 (control)"
echo "########################################################################"

# 先跑一个 nonblocked 作为对照
echo ""
echo "========================================"
echo "[$(date +%H:%M:%S)] Control: nonblocked interval=500"
LOG="tmp/rl_interval_1063_nb_500.log"
echo "  Log → $LOG"
eval "env $COMMON LOH_WAIT_MODE=nonblocked LOH_RL_UPDATE_INTERVAL=500 \
  bash scripts/test_loh_rl_sb3.sh \"$TRACE\" 0.1" > "$LOG" 2>&1 || true
MR=$(grep "miss ratio" "$LOG" | grep -v "Byte\|weight\|miss_ratio" | tail -1 | grep -oP 'miss ratio \K[0-9.]+' | head -1)
MQPS=$(grep -oP 'throughput \K[0-9.]+' "$LOG" | tail -1)
echo "  Result: MR=${MR:-FAILED}, MQPS=${MQPS:-?}"

# 跑各个 blocked 间隔
for interval in "${INTERVALS[@]}"; do
  echo ""
  echo "========================================"
  echo "[$(date +%H:%M:%S)] Blocked interval=${interval}"
  LOG="tmp/rl_interval_1063_bl_${interval}.log"
  echo "  Log → $LOG"

  eval "env $COMMON LOH_WAIT_MODE=blocked LOH_RL_UPDATE_INTERVAL=${interval} \
    bash scripts/test_loh_rl_sb3.sh \"$TRACE\" 0.1" > "$LOG" 2>&1 || true

  MR=$(grep "miss ratio" "$LOG" | grep -v "Byte\|weight\|miss_ratio" | tail -1 | grep -oP 'miss ratio \K[0-9.]+' | head -1)
  MQPS=$(grep -oP 'throughput \K[0-9.]+' "$LOG" | tail -1)
  STEPS=$(grep "env.step_total" "$LOG" | awk '{print $2}' | head -1)
  echo "  Result: MR=${MR:-FAILED}, MQPS=${MQPS:-?}, steps=${STEPS:-?}"
done

# Summary
echo ""
echo "========== SUMMARY =========="
printf "%-10s %-8s %-10s %-10s\n" "Mode" "Interval" "MR" "MQPS"
printf "%-10s %-8s %-10s %-10s\n" "----" "--------" "--" "----"

# Nonblocked control
f="tmp/rl_interval_1063_nb_500.log"
MR=$(grep "miss ratio" "$f" | grep -v "Byte\|weight\|miss_ratio" | tail -1 | grep -oP 'miss ratio \K[0-9.]+' | head -1)
MQPS=$(grep -oP 'throughput \K[0-9.]+' "$f" | tail -1)
printf "%-10s %-8s %-10s %-10s\n" "nonblock" "500" "${MR:-N/A}" "${MQPS:-N/A}"

for interval in "${INTERVALS[@]}"; do
  f="tmp/rl_interval_1063_bl_${interval}.log"
  MR=$(grep "miss ratio" "$f" 2>/dev/null | grep -v "Byte\|weight\|miss_ratio" | tail -1 | grep -oP 'miss ratio \K[0-9.]+' | head -1)
  MQPS=$(grep -oP 'throughput \K[0-9.]+' "$f" 2>/dev/null | tail -1)
  printf "%-10s %-8s %-10s %-10s\n" "blocked" "${interval}" "${MR:-N/A}" "${MQPS:-N/A}"
done

echo ""
echo "Done at $(date)"
