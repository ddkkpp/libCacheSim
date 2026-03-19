# LOH算法完整架构文档

## 概述

LOH (Learning-based Object Handling) 是一个结合传统启发式算法和强化学习的缓存驱逐算法。它维护多维特征统计，通过Actor-Critic网络进行在线学习和权重更新。

## 1. 主要数据结构

### 1.1 核心参数结构 `LOH_params_t`

```c
typedef struct {
  // 基础配置和时间戳
  int64_t current_timestamp;          // 逻辑时间戳
  bool is_warmed_up;                  // 是否完成热身
  int64_t rl_update_interval;         // RL更新间隔
  int64_t requests_since_rl_update;   // 距离上次RL更新的请求数

  // 候选对象池 (600个)
  cache_obj_t *candidates[MAX_CANDIDATES];
  int n_candidates;

  // 频率表 (LFU维度) - 双向链表
  loh_freq_node_t *freq_table[FREQ_MAX + 1];      // 头部指针(最新)
  loh_freq_node_t *freq_table_tail[FREQ_MAX + 1]; // 尾部指针(更老)

  // 尺寸桶 (Size维度) - 双向链表
  size_node_t *size_buckets[SIZE_BUCKET_COUNT];      // 头部指针(最新)
  size_node_t *size_buckets_tail[SIZE_BUCKET_COUNT]; // 尾部指针(更老)

  // IRT堆 (3个历史IRT维度) - 最大堆
  irt_heap_entry_t *irt_heap[3];      // 堆顶IRT最大(最久未访问)
  int irt_heap_size[3];
  int irt_heap_capacity;

  // Ghost Cache - 保存被驱逐对象的历史信息
  GHashTable *ghost_cache;

  // 38维状态向量
  double context_state[CONTEXT_DIM];

  // 【类型A】全局性能统计 (仅warmup后更新，RL周期后重置)
  double epoch_obj_count;         // 总请求数
  double epoch_obj_miss_count;    // 对象未命中数
  double epoch_byte_count;        // 总字节数
  double epoch_byte_miss_count;   // 字节未命中数

  // 【类型B】命中/未命中特征统计 (仅warmup后更新，RL周期后重置)
  double hit_feature_sum[FEATURE_DIM];
  double hit_feature_sum_sq[FEATURE_DIM];
  int hit_feature_count;
  double miss_feature_sum[FEATURE_DIM];
  double miss_feature_sum_sq[FEATURE_DIM];
  int miss_feature_count;

  // 【类型C】缓存内容特征统计 (始终更新，永不重置)
  double cache_feature_sum[FEATURE_DIM];     // 省略feature0
  double cache_feature_sum_sq[FEATURE_DIM];  // 省略feature0
  int cache_object_count;

  // 强化学习相关
  FILE *shm_file;                    // 共享内存文件
  // ... 其他网络权重和配置参数
} LOH_params_t;
```

### 1.2 对象级数据 `cache_obj_t.LOH`

```c
typedef struct {
  int64_t irt_values[3];        // 简化的IRT历史，位置0最新
  int irt_count;                // 有效IRT值数量
  int access_count;             // 访问次数
  int64_t last_access_counter;  // 上次访问时间戳
  time_t last_access_time;      // 实际时间
  int loh_state;                // 对象状态(ACTIVE/INVALID等)
} cache_obj_LOH_t;
```

### 1.3 Ghost Cache条目

```c
typedef struct {
  int access_count;             // 被驱逐时的访问次数
  int64_t last_access_counter;  // 被驱逐时的最后访问时间
  int64_t irt_values[3];        // 被驱逐时的IRT历史
} LOH_ghost_entry_t;
```

## 2. 核心函数功能

### 2.1 LOH_get函数
**功能**: 缓存访问入口，管理统计更新和RL周期

```c
bool LOH_get(cache_t *cache, const request_t *req) {
  params->current_timestamp += 1;

  // 1. 仅warmup后计数RL更新
  if (params->is_warmed_up) {
    params->requests_since_rl_update += 1;
  }

  // 2. RL周期管理
  if (params->is_warmed_up &&
      params->requests_since_rl_update >= params->rl_update_interval) {
    sync_with_actor_critic(params);    // 发送状态向量，接收新权重
    reset_rl_statistics(params);       // 重置类型A和B统计
  }

  // 3. 预测是否命中并计算特征
  bool will_hit = (cache_get_base(cache, req) != NULL);
  calculate_object_features(params, req, obj, features);

  // 4. 执行实际访问
  bool hit = cache_get_base(cache, req);

  // 5. 【统计更新】仅warmup后更新
  if (params->is_warmed_up) {
    // 类型A: 全局性能统计
    params->epoch_obj_count++;
    params->epoch_byte_count += req->obj_size;
    if (!hit) {
      params->epoch_obj_miss_count++;
      params->epoch_byte_miss_count += req->obj_size;
    }

    // 类型B: 命中/未命中特征统计
    if (hit) {
      update_hit_feature_stats(params, features);
    } else {
      update_miss_feature_stats(params, features);
    }
  }

  return hit;
}
```

