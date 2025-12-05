#!/usr/bin/env bash
set -euo pipefail
cd /home/dingkp/libCacheSim

mkdir -p runs/full_trace

run_full() {
    local TRACE="$1"
    local NAME="$2"
    local W="$3"
    local LOG="runs/full_trace/${NAME}_full.log"

    SHM_KEY=$((RANDOM * 1000 + $$))
    rm -f "/dev/shm/loh_ac_${SHM_KEY}" 2>/dev/null || true

    echo "[$(date '+%H:%M:%S')] $NAME 完整 trace (权重: $W)..." >&2

    LOH_SHM_KEY="$SHM_KEY" LOH_FIXED_WEIGHTS="$W" EVICTION_ALGO="LOH-mr-blocked" \
        python3 scripts/loh_constant_weights.py &
    PY_PID=$!

    for i in $(seq 1 30); do
        [ -f "/dev/shm/loh_ac_${SHM_KEY}" ] && break
        sleep 0.5
    done

    LOH_SHM_KEY="$SHM_KEY" \
        _build_dbg/bin/cachesim "$TRACE" oracleGeneral LOH-mr-blocked 0.1 -v 1 2>&1 | tee "$LOG" | tail -3

    kill $PY_PID 2>/dev/null || true
    rm -f "/dev/shm/loh_ac_${SHM_KEY}" 2>/dev/null || true
    echo "$NAME done" >&2
}

echo "=== 最优权重完整 Trace 测试 ===" >&2

run_full "data/MetaCDN/meta_reag.oracleGeneral.zst" "meta" "0,0,1,0,0,0"
run_full "data/WikiCDN/wiki_2019t.oracleGeneral.zst" "wiki" "3,1,4,0,0,0"
run_full "data/TencentCBS/1063.oracleGeneral.zst" "tencent" "1,0,3,0,0,0"

echo "=== All Full Trace Done ===" >&2
