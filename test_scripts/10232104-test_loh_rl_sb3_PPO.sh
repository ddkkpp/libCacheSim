#!/bin/bash
# 测试LOH算法与stable-baselines3 RL集成的脚本

# 使用说明函数
usage() {
    echo "Usage: $0 [trace_file] [state_dim] [cache_size] [miss_ratio_weight]"
    echo "  trace_file:         Path to trace file (optional, default: data/MetaCDN/meta_reag.oracleGeneral.zst)"
    echo "  state_dim:          State dimension (optional, default: 26)"
    echo "  cache_size:         Cache size as ratio (optional, default: 0.1)"
    echo "  miss_ratio_weight:  Weight for object miss ratio in reward (optional, default: 1.0, byte_miss_ratio_weight = 1.0 - miss_ratio_weight)"
    echo
    echo "Examples:"
    echo "  $0"
    echo "  $0 /path/to/trace.gz"
    echo "  $0 /path/to/trace.gz 26"
    echo "  $0 /path/to/trace.gz 26 0.2"
    echo "  $0 /path/to/trace.gz 26 0.2 0.8    # 80% object miss ratio, 20% byte miss ratio"
    exit 1
}

# 处理帮助参数
if [[ "$1" == "--help" ]] || [[ "$1" == "-h" ]]; then
    usage
fi

echo "=== Testing LOH with stable-baselines3 Reinforcement Learning ==="
echo

# 预清理：为了避免上一次残留的 Python/cachesim/共享内存影响本次运行，先优雅停止两端。
# 注意：如果你计划并行运行多个实例，请勿直接使用此段逻辑（会杀掉所有匹配进程）；
#      建议为每个实例使用独立的 SHM KEY、日志文件与进程标签，并修改 stop 脚本只匹配对应实例。
echo "[pre-stop] 停止可能残留的上一次运行..."
if [ -x scripts/stop_loh_rl.sh ]; then
    ./scripts/stop_loh_rl.sh || true
else
    # 兜底：尽量不报错地清理
    pkill -f scripts/loh_actor_critic_sb3.py || true
    pkill -f "_build_dbg/bin/cachesim.* LOH" || true
    [ -f /dev/shm/loh_ac_9876 ] && rm -f /dev/shm/loh_ac_9876 || true
fi
echo "[pre-stop] 完成。"

# --- 【新增】状态向量维度配置 ---
# 检查是否提供了状态向量维度参数（第二个参数）
if [ -n "$2" ]; then
    STATE_DIM="$2"
    if [ "$STATE_DIM" != "26" ] && [ "$STATE_DIM" != "38" ]; then
        echo -e "\033[0;31m错误: 状态向量维度必须是26或38，您提供的是: $STATE_DIM\033[0m"
        echo "用法: $0 [trace_file] [state_dim] [cache_size]"
        echo "示例: $0 data/meta.zst 26 0.1      # 使用26维状态向量，缓存大小0.1"
        echo "示例: $0 data/meta.zst 38 0.05     # 使用38维状态向量，缓存大小0.05"
        exit 1
    fi
    export LOH_STATE_DIM="$STATE_DIM"
    echo "使用您指定的状态向量维度: ${STATE_DIM}维"
else
    export LOH_STATE_DIM="26"
    echo "未指定状态向量维度，使用默认: 26维（不包含缓存特征）"
fi

# --- 【新增】缓存大小配置 ---
# 检查是否提供了缓存大小参数（第三个参数）
if [ -n "$3" ]; then
    CACHE_SIZE="$3"
    # 验证cache_size是有效数值
    if ! [[ "$CACHE_SIZE" =~ ^[0-9]*\.?[0-9]+$ ]] || (( $(echo "$CACHE_SIZE <= 0" | bc -l) )) || (( $(echo "$CACHE_SIZE > 1" | bc -l) )); then
        echo "错误: 缓存大小必须是0到1之间的数值，您输入的是: $CACHE_SIZE"
        usage
    fi
    echo "使用您指定的缓存大小: $CACHE_SIZE"
