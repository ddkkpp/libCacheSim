#!/bin/bash
# 测试LOH推理服务与cachesim集成的脚本

# 使用说明函数
usage() {
    echo "Usage: $0 <model_path> [trace_file] [cache_size] [test_duration]"
    echo "  model_path:     Path to trained PPO model (.zip file) - REQUIRED"
    echo "  trace_file:     Path to trace file (optional, default: data/MetaCDN/meta_reag.oracleGeneral.zst)"
    echo "  cache_size:     Cache size as ratio (optional, default: 0.1)"
    echo "  test_duration:  Test duration in seconds (optional, default: unlimited until cachesim finishes)"
    echo
    echo "Examples:"
    echo "  $0 runs/1016_223702/ppo_loh_interrupted.zip"
    echo "  $0 runs/1016_223702/ppo_loh_final.zip /path/to/trace.gz"
    echo "  $0 model.zip /path/to/trace.gz 0.2 120    # 限制运行120秒"
    exit 1
}

# 处理帮助参数
if [[ "$1" == "--help" ]] || [[ "$1" == "-h" ]] || [[ -z "$1" ]]; then
    usage
fi

# 检查模型文件参数
MODEL_PATH="$1"
if [ ! -f "$MODEL_PATH" ]; then
    echo -e "\033[0;31m错误: 模型文件 '$MODEL_PATH' 不存在! 请检查路径。\033[0m"
    usage
fi

echo "=== Testing LOH Inference Service with cachesim ==="
echo "📦 Model: $MODEL_PATH"
echo

# 预清理：停止可能残留的进程
echo "[pre-stop] 停止可能残留的上一次运行..."
if [ -x scripts/stop_loh_rl.sh ]; then
    ./scripts/stop_loh_rl.sh || true
else
    # 兜底：尽量不报错地清理
    pkill -f scripts/loh_inference_only.py || true
    pkill -f "_build_dbg/bin/cachesim.* LOH" || true
    [ -f /dev/shm/loh_ac_9876 ] && rm -f /dev/shm/loh_ac_9876 || true
    # 清理信号量
    rm -f /dev/shm/sem.loh_ac_ready_9876 || true
    rm -f /dev/shm/sem.loh_ac_ack_9876 || true
fi
echo "[pre-stop] 完成。"

# 设置参数默认值
DEFAULT_TRACE_FILE="data/MetaCDN/meta_reag.oracleGeneral.zst"
DEFAULT_CACHE_SIZE="0.1"
DEFAULT_TEST_DURATION="unlimited"  # 默认不限制时间

# 解析参数
TRACE_FILE="${2:-$DEFAULT_TRACE_FILE}"
CACHE_SIZE="${3:-$DEFAULT_CACHE_SIZE}"
TEST_DURATION="${4:-$DEFAULT_TEST_DURATION}"

echo "📋 配置参数:"
echo "   模型文件: $MODEL_PATH"
echo "   跟踪文件: $TRACE_FILE"
echo "   缓存大小: $CACHE_SIZE"
if [ "$TEST_DURATION" = "unlimited" ]; then
    echo "   测试时长: 不限制（直到cachesim完成）"
else
    echo "   测试时长: ${TEST_DURATION}秒"
fi

# 验证数据文件是否存在
if [ ! -f "$TRACE_FILE" ]; then
    echo -e "\033[0;31m错误: Trace文件 '$TRACE_FILE' 不存在! 请检查路径。\033[0m"
    exit 1
fi

# 设置错误处理
set -e

# 生成唯一的时间戳
RUN_TIMESTAMP=$(date +%m%d_%H%M%S)

# 设置颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 清理可能存在的共享内存和信号量
echo "🧹 清理共享内存和信号量..."
rm -f /dev/shm/loh_ac_9876 || true
rm -f /dev/shm/sem.loh_ac_ready_9876 || true
rm -f /dev/shm/sem.loh_ac_ack_9876 || true
echo "✅ 清理完成"

# 检查并构建libCacheSim
echo "🔧 检查libCacheSim构建状态..."
if [ ! -f "_build_dbg/bin/cachesim" ]; then
    echo "📦 构建libCacheSim..."
    bash scripts/debug.sh -c
    if [ $? -ne 0 ]; then
        echo -e "${RED}构建失败，请修复编译错误。${NC}"
        exit 1
    fi
    echo "✅ 构建完成"
