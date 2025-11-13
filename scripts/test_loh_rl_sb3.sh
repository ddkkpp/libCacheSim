#!/bin/bash
# 测试LOH算法与stable-baselines3 RL集成的脚本

# 使用说明函数
usage() {
    echo "Usage: $0 [trace_file] [state_dim] [cache_size] [miss_ratio_weight] [python_script] [eviction_algo]"
    echo "  trace_file:         Path to trace file (optional, default: data/MetaCDN/meta_reag.oracleGeneral.zst)"
    echo "  state_dim:          State dimension (optional, default: 26)"
    echo "  cache_size:         Cache size as ratio (optional, default: 0.1)"
    echo "  miss_ratio_weight:  Weight for object miss ratio in reward (optional, default: 1.0, byte_miss_ratio_weight = 1.0 - miss_ratio_weight)"
    echo "  python_script:      Python script to run (optional, default: loh_actor_critic_sb3.py)"
    echo "  eviction_algo:      Eviction algorithm name passed to cachesim (optional, default: LOH). Examples: LOH, loh-mr-blocked, loh-mr-noblocked"
    echo
    echo "Environment Variables:"
    echo "  LEARNING_STARTS:      Number of steps before training starts (default: 1000)"
    echo "  EXCLUDE_RECENT_STEPS: Number of recent steps to exclude from sampling (default: 100)"
    echo "  PYTHON_SCRIPT:        Python script to run (default: loh_actor_critic_sb3.py)"
    echo "  EVICTION_ALGO:        Eviction algorithm to pass to cachesim (default: LOH)"
    echo "  RL_UPDATE_INTERVAL:   Interval for RL updates (optional, no default)"
    echo "  CACHESIM_NUM_REQ:     Number of requests to process (optional, processes entire trace by default)"
    echo
    echo "Examples:"
    echo "  $0"
    echo "  $0 /path/to/trace.gz"
    echo "  $0 /path/to/trace.gz 26"
    echo "  $0 /path/to/trace.gz 26 0.2"
    echo "  $0 /path/to/trace.gz 26 0.2 0.8    # 80% object miss ratio, 20% byte miss ratio"
    echo "  $0 /path/to/trace.gz 26 0.2 0.8 loh_actor_critic_sb3_SACblocked.py  # Use blocked MR variant (loh-mr-blocked)"
    echo "  LEARNING_STARTS=500 EXCLUDE_RECENT_STEPS=50 $0 /path/to/trace.gz"
    echo "  PYTHON_SCRIPT=loh_actor_critic_sb3_SACblocked.py CACHESIM_NUM_REQ=100000 $0 /path/to/trace.gz"
    echo "  RL_UPDATE_INTERVAL=1000 CACHESIM_NUM_REQ=100000 $0 /path/to/trace.gz  # With RL update interval"
    exit 1
}

# 处理帮助参数
if [[ "$1" == "--help" ]] || [[ "$1" == "-h" ]]; then
    usage
fi

echo "=== Testing LOH with stable-baselines3 Reinforcement Learning ==="
echo

# 预清理：避免上一轮残留影响本次运行。
# 并行安全模式：设置 LOH_PARALLEL_SAFE=1 将跳过全局 pkill/stop，仅按本次 LOH_SHM_KEY 做局部清理。
if [ "${LOH_PARALLEL_SAFE:-0}" = "1" ]; then
    echo "[pre-stop] Parallel-safe mode enabled: skip global stop/kill."
    # 仅在提供了 LOH_SHM_KEY 时，尝试清理对应共享内存文件（不影响其它实例）
    if [ -n "${LOH_SHM_KEY:-}" ] && [ -f "/dev/shm/loh_ac_${LOH_SHM_KEY}" ]; then
        rm -f "/dev/shm/loh_ac_${LOH_SHM_KEY}" || true
        echo "[pre-stop] Removed /dev/shm/loh_ac_${LOH_SHM_KEY}"
    fi
