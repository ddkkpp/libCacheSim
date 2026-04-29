# twitter vs metaKV 统计指标对比分析

**日期**: 2026-04-20
**目的**: 分析 twitter 和 metaKV 两组 KV 型 trace 的统计特征差异，解释为何 LOH 在这两组 BMR 表现不佳
**数据来源**: `docs/20260415-ablation-per-group/cmaes版本LOH/` 各组 ablation 文档

---

## 1. 八组统计指标汇总

### 1.1 基础特征分布指标（中位数）

| group | N | cv_sz | cv_freq | cv_rec | avg_sz | n_obj (med) | one_hit |
|---|---:|---:|---:|---:|---:|---:|---:|
| alibabaBlock | 998 | 0.108 | 0.488 | 0.120 | 19,228 | 13,651 | — |
| cloudphysics | 106 | 0.133 | 0.428 | 0.095 | 22,741 | 149,714 | — |
| metaCDN | 3 | 0.209 | 0.477 | 0.073 | 15,945,708 | 3,993,192 | — |
| **metaKV** | **5** | **0.472** | **0.698** | **0.076** | **896** | **7,124,815** | — |
| tencentBlock | 4755 | 0.108 | 0.590 | 0.115 | 15,350 | 20,302 | — |
| tencentPhoto | 2 | 0.092 | 0.608 | 0.069 | 22,934 | 56,728,528 | — |
| **twitter** | **11** | **0.349** | **0.473** | **0.095** | **370** | **389,885** | 0.615 |
| wiki | 3 | 0.153 | 0.680 | 0.089 | 94,302 | 5,083,064 | — |

### 1.2 特征相关性指标（中位数）

| group | r1(freq,fs) | r2(rec,rs) | r3(freq,fr) | r4(sz,fs) | r5(sz,rs) | r6(rec,fr) |
|---|---:|---:|---:|---:|---:|---:|
| alibabaBlock | 0.983 | 0.731 | 0.876 | −0.14 | 0.88 | −0.56 |
| cloudphysics | 0.961 | 0.578 | 0.927 | −0.26 | 0.92 | −0.55 |
| metaCDN | 0.780 | 0.333 | 0.960 | −0.18 | 0.91 | −0.53 |
| **metaKV** | **0.846** | **0.149** | **0.970** | **−0.36** | **0.98** | **−0.53** |
| tencentBlock | 0.982 | 0.726 | 0.884 | −0.14 | 0.87 | −0.54 |
| tencentPhoto | 0.985 | 0.581 | 0.983 | −0.11 | 0.94 | −0.47 |
| **twitter** | **0.783** | **0.217** | **0.928** | **−0.59** | **0.97** | **−0.58** |
| wiki | 0.962 | 0.551 | 0.972 | −0.20 | 0.97 | −0.44 |

### 1.3 多元回归 R² 与交叉相关（中位数）

| group | R²m_fs | R²m_rs | R²m_fr | r(freq,sz) | r(rec,sz) | r(freq,rec) |
|---|---:|---:|---:|---:|---:|---:|
| alibabaBlock | 0.987 | 0.993 | 0.869 | 0.07 | −0.03 | −0.37 |
| cloudphysics | 0.969 | 0.994 | 0.934 | 0.05 | −0.02 | −0.38 |
| metaCDN | 0.893 | 0.998 | 0.965 | 0.01 | −0.01 | −0.09 |
| **metaKV** | **0.859** | **0.994** | **0.961** | **0.03** | **−0.02** | **−0.43** |
| tencentBlock | 0.987 | 0.993 | 0.873 | 0.07 | −0.03 | −0.37 |
| tencentPhoto | 0.990 | 0.994 | 0.966 | 0.03 | −0.03 | −0.29 |
| **twitter** | **0.930** | **0.991** | **0.905** | **−0.10** | **−0.03** | **−0.35** |
| wiki | 0.975 | 0.994 | 0.972 | 0.03 | −0.02 | −0.43 |

### 1.4 LOH 排名（在 14 算法中）

| group | MR rank | BMR rank | BMR-wt rank | MR-wt rank |
|---|---:|---:|---:|---:|
| alibabaBlock | 1 | **1** | 1 | 1 |
| cloudphysics | 1 | 6 | 6 | 2 |
| metaCDN | 1 | **1** | 1 | 1 |
| **metaKV** | **1** | **9** | **8** | **2** |
| tencentBlock | 1 | **1** | 1 | 1 |
| tencentPhoto | 1 | 7 | 7 | 1 |
| **twitter** | **1** | **7** | **6** | **1** |
| wiki | 1 | 4 | 4 | 1 |

---

## 2. twitter vs metaKV 详细对比

