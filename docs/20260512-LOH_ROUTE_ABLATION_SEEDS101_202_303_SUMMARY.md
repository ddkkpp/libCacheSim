# LOH Route Ablation Seeds101/202/303 当前结果与 Step 说明

本文档汇总 `tmp/20260512-loh-route-ablation/run_staged_cmaes.py` 的 9-step LOH evict pool 路线消融实验当前结果，统计口径改为 `seed=101/202/303`，并用中文说明每个 step 的含义。

## 当前数据范围

- 结果目录: `tmp/20260512-loh-route-ablation/staged-cmaes/`
- 原始结果总表: `tmp/20260512-loh-route-ablation/staged-cmaes/matrix_results.tsv`
- 三 seed 分步总表: `tmp/20260512-loh-route-ablation/staged-cmaes/current_seed101_202_303_full_step_summary.tsv`
- 三 seed 分 trace 组表: `tmp/20260512-loh-route-ablation/staged-cmaes/current_seed101_202_303_group_step_summary.tsv`
- 当前统计覆盖 `seed=101/202/303`。
- 当前公平统计只纳入同一 `seed/trace/target/cfg` 下 9 个 step 都已经 `ok` 的组；本次共有 156/156 个完整 seed-trace-target 组。
- 三 seed 原始 OK 行共 1404 条；本次三 seed 口径没有 incomplete seed-trace-target 组。
- 实验使用 CMA-ES 直接运行 `cachesim`，不是 DRL。

## 百分比口径

表中的所有 `Δ%` 都是相对同一个 `seed/trace/target/cfg` 下的 `base_no_pool` 计算：

```text
(当前 step 的目标指标 / base_no_pool 的目标指标 - 1) * 100
```

- `target=mr` 时，目标指标是 MR。
- `target=bmr` 时，目标指标是 BMR。
- 负数表示比 `base_no_pool` 更好；正数表示比 `base_no_pool` 变弱。
- `speedup` 是同一个 trace-target 上的 `当前 step MQPS / base_no_pool MQPS`。
- 分步总表里的 `quality_ok_0p5pct` 表示五个 trace group 的 MR/BMR target 平均退化都不超过 +0.5%。
- 分 trace 组表里的 `worst_target_rel_pct` 表示该组内最差的单个 seed-trace-target 退化；它比只看组平均更严格。

## 代码默认开关状态

截至本次整理，`libCacheSim/cache/eviction/LOH.c` 中新增 evict pool 路线相关布尔开关默认全部关闭。只有显式设置环境变量时才启用对应逻辑：

- `LOH_EVICT_POOL_ENABLE=0`
- `LOH_EVICT_POOL_REFILL=0`
- `LOH_EVICT_POOL_NEWOBJ=0`
- `LOH_EVICT_POOL_GUARD=0`
- `LOH_EVICT_POOL_HEALTH_LOG=0`
- `LOH_EVICT_POOL_EVENT_REBUILD=0`
- `LOH_EVICT_POOL_GUARD_REBUILD_ONLY=0`
- `LOH_EVICT_POOL_ADAPTIVE=0`
- `LOH_EVICT_POOL_SOURCE_ADAPTIVE=0`
- `LOH_EVICT_POOL_NEWOBJ_STAGING=0`
- `LOH_EVICT_POOL_WARMUP_ALLOWLIST=0`
- `LOH_EVICT_POOL_LOW_WATERMARK=0`

非布尔阈值参数保留原默认值，例如 `LOH_BATCH_EVICT_SIZE=16`、`LOH_EVICT_POOL_HEALTH_WINDOW=256`、`LOH_EVICT_POOL_MIN_VALID_RATE=0.60`、`LOH_EVICT_POOL_WARMUP_MAX_BATCH=8`、`LOH_EVICT_POOL_WARMUP_MAX_ONE_HIT=1.0`。这些阈值只有在对应布尔开关打开后才参与逻辑。

## 实验固定参数

除每个 step 自己覆盖的 evict pool 开关外，`run_staged_cmaes.py` 对所有 step 使用同一组 LOH/CMA-ES 环境：

