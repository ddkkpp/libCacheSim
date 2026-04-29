# 20260422-autocompound-cache0001-ready 结果汇总（截至当前已完成）

**MR 结果目录**: `tmp/20260422-autocompound-cache0001-ready/mr/results`
**BMR 结果目录**: `tmp/20260422-autocompound-cache0001-ready/bmr/results`
**Baseline 目录**: `/home/丁坤鹏/libCacheSim/result`
**Baseline 匹配规则**: cache size 相对误差 <= 5.0%

## 1. 覆盖与匹配情况

- MR 文件数: 5866
- BMR 文件数: 5865
- MR∩BMR（可合并）: 5864
- 仅 MR: 2
- 仅 BMR: 1
- baseline 文件数: 6041
- 成功匹配 baseline（trace+cache）: 5863
- baseline trace 缺失: 0
- baseline cache 不在容差内: 1

## 2. 全局指标（LOH vs 最优 baseline）

- LOH MR 平均/中位: 0.545940 / 0.510843
- 最优 baseline MR 平均/中位: 0.458947 / 0.439700
- LOH BMR 平均/中位: 0.720282 / 0.729678
- 最优 baseline BMR 平均/中位: 0.666708 / 0.673400
- 相对最优 baseline 的 MR 改善均值/中位: -29.02% / -2.23%
- 相对最优 baseline 的 BMR 改善均值/中位: -10.33% / -2.11%

## 3. 数据集分布（已成功匹配）

| dataset | count |
|---|---:|
| alibabaBlock | 994 |
| meta | 4 |
| other | 108 |
| tencentBlock | 4754 |
| wiki | 3 |

## 4. 对比算法胜率（按覆盖排序）

| algo | 覆盖数 | MR胜率 | BMR胜率 | MR平均改善 | BMR平均改善 |
|---|---:|---:|---:|---:|---:|
| ARC | 5862 | 61.07% | 56.04% | -16.55% | -4.60% |
| LRU | 5862 | 71.92% | 77.00% | -8.28% | -0.67% |
| Cacheus | 5861 | 53.56% | 45.71% | -18.62% | -5.16% |
| GDSF | 5861 | 40.16% | 51.75% | -25.54% | -3.40% |
| LHD | 5861 | 54.62% | 71.71% | -19.28% | 2.94% |
| S3FIFO-0.1000-2 | 5861 | 50.08% | 39.16% | -21.44% | -6.92% |
| Sieve | 5861 | 64.72% | 59.48% | -14.51% | -3.66% |
| ThreeLCache-BMR | 5861 | 47.59% | 35.27% | -20.38% | -7.57% |
| WTinyLFU-w0.01-SLRU | 5861 | 69.31% | 69.95% | -1.08% | 7.57% |
| GLCache | 5501 | 72.13% | 81.15% | -0.63% | 5.08% |
| LRB-BMR | 5486 | 63.62% | 52.90% | -14.22% | -4.94% |
| LeCaR | 1738 | 76.29% | 67.66% | -7.55% | -1.89% |

## 5. 说明

- LOH 使用 MR 目录中的 `miss ratio` 与 BMR 目录中的 `byte miss ratio`，两者按同名结果文件合并。
- baseline 在同 trace 下按算法分别选择最接近 cache size 且误差不超过阈值的记录。
- `*_details.csv` 提供逐 trace 明细，可用于后续按组/按算法继续细分。

## 6. 解析告警

- MR 解析失败文件数: 4
- BMR 解析失败文件数: 4
- baseline 无法识别行数: 215
