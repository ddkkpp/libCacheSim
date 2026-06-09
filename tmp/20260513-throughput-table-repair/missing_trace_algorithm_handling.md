# Cache01 Throughput Missing Trace/Algorithm Handling

本次修复前，三个目录的问题分两类：

- `tmp/20260511-cache01-precise-throughput-fair-nocloudphysics` 和 `tmp/20260511-cache01-precise-throughput-fair` 原来直接排除了 `tencent_photo1`、`tencent_photo2`、`wiki_2016u`、`wiki_2019t` 四个 trace。
- `tmp/20260511-cache01-precise-throughput` 原来已经包含这四个 trace，但缺 23 个 `trace x algorithm` 吞吐行。

## 缺失行清单与处理

| group | trace | algorithm | 处理方式 | source/note |
| --- | --- | --- | --- | --- |
| tencentPhoto | tencent_photo1 | drl-v7-omr-cache01 | 使用 `drl-v7-omr-cache01` 真实 OMR `f001_orig` cachesim 日志 | `repaired_exact_drl_v7_omr_result`; source=`tmp/20260510-drl-v7-omr-cache01-plan/logs/cachesim/cachesim_sb3_tencentPhoto__tencent_photo1__f001_orig.log`; mqps=`0.123755590` |
| tencentPhoto | tencent_photo2 | drl-v7-omr-cache01 | 使用 `drl-v7-omr-cache01` 真实 OMR `f001_orig` cachesim 日志 | `repaired_exact_drl_v7_omr_result`; source=`tmp/20260510-drl-v7-omr-cache01-plan/logs/cachesim/cachesim_sb3_tencentPhoto__tencent_photo2__f001_orig.log`; mqps=`0.127094162` |
| wiki | wiki_2016u | ARC | 未找到 exact runtime，使用同 group+algorithm 已有行均值估算 | `repaired_imputed_group_algorithm_mean_no_exact_runtime_source`; mqps=`1.950000000` |
| wiki | wiki_2016u | Cacheus | 未找到 exact runtime，使用同 group+algorithm 已有行均值估算 | `repaired_imputed_group_algorithm_mean_no_exact_runtime_source`; mqps=`0.670000000` |
| wiki | wiki_2016u | GDSF | 未找到 exact runtime，使用同 group+algorithm 已有行均值估算 | `repaired_imputed_group_algorithm_mean_no_exact_runtime_source`; mqps=`0.280000000` |
| wiki | wiki_2016u | GLCache | 未找到 exact runtime，使用同 group+algorithm 已有行均值估算 | `repaired_imputed_group_algorithm_mean_no_exact_runtime_source`; mqps=`1.320000000` |
| wiki | wiki_2016u | LHD | 未找到 exact runtime，使用同 group+algorithm 已有行均值估算 | `repaired_imputed_group_algorithm_mean_no_exact_runtime_source`; mqps=`1.110000000` |
| wiki | wiki_2016u | LRU | 未找到 exact runtime，使用同 group+algorithm 已有行均值估算 | `repaired_imputed_group_algorithm_mean_no_exact_runtime_source`; mqps=`2.200000000` |
| wiki | wiki_2016u | LeCaR | 未找到 exact runtime，使用同 group+algorithm 已有行均值估算 | `repaired_imputed_group_algorithm_mean_no_exact_runtime_source`; mqps=`1.340000000` |
| wiki | wiki_2016u | S3FIFO-0.1000-2 | 未找到 exact runtime，使用同 group+algorithm 已有行均值估算 | `repaired_imputed_group_algorithm_mean_no_exact_runtime_source`; mqps=`1.840000000` |
| wiki | wiki_2016u | Sieve | 未找到 exact runtime，使用同 group+algorithm 已有行均值估算 | `repaired_imputed_group_algorithm_mean_no_exact_runtime_source`; mqps=`2.600000000` |
| wiki | wiki_2016u | WTinyLFU-w0.01-SLRU | 未找到 exact runtime，使用同 group+algorithm 已有行均值估算 | `repaired_imputed_group_algorithm_mean_no_exact_runtime_source`; mqps=`1.590000000` |
| wiki | wiki_2019t | ARC | 未找到 exact runtime，使用同 group+algorithm 已有行均值估算 | `repaired_imputed_group_algorithm_mean_no_exact_runtime_source`; mqps=`1.950000000` |
| wiki | wiki_2019t | Cacheus | 未找到 exact runtime，使用同 group+algorithm 已有行均值估算 | `repaired_imputed_group_algorithm_mean_no_exact_runtime_source`; mqps=`0.670000000` |
| wiki | wiki_2019t | GDSF | 使用 result 中近目标 cache size 且 MR/BMR 匹配的真实吞吐行 | `repaired_exact_throughput_source`; source=`result/wiki_2019t.oracleGeneral.zst.cachesim`; mqps=`0.200000000` |
| wiki | wiki_2019t | GLCache | 未找到 exact runtime，使用同 group+algorithm 已有行均值估算 | `repaired_imputed_group_algorithm_mean_no_exact_runtime_source`; mqps=`1.320000000` |
| wiki | wiki_2019t | LHD | 未找到 exact runtime，使用同 group+algorithm 已有行均值估算 | `repaired_imputed_group_algorithm_mean_no_exact_runtime_source`; mqps=`1.110000000` |
| wiki | wiki_2019t | LRU | 使用 result 中近目标 cache size 且 MR/BMR 匹配的真实吞吐行 | `repaired_exact_throughput_source`; source=`result/wiki_2019t.oracleGeneral.zst.cachesim`; mqps=`1.730000000` |
| wiki | wiki_2019t | LeCaR | 未找到 exact runtime，使用同 group+algorithm 已有行均值估算 | `repaired_imputed_group_algorithm_mean_no_exact_runtime_source`; mqps=`1.340000000` |
| wiki | wiki_2019t | S3FIFO-0.1000-2 | 使用 result 中近目标 cache size 且 MR/BMR 匹配的真实吞吐行 | `repaired_exact_throughput_source`; source=`result/wiki_2019t.oracleGeneral.zst.cachesim`; mqps=`1.080000000` |
| wiki | wiki_2019t | Sieve | 未找到 exact runtime，使用同 group+algorithm 已有行均值估算 | `repaired_imputed_group_algorithm_mean_no_exact_runtime_source`; mqps=`2.600000000` |
| wiki | wiki_2019t | WTinyLFU-w0.01-SLRU | 未找到 exact runtime，使用同 group+algorithm 已有行均值估算 | `repaired_imputed_group_algorithm_mean_no_exact_runtime_source`; mqps=`1.590000000` |
| wiki | wiki_2019t | LRB-BMR | 未找到 exact runtime，使用同 group+algorithm 已有行均值估算 | `repaired_imputed_group_algorithm_mean_no_exact_runtime_source`; mqps=`0.075000000` |

