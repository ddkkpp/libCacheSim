# MetaKV + Original-3 Algorithms Summary (2026-03-13)

## Data Sources
- Current run queue results: `tmp/phase_ab_latest/results.csv`
- Historical full-trace baseline table: `docs/20260317-FULL_EXPERIMENT_RESULTS.md` (section around 12.4)

## 1) MetaKV-202401: Your Algorithm (LOH-RL) and Current Baselines

Current queue contains MetaKV size `0.1` results. Your LOH-RL runs on MetaKV are currently failed (`rc=143`), while baseline algorithms completed.

| Rank (by MR) | Trace | Size | Algorithm | Miss Ratio | Byte Miss Ratio | Throughput (MQPS) | Status | Task ID |
|---|---|---:|---|---:|---:|---:|---|---|
| 1 | MetaKV-202401 | 0.1 | BeladySize | 0.046484 | 0.036074 | 1.83 | ok | `phaseB_bl_MetaKV-202401_0p1_BeladySize` |
| 2 | MetaKV-202401 | 0.1 | GDSF | 0.047397 | 0.056294 | 0.15 | ok | `phaseB_bl_MetaKV-202401_0p1_GDSF` |
| 3 | MetaKV-202401 | 0.1 | Belady | 0.048864 | 0.034821 | 0.83 | ok | `phaseB_bl_MetaKV-202401_0p1_Belady` |
| 4 | MetaKV-202401 | 0.1 | 3LCache-OMR | 0.056698 | 0.051139 | 0.43 | ok | `phaseB_bl_MetaKV-202401_0p1_3LCache-OMR` |
| 5 | MetaKV-202401 | 0.1 | 3LCache-BMR | 0.071056 | 0.043228 | 0.38 | ok | `phaseB_bl_MetaKV-202401_0p1_3LCache-BMR` |
| 6 | MetaKV-202401 | 0.1 | S3FIFO | 0.071075 | 0.043753 | 1.22 | ok | `phaseB_bl_MetaKV-202401_0p1_S3FIFO` |
| 7 | MetaKV-202401 | 0.1 | LRU | 0.074486 | 0.048201 | 1.56 | ok | `phaseB_bl_MetaKV-202401_0p1_LRU` |
| 8 | MetaKV-202401 | 0.1 | LFU | 0.259751 | 0.301502 | 1.34 | ok | `phaseB_bl_MetaKV-202401_0p1_LFU` |
| - | MetaKV-202401 | 0.1 | LOH-RL (log1p,w0) | - | - | - | failed rc=143 | `phaseB_rl_MetaKV-202401_0p1_log1p_w0` |
| - | MetaKV-202401 | 0.1 | LOH-RL (reciprocal,w0) | - | - | - | failed rc=143 | `phaseB_rl_MetaKV-202401_0p1_reciprocal_w0` |

## 2) Original 3 Traces: All Algorithms Table

This table is the all-algorithm reference for the original 3 traces (1063 / Wiki / Meta), from the historical full-trace comparison in `docs/20260317-FULL_EXPERIMENT_RESULTS.md`.

| Algorithm | 1063 MR / Byte MR / MQPS | Wiki MR / Byte MR / MQPS | Meta MR / Byte MR / MQPS |
|---|---|---|---|
| BeladySize | 0.018200 / 0.018689 / 0.74 | 0.124325 / 0.104216 / 0.29 | 0.268778 / 0.144016 / 3.51 |
| LOH-RandOnly | 0.023817 / 0.027561 / 0.78 | 0.172273 / 0.135979 / 0.14 | 0.269843 / 0.156441 / 0.43 |
| LOH-RL nb_500 | 0.026646 / 0.029527 / 0.58 | - | - |
| LOH-RL gated-penalty (0312) | 0.026796 / 0.029398 / 0.33 | - | - |
| LOH-RL (0306) | 0.027361 / 0.030195 / 0.75 | 0.176183 / 0.141579 / 0.15 | 0.269384 / 0.156423 / 0.97 |
| LOH-RL bl_50000 | 0.027407 / 0.030382 / 0.50 | - | - |
| GDSF | 0.054791 / 0.058776 / 0.33 | 0.180493 / 0.152894 / 0.20 | 0.268918 / 0.152952 / 0.27 |
| 3LCache-OMR | 0.060630 / 0.062025 / 0.54 | 0.174871 / 0.153405 / 0.31 | 0.392964 / 0.192144 / 0.39 |
| 3LCache-BMR | 0.252227 / 0.207182 / 0.46 | 0.182787 / 0.126047 / 0.31 | 0.324215 / 0.170269 / 0.38 |
| S3FIFO | 0.260116 / 0.215841 / 0.85 | 0.187962 / 0.129958 / 0.85 | 0.326397 / 0.170717 / 1.20 |
| LRU | 0.261774 / 0.220946 / 2.54 | 0.230638 / 0.161934 / 1.51 | 0.326804 / 0.175302 / 3.00 |
| LFUDA | fail (rc=147, stopped) | 0.193518 / 0.134803 / 0.87 | 0.356184 / 0.183358 / 1.63 |

