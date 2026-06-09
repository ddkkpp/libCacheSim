# 20260403 CMAES Update Interval Grid Summary

## 1. Run Configuration
- Mode: before_rebalance_only (LOH_ADAPTIVE_INCLUDE_RANDOM=0)
- Debug: LOH_DEBUG_LEVEL=0
- Budget log: LOH_ADAPTIVE_BUDGET_LOG=0 (off)
- Perf profiling: enabled by build
- Engine mode: LOH_ENABLE_CMAES=1, LOH_ENABLE_RL=0
- Parallelism: 42
- Grid: 3 traces x 14 intervals = 42 jobs

## 2. Completion Status
- Launcher status: finished
- Result rows: 42/42
- Exit code: all 42 rows are 0

## 3. Best Interval Per Trace (by miss_ratio)

| trace | best interval | miss_ratio | byte_miss_ratio | throughput_mqps | note |
|---|---:|---:|---:|---:|---|
| 1063 | 6000 | 0.015947 | 0.018319 | 0.63 | Also highest throughput for this trace |
| wiki_2019t | 200 | 0.169590 | 0.133313 | 0.09 | 100/200/500/1000/1500 are very close |
| meta_reag | 5000 | 0.269031 | 0.154287 | 0.89 | Best mr and highest throughput |

## 4. Additional Metric Notes

### 4.1 1063
- Best mr: interval=6000, mr=0.015947
- Best bmr: interval=7000, bmr=0.017961
- Best mqps: interval=6000, mqps=0.63

### 4.2 wiki_2019t
- Best mr: interval=200, mr=0.169590
- Best bmr: interval=6000, bmr=0.130490
- Best mqps: 0.09 (many intervals tie)

### 4.3 meta_reag
- Best mr: interval=5000, mr=0.269031
- Best bmr: interval=10000, bmr=0.152122
- Best mqps: interval=5000, mqps=0.89

## 5. Practical Recommendation
- If selecting one per-trace setting by mr:
  - 1063 -> 6000
  - wiki_2019t -> 200
  - meta_reag -> 5000
- If prioritizing bmr for wiki_2019t, interval=6000 is preferable.
- For meta_reag, 6000/7000 are clearly worse in mr and should be avoided.

## 6. Source Files
- Results CSV: tmp/20260402-default-update-interval-grid-cmaes-rerun/results.csv
- Launcher log: tmp/20260402-default-update-interval-grid-cmaes-rerun/logs/cmd_logs_launcher_run_cmaes_grid_parallel42.log
- PIDs snapshot: tmp/20260402-default-update-interval-grid-cmaes-rerun/pids.tsv

## 7. Full Table (42 Rows)

### 7.1 1063
| interval | miss_ratio | byte_miss_ratio | throughput_mqps | exit_code |
|---:|---:|---:|---:|---:|
| 100 | 0.020565 | 0.021795 | 0.23 | 0 |
| 200 | 0.020600 | 0.021846 | 0.33 | 0 |
| 500 | 0.020971 | 0.022282 | 0.35 | 0 |
| 1000 | 0.019252 | 0.020195 | 0.40 | 0 |
| 1500 | 0.019725 | 0.020810 | 0.53 | 0 |
| 2000 | 0.033249 | 0.036582 | 0.33 | 0 |
| 3000 | 0.024706 | 0.026689 | 0.47 | 0 |
| 4000 | 0.020773 | 0.021949 | 0.54 | 0 |
| 5000 | 0.028165 | 0.030502 | 0.36 | 0 |
| 6000 | 0.015947 | 0.018319 | 0.63 | 0 |
| 7000 | 0.015956 | 0.017961 | 0.58 | 0 |
| 8000 | 0.022853 | 0.025498 | 0.38 | 0 |
| 9000 | 0.027017 | 0.028807 | 0.34 | 0 |
| 10000 | 0.022590 | 0.024920 | 0.39 | 0 |

### 7.2 wiki_2019t
| interval | miss_ratio | byte_miss_ratio | throughput_mqps | exit_code |
|---:|---:|---:|---:|---:|
| 100 | 0.169603 | 0.133309 | 0.08 | 0 |
| 200 | 0.169590 | 0.133313 | 0.09 | 0 |
| 500 | 0.169642 | 0.133419 | 0.09 | 0 |
| 1000 | 0.169684 | 0.133895 | 0.08 | 0 |
| 1500 | 0.169647 | 0.133306 | 0.09 | 0 |
| 2000 | 0.170085 | 0.132573 | 0.07 | 0 |
| 3000 | 0.170889 | 0.135210 | 0.08 | 0 |
| 4000 | 0.170764 | 0.142794 | 0.08 | 0 |
| 5000 | 0.170499 | 0.131461 | 0.08 | 0 |
| 6000 | 0.170267 | 0.130490 | 0.08 | 0 |
| 7000 | 0.171166 | 0.133351 | 0.09 | 0 |
| 8000 | 0.170855 | 0.134298 | 0.09 | 0 |
| 9000 | 0.171040 | 0.134576 | 0.08 | 0 |
| 10000 | 0.173373 | 0.136459 | 0.09 | 0 |

