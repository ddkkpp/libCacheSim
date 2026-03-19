#!/usr/bin/env bash
# 批量 sweep：多组环境变量配置 -> 运行 scripts/test_loh_rl_sb3.sh -> 汇总最终 miss ratio + TB 路径
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  bash scripts/sweep_loh_rl_sb3.sh <configs.txt> [trace_file] [cache_ratio]

configs.txt format:
  - 每行一组配置（空行/以 # 开头的行会被忽略）
  - 行内写 shell 风格的 KEY=VALUE，用空格分隔

Example line:
  LOH_RL_ALGO=TD3 LOH_SCORE_USE_COMPOUND=1 LOH_ACTION_SCALE=3

Outputs:
  - sweeps/<SWEEP_ID>/results.csv   汇总表
  - sweeps/<SWEEP_ID>/summary.csv   按 config 聚合（均值/方差）
  - sweeps/<SWEEP_ID>/runs.txt      每次 run 的 TB 目录提示（基于 ./runs/<RUN_TIMESTAMP>/tensorboard）

Tips:
  - 用 TensorBoard 看所有本次 sweep：
      tensorboard --logdir ./runs --port 6006
USAGE
}

if [[ ${1:-} == "-h" || ${1:-} == "--help" ]]; then
  usage
  exit 0
fi

CONFIG_FILE=${1:-}
TRACE_FILE=${2:-data/MetaCDN/meta_reag.oracleGeneral.zst}
CACHE_RATIO=${3:-0.1}

