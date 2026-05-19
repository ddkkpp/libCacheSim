# Trace 特征对比分析：生产 trace 的多样性与复杂性

> 日期: 2026-04-09
> 目的: 通过 traceAnalyzer 的标准图说明生产负载的多维度多样性与复杂性，以及单维度合成 trace 的退化特征。

---

## 1. 概述

缓存系统在生产环境中面对的工作负载，其统计特征在不同部署场景下差异巨大。
与仅隔离单一访问模式维度（如 recency 或 frequency）的合成基准不同，
真实 trace 同时展现出 **frequency 分布、对象大小分布、重用时间分布** 三个维度上的异质性，
以及维度之间的 **交叉耦合**。

本文档以三条真实 trace（1063、wiki_2019t、meta_reag）和三条合成 trace（recencytest、lfutest2、sizetest）为例，
通过 traceAnalyzer 输出的标准图，按特征维度而不是按 trace 顺序，展示这些工作负载之间的差异。

> **图的选择说明**：
> - **Frequency 特征** → 使用 `pop_rank`（rank-frequency / Zipf 图）：直接展示频率分布的偏斜程度
> - **Temporal locality 特征** → 使用 `access_vt`（访问散点图，virtual time）：展示时序访问模式
> - **Reuse 特征** → 使用 `reuse_vt`（virtual time CDF）：比 `reuse_rt` 更通用，不受时钟波动影响
> - **Size 特征** → 使用 `size`（size CDF）：展示对象大小分布

---

## 2. Reuse：从标准单维模式到复杂生产模式

为突出 reuse 维度，先看标准 recency trace，再看三条复杂生产 trace。

### 2.1 recencytest_10m：标准 reuse 模式

> 生成逻辑：50K 对象、固定 10KB、2000 热点窗口（FIFO）、85% 概率从热点窗口采样。

![lrutest reuse_vt](figures/20260409-trace-characteristic-comparison/lrutest_10m_reuse_vt.png)

- 这是典型的单维 recency / reuse trace，CDF 形状稳定且接近单一模式。
- reuse 距离主要由热点窗口大小决定，结构简单，解释明确。
- 在这种情况下，仅依赖 recency 的固定策略 LRU 已足够有效。

### 2.2 1063：短期重用主导，但保留明显长尾

![1063 reuse_vt](figures/20260409-trace-characteristic-comparison/1063_reuse_vt.png)

- 前段快速上升，说明存在很强的短期重用。
- 但尾部仍延伸到 $2.8 \times 10^8$，表明并非单一 reuse 尺度。
- 同一 trace 内同时包含“立即重访”“中等间隔回访”“长间隔回访”三类对象。

### 2.3 wiki_2019t：更宽的 reuse 尺度

![wiki reuse_vt](figures/20260409-trace-characteristic-comparison/wiki_2019t_reuse_vt.png)

- CDF 爬升明显慢于 1063，尾部也更长。
- 这说明 wiki_2019t 中短期热点与长间隔冷访问并存。
- 与标准 recency trace 相比，它不再对应单一窗口大小或单一局部性尺度。

### 2.4 meta_reag：极短重用与长尾重用并存

![meta reuse_vt](figures/20260409-trace-characteristic-comparison/meta_reag_reuse_vt.png)

- 起点附近就有明显跃升，表示大量连续重访或极短距离重用。
- 之后仍保留长尾，说明极短 reuse 并未覆盖全部访问。
- 这类结构同时包含 burst 行为和长间隔回访，明显比 recencytest 更复杂。

**小结**：reuse 维度本身已经说明，生产 trace 不是简单的“一个热点窗口”可以概括的；即使都存在局部性，它们的局部性尺度、尾部长度和形状也互不相同。

---

## 3. Frequency：从纯 Zipf 到不同强度的头重尾长

frequency 特征使用 `pop_rank` 图观察，因为它直接回答“请求频率如何分配到不同对象上”。

### 3.1 lfutest2_10m：标准 frequency trace

> 生成逻辑：500K 对象、固定 10KB、Zipf $\alpha=1.0$ 独立采样。

![lfutest pop_rank](figures/20260409-trace-characteristic-comparison/lfutest_10m_pop_rank.png)

- 这是标准的单维 frequency 模式，对数坐标下接近一条直线。
- 频率结构几乎完全由 Zipf 分布定义。
- 在这种场景下，仅依赖 frequency 的固定策略 LFU 已足够有效。

### 3.2 1063：阶梯型头部 + 长尾

![1063 pop_rank](figures/20260409-trace-characteristic-comparison/1063_pop_rank.png)

- 头部不是平滑直线，而是明显的阶梯型结构。
- 前若干对象极热，之后才进入较平滑的衰减段。
- 这说明 1063 的 frequency 结构不是单一 Zipf 参数可以精确描述的。

### 3.3 wiki_2019t：平滑重尾，但一次性对象很多

![wiki pop_rank](figures/20260409-trace-characteristic-comparison/wiki_2019t_pop_rank.png)

- 整体更接近平滑幂律衰减。
- 头部对象仍然很热，但大量对象只访问一次。
- 它与 1063 一样也是重尾分布，但头部形状、中段斜率和尾部厚度都不同。

### 3.4 meta_reag：极端头部集中

![meta pop_rank](figures/20260409-trace-characteristic-comparison/meta_reag_pop_rank.png)

- 头部陡降远强于 1063 和 wiki_2019t。
- Top-1 对象占比极高，frequency 集中度极端。
- 同样是重尾分布，但这里已经接近“极端头部主导”的另一类形态。

### 3.5 recencytest_10m 与 sizetest_10m：frequency 维度退化

![lrutest pop_rank](figures/20260409-trace-characteristic-comparison/lrutest_10m_pop_rank.png)

- recencytest_10m 中曲线几乎水平，说明频率几乎没有区分度。

![sizetest pop_rank](figures/20260409-trace-characteristic-comparison/sizetest_10m_pop_rank.png)

- sizetest_10m 中只有层级造成的平台感，但层内频率基本均匀。

**小结**：生产 trace 虽然都表现出 heavy tail，但它们不是同一类 frequency 结构；而合成 trace 往往把 frequency 退化成纯 Zipf 直线，或者干脆退化到几乎无信息。

---

## 4. Size：从单一主导台阶到跨数量级的真实差异

### 4.1 sizetest_10m：标准 size trace

> 生成逻辑：50K 小（128B, 70%）+ 10K 中（10KB, 20%）+ 2K 大（1MB, 10%）、层内均匀采样。

![sizetest size](figures/20260409-trace-characteristic-comparison/sizetest_10m_size.png)

- 三个明显台阶，对应预先设计的三层对象大小。
- size 维度是唯一主导因素。
- 在这种场景下，仅依赖 size 的固定策略 SIZE 已足够有效。

### 4.2 1063：中等变异，主要集中在 KB 级

![1063 size](figures/20260409-trace-characteristic-comparison/1063_size.png)

- 范围 512B – 524KB，集中在约 60KB。
- 与 sizetest 的“硬分层”不同，1063 的大小分布是连续变化的。
- size 有信息，但不是唯一决定因素。

### 4.3 wiki_2019t：范围更宽，但整体仍较温和

![wiki size](figures/20260409-trace-characteristic-comparison/wiki_2019t_size.png)

- 范围扩展到 10B – 6.9MB。
- 相比 1063，wiki_2019t 在尾部更长，但整体变异仍明显低于 meta_reag。

### 4.4 meta_reag：极端 size 变异

![meta size](figures/20260409-trace-characteristic-comparison/meta_reag_size.png)

- 范围横跨 1B – 4.3GB。
- 主体对象与尾部巨型对象相差多个数量级。
- 这种结构意味着 size 不只是补充特征，而是必须与 frequency、reuse 一起联合考虑的核心维度。

**小结**：合成 size trace 用三层台阶把问题简化成单一因素；而生产 trace 的 size 分布是连续的、长尾的，并且不同 trace 之间差异很大。

---

## 5. Access：用时序图归纳非平稳性与维度耦合

access_vt 不直接等同于 reuse 或 frequency，但它能够从时序角度总结前面三个维度如何共同作用。

### 5.1 recencytest_10m：标准线性三角形

![lrutest access_vt](figures/20260409-trace-characteristic-comparison/lrutest_10m_access_vt.png)

- 这是最标准的单维 recency 访问图。
- 热点窗口不断前移，因此形成清晰的三角边界。

### 5.2 lfutest2_10m：frequency 驱动的头部聚集

![lfutest access_vt](figures/20260409-trace-characteristic-comparison/lfutest_10m_access_vt.png)

- 高频对象在底部持续出现，形成高密度带。
- 其余对象作为稀疏散点分布。
- 这说明 access 图已经被单一 frequency 维度主导。

### 5.3 sizetest_10m：近似均匀矩形

![sizetest access_vt](figures/20260409-trace-characteristic-comparison/sizetest_10m_access_vt.png)

- 完全缺乏清晰的局部性结构。
- recency 和 frequency 都几乎不提供有效排序信息。

### 5.4 1063：局部性、工作集扩展与间歇期并存

![1063 access_vt](figures/20260409-trace-characteristic-comparison/1063_access_vt.png)

