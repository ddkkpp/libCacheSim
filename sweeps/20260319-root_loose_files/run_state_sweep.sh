#!/bin/bash
# ====================================================================
# State 维度对比实验 v3
# 使用两种候选（STRUCTURED=96 + RANDOM=64），避免 state 维度为全 0
# 速度优化：release build + nonblocked + DEBUG_LEVEL=0
# 基准：Meta compound + 8M
# ====================================================================
set -e
cd "$(dirname "$0")/.."

NUM_REQ=8000000

# 共享运行时配置（含速度优化）
RUNTIME_ENV="LOH_SCORE_USE_COMPOUND=1 LOH_SCORE_USE_IRT=0 LOH_FEATURE_LOG1P=1"
RUNTIME_ENV+=" LOH_STRUCTURED_CANDIDATES=96 LOH_RANDOM_CANDIDATES=64"
RUNTIME_ENV+=" LOH_SKIP_PIP_INSTALL=1"
RUNTIME_ENV+=" CACHESIM_NUM_REQ=$NUM_REQ"
RUNTIME_ENV+=" LOH_BUILD_RELEASE=1"          # 使用 release build（~44x faster）
RUNTIME_ENV+=" LOH_WAIT_MODE=nonblocked"     # 非阻塞同步（mmap 快速路径）
RUNTIME_ENV+=" LOH_DEBUG_LEVEL=0"            # 最小日志开销

# 所有编译期开关的默认关闭值
ALL_OFF="LOH_INCLUDE_HIT_MISS_FEATURES=0 LOH_INCLUDE_CACHE_FEATURES=0"
ALL_OFF+=" LOH_INCLUDE_CANDIDATE_FEATURES=0 LOH_INCLUDE_TOPK_CANDIDATE_FEATURES=0"
ALL_OFF+=" LOH_INCLUDE_AVGTOPK_CANDIDATE_FEATURES=0 LOH_INCLUDE_REQUEST=0"

# 测试组
declare -a TEST_NAMES=(baseline hit_miss cache candidate avgtopk request)
declare -A TEST_FLAGS
TEST_FLAGS[baseline]=""
TEST_FLAGS[hit_miss]="LOH_INCLUDE_HIT_MISS_FEATURES=1"
TEST_FLAGS[cache]="LOH_INCLUDE_CACHE_FEATURES=1"
TEST_FLAGS[candidate]="LOH_INCLUDE_CANDIDATE_FEATURES=1"
TEST_FLAGS[avgtopk]="LOH_INCLUDE_AVGTOPK_CANDIDATE_FEATURES=1"
TEST_FLAGS[request]="LOH_INCLUDE_REQUEST=1"

echo "=== State Dimension Sweep v3 (STRUCT=96 + RANDOM=64, Release+Nonblocked) ==="
echo "每组重新编译以正确设置编译期宏（release mode）"
echo ""

for name in "${TEST_NAMES[@]}"; do
  extra="${TEST_FLAGS[$name]}"
  LOG="tmp/rl_state2_${name}_meta_8M.log"
  echo "========================================"
  echo "[$(date +%H:%M:%S)] Running: $name (extra: ${extra:-none})"
  echo "  Log → $LOG"

  ENV_STR="$ALL_OFF $RUNTIME_ENV"
  if [ -n "$extra" ]; then
    ENV_STR+=" $extra"
  fi

  eval "env $ENV_STR bash scripts/test_loh_rl_sb3.sh" > "$LOG" 2>&1 || true

  MR=$(cat "$LOG" | grep "miss ratio" | grep -v Byte | tail -1 | grep -oP 'miss ratio \K[0-9.]+' | head -1)
  echo "  Result: MR = ${MR:-FAILED}"
  echo ""
done

echo "=== Summary ==="
printf "%-15s %10s\n" "State Group" "Miss Ratio"
printf "%-15s %10s\n" "-----------" "----------"
for name in "${TEST_NAMES[@]}"; do
  LOG="tmp/rl_state2_${name}_meta_8M.log"
  MR=$(cat "$LOG" 2>/dev/null | grep "miss ratio" | grep -v Byte | tail -1 | grep -oP 'miss ratio \K[0-9.]+' | head -1)
  printf "%-15s %10s\n" "$name" "${MR:-N/A}"
done
