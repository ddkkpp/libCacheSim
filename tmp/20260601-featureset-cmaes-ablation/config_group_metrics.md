# Feature Set CMA-ES：按配置和 trace group 汇总

## 口径

- 数据来源：`tmp/20260601-featureset-cmaes-ablation/results_all.tsv`
- 列为 6 个 trace group；行为实验配置。
- MR/BMR：对 group 内有效 trace 的 `mr` / `bmr` 做算术平均。
- 吞吐量计算值：优先使用 `n_req / runtime_sec` 得到 QPS；缺失时回退到 `mqps * 1e6`。
- 空单元格表示该配置在该 cache/group/metric 下没有有效结果。

## cache01

### MR

| config | alibabaBlock | metaCDN | metaKV | tencentBlock | tencentPhoto | wiki |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 3lcache | 0.329725 | 0.322656 | 0.038709 | 0.227336 | 0.223975 | 0.074457 |
| lrb | 0.535767 | 0.438977 | 0.233336 | 0.447549 | 0.747819 | 0.601131 |

### BMR

| config | alibabaBlock | metaCDN | metaKV | tencentBlock | tencentPhoto | wiki |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 3lcache | 0.497739 | 0.182790 | 0.099310 | 0.350310 | 0.230426 | 0.193219 |
| lrb | 0.706860 | 0.301268 | 0.359694 | 0.616225 | 0.751937 | 0.828828 |

### throughput_qps_calc

| config | alibabaBlock | metaCDN | metaKV | tencentBlock | tencentPhoto | wiki |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 3lcache | 302,347.460 | 365,009.790 | 993,929.222 | 374,043.242 | 126,015.153 | 512,234.894 |
| lrb | 89,512.387 | 91,642.845 | 130,689.996 | 100,337.628 | 69,804.760 | 59,643.919 |

## cache0001

### MR

| config | alibabaBlock | metaCDN | metaKV | tencentBlock | tencentPhoto | wiki |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 3lcache | 0.561519 | 0.395143 | 0.126351 | 0.448072 | 0.633774 | 0.438676 |
| lrb | 0.633232 | 0.536817 | 0.380097 | 0.543830 | 0.859368 | 0.750209 |

### BMR

| config | alibabaBlock | metaCDN | metaKV | tencentBlock | tencentPhoto | wiki |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 3lcache | 0.762355 | 0.234998 | 0.327856 | 0.677745 | 0.704207 | 0.756798 |
| lrb | 0.802844 | 0.354929 | 0.497678 | 0.738152 | 0.869572 | 0.919191 |

### throughput_qps_calc

| config | alibabaBlock | metaCDN | metaKV | tencentBlock | tencentPhoto | wiki |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 3lcache | 385,095.806 | 108,745.216 | 234,852.529 | 357,860.347 | 52,605.409 | 86,440.375 |
| lrb | 126,760.029 | 41,439.225 | 112,165.587 | 130,828.529 | 53,440.403 | 45,180.102 |

## 生成信息

- 有效聚合单元格数：72
- 配置数：2
