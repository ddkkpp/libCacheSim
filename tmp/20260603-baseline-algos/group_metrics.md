# Cache01 Baseline Algorithms Group Metrics

生成时间：2026-06-06 08:51:25

数据源：`tmp/20260603-cache01-baseline-algos/results/**/*.tsv`

只填入已经完整跑完的算法；未完成算法显示 `-`。相对指标需要同 cache 下 LRU 完整完成后才会填入。

## 完成度

| 算法 | cache01 | cache0001 |
|---|---:|---:|
| LRU | 5768/5768 | 5768/5768 |
| LHD | 5768/5768 | 5768/5768 |
| ARC | 5768/5768 | 5768/5768 |
| SIEVE | 5768/5768 | 5768/5768 |
| S3-FIFO | 5768/5768 | 5768/5768 |
| W-TinyLFU | 5768/5768 | 5768/5768 |
| LeCaR | 5768/5768 | 5768/5768 |
| CACHEUS | 5768/5768 | 5768/5768 |
| GL-Cache | 5768/5768 | 5768/5768 |
| 3L-Cache | 5768/5768 | 5768/5768 |
| LRB | 5768/5768 | 5762/5768 |

## cache01 (0.1)

### 相对 MR

每个 trace 的 MR / 同 cache 下该 trace 的 LRU MR，然后在组内算术平均。

| 算法 | tencentPhoto | metaKV | wiki | metaCDN | alibabaBlock | tencentBlock |
|---|---:|---:|---:|---:|---:|---:|
| LRU | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| LHD | 1.0369 | 0.8548 | 0.6575 | 0.7889 | 0.8392 | 0.8468 |
| ARC | 1.1075 | 1.0117 | 0.7864 | 1.0518 | 0.9797 | 0.9994 |
| SIEVE | 0.9604 | 0.9474 | 0.7618 | 1.0267 | 1.4445 | 1.0214 |
| S3-FIFO | 0.9609 | 0.9066 | 0.7489 | 0.9990 | 0.9254 | 0.9271 |
| W-TinyLFU | 1.0970 | 0.8704 | 0.7296 | 0.8532 | 0.9717 | 0.9040 |
| LeCaR | 0.9571 | 0.9640 | 0.8686 | 1.0001 | 0.9712 | 0.9825 |
| CACHEUS | 0.9626 | 0.9559 | 0.9002 | 1.0076 | 0.9538 | 0.9643 |
| GL-Cache | 0.9979 | 0.7647 | 0.6474 | 0.8386 | 0.8143 | 0.7917 |
| 3L-Cache | 1.1511 | 0.9399 | 0.7606 | 0.9833 | 0.9311 | 0.9394 |
| LRB | 1.0000 | 0.9852 | 0.9097 | 0.9717 | 0.9446 | 0.9316 |
| RSM | 1.3102 | 0.6698 | 0.5072 | 0.7824 | 0.9411 | 0.8596 |

### 相对 BMR

每个 trace 的 BMR / 同 cache 下该 trace 的 LRU BMR，然后在组内算术平均。

| 算法 | tencentPhoto | metaKV | wiki | metaCDN | alibabaBlock | tencentBlock |
|---|---:|---:|---:|---:|---:|---:|
| LRU | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| LHD | 1.4357 | 1.2160 | 1.3406 | 0.9595 | 0.9555 | 1.1393 |
| ARC | 1.1181 | 1.1433 | 0.8366 | 1.0375 | 0.9584 | 0.9756 |
| SIEVE | 0.9608 | 0.9562 | 0.8109 | 1.0106 | 1.2511 | 1.1962 |
| S3-FIFO | 0.9642 | 0.9212 | 0.8008 | 0.9767 | 0.9261 | 0.9190 |
| W-TinyLFU | 1.2055 | 1.0063 | 0.8502 | 0.8901 | 0.9330 | 0.9321 |
| LeCaR | 0.9541 | 0.9718 | 0.8982 | 1.0000 | 0.9797 | 0.9826 |
| CACHEUS | 0.9610 | 0.9679 | 0.9228 | 1.0012 | 0.9644 | 0.9667 |
| GL-Cache | 1.1657 | 1.1091 | 1.2434 | 0.9079 | 0.8810 | 1.0254 |
| 3L-Cache | 1.1790 | 0.9328 | 0.8093 | 0.9659 | 0.9228 | 0.9223 |
| LRB | 1.0000 | 0.9840 | 0.9179 | 0.9662 | 0.9240 | 0.9232 |
| RSM | 1.6405 | 1.2221 | 1.0582 | 0.8669 | 0.9175 | 1.0284 |

