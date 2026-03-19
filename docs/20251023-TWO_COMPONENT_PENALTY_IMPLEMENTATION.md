# 两分量惩罚机制实现文档

## 概述

本文档记录了将LOH算法的惩罚机制从单一惩罚值改为两分量惩罚（对象分量+字节分量），并延迟计算最终奖励的完整实现。

## 核心改动

### 1. 设计原理

**旧方案**:
- 惩罚值: `penalty = (1/rl_update_interval) * distance_weight`
- 立即修正: `corrected_reward = original_reward + penalty`
- 问题: 未区分对象命中率和字节命中率的影响

**新方案**:
- **对象惩罚分量**: `obj_comp = (1/rl_update_interval) * (1/distance)`
  - 衡量"在一个epoch内多驱逐一个对象"对对象命中率的影响
- **字节惩罚分量**: `byte_comp = (obj_size/total_evicted_bytes) * (1/distance)`
  - 衡量该对象大小在该周期驱逐总量中的占比对字节命中率的影响
- **延迟计算**: 惩罚累积到列表中，在超过`exclude_recent_steps`后计算最终奖励
- **最终奖励**: `reward = 1 - pow(α*Σobj_comp + β*Σbyte_comp, γ)`
  - α: 对象惩罚权重 (默认0.5)
  - β: 字节惩罚权重 (默认0.5)
  - γ: 奖励计算指数 (默认1.0)

## C端修改 (libCacheSim/cache/eviction/LOH.c)

### 1.1 修改 `penalty_entry_t` 结构

```c
typedef struct {
  uint64_t penalty_version;        // 要惩罚的历史状态版本号
  double obj_penalty_component;    // 基于对象数的惩罚分量
  double byte_penalty_component;   // 基于字节数的惩罚分量
  int64_t obj_size;                // 对象大小（用于验证）
  uint64_t obj_id;                 // 触发惩罚的对象ID（用于调试）
} penalty_entry_t;
```

**变化**:
- 删除 `penalty_value`
- 添加 `obj_penalty_component`, `byte_penalty_component`, `obj_size`

### 1.2 修改 `shm_data_t` 结构

```c
typedef struct {
  // ... 其他字段保持不变 ...

  // 【删除】以下字段:
  // double miss_ratio;
  // double byte_miss_ratio;
  // double reward;

  // 【新增】以下字段:
  uint64_t total_evicted_bytes;  // 当前周期累计驱逐的字节数

  // ... penalty_queue 等其他字段保持不变 ...
} shm_data_t;
```

**原因**:
- 奖励现在在Python端延迟计算，不再从C端传递
- 需要 `total_evicted_bytes` 来归一化字节惩罚分量

### 1.3 在 `LOH_params_t` 添加字段

```c
typedef struct {
  // ... 其他字段 ...
  uint64_t epoch_evicted_bytes;  // 当前周期累计驱逐的字节数
  // ...
} LOH_params_t;
```

### 1.4 修改 `enqueue_penalty` 函数

```c
static bool enqueue_penalty(LOH_params_t *params, uint64_t penalty_version,
                            double obj_penalty_component,
                            double byte_penalty_component,
                            int64_t obj_size, uint64_t obj_id)
```

**变化**: 签名从单一 `penalty_value` 改为两个分量 + `obj_size`

### 1.5 修改惩罚计算逻辑 (LOH_get中的ghost miss检测)

**位置**: `LOH_get()` 函数，检测到 ghost cache miss 时

```c
// 计算两个惩罚分量
int64_t eviction_to_access = params->current_timestamp - ghost_entry->eviction_timestamp;
if (eviction_to_access < 1) eviction_to_access = 1;

// 分量1: 基于对象数
double obj_penalty_component =
    (1.0 / (double)params->rl_update_interval) *
    (1.0 / (double)eviction_to_access);

// 分量2: 基于字节数
double byte_penalty_component = 0.0;
if (params->epoch_evicted_bytes > 0) {
  byte_penalty_component =
      ((double)ghost_entry->obj_size / (double)params->epoch_evicted_bytes) *
      (1.0 / (double)eviction_to_access);
}

enqueue_penalty(params, ghost_entry->eviction_version,
                obj_penalty_component, byte_penalty_component,
                ghost_entry->obj_size, req->obj_id);
```

