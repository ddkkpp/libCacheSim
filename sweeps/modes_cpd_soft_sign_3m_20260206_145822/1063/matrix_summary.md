# compound/softmax/sign matrix summary

说明：
- softmax 对应 `LOH_USE_SOFTMAX`（Python 端动作映射）。
- signs 对应 `LOH_USE_HEURISTIC_SIGNS`（C 端评分符号修正）。
- 注意：当 `LOH_SCORE_USE_COMPOUND=1` 时，LOH.c 中 signs 对评分不生效（可能导致 signs=0/1 结果相同）。

|trace|mode|softmax|signs|miss_ratio|byte_miss_ratio|thr_mqps|exit|run_timestamp|
|---|---|---:|---:|---:|---:|---:|---:|---|
|1063|compound=1|0|0|0.371348|0.354818|0.0100|0|modes_cpd_soft_sign_3m_20260206_145822_1063_001_r01|
|1063|compound=1|0|1|0.370179|0.352702|0.0100|0|modes_cpd_soft_sign_3m_20260206_145822_1063_002_r01|
|1063|compound=1|1|0|0.422620|0.401954|0.0100|0|modes_cpd_soft_sign_3m_20260206_145822_1063_003_r01|
|1063|compound=1|1|1|0.423067|0.402095|0.0100|0|modes_cpd_soft_sign_3m_20260206_145822_1063_004_r01|
|1063|compound=0,irt=0|0|0|0.365686|0.348606|0.0100|0|modes_cpd_soft_sign_3m_20260206_145822_1063_005_r01|
|1063|compound=0,irt=0|0|1|0.369175|0.351596|0.0100|0|modes_cpd_soft_sign_3m_20260206_145822_1063_006_r01|
|1063|compound=0,irt=0|1|0|0.420310|0.400529|0.0100|0|modes_cpd_soft_sign_3m_20260206_145822_1063_007_r01|
|1063|compound=0,irt=0|1|1|0.601121|0.572551|0.0100|0|modes_cpd_soft_sign_3m_20260206_145822_1063_008_r01|