### 7.3 meta_reag
| interval | miss_ratio | byte_miss_ratio | throughput_mqps | exit_code |
|---:|---:|---:|---:|---:|
| 100 | 0.269238 | 0.152962 | 0.25 | 0 |
| 200 | 0.269233 | 0.153024 | 0.33 | 0 |
| 500 | 0.269212 | 0.153184 | 0.55 | 0 |
| 1000 | 0.269279 | 0.152986 | 0.57 | 0 |
| 1500 | 0.271848 | 0.153637 | 0.19 | 0 |
| 2000 | 0.269540 | 0.152636 | 0.35 | 0 |
| 3000 | 0.269106 | 0.153807 | 0.76 | 0 |
| 4000 | 0.269407 | 0.153034 | 0.26 | 0 |
| 5000 | 0.269031 | 0.154287 | 0.89 | 0 |
| 6000 | 0.277971 | 0.155532 | 0.12 | 0 |
| 7000 | 0.276269 | 0.155088 | 0.08 | 0 |
| 8000 | 0.271155 | 0.153610 | 0.21 | 0 |
| 9000 | 0.269400 | 0.153446 | 0.45 | 0 |
| 10000 | 0.269407 | 0.152122 | 0.24 | 0 |

## 8. Perf Counts and Avg Latency

说明：以下是每个 trace 在“最佳 miss_ratio interval”对应 case 的 perf 统计，单位为 avg_ms。

### 8.1 1063 (interval=6000)
| part | count | avg_ms |
|---|---:|---:|
| find | 360960512 | 0.000 |
| insert | 5756286 | 0.000 |
| evict | 4848105 | 0.058 |
| candidate_collect | 4848105 | 0.000 |
| calc_features | 1241114880 | 0.000 |
| calc_score | 4848105 | 0.001 |
| to_evict_total | 4848105 | 0.057 |
| cmaes_tell | 60107 | 0.168 |
| cmaes_ask | 60107 | 0.000 |
| tell_optimizer | 60107 | 0.100 |
| tell_refill | 60107 | 0.068 |

### 8.2 wiki_2019t (interval=200)
| part | count | avg_ms |
|---|---:|---:|
| find | 207646002 | 0.000 |
| insert | 35214623 | 0.000 |
| evict | 33058400 | 0.060 |
| candidate_collect | 33058400 | 0.000 |
| calc_features | 8462950400 | 0.000 |
| calc_score | 33058400 | 0.001 |
| to_evict_total | 33058400 | 0.059 |
| cmaes_tell | 1011863 | 0.204 |
| cmaes_ask | 1011863 | 0.000 |
| tell_optimizer | 1011863 | 0.114 |
| tell_refill | 1011863 | 0.090 |

### 8.3 meta_reag (interval=5000)
| part | count | avg_ms |
|---|---:|---:|
| find | 45623306 | 0.000 |
| insert | 12274103 | 0.000 |
| evict | 124457 | 0.116 |
| candidate_collect | 124457 | 0.000 |
| calc_features | 31860992 | 0.000 |
| calc_score | 124457 | 0.001 |
| to_evict_total | 124457 | 0.114 |
| cmaes_tell | 8448 | 0.114 |
| cmaes_ask | 8448 | 0.000 |
| tell_optimizer | 8448 | 0.079 |
| tell_refill | 8448 | 0.035 |

### 8.4 Perf Source Logs
- [tmp/20260402-default-update-interval-grid-cmaes-rerun/logs/case_10_1063_u6000.log](tmp/20260402-default-update-interval-grid-cmaes-rerun/logs/case_10_1063_u6000.log)
- [tmp/20260402-default-update-interval-grid-cmaes-rerun/logs/case_16_wiki_2019t_u200.log](tmp/20260402-default-update-interval-grid-cmaes-rerun/logs/case_16_wiki_2019t_u200.log)
- [tmp/20260402-default-update-interval-grid-cmaes-rerun/logs/case_37_meta_reag_u5000.log](tmp/20260402-default-update-interval-grid-cmaes-rerun/logs/case_37_meta_reag_u5000.log)

## 9. Major Perf Parts by Update Interval