| 参数 | 值 | 作用 |
| --- | --- | --- |
| `LOH_ENABLE_RL` | `0` | 关闭 DRL，只跑 C 侧 LOH/CMA-ES。 |
| `LOH_ENABLE_CMAES` | `1` | 启用 CMA-ES 权重优化/推理路径。 |
| `LOH_AUTO_COMPOUND` | `0` | 不使用 auto compound 自动特征裁剪。 |
| `LOH_SCORE_USE_COMPOUND` | `1` | 使用 compound scoring。 |
| `LOH_SCORE_USE_IRT` | `0` | 不启用 IRT 来源，因此 evict pool refill 来源为 recency/frequency/size 三类。 |
| `LOH_INCLUDE_HIT_MISS_FEATURES` | `1` | 包含 hit/miss 相关特征。 |
| `LOH_FEATURE_LOG1P` | `1` | 对特征使用 log1p 变换。 |
| `LOH_MISS_RATIO_WEIGHT` | `1.0` | 本轮目标按对应 cfg 的 MR/BMR 权重运行。 |
| `LOH_RANDOM_CANDIDATES` | `256` | 每次 fresh scoring 的随机候选数。 |
| `LOH_STRUCTURED_CANDIDATES` | `16` | 每次 fresh scoring 的结构化候选总数。 |
| `LOH_CMAES_DEGRADE_DETECT` | `0` | 关闭 CMA-ES degrade restart 检测，避免重启噪声影响路线对比。 |
| `LOH_CMAES_FEEDBACK` | `weighted` | 使用 weighted feedback。 |
| `LOH_CMAES_ASYNC` | `1` | 异步 CMA-ES。 |
| `LOH_CMAES_ALGO` | `aipop` | 使用 aIPOP CMA-ES。 |
| `LOH_PARALLEL_SAFE` | `1` | 并行任务使用隔离 key/日志路径。 |

未在 step 中显式覆盖的 evict pool 阈值使用 `LOH.c` 默认值：`LOH_EVICT_POOL_GUARD_INTERVAL=256`、`LOH_EVICT_POOL_GUARD_MIN_SAMPLES=8`、`LOH_EVICT_POOL_GUARD_BAD_RATE=0.25`、`LOH_EVICT_POOL_GUARD_REL_EPS=0.01`、`LOH_EVICT_POOL_GUARD_ABS_EPS=0.0`、`LOH_EVICT_POOL_HEALTH_WINDOW=256`、`LOH_EVICT_POOL_MIN_VALID_RATE=0.60`、`LOH_EVICT_POOL_NEWOBJ_PRESSURE_PCT=0.005`、`LOH_BATCH_MAX_AGE=0`。

## Evict Pool 代码级公共流程

以下流程来自 `libCacheSim/cache/eviction/LOH.c`，所有打开 evict pool 的 step 都沿用同一套骨架，只是打开的维护/保护分支不同。

1. fresh scoring 路径先收集候选：compound 模式且 IRT 关闭时，结构化候选来自 recency、frequency、size 三类来源；再加入随机候选。每个候选用当前 LOH 权重算比较分数，选出本次 victim。
2. 在选出本次 victim 后，代码把后续 `LOH_BATCH_EVICT_SIZE-1` 个最差候选写入 `evict_queue`。队列记录对象指针/obj_id、入队时的 `last_access_counter`、`access_count`、score、source、weight epoch 和填充时 virtual time。
3. 如果 `LOH_EVICT_POOL_ENABLE=0`，队列只作为本次驱逐流程的短期 batch 队列；如果 `LOH_EVICT_POOL_ENABLE=1`，队列允许跨请求复用，后续 eviction 可以先走快路径。
4. 快路径取队列头时会验证 weight epoch、队列年龄、对象是否仍存在，以及 `last_access_counter/access_count` 是否仍等于入队快照。验证失败记为 invalid/stale/null，并根据健康窗口逻辑决定是否清队列。
5. 快路径命中后，如果打开 refill，会按被弹出候选的 source 补一个新候选；默认补同源，source-adaptive 打开后会根据队列占用压力和历史 bad rate 选择成本最低的来源。
6. 如果打开 newobj 直插，新对象插入缓存时会按当前 score 尝试插入 evict queue；如果打开 staging，则不直接插入，而是累计新对象字节压力，达到 `max(obj_size, cache_size * LOH_EVICT_POOL_NEWOBJ_PRESSURE_PCT)` 后清队列，等待后续 fresh scoring 重建。
7. 如果打开 guard，代码每 `LOH_EVICT_POOL_GUARD_INTERVAL` 次 pool pop 做一次 shadow fresh-selection audit：比较队列候选 score 与新鲜候选 score；若 fresh candidate 明显更应被驱逐（score 更小），则说明队列头不够新鲜并计为 bad。bad 样本数达到 `LOH_EVICT_POOL_GUARD_MIN_SAMPLES` 后，若 bad rate >= `LOH_EVICT_POOL_GUARD_BAD_RATE`，则按 step 配置选择禁用 pool 或清队列重建。
8. 如果打开 event rebuild，健康窗口每 `LOH_EVICT_POOL_HEALTH_WINDOW` 次 probe 计算 valid rate；valid rate 低于 `LOH_EVICT_POOL_MIN_VALID_RATE` 时清空队列。guard 触发时也清空队列并保留 pool，而不是永久禁用 pool。
9. 如果打开 low-watermark，快路径命中后检查剩余队列长度；剩余元素数 <= `LOH_EVICT_POOL_LOW_WATERMARK` 时清空队列，让下一次 eviction 走 fresh scoring 重建。
10. 如果打开 warmup allowlist，初始化时先把 requested pool 暂缓，等 workload one-hit ratio 可用后，只有 `batch_evict_size <= LOH_EVICT_POOL_WARMUP_MAX_BATCH` 且 `one_hit_ratio <= LOH_EVICT_POOL_WARMUP_MAX_ONE_HIT` 才允许启用 pool。

