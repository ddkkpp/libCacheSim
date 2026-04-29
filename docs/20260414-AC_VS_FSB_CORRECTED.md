# AC (FR=OFF) vs FSB v2 修正对比报告

**日期**: 2026-04-14 (修正版)
**前情**: 两份先行文档 (`20260414-AC_VS_FSB_COMPARISON.md` 和 `20260414-FSB_V2_BROAD_EVALUATION.md`) 得出**相反结论**。本文档纠正方法论问题，给出**同一样本、同一 AC 定义**的可信对比。

---

## 1. 先行文档的矛盾与问题

### 1.1 矛盾概览

| | 文档 1 (04-16 COMPARISON) | 文档 2 (04-15 EVALUATION) |
|:---|:---|:---|
| **主张** | AC 全面优于 FSB | FSB 全面优于 AC |
| **AC 版本** | FR=OFF (f0xx, 真实代码) | AC v5 FR=ON (f1xx, 假设变体) |
| **AC 数据** | 1115 traces, post-hoc | 43 traces, r1/r2 模拟 |
| **FSB 数据** | 43 traces | 43 traces (同一数据) |
| **AC avg regret** | 3.75% | 38.17% (FR=ON) / 33.10% (FR=OFF) |

### 1.2 确认的问题

#### 问题 A：AC 定义不一致

- **真实代码**的 AUTO_COMPOUND: `freq_rec 固定关闭`, r1>0.98→关 freq_size, r2>0.98→关 rec_size → 搜索空间 f0xx (f000/f001/f010/f011)
- 文档 1 使用了正确定义
- 文档 2 的主要对比用了 "AC v5 FR=ON" (搜索 f1xx)——这**不是真实代码**

#### 问题 B：样本池不对等（文档 1 的致命缺陷）

文档 1 用 1115-trace 全局平均 (3.75%) 与 43-trace FSB 平均 (10.22%) 直接比较。

1115 traces 的组成中有 ~396 条 alibaba_10K/100K/1K 子集，它们的 avg gap 仅 0.12%~1.71%（决策极容易），把全局均值大幅稀释。43 条 FSB traces 没有这些容易子集，是刻意选取的多样化代表（含 tencent、twitter 等难组）。

> **3.75% vs 10.22% 是苹果比桔子，不可信。**

#### 问题 C：文档 2 的 AC FR=OFF 对比也有偏差

文档 2 Section 6.4 的 "AC v5 FR=OFF" median regret 7.16%（43 traces）远高于文档 1 的全局 3.75%。这是因为 43 traces 子集确实比 1115-trace 全局更"难"。但文档 2 的 AC FR=OFF 数据来源是 r1/r2 gating 模拟，**未使用实际穷举 ablation 的 AC MR 值**（部分 trace 用的可能是近似值而非实测值）。

---

## 2. 修正方法

### 2.1 统一样本

使用 FSB v2 实测的 43 traces 中**有完整数据的 42 条**作为统一样本（排除 kv_202206，无 ext ablation 数据）。

### 2.2 统一 AC 定义

AC = 真实代码的 AUTO_COMPOUND (FR=OFF):
- freq_rec 固定关闭
- r1>0.98 → 关闭 freq_size
- r2>0.98 → 关闭 rec_size
- 搜索空间: f000 / f001 / f010 / f011

### 2.3 AC MR 数据来源

- **29 traces** (alibaba, cloudphysics, metaCDN, metaKV, wiki): 从 `tmp/20260411-feature-ablation/ablation_autocompound.md` 提取实测 AC MR
- **13 traces** (tencent, twitter): 从 `tmp/20260413-feature-ablation-ext/results/` 的对应 config .cachesim 文件提取实测 MR
- r1/r2 值来源: FSB 运行日志中的 WARMUP_DIAG

### 2.4 Oracle 基准

穷举 8 config (f000~f111) 的 MR 最小值作为 Oracle。

---

## 3. 修正结果

### 3.1 总体对比 (n=42)

| 指标 | AC (FR=OFF) | FSB v2 |
|:---|:---|:---|
| **胜负** | **23 胜 (54.8%)** | 16 胜 (38.1%) |
| 平局 | 3 (7.1%) | — |
| **avg MR regret** | **+4.22%** | +22.88% |
| **median MR regret** | **+0.48%** | +2.76% |
| max MR regret | +34.1% | +532.3% |

### 3.2 去除 alibaba_188 极端 outlier (n=41)

