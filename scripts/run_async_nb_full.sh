#!/usr/bin/env bash
# 最优配置 + 异步训练 (LOH_ASYNC_TRAIN=1) 全量三 trace 测试
# 配置与 nb_500 (§15.1) 相同，仅多设 LOH_ASYNC_TRAIN=1
set -euo pipefail

cd "$(dirname "$0")/.."

TAG="${1:-async_nb_full_$(date +%m%d_%H%M%S)}"
LOG_DIR="tmp/${TAG}"
mkdir -p "$LOG_DIR"

# ── 公共环境 ──
export LOH_WAIT_MODE=nonblocked
export LOH_ASYNC_TRAIN=1              # ← 与 nb_500 唯一差异
export LOH_ENABLE_SEMAPHORE=1
export LOH_SCORE_USE_COMPOUND=1
export LOH_SCORE_USE_IRT=0
export LOH_RANDOM_CANDIDATES=64
export LOH_BUILD_RELEASE=1
export LOH_SKIP_BUILD=1
export LOH_SKIP_PIP_INSTALL=1
export CACHESIM_NUM_REQ=ALL

# 三条 trace 配置 (trace path, cache ratio, log1p setting)
# LOG1P 已从 0306 基线和 NB36 复现中确认正确值
TRACES=(
  "data/TencentCBS/1063.oracleGeneral.zst 0.1 1"
  "data/WikiCDN/wiki_2019t.oracleGeneral.zst      0.1 0"
  "data/MetaCDN/meta_reag.oracleGeneral.zst       0.1 1"
)
NAMES=("1063" "wiki" "meta")

echo "=== Async NonBlocked Full-Trace Test ==="
echo "  TAG=$TAG  LOG_DIR=$LOG_DIR"
echo "  LOH_WAIT_MODE=$LOH_WAIT_MODE  LOH_ASYNC_TRAIN=$LOH_ASYNC_TRAIN"
echo "  LOH_SCORE_USE_COMPOUND=$LOH_SCORE_USE_COMPOUND  LOH_SCORE_USE_IRT=$LOH_SCORE_USE_IRT"
echo "  LOH_RANDOM_CANDIDATES=$LOH_RANDOM_CANDIDATES"
echo ""

for i in "${!TRACES[@]}"; do
  read -r TPATH CRATIO LOG1P_VAL <<< "${TRACES[$i]}"
  NAME="${NAMES[$i]}"

  # 显式设置特征模式（不依赖 auto-detect）
  export LOH_FEATURE_LOG1P="$LOG1P_VAL"
  if [[ "$LOG1P_VAL" == "1" ]]; then
    export LOH_FEATURE_LOG1P_RECIPROCAL=0
  else
    export LOH_FEATURE_LOG1P_RECIPROCAL=1
  fi
  # 不设置 _LOH_DETECT_APPLIED：让 test script 走"用户显式设置"路径跳过 detect
  unset _LOH_DETECT_APPLIED 2>/dev/null || true

  echo "──────────────────────────────────────"
  echo "[${NAME}] trace=$TPATH  cache_ratio=$CRATIO"
  echo "[${NAME}] start: $(date '+%Y-%m-%d %H:%M:%S')"

  LOG_FILE="$LOG_DIR/${NAME}.log"
  bash scripts/test_loh_rl_sb3.sh "$TPATH" "$CRATIO" > "$LOG_FILE" 2>&1 || {
    echo "[${NAME}] FAILED (rc=$?), see $LOG_FILE"
    continue
  }

  # 提取结果
  MR_LINE=$(grep -E "miss ratio [0-9]" "$LOG_FILE" | tail -1 || true)
  echo "[${NAME}] done: $(date '+%Y-%m-%d %H:%M:%S')"
  echo "[${NAME}] result: $MR_LINE"
  echo ""
done

echo "=== All done. Logs in $LOG_DIR ==="