### 2.2 LOH_find函数
**功能**: 查找对象并更新访问信息，管理缓存内容特征统计

```c
cache_obj_t *LOH_find(cache_t *cache, const request_t *req, bool update_cache) {
  cache_obj_t *obj = cache_find_base(cache, req, update_cache);

  if (obj && update_cache) {
    // 1. 先更新缓存内容特征统计(类型C，使用访问前状态，始终更新)
    int64_t irt = params->current_timestamp - obj->LOH.last_access_counter;
    update_cache_content_stats_find(params, obj, irt);

    // 2. 更新对象访问信息
    obj->LOH.access_count++;
    if (irt > 0) {
      update_irt_values(obj, irt); // 更新IRT历史数组
    }
    obj->LOH.last_access_counter = params->current_timestamp;

    // 3. 更新辅助数据结构(频率表、IRT堆)
    loh_atomic_update_obj(params, obj);
  }

  return obj;
}
```

### 2.3 LOH_insert函数
**功能**: 插入新对象，初始化并更新缓存内容特征统计

```c
cache_obj_t *LOH_insert(cache_t *cache, const request_t *req) {
  // 1. 基础插入
  cache_obj_t *obj = cache_insert_base(cache, req);

  // 2. 初始化LOH字段
  obj->LOH.access_count = 1;
  obj->LOH.last_access_counter = params->current_timestamp;
  memset(obj->LOH.irt_values, 0, sizeof(obj->LOH.irt_values));
  obj->LOH.irt_count = 0;
  loh_obj_set_state(obj, LOH_OBJ_STATE_ACTIVE);

  // 3. 从ghost cache恢复历史(如果存在)
  restore_from_ghost_cache(params, obj, req);

  // 4. 添加到辅助数据结构
  freq_table_add(params, obj);
  size_buckets_add(params, obj);
  irt_heap_add_all(params, obj);

  // 5. 更新缓存内容特征统计(类型C，始终更新)
  update_cache_content_stats_add(params, obj);

  return obj;
}
```

### 2.4 LOH_evict函数
**功能**: 驱逐选定对象，更新缓存内容特征统计

```c
void LOH_evict(cache_t *cache, const request_t *req) {
  cache_obj_t *obj_to_evict = LOH_to_evict(cache, req);

  // 1. 更新缓存内容特征统计(类型C，移除，始终更新)
  update_cache_content_stats_remove(params, obj_to_evict);

  // 2. 保存到ghost cache
  save_to_ghost_cache(params, obj_to_evict);

  // 3. 从辅助数据结构移除
  freq_table_remove(params, obj_to_evict);
  size_buckets_remove(params, obj_to_evict);
  irt_heap_remove_all(params, obj_to_evict);

  // 4. 执行实际驱逐
  cache_evict_base(cache, obj_to_evict, true);
}
```

## 3. 特征计算公式

### 3.1 六维特征向量

```c
void calculate_object_features(params, req, obj, features[6]) {
  if (obj != NULL) {
    // Feature 0: Recency (最近性) - 基于时间戳差异
    features[0] = 1.0 / (1.0 + (current_timestamp - obj->last_access_counter));

  // Feature 1: Frequency (频率) - 无log，采用 f/(f+K) 且 K=1
  double f = (double)obj->access_count;
  features[1] = (f <= 0.0) ? 0.0 : (f / (f + 1.0));

  // Feature 2: Size (大小) - 无log，转换为MB后采用 1/(1 + A*MB) 且 A=1
    double size_mb = (double)req->obj_size / (1024.0 * 1024.0);
  features[2] = 1.0 / (1.0 + size_mb);

    // Feature 3-5: IRT History (访问间隔历史)
    features[3] = calculate_irt_feature(obj->irt_values[0]); // 最新IRT
    features[4] = calculate_irt_feature(obj->irt_values[1]); // 第2新IRT
    features[5] = calculate_irt_feature(obj->irt_values[2]); // 第3新IRT
  } else {
    // 新对象情况，从ghost cache获取特征或设为0
    for (int i = 0; i < FEATURE_DIM; i++) features[i] = 0.0;
  }
}

// IRT特征归一化公式
double calculate_irt_feature(int64_t irt) {
  if (irt <= 0) return 0.0;
  return 1.0 / (1.0 + (double)irt);  // 倒数归一化，IRT越大特征值越小
}
```

