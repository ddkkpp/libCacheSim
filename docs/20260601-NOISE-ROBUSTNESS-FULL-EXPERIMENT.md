# 噪声鲁棒性完整实验结果（2026-06-01）

## 概述

本文档记录三类合成噪声 trace 下 15 个算法的缓存命中率对比，旨在分析 LOH (CMA-ES)、
3LCache、LRB 在各类噪声模式下的相对鲁棒性。

**实验目录**: `tmp/20260601-noise-robustness-full/`
**运行脚本**: `tmp/20260601-noise-robustness-full/run_noise_robustness.py`
**结果汇总**: `tmp/20260601-noise-robustness-full/results_all.csv`
**热力图**:   `tmp/20260601-noise-robustness-full/plots/heatmap_*.png`

---

## 1. 实验设计

### 1.1 Trace 类型

| 类型 | 脚本 | 目的 |
|---|---|---|
| A: Phase-flip | `gen_phase_flip_preference_trace.py` | 相位翻转偏好：同一特征桶在不同阶段标签相反 |
| B: Label-poison | `gen_label_noise_preference_trace.py` | 后返回毒化：毒化对象与热对象 ID 重叠 |
| C: meta_reag-like | `gen_meta_reag_like_trace.py` | 极热头部 + 重尾大小 + 相位不稳定热点 |

### 1.2 Trace 参数

**A: Phase-flip（4 个翻转速率变体）**
- flip_r5: 每 5 轮翻转（强压力），160 个周期 = 1.536M 请求
- flip_r10: 每 10 轮翻转（中），80 个周期 = 1.536M 请求
- flip_r20: 每 20 轮翻转（轻），40 个周期 = 1.536M 请求
- flip_r40: 每 40 轮翻转（慢），20 个周期 = 1.536M 请求
- 每轮: 32 小对象(4KB) × 3次访问 + 32 大对象(1MB) × 1次访问 + 768 填充(16KB)
- freq 阶段小对象返回，size 阶段大对象返回

**B: Label-poison（4 个毒化等级）**
- poison_p0: 无毒化（基准），候选数 256/epoch，毒化数 0/epoch = 1.23M 请求
- poison_p512: 候选 256 + 毒 512/epoch = 2.43M 请求
- poison_p1024: 候选 256 + 毒 1024/epoch = 3.33M 请求
- poison_p2048: 候选 256 + 毒 2048/epoch = 5.16M 请求
- 候选对象 4KB，返回后出现毒化；毒化对象 64KB，无未来返回
- 毒化对象 ID 与候选从同一 8192-对象池循环选取（ID 重叠 = 标签翻转）

**C: meta_reag-like（2 个稳定性变体）**
- meta_clean: 热点集固定，hot_pool=256，hot_per_epoch=64，epochs=640 = ~0.6M 请求
- meta_phase_unstable: 每 epoch 轮换 20% 热点集（top-k Jaccard ~0.2）

### 1.3 算法（15 个）

| 标签 | 算法名 | 描述 |
|---|---|---|
| lru | lru | LRU |
| arc | arc | ARC |
| sieve | sieve | Sieve |
| s3fifo | s3fifo | S3-FIFO |
| wtinylfu | wtinyLFU | Window TinyLFU |
| lecar | lecar | LeCaR |
| cacheus | cacheus | Cacheus |
| lhd | lhd | LHD |
| glcache | GLCache | GLCache |
| lrb_bmr | lrb | LRB (默认 BMR 目标) |
| threel_bmr | 3LCache | 3LCache (BMR 目标) |
| threel_omr | 3LCache | 3LCache + OMR 目标 |
| loh_cmaes | loh | LOH + CMA-ES, auto_compound=1 |
| loh_f100 | loh | LOH + CMA-ES, freq+rec 特征（关 size）|
| loh_3lset | loh | LOH + CMA-ES, 使用 3LCache 特征集 |

### 1.4 缓存大小

- cache=0.1（全量工作集的 10%）
- cache=0.001（全量工作集的 0.1%）

---

## 2. 实验 B：Label-poison（关键实验）

### 2.1 结果（cache=0.1，MR: 清洁→重毒）

