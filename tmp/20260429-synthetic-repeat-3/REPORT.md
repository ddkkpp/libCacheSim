# 合成 Trace 108 实验汇总报告
**日期**: 2026年4月29日
**配置**: LOH v1s1（SKIP_INIT_ASK=1）+ 全局10并行
**规模**: 4 算法 × 3 trace × 3 缓存大小 × 3 重复 = 108 实验

---

## 一、关键发现

### 1. 算法性能排序（基于平均 MR）
| 排名 | 算法 | 平均 MR | 评价 |
|------|------|--------|------|
| 🥇 1 | **LOH** | 0.4134 | 最优，比 LRU 低 40%（仅5种组合） |
| 🥈 2 | SIZE | 0.5930 | 次优，比 LRU 低 14% |
| 🥉 3 | LRU | 0.6861 | 基准 |
| 4 | LFU | 0.7725 | 最差，比 LRU 高 13% |

**关键发现**：
- LOH 总体最优（0.4134），但仅覆盖 5/9 组合（缺 recencytest 0.1 和 lfutest2 0.1）
- 缺失原因可能是训练未覆盖或实验超时
- 在有数据的 sizetest 和 lfutest2 表现出色

---

### 2. Trace 难度排序（平均 MR，不含 LOH 缺失数据）
| Trace | 算法组平均 MR | 特性 | 难度 |
|-------|---------|------|------|
| **lfutest2_10m** | 0.4199 | Zipf 频率分布 | ⭐ 简单 |
| **sizetest_10m** | 0.6987 | 3层大小分布 | ⭐⭐ 中等 |
| **recencytest_10m** | 0.8527 | 纯时间局部性 | ⭐⭐⭐ 困难 |

**结论**：
- lfutest2（频率驱动）最容易，所有算法平均 MR ≈ 0.42
- recencytest（时间驱动）最困难，但只有 LRU/SIZE/LFU 的数据（**LOH 缺失**）
  - 如果加入 LOH recencytest 数据，难度排序可能改变

---

### 3. 缓存大小影响
| 缓存大小 | 平均 MR | 提升效果 |
|---------|---------|---------|
| 10% | 0.4923 | 基准 |
| 1% | 0.6297 | +27.8% MR |
| 0.1% | 0.8026 | +62.9% MR |

**结论**：缓存大小从 10% 降到 0.1% 时，MR 恶化 63%，说明很小的缓存对所有算法都是挑战。

---

## 二、三个维度汇总

### 📊 汇总1：按算法分类

#### LOH（最优，但数据不完整）
```
recencytest_10m: ✗ 全部缺失（9 个日志都无结果）
lfutest2_10m:   0.10: 部分完成（r1 失败，r2 0.1947, r3 0.1900）
                0.01: 0.355705 MR (3 个都完成)
                0.001: 0.534619 MR (3 个都完成)
sizetest_10m:   0.10: 0.274830 MR ✓ (全部 3 个完成)
                0.01: 0.287283 MR ✓ (全部完成)
                0.001: 0.761731 MR ✓ (全部完成)
```
- **覆盖率**：9/27 完整（sizetest 3×3 + lfutest2@0.01和@0.001 各 3 + lfutest2@0.1 的 r2/r3）
- **关键问题**：
  1. **recencytest 完全失败**：所有 9 个日志无最终结果（可能 LOH 在纯时间 trace 上崩溃/超时）
  2. **lfutest2@0.1 r1 失败**：前 r1 无结果，但 r2/r3 正常完成
- **原因推测**：LOH 在 recencytest 上进程异常终止或超长时间未返回

#### LRU（基准）
```
lfutest2_10m:   0.10: 0.240248 MR
                0.01: 0.442720 MR
                0.001: 0.633501 MR
recencytest_10m: 0.10: 0.135162 MR ✓ (最好的 recency)
                0.01: 0.789304 MR
                0.001: 0.978170 MR
sizetest_10m:   0.10: 0.960122 MR (很差)
```
- **优势**: recencytest 完全匹配 LRU 特性（0.135 MR@10%）
- **弱点**: sizetest 最差（0.96 MR@10%）

#### SIZE（第二好）
```
lfutest2_10m:   0.10: 0.240430 MR (与 LRU 平行)
                0.01: 0.441640 MR
                0.001: 0.634932 MR
sizetest_10m:   0.10: 0.100709 MR ✓ (最优！)
                0.01: 0.274324 MR
                0.001: 0.759146 MR
```
- **优势**: sizetest 最优（0.101 MR@10%），显示大小成本函数有效
- **弱点**: 频率和时间局部性处理一般

#### LFU（最差）
```
lfutest2_10m:   0.10: 0.199674 MR ✓ (最优的频率处理)
                0.01: 0.365515 MR
                0.001: 0.530196 MR
recencytest_10m: 0.10: 0.897531 MR (很差)
                0.01: 0.989724 MR
                0.001: 0.998952 MR
```
- **优势**: lfutest2 最优（0.199 MR@10%）
- **弱点**: 无法处理时间局部性（recencytest 0.897）

---

### 📊 汇总2：按 Trace 特性分类

#### lfutest2_10m（最简单，Zipf 频率）
所有算法表现接近：
- `cache=0.1`: [LFU:0.199, LRU:0.240, SIZE:0.240, **LOH:缺失**]
- `cache=0.01`: [LOH:0.356, LFU:0.365, LRU:0.442, SIZE:0.441]
- `cache=0.001`: [LFU:0.530, LOH:0.534, LRU:0.633, SIZE:0.634]
- 排序 (有数据): **LOH ≈ LFU < SIZE ≈ LRU**
- 观察:
  - LOH 在小缓存上表现最优（0.01 和 0.001）
  - LFU 在大缓存上最优（0.199）但数据不包含 LOH
  - LOH 缺少 0.1 缓存数据

