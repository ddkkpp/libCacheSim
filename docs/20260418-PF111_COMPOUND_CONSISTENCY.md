# pf111 Compound 排名一致性验证

> 日期：2026-04-18
> 实验目录：`tmp/20260416-perfeat-sweep-allgroups/`
> 原始数据源：见 §2

## 1. 目的

验证新的 per-feature sweep 实验中 pf111（全 log1p）下 8 种 compound 配置的排名，是否与原始 feature ablation 实验（默认 `LOH_FEATURE_LOG1P=1`，等价 pf111）一致。

如果一致 → pf111 结果可信，可直接使用新数据做 AUTO_PERFEAT 策略评估。
如果不一致 → 说明 CMA-ES 存在 run-to-run variance，compound 排名本身不够稳定。

## 2. 数据覆盖

| 数据源 | Traces 数 | 类型 | 说明 |
|--------|-----------|------|------|
| 0411-feature-ablation/summary.csv | 114 | cloudphysics (w01-w99+), wiki_2016u (不完整) | 仅 8-compound 完整的 |
| 0411-feature-ablation/results/ | +5 | alibabaBlock (`_1M` 命名) | 104, 152, 590, 774, 815 |
| 0411-feature-ablation/results/ | +1 | wiki_2016u | summary.csv 漏录 f100-f111，文件完整 |
| 0411-wiki-feature-ablation/results/ | +1 | wiki_2019t | 完整 8 compound |
| 0413-feature-ablation-ext/results/ | +13 | tencentBlock | 2610, 2902 等 13 个 |
| 0416-perfeat-sweep-allgroups (新) | 44 | 14 cp + 11 ali + 13 tc + 2 wiki | 非 meta traces |
| 0416-per-feature-sweep (新) | 7 | 4 metaCDN + 3 metaKV | meta/kv traces |

交集（可对比）：**41 traces**
- cloudphysics: 14 (w10, w12, w19, w21, w22, w35, w36, w46, w58, w59, w60, w64, w83, w85)
- alibabaBlock: 5 (104, 152, 590, 774, 815) — 其余 6 个无原始数据
- tencentBlock: 13 (2610, 2902, 3310, 4769, 13068, 18304, 18447, 19734, 21042, 21551, 21582, 23871, 25434)
- wiki: 2 (wiki_2016u, wiki_2019t) — wiki_2016u 的 f100-f111 在 results/ 文件中存在（summary.csv 漏录）
- metaCDN: 4 (meta_kvcache_traces_1, meta_reag, meta_rnha, meta_rprn)
- metaKV: 3 (202206_kv_traces_all, 202210_kv_traces_all_sort, 202401_kv_traces_all_sort)

**注意**: alibabaBlock 原始结果使用 `_1M` 命名（1M 对象子集 trace），新 sweep 也使用同一 1M trace，两边 trace 一致（已验证 req 数相同）。

## 3. 总体结果

| 指标 | 值 |
|------|-----|
| 可对比 traces | 41 |
| best compound 完全匹配 | **14 (34.1%)** |
| 平均 cross-regret | **5.08%** |
| 最大 cross-regret | **77.7%** (alibabaBlock_590) |

**cross-regret 定义**：如果按新实验选出的 best compound 去原始实验执行，相对原始 best compound 的 MR 增量百分比。

## 4. 逐 trace 对比

### 4.1 alibabaBlock (5 traces, match 1/5 = 20.0%)

| trace | orig_best | orig_MR | new_best | new_MR | match | x-regret | 备注 |
|-------|-----------|---------|----------|--------|-------|----------|------|
| alibabaBlock_104 | f001 | 0.2605 | f001 | 0.2779 | ✓ | 0.00% | |
| alibabaBlock_152 | f110 | 0.1444 | f010 | 0.1442 | ✗ | 0.02% | 极小差 |
| alibabaBlock_590 | f001 | 0.0646 | f000 | 0.0609 | ✗ | **77.67%** | f000 orig=0.115 vs new=0.061 |
| alibabaBlock_774 | f000 | 0.1271 | f100 | 0.1297 | ✗ | 1.19% | |
| alibabaBlock_815 | f111 | 0.4447 | f010 | 0.4435 | ✗ | 0.21% | |

> alibabaBlock_590 的 77.7% regret 来源：f000 在原始实验中 MR=0.1148 而新实验中仅 0.0609——同一 compound、同一 trace 两次运行 MR 相差近 2 倍，CMA-ES variance 极端情况。

### 4.2 tencentBlock (13 traces, match 5/13 = 38.5%)

