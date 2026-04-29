# FSB (Feature Selection Bandit) 策略详解

**日期**: 2026-04-14
**相关代码**: `libCacheSim/cache/eviction/LOH.c` (第 236~269 行定义, 第 5109~5310 行核心函数)
**相关评测**: `docs/20260414-FSB_V2_BROAD_EVALUATION.md`

---

## 1. 概述

FSB 是一个**在线特征组合选择器**，在缓存 warmup 完成后自动从 8 种 compound feature 配置中选出最优的一种，然后交给 CMA-ES 做权重优化。

目标：替代 AUTO_COMPOUND (AC) 的启发式判断（通过 r1/r2 统计指标），改用**实际运行效果**做决策。

---

## 2. 8 个 Arms

每个 arm 是一种 feature 开关组合 `f{FR}{FS}{RS}`：

| arm index | config | FR (freq×rec) | FS (freq÷size) | RS (rec×size) |
|-----------|--------|:---:|:---:|:---:|
| 0 | f000 | OFF | OFF | OFF |
| 1 | f001 | OFF | OFF | ON  |
| 2 | f010 | OFF | ON  | OFF |
| 3 | f011 | OFF | ON  | ON  |
| 4 | f100 | ON  | OFF | OFF |
| 5 | f101 | ON  | OFF | ON  |
| 6 | f110 | ON  | ON  | OFF |
| 7 | f111 | ON  | ON  | ON  |

- **基础 3 维**（rec, freq, size）始终开启，权重固定 0.5
- 开启的 compound 特征权重 0.5，关闭的权重 0.0
- arm index 编码：`bit2=FR, bit1=FS, bit0=RS`

---

## 3. 关键参数

| 参数 | 环境变量 | 默认值 | 含义 |
|------|---------|--------|------|
| block_size | `LOH_FSB_BLOCK_SIZE` | n_obj/4（最低 10000） | 每个 arm 每次试探的请求数 |
| min_rounds | `LOH_FSB_MIN_ROUNDS` | 2 | 最少完整轮数（不计 warmup） |
| max_rounds | `LOH_FSB_MAX_ROUNDS` | 5 | 最多轮数，到达后强制锁定 |
| warmup_rounds | `LOH_FSB_WARMUP_ROUNDS` | 0 | 预热轮数（不计入统计） |
| ucb_c | `LOH_FSB_UCB_C` | 1.0 | UCB 探索系数 |

### n_obj 的确定

`n_obj` 不是人为设定的，而是 **cache warmup 完成时缓存中的实际对象数量**。

- 触发条件（`LOH.c:7193`）：`cache_get_occupied_byte_default(cache) >= cache->cache_size`（缓存字节占满 ≥100%）
- 此时：`n_obj = cache->get_n_obj(cache)` — 即缓存中存储的对象总数
- 然后：`block_size = max(n_obj / 4, 10000)`

例如 cache_size = 总数据的 10%，对象大小均匀时 n_obj ≈ 总对象数 × 10%。

---

## 4. 完整执行流程

### 4.1 触发

1. Cache warmup 完成（缓存字节占满）
2. 如果 `LOH_FSB=1`：
   - 禁用 auto_compound，启用 compound 模式
   - 计算 block_size = max(n_obj/4, 10000)
   - 初始化 8 个 arm 的配置
   - 应用 arm 0（f000），开始第 0 轮

### 4.2 每轮 (round) 流程

一轮 = **依次试探全部 8 个 arm**，每个 arm 运行 block_size 个请求。

```
Round k:
  arm 0: 运行 block_size 个请求 → 记录 block_MR[0]
  arm 1: 运行 block_size 个请求 → 记录 block_MR[1]
  ...
  arm 7: 运行 block_size 个请求 → 记录 block_MR[7]
  → 轮结束处理
```

**每个 arm 在每轮内都被试探恰好 1 次**，所以所有 arm 的累计 pull 次数始终相等。

### 4.3 去趋势（轮结束处理）

