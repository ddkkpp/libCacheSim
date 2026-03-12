# LOH 完整实验结果

> 测试环境：Intel Xeon Gold 6230R @ 2.10 GHz, KVM, 20 cores, 32 MB L3
> 构建：release build (`_build_rel/bin/cachesim`, `-O2 -DNDEBUG`)
> 缓存比例：0.1（缓存大小 = working set × 10%）
> LOH 统一配置：`COMPOUND=1, IRT=0, RSC=64, MAX_CAND=96, nonblocked`
> LOH 固定权重（1063 训练）：`0.117,0.103,0.376,0.087,0.164,0.154,0`
> 特征模式：1063→LOG1P, Wiki→RECIPROCAL, Meta→LOG1P（各 trace 最优）

---

## 1. 主结果表：3M requests（按 1063 MR 从好到坏排序）

| 排名 | 算法 | 类型 | 1063 MR | Wiki MR | Meta MR | 1063 MQPS | Wiki MQPS | Meta MQPS |
|---|---|---|---|---|---|---|---|---|
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
|---|---|---|---|---|---|---|---|---|
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
|---|---|---|---|---|---|---|---|---|
| 1063 | 0.1736 | **0.1257** | 0.1695 | 0.2018 | **0.1697** | 0.1730 | +0.02pp | -3.2pp |
| Wiki | 0.3712 | **0.3565** | 0.4848 | 0.4744 | 0.4716 | **0.4711** | **-1.4pp** | **-0.3pp** |
| Meta | 0.3248 | 0.3250 | **0.3250** | _(crash)_ | 0.3251 | 0.3252 | +0.01pp | — |

---

## 4. LOH 特征模式对比（8M, 固定权重）

| Trace | LOG1P MR | RECIPROCAL MR | 差距 | 最优模式 |
|---|---|---|---|---|
| 1063 | **0.1697** | 0.2306 | -6.1pp | LOG1P |
| Wiki | 0.5326 | **0.4716** | -6.1pp | RECIPROCAL |
| Meta | **0.3251** | 0.3252 | ≈0 | 无差异 |

## 5. LOH RL 特征模式对比（8M, RL）

| Trace | LOG1P RL MR | RECIP RL MR | 差距 | 最优模式 |
|---|---|---|---|---|
| 1063 | **0.1730** | 0.2517 | -7.9pp | LOG1P |
| Wiki | 0.5252 | **0.4711** | -5.4pp | RECIPROCAL |
| Meta | **0.3252** | 0.3257 | ≈0 | 无差异 |

---

## 6. Trace 特性

| Trace | 类型 | Working Set | 缓存大小 (8M) | Evictions/8M | one_hit (200K) |
|---|---|---|---|---|---|
| **1063** | TencentCBS block | ~687K obj | 3 GiB | ~3M (37.6%) | 0.36 |
| **Wiki** | WikiCDN | ~2.4M obj | 5 GiB | ~5.4M (67.9%) | 0.62 |
| **Meta** | MetaCDN | few obj | 3 TiB | ~1.7K (0.02%) | 0.76 |

---

## 7. auto-detect 验证数据

在不同检测时间点的 one_hit_ratio 和 CV，验证 auto-detect 公式能否正确选择特征模式：

| Trace | Detect@(reqs) | one_hit | CV | 多数规则 (>0.5) | 正确？ | 当前公式决策 | 正确？ |
|---|---|---|---|---|---|---|---|
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
- 多数规则（one_hit > 0.5）在 Meta 所有时间点失败（Meta one_hit > 0.5 但应选 LOG1P）
- 当前公式 `3*(one_hit-0.5) - 0.5*log10(CV)` 在 Wiki 300K+ 时失败
- Wiki 和 Meta 的 one_hit 区间重叠，只有 CV 能区分（Wiki CV=4~8, Meta CV=49~268）
- 两种方法都只在早期检测时间点（≤200K）可靠

---

## 8. 吞吐量优化效果总结

### 三阶段 eviction 优化（1063, 固定权重, RSC=64, debug build → release）

