#!/usr/bin/env bash
# 第二步（单 seed）策略形态升级：
# - 不做多 seed（固定 SWEEP_REPEATS=1）
# - 引入更强 scoring 分支（compound/IRT 组合）
# - 拉长训练窗口（不只看 3M）

set -euo pipefail

TRACE_FILE=${TRACE_FILE:-"data/TencentCBS/1063.oracleGeneral.zst"}
CACHE_RATIO=${CACHE_RATIO:-0.1}
TARGET_MR=${TARGET_MR:-0.32}
DRY_RUN=${DRY_RUN:-0}

# 单 seed 固定
SWEEP_REPEATS=1
SEED_BASE=${SEED_BASE:-0}

# 训练窗口（可覆盖）
NUM_REQ_LIST=${NUM_REQ_LIST:-"3000000 5000000 8000000"}

TS=${TS:-"1063_stage2_upgrade_single_seed_$(date +%Y%m%d_%H%M%S)"}
OUT_ROOT=${OUT_ROOT:-"sweeps/${TS}"}
mkdir -p "${OUT_ROOT}"

log() { echo "[$(date +%H:%M:%S)] $*"; }

if [[ ! -f "${TRACE_FILE}" ]]; then
  echo "Error: trace not found: ${TRACE_FILE}" >&2
  exit 1
fi

# 固定状态布局与 penalty 开关，保证 C/Python shm 维度一致
BASE_COMMON="LOH_PARALLEL_SAFE=1 LOH_SKIP_PIP_INSTALL=1 LOH_SKIP_BUILD=1 CACHESIM_VERBOSE=0"
BASE_COMMON+=" LOH_INCLUDE_HIT_MISS_FEATURES=1 LOH_INCLUDE_CACHE_FEATURES=1 LOH_INCLUDE_CANDIDATE_FEATURES=0"
BASE_COMMON+=" LOH_INCLUDE_TOPK_CANDIDATE_FEATURES=0 LOH_INCLUDE_AVGTOPK_CANDIDATE_FEATURES=0 LOH_INCLUDE_REQUEST=1"
BASE_COMMON+=" RL_STATE_USE_MISSRATIO=1 LOH_ENABLE_PENALTY=1"

# penalty 次级参数默认值
PEN_SECONDARY="LOH_PENALTY_CUTOFF=0 LOH_PENALTY_DMAX=400000 LOH_PENALTY_EMPTY_AS_GOOD=1 LOH_PENALTY_REFINE_ON_LATE=1"
PEN_SECONDARY+=" LOH_PENALTY_NO_EVICT_REWARD=keep LOH_PENALTY_BASELINE_DECAY=0.99"
PEN_SECONDARY+=" LOH_SURVIVAL_BINS=64 LOH_SURVIVAL_QUANTILE=0.99 LOH_SURVIVAL_MINCOUNT=1000"
PEN_SECONDARY+=" LOH_PENALTY_NET_GOOD_SCALE=1.0 LOH_PENALTY_NET_PENALTY_SCALE=1.0"

CFG_FILE="${OUT_ROOT}/configs.txt"

