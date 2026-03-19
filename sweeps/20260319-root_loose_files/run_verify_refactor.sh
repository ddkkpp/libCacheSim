#!/bin/bash
# 验证重构后结果一致性：Meta compound RandOnly cand192 8M
# 旧配置：LOH_MAX_CANDIDATES=192 LOH_RANDOM_ONLY_CANDIDATES=1 LOH_RANDOM_SAMPLE_COUNT=64
# 新配置：LOH_STRUCTURED_CANDIDATES=0 LOH_RANDOM_CANDIDATES=192
# 预期 MR ≈ 0.3257

cd "$(dirname "$0")/.."

LOG="tmp/rl_verify_meta_cand192_8M.log"

LOH_SCORE_USE_COMPOUND=1 \
  LOH_SCORE_USE_IRT=0 \
  LOH_FEATURE_LOG1P=1 \
  LOH_STRUCTURED_CANDIDATES=0 \
  LOH_RANDOM_CANDIDATES=192 \
  LOH_SKIP_BUILD=1 \
  LOH_SKIP_PIP_INSTALL=1 \
  CACHESIM_NUM_REQ=8000000 \
  bash scripts/test_loh_rl_sb3.sh > "$LOG" 2>&1

echo "=== Result ==="
grep "miss ratio" "$LOG" | tail -1