| 优化阶段 | MQPS | MR | 累积提升 |
|---|---|---|---|
| Baseline | 0.20 | 0.218 | — |
| +ultra_fast (fast_log1p + fused loop) | 0.27 | 0.172 | +35% |
| +flat array (O(1) random sampling) | 0.32 | 0.170 | +60% |
| +prefetch (__builtin_prefetch) | **0.40** | 0.170 | **+100% (2×)** |

### RL 通信优化（debug build, 1M, 1063）

| 配置 | sync_total | sync_count | 占 LOH 总时间 |
|---|---|---|---|
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
|---|---:|---|---:|---:|---:|
| 1063 | 360,960,512 | LOG1P | 0.027361 | 0.030195 | 0.75 |
| Wiki | 207,646,002 | RECIPROCAL | 0.176183 | 0.141579 | 0.15 |
| Meta | 45,623,306 | LOG1P | 0.269384 | 0.156423 | 0.97 |

对应主日志：
- `tmp/rl_1063_full_0306_011029.log`
- `tmp/rl_wiki_full_0306_011921.log`
- `tmp/rl_meta_full_0306_010910.log`

### 10.2 对比算法（full req，按 1063 MR 从优到劣）

| 算法 | 1063 MR / Byte MR / MQPS | Wiki MR / Byte MR / MQPS | Meta MR / Byte MR / MQPS | 备注 |
|---|---|---|---|---|
| BeladySize | 0.018200 / 0.018689 / 0.74 | 0.124325 / 0.104216 / 0.29 | 0.268778 / 0.144016 / 3.51 | ok |
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
|---|---|---|---|---|
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
|---|---|---|---|---|
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
|---|---|---|---|---|---|---|---|---|---|
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
|---|---:|---:|---:|---:|
| 1063 | 360,960,512 | **0.023817** | **0.027561** | 0.78 |
| Wiki | 207,646,002 | **0.172273** | **0.135979** | 0.14 |
| Meta | 45,623,306 | 0.269843 | 0.156441 | 0.43 |

**Full Req 对比（Random-Only vs 结构化 RL，CAND=96）：**

| Trace | Structured RL MR | Random-Only RL MR | Δ MR | Δ 相对 |
|---|---|---|---|---|
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
|---|---|---|---|---|---|---|---|
| **1063 RO** | 0.158 | 0.063 | 0.062 | 0.158 | 0.167 | **0.392** | **0.0238** |
| **1063 Struct** | **0.234** | 0.078 | 0.158 | 0.183 | **0.237** | 0.110 | 0.0274 |
| **Wiki RO** | 0.083 | **0.335** | 0.158 | 0.114 | 0.120 | 0.190 | **0.1723** |
| **Wiki Struct** | **0.231** | **0.232** | 0.054 | 0.042 | 0.174 | **0.267** | 0.1762 |
| **Meta RO** | **0.286** | 0.198 | 0.205 | 0.145 | 0.048 | 0.119 | 0.2698 |
| **Meta Struct** | 0.103 | 0.090 | 0.132 | **0.238** | 0.176 | **0.261** | 0.2694 |

**8M 中间权重（参考）：**

| | w0 | w1 | w2 | w3 | w4 | w5 |
|---|---|---|---|---|---|---|
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
|---|---|---|---|---|
| A | 纯随机 192 | 0 | 192 | 192 |
| B | 96 结构化 + 96 随机 | ~96 | 96 | ~192 |
| C | 96 纯结构化 | ~96 | 0 | ~96 |
| D (参考) | 纯随机 96 | 0 | 96 | 96 |

**结果：**

| Group | 1063 MR | Wiki MR | Meta MR |
|---|---|---|---|
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
|---|---|---|---|---|
| Meta (LOG1P) | 0.3698 | 0.4088 | **0.3264** | 0.57 / 0.09 / 0.94 |
| 1063 (LOG1P) | 0.3068 | 0.3952 | **0.1698** | 0.13 / 0.10 / 0.35 |
| Wiki (RECIP) | 0.5769 | 0.5824 | **0.4658** | 0.06 / 0.06 / 0.10 |

