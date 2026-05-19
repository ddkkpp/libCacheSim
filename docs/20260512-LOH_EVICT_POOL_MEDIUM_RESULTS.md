# LOH Evict Pool 中等规模 trace 结果

## 范围

本文记录 `tmp/20260511-loh-evict-pool/` 中等规模 trace 上的 LOH evict/candidate pool 复用验证。

目标是：平均 MR 和 BMR 不退，同时显著提高平均吞吐量。

## 详细算法

这次改动不只是增加几个开关，而是在 LOH 原有候选评分路径上增加了一层“已评分驱逐候选复用”。

普通 LOH 在 miss 且需要腾空间时，大致流程是：

1. 从 cache 里抽取当前配置的候选集合。
2. 对每个候选计算 LOH 特征，再用当前 CMA-ES、RL 或静态权重得到候选分数。
3. 按比较分数选出最差候选并驱逐。

evict pool 路径保留同一套评分函数，但把第 1 步和第 2 步的成本摊到后续驱逐上：

1. 完成一次完整候选扫描后，从同一批已评分候选里继续选出后续最差的一组对象。
2. 把这些对象写入 `evict_queue`，同时保存 `obj_id`、`last_access_counter`、`access_count`、填充时间戳和权重 epoch。
3. 后续 eviction 先尝试复用 `evict_queue`，成功时不用重新抽样和重新计算整批候选分数。
4. 只有当队列项仍在 cache 中，并且入队后没有被再次访问，才允许复用。
5. 如果权重 epoch 改变、队列超过 `LOH_EVICT_POOL_MAX_AGE`、队列耗尽，直接清空队列。

注意，周期切换时只做失效和清池，不主动重建 pool。新的候选池必须在该周期第一次真正需要 eviction 时，由 `LOH_to_evict()` 走完整候选评分后惰性填充；这样没有 eviction 的周期不会额外付出扫描成本。

关键安全点是：队列里不是裸指针直驱逐。`LOH_EVICT_POOL_ENABLE=1` 时，fast path 会按 `obj_id` 重新查找对象，并校验旧的访问元数据；对象被访问过、删除过或权重变化过都会失效。不启用 pool 时，每个请求都会清掉队列，所以 batching 只对一次插入触发的连续多次 eviction 有帮助。

当前实现给 LOH 增加了低开销的新对象入池路径。一次 miss 需要为新对象腾空间时，新对象仍然不是当次 eviction 候选；但插入 cache 之后，如果 `LOH_EVICT_POOL_ENABLE=1` 且旧 `evict_queue` 仍在有效期内，`LOH_EVICT_POOL_NEWOBJ=1` 会只给这个新对象计算一次同口径比较分数。只有当新对象分数比当前未消费 pool 的边界更差时，才把它按分数插入队列；否则跳过。因此它不是无条件追加，也不会触发全 cache 重排。

同源前沿补位进一步减少了“有限结构化前沿”导致的偏差。完整候选评分时，每个入队对象会保存来源：recency、frequency、size、IRT1、IRT2、IRT3 或 random。完整路径本次选出的最差对象，以及 fast path 后续消费的结构化来源队列项，都会在 `LOH_EVICT_POOL_REFILL=1` 时从同一个结构化源扫描下一个未在剩余队列中的候选，按当前权重计算一次比较分数后插回未消费队列。这样 pool 不再只是上一次有限候选集合的静态 next-K 快照，而是在复用期间持续补齐被消费来源的前沿。random 来源和新对象来源不做补位；队列已经耗尽时仍回到下一次完整候选评分，避免单源链条无限延长。

为了让这个增量排序安全，`evict_queue` 现在会保存每个队列项的 `compare_score`。新对象插入时只搬运未消费队列项的旧快照元数据，不重写旧对象的 `last_access_counter` 和 `access_count`。这很重要：如果旧队列项已经被命中过，它仍会在 fast path 校验时失效，不会因为队列压缩被重新标记为有效候选。队列年龄和权重 epoch 也不因新对象插入而延长。

比较分数默认仍是 LOH score。`LOH_EVICT_SCORE_BY_SIZE=1` 会改成 `score / obj_size`，更偏向驱逐“大且低收益”的对象，理论上可能改善 BMR。但当前中等 trace 数据不支持默认打开它，尤其 `f101_orig` 更敏感，所以除非有 allowlist 或在线 guard 证明安全，否则保持关闭。

## v7 特征空间

v7 不是只有 `f100_ns` 和 `f101`。完整紧凑命名是 `fXYZ_suffix`：

- `X` 表示 `LOH_USE_FREQ_REC`，即 `freq/rec` 复合特征。
- `Y` 表示 `LOH_USE_FREQ_SIZE`，即 `freq/size` 复合特征。
- `Z` 表示 `LOH_USE_REC_SIZE`，即 `rec*size` 复合特征。
- `suffix=orig` 表示 `LOH_USE_SIZE=1`，基础 size 特征参与评分。
- `suffix=ns` 表示 `LOH_USE_SIZE=0`，基础 size 特征关闭。

LOH 始终保留 recency 和 frequency 两个基础维度；`fXYZ` 三个 bit 只控制三个复合维度。因此 8 种 bit 模式乘以 `orig/ns` 后，共有 16 个 v7 特征配置：`f000_ns` 到 `f111_ns`，以及 `f000_orig` 到 `f111_orig`。

`baseline_summary_v7*.md` 中使用的 v7 策略是：

- MR 目标：优先 `f001_orig`，fallback 为 `f100_ns`。
- BMR 目标：如果 `one_hit <= 0.72`，用 `f100_ns`；否则用 `f101_orig`，fallback 为 `f100_ns`。

旧实验记录里有时把 `f101_orig` 简写成 `f101`。本文中的 `f101` 都按 `f101_orig` 理解，不是 v7 之外的独立配置。

当前 `LOH_AUTO_COMPOUND` 代码里也有相近的 BMR 分支，但实现阈值是 `one_hit <= 0.67`，和 v7 文档阈值 `0.72` 不完全一致。复现实验报告时以 v7 文档为准；后续若改 `LOH.c`，应把阈值显式参数化，不要把新阈值硬编码进 pool 逻辑。

## 自适应 pool 选择

这里有两个决策，不能混在一起：

- 特征配置选择：决定 LOH 用哪个 `fXYZ_orig/ns` 评分模型，以及目标是 MR 还是 BMR。
- evict pool 选择：决定是否安全地跨请求复用已评分 eviction 候选。

当前中等 trace 结果说明，pool 安全性不能只看是不是 `f100_ns`。`alibabaBlock_3`、`alibabaBlock_507`、`tencentBlock_3879` 在 `f100_ns pool128_age0_newobj` 下收益很大；`tencentBlock_1069 f100_ns` 需要更保守的 `pool8_age0_newobj` 才能严格 MR/BMR 不退。`f101_orig` 与 `f100_orig` 不是必然退化，但非常不稳定：补测 6 个 trace/config、12 个 pool 变体后，只有 2 个变体同时满足 MR/BMR 不退。

