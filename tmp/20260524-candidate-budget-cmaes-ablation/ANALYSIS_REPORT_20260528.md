# 实验分析报告 - 2026/05/28

## 1. Warmup 对象数分析（r64_s8 配置）

### 1.1 数据规模
- **日志来源**: r64_s8 配置（64 random candidates，8 structured candidates）
- **指标范围**: MR（误失率）指标的全部日志
- **总日志数**: 11,536 条
- **唯一 trace 条目**: 11,529 条（cache × group × trace 组合去重）
- **缺失 warmup 行**: 7 条（占比 0.06%，可能为截断日志）
- **重复检查**: 0 个不一致（同 trace 的 16 个 cfg 变体 n_obj 值完全一致）

### 1.2 数据特征分布

#### 物理缓存（cache01，1TB）
| 数据组 | 均值 | p50 | p0-p100 范围 | 特点 |
|--------|------|------|----------|------|
| tencentPhoto | 56.7M | 56.9M | 55.8M~57.7M | 极紧凑，方差最小 |
| metaKV | 10.0M | 10.2M | 1.9M~27.6M | 中等紧凑 |
| wiki | 5.2M | 5.3M | 1.7M~8.9M | 均衡分布 |
| metaCDN | 3.3M | 3.4M | 1.2M~4.8M | 均衡分布 |
| alibabaBlock | 0.16M | 0.08M | 2~7.5M | **高度分化**（p0=2，p100=750万） |
| tencentBlock | 0.045M | 0.03M | 101~2.7M | **高度分化**（p0=101，p100=270万） |

#### 稀疏缓存（cache0001，0.1TB）
| 数据组 | 均值 | p50 | p0-p100 范围 | 稀疏度 |
|--------|------|------|----------|---------|
| tencentPhoto | 0.48M | 0.48M | 0.46M~0.49M | cache01 的 1.18% |
| metaKV | 0.125M | 0.12M | 0.02M~0.38M | cache01 的 1.25% |
| wiki | 0.091M | 0.09M | 0.013M~0.16M | cache01 的 1.75% |
| metaCDN | 0.035M | 0.034M | 0.017M~0.044M | cache01 的 1.06% |
| alibabaBlock | 0.0029M | 0.00024M | 2~0.10M | cache01 的 1.81% |
| tencentBlock | 0.00071M | 0.00028M | 2~0.072M | cache01 的 1.58% |

### 1.3 关键观察
1. **Photo 类 traces**（tencentPhoto）对象数最多（百万级），方差最小
2. **Block 类 traces**（tencentBlock）对象数最少（千级），方差最大
3. **缓存大小比 ≈ 对象数比**: cache01/cache0001 = 10×，对象数差异 1~2%（表明不同缓存大小中对象数比例接近）
4. **Block traces 中单个对象通常较大**：即使 cache01 中对象数少（千级），但占用大量字节

---

## 2. 3LCache 候选采样机制

### 2.1 参数说明

| 参数 | 初始值 | 类型 | 动态性 | 说明 |
|------|--------|------|--------|------|
| `sample_rate` | 1024 | uint16 | **是** | 采样集合大小（每次 rank() 调用时可重新计算） |
| `eviction_rate` | 2 | uint8 | 否 | 驱逐批处理因子（固定值） |
| `evict_nums` | 动态 | int32 | **是** | 当前驱逐预算（由 rank() 返回值计算） |
| `initial_queue_length` | 0 | int32 | **是** | 缓存中当前对象数（动态更新） |

### 2.2 候选数量动态调整机制

#### 核心公式
```cpp
// rank() 方法内的采样率自适应逻辑
if (sample_rate >= initial_queue_length * 0.01 + eviction_rate)
    sample_rate = initial_queue_length > 2
                      ? initial_queue_length * 0.01 + eviction_rate
                      : 1;
```

#### 解读
- **这里计算的是 `sample_rate`，不是 `rank()` 最终返回的候选总数。**
- `sample_rate` 初始值是 1024，并且每次扫描完整个 in-cache 队列后也会先重置为 1024。
- 只有当 `sample_rate >= initial_queue_length * 0.01 + eviction_rate` 时，才会下调为 `initial_queue_length * 0.01 + eviction_rate`；赋值到 `uint16_t`，小数部分会被截断。
- 因此在一次重置后的常见情况中，`sample_rate ≈ min(1024, floor(initial_queue_length * 0.01 + 2))`。对象数足够大时就是 1024；小 cache 才是 1%+2。
- `eviction_rate` 在当前代码中固定为 2，没有看到运行时更新逻辑。

#### 驱逐预算计算
```cpp
if (evict_nums <= 0 || pred_map.empty()) {
    evict_nums = rank() / eviction_rate;  // rank() 返回采样的对象数
}
evict_nums -= 1;  // 每次驱逐一个，递减
```

- **驱逐频度**: 每次从 LightGBM 预测池中驱逐 1 个对象
- **补充机制**: 当驱逐预算耗尽（≤0）时，调用 `rank()` 重新采样，计算新的 `evict_nums`

### 2.3 采样数量的实际数值

#### 第一层：sample_rate
`sample_rate` 是常规扫描的目标采样配额，重置后通常为：

```
sample_rate = min(1024, floor(initial_queue_length * 0.01 + 2))
```

#### 第二层：rank() 实际返回值
`rank()` 返回的是 `sampled_objects.size()`，不是单纯的 `sample_rate`：

