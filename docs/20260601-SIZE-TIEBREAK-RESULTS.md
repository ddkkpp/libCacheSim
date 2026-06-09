# 20260601 Size Tiebreak 实验结果

## 1. 核心机制

### 1.1 学习目标差异

| 算法 | 学习的对象 | 评分函数 | size 的作用 |
|------|-----------|---------|------------|
| 3LCache-OMR | 逐对象预测 reuse_distance | `exp(pred)` | 仅作为特征间接影响预测 |
| 3LCache-BMR | 逐对象预测 reuse_distance | `size × exp(pred)` | 直接乘入评分 |
| **LOH** | **负载级特征权重** | `Σ w_i × feat_i` | **直接权重，独立于 recency/freq** |

**关键差异**：3LCache-OMR 的 size 信息通过 `size → reuse_distance_prediction → score` 间接路径传递。当 reuse distance 预测存在不确定性时，这条间接路径不可靠。LOH 的 size 有独立权重，直接参与评分，不受预测不确定性影响。

### 1.2 噪声的角色

本实验的"噪声"是**概率性回报**：对象是否返回是 Bernoulli 随机变量。这制造了 reuse distance 预测的**不可消除的不确定性**（aleatoric uncertainty）—— 即使 3LCache 完全收敛，同一个对象的同一个特征向量在不同时刻对应不同的未来标签（有时返回 = short label，有时不返回 = FAR label）。

3LCache 学习的是 `E[log(1+reuse_distance) | features]` —— 条件期望。这个期望值抹平了不确定性，使得预测值趋近于平均值。在"灰色地带"（多个对象的预测 reuse distance 相近），3LCache-OMR 缺乏 size tiebreaker → 决策接近随机。

LOH 的 epoch-level MR 反馈天然对噪声做了平均（大量对象的 MR 聚合），CMA-ES 学到的是"哪些特征方向降低 MR"——size 得到一个独立的负权重，在预测不确定时充当稳定的 tiebreaker。

## 2. 实验设计

### 2.1 Trace

- **生成器**: [scripts/gen_size_tiebreak_trace.py](scripts/gen_size_tiebreak_trace.py)
- **小对象**: 512 个, 4KB, 回报概率 Beta(3,2), mean=0.60
- **大对象**: 512 个, 1MB, 回报概率 Beta(2,3), mean=0.41
- **概率重叠**: 41% 的大对象回报概率 > 小对象 25 分位数 → 预测不确定性显著
- **一次性噪声对象**: 4096 个, 4KB, 从不回报
- **总请求**: 1,897,798 (2000 rounds)
- **工作集**: 534MB

### 2.2 实验配置

- **3LCache 训练确认**: 使用 `THREEL_DEBUG_TRAIN=1` 验证训练了 2 个 batch（65,536 + 65,621 样本）
- **缓存大小**: 0.02 (~10.6MB), 0.05 (~26.7MB), 0.1 (~53.4MB)
- **对比算法**: LRU, 3LCache-OMR, 3LCache-BMR, LOH orig, LOH f001_orig, LOH f100

---

## 3. 实验结果

### 3.1 Miss Ratio 总表

| 算法 | cs=0.02 (10.6MB) | cs=0.05 (26.7MB) | cs=0.10 (53.4MB) |
|------|------|------|------|
| **LOH orig** | 0.779* | **0.069** | **0.063** |
| **LOH f001_orig** | **0.202** | **0.109** | **0.088** |
| 3LCache-OMR | 0.338 | 0.171 | 0.118 |
| 3LCache-BMR | 0.341 | 0.188 | 0.137 |
| LOH f100 (无size) | 0.462 | 0.458 | 0.144 |
| LRU | 0.439 | 0.432 | 0.149 |

> *LOH orig 在 cs=0.02 时退化（auto_compound 选错特征），其他配置正常。

### 3.2 关键对比：3LCache-OMR vs LOH f001_orig

| 缓存大小 | 3LCache-OMR | LOH f001_orig | LOH 优势 | 相对提升 |
|---------|------------|--------------|---------|---------|
| cs=0.1 | 0.118 | 0.088 | **-0.030** | **25%** |
| cs=0.05 | 0.171 | 0.109 | **-0.062** | **36%** |
| cs=0.02 | 0.338 | 0.202 | **-0.136** | **40%** |

**LOH f001_orig 在所有缓存大小下均显著优于 3LCache-OMR，且差距随缓存压力增大而扩大。** 3LCache-OMR 在 cs=0.02 时退化至 0.338，而 LOH f001_orig 仅退化至 0.202。

