# Reward差异性与训练效率改进方案

## 问题分析

### 1. Reward普遍接近1（缺乏差异性）
**原因**：
- `penalty_data`大多为0（penalties还没到达或对象未被重访问）
- `corrected_hit_ratio ≈ 1.0 - 0.0 = 1.0`
- `final_reward = pow(1.0, 5.0) = 1.0`

**结果**：
- 模型无法区分好坏决策
- 训练信号微弱，学习困难

### 2. Learning_starts与batch_size不匹配
- `learning_starts=100`：100步后开始训练
- `batch_size=256`：但buffer里只有100个样本！
- **问题**：batch采样会重复使用样本（bootstrap采样），降低训练质量

### 3. 缓存满后第一个周期数据被reset浪费
- Reset时reset()消耗了seq=1作为初始观察
- 但这个周期可能包含重要的驱逐信息（缓存刚满时的驱逐行为）

---

## 解决方案

### 方案1：改进Reward归一化（推荐）

#### 当前问题
```python
# 当前逻辑
corrected_hit_ratio = 1.0 - weighted_sum  # weighted_sum通常很小(~0.001)
final_reward = pow(corrected_hit_ratio, 5.0)  # pow(0.999, 5) ≈ 0.995
```

**问题**：
- Penalty太小（因为归一化：1/evicted_count）
- Hit_ratio本身已经很高（0.6-0.9）
- 差异被pow()放大但基数太接近

#### 改进方案A：不使用pow，直接用penalty作为负reward
```python
# 基础reward：命中率
base_reward = obj_hit_ratio  # 0.6-0.9

# 惩罚：不归一化，直接累加
penalty_sum = 0.0
for (eviction_to_access, obj_size) in penalty_data:
    # 每个过早驱逐的惩罚：与距离成反比
    penalty_sum += 1.0 / eviction_to_access

# 最终reward = 基础reward - 惩罚系数 * penalty
final_reward = base_reward - (penalty_coefficient * penalty_sum)
```

**优点**：
- 直接、线性的惩罚信号
- Penalty越多，reward越低
- 差异性明显

**参数**：
- `penalty_coefficient = 0.01`（可调）：控制penalty的影响力

#### 改进方案B：使用miss_ratio的相对变化
```python
# 计算实际miss_ratio（考虑penalty修正）
actual_misses = epoch_misses + len(penalty_data)  # 加上过早驱逐
actual_miss_ratio = actual_misses / epoch_requests

# 相对于baseline的改进
baseline_miss_ratio = 0.5  # 假设的baseline
improvement = (baseline_miss_ratio - actual_miss_ratio) / baseline_miss_ratio

# Reward = improvement（可为负）
final_reward = improvement
```

**优点**：
- Reward可以为负（更强的信号）
- 相对变化更明显

#### 改进方案C：组合方案（最推荐）
```python
# 1. 基础reward：命中率
base_reward = obj_hit_ratio

# 2. Penalty惩罚（放大系数）
penalty_term = 0.0
if evicted_count > 0:
    for (distance, size) in penalty_data:
        # 每个penalty贡献 1/(distance * sqrt(evicted_count))
        # 使用sqrt减少归一化的影响
        penalty_term += 1.0 / (distance * math.sqrt(evicted_count))

# 3. 组合（使用可调系数）
penalty_weight = 0.1  # 可调参数
final_reward = base_reward - penalty_weight * penalty_term

# 4. 限制范围
final_reward = max(-1.0, min(1.0, final_reward))
```

---

### 方案2：调整exclude_recent_steps

#### 当前设置
- `exclude_recent_steps=20`：排除最近20步
- 问题：penalties可能在20步后很久才到达

#### 建议
- **增加到100-200**：让更多penalties到达后再计算final_reward
- 代价：训练延迟增加
- 好处：reward更准确

#### 动态exclude策略
```python
# 根据buffer填充程度动态调整
if buffer.full:
    exclude_steps = 200  # Buffer满后，有足够样本，可以等更久
else:
    exclude_steps = 50   # Buffer未满时，尽快开始训练
```

---

### 方案3：修复learning_starts与batch_size匹配

#### 当前问题
```
learning_starts = 100
batch_size = 256  # > learning_starts!
```

#### 解决方案
```python
# 方案A：增加learning_starts
learning_starts = max(batch_size * 4, 1000)  # 至少是batch_size的4倍

# 方案B：动态batch_size
if buffer.size() < batch_size:
    actual_batch_size = buffer.size()
else:
    actual_batch_size = batch_size
```

#### 推荐配置
```python
buffer_size = 10000
learning_starts = 1000  # 10% buffer填充后开始
batch_size = 256
exclude_recent_steps = 100  # 留足时间等penalties
```

---

### 方案4：利用reset时的初始数据

