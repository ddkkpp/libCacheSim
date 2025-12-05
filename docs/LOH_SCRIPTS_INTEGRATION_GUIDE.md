# LOH RL 脚本整合指南

## 整合完成情况

已将以下脚本的功能整合到 `loh_actor_critic_sb3.py`：

1. **loh_actor_critic_sb3_mr_PPO.py** - PPO 算法（miss ratio 奖励）
2. **loh_actor_critic_sb3_mr_SAC.py** - SAC 算法（miss ratio 奖励）
3. **loh_actor_critic_sb3_mr_RewardSlide_PPO.py** - PPO + 奖励滑动窗口
4. **loh_actor_critic_sb3_pen_d_SAC.py** - SAC + penalty 倒数缩放
5. **loh_actor_critic_sb3_pen_d_TD3.py** - TD3 + penalty 倒数缩放
6. **loh_actor_critic_sb3_pen_log_SAC.py** - SAC + penalty 对数缩放
7. **loh_actor_critic_sb3_pen_survival_SAC.py** - SAC + penalty 生存函数缩放

## C 端 LOH / LOH-mr-blocked 环境变量总览（运行时）

> 下列环境变量由 C 端 `LOH.c` / `LOH_mr_blocked.c` 在运行时读取；
> 未显式设置时均有合理默认值，可直接运行。

### 1. RL / 权重控制

- `LOH_ENABLE_RL`（默认: `1`）
  - 是否启用与 Python 进程的 RL 通信（共享内存 + 信号量）。
  - 设为 `0`/`false` 时，完全关闭 RL，同步逻辑不会触发，适合固定权重或纯启发式运行。

- `LOH_DISABLE_RL`（默认: 未设置）
  - 与 `LOH_ENABLE_RL` 互斥；若显式设为 `1`/`true`，则强制关闭 RL。

- `LOH_FIXED_WEIGHTS`（默认: 未设置）
  - 固定 6 维特征权重，格式：`"w1,w2,w3,w4,w5,w6"`。
  - 当解析成功时会覆盖 C 端内部的默认权重：
    - `LOH` / `LOH-mr-blocked` 默认均为 `[1,0,0,0,0,0]`（纯 recency）。
  - 典型用法（不需要 Python）：

    ```bash
    LOH_ENABLE_RL=0 \
    LOH_FIXED_WEIGHTS="0,0,1,0,0,0" \
      _build_dbg/bin/cachesim trace oracleGeneral LOH-mr-blocked 0.1 --num-req=3000000 -v 1
    ```

- `miss-ratio-weight`（通过 `cache_specific_params` 传入，默认: `1.0`）
  - 例：`"miss-ratio-weight=1.0"`。
  - 控制 C 端内部奖励中对象 miss 与字节 miss 的权重比例。

### 2. 共享内存 / 信号量

- `LOH_SHM_KEY`（默认: `9876`）
  - 决定共享内存文件 `/dev/shm/loh_ac_<KEY>` 以及 POSIX 信号量名
    `/loh_ac_ready_<KEY>`、`/loh_ac_ack_<KEY>`。
  - 未设置时使用 `9876`。

- `LOH_ENABLE_SEMAPHORE` / `LOH_DISABLE_SEMAPHORE`
  - `LOH_DISABLE_SEMAPHORE=1/true` 时：禁用信号量，仅用轮询读取 `weights_updated` 标志。
  - 否则若 `LOH_ENABLE_SEMAPHORE=1/true`：强制启用信号量。
  - 两者都未设置时：默认启用信号量。

- `LOH_WAIT_MODE`（默认: `blocked`）
  - 控制 C 端在发送状态后是否阻塞等待权重更新：
    - `blocked`：使用 `sem_timedwait` + 轮询，最长等待约 50s。
    - `nonblocked` / `non-blocked`：若 Python 正在训练，则不等待，继续使用缓存中的旧权重。

### 3. 特征变换 / 归一化

- `LOH_FEATURE_LOG1P`（默认: `0`）
  - 设为 `1/true` 时，所有特征采用 `log1p(raw)` 形式。

- `LOH_FEATURE_LOG1P_RECIPROCAL`（默认: `0`）
  - 设为 `1/true` 时，采用 `log1p+1/(1+x)` 形式；若 `LOH_FEATURE_LOG1P=1` 则忽略此项。

- `LOH_ENABLE_FEATURE_NORMALIZATION`（仅在 `LOH.c` 中，默认: `0`）
  - 设为 `1/true` 时，对特征做基于 `log1p(max)` 的归一化与裁剪，同时统计裁剪比例。

- `LOH_FEATURE_NORM_MAX_RECENCY` / `LOH_FEATURE_NORM_MAX_FREQ` /
  `LOH_FEATURE_NORM_MAX_SIZE` / `LOH_FEATURE_NORM_MAX_IRT`（仅 `LOH.c`）
  - 覆盖各特征的归一化上界，默认值由 `loh_feature_norm_max[]` 给出：
    - recency≈`128e6`、freq≈`1e6`、size≈`16e9`、IRT≈`128e6`。