### 直接吞吐量 (MQPS)

每个 trace 使用 cachesim 结果行中的 throughput/MQPS 字段，然后在组内算术平均。

| 算法 | tencentPhoto | metaKV | wiki | metaCDN | alibabaBlock | tencentBlock | 平均 |
|---|---:|---:|---:|---:|---:|---:|---:|
| LRU | 0.695 | 0.834 | 0.603 | 0.323 | 1.033 | 0.751 | 0.706 |
| LHD | 0.410 | 0.750 | 0.533 | 0.337 | 0.980 | 0.757 | 0.628 |
| ARC | 0.670 | 0.836 | 0.603 | 0.340 | 1.038 | 0.751 | 0.706 |
| SIEVE | 0.875 | 2.362 | 1.413 | 1.930 | 1.746 | 0.758 | 1.514 |
| S3-FIFO | 0.590 | 0.836 | 0.620 | 0.343 | 0.872 | 0.767 | 0.671 |
| W-TinyLFU | 0.305 | 0.658 | 0.580 | 0.230 | 0.945 | 1.443 | 0.694 |
| LeCaR | 0.615 | 0.792 | 0.587 | 0.333 | 0.916 | 0.708 | 0.658 |
| CACHEUS | 0.415 | 0.960 | 0.520 | 0.350 | 0.894 | 0.884 | 0.671 |
| GL-Cache | 0.645 | 0.858 | 0.607 | 0.333 | 0.857 | 0.741 | 0.673 |
| 3L-Cache | 0.250 | 0.638 | 0.447 | 0.277 | 0.926 | 1.259 | 0.633 |
| LRB | 0.080 | 0.088 | 0.047 | 0.013 | 0.145 | 0.105 | 0.080 |
| RSM | 0.315 | 0.910 | 0.490 | 0.540 | 0.772 | 0.785 | 0.635 |

### 计算吞吐量 (Mreq/s)

每个 trace 的 n_req / runtime_sec / 1e6，然后在组内算术平均。

| 算法 | tencentPhoto | metaKV | wiki | metaCDN | alibabaBlock | tencentBlock | 平均 |
|---|---:|---:|---:|---:|---:|---:|---:|
| LRU | 0.695 | 0.832 | 0.605 | 0.325 | 0.586 | 0.640 | 0.614 |
| LHD | 0.412 | 0.749 | 0.534 | 0.337 | 0.623 | 0.687 | 0.557 |
| ARC | 0.669 | 0.833 | 0.606 | 0.340 | 0.580 | 0.639 | 0.611 |
| SIEVE | 0.875 | 2.363 | 1.415 | 1.932 | 1.268 | 0.639 | 1.415 |
| S3-FIFO | 0.589 | 0.838 | 0.620 | 0.344 | 0.607 | 0.702 | 0.617 |
| W-TinyLFU | 0.306 | 0.659 | 0.579 | 0.230 | 0.914 | 1.391 | 0.680 |
| LeCaR | 0.615 | 0.794 | 0.587 | 0.334 | 0.589 | 0.642 | 0.594 |
| CACHEUS | 0.416 | 0.963 | 0.520 | 0.350 | 0.843 | 0.869 | 0.660 |
| GL-Cache | 0.645 | 0.860 | 0.608 | 0.334 | 0.580 | 0.701 | 0.621 |
| 3L-Cache | 0.252 | 0.635 | 0.447 | 0.275 | 0.731 | 1.073 | 0.569 |
| LRB | 0.084 | 0.088 | 0.044 | 0.014 | 0.133 | 0.105 | 0.078 |
| RSM | 0.313 | 0.911 | 0.491 | 0.541 | 0.729 | 0.759 | 0.624 |

### CPU 开销 (sec/Mreq)

每个 trace 的 cpu_time_sec / (n_req / 1e6)，然后在组内算术平均。

