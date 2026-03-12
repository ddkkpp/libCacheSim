# LOH Penalty Runs Summary (0203+ / penalty enabled)

本文件从 0203/0204 日志中筛选 `LOH_ENABLE_PENALTY=1` 的 run，汇总 penalty 相关配置与最终 miss/byte-miss 结果。

说明：`LOH_ENABLE_PENALTY=1` 表示启用 penalty 机制（C 端编译期开关）。`LOH_REWARD_USE_PENALTY`（若出现在旧日志中）表示 reward 是否使用 penalty 项。

## Trace: data/TencentCBS/1063.oracleGeneral.zst

|run_id|req|seed|trace|cache_bytes|softmax|action_scale|log1p|irt|compound|use_pen|pen_mode|formula|dmax|cutoff|w_pen|miss|byte_miss|baseline|Δmiss|Δbyte|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|0204_020044|120000|-|data/TencentCBS/1063.oracleGeneral.zst|287582873|1|1.0|0|1|0|1|reciprocal|-|-|-|1.0|0.763875|0.755502|-|-|-|
|0204_015727|200000|-|data/TencentCBS/1063.oracleGeneral.zst|394112716|1|1.0|0|1|0|1|reciprocal|-|-|-|1.0|0.715060|0.712094|-|-|-|
|0204_300k_1063_p1_pen_default_s124|300000|124|data/TencentCBS/1063.oracleGeneral.zst|479706163|1|1.0|0|1|0|1|reciprocal|-|-|-|1.0|0.653667|0.658138|-|-|-|
|0204_300k_1063_p1_pen_log_w0p1_centered_orig1_s124|300000|124|data/TencentCBS/1063.oracleGeneral.zst|479706163|1|1.0|0|1|0|1|log|-|-|-|0.1|0.653667|0.658138|-|-|-|
|0204_diag_1063_p1_nopen_s124|300000|124|data/TencentCBS/1063.oracleGeneral.zst|479706163|1|1.0|0|1|0|0|reciprocal|-|-|-|1.0|0.653667|0.658138|0204_diag_1063_p0_s124|+0.000000|+0.000000|
|0204_095921|1000000|123|data/TencentCBS/1063.oracleGeneral.zst|1045332428|1|1.0|0|1|0|1|survival|-|-|-|0.25|0.532094|0.488547|-|-|-|
|0204_020116|3000000|-|data/TencentCBS/1063.oracleGeneral.zst|2372143206|1|1.0|0|1|0|1|reciprocal|-|-|-|0.5|0.422000|0.425132|-|-|-|
|0204_021319|3000000|-|data/TencentCBS/1063.oracleGeneral.zst|2372143206|1|1.0|0|1|0|1|reciprocal|-|-|-|0.5|0.420567|0.423393|-|-|-|
|0204_022347|3000000|123|data/TencentCBS/1063.oracleGeneral.zst|2372143206|1|1.0|0|1|0|1|reciprocal|-|-|-|0.5|0.422253|0.424503|-|-|-|
|0204_023003|3000000|123|data/TencentCBS/1063.oracleGeneral.zst|2372143206|1|1.0|0|1|0|1|log|-|-|-|0.5|0.422972|0.425097|-|-|-|
|0204_030758|3000000|123|data/TencentCBS/1063.oracleGeneral.zst|2372143206|1|1.0|0|1|0|1|survival|-|-|-|0.25|0.421375|0.422468|-|-|-|
|0204_093859|3000000|123|data/TencentCBS/1063.oracleGeneral.zst|2372143206|1|1.0|0|1|0|1|survival|-|-|-|0.25|0.421375|0.422468|-|-|-|
|0204_094504|3000000|124|data/TencentCBS/1063.oracleGeneral.zst|2372143206|1|1.0|0|1|0|1|survival|-|-|-|0.25|0.422218|0.426798|-|-|-|
|0204_095110|3000000|125|data/TencentCBS/1063.oracleGeneral.zst|2372143206|1|1.0|0|1|0|1|survival|-|-|-|0.25|0.420925|0.425681|-|-|-|
|0204_100126|3000000|123|data/TencentCBS/1063.oracleGeneral.zst|2372143206|1|1.0|0|1|0|1|survival|-|-|-|0.15|0.422489|0.427334|-|-|-|
|0204_100753|3000000|123|data/TencentCBS/1063.oracleGeneral.zst|2372143206|1|1.0|0|1|0|1|survival|-|-|-|0.25|0.422016|0.423593|-|-|-|
|0204_101659|3000000|124|data/TencentCBS/1063.oracleGeneral.zst|2372143206|1|1.0|0|1|0|1|survival|-|-|-|0.25|0.421930|0.426449|-|-|-|
|0204_102313|3000000|124|data/TencentCBS/1063.oracleGeneral.zst|2372143206|1|1.0|0|1|0|1|survival|-|-|-|0.10|0.421877|0.426494|-|-|-|
|0204_102923|3000000|124|data/TencentCBS/1063.oracleGeneral.zst|2372143206|1|1.0|0|1|0|1|log|-|-|-|0.25|0.422108|0.427497|-|-|-|
|0204_103522|3000000|124|data/TencentCBS/1063.oracleGeneral.zst|2372143206|1|1.0|0|1|0|0|reciprocal|-|-|-|1.0|0.421983|0.427308|-|-|-|
|0204_3m_1063_p1_nopen_s124|3000000|124|data/TencentCBS/1063.oracleGeneral.zst|2372143206|1|1.0|0|1|0|0|reciprocal|-|-|-|1.0|0.437175|0.445586|0204_3m_1063_p0_s124|+0.000000|+0.000000|
|0204_3m_1063_p1_pen_log_neg_w1_orig1_s124|3000000|124|data/TencentCBS/1063.oracleGeneral.zst|2372143206|1|1.0|0|1|0|1|log|-|-|-|1.0|0.439322|0.448582|0204_3m_1063_p0_s124|+0.002147|+0.002996|
|0204_3m_1063_p1_pen_w0p2_centered_s124|3000000|124|data/TencentCBS/1063.oracleGeneral.zst|2372143206|1|1.0|0|1|0|1|reciprocal|-|-|-|0.2|0.438128|0.448102|0204_3m_1063_p0_s124|+0.000953|+0.002516|

## Notes

- `baseline`：仅在能找到同 trace 且同 `req` 的 `_p0_` 对照日志时填写；否则为 `-`。
- `dmax/cutoff`：优先从文件名推断（仅对少数命名包含这些字段的 run 有值）。