因此，不提前做完整 A/B 的选择算法要先保质量。当前 online guard 第一版不做 warmup eligibility，也不使用 MR/BMR quality-window 归因；只要调用者同时开启 `LOH_EVICT_POOL_ENABLE=1` 与 `LOH_EVICT_POOL_GUARD=1`，所有 `fXYZ_orig/ns` 配置都走同一套在线审计。

运行逻辑：

1. 大部分 eviction 仍从 `evict_queue` fast path 复用候选。
2. 每隔 `LOH_EVICT_POOL_GUARD_INTERVAL` 次 pooled pop 抽样一次 shadow audit：不直接返回队列候选，而是临时清队列并走完整候选评分路径。
3. 对比队列候选入池时保存的 `compare_score` 与当前 fresh full-rescore 选出的最差候选分数。
4. 如果 fresh 候选不是同一个对象，并且 `fresh_score + abs_eps + rel_eps * max(|queued_score|, 1) < queued_score`，记为一次 bad audit。
5. 当 audit 样本数达到 `LOH_EVICT_POOL_GUARD_MIN_SAMPLES`，且 bad 比例达到 `LOH_EVICT_POOL_GUARD_BAD_RATE`，立即清队列并把 `evict_pool_enable` 置 0，本次运行不再跨请求复用 pool。
6. 这个 guard 只审计 pool 候选是否相对当前候选集过旧，不用 MR/BMR 窗口判断整体质量，因此不会把 workload 自身波动误归因给 pool。

可用的 warmup 信号已经在 `[LOH WARMUP_DIAG]` 和 `[LOH WARMUP_DIAG_BMR]` 中输出：

- `one_hit`：v7 BMR 分流信号，低值更倾向 `f100_ns`。
- `r1/r2` 与 `R2m_fs/R2m_rs`：判断 size 相关复合特征是否冗余，或是否被基础特征强解释。
- `cv_freq`、`cv_sz`、`cv_rec` 以及原始 CV：判断 workload 是 churn/bursty 还是更稳定。
- `r_bmr_fs`、`r_bmr_rs`：判断 size 相关复合特征是否可能通过偏向大对象 eviction 伤害 BMR。

推荐使用形态是：

```text
diag = read_warmup_diag()
cfg = select_v7_cfg(target, diag)

if pool_experiment_enabled:
	enable_pool(batch_size)
	enable_shadow_audit_guard()

while running:
	validate_queue_entry()
	if sampled_pooled_pop:
		fresh = full_rescore_current_candidates()
		compare_queued_vs_fresh()
	if shadow_audit_bad_rate_trips:
		clear_pool()
		disable_pool_for_rest_of_run()
```

初始安全谓词应当保守，不能只把这 5 条中等 trace 的名字硬编码进去。第一版采用单向回退：guard 只要判定队列候选在当前 fresh rescore 下过旧，就关闭 pool 到运行结束。这样会牺牲一部分单 trace 速度，但避免在非平稳 trace 上反复开关。

仅靠 warmup diagnostics 不能严格保证不退，因为同一次运行里没有完全等价的 base 反事实。真正适合这里的 guard 不是完整预跑 A/B，也不是 quality-window guard，而是在线轻量审计：大部分 eviction 走 pool；每隔固定次数抽样一次 shadow full-rescore，用原始完整候选评分路径审计“pool 给出的对象是否仍然接近当前最差候选”。如果 shadow 审计失败率超过阈值，就关闭 pool。

## 3LCache 的选择和池化

3LCache 在本仓库里有两个层面的选择：

- 运行目标由调用者选择。默认 `objective=byte-miss-ratio`，cache 名称为 `ThreeLCache-BMR`；传 `objective=object-miss-ratio` 时名称为 `ThreeLCache-OMR`。
- summary 文档里的 `ThreeLCache-target` 是评测层的目标映射，不是一次运行中 3LCache 自动在 OMR/BMR 之间切换。

所以 3LCache 的 metric objective 是固定的：一次运行开始前选 BMR 或 OMR，运行中不会自动切换目标。

但 3LCache 的候选采样并不是一个完全固定的池，也不是 LOH 现在这种跨请求复用 `evict_queue` 的池。它的核心是“固定默认值 + 在线调整采样边界”：

- `sample_rate` 名义默认是 `1024`，但 `rank()` 会按当前 in-cache 队列长度和 eviction rate 做 cap，所以实际每轮候选数不是无条件固定 1024。
- BMR 目标下，完成一轮扫描后会根据 eviction 频率分布更新 `sample_boundary`，决定后续优先采哪些 frequency 区间。
- OMR 目标下，初始化时把 `sample_boundary` 放开，基本不走 BMR 的频率边界收缩逻辑。
- `sampling_lru` 会根据 eviction 分布递增或递减，影响从 LRU 方向扫描时保底采样的比例。
- `reserved_space` 会根据新对象压力和 eviction 分布递增或折半，影响 `quick_demotion()` 何时优先拿新对象做候选。
- `hsw` 会根据 window hit 信号最多增到 6，从而扩大 out-cache 历史窗口，给 LightGBM 训练提供更长历史。

具体采哪些对象作为候选，分三层：

1. 还没有 LightGBM booster 时，`evict_predobj()` 直接回退到 in-cache 队列头，也就是当前 LRU 端对象。
2. 有 booster 后，`rank()` 先调用 `quick_demotion()`。如果累计新对象大小 `new_obj_size` 超过 `_currentSize * reserved_space / 100`，它会从 `new_obj_keys` 中取仍在 in-cache 的新对象作为候选，上限约为 `sample_rate * 1.5`。
3. 然后从 `samplepointer` 开始沿 in-cache 环形队列扫描。对象满足 `freq < sample_boundary`，或者仍处在 `initial_queue_length * sampling_lru / 100 + eviction_rate` 的 LRU 保底扫描区间，就会进入候选集。扫描直到收满本轮 `sample_rate` 候选，或者绕过当前 in-cache 队列。
4. `prediction()` 对这些候选提取 age、历史距离、size、frequency 等特征，写入 `pred_map` 和 `pred_times`。后续 eviction 从预测堆里取预测复用距离或 size-weighted 复用距离最大的有效对象。

3LCache 的“池”主要是 `pred_map` + `pred_times` 这个预测候选缓存。它没有固定 TTL，也没有类似 `LOH_EVICT_POOL_MAX_AGE` 的 request-age 保留时间；保留多久由事件驱动：

