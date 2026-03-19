#!/bin/bash
# ====================================================================
# State 维度对比实验 — 1063 trace
# 三轮测试：8M nonblocked → full nonblocked → 3M blocked
# ====================================================================
set -e
cd "$(dirname "$0")/.."

TRACE="data/TencentCBS/1063.oracleGeneral.zst"

# 所有编译期开关的默认关闭值
ALL_OFF="LOH_INCLUDE_HIT_MISS_FEATURES=0 LOH_INCLUDE_CACHE_FEATURES=0"
ALL_OFF+=" LOH_INCLUDE_CANDIDATE_FEATURES=0 LOH_INCLUDE_TOPK_CANDIDATE_FEATURES=0"
ALL_OFF+=" LOH_INCLUDE_AVGTOPK_CANDIDATE_FEATURES=0 LOH_INCLUDE_REQUEST=0"

# 公共运行时配置
COMMON="LOH_SCORE_USE_COMPOUND=1 LOH_SCORE_USE_IRT=0 LOH_FEATURE_LOG1P=1"
COMMON+=" LOH_STRUCTURED_CANDIDATES=96 LOH_RANDOM_CANDIDATES=64"
COMMON+=" LOH_SKIP_PIP_INSTALL=1 LOH_BUILD_RELEASE=1"

# 测试组
declare -a TEST_NAMES=(baseline hit_miss cache candidate avgtopk request)
declare -A TEST_FLAGS
TEST_FLAGS[baseline]=""
TEST_FLAGS[hit_miss]="LOH_INCLUDE_HIT_MISS_FEATURES=1"
TEST_FLAGS[cache]="LOH_INCLUDE_CACHE_FEATURES=1"
TEST_FLAGS[candidate]="LOH_INCLUDE_CANDIDATE_FEATURES=1"
TEST_FLAGS[avgtopk]="LOH_INCLUDE_AVGTOPK_CANDIDATE_FEATURES=1"
TEST_FLAGS[request]="LOH_INCLUDE_REQUEST=1"

run_sweep() {
  local LABEL=$1
  local NUM_REQ=$2
  local WAIT_MODE=$3

  echo ""
  echo "########################################################################"
  echo "# Round: ${LABEL} (reqs=${NUM_REQ:-all}, wait=${WAIT_MODE})"
  echo "########################################################################"

  for name in "${TEST_NAMES[@]}"; do
    extra="${TEST_FLAGS[$name]}"
    LOG="tmp/rl_state_1063_${LABEL}_${name}.log"
    echo "========================================"
    echo "[$(date +%H:%M:%S)] ${LABEL}/${name} (extra: ${extra:-none})"
    echo "  Log → $LOG"

    ENV_STR="$ALL_OFF $COMMON LOH_WAIT_MODE=${WAIT_MODE} LOH_DEBUG_LEVEL=0"
    if [ -n "$NUM_REQ" ] && [ "$NUM_REQ" != "ALL" ]; then
      ENV_STR+=" CACHESIM_NUM_REQ=$NUM_REQ"
    elif [ "$NUM_REQ" = "ALL" ]; then
      ENV_STR+=" CACHESIM_NUM_REQ=ALL"
    fi
    if [ -n "$extra" ]; then
      ENV_STR+=" $extra"
    fi

    eval "env $ENV_STR bash scripts/test_loh_rl_sb3.sh \"$TRACE\" 0.1" > "$LOG" 2>&1 || true

    MR=$(grep "miss ratio" "$LOG" | grep -v Byte | tail -1 | grep -oP 'miss ratio \K[0-9.]+' | head -1)
    echo "  Result: MR = ${MR:-FAILED}"
  done
}

# === Round 1: 8M nonblocked ===
run_sweep "8M_nb" "8000000" "nonblocked"

# === Round 2: full-req nonblocked ===
run_sweep "full_nb" "ALL" "nonblocked"

# === Round 3: 3M blocked ===
run_sweep "3M_bl" "3000000" "blocked"

# === Final Summary ===
echo ""
echo "========== FINAL SUMMARY =========="
printf "%-12s %-12s %-12s %-12s\n" "State" "8M_nb" "full_nb" "3M_bl"
printf "%-12s %-12s %-12s %-12s\n" "-----" "-----" "-------" "-----"
for name in "${TEST_NAMES[@]}"; do
  MR1=$(grep "miss ratio" "tmp/rl_state_1063_8M_nb_${name}.log" 2>/dev/null | grep -v Byte | tail -1 | grep -oP 'miss ratio \K[0-9.]+' | head -1)
  MR2=$(grep "miss ratio" "tmp/rl_state_1063_full_nb_${name}.log" 2>/dev/null | grep -v Byte | tail -1 | grep -oP 'miss ratio \K[0-9.]+' | head -1)
  MR3=$(grep "miss ratio" "tmp/rl_state_1063_3M_bl_${name}.log" 2>/dev/null | grep -v Byte | tail -1 | grep -oP 'miss ratio \K[0-9.]+' | head -1)
  printf "%-12s %-12s %-12s %-12s\n" "$name" "${MR1:-N/A}" "${MR2:-N/A}" "${MR3:-N/A}"
done
