#!/bin/bash
# 测试新的reward改进（纯penalty-based + 连续运行）

set -e

echo "🧪 Testing Pure Penalty-Based Reward + Continuous Running..."
echo "=============================================================="
echo ""

# 清理
echo "🧹 Cleaning up..."
rm -f /dev/shm/loh_ac_9876
pkill -9 -f "loh_actor_critic_sb3.py" || true
pkill -9 -f "cachesim.*loh" || true
sleep 1

# 设置环境
export LOH_STATE_DIM=26
export RUN_TIMESTAMP=$(date +%m%d_%H%M%S)

echo "📋 New Configuration:"
echo "  ✅ Reward: (baseline - current) / baseline (pure penalty-based)"
echo "  ✅ Continuous Running: truncated=False (no reset)"
echo "  ✅ TensorBoard: reward stats + penalty baseline"
echo "  - learning_starts: 1000"
echo "  - exclude_recent_steps: 100"
echo ""

# 启动Python
echo "🐍 Starting Python RL agent..."
python3 scripts/loh_actor_critic_sb3.py \
    --learning-starts 1000 \
    --exclude-recent-steps 100 \
    > ac_sb3_${RUN_TIMESTAMP}.log 2>&1 &

PYTHON_PID=$!
echo "  Python PID: $PYTHON_PID"

# 等待共享内存
echo "⏳ Waiting for shared memory..."
timeout=60
elapsed=0
while [ ! -f /dev/shm/loh_ac_9876 ]; do
    if [ $((elapsed % 10)) -eq 0 ]; then
        echo "  ... waiting (${elapsed}s)"
    fi
    sleep 1
    elapsed=$((elapsed + 1))
    if [ $elapsed -ge $timeout ]; then
        echo "❌ Timeout"
        kill $PYTHON_PID 2>/dev/null || true
        exit 1
    fi
done
echo "✅ Shared memory created"

# 启动cachesim
echo "🚀 Starting cachesim..."
_build_dbg/bin/cachesim \
    data/trace.txt \
    loh \
    --trace-format=csv \
    --trace-format-fields=time,id,size \
    --num-req=100000 \
    --cache-size=1GB \
    > cachesim_${RUN_TIMESTAMP}.log 2>&1 &

CACHESIM_PID=$!
echo "  Cachesim PID: $CACHESIM_PID"

# 运行60秒
echo "⏳ Running for 60 seconds..."
sleep 60

# 停止
echo "🛑 Stopping..."
kill $CACHESIM_PID 2>/dev/null || true
python3 scripts/loh_stop.py 2>/dev/null || true
sleep 2
kill $PYTHON_PID 2>/dev/null || true

# 分析
echo ""
echo "📊 Analysis"
echo "==========="

echo ""
echo "🎁 Reward Distribution:"
grep "reward (before clip):" ac_sb3_${RUN_TIMESTAMP}.log | tail -50 | awk -F': ' '{print $NF}' | awk '
BEGIN {min=999; max=-999; sum=0; count=0}
{
    val=$1
    sum+=val
    count++
    if(val<min) min=val
    if(val>max) max=val
    values[count]=val
}
END {
    if(count>0) {
        mean=sum/count
        sum_sq=0
        for(i=1;i<=count;i++) {
            diff=values[i]-mean
            sum_sq+=diff*diff
        }
        std=sqrt(sum_sq/count)
        printf "  Count: %d\n", count
        printf "  Mean: %.6f\n", mean
        printf "  Std: %.6f\n", std
        printf "  Min: %.6f\n", min
        printf "  Max: %.6f\n", max
        printf "  Range: %.6f\n", max-min
        if(std>0.1) print "  ✅ Good diversity (std>0.1)"
        else print "  ⚠️  Low diversity"
        if(max-min>0.3) print "  ✅ Wide range (>0.3)"
        else print "  ⚠️  Narrow range"
    }
}'

echo ""
echo "📐 Penalty Baseline:"
grep "penalty_baseline:" ac_sb3_${RUN_TIMESTAMP}.log | tail -20 | awk -F': ' '{print $NF}' | awk '
BEGIN {sum=0; count=0}
{sum+=$1; count++; last=$1}
END {
    if(count>0) {
        printf "  Latest: %.6f\n", last
        printf "  Average: %.6f\n", sum/count
    }
}'

echo ""
echo "🔢 Penalty Count:"
grep "penalty_sum:" ac_sb3_${RUN_TIMESTAMP}.log | tail -50 | awk -F': ' '{print $NF}' | awk '
BEGIN {zero=0; nonzero=0; sum=0}
{
    if($1 < 0.001) zero++
    else {nonzero++; sum+=$1}
}
END {
    total=zero+nonzero
    if(total>0) {
        printf "  Total samples: %d\n", total
        printf "  With penalty: %d (%.1f%%)\n", nonzero, nonzero*100.0/total
        printf "  Without penalty: %d (%.1f%%)\n", zero, zero*100.0/total
        if(nonzero>0) printf "  Avg penalty (when >0): %.6f\n", sum/nonzero
    }
}'

echo ""
echo "📝 Log files:"
echo "  - Python: ac_sb3_${RUN_TIMESTAMP}.log"
echo "  - Cachesim: cachesim_${RUN_TIMESTAMP}.log"

echo ""
echo "💡 To view TensorBoard:"
echo "  tensorboard --logdir ./runs --port 6006"

echo ""
echo "✅ Test completed"
