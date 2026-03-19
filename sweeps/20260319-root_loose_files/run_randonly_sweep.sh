#!/bin/bash
# Random-Only RL sweep: MAX_CAND in {32, 256}, 3 traces, 8M, serial
# MAX_CAND=96 already done, skip.
set -e

cd /home/dingkp/libCacheSim

COMMON_ENV="LOH_SKIP_PIP_INSTALL=1 LOH_SKIP_BUILD=1 LOH_DEBUG_LEVEL=0 \
LOH_WAIT_MODE=nonblocked LOH_PIN_CPU=0 \
LOH_SCORE_USE_COMPOUND=1 LOH_SCORE_USE_IRT=0 \
LOH_RANDOM_SAMPLE_COUNT=64 LOH_RANDOM_ONLY_CANDIDATES=1"

run_test() {
  local trace=$1 trace_name=$2 feat_log1p=$3 feat_recip=$4 max_cand=$5
  local logfile="tmp/rl_${trace_name}_randonly_cand${max_cand}_8M.log"

  echo "=== [$(date '+%H:%M:%S')] Starting: ${trace_name} CAND=${max_cand} ==="

  # cleanup
  pkill -9 -f "loh_actor_critic" 2>/dev/null || true
  rm -f /dev/shm/loh_ac_*
  sleep 2

  CACHESIM_NUM_REQ=8000000 LOH_CACHESIM_BIN=_build_rel/bin/cachesim \
  LOH_SKIP_PIP_INSTALL=1 LOH_SKIP_BUILD=1 LOH_DEBUG_LEVEL=0 \
  LOH_WAIT_MODE=nonblocked LOH_PIN_CPU=0 \
  LOH_FEATURE_LOG1P=$feat_log1p LOH_FEATURE_LOG1P_RECIPROCAL=$feat_recip \
  LOH_SCORE_USE_COMPOUND=1 LOH_SCORE_USE_IRT=0 \
  LOH_RANDOM_SAMPLE_COUNT=64 LOH_MAX_CANDIDATES=$max_cand \
  LOH_RANDOM_ONLY_CANDIDATES=1 \
  bash scripts/test_loh_rl_sb3.sh "$trace" 0.1 > "$logfile" 2>&1

  local rc=$?
  local result=$(grep "miss ratio" "$logfile" | tail -1)
  echo "=== [$(date '+%H:%M:%S')] Done: ${trace_name} CAND=${max_cand} rc=${rc} ==="
  echo "  ${result}"
  echo "${trace_name},${max_cand},${result}" >> tmp/randonly_sweep_results.csv
}

echo "trace,max_cand,raw_result" > tmp/randonly_sweep_results.csv

# Meta (LOG1P, fastest)
run_test "data/MetaCDN/meta_reag.oracleGeneral.zst" "meta" 1 0 32
run_test "data/MetaCDN/meta_reag.oracleGeneral.zst" "meta" 1 0 256

# 1063 (LOG1P)
run_test "data/TencentCBS/1063.oracleGeneral.zst" "1063" 1 0 32
run_test "data/TencentCBS/1063.oracleGeneral.zst" "1063" 1 0 256

# Wiki (RECIPROCAL, slowest)
run_test "data/WikiCDN/wiki_2019t.oracleGeneral.zst" "wiki" 0 1 32
run_test "data/WikiCDN/wiki_2019t.oracleGeneral.zst" "wiki" 0 1 256

echo ""
echo "=== ALL SWEEP DONE ==="
echo "Results CSV: tmp/randonly_sweep_results.csv"
cat tmp/randonly_sweep_results.csv
