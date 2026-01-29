#!/usr/bin/env bash
set -euo pipefail

# 对固定权重进行穷举搜索，只运行 C 端 LOH（不启动 Python/RL），
# 通过环境变量 LOH_ENABLE_RL=0 + LOH_FIXED_WEIGHTS=... 直接评估 miss ratio。
#
# 覆盖的 trace：
#   - data/MetaCDN/meta_reag.oracleGeneral.zst
#   - data/WikiCDN/wiki_2019t.oracleGeneral.zst
#   - data/TencentCBS/1063.oracleGeneral.zst
#
# 默认：每个维度取值 0/1/2（可通过 OVERRIDE_VALUES 覆盖），排除全 0，
#       共 3^6-1 = 728 组权重；对每个 trace 分别跑一遍。
# 并行：通过 MAX_PARALLEL 控制最大并行任务数（默认 8）。
# 请求数：通过 CACHESIM_NUM_REQ 控制（默认 3000000）。
# cache 比例：通过 CACHE_RATIO 控制（默认 0.1）。
#
# 用法示例：
#   bash scripts/sweep_loh_constant_weights_norl.sh
#   MAX_PARALLEL=16 CACHE_RATIO=0.05 bash scripts/sweep_loh_constant_weights_norl.sh
#   OVERRIDE_VALUES="0,1" bash scripts/sweep_loh_constant_weights_norl.sh   # 仅扫 0/1 组合
#   TRACE_LIST="data/Custom/trace1.txt,data/Custom/trace2.txt" bash scripts/sweep_loh_constant_weights_norl.sh  # 自定义 trace 列表
#   SKIP_REFINE=1 bash scripts/sweep_loh_constant_weights_norl.sh   # 仅粗粒度扫 + 汇总，不跑 refine

# 三条固定 trace（可通过 TRACE_LIST 覆盖）
TRACES=(
  "data/MetaCDN/meta_reag.oracleGeneral.zst"
  "data/WikiCDN/wiki_2019t.oracleGeneral.zst"
  "data/TencentCBS/1063.oracleGeneral.zst"
)
if [ -n "${TRACE_LIST:-}" ]; then
  IFS=',' read -r -a CUSTOM_TRACES <<< "${TRACE_LIST}"
  TRACES=()
  for TRACE in "${CUSTOM_TRACES[@]}"; do
    TRACES+=("$TRACE")
  done
fi

CACHE_RATIO=${CACHE_RATIO:-0.1}
CACHESIM_NUM_REQ=${CACHESIM_NUM_REQ:-3000000}
MAX_PARALLEL=${MAX_PARALLEL:-16}
REFINE_TOP_K=${REFINE_TOP_K:-5}       # 每个 trace 细粒度 refine 的 top-K 组合数
REFINE_DELTA=${REFINE_DELTA:-0.5}     # 细粒度步长（在原始权重基础上 ±DELTA）

# 每个维度的粗粒度取值；如设置环境变量 OVERRIDE_VALUES="0,1" 则改为对应取值
if [ -n "${OVERRIDE_VALUES:-}" ]; then
  IFS=',' read -r -a VALUES <<< "${OVERRIDE_VALUES}"
else
  VALUES=(0 1 2)
fi

if [ -n "${OUT_DIR:-}" ]; then
  # 若外部已指定 OUT_DIR，则复用该目录（用于仅汇总/refine 已有结果）
  RUN_TS="manual"
  mkdir -p "${OUT_DIR}"
else
  RUN_TS=$(date +%m%d_%H%M%S)
  OUT_DIR="runs/constant_weight_norl_${RUN_TS}"
  mkdir -p "${OUT_DIR}"
fi

echo "[sweep_loh_constant_weights_norl] CACHE_RATIO=${CACHE_RATIO}, NUM_REQ=${CACHESIM_NUM_REQ}, MAX_PARALLEL=${MAX_PARALLEL}, OUT_DIR=${OUT_DIR}" >&2

# 确认 cachesim 已构建
if [ ! -x "_build_dbg/bin/cachesim" ]; then
  echo "ERROR: _build_dbg/bin/cachesim not found. Please run 'bash scripts/debug.sh -c' first." >&2
  exit 1
fi

job_count=0