write_configs() {
  local f=$1
  {
    echo "# 第二步单 seed：形态升级 + 更长训练窗口"
    for nreq in ${NUM_REQ_LIST}; do
      for algo in A2C SAC; do
        if [[ "${algo}" == "A2C" ]]; then
          upd=100
          act=0.8
        else
          upd=50
          act=0.8
        fi

        # shape0: 当前最佳形态（对照）
        for pen in 0 1; do
          if [[ "${pen}" == "1" ]]; then
            echo "${BASE_COMMON} CACHESIM_NUM_REQ=${nreq} LOH_REWARD_USE_PENALTY=1 LOH_RL_ALGO=${algo} RL_UPDATE_INTERVAL=${upd} LOH_ACTION_SCALE=${act} LOH_SCORE_USE_COMPOUND=0 LOH_SCORE_USE_IRT=0 LOH_USE_SOFTMAX=0 LOH_USE_HEURISTIC_SIGNS=0 LOH_PENALTY_SCALE=log LOH_PENALTY_REWARD_FORMULA=neg LOH_REWARD_W_PENALTY=0.1 ${PEN_SECONDARY}"
          else
            echo "${BASE_COMMON} CACHESIM_NUM_REQ=${nreq} LOH_REWARD_USE_PENALTY=0 LOH_RL_ALGO=${algo} RL_UPDATE_INTERVAL=${upd} LOH_ACTION_SCALE=${act} LOH_SCORE_USE_COMPOUND=0 LOH_SCORE_USE_IRT=0 LOH_USE_SOFTMAX=0 LOH_USE_HEURISTIC_SIGNS=0"
          fi
        done

        # shape1: compound+IRT+softmax
        for pen in 0 1; do
          if [[ "${pen}" == "1" ]]; then
            echo "${BASE_COMMON} CACHESIM_NUM_REQ=${nreq} LOH_REWARD_USE_PENALTY=1 LOH_RL_ALGO=${algo} RL_UPDATE_INTERVAL=${upd} LOH_ACTION_SCALE=${act} LOH_SCORE_USE_COMPOUND=1 LOH_SCORE_USE_IRT=1 LOH_USE_SOFTMAX=1 LOH_USE_HEURISTIC_SIGNS=0 LOH_PENALTY_SCALE=log LOH_PENALTY_REWARD_FORMULA=neg LOH_REWARD_W_PENALTY=0.1 ${PEN_SECONDARY}"
          else
            echo "${BASE_COMMON} CACHESIM_NUM_REQ=${nreq} LOH_REWARD_USE_PENALTY=0 LOH_RL_ALGO=${algo} RL_UPDATE_INTERVAL=${upd} LOH_ACTION_SCALE=${act} LOH_SCORE_USE_COMPOUND=1 LOH_SCORE_USE_IRT=1 LOH_USE_SOFTMAX=1 LOH_USE_HEURISTIC_SIGNS=0"
          fi
        done

        # shape2: compound+IRT, no softmax
        for pen in 0 1; do
          if [[ "${pen}" == "1" ]]; then
            echo "${BASE_COMMON} CACHESIM_NUM_REQ=${nreq} LOH_REWARD_USE_PENALTY=1 LOH_RL_ALGO=${algo} RL_UPDATE_INTERVAL=${upd} LOH_ACTION_SCALE=${act} LOH_SCORE_USE_COMPOUND=1 LOH_SCORE_USE_IRT=1 LOH_USE_SOFTMAX=0 LOH_USE_HEURISTIC_SIGNS=0 LOH_PENALTY_SCALE=log LOH_PENALTY_REWARD_FORMULA=neg LOH_REWARD_W_PENALTY=0.1 ${PEN_SECONDARY}"
          else
            echo "${BASE_COMMON} CACHESIM_NUM_REQ=${nreq} LOH_REWARD_USE_PENALTY=0 LOH_RL_ALGO=${algo} RL_UPDATE_INTERVAL=${upd} LOH_ACTION_SCALE=${act} LOH_SCORE_USE_COMPOUND=1 LOH_SCORE_USE_IRT=1 LOH_USE_SOFTMAX=0 LOH_USE_HEURISTIC_SIGNS=0"
          fi
        done

        # shape3: compound only + softmax
        for pen in 0 1; do
          if [[ "${pen}" == "1" ]]; then
            echo "${BASE_COMMON} CACHESIM_NUM_REQ=${nreq} LOH_REWARD_USE_PENALTY=1 LOH_RL_ALGO=${algo} RL_UPDATE_INTERVAL=${upd} LOH_ACTION_SCALE=${act} LOH_SCORE_USE_COMPOUND=1 LOH_SCORE_USE_IRT=0 LOH_USE_SOFTMAX=1 LOH_USE_HEURISTIC_SIGNS=0 LOH_PENALTY_SCALE=log LOH_PENALTY_REWARD_FORMULA=neg LOH_REWARD_W_PENALTY=0.1 ${PEN_SECONDARY}"
          else
            echo "${BASE_COMMON} CACHESIM_NUM_REQ=${nreq} LOH_REWARD_USE_PENALTY=0 LOH_RL_ALGO=${algo} RL_UPDATE_INTERVAL=${upd} LOH_ACTION_SCALE=${act} LOH_SCORE_USE_COMPOUND=1 LOH_SCORE_USE_IRT=0 LOH_USE_SOFTMAX=1 LOH_USE_HEURISTIC_SIGNS=0"
          fi
        done
      done
    done
  } > "${f}"
}

