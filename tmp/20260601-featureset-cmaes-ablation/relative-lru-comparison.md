# 3lcache / LRB / best_LOH 相对 LRU 对比报告（per-trace）

**方法说明**：对每条 trace 计算 `rel_mr = LOH_mr / LRU_mr`（per-trace），再对 group 内所有 trace 取均值。

**数据来源**：
- 3lcache / LRB：`tmp/20260601-featureset-cmaes-ablation/results/`（各 11536 条，全部 ok）
- CMA-ES 3lcache-target best_LOH (cache01)：`docs/20260422-ablation-per-group-cache01/cmaes版本LOH/baseline_summary_v7_3lcache-target.md`
- CMA-ES 3lcache-target best_LOH (cache0001)：`docs/20260423-ablation-per-group-fixxxx-cache0001/cmaes版本LOH/baseline_summary_v7_3lcache-target.md`
- LRU 基线（per-trace）：`lru_summary_v7.md`

**说明**：
- `3lcache`、`lrb`：CMA-ES 使用对应特征集在线评分，单一配置，不区分 MR/BMR 目标。
- `best_LOH`：v7 固定策略（MR 固定 `f001_orig`，BMR 按 `one_hit` 阈值选），数据来自 baseline summary 文档 best_LOH 列。

---

## 一、3lcache — cache01（cache_ratio=0.1）

| group | n | avg_LOH_mr | avg_LRU_mr | avg(rel_mr) | avg_LOH_bmr | avg_LRU_bmr | avg(rel_bmr) | avg(rel_combo) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| alibabaBlock | 1000 | 0.3297 | 0.4031 | **0.7787** | 0.4977 | 0.5774 | **0.8400** | **0.8094** |
| metaCDN | 3 | 0.3227 | 0.4155 | **0.7814** | 0.1828 | 0.2137 | **0.8574** | **0.8194** |
| metaKV | 5 | 0.0387 | 0.0585 | **0.6579** | 0.0993 | 0.0841 | **1.1588** | **0.9083** |
| tencentBlock | 4755 | 0.2273 | 0.2939 | **0.7717** | 0.3503 | 0.4006 | **0.9910** | **0.8813** |
| tencentPhoto | 2 | 0.2240 | 0.2526 | **0.8867** | 0.2304 | 0.2190 | **1.0522** | **0.9694** |
| wiki | 3 | 0.0745 | 0.1205 | **0.4994** | 0.1932 | 0.2031 | **0.9440** | **0.7217** |
| **avg(groups)** | - | - | - | **0.7293** | - | - | **0.9739** | **0.8516** |

---

## 二、3lcache — cache0001（cache_ratio=0.001）

| group | n | avg_LOH_mr | avg_LRU_mr | avg(rel_mr) | avg_LOH_bmr | avg_LRU_bmr | avg(rel_bmr) | avg(rel_combo) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| alibabaBlock | 1000 | 0.5615 | 0.6349 | **0.8805** | 0.7624 | 0.7973 | **0.9569** | **0.9187** |
| metaCDN | 3 | 0.3951 | 0.5627 | **0.7052** | 0.2350 | 0.2645 | **0.8909** | **0.7980** |
| metaKV | 5 | 0.1264 | 0.2404 | **0.5118** | 0.3279 | 0.2924 | **1.1203** | **0.8161** |
| tencentBlock | 4755 | 0.4481 | 0.5150 | **0.8761** | 0.6777 | 0.7078 | **0.9671** | **0.9216** |
| tencentPhoto | 2 | 0.6338 | 0.7026 | **0.9020** | 0.7042 | 0.6599 | **1.0672** | **0.9846** |
| wiki | 3 | 0.4387 | 0.6369 | **0.6475** | 0.7568 | 0.8121 | **0.9320** | **0.7898** |
| **avg(groups)** | - | - | - | **0.7539** | - | - | **0.9891** | **0.8715** |

---

## 三、LRB — cache01（cache_ratio=0.1）