else
    echo "✅ 构建已存在，跳过重新构建"
fi

# 设置Python环境
echo "🐍 检查Python环境..."
pip install -q stable-baselines3 gymnasium torch numpy

# 确保权限设置正确
umask 0

# 创建日志文件
INFERENCE_LOG_FILE="inference_${RUN_TIMESTAMP}.log"
CACHESIM_LOG_FILE="cachesim_${RUN_TIMESTAMP}.log"

echo -e "${BLUE}🚀 启动推理服务和cachesim...${NC}"

# 清理函数
cleanup() {
    echo -e "\n${YELLOW}🛑 开始清理...${NC}"

    # 终止Python推理服务
    if [ ! -z "$PYTHON_PID" ] && kill -0 $PYTHON_PID 2>/dev/null; then
        echo "📤 终止Python推理服务 (PID: $PYTHON_PID)"
        kill -TERM $PYTHON_PID 2>/dev/null || true
        sleep 2
        if kill -0 $PYTHON_PID 2>/dev/null; then
            echo "🔥 强制终止Python推理服务"
            kill -KILL $PYTHON_PID 2>/dev/null || true
        fi
    fi

    # 终止cachesim
    if [ ! -z "$CACHESIM_PID" ] && kill -0 $CACHESIM_PID 2>/dev/null; then
        echo "📤 终止cachesim (PID: $CACHESIM_PID)"
        kill -TERM $CACHESIM_PID 2>/dev/null || true
        sleep 2
        if kill -0 $CACHESIM_PID 2>/dev/null; then
            echo "🔥 强制终止cachesim"
            kill -KILL $CACHESIM_PID 2>/dev/null || true
        fi
    fi

    # 清理共享内存和信号量
    echo "🧹 清理共享资源..."
    rm -f /dev/shm/loh_ac_9876 || true
    rm -f /dev/shm/sem.loh_ac_ready_9876 || true
    rm -f /dev/shm/sem.loh_ac_ack_9876 || true

    echo -e "${GREEN}✅ 清理完成${NC}"

    # 显示日志文件信息
    echo -e "\n${BLUE}📋 日志文件:${NC}"
    if [ -f "$INFERENCE_LOG_FILE" ]; then
        echo "   推理服务: $INFERENCE_LOG_FILE"
        echo "   文件大小: $(du -h "$INFERENCE_LOG_FILE" | cut -f1)"
    fi
    if [ -f "$CACHESIM_LOG_FILE" ]; then
        echo "   Cachesim: $CACHESIM_LOG_FILE"
        echo "   文件大小: $(du -h "$CACHESIM_LOG_FILE" | cut -f1)"
    fi
}

# 设置信号处理
trap cleanup EXIT INT TERM

# 设置推理服务环境变量
export LOH_DEBUG_LEVEL=1  # 基本监控模式
export LOH_POLL_SLEEP_US=100  # 快速轮询
export LOH_SEM_TIMEOUT_S=0.5  # 短超时
export PYTHONUNBUFFERED=1

# 启动推理服务
echo "🤖 启动推理服务..."
python3 scripts/loh_inference_only.py "$MODEL_PATH" --debug-level 1 > "$INFERENCE_LOG_FILE" 2>&1 &
PYTHON_PID=$!
echo "✅ 推理服务已启动 (PID: $PYTHON_PID)"

# 等待推理服务初始化
echo "⏳ 等待推理服务初始化..."
sleep 3

# 检查推理服务是否正常运行
if ! kill -0 $PYTHON_PID 2>/dev/null; then
    echo -e "${RED}❌ 推理服务启动失败${NC}"
    echo "推理服务日志:"
    cat "$INFERENCE_LOG_FILE"
    exit 1
fi
echo "✅ 推理服务初始化完成"

# 构建cachesim命令
CACHESIM_CMD="_build_dbg/bin/cachesim $TRACE_FILE oracleGeneral LOH ${CACHE_SIZE}"

# 启动cachesim
echo "🗃️  启动cachesim..."
echo "   命令: $CACHESIM_CMD"
$CACHESIM_CMD > "$CACHESIM_LOG_FILE" 2>&1 &
CACHESIM_PID=$!
echo "✅ Cachesim已启动 (PID: $CACHESIM_PID)"

# 监控进程状态
echo -e "${GREEN}🔄 系统运行中...${NC}"
echo "📊 监控信息将每10秒更新一次"
echo "🛑 按 Ctrl+C 停止测试"
echo