### 1.6 累加驱逐字节数 (LOH_evict)

**位置**: `LOH_evict()` 函数，在 `add_to_ghost_cache()` 之后

```c
add_to_ghost_cache(params, obj_to_evict, cache);
params->epoch_evicted_bytes += (uint64_t)obj_to_evict->obj_size;
```

### 1.7 同步时传递 `total_evicted_bytes`

**位置**: `sync_with_actor_critic()` 函数

```c
shm_data.total_evicted_bytes = params->epoch_evicted_bytes;
// 移除以下赋值:
// shm_data.miss_ratio = ...;
// shm_data.byte_miss_ratio = ...;
// shm_data.reward = ...;
```

### 1.8 周期重置

**位置**: `LOH_init()` 和 `sync_with_actor_critic()` 后的重置逻辑

```c
params->epoch_evicted_bytes = 0;  // 新增
```

## Python端修改 (scripts/loh_actor_critic_sb3.py)

### 2.1 修改 `PenaltyEntry` 结构

```python
class PenaltyEntry(ctypes.Structure):
    _fields_ = [
        ("penalty_version", ctypes.c_uint64),
        ("obj_penalty_component", ctypes.c_double),
        ("byte_penalty_component", ctypes.c_double),
        ("obj_size", ctypes.c_int64),
        ("obj_id", ctypes.c_uint64),
    ]
```

### 2.2 修改 `SharedMemoryData` 结构

```python
def create_shared_memory_class(context_dim):
    class SharedMemoryData(ctypes.Structure):
        _fields_ = [
            ("ready_for_inference", ctypes.c_int),
            ("weights_updated", ctypes.c_int),
            ("terminate", ctypes.c_int),
            ("is_training", ctypes.c_int),
            ("state", ctypes.c_double * context_dim),
            ("weights", ctypes.c_double * FEATURE_DIM),
            # 【删除】
            # ("miss_ratio", ctypes.c_double),
            # ("byte_miss_ratio", ctypes.c_double),
            # ("reward", ctypes.c_double),
            # 【新增】
            ("total_evicted_bytes", ctypes.c_uint64),
            ("state_version", ctypes.c_uint64),
            ("ack_version", ctypes.c_uint64),
            ("timestamp", ctypes.c_int64),
            ("penalty_queue_size", ctypes.c_int),
            ("penalty_queue", PenaltyEntry * MAX_PENALTY_QUEUE_SIZE),
        ]
    return SharedMemoryData
```

### 2.3 修改 `RetrospectiveReplayBuffer.__init__`

**新增参数**:
- `obj_penalty_weight`: 对象惩罚权重 (α)
- `byte_penalty_weight`: 字节惩罚权重 (β)
- `reward_exponent`: 奖励计算指数 (γ)

**新增成员**:
- `self.obj_penalties`: 每个buffer位置的对象惩罚分量列表
- `self.byte_penalties`: 每个buffer位置的字节惩罚分量列表
- `self.reward_finalized`: 标记哪些位置的奖励已最终化

### 2.4 修改 `RetrospectiveReplayBuffer.add()`

```python
def add(self, obs, next_obs, action, reward, done, infos):
    pos_before = self.pos

    # 初始化惩罚列表
    self.obj_penalties[pos_before] = []
    self.byte_penalties[pos_before] = []
    self.reward_finalized[pos_before] = False

    # 调用父类（reward为初始值1.0）
    super().add(obs, next_obs, action, reward, done, infos)
```

### 2.5 修改 `retrospective_correct_reward()`

**旧版本**: 立即修正奖励 `rewards[pos] += penalty`

**新版本**: 累积惩罚分量

