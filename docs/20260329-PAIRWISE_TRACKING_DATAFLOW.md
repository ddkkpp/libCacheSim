# LOH Pairwise 跟踪数据结构与调用流程（2026-03-29）

本文补充当前 C 侧 pairwise 反馈链路的实现细节，覆盖：
- 核心数据结构
- 关键函数（作用、调用时机、处理过程）
- 同步时机与 TTL 检查语义
- C -> Python 事件语义对齐

涉及代码文件：
- libCacheSim/cache/eviction/LOH.c

## 1. 设计目标

pairwise 机制用于把一次驱逐决策拆成对比样本：
- evicted: 被驱逐对象
- kept: 同轮候选但未被驱逐对象

在后续运行中分别观测两侧生命周期，再发送一个 event_type=2 的对比事件给 Python。该事件携带：
- penalty_version: 关联的状态版本
- eviction_to_access: evicted_life
- observed_lifetime: kept_life
- obj_id / obj_size: 使用 evicted 侧对象信息

## 2. 核心数据结构

### 2.1 loh_candidate_pair_t（单个 pair 实体）

定义位置：LOH.c 的 pairwise 结构体区域。

字段语义：
- penalty_version: 创建 pair 时抓取的版本号
- evicted_obj_id / kept_obj_id: 两侧对象 id
- evicted_obj_size: evicted 侧对象大小
- decision_timestamp: 创建 pair 的时间戳
- have_evicted / have_kept: 两侧是否已观测完成
- evicted_lifetime / kept_lifetime: 两侧生命周期

### 2.2 三张索引表（都在 LOH_params_t 中）

- pair_track_by_evicted: key=evicted_obj_id, value=GSList(pair*)
- pair_track_by_kept: key=kept_obj_id, value=GSList(pair*)
- pair_track_by_version: key=penalty_version, value=GSList(pair*)

说明：
- value 使用 GSList，而不是单指针。
- 这允许同一个对象同时处于多个 pair，不做互斥清理。
- 一次驱逐可对应多个 kept：实现上是多个 pair 共享同一个 evicted_obj_id，
   每个 pair 独立维护 have_kept/kept_lifetime。

## 3. 辅助函数（索引维护）

### 3.1 loh_pair_track_get_list / loh_pair_track_get_list_by_version

作用：
- 从哈希表中读取某个 key 对应的 pair 列表。

调用时机：
- add/del/update 查询入口。

过程：
- 只读获取 GSList*，不改表。

### 3.2 loh_pair_track_add_ref / loh_pair_track_add_ref_by_version

作用：
- 将 pair 挂到对象索引或版本索引。

调用时机：
- loh_pair_track_create 新建 pair 时。

过程：
- 取出旧列表
- g_slist_prepend 插入 pair
- 写回哈希表

### 3.3 loh_pair_track_del_ref / loh_pair_track_del_ref_by_version

作用：
- 将 pair 从某个 key 的列表中移除。

调用时机：
- pair 完成发送后 remove。

过程：
- g_slist_remove 删除
- 列表空则删 key，非空则写回新头指针

## 4. 生命周期函数（核心）

### 4.1 loh_pair_track_create

作用：
- 为一次驱逐决策创建 pair。

调用时机：
- LOH_to_evict 选出 obj_to_evict 后
- 根据策略选 kept（runner_up 和随机补齐）时调用

过程：
1. 校验参数与开关
2. 记录 penalty_version=loh_current_state_version(params)
3. 记录 decision_timestamp
4. 分别挂入 evicted/kept/version 三张索引表

### 4.2 loh_pair_track_on_evicted_event

作用：
- 回填 pair 的 evicted_life。

调用时机：
- ghost miss: 对象被驱逐后再次访问 miss
- ghost aged-out: ghost entry 过期淘汰

过程：
1. 在 pair_track_by_evicted 按 obj_id 找到所有相关 pair
2. 对每个 pair 设置 have_evicted=true 和 evicted_lifetime
3. 调用 try_emit

### 4.3 loh_pair_track_on_kept_hit

作用：
- 回填 kept_life（hit 观测路径）。

调用时机：
- 请求命中且命中对象曾作为 kept 出现时

