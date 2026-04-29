# tencentPhoto 组 DRL-LOH 原始数据

**trace 数**: 2
**数据来源**: drl-feature-sweep
**日志目录**: `tmp/20260418-drl-feature-sweep/logs/`
**提取文件**: `tmp/20260418-drl-feature-sweep/logs/drl_from_cachesim_logs.tsv`
**非LOH Baseline 来源**: `/home/丁坤鹏/libCacheSim/result`（对应表4/表5）
**LOH 数据来源说明**: 表2/表3及 `best_LOH` 列来自上述 DRL 单模型实验批次；由于 DRL 仅有单一配置，`best_LOH` 与 `drl` 列一致。
**非LOH 数据来源说明**: 表4/表5按固定规则取值：先读取 `/home/丁坤鹏/libCacheSim/result` 中该 trace 的 baseline 记录；若 `LeCaR` 或 `LRB-BMR` 在主源缺失，则仅对缺失单元依次使用 `tmp/20260415-baseline-fill/`、`tmp/20260418-lecar-fill/` 下的补跑记录；`ThreeLCache-BMR` 优先使用 `tmp/20260417-3lcache-cachesize/`（修改版ThreeLCache重跑结果），缺失时回退主源。
**非LOH 算法来源分配**: `ARC/Cacheus/GDSF/GLCache/LHD/LRU/S3FIFO-0.1000-2/Sieve/WTinyLFU-w0.01-SLRU` 只取主源；`LeCaR/LRB-BMR` 按“主源优先，缺失补跑”规则逐 trace 取值（补跑源：`20260415-baseline-fill`、`20260418-lecar-fill`）；`ThreeLCache-BMR` 优先取 `20260417-3lcache-cachesize`（修改版重跑），缺失时回退主源。
**来源粒度说明**: 非LOH 是“按 trace、按算法单元”定源：同一算法在不同 trace 的来源由上述规则逐条确定，不做整算法全局覆盖假设。
**Baseline 匹配规则**: `cache size` 与表1误差在 5% 以内视为同一配置
**LOH 覆盖核定**: DRL 当前覆盖 2/2（缺失 0）
**Baseline 覆盖核定**: LRB-BMR 当前覆盖 2/2（缺失 0），其余算法覆盖情况见表4/表5覆盖行

## 表1: Trace 元数据

| trace | n_req | cache_size | r1(freq,fs) | r2(rec,rs) | r3(freq,fr) | r4(sz,fs) | r5(sz,rs) | r6(rec,fr) | r(freq,sz) | r(rec,sz) | r(freq,rec) | R²m_fs | R²m_rs | R²m_fr | cv_sz | cv_freq | cv_rec | avg_sz | n_obj |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| tencent_photo1 | 2,917,228,640 | 1TiB | 0.9845 | 0.5811 | 0.9833 | -0.1305 | 0.7866 | -0.4931 | 0.0191 | -0.0423 | -0.3827 | 0.9915 | 0.9968 | 0.9829 | 0.0921 | 0.6080 | 0.0694 | 22,959 | 57,668,763 |
| tencent_photo2 | 2,731,876,301 | 1TiB | 0.9844 | 0.5806 | 0.9830 | -0.1296 | 0.7870 | -0.4950 | 0.0206 | -0.0421 | -0.3848 | 0.9915 | 0.9968 | 0.9822 | 0.0921 | 0.6069 | 0.0694 | 22,908 | 55,788,293 |


## 表2: Miss Ratio (MR)

| trace | drl | best |
|---|---:|---|
| tencent_photo1 | **0.222938** | drl |
| tencent_photo2 | **0.227818** | drl |
| **简单平均** | 0.225378 | drl |

## 表3: Byte Miss Ratio (BMR)

| trace | drl | best |
|---|---:|---|
| tencent_photo1 | **0.236663** | drl |
| tencent_photo2 | **0.239311** | drl |
| **简单平均** | 0.237987 | drl |

## 表4: Baseline MR 对比

数据来源: /home/丁坤鹏/libCacheSim/result；cache size 与表1误差在 5% 以内视为同一配置。

所有 12 个 baseline 算法均覆盖全部 trace。

| trace | ARC | Cacheus | GDSF | GLCache | LHD | LRU | LeCaR | S3FIFO-0.1000-2 | Sieve | WTinyLFU-w0.01-SLRU | LRB-BMR | ThreeLCache-BMR | ThreeLCache-OMR | best_LOH |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| tencent_photo1 | 0.275900 | 0.240600 | 0.221000 | 0.249800 | 0.253400 | 0.250000 | 0.239200 | 0.239900 | 0.239900 | 0.275600 | 0.250000 | 0.293893 | 0.258549 |  |
| tencent_photo2 | 0.281900 | 0.245700 | 0.226100 | 0.251500 | 0.261700 | 0.255200 | 0.244300 | 0.245500 | 0.245300 | 0.278300 | 0.255200 | 0.287494 | 0.252268 |  |
| **覆盖数** | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |  |
| **平均** | 0.278900 | 0.243150 | 0.223550 | 0.250650 | 0.257550 | 0.252600 | 0.241750 | 0.242700 | 0.242600 | 0.276950 | 0.252600 | 0.290694 | 0.255408 |  |

## 表5: Baseline BMR 对比

数据来源: /home/丁坤鹏/libCacheSim/result；cache size 与表1误差在 5% 以内视为同一配置。

所有 12 个 baseline 算法均覆盖全部 trace。

| trace | ARC | Cacheus | GDSF | GLCache | LHD | LRU | LeCaR | S3FIFO-0.1000-2 | Sieve | WTinyLFU-w0.01-SLRU | LRB-BMR | ThreeLCache-BMR | ThreeLCache-OMR | best_LOH |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| tencent_photo1 | 0.241600 | 0.208400 | 0.227300 | 0.251800 | 0.294800 | 0.216900 | 0.206800 | 0.208800 | 0.208100 | 0.259400 | 0.216900 | 0.261987 | 0.262723 |  |
| tencent_photo2 | 0.246600 | 0.212500 | 0.232600 | 0.256400 | 0.306300 | 0.221100 | 0.211000 | 0.213400 | 0.212600 | 0.268200 | 0.221100 | 0.254174 | 0.261644 |  |
| **覆盖数** | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |  |
| **平均** | 0.244100 | 0.210450 | 0.229950 | 0.254100 | 0.300550 | 0.219000 | 0.208900 | 0.211100 | 0.210350 | 0.263800 | 0.219000 | 0.258081 | 0.262184 |  |
