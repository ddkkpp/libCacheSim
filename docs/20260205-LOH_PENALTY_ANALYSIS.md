# LOH penalty runs 汇总（无Δ，仅配置+结果 / 自动生成）

总计 penalty-enabled runs = **33**（去重 run_id = **29**）
- penalty_0203_plus: 20
- tested_summary: 13

## 全量明细

|src|date|trace|miss|byte_miss|req|run|pen|w_pen|formula|r_use_pen|penonly|seed|cfg|
|---|---|---|---:|---:|---:|---|---|---:|---|---:|---:|---:|---|
|ts|0205|meta_reag|0.384826|0.239493|3M|meta_reag_stat…5_112015|1|2.0|net|-|-|-|SAC linear irt=1 cpd=0 state=2 pen=1<br>formula=net w_pen=2.0|
|ts|0106|1063|0.437083|0.443746|6|sweep_20260106_153622|survival|-|-|-|-|-|SAC pen=survival|
|ts|0204|1063|0.653667|0.658138|300k|0204_300k_1063…ult_s124|1|-|-|-|-|124|SAC irt=1 cpd=0 state=2 signs=1 pen=1<br>seed=124|
|ts|0204|1063|0.653667|0.658138|300k|0204_300k_1063…ig1_s124|1|-|-|-|-|124|SAC irt=1 cpd=0 state=2 signs=1 pen=1<br>seed=124|
|ts|0204|1063|0.653667|0.658138|300k|0204_diag_1063…pen_s124|1|-|-|-|-|124|SAC irt=1 cpd=0 state=2 signs=1 pen=1<br>seed=124 diag|
|ts|0204|1063|0.437175|0.445586|3M|0204_3m_1063_p…pen_s124|1|-|-|0|-|124|SAC softmax irt=1 cpd=0 state=2 pen=1<br>r_use_pen=0 seed=124|
|ts|0204|1063|0.439322|0.448582|3M|0204_3m_1063_p…ig1_s124|log|1.0|-|1|-|124|SAC softmax irt=1 cpd=0 state=2 pen=1<br>r_use_pen=1 w_pen=1.0 pen=log seed=124|
|ts|0204|1063|0.438128|0.448102|3M|0204_3m_1063_p…red_s124|reciprocal|0.2|-|1|-|124|SAC softmax irt=1 cpd=0 state=2 pen=1<br>r_use_pen=1 w_pen=0.2 pen=reciprocal seed=124|
|ts|0205|1063|0.366161|0.349840|3M|1063_state2_no…5_114946|1|1.0|net2|-|1|-|SAC linear irt=1 cpd=0 state=2 pen=1<br>formula=net2 w_pen=1.0 penonly=1|
|ts|0205|1063|0.363873|0.348989|3M|1063_state2_no…5_111352|1|2.0|net|-|-|-|SAC linear irt=1 cpd=0 state=2 pen=1<br>formula=net w_pen=2.0|
|ts|0205|1063|0.371462|0.352522|3M|1063_state2_no…5_152627|1|3.0|net|-|-|-|SAC linear irt=1 cpd=0 state=2 pen=1<br>formula=net w_pen=3.0|
|ts|0205|wiki_2019t|0.637197|0.559970|3M|wiki_2019t_sta…5_113957|1|2.0|net(v2)|-|-|-|SAC linear irt=1 cpd=0 state=2 pen=1<br>formula=net(v2) w_pen=2.0|
|ts|0205|wiki_2019t|0.636374|0.560580|3M|wiki_2019t_sta…5_112839|1|2.0|net|-|-|-|SAC linear irt=1 cpd=0 state=2 pen=1<br>formula=net w_pen=2.0|
|p0203|-|1063.oracleGeneral|0.763875|0.755502|120k|0204_020044|reciprocal|1.0|-|1|-|-|SAC softmax irt=1 cpd=0 pen=1 r_use_pen=1<br>pen=reciprocal w_pen=1.0 formula=-|
|p0203|-|1063.oracleGeneral|0.715060|0.712094|200k|0204_015727|reciprocal|1.0|-|1|-|-|SAC softmax irt=1 cpd=0 pen=1 r_use_pen=1<br>pen=reciprocal w_pen=1.0 formula=-|
|p0203|-|1063.oracleGeneral|0.653667|0.658138|300k|0204_300k_1063…ult_s124|reciprocal|1.0|-|1|-|124|SAC softmax irt=1 cpd=0 pen=1 r_use_pen=1<br>pen=reciprocal w_pen=1.0 formula=- seed=124|
|p0203|-|1063.oracleGeneral|0.653667|0.658138|300k|0204_300k_1063…ig1_s124|log|0.1|-|1|-|124|SAC softmax irt=1 cpd=0 pen=1 r_use_pen=1<br>pen=log w_pen=0.1 formula=- seed=124|
|p0203|-|1063.oracleGeneral|0.532094|0.488547|1M|0204_095921|survival|0.25|-|1|-|123|SAC softmax irt=1 cpd=0 pen=1 r_use_pen=1<br>pen=survival w_pen=0.25 formula=- seed=123|
|p0203|-|1063.oracleGeneral|0.422000|0.425132|3M|0204_020116|reciprocal|0.5|-|1|-|-|SAC softmax irt=1 cpd=0 pen=1 r_use_pen=1<br>pen=reciprocal w_pen=0.5 formula=-|
|p0203|-|1063.oracleGeneral|0.420567|0.423393|3M|0204_021319|reciprocal|0.5|-|1|-|-|SAC softmax irt=1 cpd=0 pen=1 r_use_pen=1<br>pen=reciprocal w_pen=0.5 formula=-|
|p0203|-|1063.oracleGeneral|0.422253|0.424503|3M|0204_022347|reciprocal|0.5|-|1|-|123|SAC softmax irt=1 cpd=0 pen=1 r_use_pen=1<br>pen=reciprocal w_pen=0.5 formula=- seed=123|
|p0203|-|1063.oracleGeneral|0.422972|0.425097|3M|0204_023003|log|0.5|-|1|-|123|SAC softmax irt=1 cpd=0 pen=1 r_use_pen=1<br>pen=log w_pen=0.5 formula=- seed=123|
|p0203|-|1063.oracleGeneral|0.421375|0.422468|3M|0204_030758|survival|0.25|-|1|-|123|SAC softmax irt=1 cpd=0 pen=1 r_use_pen=1<br>pen=survival w_pen=0.25 formula=- seed=123|
|p0203|-|1063.oracleGeneral|0.421375|0.422468|3M|0204_093859|survival|0.25|-|1|-|123|SAC softmax irt=1 cpd=0 pen=1 r_use_pen=1<br>pen=survival w_pen=0.25 formula=- seed=123|
|p0203|-|1063.oracleGeneral|0.422218|0.426798|3M|0204_094504|survival|0.25|-|1|-|124|SAC softmax irt=1 cpd=0 pen=1 r_use_pen=1<br>pen=survival w_pen=0.25 formula=- seed=124|
|p0203|-|1063.oracleGeneral|0.420925|0.425681|3M|0204_095110|survival|0.25|-|1|-|125|SAC softmax irt=1 cpd=0 pen=1 r_use_pen=1<br>pen=survival w_pen=0.25 formula=- seed=125|
|p0203|-|1063.oracleGeneral|0.422489|0.427334|3M|0204_100126|survival|0.15|-|1|-|123|SAC softmax irt=1 cpd=0 pen=1 r_use_pen=1<br>pen=survival w_pen=0.15 formula=- seed=123|
|p0203|-|1063.oracleGeneral|0.422016|0.423593|3M|0204_100753|survival|0.25|-|1|-|123|SAC softmax irt=1 cpd=0 pen=1 r_use_pen=1<br>pen=survival w_pen=0.25 formula=- seed=123|
|p0203|-|1063.oracleGeneral|0.421930|0.426449|3M|0204_101659|survival|0.25|-|1|-|124|SAC softmax irt=1 cpd=0 pen=1 r_use_pen=1<br>pen=survival w_pen=0.25 formula=- seed=124|
|p0203|-|1063.oracleGeneral|0.421877|0.426494|3M|0204_102313|survival|0.1|-|1|-|124|SAC softmax irt=1 cpd=0 pen=1 r_use_pen=1<br>pen=survival w_pen=0.1 formula=- seed=124|
|p0203|-|1063.oracleGeneral|0.422108|0.427497|3M|0204_102923|log|0.25|-|1|-|124|SAC softmax irt=1 cpd=0 pen=1 r_use_pen=1<br>pen=log w_pen=0.25 formula=- seed=124|
|p0203|-|1063.oracleGeneral|0.439322|0.448582|3M|0204_3m_1063_p…ig1_s124|log|1.0|-|1|-|124|SAC softmax irt=1 cpd=0 pen=1 r_use_pen=1<br>pen=log w_pen=1.0 formula=- seed=124|
|p0203|-|1063.oracleGeneral|0.438128|0.448102|3M|0204_3m_1063_p…red_s124|reciprocal|0.2|-|1|-|124|SAC softmax irt=1 cpd=0 pen=1 r_use_pen=1<br>pen=reciprocal w_pen=0.2 formula=- seed=124|

