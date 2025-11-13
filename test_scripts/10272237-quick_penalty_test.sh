#!/bin/bash
# 简化版端到端测试：同时运行 C 和 Python，检查 penalty 流程

set -e

echo "========== Quick Penalty Flow Test =========="

# 清理
pkill -f "loh_actor_critic_sb3.py" 2>/dev/null || true
pkill -f "cachesim" 2>/dev/null || true
rm -f /dev/shm/loh_ac_9876 2>/dev/null || true
sleep 1

# 启动 Python（后台）
echo "[1] Starting Python RL..."
export LOH_DEBUG_LEVEL=1
export LOH_STATE_DIM=26
python3 scripts/loh_actor_critic_sb3.py > /tmp/quick_python.log 2>&1 &
PYTHON_PID=$!

# 等待共享内存
echo "[2] Waiting for shared memory..."
for i in {1..20}; do
    [ -f /dev/shm/loh_ac_9876 ] && break
    sleep 0.5
done

if [ ! -f /dev/shm/loh_ac_9876 ]; then
    echo "❌ Shared memory not created"
    kill $PYTHON_PID 2>/dev/null || true
    exit 1
fi
echo "✅ Shared memory ready"

# 运行 C 端（限时 20 秒）
echo "[3] Running cachesim..."
timeout 20 _build_dbg/bin/cachesim \
    data/test/twitter/twitter_cluster52_10m.csv.zst \
    csvzst LOH 8mb \
    > /tmp/quick_c.log 2>&1 || true

# 停止 Python
echo "[4] Stopping Python..."
python3 scripts/loh_stop.py 2>/dev/null || kill $PYTHON_PID 2>/dev/null || true
sleep 1

# 分析结果
echo
echo "========== Results =========="
echo "C-side penalties sent:"
grep -c "\[C\]\[BASIC\]   penalty\[" /tmp/quick_c.log 2>/dev/null || echo "0"

echo "Python-side penalties read:"
grep -c "\[Python\]\[BASIC\]   penalty\[" /tmp/quick_python.log 2>/dev/null || echo "0"

echo
echo "Sample C-side output:"
grep "\[C\]\[BASIC\] Wrote penalty" /tmp/quick_c.log 2>/dev/null | head -3 || echo "(none)"

echo
echo "Sample Python-side output:"
grep "\[Python\]\[BASIC\] Reading.*penalties" /tmp/quick_python.log 2>/dev/null | head -3 || echo "(none)"

echo
echo "Full logs: /tmp/quick_c.log, /tmp/quick_python.log"
