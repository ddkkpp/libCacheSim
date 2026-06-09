# cache01 + fixxxx-cache0001 四值平均对比

生成时间: 2026-06-07 11:37:10

- 左侧缓存来源: `docs/20260422-ablation-per-group-cache01/cmaes版本LOH/20260519-v7-16cfg-relative-lru-6groups.md`
- 右侧缓存来源: `docs/20260423-ablation-per-group-fixxxx-cache0001/cmaes版本LOH/20260519-v7-16cfg-relative-lru-6groups.md`
- 单元格定义: 对同一 config、同一 trace group，取 `cache01 相对 MR`、`cache01 相对 BMR`、`cache0001 相对 MR`、`cache0001 相对 BMR` 四个值的简单平均。
- 组平均: 对 6 个 trace group 的单元格做等权平均；任一 group 四值不齐则该格为 `-`。
- `cache01:v7` 与 `fixxxx-cache0001:best_LOH` 作为同一 LOH/best 策略行配对；fixxxx 的其他 baseline 算法没有 cache01 v7-16cfg 同名行，因此不进入四值平均表。

| config | alibabaBlock | metaCDN | metaKV | tencentBlock | tencentPhoto | wiki | avg_6groups |
|---|---:|---:|---:|---:|---:|---:|---:|
| v7 + best_LOH | 0.855158 | 0.811000 | 0.760037 | 0.850393 | 0.929814 | 0.702905 | 0.818218 |
| v7(原cache0001) | 0.865132 | 0.818532 | 0.781555 | 0.865003 | 0.950957 | 0.717698 | 0.833146 |