else
    CACHE_SIZE="0.1"
    echo "未指定缓存大小，使用默认: $CACHE_SIZE"
fi

# 检查是否提供了miss ratio权重参数（第四个参数）
if [ -n "$4" ]; then
    MISS_RATIO_WEIGHT="$4"
    # 验证miss_ratio_weight是有效数值
    if ! [[ "$MISS_RATIO_WEIGHT" =~ ^[0-9]*\.?[0-9]+$ ]] || (( $(echo "$MISS_RATIO_WEIGHT < 0" | bc -l) )) || (( $(echo "$MISS_RATIO_WEIGHT > 1" | bc -l) )); then
        echo "错误: miss ratio权重必须是0到1之间的数值，您输入的是: $MISS_RATIO_WEIGHT"
        usage
    fi
    BYTE_MISS_RATIO_WEIGHT=$(echo "1.0 - $MISS_RATIO_WEIGHT" | bc -l)
    echo "使用您指定的权重: miss_ratio_weight=$MISS_RATIO_WEIGHT, byte_miss_ratio_weight=$BYTE_MISS_RATIO_WEIGHT"
else
    MISS_RATIO_WEIGHT="1.0"
    BYTE_MISS_RATIO_WEIGHT="0.0"
    echo "未指定权重，使用默认: miss_ratio_weight=$MISS_RATIO_WEIGHT, byte_miss_ratio_weight=$BYTE_MISS_RATIO_WEIGHT"
fi

# --- 【核心功能】: 处理trace文件参数 ---
# 设置默认的trace文件路径
DEFAULT_TRACE_FILE="data/MetaCDN/meta_reag.oracleGeneral.zst"


# 检查是否提供了trace文件和请求数参数
if [ -n "$1" ]; then
    TRACE_FILE="$1"
    echo "使用您指定的trace文件: $TRACE_FILE"
else
    TRACE_FILE="$DEFAULT_TRACE_FILE"
    echo "未指定trace文件，使用默认路径: $TRACE_FILE"
fi

# 验证数据文件是否存在
if [ ! -f "$TRACE_FILE" ]; then
    echo -e "\033[0;31m错误: Trace文件 '$TRACE_FILE' 不存在! 请检查路径。\033[0m"
    exit 1
fi
# --- 功能结束 ---

# 设置错误处理和调试
set -e  # 遇到错误时停止执行

# 生成唯一的时间戳
RUN_TIMESTAMP=$(date +%m%d_%H%M%S) # 例如: 0730_173500

# 清理可能存在的共享内存文件
echo "Cleaning up any existing shared memory files..."
if [ -f /dev/shm/loh_ac_9876 ]; then
    rm -f /dev/shm/loh_ac_9876
    echo "Removed existing shared memory file"
fi

# 设置一些颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}开始测试LOH算法与stable-baselines3强化学习的集成...${NC}"

# --- 【新增】根据状态向量维度配置C代码 ---
echo "Configuring LOH.c for ${LOH_STATE_DIM}-dimensional state vector..."
LOH_FILE="libCacheSim/cache/eviction/LOH.c"

# 检查当前配置
CURRENT_CONFIG=$(grep "#define LOH_INCLUDE_CACHE_FEATURES" "$LOH_FILE" | grep -o "[01]$" || echo "unknown")
NEED_REBUILD=false

if [ "$LOH_STATE_DIM" = "26" ]; then
    # 需要26维状态向量（不包含缓存特征）
    if [ "$CURRENT_CONFIG" != "0" ]; then
        echo "Switching LOH.c to 26-dimensional mode (disabling cache features)..."
        sed -i 's/#define LOH_INCLUDE_CACHE_FEATURES 1/#define LOH_INCLUDE_CACHE_FEATURES 0/' "$LOH_FILE"
        sed -i 's/#define LOH_INCLUDE_CACHE_FEATURES [^01]/#define LOH_INCLUDE_CACHE_FEATURES 0/' "$LOH_FILE"
        NEED_REBUILD=true
        echo "✅ Configured LOH.c for 26-dimensional state vector"
    else
        echo "✅ LOH.c already configured for 26-dimensional state vector"
    fi
