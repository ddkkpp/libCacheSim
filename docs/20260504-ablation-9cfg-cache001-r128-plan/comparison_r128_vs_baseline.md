# r128 vs baseline 对比（20260504 r128 vs 20260430 baseline，cache=0.01）

- r128: `tmp/20260504-ablation-9cfg-cache001-r128-plan` （LOH_RANDOM_CANDIDATES=128）
- baseline: `tmp/20260430-ablation-9cfg-cache001-plan` （LOH_RANDOM_CANDIDATES=16，默认）
- 数据来源: results/ 目录（已从 logs/ 补全缺失结果，共补 45 条）
- best_LOH: 每条 trace 在 9 种 cfg 中取最小 MR/BMR
- 相对值: per-trace ratio = r128_best / baseline_best，组内平均/加权平均
- 值 < 1 表示 r128 优于 baseline

# 指标: MR

## MR（miss ratio） — 组内平均值（基于 n_common）

| trace 组 | n_all | n_common | r128 best_LOH avg | baseline best_LOH avg | r128/baseline |
|---|---:|---:|---:|---:|---:|
| alibabaBlock | 1000 | 1000 | 0.443212 | 0.442951 | 1.000589 |
| cloudphysics | 106 | 106 | 0.557273 | 0.556405 | 1.001560 |
| metaCDN | 3 | 3 | 0.339556 | 0.338332 | 1.003618 |
| metaKV | 5 | 5 | 0.063693 | 0.062046 | 1.026538 |
| tencentBlock | 4755 | 4755 | 0.339661 | 0.338941 | 1.002126 |
| tencentPhoto | 2 | 2 | 0.381876 | 0.382064 | 0.999508 |
| wiki | 3 | 3 | 0.220687 | 0.216988 | 1.017044 |

## MR（miss ratio） — 加权平均值（按 n_req 加权，基于 n_common）

| trace 组 | n_all | n_common | r128 best_LOH wavg | baseline best_LOH wavg | r128/baseline |
|---|---:|---:|---:|---:|---:|
| alibabaBlock | 1000 | 1000 | 0.350485 | 0.349284 | 1.003438 |
| cloudphysics | 106 | 106 | 0.580998 | 0.579886 | 1.001918 |
| metaCDN | 3 | 3 | 0.352797 | 0.352211 | 1.001664 |
| metaKV | 5 | 5 | 0.043760 | 0.042711 | 1.024563 |
| tencentBlock | 4755 | 4755 | 0.320455 | 0.319072 | 1.004333 |
| tencentPhoto | 2 | 2 | 0.381786 | 0.381978 | 0.999497 |
| wiki | 3 | 3 | 0.116001 | 0.110672 | 1.048147 |

## MR（miss ratio） — 相对值（per-trace ratio 的组内算术平均，基于 n_common）

| trace 组 | n_all | n_common | avg(r128/baseline) | 说明 |
|---|---:|---:|---:|---|
| alibabaBlock | 1000 | 1000 | 1.000434 | ✗ r128劣 |
| cloudphysics | 106 | 106 | 1.003106 | ✗ r128劣 |
| metaCDN | 3 | 3 | 1.004705 | ✗ r128劣 |
| metaKV | 5 | 5 | 1.025315 | ✗ r128劣 |
| tencentBlock | 4755 | 4755 | 1.002808 | ✗ r128劣 |
| tencentPhoto | 2 | 2 | 0.999506 | ✓ r128优 |
| wiki | 3 | 3 | 1.037560 | ✗ r128劣 |

## MR（miss ratio） — 加权相对值（per-trace ratio 的 n_req 加权平均，基于 n_common）