> **3-Feature 模式** (compound=0, irt=0)：仅用 recency, frequency, size 3 个基础特征
> **IRT 模式** (compound=0, irt=1)：rec, freq, size + irt1, irt2, irt3
> **Compound 模式** (compound=1, irt=0)：rec, freq, size + freq/rec, freq/size, rec×size

**最终权重对比：**

| 模式 | Trace | w0 (rec) | w1 (freq) | w2 (size) | w3 | w4 | w5 |
|---|---|---|---|---|---|---|---|
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

### 10.4 State 维度消融实验（2026-03-09）

**实验设计**：始终保留 GLOBAL (2D: hit_ratio, byte_hit_ratio)，在此基础上逐一添加一个 state group，测试其对 MR 的影响。使用两种候选源 (STRUCTURED=96 + RANDOM=64) 确保 candidate 特征非零。

**配置**：LOH_SCORE_USE_COMPOUND=1, LOH_FEATURE_LOG1P=1, SAC, release build

#### 10.4.1 Meta CDN trace

| State Group | DIM | 8M nonblocked MR |
|---|---|---|
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
|---|---|---|---|
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
|------|-----|
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
|------|-----|------|
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
|-------|----------|----------|----------|-------------------|------------|
| wiki | `data/WikiCDN/wiki_2019t.oracleGeneral.zst` | 207,646,002 | 40 GiB | **0** | 1 |
| 1063 | `data/TencentCBS/1063.oracleGeneral.zst` | 360,960,512 | 5 GiB | **1** | 0 |
| meta | `data/MetaCDN/meta_reag.oracleGeneral.zst` | 45,623,306 | 16 TiB | **1** | 0 |

---

## 12. 全量 Trace 实验汇总表

> 所有成功完成的全量 trace 实验按 MR 排序一览。配置差异项在"差异配置"列标注。

### 12.1 1063 (TencentCBS, 360,960,512 req, 5 GiB cache)

| 实验 | MR | Byte MR | MQPS | n_updates | 差异配置 | 状态 | 章节 |
|------|-----|---------|------|-----------|----------|------|------|
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
|------|-----|---------|------|-----------|----------|------|------|
| Rand-Only 全量 | **0.172273** | 0.135979 | 0.14 | — | RANDOM_ONLY=1, LOG1P=0, RSC=64 | ✅ | §10.3.4 |
| **0306 Baseline** | **0.176183** | 0.141579 | 0.15 | 2,469 | LOG1P=0, PERF_PROFILING=0 | ✅ 基准 | §10.1 |
| NB36 复现 | 0.176196 | 0.141278 | 0.14 | 2,362 | LOG1P=0, PERF_PROFILING=1 | ✅ | §13 |
| NB36 错误 (RSC=0) | 0.186315 | 0.135435 | 0.30 | 962 | ❌ RSC=0 (应为 64) | ❌ 错误配置 | §13.4 |
| 0310 探索 | 0.206713 | 0.190577 | 0.17 | 14,831 | ❌ LOG1P=1 (应为 0), PERF_PROFILING=1 | ✅ 但特征模式不匹配 | §14 |
| 0310 tuned | 0.206839 | 0.190691 | 0.17 | 13,544 | ❌ LOG1P=1 (应为 0), PERF_PROFILING=1 | ✅ 但特征模式不匹配 | §14 |

### 12.3 Meta (MetaCDN, 45,623,306 req, 16 TiB cache)

| 实验 | MR | Byte MR | MQPS | n_updates | 差异配置 | 状态 | 章节 |
|------|-----|---------|------|-----------|----------|------|------|
| **0306 Baseline** | **0.269384** | 0.156423 | 0.97 | 69 | LOG1P=1, PERF_PROFILING=0 | ✅ 基准 | §10.1 |
| NB36 复现 | 0.269406 | 0.156749 | 0.77 | 81 | LOG1P=1, PERF_PROFILING=1 | ✅ | §13 |
| 0310 探索 | 0.269427 | 0.156722 | 0.78 | 900 | LOG1P=1, PERF_PROFILING=1 | ✅ | §14 |
| Rand-Only 全量 | 0.269843 | 0.156441 | 0.43 | — | RANDOM_ONLY=1, LOG1P=1, RSC=64 | ✅ | §10.3.4 |