### Step 新增术语与统计量定义

- candidate：一次 fresh scoring 或 refill 中被考虑的待驱逐对象候选。
- victim：本次 eviction 最终选中的驱逐对象。LOH 当前 score 越小，越倾向于被选为 victim。
- score：LOH 用当前权重和特征计算出的比较值。本文涉及 guard 时，`fresh_score + tolerance < queued_score` 表示 fresh 路径找到的对象比队列头更应该驱逐。
- source：候选来源。本文 IRT 关闭，所以主要来源是 recency、frequency、size 三类结构化来源，另有 random 候选参与 fresh scoring。
- evict queue：C 代码里的 `evict_queue`，保存 fresh scoring 后的后续候选，供后续 eviction 快路径复用。
- evict pool：本文对“允许跨请求复用 evict queue 的机制”的统称；`LOH_EVICT_POOL_ENABLE=1` 时才真正跨请求复用。
- batch：一次 fresh scoring 后保留的候选批大小。`LOH_BATCH_EVICT_SIZE=4` 表示当前 victim 之外最多再缓存 3 个候选。
- weight epoch：LOH 权重版本号。队列候选入队时记录 epoch；如果后续 CMA-ES 更新权重导致 epoch 变化，该候选快路径校验失败。
- virtual time：代码里用请求推进的逻辑时间。队列填充时记录 `evict_queue_fill_vtime`；`LOH_BATCH_MAX_AGE=0` 表示不按 virtual time 限制队列年龄。
- last access counter / access count：对象入队时记录的访问快照；后续如果对象被访问过，这两个计数会变化，队列候选被判为 stale。
- fresh scoring：不复用队列，重新扫描随机候选和结构化候选并计算 LOH score。当前实现按最小 score 选择 victim，因此“fresh score 更小”表示 fresh 路径找到了比队列头更应该驱逐的对象。
- pool pop：一次从 `evict_queue` 取队列头候选的尝试。guard 的 `LOH_EVICT_POOL_GUARD_INTERVAL=256` 统计的是 pool pop 次数，而不是总请求数。
- probe：health window 里的一个观测样本，只在 pool 快路径尝试后记录，不等于请求数，也不等于所有 eviction 次数。一次 pool pop 如果候选通过校验并返回 victim，就记为 valid probe；如果候选不存在或已陈旧，就记为 invalid probe。`LOH_EVICT_POOL_HEALTH_WINDOW=256` 表示累计 256 个 probe 后计算一次窗口统计。
- fast hit：pool pop 后，队列头候选通过全部快路径校验并被直接作为 victim 返回。代码会增加 `evict_pool_fast_hits`，同时把该候选 source 的 `evict_pool_source_pop[source]` 加 1，并向 health window 记一个 valid probe。
- invalid probe：pool pop 后候选不能直接使用，向 health window 记一个 invalid probe。原因包括 `null` 和 `stale`；`null` 表示 obj_id 已经不在哈希表中，`stale` 表示对象仍在但 `last_access_counter` 或 `access_count` 与入队快照不一致。
- valid rate：健康窗口内 `valid_probe / total_probe`。窗口大小是 `LOH_EVICT_POOL_HEALTH_WINDOW=256`；当 `EVENT_REBUILD=1` 且 `valid_rate < LOH_EVICT_POOL_MIN_VALID_RATE=0.60` 时，代码清空队列并保留 pool。
- guard audit：guard 不在每次 pop 都重算 fresh 路径，而是每 256 次 pool pop 抽样一次。audit 时先暂存队列头，再做一次 fresh scoring，比较队列候选和 fresh 候选。
- guard bad：若 fresh 候选不是同一个对象，且 `fresh_score + tolerance < queued_score`，则记为 bad；`tolerance = GUARD_ABS_EPS + GUARD_REL_EPS * max(abs(queued_score), 1)`，本实验为 `0.0 + 0.01 * max(abs(queued_score), 1)`。
- guard bad rate：`evict_pool_guard_bad / evict_pool_guard_audits`。只有 audit 数达到 `LOH_EVICT_POOL_GUARD_MIN_SAMPLES=8` 后才比较阈值；当 bad rate >= `LOH_EVICT_POOL_GUARD_BAD_RATE=0.25` 时，step01 禁用 pool，step02 及之后清队列重建。
- source bad rate：source-adaptive 使用的每源历史坏样本比例，来自 `evict_pool_source_bad[source] / evict_pool_source_pop[source]`；guard bad 会把队列候选的 source 记入 source bad。
- queue pressure：source-adaptive 使用的当前队列占用压力，约为 `queued_count_for_source / source_budget`。本实验 IRT 关闭，候选来源为 recency/frequency/size 三类；未显式设置 source budget 时，refill 的单源预算按 `max(batch/n_sources, 1)` 计算，batch=4 时为 1。
- source-adaptive cost：refill 选源成本为 `queue_pressure + source_bad_rate`，requested source 额外减 `0.05`。成本越低越优先尝试。
- refill：快路径弹出一个队列候选后，再扫描候选补回队列。未打开 source-adaptive 时补同源；打开后按 source-adaptive cost 选择来源。
- refill scan limit：refill 单次扫描候选上限为 `max(32, LOH_STRUCTURED_CANDIDATES + batch + 16)`，本实验 batch=4 时为 36。
- newobj direct insert：新对象刚进入缓存时，立即按当前 score 尝试插入 evict queue 的机制；对应 `LOH_EVICT_POOL_NEWOBJ=1` 且 `NEWOBJ_STAGING=0`。
- staging：新对象不直接进队列，而是先累计 count/bytes 压力；达到 newobj pressure 后清队列，等待 fresh scoring 重建。
- promotion：staging 累计压力达到阈值后触发的一次队列清空/重建事件，代码计入 `newobj_promotions`。
- newobj pressure：new object staging 的累计字节门槛为 `max(obj_size, cache_size * LOH_EVICT_POOL_NEWOBJ_PRESSURE_PCT)`；本实验默认 `LOH_EVICT_POOL_NEWOBJ_PRESSURE_PCT=0.005`。
- event rebuild：不永久关闭 pool，只清空当前队列并让下一次 eviction 重新 fresh scoring 填队列的动作。guard、health valid-rate、newobj staging、low-watermark 都可能触发清队列。
- guard rebuild-only：guard 触发时只做 event rebuild，不设置 `evict_pool_guard_disabled=1`；step02 及之后使用这个模式，step01 不使用。
- health log：只输出/统计健康窗口信息的开关。`HEALTH_LOG=1` 本身不代表会重建；只有 `EVENT_REBUILD=1` 时 valid rate 低于阈值才清队列。
- low-watermark remaining：快路径命中和 refill 后的剩余队列长度，计算为 `evict_queue_len - evict_queue_pos`；当 remaining <= `LOH_EVICT_POOL_LOW_WATERMARK` 时清队列。
- requested pool：脚本请求启用 pool 的状态。warmup allowlist 打开时，代码会先记住 requested 状态，再临时延迟真正启用。
- warmup deferred：warmup allowlist 生效期间的暂缓状态，表示 pool 已被请求但还没通过 one-hit/batch 条件。
- one-hit ratio：warmup allowlist 使用的 workload 一次命中/一次访问对象比例。阈值为 `LOH_EVICT_POOL_WARMUP_MAX_ONE_HIT`；本实验 warmup step 设置为 0.90，默认值是 1.0。
- adaptive bundle：`LOH_EVICT_POOL_ADAPTIVE=1` 的组合开关。它会在初始化阶段派生打开 event rebuild、guard rebuild-only、source-adaptive、newobj staging，并自动设置 low-watermark。

