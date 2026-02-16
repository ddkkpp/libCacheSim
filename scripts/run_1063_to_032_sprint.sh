#!/usr/bin/env bash
# 1063 冲刺脚本：用分阶段 sweep 方式尽可能把 miss_ratio 拉向目标（默认 0.32）。
#
# 设计要点：
# - 固定 1063 + 3Mreq + cache_ratio=0.1（可通过环境变量覆盖）
# - 从当前已知最强起点出发（best state + best scoring）
# - 分三阶段逐步扩展搜索空间；每阶段结束后自动汇总 best
# - 若达到 TARGET_MR 则提前停止

set -euo pipefail

TRACE_FILE=${TRACE_FILE:-"data/TencentCBS/1063.oracleGeneral.zst"}
CACHE_RATIO=${CACHE_RATIO:-0.1}
CACHESIM_NUM_REQ=${CACHESIM_NUM_REQ:-3000000}
TARGET_MR=${TARGET_MR:-0.32}

SWEEP_REPEATS=${SWEEP_REPEATS:-1}
SEED_BASE=${SEED_BASE:-0}
DRY_RUN=${DRY_RUN:-0}

TS=${TS:-"1063_to032_$(date +%Y%m%d_%H%M%S)"}
OUT_ROOT=${OUT_ROOT:-"sweeps/${TS}"}
mkdir -p "${OUT_ROOT}"

log() { echo "[$(date +%H:%M:%S)] $*"; }

if [[ ! -f "${TRACE_FILE}" ]]; then
  echo "Error: trace not found: ${TRACE_FILE}" >&2
  exit 1
fi

# 当前最强起点（来自最近的 state + penalty 汇总）
# best scoring: compound=0, irt=0, softmax=0, signs=0
# best state layout: hm=1 cache=1 cand=0 topk=0 avgtopk=0 req=1, RL_STATE_USE_MISSRATIO=1
BASE_COMMON="LOH_PARALLEL_SAFE=1 LOH_SKIP_PIP_INSTALL=1 LOH_SKIP_BUILD=1 CACHESIM_VERBOSE=0"
BASE_COMMON+=" CACHESIM_NUM_REQ=${CACHESIM_NUM_REQ}"
BASE_COMMON+=" LOH_SCORE_USE_COMPOUND=0 LOH_SCORE_USE_IRT=0 LOH_USE_SOFTMAX=0 LOH_USE_HEURISTIC_SIGNS=0"
BASE_COMMON+=" LOH_INCLUDE_HIT_MISS_FEATURES=1 LOH_INCLUDE_CACHE_FEATURES=1 LOH_INCLUDE_CANDIDATE_FEATURES=0"
BASE_COMMON+=" LOH_INCLUDE_TOPK_CANDIDATE_FEATURES=0 LOH_INCLUDE_AVGTOPK_CANDIDATE_FEATURES=0 LOH_INCLUDE_REQUEST=1"
BASE_COMMON+=" RL_STATE_USE_MISSRATIO=1"

COMMON_NO_PEN="${BASE_COMMON} LOH_ENABLE_PENALTY=1 LOH_REWARD_USE_PENALTY=0"
COMMON_PEN="${BASE_COMMON} LOH_ENABLE_PENALTY=1 LOH_REWARD_USE_PENALTY=1"

# 统一 penalty 次级参数默认值（可在个别配置行覆盖）
PEN_SECONDARY="LOH_PENALTY_CUTOFF=0 LOH_PENALTY_DMAX=400000 LOH_PENALTY_EMPTY_AS_GOOD=1 LOH_PENALTY_REFINE_ON_LATE=1"
PEN_SECONDARY+=" LOH_PENALTY_NO_EVICT_REWARD=keep LOH_PENALTY_BASELINE_DECAY=0.99"
PEN_SECONDARY+=" LOH_SURVIVAL_BINS=64 LOH_SURVIVAL_QUANTILE=0.99 LOH_SURVIVAL_MINCOUNT=1000"
PEN_SECONDARY+=" LOH_PENALTY_NET_GOOD_SCALE=1.0 LOH_PENALTY_NET_PENALTY_SCALE=1.0"