## 3) Current Queue LOH-RL (Original 3, size=0.1)

For convenience, below are the latest successful LOH-RL entries from the current queue for original 3 traces:

| Trace | Algorithm | Miss Ratio | Byte Miss Ratio | Throughput (MQPS) | Task ID |
|---|---|---:|---:|---:|---|
| 1063 | LOH-RL (log1p,w1) | 0.026920 | 0.029850 | 0.33 | `phaseA_rl_1063_0p1_log1p_w1` |
| 1063 | LOH-RL (log1p,w0) | 0.027173 | 0.030128 | 0.55 | `phaseB_rl_1063_0p1_log1p_w0` |
| meta | LOH-RL (log1p,w1) | 0.269001 | 0.157198 | 0.80 | `phaseA_rl_meta_0p1_log1p_w1` |
| meta | LOH-RL (log1p,w0) | 0.269004 | 0.157267 | 0.71 | `phaseB_rl_meta_0p1_log1p_w0` |
| wiki | LOH-RL (reciprocal,w1) | 0.177137 | 0.138797 | 0.07 | `phaseA_rl_wiki_0p1_reciprocal_w1` |
| wiki | LOH-RL (reciprocal,w0) | 0.178754 | 0.139111 | 0.07 | `phaseB_rl_wiki_0p1_reciprocal_w0` |

## 4) Matrix View (Algorithm x Trace)

Cell format: `MR / ByteMR / MQPS`.

| Rank | Algorithm | 1063 | wiki | meta | MetaKV-202401 | Alibaba-4 |
|---|---|---|---|---|---|---|
| 1 | BeladySize | 0.018200 / 0.018689 / 0.74 | 0.124325 / 0.104216 / 0.29 | 0.268778 / 0.144016 / 3.51 | 0.046484 / 0.036074 / 1.83 | 0.031616 / 0.047520 / 7.54 |
| 2 | LOH-RL (w1/weights-in-obs) | 0.026920 / 0.029850 / 0.33 | 0.177137 / 0.138797 / 0.07 | 0.269001 / 0.157198 / 0.80 | - | - |
| 3 | LOH-RL (w0/default obs) | 0.027173 / 0.030128 / 0.55 | 0.178754 / 0.139111 / 0.07 | 0.269004 / 0.157267 / 0.71 | fail(rc=143) | fail(rc=143) |
| 4 | GDSF | 0.054791 / 0.058776 / 0.33 | 0.180493 / 0.152894 / 0.20 | 0.268918 / 0.152952 / 0.27 | 0.047397 / 0.056294 / 0.15 | 0.032012 / 0.049435 / 0.69 |
| 5 | 3LCache-OMR | 0.060630 / 0.062025 / 0.54 | 0.174871 / 0.153405 / 0.31 | 0.392964 / 0.192144 / 0.39 | 0.056698 / 0.051139 / 0.43 | 0.031689 / 0.048377 / 1.02 |
| 6 | Belady | 0.147024 / 0.124058 / 1.33 | 0.134717 / 0.093238 / 0.75 | 0.268778 / 0.144016 / 1.51 | 0.048864 / 0.034821 / 0.83 | 0.031616 / 0.047520 / 5.04 |
| 7 | 3LCache-BMR | 0.252227 / 0.207182 / 0.46 | 0.182787 / 0.126047 / 0.31 | 0.324215 / 0.170269 / 0.38 | 0.071056 / 0.043228 / 0.38 | 0.031700 / 0.047994 / 0.99 |
| 8 | S3FIFO | 0.260116 / 0.215841 / 0.85 | 0.187962 / 0.129958 / 0.85 | 0.326397 / 0.170717 / 1.20 | 0.071075 / 0.043753 / 1.22 | 0.031703 / 0.047989 / 5.87 |
| 9 | LRU | 0.261774 / 0.220946 / 2.54 | 0.230638 / 0.161934 / 1.51 | 0.326804 / 0.175302 / 3.00 | 0.074486 / 0.048201 / 1.56 | 0.031712 / 0.048006 / 8.73 |
| 10 | LFU / LFUDA | LFUDA fail(rc=147) | 0.193518 / 0.134803 / 0.87 (LFUDA) | 0.356184 / 0.183358 / 1.63 (LFUDA) | 0.259751 / 0.301502 / 1.34 (LFU) | 0.280883 / 0.271615 / 4.72 (LFU) |

Notes:
- Original 3 all-algorithm values are from `docs/20260317-FULL_EXPERIMENT_RESULTS.md` (full-trace baseline table).
- MetaKV and Alibaba values are from current queue `tmp/phase_ab_latest/results.csv`.
- Original-3 S3FIFO values are from manual logs: `tmp/phase_ab_0312_223925/logs/manual_s3fifo_{1063,meta,wiki}_0p1.log`.
- Row order is sorted by `1063` miss ratio ascending; rows without valid `1063` MR are placed at the end.
