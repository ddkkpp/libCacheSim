# Cache01 Precise Throughput Summary

Throughput uses n_req / runtime / 1e6 when runtime is available; if an exact MR/BMR match has no runtime, it falls back to that line's MQPS text.
`mean_mqps` is computed by averaging each algorithm within every group first, then averaging those group means.

## Coverage

- trace universe: 5874
- included groups: tencentPhoto, metaKV, wiki, metaCDN, alibabaBlock, tencentBlock, cloudphysics
- repaired traces: tencent_photo1, tencent_photo2, wiki_2016u, wiki_2019t
- drl-v7-omr-cache01 throughput coverage: 5874/5874
- drl-v7-bmr-cache01 throughput coverage: 5874/5874

## Repair Notes

- repaired_exact_drl_v7_omr_result: 2
- repaired_exact_throughput_source: 3
- repaired_imputed_group_algorithm_mean_no_exact_runtime_source: 18

## Source Verification

- baseline-ARC: mqps_fallback=5871; ok=1; repaired_imputed_group_algorithm_mean=2
- baseline-Cacheus: mqps_fallback=5871; ok=1; repaired_imputed_group_algorithm_mean=2
- baseline-GDSF: mqps_fallback=5871; ok=1; repaired_exact_throughput_source=1; repaired_imputed_group_algorithm_mean=1
- baseline-GLCache: mqps_fallback=5871; ok=1; repaired_imputed_group_algorithm_mean=2
- baseline-LHD: mqps_fallback=5871; ok=1; repaired_imputed_group_algorithm_mean=2
- baseline-LRB-BMR: mqps_fallback=5495; ok=378; repaired_imputed_group_algorithm_mean=1
- baseline-LRU: mqps_fallback=5871; ok=1; repaired_exact_throughput_source=1; repaired_imputed_group_algorithm_mean=1
- baseline-LeCaR: mqps_fallback=1814; ok=4058; repaired_imputed_group_algorithm_mean=2
- baseline-S3FIFO-0.1000-2: mqps_fallback=5870; ok=2; repaired_exact_throughput_source=1; repaired_imputed_group_algorithm_mean=1
- baseline-Sieve: mqps_fallback=5871; ok=1; repaired_imputed_group_algorithm_mean=2
- baseline-ThreeLCache-BMR: mqps_fallback=404; ok=5470
- baseline-ThreeLCache-OMR: mqps_fallback=410; ok=5464
- baseline-WTinyLFU-w0.01-SLRU: mqps_fallback=5872; repaired_imputed_group_algorithm_mean=2
- cmaes-v7-bmr-runtime: mqps_fallback=79; ok=5795
- cmaes-v7-bmr-source: historical_source_missing_use_raw_result=3799; ok=2075
- cmaes-v7-omr-runtime: mqps_fallback=129; ok=5745
- cmaes-v7-omr-source: historical_source_missing_use_raw_result=5874
- drl-v7-bmr-runtime: mqps_fallback=19; ok=5855
- drl-v7-omr-runtime: mqps_fallback=19; ok=5853; repaired_exact_drl_v7_omr_result=2

## Throughput Stats

| algorithm | coverage | mean_mqps | p05_mqps | p25_mqps | p50_mqps | p75_mqps | p95_mqps | p100_mqps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| drl-v7-omr-cache01 | 5874/5874 | 0.225546 | 0.018083 | 0.042007 | 0.075058 | 0.145858 | 0.423103 | 3.055480 |
| drl-v7-bmr-cache01 | 5874/5874 | 0.231617 | 0.032955 | 0.070466 | 0.118293 | 0.203036 | 0.516825 | 2.982731 |
| cmaes-v7-omr-cache01 | 5874/5874 | 0.500525 | 0.065513 | 0.176030 | 0.299848 | 0.484059 | 0.991863 | 4.546645 |
| cmaes-v7-bmr-cache01 | 5874/5874 | 0.447927 | 0.073215 | 0.155524 | 0.235312 | 0.390574 | 0.761396 | 6.986397 |
| ARC | 5874/5874 | 3.424925 | 2.580000 | 3.730000 | 4.860000 | 6.747500 | 9.720000 | 19.430000 |
| Cacheus | 5874/5874 | 1.068580 | 0.710000 | 1.090000 | 1.480000 | 2.050000 | 3.230000 | 7.180000 |
| GDSF | 5874/5874 | 0.730940 | 0.600000 | 0.930000 | 1.230000 | 1.770000 | 2.770000 | 6.320000 |
| GLCache | 5874/5874 | 2.318049 | 1.640000 | 2.380000 | 3.110000 | 4.340000 | 6.483500 | 17.750000 |
| LHD | 5874/5874 | 1.338360 | 0.800000 | 1.200000 | 1.750000 | 2.690000 | 4.520000 | 9.650000 |
| LRU | 5874/5874 | 3.665183 | 2.760000 | 3.890000 | 5.125000 | 7.210000 | 10.423500 | 19.480000 |
| LeCaR | 5874/5874 | 1.920204 | 0.400075 | 0.437493 | 0.482726 | 3.957500 | 6.440000 | 14.755149 |
| S3FIFO-0.1000-2 | 5874/5874 | 2.272233 | 1.450000 | 2.222500 | 3.050000 | 4.407500 | 7.083500 | 17.050000 |
| Sieve | 5874/5874 | 3.865195 | 2.810000 | 3.990000 | 5.210000 | 7.367500 | 10.773500 | 20.650000 |
| WTinyLFU-w0.01-SLRU | 5874/5874 | 1.603787 | 0.780000 | 1.420000 | 2.020000 | 2.720000 | 4.390000 | 13.310000 |
| LRB-BMR | 5874/5874 | 0.087827 | 0.010000 | 0.020000 | 0.030000 | 0.050000 | 0.950000 | 2.480000 |
| ThreeLCache-BMR | 5874/5874 | 0.842338 | 0.517920 | 0.801819 | 1.039268 | 1.501674 | 2.781895 | 8.341320 |
| ThreeLCache-OMR | 5874/5874 | 0.737083 | 0.610062 | 0.861370 | 1.101772 | 1.543613 | 2.931573 | 8.341320 |
