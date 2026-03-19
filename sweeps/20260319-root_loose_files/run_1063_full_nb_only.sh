#!/bin/bash
# ====================================================================
# 只重跑 1063 full_nb 轮 (full-req nonblocked)
# ====================================================================
set -e
cd "$(dirname "$0")/.."

TRACE="data/TencentCBS/1063.oracleGeneral.zst"

ALL_OFF="LOH_INCLUDE_HIT_MISS_FEATURES=0 LOH_INCLUDE_CACHE_FEATURES=0"
ALL_OFF+=" LOH_INCLUDE_CANDIDATE_FEATURES=0 LOH_INCLUDE_TOPK_CANDIDATE_FEATURES=0"
ALL_OFF+=" LOH_INCLUDE_AVGTOPK_CANDIDATE_FEATURES=0 LOH_INCLUDE_REQUEST=0"

COMMON="LOH_SCORE_USE_COMPOUND=1 LOH_SCORE_USE_IRT=0 LOH_FEATURE_LOG1P=1"
COMMON+=" LOH_STRUCTURED_CANDIDATES=96 LOH_RANDOM_CANDIDATES=64"
COMMON+=" LOH_SKIP_PIP_INSTALL=1 LOH_BUILD_RELEASE=1"

declare -a TEST_NAMES=(baseline hit_miss cache candidate avgtopk request)
declare -A TEST_FLAGS
TEST_FLAGS[baseline]=""
TEST_FLAGS[hit_miss]="LOH_INCLUDE_HIT_MISS_FEATURES=1"
TEST_FLAGS[cache]="LOH_INCLUDE_CACHE_FEATURES=1"
TEST_FLAGS[candidate]="LOH_INCLUDE_CANDIDATE_FEATURES=1"
TEST_FLAGS[avgtopk]="LOH_INCLUDE_AVGTOPK_CANDIDATE_FEATURES=1"
TEST_FLAGS[request]="LOH_INCLUDE_REQUEST=1"

echo "########################################################################"
echo "# Re-run: full_nb (ALL requests, nonblocked) for 1063"
echo "########################################################################"

for name in "${TEST_NAMES[@]}"; do
  extra="${TEST_FLAGS[$name]}"
  LOG="tmp/rl_state_1063_full_nb_${name}.log"
  echo "========================================"
  echo "[$(date +%H:%M:%S)] full_nb/${name} (extra: ${extra:-none})"
  echo "  Log → $LOG"

  ENV_STR="$ALL_OFF $COMMON LOH_WAIT_MODE=nonblocked LOH_DEBUG_LEVEL=0"
  ENV_STR+=" CACHESIM_NUM_REQ=ALL"
  if [ -n "$extra" ]; then
    ENV_STR+=" $extra"
  fi

  eval "env $ENV_STR bash scripts/test_loh_rl_sb3.sh \"$TRACE\" 0.1" > "$LOG" 2>&1 || true

  MR=$(grep "miss ratio" "$LOG" | grep -v Byte | tail -1 | grep -oP 'miss ratio \K[0-9.]+' | head -1)
  echo "  Result: MR = ${MR:-FAILED}"
done

echo ""
echo "========== FULL_NB SUMMARY =========="
printf "%-12s %-12s\n" "State" "full_nb"
printf "%-12s %-12s\n" "-----" "-------"
for name in "${TEST_NAMES[@]}"; do
  MR=$(grep "miss ratio" "tmp/rl_state_1063_full_nb_${name}.log" 2>/dev/null | grep -v Byte | tail -1 | grep -oP 'miss ratio \K[0-9.]+' | head -1)
  printf "%-12s %-12s\n" "$name" "${MR:-N/A}"
done

echo ""
echo "Done at $(date)"
