# Hit/Miss GBM：按配置和 trace group 汇总

## 口径

- 数据来源：`tmp/20260526-hitmiss-gbm/results_all.tsv`
- 列为 6 个 trace group；行为实验配置。
- MR/BMR：对 group 内有效 trace 的 `mr` / `bmr` 做算术平均。
- 吞吐量计算值：优先使用 `n_req / runtime_sec` 得到 QPS；缺失时回退到 `mqps * 1e6`。
- 空单元格表示该配置在该 cache/group/metric 下没有有效结果。

## cache01

### MR

| config | alibabaBlock | metaCDN | metaKV | tencentBlock | tencentPhoto | wiki |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| hitmiss / MR target | 0.406077 | 0.413493 | 0.054612 | 0.294058 | 0.250431 | 0.116077 |
| hitmiss / BMR target | 0.418786 | 0.413706 | 0.058063 | 0.295882 | 0.246505 | 0.113970 |

### BMR

| config | alibabaBlock | metaCDN | metaKV | tencentBlock | tencentPhoto | wiki |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| hitmiss / MR target | 0.577548 | 0.213015 | 0.083062 | 0.400642 | 0.217718 | 0.199212 |
| hitmiss / BMR target | 0.582567 | 0.213029 | 0.074335 | 0.401444 | 0.215226 | 0.195501 |

### throughput_qps_calc

| config | alibabaBlock | metaCDN | metaKV | tencentBlock | tencentPhoto | wiki |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| hitmiss / MR target | 618,097.763 | 706,276.564 | 689,860.963 | 552,186.449 | 166,137.413 | 252,237.194 |
| hitmiss / BMR target | 265,040.856 | 411,772.701 | 373,594.523 | 342,615.303 | 144,252.974 | 199,501.285 |

## cache0001

### MR

| config | alibabaBlock | metaCDN | metaKV | tencentBlock | tencentPhoto | wiki |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| hitmiss / MR target | 0.623872 | 0.562149 | 0.248388 | 0.511356 | 0.698484 | 0.626656 |
| hitmiss / BMR target | 0.621018 | 0.562089 | 0.225567 | 0.508717 | 0.694671 | 0.622925 |

### BMR

| config | alibabaBlock | metaCDN | metaKV | tencentBlock | tencentPhoto | wiki |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| hitmiss / MR target | 0.793912 | 0.264420 | 0.315541 | 0.705427 | 0.658910 | 0.809124 |
| hitmiss / BMR target | 0.791648 | 0.264385 | 0.284851 | 0.703034 | 0.656108 | 0.806753 |

### throughput_qps_calc

| config | alibabaBlock | metaCDN | metaKV | tencentBlock | tencentPhoto | wiki |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| hitmiss / MR target | 246,937.847 | 596,310.406 | 278,373.482 | 322,141.573 | 148,576.282 | 176,913.897 |
| hitmiss / BMR target | 251,780.586 | 580,965.197 | 276,029.931 | 340,628.192 | 123,539.785 | 169,989.744 |

## 生成信息

- 有效聚合单元格数：72
- 配置数：2
