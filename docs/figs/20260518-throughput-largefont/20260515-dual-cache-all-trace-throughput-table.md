# cache=0.001 与 cache=0.01 全 trace 吞吐量对照表（去 cloudphysics）

数据来源：
- cache=0.001：从 [docs/20260514-step2-vs-v7-cache0001-compare.md](docs/20260514-step2-vs-v7-cache0001-compare.md) 的“各 group 吞吐量 QPS（已去 cloudphysics）”按 6 组等权平均得到。
- cache=0.01：直接使用 [docs/20260514-r128-step02-vs-v7-cache01-compare.md](docs/20260514-r128-step02-vs-v7-cache01-compare.md) 的“全 trace 吞吐量 QPS（去 cloudphysics）”。

口径说明：
- 单位均为 req/s。
- 两个缓存比例不同（0.001 vs 0.01），数值用于横向参考，不代表同配置直接对照。

每 trace 明细：
- [docs/20260515-cache0001-per-trace-maxavg-throughput.csv](docs/20260515-cache0001-per-trace-maxavg-throughput.csv)
- [docs/20260515-cache01-per-trace-maxavg-throughput.csv](docs/20260515-cache01-per-trace-maxavg-throughput.csv)

## 核心算法对照

| algo | cache=0.001 | cache=0.01 |
|---|---:|---:|
| step2 / RSD | 506,266 | 775,880 |
| cmaes-v7 | 151,757 | 532,311 |
| drl-v7 | 106,595 | 255,196 |

## 各算法全 trace 吞吐量对照

| canonical_algo | cache0001_algo_name | cache0001_qps | cache01_algo_name | cache01_qps |
|---|---|---:|---|---:|
| ARC | ARC | 4,368,724 | ARC | 3,169,661 |
| Cacheus | Cacheus | 1,374,487 | Cacheus | 1,004,066 |
| GL-Cache | GLCache | 2,407,826 | GL-Cache | 2,128,117 |
| LHD | LHD | 1,355,597 | LHD | 1,300,445 |
| LRU | LRU | 5,016,795 | LRU | 3,418,232 |
| LeCaR | LeCaR | 3,139,357 | LeCaR | 1,623,791 |
| S3-FIFO | S3FIFO-0.1000-2 | 2,980,467 | S3-FIFO | 2,181,174 |
| SIEVE | Sieve | 5,260,255 | SIEVE | 3,625,149 |
| W-TinyLFU | WTinyLFU-w0.01-SLRU | 2,135,222 | W-TinyLFU | 1,538,264 |
| LRB | LRB-BMR | 56,036 | LRB | 98,569 |
| ThreeLCache-OMR | ThreeLCache-OMR | 594,678 | - | - |
| ThreeLCache-BMR | ThreeLCache-BMR | 589,608 | - | - |
| 3L-Cache (OMR/BMR avg) | (ThreeLCache-OMR, ThreeLCache-BMR) | 592,143 | 3L-Cache | 818,287 |
