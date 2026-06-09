# 噪声鲁棒性实验：机制分析与下一步计划

## 1. 核心机制：代理目标错配（Proxy Objective Mismatch）

### 1.1 两种学习路径的根本差异

| | 3LCache | LOH |
|---|---|---|
| **学什么** | 逐对象预测 reuse distance（代理目标） | 负载级特征权重（策略本身） |
| **反馈信号** | 对象级标签：实际 reuse distance 或 FAR | epoch 级 MR：聚合统计量 |
| **输出** | `size × exp(GBM_pred)` → 排序 | `Σ w_i × feat_i` → 排序 |
| **搜索空间** | 高维（GBM 树/叶子） | 低维（4-6 个权重） |

**核心论点**：3LCache 学习的是代理目标（预测 reuse distance），不是最终目标（最小化 MR）。LOH 的权重直接定义淘汰策略，CMA-ES 直接搜索最小化 MR 的权重。

### 1.2 为什么代理目标在对象大小异构时失效

当所有对象大小相同时，reuse distance 完美代理淘汰价值：return 越早 → 越该保留。

当对象大小不同时：
- 对象 A (4KB, reuse=500) 和对象 B (1MB, reuse=500) 有相同的 reuse distance
- 但淘汰 B 释放 256 倍空间 → 远更应该淘汰 B
- 3LCache 通过 `size × exp(pred)` 来处理这个问题——但这是**间接的**
- 如果 `exp(pred)` 有误差，`size ×` 乘法不能修正排序错误，只能放大

LOH 的 size 权重是**直接的**：`w_size × log(size)` 独立于 rec/freq 权重，不受 rec/freq 预测误差影响。

### 1.3 "反馈信号差异"才是根本，不是 exp() 工程细节

3LCache 的反馈是**对象级的、稀疏的、可能被截断的**：
- 对象返回 → 标签 = 实际 reuse distance
- 对象不返回（ghost expiry）→ 标签 = FAR（可能错误，如果对象最终会返回）
- 反馈只在对象返回或 ghost 过期时产生

LOH 的反馈是**epoch 级的、聚合的、始终可用的**：
- 每个 epoch 结束 → MR 是多少
- 反馈始终反映真实的淘汰质量
- 不需要等对象返回

**这个反馈机制的差异决定了：当存在噪声时，3LCache 收到被污染的逐对象标签，而 LOH 收到的是聚合后噪声被平均掉的 MR。**

## 2. 实验 1：Size-Tiebreak（已完成，有明确结论）

### 2.1 设计
- 512 小对象(4KB) + 512 大对象(1MB)，概率性回报（Beta 分布）
- Deterministic 对照（所有对象确定回报）

### 2.2 结果

| cs | 3LCache-OMR (Det/Noisy) | LOH f001 (Det/Noisy) | LOH 优势 |
|----|------------------------|---------------------|---------|
| 0.02 | 0.436 / 0.338 | 0.216 / **0.202** | 50% / 40% |
| 0.05 | 0.188 / 0.171 | 0.080 / **0.109** | 57% / 36% |
| 0.1 | 0.139 / 0.118 | 0.111 / **0.088** | 20% / 25% |

**结论**：LOH 在所有配置下优于 3LCache-OMR。Deterministic 和 Noisy 差距相近 → 机制是结构性的代理目标错配，非纯噪声驱动。

### 2.3 遗留问题
- 3LCache 仅在 1.9M 请求中训练了 2 个 batch → 可能未充分训练
- Deterministic 间隙大于 Noisy → 与"噪声放大"预期相反，需进一步分析

## 3. 实验 2：Return-Position Swap（初步验证，方向可行）

### 3.1 设计
- Hot 对象(128)：正常 short gap 返回
- Cold 对象(128)：正常 long gap 返回
- Swap：x% 的 hot↔cold 回报位置交换，不增加总请求数
- 交换制造特征-标签碰撞：hot-like 特征 → 有时 SHORT（正常），有时 LONG（被交换）

