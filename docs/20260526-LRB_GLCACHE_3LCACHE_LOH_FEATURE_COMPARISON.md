# LRB / GLCache / 3LCache / LOH 特征对比

本文对比 `LRB`、`GLCache`、`3LCache` 和 `LOH` 在代码中实际使用的特征。核心结论是：前三者的学习目标主要是直接预测对象或段的未来效用，而 LOH 更像是在候选对象集合之上学习一组 scoring 权重；因此 LOH 的特征不仅包含对象级统计，还包含候选集合与窗口级状态。

## 1. 总览

| 算法 | 特征粒度 | 模型输入 | 模型/策略输出 | 训练标签或反馈 | 主要用途 |
| --- | --- | --- | --- | --- | --- |
| LRB | object-level | 单个对象的 age、历史复用间隔、size、EDC 等稀疏特征 | 预测未来复用间隔 `log1p(future_interval)` | 采样对象在未来窗口内/外再次访问形成的 delayed label | 直接给对象排序，选择 predicted reuse 最远/效用最低者淘汰 |
| 3LCache | object-level | 单个对象的 age、最近 3 个 past distance、size、frequency | 预测未来复用间隔 `log1p(future_interval)`，再按 OMR/BMR 改写 score | 对采样对象在未来访问时得到的 future distance | 对采样候选对象做 LightGBM 预测，选择 OMR/BMR 目标下最差者淘汰 |
| GLCache | segment-level | segment age、平均对象大小、hit/active 数、创建时 req_rate/miss_ratio 等 | 预测 segment utility | snapshot segment 后，后续访问累计 utility，或 oracle utility | 排序 segment，选择低 utility segment 进行淘汰/合并 |
| LOH | candidate/window-level + object-level | 对象基础特征、候选集合统计、Hit/Miss/Cache/TopK/Request 窗口状态 | 7 维 scoring 权重或固定配置下的 score | 窗口级 miss/byte miss reward，CMA-ES/RL/GBM 更新权重 | 在候选生成与 scoring 中间层上适配 workload，而不是直接预测单对象 future reuse |

## 2. LRB 使用的特征

LRB 的特征在 [libCacheSim/cache/eviction/LRB/lrb.h](../libCacheSim/cache/eviction/LRB/lrb.h) 和 [libCacheSim/cache/eviction/LRB/lrb.cpp](../libCacheSim/cache/eviction/LRB/lrb.cpp) 中构造。它使用 LightGBM regression，训练标签是 `log1p(future_interval)`。

LRB 的特征向量维度由代码设为：

```text
n_feature = max_n_past_timestamps + n_extra_fields + 2 + n_edc_feature
          = 32 + 0 + 2 + 10
          = 44
```

实际字段包括：

| 特征 | 代码含义 | 说明 |
| --- | --- | --- |
| `sample_timestamp - meta._past_timestamp` | waiting time / age | 当前采样时刻距离对象上次访问的间隔 |
| 最近最多 31 个 `_past_distances` | past reuse distances | 对象历史复用间隔序列 |
| `meta._size` | object size | 对象大小 |
| `extra_features` | categorical feature | 当前接口里 `n_extra_fields = 0`，实际没有启用 |
| `n_within` | recent reuse count within memory window | 累计 past distances 后仍在 `memory_window` 内的次数 |
| 10 个 EDC 特征 | exponentially decayed counters | `n_edc_feature = 10`，窗口为 `2^(10+i)`，表示不同时间尺度上的衰减访问历史 |

LRB 的关键点是：特征完全围绕“这个对象未来多久会再被访问”构造。它还维护 in-cache 与 out-cache metadata，并对采样对象延迟补标签。BMR/OMR 的差异不是改变输入特征，而是在排序时改变 score 解释：object-miss-ratio 模式下会把 predicted score 乘以 size，从而改变淘汰排序。

## 3. 3LCache 使用的特征

3LCache 的特征在 [libCacheSim/cache/eviction/3LCache/ThreeLCache.hpp](../libCacheSim/cache/eviction/3LCache/ThreeLCache.hpp) 与 [libCacheSim/cache/eviction/3LCache/ThreeLCache.cpp](../libCacheSim/cache/eviction/3LCache/ThreeLCache.cpp) 中构造。它同样使用 LightGBM regression，标签也是 `log1p(future_interval)`。

3LCache 的特征维度是：

```text
n_feature = max_n_past_timestamps + 2
          = 4 + 2
          = 6
```

实际字段包括：