| group | n | avg_LOH_mr | avg_LRU_mr | avg(rel_mr) | avg_LOH_bmr | avg_LRU_bmr | avg(rel_bmr) | avg(rel_combo) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| alibabaBlock | 1000 | 0.5358 | 0.4031 | **2.2760** | 0.7069 | 0.5774 | **1.9204** | **2.0982** |
| metaCDN | 3 | 0.4390 | 0.4155 | **1.0515** | 0.3013 | 0.2137 | **1.4009** | **1.2262** |
| metaKV | 5 | 0.2333 | 0.0585 | **4.2060** | 0.3597 | 0.0841 | **4.6139** | **4.4100** |
| tencentBlock | 4755 | 0.4475 | 0.2939 | **2.2070** | 0.6162 | 0.4006 | **2.8887** | **2.5478** |
| tencentPhoto | 2 | 0.7478 | 0.2526 | **2.9608** | 0.7519 | 0.2190 | **3.4338** | **3.1973** |
| wiki | 3 | 0.6011 | 0.1205 | **5.8910** | 0.8288 | 0.2031 | **4.2240** | **5.0575** |
| **avg(groups)** | - | - | - | **3.0987** | - | - | **3.0803** | **3.0895** |

---

## 四、LRB — cache0001（cache_ratio=0.001）

| group | n | avg_LOH_mr | avg_LRU_mr | avg(rel_mr) | avg_LOH_bmr | avg_LRU_bmr | avg(rel_bmr) | avg(rel_combo) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| alibabaBlock | 1000 | 0.6332 | 0.6349 | **1.0549** | 0.8028 | 0.7973 | **1.0226** | **1.0388** |
| metaCDN | 3 | 0.5368 | 0.5627 | **0.9601** | 0.3549 | 0.2645 | **1.3342** | **1.1472** |
| metaKV | 5 | 0.3801 | 0.2404 | **1.6181** | 0.4977 | 0.2924 | **1.7408** | **1.6794** |
| tencentBlock | 4755 | 0.5438 | 0.5150 | **1.0945** | 0.7382 | 0.7078 | **1.0635** | **1.0790** |
| tencentPhoto | 2 | 0.8594 | 0.7026 | **1.2230** | 0.8696 | 0.6599 | **1.3178** | **1.2704** |
| wiki | 3 | 0.7502 | 0.6369 | **1.2043** | 0.9192 | 0.8121 | **1.1318** | **1.1681** |
| **avg(groups)** | - | - | - | **1.1925** | - | - | **1.2685** | **1.2305** |

---

## 五、CMA-ES 3lcache-target best_LOH — cache01（cache_ratio=0.1）

> 数据来源：`baseline_summary_v7_3lcache-target.md` 的「MR/BMR 相对 LRU 比例」表 best_LOH 列（去掉 cloudphysics，avg 重新计算）。

| group | n | avg(rel_mr) | avg(rel_bmr) |
|---|---:|---:|---:|
| alibabaBlock | 1000 | **0.7577** | **0.8743** |
| metaCDN | 3 | **0.7957** | **0.8749** |
| metaKV | 5 | **0.6803** | **0.9258** |
| tencentBlock | 4755 | **0.7436** | **0.8935** |
| tencentPhoto | 2 | **0.8910** | **0.9945** |
| wiki | 3 | **0.5323** | **0.7708** |
| **avg(groups)** | - | **0.7334** | **0.8890** |

---

## 六、CMA-ES 3lcache-target best_LOH — cache0001（cache_ratio=0.001）

> 数据来源：`baseline_summary_v7_3lcache-target.md` 的「MR/BMR 相对 LRU 比例」表 best_LOH 列（去掉 cloudphysics，avg 重新计算）。

| group | n | avg(rel_mr) | avg(rel_bmr) |
|---|---:|---:|---:|
| alibabaBlock | 1000 | **0.8772** | **0.9513** |
| metaCDN | 3 | **0.6849** | **0.9187** |
| metaKV | 5 | **0.5571** | **0.9028** |
| tencentBlock | 4755 | **0.8793** | **0.9436** |
| tencentPhoto | 2 | **0.8732** | **0.9606** |
| wiki | 3 | **0.6603** | **0.8631** |
| **avg(groups)** | - | **0.7553** | **0.9234** |

