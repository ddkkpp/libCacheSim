#!/bin/bash
# 批量测试 LOH penalty 所有组合 (4 scale × 6 formula × 2 pos = 48 组)
# 使用 3M 请求在 1063 trace 上测试

set -euo pipefail

TRACE="data/TencentCBS/1063.oracleGeneral.zst"
RESULT_DIR="tmp/penalty_sweep"
mkdir -p "$RESULT_DIR"

SCALES=(reciprocal log survival binary)
FORMULAS=(relative centered one_minus neg net net2)
POS_VALUES=(0 1)

TOTAL=$((${#SCALES[@]} * ${#FORMULAS[@]} * ${#POS_VALUES[@]}))
COUNT=0
SUMMARY_FILE="$RESULT_DIR/summary.csv"

echo "scale,formula,pos,miss_ratio,byte_miss_ratio,mqps" > "$SUMMARY_FILE"
echo "=== Penalty Batch Test: $TOTAL combinations ==="
echo "Trace: $TRACE, Requests: 3M"
echo ""

for scale in "${SCALES[@]}"; do
  for formula in "${FORMULAS[@]}"; do
    for pos in "${POS_VALUES[@]}"; do
      COUNT=$((COUNT + 1))
      TAG="${scale}_${formula}_pos${pos}"
      LOG="$RESULT_DIR/${TAG}.log"
      echo "[$COUNT/$TOTAL] scale=$scale formula=$formula pos=$pos ..."

      LOH_BUILD_RELEASE=1 \
      LOH_ENABLE_PENALTY=1 \
      LOH_DEBUG_LEVEL=0 \
      LOH_PERF_PROFILING=0 \
      LOH_ENABLE_PROFILING=0 \
      CACHESIM_VERBOSE=0 \
      LOH_FEATURE_LOG1P=1 \
      LOH_RANDOM_CANDIDATES=96 \
      LOH_STRUCTURED_CANDIDATES=96 \
      LOH_TAIL_SAMPLE=1 \
      LOH_TAIL_SAMPLE_DECAY=0.99 \
      LOH_ADAPTIVE_BUDGET=1 \
      LOH_ASYNC_TRAIN=1 \
      LOH_WAIT_MODE=nonblocked \
      LOH_SCORE_USE_COMPOUND=1 \
      LOH_SCORE_USE_IRT=0 \
      LOH_SKIP_BUILD=1 \
      LOH_PENALTY_TRACE_ALL=1 \
      LOH_PENALTY_SCALE="$scale" \
      LOH_PENALTY_REWARD_FORMULA="$formula" \
      LOH_PENALTY_SEND_POSITIVE="$pos" \
      CACHESIM_NUM_REQ=3000000 \
      bash scripts/test_loh_rl_sb3.sh "$TRACE" > "$LOG" 2>&1 || true

      # 提取结果
      RESULT_LINE=$(grep -o "miss ratio [0-9.]*.*throughput [0-9.]* MQPS" "$LOG" 2>/dev/null | tail -1 || echo "")
      if [ -n "$RESULT_LINE" ]; then
        MR=$(echo "$RESULT_LINE" | grep -o "miss ratio [0-9.]*" | head -1 | awk '{print $3}')
        BMR=$(echo "$RESULT_LINE" | grep -o "byte miss ratio [0-9.]*" | awk '{print $4}')
        MQPS=$(echo "$RESULT_LINE" | grep -o "throughput [0-9.]*" | awk '{print $2}')
        echo "  -> MR=$MR BMR=$BMR MQPS=$MQPS"
        echo "$scale,$formula,$pos,$MR,$BMR,$MQPS" >> "$SUMMARY_FILE"
      else
        echo "  -> FAILED (no result line found)"
        echo "$scale,$formula,$pos,FAIL,FAIL,FAIL" >> "$SUMMARY_FILE"
      fi
    done
  done
done

echo ""
echo "=== All $TOTAL tests completed ==="
echo "Summary: $SUMMARY_FILE"
echo ""
cat "$SUMMARY_FILE"
