# metaCDN / meta_rnha cache=0.1 吞吐量整理

来源：
- 算法吞吐量：`docs/20260515-cache0001-per-trace-maxavg-throughput.csv` 中 `meta_rnha,metaCDN` 这一行。
- raven 结果：`/home/丁坤鹏/raven/runs/manifest_20260510_ravenl_ohr_pretrained_nocloud_cache0p1_p40_cpu4_watchdog_failfirst_20260514-221249/results_ok_detailed.tsv` 与同目录 `results.tsv` 中未找到 `meta_rnha` 的最终汇总行；当前仅能确认对应 trace log 存在于 `trace_logs/0012_metaCDN__meta_rnha.log`。
- quantiles：`/home/丁坤鹏/tmp/adjacent_request_time_stats/manifest_20260514_watchdog_failfirst_full/per_trace_quantiles.tsv` 中 `metaCDN / meta_rnha` 行。

说明：
- 吞吐量单元为 req/s。
- 算法列格式为 `(max_qps, avg_qps)`。
- raven 最终汇总值在给定结果表中缺失；本文使用 trace log 最新 checkpoint（35,000,000 req）与起始时间差计算近似吞吐量，仅作参考。

## 算法吞吐量

| algo | max_qps | avg_qps |
|---|---:|---:|
| step2 | 219,031.871319 | 211,997.033815 |
| cmaes-v7 | 197,670.554079 | 170,123.190327 |
| drl-v7 | 99,271.658281 | 95,762.102041 |
| ARC | 4,120,000.000000 | 4,120,000.000000 |
| Cacheus | 1,120,000.000000 | 1,120,000.000000 |
| GLCache | 1,970,000.000000 | 1,970,000.000000 |
| LHD | 660,000.000000 | 660,000.000000 |
| LRU | 4,790,000.000000 | 4,790,000.000000 |
| LeCaR | 2,520,000.000000 | 2,520,000.000000 |
| S3FIFO-0.1000-2 | 2,280,000.000000 | 2,280,000.000000 |
| Sieve | 4,640,000.000000 | 4,640,000.000000 |
| WTinyLFU-w0.01-SLRU | 1,210,000.000000 | 1,210,000.000000 |
| LRB-BMR | 10,000.000000 | 10,000.000000 |
| ThreeLCache-BMR | 560,000.000000 | 560,000.000000 |
| ThreeLCache-OMR | 446,974.886731 | 446,974.886731 |

## raven

| item | value |
|---|---:|
| throughput_req_per_s (approx) | 191.531044 |
| note | 基于 `trace_logs/0012_metaCDN__meta_rnha.log`：从 `2026-05-14 22:12:54` 到 `2026-05-17 00:58:32`，按 35,000,000 req / 182,738 s 计算；非最终完赛吞吐 |

## quantiles

| item | value |
|---|---:|
| mean_arrival_rate | 139.87040881576815 |
| max_arrival_rate | 27374 |
