#!/bin/bash
# Additive comparison: truly additive structured+random vs pure random
# Group B: 96 structured + 96 random (total ~192)
# Group C: 96 structured + 0 random  (total ~96, pure structured)
set -e
cd /home/dingkp/libCacheSim

run_test() {
  local trace=$1 trace_name=$2 feat_log1p=$3 feat_recip=$4 rsc=$5 group=$6
  local logfile="tmp/rl_${trace_name}_additive_${group}_8M.log"
  echo "=== [$(date '+%H:%M:%S')] ${group}: ${trace_name} RSC=${rsc} ==="
  pkill -9 -f "loh_actor_critic" 2>/dev/null || true
  rm -f /dev/shm/loh_ac_*
  sleep 2
  CACHESIM_NUM_REQ=8000000 LOH_CACHESIM_BIN=_build_rel/bin/cachesim \
  LOH_SKIP_PIP_INSTALL=1 LOH_SKIP_BUILD=1 LOH_DEBUG_LEVEL=0 \
  LOH_WAIT_MODE=nonblocked LOH_PIN_CPU=0 \
  LOH_FEATURE_LOG1P=$feat_log1p LOH_FEATURE_LOG1P_RECIPROCAL=$feat_recip \
  LOH_SCORE_USE_COMPOUND=1 LOH_SCORE_USE_IRT=0 \
  LOH_RANDOM_SAMPLE_COUNT=$rsc LOH_MAX_CANDIDATES=96 \
  LOH_RANDOM_ONLY_CANDIDATES=0 \
  bash scripts/test_loh_rl_sb3.sh "$trace" 0.1 > "$logfile" 2>&1
  local result=$(grep "miss ratio" "$logfile" | tail -1)
  echo "=== [$(date '+%H:%M:%S')] Done: ${group} ${trace_name} rc=$? ==="
  echo "  $result"
  echo "${group},${trace_name},$result" >> tmp/additive_results.csv
}

echo "group,trace,raw_result" > tmp/additive_results.csv

# Group B: 96 structured + 96 random (additive, total ~192)
for spec in "data/MetaCDN/meta_reag.oracleGeneral.zst meta 1 0" "data/TencentCBS/1063.oracleGeneral.zst 1063 1 0" "data/WikiCDN/wiki_2019t.oracleGeneral.zst wiki 0 1"; do
  read -r trace name log1p recip <<< "$spec"
  run_test "$trace" "$name" "$log1p" "$recip" 96 "groupB"
done

# Group C: 96 structured + 0 random (pure structured, total ~96)
for spec in "data/MetaCDN/meta_reag.oracleGeneral.zst meta 1 0" "data/TencentCBS/1063.oracleGeneral.zst 1063 1 0" "data/WikiCDN/wiki_2019t.oracleGeneral.zst wiki 0 1"; do
  read -r trace name log1p recip <<< "$spec"
  run_test "$trace" "$name" "$log1p" "$recip" 0 "groupC"
done

echo ""
echo "=== ADDITIVE COMPARISON DONE ==="
cat tmp/additive_results.csv