| 算法 | tencentPhoto | metaKV | wiki | metaCDN | alibabaBlock | tencentBlock | 平均 |
|---|---:|---:|---:|---:|---:|---:|---:|
| LRU | 0.772 | 0.526 | 0.691 | 0.748 | 0.420 | 0.436 | 0.599 |
| LHD | 1.939 | 0.814 | 1.273 | 1.128 | 0.602 | 0.613 | 1.061 |
| ARC | 0.836 | 0.552 | 0.702 | 0.901 | 0.419 | 0.462 | 0.645 |
| SIEVE | 0.594 | 0.280 | 0.425 | 0.520 | 0.325 | 0.410 | 0.426 |
| S3-FIFO | 1.104 | 0.556 | 0.734 | 1.123 | 0.541 | 0.577 | 0.772 |
| W-TinyLFU | 2.347 | 1.047 | 1.211 | 3.889 | 1.695 | 1.254 | 1.907 |
| LeCaR | 1.025 | 0.663 | 0.896 | 1.014 | 0.498 | 0.559 | 0.776 |
| CACHEUS | 2.185 | 0.867 | 1.608 | 1.883 | 0.945 | 0.937 | 1.404 |
| GL-Cache | 0.896 | 0.519 | 0.747 | 0.867 | 0.572 | 0.512 | 0.685 |
| 3L-Cache | 3.911 | 1.589 | 2.320 | 3.645 | 1.290 | 1.143 | 2.316 |
| LRB | 11.859 | 12.959 | 29.259 | 75.642 | 33.503 | 34.213 | 32.906 |
| RSM | 3.584 | 1.311 | 2.291 | 2.081 | 1.443 | 1.533 | 2.008 |

## cache0001 (0.001)

### 相对 MR

每个 trace 的 MR / 同 cache 下该 trace 的 LRU MR，然后在组内算术平均。

| 算法 | tencentPhoto | metaKV | wiki | metaCDN | alibabaBlock | tencentBlock |
|---|---:|---:|---:|---:|---:|---:|
| LRU | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| LHD | 0.8745 | 0.5778 | 0.6628 | 0.8174 | 0.9047 | 0.9194 |
| ARC | 1.0051 | 0.9402 | 0.8276 | 1.0249 | 0.9184 | 0.9447 |
| SIEVE | 0.9825 | 0.9007 | 0.8063 | 1.0093 | 1.1328 | 1.0172 |
| S3-FIFO | 0.9499 | 0.8680 | 0.8000 | 0.9919 | 0.9042 | 0.9031 |
| W-TinyLFU | 0.9846 | 0.8222 | 0.7964 | 0.9126 | 1.0779 | 1.2259 |
| LeCaR | 0.9714 | 0.9429 | 0.9062 | 1.0003 | 0.9469 | 0.9520 |
| CACHEUS | 0.9620 | 0.9554 | 0.8855 | 1.0033 | 0.9130 | 0.9175 |
| GL-Cache | 1.0618 | 0.6560 | 0.8093 | 0.8565 | 1.1070 | 1.2030 |
| 3L-Cache | 0.9403 | 0.8601 | 0.7770 | 0.9990 | 0.9068 | 0.8959 |
| LRB | - | - | - | - | - | - |
| RSM | 0.9521 | 0.5700 | 0.6356 | 0.6658 | 0.9436 | 0.9557 |

### 相对 BMR

每个 trace 的 BMR / 同 cache 下该 trace 的 LRU BMR，然后在组内算术平均。

| 算法 | tencentPhoto | metaKV | wiki | metaCDN | alibabaBlock | tencentBlock |
|---|---:|---:|---:|---:|---:|---:|
| LRU | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| LHD | 1.1117 | 1.4063 | 1.0245 | 1.2387 | 1.0399 | 1.0732 |
| ARC | 0.9990 | 0.9869 | 0.9001 | 1.0565 | 0.9595 | 0.9578 |
| SIEVE | 0.9721 | 0.9378 | 0.8839 | 1.0045 | 1.0689 | 0.9988 |
| S3-FIFO | 0.9422 | 0.9137 | 0.8775 | 0.9922 | 0.9808 | 0.9488 |
| W-TinyLFU | 1.0129 | 1.0088 | 0.9001 | 1.2152 | 1.1081 | 1.1932 |
| LeCaR | 0.9680 | 0.9576 | 0.9470 | 1.0000 | 0.9772 | 0.9776 |
| CACHEUS | 0.9585 | 0.9667 | 0.9333 | 1.0000 | 0.9613 | 0.9583 |
| GL-Cache | 1.1930 | 1.1626 | 1.0673 | 0.9642 | 1.0575 | 1.1107 |
| 3L-Cache | 0.9312 | 0.9382 | 0.8637 | 0.9915 | 0.9524 | 0.9335 |
| LRB | - | - | - | - | - | - |
| RSM | 1.1421 | 1.2444 | 0.9671 | 0.8881 | 0.9799 | 1.0020 |

### 直接吞吐量 (MQPS)

每个 trace 使用 cachesim 结果行中的 throughput/MQPS 字段，然后在组内算术平均。