# 默认限制 MetaCDN sweep 的请求数，避免误跑全量 trace
if [[ -z "${CACHESIM_NUM_REQ:-}" && "${TRACE_FILE}" == data/MetaCDN/* ]]; then
  export CACHESIM_NUM_REQ=3000000
  echo "[sweep] CACHESIM_NUM_REQ not set; defaulting to ${CACHESIM_NUM_REQ} for MetaCDN trace"
fi

# 默认限制 TencentCBS sweep 的请求数，避免误跑全量 trace
if [[ -z "${CACHESIM_NUM_REQ:-}" && "${TRACE_FILE}" == data/TencentCBS/* ]]; then
  export CACHESIM_NUM_REQ=3000000
  echo "[sweep] CACHESIM_NUM_REQ not set; defaulting to ${CACHESIM_NUM_REQ} for TencentCBS trace"
fi

# 默认限制 WikiCDN sweep 的请求数，避免误跑全量 trace
if [[ -z "${CACHESIM_NUM_REQ:-}" && "${TRACE_FILE}" == data/WikiCDN/* ]]; then
  export CACHESIM_NUM_REQ=3000000
  echo "[sweep] CACHESIM_NUM_REQ not set; defaulting to ${CACHESIM_NUM_REQ} for WikiCDN trace"
fi

if [[ -z "${CONFIG_FILE}" || ! -f "${CONFIG_FILE}" ]]; then
  echo "Error: configs file not found: ${CONFIG_FILE}" >&2
  usage
  exit 1
fi

SWEEP_ID=${SWEEP_ID:-"sweep_$(date +%Y%m%d_%H%M%S)"}
OUT_DIR=${SWEEP_OUTDIR:-"sweeps/${SWEEP_ID}"}
LOG_DIR=${LOH_LOG_DIR:-"logs"}
mkdir -p "${OUT_DIR}"
mkdir -p "${LOG_DIR}"

# 断点续跑：
# - SWEEP_RESUME=1：若 results.csv 里已经存在“成功完成”的 (idx,rep)，则跳过该 run；否则重跑。
#   成功定义：exit_code==0 且 miss_ratio/byte_miss_ratio/throughput 都不是 NA。
# - 续跑模式下不会清空 runs.txt（会在文件末尾追加）。
SWEEP_RESUME=${SWEEP_RESUME:-0}

RESULTS_CSV="${OUT_DIR}/results.csv"
SUMMARY_CSV="${OUT_DIR}/summary.csv"
RUNS_TXT="${OUT_DIR}/runs.txt"

# CSV header
if [[ ! -f "${RESULTS_CSV}" ]]; then
  echo "idx,rep,seed,run_timestamp,exit_code,miss_ratio,byte_miss_ratio,throughput_mqps,trace_file,cache_ratio,config" > "${RESULTS_CSV}"
fi

if [[ "${SWEEP_RESUME}" != "1" ]]; then
  : > "${RUNS_TXT}"
fi

echo "[sweep] SWEEP_ID=${SWEEP_ID}"
echo "[sweep] configs=${CONFIG_FILE}"
echo "[sweep] trace=${TRACE_FILE} cache_ratio=${CACHE_RATIO}"
echo "[sweep] out=${OUT_DIR}"

SWEEP_REPEATS=${SWEEP_REPEATS:-1}
SEED_BASE=${SEED_BASE:-0}
echo "[sweep] repeats=${SWEEP_REPEATS} seed_base=${SEED_BASE}"

# 从 cachesim 日志中解析一行形如："..., miss ratio 0.3685, byte miss ratio 0.2177, throughput 0.02 MQPS"
parse_cachesim_metrics() {
  local log_file=$1
  # 用 python regex 在“全文（含换行）”里找最后一次匹配，避免日志换行导致 sed/grep 误解析。
  python3 - <<'PY' "${log_file}"
import re
import sys

path = sys.argv[1]
try:
    text = open(path, 'r', errors='ignore').read()
except Exception:
    print('NA,NA,NA')
    raise SystemExit(0)

pat = re.compile(
    r"miss ratio\s+([0-9]*\.[0-9]+)\s*,\s*byte miss ratio\s+([0-9]*\.[0-9]+)\s*,\s*throughput\s+([0-9]*\.[0-9]+)\s+MQPS",
    re.IGNORECASE | re.MULTILINE | re.DOTALL,
)
ms = list(pat.finditer(text))
if not ms:
    print('NA,NA,NA')
else:
    m = ms[-1]
    print(f"{m.group(1)},{m.group(2)},{m.group(3)}")
PY
}

# 读取已完成（成功）的 run，用于续跑跳过
declare -A _done_success
if [[ "${SWEEP_RESUME}" == "1" && -f "${RESULTS_CSV}" ]]; then
  while IFS=$'\t' read -r didx drep; do
    if [[ -n "${didx}" && -n "${drep}" ]]; then
      _done_success["${didx}|${drep}"]=1
    fi
  done < <(
    python3 - <<'PY' "${RESULTS_CSV}"
import csv
import sys

path = sys.argv[1]
try:
    with open(path, newline='') as f:
        r = csv.DictReader(f)
        for row in r:
            idx = (row.get('idx') or '').strip()
            rep = (row.get('rep') or '').strip()
            exit_code = (row.get('exit_code') or '').strip()
            mr = (row.get('miss_ratio') or '').strip()
            bmr = (row.get('byte_miss_ratio') or '').strip()
            thr = (row.get('throughput_mqps') or '').strip()
            if not idx or not rep:
                continue
            ok = (
                exit_code == '0'
                and mr.upper() != 'NA' and mr != ''
                and bmr.upper() != 'NA' and bmr != ''
                and thr.upper() != 'NA' and thr != ''
            )
            if ok:
                print(f"{idx}\t{rep}")
except Exception:
    pass
PY
  )
fi

idx=0
# 进度条总数：只统计“非空且非注释”的配置行（与实际执行条数一致）
TOTAL_CONFIGS=$(awk '{
  line=$0
  sub(/^[ \t]+/, "", line)
  sub(/[ \t]+$/, "", line)
  if (line == "" || line ~ /^#/) next
  c++
} END {print c+0}' "${CONFIG_FILE}")
# 防止配置串味：记录之前 export 过的键，每次 run 前先全部 unset
declare -A _sweep_keys_seen
while IFS= read -r raw_line || [[ -n "${raw_line}" ]]; do
  # trim
  line=$(echo "${raw_line}" | sed -e 's/^\s\+//g' -e 's/\s\+$//g')
  if [[ -z "${line}" ]]; then
    continue
  fi
  if [[ "${line}" == \#* ]]; then
    continue
  fi

  idx=$((idx + 1))
  echo ""
  echo "[sweep] ===== ${idx} / ${TOTAL_CONFIGS} ====="
  echo "[sweep] config: ${line}"

  # 让 test 脚本不 pkill 其他进程（如果你要并行跑可以设置 LOH_PARALLEL_SAFE=1）
  export LOH_PARALLEL_SAFE=${LOH_PARALLEL_SAFE:-1}

  # 清理上一组配置遗留的环境变量（避免本组未显式设置的键沿用旧值）
  for k in "${!_sweep_keys_seen[@]}"; do
    unset "${k}" || true
  done

  # 解析本行 keys 并登记（只登记 KEY=VALUE 形式，忽略异常片段）
  # shellcheck disable=SC2206
  parts=( ${line} )
  for part in "${parts[@]}"; do
    if [[ "${part}" == *=* ]]; then
      key=${part%%=*}
      if [[ -n "${key}" ]]; then
        _sweep_keys_seen["${key}"]=1
      fi
    fi
  done

  # 将本行配置注入环境
  # shellcheck disable=SC2086
  eval "export ${line}"

  # sweep 默认使用最小 debug（LOH_DEBUG_CONFIG=0），除非在 config 行或外部显式设置
  if [[ "${line}" != *"LOH_DEBUG_LEVEL="* && -z "${LOH_DEBUG_LEVEL:-}" ]]; then
    export LOH_DEBUG_LEVEL=0
  fi

  rep=0
  while [[ ${rep} -lt ${SWEEP_REPEATS} ]]; do
    rep=$((rep + 1))
    run_ts="${SWEEP_ID}_$(printf '%03d' "${idx}")_r$(printf '%02d' "${rep}")"
    seed=$((SEED_BASE + idx * 100 + rep))

    if [[ "${SWEEP_RESUME}" == "1" && -n "${_done_success["${idx}|${rep}"]:-}" ]]; then
      echo "[sweep] (resume) skip idx=${idx} rep=${rep} (already successful)"
      continue
    fi

    echo "[sweep] RUN_TIMESTAMP=${run_ts} rep=${rep}/${SWEEP_REPEATS} seed=${seed}"
    export RUN_TIMESTAMP="${run_ts}"
    export LOH_SEED="${seed}"

    set +e
    bash scripts/test_loh_rl_sb3.sh "${TRACE_FILE}" "${CACHE_RATIO}" > "${OUT_DIR}/${run_ts}.stdout.txt" 2>&1
    exit_code=$?
    set -e

    cachesim_log="${LOG_DIR}/cachesim_sb3_${run_ts}.log"
    py_log="${LOG_DIR}/ac_sb3_${run_ts}.log"

    mr="NA"; bmr="NA"; thr="NA"
    if [[ -f "${cachesim_log}" ]]; then
      IFS=',' read -r mr bmr thr < <(parse_cachesim_metrics "${cachesim_log}")
    fi

    tb_dir="./runs/${run_ts}/tensorboard"
    echo -e "${idx}\t${rep}\t${seed}\t${run_ts}\t${tb_dir}\t${py_log}\t${cachesim_log}" >> "${RUNS_TXT}"

    cfg_csv=$(printf '%s' "${line}" | sed 's/"/""/g')
    echo "${idx},${rep},${seed},${run_ts},${exit_code},${mr},${bmr},${thr},\"${TRACE_FILE}\",${CACHE_RATIO},\"${cfg_csv}\"" >> "${RESULTS_CSV}"

    echo "[sweep] exit=${exit_code} OMR=${mr} BMR=${bmr} thr_mqps=${thr}"
    echo "[sweep] TB: ${tb_dir}"
  done

done < "${CONFIG_FILE}"

# 生成聚合 summary.csv（按 idx/config 聚合 OMR/BMR/throughput 的均值与标准差）
python3 - <<'PY' "${RESULTS_CSV}" "${SUMMARY_CSV}"
import csv
import math
import sys

src, dst = sys.argv[1], sys.argv[2]

def to_float(x):
    try:
        return float(x)
    except Exception:
        return None

rows = []
with open(src, newline='') as f:
    reader = csv.DictReader(f)
    for r in reader:
        rows.append(r)

groups = {}
for r in rows:
    key = (r.get('idx',''), r.get('config',''))
    groups.setdefault(key, []).append(r)

with open(dst, 'w', newline='') as f:
    fieldnames = [
        'idx','n','miss_ratio_mean','miss_ratio_std','byte_miss_ratio_mean','byte_miss_ratio_std','throughput_mqps_mean','throughput_mqps_std','config'
    ]
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    for (idx, cfg), rs in sorted(groups.items(), key=lambda x: int(x[0][0])):
        def stats(col):
            vals = [to_float(r.get(col)) for r in rs]
            vals = [v for v in vals if v is not None]
            if not vals:
                return (None, None)
            m = sum(vals) / len(vals)
            if len(vals) == 1:
                return (m, 0.0)
            var = sum((v-m)*(v-m) for v in vals) / (len(vals)-1)
            return (m, math.sqrt(var))

        # n 统计为“有效样本数”（miss_ratio 可解析为 float 的条目数），避免续跑时把 NA 也算进 n
        n_valid = sum(1 for r in rs if to_float(r.get('miss_ratio')) is not None)

        mr_m, mr_s = stats('miss_ratio')
        bmr_m, bmr_s = stats('byte_miss_ratio')
        thr_m, thr_s = stats('throughput_mqps')
        w.writerow({
          'idx': idx,
          'n': n_valid,
          'miss_ratio_mean': 'NA' if mr_m is None else f'{mr_m:.6f}',
          'miss_ratio_std': 'NA' if mr_s is None else f'{mr_s:.6f}',
          'byte_miss_ratio_mean': 'NA' if bmr_m is None else f'{bmr_m:.6f}',
          'byte_miss_ratio_std': 'NA' if bmr_s is None else f'{bmr_s:.6f}',
          'throughput_mqps_mean': 'NA' if thr_m is None else f'{thr_m:.6f}',
          'throughput_mqps_std': 'NA' if thr_s is None else f'{thr_s:.6f}',
          'config': cfg,
        })
PY

echo ""
echo "[sweep] Done."
echo "[sweep] Results: ${RESULTS_CSV}"
echo "[sweep] Summary:  ${SUMMARY_CSV}"
echo "[sweep] Runs:    ${RUNS_TXT}"

# 可选：自动把本次 sweep 的 results.csv 追加到测试汇总（按 trace 分组）
# 默认开启；如不需要可设 SWEEP_APPEND_TO_MD=0
SWEEP_APPEND_TO_MD=${SWEEP_APPEND_TO_MD:-1}
SUMMARY_MD=${SUMMARY_MD:-20260129-LOH_TESTED_CONFIGS_SUMMARY.md}
if [[ "${SWEEP_APPEND_TO_MD}" == "1" && -f "${SUMMARY_MD}" ]]; then
  python3 scripts/append_sweep_results_to_summary.py \
    --summary-md "${SUMMARY_MD}" \
    --trace "${TRACE_FILE}" \
    --results "${RESULTS_CSV}" \
    --sweep-id "${SWEEP_ID}" \
    --results-link "${RESULTS_CSV}"
fi