- `evict_nums <= 0` 或 `pred_map` 为空时，会重新 `rank()` 生成新候选。
- 一次 `rank()` 后，`evict_nums = rank_result / eviction_rate`，默认 `eviction_rate=2`，所以预测池大致服务本轮候选数一半的后续 eviction。
- 每驱逐一个预测对象，会从 `pred_map` 删除该 key。
- 如果对象命中并更新位置，`lookup()` 会删除该对象的旧预测。
- 如果扫描绕完整个 in-cache 队列，`rank()` 会清空 `pred_map` 和 `pred_times`。
- 每次 `train()` 重新训练 LightGBM 后，也会清空 `pred_map` 和 `pred_times`。
- 如果从预测堆取出的对象已经不在 in-cache，或位置越界，`evict_predobj()` 会丢弃该预测并继续弹下一个。
- `ThreeLCache_to_evict()` 里的 `to_evict_candidate_gen_vtime` 只保证同一个 request vtime 内 `to_evict` 和 `evict` 是同一对象，不是跨请求池化。

因此，“一次 rank 服务 512 次 eviction”不是代码保证，而只是默认大 cache、默认参数下的典型值：`sample_rate=1024`、`eviction_rate=2`、且 `rank_result` 恰好约等于 1024 时，`evict_nums=512`。实际会被以下条件改变：

1. `ThreeLCacheCache::init_with_params()` 支持 `sample_rate`，但当前 C wrapper 的 `ThreeLCache_parse_params()` 只暴露 `objective` 与 `print`，`ThreeLCache_init()` 也只把 `objective` 放进 `params_map`。因此在当前 cachesim 入口下，`sample_rate` 实际按默认 `1024` 运行，除非未来扩展 wrapper 参数透传。
2. `rank()` 会原地把 `sample_rate` cap 到 `initial_queue_length * 0.01 + eviction_rate`，小 cache 或当前 in-cache 队列较短时，`rank_result` 会低于 1024。
3. `quick_demotion()` 会在新对象累计大小超过 `_currentSize * reserved_space / 100` 时先加入新对象候选，最多约 `sample_rate * 1.5` 个；如果后续新对象压力降到 `_currentSize * reserved_space / 10` 以下，普通 in-cache 扫描还会继续补候选，所以 `rank_result` 也可能高于名义 `sample_rate`。
4. 普通扫描还受 `sample_boundary`、`sampling_lru` 和绕完整个 in-cache 环形队列的事件影响。绕圈时会重置 `sample_rate`、清空旧预测池，并更新 `sample_boundary`、`sampling_lru`、`reserved_space`；本轮最终 `rank_result` 取决于这些在线状态。
5. 即使已经得到 `evict_nums = rank_result / eviction_rate`，实际复用次数也可能提前结束：命中会删除对应 `pred_map` 项，训练会清空预测池，过期或越界预测会被跳过；只要 `evict_nums <= 0` 或 `pred_map` 为空，就会触发下一次 `rank()`。

新对象到来后的处理也和 LOH 不同：3LCache 在 `admit()` 里把新对象 id 追加到 `new_obj_keys`，并累计 `new_obj_size`。已经生成的 `pred_map/pred_times` 不会立刻包含这些新对象；只要 `evict_nums > 0` 且 `pred_map` 还没空，后续 eviction 仍优先消费旧预测池。等下一次 `rank()` 触发时，`quick_demotion()` 会先看 `new_obj_size > _currentSize * reserved_space / 100` 是否成立，成立才把仍在 in-cache 的新对象加入候选。因此，3LCache 会主动追踪新对象，但新对象进入候选池是下一轮 rank 的事情，不是旧预测池的即时增量更新。

因此，3LCache 的“池化”不是固定 pool，也不是跨请求直接复用旧 eviction 结果。它更像一个在线采样与模型维护系统：目标固定，候选采样边界、LRU 扫描比例、reserved space、预测候选缓存、历史窗口和 LightGBM 训练都会随运行过程或事件变化。

### 3LCache 为吞吐量做了什么

3LCache 的吞吐优化不是单个 pool 开关，而是一整套“少调用模型、批量调用模型、复用模型结果、延后训练”的设计。

第一层是命中路径不做模型推理。`ThreeLCache_find()` 只把请求转成 `SimpleRequest` 后调用 `ThreeLCacheCache::lookup()`。`lookup()` 命中时更新 `Meta` 的时间、频率和历史距离，必要时把命中的对象从 `pred_map` 里删掉，避免后续驱逐使用旧预测；它不会为每个 hit 调 LightGBM。训练样本也不是每次 hit 都生成：只有对象之前被 `sample()` 标记过，且满足随机 1/4 抽样或当前还没有 booster 时，才调用 `training_data->emplace_back()`。

第二层是没有模型时直接退回 LRU。`evict_predobj()` 开头检查 `if (!booster)`，没有训练出 LightGBM booster 时直接返回 `in_cache.q.head`。这样 warmup 早期不会为了不成熟模型付推理成本，也避免冷启动阶段频繁采样、预测。

第三层是一次 rank 批量推理一组候选，而不是每次 eviction 推理一个候选。`rank()` 先用 `quick_demotion()` 收集新对象压力候选，再从 `samplepointer` 沿 in-cache 环形队列扫描；候选只要满足 `freq < sample_boundary`，或落在 `sampling_lru` 控制的 LRU 保底区间，就进入 `sampled_objects`。随后 `prediction(sampled_objects)` 把整批候选转成 CSR 格式，一次调用 `LGBM_BoosterPredictForCSR()` 得到全部 scores。也就是说，LightGBM 推理成本按一批候选摊销，而不是按一次 eviction 支付。

第四层是预测结果跨多次 eviction 复用。`prediction()` 把每个候选写入 `pred_map`，同时推入 `pred_times` heap；`evict_predobj()` 后续从 heap 里弹出预测复用距离最大的对象。只有当 `evict_nums <= 0` 或 `pred_map` 为空时，才重新 `rank()`。默认大 cache 情况下，`rank()` 返回约 1024 个候选，`evict_nums = rank() / eviction_rate`，默认 `eviction_rate=2`，因此一轮批量推理通常可以服务约 512 次 eviction。

第五层是用事件让旧预测自然失效，而不是每次重新验证全候选。命中时 `lookup()` 删除该对象的 `pred_map` 项；驱逐时 `evict_with_candidate()` 删除被驱逐 key；`evict_predobj()` 弹 heap 时如果对象已不在 in-cache、位置越界、或 `pred_map[key]` 与 heap 里的 score 不一致，就跳过该旧预测。这样保留了大部分预测复用收益，同时避免为每个 pooled candidate 做完整重评分。

第六层是训练批量化且避开正在消费的预测池。`TrainingData` 预留 `batch_size = 131072 / 2` 条样本，只有 `labels.size() >= batch_size && evict_nums <= 0` 时才 `train()`。`train()` 使用 LightGBM 的 CSR 数据集，默认 `num_iterations=16`、`num_leaves=32`、`num_threads=1`、`feature_fraction=0.8`、`bagging_fraction=0.8`，训练结束后清空 `pred_map/pred_times`。这个条件很关键：模型重训不会在一轮预测池还没消费完时打断复用，而是等候选池耗尽后再切换模型。