| 指标 | AC (FR=OFF) | FSB v2 |
|:---|:---|:---|
| **胜负** | **22 胜 (53.7%)** | 16 胜 (39.0%) |
| **avg MR regret** | **+4.07%** | +10.45% |
| **median MR regret** | **+0.42%** | +2.69% |

### 3.3 分组对比

| 组 | n | AC avg reg | FSB avg reg | AC med | FSB med | AC胜 | FSB胜 | 平 | 组胜者 |
|:---|---:|---:|---:|---:|---:|---:|---:|---:|:---|
| alibaba | 9 | **+3.4%** | +73.7% | **+0.2%** | +0.3% | 5 | 3 | 1 | **AC** |
| cloudphysics | 14 | **+1.8%** | +6.8% | **+0.0%** | +2.8% | 8 | 5 | 1 | **AC** |
| metaCDN | 2 | **+0.0%** | +2.5% | **+0.0%** | +2.5% | 2 | 0 | 0 | **AC** |
| metaKV | 1 | **+0.5%** | +1.6% | — | — | 1 | 0 | 0 | **AC** |
| tencent | 10 | **+6.3%** | +12.2% | **+4.8%** | +9.0% | 5 | 4 | 1 | **AC** |
| twitter | 3 | +17.1% | +23.8% | +17.1% | +28.2% | 1 | **2** | 0 | **FSB** |
| wiki | 3 | +2.4% | **+1.0%** | +1.3% | **+0.1%** | 1 | **2** | 0 | **FSB** |

AC 在 5/7 组胜出，FSB 仅在 twitter 和 wiki 两组胜出。

---

## 4. 逐 trace 对比表