```python
def retrospective_correct_reward(self, state_version, obj_penalty_comp, byte_penalty_comp):
    pos = self.version_to_pos[state_version]

    # 累积惩罚分量
    self.obj_penalties[pos].append(obj_penalty_comp)
    self.byte_penalties[pos].append(byte_penalty_comp)

    # 更新统计
    self.reward_corrections += 1
    self.total_obj_penalty += obj_penalty_comp
    self.total_byte_penalty += byte_penalty_comp

    return True
```

### 2.6 新增 `compute_final_rewards()` 方法

```python
def compute_final_rewards(self, start_pos, end_pos):
    """
    计算指定范围内的最终奖励

    公式: reward = 1 - pow(α*Σobj_penalties + β*Σbyte_penalties, γ)
    """
    for pos in range(start_pos, end_pos):
        pos = pos % self.buffer_size

        if self.reward_finalized[pos]:
            continue

        # 计算加权惩罚总和
        obj_sum = sum(self.obj_penalties[pos])
        byte_sum = sum(self.byte_penalties[pos])
        weighted_sum = (self.obj_penalty_weight * obj_sum +
                       self.byte_penalty_weight * byte_sum)

        # 计算最终奖励
        final_reward = 1.0 - pow(weighted_sum, self.reward_exponent)

        # 写入buffer
        self.rewards[pos, 0] = final_reward
        self.reward_finalized[pos] = True
```

### 2.7 修改 `LohEnv.step()` 中的奖励计算

**旧版本**:
```python
new_miss_ratio = data.miss_ratio
new_byte_miss_ratio = data.byte_miss_ratio
reward = alpha * (1 - new_miss_ratio) + beta * (1 - new_byte_miss_ratio)
```

**新版本**:
```python
# 不再从共享内存读取 miss_ratio（已删除）
reward = 1.0  # 初始奖励，将被 compute_final_rewards() 覆盖
```

### 2.8 修改惩罚队列处理 (LohEnv.step中)

**旧版本**: 立即调用 `retrospective_correct_reward(penalty_version, penalty_value)`

**新版本**: 调用两分量版本

```python
for i in range(data.penalty_queue_size):
    penalty_entry = data.penalty_queue[i]
    obj_comp = float(penalty_entry.obj_penalty_component)
    byte_comp = float(penalty_entry.byte_penalty_component)

    replay_buffer.retrospective_correct_reward(
        penalty_entry.penalty_version, obj_comp, byte_comp)
```

### 2.9 新增延迟奖励计算调用 (LohEnv.step中)

在处理完惩罚队列后:

```python
# 计算旧数据的最终奖励
if buffer_size > exclude_steps:
    if not replay_buffer.full:
        finalize_end = max(0, current_pos - exclude_steps)
        if finalize_end > 0:
            replay_buffer.compute_final_rewards(0, finalize_end)
    else:
        # Buffer已满：只finalize刚离开排除窗口的位置
        pos_to_finalize = (current_pos - exclude_steps) % replay_buffer.buffer_size
        if not replay_buffer.reward_finalized[pos_to_finalize]:
            replay_buffer.compute_final_rewards(pos_to_finalize, pos_to_finalize + 1)
```

## 结构大小验证

### Python端

运行 `python3 verify_shm_structure.py`:

```
sizeof(PenaltyEntry): 40 字节
sizeof(SharedMemoryData): 5432 字节 (CONTEXT_DIM=26)
```

### C端

编译后运行cachesim，会在日志中输出:
```
sizeof(penalty_entry_t) = 40 bytes
sizeof(shm_data_t) = 5432 bytes
```

两端**必须一致**，否则会导致内存读写错误。

## 参数配置

### ReplayBuffer参数 (在创建SAC模型时设置)

```python
replay_buffer_class = RetrospectiveReplayBuffer
replay_buffer_kwargs = {
    'exclude_recent_steps': 200,      # 排除最新200步（约1个epoch）
    'obj_penalty_weight': 0.5,        # α: 对象惩罚权重
    'byte_penalty_weight': 0.5,       # β: 字节惩罚权重
    'reward_exponent': 1.0,           # γ: 奖励计算指数
}
```

### 调整建议

