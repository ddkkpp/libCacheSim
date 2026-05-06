# tencentPhoto 组特征组合结果（20260504 ablation r128 cache=0.01）

- trace_count: 2
- 数据源: tmp/20260504-ablation-9cfg-cache001-r128-plan/results/
- LOH_RANDOM_CANDIDATES=128, LOH_AUTO_COMPOUND=0, cache_size=0.01
- combo命名映射: f***_orig 表示 use_size=1，f***_ns 表示 use_size=0。
- 其中 *** 按位对应 (freq_rec, freq_size, rec_size)。

## 表1: Trace 元数据

| trace | n_req | cache_size | r1(freq,fs) | r2(rec,rs) | one_hit |
|---|---:|---:|---:|---:|---:|
| tencent_photo1 | 2,917,228,640 | 123GiB | 0.9760 | 0.6216 | 0.7376 |
| tencent_photo2 | 2,731,876,301 | 119GiB | 0.9756 | 0.6225 | 0.7402 |

## 表2: Miss Ratio (MR)

| trace | f000_orig | f001_orig | f010_orig | f011_orig | f100_orig | f101_orig | f110_orig | f111_orig | f100_ns | best_LOH | best_cfg |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| tencent_photo1 | 0.381420 | 0.379137 | 0.432783 | 0.404518 | 0.417546 | 0.388256 | 0.447206 | 0.419522 | 0.515709 | 0.379137 | f001_orig |
| tencent_photo2 | 0.387850 | 0.384614 | 0.439887 | 0.410303 | 0.425473 | 0.394745 | 0.455403 | 0.426419 | 0.521927 | 0.384614 | f001_orig |

- best_LOH MR 组平均: 0.381876
- best_LOH MR 加权平均(n_req): 0.381786
- best_LOH MR 标准差: 0.002739
- 有结果 trace 数: 2/2

## 表3: Byte Miss Ratio (BMR)

| trace | f000_orig | f001_orig | f010_orig | f011_orig | f100_orig | f101_orig | f110_orig | f111_orig | f100_ns | best_LOH | best_cfg |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| tencent_photo1 | 0.433655 | 0.449147 | 0.473942 | 0.463490 | 0.432056 | 0.425978 | 0.461082 | 0.451294 | 0.468921 | 0.425978 | f101_orig |
| tencent_photo2 | 0.437439 | 0.450943 | 0.477590 | 0.466094 | 0.437827 | 0.430087 | 0.466324 | 0.455581 | 0.474146 | 0.430087 | f101_orig |

- best_LOH BMR 组平均: 0.428033
- best_LOH BMR 加权平均(n_req): 0.427965
- best_LOH BMR 标准差: 0.002054
- 有结果 trace 数: 2/2
