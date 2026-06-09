# Alibaba 740 one-hit selected LOH

Selection rule: use `f100_ns` when `one_hit <= 0.72`, otherwise use `f101_orig`.

Warmdiag selection:

| ratio | one_hit | selected |
|---:|---:|---|
| 0.001 | 0.8740 | LOH_F101_ORIG |
| 0.01 | 0.8411 | LOH_F101_ORIG |
| 0.02 | 0.8646 | LOH_F101_ORIG |
| 0.05 | 0.8390 | LOH_F101_ORIG |
| 0.1 | 0.7380 | LOH_F101_ORIG |

Combined result table is in `combined_summary.tsv`.