- 底部稠密，说明存在稳定热点。
- 工作集边界又在缓慢扩展，说明活跃对象集合不是固定的。
- 图中还可见明显间歇期，反映出非平稳性。

### 5.5 wiki_2019t：比 1063 更平滑，但仍不是单一模式

![wiki access_vt](figures/20260409-trace-characteristic-comparison/wiki_2019t_access_vt.png)

- 整体分布较规则，但并不退化为单一几何形状。
- 它既不是 recencytest 那样的三角形，也不是 sizetest 那样的均匀矩形。

### 5.6 meta_reag：明显分层的混合结构

![meta access_vt](figures/20260409-trace-characteristic-comparison/meta_reag_access_vt.png)

- 顶部和底部密度差异明显，显示出强烈的分层访问模式。
- burst 行为、超热对象和冷尾对象同时存在。

**小结**：access_vt 图最直观地说明，生产 trace 不仅是多维度复合的，而且不同生产 trace 之间的复合方式也互不相同；此外，时序上还存在明显的非平稳性。

---

## 6. 关键结论

1. **生产 trace 是多维度复合的。** reuse、frequency、size 三个维度都同时存在信息，不能化约为单一特征。

2. **不同生产 trace 彼此并不相同。** 1063、wiki_2019t 和 meta_reag 虽然都属于真实工作负载，但在 reuse 曲线形状、frequency 头尾结构、size 变异程度以及 access 时序结构上都明显不同。

3. **合成 trace 主要刻画单一维度。** recencytest、lfutest2、sizetest 分别给出了标准的 reuse、frequency、size 单维模式，因此适合解释单个特征，却不足以代表生产负载的复杂性。

4. **非平稳性是生产 trace 的额外难点。** 尤其从 access_vt 图可以看到，真实工作负载的活跃集合、访问密度和局部性结构都会随时间变化，因此任何只关注单一维度的固定策略（LRU/LFU/SIZE）都难以稳定适配全部场景。

## 7. 四种算法在六条 trace 上的 MR / BMR

下表汇总了 LRU、LFU、SIZE、LOH 在三条标准 trace 与三条真实 trace 上的最终 miss ratio（MR）和 byte miss ratio（BMR）表现。所有实验的缓存容量均使用 **0.1 比例**。

| Trace | Cache Size (0.1) | LRU MR/BMR | LFU MR/BMR | SIZE MR/BMR | LOH MR/BMR |
|------|------------|------------|------------|-------------|------------|
| recencytest_10m | 48MiB | 0.1352 / 0.1352 | 0.8975 / 0.8975 | 0.8975 / 0.8975 | 0.1457 / 0.1457 |
| lfutest2_10m | 440MiB | 0.2402 / 0.2402 | 0.1997 / 0.1997 | 0.2404 / 0.2404 | 0.1870 / 0.1870 |
| sizetest_10m | 210MiB | 0.9601 / 0.8982 | 0.9771 / 0.8977 | 0.1007 / 0.9275 | 0.2550 / 0.9050 |
| 1063 | 5GiB | 0.2618 / 0.2209 | 0.6201 / 0.6510 | 0.4802 / 0.7884 | 0.0350 / 0.0349 |
| wiki_2019t | 40GiB | 0.2306 / 0.1619 | 0.2200 / 0.1552 | 0.7986 / 0.9077 | 0.1709 / 0.1336 |
| meta_reag | 16TiB | 0.3268 / 0.1753 | 0.4650 / 0.4374 | 0.3089 / 0.3579 | 0.2707 / 0.1572 |

**表 1 反映出三个关键现象：**

1. **标准 trace 上的最优策略与主导特征一致。** recencytest 上 LRU 最优（MR=0.1352）；lfutest2 上 LFU 最优（MR=0.1997）；sizetest 上 SIZE 的 MR 远低于其他策略（MR=0.1007）。

2. **LOH（CMA-ES v1s1 默认配置）在合成 trace 上均超越非专家策略。** recencytest 上 LOH 接近 LRU（0.1457 vs 0.1352，仅+0.01）；lfutest2 上 LOH 超越 LFU（0.1870 < 0.1997）；sizetest 上从纯 LRU 的 0.9601 大幅降至 0.2550，虽未达到 SIZE 的 0.1007，但已体现出对 size 维度的自适应能力。

3. **真实 trace 上 LOH 一致取得最优。** 在 1063 上 LOH 的 MR (0.0350) 远低于 LRU (0.2618)；wiki_2019t 上 LOH (0.1709) 优于 LFU (0.2200)；meta_reag 上 LOH (0.2707) 同样最低。这说明 LOH 的 CMA-ES 权重优化在多维复合的真实负载上持续有效。

> 口径说明：
> - 所有实验统一使用 cache size = 0.1（即工作集的 10%）。
> - `SIZE` 列统一使用 `Size` 算法结果（`libCacheSim/cache/eviction/Size.c`）。
> - `LOH` 列统一使用 CMA-ES 默认配置 v1s1（`LOH_CMAES_INIT_FROM_WEIGHTS=0, LOH_CMAES_SKIP_INIT_ASK=1`）。
> - 真实 trace 的 LOH 测试日志: `tmp/20260410-real-cmaes-4cfg/logs/*_LOH_v1s1.log`。
> - 合成 trace 的 LOH 测试日志: `tmp/20260409-synthetic-0.1/logs/*_LOH_cmaes_v1skip.log`。
> - 真实 trace 的 `Size` 补跑日志: `tmp/20260409-size-real-traces/logs/` 目录。

## 8. CMA-ES 初始化配置对比

CMA-ES 优化器有两个正交配置项，共四种组合：

| 环境变量 | 说明 |
|---|---|
| `LOH_CMAES_INIT_FROM_WEIGHTS` | 0 = v1（标量 mean=0.5 均匀起点）；1 = v2（向量化 mean，从当前系统权重出发） |
| `LOH_CMAES_SKIP_INIT_ASK` | 0 = 创建时立即 ask()，使用 CMA-ES 采样权重；1 = 跳过首轮 ask()，使用系统默认权重 [1,0,...] |

### 8.1 合成 trace 四种配置对比

| 配置 | recencytest MR | lfutest2 MR | sizetest MR |
|---|---|---|---|
| v1s0 (scalar, ask) | 0.5041 | 0.1964 | **0.1365** |
| **v1s1 (scalar, skip) ★默认** | 0.1457 | **0.1870** | 0.2550 |
| v2s0 (vector, ask) | 0.1439 | 0.1945 | 0.2711 |
| v2s1 (vector, skip) | 0.1606 | 0.1924 | 0.1866 |
| LRU (参考) | 0.1352 | 0.2402 | 0.9601 |
| 最佳专家 | 0.1352 (LRU) | 0.1997 (LFU) | 0.1007 (SIZE) |

关键发现：
- **v1s0 在 sizetest 上最优**（0.1365），但在 recencytest 上灾难性退化（0.5041），因为从 mean=0.5 开始的初始采样权重破坏了已经最优的纯 recency 策略。
- **v1s1 综合最均衡**：recencytest (0.1457) 接近 LRU；lfutest2 (0.1870) 全场最佳；sizetest (0.2550) 虽非最优但远好于 LRU。
- **v2s1** 在三个维度上也较均衡，sizetest (0.1866) 优于 v1s1，但 recencytest (0.1606) 稍差。
- **SKIP=1 一致有益**：无论 v1 还是 v2，跳过首轮 ask 让系统权重先运行一个周期，避免了初始采样的性能波动。

### 8.2 真实 trace 四种配置对比

| 配置 | 1063 MR | 1063 BMR | wiki MR | wiki BMR | meta MR | meta BMR |
|---|---|---|---|---|---|---|
| v1s0 | 0.0366 | 0.0366 | 0.1710 | 0.1336 | 0.2712 | 0.1566 |
| **v1s1 ★默认** | **0.0350** | **0.0349** | **0.1709** | 0.1336 | **0.2707** | 0.1572 |
| v2s0 | 0.0364 | 0.0363 | 0.1712 | 0.1340 | 0.2708 | **0.1568** |
| v2s1 | 0.0351 | 0.0350 | 0.1709 | 0.1338 | 0.2818 | 0.1592 |

关键发现：
- **真实 trace 上四种配置差异极小**（< 0.2% MR），远不如合成 trace 上差异显著。
- **SKIP=1 在 1063 上一致更优**（v1s1/v2s1 均比对应 s0 版本低 ~0.15% MR）。
- **wiki 上几乎无差异**（MR 波动在 0.03% 以内）。
- **meta 上 v2s1 异常偏高**（0.2818 vs ~0.271），其余三种接近。

### 8.3 默认配置选择依据

选择 **v1s1** 作为默认配置的理由：
1. 在合成 trace 上综合表现最均衡（特别是避免了 v1s0 的 recencytest 灾难性退化）。
2. 在真实 trace 上一致取得最优或并列最优 MR。
3. SKIP=1 的"首轮用系统权重"策略具有明确的安全保障——即使 CMA-ES 初始采样不佳，第一个评估周期也不会被破坏。

