# 已测试配置汇总（来自 sweeps/ 与 conversation.txt）

说明：本文件自动从 conversation.txt 抽取实际执行过的命令，并按 trace 与 CACHESIM_NUM_REQ 分组。
各 sweep 的配置以 `scripts/sweep_configs_*.txt` 为准；本文不展开逐行配置，只在表格与通用配置中保留与策略行为直接相关的关键开关（特征/归一化/评分与动作选择/奖励惩罚/算法等），并纳入训练超参；仍排除 IPC/共享内存/信号量等同步参数。

说明更新（2026-01-31）：训练参数需要纳入本汇总；仍排除 IPC/共享内存/信号量等同步参数。

## 默认值速查（未显式设置时）

### 脚本层（Shell）

- scripts/test_loh_rl_sb3.sh：trace 默认 data/MetaCDN/meta_reag.oracleGeneral.zst；cache_ratio 默认 0.1；CACHESIM_NUM_REQ 未设置则表示 ALL（不主动限制）。
- scripts/sweep_loh_rl_sb3.sh：trace 默认 data/MetaCDN/meta_reag.oracleGeneral.zst；cache_ratio 默认 0.1；若 trace 位于 data/MetaCDN/* 或 data/TencentCBS/* 且未设置 CACHESIM_NUM_REQ，则默认 3000000。
- scripts/sweep_loh_constant_weights_norl.sh：CACHESIM_NUM_REQ 默认 3000000；CACHE_RATIO 默认 0.1；TRACE_LIST 未设置则默认顺序：meta_reag → wiki_2019t → 1063（三条）。

- LOH_FEATURE_LOG1P = 0
- LOH_SOFTMAX_TEMP = 1.0
- LOH_ACTION_BOUND = 1.0
- LOH_ACTION_SCALE = 1.0
- LOH_FIXED_OBS = 0
- LOH_SCORE_USE_IRT = 1
- LOH_SCORE_USE_COMPOUND = 0
- LOH_USE_HEURISTIC_SIGNS = 1
- LOH_REWARD_SCALE = 1.0
- LOH_MISS_RATIO_WEIGHT = 1.0
- LOH_RL_ALGO = SAC
- LOH_SOFT_PRIOR = 0
- LOH_SOFT_PRIOR_BIAS = 0.5
## 配置缩写速查（细表 cfg 列）

为避免表格横向滚动，本文件在 `cfg` 列使用短写；其来源基本对应 `scripts/sweep_configs_*.txt` 中的环境变量。

- `cpd`：`LOH_SCORE_USE_COMPOUND`（是否启用 compound 评分/特征组，1=开，0=关）
- `irt`：`LOH_SCORE_USE_IRT`（是否启用 IRT 评分/特征组，1=开，0=关）
- `norm`：`LOH_ENABLE_FEATURE_NORMALIZATION`（特征归一化/裁剪统计开关，1=开，0=关）
- `int`：`RL_UPDATE_INTERVAL`（模拟器端与 RL 同步/更新权重的触发间隔）
- `bound`：`LOH_ACTION_BOUND`（动作空间范围，Box [-bound, bound]）
- `temp`：`LOH_SOFTMAX_TEMP`（仅当 `LOH_USE_SOFTMAX=1` 时生效）
- `scale`：`LOH_ACTION_SCALE`（动作缩放因子）
- `softmax`：表示 `LOH_USE_SOFTMAX=1`（动作通过 softmax 选择）
- `linear`：表示 `LOH_USE_SOFTMAX=0` 且通常伴随 `LOH_SCORE_MODEL=linear`（线性对照/不走 softmax）
- `cacheF`：`LOH_INCLUDE_CACHE_FEATURES=1`（在 state 中加入 cache 侧特征）
- `candF`：`LOH_INCLUDE_CANDIDATE_FEATURES=1`（在 state 中加入候选/受害者侧特征）
- `mrw`：`LOH_MISS_RATIO_WEIGHT`（reward 或统计中 miss_ratio 权重）
- `ema`：`LOH_WEIGHT_EMA`（weights 平滑系数，0 表示不做 EMA）
- `clip`：`LOH_WEIGHT_CLIP`（weights 绝对值裁剪，0 表示不裁剪）
- `rmode`：`LOH_REWARD_MODE`（`absolute`/`delta`）
- `rscale`：`LOH_REWARD_SCALE`（reward 缩放）
- `pen=...`：`LOH_ENABLE_PENALTY=1` 且 `LOH_PENALTY_SCALE=...`（penalty 形式，如 `reciprocal/log/survival/linear`）

约定：从本段之后新增/修订的 sweep 细表，都会先写“通用配置”，并让表内 `cfg` 仅列出该行相对通用配置的差异项。



### sweeps 全量索引（最近 → 最旧）

说明：扫描 `sweeps/` 下全部 `results.csv` 与 `combined_summary.csv`，按目录名推断日期并倒序排列；另外把仓库里较早的“非 sweeps 目录”的遗留汇总（如 [sweep_results.md](sweep_results.md)、[docs/sweep_results.md](docs/sweep_results.md)、[runs/sweep_results.md](runs/sweep_results.md)）也补入（这类记录通常缺失精确日期，统一标为 `unknown` 并放在表尾）。为避免横向滚动，`trace` 列使用短标识（完整 `trace_file` 以 CSV 为准，或见下方各 trace 章节标题）。

| date | sweep | trace | best | OMR | BMR | cfg | ref | note |
| ---: | --- | --- | ---: | ---: | ---: | --- | --- | --- |
| 20260130 | modes2_mrw0_0130_112123 | MetaCDN/meta_reag | 2 | 0.367959 | 0.217457 | SAC softmax score=linear log1p=1 norm=1 int=200 temp=1.3 scale=0.5 mrw=0.0 | [cs](sweeps/modes2_mrw0_0130_112123/combined_summary.csv) |  |
| 20260130 | modes2_mrw0_0130_112123 | TencentCBS/1063 | 2 | 0.373018 | 0.329636 | SAC softmax score=linear log1p=1 norm=1 int=200 temp=1.3 scale=0.5 mrw=0.0 | [cs](sweeps/modes2_mrw0_0130_112123/combined_summary.csv) |  |
| 20260130 | modes2_mrw0_0130_112123 | WikiCDN/wiki_2019t | 1 | 0.595771 | 0.475249 | SAC softmax score=linear log1p=1 norm=1 cpd=1 int=200 temp=1.3 scale=0.5 mrw=0.0 | [cs](sweeps/modes2_mrw0_0130_112123/combined_summary.csv) |  |
| 20260130 | modes2_mrw0_0130_112123 | Alibaba/4 | 2 | 0.075593 | 0.097003 | SAC softmax score=linear log1p=1 norm=1 int=200 temp=1.3 scale=0.5 mrw=0.0 | [cs](sweeps/modes2_mrw0_0130_112123/combined_summary.csv) |  |
| 20260130 | modes2_mrw0_0130_112123 | MetaKV/202401_kv_all_sort | 2 | 0.238511 | 0.228688 | SAC softmax score=linear log1p=1 norm=1 int=200 temp=1.3 scale=0.5 mrw=0.0 | [cs](sweeps/modes2_mrw0_0130_112123/combined_summary.csv) |  |
| 20260130 | modes2_mrw0_0130_112123 | TencentPhoto/tencent_photo1 | 2 | 0.740089 | 0.763673 | SAC softmax score=linear log1p=1 norm=1 int=200 temp=1.3 scale=0.5 mrw=0.0 | [cs](sweeps/modes2_mrw0_0130_112123/combined_summary.csv) |  |
| 20260130 | modes2_mrw0_0130_112123 | WikiCDN/wiki_2016u | 1 | 0.349572 | 0.822682 | SAC softmax score=linear log1p=1 norm=1 cpd=1 int=200 temp=1.3 scale=0.5 mrw=0.0 | [cs](sweeps/modes2_mrw0_0130_112123/combined_summary.csv) |  |
| 20260130 | modes3_batch_0130_021623 | TencentCBS/1063 | 3 | 0.373167 | 0.329636 | SAC softmax score=linear log1p=1 norm=1 int=200 temp=1.3 scale=0.5 | [cs](sweeps/modes3_batch_0130_021623/combined_summary.csv) |  |
| 20260130 | modes3_batch_0130_021623 | MetaKV/202401_kv_all_sort | 3 | 0.237896 | 0.229392 | SAC softmax score=linear log1p=1 norm=1 int=200 temp=1.3 scale=0.5 | [cs](sweeps/modes3_batch_0130_021623/combined_summary.csv) |  |
| 20260130 | modes3_batch_0130_021623 | Alibaba/4 | 3 | 0.075504 | 0.096678 | SAC softmax score=linear log1p=1 norm=1 int=200 temp=1.3 scale=0.5 | [cs](sweeps/modes3_batch_0130_021623/combined_summary.csv) |  |
| 20260130 | modes3_batch_0130_021623 | MetaCDN/meta_reag | 3 | 0.367960 | 0.217561 | SAC softmax score=linear log1p=1 norm=1 int=200 temp=1.3 scale=0.5 | [cs](sweeps/modes3_batch_0130_021623/combined_summary.csv) |  |
| 20260130 | modes3_batch_0130_021623 | TencentPhoto/tencent_photo1 | 3 | 0.740252 | 0.763826 | SAC softmax score=linear log1p=1 norm=1 int=200 temp=1.3 scale=0.5 | [cs](sweeps/modes3_batch_0130_021623/combined_summary.csv) |  |
| 20260130 | modes3_batch_0130_021623 | WikiCDN/wiki_2016u | 1 | 0.349567 | 0.822716 | SAC softmax score=linear log1p=1 norm=1 cpd=1 irt=1 int=200 temp=1.3 scale=0.5 | [cs](sweeps/modes3_batch_0130_021623/combined_summary.csv) |  |
| 20260130 | modes3_batch_0130_021623 | WikiCDN/wiki_2019t | 1 | 0.595705 | 0.475151 | SAC softmax score=linear log1p=1 norm=1 cpd=1 irt=1 int=200 temp=1.3 scale=0.5 | [cs](sweeps/modes3_batch_0130_021623/combined_summary.csv) |  |
| 20260129 | next_wiki_bootstrap_req1_3m_20260129_184646 | WikiCDN/wiki_2019t | 3 | 0.595814 | 0.475283 | SAC softmax log1p=1 norm=1 cpd=1 irt=1 int=200 temp=1.3 scale=0.5 | [res](sweeps/next_wiki_bootstrap_req1_3m_20260129_184646/results.csv) |  |
| 20260129 | next_1063_localgrid_req1_3m_20260129_184633 | TencentCBS/1063 | 10 | 0.370464 | 0.351355 | SAC linear score=linear log1p=1 norm=1 int=50 scale=1.0 | [res](sweeps/next_1063_localgrid_req1_3m_20260129_184633/results.csv) |  |
| 20260129 | next_meta_modes_req1_3m_20260129_184621 | MetaCDN/meta_reag | 1 | 0.367959 | 0.217529 | SAC softmax log1p=1 norm=1 int=200 temp=1.3 scale=0.5 | [res](sweeps/next_meta_modes_req1_3m_20260129_184621/results.csv) |  |
| 20260129 | next_wiki_bootstrap_nosem_3m_20260129_184204 | WikiCDN/wiki_2019t | - | NA | NA | — | [res](sweeps/next_wiki_bootstrap_nosem_3m_20260129_184204/results.csv) | NA |
| 20260129 | next_1063_localgrid_nosem_3m_20260129_184141 | TencentCBS/1063 | - | NA | NA | — | [res](sweeps/next_1063_localgrid_nosem_3m_20260129_184141/results.csv) | NA |
| 20260129 | next_meta_modes_nosem_3m_20260129_184111 | MetaCDN/meta_reag | - | NA | NA | — | [res](sweeps/next_meta_modes_nosem_3m_20260129_184111/results.csv) | NA |
| 20260129 | next_meta_modes_3m_20260129_183812 | MetaCDN/meta_reag | - | NA | NA | — | [res](sweeps/next_meta_modes_3m_20260129_183812/results.csv) | NA |
| 20260129 | next_meta_modes_3m_20260129_183751 | MetaCDN/meta_reag | - | NA | NA | — | [res](sweeps/next_meta_modes_3m_20260129_183751/results.csv) | NA |
| 20260110 | meta_mlp_vs_linear_20260110_181300 | MetaCDN/meta_reag | 2 | 0.384379 | 0.235512 | SAC linear score=mlp int=50 scale=1.0 | [res](sweeps/meta_mlp_vs_linear_20260110_181300/results.csv) |  |
| 20260108 | 1063_linear_only_20260108_115104 | TencentCBS/1063 | 1 | 0.356387 | 0.346686 | SAC linear score=linear int=50 scale=1.0 | [res](sweeps/1063_linear_only_20260108_115104/results.csv) |  |
| 20260107 | 1063_mlp_vs_linear_20260107_180946 | TencentCBS/1063 | 2 | 0.365308 | 0.357196 | SAC linear score=mlp int=50 scale=1.0 | [res](sweeps/1063_mlp_vs_linear_20260107_180946/results.csv) |  |
| 20260106 | 1063_core_rl_nowait_20260106_215817 | TencentCBS/1063 | 7 | 0.356964 | 0.346599 | SAC linear int=50 scale=1.0 | [res](sweeps/1063_core_rl_nowait_20260106_215817/results.csv) |  |
| 20260106 | sweep_20260106_153622 | TencentCBS/1063 | 6 | 0.437083 | 0.443746 | SAC pen=survival | [res](sweeps/sweep_20260106_153622/results.csv) |  |
| 20251231 | 1063_kitchensink_r1_20251231_144653 | TencentCBS/1063 | 7 | 0.376640 | 0.353541 | SAC linear norm=1 int=120 scale=1.5 cacheF=1 candF=1 | [res](sweeps/1063_kitchensink_r1_20251231_144653/results.csv) |  |
| 20251231 | 1063_cachefeat_r1_20251231_112906 | TencentCBS/1063 | 10 | 0.375308 | 0.354051 | SAC linear norm=1 int=120 scale=1.5 cacheF=1 | [res](sweeps/1063_cachefeat_r1_20251231_112906/results.csv) |  |
| 20251229 | 1063_featnorm_r1_20251229_140452 | TencentCBS/1063 | 11 | 0.376843 | 0.352218 | SAC linear norm=1 int=120 scale=1.0 | [res](sweeps/1063_featnorm_r1_20251229_140452/results.csv) |  |
| 20251226 | 1063_wide_r2_20251226_112012 | TencentCBS/1063 | 11 | 0.369881 | 0.327366 | A2C softmax log1p=1 norm=1 int=200 temp=1.7 scale=0.7 A2C_ns=256 A2C_lr=3e-4 A2C_ent=0.01 | [res](sweeps/1063_wide_r2_20251226_112012/results.csv) |  |
| 20251225 | 1063_wide_r1_20251225_215654 | TencentCBS/1063 | 11 | 0.369881 | 0.327366 | A2C softmax log1p=1 norm=1 int=200 temp=1.7 scale=0.7 A2C_ns=256 A2C_lr=3e-4 A2C_ent=0.01 | [res](sweeps/1063_wide_r1_20251225_215654/results.csv) |  |
| 20251225 | 1063_reward_penalty_r1_20251225_163358 | TencentCBS/1063 | 4 | 0.371939 | 0.328724 | PPO softmax log1p=1 norm=1 int=200 temp=1.6 scale=0.6 PPO_ns=2048 PPO_bs=256 PPO_lr=3e-4 PPO_ent=0.01 PPO_g=0.99 | [res](sweeps/1063_reward_penalty_r1_20251225_163358/results.csv) |  |
| 20251225 | 1063_quick_r1_20251225_110318 | TencentCBS/1063 | 5 | 0.371105 | 0.328755 | PPO softmax log1p=1 norm=1 int=200 temp=1.3 scale=0.5 PPO_ns=1024 PPO_bs=256 PPO_lr=3e-4 PPO_ent=0.0 PPO_g=0.99 | [res](sweeps/1063_quick_r1_20251225_110318/results.csv) |  |
| 20251225 | 1063_best_20251225_100313 | TencentCBS/1063 | 1 | 0.372756 | 0.329203 | SAC softmax log1p=1 norm=1 int=200 temp=1.3 scale=0.5 | [res](sweeps/1063_best_20251225_100313/results.csv) |  |
| 20251224 | meta_temp_interval_scale_aggr_r2_20251224_205809 | MetaCDN/meta_reag | 2 | 0.367958 | 0.217502 | SAC softmax log1p=1 norm=1 int=180 temp=1.5 scale=0.5 | [res](sweeps/meta_temp_interval_scale_aggr_r2_20251224_205809/results.csv) |  |
| 20251224 | meta_temp_scale_grid_r2_20251224_142147 | MetaCDN/meta_reag | 7 | 0.367958 | 0.217502 | SAC softmax log1p=1 norm=1 int=200 temp=1.4 scale=0.45 | [res](sweeps/meta_temp_scale_grid_r2_20251224_142147/results.csv) |  |
| 20251223 | meta_best_scale_fine_r2_20251223_110142 | MetaCDN/meta_reag | 5 | 0.367958 | 0.217548 | SAC softmax log1p=1 norm=1 int=200 temp=1.3 scale=0.65 | [res](sweeps/meta_best_scale_fine_r2_20251223_110142/results.csv) |  |
| 20251222 | meta_best_action_scale_winner_repeat5_20251222_201349 | MetaCDN/meta_reag | 1 | 0.367959 | 0.217551 | SAC softmax log1p=1 norm=1 int=200 temp=1.3 scale=0.5 | [res](sweeps/meta_best_action_scale_winner_repeat5_20251222_201349/results.csv) |  |
| 20251222 | meta_best_action_scale_r2_20251222_183925 | MetaCDN/meta_reag | 1 | 0.367959 | 0.217575 | SAC softmax log1p=1 norm=1 int=200 temp=1.3 scale=0.5 | [res](sweeps/meta_best_action_scale_r2_20251222_183925/results.csv) |  |
| 20251222 | meta_best_grid_winner_repeat5_20251222_102624 | MetaCDN/meta_reag | 1 | 0.367962 | 0.217582 | SAC softmax log1p=1 norm=1 int=200 temp=1.3 scale=1.0 | [res](sweeps/meta_best_grid_winner_repeat5_20251222_102624/results.csv) |  |
| 20251217 | meta_best_grid_interval_temp_r2_20251217_234028 | MetaCDN/meta_reag | 3 | 0.367961 | 0.217590 | SAC softmax log1p=1 norm=1 int=200 temp=1.3 scale=1.0 | [res](sweeps/meta_best_grid_interval_temp_r2_20251217_234028/results.csv) |  |
| 20251217 | meta_best_v5_idx6_repeat5_20251217_182945 | MetaCDN/meta_reag | 1 | 0.367968 | 0.217533 | SAC softmax log1p=1 norm=1 int=250 temp=1.0 scale=1.0 | [res](sweeps/meta_best_v5_idx6_repeat5_20251217_182945/results.csv) |  |
| 20251215 | meta_reward_algo_v4_tqc_only_fix_20251215_211951 | MetaCDN/meta_reag | 1 | 0.369536 | 0.216303 | TQC softmax log1p=1 norm=1 int=500 temp=0.3 scale=3.0 | [res](sweeps/meta_reward_algo_v4_tqc_only_fix_20251215_211951/results.csv) |  |
| 20251215 | meta_reward_algo_v4_20251215_145147 | MetaCDN/meta_reag | 1 | 0.367987 | 0.217459 | SAC softmax log1p=1 norm=1 int=500 temp=1.0 scale=1.0 | [res](sweeps/meta_reward_algo_v4_20251215_145147/results.csv) |  |
| 20251215 | meta_algo_expand_v6_1215_011924 | MetaCDN/meta_reag | 1 | 0.269697 | 0.164610 | SAC softmax log1p=1 norm=1 int=250 temp=1.0 scale=1.0 | [res](sweeps/meta_algo_expand_v6_1215_011924/results.csv) |  |
| 20251214 | meta_precision_refine_v5_1214_212442 | MetaCDN/meta_reag | 6 | 0.367980 | 0.217538 | SAC softmax log1p=1 norm=1 int=250 temp=1.0 scale=1.0 | [res](sweeps/meta_precision_refine_v5_1214_212442/results.csv) |  |
| 20251214 | meta_reward_algo_v4_fix_1214_014409 | MetaCDN/meta_reag | 1 | 0.368000 | 0.217450 | SAC softmax log1p=1 norm=1 int=500 | [res](sweeps/meta_reward_algo_v4_fix_1214_014409/results.csv) |  |
| 20251214 | meta_reward_algo_v4_1214_014136 | MetaCDN/meta_reag | - | NA | NA | — | [res](sweeps/meta_reward_algo_v4_1214_014136/results.csv) | NA |
| 20251214 | meta_try_candfeat_3m_1214_005451 | MetaCDN/meta_reag | 1 | 0.368000 | 0.217550 | SAC softmax log1p=1 norm=1 int=500 | [res](sweeps/meta_try_candfeat_3m_1214_005451/results.csv) |  |
| 20251214 | meta_try_cachefeat_3m_fix_1214_000103 | MetaCDN/meta_reag | 1 | 0.368000 | 0.217550 | SAC softmax log1p=1 norm=1 int=500 | [res](sweeps/meta_try_cachefeat_3m_fix_1214_000103/results.csv) |  |
| 20251213 | meta_try_cachefeat_3m_1213_234146 | MetaCDN/meta_reag | 2 | 0.368000 | 0.217500 | SAC softmax log1p=1 norm=1 int=500 cacheF=1 | [res](sweeps/meta_try_cachefeat_3m_1213_234146/results.csv) |  |
| 20251213 | meta_refine6_3m_v3_1213_214805 | MetaCDN/meta_reag | 2 | 0.368000 | 0.217450 | SAC softmax log1p=1 norm=1 int=500 | [res](sweeps/meta_refine6_3m_v3_1213_214805/results.csv) |  |
| 20251213 | meta_lower_omr_3m_v2_1213_135303 | MetaCDN/meta_reag | 6 | 0.368000 | 0.217500 | SAC softmax log1p=1 norm=1 int=500 | [res](sweeps/meta_lower_omr_3m_v2_1213_135303/results.csv) |  |
| 20251212 | meta_refine_user_3m_1212_160647 | MetaCDN/meta_reag | 4 | 0.368100 | 0.218200 | SAC softmax log1p=1 norm=1 cpd=1 irt=1 temp=0.7 scale=1.0 | [res](sweeps/meta_refine_user_3m_1212_160647/results.csv) |  |
| 20251212 | meta_3m_1212_152109 | MetaCDN/meta_reag | 1 | 0.383033 | 0.242300 | TD3 softmax scale=1.0 | [res](sweeps/meta_3m_1212_152109/results.csv) |  |
| 20251212 | seedfocus3m_1212_144046 | - | - | NA | NA | — | [res](sweeps/seedfocus3m_1212_144046/results.csv) | empty |
| 20251212 | seedfocus3m_1212_143747 | test_loh_comprehensive_10k.csv | - | NA | NA | — | [res](sweeps/seedfocus3m_1212_143747/results.csv) | NA |
| 20251212 | rec3m_1212_133521 | MetaCDN/meta_reag | 1 | 0.368500 | 0.219000 | TD3 softmax log1p=1 norm=1 cpd=1 irt=1 temp=1.0 scale=1.0 | [res](sweeps/rec3m_1212_133521/results.csv) |  |
| unknown | const_weights_mr_blocked | MetaCDN/meta_reag | - | 0.3680 | 0.2175 | LOH-mr-blocked const weights (Top20) | [docs](docs/sweep_results.md) | date 未记录 |
| unknown | const_weights_mr_blocked | WikiCDN/wiki_2019t | - | 0.5995 | 0.4778 | LOH-mr-blocked const weights (Top20) | [docs](docs/sweep_results.md) | date 未记录 |
| unknown | const_weights_mr_blocked | TencentCBS/1063 | - | 0.3971 | 0.3615 | LOH-mr-blocked const weights (Top20) | [docs](docs/sweep_results.md) | date 未记录 |
| unknown | legacy_sizebucket_weights | TencentCBS/1063 | 1 | 0.4369 | 0.5434 | size-buckets enabled, no transforms | [md](sweep_results.md) | date 未记录 |
| unknown | legacy_sizebucket_weights | MetaCDN/meta_reag | 1 | 0.3680 | 0.2186 | size-buckets enabled, no transforms | [md](sweep_results.md) | date 未记录 |
| unknown | legacy_sizebucket_weights | WikiCDN/wiki_2019t | 1 | 0.5940 | 0.4922 | size-buckets enabled, no transforms | [md](sweep_results.md) | date 未记录 |






<!-- ROOT_LOG_INDEX_BEGIN -->

### 根目录日志索引（cachesim_sb3_MMDD_HHMMSS.log）

说明：扫描仓库根目录下 `cachesim_sb3_MMDD_HHMMSS.log` / `ac_sb3_MMDD_HHMMSS.log`，按文件名推断日期（基于当前日期跨年），并从日志末尾的 `LOH-OMR ... miss ratio ... byte miss ratio ... throughput ... ` 汇总行提取 OMR/BMR/。

只保留 `req>=3000000` 的 runs；trace 内再按 `req` 分组。

| date | run | trace | req | OMR | BMR | cfg | ref | note |
| ---: | --- | --- | ---: | ---: | ---: | --- | --- | --- |
| 20260202 | 0202_3m_nosoftmax_tf1_gs1_ls1k | TencentCBS/1063 | 3000000 | 0.392134 | 0.361351 | SAC linear bound=5 scale=1 temp=0.3 ema=0 clip=0 rmode=absolute rscale=1 | [cs](cachesim_sb3_0202_3m_nosoftmax_tf1_gs1_ls1k.log) [ac](ac_sb3_0202_3m_nosoftmax_tf1_gs1_ls1k.log) | no-softmax + 更激进训练（tf=1 gs=1 ls=1000） |
| 20260202 | 0202_3m_nosoftmax_ab5_as1 | TencentCBS/1063 | 3000000 | 0.368934 | 0.346120 | SAC linear bound=5 scale=1 temp=0.3 ema=0 clip=0 rmode=absolute rscale=1 | [cs](cachesim_sb3_0202_3m_nosoftmax_ab5_as1.log) [ac](ac_sb3_0202_3m_nosoftmax_ab5_as1.log) | no-softmax |
| 20260202 | 0202_default16_norm1_ab5_mw05_1063 | TencentCBS/1063 | 3000000 | 0.390506 | 0.350576 | SAC softmax log1p=1 norm=1 cpd=1 irt=0 int=250 bound=5 scale=1 temp=1 ema=0.9 clip=1 rmode=delta rscale=10 mrw=0.5 tf=16 gs=1 | [cs](cachesim_sb3_0202_default16_norm1_ab5_mw05_1063.log) [ac](ac_sb3_0202_default16_norm1_ab5_mw05_1063.log) | 默认训练频率；build 开启 cacheF/candF/hitmiss/avgtopk |
| 20260202 | 0202_default16_norm1_ab1_mw10_1063 | TencentCBS/1063 | 3000000 | 0.402147 | 0.364733 | SAC softmax log1p=1 norm=1 cpd=1 irt=0 int=250 bound=1 scale=1 temp=1 ema=0.9 clip=1 rmode=delta rscale=10 mrw=1.0 tf=16 gs=1 | [cs](cachesim_sb3_0202_default16_norm1_ab1_mw10_1063.log) [ac](ac_sb3_0202_default16_norm1_ab1_mw10_1063.log) | 默认训练频率；build 开启 cacheF/candF/hitmiss/avgtopk |
| 20260202 | 0202_delta_softmax_ema_1063 | TencentCBS/1063 | 3000000 | 0.370991 | 0.332388 | SAC softmax log1p=1 norm=1 cpd=1 irt=0 int=250 bound=5 scale=1 temp=1 ema=0.9 clip=1 rmode=delta rscale=10 tf=1 gs=1 | [cs](cachesim_sb3_0202_delta_softmax_ema_1063.log) [ac](ac_sb3_0202_delta_softmax_ema_1063.log) | 非默认训练频率（tf=1 ls=1000） |
| 20260202 | 0202_delta_softmax_ema_norm_1063 | TencentCBS/1063 | 3000000 | 0.373982 | 0.334880 | SAC softmax log1p=1 norm=1 cpd=1 irt=0 int=250 bound=5 scale=1 temp=1 ema=0.9 clip=1 rmode=delta rscale=1 tf=1 gs=1 | [cs](cachesim_sb3_0202_delta_softmax_ema_norm_1063.log) [ac](ac_sb3_0202_delta_softmax_ema_norm_1063.log) | 非默认训练频率（tf=1 ls=1000） |
| 20260202 | 0202_delta_1063 | TencentCBS/1063 | 3000000 | 0.372395 | 0.344350 | SAC softmax log1p=1 norm=1 cpd=1 irt=0 int=200 bound=5 scale=1 temp=0.3 ema=0 clip=0 rmode=delta rscale=10 tf=1 gs=1 | [cs](cachesim_sb3_0202_delta_1063.log) [ac](ac_sb3_0202_delta_1063.log) | 非默认训练频率（tf=1 ls=1000） |
| 20260202 | 0202_abs_1063 | TencentCBS/1063 | 3000000 | 0.403911 | 0.377714 | SAC softmax log1p=1 norm=1 cpd=1 irt=0 int=200 bound=5 scale=1 temp=0.3 ema=0 clip=0 rmode=absolute rscale=10 tf=1 gs=1 | [cs](cachesim_sb3_0202_abs_1063.log) [ac](ac_sb3_0202_abs_1063.log) | 非默认训练频率（tf=1 ls=1000） |
| 20260202 | 0202_fixdims_compound_delta_as12_t03_ema_riu250_1063 | TencentCBS/1063 | 3000000 | 0.388787 | 0.349349 | SAC softmax log1p=1 norm=0 cpd=1 irt=0 int=250 bound=1 scale=12 temp=0.3 ema=0.9 clip=1 rmode=delta rscale=10 tf=16 gs=1 | [cs](cachesim_sb3_0202_fixdims_compound_delta_as12_t03_ema_riu250_1063.log) [ac](ac_sb3_0202_fixdims_compound_delta_as12_t03_ema_riu250_1063.log) | fixdims + norm=0 |
| 20260202 | 0202_fixdims_compound_delta_softmax_ema_riu125_1063 | TencentCBS/1063 | 3000000 | 0.388929 | 0.348748 | SAC softmax log1p=1 norm=0 cpd=1 irt=0 int=125 bound=1 scale=1 temp=1 ema=0.9 clip=1 rmode=delta rscale=10 tf=16 gs=1 | [cs](cachesim_sb3_0202_fixdims_compound_delta_softmax_ema_riu125_1063.log) [ac](ac_sb3_0202_fixdims_compound_delta_softmax_ema_riu125_1063.log) | fixdims + norm=0 |
| 20260202 | 0202_fixdims_compound_delta_softmax_ema_riu500_1063 | TencentCBS/1063 | 3000000 | 0.387517 | 0.347069 | SAC softmax log1p=1 norm=0 cpd=1 irt=0 int=500 bound=1 scale=1 temp=1 ema=0.9 clip=1 rmode=delta rscale=10 tf=16 gs=1 | [cs](cachesim_sb3_0202_fixdims_compound_delta_softmax_ema_riu500_1063.log) [ac](ac_sb3_0202_fixdims_compound_delta_softmax_ema_riu500_1063.log) | fixdims + norm=0 |
| 20260202 | 0202_fixdims_compound_delta_softmax_ema_riu1000_1063 | TencentCBS/1063 | 3000000 | 0.388983 | 0.348513 | SAC softmax log1p=1 norm=0 cpd=1 irt=0 int=1000 bound=1 scale=1 temp=1 ema=0.9 clip=1 rmode=delta rscale=10 tf=16 gs=1 | [cs](cachesim_sb3_0202_fixdims_compound_delta_softmax_ema_riu1000_1063.log) [ac](ac_sb3_0202_fixdims_compound_delta_softmax_ema_riu1000_1063.log) | fixdims + norm=0 |
| 20260202 | 0202_delta_softmax_ema_riu500_1063 | TencentCBS/1063 | 3000000 | 0.428394 | 0.398577 | SAC softmax log1p=0 norm=0 cpd=0 irt=1 int=500 bound=1 scale=1 temp=1 ema=0.9 clip=1 rmode=delta rscale=10 tf=16 gs=1 | [cs](cachesim_sb3_0202_delta_softmax_ema_riu500_1063.log) [ac](ac_sb3_0202_delta_softmax_ema_riu500_1063.log) | irt=1 + 无 transforms；state=134/134 |
| 20260201 | 0201_3m_ab1_as12_t03 | TencentCBS/1063 | 3000000 | 0.369784 | 0.334838 | SAC softmax bound=1 scale=12 temp=0.3 ema=0 clip=0 rmode=absolute rscale=1 | [cs](cachesim_sb3_0201_3m_ab1_as12_t03.log) [ac](ac_sb3_0201_3m_ab1_as12_t03.log) | sharp softmax |
| 20260130 | 0130_001255 | WikiCDN/wiki_2019t | 3000000 | 0.595834 | 0.475232 | SAC log1p=1 norm=1 cpd=1 irt=0 cacheF=0 candF=0 int=1000 | [cs](cachesim_sb3_0130_001255.log) [ac](ac_sb3_0130_001255.log) |  |
| 20260130 | 0130_001022 | TencentCBS/1063 | 3000000 | 0.377418 | 0.344870 | SAC log1p=1 norm=1 cpd=0 irt=1 cacheF=0 candF=0 int=1000 | [cs](cachesim_sb3_0130_001022.log) [ac](ac_sb3_0130_001022.log) |  |
| 20260130 | 0130_000700 | TencentCBS/1063 | 3000000 | 0.376553 | 0.344642 | SAC log1p=1 norm=1 cpd=0 irt=1 cacheF=0 candF=0 int=1000 | [cs](cachesim_sb3_0130_000700.log) [ac](ac_sb3_0130_000700.log) |  |
| 20260130 | 0130_000535 | MetaCDN/meta_reag | 3000000 | 0.415580 | 0.238538 | SAC log1p=1 norm=1 cpd=0 irt=1 cacheF=0 candF=0 int=1000 | [cs](cachesim_sb3_0130_000535.log) [ac](ac_sb3_0130_000535.log) |  |
| 20260129 | 0129_210218 | MetaCDN/meta_reag | 3000000 | 0.372619 | 0.216890 | SAC log1p=1 norm=1 cpd=0 irt=0 cacheF=0 candF=0 int=250 | [cs](cachesim_sb3_0129_210218.log) [ac](ac_sb3_0129_210218.log) |  |
| 20260129 | 0129_203548 | MetaCDN/meta_reag | 3000000 | 0.367969 | 0.217511 | SAC log1p=1 norm=1 cpd=0 irt=0 cacheF=0 candF=0 int=250 | [cs](cachesim_sb3_0129_203548.log) [ac](ac_sb3_0129_203548.log) |  |
| 20251214 | 1214_211604 | MetaCDN/meta_reag | 3000000 | 0.367988 | 0.217458 | SAC log1p=1 norm=1 cpd=0 irt=0 cacheF=0 candF=0 int=500 | [cs](cachesim_sb3_1214_211604.log) [ac](ac_sb3_1214_211604.log) |  |
| 20251214 | 1214_211231 | MetaCDN/meta_reag | 3000000 | 0.367997 | 0.217405 | SAC log1p=1 norm=1 cpd=0 irt=0 cacheF=0 candF=0 int=500 | [cs](cachesim_sb3_1214_211231.log) [ac](ac_sb3_1214_211231.log) |  |
| 20251214 | 1214_210536 | MetaCDN/meta_reag | 3000000 | 0.367998 | 0.217400 | SAC log1p=1 norm=1 cpd=0 irt=0 cacheF=0 candF=0 int=500 | [cs](cachesim_sb3_1214_210536.log) [ac](ac_sb3_1214_210536.log) |  |
| 20251214 | 1214_205956 | MetaCDN/meta_reag | 3000000 | 0.3680 | 0.217603 | SAC log1p=1 norm=1 cpd=0 irt=0 cacheF=0 candF=0 int=500 | [cs](cachesim_sb3_1214_205956.log) [ac](ac_sb3_1214_205956.log) |  |
| 20251212 | 1212_115506 | MetaCDN/meta_reag | 3000000 | 0.3685 | 0.2177 | TD3 log1p=1 norm=1 cpd=1 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1212_115506.log) [ac](ac_sb3_1212_115506.log) |  |
| 20251212 | 1212_113901 | MetaCDN/meta_reag | 3000000 | 0.3691 | 0.2173 | PPO_LSTM log1p=1 norm=1 cpd=1 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1212_113901.log) [ac](ac_sb3_1212_113901.log) |  |
| 20251212 | 1212_113231 | WikiCDN/wiki_2019t | 3000000 | 0.5945 | 0.4766 | PPO log1p=1 norm=1 cpd=1 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1212_113231.log) [ac](ac_sb3_1212_113231.log) |  |
| 20251212 | 1212_112245 | WikiCDN/wiki_2019t | 3000000 | 0.5949 | 0.4776 | PPO_LSTM log1p=1 norm=1 cpd=1 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1212_112245.log) [ac](ac_sb3_1212_112245.log) |  |
| 20251209 | 1209_010657 | TencentCBS/1063 | 360960512 | 0.2756 | 0.2486 | log1p=1 norm=1 cpd=1 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1209_010657.log) |  |
| 20251208 | 1208_221200 | TencentCBS/1063 | 3000000 | 0.9075 | 0.9067 | PPO log1p=1 norm=1 cpd=1 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_221200.log) [ac](ac_sb3_1208_221200.log) |  |
| 20251208 | 1208_215501 | WikiCDN/wiki_2019t | 3000000 | 0.9369 | 0.9284 | PPO log1p=1 norm=1 cpd=1 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_215501.log) [ac](ac_sb3_1208_215501.log) |  |
| 20251208 | 1208_214431 | MetaCDN/meta_reag | 3000000 | 0.4496 | 0.2550 | PPO log1p=1 norm=1 cpd=1 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_214431.log) [ac](ac_sb3_1208_214431.log) |  |
| 20251208 | 1208_180321 | WikiCDN/wiki_2019t | 3000000 | 0.5962 | 0.4947 | PPO log1p=1 norm=1 cpd=1 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_180321.log) [ac](ac_sb3_1208_180321.log) |  |
| 20251208 | 1208_180301 | WikiCDN/wiki_2019t | 3000000 | 0.6224 | 0.5144 | PPO log1p=1 norm=1 cpd=1 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_180301.log) [ac](ac_sb3_1208_180301.log) |  |
| 20251208 | 1208_180236 | WikiCDN/wiki_2019t | 3000000 | 0.5951 | 0.4740 | PPO log1p=1 norm=1 cpd=1 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_180236.log) [ac](ac_sb3_1208_180236.log) |  |
| 20251208 | 1208_180213 | WikiCDN/wiki_2019t | 3000000 | 0.7006 | 0.5939 | PPO log1p=1 norm=1 cpd=1 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_180213.log) [ac](ac_sb3_1208_180213.log) |  |
| 20251208 | 1208_180136 | WikiCDN/wiki_2019t | 3000000 | 0.6468 | 0.5463 | PPO log1p=1 norm=1 cpd=1 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_180136.log) [ac](ac_sb3_1208_180136.log) |  |
| 20251208 | 1208_180113 | WikiCDN/wiki_2019t | 3000000 | 0.5956 | 0.4763 | PPO log1p=1 norm=1 cpd=1 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_180113.log) [ac](ac_sb3_1208_180113.log) |  |
| 20251208 | 1208_180037 | MetaCDN/meta_reag | 3000000 | 0.3683 | 0.2212 | PPO log1p=1 norm=1 cpd=1 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_180037.log) [ac](ac_sb3_1208_180037.log) |  |
| 20251208 | 1208_175953 | MetaCDN/meta_reag | 3000000 | 0.3687 | 0.2176 | PPO log1p=1 norm=1 cpd=1 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_175953.log) [ac](ac_sb3_1208_175953.log) |  |
| 20251208 | 1208_175816 | MetaCDN/meta_reag | 3000000 | 0.4200 | 0.2244 | PPO log1p=1 norm=1 cpd=1 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_175816.log) [ac](ac_sb3_1208_175816.log) |  |
| 20251208 | 1208_175534 | MetaCDN/meta_reag | 3000000 | 0.3684 | 0.2377 | PPO log1p=1 norm=1 cpd=1 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_175534.log) [ac](ac_sb3_1208_175534.log) |  |
| 20251208 | 1208_174737 | MetaCDN/meta_reag | 3000000 | 0.3742 | 0.2155 | PPO log1p=1 norm=1 cpd=1 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_174737.log) [ac](ac_sb3_1208_174737.log) |  |
| 20251208 | 1208_172033 | MetaCDN/meta_reag | 3000000 | 0.3694 | 0.2163 | PPO log1p=1 norm=1 cpd=1 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_172033.log) [ac](ac_sb3_1208_172033.log) |  |
| 20251208 | 1208_171331 | WikiCDN/wiki_2019t | 3000000 | 0.5942 | 0.4768 | PPO log1p=1 norm=1 cpd=1 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_171331.log) [ac](ac_sb3_1208_171331.log) |  |
| 20251208 | 1208_165353 | WikiCDN/wiki_2019t | 3000000 | 0.5949 | 0.4780 | PPO log1p=1 norm=1 cpd=1 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_165353.log) [ac](ac_sb3_1208_165353.log) |  |
| 20251208 | 1208_164957 | MetaCDN/meta_reag | 3000000 | 0.3694 | 0.2163 | PPO log1p=1 norm=1 cpd=1 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_164957.log) [ac](ac_sb3_1208_164957.log) |  |
| 20251208 | 1208_163327 | MetaCDN/meta_reag | 3000000 | 0.3915 | 0.2206 | PPO log1p=1 norm=1 cpd=1 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_163327.log) [ac](ac_sb3_1208_163327.log) |  |
| 20251208 | 1208_113816 | WikiCDN/wiki_2019t | 207646002 | 0.1889 | 0.1337 | PPO log1p=1 norm=1 cpd=1 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_113816.log) [ac](ac_sb3_1208_113816.log) |  |
| 20251208 | 1208_103353 | TencentCBS/1063 | 3000000 | 0.3711 | 0.3308 | PPO cpd=1 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_103353.log) [ac](ac_sb3_1208_103353.log) |  |
| 20251208 | 1208_100023 | MetaCDN/meta_reag | 45623306 | 0.2735 | 0.1629 | PPO cpd=1 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_100023.log) [ac](ac_sb3_1208_100023.log) |  |
| 20251208 | 1208_095510 | WikiCDN/wiki_2019t | 3000000 | 0.6407 | 0.5507 | PPO cpd=1 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_095510.log) [ac](ac_sb3_1208_095510.log) |  |
| 20251208 | 1208_095231 | MetaCDN/meta_reag | 3000000 | 0.3976 | 0.2350 | PPO cpd=1 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_095231.log) [ac](ac_sb3_1208_095231.log) |  |
| 20251208 | 1208_094831 | WikiCDN/wiki_2019t | 3000000 | 0.5938 | 0.4759 | PPO cpd=1 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_094831.log) [ac](ac_sb3_1208_094831.log) |  |
| 20251208 | 1208_094611 | MetaCDN/meta_reag | 3000000 | 0.3692 | 0.2165 | PPO cpd=1 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_094611.log) [ac](ac_sb3_1208_094611.log) |  |
| 20251208 | 1208_032052 | MetaCDN/meta_reag | 3000000 | 0.3902 | 0.2277 | PPO cpd=0 irt=1 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_032052.log) [ac](ac_sb3_1208_032052.log) |  |
| 20251208 | 1208_031028 | WikiCDN/wiki_2019t | 3000000 | 0.6429 | 0.5591 | PPO cpd=0 irt=1 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_031028.log) [ac](ac_sb3_1208_031028.log) |  |
| 20251208 | 1208_025733 | WikiCDN/wiki_2019t | 3000000 | 0.6434 | 0.5529 | PPO cpd=0 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_025733.log) [ac](ac_sb3_1208_025733.log) |  |
| 20251208 | 1208_024310 | MetaCDN/meta_reag | 3000000 | 0.3973 | 0.2363 | PPO cpd=0 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_024310.log) [ac](ac_sb3_1208_024310.log) |  |
| 20251208 | 1208_022958 | MetaCDN/meta_reag | 3000000 | 0.3724 | 0.2161 | SAC cpd=0 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_022958.log) [ac](ac_sb3_1208_022958.log) |  |
| 20251208 | 1208_021438 | MetaCDN/meta_reag | 3000000 | 0.4104 | 0.2294 | PPO cpd=0 irt=1 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_021438.log) [ac](ac_sb3_1208_021438.log) |  |
| 20251208 | 1208_020748 | WikiCDN/wiki_2019t | 3000000 | 0.5934 | 0.4756 | PPO cpd=0 irt=1 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_020748.log) [ac](ac_sb3_1208_020748.log) |  |
| 20251208 | 1208_013151 | WikiCDN/wiki_2019t | 3000000 | 0.6298 | 0.5275 | PPO cpd=0 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_013151.log) [ac](ac_sb3_1208_013151.log) |  |
| 20251208 | 1208_011625 | MetaCDN/meta_reag | 3000000 | 0.3762 | 0.2154 | PPO cpd=0 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_011625.log) [ac](ac_sb3_1208_011625.log) |  |
| 20251206 | 1206_030519 | MetaCDN/meta_reag | 3000000 | 0.3784 | 0.2172 | PPO cpd=0 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1206_030519.log) [ac](ac_sb3_1206_030519.log) |  |
| 20251204 | 1204_102246 | MetaCDN/meta_reag | 3000000 | 0.4202 | 0.2315 | PPO int=200 | [cs](cachesim_sb3_1204_102246.log) [ac](ac_sb3_1204_102246.log) |  |
| 20251204 | 1204_020125 | WikiCDN/wiki_2019t | 3000000 | 0.5933 | 0.4754 | PPO int=200 | [cs](cachesim_sb3_1204_020125.log) [ac](ac_sb3_1204_020125.log) |  |
| 20251202 | 1202_181054 | WikiCDN/wiki_2019t | 3000000 | 0.5948 | 0.4759 | PPO_LSTM int=200 | [cs](cachesim_sb3_1202_181054.log) [ac](ac_sb3_1202_181054.log) |  |
| 20251202 | 1202_175648 | MetaCDN/meta_reag | 3000000 | 0.4157 | 0.2306 | PPO_LSTM int=200 | [cs](cachesim_sb3_1202_175648.log) [ac](ac_sb3_1202_175648.log) |  |
| 20251202 | 1202_174503 | MetaCDN/meta_reag | 3000000 | 0.4185 | 0.2303 | PPO int=200 | [cs](cachesim_sb3_1202_174503.log) [ac](ac_sb3_1202_174503.log) |  |
| 20251202 | 1202_164231 | MetaCDN/meta_reag | 3000000 | 0.4197 | 0.2304 | PPO_LSTM int=200 | [cs](cachesim_sb3_1202_164231.log) [ac](ac_sb3_1202_164231.log) |  |
| 20251202 | 1202_155720 | MetaCDN/meta_reag | 3000000 | 0.4189 | 0.2313 | PPO_LSTM int=200 | [cs](cachesim_sb3_1202_155720.log) [ac](ac_sb3_1202_155720.log) |  |
| 20251202 | 1202_155326 | MetaCDN/meta_reag | 3000000 | 0.4169 | 0.2305 | PPO int=200 | [cs](cachesim_sb3_1202_155326.log) [ac](ac_sb3_1202_155326.log) |  |
| 20251202 | 1202_154811 | WikiCDN/wiki_2019t | 3000000 | 0.5954 | 0.4765 | PPO int=200 | [cs](cachesim_sb3_1202_154811.log) [ac](ac_sb3_1202_154811.log) |  |
| 20251202 | 1202_154004 | WikiCDN/wiki_2019t | 3000000 | 0.5949 | 0.4758 | PPO_LSTM int=200 | [cs](cachesim_sb3_1202_154004.log) [ac](ac_sb3_1202_154004.log) |  |
| 20251201 | 1201_224555 | WikiCDN/wiki_2019t | 3000000 | 0.6381 | 0.5584 | SAC int=200 | [cs](cachesim_sb3_1201_224555.log) [ac](ac_sb3_1201_224555.log) |  |
| 20251201 | 1201_223820 | MetaCDN/meta_reag | 3000000 | 0.3987 | 0.2286 | SAC int=200 | [cs](cachesim_sb3_1201_223820.log) [ac](ac_sb3_1201_223820.log) |  |
| 20251201 | 1201_220435 | MetaCDN/meta_reag | 3000000 | 0.4087 | 0.2250 | PPO int=200 | [cs](cachesim_sb3_1201_220435.log) [ac](ac_sb3_1201_220435.log) |  |
| 20251201 | 1201_215616 | MetaCDN/meta_reag | 3000000 | 0.4094 | 0.2256 | PPO int=200 | [cs](cachesim_sb3_1201_215616.log) [ac](ac_sb3_1201_215616.log) |  |
| 20251201 | 1201_215107 | WikiCDN/wiki_2019t | 3000000 | 0.5950 | 0.4966 | PPO int=200 | [cs](cachesim_sb3_1201_215107.log) [ac](ac_sb3_1201_215107.log) |  |
| 20251201 | 1201_153642 | WikiCDN/wiki_2019t | 3000000 | 0.5960 | 0.4954 | PPO int=200 | [cs](cachesim_sb3_1201_153642.log) [ac](ac_sb3_1201_153642.log) |  |
| 20251201 | 1201_151211 | MetaCDN/meta_reag | 3000000 | 0.4079 | 0.2254 | PPO int=200 | [cs](cachesim_sb3_1201_151211.log) [ac](ac_sb3_1201_151211.log) |  |
| 20251201 | 1201_112038 | MetaCDN/meta_reag | 3000000 | 0.4091 | 0.2255 | PPO int=200 | [cs](cachesim_sb3_1201_112038.log) [ac](ac_sb3_1201_112038.log) |  |
| 20251201 | 1201_105056 | WikiCDN/wiki_2019t | 3000000 | 0.5952 | 0.4940 | PPO int=200 | [cs](cachesim_sb3_1201_105056.log) [ac](ac_sb3_1201_105056.log) |  |
| 20251129 | 1129_182809 | MetaCDN/meta_reag | 45623306 | 0.3217 | 0.1746 | PPO int=200 | [cs](cachesim_sb3_1129_182809.log) [ac](ac_sb3_1129_182809.log) |  |
| 20251129 | 1129_182010 | MetaCDN/meta_reag | 3000000 | 0.4171 | 0.2302 | PPO int=200 | [cs](cachesim_sb3_1129_182010.log) [ac](ac_sb3_1129_182010.log) |  |
| 20251129 | 1129_181308 | MetaCDN/meta_reag | 3000000 | 0.4075 | 0.2259 | PPO int=200 | [cs](cachesim_sb3_1129_181308.log) [ac](ac_sb3_1129_181308.log) |  |
| 20251129 | 1129_180836 | WikiCDN/wiki_2019t | 3000000 | 0.5931 | 0.4905 | PPO int=200 | [cs](cachesim_sb3_1129_180836.log) [ac](ac_sb3_1129_180836.log) |  |
| 20251129 | 1129_172109 | MetaCDN/meta_reag | 3000000 | 0.4070 | 0.2266 | PPO int=200 | [cs](cachesim_sb3_1129_172109.log) [ac](ac_sb3_1129_172109.log) |  |
| 20251129 | 1129_171412 | WikiCDN/wiki_2019t | 3000000 | 0.5944 | 0.4922 | PPO int=200 | [cs](cachesim_sb3_1129_171412.log) [ac](ac_sb3_1129_171412.log) |  |
| 20251129 | 1129_170408 | WikiCDN/wiki_2019t | 3000000 | 0.6396 | 0.5603 | PPO int=200 | [cs](cachesim_sb3_1129_170408.log) [ac](ac_sb3_1129_170408.log) |  |
| 20251129 | 1129_164608 | WikiCDN/wiki_2019t | 3000000 | 0.5945 | 0.4760 | PPO int=200 | [cs](cachesim_sb3_1129_164608.log) [ac](ac_sb3_1129_164608.log) |  |
| 20251129 | 1129_161807 | WikiCDN/wiki_2019t | 3000000 | 0.6392 | 0.5598 | PPO int=200 | [cs](cachesim_sb3_1129_161807.log) [ac](ac_sb3_1129_161807.log) |  |


| date | run | trace | req | OMR | BMR | cfg | ref | note |
| ---: | --- | --- | ---: | ---: | ---: | --- | --- | --- |
| 20251129 | 1129_161147 | WikiCDN/wiki_2019t | 3000000 | 0.6387 | 0.5595 | PPO int=200 | [cs](cachesim_sb3_1129_161147.log) [ac](ac_sb3_1129_161147.log) |  |
| 20251129 | 1129_155418 | MetaCDN/meta_reag | 3000000 | 0.3968 | 0.2296 | PPO int=200 | [cs](cachesim_sb3_1129_155418.log) [ac](ac_sb3_1129_155418.log) |  |
| 20251129 | 1129_154732 | WikiCDN/wiki_2019t | 3000000 | 0.6385 | 0.5569 | PPO int=200 | [cs](cachesim_sb3_1129_154732.log) [ac](ac_sb3_1129_154732.log) |  |
| 20251129 | 1129_152328 | MetaCDN/meta_reag | 3000000 | 0.3993 | 0.2279 | PPO int=200 | [cs](cachesim_sb3_1129_152328.log) [ac](ac_sb3_1129_152328.log) |  |
| 20251129 | 1129_151819 | WikiCDN/wiki_2019t | 3000000 | 0.6409 | 0.5583 | PPO int=200 | [cs](cachesim_sb3_1129_151819.log) [ac](ac_sb3_1129_151819.log) |  |
| 20251128 | 1128_181003 | MetaCDN/meta_reag | 45623306 | 0.3378 | 0.1776 | PPO int=200 | [cs](cachesim_sb3_1128_181003.log) [ac](ac_sb3_1128_181003.log) |  |
| 20251128 | 1128_175715 | WikiCDN/wiki_2019t | 3000000 | 0.5932 | 0.4750 | PPO int=200 | [cs](cachesim_sb3_1128_175715.log) [ac](ac_sb3_1128_175715.log) |  |
| 20251128 | 1128_174927 | MetaCDN/meta_reag | 3000000 | 0.4193 | 0.2305 | PPO int=200 | [cs](cachesim_sb3_1128_174927.log) [ac](ac_sb3_1128_174927.log) |  |
| 20251128 | 1128_172319 | MetaCDN/meta_reag | 3000000 | 0.4170 | 0.2307 | PPO int=200 | [cs](cachesim_sb3_1128_172319.log) [ac](ac_sb3_1128_172319.log) |  |
| 20251128 | 1128_153856 | MetaCDN/meta_reag | 3000000 | 0.4177 | 0.2307 | PPO int=200 | [cs](cachesim_sb3_1128_153856.log) [ac](ac_sb3_1128_153856.log) |  |
| 20251128 | 1128_152938 | WikiCDN/wiki_2019t | 3000000 | 0.5924 | 0.4764 | PPO int=200 | [cs](cachesim_sb3_1128_152938.log) [ac](ac_sb3_1128_152938.log) |  |
| 20251128 | 1128_014635 | MetaCDN/meta_reag | 45623306 | 0.3592 | 0.1874 | PPO int=200 | [cs](cachesim_sb3_1128_014635.log) [ac](ac_sb3_1128_014635.log) |  |
| 20251128 | 1128_013716 | WikiCDN/wiki_2019t | 3000000 | 0.6005 | 0.4743 | PPO int=200 | [cs](cachesim_sb3_1128_013716.log) [ac](ac_sb3_1128_013716.log) |  |
| 20251128 | 1128_011929 | WikiCDN/wiki_2019t | 3000000 | 0.6093 | 0.4869 | PPO int=200 | [cs](cachesim_sb3_1128_011929.log) [ac](ac_sb3_1128_011929.log) |  |
| 20251128 | 1128_005757 | WikiCDN/wiki_2019t | 3000000 | 0.6038 | 0.4777 | PPO int=200 | [cs](cachesim_sb3_1128_005757.log) [ac](ac_sb3_1128_005757.log) |  |
| 20251128 | 1128_004348 | WikiCDN/wiki_2019t | 3000000 | 0.6489 | 0.5464 | PPO int=200 | [cs](cachesim_sb3_1128_004348.log) [ac](ac_sb3_1128_004348.log) |  |
| 20251127 | 1127_234506 | WikiCDN/wiki_2019t | 3000000 | 0.6005 | 0.4739 | PPO int=200 | [cs](cachesim_sb3_1127_234506.log) [ac](ac_sb3_1127_234506.log) |  |
| 20251127 | 1127_234011 | MetaCDN/meta_reag | 3000000 | 0.4247 | 0.2332 | PPO int=200 | [cs](cachesim_sb3_1127_234011.log) [ac](ac_sb3_1127_234011.log) |  |
| 20251127 | 1127_223446 | MetaCDN/meta_reag | 3000000 | 0.4193 | 0.2340 | PPO int=200 | [cs](cachesim_sb3_1127_223446.log) [ac](ac_sb3_1127_223446.log) |  |
| 20251127 | 1127_204730 | WikiCDN/wiki_2019t | 3000000 | 0.6045 | 0.4760 | PPO int=200 | [cs](cachesim_sb3_1127_204730.log) [ac](ac_sb3_1127_204730.log) |  |
| 20251127 | 1127_203955 | WikiCDN/wiki_2019t | 3000000 | 0.5999 | 0.4724 | PPO int=200 | [cs](cachesim_sb3_1127_203955.log) [ac](ac_sb3_1127_203955.log) |  |
| 20251127 | 1127_201436 | WikiCDN/wiki_2019t | 3000000 | 0.6026 | 0.4765 | PPO int=200 | [cs](cachesim_sb3_1127_201436.log) [ac](ac_sb3_1127_201436.log) |  |
| 20251127 | 1127_200604 | MetaCDN/meta_reag | 3000000 | 0.4242 | 0.2339 | SAC int=200 | [cs](cachesim_sb3_1127_200604.log) [ac](ac_sb3_1127_200604.log) |  |
| 20251127 | 1127_195505 | WikiCDN/wiki_2019t | 3000000 | 0.6012 | 0.4736 | SAC int=200 | [cs](cachesim_sb3_1127_195505.log) [ac](ac_sb3_1127_195505.log) |  |
| 20251127 | 1127_193851 | MetaCDN/meta_reag | 3000000 | 0.4272 | 0.2338 | SAC int=200 | [cs](cachesim_sb3_1127_193851.log) [ac](ac_sb3_1127_193851.log) |  |
| 20251127 | 1127_180428 | WikiCDN/wiki_2019t | 3000000 | 0.6019 | 0.4742 | SAC int=200 | [cs](cachesim_sb3_1127_180428.log) [ac](ac_sb3_1127_180428.log) |  |
| 20251127 | 1127_111716 | WikiCDN/wiki_2019t | 3000000 | 0.6019 | 0.4742 | SAC int=200 | [cs](cachesim_sb3_1127_111716.log) [ac](ac_sb3_1127_111716.log) |  |
| 20251126 | 1126_184728 | MetaCDN/meta_reag | 3000000 | 0.4275 | 0.2341 | SAC int=200 | [cs](cachesim_sb3_1126_184728.log) [ac](ac_sb3_1126_184728.log) |  |
| 20251126 | 1126_183124 | WikiCDN/wiki_2019t | 3000000 | 0.6020 | 0.4744 | SAC int=200 | [cs](cachesim_sb3_1126_183124.log) [ac](ac_sb3_1126_183124.log) |  |
| 20251125 | 1125_195648 | MetaCDN/meta_reag | 3000000 | 0.4239 | 0.2320 | int=200 | [cs](cachesim_sb3_1125_195648.log) [ac](ac_sb3_1125_195648.log) |  |
| 20251125 | 1125_195436 | MetaCDN/meta_reag | 3000000 | 0.4238 | 0.2316 | int=200 | [cs](cachesim_sb3_1125_195436.log) [ac](ac_sb3_1125_195436.log) |  |
| 20251125 | 1125_195201 | MetaCDN/meta_reag | 3000000 | 0.4265 | 0.2332 | int=200 | [cs](cachesim_sb3_1125_195201.log) [ac](ac_sb3_1125_195201.log) |  |
| 20251125 | 1125_192821 | WikiCDN/wiki_2019t | 3000000 | 0.6015 | 0.4739 | int=200 | [cs](cachesim_sb3_1125_192821.log) [ac](ac_sb3_1125_192821.log) |  |
| 20251125 | 1125_192214 | WikiCDN/wiki_2019t | 3000000 | 0.6031 | 0.4758 | int=200 | [cs](cachesim_sb3_1125_192214.log) [ac](ac_sb3_1125_192214.log) |  |
| 20251125 | 1125_191855 | WikiCDN/wiki_2019t | 3000000 | 0.6008 | 0.4734 | int=200 | [cs](cachesim_sb3_1125_191855.log) [ac](ac_sb3_1125_191855.log) |  |
| 20251124 | 1124_173556 | WikiCDN/wiki_2019t | 3000000 | 0.6011 | 0.4738 | int=200 | [cs](cachesim_sb3_1124_173556.log) [ac](ac_sb3_1124_173556.log) |  |
| 20251124 | 1124_170730 | MetaCDN/meta_reag | 3000000 | 0.4257 | 0.2328 | int=200 | [cs](cachesim_sb3_1124_170730.log) [ac](ac_sb3_1124_170730.log) |  |
| 20251124 | 1124_170424 | MetaCDN/meta_reag | 3000000 | 0.4234 | 0.2317 | int=200 | [cs](cachesim_sb3_1124_170424.log) [ac](ac_sb3_1124_170424.log) |  |
| 20251124 | 1124_170207 | MetaCDN/meta_reag | 3000000 | 0.4259 | 0.2324 | int=200 | [cs](cachesim_sb3_1124_170207.log) [ac](ac_sb3_1124_170207.log) |  |
| 20251124 | 1124_162845 | MetaCDN/meta_reag | 3000000 | 0.4045 | 0.2240 | int=200 | [cs](cachesim_sb3_1124_162845.log) [ac](ac_sb3_1124_162845.log) |  |
| 20251124 | 1124_162539 | MetaCDN/meta_reag | 3000000 | 0.4270 | 0.2337 | int=200 | [cs](cachesim_sb3_1124_162539.log) [ac](ac_sb3_1124_162539.log) |  |
| 20251124 | 1124_162416 | MetaCDN/meta_reag | 3000000 | 0.4283 | 0.2344 | int=200 | [cs](cachesim_sb3_1124_162416.log) [ac](ac_sb3_1124_162416.log) |  |
| 20251124 | 1124_162219 | MetaCDN/meta_reag | 3000000 | 0.4247 | 0.2328 | int=200 | [cs](cachesim_sb3_1124_162219.log) [ac](ac_sb3_1124_162219.log) |  |
| 20251124 | 1124_160957 | WikiCDN/wiki_2019t | 3000000 | 0.6027 | 0.4756 | int=200 | [cs](cachesim_sb3_1124_160957.log) [ac](ac_sb3_1124_160957.log) |  |
| 20251124 | 1124_154707 | WikiCDN/wiki_2019t | 3000000 | 0.6002 | 0.4724 | int=200 | [cs](cachesim_sb3_1124_154707.log) [ac](ac_sb3_1124_154707.log) |  |
| 20251124 | 1124_154301 | WikiCDN/wiki_2019t | 3000000 | 0.6018 | 0.4742 | int=200 | [cs](cachesim_sb3_1124_154301.log) [ac](ac_sb3_1124_154301.log) |  |
| 20251124 | 1124_154035 | WikiCDN/wiki_2019t | 3000000 | 0.6016 | 0.4740 | int=200 | [cs](cachesim_sb3_1124_154035.log) [ac](ac_sb3_1124_154035.log) |  |
| 20251124 | 1124_105600 | MetaCDN/meta_reag | 3000000 | 0.4045 | 0.2240 | int=200 | [cs](cachesim_sb3_1124_105600.log) [ac](ac_sb3_1124_105600.log) |  |
| 20251124 | 1124_105515 | MetaCDN/meta_reag | 3000000 | 0.4298 | 0.2335 | int=200 | [cs](cachesim_sb3_1124_105515.log) [ac](ac_sb3_1124_105515.log) |  |
| 20251124 | 1124_105331 | WikiCDN/wiki_2019t | 3000000 | 0.6018 | 0.4725 | int=200 | [cs](cachesim_sb3_1124_105331.log) [ac](ac_sb3_1124_105331.log) |  |
| 20251124 | 1124_105137 | WikiCDN/wiki_2019t | 3000000 | 0.6489 | 0.5464 | int=200 | [cs](cachesim_sb3_1124_105137.log) [ac](ac_sb3_1124_105137.log) |  |
| 20251121 | 1121_171039 | MetaCDN/meta_reag | 3000000 | 0.3911 | 0.2216 | int=200 | [cs](cachesim_sb3_1121_171039.log) [ac](ac_sb3_1121_171039.log) |  |
| 20251121 | 1121_170810 | MetaCDN/meta_reag | 3000000 | 0.3930 | 0.2221 | int=200 | [cs](cachesim_sb3_1121_170810.log) [ac](ac_sb3_1121_170810.log) |  |
| 20251121 | 1121_145633 | WikiCDN/wiki_2019t | 207646002 | 0.2344 | 0.1731 | int=200 | [cs](cachesim_sb3_1121_145633.log) [ac](ac_sb3_1121_145633.log) |  |
| 20251121 | 1121_143202 | WikiCDN/wiki_2019t | 3000000 | 0.6251 | 0.5148 | int=200 | [cs](cachesim_sb3_1121_143202.log) [ac](ac_sb3_1121_143202.log) |  |
| 20251121 | 1121_142752 | WikiCDN/wiki_2019t | 3000000 | 0.6264 | 0.5166 | int=200 | [cs](cachesim_sb3_1121_142752.log) [ac](ac_sb3_1121_142752.log) |  |
| 20251121 | 1121_142540 | WikiCDN/wiki_2019t | 3000000 | 0.6403 | 0.5398 | int=200 | [cs](cachesim_sb3_1121_142540.log) [ac](ac_sb3_1121_142540.log) |  |
| 20251121 | 1121_142212 | MetaCDN/meta_reag | 3000000 | 0.3975 | 0.2234 | int=200 | [cs](cachesim_sb3_1121_142212.log) [ac](ac_sb3_1121_142212.log) |  |
| 20251121 | 1121_142043 | MetaCDN/meta_reag | 3000000 | 0.4026 | 0.2246 | int=200 | [cs](cachesim_sb3_1121_142043.log) [ac](ac_sb3_1121_142043.log) |  |
| 20251121 | 1121_141842 | MetaCDN/meta_reag | 3000000 | 0.3906 | 0.2215 | int=200 | [cs](cachesim_sb3_1121_141842.log) [ac](ac_sb3_1121_141842.log) |  |
| 20251121 | 1121_140853 | MetaCDN/meta_reag | 3000000 | 0.3901 | 0.2216 | int=200 | [cs](cachesim_sb3_1121_140853.log) [ac](ac_sb3_1121_140853.log) |  |
| 20251121 | 1121_134849 | MetaCDN/meta_reag | 3000000 | 0.3805 | 0.2227 | int=200 | [cs](cachesim_sb3_1121_134849.log) [ac](ac_sb3_1121_134849.log) |  |
| 20251121 | 1121_115911 | WikiCDN/wiki_2019t | 3000000 | 0.6699 | 0.5669 | int=200 | [cs](cachesim_sb3_1121_115911.log) [ac](ac_sb3_1121_115911.log) |  |
| 20251121 | 1121_030525 | WikiCDN/wiki_2019t | 3000000 | 0.6063 | 0.4847 | int=200 | [cs](cachesim_sb3_1121_030525.log) [ac](ac_sb3_1121_030525.log) |  |
| 20251121 | 1121_030407 | WikiCDN/wiki_2019t | 3000000 | 0.7007 | 0.5935 | int=200 | [cs](cachesim_sb3_1121_030407.log) [ac](ac_sb3_1121_030407.log) |  |
| 20251121 | 1121_025424 | WikiCDN/wiki_2019t | 3000000 | 0.6961 | 0.5865 | int=200 | [cs](cachesim_sb3_1121_025424.log) [ac](ac_sb3_1121_025424.log) |  |
| 20251121 | 1121_024336 | WikiCDN/wiki_2019t | 3000000 | 0.7086 | 0.6081 | int=200 | [cs](cachesim_sb3_1121_024336.log) [ac](ac_sb3_1121_024336.log) |  |
| 20251121 | 1121_023203 | WikiCDN/wiki_2019t | 3000000 | 0.6990 | 0.5916 | int=200 | [cs](cachesim_sb3_1121_023203.log) [ac](ac_sb3_1121_023203.log) |  |
| 20251121 | 1121_022030 | WikiCDN/wiki_2019t | 3000000 | 0.7089 | 0.6050 | int=200 | [cs](cachesim_sb3_1121_022030.log) [ac](ac_sb3_1121_022030.log) |  |
| 20251120 | 1120_190639 | WikiCDN/wiki_2019t | 3000000 | 0.6059 | 0.4852 | int=200 | [cs](cachesim_sb3_1120_190639.log) [ac](ac_sb3_1120_190639.log) |  |
| 20251120 | 1120_190412 | WikiCDN/wiki_2019t | 3000000 | 0.6064 | 0.4848 | int=200 | [cs](cachesim_sb3_1120_190412.log) [ac](ac_sb3_1120_190412.log) |  |
| 20251120 | 1120_170745 | WikiCDN/wiki_2019t | 3000000 | 0.6071 | 0.4870 | int=200 | [cs](cachesim_sb3_1120_170745.log) [ac](ac_sb3_1120_170745.log) |  |
| 20251120 | 1120_160659 | WikiCDN/wiki_2019t | 3000000 | 0.6315 | 0.5247 | int=200 | [cs](cachesim_sb3_1120_160659.log) [ac](ac_sb3_1120_160659.log) |  |
| 20251119 | 1119_172943 | MetaCDN/meta_reag | 45623306 | 0.2690 | 0.1544 | int=200 | [cs](cachesim_sb3_1119_172943.log) [ac](ac_sb3_1119_172943.log) |  |
| 20251118 | 1118_213115 | WikiCDN/wiki_2019t | 207646002 | 0.2061 | 0.1525 | int=200 | [cs](cachesim_sb3_1118_213115.log) [ac](ac_sb3_1118_213115.log) |  |
| 20251118 | 1118_212802 | WikiCDN/wiki_2019t | 3000000 | 0.6279 | 0.5211 | int=200 | [cs](cachesim_sb3_1118_212802.log) [ac](ac_sb3_1118_212802.log) |  |
| 20251118 | 1118_210840 | WikiCDN/wiki_2019t | 207646002 | 0.1896 | 0.1373 | int=200 | [cs](cachesim_sb3_1118_210840.log) [ac](ac_sb3_1118_210840.log) |  |
| 20251118 | 1118_210712 | WikiCDN/wiki_2019t | 3000000 | 0.6075 | 0.4943 | int=200 | [cs](cachesim_sb3_1118_210712.log) [ac](ac_sb3_1118_210712.log) |  |
| 20251118 | 1118_120239 | MetaCDN/meta_reag | 45623306 | 0.2999 | 0.1632 | int=200 | [cs](cachesim_sb3_1118_120239.log) [ac](ac_sb3_1118_120239.log) |  |
| 20251118 | 1118_115151 | WikiCDN/wiki_2019t | 3000000 | 0.6206 | 0.5013 | int=200 | [cs](cachesim_sb3_1118_115151.log) [ac](ac_sb3_1118_115151.log) |  |
| 20251118 | 1118_115104 | WikiCDN/wiki_2019t | 3000000 | 0.6202 | 0.5003 | int=200 | [cs](cachesim_sb3_1118_115104.log) [ac](ac_sb3_1118_115104.log) |  |
| 20251118 | 1118_115018 | WikiCDN/wiki_2019t | 3000000 | 0.6053 | 0.4820 | int=200 | [cs](cachesim_sb3_1118_115018.log) [ac](ac_sb3_1118_115018.log) |  |
| 20251118 | 1118_114933 | WikiCDN/wiki_2019t | 3000000 | 0.6010 | 0.4758 | int=200 | [cs](cachesim_sb3_1118_114933.log) [ac](ac_sb3_1118_114933.log) |  |
| 20251118 | 1118_114844 | WikiCDN/wiki_2019t | 3000000 | 0.6695 | 0.5730 | int=200 | [cs](cachesim_sb3_1118_114844.log) [ac](ac_sb3_1118_114844.log) |  |
| 20251118 | 1118_114757 | WikiCDN/wiki_2019t | 3000000 | 0.6018 | 0.4725 | int=200 | [cs](cachesim_sb3_1118_114757.log) [ac](ac_sb3_1118_114757.log) |  |
| 20251118 | 1118_114705 | WikiCDN/wiki_2019t | 3000000 | 0.6489 | 0.5464 | int=200 | [cs](cachesim_sb3_1118_114705.log) [ac](ac_sb3_1118_114705.log) |  |
| 20251118 | 1118_113120 | WikiCDN/wiki_2019t | 207646002 | 0.1864 | 0.1362 | int=200 | [cs](cachesim_sb3_1118_113120.log) [ac](ac_sb3_1118_113120.log) |  |
| 20251118 | 1118_112411 | WikiCDN/wiki_2019t | 3000000 | 0.6000 | 0.4789 | int=200 | [cs](cachesim_sb3_1118_112411.log) [ac](ac_sb3_1118_112411.log) |  |
| 20251118 | 1118_103046 | WikiCDN/wiki_2019t | 3000000 | 0.6070 | 0.4867 | int=50 | [cs](cachesim_sb3_1118_103046.log) [ac](ac_sb3_1118_103046.log) |  |
| 20251118 | 1118_102436 | WikiCDN/wiki_2019t | 3000000 | 0.6073 | 0.4873 | int=200 | [cs](cachesim_sb3_1118_102436.log) [ac](ac_sb3_1118_102436.log) |  |
| 20251117 | 1117_115330 | WikiCDN/wiki_2019t | 3000000 | 0.6209 | 0.5013 | TD3 int=200 | [cs](cachesim_sb3_1117_115330.log) [ac](ac_sb3_1117_115330.log) |  |
| 20251114 | 1114_183759 | WikiCDN/wiki_2019t | 10000000 | 0.5189 | 0.4193 | TD3 int=200 | [cs](cachesim_sb3_1114_183759.log) [ac](ac_sb3_1114_183759.log) |  |
| 20251114 | 1114_181503 | WikiCDN/wiki_2019t | 10000000 | 0.5101 | 0.3883 | TD3 int=200 | [cs](cachesim_sb3_1114_181503.log) [ac](ac_sb3_1114_181503.log) |  |
| 20251114 | 1114_172051 | WikiCDN/wiki_2019t | 3000000 | 0.6060 | 0.4844 | int=200 | [cs](cachesim_sb3_1114_172051.log) [ac](ac_sb3_1114_172051.log) |  |
| 20251114 | 1114_164220 | WikiCDN/wiki_2019t | 3000000 | 0.6059 | 0.4852 | int=200 | [cs](cachesim_sb3_1114_164220.log) [ac](ac_sb3_1114_164220.log) |  |
| 20251114 | 1114_163206 | WikiCDN/wiki_2019t | 3000000 | 0.6068 | 0.4861 | int=200 | [cs](cachesim_sb3_1114_163206.log) [ac](ac_sb3_1114_163206.log) |  |
| 20251114 | 1114_005014 | WikiCDN/wiki_2019t | 3000000 | 0.6070 | 0.4859 | int=200 | [cs](cachesim_sb3_1114_005014.log) [ac](ac_sb3_1114_005014.log) |  |
| 20251114 | 1114_000426 | WikiCDN/wiki_2019t | 3000000 | 0.6072 | 0.4864 | int=200 | [cs](cachesim_sb3_1114_000426.log) [ac](ac_sb3_1114_000426.log) |  |
| 20251113 | 1113_235904 | WikiCDN/wiki_2019t | 3000000 | 0.6069 | 0.4861 | int=200 | [cs](cachesim_sb3_1113_235904.log) [ac](ac_sb3_1113_235904.log) |  |
| 20251113 | 1113_235401 | WikiCDN/wiki_2019t | 3000000 | 0.6194 | 0.4992 | TD3 int=200 | [cs](cachesim_sb3_1113_235401.log) [ac](ac_sb3_1113_235401.log) |  |
| 20251113 | 1113_020223 | MetaCDN/meta_reag | 45623306 | 0.3257 | 0.1703 | int=200 | [cs](cachesim_sb3_1113_020223.log) |  |
| 20251113 | 1113_013954 | WikiCDN/wiki_2019t | 3000000 | 0.6071 | 0.4861 | SAC int=200 | [cs](cachesim_sb3_1113_013954.log) [ac](ac_sb3_1113_013954.log) |  |
| 20251112 | 1112_215139 | WikiCDN/wiki_2019t | 3000000 | 0.6070 | 0.4862 | SAC int=200 | [cs](cachesim_sb3_1112_215139.log) [ac](ac_sb3_1112_215139.log) |  |
| 20251112 | 1112_214357 | WikiCDN/wiki_2019t | 3000000 | 0.6070 | 0.4862 | SAC int=200 | [cs](cachesim_sb3_1112_214357.log) [ac](ac_sb3_1112_214357.log) |  |
| 20251112 | 1112_201701 | WikiCDN/wiki_2019t | 3000000 | 0.6070 | 0.4859 | SAC int=200 | [cs](cachesim_sb3_1112_201701.log) [ac](ac_sb3_1112_201701.log) |  |
| 20251112 | 1112_171554 | WikiCDN/wiki_2019t | 3000000 | 0.6067 | 0.4858 | SAC int=200 | [cs](cachesim_sb3_1112_171554.log) [ac](ac_sb3_1112_171554.log) |  |
| 20251112 | 1112_170854 | WikiCDN/wiki_2019t | 3000000 | 0.6068 | 0.4859 | SAC int=200 | [cs](cachesim_sb3_1112_170854.log) [ac](ac_sb3_1112_170854.log) |  |
| 20251112 | 1112_170054 | WikiCDN/wiki_2019t | 3000000 | 0.6067 | 0.4860 | SAC int=200 | [cs](cachesim_sb3_1112_170054.log) [ac](ac_sb3_1112_170054.log) |  |
| 20251112 | 1112_165337 | WikiCDN/wiki_2019t | 3000000 | 0.6072 | 0.4861 | SAC int=200 | [cs](cachesim_sb3_1112_165337.log) [ac](ac_sb3_1112_165337.log) |  |
| 20251112 | 1112_164813 | WikiCDN/wiki_2019t | 3000000 | 0.6066 | 0.4860 | SAC int=200 | [cs](cachesim_sb3_1112_164813.log) [ac](ac_sb3_1112_164813.log) |  |
| 20251112 | 1112_164233 | WikiCDN/wiki_2019t | 3000000 | 0.6065 | 0.4856 | SAC int=200 | [cs](cachesim_sb3_1112_164233.log) [ac](ac_sb3_1112_164233.log) |  |
| 20251112 | 1112_163452 | WikiCDN/wiki_2019t | 3000000 | 0.6071 | 0.4860 | SAC int=200 | [cs](cachesim_sb3_1112_163452.log) [ac](ac_sb3_1112_163452.log) |  |
| 20251112 | 1112_162428 | WikiCDN/wiki_2019t | 3000000 | 0.6066 | 0.4855 | SAC int=200 | [cs](cachesim_sb3_1112_162428.log) [ac](ac_sb3_1112_162428.log) |  |
| 20251112 | 1112_153403 | WikiCDN/wiki_2019t | 3000000 | 0.6067 | 0.4859 | SAC int=200 | [cs](cachesim_sb3_1112_153403.log) [ac](ac_sb3_1112_153403.log) |  |
| 20251112 | 1112_152834 | WikiCDN/wiki_2019t | 3000000 | 0.6066 | 0.4858 | SAC int=200 | [cs](cachesim_sb3_1112_152834.log) [ac](ac_sb3_1112_152834.log) |  |
| 20251112 | 1112_152205 | WikiCDN/wiki_2019t | 3000000 | 0.6073 | 0.4866 | SAC int=200 | [cs](cachesim_sb3_1112_152205.log) [ac](ac_sb3_1112_152205.log) |  |
| 20251112 | 1112_151606 | WikiCDN/wiki_2019t | 3000000 | 0.6065 | 0.4855 | SAC int=200 | [cs](cachesim_sb3_1112_151606.log) [ac](ac_sb3_1112_151606.log) |  |
| 20251112 | 1112_150239 | WikiCDN/wiki_2019t | 3000000 | 0.6072 | 0.4861 | SAC int=200 | [cs](cachesim_sb3_1112_150239.log) [ac](ac_sb3_1112_150239.log) |  |
| 20251112 | 1112_111121 | WikiCDN/wiki_2019t | 3000000 | 0.6067 | 0.4859 | SAC int=200 | [cs](cachesim_sb3_1112_111121.log) [ac](ac_sb3_1112_111121.log) |  |
| 20251112 | 1112_104707 | WikiCDN/wiki_2019t | 3000000 | 0.6070 | 0.4859 | SAC int=200 | [cs](cachesim_sb3_1112_104707.log) [ac](ac_sb3_1112_104707.log) |  |
| 20251112 | 1112_104205 | WikiCDN/wiki_2019t | 3000000 | 0.6067 | 0.4861 | SAC int=200 | [cs](cachesim_sb3_1112_104205.log) [ac](ac_sb3_1112_104205.log) |  |
| 20251112 | 1112_103344 | WikiCDN/wiki_2019t | 3000000 | 0.6060 | 0.4850 | SAC int=200 | [cs](cachesim_sb3_1112_103344.log) [ac](ac_sb3_1112_103344.log) |  |
| 20251112 | 1112_102230 | WikiCDN/wiki_2019t | 3000000 | 0.6065 | 0.4855 | SAC int=200 | [cs](cachesim_sb3_1112_102230.log) [ac](ac_sb3_1112_102230.log) |  |
| 20251112 | 1112_093841 | WikiCDN/wiki_2019t | 3000000 | 0.6070 | 0.4856 | SAC int=200 | [cs](cachesim_sb3_1112_093841.log) [ac](ac_sb3_1112_093841.log) |  |
| 20251112 | 1112_093143 | WikiCDN/wiki_2019t | 3000000 | 0.6070 | 0.4862 | SAC int=200 | [cs](cachesim_sb3_1112_093143.log) [ac](ac_sb3_1112_093143.log) |  |
| 20251112 | 1112_092240 | WikiCDN/wiki_2019t | 3000000 | 0.6068 | 0.4858 | SAC int=200 | [cs](cachesim_sb3_1112_092240.log) [ac](ac_sb3_1112_092240.log) |  |
| 20251112 | 1112_091649 | WikiCDN/wiki_2019t | 3000000 | 0.6069 | 0.4858 | SAC int=200 | [cs](cachesim_sb3_1112_091649.log) [ac](ac_sb3_1112_091649.log) |  |
| 20251111 | 1111_232759 | WikiCDN/wiki_2019t | 3000000 | 0.6069 | 0.4859 | SAC int=200 | [cs](cachesim_sb3_1111_232759.log) [ac](ac_sb3_1111_232759.log) |  |
| 20251111 | 1111_225744 | WikiCDN/wiki_2019t | 3000000 | 0.6070 | 0.4860 | SAC int=200 | [cs](cachesim_sb3_1111_225744.log) [ac](ac_sb3_1111_225744.log) |  |
| 20251111 | 1111_173233 | WikiCDN/wiki_2019t | 3000000 | 0.6071 | 0.4861 | SAC int=200 | [cs](cachesim_sb3_1111_173233.log) [ac](ac_sb3_1111_173233.log) |  |
| 20251111 | 1111_110801 | WikiCDN/wiki_2019t | 3000000 | 0.6071 | 0.4860 | SAC int=200 | [cs](cachesim_sb3_1111_110801.log) [ac](ac_sb3_1111_110801.log) |  |
| 20251111 | 1111_105220 | WikiCDN/wiki_2019t | 3000000 | 0.6068 | 0.4862 | SAC int=200 | [cs](cachesim_sb3_1111_105220.log) [ac](ac_sb3_1111_105220.log) |  |
| 20251111 | 1111_104721 | WikiCDN/wiki_2019t | 3000000 | 0.6067 | 0.4860 | SAC int=200 | [cs](cachesim_sb3_1111_104721.log) [ac](ac_sb3_1111_104721.log) |  |
| 20251111 | 1111_093620 | WikiCDN/wiki_2019t | 3000000 | 0.6065 | 0.4864 | SAC int=200 | [cs](cachesim_sb3_1111_093620.log) [ac](ac_sb3_1111_093620.log) |  |
| 20251111 | 1111_092603 | WikiCDN/wiki_2019t | 3000000 | 0.6062 | 0.4854 | SAC int=200 | [cs](cachesim_sb3_1111_092603.log) [ac](ac_sb3_1111_092603.log) |  |
| 20251111 | 1111_022525 | WikiCDN/wiki_2019t | 3000000 | 0.6069 | 0.4860 | int=200 | [cs](cachesim_sb3_1111_022525.log) [ac](ac_sb3_1111_022525.log) |  |
| 20251111 | 1111_021920 | WikiCDN/wiki_2019t | 3000000 | 0.6247 | 0.5123 | int=200 | [cs](cachesim_sb3_1111_021920.log) [ac](ac_sb3_1111_021920.log) |  |
| 20251111 | 1111_021301 | WikiCDN/wiki_2019t | 3000000 | 0.6069 | 0.4857 | int=200 | [cs](cachesim_sb3_1111_021301.log) [ac](ac_sb3_1111_021301.log) |  |
| 20251110 | 1110_234753 | WikiCDN/wiki_2019t | 3000000 | 0.6089 | 0.4856 | TD3 int=200 | [cs](cachesim_sb3_1110_234753.log) [ac](ac_sb3_1110_234753.log) |  |
| 20251110 | 1110_233455 | WikiCDN/wiki_2019t | 3000000 | 0.6069 | 0.4859 | SAC int=200 | [cs](cachesim_sb3_1110_233455.log) [ac](ac_sb3_1110_233455.log) |  |
| 20251110 | 1110_232815 | WikiCDN/wiki_2019t | 3000000 | 0.6067 | 0.4858 | SAC int=200 | [cs](cachesim_sb3_1110_232815.log) [ac](ac_sb3_1110_232815.log) |  |
| 20251110 | 1110_210902 | WikiCDN/wiki_2019t | 10000000 | 0.4807 | 0.3660 | SAC int=200 | [cs](cachesim_sb3_1110_210902.log) [ac](ac_sb3_1110_210902.log) |  |
| 20251110 | 1110_201409 | WikiCDN/wiki_2019t | 10000000 | 0.4808 | 0.3660 | SAC int=200 | [cs](cachesim_sb3_1110_201409.log) [ac](ac_sb3_1110_201409.log) |  |
| 20251110 | 1110_191734 | WikiCDN/wiki_2019t | 10000000 | 0.4801 | 0.3654 | SAC int=200 | [cs](cachesim_sb3_1110_191734.log) [ac](ac_sb3_1110_191734.log) |  |
| 20251110 | 1110_174118 | WikiCDN/wiki_2019t | 10000000 | 0.4804 | 0.3657 | SAC int=200 | [cs](cachesim_sb3_1110_174118.log) [ac](ac_sb3_1110_174118.log) |  |
| 20251110 | 1110_162506 | WikiCDN/wiki_2019t | 10000000 | 0.4801 | 0.3653 | SAC int=200 | [cs](cachesim_sb3_1110_162506.log) [ac](ac_sb3_1110_162506.log) |  |
| 20251110 | 1110_162426 | WikiCDN/wiki_2019t | 10000000 | 0.4804 | 0.3655 | SAC int=200 | [cs](cachesim_sb3_1110_162426.log) [ac](ac_sb3_1110_162426.log) |  |
| 20251108 | 1108_194813 | WikiCDN/wiki_2019t | 10000000 | 0.4789 | 0.3697 | TD3 int=200 | [cs](cachesim_sb3_1108_194813.log) [ac](ac_sb3_1108_194813.log) |  |
| 20251108 | 1108_180329 | WikiCDN/wiki_2019t | 10000000 | 0.4977 | 0.3937 | TD3 int=200 | [cs](cachesim_sb3_1108_180329.log) [ac](ac_sb3_1108_180329.log) |  |
| 20251108 | 1108_180314 | WikiCDN/wiki_2019t | 10000000 | 0.4948 | 0.3844 | TD3 int=200 | [cs](cachesim_sb3_1108_180314.log) [ac](ac_sb3_1108_180314.log) |  |
| 20251108 | 1108_173309 | WikiCDN/wiki_2019t | 10000000 | 0.4862 | 0.3728 | TD3 int=200 | [cs](cachesim_sb3_1108_173309.log) [ac](ac_sb3_1108_173309.log) |  |
| 20251108 | 1108_025635 | lfutest_10m.csv | 10000000 | 0.0964 | 0.0984 | SAC int=200 | [cs](cachesim_sb3_1108_025635.log) [ac](ac_sb3_1108_025635.log) |  |
| 20251108 | 1108_025630 | lfutest_10m.csv | 10000000 | 0.0947 | 0.0979 | TD3 int=200 | [cs](cachesim_sb3_1108_025630.log) [ac](ac_sb3_1108_025630.log) |  |
| 20251108 | 1108_025622 | lrutest_10m.csv | 10000000 | 0.1261 | 0.1288 | SAC int=200 | [cs](cachesim_sb3_1108_025622.log) [ac](ac_sb3_1108_025622.log) |  |
| 20251108 | 1108_025614 | lrutest_10m.csv | 10000000 | 0.1368 | 0.1390 | TD3 int=200 | [cs](cachesim_sb3_1108_025614.log) [ac](ac_sb3_1108_025614.log) |  |
| 20251108 | 1108_023745 | WikiCDN/wiki_2019t | 10000000 | 0.4800 | 0.3651 | SAC int=200 | [cs](cachesim_sb3_1108_023745.log) [ac](ac_sb3_1108_023745.log) |  |
| 20251108 | 1108_023556 | WikiCDN/wiki_2019t | 10000000 | 0.4877 | 0.3685 | TD3 int=200 | [cs](cachesim_sb3_1108_023556.log) [ac](ac_sb3_1108_023556.log) |  |
| 20251108 | 1108_020729 | WikiCDN/wiki_2019t | 10000000 | 0.4835 | 0.3710 | TD3 int=200 | [cs](cachesim_sb3_1108_020729.log) [ac](ac_sb3_1108_020729.log) |  |
| 20251108 | 1108_014010 | WikiCDN/wiki_2019t | 10000000 | 0.5119 | 0.4023 | TD3 int=200 | [cs](cachesim_sb3_1108_014010.log) [ac](ac_sb3_1108_014010.log) |  |
| 20251108 | 1108_002806 | WikiCDN/wiki_2019t | 10000000 | 0.4856 | 0.3672 | TD3 int=200 | [cs](cachesim_sb3_1108_002806.log) [ac](ac_sb3_1108_002806.log) |  |
| 20251107 | 1107_193909 | WikiCDN/wiki_2019t | 10000000 | 0.4813 | 0.3683 | int=200 | [cs](cachesim_sb3_1107_193909.log) [ac](ac_sb3_1107_193909.log) |  |
| 20251107 | 1107_190129 | WikiCDN/wiki_2019t | 10000000 | 0.4805 | 0.3655 | SAC int=200 | [cs](cachesim_sb3_1107_190129.log) [ac](ac_sb3_1107_190129.log) |  |
| 20251107 | 1107_174730 | WikiCDN/wiki_2019t | 10000000 | 0.4830 | 0.3602 | TD3 int=200 | [cs](cachesim_sb3_1107_174730.log) [ac](ac_sb3_1107_174730.log) |  |
| 20251107 | 1107_132955 | WikiCDN/wiki_2019t | 10000000 | 0.4822 | 0.3671 | TD3 int=200 | [cs](cachesim_sb3_1107_132955.log) [ac](ac_sb3_1107_132955.log) |  |
| 20251107 | 1107_123724 | WikiCDN/wiki_2019t | 10000000 | 0.4866 | 0.3764 | TD3 int=200 | [cs](cachesim_sb3_1107_123724.log) [ac](ac_sb3_1107_123724.log) |  |
| 20251107 | 1107_111443 | WikiCDN/wiki_2019t | 10000000 | 0.4806 | 0.3658 | SAC int=200 | [cs](cachesim_sb3_1107_111443.log) [ac](ac_sb3_1107_111443.log) |  |
| 20251107 | 1107_101048 | WikiCDN/wiki_2019t | 10000000 | 0.4862 | 0.3823 | TD3 int=200 | [cs](cachesim_sb3_1107_101048.log) [ac](ac_sb3_1107_101048.log) |  |
| 20251107 | 1107_033258 | WikiCDN/wiki_2019t | 10000000 | 0.4859 | 0.3770 | TD3 int=200 | [cs](cachesim_sb3_1107_033258.log) [ac](ac_sb3_1107_033258.log) |  |
| 20251107 | 1107_005228 | WikiCDN/wiki_2019t | 10000000 | 0.4828 | 0.3717 | TD3 int=200 | [cs](cachesim_sb3_1107_005228.log) [ac](ac_sb3_1107_005228.log) |  |
| 20251107 | 1107_005128 | WikiCDN/wiki_2019t | 10000000 | 0.5020 | 0.3866 | TD3 int=200 | [cs](cachesim_sb3_1107_005128.log) [ac](ac_sb3_1107_005128.log) |  |
| 20251106 | 1106_235905 | WikiCDN/wiki_2019t | 10000000 | 0.4944 | 0.3846 | TD3 int=200 | [cs](cachesim_sb3_1106_235905.log) [ac](ac_sb3_1106_235905.log) |  |
| 20251106 | 1106_231034 | WikiCDN/wiki_2019t | 10000000 | 0.4808 | 0.3589 | TD3 int=200 | [cs](cachesim_sb3_1106_231034.log) [ac](ac_sb3_1106_231034.log) |  |
| 20251106 | 1106_222626 | WikiCDN/wiki_2019t | 10000000 | 0.5075 | 0.3868 | TD3 int=200 | [cs](cachesim_sb3_1106_222626.log) [ac](ac_sb3_1106_222626.log) |  |
| 20251106 | 1106_213930 | WikiCDN/wiki_2019t | 10000000 | 0.4965 | 0.3867 | TD3 int=200 | [cs](cachesim_sb3_1106_213930.log) [ac](ac_sb3_1106_213930.log) |  |
| 20251106 | 1106_210904 | WikiCDN/wiki_2019t | 10000000 | 0.4957 | 0.3795 | TD3 int=200 | [cs](cachesim_sb3_1106_210904.log) [ac](ac_sb3_1106_210904.log) |  |
| 20251106 | 1106_195917 | WikiCDN/wiki_2019t | 10000000 | 0.4979 | 0.3901 | TD3 int=200 | [cs](cachesim_sb3_1106_195917.log) [ac](ac_sb3_1106_195917.log) |  |
| 20251106 | 1106_195218 | WikiCDN/wiki_2019t | 10000000 | 0.4998 | 0.3824 | TD3 int=200 | [cs](cachesim_sb3_1106_195218.log) [ac](ac_sb3_1106_195218.log) |  |
| 20251106 | 1106_111646 | WikiCDN/wiki_2019t | 10000000 | 0.4780 | 0.3619 | TD3 int=200 | [cs](cachesim_sb3_1106_111646.log) [ac](ac_sb3_1106_111646.log) |  |
| 20251106 | 1106_101920 | WikiCDN/wiki_2019t | 10000000 | 0.4779 | 0.3656 | TD3 int=200 | [cs](cachesim_sb3_1106_101920.log) [ac](ac_sb3_1106_101920.log) |  |
| 20251106 | 1106_095956 | WikiCDN/wiki_2019t | 10000000 | 0.5161 | 0.4107 | int=200 | [cs](cachesim_sb3_1106_095956.log) [ac](ac_sb3_1106_095956.log) |  |
| 20251106 | 1106_094634 | WikiCDN/wiki_2019t | 10000000 | 0.4863 | 0.3658 | int=200 | [cs](cachesim_sb3_1106_094634.log) [ac](ac_sb3_1106_094634.log) |  |
| 20251106 | 1106_093058 | WikiCDN/wiki_2019t | 10000000 | 0.4804 | 0.3657 | int=200 | [cs](cachesim_sb3_1106_093058.log) [ac](ac_sb3_1106_093058.log) |  |
| 20251106 | 1106_023228 | WikiCDN/wiki_2019t | 207646002 | 0.1928 | 0.1422 | int=200 | [cs](cachesim_sb3_1106_023228.log) [ac](ac_sb3_1106_023228.log) |  |
| 20251105 | 1105_183807 | WikiCDN/wiki_2019t | 207646002 | 0.2211 | 0.1726 | int=200 | [cs](cachesim_sb3_1105_183807.log) [ac](ac_sb3_1105_183807.log) |  |
| 20251105 | 1105_174733 | lrutest_10m.csv | 10000000 | 0.0875 | 0.0919 | int=200 | [cs](cachesim_sb3_1105_174733.log) [ac](ac_sb3_1105_174733.log) |  |
| 20251105 | 1105_173057 | lfutest_10m.csv | 10000000 | 0.0954 | 0.0977 | int=200 | [cs](cachesim_sb3_1105_173057.log) [ac](ac_sb3_1105_173057.log) |  |
| 20251104 | 1104_231245 | lfutest_10m.csv | 10000000 | 0.0956 | 0.0984 | TD3 int=200 | [cs](cachesim_sb3_1104_231245.log) [ac](ac_sb3_1104_231245.log) |  |
| 20251104 | 1104_230241 | lrutest_10m.csv | 10000000 | 0.3624 | 0.3618 | SAC int=200 | [cs](cachesim_sb3_1104_230241.log) [ac](ac_sb3_1104_230241.log) |  |
| 20251104 | 1104_230110 | lrutest_10m.csv | 10000000 | 0.0907 | 0.0949 | SAC int=200 | [cs](cachesim_sb3_1104_230110.log) [ac](ac_sb3_1104_230110.log) |  |
| 20251104 | 1104_225920 | lrutest_10m.csv | 10000000 | 0.0904 | 0.0947 | SAC int=200 | [cs](cachesim_sb3_1104_225920.log) [ac](ac_sb3_1104_225920.log) |  |
| 20251104 | 1104_225738 | lrutest_10m.csv | 10000000 | 0.0908 | 0.0950 | SAC int=200 | [cs](cachesim_sb3_1104_225738.log) [ac](ac_sb3_1104_225738.log) |  |
| 20251104 | 1104_225331 | lrutest_10m.csv | 10000000 | 0.0914 | 0.0962 | SAC int=200 | [cs](cachesim_sb3_1104_225331.log) [ac](ac_sb3_1104_225331.log) |  |
| 20251104 | 1104_220437 | lfutest_10m.csv | 10000000 | 0.0954 | 0.0982 | SAC int=200 | [cs](cachesim_sb3_1104_220437.log) [ac](ac_sb3_1104_220437.log) |  |
| 20251104 | 1104_193330 | WikiCDN/wiki_2019t | 10000000 | 0.4804 | 0.3656 | SAC int=200 | [cs](cachesim_sb3_1104_193330.log) [ac](ac_sb3_1104_193330.log) |  |
| 20251104 | 1104_180855 | WikiCDN/wiki_2019t | 10000000 | 0.4803 | 0.3655 | SAC int=200 | [cs](cachesim_sb3_1104_180855.log) [ac](ac_sb3_1104_180855.log) |  |
| 20251103 | 1103_213043 | lrutest_10m.csv | 10000000 | 0.1379 | 0.1400 | TD3 int=200 | [cs](cachesim_sb3_1103_213043.log) [ac](ac_sb3_1103_213043.log) |  |
| 20251103 | 1103_204120 | lrutest_10m.csv | 10000000 | 0.1265 | 0.1305 | SAC int=200 | [cs](cachesim_sb3_1103_204120.log) [ac](ac_sb3_1103_204120.log) |  |
| 20251103 | 1103_202052 | lrutest_10m.csv | 10000000 | 0.1248 | 0.1276 | SAC int=200 | [cs](cachesim_sb3_1103_202052.log) [ac](ac_sb3_1103_202052.log) |  |
| 20251103 | 1103_200736 | lfutest_10m.csv | 10000000 | 0.0954 | 0.0982 | SAC int=200 | [cs](cachesim_sb3_1103_200736.log) [ac](ac_sb3_1103_200736.log) |  |
| 20251103 | 1103_194355 | lrutest_10m.csv | 10000000 | 0.1248 | 0.1283 | SAC int=200 | [cs](cachesim_sb3_1103_194355.log) [ac](ac_sb3_1103_194355.log) |  |
| 20251103 | 1103_190008 | lrutest_10m.csv | 10000000 | 0.0973 | 0.1017 | int=200 | [cs](cachesim_sb3_1103_190008.log) [ac](ac_sb3_1103_190008.log) |  |
| 20251103 | 1103_113829 | lfutest_10m.csv | 10000000 | 0.0954 | 0.0977 | int=200 | [cs](cachesim_sb3_1103_113829.log) [ac](ac_sb3_1103_113829.log) |  |
| 20251103 | 1103_112912 | lrutest_10m.csv | 10000000 | 0.0980 | 0.1017 | int=200 | [cs](cachesim_sb3_1103_112912.log) [ac](ac_sb3_1103_112912.log) |  |
| 20251031 | 1031_161840 | WikiCDN/wiki_2019t | 10000000 | 0.4816 | 0.3696 | int=200 | [cs](cachesim_sb3_1031_161840.log) [ac](ac_sb3_1031_161840.log) |  |
| 20251031 | 1031_151728 | WikiCDN/wiki_2019t | 10000000 | 0.4790 | 0.3624 | int=200 | [cs](cachesim_sb3_1031_151728.log) [ac](ac_sb3_1031_151728.log) |  |
| 20251031 | 1031_024219 | WikiCDN/wiki_2019t | 207646002 | 0.1929 | 0.1421 | int=200 | [cs](cachesim_sb3_1031_024219.log) [ac](ac_sb3_1031_024219.log) |  |
| 20251031 | 1031_023342 | WikiCDN/wiki_2019t | 10000000 | 0.4893 | 0.3729 | — | [cs](cachesim_sb3_1031_023342.log) [ac](ac_sb3_1031_023342.log) |  |
| 20251031 | 1031_022915 | WikiCDN/wiki_2019t | 10000000 | 0.4857 | 0.3677 | — | [cs](cachesim_sb3_1031_022915.log) [ac](ac_sb3_1031_022915.log) |  |
| 20251031 | 1031_015607 | WikiCDN/wiki_2019t | 10000000 | 0.4804 | 0.3665 | int=200 | [cs](cachesim_sb3_1031_015607.log) [ac](ac_sb3_1031_015607.log) |  |
| 20251031 | 1031_014543 | WikiCDN/wiki_2019t | 10000000 | 0.4794 | 0.3652 | int=200 | [cs](cachesim_sb3_1031_014543.log) [ac](ac_sb3_1031_014543.log) |  |
| 20251030 | 1030_231012 | WikiCDN/wiki_2019t | 10000000 | 0.4803 | 0.3654 | SAC int=200 | [cs](cachesim_sb3_1030_231012.log) [ac](ac_sb3_1030_231012.log) |  |
| 20251030 | 1030_213330 | WikiCDN/wiki_2019t | 10000000 | 0.4803 | 0.3656 | SAC int=200 | [cs](cachesim_sb3_1030_213330.log) [ac](ac_sb3_1030_213330.log) |  |
| 20251030 | 1030_183716 | WikiCDN/wiki_2019t | 10000000 | 0.4804 | 0.3656 | SAC int=200 | [cs](cachesim_sb3_1030_183716.log) [ac](ac_sb3_1030_183716.log) |  |
| 20251030 | 1030_014039 | WikiCDN/wiki_2019t | 10000000 | 0.4860 | 0.3751 | SAC int=200 | [cs](cachesim_sb3_1030_014039.log) [ac](ac_sb3_1030_014039.log) |  |

<!-- ROOT_LOG_INDEX_END -->


## Trace: data/MetaCDN/meta_reag.oracleGeneral.zst

### Sweeps（CACHESIM_NUM_REQ=3000000）

| date | id | best | OMR | BMR | cfg | ref | note |
| ---: | --- | ---: | ---: | ---: | --- | --- | --- |
| 20251212 | meta_3m | 1 | 0.383033 | 0.242300 | TD3 scale=1.0 | [res](sweeps/meta_3m_1212_152109/results.csv) |  |
| 20251214 | meta_rwd | 1 | NA | NA | cpd=0 irt=0 int=500 | [res](sweeps/meta_reward_algo_v4_1214_014136/results.csv) | NA |
| 20251215 | alg6 | 1 | 0.269697 | 0.164610 | SAC algo-expand | [res](sweeps/meta_algo_expand_v6_1215_011924/results.csv) | ALL |
| 20251212 | rec | 1 | 0.368500 | 0.219000 | TD3 rec | [res](sweeps/rec3m_1212_133521/results.csv) |  |
| 20251222 | act | 1 | 0.367959 | 0.217575 | SAC scale-sweep | [res](sweeps/meta_best_action_scale_r2_20251222_183925/results.csv) |  |
| 20251222 | actW | 1 | 0.367959 | 0.217551 | SAC winner | [res](sweeps/meta_best_action_scale_winner_repeat5_20251222_201349/results.csv) |  |
| 20251217 | gridIT | 3 | 0.367961 | 0.217590 | SAC grid int×temp | [res](sweeps/meta_best_grid_interval_temp_r2_20251217_234028/results.csv) |  |
| 20251222 | gridW | 1 | 0.367962 | 0.217582 | SAC grid winner | [res](sweeps/meta_best_grid_winner_repeat5_20251222_102624/results.csv) |  |
| 20251223 | scale | 5 | 0.367958 | 0.217548 | SAC scale-fine | [res](sweeps/meta_best_scale_fine_r2_20251223_110142/results.csv) |  |
| 20251217 | v5 | 1 | 0.367968 | 0.217533 | SAC v5 repeat | [res](sweeps/meta_best_v5_idx6_repeat5_20251217_182945/results.csv) |  |
| 20251213 | low2 | 6 | 0.368000 | 0.217500 | SAC lower v2 | [res](sweeps/meta_lower_omr_3m_v2_1213_135303/results.csv) |  |
| 20251213 | ref6 | 2 | 0.368000 | 0.217450 | SAC refine6 | [res](sweeps/meta_refine6_3m_v3_1213_214805/results.csv) |  |
| 20251212 | refU | 4 | 0.368100 | 0.218200 | SAC refine-user | [res](sweeps/meta_refine_user_3m_1212_160647/results.csv) |  |
| 20251214 | rwdFix | 1 | 0.368000 | 0.217450 | SAC reward-v4 fix | [res](sweeps/meta_reward_algo_v4_fix_1214_014409/results.csv) |  |
| 20251215 | rwd15 | 1 | 0.367987 | 0.217459 | SAC reward-v4 | [res](sweeps/meta_reward_algo_v4_20251215_145147/results.csv) |  |
| 20251215 | tqc | 1 | 0.369536 | 0.216303 | TQC reward-v4 | [res](sweeps/meta_reward_algo_v4_tqc_only_fix_20251215_211951/results.csv) |  |
| 20251214 | prec5 | 6 | 0.367980 | 0.217538 | SAC prec-v5 | [res](sweeps/meta_precision_refine_v5_1214_212442/results.csv) |  |
| 20251224 | tempA | 2 | 0.367958 | 0.217502 | SAC temp×int×scale | [res](sweeps/meta_temp_interval_scale_aggr_r2_20251224_205809/results.csv) |  |
| 20251224 | tempG | 7 | 0.367958 | 0.217502 | SAC temp×scale grid | [res](sweeps/meta_temp_scale_grid_r2_20251224_142147/results.csv) |  |
| 20251214 | cacheFix | 1 | 0.368000 | 0.217550 | SAC cacheF fix | [res](sweeps/meta_try_cachefeat_3m_fix_1214_000103/results.csv) |  |
| 20251213 | cacheTry | 2 | 0.368000 | 0.217500 | SAC cacheF | [res](sweeps/meta_try_cachefeat_3m_1213_234146/results.csv) |  |
| 20251214 | candTry | 1 | 0.368000 | 0.217550 | SAC candF | [res](sweeps/meta_try_candfeat_3m_1214_005451/results.csv) |  |
| 20260129 | next_m1 | 1 | NA | NA | SAC cpd=0 irt=0 int=200 scale=0.5 temp=1.3 | [res](sweeps/next_meta_modes_3m_20260129_183751/results.csv) | NA |
| 20260129 | next_m2 | 1 | NA | NA | SAC cpd=0 irt=0 int=200 scale=0.5 temp=1.3 | [res](sweeps/next_meta_modes_3m_20260129_183812/results.csv) | NA |
| 20260129 | next_ns | 1 | NA | NA | SAC cpd=0 irt=0 int=200 scale=0.5 temp=1.3 | [res](sweeps/next_meta_modes_nosem_3m_20260129_184111/results.csv) | NA |
| 20260129 | next | 1 | 0.367959 | 0.217529 | SAC cpd=0 irt=0 int=200 scale=0.5 temp=1.3 | [res](sweeps/next_meta_modes_req1_3m_20260129_184621/results.csv) | req1 |
| 20260130 | m2 | 2 | 0.367959 | 0.217457 | SAC cpd=0 irt=0 int=200 scale=0.5 temp=1.3 mrw=0.0 | [cs](sweeps/modes2_mrw0_0130_112123/combined_summary.csv) |  |
| 20260130 | m3 | 3 | 0.367960 | 0.217561 | SAC cpd=0 irt=0 int=200 scale=0.5 temp=1.3 | [cs](sweeps/modes3_batch_0130_021623/combined_summary.csv) |  |
| unknown | cw | - | NA | NA | const_weight | - | const |


<!-- ROOT_LOGS_BEGIN -->

### 根目录日志（76 条，req>=3000000）

#### req=45623306（7 条）

| date | run | OMR | BMR | cfg | ref | note |
| ---: | --- | ---: | ---: | --- | --- | --- |
| 20251208 | 1208_100023 | 0.2735 | 0.1629 | PPO cpd=1 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_100023.log) [ac](ac_sb3_1208_100023.log) |  |
| 20251129 | 1129_182809 | 0.3217 | 0.1746 | PPO int=200 | [cs](cachesim_sb3_1129_182809.log) [ac](ac_sb3_1129_182809.log) |  |
| 20251128 | 1128_181003 | 0.3378 | 0.1776 | PPO int=200 | [cs](cachesim_sb3_1128_181003.log) [ac](ac_sb3_1128_181003.log) |  |
| 20251128 | 1128_014635 | 0.3592 | 0.1874 | PPO int=200 | [cs](cachesim_sb3_1128_014635.log) [ac](ac_sb3_1128_014635.log) |  |
| 20251119 | 1119_172943 | 0.2690 | 0.1544 | int=200 | [cs](cachesim_sb3_1119_172943.log) [ac](ac_sb3_1119_172943.log) |  |
| 20251118 | 1118_120239 | 0.2999 | 0.1632 | int=200 | [cs](cachesim_sb3_1118_120239.log) [ac](ac_sb3_1118_120239.log) |  |
| 20251113 | 1113_020223 | 0.3257 | 0.1703 | int=200 | [cs](cachesim_sb3_1113_020223.log) |  |

##### 逐日志明细（req=45623306）

**1208_100023**（20251208）

- 结果：OMR=0.2735，BMR=0.1629
- logs：[cachesim_sb3_1208_100023.log](cachesim_sb3_1208_100023.log) / [ac_sb3_1208_100023.log](ac_sb3_1208_100023.log)
- cachesim：req=45623306；int=200；mr_w=1.000 bmr_w=0.000；irt=0；cpd=1；cacheF=0；candF=0；state=0->14
 - [LOH INIT] AvgTopK enabled: TOP4 × 6特征 = 24维
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1129_182809**（20251129）

- 结果：OMR=0.3217，BMR=0.1746
- logs：[cachesim_sb3_1129_182809.log](cachesim_sb3_1129_182809.log) / [ac_sb3_1129_182809.log](ac_sb3_1129_182809.log)
- cachesim：req=45623306；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1128_181003**（20251128）

- 结果：OMR=0.3378，BMR=0.1776
- logs：[cachesim_sb3_1128_181003.log](cachesim_sb3_1128_181003.log) / [ac_sb3_1128_181003.log](ac_sb3_1128_181003.log)
- cachesim：req=45623306；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1128_014635**（20251128）

- 结果：OMR=0.3592，BMR=0.1874
- logs：[cachesim_sb3_1128_014635.log](cachesim_sb3_1128_014635.log) / [ac_sb3_1128_014635.log](ac_sb3_1128_014635.log)
- cachesim：req=45623306；int=200；mr_w=1.000 bmr_w=0.000
 - [LOH INIT] AvgTopK enabled: TOP4 × 6特征 = 24维
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1119_172943**（20251119）

- 结果：OMR=0.2690，BMR=0.1544
- logs：[cachesim_sb3_1119_172943.log](cachesim_sb3_1119_172943.log) / [ac_sb3_1119_172943.log](ac_sb3_1119_172943.log)
- cachesim：req=45623306；int=200；mr_w=1.000 bmr_w=0.000

**1118_120239**（20251118）

- 结果：OMR=0.2999，BMR=0.1632
- logs：[cachesim_sb3_1118_120239.log](cachesim_sb3_1118_120239.log) / [ac_sb3_1118_120239.log](ac_sb3_1118_120239.log)
- cachesim：req=45623306；int=200；mr_w=1.000 bmr_w=0.000

**1113_020223**（20251113）

- 结果：OMR=0.3257，BMR=0.1703
- logs：[cachesim_sb3_1113_020223.log](cachesim_sb3_1113_020223.log)
- cachesim：req=45623306；int=200；mr_w=1.000 bmr_w=0.000

#### req=3000000（69 条）

| date | run | OMR | BMR | cfg | ref | note |
| ---: | --- | ---: | ---: | --- | --- | --- |
| 20260130 | 0130_000535 | 0.415580 | 0.238538 | SAC log1p=1 norm=1 cpd=0 irt=1 cacheF=0 candF=0 int=1000 | [cs](cachesim_sb3_0130_000535.log) [ac](ac_sb3_0130_000535.log) |  |
| 20260129 | 0129_210218 | 0.372619 | 0.216890 | SAC log1p=1 norm=1 cpd=0 irt=0 cacheF=0 candF=0 int=250 | [cs](cachesim_sb3_0129_210218.log) [ac](ac_sb3_0129_210218.log) |  |
| 20260129 | 0129_203548 | 0.367969 | 0.217511 | SAC log1p=1 norm=1 cpd=0 irt=0 cacheF=0 candF=0 int=250 | [cs](cachesim_sb3_0129_203548.log) [ac](ac_sb3_0129_203548.log) |  |
| 20251214 | 1214_211604 | 0.367988 | 0.217458 | SAC log1p=1 norm=1 cpd=0 irt=0 cacheF=0 candF=0 int=500 | [cs](cachesim_sb3_1214_211604.log) [ac](ac_sb3_1214_211604.log) |  |
| 20251214 | 1214_211231 | 0.367997 | 0.217405 | SAC log1p=1 norm=1 cpd=0 irt=0 cacheF=0 candF=0 int=500 | [cs](cachesim_sb3_1214_211231.log) [ac](ac_sb3_1214_211231.log) |  |
| 20251214 | 1214_210536 | 0.367998 | 0.217400 | SAC log1p=1 norm=1 cpd=0 irt=0 cacheF=0 candF=0 int=500 | [cs](cachesim_sb3_1214_210536.log) [ac](ac_sb3_1214_210536.log) |  |
| 20251214 | 1214_205956 | 0.3680 | 0.217603 | SAC log1p=1 norm=1 cpd=0 irt=0 cacheF=0 candF=0 int=500 | [cs](cachesim_sb3_1214_205956.log) [ac](ac_sb3_1214_205956.log) |  |
| 20251212 | 1212_115506 | 0.3685 | 0.2177 | TD3 log1p=1 norm=1 cpd=1 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1212_115506.log) [ac](ac_sb3_1212_115506.log) |  |
| 20251212 | 1212_113901 | 0.3691 | 0.2173 | PPO_LSTM log1p=1 norm=1 cpd=1 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1212_113901.log) [ac](ac_sb3_1212_113901.log) |  |
| 20251208 | 1208_214431 | 0.4496 | 0.2550 | PPO log1p=1 norm=1 cpd=1 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_214431.log) [ac](ac_sb3_1208_214431.log) |  |
| 20251208 | 1208_180037 | 0.3683 | 0.2212 | PPO log1p=1 norm=1 cpd=1 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_180037.log) [ac](ac_sb3_1208_180037.log) |  |
| 20251208 | 1208_175953 | 0.3687 | 0.2176 | PPO log1p=1 norm=1 cpd=1 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_175953.log) [ac](ac_sb3_1208_175953.log) |  |
| 20251208 | 1208_175816 | 0.4200 | 0.2244 | PPO log1p=1 norm=1 cpd=1 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_175816.log) [ac](ac_sb3_1208_175816.log) |  |
| 20251208 | 1208_175534 | 0.3684 | 0.2377 | PPO log1p=1 norm=1 cpd=1 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_175534.log) [ac](ac_sb3_1208_175534.log) |  |
| 20251208 | 1208_174737 | 0.3742 | 0.2155 | PPO log1p=1 norm=1 cpd=1 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_174737.log) [ac](ac_sb3_1208_174737.log) |  |
| 20251208 | 1208_172033 | 0.3694 | 0.2163 | PPO log1p=1 norm=1 cpd=1 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_172033.log) [ac](ac_sb3_1208_172033.log) |  |
| 20251208 | 1208_164957 | 0.3694 | 0.2163 | PPO log1p=1 norm=1 cpd=1 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_164957.log) [ac](ac_sb3_1208_164957.log) |  |
| 20251208 | 1208_163327 | 0.3915 | 0.2206 | PPO log1p=1 norm=1 cpd=1 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_163327.log) [ac](ac_sb3_1208_163327.log) |  |
| 20251208 | 1208_095231 | 0.3976 | 0.2350 | PPO cpd=1 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_095231.log) [ac](ac_sb3_1208_095231.log) |  |
| 20251208 | 1208_094611 | 0.3692 | 0.2165 | PPO cpd=1 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_094611.log) [ac](ac_sb3_1208_094611.log) |  |
| 20251208 | 1208_032052 | 0.3902 | 0.2277 | PPO cpd=0 irt=1 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_032052.log) [ac](ac_sb3_1208_032052.log) |  |
| 20251208 | 1208_024310 | 0.3973 | 0.2363 | PPO cpd=0 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_024310.log) [ac](ac_sb3_1208_024310.log) |  |
| 20251208 | 1208_022958 | 0.3724 | 0.2161 | SAC cpd=0 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_022958.log) [ac](ac_sb3_1208_022958.log) |  |
| 20251208 | 1208_021438 | 0.4104 | 0.2294 | PPO cpd=0 irt=1 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_021438.log) [ac](ac_sb3_1208_021438.log) |  |
| 20251208 | 1208_011625 | 0.3762 | 0.2154 | PPO cpd=0 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_011625.log) [ac](ac_sb3_1208_011625.log) |  |
| 20251206 | 1206_030519 | 0.3784 | 0.2172 | PPO cpd=0 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1206_030519.log) [ac](ac_sb3_1206_030519.log) |  |
| 20251204 | 1204_102246 | 0.4202 | 0.2315 | PPO int=200 | [cs](cachesim_sb3_1204_102246.log) [ac](ac_sb3_1204_102246.log) |  |
| 20251202 | 1202_175648 | 0.4157 | 0.2306 | PPO_LSTM int=200 | [cs](cachesim_sb3_1202_175648.log) [ac](ac_sb3_1202_175648.log) |  |
| 20251202 | 1202_174503 | 0.4185 | 0.2303 | PPO int=200 | [cs](cachesim_sb3_1202_174503.log) [ac](ac_sb3_1202_174503.log) |  |
| 20251202 | 1202_164231 | 0.4197 | 0.2304 | PPO_LSTM int=200 | [cs](cachesim_sb3_1202_164231.log) [ac](ac_sb3_1202_164231.log) |  |
| 20251202 | 1202_155720 | 0.4189 | 0.2313 | PPO_LSTM int=200 | [cs](cachesim_sb3_1202_155720.log) [ac](ac_sb3_1202_155720.log) |  |
| 20251202 | 1202_155326 | 0.4169 | 0.2305 | PPO int=200 | [cs](cachesim_sb3_1202_155326.log) [ac](ac_sb3_1202_155326.log) |  |
| 20251201 | 1201_223820 | 0.3987 | 0.2286 | SAC int=200 | [cs](cachesim_sb3_1201_223820.log) [ac](ac_sb3_1201_223820.log) |  |
| 20251201 | 1201_220435 | 0.4087 | 0.2250 | PPO int=200 | [cs](cachesim_sb3_1201_220435.log) [ac](ac_sb3_1201_220435.log) |  |
| 20251201 | 1201_215616 | 0.4094 | 0.2256 | PPO int=200 | [cs](cachesim_sb3_1201_215616.log) [ac](ac_sb3_1201_215616.log) |  |
| 20251201 | 1201_151211 | 0.4079 | 0.2254 | PPO int=200 | [cs](cachesim_sb3_1201_151211.log) [ac](ac_sb3_1201_151211.log) |  |
| 20251201 | 1201_112038 | 0.4091 | 0.2255 | PPO int=200 | [cs](cachesim_sb3_1201_112038.log) [ac](ac_sb3_1201_112038.log) |  |
| 20251129 | 1129_182010 | 0.4171 | 0.2302 | PPO int=200 | [cs](cachesim_sb3_1129_182010.log) [ac](ac_sb3_1129_182010.log) |  |
| 20251129 | 1129_181308 | 0.4075 | 0.2259 | PPO int=200 | [cs](cachesim_sb3_1129_181308.log) [ac](ac_sb3_1129_181308.log) |  |
| 20251129 | 1129_172109 | 0.4070 | 0.2266 | PPO int=200 | [cs](cachesim_sb3_1129_172109.log) [ac](ac_sb3_1129_172109.log) |  |
| 20251129 | 1129_155418 | 0.3968 | 0.2296 | PPO int=200 | [cs](cachesim_sb3_1129_155418.log) [ac](ac_sb3_1129_155418.log) |  |
| 20251129 | 1129_152328 | 0.3993 | 0.2279 | PPO int=200 | [cs](cachesim_sb3_1129_152328.log) [ac](ac_sb3_1129_152328.log) |  |
| 20251128 | 1128_174927 | 0.4193 | 0.2305 | PPO int=200 | [cs](cachesim_sb3_1128_174927.log) [ac](ac_sb3_1128_174927.log) |  |
| 20251128 | 1128_172319 | 0.4170 | 0.2307 | PPO int=200 | [cs](cachesim_sb3_1128_172319.log) [ac](ac_sb3_1128_172319.log) |  |
| 20251128 | 1128_153856 | 0.4177 | 0.2307 | PPO int=200 | [cs](cachesim_sb3_1128_153856.log) [ac](ac_sb3_1128_153856.log) |  |
| 20251127 | 1127_234011 | 0.4247 | 0.2332 | PPO int=200 | [cs](cachesim_sb3_1127_234011.log) [ac](ac_sb3_1127_234011.log) |  |
| 20251127 | 1127_223446 | 0.4193 | 0.2340 | PPO int=200 | [cs](cachesim_sb3_1127_223446.log) [ac](ac_sb3_1127_223446.log) |  |
| 20251127 | 1127_200604 | 0.4242 | 0.2339 | SAC int=200 | [cs](cachesim_sb3_1127_200604.log) [ac](ac_sb3_1127_200604.log) |  |
| 20251127 | 1127_193851 | 0.4272 | 0.2338 | SAC int=200 | [cs](cachesim_sb3_1127_193851.log) [ac](ac_sb3_1127_193851.log) |  |
| 20251126 | 1126_184728 | 0.4275 | 0.2341 | SAC int=200 | [cs](cachesim_sb3_1126_184728.log) [ac](ac_sb3_1126_184728.log) |  |
| 20251125 | 1125_195648 | 0.4239 | 0.2320 | int=200 | [cs](cachesim_sb3_1125_195648.log) [ac](ac_sb3_1125_195648.log) |  |
| 20251125 | 1125_195436 | 0.4238 | 0.2316 | int=200 | [cs](cachesim_sb3_1125_195436.log) [ac](ac_sb3_1125_195436.log) |  |
| 20251125 | 1125_195201 | 0.4265 | 0.2332 | int=200 | [cs](cachesim_sb3_1125_195201.log) [ac](ac_sb3_1125_195201.log) |  |
| 20251124 | 1124_170730 | 0.4257 | 0.2328 | int=200 | [cs](cachesim_sb3_1124_170730.log) [ac](ac_sb3_1124_170730.log) |  |
| 20251124 | 1124_170424 | 0.4234 | 0.2317 | int=200 | [cs](cachesim_sb3_1124_170424.log) [ac](ac_sb3_1124_170424.log) |  |
| 20251124 | 1124_170207 | 0.4259 | 0.2324 | int=200 | [cs](cachesim_sb3_1124_170207.log) [ac](ac_sb3_1124_170207.log) |  |
| 20251124 | 1124_162845 | 0.4045 | 0.2240 | int=200 | [cs](cachesim_sb3_1124_162845.log) [ac](ac_sb3_1124_162845.log) |  |
| 20251124 | 1124_162539 | 0.4270 | 0.2337 | int=200 | [cs](cachesim_sb3_1124_162539.log) [ac](ac_sb3_1124_162539.log) |  |
| 20251124 | 1124_162416 | 0.4283 | 0.2344 | int=200 | [cs](cachesim_sb3_1124_162416.log) [ac](ac_sb3_1124_162416.log) |  |
| 20251124 | 1124_162219 | 0.4247 | 0.2328 | int=200 | [cs](cachesim_sb3_1124_162219.log) [ac](ac_sb3_1124_162219.log) |  |
| 20251124 | 1124_105600 | 0.4045 | 0.2240 | int=200 | [cs](cachesim_sb3_1124_105600.log) [ac](ac_sb3_1124_105600.log) |  |
| 20251124 | 1124_105515 | 0.4298 | 0.2335 | int=200 | [cs](cachesim_sb3_1124_105515.log) [ac](ac_sb3_1124_105515.log) |  |
| 20251121 | 1121_171039 | 0.3911 | 0.2216 | int=200 | [cs](cachesim_sb3_1121_171039.log) [ac](ac_sb3_1121_171039.log) |  |
| 20251121 | 1121_170810 | 0.3930 | 0.2221 | int=200 | [cs](cachesim_sb3_1121_170810.log) [ac](ac_sb3_1121_170810.log) |  |
| 20251121 | 1121_142212 | 0.3975 | 0.2234 | int=200 | [cs](cachesim_sb3_1121_142212.log) [ac](ac_sb3_1121_142212.log) |  |
| 20251121 | 1121_142043 | 0.4026 | 0.2246 | int=200 | [cs](cachesim_sb3_1121_142043.log) [ac](ac_sb3_1121_142043.log) |  |
| 20251121 | 1121_141842 | 0.3906 | 0.2215 | int=200 | [cs](cachesim_sb3_1121_141842.log) [ac](ac_sb3_1121_141842.log) |  |
| 20251121 | 1121_140853 | 0.3901 | 0.2216 | int=200 | [cs](cachesim_sb3_1121_140853.log) [ac](ac_sb3_1121_140853.log) |  |
| 20251121 | 1121_134849 | 0.3805 | 0.2227 | int=200 | [cs](cachesim_sb3_1121_134849.log) [ac](ac_sb3_1121_134849.log) |  |

##### 逐日志明细（req=3000000）

**0130_000535**（20260130）

- 结果：OMR=0.415580，BMR=0.238538
- logs：[cachesim_sb3_0130_000535.log](cachesim_sb3_0130_000535.log) / [ac_sb3_0130_000535.log](ac_sb3_0130_000535.log)
- cachesim：req=3000000；int=1000；mr_w=1.000 bmr_w=0.000；log1p=1；recip=0；norm=1；irt=1；cpd=0；cacheF=0；candF=0；state=1200->1202
 - [LOH INIT] Wait mode: default (BLOCKED)
 - [LOH INIT] Size data structure: SIZE_BUCKETS (全量分桶)
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**0129_210218**（20260129）

- 结果：OMR=0.372619，BMR=0.216890
- logs：[cachesim_sb3_0129_210218.log](cachesim_sb3_0129_210218.log) / [ac_sb3_0129_210218.log](ac_sb3_0129_210218.log)
- cachesim：req=3000000；int=250；mr_w=1.000 bmr_w=0.000；log1p=1；recip=0；norm=1；irt=0；cpd=0；cacheF=0；candF=0；state=600->602
 - [LOH INIT] Wait mode: default (BLOCKED)
 - [LOH INIT] Size data structure: SIZE_BUCKETS (全量分桶)
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**0129_203548**（20260129）

- 结果：OMR=0.367969，BMR=0.217511
- logs：[cachesim_sb3_0129_203548.log](cachesim_sb3_0129_203548.log) / [ac_sb3_0129_203548.log](ac_sb3_0129_203548.log)
- cachesim：req=3000000；int=250；mr_w=1.000 bmr_w=0.000；log1p=1；recip=0；norm=1；irt=0；cpd=0；cacheF=0；candF=0；state=600->602
 - [LOH INIT] Wait mode: default (BLOCKED)
 - [LOH INIT] Size data structure: SIZE_BUCKETS (全量分桶)
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**1214_211604**（20251214）

- 结果：OMR=0.367988，BMR=0.217458
- logs：[cachesim_sb3_1214_211604.log](cachesim_sb3_1214_211604.log) / [ac_sb3_1214_211604.log](ac_sb3_1214_211604.log)
- cachesim：req=3000000；int=500；mr_w=1.000 bmr_w=0.000；log1p=1；recip=0；norm=1；irt=0；cpd=0；cacheF=0；candF=0；state=600->602
 - [LOH INIT] Wait mode: default (BLOCKED)
 - [LOH INIT] Size data structure: SIZE_BUCKETS (全量分桶)
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**1214_211231**（20251214）

- 结果：OMR=0.367997，BMR=0.217405
- logs：[cachesim_sb3_1214_211231.log](cachesim_sb3_1214_211231.log) / [ac_sb3_1214_211231.log](ac_sb3_1214_211231.log)
- cachesim：req=3000000；int=500；mr_w=1.000 bmr_w=0.000；log1p=1；recip=0；norm=1；irt=0；cpd=0；cacheF=0；candF=0；state=600->602
 - [LOH INIT] Wait mode: default (BLOCKED)
 - [LOH INIT] Size data structure: SIZE_BUCKETS (全量分桶)
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**1214_210536**（20251214）

- 结果：OMR=0.367998，BMR=0.217400
- logs：[cachesim_sb3_1214_210536.log](cachesim_sb3_1214_210536.log) / [ac_sb3_1214_210536.log](ac_sb3_1214_210536.log)
- cachesim：req=3000000；int=500；mr_w=1.000 bmr_w=0.000；log1p=1；recip=0；norm=1；irt=0；cpd=0；cacheF=0；candF=0；state=600->602
 - [LOH INIT] Wait mode: default (BLOCKED)
 - [LOH INIT] Size data structure: SIZE_BUCKETS (全量分桶)
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**1214_205956**（20251214）

- 结果：OMR=0.3680，BMR=0.217603
- logs：[cachesim_sb3_1214_205956.log](cachesim_sb3_1214_205956.log) / [ac_sb3_1214_205956.log](ac_sb3_1214_205956.log)
- cachesim：req=3000000；int=500；mr_w=1.000 bmr_w=0.000；log1p=1；recip=0；norm=1；irt=0；cpd=0；cacheF=0；candF=0；state=600->602
 - [LOH INIT] Wait mode: default (BLOCKED)
 - [LOH INIT] Size data structure: SIZE_BUCKETS (全量分桶)
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**1212_115506**（20251212）

- 结果：OMR=0.3685，BMR=0.2177
- logs：[cachesim_sb3_1212_115506.log](cachesim_sb3_1212_115506.log) / [ac_sb3_1212_115506.log](ac_sb3_1212_115506.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000；log1p=1；recip=0；norm=1；irt=0；cpd=1；cacheF=0；candF=0；state=600->602
 - [LOH INIT] Wait mode: default (BLOCKED)
 - [LOH INIT] Size data structure: SIZE_BUCKETS (全量分桶)
- RL：algo=TD3；batch=256；lr=0.0003；gamma=0.99；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - policy_delay: 2
 - - target_policy_noise: 0.2
 - - policy.hidden_layers: [256, 256, 6]
 - - policy.activation_fn: ReLU

**1212_113901**（20251212）

- 结果：OMR=0.3691，BMR=0.2173
- logs：[cachesim_sb3_1212_113901.log](cachesim_sb3_1212_113901.log) / [ac_sb3_1212_113901.log](ac_sb3_1212_113901.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000；log1p=1；recip=0；norm=1；irt=0；cpd=1；cacheF=0；candF=0；state=600->602
 - [LOH INIT] Wait mode: default (BLOCKED)
 - [LOH INIT] Size data structure: SIZE_BUCKETS (全量分桶)
- RL：algo=PPO_LSTM；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1208_214431**（20251208）

- 结果：OMR=0.4496，BMR=0.2550
- logs：[cachesim_sb3_1208_214431.log](cachesim_sb3_1208_214431.log) / [ac_sb3_1208_214431.log](ac_sb3_1208_214431.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000；log1p=1；recip=0；norm=1；irt=0；cpd=1；cacheF=0；candF=0；state=0->2
 - [LOH INIT] Wait mode: default (BLOCKED)
 - [LOH INIT] Size data structure: SIZE_BUCKETS (全量分桶)
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1208_180037**（20251208）

- 结果：OMR=0.3683，BMR=0.2212
- logs：[cachesim_sb3_1208_180037.log](cachesim_sb3_1208_180037.log) / [ac_sb3_1208_180037.log](ac_sb3_1208_180037.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000；log1p=1；recip=0；norm=1；irt=0；cpd=1；cacheF=0；candF=0；state=0->2
 - [LOH INIT] Wait mode: default (BLOCKED)
 - [LOH INIT] Size data structure: SIZE_BUCKETS (全量分桶)
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1208_175953**（20251208）

- 结果：OMR=0.3687，BMR=0.2176
- logs：[cachesim_sb3_1208_175953.log](cachesim_sb3_1208_175953.log) / [ac_sb3_1208_175953.log](ac_sb3_1208_175953.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000；log1p=1；recip=0；norm=1；irt=0；cpd=1；cacheF=0；candF=0；state=0->2
 - [LOH INIT] Wait mode: default (BLOCKED)
 - [LOH INIT] Size data structure: SIZE_BUCKETS (全量分桶)
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1208_175816**（20251208）

- 结果：OMR=0.4200，BMR=0.2244
- logs：[cachesim_sb3_1208_175816.log](cachesim_sb3_1208_175816.log) / [ac_sb3_1208_175816.log](ac_sb3_1208_175816.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000；log1p=1；recip=0；norm=1；irt=0；cpd=1；cacheF=0；candF=0；state=0->2
 - [LOH INIT] Wait mode: default (BLOCKED)
 - [LOH INIT] Size data structure: SIZE_BUCKETS (全量分桶)
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1208_175534**（20251208）

- 结果：OMR=0.3684，BMR=0.2377
- logs：[cachesim_sb3_1208_175534.log](cachesim_sb3_1208_175534.log) / [ac_sb3_1208_175534.log](ac_sb3_1208_175534.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000；log1p=1；recip=0；norm=1；irt=0；cpd=1；cacheF=0；candF=0；state=0->2
 - [LOH INIT] Wait mode: default (BLOCKED)
 - [LOH INIT] Size data structure: SIZE_BUCKETS (全量分桶)
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1208_174737**（20251208）

- 结果：OMR=0.3742，BMR=0.2155
- logs：[cachesim_sb3_1208_174737.log](cachesim_sb3_1208_174737.log) / [ac_sb3_1208_174737.log](ac_sb3_1208_174737.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000；log1p=1；recip=0；norm=1；irt=0；cpd=1；cacheF=0；candF=0；state=0->2
 - [LOH INIT] Wait mode: default (BLOCKED)
 - [LOH INIT] Size data structure: SIZE_BUCKETS (全量分桶)
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1208_172033**（20251208）

- 结果：OMR=0.3694，BMR=0.2163
- logs：[cachesim_sb3_1208_172033.log](cachesim_sb3_1208_172033.log) / [ac_sb3_1208_172033.log](ac_sb3_1208_172033.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000；log1p=1；recip=0；norm=1；irt=0；cpd=1；cacheF=0；candF=0；state=0->2
 - [LOH INIT] Wait mode: default (BLOCKED)
 - [LOH INIT] Size data structure: SIZE_BUCKETS (全量分桶)
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1208_164957**（20251208）

- 结果：OMR=0.3694，BMR=0.2163
- logs：[cachesim_sb3_1208_164957.log](cachesim_sb3_1208_164957.log) / [ac_sb3_1208_164957.log](ac_sb3_1208_164957.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000；log1p=1；recip=0；norm=1；irt=0；cpd=1；cacheF=0；candF=0；state=600->614
 - [LOH INIT] AvgTopK enabled: TOP4 × 6特征 = 24维
 - [LOH INIT] Wait mode: default (BLOCKED)
 - [LOH INIT] Size data structure: SIZE_BUCKETS (全量分桶)
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1208_163327**（20251208）

- 结果：OMR=0.3915，BMR=0.2206
- logs：[cachesim_sb3_1208_163327.log](cachesim_sb3_1208_163327.log) / [ac_sb3_1208_163327.log](ac_sb3_1208_163327.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000；log1p=1；recip=0；norm=1；irt=0；cpd=1；cacheF=0；candF=0；state=0->14
 - [LOH INIT] AvgTopK enabled: TOP4 × 6特征 = 24维
 - [LOH INIT] Wait mode: default (BLOCKED)
 - [LOH INIT] Size data structure: SIZE_BUCKETS (全量分桶)
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1208_095231**（20251208）

- 结果：OMR=0.3976，BMR=0.2350
- logs：[cachesim_sb3_1208_095231.log](cachesim_sb3_1208_095231.log) / [ac_sb3_1208_095231.log](ac_sb3_1208_095231.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000；irt=0；cpd=1；cacheF=0；candF=0；state=0->14
 - [LOH INIT] AvgTopK enabled: TOP4 × 6特征 = 24维
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1208_094611**（20251208）

- 结果：OMR=0.3692，BMR=0.2165
- logs：[cachesim_sb3_1208_094611.log](cachesim_sb3_1208_094611.log) / [ac_sb3_1208_094611.log](ac_sb3_1208_094611.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000；irt=0；cpd=1；cacheF=0；candF=0；state=0->14
 - [LOH INIT] AvgTopK enabled: TOP4 × 6特征 = 24维
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1208_032052**（20251208）

- 结果：OMR=0.3902，BMR=0.2277
- logs：[cachesim_sb3_1208_032052.log](cachesim_sb3_1208_032052.log) / [ac_sb3_1208_032052.log](ac_sb3_1208_032052.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000；irt=1；cpd=0；cacheF=0；candF=0；state=0->26
 - [LOH INIT] AvgTopK enabled: TOP4 × 6特征 = 24维
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1208_024310**（20251208）

- 结果：OMR=0.3973，BMR=0.2363
- logs：[cachesim_sb3_1208_024310.log](cachesim_sb3_1208_024310.log) / [ac_sb3_1208_024310.log](ac_sb3_1208_024310.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000；irt=0；cpd=0；cacheF=0；candF=0；state=0->14
 - [LOH INIT] AvgTopK enabled: TOP4 × 6特征 = 24维
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1208_022958**（20251208）

- 结果：OMR=0.3724，BMR=0.2161
- logs：[cachesim_sb3_1208_022958.log](cachesim_sb3_1208_022958.log) / [ac_sb3_1208_022958.log](ac_sb3_1208_022958.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000；irt=0；cpd=0；cacheF=0；candF=0；state=0->14
 - [LOH INIT] AvgTopK enabled: TOP4 × 6特征 = 24维
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**1208_021438**（20251208）

- 结果：OMR=0.4104，BMR=0.2294
- logs：[cachesim_sb3_1208_021438.log](cachesim_sb3_1208_021438.log) / [ac_sb3_1208_021438.log](ac_sb3_1208_021438.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000；irt=1；cpd=0；cacheF=0；candF=0；state=0->26
 - [LOH INIT] AvgTopK enabled: TOP4 × 6特征 = 24维
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1208_011625**（20251208）

- 结果：OMR=0.3762，BMR=0.2154
- logs：[cachesim_sb3_1208_011625.log](cachesim_sb3_1208_011625.log) / [ac_sb3_1208_011625.log](ac_sb3_1208_011625.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000；irt=0；cpd=0；cacheF=0；candF=0；state=0->14
 - [LOH INIT] AvgTopK enabled: TOP4 × 6特征 = 24维
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1206_030519**（20251206）

- 结果：OMR=0.3784，BMR=0.2172
- logs：[cachesim_sb3_1206_030519.log](cachesim_sb3_1206_030519.log) / [ac_sb3_1206_030519.log](ac_sb3_1206_030519.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000；irt=0；cpd=0；cacheF=0；candF=0；state=0->14
 - [LOH INIT] AvgTopK enabled: TOP4 × 6特征 = 24维
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1204_102246**（20251204）

- 结果：OMR=0.4202，BMR=0.2315
- logs：[cachesim_sb3_1204_102246.log](cachesim_sb3_1204_102246.log) / [ac_sb3_1204_102246.log](ac_sb3_1204_102246.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1202_175648**（20251202）

- 结果：OMR=0.4157，BMR=0.2306
- logs：[cachesim_sb3_1202_175648.log](cachesim_sb3_1202_175648.log) / [ac_sb3_1202_175648.log](ac_sb3_1202_175648.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=PPO_LSTM；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1202_174503**（20251202）

- 结果：OMR=0.4185，BMR=0.2303
- logs：[cachesim_sb3_1202_174503.log](cachesim_sb3_1202_174503.log) / [ac_sb3_1202_174503.log](ac_sb3_1202_174503.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1202_164231**（20251202）

- 结果：OMR=0.4197，BMR=0.2304
- logs：[cachesim_sb3_1202_164231.log](cachesim_sb3_1202_164231.log) / [ac_sb3_1202_164231.log](ac_sb3_1202_164231.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=PPO_LSTM；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1202_155720**（20251202）

- 结果：OMR=0.4189，BMR=0.2313
- logs：[cachesim_sb3_1202_155720.log](cachesim_sb3_1202_155720.log) / [ac_sb3_1202_155720.log](ac_sb3_1202_155720.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=PPO_LSTM；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1202_155326**（20251202）

- 结果：OMR=0.4169，BMR=0.2305
- logs：[cachesim_sb3_1202_155326.log](cachesim_sb3_1202_155326.log) / [ac_sb3_1202_155326.log](ac_sb3_1202_155326.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1201_223820**（20251201）

- 结果：OMR=0.3987，BMR=0.2286
- logs：[cachesim_sb3_1201_223820.log](cachesim_sb3_1201_223820.log) / [ac_sb3_1201_223820.log](ac_sb3_1201_223820.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**1201_220435**（20251201）

- 结果：OMR=0.4087，BMR=0.2250
- logs：[cachesim_sb3_1201_220435.log](cachesim_sb3_1201_220435.log) / [ac_sb3_1201_220435.log](ac_sb3_1201_220435.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
 - [LOH INIT] AvgTopK enabled: TOP4 × 6特征 = 24维
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1201_215616**（20251201）

- 结果：OMR=0.4094，BMR=0.2256
- logs：[cachesim_sb3_1201_215616.log](cachesim_sb3_1201_215616.log) / [ac_sb3_1201_215616.log](ac_sb3_1201_215616.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
 - [LOH INIT] AvgTopK enabled: TOP4 × 6特征 = 24维
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1201_151211**（20251201）

- 结果：OMR=0.4079，BMR=0.2254
- logs：[cachesim_sb3_1201_151211.log](cachesim_sb3_1201_151211.log) / [ac_sb3_1201_151211.log](ac_sb3_1201_151211.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1201_112038**（20251201）

- 结果：OMR=0.4091，BMR=0.2255
- logs：[cachesim_sb3_1201_112038.log](cachesim_sb3_1201_112038.log) / [ac_sb3_1201_112038.log](ac_sb3_1201_112038.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1129_182010**（20251129）

- 结果：OMR=0.4171，BMR=0.2302
- logs：[cachesim_sb3_1129_182010.log](cachesim_sb3_1129_182010.log) / [ac_sb3_1129_182010.log](ac_sb3_1129_182010.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1129_181308**（20251129）

- 结果：OMR=0.4075，BMR=0.2259
- logs：[cachesim_sb3_1129_181308.log](cachesim_sb3_1129_181308.log) / [ac_sb3_1129_181308.log](ac_sb3_1129_181308.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1129_172109**（20251129）

- 结果：OMR=0.4070，BMR=0.2266
- logs：[cachesim_sb3_1129_172109.log](cachesim_sb3_1129_172109.log) / [ac_sb3_1129_172109.log](ac_sb3_1129_172109.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1129_155418**（20251129）

- 结果：OMR=0.3968，BMR=0.2296
- logs：[cachesim_sb3_1129_155418.log](cachesim_sb3_1129_155418.log) / [ac_sb3_1129_155418.log](ac_sb3_1129_155418.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1129_152328**（20251129）

- 结果：OMR=0.3993，BMR=0.2279
- logs：[cachesim_sb3_1129_152328.log](cachesim_sb3_1129_152328.log) / [ac_sb3_1129_152328.log](ac_sb3_1129_152328.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1128_174927**（20251128）

- 结果：OMR=0.4193，BMR=0.2305
- logs：[cachesim_sb3_1128_174927.log](cachesim_sb3_1128_174927.log) / [ac_sb3_1128_174927.log](ac_sb3_1128_174927.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
 - [LOH INIT] AvgTopK enabled: TOP4 × 6特征 = 24维
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1128_172319**（20251128）

- 结果：OMR=0.4170，BMR=0.2307
- logs：[cachesim_sb3_1128_172319.log](cachesim_sb3_1128_172319.log) / [ac_sb3_1128_172319.log](ac_sb3_1128_172319.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1128_153856**（20251128）

- 结果：OMR=0.4177，BMR=0.2307
- logs：[cachesim_sb3_1128_153856.log](cachesim_sb3_1128_153856.log) / [ac_sb3_1128_153856.log](ac_sb3_1128_153856.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1127_234011**（20251127）

- 结果：OMR=0.4247，BMR=0.2332
- logs：[cachesim_sb3_1127_234011.log](cachesim_sb3_1127_234011.log) / [ac_sb3_1127_234011.log](ac_sb3_1127_234011.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
 - [LOH INIT] AvgTopK enabled: TOP4 × 6特征 = 24维
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1127_223446**（20251127）

- 结果：OMR=0.4193，BMR=0.2340
- logs：[cachesim_sb3_1127_223446.log](cachesim_sb3_1127_223446.log) / [ac_sb3_1127_223446.log](ac_sb3_1127_223446.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1127_200604**（20251127）

- 结果：OMR=0.4242，BMR=0.2339
- logs：[cachesim_sb3_1127_200604.log](cachesim_sb3_1127_200604.log) / [ac_sb3_1127_200604.log](ac_sb3_1127_200604.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**1127_193851**（20251127）

- 结果：OMR=0.4272，BMR=0.2338
- logs：[cachesim_sb3_1127_193851.log](cachesim_sb3_1127_193851.log) / [ac_sb3_1127_193851.log](ac_sb3_1127_193851.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**1126_184728**（20251126）

- 结果：OMR=0.4275，BMR=0.2341
- logs：[cachesim_sb3_1126_184728.log](cachesim_sb3_1126_184728.log) / [ac_sb3_1126_184728.log](ac_sb3_1126_184728.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**1125_195648**（20251125）

- 结果：OMR=0.4239，BMR=0.2320
- logs：[cachesim_sb3_1125_195648.log](cachesim_sb3_1125_195648.log) / [ac_sb3_1125_195648.log](ac_sb3_1125_195648.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：batch=32；lr=0.0001；ent=0.02；state=194；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)

**1125_195436**（20251125）

- 结果：OMR=0.4238，BMR=0.2316
- logs：[cachesim_sb3_1125_195436.log](cachesim_sb3_1125_195436.log) / [ac_sb3_1125_195436.log](ac_sb3_1125_195436.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：batch=32；lr=0.0001；ent=0.02；state=194；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)

**1125_195201**（20251125）

- 结果：OMR=0.4265，BMR=0.2332
- logs：[cachesim_sb3_1125_195201.log](cachesim_sb3_1125_195201.log) / [ac_sb3_1125_195201.log](ac_sb3_1125_195201.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：batch=32；lr=0.0001；ent=0.02；state=194；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)

**1124_170730**（20251124）

- 结果：OMR=0.4257，BMR=0.2328
- logs：[cachesim_sb3_1124_170730.log](cachesim_sb3_1124_170730.log) / [ac_sb3_1124_170730.log](ac_sb3_1124_170730.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000

**1124_170424**（20251124）

- 结果：OMR=0.4234，BMR=0.2317
- logs：[cachesim_sb3_1124_170424.log](cachesim_sb3_1124_170424.log) / [ac_sb3_1124_170424.log](ac_sb3_1124_170424.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000

**1124_170207**（20251124）

- 结果：OMR=0.4259，BMR=0.2324
- logs：[cachesim_sb3_1124_170207.log](cachesim_sb3_1124_170207.log) / [ac_sb3_1124_170207.log](ac_sb3_1124_170207.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000

**1124_162845**（20251124）

- 结果：OMR=0.4045，BMR=0.2240
- logs：[cachesim_sb3_1124_162845.log](cachesim_sb3_1124_162845.log) / [ac_sb3_1124_162845.log](ac_sb3_1124_162845.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000

**1124_162539**（20251124）

- 结果：OMR=0.4270，BMR=0.2337
- logs：[cachesim_sb3_1124_162539.log](cachesim_sb3_1124_162539.log) / [ac_sb3_1124_162539.log](ac_sb3_1124_162539.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：batch=32；lr=0.0001；ent=0.02；state=38；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)

**1124_162416**（20251124）

- 结果：OMR=0.4283，BMR=0.2344
- logs：[cachesim_sb3_1124_162416.log](cachesim_sb3_1124_162416.log) / [ac_sb3_1124_162416.log](ac_sb3_1124_162416.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：batch=32；lr=0.0001；ent=0.02；state=38；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)

**1124_162219**（20251124）

- 结果：OMR=0.4247，BMR=0.2328
- logs：[cachesim_sb3_1124_162219.log](cachesim_sb3_1124_162219.log) / [ac_sb3_1124_162219.log](ac_sb3_1124_162219.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：batch=32；lr=0.0001；ent=0.02；state=38；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)

**1124_105600**（20251124）

- 结果：OMR=0.4045，BMR=0.2240
- logs：[cachesim_sb3_1124_105600.log](cachesim_sb3_1124_105600.log) / [ac_sb3_1124_105600.log](ac_sb3_1124_105600.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000

**1124_105515**（20251124）

- 结果：OMR=0.4298，BMR=0.2335
- logs：[cachesim_sb3_1124_105515.log](cachesim_sb3_1124_105515.log) / [ac_sb3_1124_105515.log](ac_sb3_1124_105515.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000

**1121_171039**（20251121）

- 结果：OMR=0.3911，BMR=0.2216
- logs：[cachesim_sb3_1121_171039.log](cachesim_sb3_1121_171039.log) / [ac_sb3_1121_171039.log](ac_sb3_1121_171039.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：batch=32；lr=0.0001；ent=0.02；state=38；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)

**1121_170810**（20251121）

- 结果：OMR=0.3930，BMR=0.2221
- logs：[cachesim_sb3_1121_170810.log](cachesim_sb3_1121_170810.log) / [ac_sb3_1121_170810.log](ac_sb3_1121_170810.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：batch=32；lr=0.0001；ent=0.02；state=38；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)

**1121_142212**（20251121）

- 结果：OMR=0.3975，BMR=0.2234
- logs：[cachesim_sb3_1121_142212.log](cachesim_sb3_1121_142212.log) / [ac_sb3_1121_142212.log](ac_sb3_1121_142212.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：batch=32；lr=0.0001；ent=0.02；state=38；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)

**1121_142043**（20251121）

- 结果：OMR=0.4026，BMR=0.2246
- logs：[cachesim_sb3_1121_142043.log](cachesim_sb3_1121_142043.log) / [ac_sb3_1121_142043.log](ac_sb3_1121_142043.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：batch=32；lr=0.0001；ent=0.02；state=38；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)

**1121_141842**（20251121）

- 结果：OMR=0.3906，BMR=0.2215
- logs：[cachesim_sb3_1121_141842.log](cachesim_sb3_1121_141842.log) / [ac_sb3_1121_141842.log](ac_sb3_1121_141842.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：batch=32；lr=0.0001；ent=0.02；state=38；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)

**1121_140853**（20251121）

- 结果：OMR=0.3901，BMR=0.2216
- logs：[cachesim_sb3_1121_140853.log](cachesim_sb3_1121_140853.log) / [ac_sb3_1121_140853.log](ac_sb3_1121_140853.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：batch=32；lr=0.0001；ent=0.02；state=38；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)

**1121_134849**（20251121）

- 结果：OMR=0.3805，BMR=0.2227
- logs：[cachesim_sb3_1121_134849.log](cachesim_sb3_1121_134849.log) / [ac_sb3_1121_134849.log](ac_sb3_1121_134849.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：batch=32；lr=0.0001；ent=0.02；state=38；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)


<!-- ROOT_LOGS_END -->

#### 逐 sweep 细表

**meta_3m_1212_152109**（来源：sweeps/meta_3m_1212_152109/results.csv）

通用配置：scale=1.0；表内 `cfg` 仅列差异
| idx | n | OMR | BMR | cfg |
| ---: | ---: | ---: | ---: | --- |
| 1 | 3 | 0.383033 | 0.242300 | TD3 |
| 2 | 3 | 0.388733 | 0.247800 | TD3 |
| 3 | 3 | 0.387933 | 0.234900 | SAC |
| 4 | 3 | 0.385200 | 0.235067 | SAC |


通用配置：SAC cpd=1 irt=1 int=500；表内 `cfg` 仅列差异
| idx | n | OMR | BMR | cfg |
| ---: | ---: | ---: | ---: | --- |
| 1 | 2 | 0.400400 | 0.205900 | — |
| 2 | 2 | 0.400400 | 0.205700 | — |
| 3 | 2 | 0.400400 | 0.205700 | — |
| 4 | 2 | 0.400400 | 0.206550 | temp=0.7 |
| 5 | 2 | 0.400400 | 0.205700 | temp=0.5 |
| 6 | 2 | 0.400400 | 0.205550 | scale=2.0 |
| 7 | 2 | 0.400400 | 0.205750 | — |
| 8 | 2 | 0.400400 | 0.205750 | temp=0.7 |

**meta_reward_algo_v4_1214_014136**（来源：sweeps/meta_reward_algo_v4_1214_014136/results.csv）

| idx | n | OMR | BMR | cfg |
| ---: | ---: | ---: | ---: | --- |
| 1 | 2 | NA | NA | cpd=0 irt=0 int=500 |


通用配置：scale=1.0；表内 `cfg` 仅列差异
| idx | n | OMR | BMR | cfg |
| ---: | ---: | ---: | ---: | --- |
| 1 | 2 | NA | NA | TD3 |
| 2 | 2 | NA | NA | TD3 |
| 3 | 2 | NA | NA | SAC |
| 4 | 2 | NA | NA | SAC |


通用配置：scale=1.0；表内 `cfg` 仅列差异
| idx | n | OMR | BMR | cfg |
| ---: | ---: | ---: | ---: | --- |
| 1 | 2 | 0.512450 | 0.241800 | TD3 |
| 2 | 2 | 0.509150 | 0.241700 | TD3 |
| 3 | 2 | 0.511500 | 0.243250 | SAC |
| 4 | 2 | 0.505550 | 0.247750 | SAC |


（results.csv 仅表头，无数据行）

**meta_algo_expand_v6_1215_011924**（来源：sweeps/meta_algo_expand_v6_1215_011924/results.csv）

通用配置：SAC norm=1 temp=1.0 scale=1.0；表内 `cfg` 仅列差异
| idx | n | OMR | BMR | cfg |
| ---: | ---: | ---: | ---: | --- |
| 1 | 2 | 0.269697 | 0.164610 | int=250 |
| 2 | 2 | 0.269722 | 0.164361 | int=200 |
| 3 | 2 | 0.269705 | 0.164794 | int=300 |

**rec3m_1212_133521**（来源：sweeps/rec3m_1212_133521/results.csv）

通用配置：TD3 cpd=1 irt=1 norm=1；表内 `cfg` 仅列差异
| idx | n | OMR | BMR | cfg |
| ---: | ---: | ---: | ---: | --- |
| 1 | 1 | 0.368500 | 0.219000 | temp=1.0 scale=1.0 |
| 2 | 1 | 0.374900 | 0.228200 | temp=0.3 scale=3.0 |
| 3 | 1 | 0.522800 | 0.542300 | temp=0.7 scale=2.0 |
| 4 | 1 | 0.371800 | 0.219000 | temp=0.5 scale=3.0 |

**meta_best_action_scale_r2_20251222_183925**（来源：sweeps/meta_best_action_scale_r2_20251222_183925/results.csv）

通用配置：SAC norm=1 int=200 temp=1.3；表内 `cfg` 仅列差异
| idx | n | OMR | BMR | cfg |
| ---: | ---: | ---: | ---: | --- |
| 1 | 2 | 0.367959 | 0.217575 | scale=0.5 |
| 2 | 2 | 0.367959 | 0.217475 | scale=0.7 |
| 3 | 2 | 0.367961 | 0.217590 | scale=1.0 |
| 4 | 2 | 0.367969 | 0.217551 | scale=1.3 |
| 5 | 2 | 0.367976 | 0.217550 | scale=1.6 |

**meta_best_action_scale_winner_repeat5_20251222_201349**（来源：sweeps/meta_best_action_scale_winner_repeat5_20251222_201349/results.csv）

| idx | n | OMR | BMR | cfg |
| ---: | ---: | ---: | ---: | --- |
| 1 | 5 | 0.367959 | 0.217551 | SAC norm=1 int=200 temp=1.3 scale=0.5 |

**meta_best_grid_interval_temp_r2_20251217_234028**（来源：sweeps/meta_best_grid_interval_temp_r2_20251217_234028/results.csv）

通用配置：SAC norm=1 scale=1.0；表内 `cfg` 仅列差异
| idx | n | OMR | BMR | cfg |
| ---: | ---: | ---: | ---: | --- |
| 1 | 2 | 0.367977 | 0.217512 | int=200 temp=0.8 |
| 2 | 2 | 0.367966 | 0.217520 | int=200 temp=1.0 |
| 3 | 2 | 0.367961 | 0.217590 | int=200 temp=1.3 |
| 4 | 2 | 0.367981 | 0.217605 | int=250 temp=0.8 |
| 5 | 2 | 0.367968 | 0.217553 | int=250 temp=1.0 |
| 6 | 2 | 0.367969 | 0.217529 | int=250 temp=1.3 |
| 7 | 2 | 0.368008 | 0.217573 | int=300 temp=0.8 |
| 8 | 2 | 0.367991 | 0.217521 | int=300 temp=1.0 |
| 9 | 2 | 0.367984 | 0.217546 | int=300 temp=1.3 |
| 10 | 2 | 0.367999 | 0.217533 | int=400 temp=0.8 |
| 11 | 2 | 0.367992 | 0.217547 | int=400 temp=1.0 |
| 12 | 2 | 0.367986 | 0.217512 | int=400 temp=1.3 |
| 13 | 2 | 0.368004 | 0.217527 | int=500 temp=0.8 |
| 14 | 2 | 0.367988 | 0.217600 | int=500 temp=1.0 |
| 15 | 2 | 0.367992 | 0.217666 | int=500 temp=1.3 |

**meta_best_grid_winner_repeat5_20251222_102624**（来源：sweeps/meta_best_grid_winner_repeat5_20251222_102624/results.csv）

| idx | n | OMR | BMR | cfg |
| ---: | ---: | ---: | ---: | --- |
| 1 | 5 | 0.367962 | 0.217582 | SAC norm=1 int=200 temp=1.3 scale=1.0 |

**meta_best_scale_fine_r2_20251223_110142**（来源：sweeps/meta_best_scale_fine_r2_20251223_110142/results.csv）

通用配置：SAC norm=1 int=200 temp=1.3；表内 `cfg` 仅列差异
| idx | n | OMR | BMR | cfg |
| ---: | ---: | ---: | ---: | --- |
| 1 | 2 | 0.367959 | 0.217548 | scale=0.45 |
| 2 | 2 | 0.367959 | 0.217475 | scale=0.50 |
| 3 | 2 | 0.367960 | 0.217554 | scale=0.55 |
| 4 | 2 | 0.367959 | 0.217560 | scale=0.60 |
| 5 | 2 | 0.367958 | 0.217548 | scale=0.65 |
| 6 | 2 | 0.367961 | 0.217585 | scale=0.70 |

**meta_best_v5_idx6_repeat5_20251217_182945**（来源：sweeps/meta_best_v5_idx6_repeat5_20251217_182945/results.csv）

| idx | n | OMR | BMR | cfg |
| ---: | ---: | ---: | ---: | --- |
| 1 | 5 | 0.367968 | 0.217533 | SAC norm=1 int=250 temp=1.0 scale=1.0 |

**meta_lower_omr_3m_v2_1213_135303**（来源：sweeps/meta_lower_omr_3m_v2_1213_135303/results.csv）

通用配置：SAC norm=1；表内 `cfg` 仅列差异
| idx | n | OMR | BMR | cfg |
| ---: | ---: | ---: | ---: | --- |
| 1 | 2 | 0.368100 | 0.218050 | cpd=1 irt=1 int=500 |
| 2 | 2 | 0.397450 | 0.246500 | linear cpd=1 irt=1 int=500 scale=1.0 |
| 3 | 2 | 0.397650 | 0.253300 | cpd=1 irt=1 int=500 |
| 4 | 2 | 0.415300 | 0.238300 | irt=1 int=500 |
| 5 | 2 | 0.390650 | 0.235750 | linear irt=1 int=500 scale=1.0 |
| 6 | 2 | 0.368000 | 0.217500 | int=500 |
| 7 | 2 | 0.368100 | 0.217850 | cpd=1 irt=1 int=500 temp=0.7 |
| 8 | 2 | 0.368250 | 0.218000 | cpd=1 irt=1 int=500 scale=2.0 |
| 9 | 2 | 0.368100 | 0.218050 | cpd=1 irt=1 int=500 |
| 10 | 2 | 0.368200 | 0.218150 | cpd=1 irt=1 int=1000 |

**meta_refine6_3m_v3_1213_214805**（来源：sweeps/meta_refine6_3m_v3_1213_214805/results.csv）

通用配置：SAC norm=1；表内 `cfg` 仅列差异
| idx | n | OMR | BMR | cfg |
| ---: | ---: | ---: | ---: | --- |
| 1 | 2 | 0.368100 | 0.217850 | cpd=1 irt=1 int=500 |
| 2 | 2 | 0.368000 | 0.217450 | int=500 |
| 3 | 2 | 0.368000 | 0.217550 | int=500 temp=0.7 |
| 4 | 2 | 0.368050 | 0.217550 | int=500 scale=2.0 |
| 5 | 2 | 0.368100 | 0.217550 | int=1000 |
| 6 | 2 | 0.368000 | 0.217500 | int=500 |

**meta_refine_user_3m_1212_160647**（来源：sweeps/meta_refine_user_3m_1212_160647/results.csv）

通用配置：SAC cpd=1 irt=1 norm=1 scale=1.0；表内 `cfg` 仅列差异
| idx | n | OMR | BMR | cfg |
| ---: | ---: | ---: | ---: | --- |
| 1 | 1 | 0.368800 | 0.217300 | temp=1.0 |
| 2 | 1 | 0.368800 | 0.217100 | temp=1.0 |
| 3 | 1 | 0.369600 | 0.216700 | temp=0.7 |
| 4 | 1 | 0.368100 | 0.218200 | temp=0.7 |

**meta_reward_algo_v4_fix_1214_014409**（来源：sweeps/meta_reward_algo_v4_fix_1214_014409/results.csv）

通用配置：norm=1 int=500；表内 `cfg` 仅列差异
| idx | n | OMR | BMR | cfg |
| ---: | ---: | ---: | ---: | --- |
| 1 | 2 | 0.368000 | 0.217450 | SAC |
| 2 | 2 | 0.368000 | 0.217500 | SAC |
| 3 | 2 | 0.368000 | 0.217550 | SAC |
| 4 | 2 | 0.368000 | 0.217550 | SAC |
| 5 | 2 | 0.368000 | 0.217550 | SAC |
| 6 | 2 | 0.428800 | 0.261450 | SAC |
| 7 | 2 | 0.377200 | 0.222350 | TD3 |
| 8 | 2 | 0.375600 | 0.222400 | TD3 |

**meta_reward_algo_v4_20251215_145147**（来源：sweeps/meta_reward_algo_v4_20251215_145147/results.csv）

通用配置：norm=1；表内 `cfg` 仅列差异
| idx | n | OMR | BMR | cfg |
| ---: | ---: | ---: | ---: | --- |
| 1 | 1 | 0.367987 | 0.217459 | SAC int=500 temp=1.0 scale=1.0 |
| 2 | 1 | 0.368311 | 0.217307 | SAC int=500 temp=0.5 scale=2.0 |
| 3 | 1 | 0.369052 | 0.216666 | SAC int=500 temp=0.3 scale=3.0 |
| 4 | 1 | 0.368909 | 0.216732 | SAC int=500 temp=0.2 scale=4.0 |
| 5 | 1 | 0.369124 | 0.216132 | SAC int=200 temp=0.3 scale=3.0 |
| 6 | 1 | 0.368865 | 0.216664 | SAC int=1000 temp=0.3 scale=3.0 |
| 7 | 1 | 0.369088 | 0.216669 | SAC int=500 temp=0.3 scale=3.0 |
| 8 | 1 | 0.369163 | 0.216929 | SAC int=500 temp=0.3 scale=3.0 |
| 9 | 1 | 0.368829 | 0.217293 | SAC int=500 temp=0.3 scale=3.0 |
| 10 | 1 | 0.368704 | 0.216913 | SAC int=500 temp=0.3 scale=3.0 |
| 11 | 1 | 0.434121 | 0.284004 | SAC int=500 temp=0.3 scale=3.0 |
| 12 | 1 | 0.385692 | 0.219645 | TD3 int=500 temp=0.3 scale=3.0 |
| 13 | 1 | 0.401801 | 0.221379 | TD3 int=500 temp=0.3 scale=3.0 |
| 14 | 1 | 0.388621 | 0.223232 | DDPG int=500 temp=0.3 scale=3.0 |
| 15 | 1 | 0.406464 | 0.228920 | DDPG int=500 temp=0.3 scale=3.0 |
| 16 | 0 | NA | NA | TQC int=500 temp=0.3 scale=3.0 |
| 17 | 1 | 0.368221 | 0.217770 | A2C int=500 temp=0.3 scale=3.0 |
| 18 | 1 | 0.368844 | 0.216810 | SAC int=500 temp=0.3 scale=3.0 pen=reciprocal |
| 19 | 1 | 0.368999 | 0.216937 | SAC int=500 temp=0.3 scale=3.0 pen=log |

**meta_reward_algo_v4_tqc_only_fix_20251215_211951**（来源：sweeps/meta_reward_algo_v4_tqc_only_fix_20251215_211951/results.csv）

| idx | n | OMR | BMR | cfg |
| ---: | ---: | ---: | ---: | --- |
| 1 | 1 | 0.369536 | 0.216303 | TQC norm=1 int=500 temp=0.3 scale=3.0 |

**meta_precision_refine_v5_1214_212442**（来源：sweeps/meta_precision_refine_v5_1214_212442/results.csv）

通用配置：SAC norm=1；表内 `cfg` 仅列差异
| idx | n | OMR | BMR | cfg |
| ---: | ---: | ---: | ---: | --- |
| 1 | 2 | 0.367992 | 0.217461 | int=500 temp=1.0 scale=1.0 |
| 2 | 2 | 0.368020 | 0.217626 | int=500 temp=0.7 scale=1.0 |
| 3 | 2 | 0.367982 | 0.217504 | int=500 temp=1.3 scale=1.0 |
| 4 | 2 | 0.367982 | 0.217492 | int=500 temp=1.0 scale=0.7 |
| 5 | 2 | 0.368000 | 0.217512 | int=500 temp=1.0 scale=1.3 |
| 6 | 2 | 0.367980 | 0.217538 | int=250 temp=1.0 scale=1.0 |
| 7 | 2 | 0.368078 | 0.217460 | int=1000 temp=1.0 scale=1.0 |
| 8 | 2 | 0.367984 | 0.217495 | int=500 temp=1.0 scale=1.0 |
| 9 | 2 | 0.367988 | 0.217602 | int=500 temp=1.0 scale=1.0 |
| 10 | 2 | 0.367995 | 0.217610 | int=500 temp=1.0 scale=1.0 |

**meta_temp_interval_scale_aggr_r2_20251224_205809**（来源：sweeps/meta_temp_interval_scale_aggr_r2_20251224_205809/results.csv）

通用配置：SAC norm=1；表内 `cfg` 仅列差异
| idx | n | OMR | BMR | cfg |
| ---: | ---: | ---: | ---: | --- |
| 1 | 2 | 0.367959 | 0.217592 | int=150 temp=1.5 scale=0.5 |
| 2 | 2 | 0.367958 | 0.217502 | int=180 temp=1.5 scale=0.5 |
| 3 | 2 | 0.367959 | 0.217529 | int=220 temp=1.5 scale=0.5 |
| 4 | 2 | 0.367958 | 0.217494 | int=150 temp=1.5 scale=0.65 |
| 5 | 2 | 0.367958 | 0.217548 | int=180 temp=1.5 scale=0.65 |
| 6 | 2 | 0.367959 | 0.217529 | int=220 temp=1.5 scale=0.65 |
| 7 | 2 | 0.367959 | 0.217602 | int=150 temp=1.6 scale=0.5 |
| 8 | 2 | 0.367959 | 0.217583 | int=180 temp=1.6 scale=0.5 |
| 9 | 2 | 0.367959 | 0.217556 | int=220 temp=1.6 scale=0.5 |
| 10 | 2 | 0.367959 | 0.217494 | int=150 temp=1.6 scale=0.65 |
| 11 | 2 | 0.367959 | 0.217581 | int=180 temp=1.6 scale=0.65 |
| 12 | 2 | 0.367958 | 0.217485 | int=220 temp=1.6 scale=0.65 |
| 13 | 2 | 0.367959 | 0.217503 | int=150 temp=1.8 scale=0.5 |
| 14 | 2 | 0.367959 | 0.217494 | int=180 temp=1.8 scale=0.5 |
| 15 | 2 | 0.367958 | 0.217494 | int=220 temp=1.8 scale=0.5 |
| 16 | 2 | 0.367959 | 0.217551 | int=150 temp=1.8 scale=0.65 |
| 17 | 2 | 0.367959 | 0.217548 | int=180 temp=1.8 scale=0.65 |
| 18 | 2 | 0.367959 | 0.217494 | int=220 temp=1.8 scale=0.65 |

**meta_temp_scale_grid_r2_20251224_142147**（来源：sweeps/meta_temp_scale_grid_r2_20251224_142147/results.csv）

通用配置：SAC norm=1 int=200；表内 `cfg` 仅列差异
| idx | n | OMR | BMR | cfg |
| ---: | ---: | ---: | ---: | --- |
| 1 | 2 | 0.367959 | 0.217575 | temp=1.2 scale=0.45 |
| 2 | 2 | 0.367959 | 0.217448 | temp=1.2 scale=0.50 |
| 3 | 2 | 0.367960 | 0.217554 | temp=1.2 scale=0.55 |
| 4 | 2 | 0.367959 | 0.217502 | temp=1.3 scale=0.45 |
| 5 | 2 | 0.367959 | 0.217548 | temp=1.3 scale=0.50 |
| 6 | 2 | 0.367959 | 0.217529 | temp=1.3 scale=0.55 |
| 7 | 2 | 0.367958 | 0.217502 | temp=1.4 scale=0.45 |
| 8 | 2 | 0.367959 | 0.217556 | temp=1.4 scale=0.50 |
| 9 | 2 | 0.367959 | 0.217583 | temp=1.4 scale=0.55 |

**meta_try_cachefeat_3m_fix_1214_000103**（来源：sweeps/meta_try_cachefeat_3m_fix_1214_000103/results.csv）

通用配置：SAC norm=1 int=500；表内 `cfg` 仅列差异
| idx | n | OMR | BMR | cfg |
| ---: | ---: | ---: | ---: | --- |
| 1 | 2 | 0.368000 | 0.217550 | — |
| 2 | 2 | 0.368000 | 0.217500 | cacheF=1 |

**meta_try_cachefeat_3m_1213_234146**（来源：sweeps/meta_try_cachefeat_3m_1213_234146/results.csv）

通用配置：SAC norm=1 int=500；表内 `cfg` 仅列差异
| idx | n | OMR | BMR | cfg |
| ---: | ---: | ---: | ---: | --- |
| 1 | 0 | NA | NA | — |
| 2 | 2 | 0.368000 | 0.217500 | cacheF=1 |

**meta_try_candfeat_3m_1214_005451**（来源：sweeps/meta_try_candfeat_3m_1214_005451/results.csv）

通用配置：SAC norm=1 int=500；表内 `cfg` 仅列差异
| idx | n | OMR | BMR | cfg |
| ---: | ---: | ---: | ---: | --- |
| 1 | 2 | 0.368000 | 0.217550 | — |
| 2 | 2 | 0.368000 | 0.217550 | candF=1 |

**next_meta_modes_3m_20260129_183751**（来源：sweeps/next_meta_modes_3m_20260129_183751/results.csv）

通用配置：SAC log1p=1 norm=1 signs=1 softmax int=200 temp=1.3 scale=0.5；表内 `cfg` 仅列差异
| idx | n | OMR | BMR | cfg |
| ---: | ---: | ---: | ---: | --- |
| 1 | 2 | NA | NA | cpd=0 irt=0 |
| 2 | 2 | NA | NA | cpd=0 irt=1 |
| 3 | 2 | NA | NA | cpd=1 irt=0 |
| 4 | 2 | NA | NA | cpd=1 irt=1 |

**next_meta_modes_3m_20260129_183812**（来源：sweeps/next_meta_modes_3m_20260129_183812/results.csv）

通用配置：SAC log1p=1 norm=1 signs=1 softmax int=200 temp=1.3 scale=0.5；表内 `cfg` 仅列差异
| idx | n | OMR | BMR | cfg |
| ---: | ---: | ---: | ---: | --- |
| 1 | 2 | NA | NA | cpd=0 irt=0 |
| 2 | 2 | NA | NA | cpd=0 irt=1 |
| 3 | 2 | NA | NA | cpd=1 irt=0 |
| 4 | 2 | NA | NA | cpd=1 irt=1 |

**next_meta_modes_nosem_3m_20260129_184111**（来源：sweeps/next_meta_modes_nosem_3m_20260129_184111/results.csv）

通用配置：SAC log1p=1 norm=1 signs=1 softmax int=200 temp=1.3 scale=0.5；表内 `cfg` 仅列差异
| idx | n | OMR | BMR | cfg |
| ---: | ---: | ---: | ---: | --- |
| 1 | 2 | NA | NA | cpd=0 irt=0 |
| 2 | 2 | NA | NA | cpd=0 irt=1 |
| 3 | 2 | NA | NA | cpd=1 irt=0 |
| 4 | 2 | NA | NA | cpd=1 irt=1 |

**next_meta_modes_req1_3m_20260129_184621**（来源：sweeps/next_meta_modes_req1_3m_20260129_184621/results.csv）

通用配置：SAC log1p=1 norm=1 signs=1 softmax int=200 temp=1.3 scale=0.5；表内 `cfg` 仅列差异（cpd/irt）

| idx | n | OMR | BMR | cfg |
| ---: | ---: | ---: | ---: | --- |
| 1 | 2 | 0.367959 | 0.217529 | cpd=0 irt=0 |
| 2 | 2 | 0.416009 | 0.239102 | irt=1 |
| 3 | 2 | 0.368029 | 0.218109 | cpd=1 |
| 4 | 2 | 0.368026 | 0.218163 | cpd=1 irt=1 |


| idx | n | OMR | BMR | cfg |
| ---: | ---: | ---: | ---: | --- |
| 1 | 1 | 0.614900 | 0.614900 | TD3 temp=1.0 scale=1.0 |

**modes2_mrw0**（来源：sweeps/modes2_mrw0_0130_112123/combined_summary.csv）

通用配置：SAC score=linear log1p=1 norm=1 signs=1 softmax irt=0 int=200 temp=1.3 scale=0.5 mrw=0.0；表内 `cfg` 仅列差异
| idx | n | OMR | BMR | cfg |
| ---: | ---: | ---: | ---: | --- |
| 1 | 1 | 0.368023 | 0.218105 | cpd=1 |
| 2 | 1 | 0.367959 | 0.217457 | cpd=0 |

**modes3_batch**（来源：sweeps/modes3_batch_0130_021623/combined_summary.csv）

通用配置：SAC score=linear log1p=1 norm=1 signs=1 softmax int=200 temp=1.3 scale=0.5；表内 `cfg` 仅列差异
| idx | n | OMR | BMR | cfg |
| ---: | ---: | ---: | ---: | --- |
| 1 | 1 | 0.368023 | 0.218105 | cpd=1 irt=1 |
| 2 | 1 | 0.414926 | 0.238559 | cpd=0 irt=1 |
| 3 | 1 | 0.367960 | 0.217561 | cpd=0 irt=0 |

### CACHESIM_NUM_REQ=ALL
| 类型 | cache_ratio | num_req来源 | 配置来源 | miss_ratio | byte_miss_ratio | 外层env(仅列显式出现) |
| --- | ---: | --- | --- | ---: | ---: | --- |
| sweep | 0.1 | stdout(ALL) | scripts/sweep_configs_meta_algo_expand_v6.txt（结果见 [sweeps/meta_algo_expand_v6_1215_011924/results.csv](sweeps/meta_algo_expand_v6_1215_011924/results.csv)） | 0.269682 | 0.164866 | SEED_BASE=1000 SWEEP_REPEATS=2 |

配置来源：scripts/sweep_configs_*.txt（此处不再展开逐行配置；训练超参纳入；IPC/同步参数不纳入本汇总）

## Trace: data/WikiCDN/wiki_2019t.oracleGeneral.zst

### Sweeps（CACHESIM_NUM_REQ=3000000）

| date | id | best | OMR | BMR | cfg | ref | note |
| ---: | --- | ---: | ---: | ---: | --- | --- | --- |
| 20260129 | next_ns | 1 | NA | NA | SAC cpd=0 irt=0 int=200 scale=0.5 temp=1.3 | [res](sweeps/next_wiki_bootstrap_nosem_3m_20260129_184204/results.csv) | NA |
| 20260129 | next | 3 | 0.595814 | 0.475283 | SAC cpd=1 irt=1 temp=1.3 scale=0.5 int=200 | [res](sweeps/next_wiki_bootstrap_req1_3m_20260129_184646/results.csv) | req1 |
| 20260130 | m2 | 1 | 0.595771 | 0.475249 | SAC cpd=1 irt=0 int=200 scale=0.5 temp=1.3 mrw=0.0 | [cs](sweeps/modes2_mrw0_0130_112123/combined_summary.csv) |  |
| 20260130 | m3 | 1 | 0.595705 | 0.475151 | SAC cpd=1 irt=1 int=200 scale=0.5 temp=1.3 | [cs](sweeps/modes3_batch_0130_021623/combined_summary.csv) |  |
| unknown | cw | - | NA | NA | const_weight | - | const |


<!-- ROOT_LOGS_BEGIN -->

### 根目录日志（191 条，req>=3000000）

#### req=207646002（8 条）

| date | run | OMR | BMR | cfg | ref | note |
| ---: | --- | ---: | ---: | --- | --- | --- |
| 20251208 | 1208_113816 | 0.1889 | 0.1337 | PPO log1p=1 norm=1 cpd=1 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_113816.log) [ac](ac_sb3_1208_113816.log) |  |
| 20251121 | 1121_145633 | 0.2344 | 0.1731 | int=200 | [cs](cachesim_sb3_1121_145633.log) [ac](ac_sb3_1121_145633.log) |  |
| 20251118 | 1118_213115 | 0.2061 | 0.1525 | int=200 | [cs](cachesim_sb3_1118_213115.log) [ac](ac_sb3_1118_213115.log) |  |
| 20251118 | 1118_210840 | 0.1896 | 0.1373 | int=200 | [cs](cachesim_sb3_1118_210840.log) [ac](ac_sb3_1118_210840.log) |  |
| 20251118 | 1118_113120 | 0.1864 | 0.1362 | int=200 | [cs](cachesim_sb3_1118_113120.log) [ac](ac_sb3_1118_113120.log) |  |
| 20251106 | 1106_023228 | 0.1928 | 0.1422 | int=200 | [cs](cachesim_sb3_1106_023228.log) [ac](ac_sb3_1106_023228.log) |  |
| 20251105 | 1105_183807 | 0.2211 | 0.1726 | int=200 | [cs](cachesim_sb3_1105_183807.log) [ac](ac_sb3_1105_183807.log) |  |
| 20251031 | 1031_024219 | 0.1929 | 0.1421 | int=200 | [cs](cachesim_sb3_1031_024219.log) [ac](ac_sb3_1031_024219.log) |  |

##### 逐日志明细（req=207646002）

**1208_113816**（20251208）

- 结果：OMR=0.1889，BMR=0.1337
- logs：[cachesim_sb3_1208_113816.log](cachesim_sb3_1208_113816.log) / [ac_sb3_1208_113816.log](ac_sb3_1208_113816.log)
- cachesim：req=207646002；int=200；mr_w=1.000 bmr_w=0.000；log1p=1；recip=0；norm=1；irt=0；cpd=1；cacheF=0；candF=0；state=0->14
 - [LOH INIT] AvgTopK enabled: TOP4 × 6特征 = 24维
 - [LOH INIT] Wait mode: default (BLOCKED)
 - [LOH INIT] Size data structure: SIZE_BUCKETS (全量分桶)
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - | policy_gradient_loss | -0.00981 |
 - | policy_gradient_loss | -0.0138 |
 - | policy_gradient_loss | -0.0055 |
 - | policy_gradient_loss | -0.00263 |

**1121_145633**（20251121）

- 结果：OMR=0.2344，BMR=0.1731
- logs：[cachesim_sb3_1121_145633.log](cachesim_sb3_1121_145633.log) / [ac_sb3_1121_145633.log](ac_sb3_1121_145633.log)
- cachesim：req=207646002；int=200；mr_w=1.000 bmr_w=0.000
- RL：batch=32；lr=0.0001；ent=0.02；state=38；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)

**1118_213115**（20251118）

- 结果：OMR=0.2061，BMR=0.1525
- logs：[cachesim_sb3_1118_213115.log](cachesim_sb3_1118_213115.log) / [ac_sb3_1118_213115.log](ac_sb3_1118_213115.log)
- cachesim：req=207646002；int=200；mr_w=1.000 bmr_w=0.000

**1118_210840**（20251118）

- 结果：OMR=0.1896，BMR=0.1373
- logs：[cachesim_sb3_1118_210840.log](cachesim_sb3_1118_210840.log) / [ac_sb3_1118_210840.log](ac_sb3_1118_210840.log)
- cachesim：req=207646002；int=200；mr_w=1.000 bmr_w=0.000

**1118_113120**（20251118）

- 结果：OMR=0.1864，BMR=0.1362
- logs：[cachesim_sb3_1118_113120.log](cachesim_sb3_1118_113120.log) / [ac_sb3_1118_113120.log](ac_sb3_1118_113120.log)
- cachesim：req=207646002；int=200；mr_w=1.000 bmr_w=0.000

**1106_023228**（20251106）

- 结果：OMR=0.1928，BMR=0.1422
- logs：[cachesim_sb3_1106_023228.log](cachesim_sb3_1106_023228.log) / [ac_sb3_1106_023228.log](ac_sb3_1106_023228.log)
- cachesim：req=207646002；int=200；mr_w=1.000 bmr_w=0.000

**1105_183807**（20251105）

- 结果：OMR=0.2211，BMR=0.1726
- logs：[cachesim_sb3_1105_183807.log](cachesim_sb3_1105_183807.log) / [ac_sb3_1105_183807.log](ac_sb3_1105_183807.log)
- cachesim：req=207646002；int=200；mr_w=1.000 bmr_w=0.000

**1031_024219**（20251031）

- 结果：OMR=0.1929，BMR=0.1421
- logs：[cachesim_sb3_1031_024219.log](cachesim_sb3_1031_024219.log) / [ac_sb3_1031_024219.log](ac_sb3_1031_024219.log)
- cachesim：req=207646002；int=200；mr_w=1.000 bmr_w=0.000
- RL：state=26；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)

#### req=10000000（51 条）

| date | run | OMR | BMR | cfg | ref | note |
| ---: | --- | ---: | ---: | --- | --- | --- |
| 20251114 | 1114_183759 | 0.5189 | 0.4193 | TD3 int=200 | [cs](cachesim_sb3_1114_183759.log) [ac](ac_sb3_1114_183759.log) |  |
| 20251114 | 1114_181503 | 0.5101 | 0.3883 | TD3 int=200 | [cs](cachesim_sb3_1114_181503.log) [ac](ac_sb3_1114_181503.log) |  |
| 20251110 | 1110_210902 | 0.4807 | 0.3660 | SAC int=200 | [cs](cachesim_sb3_1110_210902.log) [ac](ac_sb3_1110_210902.log) |  |
| 20251110 | 1110_201409 | 0.4808 | 0.3660 | SAC int=200 | [cs](cachesim_sb3_1110_201409.log) [ac](ac_sb3_1110_201409.log) |  |
| 20251110 | 1110_191734 | 0.4801 | 0.3654 | SAC int=200 | [cs](cachesim_sb3_1110_191734.log) [ac](ac_sb3_1110_191734.log) |  |
| 20251110 | 1110_174118 | 0.4804 | 0.3657 | SAC int=200 | [cs](cachesim_sb3_1110_174118.log) [ac](ac_sb3_1110_174118.log) |  |
| 20251110 | 1110_162506 | 0.4801 | 0.3653 | SAC int=200 | [cs](cachesim_sb3_1110_162506.log) [ac](ac_sb3_1110_162506.log) |  |
| 20251110 | 1110_162426 | 0.4804 | 0.3655 | SAC int=200 | [cs](cachesim_sb3_1110_162426.log) [ac](ac_sb3_1110_162426.log) |  |
| 20251108 | 1108_194813 | 0.4789 | 0.3697 | TD3 int=200 | [cs](cachesim_sb3_1108_194813.log) [ac](ac_sb3_1108_194813.log) |  |
| 20251108 | 1108_180329 | 0.4977 | 0.3937 | TD3 int=200 | [cs](cachesim_sb3_1108_180329.log) [ac](ac_sb3_1108_180329.log) |  |
| 20251108 | 1108_180314 | 0.4948 | 0.3844 | TD3 int=200 | [cs](cachesim_sb3_1108_180314.log) [ac](ac_sb3_1108_180314.log) |  |
| 20251108 | 1108_173309 | 0.4862 | 0.3728 | TD3 int=200 | [cs](cachesim_sb3_1108_173309.log) [ac](ac_sb3_1108_173309.log) |  |
| 20251108 | 1108_023745 | 0.4800 | 0.3651 | SAC int=200 | [cs](cachesim_sb3_1108_023745.log) [ac](ac_sb3_1108_023745.log) |  |
| 20251108 | 1108_023556 | 0.4877 | 0.3685 | TD3 int=200 | [cs](cachesim_sb3_1108_023556.log) [ac](ac_sb3_1108_023556.log) |  |
| 20251108 | 1108_020729 | 0.4835 | 0.3710 | TD3 int=200 | [cs](cachesim_sb3_1108_020729.log) [ac](ac_sb3_1108_020729.log) |  |
| 20251108 | 1108_014010 | 0.5119 | 0.4023 | TD3 int=200 | [cs](cachesim_sb3_1108_014010.log) [ac](ac_sb3_1108_014010.log) |  |
| 20251108 | 1108_002806 | 0.4856 | 0.3672 | TD3 int=200 | [cs](cachesim_sb3_1108_002806.log) [ac](ac_sb3_1108_002806.log) |  |
| 20251107 | 1107_193909 | 0.4813 | 0.3683 | int=200 | [cs](cachesim_sb3_1107_193909.log) [ac](ac_sb3_1107_193909.log) |  |
| 20251107 | 1107_190129 | 0.4805 | 0.3655 | SAC int=200 | [cs](cachesim_sb3_1107_190129.log) [ac](ac_sb3_1107_190129.log) |  |
| 20251107 | 1107_174730 | 0.4830 | 0.3602 | TD3 int=200 | [cs](cachesim_sb3_1107_174730.log) [ac](ac_sb3_1107_174730.log) |  |
| 20251107 | 1107_132955 | 0.4822 | 0.3671 | TD3 int=200 | [cs](cachesim_sb3_1107_132955.log) [ac](ac_sb3_1107_132955.log) |  |
| 20251107 | 1107_123724 | 0.4866 | 0.3764 | TD3 int=200 | [cs](cachesim_sb3_1107_123724.log) [ac](ac_sb3_1107_123724.log) |  |
| 20251107 | 1107_111443 | 0.4806 | 0.3658 | SAC int=200 | [cs](cachesim_sb3_1107_111443.log) [ac](ac_sb3_1107_111443.log) |  |
| 20251107 | 1107_101048 | 0.4862 | 0.3823 | TD3 int=200 | [cs](cachesim_sb3_1107_101048.log) [ac](ac_sb3_1107_101048.log) |  |
| 20251107 | 1107_033258 | 0.4859 | 0.3770 | TD3 int=200 | [cs](cachesim_sb3_1107_033258.log) [ac](ac_sb3_1107_033258.log) |  |
| 20251107 | 1107_005228 | 0.4828 | 0.3717 | TD3 int=200 | [cs](cachesim_sb3_1107_005228.log) [ac](ac_sb3_1107_005228.log) |  |
| 20251107 | 1107_005128 | 0.5020 | 0.3866 | TD3 int=200 | [cs](cachesim_sb3_1107_005128.log) [ac](ac_sb3_1107_005128.log) |  |
| 20251106 | 1106_235905 | 0.4944 | 0.3846 | TD3 int=200 | [cs](cachesim_sb3_1106_235905.log) [ac](ac_sb3_1106_235905.log) |  |
| 20251106 | 1106_231034 | 0.4808 | 0.3589 | TD3 int=200 | [cs](cachesim_sb3_1106_231034.log) [ac](ac_sb3_1106_231034.log) |  |
| 20251106 | 1106_222626 | 0.5075 | 0.3868 | TD3 int=200 | [cs](cachesim_sb3_1106_222626.log) [ac](ac_sb3_1106_222626.log) |  |
| 20251106 | 1106_213930 | 0.4965 | 0.3867 | TD3 int=200 | [cs](cachesim_sb3_1106_213930.log) [ac](ac_sb3_1106_213930.log) |  |
| 20251106 | 1106_210904 | 0.4957 | 0.3795 | TD3 int=200 | [cs](cachesim_sb3_1106_210904.log) [ac](ac_sb3_1106_210904.log) |  |
| 20251106 | 1106_195917 | 0.4979 | 0.3901 | TD3 int=200 | [cs](cachesim_sb3_1106_195917.log) [ac](ac_sb3_1106_195917.log) |  |
| 20251106 | 1106_195218 | 0.4998 | 0.3824 | TD3 int=200 | [cs](cachesim_sb3_1106_195218.log) [ac](ac_sb3_1106_195218.log) |  |
| 20251106 | 1106_111646 | 0.4780 | 0.3619 | TD3 int=200 | [cs](cachesim_sb3_1106_111646.log) [ac](ac_sb3_1106_111646.log) |  |
| 20251106 | 1106_101920 | 0.4779 | 0.3656 | TD3 int=200 | [cs](cachesim_sb3_1106_101920.log) [ac](ac_sb3_1106_101920.log) |  |
| 20251106 | 1106_095956 | 0.5161 | 0.4107 | int=200 | [cs](cachesim_sb3_1106_095956.log) [ac](ac_sb3_1106_095956.log) |  |
| 20251106 | 1106_094634 | 0.4863 | 0.3658 | int=200 | [cs](cachesim_sb3_1106_094634.log) [ac](ac_sb3_1106_094634.log) |  |
| 20251106 | 1106_093058 | 0.4804 | 0.3657 | int=200 | [cs](cachesim_sb3_1106_093058.log) [ac](ac_sb3_1106_093058.log) |  |
| 20251104 | 1104_193330 | 0.4804 | 0.3656 | SAC int=200 | [cs](cachesim_sb3_1104_193330.log) [ac](ac_sb3_1104_193330.log) |  |
| 20251104 | 1104_180855 | 0.4803 | 0.3655 | SAC int=200 | [cs](cachesim_sb3_1104_180855.log) [ac](ac_sb3_1104_180855.log) |  |
| 20251031 | 1031_161840 | 0.4816 | 0.3696 | int=200 | [cs](cachesim_sb3_1031_161840.log) [ac](ac_sb3_1031_161840.log) |  |
| 20251031 | 1031_151728 | 0.4790 | 0.3624 | int=200 | [cs](cachesim_sb3_1031_151728.log) [ac](ac_sb3_1031_151728.log) |  |
| 20251031 | 1031_023342 | 0.4893 | 0.3729 | — | [cs](cachesim_sb3_1031_023342.log) [ac](ac_sb3_1031_023342.log) |  |
| 20251031 | 1031_022915 | 0.4857 | 0.3677 | — | [cs](cachesim_sb3_1031_022915.log) [ac](ac_sb3_1031_022915.log) |  |
| 20251031 | 1031_015607 | 0.4804 | 0.3665 | int=200 | [cs](cachesim_sb3_1031_015607.log) [ac](ac_sb3_1031_015607.log) |  |
| 20251031 | 1031_014543 | 0.4794 | 0.3652 | int=200 | [cs](cachesim_sb3_1031_014543.log) [ac](ac_sb3_1031_014543.log) |  |
| 20251030 | 1030_231012 | 0.4803 | 0.3654 | SAC int=200 | [cs](cachesim_sb3_1030_231012.log) [ac](ac_sb3_1030_231012.log) |  |
| 20251030 | 1030_213330 | 0.4803 | 0.3656 | SAC int=200 | [cs](cachesim_sb3_1030_213330.log) [ac](ac_sb3_1030_213330.log) |  |
| 20251030 | 1030_183716 | 0.4804 | 0.3656 | SAC int=200 | [cs](cachesim_sb3_1030_183716.log) [ac](ac_sb3_1030_183716.log) |  |
| 20251030 | 1030_014039 | 0.4860 | 0.3751 | SAC int=200 | [cs](cachesim_sb3_1030_014039.log) [ac](ac_sb3_1030_014039.log) |  |

##### 逐日志明细（req=10000000）

**1114_183759**（20251114）

- 结果：OMR=0.5189，BMR=0.4193
- logs：[cachesim_sb3_1114_183759.log](cachesim_sb3_1114_183759.log) / [ac_sb3_1114_183759.log](ac_sb3_1114_183759.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=TD3；batch=256；lr=0.0003；gamma=0.99；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: TD3 (off-policy)
 - - policy_delay: 2 # previous/SB3 default 2
 - - target_policy_noise: 0.2 # SB3 default 0.2 (env-overridable)

**1114_181503**（20251114）

- 结果：OMR=0.5101，BMR=0.3883
- logs：[cachesim_sb3_1114_181503.log](cachesim_sb3_1114_181503.log) / [ac_sb3_1114_181503.log](ac_sb3_1114_181503.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=TD3；batch=256；lr=0.0003；gamma=0.99；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: TD3 (off-policy)
 - - policy_delay: 2 # previous/SB3 default 2
 - - target_policy_noise: 0.2 # SB3 default 0.2 (env-overridable)

**1110_210902**（20251110）

- 结果：OMR=0.4807，BMR=0.3660
- logs：[cachesim_sb3_1110_210902.log](cachesim_sb3_1110_210902.log) / [ac_sb3_1110_210902.log](ac_sb3_1110_210902.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**1110_201409**（20251110）

- 结果：OMR=0.4808，BMR=0.3660
- logs：[cachesim_sb3_1110_201409.log](cachesim_sb3_1110_201409.log) / [ac_sb3_1110_201409.log](ac_sb3_1110_201409.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**1110_191734**（20251110）

- 结果：OMR=0.4801，BMR=0.3654
- logs：[cachesim_sb3_1110_191734.log](cachesim_sb3_1110_191734.log) / [ac_sb3_1110_191734.log](ac_sb3_1110_191734.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**1110_174118**（20251110）

- 结果：OMR=0.4804，BMR=0.3657
- logs：[cachesim_sb3_1110_174118.log](cachesim_sb3_1110_174118.log) / [ac_sb3_1110_174118.log](ac_sb3_1110_174118.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**1110_162506**（20251110）

- 结果：OMR=0.4801，BMR=0.3653
- logs：[cachesim_sb3_1110_162506.log](cachesim_sb3_1110_162506.log) / [ac_sb3_1110_162506.log](ac_sb3_1110_162506.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**1110_162426**（20251110）

- 结果：OMR=0.4804，BMR=0.3655
- logs：[cachesim_sb3_1110_162426.log](cachesim_sb3_1110_162426.log) / [ac_sb3_1110_162426.log](ac_sb3_1110_162426.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**1108_194813**（20251108）

- 结果：OMR=0.4789，BMR=0.3697
- logs：[cachesim_sb3_1108_194813.log](cachesim_sb3_1108_194813.log) / [ac_sb3_1108_194813.log](ac_sb3_1108_194813.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=TD3；batch=256；lr=0.0003；gamma=0.99；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: TD3 (off-policy)
 - - policy_delay: 2 # previous/SB3 default 2
 - - target_policy_noise: 0.2 # SB3 default 0.2 (env-overridable)

**1108_180329**（20251108）

- 结果：OMR=0.4977，BMR=0.3937
- logs：[cachesim_sb3_1108_180329.log](cachesim_sb3_1108_180329.log) / [ac_sb3_1108_180329.log](ac_sb3_1108_180329.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=TD3；batch=256；lr=0.0003；gamma=0.99；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: TD3 (off-policy)
 - - policy_delay: 2 # previous/SB3 default 2
 - - target_policy_noise: 0.2 # SB3 default 0.2 (env-overridable)

**1108_180314**（20251108）

- 结果：OMR=0.4948，BMR=0.3844
- logs：[cachesim_sb3_1108_180314.log](cachesim_sb3_1108_180314.log) / [ac_sb3_1108_180314.log](ac_sb3_1108_180314.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=TD3；batch=256；lr=0.0003；gamma=0.99；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: TD3 (off-policy)
 - - policy_delay: 2 # previous/SB3 default 2
 - - target_policy_noise: 0.2 # SB3 default 0.2 (env-overridable)

**1108_173309**（20251108）

- 结果：OMR=0.4862，BMR=0.3728
- logs：[cachesim_sb3_1108_173309.log](cachesim_sb3_1108_173309.log) / [ac_sb3_1108_173309.log](ac_sb3_1108_173309.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=TD3；batch=256；lr=0.0003；gamma=0.99；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: TD3 (off-policy)
 - - policy_delay: 2 # previous/SB3 default 2
 - - target_policy_noise: 0.2 # SB3 default 0.2 (env-overridable)

**1108_023745**（20251108）

- 结果：OMR=0.4800，BMR=0.3651
- logs：[cachesim_sb3_1108_023745.log](cachesim_sb3_1108_023745.log) / [ac_sb3_1108_023745.log](ac_sb3_1108_023745.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**1108_023556**（20251108）

- 结果：OMR=0.4877，BMR=0.3685
- logs：[cachesim_sb3_1108_023556.log](cachesim_sb3_1108_023556.log) / [ac_sb3_1108_023556.log](ac_sb3_1108_023556.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=TD3；batch=256；lr=0.001；gamma=0.99；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: TD3 (off-policy)
 - - policy_delay: 2 # previous/SB3 default 2
 - - target_policy_noise: 0.2 # SB3 default 0.2 (env-overridable)

**1108_020729**（20251108）

- 结果：OMR=0.4835，BMR=0.3710
- logs：[cachesim_sb3_1108_020729.log](cachesim_sb3_1108_020729.log) / [ac_sb3_1108_020729.log](ac_sb3_1108_020729.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=TD3；batch=256；lr=0.0003；gamma=0.99；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: TD3 (off-policy)
 - - policy_delay: 2 # previous/SB3 default 2
 - - target_policy_noise: 0.2 # SB3 default 0.2 (env-overridable)

**1108_014010**（20251108）

- 结果：OMR=0.5119，BMR=0.4023
- logs：[cachesim_sb3_1108_014010.log](cachesim_sb3_1108_014010.log) / [ac_sb3_1108_014010.log](ac_sb3_1108_014010.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=TD3；batch=256；lr=0.0003；gamma=0.99；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: TD3 (off-policy)
 - - policy_delay: 2 # previous/SB3 default 2
 - - target_policy_noise: 0.2 # SB3 default 0.2 (env-overridable)

**1108_002806**（20251108）

- 结果：OMR=0.4856，BMR=0.3672
- logs：[cachesim_sb3_1108_002806.log](cachesim_sb3_1108_002806.log) / [ac_sb3_1108_002806.log](ac_sb3_1108_002806.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=TD3；batch=256；lr=0.0003；gamma=0.99；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: TD3 (off-policy)
 - - policy_delay: 2 # previous/SB3 default 2
 - - target_policy_noise: 0.2 # SB3 default 0.2 (env-overridable)

**1107_193909**（20251107）

- 结果：OMR=0.4813，BMR=0.3683
- logs：[cachesim_sb3_1107_193909.log](cachesim_sb3_1107_193909.log) / [ac_sb3_1107_193909.log](ac_sb3_1107_193909.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：batch=32；lr=0.0001；ent=0.02；state=26；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)

**1107_190129**（20251107）

- 结果：OMR=0.4805，BMR=0.3655
- logs：[cachesim_sb3_1107_190129.log](cachesim_sb3_1107_190129.log) / [ac_sb3_1107_190129.log](ac_sb3_1107_190129.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**1107_174730**（20251107）

- 结果：OMR=0.4830，BMR=0.3602
- logs：[cachesim_sb3_1107_174730.log](cachesim_sb3_1107_174730.log) / [ac_sb3_1107_174730.log](ac_sb3_1107_174730.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=TD3；batch=256；lr=0.0003；gamma=0.99；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: TD3 (off-policy)
 - - policy_delay: 2 # previous/SB3 default 2
 - - target_policy_noise: 0.2 # SB3 default 0.2 (env-overridable)

**1107_132955**（20251107）

- 结果：OMR=0.4822，BMR=0.3671
- logs：[cachesim_sb3_1107_132955.log](cachesim_sb3_1107_132955.log) / [ac_sb3_1107_132955.log](ac_sb3_1107_132955.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=TD3；batch=256；lr=0.0003；gamma=0.99；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: TD3 (off-policy)
 - - policy_delay: 2 # previous/SB3 default 2
 - - policy.net_arch: [256, 256] # previous default [256,256]
 - - policy.activation_fn: ReLU # previous default ReLU

**1107_123724**（20251107）

- 结果：OMR=0.4866，BMR=0.3764
- logs：[cachesim_sb3_1107_123724.log](cachesim_sb3_1107_123724.log) / [ac_sb3_1107_123724.log](ac_sb3_1107_123724.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=TD3；batch=256；lr=0.0003；gamma=0.99；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: TD3 (off-policy)
 - - policy_delay: 2 # previous/SB3 default 2
 - - policy.net_arch: [256, 256] # previous default [256,256]
 - - policy.activation_fn: ReLU # previous default ReLU

**1107_111443**（20251107）

- 结果：OMR=0.4806，BMR=0.3658
- logs：[cachesim_sb3_1107_111443.log](cachesim_sb3_1107_111443.log) / [ac_sb3_1107_111443.log](ac_sb3_1107_111443.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)
 - - policy.net_arch: [256, 256]
 - - policy.activation_fn: <class 'torch.nn.modules.activation.ReLU'>

**1107_101048**（20251107）

- 结果：OMR=0.4862，BMR=0.3823
- logs：[cachesim_sb3_1107_101048.log](cachesim_sb3_1107_101048.log) / [ac_sb3_1107_101048.log](ac_sb3_1107_101048.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=TD3；batch=256；lr=0.0003；gamma=0.99；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: TD3 (off-policy)
 - - policy_delay: 2
 - - target_policy_noise: 0.1
 - - policy.net_arch: [256, 256]

**1107_033258**（20251107）

- 结果：OMR=0.4859，BMR=0.3770
- logs：[cachesim_sb3_1107_033258.log](cachesim_sb3_1107_033258.log) / [ac_sb3_1107_033258.log](ac_sb3_1107_033258.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=TD3；batch=256；lr=0.0003；gamma=0.99；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: TD3 (off-policy)
 - - policy_delay: 2
 - - target_policy_noise: 0.1
 - - policy.net_arch: [256, 256]

**1107_005228**（20251107）

- 结果：OMR=0.4828，BMR=0.3717
- logs：[cachesim_sb3_1107_005228.log](cachesim_sb3_1107_005228.log) / [ac_sb3_1107_005228.log](ac_sb3_1107_005228.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=TD3；batch=256；lr=0.0003；gamma=0.99；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: TD3 (off-policy)
 - - policy_delay: 2
 - - target_policy_noise: 0.1
 - - policy.net_arch: [256, 256]

**1107_005128**（20251107）

- 结果：OMR=0.5020，BMR=0.3866
- logs：[cachesim_sb3_1107_005128.log](cachesim_sb3_1107_005128.log) / [ac_sb3_1107_005128.log](ac_sb3_1107_005128.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=TD3；batch=256；lr=0.0003；gamma=0.99；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: TD3 (off-policy)
 - - policy_delay: 2
 - - target_policy_noise: 0.1
 - - policy.net_arch: [256, 256]

**1106_235905**（20251106）

- 结果：OMR=0.4944，BMR=0.3846
- logs：[cachesim_sb3_1106_235905.log](cachesim_sb3_1106_235905.log) / [ac_sb3_1106_235905.log](ac_sb3_1106_235905.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=TD3；batch=256；lr=0.0003；gamma=0.99；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: TD3 (off-policy)
 - - policy_delay: 2
 - - target_policy_noise: 0.1
 - - policy.net_arch: [256, 256]

**1106_231034**（20251106）

- 结果：OMR=0.4808，BMR=0.3589
- logs：[cachesim_sb3_1106_231034.log](cachesim_sb3_1106_231034.log) / [ac_sb3_1106_231034.log](ac_sb3_1106_231034.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=TD3；batch=256；lr=0.0003；gamma=0.99；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: TD3 (off-policy)
 - - policy_delay: 2
 - - target_policy_noise: 0.1
 - - policy.net_arch: [256, 256]

**1106_222626**（20251106）

- 结果：OMR=0.5075，BMR=0.3868
- logs：[cachesim_sb3_1106_222626.log](cachesim_sb3_1106_222626.log) / [ac_sb3_1106_222626.log](ac_sb3_1106_222626.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=TD3；batch=256；lr=0.0003；gamma=0.99；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: TD3 (off-policy)
 - - policy_delay: 2
 - - target_policy_noise: 0.1
 - - policy.net_arch: [256, 256]

**1106_213930**（20251106）

- 结果：OMR=0.4965，BMR=0.3867
- logs：[cachesim_sb3_1106_213930.log](cachesim_sb3_1106_213930.log) / [ac_sb3_1106_213930.log](ac_sb3_1106_213930.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=TD3；batch=256；lr=0.0003；gamma=0.99；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: TD3 (off-policy)
 - - policy_delay: 2
 - - target_policy_noise: 0.1
 - - policy.net_arch: [256, 256]

**1106_210904**（20251106）

- 结果：OMR=0.4957，BMR=0.3795
- logs：[cachesim_sb3_1106_210904.log](cachesim_sb3_1106_210904.log) / [ac_sb3_1106_210904.log](ac_sb3_1106_210904.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=TD3；batch=256；lr=0.0003；gamma=0.99；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: TD3 (off-policy)
 - - policy_delay: 2
 - - target_policy_noise: 0.1
 - - policy.net_arch: [256, 256]

**1106_195917**（20251106）

- 结果：OMR=0.4979，BMR=0.3901
- logs：[cachesim_sb3_1106_195917.log](cachesim_sb3_1106_195917.log) / [ac_sb3_1106_195917.log](ac_sb3_1106_195917.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=TD3；batch=256；lr=5e-06；gamma=0.99；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: TD3 (off-policy)
 - - policy_delay: 2
 - - target_policy_noise: 0.3
 - - policy.net_arch: [256, 256]

**1106_195218**（20251106）

- 结果：OMR=0.4998，BMR=0.3824
- logs：[cachesim_sb3_1106_195218.log](cachesim_sb3_1106_195218.log) / [ac_sb3_1106_195218.log](ac_sb3_1106_195218.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=TD3；batch=256；lr=5e-06；gamma=0.99；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: TD3 (off-policy)
 - - policy_delay: 2
 - - target_policy_noise: 0.1
 - - policy.net_arch: [256, 256]

**1106_111646**（20251106）

- 结果：OMR=0.4780，BMR=0.3619
- logs：[cachesim_sb3_1106_111646.log](cachesim_sb3_1106_111646.log) / [ac_sb3_1106_111646.log](ac_sb3_1106_111646.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=TD3；batch=256；lr=0.0003；gamma=0.99；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: TD3 (off-policy)
 - - policy.net_arch: [256, 256]

**1106_101920**（20251106）

- 结果：OMR=0.4779，BMR=0.3656
- logs：[cachesim_sb3_1106_101920.log](cachesim_sb3_1106_101920.log) / [ac_sb3_1106_101920.log](ac_sb3_1106_101920.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=TD3；batch=256；lr=0.0003；gamma=0.99；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: TD3 (off-policy)
 - - policy.net_arch: [256, 256]

**1106_095956**（20251106）

- 结果：OMR=0.5161，BMR=0.4107
- logs：[cachesim_sb3_1106_095956.log](cachesim_sb3_1106_095956.log) / [ac_sb3_1106_095956.log](ac_sb3_1106_095956.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000

**1106_094634**（20251106）

- 结果：OMR=0.4863，BMR=0.3658
- logs：[cachesim_sb3_1106_094634.log](cachesim_sb3_1106_094634.log) / [ac_sb3_1106_094634.log](ac_sb3_1106_094634.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000

**1106_093058**（20251106）

- 结果：OMR=0.4804，BMR=0.3657
- logs：[cachesim_sb3_1106_093058.log](cachesim_sb3_1106_093058.log) / [ac_sb3_1106_093058.log](ac_sb3_1106_093058.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000

**1104_193330**（20251104）

- 结果：OMR=0.4804，BMR=0.3656
- logs：[cachesim_sb3_1104_193330.log](cachesim_sb3_1104_193330.log) / [ac_sb3_1104_193330.log](ac_sb3_1104_193330.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=5e-05；gamma=0.99；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)
 - - policy.net_arch: [256, 256]
 - - policy.activation_fn: <class 'torch.nn.modules.activation.ReLU'>

**1104_180855**（20251104）

- 结果：OMR=0.4803，BMR=0.3655
- logs：[cachesim_sb3_1104_180855.log](cachesim_sb3_1104_180855.log) / [ac_sb3_1104_180855.log](ac_sb3_1104_180855.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=5e-05；gamma=0.99；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)
 - - policy.net_arch: [256, 256]
 - - policy.activation_fn: <class 'torch.nn.modules.activation.ReLU'>

**1031_161840**（20251031）

- 结果：OMR=0.4816，BMR=0.3696
- logs：[cachesim_sb3_1031_161840.log](cachesim_sb3_1031_161840.log) / [ac_sb3_1031_161840.log](ac_sb3_1031_161840.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：state=26；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)

**1031_151728**（20251031）

- 结果：OMR=0.4790，BMR=0.3624
- logs：[cachesim_sb3_1031_151728.log](cachesim_sb3_1031_151728.log) / [ac_sb3_1031_151728.log](ac_sb3_1031_151728.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：state=26；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)

**1031_023342**（20251031）

- 结果：OMR=0.4893，BMR=0.3729
- logs：[cachesim_sb3_1031_023342.log](cachesim_sb3_1031_023342.log) / [ac_sb3_1031_023342.log](ac_sb3_1031_023342.log)
- cachesim：req=10000000；mr_w=1.000 bmr_w=0.000
- RL：state=26；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)

**1031_022915**（20251031）

- 结果：OMR=0.4857，BMR=0.3677
- logs：[cachesim_sb3_1031_022915.log](cachesim_sb3_1031_022915.log) / [ac_sb3_1031_022915.log](ac_sb3_1031_022915.log)
- cachesim：req=10000000；mr_w=1.000 bmr_w=0.000
- RL：state=26；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)

**1031_015607**（20251031）

- 结果：OMR=0.4804，BMR=0.3665
- logs：[cachesim_sb3_1031_015607.log](cachesim_sb3_1031_015607.log) / [ac_sb3_1031_015607.log](ac_sb3_1031_015607.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：state=26；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)

**1031_014543**（20251031）

- 结果：OMR=0.4794，BMR=0.3652
- logs：[cachesim_sb3_1031_014543.log](cachesim_sb3_1031_014543.log) / [ac_sb3_1031_014543.log](ac_sb3_1031_014543.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：state=26；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)

**1030_231012**（20251030）

- 结果：OMR=0.4803，BMR=0.3654
- logs：[cachesim_sb3_1030_231012.log](cachesim_sb3_1030_231012.log) / [ac_sb3_1030_231012.log](ac_sb3_1030_231012.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=5e-05；gamma=0.99；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)
 - - policy.net_arch: [256, 256]
 - - policy.activation_fn: <class 'torch.nn.modules.activation.ReLU'>

**1030_213330**（20251030）

- 结果：OMR=0.4803，BMR=0.3656
- logs：[cachesim_sb3_1030_213330.log](cachesim_sb3_1030_213330.log) / [ac_sb3_1030_213330.log](ac_sb3_1030_213330.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=128；lr=5e-05；gamma=0.99；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)
 - - policy.net_arch: [256, 256]
 - - policy.activation_fn: <class 'torch.nn.modules.activation.ReLU'>

**1030_183716**（20251030）

- 结果：OMR=0.4804，BMR=0.3656
- logs：[cachesim_sb3_1030_183716.log](cachesim_sb3_1030_183716.log) / [ac_sb3_1030_183716.log](ac_sb3_1030_183716.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=512；lr=5e-05；gamma=0.99；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)
 - - policy.net_arch: [256, 256]
 - - policy.activation_fn: <class 'torch.nn.modules.activation.ReLU'>

**1030_014039**（20251030）

- 结果：OMR=0.4860，BMR=0.3751
- logs：[cachesim_sb3_1030_014039.log](cachesim_sb3_1030_014039.log) / [ac_sb3_1030_014039.log](ac_sb3_1030_014039.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)

#### req=3000000（132 条）

| date | run | OMR | BMR | cfg | ref | note |
| ---: | --- | ---: | ---: | --- | --- | --- |
| 20260130 | 0130_001255 | 0.595834 | 0.475232 | SAC log1p=1 norm=1 cpd=1 irt=0 cacheF=0 candF=0 int=1000 | [cs](cachesim_sb3_0130_001255.log) [ac](ac_sb3_0130_001255.log) |  |
| 20251212 | 1212_113231 | 0.5945 | 0.4766 | PPO log1p=1 norm=1 cpd=1 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1212_113231.log) [ac](ac_sb3_1212_113231.log) |  |
| 20251212 | 1212_112245 | 0.5949 | 0.4776 | PPO_LSTM log1p=1 norm=1 cpd=1 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1212_112245.log) [ac](ac_sb3_1212_112245.log) |  |
| 20251208 | 1208_215501 | 0.9369 | 0.9284 | PPO log1p=1 norm=1 cpd=1 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_215501.log) [ac](ac_sb3_1208_215501.log) |  |
| 20251208 | 1208_180321 | 0.5962 | 0.4947 | PPO log1p=1 norm=1 cpd=1 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_180321.log) [ac](ac_sb3_1208_180321.log) |  |
| 20251208 | 1208_180301 | 0.6224 | 0.5144 | PPO log1p=1 norm=1 cpd=1 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_180301.log) [ac](ac_sb3_1208_180301.log) |  |
| 20251208 | 1208_180236 | 0.5951 | 0.4740 | PPO log1p=1 norm=1 cpd=1 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_180236.log) [ac](ac_sb3_1208_180236.log) |  |
| 20251208 | 1208_180213 | 0.7006 | 0.5939 | PPO log1p=1 norm=1 cpd=1 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_180213.log) [ac](ac_sb3_1208_180213.log) |  |
| 20251208 | 1208_180136 | 0.6468 | 0.5463 | PPO log1p=1 norm=1 cpd=1 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_180136.log) [ac](ac_sb3_1208_180136.log) |  |
| 20251208 | 1208_180113 | 0.5956 | 0.4763 | PPO log1p=1 norm=1 cpd=1 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_180113.log) [ac](ac_sb3_1208_180113.log) |  |
| 20251208 | 1208_171331 | 0.5942 | 0.4768 | PPO log1p=1 norm=1 cpd=1 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_171331.log) [ac](ac_sb3_1208_171331.log) |  |
| 20251208 | 1208_165353 | 0.5949 | 0.4780 | PPO log1p=1 norm=1 cpd=1 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_165353.log) [ac](ac_sb3_1208_165353.log) |  |
| 20251208 | 1208_095510 | 0.6407 | 0.5507 | PPO cpd=1 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_095510.log) [ac](ac_sb3_1208_095510.log) |  |
| 20251208 | 1208_094831 | 0.5938 | 0.4759 | PPO cpd=1 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_094831.log) [ac](ac_sb3_1208_094831.log) |  |
| 20251208 | 1208_031028 | 0.6429 | 0.5591 | PPO cpd=0 irt=1 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_031028.log) [ac](ac_sb3_1208_031028.log) |  |
| 20251208 | 1208_025733 | 0.6434 | 0.5529 | PPO cpd=0 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_025733.log) [ac](ac_sb3_1208_025733.log) |  |
| 20251208 | 1208_020748 | 0.5934 | 0.4756 | PPO cpd=0 irt=1 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_020748.log) [ac](ac_sb3_1208_020748.log) |  |
| 20251208 | 1208_013151 | 0.6298 | 0.5275 | PPO cpd=0 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_013151.log) [ac](ac_sb3_1208_013151.log) |  |
| 20251204 | 1204_020125 | 0.5933 | 0.4754 | PPO int=200 | [cs](cachesim_sb3_1204_020125.log) [ac](ac_sb3_1204_020125.log) |  |
| 20251202 | 1202_181054 | 0.5948 | 0.4759 | PPO_LSTM int=200 | [cs](cachesim_sb3_1202_181054.log) [ac](ac_sb3_1202_181054.log) |  |
| 20251202 | 1202_154811 | 0.5954 | 0.4765 | PPO int=200 | [cs](cachesim_sb3_1202_154811.log) [ac](ac_sb3_1202_154811.log) |  |
| 20251202 | 1202_154004 | 0.5949 | 0.4758 | PPO_LSTM int=200 | [cs](cachesim_sb3_1202_154004.log) [ac](ac_sb3_1202_154004.log) |  |
| 20251201 | 1201_224555 | 0.6381 | 0.5584 | SAC int=200 | [cs](cachesim_sb3_1201_224555.log) [ac](ac_sb3_1201_224555.log) |  |
| 20251201 | 1201_215107 | 0.5950 | 0.4966 | PPO int=200 | [cs](cachesim_sb3_1201_215107.log) [ac](ac_sb3_1201_215107.log) |  |
| 20251201 | 1201_153642 | 0.5960 | 0.4954 | PPO int=200 | [cs](cachesim_sb3_1201_153642.log) [ac](ac_sb3_1201_153642.log) |  |
| 20251201 | 1201_105056 | 0.5952 | 0.4940 | PPO int=200 | [cs](cachesim_sb3_1201_105056.log) [ac](ac_sb3_1201_105056.log) |  |
| 20251129 | 1129_180836 | 0.5931 | 0.4905 | PPO int=200 | [cs](cachesim_sb3_1129_180836.log) [ac](ac_sb3_1129_180836.log) |  |
| 20251129 | 1129_171412 | 0.5944 | 0.4922 | PPO int=200 | [cs](cachesim_sb3_1129_171412.log) [ac](ac_sb3_1129_171412.log) |  |
| 20251129 | 1129_170408 | 0.6396 | 0.5603 | PPO int=200 | [cs](cachesim_sb3_1129_170408.log) [ac](ac_sb3_1129_170408.log) |  |
| 20251129 | 1129_164608 | 0.5945 | 0.4760 | PPO int=200 | [cs](cachesim_sb3_1129_164608.log) [ac](ac_sb3_1129_164608.log) |  |
| 20251129 | 1129_161807 | 0.6392 | 0.5598 | PPO int=200 | [cs](cachesim_sb3_1129_161807.log) [ac](ac_sb3_1129_161807.log) |  |
| 20251129 | 1129_161147 | 0.6387 | 0.5595 | PPO int=200 | [cs](cachesim_sb3_1129_161147.log) [ac](ac_sb3_1129_161147.log) |  |
| 20251129 | 1129_154732 | 0.6385 | 0.5569 | PPO int=200 | [cs](cachesim_sb3_1129_154732.log) [ac](ac_sb3_1129_154732.log) |  |
| 20251129 | 1129_151819 | 0.6409 | 0.5583 | PPO int=200 | [cs](cachesim_sb3_1129_151819.log) [ac](ac_sb3_1129_151819.log) |  |
| 20251128 | 1128_175715 | 0.5932 | 0.4750 | PPO int=200 | [cs](cachesim_sb3_1128_175715.log) [ac](ac_sb3_1128_175715.log) |  |
| 20251128 | 1128_152938 | 0.5924 | 0.4764 | PPO int=200 | [cs](cachesim_sb3_1128_152938.log) [ac](ac_sb3_1128_152938.log) |  |
| 20251128 | 1128_013716 | 0.6005 | 0.4743 | PPO int=200 | [cs](cachesim_sb3_1128_013716.log) [ac](ac_sb3_1128_013716.log) |  |
| 20251128 | 1128_011929 | 0.6093 | 0.4869 | PPO int=200 | [cs](cachesim_sb3_1128_011929.log) [ac](ac_sb3_1128_011929.log) |  |
| 20251128 | 1128_005757 | 0.6038 | 0.4777 | PPO int=200 | [cs](cachesim_sb3_1128_005757.log) [ac](ac_sb3_1128_005757.log) |  |
| 20251128 | 1128_004348 | 0.6489 | 0.5464 | PPO int=200 | [cs](cachesim_sb3_1128_004348.log) [ac](ac_sb3_1128_004348.log) |  |
| 20251127 | 1127_234506 | 0.6005 | 0.4739 | PPO int=200 | [cs](cachesim_sb3_1127_234506.log) [ac](ac_sb3_1127_234506.log) |  |
| 20251127 | 1127_204730 | 0.6045 | 0.4760 | PPO int=200 | [cs](cachesim_sb3_1127_204730.log) [ac](ac_sb3_1127_204730.log) |  |
| 20251127 | 1127_203955 | 0.5999 | 0.4724 | PPO int=200 | [cs](cachesim_sb3_1127_203955.log) [ac](ac_sb3_1127_203955.log) |  |
| 20251127 | 1127_201436 | 0.6026 | 0.4765 | PPO int=200 | [cs](cachesim_sb3_1127_201436.log) [ac](ac_sb3_1127_201436.log) |  |
| 20251127 | 1127_195505 | 0.6012 | 0.4736 | SAC int=200 | [cs](cachesim_sb3_1127_195505.log) [ac](ac_sb3_1127_195505.log) |  |
| 20251127 | 1127_180428 | 0.6019 | 0.4742 | SAC int=200 | [cs](cachesim_sb3_1127_180428.log) [ac](ac_sb3_1127_180428.log) |  |
| 20251127 | 1127_111716 | 0.6019 | 0.4742 | SAC int=200 | [cs](cachesim_sb3_1127_111716.log) [ac](ac_sb3_1127_111716.log) |  |
| 20251126 | 1126_183124 | 0.6020 | 0.4744 | SAC int=200 | [cs](cachesim_sb3_1126_183124.log) [ac](ac_sb3_1126_183124.log) |  |
| 20251125 | 1125_192821 | 0.6015 | 0.4739 | int=200 | [cs](cachesim_sb3_1125_192821.log) [ac](ac_sb3_1125_192821.log) |  |
| 20251125 | 1125_192214 | 0.6031 | 0.4758 | int=200 | [cs](cachesim_sb3_1125_192214.log) [ac](ac_sb3_1125_192214.log) |  |
| 20251125 | 1125_191855 | 0.6008 | 0.4734 | int=200 | [cs](cachesim_sb3_1125_191855.log) [ac](ac_sb3_1125_191855.log) |  |
| 20251124 | 1124_173556 | 0.6011 | 0.4738 | int=200 | [cs](cachesim_sb3_1124_173556.log) [ac](ac_sb3_1124_173556.log) |  |
| 20251124 | 1124_160957 | 0.6027 | 0.4756 | int=200 | [cs](cachesim_sb3_1124_160957.log) [ac](ac_sb3_1124_160957.log) |  |
| 20251124 | 1124_154707 | 0.6002 | 0.4724 | int=200 | [cs](cachesim_sb3_1124_154707.log) [ac](ac_sb3_1124_154707.log) |  |
| 20251124 | 1124_154301 | 0.6018 | 0.4742 | int=200 | [cs](cachesim_sb3_1124_154301.log) [ac](ac_sb3_1124_154301.log) |  |
| 20251124 | 1124_154035 | 0.6016 | 0.4740 | int=200 | [cs](cachesim_sb3_1124_154035.log) [ac](ac_sb3_1124_154035.log) |  |
| 20251124 | 1124_105331 | 0.6018 | 0.4725 | int=200 | [cs](cachesim_sb3_1124_105331.log) [ac](ac_sb3_1124_105331.log) |  |
| 20251124 | 1124_105137 | 0.6489 | 0.5464 | int=200 | [cs](cachesim_sb3_1124_105137.log) [ac](ac_sb3_1124_105137.log) |  |
| 20251121 | 1121_143202 | 0.6251 | 0.5148 | int=200 | [cs](cachesim_sb3_1121_143202.log) [ac](ac_sb3_1121_143202.log) |  |
| 20251121 | 1121_142752 | 0.6264 | 0.5166 | int=200 | [cs](cachesim_sb3_1121_142752.log) [ac](ac_sb3_1121_142752.log) |  |
| 20251121 | 1121_142540 | 0.6403 | 0.5398 | int=200 | [cs](cachesim_sb3_1121_142540.log) [ac](ac_sb3_1121_142540.log) |  |
| 20251121 | 1121_115911 | 0.6699 | 0.5669 | int=200 | [cs](cachesim_sb3_1121_115911.log) [ac](ac_sb3_1121_115911.log) |  |
| 20251121 | 1121_030525 | 0.6063 | 0.4847 | int=200 | [cs](cachesim_sb3_1121_030525.log) [ac](ac_sb3_1121_030525.log) |  |
| 20251121 | 1121_030407 | 0.7007 | 0.5935 | int=200 | [cs](cachesim_sb3_1121_030407.log) [ac](ac_sb3_1121_030407.log) |  |
| 20251121 | 1121_025424 | 0.6961 | 0.5865 | int=200 | [cs](cachesim_sb3_1121_025424.log) [ac](ac_sb3_1121_025424.log) |  |
| 20251121 | 1121_024336 | 0.7086 | 0.6081 | int=200 | [cs](cachesim_sb3_1121_024336.log) [ac](ac_sb3_1121_024336.log) |  |
| 20251121 | 1121_023203 | 0.6990 | 0.5916 | int=200 | [cs](cachesim_sb3_1121_023203.log) [ac](ac_sb3_1121_023203.log) |  |
| 20251121 | 1121_022030 | 0.7089 | 0.6050 | int=200 | [cs](cachesim_sb3_1121_022030.log) [ac](ac_sb3_1121_022030.log) |  |
| 20251120 | 1120_190639 | 0.6059 | 0.4852 | int=200 | [cs](cachesim_sb3_1120_190639.log) [ac](ac_sb3_1120_190639.log) |  |
| 20251120 | 1120_190412 | 0.6064 | 0.4848 | int=200 | [cs](cachesim_sb3_1120_190412.log) [ac](ac_sb3_1120_190412.log) |  |
| 20251120 | 1120_170745 | 0.6071 | 0.4870 | int=200 | [cs](cachesim_sb3_1120_170745.log) [ac](ac_sb3_1120_170745.log) |  |
| 20251120 | 1120_160659 | 0.6315 | 0.5247 | int=200 | [cs](cachesim_sb3_1120_160659.log) [ac](ac_sb3_1120_160659.log) |  |
| 20251118 | 1118_212802 | 0.6279 | 0.5211 | int=200 | [cs](cachesim_sb3_1118_212802.log) [ac](ac_sb3_1118_212802.log) |  |
| 20251118 | 1118_210712 | 0.6075 | 0.4943 | int=200 | [cs](cachesim_sb3_1118_210712.log) [ac](ac_sb3_1118_210712.log) |  |
| 20251118 | 1118_115151 | 0.6206 | 0.5013 | int=200 | [cs](cachesim_sb3_1118_115151.log) [ac](ac_sb3_1118_115151.log) |  |
| 20251118 | 1118_115104 | 0.6202 | 0.5003 | int=200 | [cs](cachesim_sb3_1118_115104.log) [ac](ac_sb3_1118_115104.log) |  |
| 20251118 | 1118_115018 | 0.6053 | 0.4820 | int=200 | [cs](cachesim_sb3_1118_115018.log) [ac](ac_sb3_1118_115018.log) |  |
| 20251118 | 1118_114933 | 0.6010 | 0.4758 | int=200 | [cs](cachesim_sb3_1118_114933.log) [ac](ac_sb3_1118_114933.log) |  |
| 20251118 | 1118_114844 | 0.6695 | 0.5730 | int=200 | [cs](cachesim_sb3_1118_114844.log) [ac](ac_sb3_1118_114844.log) |  |
| 20251118 | 1118_114757 | 0.6018 | 0.4725 | int=200 | [cs](cachesim_sb3_1118_114757.log) [ac](ac_sb3_1118_114757.log) |  |
| 20251118 | 1118_114705 | 0.6489 | 0.5464 | int=200 | [cs](cachesim_sb3_1118_114705.log) [ac](ac_sb3_1118_114705.log) |  |
| 20251118 | 1118_112411 | 0.6000 | 0.4789 | int=200 | [cs](cachesim_sb3_1118_112411.log) [ac](ac_sb3_1118_112411.log) |  |
| 20251118 | 1118_103046 | 0.6070 | 0.4867 | int=50 | [cs](cachesim_sb3_1118_103046.log) [ac](ac_sb3_1118_103046.log) |  |
| 20251118 | 1118_102436 | 0.6073 | 0.4873 | int=200 | [cs](cachesim_sb3_1118_102436.log) [ac](ac_sb3_1118_102436.log) |  |
| 20251117 | 1117_115330 | 0.6209 | 0.5013 | TD3 int=200 | [cs](cachesim_sb3_1117_115330.log) [ac](ac_sb3_1117_115330.log) |  |
| 20251114 | 1114_172051 | 0.6060 | 0.4844 | int=200 | [cs](cachesim_sb3_1114_172051.log) [ac](ac_sb3_1114_172051.log) |  |
| 20251114 | 1114_164220 | 0.6059 | 0.4852 | int=200 | [cs](cachesim_sb3_1114_164220.log) [ac](ac_sb3_1114_164220.log) |  |
| 20251114 | 1114_163206 | 0.6068 | 0.4861 | int=200 | [cs](cachesim_sb3_1114_163206.log) [ac](ac_sb3_1114_163206.log) |  |
| 20251114 | 1114_005014 | 0.6070 | 0.4859 | int=200 | [cs](cachesim_sb3_1114_005014.log) [ac](ac_sb3_1114_005014.log) |  |
| 20251114 | 1114_000426 | 0.6072 | 0.4864 | int=200 | [cs](cachesim_sb3_1114_000426.log) [ac](ac_sb3_1114_000426.log) |  |
| 20251113 | 1113_235904 | 0.6069 | 0.4861 | int=200 | [cs](cachesim_sb3_1113_235904.log) [ac](ac_sb3_1113_235904.log) |  |
| 20251113 | 1113_235401 | 0.6194 | 0.4992 | TD3 int=200 | [cs](cachesim_sb3_1113_235401.log) [ac](ac_sb3_1113_235401.log) |  |
| 20251113 | 1113_013954 | 0.6071 | 0.4861 | SAC int=200 | [cs](cachesim_sb3_1113_013954.log) [ac](ac_sb3_1113_013954.log) |  |
| 20251112 | 1112_215139 | 0.6070 | 0.4862 | SAC int=200 | [cs](cachesim_sb3_1112_215139.log) [ac](ac_sb3_1112_215139.log) |  |
| 20251112 | 1112_214357 | 0.6070 | 0.4862 | SAC int=200 | [cs](cachesim_sb3_1112_214357.log) [ac](ac_sb3_1112_214357.log) |  |
| 20251112 | 1112_201701 | 0.6070 | 0.4859 | SAC int=200 | [cs](cachesim_sb3_1112_201701.log) [ac](ac_sb3_1112_201701.log) |  |
| 20251112 | 1112_171554 | 0.6067 | 0.4858 | SAC int=200 | [cs](cachesim_sb3_1112_171554.log) [ac](ac_sb3_1112_171554.log) |  |
| 20251112 | 1112_170854 | 0.6068 | 0.4859 | SAC int=200 | [cs](cachesim_sb3_1112_170854.log) [ac](ac_sb3_1112_170854.log) |  |
| 20251112 | 1112_170054 | 0.6067 | 0.4860 | SAC int=200 | [cs](cachesim_sb3_1112_170054.log) [ac](ac_sb3_1112_170054.log) |  |
| 20251112 | 1112_165337 | 0.6072 | 0.4861 | SAC int=200 | [cs](cachesim_sb3_1112_165337.log) [ac](ac_sb3_1112_165337.log) |  |
| 20251112 | 1112_164813 | 0.6066 | 0.4860 | SAC int=200 | [cs](cachesim_sb3_1112_164813.log) [ac](ac_sb3_1112_164813.log) |  |
| 20251112 | 1112_164233 | 0.6065 | 0.4856 | SAC int=200 | [cs](cachesim_sb3_1112_164233.log) [ac](ac_sb3_1112_164233.log) |  |
| 20251112 | 1112_163452 | 0.6071 | 0.4860 | SAC int=200 | [cs](cachesim_sb3_1112_163452.log) [ac](ac_sb3_1112_163452.log) |  |
| 20251112 | 1112_162428 | 0.6066 | 0.4855 | SAC int=200 | [cs](cachesim_sb3_1112_162428.log) [ac](ac_sb3_1112_162428.log) |  |
| 20251112 | 1112_153403 | 0.6067 | 0.4859 | SAC int=200 | [cs](cachesim_sb3_1112_153403.log) [ac](ac_sb3_1112_153403.log) |  |
| 20251112 | 1112_152834 | 0.6066 | 0.4858 | SAC int=200 | [cs](cachesim_sb3_1112_152834.log) [ac](ac_sb3_1112_152834.log) |  |
| 20251112 | 1112_152205 | 0.6073 | 0.4866 | SAC int=200 | [cs](cachesim_sb3_1112_152205.log) [ac](ac_sb3_1112_152205.log) |  |
| 20251112 | 1112_151606 | 0.6065 | 0.4855 | SAC int=200 | [cs](cachesim_sb3_1112_151606.log) [ac](ac_sb3_1112_151606.log) |  |
| 20251112 | 1112_150239 | 0.6072 | 0.4861 | SAC int=200 | [cs](cachesim_sb3_1112_150239.log) [ac](ac_sb3_1112_150239.log) |  |
| 20251112 | 1112_111121 | 0.6067 | 0.4859 | SAC int=200 | [cs](cachesim_sb3_1112_111121.log) [ac](ac_sb3_1112_111121.log) |  |
| 20251112 | 1112_104707 | 0.6070 | 0.4859 | SAC int=200 | [cs](cachesim_sb3_1112_104707.log) [ac](ac_sb3_1112_104707.log) |  |
| 20251112 | 1112_104205 | 0.6067 | 0.4861 | SAC int=200 | [cs](cachesim_sb3_1112_104205.log) [ac](ac_sb3_1112_104205.log) |  |
| 20251112 | 1112_103344 | 0.6060 | 0.4850 | SAC int=200 | [cs](cachesim_sb3_1112_103344.log) [ac](ac_sb3_1112_103344.log) |  |
| 20251112 | 1112_102230 | 0.6065 | 0.4855 | SAC int=200 | [cs](cachesim_sb3_1112_102230.log) [ac](ac_sb3_1112_102230.log) |  |
| 20251112 | 1112_093841 | 0.6070 | 0.4856 | SAC int=200 | [cs](cachesim_sb3_1112_093841.log) [ac](ac_sb3_1112_093841.log) |  |
| 20251112 | 1112_093143 | 0.6070 | 0.4862 | SAC int=200 | [cs](cachesim_sb3_1112_093143.log) [ac](ac_sb3_1112_093143.log) |  |
| 20251112 | 1112_092240 | 0.6068 | 0.4858 | SAC int=200 | [cs](cachesim_sb3_1112_092240.log) [ac](ac_sb3_1112_092240.log) |  |
| 20251112 | 1112_091649 | 0.6069 | 0.4858 | SAC int=200 | [cs](cachesim_sb3_1112_091649.log) [ac](ac_sb3_1112_091649.log) |  |
| 20251111 | 1111_232759 | 0.6069 | 0.4859 | SAC int=200 | [cs](cachesim_sb3_1111_232759.log) [ac](ac_sb3_1111_232759.log) |  |
| 20251111 | 1111_225744 | 0.6070 | 0.4860 | SAC int=200 | [cs](cachesim_sb3_1111_225744.log) [ac](ac_sb3_1111_225744.log) |  |
| 20251111 | 1111_173233 | 0.6071 | 0.4861 | SAC int=200 | [cs](cachesim_sb3_1111_173233.log) [ac](ac_sb3_1111_173233.log) |  |
| 20251111 | 1111_110801 | 0.6071 | 0.4860 | SAC int=200 | [cs](cachesim_sb3_1111_110801.log) [ac](ac_sb3_1111_110801.log) |  |
| 20251111 | 1111_105220 | 0.6068 | 0.4862 | SAC int=200 | [cs](cachesim_sb3_1111_105220.log) [ac](ac_sb3_1111_105220.log) |  |
| 20251111 | 1111_104721 | 0.6067 | 0.4860 | SAC int=200 | [cs](cachesim_sb3_1111_104721.log) [ac](ac_sb3_1111_104721.log) |  |
| 20251111 | 1111_093620 | 0.6065 | 0.4864 | SAC int=200 | [cs](cachesim_sb3_1111_093620.log) [ac](ac_sb3_1111_093620.log) |  |
| 20251111 | 1111_092603 | 0.6062 | 0.4854 | SAC int=200 | [cs](cachesim_sb3_1111_092603.log) [ac](ac_sb3_1111_092603.log) |  |
| 20251111 | 1111_022525 | 0.6069 | 0.4860 | int=200 | [cs](cachesim_sb3_1111_022525.log) [ac](ac_sb3_1111_022525.log) |  |
| 20251111 | 1111_021920 | 0.6247 | 0.5123 | int=200 | [cs](cachesim_sb3_1111_021920.log) [ac](ac_sb3_1111_021920.log) |  |
| 20251111 | 1111_021301 | 0.6069 | 0.4857 | int=200 | [cs](cachesim_sb3_1111_021301.log) [ac](ac_sb3_1111_021301.log) |  |
| 20251110 | 1110_234753 | 0.6089 | 0.4856 | TD3 int=200 | [cs](cachesim_sb3_1110_234753.log) [ac](ac_sb3_1110_234753.log) |  |
| 20251110 | 1110_233455 | 0.6069 | 0.4859 | SAC int=200 | [cs](cachesim_sb3_1110_233455.log) [ac](ac_sb3_1110_233455.log) |  |
| 20251110 | 1110_232815 | 0.6067 | 0.4858 | SAC int=200 | [cs](cachesim_sb3_1110_232815.log) [ac](ac_sb3_1110_232815.log) |  |

##### 逐日志明细（req=3000000）

**0130_001255**（20260130）

- 结果：OMR=0.595834，BMR=0.475232
- logs：[cachesim_sb3_0130_001255.log](cachesim_sb3_0130_001255.log) / [ac_sb3_0130_001255.log](ac_sb3_0130_001255.log)
- cachesim：req=3000000；int=1000；mr_w=1.000 bmr_w=0.000；log1p=1；recip=0；norm=1；irt=0；cpd=1；cacheF=0；candF=0；state=600->602
 - [LOH INIT] Wait mode: default (BLOCKED)
 - [LOH INIT] Size data structure: SIZE_BUCKETS (全量分桶)
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**1212_113231**（20251212）

- 结果：OMR=0.5945，BMR=0.4766
- logs：[cachesim_sb3_1212_113231.log](cachesim_sb3_1212_113231.log) / [ac_sb3_1212_113231.log](ac_sb3_1212_113231.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000；log1p=1；recip=0；norm=1；irt=0；cpd=1；cacheF=0；candF=0；state=600->602
 - [LOH INIT] Wait mode: default (BLOCKED)
 - [LOH INIT] Size data structure: SIZE_BUCKETS (全量分桶)
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1212_112245**（20251212）

- 结果：OMR=0.5949，BMR=0.4776
- logs：[cachesim_sb3_1212_112245.log](cachesim_sb3_1212_112245.log) / [ac_sb3_1212_112245.log](ac_sb3_1212_112245.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000；log1p=1；recip=0；norm=1；irt=0；cpd=1；cacheF=0；candF=0；state=600->602
 - [LOH INIT] Wait mode: default (BLOCKED)
 - [LOH INIT] Size data structure: SIZE_BUCKETS (全量分桶)
- RL：algo=PPO_LSTM；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1208_215501**（20251208）

- 结果：OMR=0.9369，BMR=0.9284
- logs：[cachesim_sb3_1208_215501.log](cachesim_sb3_1208_215501.log) / [ac_sb3_1208_215501.log](ac_sb3_1208_215501.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000；log1p=1；recip=0；norm=1；irt=0；cpd=1；cacheF=0；candF=0；state=0->2
 - [LOH INIT] Wait mode: default (BLOCKED)
 - [LOH INIT] Size data structure: SIZE_BUCKETS (全量分桶)
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1208_180321**（20251208）

- 结果：OMR=0.5962，BMR=0.4947
- logs：[cachesim_sb3_1208_180321.log](cachesim_sb3_1208_180321.log) / [ac_sb3_1208_180321.log](ac_sb3_1208_180321.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000；log1p=1；recip=0；norm=1；irt=0；cpd=1；cacheF=0；candF=0；state=0->2
 - [LOH INIT] Wait mode: default (BLOCKED)
 - [LOH INIT] Size data structure: SIZE_BUCKETS (全量分桶)
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1208_180301**（20251208）

- 结果：OMR=0.6224，BMR=0.5144
- logs：[cachesim_sb3_1208_180301.log](cachesim_sb3_1208_180301.log) / [ac_sb3_1208_180301.log](ac_sb3_1208_180301.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000；log1p=1；recip=0；norm=1；irt=0；cpd=1；cacheF=0；candF=0；state=0->2
 - [LOH INIT] Wait mode: default (BLOCKED)
 - [LOH INIT] Size data structure: SIZE_BUCKETS (全量分桶)
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1208_180236**（20251208）

- 结果：OMR=0.5951，BMR=0.4740
- logs：[cachesim_sb3_1208_180236.log](cachesim_sb3_1208_180236.log) / [ac_sb3_1208_180236.log](ac_sb3_1208_180236.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000；log1p=1；recip=0；norm=1；irt=0；cpd=1；cacheF=0；candF=0；state=0->2
 - [LOH INIT] Wait mode: default (BLOCKED)
 - [LOH INIT] Size data structure: SIZE_BUCKETS (全量分桶)
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1208_180213**（20251208）

- 结果：OMR=0.7006，BMR=0.5939
- logs：[cachesim_sb3_1208_180213.log](cachesim_sb3_1208_180213.log) / [ac_sb3_1208_180213.log](ac_sb3_1208_180213.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000；log1p=1；recip=0；norm=1；irt=0；cpd=1；cacheF=0；candF=0；state=0->2
 - [LOH INIT] Wait mode: default (BLOCKED)
 - [LOH INIT] Size data structure: SIZE_BUCKETS (全量分桶)
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1208_180136**（20251208）

- 结果：OMR=0.6468，BMR=0.5463
- logs：[cachesim_sb3_1208_180136.log](cachesim_sb3_1208_180136.log) / [ac_sb3_1208_180136.log](ac_sb3_1208_180136.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000；log1p=1；recip=0；norm=1；irt=0；cpd=1；cacheF=0；candF=0；state=0->2
 - [LOH INIT] Wait mode: default (BLOCKED)
 - [LOH INIT] Size data structure: SIZE_BUCKETS (全量分桶)
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1208_180113**（20251208）

- 结果：OMR=0.5956，BMR=0.4763
- logs：[cachesim_sb3_1208_180113.log](cachesim_sb3_1208_180113.log) / [ac_sb3_1208_180113.log](ac_sb3_1208_180113.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000；log1p=1；recip=0；norm=1；irt=0；cpd=1；cacheF=0；candF=0；state=0->2
 - [LOH INIT] Wait mode: default (BLOCKED)
 - [LOH INIT] Size data structure: SIZE_BUCKETS (全量分桶)
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1208_171331**（20251208）

- 结果：OMR=0.5942，BMR=0.4768
- logs：[cachesim_sb3_1208_171331.log](cachesim_sb3_1208_171331.log) / [ac_sb3_1208_171331.log](ac_sb3_1208_171331.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000；log1p=1；recip=0；norm=1；irt=0；cpd=1；cacheF=0；candF=0；state=0->2
 - [LOH INIT] Wait mode: default (BLOCKED)
 - [LOH INIT] Size data structure: SIZE_BUCKETS (全量分桶)
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1208_165353**（20251208）

- 结果：OMR=0.5949，BMR=0.4780
- logs：[cachesim_sb3_1208_165353.log](cachesim_sb3_1208_165353.log) / [ac_sb3_1208_165353.log](ac_sb3_1208_165353.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000；log1p=1；recip=0；norm=1；irt=0；cpd=1；cacheF=0；candF=0；state=600->614
 - [LOH INIT] AvgTopK enabled: TOP4 × 6特征 = 24维
 - [LOH INIT] Wait mode: default (BLOCKED)
 - [LOH INIT] Size data structure: SIZE_BUCKETS (全量分桶)
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1208_095510**（20251208）

- 结果：OMR=0.6407，BMR=0.5507
- logs：[cachesim_sb3_1208_095510.log](cachesim_sb3_1208_095510.log) / [ac_sb3_1208_095510.log](ac_sb3_1208_095510.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000；irt=0；cpd=1；cacheF=0；candF=0；state=0->14
 - [LOH INIT] AvgTopK enabled: TOP4 × 6特征 = 24维
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1208_094831**（20251208）

- 结果：OMR=0.5938，BMR=0.4759
- logs：[cachesim_sb3_1208_094831.log](cachesim_sb3_1208_094831.log) / [ac_sb3_1208_094831.log](ac_sb3_1208_094831.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000；irt=0；cpd=1；cacheF=0；candF=0；state=0->14
 - [LOH INIT] AvgTopK enabled: TOP4 × 6特征 = 24维
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1208_031028**（20251208）

- 结果：OMR=0.6429，BMR=0.5591
- logs：[cachesim_sb3_1208_031028.log](cachesim_sb3_1208_031028.log) / [ac_sb3_1208_031028.log](ac_sb3_1208_031028.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000；irt=1；cpd=0；cacheF=0；candF=0；state=0->26
 - [LOH INIT] AvgTopK enabled: TOP4 × 6特征 = 24维
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1208_025733**（20251208）

- 结果：OMR=0.6434，BMR=0.5529
- logs：[cachesim_sb3_1208_025733.log](cachesim_sb3_1208_025733.log) / [ac_sb3_1208_025733.log](ac_sb3_1208_025733.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000；irt=0；cpd=0；cacheF=0；candF=0；state=0->14
 - [LOH INIT] AvgTopK enabled: TOP4 × 6特征 = 24维
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1208_020748**（20251208）

- 结果：OMR=0.5934，BMR=0.4756
- logs：[cachesim_sb3_1208_020748.log](cachesim_sb3_1208_020748.log) / [ac_sb3_1208_020748.log](ac_sb3_1208_020748.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000；irt=1；cpd=0；cacheF=0；candF=0；state=0->26
 - [LOH INIT] AvgTopK enabled: TOP4 × 6特征 = 24维
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1208_013151**（20251208）

- 结果：OMR=0.6298，BMR=0.5275
- logs：[cachesim_sb3_1208_013151.log](cachesim_sb3_1208_013151.log) / [ac_sb3_1208_013151.log](ac_sb3_1208_013151.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000；irt=0；cpd=0；cacheF=0；candF=0；state=0->14
 - [LOH INIT] AvgTopK enabled: TOP4 × 6特征 = 24维
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1204_020125**（20251204）

- 结果：OMR=0.5933，BMR=0.4754
- logs：[cachesim_sb3_1204_020125.log](cachesim_sb3_1204_020125.log) / [ac_sb3_1204_020125.log](ac_sb3_1204_020125.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1202_181054**（20251202）

- 结果：OMR=0.5948，BMR=0.4759
- logs：[cachesim_sb3_1202_181054.log](cachesim_sb3_1202_181054.log) / [ac_sb3_1202_181054.log](ac_sb3_1202_181054.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=PPO_LSTM；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1202_154811**（20251202）

- 结果：OMR=0.5954，BMR=0.4765
- logs：[cachesim_sb3_1202_154811.log](cachesim_sb3_1202_154811.log) / [ac_sb3_1202_154811.log](ac_sb3_1202_154811.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1202_154004**（20251202）

- 结果：OMR=0.5949，BMR=0.4758
- logs：[cachesim_sb3_1202_154004.log](cachesim_sb3_1202_154004.log) / [ac_sb3_1202_154004.log](ac_sb3_1202_154004.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=PPO_LSTM；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1201_224555**（20251201）

- 结果：OMR=0.6381，BMR=0.5584
- logs：[cachesim_sb3_1201_224555.log](cachesim_sb3_1201_224555.log) / [ac_sb3_1201_224555.log](ac_sb3_1201_224555.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**1201_215107**（20251201）

- 结果：OMR=0.5950，BMR=0.4966
- logs：[cachesim_sb3_1201_215107.log](cachesim_sb3_1201_215107.log) / [ac_sb3_1201_215107.log](ac_sb3_1201_215107.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
 - [LOH INIT] AvgTopK enabled: TOP4 × 6特征 = 24维
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1201_153642**（20251201）

- 结果：OMR=0.5960，BMR=0.4954
- logs：[cachesim_sb3_1201_153642.log](cachesim_sb3_1201_153642.log) / [ac_sb3_1201_153642.log](ac_sb3_1201_153642.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1201_105056**（20251201）

- 结果：OMR=0.5952，BMR=0.4940
- logs：[cachesim_sb3_1201_105056.log](cachesim_sb3_1201_105056.log) / [ac_sb3_1201_105056.log](ac_sb3_1201_105056.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1129_180836**（20251129）

- 结果：OMR=0.5931，BMR=0.4905
- logs：[cachesim_sb3_1129_180836.log](cachesim_sb3_1129_180836.log) / [ac_sb3_1129_180836.log](ac_sb3_1129_180836.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1129_171412**（20251129）

- 结果：OMR=0.5944，BMR=0.4922
- logs：[cachesim_sb3_1129_171412.log](cachesim_sb3_1129_171412.log) / [ac_sb3_1129_171412.log](ac_sb3_1129_171412.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1129_170408**（20251129）

- 结果：OMR=0.6396，BMR=0.5603
- logs：[cachesim_sb3_1129_170408.log](cachesim_sb3_1129_170408.log) / [ac_sb3_1129_170408.log](ac_sb3_1129_170408.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1129_164608**（20251129）

- 结果：OMR=0.5945，BMR=0.4760
- logs：[cachesim_sb3_1129_164608.log](cachesim_sb3_1129_164608.log) / [ac_sb3_1129_164608.log](ac_sb3_1129_164608.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1129_161807**（20251129）

- 结果：OMR=0.6392，BMR=0.5598
- logs：[cachesim_sb3_1129_161807.log](cachesim_sb3_1129_161807.log) / [ac_sb3_1129_161807.log](ac_sb3_1129_161807.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1129_161147**（20251129）

- 结果：OMR=0.6387，BMR=0.5595
- logs：[cachesim_sb3_1129_161147.log](cachesim_sb3_1129_161147.log) / [ac_sb3_1129_161147.log](ac_sb3_1129_161147.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1129_154732**（20251129）

- 结果：OMR=0.6385，BMR=0.5569
- logs：[cachesim_sb3_1129_154732.log](cachesim_sb3_1129_154732.log) / [ac_sb3_1129_154732.log](ac_sb3_1129_154732.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1129_151819**（20251129）

- 结果：OMR=0.6409，BMR=0.5583
- logs：[cachesim_sb3_1129_151819.log](cachesim_sb3_1129_151819.log) / [ac_sb3_1129_151819.log](ac_sb3_1129_151819.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1128_175715**（20251128）

- 结果：OMR=0.5932，BMR=0.4750
- logs：[cachesim_sb3_1128_175715.log](cachesim_sb3_1128_175715.log) / [ac_sb3_1128_175715.log](ac_sb3_1128_175715.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
 - [LOH INIT] AvgTopK enabled: TOP4 × 6特征 = 24维
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1128_152938**（20251128）

- 结果：OMR=0.5924，BMR=0.4764
- logs：[cachesim_sb3_1128_152938.log](cachesim_sb3_1128_152938.log) / [ac_sb3_1128_152938.log](ac_sb3_1128_152938.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1128_013716**（20251128）

- 结果：OMR=0.6005，BMR=0.4743
- logs：[cachesim_sb3_1128_013716.log](cachesim_sb3_1128_013716.log) / [ac_sb3_1128_013716.log](ac_sb3_1128_013716.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
 - [LOH INIT] AvgTopK enabled: TOP4 × 6特征 = 24维
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1128_011929**（20251128）

- 结果：OMR=0.6093，BMR=0.4869
- logs：[cachesim_sb3_1128_011929.log](cachesim_sb3_1128_011929.log) / [ac_sb3_1128_011929.log](ac_sb3_1128_011929.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1128_005757**（20251128）

- 结果：OMR=0.6038，BMR=0.4777
- logs：[cachesim_sb3_1128_005757.log](cachesim_sb3_1128_005757.log) / [ac_sb3_1128_005757.log](ac_sb3_1128_005757.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1128_004348**（20251128）

- 结果：OMR=0.6489，BMR=0.5464
- logs：[cachesim_sb3_1128_004348.log](cachesim_sb3_1128_004348.log) / [ac_sb3_1128_004348.log](ac_sb3_1128_004348.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
 - [LOH INIT] AvgTopK enabled: TOP4 × 6特征 = 24维
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1127_234506**（20251127）

- 结果：OMR=0.6005，BMR=0.4739
- logs：[cachesim_sb3_1127_234506.log](cachesim_sb3_1127_234506.log) / [ac_sb3_1127_234506.log](ac_sb3_1127_234506.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
 - [LOH INIT] AvgTopK enabled: TOP4 × 6特征 = 24维
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1127_204730**（20251127）

- 结果：OMR=0.6045，BMR=0.4760
- logs：[cachesim_sb3_1127_204730.log](cachesim_sb3_1127_204730.log) / [ac_sb3_1127_204730.log](ac_sb3_1127_204730.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1127_203955**（20251127）

- 结果：OMR=0.5999，BMR=0.4724
- logs：[cachesim_sb3_1127_203955.log](cachesim_sb3_1127_203955.log) / [ac_sb3_1127_203955.log](ac_sb3_1127_203955.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1127_201436**（20251127）

- 结果：OMR=0.6026，BMR=0.4765
- logs：[cachesim_sb3_1127_201436.log](cachesim_sb3_1127_201436.log) / [ac_sb3_1127_201436.log](ac_sb3_1127_201436.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1127_195505**（20251127）

- 结果：OMR=0.6012，BMR=0.4736
- logs：[cachesim_sb3_1127_195505.log](cachesim_sb3_1127_195505.log) / [ac_sb3_1127_195505.log](ac_sb3_1127_195505.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**1127_180428**（20251127）

- 结果：OMR=0.6019，BMR=0.4742
- logs：[cachesim_sb3_1127_180428.log](cachesim_sb3_1127_180428.log) / [ac_sb3_1127_180428.log](ac_sb3_1127_180428.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**1127_111716**（20251127）

- 结果：OMR=0.6019，BMR=0.4742
- logs：[cachesim_sb3_1127_111716.log](cachesim_sb3_1127_111716.log) / [ac_sb3_1127_111716.log](ac_sb3_1127_111716.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**1126_183124**（20251126）

- 结果：OMR=0.6020，BMR=0.4744
- logs：[cachesim_sb3_1126_183124.log](cachesim_sb3_1126_183124.log) / [ac_sb3_1126_183124.log](ac_sb3_1126_183124.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**1125_192821**（20251125）

- 结果：OMR=0.6015，BMR=0.4739
- logs：[cachesim_sb3_1125_192821.log](cachesim_sb3_1125_192821.log) / [ac_sb3_1125_192821.log](ac_sb3_1125_192821.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：batch=32；lr=0.0001；ent=0.02；state=194；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)

**1125_192214**（20251125）

- 结果：OMR=0.6031，BMR=0.4758
- logs：[cachesim_sb3_1125_192214.log](cachesim_sb3_1125_192214.log) / [ac_sb3_1125_192214.log](ac_sb3_1125_192214.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：batch=32；lr=0.0001；ent=0.02；state=194；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)

**1125_191855**（20251125）

- 结果：OMR=0.6008，BMR=0.4734
- logs：[cachesim_sb3_1125_191855.log](cachesim_sb3_1125_191855.log) / [ac_sb3_1125_191855.log](ac_sb3_1125_191855.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：batch=32；lr=0.0001；ent=0.02；state=194；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)

**1124_173556**（20251124）

- 结果：OMR=0.6011，BMR=0.4738
- logs：[cachesim_sb3_1124_173556.log](cachesim_sb3_1124_173556.log) / [ac_sb3_1124_173556.log](ac_sb3_1124_173556.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000

**1124_160957**（20251124）

- 结果：OMR=0.6027，BMR=0.4756
- logs：[cachesim_sb3_1124_160957.log](cachesim_sb3_1124_160957.log) / [ac_sb3_1124_160957.log](ac_sb3_1124_160957.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：batch=32；lr=0.0001；ent=0.02；state=38；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)

**1124_154707**（20251124）

- 结果：OMR=0.6002，BMR=0.4724
- logs：[cachesim_sb3_1124_154707.log](cachesim_sb3_1124_154707.log) / [ac_sb3_1124_154707.log](ac_sb3_1124_154707.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：batch=32；lr=0.0001；ent=0.02；state=38；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)

**1124_154301**（20251124）

- 结果：OMR=0.6018，BMR=0.4742
- logs：[cachesim_sb3_1124_154301.log](cachesim_sb3_1124_154301.log) / [ac_sb3_1124_154301.log](ac_sb3_1124_154301.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：batch=32；lr=0.0001；ent=0.02；state=38；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)

**1124_154035**（20251124）

- 结果：OMR=0.6016，BMR=0.4740
- logs：[cachesim_sb3_1124_154035.log](cachesim_sb3_1124_154035.log) / [ac_sb3_1124_154035.log](ac_sb3_1124_154035.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：batch=32；lr=0.0001；ent=0.02；state=38；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)

**1124_105331**（20251124）

- 结果：OMR=0.6018，BMR=0.4725
- logs：[cachesim_sb3_1124_105331.log](cachesim_sb3_1124_105331.log) / [ac_sb3_1124_105331.log](ac_sb3_1124_105331.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000

**1124_105137**（20251124）

- 结果：OMR=0.6489，BMR=0.5464
- logs：[cachesim_sb3_1124_105137.log](cachesim_sb3_1124_105137.log) / [ac_sb3_1124_105137.log](ac_sb3_1124_105137.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000

**1121_143202**（20251121）

- 结果：OMR=0.6251，BMR=0.5148
- logs：[cachesim_sb3_1121_143202.log](cachesim_sb3_1121_143202.log) / [ac_sb3_1121_143202.log](ac_sb3_1121_143202.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：batch=32；lr=0.0001；ent=0.02；state=38；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)

**1121_142752**（20251121）

- 结果：OMR=0.6264，BMR=0.5166
- logs：[cachesim_sb3_1121_142752.log](cachesim_sb3_1121_142752.log) / [ac_sb3_1121_142752.log](ac_sb3_1121_142752.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：batch=32；lr=0.0001；ent=0.02；state=38；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)

**1121_142540**（20251121）

- 结果：OMR=0.6403，BMR=0.5398
- logs：[cachesim_sb3_1121_142540.log](cachesim_sb3_1121_142540.log) / [ac_sb3_1121_142540.log](ac_sb3_1121_142540.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：batch=32；lr=0.0001；ent=0.02；state=38；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)

**1121_115911**（20251121）

- 结果：OMR=0.6699，BMR=0.5669
- logs：[cachesim_sb3_1121_115911.log](cachesim_sb3_1121_115911.log) / [ac_sb3_1121_115911.log](ac_sb3_1121_115911.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：batch=32；lr=0.0001；ent=0.02；state=38；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)

**1121_030525**（20251121）

- 结果：OMR=0.6063，BMR=0.4847
- logs：[cachesim_sb3_1121_030525.log](cachesim_sb3_1121_030525.log) / [ac_sb3_1121_030525.log](ac_sb3_1121_030525.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：batch=32；lr=0.0001；ent=0.02；state=38；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)

**1121_030407**（20251121）

- 结果：OMR=0.7007，BMR=0.5935
- logs：[cachesim_sb3_1121_030407.log](cachesim_sb3_1121_030407.log) / [ac_sb3_1121_030407.log](ac_sb3_1121_030407.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：batch=32；lr=0.0001；ent=0.02；state=38；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)

**1121_025424**（20251121）

- 结果：OMR=0.6961，BMR=0.5865
- logs：[cachesim_sb3_1121_025424.log](cachesim_sb3_1121_025424.log) / [ac_sb3_1121_025424.log](ac_sb3_1121_025424.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：batch=32；lr=0.0001；ent=0.02；state=38；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)

**1121_024336**（20251121）

- 结果：OMR=0.7086，BMR=0.6081
- logs：[cachesim_sb3_1121_024336.log](cachesim_sb3_1121_024336.log) / [ac_sb3_1121_024336.log](ac_sb3_1121_024336.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：batch=32；lr=0.0001；ent=0.02；state=38；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)

**1121_023203**（20251121）

- 结果：OMR=0.6990，BMR=0.5916
- logs：[cachesim_sb3_1121_023203.log](cachesim_sb3_1121_023203.log) / [ac_sb3_1121_023203.log](ac_sb3_1121_023203.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：batch=32；lr=0.0001；ent=0.02；state=38；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)

**1121_022030**（20251121）

- 结果：OMR=0.7089，BMR=0.6050
- logs：[cachesim_sb3_1121_022030.log](cachesim_sb3_1121_022030.log) / [ac_sb3_1121_022030.log](ac_sb3_1121_022030.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：batch=32；lr=0.0001；ent=0.02；state=38；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)

**1120_190639**（20251120）

- 结果：OMR=0.6059，BMR=0.4852
- logs：[cachesim_sb3_1120_190639.log](cachesim_sb3_1120_190639.log) / [ac_sb3_1120_190639.log](ac_sb3_1120_190639.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：batch=32；lr=0.0001；ent=0.02；state=38；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)

**1120_190412**（20251120）

- 结果：OMR=0.6064，BMR=0.4848
- logs：[cachesim_sb3_1120_190412.log](cachesim_sb3_1120_190412.log) / [ac_sb3_1120_190412.log](ac_sb3_1120_190412.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：batch=32；lr=0.0001；ent=0.02；state=38；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)

**1120_170745**（20251120）

- 结果：OMR=0.6071，BMR=0.4870
- logs：[cachesim_sb3_1120_170745.log](cachesim_sb3_1120_170745.log) / [ac_sb3_1120_170745.log](ac_sb3_1120_170745.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：batch=32；lr=0.0001；ent=0.02；state=38；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)

**1120_160659**（20251120）

- 结果：OMR=0.6315，BMR=0.5247
- logs：[cachesim_sb3_1120_160659.log](cachesim_sb3_1120_160659.log) / [ac_sb3_1120_160659.log](ac_sb3_1120_160659.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：batch=32；lr=0.0001；ent=0.02；state=38；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)

**1118_212802**（20251118）

- 结果：OMR=0.6279，BMR=0.5211
- logs：[cachesim_sb3_1118_212802.log](cachesim_sb3_1118_212802.log) / [ac_sb3_1118_212802.log](ac_sb3_1118_212802.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000

**1118_210712**（20251118）

- 结果：OMR=0.6075，BMR=0.4943
- logs：[cachesim_sb3_1118_210712.log](cachesim_sb3_1118_210712.log) / [ac_sb3_1118_210712.log](ac_sb3_1118_210712.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000

**1118_115151**（20251118）

- 结果：OMR=0.6206，BMR=0.5013
- logs：[cachesim_sb3_1118_115151.log](cachesim_sb3_1118_115151.log) / [ac_sb3_1118_115151.log](ac_sb3_1118_115151.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000

**1118_115104**（20251118）

- 结果：OMR=0.6202，BMR=0.5003
- logs：[cachesim_sb3_1118_115104.log](cachesim_sb3_1118_115104.log) / [ac_sb3_1118_115104.log](ac_sb3_1118_115104.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000

**1118_115018**（20251118）

- 结果：OMR=0.6053，BMR=0.4820
- logs：[cachesim_sb3_1118_115018.log](cachesim_sb3_1118_115018.log) / [ac_sb3_1118_115018.log](ac_sb3_1118_115018.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000

**1118_114933**（20251118）

- 结果：OMR=0.6010，BMR=0.4758
- logs：[cachesim_sb3_1118_114933.log](cachesim_sb3_1118_114933.log) / [ac_sb3_1118_114933.log](ac_sb3_1118_114933.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000

**1118_114844**（20251118）

- 结果：OMR=0.6695，BMR=0.5730
- logs：[cachesim_sb3_1118_114844.log](cachesim_sb3_1118_114844.log) / [ac_sb3_1118_114844.log](ac_sb3_1118_114844.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000

**1118_114757**（20251118）

- 结果：OMR=0.6018，BMR=0.4725
- logs：[cachesim_sb3_1118_114757.log](cachesim_sb3_1118_114757.log) / [ac_sb3_1118_114757.log](ac_sb3_1118_114757.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000

**1118_114705**（20251118）

- 结果：OMR=0.6489，BMR=0.5464
- logs：[cachesim_sb3_1118_114705.log](cachesim_sb3_1118_114705.log) / [ac_sb3_1118_114705.log](ac_sb3_1118_114705.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000

**1118_112411**（20251118）

- 结果：OMR=0.6000，BMR=0.4789
- logs：[cachesim_sb3_1118_112411.log](cachesim_sb3_1118_112411.log) / [ac_sb3_1118_112411.log](ac_sb3_1118_112411.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000

**1118_103046**（20251118）

- 结果：OMR=0.6070，BMR=0.4867
- logs：[cachesim_sb3_1118_103046.log](cachesim_sb3_1118_103046.log) / [ac_sb3_1118_103046.log](ac_sb3_1118_103046.log)
- cachesim：req=3000000；int=50；mr_w=1.000 bmr_w=0.000
- RL：batch=32；lr=0.0001；ent=0.02；state=38；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)

**1118_102436**（20251118）

- 结果：OMR=0.6073，BMR=0.4873
- logs：[cachesim_sb3_1118_102436.log](cachesim_sb3_1118_102436.log) / [ac_sb3_1118_102436.log](ac_sb3_1118_102436.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：batch=32；lr=0.0001；ent=0.02；state=38；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)

**1117_115330**（20251117）

- 结果：OMR=0.6209，BMR=0.5013
- logs：[cachesim_sb3_1117_115330.log](cachesim_sb3_1117_115330.log) / [ac_sb3_1117_115330.log](ac_sb3_1117_115330.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=TD3；batch=256；lr=0.0003；gamma=0.99；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: TD3 (off-policy)
 - - policy_delay: 2 # previous/SB3 default 2
 - - target_policy_noise: 0.2 # SB3 default 0.2 (env-overridable)

**1114_172051**（20251114）

- 结果：OMR=0.6060，BMR=0.4844
- logs：[cachesim_sb3_1114_172051.log](cachesim_sb3_1114_172051.log) / [ac_sb3_1114_172051.log](ac_sb3_1114_172051.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：batch=32；lr=0.0001；ent=0.02；state=38；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)

**1114_164220**（20251114）

- 结果：OMR=0.6059，BMR=0.4852
- logs：[cachesim_sb3_1114_164220.log](cachesim_sb3_1114_164220.log) / [ac_sb3_1114_164220.log](ac_sb3_1114_164220.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：batch=32；lr=0.0001；ent=0.02；state=38；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)

**1114_163206**（20251114）

- 结果：OMR=0.6068，BMR=0.4861
- logs：[cachesim_sb3_1114_163206.log](cachesim_sb3_1114_163206.log) / [ac_sb3_1114_163206.log](ac_sb3_1114_163206.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000

**1114_005014**（20251114）

- 结果：OMR=0.6070，BMR=0.4859
- logs：[cachesim_sb3_1114_005014.log](cachesim_sb3_1114_005014.log) / [ac_sb3_1114_005014.log](ac_sb3_1114_005014.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000

**1114_000426**（20251114）

- 结果：OMR=0.6072，BMR=0.4864
- logs：[cachesim_sb3_1114_000426.log](cachesim_sb3_1114_000426.log) / [ac_sb3_1114_000426.log](ac_sb3_1114_000426.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000

**1113_235904**（20251113）

- 结果：OMR=0.6069，BMR=0.4861
- logs：[cachesim_sb3_1113_235904.log](cachesim_sb3_1113_235904.log) / [ac_sb3_1113_235904.log](ac_sb3_1113_235904.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000

**1113_235401**（20251113）

- 结果：OMR=0.6194，BMR=0.4992
- logs：[cachesim_sb3_1113_235401.log](cachesim_sb3_1113_235401.log) / [ac_sb3_1113_235401.log](ac_sb3_1113_235401.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=TD3；batch=256；lr=0.0003；gamma=0.99；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: TD3 (off-policy)
 - - policy_delay: 2 # previous/SB3 default 2
 - - target_policy_noise: 0.2 # SB3 default 0.2 (env-overridable)

**1113_013954**（20251113）

- 结果：OMR=0.6071，BMR=0.4861
- logs：[cachesim_sb3_1113_013954.log](cachesim_sb3_1113_013954.log) / [ac_sb3_1113_013954.log](ac_sb3_1113_013954.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**1112_215139**（20251112）

- 结果：OMR=0.6070，BMR=0.4862
- logs：[cachesim_sb3_1112_215139.log](cachesim_sb3_1112_215139.log) / [ac_sb3_1112_215139.log](ac_sb3_1112_215139.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**1112_214357**（20251112）

- 结果：OMR=0.6070，BMR=0.4862
- logs：[cachesim_sb3_1112_214357.log](cachesim_sb3_1112_214357.log) / [ac_sb3_1112_214357.log](ac_sb3_1112_214357.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**1112_201701**（20251112）

- 结果：OMR=0.6070，BMR=0.4859
- logs：[cachesim_sb3_1112_201701.log](cachesim_sb3_1112_201701.log) / [ac_sb3_1112_201701.log](ac_sb3_1112_201701.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**1112_171554**（20251112）

- 结果：OMR=0.6067，BMR=0.4858
- logs：[cachesim_sb3_1112_171554.log](cachesim_sb3_1112_171554.log) / [ac_sb3_1112_171554.log](ac_sb3_1112_171554.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**1112_170854**（20251112）

- 结果：OMR=0.6068，BMR=0.4859
- logs：[cachesim_sb3_1112_170854.log](cachesim_sb3_1112_170854.log) / [ac_sb3_1112_170854.log](ac_sb3_1112_170854.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**1112_170054**（20251112）

- 结果：OMR=0.6067，BMR=0.4860
- logs：[cachesim_sb3_1112_170054.log](cachesim_sb3_1112_170054.log) / [ac_sb3_1112_170054.log](ac_sb3_1112_170054.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**1112_165337**（20251112）

- 结果：OMR=0.6072，BMR=0.4861
- logs：[cachesim_sb3_1112_165337.log](cachesim_sb3_1112_165337.log) / [ac_sb3_1112_165337.log](ac_sb3_1112_165337.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**1112_164813**（20251112）

- 结果：OMR=0.6066，BMR=0.4860
- logs：[cachesim_sb3_1112_164813.log](cachesim_sb3_1112_164813.log) / [ac_sb3_1112_164813.log](ac_sb3_1112_164813.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**1112_164233**（20251112）

- 结果：OMR=0.6065，BMR=0.4856
- logs：[cachesim_sb3_1112_164233.log](cachesim_sb3_1112_164233.log) / [ac_sb3_1112_164233.log](ac_sb3_1112_164233.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**1112_163452**（20251112）

- 结果：OMR=0.6071，BMR=0.4860
- logs：[cachesim_sb3_1112_163452.log](cachesim_sb3_1112_163452.log) / [ac_sb3_1112_163452.log](ac_sb3_1112_163452.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**1112_162428**（20251112）

- 结果：OMR=0.6066，BMR=0.4855
- logs：[cachesim_sb3_1112_162428.log](cachesim_sb3_1112_162428.log) / [ac_sb3_1112_162428.log](ac_sb3_1112_162428.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**1112_153403**（20251112）

- 结果：OMR=0.6067，BMR=0.4859
- logs：[cachesim_sb3_1112_153403.log](cachesim_sb3_1112_153403.log) / [ac_sb3_1112_153403.log](ac_sb3_1112_153403.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**1112_152834**（20251112）

- 结果：OMR=0.6066，BMR=0.4858
- logs：[cachesim_sb3_1112_152834.log](cachesim_sb3_1112_152834.log) / [ac_sb3_1112_152834.log](ac_sb3_1112_152834.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**1112_152205**（20251112）

- 结果：OMR=0.6073，BMR=0.4866
- logs：[cachesim_sb3_1112_152205.log](cachesim_sb3_1112_152205.log) / [ac_sb3_1112_152205.log](ac_sb3_1112_152205.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**1112_151606**（20251112）

- 结果：OMR=0.6065，BMR=0.4855
- logs：[cachesim_sb3_1112_151606.log](cachesim_sb3_1112_151606.log) / [ac_sb3_1112_151606.log](ac_sb3_1112_151606.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**1112_150239**（20251112）

- 结果：OMR=0.6072，BMR=0.4861
- logs：[cachesim_sb3_1112_150239.log](cachesim_sb3_1112_150239.log) / [ac_sb3_1112_150239.log](ac_sb3_1112_150239.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**1112_111121**（20251112）

- 结果：OMR=0.6067，BMR=0.4859
- logs：[cachesim_sb3_1112_111121.log](cachesim_sb3_1112_111121.log) / [ac_sb3_1112_111121.log](ac_sb3_1112_111121.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**1112_104707**（20251112）

- 结果：OMR=0.6070，BMR=0.4859
- logs：[cachesim_sb3_1112_104707.log](cachesim_sb3_1112_104707.log) / [ac_sb3_1112_104707.log](ac_sb3_1112_104707.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto_2.0；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**1112_104205**（20251112）

- 结果：OMR=0.6067，BMR=0.4861
- logs：[cachesim_sb3_1112_104205.log](cachesim_sb3_1112_104205.log) / [ac_sb3_1112_104205.log](ac_sb3_1112_104205.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto_1.0；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**1112_103344**（20251112）

- 结果：OMR=0.6060，BMR=0.4850
- logs：[cachesim_sb3_1112_103344.log](cachesim_sb3_1112_103344.log) / [ac_sb3_1112_103344.log](ac_sb3_1112_103344.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**1112_102230**（20251112）

- 结果：OMR=0.6065，BMR=0.4855
- logs：[cachesim_sb3_1112_102230.log](cachesim_sb3_1112_102230.log) / [ac_sb3_1112_102230.log](ac_sb3_1112_102230.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**1112_093841**（20251112）

- 结果：OMR=0.6070，BMR=0.4856
- logs：[cachesim_sb3_1112_093841.log](cachesim_sb3_1112_093841.log) / [ac_sb3_1112_093841.log](ac_sb3_1112_093841.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**1112_093143**（20251112）

- 结果：OMR=0.6070，BMR=0.4862
- logs：[cachesim_sb3_1112_093143.log](cachesim_sb3_1112_093143.log) / [ac_sb3_1112_093143.log](ac_sb3_1112_093143.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**1112_092240**（20251112）

- 结果：OMR=0.6068，BMR=0.4858
- logs：[cachesim_sb3_1112_092240.log](cachesim_sb3_1112_092240.log) / [ac_sb3_1112_092240.log](ac_sb3_1112_092240.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto_1.5；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**1112_091649**（20251112）

- 结果：OMR=0.6069，BMR=0.4858
- logs：[cachesim_sb3_1112_091649.log](cachesim_sb3_1112_091649.log) / [ac_sb3_1112_091649.log](ac_sb3_1112_091649.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto_2.0；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**1111_232759**（20251111）

- 结果：OMR=0.6069，BMR=0.4859
- logs：[cachesim_sb3_1111_232759.log](cachesim_sb3_1111_232759.log) / [ac_sb3_1111_232759.log](ac_sb3_1111_232759.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**1111_225744**（20251111）

- 结果：OMR=0.6070，BMR=0.4860
- logs：[cachesim_sb3_1111_225744.log](cachesim_sb3_1111_225744.log) / [ac_sb3_1111_225744.log](ac_sb3_1111_225744.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto_3.0；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**1111_173233**（20251111）

- 结果：OMR=0.6071，BMR=0.4861
- logs：[cachesim_sb3_1111_173233.log](cachesim_sb3_1111_173233.log) / [ac_sb3_1111_173233.log](ac_sb3_1111_173233.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**1111_110801**（20251111）

- 结果：OMR=0.6071，BMR=0.4860
- logs：[cachesim_sb3_1111_110801.log](cachesim_sb3_1111_110801.log) / [ac_sb3_1111_110801.log](ac_sb3_1111_110801.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto_1.0；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**1111_105220**（20251111）

- 结果：OMR=0.6068，BMR=0.4862
- logs：[cachesim_sb3_1111_105220.log](cachesim_sb3_1111_105220.log) / [ac_sb3_1111_105220.log](ac_sb3_1111_105220.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto_0.2；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**1111_104721**（20251111）

- 结果：OMR=0.6067，BMR=0.4860
- logs：[cachesim_sb3_1111_104721.log](cachesim_sb3_1111_104721.log) / [ac_sb3_1111_104721.log](ac_sb3_1111_104721.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto_0.5；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**1111_093620**（20251111）

- 结果：OMR=0.6065，BMR=0.4864
- logs：[cachesim_sb3_1111_093620.log](cachesim_sb3_1111_093620.log) / [ac_sb3_1111_093620.log](ac_sb3_1111_093620.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**1111_092603**（20251111）

- 结果：OMR=0.6062，BMR=0.4854
- logs：[cachesim_sb3_1111_092603.log](cachesim_sb3_1111_092603.log) / [ac_sb3_1111_092603.log](ac_sb3_1111_092603.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**1111_022525**（20251111）

- 结果：OMR=0.6069，BMR=0.4860
- logs：[cachesim_sb3_1111_022525.log](cachesim_sb3_1111_022525.log) / [ac_sb3_1111_022525.log](ac_sb3_1111_022525.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：batch=32；lr=0.0001；ent=0.02；state=26；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)

**1111_021920**（20251111）

- 结果：OMR=0.6247，BMR=0.5123
- logs：[cachesim_sb3_1111_021920.log](cachesim_sb3_1111_021920.log) / [ac_sb3_1111_021920.log](ac_sb3_1111_021920.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：batch=256；lr=0.0003；gamma=0.99
 - - policy_delay: 2 # previous/SB3 default 2
 - - policy.class: TD3Policy
 - - policy.net_arch: [256, 256]
 - - target_policy_noise: 0.2 # SB3 default 0.2 (env-overridable)

**1111_021301**（20251111）

- 结果：OMR=0.6069，BMR=0.4857
- logs：[cachesim_sb3_1111_021301.log](cachesim_sb3_1111_021301.log) / [ac_sb3_1111_021301.log](ac_sb3_1111_021301.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000

**1110_234753**（20251110）

- 结果：OMR=0.6089，BMR=0.4856
- logs：[cachesim_sb3_1110_234753.log](cachesim_sb3_1110_234753.log) / [ac_sb3_1110_234753.log](ac_sb3_1110_234753.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=TD3；batch=256；lr=0.0003；gamma=0.99；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: TD3 (off-policy)
 - - policy_delay: 2 # previous/SB3 default 2
 - - target_policy_noise: 0.2 # SB3 default 0.2 (env-overridable)

**1110_233455**（20251110）

- 结果：OMR=0.6069，BMR=0.4859
- logs：[cachesim_sb3_1110_233455.log](cachesim_sb3_1110_233455.log) / [ac_sb3_1110_233455.log](ac_sb3_1110_233455.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**1110_232815**（20251110）

- 结果：OMR=0.6067，BMR=0.4858
- logs：[cachesim_sb3_1110_232815.log](cachesim_sb3_1110_232815.log) / [ac_sb3_1110_232815.log](ac_sb3_1110_232815.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU


<!-- ROOT_LOGS_END -->

#### 逐 sweep 细表

**next_wiki_bootstrap_nosem_3m_20260129_184204**（来源：sweeps/next_wiki_bootstrap_nosem_3m_20260129_184204/results.csv）

通用配置：SAC log1p=1 norm=1 signs=1；表内 `cfg` 仅列差异
| idx | n | OMR | BMR | cfg |
| ---: | ---: | ---: | ---: | --- |
| 1 | 1 | NA | NA | cpd=0 irt=0 int=200 temp=1.3 scale=0.5 |
| 2 | 1 | NA | NA | cpd=0 irt=0 int=50 scale=1.0 |
| 3 | 1 | NA | NA | cpd=1 irt=1 int=200 temp=1.3 scale=0.5 |

**next_wiki_bootstrap_req1_3m_20260129_184646**（来源：sweeps/next_wiki_bootstrap_req1_3m_20260129_184646/results.csv）

通用配置：SAC log1p=1 norm=1 signs=1 cpd=0 irt=0；表内 `cfg` 仅列差异（softmax/linear 或 cpd/irt）

| idx | n | OMR | BMR | cfg |
| ---: | ---: | ---: | ---: | --- |
| 1 | 1 | 0.599245 | 0.482586 | softmax int=200 temp=1.3 scale=0.5 |
| 2 | 1 | 0.640042 | 0.571288 | linear int=50 scale=1.0 |
| 3 | 1 | 0.595814 | 0.475283 | softmax cpd=1 irt=1 int=200 temp=1.3 scale=0.5 |

**modes2_mrw0**（来源：sweeps/modes2_mrw0_0130_112123/combined_summary.csv）

通用配置：SAC score=linear log1p=1 norm=1 signs=1 softmax irt=0 int=200 temp=1.3 scale=0.5 mrw=0.0；表内 `cfg` 仅列差异
| idx | n | OMR | BMR | cfg |
| ---: | ---: | ---: | ---: | --- |
| 1 | 1 | 0.595771 | 0.475249 | cpd=1 |
| 2 | 1 | 0.599045 | 0.482186 | cpd=0 |


配置来源：scripts/sweep_configs_1063_*.txt（此处不再展开逐行配置；训练超参纳入；IPC/同步参数不纳入本汇总）

训练超参（仅统计在 scripts/sweep_configs_1063_*.txt 中显式设置的项）：
- A2C：A2C_N_STEPS={128,256}；A2C_LEARNING_RATE=3e-4；A2C_ENT_COEF={0.0,0.01,0.05}
- PPO：PPO_N_STEPS={1024,2048}；PPO_BATCH_SIZE=256；PPO_LEARNING_RATE=3e-4；PPO_ENT_COEF={0.0,0.01,0.02,0.05}；PPO_GAMMA=0.99
- TD3：TD3_BUFFER_SIZE={50000,100000}；TD3_BATCH_SIZE=256；TD3_LEARNING_RATE={3e-4,5e-4,1e-3}；TD3_TRAIN_FREQ={2,4,6,8,16}；TD3_GRADIENT_STEPS={1,2}；TD3_LEARNING_STARTS={500,800,1000,3000}

**1063_wide_r2_20251226_112012**（来源：sweeps/1063_wide_r2_20251226_112012/results.csv）

通用配置：norm=1；表内 `cfg` 仅列差异
| idx | n | OMR | BMR | cfg |
| ---: | ---: | ---: | ---: | --- |
| 1 | 1 | 0.373094 | 0.329602 | SAC int=120 temp=2.0 scale=0.8 |
| 2 | 1 | 0.372945 | 0.329710 | SAC int=200 temp=1.8 scale=0.7 |
| 3 | 1 | 0.372924 | 0.329326 | SAC int=50 temp=1.8 scale=0.6 |
| 4 | 1 | 0.373275 | 0.329544 | SAC int=150 temp=1.7 scale=0.7 |
| 5 | 1 | 0.373267 | 0.329685 | SAC int=200 temp=1.7 scale=0.7 pen=log |
| 6 | 1 | 0.372456 | 0.329438 | SAC int=150 temp=1.6 scale=0.6 |
| 7 | 1 | 0.388751 | 0.378225 | TD3 int=100 temp=1.8 scale=0.8 |
| 8 | 1 | 0.381599 | 0.339771 | TD3 int=200 temp=1.7 scale=0.7 |
| 9 | 1 | 0.372892 | 0.329302 | PPO int=200 temp=1.8 scale=0.7 |
| 10 | 1 | 0.376151 | 0.331411 | PPO int=200 temp=1.6 scale=0.8 |
| 11 | 1 | 0.369881 | 0.327366 | A2C int=200 temp=1.7 scale=0.7 |
| 12 | 1 | 0.373275 | 0.329315 | SAC int=150 temp=2.2 scale=0.9 |
| 13 | 1 | 0.386145 | 0.359657 | SAC cpd=1 int=150 temp=1.5 scale=0.7 |
| 14 | 1 | 0.372855 | 0.329169 | SAC int=200 temp=1.2 scale=0.5 |
| 15 | 1 | 0.652036 | 0.679375 | PPO int=200 temp=1.7 scale=0.7 |
| 16 | 1 | 0.530174 | 0.531909 | TD3 int=150 temp=1.6 scale=0.7 |
| 17 | 1 | 0.374942 | 0.330687 | SAC int=80 temp=1.8 scale=0.6 |
| 18 | 1 | 0.373209 | 0.329403 | PPO int=200 temp=1.7 scale=0.7 |
| 19 | 1 | 0.374000 | 0.329624 | SAC int=80 temp=2.5 scale=1.0 |
| 20 | 1 | 0.652191 | 0.679500 | SAC int=120 temp=1.7 scale=0.8 |
| 21 | 1 | 0.466639 | 0.463453 | SAC irt=1 int=150 temp=1.8 scale=0.7 |
| 22 | 1 | 0.392543 | 0.353529 | PPO cpd=1 int=180 temp=1.6 scale=0.7 |
| 23 | 1 | 0.372945 | 0.329011 | A2C int=120 temp=1.8 scale=0.8 |
| 24 | 1 | 0.371285 | 0.328432 | TD3 int=80 temp=1.9 scale=0.8 |
| 25 | 1 | 0.375993 | 0.331022 | SAC int=50 temp=1.9 scale=0.7 |
| 26 | 1 | 0.373050 | 0.328872 | PPO int=200 temp=1.6 scale=0.7 pen=linear |

**1063_featnorm_r1_20251229_140452**（来源：sweeps/1063_featnorm_r1_20251229_140452/results.csv）

通用配置：—；表内 `cfg` 仅列差异
| idx | n | OMR | BMR | cfg |
| ---: | ---: | ---: | ---: | --- |
| 1 | 1 | 0.633820 | 0.637001 | A2C int=200 temp=1.7 scale=0.7 |
| 2 | 1 | 0.485848 | 0.505248 | A2C int=200 temp=1.7 scale=0.7 |
| 3 | 1 | 0.652433 | 0.679598 | A2C norm=1 int=200 temp=1.7 scale=0.7 |
| 4 | 1 | 0.467842 | 0.465997 | A2C norm=1 int=200 temp=1.7 scale=0.7 |
| 5 | 1 | 0.450303 | 0.439789 | A2C norm=1 int=200 temp=1.7 scale=0.7 |
| 6 | 1 | 0.469176 | 0.469824 | A2C norm=1 int=200 temp=1.7 scale=0.7 |
| 7 | 1 | 0.652720 | 0.679179 | A2C norm=1 int=200 temp=1.7 scale=0.7 |
| 8 | 1 | 0.491394 | 0.526752 | A2C norm=1 int=200 temp=1.7 scale=0.7 |
| 9 | 1 | 0.472854 | 0.473656 | A2C norm=1 int=200 temp=1.2 scale=0.5 |
| 10 | 1 | 0.469095 | 0.473159 | SAC norm=1 int=150 temp=1.7 scale=0.7 |
| 11 | 1 | 0.376843 | 0.352218 | SAC linear norm=1 int=120 scale=1.0 |
| 12 | 1 | 0.652720 | 0.679180 | PPO norm=1 int=200 temp=1.6 scale=0.7 |

**1063_cachefeat_r1_20251231_112906**（来源：sweeps/1063_cachefeat_r1_20251231_112906/results.csv）

通用配置：cacheF=1；表内 `cfg` 仅列差异
| idx | n | OMR | BMR | cfg |
| ---: | ---: | ---: | ---: | --- |
| 1 | 1 | 0.379517 | 0.356160 | SAC linear norm=1 int=120 scale=1.0 |
| 2 | 1 | 0.378243 | 0.353989 | SAC linear norm=1 int=120 scale=0.5 |
| 3 | 1 | 0.379112 | 0.357074 | SAC linear norm=1 int=120 scale=2.0 |
| 4 | 1 | 0.379900 | 0.358781 | SAC linear int=120 scale=1.0 |
| 5 | 1 | 0.467225 | 0.466793 | SAC norm=1 int=150 temp=1.7 scale=0.7 |
| 6 | 1 | 0.468727 | 0.470622 | SAC norm=1 int=150 temp=2.0 scale=0.8 |
| 7 | 1 | 0.464236 | 0.462754 | A2C norm=1 int=200 temp=1.7 scale=0.7 |
| 8 | 1 | 0.444361 | 0.418517 | TD3 norm=1 int=200 temp=1.7 scale=0.7 |
| 9 | 1 | 0.459618 | 0.454761 | PPO norm=1 int=200 temp=1.6 scale=0.7 |
| 10 | 1 | 0.375308 | 0.354051 | SAC linear norm=1 int=120 scale=1.5 |

**1063_kitchensink_r1_20251231_144653**（来源：sweeps/1063_kitchensink_r1_20251231_144653/results.csv）

通用配置：norm=1 cacheF=1 candF=1；表内 `cfg` 仅列差异
| idx | n | OMR | BMR | cfg |
| ---: | ---: | ---: | ---: | --- |
| 1 | 1 | 0.468972 | 0.469540 | A2C int=200 temp=1.7 scale=0.7 |
| 2 | 1 | 0.379669 | 0.353826 | SAC linear int=120 scale=1.0 |
| 3 | 1 | 0.445891 | 0.433795 | TD3 int=200 temp=1.7 scale=0.7 |
| 4 | 1 | 0.453818 | 0.443892 | PPO int=200 temp=1.6 scale=0.7 |
| 5 | 1 | 0.467670 | 0.468028 | SAC int=150 temp=1.7 scale=0.7 |
| 6 | 1 | 0.455666 | 0.450123 | A2C int=200 temp=1.8 scale=0.7 |
| 7 | 1 | 0.376640 | 0.353541 | SAC linear int=120 scale=1.5 |

**1063_core_rl_nowait_20260106_215817**（来源：sweeps/1063_core_rl_nowait_20260106_215817/results.csv）

通用配置：—；表内 `cfg` 仅列差异
| idx | n | OMR | BMR | cfg |
| ---: | ---: | ---: | ---: | --- |
| 1 | 0 | NA | NA | SAC int=200 temp=1.0 scale=1.0 |
| 2 | 1 | 0.395668 | 0.369375 | SAC int=200 temp=0.3 scale=1.0 |
| 3 | 1 | 0.465066 | 0.503445 | SAC int=200 temp=2.0 scale=1.0 |
| 4 | 1 | 0.400905 | 0.378229 | SAC int=200 temp=1.0 scale=3.0 |
| 5 | 1 | 0.365522 | 0.349236 | SAC linear int=200 scale=1.0 |
| 6 | 1 | 0.369295 | 0.352791 | SAC linear int=200 scale=3.0 |
| 7 | 1 | 0.356964 | 0.346599 | SAC linear int=50 scale=1.0 |
| 8 | 1 | 0.376490 | 0.354094 | SAC linear int=1000 scale=1.0 |
| 9 | 1 | 0.563725 | 0.599789 | TD3 linear int=200 scale=1.0 |

**1063_linear_only_20260108_115104**（来源：sweeps/1063_linear_only_20260108_115104/results.csv）

| idx | n | OMR | BMR | cfg |
| ---: | ---: | ---: | ---: | --- |
| 1 | 1 | 0.356387 | 0.346686 | SAC linear int=50 scale=1.0 |

**1063_mlp_vs_linear_20260107_180946**（来源：sweeps/1063_mlp_vs_linear_20260107_180946/results.csv）

通用配置：SAC linear int=50 scale=1.0；表内 `cfg` 仅列差异
| idx | n | OMR | BMR | cfg |
| ---: | ---: | ---: | ---: | --- |
| 1 | 0 | NA | NA | — |
| 2 | 1 | 0.365308 | 0.357196 | mlp16 |

**1063_quick_r1_20251225_110318**（来源：sweeps/1063_quick_r1_20251225_110318/results.csv）

通用配置：norm=1；表内 `cfg` 仅列差异
| idx | n | OMR | BMR | cfg |
| ---: | ---: | ---: | ---: | --- |
| 1 | 1 | 0.372756 | 0.329203 | SAC int=200 temp=1.3 scale=0.5 |
| 2 | 1 | 0.373110 | 0.329374 | SAC int=150 temp=1.5 scale=0.65 |
| 3 | 1 | 0.373740 | 0.329960 | SAC int=200 temp=1.3 scale=0.7 cacheF=1 candF=1 |
| 4 | 1 | 0.385733 | 0.352876 | TD3 int=200 temp=1.3 scale=0.5 |
| 5 | 1 | 0.371105 | 0.328755 | PPO int=200 temp=1.3 scale=0.5 |
| 6 | 1 | 0.380236 | 0.335224 | A2C int=200 temp=1.3 scale=0.5 |

**1063_reward_penalty_r1_20251225_163358**（来源：sweeps/1063_reward_penalty_r1_20251225_163358/results.csv）

通用配置：norm=1 scale=0.6；表内 `cfg` 仅列差异
| idx | n | OMR | BMR | cfg |
| ---: | ---: | ---: | ---: | --- |
| 1 | 1 | 0.373035 | 0.329552 | SAC int=150 temp=1.6 |
| 2 | 1 | 0.373006 | 0.329375 | SAC int=200 temp=1.4 pen=reciprocal |
| 3 | 1 | 0.373125 | 0.329642 | SAC int=200 temp=1.5 |
| 4 | 1 | 0.371939 | 0.328724 | PPO int=200 temp=1.6 |
| 5 | 1 | 0.377811 | 0.362393 | TD3 int=150 temp=1.6 |
| 6 | 1 | 0.372603 | 0.329275 | SAC int=150 temp=1.4 |

**sweep_20260106_153622**（来源：sweeps/sweep_20260106_153622/results.csv）

通用配置：—；表内 `cfg` 仅列差异
| idx | n | OMR | BMR | cfg |
| ---: | ---: | ---: | ---: | --- |
| 1 | 0 | NA | NA | SAC pen=reciprocal |
| 2 | 1 | 0.440277 | 0.449225 | SAC pen=log |
| 3 | 1 | 0.440403 | 0.449142 | SAC pen=survival |
| 4 | 1 | 0.439434 | 0.448846 | SAC pen=reciprocal |
| 5 | 1 | 0.438666 | 0.446005 | SAC pen=log |
| 6 | 1 | 0.437083 | 0.443746 | SAC pen=survival |
| 7 | 1 | 0.439032 | 0.448081 | SAC pen=reciprocal |
| 8 | 1 | 0.439307 | 0.448529 | SAC pen=reciprocal |
| 9 | 1 | 0.468854 | 0.483732 | TD3 pen=reciprocal |

**modes2_mrw0**（来源：sweeps/modes2_mrw0_0130_112123/combined_summary.csv）

通用配置：SAC score=linear log1p=1 norm=1 signs=1 softmax irt=0 int=200 temp=1.3 scale=0.5 mrw=0.0；表内 `cfg` 仅列差异
| idx | n | OMR | BMR | cfg |
| ---: | ---: | ---: | ---: | --- |
| 1 | 1 | 0.405658 | 0.368856 | cpd=1 |
| 2 | 1 | 0.373018 | 0.329636 | cpd=0 |

**modes3_batch**（来源：sweeps/modes3_batch_0130_021623/combined_summary.csv）

通用配置：SAC score=linear log1p=1 norm=1 signs=1 softmax int=200 temp=1.3 scale=0.5；表内 `cfg` 仅列差异
| idx | n | OMR | BMR | cfg |
| ---: | ---: | ---: | ---: | --- |
| 1 | 1 | 0.404905 | 0.367867 | cpd=1 irt=1 |
| 2 | 1 | 0.466149 | 0.463402 | cpd=0 irt=1 |
| 3 | 1 | 0.373167 | 0.329636 | cpd=0 irt=0 |

## Trace: data/TencentCBS/1063.oracleGeneral.zst

<!-- ROOT_LOGS_BEGIN -->

### 根目录日志（19 条，req>=3000000）

#### req=360960512（1 条）

| date | run | OMR | BMR | cfg | ref | note |
| ---: | --- | ---: | ---: | --- | --- | --- |
| 20251209 | 1209_010657 | 0.2756 | 0.2486 | log1p=1 norm=1 cpd=1 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1209_010657.log) |  |

##### 逐日志明细（req=360960512）

**1209_010657**（20251209）

- 结果：OMR=0.2756，BMR=0.2486
- logs：[cachesim_sb3_1209_010657.log](cachesim_sb3_1209_010657.log)
- cachesim：req=360960512；int=200；mr_w=1.000 bmr_w=0.000；log1p=1；recip=0；norm=1；irt=0；cpd=1；cacheF=0；candF=0；state=0->2
 - [LOH INIT] Wait mode: default (BLOCKED)
 - [LOH INIT] Size data structure: SIZE_BUCKETS (全量分桶)

#### req=3000000（18 条）

| date | run | OMR | BMR | cfg | ref | note |
| ---: | --- | ---: | ---: | --- | --- | --- |
| 20260202 | 0202_default16_norm1_ab5_mw05_1063 | 0.390506 | 0.350576 | SAC softmax log1p=1 norm=1 cpd=1 irt=0 int=250 bound=5 scale=1 temp=1 ema=0.9 clip=1 rmode=delta rscale=10 mrw=0.5 tf=16 gs=1 | [cs](cachesim_sb3_0202_default16_norm1_ab5_mw05_1063.log) [ac](ac_sb3_0202_default16_norm1_ab5_mw05_1063.log) | 默认训练频率；build 开启 cacheF/candF/hitmiss/avgtopk |
| 20260202 | 0202_default16_norm1_ab1_mw10_1063 | 0.402147 | 0.364733 | SAC softmax log1p=1 norm=1 cpd=1 irt=0 int=250 bound=1 scale=1 temp=1 ema=0.9 clip=1 rmode=delta rscale=10 mrw=1.0 tf=16 gs=1 | [cs](cachesim_sb3_0202_default16_norm1_ab1_mw10_1063.log) [ac](ac_sb3_0202_default16_norm1_ab1_mw10_1063.log) | 默认训练频率；build 开启 cacheF/candF/hitmiss/avgtopk |
| 20260202 | 0202_delta_softmax_ema_1063 | 0.370991 | 0.332388 | SAC softmax log1p=1 norm=1 cpd=1 irt=0 int=250 bound=5 scale=1 temp=1 ema=0.9 clip=1 rmode=delta rscale=10 tf=1 gs=1 | [cs](cachesim_sb3_0202_delta_softmax_ema_1063.log) [ac](ac_sb3_0202_delta_softmax_ema_1063.log) | 非默认训练频率（tf=1 ls=1000） |
| 20260202 | 0202_delta_softmax_ema_norm_1063 | 0.373982 | 0.334880 | SAC softmax log1p=1 norm=1 cpd=1 irt=0 int=250 bound=5 scale=1 temp=1 ema=0.9 clip=1 rmode=delta rscale=1 tf=1 gs=1 | [cs](cachesim_sb3_0202_delta_softmax_ema_norm_1063.log) [ac](ac_sb3_0202_delta_softmax_ema_norm_1063.log) | 非默认训练频率（tf=1 ls=1000） |
| 20260202 | 0202_fixdims_compound_delta_as12_t03_ema_riu250_1063 | 0.388787 | 0.349349 | SAC softmax log1p=1 norm=0 cpd=1 irt=0 int=250 bound=1 scale=12 temp=0.3 ema=0.9 clip=1 rmode=delta rscale=10 tf=16 gs=1 | [cs](cachesim_sb3_0202_fixdims_compound_delta_as12_t03_ema_riu250_1063.log) [ac](ac_sb3_0202_fixdims_compound_delta_as12_t03_ema_riu250_1063.log) | fixdims + norm=0 |
| 20260202 | 0202_fixdims_compound_delta_softmax_ema_riu125_1063 | 0.388929 | 0.348748 | SAC softmax log1p=1 norm=0 cpd=1 irt=0 int=125 bound=1 scale=1 temp=1 ema=0.9 clip=1 rmode=delta rscale=10 tf=16 gs=1 | [cs](cachesim_sb3_0202_fixdims_compound_delta_softmax_ema_riu125_1063.log) [ac](ac_sb3_0202_fixdims_compound_delta_softmax_ema_riu125_1063.log) | fixdims + norm=0 |
| 20260202 | 0202_fixdims_compound_delta_softmax_ema_riu500_1063 | 0.387517 | 0.347069 | SAC softmax log1p=1 norm=0 cpd=1 irt=0 int=500 bound=1 scale=1 temp=1 ema=0.9 clip=1 rmode=delta rscale=10 tf=16 gs=1 | [cs](cachesim_sb3_0202_fixdims_compound_delta_softmax_ema_riu500_1063.log) [ac](ac_sb3_0202_fixdims_compound_delta_softmax_ema_riu500_1063.log) | fixdims + norm=0 |
| 20260202 | 0202_fixdims_compound_delta_softmax_ema_riu1000_1063 | 0.388983 | 0.348513 | SAC softmax log1p=1 norm=0 cpd=1 irt=0 int=1000 bound=1 scale=1 temp=1 ema=0.9 clip=1 rmode=delta rscale=10 tf=16 gs=1 | [cs](cachesim_sb3_0202_fixdims_compound_delta_softmax_ema_riu1000_1063.log) [ac](ac_sb3_0202_fixdims_compound_delta_softmax_ema_riu1000_1063.log) | fixdims + norm=0 |
| 20260202 | 0202_delta_softmax_ema_riu500_1063 | 0.428394 | 0.398577 | SAC softmax log1p=0 norm=0 cpd=0 irt=1 int=500 bound=1 scale=1 temp=1 ema=0.9 clip=1 rmode=delta rscale=10 tf=16 gs=1 | [cs](cachesim_sb3_0202_delta_softmax_ema_riu500_1063.log) [ac](ac_sb3_0202_delta_softmax_ema_riu500_1063.log) | irt=1 + 无 transforms；state=134/134 |
| 20260202 | 0202_delta_1063 | 0.372395 | 0.344350 | SAC softmax log1p=1 norm=1 cpd=1 irt=0 int=200 bound=5 scale=1 temp=0.3 ema=0 clip=0 rmode=delta rscale=10 tf=1 gs=1 | [cs](cachesim_sb3_0202_delta_1063.log) [ac](ac_sb3_0202_delta_1063.log) | 非默认训练频率（tf=1 ls=1000） |
| 20260202 | 0202_abs_1063 | 0.403911 | 0.377714 | SAC softmax log1p=1 norm=1 cpd=1 irt=0 int=200 bound=5 scale=1 temp=0.3 ema=0 clip=0 rmode=absolute rscale=10 tf=1 gs=1 | [cs](cachesim_sb3_0202_abs_1063.log) [ac](ac_sb3_0202_abs_1063.log) | 非默认训练频率（tf=1 ls=1000） |
| 20260202 | 0202_3m_nosoftmax_tf1_gs1_ls1k | 0.392134 | 0.361351 | SAC linear bound=5 scale=1 temp=0.3 ema=0 clip=0 rmode=absolute rscale=1 | [cs](cachesim_sb3_0202_3m_nosoftmax_tf1_gs1_ls1k.log) [ac](ac_sb3_0202_3m_nosoftmax_tf1_gs1_ls1k.log) | no-softmax + 更激进训练（tf=1 gs=1 ls=1000） |
| 20260202 | 0202_3m_nosoftmax_ab5_as1 | 0.368934 | 0.346120 | SAC linear bound=5 scale=1 temp=0.3 ema=0 clip=0 rmode=absolute rscale=1 | [cs](cachesim_sb3_0202_3m_nosoftmax_ab5_as1.log) [ac](ac_sb3_0202_3m_nosoftmax_ab5_as1.log) | no-softmax |
| 20260201 | 0201_3m_ab1_as12_t03 | 0.369784 | 0.334838 | SAC softmax bound=1 scale=12 temp=0.3 ema=0 clip=0 rmode=absolute rscale=1 | [cs](cachesim_sb3_0201_3m_ab1_as12_t03.log) [ac](ac_sb3_0201_3m_ab1_as12_t03.log) | sharp softmax |
| 20260130 | 0130_001022 | 0.377418 | 0.344870 | SAC log1p=1 norm=1 cpd=0 irt=1 cacheF=0 candF=0 int=1000 | [cs](cachesim_sb3_0130_001022.log) [ac](ac_sb3_0130_001022.log) |  |
| 20260130 | 0130_000700 | 0.376553 | 0.344642 | SAC log1p=1 norm=1 cpd=0 irt=1 cacheF=0 candF=0 int=1000 | [cs](cachesim_sb3_0130_000700.log) [ac](ac_sb3_0130_000700.log) |  |
| 20251208 | 1208_221200 | 0.9075 | 0.9067 | PPO log1p=1 norm=1 cpd=1 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_221200.log) [ac](ac_sb3_1208_221200.log) |  |
| 20251208 | 1208_103353 | 0.3711 | 0.3308 | PPO cpd=1 irt=0 cacheF=0 candF=0 int=200 | [cs](cachesim_sb3_1208_103353.log) [ac](ac_sb3_1208_103353.log) |  |

##### 逐日志明细（req=3000000）

**0202_default16_norm1_ab5_mw05_1063**（20260202）

- 结果：OMR=0.390506，BMR=0.350576
- logs：[cachesim_sb3_0202_default16_norm1_ab5_mw05_1063.log](cachesim_sb3_0202_default16_norm1_ab5_mw05_1063.log) / [ac_sb3_0202_default16_norm1_ab5_mw05_1063.log](ac_sb3_0202_default16_norm1_ab5_mw05_1063.log)
- cachesim：req=3000000；int=250；mr_w=0.500 bmr_w=0.500；log1p=1；recip=0；norm=1；irt=0；cpd=1；state=50/134
 - [LOH INIT] AvgTopK enabled: TOP4 × 6特征 = 24维
 - [LOH INIT] Wait mode: default (BLOCKED)
 - [LOH INIT] Size data structure: SIZE_BUCKETS (全量分桶)
 - [LOH INIT] feature mode: LOG1P=1, RECIPROCAL=0, NORMALIZE=1
 - [LOH INIT] Score feature mode: USE_IRT=0, USE_COMPOUND=1
 - [LOH INIT] Runtime state dims: HIT_MISS=12, CACHE=6, CAND=18, TOPK=0, AVGTOPK=12, REQUEST=0 -> ACTIVE=50/134
- RL：algo=SAC；train_freq=16；gradient_steps=1；learning_starts=3000；action=softmax(bound=5,temp=1,scale=1,ema=0.9,clip=1)；reward=rmode=delta rscale=10 mrw=0.5

**0202_default16_norm1_ab1_mw10_1063**（20260202）

- 结果：OMR=0.402147，BMR=0.364733
- logs：[cachesim_sb3_0202_default16_norm1_ab1_mw10_1063.log](cachesim_sb3_0202_default16_norm1_ab1_mw10_1063.log) / [ac_sb3_0202_default16_norm1_ab1_mw10_1063.log](ac_sb3_0202_default16_norm1_ab1_mw10_1063.log)
- cachesim：req=3000000；int=250；mr_w=1.000 bmr_w=0.000；log1p=1；recip=0；norm=1；irt=0；cpd=1；state=50/134
 - [LOH INIT] AvgTopK enabled: TOP4 × 6特征 = 24维
 - [LOH INIT] Wait mode: default (BLOCKED)
 - [LOH INIT] Size data structure: SIZE_BUCKETS (全量分桶)
 - [LOH INIT] feature mode: LOG1P=1, RECIPROCAL=0, NORMALIZE=1
 - [LOH INIT] Score feature mode: USE_IRT=0, USE_COMPOUND=1
 - [LOH INIT] Runtime state dims: HIT_MISS=12, CACHE=6, CAND=18, TOPK=0, AVGTOPK=12, REQUEST=0 -> ACTIVE=50/134
- RL：algo=SAC；train_freq=16；gradient_steps=1；learning_starts=3000；action=softmax(bound=1,temp=1,scale=1,ema=0.9,clip=1)；reward=rmode=delta rscale=10 mrw=1.0

**0202_delta_softmax_ema_1063**（20260202）

- 结果：OMR=0.370991，BMR=0.332388
- logs：[cachesim_sb3_0202_delta_softmax_ema_1063.log](cachesim_sb3_0202_delta_softmax_ema_1063.log) / [ac_sb3_0202_delta_softmax_ema_1063.log](ac_sb3_0202_delta_softmax_ema_1063.log)
- cachesim：req=3000000；int=250；mr_w=1.000 bmr_w=0.000；log1p=1；recip=0；norm=1；irt=0；cpd=1；state=50/134
 - [LOH INIT] AvgTopK enabled: TOP4 × 6特征 = 24维
 - [LOH INIT] feature mode: LOG1P=1, RECIPROCAL=0, NORMALIZE=1
 - [LOH INIT] Score feature mode: USE_IRT=0, USE_COMPOUND=1
 - [LOH INIT] Runtime state dims: HIT_MISS=12, CACHE=6, CAND=18, TOPK=0, AVGTOPK=12, REQUEST=0 -> ACTIVE=50/134
- RL：algo=SAC；train_freq=1；gradient_steps=1；learning_starts=1000；action=softmax(bound=5,temp=1,scale=1,ema=0.9,clip=1)；reward=rmode=delta rscale=10

**0202_delta_softmax_ema_norm_1063**（20260202）

- 结果：OMR=0.373982，BMR=0.334880
- logs：[cachesim_sb3_0202_delta_softmax_ema_norm_1063.log](cachesim_sb3_0202_delta_softmax_ema_norm_1063.log) / [ac_sb3_0202_delta_softmax_ema_norm_1063.log](ac_sb3_0202_delta_softmax_ema_norm_1063.log)
- cachesim：req=3000000；int=250；mr_w=1.000 bmr_w=0.000；log1p=1；recip=0；norm=1；irt=0；cpd=1；state=50/134
 - [LOH INIT] AvgTopK enabled: TOP4 × 6特征 = 24维
 - [LOH INIT] feature mode: LOG1P=1, RECIPROCAL=0, NORMALIZE=1
 - [LOH INIT] Score feature mode: USE_IRT=0, USE_COMPOUND=1
 - [LOH INIT] Runtime state dims: HIT_MISS=12, CACHE=6, CAND=18, TOPK=0, AVGTOPK=12, REQUEST=0 -> ACTIVE=50/134
- RL：algo=SAC；train_freq=1；gradient_steps=1；learning_starts=1000；action=softmax(bound=5,temp=1,scale=1,ema=0.9,clip=1)；reward=rmode=delta rscale=1

**0202_fixdims_compound_delta_as12_t03_ema_riu250_1063**（20260202）

- 结果：OMR=0.388787，BMR=0.349349
- logs：[cachesim_sb3_0202_fixdims_compound_delta_as12_t03_ema_riu250_1063.log](cachesim_sb3_0202_fixdims_compound_delta_as12_t03_ema_riu250_1063.log) / [ac_sb3_0202_fixdims_compound_delta_as12_t03_ema_riu250_1063.log](ac_sb3_0202_fixdims_compound_delta_as12_t03_ema_riu250_1063.log)
- cachesim：req=3000000；int=250；mr_w=1.000 bmr_w=0.000；log1p=1；recip=0；norm=0；irt=0；cpd=1；state=50/134
 - [LOH INIT] AvgTopK enabled: TOP4 × 6特征 = 24维
 - [LOH INIT] feature mode: LOG1P=1, RECIPROCAL=0, NORMALIZE=0
 - [LOH INIT] Score feature mode: USE_IRT=0, USE_COMPOUND=1
- RL：algo=SAC；train_freq=16；gradient_steps=1；learning_starts=3000；action=softmax(bound=1,temp=0.3,scale=12,ema=0.9,clip=1)；reward=rmode=delta rscale=10

**0202_fixdims_compound_delta_softmax_ema_riu125_1063**（20260202）

- 结果：OMR=0.388929，BMR=0.348748
- logs：[cachesim_sb3_0202_fixdims_compound_delta_softmax_ema_riu125_1063.log](cachesim_sb3_0202_fixdims_compound_delta_softmax_ema_riu125_1063.log) / [ac_sb3_0202_fixdims_compound_delta_softmax_ema_riu125_1063.log](ac_sb3_0202_fixdims_compound_delta_softmax_ema_riu125_1063.log)
- cachesim：req=3000000；int=125；mr_w=1.000 bmr_w=0.000；log1p=1；recip=0；norm=0；irt=0；cpd=1；state=50/134
 - [LOH INIT] AvgTopK enabled: TOP4 × 6特征 = 24维
 - [LOH INIT] feature mode: LOG1P=1, RECIPROCAL=0, NORMALIZE=0
 - [LOH INIT] Score feature mode: USE_IRT=0, USE_COMPOUND=1
- RL：algo=SAC；train_freq=16；gradient_steps=1；learning_starts=3000；action=softmax(bound=1,temp=1,scale=1,ema=0.9,clip=1)；reward=rmode=delta rscale=10

**0202_fixdims_compound_delta_softmax_ema_riu500_1063**（20260202）

- 结果：OMR=0.387517，BMR=0.347069
- logs：[cachesim_sb3_0202_fixdims_compound_delta_softmax_ema_riu500_1063.log](cachesim_sb3_0202_fixdims_compound_delta_softmax_ema_riu500_1063.log) / [ac_sb3_0202_fixdims_compound_delta_softmax_ema_riu500_1063.log](ac_sb3_0202_fixdims_compound_delta_softmax_ema_riu500_1063.log)
- cachesim：req=3000000；int=500；mr_w=1.000 bmr_w=0.000；log1p=1；recip=0；norm=0；irt=0；cpd=1；state=50/134
 - [LOH INIT] AvgTopK enabled: TOP4 × 6特征 = 24维
 - [LOH INIT] feature mode: LOG1P=1, RECIPROCAL=0, NORMALIZE=0
 - [LOH INIT] Score feature mode: USE_IRT=0, USE_COMPOUND=1
- RL：algo=SAC；train_freq=16；gradient_steps=1；learning_starts=3000；action=softmax(bound=1,temp=1,scale=1,ema=0.9,clip=1)；reward=rmode=delta rscale=10

**0202_fixdims_compound_delta_softmax_ema_riu1000_1063**（20260202）

- 结果：OMR=0.388983，BMR=0.348513
- logs：[cachesim_sb3_0202_fixdims_compound_delta_softmax_ema_riu1000_1063.log](cachesim_sb3_0202_fixdims_compound_delta_softmax_ema_riu1000_1063.log) / [ac_sb3_0202_fixdims_compound_delta_softmax_ema_riu1000_1063.log](ac_sb3_0202_fixdims_compound_delta_softmax_ema_riu1000_1063.log)
- cachesim：req=3000000；int=1000；mr_w=1.000 bmr_w=0.000；log1p=1；recip=0；norm=0；irt=0；cpd=1；state=50/134
 - [LOH INIT] AvgTopK enabled: TOP4 × 6特征 = 24维
 - [LOH INIT] feature mode: LOG1P=1, RECIPROCAL=0, NORMALIZE=0
 - [LOH INIT] Score feature mode: USE_IRT=0, USE_COMPOUND=1
- RL：algo=SAC；train_freq=16；gradient_steps=1；learning_starts=3000；action=softmax(bound=1,temp=1,scale=1,ema=0.9,clip=1)；reward=rmode=delta rscale=10

**0202_delta_softmax_ema_riu500_1063**（20260202）

- 结果：OMR=0.428394，BMR=0.398577
- logs：[cachesim_sb3_0202_delta_softmax_ema_riu500_1063.log](cachesim_sb3_0202_delta_softmax_ema_riu500_1063.log) / [ac_sb3_0202_delta_softmax_ema_riu500_1063.log](ac_sb3_0202_delta_softmax_ema_riu500_1063.log)
- cachesim：req=3000000；int=500；mr_w=1.000 bmr_w=0.000；log1p=0；recip=0；norm=0；irt=1；cpd=0；state=134/134
 - [LOH INIT] feature mode: LOG1P=0, RECIPROCAL=0, NORMALIZE=0
 - [LOH INIT] Score feature mode: USE_IRT=1, USE_COMPOUND=0
 - [LOH INIT] Runtime state dims: HIT_MISS=12, CACHE=6, CAND=18, TOPK=0, AVGTOPK=12, REQUEST=0 -> ACTIVE=134/134
- RL：algo=SAC；train_freq=16；gradient_steps=1；learning_starts=3000；action=softmax(bound=1,temp=1,scale=1,ema=0.9,clip=1)；reward=rmode=delta rscale=10

**0202_delta_1063**（20260202）

- 结果：OMR=0.372395，BMR=0.344350
- logs：[cachesim_sb3_0202_delta_1063.log](cachesim_sb3_0202_delta_1063.log) / [ac_sb3_0202_delta_1063.log](ac_sb3_0202_delta_1063.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000；log1p=1；recip=0；norm=1；irt=0；cpd=1；state=50/134
 - [LOH INIT] AvgTopK enabled: TOP4 × 6特征 = 24维
 - [LOH INIT] feature mode: LOG1P=1, RECIPROCAL=0, NORMALIZE=1
 - [LOH INIT] Score feature mode: USE_IRT=0, USE_COMPOUND=1
 - [LOH INIT] Runtime state dims: HIT_MISS=12, CACHE=6, CAND=18, TOPK=0, AVGTOPK=12, REQUEST=0 -> ACTIVE=50/134
- RL：algo=SAC；train_freq=1；gradient_steps=1；learning_starts=1000；action=softmax(bound=5,temp=0.3,scale=1,ema=0,clip=0)；reward=rmode=delta rscale=10

**0202_abs_1063**（20260202）

- 结果：OMR=0.403911，BMR=0.377714
- logs：[cachesim_sb3_0202_abs_1063.log](cachesim_sb3_0202_abs_1063.log) / [ac_sb3_0202_abs_1063.log](ac_sb3_0202_abs_1063.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000；log1p=1；recip=0；norm=1；irt=0；cpd=1；state=50/134
 - [LOH INIT] AvgTopK enabled: TOP4 × 6特征 = 24维
 - [LOH INIT] feature mode: LOG1P=1, RECIPROCAL=0, NORMALIZE=1
 - [LOH INIT] Score feature mode: USE_IRT=0, USE_COMPOUND=1
 - [LOH INIT] Runtime state dims: HIT_MISS=12, CACHE=6, CAND=18, TOPK=0, AVGTOPK=12, REQUEST=0 -> ACTIVE=50/134
- RL：algo=SAC；train_freq=1；gradient_steps=1；learning_starts=1000；action=softmax(bound=5,temp=0.3,scale=1,ema=0,clip=0)；reward=rmode=absolute rscale=10

**0202_3m_nosoftmax_tf1_gs1_ls1k**（20260202）

- 结果：OMR=0.392134，BMR=0.361351
- logs：[cachesim_sb3_0202_3m_nosoftmax_tf1_gs1_ls1k.log](cachesim_sb3_0202_3m_nosoftmax_tf1_gs1_ls1k.log) / [ac_sb3_0202_3m_nosoftmax_tf1_gs1_ls1k.log](ac_sb3_0202_3m_nosoftmax_tf1_gs1_ls1k.log)
- cachesim：req=3000000；int=250；mr_w=1.000 bmr_w=0.000；log1p=1；recip=0；norm=1；irt=0；cpd=1；state=50/134
 - [LOH INIT] AvgTopK enabled: TOP4 × 6特征 = 24维
 - [LOH INIT] Wait mode: default (BLOCKED)
 - [LOH INIT] Size data structure: SIZE_BUCKETS (全量分桶)
 - [LOH INIT] feature mode: LOG1P=1, RECIPROCAL=0, NORMALIZE=1
 - [LOH INIT] Score feature mode: USE_IRT=0, USE_COMPOUND=1
 - [LOH INIT] Runtime state dims: HIT_MISS=12, CACHE=6, CAND=18, TOPK=0, AVGTOPK=12, REQUEST=0 -> ACTIVE=50/134
- RL：algo=SAC；train_freq=1；gradient_steps=1；learning_starts=1000；action=linear(bound=5,temp=0.3,scale=1,ema=0,clip=0)；reward=rmode=absolute rscale=1

**0202_3m_nosoftmax_ab5_as1**（20260202）

- 结果：OMR=0.368934，BMR=0.346120
- logs：[cachesim_sb3_0202_3m_nosoftmax_ab5_as1.log](cachesim_sb3_0202_3m_nosoftmax_ab5_as1.log) / [ac_sb3_0202_3m_nosoftmax_ab5_as1.log](ac_sb3_0202_3m_nosoftmax_ab5_as1.log)
- cachesim：req=3000000；int=250；mr_w=1.000 bmr_w=0.000；log1p=1；recip=0；norm=1；irt=0；cpd=1；state=50/134
 - [LOH INIT] AvgTopK enabled: TOP4 × 6特征 = 24维
 - [LOH INIT] Wait mode: default (BLOCKED)
 - [LOH INIT] Size data structure: SIZE_BUCKETS (全量分桶)
 - [LOH INIT] feature mode: LOG1P=1, RECIPROCAL=0, NORMALIZE=1
 - [LOH INIT] Score feature mode: USE_IRT=0, USE_COMPOUND=1
 - [LOH INIT] Runtime state dims: HIT_MISS=12, CACHE=6, CAND=18, TOPK=0, AVGTOPK=12, REQUEST=0 -> ACTIVE=50/134
- RL：algo=SAC；train_freq=16；gradient_steps=1；learning_starts=3000；action=linear(bound=5,temp=0.3,scale=1,ema=0,clip=0)；reward=rmode=absolute rscale=1

**0201_3m_ab1_as12_t03**（20260201）

- 结果：OMR=0.369784，BMR=0.334838
- logs：[cachesim_sb3_0201_3m_ab1_as12_t03.log](cachesim_sb3_0201_3m_ab1_as12_t03.log) / [ac_sb3_0201_3m_ab1_as12_t03.log](ac_sb3_0201_3m_ab1_as12_t03.log)
- cachesim：req=3000000；int=250；mr_w=1.000 bmr_w=0.000；log1p=1；recip=0；norm=1；irt=0；cpd=1；state=50/134
 - [LOH INIT] AvgTopK enabled: TOP4 × 6特征 = 24维
 - [LOH INIT] Wait mode: default (BLOCKED)
 - [LOH INIT] Size data structure: SIZE_BUCKETS (全量分桶)
 - [LOH INIT] feature mode: LOG1P=1, RECIPROCAL=0, NORMALIZE=1
 - [LOH INIT] Score feature mode: USE_IRT=0, USE_COMPOUND=1
 - [LOH INIT] Runtime state dims: HIT_MISS=12, CACHE=6, CAND=18, TOPK=0, AVGTOPK=12, REQUEST=0 -> ACTIVE=50/134
- RL：algo=SAC；train_freq=16；gradient_steps=1；learning_starts=3000；action=softmax(bound=1,temp=0.3,scale=12,ema=0,clip=0)；reward=rmode=absolute rscale=1

**0130_001022**（20260130）

- 结果：OMR=0.377418，BMR=0.344870
- logs：[cachesim_sb3_0130_001022.log](cachesim_sb3_0130_001022.log) / [ac_sb3_0130_001022.log](ac_sb3_0130_001022.log)
- cachesim：req=3000000；int=1000；mr_w=1.000 bmr_w=0.000；log1p=1；recip=0；norm=1；irt=1；cpd=0；cacheF=0；candF=0；state=1200->1202
 - [LOH INIT] Wait mode: default (BLOCKED)
 - [LOH INIT] Size data structure: SIZE_BUCKETS (全量分桶)
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**0130_000700**（20260130）

- 结果：OMR=0.376553，BMR=0.344642
- logs：[cachesim_sb3_0130_000700.log](cachesim_sb3_0130_000700.log) / [ac_sb3_0130_000700.log](ac_sb3_0130_000700.log)
- cachesim：req=3000000；int=1000；mr_w=1.000 bmr_w=0.000；log1p=1；recip=0；norm=1；irt=1；cpd=0；cacheF=0；candF=0；state=1200->1202
 - [LOH INIT] Wait mode: default (BLOCKED)
 - [LOH INIT] Size data structure: SIZE_BUCKETS (全量分桶)
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**1208_221200**（20251208）

- 结果：OMR=0.9075，BMR=0.9067
- logs：[cachesim_sb3_1208_221200.log](cachesim_sb3_1208_221200.log) / [ac_sb3_1208_221200.log](ac_sb3_1208_221200.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000；log1p=1；recip=0；norm=1；irt=0；cpd=1；cacheF=0；candF=0；state=0->2
 - [LOH INIT] Wait mode: default (BLOCKED)
 - [LOH INIT] Size data structure: SIZE_BUCKETS (全量分桶)
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)

**1208_103353**（20251208）

- 结果：OMR=0.3711，BMR=0.3308
- logs：[cachesim_sb3_1208_103353.log](cachesim_sb3_1208_103353.log) / [ac_sb3_1208_103353.log](ac_sb3_1208_103353.log)
- cachesim：req=3000000；int=200；mr_w=1.000 bmr_w=0.000；irt=0；cpd=1；cacheF=0；candF=0；state=0->14
 - [LOH INIT] AvgTopK enabled: TOP4 × 6特征 = 24维
- RL：algo=PPO；batch=32；lr=0.0001；gamma=0.99；ent=0.02；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)


<!-- ROOT_LOGS_END -->

### 固定权重（不使用 RL；来自 runs/constant_weight_norl_*）

说明：这类实验不产生根目录的 `cachesim_sb3_*.log/ac_sb3_*.log` 对；日志与汇总 TSV 位于 `runs/constant_weight_norl_*`。更完整的说明见：[LOH_CONSTANT_WEIGHTS_BEST_3M_WIKI2019T_1063.md](LOH_CONSTANT_WEIGHTS_BEST_3M_WIKI2019T_1063.md)

| date | run | OMR | BMR | cfg | ref | note |
| ---: | --- | ---: | ---: | --- | --- | --- |
| 20260131 | constant_weight_norl_v01_20260131_wiki2019t_1063_3m | 0.352518 | 0.320008 | enable_rl=0 fixed_weights=[1,1,1.5,0,0,0] log1p=1 norm=1 signs=1 softmax=1 score=linear irt=1 cpd=0 | [log](runs/constant_weight_norl_v01_20260131_wiki2019t_1063_3m/1063.ora_refine_w_1_1_1.500_0_0_0.log) | refine best（按 OMR/BMR 排序） |
| 20260201 | constant_weight_norl_v012c1_mrw1_20260201_fix_wiki2019t_1063_3m | 0.323619 | 0.316550 | enable_rl=0 fixed_weights=[1,0,2.5,0,0,0] log1p=1 norm=1 signs=1 softmax=1 score=linear irt=0 cpd=1 mrw=1 | [log](runs/constant_weight_norl_v012c1_mrw1_20260201_fix_wiki2019t_1063_3m/1063.ora_refine_w_1_0_2.500_0_0_0.log) | refine best；cachesim 侧 `--eviction-params=miss-ratio-weight=1` |


## Trace: data/WikiCDN/wiki_2016u.oracleGeneral.zst

### Sweeps（CACHESIM_NUM_REQ=3000000）

| date | id | best | OMR | BMR | cfg | ref | note |
| ---: | --- | ---: | ---: | ---: | --- | --- | --- |
| 20260130 | m3 | 1 | 0.349567 | 0.822716 | SAC cpd=1 irt=1 int=200 scale=0.5 temp=1.3 | [cs](sweeps/modes3_batch_0130_021623/combined_summary.csv) |  |
| 20260130 | m2 | 1 | 0.349572 | 0.822682 | SAC cpd=1 irt=0 int=200 scale=0.5 temp=1.3 mrw=0.0 | [cs](sweeps/modes2_mrw0_0130_112123/combined_summary.csv) |  |

#### 逐 sweep 细表

**modes3_batch**（来源：sweeps/modes3_batch_0130_021623/combined_summary.csv）

通用配置：SAC score=linear log1p=1 norm=1 signs=1 softmax int=200 temp=1.3 scale=0.5；表内 `cfg` 仅列差异
| idx | n | OMR | BMR | cfg |
| ---: | ---: | ---: | ---: | --- |
| 1 | 1 | 0.349567 | 0.822716 | cpd=1 irt=1 |
| 2 | 1 | 0.374491 | 0.792119 | cpd=0 irt=1 |
| 3 | 1 | 0.354900 | 0.834167 | cpd=0 irt=0 |

**modes2_mrw0**（来源：sweeps/modes2_mrw0_0130_112123/combined_summary.csv）

通用配置：SAC score=linear log1p=1 norm=1 signs=1 softmax irt=0 int=200 temp=1.3 scale=0.5 mrw=0.0；表内 `cfg` 仅列差异
| idx | n | OMR | BMR | cfg |
| ---: | ---: | ---: | ---: | --- |
| 1 | 1 | 0.349572 | 0.822682 | cpd=1 |
| 2 | 1 | 0.354875 | 0.834181 | cpd=0 |

## Trace: data/Alibaba/4.oracleGeneral.zst

### Sweeps（CACHESIM_NUM_REQ=3000000）

| date | id | best | OMR | BMR | cfg | ref | note |
| ---: | --- | ---: | ---: | ---: | --- | --- | --- |
| 20260130 | m3 | 3 | 0.075504 | 0.096678 | SAC cpd=0 irt=0 int=200 scale=0.5 temp=1.3 | [cs](sweeps/modes3_batch_0130_021623/combined_summary.csv) |  |
| 20260130 | m2 | 2 | 0.075593 | 0.097003 | SAC cpd=0 irt=0 int=200 scale=0.5 temp=1.3 mrw=0.0 | [cs](sweeps/modes2_mrw0_0130_112123/combined_summary.csv) |  |

#### 逐 sweep 细表

**modes3_batch**（来源：sweeps/modes3_batch_0130_021623/combined_summary.csv）

通用配置：SAC score=linear log1p=1 norm=1 signs=1 softmax int=200 temp=1.3 scale=0.5；表内 `cfg` 仅列差异
| idx | n | OMR | BMR | cfg |
| ---: | ---: | ---: | ---: | --- |
| 1 | 1 | 0.078376 | 0.106549 | cpd=1 irt=1 |
| 2 | 1 | 0.240660 | 0.253150 | cpd=0 irt=1 |
| 3 | 1 | 0.075504 | 0.096678 | cpd=0 irt=0 |

**modes2_mrw0**（来源：sweeps/modes2_mrw0_0130_112123/combined_summary.csv）

通用配置：SAC score=linear log1p=1 norm=1 signs=1 softmax irt=0 int=200 temp=1.3 scale=0.5 mrw=0.0；表内 `cfg` 仅列差异
| idx | n | OMR | BMR | cfg |
| ---: | ---: | ---: | ---: | --- |
| 1 | 1 | 0.078385 | 0.106589 | cpd=1 |
| 2 | 1 | 0.075593 | 0.097003 | cpd=0 |

## Trace: data/MetaKV/202401_kv_traces_all_sort.csv.oracleGeneral.zst

### Sweeps（CACHESIM_NUM_REQ=3000000）

| date | id | best | OMR | BMR | cfg | ref | note |
| ---: | --- | ---: | ---: | ---: | --- | --- | --- |
| 20260130 | m3 | 3 | 0.237896 | 0.229392 | SAC cpd=0 irt=0 int=200 scale=0.5 temp=1.3 | [cs](sweeps/modes3_batch_0130_021623/combined_summary.csv) |  |
| 20260130 | m2 | 2 | 0.238511 | 0.228688 | SAC cpd=0 irt=0 int=200 scale=0.5 temp=1.3 mrw=0.0 | [cs](sweeps/modes2_mrw0_0130_112123/combined_summary.csv) |  |

#### 逐 sweep 细表

**modes3_batch**（来源：sweeps/modes3_batch_0130_021623/combined_summary.csv）

通用配置：SAC score=linear log1p=1 norm=1 signs=1 softmax int=200 temp=1.3 scale=0.5；表内 `cfg` 仅列差异
| idx | n | OMR | BMR | cfg |
| ---: | ---: | ---: | ---: | --- |
| 1 | 1 | 0.252792 | 0.245648 | cpd=1 irt=1 |
| 2 | 1 | 0.273809 | 0.243852 | cpd=0 irt=1 |
| 3 | 1 | 0.237896 | 0.229392 | cpd=0 irt=0 |

**modes2_mrw0**（来源：sweeps/modes2_mrw0_0130_112123/combined_summary.csv）

通用配置：SAC score=linear log1p=1 norm=1 signs=1 softmax irt=0 int=200 temp=1.3 scale=0.5 mrw=0.0；表内 `cfg` 仅列差异
| idx | n | OMR | BMR | cfg |
| ---: | ---: | ---: | ---: | --- |
| 1 | 1 | 0.252720 | 0.245458 | cpd=1 |
| 2 | 1 | 0.238511 | 0.228688 | cpd=0 |

## Trace: data/TencentPhoto/tencent_photo1.oracleGeneral.zst

### Sweeps（CACHESIM_NUM_REQ=3000000）

| date | id | best | OMR | BMR | cfg | ref | note |
| ---: | --- | ---: | ---: | ---: | --- | --- | --- |
| 20260130 | m3 | 3 | 0.740252 | 0.763826 | SAC cpd=0 irt=0 int=200 scale=0.5 temp=1.3 | [cs](sweeps/modes3_batch_0130_021623/combined_summary.csv) |  |
| 20260130 | m2 | 2 | 0.740089 | 0.763673 | SAC cpd=0 irt=0 int=200 scale=0.5 temp=1.3 mrw=0.0 | [cs](sweeps/modes2_mrw0_0130_112123/combined_summary.csv) |  |

#### 逐 sweep 细表

**modes3_batch**（来源：sweeps/modes3_batch_0130_021623/combined_summary.csv）

通用配置：SAC score=linear log1p=1 norm=1 signs=1 softmax int=200 temp=1.3 scale=0.5；表内 `cfg` 仅列差异
| idx | n | OMR | BMR | cfg |
| ---: | ---: | ---: | ---: | --- |
| 1 | 1 | 0.742116 | 0.757366 | cpd=1 irt=1 |
| 2 | 1 | 0.754706 | 0.736890 | cpd=0 irt=1 |
| 3 | 1 | 0.740252 | 0.763826 | cpd=0 irt=0 |

**modes2_mrw0**（来源：sweeps/modes2_mrw0_0130_112123/combined_summary.csv）

通用配置：SAC score=linear log1p=1 norm=1 signs=1 softmax irt=0 int=200 temp=1.3 scale=0.5 mrw=0.0；表内 `cfg` 仅列差异
| idx | n | OMR | BMR | cfg |
| ---: | ---: | ---: | ---: | --- |
| 1 | 1 | 0.742121 | 0.757384 | cpd=1 |
| 2 | 1 | 0.740089 | 0.763673 | cpd=0 |
## Trace: test_loh_comprehensive_10k.csv

### Sweeps（CACHESIM_NUM_REQ=3000000）

| date | id | best | OMR | BMR | cfg | ref | note |
| ---: | --- | ---: | ---: | ---: | --- | --- | --- |
| 20251212 | seed | - | NA | NA | seed_focus | [res](sweeps/seedfocus3m_1212_143747/results.csv) | NA |

#### 逐 sweep 细表

**seedfocus3m_1212_143747**（来源：sweeps/seedfocus3m_1212_143747/results.csv）

通用配置：scale=1.0；表内 `cfg` 仅列差异
| idx | n | OMR | BMR | cfg |
| ---: | ---: | ---: | ---: | --- |
| 1 | 0 | NA | NA | TD3 |
| 2 | 0 | NA | NA | TD3 linear |
| 3 | 0 | NA | NA | SAC |
| 4 | 0 | NA | NA | SAC linear |

配置来源：scripts/sweep_configs_seed_focus_3m.txt（此处不再展开逐行配置；训练超参纳入；IPC/同步参数不纳入本汇总）




## Trace: data/lfutest_10m.csv

<!-- ROOT_LOGS_BEGIN -->

### 根目录日志（7 条，req>=3000000）

#### req=10000000（7 条）

| date | run | OMR | BMR | cfg | ref | note |
| ---: | --- | ---: | ---: | --- | --- | --- |
| 20251108 | 1108_025635 | 0.0964 | 0.0984 | SAC int=200 | [cs](cachesim_sb3_1108_025635.log) [ac](ac_sb3_1108_025635.log) |  |
| 20251108 | 1108_025630 | 0.0947 | 0.0979 | TD3 int=200 | [cs](cachesim_sb3_1108_025630.log) [ac](ac_sb3_1108_025630.log) |  |
| 20251105 | 1105_173057 | 0.0954 | 0.0977 | int=200 | [cs](cachesim_sb3_1105_173057.log) [ac](ac_sb3_1105_173057.log) |  |
| 20251104 | 1104_231245 | 0.0956 | 0.0984 | TD3 int=200 | [cs](cachesim_sb3_1104_231245.log) [ac](ac_sb3_1104_231245.log) |  |
| 20251104 | 1104_220437 | 0.0954 | 0.0982 | SAC int=200 | [cs](cachesim_sb3_1104_220437.log) [ac](ac_sb3_1104_220437.log) |  |
| 20251103 | 1103_200736 | 0.0954 | 0.0982 | SAC int=200 | [cs](cachesim_sb3_1103_200736.log) [ac](ac_sb3_1103_200736.log) |  |
| 20251103 | 1103_113829 | 0.0954 | 0.0977 | int=200 | [cs](cachesim_sb3_1103_113829.log) [ac](ac_sb3_1103_113829.log) |  |

##### 逐日志明细（req=10000000）

**1108_025635**（20251108）

- 结果：OMR=0.0964，BMR=0.0984
- logs：[cachesim_sb3_1108_025635.log](cachesim_sb3_1108_025635.log) / [ac_sb3_1108_025635.log](ac_sb3_1108_025635.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**1108_025630**（20251108）

- 结果：OMR=0.0947，BMR=0.0979
- logs：[cachesim_sb3_1108_025630.log](cachesim_sb3_1108_025630.log) / [ac_sb3_1108_025630.log](ac_sb3_1108_025630.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=TD3；batch=256；lr=0.0003；gamma=0.99；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: TD3 (off-policy)
 - - policy_delay: 2 # previous/SB3 default 2
 - - target_policy_noise: 0.2 # SB3 default 0.2 (env-overridable)

**1105_173057**（20251105）

- 结果：OMR=0.0954，BMR=0.0977
- logs：[cachesim_sb3_1105_173057.log](cachesim_sb3_1105_173057.log) / [ac_sb3_1105_173057.log](ac_sb3_1105_173057.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000

**1104_231245**（20251104）

- 结果：OMR=0.0956，BMR=0.0984
- logs：[cachesim_sb3_1104_231245.log](cachesim_sb3_1104_231245.log) / [ac_sb3_1104_231245.log](ac_sb3_1104_231245.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=TD3；batch=256；lr=0.0003；gamma=0.99；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: TD3 (off-policy)
 - - policy.net_arch: [256, 256]

**1104_220437**（20251104）

- 结果：OMR=0.0954，BMR=0.0982
- logs：[cachesim_sb3_1104_220437.log](cachesim_sb3_1104_220437.log) / [ac_sb3_1104_220437.log](ac_sb3_1104_220437.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=5e-05；gamma=0.99；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)
 - - policy.net_arch: [256, 256]
 - - policy.activation_fn: <class 'torch.nn.modules.activation.ReLU'>

**1103_200736**（20251103）

- 结果：OMR=0.0954，BMR=0.0982
- logs：[cachesim_sb3_1103_200736.log](cachesim_sb3_1103_200736.log) / [ac_sb3_1103_200736.log](ac_sb3_1103_200736.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=5e-05；gamma=0.99；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)
 - - policy.net_arch: [256, 256]
 - - policy.activation_fn: <class 'torch.nn.modules.activation.ReLU'>

**1103_113829**（20251103）

- 结果：OMR=0.0954，BMR=0.0977
- logs：[cachesim_sb3_1103_113829.log](cachesim_sb3_1103_113829.log) / [ac_sb3_1103_113829.log](ac_sb3_1103_113829.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：state=26；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)


<!-- ROOT_LOGS_END -->


## Trace: data/lrutest_10m.csv

<!-- ROOT_LOGS_BEGIN -->

### 根目录日志（14 条，req>=3000000）

#### req=10000000（14 条）

| date | run | OMR | BMR | cfg | ref | note |
| ---: | --- | ---: | ---: | --- | --- | --- |
| 20251108 | 1108_025622 | 0.1261 | 0.1288 | SAC int=200 | [cs](cachesim_sb3_1108_025622.log) [ac](ac_sb3_1108_025622.log) |  |
| 20251108 | 1108_025614 | 0.1368 | 0.1390 | TD3 int=200 | [cs](cachesim_sb3_1108_025614.log) [ac](ac_sb3_1108_025614.log) |  |
| 20251105 | 1105_174733 | 0.0875 | 0.0919 | int=200 | [cs](cachesim_sb3_1105_174733.log) [ac](ac_sb3_1105_174733.log) |  |
| 20251104 | 1104_230241 | 0.3624 | 0.3618 | SAC int=200 | [cs](cachesim_sb3_1104_230241.log) [ac](ac_sb3_1104_230241.log) |  |
| 20251104 | 1104_230110 | 0.0907 | 0.0949 | SAC int=200 | [cs](cachesim_sb3_1104_230110.log) [ac](ac_sb3_1104_230110.log) |  |
| 20251104 | 1104_225920 | 0.0904 | 0.0947 | SAC int=200 | [cs](cachesim_sb3_1104_225920.log) [ac](ac_sb3_1104_225920.log) |  |
| 20251104 | 1104_225738 | 0.0908 | 0.0950 | SAC int=200 | [cs](cachesim_sb3_1104_225738.log) [ac](ac_sb3_1104_225738.log) |  |
| 20251104 | 1104_225331 | 0.0914 | 0.0962 | SAC int=200 | [cs](cachesim_sb3_1104_225331.log) [ac](ac_sb3_1104_225331.log) |  |
| 20251103 | 1103_213043 | 0.1379 | 0.1400 | TD3 int=200 | [cs](cachesim_sb3_1103_213043.log) [ac](ac_sb3_1103_213043.log) |  |
| 20251103 | 1103_204120 | 0.1265 | 0.1305 | SAC int=200 | [cs](cachesim_sb3_1103_204120.log) [ac](ac_sb3_1103_204120.log) |  |
| 20251103 | 1103_202052 | 0.1248 | 0.1276 | SAC int=200 | [cs](cachesim_sb3_1103_202052.log) [ac](ac_sb3_1103_202052.log) |  |
| 20251103 | 1103_194355 | 0.1248 | 0.1283 | SAC int=200 | [cs](cachesim_sb3_1103_194355.log) [ac](ac_sb3_1103_194355.log) |  |
| 20251103 | 1103_190008 | 0.0973 | 0.1017 | int=200 | [cs](cachesim_sb3_1103_190008.log) [ac](ac_sb3_1103_190008.log) |  |
| 20251103 | 1103_112912 | 0.0980 | 0.1017 | int=200 | [cs](cachesim_sb3_1103_112912.log) [ac](ac_sb3_1103_112912.log) |  |

##### 逐日志明细（req=10000000）

**1108_025622**（20251108）

- 结果：OMR=0.1261，BMR=0.1288
- logs：[cachesim_sb3_1108_025622.log](cachesim_sb3_1108_025622.log) / [ac_sb3_1108_025622.log](ac_sb3_1108_025622.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=0.0003；gamma=0.99；ent=auto；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)
 - - policy.hidden_layers: [256, 256]
 - - policy.activation_fn: ReLU

**1108_025614**（20251108）

- 结果：OMR=0.1368，BMR=0.1390
- logs：[cachesim_sb3_1108_025614.log](cachesim_sb3_1108_025614.log) / [ac_sb3_1108_025614.log](ac_sb3_1108_025614.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=TD3；batch=256；lr=0.0003；gamma=0.99；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: TD3 (off-policy)
 - - policy_delay: 2 # previous/SB3 default 2
 - - target_policy_noise: 0.2 # SB3 default 0.2 (env-overridable)

**1105_174733**（20251105）

- 结果：OMR=0.0875，BMR=0.0919
- logs：[cachesim_sb3_1105_174733.log](cachesim_sb3_1105_174733.log) / [ac_sb3_1105_174733.log](ac_sb3_1105_174733.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000

**1104_230241**（20251104）

- 结果：OMR=0.3624，BMR=0.3618
- logs：[cachesim_sb3_1104_230241.log](cachesim_sb3_1104_230241.log) / [ac_sb3_1104_230241.log](ac_sb3_1104_230241.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=5e-05；gamma=0.99；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)
 - - policy.net_arch: [256, 256]
 - - policy.activation_fn: <class 'torch.nn.modules.activation.ReLU'>

**1104_230110**（20251104）

- 结果：OMR=0.0907，BMR=0.0949
- logs：[cachesim_sb3_1104_230110.log](cachesim_sb3_1104_230110.log) / [ac_sb3_1104_230110.log](ac_sb3_1104_230110.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=5e-05；gamma=0.99；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)
 - - policy.net_arch: [256, 256]
 - - policy.activation_fn: <class 'torch.nn.modules.activation.ReLU'>

**1104_225920**（20251104）

- 结果：OMR=0.0904，BMR=0.0947
- logs：[cachesim_sb3_1104_225920.log](cachesim_sb3_1104_225920.log) / [ac_sb3_1104_225920.log](ac_sb3_1104_225920.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=5e-05；gamma=0.99；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)
 - - policy.net_arch: [256, 256]
 - - policy.activation_fn: <class 'torch.nn.modules.activation.ReLU'>

**1104_225738**（20251104）

- 结果：OMR=0.0908，BMR=0.0950
- logs：[cachesim_sb3_1104_225738.log](cachesim_sb3_1104_225738.log) / [ac_sb3_1104_225738.log](ac_sb3_1104_225738.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=5e-05；gamma=0.99；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)
 - - policy.net_arch: [256, 256]
 - - policy.activation_fn: <class 'torch.nn.modules.activation.ReLU'>

**1104_225331**（20251104）

- 结果：OMR=0.0914，BMR=0.0962
- logs：[cachesim_sb3_1104_225331.log](cachesim_sb3_1104_225331.log) / [ac_sb3_1104_225331.log](ac_sb3_1104_225331.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=5e-05；gamma=0.99；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)
 - - policy.net_arch: [256, 256]
 - - policy.activation_fn: <class 'torch.nn.modules.activation.ReLU'>

**1103_213043**（20251103）

- 结果：OMR=0.1379，BMR=0.1400
- logs：[cachesim_sb3_1103_213043.log](cachesim_sb3_1103_213043.log) / [ac_sb3_1103_213043.log](ac_sb3_1103_213043.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=TD3；batch=256；lr=0.0003；gamma=0.99；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: TD3 (off-policy)
 - - policy.net_arch: [256, 256]

**1103_204120**（20251103）

- 结果：OMR=0.1265，BMR=0.1305
- logs：[cachesim_sb3_1103_204120.log](cachesim_sb3_1103_204120.log) / [ac_sb3_1103_204120.log](ac_sb3_1103_204120.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=5e-05；gamma=0.99；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)
 - - policy.net_arch: [256, 256]
 - - policy.activation_fn: <class 'torch.nn.modules.activation.ReLU'>

**1103_202052**（20251103）

- 结果：OMR=0.1248，BMR=0.1276
- logs：[cachesim_sb3_1103_202052.log](cachesim_sb3_1103_202052.log) / [ac_sb3_1103_202052.log](ac_sb3_1103_202052.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=5e-05；gamma=0.99；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)
 - - policy.net_arch: [256, 256]
 - - policy.activation_fn: <class 'torch.nn.modules.activation.ReLU'>

**1103_194355**（20251103）

- 结果：OMR=0.1248，BMR=0.1283
- logs：[cachesim_sb3_1103_194355.log](cachesim_sb3_1103_194355.log) / [ac_sb3_1103_194355.log](ac_sb3_1103_194355.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：algo=SAC；batch=256；lr=5e-05；gamma=0.99；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)；penalty=(obj_penalty=1.000, byte_penalty=0.000)
 - - algorithm: SAC (off-policy)
 - - policy.net_arch: [256, 256]
 - - policy.activation_fn: <class 'torch.nn.modules.activation.ReLU'>

**1103_190008**（20251103）

- 结果：OMR=0.0973，BMR=0.1017
- logs：[cachesim_sb3_1103_190008.log](cachesim_sb3_1103_190008.log) / [ac_sb3_1103_190008.log](ac_sb3_1103_190008.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：state=26；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)

**1103_112912**（20251103）

- 结果：OMR=0.0980，BMR=0.1017
- logs：[cachesim_sb3_1103_112912.log](cachesim_sb3_1103_112912.log) / [ac_sb3_1103_112912.log](ac_sb3_1103_112912.log)
- cachesim：req=10000000；int=200；mr_w=1.000 bmr_w=0.000
- RL：state=26；reward=(miss_ratio=1.000, byte_miss_ratio=0.000)


<!-- ROOT_LOGS_END -->