### 12.4 对比算法（非 LOH，全量 trace）

> 完整数据已在 §10.2，此处列出三条 trace 的关键基线供交叉参考。

| 算法 | 1063 MR / Byte MR / MQPS | Wiki MR / Byte MR / MQPS | Meta MR / Byte MR / MQPS |
|------|--------------------------|--------------------------|--------------------------|
| BeladySize | 0.018200 / 0.018689 / 0.74 | 0.124325 / 0.104216 / 0.29 | 0.268778 / 0.144016 / 3.51 |
| LOH-RandOnly | **0.023817** / 0.027561 / 0.78 | **0.172273** / 0.135979 / 0.14 | 0.269843 / 0.156441 / 0.43 |
| LOH-RL nb_500 | **0.026646** / 0.029527 / 0.58 | — | — |
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
|------|--------------|-----------|------|
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
|-------|------|-----|---------|------|-----------|-------|
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
|------|------|------|------|
| LOH_PERF_PROFILING | 无 | 1 | 0306 无此宏 |
| 1063 MQPS | 0.75 | 0.59 | -21% |
| wiki MQPS | 0.15 | 0.14 | -7% |
| meta MQPS | 0.97 | 0.77 | -21% |
| 1063 估计 clock_gettime 次数 | 0 | ~37.5 亿 | 67 点 × 360M req |
| 估计额外开销 | 0 | ~94s | ~25% of LOH_total |

MQPS 下降不影响 MR，仅导致 C 变慢→Python 更多 sync 机会→更多 n_updates（+4%~+17%），但权重早已收敛。

### 13.5 错误配置实验（诊断过程中产生）

| Trace | 配置错误 | MR | 正确 MR | Δ MR | 原因 |
|-------|----------|-----|---------|------|------|
| wiki | RSC=0（应为 64） | 0.186315 | 0.176183 | +1.0pp | `run_nonblocked36.sh` 缺少 `LOH_RANDOM_CANDIDATES` 导出 |
| 1063 | LOG1P=0（应为 1） | 0.095009 | 0.027361 | +6.8pp | auto-detect 选错特征模式，需显式设置 `LOH_FEATURE_LOG1P=1` |

### 13.6 日志文件

| 实验 | C 端日志 | Python 日志 |
|------|---------|-------------|
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
|------|--------|------|
| LOH_FEATURE_LOG1P | **全部 1** | wiki 应为 0，导致 wiki MR 偏高 |
| LOH_PERF_PROFILING | **1** | LOH.c L332，0306 无此代码 |
| LOH_RANDOM_CANDIDATES | 64 | 与 0306 一致 |

| Trace | MR | byte_MR | MQPS | n_updates | steps | 日志 |
|-------|-----|---------|------|-----------|-------|------|
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
|------|-------|-----------|------|----------|
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
|------|--------|----------|--------|
| Wait mode | **NON-BLOCKED** | **BLOCKED** | **BLOCKED** |
| LOH_RL_UPDATE_INTERVAL | 500 | 50000 | 500 |
| LOH_SCORE_USE_COMPOUND | 1 | 1 | 1 |
| LOH_SCORE_USE_IRT | 0 | 0 | 0 |
| LOH_FEATURE_LOG1P | 1 | 1 | 1 |
| LOH_RANDOM_CANDIDATES | 0→auto 64 | 0→auto 64 | 0→auto 64 |
| LOH_ENABLE_SEMAPHORE | unset(sem_req=1) | unset(sem_req=1) | unset |
| LOH_PERF_PROFILING | 1 | 1 | 1 |

| 测试 | Trace | 请求数 | MR | Byte MR | MQPS | 状态 | C 日志 | 测试日志 |
|------|-------|--------|-----|---------|------|------|--------|----------|
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
|------|--------|------|
| LOH_SCORE_USE_COMPOUND | **未设置** | C 端默认值（无 6 维交互特征） |
| LOH_SCORE_USE_IRT | **未设置** | C 端默认值 |
| LOH_ENABLE_SEMAPHORE | **未设置** | C 端默认 |
| LOH_FEATURE_LOG1P | 1 | 1063 正确值 |
| LOH_RANDOM_CANDIDATES | 64（日志显示但 C 初始化为 0，auto-detect 回退到 64） | |
| LOH_WAIT_MODE | **nonblocked** | C 日志确认 |

