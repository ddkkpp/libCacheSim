#!/usr/bin/env bash
set -euo pipefail

# 基于 constant_sweep.csv 的前若干个最优解，在其附近做更细粒度的局部搜索。
# 使用 loh_constant_weights.py 通过 RL 通路写入权重，并调用 
# 在指定 trace 上跑 LOH-mr-blocked。
#
# 用法示例：
#   # 默认：使用 constant_sweep.csv 前 10 个解，在其归一化方向附近做细粒度浮点扰动
#   bash scripts/sweep_loh_constant_weights_refine.sh
#
#   # 自定义 trace / cache_ratio / N / 并行度
#   MAX_PARALLEL=16 TOP_N=20 CACHESIM_NUM_REQ=5000000 \
#     bash scripts/sweep_loh_constant_weights_refine.sh data/MetaCDN/meta_reag.oracleGeneral.zst 0.075
#
# 注意：
#   - 仍然使用 6 维权重，但不再局限于 0/1/2 整数，而是在 best 方向附近做小扰动；
#   - 具体扰动策略由 Python 脚本 scripts/loh_constant_weights_refine.py 决定。

TRACE_PATH=${1:-data/MetaCDN/meta_reag.oracleGeneral.zst}
CACHE_RATIO=${2:-0.1}
TOP_N=${TOP_N:-10}
MAX_PARALLEL=${MAX_PARALLEL:-20}

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
CSV_PATH="${ROOT_DIR}/constant_sweep.csv"
if [ ! -f "${CSV_PATH}" ]; then
  echo "[sweep_loh_constant_weights_refine] constant_sweep.csv 不存在: ${CSV_PATH}" >&2
  echo "请先运行: python3 scripts/analyze_loh_constant_sweep.py > constant_sweep.csv" >&2
  exit 1
fi

TRACE_BASENAME=$(basename "${TRACE_PATH}")
SHORT_TRACE=${TRACE_BASENAME:0:4}
RUN_TS=$(date +%m%d_%H%M%S)
OUT_DIR="${ROOT_DIR}/runs/constant_weight_refine"
mkdir -p "${OUT_DIR}"

echo "[sweep_loh_constant_weights_refine] TRACE=${TRACE_PATH} (${TRACE_BASENAME}), RATIO=${CACHE_RATIO}, TOP_N=${TOP_N}, MAX_PARALLEL=${MAX_PARALLEL}, RUN_TS=${RUN_TS}" >&2

job_count=0

# 由 Python 侧负责根据 constant_sweep.csv 读取前 TOP_N 个解并生成一系列候选权重；
# 这里逐行读取 Python 输出的候选权重列表，每行 6 个浮点数，用逗号分隔。

python3 "${ROOT_DIR}/scripts/loh_constant_weights_refine.py" "${CSV_PATH}" "${TOP_N}" "${RUN_TS}" "${SHORT_TRACE}" "${OUT_DIR}" |
while IFS= read -r line; do
  # 跳过空行或注释
  [[ -z "${line}" ]] && continue
  [[ "${line}" =~ ^# ]] && continue

  # line 形如: id<wid>,w1,w2,w3,w4,w5,w6
  IFS=',' read -r wid w1 w2 w3 w4 w5 w6 <<< "${line}"
  W="${w1},${w2},${w3},${w4},${w5},${w6}"
  LOG="${OUT_DIR}/loh_const_refine_${RUN_TS}_${SHORT_TRACE}_${wid}.log"

  echo "[sweep_loh_constant_weights_refine] wid=${wid} W=${W} -> ${LOG}" >&2

  (
    LOH_PARALLEL_SAFE=1 \
    LOH_FIXED_WEIGHTS="${W}" \
    PYTHON_SCRIPT=loh_constant_weights.py \
    EVICTION_ALGO=LOH-mr-blocked \
    bash "${ROOT_DIR}/scripts/test_loh_rl_sb3.sh" "${TRACE_PATH}" "${CACHE_RATIO}" \
    >"${LOG}" 2>&1
  ) &

  job_count=$((job_count + 1))
  if (( job_count % MAX_PARALLEL == 0 )); then
    wait
  fi

done

wait
echo "[sweep_loh_constant_weights_refine] 所有 refine 任务结束，总任务数=${job_count}" >&2