elif [ "$LOH_STATE_DIM" = "38" ]; then
    # 需要38维状态向量（包含缓存特征）
    if [ "$CURRENT_CONFIG" != "1" ]; then
        echo "Switching LOH.c to 38-dimensional mode (enabling cache features)..."
        sed -i 's/#define LOH_INCLUDE_CACHE_FEATURES 0/#define LOH_INCLUDE_CACHE_FEATURES 1/' "$LOH_FILE"
        sed -i 's/#define LOH_INCLUDE_CACHE_FEATURES [^01]/#define LOH_INCLUDE_CACHE_FEATURES 1/' "$LOH_FILE"
        NEED_REBUILD=true
        echo "✅ Configured LOH.c for 38-dimensional state vector"
    else
        echo "✅ LOH.c already configured for 38-dimensional state vector"
    fi
fi

# 只在需要时重新编译
if [ "$NEED_REBUILD" = true ]; then
    echo "📦 Configuration changed, rebuilding libCacheSim..."
    bash scripts/debug.sh -c
    if [ $? -ne 0 ]; then
        echo -e "${RED}Build failed. Please fix any compile errors.${NC}"
        exit 1
    fi
    echo "✅ Rebuild completed successfully"
else
    echo "⚡ No rebuild needed, configuration unchanged"
    # 检查是否已经有构建版本
    if [ ! -f "_build_dbg/bin/cachesim" ]; then
        echo "📦 No existing build found, building libCacheSim..."
        bash scripts/debug.sh -c
        if [ $? -ne 0 ]; then
            echo -e "${RED}Build failed. Please fix any compile errors.${NC}"
            exit 1
        fi
    fi
fi

# 设置Python环境 (新增stable-baselines3和gymnasium)
echo "Setting up Python environment..."
pip install -q stable-baselines3 gymnasium torch

# 确保权限设置正确
echo "Ensuring proper permissions..."
umask 0  # Set umask to allow full permissions


# 先启动Python脚本，由其主动创建共享内存文件（开启无缓冲输出便于实时观测日志）
PYTHON_LOG_FILE="ac_sb3_${RUN_TIMESTAMP}.log"
export PYTHONUNBUFFERED=1
echo -e "${YELLOW}Starting stable-baselines3 training script... (Log: ${PYTHON_LOG_FILE})${NC}"
python3 scripts/loh_actor_critic_sb3.py --miss-ratio-weight "$MISS_RATIO_WEIGHT" > "${PYTHON_LOG_FILE}" 2>&1 &
PYTHON_PID=$!

# 等待共享内存文件由Python端创建（延长等待时间并打印心跳，考虑首次导入torch可能较慢）
echo "Waiting for Python script to create shared memory file..."
WAIT_MAX_SEC=240
WAITED=0
while [ ${WAITED} -lt ${WAIT_MAX_SEC} ]; do
    if [ -f /dev/shm/loh_ac_9876 ]; then
        echo "Shared memory file successfully created by Python."
        ls -la /dev/shm/loh_ac_9876
        break
    fi
    if ! ps -p $PYTHON_PID > /dev/null; then
        echo -e "${RED}Error: Python SB3 script failed to start or exited early. Check ${PYTHON_LOG_FILE} for details.${NC}"
        echo "--- Python log head ---"; head -n 50 "${PYTHON_LOG_FILE}" || true; echo "-----------------------"
        echo "--- Python log tail ---"; tail -n 50 "${PYTHON_LOG_FILE}" || true; echo "-----------------------"
        exit 1
    fi
    if [ $((WAITED % 5)) -eq 0 ]; then
        echo "[wait ${WAITED}s/${WAIT_MAX_SEC}s] Waiting for /dev/shm/loh_ac_9876 ... (python pid=$PYTHON_PID)"
        # 打印一小段python日志便于诊断是否卡在导入阶段
        tail -n 5 "${PYTHON_LOG_FILE}" || true
    fi
    sleep 1
    WAITED=$((WAITED+1))