if [ "${SKIP_SWEEP:-0}" != "1" ]; then
  # 为每个 trace 单独 sweep 一遍
  for TRACE_PATH in "${TRACES[@]}"; do
    if [ ! -f "${TRACE_PATH}" ]; then
      echo "[WARN] Trace file not found, skip: ${TRACE_PATH}" >&2
      continue
    fi

    TRACE_BASENAME=$(basename "${TRACE_PATH}")
    SHORT_TRACE=${TRACE_BASENAME:0:8}
    echo "==============================" >&2
    echo "[TRACE] ${TRACE_PATH} (${TRACE_BASENAME})" >&2

    for w1 in "${VALUES[@]}"; do
      for w2 in "${VALUES[@]}"; do
        for w3 in "${VALUES[@]}"; do
          for w4 in "${VALUES[@]}"; do
            for w5 in "${VALUES[@]}"; do
              for w6 in "${VALUES[@]}"; do
                if [[ "${w1}" == 0 && "${w2}" == 0 && "${w3}" == 0 && "${w4}" == 0 && "${w5}" == 0 && "${w6}" == 0 ]]; then
                  continue
                fi

                W="${w1},${w2},${w3},${w4},${w5},${w6}"
                # 日志命名为: <SHORT_TRACE>_w_w1_w2_w3_w4_w5_w6.log，便于后续解析
                LOG="${OUT_DIR}/${SHORT_TRACE}_w_${w1}_${w2}_${w3}_${w4}_${w5}_${w6}.log"
                echo "[TRACE=${SHORT_TRACE}] LOH_FIXED_WEIGHTS=${W} -> ${LOG}" >&2

                (
                  # 仅 C 端 LOH，禁用 RL，同一进程内使用固定权重
                  LOH_ENABLE_RL=0 \
                  LOH_FIXED_WEIGHTS="${W}" \
                  _build_dbg/bin/cachesim "${TRACE_PATH}" oracleGeneral LOH "${CACHE_RATIO}" \
                    --num-req="${CACHESIM_NUM_REQ}" -v 1
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

  done

  wait
  echo "[sweep_loh_constant_weights_norl] 所有任务提交完成，总任务数=${job_count}" >&2
else
  echo "[sweep_loh_constant_weights_norl] SKIP_SWEEP=1, 仅基于现有 OUT_DIR=${OUT_DIR} 做汇总与 refine" >&2
fi

# ============================
# 第一阶段汇总：每个 trace 下所有权重的 miss ratio / byte miss ratio
# ============================
for TRACE_PATH in "${TRACES[@]}"; do
  if [ ! -f "${TRACE_PATH}" ]; then
    continue
  fi
  TRACE_BASENAME=$(basename "${TRACE_PATH}")
  SHORT_TRACE=${TRACE_BASENAME:0:8}

  RESULT_FILE="${OUT_DIR}/${SHORT_TRACE}_results.tsv"
  echo -e "#w1\tw2\tw3\tw4\tw5\tw6\tmiss_ratio\tbyte_miss_ratio\tlog" \
    >"${RESULT_FILE}"

  for f in "${OUT_DIR}/${SHORT_TRACE}_w_"*.log; do
    [ -f "${f}" ] || continue
    base=$(basename "${f}")
    # base 形如: <SHORT_TRACE>_w_w1_w2_w3_w4_w5_w6.log
    rest=${base#${SHORT_TRACE}_w_}
    rest=${rest%.log}
    IFS='_' read -r w1 w2 w3 w4 w5 w6 <<< "${rest}"

    # 取最后一行 summary（包含 miss ratio / byte miss ratio）
    line=$(grep -E "miss ratio" "${f}" | tail -n 1 || true)
    [ -n "${line}" ] || continue
    line_without_byte=$(echo "${line}" | sed -E 's/byte miss ratio.*//' )
    mr=$(echo "${line_without_byte}" | sed -E 's/.*miss ratio[[:space:]]*=?[[:space:]]*([0-9.]+).*/\1/' || true)
    bmr=$(echo "${line}" | sed -E 's/.*byte miss ratio[[:space:]]*=?[[:space:]]*([0-9.]+).*/\1/' || true)
    [ -n "${mr}" ] || continue
    [ -n "${bmr}" ] || continue

    printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
      "${w1}" "${w2}" "${w3}" "${w4}" "${w5}" "${w6}" \
      "${mr}" "${bmr}" "${f}" >>"${RESULT_FILE}"
  done

  echo -e "\n[RESULT-COARSE] Trace=${TRACE_BASENAME}" >&2
    if [ -s "${RESULT_FILE}" ]; then
    # 找到 miss ratio 最小的一行（如相同则按 byte miss ratio 再比）
    best_line=$(grep -v '^#' "${RESULT_FILE}" | sort -k7,7g -k8,8g | head -n 1 || true)
    best_mr=$(echo "${best_line}" | awk '{print $7}')
    best_bmr=$(echo "${best_line}" | awk '{print $8}')
    echo "  best miss ratio      = ${best_mr}" >&2
    echo "  best byte miss ratio = ${best_bmr}" >&2
    echo "  row: ${best_line}" >&2
    echo "  top 20 coarse rows (miss_ratio, byte_miss_ratio, weights):" >&2
      top20_path="${OUT_DIR}/${SHORT_TRACE}_top20.tsv"
      top20_lines=$(grep -v '^#' "${RESULT_FILE}" | sort -k7,7g -k8,8g | head -n 20 || true)
      {
        printf "#w1\tw2\tw3\tw4\tw5\tw6\tmiss_ratio\tbyte_miss_ratio\tlog\n"
        printf "%s\n" "${top20_lines}"
      } >"${top20_path}"
      if [ -n "${top20_lines}" ]; then
        echo "  top 20 coarse rows saved to ${top20_path}" >&2
        printf "%s" "${top20_lines}" | awk '{printf "    W=[%s,%s,%s,%s,%s,%s] mr=%s bmr=%s\n", $1,$2,$3,$4,$5,$6,$7,$8}' >&2
      else
        echo "  (no coarse rows to show)" >&2
      fi
  else
    echo "  (no valid results found)" >&2
  fi

done

if [ "${SKIP_REFINE:-0}" != "1" ]; then
  # ============================
  # 第二阶段：对每个 trace 的 top-K 组合做细粒度 refine
  # ============================
  for TRACE_PATH in "${TRACES[@]}"; do
    if [ ! -f "${TRACE_PATH}" ]; then
      continue
    fi
    TRACE_BASENAME=$(basename "${TRACE_PATH}")
    SHORT_TRACE=${TRACE_BASENAME:0:8}

    RESULT_FILE="${OUT_DIR}/${SHORT_TRACE}_results.tsv"
    [ -s "${RESULT_FILE}" ] || continue

    REFINE_CAND="${OUT_DIR}/${SHORT_TRACE}_refine_candidates.txt"
    : >"${REFINE_CAND}"

    # 选出 miss ratio 最小的前 REFINE_TOP_K 行
    set +e
    set +o pipefail 2>/dev/null || true
    grep -v '^#' "${RESULT_FILE}" | sort -k7,7g -k8,8g | head -n "${REFINE_TOP_K}" | while read -r w1 w2 w3 w4 w5 w6 mr bmr logf; do
      # 原始组合
      echo "${w1},${w2},${w3},${w4},${w5},${w6}" >>"${REFINE_CAND}"
      # 对每个维度做 ±REFINE_DELTA 的微调（不小于 0）
      for idx in 1 2 3 4 5 6; do
        eval cur=\${w${idx}}
        for sign in - +; do
          if [ "${sign}" = "-" ]; then
            new=$(awk -v c="${cur}" -v d="${REFINE_DELTA}" 'BEGIN{v=c-d; if (v<0) v=0; printf "%.3f", v}')
          else
            new=$(awk -v c="${cur}" -v d="${REFINE_DELTA}" 'BEGIN{v=c+d; printf "%.3f", v}')
          fi
          nw1=${w1}; nw2=${w2}; nw3=${w3}; nw4=${w4}; nw5=${w5}; nw6=${w6}
          case ${idx} in
            1) nw1=${new};;
            2) nw2=${new};;
            3) nw3=${new};;
            4) nw4=${new};;
            5) nw5=${new};;
            6) nw6=${new};;
          esac
          echo "${nw1},${nw2},${nw3},${nw4},${nw5},${nw6}" >>"${REFINE_CAND}"
        done
      done
    done
    set -e
    set -o pipefail 2>/dev/null || true

    # 去重 refine 候选
    sort -u "${REFINE_CAND}" -o "${REFINE_CAND}"

    cand_count=$(wc -l < "${REFINE_CAND}")
    echo -e "\n[REFINE] Trace=${TRACE_BASENAME}, candidates=${cand_count}" >&2

    refine_jobs=0
    while IFS=',' read -r rw1 rw2 rw3 rw4 rw5 rw6; do
      [ -n "${rw1:-}" ] || continue
      W="${rw1},${rw2},${rw3},${rw4},${rw5},${rw6}"
      LOG="${OUT_DIR}/${SHORT_TRACE}_refine_w_${rw1}_${rw2}_${rw3}_${rw4}_${rw5}_${rw6}.log"
      echo "  [REFINE ${SHORT_TRACE}] LOH_FIXED_WEIGHTS=${W} -> ${LOG}" >&2

      (
        LOH_ENABLE_RL=0 \
        LOH_FIXED_WEIGHTS="${W}" \
        _build_dbg/bin/cachesim "${TRACE_PATH}" oracleGeneral LOH "${CACHE_RATIO}" \
          --num-req="${CACHESIM_NUM_REQ}" -v 1
      ) >"${LOG}" 2>&1 &

      refine_jobs=$((refine_jobs + 1))
      if (( refine_jobs % MAX_PARALLEL == 0 )); then
        wait
      fi
    done <"${REFINE_CAND}"

    wait

    # 汇总 refine 结果
    REFINE_RES="${OUT_DIR}/${SHORT_TRACE}_refine_results.tsv"
    echo -e "#w1\tw2\tw3\tw4\tw5\tw6\tmiss_ratio\tbyte_miss_ratio\tlog" \
      >"${REFINE_RES}"

    for f in "${OUT_DIR}/${SHORT_TRACE}_refine_w_"*.log; do
      [ -f "${f}" ] || continue
      base=$(basename "${f}")
      rest=${base#${SHORT_TRACE}_refine_w_}
      rest=${rest%.log}
      IFS='_' read -r w1 w2 w3 w4 w5 w6 <<< "${rest}"

      line=$(grep -E "miss ratio" "${f}" | tail -n 1 || true)
      [ -n "${line}" ] || continue
      line_without_byte=$(echo "${line}" | sed -E 's/byte miss ratio.*//' )
      mr=$(echo "${line_without_byte}" | sed -E 's/.*miss ratio[[:space:]]*=?[[:space:]]*([0-9.]+).*/\1/' || true)
      bmr=$(echo "${line}" | sed -E 's/.*byte miss ratio[[:space:]]*=?[[:space:]]*([0-9.]+).*/\1/' || true)
      [ -n "${mr}" ] || continue
      [ -n "${bmr}" ] || continue

      printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
        "${w1}" "${w2}" "${w3}" "${w4}" "${w5}" "${w6}" \
        "${mr}" "${bmr}" "${f}" >>"${REFINE_RES}"
    done

    echo "[RESULT-REFINE] Trace=${TRACE_BASENAME}" >&2
    if [ -s "${REFINE_RES}" ]; then
      best_line=$(grep -v '^#' "${REFINE_RES}" | sort -k7,7g -k8,8g | head -n 1 || true)
      best_mr=$(echo "${best_line}" | awk '{print $7}')
      best_bmr=$(echo "${best_line}" | awk '{print $8}')
      echo "  best miss ratio      = ${best_mr}" >&2
      echo "  best byte miss ratio = ${best_bmr}" >&2
      echo "  row: ${best_line}" >&2
    else
      echo "  (no refine results found)" >&2
    fi

  done
else
  echo "[sweep_loh_constant_weights_norl] SKIP_REFINE=1 (only sweep + coarse summary)" >&2
fi

if [ "${SKIP_REFINE:-0}" != "1" ]; then
  echo -e "\n[sweep_loh_constant_weights_norl] 汇总完成。每个 trace 的 coarse / refine 结果见: ${OUT_DIR}/*_results.tsv" >&2
else
  echo -e "\n[sweep_loh_constant_weights_norl] 汇总完成（仅 sweep）。每个 trace 的 coarse 结果见: ${OUT_DIR}/*_results.tsv" >&2
fi
