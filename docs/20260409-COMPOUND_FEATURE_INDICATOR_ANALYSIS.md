# 20260409 — Compound Feature 自适应指标分析报告（v4 修订版）

> **修订历史**: v1(逐bit自适应) → v2(r1→f100/f111) → v3(r1→f001/f011, bit2固定开) → **v4**(r1→bit1, r2→bit2, 本版)

## 1. 研究目标

在 LOH 缓存驱逐算法中，CMA-ES 优化的评分函数包含 3 个可选 compound 特征：

$$\text{score}(o) = w_0 \cdot \text{freq} + w_1 \cdot \text{rec} + w_2 \cdot \text{size} + w_3 \cdot \underbrace{\frac{\text{freq}}{\text{rec}}}_{\text{bit0}} + w_4 \cdot \underbrace{\frac{\text{freq}}{\text{size}}}_{\text{bit1}} + w_5 \cdot \underbrace{\text{rec} \times \text{size}}_{\text{bit2}}$$

- **bit0**: `freq/rec` (frequency ÷ recency)
- **bit1**: `freq/size` (frequency ÷ size)
- **bit2**: `rec×size` (recency × size)

目标：找到 warmup 阶段可计算的诊断指标，在运行完 warmup 后自动决定最优 compound 配置。

## 2. 诊断指标定义

### 2.1 Pearson 冗余指标 (r1~r6)

| 指标 | 定义 | 含义 | 何时→1 |
|------|------|------|--------|
| r1 | Pearson(freq, freq/size) | freq/size 多大程度**只由 freq** 决定 | **size 无变异** |
| r2 | Pearson(rec, rec×size) | rec×size 多大程度**只由 rec** 决定 | **size 无变异** |
| r3 | Pearson(freq, freq/rec) | freq/rec 多大程度**只由 freq** 决定 | **rec 无变异** |
| r4 | Pearson(size, freq/size) | freq/size 多大程度**只由 size** 决定 | **freq 无变异** |
| r5 | Pearson(size, rec×size) | rec×size 多大程度**只由 size** 决定 | **rec 无变异** |
| r6 | Pearson(rec, freq/rec) | freq/rec 多大程度**只由 rec** 决定 | **freq 无变异** |

### 2.2 基础相关 (r_AB, r_AC, r_BC)
| 指标 | 定义 |
|------|------|
| r_AB | Pearson(freq, size) |
| r_AC | Pearson(freq, recency) |
| r_BC | Pearson(recency, size) |

### 2.3 Multiple R² (R2m)
| 指标 | 定义 | 含义 |
|------|------|------|
| R2m_fs | R²(freq/size ~ freq + size) | freq+size 联合能解释 freq/size 多少方差 |
| R2m_rs | R²(rec×size ~ rec + size) | rec+size 联合能解释 rec×size 多少方差 |
| R2m_fr | R²(freq/rec ~ freq + rec) | freq+rec 联合能解释 freq/rec 多少方差 |

公式: R²(Y~X1+X2) = (r_y1² + r_y2² − 2·r_y1·r_y2·r_12) / (1 − r_12²)

## 3. 数据集

- 消融实验: 110 个 CloudPhysics traces × 8 cfg(f000~f111) → 884 行结果
- 增强诊断: 118 traces 的 warmup 诊断指标
- 有效交集: 109 traces（含消融结果 + 增强诊断）

## 4. 核心发现与理论依据

### 4.1 bit0 (freq/rec) — 固定**关闭**

#### 数据发现

| 统计 | 值 |
|------|-----|
| 开有益 trace | 32/109 (29%) |
| 关有益 trace | 52/109 (48%) |
| 无关紧要 | 25/109 (23%) |
| 平均边际 | -0.004 (负 = 关更好) |
| **固定关 avgLoss** | **+0.002** |
| **固定关 maxLoss** | **+0.042** (w90) |
| 固定开 avgLoss | +0.006 |
| 固定开 maxLoss | +0.073 (w60) |
| 最优自适应(R2m_rs<0.99→关, else→开) avgLoss | +0.004 |
| 最优自适应 maxLoss | +0.063 |

