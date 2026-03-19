#!/bin/bash
# Test the new adaptive budget (score-based) against all 3 traces
# Matches §19.2 config (rand96+struct96+decay, adaptive_budget=1)
set -e
cd /home/dingkp/libCacheSim

# Common env
export LOH_WAIT_MODE=nonblocked
export LOH_SCORE_USE_COMPOUND=1
export LOH_SCORE_USE_IRT=0
export LOH_ADAPTIVE_BUDGET=1
export LOH_STRUCTURED_CANDIDATES=96
export LOH_RANDOM_CANDIDATES=96
export LOH_TAIL_SAMPLE=1
export LOH_TAIL_SAMPLE_DECAY=0.99
export LOH_AUTO_FEATURE_MODE=1

BIN=_build_rel/bin/cachesim
EV="--eviction-params=miss-ratio-weight=1.0"

echo "=== Test 1: 1063 (AUTO feature, full trace) ==="
date
$BIN data/TencentCBS/1063.oracleGeneral.zst oracleGeneral LOH 0.1 $EV -v 1 \
  > tmp/adaptive_1063.log 2>&1
echo "1063 done:"
grep "miss ratio" tmp/adaptive_1063.log | tail -1

echo ""
echo "=== Test 2: meta (AUTO feature, full trace) ==="
date
$BIN data/MetaCDN/meta_reag.oracleGeneral.zst oracleGeneral LOH 0.1 $EV -v 1 \
  > tmp/adaptive_meta.log 2>&1
echo "meta done:"
grep "miss ratio" tmp/adaptive_meta.log | tail -1

echo ""
echo "=== Test 3: wiki (AUTO feature, full trace) ==="
date
$BIN data/WikiCDN/wiki_2019t.oracleGeneral.zst oracleGeneral LOH 0.1 $EV -v 1 \
  > tmp/adaptive_wiki.log 2>&1
echo "wiki done:"
grep "miss ratio" tmp/adaptive_wiki.log | tail -1

echo ""
echo "=== ALL DONE ==="
date