### 3.2 Ghost Cache特征计算

```c
// 对于ghost cache中的对象，内联计算特征
if (ghost_entry) {
  // Recency: 从ghost cache的最后访问时间计算
  int64_t current_irt = params->current_timestamp - ghost_entry->last_access_counter;
  features[0] = 1.0 / (1.0 + (double)current_irt);

  // Frequency: 从ghost cache的访问次数计算（无log，K=1）
  if (ghost_entry->access_count > 0) {
    double f = (double)ghost_entry->access_count;
    features[1] = f / (f + 1.0);
  }

  // Size: 从请求大小计算（无log，A=1）
  double size_mb = (double)req->obj_size / (1024.0 * 1024.0);
  features[2] = 1.0 / (1.0 + size_mb);

  // IRT特征: 直接从ghost_entry获取
  features[3] = calculate_irt_feature(ghost_entry->irt_values[0]);
  features[4] = calculate_irt_feature(ghost_entry->irt_values[1]);
  features[5] = calculate_irt_feature(ghost_entry->irt_values[2]);
}
```

## 4. 状态向量(38维)更新机制

### 4.1 状态向量结构

```c
// context_state[38]:
// [0-1]:   全局性能指标 - 对象命中率, 字节命中率 (类型A)
// [2-25]:  特征表现剖析 - 6特征×2统计×2事件 (命中/未命中的均值/方差) (类型B)
// [26-37]: 缓存状态摘要 - 6特征×2统计 (当前缓存中的均值/方差) (类型C)
```

### 4.2 三类统计的更新时机和重置策略

#### 【类型A】全局性能统计 - 仅warmup后更新，RL周期后重置

```c
// 更新时机: LOH_get中，仅当is_warmed_up为true时
if (params->is_warmed_up) {
  params->epoch_obj_count++;           // 总请求计数
  params->epoch_byte_count += req->obj_size;
  if (!hit) {
    params->epoch_obj_miss_count++;    // 未命中计数
    params->epoch_byte_miss_count += req->obj_size;
  }
}

// RL周期结束重置
if (params->is_warmed_up &&
    params->requests_since_rl_update >= params->rl_update_interval) {
  sync_with_actor_critic(params);
  // 重置全局性能统计
  params->epoch_obj_count = 0;
  params->epoch_obj_miss_count = 0;
  params->epoch_byte_count = 0;
  params->epoch_byte_miss_count = 0;
}
```

#### 【类型B】命中/未命中特征统计 - 仅warmup后更新，RL周期后重置

```c
// 更新时机: LOH_get中，仅当is_warmed_up为true时
if (params->is_warmed_up) {
  if (hit && obj_before_access != NULL) {
    params->hit_feature_count++;
    for (int i = 0; i < FEATURE_DIM; i++) {
      params->hit_feature_sum[i] += features[i];
      params->hit_feature_sum_sq[i] += features[i] * features[i];
    }
  } else if (!hit) {
    params->miss_feature_count++;
    for (int i = 0; i < FEATURE_DIM; i++) {
      params->miss_feature_sum[i] += features[i];
      params->miss_feature_sum_sq[i] += features[i] * features[i];
    }
  }
}

// RL周期结束重置
params->hit_feature_count = 0;
params->miss_feature_count = 0;
for (int i = 0; i < FEATURE_DIM; i++) {
  params->hit_feature_sum[i] = 0.0;
  params->hit_feature_sum_sq[i] = 0.0;
  params->miss_feature_sum[i] = 0.0;
  params->miss_feature_sum_sq[i] = 0.0;
}
```

#### 【类型C】缓存内容特征统计 - 始终更新，永不重置

```c
// 更新时机: find/insert/evict中的实际缓存操作
// 省略feature0 (recency)：所有对象recency都会变化，全局更新成本太高

// 添加对象时 (LOH_insert)
update_cache_content_stats_add(params, obj);

// 访问对象时 (LOH_find) - 增量更新变化部分
update_cache_content_stats_find(params, obj, irt);

// 移除对象时 (LOH_evict)
update_cache_content_stats_remove(params, obj);

// 重要: RL周期结束时不重置缓存内容统计
// 因为这是累积的状态，无法重新计算
```

### 4.3 状态向量计算和发送