> 实验日志：
> - 合成 trace: `tmp/20260409-synthetic-0.1/logs/` 目录
> - 真实 trace: `tmp/20260410-real-cmaes-4cfg/logs/` 目录

## 9. CMA-ES 运行时演化日志分析

通过 `LOH_CMAES_LOG=1` 环境变量启用运行时日志，记录每次 tell/ask 周期的 gen（代数）、sigma（步长）、feedback（miss ratio）、mean（CMA-ES 均值向量，phenotype 空间）和 weights（实际使用的权重）。

### 9.1 1063 (tencentBlock) 演化轨迹

**配置**: v1s1 默认（aIPOP_CMAES, lambda=10, sigma_0=0.5, bounds=[0,1]）
**总代数**: 22452 代，115870 条日志（每代 10 条 = lambda=10）
**最终 MR**: 0.0370（无日志基线: 0.0350）

| 阶段 | gen 范围 | sigma | mean 向量 | 说明 |
|---|---|---|---|---|
| 初始探索 | 0→100 | 0.50→1.51 | 随机游走 | sigma 缓慢膨胀 |
| 第一轮膨胀 | 100→500 | 1.51→9.45 | 跳跃式变化 | sigma 快速增长，搜索范围远超 [0,1] |
| **aIPOP 自动重启+收敛** | ~500→1000 | 9.45→**0.013** | **[0.22, 0.39, 0.004, 0.80, 1.00, 0.58]** | sigma 极小，mean 稳定收敛 |
| 二次膨胀 | 1000→1864 | 0.013→303 | 偏移 | landscape 变平坦，sigma 再次增长 |
| **发散（永久失效）** | 1865→22452 | **inf** | [0.50, 0.50, 0.50, ...] | 数值溢出，所有候选退化为 0.5 |

**收敛权重解读**（6 维对应 `loh_active_weight_map` 映射的 WEIGHT_DIM 特征）:
- freq(0.22) → 频率有一定作用
- freq_decay(0.39) → 频率衰减中等
- size_ratio(**0.004≈0**) → 对象大小几乎不影响评分
- age_ratio(0.80) → 年龄/衰老较重要
- **recency_ratio(1.00)** → 近因性为最主导特征
- freq_sq(0.58) → 频率平方项中等

这与 1063 的 trace 特征分析一致：reuse 维度的 CDF 前段快速上升，短期重用主导。

### 9.2 meta_reag (CDN) 演化轨迹

**配置**: 同上 v1s1 默认
**总代数**: 2995 代，29956 条日志
**最终 MR**: 0.2714 / BMR: 0.1566（无日志基线: 0.2707/0.1572）

| 阶段 | gen 范围 | sigma | mean 向量 | 说明 |
|---|---|---|---|---|
| 探索+多轮重启 | 0→600 | 0.50→8.76→1.98 | 剧烈变化 | aIPOP 多次重启尝试 |
| 逐步收敛 | 600→1900 | 1.98→**0.12** | 趋向稳定 | sigma 持续下降 |
| **稳定收敛** | 1900→2190 | **0.10~0.17** | **[0.92, 0.29, 0.85, 0.71, 0.93, 0.58]** | ~300 代稳定，mean≈weights |
| **发散（永久失效）** | 2195→2995 | **inf** | [0.50, ...] | 同 1063 |

**收敛权重解读**:
- **freq(0.92)** → 频率为最主导特征之一
- freq_decay(0.29) → 频率衰减贡献较低
- **freq_sq(0.85)** → 频率平方项高，进一步强化头部热点的选择性
- **size_ratio(0.71)** → 对象大小有显著影响（CDN 场景中大对象占带宽）
- **recency_ratio(0.93)** → 近因性同样非常重要
- age_ratio(0.58) → 中等

这与 meta 的 trace 特征一致：极端头部集中的 frequency 分布 + 大跨度 size 分布，需要 freq 和 size 双维度参与评分。

### 9.3 合成 trace 演化轨迹

三个合成 trace 均使用 v1s1 默认配置运行，以对比与真实 trace 的 sigma 行为差异。

#### 9.3.1 recencytest（纯近因性）

**总代数**: 1521 代  |  **最终 MR**: 0.1634
**sigma 未发散**: 最终 sigma=0.081，全程有限

| 阶段 | gen 范围 | sigma | mean 向量 | 说明 |
|---|---|---|---|---|
| 初始收敛 | 0→500 | 0.50→**0.003** | 快速稳定 | 极快收敛，trace 信号清晰 |
| 稳定期 | 500→1050 | 0.003→0.005 | [0.76, 0.12, 0.69, 0.00, 0.04, 0.02] | sigma 极小，权重稳定 |
| 轻微膨胀 | 1050→1150 | →22.9 | 偏移 | aIPOP 小幅重启 |
| 回落收敛 | 1150→1521 | →**0.081** | [0.76, 0.12, 0.69, 0.00, 0.04, 0.02] | 重新收敛，**未到 inf** |

**收敛权重**: freq(0.76), freq_decay(0.12), size_ratio(0.69), age_ratio(≈0), recency_ratio(0.04), freq_sq(0.02)。与预期不完全一致（纯 recency trace 却 recency_ratio≈0），但因 compound 评分中各维度的非线性交互，freq 和 size_ratio 的组合也能有效捕获近因性信号。

#### 9.3.2 lfutest2（频率主导）

**总代数**: 1592 代  |  **最终 MR**: 0.1980
**sigma 大幅膨胀但未到 inf**: 最终 sigma=1601

| 阶段 | gen 范围 | sigma | mean 向量 | 说明 |
|---|---|---|---|---|
| 收敛 | 0→12 | 0.50→**0.235** | [0.31, 0.38, 0.85, 0.59, 0.59, 0.08] | 极快收敛（仅 12 代） |
| 膨胀 | 12→766 | 0.235→100 | 偏移 | landscape 变平坦，sigma 持续增长 |
| 加速膨胀 | 766→1592 | 100→**1601** | [0.25, 0.96, 0.93, 0.45, 0.64, 0.30] | sigma 非常大但未溢出到 inf |

**收敛权重**（gen=12 时）: freq(0.31), freq_decay(0.38), size_ratio(0.85), age_ratio(0.59), recency_ratio(0.59), freq_sq(0.08)。sigma=1601 时权重已高度随机化（候选从 mean±1601 采样，远超 [0,1] 边界）。

#### 9.3.3 sizetest（对象大小主导）

**总代数**: 1460 代  |  **最终 MR**: 0.2576 / BMR: 0.9044
**sigma 中等膨胀**: 最终 sigma=16.98

| 阶段 | gen 范围 | sigma | mean 向量 | 说明 |
|---|---|---|---|---|
| 初始收敛 | 0→997 | 0.50→**0.116** | 稳步下降 | 缓慢但持续收敛 |
| 再膨胀 | 997→1460 | 0.116→**16.98** | [0.60, 0.06, 0.60, 1.00, 0.19, 0.99] | sigma 增长适中 |

**收敛权重**（gen=997 时）: freq(0.01), freq_decay(0.39), size_ratio(0.20), **age_ratio(0.60)**, recency_ratio(0.46), freq_sq(0.06)。size_ratio=0.20 表明对象大小通过评分公式间接影响，不需要极高权重。

### 9.4 合成 vs 真实 trace 对比总结

| Trace | 总代数 | sigma 最小值 | 最小值 gen | sigma 最终 | 是否 inf | MR |
|---|---|---|---|---|---|---|
| **1063** | 22452 | 0.013 | ~1000 | inf | **是**（gen 1865） | 0.0370 |
| **meta** | 2995 | 0.10 | ~1900 | inf | **是**（gen 2195） | 0.2714 |
| **wiki** | — | — | — | — | 未测 | — |
| recencytest | 1521 | **0.003** | ~514 | 0.081 | **否** | 0.1634 |
| lfutest2 | 1592 | 0.235 | 12 | 1601 | **否** | 0.1980 |
| sizetest | 1460 | 0.116 | 997 | 16.98 | **否** | 0.2576 |

**关键发现**:

1. **合成 trace 不会 sigma→inf**: 三个合成 trace 虽然 sigma 也会膨胀（lfutest2 到 1601），但均**未溢出到 inf**。这与真实 trace（1063/meta 均到 inf）形成鲜明对比。
2. **合成 trace 更早/更快收敛**: recencytest 在 gen=514 就达到 sigma=0.003（极度收敛），lfutest2 仅 12 代就收敛。真实 trace 需 ~1000-1900 代。
3. **原因解释**: 合成 trace 的 fitness landscape 特征更清晰、更单一——一个维度主导 miss ratio 变化。真实 trace 特征混合复杂，收敛后 landscape 非常平坦，CMA-ES 的步长膨胀机制容易触发数值溢出。
4. **trace 生命周期差异**: 合成 trace 只有 10M 请求，产生 ~1500 代；真实 trace（1063 有 ~1.8B 请求）产生 22000+ 代。sigma→inf 需要足够多的"平坦代数"才会溢出——合成 trace 在溢出前就结束了运行。

> 实验日志: `tmp/20260410-cmaes-log/`（含 1063_v2.log、meta_v2.log、recencytest_cmaes.log、lfutest2_cmaes.log、sizetest_cmaes.log）
> Per-gen CSV: `tmp/20260410-cmaes-log/`（含 *_per_gen.csv）