1. **exclude_recent_steps**:
   - 应设置为 `rl_update_interval` 的1-2倍
   - 太小: 惩罚未充分累积
   - 太大: 延迟过长,影响训练效率

2. **obj_penalty_weight vs byte_penalty_weight**:
   - 如果更关注对象命中率: 增大 α (如 0.7/0.3)
   - 如果更关注字节命中率: 增大 β (如 0.3/0.7)
   - 平衡: 0.5/0.5

3. **reward_exponent**:
   - γ=1.0: 线性惩罚
   - γ>1.0: 放大惩罚效果（惩罚越大，奖励下降越快）
   - γ<1.0: 缓和惩罚效果

## 测试验证步骤

### 1. 编译C代码
```bash
bash scripts/debug.sh -c
```

### 2. 验证结构对齐
```bash
python3 verify_shm_structure.py
```

### 3. 运行集成测试
```bash
bash ./scripts/test_loh_rl_sb3.sh
```

### 4. 检查日志关键点

**C端日志** (`cachesim_sb3_*.log`):
- 搜索 `sizeof(penalty_entry_t)` 验证结构大小
- 搜索 `Ghost miss (2-comp)` 查看惩罚计算
- 搜索 `Enqueued 2-component penalty` 验证入队
- 搜索 `total_evicted_bytes` 验证字节统计

**Python端日志** (`ac_sb3_*.log`):
- 搜索 `Received 2-component penalties` 查看惩罚接收
- 搜索 `Accumulated penalty components` 验证累积
- 搜索 `Finalized reward` 查看最终奖励计算
- 搜索 `rollout/` 验证训练进行

### 5. 常见问题排查

**症状**: 程序崩溃或段错误
- **原因**: 结构大小不匹配
- **解决**: 运行 `verify_shm_structure.py` 并对比C端输出

**症状**: 惩罚队列一直为空
- **原因**: ghost cache miss未触发或 `eviction_version==0`
- **解决**: 检查 warmup 是否完成，检查 `is_warmed_up` 标志

**症状**: 奖励值异常（全为1.0或负数）
- **原因**: 延迟计算未执行或惩罚过大
- **解决**: 检查 `exclude_recent_steps` 设置，检查惩罚分量值

**症状**: 训练不收敛
- **原因**: 奖励信号质量差或惩罚权重不合理
- **解决**: 调整 `obj_penalty_weight`/`byte_penalty_weight`/`reward_exponent`

## 与旧版本的兼容性

**不兼容**: 旧版本的共享内存文件会导致结构不匹配

**迁移步骤**:
1. 停止所有运行中的LOH进程
2. 清理共享内存: `rm /dev/shm/loh_ac_*`
3. 重新编译: `bash scripts/debug.sh -c`
4. 启动新版本

## 性能影响

### 计算开销

**C端**:
- 每次 ghost miss: 增加1次除法和1次乘法（计算两个分量）
- 影响: 可忽略（相比驱逐决策的开销）

**Python端**:
- 每个buffer位置: 存储2个列表 (obj_penalties, byte_penalties)
- 每次最终化: 遍历列表求和 + 1次幂运算
- 影响: 内存增加约 10-20%，计算开销可忽略

### 训练效果

**预期改进**:
- 更精细的奖励信号（区分对象/字节维度）
- 更准确的惩罚归一化（避免受epoch大小影响）
- 更稳定的训练过程（延迟计算确保惩罚完整）

## 未来优化方向

1. **自适应权重**: 根据 workload 特征自动调整 α/β
2. **惩罚衰减**: 对老惩罚施加时间衰减因子
3. **分层奖励**: 区分短期/长期奖励
4. **惩罚阈值**: 忽略极小的惩罚分量（减少噪声）

## 参考

- 原始单一惩罚机制: `20251023-PENALTY_FIX_SUMMARY.md`
- 驱逐时间戳改进: `20251023-EVICTION_TIMESTAMP_IMPROVEMENT.md`
- 总体架构: `20250814-LOH_Algorithm_Architecture.md`

---

**作者**: Copilot Agent
**日期**: 2024-12-27
**版本**: 1.0
**状态**: 已实现，待测试验证