else
    echo "[pre-stop] 停止可能残留的上一次运行..."
    if [ -x scripts/stop_loh_rl.sh ]; then
        ./scripts/stop_loh_rl.sh || true
    else
        # 兜底：尽量不报错地清理（注意：会影响所有匹配进程，不适合并行场景）
        pkill -f "scripts/loh_actor_critic_sb3.*\.py" || true
        pkill -f "_build_dbg/bin/cachesim.* LOH" || true
        # 如果未设置 LOH_SHM_KEY，这里只做通配清理，不会误删其他实例
        if [ -n "${LOH_SHM_KEY:-}" ]; then
            [ -f "/dev/shm/loh_ac_${LOH_SHM_KEY}" ] && rm -f "/dev/shm/loh_ac_${LOH_SHM_KEY}" || true
        else
            # 保守清理：不使用 rm /dev/shm/loh_ac_*，避免误删其他并行实例
            true
        fi
    fi
    echo "[pre-stop] 完成。"
fi

# --- 【新增】Python脚本选择 ---
# 优先级：第5个位置参数 > 环境变量 PYTHON_SCRIPT > 默认值
if [ -n "$5" ]; then
    PYTHON_SCRIPT="$5"
    echo "使用您指定的Python脚本（位置参数5）: $PYTHON_SCRIPT"
elif [ -n "${PYTHON_SCRIPT:-}" ]; then
    echo "使用环境变量指定的Python脚本: $PYTHON_SCRIPT"
else
    PYTHON_SCRIPT="loh_actor_critic_sb3.py"
    echo "未指定Python脚本，使用默认: $PYTHON_SCRIPT"
fi

# 验证Python脚本文件是否存在
if [ ! -f "scripts/$PYTHON_SCRIPT" ]; then
    echo -e "\033[0;31m错误: Python脚本 'scripts/$PYTHON_SCRIPT' 不存在! 请检查路径。\033[0m"
    echo "可用的脚本："
    ls -1 scripts/loh_actor_critic_sb3*.py 2>/dev/null || echo "  (未找到匹配的脚本)"
    exit 1
fi

# --- 【修复】状态向量维度配置（尊重环境并与构建宏一致） ---
# 解析优先级：
# 1) 位置参数 $2 明确给出 26/38
# 2) 已存在的环境变量 LOH_STATE_DIM（若有效）
# 3) 环境变量 LOH_INCLUDE_CACHE_FEATURES（1->38, 0->26）
# 4) 默认：38（包含缓存特征）以与构建默认保持一致
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
    echo "使用您指定的状态向量维度: ${STATE_DIM}维（位置参数2）"
else
    # 未提供位置参数，按环境/宏推导
    if [ -n "${LOH_STATE_DIM:-}" ]; then
        if [ "${LOH_STATE_DIM}" = "26" ] || [ "${LOH_STATE_DIM}" = "38" ]; then
            echo "沿用环境变量 LOH_STATE_DIM=${LOH_STATE_DIM} 维"
        else
            echo "[WARN] 环境 LOH_STATE_DIM='${LOH_STATE_DIM}' 非法，尝试根据 LOH_INCLUDE_CACHE_FEATURES 推导"
            if [ -n "${LOH_INCLUDE_CACHE_FEATURES:-}" ] && [ "${LOH_INCLUDE_CACHE_FEATURES}" = "0" ]; then
                export LOH_STATE_DIM="26"
            else
                export LOH_STATE_DIM="38"
            fi
            echo "已解析状态向量维度为: ${LOH_STATE_DIM} 维"
        fi
    else
        # 根据 LOH_INCLUDE_CACHE_FEATURES 推导，否则默认 38
        if [ -n "${LOH_INCLUDE_CACHE_FEATURES:-}" ]; then
            if [ "${LOH_INCLUDE_CACHE_FEATURES}" = "0" ]; then
                export LOH_STATE_DIM="26"
            else
                export LOH_STATE_DIM="38"
            fi
            echo "根据 LOH_INCLUDE_CACHE_FEATURES=${LOH_INCLUDE_CACHE_FEATURES} 推导状态维度: ${LOH_STATE_DIM} 维"
        else
            export LOH_STATE_DIM="38"
            echo "未指定状态向量维度，默认: 38维（包含缓存特征）"
        fi
    fi
