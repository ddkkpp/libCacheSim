# MR one_hit 策略搜索记录

## 范围

- 数据目录：
  - `docs/20260422-ablation-per-group-cache01/cmaes版本LOH`
  - `docs/20260423-ablation-per-group-cache0001/cmaes版本`
- 评价对象：MR 相对 LRU，即逐 trace 计算 `策略MR / LRU_MR`，再做 group 内平均。
- 组间平均：包含 6 组，纳入 `tencentPhoto`：`alibabaBlock`、`metaCDN`、`metaKV`、`tencentBlock`、`tencentPhoto`、`wiki`。
- 搜索空间：
  - v7：固定使用 `f001_orig`（fallback: `f100_ns`）。
  - 16 个固定配置。
  - 二分阈值策略：`one_hit <= threshold` 使用低分支配置，否则使用高分支配置；阈值从 `0.00` 到 `1.00`，步长 `0.01`。
- 搜索脚本：`tmp/20260519-v7-16cfg-relative-lru/search_mr_policy_fast_with_photo.py`
- 搜索输出：`tmp/20260519-v7-16cfg-relative-lru/search_mr_policy_fast_with_photo.out`

## 结论

MR 可以用 one_hit 做轻微优化，但收益明显小于 BMR，且跨 cache 目录不够稳健。

| 策略 | cache01 avg | cache0001 avg | combined avg |
|---|---:|---:|---:|
| v7 / fixed `f001_orig` | 0.733414 | 0.755325 | 0.744369 |
| cache01 best fixed: `f101_orig` | 0.733211 | - | - |
| cache0001 best fixed: `f001_orig` | - | 0.755325 | - |

单目录最优 one_hit 阈值策略如下：

| 目录 | 最优候选 | avg | 相对 v7 改善 |
|---|---|---:|---:|
| cache01 | `one_hit <= 0.67 ? f101_orig : f001_orig` | 0.730762 | -0.002652 |
| cache0001 | `one_hit <= 0.72 ? f000_orig : f001_orig` | 0.751107 | -0.004218 |

跨两个 cache 目录的 combined 最优候选是：

```text
one_hit <= 0.56 ? f101_orig : f001_orig
```

| 策略 | cache01 avg | cache0001 avg | combined avg | 相对 v7 combined 改善 |
|---|---:|---:|---:|---:|
| v7 / `f001_orig` | 0.733414 | 0.755325 | 0.744369 | 0.000000 |
| `one_hit <= 0.56 ? f101_orig : f001_orig` | 0.732529 | 0.755480 | 0.744005 | -0.000365 |

这个 combined 候选在 cache01 有小幅收益，但在 cache0001 略差，因此不适合作为稳健的 MR v8 规则。

## 组内结果

### cache01 最优候选：`one_hit <= 0.67 ? f101_orig : f001_orig`

| group | v7 | candidate | delta |
|---|---:|---:|---:|
| alibabaBlock | 0.757675 | 0.761173 | +0.003497 |
| metaCDN | 0.795650 | 0.795650 | 0.000000 |
| metaKV | 0.680273 | 0.677546 | -0.002727 |
| tencentBlock | 0.743574 | 0.746565 | +0.002991 |
| tencentPhoto | 0.891041 | 0.888283 | -0.002758 |
| wiki | 0.532269 | 0.515353 | -0.016916 |

### cache0001 最优候选：`one_hit <= 0.72 ? f000_orig : f001_orig`

| group | v7 | candidate | delta |
|---|---:|---:|---:|
| alibabaBlock | 0.877191 | 0.877916 | +0.000725 |
| metaCDN | 0.684855 | 0.684855 | 0.000000 |
| metaKV | 0.557128 | 0.531537 | -0.025591 |
| tencentBlock | 0.879309 | 0.878868 | -0.000440 |
| tencentPhoto | 0.873155 | 0.873155 | 0.000000 |
| wiki | 0.660313 | 0.660313 | 0.000000 |

## 建议

- MR 不建议直接引入统一 v8 one_hit 规则；`f001_orig` 作为 v7 MR 规则仍然稳健。
- 如果只针对单个 cache 目录调优，可以分别尝试：
  - cache01: `one_hit <= 0.67 ? f101_orig : f001_orig`。
  - cache0001: `one_hit <= 0.72 ? f000_orig : f001_orig`。
- 与 BMR 相比，MR 的 one_hit 优化收益更小，而且存在 group 间 trade-off，例如 cache01 中 `wiki` 明显改善，但 `alibabaBlock` 和 `tencentBlock` 变差。
- 后续如果要形成 MR v8，建议加入更多特征或约束，而不是只用 one_hit 单阈值。
