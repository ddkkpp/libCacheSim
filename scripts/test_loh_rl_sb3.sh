#!/bin/bash
# LOH 与 stable-baselines3 RL 集成测试脚本
# 简化版：统一使用环境变量配置，移除冗余的命令行参数

# 使用说明函数
usage() {
    echo "Usage: $0 [trace_file] [cache_size]"
    echo "  trace_file:  Path to trace file (optional, default: data/MetaCDN/meta_reag.oracleGeneral.zst)"
    echo "  cache_size:  Cache size as ratio (optional, default: 0.1)"
    echo
    echo "Environment Variables (all optional):"
    echo
    echo "  === Algorithm Selection ==="
    echo "  LOH_RL_ALGO:                     RL algorithm: PPO, SAC, TD3 (default: SAC)"
    echo
    echo "  === State Dimension (C compile-time) ==="
    echo "  Note: First 2 dims (hit_ratio, byte_hit_ratio) always passed for reward calculation"
    echo "  LOH_INCLUDE_TOPK_CANDIDATE_FEATURES: Include TopK candidate features, 192 dims (default: 0)"
    echo "  LOH_INCLUDE_AVGTOPK_CANDIDATE_FEATURES: Include AvgTopK average features, 24 dims (default: 1)"
    echo "  LOH_INCLUDE_REQUEST:              Include recent request history (REQUEST_HISTORY_LEN×6 dims, default: 0)"
    echo "  LOH_INCLUDE_CACHE_FEATURES:      Include cache features, 12 dims (default: 0)"
    echo "  LOH_INCLUDE_CANDIDATE_FEATURES:  Include candidate statistics, 72 dims (default: 0)"
    echo "  LOH_INCLUDE_HIT_MISS_FEATURES:   Include hit/miss features, 24 dims (default: 0)"
    echo
    echo "  === RL Observation (Python runtime) ==="
    echo "  RL_STATE_USE_MISSRATIO:          Include first 2 dims in RL observation (default: 1)"
    echo "                                   Set to 0 to exclude hit_ratio, byte_hit_ratio from RL obs"
    echo
    echo "  === Reward/Penalty ==="
    echo "  LOH_MISS_RATIO_WEIGHT:           Weight for object miss ratio (default: 1.0)"
    echo "  LOH_ENABLE_PENALTY:              Enable penalty mechanism (default: 0, requires rebuild)"
    echo "                                   ⚠️ This affects C compilation - will trigger auto rebuild"
    echo
    echo "  === Misc ==="
    echo "  RL_UPDATE_INTERVAL:              RL update interval (optional)"
    echo "  CACHESIM_NUM_REQ:                Limit number of requests to simulate (default: all)"
    echo "  CACHESIM_NUM_THREAD:             cachesim worker threads (passed as --num-thread, default: cachesim built-in)"
    echo "  LOH_DEBUG_LEVEL:                 Debug level 0-4 (default: 1)"
    echo "  LOH_ENABLE_PROFILING:            Enable profiling timer stats (default: 0)"
    echo
    echo "  === Online Finetune (Resume) ==="
    echo "  LOH_RESUME_PATH:                 Explicit checkpoint .zip path; only when set, Python will load+finetune"
    echo "  LOH_RESUME_DIR:                  (reserved) directory option; ignored unless you implement search"
    echo "  LOH_CHECKPOINT_FREQ:             Save checkpoint every N timesteps (default: 50000)"
    echo
    echo "Examples:"
    echo "  $0"
    echo "  $0 /path/to/trace.gz"
    echo "  $0 /path/to/trace.gz 0.2"
    echo "  LOH_RL_ALGO=PPO $0 /path/to/trace.gz"
    echo "  RL_STATE_USE_MISSRATIO=0 $0 /path/to/trace.gz   # RL obs excludes miss ratios"
    echo "  LOH_ENABLE_PENALTY=1 $0 /path/to/trace.gz       # Enable penalty (triggers rebuild)"
    exit 1
}

# 处理帮助参数
if [[ "$1" == "--help" ]] || [[ "$1" == "-h" ]]; then
    usage
fi

echo "=== LOH + stable-baselines3 RL Integration Test ==="
echo