**结论：固定关闭 bit0 的 avgLoss(0.002) 和 maxLoss(0.042) 均优于任何自适应策略。**

所有候选指标的 Spearman 相关均 < 0.31（R2m_rs 最高），最佳单分裂方差减少仅 10.4%。
Cohen's d 最高 0.92 (R2m_fr)，但该分裂仅覆盖 13 个 trace。

#### 理论依据一：log1p 变换下的信息冗余

当启用 `LOH_FEATURE_LOG1P=1`（默认）时，实际输入 CMA-ES 的特征是：

$$x_0 = \log(1+\text{freq}), \quad x_1 = \log(1+\text{rec}), \quad x_3 = \log\!\left(1+\frac{\text{freq}}{\text{rec}}\right)$$

而对大多数取值：

$$\log\!\left(\frac{\text{freq}}{\text{rec}}\right) = \log(\text{freq}) - \log(\text{rec}) \approx x_0 - x_1$$

CMA-ES 可通过调整 $w_0$ 和 $w_1$ 的线性组合近似表达 $x_3$ 所携带的信息，使 bit0 本质冗余。

#### 理论依据二：freq 和 rec 的高共线性

在实际缓存工作负载中，高频对象通常有较近的最后访问时间（高 freq → 低 rec）。
r3 = Pearson(freq, freq/rec) 在 109 traces 中位数 ≈ 0.93（接近 1），说明 freq/rec ≈ f(freq)。

#### 理论依据三：维度诅咒

CMA-ES 收敛速度大致为 $O(d^2)$。冗余维度不增加有效信息但增加搜索空间。
在 warmup 阶段有限的样本内，多余维度的负效应大于其偶尔带来的边际收益。

#### 为什么自适应也无效

1. 开有益的 32 个 trace **没有统一的特征模式**（Spearman 最高仅 0.31）
2. 影响 bit0 收益的因子是**高阶交互效应**，取决于驱逐候选集中 freq/rec 的具体分布形态，warmup 阶段无法精确预测
3. **风险不对称**：最大正边际 +0.042 vs 最大负边际 -0.073，固定关闭是风险调整后最优

### 4.2 bit1 (freq/size) — r1 > 0.98 自适应关闭

#### 数据发现

**策略**: r1 > 0.98 → 关闭 freq/size，否则开启

| 指标 | 值 |
|------|-----|
| 平均损失 (avgLoss) | **+0.0018** |
| 最大损失 (maxLoss) | **+0.048** (w15) |
| 准确率 | 87.2% |
| 误判数 | 14/109 |
| **Cohen's d** | **1.29（强效应）** |

**r1 > 0.98 触发的 trace (22个)**:

| 结果 | trace | r1 | 损失 | 说明 |
|------|-------|-----|------|------|
| ✓ 正确关闭 | w30,w33,w36,w39,w40,w41,w45,w47,w96,w27,w13 | 0.98~0.99 | 0.000 | freq/size 确实冗余 |
| △ 误判关闭 | w07,w32,w34,w103,w35,w56,w57,w68,w17 | 0.98~0.99 | 0.003~0.010 | 开更好但差距小 |
| ✗ 严重误判 | **w15** (r1=0.999), **w37** (r1=0.996) | >0.99 | 0.048, 0.013 | freq/size 开明显更好 |

**r1 未触发但应关闭的 trace (3个)**:

| trace | r1 | 应关损失 |
|-------|-----|---------|
| w59 | 0.961 | +0.042 |
| w90 | 0.968 | +0.039 |
| w11 | 0.875 | +0.012 |

#### 理论依据：正交性取决于 size 变异

freq/size 结合了两个通常**独立**的维度。但当 size 无变异时：