done
if [ ! -f /dev/shm/loh_ac_9876 ]; then
    echo -e "${RED}Error: Shared memory file was not created by Python within ${WAIT_MAX_SEC}s.${NC}"
    echo "--- Python log head ---"; head -n 50 "${PYTHON_LOG_FILE}" || true; echo "-----------------------"
    echo "--- Python log tail ---"; tail -n 200 "${PYTHON_LOG_FILE}" || true; echo "-----------------------"
    kill $PYTHON_PID || true
    exit 1
fi

echo -e "${GREEN}stable-baselines3 script is running with PID: $PYTHON_PID${NC}"
echo

echo -e "${BLUE}Running cache simulation with LOH algorithm (with SB3 integration)...${NC}"
echo "You should see training updates if the system is working correctly."

# 定义测试参数 (TRACE_FILE和CACHE_SIZE已在脚本开头定义)
TRACE_TYPE="oracleGeneral"

echo "Using trace file: $TRACE_FILE (type: $TRACE_TYPE, cache size: $CACHE_SIZE)"

# 执行缓存模拟器 - 输出到文件以便调试
echo -e "${YELLOW}Running cachesim with the following parameters:${NC}"
echo "  Trace file: $TRACE_FILE"
echo "  Trace type: $TRACE_TYPE"
echo "  Cache size: $CACHE_SIZE"
echo "  Eviction: LOH (with SB3 RL)"
echo "  Processing all requests in trace file"

# 执行缓存模拟
CACHESIM_LOG_FILE="cachesim_sb3_${RUN_TIMESTAMP}.log"
echo -e "${BLUE}Running cachesim... (Log: ${CACHESIM_LOG_FILE})${NC}"
echo "  Miss ratio weight: $MISS_RATIO_WEIGHT"
echo "  Byte miss ratio weight: $BYTE_MISS_RATIO_WEIGHT"
# 支持通过环境变量或第5个位置参数指定 rl_update_interval
# 优先级：第5个参数 > 环境变量 RL_UPDATE_INTERVAL > 环境变量 rl_update_interval
ENV_RL_UPD="${RL_UPDATE_INTERVAL:-$rl_update_interval}"
if [ -n "$5" ]; then
    RL_UPDATE_INTERVAL_ARG="$5"
elif [ -n "$ENV_RL_UPD" ]; then
    RL_UPDATE_INTERVAL_ARG="$ENV_RL_UPD"
else
    RL_UPDATE_INTERVAL_ARG=""
fi

# 支持通过第6个位置参数或环境变量 CACHESIM_NUM_REQ 指定要处理的请求数
# 优先级：第6个参数 > 环境变量 CACHESIM_NUM_REQ
if [ -n "$6" ]; then
    CACHESIM_NUM_REQ_ARG="--num-req=$6"
elif [ -n "${CACHESIM_NUM_REQ:-}" ]; then
    CACHESIM_NUM_REQ_ARG="--num-req=${CACHESIM_NUM_REQ}"
else
    CACHESIM_NUM_REQ_ARG=""
fi

# 组装 eviction-params 字符串
EV_PARAMS="miss-ratio-weight=$MISS_RATIO_WEIGHT"
if [ -n "$RL_UPDATE_INTERVAL_ARG" ]; then
    EV_PARAMS=",rl-update-interval=$RL_UPDATE_INTERVAL_ARG"
    EV_PARAMS="miss-ratio-weight=$MISS_RATIO_WEIGHT,rl-update-interval=$RL_UPDATE_INTERVAL_ARG"
    echo "Using rl_update_interval=$RL_UPDATE_INTERVAL_ARG for cachesim"
