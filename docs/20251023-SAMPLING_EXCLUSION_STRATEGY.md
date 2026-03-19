# SAC采样排除策略说明

## 问题背景

在使用 Ghost Cache Miss 进行事后惩罚修正时，存在一个时间差问题：

1. **步骤 t**：对象被驱逐，权重版本为 `v_t`
2. **步骤 t+50**：该对象被重访（Ghost cache miss），检测到错误决策
3. **步骤 t+50 至 t+100**：惩罚信号传递给Python，修正buffer中版本`v_t`的奖励
4. **步骤 t+10**：如果此时恰好训练，可能采样到**未修正**的 `t` 到 `t+50` 之间的数据

## 两种解决方案

### 方案1：延迟训练（全局策略）

**实现位置**：SAC初始化参数

```python
learning_starts=5000,  # 前5000步不训练
train_freq=4,          # 每4步训练1次
gradient_steps=4,      # 每次训练4个梯度步
```

**原理**：
- 延迟训练启动，让早期数据有时间被修正
- 降低训练频率，给惩罚信号更多时间到达

**优点**：
- 简单，无需修改buffer实现
- 全局生效，对所有数据一视同仁

**缺点**：
- 牺牲sample efficiency（训练频率降低）
- 无法精确控制哪些数据可以采样

---

### 方案2：采样时排除最新数据（精确控制）✅

**实现位置**：`RetrospectiveReplayBuffer.sample()`

```python
class RetrospectiveReplayBuffer(ReplayBuffer):
    def __init__(self, *args, exclude_recent_steps=200, **kwargs):
        super().__init__(*args, **kwargs)
        self.exclude_recent_steps = exclude_recent_steps
        self.excluded_samples = 0  # 统计排除次数

    def sample(self, batch_size, env=None):
        """采样时跳过最新的exclude_recent_steps个数据"""
        effective_size = self.size()
        if effective_size <= self.exclude_recent_steps:
            return super().sample(batch_size, env)

        # 只从 [0, size - exclude_recent_steps) 采样
        max_sample_idx = effective_size - self.exclude_recent_steps

        if self.pos < self.buffer_size:
            # Buffer未满：采样 [0, max_sample_idx)
            upper = min(self.pos, max_sample_idx)
            batch_inds = np.random.randint(0, upper, size=batch_size)
        else:
            # Buffer已满（环形）：采样 [pos, pos + count)
            start = self.pos % self.buffer_size
            count = self.buffer_size - self.exclude_recent_steps
            batch_inds = (start + np.random.randint(0, count, size=batch_size)) % self.buffer_size
            self.excluded_samples += 1

        return self._get_samples(batch_inds, env=env)
```

**原理**：
- 在采样时动态计算"安全区域"（已存在足够久的数据）
- 只从安全区域采样，确保数据已被修正

**优点**：
- 精确控制，不影响训练频率
- 灵活可调（通过`--exclude-recent-steps`参数）
- 不牺牲sample efficiency（训练次数不变）

**缺点**：
- 需要修改ReplayBuffer实现
- 如果buffer太小或排除窗口太大，可能导致可采样数据不足

---

## 当前实现：双重保护策略

### 参数配置

```python
# SAC初始化
model = SAC(
    ...,
    learning_starts=5000,      # 方案1：延迟训练
    train_freq=4,              # 方案1：降低训练频率
    gradient_steps=4,          # 保持训练总量
    replay_buffer_class=RetrospectiveReplayBuffer,
    replay_buffer_kwargs=dict(
        exclude_recent_steps=200,  # 方案2：采样排除
    ),
)
```

### 时序示例

```
步骤 1000: 驱逐对象A，state_version=1000
步骤 1050: 对象A重访（Ghost cache miss）
步骤 1050-1100: penalty传递并修正buffer[1000]的奖励

--- 方案1保护：learning_starts=5000 ---
步骤 1-4999: 不训练，只收集数据
步骤 5000+: 开始训练

--- 方案2保护：exclude_recent_steps=200 ---
步骤 5001训练: 采样范围 [0, 4801)，排除 [4802, 5001]
步骤 5005训练: 采样范围 [0, 4805)，排除 [4806, 5005]
```

### 保护效果

| 数据状态 | 方案1保护 | 方案2保护 | 综合效果 |
|---------|----------|----------|---------|
| 步骤1000的transition | ✅ 在5000步前已修正 | ✅ 采样时总是在安全区 | ✅✅ 双重保护 |
| 步骤4900的transition | ❌ 可能未修正 | ✅ 排除最新200步 | ✅ 方案2保护 |
| 步骤5000的transition | ❌ 刚加入buffer | ✅ 排除最新200步 | ✅ 方案2保护 |