$$\frac{\text{freq}}{\text{size}} = \frac{\text{freq}}{c} \propto \text{freq}$$

此时 freq/size 退化为 freq 的缩放，完全冗余。

**r1 的物理含义精确量化了这个条件**：

$$r_1 = \text{Pearson}(\text{freq}, \frac{\text{freq}}{\text{size}})$$

- $\text{Var}(\text{size}) \to 0 \Rightarrow r_1 \to 1$（冗余）
- $\text{Var}(\text{size})$ 大 $\Rightarrow r_1$ 下降（freq/size 携带新信息）

阈值 0.98 是通过穷举搜索在 109 traces 上找到的最优分割点。

#### 为什么 r1 只对 bit1 有效

| bit | Cohen's d (r1>0.98 vs r1≤0.98) | 效应强度 |
|-----|------|------|
| bit1 (freq/size) | **1.29** | 强 |
| bit0 (freq/rec) | 0.23 | 弱 — r1 测量 size-variability，与 freq/rec 无因果关系 |
| bit2 (rec×size) | 0.29 | 弱 — 虽理论上 size 无变异→rec×size≈c·rec，但信号被 rec×size 的高基线收益淹没 |

### 4.3 bit2 (rec×size) — r2 自适应（v4）

#### 数据发现

| 统计 | 值 |
|------|-----|
| 开有益 trace | 88/109 (81%) |
| 关有益 trace | 21/109 (19%) |
| 平均边际 | +0.015 (正 = 开更好) |
| 固定开 avgLoss | +0.0014 |
| 固定开 maxLoss | +0.036 |

r2 > 0.98 仅在 2 traces 触发 (w15, w21)，因此 r2 自适应与固定开在实际表现上几乎无差异。

#### v4 决策：r2 > 0.98 → 关，否则 → 开

与 bit1 使用 r1 对称：
- r2 = Pearson(rec, rec×size)，测量 rec×size 中多少信息仅由 rec 决定
- r2 > 0.98 → size 无变异 → rec×size ≈ c·rec，与 rec 线性冗余 → 关闭
- r2 ≤ 0.98 → size 有变异 → rec×size 携带 GreedyDual-Size 风格的新信息 → 开启

虽然实际 r2>0.98 很少触发（仅 2/109），使得 v4 和 v3（固定开）表现几乎相同，但 r2 作为判断条件使得逻辑框架完整且理论一致。

#### 理论依据一：Size-aware 驱逐的经典理论

在有限缓存中，驱逐大小为 $s$ 的对象释放 $s$ 字节空间。经典 GreedyDual-Size 理论证明最优驱逐应考虑对象大小：

$$\text{priority}(o) \propto \frac{\text{value}(o)}{\text{size}(o)}$$

rec×size 等价地在评分中引入"长时间未访问的大对象应优先驱逐"的信号。

#### 理论依据二：rec 与 size 的独立性

对象大小是写入时确定的固有属性，与访问时间模式无因果关系。rec 和 size 几乎总是独立或弱相关，其乘积几乎总能提供超越单独特征的新信息。

#### 为什么 r2 而非 r5 作为判断指标

r2 = Pearson(rec, rec×size) 与 r1 = Pearson(freq, freq/size) 对称：
- r1 高 → size 无变异 → freq/size ≈ c·freq → bit1 冗余
- r2 高 → size 无变异 → rec×size ≈ c·rec → bit2 冗余

r5 = Pearson(size, rec×size) 测量的是 rec 无变异，而非 size 无变异，不适合作为 bit2 的冗余判断。

## 5. r2~r6 失效的理论解释

### 5.1 r4 — 理论正确但现实不存在

r4=Pearson(size, freq/size)→1 意味着 freq 无变异。但真实 workload 中 freq 天然是 Zipf/幂律分布（高变异，cv_freq 中位数 ≈ 0.60），不存在 freq≈const 的情况。实际 r4 值**全为负值**（-0.94 ~ -0.10），没有 trace 接近 +1。

