# LOH RL 统一脚本使用说明

`loh_actor_critic_sb3.py` 已完全整合了所有 LOH RL 变体的功能。

## 快速开始

### 默认配置（SAC + reciprocal penalty）
```bash
python scripts/loh_actor_critic_sb3.py
```

### 使用 PPO 算法
```bash
LOH_RL_ALGO=PPO python scripts/loh_actor_critic_sb3.py
```

### 使用 TD3 算法
```bash
LOH_RL_ALGO=TD3 python scripts/loh_actor_critic_sb3.py
```

## 核心环境变量

### 算法选择
- **LOH_RL_ALGO**: `PPO` | `SAC` | `TD3` (默认: `SAC`)

### Penalty 缩放模式
- **LOH_PENALTY_SCALE**: `reciprocal` | `log` | `survival` (默认: `reciprocal`)
  - `reciprocal`: 1/max(d,1)
  - `log`: 1 - log1p(d)/log1p(dmax)
  - `survival`: S(d) = 1 - F(d)
- **LOH_PENALTY_DMAX**: penalty 距离上限（默认: 400000）

### Reward 滑动窗口
- **LOH_REWARD_WINDOW**: 窗口大小（默认: 0，禁用）

## 使用示例

### PPO + reward 滑动窗口
```bash
LOH_RL_ALGO=PPO LOH_REWARD_WINDOW=5 python scripts/loh_actor_critic_sb3.py
```

### TD3 + 对数 penalty 缩放
```bash
LOH_RL_ALGO=TD3 LOH_PENALTY_SCALE=log LOH_PENALTY_DMAX=500000 python scripts/loh_actor_critic_sb3.py
```

### SAC + 生存函数 penalty
```bash
LOH_RL_ALGO=SAC LOH_PENALTY_SCALE=survival LOH_SURVIVAL_QUANTILE=0.95 python scripts/loh_actor_critic_sb3.py
```

## 算法特定参数

### PPO 参数（前缀 PPO_）
- PPO_BUFFER_SIZE (默认: 2048)
- PPO_BATCH_SIZE (默认: 64)
- PPO_N_EPOCHS (默认: 10)
- PPO_LEARNING_RATE (默认: 3e-4)
- PPO_GAMMA (默认: 0.99)
- PPO_GAE_LAMBDA (默认: 0.95)
- PPO_CLIP_RANGE (默认: 0.2)
- PPO_NET_ARCH (默认: "256,256")

### SAC 参数（前缀 SAC_）
- SAC_BUFFER_SIZE (默认: 10000)
- SAC_BATCH_SIZE (默认: 256)
- SAC_LEARNING_RATE (默认: 3e-4)
- SAC_TRAIN_FREQ (默认: 16)
- SAC_LEARNING_STARTS (默认: 3000)
- SAC_ENT_COEF (默认: "auto")
- SAC_NET_ARCH (默认: "256,256")

### TD3 参数（前缀 TD3_）
- TD3_BUFFER_SIZE (默认: 10000)
- TD3_BATCH_SIZE (默认: 256)
- TD3_LEARNING_RATE (默认: 3e-4)
- TD3_TRAIN_FREQ (默认: 16)
- TD3_LEARNING_STARTS (默认: 3000)
- TD3_POLICY_DELAY (默认: 2)
- TD3_ACTION_NOISE (探索噪声 σ，默认: None)
- TD3_NET_ARCH (默认: "256,256")

## 完整示例（与 test_loh_rl_sb3.sh 集成）

```bash
# PPO + reward window
LOH_RL_ALGO=PPO \
LOH_REWARD_WINDOW=5 \
PPO_N_EPOCHS=15 \
PPO_CLIP_RANGE=0.3 \
PYTHON_SCRIPT=loh_actor_critic_sb3.py \
bash ./scripts/test_loh_rl_sb3.sh data/trace.zst

# TD3 + log penalty
LOH_RL_ALGO=TD3 \
LOH_PENALTY_SCALE=log \
LOH_PENALTY_DMAX=500000 \
TD3_POLICY_DELAY=3 \
PYTHON_SCRIPT=loh_actor_critic_sb3.py \
bash ./scripts/test_loh_rl_sb3.sh data/trace.zst

# SAC + survival penalty（默认配置）
LOH_PENALTY_SCALE=survival \
LOH_SURVIVAL_QUANTILE=0.99 \
PYTHON_SCRIPT=loh_actor_critic_sb3.py \
bash ./scripts/test_loh_rl_sb3.sh data/trace.zst
```

## 注意事项

1. PPO 不使用 replay buffer，因此 `--exclude-recent-steps` 参数对 PPO 无效
2. Reward 滑动窗口适用于所有算法
3. Penalty 缩放模式仅影响 SAC 和 TD3（需要 replay buffer）
4. 所有参数都可以通过环境变量覆盖，无需修改代码

## 迁移指南

原有的独立脚本现在可以用统一脚本 + 环境变量替代：

| 原脚本 | 等价环境变量配置 |
|--------|-----------------|
| loh_actor_critic_sb3_mr_PPO.py | `LOH_RL_ALGO=PPO` |
| loh_actor_critic_sb3_mr_SAC.py | `LOH_RL_ALGO=SAC` (或省略) |
| loh_actor_critic_sb3_mr_RewardSlide_PPO.py | `LOH_RL_ALGO=PPO LOH_REWARD_WINDOW=5` |
| loh_actor_critic_sb3_pen_d_SAC.py | `LOH_PENALTY_SCALE=reciprocal` (或省略) |
| loh_actor_critic_sb3_pen_d_TD3.py | `LOH_RL_ALGO=TD3 LOH_PENALTY_SCALE=reciprocal` |
| loh_actor_critic_sb3_pen_log_SAC.py | `LOH_PENALTY_SCALE=log` |
| loh_actor_critic_sb3_pen_survival_SAC.py | `LOH_PENALTY_SCALE=survival` |