---

## 调参建议

### 1. 根据Ghost cache miss延迟调整

**测量方法**：

```bash
# 从日志中提取驱逐和重访的时间差
grep "Ghost cache miss" cachesim_*.log | head -20
```

**调参策略**：

| Ghost miss 平均延迟 | exclude_recent_steps | 说明 |
|-------------------|---------------------|------|
| < 100步 | 100-150 | 惩罚快速到达，排除窗口可以较小 |
| 100-300步 | 200-300 | 默认配置，适合大多数场景 |
| > 300步 | 400-500 | 惩罚延迟大，需要更大保护窗口 |

### 2. 根据buffer大小调整

```python
buffer_size = 100000
exclude_recent_steps = 200

# 确保有足够数据可采样
assert buffer_size - exclude_recent_steps > 5000, "可采样数据不足"
```

**经验公式**：

```
exclude_recent_steps <= buffer_size * 0.02  # 不超过2%
```

### 3. 监控排除效果

在训练中检查统计信息：

```python
stats = model.replay_buffer.get_correction_stats()
print(f"Excluded samples: {stats['excluded_samples']}")
```

**判断标准**：
- `excluded_samples=0`：排除窗口太小，没有起作用
- `excluded_samples >> training_rounds`：排除过于频繁，可能窗口太大

---

## 性能影响分析

### 方案1：延迟训练

**优点**：
- 实现简单，不需修改buffer
- 对算法透明，不引入额外复杂度

**缺点**：
- 降低sample efficiency：`train_freq=4` 意味着训练次数减少75%
- 需要更多环境交互才能达到同样训练量

### 方案2：采样排除

**优点**：
- 不影响训练频率和总量
- 精确控制数据质量

**缺点**：
- 略微降低采样随机性（排除了一部分数据）
- 增加少量计算开销（每次采样需计算范围）

### 综合效果（方案1+2）

| 指标 | 纯SAC | +方案1 | +方案2 | 方案1+2 |
|------|-------|--------|--------|---------|
| 数据质量 | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Sample Efficiency | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| 实现复杂度 | ⭐ | ⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| 适用场景 | 无延迟奖励 | 中等延迟 | 高延迟 | 强学分分配 |

---

## 实验验证

### 测试命令

```bash
# 基准测试（只有方案1）
python scripts/loh_actor_critic_sb3.py \
    --learning-starts 5000 \
    --exclude-recent-steps 0

# 完整配置（方案1+2）
python scripts/loh_actor_critic_sb3.py \
    --learning-starts 5000 \
    --exclude-recent-steps 200
```

### 预期结果

**日志关键字**：

```
✏️ [RETROSPECTIVE] reward corrected...
   - state_version: 1000
   - original_reward: 0.850000
   - penalty: 0.500000
   - corrected_reward: 0.350000
   - delta: -0.500000

Correction stats: {'corrections': 42, 'excluded_samples': 15, ...}
```

**性能指标**：

| 配置 | Miss Rate | Convergence Speed | Reward Variance |
|------|-----------|-------------------|-----------------|
| 方案1 only | 45% | 中 | 高（用了未修正数据） |
| 方案2 only | 43% | 快 | 中 |
| **方案1+2** | **42%** | **中** | **低（最稳定）** |

---

## 总结

✅ **推荐配置**（当前实现）：

```python
# 训练模式
learning_starts = 5000        # 给足时间修正早期数据
train_freq = 4                # 不要每步训练
gradient_steps = 4            # 保持训练总量
exclude_recent_steps = 200    # 采样时排除最新200步

# 推理模式（可选）
exclude_recent_steps = 0      # 推理时无需排除（不训练）
```

📊 **适用场景**：
- ✅ 有延迟奖励信号（如Ghost cache miss）
- ✅ 学分分配困难（决策与奖励时间差大）
- ✅ 需要高质量训练数据
- ❌ 无延迟奖励（标准RL问题）→ 用普通ReplayBuffer即可

🔧 **调试技巧**：
1. 先测量Ghost miss延迟分布
2. 设置 `exclude_recent_steps` 为延迟的1-2倍
3. 监控 `excluded_samples` 统计
4. 比较修正前后的reward variance

---

© 自动生成：LOH Retrospective Penalty System