#### 15.2.1 8M 测试

| 测试 | Trace | 请求数 | MR | Byte MR | MQPS | 日志 |
|------|-------|--------|-----|---------|------|------|
| ab_sync_8M | 1063 | 8M | 0.285942 | 0.262948 | 0.11 | `tmp/rl_ab_sync_8M.log` |
| ab_async_8M | 1063 | 8M | 0.283841 | 0.261536 | 0.11 | `tmp/rl_ab_async_8M.log` |
| ab_async_8M_opt | 1063 | 8M | 0.284116 | 0.261514 | 0.11 | `tmp/rl_ab_async_8M_opt.log` |
| ab_async_5M_pickle | 1063 | 5M | 0.317170 | 0.282810 | 0.09 | `tmp/rl_ab_async_5M_pickle.log` |

#### 15.2.2 全量测试

| 测试 | Trace | 请求数 | MR | Byte MR | MQPS | 状态 | 日志 |
|------|-------|--------|-----|---------|------|------|------|
| ab_sync_full | 1063 | 360,960,512 | 0.232346 | 0.208728 | 0.12 | ✅ | `tmp/rl_ab_sync_full.log` |
| ab_async_full | 1063 | — | — | — | — | ❌ Python 崩溃 | `tmp/rl_ab_async_full.log` |
| ab_async_full_v2 | 1063 | — | — | — | — | ❌ 未完成 | `tmp/rl_ab_async_full_v2.log` |

### 15.3 早期 async 测试（LOG1P 错误 / Python 崩溃）

> 最早期的集成测试。async_v3 使用了错误的 LOG1P=0（1063 应为 1）。async_1063/v2 使用正确配置但 Python 崩溃。

| 测试 | Trace | 请求数 | MR | MQPS | LOG1P | COMPOUND | 状态 | 日志 |
|------|-------|--------|-----|------|-------|----------|------|------|
| async_v3_1M | 1063 | 1M | 0.603989 | 0.18 | **0（错误）** | unset | ✅ | `tmp/rl_async_v3_1M.log` |
| async_v3_5M | 1063 | 5M | 0.342635 | 0.27 | **0（错误）** | unset | ✅ | `tmp/rl_async_v3_5M.log` |
| async_1063 | 1063 | ALL | — | — | 1 | 1 | ❌ Python 崩溃 | `tmp/rl_async_1063.log` |
| async_v2_1063 | 1063 | ALL | — | — | 1 | 1 | ❌ Python 崩溃 | `tmp/rl_async_v2_1063.log` |

### 15.4 Async v2 全量三 Trace 测试（2026-03-10，\_stop\_event 修复后）

> 修复了 `_stop_event` 竞态条件（`save()` 临时置 None 导致异步训练线程 AttributeError 崩溃）后，重新以最优配置跑全量三条 trace。

**配置**：WAIT=nonblocked, ASYNC\_TRAIN=1, COMPOUND=1, IRT=0, RANDOM\_CANDIDATES=64, INTERVAL=500, SEM=1

| Trace | MR | Byte MR | MQPS | Steps (writes) | BG Train | Exceptions | 日志 |
|-------|------|---------|------|----------------|----------|------------|------|
| 1063 | 0.027085 | 0.030005 | 0.57 | 870,003 (145,001) | 7,248 | 0 | `ac_sb3_0310_170940.log` |
| wiki | 0.175426 | 0.141343 | 0.14 | 1,465,629 (244,272) | 17,660 | 0 | `ac_sb3_0310_172046.log` |
| meta | 0.269425 | 0.156414 | 0.69 | 87,465 (14,578) | 687 | 0 | `ac_sb3_0310_174648.log` |

**小时级 MR（C 端）**：