| 特征 | 代码含义 | 说明 |
| --- | --- | --- |
| `sample_timestamp - meta._past_timestamp` / `current_seq - meta._past_timestamp` | age | 训练和推理时对象距离上次访问的间隔 |
| 最近最多 3 个 `_past_distances` | past reuse distances | 比 LRB 更短的历史复用间隔序列 |
| `meta._size` | object size | 对象大小 |
| `meta._freq` | frequency | 该对象被观察到的访问次数 |

3LCache 与 LRB 的主要差别是特征更短、更直接：LRB 有长历史和 EDC，3LCache 只有 6 维对象历史特征。3LCache 的目标分为 `ThreeLCache-OMR` 与 `ThreeLCache-BMR`：

- `byte-miss-ratio` 下，预测 reuse distance 后直接用 reuse time 排序。
- `object-miss-ratio` 下，代码会把预测距离按 size 调整，形成不同的淘汰分数。

因此 3LCache 的 OMR/BMR 更像是同一组对象特征在不同目标下的 score 变换，而不是两套完全不同的输入特征。

## 4. GLCache 使用的特征

GLCache 的特征在 [libCacheSim/cache/eviction/GLCache/dataPrep.c](../libCacheSim/cache/eviction/GLCache/dataPrep.c)、[libCacheSim/cache/eviction/GLCache/segment.c](../libCacheSim/cache/eviction/GLCache/segment.c)、[libCacheSim/cache/eviction/GLCache/init.c](../libCacheSim/cache/eviction/GLCache/init.c)、[libCacheSim/cache/eviction/GLCache/const.h](../libCacheSim/cache/eviction/GLCache/const.h) 中构造。它不是对象级预测器，而是 segment-level 学习器。

当前代码里：

```text
N_FEATURE_NORMAL = 6
N_FEATURE_TIME_WINDOW = 0
learner.n_feature = N_FEATURE_TIME_WINDOW * 3 + N_FEATURE_NORMAL = 6
```

`prepare_one_row()` 写入的 6 个常规特征是：

| 特征 | 代码字段 | 说明 |
| --- | --- | --- |
| segment age | `curr_rtime - curr_seg->create_rtime` | 段从创建到当前的真实时间年龄 |
| mean object size | `curr_seg->n_byte / curr_seg->n_obj` | 段内平均对象大小 |
| segment hit count | `curr_seg->n_hit` | 段被命中的次数 |
| active object count | `curr_seg->n_active` | 段内至少被命中过的 active 对象数 |
| request rate at creation/update | `curr_seg->req_rate` | 段创建时记录的请求速率 |
| miss ratio at creation/update | `curr_seg->miss_ratio` | 段创建时记录的 miss ratio |

代码还保留了窗口 hit 特征：`n_hit_per_min`、`n_hit_per_ten_min`、`n_hit_per_hour`，但当前 `N_FEATURE_TIME_WINDOW = 0`，所以这些窗口特征在本仓库当前配置下不会进入实际模型输入。

GLCache 的标签不是单对象 future interval，而是 segment utility。训练数据通过 snapshot segment 生成，后续请求会累计：

```text
train_utility += 1.0e6 / age / obj_size
```

也就是说 GLCache 学的是“这个 segment 未来保留价值高不高”，推理时对 segment 排序，低 utility 的段更适合被淘汰或合并。这和 LRB/3LCache 的 object-level reuse prediction 完全不同。

## 5. LOH 使用的特征

LOH 的核心特征在 [libCacheSim/cache/eviction/LOH.c](../libCacheSim/cache/eviction/LOH.c) 中。它分成两层：

1. 单对象基础特征，用于候选对象 scoring。
2. 窗口/候选集合状态，用于 RL/CMA-ES/GBM actor 选择 scoring 权重。

### 5.1 对象基础特征

`FEATURE_DIM = 6`，`calculate_object_features()` 计算：

| 维度 | 特征 | 代码含义 |
| --- | --- | --- |
| 0 | recency | 当前时间距离对象上次访问的间隔 |
| 1 | frequency | 对象访问次数 |
| 2 | size | 对象大小 |
| 3 | latest IRT | 最近一次 inter-reference time |
| 4 | second IRT | 倒数第二次 inter-reference time |
| 5 | third IRT | 倒数第三次 inter-reference time |

这些基础特征可经过 `log1p`、reciprocal、normalization 等变换。

### 5.2 LOH 的 scoring 特征

LOH 的 `WEIGHT_DIM = 7`。默认 compound scoring 不直接使用 IRT，而是把 recency/frequency/size 组合成可解释的打分项：

