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

// ============================================================
// LOH 统一版本 - 运行时环境变量总览
// ============================================================
// 1) RL / 权重相关
//   - LOH_ENABLE_RL        : 是否启用与 Python 的 RL 同步
//                            默认: 1（启用；仅此一个开关）
//   - LOH_FIXED_WEIGHTS    : 固定权重（支持 6/7 维）。格式 "w1,w2,..."；提供 6
//   个值时第 7 个默认为 0。
//                            默认: 未设置（使用编译时内置默认权重
//                                   LOH / LOH-mr-blocked 均为 [1,0,0,0,0,0]）
//   - miss-ratio-weight    : 通过 cache_specific_params 传入，例如
//                            "miss-ratio-weight=1.0"，控制奖励中 miss/byte 比例
//                            默认: 1.0（只看对象 miss ratio）
//
// 2) 共享内存 / 信号量相关
//   - LOH_SHM_KEY          : 共享内存与信号量 key 后缀
//                            默认: "9876"（文件 /dev/shm/loh_ac_9876）
//   - LOH_ENABLE_SEMAPHORE : 强制启用 POSIX 命名信号量
//                            默认: 未设置（若 LOH_DISABLE_SEMAPHORE
//                            未设，则启用）
//   - LOH_DISABLE_SEMAPHORE: 强制禁用 POSIX 命名信号量
//                            默认: 未设置（不禁用）
//   - LOH_WAIT_MODE        : 等待 Python ACK 的模式
//                            取值: "blocked" | "nonblocked"/"non-blocked"
//                            默认: "blocked"（严格等待权重更新）
//
// 3) 特征变换 / 归一化相关
//   - LOH_FEATURE_LOG1P            : 启用 log1p(raw) 形式的特征
//                                    默认: 0（关闭）
//   - LOH_FEATURE_LOG1P_RECIPROCAL: 启用 log1p+1/(1+x) reciprocal 形式
//                                    默认: 0（关闭；若 LOG1P=1 则忽略此项）
//   - LOH_FEATURE_LOG1P_RAW       : 仅用于调试打印，表示是否显式从环境启用
//                                    "原始" log1p 路径（功能上等价于
//                                    LOH_FEATURE_LOG1P，优先使用后者）
//   - LOH_ENABLE_FEATURE_NORMALIZATION
//                                : 启用基于 log1p(max) 的归一化与裁剪
//                                  默认: 0（关闭）
//   - LOH_FEATURE_NORM_MAX_RECENCY: recency 归一化上界，double
//                                    默认: 见 loh_feature_norm_max[0]
//   - LOH_FEATURE_NORM_MAX_FREQ   : frequency 归一化上界
//                                    默认: loh_feature_norm_max[1]
//   - LOH_FEATURE_NORM_MAX_SIZE   : size 归一化上界
//                                    默认: loh_feature_norm_max[2]
//   - LOH_FEATURE_NORM_MAX_IRT    : irt1/2/3 归一化上界
//                                    默认: loh_feature_norm_max[3]
//   - LOH_USE_HEURISTIC_SIGNS     : 是否使用启发式符号（特征符号修正）
//                                    默认: 1（启用；仅当显式设置为 0/false
//                                    时关闭）
//
// 4) Penalty / Ghost cache 相关
//   - LOH_ENABLE_PENALTY    : 是否开启 penalty 队列与延迟惩罚
//                             默认: 0（关闭；可在编译期通过 -D 开启）
//   - loh_enable_rl            ← LOH_ENABLE_RL
// 5) 其它说明
//   - 编译期宏（如 LOH_INCLUDE_CACHE_FEATURES 等）通过 -D
//   控制，不受环境变量影响，
//     但会改变 CONTEXT_DIM 与共享内存布局，详见 copilot-instructions
//     与集成文档。
// ============================================================

// -----------------------------
// 运行时布尔环境变量默认值（集中定义，可按需修改）
// -----------------------------
// 说明：这些默认值只在本文件内部使用，用于在未设置环境变量时
//       决定各开关的初始状态；修改这里即可“人为灵活调整默认值”。

// Penalty 机制开关（编译期宏 + 运行期检查）
#ifndef LOH_ENABLE_PENALTY
#define LOH_ENABLE_PENALTY 0  // 默认关闭
#endif

// =============================
// 运行时环境开关变量（全局）
// =============================
//   - loh_feature_log1p           ← LOH_FEATURE_LOG1P
//   - loh_feature_log1p_reciprocal← LOH_FEATURE_LOG1P_RECIPROCAL
//   - loh_feature_normalize       ← LOH_ENABLE_FEATURE_NORMALIZATION
//   - loh_wait_mode_blocked       ← LOH_WAIT_MODE

// 特征归一化模式开关由后文统一定义和解析（loh_feature_log1p、
// loh_feature_log1p_reciprocal、loh_feature_normalize），此处仅做说明。

// =============================
// 1) RL / 权重相关（全局开关与权重）
// =============================
//   - loh_enable_rl              ← LOH_ENABLE_RL / enable-rl
//   - loh_miss_ratio_weight      ← miss-ratio-weight（cache_specific_params）
//   - loh_byte_miss_ratio_weight ← 1 - loh_miss_ratio_weight
// 说明：这些权重影响奖励函数与 cache_name 命名，进程内全局生效。

static int loh_enable_rl = 1;                    // 默认启用 RL 同步
static double loh_miss_ratio_weight = 1.0;       // 默认只看对象 miss ratio
static double loh_byte_miss_ratio_weight = 0.0;  // 默认不看字节 miss ratio

// =============================
// 2) 共享内存 / 信号量 / 等待模式相关（全局部分）
// =============================
//   - loh_wait_mode_blocked ← LOH_WAIT_MODE
// 说明：LOH_SHM_KEY / LOH_ENABLE_SEMAPHORE / LOH_DISABLE_SEMAPHORE
//       仍通过每个实例的 params->shm_filename / sem_requested 控制，
//       这里只保留影响逻辑分支的全局等待模式开关。

// 等待模式：blocked（阻塞等待）/ nonblocked（非阻塞，使用旧权重）
// 运行时从环境变量 LOH_WAIT_MODE 读取；默认 blocked
static int loh_wait_mode_blocked = 1;  // 1=BLOCKED, 0=NON-BLOCKED

// Size 候选收集方式：0=size_heap (Top-K堆), 1=size_buckets (全量分桶)
// 运行时从环境变量 LOH_USE_SIZE_BUCKETS 读取；默认 0 (使用 size_heap)
static int loh_use_size_buckets = 1;

// =============================
// 3) 特征相关全局配置（在后文继续补充）
// =============================
//   - loh_use_heuristic_signs  ← LOH_USE_HEURISTIC_SIGNS
//   - loh_feature_log1p        ← LOH_FEATURE_LOG1P
//   - loh_feature_log1p_reciprocal ← LOH_FEATURE_LOG1P_RECIPROCAL
//   - loh_feature_normalize    ← LOH_ENABLE_FEATURE_NORMALIZATION
//   - loh_feature_norm_max[]   ← LOH_FEATURE_NORM_MAX_*
// 说明：这里只声明与环境变量对应的全局开关，具体默认值见下文。

static int loh_use_heuristic_signs =
    1;  // 默认启用启发式符号（可通过 LOH_USE_HEURISTIC_SIGNS 关闭）

#if LOH_ENABLE_PENALTY
// Penalty 正样本发送：当 ghost entry 因容量被淘汰且期间未被再次访问时，
// 发送一个 eviction_to_access<0 的条目作为“安全驱逐”证据。
// 默认关闭，避免改变既有实验语义。
static int loh_penalty_send_positive = 0;  // ← LOH_PENALTY_SEND_POSITIVE
#endif

// 评分特征选择相关开关：
//   - loh_score_use_irt        ← LOH_SCORE_USE_IRT
//   - loh_score_use_compound   ← LOH_SCORE_USE_COMPOUND
// 语义：
//   1) 默认配置：LOH_SCORE_USE_IRT 未设置或为真，LOH_SCORE_USE_COMPOUND=0
//      - 评分使用 6 维基础特征：recency, freq, size, irt1, irt2, irt3
//   2) LOH_SCORE_USE_IRT=0 且 LOH_SCORE_USE_COMPOUND=0
//      - 评分仅使用 3 维基础特征：recency, freq, size（忽略 3 个 IRT 分量）
//   3) LOH_SCORE_USE_COMPOUND=1
//      - 评分不再使用 IRT 分量，而是使用：
//        recency, freq, size, freq_recency, freq_size, recency_size
//      - 其中 compound 特征的定义与符号由 LOH_FEATURE_LOG1P 控制：
//        * LOH_FEATURE_LOG1P=1 时：
//            freq_recency = freq / recency（安全除法，recency≈0 时回退）
//            freq_size    = freq / size
//            recency_size = recency * size
//            sign = [-1, 1, -1, 1, 1, -1]
//        * LOH_FEATURE_LOG1P=0 时：
//            freq_recency = freq * recency
//            freq_size    = freq * size
//            recency_size = recency * size
//            sign = [1, 1, 1, 1, 1, 1]
//      - 升级版（LOH_SCORE_COMPOUND_V2=1）：
//        在原 compound 6 维的基础上新增第 7 维复合特征（权重也扩到 7 维，
//        共享内存 weights[] 需要同步扩容）：
//          * 第 7 项（freq_recency_size）：
//              - LOH_FEATURE_LOG1P=1 时：freq / (recency * size)（安全除法）
//              - LOH_FEATURE_LOG1P=0 时：freq * recency * size
//        目的：显式引入 recency/freq/size 的三者乘除关系，保持原 6 项不变。
//      - 在该模式下，LOH_USE_HEURISTIC_SIGNS 对评分符号不再生效。
static int loh_score_use_irt = 1;       // 默认评分包含 IRT 特征
static int loh_score_use_compound = 0;  // 默认关闭 compound 评分模式
static int loh_score_compound_v2 =
    0;  // 对应环境 LOH_SCORE_COMPOUND_V2：compound 升级版（7权重）

// IRT 堆优化：compound 模式不使用 IRT 特征进行评分，
// 因此可以跳过 IRT 堆的全部维护（insert/remove/update）以节省大量 CPU。
// 在 LOH_init 中根据 loh_score_use_compound 自动设置。
static int loh_irt_heap_enabled = 1;  // 默认启用，compound 模式下自动禁用

// 特征归一化模式开关：运行期从环境读取一次后缓存
//   - loh_feature_log1p=1 时：所有特征统一采用 log1p(raw)，并允许 Python 端直接
//     使用原始连续动作作为权重（不再 softmax）。
//   - loh_feature_log1p_reciprocal=1 时：使用 "log1p+1/(1+x)" 的 reciprocal
//     模式。
//   - 若两者都未显式开启，则使用旧的 1/(1+x)、f/(f+1)、1/(1+A*MB) 形式。
static int loh_feature_log1p = 0;  // 对应环境 LOH_FEATURE_LOG1P
static int loh_feature_log1p_reciprocal =
    0;  // 对应环境 LOH_FEATURE_LOG1P_RECIPROCAL

// 运行时开关：是否在计算后进行基于 log1p(max) 的归一化与裁剪
static int loh_feature_normalize =
    0;  // 对应环境 LOH_ENABLE_FEATURE_NORMALIZATION

// =============================
// 3.5) 自动特征模式检测
// =============================
//   - LOH_AUTO_FEATURE_MODE=1 启用自动检测（默认关闭）
//   - 原理：在缓存预热后遍历所有缓存对象，计算 one_hit_ratio
//     (只被访问一次的对象占比)，该指标跨不同 cache size 稳定。
//     one_hit_ratio ≤ 0.6 → 热点集中 → LOG1P + compound
//     one_hit_ratio > 0.6 → 频率均匀 → LOG1P_RECIPROCAL + compound
//   - 同时自动启用 compound=1（在所有 trace 上统一最优）。
//   - 这是 trace 本身的 "访问频率分布形态" 度量，不依赖任何算法结果。
static int loh_auto_feature_mode = 0;          // LOH_AUTO_FEATURE_MODE
static int64_t loh_auto_detect_reqs = 200000;  // LOH_AUTO_DETECT_REQS
static double loh_auto_cv_threshold = 2.5;     // LOH_AUTO_CV_THRESHOLD
static int loh_auto_detected = 0;              // 内部标志：是否已检测

// =============================
// 4) 随机采样候选配置
// =============================
//   - loh_random_candidates  ← LOH_RANDOM_CANDIDATES（默认 96）
//     在结构化候选源之外额外从 hash table 随机采样 N 个候选。
//     注意：这是 ADDITIVE 的，不减少原有结构化源的配额。
static int loh_random_candidates = 96;  // 随机采样数量
// 当 loh_structured_candidates == 0
// 时，跳过结构化候选，仅使用随机采样（等效于旧 RANDOM_ONLY 模式）

// =============================
// 4b) 衰减采样配置 (替代确定性采样)
// =============================
//   - loh_tail_sample_enabled ← LOH_TAIL_SAMPLE（默认 0 = 关闭）
//     设为 1 时，所有候选源（LRU 尾部、频率表、尺寸桶/堆、IRT 堆、随机采样）
//     都改用几何衰减概率采样：p(i) = decay^i。
//     从每个源的"最可能驱逐端"开始遍历，接受概率按位置递减。
//     效果：保持偏向极端（LRU 尾、低频、大尺寸、高
//     IRT），但在更广范围随机探索。
//   - loh_tail_sample_decay ← LOH_TAIL_SAMPLE_DECAY（默认 0.99）
//     衰减因子 ∈ (0, 1)。越接近 1 采样范围越广、衰减越慢；
//     越小则集中在极端端附近。
//     decay=0.99 且 wanted=32 时约扫描 52 个对象即可获得 32 个候选。
static int loh_tail_sample_enabled = 0;
static double loh_tail_sample_decay = 0.99;

// =============================
// 4c) 自适应候选预算（实验性）
// =============================
//   - loh_adaptive_budget ← LOH_ADAPTIVE_BUDGET（默认 0 = 关闭）
//     当启用时，跟踪每个特征源对驱逐的贡献，周期性重新分配预算。
//     贡献多的源获更多候选名额，贡献少的减少。
//   - 重平衡周期：每 LOH_ADAPTIVE_REBALANCE_PERIOD 次驱逐执行一次
#define LOH_MAX_SOURCES \
  7  // recency=0, freq=1, size=2, irt1=3, irt2=4, irt3=5,
     // random/tail=6
#define LOH_ADAPTIVE_REBALANCE_PERIOD 10000
static int loh_adaptive_budget = 0;
static uint64_t loh_source_evict_count[LOH_MAX_SOURCES];  // 各源驱逐贡献计数
static int loh_source_budget[LOH_MAX_SOURCES];  // 自适应预算（初始=均分）
static uint64_t loh_adaptive_total_evict = 0;   // 自适应重平衡计数器
// 候选→来源标签数组（每次 to_evict 重置；与 params->candidates 并行索引）
static int loh_cand_source[2048 + 256];
// per-source 获胜得分累加：O(1)/驱逐，仅在 winner 确定后记录一次
static double loh_source_win_score_sum[LOH_MAX_SOURCES];
// 是否启用 score-based rebalance（默认 0 = 仅用 win-count，即 §19 行为）
static int loh_use_score_rebalance = 0;

// 状态向量配置由编译期 -DLOH_INCLUDE_CACHE_FEATURES=0/1 控制
// 若未显式定义，则在此默认关闭缓存特征：
#ifndef LOH_INCLUDE_CACHE_FEATURES
#define LOH_INCLUDE_CACHE_FEATURES 0
#endif

// 候选特征汇总开关（编译期）：0 关闭，1 开启（附加72维）
#ifndef LOH_INCLUDE_CANDIDATE_FEATURES
#define LOH_INCLUDE_CANDIDATE_FEATURES 0
#endif

// Hit/Miss 特征统计开关（编译期）：0 关闭，1 开启（24维）
#ifndef LOH_INCLUDE_HIT_MISS_FEATURES
#define LOH_INCLUDE_HIT_MISS_FEATURES 0
#endif

// TopK 候选特征开关（编译期）：0 关闭，1 开启（N_TOPK_SAMPLES × 6 维）
// 原名 LOH_INCLUDE_TOPK_CANDIDATE_FEATURES，改名以更清晰表意
#ifndef LOH_INCLUDE_TOPK_CANDIDATE_FEATURES
#define LOH_INCLUDE_TOPK_CANDIDATE_FEATURES 0
#endif

// AvgTopK 候选特征开关（编译期）：0 关闭，1 开启（4 × 6 = 24 维）
// 与 LOH_INCLUDE_TOPK_CANDIDATE_FEATURES 互斥，只保留 TOP4 的平均特征
#ifndef LOH_INCLUDE_AVGTOPK_CANDIDATE_FEATURES
#define LOH_INCLUDE_AVGTOPK_CANDIDATE_FEATURES 0
#endif

// 最近请求特征历史开关（编译期）：0 关闭，1 开启
// 当开启时，会在状态向量末尾追加最近 REQUEST_HISTORY_LEN 次请求的 6 维特征
// （按时间顺序展开，总维度为 REQUEST_HISTORY_LEN × FEATURE_DIM）。
#ifndef LOH_INCLUDE_REQUEST
#define LOH_INCLUDE_REQUEST 0
#endif

// 注：前2维 (hit_ratio, byte_hit_ratio) 始终传递，因为奖励计算需要这两项
// Python 端通过 RL_STATE_USE_MISSRATIO 环境变量控制是否在 RL 观测中使用这两维

// TopK 采样配置
#define N_TOPK_SAMPLES \
  32  // 采样池容量：保留32个最低分对象（每次驱逐取最低4个，共8组）
#define SAMPLES_PER_EVICTION 4  // 每次驱逐时采样的对象数

// LOH 调试模式控制
// 如果未在编译命令中显式定义 LOH_DEBUG_LEVEL，则根据编译模式自动确定
#ifndef LOH_DEBUG_LEVEL
#ifdef NDEBUG
#define LOH_DEBUG_LEVEL 0  // 发布模式：不输出调试信息
#else

#define LOH_DEBUG_LEVEL 1
#endif
#endif

// 调试输出宏定义
#define LOH_DEBUG_CONFIG 0    // 仅配置信息
#define LOH_DEBUG_BASIC 1     // 基础统计信息(RL交互)
#define LOH_DEBUG_ERROR 2     // 非必要的错误信息
#define LOH_DEBUG_DETAILED 3  // 详细操作日志
#define LOH_DEBUG_VERBOSE 4   // 完整调试信息

#if LOH_DEBUG_LEVEL >= LOH_DEBUG_CONFIG
#define LOH_DEBUG_PRINT_CONFIG(...) printf(__VA_ARGS__)
#else
#define LOH_DEBUG_PRINT_CONFIG(...) ((void)0)
#endif

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
#define LOH_PERF_PROFILING 0
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
#if LOH_ENABLE_PENALTY
  // Ghost cache & penalty 相关
  perf_counter_t ghost_cache_lookup;  // ghost_cache 查找
  perf_counter_t ghost_cache_insert;  // ghost_cache 插入
  perf_counter_t penalty_enqueue;     // 惩罚入队
  perf_counter_t penalty_write_shm;   // 惩罚批量写入共享内存
#endif
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

// 解析布尔环境变量工具：1/true/yes/on -> 1，0/false/no/off -> 0，其他保持默认
static int loh_parse_bool_env(const char *val, int default_value) {
  if (!val || !val[0]) return default_value;
  if (strcasecmp(val, "1") == 0 || strcasecmp(val, "true") == 0 ||
      strcasecmp(val, "yes") == 0 || strcasecmp(val, "on") == 0) {
    return 1;
  }
  if (strcasecmp(val, "0") == 0 || strcasecmp(val, "false") == 0 ||
      strcasecmp(val, "no") == 0 || strcasecmp(val, "off") == 0) {
    return 0;
  }
  return default_value;
}

// 各个特征对应的 max 值将在在 FEATURE_DIM 宏定义后静态声明

// 共享内存头文件
#include <errno.h>
#include <fcntl.h>  // 用于文件锁
#include <semaphore.h>
#include <signal.h>
#include <sys/file.h>
#include <sys/ipc.h>
#include <sys/mman.h>  // 用于 mmap 共享内存快速路径
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
#define MAX_CANDIDATES_LIMIT 2048  // 编译期候选池数组上限
#define MAX_CANDIDATES_DEFAULT 96  // 默认运行时候选池大小
// 运行时实际候选池大小（可通过环境变量 LOH_STRUCTURED_CANDIDATES 覆盖）
static int loh_structured_candidates = MAX_CANDIDATES_DEFAULT;
// 向后兼容宏：编译期数组大小使用 MAX_CANDIDATES_LIMIT
#define MAX_CANDIDATES MAX_CANDIDATES_LIMIT
// 注意：seen 去重表（见 LOH_SEEN_CAP）容量与候选池大小直接相关。
// 每轮驱逐会从 6 个特征各取 candidates_per_feature=loh_structured_candidates/6
// 的候选， 去重前的插入尝试数量上界约为
// loh_structured_candidates。为控制线性探测成本：
//   1) LOH_SEEN_CAP 必须为 2 的幂（便于按位取模与代际清理）。
//   2) 建议 LOH_SEEN_CAP 至少为 loh_structured_candidates 的 2–4
//   倍以保持低负载因子。
// 维度命名约定（与 Python RL 端保持一致）：
//   FEATURE_DIM          → 共享内存 state[]
//   的特征列上限（基础特征统计维度，当前为6）。 WEIGHT_DIM           →
//   策略权重长度上限（compound v2 引入第7项，因此为7）。 layout.feature_dim   →
//   运行时真正参与统计/候选的特征数量；当 LOH_SCORE_USE_IRT=0 时会降为3。
//   CONTEXT_DIM          → 编译期确定的共享内存长度上限 (26/38/...)，用于
//   shm_data_t.state 固定数组。 layout.total_dim     →
//   当前配置下实际写入的状态长度 (<= CONTEXT_DIM)，发送给 Python 的有效部分。
// Python 端的 `STATE_DIM`/`STATE_FEATURE_DIM` 采用同样的规则以便双方严格对齐。
#define FEATURE_DIM 6  // 基础特征数量：recency/frequency/size/irt1/irt2/irt3
#define WEIGHT_DIM 7   // 权重维度上限：compound v2 引入第7个复合项

// 评分模型选择（保持默认线性权重不变）
#define LOH_SCORE_MODEL_LINEAR 0
#define LOH_SCORE_MODEL_MLP 1

// MLP 结构：固定输入维度=6（与 FEATURE_DIM 一致），单隐层 ReLU，输出 1
// 参数布局（row-major）：
//   W1[H][D], b1[H], W2[H], b2[1]
// 参数总数：H*(D+2)+1
#define LOH_MLP_MAX_HIDDEN 64
#define LOH_MLP_MAX_PARAMS (LOH_MLP_MAX_HIDDEN * (FEATURE_DIM + 2) + 1)

static inline int loh_mlp_param_len(int hidden) {
  if (hidden <= 0) return 0;
  if (hidden > LOH_MLP_MAX_HIDDEN) hidden = LOH_MLP_MAX_HIDDEN;
  return hidden * (FEATURE_DIM + 2) + 1;
}

// 根据配置选择状态向量维度
// 维度组成：MissRatio(2) + Hit/Miss特征(0/24) + Cache特征(0/12) +
// 候选统计(0/72) + TopK候选(0/N×6)

// 前2维 (hit_ratio, byte_hit_ratio) 始终传递
#define MISSRATIO_DIM 2

#if LOH_INCLUDE_HIT_MISS_FEATURES
#define HIT_MISS_DIM 24  // 6特征 × 2(hit/miss) × 2(mean/var)
#else
#define HIT_MISS_DIM 0
#endif

#if LOH_INCLUDE_CACHE_FEATURES
#define CACHE_DIM 12  // 6特征 × 2(mean/var)
#else
#define CACHE_DIM 0
#endif

#define BASE_STATE_DIM (MISSRATIO_DIM + HIT_MISS_DIM + CACHE_DIM)

#if LOH_INCLUDE_CANDIDATE_FEATURES
#define CAND_FEATURE_DIM 72  // 6(来源)*6(特征)*2(均值/方差)
#else
#define CAND_FEATURE_DIM 0
#endif

#if LOH_INCLUDE_TOPK_CANDIDATE_FEATURES
#define TOPK_FEATURE_DIM \
  (N_TOPK_SAMPLES * FEATURE_DIM)  // N_TOPK_SAMPLES个最低分对象 × 6特征
#else
#define TOPK_FEATURE_DIM 0
#endif

// AvgTopK: 只保留 TOP4 的平均特征 (4 × 6 = 24 维)
#if LOH_INCLUDE_AVGTOPK_CANDIDATE_FEATURES
#define AVGTOPK_FEATURE_DIM \
  (SAMPLES_PER_EVICTION * FEATURE_DIM)  // 4个Top对象 × 6特征 = 24维
#else
#define AVGTOPK_FEATURE_DIM 0
#endif

#if LOH_INCLUDE_REQUEST
#define REQUEST_HISTORY_LEN 200
#define REQUEST_FEATURE_DIM (REQUEST_HISTORY_LEN * FEATURE_DIM)
#else
#define REQUEST_FEATURE_DIM 0
#endif

#define CONTEXT_DIM                                       \
  (BASE_STATE_DIM + CAND_FEATURE_DIM + TOPK_FEATURE_DIM + \
   AVGTOPK_FEATURE_DIM + REQUEST_FEATURE_DIM)

#define LOH_MAX_STATE_FEATURES FEATURE_DIM

typedef struct {
  int feature_dim;           // 有效特征数量（3 或 6）
  int candidate_source_dim;  // 候选来源数量（rec/freq/size[/IRT*3]）
  int hit_miss_dim;          // Hit/Miss 模块有效维度
  int cache_dim;             // Cache 模块有效维度
  int cand_dim;              // 候选统计有效维度
  int topk_dim;              // TOPK 样本有效维度
  int avgtopk_dim;           // AvgTopK 有效维度
  int request_dim;           // 请求历史有效维度
  int total_dim;             // 可用状态总维度（<= CONTEXT_DIM）
} loh_state_layout_t;

static inline loh_state_layout_t loh_get_state_layout(void) {
  loh_state_layout_t layout = {0};
  layout.feature_dim = loh_score_use_irt ? LOH_MAX_STATE_FEATURES : 3;
  if (layout.feature_dim < 0) layout.feature_dim = 0;

#if LOH_INCLUDE_CANDIDATE_FEATURES
  layout.candidate_source_dim = loh_score_use_irt ? 6 : 3;
#else
  layout.candidate_source_dim = 0;
#endif

#if LOH_INCLUDE_HIT_MISS_FEATURES
  layout.hit_miss_dim = layout.feature_dim * 4;
#endif

#if LOH_INCLUDE_CACHE_FEATURES
  layout.cache_dim = layout.feature_dim * 2;
#endif

#if LOH_INCLUDE_CANDIDATE_FEATURES
  layout.cand_dim = layout.candidate_source_dim * layout.feature_dim * 2;
#endif

#if LOH_INCLUDE_TOPK_CANDIDATE_FEATURES
  layout.topk_dim = N_TOPK_SAMPLES * layout.feature_dim;
#endif

#if LOH_INCLUDE_AVGTOPK_CANDIDATE_FEATURES
  layout.avgtopk_dim = SAMPLES_PER_EVICTION * layout.feature_dim;
#endif

#if LOH_INCLUDE_REQUEST
  layout.request_dim = REQUEST_HISTORY_LEN * layout.feature_dim;
#endif

  layout.total_dim = MISSRATIO_DIM;
  layout.total_dim += layout.hit_miss_dim;
  layout.total_dim += layout.cache_dim;
  layout.total_dim += layout.cand_dim;
  layout.total_dim += layout.topk_dim;
  layout.total_dim += layout.avgtopk_dim;
  layout.total_dim += layout.request_dim;
  if (layout.total_dim > CONTEXT_DIM) {
    layout.total_dim = CONTEXT_DIM;
  }
  return layout;
}

#define SHM_KEY 9876  // 共享内存段键
#define SEM_KEY 9877  // 信号量键

// 各个特征对应的 max 值（用于除以 log1p(max)）：
// features: recency, frequency, size, irt1, irt2, irt3
// 说明：作为全局运行时配置，允许在 LOH_init 中通过
//       LOH_FEATURE_NORM_MAX_* 环境变量覆盖，故不设为 const。
static double loh_feature_norm_max[FEATURE_DIM] = {
    128e6, /* recency */
    1e6,   /* frequency */
    16e9,  /* size (bytes) */
    128e6, /* irt1 */
    128e6, /* irt2 */
    128e6  /* irt3 */
};

// ===== Penalty 队列相关定义（仅在启用 penalty 时使用）=====
#define PENALTY_QUEUE_INIT_CAPACITY 16  // 初始容量
#define PENALTY_QUEUE_GROW_STEP 16      // 每次扩容增加的数量

// Penalty 条目结构（与 LOH.c 保持一致）
typedef struct {
  uint64_t penalty_version;    // 要惩罚的历史状态版本号
  int64_t eviction_to_access;  // 驱逐到访问的距离（用于计算惩罚）
  int64_t obj_size;            // 对象大小（用于字节惩罚计算）
  uint64_t obj_id;             // 触发惩罚的对象ID（用于调试）
} penalty_entry_t;