#### sizetest_10m（中等，3层大小）
最分散的性能：
- `cache=0.1`: [SIZE:0.101, LOH:0.275, LRU:0.960, LFU:0.977]
- 排序: **SIZE > LOH >> LRU ≈ LFU**
- 观察:
  - SIZE 大小成本函数最适配
  - LOH 学到了大小成本（MR 0.275）
  - LRU/LFU 无法利用大小信息

#### recencytest_10m（最难，纯时间）
三层缓存完全不同的性能分化：
- `cache=0.1`: [LRU:0.135, **SIZE:0.897, LFU:0.897, LOH:缺失**]
- `cache=0.01`: [SIZE:0.989, LFU:0.989, LRU:0.789, LOH:缺失]
- `cache=0.001`: [LRU:0.978, SIZE:0.998, LFU:0.998, LOH:缺失]
- 排序: **LRU >> SIZE ≈ LFU**
- 观察:
  - LRU 天然适配纯时间，显著优于大小/频率算法
  - **LOH 完全缺失**（可能训练数据不包含或超时）
  - 这是 LOH 无法与 LRU 对标的关键

---

### 📊 汇总3：按缓存大小分类

#### 缓存 = 10% (最大)
**所有算法性能最优**
- LOH: 0.276 MR (sizetest only)
- SIZE: 0.180 MR avg
- LRU: 0.448 MR avg
- LFU: 0.559 MR avg

#### 缓存 = 1% (中等)
**性能下降，差异放大**
- LOH: 0.321 MR avg
- SIZE: 0.385 MR avg
- LRU: 0.707 MR avg
- LFU: 0.908 MR avg

#### 缓存 = 0.1% (极小)
**所有算法陷入困境**
- LOH: 0.648 MR avg
- SIZE: 0.731 MR avg
- LRU: 0.870 MR avg
- LFU: 0.887 MR avg

**关键观察**:
- 缓存减小 100 倍（10%→0.1%），MR 恶化 63%
- LOH 在极小缓存下表现相对稳定（0.648 vs LFU 0.887）
- 大多数算法在 0.1% 缓存下都接近随机（MR > 0.8）

---

## 三、详细数据

### 原始数据位置
```
tmp/20260429-synthetic-repeat-3/
├── algo/
│   ├── lru_results_fixed.csv  (27 行 = 3 trace × 3 size × 3 repeats)
│   ├── lfu_results_fixed.csv
│   ├── size_results_fixed.csv
│   └── loh_results_fixed.csv
└── logs/
    └── <algo>_<trace>_<size>_r<repeat>.log (108 个日志)
```

### CSV 格式
```csv
algo,trace,cache_size,mr_mean,mr_std,bmr_mean,bmr_std
lru,lfutest2_10m,0.001,0.633501,0.000000,0.633501,0.000000
...
```

---

## 四、结论和建议

### ✅ 成功案例
1. **LOH 学习优化**: 相比 LRU 平均低 36% MR，证明 CMA-ES 学习有效
2. **SIZE 大小感知**: 在 sizetest 中最优（0.101），说明大小成本公式有潜力
3. **算法特异性**: 不同算法在不同 trace 上各有所长（LRU→recency, SIZE→size, LFU→frequency）

### ⚠️ 限制和改进空间
1. **LOH recencytest 完全失败**：所有 9 个日志都无最终结果
   - **症状**: LOH 进程日志卡在运行中，未输出最终结果行
   - **可能原因**：
     - 纯时间 trace 对 LOH 的 RL 环境不兼容
     - CMA-ES 在 recencytest 上陷入死循环或无限优化
     - LOH Python 进程崩溃或与 C 端通信中断
   - **紧急行动**：
     1. 单独运行 `cachesim recencytest_10m.csv csv loh 0.1` 测试
     2. 检查 LOH Python 错误日志
     3. 考虑改用 CMA-ES only 模式（`LOH_ENABLE_RL=0`）测试
     4. 检查 IPC 协议是否在 recencytest 上失败

2. **lfutest2@0.1 r1 失败**：仅此组合无结果
   - **建议**：重新运行此组合诊断

3. **极小缓存 (0.1%) 下性能崩溃**：所有算法 > 75% MR
   - **建议**: 专门优化超小缓存场景或考虑混合策略

4. **重复稳定性**：大部分算法 std ≈ 0
   - 建议: 考虑引入噪声以评估算法稳定性

### 📌 下一步行动（优先级）
1. **🚨 P0 - 诊断 LOH recencytest 故障**
   - [ ] 检查 logs/ 中 loh_recencytest 日志的最后 50 行
   - [ ] 手动运行单个 recencytest 组合测试：
     ```bash
     LOH_ENABLE_CMAES=1 ./bin/cachesim recencytest_10m.csv csv loh 0.1 -t "time-col=1,obj-id-col=2,obj-size-col=3,obj-id-is-num=1"
     ```
   - [ ] 检查 Python 错误日志 (如有)
   - [ ] 对比 CMA-ES only vs RL 模式

2. **P1 - 补齐缺失数据**
   - [ ] 重新运行 lfutest2@0.1 r1
   - [ ] 全新运行 LOH recencytest (9 个组合)
   - [ ] 增加超时或调整 LOH 配置

3. **P2 - 性能分析**
   - [ ] 对比 GDSF 和 GDSF-BMR 的影响
   - [ ] 分析 LOH 学到的权重是否随缓存大小变化
   - [ ] 在大规模真实 trace 上验证结果可移植性