| trace | 组 | AC cfg | AC MR | FSB cfg | FSB MR | Oracle | Oracle MR | AC reg% | FSB reg% | 胜 |
|:---|:---|:---|---:|:---|---:|:---|---:|---:|---:|:---|
| alibaba_15 | alibaba | f011 | 0.5501 | f110 | 0.5519 | f011 | 0.5501 | +0.0% | +0.3% | AC |
| alibaba_17 | alibaba | f001 | 0.1483 | f111 | 0.2922 | f001 | 0.1483 | +0.0% | +97.0% | AC |
| alibaba_188 | alibaba | f001 | 0.0421 | f010 | 0.2409 | f000 | 0.0381 | +10.5% | +532.3% | AC |
| alibaba_210 | alibaba | f001 | 0.2212 | f000 | 0.2182 | f000 | 0.2182 | +1.4% | +0.0% | FSB |
| alibaba_25 | alibaba | f011 | 0.5402 | f011 | 0.5402 | f011 | 0.5402 | +0.0% | +0.0% | TIE |
| alibaba_256 | alibaba | f001 | 0.0912 | f010 | 0.1085 | f000 | 0.0910 | +0.2% | +19.2% | AC |
| alibaba_324 | alibaba | f001 | 0.1491 | f100 | 0.1709 | f001 | 0.1491 | +0.0% | +14.6% | AC |
| alibaba_401 | alibaba | f001 | 0.1642 | f000 | 0.1486 | f000 | 0.1486 | +10.5% | +0.0% | FSB |
| alibaba_742 | alibaba | f011 | 0.4704 | f111 | 0.4365 | f111 | 0.4365 | +7.8% | +0.0% | FSB |
| cluster3 | twitter | f011 | 0.0252 | f111 | 0.0241 | f000 | 0.0188 | +34.1% | +28.2% | FSB |
| cluster49 | twitter | f011 | 0.1084 | f001 | 0.0926 | f001 | 0.0926 | +17.1% | +0.0% | FSB |
| cluster7 | twitter | f011 | 0.0757 | f110 | 0.1083 | f011 | 0.0757 | +0.0% | +43.1% | AC |
| meta_kvcache1 | metaKV | f011 | 0.0559 | f110 | 0.0565 | f010 | 0.0556 | +0.5% | +1.6% | AC |
| meta_reag | metaCDN | f011 | 0.2707 | f010 | 0.2829 | f011 | 0.2707 | +0.0% | +4.5% | AC |
| meta_rprn | metaCDN | f011 | 0.3343 | f111 | 0.3359 | f011 | 0.3343 | +0.0% | +0.5% | AC |
| tBlock_1063 | tencent | f011 | 0.0201 | f010 | 0.0221 | f001 | 0.0194 | +3.4% | +13.9% | AC |
| tBlock_10927 | tencent | f011 | 0.0569 | f110 | 0.0635 | f001 | 0.0536 | +6.2% | +18.5% | AC |
| tBlock_14833 | tencent | f011 | 0.1326 | f101 | 0.1444 | f011 | 0.1326 | +0.0% | +8.9% | AC |
| tBlock_17226 | tencent | f001 | 0.0062 | f111 | 0.0056 | f111 | 0.0056 | +11.1% | +0.0% | FSB |
| tBlock_18304 | tencent | f000 | 0.0011 | f010 | 0.0013 | f110 | 0.0009 | +22.1% | +44.4% | AC |
| tBlock_20067 | tencent | f001 | 0.0063 | f111 | 0.0061 | f111 | 0.0061 | +3.1% | +0.0% | FSB |
| tBlock_2115 | tencent | f011 | 0.0286 | f111 | 0.0266 | f111 | 0.0266 | +7.3% | +0.0% | FSB |
| tBlock_22734 | tencent | f001 | 0.0021 | f010 | 0.0021 | f000 | 0.0021 | −1.5% | +0.0% | TIE |
| tBlock_23479 | tencent | f001 | 0.0061 | f101 | 0.0060 | f000 | 0.0055 | +11.1% | +9.1% | FSB |
| tBlock_6554 | tencent | f011 | 0.1274 | f110 | 0.1608 | f010 | 0.1267 | +0.5% | +26.9% | AC |
| w01 | cloudphysics | f011 | 0.7737 | f111 | 0.7754 | f011 | 0.7737 | +0.0% | +0.2% | AC |
| w03 | cloudphysics | f011 | 0.5348 | f110 | 0.5386 | f111 | 0.5335 | +0.2% | +1.0% | AC |
| w08 | cloudphysics | f011 | 0.4299 | f110 | 0.5650 | f011 | 0.4299 | +0.0% | +31.4% | AC |
| w105 | cloudphysics | f011 | 0.5733 | f111 | 0.5434 | f111 | 0.5434 | +5.5% | +0.0% | FSB |
| w11 | cloudphysics | f011 | 0.4297 | f111 | 0.4667 | f001 | 0.4176 | +2.9% | +11.8% | AC |
| w14 | cloudphysics | f011 | 0.4598 | f000 | 0.4808 | f011 | 0.4598 | +0.0% | +4.6% | AC |
| w17 | cloudphysics | f001 | 0.1203 | f101 | 0.1199 | f011 | 0.1166 | +3.2% | +2.8% | FSB |
| w20 | cloudphysics | f011 | 0.6282 | f111 | 0.6256 | f111 | 0.6256 | +0.4% | +0.0% | FSB |
| w23 | cloudphysics | f011 | 0.2032 | f011 | 0.2032 | f011 | 0.2032 | +0.0% | +0.0% | TIE |
| w50 | cloudphysics | f011 | 0.1355 | f010 | 0.1536 | f011 | 0.1355 | +0.0% | +13.4% | AC |
| w86 | cloudphysics | f011 | 0.9322 | f010 | 0.9319 | f010 | 0.9319 | +0.0% | +0.0% | FSB |
| w87 | cloudphysics | f011 | 0.7162 | f101 | 0.7355 | f011 | 0.7162 | +0.0% | +2.7% | AC |
| w90 | cloudphysics | f011 | 0.4328 | f111 | 0.4244 | f100 | 0.3851 | +12.4% | +10.2% | FSB |
| w94 | cloudphysics | f011 | 0.3397 | f110 | 0.3970 | f011 | 0.3397 | +0.0% | +16.9% | AC |
| wiki_2016u | wiki | f011 | 0.0234 | f101 | 0.0231 | f101 | 0.0231 | +1.3% | +0.0% | FSB |
| wiki_2019t | wiki | f001 | 0.1805 | f111 | 0.1707 | f010 | 0.1706 | +5.8% | +0.1% | FSB |
| wiki_2019u | wiki | f011 | 0.0283 | f111 | 0.0291 | f011 | 0.0283 | +0.0% | +2.8% | AC |

---

## 5. 分析

### 5.1 AC 为什么整体更好

1. **零噪声决策**: AC 基于 warmup 统计量 (r1/r2) 做一次性决策，不受短期 MR 波动影响；FSB 的 UCB 在 5 轮短 block 中容易被噪声误导
2. **f0xx 搜索空间匹配多数 trace**: 1115-trace 全局中 71.7% 的 Oracle 最优 config 在 f0xx 范围内，AC 天然覆盖
3. **AC 的 regret 上界更低**: max regret 34.1% vs FSB 的 532.3%；AC 没有灾难性失败