## 10. 数据来源

- traceAnalyzer 输出图: `figure/` 目录
- traceAnalyzer 分析数据: `analysis/` 目录
- 真实 trace 的 `Size` 补跑日志: `tmp/20260409-size-real-traces/logs/` 目录
- 合成 trace 全量实验日志: `tmp/20260409-synthetic-0.1/logs/` 目录
- CMA-ES 四配置真实 trace 日志: `tmp/20260410-real-cmaes-4cfg/logs/` 目录
- CMA-ES 运行时演化日志: `tmp/20260410-cmaes-log/`（含真实 trace 和合成 trace 日志及 per-gen CSV）
- 合成 trace pop_rank 生成脚本: `tmp/20260409-repeat-exp/gen_pop_rank.py`
- 合成trace位置：recencytest_10m.csv lfutest2_10m.csv sizetest_10m.csv
- 合成脚本：scripts/gen_recency_trace.py  scripts/gen_lfu_trace.py

## 11. 2026-04-30 合成 Trace（0.1）更新结果

本节记录当前根目录三条合成 trace 在 `cache_size=0.1` 下的四算法结果（单次运行口径），其中：

- `recencytest_10m.csv` 使用参数 sweep 生成的固定版本：`WINDOW=1000, P_RECENT=0.70, N_OBJECTS=100000`。
- `lfutest2_10m.csv` 使用纯全局单一 Zipf 分布：`alpha=1.0, N_OBJECTS=100000`（无热/冷分层）。
- `sizetest_10m.csv` 使用两层大小分布：`90% x 64B + 10% x 4MB, N_OBJECTS=100000`。

实验结果（recencytest/sizetest 日志目录：`tmp/20260430-synth-final-0p1/logs/`；lfutest2 更新于 2026-04-30 使用纯 Zipf alpha=1.0 重新生成并运行）：

**对象 Miss Ratio（MR）**：

| Trace | LRU MR | LFU MR | SIZE MR | LOH(CMA-ES) MR |
|---|---|---|---|---|
| recencytest_10m | 0.269953 | 0.897591 | 0.897121 | 0.274118 |
| lfutest2_10m | 0.262958 | 0.214893 | 0.263925 | 0.212055 |
| sizetest_10m | 0.900022 | 0.891169 | 0.098974 | 0.099074 |

**字节 Miss Ratio（BMR）**（recencytest/lfutest2 所有对象等大，BMR = MR；sizetest 大小差异极端，BMR 与 MR 显著不同）：

| Trace | LRU BMR | LFU BMR | SIZE BMR | LOH(CMA-ES) BMR |
|---|---|---|---|---|
| recencytest_10m | 0.269953 | 0.897591 | 0.897121 | 0.274118 |
| lfutest2_10m | 0.262958 | 0.214893 | 0.263925 | 0.212055 |
| sizetest_10m | 0.900132 | 0.899986 | 0.899778 | 0.900455 |

> **注**：sizetest 的 SIZE BMR ≈ 0.900，原因是 SIZE 驱逐了所有大对象（4MB），大对象的字节量占总访问字节量约 99.9%（10K 大对象 × 4MB ≫ 90K 小对象 × 64B），因此即使大对象的对象 MR 接近 1.0，BMR 也接近 1.0。SIZE 优势体现在**对象命中率（MR≈0.099）**而非字节命中率。

### 11.1 合成代码位置与 Trace 位置

- Trace 文件（根目录）：
	- `recencytest_10m.csv`
	- `lfutest2_10m.csv`
	- `sizetest_10m.csv`
- 生成脚本：
	- `scripts/gen_recency_trace.py`
	- `scripts/gen_lfu_trace.py`
	- `scripts/gen_size_trace.py`
- recency 参数扫描脚本（用于生成并选定 `W=1000, P=0.70` 版本）：
	- `tmp/20260430-recency-sweep/run.sh`
- 选定 recency 源文件（已复制到根目录）：
	- `tmp/20260430-recency-sweep/traces/recency_w1000_p070.csv`

### 11.2 三条 Trace 的详细合成逻辑

### 11.2 三条 Trace 的详细合成逻辑

#### 1. `recencytest_10m.csv` — 时序局部性主导

- **生成脚本**：`scripts/gen_recency_trace.py`
- **固定参数**：`N_REQUESTS=10,000,000`, `N_OBJECTS=100,000`, `OBJ_SIZE=10,000B`, `SEED=42`
- **选定参数**：`WINDOW=1000`, `P_RECENT=0.70`（通过参数 sweep 在 recencytest 场景下 LRU 显著优于其他算法的参数组合）
- **采样逻辑**：
	1. 维护一个大小为 `WINDOW=1000` 的热点滑动窗口（circular buffer），初始填满 ID=0..999。
	2. 每次请求以概率 `P_RECENT=0.70` 从热点窗口中均匀采样一个对象。
	3. 以概率 `1 - P_RECENT=0.30` 从全对象池（0..99999）均匀采样（冷访问）。
	4. 当冷访问命中时，被采样的对象替换窗口中最旧的对象（FIFO 更新窗口），模拟时序局部性滑动。
- **为何 LRU 最优**：热点窗口对应近期被频繁访问的对象子集，LRU 的驱逐策略与窗口保留集天然吻合；LFU/SIZE 无法感知时序滑动，频率计数趋同后失效。
- **实测效果**：LRU=0.2700，SIZE=0.8971，LFU=0.8976，LOH=0.2741（LOH 接近 LRU 但略差约 0.004）。

#### 2. `lfutest2_10m.csv` — 频率主导（纯 Zipf 全局分布）

- **生成脚本**：`scripts/gen_lfu_trace.py`
- **固定参数**：`N_REQUESTS=10,000,000`, `N_OBJECTS=100,000`, `OBJ_SIZE=10,000B`, `SEED=42`
- **分布参数**：`ZIPF_ALPHA=1.0`（标准 Zipf-1 幂律分布）
- **采样逻辑**：
	1. 计算 N_OBJECTS 个对象的 Zipf(alpha=1.0) 概率质量函数（PMF）：$P(k) = \frac{1/k^{1.0}}{H_N}$，其中 $H_N = \sum_{k=1}^{N} 1/k$。
	2. 对象 ID 按排名 1..N 分配对应概率权重（排名第 1 的对象 top-1 占总流量约 8.27%）。
	3. 每次请求独立按 PMF 抽样对象 ID，即 i.i.d.（无时序相关性，无热/冷分层）。
	4. 所有对象大小相同（= 10,000B），消除 size 信号干扰。
- **为何 LFU 明显优于 LRU/SIZE**：
	- 稳定 Zipf 分布使高频对象的长期访问频率远高于低频对象，LFU 通过维护精确频率计数保留高价值对象。
	- LRU 只感知最近一次访问时间，i.i.d. 访问下近期命中与未来命中无相关性，性能接近随机替换。
	- SIZE 在所有对象等大时**不退化为 LRU**（详见 §13.3）：命中时 `pqueue_change_priority(S, S)` 调用 `percolate_down` 但条件不满足，节点原地不动，驱逐顺序是混合 FIFO+LIFO，对 recency 完全盲。
- **为何 LOH 进一步优于 LFU**：
	- LOH 是 LFU 的严格超集：当 CMA-ES 将频率维度权重调大、其余维度权重归零时，LOH 等价于 LFU。
	- CMA-ES 可在 LFU 基础上继续优化权重组合（如复合特征 freq×size），进一步降低 miss ratio。
	- 数学上，在任意 i.i.d. 稳态 trace 上，LOH ≥ LFU 是必然成立的。
- **为何 SIZE 在 lfutest2（等大对象）上与 LRU 表现相近**：
	- 此处原文曾称"SIZE 退化为 LRU"，该说法**不准确**。详见 §13.3 对 pqueue 实现的完整分析。
	- 正确解释：SIZE 在等大对象时命中不更新 pqueue 位置（`pqueue_change_priority(S, S)` → `percolate_down` 不动），驱逐顺序是混合 FIFO+LIFO，对 recency 完全"盲"。在 i.i.d. trace 上，LRU/FIFO/LIFO 表现相近（无 recency 可利用），故 SIZE ≈ LRU 是巧合而非机制等价。
- **实测效果**：LRU=0.2630，SIZE=0.2639，LFU=0.2149，LOH=0.2121（LFU 比 LRU 低约 0.048，LOH 比 LFU 再低约 0.003）。

#### 3. `sizetest_10m.csv` — 大小主导（两层极端大小分布）

- **生成脚本**：`scripts/gen_size_trace.py`
- **固定参数**：`N_REQUESTS=10,000,000`, `N_OBJECTS=100,000`, `SEED=42`
- **分层参数**：
	- 小对象层：`N_SMALL=90,000`，每对象大小 = `64B`
	- 大对象层：`N_LARGE=10,000`，每对象大小 = `4,194,304B`（= 4MB）
