#!/bin/bash
# compound=0, irt=0, 纯随机候选 RL 测试
# 3 维特征: recency, freq, size (最简模式)
# CAND=96, 3M requests, 3 traces
set -e
cd /home/dingkp/libCacheSim

for spec in "data/MetaCDN/meta_reag.oracleGeneral.zst meta 1 0" "data/TencentCBS/1063.oracleGeneral.zst 1063 1 0" "data/WikiCDN/wiki_2019t.oracleGeneral.zst wiki 0 1"; do
  read -r trace name log1p recip <<< "$spec"
  logfile="tmp/rl_${name}_3feat_randonly_3M.log"
  echo "=== [$(date '+%H:%M:%S')] Starting: ${name} 3-Feature+RandOnly (compound=0, irt=0) ==="
  pkill -9 -f "loh_actor_critic" 2>/dev/null || true
  rm -f /dev/shm/loh_ac_*
  sleep 2
  LOH_CACHESIM_BIN=_build_rel/bin/cachesim \
  LOH_SKIP_PIP_INSTALL=1 LOH_SKIP_BUILD=1 LOH_DEBUG_LEVEL=0 \
  LOH_WAIT_MODE=nonblocked LOH_PIN_CPU=0 \
  LOH_FEATURE_LOG1P=$log1p LOH_FEATURE_LOG1P_RECIPROCAL=$recip \
  LOH_SCORE_USE_COMPOUND=0 LOH_SCORE_USE_IRT=0 \
  LOH_RANDOM_SAMPLE_COUNT=64 LOH_MAX_CANDIDATES=96 \
  LOH_RANDOM_ONLY_CANDIDATES=1 \
  CACHESIM_NUM_REQ=3000000 \
  bash scripts/test_loh_rl_sb3.sh "$trace" 0.1 > "$logfile" 2>&1
  result=$(grep "miss ratio" "$logfile" | tail -1)
  echo "=== [$(date '+%H:%M:%S')] Done: ${name} rc=$? ==="
  echo "  $result"
done
echo "=== ALL 3-FEATURE+RANDONLY TESTS DONE ==="