## 重点子集：formula=net/net2 且 w_pen=2/3

匹配到 runs = **5**

|date|trace|req|miss|byte_miss|run|pen|w_pen|formula|cfg|
|---|---|---:|---:|---:|---|---|---:|---|---|
|0205|meta_reag|3M|0.384826|0.239493|meta_reag_stat…5_112015|1|2.0|net|SAC linear irt=1 cpd=0 state=2 pen=1<br>formula=net w_pen=2.0|
|0205|1063|3M|0.363873|0.348989|1063_state2_no…5_111352|1|2.0|net|SAC linear irt=1 cpd=0 state=2 pen=1<br>formula=net w_pen=2.0|
|0205|1063|3M|0.371462|0.352522|1063_state2_no…5_152627|1|3.0|net|SAC linear irt=1 cpd=0 state=2 pen=1<br>formula=net w_pen=3.0|
|0205|wiki_2019t|3M|0.637197|0.559970|wiki_2019t_sta…5_113957|1|2.0|net(v2)|SAC linear irt=1 cpd=0 state=2 pen=1<br>formula=net(v2) w_pen=2.0|
|0205|wiki_2019t|3M|0.636374|0.560580|wiki_2019t_sta…5_112839|1|2.0|net|SAC linear irt=1 cpd=0 state=2 pen=1<br>formula=net w_pen=2.0|

