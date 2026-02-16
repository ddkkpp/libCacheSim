# compound/softmax/sign matrix summary

说明：
- softmax 对应 `LOH_USE_SOFTMAX`（Python 端动作映射）。
- signs 对应 `LOH_USE_HEURISTIC_SIGNS`（C 端评分符号修正）。
- 注意：当 `LOH_SCORE_USE_COMPOUND=1` 时，LOH.c 中 signs 对评分不生效（可能导致 signs=0/1 结果相同）。

|trace|mode|softmax|signs|miss_ratio|byte_miss_ratio|thr_mqps|exit|run_timestamp|
|---|---|---:|---:|---:|---:|---:|---:|---|
|wiki_2019t|compound=1|0|0|0.636773|0.558983|0.0100|0|modes_cpd_soft_sign_3m_20260206_145822_wiki_2019t_001_r01|
|wiki_2019t|compound=1|0|1|0.636279|0.558764|0.0100|0|modes_cpd_soft_sign_3m_20260206_145822_wiki_2019t_002_r01|
|wiki_2019t|compound=1|1|0|0.595652|0.485654|0.0100|0|modes_cpd_soft_sign_3m_20260206_145822_wiki_2019t_003_r01|
|wiki_2019t|compound=1|1|1|0.595572|0.485684|0.0100|0|modes_cpd_soft_sign_3m_20260206_145822_wiki_2019t_004_r01|
|wiki_2019t|compound=0,irt=0|0|0|0.637266|0.560089|0.0100|0|modes_cpd_soft_sign_3m_20260206_145822_wiki_2019t_005_r01|
|wiki_2019t|compound=0,irt=0|0|1|0.636703|0.558997|0.0100|0|modes_cpd_soft_sign_3m_20260206_145822_wiki_2019t_006_r01|
|wiki_2019t|compound=0,irt=0|1|0|0.594160|0.490828|0.0100|0|modes_cpd_soft_sign_3m_20260206_145822_wiki_2019t_007_r01|
|wiki_2019t|compound=0,irt=0|1|1|0.649002|0.523133|0.0100|0|modes_cpd_soft_sign_3m_20260206_145822_wiki_2019t_008_r01|