## Step 设计说明

### 参数矩阵

| step | pool | batch | refill | newobj | guard | adaptive | event_rebuild | guard_rebuild_only | source_adaptive | newobj_staging | warmup_allowlist | low_watermark | health_log |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `base_no_pool` | 0 | 16 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `step00_pool_only` | 1 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| `step01_health_guard` | 1 | 4 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| `step02_event_rebuild` | 1 | 4 | 1 | 1 | 1 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 1 |
| `step03_source_adaptive` | 1 | 4 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 0 | 0 | 0 | 1 |
| `step04_newobj_staging` | 1 | 4 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 1 | 0 | 0 | 1 |
| `step05_warmup_allowlist` | 1 | 4 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 1 | 1 (`8`/`0.90`) | 0 | 1 |
| `step06_low_watermark` | 1 | 4 | 1 | 1 | 1 | 0 | 1 | 1 | 1 | 1 | 1 (`8`/`0.90`) | 1 | 1 |
| `step07_adaptive_bundle` | 1 | 4 | 1 | 1 | 1 | 1 | 1* | 1* | 1* | 1* | 1 (`8`/`0.90`) | 1* | 1 |

`*` 表示不是脚本直接写入该变量，而是 `LOH_EVICT_POOL_ADAPTIVE=1` 在 `LOH.c` 初始化阶段自动派生：打开 event rebuild、guard rebuild-only、newobj staging、source-adaptive；batch=4 且未显式设置 low-watermark 时，自动设置 `low_watermark=batch/4=1`。

### 逐 Step 参数明细（含隐式阈值）

