#!/bin/bash
# 测试两分量惩罚机制

set -e

echo "========================================="
echo "两分量惩罚机制测试"
echo "========================================="

# 清理旧的共享内存和进程
echo "1. 清理环境..."
pkill -9 -f "loh_actor_critic_sb3.py" 2>/dev/null || true
pkill -9 -f "cachesim.*LOH" 2>/dev/null || true
rm -f /dev/shm/loh_ac_9876 2>/dev/null || true
rm -f /tmp/loh_test_*.log 2>/dev/null || true

# 创建测试trace（较小，快速测试）
echo "2. 创建测试trace..."
cat > /tmp/test_trace_penalty.csv << 'EOF'
time,obj_id,size
1,1,4096
2,2,4096
3,3,4096
4,4,4096
5,5,4096
6,1,4096
7,2,4096
8,6,4096
9,7,4096
10,8,4096
11,1,4096
12,9,4096
13,10,4096
14,11,4096
15,1,4096
EOF

# 启动Python RL进程
echo "3. 启动Python RL进程..."
LOH_DEBUG=1 python3 scripts/loh_actor_critic_sb3.py \
    --miss-ratio-weight 1.0 \
    > /tmp/loh_test_python.log 2>&1 &
PYTHON_PID=$!

echo "Python PID: $PYTHON_PID"
echo "等待Python创建共享内存..."

# 等待共享内存文件创建
for i in {1..60}; do
    if [ -f /dev/shm/loh_ac_9876 ]; then
        echo "✅ 共享内存已创建"
        break
    fi
    sleep 1
    if [ $i -eq 60 ]; then
        echo "❌ 超时：共享内存未创建"
        kill -9 $PYTHON_PID 2>/dev/null || true
        exit 1
    fi
done

# 启动C端模拟器
echo "4. 启动C端cachesim..."
_build_dbg/bin/cachesim /tmp/test_trace_penalty.csv csv LOH 8KB \
    > /tmp/loh_test_c.log 2>&1 &
C_PID=$!

echo "C端 PID: $C_PID"

# 等待一段时间让它们交互
echo "5. 等待交互完成（10秒）..."
sleep 10

# 停止进程
echo "6. 停止进程..."
kill -TERM $C_PID 2>/dev/null || true
kill -TERM $PYTHON_PID 2>/dev/null || true
sleep 2
kill -9 $C_PID 2>/dev/null || true
kill -9 $PYTHON_PID 2>/dev/null || true

# 分析日志
echo ""
echo "========================================="
echo "日志分析"
echo "========================================="

echo ""
echo "=== C端关键信息 ==="
echo "结构大小:"
grep "sizeof" /tmp/loh_test_c.log | head -2

echo ""
echo "驱逐统计:"
grep -E "(Evicted|epoch_evicted)" /tmp/loh_test_c.log | head -5

echo ""
echo "Ghost miss检测:"
grep "Ghost miss" /tmp/loh_test_c.log | head -5

echo ""
echo "惩罚入队:"
grep "Enqueued penalty" /tmp/loh_test_c.log | head -5

echo ""
echo "同步统计:"
grep "Sending eviction stats" /tmp/loh_test_c.log | head -3

echo ""
echo "=== Python端关键信息 ==="
echo "ReplayBuffer初始化:"
grep "Initialized with:" /tmp/loh_test_python.log -A4

echo ""
echo "惩罚接收:"
grep "Received.*penalty" /tmp/loh_test_python.log | head -5

echo ""
echo "惩罚累积:"
grep "Accumulated penalty" /tmp/loh_test_python.log | head -5

echo ""
echo "最终奖励计算:"
grep "Finalized reward" /tmp/loh_test_python.log | head -5

echo ""
echo "初始奖励:"
grep "Initial reward:" /tmp/loh_test_python.log | head -5

echo ""
echo "========================================="
echo "完整日志位置:"
echo "  C端:   /tmp/loh_test_c.log"
echo "  Python: /tmp/loh_test_python.log"
echo "========================================="
