#!/bin/bash
# =====================================================================
# LOH Auto-Detect Script
# =====================================================================
# 独立于 LOH 仿真的特征模式检测脚本。
# 运行一次短暂的 cachesim 仿真（默认 500K 请求），分析 trace 的频率/大小/
# recency 分布，输出最优的 LOH 配置（LOG1P vs LOG1P_RECIPROCAL、COMPOUND 等）。
#
# 用法:
#   bash scripts/loh_detect.sh <trace_file> [cache_size_ratio] [detect_reqs]
#
# 输出:
#   stdout: shell export 语句（可直接 eval）
#   stderr: 检测过程的详细日志
#
# 示例:
#   # 直接使用
#   eval "$(bash scripts/loh_detect.sh data/MetaCDN/meta_reag.oracleGeneral.zst 0.1)"
#   echo "LOG1P=$LOH_FEATURE_LOG1P, COMPOUND=$LOH_SCORE_USE_COMPOUND"
#
#   # 在 RL 脚本中使用
#   source <(bash scripts/loh_detect.sh "$TRACE_FILE" "$CACHE_SIZE")
# =====================================================================

set -euo pipefail

# --- 参数解析 ---
TRACE_FILE="${1:?Usage: $0 <trace_file> [cache_size_ratio] [detect_reqs]}"
CACHE_SIZE="${2:-0.1}"
DETECT_REQS="${3:-300000}"

# --- 选择 cachesim 二进制（优先 release build） ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

if [ -x "_build_rel/bin/cachesim" ]; then
    CACHESIM="_build_rel/bin/cachesim"
elif [ -x "_build_dbg/bin/cachesim" ]; then
    CACHESIM="_build_dbg/bin/cachesim"
else
    echo "Error: No cachesim binary found. Run 'bash scripts/debug.sh -c' first." >&2
    exit 1
fi

# --- 确定 trace 类型 ---
if [[ "$TRACE_FILE" == *.csv ]]; then
    TRACE_TYPE="csv"
else
    TRACE_TYPE="oracleGeneral"
fi

# --- 验证文件 ---
if [ ! -f "$TRACE_FILE" ]; then
    echo "Error: Trace file '$TRACE_FILE' not found." >&2
    exit 1
fi

echo "[loh_detect] Analyzing trace: $TRACE_FILE" >&2
echo "[loh_detect] Cache size ratio: $CACHE_SIZE, detect requests: $DETECT_REQS" >&2
echo "[loh_detect] Using: $CACHESIM" >&2

# --- 运行短暂的 cachesim 以触发 auto-detect ---
# LOH_ENABLE_RL=0: 不需要 RL 端
# LOH_AUTO_FEATURE_MODE=1: 启用自动检测
# LOH_AUTO_DETECT_REQS=100000: 提前触发检测（100K 请求后）
# LOH_DEBUG_LEVEL=0: 最少调试输出
DETECT_OUTPUT=$(LOH_ENABLE_RL=0 \
    LOH_AUTO_FEATURE_MODE=1 \
    LOH_AUTO_DETECT_REQS=100000 \
    LOH_DEBUG_LEVEL=0 \
    "$CACHESIM" "$TRACE_FILE" "$TRACE_TYPE" loh "$CACHE_SIZE" \
    --num-req "$DETECT_REQS" 2>&1) || {
    echo "Error: cachesim detection run failed." >&2
    echo "$DETECT_OUTPUT" >&2
    exit 1
}

# --- 解析 auto-detect 输出 ---
# 打印检测日志到 stderr
echo "$DETECT_OUTPUT" | grep -E "^\[LOH AUTO-DETECT\]|\[LOH FEATURE" >&2 || true

# 提取决策
DECISION=$(echo "$DETECT_OUTPUT" | grep -o "DECISION: [A-Z0-9_]* mode" | head -1 || true)

if echo "$DECISION" | grep -q "LOG1P_RECIPROCAL"; then
    FEAT_LOG1P=0
    FEAT_RECIPROCAL=1
    MODE_NAME="LOG1P_RECIPROCAL"
elif echo "$DECISION" | grep -q "LOG1P"; then
    FEAT_LOG1P=1
    FEAT_RECIPROCAL=0
    MODE_NAME="LOG1P"
else
    echo "[loh_detect] WARNING: Could not parse feature mode from output, defaulting to LOG1P" >&2
    FEAT_LOG1P=1
    FEAT_RECIPROCAL=0
    MODE_NAME="LOG1P (default)"
fi

# 提取 composite score（允许匹配失败）
SCORE=""
CV=""
ONE_HIT=""
MEAN_FREQ=""
MISS_RATIO=""

# 使用 set +e 避免 grep 无匹配时退出
set +e
SCORE=$(echo "$DETECT_OUTPUT" | grep -oP "SCORE = .* = \K[-0-9.]+" | head -1)
CV=$(echo "$DETECT_OUTPUT" | grep -oP "cv=\K[0-9.]+" | head -1)
ONE_HIT=$(echo "$DETECT_OUTPUT" | grep -oP "one_hit=\K[0-9.]+" | head -1)
MEAN_FREQ=$(echo "$DETECT_OUTPUT" | grep -oP "mean_freq=\K[0-9.]+" | head -1)
MISS_RATIO=$(echo "$DETECT_OUTPUT" | grep -oP "miss ratio \K[0-9.]+" | head -1)
set -e

# --- 输出结果 ---
echo "[loh_detect] ===== Detection Result =====" >&2
echo "[loh_detect] Feature mode: $MODE_NAME (score=${SCORE:-N/A})" >&2
echo "[loh_detect] Stats: cv=${CV:-N/A}, one_hit=${ONE_HIT:-N/A}, mean_freq=${MEAN_FREQ:-N/A}" >&2
echo "[loh_detect] Ref miss ratio (${DETECT_REQS} reqs): ${MISS_RATIO:-N/A}" >&2
echo "[loh_detect] =============================" >&2

# 输出 shell export 语句到 stdout（可被 eval 或 source 使用）
cat <<EOF
# LOH Auto-Detect Results
# Trace: $TRACE_FILE
# Score: ${SCORE:-N/A} → $MODE_NAME
# Stats: cv=${CV:-N/A}, one_hit=${ONE_HIT:-N/A}, mean_freq=${MEAN_FREQ:-N/A}
export LOH_FEATURE_LOG1P=$FEAT_LOG1P
export LOH_FEATURE_LOG1P_RECIPROCAL=$FEAT_RECIPROCAL
export LOH_SCORE_USE_COMPOUND=1
export LOH_SCORE_USE_IRT=0
export LOH_RANDOM_CANDIDATES=${LOH_RANDOM_CANDIDATES:-96}
# 禁用仿真内的 auto-detect（已在此脚本完成检测）
export LOH_AUTO_FEATURE_MODE=0
EOF
