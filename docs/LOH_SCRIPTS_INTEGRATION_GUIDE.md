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

## Teacher 训练流程详解（当前使用模式，非 RL）

本节描述你最近在做的 `train_loh_teacher_ranker.py` 路线，分为「样本收集 → 监督训练 → 固定权重评测」。

### 结论先说

- 这条流程不是 RL 训练。
- 它是离线监督学习（imitation/ranking）：用 `loh-teacher` 导出的 Belady 标签样本训练 6 维线性权重。
- 评测时也是固定权重推理，不与 Python Actor-Critic 交互。

### 0) 为什么说不是 RL

- 样本收集阶段设置 `LOH_ENABLE_RL=0`，且算法使用 `loh-teacher`。
- 训练阶段执行的是 `scripts/train_loh_teacher_ranker.py`（PyTorch 监督训练），不是 `loh_actor_critic_sb3.py`。
- 评测阶段设置 `LOH_ENABLE_RL=0` + `LOH_FIXED_WEIGHTS=...`，直接用 C 端线性打分。

### 1) 样本收集（teacher label export）

输入：某条 trace（例如 1063/wiki/meta）。

执行方式（可参考 `scripts/run_loh_teacher_train_and_eval_fixed_3m.sh`）：

- `LOH_ENABLE_RL=0`
- `LOH_TEACHER_EXPORT_PATH=<run_dir>/teacher_samples.csv`
- `LOH_TEACHER_EXPORT_MAX_ROWS` 控制导出上限
- 运行：`_build_dbg/bin/cachesim <trace> oracleGeneral loh-teacher 0.1 --num-req=3000000 ...`

输出：`teacher_samples.csv`（按 eviction group 组织，含 `feature0..5`、`is_teacher`、可选 `belady_key`）。

### 2) 训练前特征对齐（关键）

`scripts/train_loh_teacher_ranker.py` 不直接用 raw `feature0..5`，而是先映射到和 C 端一致的 score-space：

- 读取模式开关：`LOH_SCORE_USE_COMPOUND`、`LOH_SCORE_USE_IRT`、`LOH_FEATURE_LOG1P`、`LOH_USE_HEURISTIC_SIGNS`
- 在 compound=1 时构造 `[rec, freq, size, freq/rec(或乘), freq/size(或乘), rec*size]`
- 按部署语义应用符号（`apply_sign_to_features`）

这一步用于避免“离线训练空间”和“线上打分空间”不一致导致的失真。

### 3) 监督目标与优化

每个 eviction group 是一个候选集合，设：

- 候选特征矩阵为 $X \in \mathbb{R}^{K \times 6}$（$K$ 为该组候选数）
- 可训练参数为 $w \in \mathbb{R}^{6}$
- 组标签分布为 $y \in [0,1]^K$，且 $\sum_i y_i=1$

具体执行步骤如下：

1. **打分（group 内）**
  - 计算 `logits = X @ w`，得到该组每个候选的分数。

2. **主损失（group cross-entropy）**
  - 主项是组内交叉熵：$L_{ce}=CE(logits, y)$。
  - `y` 的构造优先使用 `belady_key` 最大值（并列时为 soft label），没有 `belady_key` 时回退到 `is_teacher` one-hot。

3. **可选 pairwise 排序项（--pairwise-lambda）**
  - 从正样本集合与负样本集合采样，优化正样本分数高于负样本。
  - 形式是 `softplus(neg_logit - pos_logit)` 的平均，记为 $L_{pw}$。
  - 组损失变为：$L = L_{ce} + \lambda_{pw}L_{pw}$。

4. **可选 L1 正则（--l1-lambda）**
  - 增加参数稀疏约束：$\lambda_{l1}\|w\|_1$。

5. **可选防塌缩项（--entropy-lambda）**
  - 对 $p=softmax(w)$ 增加：$\lambda_{ent}\sum_i p_i\log(p_i)$。
  - 该项越小代表分布越“均匀”，用于抑制单维独占（权重塌缩）。

6. **批训练与更新**
  - 以 group 为 batch 单位求平均损失，`Adam` 反向传播更新。
  - 若启用 `--nonnegative`，每个优化步后执行投影：`w = max(w, 0)`。

7. **训练后归一化（--l1-normalize）**
  - 若启用，则输出前执行：$w \leftarrow w / \sum_i |w_i|$。

最终目标可写为：

$$
L_{total}=L_{ce}+\lambda_{pw}L_{pw}+\lambda_{l1}\|w\|_1+\lambda_{ent}\sum_i p_i\log(p_i),\quad p=softmax(w)
$$

### 4) 单 trace 与多 trace 两种训练模式

- 单 trace：`--csv <one_csv>`
  - 只用一条 trace 的样本训练一个权重。
- 多 trace 平衡：`--csv-list a.csv,b.csv,c.csv`
  - 先分别读每条 trace 的 group；
  - 每条取相同数量（受最小可用组数与 `--max-groups` 均分限制）；
  - 合并后打乱训练，得到通用权重。

### 5) 线上评测（固定权重）

训练完写出 6 维权重文本后，评测流程为：

- `LOH_ENABLE_RL=0`
- `LOH_FIXED_WEIGHTS=<w1..w6>`
- 保持与训练一致的特征开关（尤其 `compound/log1p/sign/normalize`）
- 运行：`_build_dbg/bin/cachesim <trace> oracleGeneral LOH 0.1 --num-req=3000000 --eviction-params=miss-ratio-weight=1.0`

输出关注：最终 `miss ratio` 与 `byte miss ratio`。

### 6) 你最近遇到的 1063 异常（对应现象）

- 某次单 trace 1063 训练出现权重塌缩到近单维，导致线上 miss ratio 显著变差。
- wiki/meta 没有同等程度塌缩，因此看起来“正常”。
- 增加 `--entropy-lambda` 后，1063 权重分布恢复为多维组合，线上结果有明显回升。

## Teacher 的 RL 训练路径（新增，监督版保留）

为满足“Teacher 使用强化学习训练（且保留原监督版本）”，已新增脚本：

- `scripts/train_loh_teacher_ranker_rl.py`

说明：

1. 该脚本复用 `train_loh_teacher_ranker.py` 的样本读取与 score-space 特征对齐逻辑。
2. 优化方法为 REINFORCE（策略梯度）：
   - 策略：对每个 eviction group 的候选分数做 `softmax` 形成离散分布；
   - 动作：按分布采样一个候选；
   - 奖励：`hard` 模式下选中 teacher 候选得 1 否则 0；`soft` 模式下用 soft-label 值作为奖励；
   - 更新：最大化期望奖励，含 baseline（EMA）和熵正则（`--entropy-coef`）。
3. 输出仍是 6 维固定权重，可直接用于 `LOH_FIXED_WEIGHTS` 线上评测。
4. 原监督脚本 `scripts/train_loh_teacher_ranker.py` 保持不变，可继续并行使用。

快速示例：

```bash
python3 scripts/train_loh_teacher_ranker_rl.py \
  --csv runs/teacher_xxx/teacher_samples.csv \
  --out runs/teacher_xxx/teacher_weights_rl.txt \
  --episodes 3000 \
  --batch-groups 512 \
  --lr 3e-3 \
  --entropy-coef 1e-2 \
  --nonnegative \
  --l1-normalize \
  --eval-final-top1
```

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
