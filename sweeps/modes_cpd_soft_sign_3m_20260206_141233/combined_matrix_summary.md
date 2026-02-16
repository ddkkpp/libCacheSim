# compound/softmax/sign matrix summary

说明：
- softmax 对应 `LOH_USE_SOFTMAX`（Python 端动作映射）。
- signs 对应 `LOH_USE_HEURISTIC_SIGNS`（C 端评分符号修正）。
- 注意：当 `LOH_SCORE_USE_COMPOUND=1` 时，LOH.c 中 signs 对评分不生效（可能导致 signs=0/1 结果相同）。

|trace|mode|softmax|signs|miss_ratio|byte_miss_ratio|thr_mqps|exit|run_timestamp|
|---|---|---:|---:|---:|---:|---:|---:|---|
|meta_reag|compound=1|0|0|0.484770|0.259536|0.0400|0|modes_cpd_soft_sign_3m_20260206_141233_meta_reag_001_r01|
|meta_reag|compound=1|0|1|0.477940|0.250750|0.0400|0|modes_cpd_soft_sign_3m_20260206_141233_meta_reag_002_r01|
|meta_reag|compound=1|1|0|0.428420|0.210814|0.0700|0|modes_cpd_soft_sign_3m_20260206_141233_meta_reag_003_r01|
|meta_reag|compound=1|1|1|0.428420|0.211707|0.0700|0|modes_cpd_soft_sign_3m_20260206_141233_meta_reag_004_r01|
|meta_reag|compound=0,irt=0|0|0|0.464950|0.252850|0.0400|0|modes_cpd_soft_sign_3m_20260206_141233_meta_reag_005_r01|
|meta_reag|compound=0,irt=0|0|1|0.466605|0.259354|0.0400|0|modes_cpd_soft_sign_3m_20260206_141233_meta_reag_006_r01|
|meta_reag|compound=0,irt=0|1|0|0.428895|0.212448|0.0700|0|modes_cpd_soft_sign_3m_20260206_141233_meta_reag_007_r01|
|meta_reag|compound=0,irt=0|1|1|0.514100|0.263745|0.0300|0|modes_cpd_soft_sign_3m_20260206_141233_meta_reag_008_r01|