```c
void update_state_vector(LOH_params_t *params) {
  // A. 全局性能指标 (类型A统计)
  double hit_ratio = 0.0;
  if (params->epoch_obj_count > 0) {
    hit_ratio = 1.0 - (params->epoch_obj_miss_count / params->epoch_obj_count);
  }

  double byte_hit_ratio = 0.0;
  if (params->epoch_byte_count > 0) {
    byte_hit_ratio = 1.0 - (params->epoch_byte_miss_count / params->epoch_byte_count);
  }

  params->context_state[0] = hit_ratio;
  params->context_state[1] = byte_hit_ratio;

  // B. 特征表现剖析 (类型B统计，24维)
  for (int i = 0; i < FEATURE_DIM; i++) {
    // 命中对象特征均值/方差
    if (params->hit_feature_count > 0) {
      double mean = params->hit_feature_sum[i] / params->hit_feature_count;
      params->context_state[2 + i*4] = mean;

      if (params->hit_feature_count > 1) {
        double variance = (params->hit_feature_sum_sq[i] / params->hit_feature_count) - (mean * mean);
        params->context_state[2 + i*4 + 1] = variance > 0 ? variance : 0.0;
      }
    }

    // 未命中对象特征均值/方差
    if (params->miss_feature_count > 0) {
      double mean = params->miss_feature_sum[i] / params->miss_feature_count;
      params->context_state[2 + i*4 + 2] = mean;

      if (params->miss_feature_count > 1) {
        double variance = (params->miss_feature_sum_sq[i] / params->miss_feature_count) - (mean * mean);
        params->context_state[2 + i*4 + 3] = variance > 0 ? variance : 0.0;
      }
    }
  }

  // C. 缓存状态摘要 (类型C统计，12维)
  for (int i = 0; i < FEATURE_DIM; i++) {
    if (params->cache_object_count > 0) {
      // 省略feature0，从feature1开始
      if (i >= 1) {
        double mean = params->cache_feature_sum[i] / params->cache_object_count;
        params->context_state[26 + (i-1)*2] = mean;

        if (params->cache_object_count > 1) {
          double variance = (params->cache_feature_sum_sq[i] / params->cache_object_count) - (mean * mean);
          params->context_state[26 + (i-1)*2 + 1] = variance > 0 ? variance : 0.0;
        }
      }
    }
  }
}
```

## 5. 其他重要逻辑

### 5.1 Warmup机制

```c
// Warmup条件检查
if (!params->is_warmed_up &&
    cache->get_occupied_byte(cache) >= cache->cache_size / 2 &&
    params->current_timestamp >= 10000) {
  params->is_warmed_up = true;
  printf("[LOH] Cache warmed up at request %ld\n", params->current_timestamp);
}

// Warmup参数设置:
// - IRT堆容量: MAX_CANDIDATES/6*2 = 200个对象
// - Warmup触发条件: 缓存占用达到50% 且 处理>=10000个请求
```

### 5.2 候选对象选择策略

```c
// 驱逐优先级: 低频率 > 大尺寸 > 大IRT
// 同级别内选择更老的对象(更长时间未被访问)

void LOH_to_evict() {
  int candidates_per_feature = MAX_CANDIDATES / 5;  // 每个维度120个候选

  // 1. 频率表: 从freq=1开始，同频率从尾部(更老)选择
  freq_table_get_candidates(params, candidates_per_feature, &n_candidates);

  // 2. 尺寸桶: 从大尺寸开始，同尺寸从尾部(更老)选择
  size_buckets_get_candidates(params, candidates_per_feature, &n_candidates);

  // 3. IRT堆: 从大IRT开始选择(堆顶最大)
  irt1_heap_get_candidates(params, candidates_per_feature, &n_candidates);
  irt2_heap_get_candidates(params, candidates_per_feature, &n_candidates);
  irt3_heap_get_candidates(params, candidates_per_feature, &n_candidates);

  // 4. 使用机器学习模型评分选择最终驱逐对象
  return select_victim_by_ml_score(params);
}

// 同级别选择策略:
// - 频率表: 从尾部向前遍历 (curr = curr->prev)
// - 尺寸桶: 从尾部向前遍历 (curr = curr->prev)
// - IRT堆: 最大堆，直接取堆顶
```

### 5.3 Ghost Cache机制

