# LOH 在线 GBM actor 与 Hit/Miss 输入对照

## 目的

本实验把 LOH 的外部 actor 从 SB3/RL 替换为在线 LightGBM/GBM 权重预测器，仍然使用 LOH 原有的候选生成与 scoring 中间层，actor 输出 7 维权重向量。实验目标有两个：

1. 判断 LOH/RSD 的效果主要来自中间层设计，还是来自某个具体模型。
2. 判断把 Hit/Miss 统计加入 actor 输入后，在线 GBM 是否能稳定受益。

## 实验配置

### 2 维在线 GBM actor

本文中的“2 维 GBM”指最早一版 online GBM actor 的输入状态只有 2 维，即 `hit_ratio` 和 `byte_hit_ratio`。它不是输出维度；actor 输出始终是 LOH 使用的 7 维权重向量。

- 代码路径：`scripts/loh_gbm_weight_actor.py`
- cachesim：`_build_rel_gbm_actor/bin/cachesim`
- 运行脚本：`tmp/20260525-loh-gbm-actor/run_online_gbm_meta_1063.sh`
- 日志目录：`tmp/20260525-loh-gbm-actor/logs/`
- actor 后端：LightGBM C API，`/usr/local/lib/lib_lightgbm.so`
- shared-memory 模式：`LOH_ENABLE_RL=1`，`LOH_ENABLE_CMAES=0`，`LOH_WAIT_MODE=nonblocked`
- LOH 候选：`LOH_RANDOM_CANDIDATES=256`，`LOH_STRUCTURED_CANDIDATES=16`
- scoring：compound on，IRT off，log1p features on
- actor 状态维度：2，即 `hit_ratio` 与 `byte_hit_ratio`
- 在线训练：batch 256，max samples 4096，16 boost rounds，explore prob 0.25
- 权重范围：`LOH_GBM_WEIGHT_LB=0`，`LOH_GBM_WEIGHT_UB=1`

### Hit/Miss 输入对照

- No-Hit/Miss binary：`_build_rel_gbm_actor/bin/cachesim`
- Hit/Miss binary：`_build_rel_gbm_actor_hitmiss/bin/cachesim`
- Hit/Miss 构建开关：`LOH_INCLUDE_HIT_MISS_FEATURES=1`
- actor 输入：`LOH_GBM_INPUT_DIM=active`
- No-Hit/Miss active state：2 维
- Hit/Miss active state：14 维，位于 26 维 shared-memory envelope 中
- fast online GBM budget：batch size 4096，min train samples 4096，max samples 4096，boost rounds 4，leaves 7，LightGBM threads 1
- 运行脚本：
  - `tmp/20260526-hitmiss-gbm/run_hitmiss_main_and_medium.sh`
  - `tmp/20260526-hitmiss-gbm/run_main_nohit_fast_matched.sh`
- 结果表：`tmp/20260526-hitmiss-gbm/hitmiss_results.md`

### manifest-v7 runner 的模型配置

`tmp/20260526-hitmiss-gbm/run_manifest_v7_gbm_main_and_medium.sh` 用 `tmp/20260524-drl-v7-manifest-selected` 作为 LOH-v7 scoring 配置源；它不再手写或推导 `f001_orig/f100_ns/f101_orig` 规则，而是逐行读取 `trace_path`、`trace_type`、`LOH_USE_SIZE`、`LOH_USE_FREQ_REC`、`LOH_USE_FREQ_SIZE`、`LOH_USE_REC_SIZE`。

在线 GBM actor 本身的模型配置如下：

- 模型后端：LightGBM C API，`/usr/local/lib/lib_lightgbm.so`
- 模型形式：7 个独立的 LightGBM regression boosters，每个 booster 预测 1 个 LOH weight；最终写回 7 维权重向量。
- booster 数量固定为 7，不随 manifest score 配置变化。manifest 只决定 C 侧当前 scoring 会实际启用哪些权重；未启用的权重即使由 actor 写回，也不会参与该次 LOH score 计算。
- 输入状态：`LOH_GBM_INPUT_DIM=active`。No-Hit/Miss 为 2 维 active state；Hit/Miss 为 14 维 active state。
- 在线训练标签：上一窗口实际采用的 7 维权重向量；窗口反馈 reward 用来筛选/加权样本。
- reward 模式：`LOH_GBM_ONLINE_REWARD_MODE=delta`。
- 目标权重：MR case 使用 `LOH_MISS_RATIO_WEIGHT=1.0`；BMR case 使用 `LOH_MISS_RATIO_WEIGHT=0.0`。
- LightGBM 训练预算：batch size 4096，min train samples 4096，max samples 4096，boost rounds 4，learning rate 0.05，num leaves 7，min data in leaf 16，feature fraction 1.0，bagging fraction 1.0，bagging freq 0，num threads 1，seed 42。
- 探索策略：`explore_prob=0.25`，`bootstrap_explore_prob=1.0`，`explore_std=0.08`，`explore_decay=0.995`，`min_explore_std=0.02`。
- 权重约束：`LOH_GBM_WEIGHT_LB=0`，`LOH_GBM_WEIGHT_UB=1`。
- LOH 候选配置：`LOH_RANDOM_CANDIDATES=256`，`LOH_STRUCTURED_CANDIDATES=16`，`LOH_ADAPTIVE_BUDGET=1`。