说明：按你的要求，以下在每个 update interval 列出 3 个主要部分：
- `to_evict_total`：count / avg_ms / total_s
- `tell_optimizer`：count / avg_ms / total_s
- `tell_refill`：count / avg_ms / total_s

### 9.1 1063
| interval | to_evict_count | to_evict_avg_ms | to_evict_total_s | tell_optimizer_count | tell_optimizer_avg_ms | tell_optimizer_total_s | tell_refill_count | tell_refill_avg_ms | tell_refill_total_s |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 100 | 6530329 | 0.074 | 484.658 | 3606434 | 0.104 | 374.239 | 3606434 | 0.089 | 322.378 |
| 200 | 6543804 | 0.063 | 412.012 | 1803217 | 0.105 | 189.760 | 1803217 | 0.089 | 161.190 |
| 500 | 6677236 | 0.075 | 503.601 | 721286 | 0.109 | 78.935 | 721286 | 0.089 | 64.170 |
| 1000 | 6059217 | 0.076 | 460.709 | 360643 | 0.116 | 41.893 | 360643 | 0.089 | 32.193 |
| 1500 | 6229356 | 0.057 | 355.132 | 240428 | 0.117 | 28.147 | 240428 | 0.090 | 21.727 |
| 2000 | 11115191 | 0.063 | 698.088 | 180321 | 0.122 | 21.939 | 180321 | 0.087 | 15.682 |
| 3000 | 8028065 | 0.056 | 452.491 | 120214 | 0.114 | 13.754 | 120214 | 0.084 | 10.065 |
| 4000 | 6606428 | 0.056 | 371.189 | 90160 | 0.112 | 10.137 | 90160 | 0.082 | 7.358 |
| 5000 | 9277349 | 0.068 | 630.813 | 72128 | 0.123 | 8.869 | 72128 | 0.080 | 5.792 |
| 6000 | 4848105 | 0.057 | 277.987 | 60107 | 0.100 | 5.987 | 60107 | 0.068 | 4.063 |
| 7000 | 4868849 | 0.064 | 313.129 | 51520 | 0.103 | 5.293 | 51520 | 0.069 | 3.559 |
| 8000 | 7349796 | 0.077 | 562.406 | 45080 | 0.114 | 5.142 | 45080 | 0.071 | 3.181 |
| 9000 | 8862651 | 0.076 | 672.487 | 40071 | 0.114 | 4.570 | 40071 | 0.070 | 2.809 |
| 10000 | 7255391 | 0.075 | 545.403 | 36064 | 0.104 | 3.758 | 36064 | 0.060 | 2.175 |

### 9.2 wiki_2019t
| interval | to_evict_count | to_evict_avg_ms | to_evict_total_s | tell_optimizer_count | tell_optimizer_avg_ms | tell_optimizer_total_s | tell_refill_count | tell_refill_avg_ms | tell_refill_total_s |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 100 | 33061345 | 0.059 | 1935.511 | 2023727 | 0.107 | 217.279 | 2023727 | 0.090 | 182.808 |
| 200 | 33058400 | 0.059 | 1953.583 | 1011863 | 0.114 | 115.231 | 1011863 | 0.090 | 91.137 |
| 500 | 33069588 | 0.061 | 2028.611 | 404745 | 0.120 | 48.694 | 404745 | 0.089 | 36.041 |
| 1000 | 33077878 | 0.068 | 2262.735 | 202372 | 0.126 | 25.596 | 202372 | 0.088 | 17.828 |
| 1500 | 33071231 | 0.063 | 2099.840 | 134915 | 0.118 | 15.940 | 134915 | 0.086 | 11.618 |
| 2000 | 33163639 | 0.075 | 2499.431 | 101186 | 0.128 | 12.909 | 101186 | 0.084 | 8.525 |
| 3000 | 33324712 | 0.070 | 2325.698 | 67457 | 0.116 | 7.803 | 67457 | 0.077 | 5.213 |
| 4000 | 33267266 | 0.069 | 2300.303 | 50593 | 0.108 | 5.441 | 50593 | 0.071 | 3.614 |
| 5000 | 33262442 | 0.075 | 2482.704 | 40474 | 0.111 | 4.495 | 40474 | 0.068 | 2.758 |
| 6000 | 33222955 | 0.074 | 2454.636 | 33728 | 0.099 | 3.347 | 33728 | 0.057 | 1.939 |
| 7000 | 33395959 | 0.059 | 1977.419 | 28910 | 0.087 | 2.517 | 28910 | 0.057 | 1.653 |
| 8000 | 33317181 | 0.063 | 2097.129 | 25296 | 0.076 | 1.915 | 25296 | 0.043 | 1.097 |
| 9000 | 33357715 | 0.072 | 2409.156 | 22485 | 0.075 | 1.691 | 22485 | 0.035 | 0.780 |
| 10000 | 33873349 | 0.061 | 2062.739 | 20237 | 0.063 | 1.282 | 20237 | 0.034 | 0.682 |

