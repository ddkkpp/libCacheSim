# SAC + 事后奖励修正方案

## 🎯 核心改进

从 **PPO (on-policy)** 切换到 **SAC (off-policy)** + 自定义 ReplayBuffer，支持事后修正历史奖励。

---

## ✅ 已实现的功能

### 1. 自定义 ReplayBuffer (`RetrospectiveReplayBuffer`)

```python
class RetrospectiveReplayBuffer(ReplayBuffer):
    """支持事后修正奖励的 ReplayBuffer"""

    # 核心功能：
    # 1. 维护 version -> buffer_position 映射
    # 2. 允许事后修正任意version的奖励
    # 3. SAC采样时自动使用修正后的奖励
```

**关键方法**：

- `add()`: 存储transition时记录state_version映射
- `retrospective_correct_reward(state_version, penalty)`: 事后修正指定version的奖励
- `get_correction_stats()`: 获取修正统计信息

### 2. 奖励修正机制

#### 当前实现（方案2 + Buffer修正）

```python
# 在 step() 中：
# 1. 计算即时奖励
immediate_reward = alpha * obj_hit_ratio + beta * byte_hit_ratio

# 2. 滑动窗口平滑（已有）
smoothed_reward = weighted_average(window, decay_weights)

# 3. 返回给SAC（存入buffer）
return obs, smoothed_reward, done, truncated, info

# 【预留】未来扩展：C端检测到延迟惩罚时
# model.replay_buffer.retrospective_correct_reward(
#     state_version=5,  # 哪个version的决策造成了Miss
#     penalty=0.8       # 惩罚值
# )
```

---

## 📊 与PPO版本的对比

| 特性 | PPO（旧版） | SAC（新版） |
|------|------------|------------|
| **算法类型** | On-policy | Off-policy |
| **Buffer类型** | RolloutBuffer（只写） | ReplayBuffer（可读写） |
| **奖励修正** | ❌ 不支持 | ✅ 支持事后修正 |
| **样本效率** | 低（每次rollout后丢弃） | 高（经验回放） |
| **训练稳定性** | 较高（PPO clip） | 中等（需调参） |
| **超参数** | n_steps, batch_size, n_epochs | buffer_size, learning_starts |
| **收敛速度** | 较慢 | 较快（off-policy） |

---

## 🔧 SAC 超参数配置

```python
SAC(
    buffer_size=100000,      # replay buffer容量（默认100k）
    learning_rate=3e-4,      # 学习率
    batch_size=256,          # 梯度batch大小
    tau=0.005,               # 目标网络软更新系数
    gamma=0.99,              # 折扣因子
    train_freq=1,            # 每步训练一次
    gradient_steps=1,        # 每次训练1个梯度步
    learning_starts=1000,    # 预热步数（默认1000）
    replay_buffer_class=RetrospectiveReplayBuffer,  # 自定义buffer
)
```

### 参数说明

#### `buffer_size` (100000)
- **作用**：ReplayBuffer 容量
- **权衡**：
  - 太小：无法捕获足够的延迟反馈
  - 太大：显存占用高，旧样本权重过大
- **推荐**：100k-500k（根据显存）

#### `learning_starts` (1000)
- **作用**：收集多少样本后开始训练
- **权衡**：
  - 太小：初期样本质量差
  - 太大：浪费时间
- **推荐**：1000-5000

#### `train_freq` (1)
- **作用**：每隔多少环境步训练一次
- **当前**：每步都训练（最积极）
- **可选**：设为4或8减少计算

#### `gradient_steps` (1)
- **作用**：每次训练时的梯度更新次数
- **当前**：1（保守）
- **可选**：增大到2-4加快学习

---

## 🚀 使用方法

### 基本运行

```bash
# 使用默认配置
bash ./scripts/test_loh_rl_sb3.sh <trace> 26 <cache_size> <miss_ratio_weight>

# 示例
bash ./scripts/test_loh_rl_sb3.sh \
    data/MetaCDN/meta_reag.oracleGeneral.zst \
    26 \
    1073741824 \
    1.0
```

### 自定义SAC参数

```bash
# 修改 scripts/loh_actor_critic_sb3.py 中的 main() 函数
# 或通过命令行参数：

python3 scripts/loh_actor_critic_sb3.py \
    --miss-ratio-weight 1.0 \
    --buffer-size 200000 \
    --learning-starts 2000
```

---

## 📈 监控与调试

### 查看训练日志

```bash
# Python端日志
tail -f ac_sb3_*.log | grep -E "SAC|ReplayBuffer|Corrected"

# 关键输出：
# [ReplayBuffer] Added transition at pos=X, version=Y
# [ReplayBuffer] Corrected version=5 at pos=123: 0.8234 -> 0.7234 (penalty=0.1)
```