下面列的是实际运行值，包含脚本显式设置项和 `LOH.c` 默认项。所有 step 共享 fresh scoring 参数：`LOH_RANDOM_CANDIDATES=256`、`LOH_STRUCTURED_CANDIDATES=16`、`LOH_MIN_CAND_PER_FEATURE=1`、`LOH_SCORE_USE_IRT=0`，因此结构化来源数为 3（recency/frequency/size），每源基础候选配额为 `max(16/3, 1)=5`。

- `base_no_pool`
	- 队列参数: `LOH_BATCH_EVICT_SIZE=16`，fresh scoring 后最多缓存 15 个后续候选；`LOH_BATCH_MAX_AGE=0`/`LOH_EVICT_POOL_MAX_AGE` 未设置，队列年龄不限。
	- pool 参数: `LOH_EVICT_POOL_ENABLE=0`，不跨请求复用 pool；`REFILL/NEWOBJ/GUARD/EVENT_REBUILD/SOURCE_ADAPTIVE/NEWOBJ_STAGING/WARMUP/LOW_WATERMARK/HEALTH_LOG` 全部为 0。
	- 生效阈值: 只有候选收集和 batch 大小生效；guard、health、warmup、low-watermark、新对象压力阈值均不参与。

- `step00_pool_only`
	- 队列参数: `LOH_BATCH_EVICT_SIZE=4`，fresh scoring 后缓存 3 个后续候选；`LOH_BATCH_MAX_AGE=0`，不按请求年龄过期。
	- pool 参数: `ENABLE=1`，`REFILL=0`、`NEWOBJ=0`、`GUARD=0`、`EVENT_REBUILD=0`、`SOURCE_ADAPTIVE=0`、`NEWOBJ_STAGING=0`、`WARMUP_ALLOWLIST=0`、`LOW_WATERMARK=0`。
	- health 参数: `HEALTH_LOG=1`、`LOH_EVICT_POOL_HEALTH_WINDOW=256`、`LOH_EVICT_POOL_MIN_VALID_RATE=0.60`；由于 `EVENT_REBUILD=0`，valid rate 只用于统计/日志，不触发清队列。
	- 生效阈值: 对象快照校验（obj_id、LAC、access_count、weight_epoch）生效；候选池不会主动补充、不会 guard 禁用、不会事件重建。

- `step01_health_guard`
	- 队列参数: `BATCH_EVICT_SIZE=4`、`BATCH_MAX_AGE=0`。
	- refill 参数: `REFILL=1`，`SOURCE_ADAPTIVE=0`，快路径弹出候选后按原 source 补 1 个同源候选；refill scan limit 为 `max(32, LOH_STRUCTURED_CANDIDATES + batch + 16)=36`。
	- newobj 参数: `NEWOBJ=1`、`NEWOBJ_STAGING=0`，新对象按当前 score 直接尝试插入队列；只有 score 赢过队列边界时才插入。
	- guard 参数: `GUARD=1`、`GUARD_INTERVAL=256`、`GUARD_MIN_SAMPLES=8`、`GUARD_BAD_RATE=0.25`、`GUARD_REL_EPS=0.01`、`GUARD_ABS_EPS=0.0`。
	- guard 动作: `EVENT_REBUILD=0`、`GUARD_REBUILD_ONLY=0`，bad rate 达阈值后设置 `evict_pool_guard_disabled=1`、`evict_pool_enable=0` 并清队列，后续回退 fresh scoring。
	- health 参数: `HEALTH_LOG=1`、`HEALTH_WINDOW=256`、`MIN_VALID_RATE=0.60`；由于 event rebuild 关闭，health 只统计/日志。

- `step02_event_rebuild`
	- 继承 step01 的队列、refill、newobj、guard 阈值: `batch=4`、`refill_scan_limit=36`、`GUARD_INTERVAL=256`、`GUARD_MIN_SAMPLES=8`、`GUARD_BAD_RATE=0.25`、`REL_EPS=0.01`、`ABS_EPS=0.0`。
	- event 参数: `EVENT_REBUILD=1`、`GUARD_REBUILD_ONLY=1`、`HEALTH_WINDOW=256`、`MIN_VALID_RATE=0.60`。
	- event 动作: guard bad rate 达阈值时清空队列但保留 pool；fast hit/invalid probe 满 256 个窗口且 valid rate <0.60 时也清空队列。下一次 eviction 通过 fresh scoring 重建队列。
	- 生效阈值: guard 阈值和 health valid-rate 阈值都参与决策；low-watermark 和 warmup 仍关闭。

- `step03_source_adaptive`
	- 继承 step02 的 guard/event 阈值。
	- source-adaptive 参数: `SOURCE_ADAPTIVE=1`，IRT 关闭时来源数为 3；未设置 `loh_source_budget[]`，因此 refill 的 equal budget 为 `max(batch/n_sources, 1)=1`。
	- source 选择公式: 对每个未尝试来源计算 `cost = queue_pressure + bad_rate`，requested source 额外减 `0.05`；`queue_pressure=queued/source_budget`，`bad_rate=source_bad/source_pop`。
	- refill scan limit: 仍为 36；按最低 cost 来源尝试补候选，失败再尝试下一个来源。
	- 生效阈值: source budget、source bad rate、guard 阈值、health 阈值共同参与；newobj 仍为直接插入。

