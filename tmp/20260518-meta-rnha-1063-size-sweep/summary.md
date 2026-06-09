# meta_rnha and tencentBlock_1063 size sweep

## Scope

- Traces: meta_rnha, tencentBlock_1063
- Cache sizes: 0.001, 0.01, 0.02, 0.05, 0.1
- Policies: LRU, LRB-BMR, ThreeLCache-OMR, ThreeLCache-BMR, LOH-cmaes-step2-f001-r128-seed101
- LOH step2 settings: CMA-ES on, RL off, random_candidates=128, structured_candidates=16, rng_seed=101, auto_compound=0, step02_event_rebuild pool enabled
- LOH cfg source: tmp/20260510-drl-v7-omr-cache01-plan/manifest.tsv matching trace rows; both target traces use cfg=f001_orig, LOH_USE_FREQ_REC=0, LOH_USE_FREQ_SIZE=0, LOH_USE_REC_SIZE=1, LOH_USE_SIZE=1
- Arrival-rate source: /home/丁坤鹏/tmp/adjacent_request_time_stats/manifest_20260514_watchdog_failfirst_full/per_trace_quantiles.tsv

## Arrival Rates

| trace | mean arrival req/s | max arrival req/s |
|---|---:|---:|
| meta_rnha | 139.870409 | 27,374.000 |
| tencentBlock_1063 | 500.482361 | 2,289.000 |

## Results

### meta_rnha

| cache | policy | rc | MR | BMR | MQPS | throughput req/s | x mean arrival | x max arrival | >= mean | >= max |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| 0.001 | LRU | 0 | 0.664542 | 0.286474 | 3.85 | 3,850,000.000 | 27,525.479 | 140.644 | yes | yes |
| 0.001 | LRB-BMR | 0 | 0.651141 | 0.292551 | 0.01 | 10,000.000 | 71.495 | 0.365 | yes | no |
| 0.001 | ThreeLCache-OMR | 0 | 0.736570 | 0.315054 | 0.44 | 440,000.000 | 3,145.769 | 16.074 | yes | yes |
| 0.001 | ThreeLCache-BMR | 0 | 0.669745 | 0.285121 | 0.59 | 590,000.000 | 4,218.190 | 21.553 | yes | yes |
| 0.001 | LOH-cmaes-step2-f001-r128-seed101 | 0 | 0.440300 | 0.243803 | 0.28 | 280,000.000 | 2,001.853 | 10.229 | yes | yes |
| 0.01 | LRU | 0 | 0.593428 | 0.267784 | 3.60 | 3,600,000.000 | 25,738.110 | 131.512 | yes | yes |
| 0.01 | LRB-BMR | 0 | 0.577939 | 0.265129 | 0.01 | 10,000.000 | 71.495 | 0.365 | yes | no |
| 0.01 | ThreeLCache-OMR | 0 | 0.654916 | 0.281235 | 0.36 | 360,000.000 | 2,573.811 | 13.151 | yes | yes |
| 0.01 | ThreeLCache-BMR | 0 | 0.595004 | 0.264294 | 0.37 | 370,000.000 | 2,645.306 | 13.516 | yes | yes |
| 0.01 | LOH-cmaes-step2-f001-r128-seed101 | 0 | 0.396957 | 0.214324 | 0.45 | 450,000.000 | 3,217.264 | 16.439 | yes | yes |
| 0.02 | LRU | 0 | 0.566800 | 0.260030 | 3.52 | 3,520,000.000 | 25,166.152 | 128.589 | yes | yes |
| 0.02 | LRB-BMR | 0 | 0.552427 | 0.255634 | 0.01 | 10,000.000 | 71.495 | 0.365 | yes | no |
| 0.02 | ThreeLCache-OMR | 0 | 0.639096 | 0.276238 | 0.42 | 420,000.000 | 3,002.780 | 15.343 | yes | yes |
| 0.02 | ThreeLCache-BMR | 0 | 0.561025 | 0.252941 | 0.35 | 350,000.000 | 2,502.316 | 12.786 | yes | yes |
| 0.02 | LOH-cmaes-step2-f001-r128-seed101 | 0 | 0.385165 | 0.205991 | 0.68 | 680,000.000 | 4,861.643 | 24.841 | yes | yes |
| 0.05 | LRU | 0 | 0.524739 | 0.242744 | 3.42 | 3,420,000.000 | 24,451.205 | 124.936 | yes | yes |
| 0.05 | LRB-BMR | 0 | 0.504912 | 0.235018 | 0.02 | 20,000.000 | 142.990 | 0.731 | yes | no |
| 0.05 | ThreeLCache-OMR | 0 | 0.621299 | 0.268678 | 0.36 | 360,000.000 | 2,573.811 | 13.151 | yes | yes |
| 0.05 | ThreeLCache-BMR | 0 | 0.517033 | 0.233621 | 0.44 | 440,000.000 | 3,145.769 | 16.074 | yes | yes |
| 0.05 | LOH-cmaes-step2-f001-r128-seed101 | 0 | 0.376518 | 0.198131 | 0.55 | 550,000.000 | 3,932.211 | 20.092 | yes | yes |
| 0.1 | LRU | 0 | 0.485568 | 0.225393 | 2.26 | 2,260,000.000 | 16,157.814 | 82.560 | yes | yes |
| 0.1 | LRB-BMR | 0 | 0.464867 | 0.213885 | 0.02 | 20,000.000 | 142.990 | 0.731 | yes | no |
| 0.1 | ThreeLCache-OMR | 0 | 0.604016 | 0.261185 | 0.34 | 340,000.000 | 2,430.822 | 12.421 | yes | yes |
| 0.1 | ThreeLCache-BMR | 0 | 0.482975 | 0.217881 | 0.45 | 450,000.000 | 3,217.264 | 16.439 | yes | yes |
| 0.1 | LOH-cmaes-step2-f001-r128-seed101 | 0 | 0.370320 | 0.190117 | 0.76 | 760,000.000 | 5,433.601 | 27.764 | yes | yes |

