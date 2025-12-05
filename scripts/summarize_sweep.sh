#!/usr/bin/env bash
# 汇总 sweep 结果，提取每个权重组合的 miss ratio 和 byte miss ratio
# 用法: bash scripts/summarize_sweep.sh [trace_prefix]
# 例如: bash scripts/summarize_sweep.sh meta
#       bash scripts/summarize_sweep.sh wiki
#       bash scripts/summarize_sweep.sh 1063

TRACE_PREFIX=${1:-}
LOG_DIR="runs/constant_weight"

if [ -n "$TRACE_PREFIX" ]; then
  PATTERN="${LOG_DIR}/loh_const_*_${TRACE_PREFIX}_*.log"
else
  PATTERN="${LOG_DIR}/loh_const_*.log"
fi

echo "=== Sweep Results Summary ==="
echo "Pattern: $PATTERN"
echo ""
echo "weights,miss_ratio,byte_miss_ratio,trace"

for log in $PATTERN; do
  [ -f "$log" ] || continue

  # 从文件名提取权重: loh_const_TIMESTAMP_TRACE_w1_w2_w3_w4_w5_w6.log
  fname=$(basename "$log" .log)
  # 提取 trace 名和权重
  trace=$(echo "$fname" | sed -E 's/loh_const_[0-9]+_[0-9]+_([^_]+)_.*/\1/')
  weights=$(echo "$fname" | sed -E 's/loh_const_[0-9]+_[0-9]+_[^_]+_(.*)$/\1/' | tr '_' ',')

  # 从日志提取 miss ratio 和 byte miss ratio
  result=$(grep -E "miss ratio [0-9.]+" "$log" | tail -1)
  if [ -n "$result" ]; then
    mr=$(echo "$result" | grep -oP 'miss ratio \K[0-9.]+')
    bmr=$(echo "$result" | grep -oP 'byte miss ratio \K[0-9.]+')
    echo "${weights},${mr},${bmr},${trace}"
  fi
done | sort -t',' -k2 -n

echo ""
echo "=== Top 10 Best (lowest miss ratio) ==="
for log in $PATTERN; do
  [ -f "$log" ] || continue
  fname=$(basename "$log" .log)
  trace=$(echo "$fname" | sed -E 's/loh_const_[0-9]+_[0-9]+_([^_]+)_.*/\1/')
  weights=$(echo "$fname" | sed -E 's/loh_const_[0-9]+_[0-9]+_[^_]+_(.*)$/\1/' | tr '_' ',')
  result=$(grep -E "miss ratio [0-9.]+" "$log" | tail -1)
  if [ -n "$result" ]; then
    mr=$(echo "$result" | grep -oP 'miss ratio \K[0-9.]+')
    bmr=$(echo "$result" | grep -oP 'byte miss ratio \K[0-9.]+')
    echo "${weights},${mr},${bmr},${trace}"
  fi
done | sort -t',' -k2 -n | head -10
