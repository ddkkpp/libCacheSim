# LOH vs GDSF 差距分析与改进方案

**日期**: 2026-04-15
**来源**: `docs/20260415-ablation-per-group/baseline_summary.md`

## 1. 现状总览

### 1.1 MR（简单平均）胜负统计

| group | n_traces | LOH best_MR | 最强对手 | 对手 MR | LOH 差距 | LOH 胜? |
|---|---|---|---|---|---|---|
| alibabaBlock | 1000 | **0.3148** | GDSF 0.3314 | -5.0% | ✅ |
| cloudphysics | 106 | **0.3752** | GDSF 0.3867 | -3.0% | ✅ |
| tencentBlock | 4755 | **0.2101** | GLCache 0.2304| -8.8% | ✅ |
| twitter | 11 | **0.1304** | GDSF 0.1336 | -2.4% | ✅ |
| wiki | 3 | **0.0740** | GDSF 0.0746 | -0.8% | ✅ |
| tencentPhoto | 2 | 0.2238 | GDSF **0.2236** | +0.1% | ≈ |
| metaCDN | 3 | 0.3275 | GDSF **0.3200** | +2.3% | ❌ |
| metaKV | 5 | 0.0390 | GDSF **0.0379** | +2.9% | ❌ |

**总结**: LOH 在 5/8 组最优，1 组持平，2 组小幅落后（均输给 GDSF，差距 2-3%）。

### 1.2 LOH 落后的具体 trace

**metaCDN**（RC=256, SC=16, MRW=1.0）:
| trace | GDSF MR | LOH best MR | 最佳 feature | 差距 |
|---|---|---|---|---|
| meta_reag | 0.2689 | 0.2707 (f011) | +0.7% |
| meta_rnha | 0.3628 | 0.3774 (f111) | +4.0% |
| meta_rprn | 0.3284 | 0.3343 (f011) | +1.8% |

**metaKV**（RC=256, SC=16, MRW=1.0）:
| trace | GDSF MR | LOH best MR | 最佳 feature | 差距 |
|---|---|---|---|---|
| 202206_kv | 0.0325 | 0.033298 (f010) | +2.5% |
| 202210_kv | 0.0325 | 0.033263 (f010) | +2.4% |
| 202312_kv | 0.0233 | 0.023925 (f010) | +2.7% |
| 202401_kv | 0.0474 | 0.049164 (f010) | +3.7% |
| meta_kvcache_1 | 0.0540 | 0.055560 (f010) | +2.9% |

## 2. 根因分析

### 2.1 GDSF 为什么在这些 trace 上赢

GDSF 的评分公式：`score = (freq + 1) × cost / size`。

对于 CDN 和 KV 工作负载（对象大小差异大）：
- GDSF 天然偏好"高频率 + 小体积"的对象
- 公式是固定的，无需学习/优化，从第一个请求就生效
- 这恰好是这类工作负载的最优策略

### 2.2 LOH 的表达能力不是问题

LOH 的 compound 模式（LOG1P=1）下：
- `freq_size = log1p(freq) / log1p(size)`（比率，类似 GDSF 的 freq/size）
- `sign[4] = +1`（高 freq/size 比 → 加分 → 保留 → 与 GDSF 方向一致）

因此 LOH **理论上能通过 w4≈1 精确表达 GDSF** 的核心信号。表达能力不是瓶颈。

### 2.3 ★ 真正根因：CMA-ES 退化检测器反复触发冷重启（thrashing）

**实验证据——CMA-ES `full_restart` 次数对比（f010 feature）**:

| trace | full_restart 次数 | LOH vs GDSF |
|---|---|---|
| 202312_kv_traces_all | **445,471** | LOH 输 |
| 202210_kv_traces_all_sort | **66,130** | LOH 输 |
| 202206_kv_traces_all | **66,106** | LOH 输 |
| wiki_2016u | **58,137** | 视配置 |
| 202401_kv_traces_all_sort | **39,932** | LOH 输 |
| meta_kvcache_traces_1 | **13,424** | LOH 输 |
| meta_reag | 152 | LOH 接近 GDSF |
| alibabaBlock_* | **0** | LOH 赢 |
| tencentBlock 1063 | **0** | LOH 赢 |

