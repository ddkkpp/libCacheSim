# compound/softmax/sign matrix summary

说明：
- softmax 对应 `LOH_USE_SOFTMAX`（Python 端动作映射）。
- signs 对应 `LOH_USE_HEURISTIC_SIGNS`（C 端评分符号修正）。
- 注意：当 `LOH_SCORE_USE_COMPOUND=1` 时，LOH.c 中 signs 对评分不生效（可能导致 signs=0/1 结果相同）。

|trace|mode|softmax|signs|miss_ratio|byte_miss_ratio|thr_mqps|exit|run_timestamp|
|---|---|---:|---:|---:|---:|---:|---:|---|
|meta_reag|compound=1|0|0|0.397913|0.244240|0.0100|0|modes_cpd_soft_sign_3m_20260206_145822_meta_reag_001_r01|
|meta_reag|compound=1|0|1|0.398412|0.241391|0.0100|0|modes_cpd_soft_sign_3m_20260206_145822_meta_reag_002_r01|
|meta_reag|compound=1|1|0|0.368247|0.225172|0.0100|0|modes_cpd_soft_sign_3m_20260206_145822_meta_reag_003_r01|
|meta_reag|compound=1|1|1|0.368286|0.225248|0.0100|0|modes_cpd_soft_sign_3m_20260206_145822_meta_reag_004_r01|
|meta_reag|compound=0,irt=0|0|0|0.400891|0.240756|0.0100|0|modes_cpd_soft_sign_3m_20260206_145822_meta_reag_005_r01|
|meta_reag|compound=0,irt=0|0|1|0.395534|0.238370|0.0100|0|modes_cpd_soft_sign_3m_20260206_145822_meta_reag_006_r01|
|meta_reag|compound=0,irt=0|1|0|0.368942|0.225700|0.0100|0|modes_cpd_soft_sign_3m_20260206_145822_meta_reag_007_r01|
|meta_reag|compound=0,irt=0|1|1|0.425637|0.262699|0.0100|0|modes_cpd_soft_sign_3m_20260206_145822_meta_reag_008_r01|
