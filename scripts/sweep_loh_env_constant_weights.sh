#!/usr/bin/env bash
set -euo pipefail

# 纯 C 端 sweep：通过环境变量 LOH_ENABLE_RL=0 + LOH_FIXED_WEIGHTS
#  直接运行 cachesim(LOH-mr-blocked)，不再依赖 Python / 共享内存。
#
# 用法示例：
#   bash scripts/sweep_loh_env_constant_weights.sh \
#       data/MetaCDN/meta_reag.oracleGeneral.zst 0.1
#
# 可选环境变量：
#   OVERRIDE_VALUES   用逗号指定离散取值集合，默认 0,1,2
#   CACHESIM_NUM_REQ  限制请求数，默认 3000000
#   OUT_DIR           输出目录，默认 runs/constant_weight_env

TRACE_PATH=${1:-data/MetaCDN/meta_reag.oracleGeneral.zst}
CACHE_RATIO=${2:-0.1}

if [ -n "${OVERRIDE_VALUES:-}" ]; then
  IFS=',' read -r -a VALUES <<< "${OVERRIDE_VALUES}"
else
  VALUES=(0 1 2)
fi

CACHESIM_NUM_REQ=${CACHESIM_NUM_REQ:-3000000}
OUT_DIR=${OUT_DIR:-runs/constant_weight_env}

TRACE_BASENAME=$(basename "${TRACE_PATH}")
SHORT_TRACE=${TRACE_BASENAME:0:4}
RUN_TS=$(date +%m%d_%H%M%S)

mkdir -p "${OUT_DIR}"

echo "[sweep_loh_env] TRACE=${TRACE_PATH} (${TRACE_BASENAME}), RATIO=${CACHE_RATIO}, NUM_REQ=${CACHESIM_NUM_REQ}" >&2

job_id=0

for w1 in "${VALUES[@]}"; do
  for w2 in "${VALUES[@]}"; do
    for w3 in "${VALUES[@]}"; do
      for w4 in "${VALUES[@]}"; do
        for w5 in "${VALUES[@]}"; do
          for w6 in "${VALUES[@]}"; do
            if [[ "$w1" == 0 && "$w2" == 0 && "$w3" == 0 && "$w4" == 0 && "$w5" == 0 && "$w6" == 0 ]]; then
              continue
            fi
            W="${w1},${w2},${w3},${w4},${w5},${w6}"
            LOG="${OUT_DIR}/loh_env_${RUN_TS}_${SHORT_TRACE}_${w1}_${w2}_${w3}_${w4}_${w5}_${w6}.log"
            echo "[sweep_loh_env] LOH_FIXED_WEIGHTS=${W} -> ${LOG}" >&2

            LOH_ENABLE_RL=0 \
            LOH_FIXED_WEIGHTS="${W}" \
              _build_dbg/bin/cachesim "${TRACE_PATH}" oracleGeneral LOH-mr-blocked "${CACHE_RATIO}" \
                --num-req="${CACHESIM_NUM_REQ}" -v 1 >"${LOG}" 2>&1

            job_id=$((job_id + 1))
          done
        done
      done
    done
  done
done

echo "[sweep_loh_env] 所有权重 sweep 完成，总组合数=${job_id}" >&2