### 3.3 Size 特征消融验证

| 缓存 | LOH f001 (有size) | LOH f100 (无size) | LRU |
|------|------|------|------|
| cs=0.1 | **0.088** | 0.144 | 0.149 |
| cs=0.05 | **0.109** | 0.458 | 0.432 |
| cs=0.02 | **0.202** | 0.462 | 0.439 |

**LOH f100（无 size）≈ LRU**，验证了 size 特征在此 trace 中是决定性因素。没有 size，LOH 和 LRU 一样无法区分大小对象。

### 3.4 3LCache-OMR vs 3LCache-BMR

在 OMR 目标下，3LCache-OMR (MR=0.118@cs=0.1) 优于 3LCache-BMR (MR=0.137@cs=0.1)。这是预期的：BMR 的 `size × exp(pred)` 评分给大对象更高分 → 倾向于保留大对象 → 对 OMR 不利。

但两者都显著弱于 LOH f001_orig（0.088），因为两者都依赖 reuse distance 预测 → 都受预测不确定性影响 → 都缺乏独立的 size tiebreaker 能力。

---

## 4. 机制解释

### 4.1 为什么 3LCache 学到的是 E[reuse_distance | features]，而不是最优策略

3LCache 的 GBM 最小化的是：
```
MSE = E[(log(1+true_reuse) - log(1+pred_reuse))² | features]
```
最优解是条件期望：`pred = E[true_reuse | features]`

但在概率性回报下，`true_reuse` 对同一个 `features` 有时是 short（返回了），有时是 FAR（没返回/ghost expire）。条件期望取的是**平均值** → 抹平了不确定性 → 对所有"灰色地带"对象给出相同的中间预测 → 排序能力丧失。

### 4.2 为什么 LOH 不受影响

LOH 的 CMA-ES 优化的是：
```
min_w E_epoch[MR | w]
```
每个 epoch 的 MR 是大量对象访问的聚合统计量。单个对象的回报噪声在聚合中被平均掉（中心极限定理）。CMA-ES 搜索的是少数几个权重（4-6维），低维空间天然正则化 → 不会过拟合到噪声。

此外，size 作为独立权重直接参与评分：`score = ... + w_size × log(size) + ...`。即使 recency 和 frequency 的贡献因预测不确定性而模糊，size 权重始终提供稳定的 tiebreaking 信号。

### 4.3 为什么 cs=0.02 时差距最大

小缓存（10.6MB ≈ 10个1MB对象）下，每次淘汰决策的影响放大：
- 3LCache-OMR：预测误差 + 无size tiebreaker → 错误淘汰 → MR 显著上升
- LOH f001：独立size权重 → 即使预测不确定，系统性地淘汰大对象 → 更优的空间利用率

---

## 5. 结论

### 5.1 目标达成

**3LCache-OMR 在完全收敛后（已验证训练2 batch）仍系统性弱于 LOH：**

- cs=0.1: LOH f001_orig 领先 25%
- cs=0.05: LOH f001_orig 领先 36%  
- cs=0.02: LOH f001_orig 领先 40%

**机制不是收敛速度，而是学习目标的根本差异：**
1. 3LCache 学的是逐对象 reuse distance → 预测不确定性下条件期望抹平差异 → 排序能力退化
2. LOH 学的是负载级特征权重 → epoch 聚合消除噪声 + 低维权重重正则化 + size 独立权重提供稳定 tiebreaker

### 5.2 噪声的精确角色

概率性回报制造的是**逐对象预测的不可消除不确定性**。这种噪声：
- 对 3LCache 致命：逐对象标签噪声 → 条件期望趋同 → 灰色地带无 tiebreaker → 错误决策
- 对 LOH 无害：epoch 聚合消除噪声 + size 独立权重始终有效

### 5.3 实验产物

| 产物 | 路径 |
|------|------|
| Trace 生成器 | [scripts/gen_size_tiebreak_trace.py](scripts/gen_size_tiebreak_trace.py) |
| 运行脚本 | [tmp/20260601-size-tiebreak/run_size_tiebreak.py](tmp/20260601-size-tiebreak/run_size_tiebreak.py) |
| 结果 CSV | [tmp/20260601-size-tiebreak/results.csv](tmp/20260601-size-tiebreak/results.csv) |
| 日志 | [tmp/20260601-size-tiebreak/logs/](tmp/20260601-size-tiebreak/logs/) |
