#!/bin/bash
export LOH_WAIT_MODE=nonblocked
export LOH_SCORE_USE_COMPOUND=1
export LOH_SCORE_USE_IRT=0
export LOH_ADAPTIVE_BUDGET=1
export LOH_STRUCTURED_CANDIDATES=96
export LOH_RANDOM_CANDIDATES=96
export LOH_TAIL_SAMPLE=1
export LOH_TAIL_SAMPLE_DECAY=0.99
export LOH_FEATURE_MODE=LOG1P

_build_rel/bin/cachesim data/TencentCBS/1063.oracleGeneral.zst oracleGeneral LOH 0.1 \
  --eviction-params="miss-ratio-weight=1.0" -v 1 --num-req=3000000 \
  > tmp/test_1063_adaptive.log 2>&1

echo "DONE exit=$?"
