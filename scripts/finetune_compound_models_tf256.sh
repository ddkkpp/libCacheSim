#!/bin/bash
set -euo pipefail

# 使用 compound 模型对各自 trace 在线微调（SAC_TRAIN_FREQ=256）
# - 仅当 LOH_RESUME_PATH 指定时才会 resume（loh_actor_critic_sb3.py 已强制 path-required）
# - 默认请求数：对 MetaCDN/TencentCBS trace，test_loh_rl_sb3.sh 会默认 3M；这里显式固定为 3M 避免误跑

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

CACHE_SIZE="${1:-0.1}"
NUM_REQ="${CACHESIM_NUM_REQ:-3000000}"
RUN_SUFFIX="${RUN_SUFFIX:-}"

META_TRACE="data/MetaCDN/meta_reag.oracleGeneral.zst"
T1063_TRACE="data/TencentCBS/1063.oracleGeneral.zst"

META_MODEL="./runs/0203_3m_meta_cpd/sac_loh_interrupted.zip"
T1063_MODEL="./runs/0203_3m_1063_cpd/sac_loh_interrupted.zip"

if [ ! -f "$META_MODEL" ]; then
  echo "error: meta model not found: $META_MODEL" >&2
  exit 1
fi
if [ ! -f "$T1063_MODEL" ]; then
  echo "error: 1063 model not found: $T1063_MODEL" >&2
  exit 1
fi

common_env=(
  "LOH_RL_ALGO=SAC"
  "SAC_TRAIN_FREQ=256"
  "CACHESIM_NUM_REQ=${NUM_REQ}"
  "LOH_SCORE_USE_COMPOUND=1"
  "LOH_SCORE_USE_IRT=0"
  "LOH_CHECKPOINT_FREQ=${LOH_CHECKPOINT_FREQ:-50000}"
  "LOH_SKIP_PIP_INSTALL=${LOH_SKIP_PIP_INSTALL:-1}"
)

run_one() {
  local run_id="$1"
  local trace="$2"
  local model="$3"
  local run_id_full="${run_id}${RUN_SUFFIX}"

  echo ""
  echo "=== finetune: ${run_id_full} ==="
  echo "trace: ${trace}"
  echo "model: ${model}"
  echo "cache_size: ${CACHE_SIZE}"
  echo "num_req: ${NUM_REQ}"
  echo "SAC_ENT_COEF: ${SAC_ENT_COEF:-<unset>}"
  echo "SAC_TARGET_ENTROPY: ${SAC_TARGET_ENTROPY:-<unset>}"
  echo "LOH_USE_SOFTMAX: ${LOH_USE_SOFTMAX:-<unset>}"

  env \
    RUN_TIMESTAMP="$run_id_full" \
    LOH_RESUME_PATH="$model" \
    "${common_env[@]}" \
    bash scripts/test_loh_rl_sb3.sh "$trace" "$CACHE_SIZE"
}

# 1) meta model -> meta trace
run_one "0203_ft_meta_cpd_on_meta_tf256" "$META_TRACE" "$META_MODEL"

# 2) 1063 model -> 1063 trace
run_one "0203_ft_1063_cpd_on_1063_tf256" "$T1063_TRACE" "$T1063_MODEL"
