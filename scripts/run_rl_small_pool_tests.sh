#!/bin/bash
# RL Small Candidate Pool Tests: 3 traces × 2 pool sizes (48, 32)
set -e

CACHESIM="/home/dingkp/libCacheSim/_build_dbg/bin/cachesim"
PY_SCRIPT="/home/dingkp/libCacheSim/scripts/loh_actor_critic_sb3.py"
RESULT_FILE="/tmp/rl_small_pool_results.txt"

TRACE_1063="data/TencentCBS/1063.oracleGeneral.zst"
TRACE_WIKI="data/WikiCDN/wiki_2019t.oracleGeneral.zst"
TRACE_META="data/MetaCDN/meta_reag.oracleGeneral.zst"

NUM_REQ=3000000

echo "=== RL Small Pool Tests ===" | tee "$RESULT_FILE"
echo "Start: $(date)" | tee -a "$RESULT_FILE"

run_one_rl_test() {
    local TRACE="$1"
    local TRACE_NAME="$2"
    local CAND_SIZE="$3"
    local SHM_KEY="$4"
    local EXTRA_ENV="$5"
    local EXTRA_PARAMS="$6"

    local LOG_C="/tmp/rl_${TRACE_NAME}_${CAND_SIZE}_cachesim.log"
    local LOG_PY="/tmp/rl_${TRACE_NAME}_${CAND_SIZE}_python.log"
    local SHM_FILE="/dev/shm/loh_ac_${SHM_KEY}"

    echo "" | tee -a "$RESULT_FILE"
    echo ">>> Test: ${TRACE_NAME} candidates=${CAND_SIZE} SHM_KEY=${SHM_KEY}" | tee -a "$RESULT_FILE"
    echo "    $(date)"

    # Cleanup
    rm -f "$SHM_FILE" 2>/dev/null || true
    rm -f "$LOG_C" "$LOG_PY" 2>/dev/null || true

    # Common env vars
    export LOH_ENABLE_RL=1
    export LOH_SHM_KEY="$SHM_KEY"
    export LOH_SCORE_USE_IRT=1
    export LOH_USE_HEURISTIC_SIGNS=1
    export LOH_USE_SOFTMAX=1
    export LOH_FEATURE_LOG1P=1
    export LOH_FEATURE_LOG1P_RECIPROCAL=0
    export LOH_ENABLE_FEATURE_NORMALIZATION=1
    export LOH_SCORE_MODEL=linear
    export LOH_MAX_CANDIDATES="$CAND_SIZE"
    export LOH_RL_ALGO=SAC
    export LOH_ENABLE_SEMAPHORE=1
    export LOH_DISABLE_SEMAPHORE=0
    export LOH_REWARD_TYPE=delta

    # Apply extra env
    eval "$EXTRA_ENV"

    # Start Python RL
    python3 "$PY_SCRIPT" > "$LOG_PY" 2>&1 &
    local PY_PID=$!
    echo "    Python PID: $PY_PID"

    # Wait for SHM file (max 120s)
    local waited=0
    while [ ! -f "$SHM_FILE" ] && [ $waited -lt 120 ]; do
        sleep 1
        waited=$((waited + 1))
    done
    if [ ! -f "$SHM_FILE" ]; then
        echo "    ERROR: SHM file not created after 120s" | tee -a "$RESULT_FILE"
        kill $PY_PID 2>/dev/null || true
        return 1
    fi
    echo "    SHM ready after ${waited}s"
    sleep 2

    # Start cachesim
    $CACHESIM "$TRACE" oracleGeneral LOH 0.1 --num-req=$NUM_REQ $EXTRA_PARAMS -v 0 > "$LOG_C" 2>&1 &
    local C_PID=$!
    echo "    Cachesim PID: $C_PID"

    # Wait for cachesim to finish (max 900s)
    local c_waited=0
    while kill -0 $C_PID 2>/dev/null && [ $c_waited -lt 900 ]; do
        sleep 5
        c_waited=$((c_waited + 5))
    done

    if kill -0 $C_PID 2>/dev/null; then
        echo "    WARNING: cachesim timed out, killing"
        kill $C_PID 2>/dev/null || true
    fi

    sleep 2
    kill $PY_PID 2>/dev/null || true
    wait $PY_PID 2>/dev/null || true
    wait $C_PID 2>/dev/null || true

    local RESULT=$(grep "miss ratio" "$LOG_C" | tail -1)
    echo "    RESULT: $RESULT"
    echo "${TRACE_NAME} cand=${CAND_SIZE}: $RESULT" | tee -a "$RESULT_FILE"

    rm -f "$SHM_FILE" 2>/dev/null || true
    unset LOH_SCORE_USE_COMPOUND LOH_RL_TEMPERATURE LOH_RL_ENTROPY_SCALE LOH_AC_CPD LOH_SYNC_INTERVAL 2>/dev/null || true
}

cd /home/dingkp/libCacheSim

# 1063: 48 and 32
run_one_rl_test "$TRACE_1063" "1063" 48 "41048" \
    "export LOH_SCORE_USE_COMPOUND=1; export LOH_AC_CPD=1; export LOH_SYNC_INTERVAL=200; export LOH_RL_TEMPERATURE=1.3; export LOH_RL_ENTROPY_SCALE=0.5" \
    "--eviction-params=miss-ratio-weight=1.0"

run_one_rl_test "$TRACE_1063" "1063" 32 "41032" \
    "export LOH_SCORE_USE_COMPOUND=1; export LOH_AC_CPD=1; export LOH_SYNC_INTERVAL=200; export LOH_RL_TEMPERATURE=1.3; export LOH_RL_ENTROPY_SCALE=0.5" \
    "--eviction-params=miss-ratio-weight=1.0"

# wiki: 48 and 32
run_one_rl_test "$TRACE_WIKI" "wiki" 48 "42048" \
    "export LOH_SCORE_USE_COMPOUND=1; export LOH_AC_CPD=1; export LOH_SYNC_INTERVAL=1000" \
    "--eviction-params=miss-ratio-weight=1.0"

run_one_rl_test "$TRACE_WIKI" "wiki" 32 "42032" \
    "export LOH_SCORE_USE_COMPOUND=1; export LOH_AC_CPD=1; export LOH_SYNC_INTERVAL=1000" \
    "--eviction-params=miss-ratio-weight=1.0"

# meta: 48 and 32
run_one_rl_test "$TRACE_META" "meta" 48 "43048" \
    "export LOH_SCORE_USE_COMPOUND=0; export LOH_SYNC_INTERVAL=200; export LOH_RL_TEMPERATURE=1.3; export LOH_RL_ENTROPY_SCALE=0.5" \
    ""

run_one_rl_test "$TRACE_META" "meta" 32 "43032" \
    "export LOH_SCORE_USE_COMPOUND=0; export LOH_SYNC_INTERVAL=200; export LOH_RL_TEMPERATURE=1.3; export LOH_RL_ENTROPY_SCALE=0.5" \
    ""

echo ""
echo "=== All small pool RL tests complete ===" | tee -a "$RESULT_FILE"
echo "End: $(date)" | tee -a "$RESULT_FILE"
cat "$RESULT_FILE"