---

## Notes

- `avg(rel_mr)` = 每条 trace 的 `LOH_mr / LRU_mr` 在 group 内取均值；`avg(rel_combo)` = (avg(rel_mr) + avg(rel_bmr)) / 2。
- `avg(groups)` = 6 group 值的简单算术平均（非加权）。
- LRU 基线来自 `lru_summary_v7.md` per-trace 数据。
- LRB 特征集在 cache_ratio=0.1 下表现较差（特别是 LRU miss ratio 极小的 trace 上，微小绝对差异导致巨大比值）。
- 3lcache 的 BMR 在 metaKV、tencentPhoto 可能 >1（3lcache 主要优化 MR）。
- CMA-ES 3lcache-target best_LOH 数据来自 baseline summary 文档 best_LOH 列（已去掉 cloudphysics 重新计算 avg）。

---

## 总结

### avg(rel_mr) 对比

| group | 3lcache cache01 | 3lcache cache0001 | LRB cache01 | LRB cache0001 | best_LOH cache01 | best_LOH cache0001 |
|---|---:|---:|---:|---:|---:|---:|
| alibabaBlock | 0.7787 | 0.8805 | 2.2760 | 1.0549 | 0.7577 | 0.8772 |
| metaCDN | 0.7814 | 0.7052 | 1.0515 | 0.9601 | 0.7957 | 0.6849 |
| metaKV | 0.6579 | 0.5118 | 4.2060 | 1.6181 | 0.6803 | 0.5571 |
| tencentBlock | 0.7717 | 0.8761 | 2.2070 | 1.0945 | 0.7436 | 0.8793 |
| tencentPhoto | 0.8867 | 0.9020 | 2.9608 | 1.2230 | 0.8910 | 0.8732 |
| wiki | 0.4994 | 0.6475 | 5.8910 | 1.2043 | 0.5323 | 0.6603 |
| **avg(groups)** | **0.7293** | **0.7539** | **3.0987** | **1.1925** | **0.7334** | **0.7553** |

### avg(rel_bmr) 对比

| group | 3lcache cache01 | 3lcache cache0001 | LRB cache01 | LRB cache0001 | best_LOH cache01 | best_LOH cache0001 |
|---|---:|---:|---:|---:|---:|---:|
| alibabaBlock | 0.8400 | 0.9569 | 1.9204 | 1.0226 | 0.8743 | 0.9513 |
| metaCDN | 0.8574 | 0.8909 | 1.4009 | 1.3342 | 0.8749 | 0.9187 |
| metaKV | 1.1588 | 1.1203 | 4.6139 | 1.7408 | 0.9258 | 0.9028 |
| tencentBlock | 0.9910 | 0.9671 | 2.8887 | 1.0635 | 0.8935 | 0.9436 |
| tencentPhoto | 1.0522 | 1.0672 | 3.4338 | 1.3178 | 0.9945 | 0.9606 |
| wiki | 0.9440 | 0.9320 | 4.2240 | 1.1318 | 0.7708 | 0.8631 |
| **avg(groups)** | **0.9739** | **0.9891** | **3.0803** | **1.2685** | **0.8890** | **0.9234** |

---

## 综合均值（两缓存 × MR/BMR 四值平均）

> 每个 group 一个标量：`mean(cache01_rel_mr, cache0001_rel_mr, cache01_rel_bmr, cache0001_rel_bmr)`

| group | 3lcache | LRB | best_LOH |
|---|---:|---:|---:|
| alibabaBlock | **0.8660** | 1.5685 | **0.8651** |
| metaCDN | **0.8187** | 1.1867 | **0.8186** |
| metaKV | 0.8622 | 3.0447 | **0.7665** |
| tencentBlock | **0.9015** | 1.8134 | **0.8650** |
| tencentPhoto | 0.9770 | 2.2339 | **0.9298** |
| wiki | **0.7557** | 3.1128 | **0.7066** |
| **avg(groups)** | **0.8615** | 2.1600 | **0.8253** |

![Avg. Rel. MR by group](rsd_deep_feature_ablation.png)
