# LOH penalty 参数效果分析（自动生成）

统计样本：可对齐 baseline 的 penalty runs = **6**

## 整体最优（按 Δmiss 排序，Top 6）

|trace|req|run_id|baseline|baseline_miss|baseline_byte|Δmiss|Δbyte|pen|w_pen|formula|r_use_pen|penonly|cfg|
|---|---:|---|---|---:|---:|---:|---:|---|---:|---|---:|---:|---|
|TencentCBS/1063|300000|0204_300k_1063_p1_pen_default_s124|0205_1063_newp_ex200_s124|0.740193|0.727933|-0.086526|-0.069795|1|-|-|-|-|SAC irt=1 cpd=0 state=2 signs=1 pen=1 seed=124|
|TencentCBS/1063|300000|0204_300k_1063_p1_pen_log_w0p1_centered_orig1_s124|0205_1063_newp_ex200_s124|0.740193|0.727933|-0.086526|-0.069795|1|-|-|-|-|SAC irt=1 cpd=0 state=2 signs=1 pen=1 seed=124|
|TencentCBS/1063|300000|0204_diag_1063_p1_nopen_s124|0204_diag_1063_p0_s124|0.653667|0.658138|+0.000000|+0.000000|1|-|-|-|-|SAC irt=1 cpd=0 state=2 signs=1 pen=1 seed=124 diag|
|TencentCBS/1063|3000000|0204_3m_1063_p1_nopen_s124|0204_3m_1063_p0_s124|0.437175|0.445586|+0.000000|+0.000000|1|-|-|0|-|SAC softmax irt=1 cpd=0 state=2 pen=1 r_use_pen=0 seed=124|
|TencentCBS/1063|3000000|0204_3m_1063_p1_pen_w0p2_centered_s124|0204_3m_1063_p0_s124|0.437175|0.445586|+0.000953|+0.002516|reciprocal|0.2|-|1|-|SAC softmax irt=1 cpd=0 state=2 pen=1 r_use_pen=1 w_pen=0.2 pen=reciprocal seed=124|
|TencentCBS/1063|3000000|0204_3m_1063_p1_pen_log_neg_w1_orig1_s124|0204_3m_1063_p0_s124|0.437175|0.445586|+0.002147|+0.002996|log|1.0|-|1|-|SAC softmax irt=1 cpd=0 state=2 pen=1 r_use_pen=1 w_pen=1.0 pen=log seed=124|

## 整体最差（按 Δmiss 排序，Bottom 6）

|trace|req|run_id|baseline|baseline_miss|baseline_byte|Δmiss|Δbyte|pen|w_pen|formula|r_use_pen|penonly|cfg|
|---|---:|---|---|---:|---:|---:|---:|---|---:|---|---:|---:|---|
|TencentCBS/1063|3000000|0204_3m_1063_p1_pen_log_neg_w1_orig1_s124|0204_3m_1063_p0_s124|0.437175|0.445586|+0.002147|+0.002996|log|1.0|-|1|-|SAC softmax irt=1 cpd=0 state=2 pen=1 r_use_pen=1 w_pen=1.0 pen=log seed=124|
|TencentCBS/1063|3000000|0204_3m_1063_p1_pen_w0p2_centered_s124|0204_3m_1063_p0_s124|0.437175|0.445586|+0.000953|+0.002516|reciprocal|0.2|-|1|-|SAC softmax irt=1 cpd=0 state=2 pen=1 r_use_pen=1 w_pen=0.2 pen=reciprocal seed=124|
|TencentCBS/1063|3000000|0204_3m_1063_p1_nopen_s124|0204_3m_1063_p0_s124|0.437175|0.445586|+0.000000|+0.000000|1|-|-|0|-|SAC softmax irt=1 cpd=0 state=2 pen=1 r_use_pen=0 seed=124|
|TencentCBS/1063|300000|0204_diag_1063_p1_nopen_s124|0204_diag_1063_p0_s124|0.653667|0.658138|+0.000000|+0.000000|1|-|-|-|-|SAC irt=1 cpd=0 state=2 signs=1 pen=1 seed=124 diag|
|TencentCBS/1063|300000|0204_300k_1063_p1_pen_log_w0p1_centered_orig1_s124|0205_1063_newp_ex200_s124|0.740193|0.727933|-0.086526|-0.069795|1|-|-|-|-|SAC irt=1 cpd=0 state=2 signs=1 pen=1 seed=124|
|TencentCBS/1063|300000|0204_300k_1063_p1_pen_default_s124|0205_1063_newp_ex200_s124|0.740193|0.727933|-0.086526|-0.069795|1|-|-|-|-|SAC irt=1 cpd=0 state=2 signs=1 pen=1 seed=124|

## 每个 trace+req 的最优 penalty 配置

|trace|req|best_run|baseline|Δmiss|Δbyte|pen|w_pen|formula|cfg|
|---|---:|---|---|---:|---:|---|---:|---|---|
|TencentCBS/1063|300000|0204_300k_1063_p1_pen_default_s124|0205_1063_newp_ex200_s124|-0.086526|-0.069795|1|-|-|SAC irt=1 cpd=0 state=2 signs=1 pen=1 seed=124|
|TencentCBS/1063|3000000|0204_3m_1063_p1_nopen_s124|0204_3m_1063_p0_s124|+0.000000|+0.000000|1|-|-|SAC softmax irt=1 cpd=0 state=2 pen=1 r_use_pen=0 seed=124|

## 参数组合的平均效果（按 Δmiss 均值排序）

|pen|w_pen|formula|n|avg_Δmiss|avg_Δbyte|
|---|---:|---|---:|---:|---:|
|1|-|-|4|-0.043263|-0.034898|
|reciprocal|0.2|-|1|+0.000953|+0.002516|
|log|1.0|-|1|+0.002147|+0.002996|

