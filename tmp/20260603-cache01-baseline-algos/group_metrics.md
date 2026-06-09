# Cache01 Baseline Algorithms Group Metrics

生成时间：2026-06-07 02:25:49

数据源：`tmp/20260603-cache01-baseline-algos/results/**/*.tsv`

只填入已经完整跑完的算法；未完成算法显示 `-`。相对指标需要同 cache 下 LRU 完整完成后才会填入。

## 完成度

| 算法 | cache01 | cache0001 |
|---|---:|---:|
| LRU | 0/0 | 0/0 |
| LHD | 0/0 | 0/0 |
| ARC | 0/0 | 0/0 |
| SIEVE | 0/0 | 0/0 |
| S3-FIFO | 0/0 | 0/0 |
| W-TinyLFU | 0/0 | 0/0 |
| LeCaR | 0/0 | 0/0 |
| CACHEUS | 0/0 | 0/0 |
| GL-Cache | 0/0 | 0/0 |
| 3L-Cache | 0/0 | 0/0 |
| LRB | 0/0 | 0/0 |

## cache01 (0.1)

### 相对 MR

每个 trace 的 MR / 同 cache 下该 trace 的 LRU MR，然后在组内算术平均。

| 算法 | tencentPhoto | metaKV | wiki | metaCDN | alibabaBlock | tencentBlock |
|---|---:|---:|---:|---:|---:|---:|
| LRU | - | - | - | - | - | - |
| LHD | - | - | - | - | - | - |
| ARC | - | - | - | - | - | - |
| SIEVE | - | - | - | - | - | - |
| S3-FIFO | - | - | - | - | - | - |
| W-TinyLFU | - | - | - | - | - | - |
| LeCaR | - | - | - | - | - | - |
| CACHEUS | - | - | - | - | - | - |
| GL-Cache | - | - | - | - | - | - |
| 3L-Cache | - | - | - | - | - | - |
| LRB | - | - | - | - | - | - |

### 相对 BMR

每个 trace 的 BMR / 同 cache 下该 trace 的 LRU BMR，然后在组内算术平均。

| 算法 | tencentPhoto | metaKV | wiki | metaCDN | alibabaBlock | tencentBlock |
|---|---:|---:|---:|---:|---:|---:|
| LRU | - | - | - | - | - | - |
| LHD | - | - | - | - | - | - |
| ARC | - | - | - | - | - | - |
| SIEVE | - | - | - | - | - | - |
| S3-FIFO | - | - | - | - | - | - |
| W-TinyLFU | - | - | - | - | - | - |
| LeCaR | - | - | - | - | - | - |
| CACHEUS | - | - | - | - | - | - |
| GL-Cache | - | - | - | - | - | - |
| 3L-Cache | - | - | - | - | - | - |
| LRB | - | - | - | - | - | - |

### 直接吞吐量 (MQPS)

每个 trace 使用 cachesim 结果行中的 throughput/MQPS 字段，然后在组内算术平均。

| 算法 | tencentPhoto | metaKV | wiki | metaCDN | alibabaBlock | tencentBlock | 平均 |
|---|---:|---:|---:|---:|---:|---:|---:|
| LRU | - | - | - | - | - | - | - |
| LHD | - | - | - | - | - | - | - |
| ARC | - | - | - | - | - | - | - |
| SIEVE | - | - | - | - | - | - | - |
| S3-FIFO | - | - | - | - | - | - | - |
| W-TinyLFU | - | - | - | - | - | - | - |
| LeCaR | - | - | - | - | - | - | - |
| CACHEUS | - | - | - | - | - | - | - |
| GL-Cache | - | - | - | - | - | - | - |
| 3L-Cache | - | - | - | - | - | - | - |
| LRB | - | - | - | - | - | - | - |

### 计算吞吐量 (Mreq/s)

每个 trace 的 n_req / runtime_sec / 1e6，然后在组内算术平均。