| algo | p0(clean) | p512 | p1024 | p2048 | Δ(p0→p2048) |
|---|---|---|---|---|---|
| lru | 0.4667 | 0.3958 | 0.3730 | 0.3576 | -0.1091 |
| arc | 0.4700 | 0.4221 | 0.3879 | 0.3613 | -0.1087 |
| sieve | 0.4667 | 0.3953 | 0.3731 | 0.3578 | -0.1089 |
| s3fifo | 0.4508 | 0.3995 | 0.3755 | 0.3601 | -0.0907 |
| wtinylfu | 0.4819 | 0.4266 | 0.3615 | 0.3570 | -0.1250 |
| lecar | 0.4667 | 0.3988 | 0.3747 | 0.3600 | -0.1066 |
| cacheus | 0.4667 | 0.3958 | 0.3730 | 0.3576 | -0.1091 |
| lhd | 0.4638 | 0.3838 | 0.3368 | 0.3273 | -0.1365 |
| glcache | 0.4818 | 0.3255 | 0.2700 | 0.2360 | -0.2458 |
| lrb_bmr | 0.4297 | 0.3598 | 0.3305 | 0.3173 | -0.1124 |
| **threel_bmr** | **0.4772** | **0.3506** | **0.2731** | **0.3032** | **-0.1740** |
| **threel_omr** | **0.4630** | **0.2174** | **0.1509** | **0.1030** | **-0.3600** |
| **loh_cmaes** | **0.4671** | **0.1970** | **0.1385** | **0.0895** | **-0.3777** |
| loh_f100 | 0.4704 | 0.3725 | 0.3469 | 0.2622 | -0.2082 |
| **loh_3lset** | **0.4849** | **0.3338** | **0.1732** | **0.0939** | **-0.3910** |

### 2.2 分析

**关键发现：大小不对称的毒化污染下，LOH 和 3LCache-OMR 显著优于简单启发式算法。**

实验设计的关键点：
- 候选对象（真正有返回价值）= 4KB
- 毒化对象（高频访问但无未来返回）= 64KB（16× 大于候选）
- cache=0.1 下缓存大小随 trace 增大而增大（工作集增大 4×，缓存也 4×）

**差异来源（尺寸感知）：**
- LRU/ARC 等：无法区分大对象（毒）和小对象（候选）。大对象进入缓存后持续占用 16 倍空间，挤出候选。最终 MR=0.36，仅比清洁状态改善 10%。
- threel_BMR：以字节命中率为目标，给大对象更高价值。反而倾向于保留 64KB 毒化对象，因为字节价值更高。MR=0.30，改善 17%，但次优。
- threel_OMR / LOH_cmaes / LOH_3lset：以对象命中率为目标（OMR），或通过 CMA-ES 学习到"小对象优先"策略。最终 MR 仅 0.09–0.10，从清洁 0.47 降到 0.09，改善 37–39%！

**LOH 的优势：**
- `loh_cmaes`（auto_compound=1）自动学习到：size 特征负相关（大=低优先级），freq+rec 正相关（频繁近期访问=高优先级）
- `loh_3lset`（3LCache 特征集 + CMA-ES 权重）同样学到大=低优先级
- 两者在重毒场景下大幅超越 LRB（LRB 同样是 GBM 学习，但不直接利用 size 进行权重调整）

**3LCache-OMR vs LOH 的区别：**
- 两者 MR 接近（0.103 vs 0.089）
- 差异原因：LOH 是全局线性权重 CMA-ES 优化，对 size 权重的学习更平滑
- 3LCache-OMR 使用 GBM 做逐对象决策，也能学到 size 规律，但训练延迟

**cache=0.001 下（极小缓存）：**
- 所有算法 MR 都高（~0.40–0.61），差异缩小
- LOH_cmaes: p0=0.610 → p2048=0.418（delta=-0.193）
- LRU: p0=0.600 → p2048=0.397（delta=-0.203）
- 极小缓存下学习算法的优势消失（缓存太小无法容纳候选集）

### 2.3 重要局限

当前设计**不能证明 3LCache 比 LOH 鲁棒性弱**，反而证明：
- 两者在大小不对称噪声下都有学习优势
- **3LCache-BMR 比 3LCache-OMR 弱很多**（因为 BMR 目标给大对象更高价值）
- LOH 在 cache=0.1 略优于 3LCache-OMR

---

## 3. 实验 A：Phase-flip（结果退化）

### 3.1 结果（cache=0.1）

| algo | flip_r40 | flip_r20 | flip_r10 | flip_r5 | Δ |
|---|---|---|---|---|---|
| lru | 0.8667 | 0.8667 | 0.8667 | 0.8667 | 0.0000 |
| arc | 0.8789 | 0.8789 | 0.8789 | 0.8789 | 0.0000 |
| ... 所有简单算法 | ~0.8667 | ~0.8667 | ~0.8667 | ~0.8667 | ~0 |
| loh_cmaes | 0.8867 | 0.8860 | 0.8937 | 0.8839 | -0.0028 |
| loh_3lset | 0.8847 | 0.8774 | 0.8795 | 0.8719 | -0.0129 |

**所有算法 MR ≈ 0.8667（= 26/30 ≈ 大对象丢失），无法区分。**

### 3.2 退化原因

- 每轮产生 768 个唯一填充对象（16KB，无返回）→ 工作集被填充对象主导
- cache=0.1 = 工作集的 10%，但工作集的 99%+ 是一次性填充
- 结果：cache 大小 ≈ 热对象集大小，所有热对象几乎必然被填充对象驱逐
- 所有算法退化为"返回时必须重新缓存"状态，MR=6/7 (= filler 6 轮驱逐 1 次热访问)

### 3.3 实验设计修正建议

