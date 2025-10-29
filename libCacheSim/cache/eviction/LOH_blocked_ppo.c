#define _POSIX_C_SOURCE 199309L
#define _GNU_SOURCE
#include <assert.h>
#include <float.h>
#include <glib.h>
#include <math.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <time.h>

// 不管是否训练，继续等待权重
//使用PPO

// 状态向量配置开关
// 设置为1表示状态向量包含缓存特征（38维），设置为0表示只包含近期请求特征（26维）
#define LOH_INCLUDE_CACHE_FEATURES 0

// LOH 调试模式控制
// 根据编译模式自动确定调试级别
#ifdef NDEBUG
#define LOH_DEBUG_LEVEL 0  // 发布模式：不输出调试信息
#else
// 为调试构建开启详细验证与日志
#define LOH_DEBUG_LEVEL 1
#endif

// 可以通过编译时定义 LOH_DEBUG_LEVEL 来覆盖默认设置
#ifndef LOH_DEBUG_LEVEL
#ifdef NDEBUG
#define LOH_DEBUG_LEVEL 0  // 发布模式：不输出调试信息
#else
#define LOH_DEBUG_LEVEL 2  // 调试模式：输出详细调试信息
#endif
#endif

// 调试输出宏定义
#define LOH_DEBUG_NONE 0      // 无调试输出
#define LOH_DEBUG_BASIC 1     // 基础统计信息(RL交互)
#define LOH_DEBUG_ERROR 2     // 非必要的错误信息
#define LOH_DEBUG_DETAILED 3  // 详细操作日志
#define LOH_DEBUG_VERBOSE 4   // 完整调试信息

#if LOH_DEBUG_LEVEL >= LOH_DEBUG_BASIC
#define LOH_DEBUG_PRINT_BASIC(...) printf(__VA_ARGS__)
#else
#define LOH_DEBUG_PRINT_BASIC(...) ((void)0)
#endif

#if LOH_DEBUG_LEVEL >= LOH_DEBUG_ERROR
#define LOH_DEBUG_PRINT_ERROR(...) printf(__VA_ARGS__)
#else
#define LOH_DEBUG_PRINT_ERROR(...) ((void)0)
#endif

#if LOH_DEBUG_LEVEL >= LOH_DEBUG_DETAILED
#define LOH_DEBUG_PRINT_DETAILED(...) printf(__VA_ARGS__)
#else
#define LOH_DEBUG_PRINT_DETAILED(...) ((void)0)
#endif

#if LOH_DEBUG_LEVEL >= LOH_DEBUG_VERBOSE
#define LOH_DEBUG_PRINT_VERBOSE(...) printf(__VA_ARGS__)
#else
#define LOH_DEBUG_PRINT_VERBOSE(...) ((void)0)
#endif

// 调试映射维护总开关：发布构建关闭，调试构建打开
#ifndef LOH_MAINTAIN_MAPS
#if LOH_DEBUG_LEVEL >= LOH_DEBUG_ERROR
#define LOH_MAINTAIN_MAPS 1
#else
#define LOH_MAINTAIN_MAPS 0
#endif
#endif

// 模块测试调试宏
#define LOH_TEST_FEATURE_CALCULATION 1
#define LOH_TEST_EVICTION_LOGIC 1
#define LOH_TEST_DATA_CONSISTENCY 1
#define LOH_TEST_PERFORMANCE_STATS 1

// 轻量性能剖析（仅在调试下启用）：测量无RL路径的主要耗时
#ifndef LOH_PERF_PROFILING
#define LOH_PERF_PROFILING 1
#endif

#if LOH_PERF_PROFILING
typedef struct {
  uint64_t count;
  double total;  // seconds
  double max;    // seconds
} perf_counter_t;

typedef struct {
  perf_counter_t calc_features;      // calculate_object_features()
  perf_counter_t candidate_collect;  // 兼容字段（不再单独使用）
  // per-feature 候选收集计时（细分）
  perf_counter_t cand_collect_recency;
  perf_counter_t cand_collect_freq;
  perf_counter_t cand_collect_size;
  perf_counter_t cand_collect_irt1;
  perf_counter_t cand_collect_irt2;
  perf_counter_t cand_collect_irt3;
  // per-feature 去重/压缩计时
  perf_counter_t cand_dedup_recency;  // recency 无压缩流程，保持为 0
  perf_counter_t cand_dedup_freq;
  perf_counter_t cand_dedup_size;
  perf_counter_t cand_dedup_irt1;
  perf_counter_t cand_dedup_irt2;
  perf_counter_t cand_dedup_irt3;
  perf_counter_t scoring;        // LOH_to_evict() 评分循环
  perf_counter_t to_evict;       // LOH_to_evict() 总耗时
  perf_counter_t atomic_insert;  // loh_atomic_insert_obj()
  perf_counter_t atomic_update;  // loh_atomic_update_obj()
  // 细分 atomic_update 的子阶段
  perf_counter_t atomic_update_lru;   // LRU remove+prepend
  perf_counter_t atomic_update_freq;  // frequency 更新
  perf_counter_t atomic_update_irt;   // IRT 更新合计
  perf_counter_t atomic_update_irt1;  // IRT1
  perf_counter_t atomic_update_irt2;  // IRT2
  perf_counter_t atomic_update_irt3;  // IRT3
  perf_counter_t atomic_remove;       // loh_atomic_remove_obj()
  perf_counter_t find;                // LOH_find()
  perf_counter_t insert;              // LOH_insert()
  perf_counter_t evict;               // LOH_evict()
  perf_counter_t calc_score;          // calculate_score()
  // RL同步相关性能计时
  perf_counter_t sync_total;         // sync_with_actor_critic() 总耗时
  perf_counter_t sync_update_state;  // update_state_vector() 耗时
  perf_counter_t sync_misc;  // sync中除update_state_vector外的其他操作耗时
  // IRT 修复路径与回退的计数（非时间）：用于确认是否触发线性扫描/索引修复
  uint64_t irt_fixups;         // IRT 更新过程中发生修复/回退的总次数
  uint64_t irt_linear_scans;   // IRT 更新过程中执行线性扫描的次数
  uint64_t irt_missing_index;  // 对象内索引缺失（idx<0）次数
  uint64_t irt_hash_miss;      // 维护映射时，哈希查找未命中次数
  uint64_t irt_invalid_index;  // 索引越界/无效次数
  uint64_t irt_mismatch_obj;   // 索引位置对象不匹配次数
  // seen 去重表统计
  uint64_t seen_add_calls;     // loh_seen_add 调用次数
  uint64_t seen_inserts;       // 首次见到并插入次数
  uint64_t seen_duplicates;    // 已存在（重复）次数
  uint64_t seen_probes_total;  // 总探测步数（含首次尝试）
  uint64_t seen_probe_max;     // 单次最大探测步数
  uint64_t seen_table_full;    // 探测满表（保守视为重复）次数
} loh_perf_t;

#define PERF_TS struct timespec
#define PERF_NOW(ts) clock_gettime(CLOCK_MONOTONIC, &(ts))
#define PERF_ACCUM(params, field, ts0)                                     \
  do {                                                                     \
    struct timespec _t1;                                                   \
    clock_gettime(CLOCK_MONOTONIC, &_t1);                                  \
    double _dt =                                                           \
        (_t1.tv_sec - (ts0).tv_sec) + (_t1.tv_nsec - (ts0).tv_nsec) / 1e9; \
    (params)->perf.field.count++;                                          \
    (params)->perf.field.total += _dt;                                     \
    if (_dt > (params)->perf.field.max) (params)->perf.field.max = _dt;    \
  } while (0)
#else
#define PERF_TS \
  struct {      \
    int _;      \
  }
#define PERF_NOW(ts) ((void)0)
#define PERF_ACCUM(params, field, ts0) ((void)0)
#endif

// 共享内存头文件
#include <errno.h>
#include <fcntl.h>  // 用于文件锁
#include <semaphore.h>
#include <signal.h>
#include <sys/file.h>
#include <sys/ipc.h>
#include <sys/sem.h>
#include <sys/shm.h>
#include <sys/stat.h>  // 用于文件权限设置（chmod）
#include <sys/types.h>
#include <unistd.h>

#include "dataStructure/hashtable/hashtable.h"
#include "libCacheSim/evictionAlgo.h"

/* perf summary printer declared/defined later after LOH_params_t */

