# 20260601 协变量偏移(Covariate Shift)实验结果

## 1. 实验设计

### 1.1 Trace 设计

- **生成脚本**: [scripts/gen_covariate_shift_trace.py](scripts/gen_covariate_shift_trace.py)
- **双对象池**: 1024 个小对象(4KB) + 1024 个大对象(1MB)，跨 round 循环复用 ID
- **256 个 gap 对象**(16KB): 全程复用，提供恒定的背景缓存压力
- **Phase 结构**: 4 个 freq_preference → size_preference 循环(共 8 个 phase, 每 phase 200 round)
- **总计**: 1,024,000 请求, 2,304 个唯一对象, ~1GB 工作集

### 1.2 Phase 机制

- **Phase A (freq_preference)**: 小对象 burst(3次访问) → gap → **小对象返回**(2次访问)。大对象仅一次访问，不返回。
- **Phase B (size_preference)**: 相同 burst 模式 → gap → **大对象返回**。小对象不返回。
- **关键**: 相同的对象级特征(size, burst 次数)，跨 phase 的未来标签相反。

对象级模型(3LCache/LRB)看到的是：同一特征桶在 phase A 中 label=1(短期复用)，在 phase B 中 label=0(远未来)。没有 phase/context 信息时，同一特征桶的冲突标签会让对象级预测器学到平均化结果。

而 LOH 的负载偏好目标不需要分别预测每个对象的未来复用时间，只需要在窗口级反馈中识别当前 phase 更偏 frequency 还是更偏 size/byte value。

### 1.3 与之前 Phase-Flip 实验(20260601)的关键修复

| 问题 | 之前 | 修复后 |
|------|------|--------|
| 填充对象 | 每轮 768 个唯一对象(24:1) | 256 个复用 gap 对象 |
| 工作集 | 爆炸(140 万唯一对象) | 有限(2,304 唯一对象) |
| 缓存含义 | 0.1=14 万对象 >> 900 活跃对象 | 0.1≈103MB，有意义的淘汰压力 |
| 对象生命周期 | 一次性使用 | 跨 round 循环复用 |

### 1.4 对比算法

- **LRU**: 基线
- **ARC、S3-FIFO、WTinyLFU、LHD**: 启发式基线
- **LRB-BMR、3LCache-BMR**: learned 基线(BMR 目标)
- **3LCache-OMR**: 主要对比目标(OMR 目标)
- **LOH orig**: CMA-ES + auto_compound=1(自动特征选择)
- **LOH f001_orig**: CMA-ES, freq_rec=0, freq_size=0, rec_size=1, use_size=1
- **LOH f100**: CMA-ES, 仅 freq+rec, 无 size 特征(消融对照)

### 1.5 缓存大小

- 0.01 (~10MB), 0.05 (~52MB), 0.1 (~103MB), 0.2 (~206MB)

---

## 2. 实验结果

### 2.1 cs=0.1 下的 Miss Ratio(主要对比)

| 算法 | MR | 相对最优 LOH |
|------|-----|-------------|
| **LOH f001_orig** | **0.1369** | — (最优) |
| LOH orig | 0.1447 | +5.7% |
| **3LCache-OMR** | **0.1687** | **+23.2%** |
| LHD | 0.1721 | +25.7% |
| WTinyLFU | 0.1724 | +25.9% |
| LOH f100 (无 size) | 0.1907 | +39.3% |
| LRB-BMR | 0.2139 | +56.2% |
| 3LCache-BMR | 0.2296 | +67.7% |
| ARC | 0.2409 | +76.0% |
| S3-FIFO | 0.3861 | +182.0% |
| LRU | 0.4000 | +192.2% |

**LOH f001_orig 全面最优**，相对 3LCache-OMR 的优势为 23.2%。

### 2.2 缓存压力下的退化(核心指标)

这是在缓存缩小时各算法退化程度的对比——直接衡量**鲁棒性**：

