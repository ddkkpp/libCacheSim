#!/usr/bin/env bash
# wiki 全量测试 - blocked 模式（C端等待Python回写权重）
# 目的：复现 0306 baseline 配置（默认 blocked + 默认 torch threads）
set -euo pipefail

cd "$(dirname "$0")/.."

TAG="wiki_blocked_$(date +%m%d_%H%M%S)"
LOG_DIR="tmp/rl_${TAG}"
mkdir -p "$LOG_DIR"

# === 预清理 ===
echo "[${TAG}] 预清理残留进程..."
pkill -f "loh_actor_critic_sb3" 2>/dev/null || true
pkill -f "cachesim.*wiki" 2>/dev/null || true
sleep 2
rm -f /dev/shm/loh_ac_9876

# === 配置 ===
# 关键：使用 blocked 模式（C等待Python响应），这是C端默认值
export LOH_WAIT_MODE=blocked
export LOH_SCORE_USE_COMPOUND=1
export LOH_SCORE_USE_IRT=0
export LOH_BUILD_RELEASE=1
export LOH_ENABLE_SEMAPHORE=1
export CACHESIM_NUM_REQ=ALL

# 不设置 torch.set_num_threads（已在脚本中注释掉）

TRACE="data/WikiCDN/wiki_2019t.oracleGeneral.zst"
CACHE_SIZE="0.1"

echo "[${TAG}] === Wiki 全量 (BLOCKED 模式 + 默认 threads) ==="
echo "[${TAG}] LOH_WAIT_MODE=${LOH_WAIT_MODE}"
echo "[${TAG}] Trace: ${TRACE}"
echo "[${TAG}] 日志目录: ${LOG_DIR}"

# === 启动 Python ===
echo "[${TAG}] 启动 Python RL..."
python3 scripts/loh_actor_critic_sb3.py > "${LOG_DIR}/ac_sb3.log" 2>&1 &
PY_PID=$!
echo "[${TAG}] Python PID: ${PY_PID}"

# === 等待 shared memory ===
echo "[${TAG}] 等待 /dev/shm/loh_ac_9876..."
for i in $(seq 1 60); do
    if [ -f /dev/shm/loh_ac_9876 ]; then
        echo "[${TAG}] shared memory 就绪 (${i}s)"
        break
    fi
    sleep 1
done
if [ ! -f /dev/shm/loh_ac_9876 ]; then
    echo "[${TAG}] ERROR: shared memory 未创建，退出"
    kill $PY_PID 2>/dev/null || true
    exit 1
fi

# === 启动 cachesim ===
CACHESIM_BIN="_build_rel/bin/cachesim"
echo "[${TAG}] 启动 cachesim: ${CACHESIM_BIN}"

START_TIME=$(date +%s)
${CACHESIM_BIN} ${TRACE} oracleGeneral LOH ${CACHE_SIZE} \
    --ignore-obj-size 1 \
    --consider-obj-metadata 0 \
    > "${LOG_DIR}/cachesim.log" 2>&1
EXIT_CODE=$?
END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))

echo "[${TAG}] cachesim 完成 (exit=${EXIT_CODE}, ${ELAPSED}s)"

# === 停止 Python ===
echo "[${TAG}] 停止 Python..."
python3 scripts/loh_stop.py 2>/dev/null || true
sleep 3
kill $PY_PID 2>/dev/null || true
wait $PY_PID 2>/dev/null || true

# === 结果分析 ===
echo ""
echo "=========================================="
echo "[${TAG}] 结果分析"
echo "=========================================="

# cachesim 输出
echo "--- cachesim 最终输出 ---"
tail -5 "${LOG_DIR}/cachesim.log"

# MR
echo ""
echo "--- MR 提取 ---"
grep -i "miss ratio" "${LOG_DIR}/cachesim.log" | tail -3
echo ""
echo "Baseline: MR=0.176183, Byte_MR=0.141579"

# n_updates
echo ""
echo "--- n_updates ---"
grep "n_updates" "${LOG_DIR}/ac_sb3.log" | tail -3

echo ""
echo "--- 对比 ---"
echo "0306 baseline: MR=0.176183, n_updates=2,469"
echo "async+threads=1: MR=0.206713, n_updates=14,831"
echo "async+默认threads: MR=0.188123, n_updates=837"
echo "本次(blocked+默认threads): 见上方输出"

echo ""
echo "[${TAG}] 完成！日志: ${LOG_DIR}"