- `LOH_USE_HEURISTIC_SIGNS`（默认: 启用）
  - 默认只要不是显式 `0/false` 就视为启用，用于对部分特征符号做启发式修正。

### 4. Penalty / Ghost cache

- `LOH_ENABLE_PENALTY`（默认: `0`）
  - 是否启用 penalty 队列与延迟惩罚；目前主要通过编译期 `-DLOH_ENABLE_PENALTY=1` 控制，
    运行时变量用于在已编译支持的前提下打开/关闭相关逻辑。

> 说明：编译期宏（`LOH_INCLUDE_CACHE_FEATURES`、`LOH_INCLUDE_HIT_MISS_FEATURES`、
> `LOH_INCLUDE_SAMPLE_FEATURES` 等）会影响 `CONTEXT_DIM` 和共享内存布局，
> 需要与 Python 端 `STATE_DIM` 保持一致，详见仓库根目录的 `copilot-instructions`。

---

## Python 端统一 RL 脚本环境变量

### 算法选择
- **LOH_RL_ALGO**: 选择 RL 算法
  - 值: `PPO` | `SAC` | `TD3`
  - 默认: `SAC`

### Penalty 缩放模式
- **LOH_PENALTY_SCALE**: Penalty 缩放方式
  - 值: `reciprocal` | `log` | `survival`
  - 默认: `reciprocal`
  - `reciprocal`: 倒数缩放 1/max(d,1)
  - `log`: 对数缩放 1 - log1p(d)/log1p(dmax)
  - `survival`: 生存函数缩放 S(d) = 1 - F(d)

- **LOH_PENALTY_DMAX**: penalty 距离上限（用于 log 和 survival 模式）
  - 默认: `400000`

### Survival 模式特有参数
- **LOH_SURVIVAL_QUANTILE**: 高分位数阈值
  - 默认: `0.99`
- **LOH_SURVIVAL_BINS**: 直方图bins数量
  - 默认: `64`
- **LOH_SURVIVAL_MINCOUNT**: 最小样本数（冷启动阈值）
  - 默认: `1000`

### Reward 滑动窗口
- **LOH_REWARD_WINDOW**: 奖励滑动窗口大小
  - 默认: `0` （禁用）
  - 设置为 > 0 启用指数衰减滑动平均

### PPO 特有参数（前缀 PPO_）
- **PPO_BUFFER_SIZE**: 回放缓冲区大小（默认: 2048）
- **PPO_BATCH_SIZE**: 批次大小（默认: 64）
- **PPO_N_EPOCHS**: 每次更新的 epoch 数（默认: 10）
- **PPO_LEARNING_RATE**: 学习率（默认: 3e-4）
- **PPO_GAMMA**: 折扣因子（默认: 0.99）
- **PPO_GAE_LAMBDA**: GAE λ 参数（默认: 0.95）
- **PPO_CLIP_RANGE**: 裁剪范围（默认: 0.2）
- **PPO_ENT_COEF**: 熵系数（默认: 0.0）
- **PPO_VF_COEF**: 价值函数系数（默认: 0.5）
- **PPO_MAX_GRAD_NORM**: 梯度裁剪（默认: 0.5）
- **PPO_NET_ARCH**: 网络结构（默认: "256,256"）
- **PPO_ACTIVATION_FN**: 激活函数（relu/tanh/elu/leakyrelu，默认: relu）

### SAC 特有参数（前缀 SAC_）
- **SAC_BUFFER_SIZE**: 回放缓冲区大小（默认: 10000）
- **SAC_BATCH_SIZE**: 批次大小（默认: 256）
- **SAC_LEARNING_RATE**: 学习率（默认: 3e-4）
- **SAC_TAU**: 目标网络更新系数（默认: 0.005）
- **SAC_GAMMA**: 折扣因子（默认: 0.99）
- **SAC_TRAIN_FREQ**: 训练频率（默认: 16）
- **SAC_GRADIENT_STEPS**: 每次训练的梯度步数（默认: 1）
- **SAC_LEARNING_STARTS**: 开始学习的步数（默认: 3000）
- **SAC_ENT_COEF**: 熵系数（默认: "auto"）
- **SAC_TARGET_ENTROPY**: 目标熵（默认: -action_dim）
- **SAC_NET_ARCH**: 网络结构（默认: "256,256"）
- **SAC_ACTIVATION_FN**: 激活函数（默认: ReLU）