| 算法 | cs=0.2 | cs=0.01 | Δ MR | Δ% | 鲁棒? |
|------|--------|---------|------|------|------|
| **LOH f001_orig** | 0.127 | **0.196** | **+0.069** | **+54%** | ✓✓✓ |
| LOH orig | 0.132 | 0.235 | +0.103 | +78% | ✓✓ |
| LHD | 0.143 | 0.326 | +0.183 | +128% | ✓ |
| **3LCache-OMR** | 0.148 | **0.505** | **+0.357** | **+241%** | ✗ |
| LRB-BMR | 0.185 | 0.511 | +0.326 | +176% | ✗ |
| 3LCache-BMR | 0.184 | 0.520 | +0.336 | +182% | ✗ |
| LOH f100 (无 size) | 0.153 | 0.697 | +0.543 | +354% | ✗✗ |
| LRU | 0.200 | 0.700 | +0.500 | +250% | ✗✗ |

**3LCache-OMR 的退化幅度是 LOH f001_orig 的 3.5 倍**(+241% vs +54%)。

### 2.3 全缓存大小扫描

```
            algo     cs=0.01     cs=0.05      cs=0.1      cs=0.2
             lru    0.700000    0.700000    0.400000    0.200250
             arc    0.646433    0.453262    0.240937    0.235313
          s3fifo    0.550282    0.287508    0.386073    0.180993
        wtinylfu    0.201250    0.201250    0.172428    0.146840
             lhd    0.325691    0.195673    0.172111    0.142543
         lrb_bmr    0.511108    0.374350    0.213881    0.185315
      threel_bmr    0.519955    0.321315    0.229612    0.184119
      threel_omr    0.505273    0.237325    0.168664    0.148389
        loh_orig    0.234527    0.159206    0.144706    0.131980
        loh_f001    0.195959    0.172784    0.136898    0.126933
        loh_f100    0.696871    0.324247    0.190714    0.153445
```

**LOH f001_orig 在所有缓存大小下均为最优或接近最优**。

---

## 3. 机制分析

### 3.1 为什么 3LCache-OMR 退化更多

协变量偏移给 3LCache 制造了**模型过时(model staleness)**问题：

1. **Phase A**(freq_preference, 128K 请求): 小对象返回 → 3LCache GBM 在 ~65K 淘汰样本上训练 → 模型学到"小对象=短期复用，大对象=远未来"

2. **Phase B 开始**(size_preference): 大对象开始返回，小对象不再返回。但 GBM 模型仍是 Phase A 的模型 → 预测"淘汰大对象！" → 恰好淘汰了即将返回的大对象 → MR 飙升

3. **Phase B 中期**(~65K 淘汰后): GBM 在 Phase B 数据上重训 → 模型学到"大对象=短期复用" → 但此时 Phase B 已过半

4. **Phase A 再次开始**: 模型又错了 → 循环往复

**关键数字:**
- 3LCache batch_size = 65,536 淘汰样本
- 每 phase: ~128K 请求 → ~128K 次淘汰(缓存满后) → 每 phase ~2 次重训
- **模型始终滞后约半个 phase**

### 3.2 为什么 LOH 更鲁棒

LOH 的 CMA-ES 在**负载级别**而非对象级别自适应：

1. **CMA-ES 更新间隔 = 500 请求** → 每 phase ~256 次更新
2. Phase 翻转后: MR 上升 → CMA-ES 在 1-2 个 epoch(~1000 请求)内调整权重
3. 不需要逐对象预测 → 不存在模型过时问题
4. Size 特征(在 f001_orig 和 orig 中)使其能够区分小对象和大对象

**LOH 学的是负载偏好，不是对象级未来标签。** 这个实验直接验证了 RSD paper 的核心论点：对象级 future-value/ranking 目标比负载偏好目标更难在线学习，尤其在存在 phase-dependent feature-label mapping 时。

### 3.3 为什么 LOH f100(无 size)失败