### tencentBlock_1063

| cache | policy | rc | MR | BMR | MQPS | throughput req/s | x mean arrival | x max arrival | >= mean | >= max |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| 0.001 | LRU | 0 | 0.916657 | 0.925067 | 5.05 | 5,050,000.000 | 10,090.266 | 2,206.204 | yes | yes |
| 0.001 | LRB-BMR | 0 | 0.853508 | 0.885013 | 0.02 | 20,000.000 | 39.961 | 8.737 | yes | yes |
| 0.001 | ThreeLCache-OMR | 0 | 0.732876 | 0.844205 | 0.55 | 550,000.000 | 1,098.940 | 240.280 | yes | yes |
| 0.001 | ThreeLCache-BMR | 0 | 0.854104 | 0.879258 | 0.44 | 440,000.000 | 879.152 | 192.224 | yes | yes |
| 0.001 | LOH-cmaes-step2-f001-r128-seed101 | 0 | 0.703136 | 0.788880 | 0.43 | 430,000.000 | 859.171 | 187.855 | yes | yes |
| 0.01 | LRU | 0 | 0.802736 | 0.828134 | 4.88 | 4,880,000.000 | 9,750.593 | 2,131.935 | yes | yes |
| 0.01 | LRB-BMR | 0 | 0.663574 | 0.684454 | 0.02 | 20,000.000 | 39.961 | 8.737 | yes | yes |
| 0.01 | ThreeLCache-OMR | 0 | 0.455387 | 0.478782 | 0.59 | 590,000.000 | 1,178.863 | 257.754 | yes | yes |
| 0.01 | ThreeLCache-BMR | 0 | 0.652683 | 0.676670 | 0.57 | 570,000.000 | 1,138.901 | 249.017 | yes | yes |
| 0.01 | LOH-cmaes-step2-f001-r128-seed101 | 0 | 0.399523 | 0.437834 | 0.33 | 330,000.000 | 659.364 | 144.168 | yes | yes |
| 0.02 | LRU | 0 | 0.684308 | 0.691160 | 4.57 | 4,570,000.000 | 9,131.191 | 1,996.505 | yes | yes |
| 0.02 | LRB-BMR | 0 | 0.561459 | 0.545658 | 0.02 | 20,000.000 | 39.961 | 8.737 | yes | yes |
| 0.02 | ThreeLCache-OMR | 0 | 0.336011 | 0.340289 | 0.69 | 690,000.000 | 1,378.670 | 301.442 | yes | yes |
| 0.02 | ThreeLCache-BMR | 0 | 0.557177 | 0.543494 | 0.61 | 610,000.000 | 1,218.824 | 266.492 | yes | yes |
| 0.02 | LOH-cmaes-step2-f001-r128-seed101 | 0 | 0.293624 | 0.328926 | 0.40 | 400,000.000 | 799.229 | 174.749 | yes | yes |
| 0.05 | LRU | 0 | 0.404958 | 0.386623 | 4.03 | 4,030,000.000 | 8,052.232 | 1,760.594 | yes | yes |
| 0.05 | LRB-BMR | 0 | 0.362707 | 0.313745 | 0.02 | 20,000.000 | 39.961 | 8.737 | yes | yes |
| 0.05 | ThreeLCache-OMR | 0 | 0.184104 | 0.198940 | 0.72 | 720,000.000 | 1,438.612 | 314.548 | yes | yes |
| 0.05 | ThreeLCache-BMR | 0 | 0.372777 | 0.321792 | 0.60 | 600,000.000 | 1,198.843 | 262.123 | yes | yes |
| 0.05 | LOH-cmaes-step2-f001-r128-seed101 | 0 | 0.118614 | 0.130011 | 0.57 | 570,000.000 | 1,138.901 | 249.017 | yes | yes |
| 0.1 | LRU | 0 | 0.261774 | 0.220946 | 5.15 | 5,150,000.000 | 10,290.073 | 2,249.891 | yes | yes |
| 0.1 | LRB-BMR | 0 | 0.249866 | 0.207887 | 0.02 | 20,000.000 | 39.961 | 8.737 | yes | yes |
| 0.1 | ThreeLCache-OMR | 0 | 0.060630 | 0.062025 | 0.92 | 920,000.000 | 1,838.227 | 401.922 | yes | yes |
| 0.1 | ThreeLCache-BMR | 0 | 0.252227 | 0.207182 | 0.64 | 640,000.000 | 1,278.766 | 279.598 | yes | yes |
| 0.1 | LOH-cmaes-step2-f001-r128-seed101 | 0 | 0.018359 | 0.021598 | 1.31 | 1,310,000.000 | 2,617.475 | 572.302 | yes | yes |

## Files

- Task manifest: /home/丁坤鹏/libcachesim_new/tmp/20260518-meta-rnha-1063-size-sweep/task_manifest.tsv
- Machine-readable summary: /home/丁坤鹏/libcachesim_new/tmp/20260518-meta-rnha-1063-size-sweep/summary.tsv
- Logs: /home/丁坤鹏/libcachesim_new/tmp/20260518-meta-rnha-1063-size-sweep/logs
- Result files: /home/丁坤鹏/libcachesim_new/tmp/20260518-meta-rnha-1063-size-sweep/results