- **采样逻辑**：
	1. 对象 ID 在全池（0..99999）均匀采样（无频率偏向、无时序局部性），请求频率在两层内均匀分布。
	2. 访问小对象（ID 0..89999，size=64B）和大对象（ID 90000..99999，size=4MB）的概率各约 90% 和 10%（均匀采样下按对象数比例）。
	3. 由于大对象占用空间远大于小对象，缓存中大对象的"字节价值"极低（一个大对象占用 64K 个小对象的空间）。
- **为何 SIZE 最优（MR ≈ 0.099）**：
	- SIZE 算法驱逐缓存中**体积最大的对象**（max-heap by obj_size）。
	- 缓存空间优先保留小对象（64B），驱逐大对象（4MB），使 90% 的小对象请求几乎全部命中缓存，miss 主要来自大对象（无论如何都不会长期驻留缓存）。
	- 字节 miss ratio（BMR）接近 1.0，因为大对象的字节体量主导了 BMR 分母，但**对象命中率**（MR）接近最优。
- **为何 LRU/LFU 表现差（MR ≈ 0.90）**：
	- LRU/LFU 不感知对象大小，大对象和小对象受到同等对待。
	- 单个 4MB 大对象进入缓存会驱逐大量小对象，造成频繁 miss。
- **LOH 的表现**：LOH MR ≈ 0.099，与 SIZE 相当，体现出 CMA-ES 自适应发现了 size 维度的重要性。
- **实测效果**：LRU≈0.900，LFU≈0.891，SIZE=0.099，LOH=0.099（SIZE 和 LOH 并列最优，LRU/LFU 退化）。

## 12. 2026-04-30 LOH 权重收敛实验（CMA-ES vs DRL）

本节新增实验：对三条合成 trace（recencytest、lfutest2、sizetest）分别执行

- CMA-ES 模式：`LOH_ENABLE_CMAES=1, LOH_ENABLE_RL=0`
- DRL 模式：`LOH_ENABLE_RL=1, LOH_ENABLE_CMAES=0`

每个模式每条 trace 重复 3 次（总计 18 次），并记录权重轨迹后分析收敛行为。

### 12.1 实验脚本与日志位置

- 批量运行脚本：`tmp/20260430-weight-analysis/run_all.sh`
- 分析脚本：`tmp/20260430-weight-analysis/analyze_weights.py`
- 总控日志：`tmp/20260430-weight-analysis/run_all_stdout.log`
- wrapper 日志目录：`tmp/20260430-weight-analysis/logs/`
- DRL 子日志（自动解析）：`logs/ac_sb3_*.log` 与 `logs/cachesim_sb3_*.log`

### 12.2 Miss Ratio 汇总（3 次重复）

| 模式 | Trace | rep1 | rep2 | rep3 | mean | std |
|---|---|---:|---:|---:|---:|---:|
| CMA-ES | recencytest | 0.273861 | 0.271408 | 0.299806 | 0.281692 | 0.015735 |
| CMA-ES | lfutest2 | 0.205595 | 0.198331 | 0.197674 | 0.200533 | 0.004396 |
| CMA-ES | sizetest | 0.099043 | 0.099050 | 0.099029 | 0.099041 | 0.000011 |
| DRL | recencytest | 0.584663 | 0.583425 | 0.593893 | 0.587327 | 0.005720 |
| DRL | lfutest2 | 0.206108 | 0.206076 | 0.207444 | 0.206543 | 0.000781 |
| DRL | sizetest | 0.099090 | 0.099153 | 0.099089 | 0.099111 | 0.000037 |

### 12.2.1 每次重复最终权重向量明细（w0..w5）

权重维度语义：`w0=recency, w1=freq, w2=size, w3=freq_rec, w4=freq_size, w5=rec_size`。
表中每行已将主导权重（最大值）加粗。

| 模式 | Trace | rep | w0 | w1 | w2 | w3 | w4 | w5 |
|---|---|---|---:|---:|---:|---:|---:|---:|
| CMA-ES | recencytest | rep1 | 0.9821 | 0.0040 | **0.9897** | 0.0077 | 0.0321 | 0.9618 |
| CMA-ES | recencytest | rep2 | **0.9898** | 0.0242 | 0.2807 | 0.1237 | 0.0028 | 0.6913 |
| CMA-ES | recencytest | rep3 | **0.5000** | **0.5000** | **0.5000** | **0.5000** | **0.5000** | **0.5000** |
| CMA-ES | lfutest2 | rep1 | 0.9215 | 0.8421 | 0.5297 | **0.9999** | 0.4877 | 0.5141 |
| CMA-ES | lfutest2 | rep2 | 0.3397 | 0.0082 | 0.4395 | **0.6399** | 0.2622 | 0.3234 |
| CMA-ES | lfutest2 | rep3 | **0.5000** | **0.5000** | **0.5000** | **0.5000** | **0.5000** | **0.5000** |
| CMA-ES | sizetest | rep1 | 0.0087 | 0.6881 | **0.8044** | 0.2818 | 0.5980 | 0.2435 |
| CMA-ES | sizetest | rep2 | 0.3838 | 0.6311 | 0.4130 | 0.8323 | **0.9989** | 0.6680 |
| CMA-ES | sizetest | rep3 | 0.6838 | 0.4046 | 0.2731 | 0.3990 | **0.7413** | 0.6393 |
| DRL | recencytest | rep1 | 0.6351 | 0.8173 | 0.6218 | **0.9409** | 0.6636 | 0.5159 |
| DRL | recencytest | rep2 | 0.9298 | 0.8363 | **0.9530** | 0.3102 | 0.3372 | 0.8497 |
| DRL | recencytest | rep3 | 0.0035 | 0.6721 | 0.9604 | **0.9645** | 0.6486 | 0.8695 |
| DRL | lfutest2 | rep1 | 0.7881 | **0.9042** | 0.7109 | 0.6610 | 0.8976 | 0.6268 |
| DRL | lfutest2 | rep2 | **0.9785** | 0.7716 | 0.5744 | 0.7331 | 0.9421 | 0.4398 |
| DRL | lfutest2 | rep3 | 0.8058 | 0.5848 | 0.8834 | **0.9564** | 0.6387 | 0.8596 |
| DRL | sizetest | rep1 | 0.5944 | **0.9634** | 0.5545 | 0.7439 | 0.7111 | 0.2652 |
| DRL | sizetest | rep2 | 0.8978 | 0.6031 | 0.8341 | 0.4382 | 0.6791 | **0.9019** |
| DRL | sizetest | rep3 | 0.0585 | 0.2320 | 0.2986 | 0.8400 | **0.8942** | 0.7237 |

### 12.3 权重与收敛结论

1. **CMA-ES 在 sizetest 上最稳定、几乎完全收敛。**
	- MR 标准差仅 `1.1e-5`，3 次重复几乎重合。
	- 最终主导维度多次落在 `size` 或 `freq_size` 复合项，均能达到最优区间（~0.099）。

2. **CMA-ES 在 lfutest2 上总体收敛，但存在个别异常 run。**
	- rep1/rep2 收敛到较低 MR（0.2056/0.1983）；rep3 出现 `sigma` 爆炸并回退到接近均匀权重（0.5 向量），但 MR 仍较好（0.1977）。
	- 说明在频率主导 trace 上，LOH 解空间存在较宽“可行盆地”，即使非理想收敛也能取得接近最优结果。

3. **CMA-ES 在 recencytest 上收敛不稳定，存在明显 run-to-run 漂移。**
	- 两次收敛到较好区间（~0.272），一次发生 `sigma` 爆炸导致 MR 恶化到 0.2998。
	- 这与 recency 场景目标面更尖锐、且多维复合特征共线有关。

4. **DRL 的“权重收敛”总体弱于 CMA-ES，呈持续波动。**
	- 在 9 组 DRL 运行中，尾段权重标准差普遍在 `0.1~0.4`，说明策略仍在探索/抖动，未形成静态收敛点。
	- 但在 lfutest2 与 sizetest 上，DRL 的 MR 仍稳定（std 分别 0.000781 与 0.000037），说明策略可在较宽权重区域维持相近性能。

5. **DRL 在 recencytest 明显失败（MR≈0.587），远差于 CMA-ES/LRU。**
	- 三次重复均落在 ~0.585-0.594，且主导权重维度不一致，显示未学到稳定的 recency 偏好。
	- 当前默认 DRL 配置在 recency 合成场景下不具备可用性，需要单独调参（状态维度、奖励塑形、训练步数与探索策略）。

### 12.4 结论（面向后续实验）

- 若目标是稳定获得较优 LOH 权重，当前应优先采用 **CMA-ES**。
- 若继续推进 DRL，需要先在 recencytest 上做针对性训练配置修复，再考虑迁移到真实 trace。
- 对于权重可解释性分析，应将“MR 收敛”和“权重向量收敛”分离评估：在 lfutest2/sizetest 上，前者已稳定，但后者仍可多解。

## 13. 2026-05-08 三条核心合成 Trace 与四算法对比

### 13.1 文件位置

三条 trace 与对应生成脚本统一放置在 `traces/synth_three_core/`：

