# LOH trace 特征偏好（从 analysis 推断）
说明：w1..w6 = recency / frequency / size / irt1 / irt2 / irt3（见 LOH.c FEATURE_DIM 注释）。
本报告基于 analysis 的聚合统计（summary.json、reqRate_w300、reuse histogram），给出可复现的启发式建议，不等价于最优解。
## 1063.oracleGeneral.zst
**概况**
- trace_type=block
- total_req=360,960,512, total_obj=1,157,471, zipf_alpha=0.698
- stationarity_labels: distribution=weak, identity=weak, size=unstable
- topk(top1/top10/top100/top1pct)=0.0035/0.0303/0.0909/0.3157
**reqRate_w300（300s 窗口）**
- req_mean=461.56, req_cv=0.724, p50/p90/p99=403/904/1009, zero_frac=0.008, mean|Δreq|=136.13
- bytes/req mean=55734.45, cv=0.260, p50/p90=60582.48/67516.94; cold_obj_ratio mean=0.007, p90=0.005
**reuse（复用间隔，granularity=5）**
- reuse_p50/p90/p99=2.1m / 13.8m / 6.04h (spread_log=5.151)
- reuse share: <=1h=0.951, 1h-1d=0.048, >1d=0.001, <=7d=1.000
**建议权重（归一化，w1..w6）**
- w=[0.501, 0.193, 0.016, 0.169, 0.077, 0.044]

## meta_reag.oracleGeneral.zst
**概况**
- trace_type=object
- total_req=45,623,306, total_obj=12,262,537, zipf_alpha=0.714
- stationarity_labels: distribution=unstable, identity=unstable, size=unstable
- topk(top1/top10/top100/top1pct)=0.2439/0.2609/0.2956/0.5114
**reqRate_w300（300s 窗口）**
- req_mean=65.51, req_cv=0.246, p50/p90/p99=61/83/107, zero_frac=0.000, mean|Δreq|=3.90
- bytes/req mean=27948341.82, cv=0.628, p50/p90=23480172.15/48338859.83; cold_obj_ratio mean=0.576, p90=0.676
**reuse（复用间隔，granularity=5）**
- reuse_p50/p90/p99=10s / 17.0m / 2.73d (spread_log=9.973)
- reuse share: <=1h=0.918, 1h-1d=0.053, >1d=0.029, <=7d=1.000
**建议权重（归一化，w1..w6）**
- w=[0.223, 0.226, 0.314, 0.135, 0.063, 0.040]

## wiki_2019t.oracleGeneral.zst
**概况**
- trace_type=object
- total_req=207,646,002, total_obj=18,394,481, zipf_alpha=1.238
- stationarity_labels: distribution=weak, identity=unstable, size=weak
- topk(top1/top10/top100/top1pct)=0.0047/0.0141/0.0320/0.5552
**reqRate_w300（300s 窗口）**
- req_mean=113.95, req_cv=0.359, p50/p90/p99=121/163/201, zero_frac=0.000, mean|Δreq|=2.53
- bytes/req mean=33535.07, cv=0.066, p50/p90=33746.85/36305.03; cold_obj_ratio mean=0.104, p90=0.173
**reuse（复用间隔，granularity=5）**
- reuse_p50/p90/p99=3.0m / 7.96h / 5.40d (spread_log=7.854)
- reuse share: <=1h=0.786, 1h-1d=0.163, >1d=0.052, <=7d=0.994
**建议权重（归一化，w1..w6）**
- w=[0.165, 0.528, 0.000, 0.160, 0.091, 0.056]

