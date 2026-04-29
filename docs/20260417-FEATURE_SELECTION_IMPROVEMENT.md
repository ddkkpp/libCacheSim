# 特征选择策略改进分析

> 日期: 20260417
> 数据量: 5883 traces (全量新格式 DIAG / 8-config 穷举结果)
> 目标: 找到比 AC v5 更好的特征选择方法

## 1. 背景

LOH 缓存算法使用 3 个 compound 特征（交互项）来增强打分：

| bit | compound 特征 | Pearson 诊断指标 | Multi-R² 诊断指标 |
|-----|--------------|-----------------|-------------------|
| FR  | freq × rec   | r3 = Pearson(freq, freq×rec) | R2m_fr = R²(freq_rec ~ freq+rec) |
| FS  | freq × size  | r1 = Pearson(freq, freq×size) | R2m_fs = R²(freq_size ~ freq+size) |
| RS  | rec × size   | r2 = Pearson(rec, rec×size)   | R2m_rs = R²(rec_size ~ rec+size) |

**AC v5 策略**：FR=1（固定开启），FS = (r1 ≤ 0.98)，RS = (r2 ≤ 0.98)
含义：r1/r2 > 0.98 表示 compound ≈ 基本特征（冗余），关闭之。FR 恒开。

## 2. 核心发现

### 2.1 Oracle config 分布（MR 目标）

| config | oracle 数量 | 比例 |
|--------|-----------|------|
| f000 | 1013 | 17.2% |
| f001 | 1457 | **24.8%** |
| f010 | 921 | 15.7% |
| f011 | 1208 | 20.5% |
| f100 | 284 | 4.8% |
| f101 | 436 | 7.4% |
| f110 | 276 | 4.7% |
| f111 | 288 | 4.9% |

**关键洞察：FR=0（f0xx）占 oracle 的 78.2%，FR=1（f1xx）仅 21.8%。**
这意味着 AC v5 固定 FR=1 的决策在绝大多数 traces 上是错的。

### 2.2 Per-group FR oracle 分布

| group | n | FR=0 oracle | FR=1 oracle |
|-------|---|------------|------------|
| alibabaBlock | 998 | 721 (72%) | 277 (28%) |
| cloudphysics | 106 | 69 (65%) | 37 (35%) |
| metaCDN | 3 | 2 (67%) | 1 (33%) |
| metaKV | 5 | 5 (100%) | 0 (0%) |
| tencentBlock | 4755 | 3789 (80%) | 966 (20%) |
| tencentPhoto | 2 | 2 (100%) | 0 (0%) |
| twitter | 11 | 9 (82%) | 2 (18%) |
| wiki | 3 | 2 (67%) | 1 (33%) |

所有 8 组 FR=0 的 oracle 占比都在 65%-100%，没有任何组应该默认开启 FR=1。

### 2.3 FR 切换的 MR vs BMR 影响

对比 AC v5（FR=1）和 AC v6（FR=0），在相同 FS/RS gating 下：

| 指标 | FR=0 更好的比例 |
|------|---------------|
| MR | 67.0% (3864/5770) |
| BMR | 42.3% (2441/5770) |
| MR 和 BMR 都更好 | 40.1% (2312/5770) |
| MR 更好但 BMR 更差 | 26.9% (1550/5770) |

FR=0 在 MR 上优势明显（67%），但在 BMR 上只有 42% 更好。存在 27% 的 traces 是 MR-BMR tradeoff（MR 得分但 BMR 失分）。

## 3. 策略对比

### 3.1 全局评估

| 策略 | MR mean% | BMR mean% | wMR gap% | wBMR gap% | macro_MR% | macro_BMR% | 说明 |
|------|---------|----------|---------|----------|-----------|-----------|------|
| **AC v6 (FR=0)** | **4.28** | 15.39 | 5.76 | 13.95 | 6.26 | 19.95 | MR 最优 |
| AC v6.1 (FR=0, thr 0.96) | 4.91 | 16.68 | **4.17** | 12.64 | 6.66 | 20.05 | wMR 最优 |
| static_f001 | 5.58 | 17.71 | 5.05 | 11.55 | **4.66** | 14.69 | macro_MR 最优 |
| R2m_fr>0.9 + r1/r2>0.98 | 6.32 | 8.81 | 6.12 | 11.53 | 6.13 | 15.27 | **MR/BMR 平衡** |
| R2m_fr>0.92 + r1/r2>0.96 | 6.95 | 7.32 | 5.12 | 9.81 | 6.76 | 14.32 | **综合 MR+BMR 优秀** |
| R2m_fr>0.94 + r1/r2>0.96 | 7.41 | 6.17 | 6.07 | 9.92 | 6.94 | 13.91 | **MR+BMR sum 最小 (13.58)** |
| AC v5 (FR=1) | 7.76 | **6.59** | 8.28 | **7.02** | 5.65 | **7.43** | BMR 最优 |