过程：
1. 在 pair_track_by_kept 按 obj_id 找列表
2. 对每个未完成 kept 的 pair，计算 now - decision_timestamp
3. 设置 have_kept=true 后调用 try_emit

### 4.4 loh_pair_track_on_kept_evict

作用：
- 回填 kept_life（miss 观测路径）。

调用时机：
- 对象曾作为 kept，后续被驱逐，再次访问 miss（ghost miss 分支）

过程：
1. 在 pair_track_by_kept 查找相关 pair
2. 对未完成 kept 的 pair 计算 kept_life
3. 设置 have_kept=true 后调用 try_emit

### 4.5 loh_pair_track_ttl_check_window

作用：
- 对固定窗口前一个目标版本做 TTL 检查与补齐。

调用时机：
- 仅在 sync_with_actor_critic 路径调用（包括 fast/non-fast）
- 不在每次 to_evict 调用
- 调用参数使用自增后的 state_version（即本轮已写入的新版本）

过程：
1. current_version 由调用方在 sync 中传入（state_version 自增后的值）
2. 计算 target_version=current_version-loh_penalty_ttl_versions
3. 只取 pair_track_by_version[target_version]
4. 对缺失一侧的 pair 用 now_life 补齐
5. 调用 try_emit

说明：
- 这里不遍历全部版本，只检查固定目标版本。
- 触发频率由 sync 周期决定。

### 4.6 loh_pair_track_try_emit

作用：
- 两侧都 ready 时发送 event_type=2，并清理 pair。

调用时机：
- on_evicted_event / on_kept_hit / on_kept_evict / ttl_check_window

过程：
1. 检查 have_evicted && have_kept
2. 归一化生命周期为非负
3. enqueue_penalty(..., event_type=2, observed_lifetime=kept_life)
4. loh_pair_track_remove 从三张表移除并释放 pair

### 4.7 loh_pair_track_remove

作用：
- pair 的统一收尾。

调用时机：
- try_emit 成功发送后

过程：
- 分别从 evicted/kept/version 三张索引删除
- pair_track_count--
- g_free(pair)

## 5. 调用链路总览

### 5.1 创建链路（决策阶段）

1. LOH_to_evict 完成候选评分并确定驱逐对象
2. 依据 kept 策略挑选 kept 对象
3. 对每个 (evicted, kept) 调用 loh_pair_track_create

### 5.2 观测链路（请求阶段）

1. 命中路径可触发 loh_pair_track_on_kept_hit
2. ghost miss 路径可触发
   - loh_pair_track_on_evicted_event
   - loh_pair_track_on_kept_evict
3. ghost aged-out 可触发 loh_pair_track_on_evicted_event

### 5.3 TTL 链路（同步阶段）

1. RL sync 周期到达，进入 sync_with_actor_critic
2. 在 state_version 递增后立即调用
3. 调用 loh_pair_track_ttl_check_window(params, state_version)
4. 对 target_version 做一次定点补齐并尝试发送

## 6. 与 Python 端的事件对齐

event_type=2 由 C 侧 enqueue_penalty 写入共享内存，Python 侧读取后用于 pairwise reward 回填。

语义约定：
- eviction_to_access: evicted_life
- observed_lifetime: kept_life
- penalty_version: 训练样本版本定位键

当 Python 尚未建立 version_to_pos 映射时，会进入 pending 队列，等待后续回放。

## 7. 关键不变量

- 同一个对象 id 可以对应多个 pair（列表存储保证）。
- have_kept 是 pair 级字段，不是对象级全局字段，不会跨 pair 互相覆盖。
- pair 只有在两侧都 ready 时才 emit。
- TTL 仅对固定 target_version 生效，不做全表扫描。
- TTL 调用时机在 sync，不在每次驱逐。

## 8. 维护建议

- 若后续调整 shm_data_t 或 penalty_entry_t 字段，必须同步 Python 端结构。
- 若新增 pair 事件类型，先定义 event_type 语义，再改 Python 解析。
- 调整 TTL 窗口时，优先通过 LOH_EXCLUDE_RECENT_STEPS / LOH_PENALTY_TTL_VERSIONS 统一控制。