也就是说，manifest-v7 runner 改的是 LOH scoring feature 开关和 MR/BMR 目标；GBM actor 的训练模型仍是同一套低频 online LightGBM 配置。

`scripts/test_loh_rl_sb3.sh` 的结尾分析仍按 SB3 日志关键字判断，所以会提示“未检测到SB3训练更新/权重更新”。这不是本实验失败信号；有效信号以 actor 日志中的 `[GBM ONLINE] trained`、`[WEIGHTS_UPDATED]` 和 cachesim final summary 为准。

### 三个 GBM 列名的区别

这三个列名都表示“GBM actor 输出 LOH 的 7 维权重向量”，区别不在输出，而在输入特征和训练/运行配置。

| 列名 | 用途 | actor 输入 | 训练/运行配置 | 是否用于 Hit/Miss 公平消融 |
|---|---|---|---|---|
| 2维 GBM | 最早一版 online GBM 主实验 | 2 维：`hit_ratio`、`byte_hit_ratio` | 原始 online 配置：batch 256、16 boost rounds、explore prob 0.25 | 否，主要用于说明“简单 GBM + LOH 中间层”的效果 |
| No-Hit/Miss GBM | Hit/Miss 消融中的无 Hit/Miss 对照组 | 2 维 active state：`hit_ratio`、`byte_hit_ratio` | fast matched 配置：batch 4096、4 boost rounds、leaves 7、threads 1 | 是，与 Hit/Miss GBM 参数匹配 |
| Hit/Miss GBM | Hit/Miss 消融中的实验组 | 14 维 active state：前 2 维 ratio + 12 维 Hit/Miss 统计 | fast matched 配置：batch 4096、4 boost rounds、leaves 7、threads 1 | 是，与 No-Hit/Miss GBM 只差 Hit/Miss 输入 |

因此，`2维 GBM` 和 `No-Hit/Miss GBM` 都没有 Hit/Miss 输入，但不能直接把二者差异解释成算法收益；它们使用的是不同训练预算和运行配置。判断 Hit/Miss 是否有效，应看 `No-Hit/Miss GBM` 与 `Hit/Miss GBM` 的成对比较。

“输出 7 维”来自 C/Python shared-memory 协议，而不是表格列名的推断：

- Python actor 在 `scripts/loh_gbm_weight_actor.py` 中定义 `SHM_WEIGHT_DIM = 7`，`SharedMemoryData.weights` 是 `ctypes.c_double * SHM_WEIGHT_DIM`，写回时循环 `for i in range(SHM_WEIGHT_DIM): data.weights[i] = ...`。
- C 侧在 `libCacheSim/cache/eviction/LOH.c` 中定义 `WEIGHT_DIM 7`，`shm_data_t.weights` 是 `double weights[WEIGHT_DIM]`，读取 Python 回写时使用 `memcpy(params->weights, shm_data.weights, sizeof(double) * WEIGHT_DIM)`。
- 因此 actor 与 C 侧通信的权重向量长度固定是 7。具体一次 scoring 是否使用全部 7 个权重，取决于 C 侧当前 scoring 配置；日志里的 `dim=x/7` 表示当前有效使用 `x` 维、协议上限为 7 维。

## 2 维在线 GBM 结果

这里的“2 维”只描述 actor 输入，不描述模型输出。所有 GBM 版本最终都会写回 7 个 LOH scoring weights。