第七层是特征和历史窗口都被刻意限宽。`n_feature = max_n_past_timestamps + 2`，当前只有 age、最多 3 个 past distance、size、frequency 这类小特征；`out_cache` 的大小由 `hsw` 控制，`hsw` 最多增到 6。也就是说，3LCache 用较小的 per-object 元数据和短历史窗口换取可承受的在线训练/推理成本。

第八层是采样边界自适应减少无效候选。BMR 目标下，扫描绕完整个 in-cache 队列后，`rank()` 根据 `object_distribution_n_eviction` 的 99% 分位更新 `sample_boundary`，根据 eviction 分布调整 `sampling_lru`，并根据新对象压力调整 `reserved_space`。这让后续 rank 更倾向于采到可能被驱逐的频率区间、LRU 区间和新对象区间，而不是每轮都在全 cache 上做均匀大采样。

因此，3LCache 的吞吐来自多个摊销层叠加：hit 路径只更新元数据；miss eviction 不一定触发 rank；rank 后一次 LightGBM batch inference 服务多次 eviction；训练等样本够多且候选池耗尽才发生；候选覆盖范围随运行状态调整。它和 LOH 当前 pool 的主要差别是，3LCache 从一开始就把模型、采样、预测缓存和训练时机作为一个整体来摊销，而 LOH pool 是在原本每次 eviction fresh scoring 的路径外面再加一层结果复用。

### 为什么 3LCache 的池化更稳

3LCache 的 pool 效果好，主要不是因为“保存一批候选再复用”这个动作本身，而是因为它的候选池和模型是一起设计的。

- 3LCache 复用的是 `pred_map/pred_times` 预测候选缓存，不是一次 fresh selection 后的静态 next-K 驱逐顺序。每轮 `rank()` 都会按当前采样边界、LRU 保底比例、新对象压力和训练状态重新生成候选。
- 3LCache 的池生命周期是事件驱动的：命中删除旧预测、驱逐删除对象、LightGBM 重新训练清空预测、扫描绕环也清空预测。因此它不只校验“对象还在不在”，还会在模型或候选覆盖面明显变化时重建候选集。
- 3LCache 的候选覆盖更像在线采样系统。`sample_boundary`、`sampling_lru`、`reserved_space` 会随 eviction 分布调整；新对象先累计到 `new_obj_keys/new_obj_size`，再由 `quick_demotion()` 控制是否进入下一轮候选。LOH 当前 pool 只是在一次完整评分后复用同一批已评分对象，`refill` 也只是同源前沿补位，不能等价覆盖当前 cache 的全局最差对象。
- 3LCache 的预测目标和池化策略绑定得更紧：BMR/OMR 目标在运行开始前固定，候选生成和 LightGBM 特征都服务这个目标。LOH v7 虽然按 target 选择特征配置，但 pool 复用的是旧 `compare_score`，当 cache 组成和局部访问模式变化时，旧分数仍可能有效却不再代表“当前最该驱逐”的对象。
- LOH 的候选分数经常在多个对象之间很接近，尤其 recency/frequency/size 复合特征会随短期访问快速翻转。这样 next-K 快照很容易从“省计算”变成“放大旧排序偏差”；大 pool 的吞吐提升越高，这种偏差累计越明显。

所以本轮结果不是说明 pool 方向错了，而是说明 LOH 不能直接照搬 3LCache 的收益假设。3LCache 的 pool 是自适应候选生成系统的一部分；LOH 当前 pool 是对 per-eviction fresh scoring 的加速层。要让 LOH 接近 3LCache 的稳定性，下一步更应该做事件驱动重建、候选覆盖自适应和轻量 warmup allowlist，而不是单纯继续增大 pool。

### 如何借鉴到 LOH

LOH 不需要照搬 3LCache 的 LightGBM；更适合借鉴的是它的候选池维护方式，把 `evict_queue` 从“静态 next-K 队列”升级成“可重建的候选缓存”。建议按以下顺序做：

1. 先把 pool 的健康指标补齐。每轮记录 pooled pop 有效率、失效率、shadow audit bad rate、队列平均 age、候选分数 margin、候选来源分布和新对象累计大小。没有这些信号，自动策略只能盲调 pool size。
2. 做事件驱动重建，而不是只靠固定 request-age。命中对象删除对应队列项已经有了，下一步应在权重 epoch 变化、shadow bad rate 升高、队列有效率过低、来源前沿耗尽、new object 压力超过阈值时直接重建 pool。
3. 把 `refill` 从“同源补一个”扩展成“来源预算自适应”。保留 recency、frequency、size、IRT/random 等来源，但用最近 eviction 成功率和 audit 结果调整每个来源的候选预算；某个来源频繁在 audit 中输给 fresh candidate，就降低它的预算或缩短它的 TTL。
4. 新对象不要即时无条件搅动旧 pool。借鉴 3LCache 的 `new_obj_keys/new_obj_size` 思路，先累计新对象压力；只有当新对象总大小超过 cache 的小比例阈值，或 pooled 候选持续输给 fresh 新对象候选时，才把新对象批量纳入下一轮重建。
5. 引入轻量 warmup allowlist。warmup 后根据 `one_hit`、eviction rate、score margin、候选有效率和最初几次 shadow audit 判断是否启用 pool、启用多大 pool、是否启用 refill。这样不是 quality-window guard，而是 pool 自身可复用性判断。
6. 消费策略改为低水位重建。当前队列耗尽才回到完整评分；可以在未消费队列低于阈值时提前重建，把“最后几个老候选”替换掉，减少大 pool 尾部过期问题。
7. 默认策略应保守：生产默认只允许小 pool，例如 `pool4_refill_age0_newobj_guard1` 这一类；大 pool 只在 warmup 和在线 audit 都证明 score margin 稳定、valid pop 高、bad audit 低时开启。

这样借鉴后的 LOH pool 仍然使用 LOH 自己的评分函数和 v7 target 配置，但候选缓存的生命周期会更接近 3LCache：由事件和在线信号控制，而不是把一次完整评分的排序结果跨请求硬复用到底。

当前已把第一版借鉴实现做成可切换开关，默认不改变旧实验行为：

