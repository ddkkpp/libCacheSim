# Baseline 缺失清单

数据来源: /home/丁坤鹏/libCacheSim/result

匹配规则: result 中 cache size 与 per-group 文档表1的 cache_size 误差在 5% 以内，视为同一配置。

目标算法: ARC, Cacheus, GDSF, GLCache, LHD, LRU, LeCaR, S3FIFO-0.1000-2, Sieve, WTinyLFU-w0.01-SLRU, LRB-BMR, ThreeLCache-BMR

## alibabaBlock

总 trace 数: 1000
存在缺失算法的 trace 数: 0

### 算法覆盖

| algorithm | covered_traces |
|---|---:|
| ARC | 1000/1000 |
| Cacheus | 1000/1000 |
| GDSF | 1000/1000 |
| GLCache | 1000/1000 |
| LHD | 1000/1000 |
| LRU | 1000/1000 |
| LeCaR | 1000/1000 |
| S3FIFO-0.1000-2 | 1000/1000 |
| Sieve | 1000/1000 |
| WTinyLFU-w0.01-SLRU | 1000/1000 |
| LRB-BMR | 1000/1000 |
| ThreeLCache-BMR | 1000/1000 |

### 缺失明细

| trace | cache_size | missing_algorithms | matched_algorithms |
|---|---|---|---|
| 无 | 无 | 无 | 全部算法齐全 |

## cloudphysics

总 trace 数: 106
存在缺失算法的 trace 数: 0

### 算法覆盖

| algorithm | covered_traces |
|---|---:|
| ARC | 106/106 |
| Cacheus | 106/106 |
| GDSF | 106/106 |
| GLCache | 106/106 |
| LHD | 106/106 |
| LRU | 106/106 |
| LeCaR | 106/106 |
| S3FIFO-0.1000-2 | 106/106 |
| Sieve | 106/106 |
| WTinyLFU-w0.01-SLRU | 106/106 |
| LRB-BMR | 106/106 |
| ThreeLCache-BMR | 106/106 |

### 缺失明细

| trace | cache_size | missing_algorithms | matched_algorithms |
|---|---|---|---|
| 无 | 无 | 无 | 全部算法齐全 |

## metaCDN

总 trace 数: 3
存在缺失算法的 trace 数: 0

### 算法覆盖

| algorithm | covered_traces |
|---|---:|
| ARC | 3/3 |
| Cacheus | 3/3 |
| GDSF | 3/3 |
| GLCache | 3/3 |
| LHD | 3/3 |
| LRU | 3/3 |
| LeCaR | 3/3 |
| S3FIFO-0.1000-2 | 3/3 |
| Sieve | 3/3 |
| WTinyLFU-w0.01-SLRU | 3/3 |
| LRB-BMR | 3/3 |
| ThreeLCache-BMR | 3/3 |

### 缺失明细

| trace | cache_size | missing_algorithms | matched_algorithms |
|---|---|---|---|
| 无 | 无 | 无 | 全部算法齐全 |

## metaKV

总 trace 数: 5
存在缺失算法的 trace 数: 0

### 算法覆盖

| algorithm | covered_traces |
|---|---:|
| ARC | 5/5 |
| Cacheus | 5/5 |
| GDSF | 5/5 |
| GLCache | 5/5 |
| LHD | 5/5 |
| LRU | 5/5 |
| LeCaR | 5/5 |
| S3FIFO-0.1000-2 | 5/5 |
| Sieve | 5/5 |
| WTinyLFU-w0.01-SLRU | 5/5 |
| LRB-BMR | 5/5 |
| ThreeLCache-BMR | 5/5 |

### 缺失明细

| trace | cache_size | missing_algorithms | matched_algorithms |
|---|---|---|---|
| 无 | 无 | 无 | 全部算法齐全 |

## tencentBlock

总 trace 数: 4755
存在缺失算法的 trace 数: 0

### 算法覆盖

| algorithm | covered_traces |
|---|---:|
| ARC | 4755/4755 |
| Cacheus | 4755/4755 |
| GDSF | 4755/4755 |
| GLCache | 4755/4755 |
| LHD | 4755/4755 |
| LRU | 4755/4755 |
| LeCaR | 4755/4755 |
| S3FIFO-0.1000-2 | 4755/4755 |
| Sieve | 4755/4755 |
| WTinyLFU-w0.01-SLRU | 4755/4755 |
| LRB-BMR | 4755/4755 |
| ThreeLCache-BMR | 4755/4755 |

### 缺失明细

无缺失（LRB-BMR @ tencentBlock_1548 已于 20260423 从 tmp/20260415-baseline-fill 覆盖入表，MR=0.726526, BMR=0.481776）。

## tencentPhoto

总 trace 数: 2
存在缺失算法的 trace 数: 0

### 算法覆盖

| algorithm | covered_traces |
|---|---:|
| ARC | 2/2 |
| Cacheus | 2/2 |
| GDSF | 2/2 |
| GLCache | 2/2 |
| LHD | 2/2 |
| LRU | 2/2 |
| LeCaR | 2/2 |
| S3FIFO-0.1000-2 | 2/2 |
| Sieve | 2/2 |
| WTinyLFU-w0.01-SLRU | 2/2 |
| LRB-BMR | 2/2 |
| ThreeLCache-BMR | 2/2 |

### 缺失明细

| trace | cache_size | missing_algorithms | matched_algorithms |
|---|---|---|---|
| 无 | 无 | 无 | 全部算法齐全 |

## twitter

总 trace 数: 11
存在缺失算法的 trace 数: 0

### 算法覆盖

| algorithm | covered_traces |
|---|---:|
| ARC | 11/11 |
| Cacheus | 11/11 |
| GDSF | 11/11 |
| GLCache | 11/11 |
| LHD | 11/11 |
| LRU | 11/11 |
| LeCaR | 11/11 |
| S3FIFO-0.1000-2 | 11/11 |
| Sieve | 11/11 |
| WTinyLFU-w0.01-SLRU | 11/11 |
| LRB-BMR | 11/11 |
| ThreeLCache-BMR | 11/11 |

### 缺失明细

| trace | cache_size | missing_algorithms | matched_algorithms |
|---|---|---|---|
| 无 | 无 | 无 | 全部算法齐全 |

## wiki

总 trace 数: 3
存在缺失算法的 trace 数: 0

### 算法覆盖

| algorithm | covered_traces |
|---|---:|
| ARC | 3/3 |
| Cacheus | 3/3 |
| GDSF | 3/3 |
| GLCache | 3/3 |
| LHD | 3/3 |
| LRU | 3/3 |
| LeCaR | 3/3 |
| S3FIFO-0.1000-2 | 3/3 |
| Sieve | 3/3 |
| WTinyLFU-w0.01-SLRU | 3/3 |
| LRB-BMR | 3/3 |
| ThreeLCache-BMR | 3/3 |

### 缺失明细

| trace | cache_size | missing_algorithms | matched_algorithms |
|---|---|---|---|
| 无 | 无 | 无 | 全部算法齐全 |