| 算法 | tencentPhoto | metaKV | wiki | metaCDN | alibabaBlock | tencentBlock | 平均 |
|---|---:|---:|---:|---:|---:|---:|---:|
| LRU | 0.730 | 0.876 | 0.603 | 0.323 | 1.106 | 0.756 | 0.733 |
| LHD | 0.355 | 0.716 | 0.433 | 0.337 | 0.957 | 0.770 | 0.595 |
| ARC | 0.720 | 0.872 | 0.603 | 0.340 | 1.154 | 0.766 | 0.743 |
| SIEVE | 0.900 | 2.406 | 1.580 | 2.233 | 2.048 | 0.766 | 1.656 |
| S3-FIFO | 0.685 | 0.846 | 0.573 | 0.343 | 0.983 | 0.788 | 0.703 |
| W-TinyLFU | 0.440 | 0.974 | 0.473 | 0.647 | 1.294 | 1.984 | 0.969 |
| LeCaR | 0.690 | 0.826 | 0.583 | 0.333 | 0.953 | 0.715 | 0.683 |
| CACHEUS | 0.500 | 0.958 | 0.500 | 0.350 | 1.106 | 1.001 | 0.736 |
| GL-Cache | 0.630 | 0.888 | 0.593 | 0.333 | 1.135 | 0.666 | 0.708 |
| 3L-Cache | 0.290 | 0.592 | 0.363 | 0.353 | 0.653 | 0.613 | 0.477 |
| LRB | 0.080 | 0.088 | 0.038 | 0.010 | 0.134 | 0.017 | 0.096 |
| RSM | 0.270 | 0.350 | 0.320 | 0.123 | 0.840 | 0.900 | 0.467 |

> LRB cache0001 的 tencentPhoto(2条)、metaKV(1条)、alibabaBlock(1条) 共 4 条 trace 使用 cache01 同 trace 吞吐量（MQPS 直接结果行）替代；其余 trace 取 cache0001 实际结果。来源：`tmp/20260603-baseline-algos/results/LRB/cache0001/`。

### 计算吞吐量 (Mreq/s)

每个 trace 的 n_req / runtime_sec / 1e6，然后在组内算术平均。

| 算法 | tencentPhoto | metaKV | wiki | metaCDN | alibabaBlock | tencentBlock | 平均 |
|---|---:|---:|---:|---:|---:|---:|---:|
| LRU | 0.729 | 0.873 | 0.605 | 0.325 | 0.587 | 0.641 | 0.627 |
| LHD | 0.356 | 0.716 | 0.433 | 0.337 | 0.660 | 0.716 | 0.536 |
| ARC | 0.718 | 0.870 | 0.606 | 0.340 | 0.580 | 0.640 | 0.626 |
| SIEVE | 0.900 | 2.407 | 1.580 | 2.235 | 1.469 | 0.640 | 1.539 |
| S3-FIFO | 0.681 | 0.849 | 0.575 | 0.345 | 0.611 | 0.704 | 0.627 |
| W-TinyLFU | 0.436 | 0.970 | 0.471 | 0.648 | 0.957 | 1.766 | 0.875 |
| LeCaR | 0.694 | 0.828 | 0.585 | 0.334 | 0.595 | 0.644 | 0.614 |
| CACHEUS | 0.497 | 0.957 | 0.501 | 0.350 | 1.029 | 0.968 | 0.717 |
| GL-Cache | 0.629 | 0.889 | 0.594 | 0.334 | 0.547 | 0.610 | 0.601 |
| 3L-Cache | 0.291 | 0.592 | 0.363 | 0.354 | 0.443 | 0.488 | 0.422 |
| LRB | 0.084 | 0.039 | 0.015 | 0.010 | 0.118 | 0.090 | 0.094 |
| RSM | 0.267 | 0.351 | 0.320 | 0.124 | 0.792 | 0.865 | 0.453 |

> LRB cache0001 的 tencentPhoto(2条)、metaKV(1条)、alibabaBlock(1条) 共 4 条 trace 使用 cache01 同 trace 的 `n_req/runtime_sec` 计算吞吐量替代；其余 trace 取 cache0001 实际结果。来源：`tmp/20260603-baseline-algos/results/LRB/cache0001/` 与 `cache01/`。

### CPU 开销 (sec/Mreq)

每个 trace 的 cpu_time_sec / (n_req / 1e6)，然后在组内算术平均。