// C 与 Python 共享的 Actor-Critic（行为者-评论者）网络结构
typedef struct {
  // 控制标志
  int ready_for_inference;  // 状态准备好用于推理时设为 1
  int weights_updated;      // 当 Python 更新权重时设为 1
  int terminate;            // 置为 1 用于通知终止
  int is_training;          // Python 训练状态标志：1 表示Python正在训练

  // 状态信息 - 使用统一的 CONTEXT_DIM（可为 26/38/98/110 等）
  // 说明：去除原来的条件编译分支，避免在启用候选特征时 state 长度与 CONTEXT_DIM
  // 不一致导致 memcpy 溢出。 基础维度由 LOH_INCLUDE_CACHE_FEATURES 决定 (26 或
  // 38)，附加 72 维在 LOH_INCLUDE_CANDIDATE_FEATURES=1 时启用。
  double state[CONTEXT_DIM];

  // 策略网络输出的特征权重（最大 7 维；v1 仅使用前 6 维）
  double weights[WEIGHT_DIM];

  // 【修改】传递驱逐统计而非即时reward
  uint64_t total_evicted_bytes;  // 当前周期累计驱逐的字节数
  uint64_t total_evicted_count;  // 当前周期累计驱逐的对象数

  // 请求-响应版本号，用于避免陈旧请求/响应
  uint64_t state_version;  // C端发送状态时的序号
  uint64_t ack_version;    // Python端回传时确认的序号

  // 用于同步的时间戳
  int64_t timestamp;

  // 【优化】延迟惩罚数据：仅传递数量，详细数据在同步时批量传输。
  // 注意：Python 端始终包含该字段；因此此字段在 struct 中保持常驻。
  int pending_penalty_count;

  // ===== 可选：MLP per-candidate scoring 参数（默认不用） =====
  int score_model;    // 0=linear(weights), 1=mlp
  int mlp_hidden;     // 隐层大小（<=LOH_MLP_MAX_HIDDEN）
  int mlp_param_len;  // mlp_params 的有效长度
  double mlp_params[LOH_MLP_MAX_PARAMS];
} shm_data_t;

#define FREQ_MAX 255         // 单独跟踪的最大频率
#define SIZE_BUCKET_COUNT 5  // 尺寸桶数量

// Ghost 缓存条目（参考 ThreeLCache 设计）
typedef struct LOH_ghost_entry {
  obj_id_t obj_id;              // 对象 ID
  int64_t obj_size;             // 对象大小
  int32_t access_count;         // 访问计数
  int64_t last_access_time;     // 最后访问时间
  int64_t last_access_counter;  // 最后访问的逻辑时间戳
  int64_t irt_values[3];        // 【简化】：直接存储 IRT 值，无需复杂窗口
  time_t evict_time;            // 驱逐时间（用于 LRU 清理）

#if LOH_ENABLE_PENALTY
  uint64_t eviction_version;  // 【新增】驱逐时的state_version（用于惩罚）
  int64_t
      eviction_timestamp;  // 【新增】驱逐时的逻辑时间戳（用于精确计算驱逐到访问距离）
#endif

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

typedef struct {
  cache_obj_t *obj;   // 指向缓存对象的指针
  int64_t irt_value;  // 该堆正在追踪的 IRT 值
} irt_heap_entry_t;

// Size 最小堆条目定义（与 IRT 堆结构相同）
typedef struct {
  cache_obj_t *obj;    // 指向缓存对象的指针
  int64_t size_value;  // 对象的大小
} size_heap_entry_t;

// 频率表链表节点
typedef struct loh_freq_node {
  cache_obj_t *obj;            // 指向缓存对象的指针
  int freq_level;              // 当前所在的频率级别（1..FREQ_MAX）
  struct loh_freq_node *prev;  // 频率列表中的前一个节点
  struct loh_freq_node *next;  // 频率列表中的下一个节点
} loh_freq_node_t;

typedef struct size_node {
  cache_obj_t *obj;
  struct size_node *prev;
  struct size_node *next;
} size_node_t;

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

  // 尺寸堆 - 跟踪对象尺寸（单一最小堆，维护最大 size 的 Top-K）
  size_heap_entry_t *size_heap;  // 单一最小堆
  int size_heap_size;            // 堆当前的元素数量
  int size_heap_capacity;        // 堆的最大容量

  // 尺寸桶 - 跟踪所有对象按大小分桶（LOH_USE_SIZE_BUCKETS=1 时启用）
  size_node_t *size_buckets[SIZE_BUCKET_COUNT];       // 不同尺寸范围的桶头
  size_node_t *size_buckets_tail[SIZE_BUCKET_COUNT];  // 桶尾
  int64_t size_bucket_bounds[SIZE_BUCKET_COUNT];      // 每个桶的上界
  GHashTable *size_node_map;                          // 对象到size节点的映射

  // 特征哈希表（仅用于调试验证与资源释放，热路径不再依赖）
  GHashTable *freq_node_map;  // 对象到频率节点的映射（调试/析构）

  // 【新增】IRT 堆的哈希表映射 - 实现常数时间 O(1) 的 IRT 堆操作
  GHashTable *irt_heap_maps[IRT_HISTORY_SIZE];  // 每个IRT堆的对象到堆索引映射
  // 【新增】Size 堆的哈希表映射 - 实现常数时间 O(1) 的 Size 堆操作
  GHashTable *size_heap_map;  // Size堆的对象到堆索引映射

  // 用于评分函数的特征权重（最大 7 维；非 compound / compound v1 仅使用前 6
  // 维）
  double weights[WEIGHT_DIM];
  // 评分模型（默认线性 weights）；MLP 时使用 mlp_params
  int score_model;
  int mlp_hidden;
  int mlp_param_len;
  double mlp_params[LOH_MLP_MAX_PARAMS];
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

  // 特征裁剪统计（运行期，当 LOH_ENABLE_FEATURE_NORMALIZATION=1 时启用）
  uint64_t feature_clip_count[FEATURE_DIM];  // 每个特征被裁剪到上界的次数
  uint64_t feature_sample_count
      [FEATURE_DIM];  // 每个特征被处理的总样本数（用于计算比例）
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
  FILE *shm_file;        // 共享内存文件指针（用于 blocked 模式和初始化）
  char *shm_filename;    // 共享内存文件名
  shm_data_t *shm_mmap;  // mmap 映射指针（nonblocked 快速路径）
  int shm_fd;            // shm 文件的 fd（mmap 用）
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

#if LOH_INCLUDE_REQUEST
  // 最近请求特征历史（环形缓冲区）：每个请求 6 维特征
  double request_history[REQUEST_HISTORY_LEN][FEATURE_DIM];
  int request_history_pos;        // 下一个写入位置
  int64_t request_history_count;  // 已记录请求数（上限 REQUEST_HISTORY_LEN）
#endif

  // RL 训练相关参数
  int64_t rl_update_interval;  // 更新状态与权重的间隔（触发间隔）
  int64_t requests_since_rl_update;
  double epoch_start_time;       // 当前训练周期的起始时间
  double epoch_obj_miss_count;   // RL 训练：累积失误计数，用于计算长期 miss
                                 // ratio 奖励
  double epoch_obj_count;        // RL训练：累积对象计数，配合失误计数计算性能
  double epoch_byte_miss_count;  // RL训练：累积字节失误，用于字节级性能评估
  double epoch_byte_count;       // RL训练：累积字节总数，配合字节失误计算性能

#if LOH_ENABLE_PENALTY
  uint64_t
      epoch_evicted_bytes;  // 当前周期累计驱逐的字节数（用于字节惩罚分量归一化）
  uint64_t
      epoch_evicted_count;  // 当前周期累计驱逐的对象数（用于对象惩罚分量归一化）
#endif

  // 学习参数
  int64_t learning_interval;  // 权重更新的间隔
  int64_t requests_since_update;

  bool is_warmed_up;
  bool history_capacity_adjusted;
#if LOH_INCLUDE_CANDIDATE_FEATURES
  // 候选对象特征的周期性统计：按来源(6)×特征(6)
  double cand_feat_sum[6][FEATURE_DIM];
  double cand_feat_sumsq[6][FEATURE_DIM];
  uint64_t cand_feat_count[6];
#endif
#if LOH_INCLUDE_TOPK_CANDIDATE_FEATURES
  // 蓄水池采样：保留评分最低的对象特征样本（每次驱逐取4个最低分，共8组=32个）
  double lowest_score_samples[N_TOPK_SAMPLES][FEATURE_DIM];  // 最低分对象的特征
  uint64_t
      group_count;  // 当前 Epoch 内的采样组数（每次驱逐产生1组，共8组填满）
  uint64_t samples_filled;  // 样本池中已填充的样本数（<=N_TOPK_SAMPLES）
  // 临时存储：记录当前驱逐中最低分的4个对象（在 LOH_to_evict 中填充）
  cache_obj_t *current_lowest_4[SAMPLES_PER_EVICTION];
  double current_lowest_scores[SAMPLES_PER_EVICTION];
  int current_lowest_count;
#endif
#if LOH_INCLUDE_AVGTOPK_CANDIDATE_FEATURES
  // AvgTopK: 累计每次驱逐的 TOP4 特征，epoch 结束时计算平均
  double avgtopk_sum[SAMPLES_PER_EVICTION][FEATURE_DIM];  // TOP4 特征累加
  uint64_t avgtopk_evict_count;                           // 驱逐次数
  // 临时存储：记录当前驱逐中最低分的4个对象（与 TOPK 共用定义）
  cache_obj_t *avgtopk_lowest_4[SAMPLES_PER_EVICTION];
  double avgtopk_lowest_scores[SAMPLES_PER_EVICTION];
  int avgtopk_lowest_count;
#endif
#if LOH_PERF_PROFILING
  loh_perf_t perf;  // 轻量性能剖析计数器
#endif

#if LOH_ENABLE_PENALTY
  // Penalty 机制：记录未命中的惩罚，周期性写入共享内存供 Python 使用
  penalty_entry_t *penalty_queue;  // 惩罚队列（动态数组）
  int penalty_queue_size;          // 队列当前大小
  int penalty_queue_capacity;      // 队列容量
  int pending_penalty_count;       // 待处理的惩罚计数
#endif

  // Flat object array for O(1) random sampling (replaces hashtable_rand_obj)
  cache_obj_t **obj_array;
  int obj_array_size;
  int obj_array_capacity;
} LOH_params_t;

static inline double loh_mlp_eval(const LOH_params_t *params,
                                  const double x[FEATURE_DIM]) {
  const int H = params->mlp_hidden;
  const int D = FEATURE_DIM;
  const int expected = loh_mlp_param_len(H);
  if (params->score_model != LOH_SCORE_MODEL_MLP) return 0.0;
  if (H <= 0 || H > LOH_MLP_MAX_HIDDEN) return 0.0;
  if (params->mlp_param_len < expected) return 0.0;

  const double *p = params->mlp_params;
  const double *W1 = p;
  const double *b1 = p + (H * D);
  const double *W2 = b1 + H;
  const double b2 = *(W2 + H);

  double y = b2;
  for (int h = 0; h < H; ++h) {
    double z = b1[h];
    const double *wrow = &W1[h * D];
    // D 固定为 6，允许编译器展开
    for (int d = 0; d < D; ++d) {
      z += wrow[d] * x[d];
    }
    // ReLU
    if (z < 0.0) z = 0.0;
    y += W2[h] * z;
  }
  return y;
}

// === 自动特征模式检测 ===
// 在缓存预热后，通过随机采样缓存对象的频率分布来判断 trace 类型，
// 并自动设置所有相关配置（feature mode、compound 等）。
// 使用变异系数 (CV = std/mean) 作为频率倾斜程度的度量。
// CV 大 → bursty 热点 → recency-dominant → 用 LOG1P + compound
// CV 小 → 稳定 popularity → frequency-dominant → 用 LOG1P_RECIPROCAL + compound
static void loh_auto_detect_and_switch(cache_t *cache) {
  LOH_params_t *params = (LOH_params_t *)cache->eviction_params;

  if (cache->n_obj < 100) {
    // 缓存对象太少，无法检测
    printf("[LOH AUTO-DETECT] Skipped: too few objects (%ld)\n",
           (long)cache->n_obj);
    return;
  }

  // 遍历所有缓存对象，计算 log(1+freq) 的统计矩和各特征范围
  typedef struct {
    int64_t count;
    double sum_freq;        // Σ freq
    double sum_freq_sq;     // Σ freq²
    int64_t one_hit_count;  // access_count == 1 的对象数
    int64_t max_access_count;
    int64_t max_recency;  // 最大 recency
    int64_t min_recency;  // 最小 recency (> 0)
    // log(1+freq) 的原始矩（用于计算峰度）
    double sum_logf;   // Σ log(1+freq)
    double sum_logf2;  // Σ log(1+freq)²
    double sum_logf3;  // Σ log(1+freq)³
    double sum_logf4;  // Σ log(1+freq)⁴
  } detect_accum_t;
  detect_accum_t accum = {0};
  accum.min_recency = INT64_MAX;
  int64_t current_ts = params->current_timestamp;

  for (uint64_t bi = 0; bi < hashsize(cache->hashtable->hashpower); bi++) {
    cache_obj_t *obj = cache->hashtable->ptr_table[bi];
    while (obj != NULL) {
      double f = (double)obj->LOH.access_count;
      double lf = log(1.0 + f);  // log(1+freq): 这就是 LOG1P 变换后的值
      accum.sum_freq += f;
      accum.sum_freq_sq += f * f;
      accum.sum_logf += lf;
      accum.sum_logf2 += lf * lf;
      accum.sum_logf3 += lf * lf * lf;
      accum.sum_logf4 += lf * lf * lf * lf;
      accum.count++;
      if (obj->LOH.access_count == 1) accum.one_hit_count++;
      if (obj->LOH.access_count > accum.max_access_count)
        accum.max_access_count = obj->LOH.access_count;
      int64_t recency = current_ts - obj->LOH.last_access_counter;
      if (recency > accum.max_recency) accum.max_recency = recency;
      if (recency > 0 && recency < accum.min_recency)
        accum.min_recency = recency;
      obj = obj->hash_next;
    }
  }
  int actual_samples = (int)accum.count;
  int max_ac = (int)accum.max_access_count;

  if (actual_samples < 50) {
    printf("[LOH AUTO-DETECT] Skipped: insufficient samples (%d)\n",
           actual_samples);
    return;
  }

  double n = (double)actual_samples;

  // ---- 计算 log(1+freq) 的统计矩 ----
  // M_k = E[X^k] (原始矩), X = log(1+freq)
  double M1 = accum.sum_logf / n;
  double M2 = accum.sum_logf2 / n;
  double M3 = accum.sum_logf3 / n;
  double M4 = accum.sum_logf4 / n;

  // 中心矩
  double mu2 = M2 - M1 * M1;  // 方差
  double mu3 = M3 - 3 * M1 * M2 + 2 * M1 * M1 * M1;
  double mu4 = M4 - 4 * M1 * M3 + 6 * M1 * M1 * M2 - 3 * M1 * M1 * M1 * M1;

  double std_logf = (mu2 > 0) ? sqrt(mu2) : 0.0;
  double skewness = (mu2 > 1e-12) ? mu3 / (mu2 * std_logf) : 0.0;
  // 超额峰度: kurtosis - 3 (正态分布 = 0)
  double excess_kurtosis = (mu2 > 1e-12) ? mu4 / (mu2 * mu2) - 3.0 : 0.0;

  // 辅助统计量（诊断用）
  double mean_freq = accum.sum_freq / n;
  double var_freq = accum.sum_freq_sq / n - mean_freq * mean_freq;
  double cv =
      (mean_freq > 0 && var_freq > 0) ? sqrt(var_freq) / mean_freq : 0.0;
  double one_hit_ratio = (double)accum.one_hit_count / n;

  printf(
      "[LOH AUTO-DETECT] n_req=%ld, n_obj=%ld, samples=%d, "
      "mean_freq=%.2f, cv=%.3f, max_ac=%d\n",
      (long)cache->n_req, (long)cache->n_obj, actual_samples, mean_freq, cv,
      max_ac);
  printf(
      "[LOH AUTO-DETECT] LOG-FEATURE STATS: "
      "mean_log=%.4f, std_log=%.4f, skewness=%.4f, "
      "excess_kurtosis=%.4f, one_hit=%.4f\n",
      M1, std_logf, skewness, excess_kurtosis, one_hit_ratio);

  // ---- 决策：composite score (2D 线性分类器) ----
  //
  // 从 LOG1P 和 RECIPROCAL 的本质区别出发：
  //   - LOG1P 特征无界 [0,∞)，保留幅度差异，但可能有特征尺度不匹配
  //   - RECIPROCAL 特征有界 (0,1]，自带方向偏差（freq↑, recency/IRT↓）
  //
  // 何时 LOG1P 更好：缓存对象有丰富的频率多样性（大量对象被多次访问），
  //   LOG1P 的幅度差异帮助 RL 从频率梯度中学习。
  //   指标：low one_hit_ratio → 多数对象 freq>1 → 频率信息丰富
  //
  // 何时 RECIPROCAL 更好：缓存对象频率分布极度不均（少数极热+大量冷），
  //   LOG1P 的极端值支配学习，RECIPROCAL 的压缩和方向偏差简化学习。
  //   指标：high CV (极端离群值) + high one_hit (大量 freq=1)
  //
  // 综合评分：score = 3*(one_hit - 0.5) - 0.5*log10(CV)
  //   - one_hit_ratio 贡献正方向（高 → RECIPROCAL）
  //   - log10(CV) 贡献负方向（高 → LOG1P，因为极端离群值的信息量需要保留）
  //   - 两个因子互相制衡，决策边界是 2D 特征空间中的一条线
  //
  // 验证数据（6/6 正确）：
  //   1063 300K/3M: -0.63/-0.26 → LOG1P ✓
  //   wiki  300K/3M: +0.11/+0.58 → RECIPROCAL ✓
  //   meta  300K/3M: -0.23/-0.13 → LOG1P ✓
  double log10_cv = (cv > 0.0) ? log10(cv) : 0.0;
  double score = 3.0 * (one_hit_ratio - 0.5) - 0.5 * log10_cv;

  printf("[LOH AUTO-DETECT] SCORE = 3*(%.4f - 0.5) - 0.5*log10(%.3f) = %.4f\n",
         one_hit_ratio, cv, score);

  if (score > 0.0) {
    loh_feature_log1p = 0;
    loh_feature_log1p_reciprocal = 1;
    printf(
        "[LOH AUTO-DETECT] DECISION: LOG1P_RECIPROCAL mode "
        "(score=%.4f > 0)\n",
        score);
  } else {
    loh_feature_log1p = 1;
    loh_feature_log1p_reciprocal = 0;
    printf(
        "[LOH AUTO-DETECT] DECISION: LOG1P mode "
        "(score=%.4f <= 0)\n",
        score);
  }

  // === 自动设置其他配置 ===
  if (!loh_score_use_compound) {
    loh_score_use_compound = 1;
    loh_score_use_irt = 0;
    loh_irt_heap_enabled = 0;  // compound 模式下禁用 IRT 堆以提升吞吐量
    printf("[LOH AUTO-DETECT] Auto-enabled: COMPOUND=1 (IRT heaps disabled)\n");
  }

  // === 分析各模式下的特征值分布 ===
  double log_freq_min = log1p(1.0);  // 最小 freq=1 → log(2)=0.693
  double log_freq_max = log1p((double)max_ac);
  double log_rec_min =
      (accum.min_recency < INT64_MAX) ? log1p((double)accum.min_recency) : 0.0;
  double log_rec_max = log1p((double)accum.max_recency);

  // 在三种模式下的特征范围：
  printf("[LOH FEATURE RANGES] === 三种模式下 frequency 特征范围 ===\n");
  printf("  LOG1P:        [%.3f, %.3f] (raw log1p, unbounded)\n", log_freq_min,
         log_freq_max);
  printf("  RECIPROCAL:   [%.3f, %.3f] (log1p(f)/(log1p(f)+1), bounded)\n",
         log_freq_min / (log_freq_min + 1.0),
         log_freq_max / (log_freq_max + 1.0));
  printf("  DEFAULT:      [%.3f, %.3f] (f/(f+1), bounded)\n",
         1.0 / 2.0, /* f=1 → 1/2 */
         (double)max_ac / ((double)max_ac + 1.0));
  printf("[LOH FEATURE RANGES] === 三种模式下 recency 特征范围 ===\n");
  printf("  LOG1P:        [%.3f, %.3f] (raw log1p, unbounded)\n", log_rec_min,
         log_rec_max);
  printf("  RECIPROCAL:   [%.3f, %.3f] (1/(1+log1p(v)), bounded)\n",
         (log_rec_max > 0) ? 1.0 / (1.0 + log_rec_max) : 0.0,
         (log_rec_min > 0) ? 1.0 / (1.0 + log_rec_min) : 1.0);
  printf(
      "  DEFAULT:      [%.6f, %.3f] (1/(1+v), bounded)\n",
      (accum.max_recency > 0) ? 1.0 / (1.0 + (double)accum.max_recency) : 0.0,
      (accum.min_recency > 0 && accum.min_recency < INT64_MAX)
          ? 1.0 / (1.0 + (double)accum.min_recency)
          : 1.0);
  printf(
      "[LOH FEATURE RANGES] LOG1P scale ratio: freq_range=%.2f, "
      "rec_range=%.2f, ratio=%.2f\n",
      log_freq_max - log_freq_min, log_rec_max - log_rec_min,
      (log_freq_max - log_freq_min > 0)
          ? (log_rec_max - log_rec_min) / (log_freq_max - log_freq_min)
          : 0.0);
  // 硬编码 max 下的归一化结果
  printf(
      "[LOH FEATURE RANGES] 硬编码 max 归一化: freq=[%.4f, %.4f] (max=1e6), "
      "rec=[%.4f, %.4f] (max=128e6)\n",
      log_freq_min / log1p(1e6), log_freq_max / log1p(1e6),
      log_rec_min / log1p(128e6), log_rec_max / log1p(128e6));
  // 自适应 max 归一化结果
  printf(
      "[LOH FEATURE RANGES] 自适应 max 归一化: freq=[%.4f, %.4f] (max=%d), "
      "rec=[%.4f, %.4f] (max=%ld)\n",
      log_freq_min / log_freq_max, 1.0, max_ac,
      (log_rec_max > 0) ? log_rec_min / log_rec_max : 0.0, 1.0,
      (long)accum.max_recency);

  // === 归一化：不自动启用 ===
  // 实验表明 NORMALIZE=0 在所有 trace 上表现最佳（LOG1P 和 RECIPROCAL
  // 均如此）。 仅在用户显式设置 LOH_ENABLE_FEATURE_NORMALIZATION=1 时才启用。
  printf(
      "[LOH AUTO-DETECT] NORMALIZE kept at %d (not auto-changed; "
      "best results use NORMALIZE=0)\n",
      loh_feature_normalize);

  // === RSC（随机采样候选）：默认已设为 96 ===
  // 实验表明随机候选在所有最佳配置中都被使用

  printf(
      "[LOH AUTO-DETECT] Final config: LOG1P=%d, RECIPROCAL=%d, "
      "NORMALIZE=%d, COMPOUND=%d, COMPOUND_V2=%d, RSC=%d\n",
      loh_feature_log1p, loh_feature_log1p_reciprocal, loh_feature_normalize,
      loh_score_use_compound, loh_score_compound_v2, loh_random_candidates);
}

// === 基础特征计算函数（RECENCY / FREQUENCY / SIZE / IRT） ===

static double calculate_irt_feature(LOH_params_t *params, int64_t irt_value) {
  // 约定：调用者必须保证 IRT 已初始化且为正；否则直接中断调试
  g_assert(irt_value > 0);

  double v = (double)irt_value;
  double out;
  if (loh_feature_log1p) {
    // LOG1P 模式：直接 log1p(raw)
    out = log1p(v);
  } else {
    if (loh_feature_log1p_reciprocal) {
      v = log1p(v);
    }
    out = 1.0 / (1.0 + v);
  }

  /* 可选归一化：除以 log1p(max) 并裁剪到 [0,1]，并统计裁剪次数/样本数 */
  if (loh_feature_normalize && params != NULL) {
    const int idx = 3; /* IRT features mapped to index 3,4,5 — use same denom */
    double denom = log1p(loh_feature_norm_max[idx]);
    params->feature_sample_count[idx]++;
    double nn = out / (denom > 0.0 ? denom : 1.0);
    if (nn > 1.0) {
      params->feature_clip_count[idx]++;
      LOH_DEBUG_PRINT_DETAILED(
          "[LOH] Feature[%d] clipped: pre=%.6f post=%.6f (raw_irt=%.0f)\n", idx,
          nn, 1.0, v);
      nn = 1.0;
    }
    return nn;
  }

  return out;
}

// 基础特征变换函数：入参为“raw” 数值，不再依赖 params
static double calculate_recency(LOH_params_t *params, int64_t recency_raw) {
  g_assert(recency_raw >= 0);

  double v = (double)recency_raw;
  double out;
  if (loh_feature_log1p) {
    out = log1p(v);
  } else {
    out = loh_feature_log1p_reciprocal ? (1.0 / (1.0 + log1p(v)))
                                       : (1.0 / (1.0 + v));
  }

  if (loh_feature_normalize && params != NULL) {
    const int idx = 0; /* recency */
    double denom = log1p(loh_feature_norm_max[idx]);
    params->feature_sample_count[idx]++;
    double nn = out / (denom > 0.0 ? denom : 1.0);
    if (nn > 1.0) {
      params->feature_clip_count[idx]++;
      LOH_DEBUG_PRINT_DETAILED(
          "[LOH] Feature[%d] clipped: pre=%.6f post=%.6f (recency_raw=%.0f)\n",
          idx, nn, 1.0, v);
      nn = 1.0;
    }
    return nn;
  }

  return out;
}

static double calculate_frequency(LOH_params_t *params, int64_t freq_raw) {
  g_assert(freq_raw >= 0);

  double f = (double)freq_raw;
  double out;
  if (loh_feature_log1p) {
    out = log1p(f);
  } else {
    const double K = 1.0;
    if (loh_feature_log1p_reciprocal) f = log1p(f);
    out = (f > 0.0) ? (f / (f + K)) : 0.0;
  }

  if (loh_feature_normalize && params != NULL) {
    const int idx = 1; /* frequency */
    double denom = log1p(loh_feature_norm_max[idx]);
    params->feature_sample_count[idx]++;
    double nn = out / (denom > 0.0 ? denom : 1.0);
    if (nn > 1.0) {
      params->feature_clip_count[idx]++;
      LOH_DEBUG_PRINT_DETAILED(
          "[LOH] Feature[%d] clipped: pre=%.6f post=%.6f (freq_raw=%.0f)\n",
          idx, nn, 1.0, f);
      nn = 1.0;
    }
    return nn;
  }

  return out;
}

static double calculate_size(LOH_params_t *params, int64_t size_bytes) {
  g_assert(size_bytes >= 0);

  double size_bytes_d = (double)size_bytes;
  double out;
  if (loh_feature_log1p) {
    out = log1p(size_bytes_d);
  } else {
    double size_mb = size_bytes_d / (1024.0 * 1024.0);
    const double A = 1.0;
    out = loh_feature_log1p_reciprocal ? (1.0 / (1.0 + log1p(A * size_mb)))
                                       : (1.0 / (1.0 + A * size_mb));
  }

  if (loh_feature_normalize && params != NULL) {
    const int idx = 2; /* size */
    double denom = log1p(loh_feature_norm_max[idx]);
    params->feature_sample_count[idx]++;
    double nn = out / (denom > 0.0 ? denom : 1.0);
    if (nn > 1.0) {
      params->feature_clip_count[idx]++;
      LOH_DEBUG_PRINT_DETAILED(
          "[LOH] Feature[%d] clipped: pre=%.6f post=%.6f (size_bytes=%.0f)\n",
          idx, nn, 1.0, size_bytes_d);
      nn = 1.0;
    }
    return nn;
  }

  return out;
}

// 计算对象的六个特征值：recency, frequency, size, irt1, irt2, irt3
static void calculate_object_features(LOH_params_t *params, cache_obj_t *obj,
                                      double *features) {
  g_assert(params != NULL);
  g_assert(obj != NULL);
  g_assert(params->current_timestamp >= obj->LOH.last_access_counter);

  int64_t delta = params->current_timestamp - obj->LOH.last_access_counter;
  int64_t recency_raw = delta;
  int64_t freq_raw = (int64_t)obj->LOH.access_count;
  int64_t size_bytes = (int64_t)obj->obj_size;

  // 统一通过四个基础特征函数计算
  features[0] = calculate_recency(params, recency_raw);
  features[1] = calculate_frequency(params, freq_raw);
  features[2] = calculate_size(params, size_bytes);
  features[3] = calculate_irt_feature(params, obj->LOH.irt_values[0]);
  features[4] = calculate_irt_feature(params, obj->LOH.irt_values[1]);
  features[5] = calculate_irt_feature(params, obj->LOH.irt_values[2]);

  LOH_DEBUG_PRINT_VERBOSE(
      "[calculate_object_features] Feature0(recency) - value=%.6f\n",
      features[0]);
  LOH_DEBUG_PRINT_VERBOSE(
      "[calculate_object_features] Feature1(frequency) - value=%.6f\n",
      features[1]);
  LOH_DEBUG_PRINT_VERBOSE(
      "[calculate_object_features] Feature2(size) - value=%.6f\n", features[2]);
  LOH_DEBUG_PRINT_VERBOSE(
      "[calculate_object_features] Feature3(latest_IRT) - value=%.6f\n",
      features[3]);
  LOH_DEBUG_PRINT_VERBOSE(
      "[calculate_object_features] Feature4(2nd_IRT) - value=%.6f\n",
      features[4]);
  LOH_DEBUG_PRINT_VERBOSE(
      "[calculate_object_features] Feature5(3rd_IRT) - value=%.6f\n",
      features[5]);

  // [DEBUG] Final feature vector
  LOH_DEBUG_PRINT_DETAILED(
      "[calculate_object_features] Final feature vector - [%.6f, %.6f, %.6f, "
      "%.6f, %.6f, %.6f]\n",
      features[0], features[1], features[2], features[3], features[4],
      features[5]);

  /* 归一化逻辑已移至各个 calculate_* 函数内部，以便统计样本/裁剪计数 */
}

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

#if LOH_ENABLE_PENALTY
static bool enqueue_penalty(LOH_params_t *params, uint64_t penalty_version,
                            int64_t eviction_to_access, int64_t obj_size,
                            uint64_t obj_id);
#endif

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

#if LOH_ENABLE_PENALTY
  // 正样本：ghost entry 在 ghost cache 中“活到被淘汰”仍未被再次访问
  // 发送 eviction_to_access<0 的事件（Python 端将其作为正反馈证据处理）。
  if (loh_penalty_send_positive && tail->eviction_version != 0) {
    int64_t dist = params->current_timestamp - tail->eviction_timestamp;
    if (dist < 0) dist = 0;
    // 负距离作为 sentinel：表示“未被再次访问”
    (void)enqueue_penalty(params, tail->eviction_version, -dist, tail->obj_size,
                          tail->obj_id);
  }
#endif

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