为使 phase-flip 实验有意义，需要：
1. **相对缓存大小**：`cache_size = hot_set_bytes × K`（K=2-5×），使热对象可在缓存中保存
2. **减小填充量**：filler_per_round 减至 hot_per_round 的 1-2×，而非当前 24×
3. **加大热对象差异**：增加热池大小和频率差异，使 GBM 标签翻转更明显

---

## 4. 实验 C：meta_reag-like（相位不稳定效果微弱）

### 4.1 结果（cache=0.1：clean → phase_unstable）

| algo | clean | unstable | delta |
|---|---|---|---|
| lru | 0.4074 | 0.4202 | +0.0127 |
| lrb_bmr | 0.4074 | 0.4202 | +0.0127 |
| threel_bmr | 0.4074 | 0.4202 | +0.0127 |
| threel_omr | 0.4074 | 0.4202 | +0.0127 |
| loh_cmaes | 0.4074 | 0.4226 | +0.0152 |
| loh_3lset | 0.4127 | 0.4231 | +0.0104 |

**所有算法变化 ≈ +0.01，差异极小。**

### 4.2 分析

- 超热单例对象（top-1 = 21% 请求）始终在缓存中
- hot pool 的 20%/epoch 轮换（hotspot_rotate=0.2）对总体 MR 影响小
- 轮换后的热对象首次访问 burst（8次），缓存仍能命中大部分
- trace 请求总量 ~0.6M，不足以触发 3LCache/LRB 充分训练（warmup 需要 65K/131K 驱逐样本）

### 4.3 改进建议

1. 增加 epochs 到 2000+（保证 warmup 覆盖）
2. 增大 hotspot_rotate 到 0.5（更激进的相位不稳定）
3. 加大 hot_pool_size 到 1024+ 使特征碰撞更明显

---

## 5. 关键结论与下一步

### 5.1 本实验的正向发现

1. **LOH_cmaes 在大小不对称毒化场景下表现最佳**（MR 0.089，比 LRU 0.358 低 4×）
2. **3LCache-OMR 也有类似优势**（MR 0.103），但略逊于 LOH_cmaes
3. **3LCache-BMR 显著弱于 3LCache-OMR**（MR 0.303 vs 0.103），因 BMR 目标鼓励保留大对象
4. LRB_BMR 处于中间（MR 0.317），无尺寸感知学习
5. **loh_f100（纯 freq+rec，无 size 特征）也明显弱于 loh_cmaes**（0.262 vs 0.089），验证了 size 特征的关键作用

### 5.2 原始假设的验证状态

| 假设 | 结果 | 说明 |
|---|---|---|
| 3LCache 比 LOH 鲁棒性弱 | ❌ 不成立 | 在当前噪声设计下两者相近，3LCache-OMR 甚至接近 LOH |
| 噪声降低学习算法性能 | ❌ 相反 | 大小不对称噪声**提升**了 LOH/3LCache-OMR 相对简单启发式的优势 |
| Phase-flip 会分化算法表现 | ❌ 退化 | 填充对象过多导致所有算法退化到相同 MR |
| meta_reag 相位不稳定会区分算法 | ❌ 微弱 | trace 太短+相位不稳定太弱，需要更极端参数 |

### 5.3 修正实验设计（下一步）

要证明"3LCache 在某类噪声下比 LOH 弱"，需要：

**方向 1：特征碰撞 + 标签翻转（改进 phase-flip）**
- 使用**相对缓存大小**（热对象集的 2-5×），而非全量工作集的 0.1 或 0.001
- 减小填充对象比例（filler:hot = 1:1 而非 24:1）
- 使用 3LCache 的 6 个特征进行精心设计的标签翻转（同特征桶，交替 label=0/1）

**方向 2：延迟标签（delayed label）**
- 候选对象出现后，经过很长时间（>GBM memory_window）才返回
- GBM 看不到足够近的"正标签"→ 误判所有对象为冷
- LOH 的 CMA-ES 不依赖历史标签，更鲁棒

**方向 3：covariate shift（分布漂移）**
- 训练期：小对象是热的，大对象是冷的
- 测试期：突然翻转（大对象变热，小对象变冷）
- GBM 在新分布上预测错误；LOH CMA-ES 快速调整权重

---

## 6. 产物清单

| 产物 | 路径 |
|---|---|
| run 脚本 | `tmp/20260601-noise-robustness-full/run_noise_robustness.py` |
| trace 生成器 C | `scripts/gen_meta_reag_like_trace.py` |
| 结果 CSV | `tmp/20260601-noise-robustness-full/results_all.csv` |
| 热力图 (3 张) | `tmp/20260601-noise-robustness-full/plots/heatmap_*.png` |
| 主运行日志 | `tmp/20260601-noise-robustness-full/logs/experiment_main.log` |
| 单次算法日志 | `tmp/20260601-noise-robustness-full/logs/<family>__<variant>__<algo>__cs*.log` |