# 打印与评分模式相关的核心环境变量，便于区分本次运行属于哪种模式
echo "[config] LOH_SCORE_USE_IRT=${LOH_SCORE_USE_IRT:-<unset>}"
echo "[config] LOH_SCORE_USE_COMPOUND=${LOH_SCORE_USE_COMPOUND:-<unset>}"
echo "[config] LOH_SCORE_MODEL=${LOH_SCORE_MODEL:-<unset>}"
echo "[config] LOH_MLP_HIDDEN=${LOH_MLP_HIDDEN:-<unset>}"
echo "[config] LOH_FEATURE_LOG1P=${LOH_FEATURE_LOG1P:-0}"
echo "[config] LOH_DUAL_CHANNEL=${LOH_DUAL_CHANNEL:-0}"
echo "[config] CACHESIM_NUM_REQ=${CACHESIM_NUM_REQ:-ALL}"
echo "[config] LOH_RESUME_DIR=${LOH_RESUME_DIR:-./runs}"
echo "[config] LOH_RESUME_PATH=${LOH_RESUME_PATH:-<unset>}"
echo "[config] LOH_CHECKPOINT_FREQ=${LOH_CHECKPOINT_FREQ:-50000}"

# 预清理：避免上一轮残留影响本次运行
if [ "${LOH_PARALLEL_SAFE:-0}" = "1" ]; then
    echo "[pre-stop] Parallel-safe mode: skip global cleanup"
    if [ -n "${LOH_SHM_KEY:-}" ] && [ -f "/dev/shm/loh_ac_${LOH_SHM_KEY}" ]; then
        rm -f "/dev/shm/loh_ac_${LOH_SHM_KEY}" || true
    fi
else
    echo "[pre-stop] Cleaning up previous runs..."
    if [ -x scripts/stop_loh_rl.sh ]; then
        ./scripts/stop_loh_rl.sh || true
    else
        pkill -f "scripts/loh_actor_critic_sb3.*\.py" || true
        pkill -f "_build_dbg/bin/cachesim.* LOH" || true
    fi
    echo "[pre-stop] Done."
fi

# Python 脚本固定为统一脚本（已整合 PPO/SAC/TD3）
PYTHON_SCRIPT="loh_actor_critic_sb3.py"

# Eviction 算法默认 LOH，可通过环境变量覆盖（例如 loh-teacher）
EVICTION_ALGO="${LOH_EVICTION_ALGO:-LOH}"

# 状态维度由环境变量控制（不再通过命令行）
echo "State dimension controlled by LOH_INCLUDE_* environment variables"

# 验证Python脚本文件是否存在
if [ ! -f "scripts/$PYTHON_SCRIPT" ]; then
    echo -e "\033[0;31m错误: Python脚本 'scripts/$PYTHON_SCRIPT' 不存在! 请检查路径。\033[0m"
    echo "可用的脚本："
    ls -1 scripts/loh_actor_critic_sb3*.py 2>/dev/null || echo "  (未找到匹配的脚本)"
    exit 1
fi

# --- 【简化】状态向量维度配置 ---
# 状态维度完全由 C/Python 代码中的默认值和环境变量控制，不再通过命令行参数指定
# 默认值：GLOBAL(2) + SAMPLE(192) = 194 维
# 如需调整，可设置环境变量：LOH_INCLUDE_SAMPLE_FEATURES, LOH_INCLUDE_CACHE_FEATURES 等
echo "状态向量维度由环境变量控制（默认：GLOBAL(2)+SAMPLE(192)=194维）"

# --- 【新增】可选的 eviction algorithm 选择 ---
# --- 参数解析 ---
# 参数1: trace文件路径
DEFAULT_TRACE_FILE="data/MetaCDN/meta_reag.oracleGeneral.zst"
if [ -n "$1" ]; then
    TRACE_FILE="$1"
    echo "Using trace file: $TRACE_FILE"
else
    TRACE_FILE="$DEFAULT_TRACE_FILE"
    echo "Using default trace file: $TRACE_FILE"
fi

# 验证数据文件是否存在
if [ ! -f "$TRACE_FILE" ]; then
    echo -e "\033[0;31mError: Trace file '$TRACE_FILE' not found!\033[0m"
    exit 1
fi

# 参数2: 缓存大小
if [ -n "$2" ]; then
    CACHE_SIZE="$2"
    if ! [[ "$CACHE_SIZE" =~ ^[0-9]*\.?[0-9]+$ ]] || (( $(echo "$CACHE_SIZE <= 0" | bc -l) )) || (( $(echo "$CACHE_SIZE > 1" | bc -l) )); then
        echo "Error: cache_size must be between 0 and 1, got: $CACHE_SIZE"
        usage
    fi
    echo "Using cache size: $CACHE_SIZE"