- `step04_newobj_staging`
	- 继承 step03 的 source-adaptive、guard、event 阈值。
	- newobj staging 参数: `NEWOBJ=1`、`NEWOBJ_STAGING=1`、`LOH_EVICT_POOL_NEWOBJ_PRESSURE_PCT=0.005`。
	- staging 阈值: 新对象累计字节达到 `max(obj_size, cache_size * 0.005)` 后，增加 `newobj_promotions`/`event_rebuilds`，清空队列并重置 staged count/bytes。
	- 生效阈值: 新对象不再直接进入队列；新对象压力阈值成为新的清队列触发器，guard/event/source-adaptive 仍同时生效。

- `step05_warmup_allowlist`
	- 继承 step04 的全部阈值。
	- warmup 参数: `WARMUP_ALLOWLIST=1`、`WARMUP_MAX_BATCH=8`、`WARMUP_MAX_ONE_HIT=0.90`。
	- warmup 判定: 初始化时先暂缓 pool；当 one-hit ratio 可用时，只有 `batch=4 <= 8` 且 `one_hit_ratio <= 0.90` 才启用 pool，否则保持 pool disabled 并清空队列。
	- 生效阈值: batch 上限在本实验恒通过，主要门槛是 one-hit ratio 0.90；low-watermark 仍关闭。

- `step06_low_watermark`
	- 继承 step05 的全部阈值。
	- low-watermark 参数: `LOW_WATERMARK=1`。
	- low-watermark 判定: 每次快路径命中并 refill 后，若剩余队列长度 `evict_queue_len - evict_queue_pos <= 1`，立即清空队列，强制下次 eviction 走 fresh scoring 重建。
	- 生效阈值: warmup、newobj pressure、source-adaptive、guard、health、low-watermark 全部参与。

- `step07_adaptive_bundle`
	- 显式参数: `ADAPTIVE=1`、`WARMUP_ALLOWLIST=1`、`WARMUP_MAX_BATCH=8`、`WARMUP_MAX_ONE_HIT=0.90`，并保留 `ENABLE=1`、`BATCH=4`、`REFILL=1`、`NEWOBJ=1`、`GUARD=1`、`HEALTH_LOG=1`。
	- 派生参数: 代码看到 `ADAPTIVE=1` 后自动设置 `EVENT_REBUILD=1`、`GUARD_REBUILD_ONLY=1`、`NEWOBJ_STAGING=1`、`SOURCE_ADAPTIVE=1`；若未显式设置 low-watermark 且 batch>1，则设置 `LOW_WATERMARK=batch/4=1`。
	- 继承阈值: `GUARD_INTERVAL=256`、`GUARD_MIN_SAMPLES=8`、`GUARD_BAD_RATE=0.25`、`REL_EPS=0.01`、`ABS_EPS=0.0`、`HEALTH_WINDOW=256`、`MIN_VALID_RATE=0.60`、`NEWOBJ_PRESSURE_PCT=0.005`、`WARMUP_MAX_BATCH=8`、`WARMUP_MAX_ONE_HIT=0.90`、`LOW_WATERMARK=1`、`refill_scan_limit=36`。
	- 生效阈值: step02 到 step06 的所有阈值都同时参与，是组合 bundle，不代表任何单机制的独立效果。

### base_no_pool

完整参数：`LOH_EVICT_POOL_ENABLE=0`、`LOH_EVICT_POOL_HEALTH_LOG=0`、`LOH_BATCH_EVICT_SIZE=16`；其余 evict pool 开关保持默认关闭。

算法流程：每次需要驱逐时走 LOH 原始 fresh scoring 路径，收集 recency/frequency/size + random 候选并逐个评分。batch queue 只服务于当前驱逐流程，不跨请求复用，也不做 refill、newobj 插入、guard、健康窗口或重建。这个 step 是所有 `Δ%` 与 `speedup` 的质量/吞吐基线。

三 seed 结果：基线本身不计算相对退化；后续所有 step 均相对它计算。

### step00_pool_only

完整参数：`LOH_EVICT_POOL_ENABLE=1`、`LOH_BATCH_EVICT_SIZE=4`、`LOH_EVICT_POOL_REFILL=0`、`LOH_EVICT_POOL_NEWOBJ=0`、`LOH_EVICT_POOL_GUARD=0`、`LOH_EVICT_POOL_ADAPTIVE=0`、`LOH_EVICT_POOL_EVENT_REBUILD=0`、`LOH_EVICT_POOL_SOURCE_ADAPTIVE=0`、`LOH_EVICT_POOL_NEWOBJ_STAGING=0`、`LOH_EVICT_POOL_WARMUP_ALLOWLIST=0`、`LOH_EVICT_POOL_LOW_WATERMARK=0`、`LOH_EVICT_POOL_HEALTH_LOG=1`。

