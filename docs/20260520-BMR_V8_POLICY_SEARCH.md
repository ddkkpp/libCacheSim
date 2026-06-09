# BMR v8 策略搜索记录

## 范围

- 数据目录：
  - `docs/20260422-ablation-per-group-cache01/cmaes版本LOH`
  - `docs/20260423-ablation-per-group-cache0001/cmaes版本`
- 评价对象：BMR 相对 LRU，即逐 trace 计算 `策略BMR / LRU_BMR`，再做 group 内平均。
- 组间平均：同时记录两种口径：
  - 非 photo 5 组：`alibabaBlock`、`metaCDN`、`metaKV`、`tencentBlock`、`wiki`。
  - 包含 photo 6 组：在上述 5 组基础上纳入 `tencentPhoto`。
- 搜索空间：
  - v7：`one_hit <= 0.72` 使用 `f100_ns`，否则使用 `f101_orig`。
  - 16 个固定配置。
  - 二分阈值策略：`one_hit <= threshold` 使用低分支配置，否则使用高分支配置；阈值从 `0.00` 到 `1.00`，步长 `0.01`。
- 搜索脚本：`tmp/20260519-v7-16cfg-relative-lru/search_bmr_policy_fast.py`
- 搜索输出：`tmp/20260519-v7-16cfg-relative-lru/search_bmr_policy_fast.out`
- 包含 photo 搜索脚本：`tmp/20260519-v7-16cfg-relative-lru/search_bmr_policy_fast_with_photo.py`
- 包含 photo 搜索输出：`tmp/20260519-v7-16cfg-relative-lru/search_bmr_policy_fast_with_photo.out`

## 结论

### 非 photo 5 组口径

固定单一配置没有超过 v7。两个 cache 目录中，固定配置里最好的都是 `f101_ns`，但平均值仍高于 v7。

| 策略 | cache01 avg | cache0001 avg | combined avg |
|---|---:|---:|---:|
| v7 | 0.867869 | 0.936819 | 0.902344 |
| best fixed: f101_ns | 0.879128 | 0.941431 | 0.910279 |

如果允许按目录单独选策略，两个目录各自都有优于 v7 的 one_hit 阈值策略：

| 目录 | 最优候选 | avg | 相对 v7 改善 |
|---|---|---:|---:|
| cache01 | `one_hit <= 0.66 ? f100_ns : f101_orig` | 0.861194 | -0.006675 |
| cache0001 | `one_hit <= 0.71 ? f000_ns : f101_orig` | 0.926507 | -0.010312 |

如果需要一个跨两个 cache 目录共用的候选，当前搜索到的 combined 最优是：

```text
one_hit <= 0.66 ? f000_ns : f101_orig
```

| 策略 | cache01 avg | cache0001 avg | combined avg | 相对 v7 combined 改善 |
|---|---:|---:|---:|---:|
| v7 | 0.867869 | 0.936819 | 0.902344 | 0.000000 |
| `one_hit <= 0.66 ? f000_ns : f101_orig` | 0.865802 | 0.927496 | 0.896649 | -0.005695 |

## 组内结果

### combined 最优候选：`one_hit <= 0.66 ? f000_ns : f101_orig`

| 目录 | group | v7 | candidate | delta |
|---|---|---:|---:|---:|
| cache01 | alibabaBlock | 0.874342 | 0.863590 | -0.010752 |
| cache01 | metaCDN | 0.874892 | 0.874892 | 0.000000 |
| cache01 | metaKV | 0.925819 | 0.920357 | -0.005463 |
| cache01 | tencentBlock | 0.893481 | 0.868821 | -0.024660 |
| cache01 | wiki | 0.770810 | 0.801349 | +0.030539 |
| cache0001 | alibabaBlock | 0.951320 | 0.951142 | -0.000178 |
| cache0001 | metaCDN | 0.918730 | 0.918730 | 0.000000 |
| cache0001 | metaKV | 0.963001 | 0.915079 | -0.047922 |
| cache0001 | tencentBlock | 0.943648 | 0.945131 | +0.001484 |
| cache0001 | wiki | 0.907399 | 0.907399 | 0.000000 |

