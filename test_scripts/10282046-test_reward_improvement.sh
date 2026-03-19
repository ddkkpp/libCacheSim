#!/bin/bash
# 测试reward改进效果

set -e

echo "🧪 Testing Reward Improvement..."
echo "================================"
echo ""

# 设置环境变量
export LOH_STATE_DIM=26
export RUN_TIMESTAMP=$(date +%m%d_%H%M%S)
LOG_DIR="logs"
mkdir -p "${LOG_DIR}"

# 配置参数
LEARNING_STARTS=1000       # 从100增加到1000
EXCLUDE_RECENT_STEPS=100   # 从20增加到100

echo "📋 Configuration:"
echo "  - learning_starts: $LEARNING_STARTS (was 100)"
echo "  - exclude_recent_steps: $EXCLUDE_RECENT_STEPS (was 20)"
echo "  - buffer_size: 10000"
echo "  - batch_size: 256"
echo ""

# 清理旧的共享内存
echo "🧹 Cleaning up old shared memory..."
rm -f /dev/shm/loh_ac_9876
pkill -9 -f "loh_actor_critic_sb3.py" || true
pkill -9 -f "cachesim.*loh" || true
sleep 1

# 启动Python RL进程
echo "🐍 Starting Python RL agent..."
python3 scripts/loh_actor_critic_sb3.py \
    --learning-starts $LEARNING_STARTS \
    --exclude-recent-steps $EXCLUDE_RECENT_STEPS \
    > "${LOG_DIR}/ac_sb3_${RUN_TIMESTAMP}.log" 2>&1 &

PYTHON_PID=$!
echo "  Python PID: $PYTHON_PID"

# 等待共享内存创建
echo "⏳ Waiting for shared memory..."
timeout=60
elapsed=0
while [ ! -f /dev/shm/loh_ac_9876 ]; do
    if [ $elapsed -ge $timeout ]; then
        echo "❌ Timeout waiting for shared memory"
        kill $PYTHON_PID 2>/dev/null || true
        exit 1
    fi
    sleep 1
    elapsed=$((elapsed + 1))
    if [ $((elapsed % 10)) -eq 0 ]; then
        echo "  ... still waiting (${elapsed}s)"
    fi
done
echo "✅ Shared memory created"

# 启动cachesim（运行较短时间，观察reward分布）
echo "🚀 Starting cachesim (short run for testing)..."
_build_dbg/bin/cachesim \
    data/trace.txt \
    loh \
    --trace-format=csv \
    --trace-format-fields=time,id,size \
    --num-req=50000 \
    --cache-size=1GB \
    > "${LOG_DIR}/cachesim_${RUN_TIMESTAMP}.log" 2>&1 &

CACHESIM_PID=$!
echo "  Cachesim PID: $CACHESIM_PID"

# 等待运行一段时间
echo "⏳ Running simulation for 30 seconds..."
sleep 30

# 停止进程
echo "🛑 Stopping processes..."
kill $CACHESIM_PID 2>/dev/null || true
python3 scripts/loh_stop.py 2>/dev/null || true
sleep 2
kill $PYTHON_PID 2>/dev/null || true

echo ""
echo "📊 Analyzing results..."
echo "======================="

# 提取reward统计
echo ""
echo "🎁 Reward Distribution:"
grep "final_reward" "${LOG_DIR}/ac_sb3_${RUN_TIMESTAMP}.log" | tail -20 | grep -oP "final_reward.*?:\s*\K[-+]?[0-9]*\.?[0-9]+" | awk '
BEGIN {
    min = 999
    max = -999
    sum = 0
    count = 0
}
{
    val = $1
    sum += val
    count++
    if (val < min) min = val
    if (val > max) max = val
    values[count] = val
}
END {
    if (count > 0) {
        mean = sum / count
        # 计算标准差
        sum_sq = 0
        for (i = 1; i <= count; i++) {
            diff = values[i] - mean
            sum_sq += diff * diff
        }
        std = sqrt(sum_sq / count)

        printf "  📈 Count: %d\n", count
        printf "  📊 Mean: %.6f\n", mean
        printf "  📊 Std: %.6f\n", std
        printf "  📊 Min: %.6f\n", min
        printf "  📊 Max: %.6f\n", max
        printf "  📊 Range: %.6f\n", max - min

        # 检查改进
        if (std > 0.05) {
            print "  ✅ Good diversity (std > 0.05)"
        } else {
            print "  ⚠️  Low diversity (std < 0.05)"
        }

        if (max - min > 0.2) {
            print "  ✅ Good range (> 0.2)"
        } else {
            print "  ⚠️  Narrow range (< 0.2)"
        }
    }
}'

echo ""
echo "🔍 Penalty Statistics:"
grep "penalty_data:" "${LOG_DIR}/ac_sb3_${RUN_TIMESTAMP}.log" | tail -20 | grep -oP "penalty_data:\s*\K[0-9]+" | awk '
BEGIN {
    sum = 0
    count = 0
    zero_count = 0
}
{
    val = $1
    sum += val
    count++
    if (val == 0) zero_count++
}
END {
    if (count > 0) {
        printf "  📊 Total samples: %d\n", count
        printf "  📊 Samples with penalties: %d (%.1f%%)\n", count - zero_count, (count - zero_count) * 100.0 / count
        printf "  📊 Samples without penalties: %d (%.1f%%)\n", zero_count, zero_count * 100.0 / count
        printf "  📊 Avg penalties per sample: %.2f\n", sum / count
    }
}'

echo ""
echo "📝 Log files:"
echo "  - Python: ${LOG_DIR}/ac_sb3_${RUN_TIMESTAMP}.log"
echo "  - Cachesim: ${LOG_DIR}/cachesim_${RUN_TIMESTAMP}.log"

echo ""
echo "✅ Test completed"
