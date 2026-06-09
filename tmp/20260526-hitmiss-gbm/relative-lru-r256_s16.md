# hitmiss GBM + CMA-ES 3lcache-target best_LOH 相对 LRU 对比报告（per-trace）

**方法说明**：对每条 trace 计算 `rel_mr = LOH_mr / LRU_mr`（per-trace），再对 group 内所有 trace 取均值。

**数据来源**：
- hitmiss GBM：`tmp/20260526-hitmiss-gbm/results_all.tsv`（23072 行，743 条 NA 已从 `result/*.cachesim` 回填，余 6 条 metaKV NA）
- CMA-ES 3lcache-target best_LOH (cache01)：`docs/20260422-ablation-per-group-cache01/cmaes版本LOH/baseline_summary_v7_3lcache-target.md`
- CMA-ES 3lcache-target best_LOH (cache0001)：`docs/20260423-ablation-per-group-fixxxx-cache0001/cmaes版本LOH/baseline_summary_v7_3lcache-target.md`
- DRL 3lcache-target best_LOH (cache01)：`docs/20260422-ablation-per-group-cache01/drl版本LOH/baseline_summary_v7_3lcache-target.md`
- DRL 3lcache-omr best_LOH (cache0001)：`docs/20260423-ablation-per-group-cache0001/drl版本/baseline_summary_v7_3lcache-omr.md`
- LRU 基线（per-trace）：`lru_summary_v7.md`

**cfg 说明**：`f001_orig`（metric=MR），`f100_ns`、`f101_orig`（metric=BMR）。
**best_LOH 策略（v7）**：MR 固定 `f001_orig`，BMR 按 `one_hit` 阈值选 `f100_ns`/`f101_orig`。

---

## 一、hitmiss GBM — cache01（cache_ratio=0.1）

### cache01 / MR 目标（cfg=f001_orig）

| group | n | avg_LOH_mr | avg_LRU_mr | avg(rel_mr) | avg_LOH_bmr | avg_LRU_bmr | avg(rel_bmr) | avg(rel_combo) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| alibabaBlock | 1000 | 0.4061 | 0.4031 | **1.0005** | 0.5775 | 0.5774 | **0.9970** | **0.9987** |
| metaCDN | 3 | 0.4135 | 0.4155 | **0.9956** | 0.2130 | 0.2137 | **0.9968** | **0.9962** |
| metaKV | 5 | 0.0546 | 0.0585 | **0.9171** | 0.0831 | 0.0841 | **0.9849** | **0.9510** |
| tencentBlock | 4755 | 0.2941 | 0.2939 | **1.0019** | 0.4006 | 0.4006 | **1.0396** | **1.0207** |
| tencentPhoto | 2 | 0.2504 | 0.2526 | **0.9914** | 0.2177 | 0.2190 | **0.9942** | **0.9928** |
| wiki | 3 | 0.1161 | 0.1205 | **0.9382** | 0.1992 | 0.2031 | **0.9818** | **0.9600** |
| **avg(groups)** | - | - | - | **0.9741** | - | - | **0.9990** | **0.9866** |

### cache01 / BMR 目标（cfg=f100_ns + f101_orig）

| group | n | avg_LOH_mr | avg_LRU_mr | avg(rel_mr) | avg_LOH_bmr | avg_LRU_bmr | avg(rel_bmr) | avg(rel_combo) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| alibabaBlock | 1000 | 0.4188 | 0.4031 | **1.0245** | 0.5826 | 0.5774 | **1.0020** | **1.0132** |
| metaCDN | 3 | 0.4137 | 0.4155 | **0.9960** | 0.2130 | 0.2137 | **0.9968** | **0.9964** |
| metaKV | 2 | 0.0581 | 0.0629 | **0.9212** | 0.0820 | 0.0837 | **0.9790** | **0.9501** |
| tencentBlock | 4755 | 0.2959 | 0.2939 | **1.0211** | 0.4014 | 0.4006 | **1.0004** | **1.0108** |
| tencentPhoto | 2 | 0.2465 | 0.2526 | **0.9759** | 0.2152 | 0.2190 | **0.9828** | **0.9793** |
| wiki | 3 | 0.1140 | 0.1205 | **0.9144** | 0.1955 | 0.2031 | **0.9643** | **0.9394** |
| **avg(groups)** | - | - | - | **0.9755** | - | - | **0.9876** | **0.9815** |

---

## 二、hitmiss GBM — cache0001（cache_ratio=0.001）

### cache0001 / MR 目标（cfg=f001_orig）

| group | n | avg_LOH_mr | avg_LRU_mr | avg(rel_mr) | avg_LOH_bmr | avg_LRU_bmr | avg(rel_bmr) | avg(rel_combo) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| alibabaBlock | 1000 | 0.6239 | 0.6349 | **0.9853** | 0.7939 | 0.7973 | **0.9956** | **0.9904** |
| metaCDN | 3 | 0.5621 | 0.5627 | **0.9991** | 0.2644 | 0.2645 | **0.9997** | **0.9994** |
| metaKV | 3 | 0.2484 | 0.2625 | **0.9406** | 0.3155 | 0.3181 | **0.9916** | **0.9661** |
| tencentBlock | 4755 | 0.5114 | 0.5150 | **0.9926** | 0.7054 | 0.7078 | **0.9964** | **0.9945** |
| tencentPhoto | 2 | 0.6985 | 0.7026 | **0.9941** | 0.6589 | 0.6599 | **0.9986** | **0.9963** |
| wiki | 3 | 0.6267 | 0.6369 | **0.9813** | 0.8091 | 0.8121 | **0.9964** | **0.9888** |
| **avg(groups)** | - | - | - | **0.9822** | - | - | **0.9964** | **0.9893** |

