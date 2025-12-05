#!/usr/bin/env bash
set -euo pipefail

# 遍历一批固定权重，调用 loh_constant_weights.py 通过 RL 通路写入权重，
#  在指定 trace 上跑 LOH-mr-blocked。
#
# 需求：
#   - 6 个维度的权重都要尝试；
#   - 先用粗粒度区间；
#   - 最多并行 20 个任务；
#   - 默认先跑 meta trace (data/MetaCDN/meta_reag.oracleGeneral.zst)。
#
# 用法示例：
#   # 使用默认 meta trace + 粗粒度权重 + 最多 20 并行
#   bash scripts/sweep_loh_constant_weights.sh
#
#   # 自定义 trace / cache_ratio / 最大并行数
#   MAX_PARALLEL=16 CACHESIM_NUM_REQ=5000000 \
#     bash scripts/sweep_loh_constant_weights.sh data/MetaCDN/meta_reag.oracleGeneral.zst 0.075

TRACE_PATH=${1:-data/MetaCDN/meta_reag.oracleGeneral.zst}
CACHE_RATIO=${2:-0.1}

# 每个维度的粗粒度取值；如设置环境变量 OVERRIDE_VALUES="0,1" 则改为对应取值
if [ -n "${OVERRIDE_VALUES:-}" ]; then
  IFS=',' read -r -a VALUES <<< "${OVERRIDE_VALUES}"
else
  VALUES=(0 1 2)
fi
MAX_PARALLEL=${MAX_PARALLEL:-20}

# 为了“尽可能多”但又不爆炸：
#   - 6 维，每维取 0/1/2，共 3^6=729 组，排除全 0 剩 728 组；
#   - loh_constant_weights.py 内部会自动归一化到和为 1。

TRACE_BASENAME=$(basename "${TRACE_PATH}")
SHORT_TRACE=${TRACE_BASENAME:0:4}
RUN_TS=$(date +%m%d_%H%M%S)
echo "[sweep_loh_constant_weights] TRACE=${TRACE_PATH} (${TRACE_BASENAME}), RATIO=${CACHE_RATIO}, MAX_PARALLEL=${MAX_PARALLEL}, RUN_TS=${RUN_TS}" >&2

mkdir -p runs/constant_weight

job_count=0

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
            LOG="runs/constant_weight/loh_const_${RUN_TS}_${SHORT_TRACE}_${w1}_${w2}_${w3}_${w4}_${w5}_${w6}.log"
            echo "==============================" >&2
            echo "[sweep_loh_constant_weights] LOH_FIXED_WEIGHTS=${W} -> ${LOG}" >&2

            # 后台启动一个任务：直接调用 Python + cachesim，不经过 test_loh_rl_sb3.sh
            (
              # 生成唯一的 SHM_KEY
              SHM_KEY="$((RANDOM * 1000 + $$))"
              rm -f "/dev/shm/loh_ac_${SHM_KEY}" 2>/dev/null || true

              # 启动 Python 固定权重脚本（设置 EVICTION_ALGO 让 Python 使用正确的状态维度）
              LOH_SHM_KEY="$SHM_KEY" \
              LOH_FIXED_WEIGHTS="$W" \
              EVICTION_ALGO="LOH-mr-blocked" \
              python3 scripts/loh_constant_weights.py &
              PY_PID=$!

              # 等待共享内存文件创建
              for i in $(seq 1 60); do
                [ -f "/dev/shm/loh_ac_${SHM_KEY}" ] && break
                sleep 1
              done

              if [ ! -f "/dev/shm/loh_ac_${SHM_KEY}" ]; then
                echo "ERROR: SHM not created" >&2
                kill $PY_PID 2>/dev/null || true
                exit 1
              fi

              # 运行 cachesim
              LOH_SHM_KEY="$SHM_KEY" \
              _build_dbg/bin/cachesim "${TRACE_PATH}" oracleGeneral LOH-mr-blocked "${CACHE_RATIO}" \
                --num-req="${CACHESIM_NUM_REQ:-3000000}" -v 1

              # 停止 Python
              kill $PY_PID 2>/dev/null || true
              rm -f "/dev/shm/loh_ac_${SHM_KEY}" 2>/dev/null || true
            ) >"${LOG}" 2>&1 &

            job_count=$((job_count + 1))
            # 控制并行度
            if (( job_count % MAX_PARALLEL == 0 )); then
              wait
            fi
          done
        done
      done
    done
  done
done

wait
echo "[sweep_loh_constant_weights] 所有权重 sweep 结束，总任务数=${job_count}" >&2