| trace | orig_best | orig_MR | new_best | new_MR | match | x-regret |
|-------|-----------|---------|----------|--------|-------|----------|
| tencentBlock_2610 | f001 | 0.1773 | f001 | 0.1723 | ✓ | 0.00% |
| tencentBlock_2902 | f011 | 0.1394 | f011 | 0.1270 | ✓ | 0.00% |
| tencentBlock_3310 | f010 | 0.5389 | f011 | 0.5380 | ✗ | 0.16% |
| tencentBlock_4769 | f010 | 0.2638 | f000 | 0.2608 | ✗ | 5.17% |
| tencentBlock_13068 | f100 | 0.1205 | f110 | 0.1202 | ✗ | 0.41% |
| tencentBlock_18304 | f110 | 0.000889 | f100 | 0.000865 | ✗ | **41.40%** |
| tencentBlock_18447 | f100 | 0.3922 | f100 | 0.4206 | ✓ | 0.00% |
| tencentBlock_19734 | f000 | 0.2031 | f000 | 0.2055 | ✓ | 0.00% |
| tencentBlock_21042 | f100 | 0.0103 | f111 | 0.0105 | ✗ | 3.08% |
| tencentBlock_21551 | f101 | 0.1976 | f001 | 0.1916 | ✗ | 3.07% |
| tencentBlock_21582 | f001 | 0.0765 | f111 | 0.0766 | ✗ | 8.11% |
| tencentBlock_23871 | f010 | 0.0021 | f111 | 0.0021 | ✗ | 1.23% |
| tencentBlock_25434 | f000 | 1.0000 | f000 | 1.0000 | ✓ | 0.00% |

> tencentBlock_18304 的 41.4% regret：orig f110=0.000889 vs orig f100=0.001257，绝对差 0.000368，但 MR 极低导致百分比放大。

### 4.3 cloudphysics (14 traces, match 4/14 = 28.6%)

| trace | orig_best | orig_MR | new_best | new_MR | match | x-regret |
|-------|-----------|---------|----------|--------|-------|----------|
| w10 | f011 | 0.3566 | f010 | 0.3454 | ✗ | 5.65% |
| w12 | f010 | 0.0115 | f010 | 0.0113 | ✓ | 0.00% |
| w19 | f011 | 0.1009 | f001 | 0.0958 | ✗ | 0.72% |
| w21 | f011 | 0.8877 | f010 | 0.8107 | ✗ | 0.46% |
| w22 | f111 | 0.8752 | f010 | 0.8658 | ✗ | 0.16% |
| w35 | f011 | 0.0495 | f111 | 0.0488 | ✗ | 1.89% |
| w36 | f100 | 0.1382 | f100 | 0.1369 | ✓ | 0.00% |
| w46 | f010 | 0.4279 | f011 | 0.4287 | ✗ | 0.31% |
| w58 | f011 | 0.2347 | f000 | 0.2285 | ✗ | **14.44%** |
| w59 | f001 | 0.5689 | f001 | 0.5852 | ✓ | 0.00% |
| w60 | f010 | 0.5169 | f101 | 0.4030 | ✗ | **19.93%** |
| w64 | f110 | 0.8935 | f101 | 0.8916 | ✗ | 0.31% |
| w83 | f011 | 0.3023 | f111 | 0.2828 | ✗ | 1.46% |
| w85 | f011 | 0.5695 | f011 | 0.5258 | ✓ | 0.00% |

### 4.4 wiki (2 traces, match 0/2 = 0%)

| trace | orig_best | orig_MR | new_best | new_MR | match | x-regret |
|-------|-----------|---------|----------|--------|-------|----------|
| wiki_2016u | f101 | 0.0231 | f011 | 0.0222 | ✗ | 1.63% |
| wiki_2019t | f010 | 0.1706 | f111 | 0.1701 | ✗ | 0.05% |

### 4.5 metaCDN (4 traces, match 1/4 = 25.0%)

| trace | orig_best | orig_MR | new_best | new_MR | match | x-regret |
|-------|-----------|---------|----------|--------|-------|----------|
| meta_kvcache_traces_1 | f010 | 0.0556 | f010 | 0.0550 | ✓ | 0.00% |
| meta_reag | f011 | 0.2707 | f010 | 0.2693 | ✗ | 4.51% |
| meta_rnha | f111 | 0.3774 | f000 | 0.3700 | ✗ | **12.54%** |
| meta_rprn | f011 | 0.3343 | f010 | 0.3314 | ✗ | 2.68% |

> meta_rnha 的 12.5% regret：原始 best=f111(0.377)，新选出 f000，查原始 f000=0.425，差距大。

### 4.6 metaKV (3 traces, match 3/3 = 100%)

| trace | orig_best | orig_MR | new_best | new_MR | match | x-regret |
|-------|-----------|---------|----------|--------|-------|----------|
| 202206_kv_traces_all | f010 | 0.0333 | f010 | 0.0329 | ✓ | 0.00% |
| 202210_kv_traces_all_sort | f010 | 0.0333 | f010 | 0.0333 | ✓ | 0.00% |
| 202401_kv_traces_all_sort | f010 | 0.0492 | f010 | 0.0487 | ✓ | 0.00% |

> metaKV traces compound 排名完全一致且 regret=0%，说明这类 KV workload 对 CMA-ES 来说优化空间较稳定。

### 4.7 分组汇总