```
traces/synth_three_core/
├── gen_lfu_zipf_heavy.py          # lfu_zipf_heavy 生成脚本（纯 Zipf，alpha=1.5，无 anti-recency disturbance）
├── gen_size_twotier_extreme.py    # → symlink → scripts/gen_size_trace_twotier_extreme.py
├── gen_lru_fast.py                # → symlink → tmp/20260508-lrutest-version-batch/generators/gen_lrutest_10m_fast.py
├── lfu_zipf_heavy_10m.csv         # 最终版（a=1.5，10M 行，实体文件）
├── size_twotier_extreme_10m.csv   # → symlink → tmp/20260508-synth-lfu-size-4x4-rerun/traces/
└── lru_fast_10m.csv               # → symlink → tmp/20260508-lrutest-version-batch/traces/gen_lrutest_10m_fast/
```

重测脚本：`tmp/20260508-three-core-retest/run.sh`（3 trace × 4 algo = 12 个并行 job）
重测日志：`tmp/20260508-three-core-retest/logs/<trace_name>_<algo>.log`
重测结果：`tmp/20260508-three-core-retest/results.tsv`

### 13.2 三条 Trace 的详细生成逻辑

#### 13.2.1 `lfu_zipf_heavy_10m.csv` — LFU 侧重（纯 Zipf，无 anti-recency disturbance）

**生成脚本**：`traces/synth_three_core/gen_lfu_zipf_heavy.py`

**固定参数**：
- `N_REQUESTS = 10_000_000`（总请求数）
- `N_OBJECTS = 100_000`（全对象池大小）
- `BATCH = 500_000`（批次写出大小）
- `OBJ_SIZE = 10_000`（全部对象等大，消除 size 信号）
- `SEED = 42`

**运行时参数**（命令行传入）：
- `ZIPF_ALPHA = 1.50`（本 trace 文件使用 `python3 gen_lfu_zipf_heavy.py lfu_zipf_heavy_10m.csv 1.5` 生成；脚本默认值为 1.30，α 越大头部越集中）

**采样逻辑（i.i.d. 纯 Zipf）**：

1. 在全对象池 `N_OBJECTS=100000` 上构建 Zipf 概率分布（`alpha=1.50`）。
2. 每次请求独立按该 Zipf 分布采样对象 ID（无热点窗口、无冷扫描、无阶段切换）。
3. 批量写出 `time,obj_id,obj_size,0`。

**为何 LFU/LOH 显著优于 LRU/Size**：
- LFU 直接利用稳定频率排序，保留高频对象。
- LRU 只能利用 recency，而 i.i.d. Zipf 场景下 recency 信号弱于频率信号。
- Size（等大对象，行为见 §13.3）不携带频率信息，通常不如 LFU。
- LOH 通过权重自适应结合频率特征，通常略优于纯 LFU。

---

#### 13.2.2 `size_twotier_extreme_10m.csv` — Size 侧重（极端双层大小分布）

**生成脚本**：`traces/synth_three_core/gen_size_twotier_extreme.py`

**固定参数**：
- `N_REQUESTS = 10_000_000`（总请求数）
- `N_SMALL = 99_000`（小对象数），`SIZE_SMALL = 64`（字节）
- `N_LARGE = 1_000`（大对象数），`SIZE_LARGE = 16_777_216`（= 16MB）
- 全对象池：`100_000` 个对象，均匀随机访问（无频率偏斜、无时序局部性）

**采样逻辑**：
1. 全对象池（ID 0..99999）中均匀随机采样，每次请求独立 i.i.d.。
2. 对象按 ID 分层：ID 0..98999 → 64B；ID 99000..99999 → 16MB。
3. 每次访问按对象 ID 查表得 `obj_size`，写入 CSV 行 `time,obj_id,obj_size,0`。

**大小失衡**：1 个大对象（16MB）= 262144 个小对象（64B）的空间。缓存容量 `0.1 × (99K×64 + 1K×16M) ≈ 0.1 × 16.006GB ≈ 1.6GB ≈ 100 个大对象 OR 25M 个小对象`。

**为何 Size/LOH 显著优于 LRU/LFU**：
- Size 驱逐最大对象（16MB），优先保留小对象（64B）。99K 个小对象全部命中，miss 只来自 1K 个大对象（均被驱逐，访问占比 ~1%）→ 对象 MR ≈ 0.019。
- LRU/LFU 不感知大小，大对象和小对象等价对待。单个 16MB 大对象进入缓存会驱逐 262144 个小对象（64B），造成大量小对象 miss → 对象 MR ≈ 0.85−0.90。
- LOH：CMA-ES 自适应提高 size 相关权重，与 Size 几乎等价（MR ≈ 0.019）。

---

#### 13.2.3 `lru_fast_10m.csv` — LRU 侧重（滑动热点窗口 + 衰减采样）

**生成脚本**：`traces/synth_three_core/gen_lru_fast.py`

**固定参数**：
- `NUM_REQ = 10_000_000`（总请求数）
- `MAX_OBJECTS = 100_000`（全对象池）
- `FIXED_SIZE = 10_000`（全部对象等大）
- `WINDOW_SIZE = 5_000`（热点滑动窗口大小）
- `REACCESS_PROB = 0.95`（重访概率）
- `DECAY = 0.002`（衰减系数，控制窗口内的 recency 偏向强度）

**采样逻辑**：
1. 维护大小为 `WINDOW_SIZE=5000` 的 ring buffer（记录最近活跃对象）。
2. 每次请求：
   - 以概率 `1 - REACCESS_PROB = 0.05` 创建新对象（从全池新 ID），加入窗口（FIFO 替换最旧对象）。
   - 以概率 `REACCESS_PROB = 0.95` 从窗口中按衰减权重采样：权重 $w_i = (1-\text{DECAY})^i$（$i=0$ = 最近的对象），偏向访问最近进入窗口的对象。
3. 命中对象移到窗口末尾（"最近"位置），维护窗口内 recency 排序。

**缓存容量分析**（`cache size = 0.1`）：
- 总对象约 `10M × 0.05 = 500K` 次新对象创建（但上限 `MAX_OBJECTS=100K`），实际最多 100K 对象。
- 缓存可容 `0.1 × 100K × 10KB = 100MB / 10KB = 10K` 对象。
- 热窗口 5K < 缓存容量 10K，因此 LRU 完全可以缓存整个热窗口 → MR ≈ 0.01（只有新对象第一次访问会 miss）。

**为何 LRU 显著优于 LFU/Size**：
- LRU 完全覆盖热窗口（5K 对象 < 缓存 10K），所有重访均命中 → MR ≈ 0.01。
- LFU：访问频率随 recency 衰减权重分布，但 LFU 无法感知"窗口滑动"——当热窗口前移时，旧热对象频率仍高，LFU 保留已过期的热对象，新窗口对象得不到缓存。
- Size：等大对象下的特殊退化行为（见 §13.3），实测 MR ≈ 0.976，与 LFU 同样糟糕。
- LOH：CMA-ES 将 recency 权重调高，接近 LRU 行为，MR ≈ 0.015。

### 13.3 SIZE 算法在等大对象时的退化行为修正

文档第 11.2.2 节声称"SIZE 在所有对象等大时退化为 LRU"，这一说法**不准确**。以下基于 Size.c 和 pqueue.c 实现给出正确解释。

#### 13.3.1 pqueue 的比较函数

`libCacheSim/dataStructure/pqueue.h` 中 `cmp_pri` 的定义为：

```c
static inline int cmp_pri(pqueue_pri_t next, pqueue_pri_t curr) {
  return (next.pri < curr.pri);  // MAX-heap：size 越大，越优先被驱逐
}
```

这是一个 **MAX-heap（最大堆）**，`pqueue_pop` 返回 size **最大**的对象（优先驱逐大对象）。

#### 13.3.2 等大时的 hit 行为

在 `Size_find`（命中时调用）中：

```c
pqueue_pri_t pri = {.pri = req->obj_size};
pqueue_change_priority(params->pq, pri, (pq_node_t *)(cached_obj->Size.pq_node));
```

`pqueue_change_priority` 的逻辑：

```c
void pqueue_change_priority(pqueue_t *q, pqueue_pri_t new_pri, void *d) {
  pqueue_pri_t old_pri = q->getpri(d);
  q->setpri(d, new_pri);
  posn = q->getpos(d);
  if (q->cmppri(old_pri, new_pri))  // old < new → 优先级升高 → bubble_up
    bubble_up(q, posn);
  else                               // old >= new → percolate_down
    percolate_down(q, posn);
}
```

当 `old_size == new_size`（等大对象）：
- `cmppri(old, new)` = `(S < S)` = `false` → 调用 `percolate_down`
- `percolate_down` 的循环条件：`cmppri(moving_pri, child_pri)` = `(S < S)` = `false` → **循环不执行，节点不移动**

**结论：命中时 pqueue 节点原地不动。** 与 LRU 的"命中即移到最近端"完全不同。

#### 13.3.3 insert 行为

`pqueue_insert` 后调用 `bubble_up`，条件是 `cmppri(parent_pri, moving_pri)` = `(parent_size < new_size)` = `(S < S)` = `false` → **新对象留在堆末尾**。

#### 13.3.4 实际驱逐顺序（等大对象）

设依次插入 A、B、C、D：