summarize_results() {
  local results_csv=$1
  local out_root=$2

  /bin/python3 - <<'PY' "${results_csv}" "${out_root}" "${TARGET_MR}"
import csv, os, sys

results_csv, out_root, target = sys.argv[1], sys.argv[2], float(sys.argv[3])
rows=[]

def parse_cfg(s):
    d={}
    for tok in (s or '').split():
        if '=' in tok:
            k,v = tok.split('=',1)
            d[k]=v
    return d

with open(results_csv, newline='') as f:
    r=csv.DictReader(f)
    for row in r:
        if str(row.get('exit_code','')).strip() != '0':
            continue
        try:
            mr=float(row.get('miss_ratio',''))
        except Exception:
            continue
        cfg=parse_cfg(row.get('config',''))
        row['_mr']=mr
        row['_cfg']=cfg
        rows.append(row)

rows.sort(key=lambda x:x['_mr'])

best_path=os.path.join(out_root,'best_overall.csv')
with open(best_path,'w',newline='') as f:
    w=csv.writer(f)
    w.writerow(['best_miss_ratio','run_timestamp','reached_target','config'])
    if rows:
        b=rows[0]
        w.writerow([f"{b['_mr']:.6f}", b.get('run_timestamp',''), int(b['_mr']<=target), b.get('config','')])

# 按 CACHESIM_NUM_REQ 分组 best
by_req={}
for r in rows:
    req=r['_cfg'].get('CACHESIM_NUM_REQ','')
    if req not in by_req or r['_mr'] < by_req[req]['_mr']:
        by_req[req]=r

with open(os.path.join(out_root,'best_by_num_req.csv'),'w',newline='') as f:
    w=csv.writer(f)
    w.writerow(['CACHESIM_NUM_REQ','best_miss_ratio','run_timestamp','config'])
    for req in sorted(by_req.keys(), key=lambda x: int(x) if x.isdigit() else 10**18):
        r=by_req[req]
        w.writerow([req, f"{r['_mr']:.6f}", r.get('run_timestamp',''), r.get('config','')])

# 按策略形态分组 best
shape_keys=['LOH_SCORE_USE_COMPOUND','LOH_SCORE_USE_IRT','LOH_USE_SOFTMAX','LOH_USE_HEURISTIC_SIGNS']
by_shape={}
for r in rows:
    cfg=r['_cfg']
    shape=' '.join(f"{k}={cfg.get(k,'')}" for k in shape_keys)
    if shape not in by_shape or r['_mr'] < by_shape[shape]['_mr']:
        by_shape[shape]=r

with open(os.path.join(out_root,'best_by_shape.csv'),'w',newline='') as f:
    w=csv.writer(f)
    w.writerow(['shape','best_miss_ratio','run_timestamp','config'])
    for shape, r in sorted(by_shape.items(), key=lambda kv: kv[1]['_mr']):
        w.writerow([shape, f"{r['_mr']:.6f}", r.get('run_timestamp',''), r.get('config','')])

print('rows', len(rows))
if rows:
    print('best_mr', f"{rows[0]['_mr']:.6f}")
PY
}

log "trace=${TRACE_FILE} cache_ratio=${CACHE_RATIO} target=${TARGET_MR}"
log "num_req_list=${NUM_REQ_LIST}"
log "out_root=${OUT_ROOT}"

log "[build] compile with fixed state layout"
export LOH_INCLUDE_HIT_MISS_FEATURES=1
export LOH_INCLUDE_CACHE_FEATURES=1
export LOH_INCLUDE_CANDIDATE_FEATURES=0
export LOH_INCLUDE_TOPK_CANDIDATE_FEATURES=0
export LOH_INCLUDE_AVGTOPK_CANDIDATE_FEATURES=0
export LOH_INCLUDE_REQUEST=1
export LOH_ENABLE_PENALTY=1
export LOH_DEBUG_LEVEL=0
log "[build] compile-time LOH_DEBUG_LEVEL=${LOH_DEBUG_LEVEL}"
bash scripts/debug.sh -c >/dev/null

write_configs "${CFG_FILE}"
N_CFG=$(grep -vE '^[[:space:]]*(#|$)' "${CFG_FILE}" | wc -l)
log "generated configs=${N_CFG} file=${CFG_FILE}"

if [[ "${DRY_RUN}" == "1" ]]; then
  log "DRY_RUN=1 done"
  exit 0
fi

SWEEP_ID="${TS}" \
SWEEP_OUTDIR="${OUT_ROOT}" \
SWEEP_REPEATS="${SWEEP_REPEATS}" \
SEED_BASE="${SEED_BASE}" \
SWEEP_RESUME=1 \
bash scripts/sweep_loh_rl_sb3.sh "${CFG_FILE}" "${TRACE_FILE}" "${CACHE_RATIO}" >/dev/null

summarize_results "${OUT_ROOT}/results.csv" "${OUT_ROOT}"
log "summary: ${OUT_ROOT}/best_overall.csv ${OUT_ROOT}/best_by_num_req.csv ${OUT_ROOT}/best_by_shape.csv"