### 修正统计

```python
# 在训练中定期打印
stats = model.replay_buffer.get_correction_stats()
print(f"Reward corrections: {stats['corrections']}")
print(f"Average penalty: {stats['avg_penalty']:.4f}")
```

---

## 🔮 未来扩展：完整的事后修正

### 当前限制
当前版本只有滑动窗口平滑，**未启用真正的事后修正**（因为需要C端支持）。

### 完整实现需要：

#### 1. C端修改（未实现）

```c
// 在 LOH.c 中添加
typedef struct {
    // ... 现有字段 ...

    // 延迟惩罚信号
    int has_delayed_penalty;      // 是否有延迟惩罚
    uint64_t penalty_version;     // 哪个version造成的
    double penalty_value;         // 惩罚值
} shm_data_t;

// 在 LOH_get() 中检测Miss
if (obj == NULL && /* 发现是历史驱逐造成的 */) {
    params->shm_data->has_delayed_penalty = 1;
    params->shm_data->penalty_version = rec->state_version;
    params->shm_data->penalty_value = penalty;
}
```

#### 2. Python端调用（已实现，待激活）

```python
def step(self, action):
    # ... 现有逻辑 ...

    data = self._read_shm()

    # 【未来扩展】检测延迟惩罚信号
    if hasattr(data, 'has_delayed_penalty') and data.has_delayed_penalty:
        # 事后修正ReplayBuffer
        if hasattr(self, 'replay_buffer'):
            self.replay_buffer.retrospective_correct_reward(
                state_version=int(data.penalty_version),
                penalty=float(data.penalty_value)
            )
            # 清除信号
            data.has_delayed_penalty = 0
            self._write_shm(data)

    return obs, reward, done, truncated, info
```

---

## ⚠️ 注意事项

### 1. Buffer循环覆盖
```python
# ReplayBuffer 是循环buffer
# 如果 buffer_size=100k，第100001个sample会覆盖第1个
# → 延迟惩罚必须在被覆盖前发送！

# 建议：
# - C端检测到Miss后，立即发送惩罚信号（不要累积）
# - 或增大 buffer_size
```

### 2. Version映射失效
```python
# 如果buffer已满并循环，老的version映射会失效
# RetrospectiveReplayBuffer 会检测并跳过无效修正
```

### 3. 训练不稳定风险
```python
# 事后修正可能导致：
# - 同一transition的奖励被多次修改
# - 破坏样本的时间一致性

# 缓解方法：
# - 限制每个transition最多修正1次
# - 修正后标记，避免重复
```

---

## 📝 实验建议

### 阶段1：验证SAC基础版本（当前）
```bash
# 运行1-2小时，观察：
# 1. SAC是否能正常训练（loss曲线）
# 2. 奖励是否比PPO更稳定
# 3. 收敛速度是否更快
```

### 阶段2：对比PPO（可选）
```bash
# 恢复PPO版本运行，对比：
# - 样本效率（相同steps下的性能）
# - 最终性能（长时间训练后的Miss率）
# - 训练稳定性（reward variance）
```

### 阶段3：实现完整事后修正（需要C端支持）
```bash
# 1. 修改LOH.c添加惩罚信号
# 2. 扩展共享内存结构
# 3. 激活Python端的修正逻辑
# 4. 验证修正统计
```

---

## 🎓 理论基础

### 为什么SAC适合这个问题？

1. **Off-policy特性**
   - 可以从旧样本中学习
   - 支持经验回放
   - → 完美支持事后修正

2. **连续动作空间**
   - LOH的权重是连续值
   - SAC原生支持连续动作
   - → 无需离散化

3. **熵正则化**
   - 鼓励探索
   - 避免过早收敛到次优策略
   - → 适合缓存这种高噪声环境

### 学分分配问题的解决

```
传统方法（PPO）：
  t=5: 做决策 A_5 → 得到 R_5（错位！）

SAC + 事后修正：
  t=5:  做决策 A_5 → 得到 R_5 → 存入buffer[pos=5]
  t=10: 检测到 A_5 造成了Miss → buffer[pos=5].reward -= penalty
  t=15: SAC采样时，读到修正后的reward训练

→ 正确的因果关系！
```

---

## 📚 参考资料

- [Soft Actor-Critic (SAC) 论文](https://arxiv.org/abs/1801.01290)
- [Stable-Baselines3 SAC文档](https://stable-baselines3.readthedocs.io/en/master/modules/sac.html)
- [Hindsight Experience Replay (HER)](https://arxiv.org/abs/1707.01495) - 类似的"事后修正"思想

---

**总结**：当前版本已经切换到SAC并实现了RetrospectiveReplayBuffer的基础设施。滑动窗口平滑继续生效。完整的事后修正功能已预留接口，待C端支持后即可激活。