fi

_build_dbg/bin/cachesim \
    "$TRACE_FILE" \
    "$TRACE_TYPE" \
    LOH \
    "$CACHE_SIZE" \
    --eviction-params="$EV_PARAMS" \
    ${CACHESIM_NUM_REQ_ARG:+$CACHESIM_NUM_REQ_ARG} \
    -v 1 > "${CACHESIM_LOG_FILE}" 2>&1

# 检查执行结果
if [ $? -ne 0 ]; then
    echo -e "${RED}Error: cachesim execution failed. Check ${CACHESIM_LOG_FILE} for details.${NC}"
    cat "${CACHESIM_LOG_FILE}"
    exit 1
else
    echo -e "${GREEN}Cachesim execution completed successfully.${NC}"
fi

# 显示cachesim的输出
echo -e "\n${YELLOW}Cachesim execution output summary:${NC}"
echo "----------------------------------------"
grep -E "LOH:|miss ratio|^cache size" "${CACHESIM_LOG_FILE}" | tail -n 20
echo "----------------------------------------"
echo "Full log available in ${CACHESIM_LOG_FILE}"

# 显示SB3训练的输出
echo -e "\n${YELLOW}stable-baselines3 training output:${NC}"
echo "----------------------------------------"
tail -n 30 "${PYTHON_LOG_FILE}"
echo "----------------------------------------"

# 检查执行过程中的错误
echo -e "\n${YELLOW}检查日志中的错误信息...${NC}"
if grep -q -E "(^Error|Exception|Failed|Fatal)" "${PYTHON_LOG_FILE}"; then
    echo -e "${RED}警告：在Python日志中检测到错误信息。${NC}"
    grep -n -E "(^Error|Exception|Failed|Fatal)" "${PYTHON_LOG_FILE}" | head -5
else
    echo -e "${GREEN}Python日志中未检测到错误信息。${NC}"
fi

# 优雅停止：通过共享内存写 terminate=1，再等待Python自行退出
echo -e "\n${YELLOW}Stopping stable-baselines3 training script gracefully...${NC}"
if ps -p $PYTHON_PID > /dev/null; then
    python3 scripts/loh_stop.py || true
    # 最多等待8秒
    # 使用 seq 代替 brace expansion ("{1..16}") 以提高兼容性，避免在非-bash shell 中出现语法错误
    for i in $(seq 1 16); do
        if ! ps -p $PYTHON_PID > /dev/null; then
            break
        fi
        sleep 0.5
    done
    if ps -p $PYTHON_PID > /dev/null; then
        echo "Graceful stop timed out, sending SIGTERM..."
        kill $PYTHON_PID
    else
        echo "Python process exited gracefully."
    fi
else
    echo "Python process not found. It may have terminated already."
fi

# 清理共享内存文件
echo "Cleaning up shared memory file..."
if [ -f /dev/shm/loh_ac_9876 ]; then
    rm -f /dev/shm/loh_ac_9876
    echo "Removed existing shared memory file"
fi

# ====================================================================
# 分析部分
# ====================================================================

echo -e "\n${BLUE}=== stable-baselines3 训练结果分析 ===${NC}"

# 【新增】分析C++发送给Python的性能指标
echo -e "\n${YELLOW}C++性能指标分析 (发送给RL):${NC}"
if grep -q "Sending RL request" "${CACHESIM_LOG_FILE}"; then
    echo -e "${GREEN}检测到C++向Python发送的性能指标日志！${NC}"
    echo "OMR = Object Miss Ratio (对象未命中率), BMR = Byte Miss Ratio (字节未命中率)"
    echo -e "\n最后几次发送的指标:"
    grep "Sending RL request" "${CACHESIM_LOG_FILE}" | tail -n 10
else
    echo -e "${RED}未检测到C++性能指标日志。${NC}"
fi

