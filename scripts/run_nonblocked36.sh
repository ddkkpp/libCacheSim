#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

TRACE="${1:-data/TencentCBS/1063.oracleGeneral.zst}"
CACHE_SIZE="${2:-0.1}"
NUM_REQ="${3:-8000000}"
TAG="${4:-nonblocked36_$(date +%m%d_%H%M%S)}"
LOG_DIR="tmp/${TAG}"
mkdir -p "$LOG_DIR"

export LOH_WAIT_MODE=nonblocked
export LOH_ASYNC_TRAIN=0
export LOH_ENABLE_SEMAPHORE="${LOH_ENABLE_SEMAPHORE:-1}"
export LOH_SCORE_USE_COMPOUND="${LOH_SCORE_USE_COMPOUND:-1}"
export LOH_SCORE_USE_IRT="${LOH_SCORE_USE_IRT:-0}"
export LOH_BUILD_RELEASE="${LOH_BUILD_RELEASE:-1}"
export LOH_SKIP_BUILD="${LOH_SKIP_BUILD:-1}"
export LOH_SKIP_PIP_INSTALL="${LOH_SKIP_PIP_INSTALL:-1}"
# 直接传递 NUM_REQ，让 test_loh_rl_sb3.sh 处理 ALL/0 → unset 逻辑
export CACHESIM_NUM_REQ="$NUM_REQ"
export LOH_RANDOM_CANDIDATES="${LOH_RANDOM_CANDIDATES:-64}"
# 保持“3.6 原始 non-blocked”特征：
# 1) C 端 nonblocked
# 2) Python 不开异步训练
# 3) Python 不限制 torch 线程（依赖脚本当前默认）

echo "[run_nonblocked36] trace=$TRACE"
echo "[run_nonblocked36] cache_size=$CACHE_SIZE num_req=$NUM_REQ"
echo "[run_nonblocked36] log_dir=$LOG_DIR"
echo "[run_nonblocked36] LOH_WAIT_MODE=$LOH_WAIT_MODE LOH_ASYNC_TRAIN=$LOH_ASYNC_TRAIN LOH_RANDOM_CANDIDATES=$LOH_RANDOM_CANDIDATES"

bash scripts/test_loh_rl_sb3.sh "$TRACE" "$CACHE_SIZE" > "$LOG_DIR/run.log" 2>&1

echo "[run_nonblocked36] done"
echo "[run_nonblocked36] main log: $LOG_DIR/run.log"
LATEST_PY_LOG=$(ls -1t ac_sb3_*.log 2>/dev/null | head -1 || true)
LATEST_CS_LOG=$(ls -1t cachesim_sb3_*.log 2>/dev/null | head -1 || true)
if [[ -n "$LATEST_PY_LOG" ]]; then
  echo "[run_nonblocked36] python log: $LATEST_PY_LOG"
fi
if [[ -n "$LATEST_CS_LOG" ]]; then
  echo "[run_nonblocked36] cachesim log: $LATEST_CS_LOG"
fi