write_stage1_configs() {
  local f=$1
  {
    echo "# Stage1: 先吃掉低风险收益（已知有效 penalty 主组合 + 小范围邻域）"
    echo "${COMMON_NO_PEN} LOH_RL_ALGO=SAC LOH_ACTION_SCALE=1.0"
    echo "${COMMON_PEN} LOH_RL_ALGO=SAC LOH_ACTION_SCALE=1.0 LOH_PENALTY_SCALE=log LOH_PENALTY_REWARD_FORMULA=neg LOH_REWARD_W_PENALTY=0.1 ${PEN_SECONDARY}"
    echo "${COMMON_PEN} LOH_RL_ALGO=SAC LOH_ACTION_SCALE=1.0 LOH_PENALTY_SCALE=reciprocal LOH_PENALTY_REWARD_FORMULA=relative LOH_REWARD_W_PENALTY=0.2 ${PEN_SECONDARY}"
    echo "${COMMON_PEN} LOH_RL_ALGO=SAC LOH_ACTION_SCALE=1.0 LOH_PENALTY_SCALE=log LOH_PENALTY_REWARD_FORMULA=net2 LOH_REWARD_W_PENALTY=3.0 ${PEN_SECONDARY}"
    echo "${COMMON_PEN} LOH_RL_ALGO=SAC LOH_ACTION_SCALE=1.0 LOH_PENALTY_SCALE=log LOH_PENALTY_REWARD_FORMULA=centered LOH_REWARD_W_PENALTY=1.0 ${PEN_SECONDARY}"

    for w in 0.05 0.1 0.15 0.2 0.3; do
      echo "${COMMON_PEN} LOH_RL_ALGO=SAC LOH_ACTION_SCALE=1.0 LOH_PENALTY_SCALE=log LOH_PENALTY_REWARD_FORMULA=neg LOH_REWARD_W_PENALTY=${w} ${PEN_SECONDARY}"
    done
    for w in 0.1 0.2 0.3 0.5; do
      echo "${COMMON_PEN} LOH_RL_ALGO=SAC LOH_ACTION_SCALE=1.0 LOH_PENALTY_SCALE=reciprocal LOH_PENALTY_REWARD_FORMULA=relative LOH_REWARD_W_PENALTY=${w} ${PEN_SECONDARY}"
    done
  } > "${f}"
}

write_stage2_configs() {
  local f=$1
  {
    echo "# Stage2: 放开 scoring 形态（保持与当前编译布局一致，避免 C/Python 结构错位）"
    for soft in 0 1; do
      for signs in 0 1; do
        echo "${COMMON_NO_PEN} LOH_RL_ALGO=SAC LOH_ACTION_SCALE=1.0 LOH_USE_SOFTMAX=${soft} LOH_USE_HEURISTIC_SIGNS=${signs}"
        echo "${COMMON_PEN} LOH_RL_ALGO=SAC LOH_ACTION_SCALE=1.0 LOH_USE_SOFTMAX=${soft} LOH_USE_HEURISTIC_SIGNS=${signs} LOH_PENALTY_SCALE=log LOH_PENALTY_REWARD_FORMULA=neg LOH_REWARD_W_PENALTY=0.1 ${PEN_SECONDARY}"
      done
    done

    echo "${COMMON_NO_PEN} LOH_RL_ALGO=SAC LOH_ACTION_SCALE=1.0 LOH_SCORE_USE_COMPOUND=1 LOH_SCORE_USE_IRT=1 LOH_USE_SOFTMAX=1 LOH_USE_HEURISTIC_SIGNS=0"
    echo "${COMMON_PEN} LOH_RL_ALGO=SAC LOH_ACTION_SCALE=1.0 LOH_SCORE_USE_COMPOUND=1 LOH_SCORE_USE_IRT=1 LOH_USE_SOFTMAX=1 LOH_USE_HEURISTIC_SIGNS=0 LOH_PENALTY_SCALE=log LOH_PENALTY_REWARD_FORMULA=net2 LOH_REWARD_W_PENALTY=2.0 ${PEN_SECONDARY}"
    echo "${COMMON_NO_PEN} LOH_RL_ALGO=SAC LOH_ACTION_SCALE=1.0 RL_STATE_USE_MISSRATIO=0"
  } > "${f}"
}