## baseline 对齐检查（忽略 seed + 把 formula/penonly 视为 penalty 相关）

口径：对 cfg 生成 relaxed signature，移除 `pen/w_pen/r_use_pen/penonly/formula/seed` 后对齐；另外忽略 `posnet`（视为标签）；其余开关（如 softmax/linear、irt/cpd/state、diag/signs 等）必须一致。

tested_summary 中：penalty 行数 = **13**，baseline 行数 = **413**；缺少 baseline 的去重签名数 = **2**

### 其它配置是否统一？（仅 req=3000000；按 trace+req 统计 penalty 的 signature 种类数）

|trace|req|penalty_signatures|
|---|---:|---:|
|1063|3M|2|
|meta_reag|3M|1|
|wiki_2019t|3M|1|

说明：`n_penalty` = 在 tested_summary 中，命中该签名的 penalty 行数（同一签名下可能有多条 penalty 配置/不同 w_pen/formula）。

### 缺少 baseline 的签名（仅 req=3000000；按 trace 去重后最小补跑集合）

|trace|req|n_penalty|example_penalty_run|signature(relaxed)|example_penalty_cfg|
|---|---:|---:|---|---|---|
|wiki_2019t|3M|2|wiki_2019t_sta…5_112839|SAC linear cpd=0 irt=1 state=2|SAC linear irt=1 cpd=0 state=2 pen=1<br>formula=net w_pen=2.0|