| 指标 | twitter (med) | metaKV (med) | Δ | 解读 |
|---|---:|---:|---:|---|
| **cv_sz** | 0.349 | 0.472 | −0.123 | metaKV 对象大小变异更大 |
| **cv_freq** | 0.473 | 0.698 | **−0.225** | metaKV 频率变异显著更大 |
| cv_rec | 0.095 | 0.076 | +0.019 | 两组近似，recency 分布都高度集中 |
| avg_sz | 370 B | 896 B | −526 | 两组都是超小对象（<1KB） |
| n_obj (med) | 389,885 | 7,124,815 | −6.7M | metaKV 唯一对象多一个量级 |
| one_hit (med) | 0.615 | — | — | twitter 有 one_hit 统计；metaKV 未记录 |
| r1(freq,fs) | 0.783 | 0.846 | −0.063 | 两组 freq×size 相关都高 |
| **r2(rec,rs)** | **0.217** | **0.149** | **+0.068** | **两组 recency 都极弱** |
| r3(freq,fr) | 0.928 | 0.970 | −0.042 | 两组 freq×rec 相关都很高 |
| R²m_fs | 0.930 | 0.859 | +0.071 | twitter 的 freq/size 模型解释力更强 |
| R²m_rs | 0.991 | 0.994 | −0.003 | 两组 rec/size 模型都近乎完美 |
| R²m_fr | 0.905 | 0.961 | −0.056 | metaKV 的 freq/rec 模型解释力更强 |

---

## 3. 关键发现

### 3.1 twitter 和 metaKV 的最大共同点

1. **r2(rec,rs) 都极低**（0.15~0.22）：recency 特征在这两组中几乎无用。这是 8 组中唯二 r2 < 0.25 的组。
2. **cv_rec 都极低**（<0.1）：recency 分布高度集中，区分度差。
3. **avg_sz 都极小**（<1KB）：小对象为主的 KV 工作负载。
4. **LOH 的 MR 排名都是第 1**，但 **BMR 排名都很差**（7 和 9）。

> **结论**：两组的核心共同特征是 **recency 无关性** — 这正是当前 compound 公式以 recency 为基础特征的致命弱点。

### 3.2 twitter 和 metaKV 的最大差异

| 差异指标 | twitter | metaKV | 影响 |
|---|---|---|---|
| **cv_freq** | 0.473（中等） | 0.698（高） | metaKV 频率特征区分度更强，理论上更有利于频率导向的评分 |
| **cv_sz** | 0.349（中等） | 0.472（高） | metaKV 对象大小变异更大 → BMR 对 size 更敏感 |
| **n_obj** | ~390K | ~7.1M | metaKV 对象空间大一个量级 → ghost cache 覆盖率更低 |

> cv_freq 和 cv_sz 的差异**不足以解释 BMR 排名差异**（twitter BMR=7, metaKV BMR=9），因为两组 BMR 都差。

### 3.3 与 BMR 好的组的对比

| 指标 | BMR-好组 (alibabaBlock/tencentBlock) | BMR-差的KV组 (twitter/metaKV) |
|---|---|---|
| r2(rec,rs) | **0.73** | **0.15~0.22** |
| cv_rec | 0.115~0.120 | 0.076~0.095 |
| cv_sz | 0.108 | 0.349~0.472 |
| avg_sz | 15~19 KB | < 1 KB |

**最显著差异是 r2(rec,rs)**：BMR 好的组 recency 与 rec/size 复合特征高度相关（r2≈0.73），而 BMR 差的两组 recency 几乎无信息（r2≈0.15~0.22）。

### 3.4 为什么 cv_sz 不是充分解释

之前认为"cv_sz 高导致 BMR 差"。但：
- tencentPhoto cv_sz=0.092（最低），BMR rank=7（差） → **反例**
- alibabaBlock/tencentBlock cv_sz=0.108，BMR rank=1（好）
- tencentPhoto 和 twitter/metaKV 的真正共同点：**r2(rec,rs) 偏低**（tencentPhoto r2=0.58，比 BMR-好组的 0.73 低）

---

## 4. 总结：twitter 和 metaKV 不只是 cv_size 不同

**cv_sz 是两组最大的数值差异**（0.349 vs 0.472），但这不是导致 BMR 差的根本原因。

**根本原因是 recency 无关性**（r2 < 0.25），这是两组的最大共同特征：
- 当前 compound 公式的 6 个特征中有 3 个直接依赖 recency：`rec`、`freq/rec`、`rec*size`
- 在 recency 无信息的 workload 上，这 3 个特征退化为噪声
- CMA-ES 只能优化权重，无法补救特征本身的信息不足

**LOH_COMPOUND_USE_IRT1 的设计逻辑**：用 irt1 替代 rec，因为：
- irt1 对 one-hit wonder 有天然区分度（128e6 vs 正常访问间隔）
- irt1 与 recency 在 r2 高的组行为相似（都反映对象的"活跃度"），但在 recency 低的组提供额外信息
- 目标：在不损害 BMR-好组的前提下，改善 BMR-差的 KV 类组

---

## 5. 实验跟踪

- **实验目录**: `tmp/20260420-irt1-compound/`
- **运行脚本**: `tmp/20260420-irt1-compound/run.sh`
- **配置**: LOH_COMPOUND_USE_IRT1=1, autocompound=1, r256_s16, log1p, ratio=0.1
- **Traces**: twitter (11 clusters) + metaKV (4 traces) = 15 并行
- **状态**: 运行中