- `LOH_EVICT_POOL_ADAPTIVE=1`：组合开关，开启事件重建、guard rebuild-only、新对象 staging，并在未显式设置时给低水位重建一个保守默认值。
- `LOH_EVICT_POOL_EVENT_REBUILD=1`：pool 健康窗口低于有效率阈值时只清空队列，让下一次 eviction 走 fresh scoring 重建 pool，而不是永久关闭 pool。
- `LOH_EVICT_POOL_HEALTH_LOG=1`：输出 `[LOH POOL_HEALTH]` 窗口日志和运行结束摘要，包括 pooled hit、invalid/stale/null、event rebuild、source pop/bad、平均 score margin。
- `LOH_EVICT_POOL_HEALTH_WINDOW` 与 `LOH_EVICT_POOL_MIN_VALID_RATE`：控制健康窗口大小和最低有效 pooled pop 比例，默认分别是 `256` 和 `0.60`。
- `LOH_EVICT_POOL_GUARD_REBUILD_ONLY=1`：guard bad rate 达阈值时只重建 pool 并清零 audit 计数；默认仍保留旧行为，即触发后永久 disabled。
- `LOH_EVICT_POOL_LOW_WATERMARK=N`：未消费队列长度低于等于 `N` 时提前清池，让后续 eviction 重新 full scoring，减少大 pool 尾部过期候选。
- `LOH_EVICT_POOL_NEWOBJ_STAGING=1`：新对象不再即时插入旧 pool，而是累计新对象字节压力；超过 `LOH_EVICT_POOL_NEWOBJ_PRESSURE_PCT` 指定的 cache 比例后清池重建。默认压力阈值是 `0.005`。
- `LOH_EVICT_POOL_WARMUP_ALLOWLIST=1`：用户请求开启 pool 时先延迟到 warmup 诊断之后，再按 `LOH_EVICT_POOL_WARMUP_MAX_BATCH` 和 `LOH_EVICT_POOL_WARMUP_MAX_ONE_HIT` 判断是否恢复 pool。默认 max batch 是 `8`，max one-hit 是 `1.0`。

## 已实现的 LOH guard 策略

`LOH.c` 已增加 `LOH_EVICT_POOL_GUARD`，只控制 pool，不直接改变现有 v7 特征选择。guard 本身不是 `LOH_EVICT_POOL_AUTO`，也不做 MR/BMR quality-window 归因；新增的 warmup allowlist 是独立开关。所有配置只要手动启用 pool 与 guard，就按同一套 shadow audit 规则运行。

1. 硬门禁：默认不开 guard；需要显式设置 `LOH_EVICT_POOL_ENABLE=1` 与 `LOH_EVICT_POOL_GUARD=1`。
2. 抽样审计：默认每 `256` 次 pooled pop 审计一次，可用 `LOH_EVICT_POOL_GUARD_INTERVAL` 调整。
3. 判定阈值：默认至少 `8` 个 audit 样本后判断，bad 比例阈值默认 `0.25`，对应 `LOH_EVICT_POOL_GUARD_MIN_SAMPLES` 和 `LOH_EVICT_POOL_GUARD_BAD_RATE`。
4. 容忍区间：默认 `LOH_EVICT_POOL_GUARD_REL_EPS=0.01`、`LOH_EVICT_POOL_GUARD_ABS_EPS=0.0`，避免很小的分数差触发回退。
5. rollback：触发后输出 `[LOH POOL_GUARD] disabled ...`，清空队列并关闭跨请求 pool，本次运行不再重新启用。
6. 收尾日志：运行结束时输出 `[LOH POOL_GUARD] summary ...`，记录 audit 次数、bad 次数和是否触发关闭。

可以借鉴 3LCache 的事件失效思路：命中则删预测、权重 epoch 变化则清池、驱逐则删对应对象、新对象进入时记录下来。但这仍不能保证 pool 一定不退化，因为它只解决“对象还在不在、元数据有没有明显过期”，不能保证旧候选池相对于当前 cache 状态仍然包含真正最差的对象。

新对象直接进入 LOH pool 也要谨慎。当前实现采用保守边界插入：用当前权重和同一套 `compare_key` 先给新对象打分；只有当它比当前 pool 边界更差，才放入 pool；入池时同样保存 `last_access_counter`、`access_count`、weight epoch 和入池时间。否则，大量新对象会把旧 pool 冲散，或者在有短期局部性的 trace 上过早驱逐刚进入 cache 的对象，MR/BMR 仍可能退化。

所以这些规则可以作为 guard 的基础，但真正触发回退的信号只来自 shadow-rescore audit。要接近“不退化”，仍需要周期性完整重评分抽样，确认 pooled 候选在当前候选集中仍然足够差；MR/BMR 窗口只用于离线分析结果，不作为在线 guard 的触发条件。

初始阈值建议保守：shadow audit 至少积累一批样本后再判断；一旦触发输出 `[LOH POOL_GUARD]` 日志，记录 audit 次数、bad 次数、bad rate、queued/fresh 对象与分数。后续如果要更激进，再增加 cooldown 后重新试探，而不是第一版就来回开关。

## 脚本

- 串行与初始中等规模对比：`tmp/20260511-loh-evict-pool/run_medium_bmr_compare.sh`
- 并行补跑缺失 case：`tmp/20260511-loh-evict-pool/run_medium_bmr_parallel_missing.sh`
- `tencentBlock_3879 f100_ns` 的 v7 修正补跑：`tmp/20260511-loh-evict-pool/run_medium_bmr_parallel_v7_extra.sh`
- `alibabaBlock_746 f101_orig` 调参：`tmp/20260511-loh-evict-pool/run_alibaba746_f101_tune_parallel.sh`
- `tencentBlock_3879 f100_ns` 调参：`tmp/20260511-loh-evict-pool/run_tencent3879_f100_tune_parallel.py`
- 最终聚合：`tmp/20260511-loh-evict-pool/aggregate_medium_bmr_parallel.py`
- 新对象边界插入 + age0 重跑：`tmp/20260512-loh-pool-newobj/run_newobj_age0_matrix.py`
- refill 反例矩阵：`tmp/20260512-loh-pool-refill/run_refill_matrix.py`
- `f101_orig/f100_orig` 退化验证矩阵：`tmp/20260512-loh-pool-orig/run_orig_matrix.py`
- 三条关键 trace 的 `pool128_age0_newobj` 对比矩阵：`tmp/20260512-loh-pool-keytraces/run_keytrace_pool_matrix.py`

## 结果文件