```c
// 保存驱逐对象的关键信息用于历史恢复
void save_to_ghost_cache(LOH_params_t *params, cache_obj_t *obj) {
  LOH_ghost_entry_t *entry = g_new0(LOH_ghost_entry_t, 1);
  entry->access_count = obj->LOH.access_count;
  entry->last_access_counter = obj->LOH.last_access_counter;
  for (int i = 0; i < 3; i++) {
    entry->irt_values[i] = obj->LOH.irt_values[i];
  }

  g_hash_table_insert(params->ghost_cache,
                      GINT_TO_POINTER((int)obj->obj_id), entry);
}

// 恢复时正确更新IRT历史
void restore_from_ghost_cache(LOH_params_t *params, cache_obj_t *obj, const request_t *req) {
  LOH_ghost_entry_t *ghost_entry = g_hash_table_lookup(
    params->ghost_cache, GINT_TO_POINTER((int)req->obj_id));

  if (ghost_entry) {
    // 恢复历史信息
    obj->LOH.access_count = ghost_entry->access_count + 1;  // 加上当前请求

    // 先复制历史IRT值
    for (int i = 0; i < 3; i++) {
      obj->LOH.irt_values[i] = ghost_entry->irt_values[i];
    }

    // 计算从ghost cache到现在的IRT，并更新到位置0
    int64_t current_irt = params->current_timestamp - ghost_entry->last_access_counter;
    if (current_irt > 0) {
      update_irt_values(obj, current_irt);
    }

    // 恢复IRT计数
    obj->LOH.irt_count = 0;
    for (int i = 0; i < 3; i++) {
      if (obj->LOH.irt_values[i] > 0) {
        obj->LOH.irt_count++;
      }
    }

    // 从ghost cache移除
    g_hash_table_remove(params->ghost_cache, GINT_TO_POINTER((int)req->obj_id));
  }
}
```

### 5.4 IRT历史管理

```c
// 更新IRT值数组 - 新值插入位置0，其他值后移
void update_irt_values(cache_obj_t *obj, int64_t new_irt) {
  // 向后移动现有IRT值
  obj->LOH.irt_values[2] = obj->LOH.irt_values[1];
  obj->LOH.irt_values[1] = obj->LOH.irt_values[0];

  // 插入新的IRT值到位置0
  obj->LOH.irt_values[0] = new_irt;

  // 更新有效IRT计数
  if (obj->LOH.irt_count < 3) {
    obj->LOH.irt_count++;
  }
}
```

### 5.5 缓存内容特征增量更新

```c
// LOH_find中的增量更新示例
void update_cache_content_stats_find(LOH_params_t *params, cache_obj_t *obj, int64_t new_irt) {
  // Feature 1: frequency从access_count变为access_count+1（无log，K=1）
  double f_old = (double)obj->LOH.access_count;
  double f_new = (double)(obj->LOH.access_count + 1);
  double old_freq = (f_old <= 0.0) ? 0.0 : (f_old / (f_old + 1.0));
  double new_freq = f_new / (f_new + 1.0);

  double freq_delta = new_freq - old_freq;
  params->cache_feature_sum[1] += freq_delta;
  params->cache_feature_sum_sq[1] += new_freq * new_freq - old_freq * old_freq;

  // Feature 3: 最新IRT从irt_values[0]变为new_irt
  double old_irt_feature = calculate_irt_feature(obj->LOH.irt_values[0]);
  double new_irt_feature = calculate_irt_feature(new_irt);

  double irt_delta = new_irt_feature - old_irt_feature;
  params->cache_feature_sum[3] += irt_delta;
  params->cache_feature_sum_sq[3] += new_irt_feature * new_irt_feature - old_irt_feature * old_irt_feature;

  // Feature 4,5: IRT历史移动的更新
  // ...
}
```

## 6. 关键设计原则

### 6.1 差异化统计策略
- **全局性能**: 仅warmup后统计，提供准确的性能基线
- **命中特征**: 仅warmup后统计，避免不稳定期的噪声干扰
- **缓存内容**: 始终统计，反映真实的缓存状态变化

### 6.2 省略feature0的原因
缓存内容特征统计中省略feature0 (recency)，因为:
- 每次访问都会改变所有对象的相对recency
- 全局更新所有对象的成本过高
- ThreeLCache等算法也采用类似策略

### 6.3 同级别选择策略
在相同优先级内选择更老的对象:
- 频率表和尺寸桶采用双向链表，从尾部选择
- 新对象添加到头部，尾部保存更老对象
- 符合LRU原则，提高缓存效率

### 6.4 强化学习集成
- 38维状态向量涵盖性能、特征分布、缓存状态
- Actor-Critic网络提供权重更新
- 共享内存实现C++与Python的高效通信

这个架构的核心优势是**多维度特征融合**和**自适应学习能力**，通过差异化的统计策略在不同阶段提供准确的训练数据，实现了传统启发式算法与现代机器学习方法的有效结合。