MONITOR_INTERVAL=10
START_TIME=$(date +%s)
LAST_INFERENCE_COUNT=0

# 设置最大监控次数（如果指定了时间限制）
if [ "$TEST_DURATION" != "unlimited" ]; then
    MAX_ITERATIONS=$((TEST_DURATION/MONITOR_INTERVAL+1))
    echo "⏰ 将在 ${TEST_DURATION} 秒后自动停止"
else
    MAX_ITERATIONS=999999  # 一个很大的数字，实际上不会达到
    echo "♾️  无时间限制，将等待cachesim自然完成"
fi

for ((i=1; i<=MAX_ITERATIONS; i++)); do
    # 检查进程是否还在运行
    PYTHON_RUNNING=$(kill -0 $PYTHON_PID 2>/dev/null && echo "✅" || echo "❌")
    CACHESIM_RUNNING=$(kill -0 $CACHESIM_PID 2>/dev/null && echo "✅" || echo "❌")

    # 获取推理统计信息
    INFERENCE_COUNT=$(grep -c "\[推理\]" "$INFERENCE_LOG_FILE" 2>/dev/null || echo "0")
    INFERENCE_RATE=$(echo "scale=1; ($INFERENCE_COUNT - $LAST_INFERENCE_COUNT) / $MONITOR_INTERVAL" | bc -l 2>/dev/null || echo "0.0")
    LAST_INFERENCE_COUNT=$INFERENCE_COUNT

    # 获取cachesim统计信息
    CURRENT_TIME=$(date +%s)
    ELAPSED_TIME=$((CURRENT_TIME - START_TIME))

    # 显示状态
    echo -e "${BLUE}📊 [${ELAPSED_TIME}s]${NC} Python: $PYTHON_RUNNING | Cachesim: $CACHESIM_RUNNING | 推理次数: $INFERENCE_COUNT | 推理速率: ${INFERENCE_RATE}/s"

    # 检查是否有进程崩溃
    if [[ "$PYTHON_RUNNING" == "❌" ]]; then
        echo -e "${RED}❌ 推理服务已停止${NC}"
        break
    fi

    if [[ "$CACHESIM_RUNNING" == "❌" ]]; then
        echo -e "${YELLOW}⚠️  Cachesim已完成${NC}"
        break
    fi

    # 检查是否达到测试时间（仅在指定时间限制时）
    if [ "$TEST_DURATION" != "unlimited" ] && [ $ELAPSED_TIME -ge $TEST_DURATION ]; then
        echo -e "${YELLOW}⏰ 达到测试时间限制 (${TEST_DURATION}s)${NC}"
        break
    fi

    sleep $MONITOR_INTERVAL
done

# 等待额外时间让进程完成
echo "⏳ 等待进程完成..."
sleep 5

echo -e "\n${GREEN}🎉 测试完成！${NC}"

# 显示最终统计
echo -e "\n${BLUE}📈 最终统计:${NC}"

# 创建统计信息写入函数
write_stats() {
    local message="$1"
    echo -e "$message"
    # 同时写入推理日志（去除颜色代码）
    echo "$(echo -e "$message" | sed 's/\x1b\[[0-9;]*m//g')" >> "$INFERENCE_LOG_FILE"
}

# 写入统计开始标记到日志
echo "" >> "$INFERENCE_LOG_FILE"
echo "=== 测试完成统计信息 $(date) ===" >> "$INFERENCE_LOG_FILE"

# 推理服务统计
if [ -f "$INFERENCE_LOG_FILE" ]; then
    TOTAL_INFERENCES=$(grep -c "\[推理\]" "$INFERENCE_LOG_FILE" 2>/dev/null || echo "0")
    write_stats "   推理总次数: $TOTAL_INFERENCES"

    # 检查是否有错误
    ERROR_COUNT=$(grep -c "❌\|ERROR\|失败" "$INFERENCE_LOG_FILE" 2>/dev/null || echo "0")
    ERROR_COUNT=$(echo "$ERROR_COUNT" | tr -d '\n\r ')  # 清理换行符和空格
    if [ "$ERROR_COUNT" -gt 0 ] 2>/dev/null; then
        write_stats "   ${RED}推理错误数: $ERROR_COUNT${NC}"
    else
        write_stats "   ${GREEN}推理错误数: 0${NC}"
    fi
