# Sync Interval CMA-ES Ablation (Grid)

格式：<Relative-to-LRU(MR), Relative-to-LRU(BMR), MQPS_avg, CPU-sec/MReq_avg>

## cache01

| sync_interval | value |
|---|---|
| 100 | <0.735850, 0.894033, 0.313, 4.138> |
| 250 | <0.739614, 0.896181, 0.374, 3.382> |
| 1000 | <0.739590, 0.894319, 0.379, 2.905> |
| 2000 | <0.785295, nan, 0.370, 2.535><br>incomplete: MR 3281/5768; BMR 0/5768 |

## cache0001

| sync_interval | value |
|---|---|
| 100 | <0.894530, 0.959962, 0.321, 8.339> |
| 250 | <0.892245, 0.960232, 0.376, 6.949> |
| 1000 | <0.878404, 0.957455, 0.411, 5.866> |
| 2000 | <nan, nan, nan, nan><br>incomplete: MR 0/5768; BMR 0/5768 |

## Combined Average (cache01 + cache0001)

| sync_interval | value |
|---|---|
| 100 | <0.815190, 0.926997, 0.317, 6.238> |
| 250 | <0.815929, 0.928206, 0.375, 5.166> |
| 1000 | <0.808997, 0.925887, 0.395, 4.385> |
| 2000 | <0.785295, nan, 0.370, 2.535><br>incomplete: cache01 MR 3281/5768; cache01 BMR 0/5768; cache0001 MR 0/5768; cache0001 BMR 0/5768 |

## Score/Throughput Average (cache01 + cache0001)

格式：<((Relative-to-LRU(MR)_avg + Relative-to-LRU(BMR)_avg) / 2), MQPS_avg>

| sync_interval | value |
|---|---|
| 100 | <0.871094, 0.316937> |
| 250 | <0.872068, 0.375270> |
| 500 | <0.867251, 0.305245><br>source: tmp/20260524-candidate-budget-cmaes-ablation/summary_grid.md, Score/Throughput Average -> s16 Across r -> r=256 |
| 1000 | <0.867442, 0.395142> |
| 2000 | <0.785295, 0.370323><br>incomplete: cache01 MR 3281/5768; cache01 BMR 0/5768; cache0001 MR 0/5768; cache0001 BMR 0/5768 |

## Score Trend (100 / 250 / 500 / 1000)

格式：((Relative-to-LRU(MR)_avg + Relative-to-LRU(BMR)_avg) / 2)

| sync_interval | score |
|---|---|
| 100 | 0.873094 |
| 250 | 0.872068 |
| 500 | 0.867251 |
| 1000 | 0.867442 |

折线图: [sync_interval_score_trend.pdf](sync_interval_score_trend.pdf)
