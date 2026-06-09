# Cache01 Precise Throughput Summary

Throughput uses n_req / runtime / 1e6 when runtime is available; if an exact MR/BMR match has no runtime, it falls back to that line's MQPS text.
`mean_mqps` is computed by averaging each algorithm within every group first, then averaging those group means.

## Coverage

- trace universe: 5768
- included groups: tencentPhoto, metaKV, wiki, metaCDN, alibabaBlock, tencentBlock
- excluded groups: cloudphysics
- repaired traces: tencent_photo1, tencent_photo2, wiki_2016u, wiki_2019t
- drl-v7-omr-cache01 throughput coverage: 5768/5768
- drl-v7-bmr-cache01 throughput coverage: 5768/5768

## Repair Notes

- repaired_exact_drl_v7_omr_result: 2
- repaired_exact_throughput_source: 3
- repaired_imputed_group_algorithm_mean_no_exact_runtime_source: 18

## Source Verification

- baseline-ARC: mqps_fallback=5765; ok=1; repaired_imputed_group_algorithm_mean=2
- baseline-Cacheus: mqps_fallback=5765; ok=1; repaired_imputed_group_algorithm_mean=2
- baseline-GDSF: mqps_fallback=5765; ok=1; repaired_exact_throughput_source=1; repaired_imputed_group_algorithm_mean=1
- baseline-GLCache: mqps_fallback=5765; ok=1; repaired_imputed_group_algorithm_mean=2
- baseline-LHD: mqps_fallback=5765; ok=1; repaired_imputed_group_algorithm_mean=2
- baseline-LRB-BMR: mqps_fallback=5389; ok=378; repaired_imputed_group_algorithm_mean=1
- baseline-LRU: mqps_fallback=5765; ok=1; repaired_exact_throughput_source=1; repaired_imputed_group_algorithm_mean=1
- baseline-LeCaR: mqps_fallback=1708; ok=4058; repaired_imputed_group_algorithm_mean=2
- baseline-S3FIFO-0.1000-2: mqps_fallback=5764; ok=2; repaired_exact_throughput_source=1; repaired_imputed_group_algorithm_mean=1
- baseline-Sieve: mqps_fallback=5765; ok=1; repaired_imputed_group_algorithm_mean=2
- baseline-ThreeLCache-BMR: mqps_fallback=404; ok=5364
- baseline-ThreeLCache-OMR: mqps_fallback=410; ok=5358
- baseline-WTinyLFU-w0.01-SLRU: mqps_fallback=5766; repaired_imputed_group_algorithm_mean=2
- cmaes-v7-bmr-runtime: mqps_fallback=22; ok=5746
- cmaes-v7-bmr-source: historical_source_missing_use_raw_result=3742; ok=2026
- cmaes-v7-omr-runtime: mqps_fallback=23; ok=5745
- cmaes-v7-omr-source: historical_source_missing_use_raw_result=5768
- drl-v7-bmr-runtime: mqps_fallback=19; ok=5749
- drl-v7-omr-runtime: mqps_fallback=19; ok=5747; repaired_exact_drl_v7_omr_result=2

## Throughput Stats

| algorithm | coverage | mean_mqps | p05_mqps | p25_mqps | p50_mqps | p75_mqps | p95_mqps | p100_mqps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| drl-v7-omr-cache01 | 5768/5768 | 0.252716 | 0.018949 | 0.042679 | 0.075842 | 0.147504 | 0.426050 | 3.055480 |
| drl-v7-bmr-cache01 | 5768/5768 | 0.257548 | 0.035667 | 0.072214 | 0.119712 | 0.204519 | 0.518368 | 2.982731 |
| cmaes-v7-omr-cache01 | 5768/5768 | 0.565628 | 0.073919 | 0.180381 | 0.304874 | 0.489321 | 0.994315 | 4.546645 |
| cmaes-v7-bmr-cache01 | 5768/5768 | 0.498864 | 0.082732 | 0.157947 | 0.239102 | 0.393871 | 0.767155 | 6.986397 |
| ARC | 5768/5768 | 3.169661 | 2.580000 | 3.730000 | 4.880000 | 6.760000 | 9.720000 | 19.430000 |
| Cacheus | 5768/5768 | 1.004066 | 0.710000 | 1.100000 | 1.490000 | 2.050000 | 3.230000 | 7.180000 |
| GDSF | 5768/5768 | 0.661977 | 0.593500 | 0.930000 | 1.230000 | 1.780000 | 2.780000 | 6.320000 |
| GLCache | 5768/5768 | 2.128117 | 1.640000 | 2.380000 | 3.110000 | 4.342500 | 6.480000 | 17.750000 |
| LHD | 5768/5768 | 1.300445 | 0.803500 | 1.210000 | 1.755000 | 2.700000 | 4.530000 | 9.650000 |
| LRU | 5768/5768 | 3.418232 | 2.760000 | 3.890000 | 5.140000 | 7.232500 | 10.446500 | 19.480000 |
| LeCaR | 5768/5768 | 1.623791 | 0.399657 | 0.436940 | 0.479994 | 3.850000 | 6.456500 | 14.755149 |
| S3FIFO-0.1000-2 | 5768/5768 | 2.181174 | 1.450000 | 2.240000 | 3.060000 | 4.412500 | 7.106500 | 17.050000 |
| Sieve | 5768/5768 | 3.625149 | 2.803500 | 3.990000 | 5.230000 | 7.380000 | 10.790000 | 20.650000 |
| WTinyLFU-w0.01-SLRU | 5768/5768 | 1.538113 | 0.780000 | 1.420000 | 2.020000 | 2.720000 | 4.396500 | 13.310000 |
| LRB-BMR | 5768/5768 | 0.097387 | 0.010000 | 0.020000 | 0.030000 | 0.050000 | 0.960000 | 2.480000 |
| ThreeLCache-BMR | 5768/5768 | 0.868565 | 0.547831 | 0.809400 | 1.047314 | 1.509888 | 2.790000 | 8.341320 |
| ThreeLCache-OMR | 5768/5768 | 0.768009 | 0.640184 | 0.869924 | 1.111390 | 1.557100 | 2.950081 | 8.341320 |

## CMAES v7 Selection And Source Audit

- CMAES result-dir source rows: 1624
- cmaes-v7-bmr-cache01 selected_cfg=f100_ns: 2026
- cmaes-v7-bmr-cache01 selected_cfg=f101_orig: 3742
- cmaes-v7-omr-cache01 selected_cfg=f001_orig: 5768
