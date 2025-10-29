# LOH惩罚机制重新设计方案

## 当前问题分析

### 问题1：惩罚值基于错误的时间距离
**当前实现**：
```c
int64_t revisit_distance = params->current_timestamp - ghost_entry->last_access_counter;
double penalty = 1.0 / (1.0 + (double)revisit_distance / 1000.0);
```

**问题**：
- `last_access_counter`是对象**被驱逐前的最后访问时间**
- `revisit_distance`计算的是"**重访间隔**"（被驱逐前最后访问 → 当前访问）
- 但真正的错误是"**驱逐到再次访问的距离**"（驱逐时间 → 当前访问）

**正确应该用**：
```c
int64_t eviction_to_access = params->current_timestamp - <驱逐时刻的timestamp>;
```

### 问题2：惩罚值与reward量纲不一致
**当前实现**：
```python
# Python端：直接从reward减去penalty
corrected_reward = original_reward - penalty
```

**问题**：
- `reward`是命中率（0-1之间）
- `penalty`是基于请求数量计算的（0-1之间，但含义完全不同）
- 直接相减没有物理意义

### 问题3：原reward统计被污染
**当前实现**：
- 每个RL step的reward基于整个epoch（200个请求）的miss_ratio
- 但被驱逐对象的miss可能只是200个请求中的1个
- 直接减去penalty会过度惩罚

---

## 解决方案

### 方案A：最简单 - 归一化惩罚为miss_ratio增量（推荐）

**核心思想**：将惩罚转换为"如果这次miss不发生，miss_ratio会降低多少"

#### C端修改（LOH.c）

```c
// 在LOH_get()中检测ghost cache miss时
if (ghost_entry && params->is_warmed_up && ghost_entry->eviction_version > 0) {
  // 计算驱逐到再次访问的距离
  int64_t eviction_to_access = params->current_timestamp - ghost_entry->last_access_counter;
  // 注意：这里仍然用last_access_counter，但我们用它作为驱逐时刻的近似
  // 更准确的做法是在ghost_entry中额外存储eviction_timestamp

  // 【新方案】惩罚值 = 1.0 / rl_update_interval（单次miss的影响）
  // 因为每个epoch有rl_update_interval个请求，1次miss造成miss_ratio增加1/rl_update_interval
  double single_miss_penalty = 1.0 / (double)params->rl_update_interval;

  // 【可选】根据驱逐到访问距离调整惩罚权重
  // 距离越短 → 权重越大（说明驱逐决策错误很明显）
  double distance_weight = 1.0;
  if (eviction_to_access < 100) {
    distance_weight = 2.0;  // 很快就被访问 → 严重错误
  } else if (eviction_to_access < 500) {
    distance_weight = 1.5;
  } else if (eviction_to_access < 1000) {
    distance_weight = 1.0;
  } else {
    distance_weight = 0.5;  // 很久之后才访问 → 驱逐决策可能合理
  }

  double penalty = single_miss_penalty * distance_weight;

  enqueue_penalty(params, ghost_entry->eviction_version, penalty, req->obj_id);

  LOH_DEBUG_PRINT_BASIC(
    "[LOH] Ghost miss: obj_id=%lu, evict_version=%lu, "
    "evict_to_access=%ld, base_penalty=%.6f, weight=%.2f, final_penalty=%.6f\n",
    req->obj_id, ghost_entry->eviction_version, eviction_to_access,
    single_miss_penalty, distance_weight, penalty
  );
}
```

#### Python端修改（loh_actor_critic_sb3.py）

