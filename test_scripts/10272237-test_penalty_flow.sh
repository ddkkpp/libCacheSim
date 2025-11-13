#!/bin/bash
# 测试 penalty 数据从 C 端收集 → 传递 → Python 读取 → 修改 buffer → 计算 reward 的完整流程

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=========================================="
echo "Penalty Flow End-to-End Test"
echo "=========================================="
echo

# 1. 清理旧数据
echo "[1/6] Cleaning up old processes and shared memory..."
pkill -f "loh_actor_critic_sb3.py" 2>/dev/null || true
pkill -f "cachesim" 2>/dev/null || true
rm -f /dev/shm/loh_ac_9876 2>/dev/null || true
rm -f /tmp/loh_ac_ready_9876 /tmp/loh_ac_ack_9876 2>/dev/null || true
sleep 1

# 2. 检查编译
echo "[2/6] Checking build..."
if [ ! -f "$REPO_ROOT/_build_dbg/bin/cachesim" ]; then
    echo "❌ cachesim not found, building..."
    cd "$REPO_ROOT"
    bash scripts/debug.sh -c
fi

# 3. 准备测试 trace（使用 complex_test.csv，更多请求）
echo "[3/6] Preparing test trace..."
TRACE_FILE="$REPO_ROOT/complex_test.csv"
if [ ! -f "$TRACE_FILE" ]; then
    echo "❌ Test trace not found: $TRACE_FILE"
    exit 1
fi
CACHE_SIZE="64kb"  # 小 cache，容易触发驱逐

# 4. 启动 Python RL 进程（后台）
echo "[4/6] Starting Python RL process..."
cd "$REPO_ROOT"
export LOH_DEBUG_LEVEL=1  # BASIC 级别
export LOH_STATE_DIM=26
nohup python3 scripts/loh_actor_critic_sb3.py > /tmp/test_penalty_python.log 2>&1 &
PYTHON_PID=$!
echo "Python PID: $PYTHON_PID"

# 等待共享内存文件创建
echo "Waiting for shared memory file..."
for i in {1..30}; do
    if [ -f /dev/shm/loh_ac_9876 ]; then
        echo "✅ Shared memory file created"
        break
    fi
    sleep 1
    echo -n "."
done
echo

if [ ! -f /dev/shm/loh_ac_9876 ]; then
    echo "❌ Shared memory file not created after 30s"
    kill $PYTHON_PID 2>/dev/null || true
    exit 1
fi

# 5. 运行 C 端模拟器（限制运行时间）
echo "[5/6] Running C-side cachesim (30 seconds)..."
timeout 30 "$REPO_ROOT/_build_dbg/bin/cachesim" \
    "$TRACE_FILE" csv LOH "$CACHE_SIZE" \
    > /tmp/test_penalty_cachesim.log 2>&1 || true

# 6. 停止 Python 并分析日志
echo "[6/6] Stopping Python and analyzing logs..."
python3 "$SCRIPT_DIR/loh_stop.py" 2>/dev/null || kill $PYTHON_PID 2>/dev/null || true
sleep 2

echo
echo "=========================================="
echo "Log Analysis"
echo "=========================================="
echo

# C 端：检查 penalty 收集和发送
echo "--- C-side: Penalty Collection & Sending ---"
echo "Penalty enqueued:"
grep -E "\[LOH\] Enqueued penalty|Expanded penalty queue" /tmp/test_penalty_cachesim.log | head -5 || echo "(none)"
echo
echo "Penalty sent to Python:"
grep -E "\[C\]\[BASIC\] Wrote penalty data" /tmp/test_penalty_cachesim.log | head -3 || echo "(none)"
echo
echo "Sample penalty entries:"
grep -E "\[C\]\[BASIC\]   penalty\[" /tmp/test_penalty_cachesim.log | head -5 || echo "(none)"
echo

# Python 端：检查 penalty 读取
echo "--- Python-side: Penalty Reading ---"
echo "Penalty read from shared memory:"
grep -E "\[Python\]\[BASIC\] Reading.*penalties from offset" /tmp/test_penalty_python.log | head -3 || echo "(none)"
echo
echo "Sample penalty entries:"
grep -E "\[Python\]\[BASIC\]   penalty\[" /tmp/test_penalty_python.log | head -5 || echo "(none)"
echo

# Python 端：检查 buffer 修改
echo "--- Python-side: Buffer Modification ---"
echo "Penalty applied to buffer:"
grep -E "Accumulated penalty data for version" /tmp/test_penalty_python.log | head -5 || echo "(none)"
echo

# Python 端：检查 reward 计算
echo "--- Python-side: Reward Calculation ---"
echo "Initial rewards:"
grep -E "Initial reward:" /tmp/test_penalty_python.log | head -3 || echo "(none)"
echo
echo "Retrospective reward corrections:"
grep -E "retrospective_correct_reward.*corrected" /tmp/test_penalty_python.log | head -5 || echo "(none)"
echo

# 统计
echo "=========================================="
echo "Statistics"
echo "=========================================="
PENALTIES_SENT=$(grep -c "\[C\]\[BASIC\]   penalty\[" /tmp/test_penalty_cachesim.log 2>/dev/null || echo 0)
PENALTIES_READ=$(grep -c "\[Python\]\[BASIC\]   penalty\[" /tmp/test_penalty_python.log 2>/dev/null || echo 0)
PENALTIES_APPLIED=$(grep -c "Accumulated penalty data for version" /tmp/test_penalty_python.log 2>/dev/null || echo 0)

echo "Penalties sent by C:      $PENALTIES_SENT"
echo "Penalties read by Python: $PENALTIES_READ"
echo "Penalties applied to buffer: $PENALTIES_APPLIED"
echo

if [ "$PENALTIES_SENT" -gt 0 ] && [ "$PENALTIES_READ" -gt 0 ]; then
    echo "✅ Data flow check: PASSED"
    echo "   - C端收集并发送了 $PENALTIES_SENT 个 penalty"
    echo "   - Python 端读取了 $PENALTIES_READ 个 penalty"
    if [ "$PENALTIES_APPLIED" -gt 0 ]; then
        echo "   - Python 端应用了 $PENALTIES_APPLIED 个 penalty 到 buffer"
    fi
else
    echo "❌ Data flow check: FAILED"
    if [ "$PENALTIES_SENT" -eq 0 ]; then
        echo "   - C端没有发送 penalty 数据"
    fi
    if [ "$PENALTIES_READ" -eq 0 ]; then
        echo "   - Python 端没有读取 penalty 数据"
    fi
fi

echo
echo "Full logs:"
echo "  C-side:   /tmp/test_penalty_cachesim.log"
echo "  Python:   /tmp/test_penalty_python.log"
echo
echo "=========================================="