fi

# --- 【新增】可选的 eviction algorithm 选择 ---
# 优先级：第6个位置参数 > 环境变量 EVICTION_ALGO > 默认值
if [ -n "$6" ]; then
    EVICTION_ALGO="$6"
    echo "使用您指定的 eviction 算法（位置参数6）: $EVICTION_ALGO"
elif [ -n "${EVICTION_ALGO:-}" ]; then
    echo "使用环境变量指定的 eviction 算法: $EVICTION_ALGO"
else
    EVICTION_ALGO="LOH"
    echo "未指定 eviction 算法，使用默认: $EVICTION_ALGO"
fi

# 小写/大写不敏感，但保持原始大小写用于日志显示


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
export RUN_TIMESTAMP  # 导出供Python脚本使用

# 为本次运行生成唯一的共享内存键（支持外部传入覆盖）
# 优先使用已有的 LOH_SHM_KEY，否则用 时间戳+PID 组合成一个数值键
if [ -z "${LOH_SHM_KEY:-}" ]; then
    LOH_SHM_KEY="$((10#$(date +%H%M%S) * 1000 + ($$ % 1000)))"
fi
export LOH_SHM_KEY
echo "Using LOH_SHM_KEY=${LOH_SHM_KEY} (shared memory: /dev/shm/loh_ac_${LOH_SHM_KEY})"

# 清理可能存在的共享内存文件
echo "Cleaning up any existing shared memory files for this run..."
if [ -f "/dev/shm/loh_ac_${LOH_SHM_KEY}" ]; then
    rm -f "/dev/shm/loh_ac_${LOH_SHM_KEY}"
    echo "Removed existing shared memory file /dev/shm/loh_ac_${LOH_SHM_KEY}"
fi

# 设置一些颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}开始测试LOH算法与stable-baselines3强化学习的集成...${NC}"

echo "Configuring build for LOH_STATE_DIM=${LOH_STATE_DIM} (26->no cache, 38->with cache)"
# 统一通过构建宏控制（不再修改源码）——始终重建以确保宏生效
echo "📦 Rebuilding libCacheSim with LOH_INCLUDE_CACHE_FEATURES derived from LOH_STATE_DIM..."
bash scripts/debug.sh -c
if [ $? -ne 0 ]; then
    echo -e "${RED}Build failed. Please fix any compile errors.${NC}"
    exit 1
fi
echo "✅ Rebuild completed successfully"

# 设置Python环境 (新增stable-baselines3和gymnasium)
echo "Setting up Python environment..."
pip install -q stable-baselines3 gymnasium torch

# 确保权限设置正确
echo "Ensuring proper permissions..."
umask 0  # Set umask to allow full permissions


# 先启动Python脚本，由其主动创建共享内存文件（开启无缓冲输出便于实时观测日志）
PYTHON_LOG_FILE="ac_sb3_${RUN_TIMESTAMP}.log"
export PYTHONUNBUFFERED=1

# 构建Python脚本参数
PYTHON_ARGS="--miss-ratio-weight $MISS_RATIO_WEIGHT"

# 支持通过环境变量配置learning-starts
if [ -n "${LEARNING_STARTS:-}" ]; then
    PYTHON_ARGS="$PYTHON_ARGS --learning-starts $LEARNING_STARTS"
    echo "Using learning-starts=$LEARNING_STARTS"
fi

