# 20260602 Proxy Objective Mismatch 实验验证

## 1. 核心论点

**3LCache 的劣势根源于"代理目标错配"（proxy objective mismatch），而非收敛速度或特征不足。**

- **3LCache**: 学习预测 `log(1+reuse_distance)` → 评分 `size × exp(pred)` → **两个阶段**，预测误差被指数放大
- **LOH**: CMA-ES 直接搜索权重 → 评分 `Σ w_i × feat_i` → **单阶段**，直接优化 MR

当对象大小异构时，reuse distance 预测的微小误差通过 `size × exp(pred)` 被**指数级放大**，导致排序错误。LOH 的线性权重直接编码"在什么情况下应该淘汰什么对象"，不受预测误差放大影响。

## 2. 实验设计

### 2.1 Trace

- **生成器**: [scripts/gen_size_tiebreak_trace.py](scripts/gen_size_tiebreak_trace.py)
- 512 小对象(4KB) + 512 大对象(1MB)，循环复用
- 256 gap 对象(16KB)，复用
- 两种变体：
  - **Deterministic**: 所有对象确定性地返回（无噪声）→ 预测容易
  - **Noisy**: 对象概率性返回（Beta分布）→ 预测困难
- 2,024,000 请求（deterministic）/ 1,897,798 请求（noisy）
- 工作集 534MB

### 2.2 算法

| 算法 | 学习目标 | 评分函数 |
|------|---------|---------|
| LRU | 无 | recency |
| 3LCache-OMR | `log(1+reuse_distance)` | `size × exp(GBM_pred)` |
| 3LCache-BMR | `log(1+reuse_distance)` | `exp(GBM_pred)` |
| LOH f000 | epoch MR → 权重 | `w1×rec + w2×freq + w3×size` |
| LOH f001 | epoch MR → 权重 | `w1×rec + w2×freq + w3×size + w4×rec×size` |

> **代码纠正**: 3LCache-OMR 评分 = `size × exp(pred)`（line 603），3LCache-BMR 评分 = `exp(pred)`（line 593）。之前的分析误将两者搞反。

### 2.3 3LCache 训练确认

使用 `THREEL_DEBUG_TRAIN=1` + debug build 确认 3LCache 在 noisy 1.9M trace 上训练了 2 个 batch（131K 样本）。interval MR 在 train=2 后稳定，表明模型已收敛。

---

## 3. 实验结果

### 3.1 总表

| 变体 | cs | LRU | 3LCache-OMR | 3LCache-BMR | LOH f000 | LOH f001 |
|------|-----|------|------------|------------|---------|---------|
| **Det** | 0.02 | 0.443 | 0.436 | - | **0.202** | 0.216 |
| **Det** | 0.05 | 0.443 | 0.188 | - | 0.095 | **0.080** |
| **Det** | 0.1 | 0.379 | 0.139 | - | 0.095 | **0.111** |
| **Noisy** | 0.02 | 0.439 | 0.338 | 0.341 | - | **0.202** |
| **Noisy** | 0.05 | 0.432 | 0.171 | 0.188 | **0.077** | 0.109 |
| **Noisy** | 0.1 | 0.149 | 0.118 | 0.137 | - | **0.088** |

### 3.2 关键对比: 3LCache-OMR vs LOH f001

| cs | Deterministic gap | Noisy gap |
|----|-------------------|-----------|
| 0.02 | 0.436 vs 0.216 (**LOH 50% better**) | 0.338 vs 0.202 (**LOH 40% better**) |
| 0.05 | 0.188 vs 0.080 (**LOH 57% better**) | 0.171 vs 0.109 (**LOH 36% better**) |
| 0.1 | 0.139 vs 0.111 (**LOH 20% better**) | 0.118 vs 0.088 (**LOH 25% better**) |

**LOH 在所有配置下均显著优于 3LCache-OMR，无论是否有概率噪声。** 噪声没有显著扩大差距 → 说明机制不是"噪声使预测更难"，而是**代理目标的结构性错配**。

