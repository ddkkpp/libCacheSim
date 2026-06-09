# 20260529 Post-return-poison 同基线前后对照测试

## 1. 目标

- 在同一基线规则下，仅调整 poison 强度，验证两件事：
  - cache size 0.1 和 0.001 下，LOH 是否都优于 LRB/3L。
  - 加噪前后，LRB/3L 的 MR 退化是否明显。

## 2. 产物路径

- 对照目录：[tmp/20260529-two-stage-compare-search](tmp/20260529-two-stage-compare-search)
- 对照汇总表：[tmp/20260529-two-stage-compare-search/results/comparison_table.tsv](tmp/20260529-two-stage-compare-search/results/comparison_table.tsv)
- 下降差值表：[tmp/20260529-two-stage-compare-search/results/delta_vs_base.tsv](tmp/20260529-two-stage-compare-search/results/delta_vs_base.tsv)

## 3. 生成口径与参数

- 生成脚本：[scripts/gen_label_noise_preference_trace.py](scripts/gen_label_noise_preference_trace.py)
- 机制：候选对象先返回，再注入 poison（post-return-poison）。

### 3.1 case 定义

- base_clean：poison-per-epoch=0
- noise_p2048：poison-per-epoch=2048
- noise_p3072：poison-per-epoch=3072

### 3.2 固定参数

- epochs=120
- hot-pool=65536
- filler-pool=65536
- candidate-per-epoch=64
- short-gap-per-epoch=16
- tail-gap-per-epoch=512
- candidate-burst-repeats=5
- poison-burst-repeats=1
- return-repeats=2
- candidate-size=4096
- poison-size=4096
- scan-size=4096

## 4. 双缓存下 LOH 与 LRB/3L 对比（MR）

| case | cache | LRB-BMR | 3LCache-BMR | 3LCache-OMR | LOH |
|---|---:|---:|---:|---:|---:|
| noise_p2048 | 0.1 | 0.865909 | 0.859915 | 0.859923 | 0.827017 |
| noise_p2048 | 0.001 | 0.874846 | 0.873476 | 0.884538 | 0.873016 |
| noise_p3072 | 0.1 | 0.896628 | 0.895267 | 0.894938 | 0.855416 |
| noise_p3072 | 0.001 | 0.907028 | 0.911277 | 0.914285 | 0.905015 |

结论：在 noise_p2048 和 noise_p3072 下，cache=0.1 与 0.001 两档中，LOH 都优于 LRB 与 3L（BMR/OMR）。

## 5. 噪声前后下降幅度（noise - base，MR 增量）

| noise case | cache | LRB-BMR | 3LCache-BMR | 3LCache-OMR | LOH |
|---|---:|---:|---:|---:|---:|
| noise_p2048 | 0.1 | +0.259352 | +0.253358 | +0.253366 | +0.220460 |
| noise_p2048 | 0.001 | +0.202715 | +0.201345 | +0.212407 | +0.244652 |
| noise_p3072 | 0.1 | +0.290071 | +0.288710 | +0.288381 | +0.248859 |
| noise_p3072 | 0.001 | +0.234897 | +0.239146 | +0.242154 | +0.276651 |

说明：

- 0.1 档中，LRB/3L 退化明显，LOH 仍保持更低 MR。
- 0.001 档中，LRB/3L 同样明显退化；LOH 也受影响，但最终 MR 仍低于 LRB/3L。