# 支持通过环境变量配置exclude-recent-steps
if [ -n "${EXCLUDE_RECENT_STEPS:-}" ]; then
    PYTHON_ARGS="$PYTHON_ARGS --exclude-recent-steps $EXCLUDE_RECENT_STEPS"
    echo "Using exclude-recent-steps=$EXCLUDE_RECENT_STEPS"
fi

# --- 【新增】支持通过环境变量设置随机种子（LOH_RL_SEED 或 SEED） ---
# 目的：允许在一行内联环境变量运行（例如：LOH_RL_SEED=42 bash test_loh_rl_sb3.sh ...），
# 并把种子传递给 Python（--seed）和设置 PYTHONHASHSEED，以提高可重复性。
if [ -n "${LOH_RL_SEED:-}" ]; then
    # 优先使用 LOH_RL_SEED
    export LOH_RL_SEED
    export PYTHONHASHSEED="${LOH_RL_SEED}"
    echo "Using LOH_RL_SEED=${LOH_RL_SEED} (exported to Python environment, PYTHONHASHSEED set)"
elif [ -n "${SEED:-}" ]; then
    # 向后兼容: 如果只设置了 SEED，也导出为 LOH_RL_SEED
    export LOH_RL_SEED="${SEED}"
    export PYTHONHASHSEED="${SEED}"
    echo "Using SEED=${SEED} (exported as LOH_RL_SEED to Python environment, PYTHONHASHSEED set)"
fi

echo -e "${YELLOW}Starting stable-baselines3 training script... (Log: ${PYTHON_LOG_FILE})${NC}"
echo "Python script: scripts/$PYTHON_SCRIPT"
echo "Python arguments: $PYTHON_ARGS"
python3 "scripts/$PYTHON_SCRIPT" $PYTHON_ARGS \
    > "${PYTHON_LOG_FILE}" 2>&1 &
PYTHON_PID=$!

# 等待共享内存文件由Python端创建（延长等待时间并打印心跳，考虑首次导入torch可能较慢）
echo "Waiting for Python script to create shared memory file..."
WAIT_MAX_SEC=240
WAITED=0
while [ ${WAITED} -lt ${WAIT_MAX_SEC} ]; do
    if [ -f "/dev/shm/loh_ac_${LOH_SHM_KEY}" ]; then
        echo "Shared memory file successfully created by Python."
        ls -la "/dev/shm/loh_ac_${LOH_SHM_KEY}"
        break
    fi
    if ! ps -p $PYTHON_PID > /dev/null; then
        echo -e "${RED}Error: Python SB3 script failed to start or exited early. Check ${PYTHON_LOG_FILE} for details.${NC}"
        echo "--- Python log head ---"; head -n 50 "${PYTHON_LOG_FILE}" || true; echo "-----------------------"
        echo "--- Python log tail ---"; tail -n 50 "${PYTHON_LOG_FILE}" || true; echo "-----------------------"
        exit 1
    fi
    if [ $((WAITED % 5)) -eq 0 ]; then
    echo "[wait ${WAITED}s/${WAIT_MAX_SEC}s] Waiting for /dev/shm/loh_ac_${LOH_SHM_KEY} ... (python pid=$PYTHON_PID)"
        # 打印一小段python日志便于诊断是否卡在导入阶段
        tail -n 5 "${PYTHON_LOG_FILE}" || true
    fi
    sleep 1
    WAITED=$((WAITED+1))
done
if [ ! -f "/dev/shm/loh_ac_${LOH_SHM_KEY}" ]; then
    echo -e "${RED}Error: Shared memory file was not created by Python within ${WAIT_MAX_SEC}s.${NC}"
    echo "--- Python log head ---"; head -n 50 "${PYTHON_LOG_FILE}" || true; echo "-----------------------"
    echo "--- Python log tail ---"; tail -n 200 "${PYTHON_LOG_FILE}" || true; echo "-----------------------"
    kill $PYTHON_PID || true
    exit 1
fi