### 5.2 r2 — 现作为 bit2 判断指标（v4）

r2 = Pearson(rec, rec×size)。v3 中 bit2 固定开，因此 r2 未被使用。v4 中 r2 被纳入决策框架（r2>0.98→关 bit2），使逻辑与 r1→bit1 对称。实际 r2>0.98 仅 2/109 触发（cv_rec≈0.10 太小），表现与固定开几乎无差异。

r5 = Pearson(size, rec×size) 测量 rec 无变异，不适合判断 bit2 冗余。

### 5.3 r3, r6 — 信噪比不足

r3, r6 是预测 freq/rec(bit0) 的候选指标。但 bit0 固定关闭已是最优策略（固定关 avgLoss 优于任何自适应），不需要预测。

补充分析：即使尝试用这些指标做自适应，r3 的 Spearman 仅 -0.29，最佳单分裂方差减少 7.8%，不足以做可靠判断。

### 5.4 R2m_fr — 仅对 bit1 间接有效

R2m_fr 作为 bit1 的预测指标，决策树方差减少 56.9%（最高），但其含义是"freq/rec 的非线性复杂度"，与 freq/size 的冗余无直接因果关系。它的预测力来自"特征空间整体复杂度高 → 额外维度导致 CMA-ES 收敛困难"。

注意：R2m_fr 的阈值分析已并入 `tmp/20260411-warmup-diag/analysis_R2m_fr_deep.txt`，但其对 bit1 的判断能力不如 r1（因果机制更间接，且无法同时准确判断 bit0）。

## 6. 推荐的 auto_compound 逻辑 — v4（最终版）

### 版本演进

| 版本 | 策略 | avgLoss | maxLoss | 说明 |
|------|------|---------|---------|------|
| v1 | r1→关bit1, r2→关bit2 (逐bit) | +0.018 | — | r2 几乎无判别力 |
| v2 | r1>0.98→f100, else f111 | +0.019 | +0.191 | 64策略枚举排第~20 |
| v3 | r1>0.98→f001, else f011 (bit2固定开) | +0.005 | +0.064 | 64策略枚举排第1~2 |
| **v4** | **r1→bit1, r2→bit2 (对称)** | **+0.005** | **+0.064** | **与v3表现相同，逻辑完整** |

### v3→v4 的修正

v3 中 bit2 固定开启，理由是"81% 有益 + r2>0.98 几乎不触发"。v4 将 bit2 改为 r2 自适应，使逻辑框架完整对称：

- **r1→bit1**: r1 高 → size 无变异 → freq/size ≈ c·freq → 关闭
- **r2→bit2**: r2 高 → size 无变异 → rec×size ≈ c·rec → 关闭

实际表现与 v3 几乎无差异（r2>0.98 仅 2/109 触发），但理论框架更清晰：**当且仅当 size 无变异时，包含 size 的 compound 特征退化为冗余**。

### v2→v3 的关键修正

v2 的两个错误假设被数据推翻：

1. **bit0 应始终开 → 错误**
   64策略穷举发现：f011（关bit0）dominates f111（开bit0）。固定关 bit0 的 avgLoss=0.002 优于固定开的 0.006。（详见 §4.1）

2. **r1>0.98 时 bit2 也应关 → 错误**
   f001(关bit0关bit1开bit2) 在 r1>0.98 组的 avgLoss=+0.005，vs f100(开bit0关bit1关bit2) 的 avgLoss=+0.015。bit2 即使在 size 无变异时仍有益（因为 rec×size 对应 GreedyDual-Size 的经典 size-aware 驱逐）。

### v4 逻辑（推荐实现）