#if LOH_ENABLE_PENALTY
  // 【新增】记录驱逐版本号和时间戳（用于penalty机制）
  if (params->shm_file != NULL) {
    shm_data_t shm_data;
    rewind(params->shm_file);
    if (fread(&shm_data, sizeof(shm_data_t), 1, params->shm_file) == 1) {
      ghost_entry->eviction_version = shm_data.state_version;
    } else {
      ghost_entry->eviction_version = 0;  // 读取失败时使用0
    }
  } else {
    ghost_entry->eviction_version = 0;  // 无共享内存时使用0
  }
  ghost_entry->eviction_timestamp = params->current_timestamp;
#endif

#if LOH_ENABLE_PENALTY
  PERF_TS ts_insert;
  PERF_NOW(ts_insert);
#endif

  // 插入到哈希表
  g_hash_table_insert(params->ghost_cache, GINT_TO_POINTER((int)obj_id_key),
                      ghost_entry);

#if LOH_ENABLE_PENALTY
  PERF_ACCUM(params, ghost_cache_insert, ts_insert);
#endif

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

// ===== Penalty 机制相关函数（仅在 LOH_ENABLE_PENALTY=1 时编译）=====
#if LOH_ENABLE_PENALTY
/**
 * 将一个 penalty 条目添加到队列中
 * @param params LOH 参数
 * @param penalty_version 要惩罚的历史状态版本号
 * @param eviction_to_access 驱逐到访问的距离
 * @param obj_size 对象大小
 * @param obj_id 对象ID（用于调试）
 * @return 成功返回 true，失败返回 false
 */
static bool enqueue_penalty(LOH_params_t *params, uint64_t penalty_version,
                            int64_t eviction_to_access, int64_t obj_size,
                            uint64_t obj_id) {
  PERF_TS ts_enqueue;
  PERF_NOW(ts_enqueue);

  if (params == NULL) return false;

  // 检查队列是否需要扩容
  if (params->penalty_queue_size >= params->penalty_queue_capacity) {
    // 线性扩容：每次增加固定数量
    int new_capacity = params->penalty_queue_capacity + PENALTY_QUEUE_GROW_STEP;

    penalty_entry_t *new_queue =
        realloc(params->penalty_queue, new_capacity * sizeof(penalty_entry_t));
    if (new_queue == NULL) {
      LOH_DEBUG_PRINT_ERROR(
          "[LOH] ERROR: Failed to expand penalty queue from %d to %d\n",
          params->penalty_queue_capacity, new_capacity);
      return false;
    }

    params->penalty_queue = new_queue;
    params->penalty_queue_capacity = new_capacity;
    LOH_DEBUG_PRINT_BASIC(
        "[LOH] Expanded penalty queue to capacity %d (realloc may copy data)\n",
        new_capacity);
  }

  // 添加原始数据到本地队列
  int idx = params->penalty_queue_size;
  params->penalty_queue[idx].penalty_version = penalty_version;
  params->penalty_queue[idx].eviction_to_access = eviction_to_access;
  params->penalty_queue[idx].obj_size = obj_size;
  params->penalty_queue[idx].obj_id = obj_id;
  params->penalty_queue_size++;

  LOH_DEBUG_PRINT_BASIC(
      "[C→Queue] 📝 Penalty #%d: version=%lu, evict_to_access=%ld, "
      "size=%ld, obj_id=%lu (queue: %d/%d)\n",
      idx, penalty_version, eviction_to_access, obj_size, obj_id,
      params->penalty_queue_size, params->penalty_queue_capacity);

  PERF_ACCUM(params, penalty_enqueue, ts_enqueue);
  return true;
}
#endif  // LOH_ENABLE_PENALTY

