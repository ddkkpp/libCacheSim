# 各配置相对 LRU 汇总

数据来源：

- **cs01 / cs0001 (CMA-ES v7)**：`docs/baseline_three_cache_compare.md`，best_LOH（v7 策略）
- **original / pool_off_b16**：`tmp/20260606-loh-adaptive-batch-experiments/group_metrics_rel_lru.md`，f001_orig 逐 trace 相对 LRU 后组内平均
- **r128 step01/step02**：`tmp/20260512-loh-route-ablation/final-step01-step02-r128/relative_lru.md`，逐 trace 相对 LRU 后组内平均
- **step2**：`tmp/20260514-step2-cache0001-manifest/relative_lru.md`，逐 trace 相对 LRU 后组内平均

---

## cache01 — 相对 MR

| 配置 | alibabaBlock | metaCDN | metaKV | tencentBlock | tencentPhoto | wiki | 组平均 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| cs01 (CMA-ES v7) | 0.7577 | 0.7957 | 0.6803 | 0.7436 | 0.8910 | 0.5323 | 0.7334 |
| r128 step01_health_guard | 0.7586 | 0.7847 | 0.6782 | 0.7373 | 0.8916 | 0.5158 | 0.7277 |
| r128 step02_event_rebuild | 0.7651 | 0.7955 | 0.6812 | 0.7453 | 0.8919 | 0.5208 | 0.7333 |
| pool_off_b16 | 0.7996 | 0.7976 | 0.6793 | 0.7955 | 0.8881 | 0.5262 | 0.7477 |
| original (pool on, batch=4) | 0.9411 | 0.7824 | 0.6698 | 0.8596 | 1.3102 | 0.5072 | 0.8451 |

## cache01 — 相对 BMR

| 配置 | alibabaBlock | metaCDN | metaKV | tencentBlock | tencentPhoto | wiki | 组平均 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| cs01 (CMA-ES v7) | 0.8743 | 0.8749 | 0.9258 | 0.8935 | 0.9945 | 0.7708 | 0.8890 |
| r128 step01_health_guard | 0.8755 | 0.8648 | 0.9258 | 0.8917 | 0.9943 | 0.7703 | 0.8871 |
| r128 step02_event_rebuild | 0.8791 | 0.8684 | 0.9264 | 0.9027 | 0.9913 | 0.7710 | 0.8898 |
| pool_off_b16 | 0.8418 | 0.8908 | 1.0989 | 0.8690 | 1.0986 | 1.0027 | 0.9670 |
| original (pool on, batch=4) | 0.9175 | 0.8669 | 1.2221 | 1.0284 | 1.6405 | 1.0582 | 1.1222 |

## cache0001 — 相对 MR

| 配置 | alibabaBlock | metaCDN | metaKV | tencentBlock | tencentPhoto | wiki | 组平均 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| cs0001 (CMA-ES v7) | 0.8772 | 0.6849 | 0.5571 | 0.8793 | 0.8732 | 0.6603 | 0.7553 |
| step2 (step02_event_rebuild) | 0.8793 | 0.6759 | 0.5519 | 0.8836 | 0.8757 | 0.6568 | 0.7539 |
| pool_off_b16 | 0.8897 | 0.7100 | 0.5950 | 0.8847 | 0.8726 | 0.6740 | 0.7710 |
| original (pool on, batch=4) | 0.9436 | 0.6658 | 0.5700 | 0.9557 | 0.9521 | 0.6356 | 0.7872 |

## cache0001 — 相对 BMR

| 配置 | alibabaBlock | metaCDN | metaKV | tencentBlock | tencentPhoto | wiki | 组平均 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| cs0001 (CMA-ES v7) | 0.9513 | 0.9187 | 0.9630 | 0.9436 | 1.0452 | 0.9074 | 0.9549 |
| step2 (step02_event_rebuild) | 0.9671 | 0.9047 | 0.9809 | 0.9561 | 1.0500 | 0.9100 | 0.9614 |
| pool_off_b16 | 0.9543 | 0.8967 | 1.0381 | 0.9520 | 1.0345 | 0.9451 | 0.9701 |
| original (pool on, batch=4) | 0.9799 | 0.8881 | 1.2444 | 1.0020 | 1.1421 | 0.9671 | 1.0373 |