缓存的 miss ratio 会随时间自然变化（热点迁移、缓存逐渐稳定等）。如果直接比较 arm 0（在轮开始时跑的）和 arm 7（轮末尾跑的）的绝对 MR，会有时序偏差。

去趋势方法：

$$\text{mean}_k = \frac{1}{8} \sum_{i=0}^{7} MR_{k,i}$$

$$\text{relative\_MR}_{k,i} = MR_{k,i} - \text{mean}_k$$

只有 relative MR 参与 arm 排名。这消除了轮内的全局 MR 漂移，保留了 **config 之间的相对优劣**。

如果当前轮是 warmup 轮（`round < warmup_rounds`），则仅打印不计入统计。

### 4.4 累计统计更新

每个 arm 维护两个累计量：

$$\text{pulls}[i] \mathrel{+}= 1$$
$$\text{sum\_relative\_mr}[i] \mathrel{+}= \text{relative\_MR}_{k,i}$$

平均值：

$$\bar{x}_i = \frac{\text{sum\_relative\_mr}[i]}{\text{pulls}[i]}$$

$\bar{x}_i$ 越低 → arm $i$ 的 miss ratio 越低 → 越好。

### 4.5 收敛检测

每轮结束后检查是否可以锁定最优 arm（`fsb_check_convergence()`）：

**步骤 1: 前置条件**

```
if effective_rounds < min_rounds:
    return -1  (继续探索)
```

其中 `effective_rounds = current_round + 1 - warmup_rounds`。

**步骤 2: 找 best arm**

$$\text{best} = \arg\min_i \bar{x}_i$$

**步骤 3: 检查是否达到 max_rounds**

```
if current_round + 1 >= max_rounds:
    return best  (强制锁定)
```

**步骤 4: UCB/LCB 置信区间检查**

定义 $N = \sum_{i} \text{pulls}[i]$（总 pull 次数），则：

$$\text{UCB}_{\text{best}} = \bar{x}_{\text{best}} + c \cdot \sqrt{\frac{\ln N}{\text{pulls}[\text{best}]}}$$

$$\text{LCB}_i = \bar{x}_i - c \cdot \sqrt{\frac{\ln N}{\text{pulls}[i]}}$$

收敛条件：**best arm 的 UCB < 所有其他 arm 的 LCB**

$$\forall i \neq \text{best}: \quad \text{UCB}_{\text{best}} < \text{LCB}_i$$

含义：即使对 best arm 做最乐观（最差）估计，对其他 arm 做最悲观（最好）估计，best arm 仍然"更好"。此时可以确信 best 就是最优。

如果任意一个其他 arm 的 LCB ≤ best 的 UCB（置信区间重叠），则继续探索。

### 4.6 锁定

锁定后：
1. 设置全局 feature flags（`loh_use_freq_rec`, `loh_use_freq_size`, `loh_use_rec_size`）
2. 调用 `loh_rebuild_active_weight_map()` → 确定 CMA-ES 优化维度
3. 创建 CMA-ES 实例，开始权重优化
4. FSB phase 设为 1，此后 `fsb_step()` 直接返回不再干预

---

## 5. 与标准 UCB1 的区别

### 标准 UCB1（经典多臂赌博机）

标准 UCB1 的设计目标是**最大化累积收益**（regret minimization）：

- **每步选 1 个 arm**：选 UCB 值最高的那个
- **各 arm pull 次数不同**：好的 arm 被拉更多次（exploitation），差的偶尔拉（exploration）
- **探索-利用权衡**：UCB 值 = 平均回报 + 探索奖励。差 arm 因为拉得少，探索项大，偶尔会被选中
- **在线决策**：每步的选择直接影响总收益

### FSB 的 UCB1 变体

FSB 的设计目标不同 — 它是 **Best Arm Identification**（识别最优 arm，而非最大化累积收益）：