else
    CACHE_SIZE="0.1"
    echo "Using default cache size: $CACHE_SIZE"
fi

# Miss ratio 权重从环境变量读取（不再通过位置参数）
MISS_RATIO_WEIGHT="${LOH_MISS_RATIO_WEIGHT:-1.0}"
BYTE_MISS_RATIO_WEIGHT=$(echo "1.0 - $MISS_RATIO_WEIGHT" | bc -l)
echo "Using weights: miss_ratio_weight=$MISS_RATIO_WEIGHT, byte_miss_ratio_weight=$BYTE_MISS_RATIO_WEIGHT"

# 设置错误处理和调试
set -e  # 遇到错误时停止执行

# 生成唯一的时间戳（允许外部预先设置 RUN_TIMESTAMP，便于 sweep 批量实验做归档）
if [ -z "${RUN_TIMESTAMP:-}" ]; then
    RUN_TIMESTAMP=$(date +%m%d_%H%M%S) # 例如: 0730_173500
fi
export RUN_TIMESTAMP  # 导出供Python脚本使用

# 默认冷启动：只有显式设置 LOH_RESUME_PATH 才会加载模型继续训练
export LOH_RESUME_DIR="${LOH_RESUME_DIR:-./runs}"
export LOH_CHECKPOINT_FREQ="${LOH_CHECKPOINT_FREQ:-50000}"

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

# ---- Stop / cleanup helpers ----
_CLEANUP_DONE=0

write_terminate_flag() {
    # 使用统一工具脚本写 terminate，确保共享内存结构体字段/偏移与当前版本一致（weights[7]）
    if [ -f scripts/loh_stop.py ]; then
        python3 scripts/loh_stop.py "${LOH_SHM_KEY}" >/dev/null 2>&1 || true
    fi
}

cleanup_on_exit() {
    if [ "${_CLEANUP_DONE}" = "1" ]; then
        return
    fi
    _CLEANUP_DONE=1

    # signal Python to stop if shm exists
    write_terminate_flag || true

    # stop cachesim if still running
    if [ -n "${CACHESIM_PID:-}" ] && ps -p "${CACHESIM_PID}" > /dev/null 2>&1; then
        echo "[cleanup] stopping cachesim pid=${CACHESIM_PID}"
        kill -INT "${CACHESIM_PID}" 2>/dev/null || true
        sleep 1
        kill -TERM "${CACHESIM_PID}" 2>/dev/null || true
        sleep 1
        kill -KILL "${CACHESIM_PID}" 2>/dev/null || true
    fi

    # stop Python if still running
    if [ -n "${PYTHON_PID:-}" ] && ps -p "${PYTHON_PID}" > /dev/null 2>&1; then
        echo "[cleanup] stopping python pid=${PYTHON_PID}"
        kill -TERM "${PYTHON_PID}" 2>/dev/null || true
        sleep 1
        kill -KILL "${PYTHON_PID}" 2>/dev/null || true
    fi

    # remove shm
    if [ -n "${LOH_SHM_KEY:-}" ] && [ -f "/dev/shm/loh_ac_${LOH_SHM_KEY}" ]; then
        rm -f "/dev/shm/loh_ac_${LOH_SHM_KEY}" || true
    fi
}

trap cleanup_on_exit INT TERM EXIT

# ==== 构建策略说明（现在只在读到特定环境变量时才构建）====
# 1) 默认行为
#    - 不触发任何构建，直接复用已有的 _build_dbg/bin/cachesim。
#    - 如果该可执行文件不存在，则报错提示你手动构建。
#
# 2) 编译相关环境变量（触发增量构建）
#    - 若设置了以下任意环境变量，将在进入模拟前调用一次 scripts/debug.sh（不加 -c），进行增量构建：
#        * LOH_INCLUDE_HIT_MISS_FEATURES    # 显式控制是否包含 hit/miss 统计 (24维)
#        * LOH_INCLUDE_CACHE_FEATURES       # 显式控制是否包含 cache 特征 (12维)
#        * LOH_INCLUDE_CANDIDATE_FEATURES   # 显式控制是否包含 candidate 特征 (72维)
#        * LOH_INCLUDE_TOPK_CANDIDATE_FEATURES  # 显式控制是否包含 TopK 候选特征 (192维)
#        * LOH_INCLUDE_AVGTOPK_CANDIDATE_FEATURES  # 显式控制是否包含 AvgTopK 平均特征 (24维)
#        * LOH_DEBUG_LEVEL                  # 显式控制 C 端调试日志级别（0-4）
#    - 注：前2维(hit_ratio, byte_hit_ratio)始终传递，不再通过宏控制
#    - 这些变量会在 scripts/debug.sh 中被转换为编译宏，通常意味着你希望修改 C 侧特征维度/候选特征布局或调试日志级别。
#    - 一旦设置，我们假定你"需要重建"，因此不会再做额外比较，直接增量构建一次。
# ============================================================