write_stage3_configs() {
  local f=$1
  {
    echo "# Stage3: 强化训练侧超参（算法/更新频率/动作幅度）"
    for algo in SAC TD3 PPO A2C; do
      for upd in 50 100 200 400; do
        for act in 0.6 0.8 1.0 1.2; do
          echo "${COMMON_NO_PEN} LOH_RL_ALGO=${algo} RL_UPDATE_INTERVAL=${upd} LOH_ACTION_SCALE=${act}"
          echo "${COMMON_PEN} LOH_RL_ALGO=${algo} RL_UPDATE_INTERVAL=${upd} LOH_ACTION_SCALE=${act} LOH_PENALTY_SCALE=log LOH_PENALTY_REWARD_FORMULA=neg LOH_REWARD_W_PENALTY=0.1 ${PEN_SECONDARY}"
        done
      done
    done
  } > "${f}"
}

summarize_stage_best() {
  local stage_name=$1
  local results_csv=$2
  local out_csv=$3

  /bin/python3 - <<'PY' "${stage_name}" "${results_csv}" "${out_csv}"
import csv, sys
stage, src, out = sys.argv[1:4]

rows=[]
with open(src, newline='') as f:
    r=csv.DictReader(f)
    for row in r:
        if str(row.get('exit_code','')).strip() != '0':
            continue
        try:
            mr=float(row.get('miss_ratio',''))
        except Exception:
            continue
        rows.append((mr,row))

rows.sort(key=lambda x:x[0])
best = rows[0] if rows else None

with open(out, 'w', newline='') as f:
    w=csv.writer(f)
    w.writerow(['stage','best_miss_ratio','run_timestamp','config'])
    if best:
        w.writerow([stage, f"{best[0]:.6f}", best[1].get('run_timestamp',''), best[1].get('config','')])

print('stage', stage, 'best_mr', (f"{best[0]:.6f}" if best else 'NA'))
PY
}

run_stage() {
  local stage_name=$1
  local cfg_file=$2
  local out_dir=$3

  mkdir -p "${out_dir}"

  local n_cfg
  n_cfg=$(grep -vE '^[[:space:]]*(#|$)' "${cfg_file}" | wc -l)
  log "[${stage_name}] configs=${n_cfg} out=${out_dir}"

  if [[ "${DRY_RUN}" == "1" ]]; then
    log "[${stage_name}] DRY_RUN=1, skip execution"
    return 0
  fi

  SWEEP_ID="${TS}__${stage_name}" \
  SWEEP_OUTDIR="${out_dir}" \
  SWEEP_REPEATS="${SWEEP_REPEATS}" \
  SEED_BASE="${SEED_BASE}" \
  SWEEP_RESUME=1 \
  bash scripts/sweep_loh_rl_sb3.sh "${cfg_file}" "${TRACE_FILE}" "${CACHE_RATIO}" >/dev/null

  summarize_stage_best "${stage_name}" "${out_dir}/results.csv" "${out_dir}/best.csv"
}

extract_best_mr() {
  local f=$1
  /bin/python3 - <<'PY' "${f}"
import csv, sys
p=sys.argv[1]
try:
    with open(p, newline='') as fp:
        r=csv.DictReader(fp)
        row=next(r, None)
        if row and row.get('best_miss_ratio'):
            print(row['best_miss_ratio'])
        else:
            print('NA')
except Exception:
    print('NA')
PY
}