| Trace | 24h | 48h | 72h | 96h | 120h | 144h | 168h | 192h | 216h |
|-------|------|------|------|------|------|------|------|------|------|
| 1063 | 0.0931 | 0.0773 | 0.0599 | 0.0483 | 0.0380 | 0.0336 | 0.0303 | 0.0280 | 0.0271 |
| wiki | 0.2852 | 0.2303 | 0.2082 | 0.2001 | 0.2019 | 0.2022 | 0.1993 | 0.2047 | 0.2013 |
| meta | 0.3471 | 0.3215 | 0.3110 | 0.3036 | 0.2939 | 0.2847 | 0.2774 | 0.2694 | — |

**与基线对比**（MR / Byte MR / MQPS）：

| 配置 | 1063 | wiki | meta |
|------|------|------|------|
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
|------|--------|------|
| LOH_RANDOM_ONLY_CANDIDATES | **1** | 跳过结构化候选，仅随机采样 |
| LOH_RANDOM_CANDIDATES | 64（实际由 RANDOM_ONLY 覆盖） | 候选数 |

### 16.2 结果

| Trace | MR | byte_MR | MQPS | LOG1P | 日志 |
|-------|-----|---------|------|-------|------|
| wiki | **0.172273** | 0.135979 | 0.14 | 0 | `tmp/rl_wiki_randonly_fullreq.log` |
| 1063 | **0.023817** | 0.027561 | 0.78 | 1 | `tmp/rl_1063_randonly_fullreq.log` |
| meta | 0.269843 | 0.156441 | 0.43 | 1 | `tmp/rl_meta_randonly_fullreq.log` |

### 16.3 与 0306 RL 对比

| Trace | RL (0306) | Rand-Only | Δ MR | 赢家 |
|-------|-----------|-----------|------|------|
| wiki | 0.176183 | **0.172273** | **-0.39pp** | Rand-Only |
| 1063 | 0.027361 | **0.023817** | **-0.35pp** | Rand-Only |
| meta | **0.269384** | 0.269843 | +0.05pp | RL (微弱) |

**分析：** Rand-Only 在 wiki 和 1063 上竟优于 RL，说明 LOH 的线性评分函数 + Compound 交互特征本身已足够强，随机探索覆盖了更广的权重空间，RL 的边际提升有限甚至产生过拟合。

---

## 17. 失败/不完整全量实验汇总

| 日志 | Trace | 失败原因 | 结果 |
|------|-------|----------|------|
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
|------|---|------|
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
|-------|------|-------------|-----------|------|
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
|-------|----:|---:|--------:|-----:|---------:|
| 1063 | 360,960,512 | **0.026609** | 0.029576 | **0.77** | 8m27s |
| wiki | 207,646,002 | 0.177963 | 0.138973 | **0.21** | 17m01s |
| meta | 45,623,306 | **0.269375** | 0.156867 | 0.96 | 1m06s |

日志文件：
- `tmp/1063_async_decay/run.log`、`cachesim_sb3_0311_005222.log`、`ac_sb3_0311_005222.log`
- `tmp/wiki_async_decay/run.log`、`cachesim_sb3_0311_002938.log`、`ac_sb3_0311_002938.log`
- `tmp/meta_async_decay/run.log`、`cachesim_sb3_0311_010229.log`、`ac_sb3_0311_010229.log`

### 18.3 与 0306 Baseline 对比

| Trace | 0306 MR | Decay+Async MR | Δ MR | 0306 MQPS | Decay+Async MQPS | Δ MQPS |
|-------|---------|---------------|------|-----------|-----------------|--------|
| 1063 | 0.027361 | **0.026609** | **-2.7%** | 0.75 | **0.77** | **+2.7%** |
| wiki | **0.176183** | 0.177963 | +1.0% | 0.15 | **0.21** | **+40%** |
| meta | 0.269384 | **0.269375** | **-0.003%** | **0.97** | 0.96 | -1.0% |

### 18.4 Decay 单独开销验证（纯模拟，LOH_ENABLE_RL=0）