echo -e "${GREEN}stable-baselines3 script is running with PID: $PYTHON_PID${NC}"
echo

echo -e "${BLUE}Running cache simulation with eviction algorithm ${EVICTION_ALGO} (with SB3 integration)...${NC}"
echo "You should see training updates if the system is working correctly."

# 定义测试参数 (TRACE_FILE和CACHE_SIZE已在脚本开头定义)
# 如果 trace 文件是 CSV，则把 TRACE_TYPE 设置为 csv（cachesim 支持的 trace type），否则使用默认 oracleGeneral
if [[ "$TRACE_FILE" == *.csv ]]; then
    TRACE_TYPE="csv"
else
    TRACE_TYPE="oracleGeneral"
fi

echo "Using trace file: $TRACE_FILE (type: $TRACE_TYPE, cache size: $CACHE_SIZE)"

# 执行缓存模拟器 - 输出到文件以便调试
echo -e "${YELLOW}Running cachesim with the following parameters:${NC}"
echo "  Trace file: $TRACE_FILE"
echo "  Trace type: $TRACE_TYPE"
echo "  Cache size: $CACHE_SIZE"
echo "  Eviction: $EVICTION_ALGO (with SB3 RL)"
echo "  Processing all requests in trace file"

# 执行缓存模拟
CACHESIM_LOG_FILE="cachesim_sb3_${RUN_TIMESTAMP}.log"
echo -e "${BLUE}Running cachesim... (Log: ${CACHESIM_LOG_FILE})${NC}"
echo "  Miss ratio weight: $MISS_RATIO_WEIGHT"
echo "  Byte miss ratio weight: $BYTE_MISS_RATIO_WEIGHT"

# 支持通过环境变量指定 rl_update_interval
if [ -n "${RL_UPDATE_INTERVAL:-}" ]; then
    RL_UPDATE_INTERVAL_ARG="$RL_UPDATE_INTERVAL"
    echo "  RL update interval: $RL_UPDATE_INTERVAL"
else
    RL_UPDATE_INTERVAL_ARG=""
fi

# 支持通过环境变量 CACHESIM_NUM_REQ 指定要处理的请求数
if [ -n "${CACHESIM_NUM_REQ:-}" ]; then
    CACHESIM_NUM_REQ_ARG="--num-req=${CACHESIM_NUM_REQ}"
    echo "  Num requests: $CACHESIM_NUM_REQ"
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

# 如果是 CSV Trace，则提供默认的 trace-type-params（作为单个字符串值），
# 并确保以两个 argv 项（flag + value）传递给 cachesim，避免 shell 引号问题。
TRACE_TYPE_PARAMS_ARG=()
if [ "${TRACE_TYPE}" = "csv" ]; then
    # 默认的 CSV 列映射（可根据具体 CSV 结构调整）
    TRACE_TYPE_PARAMS_VAL="time-col=1,obj-id-col=2,obj-size-col=3,obj-id-is-num=1,has-header=false,delimiter,"
    # 注意 delimiter 逗号在参数值中，需要传为普通字符（不加转义在数组中没问题）
    TRACE_TYPE_PARAMS_VAL="time-col=1,obj-id-col=2,obj-size-col=3,obj-id-is-num=1,has-header=false,delimiter=,"
    TRACE_TYPE_PARAMS_ARG=(--trace-type-params "$TRACE_TYPE_PARAMS_VAL")
    echo "Using CSV trace-type-params: $TRACE_TYPE_PARAMS_VAL"
fi