## 处理原则

1. 如果 raw 表里已有目标 trace 的其它算法行，就直接把四个目标 trace 纳入 `fair` 和 `fair-nocloudphysics`，不再把它们作为 excluded trace。
2. 对 `tencent_photo1/2` 的 `drl-v7-omr-cache01`，使用 `tmp/20260510-drl-v7-omr-cache01-plan/logs/cachesim/` 下真实 OMR `f001_orig` cachesim 完整日志，并在 `note` 中标记为 `repaired_exact_drl_v7_omr_result`。
3. 对 wiki baseline，优先搜索 result 中 cache size 接近目标且 MR/BMR 匹配的真实吞吐行，并补充搜索 `tmp/20260501-baseline001-plan/logs/tasks/wiki__<trace>__<algorithm>__*.log`；找到则写入 `note=repaired_exact_throughput_source`。
4. 对其余 wiki baseline 缺失行，如果仍没有 exact runtime/throughput source，则使用同一 `wiki` group 内该 algorithm 的已有 MQPS 均值补齐，并明确写入 `source=derived:group_algorithm_mean_from_available_rows` 与 `note=repaired_imputed_group_algorithm_mean_no_exact_runtime_source`。
5. 所有 `throughput_stats.csv` 的 `mean_mqps` 已改为先对每个 group 内求算法均值，再对 group 均值求平均；percentile 列仍按逐 trace 行计算。

## 校验结果

独立复算日志：`tmp/20260513-throughput-table-repair/logs/validate_final_drl_omr_and_group_first.log`

```text
tmp/20260511-cache01-precise-throughput: traces=5874 rows=99858 missing=0 repaired_rows=23 max_mean_diff=4.441e-16
tmp/20260511-cache01-precise-throughput-fair: traces=5874 rows=99858 missing=0 repaired_rows=23 max_mean_diff=4.441e-16
tmp/20260511-cache01-precise-throughput-fair-nocloudphysics: traces=5768 rows=98056 missing=0 repaired_rows=23 max_mean_diff=4.441e-16
```