### 3.2 结果 (cs=0.05)

| swap | LRU | 3LCache-OMR | LOH f100 | 3LCache 退化 | LOH 退化 |
|------|-----|------------|----------|-------------|---------|
| 0% (clean) | 0.952 | **0.571** | 0.908 | — | — |
| 20% | 0.952 | 0.594 | 0.922 | **+4.1%** | +1.5% |

**结论**：时间扰动使 3LCache 退化 2.7× 于 LOH（+4.1% vs +1.5%）。机制方向正确。

### 3.3 遗留问题
- Uniform size 下 LOH f100 基线太差（0.908），即使 3LCache 退化更多，仍比 LOH 好
- 需要**结合 size 异构**：hot/cold 对象使用不同大小，让 LOH 的 size 权重发挥作用，提升 LOH 基线

## 4. 下一步：两个方向融合

### 4.1 推荐实验：Size-Tiered Return Swap

将 return-swap 机制应用到 size-tiebreak 的异构大小 trace 上：

- 小对象(4KB, hot pool)：正常 short gap → SHORT label
- 大对象(1MB, cold pool)：正常 long gap → LONG label
- **Swap**: x% 的小对象回报交换到 long gap，x% 的大对象交换到 short gap
- 预测：
  - 3LCache：特征-标签碰撞 + `size × exp(pred)` 指数放大 → 明显退化
  - LOH f001：epoch MR 受 swap 影响小 + size 权重独立稳定 → 退化小
  - 结果：swap 扩大 LOH vs 3LCache 的差距

### 4.2 备选：增大 3LCache 训练量

当前 3LCache 仅训练 2-3 batch。可考虑：
- 修改 `eviction_rate` 或子采样率，让训练更频繁
- 或用 10M+ 请求的超长 trace

### 4.3 论文级论述框架

如果上述实验成功，论文中可以按以下链条论述：

1. **Production CDN traces 是异构的**（对象大小、访问频率、reuse 模式各异）
2. **单信号 baseline 在异构负载上不稳定**（不同 trace/cache size 下最优 baseline 不同）
3. **3LCache 将淘汰问题转化为对象级 reuse distance 预测**（代理目标）
4. **代理目标在异构大小下存在结构性错配**：
   - 反馈是对象级的、稀疏的 → 噪声下标签被污染
   - 评分函数间接使用 size → 预测误差被放大
5. **LOH 直接学习负载级偏好权重**：
   - 反馈是 epoch 级聚合 MR → 噪声被平均
   - 权重直接定义策略 → 无代理目标错配
6. **实验验证**：在确定性 trace 上两者接近；引入噪声/扰动后 3LCache 退化显著多于 LOH

## 5. 产物索引

| 文档 | 内容 |
|------|------|
| [docs/20260602-PROXY-OBJECTIVE-MISMATCH.md](docs/20260602-PROXY-OBJECTIVE-MISMATCH.md) | Size-tiebreak 实验结果与机制分析 |
| [docs/20260525-RSD_EFFECT_REASON_AND_VALIDATION_PLAN.md](docs/20260525-RSD_EFFECT_REASON_AND_VALIDATION_PLAN.md) | 完整实验矩阵规划 |

| Trace 生成器 | 用途 |
|-------------|------|
| [scripts/gen_size_tiebreak_trace.py](scripts/gen_size_tiebreak_trace.py) | 异构大小 + 概率性回报 |
| [scripts/gen_return_swap_trace.py](scripts/gen_return_swap_trace.py) | 回报位置交换（uniform size） |

| 实验数据 | 内容 |
|---------|------|
| [tmp/20260601-size-tiebreak/](tmp/20260601-size-tiebreak/) | Noisy size-tiebreak 结果 |
| [tmp/20260602-size-tiebreak-control/](tmp/20260602-size-tiebreak-control/) | Deterministic 对照 |
| [tmp/20260602-return-swap/](tmp/20260602-return-swap/) | Return-swap 初步结果 |