### 包含 tencentPhoto 的 6 组口径

包含 `tencentPhoto` 后，仍能找到优于 v7 的 one_hit 阈值策略。由于 `tencentPhoto` 的部分 `_ns` 配置缺失，搜索中对“策略选中但配置缺失”的情况使用 `f100_ns` fallback，与 v7 的 fallback 思路保持一致。

| 策略 | cache01 avg | cache0001 avg | combined avg |
|---|---:|---:|---:|
| v7 | 0.888966 | 0.954879 | 0.921923 |
| best fixed: f101_ns | 0.898349 | 0.954099 | 0.926224 |

如果允许按目录单独选策略，包含 photo 后的最优候选为：

| 目录 | 最优候选 | avg | 相对 v7 改善 |
|---|---|---:|---:|
| cache01 | `one_hit <= 0.67 ? f100_ns : f101_orig` | 0.884088 | -0.004878 |
| cache0001 | `one_hit <= 0.71 ? f000_ns : f101_orig` | 0.946286 | -0.008594 |

如果需要一个跨两个 cache 目录共用、且包含 photo 的候选，当前 combined 最优是：

```text
one_hit <= 0.67 ? f000_ns : f101_orig
```

| 策略 | cache01 avg | cache0001 avg | combined avg | 相对 v7 combined 改善 |
|---|---:|---:|---:|---:|
| v7 | 0.888966 | 0.954879 | 0.921923 | 0.000000 |
| `one_hit <= 0.67 ? f000_ns : f101_orig` | 0.887944 | 0.947255 | 0.917600 | -0.004323 |

#### combined 最优候选组内结果（包含 photo）

| 目录 | group | v7 | candidate | delta |
|---|---|---:|---:|---:|
| cache01 | alibabaBlock | 0.874342 | 0.864440 | -0.009903 |
| cache01 | metaCDN | 0.874892 | 0.874892 | 0.000000 |
| cache01 | metaKV | 0.925819 | 0.920357 | -0.005463 |
| cache01 | tencentBlock | 0.893481 | 0.872176 | -0.021305 |
| cache01 | tencentPhoto | 0.994452 | 0.994452 | 0.000000 |
| cache01 | wiki | 0.770810 | 0.801349 | +0.030539 |
| cache0001 | alibabaBlock | 0.951320 | 0.951713 | +0.000393 |
| cache0001 | metaCDN | 0.918730 | 0.918730 | 0.000000 |
| cache0001 | metaKV | 0.963001 | 0.915079 | -0.047922 |
| cache0001 | tencentBlock | 0.943648 | 0.945430 | +0.001782 |
| cache0001 | tencentPhoto | 1.045179 | 1.045179 | 0.000000 |
| cache0001 | wiki | 0.907399 | 0.907399 | 0.000000 |

## 建议

- 若目标是单目录最优且不包含 photo：
  - cache01 使用 `one_hit <= 0.66 ? f100_ns : f101_orig`。
  - cache0001 使用 `one_hit <= 0.71 ? f000_ns : f101_orig`。
- 若目标是单目录最优且包含 photo：
  - cache01 使用 `one_hit <= 0.67 ? f100_ns : f101_orig`。
  - cache0001 使用 `one_hit <= 0.71 ? f000_ns : f101_orig`。
- 若目标是跨两个目录共用一个 BMR v8 候选：
  - 不包含 photo 口径优先试 `one_hit <= 0.66 ? f000_ns : f101_orig`。
  - 包含 photo 口径优先试 `one_hit <= 0.67 ? f000_ns : f101_orig`。
- 候选并非每个 group 都优于 v7，例如 cache01 的 `wiki` 在两个 combined 候选下都变差。因此它适合作为下一轮实验候选，不建议直接作为最终结论。
- 下一步建议在更多 cache size、`cloudphysics`/`twitter` 或 held-out trace 上验证，避免只对这两个目录过拟合。