### 9.3 meta_reag
| interval | to_evict_count | to_evict_avg_ms | to_evict_total_s | tell_optimizer_count | tell_optimizer_avg_ms | tell_optimizer_total_s | tell_refill_count | tell_refill_avg_ms | tell_refill_total_s |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 100 | 492448 | 0.116 | 57.267 | 422425 | 0.103 | 43.410 | 422425 | 0.089 | 37.623 |
| 200 | 491018 | 0.116 | 57.041 | 211212 | 0.101 | 21.431 | 211212 | 0.087 | 18.337 |
| 500 | 480094 | 0.077 | 36.827 | 84485 | 0.099 | 8.349 | 84485 | 0.079 | 6.640 |
| 1000 | 522368 | 0.077 | 40.415 | 42242 | 0.103 | 4.348 | 42242 | 0.073 | 3.066 |
| 1500 | 2642696 | 0.077 | 202.926 | 28161 | 0.082 | 2.323 | 28161 | 0.052 | 1.468 |
| 2000 | 796055 | 0.111 | 88.262 | 21121 | 0.089 | 1.873 | 21121 | 0.045 | 0.956 |
| 3000 | 291444 | 0.087 | 25.432 | 14080 | 0.069 | 0.968 | 14080 | 0.033 | 0.464 |
| 4000 | 1397769 | 0.098 | 137.583 | 10560 | 0.075 | 0.797 | 10560 | 0.035 | 0.370 |
| 5000 | 124457 | 0.114 | 14.225 | 8448 | 0.079 | 0.667 | 8448 | 0.035 | 0.294 |
| 6000 | 3335307 | 0.102 | 338.725 | 7040 | 0.078 | 0.553 | 7040 | 0.036 | 0.252 |
| 7000 | 5385840 | 0.091 | 490.751 | 6034 | 0.073 | 0.443 | 6034 | 0.035 | 0.208 |
| 8000 | 1810938 | 0.101 | 182.642 | 5280 | 0.070 | 0.368 | 5280 | 0.036 | 0.188 |
| 9000 | 720821 | 0.090 | 64.963 | 4693 | 0.071 | 0.335 | 4693 | 0.035 | 0.165 |
| 10000 | 1418527 | 0.104 | 147.534 | 4224 | 0.082 | 0.345 | 4224 | 0.035 | 0.149 |

## 10. Which Part Dominates Time

结论先行：
- 全部 trace、全部 interval 下，绝对耗时主导项都是 `to_evict_total`。
- 在 CMA-ES 同步内部，`tell_optimizer` 通常高于 `tell_refill`，二者合计才是与 `to_evict_total` 对比的第二层耗时。

### 10.1 Absolute Total Time Ranges (s)
| trace | to_evict_total_s range | tell_optimizer_s range | tell_refill_s range | dominant |
|---|---:|---:|---:|---|
| 1063 | 277.987 ~ 698.088 | 3.758 ~ 374.239 | 2.175 ~ 322.378 | to_evict_total |
| wiki_2019t | 1935.511 ~ 2499.431 | 1.282 ~ 217.279 | 0.682 ~ 182.808 | to_evict_total |
| meta_reag | 14.225 ~ 490.751 | 0.335 ~ 43.410 | 0.149 ~ 37.623 | to_evict_total |

### 10.2 Share Insight (using section 9 totals)
- 当 interval 较小（如 100/200）时，`tell_optimizer` 与 `tell_refill` 的总时延会显著增大，但通常仍低于 `to_evict_total`。
- 随 interval 增大，`tell_optimizer`/`tell_refill` 总时延明显下降（同步频率下降），`to_evict_total` 仍保持主导地位。
- 在很多点上，`tell_optimizer > tell_refill`，且二者比值常见在约 `1.2x ~ 2.0x`。

### 10.3 Best-MR Points (for quick reference)
| trace | interval | to_evict_total_s | tell_optimizer_s | tell_refill_s | dominant |
|---|---:|---:|---:|---:|---|
| 1063 | 6000 | 277.987 | 5.987 | 4.063 | to_evict_total |
| wiki_2019t | 200 | 1953.583 | 115.231 | 91.137 | to_evict_total |
| meta_reag | 5000 | 14.225 | 0.667 | 0.294 | to_evict_total |
