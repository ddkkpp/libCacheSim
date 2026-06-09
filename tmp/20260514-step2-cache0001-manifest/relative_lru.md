# Step2 相对 LRU 汇总

生成时间：2026-06-08 10:57:11

数据源：`step2_cache0001_manifest_results.tsv`，LRU 基线：`docs/20260423-ablation-per-group-cache0001/cmaes版本/lru_summary_v7.md`

**cfg 说明**：MR 目标 `f001_orig`，BMR 目标 `f101_orig`/`f100_ns`（按 one_hit 阈值分流）。

## step2 (step02_event_rebuild) — cache0001
| group | n | avg(rel_mr) | avg(rel_bmr) |
| ---: | ---: | ---: | ---: |
| alibabaBlock | 1000 | 0.8793 | 0.9671 |
| metaCDN | 3 | 0.6759 | 0.9047 |
| metaKV | 5 | 0.5519 | 0.9809 |
| tencentBlock | 4755 | 0.8836 | 0.9561 |
| tencentPhoto | 2 | 0.8757 | 1.0500 |
| wiki | 3 | 0.6568 | 0.9100 |
| **avg(groups)** | - | **0.7539** | **0.9614** |