- 合并明细：`tmp/20260511-loh-evict-pool/medium_bmr_parallel_combined_results.csv`
- 三条关键 trace 对比明细：`tmp/20260512-loh-pool-keytraces/keytrace_pool_results.csv`
- 三条关键 trace 相对变化汇总：`tmp/20260512-loh-pool-keytraces/keytrace_pool_summary.csv`
- 选中 case 汇总：`tmp/20260511-loh-evict-pool/medium_bmr_parallel_selected_summary.csv`
- 选中 case 平均值：`tmp/20260511-loh-evict-pool/medium_bmr_parallel_selected_averages.csv`
- `alibabaBlock_746 f101_orig` 调参汇总：`tmp/20260511-loh-evict-pool/alibaba746_f101_tune_summary.csv`
- `tencentBlock_3879 f100_ns` 调参汇总：`tmp/20260511-loh-evict-pool/tencent3879_f100_tune_summary.csv`
- `age0 + newobj` 补测明细：`tmp/20260512-loh-pool-newobj/age0_matrix_results.csv`
- `age0 + newobj` 补测选中策略：`tmp/20260512-loh-pool-newobj/age0_matrix_selected_summary.csv`
- `refill` 补测明细：`tmp/20260512-loh-pool-refill/refill_matrix_results.csv`
- `refill` 补测选中策略：`tmp/20260512-loh-pool-refill/refill_matrix_selected_summary.csv`
- `f101_orig/f100_orig` 补测明细：`tmp/20260512-loh-pool-orig/orig_matrix_results.csv`
- `f101_orig/f100_orig` 补测选中策略：`tmp/20260512-loh-pool-orig/orig_matrix_selected_summary.csv`
- `f101_orig/f100_orig` 绝对与相对变化表：`tmp/20260512-loh-pool-orig/logs/orig_matrix_delta_relative_table.log`

## `f101_orig/f100_orig` 补测结论

本轮补测 6 个 trace/config，每个配置测 `base` 与 2 个 `age0_newobj` pool 档位，共 18 个 case，全部 `ok`。12 个 pool 变体中只有 2 个满足严格 MR/BMR 双不退，因此结论不是“全都退化”，而是 `orig` 系配置不能默认打开 pool，必须依赖在线 guard、allowlist 或同 trace A/B。

| Trace | 配置 | pool 变体 | MR 变化 | MR 相对 base | BMR 变化 | BMR 相对 base | 吞吐加速 | 严格双不退 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| alibabaBlock_3 | f100_orig | pool128_age0_newobj | +0.000549 | +0.107% | -0.009367 | -6.373% | 15.181303 | False |
| alibabaBlock_3 | f100_orig | pool8_age0_newobj | -0.003106 | -0.605% | +0.002742 | +1.865% | 4.849774 | False |
| alibabaBlock_746 | f101_orig | pool2_age0_newobj | +0.000748 | +0.115% | -0.006318 | -0.750% | 2.069870 | False |
| alibabaBlock_746 | f101_orig | pool8_age0_newobj | -0.006527 | -1.005% | -0.004710 | -0.559% | 6.875407 | True |
| tencentBlock_1069 | f100_orig | pool128_age0_newobj | +0.015701 | +5.218% | -0.004141 | -0.936% | 13.631769 | False |
| tencentBlock_1069 | f100_orig | pool8_age0_newobj | -0.001007 | -0.335% | -0.008166 | -1.845% | 5.703928 | True |
| tencentBlock_12654 | f101_orig | pool2_age0_newobj | -0.003354 | -2.322% | +0.001249 | +4.327% | 1.333333 | False |
| tencentBlock_12654 | f101_orig | pool8_age0_newobj | +0.000580 | +0.402% | -0.003207 | -11.111% | 3.272727 | False |
| tencentBlock_3879 | f100_orig | pool128_age0_newobj | +0.030704 | +10.606% | -0.022741 | -8.141% | 6.133333 | False |
| tencentBlock_3879 | f100_orig | pool8_age0_newobj | +0.002728 | +0.942% | -0.011952 | -4.279% | 2.866332 | False |
| tencentBlock_3879 | f101_orig | pool2_age0_newobj | -0.001476 | -0.582% | +0.055407 | +18.922% | 0.936793 | False |
| tencentBlock_3879 | f101_orig | pool8_age0_newobj | +0.005629 | +2.221% | +0.025781 | +8.804% | 2.143750 | False |

按 trace/config 选最优非退化 pool 后，`f101_orig` 只有 `alibabaBlock_746 pool8_age0_newobj` 通过，`f100_orig` 只有 `tencentBlock_1069 pool8_age0_newobj` 通过；其余 4 个 trace/config 均回退 `base`。因此最终自动策略仍保持 conservative：`orig` 系默认 off，`f100_ns` 才进入 pool 试探。

## 最终选择策略

| Trace | 配置 | 选中变体 | MR 变化 | BMR 变化 | 吞吐加速 |
|---|---|---:|---:|---:|---:|
| alibabaBlock_3 | f100_ns | pool128_age0_newobj | -0.001345 | -0.001809 | 13.250794 |
| alibabaBlock_507 | f100_ns | pool128_age0_newobj | -0.001718 | -0.002021 | 8.431818 |
| alibabaBlock_746 | f101_orig | base | 0.000000 | 0.000000 | 1.000000 |
| tencentBlock_1069 | f100_ns | pool8_age0_newobj | -0.000621 | -0.000587 | 6.079764 |
| tencentBlock_3879 | f100_ns | pool128_age0_newobj | -0.090843 | -0.078158 | 14.241685 |

5 个选中 case 的最终平均：

- 平均 MR 变化: `-0.018905400`
- 平均 BMR 变化: `-0.016515000`
- 平均吞吐加速: `8.600812x`
- `all_quality_ok=True`
- `average_ok=True`

## 20260512 v7 全量单 seed 矩阵

用户将三 seed 计划改为“每个版本只跑一次”后，本轮最终按 `seed=101` 完成 v7 全量矩阵。范围如下：

- Trace：`alibabaBlock_3`、`alibabaBlock_507`、`alibabaBlock_746`、`meta_reag`、`wiki_2019t`、`tencentBlock_1063`、`tencentBlock_1069`、`tencentBlock_12654`、`tencentBlock_3879`。
- 每个 trace 跑两个 v7 目标配置：MR 固定 `f001_orig`；BMR 按 `one_hit <= 0.72` 选择 `f100_ns`，否则 `f101_orig`。
- 每个目标配置跑 29 个版本：`base_no_pool`，以及 `pool{2,4,8,16,32,64,128}` 的 `age0_newobj`、`refill_age0_newobj`，各自再分 `guard0/guard1`。
- 共 `9 traces * 2 target cfg * 29 versions * 1 seed = 522` case，全部 full trace（`--num-req=0`）。
- 运行复用了已完成结果：旧三 seed 目录中的 `seed101` 结果 `132` 条、当前单 seed 目录缓存 `18` 条，本次补跑 `372` 条。
- Driver 最终退出码为 `0`，最终日志为 `[done] cases=522 ok=522 failed=0`。

结果文件：

- 明细：`tmp/20260512-loh-v7-full-single-seed/v7_full_seeded_results.csv`，其中第 3、4、5 列分别是 `mr`、`bmr`、`mqps`。
- 分组汇总：`tmp/20260512-loh-v7-full-single-seed/v7_full_seeded_summary.csv`
- 所有版本平均表：`tmp/20260512-loh-v7-full-single-seed/v7_full_variant_average_table.csv`，其中第 3、4、5 列分别是 `avg_mr`、`avg_bmr`、`avg_mqps`。
- 综合排序日志：`tmp/20260512-loh-v7-full-single-seed/logs/final_variant_quality_speed.log`
- 每组最优日志：`tmp/20260512-loh-v7-full-single-seed/logs/final_variant_ranking.log`

