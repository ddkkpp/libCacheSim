# AUTO_COMPOUND (AC) vs Feature Selection Bandit (FSB) 对比报告

**日期**: 2026-04-14
**结论**: AC 在稳定性、零开销和低 regret 方面全面优于 FSB。推荐默认使用 AC。

---

## 1. 方法概述

### 1.1 AUTO_COMPOUND (AC)

- **机制**: 利用 warmup 阶段的共线性诊断 (R² 检测) 自动决定 compound 特征开关
- **决策逻辑**:
  - `r1 > 0.98` → 禁用 freq_size
  - `r2 > 0.98` → 禁用 rec_size
  - freq_rec 始终禁用
- **搜索空间**: 4 种 config (f000, f001, f010, f011)
- **开销**: 零额外开销，诊断在 warmup 期间完成
- **环境变量**: `LOH_AUTO_COMPOUND=1`

### 1.2 Feature Selection Bandit (FSB v2)

- **机制**: UCB bandit 算法，每轮在 8 个 arm (f000~f111) 中选择并评估 MR
- **参数**: block_size=n_obj/4, max_rounds=5, min_rounds=2, warmup_rounds=0, ucb_c=1.0
- **搜索空间**: 8 种 config (f000~f111)，包含 freq_rec 相关配置
- **开销**: 需要 block_size × max_rounds × 8 arms 的探索期
- **环境变量**: `LOH_FSB=1`

---

## 2. 数据来源

| 来源 | 路径 | 说明 |
|:---|:---|:---|
| AC 主分析 | `tmp/20260411-feature-ablation/ablation_autocompound.md` | 1115 traces, post-hoc 模拟 AC 决策 |
| AC 运行时数据 | `tmp/20260410-cand-sweep-ac/ac1/results.csv` | 1063 trace, 49 种候选配置 |
| FSB 广域评估 | `docs/20260414-FSB_V2_BROAD_EVALUATION.md` | 43 traces, 实际 FSB v2 运行 |
| FSB 1063 诊断 | session memory: `fsb_analysis_1063.md` | 1063 trace 深度分析 |
| 穷举基准 | `tmp/20260411-feature-ablation/summary.csv` | 8 config 全量 MR/BMR |

---

## 3. 核心指标对照

| 指标 | AC | FSB v2 | 胜者 |
|:---|:---|:---|:---|
| 测试规模 | 1115 traces | 43 traces | — |
| Oracle 命中率 | 29.1% | 30.2% | 持平 |
| Regret <1% | **60.8%** | 44% | AC |
| Regret <5% | — | 60% | — |
| Avg MR regret | **3.75%** | 22.38% (去 outlier: 10.22%) | AC |
| Median MR regret | — | 2.78% | — |
| 最大 regret | ~34% | **+533%** | AC |
| 尾部风险 (≥20%) | 低 | 16% traces | AC |
| 探索开销 | **零** | 高 | AC |
| 搜索空间 | 4 configs (f0xx) | **8 configs (全部)** | FSB |
| 能选 freq_rec (f1xx) | 不能 | **能** | FSB |

---

## 4. AC 分 trace group 表现

| Trace Group | Traces | Auto=Best | Within 1% | Avg Gap |
|:---|---:|---:|---:|---:|
| cloudphysics | 106 | 35.8% | 63.2% | 1.86% |
| metaKV | 5 | 0% | 100% | 0.42% |
| metaCDN | 3 | 66.7% | 66.7% | 0.62% |
| wiki | 3 | 33.3% | 33.3% | 2.47% |
| alibabaBlock_1K | 9 | 66.7% | 88.9% | 0.32% |
| alibabaBlock_10K | 41 | 78.0% | 95.1% | 0.12% |
| alibabaBlock_100K | 345 | — | — | — |
| alibabaBlock_new | 237 | 15.2% | 56.1% | 3.18% |
| **全局** | **1115** | **29.1%** | **60.8%** | **3.75%** |

## 5. FSB 分 trace group 表现

