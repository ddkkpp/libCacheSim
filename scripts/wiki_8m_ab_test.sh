#!/bin/bash
# Wiki 8M A/B 对比：调整 SAC 训练超参数
set -e

cd "$(cd "$(dirname "$0")" && pwd)/.."
TIMESTAMP=$(date +%m%d_%H%M%S)
mkdir -p tmp

echo "========================================="
echo "Wiki 8M A/B: SAC train_freq / gradient_steps / batch_size"
echo "Started: $(date)"
echo "========================================="

# 公共配置
export LOH_SCORE_USE_COMPOUND=1
export LOH_SCORE_USE_IRT=0
export LOH_FEATURE_LOG1P=1
export LOH_RANDOM_CANDIDATES=64
export LOH_SKIP_PIP_INSTALL=1
export LOH_SKIP_BUILD=1
export LOH_DEBUG_LEVEL=0
export LOH_WAIT_MODE=nonblocked
export LOH_PIN_CPU=0
export LOH_CACHESIM_BIN=_build_rel/bin/cachesim
export LOH_CHECKPOINT_FREQ=50000
export CACHESIM_NUM_REQ=8000000

TRACE="data/WikiCDN/wiki_2019t.oracleGeneral.zst"
CACHE=0.1

# === Test A: 原始参数 ===
echo ""
echo "========================================="
echo "[A] 原始参数: train_freq=16, gradient_steps=1, batch_size=256"
echo "========================================="
rm -f /dev/shm/loh_ac_* 2>/dev/null || true
pkill -f "loh_actor_critic_sb3" 2>/dev/null || true
sleep 1

export SAC_TRAIN_FREQ=16
export SAC_GRADIENT_STEPS=1
export SAC_BATCH_SIZE=256

A_LOG="tmp/wiki_8m_A_orig_${TIMESTAMP}.log"
A_START=$(date +%s)
bash scripts/test_loh_rl_sb3.sh "$TRACE" "$CACHE" > "$A_LOG" 2>&1 || true
A_END=$(date +%s)
A_ELAPSED=$((A_END - A_START))
A_RESULT=$(grep "MQPS" "$A_LOG" | tail -1)
A_UPDATES=$(grep "n_updates" "$A_LOG" | tail -1 || echo "N/A")

echo "  [A] Duration: ${A_ELAPSED}s"
echo "  [A] Result: ${A_RESULT}"
echo "  [A] n_updates: ${A_UPDATES}"
echo "  [A] Log: ${A_LOG}"

# 清理
rm -f /dev/shm/loh_ac_* 2>/dev/null || true
pkill -f "loh_actor_critic_sb3" 2>/dev/null || true
sleep 2

# === Test B: 方案1 参数 ===
echo ""
echo "========================================="
echo "[B] 方案1: train_freq=64, gradient_steps=4, batch_size=512"
echo "========================================="
rm -f /dev/shm/loh_ac_* 2>/dev/null || true

export SAC_TRAIN_FREQ=64
export SAC_GRADIENT_STEPS=4
export SAC_BATCH_SIZE=512

B_LOG="tmp/wiki_8m_B_tuned_${TIMESTAMP}.log"
B_START=$(date +%s)
bash scripts/test_loh_rl_sb3.sh "$TRACE" "$CACHE" > "$B_LOG" 2>&1 || true
B_END=$(date +%s)
B_ELAPSED=$((B_END - B_START))
B_RESULT=$(grep "MQPS" "$B_LOG" | tail -1)
B_UPDATES=$(grep "n_updates" "$B_LOG" | tail -1 || echo "N/A")

echo "  [B] Duration: ${B_ELAPSED}s"
echo "  [B] Result: ${B_RESULT}"
echo "  [B] n_updates: ${B_UPDATES}"
echo "  [B] Log: ${B_LOG}"

# 清理
rm -f /dev/shm/loh_ac_* 2>/dev/null || true
pkill -f "loh_actor_critic_sb3" 2>/dev/null || true

echo ""
echo "========================================="
echo "Summary"
echo "-----------------------------------------"
echo "[A] Original (tf=16,gs=1,bs=256): ${A_ELAPSED}s | ${A_RESULT}"
echo "[B] Tuned    (tf=64,gs=4,bs=512): ${B_ELAPSED}s | ${B_RESULT}"
echo "========================================="