### 5.2 FSB 什么时候更好

FSB 在 **twitter 和 wiki 组**胜出（共 6 traces），原因：
- **twitter cluster3/cluster49**: Oracle 最优 config 分别是 f000 和 f001，但 AC 选了 f011（r1/r2 都不超 0.98）。AC 的 gating 阈值 (0.98) 不够敏感，该关的 compound 没关
- **wiki_2019t**: Oracle = f010，AC 选了 f001（r1=0.9915>0.98 关了 freq_size → 正确，但 r2=0.7626 保留了 rec_size → 错误，应该也关）
- **wiki_2016u**: Oracle = f101 (含 freq_rec)，AC(FR=OFF) 结构上不可达

### 5.3 两方各自的系统性弱点

| | AC (FR=OFF) | FSB v2 |
|:---|:---|:---|
| **结构性盲区** | 无法选 f1xx (含 freq_rec)；影响 28.3% 的全局 oracle | 无盲区，可搜全部 8 config |
| **噪声敏感性** | 不敏感（单次统计决策） | **高度敏感**（5 轮 UCB 可被 R0 主导） |
| **尾部灾难** | 最大 34.1% | **最大 532.3%** |
| **额外开销** | 零 | 需要 block_size × rounds × arms 的探索期 |
| **gating 阈值问题** | 0.98 不适用所有 trace | N/A |

---

## 6. 与两份先行文档的对标

### 6.1 vs 文档 1 (AC_VS_FSB_COMPARISON.md)

- **方向正确**: AC 确实优于 FSB
- **量级不准**: 文档 1 声称 AC avg 3.75% vs FSB 10.22%，实际同样本比是 AC 4.22% vs FSB 22.88%（或去 outlier 4.07% vs 10.45%）
- **方法有缺陷**: 不等样本比较不具说服力

### 6.2 vs 文档 2 (FSB_V2_BROAD_EVALUATION.md)

- **Section 6.3 结论错误**: "FSB 在所有维度显著优于 AC v5"——使用了错误的 AC 变体 (FR=ON)
- **Section 6.4 AC FR=OFF 数据**: median 7.16% 偏高（本文修正为 0.48%），原因未查明，可能是 r1/r2 gating 模拟方式与实际穷举结果有差异
- **FSB 自身评估仍然准确**: FSB median 2.76~2.78%、命中率 30% 等数据本文复现一致

---

## 7. 结论

### 7.1 修正后的可信结论

**AC(FR=OFF) 在同样本 42 traces 上以 54.8% 胜率和 5× 更低 avg regret 胜过 FSB v2。** 推荐默认使用 AC (`LOH_AUTO_COMPOUND=1`)。

### 7.2 各方法定位

| 方法 | avg regret | median regret | 最大风险 | 推荐场景 |
|:---|:---|:---|:---|:---|
| **AC (FR=OFF)** | 4.2% | 0.5% | 34% | **默认方案**，适用于大多数 trace |
| FSB v2 | 22.9% | 2.8% | 532% | 需探索 f1xx 时可考虑，但需防尾部风险 |
| Full ablation | 0% | 0% | 0% | 对 regret 敏感的关键场景 |

### 7.3 注意事项

- AC 在 **twitter 和 wiki 组**表现不如 FSB
- AC 结构上无法覆盖 f1xx (含 freq_rec)，影响约 28% 的 trace
- 如果未来扩展 AC 使其能探索 freq_rec，预期能进一步缩小 gap

---

## 附录：数据来源索引

| 数据 | 来源 |
|:---|:---|
| AC MR (alibaba, cloudphysics, metaCDN, metaKV, wiki) | `tmp/20260411-feature-ablation/ablation_autocompound.md` |
| AC MR (tencent, twitter) | `tmp/20260413-feature-ablation-ext/results/*.cachesim` |
| r1/r2 值 | `tmp/20260415-fsb-v2-broad/logs/*.log` WARMUP_DIAG |
| FSB 选择与 MR | `docs/20260414-FSB_V2_BROAD_EVALUATION.md` 附录表 |
| Oracle 基准 | 8 config 穷举 ablation (同上两来源) |
| 排除 trace | kv_202206（无 ext ablation 数据，共 42/43 有效） |