本节的综合指标按 18 个 `trace + target + cfg` 组归一化：MR 目标只看 MR，BMR 目标只看 BMR。`avg target metric` 是按目标列取值后的原始均值；`avg target Δ`、`median target Δ`、`worst target Δ` 均为相对同组 `base_no_pool` 的百分比变化，负数表示更好。`avg speedup` 为 MQPS 相对同组 `base_no_pool` 的平均加速。下表按 `avg target Δ` 从好到差排序，`avg MR/BMR/MQPS` 仍保留为 raw average 便于横向检查。

| 固定版本 | n | avg MR | avg BMR | avg MQPS | avg target metric | avg target Δ | median target Δ | worst target Δ | 不退化组数 | avg speedup | guard disabled |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `pool4_age0_newobj_guard1` | 18 | 0.275367 | 0.326278 | 0.230556 | 0.294207 | -1.9030% | -0.1281% | +15.3076% | 13/18 | 1.240x | 88.9% |
| `pool32_age0_newobj_guard1` | 18 | 0.278465 | 0.317733 | 0.248333 | 0.291677 | -1.8095% | -0.3205% | +8.8746% | 13/18 | 0.965x | 100.0% |
| `pool2_refill_age0_newobj_guard0` | 18 | 0.275057 | 0.325453 | 0.265000 | 0.293391 | -1.7610% | -0.6176% | +13.2031% | 12/18 | 1.378x | - |
| `pool4_refill_age0_newobj_guard0` | 18 | 0.277221 | 0.323530 | 0.387222 | 0.293028 | -1.7431% | -0.3500% | +4.2249% | 11/18 | 2.761x | - |
| `pool8_refill_age0_newobj_guard1` | 18 | 0.276692 | 0.321976 | 0.250556 | 0.293303 | -1.3429% | -0.1525% | +7.0989% | 11/18 | 1.039x | 100.0% |
| `pool4_refill_age0_newobj_guard1` | 18 | 0.276925 | 0.329571 | 0.241667 | 0.292959 | -1.3191% | -0.4152% | +3.6758% | 11/18 | 1.490x | 94.4% |
| `pool2_refill_age0_newobj_guard1` | 18 | 0.278295 | 0.336031 | 0.208889 | 0.296768 | -1.2122% | -0.1353% | +12.7127% | 10/18 | 1.123x | 72.2% |
| `pool8_age0_newobj_guard0` | 18 | 0.278309 | 0.321908 | 0.467778 | 0.294019 | -0.6382% | -0.0631% | +5.0687% | 10/18 | 3.312x | - |
| `pool8_refill_age0_newobj_guard0` | 18 | 0.279630 | 0.322383 | 0.518333 | 0.295142 | -0.0785% | +0.2338% | +7.8547% | 7/18 | 4.214x | - |
| `base_no_pool` | 18 | 0.277002 | 0.322294 | 0.257778 | 0.292293 | +0.0000% | +0.0000% | +0.0000% | 18/18 | 1.000x | - |
| `pool4_age0_newobj_guard0` | 18 | 0.281732 | 0.336918 | 0.324444 | 0.299268 | +0.2929% | -0.1533% | +12.5260% | 10/18 | 2.075x | - |
| `pool32_refill_age0_newobj_guard1` | 18 | 0.279103 | 0.324850 | 0.237778 | 0.293753 | +0.3078% | +0.1891% | +20.6447% | 6/18 | 0.940x | 100.0% |
| `pool16_age0_newobj_guard1` | 18 | 0.283642 | 0.336049 | 0.228889 | 0.294707 | +0.5614% | -0.1631% | +26.3030% | 10/18 | 0.976x | 100.0% |
| `pool2_age0_newobj_guard1` | 18 | 0.278349 | 0.330148 | 0.233889 | 0.297548 | +0.7096% | -0.1594% | +22.3808% | 11/18 | 1.107x | 77.8% |
| `pool64_age0_newobj_guard1` | 18 | 0.280748 | 0.322161 | 0.230556 | 0.295382 | +0.7808% | +0.0313% | +30.1752% | 8/18 | 0.859x | 100.0% |
| `pool2_age0_newobj_guard0` | 18 | 0.280724 | 0.351136 | 0.251667 | 0.299729 | +1.3661% | -0.2068% | +48.3360% | 12/18 | 1.372x | - |
| `pool128_age0_newobj_guard1` | 18 | 0.280444 | 0.331473 | 0.178333 | 0.293041 | +2.1802% | +0.2717% | +30.8000% | 6/18 | 0.648x | 100.0% |
| `pool16_refill_age0_newobj_guard0` | 18 | 0.283652 | 0.322950 | 0.636667 | 0.295876 | +2.7372% | +0.6266% | +42.7852% | 6/18 | 5.770x | - |
| `pool64_refill_age0_newobj_guard1` | 18 | 0.279393 | 0.322447 | 0.232222 | 0.293841 | +2.7523% | +0.1864% | +28.9469% | 7/18 | 0.904x | 100.0% |
| `pool8_age0_newobj_guard1` | 18 | 0.283141 | 0.352220 | 0.235556 | 0.300528 | +3.1175% | +0.0015% | +55.6949% | 9/18 | 1.236x | 94.4% |
| `pool128_refill_age0_newobj_guard1` | 18 | 0.281316 | 0.328222 | 0.209444 | 0.294619 | +3.7915% | +0.2574% | +39.6817% | 6/18 | 0.696x | 100.0% |
| `pool16_age0_newobj_guard0` | 18 | 0.286228 | 0.331367 | 0.587778 | 0.299420 | +6.9359% | +0.4324% | +52.1286% | 8/18 | 5.127x | - |
| `pool16_refill_age0_newobj_guard1` | 18 | 0.289186 | 0.357310 | 0.229444 | 0.304809 | +6.9811% | +0.1847% | +72.3469% | 6/18 | 0.940x | 100.0% |
| `pool32_age0_newobj_guard0` | 18 | 0.290710 | 0.322455 | 0.696667 | 0.302868 | +22.6240% | +0.7341% | +196.7177% | 7/18 | 6.450x | - |
| `pool32_refill_age0_newobj_guard0` | 18 | 0.295507 | 0.323128 | 0.746667 | 0.306330 | +40.1247% | +0.7676% | +320.8866% | 6/18 | 7.241x | - |
| `pool64_age0_newobj_guard0` | 18 | 0.318291 | 0.361893 | 0.726111 | 0.326269 | +70.0808% | +3.0655% | +719.9600% | 5/18 | 7.362x | - |
| `pool64_refill_age0_newobj_guard0` | 18 | 0.315603 | 0.335835 | 0.733889 | 0.323592 | +76.9608% | +2.5429% | +724.8229% | 4/18 | 7.851x | - |
| `pool128_age0_newobj_guard0` | 18 | 0.327982 | 0.343075 | 0.750556 | 0.333616 | +94.4002% | +3.2681% | +1014.7520% | 5/18 | 8.190x | - |
| `pool128_refill_age0_newobj_guard0` | 18 | 0.330210 | 0.351298 | 0.801667 | 0.333992 | +98.7608% | +3.4006% | +990.3894% | 3/18 | 9.085x | - |