# 整个检查+（可选）构建过程用 flock 串行化，避免并发冲突。
(
    flock 9

    if [ "${LOH_SKIP_BUILD:-0}" = "1" ]; then
        echo "[build] LOH_SKIP_BUILD=1, skip build step"
        NEED_REBUILD=0
    else

        # 是否存在编译相关环境变量（LOH_INCLUDE_* / LOH_DEBUG_LEVEL / LOH_ENABLE_PENALTY），决定是否需要构建
        NEED_REBUILD=0
         if [ -n "${LOH_INCLUDE_CACHE_FEATURES:-}" ] || \
             [ -n "${LOH_INCLUDE_CANDIDATE_FEATURES:-}" ] || \
             [ -n "${LOH_INCLUDE_HIT_MISS_FEATURES:-}" ] || \
             [ -n "${LOH_INCLUDE_TOPK_CANDIDATE_FEATURES:-}" ] || \
             [ -n "${LOH_INCLUDE_AVGTOPK_CANDIDATE_FEATURES:-}" ] || \
             [ -n "${LOH_INCLUDE_REQUEST:-}" ] || \
             [ -n "${LOH_DEBUG_LEVEL:-}" ] || \
             [ -n "${LOH_ENABLE_PENALTY:-}" ]; then
            NEED_REBUILD=1
        fi
    fi

    if [ "${NEED_REBUILD}" = "1" ]; then
        echo "[build] 检测到编译相关环境变量，将触发构建"
    fi

    if [ ! -x "_build_dbg/bin/cachesim" ]; then
        if [ "${NEED_REBUILD}" = "1" ]; then
            echo "[build] 未找到 _build_dbg/bin/cachesim，且检测到编译相关环境变量，执行一次增量构建..."
            bash scripts/debug.sh
            if [ $? -ne 0 ]; then
                echo -e "${RED}Build failed. Please fix any compile errors.${NC}"
                exit 1
            fi
            echo "✅ Rebuild completed successfully"
        else
            echo -e "${RED}[build] 未找到 _build_dbg/bin/cachesim。请先手动运行 scripts/debug.sh 构建项目。${NC}"
            exit 1
        fi
    elif [ "${NEED_REBUILD}" = "1" ]; then
        echo "[build] 检测到编译相关环境变量，复用现有 _build_dbg 目录执行一次增量构建..."
        bash scripts/debug.sh
        if [ $? -ne 0 ]; then
            echo -e "${RED}Build failed. Please fix any compile errors.${NC}"
            exit 1
        fi
        echo "✅ Rebuild completed successfully"
    else
        echo "[build] 未设置编译相关环境变量，直接复用已有 _build_dbg/bin/cachesim（不触发构建）"
    fi
) 9>/tmp/libcachesim_build.lock

# 设置Python环境 (stable-baselines3 / gymnasium / torch)
if [ "${LOH_SKIP_PIP_INSTALL:-0}" = "1" ]; then
    echo "[python] LOH_SKIP_PIP_INSTALL=1, skip pip install"
else
    echo "Setting up Python environment..."
    pip install -q stable-baselines3 sb3-contrib gymnasium torch
fi

# 确保权限设置正确
echo "Ensuring proper permissions..."
umask 0  # Set umask to allow full permissions


# 先启动Python脚本，由其主动创建共享内存文件（开启无缓冲输出便于实时观测日志）
PYTHON_LOG_FILE="ac_sb3_${RUN_TIMESTAMP}.log"
export PYTHONUNBUFFERED=1

# Python 脚本不再需要命令行参数，全部通过环境变量配置
# 导出必要的环境变量给 Python 使用
export LOH_MISS_RATIO_WEIGHT="${MISS_RATIO_WEIGHT}"