# 使用数组构建命令以正确传递参数而不被 shell 重写或错误引用
CACHESIM_CMD=("_build_dbg/bin/cachesim" "$TRACE_FILE" "$TRACE_TYPE" "$EVICTION_ALGO" "$CACHE_SIZE")
if [ ${#TRACE_TYPE_PARAMS_ARG[@]} -ne 0 ]; then
    CACHESIM_CMD+=("${TRACE_TYPE_PARAMS_ARG[@]}")
fi
CACHESIM_CMD+=("--eviction-params=$EV_PARAMS")
if [ -n "${CACHESIM_NUM_REQ_ARG:-}" ]; then
    CACHESIM_CMD+=("${CACHESIM_NUM_REQ_ARG}")
fi
CACHESIM_CMD+=("-v" "1")

# 打印并执行命令
echo "Executing cachesim command:"
printf ' %q' "${CACHESIM_CMD[@]}"; echo
"${CACHESIM_CMD[@]}" > "${CACHESIM_LOG_FILE}" 2>&1

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
    LOH_SHM_KEY="${LOH_SHM_KEY}" python3 scripts/loh_stop.py || true
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
if [ -f "/dev/shm/loh_ac_${LOH_SHM_KEY}" ]; then
    rm -f "/dev/shm/loh_ac_${LOH_SHM_KEY}"
    echo "Removed existing shared memory file /dev/shm/loh_ac_${LOH_SHM_KEY}"
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
# 优先用SB3自带的表格（包含 "rollout/"），否则退化为我们自定义的训练与通信信号
if grep -q "rollout/" "${PYTHON_LOG_FILE}"; then
    TRAINING_UPDATES=$(grep -c "rollout/" "${PYTHON_LOG_FILE}")
    echo -e "${GREEN}检测到SB3训练正常启动并进行了更新！${NC}"
    echo -e "📊 SB3 训练更新次数: $TRAINING_UPDATES"

    echo -e "\n${YELLOW}最近的训练指标 (包含奖励):${NC}"
    grep -E "rollout/|time/|train/" "${PYTHON_LOG_FILE}" | tail -n 15
else
    # 兜底：检查我们在脚本中打印的训练/通信信号，诸如 [Step N]、weights write completed、Python weights written 等
    if grep -q -E "\[Step[[:space:]]+[0-9]+\]|weights write completed|Python weights written" "${PYTHON_LOG_FILE}"; then
        STEP_COUNT=$(grep -c -E "\[Step[[:space:]]+[0-9]+\]" "${PYTHON_LOG_FILE}" || true)
        WEIGHTS_WRITTEN_COUNT=$(grep -c -E "weights write completed|Python weights written" "${PYTHON_LOG_FILE}" || true)
        echo -e "${GREEN}检测到自定义训练/通信日志，SB3循环正常运行。${NC}"
        echo -e "📊 Step事件: ${STEP_COUNT:-0} 次，权重写入: ${WEIGHTS_WRITTEN_COUNT:-0} 次"
        echo -e "\n${YELLOW}最近的事件片段:${NC}"
        grep -E "\[Step|weights write completed|Python weights written|ReplayBuffer|Reward→Final" "${PYTHON_LOG_FILE}" | tail -n 20 || true
    else
        echo -e "${RED}未检测到SB3训练更新。请检查 ${PYTHON_LOG_FILE} 确认环境是否正确启动。${NC}"
    fi
fi

# 检查权重更新
echo -e "\n${YELLOW}权重更新分析 (C++端接收):${NC}"
if grep -q -E "Updated weights from Actor-Critic|Received weights from Python|\[C-WEIGHTS\]" "${CACHESIM_LOG_FILE}"; then
    WEIGHT_COUNT=$(grep -c -E "Updated weights from Actor-Critic|Received weights from Python|\[C-WEIGHTS\]" "${CACHESIM_LOG_FILE}")
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
elif { grep -q "rollout/" "${PYTHON_LOG_FILE}" || grep -q -E "\[Step[[:space:]]+[0-9]+\]|weights write completed|Python weights written" "${PYTHON_LOG_FILE}"; } \
     && grep -q -E "Updated weights from Actor-Critic|Received weights from Python|\[C-WEIGHTS\]" "${CACHESIM_LOG_FILE}"; then
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