```python
def retrospective_correct_reward(self, state_version, penalty):
    """
    事后修正奖励：penalty现在表示miss_ratio的增量

    修正逻辑：
    - 原reward = hit_ratio = 1 - miss_ratio
    - 如果这次miss不发生：new_miss_ratio = miss_ratio - penalty
    - 修正后的reward = 1 - new_miss_ratio = (1 - miss_ratio) + penalty
    """
    if state_version not in self.version_to_pos:
        if LOH_DEBUG_VERBOSE():
            print(f"[ReplayBuffer] Version {state_version} not in buffer")
        return False

    pos = self.version_to_pos[state_version]

    if not self.full and pos >= self.pos:
        if LOH_DEBUG_VERBOSE():
            print(f"[ReplayBuffer] Position {pos} invalid")
        return False

    # 修正奖励：加上penalty（因为避免了miss，hit_ratio应该更高）
    original_reward = float(self.rewards[pos, 0])
    corrected_reward = original_reward + penalty  # ⚠️ 改为加号
    self.rewards[pos, 0] = corrected_reward

    self.reward_corrections += 1
    self.total_penalty_applied += penalty

    if LOH_DEBUG_BASIC():
        print(f"[ReplayBuffer] ✏️  Correcting reward at buffer position {pos}:")
        print(f"  - state_version: {state_version}")
        print(f"  - original_reward (hit_ratio): {original_reward:.6f}")
        print(f"  - penalty (avoided_miss_ratio): {penalty:.6f}")
        print(f"  - corrected_reward: {corrected_reward:.6f}")
        print(f"  - interpretation: if this miss didn't happen, hit_ratio would be {corrected_reward:.6f}")

    return True
```

---

### 方案B：精确版 - 使用version差值估算驱逐到访问距离

需要在`ghost_cache_entry_t`中增加字段：

```c
typedef struct LOH_ghost_entry_t {
  uint64_t obj_id;
  int64_t obj_size;
  int64_t access_count;
  time_t last_access_time;
  int64_t last_access_counter;
  int64_t irt_values[3];
  time_t evict_time;
  uint64_t eviction_version;  // 已有
  int64_t eviction_timestamp;  // 【新增】驱逐时的timestamp
  // ... 其他字段
} LOH_ghost_entry_t;
```

然后在`add_to_ghost_cache()`中记录：
```c
ghost_entry->eviction_timestamp = params->current_timestamp;
```

在`LOH_get()`中使用：
```c
int64_t eviction_to_access = params->current_timestamp - ghost_entry->eviction_timestamp;
```

**缺点**：需要修改结构体（但你想避免这个）。

---

### 方案C：最简化 - 固定惩罚值（测试用）

如果你只是想快速验证机制是否work：

```c
// C端：所有ghost cache miss都用固定惩罚
double penalty = 0.05;  // 相当于5%的miss_ratio增量
enqueue_penalty(params, ghost_entry->eviction_version, penalty, req->obj_id);
```

```python
# Python端：直接加上penalty
corrected_reward = original_reward + penalty
```

---

## 推荐实施步骤

### 第一阶段：修复量纲问题（最紧急）

1. **C端改动**（`LOH.c`行2534附近）：
   ```c
   double single_miss_penalty = 1.0 / (double)params->rl_update_interval;
   double penalty = single_miss_penalty * 2.0;  // 先用固定权重2.0测试
   ```

2. **Python端改动**（`loh_actor_critic_sb3.py` `retrospective_correct_reward`方法）：
   ```python
   corrected_reward = original_reward + penalty  # 改为加号
   ```

### 第二阶段：引入距离权重

在C端根据`eviction_to_access`距离动态调整权重（使用当前的`revisit_distance`作为近似）。

### 第三阶段：精确化（可选）

如果效果不够好，再考虑在`ghost_cache_entry_t`中增加`eviction_timestamp`字段。

---

## 验证方法

修改后观察：

1. **惩罚值范围检查**：
   ```bash
   grep "final_penalty=" cachesim_sb3_*.log | awk '{print $NF}' | sort -n
   ```
   应该在[0.001, 0.02]范围内（假设rl_update_interval=200）

2. **修正后的reward范围**：
   ```bash
   grep "corrected_reward:" ac_sb3_*.log | awk '{print $3}' | sort -n
   ```
   应该在[0, 1.2]范围内（允许超过1.0一点点，因为多个penalty叠加）

3. **训练曲线**：
   看`rollout/ep_rew_mean`是否从负值逐渐上升到正值。

---

## 需要你做的决定

1. **要不要修改结构体**？
   - 不修改：使用方案A（用`last_access_counter`近似）
   - 修改：使用方案B（精确的`eviction_timestamp`）

2. **距离权重策略**？
   - 简单：固定权重（如2.0）
   - 复杂：分段权重（如我上面的例子）

3. **是否要额外记录信息**？
   - 比如在penalty队列中记录`eviction_to_access`距离，方便分析

请告诉我你的选择，我会据此实施修改！