echo -e "${YELLOW}Starting stable-baselines3 training script... (Log: ${PYTHON_LOG_FILE})${NC}"
echo "Python script: scripts/$PYTHON_SCRIPT"
echo "RL Algorithm: ${LOH_RL_ALGO:-SAC}"
echo "Miss ratio weight: ${LOH_MISS_RATIO_WEIGHT}"
python3 "scripts/$PYTHON_SCRIPT" \
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

echo "Using trace file: $TRACE_FILE (type: $TRACE_TYPE, cache size ratio: $CACHE_SIZE)"

# 默认限制 MetaCDN/TencentCBS 运行请求数，避免误跑全量 trace
if [ -z "${CACHESIM_NUM_REQ:-}" ]; then
    case "${TRACE_FILE}" in
        data/MetaCDN/*)
            export CACHESIM_NUM_REQ=3000000
            echo "[config] CACHESIM_NUM_REQ not set; defaulting to ${CACHESIM_NUM_REQ} for MetaCDN trace"
            ;;
        data/TencentCBS/*)
            export CACHESIM_NUM_REQ=3000000
            echo "[config] CACHESIM_NUM_REQ not set; defaulting to ${CACHESIM_NUM_REQ} for TencentCBS trace"
            ;;
    esac
fi

# 执行缓存模拟器 - 输出到文件以便调试
echo -e "${YELLOW}Running cachesim with the following parameters:${NC}"
echo "  Trace file: $TRACE_FILE"
echo "  Trace type: $TRACE_TYPE"
echo "  Cache size ratio: $CACHE_SIZE"
echo "  Eviction: $EVICTION_ALGO (with SB3 RL)"
if [ -n "${CACHESIM_NUM_REQ:-}" ]; then
    echo "  Num requests: $CACHESIM_NUM_REQ"
else
    echo "  Num requests: ALL"
fi
echo "  Python script: ${PYTHON_SCRIPT:-<unset>}"
echo "  LOH_FIXED_WEIGHTS: ${LOH_FIXED_WEIGHTS:-<unset>}"

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

# 可选：控制 cachesim 的线程数（如果不设置则使用 cachesim 默认值）
if [ -n "${CACHESIM_NUM_THREAD:-}" ]; then
    CACHESIM_CMD+=("--num-thread=${CACHESIM_NUM_THREAD}")
fi

CACHESIM_CMD+=("--eviction-params=$EV_PARAMS")
if [ -n "${CACHESIM_NUM_REQ_ARG:-}" ]; then
    CACHESIM_CMD+=("${CACHESIM_NUM_REQ_ARG}")
fi
# 控制 cachesim 输出冗余度（默认=1，便于和历史日志一致；sweep 时可设为 0 大幅减少日志体积）
CACHESIM_CMD+=("-v" "${CACHESIM_VERBOSE:-1}")

# 打印并执行命令
echo "Executing cachesim command:"
printf ' %q' "${CACHESIM_CMD[@]}"; echo

"${CACHESIM_CMD[@]}" > "${CACHESIM_LOG_FILE}" 2>&1 &
CACHESIM_PID=$!

# 如果 Python 先退出，cachesim 可能卡在等待 ACK；这里做兜底收敛
(
    while ps -p "${CACHESIM_PID}" > /dev/null 2>&1; do
        if [ -n "${PYTHON_PID:-}" ] && ! ps -p "${PYTHON_PID}" > /dev/null 2>&1; then
            echo "[watch] Python exited early; signal cachesim to stop (pid=${CACHESIM_PID})"
            write_terminate_flag || true
            kill -INT "${CACHESIM_PID}" 2>/dev/null || true
            sleep 2
            kill -TERM "${CACHESIM_PID}" 2>/dev/null || true
            sleep 2
            kill -KILL "${CACHESIM_PID}" 2>/dev/null || true
            break
        fi
        sleep 1
    done
) &
WATCH_PID=$!

wait "${CACHESIM_PID}"
CACHESIM_EXIT=$?

if ps -p "${WATCH_PID}" > /dev/null 2>&1; then
    kill "${WATCH_PID}" 2>/dev/null || true
fi

# 检查执行结果
if [ "${CACHESIM_EXIT}" -ne 0 ]; then
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
write_terminate_flag || true

if ps -p $PYTHON_PID > /dev/null 2>&1; then
    for i in $(seq 1 16); do
        if ! ps -p $PYTHON_PID > /dev/null 2>&1; then
            break
        fi
        sleep 0.5
    done
    if ps -p $PYTHON_PID > /dev/null 2>&1; then
        echo "Graceful stop timed out, sending SIGTERM..."
        kill $PYTHON_PID || true
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