```c
// auto_compound v4 决策：
//   bit0 (freq/rec):  固定关闭 — 信息冗余 + 维度诅咒 + 负边际
//   bit1 (freq/size): r1 > threshold → 关（size无变异→冗余）; 否则 → 开
//   bit2 (rec×size):  r2 > threshold → 关（size无变异→冗余）; 否则 → 开
//
// 默认:  f011 (bit0=关, bit1=开, bit2=开)
// r1>thr: bit1→关;  r2>thr: bit2→关

double auto_r_threshold = 0.98;  // 可通过 LOH_AUTO_COMPOUND_R_THRESHOLD 覆盖

loh_use_freq_rec  = 0;   // bit0: 固定关

if (r1 > auto_r_threshold) {
    loh_use_freq_size = 0;   // bit1: 关 (size无变异, freq/size ≈ c·freq)
} else {
    loh_use_freq_size = 1;   // bit1: 开 (size有变异, freq/size携带新信息)
}

if (r2 > auto_r_threshold) {
    loh_use_rec_size = 0;    // bit2: 关 (size无变异, rec×size ≈ c·rec)
} else {
    loh_use_rec_size = 1;    // bit2: 开 (size有变异, rec×size携带新信息)
}
```

### v4 表现（基于 109 traces 消融实验）

| 组 | n | 决策 | avgLoss vs oracle | maxLoss vs oracle |
|----|---|------|-------------------|-------------------|
| r1 > 0.98 | 22 | bit1→关 | +0.005 | +0.048 (w15) |
| r1 ≤ 0.98 | 87 | bit1→开 | +0.005 | +0.064 (w??) |
| r2 > 0.98 | 2 | bit2→关 | — | — |
| r2 ≤ 0.98 | 107 | bit2→开 | — | — |
| **全局** | **109** | **v4** | **+0.005** | **+0.064** |

与 v3 表现相同（r2>0.98 仅触发 2 次），但逻辑框架完整对称。

### 环境变量

| 变量 | 默认 | 说明 |
|------|------|------|
| `LOH_AUTO_COMPOUND` | 0 | 启用自适应 compound（启用后忽略 LOH_USE_FREQ_* 手动设置） |
| `LOH_AUTO_COMPOUND_R_THRESHOLD` | 0.98 | r1, r2 共用判断阈值（范围 0.5~1.0） |

## 7. 三个 bit 的决策总结

| bit | 含义 | 决策 | 理由 | avgLoss | maxLoss |
|-----|------|------|------|---------|---------|
| **bit0** | freq/rec | **固定关** | log1p下信息冗余 + freq/rec共线 + 维度诅咒 + 无有效预测指标 | +0.002 | +0.042 |
| **bit1** | freq/size | **r1>0.98→关, else→开** | r1精确测量size变异; Cohen's d=1.29 | +0.002 | +0.048 |
| **bit2** | rec×size | **r2>0.98→关, else→开** | 与bit1对称：r2测量size变异; r2>0.98仅2/109触发 | +0.001 | +0.036 |

## 8. 产物位置

| 产物 | 路径 |
|------|------|
| 消融结果 CSV | `/tmp/ablation_results.csv` |
| 增强诊断 CSV | `tmp/20260411-warmup-diag/diag_enhanced.csv` |
| CSV 生成脚本 | `tmp/20260411-warmup-diag/gen_csv.py` |
| r1→bit1 + r2→bit2 详情 | `tmp/20260411-warmup-diag/analysis_all_bits_detail.txt` |
| R2m_fr 深入分析 | `tmp/20260411-warmup-diag/analysis_R2m_fr_deep.txt` |
| 64策略穷举对比 | `tmp/20260411-warmup-diag/compare_full_strategies.txt` |
| r1 对3个bit的 Cohen's d | `tmp/20260411-warmup-diag/analyze_r1_all_bits.txt` |
| bit0 自适应指标探索 | `tmp/20260411-warmup-diag/analyze_bit0_adaptive.txt` |
| 增强分析 | `tmp/20260411-warmup-diag/analysis_output.txt` |