### TD3 特有参数（前缀 TD3_）
- **TD3_BUFFER_SIZE**: 回放缓冲区大小（默认: 10000）
- **TD3_BATCH_SIZE**: 批次大小（默认: 256）
- **TD3_LEARNING_RATE**: 学习率（默认: 3e-4）
- **TD3_TAU**: 目标网络更新系数（默认: 0.005）
- **TD3_GAMMA**: 折扣因子（默认: 0.99）
- **TD3_TRAIN_FREQ**: 训练频率（默认: 16）
- **TD3_GRADIENT_STEPS**: 每次训练的梯度步数（默认: 1）
- **TD3_LEARNING_STARTS**: 开始学习的步数（默认: 3000）
- **TD3_POLICY_DELAY**: 策略延迟更新（默认: 2）
- **TD3_TARGET_POLICY_NOISE**: 目标策略噪声（默认: 0.2）
- **TD3_TARGET_NOISE_CLIP**: 目标噪声裁剪（默认: 0.5）
- **TD3_ACTION_NOISE**: 探索噪声标准差（默认: None）
- **TD3_NET_ARCH**: 网络结构（默认: "256,256"）
- **TD3_ACTIVATION_FN**: 激活函数（默认: ReLU）

## 使用示例

### 使用 PPO 算法
```bash
LOH_RL_ALGO=PPO python scripts/loh_actor_critic_sb3.py
```

### 使用 TD3 + 对数 penalty 缩放
```bash
LOH_RL_ALGO=TD3 LOH_PENALTY_SCALE=log LOH_PENALTY_DMAX=500000 python scripts/loh_actor_critic_sb3.py
```

### 使用 SAC + 生存函数 penalty + reward 滑动窗口
```bash
LOH_RL_ALGO=SAC LOH_PENALTY_SCALE=survival LOH_REWARD_WINDOW=5 python scripts/loh_actor_critic_sb3.py
```

### 使用 PPO + reward 滑动窗口（模拟 RewardSlide 版本）
```bash
LOH_RL_ALGO=PPO LOH_REWARD_WINDOW=5 python scripts/loh_actor_critic_sb3.py
```

## 已完成的代码修改

1. ✅ 导入 PPO、SAC、TD3 模块
2. ✅ 添加 ProfiledPPO 和 ProfiledTD3 类
3. ✅ RetrospectiveReplayBuffer 中添加 penalty_scale_mode 支持
4. ✅ 实现 _penalty_scale()、_update_hist()、_cdf_from_hist()、_get_quantile_threshold() 方法
5. ✅ LohEnv 中添加 _reward_window 支持
6. ✅ step() 中实现 reward 滑动窗口逻辑
7. ✅ reset() 中清空 reward_window

## 待完成的工作

main() 函数中的算法选择逻辑需要根据 LOH_RL_ALGO 创建相应的模型。建议修改方式：

在 main() 函数的模型创建部分（约 3180 行），将现有的 ProfiledSAC 创建逻辑改为：

```python
# 根据算法类型读取相应的超参数并创建模型
algo_name = os.environ.get("LOH_RL_ALGO", "SAC").strip().upper()

if algo_name == "PPO":
    # 读取 PPO 超参数
    n_steps = _env_int("PPO_BUFFER_SIZE", 2048)
    batch_size = _env_int("PPO_BATCH_SIZE", 64)
    n_epochs = _env_int("PPO_N_EPOCHS", 10)
    # ... 其他 PPO 参数

    model = ProfiledPPO(
        "MlpPolicy",
        env,
        n_steps=n_steps,
        batch_size=batch_size,
        n_epochs=n_epochs,
        # ... 其他配置
    )

elif algo_name == "TD3":
    # 读取 TD3 超参数
    buffer_size = _env_int("TD3_BUFFER_SIZE", 10000)
    # ... 其他 TD3 参数

    model = ProfiledTD3(
        "MlpPolicy",
        env,
        buffer_size=buffer_size,
        # ... 其他配置
        replay_buffer_class=RetrospectiveReplayBuffer,
        replay_buffer_kwargs=dict(
            exclude_recent_steps=args.exclude_recent_steps,
            obj_penalty_weight=obj_penalty_weight,
            byte_penalty_weight=byte_penalty_weight,
        ),
    )

else:  # SAC（默认）
    # 现有的 SAC 创建逻辑
    model = ProfiledSAC(...)
```

## 兼容性说明

- 原有的独立脚本（loh_actor_critic_sb3_mr_*.py, loh_actor_critic_sb3_pen_*.py）可以保留作为参考
- 新的统一脚本通过环境变量提供了所有变体的功能
- 默认行为与原 loh_actor_critic_sb3.py 保持一致（SAC + reciprocal penalty）

## 测试建议

1. 测试默认配置（SAC + reciprocal）
2. 测试各算法切换（PPO/SAC/TD3）
3. 测试各 penalty 缩放模式（reciprocal/log/survival）
4. 测试 reward 滑动窗口功能
5. 测试组合配置（如 TD3 + log + reward_window）
