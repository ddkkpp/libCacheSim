# 测试脚本文件夹

此文件夹包含LOH强化学习集成的各种测试脚本。

## 文件命名规则

格式：`MMDDHHMM-脚本名称.sh`
- 前缀为脚本最后修改时间（月日时分）
- 例如：`10282046-test_reward_improvement.sh` 表示10月28日20:46修改

## 脚本列表

### 主要测试脚本
- `10282046-test_reward_improvement.sh` - 奖励改进测试
- `10282045-test_two_component_penalty.sh` - 双组件penalty测试
- `10282026-test_pure_penalty_reward.sh` - 纯penalty奖励测试

### Penalty 机制测试
- `10272237-test_penalty_flow.sh` - Penalty流程测试
- `10272237-quick_penalty_test.sh` - 快速penalty测试
- `10272237-verify_penalty_shm.py` - Penalty共享内存验证

### 推理测试
- `10170043-test_inference.sh` - 推理模式测试
- `10170043-test_loh_inference.sh` - LOH推理测试

### 分析与调试
- `10230213-analyze_training.sh` - 训练分析脚本

### 工具脚本
- `10162108-stop_loh_rl.sh` - 停止LOH RL进程

### 其他算法
- `10232104-test_loh_rl_sb3_PPO.sh` - PPO算法测试（已废弃，使用SAC）

## 使用方法

```bash
# 主测试（根目录的 test_loh_rl_sb3.sh）
cd /home/dingkp/libCacheSim
CACHESIM_NUM_REQ=10000000 LOH_DEBUG_BASIC=1 bash test_loh_rl_sb3.sh data/WikiCDN/wiki_2019t.oracleGeneral.zst

# 纯penalty奖励测试
bash test_scripts/10282026-test_pure_penalty_reward.sh

# 奖励改进测试
bash test_scripts/10282046-test_reward_improvement.sh

# Penalty流程测试
bash test_scripts/10272237-test_penalty_flow.sh

# 训练分析
bash test_scripts/10230213-analyze_training.sh

# 停止所有LOH RL进程
bash test_scripts/10162108-stop_loh_rl.sh
```

## 注意事项

1. 所有脚本都假设从仓库根目录运行
2. 需要先构建项目：`bash scripts/debug.sh -c`
3. Python依赖：stable-baselines3, gymnasium, torch
4. 详细说明请参考 `docs/` 文件夹中的对应文档