| 特性 | 标准 UCB1 | FSB 的变体 |
|------|----------|-----------|
| **目标** | 最大化累积收益 | 识别最优 arm |
| **每步选几个 arm** | 1 个（UCB 最高的） | **全部 8 个**（round-robin） |
| **各 arm pull 次数** | 不同（好的多、差的少） | **始终相同**（每轮每个 arm 各 1 次） |
| **UCB 的用途** | 决定选哪个 arm | **判断是否收敛**（提前停止） |
| **结束条件** | 无限运行 | min/max rounds 限制 |
| **arm 顺序** | 随机/按 UCB | 固定 0→1→2→...→7 |

### 为什么采用 round-robin 而非标准 UCB1

1. **去趋势需求**: 缓存 MR 随时间变化，必须在同一轮内试探所有 arm 才能计算 mean 去趋势。如果用标准 UCB1 每步只选 1 个 arm，无法有效去趋势。

2. **公平比较**: round-robin 保证每个 arm 在相同的缓存状态下被测试相同次数。标准 UCB1 中好 arm 被拉更多，但缓存场景中"被拉更多"的 arm 恰好享受了更稳定的缓存状态，造成偏差。

3. **固定开销**: FSB 的目标是"尽快选好 config 然后交给 CMA-ES"。与其让 UCB1 在 exploration 上浪费 pull（拉明显差的 arm），不如固定 N 轮 round-robin 后直接选最优。UCB 仅用于检测"是否可以提前停止"。

### 为什么实际上 UCB 提前收敛几乎不会触发

8 个 arm 的 MR 差异通常仅 0.001~0.01，而 UCB/LCB 的置信半径：

$$c \cdot \sqrt{\frac{\ln N}{n_i}} \approx 1.0 \times \sqrt{\frac{\ln(8 \times R)}{R}}$$

其中 $R$ = 有效轮数。当 $R=5$：

$$\text{半径} \approx 1.0 \times \sqrt{\frac{\ln 40}{5}} = \sqrt{\frac{3.69}{5}} = 0.86$$

置信区间总宽度 ≈ 1.72 >> MR 差异 ~0.01。所以 FSB 实际上总是跑满 max_rounds 然后强制锁定。

---

## 6. 与 AUTO_COMPOUND (AC) v5 的对比

### 决策方式

| 维度 | FSB v2 | AC v5 |
|------|--------|-------|
| **决策依据** | 实际运行 MR（经验数据） | 统计代理指标 r1/r2（Pearson 相关性） |
| **决策时间** | warmup 后 + 4~10 × n_obj 请求 | warmup 时一次性决定（零额外请求） |
| **搜索空间** | 全部 8 种 config | 仅 f1xx（FR 固定开启，4 种） |
| **计算开销** | 每请求 1 次比较（极低） | warmup 时一次 O(n_obj) 扫描（极低） |
| **CMA-ES 延迟** | 延迟 8 × block_size × rounds 请求 | 无延迟 |

### 开销量化

以 n_obj = 100,000 为例：

- **block_size** = 100,000 / 4 = 25,000
- **每轮请求** = 8 × 25,000 = 200,000
- **min_rounds=2**: 至少 400,000 请求（约 4× n_obj）
- **max_rounds=5**: 最多 1,000,000 请求（约 10× n_obj）

FSB 期间权重固定为 0.5/0.0，**不做 CMA-ES 优化**，性能低于稳态。

AC 的开销是零—它在 warmup 扫描缓存对象时顺便计算 r1/r2，不需要额外请求。

### 效果对比

- FSB 胜率 65~74%（vs AC_OFF 和 AC_ON）
- FSB median MR regret 2.78% vs AC 的 7~8%
- 代价是开销大（数十万~百万请求的试探期）

---

## 7. 总结

FSB v2 本质上是一个 **fixed-design best-arm-identification 算法**：
- 固定 N 轮 round-robin 试探所有 8 种 feature config
- 每轮去趋势消除时序偏差
- 选平均 relative MR 最低的 config 锁定
- UCB/LCB 仅作为理论提前终止条件（实际不触发）
- 锁定后启动 CMA-ES 在选定的 feature 空间内做权重优化

与 AC 的核心权衡：**用更多的试探开销换取更准确的选择**。