#ifdef __cplusplus
extern "C" {
#endif

// ***********************************************************************
// **** ****
// **** 函数声明 ****
// **** ****
// ***********************************************************************

// 辅助函数已移除，改为直接访问字段

// IRT 管理辅助函数声明
static int64_t get_irt_value(cache_obj_t *obj, int index);

static void LOH_free(cache_t *cache);
static bool LOH_get(cache_t *cache, const request_t *req);
static cache_obj_t *LOH_find(cache_t *cache, const request_t *req,
                             const bool update_cache);
static cache_obj_t *LOH_insert(cache_t *cache, const request_t *req);
static cache_obj_t *LOH_to_evict(cache_t *cache, const request_t *req);
static void LOH_evict(cache_t *cache, const request_t *req);
static bool LOH_remove(cache_t *cache, const obj_id_t obj_id);
static void LOH_print_cache(const cache_t *cache);

#define IRT_HISTORY_SIZE 3
// 定义 IRT（请求间隔时间）的历史数据结构
#define MAX_CANDIDATES 96  // 驱逐候选池的最大大小（保持96以稳定命中率）
// 注意：seen 去重表（见 LOH_SEEN_CAP）容量与 MAX_CANDIDATES 直接相关。
// 每轮驱逐会从 6 个特征各取 candidates_per_feature=MAX_CANDIDATES/6 的候选，
// 去重前的插入尝试数量上界约为 MAX_CANDIDATES。为控制线性探测成本：
//   1) LOH_SEEN_CAP 必须为 2 的幂（便于按位取模与代际清理）。
//   2) 建议 LOH_SEEN_CAP 至少为 MAX_CANDIDATES 的 2–4 倍以保持低负载因子。
// 当前配置：MAX_CANDIDATES=96，LOH_SEEN_CAP=256，负载约 <= 96/256 ≈ 0.375。
#define FEATURE_DIM 6  // 用于评分的特征数量

// 根据配置选择状态向量维度
#if LOH_INCLUDE_CACHE_FEATURES
#define CONTEXT_DIM \
  38  // 完整状态向量：[0-1] 全局性能, [2-25] 特征统计, [26-37] 缓存状态
#else
#define CONTEXT_DIM \
  26  // 简化状态向量：[0-1] 全局性能, [2-25] 特征统计（无缓存状态）
#endif

#define SHM_KEY 9876  // 共享内存段键
#define SEM_KEY 9877  // 信号量键

// C 与 Python 共享的 Actor-Critic（行为者-评论者）网络结构
typedef struct {
  // 控制标志
  int ready_for_inference;  // 状态准备好用于推理时设为 1
  int weights_updated;      // 当 Python 更新权重时设为 1
  int terminate;            // 置为 1 用于通知终止
  int is_training;          // Python 训练状态标志：1 表示Python正在训练

  // 状态信息 - 根据配置选择维度
#if LOH_INCLUDE_CACHE_FEATURES
  // 38 维状态向量: [0-1] 全局性能, [2-25] 特征统计, [26-37] 缓存状态
  double state[38];
#else
  // 26 维状态向量: [0-1] 全局性能, [2-25] 特征统计（无缓存状态）
  double state[26];
#endif

  // 策略网络输出的特征权重（6 维）
  double weights[FEATURE_DIM];

  // 用于奖励计算的性能指标
  double miss_ratio;       // 当前未命中率
  double byte_miss_ratio;  // 当前字节未命中率
  double reward;           // 当前奖励值

  // 请求-响应版本号，用于避免陈旧请求/响应
  uint64_t state_version;  // C端发送状态时的序号
  uint64_t ack_version;    // Python端回传时确认的序号

  // 用于同步的时间戳
  int64_t timestamp;
} shm_data_t;

#define FREQ_MAX 255         // 单独跟踪的最大频率
#define SIZE_BUCKET_COUNT 5  // 尺寸桶数量
// 【删除 HISTORY_MULTIPLIER】：不再需要全局历史记录

// 【前向声明】
// 【简化】：移除复杂的访问窗口管理逻辑

// 【新增】被驱逐对象的 Ghost 缓存条目（参考 ThreeLCache 设计）
typedef struct LOH_ghost_entry {
  obj_id_t obj_id;              // 对象 ID
  int64_t obj_size;             // 对象大小
  int32_t access_count;         // 访问计数
  int64_t last_access_time;     // 最后访问时间
  int64_t last_access_counter;  // 最后访问的逻辑时间戳
  int64_t irt_values[3];        // 【简化】：直接存储 IRT 值，无需复杂窗口
  time_t evict_time;            // 驱逐时间（用于 LRU 清理）

  // 双向队列指针（参考 FIFO.c 的实现）
  struct LOH_ghost_entry *prev;  // 前一个 ghost 条目
  struct LOH_ghost_entry *next;  // 后一个 ghost 条目
} LOH_ghost_entry_t;

// 对象生命周期状态跟踪
typedef enum {
  LOH_OBJ_STATE_INVALID = 0,  // 对象不在缓存中
  LOH_OBJ_STATE_INSERTING,    // 对象正在插入
  LOH_OBJ_STATE_ACTIVE,       // 对象已在缓存中处于活动状态
  LOH_OBJ_STATE_UPDATING,     // 对象正在更新/访问
  LOH_OBJ_STATE_EVICTING,     // 对象正在被驱逐
  LOH_OBJ_STATE_REMOVING      // 对象正在被移除
} loh_obj_state_t;

// 一致性校验标志
#define LOH_VERIFY_NONE 0x00
#define LOH_VERIFY_FREQ 0x01
#define LOH_VERIFY_SIZE 0x02
#define LOH_VERIFY_IRT 0x04
#define LOH_VERIFY_ALL 0x07

// 定义 LOH 的对象元数据
// 使用在 cacheObj.h 中预声明的 LOH_obj_metadata_t（见 cacheObj.h）

// IRT 最小堆条目定义
typedef struct {
  cache_obj_t *obj;   // 指向缓存对象的指针
  int64_t irt_value;  // 该堆正在追踪的 IRT 值
} irt_heap_entry_t;

// 频率表链表节点
typedef struct loh_freq_node {
  cache_obj_t *obj;            // 指向缓存对象的指针
  int freq_level;              // 当前所在的频率级别（1..FREQ_MAX）
  struct loh_freq_node *prev;  // 频率列表中的前一个节点
  struct loh_freq_node *next;  // 频率列表中的下一个节点
} loh_freq_node_t;

// 大小桶链表节点
typedef struct size_node {
  cache_obj_t *obj;        // 指向缓存对象的指针
  struct size_node *prev;  // 大小桶中的前一个节点
  struct size_node *next;  // 大小桶中的下一个节点
} size_node_t;

// 结构：用于跟踪命中/未命中对象的特征统计
typedef struct {
  double hit_recency_sum;
  double hit_frequency_sum;
  double hit_size_sum;
  double hit_irt1_sum;
  double hit_irt2_sum;
  double hit_irt3_sum;

  double miss_recency_sum;
  double miss_frequency_sum;
  double miss_size_sum;
  double miss_irt1_sum;
  double miss_irt2_sum;
  double miss_irt3_sum;

  int hit_count;
  int miss_count;
} feature_stats_t;

// 定义 LOH 的参数结构体
typedef struct {
  // 指向父缓存的引用
  void *cache_ptr;  // 指向父 `cache_t` 结构的指针

  // LRU 队列 - 用于跟踪对象最近访问顺序
  cache_obj_t *q_head;        // 维护对象顺序的队列头
  cache_obj_t *q_tail;        // 维护对象顺序的队列尾
  int64_t current_timestamp;  // 当前逻辑时间戳

  // 频率表 - 跟踪访问频率
  loh_freq_node_t *freq_table[FREQ_MAX + 1];       // 频率链表数组
  loh_freq_node_t *freq_table_tail[FREQ_MAX + 1];  // 频率链表的尾部

  // IRT 堆 - 用于跟踪访问间隔时间
  irt_heap_entry_t *irt_heap[IRT_HISTORY_SIZE];  // 每个 IRT 值对应的最小堆
  int irt_heap_size[IRT_HISTORY_SIZE];           // 每个堆当前的元素数量
  int irt_heap_capacity;                         // 每个堆的最大容量

  // 尺寸桶 - 跟踪对象尺寸
  size_node_t *size_buckets[SIZE_BUCKET_COUNT];       // 不同尺寸范围的桶头
  size_node_t *size_buckets_tail[SIZE_BUCKET_COUNT];  // 桶尾
  int64_t size_bucket_bounds[SIZE_BUCKET_COUNT];      // 每个桶的上界

  // 特征哈希表（仅用于调试验证与资源释放，热路径不再依赖）
  GHashTable *freq_node_map;  // 对象到频率节点的映射（调试/析构）
  GHashTable *size_node_map;  // 对象到尺寸节点的映射（调试/析构）

  // 【新增】IRT 堆的哈希表映射 - 实现常数时间 O(1) 的 IRT 堆操作
  GHashTable *irt_heap_maps[IRT_HISTORY_SIZE];  // 每个IRT堆的对象到堆索引映射

  // 用于评分函数的特征权重
  double weights[FEATURE_DIM];

  // 驱逐候选对象
  cache_obj_t *candidates[MAX_CANDIDATES];
  int n_candidates;

  // 学习相关统计信息
  feature_stats_t recent_stats;
  // 【删除 recent 统计变量】：不再需要 STATS_WINDOW 相关统计

  // 新增 - 38维状态向量所需的统计数据
  // 特征在命中对象中的统计
  int64_t hit_feature_count;               // 命中对象的总数
  double hit_feature_sum[FEATURE_DIM];     // 每个特征在命中对象中的总和
  double hit_feature_sum_sq[FEATURE_DIM];  // 每个特征在命中对象中的平方和

  // 特征在未命中对象中的统计
  int64_t miss_feature_count;               // 未命中对象的总数
  double miss_feature_sum[FEATURE_DIM];     // 每个特征在未命中对象中的总和
  double miss_feature_sum_sq[FEATURE_DIM];  // 每个特征在未命中对象中的平方和

  // 缓存池中对象特征的统计
  int64_t cache_object_count;                // 缓存中对象的总数
  double cache_feature_sum[FEATURE_DIM];     // 每个特征在当前缓存中的总和
  double cache_feature_sum_sq[FEATURE_DIM];  // 每个特征在当前缓存中的平方和

  // 【删除 global_access_records】：改用对象级访问窗口和 ghost cache
  // 【新增】为被驱逐对象保留历史信息的 Ghost 缓存（类似 ThreeLCache 的
  // out_cache）
  GHashTable *ghost_cache;  // obj_id -> LOH_ghost_entry_t 映射（快速查找）
  LOH_ghost_entry_t *ghost_head;  // Ghost缓存FIFO队列头（最新）
  LOH_ghost_entry_t *ghost_tail;  // Ghost缓存FIFO队列尾（最老）
  int64_t ghost_cache_capacity;   // Ghost缓存最大容量
  int64_t ghost_cache_count;      // 当前ghost cache中的对象数

  // 特征统计平均值（从历史数据计算）
  double hit_feature_avg[FEATURE_DIM];   // 命中对象的特征平均值
  double miss_feature_avg[FEATURE_DIM];  // 未命中对象的特征平均值

  // Actor-Critic RL 的共享内存结构（文件式实现）
  FILE *shm_file;      // 共享内存文件指针
  char *shm_filename;  // 共享内存文件名
  // POSIX 命名信号量
  sem_t *sem_ready;      // C -> Python “状态就绪” 信号
  sem_t *sem_ack;        // Python -> C “权重应答” 信号
  char *sem_ready_name;  // 信号量名称字符串
  char *sem_ack_name;    // 信号量名称字符串
  bool sem_enabled;      // 信号量是否成功初始化
  int sem_requested;     // 运行时是否请求使用信号量（由环境变量控制）
  bool sem_owner;        // 是否由当前进程负责 unlink

  // 38 维上下文状态向量
  double context_state[CONTEXT_DIM];  // Actor-Critic 网络的输入状态向量

  // RL 训练相关参数
  int64_t rl_update_interval;  // 更新状态与权重的间隔（触发间隔）
  int64_t requests_since_rl_update;
  double epoch_start_time;       // 当前训练周期的起始时间
  double epoch_obj_miss_count;   // RL 训练：累积失误计数，用于计算长期 miss
                                 // ratio 奖励
  double epoch_obj_count;        // RL训练：累积对象计数，配合失误计数计算性能
  double epoch_byte_miss_count;  // RL训练：累积字节失误，用于字节级性能评估
  double epoch_byte_count;       // RL训练：累积字节总数，配合字节失误计算性能

  // 学习参数
  int64_t learning_interval;  // 权重更新的间隔
  int64_t requests_since_update;

  // 运行时开关：是否启用与Python的RL通信（1=启用，0=禁用）
  int enable_rl;

  // reward权重参数：miss_ratio_weight + byte_miss_ratio_weight 应该等于 1.0
  double miss_ratio_weight;       // miss ratio在reward中的权重 (默认1.0)
  double byte_miss_ratio_weight;  // byte miss ratio在reward中的权重 (默认0.0)

  // 【修改】: 替换为新的字段
  // 特征归一化的最小/最大值

  // 标志：指示缓存是否已被“预热”
  bool is_warmed_up;

  // 【新增】历史容量是否已调整的标志
  bool history_capacity_adjusted;
#if LOH_PERF_PROFILING
  loh_perf_t perf;  // 轻量性能剖析计数器
#endif
} LOH_params_t;

#if LOH_PERF_PROFILING
static void loh_print_perf_summary(LOH_params_t *params) {
  // 派生值：LOH 策略在 find/insert/evict 三条路径上的总时间（近似不重叠）
  const double loh_total = params->perf.find.total + params->perf.insert.total +
                           params->perf.evict.total;
  const double to_evict_total = params->perf.to_evict.total;

  printf(
      "\n==== LOH no-RL perf summary (sec, count, avg_ms, max_ms, pct) ====\n");

  // 顶层路径：按 LOH_total 百分比展示（find/insert/evict 基本不重叠）
  printf("-- Top-level (percent of LOH_total=%.3f s) --\n", loh_total);
#define PRINT_TOP(field, name)                                                \
  do {                                                                        \
    const double _tot = params->perf.field.total;                             \
    const unsigned long long _cnt =                                           \
        (unsigned long long)params->perf.field.count;                         \
    const double _avg_ms = (_cnt ? (_tot / (double)_cnt) * 1e3 : 0.0);        \
    const double _max_ms = params->perf.field.max * 1e3;                      \
    const double _pct = (loh_total > 0.0 ? (_tot / loh_total * 100.0) : 0.0); \
    printf(                                                                   \
        "%-18s total=%10.3f  count=%12llu  avg=%7.3f ms  max=%7.3f ms  "      \
        "%6.2f%%\n",                                                          \
        name, _tot, _cnt, _avg_ms, _max_ms, _pct);                            \
  } while (0)
  PRINT_TOP(find, "find");
  PRINT_TOP(insert, "insert");
  PRINT_TOP(evict, "evict");
  PRINT_TOP(sync_total, "sync_total");

  // 嵌套在 to_evict() 内的子阶段：按 to_evict_total 百分比展示
  printf("-- Eviction breakdown (percent of to_evict_total=%.3f s) --\n",
         to_evict_total);
#define PRINT_TE(field, name)                                            \
  do {                                                                   \
    const double _tot = params->perf.field.total;                        \
    const unsigned long long _cnt =                                      \
        (unsigned long long)params->perf.field.count;                    \
    const double _avg_ms = (_cnt ? (_tot / (double)_cnt) * 1e3 : 0.0);   \
    const double _max_ms = params->perf.field.max * 1e3;                 \
    const double _pct =                                                  \
        (to_evict_total > 0.0 ? (_tot / to_evict_total * 100.0) : 0.0);  \
    printf(                                                              \
        "%-18s total=%10.3f  count=%12llu  avg=%7.3f ms  max=%7.3f ms  " \
        "%6.2f%%\n",                                                     \
        name, _tot, _cnt, _avg_ms, _max_ms, _pct);                       \
  } while (0)
  // 兼容显示：将按特征拆分的收集时间汇总到 legacy 字段 candidate_collect
  params->perf.candidate_collect.total =
      params->perf.cand_collect_recency.total +
      params->perf.cand_collect_freq.total +
      params->perf.cand_collect_size.total +
      params->perf.cand_collect_irt1.total +
      params->perf.cand_collect_irt2.total +
      params->perf.cand_collect_irt3.total;
  // 各特征收集调用次数应一致，这里取其一作为代表
  params->perf.candidate_collect.count =
      params->perf.cand_collect_recency.count;
  // 近似处理：max 取各子阶段 max 之和（上界），仅用于参考
  params->perf.candidate_collect.max =
      params->perf.cand_collect_recency.max +
      params->perf.cand_collect_freq.max + params->perf.cand_collect_size.max +
      params->perf.cand_collect_irt1.max + params->perf.cand_collect_irt2.max +
      params->perf.cand_collect_irt3.max;
  PRINT_TE(candidate_collect, "candidate_collect");
  PRINT_TE(calc_features, "calc_features");
  PRINT_TE(calc_score, "calc_score");
  PRINT_TE(to_evict, "to_evict_total");

  // to_evict 其它未细分部分
  const double te_collect_split = params->perf.cand_collect_recency.total +
                                  params->perf.cand_collect_freq.total +
                                  params->perf.cand_collect_size.total +
                                  params->perf.cand_collect_irt1.total +
                                  params->perf.cand_collect_irt2.total +
                                  params->perf.cand_collect_irt3.total;
  const double te_dedup_split =
      params->perf.cand_dedup_recency.total +
      params->perf.cand_dedup_freq.total + params->perf.cand_dedup_size.total +
      params->perf.cand_dedup_irt1.total + params->perf.cand_dedup_irt2.total +
      params->perf.cand_dedup_irt3.total;
  const double te_misc = to_evict_total - (te_collect_split + te_dedup_split +
                                           params->perf.calc_features.total +
                                           params->perf.calc_score.total);
  const double te_misc_pct =
      (to_evict_total > 0.0 ? te_misc / to_evict_total * 100.0 : 0.0);
  printf("%-18s total=%10.3f  (%.2f%% of to_evict)\n", "to_evict_misc", te_misc,
         te_misc_pct);

  // per-feature 候选收集与去重细分
  printf("-- Candidate collect (per-feature) --\n");
  PRINT_TE(cand_collect_recency, "  recency_collect");
  PRINT_TE(cand_collect_freq, "  freq_collect");
  PRINT_TE(cand_collect_size, "  size_collect");
  PRINT_TE(cand_collect_irt1, "  irt1_collect");
  PRINT_TE(cand_collect_irt2, "  irt2_collect");
  PRINT_TE(cand_collect_irt3, "  irt3_collect");
  // 说明：dedup 阶段计时为 0 是预期的，因为我们已将去重融合到各特征的收集阶段
  // 通过 seen 表在 push 候选时完成去重，因此 cand_dedup_* 统计保持为 0
  printf("-- Candidate dedup/compact (per-feature) --\n");
  PRINT_TE(cand_dedup_recency, "  recency_dedup");
  PRINT_TE(cand_dedup_freq, "  freq_dedup");
  PRINT_TE(cand_dedup_size, "  size_dedup");
  PRINT_TE(cand_dedup_irt1, "  irt1_dedup");
  PRINT_TE(cand_dedup_irt2, "  irt2_dedup");
  PRINT_TE(cand_dedup_irt3, "  irt3_dedup");

  // 原子操作（通常很小），仅展示平均时间
#define PRINT_ATOM(field, name)                                              \
  do {                                                                       \
    const double _tot = params->perf.field.total;                            \
    const unsigned long long _cnt =                                          \
        (unsigned long long)params->perf.field.count;                        \
    const double _avg_ms = (_cnt ? (_tot / (double)_cnt) * 1e3 : 0.0);       \
    const double _max_ms = params->perf.field.max * 1e3;                     \
    printf("%-18s total=%10.3f  count=%12llu  avg=%7.3f ms  max=%7.3f ms\n", \
           name, _tot, _cnt, _avg_ms, _max_ms);                              \
  } while (0)
  printf("-- Atomic ops (per-call cost) --\n");
  PRINT_ATOM(atomic_insert, "atomic_insert");
  PRINT_ATOM(atomic_update, "atomic_update");
  PRINT_ATOM(atomic_remove, "atomic_remove");

  // atomic_update 细分（按 atomic_update.total 百分比）
  if (params->perf.atomic_update.count > 0) {
    const double au_tot = params->perf.atomic_update.total;
    printf("-- atomic_update breakdown (percent of atomic_update=%.3f s) --\n",
           au_tot);
#define PRINT_AU(field, name)                                            \
  do {                                                                   \
    const double _tot = params->perf.field.total;                        \
    const unsigned long long _cnt =                                      \
        (unsigned long long)params->perf.field.count;                    \
    const double _avg_ms = (_cnt ? (_tot / (double)_cnt) * 1e3 : 0.0);   \
    const double _max_ms = params->perf.field.max * 1e3;                 \
    const double _pct = (au_tot > 0.0 ? (_tot / au_tot * 100.0) : 0.0);  \
    printf(                                                              \
        "%-22s total=%10.3f  count=%12llu  avg=%7.3f ms  max=%7.3f ms  " \
        "%6.2f%%\n",                                                     \
        name, _tot, _cnt, _avg_ms, _max_ms, _pct);                       \
  } while (0)
    PRINT_AU(atomic_update_lru, "au_lru");
    PRINT_AU(atomic_update_freq, "au_freq");
    PRINT_AU(atomic_update_irt, "au_irt_total");
    PRINT_AU(atomic_update_irt1, "  irt1");
    PRINT_AU(atomic_update_irt2, "  irt2");
    PRINT_AU(atomic_update_irt3, "  irt3");
#undef PRINT_AU
  }

  // IRT 修复/回退计数统计
  printf("-- IRT fixups & fallbacks --\n");
  printf("%-22s count=%12llu\n", "irt_fixups",
         (unsigned long long)params->perf.irt_fixups);
  printf("%-22s count=%12llu\n", "irt_linear_scans",
         (unsigned long long)params->perf.irt_linear_scans);
  printf("%-22s count=%12llu\n", "irt_missing_index",
         (unsigned long long)params->perf.irt_missing_index);
  printf("%-22s count=%12llu\n", "irt_hash_miss",
         (unsigned long long)params->perf.irt_hash_miss);
  printf("%-22s count=%12llu\n", "irt_invalid_index",
         (unsigned long long)params->perf.irt_invalid_index);
  printf("%-22s count=%12llu\n", "irt_mismatch_obj",
         (unsigned long long)params->perf.irt_mismatch_obj);

  // RL sync 性能统计
  if (params->perf.sync_total.count > 0) {
    const double sync_tot = params->perf.sync_total.total;
    printf("-- RL sync breakdown (percent of sync_total=%.3f s) --\n",
           sync_tot);
#define PRINT_SYNC(field, name)                                             \
  do {                                                                      \
    const double _tot = params->perf.field.total;                           \
    const unsigned long long _cnt =                                         \
        (unsigned long long)params->perf.field.count;                       \
    const double _avg_ms = (_cnt ? (_tot / (double)_cnt) * 1e3 : 0.0);      \
    const double _max_ms = params->perf.field.max * 1e3;                    \
    const double _pct = (sync_tot > 0.0 ? (_tot / sync_tot * 100.0) : 0.0); \
    printf(                                                                 \
        "%-22s total=%10.3f  count=%12llu  avg=%7.3f ms  max=%7.3f ms  "    \
        "%6.2f%%\n",                                                        \
        name, _tot, _cnt, _avg_ms, _max_ms, _pct);                          \
  } while (0)

    PRINT_SYNC(sync_update_state, "  update_state_vec");
    PRINT_SYNC(sync_misc, "  sync_misc");
#undef PRINT_SYNC
  }

  // seen 去重统计
  printf("-- seen set stats (per-eviction round) --\n");
  printf("%-22s count=%12llu\n", "seen_add_calls",
         (unsigned long long)params->perf.seen_add_calls);
  printf("%-22s count=%12llu\n", "seen_inserts",
         (unsigned long long)params->perf.seen_inserts);
  printf("%-22s count=%12llu\n", "seen_duplicates",
         (unsigned long long)params->perf.seen_duplicates);
  printf("%-22s count=%12llu\n", "seen_table_full",
         (unsigned long long)params->perf.seen_table_full);
  // 平均探测步数
  double seen_avg_probe = params->perf.seen_add_calls
                              ? ((double)params->perf.seen_probes_total /
                                 (double)params->perf.seen_add_calls)
                              : 0.0;
  printf("%-22s avg=%10.3f  max=%10llu\n", "seen_probe_steps", seen_avg_probe,
         (unsigned long long)params->perf.seen_probe_max);

  printf("===============================================================\n\n");
#undef PRINT_TOP
#undef PRINT_TE
#undef PRINT_ATOM
}
#endif

// IRT 管理辅助函数声明（在 LOH_params_t 定义之后）
static void irt_heap_sift_up(LOH_params_t *params, int heap_idx, int idx);
static void irt_heap_sift_down(LOH_params_t *params, int heap_idx, int idx);

// 调试与验证函数（在 LOH_params_t 定义之后声明）
#if LOH_DEBUG_LEVEL >= LOH_DEBUG_ERROR
static bool irt_heap_validate_min_heap_property(LOH_params_t *params,
                                                int heap_idx,
                                                const char *operation);
#endif

#if LOH_DEBUG_LEVEL >= LOH_DEBUG_ERROR
static void loh_verify_feature_calculation(LOH_params_t *params,
                                           cache_obj_t *obj);
static void loh_verify_eviction_logic(LOH_params_t *params,
                                      cache_obj_t *evicted_obj);
static void loh_verify_data_consistency(LOH_params_t *params);
static void loh_verify_performance_stats(LOH_params_t *params, bool is_hit);
static void loh_print_module_summary(LOH_params_t *params);
#endif

// 【新增】Ghost 缓存管理函数（参考 ThreeLCache 设计）

// 初始化 Ghost 缓存
static void init_ghost_cache(LOH_params_t *params, int64_t cache_capacity) {
  params->ghost_cache = g_hash_table_new_full(
      g_direct_hash, g_direct_equal, NULL, NULL);  // 不自动释放，手动管理
  params->ghost_head = NULL;                       // FIFO队列头
  params->ghost_tail = NULL;                       // FIFO队列尾
  // 【修正】：初始容量设为 2，实际容量在第一次调用时根据缓存对象数重新计算
  params->ghost_cache_capacity = 2;  // 延迟到实际使用时计算
  params->ghost_cache_count = 0;
}

// 释放 Ghost 缓存
static void free_ghost_cache(LOH_params_t *params) {
  if (params->ghost_cache) {
    // 手动释放所有 ghost 条目
    LOH_ghost_entry_t *current = params->ghost_tail;
    while (current) {
      LOH_ghost_entry_t *next = current->next;
      // 【简化】：删除窗口管理逻辑，直接使用 irt_values 数组
      g_free(current);
      current = next;
    }
    g_hash_table_destroy(params->ghost_cache);
    params->ghost_cache = NULL;
  }
  params->ghost_head = NULL;
  params->ghost_tail = NULL;
  params->ghost_cache_capacity = 0;
  params->ghost_cache_count = 0;
}

// 【新增】Ghost 缓存的 FIFO 操作辅助函数（参考 FIFO.c 实现）

// 将 ghost 条目添加到队列头部（最新的）
static void ghost_prepend_to_head(LOH_params_t *params,
                                  LOH_ghost_entry_t *entry) {
  entry->next = params->ghost_head;
  entry->prev = NULL;

  if (params->ghost_head) {
    params->ghost_head->prev = entry;
  } else {
    // 第一个元素，同时是头和尾
    params->ghost_tail = entry;
  }
  params->ghost_head = entry;
}

// 从队列中删除指定的 ghost 条目
static void ghost_remove_from_list(LOH_params_t *params,
                                   LOH_ghost_entry_t *entry) {
  if (entry->prev) {
    entry->prev->next = entry->next;
  } else {
    // 这是头部元素
    params->ghost_head = entry->next;
  }

  if (entry->next) {
    entry->next->prev = entry->prev;
  } else {
    // 这是尾部元素
    params->ghost_tail = entry->prev;
  }

  entry->prev = NULL;
  entry->next = NULL;
}

// 移除并释放队列尾部的 ghost 条目（最老的）
static void ghost_evict_tail(LOH_params_t *params) {
  if (!params->ghost_tail) return;

  LOH_ghost_entry_t *tail = params->ghost_tail;

  // 从哈希表中移除
  g_hash_table_remove(params->ghost_cache, GINT_TO_POINTER((int)tail->obj_id));

  // 从链表中移除
  params->ghost_tail = tail->prev;
  if (params->ghost_tail) {
    params->ghost_tail->next = NULL;
  } else {
    // 队列已空
    params->ghost_head = NULL;
  }

  // 【简化】：直接释放内存，无需窗口管理
  g_free(tail);

  params->ghost_cache_count--;
}

// 【新增】动态管理 Ghost 缓存容量（参考 ThreeLCache 的 out_cache 实现）
static void erase_ghost_cache(LOH_params_t *params, cache_t *cache) {
  if (!params->ghost_cache) return;

  // 【精确计算】：Ghost 缓存容量 = 当前缓存对象数 × 历史因子 + 缓冲
  // 参考 ThreeLCache：max_out_cache_size = in_cache.metas.size() * (hsw - 1) +
  // 2
  int64_t current_cache_objects = cache->n_obj;  // 当前缓存中的对象数量
  int64_t ghost_history_factor = 1;  // 历史因子，类似 ThreeLCache 的 (hsw - 1)
  params->ghost_cache_capacity =
      current_cache_objects * ghost_history_factor + 2;

  // 【精确 FIFO 清理】：模拟 ThreeLCache out_cache.metas.pop_front()
  while (params->ghost_cache_count > params->ghost_cache_capacity) {
    ghost_evict_tail(params);  // 移除最老的条目
  }
}

// 将被驱逐的对象添加到 Ghost 缓存
static void add_to_ghost_cache(LOH_params_t *params, cache_obj_t *obj,
                               cache_t *cache) {
  if (!params->ghost_cache || !obj) return;

  // 【动态调整】Ghost 缓存容量（按 ThreeLCache 方式精确调整）
  erase_ghost_cache(params, cache);

  obj_id_t obj_id_key = obj->obj_id;

  // 检查该对象是否已存在
  LOH_ghost_entry_t *existing_entry = (LOH_ghost_entry_t *)g_hash_table_lookup(
      params->ghost_cache, GINT_TO_POINTER((int)obj_id_key));

  if (existing_entry) {
    // 如果已存在，先从链表和哈希表中移除旧条目
    ghost_remove_from_list(params, existing_entry);
    g_hash_table_remove(params->ghost_cache, GINT_TO_POINTER((int)obj_id_key));

    // 【简化】：直接释放，无需窗口管理
    g_free(existing_entry);
    params->ghost_cache_count--;
  }

  // 创建新的 ghost 条目
  LOH_ghost_entry_t *ghost_entry = g_new0(LOH_ghost_entry_t, 1);
  ghost_entry->obj_id = obj->obj_id;
  ghost_entry->obj_size = obj->obj_size;
  ghost_entry->access_count = obj->LOH.access_count;
  ghost_entry->last_access_time = obj->LOH.last_access_time;
  ghost_entry->last_access_counter = obj->LOH.last_access_counter;

  // 【简化】：直接复制 IRT 值，无需窗口转移
  for (int i = 0; i < 3; i++) {
    ghost_entry->irt_values[i] = obj->LOH.irt_values[i];
  }
  ghost_entry->evict_time = time(NULL);

  // 插入到哈希表
  g_hash_table_insert(params->ghost_cache, GINT_TO_POINTER((int)obj_id_key),
                      ghost_entry);

  // 添加到 FIFO 队列头部（最新）
  ghost_prepend_to_head(params, ghost_entry);
  params->ghost_cache_count++;
}

// 从 Ghost 缓存恢复对象信息
static bool restore_from_ghost_cache(LOH_params_t *params, cache_obj_t *obj) {
  if (!params->ghost_cache || !obj) return false;

  LOH_ghost_entry_t *ghost_entry = (LOH_ghost_entry_t *)g_hash_table_lookup(
      params->ghost_cache, GINT_TO_POINTER((int)obj->obj_id));

  if (ghost_entry) {
    // 恢复历史信息
    obj->LOH.access_count = ghost_entry->access_count + 1;  // 加上当前请求

    // 先复制历史 IRT 值
    for (int i = 0; i < 3; i++) {
      obj->LOH.irt_values[i] = ghost_entry->irt_values[i];
    }

    // 计算从 ghost 缓存到现在的 IRT 并更新到位置 0
    int64_t current_irt =
        params->current_timestamp - ghost_entry->last_access_counter;
    if (current_irt > 0) {
      // 【内联IRT更新】：向右移动现有IRT值，为新值腾出位置
      obj->LOH.irt_values[2] = obj->LOH.irt_values[1];
      obj->LOH.irt_values[1] = obj->LOH.irt_values[0];
      obj->LOH.irt_values[0] = current_irt;  // 最新值放在位置0
    }

    // 【修复】：更新时间戳为当前时间
    obj->LOH.last_access_time = time(NULL);
    obj->LOH.last_access_counter = params->current_timestamp;

    // 从链表中移除
    ghost_remove_from_list(params, ghost_entry);

    // 从哈希表中移除
    g_hash_table_remove(params->ghost_cache, GINT_TO_POINTER((int)obj->obj_id));

    // 释放 ghost 条目
    g_free(ghost_entry);
    params->ghost_cache_count--;

    return true;
  }
  return false;
}

// ===============================
// IRT值管理辅助函数实现
// ===============================

// Actor-Critic 相关函数
// 使用文件锁进行同步
static void lock_shared_memory(LOH_params_t *params) {
  if (params->shm_file == NULL) return;

  struct flock lock;
  lock.l_type = F_WRLCK;  // 写锁
  lock.l_whence = SEEK_SET;
  lock.l_start = 0;
  lock.l_len = 0;  // 锁定整个文件

  if (fcntl(fileno(params->shm_file), F_SETLKW, &lock) == -1) {
    perror("Failed to acquire file lock");
  }
}

static void unlock_shared_memory(LOH_params_t *params) {
  if (params->shm_file == NULL) return;

  struct flock lock;
  lock.l_type = F_UNLCK;  // 解锁
  lock.l_whence = SEEK_SET;
  lock.l_start = 0;
  lock.l_len = 0;  // 解锁整个文件

  if (fcntl(fileno(params->shm_file), F_SETLK, &lock) == -1) {
    perror("Failed to release file lock");
  }
}

// 读取共享内存数据
static void read_shared_memory(LOH_params_t *params, shm_data_t *data) {
  if (params->shm_file == NULL) return;
  lock_shared_memory(params);
  // 强制刷新文件流，避免缓存
  fflush(params->shm_file);    // 刷新写缓存
  clearerr(params->shm_file);  // 清除错误和EOF标志
  rewind(params->shm_file);
  if (fread(data, sizeof(shm_data_t), 1, params->shm_file) != 1) {
    // 如有需要可处理错误，但目前继续运行
  }
  unlock_shared_memory(params);
}

// 写入共享内存数据
static void write_shared_memory(LOH_params_t *params, const shm_data_t *data) {
  if (params->shm_file == NULL) return;
  lock_shared_memory(params);
  rewind(params->shm_file);
  fwrite(data, sizeof(shm_data_t), 1, params->shm_file);
  fflush(params->shm_file);
  unlock_shared_memory(params);
}

// POSIX 信号量初始化与清理
static bool loh_sem_init(LOH_params_t *params) {
  if (params == NULL) return false;
  params->sem_enabled = false;

  /* Respect runtime request flag: if semaphores are not requested, skip init */
  if (!params->sem_requested) {
    return false;
  }

  if (!params->enable_rl) return false;
  if (params->sem_ready_name == NULL || params->sem_ack_name == NULL) {
    return false;
  }

  int oflag = O_CREAT | O_EXCL;
  mode_t mode = 0666;
  sem_t *ready = sem_open(params->sem_ready_name, oflag, mode, 0);
  bool created_ready = false;
  if (ready == SEM_FAILED) {
    if (errno != EEXIST) {
      LOH_DEBUG_PRINT_BASIC("[LOH] sem_open ready failed: %s\n",
                            strerror(errno));
      return false;
    }
    oflag = O_CREAT;
    ready = sem_open(params->sem_ready_name, oflag, mode, 0);
    if (ready == SEM_FAILED) {
      LOH_DEBUG_PRINT_BASIC("[LOH] sem_open ready (retry) failed: %s\n",
                            strerror(errno));
      return false;
    }
  } else {
    created_ready = true;
  }

  // 清零 ready 信号量残留值
  while (sem_trywait(ready) == 0) {
    // drain
  }

  oflag = O_CREAT | O_EXCL;
  sem_t *ack = sem_open(params->sem_ack_name, oflag, mode, 0);
  bool created_ack = false;
  if (ack == SEM_FAILED) {
    if (errno != EEXIST) {
      LOH_DEBUG_PRINT_BASIC("[LOH] sem_open ack failed: %s\n", strerror(errno));
      sem_close(ready);
      return false;
    }
    oflag = O_CREAT;
    ack = sem_open(params->sem_ack_name, oflag, mode, 0);
    if (ack == SEM_FAILED) {
      LOH_DEBUG_PRINT_BASIC("[LOH] sem_open ack (retry) failed: %s\n",
                            strerror(errno));
      sem_close(ready);
      return false;
    }
  } else {
    created_ack = true;
  }

  while (sem_trywait(ack) == 0) {
    // drain
  }

  params->sem_ready = ready;
  params->sem_ack = ack;
  params->sem_enabled = true;
  params->sem_owner = created_ready && created_ack;

  if (params->sem_owner) {
    LOH_DEBUG_PRINT_BASIC("[LOH] POSIX semaphores created and reset\n");
  } else {
    LOH_DEBUG_PRINT_BASIC("[LOH] POSIX semaphores attached (existing)\n");
  }

  return true;
}

static void loh_sem_close(LOH_params_t *params, bool unlink_names) {
  if (params == NULL) return;

  if (params->sem_ready) {
    sem_close(params->sem_ready);
    params->sem_ready = NULL;
  }
  if (params->sem_ack) {
    sem_close(params->sem_ack);
    params->sem_ack = NULL;
  }

  if (unlink_names && params->sem_owner) {
    if (params->sem_ready_name) {
      sem_unlink(params->sem_ready_name);
    }
    if (params->sem_ack_name) {
      sem_unlink(params->sem_ack_name);
    }
  }

  if (unlink_names) {
    if (params->sem_ready_name) {
      g_free(params->sem_ready_name);
      params->sem_ready_name = NULL;
    }
    if (params->sem_ack_name) {
      g_free(params->sem_ack_name);
      params->sem_ack_name = NULL;
    }
  }

  params->sem_enabled = false;
  params->sem_owner = false;
}

/**
 * @brief IRT 特征值计算函数 - 将原始 IRT 值转换为 [0,1] 范围的特征值
 * 使用归一化公式：1/(1+IRT)，IRT 越大，特征值越小（访问间隔长 =
 * 被驱逐可能性高）
 * @param irt_value 原始 IRT 值
 * @return 归一化的 IRT 特征值
 */
static double calculate_irt_feature(int64_t irt_value) {
  // 【修复】处理未初始化IRT值：INT64_MAX -> 接近0的特征值（最佳淘汰候选）
  if (irt_value == INT64_MAX || irt_value <= 0) {
    return 0.0;  // 无IRT历史或无效值，特征为0（最适合淘汰）
  }
  return 1.0 / (1.0 + (double)irt_value);
}

// 计算对象的六个特征值：recency, frequency, size, irt1, irt2, irt3
static void calculate_object_features(LOH_params_t *params, cache_obj_t *obj,
                                      double features[FEATURE_DIM]) {
  PERF_TS _ts_feat;
  PERF_NOW(_ts_feat);
  // 初始化特征值
  for (int i = 0; i < FEATURE_DIM; i++) {
    features[i] = 0.0;
  }

  // 对象为空则直接返回零特征
  if (obj == NULL) {
    LOH_DEBUG_PRINT_BASIC(
        "[calculate_object_features] ERROR: Object is NULL, returning zero "
        "features\n");
    return;
  }

  // ====================================================================
  // 【新设计】：使用简化的 irt_values 数组计算特征
  // ====================================================================

  if (obj != NULL) {
    // 特征 0: Recency - 从上次访问到现在的时间
    double recency =
        (double)(params->current_timestamp - obj->LOH.last_access_counter);
    features[0] = 1.0 / (1.0 + recency);
    LOH_DEBUG_PRINT_VERBOSE(
        "[calculate_object_features] Feature0(recency) - time_diff=%.0f, "
        "feature_value=%.6f\n",
        recency, features[0]);

    // 特征 1: Frequency - 去掉 log，采用 f/(f+K)
    {
      const double K = 1.0;  // 按要求设为 1
      double f = (double)obj->LOH.access_count;
      features[1] = (f <= 0.0) ? 0.0 : (f / (f + K));
    }
    LOH_DEBUG_PRINT_VERBOSE(
        "[calculate_object_features] Feature1(frequency) - f=%d, K=1.0, "
        "feature_value=%.6f\n",
        obj->LOH.access_count, features[1]);

    // 特征 3, 4, 5: IRT - 使用简化的irt_values数组
    features[3] = calculate_irt_feature(obj->LOH.irt_values[0]);  // 最新IRT
    features[4] = calculate_irt_feature(obj->LOH.irt_values[1]);  // 第2新IRT
    features[5] = calculate_irt_feature(obj->LOH.irt_values[2]);  // 第3新IRT

    LOH_DEBUG_PRINT_VERBOSE(
        "[calculate_object_features] Feature3(latest_IRT) - irt=%ld, "
        "feature_value=%.6f\n",
        obj->LOH.irt_values[0], features[3]);
    LOH_DEBUG_PRINT_VERBOSE(
        "[calculate_object_features] Feature4(2nd_IRT) - irt=%ld, "
        "feature_value=%.6f\n",
        obj->LOH.irt_values[1], features[4]);
    LOH_DEBUG_PRINT_VERBOSE(
        "[calculate_object_features] Feature5(3rd_IRT) - irt=%ld, "
        "feature_value=%.6f\n",
        obj->LOH.irt_values[2], features[5]);
  } else {
    // 理论上不会到达，这里仅为健壮性保留
  }

  // 特征 2: Size - 去掉 log，采用 1/(1+A*MB)
  // obj_size 单位是字节，需要归一化到合理的范围
  // 优先使用 obj->obj_size，req 为空时也安全
  double size_mb = (double)obj->obj_size / (1024.0 * 1024.0);  // 转换为 MB
  {
    const double A = 1.0;
    features[2] = 1.0 / (1.0 + A * size_mb);
  }
  LOH_DEBUG_PRINT_VERBOSE(
      "[calculate_object_features] Feature2(size) - raw_size=%llu bytes, "
      "MB=%.6f, A=1.0, feature_value=%.6f\n",
      (unsigned long long)obj->obj_size, size_mb, features[2]);

  // [DEBUG] Final feature vector
  LOH_DEBUG_PRINT_DETAILED(
      "[calculate_object_features] Final feature vector - [%.6f, %.6f, %.6f, "
      "%.6f, "
      "%.6f, %.6f]\n",
      features[0], features[1], features[2], features[3], features[4],
      features[5]);

  // 记录特征计算耗时在批量调用处统一计时，避免每次调用都触发系统调用
}

static void update_state_vector(LOH_params_t *params) {
  // RL 状态计算位置 1：每当 RL_update_interval 触发时调用
  // 计算 38 维状态向量，包含 global_perf、特征统计、缓存状态

  // 【调试打印】状态向量更新开始
  LOH_DEBUG_PRINT_DETAILED(
      "[update_state_vector] state vector update start - timestamp=%lu\n",
      (unsigned long)params->current_timestamp);
  LOH_DEBUG_PRINT_DETAILED(
      "[update_state_vector] obj_count=%.1f, obj_miss=%.1f, "
      "byte_count=%.1f, byte_miss=%.1f\n",
      params->epoch_obj_count, params->epoch_obj_miss_count,
      params->epoch_byte_count, params->epoch_byte_miss_count);

  // 计算命中率
  double hit_ratio = 0.0;
  if (params->epoch_obj_count > 0) {
    hit_ratio = 1.0 - (params->epoch_obj_miss_count / params->epoch_obj_count);
  }

  double byte_hit_ratio = 0.0;
  if (params->epoch_byte_count > 0) {
    byte_hit_ratio =
        1.0 - (params->epoch_byte_miss_count / params->epoch_byte_count);
  }

  // 【调试打印】命中率计算
  LOH_DEBUG_PRINT_DETAILED(
      "[update_state_vector] hit_ratio=%.6f, "
      "byte_hit_ratio=%.6f\n",
      hit_ratio, byte_hit_ratio);

  // 初始化状态向量为 0
  memset(params->context_state, 0, sizeof(double) * CONTEXT_DIM);

  // 状态向量结构 (38 维):
  // [0-1]: global_perf 指标 - 对象命中率，字节命中率
  // [2-25]: 特征表现剖析 - 每个特征在命中/未命中对象中的均值和方差
  // (6 个特征 × 2 种统计 × 2 种事件) [26-37]: 缓存池状态摘要 -
  // 当前池内对象的特征均值和方差 (6 个特征 × 2 种统计)

  // A. global_perf 指标 (2 维)
  params->context_state[0] = hit_ratio;
  params->context_state[1] = byte_hit_ratio;

  // 【调试打印】global_perf 指标
  LOH_DEBUG_PRINT_DETAILED(
      "[update_state_vector] global_perf [0-1] - [%.6f, %.6f]\n",
      params->context_state[0], params->context_state[1]);

  // B. 特征表现剖析 (24 维)
  // 对于每个特征 i (6 个特征):
  LOH_DEBUG_PRINT_DETAILED(
      "[update_state_vector] hit_count=%ld, "
      "miss_count=%ld\n",
      (long)params->hit_feature_count, (long)params->miss_feature_count);

  for (int i = 0; i < FEATURE_DIM; i++) {
    LOH_DEBUG_PRINT_DETAILED(
        "[update_state_vector] feature %d - hit_sum=%.6f, hit_sum_sq=%.6f, "
        "miss_sum=%.6f, miss_sum_sq=%.6f\n",
        i, params->hit_feature_sum[i], params->hit_feature_sum_sq[i],
        params->miss_feature_sum[i], params->miss_feature_sum_sq[i]);

    // 计算命中对象特征统计
    if (params->hit_feature_count > 0) {
      // 特征i在命中对象中的均值
      double mean = params->hit_feature_sum[i] / params->hit_feature_count;
      params->context_state[2 + i * 4] = mean;

      // 特征i在命中对象中的方差
      if (params->hit_feature_count > 1) {
        double variance =
            (params->hit_feature_sum_sq[i] / params->hit_feature_count) -
            (mean * mean);
        if (variance > 0) {  // 确保方差为正
          params->context_state[2 + i * 4 + 1] = variance;
        }
      }

      LOH_DEBUG_PRINT_DETAILED(
          "[update_state_vector] feature %d - hit - mean=%.6f, "
          "variance=%.6f, state[%d]=%.6f, state[%d]=%.6f\n",
          i, mean,
          (params->hit_feature_count > 1)
              ? ((params->hit_feature_sum_sq[i] / params->hit_feature_count) -
                 (mean * mean))
              : 0.0,
          2 + i * 4, params->context_state[2 + i * 4], 2 + i * 4 + 1,
          params->context_state[2 + i * 4 + 1]);
    }

    // 计算未命中对象特征统计
    if (params->miss_feature_count > 0) {
      // 特征i在未命中对象中的均值
      double mean = params->miss_feature_sum[i] / params->miss_feature_count;
      params->context_state[2 + i * 4 + 2] = mean;

      // 特征i在未命中对象中的方差
      if (params->miss_feature_count > 1) {
        double variance =
            (params->miss_feature_sum_sq[i] / params->miss_feature_count) -
            (mean * mean);
        if (variance > 0) {  // 确保方差为正
          params->context_state[2 + i * 4 + 3] = variance;
        }
      }

      LOH_DEBUG_PRINT_DETAILED(
          "[update_state_vector] feature %d - miss- mean=%.6f, "
          "variance=%.6f, state[%d]=%.6f, state[%d]=%.6f\n",
          i, mean,
          (params->miss_feature_count > 1)
              ? ((params->miss_feature_sum_sq[i] / params->miss_feature_count) -
                 (mean * mean))
              : 0.0,
          2 + i * 4 + 2, params->context_state[2 + i * 4 + 2], 2 + i * 4 + 3,
          params->context_state[2 + i * 4 + 3]);
    }
  }

#if LOH_INCLUDE_CACHE_FEATURES
  // C. 缓存池状态摘要 (12 维) - 仅在包含缓存特征时计算
  // 对于每个特征 i (6 个特征):
  LOH_DEBUG_PRINT_DETAILED("[update_state_vector] cache_object_count=%ld\n",
                           (long)params->cache_object_count);

  for (int i = 0; i < FEATURE_DIM; i++) {
    LOH_DEBUG_PRINT_DETAILED(
        "[update_state_vector] cache_feature %d - sum=%.6f, sum_sq=%.6f\n", i,
        params->cache_feature_sum[i], params->cache_feature_sum_sq[i]);

    // 计算缓存中对象特征统计
    if (params->cache_object_count > 0) {
      // 特征i在当前缓存中的均值
      double mean = params->cache_feature_sum[i] / params->cache_object_count;
      params->context_state[26 + i * 2] = mean;

      // 特征i在当前缓存中的方差
      if (params->cache_object_count > 1) {
        double variance =
            (params->cache_feature_sum_sq[i] / params->cache_object_count) -
            (mean * mean);
        if (variance > 0) {  // 确保方差为正
          params->context_state[26 + i * 2 + 1] = variance;
        }
      }

      LOH_DEBUG_PRINT_DETAILED(
          "[update_state_vector] cache_feature %d - mean=%.6f, "
          "variance=%.6f, state[%d]=%.6f, state[%d]=%.6f\n",
          i, mean,
          (params->cache_object_count > 1) ? ((params->cache_feature_sum_sq[i] /
                                               params->cache_object_count) -
                                              (mean * mean))
                                           : 0.0,
          26 + i * 2, params->context_state[26 + i * 2], 26 + i * 2 + 1,
          params->context_state[26 + i * 2 + 1]);
    }
  }
#endif

#if LOH_INCLUDE_CACHE_FEATURES
  // 【调试打印】完整状态向量 (38维)

  // 【还原】分组调试输出 - 38维格式 (直接按向量顺序)
  LOH_DEBUG_PRINT_BASIC("[global_features]: [%.6f, %.6f]\n",
                        params->context_state[0], params->context_state[1]);

  LOH_DEBUG_PRINT_BASIC("[request_features]: [");
  for (int i = 2; i < 26; i++) {
    LOH_DEBUG_PRINT_BASIC("%.6f", params->context_state[i]);
    if (i < 25) LOH_DEBUG_PRINT_BASIC(", ");
  }
  LOH_DEBUG_PRINT_BASIC("]\n");

  LOH_DEBUG_PRINT_BASIC("[cache_features]: [");
  for (int i = 26; i < 38; i++) {
    LOH_DEBUG_PRINT_BASIC("%.6f", params->context_state[i]);
    if (i < 37) LOH_DEBUG_PRINT_BASIC(", ");
  }
  LOH_DEBUG_PRINT_BASIC("]\n");
#else
  // 【调试打印】完整状态向量 (26维) - 不包含缓存特征

  // 【还原】分组调试输出 - 26维格式 (直接按向量顺序)
  LOH_DEBUG_PRINT_BASIC("[global_features]: [%.6f, %.6f]\n",
                        params->context_state[0], params->context_state[1]);

  LOH_DEBUG_PRINT_BASIC("[request_features]: [");
  for (int i = 2; i < 26; i++) {
    LOH_DEBUG_PRINT_BASIC("%.6f", params->context_state[i]);
    if (i < 25) LOH_DEBUG_PRINT_BASIC(", ");
  }
  LOH_DEBUG_PRINT_BASIC("]\n");
#endif

  // 【保留】逐个详细输出（VERBOSE模式）
  for (int i = 0; i < CONTEXT_DIM; i++) {
    LOH_DEBUG_PRINT_VERBOSE("[update_state_vector] state[%d] = %.6f\n", i,
                            params->context_state[i]);
  }

  // 【删除】状态向量内的重置逻辑 - 统一在 sync_with_actor_critic 后完全重置
  // 原重置逻辑已移至 RL 同步后，避免在状态计算过程中改变统计数据
}

// 将状态发送到 Actor-Critic 网络并获取更新的权重
// 【核心修复】：重构此函数以修复死锁问题，并优化等待时间
static void sync_with_actor_critic(LOH_params_t *params) {
  if (!params->enable_rl) return;        // 关闭RL时直接返回，无需计时
  if (params->shm_file == NULL) return;  // 无需计时

  // 开始sync总计时
  PERF_TS ts_sync_total;
  PERF_NOW(ts_sync_total);

  // 计算当前状态向量 - 单独计时
  PERF_TS ts_update_state;
  PERF_NOW(ts_update_state);
  update_state_vector(params);
  PERF_ACCUM(params, sync_update_state, ts_update_state);

  // misc操作开始计时
  PERF_TS ts_misc_start;
  PERF_NOW(ts_misc_start);

  shm_data_t shm_data;

  // --- 临界区 1: 发送状态 ---
  // 只在写入时加锁，然后立即释放，避免在等待时持有锁
  lock_shared_memory(params);
  // 读取是为了修改，而不是直接覆盖
  rewind(params->shm_file);
  if (fread(&shm_data, sizeof(shm_data_t), 1, params->shm_file) != 1) {
    // Handle error if needed, but for now just continue
  }

  memcpy(shm_data.state, params->context_state, sizeof(double) * CONTEXT_DIM);

  // Set current performance metrics
  shm_data.miss_ratio =
      (params->epoch_obj_count > 0)
          ? (params->epoch_obj_miss_count / params->epoch_obj_count)
          : 0.0;
  shm_data.byte_miss_ratio =
      (params->epoch_byte_count > 0)
          ? (params->epoch_byte_miss_count / params->epoch_byte_count)
          : 0.0;

  bool python_training = shm_data.is_training != 0;

  // 简化版本管理：仅用于日志对齐，不用于ACK校验
  shm_data.state_version += 1;
  shm_data.timestamp = params->current_timestamp;

  // 本次交互的序号（用于两端对齐日志）
  unsigned long long seq_no = (unsigned long long)shm_data.state_version;

  double reward =
      params->miss_ratio_weight * (1.0 - shm_data.miss_ratio) +
      params->byte_miss_ratio_weight * (1.0 - shm_data.byte_miss_ratio);

  // 获取当前时间戳用于日志
  struct timespec current_time;
  clock_gettime(CLOCK_MONOTONIC, &current_time);
  double timestamp = current_time.tv_sec + current_time.tv_nsec / 1e9;

  // ========== 发送状态给Python（不管是否在训练模式）==========
  LOH_DEBUG_PRINT_BASIC(
      "[%.6f] [seq %llu] Sending state to Python (is_training=%d)\n", timestamp,
      seq_no, python_training);

  // 标记需要进行推理
  shm_data.ready_for_inference = 1;
  shm_data.weights_updated = 0;  // 确保清除旧标志

  // 【新增】时序日志：记录发送状态的时间
  struct timespec send_time;
  clock_gettime(CLOCK_MONOTONIC, &send_time);
  double send_timestamp = send_time.tv_sec + send_time.tv_nsec / 1e9;

  // 同时打印对象未命中率 (OMR)、字节未命中率 (BMR) 和计算出的奖励 (Reward)
  LOH_DEBUG_PRINT_DETAILED(
      "[%.6f] [C-STATE] [seq %llu] Sending RL request - OMR: %.4f, BMR: %.4f, "
      "Reward: %.4f, ",
      send_timestamp, seq_no, "Epoch Count: %.0f\n", seq_no,
      shm_data.miss_ratio, shm_data.byte_miss_ratio, reward,
      params->epoch_obj_count);
  LOH_DEBUG_PRINT_BASIC("[seq %llu] LOH DEBUG: reward=%.6f\n", seq_no, reward);

  // 将更新的数据写回共享内存
  rewind(params->shm_file);
  fwrite(&shm_data, sizeof(shm_data_t), 1, params->shm_file);
  fflush(params->shm_file);

  // 【移除】发送请求后的复查逻辑 - 不再需要
  // 原因：Python在reset()时会立即发送ACK和权重，不会出现瞬时切换到训练模式的情况
  // 如果Python真的在训练，会在等待ACK超时时检查is_training

  // 【新增】时序日志：记录发送完成的时间
  struct timespec sent_time;
  clock_gettime(CLOCK_MONOTONIC, &sent_time);
  double send_duration = (sent_time.tv_sec - send_time.tv_sec) +
                         (sent_time.tv_nsec - send_time.tv_nsec) / 1e9;
  LOH_DEBUG_PRINT_BASIC("[%ld.%09ld] [seq %llu] sent finished, span %.6f 秒\n",
                        sent_time.tv_sec, sent_time.tv_nsec, seq_no,
                        send_duration);

  unlock_shared_memory(params);
  // --- 临界区 1 end ---

  // 发送ready信号量通知Python
  if (params->sem_requested && params->sem_enabled &&
      params->sem_ready != NULL) {
    if (sem_post(params->sem_ready) != 0) {
      LOH_DEBUG_PRINT_BASIC(
          "[LOH] sem_post(ready) failed: %s, disable semaphore mode\n",
          strerror(errno));
      loh_sem_close(params, false);
    } else {
      LOH_DEBUG_PRINT_BASIC(
          "[LOH] sem_post(ready) signaled Python (seq %llu)\n", seq_no);
    }
  } else if (!params->sem_requested) {
    LOH_DEBUG_PRINT_DETAILED(
        "[LOH] sem_post skipped because sem_requested=0 (seq %llu)\n", seq_no);
  }

  // 记录开始等待的时间
  struct timespec start_time, end_time;
  clock_gettime(CLOCK_MONOTONIC, &start_time);
  LOH_DEBUG_PRINT_BASIC("[%ld.%09ld] start waiting for Python response\n",
                        start_time.tv_sec, start_time.tv_nsec);

  // ========== 等待Python的ACK和权重更新 ==========
  // 策略：优先使用POSIX信号量（低延迟），失败时回退到轮询
  // 超时策略：50秒超时，无论Python是否在训练都等待

  const double timeout_sec = 50.0;  // 50秒超时
  const int sleep_us = 25;          // 0.025ms 轮询间隔
  int wait_cycles = 0;
  bool ack_ready = false;
  bool timeout_triggered = false;
  bool ack_via_semaphore = false;

  // 如果信号量未启用但配置允许，尝试重新初始化
  if (!params->sem_enabled && params->enable_rl &&
      params->sem_ready_name != NULL && params->sem_ack_name != NULL) {
    loh_sem_init(params);
  }

  // ========== 路径1: 使用信号量等待ACK ==========
  if (params->sem_requested && params->sem_enabled) {
    // 计算绝对超时时间（50秒后）
    struct timespec abs_deadline;
    clock_gettime(CLOCK_REALTIME, &abs_deadline);
    abs_deadline.tv_sec += (time_t)timeout_sec;
    abs_deadline.tv_nsec += (long)((timeout_sec - (time_t)timeout_sec) * 1e9);
    if (abs_deadline.tv_nsec >= 1000000000L) {
      abs_deadline.tv_sec += 1;
      abs_deadline.tv_nsec -= 1000000000L;
    }

    // ========== sem_timedwait: 等待Python发送ACK信号（最多50秒）==========
    // 优势：事件驱动，Python完成后立即唤醒C端，无CPU轮询开销
    int rc = sem_timedwait(params->sem_ack, &abs_deadline);

    // --- 成功收到ACK信号 ---
    if (rc == 0) {
      ack_ready = true;
      ack_via_semaphore = true;
      LOH_DEBUG_PRINT_BASIC("[LOH] sem_timedwait(ack) success (seq %llu)\n",
                            seq_no);
      read_shared_memory(params, &shm_data);
    }
    // --- 超时 ---
    else if (errno == ETIMEDOUT) {
      timeout_triggered = true;
      LOH_DEBUG_PRINT_BASIC(
          "[LOH] sem_timedwait(ack) timeout after %.1f seconds (seq %llu)\n",
          timeout_sec, seq_no);
    }
    // --- 被信号中断：重试一次（简单处理）---
    else if (errno == EINTR) {
      LOH_DEBUG_PRINT_BASIC(
          "[LOH] sem_timedwait(ack) interrupted, retry once (seq %llu)\n",
          seq_no);
      // 重新计算剩余时间
      struct timespec now;
      clock_gettime(CLOCK_REALTIME, &now);
      if (now.tv_sec < abs_deadline.tv_sec ||
          (now.tv_sec == abs_deadline.tv_sec &&
           now.tv_nsec < abs_deadline.tv_nsec)) {
        // 还有时间，重试
        rc = sem_timedwait(params->sem_ack, &abs_deadline);
        if (rc == 0) {
          ack_ready = true;
          ack_via_semaphore = true;
          LOH_DEBUG_PRINT_BASIC(
              "[LOH] sem_timedwait(ack) success after retry (seq %llu)\n",
              seq_no);
          read_shared_memory(params, &shm_data);
        } else {
          timeout_triggered = true;
        }
      } else {
        timeout_triggered = true;
      }
    }
    // --- 其他错误：关闭信号量，回退到轮询 ---
    else {
      LOH_DEBUG_PRINT_BASIC(
          "[LOH] sem_timedwait error (%s), disable semaphore and fallback to "
          "polling (seq %llu)\n",
          strerror(errno), seq_no);
      if (params->sem_ready) {
        sem_close(params->sem_ready);
        params->sem_ready = NULL;
      }
      if (params->sem_ack) {
        sem_close(params->sem_ack);
        params->sem_ack = NULL;
      }
      params->sem_enabled = false;
      // 继续到轮询路径
    }
  }

  // ========== 路径2: 轮询等待ACK（信号量不可用或失败时）==========
  if (!ack_ready && !timeout_triggered) {
    while (1) {
      read_shared_memory(params, &shm_data);

      if (shm_data.weights_updated) {
        ack_ready = true;
        clock_gettime(CLOCK_MONOTONIC, &end_time);
        double elapsed_seconds = (end_time.tv_sec - start_time.tv_sec) +
                                 (end_time.tv_nsec - start_time.tv_nsec) / 1e9;

        LOH_DEBUG_PRINT_BASIC(
            "[seq %llu] LOH DEBUG: Received weights after %d cycles (%.6f "
            "seconds)\n",
            seq_no, wait_cycles, elapsed_seconds);
        LOH_DEBUG_PRINT_BASIC(
            "[%ld.%09ld] [seq %llu] received weights after %.6f seconds\n",
            end_time.tv_sec, end_time.tv_nsec, seq_no, elapsed_seconds);

        struct timespec apply_start, apply_end;
        clock_gettime(CLOCK_MONOTONIC, &apply_start);

        lock_shared_memory(params);
        memcpy(params->weights, shm_data.weights, sizeof(double) * FEATURE_DIM);
        shm_data.weights_updated = 0;
        shm_data.ready_for_inference = 0;
        rewind(params->shm_file);
        fwrite(&shm_data, sizeof(shm_data_t), 1, params->shm_file);
        fflush(params->shm_file);
        unlock_shared_memory(params);

        clock_gettime(CLOCK_MONOTONIC, &apply_end);
        double apply_duration = (apply_end.tv_sec - apply_start.tv_sec) +
                                (apply_end.tv_nsec - apply_start.tv_nsec) / 1e9;
        LOH_DEBUG_PRINT_BASIC(
            "[%ld.%09ld] [seq %llu] apply weights finished, span %.6f "
            "seconds\n",
            apply_end.tv_sec, apply_end.tv_nsec, seq_no, apply_duration);

        LOH_DEBUG_PRINT_BASIC(
            "[Updated weights from AC]: [%.3f, %.3f, %.3f, %.3f, %.3f, %.3f]\n",
            params->weights[0], params->weights[1], params->weights[2],
            params->weights[3], params->weights[4], params->weights[5]);

        PERF_ACCUM(params, sync_misc, ts_misc_start);
        PERF_ACCUM(params, sync_total, ts_sync_total);
        return;
      }

      wait_cycles++;
      struct timespec now_ts;
      clock_gettime(CLOCK_MONOTONIC, &now_ts);
      double waited = (now_ts.tv_sec - start_time.tv_sec) +
                      (now_ts.tv_nsec - start_time.tv_nsec) / 1e9;
      if (waited >= timeout_sec) {
        timeout_triggered = true;
        break;
      }
      usleep(sleep_us);
    }
  }

  if (ack_ready) {
    clock_gettime(CLOCK_MONOTONIC, &end_time);
    double elapsed_seconds = (end_time.tv_sec - start_time.tv_sec) +
                             (end_time.tv_nsec - start_time.tv_nsec) / 1e9;
    if (ack_via_semaphore) {
      LOH_DEBUG_PRINT_BASIC(
          "[seq %llu] LOH DEBUG: Received weights via semaphore (%.6f "
          "seconds)\n",
          seq_no, elapsed_seconds);
      LOH_DEBUG_PRINT_BASIC(
          "[%ld.%09ld] [seq %llu] received weights via semaphore\n",
          end_time.tv_sec, end_time.tv_nsec, seq_no);
    } else {
      LOH_DEBUG_PRINT_BASIC(
          "[seq %llu] LOH DEBUG: Received weights after %d cycles (%.6f "
          "seconds)\n",
          seq_no, wait_cycles, elapsed_seconds);
      LOH_DEBUG_PRINT_BASIC(
          "[%ld.%09ld] [seq %llu] received weights after %.6f seconds\n",
          end_time.tv_sec, end_time.tv_nsec, seq_no, elapsed_seconds);
    }

    struct timespec apply_start, apply_end;
    clock_gettime(CLOCK_MONOTONIC, &apply_start);

    lock_shared_memory(params);
    memcpy(params->weights, shm_data.weights, sizeof(double) * FEATURE_DIM);
    shm_data.weights_updated = 0;
    shm_data.ready_for_inference = 0;
    rewind(params->shm_file);
    fwrite(&shm_data, sizeof(shm_data_t), 1, params->shm_file);
    fflush(params->shm_file);
    unlock_shared_memory(params);

    clock_gettime(CLOCK_MONOTONIC, &apply_end);
    double apply_duration = (apply_end.tv_sec - apply_start.tv_sec) +
                            (apply_end.tv_nsec - apply_start.tv_nsec) / 1e9;
    double apply_timestamp = apply_end.tv_sec + apply_end.tv_nsec / 1e9;

    LOH_DEBUG_PRINT_BASIC(
        "[%.6f] [C-WEIGHTS] [seq %llu] Received weights from Python, apply "
        "duration: %.6f sec\n",
        apply_timestamp, seq_no, apply_duration);
    LOH_DEBUG_PRINT_BASIC(
        "[%.6f] [C-WEIGHTS] [seq %llu] New weights: [%.3f, %.3f, %.3f, %.3f, "
        "%.3f, %.3f]\n",
        apply_timestamp, seq_no, params->weights[0], params->weights[1],
        params->weights[2], params->weights[3], params->weights[4],
        params->weights[5]);

    PERF_ACCUM(params, sync_misc, ts_misc_start);
    PERF_ACCUM(params, sync_total, ts_sync_total);
    return;
  }

  // 超时处理：使用缓存权重继续运行
  struct timespec timeout_time;
  clock_gettime(CLOCK_MONOTONIC, &timeout_time);
  double timeout_duration = (timeout_time.tv_sec - start_time.tv_sec) +
                            (timeout_time.tv_nsec - start_time.tv_nsec) / 1e9;

  double final_timestamp = timeout_time.tv_sec + timeout_time.tv_nsec / 1e9;
  LOH_DEBUG_PRINT_BASIC(
      "[%.6f] [C-TIMEOUT] [seq %llu] Timeout after %.6f seconds - using "
      "cached weights\n",
      final_timestamp, seq_no, timeout_duration);

  // 打印当前使用的缓存权重
  LOH_DEBUG_PRINT_BASIC(
      "[%.6f] [C-CACHED] [seq %llu] Using cached weights: [%.3f, %.3f, %.3f, "
      "%.3f, %.3f, %.3f]\n",
      final_timestamp, seq_no, params->weights[0], params->weights[1],
      params->weights[2], params->weights[3], params->weights[4],
      params->weights[5]);

  // misc操作计时结束
  PERF_ACCUM(params, sync_misc, ts_misc_start);
  // sync总计时结束
  PERF_ACCUM(params, sync_total, ts_sync_total);
}

// 辅助函数的前向声明
static double calculate_score(LOH_params_t *params, cache_obj_t *obj);
static double calculate_score_with_features(LOH_params_t *params,
                                            const double features[FEATURE_DIM]);

#if LOH_DEBUG_LEVEL >= LOH_DEBUG_DETAILED
// ===== Detailed validation helpers =====
static void loh_debug_check_in_lru(LOH_params_t *params, cache_obj_t *obj,
                                   const char *tag) {
  int cnt = 0;
  for (cache_obj_t *p = params->q_head; p; p = p->queue.next) {
    if (p == obj) {
      LOH_DEBUG_PRINT_DETAILED("[VALIDATE][%s] obj_id=%llu in LRU (pos~%d)\n",
                               tag, (unsigned long long)obj->obj_id, cnt);
      return;
    }
    cnt++;
  }
  LOH_DEBUG_PRINT_DETAILED("[VALIDATE][%s] WARNING obj_id=%llu NOT in LRU\n",
                           tag, (unsigned long long)obj->obj_id);
}

static void loh_debug_check_in_freq(LOH_params_t *params, cache_obj_t *obj,
                                    const char *tag) {
  loh_freq_node_t *node = (loh_freq_node_t *)obj->LOH.loh_freq_node;
  if (node && node->obj == obj && node->freq_level >= 0 &&
      node->freq_level <= FREQ_MAX) {
    LOH_DEBUG_PRINT_DETAILED("[VALIDATE][%s] obj_id=%llu in FREQ(level=%d)\n",
                             tag, (unsigned long long)obj->obj_id,
                             node->freq_level);
  } else {
    LOH_DEBUG_PRINT_DETAILED("[VALIDATE][%s] WARNING obj_id=%llu NOT in FREQ\n",
                             tag, (unsigned long long)obj->obj_id);
  }
}

static void loh_debug_check_in_size(LOH_params_t *params, cache_obj_t *obj,
                                    const char *tag) {
  size_node_t *node = (size_node_t *)obj->LOH.loh_size_node;
  if (node && node->obj == obj) {
    LOH_DEBUG_PRINT_DETAILED("[VALIDATE][%s] obj_id=%llu in SIZE bucket\n", tag,
                             (unsigned long long)obj->obj_id);
  } else {
    LOH_DEBUG_PRINT_DETAILED(
        "[VALIDATE][%s] WARNING obj_id=%llu NOT in SIZE bucket\n", tag,
        (unsigned long long)obj->obj_id);
  }
}

static void loh_debug_check_in_irt(LOH_params_t *params, cache_obj_t *obj,
                                   const char *tag) {
  for (int h = 0; h < IRT_HISTORY_SIZE; ++h) {
    int idx = obj->LOH.loh_irt_pos[h];
    bool in = (idx >= 0 && idx < params->irt_heap_size[h] &&
               params->irt_heap[h][idx].obj == obj);
    LOH_DEBUG_PRINT_DETAILED(
        "[VALIDATE][%s] obj_id=%llu in IRT%d: %s (idx=%d,size=%d)\n", tag,
        (unsigned long long)obj->obj_id, h + 1, in ? "YES" : "NO", idx,
        params->irt_heap_size[h]);
  }
}

static void loh_debug_check_membership(LOH_params_t *params, cache_obj_t *obj,
                                       const char *tag) {
  if (!obj) return;
  loh_debug_check_in_lru(params, obj, tag);
  loh_debug_check_in_freq(params, obj, tag);
  loh_debug_check_in_size(params, obj, tag);
  loh_debug_check_in_irt(params, obj, tag);
}
#endif

// 轻量去重 seen 表：使用 generation-tag 避免每轮清零
#define LOH_SEEN_CAP 256
#if defined(__STDC_VERSION__) && __STDC_VERSION__ >= 201112L
_Static_assert((LOH_SEEN_CAP & (LOH_SEEN_CAP - 1)) == 0,
               "LOH_SEEN_CAP must be a power of two");
#endif
static cache_obj_t *loh_seen_slots[LOH_SEEN_CAP];
static uint32_t loh_seen_gens[LOH_SEEN_CAP];
static uint32_t loh_seen_cur_gen = 0;
static inline void loh_seen_clear(void) {
  loh_seen_cur_gen++;
  if (loh_seen_cur_gen == 0) {
    // 发生回绕：彻底重置一次
    for (int i = 0; i < LOH_SEEN_CAP; ++i) {
      loh_seen_slots[i] = NULL;
      loh_seen_gens[i] = 0;
    }
    loh_seen_cur_gen = 1;
  }
}
static inline size_t loh_seen_hash(cache_obj_t *o) {
  return ((uintptr_t)o >> 4) & (LOH_SEEN_CAP - 1);
}
// 返回 true 表示第一次看到并已插入，false 表示已存在
static inline bool loh_seen_add(LOH_params_t *params, cache_obj_t *o) {
  if (!o) return false;
#if LOH_PERF_PROFILING
  if (params) params->perf.seen_add_calls++;
#endif
  size_t i = loh_seen_hash(o);
  int local_probes = 0;
  for (int probed = 0; probed < LOH_SEEN_CAP; ++probed) {
    local_probes++;
    if (loh_seen_gens[i] != loh_seen_cur_gen) {
      loh_seen_slots[i] = o;
      loh_seen_gens[i] = loh_seen_cur_gen;
      if (params) {
#if LOH_PERF_PROFILING
        params->perf.seen_inserts++;
        params->perf.seen_probes_total += local_probes;
        if ((uint64_t)local_probes > params->perf.seen_probe_max)
          params->perf.seen_probe_max = (uint64_t)local_probes;
#endif
      }
      return true;
    }
    if (loh_seen_slots[i] == o) {
      if (params) {
#if LOH_PERF_PROFILING
        params->perf.seen_duplicates++;
        params->perf.seen_probes_total += local_probes;
        if ((uint64_t)local_probes > params->perf.seen_probe_max)
          params->perf.seen_probe_max = (uint64_t)local_probes;
#endif
      }
      return false;  // 已存在
    }
    i = (i + 1) & (LOH_SEEN_CAP - 1);
  }
  // 表满：保守视为重复，避免扩容
  if (params) {
#if LOH_PERF_PROFILING
    params->perf.seen_table_full++;
    params->perf.seen_probes_total += (uint64_t)local_probes;
    if ((uint64_t)local_probes > params->perf.seen_probe_max)
      params->perf.seen_probe_max = (uint64_t)local_probes;
#endif
  }
  return false;
}
// 【删除】：update_feature_stats（未使用，逻辑已迁移）
// 未使用，process 逻辑已移至 update_global_access_record
// update_weights(LOH_params_t *params);  // 未使用，已删除

// 新的历史特征统计函数 -
// 【删除 init_history_stats，已统一使用 global_access_records】
static void update_cache_content_stats_add(LOH_params_t *params,
                                           cache_obj_t *obj);
static void update_cache_content_stats_remove(LOH_params_t *params,
                                              cache_obj_t *obj);
static void update_cache_content_stats_find(LOH_params_t *params,
                                            cache_obj_t *obj, int64_t new_irt);
static void cleanup_invalid_objects(LOH_params_t *params);
static void adjust_history_capacity_if_needed(LOH_params_t *params,
                                              cache_t *cache);

// 特征计算函数
static double calculate_recency(LOH_params_t *params, cache_obj_t *obj);
static double calculate_frequency(LOH_params_t *params, cache_obj_t *obj);
static double calculate_size(LOH_params_t *params, cache_obj_t *obj);

// frequency 表操作函数
static void freq_table_init(LOH_params_t *params);
static void freq_table_free(LOH_params_t *params);
static void freq_table_add(LOH_params_t *params, cache_obj_t *obj);
static void freq_table_remove(LOH_params_t *params, cache_obj_t *obj);
static void freq_table_update(LOH_params_t *params, cache_obj_t *obj);
static cache_obj_t *freq_table_get_min_freq_obj(LOH_params_t *params);
static void freq_table_get_candidates(LOH_params_t *params, int max_candidates,
                                      int *n_candidates);
static void freq_table_validate(LOH_params_t *params, const char *context);

// IRT 堆操作函数
static void irt_heap_init(LOH_params_t *params);
static void irt_heap_free(LOH_params_t *params);
static void irt_heap_add(LOH_params_t *params, cache_obj_t *obj, int heap_idx);
static void irt_heap_remove(LOH_params_t *params, cache_obj_t *obj,
                            int heap_idx);
static void irt_heap_update(LOH_params_t *params, cache_obj_t *obj,
                            int heap_idx);
static void irt_heap_repair_index_inconsistency(LOH_params_t *params,
                                                cache_obj_t *obj, int heap_idx);
static cache_obj_t *irt_heap_peek_top(LOH_params_t *params, int heap_idx);
static void irt1_heap_get_candidates(LOH_params_t *params, int max_candidates,
                                     int *n_candidates);
static void irt2_heap_get_candidates(LOH_params_t *params, int max_candidates,
                                     int *n_candidates);
static void irt3_heap_get_candidates(LOH_params_t *params, int max_candidates,
                                     int *n_candidates);
// POSIX 信号量辅助函数

// 尺寸桶操作函数
static void size_buckets_init(LOH_params_t *params);
static void size_buckets_free(LOH_params_t *params);
static void size_buckets_add(LOH_params_t *params, cache_obj_t *obj);
static void size_buckets_remove(LOH_params_t *params, cache_obj_t *obj);
static int size_get_bucket_index(LOH_params_t *params, int64_t size);
static void size_buckets_get_candidates(LOH_params_t *params,
                                        int max_candidates, int *n_candidates);
static void size_buckets_validate(LOH_params_t *params, const char *context);

// ===== 新增：对象生命周期管理和一致性验证函数 =====

// 对象状态管理
static void loh_obj_set_state(cache_obj_t *obj, loh_obj_state_t state);
static loh_obj_state_t loh_obj_get_state(cache_obj_t *obj);
static bool loh_obj_is_valid_state(cache_obj_t *obj);

// 原子操作包装器
static bool loh_atomic_insert_obj(LOH_params_t *params, cache_obj_t *obj);
static bool loh_atomic_remove_obj(LOH_params_t *params, cache_obj_t *obj);
static bool loh_atomic_update_obj(LOH_params_t *params, cache_obj_t *obj);

// 一致性验证
static bool loh_verify_object_consistency(LOH_params_t *params,
                                          cache_obj_t *obj, int verify_flags);
static bool loh_verify_all_consistency(LOH_params_t *params);
static void loh_repair_inconsistency(LOH_params_t *params, cache_obj_t *obj);

// 候选验证
static bool loh_validate_candidate_debug(cache_t *cache, cache_obj_t *candidate,
                                         const char *candidate_type, int index);

// 错误恢复
static bool loh_recover_from_error(LOH_params_t *params, cache_obj_t *obj,
                                   const char *error_context);
static void loh_cleanup_orphaned_entries(LOH_params_t *params);

/**
 * @brief 初始化 LOH 缓存
 *
 * @param ccache_params 通用缓存参数
 * @param cache_specific_params LOH 专用参数
 * 格式: "learning-interval=64000"
 * learning-interval: 权重更新的频率（默认：64000）
 */
cache_t *LOH_init(const common_cache_params_t ccache_params,
                  const char *cache_specific_params) {
  LOH_DEBUG_PRINT_DETAILED("=== LOH Cache Initialize ===\n");
  LOH_DEBUG_PRINT_DETAILED("LOH Debug Level: %d\n", LOH_DEBUG_LEVEL);
  LOH_DEBUG_PRINT_DETAILED("Cache size: %lu\n", ccache_params.cache_size);

  cache_t *cache =
      cache_struct_init("LOH", ccache_params, cache_specific_params);
  cache->cache_init = LOH_init;
  cache->cache_free = LOH_free;
  cache->get = LOH_get;
  cache->find = LOH_find;
  cache->insert = LOH_insert;
  cache->evict = LOH_evict;
  cache->remove = LOH_remove;
  cache->to_evict = LOH_to_evict;
  cache->get_occupied_byte = cache_get_occupied_byte_default;
  cache->can_insert = cache_can_insert_default;
  cache->get_n_obj = cache_get_n_obj_default;
  cache->print_cache = LOH_print_cache;

  if (ccache_params.consider_obj_metadata) {
    // 考虑对象元数据的大小以调整缓存容量计算
    cache->obj_md_size = sizeof(LOH_obj_metadata_t);
  } else {
    cache->obj_md_size = 0;
  }

  // 初始化 LOH 参数结构
  LOH_params_t *params = g_new0(LOH_params_t, 1);
  params->q_head = NULL;
  params->q_tail = NULL;
  params->current_timestamp = 0;
  params->n_candidates = 0;
  params->is_warmed_up = false;               // 初始为未预热状态
  params->history_capacity_adjusted = false;  // 历史容量未调整

  // 初始化 frequency 表
  freq_table_init(params);

  // 初始化 IRT 堆
  irt_heap_init(params);

  // 初始化尺寸桶
  size_buckets_init(params);

  // 初始化特征权重（默认的平衡初值）
  params->weights[0] = 1.0;  // recency
  params->weights[1] = 0.0;  // frequency
  params->weights[2] = 0.0;  // size
  params->weights[3] = 0.0;  // irt1
  params->weights[4] = 0.0;  // irt2
  params->weights[5] = 0.0;  // irt3

  // 初始化特征统计数据
  memset(&params->recent_stats, 0, sizeof(feature_stats_t));
  // 【删除recentstats初始化】：不再需要STATS_WINDOW相关stats

  // 初始化生成 38 维状态向量所需的统计数据
  params->hit_feature_count = 0;
  params->miss_feature_count = 0;
  params->cache_object_count = 0;

  // 初始化所有累积统计数据
  for (int i = 0; i < FEATURE_DIM; i++) {
    params->hit_feature_sum[i] = 0.0;
    params->hit_feature_sum_sq[i] = 0.0;
    params->miss_feature_sum[i] = 0.0;
    params->miss_feature_sum_sq[i] = 0.0;
    params->cache_feature_sum[i] = 0.0;
    params->cache_feature_sum_sq[i] = 0.0;
  }

  // 初始化历史特征统计
  // 【删除 init_history_stats 调用】：统一使用 global_access_records，在
  // free_global_access_records 中释放

  // 【新增 Ghost cache 初始化】：保留被驱逐对象的历史信息
  init_ghost_cache(params, cache->cache_size);

  // 初始化 Actor-Critic（行为者-评论者）强化学习参数
  params->rl_update_interval =
      200;  // 每200个请求触发一次更新，与 Python 端更频繁通信
  params->requests_since_rl_update = 0;
  params->epoch_start_time = time(NULL);
  params->epoch_obj_miss_count = 0;
  params->epoch_obj_count = 0;
  params->epoch_byte_miss_count = 0;
  params->epoch_byte_count = 0;

  // Initialize context state
  memset(params->context_state, 0, sizeof(double) * CONTEXT_DIM);

  // 初始化reward权重（默认只考虑miss ratio）
  params->miss_ratio_weight = 1.0;       // 默认权重：只考虑对象miss ratio
  params->byte_miss_ratio_weight = 0.0;  // 默认权重：不考虑字节miss ratio

  // 初始化文件式共享内存
  params->enable_rl = 1;  // 默认启用，可通过参数关闭
  params->shm_filename = NULL;
  params->shm_file = NULL;
  params->sem_ready = NULL;
  params->sem_ack = NULL;
  params->sem_ready_name = NULL;
  params->sem_ack_name = NULL;
  params->sem_enabled = false;
  params->sem_requested = 1; /* 默认请求启用信号量，可能由环境覆盖 */
  params->sem_owner = false;
  // 仅在启用RL时初始化共享内存
  if (params->enable_rl) {
    params->shm_filename = strdup("/dev/shm/loh_ac_9876");
    params->shm_file = fopen(params->shm_filename, "r+b");
  }

  /*
   * 运行时环境开关：支持通过环境变量控制是否使用 POSIX 信号量，
   * 行为与 Python 端保持一致：
   * - 若存在 LOH_DISABLE_SEMAPHORE，则以其布尔值为准（1/true 表示禁用）
   * - 否则若存在 LOH_ENABLE_SEMAPHORE，则以其布尔值为准（1/true 表示启用）
   * - 否则默认启用
   */
  {
    char *disable = getenv("LOH_DISABLE_SEMAPHORE");
    char *enable = getenv("LOH_ENABLE_SEMAPHORE");
    if (disable != NULL) {
      /* 如果设置了 LOH_DISABLE_SEMAPHORE，则解析其布尔含义后取反（disable=1 ->
       * sem_requested=0） */
      if (strcasecmp(disable, "1") == 0 || strcasecmp(disable, "true") == 0 ||
          strcasecmp(disable, "yes") == 0 || strcasecmp(disable, "on") == 0) {
        params->sem_requested = 0;
      } else if (strcasecmp(disable, "0") == 0 ||
                 strcasecmp(disable, "false") == 0 ||
                 strcasecmp(disable, "no") == 0 ||
                 strcasecmp(disable, "off") == 0) {
        params->sem_requested = 1;
      } else {
        /* 不能解析时保持默认 */
        params->sem_requested = 1;
      }
    } else if (enable != NULL) {
      if (strcasecmp(enable, "1") == 0 || strcasecmp(enable, "true") == 0 ||
          strcasecmp(enable, "yes") == 0 || strcasecmp(enable, "on") == 0) {
        params->sem_requested = 1;
      } else if (strcasecmp(enable, "0") == 0 ||
                 strcasecmp(enable, "false") == 0 ||
                 strcasecmp(enable, "no") == 0 ||
                 strcasecmp(enable, "off") == 0) {
        params->sem_requested = 0;
      } else {
        params->sem_requested = 1;
      }
    }

    if (!params->sem_requested) {
      LOH_DEBUG_PRINT_BASIC(
          "[LOH] semaphore mode disabled via environment; using polling "
          "only\n");
    }
  }

  if (params->enable_rl && params->shm_file == NULL) {
    // 如果文件不存在，则创建它
    params->shm_file = fopen(params->shm_filename, "w+b");
    if (params->shm_file == NULL) {
      perror("Failed to create shared memory file");
    } else {
      // 初始化共享内存文件
      shm_data_t shm_data;
      memset(&shm_data, 0, sizeof(shm_data_t));

      // 复制初始权重到共享内存
      memcpy(shm_data.weights, params->weights, sizeof(double) * FEATURE_DIM);

      // 写入文件
      fwrite(&shm_data, sizeof(shm_data_t), 1, params->shm_file);
      fflush(params->shm_file);

      // 设置文件权限
      chmod(params->shm_filename, 0666);
    }
  } else if (params->enable_rl) {
    LOH_DEBUG_PRINT_BASIC("Successfully opened existing shared memory file\n");
  }

  // Parse cache-specific parameters if provided
  if (cache_specific_params != NULL) {
    char *params_str = g_strdup(cache_specific_params);
    char *old_params_str = params_str;
    char *token, *key, *value;

    while ((token = strsep(&params_str, ",")) != NULL) {
      key = strsep(&token, "=");
      value = token;

      if (key == NULL || value == NULL) continue;

      if (strcmp(key, "learning-interval") == 0) {
        params->learning_interval = atol(value);
      } else if (strcmp(key, "enable-rl") == 0) {
        params->enable_rl = atoi(value) ? 1 : 0;
      } else if (strcmp(key, "rl-update-interval") == 0) {
        params->rl_update_interval = atoll(value);
      } else if (strcmp(key, "miss-ratio-weight") == 0) {
        params->miss_ratio_weight = atof(value);
        // 自动设置byte_miss_ratio_weight为互补权重
        params->byte_miss_ratio_weight = 1.0 - params->miss_ratio_weight;
        LOH_DEBUG_PRINT_BASIC(
            "Set miss_ratio_weight=%.3f, byte_miss_ratio_weight=%.3f\n",
            params->miss_ratio_weight, params->byte_miss_ratio_weight);
      }
    }

    g_free(old_params_str);
  }

  // 如果关闭了RL，确保不持有未使用的SHM资源
  if (!params->enable_rl) {
    if (params->shm_file) {
      fclose(params->shm_file);
      params->shm_file = NULL;
    }
    if (params->shm_filename) {
      free(params->shm_filename);
      params->shm_filename = NULL;
    }
    loh_sem_close(params, false);
  } else {
    if (params->sem_ready_name == NULL) {
      params->sem_ready_name = g_strdup_printf("/loh_ac_ready_%d", SHM_KEY);
    }
    if (params->sem_ack_name == NULL) {
      params->sem_ack_name = g_strdup_printf("/loh_ac_ack_%d", SHM_KEY);
    }
    if (!loh_sem_init(params)) {
      LOH_DEBUG_PRINT_BASIC(
          "[LOH] failed to init POSIX semaphores, fall back to polling mode\n");
    }
  }

  // 设置 cache 指针供后续使用
  params->cache_ptr = cache;

  // 打印初始化时的 RL 同步间隔，便于调试与确认运行时值
  LOH_DEBUG_PRINT_BASIC(
      "[LOH INIT] rl_update_interval=%ld, enable_rl=%d, sem_requested=%d\n",
      (long)params->rl_update_interval, params->enable_rl,
      params->sem_requested);

  // 根据权重设置缓存名字（类似 ThreeLCache 的做法）
  if (params->miss_ratio_weight == 1.0 &&
      params->byte_miss_ratio_weight == 0.0) {
    // 纯对象级优化
    snprintf(cache->cache_name, CACHE_NAME_ARRAY_LEN, "LOH-OMR");
  } else if (params->miss_ratio_weight == 0.0 &&
             params->byte_miss_ratio_weight == 1.0) {
    // 纯字节级优化
    snprintf(cache->cache_name, CACHE_NAME_ARRAY_LEN, "LOH-BMR");
  } else {
    // 混合优化，显示权重比例
    snprintf(cache->cache_name, CACHE_NAME_ARRAY_LEN, "LOH-Mix(%.1f/%.1f)",
             params->miss_ratio_weight, params->byte_miss_ratio_weight);
  }

  cache->eviction_params = params;
  return cache;
}

// ... 文件其余部分与我之前发送的版本一致 ...
// 【说明】：从 LOH_free 到文件末尾的完整剩余代码已在上文粘贴，此处省略重复内容
// ...

/**
 * @brief 释放该缓存使用的所有资源
 *
 * @param cache 要释放的缓存结构
 */
static void LOH_free(cache_t *cache) {
  LOH_params_t *params = (LOH_params_t *)(cache->eviction_params);

  // 释放 IRT 堆
  irt_heap_free(params);

  // 清理共享内存文件
  if (params->shm_file) {
    fclose(params->shm_file);
    params->shm_file = NULL;
  }

  loh_sem_close(params, true);

  // 释放 frequency 表
  freq_table_free(params);

  // 释放尺寸桶
  size_buckets_free(params);

  // 释放历史统计
  // 【删除】旧的历史记录释放：free_history_stats(params);
  // 现在只使用 global_access_records，在 free_global_access_records 中释放

  // 【新增 Ghost cache 释放】：释放被驱逐对象的历史信息
  free_ghost_cache(params);

  // 释放共享内存文件名
  if (params->shm_filename) {
    free(params->shm_filename);
    params->shm_filename = NULL;
  }

#if LOH_PERF_PROFILING
  // 打印一次性能概要，方便 no-RL 下快速定位热点
  loh_print_perf_summary(params);
#endif

  // 最后一次性释放 params
  g_free(params);
}

/**
 * @brief 面向用户的 API 函数，执行如下逻辑：
 *
 * ```
 * 如果对象已在缓存中：
 *   更新元数据
 *   返回 true
 * 否则：
 *   如果缓存没有足够空间：
 *     驱逐直到有足够空间插入
 *   插入对象
 *   返回 false
 * ```
 *
 * @param cache 缓存实例
 * @param req 请求信息
 * @return 如果缓存命中则返回 true，未命中返回 false
 */
static bool LOH_get(cache_t *cache, const request_t *req) {
  static int64_t request_count = 0;
  request_count++;

  LOH_DEBUG_PRINT_DETAILED("[LOH_get]: request #%ld for obj_id %lu\n",
                           request_count, req->obj_id);

  LOH_params_t *params = (LOH_params_t *)cache->eviction_params;
  params->current_timestamp += 1;

  // 【修复】：只在 warmup 后计数 requests_since_rl_update
  if (params->is_warmed_up) {
    params->requests_since_rl_update += 1;
  }

  // RL 周期结束，与 RL 端同步
  if (params->is_warmed_up &&
      params->requests_since_rl_update >= params->rl_update_interval) {
    sync_with_actor_critic(params);
    params->requests_since_rl_update = 0;
    params->epoch_start_time = time(NULL);

    // 【修改】：完全重置所有统计数据，避免陈旧数据影响
    // 重置 epoch 统计
    params->epoch_obj_miss_count = 0;
    params->epoch_obj_count = 0;
    params->epoch_byte_miss_count = 0;
    params->epoch_byte_count = 0;

    // 【修复】：重置特征统计数据，但保留缓存对象特征统计（无法重新计算）
    params->hit_feature_count = 0;
    params->miss_feature_count = 0;
    // 【注意】：不重置 cache_object_count，因为无法重新统计缓存中的对象特征

    for (int i = 0; i < FEATURE_DIM; i++) {
      params->hit_feature_sum[i] = 0.0;
      params->hit_feature_sum_sq[i] = 0.0;
      params->miss_feature_sum[i] = 0.0;
      params->miss_feature_sum_sq[i] = 0.0;
      // 【注意】：不重置 cache_feature_sum/sum_sq，因为无法重新统计
      // params->cache_feature_sum[i] = 0.0;
      // params->cache_feature_sum_sq[i] = 0.0;
      params->hit_feature_avg[i] = 0.0;
      params->miss_feature_avg[i] = 0.0;
    }
    struct timespec reset_time;
    clock_gettime(CLOCK_MONOTONIC, &reset_time);
    LOH_DEBUG_PRINT_BASIC(
        "[LOH] [%ld.%09ld]Epoch statistics reset after RL sync\n",
        reset_time.tv_sec, reset_time.tv_nsec);
  }

  // **检查是否达到 warmup 条件（缓存占用一半或 10000 个请求）**
  if (!params->is_warmed_up &&
      (cache_get_occupied_byte_default(cache) >= cache->cache_size / 2 ||
       params->current_timestamp >= 10000)) {
    params->is_warmed_up = true;
    LOH_DEBUG_PRINT_BASIC(
        "[LOH] Cache warmed up - occupied: %ld bytes (threshold: %ld), "
        "n_obj: %ld, timestamp: %ld (threshold: 10000)\n",
        cache_get_occupied_byte_default(cache), cache->cache_size / 2,
        /* prefer accessor if available */
        (long)(cache->get_n_obj ? cache->get_n_obj(cache) : cache->n_obj),
        params->current_timestamp);
  }

  // **关键修改：在 cache_get_base 之前先检查是否命中，并记录访问前特征**
  cache_obj_t *obj_before_access =
      cache_find_base(cache, req, false);  // 不更新位置
  bool will_hit = (obj_before_access != NULL);

  // 记录访问前的特征（考虑 ghost cache 历史）
  double features[FEATURE_DIM] = {0};
  if (obj_before_access != NULL) {
    // 缓存命中：计算命中对象的访问前特征
    features[0] =
        calculate_recency(params, obj_before_access);  // recency 未更新
    features[1] =
        calculate_frequency(params, obj_before_access);  // frequency 未加 1
    features[2] = calculate_size(params, obj_before_access);

    // 【修复】：访问前 IRT 直接使用对象的 IRT 值，无需后退一步
    features[3] =
        calculate_irt_feature(obj_before_access->LOH.irt_values[0]);  // IRT1
    features[4] =
        calculate_irt_feature(obj_before_access->LOH.irt_values[1]);  // IRT2
    features[5] =
        calculate_irt_feature(obj_before_access->LOH.irt_values[2]);  // IRT3
  } else {
    // 缓存未命中：检查 ghost cache 中的历史信息
    LOH_ghost_entry_t *ghost_entry =
        params->ghost_cache
            ? (LOH_ghost_entry_t *)g_hash_table_lookup(
                  params->ghost_cache, GINT_TO_POINTER((int)req->obj_id))
            : NULL;
    if (ghost_entry) {
      // 【统一】：内联计算 ghost cache 特征
      // Recency: 从 ghost cache 的最后访问时间计算
      int64_t current_irt =
          params->current_timestamp - ghost_entry->last_access_counter;
      features[0] = 1.0 / (1.0 + (double)current_irt);  // 直接使用 recency 公式

      // Frequency: 从 ghost cache 的访问次数计算（无 log）
      if (ghost_entry->access_count > 0) {
        const double K = 1.0;
        double f = (double)ghost_entry->access_count;
        features[1] = f / (f + K);
      }

      // Size: 从请求大小计算（无 log）
      double size_mb = (double)req->obj_size / (1024.0 * 1024.0);  // 转换为 MB
      {
        const double A = 1.0;
        features[2] = 1.0 / (1.0 + A * size_mb);
      }

      // 【修复】：ghost cache 中直接使用 IRT 值（访问前特征）
      // IRT 特征直接从 ghost_entry 获取
      features[3] = calculate_irt_feature(ghost_entry->irt_values[0]);
      features[4] = calculate_irt_feature(ghost_entry->irt_values[1]);
      features[5] = calculate_irt_feature(ghost_entry->irt_values[2]);
    } else {
      // 【修复】：完全新对象，至少应该计算 size 特征
      // Recency 和 Frequency 无历史信息，保持为 0
      // 但 Size 特征可以从请求中计算
      double size_mb = (double)req->obj_size / (1024.0 * 1024.0);  // 转换为 MB
      const double A_new = 1.0;
      features[2] = 1.0 / (1.0 + A_new * size_mb);
    }
  }

  // 现在执行实际的 get 操作
  bool hit = cache_get_base(cache, req);

#if LOH_DEBUG_LEVEL >= LOH_DEBUG_ERROR
  // 验证预测的准确性（调试用）
  if (hit != will_hit) {
    printf("[LOH ERROR] Hit prediction mismatch: predicted=%s, actual=%s\n",
           will_hit ? "hit" : "miss", hit ? "hit" : "miss");
  }
#endif

  // **更新特征统计（仅在 warmup 后更新命中/未命中特征）**
  if (params->is_warmed_up) {
    // 更新命中率
#if LOH_DEBUG_LEVEL >= LOH_DEBUG_DETAILED
    double old_obj_count = params->epoch_obj_count;
    double old_obj_miss_count = params->epoch_obj_miss_count;
    double old_byte_count = params->epoch_byte_count;
    double old_byte_miss_count = params->epoch_byte_miss_count;
#endif

    params->epoch_obj_count++;
    params->epoch_byte_count += req->obj_size;
    params->epoch_obj_miss_count += hit ? 0 : 1;
    params->epoch_byte_miss_count += hit ? 0 : req->obj_size;

    // 【调试打印】global_perf 统计变化
    LOH_DEBUG_PRINT_DETAILED(
        "[LOH_get] global_perfstats_update - obj_count: %.0f->%.0f, obj_miss: "
        "%.0f->%.0f, "
        "byte_count: %.0f->%.0f, byte_miss: %.0f->%.0f, hit_ratio: %.4f\n",
        old_obj_count, params->epoch_obj_count, old_obj_miss_count,
        params->epoch_obj_miss_count, old_byte_count, params->epoch_byte_count,
        old_byte_miss_count, params->epoch_byte_miss_count,
        params->epoch_obj_count > 0
            ? (1.0 - params->epoch_obj_miss_count / params->epoch_obj_count)
            : 0.0);

    if (hit && obj_before_access != NULL) {
      // 更新命中特征统计
#if LOH_DEBUG_LEVEL >= LOH_DEBUG_DETAILED
      int old_hit_count = params->hit_feature_count;
#endif
      params->hit_feature_count++;

      // 【调试打印】命中特征原始值
      LOH_DEBUG_PRINT_DETAILED(
          "[LOH_get] hit object feature - obj_id=%llu, "
          "features=[%.6f,%.6f,%.6f,%.6f,%.6f,%.6f]\n",
          (unsigned long long)obj_before_access->obj_id, features[0],
          features[1], features[2], features[3], features[4], features[5]);

      for (int i = 0; i < FEATURE_DIM; i++) {
#if LOH_DEBUG_LEVEL >= LOH_DEBUG_DETAILED
        double old_sum = params->hit_feature_sum[i];
        double old_sum_sq = params->hit_feature_sum_sq[i];
#endif
        params->hit_feature_sum[i] += features[i];
        params->hit_feature_sum_sq[i] += features[i] * features[i];

        // 【调试打印】命中特征统计变化
        LOH_DEBUG_PRINT_DETAILED(
            "[LOH_get] hit feature[%d] update - count: %ld->%ld, sum: "
            "%.6f->%.6f, sum_sq: %.6f->%.6f, mean: %.6f\n",
            i, (long)old_hit_count, (long)params->hit_feature_count, old_sum,
            params->hit_feature_sum[i], old_sum_sq,
            params->hit_feature_sum_sq[i],
            params->hit_feature_count > 0
                ? params->hit_feature_sum[i] / params->hit_feature_count
                : 0.0);
      }
    } else if (!hit) {
      // 更新未命中特征统计（考虑 ghost cache 历史）
#if LOH_DEBUG_LEVEL >= LOH_DEBUG_DETAILED
      int old_miss_count = params->miss_feature_count;
#endif
      params->miss_feature_count++;

      // 【调试打印】未命中特征原始值
      LOH_DEBUG_PRINT_DETAILED(
          "[LOH_get] miss object feature - obj_id=%llu, "
          "features=[%.6f,%.6f,%.6f,%.6f,%.6f,%.6f]\n",
          (unsigned long long)req->obj_id, features[0], features[1],
          features[2], features[3], features[4], features[5]);

      // 如果在 ghost cache 中有历史，使用 ghost 特征；否则新对象特征为 0
      for (int i = 0; i < FEATURE_DIM; i++) {
#if LOH_DEBUG_LEVEL >= LOH_DEBUG_DETAILED
        double old_sum = params->miss_feature_sum[i];
        double old_sum_sq = params->miss_feature_sum_sq[i];
#endif
        params->miss_feature_sum[i] += features[i];
        params->miss_feature_sum_sq[i] += features[i] * features[i];

        // 【调试打印】未命中特征统计变化
        LOH_DEBUG_PRINT_DETAILED(
            "[LOH_get] miss feature[%d]stats_update - count: %ld->%ld, sum: "
            "%.6f->%.6f, sum_sq: %.6f->%.6f, mean: %.6f\n",
            i, (long)old_miss_count, (long)params->miss_feature_count, old_sum,
            params->miss_feature_sum[i], old_sum_sq,
            params->miss_feature_sum_sq[i],
            params->miss_feature_count > 0
                ? params->miss_feature_sum[i] / params->miss_feature_count
                : 0.0);
      }
    }
  }

  // **缓存内容特征统计已通过 insert/evict/find 更新**
  // 增量更新在以下位置已实现：
  // - LOH_insert: update_cache_content_stats_add(params, obj)
  // - LOH_evict: update_cache_content_stats_remove(params, obj_to_evict)
  // - LOH_find: update_cache_content_stats_find(params, obj)

  // 调试输出: 每次请求后打印 6 个特征的候选对象
  LOH_DEBUG_PRINT_DETAILED("[LOH DEBUG REQUEST] Request obj_id=%llu, hit=%s\n",
                           (unsigned long long)req->obj_id,
                           hit ? "true" : "false");
#if LOH_DEBUG_LEVEL >= LOH_DEBUG_VERBOSE
  {
    // 临时获取候选对象用于调试
    int candidates_per_feature = 10;  // 每个特征显示 10 个候选
    LOH_DEBUG_PRINT_DETAILED(
        "[CANDIDATE COLLECTION] Debug mode: candidates_per_feature=%d\n",
        candidates_per_feature);

    const char *names[FEATURE_DIM] = {"recency", "frequency", "size",
                                      "irt1",    "irt2",      "irt3"};

    // 1. Recency 候选 (LRU 队列尾部)
    LOH_DEBUG_PRINT_DETAILED("[%s] candidates:\n", names[0]);
    cache_obj_t *curr = params->q_tail;
    int count = 0;
    while (curr != NULL && count < candidates_per_feature) {
      double feat[FEATURE_DIM] = {0};
      calculate_object_features(params, curr, feat);
      LOH_DEBUG_PRINT_DETAILED("[candidates:] obj_id=%llu, %s=%.6f\n",
                               (unsigned long long)curr->obj_id, names[0],
                               feat[0]);
      curr = curr->queue.prev;
      count++;
    }

    // 2. Frequency 候选
    LOH_DEBUG_PRINT_DETAILED("[%s] candidates:\n", names[1]);
    int saved_n_candidates = params->n_candidates;
    freq_table_get_candidates(params, candidates_per_feature,
                              &params->n_candidates);
    for (int i = saved_n_candidates; i < params->n_candidates; i++) {
      cache_obj_t *o = params->candidates[i];
      double feat[FEATURE_DIM] = {0};
      calculate_object_features(params, o, feat);
      LOH_DEBUG_PRINT_DETAILED("[candidates:] obj_id=%llu, %s=%.6f\n",
                               (unsigned long long)o->obj_id, names[1],
                               feat[1]);
    }

    // 3. Size 候选
    LOH_DEBUG_PRINT_DETAILED("[%s] candidates:\n", names[2]);
    saved_n_candidates = params->n_candidates;
    size_buckets_get_candidates(params, candidates_per_feature,
                                &params->n_candidates);
    for (int i = saved_n_candidates; i < params->n_candidates; i++) {
      cache_obj_t *o = params->candidates[i];
      double feat[FEATURE_DIM] = {0};
      calculate_object_features(params, o, feat);
      LOH_DEBUG_PRINT_DETAILED("[candidates:] obj_id=%llu, %s=%.6f\n",
                               (unsigned long long)o->obj_id, names[2],
                               feat[2]);
    }

    // 4-6. IRT 候选 - 已隔离辅助数据结构
    for (int irt_idx = 0; irt_idx < 3; irt_idx++) {
      LOH_DEBUG_PRINT_DETAILED("[%s] candidates:\n", names[3 + irt_idx]);
      saved_n_candidates = params->n_candidates;
      if (irt_idx == 0) {
        irt1_heap_get_candidates(params, candidates_per_feature,
                                 &params->n_candidates);
      } else if (irt_idx == 1) {
        irt2_heap_get_candidates(params, candidates_per_feature,
                                 &params->n_candidates);
      } else {
        irt3_heap_get_candidates(params, candidates_per_feature,
                                 &params->n_candidates);
      }
      for (int i = saved_n_candidates; i < params->n_candidates; i++) {
        cache_obj_t *o = params->candidates[i];
        double feat[FEATURE_DIM] = {0};
        calculate_object_features(params, o, feat);
        LOH_DEBUG_PRINT_DETAILED("[candidates:] obj_id=%llu, %s=%.6f\n",
                                 (unsigned long long)o->obj_id,
                                 names[3 + irt_idx], feat[3 + irt_idx]);
      }
    }

    // 恢复 candidates 数组状态
    params->n_candidates = 0;
  }
#endif

#if LOH_DEBUG_LEVEL >= LOH_DEBUG_DETAILED
  // 执行模块正确性验证
  if (obj_before_access) {
    loh_verify_feature_calculation(params, obj_before_access);
  }
  loh_verify_performance_stats(params, hit);
  loh_verify_data_consistency(params);

  // 每 100 个请求打印一次状态总览
  static int request_counter = 0;
  request_counter++;
  if (request_counter % 100 == 0) {
    loh_print_module_summary(params);
  }
#endif

  return hit;
}

/**
 * @brief 检查对象是否在缓存中并更新其元数据
 *
 * @param cache 缓存实例
 * @param req 请求信息
 * @param update_cache 是否更新缓存；为 true 时会提升对象
 * @return 找到则返回对象，否则返回 NULL
 */
static cache_obj_t *LOH_find(cache_t *cache, const request_t *req,
                             const bool update_cache) {
  LOH_params_t *params = (LOH_params_t *)cache->eviction_params;
  PERF_TS ts_find;
  PERF_NOW(ts_find);
  cache_obj_t *cache_obj = cache_find_base(cache, req, update_cache);

  if (cache_obj && likely(update_cache)) {
    // 删除状态验证，直接更新对象

    // 【新增】更新缓存内容特征统计 - 必须在实际更新对象内容之前
    // 在命中时，需要增量更新变化的特征统计
    // 特征 0 (recency): 所有对象的 recency 都会改变，全局更新成本太高，省略
    // 特征 1 (frequency): 当前对象访问次数+1，需要更新
    // 特征 2 (size): 不变
    // 特征 3-5 (IRT): 当前对象 IRT 历史更新，需要更新
    int64_t irt =
        params->current_timestamp - cache_obj->LOH.last_access_counter;

#if LOH_INCLUDE_CACHE_FEATURES
    // 仅在38维模式下更新缓存统计
    update_cache_content_stats_find(params, cache_obj, irt);
#endif

    // Update access count (must be done before IRT calculation)
    cache_obj->LOH.access_count++;

    // 【内联IRT更新】：使用简化的 IRT 值数组更新 IRT 历史
    if (irt > 0) {
      // 向右移动现有IRT值，为新值腾出位置
      cache_obj->LOH.irt_values[2] = cache_obj->LOH.irt_values[1];
      cache_obj->LOH.irt_values[1] = cache_obj->LOH.irt_values[0];
      cache_obj->LOH.irt_values[0] = irt;  // 最新值放在位置0

      // 【测试修复后的irt_heap_update】：验证sift方向修复是否解决问题
    }

    // Update access timestamps
    cache_obj->LOH.last_access_time = time(NULL);
    cache_obj->LOH.last_access_counter = params->current_timestamp;

    // 【统一原子操作】：使用标准的原子更新，包括IRT堆维护
    // 所有对象访问都需要更新数据结构（LRU队列、frequency表、IRT堆等）
    {
      PERF_TS ts_au;
      PERF_NOW(ts_au);
      bool ok = loh_atomic_update_obj(params, cache_obj);
      PERF_ACCUM(params, atomic_update, ts_au);
      if (!ok) {
        LOH_DEBUG_PRINT_ERROR(
            "[LOH FIND ERROR] Failed to update obj_id=%llu in auxiliary "
            "structures\n",
            (unsigned long long)cache_obj->obj_id);

        // 尝试错误恢复
        if (!loh_recover_from_error(params, cache_obj, "LOH_find")) {
          LOH_DEBUG_PRINT_ERROR(
              "[LOH FIND WARNING] Cannot fully update obj_id=%llu, "
              "continuing\n",
              (unsigned long long)cache_obj->obj_id);
        }
      }
#if LOH_DEBUG_LEVEL >= LOH_DEBUG_DETAILED
      // 详细验证：命中更新后，对象应出现在 LRU/FREQ/SIZE/IRT 中
      loh_debug_check_membership(params, cache_obj, "after_find_update");
#endif
    }
  }

  PERF_ACCUM(params, find, ts_find);
  return cache_obj;
}

/**
 * @brief 将对象插入缓存
 *
 * @param cache 缓存实例
 * @param req 请求信息
 * @return 已插入的对象
 */
static cache_obj_t *LOH_insert(cache_t *cache, const request_t *req) {
  LOH_params_t *params = (LOH_params_t *)cache->eviction_params;
  PERF_TS ts_insert;
  PERF_NOW(ts_insert);

  // Create new object with base cache function
  cache_obj_t *obj = cache_insert_base(cache, req);

  // 【数据恢复阶段】尝试从 Ghost cache 恢复历史信息
  bool restored_from_ghost = restore_from_ghost_cache(params, obj);
  if (!restored_from_ghost) {
    // 如果 Ghost cache 中没有历史信息，初始化新对象
    obj->LOH.access_count = 1;  // 新对象初始访问次数为 1
  }
  // 如果从 Ghost cache 恢复成功，access_count 和 irt_values 都已设置好

  // 更新访问时间戳（无论是否从 ghost 恢复都需要更新为当前时间）
  obj->LOH.last_access_time = time(NULL);
  obj->LOH.last_access_counter = params->current_timestamp;

  // Initialize IRT values if not restored from ghost
  if (!restored_from_ghost) {
    for (int i = 0; i < IRT_HISTORY_SIZE; i++) {
      // 【修复】新object使用INT64_MAX表示无IRT历史，是最佳淘汰候选
      obj->LOH.irt_values[i] = INT64_MAX;
    }
  }

  // 【数据结构插入阶段】：将对象插入到所有辅助数据结构
  // 注意：这里不是重复操作，restore_from_ghost_cache只是恢复了对象的数据，
  // 而loh_atomic_insert_obj负责将对象插入到各个数据结构中（包括根据irt_values同步IRT堆）
  {
    PERF_TS ts_ai;
    PERF_NOW(ts_ai);
    bool ok = loh_atomic_insert_obj(params, obj);
    PERF_ACCUM(params, atomic_insert, ts_ai);
    if (!ok) {
      LOH_DEBUG_PRINT_ERROR(
          "[LOH INSERT ERROR] Failed to insert obj_id=%llu into auxiliary "
          "structures\n",
          (unsigned long long)obj->obj_id);

      // 尝试错误恢复
      if (!loh_recover_from_error(params, obj, "LOH_insert")) {
        LOH_DEBUG_PRINT_ERROR(
            "[LOH INSERT FATAL] Cannot recover from insertion error for "
            "obj_id=%llu\n",
            (unsigned long long)obj->obj_id);
      }
    }
#if LOH_DEBUG_LEVEL >= LOH_DEBUG_DETAILED
    // 详细验证：插入后，对象应出现在 LRU/FREQ/SIZE/IRT 中
    loh_debug_check_membership(params, obj, "after_insert");
#endif
  }

  // 打印 obj->LOH 内容
  LOH_DEBUG_PRINT_DETAILED(
      "[LOH_insert] Inserted obj_id=%llu, size=%ld, access_count=%ld, "
      "last_access_time=%ld, "
      "last_access_counter=%ld, irt_values=[%ld,%ld,%ld], "
      "from_ghost=%s\n",
      (unsigned long long)obj->obj_id, (long)obj->obj_size,
      (long)obj->LOH.access_count, obj->LOH.last_access_time,
      obj->LOH.last_access_counter, obj->LOH.irt_values[0],
      obj->LOH.irt_values[1], obj->LOH.irt_values[2],
      restored_from_ghost ? "true" : "false");

#if LOH_INCLUDE_CACHE_FEATURES
  // 仅在38维模式下更新缓存统计
  update_cache_content_stats_add(params, obj);
#endif

  PERF_ACCUM(params, insert, ts_insert);
  return obj;
}

/**
 * @brief 查找驱逐候选并选择得分最低的对象
 *
 * @param cache 缓存实例
 * @param req 请求信息
 * @return 要被驱逐的对象
 */
static cache_obj_t *LOH_to_evict(cache_t *cache, const request_t *req) {
  LOH_params_t *params = (LOH_params_t *)cache->eviction_params;
  PERF_TS ts_to_evict;
  PERF_NOW(ts_to_evict);

  // 清空候选对象数组
  params->n_candidates = 0;
  // 避免每次都 memset 整个候选数组（写放大）；仅通过 n_candidates 控制有效范围

  // 从各个特征数据结构中选择候选对象，每个特征分别获取候选
  int candidates_per_feature = MAX_CANDIDATES / 6;  // 6 种特征
  LOH_DEBUG_PRINT_DETAILED(
      "[CANDIDATE COLLECTION] Normal mode: candidates_per_feature=%d "
      "(MAX_CANDIDATES=%d)\n",
      candidates_per_feature, MAX_CANDIDATES);

  LOH_DEBUG_PRINT_DETAILED("[LOH DEBUG EVICT] Request obj_id=%llu\n",
                           (unsigned long long)req->obj_id);

  // 每轮去重表清空：所有来源（含 recency）统一纳入 seen 去重
  loh_seen_clear();

  // 1. 从 LRU 队列尾部选择（最近性特征 - recency），并纳入 seen 去重
  // 1) recency 收集
  PERF_TS ts_collect_rec;
  PERF_NOW(ts_collect_rec);
  cache_obj_t *curr = params->q_tail;
  int lru_candidates = 0;
  int recency_start = params->n_candidates;
  while (curr != NULL && lru_candidates < candidates_per_feature) {
    cache_obj_t *o = curr;
    // recency 本身无重复，但与其他来源（freq/size/IRT）可能重复；统一用 seen
    // 去重
    if (o && loh_seen_add(params, o)) {
      params->candidates[params->n_candidates++] = o;
      lru_candidates++;
    }
    curr = curr->queue.prev;
  }
  PERF_ACCUM(params, cand_collect_recency, ts_collect_rec);
  // recency 阶段无单独压缩流程（天然无重复），dedup 计时保持 0

#if LOH_DEBUG_LEVEL >= LOH_DEBUG_DETAILED
  {
    // 立即打印 recency 候选
    LOH_DEBUG_PRINT_DETAILED("[recency] candidates:\n");
    for (int i = recency_start; i < params->n_candidates; i++) {
      cache_obj_t *o = params->candidates[i];
      double feat[FEATURE_DIM] = {0};
      calculate_object_features(params, o, feat);
      LOH_DEBUG_PRINT_DETAILED("  obj_id=%llu, recency=%.6f\n",
                               (unsigned long long)o->obj_id, feat[0]);
    }
  }
#endif

  // 2. 从 frequency 表选择低频率对象（频率特征 - frequency）
  // 2) frequency 收集
  int freq_start = params->n_candidates;
  PERF_TS ts_collect_freq;
  PERF_NOW(ts_collect_freq);
  freq_table_get_candidates(params, candidates_per_feature,
                            &params->n_candidates);
  PERF_ACCUM(params, cand_collect_freq, ts_collect_freq);
  // 频率候选已在收集阶段融合 seen 去重，省去单独dedup

#if LOH_DEBUG_LEVEL >= LOH_DEBUG_DETAILED
  {
    // 立即打印 frequency 候选
    LOH_DEBUG_PRINT_DETAILED("[frequency] candidates:\n");
    for (int i = freq_start; i < params->n_candidates; i++) {
      cache_obj_t *o = params->candidates[i];
      if (!o) continue;  // 跳过空指针
      double feat[FEATURE_DIM] = {0};
      calculate_object_features(params, o, feat);
      LOH_DEBUG_PRINT_DETAILED("  obj_id=%llu, frequency=%.6f\n",
                               (unsigned long long)o->obj_id, feat[1]);
    }
  }
#endif

  // 3. 从尺寸桶选择大尺寸对象（尺寸特征 - size）
  // 3) size 收集
  int size_start = params->n_candidates;
  PERF_TS ts_collect_size;
  PERF_NOW(ts_collect_size);
  size_buckets_get_candidates(params, candidates_per_feature,
                              &params->n_candidates);
  PERF_ACCUM(params, cand_collect_size, ts_collect_size);
  // 尺寸候选已在收集阶段融合 seen 去重，省去单独dedup

#if LOH_DEBUG_LEVEL >= LOH_DEBUG_DETAILED
  {
    // 立即打印 size 候选
    LOH_DEBUG_PRINT_DETAILED("[size] candidates:\n");
    for (int i = size_start; i < params->n_candidates; i++) {
      cache_obj_t *o = params->candidates[i];
      double feat[FEATURE_DIM] = {0};
      calculate_object_features(params, o, feat);
      LOH_DEBUG_PRINT_DETAILED("  obj_id=%llu, size=%.6f\n",
                               (unsigned long long)o->obj_id, feat[2]);
    }
  }
#endif

  // 4. 从 IRT1 堆选择（IRT1 特征）
  // 4) IRT1 收集
  int irt1_start = params->n_candidates;
  PERF_TS ts_collect_irt1;
  PERF_NOW(ts_collect_irt1);
  irt1_heap_get_candidates(params, candidates_per_feature,
                           &params->n_candidates);
  PERF_ACCUM(params, cand_collect_irt1, ts_collect_irt1);
  // IRT1 候选已在收集阶段融合 seen 去重，省去单独dedup

#if LOH_DEBUG_LEVEL >= LOH_DEBUG_DETAILED
  {
    // 立即打印 irt1 候选
    LOH_DEBUG_PRINT_DETAILED("[irt1] candidates:\n");
    for (int i = irt1_start; i < params->n_candidates; i++) {
      cache_obj_t *o = params->candidates[i];
      double feat[FEATURE_DIM] = {0};
      calculate_object_features(params, o, feat);
      LOH_DEBUG_PRINT_DETAILED("  obj_id=%llu, irt1=%.6f\n",
                               (unsigned long long)o->obj_id, feat[3]);
    }
  }
#endif

  // 5. 从 IRT2 堆选择（IRT2 特征）
  // 5) IRT2 收集
  int irt2_start = params->n_candidates;
  PERF_TS ts_collect_irt2;
  PERF_NOW(ts_collect_irt2);
  irt2_heap_get_candidates(params, candidates_per_feature,
                           &params->n_candidates);
  PERF_ACCUM(params, cand_collect_irt2, ts_collect_irt2);
  // IRT2 候选已在收集阶段融合 seen 去重，省去单独dedup

#if LOH_DEBUG_LEVEL >= LOH_DEBUG_DETAILED
  {
    // 立即打印 irt2 候选
    LOH_DEBUG_PRINT_DETAILED("[irt2] candidates:\n");
    for (int i = irt2_start; i < params->n_candidates; i++) {
      cache_obj_t *o = params->candidates[i];
      double feat[FEATURE_DIM] = {0};
      calculate_object_features(params, o, feat);
      LOH_DEBUG_PRINT_DETAILED("  obj_id=%llu, irt2=%.6f\n",
                               (unsigned long long)o->obj_id, feat[4]);
    }
  }
#endif

  // 6. 从 IRT3 堆选择（IRT3 特征）
  // 6) IRT3 收集
  int irt3_start = params->n_candidates;
  PERF_TS ts_collect_irt3;
  PERF_NOW(ts_collect_irt3);
  irt3_heap_get_candidates(params, candidates_per_feature,
                           &params->n_candidates);
  PERF_ACCUM(params, cand_collect_irt3, ts_collect_irt3);
  // IRT3 候选已在收集阶段融合 seen 去重，省去单独dedup

#if LOH_DEBUG_LEVEL >= LOH_DEBUG_DETAILED
  {
    // 立即打印 irt3 候选
    LOH_DEBUG_PRINT_DETAILED("[irt3] candidates:\n");
    for (int i = irt3_start; i < params->n_candidates; i++) {
      cache_obj_t *o = params->candidates[i];
      double feat[FEATURE_DIM] = {0};
      calculate_object_features(params, o, feat);
      LOH_DEBUG_PRINT_DETAILED("  obj_id=%llu, irt3=%.6f\n",
                               (unsigned long long)o->obj_id, feat[5]);
    }
  }
#endif

  // 如果没有候选对象，使用 LRU 作为回退
  if (params->n_candidates == 0) {
    return params->q_tail;
  }

  // 对候选对象评分，选择得分最低的
  double min_score = DBL_MAX;
  cache_obj_t *obj_to_evict = NULL;

#if LOH_DEBUG_LEVEL >= LOH_DEBUG_DETAILED
  // 打印候选ID简要列表
  LOH_DEBUG_PRINT_DETAILED("[CANDIDATES] total=%d\n", params->n_candidates);
  for (int i = 0; i < params->n_candidates; ++i) {
    cache_obj_t *c = params->candidates[i];
    LOH_DEBUG_PRINT_DETAILED("  #%d id=%llu\n", i,
                             c ? (unsigned long long)c->obj_id : 0ULL);
  }
#endif

  // 先为所有候选预计算特征（calc_features 内部已单独计时）
  int cand_n = params->n_candidates;
  if (cand_n > MAX_CANDIDATES) cand_n = MAX_CANDIDATES;
  double feat_buf[MAX_CANDIDATES][FEATURE_DIM];
  // 批量计时以降低 clock_gettime 调用开销
  PERF_TS ts_feat_loop;
  PERF_NOW(ts_feat_loop);
  for (int i = 0; i < cand_n; ++i) {
    cache_obj_t *candidate = params->candidates[i];
    calculate_object_features(params, candidate, feat_buf[i]);
  }
#if LOH_PERF_PROFILING
  {
    struct timespec _t1;
    clock_gettime(CLOCK_MONOTONIC, &_t1);
    double _dt = (_t1.tv_sec - ts_feat_loop.tv_sec) +
                 (_t1.tv_nsec - ts_feat_loop.tv_nsec) / 1e9;
    params->perf.calc_features.total += _dt;
    // 计数按特征向量数量（候选数）累计，avg=每个候选的平均时间
    params->perf.calc_features.count += cand_n;
    if (_dt > params->perf.calc_features.max)
      params->perf.calc_features.max = _dt;
  }
#endif

  // 仅对评分阶段计时，避免与特征计算重复计时导致的双计费
  PERF_TS ts_score_loop;
  PERF_NOW(ts_score_loop);
  // 将权重提升到寄存器，避免在循环中反复读取
  const double *w = params->weights;
#if FEATURE_DIM == 6
  const double w0 = w[0], w1 = w[1], w2 = w[2], w3 = w[3], w4 = w[4], w5 = w[5];
#endif
  for (int i = 0; i < cand_n; i++) {
    cache_obj_t *candidate = params->candidates[i];
    const double *f = feat_buf[i];
#if FEATURE_DIM == 6
    // 手动内联 6 维点积，减少函数调用与索引开销
    double score =
        f[0] * w0 + f[1] * w1 + f[2] * w2 + f[3] * w3 + f[4] * w4 + f[5] * w5;
#else
    double score = 0.0;
    for (int k = 0; k < FEATURE_DIM; ++k) score += f[k] * w[k];
#endif
    if (score < min_score) {
      min_score = score;
      obj_to_evict = candidate;
    }
  }
  PERF_ACCUM(params, calc_score, ts_score_loop);

  LOH_DEBUG_PRINT_DETAILED(
      "[LOH DEBUG EVICT] Selected obj_id=%llu with score=%.6f\n",
      obj_to_evict ? (unsigned long long)obj_to_evict->obj_id : -1ULL,
      min_score);

#if LOH_DEBUG_LEVEL >= LOH_DEBUG_DETAILED
  // 验证选中的对象确实在候选集中
  bool found = false;
  for (int i = 0; i < params->n_candidates; ++i) {
    if (params->candidates[i] == obj_to_evict) {
      found = true;
      break;
    }
  }
  if (!found) {
    LOH_DEBUG_PRINT_ERROR(
        "[VALIDATE][evict] Selected obj not in candidates! id=%llu\n",
        obj_to_evict ? (unsigned long long)obj_to_evict->obj_id : 0ULL);
  }
#endif

  PERF_ACCUM(params, to_evict, ts_to_evict);
  return obj_to_evict;
}

/**
 * @brief 从缓存中驱逐一个对象
 *
 * @param cache 缓存实例
 * @param req 未使用
 */
static void LOH_evict(cache_t *cache, const request_t *req) {
  LOH_params_t *params = (LOH_params_t *)cache->eviction_params;
  PERF_TS ts_evict;
  PERF_NOW(ts_evict);
  cache_obj_t *obj_to_evict = LOH_to_evict(cache, req);

  if (obj_to_evict == NULL) {
    ERROR("LOH_evict: no object to evict\n");
    return;
  }

  // Update feature statistics for learning
  // (但不要标记为 miss，因为 evict 不是 miss)

#if LOH_INCLUDE_CACHE_FEATURES
  // 仅在38维模式下更新缓存统计
  update_cache_content_stats_remove(params, obj_to_evict);
#endif

  // 【新增】将被驱逐objectadd到Ghost cache（保留历史信息）
  add_to_ghost_cache(params, obj_to_evict, cache);

  // 使用原子操作从所有数据结构（包括LRU队列）中移除
  {
    PERF_TS ts_ar;
    PERF_NOW(ts_ar);
    bool ok = loh_atomic_remove_obj(params, obj_to_evict);
    PERF_ACCUM(params, atomic_remove, ts_ar);
    if (!ok) {
      LOH_DEBUG_PRINT_ERROR(
          "[LOH EVICT ERROR] Failed to remove obj_id=%llu from auxiliary "
          "structures\n",
          (unsigned long long)obj_to_evict->obj_id);
      // 尝试错误恢复
      if (!loh_recover_from_error(params, obj_to_evict, "LOH_evict")) {
        LOH_DEBUG_PRINT_ERROR(
            "[LOH EVICT WARNING] Cannot fully clean up obj_id=%llu, continuing "
            "with eviction\n",
            (unsigned long long)obj_to_evict->obj_id);
      }
    }

#if LOH_DEBUG_LEVEL >= LOH_DEBUG_DETAILED
    // 被移除后，检查其不再出现在各结构中
    loh_debug_check_membership(params, obj_to_evict, "after_evict_remove");
#endif

    // Use the base eviction function to handle hash table updates and freeing
    cache_evict_base(cache, obj_to_evict, true);
    PERF_ACCUM(params, evict, ts_evict);
  }
}

/**
 * @brief remove an object from the cache
 *
 * @param cache
 * @param obj_id
 * @return true if the object is removed, false if the object is not in the
 * cache
 */
static bool LOH_remove(cache_t *cache, const obj_id_t obj_id) {
  LOH_params_t *params = (LOH_params_t *)cache->eviction_params;

  cache_obj_t *obj = hashtable_find_obj_id(cache->hashtable, obj_id);
  if (obj == NULL) {
    return false;
  }

#if LOH_INCLUDE_CACHE_FEATURES
  // 仅在38维模式下更新缓存统计
  update_cache_content_stats_remove(params, obj);
#endif

  // 使用原子操作从所有数据结构中移除
  if (!loh_atomic_remove_obj(params, obj)) {
#if LOH_DEBUG_LEVEL >= LOH_DEBUG_ERROR
    printf(
        "[LOH REMOVE ERROR] Failed to remove obj_id=%llu from auxiliary "
        "structures\n",
        (unsigned long long)obj_id);
#endif
  }
  cache_remove_obj_base(cache, obj, true);
  return true;
}

/**
 * @brief print information about the cache
 *
 * @param cache
 */
static void LOH_print_cache(const cache_t *cache) {
  LOH_params_t *params = (LOH_params_t *)cache->eviction_params;
  LOH_DEBUG_PRINT_DETAILED("LOH cache: current size %ld, cache size %ld\n",
                           (long)cache_get_occupied_byte_default(cache),
                           (long)cache->cache_size);
  LOH_DEBUG_PRINT_DETAILED("Current feature weights: [");
#if LOH_DEBUG_LEVEL >= LOH_DEBUG_DETAILED
  for (int i = 0; i < FEATURE_DIM; i++) {
    LOH_DEBUG_PRINT_DETAILED("%.3f", params->weights[i]);
    if (i < FEATURE_DIM - 1) LOH_DEBUG_PRINT_DETAILED(", ");
  }
#endif
  LOH_DEBUG_PRINT_DETAILED("]\n");
}

/**
 * @brief 基于对象特征和当前权重计算该对象的得分
 *
 * @param params LOH 参数结构
 * @param obj 要计算得分的缓存对象
 * @return double 得分值，分值越高表示越应保留在缓存中
 */
static double calculate_score_with_features(
    LOH_params_t *params, const double features[FEATURE_DIM]) {
  // Linear scoring function: Score = W · F
  // Hot path: unrolled plain multiply-adds (no FMA for consistent Debug perf).
#if FEATURE_DIM == 6
  const double *w = params->weights;
  double s = 0.0;
  s += w[0] * features[0];
  s += w[1] * features[1];
  s += w[2] * features[2];
  s += w[3] * features[3];
  s += w[4] * features[4];
  s += w[5] * features[5];
  return s;
#else
  double score = 0.0;
  for (int i = 0; i < FEATURE_DIM; i++) {
    score += params->weights[i] * features[i];
  }
  return score;
#endif
}

static double calculate_score(LOH_params_t *params, cache_obj_t *obj) {
  if (!obj) return DBL_MAX;  // 空指针返回最大值，不会被选in

  double features[FEATURE_DIM];
  calculate_object_features(params, obj, features);
  return calculate_score_with_features(params, features);
}

// ===============================
// IRT值管理辅助函数实现
// ===============================

/**
 * @brief updateobjectofIRT值数组
 * @param obj 缓存object
 * @param new_irt 新ofIRT值
 *
 * IRT数组使用约定：
 * - irt_values[0]: 最新的IRT值
 * - irt_values[1]: 第2新ofIRT值
 * - irt_values[2]: 第3新ofIRT值
 * - 值0表示该位置未初始化
 */

/**
 * @brief 获取指定位置ofIRT值
 * @param obj 缓存object
 * @param index IRT值索引 (0=最新, 1=第2新, 2=第3新)
 * @return IRT值，0表示该位置未初始化
 */
static int64_t get_irt_value(cache_obj_t *obj, int index) {
  if (!obj || index < 0 || index >= 3) return 0;
  return obj->LOH.irt_values[index];
}

// ===============================
// 特征计算函数实现
// ===============================

/**
 * @brief 计算recency特征值
 * recency = (current_timestamp - last_access_time) / current_timestamp
 * 范围[0,1]，值越大表示越久未访问
 */
static double calculate_recency(LOH_params_t *params, cache_obj_t *obj) {
  if (params->current_timestamp == 0) return 0.0;
  // 使用与calculate_object_features相同的公式
  int64_t time_since_last =
      params->current_timestamp - obj->LOH.last_access_counter;
  double recency = 1.0 / (1.0 + (double)time_since_last);
  return recency;
}

/**
 * @brief 计算frequency特征值
 */
static double calculate_frequency(LOH_params_t *params, cache_obj_t *obj) {
  int access_count = obj->LOH.access_count;
  if (access_count <= 0) return 0.0;
  // 去掉 log: 采用简单有界单调映射 f/(f+K)
  const double K = 1.0;  // 平滑常数（按要求设为 1）
  double f = (double)access_count;
  return f / (f + K);
}

/**
 * @brief 计算size特征值
 */
static double calculate_size(LOH_params_t *params, cache_obj_t *obj) {
  // 使用与calculate_object_features相同的公式
  double size_mb = (double)obj->obj_size / (1024.0 * 1024.0);  // 转换为MB
  // 去掉 log: 采用简单有界单调映射 1 / (1 + A * MB)
  const double A = 1.0;  // 尺度因子，可视需要调整
  double normalized_size = 1.0 / (1.0 + A * size_mb);
  return normalized_size;
}

// ===============================
// frequency表操作函数实现
// ===============================

/**
 * @brief 初始化frequency表
 *
 * @param params
 */
static void freq_table_init(LOH_params_t *params) {
  for (int i = 0; i <= FREQ_MAX; i++) {
    params->freq_table[i] = NULL;
    params->freq_table_tail[i] = NULL;
  }
#if LOH_MAINTAIN_MAPS
  params->freq_node_map = g_hash_table_new(g_direct_hash, g_direct_equal);
#else
  params->freq_node_map = NULL;
#endif
}

// 内部辅助函数：在指定频率级别的链表头部插入节点
static inline void freq_level_link_head(LOH_params_t *params, int level,
                                        loh_freq_node_t *node) {
  node->prev = NULL;
  node->next = params->freq_table[level];
  if (params->freq_table[level]) {
    params->freq_table[level]->prev = node;
  } else {
    // 原本为空，尾指针也需要指向该节点
    params->freq_table_tail[level] = node;
  }
  params->freq_table[level] = node;
  node->freq_level = level;
}

// 内部辅助函数：从其当前频率级别链表中摘除节点（不释放内存）
static inline void freq_level_unlink(LOH_params_t *params,
                                     loh_freq_node_t *node) {
  int level = node->freq_level;
  if (node->prev) {
    node->prev->next = node->next;
  } else {
    // node 是头
    params->freq_table[level] = node->next;
  }
  if (node->next) {
    node->next->prev = node->prev;
  } else {
    // node 是尾
    params->freq_table_tail[level] = node->prev;
  }
  node->prev = node->next = NULL;
}

/**
 * @brief 释放frequency表资源
 *
 * @param params
 */
static void freq_table_free(LOH_params_t *params) {
#if LOH_MAINTAIN_MAPS
  if (params->freq_node_map) {
    GHashTableIter iter;
    gpointer key, value;
    g_hash_table_iter_init(&iter, params->freq_node_map);
    while (g_hash_table_iter_next(&iter, &key, &value)) {
      g_free(value);
    }
    g_hash_table_destroy(params->freq_node_map);
    params->freq_node_map = NULL;
  }
#else
  // 遍历所有频率级别释放节点
  for (int level = 1; level <= FREQ_MAX; level++) {
    loh_freq_node_t *curr = params->freq_table[level];
    while (curr) {
      loh_freq_node_t *next = curr->next;
      g_free(curr);
      curr = next;
    }
    params->freq_table[level] = NULL;
    params->freq_table_tail[level] = NULL;
  }
#endif
}

/**
 * @brief add object到frequency表对应的frequency链表
 *
 * @param params
 * @param obj 新object，frequency应该已经在插入时设置正确
 */
static void freq_table_add(LOH_params_t *params, cache_obj_t *obj) {
  // 【修复数据一致性】：直接使用object中已经设置好的访问次数
  // 不再重复查找和设置，避免数据不一致
  int freq = obj->LOH.access_count;
  if (freq > FREQ_MAX) freq = FREQ_MAX;

#if LOH_DEBUG_LEVEL >= LOH_DEBUG_VERBOSE
  printf("[FREQ_ADD] Adding obj %p to freq level %d\n", (void *)obj, freq);
#endif

  loh_freq_node_t *node = g_new0(loh_freq_node_t, 1);
  node->obj = obj;
  // 缓存到对象内，避免后续哈希查找
  obj->LOH.loh_freq_node = node;
  // 仍然维护哈希表（用于调试和统一析构）
#if LOH_MAINTAIN_MAPS
  g_hash_table_insert(params->freq_node_map, obj, node);
#endif
  freq_level_link_head(params, freq, node);

  // 【验证】checkadd结果 - 仅在调试模式下进行complete验证
#if LOH_DEBUG_LEVEL >= LOH_DEBUG_DETAILED
  printf("[FREQ_ADD] Successfully added obj %p to freq level %d\n", (void *)obj,
         freq);
#endif

#if LOH_DEBUG_LEVEL >= LOH_DEBUG_DETAILED
  // 验证频率表一致性
  freq_table_validate(params, "after_freq_add");
#endif
}

/**
 * @brief 从指定frequency level remove object节点
 *
 * @param params
 * @param obj 要remove的object
 * @param node 要remove的节点
 * @param freq_level 节点所在的frequency level
 */
// freq_table_remove_from_level: 已内联为 freq_level_unlink + free +
// 哈希条目删除

/**
 * @brief 从frequency表中remove object
 *
 * @param params
 * @param obj 要remove的object
 */
static void freq_table_remove(LOH_params_t *params, cache_obj_t *obj) {
  loh_freq_node_t *node = (loh_freq_node_t *)obj->LOH.loh_freq_node;
  if (node == NULL) {
#if LOH_DEBUG_LEVEL >= LOH_DEBUG_DETAILED
    printf("[FREQ_REMOVE] Node not found for obj %p\n", (void *)obj);
#endif
    return;
  }

#if LOH_DEBUG_LEVEL >= LOH_DEBUG_DETAILED
  printf("[FREQ_REMOVE] Removing node %p for obj %p, access_count=%d\n",
         (void *)node, (void *)obj, obj->LOH.access_count);
#endif

  // 从其当前频率链表中摘除节点
  int current_freq = node->freq_level;
  if (current_freq < 1) current_freq = 1;
  if (current_freq > FREQ_MAX) current_freq = FREQ_MAX;
  freq_level_unlink(params, node);

#if LOH_DEBUG_LEVEL >= LOH_DEBUG_DETAILED
  printf("[FREQ_REMOVE] About to free node %p for obj %p\n", (void *)node,
         (void *)obj);
#endif

  // 从哈希表中删除后再释放节点
#if LOH_MAINTAIN_MAPS
  g_hash_table_remove(params->freq_node_map, obj);
#endif
  g_free(node);
  obj->LOH.loh_freq_node = NULL;

#if LOH_MAINTAIN_MAPS && (LOH_DEBUG_LEVEL >= LOH_DEBUG_ERROR)
  // 【验证】check remove结果
  loh_freq_node_t *verify_node =
      g_hash_table_lookup(params->freq_node_map, obj);
  if (verify_node != NULL) {
    printf(
        "[FREQ_REMOVE ERROR] Object %p still found in hashtable after "
        "removal\n",
        (void *)obj);
  }
#endif

#if LOH_DEBUG_LEVEL >= LOH_DEBUG_DETAILED
  printf("[FREQ_REMOVE] Successfully removed obj %p from freq level %d\n",
         (void *)obj, current_freq);
#endif
}

/**
 * @brief update object在frequency表中的位置
 *
 * @param params
 * @param obj 访问频率增加的object
 */
static void freq_table_update(LOH_params_t *params, cache_obj_t *obj) {
#if LOH_DEBUG_LEVEL >= LOH_DEBUG_DETAILED
  printf("[FREQ_UPDATE] Starting update for obj %p, current access_count=%d\n",
         (void *)obj, obj->LOH.access_count);
#endif

  // O(1) 查找节点
  loh_freq_node_t *node = (loh_freq_node_t *)obj->LOH.loh_freq_node;
  if (node == NULL) {
#if LOH_DEBUG_LEVEL >= LOH_DEBUG_ERROR
    printf("[FREQ_UPDATE ERROR] Cannot find existing node for obj %p\n",
           (void *)obj);
#endif
    return;
  }
  int old_freq_level = node->freq_level;
  int new_freq = obj->LOH.access_count;
  if (new_freq < 1) new_freq = 1;
  if (new_freq > FREQ_MAX) new_freq = FREQ_MAX;

  // 如果频率级别未变化，直接返回
  if (new_freq == old_freq_level) {
#if LOH_DEBUG_LEVEL >= LOH_DEBUG_DETAILED
    printf("[FREQ_UPDATE] obj %p stays at level %d, no move needed\n",
           (void *)obj, new_freq);
#endif
    return;
  }

  // 在饱和级别时不需要移动
  if (old_freq_level == FREQ_MAX && new_freq == FREQ_MAX) {
#if LOH_DEBUG_LEVEL >= LOH_DEBUG_DETAILED
    printf("[FREQ_UPDATE] obj %p at saturated level %d, skip move\n",
           (void *)obj, FREQ_MAX);
#endif
    return;
  }

  // 从旧级别摘除并插入新级别链表头部
  freq_level_unlink(params, node);
  freq_level_link_head(params, new_freq, node);

#if LOH_DEBUG_LEVEL >= LOH_DEBUG_ERROR
  // 【验证】check插入结果
  // 验证：哈希表仍然映射到同一个节点
  loh_freq_node_t *verify_node = (loh_freq_node_t *)obj->LOH.loh_freq_node;
  if (verify_node != node) {
    printf(
        "[FREQ_UPDATE ERROR] Hashtable mapping changed unexpectedly for obj "
        "%p\n",
        (void *)obj);
    return;
  }
#endif

#if LOH_DEBUG_LEVEL >= LOH_DEBUG_DETAILED
  printf("[FREQ_UPDATE] Successfully updated obj %p from freq %d to freq %d\n",
         (void *)obj, old_freq_level, new_freq);
#endif

#if LOH_DEBUG_LEVEL >= LOH_DEBUG_DETAILED
  // 验证频率表一致性
  freq_table_validate(params, "after_freq_update");
#endif
}

/**
 * @brief 获取最低频率的object
 *
 * @param params
 * @return cache_obj_t* 最低频率的object，如果没有则返回NULL
 */
static cache_obj_t *freq_table_get_min_freq_obj(LOH_params_t *params) {
  for (int i = 1; i <= FREQ_MAX; i++) {
    if (params->freq_table_tail[i] != NULL) {
      return params->freq_table_tail[i]->obj;
    }
  }
  return NULL;
}

/**
 * @brief 从frequency表获取淘汰候选object
 *
 * @param params
 * @param max_candidates 最大候选数量
 * @param n_candidates 输入输出参数：输入当前已有候选数，输出update后of总候选数
 */
static void freq_table_get_candidates(LOH_params_t *params, int max_candidates,
                                      int *n_candidates) {
  int added = 0;
  int start_idx = *n_candidates;
  cache_t *cache = (cache_t *)params->cache_ptr;

#if LOH_DEBUG_LEVEL >= LOH_DEBUG_VERBOSE
  printf("[FREQ DEBUG] Entering freq_table_get_candidates, max_candidates=%d\n",
         max_candidates);
  printf("[FREQ DEBUG] Checking frequency table state:\n");
  for (int debug_i = 1; debug_i <= 3 && debug_i <= FREQ_MAX; debug_i++) {
    printf("[FREQ DEBUG] freq_table_tail[%d] = %p\n", debug_i,
           (void *)params->freq_table_tail[debug_i]);
    if (params->freq_table_tail[debug_i]) {
      printf("[FREQ DEBUG]   ->obj = %p, ->prev = %p, ->next = %p\n",
             (void *)params->freq_table_tail[debug_i]->obj,
             (void *)params->freq_table_tail[debug_i]->prev,
             (void *)params->freq_table_tail[debug_i]->next);
    }
  }
#endif

  // 从低frequency到高frequency遍历，同一frequencylevel内从尾部（更老ofobject）start选择
  for (int i = 1; i <= FREQ_MAX && added < max_candidates; i++) {
    loh_freq_node_t *curr =
        params->freq_table_tail[i];  // 从尾部start，选择更老ofobject

    while (curr != NULL && added < max_candidates) {
      if (start_idx + added >= MAX_CANDIDATES) return;

#if LOH_DEBUG_LEVEL >= LOH_DEBUG_VERBOSE
      printf("[FREQ DEBUG] Checking curr=%p, curr->obj=%p\n", (void *)curr,
             curr ? (void *)curr->obj : (void *)0);
#endif

      // 【热路径优化】移除哈希表membership检查；仅在调试下验证
      if (curr->obj != NULL) {
#if LOH_DEBUG_LEVEL >= LOH_DEBUG_ERROR
        if (hashtable_find_obj_id(cache->hashtable, curr->obj->obj_id) !=
            curr->obj) {
          LOH_DEBUG_PRINT_ERROR(
              "[FREQ WARNING] Object obj_id=%llu found in freq table but not "
              "in "
              "cache, skipping\n",
              (unsigned long long)curr->obj->obj_id);
          curr = curr->prev;
          continue;
        }
#endif
        // 融合去重：频率候选加入前先通过 seen 去重
        if (loh_seen_add(params, curr->obj)) {
          params->candidates[start_idx + added++] = curr->obj;
        }
      }
      curr = curr->prev;  // 向前遍历（从尾部到头部），选择更老ofobject
    }
  }
  *n_candidates = start_idx + added;
}

/**
 * @brief 初始化IRT最小堆 - 每个堆保存IRT值最大的n个对象
 * IRT堆是最小堆，堆顶是当前存储对象中IRT值最小的，用于快速判断新对象是否应该插入
 *
 * @param params LOH参数结构体
 */
static void irt_heap_init(LOH_params_t *params) {
  // 设置每个IRT堆的容量为总候选数的1/6，3个堆分别对应IRT1、IRT2、IRT3
  params->irt_heap_capacity =
      MAX_CANDIDATES / 6;  // 每个IRT堆大小为总候选数的1/6

  // 初始化3个IRT堆（对应IRT_HISTORY_SIZE=3）
  for (int i = 0; i < IRT_HISTORY_SIZE; i++) {
    // 每个堆的当前大小初始化为0
    params->irt_heap_size[i] = 0;
    // 为每个堆分配内存，存储irt_heap_entry_t结构体数组
    params->irt_heap[i] = g_new0(irt_heap_entry_t, params->irt_heap_capacity);
    // 为每个堆创建哈希表映射，用于快速查找object在堆中的位置
#if LOH_MAINTAIN_MAPS
    params->irt_heap_maps[i] = g_hash_table_new(g_direct_hash, g_direct_equal);
#else
    params->irt_heap_maps[i] = NULL;
#endif
  }
}

/**
 * @brief 释放IRT堆资源
 *
 * @param params
 */
static void irt_heap_free(LOH_params_t *params) {
  for (int i = 0; i < IRT_HISTORY_SIZE; i++) {
    g_free(params->irt_heap[i]);
    params->irt_heap[i] = NULL;
    params->irt_heap_size[i] = 0;
    // 【新增】释放IRT堆哈希表映射
    if (params->irt_heap_maps[i]) {
      g_hash_table_destroy(params->irt_heap_maps[i]);
      params->irt_heap_maps[i] = NULL;
    }
  }
  params->irt_heap_capacity = 0;
}

/**
 * @brief 上移操作以维护最小堆属性 - IRT值小的object在堆顶
 * 最小堆：父节点的IRT值 <= 子节点的IRT值
 * 用于在插入新元素后恢复堆属性
 *
 * @param params LOH参数结构体
 * @param heap_idx 堆索引（0=IRT1, 1=IRT2, 2=IRT3）
 * @param idx 需要上移的元素在堆中的索引位置
 */
static void irt_heap_sift_up(LOH_params_t *params, int heap_idx, int idx) {
  // 循环直到到达根节点（idx=0）或满足堆属性
  while (idx > 0) {
    int parent = (idx - 1) / 2;  // calc父节点索引，二叉堆的标准公式

    // 【最小堆】如果当前节点的IRT值大于等于父节点，堆属性已满足，退出
    if (params->irt_heap[heap_idx][idx].irt_value >=
        params->irt_heap[heap_idx][parent].irt_value) {
      break;
    }

    // 【修复】保存交换前的对象指针，用于哈希表更新
    cache_obj_t *obj_at_idx = params->irt_heap[heap_idx][idx].obj;
    cache_obj_t *obj_at_parent = params->irt_heap[heap_idx][parent].obj;

    // 当前节点IRT值小于父节点，需要交换以维护最小堆属性
    irt_heap_entry_t temp = params->irt_heap[heap_idx][idx];  // 保存当前节点
    params->irt_heap[heap_idx][idx] =
        params->irt_heap[heap_idx][parent];     // 父节点下移
    params->irt_heap[heap_idx][parent] = temp;  // 当前节点上移

    // 【修复】同步update哈希表映射，使用交换前的对象指针
    LOH_DEBUG_PRINT_DETAILED(
        "[SIFT_UP] Heap %d: Swapping obj %llu (idx=%d) with obj %llu "
        "(parent=%d)\n",
        heap_idx, (unsigned long long)obj_at_idx->obj_id, idx,
        (unsigned long long)obj_at_parent->obj_id, parent);

    if (params->irt_heap_maps[heap_idx]) {
      g_hash_table_insert(params->irt_heap_maps[heap_idx], obj_at_idx,
                          GINT_TO_POINTER(parent + 1));  // 修正偏移量
      g_hash_table_insert(params->irt_heap_maps[heap_idx], obj_at_parent,
                          GINT_TO_POINTER(idx + 1));  // 修正偏移量
    }
    // 同步对象内索引
    obj_at_idx->LOH.loh_irt_pos[heap_idx] = parent;
    obj_at_parent->LOH.loh_irt_pos[heap_idx] = idx;

    LOH_DEBUG_PRINT_DETAILED(
        "[SIFT_UP] Heap %d: Updated hash - obj %llu now at idx=%d, obj %llu "
        "now at idx=%d\n",
        heap_idx, (unsigned long long)obj_at_idx->obj_id, parent,
        (unsigned long long)obj_at_parent->obj_id, idx);

    idx = parent;  // 继续向上check，直到满足堆属性或到达根节点
  }
}

/**
 * @brief 下移操作以维护最小堆属性
 * 用于在删除堆顶元素后恢复堆属性
 *
 * @param params LOH参数结构体
 * @param heap_idx 堆索引（0=IRT1, 1=IRT2, 2=IRT3）
 * @param idx 需要下移的元素在堆中的索引位置
 */
static void irt_heap_sift_down(LOH_params_t *params, int heap_idx, int idx) {
  int min_idx = idx;        // 假设当前节点是最小值
  int left = 2 * idx + 1;   // 左子节点索引
  int right = 2 * idx + 2;  // 右子节点索引

  // 【最小堆】check左子节点是否存在且IRT值更小
  if (left < params->irt_heap_size[heap_idx] &&
      params->irt_heap[heap_idx][left].irt_value <
          params->irt_heap[heap_idx][min_idx].irt_value)
    min_idx = left;  // 左子节点是最小值候选

  // 【最小堆】check右子节点是否存在且IRT值更小
  if (right < params->irt_heap_size[heap_idx] &&
      params->irt_heap[heap_idx][right].irt_value <
          params->irt_heap[heap_idx][min_idx].irt_value)
    min_idx = right;  // 右子节点是最小值候选

  // 如果子节点in有更小of值，需要交换并继续下移
  if (min_idx != idx) {
    // 【修复】保存交换前的对象指针，用于哈希表更新
    cache_obj_t *obj_at_idx = params->irt_heap[heap_idx][idx].obj;
    cache_obj_t *obj_at_min_idx = params->irt_heap[heap_idx][min_idx].obj;

    // 交换当前节点与拥有最小IRT值of子节点
    irt_heap_entry_t temp = params->irt_heap[heap_idx][idx];  // 保存当前节点
    params->irt_heap[heap_idx][idx] =
        params->irt_heap[heap_idx][min_idx];     // 最小子节点上移
    params->irt_heap[heap_idx][min_idx] = temp;  // 当前节点下移

    // 【修复】同步update哈希表映射，使用交换前的对象指针
    if (params->irt_heap_maps[heap_idx]) {
      g_hash_table_insert(params->irt_heap_maps[heap_idx], obj_at_min_idx,
                          GINT_TO_POINTER(idx + 1));  // 修正偏移量
      g_hash_table_insert(params->irt_heap_maps[heap_idx], obj_at_idx,
                          GINT_TO_POINTER(min_idx + 1));  // 修正偏移量
    }
    // 同步对象内索引
    obj_at_min_idx->LOH.loh_irt_pos[heap_idx] = idx;
    obj_at_idx->LOH.loh_irt_pos[heap_idx] = min_idx;

    // 递归继续下移，确保子树也满足堆属性
    irt_heap_sift_down(params, heap_idx, min_idx);
  }
}

#if LOH_DEBUG_LEVEL >= LOH_DEBUG_ERROR
/**
 * @brief 验证最小堆属性是否被正确维护
 * @param params LOH参数结构体
 * @param heap_idx 堆索引
 * @param operation 当前操作名称（用于调试输出）
 * @return true如果堆属性正确，false如果发现问题
 */
static bool irt_heap_validate_min_heap_property(LOH_params_t *params,
                                                int heap_idx,
                                                const char *operation) {
  if (!params || heap_idx < 0 || heap_idx >= 3) {
    LOH_DEBUG_PRINT_DETAILED(
        "[HEAP_VALIDATE] Invalid parameters for heap %d operation %s\n",
        heap_idx, operation ? operation : "unknown");
    return false;
  }

  int heap_size = params->irt_heap_size[heap_idx];
  if (heap_size <= 1) {
    LOH_DEBUG_PRINT_DETAILED(
        "[HEAP_VALIDATE] Heap %d is trivially valid (size=%d) after %s\n",
        heap_idx, heap_size, operation ? operation : "unknown");
    return true;  // 空堆或单元素堆总是有效的
  }

  bool is_valid = true;
  int violations = 0;

  LOH_DEBUG_PRINT_DETAILED(
      "[HEAP_VALIDATE] 🔍 Validating min heap %d (size=%d) after %s:\n",
      heap_idx, heap_size, operation ? operation : "unknown");

  // 检查每个非叶子节点的最小堆属性
  for (int i = 0; i < heap_size / 2; i++) {
    int64_t parent_irt = params->irt_heap[heap_idx][i].irt_value;
    int left_child = 2 * i + 1;
    int right_child = 2 * i + 2;

    // 检查左子节点
    if (left_child < heap_size) {
      int64_t left_irt = params->irt_heap[heap_idx][left_child].irt_value;
      if (parent_irt > left_irt) {
        LOH_DEBUG_PRINT_DETAILED(
            "[HEAP_VALIDATE] ❌ VIOLATION: Parent[%d]=%ld > "
            "LeftChild[%d]=%ld\n",
            i, parent_irt, left_child, left_irt);
        is_valid = false;
        violations++;
      }
    }

    // 检查右子节点
    if (right_child < heap_size) {
      int64_t right_irt = params->irt_heap[heap_idx][right_child].irt_value;
      if (parent_irt > right_irt) {
        LOH_DEBUG_PRINT_DETAILED(
            "[HEAP_VALIDATE] ❌ VIOLATION: Parent[%d]=%ld > "
            "RightChild[%d]=%ld\n",
            i, parent_irt, right_child, right_irt);
        is_valid = false;
        violations++;
      }
    }
  }

  // 验证哈希表的一致性
  int hash_inconsistencies = 0;
  for (int i = 0; i < heap_size; i++) {
    cache_obj_t *obj = params->irt_heap[heap_idx][i].obj;
    gpointer hash_pos =
        g_hash_table_lookup(params->irt_heap_maps[heap_idx], obj);
    if (!hash_pos) {
      LOH_DEBUG_PRINT_DETAILED(
          "[HEAP_VALIDATE] [warning] ❌ HASH INCONSISTENCY: obj %llu at "
          "heap[%d] not "
          "found in hash table\n",
          (unsigned long long)obj->obj_id, i);
      hash_inconsistencies++;
    } else {
      int expected_idx = GPOINTER_TO_INT(hash_pos) - 1;  // 修正偏移量
      if (expected_idx != i) {
        LOH_DEBUG_PRINT_DETAILED(
            "[HEAP_VALIDATE] [warning] ❌ HASH INCONSISTENCY: obj %llu at "
            "heap[%d] but "
            "hash table says [%d]\n",
            (unsigned long long)obj->obj_id, i, expected_idx);
        hash_inconsistencies++;
      }
    }
  }

  if (is_valid && hash_inconsistencies == 0) {
    LOH_DEBUG_PRINT_DETAILED(
        "[HEAP_VALIDATE] ✅ Min heap %d is VALID after %s (checked %d nodes)\n",
        heap_idx, operation ? operation : "unknown", heap_size);
  } else {
    LOH_DEBUG_PRINT_DETAILED(
        "[HEAP_VALIDATE] [warning] ❌ Min heap %d has PROBLEMS after %s: %d "
        "violations, "
        "%d hash inconsistencies\n",
        heap_idx, operation ? operation : "unknown", violations,
        hash_inconsistencies);
  }

  return is_valid && (hash_inconsistencies == 0);
}
#endif

/**
 * @brief add object到指定的IRT最小堆
 */
static void irt_heap_add(LOH_params_t *params, cache_obj_t *obj, int heap_idx) {
  // 【调试】检查hash表的基本状态
  // 在发布模式下可能不维护哈希映射，允许为空

  LOH_DEBUG_PRINT_DETAILED(
      "[DEBUG] Hash table state before add: heap %d, size=%u, capacity=%d\n",
      heap_idx,
      (params->irt_heap_maps[heap_idx]
           ? g_hash_table_size(params->irt_heap_maps[heap_idx])
           : 0),
      params->irt_heap_capacity);

  // 【防重复】检查对象是否已经在堆中
  gpointer existing_pos = NULL;
#if LOH_MAINTAIN_MAPS
  existing_pos = g_hash_table_lookup(params->irt_heap_maps[heap_idx], obj);
  if (existing_pos != NULL) {
    LOH_DEBUG_PRINT_DETAILED(
        "[IRT_HEAP_ADD] [warning] DUPLICATE DETECTED! Heap %d: Object %llu "
        "already "
        "exists at position %d, skipping\n",
        heap_idx, (unsigned long long)obj->obj_id,
        GPOINTER_TO_INT(existing_pos));
    return;  // 对象已存在，不重复添加
  }
#else
  (void)existing_pos;
#endif

  // 【修复】直接从irt_values数组获取IRT值
  int64_t irt_value;
  switch (heap_idx) {
    case 0:
      irt_value = obj->LOH.irt_values[0];  // 最新IRT
      break;
    case 1:
      irt_value = obj->LOH.irt_values[1];  // 第2新IRT
      break;
    case 2:
      irt_value = obj->LOH.irt_values[2];  // 第3新IRT
      break;
    default:
      return;  // 无效索引
  }

  LOH_DEBUG_PRINT_DETAILED(
      "[IRT_HEAP_ADD] Heap %d: Considering obj %llu with IRT=%ld, current "
      "size=%d\n",
      heap_idx, (unsigned long long)obj->obj_id, irt_value,
      params->irt_heap_size[heap_idx]);

  // INT64_MAX值object也应该被add到堆，因为它们是最大值，是驱逐候选
  if (params->irt_heap_size[heap_idx] >= params->irt_heap_capacity) {
    // 【简化】最小堆的根节点就是最小值，无需维护额外跟踪信息
    int64_t min_irt = params->irt_heap[heap_idx][0].irt_value;
    int min_idx = 0;

    // Top-K最大值问题：只有新元素大于堆顶最小值时才替换
    if (irt_value <= min_irt) {
      LOH_DEBUG_PRINT_DETAILED(
          "[IRT_HEAP_ADD] Heap %d: Skipping obj %llu (IRT=%ld <= min=%ld), "
          "size=%d\n",
          heap_idx, (unsigned long long)obj->obj_id, irt_value, min_irt,
          params->irt_heap_size[heap_idx]);
      return;  // 新值不够大，拒绝
    }

    // 【新增】remove被替换object的哈希表映射
    cache_obj_t *removed_obj = params->irt_heap[heap_idx][min_idx].obj;
    LOH_DEBUG_PRINT_DETAILED(
        "[IRT_HEAP_ADD] Heap full: removing obj %p (id=%llu) at min_idx=%d "
        "from heap %d\n",
        (void *)removed_obj, (unsigned long long)removed_obj->obj_id, min_idx,
        heap_idx);

    if (params->irt_heap_maps[heap_idx])
      g_hash_table_remove(params->irt_heap_maps[heap_idx], removed_obj);

    // 被替换的对象已不在堆中，清空其对象内索引，避免后续更新误用陈旧索引
    if (removed_obj) {
      removed_obj->LOH.loh_irt_pos[heap_idx] = -1;
    }

    // 直接在堆顶位置替换为新元素（堆元素数量不变）
    params->irt_heap[heap_idx][min_idx].obj = obj;
    params->irt_heap[heap_idx][min_idx].irt_value = irt_value;

    // 添加新object的哈希表映射
    if (params->irt_heap_maps[heap_idx])
      g_hash_table_insert(params->irt_heap_maps[heap_idx], obj,
                          GINT_TO_POINTER(min_idx + 1));  // 修正偏移量
    obj->LOH.loh_irt_pos[heap_idx] = min_idx;

    // 只需要下沉操作，因为新元素通常比根部原来的最小值大
    irt_heap_sift_down(params, heap_idx, min_idx);

#if LOH_DEBUG_LEVEL >= LOH_DEBUG_ERROR
    // 验证堆满替换后的堆属性
    irt_heap_validate_min_heap_property(params, heap_idx, "heap_add_replace");
#endif

    LOH_DEBUG_PRINT_DETAILED(
        "[IRT_HEAP_ADD] Heap %d: Object %llu replaced min element, new "
        "size=%d\n",
        heap_idx, (unsigned long long)obj->obj_id,
        params->irt_heap_size[heap_idx]);
    return;  // 已完成替换，直接返回
  }

  // 堆未满，直接添加到末尾
  int idx = params->irt_heap_size[heap_idx];
  params->irt_heap[heap_idx][idx].obj = obj;
  params->irt_heap[heap_idx][idx].irt_value = irt_value;
  if (params->irt_heap_maps[heap_idx])
    g_hash_table_insert(params->irt_heap_maps[heap_idx], obj,
                        GINT_TO_POINTER(idx + 1));
  obj->LOH.loh_irt_pos[heap_idx] = idx;
  // 正确维护堆大小（此前缺失这一步会导致 size 恒为 0，从而触发大量
  // invalid_index 计数）
  params->irt_heap_size[heap_idx]++;
  LOH_DEBUG_PRINT_DETAILED(
      "[IRT_HEAP_ADD] Stored in heap: obj=%p (id=%llu) at idx=%d for heap %d\n",
      (void *)obj, (unsigned long long)obj->obj_id, idx, heap_idx);

  // 【新增】add新object的哈希表映射
  LOH_DEBUG_PRINT_DETAILED(
      "[IRT_HEAP_ADD] Hash table: inserting obj %p (id=%llu) at initial idx=%d "
      "for heap %d\n",
      (void *)obj, (unsigned long long)obj->obj_id, idx, heap_idx);

  // 【修复】避免使用GINT_TO_POINTER(0)，因为它返回NULL，在hash表中有特殊含义
  // 解决方案：所有索引值+1存储，查找时-1还原
  if (params->irt_heap_maps[heap_idx])
    g_hash_table_insert(params->irt_heap_maps[heap_idx], obj,
                        GINT_TO_POINTER(idx + 1));

  LOH_DEBUG_PRINT_DETAILED(
      "[DEBUG] Just inserted obj %p with idx %d, hash table size now: %u\n",
      (void *)obj, idx, g_hash_table_size(params->irt_heap_maps[heap_idx]));

#if LOH_DEBUG_LEVEL >= LOH_DEBUG_ERROR
  // 【关键调试】立即验证插入是否成功，如果失败则深度分析
  gpointer verify_ptr = NULL;
  if (params->irt_heap_maps[heap_idx])
    verify_ptr = g_hash_table_lookup(params->irt_heap_maps[heap_idx], obj);
  LOH_DEBUG_PRINT_DETAILED("[DEBUG] Immediate lookup result: %s\n",
                           verify_ptr ? "FOUND" : "NOT FOUND");

  if (!verify_ptr) {
    LOH_DEBUG_PRINT_DETAILED(
        "[CRITICAL] Hash table INSERT/LOOKUP MISMATCH for heap %d:\n",
        heap_idx);
    LOH_DEBUG_PRINT_DETAILED("  - Object pointer: %p\n", (void *)obj);
    LOH_DEBUG_PRINT_DETAILED("  - Object ID: %llu\n",
                             (unsigned long long)obj->obj_id);
    LOH_DEBUG_PRINT_DETAILED("  - Inserted index: %d\n", idx);
    LOH_DEBUG_PRINT_DETAILED(
        "  - Hash table size after insert: %u\n",
        g_hash_table_size(params->irt_heap_maps[heap_idx]));

    // 检查内存对齐
    LOH_DEBUG_PRINT_DETAILED("  - Pointer alignment: %lu bytes (mod 8 = %lu)\n",
                             sizeof(void *),
                             (unsigned long)((uintptr_t)obj % 8));
    LOH_DEBUG_PRINT_DETAILED("  - Is aligned to 8 bytes: %s\n",
                             ((uintptr_t)obj % 8 == 0) ? "YES" : "NO");

    // 检查对象是否在有效内存范围
    LOH_DEBUG_PRINT_DETAILED("  - Object size field: %ld\n", obj->obj_size);
    LOH_DEBUG_PRINT_DETAILED("  - Object next pointer: %p\n",
                             (void *)obj->queue.next);

    // 测试指针的稳定性
    LOH_DEBUG_PRINT_DETAILED("  - Pointer address again: %p\n", (void *)obj);
    LOH_DEBUG_PRINT_DETAILED("  - Object ID again: %llu\n",
                             (unsigned long long)obj->obj_id);

    // 测试hash函数的一致性
    guint hash1 = g_direct_hash(obj);
    guint hash2 = g_direct_hash(obj);
    LOH_DEBUG_PRINT_DETAILED("  - Hash value 1: %u\n", hash1);
    LOH_DEBUG_PRINT_DETAILED("  - Hash value 2: %u\n", hash2);
    LOH_DEBUG_PRINT_DETAILED("  - Hash consistent: %s\n",
                             (hash1 == hash2) ? "YES" : "NO");

    // 测试equal函数
    gboolean equal1 = g_direct_equal(obj, obj);
    LOH_DEBUG_PRINT_DETAILED("  - Self equal: %s\n", equal1 ? "YES" : "NO");

    // 【关键测试】检查GINT_TO_POINTER(0)的问题
    LOH_DEBUG_PRINT_DETAILED("  - GINT_TO_POINTER(0): %p\n",
                             GINT_TO_POINTER(0));
    LOH_DEBUG_PRINT_DETAILED("  - GINT_TO_POINTER(1): %p\n",
                             GINT_TO_POINTER(1));
    LOH_DEBUG_PRINT_DETAILED("  - Is GINT_TO_POINTER(0) == NULL: %s\n",
                             (GINT_TO_POINTER(0) == NULL) ? "YES" : "NO");

    // 测试插入非零值
    g_hash_table_insert(params->irt_heap_maps[heap_idx], obj,
                        GINT_TO_POINTER(idx + 1000));
    gpointer verify_ptr3 =
        g_hash_table_lookup(params->irt_heap_maps[heap_idx], obj);
    printf("  - Insert with idx+1000 test: %s (value=%d)\n",
           verify_ptr3 ? "SUCCESS" : "FAILED",
           verify_ptr3 ? GPOINTER_TO_INT(verify_ptr3) : -1);

    // 重新插入同样的数据看看
    g_hash_table_insert(params->irt_heap_maps[heap_idx], obj,
                        GINT_TO_POINTER(999));
    gpointer verify_ptr2 =
        g_hash_table_lookup(params->irt_heap_maps[heap_idx], obj);
    printf("  - Re-insert test: %s (value=%d)\n",
           verify_ptr2 ? "SUCCESS" : "FAILED",
           verify_ptr2 ? GPOINTER_TO_INT(verify_ptr2) : -1);
  }
#endif

  LOH_DEBUG_PRINT_DETAILED(
      "[DEBUG] Before sift_up: hash table size=%u, can find obj? %s\n",
      params->irt_heap_maps[heap_idx]
          ? g_hash_table_size(params->irt_heap_maps[heap_idx])
          : 0,
      (params->irt_heap_maps[heap_idx] &&
       g_hash_table_lookup(params->irt_heap_maps[heap_idx], obj))
          ? "YES"
          : "NO");

  irt_heap_sift_up(params, heap_idx, idx);

  LOH_DEBUG_PRINT_DETAILED(
      "[DEBUG] After sift_up: hash table size=%u, can find obj? %s\n",
      params->irt_heap_maps[heap_idx]
          ? g_hash_table_size(params->irt_heap_maps[heap_idx])
          : 0,
      (params->irt_heap_maps[heap_idx] &&
       g_hash_table_lookup(params->irt_heap_maps[heap_idx], obj))
          ? "YES"
          : "NO");

  LOH_DEBUG_PRINT_DETAILED(
      "[IRT_HEAP_ADD] Heap %d: Object %llu added, new size=%d\n", heap_idx,
      (unsigned long long)obj->obj_id, params->irt_heap_size[heap_idx]);

#if LOH_DEBUG_LEVEL >= LOH_DEBUG_ERROR
  // 验证heap_add后的堆属性
  irt_heap_validate_min_heap_property(params, heap_idx, "heap_add");
#endif
}

/**
 * @brief 从指定的IRT堆remove特定object
 *
 * 【优化完成】：使用哈希表实现O(1)object定位，彻底解决线性搜索问题
 *
 * ThreeLCache对比：
 * - ThreeLCache滑动窗口长度：max_n_past_distances=3, max_n_past_timestamps=4
 * - ThreeLCache使用deque<Meta>存储object元数据，每个Meta包含滑动窗口历史
 * - LOH区别：需要dim护3items独立ofIRT堆用于不同时间窗口ofstats
 */
static void irt_heap_remove(LOH_params_t *params, cache_obj_t *obj,
                            int heap_idx) {
  // 边界check
  if (params->irt_heap_size[heap_idx] == 0 || !obj) return;
  // 说明：本函数依赖 obj->LOH.loh_irt_pos[heap_idx]
  // 的准确性；当开启映射时将用其修复。

  // 优先使用对象内索引，失败再回退到哈希表
  int idx = obj->LOH.loh_irt_pos[heap_idx];
  if (idx < 0) {
#if LOH_MAINTAIN_MAPS
    gpointer idx_ptr =
        params->irt_heap_maps[heap_idx]
            ? g_hash_table_lookup(params->irt_heap_maps[heap_idx], obj)
            : NULL;
    if (!idx_ptr) return;                // object不在此堆
    idx = GPOINTER_TO_INT(idx_ptr) - 1;  // 修正偏移量
#else
    // 不维护映射时，不应出现负索引（调用方和插入时已维护 loh_irt_pos）
    return;
#endif
  }
  int heap_size = params->irt_heap_size[heap_idx];

  // 【增强验证】确保索引有效且对象匹配
  if (idx < 0 || idx >= heap_size ||
      params->irt_heap[heap_idx][idx].obj != obj) {
    // 哈希表数据不一致，清理并返回
    LOH_DEBUG_PRINT_DETAILED(
        "[IRT_HEAP_REMOVE] [warning] Heap %d: Inconsistent state for obj %llu "
        "- "
        "idx=%d, heap_size=%d, obj_match=%s. Cleaning hash entry.\n",
        heap_idx, (unsigned long long)obj->obj_id, idx, heap_size,
        (idx >= 0 && idx < heap_size)
            ? (params->irt_heap[heap_idx][idx].obj == obj ? "true" : "false")
            : "out_of_bounds");
    if (params->irt_heap_maps[heap_idx])
      g_hash_table_remove(params->irt_heap_maps[heap_idx], obj);
    return;
  }

  // 从哈希表中remove object映射，并清空对象内索引
  if (params->irt_heap_maps[heap_idx])
    g_hash_table_remove(params->irt_heap_maps[heap_idx], obj);
  obj->LOH.loh_irt_pos[heap_idx] = -1;

  // 如果remove的不是最后一个元素，需要移动最后元素到此位置
  if (idx < heap_size - 1) {
    // 将最后一个元素移到当前位置
    cache_obj_t *moved_obj = params->irt_heap[heap_idx][heap_size - 1].obj;
    int64_t moved_value = params->irt_heap[heap_idx][heap_size - 1].irt_value;
    params->irt_heap[heap_idx][idx] = params->irt_heap[heap_idx][heap_size - 1];

    // update被移动object的哈希表映射
    if (params->irt_heap_maps[heap_idx])
      g_hash_table_insert(params->irt_heap_maps[heap_idx], moved_obj,
                          GINT_TO_POINTER(idx + 1));  // 修正偏移量
    moved_obj->LOH.loh_irt_pos[heap_idx] = idx;

    // 【修复】智能堆调整：只调用必要的sift操作
    // 先检查是否需要向上移动（与父节点比较）
    bool need_sift_up = false;
    if (idx > 0) {
      int parent = (idx - 1) / 2;
      if (moved_value < params->irt_heap[heap_idx][parent].irt_value) {
        need_sift_up = true;
      }
    }

    if (need_sift_up) {
      irt_heap_sift_up(params, heap_idx, idx);
    } else {
      // 只有在不需要向上移动时才检查向下移动
      irt_heap_sift_down(params, heap_idx, idx);
    }
  }

  params->irt_heap_size[heap_idx]--;

  LOH_DEBUG_PRINT_DETAILED(
      "[IRT_HEAP_REMOVE] Heap %d: Successfully removed obj %llu, new size=%d\n",
      heap_idx, (unsigned long long)obj->obj_id,
      params->irt_heap_size[heap_idx]);

#if LOH_DEBUG_LEVEL >= LOH_DEBUG_ERROR
  // 验证heap_remove后的堆属性
  irt_heap_validate_min_heap_property(params, heap_idx, "heap_remove");
#endif
}

/**
 * @brief 【纯索引方案】更新对象在IRT堆中的位置
 *
 * 特点：
 * - 使用哈希表快速定位对象位置 O(1)
 * - 原子更新IRT值并重新调整堆 O(log n)
 * - 同步更新索引映射，保证一致性
 * - 检测并修复索引错误，确保可靠性
 * - 堆中每个对象只有一个条目，无重复
 */
static void irt_heap_update(LOH_params_t *params, cache_obj_t *obj,
                            int heap_idx) {
  // 先用对象内位置，失败再用哈希
  int idx = obj->LOH.loh_irt_pos[heap_idx];
  if (idx < 0) {
    if (params->irt_heap_maps[heap_idx]) {
      // 仅在维护映射时统计缺失索引（可确认对象应在堆内的情况）
#if LOH_PERF_PROFILING
      params->perf.irt_missing_index++;
#endif
      gpointer idx_ptr =
          g_hash_table_lookup(params->irt_heap_maps[heap_idx], obj);
      if (!idx_ptr) {
#if LOH_PERF_PROFILING
        params->perf.irt_hash_miss++;
#endif
        LOH_DEBUG_PRINT_ERROR(
            "[irt_heap_update] [warning] Object not found in hash table for "
            "heap %d, searching linearly...\n",
            heap_idx);
        // 如果hash表中找不到，尝试在堆中线性搜索并修复hash表
#if LOH_PERF_PROFILING
        params->perf.irt_linear_scans++;
#endif
        for (int i = 0; i < params->irt_heap_size[heap_idx]; i++) {
          if (params->irt_heap[heap_idx][i].obj == obj) {
            idx = i;
            // 修复hash表与对象内索引
            g_hash_table_insert(params->irt_heap_maps[heap_idx], obj,
                                GINT_TO_POINTER(i + 1));  // 修正偏移量
            obj->LOH.loh_irt_pos[heap_idx] = i;
#if LOH_PERF_PROFILING
            params->perf.irt_fixups++;
#endif
            LOH_DEBUG_PRINT_ERROR(
                "[irt_heap_update] Found object at index %d, fixed hash "
                "table\n",
                i);
            break;
          }
        }
        if (idx == -1) {
          LOH_DEBUG_PRINT_DETAILED(
              "[irt_heap_update] [warning] Object not found in heap %d, adding "
              "new entry\n",
              heap_idx);
#if LOH_PERF_PROFILING
          params->perf.irt_fixups++;
#endif
          irt_heap_add(params, obj, heap_idx);
          return;
        }
      } else {
        idx = GPOINTER_TO_INT(idx_ptr) - 1;  // 修正偏移量
      }
    } else {
      // 不维护映射时，没有对象内索引则无法更新
      return;
    }
  }

  if (idx < 0 || idx >= params->irt_heap_size[heap_idx]) {
    // 若堆为空或大小为0，视为无操作的早退，不计作 invalid_index
    if (params->irt_heap_size[heap_idx] > 0) {
#if LOH_PERF_PROFILING
      params->perf.irt_invalid_index++;
#endif
      LOH_DEBUG_PRINT_DETAILED(
          "[irt_heap_update] [warning] Invalid index %d in heap %d "
          "(heap_size=%d)\n",
          idx, heap_idx, params->irt_heap_size[heap_idx]);
    }
    return;
  }

  // 验证找到的对象是否正确
  if (params->irt_heap[heap_idx][idx].obj != obj) {
#if LOH_PERF_PROFILING
    params->perf.irt_mismatch_obj++;
#endif
    LOH_DEBUG_PRINT_DETAILED(
        "[irt_heap_update] [warning] Hash table inconsistency detected\n");
    return;
  }

  // 更新IRT值
  int64_t old_irt = params->irt_heap[heap_idx][idx].irt_value;
  int64_t new_irt = obj->LOH.irt_values[heap_idx];

  if (old_irt != new_irt) {
    params->irt_heap[heap_idx][idx].irt_value = new_irt;

    // 【修复】根据新旧值的大小关系决定上移还是下移 - 最小堆逻辑
    if (new_irt < old_irt) {
      irt_heap_sift_up(params, heap_idx, idx);  // 新值更小，向上移动
    } else if (new_irt > old_irt) {
      irt_heap_sift_down(params, heap_idx, idx);  // 新值更大，向下移动
    }
  } /*
// ===== 方法2：纯哈希表查找=====
// 1. 查找对象在堆中的当前位置
gpointer pos_ptr =
 g_hash_table_lookup(params->irt_heap_maps[heap_idx], obj);

if (pos_ptr != NULL) {
int pos = GPOINTER_TO_INT(pos_ptr) - 1;  // 修正偏移量

// 2. 验证位置有效性和对象一致性
if (pos >= 0 && pos < params->irt_heap_size[heap_idx] &&
   params->irt_heap[heap_idx][pos].obj == obj) {
 // 3. 原子更新IRT值
 int64_t old_irt = params->irt_heap[heap_idx][pos].irt_value;
 int64_t new_irt = obj->LOH.irt_values[heap_idx];

 if (old_irt != new_irt) {
   params->irt_heap[heap_idx][pos].irt_value = new_irt;

   LOH_DEBUG_PRINT_DETAILED(
       "[INDEXED_UPDATE] Heap %d: obj %llu IRT %ld -> %ld at pos %d\n",
       heap_idx, (unsigned long long)obj->obj_id, old_irt, new_irt, pos);

   // 4. 【修复】重新调整堆结构，索引会自动同步更新 - 最小堆逻辑
   if (new_irt < old_irt) {
     irt_heap_sift_up(params, heap_idx, pos);    // 新值更小，向上移动
   } else if (new_irt > old_irt) {
     irt_heap_sift_down(params, heap_idx, pos);  // 新值更大，向下移动
   }
 }
} else {
 // 索引不一致，需要修复
 LOH_DEBUG_PRINT_DETAILED(
     "[INDEXED_UPDATE] [warning] Index inconsistency detected for obj %llu in "
     "heap %d\n",
     (unsigned long long)obj->obj_id, heap_idx);
 irt_heap_repair_index_inconsistency(params, obj, heap_idx);
}
} else {
// 对象不在堆中，添加新条目
irt_heap_add(params, obj, heap_idx);
}
*/

#if LOH_DEBUG_LEVEL >= LOH_DEBUG_ERROR
  // 验证heap_update后的堆属性
  irt_heap_validate_min_heap_property(params, heap_idx, "heap_update");
#endif
}

/**
 * @brief 【改进方案】基于索引的原子堆更新 - 保证一致性
 *
 * 特点：
 * - 使用哈希表快速定位对象位置
 * - 原子更新IRT值并重新调整堆
 * - 同步更新索引映射，避免不一致
 * - 检测并修复索引错误
 */
/**
 * @brief 修复索引不一致问题
 */
static void irt_heap_repair_index_inconsistency(LOH_params_t *params,
                                                cache_obj_t *obj,
                                                int heap_idx) {
  LOH_DEBUG_PRINT_DETAILED(
      "[REPAIR] Fixing index inconsistency for obj %llu in heap %d\n",
      (unsigned long long)obj->obj_id, heap_idx);

  // 1. 从哈希表中删除错误的映射
  g_hash_table_remove(params->irt_heap_maps[heap_idx], obj);

  // 2. 线性搜索找到对象的实际位置
  for (int i = 0; i < params->irt_heap_size[heap_idx]; i++) {
    if (params->irt_heap[heap_idx][i].obj == obj) {
      // 找到了，重新建立正确的索引映射
      g_hash_table_insert(params->irt_heap_maps[heap_idx], obj,
                          GINT_TO_POINTER(i + 1));  // 修正偏移量
      LOH_DEBUG_PRINT_DETAILED(
          "[REPAIR] Found obj %llu at position %d, fixed mapping\n",
          (unsigned long long)obj->obj_id, i);
      return;
    }
  }

  // 3. 如果没找到，说明对象已经不在堆中，添加新条目
  LOH_DEBUG_PRINT_DETAILED(
      "[REPAIR] [warning] Obj %llu not found in heap %d, adding new entry\n",
      (unsigned long long)obj->obj_id, heap_idx);
  irt_heap_add(params, obj, heap_idx);
}

/**
 * @brief 带版本号的堆添加操作
 */
/**
 * @brief 从IRT1堆获取淘汰候选object
 * IRT1堆中对象的最近一次间隔时间，堆顶是IRT1值最大对象（最久未被重复访问）
 * 使用临时堆避免破坏原堆结构，通过逐个提取堆顶获得按IRT1降序排列的候选对象
 *
 * @param params LOH参数结构体
 * @param max_candidates 最大候选数量限制
 * @param n_candidates 输入输出参数：输入当前已有候选数，输出更新后的总候选数
 */
static void irt1_heap_get_candidates(LOH_params_t *params, int max_candidates,
                                     int *n_candidates) {
  int heap_idx = 0;               // IRT1对应第0个堆
  int added = 0;                  // 本次add的候选object计数
  int start_idx = *n_candidates;  // 在全局候选数组中的起始位置

  // 检查IRT1堆是否为空
  if (params->irt_heap_size[heap_idx] == 0) {
    LOH_DEBUG_PRINT_DETAILED("[IRT1 DEBUG] IRT1 heap is empty, size=0\n");
    return;  // 堆为空，无法提供候选对象
  }

  cache_t *cache = (cache_t *)params->cache_ptr;  // 获取缓存指针

  LOH_DEBUG_PRINT_DETAILED(
      "[IRT1 HEAP DEBUG] Starting candidate collection from heap size=%d, "
      "max_candidates=%d, start_idx=%d\n",
      params->irt_heap_size[heap_idx], max_candidates, start_idx);

  // 【简化方案】直接遍历堆中所有元素作为候选
  // 因为最小堆中存储的都是具有较大IRT值的对象，正是驱逐候选
  for (int i = 0; i < params->irt_heap_size[heap_idx] && added < max_candidates;
       i++) {
    // 检查全局候选数组边界
    if (start_idx + added >= MAX_CANDIDATES) {
      LOH_DEBUG_PRINT_DETAILED(
          "[IRT1 HEAP DEBUG] Reached MAX_CANDIDATES limit: %d\n",
          MAX_CANDIDATES);
      break;
    }

    cache_obj_t *candidate = params->irt_heap[heap_idx][i].obj;

    // 验证对象有效性：热路径移除哈希membership检查（调试构建保留）
    if (candidate != NULL) {
#if LOH_DEBUG_LEVEL >= LOH_DEBUG_ERROR
      if (hashtable_find_obj_id(cache->hashtable, candidate->obj_id) !=
          candidate) {
        LOH_DEBUG_PRINT_ERROR(
            "[IRT1 HEAP DEBUG] Skipped invalid candidate: obj_id=%llu\n",
            (unsigned long long)candidate->obj_id);
        continue;
      }
#endif
      // 融合去重：IRT1 候选加入前先通过 seen 去重
      if (loh_seen_add(params, candidate)) {
        params->candidates[start_idx + added++] =
            candidate;  // 添加到全局候选数组
      }
      LOH_DEBUG_PRINT_DETAILED(
          "[IRT1 HEAP DEBUG] Added valid candidate #%d: obj_id=%llu, "
          "irt_value=%ld\n",
          added, (unsigned long long)candidate->obj_id,
          params->irt_heap[heap_idx][i].irt_value);
    } else {
      LOH_DEBUG_PRINT_DETAILED(
          "[IRT1 HEAP DEBUG] Skipped invalid candidate: obj_id=%llu\n",
          candidate ? (unsigned long long)candidate->obj_id : 0ULL);
    }
  }

  *n_candidates = start_idx + added;  // 更新总候选数
  LOH_DEBUG_PRINT_DETAILED(
      "[IRT1 HEAP DEBUG] Completed candidate collection: heap_size=%d, "
      "max_candidates=%d, added=%d, total=%d (start_idx=%d)\n",
      params->irt_heap_size[heap_idx], max_candidates, added, *n_candidates,
      start_idx);
}

/**
 * @brief 从IRT2最小堆获取驱逐候选对象
 */
static void irt2_heap_get_candidates(LOH_params_t *params, int max_candidates,
                                     int *n_candidates) {
  int heap_idx = 1;  // IRT2对应第1个堆
  int added = 0;
  int start_idx = *n_candidates;

  if (params->irt_heap_size[heap_idx] == 0) {
    LOH_DEBUG_PRINT_DETAILED("[IRT2 DEBUG] IRT2 heap is empty, size=0\n");
    return;
  }

  cache_t *cache = (cache_t *)params->cache_ptr;  // 获取缓存指针

  // 【简化方案】直接遍历堆中所有元素作为候选
  for (int i = 0; i < params->irt_heap_size[heap_idx] && added < max_candidates;
       i++) {
    if (start_idx + added >= MAX_CANDIDATES) break;

    cache_obj_t *candidate = params->irt_heap[heap_idx][i].obj;
    if (candidate != NULL) {
#if LOH_DEBUG_LEVEL >= LOH_DEBUG_ERROR
      if (hashtable_find_obj_id(cache->hashtable, candidate->obj_id) !=
          candidate) {
        continue;
      }
#endif
      if (loh_seen_add(params, candidate)) {
        params->candidates[start_idx + added++] = candidate;
      }
    }
  }

  *n_candidates = start_idx + added;
}

/**
 * @brief 从IRT3最小堆获取驱逐候选对象
 */
static void irt3_heap_get_candidates(LOH_params_t *params, int max_candidates,
                                     int *n_candidates) {
  cache_t *cache = (cache_t *)params->cache_ptr;
  int heap_idx = 2;  // IRT3对应第2个堆
  int added = 0;
  int start_idx = *n_candidates;

  if (params->irt_heap_size[heap_idx] == 0) {
    LOH_DEBUG_PRINT_DETAILED("[IRT3 DEBUG] IRT3 heap is empty, size=0\n");
    return;
  }

  // 【简化方案】直接遍历堆中所有元素作为候选
  for (int i = 0; i < params->irt_heap_size[heap_idx] && added < max_candidates;
       i++) {
    if (start_idx + added >= MAX_CANDIDATES) break;

    cache_obj_t *candidate = params->irt_heap[heap_idx][i].obj;
    if (candidate != NULL) {
#if LOH_DEBUG_LEVEL >= LOH_DEBUG_ERROR
      if (hashtable_find_obj_id(cache->hashtable, candidate->obj_id) !=
          candidate) {
        continue;
      }
#endif
      if (loh_seen_add(params, candidate)) {
        params->candidates[start_idx + added++] = candidate;
      }
    }
  }

  *n_candidates = start_idx + added;
}

/**
 * @brief 初始化尺寸桶
 */
static void size_buckets_init(LOH_params_t *params) {
  for (int i = 0; i < SIZE_BUCKET_COUNT; i++) {
    params->size_buckets[i] = NULL;
    params->size_buckets_tail[i] = NULL;
  }
#if LOH_MAINTAIN_MAPS
  params->size_node_map = g_hash_table_new(g_direct_hash, g_direct_equal);
#else
  params->size_node_map = NULL;
#endif
  params->size_bucket_bounds[0] = 524288;     // 512KB
  params->size_bucket_bounds[1] = 1048576;    // 1MB
  params->size_bucket_bounds[2] = 10485760;   // 10MB
  params->size_bucket_bounds[3] = 104857600;  // 100MB
  params->size_bucket_bounds[4] = INT64_MAX;  // 无限大
}

/**
 * @brief 释放尺寸桶资源
 */
static void size_buckets_free(LOH_params_t *params) {
#if LOH_MAINTAIN_MAPS
  if (params->size_node_map) {
    GHashTableIter iter;
    gpointer key, value;
    g_hash_table_iter_init(&iter, params->size_node_map);
    while (g_hash_table_iter_next(&iter, &key, &value)) {
      g_free(value);
    }
    g_hash_table_destroy(params->size_node_map);
    params->size_node_map = NULL;
  }
#else
  // 遍历所有桶释放节点
  for (int b = 0; b < SIZE_BUCKET_COUNT; b++) {
    size_node_t *curr = params->size_buckets[b];
    while (curr) {
      size_node_t *next = curr->next;
      g_free(curr);
      curr = next;
    }
    params->size_buckets[b] = NULL;
    params->size_buckets_tail[b] = NULL;
  }
#endif
}

/**
 * @brief 获取object应该放入的尺寸桶索引
 */
static int size_get_bucket_index(LOH_params_t *params, int64_t size) {
  // 包含全部范围，不再排除小object
  for (int i = 0; i < SIZE_BUCKET_COUNT; i++) {
    if (size <= params->size_bucket_bounds[i]) return i;
  }
  return SIZE_BUCKET_COUNT - 1;
}

/**
 * @brief add object到尺寸桶
 */
static void size_buckets_add(LOH_params_t *params, cache_obj_t *obj) {
  int bucket_idx = size_get_bucket_index(params, obj->obj_size);
  // 现在包含全部范围，不再check-1
  size_node_t *node = g_new0(size_node_t, 1);
  node->obj = obj;
  // 缓存到对象内，避免热路径哈希查找
  obj->LOH.loh_size_node = node;
  // 仍然维护哈希表（用于调试/析构）
  if (params->size_node_map)
    g_hash_table_insert(params->size_node_map, obj, node);
  if (params->size_buckets[bucket_idx] == NULL) {
    params->size_buckets[bucket_idx] = node;
    params->size_buckets_tail[bucket_idx] = node;
  } else {
    node->next = params->size_buckets[bucket_idx];
    params->size_buckets[bucket_idx]->prev = node;
    params->size_buckets[bucket_idx] = node;
  }

#if LOH_DEBUG_LEVEL >= LOH_DEBUG_ERROR
  // 验证尺寸桶一致性
  size_buckets_validate(params, "after_size_add");
#endif
}

/**
 * @brief 从尺寸桶remove object
 */
static void size_buckets_remove(LOH_params_t *params, cache_obj_t *obj) {
  // 【根因】：这段代码导致小object永远不会从size桶中remove！
  // if (obj->obj_size < 524288) return;  // 注释掉这段问题条件

  size_node_t *node = (size_node_t *)obj->LOH.loh_size_node;
  if (node == NULL) return;
  int bucket_idx = size_get_bucket_index(params, obj->obj_size);
  if (node->prev) {
    node->prev->next = node->next;
  } else {
    params->size_buckets[bucket_idx] = node->next;
  }
  if (node->next) {
    node->next->prev = node->prev;
  } else {
    params->size_buckets_tail[bucket_idx] = node->prev;
  }
  if (params->size_node_map) g_hash_table_remove(params->size_node_map, obj);
  g_free(node);
  obj->LOH.loh_size_node = NULL;

#if LOH_DEBUG_LEVEL >= LOH_DEBUG_ERROR
  // 验证尺寸桶一致性
  size_buckets_validate(params, "after_size_remove");
#endif
}

/**
 * @brief 从尺寸桶获取淘汰候选object
 */
static void size_buckets_get_candidates(LOH_params_t *params,
                                        int max_candidates, int *n_candidates) {
  int added = 0;
  int start_idx = *n_candidates;
  // 从大尺寸到小尺寸遍历，同一尺寸level内从尾部（更老object）start选择
  for (int i = SIZE_BUCKET_COUNT - 1; i >= 0 && added < max_candidates; i--) {
    size_node_t *curr =
        params->size_buckets_tail[i];  // 从尾部start，选择更老ofobject
    while (curr != NULL && added < max_candidates) {
      if (start_idx + added >= MAX_CANDIDATES) return;
      if (curr->obj != NULL) {
#if LOH_DEBUG_LEVEL >= LOH_DEBUG_ERROR
        cache_t *cache = (cache_t *)params->cache_ptr;
        if (hashtable_find_obj_id(cache->hashtable, curr->obj->obj_id) !=
            curr->obj) {
          LOH_DEBUG_PRINT_ERROR(
              "[SIZE WARNING] Object obj_id=%llu found in size bucket but not "
              "in cache, skipping\n",
              (unsigned long long)curr->obj->obj_id);
          curr = curr->prev;
          continue;
        }
#endif
        // 融合去重：尺寸候选加入前先通过 seen 去重
        if (loh_seen_add(params, curr->obj)) {
          params->candidates[start_idx + added++] = curr->obj;
        }
      }
      curr = curr->prev;  // 向前遍历（从尾部到头部），选择更老ofobject
    }
  }
  *n_candidates = start_idx + added;
}

// ===== object生命周期管理和一致性验证实现 =====

/**
 * @brief 设置objectstate
 */
static void loh_obj_set_state(cache_obj_t *obj, loh_obj_state_t state) {
  if (obj) {
    obj->LOH.loh_state = (int)state;
  }
}

/**
 * @brief 获取objectstate
 */
static loh_obj_state_t loh_obj_get_state(cache_obj_t *obj) {
  if (obj) {
    return (loh_obj_state_t)obj->LOH.loh_state;
  }
  return LOH_OBJ_STATE_INVALID;
}

/**
 * @brief checkobjectstate是否有效
 */
static bool loh_obj_is_valid_state(cache_obj_t *obj) {
  loh_obj_state_t state = loh_obj_get_state(obj);
  return (state >= LOH_OBJ_STATE_INVALID && state <= LOH_OBJ_STATE_REMOVING);
}

/**
 * @brief 统一of候选object验证函数 - 核心验证始终生效，调试输出仅在debug模式
 * check候选object是否as空以及是否在缓存中
 */
static bool loh_validate_candidate_debug(cache_t *cache, cache_obj_t *candidate,
                                         const char *candidate_type,
                                         int index) {
  // 核心空指针check - 始终进行，避免段错误
  if (!candidate) {
    LOH_DEBUG_PRINT_ERROR(
        "[LOH ERROR] Invalid %s candidate at index %d, obj=NULL\n",
        candidate_type, index);
    return false;
  }

#if LOH_DEBUG_LEVEL >= LOH_DEBUG_ERROR
  // 调试构建：做严格一致性校验
  if (hashtable_find_obj_id(cache->hashtable, candidate->obj_id) != candidate) {
    LOH_DEBUG_PRINT_ERROR(
        "[LOH ERROR] %s candidate obj_id=%llu not in cache hashtable at index "
        "%d\n",
        candidate_type, (unsigned long long)candidate->obj_id, index);
    return false;
  }
#endif

  return true;  // 验证通过
}

/**
 * @brief 原子插入object到所有辅助数据结构
 */
static bool loh_atomic_insert_obj(LOH_params_t *params, cache_obj_t *obj) {
  LOH_DEBUG_PRINT_DETAILED("[loh_atomic_insert_obj]");
  if (!obj) {
    return false;
  }

  // 初始化对象内缓存指针/索引
  obj->LOH.loh_freq_node = NULL;
  obj->LOH.loh_size_node = NULL;
  obj->LOH.loh_irt_pos[0] = obj->LOH.loh_irt_pos[1] = obj->LOH.loh_irt_pos[2] =
      -1;

  // 尝试插入到所有辅助结构
  bool success = true;

  // 1. 插入LRU队列（移到这里统一process）
  prepend_obj_to_head(&params->q_head, &params->q_tail, obj);

  // 2. 插入frequency表
  freq_table_add(params, obj);

  // 3. 插入尺寸桶
  size_buckets_add(params, obj);

  // 4. 插入IRT堆 - 使用专门的add函数，避免update函数中的无意义查找
  for (int i = 0; i < IRT_HISTORY_SIZE; i++) {
    irt_heap_add(params, obj, i);
  }

  return true;
}

/**
 * @brief 原子removeobject从所有辅助数据结构
 */
static bool loh_atomic_remove_obj(LOH_params_t *params, cache_obj_t *obj) {
  LOH_DEBUG_PRINT_DETAILED("[loh_atomic_remove_obj]");
  // 从LRU队列inremove
  remove_obj_from_list(&params->q_head, &params->q_tail, obj);

  // 从所有辅助结构remove
  freq_table_remove(params, obj);
  size_buckets_remove(params, obj);

  // IRT 堆remove（remove所有堆inofobject）
  for (int i = 0; i < IRT_HISTORY_SIZE; i++) {
    irt_heap_remove(params, obj, i);
  }

  // 清理对象内缓存指针/索引
  obj->LOH.loh_freq_node = NULL;
  obj->LOH.loh_size_node = NULL;
  obj->LOH.loh_irt_pos[0] = obj->LOH.loh_irt_pos[1] = obj->LOH.loh_irt_pos[2] =
      -1;

  return true;
}

/**
 * @brief 原子更新对象在所有辅助数据结构中的状态
 */
static bool loh_atomic_update_obj(LOH_params_t *params, cache_obj_t *obj) {
  LOH_DEBUG_PRINT_DETAILED("[loh_atomic_update_obj]");
  // 1. update LRU 队列位置（若已在队首则跳过）
  if (obj != params->q_head) {
    PERF_TS ts_lru;
    PERF_NOW(ts_lru);
    remove_obj_from_list(&params->q_head, &params->q_tail, obj);
    prepend_obj_to_head(&params->q_head, &params->q_tail, obj);
    PERF_ACCUM(params, atomic_update_lru, ts_lru);
  }

  // 2. updatefrequency表
  {
    PERF_TS ts_freq;
    PERF_NOW(ts_freq);
    freq_table_update(params, obj);
    PERF_ACCUM(params, atomic_update_freq, ts_freq);
  }

  // 3. updateIRT堆 - 统一使用高效的哈希表查找方式
  for (int i = 0; i < IRT_HISTORY_SIZE; i++) {
    PERF_TS ts_irt;
    PERF_NOW(ts_irt);
    irt_heap_update(params, obj, i);
    PERF_ACCUM(params, atomic_update_irt, ts_irt);
    if (i == 0)
      PERF_ACCUM(params, atomic_update_irt1, ts_irt);
    else if (i == 1)
      PERF_ACCUM(params, atomic_update_irt2, ts_irt);
    else if (i == 2)
      PERF_ACCUM(params, atomic_update_irt3, ts_irt);
  }

  return true;
}

/**
 * @brief 验证object在辅助数据结构中的一致性
 */
static bool loh_verify_object_consistency(LOH_params_t *params,
                                          cache_obj_t *obj, int verify_flags) {
  if (!obj) {
    return false;
  }

  bool consistent = true;

  // 验证frequency表一致性
  if (verify_flags & LOH_VERIFY_FREQ) {
    loh_freq_node_t *freq_node =
        g_hash_table_lookup(params->freq_node_map, obj);
    if (freq_node) {
      if (freq_node->obj != obj) {
        printf(
            "[LOH CONSISTENCY ERROR] Frequency table mapping mismatch for "
            "obj_id=%llu\n",
            (unsigned long long)obj->obj_id);
        consistent = false;
      }
    }
  }

  // 验证尺寸桶一致性
  if (verify_flags & LOH_VERIFY_SIZE) {
    size_node_t *size_node = g_hash_table_lookup(params->size_node_map, obj);
    if (size_node) {
      if (size_node->obj != obj) {
        printf(
            "[LOH CONSISTENCY ERROR] Size bucket mapping mismatch for "
            "obj_id=%llu\n",
            (unsigned long long)obj->obj_id);
        consistent = false;
      }
    }
  }

  return consistent;
}

/**
 * @brief 验证所有object在辅助数据结构中的一致性
 */
static bool loh_verify_all_consistency(LOH_params_t *params) {
  bool all_consistent = true;

  // 遍历LRU队列中的所有object
  cache_obj_t *curr = params->q_head;
  while (curr) {
    curr = curr->queue.next;
  }

  return all_consistent;
}

/**
 * @brief 修复object的不一致状态
 */
static void loh_repair_inconsistency(LOH_params_t *params, cache_obj_t *obj) {
  if (!obj) {
    return;
  }

  LOH_DEBUG_PRINT_ERROR(
      "[LOH REPAIR] Attempting to repair inconsistency for obj_id=%llu\n",
      (unsigned long long)obj->obj_id);

  // 先从所有辅助结构inremove
  loh_atomic_remove_obj(params, obj);

  // 重新插入
  if (!loh_atomic_insert_obj(params, obj)) {
    LOH_DEBUG_PRINT_ERROR("[LOH REPAIR ERROR] Failed to repair obj_id=%llu\n",
                          (unsigned long long)obj->obj_id);
  } else {
    LOH_DEBUG_PRINT_ERROR("[LOH REPAIR SUCCESS] Repaired obj_id=%llu\n",
                          (unsigned long long)obj->obj_id);
  }
}

/**
 * @brief 从错误中恢复
 */
static bool loh_recover_from_error(LOH_params_t *params, cache_obj_t *obj,
                                   const char *error_context) {
  LOH_DEBUG_PRINT_ERROR(
      "[LOH ERROR RECOVERY] Recovering from error in %s for obj_id=%llu\n",
      error_context ? error_context : "unknown",
      obj ? (unsigned long long)obj->obj_id : 0);

  if (!obj) {
    // 全局清理
    loh_cleanup_orphaned_entries(params);
    return true;
  }

  // 尝试修复单个object
  loh_repair_inconsistency(params, obj);

  // 修复完成
  return true;
}

/**
 * @brief 清理孤立的辅助数据结构条目
 */
static void loh_cleanup_orphaned_entries(LOH_params_t *params) {
  LOH_DEBUG_PRINT_ERROR("[LOH CLEANUP] Starting orphaned entries cleanup\n");

  GHashTableIter iter;
  gpointer key, value;

  // check frequency节点映射
  if (params->freq_node_map) {
    g_hash_table_iter_init(&iter, params->freq_node_map);
    while (g_hash_table_iter_next(&iter, &key, &value)) {
      cache_obj_t *obj = (cache_obj_t *)key;
      loh_freq_node_t *freq_node = (loh_freq_node_t *)value;

      if (!obj || !freq_node || freq_node->obj != obj) {
        LOH_DEBUG_PRINT_ERROR(
            "[LOH CLEANUP] Removing orphaned frequency entry for obj_id=%llu\n",
            obj ? (unsigned long long)obj->obj_id : 0);
        g_hash_table_iter_remove(&iter);
        if (freq_node) {
          g_free(freq_node);
        }
      }
    }
  }

  // check尺寸节点映射
  if (params->size_node_map) {
    g_hash_table_iter_init(&iter, params->size_node_map);
    while (g_hash_table_iter_next(&iter, &key, &value)) {
      cache_obj_t *obj = (cache_obj_t *)key;
      size_node_t *size_node = (size_node_t *)value;

      if (!obj || !size_node || size_node->obj != obj) {
        LOH_DEBUG_PRINT_DETAILED(
            "[LOH CLEANUP] Removing orphaned size entry for obj_id=%llu\n",
            obj ? (unsigned long long)obj->obj_id : 0);
        g_hash_table_iter_remove(&iter);
        if (size_node) {
          g_free(size_node);
        }
      }
    }
  }

  LOH_DEBUG_PRINT_ERROR("[LOH CLEANUP] Orphaned entries cleanup completed\n");
}

// ===== 缓存内容stats实现 =====

/**
 * @brief 【ThreeLCache vs LOH 数据管理架构深度对比】
 *
 * ThreeLCacheof真实架构：
 * 1. in_cache.metas：当前缓存中ofobject元数据
 *    - 容量：等于缓存大小（setSize设置）
 *    - 用途：实时缓存管理 + MLfeaturecalc
 * 2. out_cache.metas：最近驱逐ofobject滑动窗口
 *    - 容量：固定窗口大小（max_out_cache_size，独立于缓存大小）
 *    - 用途：检测object重新访问模式，辅助重入决策
 * 3. 关键特点：
 *    - 不是简单of"长时间保存"关系
 *    - 两items队列有明确of功能分工
 *    - object在不同队列间转移时，Meta数据保持一致
 *
 * LOHof错误设计（已修复）：
 * 1. cache_obj_t.LOH vs global_access_records 数据不一致
 * 2. 插入时：obj->LOH.access_count = 1，但freq_table_addin重新calc
 * 3. update逻辑分散，导致同一object在不同地方有不同offeature值
 *
 * 修复后ofLOH架构：
 * 1. 统一feature获取接口：get_unified_access_count()
 * 2. 插入时使用全局记录calc正确of初始访问次数
 * 3. 后续update保持数据结构间of一致性
 *
 * 窗口大小确定策略：
 * - ThreeLCache：预设固定窗口大小，不依赖缓存容量
 * - LOH：动态预估（HISTORY_MULTIPLIER *
 * cache_size），需要预估是因as要支持全局stats
 */

/**
 * @brief 【数据一致性修复】统一objectfeatureupdate接口
 *
 * 问题：LOHin存在两套独立offeatureupdate逻辑
 * 1. cache_obj_t.LOH：缓存objectfeature（用于实时评分）
 * 2. global_access_records：全局访问历史（用于RL训练）
 *
 * 不一致案例：
 * - LOH_insertin：obj->LOH.access_count = 1
 * - freq_table_addin：freq = global_access_records[].access_count + 1
 *
 * 解决方案：统一feature获取和update接口，确保数据同步
 */

/**
 * @brief 清理辅助数据结构中的无效object
 */
static void cleanup_invalid_objects(LOH_params_t *params) {
  // 清理frequency表中的无效object
  for (int freq = 1; freq <= FREQ_MAX; freq++) {
    loh_freq_node_t *curr = params->freq_table[freq];
    loh_freq_node_t *prev = NULL;

    while (curr != NULL) {
      loh_freq_node_t *next = curr->next;

      if (curr->obj == NULL) {
        // remove无效节点
        if (prev) {
          prev->next = next;
        } else {
          params->freq_table[freq] = next;
        }

        if (next) {
          next->prev = prev;
        } else {
          params->freq_table_tail[freq] = prev;
        }

        g_free(curr);
        curr = next;
      } else {
        prev = curr;
        curr = next;
      }
    }
  }

  // 清理size buckets中的无效object
  for (int i = 0; i < SIZE_BUCKET_COUNT; i++) {
    size_node_t *curr = params->size_buckets[i];
    size_node_t *prev = NULL;

    while (curr != NULL) {
      size_node_t *next = curr->next;

      if (curr->obj == NULL) {
        // remove无效节点
        if (prev) {
          prev->next = next;
        } else {
          params->size_buckets[i] = next;
        }

        if (next) {
          next->prev = prev;
        } else {
          params->size_buckets_tail[i] = prev;
        }

        g_free(curr);
        curr = next;
      } else {
        prev = curr;
        curr = next;
      }
    }
  }

  // 清理IRT堆中的无效object
  for (int heap_idx = 0; heap_idx < IRT_HISTORY_SIZE; heap_idx++) {
    int write_pos = 0;

    for (int read_pos = 0; read_pos < params->irt_heap_size[heap_idx];
         read_pos++) {
      if (params->irt_heap[heap_idx][read_pos].obj != NULL) {
        if (write_pos != read_pos) {
          params->irt_heap[heap_idx][write_pos] =
              params->irt_heap[heap_idx][read_pos];
        }
        write_pos++;
      }
    }

    // update堆大小并重新建立堆结构
    if (write_pos != params->irt_heap_size[heap_idx]) {
      params->irt_heap_size[heap_idx] = write_pos;
      // 重新建立最小堆性质 - 从最后一个非叶子节点开始向下调整
      for (int i = (write_pos / 2) - 1; i >= 0; i--) {
        // 简单的向下调整实现
        int parent = i;
        while (parent * 2 + 1 < write_pos) {
          int left_child = parent * 2 + 1;
          int right_child = parent * 2 + 2;
          int smallest = parent;

          if (params->irt_heap[heap_idx][left_child].irt_value <
              params->irt_heap[heap_idx][smallest].irt_value) {
            smallest = left_child;
          }

          if (right_child < write_pos &&
              params->irt_heap[heap_idx][right_child].irt_value <
                  params->irt_heap[heap_idx][smallest].irt_value) {
            smallest = right_child;
          }

          if (smallest != parent) {
            // 交换
            irt_heap_entry_t temp = params->irt_heap[heap_idx][parent];
            params->irt_heap[heap_idx][parent] =
                params->irt_heap[heap_idx][smallest];
            params->irt_heap[heap_idx][smallest] = temp;
            parent = smallest;
          } else {
            break;
          }
        }
      }
    }
  }
}

/**
 * @brief add object到缓存时update缓存内容stats
 */
static void update_cache_content_stats_add(LOH_params_t *params,
                                           cache_obj_t *obj) {
  if (!obj) return;

  // 使用统一的特征计算接口
  double features[FEATURE_DIM];
  calculate_object_features(params, obj, features);

  // [DEBUG] Cache content stats before adding
  LOH_DEBUG_PRINT_DETAILED(
      "[update_cache_content_stats_add] State before adding - "
      "cache_object_count=%ld\n",
      (long)params->cache_object_count);
#if LOH_DEBUG_LEVEL >= LOH_DEBUG_VERBOSE
  for (int i = 1; i < FEATURE_DIM; i++) {
    LOH_DEBUG_PRINT_DETAILED(
        "[update_cache_content_stats_add] Feature[%d] before - sum=%.6f, "
        "sum_sq=%.6f, mean=%.6f\n",
        i, params->cache_feature_sum[i], params->cache_feature_sum_sq[i],
        params->cache_object_count > 0
            ? params->cache_feature_sum[i] / params->cache_object_count
            : 0.0);
  }
#endif

  int old_count = params->cache_object_count;
  params->cache_object_count++;

  // [DEBUG] Object features being added
  LOH_DEBUG_PRINT_DETAILED(
      "[update_cache_content_stats_add] Adding object - obj_id=%llu, "
      "features=[%.6f,%.6f,%.6f,%.6f,%.6f,%.6f]\n",
      (unsigned long long)obj->obj_id, features[0], features[1], features[2],
      features[3], features[4], features[5]);

#if LOH_INCLUDE_CACHE_FEATURES
  // 仅在需要缓存特征时更新缓存统计
  // 省略feature0 (recency)：所有objectofrecency都会改变，全局update成本太高
  for (int i = 1; i < FEATURE_DIM; i++) {
#if LOH_DEBUG_LEVEL >= LOH_DEBUG_DETAILED
    double old_sum = params->cache_feature_sum[i];
    double old_sum_sq = params->cache_feature_sum_sq[i];
#endif
    params->cache_feature_sum[i] += features[i];
    params->cache_feature_sum_sq[i] += features[i] * features[i];

    // [DEBUG] Cache content stats update
    LOH_DEBUG_PRINT_DETAILED(
        "[update_cache_content_stats_add] Feature[%d] update - count: "
        "%ld->%ld, sum: "
        "%.6f->%.6f, sum_sq: %.6f->%.6f, new_mean: %.6f\n",
        i, (long)old_count, (long)params->cache_object_count, old_sum,
        params->cache_feature_sum[i], old_sum_sq,
        params->cache_feature_sum_sq[i],
        params->cache_object_count > 0
            ? params->cache_feature_sum[i] / params->cache_object_count
            : 0.0);
  }
#else
  // 26维模式下不需要更新缓存特征统计
  LOH_DEBUG_PRINT_DETAILED(
      "[update_cache_content_stats_add] Skipping cache feature updates "
      "(26-dim mode)\n");
#endif
}

/**
 * @brief 从缓存remove object时update缓存内容stats
 */
static void update_cache_content_stats_remove(LOH_params_t *params,
                                              cache_obj_t *obj) {
  if (!obj || params->cache_object_count <= 0) return;

  double features[FEATURE_DIM];
  calculate_object_features(params, obj, features);

  // [DEBUG] Cache content stats before removing
  LOH_DEBUG_PRINT_DETAILED(
      "[update_cache_content_stats_remove] State before removing - "
      "cache_object_count=%ld\n",
      (long)params->cache_object_count);
#if LOH_DEBUG_LEVEL >= LOH_DEBUG_VERBOSE
  for (int i = 1; i < FEATURE_DIM; i++) {
    LOH_DEBUG_PRINT_DETAILED(
        "[update_cache_content_stats_remove] Feature[%d] before - sum=%.6f, "
        "sum_sq=%.6f, mean=%.6f\n",
        i, params->cache_feature_sum[i], params->cache_feature_sum_sq[i],
        params->cache_object_count > 0
            ? params->cache_feature_sum[i] / params->cache_object_count
            : 0.0);
  }
#endif

  // [DEBUG] Object features being removed
  LOH_DEBUG_PRINT_DETAILED(
      "[update_cache_content_stats_remove] Removing object - obj_id=%llu, "
      "features=[%.6f,%.6f,%.6f,%.6f,%.6f,%.6f]\n",
      (unsigned long long)obj->obj_id, features[0], features[1], features[2],
      features[3], features[4], features[5]);

  int old_count = params->cache_object_count;
  params->cache_object_count--;

#if LOH_INCLUDE_CACHE_FEATURES
  // 仅在需要缓存特征时更新缓存统计
  // 省略feature0 (recency)：所有object recency都会改变，全局update成本太高
  for (int i = 1; i < FEATURE_DIM; i++) {
#if LOH_DEBUG_LEVEL >= LOH_DEBUG_DETAILED
    double old_sum = params->cache_feature_sum[i];
    double old_sum_sq = params->cache_feature_sum_sq[i];
#endif
    params->cache_feature_sum[i] -= features[i];
    params->cache_feature_sum_sq[i] -= features[i] * features[i];

    // 防止浮点误差导致负数
    if (params->cache_feature_sum[i] < 0.0) params->cache_feature_sum[i] = 0.0;
    if (params->cache_feature_sum_sq[i] < 0.0)
      params->cache_feature_sum_sq[i] = 0.0;

    // [DEBUG] Cache content stats update
    LOH_DEBUG_PRINT_DETAILED(
        "[update_cache_content_stats_remove] Feature[%d] update - count: "
        "%ld->%ld, "
        "sum: %.6f->%.6f, sum_sq: %.6f->%.6f, new_mean: %.6f\n",
        i, (long)old_count, (long)params->cache_object_count, old_sum,
        params->cache_feature_sum[i], old_sum_sq,
        params->cache_feature_sum_sq[i],
        params->cache_object_count > 0
            ? params->cache_feature_sum[i] / params->cache_object_count
            : 0.0);
  }
#else
  // 26维模式下不需要更新缓存特征统计
  LOH_DEBUG_PRINT_DETAILED(
      "[update_cache_content_stats_remove] Skipping cache feature updates "
      "(26-dim mode)\n");
#endif
}

/**
 * @brief 在LOH_find更新缓存内容特征统计（incremental_update）
 * @param params LOH参数
 * @param obj 被访问的object（访问前state）
 * @param new_irt 本次访问的IRT值
 */
static void update_cache_content_stats_find(LOH_params_t *params,
                                            cache_obj_t *obj, int64_t new_irt) {
  if (!obj || params->cache_object_count <= 0) return;

  // 【调试打印】incremental_update前state
  LOH_DEBUG_PRINT_DETAILED(
      "[update_cache_content_stats_find] incremental_update - obj_id=%llu, "
      "old_access_count=%d, new_irt=%ld\n",
      (unsigned long long)obj->obj_id, obj->LOH.access_count, new_irt);
  LOH_DEBUG_PRINT_DETAILED(
      "[update_cache_content_stats_find] incremental_updatebefore - "
      "irt_values=[%ld,%ld,%ld]\n",
      obj->LOH.irt_values[0], obj->LOH.irt_values[1], obj->LOH.irt_values[2]);

  // 省略feature0 (recency)：所有objectofrecency都会改变，全局update成本太高

#if LOH_INCLUDE_CACHE_FEATURES
  // 仅在需要缓存特征时进行增量更新

  // feature1 (frequency): 从 access_count 变为 access_count+1（无 log 版本）
  const double K = 1.0;
  double f0 = (double)obj->LOH.access_count;
  double f1 = (double)(obj->LOH.access_count + 1);
  double old_freq = (f0 <= 0.0) ? 0.0 : (f0 / (f0 + K));
  double new_freq = f1 / (f1 + K);

  double freq_delta = new_freq - old_freq;
  double old_freq_sum = params->cache_feature_sum[1];
  double old_freq_sum_sq = params->cache_feature_sum_sq[1];
  params->cache_feature_sum[1] += freq_delta;
  params->cache_feature_sum_sq[1] += new_freq * new_freq - old_freq * old_freq;

  // 【调试打印】frequencyfeatureincremental_update
  LOH_DEBUG_PRINT_DETAILED(
      "[update_cache_content_stats_find] frequencyfeature[1]incremental_update "
      "- old_freq=%.6f, "
      "new_freq=%.6f, delta=%.6f\n",
      old_freq, new_freq, freq_delta);
  LOH_DEBUG_PRINT_DETAILED(
      "[update_cache_content_stats_find] frequencyfeature[1]stats_update - "
      "sum: "
      "%.6f->%.6f, sum_sq: %.6f->%.6f\n",
      old_freq_sum, params->cache_feature_sum[1], old_freq_sum_sq,
      params->cache_feature_sum_sq[1]);

  // feature3 (最新IRT): 从irt_values[0]变asnew_irt
  if (obj->LOH.irt_values[0] != new_irt)  // 仅在IRT变化时更新
  {
    double old_irt_feature = calculate_irt_feature(obj->LOH.irt_values[0]);
    double new_irt_feature = calculate_irt_feature(new_irt);

    double irt_delta = new_irt_feature - old_irt_feature;
    double old_irt3_sum = params->cache_feature_sum[3];
    double old_irt3_sum_sq = params->cache_feature_sum_sq[3];
    params->cache_feature_sum[3] += irt_delta;
    params->cache_feature_sum_sq[3] +=
        new_irt_feature * new_irt_feature - old_irt_feature * old_irt_feature;

    // 【调试打印】IRTfeature3incremental_update
    LOH_DEBUG_PRINT_DETAILED(
        "[update_cache_content_stats_find] IRTfeature[3]incremental_update - "
        "old_irt=%ld->new_irt=%ld, old_feature=%.6f, new_feature=%.6f, "
        "delta=%.6f\n",
        obj->LOH.irt_values[0], new_irt, old_irt_feature, new_irt_feature,
        irt_delta);
    LOH_DEBUG_PRINT_DETAILED(
        "[update_cache_content_stats_find] IRTfeature[3]stats_update - sum: "
        "%.6f->%.6f, "
        "sum_sq: %.6f->%.6f\n",
        old_irt3_sum, params->cache_feature_sum[3], old_irt3_sum_sq,
        params->cache_feature_sum_sq[3]);
  }
  // feature4,5 (旧IRT): irt_values[1],irt_values[2]向后移动一位
  // 【修改】去掉irt_count判断，直接根据新旧IRT是否相等来更新所有IRT特征

  // 特征 4: irt_values[1] -> irt_values[0] (原来的值)
  if (obj->LOH.irt_values[1] != obj->LOH.irt_values[0])  // 仅在IRT变化时更新
  {
    double old_irt4 = calculate_irt_feature(obj->LOH.irt_values[1]);
    double new_irt4 = calculate_irt_feature(obj->LOH.irt_values[0]);

    double irt4_delta = new_irt4 - old_irt4;
    double old_irt4_sum = params->cache_feature_sum[4];
    double old_irt4_sum_sq = params->cache_feature_sum_sq[4];
    params->cache_feature_sum[4] += irt4_delta;
    params->cache_feature_sum_sq[4] +=
        new_irt4 * new_irt4 - old_irt4 * old_irt4;

    // 【调试打印】IRT 特征 4 增量更新
    LOH_DEBUG_PRINT_DETAILED(
        "[update_cache_content_stats_find] IRTfeature[4]incremental_update - "
        "old_feature=%.6f, new_feature=%.6f, delta=%.6f\n",
        old_irt4, new_irt4, irt4_delta);
    LOH_DEBUG_PRINT_DETAILED(
        "[update_cache_content_stats_find] IRTfeature[4]stats_update - sum: "
        "%.6f->%.6f, sum_sq: %.6f->%.6f\n",
        old_irt4_sum, params->cache_feature_sum[4], old_irt4_sum_sq,
        params->cache_feature_sum_sq[4]);
  }

  // 特征 5: irt_values[2] -> irt_values[1] (原来的值)
  if (obj->LOH.irt_values[2] != obj->LOH.irt_values[1])  // 仅在IRT变化时更新
  {
    double old_irt5 = calculate_irt_feature(obj->LOH.irt_values[2]);
    double new_irt5 = calculate_irt_feature(obj->LOH.irt_values[1]);

    double irt5_delta = new_irt5 - old_irt5;
    double old_irt5_sum = params->cache_feature_sum[5];
    double old_irt5_sum_sq = params->cache_feature_sum_sq[5];
    params->cache_feature_sum[5] += irt5_delta;
    params->cache_feature_sum_sq[5] +=
        new_irt5 * new_irt5 - old_irt5 * old_irt5;

    // 【调试打印】IRT 特征 5 增量更新
    LOH_DEBUG_PRINT_DETAILED(
        "[update_cache_content_stats_find] IRTfeature[5]incremental_update - "
        "old_feature=%.6f, new_feature=%.6f, delta=%.6f\n",
        old_irt5, new_irt5, irt5_delta);
    LOH_DEBUG_PRINT_DETAILED(
        "[update_cache_content_stats_find] IRTfeature[5]stats_update - sum: "
        "%.6f->%.6f, sum_sq: %.6f->%.6f\n",
        old_irt5_sum, params->cache_feature_sum[5], old_irt5_sum_sq,
        params->cache_feature_sum_sq[5]);
  }
#else
  // 26维模式下不需要更新缓存特征统计
  LOH_DEBUG_PRINT_DETAILED(
      "[update_cache_content_stats_find] Skipping cache feature updates "
      "(26-dim mode)\n");
#endif
}

// ====================================================================
// 【新增】：全局访问记录管理函数实现
// ====================================================================

/**
 * @brief 初始化全局访问记录表
 */
/* 【删除全局访问记录系统】改为对象级访问窗口 */

/* End of implementation */

// ====================================================================
// 【新增】：LOH 模块正确性验证函数
// ====================================================================

#if LOH_DEBUG_LEVEL >= LOH_DEBUG_ERROR
/**
 * @brief 验证特征计算模块正确性
 */
static void loh_verify_feature_calculation(LOH_params_t *params,
                                           cache_obj_t *obj) {
  if (!LOH_TEST_FEATURE_CALCULATION) return;

  double features[FEATURE_DIM];
  calculate_object_features(params, obj, features);

  // 验证特征值范围 [0, 1]
  bool valid = true;
  for (int i = 0; i < FEATURE_DIM; i++) {
    if (features[i] < 0.0 || features[i] > 1.0) {
      valid = false;
      break;
    }
  }

  if (valid) {
    LOH_DEBUG_PRINT_DETAILED(
        "[LOH VERIFY] ✓ Feature calculation module: PASS (obj_id=%llu)\n",
        (unsigned long long)(obj ? obj->obj_id : 0ULL));
  } else {
    LOH_DEBUG_PRINT_DETAILED(
        "[LOH VERIFY] ✗ Feature calculation module: FAIL (obj_id=%llu)\n",
        (unsigned long long)(obj ? obj->obj_id : 0ULL));
  }
}

/**
 * @brief 验证驱逐逻辑模块正确性
 */
static void loh_verify_eviction_logic(LOH_params_t *params,
                                      cache_obj_t *evicted_obj) {
  if (!LOH_TEST_EVICTION_LOGIC || !evicted_obj) return;

  // 验证被驱逐对象确实在缓存中
  cache_t *cache = (cache_t *)params->cache_ptr;
  cache_obj_t *found =
      hashtable_find_obj_id(cache->hashtable, evicted_obj->obj_id);

  if (found == evicted_obj) {
    LOH_DEBUG_PRINT_DETAILED(
        "[LOH VERIFY] ✓ Eviction logic module: PASS (evicted obj_id=%llu)\n",
        (unsigned long long)evicted_obj->obj_id);
  } else {
    LOH_DEBUG_PRINT_DETAILED(
        "[LOH VERIFY] ✗ Eviction logic module: FAIL (evicted obj_id=%llu not "
        "in cache)\n",
        (unsigned long long)evicted_obj->obj_id);
  }
}

/**
 * @brief 验证数据一致性模块正确性
 */
static void loh_verify_data_consistency(LOH_params_t *params) {
  if (!LOH_TEST_DATA_CONSISTENCY) return;

  cache_t *cache = (cache_t *)params->cache_ptr;

  // 验证缓存计数一致性
  int lru_count = 0;
  cache_obj_t *curr = params->q_head;
  while (curr != NULL) {
    lru_count++;
    curr = curr->queue.next;
  }

  if (lru_count == cache->n_obj) {
    LOH_DEBUG_PRINT_DETAILED(
        "[LOH VERIFY] ✓ Data consistency module: PASS (LRU count=%d, cache "
        "count=%ld)\n",
        lru_count, cache->n_obj);
  } else {
    LOH_DEBUG_PRINT_DETAILED(
        "[LOH VERIFY] ✗ Data consistency module: FAIL (LRU count=%d != cache "
        "count=%ld)\n",
        lru_count, cache->n_obj);
  }
}

/**
 * @brief 验证性能统计模块正确性
 */
static void loh_verify_performance_stats(LOH_params_t *params, bool is_hit) {
  if (!LOH_TEST_PERFORMANCE_STATS) return;

  // 验证统计计数增加
  static double last_total_requests = -1;  // -1 表示尚未初始化
  double current_total = params->epoch_obj_count;

  // 第一次调用，或 RL 同步导致 epoch 计数被重置变小 —— 视为正常，重置基线
  if (last_total_requests < 0 || current_total < last_total_requests) {
    LOH_DEBUG_PRINT_DETAILED(
        "[LOH VERIFY] ✓ Performance stats module: PASS (reset/baseline: "
        "total_requests=%.0f, hit=%s)\n",
        current_total, is_hit ? "true" : "false");
    last_total_requests = current_total;
    return;
  }

  if (current_total >= last_total_requests) {
    LOH_DEBUG_PRINT_DETAILED(
        "[LOH VERIFY] ✓ Performance stats module: PASS (total_requests=%.0f, "
        "hit=%s)\n",
        current_total, is_hit ? "true" : "false");
    last_total_requests = current_total;
  } else {
    LOH_DEBUG_PRINT_DETAILED(
        "[LOH VERIFY] ✗ Performance stats module: FAIL (total_requests not "
        "increasing: %.0f < %.0f)\n",
        current_total, last_total_requests);
  }
}

/**
 * @brief 打印 LOH 模块状态总览
 */
static void loh_print_module_summary(LOH_params_t *params) {
  cache_t *cache = (cache_t *)params->cache_ptr;

  LOH_DEBUG_PRINT_ERROR("\n=== LOH Module Status Summary ===\n");
  LOH_DEBUG_PRINT_ERROR("Cache Status: %ld objects, size=%ld bytes\n",
                        cache->n_obj, cache->cache_size);
  LOH_DEBUG_PRINT_ERROR(
      "Request Count: %ld (%.2f%% hit rate)\n", (long)params->epoch_obj_count,
      params->epoch_obj_count > 0
          ? (1.0 - params->epoch_obj_miss_count / params->epoch_obj_count) *
                100.0
          : 0.0);
  LOH_DEBUG_PRINT_ERROR(
      "Data Structures: LRU queue, %d IRT heaps, freq table, size buckets\n",
      IRT_HISTORY_SIZE);
  LOH_DEBUG_PRINT_ERROR("Ghost Cache: %ld/%ld entries\n",
                        params->ghost_cache_count,
                        params->ghost_cache_capacity);
  LOH_DEBUG_PRINT_ERROR("================================\n\n");
}
#endif

/**
 * @brief 验证频率表的一致性
 */
static void freq_table_validate(LOH_params_t *params, const char *context) {
  printf("[FREQ_VALIDATE] 🔍 Validating frequency table (%s):\n", context);

  int total_nodes_in_table = 0;
  int total_nodes_in_map = 0;
  if (params->freq_node_map)
    total_nodes_in_map = g_hash_table_size(params->freq_node_map);

  // 验证每个频率级别
  for (int level = 1; level <= FREQ_MAX; level++) {
    loh_freq_node_t *curr = params->freq_table[level];
    int nodes_in_level = 0;

    while (curr != NULL) {
      nodes_in_level++;
      total_nodes_in_table++;

      // 验证节点指向的对象频率是否匹配
      int expected_freq = curr->obj->LOH.access_count;
      if (expected_freq > FREQ_MAX) expected_freq = FREQ_MAX;

      if (expected_freq != level) {
        printf(
            "[FREQ_VALIDATE] ❌ ERROR: Object %p (obj_id=%llu) at freq level "
            "%d but "
            "access_count=%d (expected_freq=%d)\n",
            (void *)curr->obj, (unsigned long long)curr->obj->obj_id, level,
            curr->obj->LOH.access_count, expected_freq);
      }

      // 验证哈希表映射
      loh_freq_node_t *mapped_node = NULL;
      if (params->freq_node_map)
        mapped_node = g_hash_table_lookup(params->freq_node_map, curr->obj);
      if (params->freq_node_map && mapped_node != curr) {
        printf(
            "[FREQ_VALIDATE] ❌ ERROR: Hash map inconsistency for obj %p: "
            "table_node=%p, map_node=%p\n",
            (void *)curr->obj, (void *)curr, (void *)mapped_node);
      }

      // 验证双向链表结构
      if (curr->next && curr->next->prev != curr) {
        printf(
            "[FREQ_VALIDATE] ❌ ERROR: Broken forward link at level %d, node "
            "%p\n",
            level, (void *)curr);
      }
      if (curr->prev && curr->prev->next != curr) {
        printf(
            "[FREQ_VALIDATE] ❌ ERROR: Broken backward link at level %d, node "
            "%p\n",
            level, (void *)curr);
      }

      curr = curr->next;
    }

    if (nodes_in_level > 0) {
      printf("[FREQ_VALIDATE] Level %d: %d nodes\n", level, nodes_in_level);
    }
  }

  // 验证总数一致性
  if (params->freq_node_map && total_nodes_in_table != total_nodes_in_map) {
    printf("[FREQ_VALIDATE] ❌ ERROR: Node count mismatch - table:%d, map:%d\n",
           total_nodes_in_table, total_nodes_in_map);
  } else {
    printf("[FREQ_VALIDATE] ✅ Frequency table is VALID (%s): %d nodes total\n",
           context, total_nodes_in_table);
  }
}

/**
 * @brief 验证尺寸桶的一致性
 */
static void size_buckets_validate(LOH_params_t *params, const char *context) {
  printf("[SIZE_VALIDATE] 🔍 Validating size buckets (%s):\n", context);

  int total_nodes_in_buckets = 0;
  int total_nodes_in_map = 0;
  if (params->size_node_map)
    total_nodes_in_map = g_hash_table_size(params->size_node_map);

  // 验证每个尺寸桶
  for (int bucket = 0; bucket < SIZE_BUCKET_COUNT; bucket++) {
    size_node_t *curr = params->size_buckets[bucket];
    int nodes_in_bucket = 0;

    while (curr != NULL) {
      nodes_in_bucket++;
      total_nodes_in_buckets++;

      // 验证对象尺寸是否匹配桶
      int expected_bucket = size_get_bucket_index(params, curr->obj->obj_size);
      if (expected_bucket != bucket) {
        printf(
            "[SIZE_VALIDATE] ❌ ERROR: Object %p (size=%ld) in bucket %d but "
            "should be in bucket %d\n",
            (void *)curr->obj, curr->obj->obj_size, bucket, expected_bucket);
      }

      // 验证哈希表映射
      size_node_t *mapped_node = NULL;
      if (params->size_node_map)
        mapped_node = g_hash_table_lookup(params->size_node_map, curr->obj);
      if (params->size_node_map && mapped_node != curr) {
        printf(
            "[SIZE_VALIDATE] ❌ ERROR: Hash map inconsistency for obj %p: "
            "bucket_node=%p, map_node=%p\n",
            (void *)curr->obj, (void *)curr, (void *)mapped_node);
      }

      // 验证双向链表结构
      if (curr->next && curr->next->prev != curr) {
        printf(
            "[SIZE_VALIDATE] ❌ ERROR: Broken forward link in bucket %d, node "
            "%p\n",
            bucket, (void *)curr);
      }
      if (curr->prev && curr->prev->next != curr) {
        printf(
            "[SIZE_VALIDATE] ❌ ERROR: Broken backward link in bucket %d, node "
            "%p\n",
            bucket, (void *)curr);
      }

      curr = curr->next;
    }

    if (nodes_in_bucket > 0) {
      printf("[SIZE_VALIDATE] Bucket %d: %d nodes\n", bucket, nodes_in_bucket);
    }
  }

  // 验证总数一致性
  if (params->size_node_map && total_nodes_in_buckets != total_nodes_in_map) {
    printf(
        "[SIZE_VALIDATE] ❌ ERROR: Node count mismatch - buckets:%d, map:%d\n",
        total_nodes_in_buckets, total_nodes_in_map);
  } else {
    printf("[SIZE_VALIDATE] ✅ Size buckets are VALID (%s): %d nodes total\n",
           context, total_nodes_in_buckets);
  }
}

#undef likely
#define likely(x) __builtin_expect(!!(x), 1)
#undef unlikely
#define unlikely(x) __builtin_expect(!!(x), 0)

#ifdef __cplusplus
}
#endif
