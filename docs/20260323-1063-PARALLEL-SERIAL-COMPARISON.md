# 20260323 1063 并行/串行对比汇总

## 1. 范围与目标

本文汇总 1063 trace 在以下三类场景下的 LOH-OMR 结果：

- 本次实验：并行（两作业同时跑，均固定 20 线程）
- 本次实验：串行（不显式设置线程，默认线程数）
- 之前实验：串行（固定 20 线程）与并行（历史默认配置）
- 其他机器历史基线：`0318_204023_1063_SAC_ex0_run2_0318_204023_1773837623`

对比指标：MR / BMR / MQPS。

## 2. 原始结果汇总

| 组别 | 子场景 | MR | BMR | MQPS | 结果行 |
|---|---|---:|---:|---:|---|
| 本次并行（20x2） | seed=3407 | 0.023625 | 0.024980 | 0.70 | [tmp/20260323-par20-seed3407.log#L96](../tmp/20260323-par20-seed3407.log#L96) |
| 本次并行（20x2） | seed=unset | 0.023625 | 0.024983 | 0.70 | [tmp/20260323-par20-seed-unset.log#L95](../tmp/20260323-par20-seed-unset.log#L95) |
| 本次串行（默认线程） | seed=3407 | 0.023253 | 0.024638 | 0.94 | [tmp/20260323-serdef-seed3407.log#L94](../tmp/20260323-serdef-seed3407.log#L94) |
| 本次串行（默认线程） | seed=unset | 0.022970 | 0.024332 | 0.95 | [tmp/20260323-serdef-seed-unset.log#L94](../tmp/20260323-serdef-seed-unset.log#L94) |
| 之前串行（固定20） | seed=3407 | 0.023119 | 0.024555 | 0.97 | [tmp/20260323-cmp-single-seed3407-rerun3.log#L94](../tmp/20260323-cmp-single-seed3407-rerun3.log#L94) |
| 之前串行（固定20） | seed=unset | 0.022805 | 0.024166 | 0.99 | [tmp/20260323-cmp-single-seed-unset-rerun4.log#L94](../tmp/20260323-cmp-single-seed-unset-rerun4.log#L94) |
| 之前并行（历史默认） | seed=3407 | 0.023644 | 0.024986 | 0.71 | [tmp/20260323-default-release-seed3407.log#L94](../tmp/20260323-default-release-seed3407.log#L94) |
| 之前并行（历史默认） | seed=unset | 0.023376 | 0.024721 | 0.72 | [tmp/20260323-default-release-seed-unset.log#L94](../tmp/20260323-default-release-seed-unset.log#L94) |
| 其他机器 0318 基线 | run2 | 0.022901 | 0.024290 | 0.47 | [logs/cachesim_sb3_0318_204023_1063_SAC_ex0_run2_0318_204023_1773837623.log#L51](../logs/cachesim_sb3_0318_204023_1063_SAC_ex0_run2_0318_204023_1773837623.log#L51) |

## 3. 线程与运行形态证据

- 本次并行组为 20 线程：
  - [logs/cachesim_sb3_20260323_par20_seed3407.log#L39](../logs/cachesim_sb3_20260323_par20_seed3407.log#L39)
  - [logs/cachesim_sb3_20260323_par20_seed_unset.log#L39](../logs/cachesim_sb3_20260323_par20_seed_unset.log#L39)
- 本次串行默认组为 112 线程：
  - [logs/cachesim_sb3_20260323_serDef_seed3407.log#L39](../logs/cachesim_sb3_20260323_serDef_seed3407.log#L39)
  - [logs/cachesim_sb3_20260323_serDef_seed_unset.log#L39](../logs/cachesim_sb3_20260323_serDef_seed_unset.log#L39)
- 其他机器 0318 基线为 20 线程：
  - [logs/cachesim_sb3_0318_204023_1063_SAC_ex0_run2_0318_204023_1773837623.log#L3](../logs/cachesim_sb3_0318_204023_1063_SAC_ex0_run2_0318_204023_1773837623.log#L3)

## 4. 结论

1. 在本机上，本次“并行 20x2”显著弱于“串行默认 112 线程”。
- 并行 20x2 平均：MR 0.023625，BMR 0.024982，MQPS 0.70。
- 串行默认平均：MR 0.023112，BMR 0.024485，MQPS 0.945。

2. 之前实验也呈现类似趋势：
- 之前并行（历史默认）平均 MQPS 约 0.715，明显低于之前串行固定20（平均约 0.98）。
- 说明“并行两任务”会带来额外竞争开销，且影响不仅体现在吞吐，也体现在 MR/BMR。

3. 与其他机器 0318 基线比较：
- 0318 的 MR/BMR 接近较优水平（MR 0.022901，BMR 0.024290），但 MQPS 仅 0.47。
- 该条结果来自不同机器与不同运行现场，MQPS 不宜直接与本机做绝对横比，主要用于命中率量级参考。

## 5. 原因解释（结合现有证据）

1. 并行任务存在复合资源竞争。
- 即使总核心数较高，两个任务并行时仍会共享/争用内存带宽、LLC、NUMA 访问路径、调度时片与日志 IO。
- 当前工作负载含 cachesim + Python RL 进程，交互与更新节奏对抖动敏感，导致 MQPS 与命中率同时受影响。

2. 线程配置差异会放大性能差距。
- 本次并行组是 20 线程；本次串行默认组是 112 线程。
- 线程数差异本身会提升串行默认组 MQPS，并可能改善策略交互稳定性。

3. 跨机器基线只能做趋势参考。
- 0318 基线在不同机器，系统拓扑和负载背景不同；应重点看趋势，不应直接做同机同条件性能宣判。

## 6. 训练次数对比（ASYNC）

| 组别 | 子场景 | 后台训练次数 | 证据 |
|---|---|---:|---|
| 本次并行（20x2） | seed=3407 | 1556 | [tmp/20260323-par20-seed3407.log#L128](../tmp/20260323-par20-seed3407.log#L128) |
| 本次并行（20x2） | seed=unset | 1539（`n_updates`） | [tmp/20260323-par20-seed-unset.log#L106](../tmp/20260323-par20-seed-unset.log#L106) |
| 本次串行（默认线程） | seed=3407 | 5394 | [tmp/20260323-serdef-seed3407.log#L126](../tmp/20260323-serdef-seed3407.log#L126) |
| 本次串行（默认线程） | seed=unset | 4890 | [tmp/20260323-serdef-seed-unset.log#L126](../tmp/20260323-serdef-seed-unset.log#L126) |
| 之前串行（固定20） | seed=3407 | 5328 | [tmp/20260323-cmp-single-seed3407-rerun3.log#L126](../tmp/20260323-cmp-single-seed3407-rerun3.log#L126) |
| 之前串行（固定20） | seed=unset | 5230 | [tmp/20260323-cmp-single-seed-unset-rerun4.log#L126](../tmp/20260323-cmp-single-seed-unset-rerun4.log#L126) |
| 之前并行（历史默认） | seed=3407 | 1690 | [tmp/20260323-default-release-seed3407.log#L126](../tmp/20260323-default-release-seed3407.log#L126) |
| 之前并行（历史默认） | seed=unset | 1506 | [tmp/20260323-default-release-seed-unset.log#L127](../tmp/20260323-default-release-seed-unset.log#L127) |
| 其他机器 0318 基线 | run2 | 6697（`n_updates` 终值） | [logs/ac_sb3_0318_204023_1063_SAC_ex0_run2_0318_204023_1773837623.log#L3184156](../logs/ac_sb3_0318_204023_1063_SAC_ex0_run2_0318_204023_1773837623.log#L3184156) |

补充说明：

- 本次并行 seed=unset 日志未打印“后台训练次数”，表中采用 `n_updates=1539` 作为更新次数参考。
- 从可用统计看，并行组训练次数约 1.5k~1.7k，显著低于串行组约 4.9k~5.4k，和并行组命中率/吞吐劣化趋势一致。
- 0318 基线未打印“后台训练次数”，此处使用 AC 日志最后一次 `n_updates` 作为训练规模参考值。

## 7. 复现入口与产物映射

- 运行脚本：
  - [scripts/test_loh_rl_sb3.sh](../scripts/test_loh_rl_sb3.sh)
- 命令记录：
  - [tmp/20260323-cmd-par-vs-ser.log](../tmp/20260323-cmd-par-vs-ser.log)
- 本次对比产物：
  - [tmp/20260323-par20-seed3407.log](../tmp/20260323-par20-seed3407.log)
  - [tmp/20260323-par20-seed-unset.log](../tmp/20260323-par20-seed-unset.log)
  - [tmp/20260323-serdef-seed3407.log](../tmp/20260323-serdef-seed3407.log)
  - [tmp/20260323-serdef-seed-unset.log](../tmp/20260323-serdef-seed-unset.log)
- 历史参考产物：
  - [tmp/20260323-cmp-single-seed3407-rerun3.log](../tmp/20260323-cmp-single-seed3407-rerun3.log)
  - [tmp/20260323-cmp-single-seed-unset-rerun4.log](../tmp/20260323-cmp-single-seed-unset-rerun4.log)
  - [tmp/20260323-default-release-seed3407.log](../tmp/20260323-default-release-seed3407.log)
  - [tmp/20260323-default-release-seed-unset.log](../tmp/20260323-default-release-seed-unset.log)
  - [logs/cachesim_sb3_0318_204023_1063_SAC_ex0_run2_0318_204023_1773837623.log](../logs/cachesim_sb3_0318_204023_1063_SAC_ex0_run2_0318_204023_1773837623.log)