综合结论：

- 如果要求严格“所有 trace/target 都不退化”，唯一通过的是 `base_no_pool`；任何固定 pool 版本都有至少 5 个组在目标指标上退化。因此不能把 pool 当成无条件默认打开项。
- 如果只看 target-aware 平均质量，最优是 `pool4_age0_newobj_guard1`：平均目标指标改善 `1.9030%`，13/18 组不退化，平均吞吐 `1.240x`。但它的最差退化达到 `15.3076%`，说明均值好但尾部风险仍偏大。
- 如果允许在线 guard 参与回退，并希望有一个固定的 pool 默认试探配置，当前最均衡的是 `pool4_refill_age0_newobj_guard1`。它的平均目标指标改善 `1.3191%`，中位数改善 `0.4152%`，观测到的最差退化是 `3.6758%`，平均吞吐 `1.490x`。它不是平均质量最优，但在 guard-on 且仍有吞吐收益的候选里，最差退化最小，因此是当前最适合作为默认候选的配置。
- 如果是离线实验、允许不用 guard 并接受少量分组退化，`pool4_refill_age0_newobj_guard0` 是更强的吞吐/质量折中：平均目标指标改善 `1.7431%`，平均吞吐 `2.761x`，最差退化 `4.2249%`。但它没有在线回退，不建议作为生产默认。
- 不建议默认使用 `pool64/128 guard0`。它们平均吞吐高，但目标指标最差退化可达数倍到十倍级，说明大 pool 在部分 trace 上仍会显著过期。

本轮 guard 行为也很明确：252 个 guard case 中有 239 个最终触发 disabled，说明 shadow audit 多数时候能识别 pool 候选过期并关闭 pool；但这也意味着大多数 guard-on 配置的吞吐收益会被回退抵消。后续若想提高 guard-on 的吞吐，需要优化 guard 的开关策略，而不是简单增大 pool。

按每个 `trace + target + cfg` 单独选择时，最优版本如下：

| Trace | Target | Cfg | Metric | Base | 最优版本 | 最优值 | 相对 base |
| --- | --- | --- | --- | ---: | --- | ---: | ---: |
| alibabaBlock_3 | bmr | f100_ns | BMR | 0.136084 | `pool2_age0_newobj_guard0` | 0.134926 | -0.851% |
| alibabaBlock_3 | mr | f001_orig | MR | 0.512249 | `pool64_refill_age0_newobj_guard0` | 0.510537 | -0.334% |
| alibabaBlock_507 | bmr | f101_orig | BMR | 0.732821 | `pool32_age0_newobj_guard1` | 0.732290 | -0.072% |
| alibabaBlock_507 | mr | f001_orig | MR | 0.166331 | `pool2_age0_newobj_guard1` | 0.161992 | -2.609% |
| alibabaBlock_746 | bmr | f101_orig | BMR | 0.810248 | `pool4_age0_newobj_guard1` | 0.809210 | -0.128% |
| alibabaBlock_746 | mr | f001_orig | MR | 0.639254 | `pool2_refill_age0_newobj_guard0` | 0.635341 | -0.612% |
| meta_reag | bmr | f101_orig | BMR | 0.158150 | `pool2_age0_newobj_guard1` | 0.153566 | -2.899% |
| meta_reag | mr | f001_orig | MR | 0.270199 | `pool2_age0_newobj_guard1` | 0.269351 | -0.314% |
| tencentBlock_1063 | bmr | f101_orig | BMR | 0.025004 | `pool2_refill_age0_newobj_guard1` | 0.021247 | -15.026% |
| tencentBlock_1063 | mr | f001_orig | MR | 0.016513 | `pool2_age0_newobj_guard1` | 0.013810 | -16.369% |
| tencentBlock_1069 | bmr | f100_ns | BMR | 0.433551 | `pool8_refill_age0_newobj_guard1` | 0.432174 | -0.318% |
| tencentBlock_1069 | mr | f001_orig | MR | 0.298506 | `pool32_age0_newobj_guard1` | 0.286417 | -4.050% |
| tencentBlock_12654 | bmr | f101_orig | BMR | 0.029981 | `pool128_age0_newobj_guard1` | 0.022134 | -26.173% |
| tencentBlock_12654 | mr | f001_orig | MR | 0.153610 | `pool64_refill_age0_newobj_guard0` | 0.142671 | -7.121% |
| tencentBlock_3879 | bmr | f101_orig | BMR | 0.305064 | `pool32_refill_age0_newobj_guard0` | 0.241269 | -20.912% |
| tencentBlock_3879 | mr | f001_orig | MR | 0.255293 | `pool2_refill_age0_newobj_guard0` | 0.251761 | -1.384% |
| wiki_2019t | bmr | f101_orig | BMR | 0.138841 | `pool32_refill_age0_newobj_guard0` | 0.137081 | -1.268% |
| wiki_2019t | mr | f001_orig | MR | 0.179566 | `pool2_refill_age0_newobj_guard1` | 0.179247 | -0.178% |

## 备注

- `tencentBlock_3879` 的早期探索曾记录 `one_hit=0.4927` 并按 `f100_ns` 补跑；本轮 v7 全量矩阵使用的 warmup 分流是 `one_hit=0.8494`，因此 BMR 目标进入 `f101_orig`。复现最终矩阵时以本轮 `f101_orig` 结果为准。
- `alibabaBlock_746 f101_orig` 仍然对 pool 敏感。单组最优可以找到小 pool 改善，但固定版本里仍不能保证所有 trace/target 不退化。
- `tencentBlock_1069 f100_ns` 仍是敏感 case：大 pool 不适合直接开；本轮 BMR 单组最优变为 `pool8_refill_age0_newobj_guard1`，MR 单组最优为 `pool32_age0_newobj_guard1`，二者都依赖 guard 回退。
- `LOH_EVICT_POOL_REFILL=1` 的结论从“不要默认大 pool refill”细化为“小 pool refill 可以作为折中”。`pool4_refill_age0_newobj_guard1` 是本轮 guard-on 固定配置里质量风险和吞吐收益最均衡的版本；但 `pool64/128 refill guard0` 仍然有严重退化风险。
- 本轮是单 seed 结论，用于选择下一步默认候选足够；如果要把 `pool4_refill_age0_newobj_guard1` 写成代码默认值，建议再做至少 3 seed 复验，并重点看最差退化组是否稳定。