说明：
- MR mean%：相对于 per-trace MR oracle 的平均 regret（全局所有 traces 简单平均）
- BMR mean%：相对于 per-trace BMR oracle 的平均 regret（全局所有 traces 简单平均）
- wMR gap%：按请求数加权的 MR relative gap = (wMR_sel - wMR_oracle) / wMR_oracle × 100
- wBMR gap%：按请求数加权的 BMR relative gap
- macro_MR%：8 组各自 MR mean% 后取 8 组均值（消除组大小差异的影响）
- macro_BMR%：8 组各自 BMR mean% 后取 8 组均值

### 3.2 Per-group 评估

每组列出核心策略的 MR mean% 和 BMR mean%（相对 per-trace oracle 的平均 regret）。

#### tencentBlock (n=4755, 占总量 82%)

| 策略 | MR mean% | BMR mean% |
|------|---------|----------|
| AC v5 (FR=1) | 8.27 | 6.84 |
| **AC v6 (FR=0)** | **4.33** | 16.81 |
| R2m_fr>0.9 + r1/r2>0.98 | 6.54 | 9.14 |
| R2m_fr>0.92 + r1/r2>0.96 | 7.37 | 7.56 |
| R2m_fr>0.94 + r1/r2>0.96 | 7.90 | **6.18** |

#### alibabaBlock (n=998)

| 策略 | MR mean% | BMR mean% |
|------|---------|----------|
| AC v5 (FR=1) | 5.70 | **5.44** |
| AC v6 (FR=0) | 3.98 | 8.66 |
| static_f001 | **3.61** | 7.29 |
| R2m_fr>0.9 + r1/r2>0.98 | 5.50 | 6.91 |
| R2m_fr>0.94 + r1/r2>0.96 | 5.37 | 5.54 |

#### cloudphysics (n=106)

| 策略 | MR mean% | BMR mean% |
|------|---------|----------|
| AC v5 (FR=1) | 3.54 | **4.43** |
| AC v6 (FR=0) | 1.86 | 9.03 |
| R2m_fr>0.9 + r1/r2>0.98 | **1.82** | 7.02 |
| R2m_fr>0.94 + r1/r2>0.96 | 3.10 | 6.75 |

#### metaCDN (n=3)

| 策略 | MR mean% | BMR mean% |
|------|---------|----------|
| AC v5 (FR=1) | **0.27** | **0.05** |
| AC v6 (FR=0) | 0.62 | 0.30 |
| R2m_fr>0.9 + r1/r2>0.98 | 0.62 | 0.30 |
| R2m_fr>0.94 + r1/r2>0.96 | 0.74 | 0.25 |

#### metaKV (n=5)

| 策略 | MR mean% | BMR mean% |
|------|---------|----------|
| AC v5 (FR=1) | 1.40 | 8.66 |
| AC v6 (FR=0) | **0.42** | 22.08 |
| R2m_fr>0.9 + r1/r2>0.98 | **0.42** | 22.08 |
| R2m_fr>0.94 + r1/r2>0.96 | 1.35 | **17.64** |

#### tencentPhoto (n=2)

| 策略 | MR mean% | BMR mean% |
|------|---------|----------|
| AC v5 (FR=1) | **0.26** | **2.04** |
| AC v6 (FR=0) | 0.57 | 8.59 |
| R2m_fr>0.9 + r1/r2>0.98 | 0.57 | 8.59 |
| R2m_fr>0.94 + r1/r2>0.96 | 0.57 | 8.59 |

#### twitter (n=11)

| 策略 | MR mean% | BMR mean% |
|------|---------|----------|
| AC v5 (FR=1) | 23.79 | 24.31 |
| AC v6 (FR=0) | 35.81 | 74.86 |
| static_f001 | **12.75** | **26.63** |
| R2m_fr>0.9 + r1/r2>0.98 | 31.06 | 48.90 |
| R2m_fr>0.94 + r1/r2>0.96 | 33.34 | 43.30 |

twitter 是 AC v6 表现最差的组（MR 和 BMR 都大幅恶化），static_f001 反而最优。

#### wiki (n=3)