fi

# Cachesim统计
if [ -f "$CACHESIM_LOG_FILE" ]; then
    # 提取最终统计行的miss ratio信息
    FINAL_STATS_LINE=$(grep "cache size.*req.*miss ratio" "$CACHESIM_LOG_FILE" | tail -1)
    if [ ! -z "$FINAL_STATS_LINE" ]; then
        # 提取miss ratio (格式: miss ratio 0.3440, byte miss ratio 0.1784)
        MISS_RATIO=$(echo "$FINAL_STATS_LINE" | grep -o "miss ratio [0-9]\+\.[0-9]\+" | head -1 | grep -o "[0-9]\+\.[0-9]\+")
        BYTE_MISS_RATIO=$(echo "$FINAL_STATS_LINE" | grep -o "byte miss ratio [0-9]\+\.[0-9]\+" | head -1 | grep -o "[0-9]\+\.[0-9]\+")

        if [ ! -z "$MISS_RATIO" ]; then
            HIT_RATIO=$(echo "scale=4; 1 - $MISS_RATIO" | bc -l 2>/dev/null || echo "unknown")
            write_stats "   缓存命中率: ${HIT_RATIO} (miss ratio: ${MISS_RATIO})"
        fi

        if [ ! -z "$BYTE_MISS_RATIO" ]; then
            BYTE_HIT_RATIO=$(echo "scale=4; 1 - $BYTE_MISS_RATIO" | bc -l 2>/dev/null || echo "unknown")
            write_stats "   字节命中率: ${BYTE_HIT_RATIO} (byte miss ratio: ${BYTE_MISS_RATIO})"
        fi

        # 提取请求总数 (格式: 45623306 req)
        TOTAL_REQUESTS=$(echo "$FINAL_STATS_LINE" | grep -o "[0-9]\+ req" | head -1 | grep -o "[0-9]\+")
        if [ ! -z "$TOTAL_REQUESTS" ]; then
            write_stats "   处理请求数: $TOTAL_REQUESTS"
        fi
    fi
fi

# 计算推理效率
if [ "$TOTAL_INFERENCES" -gt 0 ] && [ -n "$TOTAL_REQUESTS" ] && [ "$TOTAL_REQUESTS" -gt 0 ]; then
    INFERENCE_RATIO=$(echo "scale=6; $TOTAL_INFERENCES * 100 / $TOTAL_REQUESTS" | bc -l 2>/dev/null || echo "unknown")
    # 计算每万次请求的推理次数，更直观
    INFERENCE_PER_10K=$(echo "scale=1; $TOTAL_INFERENCES * 10000 / $TOTAL_REQUESTS" | bc -l 2>/dev/null || echo "unknown")
    # 计算平均多少次请求需要1次推理
    REQUESTS_PER_INFERENCE=$(echo "scale=0; $TOTAL_REQUESTS / $TOTAL_INFERENCES" | bc -l 2>/dev/null || echo "unknown")
    write_stats "   推理覆盖率: ${INFERENCE_RATIO}% (平均每${REQUESTS_PER_INFERENCE}个请求推理1次)"

    # 显示状态更新vs推理比例
    if grep -q "update_state_vec.*count=" "$CACHESIM_LOG_FILE"; then
        STATE_UPDATES=$(grep "update_state_vec.*count=" "$CACHESIM_LOG_FILE" | tail -1 | grep -o "count=[[:space:]]*[0-9]\+" | head -1 | grep -o "[0-9]\+")
        if [ -n "$STATE_UPDATES" ] && [ "$STATE_UPDATES" -gt 0 ]; then
            UPDATE_RATIO=$(echo "scale=1; $STATE_UPDATES / $TOTAL_INFERENCES" | bc -l 2>/dev/null || echo "unknown")
            write_stats "   状态更新数: $STATE_UPDATES (更新/推理比例: ${UPDATE_RATIO}:1)"
        fi
    fi
fi

# 写入统计结束标记到日志
echo "=== 统计信息结束 ===" >> "$INFERENCE_LOG_FILE"

echo
echo -e "${GREEN}✅ 测试成功完成！${NC}"
echo -e "${BLUE}📄 查看详细日志:${NC}"
echo "   tail -f $INFERENCE_LOG_FILE"
echo "   tail -f $CACHESIM_LOG_FILE"