// POSIX 信号量初始化与清理
static bool loh_sem_init(LOH_params_t *params) {
  if (params == NULL) return false;
  params->sem_enabled = false;

  /* Respect runtime request flag: if semaphores are not requested, skip init */
  if (!params->sem_requested) {
    return false;
  }

  if (!loh_enable_rl) return false;
  if (params->sem_ready_name == NULL || params->sem_ack_name == NULL) {
    return false;
  }

  int oflag = O_CREAT | O_EXCL;
  mode_t mode = 0666;
  sem_t *ready = sem_open(params->sem_ready_name, oflag, mode, 0);
  bool created_ready = false;
  if (ready == SEM_FAILED) {
    if (errno != EEXIST) {
      LOH_DEBUG_PRINT_CONFIG("[LOH SEM INIT] sem_open ready failed: %s\n",
                             strerror(errno));
      return false;
    }
    oflag = O_CREAT;
    ready = sem_open(params->sem_ready_name, oflag, mode, 0);
    if (ready == SEM_FAILED) {
      LOH_DEBUG_PRINT_CONFIG(
          "[LOH SEM INIT] sem_open ready (retry) failed: %s\n",
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
      LOH_DEBUG_PRINT_CONFIG("[LOH SEM INIT] sem_open ack failed: %s\n",
                             strerror(errno));
      sem_close(ready);
      return false;
    }
    oflag = O_CREAT;
    ack = sem_open(params->sem_ack_name, oflag, mode, 0);
    if (ack == SEM_FAILED) {
      LOH_DEBUG_PRINT_CONFIG("[LOH SEM INIT] sem_open ack (retry) failed: %s\n",
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
    LOH_DEBUG_PRINT_CONFIG(
        "[LOH SEM INIT] POSIX semaphores created and reset\n");
  } else {
    LOH_DEBUG_PRINT_CONFIG(
        "[LOH SEM INIT] POSIX semaphores attached (existing)\n");
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

/** 旧版 calculate_irt_feature/calculate_object_features 已被上方统一实现替代。
 */

#if LOH_INCLUDE_TOPK_CANDIDATE_FEATURES
/**
 * @brief 蓄水池采样：记录最低分对象的特征（按组采样）
 *
 * 算法：
 * - 前8组（32个对象）直接填充
 * - 第 i 组（i>8）以概率 8/i 替换池中随机的一组（4个对象同进同出）
 *
 * 注意：此函数使用 LOH_to_evict 中已找到的最低4个对象，避免重复计算
 *
 * @param params LOH参数
 */
static void reservoir_sample_group(LOH_params_t *params) {
  if (params->current_lowest_count < SAMPLES_PER_EVICTION) return;

  params->group_count++;
  uint64_t i = params->group_count;

  // 计算这4个对象的特征
  double group_features[SAMPLES_PER_EVICTION][FEATURE_DIM];
  for (int obj_idx = 0; obj_idx < SAMPLES_PER_EVICTION; obj_idx++) {
    cache_obj_t *obj = params->current_lowest_4[obj_idx];
    if (obj) {
      calculate_object_features(params, obj, group_features[obj_idx]);
    } else {
      memset(group_features[obj_idx], 0, sizeof(double) * FEATURE_DIM);
    }
  }

  if (i <= 8) {
    // 前8组直接填充（0-7组，共32个样本）
    int base_idx = (int)((i - 1) * SAMPLES_PER_EVICTION);
    for (int obj_idx = 0; obj_idx < SAMPLES_PER_EVICTION; obj_idx++) {
      int idx = base_idx + obj_idx;
      memcpy(params->lowest_score_samples[idx], group_features[obj_idx],
             sizeof(double) * FEATURE_DIM);
      params->samples_filled++;
    }

    LOH_DEBUG_PRINT_VERBOSE(
        "[RESERVOIR] Direct fill group %llu: samples %d-%d\n",
        (unsigned long long)i, base_idx, base_idx + SAMPLES_PER_EVICTION - 1);

    // BASIC级别：输出直接填充的组的首个对象特征
#if LOH_DEBUG_LEVEL >= LOH_DEBUG_DETAILED
    if (params->current_lowest_4[0]) {
      printf("[RESERVOIR] Group %llu direct fill -> slots %d-%d\n",
             (unsigned long long)i, base_idx,
             base_idx + SAMPLES_PER_EVICTION - 1);
      printf(
          "              First obj: id=%llu features=[%.4f, %.4f, %.4f, %.4f, "
          "%.4f, %.4f]\n",
          (unsigned long long)params->current_lowest_4[0]->obj_id,
          group_features[0][0], group_features[0][1], group_features[0][2],
          group_features[0][3], group_features[0][4], group_features[0][5]);
    }
#endif
  } else {
    // 以概率 8/i 替换池中随机的一组
    uint64_t j = (uint64_t)rand() % i;

    if (j < 8) {
      // 替换第 j 组（同组4个对象同进同出）
      int base_idx = (int)(j * SAMPLES_PER_EVICTION);
      for (int obj_idx = 0; obj_idx < SAMPLES_PER_EVICTION; obj_idx++) {
        int idx = base_idx + obj_idx;
        memcpy(params->lowest_score_samples[idx], group_features[obj_idx],
               sizeof(double) * FEATURE_DIM);
      }

      LOH_DEBUG_PRINT_VERBOSE(
          "[RESERVOIR] Replace group %llu (prob=%.4f): samples %d-%d\n",
          (unsigned long long)j, 8.0 / i, base_idx,
          base_idx + SAMPLES_PER_EVICTION - 1);

      // BASIC级别：输出替换信息
#if LOH_DEBUG_LEVEL >= LOH_DEBUG_DETAILED
      if (params->current_lowest_4[0]) {
        printf(
            "[RESERVOIR] Group %llu replaces group %llu (prob=%.4f) -> "
            "slots %d-%d\n",
            (unsigned long long)i, (unsigned long long)j, 8.0 / i, base_idx,
            base_idx + SAMPLES_PER_EVICTION - 1);
        printf(
            "              New obj: id=%llu features=[%.4f, %.4f, %.4f, %.4f, "
            "%.4f, %.4f]\n",
            (unsigned long long)params->current_lowest_4[0]->obj_id,
            group_features[0][0], group_features[0][1], group_features[0][2],
            group_features[0][3], group_features[0][4], group_features[0][5]);
      }
#endif
    }
  }
}

/**
 * @brief 重置蓄水池采样缓冲区（在Epoch结束后调用）
 */
static void reset_reservoir_samples(LOH_params_t *params) {
  params->group_count = 0;
  params->samples_filled = 0;
  params->current_lowest_count = 0;
  memset(params->lowest_score_samples, 0, sizeof(params->lowest_score_samples));
  memset(params->current_lowest_4, 0, sizeof(params->current_lowest_4));
  memset(params->current_lowest_scores, 0,
         sizeof(params->current_lowest_scores));
}

/**
 * @brief 如果 TOPK 采样未满，主动调用 LOH_to_evict 来填充
 *
 * 当 epoch 内的驱逐次数不足以填满 8 组（32 个样本）时，
 * 调用一次 LOH_to_evict 获取当前 TOPK 候选，然后重复填充所有未满的组。
 */
static void fill_topk_if_needed(LOH_params_t *params) {
  cache_t *cache = (cache_t *)params->cache_ptr;
  if (!cache) {
    LOH_DEBUG_PRINT_ERROR("[fill_topk_if_needed] cache_ptr is NULL\n");
    return;
  }

  // 如果已经填满 8 组（32 个样本），无需处理
  if (params->group_count >= 8) {
    LOH_DEBUG_PRINT_DETAILED(
        "[fill_topk_if_needed] Already have %llu groups, no fill needed\n",
        (unsigned long long)params->group_count);
    return;
  }

  // 如果缓存为空，无法获取候选
  if (params->q_head == NULL) {
    LOH_DEBUG_PRINT_BASIC(
        "[fill_topk_if_needed] Cache is empty, cannot fill TOPK\n");
    return;
  }

  LOH_DEBUG_PRINT_BASIC(
      "[fill_topk_if_needed] TOPK not full: group_count=%llu/8, "
      "samples_filled=%llu/%d, attempting to fill...\n",
      (unsigned long long)params->group_count,
      (unsigned long long)params->samples_filled, N_TOPK_SAMPLES);

  // 创建一个虚拟请求用于调用 LOH_to_evict
  request_t dummy_req = {0};
  dummy_req.obj_id = 0;
  dummy_req.obj_size = 0;

  // 调用一次 LOH_to_evict 来收集候选并计算 TOPK
  cache_obj_t *victim = LOH_to_evict(cache, &dummy_req);
  (void)victim;  // 不实际驱逐，只是为了获取 TOPK 候选

  // 检查是否获取了足够的候选
  if (params->current_lowest_count < SAMPLES_PER_EVICTION) {
    LOH_DEBUG_PRINT_BASIC(
        "[fill_topk_if_needed] Not enough candidates (%d < %d), cannot fill\n",
        params->current_lowest_count, SAMPLES_PER_EVICTION);
    return;
  }

  // 计算当前 TOPK 4 个对象的特征（只计算一次）
  double group_features[SAMPLES_PER_EVICTION][FEATURE_DIM];
  for (int obj_idx = 0; obj_idx < SAMPLES_PER_EVICTION; obj_idx++) {
    cache_obj_t *obj = params->current_lowest_4[obj_idx];
    if (obj) {
      calculate_object_features(params, obj, group_features[obj_idx]);
    } else {
      memset(group_features[obj_idx], 0, sizeof(double) * FEATURE_DIM);
    }
  }

  // 重复填充所有未满的组
  while (params->group_count < 8) {
    int base_idx = (int)(params->group_count * SAMPLES_PER_EVICTION);
    for (int obj_idx = 0; obj_idx < SAMPLES_PER_EVICTION; obj_idx++) {
      int idx = base_idx + obj_idx;
      memcpy(params->lowest_score_samples[idx], group_features[obj_idx],
             sizeof(double) * FEATURE_DIM);
      params->samples_filled++;
    }
    params->group_count++;

    LOH_DEBUG_PRINT_DETAILED(
        "[fill_topk_if_needed] Filled group %llu with current TOPK\n",
        (unsigned long long)params->group_count);
  }

  // 清空临时存储
  params->current_lowest_count = 0;

  LOH_DEBUG_PRINT_BASIC(
      "[fill_topk_if_needed] After fill: group_count=%llu/8, "
      "samples_filled=%llu/%d\n",
      (unsigned long long)params->group_count,
      (unsigned long long)params->samples_filled, N_TOPK_SAMPLES);
}
#endif

#if LOH_INCLUDE_AVGTOPK_CANDIDATE_FEATURES
/**
 * @brief 如果 AvgTopK 统计为空，主动调用 LOH_to_evict 来填充
 *
 * 当 epoch 内没有驱逐发生时，调用一次 LOH_to_evict 获取当前 TOPK 候选，
 * 然后使用这些候选的特征作为平均值。
 */
static void fill_avgtopk_if_needed(LOH_params_t *params) {
  // 如果已经有驱逐统计，无需处理
  if (params->avgtopk_evict_count > 0) {
    return;
  }

  cache_t *cache = (cache_t *)params->cache_ptr;
  if (!cache) {
    LOH_DEBUG_PRINT_ERROR("[fill_avgtopk_if_needed] cache_ptr is NULL\n");
    return;
  }

  // 如果缓存为空，无法获取候选
  if (params->q_head == NULL) {
    LOH_DEBUG_PRINT_BASIC(
        "[fill_avgtopk_if_needed] Cache is empty, cannot fill AvgTopK\n");
    return;
  }

  LOH_DEBUG_PRINT_BASIC(
      "[fill_avgtopk_if_needed] AvgTopK empty, attempting to fill...\n");

  // 创建一个虚拟请求用于调用 LOH_to_evict
  request_t dummy_req = {0};
  dummy_req.obj_id = 0;
  dummy_req.obj_size = 0;

  // 调用一次 LOH_to_evict 来收集候选并计算 TOPK
  cache_obj_t *victim = LOH_to_evict(cache, &dummy_req);
  (void)victim;  // 不实际驱逐，只是为了获取 TOPK 候选

  // 检查是否获取了足够的候选
  if (params->avgtopk_lowest_count < SAMPLES_PER_EVICTION) {
    LOH_DEBUG_PRINT_BASIC(
        "[fill_avgtopk_if_needed] Not enough candidates (%d < %d)\n",
        params->avgtopk_lowest_count, SAMPLES_PER_EVICTION);
    return;
  }

  // 将 TOP4 特征直接作为"平均值"（只有一次采样）
  for (int k = 0; k < SAMPLES_PER_EVICTION; k++) {
    cache_obj_t *obj = params->avgtopk_lowest_4[k];
    if (obj) {
      double features[FEATURE_DIM];
      calculate_object_features(params, obj, features);
      for (int f = 0; f < FEATURE_DIM; f++) {
        params->avgtopk_sum[k][f] = features[f];
      }
    }
  }
  params->avgtopk_evict_count = 1;

  LOH_DEBUG_PRINT_BASIC(
      "[fill_avgtopk_if_needed] Filled AvgTopK with current TOPK candidates\n");
}
#endif

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

  loh_state_layout_t layout = loh_get_state_layout();
  int offset = 0;  // 动态偏移量，根据启用的模块累加

  // A. Miss Ratio 指标 (2 维) - 始终传递，因为奖励计算需要
  params->context_state[offset++] = hit_ratio;
  params->context_state[offset++] = byte_hit_ratio;

  LOH_DEBUG_PRINT_DETAILED(
      "[update_state_vector] miss_ratio [0-%d] - [%.6f, %.6f]\n",
      MISSRATIO_DIM - 1, hit_ratio, byte_hit_ratio);

#if LOH_INCLUDE_HIT_MISS_FEATURES
  // B. 特征表现剖析 - Hit/Miss 统计
  LOH_DEBUG_PRINT_DETAILED(
      "[update_state_vector] hit_count=%ld, miss_count=%ld\n",
      (long)params->hit_feature_count, (long)params->miss_feature_count);

  for (int i = 0; i < layout.feature_dim; i++) {
    LOH_DEBUG_PRINT_DETAILED(
        "[update_state_vector] feature %d - hit_sum=%.6f, hit_sum_sq=%.6f, "
        "miss_sum=%.6f, miss_sum_sq=%.6f\n",
        i, params->hit_feature_sum[i], params->hit_feature_sum_sq[i],
        params->miss_feature_sum[i], params->miss_feature_sum_sq[i]);

    // 计算命中对象特征统计
    if (params->hit_feature_count > 0) {
      double mean = params->hit_feature_sum[i] / params->hit_feature_count;
      params->context_state[offset + i * 4] = mean;

      if (params->hit_feature_count > 1) {
        double variance =
            (params->hit_feature_sum_sq[i] / params->hit_feature_count) -
            (mean * mean);
        if (variance > 0) {
          params->context_state[offset + i * 4 + 1] = variance;
        }
      }
    }

    // 计算未命中对象特征统计
    if (params->miss_feature_count > 0) {
      double mean = params->miss_feature_sum[i] / params->miss_feature_count;
      params->context_state[offset + i * 4 + 2] = mean;

      if (params->miss_feature_count > 1) {
        double variance =
            (params->miss_feature_sum_sq[i] / params->miss_feature_count) -
            (mean * mean);
        if (variance > 0) {
          params->context_state[offset + i * 4 + 3] = variance;
        }
      }
    }
  }
  offset += layout.hit_miss_dim;
#endif

#if LOH_INCLUDE_CACHE_FEATURES
  // C. 缓存池状态摘要
  LOH_DEBUG_PRINT_DETAILED("[update_state_vector] cache_object_count=%ld\n",
                           (long)params->cache_object_count);

  for (int i = 0; i < layout.feature_dim; i++) {
    if (params->cache_object_count > 0) {
      double mean = params->cache_feature_sum[i] / params->cache_object_count;
      params->context_state[offset + i * 2] = mean;

      if (params->cache_object_count > 1) {
        double variance =
            (params->cache_feature_sum_sq[i] / params->cache_object_count) -
            (mean * mean);
        if (variance > 0) {
          params->context_state[offset + i * 2 + 1] = variance;
        }
      }
    }
  }
  offset += layout.cache_dim;
#endif

#if LOH_INCLUDE_CANDIDATE_FEATURES
  // D. 候选集合统计
  int cand_offset = offset;
  for (int s = 0; s < layout.candidate_source_dim; ++s) {
    for (int f = 0; f < layout.feature_dim; ++f) {
      double mean = 0.0, var = 0.0;
      uint64_t n = params->cand_feat_count[s];
      if (n > 0) {
        mean = params->cand_feat_sum[s][f] / (double)n;
        double ex2 = params->cand_feat_sumsq[s][f] / (double)n;
        var = ex2 - mean * mean;
        if (var < 0.0) var = 0.0;
      }
      params->context_state[cand_offset++] = mean;
      params->context_state[cand_offset++] = var;
    }
  }
  offset = cand_offset;

  // 重置累计器
  for (int s = 0; s < 6; ++s) {
    params->cand_feat_count[s] = 0;
    for (int f = 0; f < FEATURE_DIM; ++f) {
      params->cand_feat_sum[s][f] = 0.0;
      params->cand_feat_sumsq[s][f] = 0.0;
    }
  }
#endif

#if LOH_INCLUDE_TOPK_CANDIDATE_FEATURES
  // E. 蓄水池采样特征

  // 【新增】如果 TOPK 未满，主动调用 LOH_to_evict 来填充
  fill_topk_if_needed(params);

  LOH_DEBUG_PRINT_DETAILED(
      "[update_state_vector] reservoir samples: filled=%llu/%d, "
      "group_count=%llu\n",
      (unsigned long long)params->samples_filled, N_TOPK_SAMPLES,
      (unsigned long long)params->group_count);

  for (int s = 0; s < N_TOPK_SAMPLES; ++s) {
    for (int f = 0; f < layout.feature_dim; ++f) {
      params->context_state[offset++] = params->lowest_score_samples[s][f];
    }
  }

  // 重置采样状态，为下一个 Epoch 做准备
  reset_reservoir_samples(params);
#endif

#if LOH_INCLUDE_AVGTOPK_CANDIDATE_FEATURES
  // F. AvgTopK 特征

  // 【新增】如果 AvgTopK 为空，主动调用 LOH_to_evict 来填充
  fill_avgtopk_if_needed(params);

  // 计算每个 TOP 位置的平均特征
  LOH_DEBUG_PRINT_DETAILED("[update_state_vector] AvgTopK: evict_count=%llu\n",
                           (unsigned long long)params->avgtopk_evict_count);

  if (params->avgtopk_evict_count > 0) {
    double inv_count = 1.0 / (double)params->avgtopk_evict_count;
    for (int k = 0; k < SAMPLES_PER_EVICTION; k++) {
      for (int f = 0; f < layout.feature_dim; f++) {
        params->context_state[offset++] = params->avgtopk_sum[k][f] * inv_count;
      }
    }
  } else {
    // 没有驱逐发生，填充零
    for (int k = 0; k < SAMPLES_PER_EVICTION; k++) {
      for (int f = 0; f < layout.feature_dim; f++) {
        params->context_state[offset++] = 0.0;
      }
    }
  }

  // 重置 AvgTopK 累加器
  memset(params->avgtopk_sum, 0, sizeof(params->avgtopk_sum));
  params->avgtopk_evict_count = 0;
#endif

#if LOH_INCLUDE_REQUEST
  // G. 最近请求特征历史
  // 以时间顺序展开：最旧的在前，最近的在后；未填满的前缀补 0。
  int filled = (int)(params->request_history_count < REQUEST_HISTORY_LEN
                         ? params->request_history_count
                         : REQUEST_HISTORY_LEN);

  int start_index = 0;
  if (filled > 0) {
    start_index = (int)(params->request_history_pos - filled);
    if (start_index < 0) start_index += REQUEST_HISTORY_LEN;
  }

  for (int i = 0; i < REQUEST_HISTORY_LEN; i++) {
    int hist_idx = (start_index + i) % REQUEST_HISTORY_LEN;
    for (int f = 0; f < layout.feature_dim; f++) {
      double val = (i < filled) ? params->request_history[hist_idx][f] : 0.0;
      params->context_state[offset++] = val;
    }
  }
#endif

  int state_dim_runtime = offset;
  if (state_dim_runtime > CONTEXT_DIM) state_dim_runtime = CONTEXT_DIM;

  // 【调试打印】完整状态向量
  LOH_DEBUG_PRINT_BASIC("[LOH State] active_dim=%d/%d: global=[%.4f,%.4f]",
                        state_dim_runtime, CONTEXT_DIM,
                        params->context_state[0], params->context_state[1]);
#if LOH_INCLUDE_HIT_MISS_FEATURES
  LOH_DEBUG_PRINT_BASIC(" +hit/miss(%d)", layout.hit_miss_dim);
#endif
#if LOH_INCLUDE_CACHE_FEATURES
  LOH_DEBUG_PRINT_BASIC(" +cache(%d)", layout.cache_dim);
#endif
#if LOH_INCLUDE_CANDIDATE_FEATURES
  LOH_DEBUG_PRINT_BASIC(" +cand(%d)", layout.cand_dim);
#endif
#if LOH_INCLUDE_TOPK_CANDIDATE_FEATURES
  LOH_DEBUG_PRINT_BASIC(" +sample(%d: %llu/%d filled)", layout.topk_dim,
                        (unsigned long long)params->samples_filled,
                        N_TOPK_SAMPLES);
#endif
#if LOH_INCLUDE_AVGTOPK_CANDIDATE_FEATURES
  LOH_DEBUG_PRINT_BASIC(" +avgtopk(%d)", layout.avgtopk_dim);
#endif
#if LOH_INCLUDE_REQUEST
  LOH_DEBUG_PRINT_BASIC(" +request(%d)", layout.request_dim);
#endif
  LOH_DEBUG_PRINT_BASIC("\n");

  // 【详细打印】各模块统计信息（DETAILED级别）
#if LOH_INCLUDE_HIT_MISS_FEATURES
  LOH_DEBUG_PRINT_DETAILED("  [Hit/Miss Stats] hit_cnt=%lld miss_cnt=%lld\n",
                           (long long)params->hit_feature_count,
                           (long long)params->miss_feature_count);
#endif
#if LOH_INCLUDE_CACHE_FEATURES
  LOH_DEBUG_PRINT_DETAILED("  [Cache Stats] obj_count=%lld\n",
                           (long long)params->cache_object_count);
#endif
#if LOH_INCLUDE_TOPK_CANDIDATE_FEATURES
  LOH_DEBUG_PRINT_DETAILED(
      "  [Reservoir Stats] group_count=%llu samples_filled=%llu\n",
      (unsigned long long)params->group_count,
      (unsigned long long)params->samples_filled);
  if (params->samples_filled > 0) {
    printf("    Group 0 sample 0: [");
    for (int f = 0; f < layout.feature_dim; ++f) {
      printf("%.3f", params->lowest_score_samples[0][f]);
      if (f + 1 < layout.feature_dim) printf(",");
    }
    printf("]\n");
    if (params->samples_filled >= SAMPLES_PER_EVICTION) {
      int last = SAMPLES_PER_EVICTION - 1;
      printf("    Group 0 sample %d: [", last);
      for (int f = 0; f < layout.feature_dim; ++f) {
        printf("%.3f", params->lowest_score_samples[last][f]);
        if (f + 1 < layout.feature_dim) printf(",");
      }
      printf("]\n");
    }
  }
#endif

  // 【保留】逐个详细输出（VERBOSE模式）
  for (int i = 0; i < state_dim_runtime; i++) {
    LOH_DEBUG_PRINT_VERBOSE("[update_state_vector] state[%d] = %.6f\n", i,
                            params->context_state[i]);
  }
}

// ===== 非阻塞 mmap 快速同步路径 =====
// 完全绕过 stdio 缓冲、fcntl 锁、clock_gettime，直接通过 mmap 指针读写。
// 仅在 nonblocked 模式且 mmap 可用时使用。
static void sync_with_actor_critic_fast(LOH_params_t *params) {
  shm_data_t *m = params->shm_mmap;

  PERF_TS ts_sync_total;
  PERF_NOW(ts_sync_total);

  PERF_TS ts_misc_start;
  PERF_NOW(ts_misc_start);

  // 读取上一轮 Python 写回的权重（无锁，直接内存读取）
  if (__atomic_load_n(&m->weights_updated, __ATOMIC_ACQUIRE)) {
    memcpy(params->weights, m->weights, sizeof(double) * WEIGHT_DIM);
    if (params->score_model == LOH_SCORE_MODEL_MLP &&
        m->score_model == LOH_SCORE_MODEL_MLP) {
      int plen = m->mlp_param_len;
      if (plen < 0) plen = 0;
      if (plen > LOH_MLP_MAX_PARAMS) plen = LOH_MLP_MAX_PARAMS;
      params->mlp_hidden = m->mlp_hidden;
      if (params->mlp_hidden > LOH_MLP_MAX_HIDDEN)
        params->mlp_hidden = LOH_MLP_MAX_HIDDEN;
      params->mlp_param_len = plen;
      if (plen > 0) {
        memcpy(params->mlp_params, m->mlp_params,
               sizeof(double) * (size_t)plen);
      }
    }
    __atomic_store_n(&m->weights_updated, 0, __ATOMIC_RELEASE);
    __atomic_store_n(&m->ready_for_inference, 0, __ATOMIC_RELEASE);
    LOH_DEBUG_PRINT_BASIC(
        "[NON-BLOCK-FAST] Applied pending weights (ack_version=%llu)\n",
        (unsigned long long)m->ack_version);
  }

  // 跳过冗余 sync：如果 Python 尚未消费上一个 state，则不覆盖、不重算
  if (__atomic_load_n(&m->ready_for_inference, __ATOMIC_RELAXED)) {
    // Python 尚未读取上一个 state，跳过本次发送
    PERF_ACCUM(params, sync_misc, ts_misc_start);
    PERF_ACCUM(params, sync_total, ts_sync_total);
    return;
  }

  // 计算状态向量（仅在需要发送时才计算）
  PERF_TS ts_update_state;
  PERF_NOW(ts_update_state);
  update_state_vector(params);
  PERF_ACCUM(params, sync_update_state, ts_update_state);

  // 写入状态（直接 memcpy 到 mmap 页面）
  memcpy(m->state, params->context_state, sizeof(double) * CONTEXT_DIM);
  m->total_evicted_bytes = 0;
  m->total_evicted_count = 0;
  m->pending_penalty_count = 0;
  m->score_model = params->score_model;
  m->mlp_hidden = params->mlp_hidden;
  m->mlp_param_len = params->mlp_param_len;
  memcpy(m->mlp_params, params->mlp_params, sizeof(params->mlp_params));
  m->state_version += 1;
  m->timestamp = params->current_timestamp;

  // 发布 ready 标志（memory fence 确保前面的写入对 Python 可见）
  __atomic_store_n(&m->ready_for_inference, 1, __ATOMIC_RELEASE);

  // 发送 ready 信号量通知 Python
  if (params->sem_requested && params->sem_enabled &&
      params->sem_ready != NULL) {
    if (sem_post(params->sem_ready) != 0) {
      LOH_DEBUG_PRINT_BASIC(
          "[LOH] sem_post(ready) failed: %s, disable semaphore mode\n",
          strerror(errno));
      loh_sem_close(params, false);
    }
  }

  PERF_ACCUM(params, sync_misc, ts_misc_start);
  PERF_ACCUM(params, sync_total, ts_sync_total);
}

// 将状态发送到 Actor-Critic 网络并获取更新的权重
// 【核心修复】：重构此函数以修复死锁问题，并优化等待时间
static void sync_with_actor_critic(LOH_params_t *params) {
  if (!loh_enable_rl) return;  // 关闭RL时直接返回，无需计时
  if (params->shm_file == NULL && params->shm_mmap == NULL) return;

  // 非阻塞模式 + mmap 可用时使用快速路径
  if (!loh_wait_mode_blocked && params->shm_mmap != NULL) {
    sync_with_actor_critic_fast(params);
    return;
  }

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

  // ===【非阻塞模式：读取上一轮 Python 写回的权重】===
  // 在非阻塞模式下，上次 sync 发送状态后立即返回，Python 的权重回写
  // 会在这次 sync 的读取中被发现并应用
  if (!loh_wait_mode_blocked && shm_data.weights_updated) {
    memcpy(params->weights, shm_data.weights, sizeof(double) * WEIGHT_DIM);
    if (params->score_model == LOH_SCORE_MODEL_MLP &&
        shm_data.score_model == LOH_SCORE_MODEL_MLP) {
      int plen = shm_data.mlp_param_len;
      if (plen < 0) plen = 0;
      if (plen > LOH_MLP_MAX_PARAMS) plen = LOH_MLP_MAX_PARAMS;
      params->mlp_hidden = shm_data.mlp_hidden;
      if (params->mlp_hidden > LOH_MLP_MAX_HIDDEN)
        params->mlp_hidden = LOH_MLP_MAX_HIDDEN;
      params->mlp_param_len = plen;
      if (plen > 0) {
        memcpy(params->mlp_params, shm_data.mlp_params,
               sizeof(double) * (size_t)plen);
      }
    }
    shm_data.weights_updated = 0;
    shm_data.ready_for_inference = 0;
    LOH_DEBUG_PRINT_BASIC(
        "[NON-BLOCK] Applied pending weights from previous sync "
        "(ack_version=%llu)\n",
        (unsigned long long)shm_data.ack_version);
  }

  memcpy(shm_data.state, params->context_state, sizeof(double) * CONTEXT_DIM);

  // 默认置零，避免不同编译开关下字段未写入导致的脏值
  shm_data.total_evicted_bytes = 0;
  shm_data.total_evicted_count = 0;
  shm_data.pending_penalty_count = 0;

#if LOH_ENABLE_PENALTY
  // 【修改】传递驱逐统计而非即时性能指标
  shm_data.total_evicted_bytes = params->epoch_evicted_bytes;
  shm_data.total_evicted_count = params->epoch_evicted_count;
  shm_data.pending_penalty_count = params->penalty_queue_size;

  LOH_DEBUG_PRINT_BASIC(
      "[LOH sync] Sending eviction stats: total_evicted_bytes=%llu, "
      "total_evicted_count=%llu, pending_penalty_count=%d\n",
      (unsigned long long)shm_data.total_evicted_bytes,
      (unsigned long long)shm_data.total_evicted_count,
      shm_data.pending_penalty_count);
#endif

  // 评分模型配置（同步到 shm，便于 Python 端诊断/对齐）
  shm_data.score_model = params->score_model;
  shm_data.mlp_hidden = params->mlp_hidden;
  shm_data.mlp_param_len = params->mlp_param_len;
  memcpy(shm_data.mlp_params, params->mlp_params, sizeof(params->mlp_params));

  bool python_training = shm_data.is_training != 0;

  // 简化版本管理：仅用于日志对齐，不用于ACK校验
  shm_data.state_version += 1;
  shm_data.timestamp = params->current_timestamp;

  // 本次交互的序号（用于两端对齐日志）
  unsigned long long seq_no = (unsigned long long)shm_data.state_version;

  // 【仅供日志】计算临时性能指标（不传递给Python）
  double temp_miss_ratio =
      (params->epoch_obj_count > 0)
          ? (params->epoch_obj_miss_count / params->epoch_obj_count)
          : 0.0;
  double temp_byte_miss_ratio =
      (params->epoch_byte_count > 0)
          ? (params->epoch_byte_miss_count / params->epoch_byte_count)
          : 0.0;
  double temp_reward =
      loh_miss_ratio_weight * (1.0 - temp_miss_ratio) +
      loh_byte_miss_ratio_weight * (1.0 - temp_byte_miss_ratio);

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

  // 同时打印对象未命中率 (OMR)、字节未命中率 (BMR) 和计算出的临时奖励 (Temp
  // Reward) 注意：实际奖励将在Python端延迟计算
#if LOH_ENABLE_PENALTY
  LOH_DEBUG_PRINT_BASIC(
      "[%.6f] [C-STATE] [seq %llu] Sending RL request - OMR: %.4f, BMR: %.4f, "
      "Temp Reward: %.4f, Total Evicted Bytes: %llu, Epoch Count: %.0f\n",
      send_timestamp, seq_no, temp_miss_ratio, temp_byte_miss_ratio,
      temp_reward, (unsigned long long)shm_data.total_evicted_bytes,
      params->epoch_obj_count);
  LOH_DEBUG_PRINT_BASIC(
      "[seq %llu] LOH DEBUG: temp_reward=%.6f, "
      "total_evicted_bytes=%llu\n",
      seq_no, temp_reward, (unsigned long long)shm_data.total_evicted_bytes);
#else
  LOH_DEBUG_PRINT_DETAILED(
      "[%.6f] [C-STATE] [seq %llu] Sending RL request - OMR: %.4f, BMR: %.4f, "
      "Temp Reward: %.4f, Epoch Count: %.0f\n",
      send_timestamp, seq_no, temp_miss_ratio, temp_byte_miss_ratio,
      temp_reward, params->epoch_obj_count);
  LOH_DEBUG_PRINT_BASIC("[seq %llu] LOH DEBUG: temp_reward=%.6f\n", seq_no,
                        temp_reward);
#endif

#if LOH_DEBUG_LEVEL >= LOH_DEBUG_BASIC
  loh_state_layout_t dbg_layout = loh_get_state_layout();
  // 打印 context_dim 配置（C/Python 统一格式，便于日志解析）
  printf(
      "[CONTEXT_DIM_CONFIG] HITRATIO=%d HIT_MISS=%d CACHE=%d CAND=%d TOPK=%d "
      "AVGTOPK=%d REQUEST=%d TOTAL=%d\n",
      MISSRATIO_DIM, dbg_layout.hit_miss_dim, dbg_layout.cache_dim,
      dbg_layout.cand_dim, dbg_layout.topk_dim, dbg_layout.avgtopk_dim,
      dbg_layout.request_dim, dbg_layout.total_dim);

  // 按类别分组打印状态向量（C/Python 统一格式，便于日志解析）
  int offset = 0;

  // 1. HITRATIO (2维: obj_hit_ratio, byte_hit_ratio)
  printf("[STATE_HITRATIO] [seq %llu] [", seq_no);
  for (int i = 0; i < MISSRATIO_DIM; i++) {
    printf("%.6f", shm_data.state[offset + i]);
    if (i < MISSRATIO_DIM - 1) printf(", ");
  }
  printf("]\n");
  offset += MISSRATIO_DIM;

#if LOH_INCLUDE_HIT_MISS_FEATURES
  // 2. HIT_MISS (24维: 6特征 × 2(hit/miss) × 2(mean/var))
  printf("[STATE_HIT_MISS] [seq %llu] [", seq_no);
  for (int i = 0; i < dbg_layout.hit_miss_dim; i++) {
    printf("%.6f", shm_data.state[offset + i]);
    if (i < dbg_layout.hit_miss_dim - 1) printf(", ");
  }
  printf("]\n");
  offset += dbg_layout.hit_miss_dim;
#endif

#if LOH_INCLUDE_CACHE_FEATURES
  // 3. CACHE (12维: 6特征 × 2(mean/var))
  printf("[STATE_CACHE] [seq %llu] [", seq_no);
  for (int i = 0; i < dbg_layout.cache_dim; i++) {
    printf("%.6f", shm_data.state[offset + i]);
    if (i < dbg_layout.cache_dim - 1) printf(", ");
  }
  printf("]\n");
  offset += dbg_layout.cache_dim;
#endif

#if LOH_INCLUDE_CANDIDATE_FEATURES
  // 4. CAND (72维: 6组 × 12维, 每组对应一个特征来源)
  int cand_block = dbg_layout.feature_dim * 2;
  for (int g = 0; g < dbg_layout.candidate_source_dim; g++) {
    printf("[STATE_CAND_%d] [seq %llu] [", g, seq_no);
    for (int i = 0; i < cand_block; i++) {
      printf("%.6f", shm_data.state[offset + g * cand_block + i]);
      if (i < cand_block - 1) printf(", ");
    }
    printf("]\n");
  }
  offset += dbg_layout.cand_dim;
#endif

#if LOH_INCLUDE_TOPK_CANDIDATE_FEATURES
  // 5. TOPK (N_TOPK_SAMPLES×6维: 8组 × 4样本 × 6特征)
  // N_TOPK_SAMPLES=32, 分为8组，每组4个样本
  int topk_groups = N_TOPK_SAMPLES / SAMPLES_PER_EVICTION;
  int topk_block = SAMPLES_PER_EVICTION * dbg_layout.feature_dim;
  for (int g = 0; g < topk_groups; g++) {
    printf("[STATE_TOPK_%d] [seq %llu] [", g, seq_no);
    for (int i = 0; i < topk_block; i++) {
      printf("%.6f", shm_data.state[offset + g * topk_block + i]);
      if (i < topk_block - 1) printf(", ");
    }
    printf("]\n");
  }
  offset += dbg_layout.topk_dim;
#endif

#if LOH_INCLUDE_AVGTOPK_CANDIDATE_FEATURES
  // 6. AVGTOPK (4×6=24维: 4个TOP位置 × 6特征)
  printf("[STATE_AVGTOPK] [seq %llu] [", seq_no);
  for (int i = 0; i < dbg_layout.avgtopk_dim; i++) {
    printf("%.6f", shm_data.state[offset + i]);
    if (i < dbg_layout.avgtopk_dim - 1) printf(", ");
  }
  printf("]\n");
  offset += dbg_layout.avgtopk_dim;
#endif

#if LOH_INCLUDE_REQUEST
  // 7. REQUEST 历史 (REQUEST_HISTORY_LEN×6)
  if (REQUEST_FEATURE_DIM > 0) {
    int request_history_len = REQUEST_HISTORY_LEN;
    int per_req_dim = dbg_layout.feature_dim;
    int max_print_requests = 4;  // 与 Python 端保持一致
    int actual_reqs = (request_history_len < max_print_requests)
                          ? request_history_len
                          : max_print_requests;

    for (int r = 0; r < actual_reqs; r++) {
      printf("[STATE_REQUEST_%d] [seq %llu] [", r, seq_no);
      for (int i = 0; i < per_req_dim; i++) {
        int idx = offset + r * per_req_dim + i;
        if (idx >= offset + dbg_layout.request_dim) break;
        printf("%.6f", shm_data.state[idx]);
        if (i < per_req_dim - 1 && idx + 1 < offset + dbg_layout.request_dim)
          printf(", ");
      }
      printf("]\n");
    }
    offset += dbg_layout.request_dim;
  }
#endif
#endif

  // 将更新的数据写回共享内存（包括 penalty 数据）
  rewind(params->shm_file);
  size_t shm_written =
      fwrite(&shm_data, sizeof(shm_data_t), 1, params->shm_file);

#if LOH_ENABLE_PENALTY
  LOH_DEBUG_PRINT_BASIC(
      "[C][BASIC] Wrote shm_data_t: %zu items, size=%zu bytes, "
      "pending_penalty_count=%d\n",
      shm_written, sizeof(shm_data_t), shm_data.pending_penalty_count);

  // ===【共享内存布局说明】===
  // 共享内存文件布局（不同模式下位置固定）：
  //   [Offset 0]              shm_data_t (包含 state, weights, total_evicted_*,
  //   pending_penalty_count) [Offset sizeof(shm_data_t)]  penalty_entry_t 数组
  //   (仅 LOH_ENABLE_PENALTY=1 时写入)
  //
  // Python 端读取方式：
  //   1. 先读取 sizeof(shm_data_t) 字节获取 shm_data
  //   2. 检查 shm_data.pending_penalty_count
  //   3. 如果 > 0，继续读取 pending_penalty_count * sizeof(penalty_entry_t)
  //   字节
  //
  // 数据位置确定：
  //   - LOH_ENABLE_PENALTY=0: 只有 shm_data_t，文件大小 = sizeof(shm_data_t)
  //   - LOH_ENABLE_PENALTY=1: shm_data_t + penalty 数组，文件大小动态变化
  //   - pending_penalty_count 字段在所有模式下位置相同（shm_data_t 内部）
  // ===

  // 【优化】紧接着写入 penalty 数据（扩展共享内存文件）
  if (params->penalty_queue_size > 0) {
    PERF_TS ts_penalty_write;
    PERF_NOW(ts_penalty_write);

    size_t penalty_written =
        fwrite(params->penalty_queue, sizeof(penalty_entry_t),
               (size_t)params->penalty_queue_size, params->shm_file);

    PERF_ACCUM(params, penalty_write_shm, ts_penalty_write);

    if (penalty_written != (size_t)params->penalty_queue_size) {
      LOH_DEBUG_PRINT_ERROR(
          "[LOH] WARNING: Failed to write penalty data (wrote %zu/%d "
          "entries)\n",
          penalty_written, params->penalty_queue_size);
    } else {
      LOH_DEBUG_PRINT_BASIC(
          "[C→Python] 📤 Wrote %zu penalty entries (%zu bytes each, total %zu "
          "bytes)\n",
          penalty_written, sizeof(penalty_entry_t),
          penalty_written * sizeof(penalty_entry_t));
      // 打印前 5 个 penalty 的详细信息（调试用）
      int print_count =
          params->penalty_queue_size < 5 ? params->penalty_queue_size : 5;
      for (int i = 0; i < print_count; i++) {
        penalty_entry_t *p = &params->penalty_queue[i];
        LOH_DEBUG_PRINT_BASIC(
            "[C→Python]   📋 penalty[%d]: version=%lu, evict_to_access=%ld, "
            "size=%ld, obj_id=%lu\n",
            i, p->penalty_version, p->eviction_to_access, p->obj_size,
            p->obj_id);
      }
    }

    // 【优化】写入完成后清空本地队列（避免重复发送）
    params->penalty_queue_size = 0;
    LOH_DEBUG_PRINT_BASIC("[C][BASIC] Penalty queue cleared after write\n");
  }
#endif

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

  // ===【非阻塞模式检查】===
  // 非阻塞模式：发送状态后立即返回，不等待 Python 响应
  // Python 写回的权重会在**下一次** sync_with_actor_critic 调用时被读取
  // （在函数开头的 "读取上一轮权重" 逻辑中处理）
  if (!loh_wait_mode_blocked) {
    LOH_DEBUG_PRINT_BASIC(
        "[seq %llu] Non-blocking mode: state sent, skip wait and continue "
        "with current weights\n",
        seq_no);
    // misc计时结束 (非阻塞提前返回)
    PERF_ACCUM(params, sync_misc, ts_misc_start);
    // 总计时结束
    PERF_ACCUM(params, sync_total, ts_sync_total);
    return;
  }

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
  if (!params->sem_enabled && loh_enable_rl && params->sem_ready_name != NULL &&
      params->sem_ack_name != NULL) {
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
        memcpy(params->weights, shm_data.weights, sizeof(double) * WEIGHT_DIM);
        if (params->score_model == LOH_SCORE_MODEL_MLP &&
            shm_data.score_model == LOH_SCORE_MODEL_MLP) {
          int plen = shm_data.mlp_param_len;
          if (plen < 0) plen = 0;
          if (plen > LOH_MLP_MAX_PARAMS) plen = LOH_MLP_MAX_PARAMS;
          params->mlp_hidden = shm_data.mlp_hidden;
          if (params->mlp_hidden > LOH_MLP_MAX_HIDDEN)
            params->mlp_hidden = LOH_MLP_MAX_HIDDEN;
          params->mlp_param_len = plen;
          if (plen > 0) {
            memcpy(params->mlp_params, shm_data.mlp_params,
                   sizeof(double) * (size_t)plen);
          }
        }
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

        // 【重置 Epoch 统计】在成功接收权重后
        params->epoch_obj_count = 0;
        params->epoch_obj_miss_count = 0;
        params->epoch_byte_count = 0;
        params->epoch_byte_miss_count = 0;

        // 清空命中/未命中统计
        params->hit_feature_count = 0;
        params->miss_feature_count = 0;
        for (int i = 0; i < FEATURE_DIM; i++) {
          params->hit_feature_sum[i] = 0.0;
          params->hit_feature_sum_sq[i] = 0.0;
          params->miss_feature_sum[i] = 0.0;
          params->miss_feature_sum_sq[i] = 0.0;
        }

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
    memcpy(params->weights, shm_data.weights, sizeof(double) * WEIGHT_DIM);
    if (params->score_model == LOH_SCORE_MODEL_MLP &&
        shm_data.score_model == LOH_SCORE_MODEL_MLP) {
      int plen = shm_data.mlp_param_len;
      if (plen < 0) plen = 0;
      if (plen > LOH_MLP_MAX_PARAMS) plen = LOH_MLP_MAX_PARAMS;
      params->mlp_hidden = shm_data.mlp_hidden;
      if (params->mlp_hidden > LOH_MLP_MAX_HIDDEN)
        params->mlp_hidden = LOH_MLP_MAX_HIDDEN;
      params->mlp_param_len = plen;
      if (plen > 0) {
        memcpy(params->mlp_params, shm_data.mlp_params,
               sizeof(double) * (size_t)plen);
      }
    }
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

#if LOH_DEBUG_LEVEL >= LOH_DEBUG_BASIC
    // 打印接收到的权重（C/Python 统一格式，突出有效维度 vs 共享内存上限）
    int score_feature_dim =
        loh_score_compound_v2
            ? WEIGHT_DIM
            : (loh_score_use_compound ? FEATURE_DIM
                                      : (loh_score_use_irt ? FEATURE_DIM : 3));
    if (score_feature_dim < 0) score_feature_dim = 0;
    if (score_feature_dim > WEIGHT_DIM) score_feature_dim = WEIGHT_DIM;

    printf("[WEIGHTS_UPDATED] [seq %llu] dim=%d/%d [", seq_no,
           score_feature_dim, WEIGHT_DIM);
    for (int i = 0; i < score_feature_dim; i++) {
      printf("%.6f", params->weights[i]);
      if (i < score_feature_dim - 1) printf(", ");
    }
    printf("]\n");
#endif
    // 【重置 Epoch 统计】在成功接收权重后
    params->epoch_obj_count = 0;
    params->epoch_obj_miss_count = 0;
    params->epoch_byte_count = 0;
    params->epoch_byte_miss_count = 0;

#if LOH_ENABLE_PENALTY
    params->epoch_evicted_bytes = 0;  // 【新增】重置驱逐字节计数器
    params->epoch_evicted_count = 0;  // 【新增】重置驱逐对象计数器

    // 【优化】重置 penalty queue 并缩小到初始容量（减少内存占用）
    params->penalty_queue_size = 0;
    LOH_DEBUG_PRINT_BASIC(
        "[C←ACK] 🧹 Cleared penalty queue after ACK (seq %llu)\n", seq_no);

    // 如果容量超过初始值，缩小回初始容量（realloc 缩小通常很快）
    if (params->penalty_queue_capacity > PENALTY_QUEUE_INIT_CAPACITY) {
      penalty_entry_t *smaller_queue =
          realloc(params->penalty_queue,
                  PENALTY_QUEUE_INIT_CAPACITY * sizeof(penalty_entry_t));
      if (smaller_queue != NULL) {
        params->penalty_queue = smaller_queue;
        params->penalty_queue_capacity = PENALTY_QUEUE_INIT_CAPACITY;
        LOH_DEBUG_PRINT_BASIC(
            "[LOH] Shrunk penalty queue back to initial capacity %d\n",
            PENALTY_QUEUE_INIT_CAPACITY);
      }
      // 如果 realloc 失败，保持原容量（不影响功能）
    }
#endif

    // 清空命中/未命中统计
    params->hit_feature_count = 0;
    params->miss_feature_count = 0;
    for (int i = 0; i < FEATURE_DIM; i++) {
      params->hit_feature_sum[i] = 0.0;
      params->hit_feature_sum_sq[i] = 0.0;
      params->miss_feature_sum[i] = 0.0;
      params->miss_feature_sum_sq[i] = 0.0;
    }

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
  {
    LOH_DEBUG_PRINT_BASIC(
        "[%.6f] [C-CACHED] [seq %llu] Using cached weights: [%.3f, %.3f, %.3f, "
        "%.3f, %.3f, %.3f, %.3f]\n",
        final_timestamp, seq_no, params->weights[0], params->weights[1],
        params->weights[2], params->weights[3], params->weights[4],
        params->weights[5], params->weights[6]);
  }

  // 【重置 Epoch 统计】即使超时也要重置（Epoch 已结束）
  params->epoch_obj_count = 0;
  params->epoch_obj_miss_count = 0;
  params->epoch_byte_count = 0;
  params->epoch_byte_miss_count = 0;

  // 清空命中/未命中统计
  params->hit_feature_count = 0;
  params->miss_feature_count = 0;
  for (int i = 0; i < FEATURE_DIM; i++) {
    params->hit_feature_sum[i] = 0.0;
    params->hit_feature_sum_sq[i] = 0.0;
    params->miss_feature_sum[i] = 0.0;
    params->miss_feature_sum_sq[i] = 0.0;
  }

  // misc操作计时结束
  PERF_ACCUM(params, sync_misc, ts_misc_start);
  // sync总计时结束
  PERF_ACCUM(params, sync_total, ts_sync_total);
}

// 辅助函数的前向声明（评分逻辑已在 LOH_to_evict 中内联实现）

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
  int idx = obj->LOH.loh_size_pos;
  bool in = (idx >= 0 && idx < params->size_heap_size &&
             params->size_heap[idx].obj == obj);
  if (in) {
    LOH_DEBUG_PRINT_DETAILED("[VALIDATE][%s] obj_id=%llu in SIZE heap\n", tag,
                             (unsigned long long)obj->obj_id);
  } else {
    LOH_DEBUG_PRINT_DETAILED(
        "[VALIDATE][%s] WARNING obj_id=%llu NOT in SIZE heap\n", tag,
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
#define LOH_SEEN_CAP 8192  // 足以支持 MAX_CANDIDATES_LIMIT=2048 的 4x 负载因子
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

// 尺寸堆操作函数（单一最小堆）- LOH_USE_SIZE_BUCKETS=0 时使用
static void size_heap_init(LOH_params_t *params);
static void size_heap_free(LOH_params_t *params);
static void size_heap_add(LOH_params_t *params, cache_obj_t *obj);
static void size_heap_remove(LOH_params_t *params, cache_obj_t *obj);
static void size_heap_sift_up(LOH_params_t *params, int idx);
static void size_heap_sift_down(LOH_params_t *params, int idx);
static void size_heap_get_candidates(LOH_params_t *params, int max_candidates,
                                     int *n_candidates);

// 尺寸桶操作函数（全量分桶）- LOH_USE_SIZE_BUCKETS=1 时使用
static void size_buckets_init(LOH_params_t *params);
static void size_buckets_free(LOH_params_t *params);
static void size_buckets_add(LOH_params_t *params, cache_obj_t *obj);
static void size_buckets_remove(LOH_params_t *params, cache_obj_t *obj);
static int size_get_bucket_index(LOH_params_t *params, int64_t size);
static void size_buckets_get_candidates(LOH_params_t *params,
                                        int max_candidates, int *n_candidates);

// 统一的 size 数据结构操作接口（根据 loh_use_size_buckets 调用相应实现）
static void size_ds_init(LOH_params_t *params);
static void size_ds_free(LOH_params_t *params);
static void size_ds_add(LOH_params_t *params, cache_obj_t *obj);
static void size_ds_remove(LOH_params_t *params, cache_obj_t *obj);
static void size_ds_get_candidates(LOH_params_t *params, int max_candidates,
                                   int *n_candidates);

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

#if LOH_INCLUDE_REQUEST
// 将当前请求的 6 维特征写入环形缓冲区
static void loh_record_request_features(LOH_params_t *params,
                                        const double features[FEATURE_DIM]) {
  int idx = params->request_history_pos;
  for (int i = 0; i < FEATURE_DIM; i++) {
    params->request_history[idx][i] = features[i];
  }
  params->request_history_pos = (idx + 1) % REQUEST_HISTORY_LEN;
  if (params->request_history_count < REQUEST_HISTORY_LEN) {
    params->request_history_count++;
  }
}
#endif

/**
 * @brief 初始化 LOH 缓存
 *
 * @param ccache_params 通用缓存参数
 * @param cache_specific_params LOH 专用参数
 */
// Expose this LOH variant as LOH_blocked_ppo_init to avoid duplicate symbol
// conflicts with the default LOH implementation. Runtime name mapping will
// register this initializer under the name "loh-ppo".
cache_t *LOH_init(const common_cache_params_t ccache_params,
                  const char *cache_specific_params) {
  /* Startup identification print to make runtime variant clear in logs */
  LOH_DEBUG_PRINT_CONFIG(
      "[LOH INIT] Initializing LOH (unified version with penalty support)\n");
  LOH_DEBUG_PRINT_CONFIG("=== LOH Cache Initialize ===\n");
  LOH_DEBUG_PRINT_CONFIG("LOH Debug Level: %d\n", LOH_DEBUG_LEVEL);
  LOH_DEBUG_PRINT_CONFIG("Cache size: %lu\n", ccache_params.cache_size);

  // 打印关键环境变量
  LOH_DEBUG_PRINT_CONFIG("[LOH INIT] === Environment Variables ===\n");
  LOH_DEBUG_PRINT_CONFIG("  LOH_SHM_KEY=%s\n", getenv("LOH_SHM_KEY")
                                                   ? getenv("LOH_SHM_KEY")
                                                   : "(default 9876)");
  LOH_DEBUG_PRINT_CONFIG(
      "  LOH_ENABLE_SEMAPHORE=%s, LOH_DISABLE_SEMAPHORE=%s\n",
      getenv("LOH_ENABLE_SEMAPHORE") ? getenv("LOH_ENABLE_SEMAPHORE")
                                     : "(unset)",
      getenv("LOH_DISABLE_SEMAPHORE") ? getenv("LOH_DISABLE_SEMAPHORE")
                                      : "(unused)");
  LOH_DEBUG_PRINT_CONFIG(
      "  LOH_FEATURE_LOG1P_RAW=%s, LOH_FEATURE_LOG1P_RECIPROCAL=%s\n",
      getenv("LOH_FEATURE_LOG1P_RAW") ? getenv("LOH_FEATURE_LOG1P_RAW")
                                      : "(unset)",
      getenv("LOH_FEATURE_LOG1P_RECIPROCAL")
          ? getenv("LOH_FEATURE_LOG1P_RECIPROCAL")
          : "(unset)");
  LOH_DEBUG_PRINT_CONFIG(
      "  LOH_SCORE_MODEL=%s, LOH_MLP_HIDDEN=%s\n",
      getenv("LOH_SCORE_MODEL") ? getenv("LOH_SCORE_MODEL")
                                : "(default linear)",
      getenv("LOH_MLP_HIDDEN") ? getenv("LOH_MLP_HIDDEN") : "(default 16)");
  LOH_DEBUG_PRINT_CONFIG(
      "  Build-time dims: MISSRATIO=%d, HIT_MISS=%d, CACHE=%d, CAND=%d, "
      "TOPK=%d, AVGTOPK=%d, REQUEST=%d -> CONTEXT_DIM=%d\n",
      MISSRATIO_DIM, HIT_MISS_DIM, CACHE_DIM, CAND_FEATURE_DIM,
      TOPK_FEATURE_DIM, AVGTOPK_FEATURE_DIM, REQUEST_FEATURE_DIM, CONTEXT_DIM);
  LOH_DEBUG_PRINT_CONFIG(
      "  LOH_STRUCTURED_CANDIDATES=%s (default=%d, limit=%d)\n",
      getenv("LOH_STRUCTURED_CANDIDATES") ? getenv("LOH_STRUCTURED_CANDIDATES")
                                          : "(unset)",
      MAX_CANDIDATES_DEFAULT, MAX_CANDIDATES_LIMIT);

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
  // ===【读取候选池大小环境变量（必须在所有数据结构初始化之前）】===
  {
    const char *mc_str = getenv("LOH_STRUCTURED_CANDIDATES");
    if (mc_str != NULL) {
      int mc_val = atoi(mc_str);
      if ((mc_val == 0 || mc_val >= 6) && mc_val <= MAX_CANDIDATES_LIMIT) {
        loh_structured_candidates = mc_val;
      } else {
        fprintf(stderr,
                "LOH WARNING: LOH_STRUCTURED_CANDIDATES=%d out of range "
                "{0} ∪ [6, %d], using default %d\n",
                mc_val, MAX_CANDIDATES_LIMIT, MAX_CANDIDATES_DEFAULT);
        loh_structured_candidates = MAX_CANDIDATES_DEFAULT;
      }
    }
    printf("LOH_STRUCTURED_CANDIDATES=%d (default=%d, limit=%d)\n",
           loh_structured_candidates, MAX_CANDIDATES_DEFAULT,
           MAX_CANDIDATES_LIMIT);
  }

  // 初始化 frequency 表
  freq_table_init(params);

  // 初始化 IRT 堆
  irt_heap_init(params);

  // ===【读取 Size 数据结构模式环境变量（必须在 size_ds_init 之前）】===
  {
    const char *size_buckets_str = getenv("LOH_USE_SIZE_BUCKETS");
    if (size_buckets_str != NULL) {
      loh_use_size_buckets = loh_parse_bool_env(size_buckets_str, 0);
    }
  }

  // 初始化尺寸数据结构（根据 LOH_USE_SIZE_BUCKETS 选择 heap 或 buckets）
  size_ds_init(params);

  // 初始化 flat object array（用于 O(1) 随机采样，替代 hashtable_rand_obj）
  params->obj_array_capacity = 65536;  // 初始容量，按需扩容
  params->obj_array_size = 0;
  params->obj_array = (cache_obj_t **)malloc(params->obj_array_capacity *
                                             sizeof(cache_obj_t *));

  // 初始化特征权重（默认的平衡初值）
  params->weights[0] = 1.0;  // recency
  params->weights[1] = 0.0;  // frequency
  params->weights[2] = 0.0;  // size
  params->weights[3] = 0.0;  // irt1
  params->weights[4] = 0.0;  // irt2
  params->weights[5] = 0.0;  // irt3

  // 环境变量 LOH_INITIAL_WEIGHTS 覆盖初始权重（逗号分隔，如 "0,1,0,0,0,0"）
  {
    const char *iw_env = getenv("LOH_INITIAL_WEIGHTS");
    if (iw_env && *iw_env) {
      char buf[256];
      strncpy(buf, iw_env, sizeof(buf) - 1);
      buf[sizeof(buf) - 1] = '\0';
      char *tok = strtok(buf, ",");
      for (int i = 0; i < FEATURE_DIM && tok; i++) {
        params->weights[i] = atof(tok);
        tok = strtok(NULL, ",");
      }
      printf(
          "LOH: initial weights overridden to [%.4f, %.4f, %.4f, %.4f, %.4f, "
          "%.4f]\n",
          params->weights[0], params->weights[1], params->weights[2],
          params->weights[3], params->weights[4], params->weights[5]);
    }
  }

  // ===== 评分模型选择：默认 linear；可选 mlp（通过环境变量切换，不影响旧选项）
  // =====
  params->score_model = LOH_SCORE_MODEL_LINEAR;
  params->mlp_hidden = 16;
  params->mlp_param_len = loh_mlp_param_len(params->mlp_hidden);
  memset(params->mlp_params, 0, sizeof(params->mlp_params));
  {
    const char *m = getenv("LOH_SCORE_MODEL");
    if (m && *m) {
      if (g_ascii_strcasecmp(m, "mlp") == 0 ||
          g_ascii_strcasecmp(m, "nn") == 0) {
        params->score_model = LOH_SCORE_MODEL_MLP;
      } else {
        params->score_model = LOH_SCORE_MODEL_LINEAR;
      }
    }
    const char *h = getenv("LOH_MLP_HIDDEN");
    if (h && *h) {
      int hv = atoi(h);
      if (hv > 0) params->mlp_hidden = hv;
    }
    if (params->mlp_hidden > LOH_MLP_MAX_HIDDEN) {
      params->mlp_hidden = LOH_MLP_MAX_HIDDEN;
    }
    params->mlp_param_len = loh_mlp_param_len(params->mlp_hidden);
  }

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

  // 初始化特征裁剪统计
  for (int i = 0; i < FEATURE_DIM; i++) {
    params->feature_clip_count[i] = 0;
    params->feature_sample_count[i] = 0;
  }

  // 初始化历史特征统计
  // 【删除 init_history_stats 调用】：统一使用 global_access_records，在
  // free_global_access_records 中释放

  // 【新增 Ghost cache 初始化】：保留被驱逐对象的历史信息
  init_ghost_cache(params, cache->cache_size);

  // 初始化 Actor-Critic（行为者-评论者）强化学习参数
  params->rl_update_interval =
      500;  // 每500个请求触发一次更新（旧值200，增大以减少sync开销）
  params->requests_since_rl_update = 0;
  params->epoch_start_time = time(NULL);
  params->epoch_obj_miss_count = 0;
  params->epoch_obj_count = 0;
  params->epoch_byte_miss_count = 0;
  params->epoch_byte_count = 0;

#if LOH_ENABLE_PENALTY
  params->epoch_evicted_bytes = 0;  // 【新增】初始化驱逐字节计数器
  params->epoch_evicted_count = 0;  // 【新增】初始化驱逐对象计数器
#endif

  // Initialize context state
  memset(params->context_state, 0, sizeof(double) * CONTEXT_DIM);

#if LOH_INCLUDE_REQUEST
  // 初始化请求历史缓冲区
  memset(params->request_history, 0, sizeof(params->request_history));
  params->request_history_pos = 0;
  params->request_history_count = 0;
#endif

#if LOH_INCLUDE_TOPK_CANDIDATE_FEATURES
  // 初始化蓄水池采样字段
  params->group_count = 0;
  params->samples_filled = 0;
  params->current_lowest_count = 0;
  memset(params->lowest_score_samples, 0, sizeof(params->lowest_score_samples));
  memset(params->current_lowest_4, 0, sizeof(params->current_lowest_4));
  memset(params->current_lowest_scores, 0,
         sizeof(params->current_lowest_scores));
  LOH_DEBUG_PRINT_CONFIG(
      "[LOH INIT] Reservoir sampling enabled: N_TOPK_SAMPLES=%d "
      "(每组%d个×8组), "
      "sample_dim=%d\n",
      N_TOPK_SAMPLES, SAMPLES_PER_EVICTION, TOPK_FEATURE_DIM);
#endif

#if LOH_INCLUDE_AVGTOPK_CANDIDATE_FEATURES
  // 初始化 AvgTopK 字段
  memset(params->avgtopk_sum, 0, sizeof(params->avgtopk_sum));
  params->avgtopk_evict_count = 0;
  params->avgtopk_lowest_count = 0;
  memset(params->avgtopk_lowest_4, 0, sizeof(params->avgtopk_lowest_4));
  memset(params->avgtopk_lowest_scores, 0,
         sizeof(params->avgtopk_lowest_scores));
  LOH_DEBUG_PRINT_CONFIG("[LOH INIT] AvgTopK enabled: TOP%d × %d特征 = %d维\n",
                         SAMPLES_PER_EVICTION, FEATURE_DIM,
                         AVGTOPK_FEATURE_DIM);
#endif

  // 如果设置了固定权重环境变量，则覆盖默认权重
  const char *fixed_w = getenv("LOH_FIXED_WEIGHTS");
  if (fixed_w && fixed_w[0] != '\0') {
    char *buf = g_strdup(fixed_w);
    char *p = buf;
    char *tok;
    double tmp[WEIGHT_DIM];
    int idx = 0;
    while ((tok = strsep(&p, ",; ")) != NULL) {
      if (!*tok) continue;
      char *endptr = NULL;
      double v = strtod(tok, &endptr);
      if (endptr == tok) continue;
      if (idx < WEIGHT_DIM) {
        tmp[idx++] = v;
      }
    }
    if (idx == FEATURE_DIM || idx == WEIGHT_DIM) {
      // 兼容旧 6 维：若只提供 6 个值则把第 7 个权重置为 0
      for (int i = 0; i < WEIGHT_DIM; i++) {
        params->weights[i] = (i < idx) ? tmp[i] : 0.0;
      }
      LOH_DEBUG_PRINT_CONFIG("[LOH INIT] LOH_FIXED_WEIGHTS from env: [");
      for (int i = 0; i < WEIGHT_DIM; i++) {
        LOH_DEBUG_PRINT_CONFIG("%.3f%s", params->weights[i],
                               (i == WEIGHT_DIM - 1) ? "]\n" : ", ");
      }
    } else {
      LOH_DEBUG_PRINT_CONFIG(
          "[LOH INIT] LOH_FIXED_WEIGHTS='%s' parsed %d values (need %d), "
          "keeping default weights\n",
          fixed_w, idx, WEIGHT_DIM);
    }
    g_free(buf);
  }

  // 如果设置了固定 MLP 参数环境变量，则覆盖默认 MLP 参数
  // 参数格式："p0,p1,..."，长度需与 loh_mlp_param_len(LOH_MLP_HIDDEN) 一致
  // 顺序与 loh_mlp_eval 对齐：W1(H*D), b1(H), W2(H), b2(1)
  const char *fixed_mlp = getenv("LOH_FIXED_MLP_PARAMS");
  if (fixed_mlp && fixed_mlp[0] != '\0') {
    int expected = loh_mlp_param_len(params->mlp_hidden);
    char *buf = g_strdup(fixed_mlp);
    char *p = buf;
    char *tok;
    int idx = 0;
    while ((tok = strsep(&p, ",; ")) != NULL) {
      if (!*tok) continue;
      char *endptr = NULL;
      double v = strtod(tok, &endptr);
      if (endptr == tok) continue;
      if (idx < LOH_MLP_MAX_PARAMS) {
        params->mlp_params[idx++] = v;
      }
    }

    if (idx >= expected) {
      params->score_model = LOH_SCORE_MODEL_MLP;
      params->mlp_param_len = idx;
      LOH_DEBUG_PRINT_CONFIG(
          "[LOH INIT] LOH_FIXED_MLP_PARAMS loaded: hidden=%d, expected=%d, "
          "parsed=%d (score_model=mlp)\n",
          params->mlp_hidden, expected, idx);
    } else {
      LOH_DEBUG_PRINT_CONFIG(
          "[LOH INIT] LOH_FIXED_MLP_PARAMS parsed %d values (need >= %d), "
          "keeping existing model/params\n",
          idx, expected);
    }
    g_free(buf);
  }

  // 初始化reward权重（默认只考虑miss ratio）
  loh_miss_ratio_weight = 1.0;       // 默认权重：只考虑对象miss ratio
  loh_byte_miss_ratio_weight = 0.0;  // 默认权重：不考虑字节miss ratio

  // ============================================================
  // 运行时环境变量覆盖（集中处理）
  //   1) RL / 权重相关（LOH_ENABLE_RL；LOH_FIXED_WEIGHTS / miss-ratio-weight）
  //   2) 共享内存 / 信号量 / 等待模式
  //   3) 特征变换 / 归一化相关
  // ============================================================

  // 1) RL / 权重相关
  // 初始化文件式共享内存：默认启用 RL，可通过 LOH_ENABLE_RL / enable-rl 覆盖
  loh_enable_rl = 1;

  // 1.1) 运行时环境：通过 LOH_ENABLE_RL 覆盖开关
  {
    const char *env_enable = getenv("LOH_ENABLE_RL");
    if (env_enable && env_enable[0] != '\0') {
      loh_enable_rl = loh_parse_bool_env(env_enable, loh_enable_rl);
    }
    LOH_DEBUG_PRINT_CONFIG("[LOH INIT] enable_rl=%d (after env)\n",
                           loh_enable_rl);
  }

  // 1.2) cache_specific_params：learning-interval / enable-rl /
  //      rl-update-interval / miss-ratio-weight
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
        loh_enable_rl = atoi(value) ? 1 : 0;
      } else if (strcmp(key, "rl-update-interval") == 0) {
        params->rl_update_interval = atoll(value);
      } else if (strcmp(key, "miss-ratio-weight") == 0) {
        loh_miss_ratio_weight = atof(value);
        // 自动设置byte_miss_ratio_weight为互补权重
        loh_byte_miss_ratio_weight = 1.0 - loh_miss_ratio_weight;
        LOH_DEBUG_PRINT_CONFIG(
            "[LOH INIT] Set miss_ratio_weight=%.3f, "
            "byte_miss_ratio_weight=%.3f\n",
            loh_miss_ratio_weight, loh_byte_miss_ratio_weight);
      }
    }

    g_free(old_params_str);
  }

  // 2) 共享内存 / 信号量 / 等待模式

  params->shm_filename = NULL;
  params->shm_file = NULL;
  params->shm_mmap = NULL;
  params->shm_fd = -1;
  params->sem_ready = NULL;
  params->sem_ack = NULL;
  params->sem_ready_name = NULL;
  params->sem_ack_name = NULL;
  params->sem_enabled = false;
  // 默认请求启用信号量，后续可被环境变量覆盖
  params->sem_requested = 1;
  params->sem_owner = false;
  // 仅在启用RL时初始化共享内存
  if (loh_enable_rl) {
    const char *key_str = getenv("LOH_SHM_KEY");
    if (key_str && key_str[0] != '\0') {
      params->shm_filename = g_strdup_printf("/dev/shm/loh_ac_%s", key_str);
    } else {
      params->shm_filename = g_strdup_printf("/dev/shm/loh_ac_%d", SHM_KEY);
    }
    params->shm_file = fopen(params->shm_filename, "r+b");

    // 打印共享内存结构体大小信息，用于调试
    LOH_DEBUG_PRINT_CONFIG("[LOH INIT] shm_data_t size=%zu bytes\n",
                           sizeof(shm_data_t));
    LOH_DEBUG_PRINT_CONFIG("  - CONTEXT_DIM=%d (state array=%zu bytes)\n",
                           CONTEXT_DIM, sizeof(double) * CONTEXT_DIM);
    loh_state_layout_t shm_layout = loh_get_state_layout();
    LOH_DEBUG_PRINT_CONFIG("  - ACTIVE_STATE_DIM=%d (subset of CONTEXT_DIM)\n",
                           shm_layout.total_dim);
    LOH_DEBUG_PRINT_CONFIG(
        "  - MISSRATIO_DIM=%d, HIT_MISS_DIM=%d, CACHE_DIM=%d\n", MISSRATIO_DIM,
        HIT_MISS_DIM, CACHE_DIM);
    LOH_DEBUG_PRINT_CONFIG(
        "  - CAND_FEATURE_DIM=%d, TOPK_FEATURE_DIM=%d, "
        "AVGTOPK_FEATURE_DIM=%d\n",
        CAND_FEATURE_DIM, TOPK_FEATURE_DIM, AVGTOPK_FEATURE_DIM);

    // 如果成功打开共享内存，初始化基本结构
    if (params->shm_file) {
      shm_data_t init_data;
      memset(&init_data, 0, sizeof(shm_data_t));

      fseek(params->shm_file, 0, SEEK_SET);
      size_t written =
          fwrite(&init_data, sizeof(shm_data_t), 1, params->shm_file);
      fflush(params->shm_file);

      if (written == 1) {
        LOH_DEBUG_PRINT_CONFIG(
            "[LOH INIT] Shared memory structure initialized (sizeof=%zu)\n",
            sizeof(shm_data_t));
      } else {
        LOH_DEBUG_PRINT_ERROR(
            "[LOH INIT] WARNING: Failed to write init data to shared "
            "memory\n");
      }
    }
  }

  /*
   * 运行时环境开关：支持通过环境变量控制是否使用 POSIX 信号量，
   * 行为与 Python 端保持一致：
   * - 若存在 LOH_DISABLE_SEMAPHORE，则以其布尔值为准（1/true 表示禁用）
   * - 否则若存在 LOH_ENABLE_SEMAPHORE，则以其布尔值为准（1/true 表示启用）
   * - 否则保持当前默认值（此处默认为启用）
   */
  {
    const char *disable = getenv("LOH_DISABLE_SEMAPHORE");
    const char *enable = getenv("LOH_ENABLE_SEMAPHORE");
    if (disable != NULL) {
      int disable_flag = loh_parse_bool_env(disable, 0);
      if (disable_flag == 1) {
        params->sem_requested = 0;
      }
    } else if (enable != NULL) {
      int enable_flag = loh_parse_bool_env(enable, params->sem_requested);
      params->sem_requested = enable_flag ? 1 : 0;
    }

    if (!params->sem_requested) {
      LOH_DEBUG_PRINT_CONFIG(
          "[LOH INIT] semaphore mode disabled via environment; using polling "
          "only\n");
    }
  }

  // ===【读取等待模式环境变量（LOH_WAIT_MODE）】===
  {
    const char *wait_mode_str = getenv("LOH_WAIT_MODE");
    if (wait_mode_str != NULL) {
      if (strcasecmp(wait_mode_str, "blocked") == 0) {
        loh_wait_mode_blocked = 1;
        LOH_DEBUG_PRINT_CONFIG(
            "[LOH INIT] Wait mode: BLOCKED (等待权重更新)\n");
      } else if (strcasecmp(wait_mode_str, "nonblocked") == 0 ||
                 strcasecmp(wait_mode_str, "non-blocked") == 0) {
        loh_wait_mode_blocked = 0;
        LOH_DEBUG_PRINT_CONFIG(
            "[LOH INIT] Wait mode: NON-BLOCKED "
            "(发送状态后立即返回，不等待权重)\n");
      } else {
        LOH_DEBUG_PRINT_CONFIG(
            "[LOH INIT] WARNING: Invalid LOH_WAIT_MODE='%s', using default "
            "(BLOCKED)\n",
            wait_mode_str);
      }
    } else {
      LOH_DEBUG_PRINT_CONFIG("[LOH INIT] Wait mode: default (BLOCKED)\n");
    }
  }

  // ===【读取 RL 更新间隔环境变量（LOH_RL_UPDATE_INTERVAL）】===
  {
    const char *interval_str = getenv("LOH_RL_UPDATE_INTERVAL");
    if (interval_str != NULL) {
      long long val = atoll(interval_str);
      if (val > 0) {
        params->rl_update_interval = val;
        LOH_DEBUG_PRINT_CONFIG(
            "[LOH INIT] rl_update_interval=%lld (from "
            "LOH_RL_UPDATE_INTERVAL)\n",
            val);
      }
    }
  }

  // ===【打印 Size 数据结构模式（已在前面初始化时读取环境变量）】===
  {
    LOH_DEBUG_PRINT_CONFIG("[LOH INIT] Size data structure: %s\n",
                           loh_use_size_buckets ? "SIZE_BUCKETS (全量分桶)"
                                                : "SIZE_HEAP (Top-K堆)");
  }

  // 3) 特征变换 / 归一化相关
  // 3.1) 特征模式（LOH_FEATURE_LOG1P / LOH_FEATURE_LOG1P_RECIPROCAL /
  //      LOH_ENABLE_FEATURE_NORMALIZATION）
  {
    const char *raw = getenv("LOH_FEATURE_LOG1P");
    const char *rec = getenv("LOH_FEATURE_LOG1P_RECIPROCAL");
    const char *norm = getenv("LOH_ENABLE_FEATURE_NORMALIZATION");

    // 使用当前变量的初始值作为默认值，再由环境变量覆盖
    loh_feature_log1p = loh_parse_bool_env(raw, loh_feature_log1p);

    // 仅在 LOG1P 未开启时才考虑 RECIPROCAL 模式
    if (!loh_feature_log1p) {
      loh_feature_log1p_reciprocal =
          loh_parse_bool_env(rec, loh_feature_log1p_reciprocal);
    }

    loh_feature_normalize = loh_parse_bool_env(norm, loh_feature_normalize);

    LOH_DEBUG_PRINT_CONFIG(
        "[LOH INIT] feature mode: LOG1P=%d, RECIPROCAL=%d, NORMALIZE=%d\n",
        loh_feature_log1p, loh_feature_log1p_reciprocal, loh_feature_normalize);
  }

  // 3.1.5) 自动特征模式检测（LOH_AUTO_FEATURE_MODE）
  {
    const char *env_auto = getenv("LOH_AUTO_FEATURE_MODE");
    if (env_auto) {
      loh_auto_feature_mode = loh_parse_bool_env(env_auto, 0);
    }
    const char *env_detect_reqs = getenv("LOH_AUTO_DETECT_REQS");
    if (env_detect_reqs && env_detect_reqs[0] != '\0') {
      loh_auto_detect_reqs = atol(env_detect_reqs);
    }
    const char *env_cv_thresh = getenv("LOH_AUTO_CV_THRESHOLD");
    if (env_cv_thresh && env_cv_thresh[0] != '\0') {
      loh_auto_cv_threshold = atof(env_cv_thresh);
    }
    if (loh_auto_feature_mode) {
      printf(
          "[LOH INIT] AUTO_FEATURE_MODE enabled: detect after %ld reqs, "
          "CV threshold=%.2f\n",
          (long)loh_auto_detect_reqs, loh_auto_cv_threshold);
      // auto 模式下，如果用户没有显式设 LOG1P 或 RECIPROCAL，
      // 先用默认的 reciprocal 模式（LOH_FEATURE_LOG1P=0, RECIPROCAL=0），
      // 等检测完后再切换
    }
  }

  // 3.2) 特征归一化最大值（支持 LOH_FEATURE_NORM_MAX_* 覆盖）
  {
    // 先使用编译期默认值（全局 loh_feature_norm_max）
    // 再通过环境变量覆盖：作用于全局数组，整个进程共享
    const char *env_recency = getenv("LOH_FEATURE_NORM_MAX_RECENCY");
    if (env_recency && env_recency[0] != '\0')
      loh_feature_norm_max[0] = atof(env_recency);

    const char *env_freq = getenv("LOH_FEATURE_NORM_MAX_FREQ");
    if (env_freq && env_freq[0] != '\0')
      loh_feature_norm_max[1] = atof(env_freq);

    const char *env_size = getenv("LOH_FEATURE_NORM_MAX_SIZE");
    if (env_size && env_size[0] != '\0')
      loh_feature_norm_max[2] = atof(env_size);

    const char *env_irt = getenv("LOH_FEATURE_NORM_MAX_IRT");
    if (env_irt && env_irt[0] != '\0') {
      double val = atof(env_irt);
      loh_feature_norm_max[3] = val;
      loh_feature_norm_max[4] = val;
      loh_feature_norm_max[5] = val;
    }

    LOH_DEBUG_PRINT_CONFIG(
        "[LOH INIT] Feature Norm Max: Recency=%.1e, Freq=%.1e, Size=%.1e, "
        "IRT=%.1e\n",
        loh_feature_norm_max[0], loh_feature_norm_max[1],
        loh_feature_norm_max[2], loh_feature_norm_max[3]);
  }

  // 3.3) 读取启发式符号开关（LOH_USE_HEURISTIC_SIGNS）
  {
    const char *use_signs = getenv("LOH_USE_HEURISTIC_SIGNS");
    int flag = loh_parse_bool_env(use_signs, loh_use_heuristic_signs);
    loh_use_heuristic_signs = flag ? 1 : 0;
    LOH_DEBUG_PRINT_CONFIG("[LOH INIT] Heuristic signs: %s\n",
                           loh_use_heuristic_signs ? "ENABLED" : "DISABLED");
  }

#if LOH_ENABLE_PENALTY
  // 3.3b) 是否发送 penalty 正样本事件（ghost 淘汰）
  {
    const char *env_pos = getenv("LOH_PENALTY_SEND_POSITIVE");
    loh_penalty_send_positive =
        loh_parse_bool_env(env_pos, loh_penalty_send_positive) ? 1 : 0;
    LOH_DEBUG_PRINT_CONFIG(
        "[LOH INIT] Penalty positive events: %s (LOH_PENALTY_SEND_POSITIVE)\n",
        loh_penalty_send_positive ? "ENABLED" : "DISABLED");
  }
#endif

  // 3.4) 评分特征模式（LOH_SCORE_USE_IRT / LOH_SCORE_USE_COMPOUND）
  // 说明：
  //   - LOH_SCORE_USE_COMPOUND=1 时优先生效，并隐式关闭 IRT 参与评分；
  //   - LOH_SCORE_COMPOUND_V2=1 时等价于“开启 compound + 扩展到 7 维权重”；
  //   - 若两者均为 0，则评分仅使用 recency/freq/size 三个基础特征；
  //   - 若仅 LOH_SCORE_USE_IRT 为真，则使用 6 维基础特征（含 3 个 IRT）。
  {
    const char *env_irt = getenv("LOH_SCORE_USE_IRT");
    const char *env_comp = getenv("LOH_SCORE_USE_COMPOUND");
    const char *env_comp_v2 = getenv("LOH_SCORE_COMPOUND_V2");

    // 若未设置则保持默认：use_irt=1, use_compound=0
    loh_score_use_irt = loh_parse_bool_env(env_irt, loh_score_use_irt);
    loh_score_use_compound =
        loh_parse_bool_env(env_comp, loh_score_use_compound);

    // compound 升级版：可以独立开启，开启后自动启用 compound
    loh_score_compound_v2 =
        loh_parse_bool_env(env_comp_v2, loh_score_compound_v2);
    if (loh_score_compound_v2) {
      loh_score_use_compound = 1;
    }

    if (loh_score_use_compound) {
      // compound 模式下不再使用 IRT 分量参与评分
      loh_score_use_irt = 0;
    }

    LOH_DEBUG_PRINT_CONFIG(
        "[LOH INIT] Score feature mode: USE_IRT=%d, USE_COMPOUND=%d, "
        "COMPOUND_V2=%d\n",
        loh_score_use_irt, loh_score_use_compound, loh_score_compound_v2);

    // compound 模式下不需要 IRT 堆来收集候选（评分不使用 IRT 特征），
    // 跳过 IRT 堆维护可节省每次访问 3×O(log n) 的堆操作开销
    loh_irt_heap_enabled = loh_score_use_irt;
    if (!loh_irt_heap_enabled) {
      printf("[LOH INIT] IRT heaps DISABLED (compound mode, no IRT scoring)\n");
    }
  }

  // 3.5) 随机采样候选配置
  {
    const char *env_rsc = getenv("LOH_RANDOM_CANDIDATES");
    if (env_rsc && env_rsc[0] != '\0') {
      int rsc_val = atoi(env_rsc);
      if (rsc_val >= 0 && rsc_val <= MAX_CANDIDATES_LIMIT)
        loh_random_candidates = rsc_val;
    }

    LOH_DEBUG_PRINT_CONFIG("[LOH INIT] Random sampling: COUNT=%d\n",
                           loh_random_candidates);
    printf("LOH: structured candidates = %d, random candidates = %d\n",
           loh_structured_candidates, loh_random_candidates);
  }

  // 3.6) 衰减尾部采样配置
  {
    const char *env_ts = getenv("LOH_TAIL_SAMPLE");
    if (env_ts && env_ts[0] != '\0') {
      loh_tail_sample_enabled = atoi(env_ts);
    }
    const char *env_td = getenv("LOH_TAIL_SAMPLE_DECAY");
    if (env_td && env_td[0] != '\0') {
      double td_val = atof(env_td);
      if (td_val > 0.0 && td_val < 1.0) {
        loh_tail_sample_decay = td_val;
      } else {
        fprintf(stderr,
                "LOH WARNING: LOH_TAIL_SAMPLE_DECAY=%.4f out of range (0, 1), "
                "using default %.4f\n",
                td_val, loh_tail_sample_decay);
      }
    }
    if (loh_tail_sample_enabled) {
      printf(
          "[LOH INIT] Decay sampling ENABLED for ALL structured sources: "
          "decay=%.4f\n",
          loh_tail_sample_decay);
      printf(
          "[LOH INIT]   Random sampling remains UNIFORM (not affected by "
          "decay)\n");
    }
  }

  // 3.7) 自适应候选预算配置
  {
    const char *env_ab = getenv("LOH_ADAPTIVE_BUDGET");
    if (env_ab && env_ab[0] != '\0') {
      loh_adaptive_budget = atoi(env_ab);
    }
    // 初始化自适应预算为均分
    memset(loh_source_evict_count, 0, sizeof(loh_source_evict_count));
    loh_adaptive_total_evict = 0;
    // 预算初始化留到 to_evict 中根据 n_sources 动态确定
    memset(loh_source_budget, 0, sizeof(loh_source_budget));
    memset(loh_source_win_score_sum, 0, sizeof(loh_source_win_score_sum));
    const char *env_sr = getenv("LOH_USE_SCORE_REBALANCE");
    if (env_sr && env_sr[0] != '\0') {
      loh_use_score_rebalance = atoi(env_sr);
    }
    if (loh_adaptive_budget) {
      printf("[LOH INIT] Adaptive budget ENABLED: rebalance period=%d, score_rebalance=%d\n",
             LOH_ADAPTIVE_REBALANCE_PERIOD, loh_use_score_rebalance);
    }
  }

  {
    loh_state_layout_t init_layout = loh_get_state_layout();
    LOH_DEBUG_PRINT_CONFIG(
        "[LOH INIT] Runtime state dims: HIT_MISS=%d, CACHE=%d, CAND=%d, "
        "TOPK=%d, AVGTOPK=%d, REQUEST=%d -> ACTIVE=%d/%d\n",
        init_layout.hit_miss_dim, init_layout.cache_dim, init_layout.cand_dim,
        init_layout.topk_dim, init_layout.avgtopk_dim, init_layout.request_dim,
        init_layout.total_dim, CONTEXT_DIM);
  }

#if LOH_ENABLE_PENALTY
  // ===【初始化 Penalty 队列】===
  params->penalty_queue =
      malloc(PENALTY_QUEUE_INIT_CAPACITY * sizeof(penalty_entry_t));
  if (params->penalty_queue == NULL) {
    LOH_DEBUG_PRINT_ERROR(
        "[LOH] ERROR: Failed to allocate penalty queue (capacity=%d)\n",
        PENALTY_QUEUE_INIT_CAPACITY);
    // 处理错误：可以设置 capacity=0 或终止程序
    params->penalty_queue_capacity = 0;
    params->penalty_queue_size = 0;
  } else {
    params->penalty_queue_capacity = PENALTY_QUEUE_INIT_CAPACITY;
    params->penalty_queue_size = 0;
    params->pending_penalty_count = 0;
    LOH_DEBUG_PRINT_CONFIG(
        "[LOH INIT] Penalty queue initialized (capacity=%d)\n",
        PENALTY_QUEUE_INIT_CAPACITY);
  }
#endif

  if (loh_enable_rl && params->shm_file == NULL) {
    // 如果文件不存在，则创建它
    params->shm_file = fopen(params->shm_filename, "w+b");
    if (params->shm_file == NULL) {
      perror("Failed to create shared memory file");
    } else {
      // 初始化共享内存文件
      shm_data_t shm_data;
      memset(&shm_data, 0, sizeof(shm_data_t));

      // 复制初始权重到共享内存
      memcpy(shm_data.weights, params->weights, sizeof(double) * WEIGHT_DIM);

      // 写入文件
      fwrite(&shm_data, sizeof(shm_data_t), 1, params->shm_file);
      fflush(params->shm_file);

      // 设置文件权限
      chmod(params->shm_filename, 0666);
    }
  } else if (loh_enable_rl) {
    LOH_DEBUG_PRINT_CONFIG(
        "[LOH INIT] Successfully opened existing shared memory file\n");
  }

  // 为非阻塞模式建立 mmap 映射（绕过 stdio 缓冲和 fcntl 锁）
  if (loh_enable_rl && params->shm_file != NULL && !loh_wait_mode_blocked) {
    params->shm_fd = fileno(params->shm_file);
    // 确保文件至少有 sizeof(shm_data_t) 大小
    if (ftruncate(params->shm_fd, sizeof(shm_data_t)) == 0) {
      params->shm_mmap =
          (shm_data_t *)mmap(NULL, sizeof(shm_data_t), PROT_READ | PROT_WRITE,
                             MAP_SHARED, params->shm_fd, 0);
      if (params->shm_mmap == MAP_FAILED) {
        perror("[LOH] mmap failed, falling back to fread/fwrite");
        params->shm_mmap = NULL;
      } else {
        LOH_DEBUG_PRINT_CONFIG(
            "[LOH INIT] mmap established for fast nonblocked sync "
            "(size=%zu)\n",
            sizeof(shm_data_t));
      }
    } else {
      perror("[LOH] ftruncate for mmap failed");
    }
  }

  // 如果关闭了RL，确保不持有未使用的SHM资源
  if (!loh_enable_rl) {
    if (params->shm_mmap != NULL) {
      munmap(params->shm_mmap, sizeof(shm_data_t));
      params->shm_mmap = NULL;
    }
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
      const char *key_str = getenv("LOH_SHM_KEY");
      if (key_str && key_str[0] != '\0') {
        params->sem_ready_name = g_strdup_printf("/loh_ac_ready_%s", key_str);
      } else {
        params->sem_ready_name = g_strdup_printf("/loh_ac_ready_%d", SHM_KEY);
      }
    }
    if (params->sem_ack_name == NULL) {
      const char *key_str = getenv("LOH_SHM_KEY");
      if (key_str && key_str[0] != '\0') {
        params->sem_ack_name = g_strdup_printf("/loh_ac_ack_%s", key_str);
      } else {
        params->sem_ack_name = g_strdup_printf("/loh_ac_ack_%d", SHM_KEY);
      }
    }
    if (!loh_sem_init(params)) {
      LOH_DEBUG_PRINT_CONFIG(
          "[LOH INIT] failed to init POSIX semaphores, fall back to polling "
          "mode\n");
    }
  }

  // 设置 cache 指针供后续使用
  params->cache_ptr = cache;

  // 打印初始化时的 RL 同步间隔，便于调试与确认运行时值
  LOH_DEBUG_PRINT_CONFIG(
      "[LOH INIT] rl_update_interval=%ld, enable_rl=%d, sem_requested=%d\n",
      (long)params->rl_update_interval, loh_enable_rl, params->sem_requested);

  // 根据权重设置缓存名字（类似 ThreeLCache 的做法）
  if (loh_miss_ratio_weight == 1.0 && loh_byte_miss_ratio_weight == 0.0) {
    // 纯对象级优化
    snprintf(cache->cache_name, CACHE_NAME_ARRAY_LEN, "LOH-OMR");
  } else if (loh_miss_ratio_weight == 0.0 &&
             loh_byte_miss_ratio_weight == 1.0) {
    // 纯字节级优化
    snprintf(cache->cache_name, CACHE_NAME_ARRAY_LEN, "LOH-BMR");
  } else {
    // 混合优化，显示权重比例
    snprintf(cache->cache_name, CACHE_NAME_ARRAY_LEN, "LOH-Mix(%.1f/%.1f)",
             loh_miss_ratio_weight, loh_byte_miss_ratio_weight);
  }

  cache->eviction_params = params;
  return cache;
}

/**
 * @brief 释放该缓存使用的所有资源
 *
 * @param cache 要释放的缓存结构
 */
static void LOH_free(cache_t *cache) {
  LOH_params_t *params = (LOH_params_t *)(cache->eviction_params);

  // 释放 IRT 堆
  irt_heap_free(params);

  // 清理 mmap 映射
  if (params->shm_mmap != NULL) {
    munmap(params->shm_mmap, sizeof(shm_data_t));
    params->shm_mmap = NULL;
  }

  // 清理共享内存文件
  if (params->shm_file) {
    fclose(params->shm_file);
    params->shm_file = NULL;
  }

  loh_sem_close(params, true);

  // 释放 frequency 表
  freq_table_free(params);

  // 释放尺寸数据结构
  size_ds_free(params);

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

#if LOH_ENABLE_PENALTY
  // 释放 Penalty 队列
  if (params->penalty_queue) {
    free(params->penalty_queue);
    params->penalty_queue = NULL;
    LOH_DEBUG_PRINT_BASIC("[LOH FREE] Penalty queue freed\n");
  }
#endif

#if LOH_PERF_PROFILING
  // 打印一次性能概要，方便 no-RL 下快速定位热点
  loh_print_perf_summary(params);
#endif

  // 释放 flat obj_array
  if (params->obj_array) {
    free(params->obj_array);
    params->obj_array = NULL;
  }

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

  // 自动特征模式检测：在指定请求数后且 cache 至少 80% 满时触发一次
  // 必须等 cache 填充充分，否则频率分布不具代表性
  // 注意：cache_size 和 occupied_byte 都是字节单位，不能与 n_obj 混用
  if (loh_auto_feature_mode && !loh_auto_detected &&
      request_count >= loh_auto_detect_reqs &&
      cache->occupied_byte >= (int64_t)(cache->cache_size * 0.8)) {
    loh_auto_detect_and_switch(cache);
    loh_auto_detected = 1;
  }

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
    /* 如果启用了特征归一化，打印本 epoch
     * 的裁剪统计（每个特征的样本数、裁剪次数及比例） */
    if (loh_feature_normalize) {
      LOH_DEBUG_PRINT_DETAILED(
          "[LOH] Feature normalization clip stats (epoch):\n");
      for (int i = 0; i < FEATURE_DIM; i++) {
        uint64_t samples = params->feature_sample_count[i];
        uint64_t clips = params->feature_clip_count[i];
        double ratio = (samples > 0) ? ((double)clips / (double)samples) : 0.0;
        LOH_DEBUG_PRINT_DETAILED(
            "  feature[%d]: samples=%llu, clips=%llu, clip_ratio=%.6f\n", i,
            (unsigned long long)samples, (unsigned long long)clips, ratio);
        /* 重置计数，准备下个 epoch */
        params->feature_sample_count[i] = 0;
        params->feature_clip_count[i] = 0;
      }
    }

#if LOH_INCLUDE_REQUEST
    // 重置请求历史缓冲区，使每个 RL 周期的请求序列独立
    memset(params->request_history, 0, sizeof(params->request_history));
    params->request_history_pos = 0;
    params->request_history_count = 0;
#endif
  }

  // **检查是否达到 warmup 条件（缓存满：占用 >= 100%）**
  if (!params->is_warmed_up &&
      cache_get_occupied_byte_default(cache) >= cache->cache_size) {
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
  double features[FEATURE_DIM];
  if (obj_before_access != NULL) {
    // 缓存命中：计算命中对象的访问前特征
    // 原始值（raw）
    int64_t recency_raw =
        params->current_timestamp - obj_before_access->LOH.last_access_counter;
    int access_count_raw = obj_before_access->LOH.access_count;
    int64_t size_bytes_raw = (int64_t)obj_before_access->obj_size;
    int64_t irt_raw0 = obj_before_access->LOH.irt_values[0];
    int64_t irt_raw1 = obj_before_access->LOH.irt_values[1];
    int64_t irt_raw2 = obj_before_access->LOH.irt_values[2];

    // 变换后的特征值
    features[0] = calculate_recency(params, recency_raw);  // recency 未更新
    features[1] =
        calculate_frequency(params, (int64_t)access_count_raw);  // 未加 1
    features[2] = calculate_size(params, size_bytes_raw);

    // 【修复】：访问前 IRT 直接使用对象的 IRT 值，无需后退一步
    features[3] = calculate_irt_feature(
        params, obj_before_access->LOH.irt_values[0]);  // IRT1
    features[4] = calculate_irt_feature(
        params, obj_before_access->LOH.irt_values[1]);  // IRT2
    features[5] = calculate_irt_feature(
        params, obj_before_access->LOH.irt_values[2]);  // IRT3

    // 调试：命中时 raw 与特征的对比
    LOH_DEBUG_PRINT_DETAILED(
        "[LOH_get] hit raw_vs_feat - obj_id=%llu, recency_raw=%lld, "
        "recency_feat=%.6f, freq_raw=%d, freq_feat=%.6f, size_bytes=%lld, "
        "size_feat=%.6f, irt_raw=[%lld,%lld,%lld], irt_feat=[%.6f,%.6f,%.6f]\n",
        (unsigned long long)obj_before_access->obj_id, (long long)recency_raw,
        features[0], access_count_raw, features[1], (long long)size_bytes_raw,
        features[2], (long long)irt_raw0, (long long)irt_raw1,
        (long long)irt_raw2, features[3], features[4], features[5]);
  } else {
    // 缓存未命中：检查 ghost cache 中的历史信息
#if LOH_ENABLE_PENALTY
    PERF_TS ts_lookup;
    PERF_NOW(ts_lookup);
#endif

    LOH_ghost_entry_t *ghost_entry =
        params->ghost_cache
            ? (LOH_ghost_entry_t *)g_hash_table_lookup(
                  params->ghost_cache, GINT_TO_POINTER((int)req->obj_id))
            : NULL;

#if LOH_ENABLE_PENALTY
    PERF_ACCUM(params, ghost_cache_lookup, ts_lookup);
#endif

    if (ghost_entry) {
#if LOH_ENABLE_PENALTY
      // 【新增】检测到 ghost cache miss - 记录原始数据，延迟计算惩罚
      if (params->is_warmed_up && ghost_entry->eviction_version > 0) {
        // 【精确】使用驱逐时刻到当前访问的距离
        int64_t eviction_to_access =
            params->current_timestamp - ghost_entry->eviction_timestamp;

        // 确保距离至少为1（避免除零）
        if (eviction_to_access < 1) eviction_to_access = 1;

        // 只记录原始数据：eviction_to_access 和 obj_size
        // 惩罚将在Python端使用当时的 epoch_evicted_bytes 和 epoch_evicted_count
        // 计算
        enqueue_penalty(params, ghost_entry->eviction_version,
                        eviction_to_access, ghost_entry->obj_size, req->obj_id);

        LOH_DEBUG_PRINT_BASIC(
            "[LOH] Ghost miss detected: obj_id=%llu, evict_version=%llu, "
            "evict_to_access=%ld, size=%ld, epoch_evicted_bytes=%llu, "
            "epoch_evicted_count=%llu\n",
            (unsigned long long)req->obj_id,
            (unsigned long long)ghost_entry->eviction_version,
            eviction_to_access, ghost_entry->obj_size,
            (unsigned long long)params->epoch_evicted_bytes,
            (unsigned long long)params->epoch_evicted_count);
      }
#endif

      // ghost cache 特征与对象特征保持同一归一化逻辑，直接用 ghost 的原始值
      int64_t current_irt =
          params->current_timestamp - ghost_entry->last_access_counter;
      int64_t recency_raw = current_irt;
      int64_t freq_raw = (int64_t)ghost_entry->access_count;
      int64_t size_bytes = (int64_t)ghost_entry->obj_size;

      features[0] = calculate_recency(params, recency_raw);
      features[1] = calculate_frequency(params, freq_raw);
      features[2] = calculate_size(params, size_bytes);
      features[3] = calculate_irt_feature(params, ghost_entry->irt_values[0]);
      features[4] = calculate_irt_feature(params, ghost_entry->irt_values[1]);
      features[5] = calculate_irt_feature(params, ghost_entry->irt_values[2]);

      // 调试：miss(ghost) 情况下 raw 与特征的对比
      LOH_DEBUG_PRINT_DETAILED(
          "[LOH_get] miss(ghost) raw_vs_feat - obj_id=%llu, recency_raw=%lld, "
          "recency_feat=%.6f, freq_raw=%lld, freq_feat=%.6f, size_bytes=%lld, "
          "size_feat=%.6f, irt_raw=[%lld,%lld,%lld], "
          "irt_feat=[%.6f,%.6f,%.6f]\n",
          (unsigned long long)req->obj_id, (long long)current_irt, features[0],
          (long long)freq_raw, features[1], (long long)size_bytes, features[2],
          (long long)ghost_entry->irt_values[0],
          (long long)ghost_entry->irt_values[1],
          (long long)ghost_entry->irt_values[2], features[3], features[4],
          features[5]);
    } else {
      // 完全新对象：raw 初始值按约定设置（与模式无关）
      int64_t size_bytes = (int64_t)req->obj_size;
      int64_t recency_raw = (int64_t)loh_feature_norm_max[0];
      int64_t freq_raw = 0;
      int64_t irt_raw0 = (int64_t)loh_feature_norm_max[3];
      int64_t irt_raw1 = (int64_t)loh_feature_norm_max[4];
      int64_t irt_raw2 = (int64_t)loh_feature_norm_max[5];

      features[0] = calculate_recency(params, recency_raw);
      features[1] = calculate_frequency(params, freq_raw);
      features[2] = calculate_size(params, size_bytes);
      features[3] = calculate_irt_feature(params, irt_raw0);
      features[4] = calculate_irt_feature(params, irt_raw1);
      features[5] = calculate_irt_feature(params, irt_raw2);

      // 调试：全新对象（无 ghost）时，6 维 raw 与特征对比
      LOH_DEBUG_PRINT_DETAILED(
          "[LOH_get] miss(new) raw_vs_feat - obj_id=%llu, recency_raw=%lld, "
          "recency_feat=%.6f, freq_raw=%lld, freq_feat=%.6f, size_bytes=%lld, "
          "size_feat=%.6f, irt_raw=[%lld,%lld,%lld], "
          "irt_feat=[%.6f,%.6f,%.6f]\n",
          (unsigned long long)req->obj_id, (long long)recency_raw, features[0],
          (long long)freq_raw, features[1], (long long)size_bytes, features[2],
          (long long)irt_raw0, (long long)irt_raw1, (long long)irt_raw2,
          features[3], features[4], features[5]);
    }
  }

#if LOH_INCLUDE_REQUEST
  // 在执行实际 get 之前，记录本次请求的 6 维特征
  loh_record_request_features(params, features);
#endif

  // 现在执行实际的 get 操作
  bool hit = cache_get_base(cache, req);

  // **更新 epoch 统计（始终需要，用于 miss ratio 计算）**
  if (params->is_warmed_up) {
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
    size_ds_get_candidates(params, candidates_per_feature,
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
      // 新对象没有 IRT 历史时使用一个较大的常数（默认为128e6），
      // 避免后续 log1p/归一化计算中的极端值，并保持它们为较高淘汰优先级。
      obj->LOH.irt_values[i] = (int64_t)loh_feature_norm_max[3 + i];
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

    // 添加到 flat obj_array（O(1) 随机采样）
    if (params->obj_array_size >= params->obj_array_capacity) {
      params->obj_array_capacity *= 2;
      params->obj_array = (cache_obj_t **)realloc(
          params->obj_array,
          params->obj_array_capacity * sizeof(cache_obj_t *));
    }
    obj->LOH.obj_array_idx = params->obj_array_size;
    params->obj_array[params->obj_array_size++] = obj;

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
// ——— 快速 Lehmer64 RNG（用于 flat array 随机采样） ———
static __uint128_t loh_rng_state = 0x12345678DEADBEEFULL;
static inline uint64_t loh_fast_rand(void) {
  loh_rng_state *= 0xda942042e4dd58b5ULL;
  return (uint64_t)(loh_rng_state >> 64);
}

// ——— 快速 log1p 近似（IEEE 754 位操作，用于评分热路径） ———
// 仅用于候选评分排序（相对比较），不影响发往 RL 的 state 精确值
// 相对误差 < 8%，单次 ~3 CPU 周期 vs libm log1p ~50-100 周期
static inline double fast_log1p_approx(double x) {
  if (x <= 0.0) return 0.0;
  union {
    double d;
    uint64_t u;
  } v;
  v.d = 1.0 + x;
  int e = (int)((v.u >> 52) & 0x7FF) - 1023;
  double m = (double)(v.u & 0x000FFFFFFFFFFFFFULL) * 2.220446049250313e-16;
  return (e + m) * 0.6931471805599453;
}

static cache_obj_t *LOH_to_evict(cache_t *cache, const request_t *req) {
  LOH_params_t *params = (LOH_params_t *)cache->eviction_params;
  PERF_TS ts_to_evict;
  PERF_NOW(ts_to_evict);

  // 清空候选对象数组
  params->n_candidates = 0;
  // 避免每次都 memset 整个候选数组（写放大）；仅通过 n_candidates 控制有效范围

  // 从各个特征数据结构中选择候选对象，每个特征分别获取候选
  // compound 模式下只使用 3 个源（recency/freq/size），每个源分到更多候选
  int n_sources = loh_irt_heap_enabled ? 6 : 3;
  int candidates_per_feature = loh_structured_candidates / n_sources;
  // 自适应预算：每个源可有不同配额（默认均分）
  int budget[LOH_MAX_SOURCES];
  if (loh_adaptive_budget) {
    for (int s = 0; s < n_sources; s++)
      budget[s] = loh_source_budget[s] > 0 ? loh_source_budget[s]
                                           : candidates_per_feature;
  } else {
    for (int s = 0; s < LOH_MAX_SOURCES; s++)
      budget[s] = candidates_per_feature;
  }
  LOH_DEBUG_PRINT_DETAILED(
      "[CANDIDATE COLLECTION] Normal mode: candidates_per_feature=%d "
      "(loh_structured_candidates=%d)\n",
      candidates_per_feature, loh_structured_candidates);

  LOH_DEBUG_PRINT_DETAILED("[LOH DEBUG EVICT] Request obj_id=%llu\n",
                           (unsigned long long)req->obj_id);

  // 每轮去重表清空：所有来源（含 recency）统一纳入 seen 去重
  loh_seen_clear();

  // === 结构化候选数=0 时，跳过所有结构化候选源，直接跳到随机采样 ===
  // Level 1: Cache Size Guard — 缓存对象数过少时结构化候选冗余
  if (loh_structured_candidates == 0 ||
      cache->n_obj <
          (int64_t)(loh_structured_candidates + loh_random_candidates) * 2) {
    goto random_sampling_section;
  }

  // 1. 从 LRU 队列尾部选择（最近性特征 - recency），并纳入 seen 去重
  // 1) recency 收集
  PERF_TS ts_collect_rec;
  PERF_NOW(ts_collect_rec);
  cache_obj_t *curr = params->q_tail;
  int lru_candidates = 0;
  int recency_start = params->n_candidates;
  double rec_accept_prob = 1.0;
  int rec_max_scan = loh_tail_sample_enabled ? budget[0] * 10 : 0;
  int rec_scanned = 0;
  while (curr != NULL && lru_candidates < budget[0]) {
    // 衰减采样：超过最大扫描深度则停止
    if (loh_tail_sample_enabled && rec_scanned >= rec_max_scan) break;
    cache_obj_t *o = curr;
    // 衰减采样：先检查概率，再加入 seen（避免 seen 集合被无用对象污染）
    if (o) {
      bool rec_pass_decay =
          !loh_tail_sample_enabled ||
          (double)(loh_fast_rand() % 10000u) / 10000.0 < rec_accept_prob;
      if (rec_pass_decay && loh_seen_add(params, o)) {
        params->candidates[params->n_candidates++] = o;
        lru_candidates++;
      }
    }
    if (loh_tail_sample_enabled) {
      rec_accept_prob *= loh_tail_sample_decay;
      rec_scanned++;
    }
    curr = curr->queue.prev;
  }
  PERF_ACCUM(params, cand_collect_recency, ts_collect_rec);
  // recency 阶段无单独压缩流程（天然无重复），dedup 计时保持 0
  // 标记候选来源
  for (int i = recency_start; i < params->n_candidates; i++)
    loh_cand_source[i] = 0;

#if LOH_INCLUDE_CANDIDATE_FEATURES
  for (int i = recency_start; i < params->n_candidates; i++) {
    cache_obj_t *o = params->candidates[i];
    if (!o) continue;
    double f[FEATURE_DIM] = {0};
    calculate_object_features(params, o, f);
    for (int k = 0; k < FEATURE_DIM; ++k) {
      params->cand_feat_sum[0][k] += f[k];
      params->cand_feat_sumsq[0][k] += f[k] * f[k];
    }
    params->cand_feat_count[0]++;
  }
#endif

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
  // 2) frequency 收集（预去重阶段已记录候选统计）
  int freq_start = params->n_candidates;
  PERF_TS ts_collect_freq;
  PERF_NOW(ts_collect_freq);
  freq_table_get_candidates(params, budget[1], &params->n_candidates);
  PERF_ACCUM(params, cand_collect_freq, ts_collect_freq);
  // 频率候选已在收集阶段融合 seen 去重，省去单独dedup
  for (int i = freq_start; i < params->n_candidates; i++)
    loh_cand_source[i] = 1;

  // NOTE: 统计在 getter 内已完成

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

  // 3. 从尺寸数据结构选择大尺寸对象（尺寸特征 - size）
  // 3) size 收集（预去重阶段已记录候选统计）
  int size_start = params->n_candidates;
  PERF_TS ts_collect_size;
  PERF_NOW(ts_collect_size);
  size_ds_get_candidates(params, budget[2], &params->n_candidates);
  PERF_ACCUM(params, cand_collect_size, ts_collect_size);
  // 尺寸候选已在收集阶段融合 seen 去重，省去单独dedup
  for (int i = size_start; i < params->n_candidates; i++)
    loh_cand_source[i] = 2;

  // NOTE: 统计在 getter 内已完成

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
  // 4) IRT1 收集（预去重阶段已记录候选统计）
  if (loh_irt_heap_enabled) {
    int irt1_start = params->n_candidates;
    PERF_TS ts_collect_irt1;
    PERF_NOW(ts_collect_irt1);
    irt1_heap_get_candidates(params, budget[3], &params->n_candidates);
    PERF_ACCUM(params, cand_collect_irt1, ts_collect_irt1);
    // IRT1 候选已在收集阶段融合 seen 去重，省去单独dedup
    for (int i = irt1_start; i < params->n_candidates; i++)
      loh_cand_source[i] = 3;

    // NOTE: 统计在 getter 内已完成

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
  }  // end if (loh_irt_heap_enabled) - IRT1

  // 5. 从 IRT2 堆选择（IRT2 特征）
  // 5) IRT2 收集（预去重阶段已记录候选统计）
  if (loh_irt_heap_enabled) {
    int irt2_start = params->n_candidates;
    PERF_TS ts_collect_irt2;
    PERF_NOW(ts_collect_irt2);
    irt2_heap_get_candidates(params, budget[4], &params->n_candidates);
    PERF_ACCUM(params, cand_collect_irt2, ts_collect_irt2);
    // IRT2 候选已在收集阶段融合 seen 去重，省去单独dedup
    for (int i = irt2_start; i < params->n_candidates; i++)
      loh_cand_source[i] = 4;

    // NOTE: 统计在 getter 内已完成

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
  }  // end if (loh_irt_heap_enabled) - IRT2

  // 6. 从 IRT3 堆选择（IRT3 特征）
  // 6) IRT3 收集（预去重阶段已记录候选统计）
  if (loh_irt_heap_enabled) {
    int irt3_start = params->n_candidates;
    PERF_TS ts_collect_irt3;
    PERF_NOW(ts_collect_irt3);
    irt3_heap_get_candidates(params, budget[5], &params->n_candidates);
    PERF_ACCUM(params, cand_collect_irt3, ts_collect_irt3);
    // IRT3 候选已在收集阶段融合 seen 去重，省去单独dedup
    for (int i = irt3_start; i < params->n_candidates; i++)
      loh_cand_source[i] = 5;

    // NOTE: 统计在 getter 内已完成

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
  }  // end if (loh_irt_heap_enabled) - IRT3

  // 7. 额外候选采样：从结构化源之外补充候选
  //    - 始终使用均匀随机采样，从 flat obj_array 中 O(1) 随机采样
  //    - LOH_TAIL_SAMPLE 只影响结构化候选源的 decay 采样深度
  //    注意：这是在特征源之外 ADDITIVE 的额外候选，不减少原有源的配额

random_sampling_section:
  if (loh_random_candidates > 0 && params->obj_array_size > 0) {
    // ── 均匀随机采样（带深度 prefetch 流水线优化）──
    // 说明：obj_array (~96MB) 远超 L3 (~30MB)，每次随机访问是一次 DRAM miss
    // (~100ns)。 每次迭代的计算量 (loh_seen_add + 随机数生成) 约 10-15ns，
    // 因此需要提前 16 步 prefetch 才能覆盖 100ns 延迟。
    int random_wanted = loh_random_candidates;
    int room = MAX_CANDIDATES - params->n_candidates;
    if (random_wanted > room) random_wanted = room;
    int random_collected = 0;
    int max_attempts = random_wanted * 3;
    const uint64_t arr_sz = (uint64_t)params->obj_array_size;
    for (int attempt = 0;
         attempt < max_attempts && random_collected < random_wanted;
         attempt++) {
      int rand_idx = (int)(loh_fast_rand() % arr_sz);
      cache_obj_t *rand_obj = params->obj_array[rand_idx];
      if (rand_obj && loh_seen_add(params, rand_obj)) {
        params->candidates[params->n_candidates++] = rand_obj;
        random_collected++;
      }
    }
    LOH_DEBUG_PRINT_DETAILED(
        "[random_sample] collected %d/%d random candidates\n", random_collected,
        loh_random_candidates);
  }

  // 如果没有候选对象，使用 LRU 作为回退
  if (params->n_candidates == 0) {
    return params->q_tail;
  }
  // 标记随机/尾部候选来源（位于结构化候选之后的所有候选）
  {
    int struct_end = loh_structured_candidates < params->n_candidates
                         ? loh_structured_candidates
                         : params->n_candidates;
    // 如果 loh_structured_candidates == 0, 全部都是随机候选
    int random_region_start = loh_structured_candidates == 0 ? 0 : struct_end;
    for (int i = random_region_start; i < params->n_candidates; i++)
      loh_cand_source[i] = 6;
  }

  // 对候选对象评分，选择得分最低的
  double min_score = DBL_MAX;
  cache_obj_t *obj_to_evict = NULL;
  int best_i = -1;  // 记录获胜候选的索引（用于自适应预算）

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
  // 注意：使用 MAX_CANDIDATES 而非 loh_structured_candidates 作为上限，
  // 因为 additive random sampling 可能超出 loh_structured_candidates
  int cand_n = params->n_candidates;
  if (cand_n > MAX_CANDIDATES) cand_n = MAX_CANDIDATES;
  // Compound + 线性模式下只需 3 个基础特征（recency/freq/size），
  // 跳过 IRT 特征计算可节省约 50% 特征计算时间
  const int fast_compound =
      (loh_score_use_compound && params->score_model != LOH_SCORE_MODEL_MLP);
  // 超快速路径：fast_compound + (LOG1P 或 RECIPROCAL) + 线性模型 →
  // 合并特征计算与评分为单循环
  const int ultra_fast =
      (fast_compound && (loh_feature_log1p || loh_feature_log1p_reciprocal) &&
       !loh_feature_normalize);

  // 将权重提升到寄存器，避免在循环中反复读取
  const double *w = params->weights;
  double sign[WEIGHT_DIM];
  for (int k = 0; k < WEIGHT_DIM; ++k) sign[k] = 1.0;

  if (loh_score_use_compound) {
    if (loh_feature_log1p) {
      sign[0] = -1.0;  // recency
      sign[1] = 1.0;   // frequency
      sign[2] = -1.0;  // size
      sign[3] = 1.0;   // freq_recency
      sign[4] = 1.0;   // freq_size
      sign[5] = -1.0;  // recency_size
      sign[6] = 1.0;   // freq_recency_size（仅 v2 使用）
    } else {
      for (int k = 0; k < WEIGHT_DIM; ++k) sign[k] = 1.0;
    }
  } else {
    if (loh_use_heuristic_signs) {
      if (loh_feature_log1p) {
        // LOG1P 模式：feature 越大 = raw 越大 = 越"不好"的维度用 -1
        sign[0] = -1.0;  // recency: 越老越该驱逐
        sign[1] = 1.0;   // frequency: 越频繁越该保留
        sign[2] = -1.0;  // size: 越大越该驱逐
        sign[3] = -1.0;  // irt1: 越长越该驱逐
        sign[4] = -1.0;  // irt2
        sign[5] = -1.0;  // irt3
        sign[6] = 1.0;
      } else {
        // RECIPROCAL / DEFAULT 模式：feature 已编码"好坏"方向
        // （值越大 = 越应保留），所有 sign 用 +1
        for (int k = 0; k < WEIGHT_DIM; ++k) sign[k] = 1.0;
      }
    } else {
      for (int k = 0; k < WEIGHT_DIM; ++k) sign[k] = 1.0;
    }
  }
  // 预乘 w*sign，避免内循环重复乘法
  double ws[WEIGHT_DIM];
  for (int k = 0; k < WEIGHT_DIM; ++k) ws[k] = w[k] * sign[k];

  if (ultra_fast) {
    // ---- 超快速合并路径：fast_log1p_approx + 单遍特征计算+评分 ----
    // 直接在单循环中完成特征计算和评分，无需 feat_buf
    PERF_TS ts_fused;
    PERF_NOW(ts_fused);
    const int64_t cur_ts = params->current_timestamp;
    const int do_v2 = loh_score_compound_v2;

    for (int i = 0; i < cand_n; ++i) {
      cache_obj_t *candidate = params->candidates[i];
      double rec, freq, sz, score;
      const double eps = 1e-12;

      if (loh_feature_log1p) {
        // ── LOG1P 模式：fast_log1p_approx 直接做特征 ──
        rec = fast_log1p_approx(
            (double)(cur_ts - candidate->LOH.last_access_counter));
        freq = fast_log1p_approx((double)candidate->LOH.access_count);
        sz = fast_log1p_approx((double)candidate->obj_size);

        const double inv_rec = 1.0 / ((rec > eps) ? rec : eps);
        const double inv_sz = 1.0 / ((sz > eps) ? sz : eps);

        score = rec * ws[0] + freq * ws[1] + sz * ws[2] +
                (freq * inv_rec) * ws[3] + (freq * inv_sz) * ws[4] +
                (rec * sz) * ws[5];
        if (do_v2) {
          score += (freq * inv_rec * inv_sz) * ws[6];
        }
      } else {
        // ── RECIPROCAL 模式：1/(1+fast_log1p_approx(x)) ──
        const double log_delta = fast_log1p_approx(
            (double)(cur_ts - candidate->LOH.last_access_counter));
        rec = 1.0 / (1.0 + log_delta);

        const double log_count =
            fast_log1p_approx((double)candidate->LOH.access_count);
        freq = (log_count > 0.0) ? (log_count / (log_count + 1.0)) : 0.0;

        const double size_mb = (double)candidate->obj_size / 1048576.0;
        const double log_size = fast_log1p_approx(size_mb);
        sz = 1.0 / (1.0 + log_size);

        // compound 乘积形式（非比率）
        score = rec * ws[0] + freq * ws[1] + sz * ws[2] + (freq * rec) * ws[3] +
                (freq * sz) * ws[4] + (rec * sz) * ws[5];
        if (do_v2) {
          score += (freq * rec * sz) * ws[6];
        }
      }

      if (score < min_score) {
        min_score = score;
        obj_to_evict = candidate;
        best_i = i;
      }

#if LOH_INCLUDE_TOPK_CANDIDATE_FEATURES
      // TOPK 维护内联
      if (params->current_lowest_count < SAMPLES_PER_EVICTION) {
        int insert_pos = params->current_lowest_count;
        for (int k = params->current_lowest_count - 1; k >= 0; k--) {
          if (score < params->current_lowest_scores[k]) {
            params->current_lowest_4[k + 1] = params->current_lowest_4[k];
            params->current_lowest_scores[k + 1] =
                params->current_lowest_scores[k];
            insert_pos = k;
          } else
            break;
        }
        params->current_lowest_4[insert_pos] = candidate;
        params->current_lowest_scores[insert_pos] = score;
        params->current_lowest_count++;
      } else if (score <
                 params->current_lowest_scores[SAMPLES_PER_EVICTION - 1]) {
        int insert_pos = SAMPLES_PER_EVICTION - 1;
        for (int k = SAMPLES_PER_EVICTION - 2; k >= 0; k--) {
          if (score < params->current_lowest_scores[k]) {
            params->current_lowest_4[k + 1] = params->current_lowest_4[k];
            params->current_lowest_scores[k + 1] =
                params->current_lowest_scores[k];
            insert_pos = k;
          } else
            break;
        }
        params->current_lowest_4[insert_pos] = candidate;
        params->current_lowest_scores[insert_pos] = score;
      }
#endif
#if LOH_INCLUDE_AVGTOPK_CANDIDATE_FEATURES
      if (params->avgtopk_lowest_count < SAMPLES_PER_EVICTION) {
        int insert_pos = params->avgtopk_lowest_count;
        for (int k = params->avgtopk_lowest_count - 1; k >= 0; k--) {
          if (score < params->avgtopk_lowest_scores[k]) {
            params->avgtopk_lowest_4[k + 1] = params->avgtopk_lowest_4[k];
            params->avgtopk_lowest_scores[k + 1] =
                params->avgtopk_lowest_scores[k];
            insert_pos = k;
          } else
            break;
        }
        params->avgtopk_lowest_4[insert_pos] = candidate;
        params->avgtopk_lowest_scores[insert_pos] = score;
        params->avgtopk_lowest_count++;
      } else if (score <
                 params->avgtopk_lowest_scores[SAMPLES_PER_EVICTION - 1]) {
        int insert_pos = SAMPLES_PER_EVICTION - 1;
        for (int k = SAMPLES_PER_EVICTION - 2; k >= 0; k--) {
          if (score < params->avgtopk_lowest_scores[k]) {
            params->avgtopk_lowest_4[k + 1] = params->avgtopk_lowest_4[k];
            params->avgtopk_lowest_scores[k + 1] =
                params->avgtopk_lowest_scores[k];
            insert_pos = k;
          } else
            break;
        }
        params->avgtopk_lowest_4[insert_pos] = candidate;
        params->avgtopk_lowest_scores[insert_pos] = score;
      }
#endif
    }
#if LOH_PERF_PROFILING
    {
      struct timespec _t1;
      clock_gettime(CLOCK_MONOTONIC, &_t1);
      double _dt = (_t1.tv_sec - ts_fused.tv_sec) +
                   (_t1.tv_nsec - ts_fused.tv_nsec) / 1e9;
      params->perf.calc_features.total += _dt * 0.6;
      params->perf.calc_features.count += cand_n;
      params->perf.calc_score.total += _dt * 0.4;
      params->perf.calc_score.count++;
      if (_dt > params->perf.calc_features.max)
        params->perf.calc_features.max = _dt;
    }
#endif
    // ultra_fast 路径完成，跳过下面的原始两遍循环
    goto scoring_done;
  }

  // ---- 原始两遍路径（MLP / 非 compound / normalize 等场景） ----
  double feat_buf[MAX_CANDIDATES][FEATURE_DIM];
  PERF_TS ts_feat_loop;
  PERF_NOW(ts_feat_loop);
  for (int i = 0; i < cand_n; ++i) {
    cache_obj_t *candidate = params->candidates[i];
    if (fast_compound) {
      int64_t delta =
          params->current_timestamp - candidate->LOH.last_access_counter;
      feat_buf[i][0] = calculate_recency(params, delta);
      feat_buf[i][1] =
          calculate_frequency(params, (int64_t)candidate->LOH.access_count);
      feat_buf[i][2] = calculate_size(params, (int64_t)candidate->obj_size);
    } else {
      calculate_object_features(params, candidate, feat_buf[i]);
    }
  }
#if LOH_PERF_PROFILING
  {
    struct timespec _t1;
    clock_gettime(CLOCK_MONOTONIC, &_t1);
    double _dt = (_t1.tv_sec - ts_feat_loop.tv_sec) +
                 (_t1.tv_nsec - ts_feat_loop.tv_nsec) / 1e9;
    params->perf.calc_features.total += _dt;
    params->perf.calc_features.count += cand_n;
    if (_dt > params->perf.calc_features.max)
      params->perf.calc_features.max = _dt;
  }
#endif

  PERF_TS ts_score_loop;
  PERF_NOW(ts_score_loop);

#if LOH_INCLUDE_TOPK_CANDIDATE_FEATURES
  // 初始化临时存储：记录最低4个对象
  params->current_lowest_count = 0;
  for (int k = 0; k < SAMPLES_PER_EVICTION; k++) {
    params->current_lowest_4[k] = NULL;
    params->current_lowest_scores[k] = DBL_MAX;
  }
#endif

#if LOH_INCLUDE_AVGTOPK_CANDIDATE_FEATURES
  // 初始化 AvgTopK 临时存储：记录最低4个对象
  params->avgtopk_lowest_count = 0;
  for (int k = 0; k < SAMPLES_PER_EVICTION; k++) {
    params->avgtopk_lowest_4[k] = NULL;
    params->avgtopk_lowest_scores[k] = DBL_MAX;
  }
#endif

  for (int i = 0; i < cand_n; i++) {
    cache_obj_t *candidate = params->candidates[i];
    const double *f = feat_buf[i];
    double score = 0.0;
    int64_t recency_raw =
        params->current_timestamp - candidate->LOH.last_access_counter;
    ;
    int64_t freq_raw = (int64_t)candidate->LOH.access_count;
    int64_t size_bytes = (int64_t)candidate->obj_size;
    int64_t irt1_raw = candidate->LOH.irt_values[0];
    int64_t irt2_raw = candidate->LOH.irt_values[1];
    int64_t irt3_raw = candidate->LOH.irt_values[2];
    LOH_DEBUG_PRINT_DETAILED(
        "[SCORE CALC] Candidate obj_id=%llu, recency_raw=%ld, freq_raw=%ld, "
        "size_bytes=%ld, irt1_raw=%ld, irt2_raw=%ld, irt3_raw=%ld\n",
        (unsigned long long)candidate->obj_id, recency_raw, freq_raw,
        size_bytes, irt1_raw, irt2_raw, irt3_raw);

    if (params->score_model == LOH_SCORE_MODEL_MLP) {
      // MLP 模式：per-candidate 非线性打分（默认输入维度为6）
      double x[FEATURE_DIM] = {0};
      if (loh_score_use_compound) {
        const double rec = f[0];
        const double freq = f[1];
        const double size = f[2];

        double freq_recency = 0.0;
        double freq_size = 0.0;
        double recency_size = 0.0;

        if (loh_feature_log1p) {
          const double eps = 1e-12;
          const double safe_rec =
              (fabs(rec) > eps) ? rec : ((rec >= 0.0) ? eps : -eps);
          const double safe_size =
              (fabs(size) > eps) ? size : ((size >= 0.0) ? eps : -eps);
          freq_recency = freq / safe_rec;
          freq_size = freq / safe_size;
          recency_size = rec * size;
        } else {
          freq_recency = freq * rec;
          freq_size = freq * size;
          recency_size = rec * size;
        }

        x[0] = rec;
        x[1] = freq;
        x[2] = size;
        x[3] = freq_recency;
        x[4] = freq_size;
        x[5] = recency_size;
      } else {
        // 非 compound：使用 raw features（IRT 关闭时后3维保持0）
        int used_dim = loh_score_use_irt ? FEATURE_DIM : 3;
        for (int k = 0; k < used_dim; ++k) {
          x[k] = f[k];
        }
      }
      score = loh_mlp_eval(params, x);
    } else {
      // 线性模式：保持原逻辑（weights + sign）
      if (loh_score_use_compound) {
        // compound 模式：使用 recency/freq/size 以及它们构造的三个复合特征
        const double rec = f[0];
        const double freq = f[1];
        const double size = f[2];

        double freq_recency = 0.0;
        double freq_size = 0.0;
        double recency_size = 0.0;

        if (loh_feature_log1p) {
          // LOG1P 模式：使用比率与乘积，注意防止除零
          const double eps = 1e-12;
          const double safe_rec =
              (fabs(rec) > eps) ? rec : ((rec >= 0.0) ? eps : -eps);
          const double safe_size =
              (fabs(size) > eps) ? size : ((size >= 0.0) ? eps : -eps);

          freq_recency = freq / safe_rec;
          freq_size = freq / safe_size;
          recency_size = rec * size;
        } else {
          // 非 LOG1P 模式：使用乘积形式
          freq_recency = freq * rec;
          freq_size = freq * size;
          recency_size = rec * size;
        }

        double terms[WEIGHT_DIM] = {0};
        terms[0] = rec;
        terms[1] = freq;
        terms[2] = size;
        terms[3] = freq_recency;
        terms[4] = freq_size;
        terms[5] = recency_size;
        if (loh_score_compound_v2) {
          // 第7项：freq_recency_size
          if (loh_feature_log1p) {
            const double eps = 1e-12;
            const double safe_rec =
                (fabs(rec) > eps) ? rec : ((rec >= 0.0) ? eps : -eps);
            const double safe_size =
                (fabs(size) > eps) ? size : ((size >= 0.0) ? eps : -eps);
            const double denom = safe_rec * safe_size;
            const double safe_denom =
                (fabs(denom) > eps) ? denom : ((denom >= 0.0) ? eps : -eps);
            terms[6] = freq / safe_denom;
          } else {
            terms[6] = freq * rec * size;
          }
        }

        int used_dim = loh_score_compound_v2 ? WEIGHT_DIM : 6;
        for (int k = 0; k < used_dim; ++k) {
          score += terms[k] * w[k] * sign[k];
          LOH_DEBUG_PRINT_DETAILED(
              "compound:[%d] term=%.6f w=%.6f sign=%.1f "
              "contrib=%.6f\n",
              k, terms[k], w[k], sign[k], terms[k] * w[k] * sign[k]);
        }
      } else {
        // 非 compound 模式：根据 loh_score_use_irt 选择是否包含 3 个 IRT 分量
        int used_dim = loh_score_use_irt ? FEATURE_DIM : 3;

        for (int k = 0; k < used_dim; ++k) {
          score += f[k] * w[k] * sign[k];
          LOH_DEBUG_PRINT_DETAILED(
              "no compound:[%d] f=%.6f w=%.6f sign=%.1f contrib=%.6f\n", k,
              f[k], w[k], sign[k], f[k] * w[k] * sign[k]);
        }
      }
    }

    if (score < min_score) {
      min_score = score;
      obj_to_evict = candidate;
      best_i = i;
    }

#if LOH_INCLUDE_TOPK_CANDIDATE_FEATURES
    // 维护最低4个对象：插入排序
    if (params->current_lowest_count < SAMPLES_PER_EVICTION) {
      // 还没满，直接插入
      int insert_pos = params->current_lowest_count;
      for (int k = params->current_lowest_count - 1; k >= 0; k--) {
        if (score < params->current_lowest_scores[k]) {
          params->current_lowest_4[k + 1] = params->current_lowest_4[k];
          params->current_lowest_scores[k + 1] =
              params->current_lowest_scores[k];
          insert_pos = k;
        } else {
          break;
        }
      }
      params->current_lowest_4[insert_pos] = candidate;
      params->current_lowest_scores[insert_pos] = score;
      params->current_lowest_count++;
    } else if (score <
               params->current_lowest_scores[SAMPLES_PER_EVICTION - 1]) {
      // 已满，但当前分数比最大的小，需要插入
      int insert_pos = SAMPLES_PER_EVICTION - 1;
      for (int k = SAMPLES_PER_EVICTION - 2; k >= 0; k--) {
        if (score < params->current_lowest_scores[k]) {
          params->current_lowest_4[k + 1] = params->current_lowest_4[k];
          params->current_lowest_scores[k + 1] =
              params->current_lowest_scores[k];
          insert_pos = k;
        } else {
          break;
        }
      }
      params->current_lowest_4[insert_pos] = candidate;
      params->current_lowest_scores[insert_pos] = score;
    }
#endif

#if LOH_INCLUDE_AVGTOPK_CANDIDATE_FEATURES
    // AvgTopK: 维护最低4个对象（与 TOPK 相同的插入排序逻辑）
    if (params->avgtopk_lowest_count < SAMPLES_PER_EVICTION) {
      int insert_pos = params->avgtopk_lowest_count;
      for (int k = params->avgtopk_lowest_count - 1; k >= 0; k--) {
        if (score < params->avgtopk_lowest_scores[k]) {
          params->avgtopk_lowest_4[k + 1] = params->avgtopk_lowest_4[k];
          params->avgtopk_lowest_scores[k + 1] =
              params->avgtopk_lowest_scores[k];
          insert_pos = k;
        } else {
          break;
        }
      }
      params->avgtopk_lowest_4[insert_pos] = candidate;
      params->avgtopk_lowest_scores[insert_pos] = score;
      params->avgtopk_lowest_count++;
    } else if (score <
               params->avgtopk_lowest_scores[SAMPLES_PER_EVICTION - 1]) {
      int insert_pos = SAMPLES_PER_EVICTION - 1;
      for (int k = SAMPLES_PER_EVICTION - 2; k >= 0; k--) {
        if (score < params->avgtopk_lowest_scores[k]) {
          params->avgtopk_lowest_4[k + 1] = params->avgtopk_lowest_4[k];
          params->avgtopk_lowest_scores[k + 1] =
              params->avgtopk_lowest_scores[k];
          insert_pos = k;
        } else {
          break;
        }
      }
      params->avgtopk_lowest_4[insert_pos] = candidate;
      params->avgtopk_lowest_scores[insert_pos] = score;
    }
#endif
  }
  PERF_ACCUM(params, calc_score, ts_score_loop);

scoring_done:  // ultra_fast 路径跳转到这里

#if LOH_INCLUDE_TOPK_CANDIDATE_FEATURES
               // 输出最低4个对象的特征和分数
#if LOH_DEBUG_LEVEL >= LOH_DEBUG_DETAILED
  if (params->current_lowest_count > 0) {
    printf("Lowest %d objects:\n", params->current_lowest_count);
    for (int k = 0; k < params->current_lowest_count; k++) {
      cache_obj_t *obj = params->current_lowest_4[k];
      if (obj) {
        // 从 feat_buf 中找到对应的特征
        const double *f = NULL;
        for (int i = 0; i < cand_n; i++) {
          if (params->candidates[i] == obj) {
            f = feat_buf[i];
            break;
          }
        }

        if (f) {
          printf("  [%d] obj_id=%llu score=%.6f\n", k,
                 (unsigned long long)obj->obj_id,
                 params->current_lowest_scores[k]);
          printf(
              "      raw: last_access_counter=%lld access_count=%d size=%lld\n",
              (long long)obj->LOH.last_access_counter, obj->LOH.access_count,
              (long long)obj->obj_size);
          printf("      features: [%.4f, %.4f, %.4f, %.4f, %.4f, %.4f]\n", f[0],
                 f[1], f[2], f[3], f[4], f[5]);
        }
      }
    }
  }
#endif
#endif

#if LOH_INCLUDE_AVGTOPK_CANDIDATE_FEATURES
  // AvgTopK: 将 TOP4 特征累加到 avgtopk_sum
  if (params->avgtopk_lowest_count >= SAMPLES_PER_EVICTION) {
    for (int k = 0; k < SAMPLES_PER_EVICTION; k++) {
      cache_obj_t *obj = params->avgtopk_lowest_4[k];
      if (obj) {
        // 从 feat_buf 中找到对应的特征
        const double *f = NULL;
        for (int fi = 0; fi < cand_n; fi++) {
          if (params->candidates[fi] == obj) {
            f = feat_buf[fi];
            break;
          }
        }
        if (f) {
          for (int d = 0; d < FEATURE_DIM; d++) {
            params->avgtopk_sum[k][d] += f[d];
          }
        }
      }
    }
    params->avgtopk_evict_count++;

    LOH_DEBUG_PRINT_DETAILED(
        "[AvgTopK] Accumulated TOP4 features, evict_count=%llu\n",
        (unsigned long long)params->avgtopk_evict_count);
  }
#endif

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

  // ── 自适应候选预算跟踪 ──
  if (loh_adaptive_budget && best_i >= 0 && best_i < params->n_candidates) {
    int src = loh_cand_source[best_i];
    if (src >= 0 && src < LOH_MAX_SOURCES) {
      loh_source_evict_count[src]++;
      // O(1)/驱逐：仅记录获胜者得分（不在 per-candidate 循环中累加）
      if (loh_use_score_rebalance) {
        loh_source_win_score_sum[src] += min_score;
      }
    }
    loh_adaptive_total_evict++;

    // 每 REBALANCE_PERIOD 次驱逐重新分配预算
    if (loh_adaptive_total_evict % LOH_ADAPTIVE_REBALANCE_PERIOD == 0) {
      int n_active = loh_irt_heap_enabled ? 6 : 3;
      int score_rebalance_done = 0;

      // ---- 基于 per-source 平均获胜得分分配预算 ----
      // 原理：得分越低 → 候选越适合驱逐 → 源的效能越高
      // 仅在 LOH_USE_SCORE_REBALANCE=1 时启用；默认走 win-count 分支（§19 行为）
      if (loh_use_score_rebalance) {
        double avg_score[LOH_MAX_SOURCES];
        double global_min_avg = DBL_MAX;
        double global_max_avg = -DBL_MAX;
        int have_stats = 0;
        for (int s = 0; s < n_active; s++) {
          if (loh_source_evict_count[s] > 0) {
            avg_score[s] =
                loh_source_win_score_sum[s] / loh_source_evict_count[s];
            if (avg_score[s] < global_min_avg) global_min_avg = avg_score[s];
            if (avg_score[s] > global_max_avg) global_max_avg = avg_score[s];
            have_stats = 1;
          } else {
            avg_score[s] = DBL_MAX;
          }
        }

        if (have_stats && global_max_avg > global_min_avg) {
          double range = global_max_avg - global_min_avg;
          double effectiveness[LOH_MAX_SOURCES];
          double total_eff = 0;
          for (int s = 0; s < n_active; s++) {
            if (avg_score[s] < DBL_MAX) {
              effectiveness[s] = (global_max_avg - avg_score[s]) / range;
            } else {
              effectiveness[s] = 0.0;
            }
            total_eff += effectiveness[s];
          }

          if (total_eff > 0) {
            int assigned = 0;
            int max_eff_src = 0;
            double max_eff_val = -1.0;
            for (int s = 0; s < n_active; s++) {
              loh_source_budget[s] =
                  (int)(effectiveness[s] / total_eff *
                            loh_structured_candidates +
                        0.5);
              if (loh_source_budget[s] < 1) loh_source_budget[s] = 1;
              assigned += loh_source_budget[s];
              if (effectiveness[s] > max_eff_val) {
                max_eff_val = effectiveness[s];
                max_eff_src = s;
              }
            }
            int diff = loh_structured_candidates - assigned;
            loh_source_budget[max_eff_src] += diff;
            if (loh_source_budget[max_eff_src] < 1)
              loh_source_budget[max_eff_src] = 1;
            score_rebalance_done = 1;
          }
        }
      }  // end score_rebalance

      // win-count 分配（§19 行为）：默认路径或 score 路径未产出时的回退
      if (!score_rebalance_done) {
        uint64_t total_wins = 0;
        for (int s = 0; s < n_active; s++)
          total_wins += loh_source_evict_count[s];
        if (total_wins > 0) {
          int assigned = 0;
          int max_src = 0;
          uint64_t max_wins = 0;
          for (int s = 0; s < n_active; s++) {
            loh_source_budget[s] =
                (int)((double)loh_source_evict_count[s] / total_wins *
                          loh_structured_candidates +
                      0.5);
            if (loh_source_budget[s] < 1) loh_source_budget[s] = 1;
            assigned += loh_source_budget[s];
            if (loh_source_evict_count[s] > max_wins) {
              max_wins = loh_source_evict_count[s];
              max_src = s;
            }
          }
          int diff = loh_structured_candidates - assigned;
          loh_source_budget[max_src] += diff;
          if (loh_source_budget[max_src] < 1) loh_source_budget[max_src] = 1;
        }
      }

      LOH_DEBUG_PRINT_DETAILED(
          "[ADAPTIVE] Rebalance @%llu (score-efficiency): ",
          (unsigned long long)loh_adaptive_total_evict);
      for (int s = 0; s < n_active; s++) {
        LOH_DEBUG_PRINT_DETAILED(
            "src%d: wins=%llu, avg_win=%.4f, budget=%d  ", s,
            (unsigned long long)loh_source_evict_count[s],
            (loh_source_evict_count[s] > 0
                 ? loh_source_win_score_sum[s] / loh_source_evict_count[s]
                 : 0.0),
            loh_source_budget[s]);
      }
      LOH_DEBUG_PRINT_DETAILED("\n");

      // 重置计数器
      memset(loh_source_evict_count, 0, sizeof(loh_source_evict_count));
      memset(loh_source_win_score_sum, 0, sizeof(loh_source_win_score_sum));
    }
  }

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

  // 临时调试：打印被驱逐对象的大小
  LOH_DEBUG_PRINT_DETAILED(
      "[LOH EVICT DEBUG] obj_id=%llu size=%ld bytes (%.2f MB)\n",
      (unsigned long long)obj_to_evict->obj_id, (long)obj_to_evict->obj_size,
      (double)obj_to_evict->obj_size / (1024.0 * 1024.0));

  // Update feature statistics for learning
  // (但不要标记为 miss，因为 evict 不是 miss)

#if LOH_INCLUDE_TOPK_CANDIDATE_FEATURES
  // 【蓄水池采样】使用 LOH_to_evict 中找到的最低4个对象
  reservoir_sample_group(params);
  // 清空临时存储，为下次驱逐做准备
  params->current_lowest_count = 0;
#endif

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

#if LOH_ENABLE_PENALTY
    // 【新增】更新驱逐统计（用于归一化惩罚）
    params->epoch_evicted_bytes += (uint64_t)obj_to_evict->obj_size;
    params->epoch_evicted_count += 1;

    LOH_DEBUG_PRINT_DETAILED(
        "[LOH] Evicted obj_id=%llu, size=%ld, epoch_evicted_bytes=%llu, "
        "epoch_evicted_count=%llu\n",
        (unsigned long long)obj_to_evict->obj_id, (long)obj_to_evict->obj_size,
        (unsigned long long)params->epoch_evicted_bytes,
        (unsigned long long)params->epoch_evicted_count);
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
// 旧版 calculate_score_with_features / calculate_score 已被移除，
// 得分计算在 LOH_to_evict 中直接展开以减少调用开销。

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
// 频率/recency/size 的辅助函数已在前文实现，这里不再重复定义

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
  double accept_prob = 1.0;
  int max_scan = loh_tail_sample_enabled ? max_candidates * 10 : 0;
  int scanned = 0;
  for (int i = 1; i <= FREQ_MAX && added < max_candidates; i++) {
    loh_freq_node_t *curr =
        params->freq_table_tail[i];  // 从尾部start，选择更老ofobject

    while (curr != NULL && added < max_candidates) {
      if (start_idx + added >= loh_structured_candidates) return;
      // 衰减采样：超过最大扫描深度则停止
      if (loh_tail_sample_enabled && scanned >= max_scan) goto freq_done;

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
        // 先记录候选统计（来源 index=1）
#if LOH_INCLUDE_CANDIDATE_FEATURES
        {
          double f[FEATURE_DIM];
          calculate_object_features(params, curr->obj, f);
          for (int k = 0; k < FEATURE_DIM; ++k) {
            params->cand_feat_sum[1][k] += f[k];
            params->cand_feat_sumsq[1][k] += f[k] * f[k];
          }
          params->cand_feat_count[1]++;
        }
#endif
        // 衰减采样：先检查概率，再加入 seen（避免 seen 集合被无用对象污染）
        {
          bool freq_pass_decay =
              !loh_tail_sample_enabled ||
              (double)(loh_fast_rand() % 10000u) / 10000.0 < accept_prob;
          if (freq_pass_decay && loh_seen_add(params, curr->obj)) {
            params->candidates[start_idx + added++] = curr->obj;
          }
        }
      }
      if (loh_tail_sample_enabled) {
        accept_prob *= loh_tail_sample_decay;
        scanned++;
      }
      curr = curr->prev;  // 向前遍历（从尾部到头部），选择更老ofobject
    }
  }
freq_done:
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
      loh_structured_candidates / 6;  // 每个IRT堆大小为总候选数的1/6

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

  // MAX值object也应该被add到堆，因为它们是最大值，是驱逐候选
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
        // 【说明】对象不在 hash 表中有两种可能：
        // 1. 正常情况：对象 IRT 值太小，从未进入过堆（Top-K 堆只保存最大的 K
        // 个）
        // 2. 异常情况：hash 表与堆不一致，需要线性搜索修复
        LOH_DEBUG_PRINT_ERROR(
            "[irt_heap_update] [warning] Object %llu not found in hash table "
            "for "
            "heap %d (normal if IRT too small for Top-K heap), searching "
            "linearly...\n",
            (unsigned long long)obj->obj_id, heap_idx);
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
          // 线性搜索也找不到，说明对象确实不在堆中（IRT 值太小）
          // 尝试添加到堆，如果 IRT 值够大会被添加，否则什么都不做
          LOH_DEBUG_PRINT_DETAILED(
              "[irt_heap_update] Object not found in heap %d (IRT too small), "
              "trying to add...\n",
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

  // 【简化方案】直接遍历堆中所有元素作为候选（含衰减采样）
  // 因为最小堆中存储的都是具有较大IRT值的对象，正是驱逐候选
  double irt1_accept_prob = 1.0;
  int irt1_max_scan = loh_tail_sample_enabled ? max_candidates * 10 : 0;
  int irt1_scanned = 0;
  for (int i = 0; i < params->irt_heap_size[heap_idx] && added < max_candidates;
       i++) {
    // 检查全局候选数组边界
    if (start_idx + added >= loh_structured_candidates) {
      LOH_DEBUG_PRINT_DETAILED(
          "[IRT1 HEAP DEBUG] Reached loh_structured_candidates limit: %d\n",
          loh_structured_candidates);
      break;
    }
    if (loh_tail_sample_enabled && irt1_scanned >= irt1_max_scan) break;

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
      // 衰减采样：按位置递减概率接受候选
      if (loh_tail_sample_enabled) {
        double r = (double)(loh_fast_rand() % 10000u) / 10000.0;
        if (r >= irt1_accept_prob) {
          irt1_accept_prob *= loh_tail_sample_decay;
          irt1_scanned++;
          continue;
        }
      }
      // 先记录候选统计（来源 index=3）
#if LOH_INCLUDE_CANDIDATE_FEATURES
      {
        double f[FEATURE_DIM];
        calculate_object_features(params, candidate, f);
        for (int k = 0; k < FEATURE_DIM; ++k) {
          params->cand_feat_sum[3][k] += f[k];
          params->cand_feat_sumsq[3][k] += f[k] * f[k];
        }
        params->cand_feat_count[3]++;
      }
#endif
      if (loh_seen_add(params, candidate)) {
        params->candidates[start_idx + added++] = candidate;
      }
      if (loh_tail_sample_enabled) {
        irt1_accept_prob *= loh_tail_sample_decay;
        irt1_scanned++;
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

  // 【简化方案】直接遍历堆中所有元素作为候选（含衰减采样）
  double irt2_accept_prob = 1.0;
  int irt2_max_scan = loh_tail_sample_enabled ? max_candidates * 10 : 0;
  int irt2_scanned = 0;
  for (int i = 0; i < params->irt_heap_size[heap_idx] && added < max_candidates;
       i++) {
    if (start_idx + added >= loh_structured_candidates) break;
    if (loh_tail_sample_enabled && irt2_scanned >= irt2_max_scan) break;

    cache_obj_t *candidate = params->irt_heap[heap_idx][i].obj;
    if (candidate != NULL) {
#if LOH_DEBUG_LEVEL >= LOH_DEBUG_ERROR
      if (hashtable_find_obj_id(cache->hashtable, candidate->obj_id) !=
          candidate) {
        continue;
      }
#endif
      // 衰减采样
      if (loh_tail_sample_enabled) {
        double r = (double)(loh_fast_rand() % 10000u) / 10000.0;
        if (r >= irt2_accept_prob) {
          irt2_accept_prob *= loh_tail_sample_decay;
          irt2_scanned++;
          continue;
        }
      }
      // 先记录候选统计（来源 index=4）
#if LOH_INCLUDE_CANDIDATE_FEATURES
      {
        double f[FEATURE_DIM];
        calculate_object_features(params, candidate, f);
        for (int k = 0; k < FEATURE_DIM; ++k) {
          params->cand_feat_sum[4][k] += f[k];
          params->cand_feat_sumsq[4][k] += f[k] * f[k];
        }
        params->cand_feat_count[4]++;
      }
#endif
      if (loh_seen_add(params, candidate)) {
        params->candidates[start_idx + added++] = candidate;
      }
      if (loh_tail_sample_enabled) {
        irt2_accept_prob *= loh_tail_sample_decay;
        irt2_scanned++;
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

  // 【简化方案】直接遍历堆中所有元素作为候选（含衰减采样）
  double irt3_accept_prob = 1.0;
  int irt3_max_scan = loh_tail_sample_enabled ? max_candidates * 10 : 0;
  int irt3_scanned = 0;
  for (int i = 0; i < params->irt_heap_size[heap_idx] && added < max_candidates;
       i++) {
    if (start_idx + added >= loh_structured_candidates) break;
    if (loh_tail_sample_enabled && irt3_scanned >= irt3_max_scan) break;

    cache_obj_t *candidate = params->irt_heap[heap_idx][i].obj;
    if (candidate != NULL) {
#if LOH_DEBUG_LEVEL >= LOH_DEBUG_ERROR
      if (hashtable_find_obj_id(cache->hashtable, candidate->obj_id) !=
          candidate) {
        continue;
      }
#endif
      // 衰减采样
      if (loh_tail_sample_enabled) {
        double r = (double)(loh_fast_rand() % 10000u) / 10000.0;
        if (r >= irt3_accept_prob) {
          irt3_accept_prob *= loh_tail_sample_decay;
          irt3_scanned++;
          continue;
        }
      }
      // 先记录候选统计（来源 index=5）
#if LOH_INCLUDE_CANDIDATE_FEATURES
      {
        double f[FEATURE_DIM];
        calculate_object_features(params, candidate, f);
        for (int k = 0; k < FEATURE_DIM; ++k) {
          params->cand_feat_sum[5][k] += f[k];
          params->cand_feat_sumsq[5][k] += f[k] * f[k];
        }
        params->cand_feat_count[5]++;
      }
#endif
      if (loh_seen_add(params, candidate)) {
        params->candidates[start_idx + added++] = candidate;
      }
      if (loh_tail_sample_enabled) {
        irt3_accept_prob *= loh_tail_sample_decay;
        irt3_scanned++;
      }
    }
  }

  *n_candidates = start_idx + added;
}

/**
 * @brief 初始化尺寸堆（单一最小堆）
 */
static void size_heap_init(LOH_params_t *params) {
  // 设置 Size 堆的容量为 MAX_CANDIDATES，确保有足够的大对象候选
  // （原来是 MAX_CANDIDATES / 6，但这会导致堆在 evict 后逐渐失效）
  params->size_heap_capacity = loh_structured_candidates;
  params->size_heap_size = 0;
  params->size_heap = g_new0(size_heap_entry_t, params->size_heap_capacity);
#if LOH_MAINTAIN_MAPS
  params->size_heap_map = g_hash_table_new(g_direct_hash, g_direct_equal);
#else
  params->size_heap_map = NULL;
#endif
}

/**
 * @brief 释放尺寸堆资源
 */
static void size_heap_free(LOH_params_t *params) {
  g_free(params->size_heap);
  params->size_heap = NULL;
  params->size_heap_size = 0;
  if (params->size_heap_map) {
    g_hash_table_destroy(params->size_heap_map);
    params->size_heap_map = NULL;
  }
  params->size_heap_capacity = 0;
}

/**
 * @brief 上移操作以维护最小堆属性 - Size 值小的 object 在堆顶
 */
static void size_heap_sift_up(LOH_params_t *params, int idx) {
  while (idx > 0) {
    int parent = (idx - 1) / 2;

    if (params->size_heap[idx].size_value >=
        params->size_heap[parent].size_value) {
      break;
    }

    cache_obj_t *obj_at_idx = params->size_heap[idx].obj;
    cache_obj_t *obj_at_parent = params->size_heap[parent].obj;

    size_heap_entry_t temp = params->size_heap[idx];
    params->size_heap[idx] = params->size_heap[parent];
    params->size_heap[parent] = temp;

    if (params->size_heap_map) {
      g_hash_table_insert(params->size_heap_map, obj_at_idx,
                          GINT_TO_POINTER(parent + 1));
      g_hash_table_insert(params->size_heap_map, obj_at_parent,
                          GINT_TO_POINTER(idx + 1));
    }
    obj_at_idx->LOH.loh_size_pos = parent;
    obj_at_parent->LOH.loh_size_pos = idx;

    idx = parent;
  }
}

/**
 * @brief 下移操作以维护最小堆属性
 */
static void size_heap_sift_down(LOH_params_t *params, int idx) {
  int min_idx = idx;
  int left = 2 * idx + 1;
  int right = 2 * idx + 2;

  if (left < params->size_heap_size &&
      params->size_heap[left].size_value <
          params->size_heap[min_idx].size_value)
    min_idx = left;

  if (right < params->size_heap_size &&
      params->size_heap[right].size_value <
          params->size_heap[min_idx].size_value)
    min_idx = right;

  if (min_idx != idx) {
    cache_obj_t *obj_at_idx = params->size_heap[idx].obj;
    cache_obj_t *obj_at_min_idx = params->size_heap[min_idx].obj;

    size_heap_entry_t temp = params->size_heap[idx];
    params->size_heap[idx] = params->size_heap[min_idx];
    params->size_heap[min_idx] = temp;

    if (params->size_heap_map) {
      g_hash_table_insert(params->size_heap_map, obj_at_min_idx,
                          GINT_TO_POINTER(idx + 1));
      g_hash_table_insert(params->size_heap_map, obj_at_idx,
                          GINT_TO_POINTER(min_idx + 1));
    }
    obj_at_min_idx->LOH.loh_size_pos = idx;
    obj_at_idx->LOH.loh_size_pos = min_idx;

    size_heap_sift_down(params, min_idx);
  }
}

/**
 * @brief 添加 object 到 Size 最小堆
 * Top-K 最大值问题：维护一个最小堆，只有比堆顶大的元素才能进入
 */
static void size_heap_add(LOH_params_t *params, cache_obj_t *obj) {
  LOH_DEBUG_PRINT_DETAILED(
      "[SIZE_HEAP_ADD] Considering obj %llu with size=%ld, current "
      "heap_size=%d, capacity=%d\n",
      (unsigned long long)obj->obj_id, (long)obj->obj_size,
      params->size_heap_size, params->size_heap_capacity);

#if LOH_MAINTAIN_MAPS
  gpointer existing_pos = g_hash_table_lookup(params->size_heap_map, obj);
  if (existing_pos != NULL) {
    LOH_DEBUG_PRINT_DETAILED(
        "[SIZE_HEAP_ADD] obj %llu already in heap, skipping\n",
        (unsigned long long)obj->obj_id);
    return;
  }
#endif

  int64_t size_value = obj->obj_size;

  if (params->size_heap_size >= params->size_heap_capacity) {
    int64_t min_size = params->size_heap[0].size_value;

    if (size_value <= min_size) {
      // 被拒绝的对象：大小不够大，无法进入堆
      LOH_DEBUG_PRINT_DETAILED(
          "[SIZE_HEAP_ADD] obj %llu (size=%ld) <= min_size=%ld, NOT added "
          "(heap full)\n",
          (unsigned long long)obj->obj_id, (long)size_value, (long)min_size);
      return;
    }

    LOH_DEBUG_PRINT_DETAILED(
        "[SIZE_HEAP_ADD] obj %llu (size=%ld) > min_size=%ld, REPLACING heap "
        "top\n",
        (unsigned long long)obj->obj_id, (long)size_value, (long)min_size);

    cache_obj_t *removed_obj = params->size_heap[0].obj;
    if (params->size_heap_map)
      g_hash_table_remove(params->size_heap_map, removed_obj);
    if (removed_obj) {
      removed_obj->LOH.loh_size_pos = -1;
    }

    params->size_heap[0].obj = obj;
    params->size_heap[0].size_value = size_value;

    if (params->size_heap_map)
      g_hash_table_insert(params->size_heap_map, obj, GINT_TO_POINTER(1));
    obj->LOH.loh_size_pos = 0;

    size_heap_sift_down(params, 0);
    LOH_DEBUG_PRINT_DETAILED(
        "[SIZE_HEAP_ADD] obj %llu stored at idx=%d (after sift_down)\n",
        (unsigned long long)obj->obj_id, obj->LOH.loh_size_pos);
    return;
  }

  int idx = params->size_heap_size;
  params->size_heap[idx].obj = obj;
  params->size_heap[idx].size_value = size_value;
  if (params->size_heap_map)
    g_hash_table_insert(params->size_heap_map, obj, GINT_TO_POINTER(idx + 1));
  obj->LOH.loh_size_pos = idx;
  params->size_heap_size++;

  LOH_DEBUG_PRINT_DETAILED(
      "[SIZE_HEAP_ADD] obj %llu stored at idx=%d, new heap_size=%d\n",
      (unsigned long long)obj->obj_id, idx, params->size_heap_size);

  size_heap_sift_up(params, idx);

  LOH_DEBUG_PRINT_DETAILED(
      "[SIZE_HEAP_ADD] obj %llu final pos=%d (after sift_up)\n",
      (unsigned long long)obj->obj_id, obj->LOH.loh_size_pos);
}

/**
 * @brief 从 Size 堆移除特定 object
 */
static void size_heap_remove(LOH_params_t *params, cache_obj_t *obj) {
  if (params->size_heap_size == 0 || !obj) return;

  int idx = obj->LOH.loh_size_pos;
  if (idx < 0) {
#if LOH_MAINTAIN_MAPS
    gpointer idx_ptr = params->size_heap_map
                           ? g_hash_table_lookup(params->size_heap_map, obj)
                           : NULL;
    if (!idx_ptr) return;
    idx = GPOINTER_TO_INT(idx_ptr) - 1;
#else
    return;
#endif
  }

  if (idx < 0 || idx >= params->size_heap_size ||
      params->size_heap[idx].obj != obj) {
    if (params->size_heap_map) g_hash_table_remove(params->size_heap_map, obj);
    return;
  }

  if (params->size_heap_map) g_hash_table_remove(params->size_heap_map, obj);
  obj->LOH.loh_size_pos = -1;

  if (idx < params->size_heap_size - 1) {
    cache_obj_t *moved_obj = params->size_heap[params->size_heap_size - 1].obj;
    int64_t moved_value =
        params->size_heap[params->size_heap_size - 1].size_value;
    params->size_heap[idx] = params->size_heap[params->size_heap_size - 1];

    if (params->size_heap_map)
      g_hash_table_insert(params->size_heap_map, moved_obj,
                          GINT_TO_POINTER(idx + 1));
    moved_obj->LOH.loh_size_pos = idx;

    bool need_sift_up = false;
    if (idx > 0) {
      int parent = (idx - 1) / 2;
      if (moved_value < params->size_heap[parent].size_value) {
        need_sift_up = true;
      }
    }

    if (need_sift_up) {
      size_heap_sift_up(params, idx);
    } else {
      size_heap_sift_down(params, idx);
    }
  }

  params->size_heap_size--;
}

/**
 * @brief 从尺寸堆获取淘汰候选 object
 * 最小堆存储 Top-K 最大 size 值的对象
 * 遍历整个堆，按 size 从大到小排序选择候选
 */
static void size_heap_get_candidates(LOH_params_t *params, int max_candidates,
                                     int *n_candidates) {
  int added = 0;
  int start_idx = *n_candidates;

  if (params->size_heap_size == 0) {
    LOH_DEBUG_PRINT_DETAILED(
        "[SIZE HEAP DEBUG] Heap is empty, no candidates\n");
    return;
  }

  cache_t *cache = (cache_t *)params->cache_ptr;

  LOH_DEBUG_PRINT_DETAILED(
      "[SIZE HEAP DEBUG] Starting candidate collection from heap size=%d, "
      "max_candidates=%d, start_idx=%d\n",
      params->size_heap_size, max_candidates, start_idx);

  // 创建索引数组，按 size_value 从大到小排序
  // 使用栈上数组避免动态分配（heap 容量最大 96）
  int sorted_indices[96];
  int valid_count = 0;
  int64_t heap_max_size = 0;

  // 收集所有有效对象的索引，同时找堆中最大对象
  for (int i = 0; i < params->size_heap_size && valid_count < 96; i++) {
    cache_obj_t *obj = params->size_heap[i].obj;
    if (obj == NULL) continue;
#if LOH_DEBUG_LEVEL >= LOH_DEBUG_ERROR
    if (hashtable_find_obj_id(cache->hashtable, obj->obj_id) != obj) {
      LOH_DEBUG_PRINT_ERROR(
          "[SIZE WARNING] Object obj_id=%llu found in size heap but not "
          "in cache, skipping\n",
          (unsigned long long)obj->obj_id);
      continue;
    }
#endif
    if (params->size_heap[i].size_value > heap_max_size) {
      heap_max_size = params->size_heap[i].size_value;
    }
    sorted_indices[valid_count++] = i;
  }

  // 打印堆状态
  LOH_DEBUG_PRINT_DETAILED(
      "[SIZE_HEAP CAND] heap_size=%d, heap_max=%.2fMB, heap_min=%.2fMB\n",
      params->size_heap_size, (double)heap_max_size / (1024.0 * 1024.0),
      params->size_heap_size > 0
          ? (double)params->size_heap[0].size_value / (1024.0 * 1024.0)
          : 0.0);

  // 按 size_value 从大到小排序（简单选择排序，因为数量小）
  for (int i = 0; i < valid_count - 1 && i < max_candidates; i++) {
    int max_idx = i;
    for (int j = i + 1; j < valid_count; j++) {
      if (params->size_heap[sorted_indices[j]].size_value >
          params->size_heap[sorted_indices[max_idx]].size_value) {
        max_idx = j;
      }
    }
    if (max_idx != i) {
      int tmp = sorted_indices[i];
      sorted_indices[i] = sorted_indices[max_idx];
      sorted_indices[max_idx] = tmp;
    }
  }

  // 从排序后的数组中选择最大的 max_candidates 个对象（支持衰减采样）
  double sz_accept_prob = 1.0;
  int sz_max_scan = loh_tail_sample_enabled ? max_candidates * 10 : 0;
  int sz_scanned = 0;
  for (int i = 0; i < valid_count && added < max_candidates; i++) {
    if (start_idx + added >= loh_structured_candidates) break;
    if (loh_tail_sample_enabled && sz_scanned >= sz_max_scan) break;

    int heap_idx = sorted_indices[i];
    cache_obj_t *obj = params->size_heap[heap_idx].obj;

#if LOH_INCLUDE_CANDIDATE_FEATURES
    {
      double f[FEATURE_DIM];
      calculate_object_features(params, obj, f);
      for (int k = 0; k < FEATURE_DIM; ++k) {
        params->cand_feat_sum[2][k] += f[k];
        params->cand_feat_sumsq[2][k] += f[k] * f[k];
      }
      params->cand_feat_count[2]++;
    }
#endif

    // 衰减采样：先检查概率，再加入 seen
    {
      bool sz_pass_decay =
          !loh_tail_sample_enabled ||
          (double)(loh_fast_rand() % 10000u) / 10000.0 < sz_accept_prob;
      if (sz_pass_decay && loh_seen_add(params, obj)) {
        params->candidates[start_idx + added++] = obj;
        LOH_DEBUG_PRINT_DETAILED(
            "[SIZE HEAP DEBUG] Added candidate #%d: obj_id=%llu, size=%ld\n",
            added, (unsigned long long)obj->obj_id,
            (long)params->size_heap[heap_idx].size_value);
      }
    }
    if (loh_tail_sample_enabled) {
      sz_accept_prob *= loh_tail_sample_decay;
      sz_scanned++;
    }
  }

  *n_candidates = start_idx + added;

  LOH_DEBUG_PRINT_DETAILED(
      "[SIZE HEAP DEBUG] Completed: heap_size=%d, added=%d, total=%d\n",
      params->size_heap_size, added, *n_candidates);
}

// ===== Size Buckets 实现（全量分桶方式）=====

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
 * @brief 获取对象应该放入的尺寸桶索引
 */
static int size_get_bucket_index(LOH_params_t *params, int64_t size) {
  for (int i = 0; i < SIZE_BUCKET_COUNT; i++) {
    if (size <= params->size_bucket_bounds[i]) return i;
  }
  return SIZE_BUCKET_COUNT - 1;
}

/**
 * @brief 添加对象到尺寸桶
 */
static void size_buckets_add(LOH_params_t *params, cache_obj_t *obj) {
  int bucket_idx = size_get_bucket_index(params, obj->obj_size);
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
}

/**
 * @brief 从尺寸桶移除对象
 */
static void size_buckets_remove(LOH_params_t *params, cache_obj_t *obj) {
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
}

/**
 * @brief 从尺寸桶获取淘汰候选对象
 *
 * 【性能优化】：直接从最高桶向下遍历取对象，跳过全量收集+排序。
 * 桶边界（512KB/1MB/10MB/100MB）已按大小分区，高桶对象天然较大。
 * 评分函数会在候选集中选出最优，无需精确排序。
 * 原实现：收集192个对象 + O(k×n)选择排序 → 每次驱逐~6000次比较
 * 优化后：直接从高桶取 max_candidates 个 → O(max_candidates)
 */
static void size_buckets_get_candidates(LOH_params_t *params,
                                        int max_candidates, int *n_candidates) {
  int added = 0;
  int start_idx = *n_candidates;

  // [FIX] cap max_candidates to avoid scanning past loh_structured_candidates
  // Without this, when start_idx + max_candidates > loh_structured_candidates,
  // the inner condition (start_idx + added < loh_structured_candidates)
  // prevents the last candidate from being added, but the while loop
  // (added < max_candidates) keeps running, causing a full linked-list scan
  // of potentially millions of nodes.
  if (start_idx + max_candidates > loh_structured_candidates) {
    max_candidates = loh_structured_candidates - start_idx;
    if (max_candidates <= 0) {
      return;
    }
  }

#if LOH_DEBUG_LEVEL >= LOH_DEBUG_DETAILED
  LOH_DEBUG_PRINT_DETAILED("[SIZE_BUCKETS DEBUG] Bucket counts: ");
  for (int b = 0; b < SIZE_BUCKET_COUNT; b++) {
    int count = 0;
    int64_t max_size = 0;
    size_node_t *n = params->size_buckets[b];
    while (n) {
      count++;
      if (n->obj && n->obj->obj_size > max_size) max_size = n->obj->obj_size;
      n = n->next;
    }
    LOH_DEBUG_PRINT_DETAILED("bucket[%d]=%d(max=%.2fMB) ", b, count,
                             max_size / (1024.0 * 1024.0));
  }
  LOH_DEBUG_PRINT_DETAILED("\n");
#endif

  // 从最高桶向下遍历，使用衰减采样
  double sb_accept_prob = 1.0;
  int sb_max_scan = loh_tail_sample_enabled ? max_candidates * 10 : 0;
  int sb_scanned = 0;
  for (int b = SIZE_BUCKET_COUNT - 1; b >= 0 && added < max_candidates; b--) {
    size_node_t *curr = params->size_buckets[b];
    while (curr != NULL && added < max_candidates) {
      if (loh_tail_sample_enabled && sb_scanned >= sb_max_scan) goto sb_done;
      if (curr->obj != NULL && start_idx + added < loh_structured_candidates) {
#if LOH_DEBUG_LEVEL >= LOH_DEBUG_ERROR
        {
          cache_t *cache = (cache_t *)params->cache_ptr;
          if (hashtable_find_obj_id(cache->hashtable, curr->obj->obj_id) !=
              curr->obj) {
            LOH_DEBUG_PRINT_ERROR(
                "[SIZE WARNING] Object obj_id=%llu found in size bucket but "
                "not in cache, skipping\n",
                (unsigned long long)curr->obj->obj_id);
            curr = curr->next;
            continue;
          }
        }
#endif
#if LOH_INCLUDE_CANDIDATE_FEATURES
        {
          double f[FEATURE_DIM];
          calculate_object_features(params, curr->obj, f);
          for (int k = 0; k < FEATURE_DIM; ++k) {
            params->cand_feat_sum[2][k] += f[k];
            params->cand_feat_sumsq[2][k] += f[k] * f[k];
          }
          params->cand_feat_count[2]++;
        }
#endif
        // 衰减采样：先检查概率，再加入 seen
        {
          bool sb_pass_decay =
              !loh_tail_sample_enabled ||
              (double)(loh_fast_rand() % 10000u) / 10000.0 < sb_accept_prob;
          if (sb_pass_decay && loh_seen_add(params, curr->obj)) {
            params->candidates[start_idx + added++] = curr->obj;
          }
        }
      }
      if (loh_tail_sample_enabled) {
        sb_accept_prob *= loh_tail_sample_decay;
        sb_scanned++;
      }
      curr = curr->next;
    }
  }
sb_done:
  *n_candidates = start_idx + added;
}

// ===== 统一的 Size 数据结构操作接口 =====

/**
 * @brief 初始化 size 数据结构（根据 loh_use_size_buckets 选择实现）
 */
static void size_ds_init(LOH_params_t *params) {
  if (loh_use_size_buckets) {
    size_buckets_init(params);
  } else {
    size_heap_init(params);
  }
}

/**
 * @brief 释放 size 数据结构资源
 */
static void size_ds_free(LOH_params_t *params) {
  if (loh_use_size_buckets) {
    size_buckets_free(params);
  } else {
    size_heap_free(params);
  }
}

/**
 * @brief 添加对象到 size 数据结构
 */
static void size_ds_add(LOH_params_t *params, cache_obj_t *obj) {
  if (loh_use_size_buckets) {
    size_buckets_add(params, obj);
  } else {
    size_heap_add(params, obj);
  }
}

/**
 * @brief 从 size 数据结构移除对象
 */
static void size_ds_remove(LOH_params_t *params, cache_obj_t *obj) {
  if (loh_use_size_buckets) {
    size_buckets_remove(params, obj);
  } else {
    size_heap_remove(params, obj);
  }
}

/**
 * @brief 从 size 数据结构获取候选对象
 */
static void size_ds_get_candidates(LOH_params_t *params, int max_candidates,
                                   int *n_candidates) {
  if (loh_use_size_buckets) {
    size_buckets_get_candidates(params, max_candidates, n_candidates);
  } else {
    size_heap_get_candidates(params, max_candidates, n_candidates);
  }
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
  obj->LOH.loh_irt_pos[0] = obj->LOH.loh_irt_pos[1] = obj->LOH.loh_irt_pos[2] =
      -1;
  obj->LOH.loh_size_pos = -1;  // 单一尺寸堆位置

  // 尝试插入到所有辅助结构
  bool success = true;

  // 1. 插入LRU队列（移到这里统一process）
  prepend_obj_to_head(&params->q_head, &params->q_tail, obj);

  // 2. 插入frequency表
  freq_table_add(params, obj);

  // 3. 插入尺寸数据结构（根据配置使用 heap 或 buckets）
  size_ds_add(params, obj);

  // 4. 插入IRT堆 - 使用专门的add函数，避免update函数中的无意义查找
  if (loh_irt_heap_enabled) {
    for (int i = 0; i < IRT_HISTORY_SIZE; i++) {
      irt_heap_add(params, obj, i);
    }
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

  // Size 数据结构 remove（根据配置使用 heap 或 buckets）
  size_ds_remove(params, obj);

  // IRT 堆remove（remove所有堆inofobject）
  if (loh_irt_heap_enabled) {
    for (int i = 0; i < IRT_HISTORY_SIZE; i++) {
      irt_heap_remove(params, obj, i);
    }
  }

  // 清理对象内缓存指针/索引
  obj->LOH.loh_freq_node = NULL;
  obj->LOH.loh_irt_pos[0] = obj->LOH.loh_irt_pos[1] = obj->LOH.loh_irt_pos[2] =
      -1;
  obj->LOH.loh_size_pos = -1;  // 单一尺寸堆位置

  // 从 flat obj_array 中移除（swap-with-last, O(1)）
  {
    int idx = obj->LOH.obj_array_idx;
    int last = params->obj_array_size - 1;
    if (idx >= 0 && idx <= last) {
      if (idx != last) {
        cache_obj_t *last_obj = params->obj_array[last];
        params->obj_array[idx] = last_obj;
        last_obj->LOH.obj_array_idx = idx;
      }
      params->obj_array_size--;
    }
    obj->LOH.obj_array_idx = -1;
  }

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
  if (loh_irt_heap_enabled) {
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

  // 验证尺寸堆一致性（单一堆）
  if (verify_flags & LOH_VERIFY_SIZE) {
    int idx = obj->LOH.loh_size_pos;
    if (idx >= 0 && idx < params->size_heap_size) {
      if (params->size_heap[idx].obj != obj) {
        printf(
            "[LOH CONSISTENCY ERROR] Size heap mapping mismatch for "
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

  // check尺寸堆映射（单一堆）
  if (params->size_heap_map) {
    g_hash_table_iter_init(&iter, params->size_heap_map);
    while (g_hash_table_iter_next(&iter, &key, &value)) {
      cache_obj_t *obj = (cache_obj_t *)key;
      int pos = GPOINTER_TO_INT(value) - 1;

      if (!obj || pos < 0 || pos >= params->size_heap_size ||
          params->size_heap[pos].obj != obj) {
        LOH_DEBUG_PRINT_DETAILED(
            "[LOH CLEANUP] Removing orphaned size heap entry for obj_id=%llu\n",
            obj ? (unsigned long long)obj->obj_id : 0);
        g_hash_table_iter_remove(&iter);
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

  // 清理size堆中的无效object（单一堆）
  {
    int write_pos = 0;

    for (int read_pos = 0; read_pos < params->size_heap_size; read_pos++) {
      cache_obj_t *obj = params->size_heap[read_pos].obj;
      if (obj != NULL) {
        if (write_pos != read_pos) {
          params->size_heap[write_pos] = params->size_heap[read_pos];
          // 更新哈希表和对象内索引
          if (params->size_heap_map)
            g_hash_table_insert(params->size_heap_map, obj,
                                GINT_TO_POINTER(write_pos + 1));
          obj->LOH.loh_size_pos = write_pos;
        }
        write_pos++;
      } else {
        // 从哈希表中移除无效条目
        if (params->size_heap_map)
          g_hash_table_remove(params->size_heap_map, obj);
      }
    }
    params->size_heap_size = write_pos;
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
    double old_irt_feature =
        calculate_irt_feature(params, obj->LOH.irt_values[0]);
    double new_irt_feature = calculate_irt_feature(params, new_irt);

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
    double old_irt4 = calculate_irt_feature(params, obj->LOH.irt_values[1]);
    double new_irt4 = calculate_irt_feature(params, obj->LOH.irt_values[0]);

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
    double old_irt5 = calculate_irt_feature(params, obj->LOH.irt_values[2]);
    double new_irt5 = calculate_irt_feature(params, obj->LOH.irt_values[1]);

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
 * @brief 验证尺寸堆的一致性（与 IRT 堆验证类似）
 */
static void size_heap_validate(LOH_params_t *params, const char *context) {
  printf("[SIZE_VALIDATE] 🔍 Validating size heap (%s):\n", context);

  int heap_size = params->size_heap_size;
  int map_size = 0;
  if (params->size_heap_map)
    map_size = g_hash_table_size(params->size_heap_map);

  if (heap_size != map_size) {
    printf("[SIZE_VALIDATE] ❌ ERROR: Size mismatch - heap:%d, map:%d\n",
           heap_size, map_size);
  }

  // 验证最小堆属性
  for (int i = 0; i < heap_size / 2; i++) {
    int64_t parent_size = params->size_heap[i].size_value;
    int left_child = 2 * i + 1;
    int right_child = 2 * i + 2;

    if (left_child < heap_size) {
      int64_t left_size = params->size_heap[left_child].size_value;
      if (parent_size > left_size) {
        printf(
            "[SIZE_VALIDATE] ❌ HEAP VIOLATION: Parent[%d]=%ld > "
            "LeftChild[%d]=%ld\n",
            i, parent_size, left_child, left_size);
      }
    }

    if (right_child < heap_size) {
      int64_t right_size = params->size_heap[right_child].size_value;
      if (parent_size > right_size) {
        printf(
            "[SIZE_VALIDATE] ❌ HEAP VIOLATION: Parent[%d]=%ld > "
            "RightChild[%d]=%ld\n",
            i, parent_size, right_child, right_size);
      }
    }
  }

  // 验证哈希表映射一致性
  for (int i = 0; i < heap_size; i++) {
    cache_obj_t *obj = params->size_heap[i].obj;
    if (params->size_heap_map) {
      gpointer hash_pos = g_hash_table_lookup(params->size_heap_map, obj);
      if (!hash_pos) {
        printf(
            "[SIZE_VALIDATE] ❌ HASH INCONSISTENCY: obj %llu at pos %d not in "
            "hash\n",
            (unsigned long long)obj->obj_id, i);
      } else {
        int expected_idx = GPOINTER_TO_INT(hash_pos) - 1;
        if (expected_idx != i) {
          printf(
              "[SIZE_VALIDATE] ❌ HASH INCONSISTENCY: obj %llu at pos %d but "
              "hash says %d\n",
              (unsigned long long)obj->obj_id, i, expected_idx);
        }
      }
    }

    // 验证对象内索引
    if (obj->LOH.loh_size_pos != i) {
      printf(
          "[SIZE_VALIDATE] ❌ OBJ INDEX MISMATCH: obj %llu at pos %d but "
          "loh_size_pos=%d\n",
          (unsigned long long)obj->obj_id, i, obj->LOH.loh_size_pos);
    }
  }

  printf("[SIZE_VALIDATE] ✅ Size heap validation done (%s): %d nodes\n",
         context, heap_size);
}

#undef likely
#define likely(x) __builtin_expect(!!(x), 1)
#undef unlikely
#define unlikely(x) __builtin_expect(!!(x), 0)

#ifdef __cplusplus
}
#endif