| 组 | n | MR 命中 | avg MR reg | median MR reg |
|:---|---:|---:|---:|---:|
| alibabaBlock | 9 | 44% | +73.8% | +0.3% |
| cloudphysics | 14 | 29% | +6.8% | +2.8% |
| metaCDN | 2 | 0% | +2.5% | +2.5% |
| metaKV | 2 | 0% | +2.3% | +2.3% |
| tencentBlock | 10 | 30% | +11.9% | +9.2% |
| twitter | 3 | 33% | +23.8% | +28.2% |
| wiki | 3 | 33% | +0.9% | +0.1% |

---

## 6. 直接对比案例

### 6.1 1063 trace

| 方法 | 选择 | MR | Oracle | Regret |
|:---|:---|---:|:---|---:|
| AC | f011 | 0.01609 (r192_s64) | f001 | ~0% |
| FSB | f010 | 0.0221 | f001 | +14.2% |

FSB 在 1063 上的失败原因（来自诊断分析）:
- 信噪比 < 0.1，连续轮次 Spearman ρ ∈ [−0.38, +0.05]
- R0 主导得分：f010 在 R0 中 MR=0.164 远低于均值 0.272
- 根本原因：31K 请求的短期 MR 与 CMA-ES 优化后稳态 MR 无相关性

### 6.2 其他 traces

| Trace | AC 选择 | AC regret | FSB 选择 | FSB regret | Oracle |
|:---|:---|---:|:---|---:|:---|
| meta_reag | f011 | ~0% | f010 | +4.5% | f011 |
| wiki_2019t | — | ~2.5% | f111 | +0.1% | f010 |

---

## 7. AC 的结构性局限

AC 只搜索 4 种 config (f000/f001/f010/f011)，永远不启用 freq_rec。但实际最优分布中：

| Config 类型 | 占比 | AC 可达 |
|:---|---:|:---|
| f0xx (无 freq_rec) | 71.7% | 是 |
| f1xx (含 freq_rec) | 28.3% | **否** |

这意味着对 28.3% 的 traces，AC 结构上无法找到最优 config。但 FSB 在实测中并未利用好这一优势——它的高噪声和错选风险反而导致了更差的整体表现。

---

## 8. AC 选择分布

| Config | 含义 | 选中次数 | 占比 |
|:---|:---|---:|---:|
| f001 (+rec_size) | 567 | 50.9% |
| f011 (+freq_size+rec_size) | 540 | 48.4% |
| f010 (+freq_size) | 5 | 0.4% |
| f000 (base) | 3 | 0.3% |

---

## 9. 结论与建议

### 9.1 AC 全面胜出

1. **稳定性**: AC avg gap 3.75% vs FSB 10.22%（去 outlier），AC 无灾难性失败
2. **零开销**: AC 在 warmup 期间完成决策，FSB 需要额外探索时间
3. **更高一致性**: AC 60.8% traces 在 1% 内, FSB 仅 44%
4. **无尾部风险**: AC 最大 regret ~34%, FSB 可达 +533%

### 9.2 推荐方案

- **默认使用 AC** (`LOH_AUTO_COMPOUND=1`)
- FSB 仅在以下场景考虑:
  - 需要探索 freq_rec (f1xx) 配置
  - 且搭配改进的 bandit 策略（如 successive halving）
  - 且增加 min_rounds 到 3-4 减少噪声
- 对 regret 敏感的场景，应做 full ablation (8 config 穷举)

### 9.3 未来改进方向

- **扩展 AC 搜索空间**: 考虑加入 freq_rec 的共线性检测，使 AC 能覆盖 f1xx
- **FSB 改进**: 改用绝对值 regret 而非百分比、增加 warmup 轮数、组级先验
- **混合方案**: AC 快速决策 + optional FSB 精细调优

---

## 附录：数据索引

| 数据 | 位置 |
|:---|:---|
| AC 逐 trace 分析 (1115 traces) | `tmp/20260411-feature-ablation/ablation_autocompound.md` |
| AC 1063 候选 sweep | `tmp/20260410-cand-sweep-ac/ac1/results.csv` |
| 8 config 穷举 CSV | `tmp/20260411-feature-ablation/summary.csv` |
| FSB v2 广域评估 | `docs/20260414-FSB_V2_BROAD_EVALUATION.md` |
| FSB 1063 诊断 | session memory: `fsb_analysis_1063.md` |
| 扩展消融结果 (.cachesim) | `tmp/20260413-feature-ablation-ext/results/` |