| 权重槽 | 含义 |
| --- | --- |
| 0 | recency |
| 1 | frequency |
| 2 | size，由 `LOH_USE_SIZE` 控制 |
| 3 | `freq_rec`，由 `LOH_USE_FREQ_REC` 控制 |
| 4 | `freq_size`，由 `LOH_USE_FREQ_SIZE` 控制 |
| 5 | `rec_size`，由 `LOH_USE_REC_SIZE` 控制 |
| 6 | compound v2 的 `freq_rec_size`，或 `LOH_COMPOUND_USE_IRT1=1` 时复用为 `irt1` |

在 `LOH_FEATURE_LOG1P=1` 时，复合项偏向比值形式：`freq / recency`、`freq / size`、`recency * size`、`freq / (recency * size)`。这与直接预测 future reuse 的 learned cache 不同：LOH 是在一组可解释 scoring basis 上调权重。

### 5.3 LOH 的 actor/window state

LOH 给外部 actor 的 state 不是单个对象，而是窗口级状态。`CONTEXT_DIM` 由下列模块拼接：

| 模块 | 维度 | 说明 |
| --- | --- | --- |
| MissRatio | 2 | `hit_ratio`、`byte_hit_ratio`，始终传递 |
| Hit/Miss feature stats | 0 或 24 | 6 个对象特征在 hit/miss 样本上的 mean/variance |
| Cache feature stats | 0 或 12 | 缓存内对象 6 个特征的 mean/variance |
| Candidate feature stats | 0 或 72 | 各候选来源的 6 个特征 mean/variance |
| TopK candidate samples | 可选 | 最低分候选对象的基础特征样本 |
| AvgTopK candidate features | 可选 24 | top 4 候选对象的平均特征 |
| Request history | 可选 | 最近请求对象特征历史 |

因此 LOH 的输入信息包含 workload/window 表现、候选池分布、缓存池状态、top candidates 等，而不只是某个对象的局部历史。

## 6. 本质差异

### 6.1 粒度不同

LRB 和 3LCache 是 object-level predictor：输入一个对象的历史特征，输出这个对象未来多久会再被访问。GLCache 是 segment-level predictor：输入一个段的统计特征，输出段未来效用。LOH 则是 candidate/window-level controller：输入窗口状态与候选集合统计，输出一组对象 scoring 权重。

### 6.2 标签目标不同

LRB/3LCache 的核心标签是 delayed future interval，存在 label delay 和 censoring：对象要等到未来访问或超过窗口后才知道标签。GLCache 的标签是 segment utility，需要 snapshot 后在后续访问中累计。LOH 不直接为每个对象学习 future reuse，而是用窗口级 miss/byte miss 改善作为反馈，调整 scoring 权重。

### 6.3 size 的角色不同

LRB/3LCache 中 size 是对象输入特征，并在 OMR/BMR 排序时进一步调整 score。GLCache 使用 segment 平均对象大小，并在 utility 中按对象大小折扣。LOH 同时把 size 作为基础 scoring 项、compound 项的一部分，以及可选的 active weight 开关，因此 size 不只是输入字段，而是 scoring basis 的一部分。

### 6.4 为什么 LOH 更像“中间层设计”

LRB/3LCache 把模型放在最底层：模型直接预测对象未来。GLCache 把模型放在段级：模型直接预测段效用。LOH 把模型/优化器放在中间层：候选对象仍由 cache 内部统计与候选生成机制产生，模型只选择当前 workload 下该如何组合 recency、frequency、size 和复合项。

这解释了前面实验中看到的现象：即使用相对简单的 GBM actor，LOH 仍能接近强 baseline，因为它不需要模型独自解决完整的 object-level future prediction；它只需要在已有候选集合和 scoring basis 之间做权重适配。

## 7. 论文写法建议

可以把四者概括为三类：

| 类型 | 算法 | 描述 |
| --- | --- | --- |
| Object-level learned eviction | LRB、3LCache | 学习每个对象的 future reuse / reuse-time proxy，然后按对象分数淘汰 |
| Segment-level learned eviction | GLCache | 学习 segment utility，按段进行淘汰或合并决策 |
| Candidate/window-level adaptive scoring | LOH | 不直接预测每个对象未来，而是在候选集合上学习 scoring 权重，适配 workload 与 MR/BMR 目标 |

因此，对比时不应只说“谁的模型更强”，而应强调输入/目标粒度差异：LRB/3LCache/GLCache 的模型承担直接预测 future utility 的责任；LOH 的模型或优化器承担的是选择 scoring rule 的责任，学习问题更低维，也更贴近 cache policy 的可控接口。