**相关性极高**：restart 次数越多的 trace，LOH 越输给 GDSF。

**机制分析**——退化检测器参数（LOH.c line 313-317）：
```
threshold = 1.5   （EMA > best × 1.5 视为退化）
patience  = 5     （连续 5 epoch 退化 → 触发重启）
ema_alpha = 0.3   （EMA 平滑系数，偏高 → 跟随噪声）
warmup    = 20    （重启后 20 epoch 免检）
cooldown  = 15    （重启后 15 epoch 冷却）
```

**因果链**：
1. metaKV/metaCDN 工作负载非平稳（请求模式持续变化）
2. miss ratio 自然波动 → EMA 大幅震荡
3. 退化检测器以为"权重变差了"，其实只是工作负载变化
4. 触发 `full_restart(mean=0.5, sigma=0.2)` → 丢弃所有学到的权重
5. 下一个 20+15=35 epoch 重新热身 → 又遭遇波动 → 再次重启
6. 无限循环：CMA-ES 永远在 mean=0.5 附近震荡，无法收敛

**对比**：
- tencentBlock 1063：工作负载稳定 → 0 次重启 → CMA-ES 充分收敛 → LOH 赢
- GDSF：固定公式，不需要收敛，永远稳定

### 2.4 次要因素

**A. 每次冷重启的代价**：
- 重置到 mean=0.5（所有权重相等 → 近似 LRU），sigma=0.2
- 需要多代迭代才能重新找到好权重
- 在 metaKV 上，平均每 ~25 epoch 就重启一次（never enough time to converge）

**B. log1p 压缩效应**：
- LOH 使用 `log1p(freq)/log1p(size)` 而非原始 `freq/size`
- log1p 压缩大值差距：`log1p(1000)/log1p(100000) = 6.91/11.51 = 0.60`
  而原始比率：`1000/100000 = 0.01`
- 导致 LOH 对大对象的惩罚弱于 GDSF（但这是次要因素，因为 CMA-ES 权重可以放大）

**C. CMA-ES 评估间隔 (rl_update_interval=500)**：
- 每 500 个请求评估一次 → 评估信号非常嘈杂
- metaKV 一天的 QPS 高（1.6B req），500 请求窗口内统计意义弱

## 3. 改进方案

### 3.1 方案 A: 关闭或大幅放松退化检测器（最直接）

**方案 A1 — 完全关闭退化检测**：
```bash
export LOH_CMAES_DEGRADE_DETECT=0
```
让 CMA-ES 内部的 aIPOP restart 机制自行管理（基于 sigma 收敛而非 MR 波动）。

**方案 A2 — 大幅放松阈值**：
```bash
export LOH_CMAES_DEGRADE_THRESHOLD=3.0     # 原 1.5 → 3.0（需要 MR 恶化到 3 倍才重启）
export LOH_CMAES_DEGRADE_PATIENCE=20        # 原 5 → 20（需连续 20 epoch 退化）
export LOH_CMAES_DEGRADE_EMA_ALPHA=0.1      # 原 0.3 → 0.1（更重的平滑，不跟踪噪声）
```

**预期效果**：在 metaKV/metaCDN 上消除 thrashing，CMA-ES 可以收敛到好权重。

### 3.2 方案 B: 温重启替代冷重启

当确实需要重启时，不要丢弃学到的知识：
```c
// 当前（冷重启）:
loh_cmaes_full_restart(handle, 0.5, 0.2);  // 回到等权值

// 改为（温重启）:
loh_cmaes_warm_restart(handle);  // 从历史最优解 restart，sigma 适当放大
```

bridge.cpp 的 sigma-overflow 机制已经支持 warm restart（使用 `best_ever_pheno_`），
只需让 LOH.c 的退化检测也走 warm restart 路径。

### 3.3 方案 C: GDSF warmup fallback