| 策略 | MR mean% | BMR mean% |
|------|---------|----------|
| AC v5 (FR=1) | **2.00** | **7.65** |
| AC v6 (FR=0) | 2.47 | 19.23 |
| R2m_fr>0.9 + r1/r2>0.98 | 2.47 | 19.23 |
| R2m_fr>0.94 + r1/r2>0.96 | 3.17 | 23.04 |

## 4. 推荐策略

### 方案 A: AC v6（仅改 FR 默认值）— MR 优先

```
FR = 0          // 修改: 从 1 → 0
FS = (r1 ≤ 0.98) ? 1 : 0     // 不变
RS = (r2 ≤ 0.98) ? 1 : 0     // 不变
```

- **MR regret: 4.28%** (vs AC v5 的 7.76%，改善 45%)
- BMR regret: 15.39% (vs AC v5 的 6.59%，恶化 134%)
- 改动量: 仅改一行代码（FR 默认值）
- 适用场景: MR 是主要优化目标

### 方案 B: R2m_fr-gated FR — MR/BMR 平衡

```
FR = (R2m_fr > 0.90) ? 0 : 1     // 新增: R2m_fr 门控
FS = (r1 > 0.98) ? 0 : 1         // 不变 (注意 r1, r2 的 gating 方向)
RS = (r2 > 0.98) ? 0 : 1         // 不变
```

含义: R2m_fr = MultiR²(freq_rec ~ freq + rec)。当 freq×rec 可被 freq 和 rec 的线性组合解释 90% 以上时，compound 冗余，关闭 FR。

- MR regret: 6.32% (vs AC v5 的 7.76%，改善 19%)
- BMR regret: 8.81% (vs AC v5 的 6.59%，恶化 34%)
- 改动量: 增加 R2m_fr 的计算和 gating 逻辑
- 适用场景: 需要 MR 和 BMR 兼顾

### 方案 C: R2m_fr>0.94 + 降低 r1/r2 阈值 — 最佳 Pareto

```
FR = (R2m_fr > 0.94) ? 0 : 1     // R2m_fr 门控，阈值 0.94
FS = (r1 > 0.96) ? 0 : 1         // 修改: 阈值从 0.98 降到 0.96
RS = (r2 > 0.96) ? 0 : 1         // 修改: 阈值从 0.98 降到 0.96
```

- MR regret: 7.41% (与 AC v5 接近)
- BMR regret: 6.17% (比 AC v5 好 6%)
- MR+BMR sum: 13.58% (**所有策略中最低**)
- 改动量: 增加 R2m_fr gating + 调整阈值
- 适用场景: 追求 MR/BMR 综合最优

## 5. DIAG 指标与 FR 选择的相关性

| 指标 | 与 "FR=1 useful fraction" 的相关系数 |
|------|-------------------------------------|
| cv_sz | -0.1714 (最显著: size 变异大 → FR=0 好) |
| r2 | +0.1388 |
| r_AC | +0.1278 |
| r4 | +0.1192 |
| R2m_fs | +0.1160 |
| r1 | +0.1065 |

所有相关系数都很弱（< 0.2），意味着**没有单一 DIAG 指标能准确预测 FR 的最优选择**。
这解释了为什么简单阈值策略（如 r3 gating）的改进有限。

## 6. 结论

1. **AC v5 的最大问题是 FR=1 固定开启**，这在 78% 的 traces 上是错的
2. **最简改进**是将 FR 默认值从 1 改为 0（方案 A），MR 改善 45%
3. **最佳平衡**是用 R2m_fr 指标门控 FR（方案 B/C），兼顾 MR 和 BMR
4. DIAG 指标与 FR 最优选择的相关性较弱，限制了条件策略的上限
5. AC v5 的 FS/RS gating 逻辑（r1/r2 > 0.98）基本合理，但阈值可微调至 0.96

### 大 regret 分析

| 策略 | regret > 10% 的 traces 数 |
|------|-------------------------|
| AC v5 (FR=1) | **1397** |
| AC v6 (FR=0) | 690 |

AC v6 将严重 regret 的 traces 数减少了 51%。

## 附录: 分析脚本

- `tmp/feature_selection_analysis.py` — 初始策略扫描
- `tmp/feature_selection_deep.py` — FR bit 深入分析 + 策略搜索
- `tmp/feature_selection_final.py` — 最终策略设计与评估
- `tmp/feature_selection_pareto2.py` — MR/BMR 双目标 Pareto 分析
- `tmp/feature_selection_analysis.txt` — 初始扫描结果
- `tmp/feature_selection_deep_analysis.txt` — 深入分析结果
- `tmp/feature_selection_final.txt` — 最终评估结果
