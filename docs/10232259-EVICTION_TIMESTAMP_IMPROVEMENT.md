# 精确驱逐时间戳改进

## 修改日期
2025-10-23

## 改进内容

### 问题
之前使用 `ghost_entry->last_access_counter` 作为驱逐时刻的近似值，但这实际上是**对象被驱逐前的最后访问时刻**，而不是驱逐的精确时刻。

### 解决方案
在 `LOH_ghost_entry_t` 结构体中新增 `eviction_timestamp` 字段，记录驱逐时的精确逻辑时间戳。

---

## 代码修改

### 1. 结构体定义（LOH.c，行293-307）

```c
typedef struct LOH_ghost_entry {
  obj_id_t obj_id;
  int64_t obj_size;
  int32_t access_count;
  int64_t last_access_time;
  int64_t last_access_counter;  // 驱逐前的最后访问时间
  int64_t irt_values[3];
  time_t evict_time;
  uint64_t eviction_version;
  int64_t eviction_timestamp;   // ✅ 新增：驱逐时的精确逻辑时间戳

  struct LOH_ghost_entry *prev;
  struct LOH_ghost_entry *next;
} LOH_ghost_entry_t;
```

### 2. 记录驱逐时刻（LOH.c，add_to_ghost_cache函数）

```c
// 创建新的 ghost 条目
LOH_ghost_entry_t *ghost_entry = g_new0(LOH_ghost_entry_t, 1);
// ... 复制对象信息 ...

ghost_entry->evict_time = time(NULL);

// ✅ 新增：记录驱逐时的精确逻辑时间戳
ghost_entry->eviction_timestamp = params->current_timestamp;

// 记录驱逐时的state_version
if (params->shm_file != NULL) {
  // ... 读取state_version ...
  ghost_entry->eviction_version = shm_data.state_version;
}
```

### 3. 使用精确时间戳计算惩罚（LOH.c，LOH_get函数）

```c
// 之前（近似）：
int64_t eviction_to_access =
    params->current_timestamp - ghost_entry->last_access_counter;

// 现在（精确）：
int64_t eviction_to_access =
    params->current_timestamp - ghost_entry->eviction_timestamp;
```

---

## 优势

### 1. 精确性提升
- **之前**：使用最后访问时间，如果对象在驱逐前很久没被访问，会低估驱逐到访问的距离
- **现在**：使用驱逐时刻，精确反映对象被驱逐后多久被再次访问

### 2. 示例场景

**场景**：某对象在t=1000时最后被访问，在t=5000时被驱逐，在t=5100时再次访问

| 方法 | 计算 | 结果 | 评价 |
|-----|------|------|------|
| 旧方法 | 5100 - 1000 | 4100 | ❌ 错误：包含了对象在缓存中未被访问的时间 |
| 新方法 | 5100 - 5000 | 100  | ✅ 正确：只计算驱逐后的距离 |

在旧方法中，距离4100会导致权重降低到1.0，而实际上距离只有100应该使用2.5的权重。

### 3. 距离权重映射更准确

| eviction_to_access | 权重 | 含义 |
|-------------------|------|------|
| < 100             | 2.5  | 刚被驱逐就被访问 → 非常严重的错误 |
| 100-499           | 2.0  | 很快被访问 → 严重错误 |
| 500-999           | 1.5  | 不久就被访问 → 中等错误 |
| 1000-4999         | 1.0  | 过了一段时间 → 轻微错误 |
| ≥ 5000            | 0.5  | 很久才被访问 → 可能合理 |

现在这些阈值基于的是**真实的驱逐后距离**，而不是包含了对象在缓存中未被访问时间的混合值。

---

## 关于 retrospective_correct_reward 的说明

### 调用关系

`retrospective_correct_reward` 是**自定义方法**，不是父类 `ReplayBuffer` 的方法。

```python
# 定义位置：scripts/loh_actor_critic_sb3.py, 行204
class RetrospectiveReplayBuffer(ReplayBuffer):
    def retrospective_correct_reward(self, state_version, penalty):
        """事后修正指定version的奖励"""
        # ...
```

### 调用位置

在 `LohEnv.step()` 方法中调用（行1083-1084）：

```python
# 在 LohEnv.step() 中处理惩罚队列
for i in range(data.penalty_queue_size):
    penalty_entry = data.penalty_queue[i]
    penalty_version = int(penalty_entry.penalty_version)
    penalty_value = float(penalty_entry.penalty_value)

    # 如果 replay buffer 存在，应用事后惩罚
    if replay_buffer is not None and hasattr(replay_buffer, 'retrospective_correct_reward'):
        success = replay_buffer.retrospective_correct_reward(penalty_version, penalty_value)
        # ...
```

### 为什么需要这个方法？

1. **父类 `ReplayBuffer` 没有这个功能**
   - 标准的 `ReplayBuffer` 只存储和采样数据
   - 不支持事后修改已存储的reward

2. **我们的需求**
   - Ghost cache miss是延迟发现的（可能在几百步之后）
   - 需要回溯修改历史transition的reward
   - 因此自定义了 `retrospective_correct_reward` 方法

3. **设计模式**
   - 通过继承 `ReplayBuffer` 并添加新方法
   - 使用 `hasattr` 检查方法是否存在（兼容性考虑）
   - 维护 `version_to_pos` 映射用于快速定位

---

## 测试验证

### 检查驱逐距离分布

```bash
# 运行测试
bash run_quick_test.sh quick

# 查看驱逐到访问距离
grep "evict_to_access=" cachesim_sb3_*.log | \
    awk -F'evict_to_access=' '{print $2}' | \
    awk '{print $1}' | \
    sort -n | \
    uniq -c

# 预期输出示例：
#   5   42    # 5次距离为42的miss
#  12   156   # 12次距离为156的miss
#   8   823   # 8次距离为823的miss
#   ...
```

### 对比新旧方法

可以临时注释掉新代码，使用旧的 `last_access_counter`，对比惩罚值的变化：

```c
// 临时测试：使用旧方法
// int64_t eviction_to_access = params->current_timestamp - ghost_entry->eviction_timestamp;
int64_t eviction_to_access = params->current_timestamp - ghost_entry->last_access_counter;
```

预期：新方法的平均惩罚值会更高（因为距离更短，权重更大）。

---

## 内存影响

### 结构体大小增加

```c
sizeof(LOH_ghost_entry_t) 增加 8 bytes（int64_t）
```

### Ghost Cache容量估算

假设 ghost cache 保存1000个条目：
- 旧版：约 80 KB
- 新版：约 88 KB
- 增加：8 KB（可忽略）

---

## 相关文档

- [PENALTY_FIX_SUMMARY.md](./PENALTY_FIX_SUMMARY.md) - 惩罚机制修复总结
- [PENALTY_MECHANISM_REDESIGN.md](./PENALTY_MECHANISM_REDESIGN.md) - 惩罚机制重新设计
- [SAC_RETROSPECTIVE_GUIDE.md](./SAC_RETROSPECTIVE_GUIDE.md) - 事后奖励修正指南

---

## 总结

✅ **改进点**：
1. 新增 `eviction_timestamp` 字段，精确记录驱逐时刻
2. 使用精确时间戳计算驱逐到访问距离
3. 距离权重映射更准确，惩罚机制更合理

✅ **兼容性**：
- 结构体增加8字节，内存影响可忽略
- 编译通过，无破坏性改动

✅ **下一步**：
- 运行测试验证距离分布
- 观察训练效果是否改善
- 根据实际数据调整距离权重阈值

---

**修改作者**: GitHub Copilot
**审核状态**: ✅ 编译通过，待测试验证