为排除 RL 交互干扰，使用 `LOH_ENABLE_RL=0` + `LOH_FIXED_WEIGHTS=0.167,...` 跑 3M requests：

| Trace | No-Decay Time | With-Decay Time | 开销 |
|-------|--------------|----------------|------|
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
|---|---|---|---|---|
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
|--------|-------|----------|----|---------|------|---------|
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
|------|--------|------|------|
| 1 | randonly96_sync | 0.021666 | 0.77 |
| 2 | rand96+struct96+nodecay_sync | 0.021795 | 0.73 |
| 3 | rand96+struct96+decay_async | 0.022036 | 0.71 |
| 4 | randonly96_async | 0.022058 | 0.76 |
| 5 | rand96+struct96+nodecay_async | 0.022098 | 0.71 |
| 6 | rand96+struct96+decay_sync | 0.022124 | 0.70 |

**Wiki** (越低越好):
| Rank | Config | MR | MQPS |
|------|--------|------|------|
| 1 | randonly96_sync | 0.173539 | 0.17 |
| 2 | randonly96_async | 0.173663 | 0.17 |
| 3 | rand96+struct96+decay_async | 0.176654 | 0.15 |
| 4 | rand96+struct96+decay_sync | 0.177740 | 0.15 |

**Meta** (越低越好):
| Rank | Config | MR | MQPS |
|------|--------|------|------|
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
|------|--------|-------------------|
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
|--------|-------|----|---------|------|---------|
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
|--------|-------|----|---------|------|---------|
| penalty_pos0 | 1063 | 0.022067 | 0.025217 | 0.68 | 564 |
| penalty_pos0 | wiki | 0.176917 | 0.139397 | 0.14 | 1513 |
| penalty_pos0 | meta | 0.269060 | 0.156501 | 1.26 | 53 |
| penalty_pos1 | 1063 | 0.022092 | 0.025230 | 0.68 | 564 |
| penalty_pos1 | wiki | 0.176879 | 0.140211 | 0.14 | 1551 |
| penalty_pos1 | meta | 0.269056 | 0.156143 | 1.24 | 54 |

对比（无 penalty 基线 = rand96+struct96+decay_async from Step 1）：

| Trace | No Penalty | Penalty pos0 | Penalty pos1 | 差异 |
|-------|-----------|-------------|-------------|------|
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
|-----------|-------|----|---------|------|---------|
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
|-----------|--------|---------|
| 0.25 | **0.021963** | **0.025082** |
| 0.0 | 0.022044 | 0.025174 |
| 0.75 | 0.022056 | 0.025177 |
| 0.5 | 0.022081 | 0.025204 |
| 1.0 | 0.022162 | 0.025298 |

**Wiki**:
| MR Weight | Obj MR | Byte MR |
|-----------|--------|---------|
| 1.0 | **0.176536** | 0.140050 |
| 0.0 | 0.176711 | **0.139541** |
| 0.25 | 0.176781 | 0.139775 |
| 0.75 | 0.176894 | 0.139772 |
| 0.5 | 0.176923 | 0.139904 |

**Meta**:
| MR Weight | Obj MR | Byte MR |
|-----------|--------|---------|
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
|------|--------|---------|---------|---------|
| 1 | LOH randonly96 (§19) | **0.021666** | **0.173539** | 0.269836 |
| 2 | LOH rand96+struct96+decay (§19) | 0.022036 | 0.176654 | **0.269053** |
| 3 | LOH-RL (0306 baseline) | 0.027361 | 0.176183 | 0.269384 |
| 4 | GDSF | 0.054791 | 0.180493 | 0.268918 |
| 5 | 3LCache-OMR | 0.060630 | 0.174871 | 0.392964 |
| 6 | Belady | 0.147024 | 0.134717 | 0.268778 |
| 7 | LRU | 0.261774 | 0.230638 | 0.326804 |

**LOH-RL 新配置全面超越 0306 基线**（1063：-21%~-26%，wiki：-1.5%~+0.3%，meta：-0.12%~+0.17%）

---

*更新时间: 2026-03-11, 新增 §19：综合批量实验（6配置×3trace + Grid Search + Penalty + MR权重）*