### cache0001 / BMR 目标（cfg=f100_ns + f101_orig）

| group | n | avg_LOH_mr | avg_LRU_mr | avg(rel_mr) | avg_LOH_bmr | avg_LRU_bmr | avg(rel_bmr) | avg(rel_combo) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| alibabaBlock | 1000 | 0.6210 | 0.6349 | **0.9804** | 0.7916 | 0.7973 | **0.9925** | **0.9865** |
| metaCDN | 3 | 0.5621 | 0.5627 | **0.9990** | 0.2644 | 0.2645 | **0.9996** | **0.9993** |
| metaKV | 4 | 0.2256 | 0.2453 | **0.9111** | 0.2849 | 0.2907 | **0.9778** | **0.9444** |
| tencentBlock | 4755 | 0.5087 | 0.5150 | **0.9871** | 0.7030 | 0.7078 | **0.9926** | **0.9898** |
| tencentPhoto | 2 | 0.6947 | 0.7026 | **0.9886** | 0.6561 | 0.6599 | **0.9943** | **0.9915** |
| wiki | 3 | 0.6229 | 0.6369 | **0.9745** | 0.8068 | 0.8121 | **0.9935** | **0.9840** |
| **avg(groups)** | - | - | - | **0.9735** | - | - | **0.9917** | **0.9826** |

---

## 三、CMA-ES 3lcache-target best_LOH — cache01（cache_ratio=0.1）

> 数据来源：`baseline_summary_v7_3lcache-target.md` 的「MR/BMR 相对 LRU 比例」表 best_LOH 列。

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

## 四、CMA-ES 3lcache-target best_LOH — cache0001（cache_ratio=0.001）

> 数据来源：`baseline_summary_3lcache-target.md` 的「MR/BMR 相对 LRU 比例」表 best_LOH 列。

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
- hitmiss GBM 原有 749 条 NA，743 条已从 `result/*.cachesim` 回填，剩余 6 条 metaKV NA。
- 回填后 alibabaBlock n=1000、tencentBlock n=4755 均已完整；部分 group 的 avg(rel_mr) 略超 1.0。
- LRU 基线来自 `lru_summary_v7.md` per-trace 数据。

---

## 总结

### best_LOH（CMA-ES 3lcache-target，v7 固定策略）

| group | cache01 | | cache0001 | |
|---|---:|---:|---:|---:|
| | avg(rel_mr) | avg(rel_bmr) | avg(rel_mr) | avg(rel_bmr) |
| alibabaBlock | 0.7577 | 0.8743 | 0.8772 | 0.9513 |
| metaCDN | 0.7957 | 0.8749 | 0.6849 | 0.9187 |
| metaKV | 0.6803 | 0.9258 | 0.5571 | 0.9028 |
| tencentBlock | 0.7436 | 0.8935 | 0.8793 | 0.9436 |
| tencentPhoto | 0.8910 | 0.9945 | 0.8732 | 0.9606 |
| wiki | 0.5323 | 0.7708 | 0.6603 | 0.8631 |
| **avg(groups)** | **0.7334** | **0.8890** | **0.7553** | **0.9234** |

### hitmiss GBM（MR 目标 + BMR 目标的 avg(rel_combo) 均值）

| group | cache01 | cache0001 | 均值（两缓存）|
|---|---:|---:|---:|
| alibabaBlock | 1.0060 | 0.9885 | 0.9972 |
| metaCDN | 0.9963 | 0.9994 | 0.9978 |
| metaKV | 0.9506 | 0.9552 | 0.9529 |
| tencentBlock | 1.0157 | 0.9922 | 1.0040 |
| tencentPhoto | 0.9860 | 0.9939 | 0.9900 |
| wiki | 0.9497 | 0.9864 | 0.9681 |
| **avg(groups)** | **0.9840** | **0.9859** | **0.9850** |

---

## 综合均值（hitmiss GBM / best_LOH）

> `hitmiss GBM` 使用上一张表的“均值（两缓存）”；`best_LOH` 使用 `mean(cache01_rel_mr, cache0001_rel_mr, cache01_rel_bmr, cache0001_rel_bmr)`。
> `best_LOH (DRL)` 来自 `docs/20260422-ablation-per-group-cache01/drl版本LOH/baseline_summary_v7_3lcache-target.md` 和 `docs/20260423-ablation-per-group-cache0001/drl版本/baseline_summary_v7_3lcache-omr.md` 的「MR 相对 LRU 比例」与「BMR 相对 LRU 比例」表 best_LOH 列，同样取四项均值。

| group | hitmiss GBM | best_LOH | best_LOH (DRL) |
|---|---:|---:|---:|
| alibabaBlock | 0.9972 | **0.8651** | 0.8667 |
| metaCDN | 0.9978 | **0.8186** | 0.8476 |
| metaKV | 0.9529 | **0.7665** | 0.8122 |
| tencentBlock | 1.0040 | **0.8650** | 0.8669 |
| tencentPhoto | 0.9900 | **0.9298** | 0.9718 |
| wiki | 0.9681 | **0.7066** | 0.7784 |
| **avg(groups)** | **0.9850** | **0.8253** | **0.8548** |

![Avg. Rel. MR by group](rsd_deep_model_ablation.png)