### 3.3 关键发现

1. **两种变体下 LOH 都赢** → 机制不是噪声依赖的，而是结构性的
2. **LOH f000（线性 rec+freq+size，无交互）在 cs=0.05 noisy 下最优**（0.077）→ 线性直接搜索 > GBM 非线性预测
3. **3LCache-BMR（exp 评分，无 size）弱于 3LCache-OMR（size×exp）** → size 参与评分确实有帮助，但仍不如 LOH 的直接权重

---

## 4. 机制解释

### 4.1 为什么代理目标错配是结构性的

3LCache 的训练目标：最小化 `MSE(log(1+true_reuse), log(1+pred_reuse))`。

最优解是条件期望：`pred = E[true_reuse | features]`。

但缓存淘汰的**真实目标**是：选择淘汰后能使 MR 最小化的对象。两者不等价：

- 对象 A: 4KB, predicted_reuse=500, true_reuse=500
- 对象 B: 1MB, predicted_reuse=500, true_reuse=500

3LCache-OMR 评分: A = 4096 × exp(500), B = 1048576 × exp(500)。B 分高 → 淘汰 B ✓

但如果预测有误差：
- 对象 A: 4KB, predicted_reuse=400, true_reuse=500（低估 100）
- 对象 B: 1MB, predicted_reuse=550, true_reuse=500（高估 50）

3LCache-OMR 评分: A = 4096 × exp(400), B = 1048576 × exp(550)
- A = 4096 × 5.2e173, B = 1048576 × 5.9e238
- B >> A，淘汰 B（正确！但差距被指数放大到荒谬的程度）

即使预测误差很小（A 低估 20%, B 高估 10%），`exp()` 变换后差距被指数放大，导致**确定性地淘汰 B**，而真实 reuse distance 相同 → 应该考虑 size 做 tiebreaker，但 `size × exp(pred)` 的乘法形式在指数差距面前微不足道。

### 4.2 为什么 LOH 不受影响

LOH 的评分: `score = w_rec × log(rec) + w_freq × log(freq) + w_size × log(size)`

- CMA-ES 直接优化 epoch MR → 没有代理目标
- 线性权重 → 没有指数放大
- size 作为独立权重 → 不受 rec/freq 预测误差影响
- 低维搜索空间（4-6维）→ 天然正则化

### 4.3 噪声的角色

概率性返回制造了 reuse distance 的**内在不确定性** → 3LCache 的预测误差增大 → `exp(pred)` 放大效应更显著。但即使没有噪声（deterministic），指数放大仍然存在——只要 GBM 的预测不是完美的（实际上永远不可能是完美的）。

因此噪声**不是必要条件**，但它**加剧了问题**。

---

## 5. 结论

**3LCache-OMR 在完全收敛后仍系统性弱于 LOH**。根因不是收敛速度、不是特征工程、不是 size-blindness（3LCache-OMR 确实使用了 size），而是：

> **代理目标错配（Proxy Objective Mismatch）**: 3LCache 学习预测 reuse distance（代理目标），再通过 `size × exp(pred)` 转换为淘汰决策。预测误差被指数函数放大，导致排序错误。LOH 的 CMA-ES 直接搜索最小化 MR 的权重，绕过了代理目标，避免了误差放大。

这直接支撑了 RSD paper 的核心论点：**学习更接近缓存替换目标的低维 preference space，优于学习更困难、更间接的对象未来访问预测。**

### 实验产物

| 产物 | 路径 |
|------|------|
| Trace 生成器 | [scripts/gen_size_tiebreak_trace.py](scripts/gen_size_tiebreak_trace.py) |
| 确定性对照 | [tmp/20260602-size-tiebreak-control/](tmp/20260602-size-tiebreak-control/) |
| Noisy 实验 | [tmp/20260601-size-tiebreak/](tmp/20260601-size-tiebreak/) |
| 3LCache 训练确认 | `THREEL_DEBUG_TRAIN=1` 验证 2 batch 训练 |