```
rank_return = quick_demotion_count + regular_scan_count
evict_nums = rank_return / 2
```

注意：`rank()` 开头会先执行 `quick_demotion()`，它可能额外加入一批新对象候选。因此 `rank()` 的真实返回值是：

```
sampled_objects.size() = quick_demotion_count + 常规扫描采样数
```

`quick_demotion_count` 的上限由 `j < sample_rate * 1.5` 控制，常见上限约为 `1.5 * sample_rate`。随后常规扫描通常再补到约 `sample_rate` 个对象。因此，在没有跨完整队列重置的常见路径下：

```
rank_return ≈ sample_rate              // quick_demotion 不触发或很少触发
rank_return <= 2.5 * sample_rate       // quick_demotion 达到上限且常规扫描也补满
```

代码里还有一个重要细节：常规扫描的 `while` 条件是 `idx_row < sample_rate && sampled_objects.size() < initial_queue_length`。如果扫描完整个队列后仍没收够当前 pass 的 `sample_rate`，代码会重置 `idx_row=0` 并继续，`sampled_objects` 不清空。所以严格上界不是 `sample_rate`，而是 `initial_queue_length`；只是常规情况下不会走到这个极端。

#### 具体例子（基于 r64_s8 warmup n_obj 数据）

**cache01（1TB，各 trace 组，下面列的是 sample_rate；rank_return 可能因 quick_demotion 更大）：**
- tencentPhoto: 56.7M 对象 → sample_rate = 1024 → evict_nums 常见约 512
- metaKV: 10.0M 对象 → sample_rate = 1024 → evict_nums 常见约 512
- wiki: 5.2M 对象 → sample_rate = 1024 → evict_nums 常见约 512
- metaCDN: 3.3M 对象 → sample_rate = 1024 → evict_nums 常见约 512
- alibabaBlock: 0.16M 对象 → sample_rate = 1024 → evict_nums 常见约 512
- tencentBlock: 0.045M 对象 → sample_rate ≈ 456（0.01 * 45,491 + 2）→ evict_nums 常见约 228

**cache0001（0.1TB，各 trace 组，下面列的是 sample_rate；rank_return 可能因 quick_demotion 更大）：**
- tencentPhoto: 0.48M 对象 → sample_rate = 1024 → evict_nums 常见约 512
- metaKV: 0.125M 对象 → sample_rate = 1024 → evict_nums 常见约 512
- wiki: 0.091M 对象 → sample_rate ≈ 908（0.01 * 90,689 + 2）→ evict_nums 常见约 454
- metaCDN: 0.035M 对象 → sample_rate ≈ 347（0.01 * 34,558 + 2）→ evict_nums 常见约 173
- alibabaBlock: 0.0029M 对象 → sample_rate ≈ 31（0.01 * 2,924 + 2）→ evict_nums 常见约 15
- tencentBlock: 0.00071M 对象 → sample_rate ≈ 9（0.01 * 706 + 2）→ evict_nums 常见约 4

#### 关键观察
- 大多数对象数超过约 102,200 的 trace 会被 1024 上限截断，`sample_rate` 就是 1024。
- 只有对象数较少的 trace 才进入 `floor(1% * n_obj + 2)` 区间，例如 cache0001 tencentBlock 约 9 个候选。
- 驱逐批大小由 `eviction_rate=2` 决定：常规情况下约为 `rank()` 返回值的一半。
- 若 `quick_demotion()` 触发，新对象候选会额外加入，真实 `rank()` 返回值可能大于常规扫描采样数。

### 2.4 动态调整时机
1. **初始化**: initial_queue_length = in_cache.metas.size()，首次计算 sample_rate
2. **周期重置**: 扫描长度达到 initial_queue_length 时，重置 sample_rate=1024，重新计算
3. **热点适应**: 通过 sampling_lru 因子动态调整扫描边界
4. **驱逐适应**: 根据 evcition_distribution[] 跟踪驱逐分布，当分布不均衡时调整采样边界

### 2.5 总结
- **sample_rate 公式**：重置后通常为 `min(1024, floor(initial_queue_length * 0.01 + 2))`
- **rank() 实际候选数**：`quick_demotion_count + regular_scan_count`，常见约等于 `sample_rate`，触发 quick_demotion 时可明显大于 `sample_rate`
- **驱逐预算公式**：`evict_nums = rank() / 2`
- **自适应但有上限**：对象数较大时 `sample_rate` 固定为 1024；对象数较小时才按 1%+2 下调
- **分段补充**：驱逐预算耗尽时调用 rank() 补充，形成持续的采样-评分-驱逐循环

---

## 3. 实验完成状态

### 3.1 已完成任务
✅ 11,529 条 trace 的 warmup 对象数统计
✅ 6 个 trace 组的百分位数分析
✅ 3LCache 采样机制代码审计

### 3.2 产物位置
- 动态采样分析脚本: `tmp/20260524-candidate-budget-cmaes-ablation/warmup_n_obj_stats_20260527.py`
- Warmup 统计表（Markdown）: `tmp/20260524-candidate-budget-cmaes-ablation/warmup_n_obj_percentiles_20260527.md`
- Warmup 统计表（TSV）: `tmp/20260524-candidate-budget-cmaes-ablation/warmup_n_obj_percentiles_20260527.tsv`
- 本分析报告: `tmp/20260524-candidate-budget-cmaes-ablation/ANALYSIS_REPORT_20260528.md`