算法流程：fresh scoring 选出当前 victim 后，把后续 3 个最差候选跨请求保存在 evict queue。下一次 eviction 优先复用队列候选，只做对象存在性、epoch、age、访问计数快照校验；队列被消费完或校验失败后回到 fresh scoring。因为没有 refill 和 newobj 直插，队列不会主动维持长度；因为没有 guard/event rebuild，候选陈旧风险只靠快照校验兜底。`HEALTH_LOG=1` 让 fast hit/invalid 进入健康统计和日志，但不会触发清队列重建。

三 seed 结果：平均目标指标改善 -0.140570%，平均吞吐 1.506501x；但 `alibabaBlock` 的 MR target 组平均退化 +4.764646%，最差单个 seed-trace-target 退化 +133.152440%，不适合作为质量约束下的折中候选。

### step01_health_guard

完整参数：在 step00 基础上打开 `LOH_EVICT_POOL_REFILL=1`、`LOH_EVICT_POOL_NEWOBJ=1`、`LOH_EVICT_POOL_GUARD=1`，并保持 `LOH_EVICT_POOL_EVENT_REBUILD=0`、`LOH_EVICT_POOL_GUARD_REBUILD_ONLY=0`、`LOH_EVICT_POOL_SOURCE_ADAPTIVE=0`、`LOH_EVICT_POOL_NEWOBJ_STAGING=0`、`LOH_EVICT_POOL_WARMUP_ALLOWLIST=0`、`LOH_EVICT_POOL_LOW_WATERMARK=0`。

算法流程：快路径弹出候选后，按该候选的 source 做一次同源 refill，使 pool 不至于迅速耗尽；新对象进入缓存时直接按当前 score 尝试插入队列。guard 每 256 次 pool pop 做 shadow fresh audit，累计至少 8 个 audit 后，如果 bad rate >=0.25 且 fresh 候选明显优于队列候选，就认为 pool 质量不安全。因为本 step 没有 event rebuild/rebuild-only，guard 触发后会设置 `evict_pool_guard_disabled=1`、`evict_pool_enable=0` 并清空队列，后续回退到原始 fresh scoring 慢路径。

三 seed 结果：平均目标指标改善 -0.812974%，最差 group-target 平均只退化 +0.015735%，是质量优先最稳配置；代价是 guard 经常禁用 pool，平均吞吐只有 1.081825x，没有达到 2x。

### step02_event_rebuild

完整参数：继承 step01，并改为 `LOH_EVICT_POOL_EVENT_REBUILD=1`、`LOH_EVICT_POOL_GUARD_REBUILD_ONLY=1`。

算法流程：保留同源 refill、新对象直插和 guard audit。差异在失败处理：guard bad rate 过高时不再永久禁用 pool，而是增加 event rebuild 计数、清空队列并保留 pool；健康窗口每 256 次 fast probe 计算 valid rate，低于 0.60 时同样清队列。下一次 eviction 走 fresh scoring 后重新填充 pool。这个 step 的核心是用“事件式清队列重建”替代“禁用 pool”，让大多数 trace 保持快路径收益。

三 seed 结果：唯一同时满足平均吞吐 >=2x 和五组 MR/BMR target 平均基本不弱的配置，平均吞吐 2.070856x，平均目标指标改善 -0.196300%，最差 group-target 平均为 `alibabaBlock` BMR +0.385718%。仍存在最差单个 seed-trace-target +42.009508% 的局部退化，因此该结论适用于组平均质量约束，不代表单 trace 最坏情况安全。

### step03_source_adaptive

完整参数：继承 step02，并打开 `LOH_EVICT_POOL_SOURCE_ADAPTIVE=1`。

算法流程：refill 不再固定补被弹出候选的同源，而是在可用来源中计算 `queue_pressure + bad_rate` 成本；requested source 有 -0.05 的轻微优先级。`queue_pressure` 来自当前队列中该来源占用数与来源预算的比例，`bad_rate` 来自历史 source pop/bad 统计。代码会尝试成本最低的来源，找不到候选再尝试下一个来源。目标是避免某个来源占满 pool，并避开历史 bad source。

三 seed 结果：该策略在本轮配置下明显过激，平均吞吐升到 4.637103x，但平均目标指标退化 +28.258237%，最差 group-target 平均达到 +63.549033%。因此 step03 不适合作为最终质量配置。

### step04_newobj_staging

完整参数：继承 step03，并打开 `LOH_EVICT_POOL_NEWOBJ_STAGING=1`；`LOH_EVICT_POOL_NEWOBJ_PRESSURE_PCT` 使用默认 `0.005`。