| 算法 | tencentPhoto | metaKV | wiki | metaCDN | alibabaBlock | tencentBlock | 平均 |
|---|---:|---:|---:|---:|---:|---:|---:|
| LRU | - | - | - | - | - | - | - |
| LHD | - | - | - | - | - | - | - |
| ARC | - | - | - | - | - | - | - |
| SIEVE | - | - | - | - | - | - | - |
| S3-FIFO | - | - | - | - | - | - | - |
| W-TinyLFU | - | - | - | - | - | - | - |
| LeCaR | - | - | - | - | - | - | - |
| CACHEUS | - | - | - | - | - | - | - |
| GL-Cache | - | - | - | - | - | - | - |
| 3L-Cache | - | - | - | - | - | - | - |
| LRB | - | - | - | - | - | - | - |

### CPU 开销 (sec/Mreq)

每个 trace 的 cpu_time_sec / (n_req / 1e6)，然后在组内算术平均。

| 算法 | tencentPhoto | metaKV | wiki | metaCDN | alibabaBlock | tencentBlock | 平均 |
|---|---:|---:|---:|---:|---:|---:|---:|
| LRU | - | - | - | - | - | - | - |
| LHD | - | - | - | - | - | - | - |
| ARC | - | - | - | - | - | - | - |
| SIEVE | - | - | - | - | - | - | - |
| S3-FIFO | - | - | - | - | - | - | - |
| W-TinyLFU | - | - | - | - | - | - | - |
| LeCaR | - | - | - | - | - | - | - |
| CACHEUS | - | - | - | - | - | - | - |
| GL-Cache | - | - | - | - | - | - | - |
| 3L-Cache | - | - | - | - | - | - | - |
| LRB | - | - | - | - | - | - | - |

## cache0001 (0.001)

### 相对 MR

每个 trace 的 MR / 同 cache 下该 trace 的 LRU MR，然后在组内算术平均。

| 算法 | tencentPhoto | metaKV | wiki | metaCDN | alibabaBlock | tencentBlock |
|---|---:|---:|---:|---:|---:|---:|
| LRU | - | - | - | - | - | - |
| LHD | - | - | - | - | - | - |
| ARC | - | - | - | - | - | - |
| SIEVE | - | - | - | - | - | - |
| S3-FIFO | - | - | - | - | - | - |
| W-TinyLFU | - | - | - | - | - | - |
| LeCaR | - | - | - | - | - | - |
| CACHEUS | - | - | - | - | - | - |
| GL-Cache | - | - | - | - | - | - |
| 3L-Cache | - | - | - | - | - | - |
| LRB | - | - | - | - | - | - |

### 相对 BMR

每个 trace 的 BMR / 同 cache 下该 trace 的 LRU BMR，然后在组内算术平均。

| 算法 | tencentPhoto | metaKV | wiki | metaCDN | alibabaBlock | tencentBlock |
|---|---:|---:|---:|---:|---:|---:|
| LRU | - | - | - | - | - | - |
| LHD | - | - | - | - | - | - |
| ARC | - | - | - | - | - | - |
| SIEVE | - | - | - | - | - | - |
| S3-FIFO | - | - | - | - | - | - |
| W-TinyLFU | - | - | - | - | - | - |
| LeCaR | - | - | - | - | - | - |
| CACHEUS | - | - | - | - | - | - |
| GL-Cache | - | - | - | - | - | - |
| 3L-Cache | - | - | - | - | - | - |
| LRB | - | - | - | - | - | - |

### 直接吞吐量 (MQPS)

每个 trace 使用 cachesim 结果行中的 throughput/MQPS 字段，然后在组内算术平均。

| 算法 | tencentPhoto | metaKV | wiki | metaCDN | alibabaBlock | tencentBlock | 平均 |
|---|---:|---:|---:|---:|---:|---:|---:|
| LRU | - | - | - | - | - | - | - |
| LHD | - | - | - | - | - | - | - |
| ARC | - | - | - | - | - | - | - |
| SIEVE | - | - | - | - | - | - | - |
| S3-FIFO | - | - | - | - | - | - | - |
| W-TinyLFU | - | - | - | - | - | - | - |
| LeCaR | - | - | - | - | - | - | - |
| CACHEUS | - | - | - | - | - | - | - |
| GL-Cache | - | - | - | - | - | - | - |
| 3L-Cache | - | - | - | - | - | - | - |
| LRB | - | - | - | - | - | - | - |