| 算法 | tencentPhoto | metaKV | wiki | metaCDN | alibabaBlock | tencentBlock | 平均 |
|---|---:|---:|---:|---:|---:|---:|---:|
| LRU | 0.502 | 0.425 | 0.594 | 0.624 | 0.387 | 0.410 | 0.490 |
| LHD | 2.652 | 1.028 | 1.799 | 1.831 | 0.534 | 0.502 | 1.391 |
| ARC | 0.548 | 0.417 | 0.576 | 0.628 | 0.390 | 0.435 | 0.499 |
| SIEVE | 0.443 | 0.256 | 0.365 | 0.450 | 0.300 | 0.398 | 0.369 |
| S3-FIFO | 0.834 | 0.629 | 0.977 | 1.069 | 0.513 | 0.529 | 0.758 |
| W-TinyLFU | 1.772 | 0.767 | 1.676 | 1.657 | 0.780 | 0.577 | 1.205 |
| LeCaR | 0.716 | 0.548 | 0.745 | 1.090 | 0.471 | 0.523 | 0.682 |
| CACHEUS | 1.725 | 0.893 | 1.648 | 1.633 | 0.711 | 0.715 | 1.221 |
| GL-Cache | 0.938 | 0.483 | 0.992 | 1.105 | 1.605 | 1.648 | 1.128 |
| 3L-Cache | 3.431 | 1.709 | 2.796 | 2.572 | 2.399 | 2.545 | 2.575 |
| LRB | - | - | - | - | - | - | - |
| RSM | 4.274 | 3.434 | 3.946 | 8.529 | 1.527 | 1.369 | 3.813 |

## 吞吐量与 CPU 汇总

所有值为 `cache01` 和 `cache0001` 的总平均：`(大缓存值 + 小缓存值) / 2`。

- **全平均**：所有 status=ok trace 的指标直接算术平均。
- **先组**：先对每个 trace 组算术平均，再对 6 组等权平均。
- **≥1w**：排除 `n_req < 10,000` 的 trace。仅影响直接 MQPS（小 trace 有 MQPS 但缺 runtime/cpu），对计算吞吐量和 CPU 无影响（小 trace 本来就被排除）。
- 计算吞吐量 = `n_req / runtime_sec / 1e6`，CPU = `cpu_time_sec / (n_req / 1e6)`。

### 吞吐量与 CPU（统一口径：仅含 valid runtime 的 trace）

以下三张表使用**完全相同的 trace 子集**（status=ok 且 `runtime_sec` 有效），跨列可直比。

### 直接吞吐量 (MQPS)

| 算法 | 全平均 | 先组 | 总请求/总时间 | n |
|---|---:|---:|---:|---:|
| LRU | 0.634 | 0.621 | 0.687 | 11015 |
| LHD | 0.693 | 0.546 | 0.622 | 10991 |
| ARC | 0.632 | 0.619 | 0.686 | 11012 |
| SIEVE | 0.756 | 1.477 | 0.853 | 11001 |
| S3-FIFO | 0.690 | 0.622 | 0.700 | 11001 |
| W-TinyLFU | 1.481 | 0.780 | 0.737 | 10869 |
| LeCaR | 0.636 | 0.603 | 0.674 | 11007 |
| CACHEUS | 0.930 | 0.692 | 0.740 | 11084 |
| GL-Cache | 0.642 | 0.611 | 0.663 | 11070 |
| 3L-Cache | 0.759 | 0.498 | 0.448 | 10771 |
| LRB | 0.101 | 0.068 | 0.023 | 11501 |
| RSM | 0.810 | 0.542 | 0.523 | 11065 |

### 计算吞吐量 (Mreq/s)

| 算法 | 全平均 | 先组 | 总请求/总时间 | n |
|---|---:|---:|---:|---:|
| LRU | 0.632 | 0.620 | 0.687 | 11015 |
| LHD | 0.692 | 0.547 | 0.622 | 10991 |
| ARC | 0.630 | 0.618 | 0.686 | 11012 |
| SIEVE | 0.754 | 1.477 | 0.853 | 11001 |
| S3-FIFO | 0.688 | 0.622 | 0.700 | 11001 |
| W-TinyLFU | 1.472 | 0.777 | 0.737 | 10869 |
| LeCaR | 0.635 | 0.604 | 0.674 | 11007 |
| CACHEUS | 0.920 | 0.688 | 0.740 | 11084 |
| GL-Cache | 0.642 | 0.611 | 0.663 | 11070 |
| 3L-Cache | 0.748 | 0.495 | 0.448 | 10771 |
| LRB | 0.102 | 0.068 | 0.023 | 11501 |
| RSM | 0.803 | 0.539 | 0.523 | 11065 |

> 计算吞吐量与总请求/总时间在 LRU/LHD/ARC 上不严格相等——因为 `总请求/总时间` 是先求 `sum(n_req)/sum(runtime)` 再取两个缓存的平均；`全平均` 是每条 trace 的 `n_req/runtime` 求平均后再取两个缓存平均。两者等价于加权平均与简单平均的区别。