| Group | n | match | match% | avg x-regret | max x-regret | regret<1% | regret<2% |
|-------|---|-------|--------|--------------|--------------|-----------|-----------|
| alibabaBlock | 5 | 1 | 20.0% | 15.82% | 77.67% | 3 | 4 |
| cloudphysics | 14 | 4 | 28.6% | 3.24% | 19.93% | 9 | 11 |
| tencentBlock | 13 | 5 | 38.5% | 4.82% | 41.40% | 7 | 8 |
| wiki | 2 | 0 | 0.0% | 0.84% | 1.63% | 1 | 2 |
| metaCDN | 4 | 1 | 25.0% | 4.93% | 12.54% | 1 | 1 |
| metaKV | 3 | 3 | 100.0% | 0.00% | 0.00% | 3 | 3 |
| **All** | **41** | **14** | **34.1%** | **5.08%** | **77.7%** | **25** | **30** |

## 5. Top-10 最差 cross-regret

| # | trace | orig_best | new_best | cross-regret | 原因 |
|---|-------|-----------|----------|--------------|------|
| 1 | alibabaBlock_590 | f001 | f000 | +77.7% | f000 MR: orig 0.115 vs new 0.061 |
| 2 | tencentBlock_18304 | f110 | f100 | +41.4% | MR≈0.0009，绝对差微小 |
| 3 | w60 | f010 | f101 | +19.9% | f101: orig 0.620 vs new 0.403 |
| 4 | w58 | f011 | f000 | +14.4% | f000: orig 0.269 vs new 0.228 |
| 5 | meta_rnha | f111 | f000 | +12.5% | f000: orig 0.425 vs new 0.370 |
| 6 | tencentBlock_21582 | f001 | f111 | +8.1% | |
| 7 | w10 | f011 | f010 | +5.6% | |
| 8 | tencentBlock_4769 | f010 | f000 | +5.2% | |
| 9 | meta_reag | f011 | f010 | +4.5% | |
| 10 | tencentBlock_21042 | f100 | f111 | +3.1% | |

## 6. 分析与结论

### 6.1 compound 排名不稳定

同为 pf111（全 log1p），两次独立运行的 best compound **仅 34.1% 一致**（41 traces 中 14 match）。这意味着：
- CMA-ES 优化存在显著 **run-to-run variance**
- 单次运行无法可靠确定 "全局最优 compound"
- **原始 ablation 的 compound 排名本身也不可作为 ground truth**

### 6.2 同一 compound 同一 trace 的 MR 差异

最极端案例 alibabaBlock_590 f000：原始 MR=0.1148，新实验 MR=0.0609（差近 2 倍）。这不是 per-feature mode 的问题，而是 CMA-ES 随机种子、优化路径不同导致的收敛差异。

### 6.3 绝对 MR 对比

多数 trace 新实验 MR 更低（负 MR_diff），说明新版代码/参数可能有改善，或 CMA-ES 高随机性下某次运行碰巧更好。

### 6.4 对 AUTO_PERFEAT 策略评估的影响

上一步分析显示 AUTO_PERFEAT 仅 56.1% 准确率。但由于 compound 排名本身就不稳定（29% match），per-feature mode 的"最优解"也存在同样噪声。因此：
- AUTO_PERFEAT 的评估精度上界受 CMA-ES variance 限制
- 要做可靠的策略评估，**需要多次重复实验取均值**
- metaKV traces 例外：3/3 完全匹配且 0% regret，说明简单 workload 下 CMA-ES 收敛稳定

### 6.5 高 regret 个案说明

| trace | 说明 |
|-------|------|
| alibabaBlock_590 | f000 两次运行 MR 差近 2 倍（0.115→0.061），极端 CMA-ES variance |
| tencentBlock_18304 | MR ≈ 0.0009，绝对差 0.000368，百分比被放大到 41%，实际可忽略 |
| w60 | f101 两次运行 MR 差 0.217（0.620→0.403），该 trace 对 compound 极敏感 |
| w58 | f000 两次运行 MR 差 0.040（0.269→0.228），中等 variance |
| meta_rnha | f000 在原始实验 MR=0.425，新实验 MR=0.370；orig best=f111(0.377)，选错代价大 |

## 7. 脚本与产物

- 对比脚本:
  - `tmp/compare_pf111_vs_original.py` (初版，仅 summary.csv)
  - `tmp/compare_pf111_full.py` (加入 ext tencentBlock)
  - `tmp/compare_pf111_v2.py` (完整版，含 alibabaBlock _1M + wiki_2016u + wiki_2019t + ext)
- 新 sweep 数据:
  - `tmp/20260416-perfeat-sweep-allgroups/summary.csv` (44 非 meta traces)
  - `tmp/20260416-per-feature-sweep/summary.csv` (7 meta/kv traces)
- 原始数据:
  - `tmp/20260411-feature-ablation/summary.csv` (cloudphysics)
  - `tmp/20260411-feature-ablation/results/` (alibabaBlock _1M files)
  - `tmp/20260411-wiki-feature-ablation/results/` (wiki_2019t)
  - `tmp/20260413-feature-ablation-ext/results/` (tencentBlock)
