#!/usr/bin/env bash
# 对三个 trace 的最优权重进行 refine（只搜索邻域，不重复 0/1/2）
# Meta: 0,0,1,0,0,0 -> 搜索 w3=3,4,5
# Wiki: 2,1,2,0,0,0 -> 搜索 w1=3,4, w2=3, w3=3,4
# Tencent: 1,0,2,0,0,0 -> 搜索 w1=3, w3=3,4

set -euo pipefail
cd /home/dingkp/libCacheSim

mkdir -p runs/refine

run_one() {
    local TRACE="$1"
    local NAME="$2"
    local W="$3"
    local LOG="runs/refine/${NAME}_${W//,/_}.log"

    SHM_KEY=$((RANDOM * 1000 + $$))
    rm -f "/dev/shm/loh_ac_${SHM_KEY}" 2>/dev/null || true

    echo "[$(date '+%H:%M:%S')] $NAME W=$W ..." >&2

    LOH_SHM_KEY="$SHM_KEY" LOH_FIXED_WEIGHTS="$W" EVICTION_ALGO="LOH-mr-blocked" \
        python3 scripts/loh_constant_weights.py &
    PY_PID=$!

    for i in $(seq 1 30); do
        [ -f "/dev/shm/loh_ac_${SHM_KEY}" ] && break
        sleep 0.5
    done

    LOH_SHM_KEY="$SHM_KEY" \
        _build_dbg/bin/cachesim "$TRACE" oracleGeneral LOH-mr-blocked 0.1 \
        --num-req=3000000 -v 1 2>&1 | tee "$LOG" | grep -E "miss ratio"

    kill $PY_PID 2>/dev/null || true
    rm -f "/dev/shm/loh_ac_${SHM_KEY}" 2>/dev/null || true
}

# Meta refine: 基础 0,0,1,0,0,0 -> 扩展 w3 到 3,4,5
echo "=== Meta Refine (base: 0,0,1,0,0,0) ===" >&2
for w3 in 3 4 5; do
    run_one "data/MetaCDN/meta_reag.oracleGeneral.zst" "meta" "0,0,$w3,0,0,0"
done

# Wiki refine: 基础 2,1,2,0,0,0 -> 扩展 w1=3,4, w2=3, w3=3,4
echo "=== Wiki Refine (base: 2,1,2,0,0,0) ===" >&2
for w1 in 3 4; do
for w2 in 0 1 2 3; do
for w3 in 1 2 3 4; do
    run_one "data/WikiCDN/wiki_2019t.oracleGeneral.zst" "wiki" "$w1,$w2,$w3,0,0,0"
done; done; done

# Tencent refine: 基础 1,0,2,0,0,0 -> 扩展 w1=3, w3=3,4
echo "=== Tencent Refine (base: 1,0,2,0,0,0) ===" >&2
for w1 in 0 1 2 3; do
for w3 in 3 4; do
    run_one "data/TencentCBS/1063.oracleGeneral.zst" "tencent" "$w1,0,$w3,0,0,0"
done; done

echo "=== All Refine Done ===" >&2