### CPU 开销 (sec/Mreq)

| 算法 | 全平均 | 先组 | n |
|---|---:|---:|---:|
| LRU | 0.454 | 0.564 | 10661 |
| LHD | 0.603 | 1.250 | 10740 |
| ARC | 0.477 | 0.591 | 10678 |
| SIEVE | 0.421 | 0.413 | 10635 |
| S3-FIFO | 0.591 | 0.789 | 10722 |
| W-TinyLFU | 1.036 | 1.597 | 10840 |
| LeCaR | 0.568 | 0.750 | 10794 |
| CACHEUS | 0.863 | 1.337 | 11066 |
| GL-Cache | 1.137 | 0.949 | 10961 |
| 3L-Cache | 1.980 | 2.523 | 10753 |
| LRB | 37.167 | 42.379 | 11501 |
| RSM | 1.460 | 2.941 | 11145 |

> CPU 的 n 略小于上面两张表——部分 trace 有 `runtime_sec` 但缺 `cpu_time_sec`。

> **n** = 参与计算的有效 trace 数（双缓存合计）。
> **全平均** = 所有 trace 直接算术平均；**先组** = 先组内平均再 6 组等权；**总请求/总时间** = `sum(n_req)/sum(runtime)`。
> 每张表使用各自算法自身的 `runtime_sec>0` 子集，各算法 n 不同。

### 交集口径（所有 12 算法共用同一 trace 子集）

取所有 12 个算法均有 `runtime_sec>0` 的 trace 交集（**n=10663**，双缓存合计），跨算法可直比。

| 算法 | MQPS 全平均 | MQPS 先组 | 计算吞吐全 | 计算吞吐先 | 总请求/总时间 | CPU 全 | CPU 先 |
|---|---:|---:|---:|---:|---:|---:|---:|
| LRU | 0.625 | 0.594 | 0.625 | 0.594 | 0.657 | 0.454 | 0.590 |
| LHD | 0.682 | 0.540 | 0.683 | 0.540 | 0.620 | 0.603 | 1.195 |
| ARC | 0.623 | 0.592 | 0.623 | 0.592 | 0.656 | 0.477 | 0.620 |
| SIEVE | 0.750 | 1.474 | 0.750 | 1.474 | 0.815 | 0.421 | 0.427 |
| S3-FIFO | 0.675 | 0.594 | 0.677 | 0.595 | 0.674 | 0.591 | 0.815 |
| W-TinyLFU | 1.483 | 0.767 | 1.481 | 0.766 | 0.753 | 1.008 | 1.629 |
| LeCaR | 0.628 | 0.577 | 0.629 | 0.578 | 0.647 | 0.568 | 0.780 |
| CACHEUS | 0.913 | 0.678 | 0.912 | 0.677 | 0.742 | 0.854 | 1.370 |
| GL-Cache | 0.635 | 0.591 | 0.636 | 0.592 | 0.637 | 1.134 | 0.945 |
| 3L-Cache | 0.755 | 0.491 | 0.747 | 0.488 | 0.447 | 1.986 | 2.571 |
| LRB | 0.066 | 0.055 | 0.066 | 0.055 | 0.023 | 39.510 | 43.495 |
| RSM | 0.791 | 0.543 | 0.792 | 0.543 | 0.545 | 1.473 | 2.885 |

> 交集口径：所有算法的值基于**完全相同的 10663 条 trace**，各列、各算法之间可直接比较。

各算法排除的 trace 分布（status=ok 但在交集中被排除，均缺 `runtime_sec`）：

| 算法 | 排除数 | alibabaBlock | tencentBlock | 其他 |
|---|---:|---:|---:|---|
| LRU | 352 | 34 | 315 | tencentPhoto:2, metaKV:1 |
| LHD | 328 | 25 | 300 | tencentPhoto:2, metaKV:1 |
| ARC | 349 | 31 | 315 | tencentPhoto:2, metaKV:1 |
| SIEVE | 338 | 24 | 311 | tencentPhoto:2, metaKV:1 |
| S3-FIFO | 338 | 31 | 304 | tencentPhoto:2, metaKV:1 |
| W-TinyLFU | 206 | 78 | 125 | tencentPhoto:2, metaKV:1 |
| LeCaR | 344 | 27 | 314 | tencentPhoto:2, metaKV:1 |
| CACHEUS | 421 | 78 | 340 | tencentPhoto:2, metaKV:1 |
| GL-Cache | 407 | 39 | 365 | tencentPhoto:2, metaKV:1 |
| 3L-Cache | 108 | 15 | 90 | tencentPhoto:2, metaKV:1 |
| LRB | 838 | 330 | 508 | — |
| RSM | 402 | 89 | 310 | tencentPhoto:2, metaKV:1 |