reached_target() {
  local mr=$1
  /bin/python3 - <<'PY' "${mr}" "${TARGET_MR}"
import sys
mr=sys.argv[1]
target=float(sys.argv[2])
try:
    v=float(mr)
except Exception:
    print('0')
    raise SystemExit(0)
print('1' if v <= target else '0')
PY
}

log "target_mr=${TARGET_MR}"
log "trace=${TRACE_FILE} cache_ratio=${CACHE_RATIO} num_req=${CACHESIM_NUM_REQ}"
log "out_root=${OUT_ROOT}"

# 关键：先按本次固定 state layout 编译，确保 C 与 Python 的 shared-memory 结构一致。
log "[build] compile cachesim with fixed base state layout"
export LOH_INCLUDE_HIT_MISS_FEATURES=1
export LOH_INCLUDE_CACHE_FEATURES=1
export LOH_INCLUDE_CANDIDATE_FEATURES=0
export LOH_INCLUDE_TOPK_CANDIDATE_FEATURES=0
export LOH_INCLUDE_AVGTOPK_CANDIDATE_FEATURES=0
export LOH_INCLUDE_REQUEST=1
export LOH_ENABLE_PENALTY=1
bash scripts/debug.sh -c >/dev/null

stage1_cfg="${OUT_ROOT}/stage1_configs.txt"
stage2_cfg="${OUT_ROOT}/stage2_configs.txt"
stage3_cfg="${OUT_ROOT}/stage3_configs.txt"

write_stage1_configs "${stage1_cfg}"
write_stage2_configs "${stage2_cfg}"
write_stage3_configs "${stage3_cfg}"

run_stage "stage1" "${stage1_cfg}" "${OUT_ROOT}/stage1"
if [[ "${DRY_RUN}" != "1" ]]; then
  mr=$(extract_best_mr "${OUT_ROOT}/stage1/best.csv")
  log "[stage1] best_mr=${mr}"
  if [[ "$(reached_target "${mr}")" == "1" ]]; then
    log "[done] reached target at stage1"
    exit 0
  fi
fi

run_stage "stage2" "${stage2_cfg}" "${OUT_ROOT}/stage2"
if [[ "${DRY_RUN}" != "1" ]]; then
  mr=$(extract_best_mr "${OUT_ROOT}/stage2/best.csv")
  log "[stage2] best_mr=${mr}"
  if [[ "$(reached_target "${mr}")" == "1" ]]; then
    log "[done] reached target at stage2"
    exit 0
  fi
fi

run_stage "stage3" "${stage3_cfg}" "${OUT_ROOT}/stage3"

if [[ "${DRY_RUN}" == "1" ]]; then
  log "[done] dry-run complete"
  exit 0
fi

# 汇总三阶段 best
/bin/python3 - <<'PY' "${OUT_ROOT}"
import csv, os, sys
root=sys.argv[1]
out=os.path.join(root,'final_best_summary.csv')
rows=[]
for st in ('stage1','stage2','stage3'):
    p=os.path.join(root,st,'best.csv')
    if not os.path.isfile(p):
        continue
    with open(p, newline='') as f:
        r=csv.DictReader(f)
        row=next(r,None)
        if row:
            rows.append(row)

rows_sorted=[]
for row in rows:
    try:
        v=float(row.get('best_miss_ratio','nan'))
    except Exception:
        v=float('inf')
    rows_sorted.append((v,row))
rows_sorted.sort(key=lambda x:x[0])

with open(out,'w',newline='') as f:
    w=csv.DictWriter(f, fieldnames=['stage','best_miss_ratio','run_timestamp','config'])
    w.writeheader()
    for _,row in rows_sorted:
      w.writerow(row)

print('Wrote:', out)
if rows_sorted:
    best=rows_sorted[0][1]
    print('global_best_stage', best.get('stage',''))
    print('global_best_mr', best.get('best_miss_ratio',''))
PY

log "[done] outputs: ${OUT_ROOT}"
log "[done] stage bests: ${OUT_ROOT}/stage*/best.csv"
log "[done] final summary: ${OUT_ROOT}/final_best_summary.csv"