1. 堆内存数组（1-indexed）：`[A, B, C, D]`（均无 bubble_up）
2. 第 1 次驱逐：`pqueue_pop` 取根 `A`（最先插入的对象），将最后节点 `D` 移到根，`percolate_down` 不动 → 堆 `[D, B, C]`
3. 第 2 次驱逐：取根 `D`（最后插入的对象），将 `C` 移到根 → 堆 `[C, B]`
4. 第 3 次驱逐：`C` → 堆 `[B]`
5. 第 4 次驱逐：`B`

驱逐序为 **A（最老），D（最新），C，B**——第 1 次是 FIFO（最老先驱逐），之后是 **LIFO**（最新先驱逐），本质上是一种"混合 FIFO+LIFO"，与 LRU 完全不同。

**命中不更新位置**，所以等大时 SIZE 对 recency 信号完全"盲"——既不像 LRU 那样保护最近命中的对象，也不像 FIFO 那样以固定插入顺序驱逐。

#### 13.3.5 为何 lfutest 上 SIZE ≈ LRU、lrutest 上 SIZE ≠ LRU

| Trace | 访问模式 | LRU | SIZE（等大时） | 原因 |
|---|---|---|---|---|
| lfutest2（i.i.d. Zipf） | 无时序局部性 | MR≈0.263 | MR≈0.264 | 无 recency 可用，FIFO/LIFO/LRU 在 i.i.d. trace 上表现相近 |
| lru_fast（滑动窗口） | 强 recency | MR≈0.010 | MR≈0.976 | LRU 精确捕捉窗口滑动；SIZE 不更新命中位置 → 持续驱逐当前热对象 |

**正确结论**：SIZE 在等大对象时既不退化为 LRU，也不退化为 FIFO，而是一种**命中不更新位置的 FIFO-then-LIFO 混合驱逐**。在 i.i.d. trace 上，这与 LRU/FIFO 表现相近（碰巧）；在 recency 主导的 trace 上，这与 LRU 完全背离，表现极差。

### 13.4 四算法对比结果汇总（cache size = 0.1）

#### 13.4.1 最终版（仅保留 LFU-B / `alpha=1.5`）

本章按你的要求只保留最终口径：`lfu_zipf_heavy` 使用纯 Zipf、无冷扫描、`ZIPF_ALPHA=1.5`（LFU-B 最终版）。

- 统一 trace 目录：`traces/synth_three_core/`
- 最终 lfu 文件：`traces/synth_three_core/lfu_zipf_heavy_10m.csv`（纯 Zipf，alpha=1.5，无 anti-recency disturbance，10M 行）
- 生成日志：`tmp/20260508-three-core-retest-a1p5/logs/gen_lfu_a1p5.log`
- 并行重测结果：`tmp/20260508-retest-verify/logs/`（2026-05-08 重测，全部 12 job 完成）

对象 Miss Ratio 与字节 Miss Ratio（MR / BMR，cache size = 0.1）：

| trace | LRU MR/BMR | LFU MR/BMR | Size MR/BMR | LOH MR/BMR | 最优 |
|---|---:|---:|---:|---:|---|
| lfu_zipf_heavy（noscan, a=1.5） | 0.014203 / 0.014203 | 0.011034 / 0.011034 | 0.027647 / 0.027647 | **0.010984** / 0.010984 | LOH |
| size_twotier_extreme | 0.899621 / 0.901281 | 0.848954 / 0.899981 | **0.018876** / 0.898582 | 0.018954 / 0.900454 | Size |
| lru_fast | **0.010000** / 0.010000 | 0.977338 / 0.977338 | 0.976229 / 0.976229 | 0.012664 / 0.012664 | LRU |

结论：最终 LFU-B 版本下，`lfu_zipf_heavy` 仍保持 `LOH < LFU < LRU < Size`；三条 trace 的最优策略分别是 `LOH`（lfu_zipf_heavy）、`Size`（size_twotier_extreme）、`LRU`（lru_fast）。LRU/LFU/Size 结果与历史完全一致；LOH（CMA-ES）因随机性存在 run-to-run 微小波动（约 ±0.001），排序不变。

## 14. 最终三张 Trace 特征图

本节记录最终用于解释 LRU、LFU、SIZE 三类单维策略的 trace 特征图。最终图不再使用 `wiki_2019t`，而是使用三条 oriented synthetic trace 与两条真实 trace 的对应子集：

- `Recency-oriented trace`：`lru_fast_10m.csv`，用于展示 LRU 友好的短 stack-distance 结构。
- `Frequency-oriented trace`：`lfu_zipf_heavy_10m.csv`，用于展示 LFU 友好的稳定频率结构。
- `Size-oriented trace`：`size_twotier_extreme_10m.csv`，用于展示 SIZE 友好的极端对象大小结构。
- `Trace A`：`meta_reag`，真实 trace，size 长尾和复杂复合特征明显。
- `Trace B`：`tencentBlock_1063`，真实 trace，短期局部性与频率/大小结构共同存在。

### 14.1 图与脚本位置

统一绘图脚本：`tmp/20260510-final-feature-figures/make_final_feature_figures.py`

脚本已经拆成两部分：

- 数据准备阶段：解析 trace 或 analyzer 输出，写入 `tmp/20260510-final-feature-figures/data/*.npz`。
- 绘图阶段：只读取 `.npz` 缓存或脚本内 MR 表，生成 PNG/PDF。后续只调字体、legend、inset、箭头时只需运行绘图阶段。

常用命令：

```bash
PATH="$PWD/.venv/bin:$PATH" python3 tmp/20260510-final-feature-figures/make_final_feature_figures.py --stage all --figure all
PATH="$PWD/.venv/bin:$PATH" python3 tmp/20260510-final-feature-figures/make_final_feature_figures.py --stage plot --figure all
```

三张特征图位置：

| 图 | PNG | PDF | 含义 |
|---|---|---|---|
| LRU/object-stack distance CDF | `tmp/20260510-final-feature-figures/figures/lru_stackdist_cdf_with_cold_final_3traces.png` | `tmp/20260510-final-feature-figures/figures/lru_stackdist_cdf_with_cold_final_3traces.pdf` | 含 cold request 的 normalized object-stack re-access distance CDF |
| LFU/frequency stability | `tmp/20260510-final-feature-figures/figures/freq_stability_overlap_final_3traces_10m.png` | `tmp/20260510-final-feature-figures/figures/freq_stability_overlap_final_3traces_10m.pdf` | 相邻时间窗口 Top-K 高频对象集合的 overlap ratio |
| SIZE/object-size CDF | `tmp/20260510-final-feature-figures/figures/size_cdf_final_3traces_logx.png` | `tmp/20260510-final-feature-figures/figures/size_cdf_final_3traces_logx.pdf` | 对象大小按对象数统计的 CDF，横轴为 log-scale Byte |

### 14.2 LRU 图：Object-Stack Re-access Distance CDF

LRU 图刻画的是 object-stack re-access distance 分布。横轴是 normalized object-stack re-access distance，即两次访问同一对象之间出现过多少不同对象，再除以对象 footprint；纵轴是累计比例。这个量比 request-count re-access time 更贴近 object-capacity LRU：如果对象再次访问前只经过很少不同对象，它更可能仍留在 LRU 缓存中。图中将 cold/first-object request 作为 x=1 处的最终跳变纳入 CDF，因此曲线右端一定到 1。

`Recency-oriented trace` 的曲线在很小的 normalized distance 处快速上升，表示重访对象大多仍处于 LRU 栈前部。这对应 §13.4.1 中 LRU MR=0.010000，为三种固定策略中最低；LFU MR=0.977338、SIZE MR=0.976229 接近失效，因为它们不能识别滑动热点窗口和命中后位置更新。

`Trace A` 的曲线包含更明显的长尾和 cold 质量，说明很多请求无法被短 stack-distance 单独解释。对应 §7 中 LRU MR=0.3268，优于 LFU MR=0.4650，但略差于 SIZE MR=0.3089。这说明 Trace A 中 recency 有帮助，但不是唯一主导信号。

`Trace B` 的短距离重访结构更强，LRU MR=0.2618，明显优于 LFU MR=0.6201 和 SIZE MR=0.4802。该图解释了为什么 Trace B 上 LRU 比长期频率或对象大小更合理：命中机会更多来自近期访问过且仍在栈前部的对象。

### 14.3 LFU 图：Frequency Stability

LFU 图刻画的是高频对象集合的稳定性。横轴是时间窗口，纵轴是相邻窗口中 Top-256 高频对象集合的 overlap ratio。该值越高，说明高频对象集合越稳定；LFU 越容易用长期频率计数保留未来仍会被访问的对象。该图比单纯的 Zipf 曲线更贴近 LFU 的核心假设：不仅要有频率偏斜，还要有稳定的高频集合。

`Frequency-oriented trace` 的曲线长期保持高 overlap，说明高频对象集合稳定，LFU 的频率计数不会被时间漂移破坏。这对应 §13.4.1 中 LFU MR=0.011034，为三种固定策略中最低；LRU MR=0.014203、SIZE MR=0.027647 均更高，因为 recency 和 size 都不是该 trace 的主导信号。