| trace | cache ratio | req | Online GBM MR | Online GBM BMR | actor train count | weight updates |
|---|---:|---:|---:|---:|---:|---:|
| meta_reag | 0.1 | 45,623,306 | 0.317896 | 0.171730 | 8 | 2258 |
| tencentBlock_1063 | 0.1 | 360,960,512 | 0.232481 | 0.202229 | 79 | 20272 |
| meta_reag | 0.001 | 45,623,306 | 0.431234 | 0.222312 | 3 | 806 |
| tencentBlock_1063 | 0.001 | 360,960,512 | 0.910380 | 0.920463 | 38 | 9908 |

## 与 LOH-v7、3LCache-OMR、3LCache-BMR 的 MR 对照

历史对照来自：

- `docs/20260422-ablation-per-group-cache01/cmaes版本LOH/metaCDN.md`
- `docs/20260422-ablation-per-group-cache01/cmaes版本LOH/tencentBlock.md`
- `docs/20260423-ablation-per-group-cache0001/cmaes版本/metaCDN.md`
- `docs/20260423-ablation-per-group-cache0001/cmaes版本/tencentBlock.md`

表中 `Hit/Miss GBM` 使用 `hitmiss_fast`；`No-Hit/Miss GBM` 使用同参数的 `nohit_fast_matched`。`LOH-v7` 对应原表中的 best_LOH/v7。

| trace | cache ratio | 2维 GBM | No-Hit/Miss GBM | Hit/Miss GBM | 3LCache-OMR | 3LCache-BMR | LOH-v7 |
|---|---:|---:|---:|---:|---:|---:|---:|
| meta_reag | 0.1 | 0.317896 | 0.323536 | 0.323025 | 0.392964 | 0.324215 | 0.270060 |
| tencentBlock_1063 | 0.1 | 0.232481 | 0.233499 | 0.233991 | 0.060630 | 0.252227 | 0.020059 |
| meta_reag | 0.001 | 0.431234 | 0.433323 | 0.433180 | 0.489205 | 0.432100 | 0.312774 |
| tencentBlock_1063 | 0.001 | 0.910380 | 0.908802 | 0.908759 | 0.732876 | 0.854600 | 0.697962 |

## 与 LOH-v7、3LCache-OMR、3LCache-BMR 的 BMR 对照

| trace | cache ratio | 2维 GBM | No-Hit/Miss GBM | Hit/Miss GBM | 3LCache-OMR | 3LCache-BMR | LOH-v7 |
|---|---:|---:|---:|---:|---:|---:|---:|
| meta_reag | 0.1 | 0.171730 | 0.173748 | 0.173596 | 0.192144 | 0.170269 | 0.155369 |
| tencentBlock_1063 | 0.1 | 0.202229 | 0.202021 | 0.202321 | 0.062025 | 0.207182 | 0.350872 |
| meta_reag | 0.001 | 0.222312 | 0.222607 | 0.222629 | 0.250859 | 0.219700 | 0.205810 |
| tencentBlock_1063 | 0.001 | 0.920463 | 0.919527 | 0.919553 | 0.844205 | 0.879500 | 0.777336 |

注意：tencentBlock_1063 cache=0.1 的 MR 最优 LOH 配置和 BMR 表中的 LOH-v7 配置明显不一致；该 trace 上 MR/BMR 目标冲突很强，不能只用其中一个目标概括全部效果。

## Hit/Miss 输入主 trace 对照

公平比较应使用 `hitmiss_fast` 与 `nohit_fast_matched`，两者 actor 参数、训练预算和运行脚本环境一致，仅是否启用 Hit/Miss 输入不同。

| trace | cache | No-Hit/Miss MR | Hit/Miss MR | delta MR | No-Hit/Miss BMR | Hit/Miss BMR | delta BMR |
|---|---:|---:|---:|---:|---:|---:|---:|
| meta_reag | 0.1 | 0.323536 | 0.323025 | -0.000511 | 0.173748 | 0.173596 | -0.000152 |
| meta_reag | 0.001 | 0.433323 | 0.433180 | -0.000143 | 0.222607 | 0.222629 | +0.000022 |
| tencentBlock_1063 | 0.1 | 0.233499 | 0.233991 | +0.000492 | 0.202021 | 0.202321 | +0.000300 |
| tencentBlock_1063 | 0.001 | 0.908802 | 0.908759 | -0.000043 | 0.919527 | 0.919553 | +0.000026 |

结论：主 trace 上 Hit/Miss 输入不是稳定显著收益。meta_reag 上 MR 略好，tencentBlock_1063 cache=0.1 上略差，cache=0.001 基本持平。差异量级通常只有 `1e-4` 到 `5e-4`。

