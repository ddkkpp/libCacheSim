# Cache01 Precise Throughput Summary

Throughput is recomputed as n_req / runtime / 1e6 and does not use rounded MQPS text from raw logs.

## Coverage

- trace universe: 2
- drl-v7-omr-cache01 available: 0/2
- drl-v7-bmr-cache01 available: 2/2
- drl-v7-omr-cache01 missing traces: tencent_photo1, tencent_photo2

## Source Verification

- baseline-ARC: exact_match_no_runtime=2
- baseline-Cacheus: exact_match_no_runtime=2
- baseline-GDSF: exact_match_no_runtime=2
- baseline-GLCache: exact_match_no_runtime=2
- baseline-LHD: exact_match_no_runtime=2
- baseline-LRB-BMR: exact_match_no_runtime=2
- baseline-LRU: exact_match_no_runtime=2
- baseline-LeCaR: exact_match_no_runtime=2
- baseline-S3FIFO-0.1000-2: exact_match_no_runtime=2
- baseline-Sieve: exact_match_no_runtime=2
- baseline-ThreeLCache-BMR: ok=2
- baseline-ThreeLCache-OMR: ok=2
- baseline-WTinyLFU-w0.01-SLRU: exact_match_no_runtime=2
- cmaes-v7-bmr-runtime: ok=2
- cmaes-v7-bmr-source: ok=2
- cmaes-v7-omr-runtime: ok=2
- cmaes-v7-omr-source: historical_source_missing_use_raw_result=2
- drl-v7-bmr-runtime: ok=2
- drl-v7-omr-runtime: missing=2

## Throughput Stats

| algorithm | coverage | mean_mqps | p05_mqps | p25_mqps | p50_mqps | p75_mqps | p95_mqps | p100_mqps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| drl-v7-omr-cache01 | 0/2 | - | - | - | - | - | - | - |
| drl-v7-bmr-cache01 | 2/2 | 0.029464 | 0.027259 | 0.028239 | 0.029464 | 0.030688 | 0.031668 | 0.031913 |
| cmaes-v7-omr-cache01 | 2/2 | 0.188419 | 0.187762 | 0.188054 | 0.188419 | 0.188785 | 0.189077 | 0.189150 |
| cmaes-v7-bmr-cache01 | 2/2 | 0.029464 | 0.027259 | 0.028239 | 0.029464 | 0.030688 | 0.031668 | 0.031913 |
| ARC | 0/2 | - | - | - | - | - | - | - |
| Cacheus | 0/2 | - | - | - | - | - | - | - |
| GDSF | 0/2 | - | - | - | - | - | - | - |
| GLCache | 0/2 | - | - | - | - | - | - | - |
| LHD | 0/2 | - | - | - | - | - | - | - |
| LRU | 0/2 | - | - | - | - | - | - | - |
| LeCaR | 0/2 | - | - | - | - | - | - | - |
| S3FIFO-0.1000-2 | 0/2 | - | - | - | - | - | - | - |
| Sieve | 0/2 | - | - | - | - | - | - | - |
| WTinyLFU-w0.01-SLRU | 0/2 | - | - | - | - | - | - | - |
| LRB-BMR | 0/2 | - | - | - | - | - | - | - |
| ThreeLCache-BMR | 2/2 | 0.314959 | 0.314362 | 0.314627 | 0.314959 | 0.315291 | 0.315557 | 0.315623 |
| ThreeLCache-OMR | 2/2 | 0.263938 | 0.257238 | 0.260216 | 0.263938 | 0.267661 | 0.270638 | 0.271383 |