算法流程：新对象不再直接按 score 插入队列，而是累计 staged count 和 staged bytes。阈值为 `max(obj_size, cache_size * 0.005)`；累计字节达到阈值后，代码增加 `newobj_promotions`/`event_rebuilds`，清空队列并重置 staged 计数，让下一次 eviction 通过 fresh scoring 重建 pool。目标是降低高 churn 场景中新对象直接挤入队列带来的排序扰动。

三 seed 结果：step04 仍严重退化，平均目标指标 +29.552006%，平均吞吐 3.910887x，最差 group-target 平均 +79.951721%，远超质量约束。

### step05_warmup_allowlist

完整参数：继承 step04，并打开 `LOH_EVICT_POOL_WARMUP_ALLOWLIST=1`、`LOH_EVICT_POOL_WARMUP_MAX_BATCH=8`、`LOH_EVICT_POOL_WARMUP_MAX_ONE_HIT=0.90`，`LOH_EVICT_POOL_LOW_WATERMARK=0`。

算法流程：初始化时如果 requested pool enable，则先把 `evict_pool_enable` 置 0 并标记 warmup deferred；等 one-hit ratio 可用时运行 allowlist。只有 batch size 不超过 8 且 one-hit ratio 不超过 0.90，才真正启用 pool 并清空旧队列。对于一次性对象比例很高的 trace，这一步会延迟或禁止 pool，避免早期缓存不稳定候选。

三 seed 结果：相比 step03/04 有缓和，但仍不合格；平均目标指标 +11.121853%，平均吞吐 2.832056x，最差 group-target 平均 +28.115777%。allowlist 有保护作用，但不足以修复 source-adaptive/newobj-staging 组合带来的质量问题。

### step06_low_watermark

完整参数：继承 step05，并设置 `LOH_EVICT_POOL_LOW_WATERMARK=1`。

算法流程：每次快路径成功弹出候选并完成 refill 后，检查剩余队列长度。如果 `evict_queue_len - evict_queue_pos <= 1`，立即清空队列。下一次 eviction 将回到 fresh scoring，重新填充 pool。目标是避免消费队列尾部少量、可能更陈旧的候选。

三 seed 结果：平均目标指标 +12.515419%，平均吞吐 2.734588x，最差 group-target 平均 +30.072455%。在当前组合下，低水位重建没有解决核心质量问题，反而可能让 pool 更频繁进入不稳定重建状态。

### step07_adaptive_bundle

完整参数：脚本显式设置 `LOH_EVICT_POOL_ADAPTIVE=1`、`LOH_EVICT_POOL_WARMUP_ALLOWLIST=1`、`LOH_EVICT_POOL_WARMUP_MAX_BATCH=8`、`LOH_EVICT_POOL_WARMUP_MAX_ONE_HIT=0.90`，并保留 pool/refill/newobj/guard/batch=4。代码派生打开 `LOH_EVICT_POOL_EVENT_REBUILD=1`、`LOH_EVICT_POOL_GUARD_REBUILD_ONLY=1`、`LOH_EVICT_POOL_NEWOBJ_STAGING=1`、`LOH_EVICT_POOL_SOURCE_ADAPTIVE=1`；由于没有显式 low-watermark 且 batch=4，初始化时自动设置 `LOH_EVICT_POOL_LOW_WATERMARK=1`。

算法流程：这是 step02 到 step06 的 bundle：同源/自适应 refill、guard audit、健康窗口 event rebuild、新对象 staging、warmup allowlist、low-watermark 都同时参与。它代表“完整自适应方案”的组合效果，而不是单个机制的独立贡献。

三 seed 结果：平均目标指标 +13.919307%，平均吞吐 2.746773x，最差 group-target 平均 +33.071476%。质量仍明显变弱，不建议作为最终配置。

## 当前推荐

按“目标质量不能基本变弱”优先：推荐 `step01_health_guard`。它的五组 MR/BMR target 平均几乎都不变弱，平均目标指标改善 -0.812974%，最差 group-target 平均 +0.015735%；代价是吞吐只有 1.081825x。

按“平均吞吐 >=2x 且五组 target 平均基本不弱”优先：推荐 `step02_event_rebuild`。它有 2.070856x 平均吞吐和 -0.196300% 平均目标改善，最差 group-target 平均为 +0.385718%，落在 +0.5% 防线内。

按“单个 trace 最坏情况也必须严格不退化”看：当前没有 step 完全安全。`step02_event_rebuild` 虽然组平均合格，但最差单个 seed-trace-target 仍有 +42.009508% 局部退化，需要后续 per-trace gating 或针对异常 trace 继续诊断。

结论：三 seed 组平均口径下，最终 manifest 若要保质量并接受较低吞吐，优先选 `step01_health_guard`；若目标是同时拿到约 2x 吞吐和五组 MR/BMR target 平均不弱，优先选 `step02_event_rebuild`。`step03_source_adaptive` 及之后 step 不建议作为质量约束下的最终配置。
