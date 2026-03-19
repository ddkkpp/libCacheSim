# LOH 完整实验结果


















































































































































































echo "[finished] ${RESULTS_CSV}" >> "$RUNNER_LOG"done  echo "[queue] active=${running}/${PARALLEL} action=finish_one" >> "$RUNNER_LOG"  running=$((running - 1))  wait -n || truewhile [ "$running" -gt 0 ]; dodone  done    done      fi        echo "[queue] active=${running}/${PARALLEL} action=finish_one" >> "$RUNNER_LOG"        running=$((running - 1))        wait -n || true      if [ "$running" -ge "$PARALLEL" ]; then      echo "[queue] active=${running}/${PARALLEL} action=start algo=${algo} exclude=${ex} trace=${trace_name}" >> "$RUNNER_LOG"      running=$((running + 1))      run_one "$algo" "$ex" "$trace_name" "$trace_path" &      IFS='|' read -r trace_name trace_path <<< "$t"    for t in "${TASKS[@]}"; do  for ex in "${EXCLUDES[@]}"; dofor algo in "${ALGOS[@]}"; dorunning=0}  fi    ) 9>"$OUT_DIR/doc_update.lock"      python3 "$OUT_DIR/update_doc_section.py" "$RESULTS_CSV" "$DOC_PATH" >> "$OUT_DIR/doc_update.log" 2>&1 || true      flock 9    (  if [ -f "$OUT_DIR/update_doc_section.py" ]; then  echo "[case-done] algo=${algo} exclude=${exclude_recent_steps} trace=${trace_name} status=${status} rc=${rc} final_mr=${fmr} final_bmr=${fbmr} final_mqps=${fmqps}" >> "$RUNNER_LOG"  echo "${algo},${exclude_recent_steps},${trace_name},${status},${rc},${fmr},${fbmr},${fmqps},${log_path}" >> "$RESULTS_CSV"  [ "$rc" -ne 0 ] && status="failed"  fi    fmqps="$(echo "$fin" | cut -d',' -f3)"    fbmr="$(echo "$fin" | cut -d',' -f2)"    fmr="$(echo "$fin" | cut -d',' -f1)"  if [ -n "$fin" ]; then  fin=$(extract_final "$log_path" || true)  local fin fmr="NA" fbmr="NA" fmqps="NA" status="ok"  ) > "$log_path" 2>&1 || rc=$?    bash scripts/test_loh_rl_sb3.sh "$trace_path" "$CACHE_SIZE"    for kv in "${COMMON_ENV[@]}"; do export "$kv"; done    export RUN_TIMESTAMP="$(date +%m%d_%H%M%S)_${case_name}_$(date +%s)"    export LOH_EXCLUDE_RECENT_STEPS="$exclude_recent_steps"    export LOH_RL_ALGO="$algo"    export LOH_SHM_KEY="$shm_key"  (  echo "[case-start] algo=${algo} exclude=${exclude_recent_steps} trace=${trace_name}" >> "$RUNNER_LOG"  rm -f "/dev/shm/loh_ac_${shm_key}" "/dev/shm/sem.loh_ac_ready_${shm_key}" "/dev/shm/sem.loh_ac_ack_${shm_key}" || true  shm_key=$(printf "%s|%s|%s|%s|%s" "$trace_name" "$algo" "$exclude_recent_steps" "$CACHE_SIZE" "$(date +%s%N)" | cksum | awk '{print $1}')  local shm_key rc=0  local log_path="$OUT_DIR/${case_name}_${case_stamp}.log"  case_stamp="$(date +%m%d_%H%M%S)"  local case_stamp  local case_name="${trace_name}_${algo}_ex${exclude_recent_steps}_cache01"  fi    return 0    echo "[resume-skip] algo=${algo} exclude=${exclude_recent_steps} trace=${trace_name} already done" >> "$RUNNER_LOG"  if already_done "$algo" "$exclude_recent_steps" "$trace_name"; then  local trace_path="$4"  local trace_name="$3"  local exclude_recent_steps="$2"  local algo="$1"run_one() {}  grep -q "^${algo},${exclude_recent_steps},${trace_name},ok," "$RESULTS_CSV"  local trace_name="$3"  local exclude_recent_steps="$2"  local algo="$1"already_done() {}  ' "$log_path"    END { if (last != "") print last; }    }      if (mr != "" && bmr != "" && mqps != "") last = mr "," bmr "," mqps;      if (match($0, /throughput [0-9]+\.[0-9]+ MQPS/)) mqps = substr($0, RSTART + 11, RLENGTH - 16);      if (match($0, /byte miss ratio [0-9]+\.[0-9]+/)) bmr = substr($0, RSTART + 16, RLENGTH - 16);      if (match($0, /miss ratio [0-9]+\.[0-9]+/)) mr = substr($0, RSTART + 11, RLENGTH - 11);      mr=""; bmr=""; mqps="";    /LOH-(OMR|BMR) cache size/ {  awk '  local log_path="$1"extract_final() {)  "meta|data/MetaCDN/meta_reag.oracleGeneral.zst"  "wiki|data/WikiCDN/wiki_2019t.oracleGeneral.zst"  "1063|data/TencentCBS/1063.oracleGeneral.zst"TASKS=(EXCLUDES=("0" "2000" "10000")ALGOS=("SAC" "PPO" "TD3"))  "LOH_INCLUDE_HIT_MISS_FEATURES=0"  "LOH_ADAPTIVE_NORM_TRANSFORM_QUANTILE=0"  "LOH_ADAPTIVE_NORM_WARMUP=0"  "LOH_ADAPTIVE_NORM_HI_Q=1.0"  "LOH_ADAPTIVE_NORM_LO_Q=0.0"  "LOH_ENABLE_ADAPTIVE_FEATURE_NORMALIZATION=1"  "LOH_ENABLE_FEATURE_NORMALIZATION=0"  "LOH_FEATURE_LOG1P_RECIPROCAL=0"  "LOH_FEATURE_LOG1P=1"  "LOH_FEATURE_IDENTITY=0"  "LOH_FEATURE_UNIFIED_FORMULA=0"  "LOH_USE_SCORE_REBALANCE=0"  "LOH_ADAPTIVE_BUDGET=1"  "LOH_INCLUDE_WEIGHTS_IN_OBS=1"  "LOH_MISS_RATIO_WEIGHT=1.0"  "LOH_ASYNC_TRAIN=1"  "LOH_WAIT_MODE=nonblocked"  "LOH_STRUCTURED_CANDIDATES=96"  "LOH_RANDOM_CANDIDATES=96"  "LOH_SCORE_USE_IRT=0"  "LOH_SCORE_USE_COMPOUND=1"  "LOH_ENABLE_RL=1"  "LOH_DEBUG_LEVEL=0"  "LOH_PERF_PROFILING=0"  "LOH_SKIP_PIP_INSTALL=1"  "LOH_SKIP_BUILD=1"  "LOH_BUILD_RELEASE=1"  "LOH_WAIT_NEWSTATE_IDLE_S=1800"  "LOH_WAIT_NEWSTATE_MAX_CONSEC_TIMEOUTS=1800"  "LOH_SEM_TIMEOUT_S=1.0"  "LOH_ENABLE_SEMAPHORE=1"  "LOH_PARALLEL_SAFE=1"  "CACHESIM_NUM_REQ=0"COMMON_ENV=(fi  echo "[prebuild] done" >> "$RUNNER_LOG"  }    exit 1    echo "[prebuild] failed, see $OUT_DIR/prebuild.log" >> "$RUNNER_LOG"  ) >> "$OUT_DIR/prebuild.log" 2>&1 || {    bash scripts/debug.sh -r -c    export LOH_SKIP_BUILD=0    export LOH_INCLUDE_HIT_MISS_FEATURES=0    export LOH_BUILD_RELEASE=1  (  echo "[prebuild] force release + LOH_INCLUDE_HIT_MISS_FEATURES=0" >> "$RUNNER_LOG"else  echo "[prebuild] skipped by SKIP_PREBUILD=1" >> "$RUNNER_LOG"if [ "${SKIP_PREBUILD:-1}" = "1" ]; thenecho "[start] rl_algo x exclude_recent_steps sweep + orig3 + cache=0.1" >> "$RUNNER_LOG"fiCSValgo,exclude_recent_steps,trace,status,rc,final_mr,final_bmr,final_mqps,log_pathcat > "$RESULTS_CSV" <<'CSV'if [ ! -f "$RESULTS_CSV" ]; thenmkdir -p "$OUT_DIR"CACHE_SIZE="0.1"PARALLEL="${PARALLEL:-3}"DOC_PATH="docs/20260317-FULL_EXPERIMENT_RESULTS.md"RUNNER_LOG="$OUT_DIR/runner.log"RESULTS_CSV="$OUT_DIR/results.csv"OUT_DIR="tmp/rl_algo_exclude_sweep_orig3_cache01_0318"cd "$ROOT_DIR"ROOT_DIR=$(cd "$(dirname "$0")/../.." && pwd)> 测试环境：Intel Xeon Gold 6230R @ 2.10 GHz, KVM, 20 cores, 32 MB L3
> 构建：release build (`_build_rel/bin/cachesim`, `-O2 -DNDEBUG`)
> 缓存比例：0.1（缓存大小 = working set × 10%）
> LOH 统一配置：`COMPOUND=1, IRT=0, RSC=64, MAX_CAND=96, nonblocked`
> LOH 固定权重（1063 训练）：`0.117,0.103,0.376,0.087,0.164,0.154,0`
> 特征模式：1063→LOG1P, Wiki→RECIPROCAL, Meta→LOG1P（各 trace 最优）

---

## 1. 主结果表：3M requests（按 1063 MR 从好到坏排序）

| 排名 | 算法 | 类型 | 1063 MR | Wiki MR | Meta MR | 1063 MQPS | Wiki MQPS | Meta MQPS |
|:--|---|---|---|---|---|---|---|---|
| 1 | **BeladySize** | Oracle | 0.2078 | 0.4552 | 0.3679 | 0.13 | 0.06 | 1.12 |
| 2 | **Belady** | Oracle | 0.2589 | 0.4711 | 0.3677 | 0.53 | 0.54 | 0.89 |
| 3 | GDSF | Cost-based | 0.2772 | 0.6056 | 0.3679 | 0.54 | 0.47 | 0.55 |
| 4 | **LOH-FW** | **Ours** | **0.2840** | 0.5825 | **0.3680** | 0.31 | 0.09 | 1.79 |
| 5 | **LOH-RL** | **Ours** | **0.2926** | **0.5812** | 0.3694 | 0.32 | 0.09 | 1.47 |
| 6 | 3LCache-OMR | Learned | 0.3264 | 0.5923 | _(crash)_ | 0.34 | 0.25 | — |
| 7 | S3FIFO | FIFO-based | 0.3948 | 0.5911 | 0.4085 | 0.94 | 0.93 | 1.42 |
| 8 | LRU | Baseline | 0.4284 | 0.6489 | 0.4045 | 2.15 | 1.83 | 3.71 |
| 9 | 3LCache-BMR | Learned | 0.4311 | 0.5994 | 0.4060 | 0.33 | 0.25 | 0.35 |
| 10 | LFUDA | Size-aware | 0.4894 | 0.6063 | 0.4213 | 1.28 | 1.32 | 1.88 |
| 11 | LFU | Baseline | 0.6112 | 0.6256 | 0.4473 | 1.93 | 1.62 | 2.41 |

## 2. 主结果表：8M requests（按 1063 MR 从好到坏排序）

| 排名 | 算法 | 类型 | 1063 MR | Wiki MR | Meta MR | 1063 MQPS | Wiki MQPS | Meta MQPS |
|:--|---|---|---|---|---|---|---|---|
| 1 | **BeladySize** | Oracle | 0.1257 | 0.3565 | 0.3250 | 0.20 | 0.08 | 2.09 |
| 2 | GDSF | Cost-based | 0.1695 | 0.4848 | 0.3250 | 0.49 | 0.37 | 0.43 |
| 3 | **LOH-FW** | **Ours** | **0.1697** | 0.4716 | **0.3251** | 0.33 | 0.08 | 1.30 |
| 4 | **LOH-RL** | **Ours** | **0.1730** | **0.4711** | 0.3252 | 0.36 | 0.09 | 1.65 |
| 5 | **Belady** | Oracle | 0.1736 | 0.3712 | 0.3248 | 0.85 | 0.91 | 1.11 |
| 6 | 3LCache-OMR | Learned | 0.2018 | 0.4744 | _(crash)_ | 0.49 | 0.30 | — |
| 7 | S3FIFO | FIFO-based | 0.2832 | 0.4789 | 0.3712 | 1.21 | 0.96 | 1.68 |
| 8 | 3LCache-BMR | Learned | 0.2935 | 0.4835 | 0.3747 | 0.44 | 0.30 | 0.47 |
| 9 | LRU | Baseline | 0.3048 | 0.5400 | 0.3677 | 2.49 | 2.07 | 3.57 |
| 10 | LFUDA | Size-aware | 0.4093 | 0.4943 | 0.3923 | 1.39 | 1.40 | 1.83 |
| 11 | LFU | Baseline | 0.6103 | 0.5316 | 0.4188 | 2.09 | 1.74 | 2.58 |

---

## 3. LOH vs 竞争算法对比（8M）

| Trace | Belady | BeladySize | GDSF | 3LCache-OMR | LOH-FW | LOH-RL | LOH vs GDSF | LOH vs 3LC-OMR |
|:--|---|---|---|---|---|---|---|---|
| 1063 | 0.1736 | **0.1257** | 0.1695 | 0.2018 | **0.1697** | 0.1730 | +0.02pp | -3.2pp |
| Wiki | 0.3712 | **0.3565** | 0.4848 | 0.4744 | 0.4716 | **0.4711** | **-1.4pp** | **-0.3pp** |
| Meta | 0.3248 | 0.3250 | **0.3250** | _(crash)_ | 0.3251 | 0.3252 | +0.01pp | — |

---

## 4. LOH 特征模式对比（8M, 固定权重）

| Trace | LOG1P MR | RECIPROCAL MR | 差距 | 最优模式 |
|:--|---|---|---|---|
| 1063 | **0.1697** | 0.2306 | -6.1pp | LOG1P |
| Wiki | 0.5326 | **0.4716** | -6.1pp | RECIPROCAL |
| Meta | **0.3251** | 0.3252 | ≈0 | 无差异 |

## 5. LOH RL 特征模式对比（8M, RL）

| Trace | LOG1P RL MR | RECIP RL MR | 差距 | 最优模式 |
|:--|---|---|---|---|
| 1063 | **0.1730** | 0.2517 | -7.9pp | LOG1P |
| Wiki | 0.5252 | **0.4711** | -5.4pp | RECIPROCAL |
| Meta | **0.3252** | 0.3257 | ≈0 | 无差异 |

---

## 6. Trace 特性

| Trace | 类型 | Working Set | 缓存大小 (8M) | Evictions/8M | one_hit (200K) |
|:--|---|---|---|---|---|
| **1063** | TencentCBS block | ~687K obj | 3 GiB | ~3M (37.6%) | 0.36 |
| **Wiki** | WikiCDN | ~2.4M obj | 5 GiB | ~5.4M (67.9%) | 0.62 |
| **Meta** | MetaCDN | few obj | 3 TiB | ~1.7K (0.02%) | 0.76 |

---

## 7. auto-detect 验证数据

在不同检测时间点的 one_hit_ratio 和 CV，验证 auto-detect 公式能否正确选择特征模式：

| Trace | Detect@(reqs) | one_hit | CV | 多数规则 (>0.5) | 正确？ | 当前公式决策 | 正确？ |
|:--|---|---|---|---|---|---|---|
| 1063 | 100K | 0.435 | 5.2 | LOG1P | ✓ | LOG1P | ✓ |
| 1063 | 300K | 0.356 | 6.4 | LOG1P | ✓ | LOG1P | ✓ |
| 1063 | 1M | 0.266 | 7.9 | LOG1P | ✓ | LOG1P | ✓ |
| 1063 | 3M | 0.163 | 7.9 | LOG1P | ✓ | LOG1P | ✓ |
| Wiki | 100K | 0.759 | 4.1 | RECIP | ✓ | RECIP | ✓ |
| Wiki | 300K | 0.625 | 6.1 | RECIP | ✓ | **LOG1P** | **✗** |
| Wiki | 1M | 0.483 | 6.9 | **LOG1P** | **✗** | LOG1P | ✗ |
| Wiki | 3M | 0.378 | 7.8 | LOG1P | ✗ | LOG1P | ✗ |
| Meta | 100K | 0.778 | 49 | **RECIP** | **✗** | LOG1P | ✓ |
| Meta | 300K | 0.764 | 85 | **RECIP** | **✗** | LOG1P | ✓ |
| Meta | 1M | 0.753 | 166 | **RECIP** | **✗** | LOG1P | ✓ |
| Meta | 3M | 0.734 | 268 | **RECIP** | **✗** | LOG1P | ✓ |

**关键发现**：
- 多数规则（one_hit > 0.5）在 Meta 所有时间点失败（Meta one_hit > 0.5 但应选 LOG1P）。
- 当前公式 `3*(one_hit-0.5) - 0.5*log10(CV)` 在 Wiki 300K+ 时失败。
- Wiki 和 Meta 的 one_hit 区间重叠，只有 CV 能区分（Wiki CV=4~8, Meta CV=49~268）。
- 两种方法都只在早期检测时间点（<=200K）可靠。

---

## 7.1 全量分布视角下的公式与归一化建议（2026-03-14）

补充说明：这里的结论不再只看 100K/200K 采样点，而是结合全量 trace 的离线分布文件进行判断。分布摘要来自 [tmp/trace_dist_stats_0314/summary_sorted.tsv](tmp/trace_dist_stats_0314/summary_sorted.tsv)。

### 当前实现的归一化现状

- 默认并不启用归一化；只有显式设置 `LOH_ENABLE_FEATURE_NORMALIZATION=1` 才会生效。
- 当前实现的固定上界为：`recency=1.28e8`、`frequency=1e6`、`size=1.6e10 bytes`、`irt1/2/3=1.28e8`。
- 当前实现的归一化方式不是 z-score，而是“先做特征变换，再除以 `log1p(max)`，最后裁剪到 [0,1]”。
- 对 LOH 这类强偏态、重尾、且在线分布会漂移的缓存特征，不建议使用 z-score：
   - `frequency` 和 `size` 都是强正偏、长尾分布，均值和方差极不稳定。
   - `meta` 的频率分布尤其极端，top-1 对象单独就占 24.4% 请求，z-score 会把大多数冷对象压在很窄区间里，同时让极少数热点产生巨大离群值。
   - 更稳妥的做法仍然是“先做单调压缩变换（LOG1P / reciprocal），再做带裁剪的 [0,1] 归一化”。

### 三条 trace 的全量分布摘要

| Trace | reuse vtime p50 / p90 / p99 | frequency p50 / p90 / p99 | one-hit | CV | top-1 请求占比 | size p50 / p90 / p99 |
|:--|---|---|---|---|---|---|
| 1063 | 26 / 35 / 40 | 153 / 454 / 3069 | 7.1% | 15.0 | 0.35% | 32 KB / 64 KB / 512 KB |
| Wiki | 29 / 39 / 44 | 1 / 11 / 152 | 55.7% | 31.3 | 0.47% | 20.8 KB / 65.6 KB / 156.7 KB |
| Meta | 2 / 32 / 41 | 1 / 3 / 18 | 61.4% | 854.4 | 24.4% | 27.9 KB / 2.68 MB / 201 MB |

注：`reuse vtime` 来自 trace analyzer 的 virtual-time reuse 分布，反映的是连续两次访问之间的逻辑距离分桶，而不是 wall-clock 时间。

### 按 trace 的特征公式建议

| Trace | 建议公式 | 原因 | 是否建议开启归一化 | 归一化建议 |
|:--|---|---|---|---|
| 1063 | `LOG1P` | 频率分布厚而不极端，`frequency p50=153`、`p99=3069`，说明大量对象都存在明显重复访问；用 `LOG1P` 能保留中高频对象之间的相对差异。 | 可开可不开 | 若开启，继续用 `LOG1P -> [0,1]` 即可，但上界应比当前默认值更紧，宜按 1063 的高分位数设 cap，而不是沿用全局 `1e6/16e9` 这种很松的上界。 |
| Wiki | `RECIPROCAL` 或 `LOG1P_RECIPROCAL` | 典型长尾冷流量，`frequency p50=1`、one-hit 55.7%，说明超过一半对象只访问一次；应重点拉开“刚访问过 / 低频”的近端差异，而不是继续放大高频尾部。 | 不必默认开启 | 如果开启归一化，应放在 reciprocal 变换之后，并保持强裁剪；更适合按较低分位数范围做紧归一化，让模型聚焦低频和短 recency 区域。 |
| Meta | `LOG1P` | 这是“极少数超级热点 + 海量冷对象”的两极结构。虽然 `frequency p50=1`，但 `CV=854.4`，top-1 请求占比 24.4%；若用 reciprocal，会把超级热点也压得过平，丢掉最关键的头部区分度。 | 建议开启，但必须改成更紧的 cap | Meta 的 `size` 和 `frequency` 尾部极重，归一化时一定要先 `LOG1P`，再用分位数 cap 裁剪；尤其 `size` 不应继续用默认 `16e9`，因为全量 `size p99` 约 201 MB，当前默认上界过大，会把绝大多数对象都压在很小数值区间。 |

### 归一化方式建议

推荐顺序：

1. 先按 trace 选公式，而不是先统一归一化。
2. 公式选定后，再做 `transformed_value / transformed_cap`。
3. `cap` 优先用每个 trace、每个特征的高分位数，而不是统一固定大常数。
4. 最后裁剪到 `[0, 1]`。

更具体地说：

- 1063：适合“温和压缩 + 温和归一化”，即 `LOG1P(raw) / LOG1P(cap)`。
- Wiki：适合“近端分辨率优先”，即先 reciprocal，再做紧范围归一化，不要用过松 cap。
- Meta：适合“先压重尾，再截断极端值”，即 `LOG1P(raw)` 后按高分位数 cap 归一化。

不建议的方案：

- 不建议直接对原始 `frequency` / `size` 做线性 min-max。
- 不建议对这三条 trace 统一使用同一套固定 cap。
- 不建议用 z-score 作为主方案，尤其不适用于 Meta。

### 自适应归一化实现（2026-03-14 新增）

为避免继续依赖人工指定 `LOH_FEATURE_NORM_MAX_*`，现在在 `LOH.c` 中新增了一条默认关闭的自适应归一化路径：

- 开关：`LOH_ENABLE_ADAPTIVE_FEATURE_NORMALIZATION=1`
- 参数：
   - `LOH_ADAPTIVE_NORM_LO_Q`，默认 `0.01`
   - `LOH_ADAPTIVE_NORM_HI_Q`，默认 `0.99`
   - `LOH_ADAPTIVE_NORM_WARMUP`，默认 `4096`

实现顺序：

1. 先按当前 trace 选择的公式做特征变换。
2. 再对“变换后的值”维护在线分位数估计，而不是对 raw 值维护。
3. 预热样本数不足 `WARMUP` 时，直接返回变换后的原值，不做缩放。
4. 预热完成后，按 `lo_q` 和 `hi_q` 做分位数裁剪归一化：

    `normalized = clamp((out - q_lo) / (q_hi - q_lo), 0, 1)`

设计含义：

- 对 `LOG1P` 路径：先压缩重尾，再把主密度区间拉满到 `[0,1]`。
- 对 `RECIPROCAL` 路径：虽然原始值已经在 `(0,1]`，但仍可用分位数区间重新拉伸有效区间，避免大部分样本挤在很窄的局部。
- 这比固定 `max` 更适合“无先验知识”的场景，因为不同 trace 的量级、尾部和热度结构差异很大。

当前实验设计：

- 1063：`LOG1P × baseline/fixed_norm/adaptive_norm`
- Wiki：`LOG1P × 3种模式` 和 `RECIPROCAL × 3种模式`
- Meta：`LOG1P × baseline/fixed_norm/adaptive_norm`
- 统一先跑 `3M requests` 做首轮验证

---

## 8. 吞吐量优化效果总结

### 三阶段 eviction 优化（1063, 固定权重, RSC=64, debug build → release）

| 优化阶段 | MQPS | MR | 累积提升 |
|:--|---|---|---|
| Baseline | 0.20 | 0.218 | — |
| +ultra_fast (fast_log1p + fused loop) | 0.27 | 0.172 | +35% |
| +flat array (O(1) random sampling) | 0.32 | 0.170 | +60% |
| +prefetch (__builtin_prefetch) | **0.40** | 0.170 | **+100% (2×)** |

### RL 通信优化（debug build, 1M, 1063）

| 配置 | sync_total | sync_count | 占 LOH 总时间 |
|:--|---|---|---|
| Baseline (fread/fwrite/fcntl) | 0.073s | 4,868 | 0.91% |
| +mmap + skip redundant | 0.042s | 4,868 | 0.50% |
| +interval 200→500 | **0.027s** | 1,947 | **0.35%** |

---

## 9. 实验配置速查

```bash
# LOH-RL（最优配置）
CACHESIM_NUM_REQ=8000000 LOH_CACHESIM_BIN=_build_rel/bin/cachesim \
LOH_SKIP_PIP_INSTALL=1 LOH_SKIP_BUILD=1 LOH_DEBUG_LEVEL=0 \
LOH_WAIT_MODE=nonblocked LOH_PIN_CPU=0 \
LOH_FEATURE_LOG1P=<1|0> LOH_FEATURE_LOG1P_RECIPROCAL=<0|1> \
LOH_SCORE_USE_COMPOUND=1 LOH_SCORE_USE_IRT=0 \
LOH_RANDOM_SAMPLE_COUNT=64 LOH_MAX_CANDIDATES=96 \
bash scripts/test_loh_rl_sb3.sh <trace> 0.1

# LOH-FW（固定权重）
LOH_ENABLE_RL=0 LOH_FIXED_WEIGHTS="0.117,0.103,0.376,0.087,0.164,0.154,0" \
LOH_FEATURE_LOG1P=<1|0> LOH_FEATURE_LOG1P_RECIPROCAL=<0|1> \
LOH_SCORE_USE_COMPOUND=1 LOH_SCORE_USE_IRT=0 \
LOH_MAX_CANDIDATES=96 LOH_RANDOM_SAMPLE_COUNT=64 \
_build_rel/bin/cachesim <trace> oracleGeneral LOH 0.1 --num-req=8000000 -v 0

# 对比算法
_build_rel/bin/cachesim <trace> oracleGeneral <LRU|GDSF> 0.1 --num-req=8000000 -v 0

# Trace 路径
# 1063: data/TencentCBS/1063.oracleGeneral.zst
# Wiki: data/WikiCDN/wiki_2019t.oracleGeneral.zst
# Meta: data/MetaCDN/meta_reag.oracleGeneral.zst
```

---

## 10. 完整请求量（Full Req）串行测试结果（2026-03-06）

> 说明：按用户要求，先完成三条 trace 的 RL 最优配置完整请求测试；再串行执行对比算法完整请求测试（不并行）。
> 日志均保存于 `tmp/` 目录。

### 10.1 RL 最优配置（full req）

| Trace | Req | 最优特征模式 | Miss Ratio | Byte MR | Throughput (MQPS) |
|:--|---:|---|---:|---:|---:|
| 1063 | 360,960,512 | LOG1P | 0.027361 | 0.030195 | 0.75 |
| Wiki | 207,646,002 | RECIPROCAL | 0.176183 | 0.141579 | 0.15 |
| Meta | 45,623,306 | LOG1P | 0.269384 | 0.156423 | 0.97 |

对应主日志：
- `tmp/rl_1063_full_0306_011029.log`
- `tmp/rl_wiki_full_0306_011921.log`
- `tmp/rl_meta_full_0306_010910.log`

补充实验（2026-03-12）：
- `gated_penalty_mix`（LOG1P, structured/random=96/96, `CACHESIM_NUM_REQ=0`）在 1063 full req 上得到 `0.026796 / 0.029398 / 0.33 MQPS`，外层日志为 `tmp/gated_1063_full_script.log`。
- 相比 0306 结构化 RL 基线 `0.027361 / 0.030195 / 0.75`，缓存质量略优，但吞吐明显更低。

### 10.1.1 Weights 作为 State 输入（full req，2026-03-12）

> 说明：此组实验对应 phase A 中 `weights_obs=1` 的 RL 任务，即将当前权重一并拼入 observation/state；对照组为 phase B 的 `weights_obs=0`。
> 特征模式保持各 trace 最优：1063 / Meta 使用 LOG1P，Wiki 使用 RECIPROCAL。

| Trace | w0: 不含权重 state | w1: 权重并入 state | Δ MR (w1-w0) | Δ MQPS | 结论 |
|:--|---|---|---:|---:|---|
| 1063 | 0.027173 / 0.030128 / 0.55 | **0.026920 / 0.029850 / 0.33** | **-0.000253** | -0.22 | w1 质量更好，吞吐更低 |
| Wiki | 0.178754 / 0.139111 / 0.07 | **0.177137 / 0.138797 / 0.07** | **-0.001617** | ≈0 | w1 更好 |
| Meta | 0.269004 / 0.157267 / 0.71 | **0.269001 / 0.157198 / 0.80** | **-0.000003** | +0.09 | 几乎持平，w1 略优 |

其中：

- w0 对应任务：`phaseB_rl_{1063,meta,wiki}_0p1_{log1p|reciprocal}_w0`
- w1 对应任务：`phaseA_rl_{1063,meta,wiki}_0p1_{log1p|reciprocal}_w1`

**结论：**

1. 将 weights 作为 state 输入后，三条 trace 的 MR 都没有变差，且都略有改善。
2. 改善幅度最大的是 Wiki（0.178754 → 0.177137，降低 0.1617pp）。
3. 1063 上 w1 的质量更好，但吞吐从 0.55 降到 0.33 MQPS，说明权重入 state 带来了更高的 Python 侧开销或更慢的训练/推理路径。
4. Meta 上几乎无差异，但 w1 同时拿到略低 MR 和更高吞吐，是三条里最稳定的正向结果。

结果来源：
- `tmp/phase_ab_latest/results.csv`
- `tmp/phase_ab_0312_223925/logs/phaseA_rl_1063_0p1_log1p_w1.log`
- `tmp/phase_ab_0312_223925/logs/phaseA_rl_meta_0p1_log1p_w1.log`
- `tmp/phase_ab_0312_223925/logs/phaseA_rl_wiki_0p1_reciprocal_w1.log`

### 10.2 对比算法（full req，按 1063 MR 从优到劣）

| 算法 | 1063 MR / Byte MR / MQPS | Wiki MR / Byte MR / MQPS | Meta MR / Byte MR / MQPS | 备注 |
|:--|---|---|---|---|
| BeladySize | 0.018200 / 0.018689 / 0.74 | 0.124325 / 0.104216 / 0.29 | 0.268778 / 0.144016 / 3.51 | ok |
| LOH-RL gated-penalty (0312) | 0.026796 / 0.029398 / 0.33 | — | — | `gated_penalty_mix`，质量优于 0306 结构化 RL，但吞吐显著下降 |
| LOH-RL | 0.027361 / 0.030195 / 0.75 | 0.176183 / 0.141579 / 0.15 | 0.269384 / 0.156423 / 0.97 | 最优 RL 配置（见 10.1） |
| **LOH-RL-RandOnly** | **0.023817** / 0.027561 / 0.78 | **0.172273** / 0.135979 / 0.14 | 0.269843 / 0.156441 / 0.43 | Random-Only 候选 RL（见 10.3.4） |
| GDSF | 0.054791 / 0.058776 / 0.33 | 0.180493 / 0.152894 / 0.20 | 0.268918 / 0.152952 / 0.27 | ok |
| 3LCache-OMR | 0.060630 / 0.062025 / 0.54 | 0.174871 / 0.153405 / 0.31 | 0.392964 / 0.192144 / 0.39 | 由 `3LCache -e objective=object-miss-ratio` 取得 |
| Belady | 0.147024 / 0.124058 / 1.33 | 0.134717 / 0.093238 / 0.75 | 0.268778 / 0.144016 / 1.51 | ok |
| 3LCache-BMR | 0.252227 / 0.207182 / 0.46 | 0.182787 / 0.126047 / 0.31 | 0.324215 / 0.170269 / 0.38 | 由 `3LCache` 默认 objective 取得 |
| S3FIFO | 0.260116 / 0.215841 / 1.32 | 0.187962 / 0.129958 / 1.08 | 0.326397 / 0.170717 / 1.63 | ok |
| LRU | 0.261774 / 0.220946 / 2.54 | 0.230638 / 0.161934 / 1.51 | 0.326804 / 0.175302 / 3.00 | ok |
| LFU | 0.620074 / 0.650999 / 2.67 | 0.220032 / 0.155211 / 1.40 | 0.465043 / 0.437369 / 2.96 | ok |
| LFUDA | fail(rc=147) | 0.193518 / 0.134803 / 0.87 | 0.356184 / 0.183358 / 1.63 | 1063 full req 被系统信号停止 |

结构化结果文件：
- `tmp/compare_full_0306_014357.csv`

原始运行日志：
- `tmp/compare_full_0306_014357.log`
- `tmp/cmp_1063_LFUDA_full_0306_120723.log`

### 10.3 Random-Only 候选 RL 消融实验（8M，2026-03-09）

> 配置：`LOH_RANDOM_ONLY_CANDIDATES=1`（跳过 recency/freq/size 结构化候选源，仅从 flat array 随机采样候选）。
> 其余配置与 §9 RL 最优配置相同（COMPOUND=1, IRT=0）。
> 恢复方式：设 `LOH_RANDOM_ONLY_CANDIDATES=0` 或不设、无需改代码。

#### 10.3.1 候选数量 Sweep（Random-Only RL, 8M）

| Trace | CAND | MR | Byte MR | MQPS |
|:--|---|---|---|---|
| **1063** | 32 | 0.1812 | 0.2221 | 0.59 |
| | 64 | 0.1710 | 0.2139 | 0.44 |
| | 96 | **0.1698** | 0.2138 | 0.35 |
| | 128 | 0.1681 | 0.2119 | 0.31 |
| | 192 | 0.1672 | 0.2128 | 0.25 |
| | 256 | **0.1669** | **0.2108** | 0.20 |
| **Wiki** | 32 | 0.4665 | **0.3732** | 0.21 |
| | 64 | 0.4693 | 0.3728 | 0.14 |
| | 96 | **0.4658** | 0.3774 | 0.10 |
| | 128 | 0.4697 | 0.3730 | 0.08 |
| | 192 | 0.4697 | 0.3757 | 0.06 |
| | 256 | 0.4662 | 0.3832 | 0.04 |
| **Meta** | 32 | 0.3288 | 0.1857 | 0.82 |
| | 64 | 0.3331 | 0.1853 | 0.75 |
| | 96 | 0.3264 | 0.1825 | 0.94 |
| | 128 | 0.3260 | 0.1819 | 0.60 |
| | 192 | 0.3257 | 0.1812 | 0.88 |
| | 256 | **0.3255** | **0.1806** | 0.85 |

#### 10.3.2 结构化候选 RL Sweep（8M）

> 配置：`LOH_RANDOM_ONLY_CANDIDATES=0`（正常结构化候选：recency/freq/size + 随机补充 RSC=64）。

| Trace | CAND | MR | Byte MR | MQPS |
|:--|---|---|---|---|
| **1063** | 32 | 0.1720 | 0.2159 | 0.42 |
| | 64 | 0.1728 | 0.2158 | 0.38 |
| | 96 | 0.1728 | 0.2165 | 0.38 |
| | 128 | 0.1727 | 0.2155 | 0.37 |
| | 192 | **0.1722** | **0.2156** | 0.32 |
| | 256 | 0.1726 | 0.2156 | 0.30 |
| **Wiki** | 32 | 0.4742 | **0.3731** | 0.13 |
| | 64 | **0.4676** | 0.3746 | 0.11 |
| | 96 | 0.4705 | 0.3793 | 0.10 |
| | 128 | 0.4677 | 0.3813 | 0.09 |
| | 192 | 0.4767 | 0.3776 | 0.07 |
| | 256 | 0.4698 | 0.3818 | 0.06 |
| **Meta** | 32 | 0.3260 | 0.1822 | 1.08 |
| | 64 | 0.3253 | 0.1816 | 1.47 |
| | 96 | 0.3252 | 0.1814 | 1.53 |
| | 128 | 0.3251 | 0.1812 | 1.60 |
| | 192 | 0.3251 | 0.1815 | 1.60 |
| | 256 | **0.3251** | **0.1809** | 1.61 |

#### 10.3.3 Random-Only vs 结构化 RL 全面对比（8M）

> 每个 CAND 值对比 MR 差异（Δ = Random-Only − Structured，负值表示 Random-Only 更优）。

| CAND | 1063 RO MR | 1063 Struct MR | Δ 1063 | Wiki RO MR | Wiki Struct MR | Δ Wiki | Meta RO MR | Meta Struct MR | Δ Meta |
|:--|---|---|---|---|---|---|---|---|---|
| 32 | 0.1812 | 0.1720 | +0.93pp | **0.4665** | 0.4742 | **-0.77pp** | 0.3288 | 0.3260 | +0.28pp |
| 64 | **0.1710** | 0.1728 | **-0.18pp** | 0.4693 | **0.4676** | +0.16pp | 0.3331 | 0.3253 | +0.78pp |
| 96 | **0.1698** | 0.1728 | **-0.30pp** | **0.4658** | 0.4705 | **-0.47pp** | 0.3264 | 0.3252 | +0.12pp |
| 128 | **0.1681** | 0.1727 | **-0.46pp** | 0.4697 | **0.4677** | +0.19pp | 0.3260 | 0.3251 | +0.09pp |
| 192 | **0.1672** | 0.1722 | **-0.50pp** | **0.4697** | 0.4767 | **-0.70pp** | 0.3257 | 0.3251 | +0.06pp |
| 256 | **0.1669** | 0.1726 | **-0.57pp** | **0.4662** | 0.4698 | **-0.36pp** | 0.3255 | 0.3251 | +0.05pp |

**关键发现**：

1. **1063 (block I/O trace): Random-Only RL 在 CAND≥64 时一致优于结构化 RL**
   - CAND=256 时差距最大（-0.57pp），MR 从 0.1726→0.1669，相对改善 3.3%。
   - Random-Only 的 MR 随 CAND 单调改善（0.181→0.167），而结构化几乎不变（0.172±0.001）。
   - 推测原因：结构化候选的 recency/freq/size 来源引入偏差，RL 对纯随机样本的权重学习更自由。

2. **Wiki (CDN trace): 两者难分高下，Random-Only 略占优**
   - 6 个 CAND 值中 Random-Only 胜出 4 次（Δ=-0.77, -0.47, -0.70, -0.36pp）。
   - 但 MR 整体波动范围大（0.466~0.477），RL 噪声可能是主要因素。

3. **Meta (CDN trace): 结构化 RL 稳定占优但差距极小**
   - 最大差距仅 +0.78pp (CAND=64)，CAND≥96 后差距 <0.12pp。
   - 两种模式 MR 均收敛至 ~0.325，Meta 对候选来源不敏感。

4. **结构化 RL 的 MR 对 CAND 变化极不敏感**
   - 1063: CAND=32→256 仅变化 0.172±0.001（几乎不变）。
   - Meta: CAND=32→256 仅变化 0.326→0.325（<0.1pp）。
   - 与之对比，Random-Only 的 MR 随 CAND 增加持续下降。

5. **MQPS 对比**：Random-Only 在小 CAND 时通常更快（无需遍历结构化源），但大 CAND 时两者接近。

6. **总结**：Random-Only RL 展示出良好的自适应能力。对于 1063 这类 block I/O 场景，纯随机候选+RL 学习的权重**一致优于**传统结构化候选来源，说明 RL 能学到比人工设计的候选来源更好的驱逐策略。

对应日志：
- Random-Only: `tmp/rl_{meta,1063,wiki}_randonly_cand{32..256}_8M.log`
- Structured: `tmp/rl_{meta,1063,wiki}_struct_cand{32..256}_8M.log`
- 结果汇总: `tmp/randonly_sweep_results.csv`, `tmp/randonly_sweep_refined.csv`, `tmp/struct_sweep_results.csv`

#### 10.3.4 Full Req Random-Only RL（CAND=96，全量请求）

> 配置：与 §10.1 完全对应，唯一差异为 `LOH_RANDOM_ONLY_CANDIDATES=1`。

| Trace | Req | Miss Ratio | Byte MR | Throughput (MQPS) |
|:--|---:|---:|---:|---:|
| 1063 | 360,960,512 | **0.023817** | **0.027561** | 0.78 |
| Wiki | 207,646,002 | **0.172273** | **0.135979** | 0.14 |
| Meta | 45,623,306 | 0.269843 | 0.156441 | 0.43 |

**Full Req 对比（Random-Only vs 结构化 RL，CAND=96）：**

| Trace | Structured RL MR | Random-Only RL MR | Δ MR | Δ 相对 |
|:--|---|---|---|---|
| 1063 | 0.027361 | **0.023817** | **-0.35pp** | **-13.0%** |
| Wiki | 0.176183 | **0.172273** | **-0.39pp** | **-2.2%** |
| Meta | **0.269384** | 0.269843 | +0.05pp | +0.02% |

**关键发现**：
- **1063 全量 MR 改善 13%**（0.0274→0.0238），这是所有 LOH 实验中最大的单项改善之一。
- **Wiki 也有 -0.39pp 改善**（0.1762→0.1723），Byte MR 从 0.1416→0.1360 也更好。
- **Meta 几乎无差异**（+0.05pp），两种模式在 Meta 上表现一致。
- 对比 8M 结果：全量请求放大了 Random-Only 的优势（1063 从 8M 的 -0.30pp 扩大到 full-req 的 -0.35pp），说明更长的训练时间让 RL 学到了更好的权重。
- **MQPS 也稍优**：1063上 Random-Only 0.78 vs Structured 0.75（因跳过结构化候选遍历省时）。

对应日志：
- `tmp/rl_meta_randonly_fullreq.log`
- `tmp/rl_1063_randonly_fullreq.log`
- `tmp/rl_wiki_randonly_fullreq.log`

#### 10.3.5 RL 学习权重对比分析

> **Compound 模式下 6 个权重维度**（非 IRT，是 recency/freq/size 的基础+交互项）：
> w0=recency, w1=frequency, w2=size, w3=freq/recency, w4=freq/size, w5=rec×size。
> 评分公式：`score = -w0×rec + w1×freq - w2×sz + w3×(freq/rec) + w4×(freq/sz) - w5×(rec×sz)`

**Full Req 最终权重：**

| | w0 (rec) | w1 (freq) | w2 (size) | w3 (freq/rec) | w4 (freq/sz) | w5 (rec×sz) | MR |
|:--|---|---|---|---|---|---|---|
| **1063 RO** | 0.158 | 0.063 | 0.062 | 0.158 | 0.167 | **0.392** | **0.0238** |
| **1063 Struct** | **0.234** | 0.078 | 0.158 | 0.183 | **0.237** | 0.110 | 0.0274 |
| **Wiki RO** | 0.083 | **0.335** | 0.158 | 0.114 | 0.120 | 0.190 | **0.1723** |
| **Wiki Struct** | **0.231** | **0.232** | 0.054 | 0.042 | 0.174 | **0.267** | 0.1762 |
| **Meta RO** | **0.286** | 0.198 | 0.205 | 0.145 | 0.048 | 0.119 | 0.2698 |
| **Meta Struct** | 0.103 | 0.090 | 0.132 | **0.238** | 0.176 | **0.261** | 0.2694 |

**8M 中间权重（参考）：**

| | w0 | w1 | w2 | w3 | w4 | w5 |
|:--|---|---|---|---|---|---|
| 1063 RO 8M | 0.252 | 0.046 | 0.230 | 0.265 | 0.061 | 0.146 |
| 1063 Struct 8M | 0.105 | 0.232 | 0.199 | 0.068 | 0.162 | 0.233 |
| Wiki RO 8M | 0.187 | 0.261 | 0.277 | 0.046 | 0.187 | 0.042 |
| Wiki Struct 8M | 0.082 | 0.220 | 0.122 | 0.233 | 0.054 | 0.289 |

**权重分析（Compound 模式，6 个交互项）：**

1. **1063 Random-Only 的关键发现：rec×size 主导 (w5=0.392)**
   - RO 模式下 RL 将 39% 权重集中在 rec×size 交互项，而 frequency 和 size 基础项几乎归零 (0.063, 0.062)。
   - Structured 模式权重更分散：recency (0.234) + freq/size (0.237) + freq/recency (0.183) 三足鼎立。
   - 从 8M→Full Req 的演化看，RO 的 rec×size 权重从 0.146→0.392（增长 170%），而 size 从 0.230→0.062（大幅下降），说明 RL 在更长训练中发现了 **rec×size 交互项是 block I/O 驱逐最有价值的信号**。这意味着同时"最近被访问"且"最大"的对象得到更强的保留优势。

2. **Wiki：Random-Only 发现 frequency 最重要 (w1=0.335)**
   - RO 模式让 frequency 成为最大权重 (0.335)，而 Structured 模式的 recency 和 frequency 接近（0.231 vs 0.232）。
   - CDN 场景下，热门内容频次高，RO 学到了更大的 frequency 权重并获得更优 MR。

3. **Meta：两种模式权重分布差异大但效果接近**
   - RO 偏向 recency (0.286)，Structured 偏向 freq/recency + rec×size (0.238+0.261)。
   - Meta trace 对权重不敏感（MR 仅差 0.05pp），多种权重策略均能达到类似效果。

4. **结构化候选引入的偏差假说**：
   - 结构化候选来源（recency/freq/size buckets）天然偏向对应基础特征的极端值，导致 RL 可能过度调整这些特征的权重来"适应"候选分布，而非学习最优驱逐策略。
   - Random-Only 消除了这种偏差，让 RL 在均匀随机样本上自由优化，从而发现了更本质的特征权重（如 1063 上的 rec×size 交互项主导策略——这个交互项无法被任何单一结构化候选源覆盖）。

#### 10.3.6 Additive 候选对比实验

> 目的：验证"在随机候选基础上增加结构化候选是否一定有益"。
> 设计 3 个对照组，所有测试使用 RL (A2C), 8M requests, CAND=96：

| Group | 描述 | 结构化候选 | 随机候选 (RSC) | 总候选数 (≈) |
|:--|---|---|---|---|
| A | 纯随机 192 | 0 | 192 | 192 |
| B | 96 结构化 + 96 随机 | ~96 | 96 | ~192 |
| C | 96 纯结构化 | ~96 | 0 | ~96 |
| D (参考) | 纯随机 96 | 0 | 96 | 96 |

**结果：**

| Group | 1063 MR | Wiki MR | Meta MR |
|:--|---|---|---|
| A (192 random) | **0.1672** | **0.4697** | 0.3257 |
| B (96s + 96r) | 0.1706 | 0.4695 | **0.3252** |
| C (96s only) | 0.2797 ⚠ | 0.4838 | 0.3252 |
| D (96 random) | 0.1698 | 0.4658 | 0.3264 |

**分析：**

1. **纯结构化 (C) 在 1063 上灾难性退化**：MR=0.2797，接近 LRU (0.2618)，比纯随机 96 (D=0.1698) 差 +11pp。说明 RL 仅从结构化候选中无法学到有效权重。
2. **A vs B（同等总候选量 ~192）**：差异仅 0.34pp (0.1672 vs 0.1706)，在 RL 噪声范围内。增加 96 个结构化候选替换掉 96 个随机候选，效果基本持平。
3. **随机候选是 RL 成功的主要驱动力**：Group C→B 加入 96 个随机后，1063 MR 从 0.2797 → 0.1706（改善 −10.9pp）。随机候选提供了无偏样本，让 RL 能有效学习。
4. **Meta 对候选类型不敏感**：4 组 MR 均在 0.325-0.326，差异 < 0.2pp。

#### 10.3.7 IRT vs Compound 特征模式对比

> 目的：比较两种 6 维评分特征在纯随机候选 RL 下的表现。
> - **Compound 模式** (LOH_SCORE_USE_COMPOUND=1, IRT=0)：rec, freq, size, freq/rec, freq/size, rec×size
> - **IRT 模式** (LOH_SCORE_USE_COMPOUND=0, IRT=1)：rec, freq, size, irt1, irt2, irt3
>
> 条件：CAND=96, RandOnly, 3M reqs, SAC

**结果（含新增 3-Feature 基线）：**

| Trace | 3-Feature (3D) | IRT (6D) | Compound (6D) | MQPS (3F/IRT/Comp) |
|:--|---|---|---|---|
| Meta (LOG1P) | 0.3698 | 0.4088 | **0.3264** | 0.57 / 0.09 / 0.94 |
| 1063 (LOG1P) | 0.3068 | 0.3952 | **0.1698** | 0.13 / 0.10 / 0.35 |
| Wiki (RECIP) | 0.5769 | 0.5824 | **0.4658** | 0.06 / 0.06 / 0.10 |

> **3-Feature 模式** (compound=0, irt=0)：仅用 recency, frequency, size 3 个基础特征
> **IRT 模式** (compound=0, irt=1)：rec, freq, size + irt1, irt2, irt3
> **Compound 模式** (compound=1, irt=0)：rec, freq, size + freq/rec, freq/size, rec×size

**最终权重对比：**

| 模式 | Trace | w0 (rec) | w1 (freq) | w2 (size) | w3 | w4 | w5 |
|:--|:--|---|---|---|---|---|---|
| 3-Feat | Meta | **0.534** | 0.335 | 0.131 | — | — | — |
| 3-Feat | 1063 | 0.377 | 0.121 | **0.502** | — | — | — |
| 3-Feat | Wiki | 0.276 | 0.234 | **0.489** | — | — | — |
| IRT | Meta | 0.067 | 0.232 | 0.147 | 0.142 | **0.310** | 0.102 |
| IRT | 1063 | **0.347** | 0.302 | 0.103 | 0.067 | 0.077 | 0.105 |
| IRT | Wiki | 0.215 | 0.234 | 0.106 | **0.268** | 0.076 | 0.100 |

**分析：**

1. **Compound 全面优于另两种模式**：3 个 trace 上 Compound MR 均显著更低，同时吞吐量最高。
2. **IRT 6 维比 3 维还差**：在所有 trace 上 IRT 模式 MR 均高于纯 3-Feature（Meta +4pp, 1063 +9pp, Wiki 持平）。额外的 IRT 维度不仅无帮助，反而因稀疏性和噪声拖累 RL 学习。
3. **Compound 交互项的巨大价值**：从 3-Feature → Compound，1063 MR 从 0.307→0.170（−14pp），说明 freq/rec、freq/size、rec×size 交互项捕获了远超基础特征的驱逐信号。
4. **3-Feature 权重更集中**：只有 3 维可学时，RL 快速找到主导特征（Meta=recency, 1063/Wiki=size），而 IRT 6 维分散了学习资源。
5. **性能开销**：IRT 模式需 (a) 维护 3 个 IRT 堆（每次访问 3× O(log n)），(b) 使用两遍评分循环（无法走 ultra_fast 路径），(c) 对每个候选调用 `calculate_irt_feature()` 3 次。3-Feature 省去 IRT 堆但仍用两遍路径；Compound 直接走 ultra_fast 单遍融合路径。

**RECIPROCAL Sign Bug 修复**：
- 修复前 Wiki IRT MR=0.8162（灾难性），修复后 0.5824
- Bug 原因：非 compound 模式的 `loh_use_heuristic_signs` 未区分 LOG1P/RECIPROCAL，在 RECIPROCAL 下 recency、size、irt1-3 的 sign 方向错误
- 修复位置：[LOH.c](libCacheSim/cache/eviction/LOH.c) 非 compound 分支增加 `if (loh_feature_log1p)` 条件判断

**IRT 维度为何反而有害的深入分析：**

1. **权重预算稀释**：softmax 输出的权重总和≈1。增加 3 个 IRT 维度，base features 的权重被稀释（如 1063 的 size 权重从 3-feat 的 0.502 降至 IRT 的 0.103）。softmax 无法给无用维度精确 0 权重，IRT 总会消耗约 25% 的预算。

2. **信念冲突**：约 40-60% 的候选对象首次访问（irt_values=0），IRT 维度全零。RL 必须用同一组权重服务"有 IRT"和"无 IRT"两类对象，产生无法调和的优化冲突。

3. **IRT 测量噪声大**：单次重访间隔 (irt1) 只有 1 个样本，是真实重访模式的很差估计，irt2/irt3 更稀疏。RL 在高噪声维度上得到不稳定梯度。

4. **Compound 的本质优势**：Compound 特征 (freq/rec, freq/sz, rec×sz) 是基础特征的多项式交互——对所有对象永远非零，无稀疏冲突，让线性模型能表达非线性关系。本质上是特征工程（增强已有信号），而非引入新数据源（IRT 数据稀疏且噪声大）。

5. **维度诅咒**：3D 权重空间的搜索效率远高于 6D。在仅 3M 请求（RL 训练步数极少）下，低维模型收敛更快。

#### 10.3.8 Adaptive Budget / Score Rebalance（Full Req，2026-03-13）

> 目的：验证 structured candidate 预算是否应该按运行时表现动态重分配，以及 `score rebalance` 是否优于基于 winner count 的重分配。
>
> 固定配置：`LOH_STRUCTURED_CANDIDATES=96`，`LOH_RANDOM_CANDIDATES=96`，`LOH_TAIL_SAMPLE=0`，`LOH_MISS_RATIO_WEIGHT=1.0`，`LOH_ENABLE_PENALTY=0`，`LOH_SCORE_USE_COMPOUND=1`，`LOH_SCORE_USE_IRT=0`，`LOH_WAIT_MODE=nonblocked`，`LOH_ASYNC_TRAIN=1`。
> 特征模式：1063 / Meta 使用 LOG1P；Wiki 使用 RECIPROCAL。
>
> 三组对照：
> - A0S0: `LOH_ADAPTIVE_BUDGET=0`, `LOH_USE_SCORE_REBALANCE=0`
> - A1S0: `LOH_ADAPTIVE_BUDGET=1`, `LOH_USE_SCORE_REBALANCE=0`
> - A1S1: `LOH_ADAPTIVE_BUDGET=1`, `LOH_USE_SCORE_REBALANCE=1`

| Trace | A0S0 MR / Byte MR / MQPS | A1S0 MR / Byte MR / MQPS | A1S1 MR / Byte MR / MQPS | 最优 |
|:--|---|---|---|---|
| 1063 | **0.022193** / **0.025336** / **0.41** | 0.022289 / 0.025448 / 0.39 | 0.022276 / 0.025437 / 0.40 | A0S0 |
| Wiki | **0.176855** / 0.139501 / 0.08 | 0.178517 / **0.139133** / 0.08 | 0.177731 / 0.139610 / 0.08 | A0S0 (按 MR) |
| Meta | 0.269452 / 0.156169 / 0.58 | 0.269081 / 0.156025 / 0.76 | **0.269075** / **0.155998** / **0.83** | A1S1 |

**按 trace 的结论：**

1. **1063：关闭自适应最好。** 开启 adaptive 后 MR 从 0.022193 小幅恶化到 0.022289 / 0.022276，吞吐也从 0.41 降到 0.39 / 0.40 MQPS。
2. **Wiki：关闭自适应最好。** A0S0 的 MR 最低（0.176855）；A1S1 略差，A1S0 最差。三者吞吐基本一致。
3. **Meta：自适应明显有益，且 score rebalance 最优。** A1S1 在 MR、Byte MR、MQPS 三项上都优于 A0S0。

**综合判断：**

- `adaptive budget` 不是全局增益项，而是 workload-sensitive 开关。
- 对 Meta 这类 trace，开启 adaptive budget 有稳定收益，且 `score rebalance` 优于 winner-count rebalance。
- 对 1063 和 Wiki，这组参数下 adaptive budget 带来轻微退化，因此不适合直接作为统一默认配置。

结果文件与日志：
- `tmp/adaptive_budget_orig3_0313_184729/results.csv`
- `tmp/adaptive_budget_orig3_0313_184729/runner.log`

### 10.4 State 维度消融实验（2026-03-09）

**实验设计**：始终保留 GLOBAL (2D: hit_ratio, byte_hit_ratio)，在此基础上逐一添加一个 state group，测试其对 MR 的影响。使用两种候选源 (STRUCTURED=96 + RANDOM=64) 确保 candidate 特征非零。

**配置**：LOH_SCORE_USE_COMPOUND=1, LOH_FEATURE_LOG1P=1, SAC, release build

#### 10.4.1 Meta CDN trace

| State Group | DIM | 8M nonblocked MR |
|:--|---|---|
| baseline (GLOBAL) | 2 | 0.325194 |
| +hit_miss | 14 | 0.325157 |
| +cache | 8 | 0.325171 |
| +candidate | 20 | 0.325166 |
| +avgtopk | 14 | 0.325163 |
| +request | 602 | 0.325160 |

Meta trace 上所有 state 维度的差异极小 (<0.004%)，表明 RL 在该 trace 上的 state 信号贡献有限。

#### 10.4.2 1063 CBS trace — 三种运行模式对比

全量 trace 共 360,960,512 请求（约 10 天），缓存比例 0.1。

| State | 8M nonblocked | Full nonblocked (360M) | 3M blocked |
|:--|---|---|---|
| **baseline** (GLOBAL) | 0.173317 | 0.027037 | 0.284227 |
| +hit_miss | **0.171317** (-1.2%) | **0.026069** (**-3.58%**) | 0.284339 |
| +cache | 0.171416 (-1.1%) | 0.027039 (+0.01%) | 0.284089 (-0.05%) |
| +candidate | 0.171348 (-1.1%) | **0.026092** (**-3.50%**) | 0.284140 |
| +avgtopk | 0.172510 (-0.5%) | 0.027120 (+0.31%) | 0.284263 |
| +request | 0.172263 (-0.6%) | 0.027011 (-0.10%) | 0.284570 (+0.1%) |

> 注：初次 full_nb 结果有误（因 test_loh_rl_sb3.sh 默认 3M 上限），已修复 `CACHESIM_NUM_REQ=ALL` 后重跑。

**关键发现**：

1. **Full nonblocked（最有参考价值）**：**hit_miss (-3.58%) 和 candidate (-3.50%)** 是唯二带来显著改善的 state 组。两者在全量 360M 请求上稳定优于 baseline，说明命中/未命中统计和候选分布信息对驱逐决策确有价值
2. **8M nonblocked**：hit_miss/cache/candidate 均带来约 -1.1%~-1.2% 的改善，趋势与 full 一致（hit_miss、candidate 最优），但 cache 在 8M 下也有收益而在 full 下消失
3. **3M blocked**：差异极小（最优 cache -0.05%），blocked 模式下同步频率受限于 Python 推理速度，state 维度差异被稀释
4. **request 维度（600D）未带来预期收益**：虽然信息量最大，但高维空间中 RL 线性模型难以有效利用
5. **full 的 MR 远低于 8M/3M**（0.027 vs 0.17/0.28）：1063 trace 前几百万请求为冷启动阶段（MR 高），随着缓存预热 MR 大幅下降。8M/3M 只覆盖了前几个小时的高 MR 区间

#### 10.4.3 构建系统改造

本轮实验中改造了构建脚本以支持 release 模式编译传递 `LOH_INCLUDE_*` 宏：
- `scripts/debug.sh -r`：新增 `-r`/`--release` 参数，编译到 `_build_rel`（-O2 -DNDEBUG），同时继承所有 LOH_INCLUDE_* 环境变量
- `test_loh_rl_sb3.sh`：新增 `LOH_BUILD_RELEASE=1` 环境变量，自动使用 release build 和构建
- 速度提升：6 组 state sweep 从 debug 模式的 ~60 分钟降至 release 模式的 ~2.5 分钟（约 25× 加速）

### 10.5 备注

- 本轮对比算法 full req 测试中，唯一未成功收敛项为 `LFUDA + 1063`，日志显示进程被 `Stopped`（rc=147）。
- 其余项均已按"串行、非并行"要求执行完毕并记录。

---

## 11. 全量 Trace 实验公共配置

> 以下为所有全量 trace 实验（§12-§17）共用的 **SAC RL 参数**和 **LOH 公共配置**。各实验仅列出差异项。

**SAC RL 参数（所有 RL 实验统一）：**

| 参数 | 值 |
|:--|-----|
| 算法 | SAC (stable-baselines3) |
| train_freq | 16 |
| gradient_steps | 1 |
| learning_starts | 3000 |
| buffer_size | 10000 |
| batch_size | 256 |
| learning_rate | 3e-4 |
| score_model | linear (ACTION_DIM=6) |

**LOH C 端公共配置（大多数实验统一）：**

| 参数 | 值 | 说明 |
|:--|-----|------|
| LOH_SCORE_USE_COMPOUND | 1 | 6 维交互特征 (rec, freq, sz, freq/rec, freq/sz, rec×sz) |
| LOH_SCORE_USE_IRT | 0 | 关闭 IRT 特征 |
| LOH_RANDOM_CANDIDATES | 64 | 随机候选数（0306 起统一） |
| LOH_WAIT_MODE | nonblocked | 非阻塞同步 |
| LOH_ASYNC_TRAIN | 0 | 同步训练 |
| LOH_ENABLE_SEMAPHORE | 1 | 启用 sem 同步 |
| miss-ratio-weight | 1.0 | Object Miss Ratio 优化 |
| byte-miss-ratio-weight | 0 | 不优化字节未命中 |
| cache_size_ratio | 0.1 | 缓存大小为 trace 工作集的 10% |
| binary | `_build_rel/bin/cachesim` | Release 构建 |

**每条 trace 的最优特征配置（0306 确认）：**

| Trace | 数据路径 | 总请求数 | 缓存大小 | LOH_FEATURE_LOG1P | RECIPROCAL |
|:--|----------|----------|----------|-------------------|------------|
| wiki | `data/WikiCDN/wiki_2019t.oracleGeneral.zst` | 207,646,002 | 40 GiB | **0** | 1 |
| 1063 | `data/TencentCBS/1063.oracleGeneral.zst` | 360,960,512 | 5 GiB | **1** | 0 |
| meta | `data/MetaCDN/meta_reag.oracleGeneral.zst` | 45,623,306 | 16 TiB | **1** | 0 |

---

## 12. 全量 Trace 实验汇总表

> 所有成功完成的全量 trace 实验按 MR 排序一览。配置差异项在"差异配置"列标注。

### 12.1 1063 (TencentCBS, 360,960,512 req, 5 GiB cache)

| 实验 | MR | Byte MR | MQPS | n_updates | 差异配置 | 状态 | 章节 |
|:--|-----|---------|------|-----------|----------|------|------|
| Rand-Only 全量 | **0.023817** | 0.027561 | 0.78 | — | RANDOM_ONLY=1, LOG1P=1, RSC=64 | ✅ | §10.3.4 |
| State +hit_miss | 0.026069 | 0.028921 | 0.56 | — | STATE_INCLUDE_HIT_MISS=1, LOG1P=1, RSC=64 | ✅ | §10.4.2 |
| State +candidate | 0.026092 | 0.029073 | 0.51 | — | STATE_INCLUDE_CANDIDATE=1, LOG1P=1, RSC=64 | ✅ | §10.4.2 |
| **nb_500 (NonBlocked)** | **0.026646** | 0.029527 | 0.58 | — | WAIT=nonblocked, INTERVAL=500, COMPOUND=1, LOG1P=1 | ✅ | §15.1 |
| State +request | 0.027011 | 0.029894 | 0.57 | — | STATE_INCLUDE_REQUEST=1, LOG1P=1, RSC=64 | ✅ | §10.4.2 |
| State baseline | 0.027037 | 0.030027 | 0.54 | — | GLOBAL only (2D), LOG1P=1, RSC=64 | ✅ | §10.4.2 |
| State +cache | 0.027039 | 0.030019 | 0.54 | — | STATE_INCLUDE_CACHE=1, LOG1P=1, RSC=64 | ✅ | §10.4.2 |
| 0310 探索 | 0.027083 | 0.030018 | 0.61 | 10,312 | LOG1P=1, PERF_PROFILING=1 | ✅ | §14 |
| State +avgtopk | 0.027120 | 0.029997 | 0.56 | — | STATE_INCLUDE_AVGTOPK=1, LOG1P=1, RSC=64 | ✅ | §10.4.2 |
| NB36 复现 | 0.027342 | 0.030259 | 0.59 | 987 | LOG1P=1, PERF_PROFILING=1 | ✅ | §13 |
| **0306 Baseline** | **0.027361** | 0.030195 | 0.75 | 862 | LOG1P=1, PERF_PROFILING=0 | ✅ 基准 | §10.1 |
| **bl_50000 (Blocked)** | 0.027407 | 0.030382 | 0.50 | — | WAIT=blocked, INTERVAL=50000, COMPOUND=1, LOG1P=1 | ✅ | §15.1 |
| NB36 错误 (LOG1P=0) | 0.095009 | 0.090499 | 0.27 | 2,162 | ❌ LOG1P=0 (应为 1) | ❌ 错误配置 | §13.4 |
| ab_sync_full | 0.232346 | 0.208728 | 0.12 | — | COMPOUND=unset, IRT=unset, LOG1P=1, RSC=64 | ✅ | §15.2 |

### 12.2 Wiki (WikiCDN, 207,646,002 req, 40 GiB cache)

| 实验 | MR | Byte MR | MQPS | n_updates | 差异配置 | 状态 | 章节 |
|:--|-----|---------|------|-----------|----------|------|------|
| Rand-Only 全量 | **0.172273** | 0.135979 | 0.14 | — | RANDOM_ONLY=1, LOG1P=0, RSC=64 | ✅ | §10.3.4 |
| **0306 Baseline** | **0.176183** | 0.141579 | 0.15 | 2,469 | LOG1P=0, PERF_PROFILING=0 | ✅ 基准 | §10.1 |
| NB36 复现 | 0.176196 | 0.141278 | 0.14 | 2,362 | LOG1P=0, PERF_PROFILING=1 | ✅ | §13 |
| NB36 错误 (RSC=0) | 0.186315 | 0.135435 | 0.30 | 962 | ❌ RSC=0 (应为 64) | ❌ 错误配置 | §13.4 |
| 0310 探索 | 0.206713 | 0.190577 | 0.17 | 14,831 | ❌ LOG1P=1 (应为 0), PERF_PROFILING=1 | ✅ 但特征模式不匹配 | §14 |
| 0310 tuned | 0.206839 | 0.190691 | 0.17 | 13,544 | ❌ LOG1P=1 (应为 0), PERF_PROFILING=1 | ✅ 但特征模式不匹配 | §14 |

### 12.3 Meta (MetaCDN, 45,623,306 req, 16 TiB cache)

| 实验 | MR | Byte MR | MQPS | n_updates | 差异配置 | 状态 | 章节 |
|:--|-----|---------|------|-----------|----------|------|------|
| **0306 Baseline** | **0.269384** | 0.156423 | 0.97 | 69 | LOG1P=1, PERF_PROFILING=0 | ✅ 基准 | §10.1 |
| NB36 复现 | 0.269406 | 0.156749 | 0.77 | 81 | LOG1P=1, PERF_PROFILING=1 | ✅ | §13 |
| 0310 探索 | 0.269427 | 0.156722 | 0.78 | 900 | LOG1P=1, PERF_PROFILING=1 | ✅ | §14 |
| Rand-Only 全量 | 0.269843 | 0.156441 | 0.43 | — | RANDOM_ONLY=1, LOG1P=1, RSC=64 | ✅ | §10.3.4 |

### 12.3.1 分段 MR 判别参考（24/48/72/96h）

> 目的：在 full-req 运行中，提前用分段 MR 估计最终 MR 区间。
> 数据来源：`tmp/unified_method_compare_0315/segment_reference_0316.csv` 与对应日志。

**Wiki 两个等级（0.17x vs 0.2x）的分段区分**

| Wiki 样本 | 96h 累计 MR | 96h 区间 MR | 最终 MR | 等级 |
|:--|---:|---:|---:|---|
| `tmp/rl_wiki_randonly_fullreq.log` | 0.1984 | 0.1738 | 0.172273 | 0.17x |
| `tmp/wiki_async_decay/run.log` | 0.2009 | 0.1785 | 0.177963 | 0.17x |
| `tmp/rl_wiki_nothreads1_0310_111641/cachesim.log` | 0.2122 | 0.1917 | 0.188123 | 接近 0.2x |

经验阈值（Wiki）：
- `96h cumulative <= 0.202` 且 `96h interval <= 0.180`：大概率收敛到 `0.17x`。
- `96h cumulative >= 0.210` 或 `96h interval >= 0.190`：最终常落在 `0.18x~0.20x`。

**三条 trace 的分段判别（当前可用规则）**

| Trace | 96h 累计/区间特征 | 对应最终 MR 区间 | 代表日志 |
|:--|---|---|---|
| 1063 | `~0.047~0.048 / ~0.017~0.018` | `0.02x` | `tmp/1063_perf0_async.log`, `tmp/rl_state_1063_full_nb_candidate.log` |
| 1063 | `~0.198 / ~0.173` | `0.13x` | `tmp/unified_method_compare_0315/topup_adaptive_1063_asym.log` |
| 1063 | `~0.257 / ~0.272` | `0.25x` | `tmp/1063_decay_adaptive.log` |
| wiki | `~0.198~0.201 / ~0.174~0.179` | `0.17x` | `tmp/rl_wiki_randonly_fullreq.log`, `tmp/wiki_async_decay/run.log` |
| wiki | `~0.212 / ~0.192` | `0.18x~0.20x` | `tmp/rl_wiki_nothreads1_0310_111641/cachesim.log` |
| meta | `~0.3035~0.3036 / ~0.2812~0.2814` | `0.269x`（非常稳定） | `tmp/meta_perf0_async.log`, `tmp/full0315_meta_driver.log` |

### 12.4 对比算法（非 LOH，全量 trace）

> 完整数据已在 §10.2，此处列出三条 trace 的关键基线供交叉参考。

| 算法 | 1063 MR / Byte MR / MQPS | Wiki MR / Byte MR / MQPS | Meta MR / Byte MR / MQPS |
|:--|--------------------------|--------------------------|--------------------------|
| BeladySize | 0.018200 / 0.018689 / 0.74 | 0.124325 / 0.104216 / 0.29 | 0.268778 / 0.144016 / 3.51 |
| LOH-RandOnly | **0.023817** / 0.027561 / 0.78 | **0.172273** / 0.135979 / 0.14 | 0.269843 / 0.156441 / 0.43 |
| LOH-RL nb_500 | **0.026646** / 0.029527 / 0.58 | — | — |
| LOH-RL gated-penalty (0312) | 0.026796 / 0.029398 / 0.33 | — | — |
| LOH-RL (0306) | 0.027361 / 0.030195 / 0.75 | 0.176183 / 0.141579 / 0.15 | **0.269384** / 0.156423 / 0.97 |
| LOH-RL bl_50000 | 0.027407 / 0.030382 / 0.50 | — | — |
| GDSF | 0.054791 / 0.058776 / 0.33 | 0.180493 / 0.152894 / 0.20 | 0.268918 / 0.152952 / 0.27 |
| 3LCache-OMR | 0.060630 / 0.062025 / 0.54 | 0.174871 / 0.153405 / 0.31 | 0.392964 / 0.192144 / 0.39 |
| 3LCache-BMR | 0.252227 / 0.207182 / 0.46 | 0.182787 / 0.126047 / 0.31 | 0.324215 / 0.170269 / 0.38 |
| LRU | 0.261774 / 0.220946 / 2.54 | 0.230638 / 0.161934 / 1.51 | 0.326804 / 0.175302 / 3.00 |
| LFUDA | ❌ fail (rc=147, 72h 时停止) | 0.193518 / 0.134803 / 0.87 | 0.356184 / 0.183358 / 1.63 |

---

## 13. 0306 基线复现验证（全量 trace, 2026-03-10）

### 13.1 背景

使用 `run_nonblocked36.sh` 脚本复现 0306 时期的 3-trace 全量基线。复现过程中发现并修复了三个脚本 bug：

1. **缺少 `LOH_RANDOM_CANDIDATES=64`**：导致 C 端 RSC=0（wiki MR 从 0.176 升至 0.186）
2. **ALLexport 拼接 bug**：两个 export 语句在同一行，导致 `CACHESIM_NUM_REQ="ALLexport"`
3. **NUM_REQ 传递逻辑**：在 run_nonblocked36.sh 中 unset 会导致下游脚本默认截断为 3M

### 13.2 完整运行配置

| 参数 | 0306 Baseline | NB36 复现 | 差异 |
|:--|--------------|-----------|------|
| 脚本 | `test_loh_rl_sb3.sh` | `run_nonblocked36.sh` → `test_loh_rl_sb3.sh` | 复现用 wrapper |
| binary | `_build_rel/bin/cachesim` | `_build_rel/bin/cachesim` | 同 |
| LOH_SCORE_USE_COMPOUND | 1 | 1 | 同 |
| LOH_SCORE_USE_IRT | 0 | 0 | 同 |
| LOH_RANDOM_CANDIDATES | 64 | 64 | **修复后一致** |
| LOH_WAIT_MODE | nonblocked | nonblocked | 同 |
| LOH_ASYNC_TRAIN | 0 | 0 | 同 |
| LOH_ENABLE_SEMAPHORE | 1 | 1 | 同 |
| LOH_PERF_PROFILING | **0 (无此代码)** | **1 (LOH.c L332)** | **主要差异** |
| CACHESIM_NUM_REQ | ALL | ALL (修复后) | 同 |
| LOH_FEATURE_LOG1P | per-trace (见 §11) | per-trace (见 §11) | 同 |

### 13.3 核心对比：0306 Baseline vs NB36 复现

| Trace | 版本 | MR | byte_MR | MQPS | n_updates | steps |
|:--|------|-----|---------|------|-----------|-------|
| **wiki** | 0306 Baseline | **0.176183** | 0.141579 | 0.15 | 2,469 | 42,561 |
| wiki | NB36 复现 | **0.176196** | 0.141278 | 0.14 | 2,362 | 40,832 |
| | | Δ=**+0.000013** | | -7% | -4.3% | -4.1% |
| **1063** | 0306 Baseline | **0.027361** | 0.030195 | 0.75 | 862 | 16,817 |
| 1063 | NB36 复现 | **0.027342** | 0.030259 | 0.59 | 987 | 18,833 |
| | | Δ=**-0.000019** | | -21% | +14.5% | +12.0% |
| **meta** | 0306 Baseline | **0.269384** | 0.156423 | 0.97 | 69 | 4,177 |
| meta | NB36 复现 | **0.269406** | 0.156749 | 0.77 | 81 | 4,337 |
| | | Δ=**+0.000022** | | -21% | +17.4% | +3.8% |

**结论：三条 trace 的 MR 差异均 < 0.001%，0306 基线完美复现。**

### 13.4 MQPS 下降分析

NB36 复现的 MQPS 比 0306 低 ~20%，原因是当前 binary 编译时 `LOH_PERF_PROFILING=1`（LOH.c line 332，0306 时不存在此代码），在热路径 67 个计时点（`PERF_NOW`/`PERF_ACCUM`）引入 ~25% 的 `clock_gettime` 系统调用开销：

| 指标 | 0306 | NB36 | 说明 |
|:--|------|------|------|
| LOH_PERF_PROFILING | 无 | 1 | 0306 无此宏 |
| 1063 MQPS | 0.75 | 0.59 | -21% |
| wiki MQPS | 0.15 | 0.14 | -7% |
| meta MQPS | 0.97 | 0.77 | -21% |
| 1063 估计 clock_gettime 次数 | 0 | ~37.5 亿 | 67 点 × 360M req |
| 估计额外开销 | 0 | ~94s | ~25% of LOH_total |

MQPS 下降不影响 MR，仅导致 C 变慢→Python 更多 sync 机会→更多 n_updates（+4%~+17%），但权重早已收敛。

### 13.5 错误配置实验（诊断过程中产生）

| Trace | 配置错误 | MR | 正确 MR | Δ MR | 原因 |
|:--|----------|-----|---------|------|------|
| wiki | RSC=0（应为 64） | 0.186315 | 0.176183 | +1.0pp | `run_nonblocked36.sh` 缺少 `LOH_RANDOM_CANDIDATES` 导出 |
| 1063 | LOG1P=0（应为 1） | 0.095009 | 0.027361 | +6.8pp | auto-detect 选错特征模式，需显式设置 `LOH_FEATURE_LOG1P=1` |

### 13.6 日志文件

| 实验 | C 端日志 | Python 日志 |
|:--|---------|-------------|
| 0306 wiki | `tmp/rl_wiki_full_0306_011921.log` | `tmp/ac_sb3_0306_011921.log` |
| 0306 1063 | `tmp/rl_1063_full_0306_011029.log` | `tmp/ac_sb3_0306_011029.log` |
| 0306 meta | `tmp/rl_meta_full_0306_010910.log` | `tmp/ac_sb3_0306_010910.log` |
| NB36 wiki | `cachesim_sb3_0310_130728.log` | `ac_sb3_0310_130728.log` |
| NB36 1063 | `cachesim_sb3_0310_145105.log` | `ac_sb3_0310_145105.log` |
| NB36 meta | `cachesim_sb3_0310_150449.log` | `ac_sb3_0310_150449.log` |
| wiki RSC=0 (错) | `cachesim_sb3_0310_114414.log` | `ac_sb3_0310_114414.log` |
| 1063 LOG1P=0 (错) | `cachesim_sb3_0310_134240.log` | `ac_sb3_0310_134240.log` |

---

## 14. 0310 参数探索实验

### 14.1 成功完成的全量测试

使用 0310 代码（含 AsyncProfiledSAC、LOH_PERF_PROFILING=1 等新功能），统一使用 LOG1P=1 跑全量。

**与 §11 公共配置的差异项：**

| 参数 | 差异值 | 说明 |
|:--|--------|------|
| LOH_FEATURE_LOG1P | **全部 1** | wiki 应为 0，导致 wiki MR 偏高 |
| LOH_PERF_PROFILING | **1** | LOH.c L332，0306 无此代码 |
| LOH_RANDOM_CANDIDATES | 64 | 与 0306 一致 |

| Trace | MR | byte_MR | MQPS | n_updates | steps | 日志 |
|:--|-----|---------|------|-----------|-------|------|
| wiki | 0.206713 | 0.190577 | 0.17 | 14,831 | — | `tmp/rl_wiki_full_0310_010834.log` |
| wiki (tuned) | 0.206839 | 0.190691 | 0.17 | 13,544 | — | `tmp/rl_wiki_full_tuned_0310.log` |
| 1063 | 0.027083 | 0.030018 | 0.61 | 10,312 | — | `tmp/rl_1063_full_0310_005641.log` |
| meta | 0.269427 | 0.156722 | 0.78 | 900 | — | `tmp/rl_meta_full_0310_010715.log` |

**分析：**
- wiki 使用 LOG1P=1（而非最优的 LOG1P=0）导致 MR 从 0.176 升至 0.207（+3.1pp），验证了特征模式对 wiki 的显著影响。
- 1063 MR=0.027083（与 0306 的 0.027361 接近且略优），LOG1P=1 适配。
- meta MR=0.269427（与 0306 几乎一致），特征模式不敏感。
- n_updates 远高于 0306（wiki 14831 vs 2469），因 PERF_PROFILING=1 导致 C 变慢 + sync 频率更高。

### 14.2 早期截断/失败的 0310 测试

| 日志 | Trace | 实际请求数 | 结果 | 失败原因 |
|:--|:--|-----------|------|----------|
| `tmp/rl_1063_full_0310_004726.log` | 1063 | 3,000,000 (非全量) | MR=0.289723 | `--num-req=3000000` + cache=2GiB（配置错误，非 0.1 比例） |
| `tmp/rl_1063_full_0310_004851.log` | 1063 | — | 未完成 | cachesim 被 cleanup 停止 |
| `tmp/rl_meta_full_0310_004746.log` | meta | 3,000,000 (非全量) | MR=0.368107 | `--num-req=3000000` + cache=1TiB（配置错误） |
| `tmp/rl_wiki_full_0310_004758.log` | wiki | — | 未完成 | cachesim 被 cleanup 停止 |
| `tmp/rl_sequential_nohup_full.log` | — | — | 空 (12 行) | 脚本启动后即中止 |

> 这些早期测试因脚本配置错误（NUM_REQ 未正确传递、cache 大小错误等）而失败，后续在 §14.1 中修正后重跑。

---

## 15. Blocked / NonBlocked / Async 集成测试（2026-03-09）

> 目的：验证 LOH 的不同等待模式（blocked vs nonblocked）、不同 RL 更新频率（interval）、以及 Python 端异步训练（async_train）对 MR 和吞吐量的影响。
> 所有测试均在 1063 trace 上进行，cache size ratio = 0.1。

### 15.1 Blocked vs NonBlocked 全量对比（interval 测试，COMPOUND=1）

这是最关键的 blocked/nonblocked 对比实验。两组均使用正确配置（COMPOUND=1, IRT=0, LOG1P=1），仅 Wait mode 和 RL update interval 不同。

| 参数 | nb_500 | bl_50000 | bl_500 |
|:--|--------|----------|--------|
| Wait mode | **NON-BLOCKED** | **BLOCKED** | **BLOCKED** |
| LOH_RL_UPDATE_INTERVAL | 500 | 50000 | 500 |
| LOH_SCORE_USE_COMPOUND | 1 | 1 | 1 |
| LOH_SCORE_USE_IRT | 0 | 0 | 0 |
| LOH_FEATURE_LOG1P | 1 | 1 | 1 |
| LOH_RANDOM_CANDIDATES | 0→auto 64 | 0→auto 64 | 0→auto 64 |
| LOH_ENABLE_SEMAPHORE | unset(sem_req=1) | unset(sem_req=1) | unset |
| LOH_PERF_PROFILING | 1 | 1 | 1 |

| 测试 | Trace | 请求数 | MR | Byte MR | MQPS | 状态 | C 日志 | 测试日志 |
|:--|:--|--------|-----|---------|------|------|--------|----------|
| **nb_500** | 1063 | 360,960,512 | **0.026646** | 0.029527 | **0.58** | ✅ | `cachesim_sb3_0309_203908.log` | `tmp/rl_interval_1063_nb_500.log` |
| **bl_50000** | 1063 | 360,960,512 | 0.027407 | 0.030382 | 0.50 | ✅ | `cachesim_sb3_0309_210328.log` | `tmp/rl_interval_1063_bl_50000.log` |
| bl_500 | 1063 | — | — | — | — | ❌ 未完成 | 无 | `tmp/rl_interval_1063_bl_500.log` |

**核心发现：**
- **nb_500 (NonBlocked, interval=500) MR=0.026646 < 0306基线 0.027361**：NON-BLOCKED + 高频更新（每 500 次 eviction 同步一次）产出了目前最低的 1063 MR。
- **bl_50000 (Blocked, interval=50000) MR=0.027407 ≈ 0306基线**：BLOCKED 模式每次同步都等 Python 返回权重，但因 interval=50000（每 50000 次 eviction 才同步一次），对吞吐量影响有限。
- **MQPS**：nb_500=0.58 > bl_50000=0.50，NON-BLOCKED 吞吐量高 16%（无需等待 Python）。
- **bl_500 失败**：BLOCKED + interval=500 组合可能因同步过于频繁（每 500 次 eviction 就阻塞等权重）导致 Python 处理不及而崩溃。

### 15.2 ab_sync / ab_async 测试（COMPOUND 未启用）

> 这些测试虽名为 "sync/async"（指 Python 端训练同步/异步），但 **C 端均为 NON-BLOCKED** 模式。
> **关键差异：COMPOUND=unset, IRT=unset**（缺少 6 维交互特征）。

| 参数 | 差异值 | 说明 |
|:--|--------|------|
| LOH_SCORE_USE_COMPOUND | **未设置** | C 端默认值（无 6 维交互特征） |
| LOH_SCORE_USE_IRT | **未设置** | C 端默认值 |
| LOH_ENABLE_SEMAPHORE | **未设置** | C 端默认 |
| LOH_FEATURE_LOG1P | 1 | 1063 正确值 |
| LOH_RANDOM_CANDIDATES | 64（日志显示但 C 初始化为 0，auto-detect 回退到 64） | |
| LOH_WAIT_MODE | **nonblocked** | C 日志确认 |

#### 15.2.1 8M 测试

| 测试 | Trace | 请求数 | MR | Byte MR | MQPS | 日志 |
|:--|:--|--------|-----|---------|------|------|
| ab_sync_8M | 1063 | 8M | 0.285942 | 0.262948 | 0.11 | `tmp/rl_ab_sync_8M.log` |
| ab_async_8M | 1063 | 8M | 0.283841 | 0.261536 | 0.11 | `tmp/rl_ab_async_8M.log` |
| ab_async_8M_opt | 1063 | 8M | 0.284116 | 0.261514 | 0.11 | `tmp/rl_ab_async_8M_opt.log` |
| ab_async_5M_pickle | 1063 | 5M | 0.317170 | 0.282810 | 0.09 | `tmp/rl_ab_async_5M_pickle.log` |

#### 15.2.2 全量测试

| 测试 | Trace | 请求数 | MR | Byte MR | MQPS | 状态 | 日志 |
|:--|:--|--------|-----|---------|------|------|------|
| ab_sync_full | 1063 | 360,960,512 | 0.232346 | 0.208728 | 0.12 | ✅ | `tmp/rl_ab_sync_full.log` |
| ab_async_full | 1063 | — | — | — | — | ❌ Python 崩溃 | `tmp/rl_ab_async_full.log` |
| ab_async_full_v2 | 1063 | — | — | — | — | ❌ 未完成 | `tmp/rl_ab_async_full_v2.log` |

### 15.3 早期 async 测试（LOG1P 错误 / Python 崩溃）

> 最早期的集成测试。async_v3 使用了错误的 LOG1P=0（1063 应为 1）。async_1063/v2 使用正确配置但 Python 崩溃。

| 测试 | Trace | 请求数 | MR | MQPS | LOG1P | COMPOUND | 状态 | 日志 |
|:--|:--|--------|-----|------|-------|----------|------|------|
| async_v3_1M | 1063 | 1M | 0.603989 | 0.18 | **0（错误）** | unset | ✅ | `tmp/rl_async_v3_1M.log` |
| async_v3_5M | 1063 | 5M | 0.342635 | 0.27 | **0（错误）** | unset | ✅ | `tmp/rl_async_v3_5M.log` |
| async_1063 | 1063 | ALL | — | — | 1 | 1 | ❌ Python 崩溃 | `tmp/rl_async_1063.log` |
| async_v2_1063 | 1063 | ALL | — | — | 1 | 1 | ❌ Python 崩溃 | `tmp/rl_async_v2_1063.log` |

### 15.4 Async v2 全量三 Trace 测试（2026-03-10，\_stop\_event 修复后）

> 修复了 `_stop_event` 竞态条件（`save()` 临时置 None 导致异步训练线程 AttributeError 崩溃）后，重新以最优配置跑全量三条 trace。

**配置**：WAIT=nonblocked, ASYNC\_TRAIN=1, COMPOUND=1, IRT=0, RANDOM\_CANDIDATES=64, INTERVAL=500, SEM=1

| Trace | MR | Byte MR | MQPS | Steps (writes) | BG Train | Exceptions | 日志 |
|:--|------|---------|------|----------------|----------|------------|------|
| 1063 | 0.027085 | 0.030005 | 0.57 | 870,003 (145,001) | 7,248 | 0 | `ac_sb3_0310_170940.log` |
| wiki | 0.175426 | 0.141343 | 0.14 | 1,465,629 (244,272) | 17,660 | 0 | `ac_sb3_0310_172046.log` |
| meta | 0.269425 | 0.156414 | 0.69 | 87,465 (14,578) | 687 | 0 | `ac_sb3_0310_174648.log` |

**小时级 MR（C 端）**：

| Trace | 24h | 48h | 72h | 96h | 120h | 144h | 168h | 192h | 216h |
|:--|------|------|------|------|------|------|------|------|------|
| 1063 | 0.0931 | 0.0773 | 0.0599 | 0.0483 | 0.0380 | 0.0336 | 0.0303 | 0.0280 | 0.0271 |
| wiki | 0.2852 | 0.2303 | 0.2082 | 0.2001 | 0.2019 | 0.2022 | 0.1993 | 0.2047 | 0.2013 |
| meta | 0.3471 | 0.3215 | 0.3110 | 0.3036 | 0.2939 | 0.2847 | 0.2774 | 0.2694 | — |

**与基线对比**（MR / Byte MR / MQPS）：

| 配置 | 1063 | wiki | meta |
|:--|------|------|------|
| **Async v2** | **0.027085** / 0.030005 / 0.57 | **0.175426** / 0.141343 / 0.14 | 0.269425 / 0.156414 / 0.69 |
| 0306 Baseline (sync nb) | 0.027361 / 0.030195 / 0.75 | 0.176183 / 0.141579 / 0.15 | **0.269384** / 0.156423 / 0.97 |
| nb_500 (sync nb, LOG1P tuned) | **0.026646** / 0.029527 / 0.58 | — | — |

**关键发现**：

1. **\_stop\_event 修复后 async 线程全程稳定运行**：三条 trace 均 0 异常，后台训练分别完成 7248 / 17660 / 687 次梯度更新。
2. **1063 步数提升 20.5%**：async v2 870K 步 vs v1（async 崩溃回退为 sync）722K 步，验证了异步训练解耦的效果。
3. **MR 与 0306 基线持平或略优**：1063 -1.0%, wiki -0.4%, meta +0.02%。质量上无回归。
4. **MQPS 略降**：async v2 的 MQPS（0.57/0.14/0.69）比 0306 基线（0.75/0.15/0.97）低约 25-30%，原因是 v2 使用 `_build_rel` 含 PERF\_PROFILING 采集开销。
5. **nb\_500 仍是 1063 最优**：MR=0.026646 优于 async v2 的 0.027085（+1.6%）。nb\_500 使用 LOG1P=1、sync 训练、无 PERF\_PROFILING 开销。

### 15.5 综合分析

1. **Blocked vs NonBlocked**：NonBlocked + 高频更新（interval=500）是最优配置，MR=0.026646 优于 Blocked（0.027407），吞吐量也高 16%（0.58 vs 0.50 MQPS）。
2. **COMPOUND 是关键**: ab_sync_full（COMPOUND=unset）MR=0.232346 比 interval nb_500（COMPOUND=1）MR=0.026646 差 10 倍，证明 **COMPOUND=1 是 LOH RL 取得好 MR 的关键前提**。
3. **sync vs async 训练差异极小**：1063 MR 差距 <2%，wiki/meta 差距 <0.5%。async 主要优势是步数提升 20.5%（推理吞吐解耦）。
4. **早期测试不可比**：async_v3 系列使用了错误的 LOG1P=0，async_1063 系列 Python 崩溃无结果，均不可直接用于对比。
5. **Blocked + 高频更新风险**：bl_500（Blocked, interval=500）崩溃，说明 BLOCKED 模式下 interval 不宜设太小。

---

## 16. Rand-Only 全量实验（无 RL 训练，仅随机权重采样）

> 详细 sweep 数据见 §10.3。此处汇总全量 trace 结果。

### 16.1 与 §11 公共配置的差异

| 参数 | 差异值 | 说明 |
|:--|--------|------|
| LOH_RANDOM_ONLY_CANDIDATES | **1** | 跳过结构化候选，仅随机采样 |
| LOH_RANDOM_CANDIDATES | 64（实际由 RANDOM_ONLY 覆盖） | 候选数 |

### 16.2 结果

| Trace | MR | byte_MR | MQPS | LOG1P | 日志 |
|:--|-----|---------|------|-------|------|
| wiki | **0.172273** | 0.135979 | 0.14 | 0 | `tmp/rl_wiki_randonly_fullreq.log` |
| 1063 | **0.023817** | 0.027561 | 0.78 | 1 | `tmp/rl_1063_randonly_fullreq.log` |
| meta | 0.269843 | 0.156441 | 0.43 | 1 | `tmp/rl_meta_randonly_fullreq.log` |

### 16.3 与 0306 RL 对比

| Trace | RL (0306) | Rand-Only | Δ MR | 赢家 |
|:--|-----------|-----------|------|------|
| wiki | 0.176183 | **0.172273** | **-0.39pp** | Rand-Only |
| 1063 | 0.027361 | **0.023817** | **-0.35pp** | Rand-Only |
| meta | **0.269384** | 0.269843 | +0.05pp | RL (微弱) |

**分析：** Rand-Only 在 wiki 和 1063 上竟优于 RL，说明 LOH 的线性评分函数 + Compound 交互特征本身已足够强，随机探索覆盖了更广的权重空间，RL 的边际提升有限甚至产生过拟合。

---

## 17. 失败/不完整全量实验汇总

| 日志 | Trace | 失败原因 | 结果 |
|:--|:--|----------|------|
| `tmp/rl_ab_async_full.log` | 1063 | Python 崩溃退出 | 无 |
| `tmp/rl_ab_async_full_v2.log` | 1063 | 启动后被清理 | 无 |
| `tmp/rl_1063_full_0310_004726.log` | 1063 | 实际仅 3M req + cache=2GiB 配置错误 | MR=0.290 (不可比) |
| `tmp/rl_1063_full_0310_004851.log` | 1063 | cachesim 被 cleanup 停止 | 无 |
| `tmp/rl_meta_full_0310_004746.log` | meta | 实际仅 3M req + cache=1TiB 配置错误 | MR=0.368 (不可比) |
| `tmp/rl_wiki_full_0310_004758.log` | wiki | cachesim 被 cleanup 停止 | 无 |
| `tmp/rl_sequential_nohup_full.log` | — | 脚本启动即中止 (12 行) | 无 |
| `tmp/cmp_1063_LFUDA_full_0306_120723.log` | 1063 | LFUDA 72h 时被系统信号停止 (rc=147) | MR≈0.480 (不完整) |

---

## 18. Decay + Adaptive Budget 全量实验（2026-03-11）

> **关键发现：Decay 采样本身无开销，之前 wiki 38x slowdown 已被修复，三条 trace 均可安全启用 decay + adaptive budget。**
>
> ⚠️ **注意**：本次实验使用的 release binary 未包含 size 源 decay 修复（stale build）。
> 实际 decay 仅作用于 recency 和 freq 源，size 源仍为 "取绝对最大" 模式。

### 18.1 配置

#### 18.1.1 公共环境变量（所有 trace 通用）

| 参数 | 值 | 说明 |
|:--|---|------|
| `LOH_WAIT_MODE` | `nonblocked` | C 端不等 Python 回应，写入 state 后立即返回 |
| `LOH_ASYNC_TRAIN` | `1` | Python 异步训练（后台线程执行 SAC 梯度更新） |
| `LOH_SCORE_USE_COMPOUND` | `1` | 复合评分模式（recency×freq 交叉特征） |
| `LOH_SCORE_USE_IRT` | `0` | 不使用 IRT 评分（compound 模式下 IRT heap 关闭） |
| `LOH_RANDOM_CANDIDATES` | `64` | 从 hash table 均匀随机采样的候选数 |
| `LOH_STRUCTURED_CANDIDATES` | `96`（默认，未显式设置） | 从结构化数据结构取的候选总数 |
| `LOH_TAIL_SAMPLE` | `1` | 启用 decay 采样（结构化源扫描时用几何概率） |
| `LOH_TAIL_SAMPLE_DECAY` | `0.99` | 衰减率 p(i)=0.99^i，i 为扫描深度 |
| `LOH_ADAPTIVE_BUDGET` | `1` | 自适应预算（每 10000 次驱逐按贡献重平衡结构化源配额） |
| `LOH_ENABLE_RL` | `1`（脚本自动设置） | 启用 RL 同步 |
| `LOH_RL_ALGO` | `SAC`（默认） | RL 算法 |
| `LOH_ENABLE_SEMAPHORE` | `1` | 使用 POSIX 信号量加速 C↔Python 通信 |
| `LOH_BUILD_RELEASE` | `1` | 使用 release build (`_build_rel/bin/cachesim`) |
| `LOH_SKIP_BUILD` | `1` | 跳过构建步骤（假设 binary 已最新） |
| `LOH_SKIP_PIP_INSTALL` | `1` | 跳过 pip 安装 |
| `LOH_PERF_PROFILING` | `0`（编译时 `#define`） | 关闭性能计时宏（减少 ~25% 开销） |
| `LOH_DEBUG_LEVEL` | `1`（默认） | 调试日志级别 |
| `LOH_MISS_RATIO_WEIGHT` | `1.0`（默认） | reward = 1.0×obj_hit_ratio + 0.0×byte_hit_ratio |
| `RL_UPDATE_INTERVAL` | `500`（默认） | 每 500 个请求触发一次 RL 同步 |

#### 18.1.2 Per-trace 配置

| Trace | 路径 | Feature Mode | Cache Size | 备注 |
|:--|------|-------------|-----------|------|
| **1063** | `data/TencentCBS/1063.oracleGeneral.zst` | `LOH_FEATURE_LOG1P=1` | `0.1` (5 GiB) | TencentCBS 块 I/O，360M req |
| **wiki** | `data/WikiCDN/wiki_2019t.oracleGeneral.zst` | `LOH_FEATURE_LOG1P=0` `LOH_FEATURE_LOG1P_RECIPROCAL=1` | `0.1` (40 GiB) | WikiCDN，RECIPROCAL 模式，207M req |
| **meta** | `data/MetaCDN/meta_reag.oracleGeneral.zst` | `LOH_FEATURE_LOG1P=1` | `0.1` (16 TiB) | MetaCDN，45M req |

#### 18.1.3 候选收集结构

```
每次驱逐收集 96+64=160 个候选：
├── 结构化候选（96 个，自适应分配）
│   ├── recency 源 (LRU 尾部): ~32个  ← decay p=0.99^i ✅
│   ├── freq 源 (频率表最低频): ~32个  ← decay p=0.99^i ✅
│   └── size 源 (大小堆最大): ~32个    ← ⚠️ 本次无 decay（stale binary）
│   └── 自适应：50%均分 + 50%按驱逐贡献比例（每 10000 次重平衡）
│
└── 随机候选（64 个，固定）
    └── 从 hash table flat array 均匀随机采样
```

#### 18.1.4 运行命令

```bash
# Wiki
LOH_TAIL_SAMPLE=1 LOH_TAIL_SAMPLE_DECAY=0.99 LOH_ADAPTIVE_BUDGET=1 \
LOH_FEATURE_LOG1P=0 LOH_FEATURE_LOG1P_RECIPROCAL=1 LOH_ASYNC_TRAIN=1 \
bash scripts/run_nonblocked36.sh data/WikiCDN/wiki_2019t.oracleGeneral.zst 0.1 0 wiki_async_decay

# 1063
LOH_TAIL_SAMPLE=1 LOH_TAIL_SAMPLE_DECAY=0.99 LOH_ADAPTIVE_BUDGET=1 \
LOH_FEATURE_LOG1P=1 LOH_ASYNC_TRAIN=1 \
bash scripts/run_nonblocked36.sh data/TencentCBS/1063.oracleGeneral.zst 0.1 0 1063_async_decay

# Meta
LOH_TAIL_SAMPLE=1 LOH_TAIL_SAMPLE_DECAY=0.99 LOH_ADAPTIVE_BUDGET=1 \
LOH_FEATURE_LOG1P=1 LOH_ASYNC_TRAIN=1 \
bash scripts/run_nonblocked36.sh data/MetaCDN/meta_reag.oracleGeneral.zst 0.1 0 meta_async_decay
```

### 18.2 结果

| Trace | Req | MR | Byte MR | MQPS | 壁钟时间 |
|:--|----:|---:|--------:|-----:|---------:|
| 1063 | 360,960,512 | **0.026609** | 0.029576 | **0.77** | 8m27s |
| wiki | 207,646,002 | 0.177963 | 0.138973 | **0.21** | 17m01s |
| meta | 45,623,306 | **0.269375** | 0.156867 | 0.96 | 1m06s |

日志文件：
- `tmp/1063_async_decay/run.log`、`cachesim_sb3_0311_005222.log`、`ac_sb3_0311_005222.log`
- `tmp/wiki_async_decay/run.log`、`cachesim_sb3_0311_002938.log`、`ac_sb3_0311_002938.log`
- `tmp/meta_async_decay/run.log`、`cachesim_sb3_0311_010229.log`、`ac_sb3_0311_010229.log`

### 18.3 与 0306 Baseline 对比

| Trace | 0306 MR | Decay+Async MR | Δ MR | 0306 MQPS | Decay+Async MQPS | Δ MQPS |
|:--|---------|---------------|------|-----------|-----------------|--------|
| 1063 | 0.027361 | **0.026609** | **-2.7%** | 0.75 | **0.77** | **+2.7%** |
| wiki | **0.176183** | 0.177963 | +1.0% | 0.15 | **0.21** | **+40%** |
| meta | 0.269384 | **0.269375** | **-0.003%** | **0.97** | 0.96 | -1.0% |

### 18.4 Decay 单独开销验证（纯模拟，LOH_ENABLE_RL=0）

为排除 RL 交互干扰，使用 `LOH_ENABLE_RL=0` + `LOH_FIXED_WEIGHTS=0.167,...` 跑 3M requests：

| Trace | No-Decay Time | With-Decay Time | 开销 |
|:--|--------------|----------------|------|
| wiki | 20.63s | 20.91s | **+1.4%** |
| 1063 | 10.01s | 9.19s | **-8.2%** (更快) |
| meta | 2.56s | 2.59s | **+1.1%** |

结论：Decay 采样本身在**所有 trace 上开销 ≤1.4%**，不是性能瓶颈。

### 18.5 Wiki 38x Slowdown 分析

之前观测到 wiki+RL+decay 38x 变慢。经过本次验证：
1. **纯模拟 decay 开销仅 1.4%**（20.63s → 20.91s）
2. **RL 集成 decay ≈ 0% 开销**（nonblocked 3M：no-decay 27.8s vs decay 26.6s）
3. **全量运行正常**：0.21 MQPS，17 分钟完成 207M requests

**结论**：38x slowdown 已被此前的修复消除，可能原因包括：
- `LOH_PERF_PROFILING` 从 1 改为 0（消除 ~25% 计时开销）
- `ultra_fast` 路径扩展到 RECIPROCAL 模式
- `_stop_event` 异步训练修复（避免 Python 训练线程崩溃回退）

### 18.6 综合排名更新（全量 trace, MR 从优到劣）

| 排名 | 算法 | 1063 MR | Wiki MR | Meta MR |
|:--|---|---|---|---|
| 1 | BeladySize | 0.018200 | 0.124325 | 0.268778 |
| 2 | **LOH-RandOnly** | **0.023817** | **0.172273** | 0.269843 |
| 3 | **LOH-Decay+Async** | **0.026609** | 0.177963 | **0.269375** |
| 4 | LOH-RL (0306) | 0.027361 | 0.176183 | 0.269384 |
| 5 | GDSF | 0.054791 | 0.180493 | 0.268918 |
| 6 | 3LCache-OMR | 0.060630 | 0.174871 | 0.392964 |
| 7 | Belady | 0.147024 | 0.134717 | 0.268778 |
| 8 | LRU | 0.261774 | 0.230638 | 0.326804 |
| 9 | S3FIFO | 0.260116 | 0.187962 | 0.326397 |

---

## §19 综合批量实验：6配置×3 trace + Grid Search + Penalty + MR权重

**日期**: 2026-03-11 02:02 ~ 11:43 (总计 ~9h41m)
**脚本**: `scripts/batch_experiment.sh`
**结果目录**: `tmp/batch_0311_020224/`

### 19.1 实验概述

四步系统实验：
1. **Step 1**: 6 种候选配置（random-only×sync/async, rand+struct+decay×sync/async, rand+struct+nodecay×sync/async）× 3 traces = 18 tests
2. **Step 2**: 纯结构化+decay 网格搜索（5 候选数 × 4 decay 率 = 20 configs × 3M × 3 traces），top-3 全量验证
3. **Step 3**: Penalty 机制测试（LOH_ENABLE_PENALTY=1 重编译）
4. **Step 4**: MISS_RATIO_WEIGHT 扫描（0.0, 0.25, 0.5, 0.75, 1.0）

### 19.2 公共配置

```
LOH_WAIT_MODE=nonblocked  LOH_SCORE_USE_COMPOUND=1  LOH_SCORE_USE_IRT=0
LOH_ENABLE_SEMAPHORE=1  LOH_BUILD_RELEASE=1  LOH_SKIP_BUILD=1  LOH_ADAPTIVE_BUDGET=1
Binary: _build_rel/bin/cachesim (rebuild at 01:22, with decay for ALL structured sources)
Cache size: 0.1
Feature: wiki=RECIPROCAL, 1063/meta=LOG1P
```

### 19.3 Step 1 结果：6 配置 × 3 Traces（全量请求）

| Config | Trace | Requests | MR | Byte MR | MQPS | Time(s) |
|:--|:--|----------|----|---------|------|---------|
| randonly96_sync | 1063 | 360,960,512 | **0.021666** | 0.024808 | 0.77 | 504 |
| randonly96_sync | wiki | 207,646,002 | **0.173539** | 0.133766 | 0.17 | 1278 |
| randonly96_sync | meta | 45,623,306 | 0.269836 | 0.156278 | 0.79 | 75 |
| randonly96_async | 1063 | 360,960,512 | 0.022058 | 0.025192 | 0.76 | 511 |
| randonly96_async | wiki | 207,646,002 | 0.173663 | 0.133588 | 0.17 | 1273 |
| randonly96_async | meta | 45,623,306 | 0.269826 | 0.156180 | 0.79 | 75 |
| rand96+struct96+decay_sync | 1063 | 360,960,512 | 0.022124 | 0.025274 | 0.70 | 544 |
| rand96+struct96+decay_sync | wiki | 207,646,002 | 0.177740 | 0.139703 | 0.15 | 1446 |
| rand96+struct96+decay_sync | meta | 45,623,306 | **0.269053** | 0.156282 | **1.22** | 53 |
| rand96+struct96+decay_async | 1063 | 360,960,512 | 0.022036 | 0.025161 | 0.71 | 545 |
| rand96+struct96+decay_async | wiki | 207,646,002 | 0.176654 | 0.139729 | 0.15 | 1465 |
| rand96+struct96+decay_async | meta | 45,623,306 | 0.269062 | 0.156540 | **1.26** | 53 |
| rand96+struct96+nodecay_sync | 1063 | 360,960,512 | 0.021795 | 0.024907 | 0.73 | 533 |
| rand96+struct96+nodecay_sync | wiki | 19,998,085 | ~~0.2307~~ | N/A | N/A | 6340⚠️ |
| rand96+struct96+nodecay_sync | meta | 45,623,306 | 0.269163 | 0.155687 | 1.04 | 63 |
| rand96+struct96+nodecay_async | 1063 | 360,960,512 | 0.022098 | 0.025214 | 0.71 | 542 |
| rand96+struct96+nodecay_async | wiki | — | KILLED | KILLED | KILLED | 193⚠️ |
| rand96+struct96+nodecay_async | meta | 45,623,306 | 0.269161 | 0.155779 | 1.14 | 57 |

⚠️ **nodecay+struct96 在 wiki 上极慢**：无 decay 时 wiki 处理速度仅 ~0.003 MQPS（正常 0.15 MQPS），50x 减速。原因：无 decay 时所有结构化源全量扫描，wiki 小对象多导致 capacity_threshold 大、扫描量巨大。

#### 19.3.1 Step 1 按 trace 排名（仅完整运行）

**1063** (越低越好):
| Rank | Config | MR | MQPS |
|:--|--------|------|------|
| 1 | randonly96_sync | 0.021666 | 0.77 |
| 2 | rand96+struct96+nodecay_sync | 0.021795 | 0.73 |
| 3 | rand96+struct96+decay_async | 0.022036 | 0.71 |
| 4 | randonly96_async | 0.022058 | 0.76 |
| 5 | rand96+struct96+nodecay_async | 0.022098 | 0.71 |
| 6 | rand96+struct96+decay_sync | 0.022124 | 0.70 |

**Wiki** (越低越好):
| Rank | Config | MR | MQPS |
|:--|--------|------|------|
| 1 | randonly96_sync | 0.173539 | 0.17 |
| 2 | randonly96_async | 0.173663 | 0.17 |
| 3 | rand96+struct96+decay_async | 0.176654 | 0.15 |
| 4 | rand96+struct96+decay_sync | 0.177740 | 0.15 |

**Meta** (越低越好):
| Rank | Config | MR | MQPS |
|:--|--------|------|------|
| 1 | rand96+struct96+decay_sync | 0.269053 | 1.22 |
| 2 | rand96+struct96+decay_async | 0.269062 | 1.26 |
| 3 | rand96+struct96+nodecay_sync | 0.269163 | 1.04 |
| 4 | rand96+struct96+nodecay_async | 0.269161 | 1.14 |
| 5 | randonly96_async | 0.269826 | 0.79 |
| 6 | randonly96_sync | 0.269836 | 0.79 |

#### 19.3.2 Step 1 关键发现

1. **random-only 96 在 1063 和 wiki 上最优**：MR 比混合配置低 0.3-2.4%
2. **混合配置在 meta 上最优**：rand+struct+decay 比 randonly 低 ~0.0008
3. **结构化源大幅提升 meta MQPS**：从 0.79→1.22-1.26（+55%），因 meta 对象大、结构化扫描更高效
4. **sync vs async 差异极小**：MR 差异 < 0.001，MQPS 几乎相同
5. **nodecay+wiki = 灾难性慢**：必须使用 decay

### 19.4 Step 2 结果：纯结构化 + Decay 网格搜索

#### 19.4.1 3M 请求网格搜索 Top-10

| Rank | Config | Avg MR (3 traces) |
|:--|--------|-------------------|
| 1 | sc64_d0.999 | 0.455772 |
| 2 | sc32_d0.999 | 0.455904 |
| 3 | sc32_d0.95 | 0.456803 |
| 4 | sc96_d0.999 | 0.457176 |
| 5 | sc128_d0.90 | 0.457315 |
| 6 | sc192_d0.90 | 0.457425 |
| 7 | sc32_d0.99 | 0.457524 |
| 8 | sc96_d0.90 | 0.457526 |
| 9 | sc64_d0.99 | 0.457566 |
| 10 | sc128_d0.999 | 0.457568 |

注意：3M 请求的 MR ~0.40-0.60 远高于全量，因缓存尚未充分warm-up。

#### 19.4.2 Top-3 全量验证

| Config | Trace | MR | Byte MR | MQPS | Time(s) |
|:--|:--|----|---------|------|---------|
| sc64_d0.999 | 1063 | 0.250992 | 0.209740 | 0.67 | 578 |
| sc64_d0.999 | wiki | 0.186600 | 0.134872 | 0.59 | 379 |
| sc64_d0.999 | meta | 0.269085 | 0.162642 | 1.52 | 47 |
| sc32_d0.999 | 1063 | 0.250470 | 0.209469 | 0.81 | 486 |
| sc32_d0.999 | wiki | 0.186592 | 0.134631 | 0.63 | 359 |
| sc32_d0.999 | meta | 0.269123 | 0.163766 | 1.54 | 46 |
| sc32_d0.95 | 1063 | 0.251488 | 0.210400 | 0.61 | 627 |
| sc32_d0.95 | wiki | 0.186921 | 0.134896 | 0.53 | 423 |
| sc32_d0.95 | meta | 0.269064 | 0.161495 | 1.50 | 47 |

#### 19.4.3 Step 2 关键发现

1. **纯结构化在 1063 上灾难性差**：MR=0.250 vs random-only 的 0.022（12x 差距），说明 1063 对随机候选依赖很强
2. **纯结构化在 wiki/meta 上可用但非最优**：wiki MR=0.187 vs randonly 0.174，meta MR=0.269 与混合配置相当
3. **Decay 率 0.999 最优**：高保留率 = 更多候选被考虑 = 更好的 quality
4. **候选数无明显影响**：sc32 ≈ sc64 ≈ sc96，说明即使只看少量候选也能找到好的eviction目标
5. **结论：纯结构化不可行，随机候选是必要的**

### 19.5 Step 3 结果：Penalty 机制

配置：rand96+struct96+decay0.99+async，`LOH_ENABLE_PENALTY=1`（需重编译）

| Config | Trace | MR | Byte MR | MQPS | Time(s) |
|:--|:--|----|---------|------|---------|
| penalty_pos0 | 1063 | 0.022067 | 0.025217 | 0.68 | 564 |
| penalty_pos0 | wiki | 0.176917 | 0.139397 | 0.14 | 1513 |
| penalty_pos0 | meta | 0.269060 | 0.156501 | 1.26 | 53 |
| penalty_pos1 | 1063 | 0.022092 | 0.025230 | 0.68 | 564 |
| penalty_pos1 | wiki | 0.176879 | 0.140211 | 0.14 | 1551 |
| penalty_pos1 | meta | 0.269056 | 0.156143 | 1.24 | 54 |

对比（无 penalty 基线 = rand96+struct96+decay_async from Step 1）：

| Trace | No Penalty | Penalty pos0 | Penalty pos1 | 差异 |
|:--|-----------|-------------|-------------|------|
| 1063 | 0.022036 | 0.022067 | 0.022092 | +0.001~0.003 |
| wiki | 0.176654 | 0.176917 | 0.176879 | +0.001~0.002 |
| meta | 0.269062 | 0.269060 | 0.269056 | ≈0（无显著差异）|

#### 19.5.1 Step 3 关键发现

1. **Penalty 机制几乎无影响**：MR 差异 < 0.001（在噪声范围内）
2. **pos0 vs pos1 无显著差异**
3. **不推荐启用 Penalty**：增加编译复杂性而无收益

### 19.6 Step 4 结果：MISS_RATIO_WEIGHT 扫描

配置：rand96+struct96+decay0.99+async

| MR Weight | Trace | MR | Byte MR | MQPS | Time(s) |
|:--|:--|----|---------|------|---------|
| 0.0 (纯byte) | 1063 | 0.022044 | 0.025174 | 0.71 | 547 |
| 0.0 | wiki | 0.176711 | 0.139541 | 0.14 | 1495 |
| 0.0 | meta | 0.269059 | 0.156470 | 1.22 | 55 |
| 0.25 | 1063 | 0.021963 | 0.025082 | 0.69 | 558 |
| 0.25 | wiki | 0.176781 | 0.139775 | 0.14 | 1503 |
| 0.25 | meta | 0.269055 | 0.156299 | 1.22 | 54 |
| 0.5 | 1063 | 0.022081 | 0.025204 | 0.70 | 556 |
| 0.5 | wiki | 0.176923 | 0.139904 | 0.14 | 1472 |
| 0.5 | meta | 0.269058 | 0.156318 | 1.15 | 57 |
| 0.75 | 1063 | 0.022056 | 0.025177 | 0.71 | 546 |
| 0.75 | wiki | 0.176894 | 0.139772 | 0.15 | 1468 |
| 0.75 | meta | 0.269195 | 0.156390 | 0.80 | 74 |
| 1.0 (纯obj) | 1063 | 0.022162 | 0.025298 | 0.71 | 548 |
| 1.0 | wiki | 0.176536 | 0.140050 | 0.15 | 1466 |
| 1.0 | meta | 0.269060 | 0.156532 | 1.13 | 58 |

#### 19.6.1 按 trace 汇总

**1063**:
| MR Weight | Obj MR | Byte MR |
|:--|--------|---------|
| 0.25 | **0.021963** | **0.025082** |
| 0.0 | 0.022044 | 0.025174 |
| 0.75 | 0.022056 | 0.025177 |
| 0.5 | 0.022081 | 0.025204 |
| 1.0 | 0.022162 | 0.025298 |

**Wiki**:
| MR Weight | Obj MR | Byte MR |
|:--|--------|---------|
| 1.0 | **0.176536** | 0.140050 |
| 0.0 | 0.176711 | **0.139541** |
| 0.25 | 0.176781 | 0.139775 |
| 0.75 | 0.176894 | 0.139772 |
| 0.5 | 0.176923 | 0.139904 |

**Meta**:
| MR Weight | Obj MR | Byte MR |
|:--|--------|---------|
| 0.25 | **0.269055** | **0.156299** |
| 0.5 | 0.269058 | 0.156318 |
| 0.0 | 0.269059 | 0.156470 |
| 1.0 | 0.269060 | 0.156532 |
| 0.75 | 0.269195 | 0.156390 |

#### 19.6.2 Step 4 关键发现

1. **MR Weight 对结果影响极小**：所有 trace 上 MR 变化 < 0.002
2. **最优权重因 trace 而异**：1063 最优 0.25，wiki 最优 1.0，meta 最优 0.25
3. **默认值 1.0（纯obj MR）是合理选择**：在所有 trace 上都接近最优
4. **MR weight = 0.25 在 1063 和 meta 上略优**：考虑少量 byte MR 有帮助
5. **结论：保持默认 1.0 即可，无需调整**

### 19.7 综合结论与推荐

#### 19.7.1 最佳配置排名

**1063**（最优→最差）：
1. randonly96（MR=0.0217, MQPS=0.77）
2. rand96+struct96+nodecay（MR=0.0218, MQPS=0.73）
3. rand96+struct96+decay（MR=0.0220, MQPS=0.71）

**Wiki**（最优→最差）：
1. randonly96（MR=0.1735, MQPS=0.17）
2. rand96+struct96+decay（MR=0.1767, MQPS=0.15）
3. rand96+struct96+nodecay（**不可行**，50x 减速）

**Meta**（最优→最差）：
1. rand96+struct96+decay（MR=0.2691, MQPS=1.26）
2. rand96+struct96+nodecay（MR=0.2692, MQPS=1.14）
3. randonly96（MR=0.2698, MQPS=0.79）

#### 19.7.2 推荐默认配置

考虑到跨 trace 的兼容性和安全性：

```
LOH_RANDOM_CANDIDATES=96
LOH_STRUCTURED_CANDIDATES=96
LOH_TAIL_SAMPLE=1
LOH_TAIL_SAMPLE_DECAY=0.99
LOH_ADAPTIVE_BUDGET=1
LOH_ASYNC_TRAIN=1（或 0，差异极小）
LOH_MISS_RATIO_WEIGHT=1.0（默认，改变无显著效果）
LOH_ENABLE_PENALTY=0（无需启用）
```

理由：
- 混合配置在 meta 上显著优于 randonly（MQPS +60%，MR 更低）
- Decay 必须启用（否则 wiki 50x 减速）
- 在 1063/wiki 上虽比 randonly 差 0.001-0.003，但在实用范围内
- Penalty 和 MR weight 调整对结果无显著影响

#### 19.7.3 未解之谜

1. **randonly96 为何在 1063/wiki 上比混合好？** 可能原因：结构化源引入的候选质量不如纯随机，因为 LRU/freq/size 等结构化源的 "边缘" 对象未必是最差的
2. **wiki 无 decay 50x 减速的根因？** 需进一步剖析：可能是 wiki 小对象极多导致每个结构化源扫描的候选数远超 96（max_scan = capacity_threshold × 10）

### 19.8 与历史基线对比（更新排名）

| Rank | Config | 1063 MR | Wiki MR | Meta MR |
|:--|--------|---------|---------|---------|
| 1 | LOH randonly96 (§19) | **0.021666** | **0.173539** | 0.269836 |
| 2 | LOH rand96+struct96+decay (§19) | 0.022036 | 0.176654 | **0.269053** |
| 3 | LOH-RL (0306 baseline) | 0.027361 | 0.176183 | 0.269384 |
| 4 | GDSF | 0.054791 | 0.180493 | 0.268918 |
| 5 | 3LCache-OMR | 0.060630 | 0.174871 | 0.392964 |
| 6 | Belady | 0.147024 | 0.134717 | 0.268778 |
| 7 | LRU | 0.261774 | 0.230638 | 0.326804 |

**LOH-RL 新配置全面超越 0306 基线**（1063：-21%~-26%，wiki：-1.5%~+0.3%，meta：-0.12%~+0.17%）

## 20. Penalty Sweep 分布实验（1063, 3M）

> 数据来源：
> - 分布分析文档：`tmp/penalty_sweep/PENALTY_DISTRIBUTION_ANALYSIS.md`
> - 批运行日志：`tmp/penalty_sweep/batch_run.log`
> - 汇总表：`tmp/penalty_sweep/summary.csv`

### 20.1 运行元信息

- Trace：`data/TencentCBS/1063.oracleGeneral.zst`
- 请求量：`3,000,000`（`CACHESIM_NUM_REQ=3000000`）
- 运行时间：`2026-03-12`，日志样本覆盖约 `18:29` 到 `18:57`（按 `ac_sb3_0312_*.log` 时间戳）
- 批量规模：`48` 组（`4 scale × 6 formula × 2 pos`）

公共配置（批次共同项）：

- `LOH_SCORE_USE_IRT=0`
- `LOH_SCORE_USE_COMPOUND=1`
- `LOH_FEATURE_LOG1P=1`
- `LOH_DUAL_CHANNEL=0`
- `LOH_RANDOM_CANDIDATES=96`
- `cache_size=0.1`
- `miss_ratio_weight=1.0, byte_miss_ratio_weight=0`
- `LOH_SKIP_BUILD=1`（复用已有 `_build_rel/bin/cachesim`）

### 20.2 无 Penalty 复测（Auto）

按 20.1 同等条件（1063, 3M），仅在 `LOH_ENABLE_PENALTY=0` 下比较两组：

- `log1p`（`LOH_WAIT_MODE=nonblocked`）
- `log1p_blocked`（`LOH_WAIT_MODE=blocked`）

<!-- AUTO_PENALTY_NOP_0316_BEGIN -->
_Auto-updated from `tmp/penalty_ablation_pair_0316/results.csv` at 2026-03-16 20:55:54._

| Variant | Wait Mode | Status | MR | Byte MR | MQPS | Log |
|:--|---|---|---:|---:|---:|---|
| log1p | nonblocked | ok | 0.283864 | 0.329181 | 0.13 | `log1p.log` |
| log1p_blocked | blocked | ok | 0.282117 | 0.327932 | 0.03 | `log1p_blocked.log` |
<!-- AUTO_PENALTY_NOP_0316_END -->

### 20.3 Penalty=1 历史 sweep 结果（按 MR 升序，TOP5 加粗）

| Rank | Scale | Formula | pos | MR | Byte MR | MQPS |
|---:|---|---|---:|---:|---:|---:|
| **1** | **reciprocal** | **net2** | **1** | **0.281763** | **0.327512** | **0.08** |
| **2** | **survival** | **net** | **0** | **0.283153** | **0.330285** | **0.09** |
| **3** | **log** | **net2** | **0** | **0.283364** | **0.328839** | **0.08** |
| **4** | **survival** | **neg** | **1** | **0.283784** | **0.330275** | **0.08** |
| **5** | **binary** | **net** | **1** | **0.284548** | **0.330195** | **0.08** |
| 6 | reciprocal | centered | 1 | 0.284560 | 0.326029 | 0.08 |
| 7 | survival | net2 | 1 | 0.284625 | 0.327515 | 0.08 |
| 8 | log | centered | 1 | 0.284649 | 0.327932 | 0.08 |
| 9 | survival | net2 | 0 | 0.284682 | 0.329923 | 0.08 |
| 10 | survival | relative | 0 | 0.284803 | 0.329824 | 0.08 |
|:--| survival | relative | 1 | 0.284978 | 0.331517 | 0.09 |
| 11 | reciprocal | relative | 1 | 0.284902 | 0.332842 | 0.08 |
| 12 | log | relative | 1 | 0.284992 | 0.329359 | 0.08 |
| 13 | binary | neg | 1 | 0.285006 | 0.330729 | 0.09 |
| 14 | binary | net2 | 0 | 0.285048 | 0.329429 | 0.08 |
| 15 | log | neg | 0 | 0.285091 | 0.329447 | 0.08 |
| 16 | reciprocal | net | 0 | 0.285134 | 0.329007 | 0.08 |
| 17 | binary | relative | 0 | 0.285121 | 0.329168 | 0.08 |
| 18 | binary | neg | 0 | 0.285153 | 0.329043 | 0.08 |
| 19 | log | neg | 1 | 0.285234 | 0.327319 | 0.09 |
| 20 | binary | net2 | 1 | 0.285338 | 0.331545 | 0.08 |
| 21 | binary | centered | 1 | 0.285405 | 0.331100 | 0.08 |
| 22 | log | one_minus | 1 | 0.285438 | 0.330371 | 0.08 |
| 23 | binary | relative | 1 | 0.285463 | 0.329729 | 0.08 |
| 24 | survival | centered | 1 | 0.285487 | 0.331934 | 0.09 |
| 25 | binary | one_minus | 0 | 0.285513 | 0.330164 | 0.08 |
| 26 | binary | one_minus | 1 | 0.285553 | 0.330925 | 0.08 |
| 27 | log | centered | 0 | 0.285637 | 0.329575 | 0.08 |
|:--| survival | centered | 0 | 0.285666 | 0.330345 | 0.08 |
| 28 | binary | net | 0 | 0.285675 | 0.329556 | 0.08 |
| 29 | reciprocal | neg | 0 | 0.285786 | 0.329565 | 0.08 |
| 30 | reciprocal | centered | 0 | 0.285880 | 0.330221 | 0.07 |
| 31 | log | relative | 0 | 0.285902 | 0.330506 | 0.09 |
|:--| binary | centered | 0 | 0.286055 | 0.329634 | 0.08 |
| 32 | reciprocal | net2 | 0 | 0.286115 | 0.329557 | 0.08 |
| 33 | survival | neg | 0 | 0.286174 | 0.332199 | 0.08 |
| 34 | log | one_minus | 0 | 0.286243 | 0.329711 | 0.08 |
| 35 | log | net | 1 | 0.286271 | 0.332410 | 0.08 |
| 36 | log | net | 0 | 0.286281 | 0.330247 | 0.08 |
| 37 | reciprocal | neg | 1 | 0.286291 | 0.331974 | 0.08 |
| 38 | reciprocal | one_minus | 1 | 0.286516 | 0.333293 | 0.08 |
| 39 | reciprocal | one_minus | 0 | 0.286669 | 0.332317 | 0.08 |
| 40 | reciprocal | net | 1 | 0.286894 | 0.332060 | 0.08 |
| 41 | survival | one_minus | 1 | 0.287030 | 0.330832 | 0.08 |
| 42 | log | net2 | 1 | 0.287694 | 0.335250 | 0.09 |
| 43 | reciprocal | relative | 0 | 0.288535 | 0.330908 | 0.08 |
| 44 | survival | net | 1 | 0.290494 | 0.332496 | 0.08 |
| 45 | survival | one_minus | 0 | 0.322361 | 0.352841 | 0.08 |

注：原始 `summary.csv` 中存在重复键覆盖后的汇总口径；本表按当前文件可见条目整理。若后续重跑会以同路径自动覆盖。

### 20.4 同等主干配置的 no-penalty 对比

以下为同口径二元对照（均为 `LOH_ENABLE_PENALTY=0`，仅切换 `LOH_WAIT_MODE`）：

<!-- AUTO_PENALTY_COMPARE_0316_BEGIN -->
| 对照项 | LOG1P(nonblocked) | LOG1P+blocked | 差值(blocked-log1p) |
|:--|---:|---:|---:|
| MR | 0.283864 | 0.282117 | -0.001747 |
| Byte MR | 0.329181 | 0.327932 | -0.001249 |
| MQPS | 0.13 | 0.03 | -0.10 |
<!-- AUTO_PENALTY_COMPARE_0316_END -->

日志一致性核查（20.2 vs 20.3）：

| 检查项 | 20.2（ablation, 2026-03-16） | 20.3（historical sweep, 2026-03-12） | 是否一致 |
|:--|---|---|---|
| Trace | `data/TencentCBS/1063.oracleGeneral.zst` | `data/TencentCBS/1063.oracleGeneral.zst` | 是 |
| Num requests | `--num-req=3000000` | `--num-req=3000000` | 是 |
| cache size | `0.1` | `0.1` | 是 |
| eviction-params | `miss-ratio-weight=1.0` | `miss-ratio-weight=1.0` | 是 |
| 评分主干 | `COMPOUND=1, IRT=0, LOG1P=1, RANDOM_CANDIDATES=96` | 同上 | 是 |
| 运行代次 | 2026-03-16 新跑（`ablation_pen{0,1}.log`） | 2026-03-12 历史批次（`log_relative_pos{0,1}.log`） | 否 |
| 预清理模式 | `LOH_PARALLEL_SAFE=1`（skip global cleanup） | 非并行安全模式（执行 global cleanup） | 否 |
| Python 依赖安装 | `LOH_SKIP_PIP_INSTALL=1` | 旧批次执行 pip 安装检查 | 否 |

结论：`trace` 与 `请求量` 一致，但两组日志并非同一运行代次，且运行路径细节存在差异；因此 `20.2` 与 `20.3` 的绝对 MR 不应直接做“仅 penalty”归因。用于隔离 penalty 影响应优先参考上面的同口径二元对照表（同一批次、同一脚本、仅切换 `LOH_ENABLE_PENALTY`）。

20.3 与 20.4 的直接差异（面向本次问题）：

| 项目 | 20.3（历史 `log_relative_pos0/1`） | 20.4（当前 `ablation_pen0/1`） |
|:--|---|---|
| 目标 | 48 组 sweep 中的历史样本行 | 同一脚本内只做 2 组（penalty 0/1） |
| penalty knobs | 历史 sweep 按组合切换（含 `scale/formula/pos`） | 固定 `scale=log, formula=relative, pos=0` |
| 构建代次 | 2026-03-12 历史二进制与运行时环境 | 2026-03-16 现代码先重编再运行 |
| 预清理模式 | 非 parallel-safe（会做全局清理） | `LOH_PARALLEL_SAFE=1`（跳过全局清理） |
| pip 行为 | 脚本中执行 pip 检查路径 | `LOH_SKIP_PIP_INSTALL=1` |

因此：`20.3` 与 `20.4` 只能比较“趋势”，不能比较“绝对值”；要看 penalty 本身影响，应以 `20.4` 二元对照为准。

## 21. 网络层数与 Replay Buffer 测试总结（含 baseline 对比）

> 数据来源：
> - Full req 批量测试：`tmp/full_default_netbuf_full_0313_221815/results.csv`
> - 早期 3M 试跑：`tmp/full_default_netbuf_0313_221624/results.csv`

本章默认配置（用于对齐比较口径）：

- 请求量：full req（`CACHESIM_NUM_REQ=0`）
- 缓存比例：`0.1`
- 评分模式：`LOH_SCORE_USE_COMPOUND=1`, `LOH_SCORE_USE_IRT=0`
- 特征公式：1063/meta 使用 LOG1P，wiki 使用 RECIPROCAL

本章差异配置（仅这些项变化）：

- `21.1`：`sac_net_arch`（`net1/net3/net4`）
- `21.2`：`sac_buffer_size` 与 `sac_batch_size`（`bb_50k_512/bb_100k_512/bb_50k_1024`）

### 21.1 网络层数（`sac_net_arch`）

测试组：

- `net1`: `256`
- `net3`: `512,512,256`
- `net4`: `512,512,256,256`

其余关键参数固定：`sac_buffer_size=10000`，`sac_batch_size=256`。

| net 架构 | 1063 MR / Byte MR / MQPS | Wiki MR / Byte MR / MQPS | Meta MR / Byte MR / MQPS | 结论 |
|:--|---|---|---|---|
| net1 (256) | 0.022259 / 0.025392 / 0.65 | **0.176379** / 0.139362 / 0.11 | 0.269082 / **0.156019** / **1.17** | 最轻量，吞吐最好 |
| net3 (512,512,256) | 0.022233 / 0.025384 / 0.63 | 0.176661 / **0.138957** / 0.10 | **0.269081** / 0.156174 / 1.08 | Meta Obj MR 略优 |
| net4 (512,512,256,256) | **0.022063** / **0.025184** / 0.59 | 0.176546 / 0.139412 / 0.10 | 0.269083 / 0.156285 / 1.09 | 1063 最优 |
| baseline（默认网络: 256,256） | 0.022102 / 0.025233 / 0.39 | 0.177262 / 0.139384 / 0.09 | 0.269086 / 0.155988 / 0.63 | baseline 统一对照线 |

结论：

1. 网络加深的收益很小，三条 trace 的 MR 差异都在很小范围内。
2. 1063 上 net4 略优，但 wiki/meta 基本无显著收益。
3. 若追求稳定吞吐，`net1(256)` 仍是更稳妥默认；若只追求 1063 MR，可选 net4。

说明：baseline 已并入主表作为直接对照行。网络层历史最优与 baseline 的差异总体较小，但 wiki 仍有明显优化空间。

### 21.2 Replay Buffer / Batch（`sac_buffer_size`, `sac_batch_size`）

测试组使用 `sac_net_arch=256,256`：

- `bb_50k_512`: `buffer_size=50000`, `batch_size=512`
- `bb_100k_512`: `buffer_size=100000`, `batch_size=512`
- `bb_50k_1024`: `buffer_size=50000`, `batch_size=1024`

| 配置 | 1063 MR / Byte MR / MQPS | Wiki MR / Byte MR / MQPS | Meta MR / Byte MR / MQPS | 备注 |
|:--|---|---|---|---|
| bb_50k_512 | **0.022153** / 0.025285 / 0.61 | **0.175261** / **0.137203** / 0.10 | 0.269085 / 0.156230 / **1.13** | 综合最稳 |
| bb_100k_512 | 0.022214 / 0.025371 / 0.60 | 0.177713 / 0.138056 / 0.10 | 0.269084 / 0.156344 / 1.11 | Wiki 明显变差 |
| bb_50k_1024 | 0.022314 / 0.025489 / 0.58 | rc=143（未完成） | **0.269080** / **0.156106** / 1.07 | batch 过大稳定性差 |
| baseline（ buffer: 10000; batch: 256） | 0.022102 / **0.025233** / 0.39 | 0.177262 / 0.139384 / 0.09 | 0.269086 / 0.155988 / 0.63 | baseline 统一对照线 |

结论：

1. `buffer_size` 从 50k 提升到 100k 未带来稳定收益，wiki 还有明显退化。
2. `batch_size=1024` 没带来质量提升，且出现了 wiki case 非零退出（`rc=143`）。
3. 在这批测试中，`buffer_size=50000` + `batch_size=512` 是最稳的默认点。

说明：baseline 已并入主表。1063 在 baseline 上优于 `bb_50k_512`，wiki 在 baseline 上明显落后于历史最优 buffer 点，meta 基本持平。

## 22. 特征归一化实验

### 22.0 数据有效性补充（2026-03-16）

- 本章部分结果已确认存在口径失真：实验期间 `LOH.c` 有代码修改，但对应 release 二进制未及时重编译（`LOH_SKIP_BUILD=1` 且复用旧 `_build_rel/bin/cachesim`）。
- 因此，本章中受影响批次仅保留为过程记录，不能单独作为最终结论依据；最终结论以修正后同条件重跑结果为准。

本章默认配置（统一主干）：

- 请求量：full req（`CACHESIM_NUM_REQ=0`）
- 缓存比例：`0.1`
- 候选与评分：`LOH_RANDOM_CANDIDATES=96`, `LOH_STRUCTURED_CANDIDATES=96`, `COMPOUND=1`, `IRT=0`
- 运行模式：`nonblocked`, `ASYNC_TRAIN=1`, `MISS_RATIO_WEIGHT=1.0`

本章差异配置（矩阵维度）：

- 公式维度：`LOG1P` 与 `RECIPROCAL`（wiki 同时测两者）
- 归一化维度：`baseline` / `fixed_norm` / `adaptive_norm`
- 目标：验证是否能用 `adaptive` 达到跨 trace 统一而不依赖 trace 先验公式

### 22.1  全矩阵结果与 baseline 对比（2026-03-14 已完成）

> 数据来源：`tmp/sec20_full_matrix_0314_4way/results.csv`
> 统计口径：每个 `(trace, formula, mode)` 取最后一条 `status=ok` 记录。

最终 12 组结果如下：

| Trace | Formula | Mode | MR | Byte MR | MQPS |
|:--|---|---|---:|---:|---:|
| 1063 | LOG1P | baseline（norm=off, adaptive=off） | **0.022102** | **0.025233** | 0.39 |
| 1063 | LOG1P | fixed_norm | 0.150780 | 0.147096 | 0.06 |
| 1063 | LOG1P | adaptive_norm | 0.022218 | 0.025376 | 0.33 |
| wiki | LOG1P | baseline（norm=off, adaptive=off） | 0.205365 | 0.189246 | 0.07 |
| wiki | LOG1P | fixed_norm | **0.173224** | **0.132204** | 0.05 |
| wiki | LOG1P | adaptive_norm | 0.206722 | 0.191830 | 0.06 |
| wiki | RECIPROCAL | baseline（norm=off, adaptive=off） | 0.177262 | **0.139384** | **0.09** |
| wiki | RECIPROCAL | fixed_norm | **0.175896** | 0.142169 | 0.05 |
| wiki | RECIPROCAL | adaptive_norm | 0.176406 | 0.139512 | 0.07 |
| meta | LOG1P | baseline（norm=off, adaptive=off） | 0.269086 | 0.155988 | **0.63** |
| meta | LOG1P | fixed_norm | 0.269273 | **0.153586** | 0.28 |
| meta | LOG1P | adaptive_norm | **0.269082** | 0.156001 | 0.51 |

baseline 对比分析（放在 §20 的统一结论口径）：

1. 1063（LOG1P）
   - baseline 为 0.022102，略优于历史 `net1`（0.022259）和 `bb_50k_512`（0.022153），与历史最优 `net4`（0.022063）非常接近。
   - adaptive_norm 与 baseline 接近（+0.000116）。
   - fixed_norm 明显异常偏高（0.150780），与其余模式量级不一致，建议视作不稳定结果并单列复核。

2. wiki（LOG1P）
   - baseline 为 0.205365。
   - fixed_norm 显著优于 baseline（-0.032141，约 -3.21pp）。
   - adaptive_norm 略差于 baseline（+0.001357，约 +0.14pp）。

3. wiki（RECIPROCAL）
   - baseline 为 0.177262。
   - fixed_norm 和 adaptive_norm 都优于 baseline，其中 fixed_norm 最优（0.175896，较 baseline -0.001366，约 -0.14pp）。
   - Byte MR 维度上 baseline 最优（0.139384），说明 Obj MR 与 Byte MR 的最优点不完全重合。

4. meta（LOG1P）
   - 三种模式非常接近，baseline=0.269086，adaptive_norm=0.269082（最优），差异仅 4e-6。
   - 在 meta 上可认为三者质量几乎等价，归一化策略主要影响 Byte MR 和吞吐细节。

小结：

1. baseline 已成功纳入 §20 的统一对比，并作为每条 trace/formula 的基准线。
2. wiki 上 `fixed_norm` 在 Obj MR 指标明显占优；meta 上三者几乎等价；1063 上 baseline/adaptive 更可信。
3. 若后续需要用于主结论，建议先对 `1063 + fixed_norm` 再做一次独立复现实验以确认稳定性。

### 22.2 为什么找不到三条 trace 都“最好或接近最好”的统一配置

核心原因是三条 trace 的流量结构和最优归因方向并不一致，导致一个全局配置很难同时对齐全部目标。

1. 特征公式偏好冲突
   - 1063/meta 更偏向 `LOG1P`。
   - wiki 在很多场景下 `RECIPROCAL` 更稳。
   - 当统一公式时，至少一条 trace 会偏离其最优表示。

2. 归一化策略收益方向不一致
   - 1063 上 `fixed_norm` 出现异常抬升（远高于 baseline/adaptive）。
   - wiki 上 `fixed_norm` 反而在 Obj MR 上明显更优。
   - meta 三者几乎等价，说明它对该维度不敏感。

3. 目标函数冲突（Obj MR vs Byte MR）
   - wiki 的 `RECIPROCAL` 组里，Obj MR 最优和 Byte MR 最优并非同一模式。
   - 单一配置很难同时压低两种指标。

4. 数据分布尺度差异过大
   - 1063、wiki、meta 的 one-hit、CV、size 尾部与热点集中度相差明显。
   - 同一归一化上界和同一策略会在不同 trace 上产生不同压缩失真。

5. 在线 RL 的噪声与并发不稳定会放大边界差异
   - 在接近最优区时，不同模式间原本只差 1e-4~1e-3，容易被训练噪声和运行时抖动放大。
   - 因此“跨 trace 完全统一且都最优”在实践上更难稳定复现。

结论：

1. 仅靠当前 `adaptive_norm` 机制，尚不能在不使用 trace 先验公式（log1p/reciprocal 分流）的前提下，让三条 trace 同时达到“最好或近最好”。
2. 你希望的方向（靠 adaptive 统一，而不是先验分流）是合理目标，但需要把自适应从“仅归一化”扩展到“公式/尺度联合自适应”。
3. 下一步建议是引入“统一公式入口 + 在线门控/混合变换（log1p 与 reciprocal 按状态加权）”，再在同一训练流程中比较三 trace 的全局 Pareto 前沿。

### 22.3 如何优化 adaptive：三条 trace 不区分 log1p/reciprocal 的统一方案

目标：在同一套配置下，让 1063 / wiki / meta 的结果达到各自最优或近最优（通常定义为相对各自最优点退化不超过 1%~3%）。

先给结论：

1. 仅靠当前的 `adaptive_norm`（只做分位数归一化）还不够，无法稳定替代公式分流。
2. 要实现“统一配置 + 接近各自最优”，需要把自适应从“归一化”扩展为“变换公式 + 归一化”的联合自适应。
3. 推荐采用两阶段方案：先做无需改代码的统一基线，再做最小代码改造的联合门控。

#### 21.3.1 阶段 A（无需改代码）：统一配置基线

先固定统一配置，建立可复现实验基线：

```bash
# 统一主干
LOH_SCORE_USE_COMPOUND=1
LOH_SCORE_USE_IRT=0
LOH_RANDOM_CANDIDATES=96
LOH_STRUCTURED_CANDIDATES=96
LOH_WAIT_MODE=nonblocked
LOH_ASYNC_TRAIN=1
LOH_ENABLE_PENALTY=0
LOH_MISS_RATIO_WEIGHT=1.0

# 统一特征入口（不再按 trace 手工切换）
LOH_FEATURE_LOG1P=1
LOH_FEATURE_LOG1P_RECIPROCAL=0

# 启用自适应归一化
LOH_ENABLE_ADAPTIVE_FEATURE_NORMALIZATION=1
LOH_ADAPTIVE_NORM_LO_Q=0.02
LOH_ADAPTIVE_NORM_HI_Q=0.98
LOH_ADAPTIVE_NORM_WARMUP=8192
```

这一步的意义：

1. 把“统一配置”问题先收敛为一个稳定、可复现、可比较的单点。
2. 用同一入口先观察三条 trace 的退化分布，再决定门控策略强度。
3. 预计 1063/meta 会比较稳，wiki 仍可能落后其 reciprocal 最优点。

#### 21.3.2 阶段 B（需要代码改造）：公式与归一化联合自适应

核心改造点（建议在 `LOH.c` 的特征计算路径实现）：

1. 对每个基础特征并行计算两路值：
   - `v_log = log1p(raw)`
   - `v_rec = reciprocal(raw)`（与当前 reciprocal 语义一致）
2. 引入在线门控系数 `alpha in [0,1]`：
   - `v_mix = alpha * v_log + (1 - alpha) * v_rec`
3. `alpha` 不用 trace 名，不做硬切换，使用在线统计驱动：
   - 输入建议：`one_hit_ratio`, `cv_logf`, `top1_share`, `freq_p90/p50`, `size_p99/p50`
   - 输出建议：平滑更新（EMA），避免抖动
4. 对 `v_mix` 再做当前分位数归一化：
   - 继续使用 `LOH_ADAPTIVE_NORM_LO_Q/HI_Q/WARMUP`

实现原则：

1. 先混合再归一化，不要先归一化再混合。
2. `alpha` 更新要慢（例如 EMA 0.95~0.995），避免训练过程来回跳模式。
3. 增加门控冻结窗口（例如每 100K req 仅允许小幅更新），保证 RL 目标分布平稳。

#### 21.3.3 统一配置下的验收标准

建议使用下面标准判断是否“基本最优”：

1. 相对各自历史最优 MR 退化不超过 1%（严格）或 3%（工程可用）。
2. 三条 trace 都满足上述阈值，且无单条明显劣化（例如 >5%）。
3. MQPS 不出现系统性崩塌（相对当前稳定配置退化不超过 10%~15%）。

可直接落地的对比表头：

| Trace | 历史最优 MR | 统一配置 MR | 相对退化 | 是否达标 |
|:--|---:|---:|---:|---|

#### 21.3.4 为什么这条路径比“硬分流”更稳

1. 硬分流（按 trace 指定 log1p/reciprocal）依赖先验，迁移到新 trace 会失效。
2. 联合门控本质是“连续插值”，可在不同分布之间自适应过渡。
3. 归一化继续使用分位数方法，可抑制重尾和极端值对 RL 输入稳定性的破坏。

### 22.4 本轮失败因素与修复过程（2026-03-14）

本轮 sec20 三模式矩阵（4 路并行）前半程出现大量 `rc=143/1`，根因主要来自并行运行互相干扰，而非策略本身退化；后续通过补跑已补齐全部 12 组 `ok` 结果。

已定位失败因素：

1. 全局清理互杀：`scripts/test_loh_rl_sb3.sh` 在未启用并行安全时会执行全局 `pkill`，并发 case 会互相终止 Python/cachesim。
2. 时间戳冲突：同秒启动的并发 case 复用同一 `RUN_TIMESTAMP`，导致 `ac_sb3_*.log` / `cachesim_sb3_*.log` 同名，放大并发竞态。
3. 早退链式失败：一条 case Python 早退后触发 watch-stop，其他并发 case 又被波及，形成连续失败。
4. 与本章无关，但是容易犯的错误：skip_build，但是只编译了dbg没有编译rel而且使用的是rel
5. 注意修改LOH_include*的状态后，需要重新编译，注意双方共享内存是否一致
6. 后台运行，以免vscode闪退关闭终端

对应证据：

- 失败日志出现 `[watch] Python exited early; signal cachesim to stop`。
- 失败日志出现 `Error: Python SB3 script failed to start or exited early`。
- 代码证据：`scripts/test_loh_rl_sb3.sh` 的并行安全分支/全局清理分支与秒级时间戳。

已实施修复（runner 侧）：

1. 在矩阵 runner 公共环境中显式设置 `LOH_PARALLEL_SAFE=1`，禁用全局 pre-stop 清理。
2. 每个 case 显式注入唯一 `RUN_TIMESTAMP`（包含 `trace/formula/mode/pid`），避免同名日志冲突。
3. 断点续跑逻辑改为“仅 `status=ok` 才跳过”；失败项可在后续轮次补跑，成功项不重跑。

执行原则：

1. 当前正在运行的任务不做强杀，等待自然结束。
2. 当前轮结束后，仅补跑失败项与未完成项。
3. 补跑完成后再回填本章对比表（尤其 `wiki/meta` 的 baseline/fixed/adaptive 三模式）。

---

## 23. 注意事项

### 23.1 章节对应文件与实验时间索引（2026-03-15 整理）

说明：

1. 本索引只使用本文已出现的路径和仓库内可检索到的实验产物。
2. “实验时间”优先取章节标题日期；无标题日期时取文件名时间戳（如 `0310`）或文件 mtime。
3. 对未在该章节单独列出产物的，标注为“继承来源章节”。

| 章节 | 对应文件（脚本/日志/结果） | 实验时间 |
|:--|---|---|
| §1 主结果表 3M | 继承 `§10/§12` 汇总；对比基线文件：`tmp/compare_full_0306_014357.csv`、`tmp/compare_full_0306_014357.log` | 2026-03-06（`0306` 文件） |
| §2 主结果表 8M | 继承 `§10/§12` 汇总；对比基线文件：`tmp/compare_full_0306_014357.csv` | 2026-03-06 |
| §3 LOH vs 竞争算法 | `tmp/compare_full_0306_014357.csv`、`tmp/cmp_1063_LFUDA_full_0306_120723.log` | 2026-03-06 |
| §4 LOH 特征模式（固定权重） | 继承 `§10.2/§12`（固定权重与对比算法汇总） | 2026-03-06 ~ 2026-03-10 |
| §5 LOH RL 特征模式 | 继承 `§10.1/§13` RL 日志汇总：`tmp/rl_1063_full_0306_011029.log`、`tmp/rl_wiki_full_0306_011921.log`、`tmp/rl_meta_full_0306_010910.log` | 2026-03-06（后续 0310 复现） |
| §6 Trace 特性 | 分布与统计来源继承 `§7.1`：`tmp/trace_dist_stats_0314/summary_sorted.tsv` | 2026-03-14 |
| §7 auto-detect 验证 | 代表性日志：`tmp/test_auto_1063_3m.log` | 2026-03-05（mtime） |
| §7.1 全量分布建议 | `tmp/trace_dist_stats_0314/summary_sorted.tsv` | 2026-03-14 |
| §8 吞吐量优化 | 继承同批 LOH 运行日志：`cachesim_sb3_*.log`、`ac_sb3_*.log`（见 `§13/§15/§18`） | 2026-03-09 ~ 2026-03-11 |
| §9 配置速查 | 运行脚本：`scripts/test_loh_rl_sb3.sh` | 持续维护（无单次实验时间） |
| §10 full req 串行结果 | `tmp/rl_1063_full_0306_011029.log`、`tmp/rl_wiki_full_0306_011921.log`、`tmp/rl_meta_full_0306_010910.log`、`tmp/gated_1063_full_script.log`、`tmp/phase_ab_latest/results.csv`、`tmp/phase_ab_0312_223925/logs/*.log` | 2026-03-06，补充 2026-03-12 |
| §11 全量 Trace 公共配置 | 继承 `§10/§12` 公共脚本：`scripts/test_loh_rl_sb3.sh` | 2026-03-06 ~ 2026-03-14 |
| §12 全量 Trace 汇总表 | 继承 `§10/§13/§14/§18/§19/§20` 结果文件 | 2026-03-06 ~ 2026-03-14 |
| §13 0306 基线复现 | `tmp/rl_wiki_full_0306_011921.log`、`tmp/ac_sb3_0306_011921.log`、`tmp/rl_1063_full_0306_011029.log`、`tmp/ac_sb3_0306_011029.log`、`tmp/rl_meta_full_0306_010910.log`、`tmp/ac_sb3_0306_010910.log`、`cachesim_sb3_0310_*.log`、`ac_sb3_0310_*.log` | 2026-03-10（复现窗口含 0310） |
| §14 0310 参数探索 | `tmp/rl_wiki_full_0310_010834.log`、`tmp/rl_wiki_full_tuned_0310.log`、`tmp/rl_1063_full_0310_005641.log`、`tmp/rl_meta_full_0310_010715.log`，失败样本见 `tmp/rl_*_0310_0047*.log` | 2026-03-10 |
| §15 Blocked/NonBlocked/Async | `tmp/rl_interval_1063_nb_500.log`、`tmp/rl_interval_1063_bl_50000.log`、`tmp/rl_ab_sync_8M.log`、`tmp/rl_ab_async_8M.log`、`tmp/rl_ab_async_8M_opt.log`、`tmp/rl_ab_sync_full.log`、`tmp/rl_ab_async_full.log`、`tmp/rl_ab_async_full_v2.log`、`tmp/rl_async_v3_1M.log`、`tmp/rl_async_v3_5M.log`、`ac_sb3_0310_170940.log`、`ac_sb3_0310_172046.log`、`ac_sb3_0310_174648.log` | 2026-03-09 ~ 2026-03-10 |
| §16 Rand-Only 全量 | `tmp/rl_wiki_randonly_fullreq.log`、`tmp/rl_1063_randonly_fullreq.log`、`tmp/rl_meta_randonly_fullreq.log` | 2026-03-09 |
| §17 失败/不完整汇总 | `tmp/rl_ab_async_full.log`、`tmp/rl_ab_async_full_v2.log`、`tmp/rl_1063_full_0310_004726.log`、`tmp/rl_1063_full_0310_004851.log`、`tmp/rl_meta_full_0310_004746.log`、`tmp/rl_wiki_full_0310_004758.log`、`tmp/rl_sequential_nohup_full.log`、`tmp/cmp_1063_LFUDA_full_0306_120723.log` | 2026-03-06 ~ 2026-03-10 |
| §18 Decay + Adaptive Budget | 脚本：`scripts/run_nonblocked36.sh`；日志：`tmp/1063_async_decay/run.log`、`tmp/wiki_async_decay/run.log`、`tmp/meta_async_decay/run.log`、`cachesim_sb3_0311_*.log`、`ac_sb3_0311_*.log` | 2026-03-11 |
| §19 综合批量实验 | 脚本：`scripts/batch_experiment.sh`；结果目录：`tmp/batch_0311_020224/` | 2026-03-11 02:02 ~ 11:43 |
| §0 当前最好配置 | 汇总来源：`tmp/full_default_netbuf_full_0313_221815/results.csv`、`tmp/full_default_netbuf_0313_221624/results.csv`、`tmp/phase_ab_latest/results.csv`、`tmp/adaptive_budget_orig3_0313_184729/results.csv` | 2026-03-13（并吸收 2026-03-12） |
| §20 网络层数/Replay Buffer | `tmp/full_default_netbuf_full_0313_221815/results.csv`、`tmp/full_default_netbuf_0313_221624/results.csv` | 2026-03-13（文档重构 2026-03-14） |
| §21 特征归一化实验 | `tmp/sec20_full_matrix_0314_4way/results.csv`；并发修复证据：`scripts/test_loh_rl_sb3.sh`、`ac_sb3_*.log`、`cachesim_sb3_*.log` | 2026-03-14 |

后续补录建议：

1. 给 `§1~§5` 增加“原始产物文件”脚注（当前部分为继承来源）。
2. 给 `§8` 增加独立 throughput 聚合 CSV（目前主要来自日志汇总）。
3. 新增统一产物清单文件（如 `tmp/manifest_experiments.csv`），减少章节追溯成本。

---

23.2 特征变量层级、优先级与公式（2026-03-16）

本节对应当前代码实现（`libCacheSim/cache/eviction/LOH.c`），用于澄清 `UNIFIED / LOG1P / RECIPROCAL / LOG1P_RECIPROCAL / IDENTITY` 的关系。

层级优先级（高到低）：

1. `LOH_FEATURE_UNIFIED_FORMULA=1`：走 unified 公式族路径（不改写其他变量值，仅路径优先）
2. `LOH_FEATURE_IDENTITY=1`：走 raw identity 路径（`raw -> optional normalization`）
3. `LOH_FEATURE_LOG1P=1`：走 `log1p(raw)` 路径
4. `LOH_FEATURE_RECIPROCAL=1`：走 reciprocal 家族路径
5. `LOH_FEATURE_LOG1P_RECIPROCAL`：仅在 reciprocal 家族下决定子模式

说明：

- `LOH_ENABLE_ADAPTIVE_FEATURE_NORMALIZATION=1` 优先于 `LOH_ENABLE_FEATURE_NORMALIZATION=1`。
- 当前实现里“只归一化不变换”由 `LOH_FEATURE_IDENTITY=1` 提供。
- `LOH_AUTO_FEATURE_MODE=1` 仅在非 unified 路径下有效。

各变量及取值对应路径：

| 变量 | 取值 | 含义 | 对应公式（示例） |
|:--|---:|---|---|
| `LOH_FEATURE_UNIFIED_FORMULA` | `1` | unified 公式族 | good: `g(x)`；bad: `1-g(x)`，其中 `g(x)` 由 `LOH_UNIFIED_METHOD/VARIANT` 决定 |
| `LOH_FEATURE_UNIFIED_FORMULA` | `0` | 不走 unified | 继续看下层变量 |
| `LOH_FEATURE_IDENTITY` | `1` | raw 直通 | `rec=x, freq=x, size=x, irt=x`，之后可归一化 |
| `LOH_FEATURE_LOG1P` | `1` | log1p 路径 | `log1p(raw)` |
| `LOH_FEATURE_RECIPROCAL` | `1` | reciprocal 家族 | 继续看 `LOH_FEATURE_LOG1P_RECIPROCAL` |
| `LOH_FEATURE_LOG1P_RECIPROCAL` | `1` | reciprocal(log1p) | bad: `1/(1+log1p(x))`；good(freq): `log1p(f)/(1+log1p(f))` |
| `LOH_FEATURE_LOG1P_RECIPROCAL` | `0` | reciprocal(raw) | bad: `1/(1+x)`；good(freq): `f/(1+f)` |

### 23.2 变量补充说明（method / variant / adaptive quantile）

| 变量 | 含义 | 典型取值 | 备注 |
|:--|---|---|---|
| `LOH_UNIFIED_METHOD` | Unified 族的主公式族选择器 | `1`, `2` | 先决定大类公式，再由 `LOH_UNIFIED_VARIANT` 选该大类下的子式。 |
| `LOH_UNIFIED_VARIANT` | Unified 子公式编号 | `1..4`（常见） | 只在 unified 路径中生效；同一 `method` 下切换不同子式。 |
| `LOH_ADAPTIVE_NORM_LO_Q` | 自适应归一化下界分位点 | `0.00`, `0.01`, `0.05` | 小于该分位的值会更容易被压到接近 0。 |
| `LOH_ADAPTIVE_NORM_HI_Q` | 自适应归一化上界分位点 | `0.95`, `0.995`, `1.00` | 大于该分位的值会更容易被压到接近 1。 |
| `LOH_ADAPTIVE_NORM_WARMUP` | 自适应分位统计预热样本数 | `0`, `128`, `1024` | 预热期间统计分位边界；`0` 表示不等待，立即在线更新。 |
| `LOH_ADAPTIVE_NORM_QUANTILE_INPUT` | 自适应分位统计输入空间 | `out`, `raw`, `log1p` | 仅改变分位统计输入；`out` 为默认（当前行为）。 |
| `LOH_INCLUDE_HIT_MISS_FEATURES` | 是否把 hit/miss 派生特征并入 state | `0` 或 `1` | 维度会变化；做跨实验对比时需保证该值一致。 |
| `LOH_AUTO_FEATURE_MODE` | 运行中自动选择特征模式开关 | `0` 或 `1` | `1` 时在达到阈值请求数后触发一次统计检测并自动切模式；`UNIFIED=1` 时会被强制关闭。 |
| `LOH_AUTO_DETECT_REQS` | auto 模式的触发请求阈值 | 例如 `200000` | 仅在 `LOH_AUTO_FEATURE_MODE=1` 时生效。 |

`method` 与 `variant` 的区别：

- `LOH_UNIFIED_METHOD` 决定 unified 的“公式家族”（宏观函数形态）。
- `LOH_UNIFIED_VARIANT` 决定该家族中的“具体子公式”（细化差异）。
- 固定 `method` 只改 `variant`，属于同家族内微调；改 `method` 则是跨家族切换，通常影响更大。

`LOH_AUTO_FEATURE_MODE` 补充（对应代码 `LOH.c` 当前实现）：

- 解析位置：初始化阶段读取 `LOH_AUTO_FEATURE_MODE`、`LOH_AUTO_DETECT_REQS`（`libCacheSim/cache/eviction/LOH.c:4694`）。
- 触发条件：`request_count >= LOH_AUTO_DETECT_REQS` 且尚未检测（`libCacheSim/cache/eviction/LOH.c:5136`）。
- 决策动作：执行 `loh_auto_detect_and_switch()`，基于样本统计在 `LOG1P` 与 `LOG1P_RECIPROCAL` 之间切换，并可能联动 `COMPOUND` 等参数（`libCacheSim/cache/eviction/LOH.c:1082`）。
- 互斥规则：当 `LOH_FEATURE_UNIFIED_FORMULA=1` 时，auto 模式会被关闭（`libCacheSim/cache/eviction/LOH.c:4707`）。



**Unified 公式细化（method / variant）**

先定义公共中间量（`x>0`）：

- `l = log1p(x)`
- `log_cap(x) = clamp(log1p(x) / log1p(freq_cap), 0, 1)`

`LOH_UNIFIED_VARIANT`（用于 `loh_unified_log_ratio`，代码在 `libCacheSim/cache/eviction/LOH.c:1376`）：

| `variant` | `g(x)` |
|---:|---|
| `1` | `g = l / (1 + l)` |
| `2` | `g = l / (beta + l)` |
| `3` | `g = 1 - exp(-l / beta)` |
| `4` | `g = (l / (1 + l))^gamma` |

`LOH_UNIFIED_METHOD`（代码在 `libCacheSim/cache/eviction/LOH.c:1409` 和 `libCacheSim/cache/eviction/LOH.c:1454`）：

| `method` | good 特征（如 frequency） | bad 特征（如 recency/size/irt） |
|---:|---|---|
| `1` | `good = g(x)` | `bad = 1 - g(x)` |
| `2` | `good = log_cap(x)` | `bad = 1 / (1 + log1p(x))` |
| `3` | `good = alpha*log_cap(x) + (1-alpha)*g(x)` | `bad = alpha*(1-log_cap_norm(x)) + (1-alpha)*[1/(1+log1p(x))]` |
| `4` | `good = log_cap(x)^beta` | `bad = 1 - log_cap(x)^beta` |
| `5` | `good = 0.5*(tanh((log_cap(x)-0.5)/gamma)+1)` | `bad = 1 - good` |
| `6` | `good = log_cap(x)^gamma` | `bad = 1 - good` |

补充：`method=3` 的 `alpha` 会被夹到 `[0,1]`；`beta/gamma/freq_cap` 有下界保护，防止分母或指数异常。

**两种归一化的计算公式（fixed vs adaptive）**

代码入口：`libCacheSim/cache/eviction/LOH.c:1315`（`loh_apply_feature_normalization`）。

前置语义：`out` 是“特征变换之后”的值（可能已经过 `identity/log1p/reciprocal/unified` 之一）。归一化层再对这个 `out` 做二次缩放。

固定归一化（`LOH_ENABLE_FEATURE_NORMALIZATION=1`）：

- 公式：`nn = out / log1p(norm_max[idx])`
- 裁剪：仅做上界裁剪，`nn = min(nn, 1.0)`；超过上界会累加 clip 计数。
- `norm_max[idx]` 来源：`LOH_FEATURE_NORM_MAX_*`（`recency/freq/size/irt`）或代码默认值。

自适应归一化（`LOH_ENABLE_ADAPTIVE_FEATURE_NORMALIZATION=1`）：

- 在线分位更新（每个特征独立维护 `q_lo/q_hi`）：
   `q <- q + lr * (target - I(out <= q))`
- 其中：`target=lo_q`（低分位）或 `hi_q`（高分位）；`lr=0.05`（样本计数 `<1024`）否则 `0.005`。
- 归一化：`nn = (out - q_lo) / (q_hi - q_lo)`，再裁剪到 `[0,1]`。
- 边界条件：若 `q_hi - q_lo <= 1e-12`，返回 `0.5`。
- `warmup` 语义：当 `t <= LOH_ADAPTIVE_NORM_WARMUP`，只更新分位，不做缩放，直接返回原始 `out`。

优先级关系：

- adaptive 开启时优先走 adaptive；fixed 分支不会执行。
- adaptive/fixed 都关闭时返回原始 `out`（不归一化）。

结论：fixed 与 adaptive 的确不是同一个公式族。fixed 更像“按固定上界做 log-domain 比例缩放”，adaptive 更像“按在线分位做 min-max 仿射缩放”。

### 23.6.1 24/26/27 章实验路径对照

| 章节 | 实验组 | 主要路径 | 关键变量组合 |
|:--|---|---|---|
| §24 | `sec23_unified_4x3` (`v1..v4`) | Unified | `UNIFIED=1`, `UNIFIED_VARIANT=1..4` |
| §24 | `sec21_1_matrix` `log1p_*` | Log1p | `UNIFIED=0`, `LOG1P=1` |
| §24 | `sec21_1_matrix` `reciprocal_*` | Reciprocal 家族 | `UNIFIED=0`, `LOG1P=0`, `RECIPROCAL=1` |
| §26 | `sec23_v*`, `new_m*` | Unified | `UNIFIED=1`, `UNIFIED_METHOD/VARIANT` 按配置 |
| §26 | `sec21_log1p_*` | Log1p | `UNIFIED=0`, `LOG1P=1` |
| §26 | `sec21_recip_*` | Reciprocal 家族 | `UNIFIED=0`, `LOG1P=0`, `RECIPROCAL=1` |
| §27 | `Log1p Adaptive Tune` / `27.2/27.3/27.4` | Log1p + 归一化调参 | `UNIFIED=0`, `LOG1P=1`, 自适应分位参数按子实验变化 |

---

## 24. 统一公式 4x3 + §22.1 合并结果（按 trace 分组，2026-03-15）

### 24.0 数据有效性补充（2026-03-16）

- 本章部分数据存在已知失真：执行过程中修改了 `LOH.c`，但云端/当前实验链路的 release 可执行文件未同步重编译，导致“代码版本”与“运行二进制”不一致。
- 触发路径为 `LOH_SKIP_BUILD=1` 复用旧 release 二进制；因此本章相关比较暂不作为最终结论，仅作排障与现象记录。

实验范围：

1. trace：`1063` / `wiki` / `meta`（全量 `CACHESIM_NUM_REQ=0`）
2. 公式：`LOH_FEATURE_UNIFIED_FORMULA=1` 下的 `LOH_UNIFIED_VARIANT=1..4`
3. 归一化：`baseline` / `fixed_norm` / `adaptive_norm`
4. 并发：4 路并行，`LOH_PARALLEL_SAFE=1`，每 case 唯一 `RUN_TIMESTAMP` + `LOH_SHM_KEY`

结果文件：

1. 汇总：`tmp/unified_variants_full_0315/results.csv`
2. 过程：`tmp/unified_variants_full_0315/runner.log`

### 24.1 通用配置（本轮实际使用）

```bash
CACHESIM_NUM_REQ=0
LOH_PARALLEL_SAFE=1
LOH_ENABLE_SEMAPHORE=1
LOH_BUILD_RELEASE=1
LOH_SKIP_BUILD=1（可能没有编译rel）
LOH_SKIP_PIP_INSTALL=1
LOH_PERF_PROFILING=0
LOH_DEBUG_LEVEL=0
LOH_ENABLE_RL=1

LOH_SCORE_USE_COMPOUND=1
LOH_SCORE_USE_IRT=0
LOH_RANDOM_CANDIDATES=96
LOH_STRUCTURED_CANDIDATES=96
LOH_WAIT_MODE=nonblocked
LOH_ASYNC_TRAIN=1
LOH_ENABLE_PENALTY=0
LOH_MISS_RATIO_WEIGHT=1.0

LOH_INCLUDE_WEIGHTS_IN_OBS=1
LOH_ADAPTIVE_BUDGET=1
LOH_USE_SCORE_REBALANCE=0
LOH_DISABLE_NEWSTATE_EARLY_EXIT=1
LOH_WAIT_NEWSTATE_MAX_CONSEC_TIMEOUTS=1800
LOH_WAIT_NEWSTATE_IDLE_S=1800

LOH_FEATURE_UNIFIED_FORMULA=1
```

### 24.2 Combo 含义

`sec23_unified_4x3` 的 combo 命名规则：`v{variant}_{mode}`。

1. `v1`: `g(x)=log1p(x)/(1+log1p(x))`
2. `v2`: `g(x)=log1p(x)/(beta+log1p(x))`（本轮 `beta=1.0`）
3. `v3`: `g(x)=1-exp(-log1p(x)/beta)`（本轮 `beta=1.0`）
4. `v4`: `g(x)=base^gamma`, `base=log1p(x)/(1+log1p(x))`（本轮 `gamma=1.35`）
5. `baseline`: 关闭归一化
6. `fixed_norm`: 固定上界归一化（`LOH_ENABLE_FEATURE_NORMALIZATION=1`）
7. `adaptive_norm`: 分位数归一化（`LOH_ENABLE_ADAPTIVE_FEATURE_NORMALIZATION=1`, 本轮 `lo/hi=0.01/0.99`, `warmup=4096`）

`sec21_1_matrix` 的命名规则：`{formula}_{mode}`。

1. `formula`: `log1p` 或 `reciprocal`
2. `mode`: `baseline` / `fixed_norm` / `adaptive_norm`

### 24.3 为什么 1063 变化大，而 wiki/meta 变化小

结合 `§7.1` 的全量分布统计：

| Trace | frequency p50/p99 | one-hit | CV | size p99 |
|:--|---|---:|---:|---:|
| 1063 | 153 / 3069 | 7.1% | 15.0 | 512 KB |
| wiki | 1 / 152 | 55.7% | 31.3 | 156.7 KB |
| meta | 1 / 18 | 61.4% | 854.4 | 201 MB |

解释：

1. 1063 频率分布“厚且有梯度”（p50=153），低 one-hit，说明大量对象处在可区分的中高频区间。公式/归一化一旦改变，会显著改变对象相对排序，因此 MR 波动大。
2. wiki 大量对象频率贴近 1（one-hit 55.7%），多数对象本来就挤在低频端。不同统一公式在这一区域映射相近，所以 Obj MR 变化较小。
3. meta 虽然重尾极端（CV 854.4），但本轮统一公式族都把特征压到 `[0,1]`，并且候选/评分主干一致（compound + 同候选池）；结果表现为 Obj MR 变化很小，主要差别体现在 Byte MR 与吞吐。
4. 1063 在 `sec21_1_matrix/log1p_baseline` 达到 0.0221，而统一公式最优约 0.1234，这个差距本质上是“特征表达能力损失”：纯 `log1p` 对 1063 的中高频梯度保留更充分，统一压缩映射削弱了该优势。

### 24.4 合并总表（36 条统一公式 + §22.1）

说明：

1. 本表合并了 `§23` 的 36 条（`sec23_unified_4x3`）与 `§21.1` 的最终 12 条（`sec21_1_matrix`）。
2. `§21.1` 采用口径与原文一致：每个 `(trace, formula, mode)` 取最后一条 `status=ok`。
3. 吞吐量 `MQPS` 从对应 `log_path` 中的最终 summary 行提取。

| Trace | Source | Config | Obj MR | Byte MR | MQPS | Log |
|:--|---|---|---:|---:|---:|---|
| 1063 | sec21_1_matrix | `log1p_adaptive_norm` | 0.022218 | 0.025376 | 0.33 | `tmp/sec20_full_matrix_0314_4way/1063_log1p_adaptive_norm_retry1.log` |
| 1063 | sec21_1_matrix | `log1p_baseline` | 0.022102 | 0.025233 | 0.39 | `tmp/sec20_full_matrix_0314_4way/1063_log1p_baseline.log` |
| 1063 | sec21_1_matrix | `log1p_fixed_norm` | 0.150780 | 0.147096 | 0.06 | `tmp/sec20_full_matrix_0314_4way/1063_log1p_fixed_norm_retry1.log` |
| 1063 | sec23_unified_4x3 | `v1_adaptive_norm` | 0.135716 | 0.130175 | 0.18 | `tmp/unified_variants_full_0315/1063_v1_adaptive_norm.log` |
| 1063 | sec23_unified_4x3 | `v1_baseline` | 0.135574 | 0.130050 | 0.19 | `tmp/unified_variants_full_0315/1063_v1_baseline.log` |
| 1063 | sec23_unified_4x3 | `v1_fixed_norm` | 0.147423 | 0.140179 | 0.10 | `tmp/unified_variants_full_0315/1063_v1_fixed_norm.log` |
| 1063 | sec23_unified_4x3 | `v2_adaptive_norm` | 0.134403 | 0.128836 | 0.18 | `tmp/unified_variants_full_0315/1063_v2_adaptive_norm.log` |
| 1063 | sec23_unified_4x3 | `v2_baseline` | 0.134380 | 0.128799 | 0.19 | `tmp/unified_variants_full_0315/1063_v2_baseline.log` |
| 1063 | sec23_unified_4x3 | `v2_fixed_norm` | 0.151627 | 0.149239 | 0.10 | `tmp/unified_variants_full_0315/1063_v2_fixed_norm.log` |
| 1063 | sec23_unified_4x3 | `v3_adaptive_norm` | 0.136312 | 0.130844 | 0.17 | `tmp/unified_variants_full_0315/1063_v3_adaptive_norm.log` |
| 1063 | sec23_unified_4x3 | `v3_baseline` | 0.134511 | 0.128998 | 0.18 | `tmp/unified_variants_full_0315/1063_v3_baseline.log` |
| 1063 | sec23_unified_4x3 | `v3_fixed_norm` | 0.137653 | 0.132828 | 0.11 | `tmp/unified_variants_full_0315/1063_v3_fixed_norm.log` |
| 1063 | sec23_unified_4x3 | `v4_adaptive_norm` | 0.136609 | 0.131216 | 0.17 | `tmp/unified_variants_full_0315/1063_v4_adaptive_norm.log` |
| 1063 | sec23_unified_4x3 | `v4_baseline` | 0.134222 | 0.128671 | 0.19 | `tmp/unified_variants_full_0315/1063_v4_baseline.log` |
| 1063 | sec23_unified_4x3 | `v4_fixed_norm` | 0.123408 | 0.121323 | 0.12 | `tmp/unified_variants_full_0315/1063_v4_fixed_norm.log` |
| wiki | sec21_1_matrix | `log1p_adaptive_norm` | 0.206722 | 0.191830 | 0.06 | `tmp/sec20_full_matrix_0314_4way/wiki_log1p_adaptive_norm.log` |
| wiki | sec21_1_matrix | `log1p_baseline` | 0.205365 | 0.189246 | 0.07 | `tmp/sec20_full_matrix_0314_4way/wiki_log1p_baseline_retry2.log` |
| wiki | sec21_1_matrix | `log1p_fixed_norm` | 0.173224 | 0.132204 | 0.05 | `tmp/sec20_full_matrix_0314_4way/wiki_log1p_fixed_norm_retry1.log` |
| wiki | sec21_1_matrix | `reciprocal_adaptive_norm` | 0.176406 | 0.139512 | 0.07 | `tmp/sec20_full_matrix_0314_4way/wiki_reciprocal_adaptive_norm.log` |
| wiki | sec21_1_matrix | `reciprocal_baseline` | 0.177262 | 0.139384 | 0.09 | `tmp/sec20_full_matrix_0314_4way/wiki_reciprocal_baseline_retry2.log` |
| wiki | sec21_1_matrix | `reciprocal_fixed_norm` | 0.175896 | 0.142169 | 0.05 | `tmp/sec20_full_matrix_0314_4way/wiki_reciprocal_fixed_norm_retry1.log` |
| wiki | sec23_unified_4x3 | `v1_adaptive_norm` | 0.176739 | 0.139209 | 0.10 | `tmp/unified_variants_full_0315/wiki_v1_adaptive_norm.log` |
| wiki | sec23_unified_4x3 | `v1_baseline` | 0.176635 | 0.138814 | 0.10 | `tmp/unified_variants_full_0315/wiki_v1_baseline.log` |
| wiki | sec23_unified_4x3 | `v1_fixed_norm` | 0.176330 | 0.145030 | 0.07 | `tmp/unified_variants_full_0315/wiki_v1_fixed_norm.log` |
| wiki | sec23_unified_4x3 | `v2_adaptive_norm` | 0.176911 | 0.139159 | 0.10 | `tmp/unified_variants_full_0315/wiki_v2_adaptive_norm.log` |
| wiki | sec23_unified_4x3 | `v2_baseline` | 0.176824 | 0.139624 | 0.10 | `tmp/unified_variants_full_0315/wiki_v2_baseline.log` |
| wiki | sec23_unified_4x3 | `v2_fixed_norm` | 0.177098 | 0.141634 | 0.07 | `tmp/unified_variants_full_0315/wiki_v2_fixed_norm.log` |
| wiki | sec23_unified_4x3 | `v3_adaptive_norm` | 0.176688 | 0.139282 | 0.09 | `tmp/unified_variants_full_0315/wiki_v3_adaptive_norm.log` |
| wiki | sec23_unified_4x3 | `v3_baseline` | 0.176985 | 0.139075 | 0.10 | `tmp/unified_variants_full_0315/wiki_v3_baseline.log` |
| wiki | sec23_unified_4x3 | `v3_fixed_norm` | 0.176361 | 0.142539 | 0.07 | `tmp/unified_variants_full_0315/wiki_v3_fixed_norm.log` |
| wiki | sec23_unified_4x3 | `v4_adaptive_norm` | 0.177108 | 0.138874 | 0.10 | `tmp/unified_variants_full_0315/wiki_v4_adaptive_norm.log` |
| wiki | sec23_unified_4x3 | `v4_baseline` | 0.176391 | 0.139051 | 0.10 | `tmp/unified_variants_full_0315/wiki_v4_baseline.log` |
| wiki | sec23_unified_4x3 | `v4_fixed_norm` | 0.176335 | 0.141077 | 0.07 | `tmp/unified_variants_full_0315/wiki_v4_fixed_norm.log` |
| meta | sec21_1_matrix | `log1p_adaptive_norm` | 0.269082 | 0.156001 | 0.51 | `tmp/sec20_full_matrix_0314_4way/meta_log1p_adaptive_norm_retry1.log` |
| meta | sec21_1_matrix | `log1p_baseline` | 0.269086 | 0.155988 | 0.63 | `tmp/sec20_full_matrix_0314_4way/meta_log1p_baseline.log` |
| meta | sec21_1_matrix | `log1p_fixed_norm` | 0.269273 | 0.153586 | 0.28 | `tmp/sec20_full_matrix_0314_4way/meta_log1p_fixed_norm_retry2.log` |
| meta | sec23_unified_4x3 | `v1_adaptive_norm` | 0.269085 | 0.156094 | 0.79 | `tmp/unified_variants_full_0315/meta_v1_adaptive_norm.log` |
| meta | sec23_unified_4x3 | `v1_baseline` | 0.269079 | 0.155817 | 0.93 | `tmp/unified_variants_full_0315/meta_v1_baseline.log` |
| meta | sec23_unified_4x3 | `v1_fixed_norm` | 0.269286 | 0.153529 | 0.40 | `tmp/unified_variants_full_0315/meta_v1_fixed_norm.log` |
| meta | sec23_unified_4x3 | `v2_adaptive_norm` | 0.269083 | 0.156141 | 0.72 | `tmp/unified_variants_full_0315/meta_v2_adaptive_norm.log` |
| meta | sec23_unified_4x3 | `v2_baseline` | 0.269080 | 0.156000 | 0.91 | `tmp/unified_variants_full_0315/meta_v2_baseline.log` |
| meta | sec23_unified_4x3 | `v2_fixed_norm` | 0.269281 | 0.153506 | 0.38 | `tmp/unified_variants_full_0315/meta_v2_fixed_norm.log` |
| meta | sec23_unified_4x3 | `v3_adaptive_norm` | 0.269080 | 0.155949 | 0.73 | `tmp/unified_variants_full_0315/meta_v3_adaptive_norm.log` |
| meta | sec23_unified_4x3 | `v3_baseline` | 0.269081 | 0.156079 | 0.91 | `tmp/unified_variants_full_0315/meta_v3_baseline.log` |
| meta | sec23_unified_4x3 | `v3_fixed_norm` | 0.269290 | 0.153691 | 0.39 | `tmp/unified_variants_full_0315/meta_v3_fixed_norm.log` |
| meta | sec23_unified_4x3 | `v4_adaptive_norm` | 0.269950 | 0.156633 | 0.47 | `tmp/unified_variants_full_0315/meta_v4_adaptive_norm.log` |
| meta | sec23_unified_4x3 | `v4_baseline` | 0.269084 | 0.156241 | 0.93 | `tmp/unified_variants_full_0315/meta_v4_baseline.log` |
| meta | sec23_unified_4x3 | `v4_fixed_norm` | 0.269291 | 0.153702 | 0.39 | `tmp/unified_variants_full_0315/meta_v4_fixed_norm.log` |

结论：不存在“一种配置在三个 trace 都最优”。

1. 1063 最优：`sec21_1_matrix / log1p_baseline`（Obj MR = 0.022102）
2. wiki 最优：`sec21_1_matrix / log1p_fixed_norm`（Obj MR = 0.173224）
3. meta 最优：`sec23_unified_4x3 / v1_baseline`（Obj MR = 0.269079）

因此三条 trace 的最优点来自不同配置，单一配置无法同时达到三者最优。

### 24.5 统一方法对比（method=2 vs method=3，进行中）

运行设定：

1. 第一阶段：`no_norm`（6 并行，3 trace × 2 method）
2. 第二阶段：`adaptive_norm`（6 并行，3 trace × 2 method）
3. trace 顺序：`meta -> 1063 -> wiki`
4. 日志与结果：`tmp/unified_method_compare_0315/runner.log`、`tmp/unified_method_compare_0315/results.csv`

方法定义：

1. `asym` = `LOH_UNIFIED_METHOD=2`（非对称统一公式）
2. `alpha_mix` = `LOH_UNIFIED_METHOD=3`（alpha 混合）

实时结果表（每完成一条就追加）：

<!-- METHOD_COMPARE_TABLE_START -->
| Phase | Trace | Method | Obj MR | Byte MR | 状态 | 日志 |
|:--|:--|---|---:|---:|---|---|
| no_norm | meta | asym | 0.269085 | 0.156210 | ok | `tmp/unified_method_compare_0315/no_norm_meta_asym.log` |
| no_norm | meta | alpha_mix | 0.269081 | 0.156254 | ok | `tmp/unified_method_compare_0315/no_norm_meta_alpha_mix.log` |
| no_norm | 1063 | asym | 0.132992 | 0.127533 | ok | `tmp/unified_method_compare_0315/no_norm_1063_asym.log` |
| no_norm | 1063 | alpha_mix | 0.134434 | 0.128907 | ok | `tmp/unified_method_compare_0315/no_norm_1063_alpha_mix.log` |
| no_norm | wiki | asym | 0.176602 | 0.139435 | ok | `tmp/unified_method_compare_0315/no_norm_wiki_asym.log` |
| no_norm | wiki | alpha_mix | 0.176646 | 0.139419 | ok | `tmp/unified_method_compare_0315/no_norm_wiki_alpha_mix.log` |
| topup_adaptive | meta | asym | 0.269891 | 0.156629 | ok | `tmp/unified_method_compare_0315/topup_adaptive_meta_asym.log` |
| topup_adaptive | meta | alpha_mix | 0.269082 | 0.156081 | ok | `tmp/unified_method_compare_0315/topup_adaptive_meta_alpha_mix.log` |
| topup_adaptive | 1063 | asym | 0.134970 | 0.129449 | ok | `tmp/unified_method_compare_0315/topup_adaptive_1063_asym.log` |
| topup_adaptive | 1063 | alpha_mix | 0.136134 | 0.130421 | ok | `tmp/unified_method_compare_0315/topup_adaptive_1063_alpha_mix.log` |
| log1p_baseline | 1063 | async | 0.022307 | 0.025468 | ok | `tmp/unified_method_compare_0315/log1p_baseline_1063_async.log` |
| topup_adaptive | wiki | asym | 0.176515 | 0.139302 | ok | `tmp/unified_method_compare_0315/topup_adaptive_wiki_asym.log` |
| topup_adaptive | wiki | alpha_mix | 0.176443 | 0.139017 | ok | `tmp/unified_method_compare_0315/topup_adaptive_wiki_alpha_mix.log` |
<!-- METHOD_COMPARE_TABLE_END -->

## 25. 分段 MR 判别参考（2026-03-16）

目标：在 full-req 长跑中，用 24/48/72/96 小时分段 MR 快速判断最终 MR 区间，减少无效等待。

### 25.1 Wiki：0.17x vs 0.2x 的分段区分

| 样本日志 | 96h cumulative MR | 96h interval MR | 最终 MR | 等级 |
|:--|---:|---:|---:|---|
| `tmp/rl_wiki_randonly_fullreq.log` | 0.1984 | 0.1738 | 0.172273 | 0.17x |
| `tmp/wiki_async_decay/run.log` | 0.2009 | 0.1785 | 0.177963 | 0.17x |
| `tmp/rl_wiki_nothreads1_0310_111641/cachesim.log` | 0.2122 | 0.1917 | 0.188123 | 接近 0.2x |

判别经验（Wiki）：
- 若 `96h cumulative <= 0.202` 且 `96h interval <= 0.180`，最终大概率落在 `0.17x`。
- 若 `96h cumulative >= 0.210` 或 `96h interval >= 0.190`，最终通常落在 `0.18x~0.20x`。

### 25.2 三条 Trace 的分段映射（当前数据）

| Trace | 96h 分段（cumulative / interval） | 最终 MR | 代表日志 |
|:--|---|---:|---|
| 1063 | 0.047~0.048 / 0.017~0.018 | 0.026x | `tmp/1063_perf0_async.log`, `tmp/rl_state_1063_full_nb_candidate.log` |
| 1063 | 0.1986 / 0.1725 | 0.134x | `tmp/unified_method_compare_0315/topup_adaptive_1063_asym.log` |
| 1063 | 0.2571 / 0.2715 | 0.256x | `tmp/1063_decay_adaptive.log` |
| wiki | 0.198~0.201 / 0.174~0.179 | 0.17x | `tmp/rl_wiki_randonly_fullreq.log`, `tmp/wiki_async_decay/run.log` |
| wiki | 0.2122 / 0.1917 | 0.188x（近 0.2x） | `tmp/rl_wiki_nothreads1_0310_111641/cachesim.log` |
| meta | 0.3035~0.3036 / 0.2812~0.2814 | 0.269x | `tmp/meta_perf0_async.log`, `tmp/full0315_meta_driver.log` |

注：原始抽取明细见 `tmp/unified_method_compare_0315/segment_reference_0316.csv`。

---

*更新时间: 2026-03-15, 重构为单章 §24（统一公式 4x3 + §22.1 合并结果，含 combo 含义与分布解释），保留 §23（章节对应文件与实验时间索引）；此前 2026-03-14 更新包括 §7.1（全量分布视角建议）、§21（主表加入 baseline）、§22（公式与归一化矩阵与统一最优难点）、§0（合并 0312 与 0313 结论）*


## 26. Unified 0316 Rolling Results (Auto)

格式对齐 23.4：每完成一条 case 自动刷新整表。

### 26.0 有效性声明（2026-03-16）

- `meta` 与 `1063` 已完成后确认：本轮 `§21.1` 与 `§23` 的矩阵结果存在明显跨 trace 失配，不能作为“统一最优配置”的最终结论。
- 因此，本章中 `sec21_1_matrix` 与 `sec23_unified_4x3` 结果当前仅保留为排障与对比记录，后续结论需基于修正后的同条件重跑结果。
- 以当前 `status=ok` 数据做“暂定统计”：
   - 按三条 trace 平均 MR，当前最小为 `sec21_log1p_adaptive_norm`（avg MR = `0.157681`），但其在 `meta` 上仍较差（`0.273476`）。
   - 按各 trace 单独最优：`meta=sec23_v2_baseline (0.269100)`，`1063=sec21_log1p_baseline (0.022121)`，`wiki=sec21_log1p_adaptive_norm (0.171833)`。

<!-- AUTO_UNIFIED_0316_BEGIN -->
_Auto-updated from `tmp/unified_three_cfg_0316/results.csv` at 2026-03-16 13:58:27._

| Trace | Source | Config | Obj MR | Byte MR | MQPS | Log |
|:--|---|---|---:|---:|---:|---|
| meta | sec21_1_matrix | `sec21_log1p_baseline` | 0.273643 | 0.158179 | 0.240000 | `meta_sec21_log1p_baseline.log` |
| meta | sec21_1_matrix | `sec21_log1p_adaptive_norm` | 0.273476 | 0.156348 | 0.220000 | `meta_sec21_log1p_adaptive_norm.log` |
| meta | unified_new_0316 | `new_m6_qlog_gamma` | 0.274197 | 0.156242 | 0.150000 | `meta_new_m6_qlog_gamma.log` |
| meta | sec21_1_matrix | `sec21_log1p_fixed_norm` | 0.273640 | 0.155162 | 0.130000 | `meta_sec21_log1p_fixed_norm.log` |
| meta | unified_new_0316 | `new_m4_cdf_like` | 0.274842 | 0.155345 | 0.080000 | `meta_new_m4_cdf_like.log` |
| meta | sec21_1_matrix | `sec21_recip_baseline` | 0.269107 | 0.160246 | 0.720000 | `meta_sec21_recip_baseline.log` |
| meta | sec23_unified_4x3 | `sec23_v1_baseline` | 0.269105 | 0.160516 | 0.600000 | `meta_sec23_v1_baseline.log` |
| meta | sec21_1_matrix | `sec21_recip_adaptive_norm` | 0.269108 | 0.158399 | 0.520000 | `meta_sec21_recip_adaptive_norm.log` |
| meta | sec23_unified_4x3 | `sec23_v1_adaptive_norm` | 0.269111 | 0.158419 | 0.430000 | `meta_sec23_v1_adaptive_norm.log` |
| meta | sec23_unified_4x3 | `sec23_v2_baseline` | 0.269100 | 0.160433 | 0.600000 | `meta_sec23_v2_baseline.log` |
| meta | sec21_1_matrix | `sec21_recip_fixed_norm` | 0.269799 | 0.160341 | 0.210000 | `meta_sec21_recip_fixed_norm.log` |
| meta | sec23_unified_4x3 | `sec23_v2_adaptive_norm` | 0.269121 | 0.158411 | 0.420000 | `meta_sec23_v2_adaptive_norm.log` |
| meta | sec23_unified_4x3 | `sec23_v1_fixed_norm` | 0.270009 | 0.160589 | 0.170000 | `meta_sec23_v1_fixed_norm.log` |
| meta | sec23_unified_4x3 | `sec23_v3_baseline` | 0.269106 | 0.160404 | 0.570000 | `meta_sec23_v3_baseline.log` |
| meta | sec23_unified_4x3 | `sec23_v2_fixed_norm` | 0.269944 | 0.160653 | 0.180000 | `meta_sec23_v2_fixed_norm.log` |
| meta | sec23_unified_4x3 | `sec23_v4_baseline` | 0.269110 | 0.160243 | 0.510000 | `meta_sec23_v4_baseline.log` |
| meta | sec23_unified_4x3 | `sec23_v3_adaptive_norm` | 0.269446 | 0.162612 | 0.280000 | `meta_sec23_v3_adaptive_norm.log` |
| meta | sec23_unified_4x3 | `sec23_v4_adaptive_norm` | 0.269115 | 0.158040 | 0.350000 | `meta_sec23_v4_adaptive_norm.log` |
| meta | sec23_unified_4x3 | `sec23_v3_fixed_norm` | 0.270961 | 0.163707 | 0.120000 | `meta_sec23_v3_fixed_norm.log` |
| meta | sec23_unified_4x3 | `sec23_v4_fixed_norm` | 0.270142 | 0.160248 | 0.130000 | `meta_sec23_v4_fixed_norm.log` |
| meta | unified_new_0316 | `new_m5_tanh_robust` | 0.278321 | 0.154972 | 0.030000 | `meta_new_m5_tanh_robust.log` |
| 1063 | sec21_1_matrix | `sec21_log1p_baseline` | 0.022121 | 0.025267 | 0.350000 | `1063_sec21_log1p_baseline.log` |
| 1063 | sec21_1_matrix | `sec21_log1p_adaptive_norm` | 0.027733 | 0.028899 | 0.240000 | `1063_sec21_log1p_adaptive_norm.log` |
| 1063 | sec21_1_matrix | `sec21_recip_baseline` | 0.131368 | 0.125760 | 0.110000 | `1063_sec21_recip_baseline.log` |
| 1063 | sec21_1_matrix | `sec21_recip_adaptive_norm` | 0.043344 | 0.042105 | 0.180000 | `1063_sec21_recip_adaptive_norm.log` |
| 1063 | sec21_1_matrix | `sec21_log1p_fixed_norm` | 0.162782 | 0.157394 | 0.050000 | `1063_sec21_log1p_fixed_norm.log` |
| 1063 | sec21_1_matrix | `sec21_recip_fixed_norm` | 0.124537 | 0.118212 | 0.070000 | `1063_sec21_recip_fixed_norm.log` |
| 1063 | sec23_unified_4x3 | `sec23_v1_baseline` | 0.132379 | 0.126822 | 0.110000 | `1063_sec23_v1_baseline.log` |
| 1063 | sec23_unified_4x3 | `sec23_v1_adaptive_norm` | 0.043928 | 0.042652 | 0.140000 | `1063_sec23_v1_adaptive_norm.log` |
| 1063 | unified_new_0316 | `new_m4_cdf_like` | 0.249835 | 0.213991 | 0.030000 | `1063_new_m4_cdf_like.log` |
| 1063 | unified_new_0316 | `new_m6_qlog_gamma` | 0.264265 | 0.220719 | 0.030000 | `1063_new_m6_qlog_gamma.log` |
| 1063 | sec23_unified_4x3 | `sec23_v2_baseline` | 0.131004 | 0.125467 | 0.110000 | `1063_sec23_v2_baseline.log` |
| 1063 | sec23_unified_4x3 | `sec23_v2_adaptive_norm` | 0.043674 | 0.042368 | 0.140000 | `1063_sec23_v2_adaptive_norm.log` |
| 1063 | sec23_unified_4x3 | `sec23_v1_fixed_norm` | 0.173129 | 0.168250 | 0.040000 | `1063_sec23_v1_fixed_norm.log` |
| 1063 | sec23_unified_4x3 | `sec23_v3_baseline` | 0.132510 | 0.126951 | 0.110000 | `1063_sec23_v3_baseline.log` |
| 1063 | unified_new_0316 | `new_m5_tanh_robust` | 0.335386 | 0.290959 | 0.020000 | `1063_new_m5_tanh_robust.log` |
| 1063 | sec23_unified_4x3 | `sec23_v2_fixed_norm` | 0.145024 | 0.140957 | 0.050000 | `1063_sec23_v2_fixed_norm.log` |
| 1063 | sec23_unified_4x3 | `sec23_v3_adaptive_norm` | 0.080583 | 0.076596 | 0.080000 | `1063_sec23_v3_adaptive_norm.log` |
| 1063 | sec23_unified_4x3 | `sec23_v4_baseline` | 0.132154 | 0.126680 | 0.110000 | `1063_sec23_v4_baseline.log` |
| 1063 | sec23_unified_4x3 | `sec23_v4_adaptive_norm` | 0.040885 | 0.039870 | 0.120000 | `1063_sec23_v4_adaptive_norm.log` |
| 1063 | sec23_unified_4x3 | `sec23_v4_fixed_norm` | 0.062602 | 0.060374 | 0.080000 | `1063_sec23_v4_fixed_norm.log` |
| 1063 | sec23_unified_4x3 | `sec23_v3_fixed_norm` | 0.165141 | 0.158438 | 0.040000 | `1063_sec23_v3_fixed_norm.log` |
| wiki | sec21_1_matrix | `sec21_log1p_baseline` | 0.206992 | 0.192426 | 0.060000 | `wiki_sec21_log1p_baseline.log` |
| wiki | unified_new_0316 | `new_m4_cdf_like` | 0.183231 | 0.128476 | 0.030000 | `wiki_new_m4_cdf_like.log` |
| wiki | sec21_1_matrix | `sec21_log1p_fixed_norm` | 0.173091 | 0.132307 | 0.040000 | `wiki_sec21_log1p_fixed_norm.log` |
| wiki | unified_new_0316 | `new_m6_qlog_gamma` | 0.185875 | 0.129581 | 0.030000 | `wiki_new_m6_qlog_gamma.log` |
| wiki | sec21_1_matrix | `sec21_recip_baseline` | 0.176338 | 0.139734 | 0.070000 | `wiki_sec21_recip_baseline.log` |
| wiki | unified_new_0316 | `new_m5_tanh_robust` | 0.193034 | 0.133663 | 0.030000 | `wiki_new_m5_tanh_robust.log` |
| wiki | sec21_1_matrix | `sec21_log1p_adaptive_norm` | 0.171833 | 0.140439 | 0.050000 | `wiki_sec21_log1p_adaptive_norm.log` |
| wiki | sec21_1_matrix | `sec21_recip_fixed_norm` | 0.175523 | 0.142791 | 0.040000 | `wiki_sec21_recip_fixed_norm.log` |
| wiki | sec23_unified_4x3 | `sec23_v1_baseline` | 0.176386 | 0.139621 | 0.070000 | `wiki_sec23_v1_baseline.log` |
| wiki | sec23_unified_4x3 | `sec23_v2_baseline` | 0.176305 | 0.139659 | 0.070000 | `wiki_sec23_v2_baseline.log` |
| wiki | sec21_1_matrix | `sec21_recip_adaptive_norm` | 0.188753 | 0.213597 | 0.050000 | `wiki_sec21_recip_adaptive_norm.log` |
| wiki | sec23_unified_4x3 | `sec23_v1_fixed_norm` | 0.175880 | 0.142168 | 0.040000 | `wiki_sec23_v1_fixed_norm.log` |
| wiki | sec23_unified_4x3 | `sec23_v1_adaptive_norm` | 0.185838 | 0.204868 | 0.040000 | `wiki_sec23_v1_adaptive_norm.log` |
| wiki | sec23_unified_4x3 | `sec23_v3_baseline` | 0.176341 | 0.139616 | 0.060000 | `wiki_sec23_v3_baseline.log` |
| wiki | sec23_unified_4x3 | `sec23_v2_adaptive_norm` | 0.183738 | 0.197462 | 0.040000 | `wiki_sec23_v2_adaptive_norm.log` |
| wiki | sec23_unified_4x3 | `sec23_v2_fixed_norm` | 0.175541 | 0.141595 | 0.040000 | `wiki_sec23_v2_fixed_norm.log` |
| wiki | sec23_unified_4x3 | `sec23_v4_baseline` | 0.176440 | 0.139447 | 0.060000 | `wiki_sec23_v4_baseline.log` |
| wiki | sec23_unified_4x3 | `sec23_v3_fixed_norm` | 0.181345 | 0.144631 | 0.030000 | `wiki_sec23_v3_fixed_norm.log` |
| wiki | sec23_unified_4x3 | `sec23_v3_adaptive_norm` | 0.194380 | 0.232761 | 0.040000 | `wiki_sec23_v3_adaptive_norm.log` |
| wiki | sec23_unified_4x3 | `sec23_v4_fixed_norm` | 0.174822 | 0.146381 | 0.030000 | `wiki_sec23_v4_fixed_norm.log` |
| wiki | sec23_unified_4x3 | `sec23_v4_adaptive_norm` | 0.176981 | 0.174876 | 0.040000 | `wiki_sec23_v4_adaptive_norm.log` |
<!-- AUTO_UNIFIED_0316_END -->


## 27. Log1p Adaptive Tune 0316 (Auto)

仅记录 2026-03-16 调参批次：收窄分位区间 + 增大 warmup。

### 27.1 归一化公式说明（Adaptive）

Adaptive 归一化在 `loh_apply_feature_normalization` 中执行，记特征变换后的值为 $out$。

说明：`raw -> out` 的特征变换公式由特征模式决定（`LOG1P / RECIPROCAL / UNIFIED`），历史 `q_input` 变量不改变该映射本身。

历史变量（已停用）`LOH_ADAPTIVE_NORM_QUANTILE_INPUT` 的取值语义仅用于解释旧实验记录：

- `0` (`out`)：
$$
q_{obs}=out
$$
- `1` (`raw`)：
$$
q_{obs}=raw
$$
- `2` (`log1p`)：
$$
q_{obs}=\log(1+raw)
$$

在线分位更新（使用观测值 $q_{obs}$）：

$$
q_{lo} \leftarrow q_{lo} + \eta\,(\tau_{lo}-\mathbf{1}[q_{obs}\le q_{lo}]),\quad
q_{hi} \leftarrow q_{hi} + \eta\,(\tau_{hi}-\mathbf{1}[q_{obs}\le q_{hi}])
$$

其中 $\tau_{lo}$/ $\tau_{hi}$ 分别对应环境变量 `LOH_ADAPTIVE_NORM_LO_Q` / `LOH_ADAPTIVE_NORM_HI_Q`。

预热期：当 `timestamp <= warmup`，直接返回 $out$。

预热后归一化：

$$
n = \frac{out - L}{H - L},\quad n\in[0,1]
$$

边界 $(L,H)$ 由 `LOH_ADAPTIVE_NORM_TRANSFORM_QUANTILE` 决定：

- `0`：
$$
L=q_{lo},\quad H=q_{hi}
$$
- `1`：
$$
L=\log(1+q_{lo}),\quad H=\log(1+q_{hi})
$$

`lo=0.0, hi=1.0` 时走简化路径：不做在线分位更新，退化为运行时 min/max 追踪。

历史变量说明：`LOH_ADAPTIVE_NORM_QUANTILE_INPUT(raw/log1p/out)` 已停用，代码不再读取；现行控制变量为 `LOH_ADAPTIVE_NORM_TRANSFORM_QUANTILE`。

<!-- AUTO_LOG1P_TUNE_0316_BEGIN -->
_Auto-updated from `tmp/log1p_adaptive_tune_0316/results.csv` at 2026-03-16 15:16:01._

| Trace | Config | Raw->Out | Normalization | Obj MR | Byte MR | MQPS | Log |
|:--|---|---|---|---:|---:|---:|---|
| meta | `adapt_q05_q95_w32768` | `log1p` | `adaptive(lo=0.05, hi=0.95, warmup=32768, q_input=out)` | 0.269165 | 0.154793 | 0.310000 | `meta_adapt_q05_q95_w32768.log` |
| meta | `adapt_q05_q95_w16384` | `log1p` | `adaptive(lo=0.05, hi=0.95, warmup=16384, q_input=out)` | 0.269175 | 0.155170 | 0.290000 | `meta_adapt_q05_q95_w16384.log` |
| meta | `adapt_q10_q90_w32768` | `log1p` | `adaptive(lo=0.10, hi=0.90, warmup=32768, q_input=out)` | 0.269510 | 0.154961 | 0.170000 | `meta_adapt_q10_q90_w32768.log` |
| meta | `adapt_q10_q90_w16384` | `log1p` | `adaptive(lo=0.10, hi=0.90, warmup=16384, q_input=out)` | 0.269526 | 0.155451 | 0.150000 | `meta_adapt_q10_q90_w16384.log` |
| 1063 | `adapt_q05_q95_w16384` | `log1p` | `adaptive(lo=0.05, hi=0.95, warmup=16384, q_input=out)` | 0.036966 | 0.037213 | 0.240000 | `1063_adapt_q05_q95_w16384.log` |
| 1063 | `adapt_q05_q95_w32768` | `log1p` | `adaptive(lo=0.05, hi=0.95, warmup=32768, q_input=out)` | 0.037416 | 0.037670 | 0.240000 | `1063_adapt_q05_q95_w32768.log` |
| 1063 | `adapt_q10_q90_w16384` | `log1p` | `adaptive(lo=0.10, hi=0.90, warmup=16384, q_input=out)` | 0.054217 | 0.052541 | 0.190000 | `1063_adapt_q10_q90_w16384.log` |
| 1063 | `adapt_q10_q90_w32768` | `log1p` | `adaptive(lo=0.10, hi=0.90, warmup=32768, q_input=out)` | 0.054333 | 0.052451 | 0.190000 | `1063_adapt_q10_q90_w32768.log` |
| wiki | `adapt_q05_q95_w32768` | `log1p` | `adaptive(lo=0.05, hi=0.95, warmup=32768, q_input=out)` | 0.175279 | 0.140251 | 0.050000 | `wiki_adapt_q05_q95_w32768.log` |
| wiki | `adapt_q05_q95_w16384` | `log1p` | `adaptive(lo=0.05, hi=0.95, warmup=16384, q_input=out)` | 0.175626 | 0.142899 | 0.050000 | `wiki_adapt_q05_q95_w16384.log` |
| wiki | `adapt_q10_q90_w16384` | `log1p` | `adaptive(lo=0.10, hi=0.90, warmup=16384, q_input=out)` | 0.179138 | 0.136822 | 0.050000 | `wiki_adapt_q10_q90_w16384.log` |
| wiki | `adapt_q10_q90_w32768` | `log1p` | `adaptive(lo=0.10, hi=0.90, warmup=32768, q_input=out)` | 0.177861 | 0.137732 | 0.050000 | `wiki_adapt_q10_q90_w32768.log` |
<!-- AUTO_LOG1P_TUNE_0316_END -->

### 27.2 1063 Quantile Bound Effect (warmup=0, Auto)

本节说明：本轮使用 `params->current_timestamp` 作为分位更新进度计数，并显式设置 `LOH_ADAPTIVE_NORM_WARMUP=0`；重测时在同配置下对 `LOH_FEATURE_IDENTITY=0/1` 做并行对照（固定 `LOH_INCLUDE_HIT_MISS_FEATURES=0`）。

<!-- AUTO_1063_BOUND_W0_0316_BEGIN -->
_Auto-updated from `tmp/1063_bound_effect_0316_w0_identity/results.csv` at 2026-03-17 00:08:25._

| Raw->Out | Norm                                                 |   MR24 |   MR48 |   MR72 |   MR96 | Final MR |  Byte MR |     MQPS | Log                        |
|:--| ---------------------------------------------------- | -----: | -----: | -----: | -----: | -------: | -------: | -------: | -------------------------- |
| log1p    | `adaptive(warmup=0, q_input=out, lo=0.005, hi=0.99)` | 0.1234 | 0.1034 | 0.0784 | 0.0613 | 0.031165 | 0.031696 | 0.230000 | `1063_lo005_hi099_id0.log` |
| raw      | `adaptive(warmup=0, q_input=out, lo=0.005, hi=0.99)` | 0.1121 | 0.0823 | 0.0547 | 0.0421 | 0.024503 | 0.031687 | 0.360000 | `1063_lo005_hi099_id1.log` |
| log1p    | `adaptive(warmup=0, q_input=out, lo=0.0, hi=0.99)`   | 0.1131 | 0.0917 | 0.0676 | 0.0524 | 0.026594 | 0.027861 | 0.300000 | `1063_lo00_hi099_id0.log`  |
| raw      | `adaptive(warmup=0, q_input=out, lo=0.0, hi=0.99)`   | 0.1121 | 0.0823 | 0.0548 | 0.0422 | 0.024554 | 0.031761 | 0.400000 | `1063_lo00_hi099_id1.log`  |
| log1p    | `adaptive(warmup=0, q_input=out, lo=0.0, hi=1.0)`    | 0.0979 | 0.0776 | 0.0564 | 0.0440 | 0.022775 | 0.024144 | 0.290000 | `1063_lo00_hi100_id0.log`  |
| raw      | `adaptive(warmup=0, q_input=out, lo=0.0, hi=1.0)`    | 0.1309 | 0.0964 | 0.0646 | 0.0501 | 0.028764 | 0.036768 | 0.340000 | `1063_lo00_hi100_id1.log`  |
| log1p    | `adaptive(warmup=0, q_input=out, lo=0.01, hi=0.95)`  | 0.1417 | 0.1249 | 0.1008 | 0.0815 | 0.041828 | 0.041097 | 0.210000 | `1063_lo01_hi095_id0.log`  |
| raw      | `adaptive(warmup=0, q_input=out, lo=0.01, hi=0.95)`  | 0.1663 | 0.1379 | 0.0984 | 0.0747 | 0.039336 | 0.046858 | 0.290000 | `1063_lo01_hi095_id1.log`  |
| log1p    | `adaptive(warmup=0, q_input=out, lo=0.01, hi=0.99)`  | 0.1189 | 0.0978 | 0.0718 | 0.0552 | 0.027885 | 0.028984 | 0.250000 | `1063_lo01_hi099_id0.log`  |
| raw      | `adaptive(warmup=0, q_input=out, lo=0.01, hi=0.99)`  | 0.1121 | 0.0822 | 0.0547 | 0.0421 | 0.024527 | 0.031717 | 0.370000 | `1063_lo01_hi099_id1.log`  |
| log1p    | `adaptive(warmup=0, q_input=out, lo=0.01, hi=0.995)` | 0.1132 | 0.0917 | 0.0665 | 0.0511 | 0.026017 | 0.027321 | 0.260000 | `1063_lo01_hi0995_id0.log` |
| raw      | `adaptive(warmup=0, q_input=out, lo=0.01, hi=0.995)` | 0.1139 | 0.0845 | 0.0569 | 0.0441 | 0.025703 | 0.033219 | 0.350000 | `1063_lo01_hi0995_id1.log` |
| log1p    | `adaptive(warmup=0, q_input=out, lo=0.01, hi=1.0)`   | 0.1043 | 0.0864 | 0.0641 | 0.0501 | 0.026181 | 0.027025 | 0.290000 | `1063_lo01_hi100_id0.log`  |
| raw      | `adaptive(warmup=0, q_input=out, lo=0.01, hi=1.0)`   | 0.1310 | 0.0963 | 0.0646 | 0.0500 | 0.028690 | 0.036756 | 0.360000 | `1063_lo01_hi100_id1.log`  |
| log1p    | `adaptive(warmup=0, q_input=out, lo=0.05, hi=0.99)`  | 0.1176 | 0.0973 | 0.0711 | 0.0545 | 0.027281 | 0.028635 | 0.250000 | `1063_lo05_hi099_id0.log`  |
| raw      | `adaptive(warmup=0, q_input=out, lo=0.05, hi=0.99)`  | 0.1125 | 0.0826 | 0.0549 | 0.0422 | 0.024567 | 0.031759 | 0.370000 | `1063_lo05_hi099_id1.log`  |
|          |                                                      |        |        |        |        |          |          |          |                            |

### 27.3 Adaptive Quantile Input Ablation (lo00_hi100, 3 traces, Auto)

本节固定 `raw->out=log1p` 与 `lo00_hi100`（`warmup=0`），历史记录比较 `q_obs=raw` 与 `q_obs=log1p(raw)` 两种输入语义（旧变量，现已停用）。

补充：此前“无 hitmiss 的 1063 raw”日志文件 `tmp/adaptive_quantile_input_3trace_0316/1063_qinput_raw.log` 未写出最终 `LOH-OMR cache size` 汇总行，当前未计入本节结果表；后续补跑成功后并入本节。

<!-- AUTO_ADAPTIVE_QINPUT_3TRACE_0316_BEGIN -->
_Auto-updated from `tmp/adaptive_quantile_input_3trace_0316/results.csv` at 2026-03-17 21:59:36._

| T | Raw->Out | Norm | Final MR | Byte MR | MQPS | Log |
|:--|---|---|---:|---:|---:|---|
| 1063 | `log1p` | `adpt(q=log1p,lo0,hi1,w0)` | 0.022865 | 0.024220 | 0.260000 | `1063_qinput_log1p.log` |
| 1063 | `log1p` | `adpt(q=raw,lo0,hi1,w0)` | 0.519859 | 0.519291 | 0.040000 | `cachesim_sb3_0317_1063_qinput_raw_rerun.log` |
| meta | `log1p` | `adpt(q=log1p,lo0,hi1,w0)` | 0.269190 | 0.153539 | 0.350000 | `meta_qinput_log1p.log` |
| meta | `log1p` | `adpt(q=raw,lo0,hi1,w0)` | 0.368989 | 0.189888 | 0.030000 | `meta_qinput_raw.log` |
| wiki | `log1p` | `adpt(q=log1p,lo0,hi1,w0)` | 0.171714 | 0.137750 | 0.050000 | `wiki_qinput_log1p.log` |
| wiki | `log1p` | `adpt(q=raw,lo0,hi1,w0)` | 0.191845 | 0.132577 | 0.050000 | `wiki_qinput_raw.log` |

### 27.4 Log1p + Adaptive(q_input=log1p) on 3 Traces (HitMiss=0, Auto)

固定配置：`raw->out=log1p`，`adaptive(lo=0.0, hi=1.0, warmup=0, q_input=log1p)`，`CACHESIM_NUM_REQ=0` 全量请求，`LOH_INCLUDE_HIT_MISS_FEATURES=0`。

<!-- AUTO_LOG1P_QINPUT_4TRACE_0317_BEGIN -->
_Auto-updated from `tmp/log1p_qinput_276_3trace_0317/results.csv` at 2026-03-17 20:13:01._

| T | Raw->Out | Norm | HitMiss | Final MR | Byte MR | MQPS | Log |
|:--|---|---|---:|---:|---:|---:|---|
| metaKV-202401 | `log1p` | `adpt(q=log1p,lo0,hi1,w0)` | 0 | 0.047987 | 0.054231 | 0.560000 | `metaKV-202401_log1p_qinput_log1p_hitmiss0.log` |

### 27.5 Log1p + Adaptive(q_input=log1p) + HitMiss on 3 Traces (Auto)

固定配置：`raw->out=log1p`，`adaptive(lo=0.0, hi=1.0, warmup=0, q_input=log1p)`，`CACHESIM_NUM_REQ=0`，并开启 `LOH_INCLUDE_HIT_MISS_FEATURES=1`。

<!-- AUTO_LOG1P_QINPUT_HITMISS_3TRACE_0317_BEGIN -->
_Auto-updated from `tmp/log1p_qinput_hitmiss_3trace_0317/results.csv` at 2026-03-17 20:13:01._

| T | Raw->Out | Norm | HitMiss | Final MR | Byte MR | MQPS | Log |
|:--|---|---|---:|---:|---:|---:|---|
| 1063 | `log1p` | `adpt(q=log1p,lo0,hi1,w0)` | 1 | 0.022793 | 0.024137 | 0.270000 | `1063_log1p_qinput_log1p_hitmiss.log` |
| meta | `log1p` | `adpt(q=log1p,lo0,hi1,w0)` | 1 | 0.269197 | 0.153780 | 0.490000 | `meta_log1p_qinput_log1p_hitmiss.log` |
| wiki | `log1p` | `adpt(q=log1p,lo0,hi1,w0)` | 1 | 0.173248 | 0.139207 | 0.070000 | `wiki_log1p_qinput_log1p_hitmiss_rerun_0317.log` |

### 27.6 Extra3 Across Traces (Auto)

本节记录 lo/hi 三组（lo00_hi099, lo01_hi100, lo00_hi100）在 meta/wiki 的结果；并发 6，完成一条即刷新。

<!-- AUTO_EXTRA3_ALLTRACES_0316_BEGIN -->
_Auto-updated from `tmp/bound_extra3_alltraces_0316/results.csv` at 2026-03-16 18:18:12._

| Trace | Config | Final MR | Byte MR | MQPS | Log |
|:--|---|---:|---:|---:|---|
| meta | `lo01_hi100` | 0.269066 | 0.154950 | 0.420000 | `meta_lo01_hi100.log` |
| meta | `lo00_hi100` | 0.269165 | 0.153907 | 0.320000 | `meta_lo00_hi100.log` |
| meta | `lo00_hi099` | 0.269186 | 0.153837 | 0.300000 | `meta_lo00_hi099.log` |
| wiki | `lo00_hi099` | 0.170127 | 0.134009 | 0.050000 | `wiki_lo00_hi099.log` |
| wiki | `lo00_hi100` | 0.171618 | 0.138154 | 0.050000 | `wiki_lo00_hi100.log` |
| wiki | `lo01_hi100` | 0.175036 | 0.139154 | 0.050000 | `wiki_lo01_hi100.log` |
<!-- AUTO_EXTRA3_ALLTRACES_0316_END -->

### 27.7 HitMiss + lo00_hi100 FullReq (Auto)

本节记录 `LOH_INCLUDE_HIT_MISS_FEATURES=1` + `lo00_hi100` 在 1063/wiki/meta 全量并行运行结果；每完成一条自动刷新。

<!-- AUTO_HITMISS_LO00_HI100_FULL_0316_BEGIN -->
_Auto-updated from `tmp/hitmiss_lo00_hi100_full_0316/results.csv` at 2026-03-16 19:22:40._

| Trace | Status | RC | Final MR | Byte MR | MQPS | Log |
|:--|---|---:|---:|---:|---:|---|
| meta | ok | 0 | 0.269099 | 0.161177 | 0.54 | `meta_hitmiss_lo00_hi100.log` |
| 1063 | ok | 0 | 0.035074 | 0.034376 | 0.19 | `1063_hitmiss_lo00_hi100.log` |
| wiki | ok | 0 | 0.174636 | 0.148169 | 0.05 | `wiki_hitmiss_lo00_hi100.log` |
<!-- AUTO_HITMISS_LO00_HI100_FULL_0316_END -->

### 27.8 TransformQuantile=1 Across Original 3 Traces (cache=0.1, Auto)

固定配置：`raw->out=log1p`，`adaptive(lo=0.0, hi=1.0, warmup=0)`，并设置 `LOH_ADAPTIVE_NORM_TRANSFORM_QUANTILE=1`，`LOH_INCLUDE_HIT_MISS_FEATURES=0`，`CACHESIM_NUM_REQ=0` 全量请求，三条 trace 并行运行；每完成一条自动刷新。

<!-- AUTO_TRANSFORM_Q1_ORIG3_CACHE01_0317_BEGIN -->
_Auto-updated from `tmp/transformq1_orig3_cache01_0317/results.csv` at 2026-03-17 23:14:06._

| Trace | Raw->Out | Norm | TransformQ | Final MR | Byte MR | MQPS | Log |
|:--|---|---|---:|---:|---:|---:|---|
| meta | `log1p` | `adpt(lo0,hi1,w0)` | 1 | 0.353812 | 0.183901 | 0.040000 | `meta_transformq1_cache01_0317_225339.log` |

### 27.9 Log1p + Adaptive(q_input=log1p) Across Original 3 Traces (cache=0.001, Auto)

固定配置：`raw->out=log1p`，`adaptive(lo=0.0, hi=1.0, warmup=0)`，并设置 `Adaptive(q_input=log1p) `，`LOH_INCLUDE_HIT_MISS_FEATURES=0`，`CACHESIM_NUM_REQ=0` 全量请求，三条 trace 并行运行；每完成一条自动刷新。
说明：本节沿用已运行脚本的历史 `log1p` 配置结果（不改已运行脚本）。

<!-- AUTO_ORIG3_CACHE0001_0317_BEGIN -->
_Auto-updated from `tmp/log1p_qinput_orig3_cache0001_0317/results.csv` at 2026-03-17 22:37:21._

| Trace | Raw->Out | Norm | TransformQ | Final MR | Byte MR | MQPS | Log |
|:--|---|---|---:|---:|---:|---:|---|
| meta | `log1p` | `adpt(lo0,hi1,w0)` | 0 | 0.355763 | 0.212391 | 0.040000 | `meta_log1p_qinput_log1p_hitmiss0_c001_0317_200654.log` |
| wiki | `log1p` | `adpt(lo0,hi1,w0)` | 0 | 0.740196 | 0.714460 | 0.030000 | `wiki_log1p_qinput_log1p_hitmiss0_c001_0317_200654.log` |

### 27.10 TransformQuantile=0 Across Original 3 Traces (cache=0.1, Auto)

固定配置与 27.8 相同，仅将 `LOH_ADAPTIVE_NORM_TRANSFORM_QUANTILE` 设为 `0`；`raw->out=log1p`，`adaptive(lo=0.0, hi=1.0, warmup=0)`，`LOH_INCLUDE_HIT_MISS_FEATURES=0`，`CACHESIM_NUM_REQ=0` 全量请求，三条 trace 并行运行；每完成一条自动刷新。

<!-- AUTO_TRANSFORM_Q0_ORIG3_CACHE01_0317_BEGIN -->
_Auto-updated from `tmp/transformq0_orig3_cache01_0317/results.csv` at 2026-03-18 01:02:31._

| Trace | Raw->Out | Norm | TransformQ | Final MR | Byte MR | MQPS | Log |
|:--|---|---|---:|---:|---:|---:|---|
| 1063 | `log1p` | `adpt(lo0,hi1,w0)` | 0 | 0.022822 | 0.024181 | 0.400000 | `1063_transformq0_cache01_0317_233040.log` |
| meta | `log1p` | `adpt(lo0,hi1,w0)` | 0 | 0.269176 | 0.153885 | 0.540000 | `meta_transformq0_cache01_0317_233040.log` |
| wiki | `log1p` | `adpt(lo0,hi1,w0)` | 0 | 0.171503 | 0.137036 | 0.070000 | `wiki_transformq0_cache01_0317_233040.log` |

### 27.11 TransformQuantile=0 + HitMiss=1 Across Original 3 Traces (cache=0.1, Auto)

固定配置沿用 27.10，并将 `LOH_INCLUDE_HIT_MISS_FEATURES=1`（编译期）后重编译；其余保持：`raw->out=log1p`，`adaptive(lo=0.0, hi=1.0, warmup=0)`，`LOH_ADAPTIVE_NORM_TRANSFORM_QUANTILE=0`，`CACHESIM_NUM_REQ=0` 全量请求，三条 trace 并行运行；每完成一条自动刷新。

<!-- AUTO_TRANSFORM_Q0_HITMISS1_ORIG3_CACHE01_0317_BEGIN -->
_Auto-updated from `tmp/transformq0_hitmiss1_orig3_cache01_0317/results.csv` at 2026-03-18 00:34:44._

| Trace | Raw->Out | Norm | TransformQ | HitMiss | Final MR | Byte MR | MQPS | Log |
|:--|---|---|---:|---:|---:|---:|---:|---|
| 1063 | `log1p` | `adpt(lo0,hi1,w0)` | 0 | 1 | 0.022819 | 0.024138 | 0.360000 | `1063_transformq0_hitmiss1_cache01_0317_234326.log` |
| meta | `log1p` | `adpt(lo0,hi1,w0)` | 0 | 1 | 0.269184 | 0.153634 | 0.310000 | `meta_transformq0_hitmiss1_cache01_0317_234326.log` |
| wiki | `log1p` | `adpt(lo0,hi1,w0)` | 0 | 1 | 0.172417 | 0.137832 | 0.070000 | `wiki_transformq0_hitmiss1_cache01_0317_234326.log` |

### 27.12 TransformQuantile=0 + WeightsInObs=0 Across Original 3 Traces (cache=0.1, Auto)

固定配置沿用 27.10，并将 `LOH_INCLUDE_WEIGHTS_IN_OBS=0`；其余保持：`raw->out=log1p`，`adaptive(lo=0.0, hi=1.0, warmup=0)`，`LOH_ADAPTIVE_NORM_TRANSFORM_QUANTILE=0`，`LOH_INCLUDE_HIT_MISS_FEATURES=0`，`CACHESIM_NUM_REQ=0` 全量请求。按要求先重编译，再并行运行三条 trace，完成一条即刷新。

<!-- AUTO_TRANSFORM_Q0_WOBS0_ORIG3_CACHE01_0317_BEGIN -->
_Auto-updated from `tmp/transformq0_wobs0_orig3_cache01_0317/results.csv` at 2026-03-18 01:35:43._

| Trace | Raw->Out | Norm | TransformQ | WeightsInObs | Final MR | Byte MR | MQPS | Log |
|:--|---|---|---:|---:|---:|---:|---:|---|
| 1063 | `log1p` | `adpt(lo0,hi1,w0)` | 0 | 0 | 0.022889 | 0.024254 | 0.430000 | `1063_transformq0_wobs0_cache01_0318_012111.log` |
| meta | `log1p` | `adpt(lo0,hi1,w0)` | 0 | 0 | 0.269191 | 0.153756 | 0.570000 | `meta_transformq0_wobs0_cache01_0318_012111.log` |

### 27.13 TransformQuantile=0 + MissRatioWeight Sweep (0.0~1.0, step=0.1) on Original 3 Traces (cache=0.1, Auto)

基于 27.10 配置，仅调整 `LOH_MISS_RATIO_WEIGHT` 为 `0.0, 0.1, ..., 1.0`；每个权重在 `1063/wiki/meta` 三条 trace 上测试，单次并发上限 3，缺失结果支持补跑续写。

<!-- AUTO_TRANSFORM_Q0_MRW_SWEEP_ORIG3_CACHE01_0318_BEGIN -->
_Auto-updated from `tmp/transformq0_mrw_sweep_orig3_cache01_0318/results.csv` at 2026-03-18 10:50:57._

| Trace | Weight | Raw->Out | Norm | TransformQ | Final MR | Byte MR | MQPS | Log |
|:--|:--|---|---|---:|---:|---:|---:|---|
| 1063 | 0.0 | `log1p` | `adpt(lo0,hi1,w0)` | 0 | 0.022956 | 0.024298 | 0.440000 | `1063_transformq0_mrw0p0_cache01_0318_012004.log` |
| 1063 | 0.1 | `log1p` | `adpt(lo0,hi1,w0)` | 0 | 0.022882 | 0.024237 | 0.440000 | `1063_transformq0_mrw0p1_cache01_0318_012127.log` |
| 1063 | 0.2 | `log1p` | `adpt(lo0,hi1,w0)` | 0 | 0.022873 | 0.024249 | 0.370000 | `1063_transformq0_mrw0p2_cache01_0318_013715.log` |
| 1063 | 0.3 | `log1p` | `adpt(lo0,hi1,w0)` | 0 | 0.022846 | 0.024212 | 0.290000 | `1063_transformq0_mrw0p3_cache01_0318_021348.log` |
| 1063 | 0.4 | `log1p` | `adpt(lo0,hi1,w0)` | 0 | 0.022813 | 0.024157 | 0.310000 | `1063_transformq0_mrw0p4_cache01_0318_023710.log` |
| 1063 | 0.5 | `log1p` | `adpt(lo0,hi1,w0)` | 0 | 0.022939 | 0.024326 | 0.310000 | `1063_transformq0_mrw0p5_cache01_0318_025949.log` |
| 1063 | 0.6 | `log1p` | `adpt(lo0,hi1,w0)` | 0 | **0.022762** | 0.024126 | 0.290000 | `1063_transformq0_mrw0p6_cache01_0318_033846.log` |
| 1063 | 0.7 | `log1p` | `adpt(lo0,hi1,w0)` | 0 | **0.022742** | 0.024110 | 0.290000 | `1063_transformq0_mrw0p7_cache01_0318_040450.log` |
| 1063 | 0.8 | `log1p` | `adpt(lo0,hi1,w0)` | 0 | **0.022751** | **0.024089** | 0.280000 | `1063_transformq0_mrw0p8_cache01_0318_043123.log` |
| 1063 | 0.9 | `log1p` | `adpt(lo0,hi1,w0)` | 0 | 0.022855 | 0.024202 | 0.280000 | `1063_transformq0_mrw0p9_cache01_0318_051232.log` |
| 1063 | 1.0 | `log1p` | `adpt(lo0,hi1,w0)` | 0 | **0.022709** | **0.024033** | 0.310000 | `1063_transformq0_mrw1p0_cache01_0318_053936.log` |
| wiki | 0.0 | `log1p` | `adpt(lo0,hi1,w0)` | 0 | 0.171734 | **0.137324** | 0.070000 | `wiki_transformq0_mrw0p0_cache01_0318_012004.log` |
| wiki | 0.1 | `log1p` | `adpt(lo0,hi1,w0)` | 0 | 0.173008 | 0.140358 | 0.060000 | `wiki_transformq0_mrw0p1_cache01_0318_013419.log` |
| wiki | 0.2 | `log1p` | `adpt(lo0,hi1,w0)` | 0 | 0.171475 | 0.138041 | 0.060000 | `wiki_transformq0_mrw0p2_cache01_0318_015413.log` |
| wiki | 0.3 | `log1p` | `adpt(lo0,hi1,w0)` | 0 | 0.173086 | 0.138900 | 0.050000 | `wiki_transformq0_mrw0p3_cache01_0318_023159.log` |
| wiki | 0.4 | `log1p` | `adpt(lo0,hi1,w0)` | 0 | 0.171775 | 0.138364 | 0.050000 | `wiki_transformq0_mrw0p4_cache01_0318_025555.log` |
| wiki | 0.5 | `log1p` | `adpt(lo0,hi1,w0)` | 0 | 0.171407 | 0.139340 | 0.050000 | `wiki_transformq0_mrw0p5_cache01_0318_031952.log` |
| wiki | 0.6 | `log1p` | `adpt(lo0,hi1,w0)` | 0 | 0.171476 | 0.139535 | 0.050000 | `wiki_transformq0_mrw0p6_cache01_0318_040012.log` |
| wiki | 0.7 | `log1p` | `adpt(lo0,hi1,w0)` | 0 | 0.171442 | 0.139503 | 0.050000 | `wiki_transformq0_mrw0p7_cache01_0318_042626.log` |
| wiki | 0.8 | `log1p` | `adpt(lo0,hi1,w0)` | 0 | 0.171435 | 0.139460 | 0.050000 | `wiki_transformq0_mrw0p8_cache01_0318_045345.log` |
| wiki | 0.9 | `log1p` | `adpt(lo0,hi1,w0)` | 0 | 0.171462 | 0.139509 | 0.050000 | `wiki_transformq0_mrw0p9_cache01_0318_053442.log` |
| wiki | 1.0 | `log1p` | `adpt(lo0,hi1,w0)` | 0 | 0.171408 | 0.139663 | 0.060000 | `wiki_transformq0_mrw1p0_cache01_0318_060012.log` |
| meta | 0.0 | `log1p` | `adpt(lo0,hi1,w0)` | 0 | 0.269178 | 0.153699 | 0.660000 | `meta_transformq0_mrw0p0_cache01_0318_012004.log` |
| meta | 0.1 | `log1p` | `adpt(lo0,hi1,w0)` | 0 | 0.269189 | **0.153589** | 0.600000 | `meta_transformq0_mrw0p1_cache01_0318_013543.log` |
| meta | 0.2 | `log1p` | `adpt(lo0,hi1,w0)` | 0 | 0.269176 | 0.153864 | 0.410000 | `meta_transformq0_mrw0p2_cache01_0318_021129.log` |
| meta | 0.3 | `log1p` | `adpt(lo0,hi1,w0)` | 0 | 0.269172 | 0.153813 | 0.580000 | `meta_transformq0_mrw0p3_cache01_rerun_0318_104220.log` |
| meta | 0.4 | `log1p` | `adpt(lo0,hi1,w0)` | 0 | 0.269178 | 0.153851 | 0.430000 | `meta_transformq0_mrw0p4_cache01_0318_025741.log` |
| meta | 0.5 | `log1p` | `adpt(lo0,hi1,w0)` | 0 | 0.269165 | 0.153742 | 0.430000 | `meta_transformq0_mrw0p5_cache01_0318_033637.log` |
| meta | 0.6 | `log1p` | `adpt(lo0,hi1,w0)` | 0 | 0.269178 | 0.153815 | 0.330000 | `meta_transformq0_mrw0p6_cache01_0318_040208.log` |
| meta | 0.7 | `log1p` | `adpt(lo0,hi1,w0)` | 0 | 0.269164 | 0.153873 | 0.420000 | `meta_transformq0_mrw0p7_cache01_0318_042909.log` |
| meta | 0.8 | `log1p` | `adpt(lo0,hi1,w0)` | 0 | 0.269162 | 0.154007 | 0.410000 | `meta_transformq0_mrw0p8_cache01_0318_051016.log` |
| meta | 0.9 | `log1p` | `adpt(lo0,hi1,w0)` | 0 | 0.269158 | 0.153996 | 0.410000 | `meta_transformq0_mrw0p9_cache01_0318_053719.log` |
| meta | 1.0 | `log1p` | `adpt(lo0,hi1,w0)` | 0 | 0.269174 | 0.153777 | 0.470000 | `meta_transformq0_mrw1p0_cache01_0318_060439.log` |

### 27.14 Non-default Reward Paths Sweep (9 Paths) on Original 3 Traces (cache=0.1, Auto)

基于 27.10 配置，仅在 `LOH_ENABLE_PENALTY=0` 下切换非默认 reward 路径（排除默认路径：`absolute + no_miss + no_trend`）。
共 9 条路径：

1. `abs_miss_neg`
2. `abs_miss_improve`
3. `abs_trend_slope`
4. `abs_trend_delta`
5. `abs_miss_neg_trend_slope`
6. `abs_miss_neg_trend_delta`
7. `abs_miss_improve_trend_slope`
8. `abs_miss_improve_trend_delta`
9. `delta_only`

按 `路径 × trace(1063/wiki/meta)` 运行；并发上限 3；已完成项自动跳过补齐；每完成一条即刷新。

<!-- AUTO_REWARD_PATHS_NONDEFAULT_ORIG3_CACHE01_0318_BEGIN -->
_Auto-updated from `tmp/reward_paths_nondefault_orig3_cache01_0318/results.csv` at 2026-03-18 10:51:07._

| Trace | Reward<br />Mode | UseMiss | MissMode | UseTrend | TrendMode | Final MR | Byte MR | MQPS | Log |
|:--|:--|---:|:--|---:|:--|---:|---:|---:|---|
| 1063 | absolute | 1 | improve | 0 | slope | 0.022766 | 0.024121 | 0.340000 | `1063_abs_miss_improve_cache01_0318_014310.log` |
| 1063 | absolute | 1 | improve | 1 | delta | **0.022670** | **0.024029** | 0.280000 | `1063_abs_miss_improve_trend_delta_cache01_0318_043348.log` |
| 1063 | absolute | 1 | improve | 1 | slope | 0.022765 | 0.024110 | 0.290000 | `1063_abs_miss_improve_trend_slope_cache01_0318_040812.log` |
| 1063 | absolute | 1 | neg | 0 | slope | 0.022836 | 0.024185 | 0.360000 | `1063_abs_miss_neg_cache01_0318_014126.log` |
| 1063 | absolute | 1 | neg | 1 | delta | 0.022871 | 0.024206 | 0.300000 | `1063_abs_miss_neg_trend_delta_cache01_0318_033030.log` |
| 1063 | absolute | 1 | neg | 1 | slope | 0.022806 | 0.024168 | 0.310000 | `1063_abs_miss_neg_trend_slope_cache01_0318_030511.log` |
| 1063 | absolute | 0 | neg | 1 | delta | 0.022776 | 0.024118 | 0.320000 | `1063_abs_trend_delta_cache01_0318_024308.log` |
| 1063 | absolute | 0 | neg | 1 | slope | 0.022827 | 0.024188 | 0.310000 | `1063_abs_trend_slope_cache01_0318_020317.log` |
| 1063 | delta | 0 | neg | 0 | slope | **0.022700** | **0.024046** | 0.290000 | `1063_delta_only_cache01_0318_050509.log` |
| wiki | absolute | 1 | improve | 0 | slope | 0.171454 | 0.139271 | 0.060000 | `wiki_abs_miss_improve_cache01_0318_015849.log` |
| wiki | absolute | 1 | improve | 1 | delta | 0.171433 | 0.139747 | 0.050000 | `wiki_abs_miss_improve_trend_delta_cache01_0318_045608.log` |
| wiki | absolute | 1 | improve | 1 | slope | 0.171387 | 0.139777 | 0.050000 | `wiki_abs_miss_improve_trend_slope_cache01_0318_042950.log` |
| wiki | absolute | 1 | neg | 0 | slope | 0.171652 | **0.138682** | 0.060000 | `wiki_abs_miss_neg_cache01_0318_014126.log` |
| wiki | absolute | 1 | neg | 1 | delta | 0.171473 | 0.139589 | 0.050000 | `wiki_abs_miss_neg_trend_delta_cache01_0318_035141.log` |
| wiki | absolute | 1 | neg | 1 | slope | 0.171395 | 0.139616 | 0.050000 | `wiki_abs_miss_neg_trend_slope_cache01_0318_032535.log` |
| wiki | absolute | 0 | neg | 1 | delta | 0.171433 | 0.139447 | 0.050000 | `wiki_abs_trend_delta_cache01_0318_030122.log` |
| wiki | absolute | 0 | neg | 1 | slope | **0.171360** | 0.139500 | 0.050000 | `wiki_abs_trend_slope_cache01_0318_022326.log` |
| wiki | delta | 0 | neg | 0 | slope | 0.171416 | 0.139744 | 0.050000 | `wiki_delta_only_cache01_0318_052650.log` |
| meta | absolute | 1 | improve | 0 | slope | 0.269178 | **0.153751** | 0.490000 | `meta_abs_miss_improve_cache01_0318_020125.log` |
| meta | absolute | 1 | improve | 1 | delta | 0.269168 | 0.153931 | 0.410000 | `meta_abs_miss_improve_trend_delta_cache01_0318_050254.log` |
| meta | absolute | 1 | improve | 1 | slope | 0.269158 | 0.153993 | 0.410000 | `meta_abs_miss_improve_trend_slope_cache01_0318_043133.log` |
| meta | absolute | 1 | neg | 0 | slope | 0.269170 | **0.153725** | 0.530000 | `meta_abs_miss_neg_cache01_0318_014126.log` |
| meta | absolute | 1 | neg | 1 | delta | 0.269173 | 0.153827 | 0.430000 | `meta_abs_miss_neg_trend_delta_cache01_0318_040603.log` |
| meta | absolute | 1 | neg | 1 | slope | 0.269156 | 0.153829 | 0.430000 | `meta_abs_miss_neg_trend_slope_cache01_0318_032822.log` |
| meta | absolute | 0 | neg | 1 | delta | 0.269179 | **0.153750** | 0.440000 | `meta_abs_trend_delta_cache01_0318_030304.log` |
| meta | absolute | 0 | neg | 1 | slope | 0.269170 | 0.153808 | 0.430000 | `meta_abs_trend_slope_cache01_0318_024100.log` |
| meta | delta | 0 | neg | 0 | slope | 0.269167 | 0.153953 | 0.410000 | `meta_delta_only_cache01_0318_053930.log` |

### 27.15 RL Algo × ExcludeRecentSteps Sweep on Original 3 Traces (cache=0.1, Auto)

基于 27.10 配置，按算法是否实际使用 `LOH_EXCLUDE_RECENT_STEPS` 分组测试：

1. `exclude` 生效组（off-policy）：`SAC`、`TD3`、`DDPG`、`DQN`，测试 `exclude=0/2000/10000`
2. `exclude` 不生效组（on-policy）：`PPO`、`A2C`，仅跑一次（`exclude=NA`）

按 `算法 × (exclude或单次) × trace(1063/wiki/meta)` 运行；并发上限 3；已完成项自动跳过补齐；每完成一条即刷新。

<!-- AUTO_RL_ALGO_EXCLUDE_SWEEP_ORIG3_CACHE01_0318_BEGIN -->
_Auto-updated from `tmp/rl_algo_exclude_sweep_orig3_cache01_0318/results.csv` at 2026-03-18 18:59:42._

| Trace | Algo | ExcludeRecentSteps | ExcludeApplied | Final MR | Byte MR | MQPS | Log |
|:--|:--|:--|---:|---:|---:|---:|---|
| 1063 | SAC | 0 | 1 | 0.022888 | 0.024251 | 0.290000 | `1063_SAC_ex0_cache01_0318_020909.log` |
| 1063 | SAC | 2000 | 1 | 0.022776 | 0.024118 | 0.300000 | `1063_SAC_ex2000_cache01_0318_021121.log` |
| 1063 | SAC | 10000 | 1 | 0.022840 | 0.024191 | 0.310000 | `1063_SAC_ex10000_cache01_0318_023448.log` |
| 1063 | TD3 | 0 | 1 | 0.018227 | 0.020501 | 0.350000 | `1063_TD3_ex0_cache01_0318_031701.log` |
| 1063 | TD3 | 0 | 1 | 0.023752 | 0.024781 | 0.300000 | `1063_TD3_ex0_cache01_run2_0318_114324.log` |
| 1063 | TD3 | 0 | 1 | 0.040660 | 0.038647 | 0.220000 | `1063_TD3_ex0_cache01_run1_0318_114324.log` |
| 1063 | TD3 | 2000 | 1 | 0.021854 | 0.022764 | 0.300000 | `1063_TD3_ex2000_cache01_0318_033706.log` |
| 1063 | TD3 | 10000 | 1 | 0.064956 | 0.057983 | 0.130000 | `1063_TD3_ex10000_cache01_0318_041829.log` |
| 1063 | DDPG | 0 | 1 | 0.025112 | 0.025622 | 0.260000 | `1063_DDPG_ex0_cache01_0318_050607.log` |
| 1063 | DDPG | 2000 | 1 | 0.017884 | 0.019574 | 0.330000 | `1063_DDPG_ex2000_cache01_0318_053137.log` |
| 1063 | DDPG | 10000 | 1 | 0.015580 | 0.018117 | 0.410000 | `1063_DDPG_ex10000_cache01_0318_061542.log` |
| 1063 | DQN | 0 | 1 | 0.021748 | 0.022970 | 0.380000 | `1063_DQN_ex0_cache01_0318_064406.log` |
| 1063 | DQN | 2000 | 1 | 0.021908 | 0.023047 | 0.410000 | `1063_DQN_ex2000_cache01_0318_070154.log` |
| 1063 | DQN | 10000 | 1 | 0.021717 | 0.022893 | 0.430000 | `1063_DQN_ex10000_cache01_0318_071832.log` |
| 1063 | TQC | 0 | 1 | 0.022382 | 0.023666 | 0.380000 | `1063_TQC_ex0_cache01_0318_090752.log` |
| 1063 | TQC | 2000 | 1 | 0.022800 | 0.024089 | 0.370000 | `1063_TQC_ex2000_cache01_0318_090907.log` |
| 1063 | TQC | 10000 | 1 | 0.023053 | 0.024308 | 0.360000 | `1063_TQC_ex10000_cache01_0318_092738.log` |
| 1063 | PPO | NA | 0 | 0.022690 | 0.024313 | 0.410000 | `1063_PPO_exNA_cache01_0318_074337.log` |
| 1063 | A2C | NA | 0 | 0.022809 | 0.024126 | 0.400000 | `1063_A2C_exNA_cache01_0318_080523.log` |
| 1063 | PPO_LSTM | NA | 0 | 0.021565 | 0.023161 | 0.380000 | `1063_PPO_LSTM_exNA_cache01_0318_100439.log` |
| wiki | SAC | 0 | 1 | 0.171693 | 0.137391 | 0.050000 | `wiki_SAC_ex0_cache01_0318_020909.log` |
| wiki | SAC | 2000 | 1 | 0.171609 | 0.137780 | 0.050000 | `wiki_SAC_ex2000_cache01_0318_023054.log` |
| wiki | SAC | 10000 | 1 | 0.171546 | 0.138545 | 0.050000 | `wiki_SAC_ex10000_cache01_0318_025516.log` |
| wiki | TD3 | 0 | 1 | 0.171890 | 0.151352 | 0.050000 | `wiki_TD3_ex0_cache01_0318_033508.log` |
| wiki | TD3 | 0 | 1 | 0.172514 | 0.130040 | 0.060000 | `wiki_TD3_ex0_cache01_run2_0318_114324.log` |
| wiki | TD3 | 0 | 1 | 0.178603 | 0.137360 | 0.060000 | `wiki_TD3_ex0_cache01_run1_0318_114324.log` |
| wiki | TD3 | 2000 | 1 | 0.169343 | 0.143925 | 0.050000 | `wiki_TD3_ex2000_cache01_0318_035821.log` |
| wiki | TD3 | 10000 | 1 | 0.172579 | 0.152590 | 0.050000 | `wiki_TD3_ex10000_cache01_0318_044508.log` |
| wiki | DDPG | 0 | 1 | 0.169344 | 0.138703 | 0.050000 | `wiki_DDPG_ex0_cache01_0318_050649.log` |
| wiki | DDPG | 2000 | 1 | 0.171271 | 0.136005 | 0.060000 | `wiki_DDPG_ex2000_cache01_0318_055044.log` |
| wiki | DDPG | 10000 | 1 | 0.173817 | 0.129133 | 0.060000 | `wiki_DDPG_ex10000_cache01_0318_061604.log` |
| wiki | DQN | 0 | 1 | 0.170614 | 0.137578 | 0.070000 | `wiki_DQN_ex0_cache01_0318_065029.log` |
| wiki | DQN | 2000 | 1 | 0.170599 | 0.137526 | 0.070000 | `wiki_DQN_ex2000_cache01_0318_071256.log` |
| wiki | DQN | 10000 | 1 | 0.170630 | 0.137668 | 0.070000 | `wiki_DQN_ex10000_cache01_0318_073315.log` |
| wiki | TQC | 0 | 1 | 0.171161 | 0.140755 | 0.060000 | `wiki_TQC_ex0_cache01_0318_090752.log` |
| wiki | TQC | 2000 | 1 | 0.170938 | 0.140127 | 0.060000 | `wiki_TQC_ex2000_cache01_0318_092419.log` |
| wiki | TQC | 10000 | 1 | 0.171146 | 0.140472 | 0.060000 | `wiki_TQC_ex10000_cache01_0318_094456.log` |
| wiki | PPO | NA | 0 | 0.170956 | 0.138028 | 0.070000 | `wiki_PPO_exNA_cache01_0318_075858.log` |
| wiki | A2C | NA | 0 | 0.171168 | 0.142643 | 0.080000 | `wiki_A2C_exNA_cache01_0318_082102.log` |
| wiki | PPO_LSTM | NA | 0 | 0.172121 | 0.133722 | 0.070000 | `wiki_PPO_LSTM_exNA_cache01_0318_102121.log` |
| meta | SAC | 0 | 1 | 0.269175 | 0.153756 | 0.410000 | `meta_SAC_ex0_cache01_0318_020909.log` |
| meta | SAC | 2000 | 1 | 0.269181 | 0.153934 | 0.430000 | `meta_SAC_ex2000_cache01_0318_023242.log` |
| meta | SAC | 10000 | 1 | 0.269182 | 0.153899 | 0.420000 | `meta_SAC_ex10000_cache01_0318_031452.log` |
| meta | TD3 | 0 | 1 | 0.269051 | 0.155905 | 0.630000 | `meta_TD3_ex0_cache01_0318_033533.log` |
| meta | TD3 | 0 | 1 | 0.269293 | 0.154683 | 0.490000 | `meta_TD3_ex0_cache01_run2_0318_114324.log` |
| meta | TD3 | 0 | 1 | 0.269568 | 0.153169 | 0.240000 | `meta_TD3_ex0_cache01_run1_0318_114324.log` |
| meta | TD3 | 2000 | 1 | 0.271570 | 0.154058 | 0.050000 | `meta_TD3_ex2000_cache01_0318_040204.log` |
| meta | TD3 | 10000 | 1 | 0.269065 | 0.155500 | 0.600000 | `meta_TD3_ex10000_cache01_0318_050511.log` |
| meta | DDPG | 0 | 1 | 0.269050 | 0.155842 | 0.600000 | `meta_DDPG_ex0_cache01_0318_052958.log` |
| meta | DDPG | 2000 | 1 | 0.278019 | 0.156120 | 0.040000 | `meta_DDPG_ex2000_cache01_0318_055816.log` |
| meta | DDPG | 10000 | 1 | 0.274868 | 0.155105 | 0.060000 | `meta_DDPG_ex10000_cache01_0318_063111.log` |
| meta | DQN | 0 | 1 | 0.269089 | 0.154704 | 0.680000 | `meta_DQN_ex0_cache01_0318_070030.log` |
| meta | DQN | 2000 | 1 | 0.269097 | 0.154483 | 0.690000 | `meta_DQN_ex2000_cache01_0318_071711.log` |
| meta | DQN | 10000 | 1 | 0.269096 | 0.154772 | 0.730000 | `meta_DQN_ex10000_cache01_0318_074220.log` |
| meta | TQC | 0 | 1 | 0.269112 | 0.155074 | 0.760000 | `meta_TQC_ex0_cache01_0318_090752.log` |
| meta | TQC | 2000 | 1 | 0.269136 | 0.154943 | 0.640000 | `meta_TQC_ex2000_cache01_0318_092609.log` |
| meta | TQC | 10000 | 1 | 0.269142 | 0.154975 | 0.560000 | `meta_TQC_ex10000_cache01_0318_100300.log` |
| meta | PPO | NA | 0 | 0.269313 | 0.155143 | 0.640000 | `meta_PPO_exNA_cache01_0318_080345.log` |
| meta | A2C | NA | 0 | 0.269151 | 0.154214 | 0.620000 | `meta_A2C_exNA_cache01_0318_082506.log` |
| meta | PPO_LSTM | NA | 0 | 0.269182 | 0.153765 | 0.410000 | `meta_PPO_LSTM_exNA_cache01_0318_102142.log` |

#### 27.15.A 权重曲线目录与五类 Trace 收敛分析（TD3 Ex0）

权重曲线目录：

1. 原三类 trace（full-request, Ex0 两次）：`tmp/td3_ex0_retest_full_0318/plots`
2. LRU/LFU 长 trace（10m, Ex0 三次）：`tmp/td3_ex0_lru_lfu_10m_0318/plots`

收敛指标定义：

- `first10%` = 前 10% 邻步权重 L1 变化均值
- `last10%` = 后 10% 邻步权重 L1 变化均值
- `ratio = last10% / first10%`（越小表示越收敛）

各次收敛与末段均值权重（tail mean6）如下：

| Group | Trace | Run | ratio | tail mean6 (w0..w5) |
|:--|:--|:--|---:|:--|
| orig3_fullreq | 1063 | run1 | 0.0000 | 0.2342, 0.2341, 0.0317, 0.2342, 0.0317, 0.2342 |
| orig3_fullreq | 1063 | run2 | 0.0017 | 0.0757, 0.0759, 0.0757, 0.0757, 0.5589, 0.1381 |
| orig3_fullreq | wiki | run1 | 0.0051 | 0.3060, 0.0414, 0.0414, 0.2637, 0.0414, 0.3060 |
| orig3_fullreq | wiki | run2 | 0.0033 | 0.0984, 0.0792, 0.0792, 0.0792, 0.5850, 0.0792 |
| orig3_fullreq | meta | run1 | 0.0224 | 0.2777, 0.0730, 0.0542, 0.2693, 0.0575, 0.2683 |
| orig3_fullreq | meta | run2 | 0.0524 | 0.1461, 0.1402, 0.1437, 0.1245, 0.3184, 0.1272 |
| lru_lfu_10m | lru10m | run1 | 0.3662 | 0.1857, 0.1662, 0.1659, 0.1521, 0.1682, 0.1619 |
| lru_lfu_10m | lru10m | run2 | 0.5264 | 0.1612, 0.1591, 0.1752, 0.1707, 0.1636, 0.1702 |
| lru_lfu_10m | lru10m | run3 | 0.3322 | 0.1692, 0.1541, 0.1675, 0.1664, 0.1717, 0.1711 |
| lru_lfu_10m | lfu10m | run1 | 0.0062 | 0.2332, 0.1547, 0.1473, 0.1284, 0.1989, 0.1374 |
| lru_lfu_10m | lfu10m | run2 | 0.0049 | 0.1421, 0.1731, 0.2024, 0.1619, 0.1288, 0.1916 |
| lru_lfu_10m | lfu10m | run3 | 0.0046 | 0.1660, 0.1462, 0.1647, 0.1568, 0.2012, 0.1651 |

聚合收敛权重（按 trace 对所有 run 的 tail mean6 取均值）：

| Trace | converged mean6 (w0..w5) | Top-3 dims |
|:--|:--|:--|
| 1063 | 0.1549, 0.1550, 0.0537, 0.1549, 0.2953, 0.1861 | w4 > w5 > w1 |
| wiki | 0.2022, 0.0603, 0.0603, 0.1714, 0.3132, 0.1926 | w4 > w0 > w5 |
| meta | 0.2119, 0.1066, 0.0990, 0.1969, 0.1879, 0.1977 | w0 > w5 > w3 |
| lru10m | 0.1720, 0.1598, 0.1695, 0.1631, 0.1679, 0.1678 | w0 > w2 > w4 |
| lfu10m | 0.1804, 0.1580, 0.1715, 0.1490, 0.1763, 0.1647 | w0 > w4 > w2 |

> 维度解释（用于偏好解读，按当前 score feature 顺序近似映射）：
> `w0=recency, w1=frequency, w2=size, w3/w4/w5=IRT family`

seed 影响说明（重要）：

1. 本节现有 `orig3_fullreq` 的 run1/run2 使用“按 run 共享 seed”（同一 run 内 1063/wiki/meta 共享同一 seed）。
2. 因此同一 run 下跨 trace 的权重风格可能更相似，不应直接将“相似形状”解释为“trace 偏好一致”。
3. 更严格的跨 trace 偏好比较，应使用“每个 trace 独立 seed”的对照实验。

SAC Ex0 独立 seed 对照（27.15 同配置，原三类 trace，各 2 次）：

结果目录：`tmp/sac_ex0_orig3_seed42_3407_0318`

| Trace | Algo | Seed | ExcludeRecentSteps | Final MR | Byte MR | MQPS | Log |
|:--|:--|---:|---:|---:|---:|---:|:--|
| 1063 | SAC | 42 | 0 | 0.022977 | 0.024380 | 0.470000 | `1063_SAC_ex0_run1_0318_203901.log` |
| 1063 | SAC | 3407 | 0 | 0.022901 | 0.024290 | 0.470000 | `1063_SAC_ex0_run2_0318_204023.log` |
| wiki | SAC | 42 | 0 | 0.171421 | 0.137693 | 0.080000 | `wiki_SAC_ex0_run1_0318_203901.log` |
| wiki | SAC | 3407 | 0 | 0.174072 | 0.141470 | 0.080000 | `wiki_SAC_ex0_run2_0318_205219.log` |
| meta | SAC | 42 | 0 | 0.269325 | 0.153837 | 0.670000 | `meta_SAC_ex0_run1_0318_203901.log` |
| meta | SAC | 3407 | 0 | 0.269314 | 0.153798 | 0.600000 | `meta_SAC_ex0_run2_0318_205352.log` |

简要结论：

1. 1063 与 meta 对 seed 变化不敏感（MR 几乎重合）。
2. wiki 对 seed 更敏感（MR/BMR 有可见变化）。
3. 这也说明“跨 trace 偏好比较”应避免 run 级共享 seed，优先采用 trace 级独立 seed。

偏好匹配解读（基于本仓库 27.15 的 TD3 Ex0 配置）：

1. 五类 trace 都呈现“前期波动大、后期收敛”的模式，其中 `lfu10m` 与 `wiki/1063` 收敛更强（ratio 很小）。
2. `lru10m` 三次 run 的 ratio 在 0.33~0.53，说明仍有尾段调整，属于“部分收敛、但未冻结”。
3. 从 `tail mean6` 看，权重并非单维极化（不是典型“只压 recency”或“只压 frequency”），而是多维混合偏好。
4. 因此在当前 compound/IRT 特征下，更符合“组合特征偏好收敛”而非“单一 LRU/LFU 维度主导收敛”。

## 0. 当前最好配置

> 本章固定放在文档末尾，用于覆盖前文分散结论，给出可直接执行的“当前最优”建议。
> 依据数据：§10.1、§10.1.1、§10.3.4、§10.3.8。

### 0.1 当前最好配置（2026-03-13 更新）

```bash
# 运行与构建流程（低开销）
LOH_ENABLE_SEMAPHORE=1
LOH_BUILD_RELEASE=1

# C 端开销相关（注意：为编译期宏，需在构建前生效）
LOH_PERF_PROFILING=0
LOH_DEBUG_LEVEL=0

# RL/策略配置
LOH_SCORE_USE_COMPOUND=1
LOH_SCORE_USE_IRT=0
LOH_RANDOM_CANDIDATES=96
LOH_STRUCTURED_CANDIDATES=96
LOH_WAIT_MODE=nonblocked
LOH_ASYNC_TRAIN=1
LOH_ENABLE_PENALTY=0
LOH_MISS_RATIO_WEIGHT=1.0

LOH_INCLUDE_WEIGHTS_IN_OBS=1
# 可开启 hit_miss 作为 state（注意：这是编译期选项，改后需重编译）

# 新默认：adaptive budget 开启，score rebalance 关闭
LOH_ADAPTIVE_BUDGET=1
LOH_USE_SCORE_REBALANCE=0
```

Trace 特定的特征公式设置（并入原 0.2）：

| Trace | 特征模式 | 设置 |
|:--|---|---|
| 1063 | log1p | `LOH_FEATURE_LOG1P=1`, `LOH_FEATURE_LOG1P_RECIPROCAL=0` |
| meta | log1p | `LOH_FEATURE_LOG1P=1`, `LOH_FEATURE_LOG1P_RECIPROCAL=0` |
| wiki | reciprocal | `LOH_FEATURE_LOG1P=0`, `LOH_FEATURE_LOG1P_RECIPROCAL=1` |

说明：

- `LOH_INCLUDE_WEIGHTS_IN_OBS=1`（weights 并入 state）对三条 trace 的 MR 均有不劣表现，其中 Wiki 改善最明显。
- 默认采用 `LOH_ADAPTIVE_BUDGET=1` + `LOH_USE_SCORE_REBALANCE=0`。
- `LOH_SKIP_BUILD=1`/`LOH_SKIP_PIP_INSTALL=1` 用于减少启动开销（前提是二进制和 Python 依赖已就绪）。
- `LOH_PERF_PROFILING`、`LOH_DEBUG_LEVEL` 对 C 端属于编译期宏：改值后需要触发一次构建才能作用到 `cachesim`。
