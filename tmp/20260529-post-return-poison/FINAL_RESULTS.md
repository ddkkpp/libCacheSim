# 学习目标难易程度 Trace 最终结果

**目标**：设计非 phase-flip 合成 trace，使得 LRB/3LCache 在学习困难，而 LOH 保持优势。

## 方案：Post-Return-Poison 等大小标签噪声

### 设计理念

- **稳定工作负载规则**：候选对象（4KiB）具有短复用特性，在间隙扫描后总是返回
- **噪声规则**：毒药对象（4KiB，同样大小）具有相同的本地特征签名，但仅在有用返回完成后注入，且永不返回
- **学习目标差异**：
  - **LRB/3LCache**：以对象级未来距离为目标，看到同样特征的候选与毒药的混合标签（45K 返回 vs 369K 不返回），无法可靠分离，目标损坏
  - **LOH**：以对象命中率为目标，因毒药在返回窗口之后到达，它主要污染标签而不是驱逐有用候选；LOH 的默认近期性启发式仍然有效

### 生成参数

```bash
python3 scripts/gen_label_noise_preference_trace.py \
  --output-dir tmp/20260529-post-return-poison \
  --post-return-poison \
  --epochs 360 \
  --hot-pool 65536 \
  --filler-pool 65536 \
  --candidate-per-epoch 128 \
  --poison-per-epoch 1024 \
  --short-gap-per-epoch 64 \
  --tail-gap-per-epoch 512 \
  --burst-repeats 3 \
  --return-repeats 2 \
  --candidate-size 4096 \
  --scan-size 4096 \
  --poison-size 4096
```

### Trace 统计

| 指标 | 值 |
|---|---|
| 总请求数 | 1,543,680 |
| 工作集对象数 | 163,840 |
| 对象大小 | 4,096 字节 |
| 候选突发 | 138,240 |
| 候选返回 | 92,160 |
| 毒药突发 | 1,105,920 |
| 短间隙扫描 | 23,040 |
| 尾间隙扫描 | 184,320 |
| 候选短复用概率 | 100.0% |
| 毒药短复用概率 | 0.0% |
| 混合短复用概率 | 11.1% |

## 最终结果

### 缓存大小 0.1

| 算法 | 对象命中率 | 字节命中率 |
|---|---|---|
| LRU | 0.3957 | 0.3957 |
| LRB-BMR | 0.3783 | 0.3783 |
| 3LCache-BMR | 0.3824 | 0.3824 |
| 3LCache-OMR | 0.3843 | 0.3843 |
| **LOH（默认）** | **0.3732** ✓ | **0.3732** ✓ |

**解释**：
- LRB 被迫学习有问题的目标，表现略差于 LRU
- 3L 在未来距离信号不稳定时通常降级到 LRU 或类似行为
- 默认 LOH 使用接近性启发式，因毒药在返回后到达，它不受影响

### 缓存大小 0.001

| 算法 | 对象命中率 | 字节命中率 |
|---|---|---|
| LRU | 0.4328 | 0.4328 |
| LRB-BMR | **0.4928** ✗ | **0.4928** ✗ |
| 3LCache-BMR | 0.4230 | 0.4230 |
| 3LCache-OMR | 0.4218 | 0.4218 |
| **LOH（默认）** | **0.4167** ✓ | **0.4167** ✓ |

**解释**：
- LRB 在极小缓存下学到有害模式，大幅恶化
- 3L 也倾向于更差的行为，但不如 LRB 恶劣
- 默认 LOH 在两个缓存大小都保持最佳表现

## 关键发现

1. **非相位翻转**：无相位翻转，工作负载偏好始终保持稳定（候选返回）
2. **学习目标污染**：同样大小、同样本地特征的毒药对象污染对象级标签，不增加字节压力
3. **噪声放置**：毒药在有用返回之后注入，避免在 LOH 命中窗口前驱逐候选
4. **清晰对比**：默认 LOH 在两个极端缓存大小（0.1 和 0.001）上都表现最佳，证明了不同的学习目标难度

## 20260529 参数增强复验（等尺寸，不改 LOH）

为回答“在对象尺寸一致时，是否能进一步放大差距”，新增两组增强参数：

- **A 组（强化污染强度）**：`poison-per-epoch=2048`，其余近似基线
- **B 组（强化候选频次）**：`candidate-burst-repeats=5`、`poison-burst-repeats=1`、`return-repeats=3`

### A 组结果（推荐）

来源：`tmp/20260529-post-return-poison-A/logs/summary_runs.log` 与 `tmp/20260529-post-return-poison-A/logs/rerun_missing_0001.log`

| 缓存大小 | LOH | LRU | LRB-BMR | 3LCache-BMR | 3LCache-OMR | 结论 |
|---|---:|---:|---:|---:|---:|---|
| 0.1 | **0.333561** | 0.368551 | 0.354491 | 0.356497 | 0.359429 | **LOH 明显领先（相对次优 -0.020930）** |
| 0.001 | **0.381385** | 0.391256 | 0.472640 | 0.381887 | 0.381413 | **LOH 仍为最优（相对次优 -0.000028）** |

结论：

- 在 **等尺寸** 前提下，单纯污染 reuse 标签依然有效。
- 差距在 `cache=0.1` 下显著放大；在 `cache=0.001` 下为“微弱但稳定领先”。

### B 组结果（不采用）

来源：`tmp/20260529-post-return-poison-B/logs/summary_runs.log`

| 缓存大小 | LOH | LRU | LRB-BMR | 3LCache-BMR | 3LCache-OMR | 结论 |
|---|---:|---:|---:|---:|---:|---|
| 0.1 | 0.618485 | 0.646612 | **0.614998** | 0.624940 | 0.625183 | LOH 非最优 |
| 0.001 | **0.675921** | 0.707182 | 0.682528 | 0.694832 | 0.704720 | LOH 最优，但整体较差 |

结论：

- B 组在 `0.001` 有一定领先，但 `0.1` 失去最优，不满足“整体稳健”的目标。
- 因此本轮建议继续采用 **A 组** 作为等尺寸污染 reuse 的主结论版本。

## 产物位置

- Trace CSV: `tmp/20260529-post-return-poison/label_noise_preference.csv`
- Metadata: `tmp/20260529-post-return-poison/label_noise_metadata.csv`
- 摘要: `tmp/20260529-post-return-poison/label_noise_summary.md`
- 标签混合图: `tmp/20260529-post-return-poison/label_noise_mix.png`
- 标签时间线图: `tmp/20260529-post-return-poison/label_noise_timeline.png`
- 完整对比日志: `tmp/20260529-post-return-poison/logs/default_compare.log`
- 生成脚本: `scripts/gen_label_noise_preference_trace.py`