CMA-ES 收敛前使用 GDSF-like 评分作为 fallback：
- warmup 阶段：`score = +w_freq × log1p(freq) - w_size × log1p(size)`
- 写死 GDSF-like 初始权重（而非 0.5 等权），例如 `w = [0, 0.8, 0, 0, 1.0, 0]`
- 这样即使 CMA-ES 不收敛，baseline 也近似 GDSF

### 3.4 方案 D: 增大评估窗口减少噪声

`rl_update_interval=500` 太短，信号太嘈杂：
```bash
export LOH_RL_UPDATE_INTERVAL=5000   # 或 10000
```
更长的评估窗口 → miss ratio 统计更稳定 → 退化检测误报率降低。

### 3.5 方案 E: 候选数调优

对 metaCDN 和 metaKV 做类似 feature-cand-sweep 的候选数搜索。
当前 sweep 只覆盖 meta_reag + 1063 + w82 + w74。

## 4. 优先级建议

| 优先级 | 方案 | 预期改善 | 工作量 | 风险 |
|---|---|---|---|---|
| 🟥 高 | A1: 关闭退化检测 | 消除 thrashing，MR 可能立刻追上 GDSF | 零（环境变量） | 低（aIPOP 自带 restart） |
| 🟥 高 | A2: 放松阈值 | 减少误报，CMA-ES 可以收敛 | 零（环境变量） | 低 |
| 🟧 中 | B: 温重启 | 保留学习成果 | 中（修改 LOH.c） | 低 |
| 🟧 中 | C: GDSF warmup | 减少冷启动 MR 损失 | 中 | 低 |
| 🟧 中 | D: 增大评估窗口 | 减少信号噪声 | 零（环境变量） | 需验证 |
| 🟨 低 | E: 候选数调优 | 可能发现更优 RC/SC | 低（复用脚本） | 低 |

## 5. 总结

LOH 在 8 组 trace 中的 5 组（含最大的 tencentBlock 4755 traces）取得最优 MR，在 2 组上小幅（2-3%）落后于 GDSF。

**根因是 CMA-ES 退化检测器（degrade detect）在非平稳工作负载上反复触发冷重启（thrashing）**：
- metaKV 202312: **445K 次**冷重启，CMA-ES 始终在 mean=0.5 附近震荡
- metaKV 202206: **66K 次**冷重启
- 对比 tencentBlock 1063: **0 次**重启，CMA-ES 充分收敛

LOH 的评分公式在理论上可以精确表达 GDSF（`freq_size = freq/size`, sign=+1），但退化检测器阻止了 CMA-ES 收敛到最优权重。

**最直接的修复**：关闭退化检测（`LOH_CMAES_DEGRADE_DETECT=0`），让 aIPOP-CMA-ES 自身管理 restart。

## 6. 验证计划

### 6.1 关键发现：旧 binary vs 新 binary

baseline_summary.md 中的 metaKV/metaCDN LOH 数据来自 `tmp/20260411-feature-ablation/`：

| 类别 | 运行时间 | degrade_detect | 证据 |
|---|---|---|---|
| metaKV/metaCDN | 04-09 | **ON** (=1) | 日志有 `CMA-ES degrade detect:` 行 |
| alibabaBlock 等 | 04-11+ | **OFF** (=0) | 日志无此行 |

二进制在 4/9 与 4/11 之间重编译，`degrade_detect` 默认值从 1→0。

当前 `_build_rel/bin/cachesim` (04-15 编译) 默认 `degrade_detect=0`。

### 6.2 重跑实验 (已启动)

- 目录: `tmp/20260415-meta-rerun/`
- 规模: 8 traces × 8 features = 64 experiments
- 配置: RC=256, SC=16, nonblocked, degrade_detect=0 (默认)
- 对比 baseline: `tmp/20260411-feature-ablation/` (degrade_detect=1)

### 6.3 后续步骤

1. 收集 64 个实验结果，与旧版 MR 对比
2. 如果 LOH MR 显著改善（追上或超过 GDSF），则确认根因即是 degrade_detect thrashing
3. 如果改善有限，需进一步排查 CMA-ES 收敛问题（评估窗口、lambda、sigma）
4. 在 LOH 已赢的 trace（1063, alibabaBlock 代表）上确认无回退