# 检查SB3训练是否成功启动
echo -e "\n${YELLOW}SB3训练与奖励分析 (Python端):${NC}"
# SB3会打印一个包含 "rollout/" 的表格
if grep -q "rollout/" "${PYTHON_LOG_FILE}"; then
    TRAINING_UPDATES=$(grep -c "rollout/" "${PYTHON_LOG_FILE}")
    echo -e "${GREEN}检测到SB3训练正常启动并进行了更新！${NC}"
    echo -e "📊 SB3 训练更新次数: $TRAINING_UPDATES"

    # 显示最后几次训练的损失和奖励
    # Python端的奖励(Reward)是基于OMR和BMR计算的，最终体现在 rollout/ep_rew_mean 指标中
    echo -e "\n${YELLOW}最近的训练指标 (包含奖励):${NC}"
    # 抓取包含SB3表格的最后几行
    grep -E "rollout/|time/|train/" "${PYTHON_LOG_FILE}" | tail -n 15
else
    echo -e "${RED}未检测到SB3训练更新。请检查 ${PYTHON_LOG_FILE} 确认环境是否正确启动。${NC}"
fi

# 检查权重更新
echo -e "\n${YELLOW}权重更新分析 (C++端接收):${NC}"
if grep -q "Updated weights from Actor-Critic" "${CACHESIM_LOG_FILE}"; then
    WEIGHT_COUNT=$(grep -c "Updated weights from Actor-Critic" "${CACHESIM_LOG_FILE}")
    echo -e "${GREEN}检测到权重更新，C++/Python通信正常！${NC}"
    echo -e "📊 权重更新次数: $WEIGHT_COUNT"
else
    echo -e "${RED}未检测到权重更新，通信可能存在问题。${NC}"
fi

# 最终结论
echo -e "\n${BLUE}=== 测试结论 ===${NC}"
if [ -f "${PYTHON_LOG_FILE}" ] && grep -q -E "(^Error|Exception|Failed|Fatal)" "${PYTHON_LOG_FILE}"; then
    echo -e "${RED}Python SB3脚本检测到错误。${NC}"
    echo -e "请检查 ${PYTHON_LOG_FILE} 中的详细错误信息。"
elif grep -q "rollout/" "${PYTHON_LOG_FILE}" && grep -q "Updated weights from Actor-Critic" "${CACHESIM_LOG_FILE}"; then
    echo -e "${GREEN}SB3集成测试成功完成！${NC}"
    echo -e "✅ C++与Python的通信正常。"
    echo -e "✅ SB3模型训练已启动并更新。"
    echo -e "✅ 缓存模拟正常执行。"
    echo -e "\n${YELLOW}下一步: 运行 'tensorboard --logdir ./runs' 来可视化训练过程。${NC}"
else
    echo -e "${YELLOW}测试完成，但SB3训练或通信未完全确认。${NC}"
    echo -e "请检查 ${PYTHON_LOG_FILE} 和 ${CACHESIM_LOG_FILE} 日志。"
fi

echo -e "\n${GREEN}LOH与stable-baselines3集成测试完成！${NC}"

# 附加：两端序号对齐快速核查
echo -e "\n${YELLOW}两端序列号对齐摘要:${NC}"
PY_SEQ_LAST=$(grep -E "\[第[0-9]+次\] Python已写入权重|\[第[0-9]+次\] 初始状态对齐|\[BG\]\[第[0-9]+次\]" "$PYTHON_LOG_FILE" | sed -E 's/.*第([0-9]+)次.*/\1/' | tail -n 1)
C_SEQ_LAST=$(grep -E "\[第[0-9]+次\] LOH DEBUG: Received weights|等待超时|Sending RL request" "$CACHESIM_LOG_FILE" | sed -E 's/.*第([0-9]+)次.*/\1/' | tail -n 1)
echo "Python最后一次序号: ${PY_SEQ_LAST:-N/A}"
echo "C端最后一次序号: ${C_SEQ_LAST:-N/A}"
