# metaCDN 组特征组合结果（20260504 ablation r128 cache=0.01）

- trace_count: 3
- 数据源: tmp/20260504-ablation-9cfg-cache001-r128-plan/results/
- LOH_RANDOM_CANDIDATES=128, LOH_AUTO_COMPOUND=0, cache_size=0.01
- combo命名映射: f***_orig 表示 use_size=1，f***_ns 表示 use_size=0。
- 其中 *** 按位对应 (freq_rec, freq_size, rec_size)。

## 表1: Trace 元数据

| trace | n_req | cache_size | r1(freq,fs) | r2(rec,rs) | one_hit |
|---|---:|---:|---:|---:|---:|
| meta_reag | 45,623,306 | 2TiB | 0.7107 | 0.3836 | 0.7615 |
| meta_rnha | 96,680,668 | 7TiB | 0.7058 | 0.3848 | 0.8256 |
| meta_rprn | 88,470,732 | 7TiB | 0.6830 | 0.3467 | 0.8329 |

## 表2: Miss Ratio (MR)

| trace | f000_orig | f001_orig | f010_orig | f011_orig | f100_orig | f101_orig | f110_orig | f111_orig | f100_ns | best_LOH | best_cfg |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| meta_reag | 0.291361 | 0.286176 | 0.286230 | 0.278524 | 0.306560 | 0.302539 | 0.324942 | 0.286442 | 0.417511 | 0.278524 | f011_orig |
| meta_rnha | 0.396348 | 0.398176 | 0.407225 | 0.393219 | 0.461809 | 0.431719 | 0.478585 | 0.429917 | 0.651124 | 0.393219 | f011_orig |
| meta_rprn | 0.348893 | 0.360672 | 0.352011 | 0.346926 | 0.386041 | 0.371849 | 0.383867 | 0.363573 | 0.556464 | 0.346926 | f011_orig |

- best_LOH MR 组平均: 0.339556
- best_LOH MR 加权平均(n_req): 0.352797
- best_LOH MR 标准差: 0.047113
- 有结果 trace 数: 3/3

## 表3: Byte Miss Ratio (BMR)

| trace | f000_orig | f001_orig | f010_orig | f011_orig | f100_orig | f101_orig | f110_orig | f111_orig | f100_ns | best_LOH | best_cfg |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| meta_reag | 0.182192 | 0.183099 | 0.183414 | 0.178066 | 0.184795 | 0.184190 | 0.194061 | 0.178239 | 0.210101 | 0.178066 | f011_orig |
| meta_rnha | 0.209940 | 0.212939 | 0.211946 | 0.208814 | 0.230967 | 0.224319 | 0.236868 | 0.221219 | 0.274141 | 0.208814 | f011_orig |
| meta_rprn | 0.227422 | 0.232281 | 0.226946 | 0.226195 | 0.236025 | 0.234417 | 0.235378 | 0.230449 | 0.272870 | 0.226195 | f011_orig |

- best_LOH BMR 组平均: 0.204358
- best_LOH BMR 加权平均(n_req): 0.209398
- best_LOH BMR 标准差: 0.019900
- 有结果 trace 数: 3/3
