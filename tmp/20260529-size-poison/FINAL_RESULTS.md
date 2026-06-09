# 最终 trace（缓存大小 0.1，含 0.001 测试）

目标：设计非 phase-flip 合成 trace，使得 LRB/3LCache 在学习上更困难，而 LOH 更容易，并且在至少一个缓存大小上明显胜出。

## 方案：post-return size-poison

- 稳定有效规则：候选对象在短间隙扫描后必定返回。
- 噪声规则：毒药对象在返回后注入，且大小偏置（候选=4,096B，毒药=262,144B）。
- 预期困难目标（LRB/3LCache）：字节导向反馈被大量大对象的无返回样本主导，与稳定短复用规则冲突。
- 预期容易目标（LOH 近因性）：毒药在命中窗口后到达，主要污染标签而非提前驱逐候选。

详见 tmp/20260529-size-poison/label_noise_summary.md。

## 结果（缓存大小 0.1）

BMR = 字节未命中率。

| 算法 | 未命中率 | BMR | 备注 |
|---|---:|---:|---|
| LOH | 0.237810 | 0.222497 | 最佳 |
| 3LCache-OMR | 0.313873 | 0.268969 | 低于 LOH |
| 3LCache-BMR | 0.412827 | 0.292522 | 明显低于 LOH |
| LRU | 0.435154 | 0.329622 | 明显低于 LOH |
| LRB-BMR | 0.437235 | 0.333474 | 明显低于 LOH |

LOH 相比最强的学习基线（3LCache-OMR）优势超过 7.6 个点，相比 LRU/LRB 优势超过 19 个点，差距明显。

## 结果（缓存大小 0.001）

| 算法 | 未命中率 | BMR | 备注 |
|---|---:|---:|---|
| 3LCache-OMR | 0.436528 | 0.326897 | 0.001 下最佳 |
| LRU | 0.441731 | 0.336106 | 接近 3LCache-OMR |
| 3LCache-BMR | 0.456708 | 0.362520 | 低于 LRU |
| LOH | 0.482547 | 0.394662 | 0.001 下落后 |
| LRB-BMR | 0.595884 | 0.586830 | 最差 |

在 0.001 下，大小偏置的毒药让缓存过小，LOH 无法稳定保住短复用窗口，因此落后。这是 size-poison 方案的预期特性，因此该方案只以 0.1 缓存为主展示学习目标差异。

## 产物

- Trace CSV: tmp/20260529-size-poison/label_noise_preference.csv
- Metadata: tmp/20260529-size-poison/label_noise_metadata.csv
- 摘要: tmp/20260529-size-poison/label_noise_summary.md
- 图表: tmp/20260529-size-poison/label_noise_mix.png, tmp/20260529-size-poison/label_noise_timeline.png
- 日志: tmp/20260529-size-poison/logs/default_compare.log