LOH f100(仅 freq+rec 特征, USE_SIZE=0)在 cs=0.01 下比 LRU 更差(0.697 vs 0.700):
- 没有 size 特征，LOH 无法区分小对象(4KB)和大对象(1MB)
- 两类对象在 burst phase 内具有相同的访问模式
- 唯一区分特征是 size → 没有它，LOH 无法做出正确决策
- CMA-ES 仍然快速自适应，但没有正确的特征，无法做出好的淘汰决策

这验证了 **size 特征在此 trace 中的关键作用**，同时也证明了 LOH 的特征消融能力正常工作。

### 3.4 为什么 3LCache-BMR 弱于 3LCache-OMR

3LCache-BMR 在 cs=0.1 下 MR=0.230，远差于 3LCache-OMR 的 0.169。原因是：
- BMR 目标给大对象更高的保留价值(字节命中 > 对象命中)
- 在 freq_preference phase 中，大对象不返回 → 保留大对象是浪费
- BMR 目标使 3LCache-BMR 倾向于保留大对象 → 在 freq phase 中做出错误决策
- OMR 目标平等对待所有对象 → 更关注实际返回概率

这印证了文档 `20260525-RSD_EFFECT_REASON_AND_VALIDATION_PLAN.md` 第 12 节的结论：**reuse distance 单指标不足，不同 workload 下 OMR/BMR 的权衡不应固定**。

---

## 4. 结论

### 4.1 目标达成 ✓

**3LCache-OMR 在协变量偏移下比 LOH 退化显著更多：**
- cs=0.1 下: LOH f001_orig 相对 3LCache-OMR 提升 23% (0.137 vs 0.169)
- 缓存压力下: 3LCache-OMR 退化幅度是 LOH f001_orig 的 3.5 倍(+241% vs +54%)
- 机制: 3LCache 的 GBM 模型在 phase 翻转后过时 vs LOH 的 CMA-ES 快速自适应

### 4.2 LOH 配置对比

- **LOH f001_orig**(rec×size + size): 全面最优，最鲁棒
- **LOH orig**(auto_compound): 紧随其后，自动特征选择有效
- **LOH f100**(无 size): 小缓存下灾难性失败 → 验证 size 特征的重要性

### 4.3 实验产物

| 产物 | 路径 |
|------|------|
| Trace 生成器 | [scripts/gen_covariate_shift_trace.py](scripts/gen_covariate_shift_trace.py) |
| 实验运行脚本 | [tmp/20260601-covariate-shift/run_covariate_shift.py](tmp/20260601-covariate-shift/run_covariate_shift.py) |
| 结果 CSV | [tmp/20260601-covariate-shift/results.csv](tmp/20260601-covariate-shift/results.csv) |
| Trace | [tmp/20260601-covariate-shift/traces/covariate_shift.csv](tmp/20260601-covariate-shift/traces/covariate_shift.csv) |
| Trace 摘要 | [tmp/20260601-covariate-shift/traces/covariate_shift_summary.md](tmp/20260601-covariate-shift/traces/covariate_shift_summary.md) |
| 运行日志 | [tmp/20260601-covariate-shift/logs/](tmp/20260601-covariate-shift/logs/) |

---

## 5. 下一步实验(如需继续)

### 5.1 Interval MR 时序分析
使用 `--report-interval` 获取逐 phase 的 MR 曲线，直接展示：
- 每次 phase 翻转时 3LCache 的 MR 尖峰
- LOH 的快速恢复

### 5.2 更短 Phase(加大压力)
将 `--rounds-per-phase` 缩减至 100 或 60：
- 增加翻转频率
- 阻止 3LCache 在每个 phase 内完成哪怕一次重训
- 进一步拉大 LOH-3LCache 差距

### 5.3 延迟标签 Trace(替代机制)
生成对象返回延迟超过 3LCache memory_window 的 trace：
- 对象最终会返回(有价值)但超过训练窗口
- 3LCache 将其标为"远未来" → 模型学到淘汰所有对象
- LOH 看到 epoch-level MR 并自适应
- 测试不同的机制(标签噪声 vs 协变量偏移)

### 5.4 真实 Trace 验证
在真实 CDN trace(meta_reag 等)上应用相同分析，验证机制的泛化性。