## Hit/Miss 输入中等 trace 对照

4 个中等请求量 Tencent traces 使用同一 runner 成对运行 No-Hit/Miss 与 Hit/Miss。

| trace | cache | No-Hit/Miss MR | Hit/Miss MR | delta MR | No-Hit/Miss BMR | Hit/Miss BMR | delta BMR |
|---|---:|---:|---:|---:|---:|---:|---:|
| tencentBlock_10635 | 0.1 | 0.190382 | 0.190339 | -0.000043 | 0.216916 | 0.216862 | -0.000054 |
| tencentBlock_1069 | 0.1 | 0.323418 | 0.323132 | -0.000286 | 0.440625 | 0.439676 | -0.000949 |
| tencentBlock_10799 | 0.1 | 0.167118 | 0.167053 | -0.000065 | 0.195932 | 0.195653 | -0.000279 |
| tencentBlock_10935 | 0.1 | 0.204923 | 0.204776 | -0.000147 | 0.581229 | 0.581219 | -0.000010 |

结论：中等 trace 上 Hit/Miss 输入稳定小幅更好，但收益很小。最大 BMR 改善出现在 tencentBlock_1069，约 `9.49e-4`。

## 结论

1. LOH 的优势主要来自中间层设计，而不是某个单一模型本身。
   把 actor 换成在线 GBM 后，只要保留 LOH 的候选生成和多信号 scoring，中等场景仍能接近或超过部分 object-level learned cache baseline。例如 meta_reag 0.1 上 2 维 online GBM 的 MR 低于 3LCache-OMR 与 3LCache-BMR，tencentBlock_1063 0.1 上也低于 3LCache-BMR。

2. 模型/优化器仍然重要，但它是在 LOH 中间层内部起作用。
   online GBM 明显弱于 LOH-v7，尤其是 meta_reag 0.001 与 tencentBlock_1063 0.001。这说明“候选生成 + scoring 空间”提供了可优化结构，但 CMA-ES/v7 的权重搜索或手工配置仍比当前 online GBM 更会利用这个空间。

3. 3LCache-OMR 在 tencentBlock_1063 上很强，说明 learned cache 路线并非天然无效。
   但它的优势高度 trace/目标相关：meta_reag 上 3LCache-OMR 明显差，tencentBlock_1063 上却很强。因此更准确的说法不是“learned cache 不行”，而是 object-level learned predictor 对目标、标签延迟、censoring、size/objective 粒度很敏感。

4. Hit/Miss 输入目前只是边际增益信号。
   中等 trace 上 Hit/Miss 稳定小赢，主 trace 上基本持平或轻微波动。当前 online GBM 训练方式还没有强力利用 14 维 Hit/Miss state，因此不能把 Hit/Miss 输入视为决定性改进。

5. 当前 online GBM 不是 LOH 中间层能力的上限。
   2 维版本只用了 `hit_ratio` 与 `byte_hit_ratio`；Hit/Miss 版本虽然增加到 active 14 维，但仍缺少候选集合统计、cache occupancy、request summary、top-k gap 等信息。因此它更像一个替换 actor 的 sanity check，而不是已经调到充分强的 actor。

## 可用于论文的表述

LOH/RSD 的核心贡献应表述为中间层设计：把在线淘汰拆成候选对象生成和轻量多信号 scoring，使模型只需要在 workload/window 级别调节少量权重，而不是直接学习每个 object 的长期命运。在线 GBM 替换实验显示，即使使用简单在线模型，保留该中间层后仍能在部分 workload 上接近或超过 3LCache；但整体仍弱于 LOH-v7，说明最终效果还依赖权重搜索/优化策略。Hit/Miss 输入带来的收益较小，进一步说明主要收益不是来自简单增加状态维度，而是来自 LOH 中间层把淘汰问题改写成了更容易优化的候选排序问题。

## 后续验证建议

- 在同一 candidate set 上比较 fixed weights、online GBM、CMA-ES/v7 和 3LCache-style object score，隔离 candidate generation 的贡献。
- 扩展 online GBM state，加入 cache/candidate/top-k/request summary，再看是否接近 LOH-v7。
- 对 tencentBlock_1063 单独做 MR 与 BMR 双目标 Pareto 分析，因为该 trace 上两个目标冲突很明显。
- 固定随机种子重复 online GBM，报告均值和方差，避免一次在线探索轨迹被误读。