| trace 组 | n_all | n_common | wavg(r128/baseline) | 说明 |
|---|---:|---:|---|---|
| alibabaBlock | 1000 | 1000 | 1.004895 | ✗ r128劣 |
| cloudphysics | 106 | 106 | 1.003881 | ✗ r128劣 |
| metaCDN | 3 | 3 | 1.002445 | ✗ r128劣 |
| metaKV | 5 | 5 | 1.022696 | ✗ r128劣 |
| tencentBlock | 4755 | 4755 | 1.004970 | ✗ r128劣 |
| tencentPhoto | 2 | 2 | 0.999494 | ✓ r128优 |
| wiki | 3 | 3 | 1.054243 | ✗ r128劣 |

# 指标: BMR

## BMR（byte miss ratio） — 组内平均值（基于 n_common）

| trace 组 | n_all | n_common | r128 best_LOH avg | baseline best_LOH avg | r128/baseline |
|---|---:|---:|---:|---:|---:|
| alibabaBlock | 1000 | 1000 | 0.660073 | 0.659731 | 1.000518 |
| cloudphysics | 106 | 106 | 0.710824 | 0.711541 | 0.998993 |
| metaCDN | 3 | 3 | 0.204358 | 0.203034 | 1.006523 |
| metaKV | 5 | 5 | 0.153527 | 0.154354 | 0.994641 |
| tencentBlock | 4755 | 4755 | 0.526465 | 0.526178 | 1.000546 |
| tencentPhoto | 2 | 2 | 0.428033 | 0.437096 | 0.979264 |
| wiki | 3 | 3 | 0.419404 | 0.419479 | 0.999820 |

## BMR（byte miss ratio） — 加权平均值（按 n_req 加权，基于 n_common）

| trace 组 | n_all | n_common | r128 best_LOH wavg | baseline best_LOH wavg | r128/baseline |
|---|---:|---:|---:|---:|---:|
| alibabaBlock | 1000 | 1000 | 0.479875 | 0.478088 | 1.003738 |
| cloudphysics | 106 | 106 | 0.719862 | 0.721368 | 0.997912 |
| metaCDN | 3 | 3 | 0.209398 | 0.208589 | 1.003882 |
| metaKV | 5 | 5 | 0.119187 | 0.119921 | 0.993877 |
| tencentBlock | 4755 | 4755 | 0.436310 | 0.435145 | 1.002678 |
| tencentPhoto | 2 | 2 | 0.427965 | 0.437037 | 0.979242 |
| wiki | 3 | 3 | 0.442119 | 0.442211 | 0.999792 |

## BMR（byte miss ratio） — 相对值（per-trace ratio 的组内算术平均，基于 n_common）

| trace 组 | n_all | n_common | avg(r128/baseline) | 说明 |
|---|---:|---:|---:|---|
| alibabaBlock | 1000 | 1000 | 1.000545 | ✗ r128劣 |
| cloudphysics | 106 | 106 | 0.998969 | ✓ r128优 |
| metaCDN | 3 | 3 | 1.007468 | ✗ r128劣 |
| metaKV | 5 | 5 | 0.994524 | ✓ r128优 |
| tencentBlock | 4755 | 4755 | 1.000609 | ✗ r128劣 |
| tencentPhoto | 2 | 2 | 0.979262 | ✓ r128优 |
| wiki | 3 | 3 | 0.999842 | ✓ r128优 |

## BMR（byte miss ratio） — 加权相对值（per-trace ratio 的 n_req 加权平均，基于 n_common）

| trace 组 | n_all | n_common | wavg(r128/baseline) | 说明 |
|---|---:|---:|---|---|
| alibabaBlock | 1000 | 1000 | 1.005012 | ✗ r128劣 |
| cloudphysics | 106 | 106 | 0.997603 | ✓ r128优 |
| metaCDN | 3 | 3 | 1.004509 | ✗ r128劣 |
| metaKV | 5 | 5 | 0.993770 | ✓ r128优 |
| tencentBlock | 4755 | 4755 | 1.000661 | ✗ r128劣 |
| tencentPhoto | 2 | 2 | 0.979240 | ✓ r128优 |
| wiki | 3 | 3 | 0.999821 | ✓ r128优 |