> 排除的 trace 几乎全部来自 alibabaBlock 和 tencentBlock，均为 `n_req < 20w` 的小 trace。tencentPhoto 2条和 metaKV 1条因 runtime=NA 被部分算法排除。LRB 排除最多（838），W-TinyLFU 排除最少（206）。

<!--
all_complete=0
status LRU cache01 5768/5768
status LRU cache0001 5768/5768
status LHD cache01 5768/5768
status LHD cache0001 5768/5768
status ARC cache01 5768/5768
status ARC cache0001 5768/5768
status SIEVE cache01 5768/5768
status SIEVE cache0001 5768/5768
status S3-FIFO cache01 5768/5768
status S3-FIFO cache0001 5768/5768
status W-TinyLFU cache01 5768/5768
status W-TinyLFU cache0001 5768/5768
status LeCaR cache01 5768/5768
status LeCaR cache0001 5768/5768
status CACHEUS cache01 5768/5768
status CACHEUS cache0001 5768/5768
status GL-Cache cache01 5768/5768
status GL-Cache cache0001 5768/5768
status 3L-Cache cache01 5768/5768
status 3L-Cache cache0001 5768/5768
status LRB cache01 5768/5768
status LRB cache0001 5762/5768
group_status 3L-Cache cache0001 alibabaBlock 1000/1000
group_status 3L-Cache cache0001 metaCDN 3/3
group_status 3L-Cache cache0001 metaKV 5/5
group_status 3L-Cache cache0001 tencentBlock 4755/4755
group_status 3L-Cache cache0001 tencentPhoto 2/2
group_status 3L-Cache cache0001 wiki 3/3
group_status 3L-Cache cache01 alibabaBlock 1000/1000
group_status 3L-Cache cache01 metaCDN 3/3
group_status 3L-Cache cache01 metaKV 5/5
group_status 3L-Cache cache01 tencentBlock 4755/4755
group_status 3L-Cache cache01 tencentPhoto 2/2
group_status 3L-Cache cache01 wiki 3/3
group_status ARC cache0001 alibabaBlock 1000/1000
group_status ARC cache0001 metaCDN 3/3
group_status ARC cache0001 metaKV 5/5
group_status ARC cache0001 tencentBlock 4755/4755
group_status ARC cache0001 tencentPhoto 2/2
group_status ARC cache0001 wiki 3/3
group_status ARC cache01 alibabaBlock 1000/1000
group_status ARC cache01 metaCDN 3/3
group_status ARC cache01 metaKV 5/5
group_status ARC cache01 tencentBlock 4755/4755
group_status ARC cache01 tencentPhoto 2/2
group_status ARC cache01 wiki 3/3
group_status CACHEUS cache0001 alibabaBlock 1000/1000
group_status CACHEUS cache0001 metaCDN 3/3
group_status CACHEUS cache0001 metaKV 5/5
group_status CACHEUS cache0001 tencentBlock 4755/4755
group_status CACHEUS cache0001 tencentPhoto 2/2
group_status CACHEUS cache0001 wiki 3/3
group_status CACHEUS cache01 alibabaBlock 1000/1000
group_status CACHEUS cache01 metaCDN 3/3
group_status CACHEUS cache01 metaKV 5/5
group_status CACHEUS cache01 tencentBlock 4755/4755
group_status CACHEUS cache01 tencentPhoto 2/2
group_status CACHEUS cache01 wiki 3/3
group_status GL-Cache cache0001 alibabaBlock 1000/1000
group_status GL-Cache cache0001 metaCDN 3/3
group_status GL-Cache cache0001 metaKV 5/5
group_status GL-Cache cache0001 tencentBlock 4755/4755
group_status GL-Cache cache0001 tencentPhoto 2/2
group_status GL-Cache cache0001 wiki 3/3
group_status GL-Cache cache01 alibabaBlock 1000/1000
group_status GL-Cache cache01 metaCDN 3/3
group_status GL-Cache cache01 metaKV 5/5
group_status GL-Cache cache01 tencentBlock 4755/4755
group_status GL-Cache cache01 tencentPhoto 2/2
group_status GL-Cache cache01 wiki 3/3
group_status LHD cache0001 alibabaBlock 1000/1000
group_status LHD cache0001 metaCDN 3/3
group_status LHD cache0001 metaKV 5/5
group_status LHD cache0001 tencentBlock 4755/4755
group_status LHD cache0001 tencentPhoto 2/2
group_status LHD cache0001 wiki 3/3
group_status LHD cache01 alibabaBlock 1000/1000
group_status LHD cache01 metaCDN 3/3
group_status LHD cache01 metaKV 5/5
group_status LHD cache01 tencentBlock 4755/4755
group_status LHD cache01 tencentPhoto 2/2
group_status LHD cache01 wiki 3/3
group_status LRB cache0001 alibabaBlock 999/1000
group_status LRB cache0001 metaCDN 3/3
group_status LRB cache0001 metaKV 4/5
group_status LRB cache0001 tencentBlock 4755/4755
group_status LRB cache0001 tencentPhoto 0/2
group_status LRB cache0001 wiki 1/3
group_status LRB cache01 alibabaBlock 1000/1000
group_status LRB cache01 metaCDN 3/3
group_status LRB cache01 metaKV 5/5
group_status LRB cache01 tencentBlock 4755/4755
group_status LRB cache01 tencentPhoto 2/2
group_status LRB cache01 wiki 3/3
group_status LRU cache0001 alibabaBlock 1000/1000
group_status LRU cache0001 metaCDN 3/3
group_status LRU cache0001 metaKV 5/5
group_status LRU cache0001 tencentBlock 4755/4755
group_status LRU cache0001 tencentPhoto 2/2
group_status LRU cache0001 wiki 3/3
group_status LRU cache01 alibabaBlock 1000/1000
group_status LRU cache01 metaCDN 3/3
group_status LRU cache01 metaKV 5/5
group_status LRU cache01 tencentBlock 4755/4755
group_status LRU cache01 tencentPhoto 2/2
group_status LRU cache01 wiki 3/3
group_status LeCaR cache0001 alibabaBlock 1000/1000
group_status LeCaR cache0001 metaCDN 3/3
group_status LeCaR cache0001 metaKV 5/5
group_status LeCaR cache0001 tencentBlock 4755/4755
group_status LeCaR cache0001 tencentPhoto 2/2
group_status LeCaR cache0001 wiki 3/3
group_status LeCaR cache01 alibabaBlock 1000/1000
group_status LeCaR cache01 metaCDN 3/3
group_status LeCaR cache01 metaKV 5/5
group_status LeCaR cache01 tencentBlock 4755/4755
group_status LeCaR cache01 tencentPhoto 2/2
group_status LeCaR cache01 wiki 3/3
group_status S3-FIFO cache0001 alibabaBlock 1000/1000
group_status S3-FIFO cache0001 metaCDN 3/3
group_status S3-FIFO cache0001 metaKV 5/5
group_status S3-FIFO cache0001 tencentBlock 4755/4755
group_status S3-FIFO cache0001 tencentPhoto 2/2
group_status S3-FIFO cache0001 wiki 3/3
group_status S3-FIFO cache01 alibabaBlock 1000/1000
group_status S3-FIFO cache01 metaCDN 3/3
group_status S3-FIFO cache01 metaKV 5/5
group_status S3-FIFO cache01 tencentBlock 4755/4755
group_status S3-FIFO cache01 tencentPhoto 2/2
group_status S3-FIFO cache01 wiki 3/3
group_status SIEVE cache0001 alibabaBlock 1000/1000
group_status SIEVE cache0001 metaCDN 3/3
group_status SIEVE cache0001 metaKV 5/5
group_status SIEVE cache0001 tencentBlock 4755/4755
group_status SIEVE cache0001 tencentPhoto 2/2
group_status SIEVE cache0001 wiki 3/3
group_status SIEVE cache01 alibabaBlock 1000/1000
group_status SIEVE cache01 metaCDN 3/3
group_status SIEVE cache01 metaKV 5/5
group_status SIEVE cache01 tencentBlock 4755/4755
group_status SIEVE cache01 tencentPhoto 2/2
group_status SIEVE cache01 wiki 3/3
group_status W-TinyLFU cache0001 alibabaBlock 1000/1000
group_status W-TinyLFU cache0001 metaCDN 3/3
group_status W-TinyLFU cache0001 metaKV 5/5
group_status W-TinyLFU cache0001 tencentBlock 4755/4755
group_status W-TinyLFU cache0001 tencentPhoto 2/2
group_status W-TinyLFU cache0001 wiki 3/3
group_status W-TinyLFU cache01 alibabaBlock 1000/1000
group_status W-TinyLFU cache01 metaCDN 3/3
group_status W-TinyLFU cache01 metaKV 5/5
group_status W-TinyLFU cache01 tencentBlock 4755/4755
group_status W-TinyLFU cache01 tencentPhoto 2/2
group_status W-TinyLFU cache01 wiki 3/3
-->