### 计算吞吐量 (Mreq/s)

每个 trace 的 n_req / runtime_sec / 1e6，然后在组内算术平均。

| 算法 | tencentPhoto | metaKV | wiki | metaCDN | alibabaBlock | tencentBlock | 平均 |
|---|---:|---:|---:|---:|---:|---:|---:|
| LRU | - | - | - | - | - | - | - |
| LHD | - | - | - | - | - | - | - |
| ARC | - | - | - | - | - | - | - |
| SIEVE | - | - | - | - | - | - | - |
| S3-FIFO | - | - | - | - | - | - | - |
| W-TinyLFU | - | - | - | - | - | - | - |
| LeCaR | - | - | - | - | - | - | - |
| CACHEUS | - | - | - | - | - | - | - |
| GL-Cache | - | - | - | - | - | - | - |
| 3L-Cache | - | - | - | - | - | - | - |
| LRB | - | - | - | - | - | - | - |

### CPU 开销 (sec/Mreq)

每个 trace 的 cpu_time_sec / (n_req / 1e6)，然后在组内算术平均。

| 算法 | tencentPhoto | metaKV | wiki | metaCDN | alibabaBlock | tencentBlock | 平均 |
|---|---:|---:|---:|---:|---:|---:|---:|
| LRU | - | - | - | - | - | - | - |
| LHD | - | - | - | - | - | - | - |
| ARC | - | - | - | - | - | - | - |
| SIEVE | - | - | - | - | - | - | - |
| S3-FIFO | - | - | - | - | - | - | - |
| W-TinyLFU | - | - | - | - | - | - | - |
| LeCaR | - | - | - | - | - | - | - |
| CACHEUS | - | - | - | - | - | - | - |
| GL-Cache | - | - | - | - | - | - | - |
| 3L-Cache | - | - | - | - | - | - | - |
| LRB | - | - | - | - | - | - | - |

## 吞吐量与 CPU 开销汇总

大缓存为 `cache01 (0.1)`，小缓存为 `cache0001 (0.001)`；单缓存平均为 6 个 trace 组均值之和除以 6，跨缓存平均为两个缓存均值的算术平均。

| 算法 | 大缓存直接吞吐量平均 | 小缓存直接吞吐量平均 | 直接吞吐量平均 | 大缓存计算吞吐量平均 | 小缓存计算吞吐量平均 | 计算吞吐量平均 | 大缓存 CPU 开销平均 | 小缓存 CPU 开销平均 | CPU 开销平均 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| LRU | - | - | - | - | - | - | - | - | - |
| LHD | - | - | - | - | - | - | - | - | - |
| ARC | - | - | - | - | - | - | - | - | - |
| SIEVE | - | - | - | - | - | - | - | - | - |
| S3-FIFO | - | - | - | - | - | - | - | - | - |
| W-TinyLFU | - | - | - | - | - | - | - | - | - |
| LeCaR | - | - | - | - | - | - | - | - | - |
| CACHEUS | - | - | - | - | - | - | - | - | - |
| GL-Cache | - | - | - | - | - | - | - | - | - |
| 3L-Cache | - | - | - | - | - | - | - | - | - |
| LRB | - | - | - | - | - | - | - | - | - |

<!--
all_complete=0
status LRU cache01 0/0
status LRU cache0001 0/0
status LHD cache01 0/0
status LHD cache0001 0/0
status ARC cache01 0/0
status ARC cache0001 0/0
status SIEVE cache01 0/0
status SIEVE cache0001 0/0
status S3-FIFO cache01 0/0
status S3-FIFO cache0001 0/0
status W-TinyLFU cache01 0/0
status W-TinyLFU cache0001 0/0
status LeCaR cache01 0/0
status LeCaR cache0001 0/0
status CACHEUS cache01 0/0
status CACHEUS cache0001 0/0
status GL-Cache cache01 0/0
status GL-Cache cache0001 0/0
status 3L-Cache cache01 0/0
status 3L-Cache cache0001 0/0
status LRB cache01 0/0
status LRB cache0001 0/0
-->
