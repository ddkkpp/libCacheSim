# 20260330 Reward/State Ablation Results

## 1. 实验范围

本轮聚焦两个问题：

1. 固定 reward 后，结果是否变化。
2. 同时固定 reward + state 后，结果是否变化。

涉及日志目录：
- tmp/20260330-meta-and-const-full/logs/

## 2. 结果汇总

### 2.1 meta 全量（meta_reag）

- baseline（无 penalty，不固定 reward/state）
  - 来源: tmp/20260330-meta-and-const-full/logs/run_meta_full_base_nopen.log:94
  - miss ratio: 0.269161
  - byte miss ratio: 0.153855
  - throughput: 1.09 MQPS

- 固定 reward=0.5（无 penalty，state 不固定）
  - 来源: tmp/20260330-meta-and-const-full/logs/run_meta_full_fixreward_nopen.log:95
  - miss ratio: 0.269155
  - byte miss ratio: 0.154082
  - throughput: 1.06 MQPS

- 固定 reward=0.5 + 固定 state=0.5（LOH_FIXED_OBS_MODE=2）
  - 来源: tmp/20260330-meta-and-const-full/logs/run_meta_full_const_reward_state_v2.log:96
  - miss ratio: 0.269142
  - byte miss ratio: 0.154017
  - throughput: 1.02 MQPS

- 仅固定 state=0.5（reward 不固定）
  - 来源: tmp/20260330-meta-and-const-full/logs/run_meta_full_const_state_only.log:95
  - miss ratio: 0.269145
  - byte miss ratio: 0.153873
  - throughput: 1.11 MQPS

### 2.2 1063 全量（tencentBlock_1063）

- 固定 reward=0.5 + 固定 state=0.5（LOH_FIXED_OBS_MODE=2）
  - 来源: tmp/20260330-meta-and-const-full/logs/run_1063_full_const_reward_state.log:96
  - miss ratio: 0.023343
  - byte miss ratio: 0.024658
  - throughput: 0.71 MQPS

## 3. 关键现象

在本轮日志中，多个 case 同时出现以下结论性提示：

- 未检测到 SB3 训练更新
  - 示例: tmp/20260330-meta-and-const-full/logs/run_meta_full_fixreward_nopen.log:147
  - 示例: tmp/20260330-meta-and-const-full/logs/run_1063_full_const_reward_state.log:148

- 未检测到权重更新（C 端未观察到 RL 权重变化）
  - 示例: tmp/20260330-meta-and-const-full/logs/run_meta_full_fixreward_nopen.log:150
  - 示例: tmp/20260330-meta-and-const-full/logs/run_1063_full_const_reward_state.log:151

## 4. 解释：如果 reward/state 看起来不起作用，效果来自哪里？

在这批实验里，最可能的主导因素不是 RL 学习结果，而是 C 端 LOH 的非学习路径和默认策略：

1. C 端打分与候选流程本身仍在工作。
2. 候选采样、预算控制、默认权重/规则会直接决定驱逐行为。
3. 当 SB3 没有稳定产生训练更新且 C 端未接收新权重时，系统等价于“固定策略 + 运行时统计扰动”。

因此会看到：

- 固定 reward 或固定 state 对最终 miss 几乎无影响。
- 指标主要由非 RL 逻辑决定，变化集中在小幅吞吐抖动和随机性。

## 5. 后续建议（用于验证上述解释）

1. 在同配置下增加“强制权重写入次数/频率”观测，确认 C 端确实收到权重变化。
2. 输出每小时或每固定请求量的权重快照，验证是否随时间有学习漂移。
3. 增加一个强对照：固定权重向量 A vs 固定权重向量 B，检验 C 端行为是否可被权重显著拉开。