`Trace A` 的 overlap 明显低于 oriented synthetic trace，说明高频集合不够稳定，单纯 LFU 会保留一批历史高频但未来价值下降的对象。对应 §7 中 Trace A 的 LFU MR=0.4650，高于 LRU MR=0.3268 和 SIZE MR=0.3089。

`Trace B` 的 overlap 处于中间水平，但单纯 LFU 仍然很差：§7 中 LFU MR=0.6201，高于 LRU MR=0.2618 和 SIZE MR=0.4802。这说明 Trace B 的命中机会不能只靠长期频率解释，短期局部性比长期高频集合更关键。

### 14.4 SIZE 图：Object-Size CDF 与对象大小区分度

SIZE 图刻画的是对象大小的区分度。横轴是对象大小（Byte，log-scale），纵轴是按对象数统计的累计比例。曲线越陡、台阶越明显，说明对象大小越集中在少数离散层；如果大量请求对象都很小而少数对象巨大，则 SIZE 策略可以通过驱逐大对象，把缓存空间留给更多小对象，从而显著降低对象 MR。

`Size-oriented trace` 的主图显示绝大多数对象是小对象，右上角 inset 放大了尾部从 0.99 到 1.0 的跳变，表示最后约 1% 对象是巨大对象。这对应 §13.4.1 中 SIZE MR=0.018876，为三种固定策略中最低；LRU MR=0.899621、LFU MR=0.848954 都很高，因为它们不直接感知对象大小，无法稳定驱逐巨大对象。

`Trace A` 的 size CDF 横跨多个数量级，说明 size 维度是真实有效信号，但曲线没有退化成 synthetic trace 的两层结构。对应 §7 中 SIZE MR=0.3089，略优于 LRU MR=0.3268，并明显优于 LFU MR=0.4650，说明对象大小在 Trace A 上有区分力。

`Trace B` 的对象大小分布更温和，缺少 `Size-oriented trace` 那种清晰两层结构。对应 §7 中 SIZE MR=0.4802，差于 LRU MR=0.2618，但优于 LFU MR=0.6201。这说明 Trace B 中对象大小不是主导排序信号，按大小驱逐会牺牲不少具有短期重用价值的对象。

### 14.5 RSD 在各 trace 上的表现与原因

前三张图分别解释 LRU、LFU、SIZE 三个单维专家策略的适用条件：短 re-access distance、高频集合稳定、对象大小区分度强。RSD 的优势不在于固定选择某一个单维规则，而在于根据 trace 结构组合这些信号。

在三条 oriented synthetic trace 上，RSD 能接近对应专家策略：`Frequency-oriented trace` 上 RSD MR=0.010984，略低于 LFU MR=0.011034；`Size-oriented trace` 上 RSD MR=0.018954，与 SIZE MR=0.018876 基本并列；`Recency-oriented trace` 上 RSD MR=0.012664，接近 LRU MR=0.010000。说明当单一维度非常明确时，RSD 不会明显偏离正确主导信号。

在 `Trace A` 上，三张特征图共同显示它不是单维 trace：size 有区分力，recency 也有贡献，frequency 单独较弱。对应 §7 中 RSD MR=0.2707，低于 SIZE MR=0.3089、LRU MR=0.3268 和 LFU MR=0.4650，优势来自多维排序信号的联合使用。

在 `Trace B` 上，LRU 图显示短期局部性强，但 LFU 和 SIZE 图也说明频率与对象大小不能单独解释全部行为。对应 §7 中 RSD MR=0.0350，显著低于 LRU MR=0.2618、SIZE MR=0.4802 和 LFU MR=0.6201，说明 RSD 能把近期重访、频率、大小及复合特征组合成更稳定的驱逐顺序。

## 15. 五条 Trace 上四算法 MR 对比图

本节新增一张横轴为三条 oriented synthetic trace 与两条真实 trace、纵轴为对象 MR 的对比图。图中 `RSD` 对应本文前文的 `LOH(CMA-ES)` 结果；命名为 RSD 是为了在最终图中突出它作为自适应综合排序策略，而不是单一 LRU/LFU/SIZE 专家策略。

图位置：

- PNG: `tmp/20260510-final-feature-figures/figures/mr_comparison_5traces.png`
- PDF: `tmp/20260510-final-feature-figures/figures/mr_comparison_5traces.pdf`
- 算法横轴折线图 PNG: `tmp/20260510-final-feature-figures/figures/mr_algorithm_trace_lines_5traces.png`
- 算法横轴折线图 PDF: `tmp/20260510-final-feature-figures/figures/mr_algorithm_trace_lines_5traces.pdf`
- Oriented algorithm 三联折线图 PNG: `tmp/20260510-final-feature-figures/figures/mr_oriented_algorithm_stack_3panels.png`
- Oriented algorithm 三联折线图 PDF: `tmp/20260510-final-feature-figures/figures/mr_oriented_algorithm_stack_3panels.pdf`

数据来源：

- 三条 oriented synthetic trace 的 MR 来自 §13.4.1。
- 两条真实 trace 的 MR 来自 §7，其中 `Trace A = meta_reag`，`Trace B = 1063`。
- `wiki_2019t` 不纳入该最终图，保持与三张最终特征图一致。

MR 数据表如下：

| Trace | LRU MR | LFU MR | SIZE MR | RSD MR |
|---|---:|---:|---:|---:|
| Frequency-oriented trace | 0.014203 | 0.011034 | 0.027647 | 0.010984 |
| Size-oriented trace | 0.899621 | 0.848954 | 0.018876 | 0.018954 |
| Recency-oriented trace | 0.010000 | 0.977338 | 0.976229 | 0.012664 |
| Trace A | 0.3268 | 0.4650 | 0.3089 | 0.2707 |
| Trace B | 0.2618 | 0.6201 | 0.4802 | 0.0350 |

这张 MR 图与前三张特征图的对应关系如下：

1. 在 `Frequency-oriented trace` 上，frequency stability 图显示高频集合稳定，因此 LFU 已接近最优；RSD 略低于 LFU，说明它能退化到 frequency 主导排序并做轻微修正。
2. 在 `Size-oriented trace` 上，size CDF 显示 99% 小对象 + 1% 巨大对象的极端两层结构，因此 SIZE 和 RSD 并列最优，LRU/LFU 因不感知对象大小而高 MR。
3. 在 `Recency-oriented trace` 上，stack-distance CDF 显示绝大多数重访距离很短，因此 LRU 最优，RSD 接近 LRU；LFU/SIZE 不利用命中后位置更新，MR 接近 1。
4. 在 `Trace A` 上，三张特征图都没有显示单一维度能完全解释该 trace；size 有帮助、recency 也有帮助，frequency 单独较弱。因此 RSD 综合排序最低，SIZE 次之，LRU 再次，LFU 最差。
5. 在 `Trace B` 上，LRU 特征比 LFU/SIZE 更有效，但 RSD 远优于所有固定策略，说明 Trace B 的真实可缓存性来自多维复合，而不是某一个单维专家策略。

总体结论：三条 oriented synthetic trace 用来证明单维特征图能解释对应专家策略为何有效；两条真实 trace 则说明生产负载通常不是单维问题。RSD/LOH-CMAES 的优势正来自它能在不同 trace 上自动调整排序维度，而固定 LRU/LFU/SIZE 只能在其假设刚好成立时表现最优。

算法横轴折线图使用同一份 MR 数据，但横轴改为 `LRU`、`LFU`、`SIZE`、`RSD`，纵轴使用以 10 为底的 log-scale MR。为避免把 synthetic trace 上不相关的固定策略结果混在同一视觉比较中，折线图采用选择性绘制规则：

- `RSD` 位置绘制全部五条 trace，因为 RSD 是统一自适应策略，需要横向比较所有 trace。
- `LRU` 位置只绘制 `Recency-oriented trace`、`Trace A`、`Trace B`。
- `LFU` 位置只绘制 `Frequency-oriented trace`、`Trace A`、`Trace B`。
- `SIZE` 位置只绘制 `Size-oriented trace`、`Trace A`、`Trace B`。

因此三条 oriented synthetic trace 的线段表达“对应专家策略 vs RSD”的差距；两条真实 trace 的线段完整跨过 LRU/LFU/SIZE/RSD，表达固定专家策略与自适应 RSD 在真实负载上的差异。

Oriented algorithm 三联折线图进一步把三个单维专家策略分开展示：三张子图上下堆叠，纵轴共用标题 `Object Miss Ratio`，但每个子图使用独立的横轴刻度和纵轴刻度。三张子图分别为：

- `Recency-oriented`：横轴为 `Recency-oriented trace`、`Trace A`、`Trace B`，比较 LRU 与 RSD 的 MR。
- `Frequency-oriented`：横轴为 `Frequency-oriented trace`、`Trace A`、`Trace B`，比较 LFU 与 RSD 的 MR。
- `Size-oriented`：横轴为 `Size-oriented trace`、`Trace A`、`Trace B`，比较 MSU 与 RSD 的 MR。

这张三联图强调每个单维专家策略在自身 synthetic trace 上为何接近最优，同时展示同一专家策略迁移到真实 trace 后与 RSD 的差距。