#### 当前问题
Reset时消耗seq=1作为初始观察，不存入buffer

#### 解决方案A：在reset后立即add一个transition
```python
def reset(self):
    # ... 等待initial_data ...
    initial_obs = self._build_observation(initial_data)

    # 【新增】如果不是第一次reset，将上一个episode的最后状态存入buffer
    if hasattr(self, '_last_obs') and self._last_obs is not None:
        # 存储 (last_obs, initial_obs, dummy_action, terminal_reward)
        # 这样可以利用episode边界的信息
        info = {
            'state_version': int(initial_data.state_version),
            'total_evicted_bytes': initial_data.total_evicted_bytes,
            'total_evicted_count': initial_data.total_evicted_count,
        }
        # Note: 需要通过model.replay_buffer手动add

    self._last_obs = initial_obs
    return initial_obs
```

#### 解决方案B：不reset，连续运行
```python
# 移除episode概念，让环境连续运行
# truncated条件改为永不truncate
# 这样所有数据都被利用
```

---

### 方案5：Reward shaping（高级）

#### 多目标reward
```python
# 组合多个指标
reward = (
    w1 * obj_hit_ratio +           # 对象命中率
    w2 * byte_hit_ratio +          # 字节命中率
    w3 * (-penalty_normalized) +   # 惩罚（归一化）
    w4 * cache_efficiency          # 缓存利用率
)
```

#### Potential-based shaping
```python
# 定义potential函数（基于状态的价值估计）
def potential(state):
    return state.obj_hit_ratio + state.cache_fill_ratio

# Shaped reward
shaped_reward = reward + gamma * potential(next_state) - potential(state)
```

---

## 推荐实施顺序

### 第一阶段（立即实施）
1. **修改reward计算**（方案C）：
   - 去除pow()
   - 使用线性组合：`base_reward - penalty_weight * penalty_term`
   - 使用sqrt(evicted_count)减少归一化影响

2. **调整超参数**：
   ```python
   learning_starts = 1000  # 增加到batch_size的4倍
   exclude_recent_steps = 100  # 增加到100
   penalty_weight = 0.1  # 新增惩罚权重参数
   ```

### 第二阶段（观察效果后）
3. **动态exclude_steps**：
   - 根据buffer填充程度调整

4. **利用reset数据**：
   - 方案B：移除episode概念，连续运行

### 第三阶段（可选）
5. **多目标reward**：
   - 组合cache_efficiency等其他指标

---

## 实施代码

### 修改1：Reward计算（scripts/loh_actor_critic_sb3.py）

```python
# 在compute_final_rewards()中
import math

# 计算惩罚（新方法）
penalty_score = 0.0
for (eviction_to_access, obj_size) in self.penalty_data[pos]:
    # 使用sqrt减少归一化影响
    if evicted_count > 0:
        penalty_score += 1.0 / (eviction_to_access * math.sqrt(evicted_count))
    else:
        # 如果没驱逐但有penalty（不应该发生），直接用距离倒数
        penalty_score += 1.0 / eviction_to_access

# 基础reward（命中率）
base_reward = initial_reward  # 已经是加权命中率

# 最终reward = 基础 - 惩罚
penalty_weight = 0.1  # 可配置
final_reward = base_reward - penalty_weight * penalty_score

# 限制范围[-1, 1]
final_reward = max(-1.0, min(1.0, final_reward))
```

### 修改2：超参数（main函数）

```python
parser.add_argument("--learning-starts", type=int, default=1000,
                   help="Steps before training starts (default: 1000)")
parser.add_argument("--exclude-recent-steps", type=int, default=100,
                   help="Exclude recent N steps (default: 100)")
parser.add_argument("--penalty-weight", type=float, default=0.1,
                   help="Weight for penalty in reward (default: 0.1)")
```

### 修改3：动态batch_size（SAC配置）

```python
# 使用ReplayBuffer的wrapper支持动态batch
class DynamicBatchWrapper:
    def sample(self, batch_size):
        actual_size = min(batch_size, self.size())
        return super().sample(actual_size)
```

---

## 预期效果

### Reward分布
- **改进前**：reward ∈ [0.95, 1.0]，缺乏差异
- **改进后**：reward ∈ [-0.5, 1.0]，差异明显

### 训练稳定性
- Learning_starts匹配batch_size：减少初期训练不稳定
- Exclude_steps增加：reward更准确

### 样本利用率
- 利用reset数据：增加5-10%样本
- 连续运行：100%样本利用

---

## 监控指标

训练时关注：
1. **Reward标准差**：应该从~0.01增加到~0.2
2. **Penalty覆盖率**：有多少%的样本有非零penalty
3. **训练loss**：是否下降
4. **Cache性能**：miss_ratio是否改善
