# RSD/LOH 效果原因与验证实验设计

本文档基于 `CDN_paper/RSD.tex`、`libCacheSim/cache/eviction/LOH.c` 以及 `libCacheSim/cache/eviction/` 下主要对比算法实现，整理 RSD/LOH 相比论文实验中 baseline 效果更好的解释方式，以及应该怎样设计实验来证明这个解释。

核心建议：不要把效果提升简单归因于“用了学习算法”或“CMA-ES 更强”。更有说服力的说法是：RSD 把学习目标和决策粒度放在了更适合缓存替换的位置。许多 learned baselines 学的是 reuse time、reuse distance 或 segment utility，这些是替换目标的代理变量；RSD 学的是当前 workload 下哪些 eviction signals 应该被放大或压低，并直接用 miss ratio 反馈更新权重。因此，即使抛开吞吐量和延迟不谈，RSD 也可能在异构 CDN 负载上更稳：它减少了代理预测目标与实际 eviction objective 之间的错配，同时保留对象级、多信号排序能力。

## 1. 一句话主张

RSD 的优势来自“可表达的中间层 + 工作负载级自适应 + 候选池化低延迟执行”的组合，而不是某一个单独技巧。

更适合写进论文的表达是：

> Production CDN traces do not have a stable single eviction signal. Recency, frequency, object size, and their interactions dominate under different workloads and cache sizes. RSD exposes these signals through a lightweight scoring layer, adapts their weights at the workload level, and limits online ranking to a small but diverse candidate set. This allows RSD to behave like specialized policies on simple workloads while remaining robust on mixed production workloads, without paying the inference cost of heavyweight learned caches on every eviction.

中文版本可以写成：

> 生产 CDN 负载中不存在长期稳定的单一淘汰信号。不同 trace、不同缓存空间下，recency、frequency、size 及其交互项对 object miss 和 byte miss 的影响会发生变化。RSD 通过一个轻量的中间评分层显式暴露这些信号，再用 epoch 级优化学习各信号的权重，并将在线决策限制在小规模但来源多样的候选池内。因此，RSD 既能在简单负载上接近专门策略，又能在混合生产负载上保持鲁棒，同时避免重 learned cache 在每次淘汰时的在线推理成本。

## 2. 与各类 baseline 的机制差异

### 2.1 固定启发式：快，但表达能力窄

代表算法包括 LRU、SIEVE、S3-FIFO、WTinyLFU、ARC。

这些算法的优势是在线开销低，缺点是规则空间相对固定：

- LRU 主要依赖 recency。实现上命中后 move-to-head，淘汰 tail。
- SIEVE 用访问 bit 和扫描指针近似保留近期命中过的对象。
- S3-FIFO 用 small/main FIFO 和 ghost 队列表达频率与队列晋升。
- WTinyLFU 更强调 admission/filtering，而不是为每个 eviction candidate 组合多个信号。
- ARC 在 recency 与 frequency 两类队列之间调 p，但仍是有限结构切换。

这些 baseline 可以在特定 workload 上很好，例如强 recency locality 时 LRU 很强，强频率稳定时 TinyLFU/S3-FIFO 类方法更强。但当对象大小分布、one-hit ratio、热点稳定性、短期 burst 同时变化时，固定规则很难同时优化 OMR 和 BMR。

RSD 的解释点：它不是抛弃启发式，而是把启发式信号变成可组合的 score terms。recency、frequency、size 和交互项可以在同一对象级决策里共同起作用。

### 2.2 双专家/在线混合：能自适应，但策略空间仍小

代表算法包括 LeCaR、Cacheus。

这类算法通常在 LRU/LFU 两个专家之间调权，或者借助 ghost history 更新选择概率。它能说明“自适应”本身有价值，但策略空间基本仍围绕 recency 与 frequency 两端摆动。

RSD 相比它们的关键优势不是“也会调权”，而是可调对象更多：

- 不只在 LRU 与 LFU 两个完整策略之间选择。
- 可以直接把 size 纳入 eviction score，从而解释 BMR 改善。
- 可以表达 `freq/recency`、`freq/size`、`recency*size` 这类交互，处理“老但高频”“大但高频”“又老又大”等对象。
- 权重表示 workload preference，而不是一次 ghost hit 后的局部专家选择。

因此论文里可以强调：RSD generalizes expert mixing from selecting among a few policies to continuously weighting eviction signals.

### 2.3 Learned/statistical cache：预测目标更复杂，但未必更贴近替换目标

这里要把算法类别讲准确：LRB、3LCache、GLCache 更接近通常意义上的 learned cache，会训练或调用 GBDT/XGBoost/LightGBM 一类模型；LHD 则更适合称为 statistical/adaptive policy。LHD 会在线统计 hit density，并周期性重估 class/age 下的 hit-density 曲线，但它不是监督学习模型，也没有像 LRB/3LCache 那样训练对象级 reuse predictor。

这些方法与 RSD 的区别要讲准确：它们不是“不学习”或“模型能力一定弱”；关键差异在于它们通常把 eviction 转化为代理统计或代理预测目标，而 RSD 学的是替换策略本身的偏好参数。

- LHD 用在线统计得到的 hit density 给 sampled candidates 排名，表达能力依赖 age/class 建模，容易把对象价值压缩到有限 class/age 统计里。它有自适应统计，但不属于对象级监督学习模型。
- LRB/3LCache 使用 LightGBM/XGBoost 类模型预测 reuse distance 或 reuse time，再把预测值转成 eviction ranking。这个预测任务与最终 OMR/BMR 目标相关，但不是同一个目标。
- GLCache 更偏 segment-level utility。即使 segment utility 预测准确，淘汰粒度仍可能把同一 segment 内的冷热对象绑在一起。
- 一些 learned cache 会复用旧 prediction 或在训练标签成熟后再更新模型。面对 burst、one-hit objects、热点迁移时，预测滞后会直接影响 victim ranking。

RSD 的效果优势叙事应该是：它没有把问题转化为“准确预测每个对象下一次访问时间”，而是直接学习“当前 workload 下什么样的对象更值得保留”。这在 CDN traces 上很重要，因为对象替换价值不只由下一次访问时间决定，还受对象大小、重复访问强度、cache size、目标是 OMR 还是 BMR 影响。

更具体地说，RSD 相比 learned/statistical baselines 的效果优势可以从四个非吞吐角度解释。

第一，代理目标错配更小。Reuse distance/time 是有用信号，但 eviction objective 是保留价值排序。一个对象下次访问更远，不一定总比另一个对象更该淘汰；对象大小、未来访问次数、byte miss 代价和缓存占用机会成本都会改变排序。LRB/3LCache 可以对预测结果做 size scaling，但这仍是先预测代理变量再后处理。RSD 的 score family 直接把 recency、frequency、size、`freq/recency`、`freq/size`、`recency*size` 放在同一排序函数里，并用 miss ratio feedback 调权，因此更贴近最终替换目标。

第二，RSD 学的是 preference，不是 object-level future label。对象级 learned cache 需要从历史访问中构造 reuse labels；长尾对象、one-hit objects、被提前淘汰的对象都会带来 censored 或延迟标签。RSD 不要求每个对象都有准确未来标签，而是用 epoch-level miss ratio 评价整组权重。这会牺牲一部分细粒度预测能力，但能减少 noisy labels 对 victim ranking 的直接干扰。

第三，RSD 的对象级候选池天然面向“可淘汰对象”。GLCache 这类 segment-level 方法可能因为粒度较粗，把冷热对象放在同一决策单元里。LRB/3LCache/LHD 也会采样候选，但采样本身不一定覆盖单信号极端对象。RSD 的结构化候选源显式覆盖老对象、低频对象、大对象和可选 IRT 对象，再用随机候选补 coverage；这提升的是候选质量，不只是降低成本。

第四，RSD 更容易表达 OMR/BMR 的目标切换。很多 learned baselines 以 reuse prediction 为中心，再针对 object miss 或 byte miss 做缩放。RSD 则可以通过 feedback 和 size-aware interactions 改变权重，使“保留高频小对象”和“避免大对象 byte miss”在同一个 score function 中重新平衡。

所以，抛开吞吐量/延迟，RSD 比 learned/statistical baselines 效果更好的核心解释是：它学习了更接近缓存替换目标的低维 preference space，而不是把对象价值固定压缩为 hit-density 统计，或转化为更困难、更噪声、更间接的对象未来访问预测问题。

## 3. RSD/LOH 实现支撑的三个机制

### 3.1 多信号可表达中间层

`LOH.c` 中的核心 score 路径会计算对象的 recency、frequency、size 等特征，并在 compound 模式下加入交互项。实现中也有开关控制 size 与各交互项是否启用，例如：

- `LOH_SCORE_USE_COMPOUND`
- `LOH_USE_SIZE`
- `LOH_USE_FREQ_REC`
- `LOH_USE_FREQ_SIZE`
- `LOH_USE_REC_SIZE`

这意味着 RSD 可以构造一组自然的 feature ablation，而不是只展示最终 full model。论文中应把它解释为“策略空间扩展”：LRU、LFU、Size-aware、Hyperbolic-like 等倾向都可以被看成这个 score family 的不同权重区域。

### 3.2 Epoch-level workload adaptation

实现中的 CMA-ES 不是每次请求或每次 miss 同步推理，而是在一个 epoch 内观察 miss ratio 反馈，再更新下一阶段的权重。这个机制适合解释为 workload-level preference search。

要强调两点：

- CMA-ES 学的是权重，不是一个在线重模型。
- feedback 可以面向 OMR、BMR 或 weighted miss ratio，因此能够解释为什么 RSD 可以同时兼顾 object miss 和 byte miss。

这也决定了实验上必须做 fixed-weight 对照。如果只和 baseline 比，不足以证明“自适应权重”本身有贡献。

### 3.3 候选池化在线执行

`LOH_to_evict` 的在线路径不是全缓存扫描。它从多个结构化来源和随机来源生成候选，再对候选算 score。结构化来源覆盖 recency tail、低频对象、大对象、可选 IRT 信号；随机候选补充可能不在极端结构里的联合劣对象。

这一点的论文价值很大：

- 它解释了为什么 RSD 比重 learned cache 更快。
- 它解释了为什么 RSD 比单一结构候选更鲁棒。
- 它给 candidate budget sensitivity 实验提供了直接动机。

## 4. 应该证明的因果链

建议把论文实验组织成下面这条链：

1. Workload heterogeneity exists.
   不同 trace 的 recency locality、frequency skew、object size dispersion、one-hit ratio 不同，因此不存在稳定最优的单一启发式。

2. Different signals matter under different workloads.
   在 recency-dominant、frequency-dominant、size-sensitive、mixed traces 上，最优权重和最有贡献的 feature 不一样。

3. RSD can express these signal combinations.
   去掉 size 或交互项后，在对应 workload 上性能下降；full compound 在跨 trace rank 上更稳。

4. Online adaptation is needed.
   固定权重在某些 trace 上接近最优，但跨 trace 平均 rank 或 worst-case 更差；CMA-ES 能接近 per-trace offline best。

5. Candidate pooling preserves most benefits at low cost.
   结构化候选 + 随机候选在较小预算下接近更大预算的 miss ratio，同时 throughput 明显优于重 learned cache。

这条链比单纯报告“RSD 平均 OMR/BMR 最低”更有说服力，因为它能回答 reviewer 最可能问的问题：效果到底来自特征、学习、候选池、调参，还是额外计算预算。

## 5. 实验矩阵

### 5.1 Workload heterogeneity 实验

目的：证明 baseline 表现波动不是偶然，而是 workload 信号不同导致的。

实验对象：论文中的所有 production traces 和 synthetic/motivation traces，使用论文已有的 cache size 设置。

统计每个 trace 的 workload descriptors：

- Recency locality：reuse distance 分布、短窗口复用率、LRU stack distance 分位数。
- Frequency skew：对象请求频次 Gini、top-k object request share、热点稳定性。
- Size dispersion：对象 size 的均值、P95/P99、Gini、large-object byte share。
- One-hit ratio：只请求一次的 object 占比和 byte 占比。
- Object/byte conflict：高频小对象与低频大对象的贡献差异。

展示方式：

- 一张 trace descriptor heatmap。
- 一张 baseline winner map：每个 trace/cache size 下哪个 baseline 最好。
- 一张相关性图：RSD 相对 LRU 或 best heuristic 的 gain 与 size dispersion、frequency skew、one-hit ratio 的关系。

预期结论：如果不同 trace 上获胜 baseline 不同，且 RSD 的增益在 mixed/high-conflict traces 上更明显，就能支撑“生产负载需要多信号组合”的解释。

### 5.2 Feature 与 interaction ablation

目的：证明 RSD 的提升来自可表达中间层，而不是单一权重或调参噪声。

建议配置：

| Variant | compound | size | freq-rec | freq-size | rec-size | 证明点 |
|---|---:|---:|---:|---:|---:|---|
| RSD-rec-freq | off | off | off | off | off | 只保留 recency/frequency 的最低表达能力 |
| RSD-base-size | off | on | off | off | off | size 对 BMR 的独立贡献 |
| RSD-comp-no-size | on | off | on | off | off | 不使用 size 时，frequency/recency 交互是否足够 |
| RSD-comp-no-freq-size | on | on | on | off | on | 大对象与高频对象冲突的贡献 |
| RSD-comp-no-rec-size | on | on | on | on | off | 老大对象惩罚是否有效 |
| RSD-full | on | on | on | on | on | 完整模型 |

指标：

- OMR、BMR，最好都用 relative to LRU。
- Average rank 和 robustness score。
- 每个 variant 的 best/worst trace。

展示方式：

- 主图用 normalized OMR/BMR rank，而不是只画平均值。
- 附图画每个 trace 的 full-minus-ablation 差值，避免平均值掩盖负例。

预期结论：

- size 项应主要改善 BMR，特别是在 size dispersion 大的 trace 上。
- frequency/recency 交互应改善热点稳定但 recency 噪声大的 trace。
- frequency/size 交互应帮助保留高频小对象，避免 byte miss 与 object miss 冲突。
- recency/size 交互应帮助淘汰又老又大的对象，改善 BMR。

如果某个交互项贡献不稳定，也可以诚实写成：该项不是全局平均提升的唯一来源，但能改善特定高冲突 workload，并提升 worst-case rank。

### 5.3 Learning ablation

目的：证明 online workload adaptation 必要，而不是某组固定权重已经足够。

建议配置：

| Variant | 权重来源 | 证明点 |
|---|---|---|
| Initial/default weights | 固定初始权重 | 证明默认启发式组合的下限 |
| Global fixed best | 在训练 traces 上找一组全局固定权重 | 检查是否只靠离线调参就够 |
| Per-trace offline best | 每个 trace/cache size 单独搜索最优固定权重 | 作为 upper bound，不作为可部署算法 |
| Online CMA-ES | 当前 RSD 主配置 | 证明在线自适应能接近 per-trace best，并优于 global fixed |
| Oracle switch among ablations | 每个 trace 选择最好的 ablation variant | 可选，用于说明 full RSD 是否覆盖多个局部专家 |

指标：

- 每个 epoch 的 OMR/BMR 曲线。
- 收敛后的权重分布。
- 跨 trace average rank、worst-case rank。

展示方式：

- Weight heatmap：trace 为行，feature weight 为列。
- Performance gap plot：Online CMA-ES 与 global fixed、per-trace offline best 的差距。
- Epoch curve：展示权重更新后 miss ratio 是否下降。

预期结论：

- 如果 global fixed 在某些 trace 很好但在另一些 trace 明显差，说明单组权重不鲁棒。
- 如果 online CMA-ES 接近 per-trace offline best，说明 RSD 学到的是 workload preference。
- 如果 per-trace offline best 远好于 online CMA-ES，说明需要改进学习速度；这会削弱当前解释，应提前检查。

### 5.4 Candidate pool ablation

目的：证明候选池设计既保留决策质量，又控制在线成本。

建议配置：

| Variant | structured candidates | random candidates | 证明点 |
|---|---:|---:|---|
| Structured-only | N | 0 | 结构化极端对象是否足够 |
| Random-only | 0 | N | 随机采样能否捕捉非极端联合劣对象 |
| Mixed small | N/2 | N/2 | 小预算混合是否高性价比 |
| Mixed default | default | default | 主配置 |
| Mixed large | 2x default | 2x default | 检查是否已经接近饱和 |
| Full scan sanity | all objects | 0 | 可选，只在小 cache/短 trace 上做近似上界 |

指标：

- OMR/BMR。
- Throughput 或 ns/request。
- 每次 eviction 的候选数、打分次数。
- candidate source hit rate：最终 victim 来自哪个 source。

展示方式：

- Candidate budget vs miss ratio/throughput 双轴图。
- Victim source breakdown stacked bar。

预期结论：

- structured-only 通常能抓到明显老、低频、大对象，但可能错过多信号联合劣对象。
- random-only 质量可能不稳定，但提供 coverage。
- mixed candidate 在小预算下接近 large budget，说明不是靠全扫描获胜。

### 5.5 Objective ablation：OMR 与 BMR 的权衡

目的：证明 RSD 能根据目标函数调整，而不是只优化 object miss。

建议配置：

- OMR-only feedback。
- BMR-only feedback。
- Weighted OMR/BMR feedback。
- 固定权重下的同三组目标，作为对照。

指标：

- OMR vs BMR Pareto frontier。
- 不同目标下的 size-related weight 分布。
- byte-heavy traces 上的 BMR gain。

展示方式：

- Pareto scatter：每个点是一个 policy/target。
- Weight-target relation：BMR 权重提高时 size/freq-size/rec-size 项是否变化。

预期结论：

如果 BMR-oriented feedback 会增加 size-aware 或 large-object penalty 相关项，同时 BMR 改善而 OMR 代价有限，就能强力证明 RSD 的 score layer 不是只在做 LRU/LFU 混合。

### 5.6 与 learned/statistical cache 的效果对照：证明不是只靠更快

目的：在不讨论吞吐量/延迟的前提下，说明 RSD 为什么可能比 LRB、3LCache、GLCache 这类 learned baselines，以及 LHD 这类 statistical/adaptive baseline，有更好的 OMR/BMR 或更稳的 rank。

核心假设：这些 baselines 常把 eviction 转化为 reuse distance/time、hit density 或 segment utility 等代理目标；RSD 直接优化一个多信号 eviction preference。两者在简单 workload 上可能接近，但在 size/frequency/recency 冲突强的 CDN workload 上，代理目标错配会让 baseline 排错 victim。

#### 5.6.1 Same-candidate scoring 实验

这是最关键的隔离实验。

做法：在同一批 eviction events 上固定候选集合，然后分别用 RSD score、LRB/3LCache prediction score、LHD hit density score 对同一候选集合排序。

候选集合建议至少做三组：

| Candidate set | 目的 |
|---|---|
| RSD mixed candidates | 判断 learned score 在 RSD 候选质量下是否仍输 |
| Learned baseline native candidates | 判断 RSD score 在对方候选集合上是否仍稳 |
| Union candidates | 尽量消除候选覆盖差异，主要比较 scoring objective |

指标：

- OMR/BMR。
- Hindsight top-1 agreement：该决策点事后看最该淘汰的对象是否被选中。
- Hindsight rank/NDCG：事后最差对象在各 score 排序中的位置。
- Per-trace rank，尤其看 high size dispersion、high one-hit ratio、hotspot-shift traces。

预期解释：

- 如果 RSD score 在同一候选集合上仍优于 learned score，说明优势主要来自更贴近 eviction objective 的 scoring。
- 如果 learned score 在 RSD candidates 上明显变好，说明 learned baseline 原本一部分问题来自候选覆盖；这仍支持 RSD 的 candidate design 有效果优势。
- 如果 RSD score 只在自己候选集合上强，在 union 上不强，说明应谨慎宣称 scoring 更好，转而强调 candidate-source design。

#### 5.6.2 Proxy objective gap 实验

目的：直接证明 reuse prediction accuracy 不等于 eviction quality。

做法：对每次 eviction 的候选对象，用未来 trace 计算 hindsight value。可以分别定义 OMR 和 BMR 版本：

- OMR hindsight：淘汰该对象后到下一次访问前造成的 object miss 风险，或者在一个有限 horizon 内的未来命中次数。
- BMR hindsight：未来 miss byte cost 与对象占用空间的组合，例如 future byte hits per cached byte，或 horizon 内 lost bytes / object size。
- Combined hindsight：按论文主目标的 OMR/BMR 权重组合。

然后比较：

- Learned model 的 predicted reuse distance/time 与 hindsight eviction value 的相关性。
- RSD score 与 hindsight eviction value 的相关性。
- 各方法选择 victim 的 regret：与 hindsight best victim 的差距。

预期解释：

- 如果 learned prediction 对 reuse distance 相关性高，但对 BMR hindsight 或 combined hindsight 相关性下降，说明代理目标存在错配。
- 如果 RSD score 对 combined hindsight 更相关，说明 RSD 的多信号 score 更贴近最终替换目标。

#### 5.6.3 Size-conflict bucket 实验

目的：证明 learned reuse prediction 在 size 与 frequency 冲突时容易排错，而 RSD 的 size interaction 有实际贡献。

做法：把 eviction events 按候选对象的 size conflict 分桶：

- large-and-cold：大对象、低频、老。
- large-but-hot：大对象、高频或短 IRT。
- small-but-cold：小对象、低频、老。
- small-and-hot：小对象、高频、近访问。
- mixed-conflict：同一候选集中同时存在大冷对象和小热对象。

对每个桶报告各 policy 的 victim 分布、OMR/BMR、hindsight regret。

预期解释：

- 如果 RSD 在 mixed-conflict bucket 中 BMR 或 combined regret 更低，说明 `freq/size`、`recency*size` 等交互项不是装饰，而是在处理 learned reuse prediction 容易混淆的对象价值冲突。
- 如果 learned baseline 更常淘汰预测 reuse time 远但 byte value 高的对象，可以用作代理目标错配的具体证据。

#### 5.6.4 Segment granularity 实验

目的：解释为什么 object-level RSD 可能比 GLCache 这类 segment-level learned policy 效果更好。

做法：分析 GLCache 被淘汰 segment 内部的对象组成：

- segment 内对象未来 hit/byte hit 的分布。
- segment 内 top hot objects 是否被一起淘汰。
- segment utility 排名与 segment 内最差对象/最好对象的差异。
- 同一时刻如果用 RSD object candidates，是否能只淘汰低价值对象。

指标：

- Evicted segment hot-object contamination：被淘汰 segment 中未来仍会命中的对象占比。
- Wasted eviction bytes：被连带淘汰的高价值对象 bytes。
- Object-level hindsight regret。

预期解释：

如果 GLCache 的 segment decision 经常连带淘汰 segment 内高价值对象，而 RSD 选择的是对象级低价值 victim，就能说明 RSD 的效果优势来自更合适的决策粒度。

#### 5.6.5 Label delay/censoring 实验

目的：证明对象级 future prediction 在 CDN 长尾和 one-hit 场景下更容易受 noisy/censored labels 影响。

做法：按对象历史标签质量分桶：

- one-hit objects。
- long reuse interval objects。
- recently admitted objects。
- history-rich hot objects。
- 被算法提前淘汰、未来标签需要等待的对象。

报告 learned/statistical baseline 与 RSD 在这些桶上的 victim regret 和 miss contribution。

预期解释：

- 如果 LRB/3LCache 这类 learned baseline 在 one-hit/long-tail 桶里误保留对象更多，说明 object-level prediction 受标签噪声影响；如果 LHD 在这些桶里表现差，则更可能说明 class/age hit-density 统计粒度不足。
- 如果 RSD 在 recently admitted 或 history-poor 对象上更稳，说明直接学习 preference 可以减少对单对象完整历史标签的依赖。

### 5.7 与 learned/statistical cache 的延迟和粒度对照

目的：证明 RSD 的优势不只是 miss ratio，而是 latency-accuracy tradeoff 更好。

对比对象：LRB、3LCache、GLCache、LHD，以及快 heuristic 中最强的几个。注意报告时应把 LHD 标为 statistical/adaptive，而不是监督学习模型。

建议报告：

| Policy | decision granularity | online model cost | candidate/ranking cost | OMR | BMR | throughput |
|---|---|---|---|---:|---:|---:|
| LRU/SIEVE/S3-FIFO | object/queue | none | O(1) or scan pointer |  |  |  |
| LHD | sampled object | statistical density | sampled ranking |  |  |  |
| LRB/3LCache | object prediction | GBDT inference/reuse | sampled ranking |  |  |  |
| GLCache | segment | learned segment utility | segment selection |  |  |  |
| RSD | object candidate | epoch-level weight update | lightweight score on candidate pool |  |  |  |

预期结论：

- RSD 的在线路径应该明显轻于对象级 GBDT inference。
- RSD 的对象级候选评分比 segment-level decision 更细，尤其对大对象和热点对象混杂的 trace 更稳。
- 如果某 learned baseline 在单个 trace 上 OMR 很强，但 throughput 或 BMR 较差，可以用 tradeoff 而不是单指标输赢来解释。

## 6. 最值得优先做的五组实验

如果时间有限，优先做这五组：

1. Feature/interaction ablation。
   这是证明“RSD 中间层有用”的主证据。没有这个实验，reviewer 很容易认为 full RSD 只是额外调参。

2. Fixed-weight vs online CMA-ES。
   这是证明“workload adaptation 有用”的主证据。最好同时给 global fixed best 和 per-trace offline best。

3. Same-candidate scoring against learned/statistical baselines。
   这是证明“RSD 相比 learned/statistical algorithm 效果更好不是因为候选集合或吞吐量”的主证据。把 RSD、LRB/3LCache/LHD 放到同一候选集合上排序，才能隔离 scoring objective。

4. Candidate budget/source ablation。
   这是证明“低延迟不是牺牲质量换来的”的主证据。需要同时报告 miss ratio 和 throughput。

5. Workload descriptor correlation。
   这是把机制解释和 trace 特性连起来的证据。它能解释为什么 RSD 在某些 traces 上提升更大，在某些 traces 上只持平。

这五组可以形成更完整的因果链：workload 异构 -> 需要多信号 -> RSD 能表达并自适应 -> 相比 learned baselines，RSD 的 scoring objective 更贴近 eviction value -> 候选池让在线成本可控。

## 7. 可直接写进论文的段落模板

### 7.1 Explaining why RSD improves miss ratio

> The improvement of RSD comes from exposing the right abstraction to the online eviction path. Many production traces are not purely recency-dominated or frequency-dominated; they contain large one-hit objects, stable hot objects, and bursts whose relative importance changes across cache sizes. Fixed heuristics encode one or two of these signals in a rigid way, while expert-mixing methods can only interpolate between a small number of complete policies. RSD instead scores each candidate with a compact feature family that includes recency, frequency, object size, and their interactions. This makes it possible to protect objects that are old but repeatedly useful, evict large objects that have little evidence of reuse, and balance object misses against byte misses within the same decision function.

### 7.2 Explaining why RSD can outperform learned baselines in miss ratio

> The advantage of RSD over learned eviction policies is not that RSD uses a more complex model. It uses a more aligned learning target. Policies such as LRB and 3LCache learn object-level reuse distance or reuse time, and GLCache learns segment-level utility. These predictions are useful proxies, but eviction quality depends on a different ranking objective: the value of keeping an object under the current cache size, object-size distribution, miss metric, and workload phase. RSD directly learns a preference vector over eviction signals and evaluates candidates with a score that combines recency, frequency, size, and their interactions. This reduces the mismatch between the learned target and the actual victim-selection objective, especially on CDN traces where large cold objects, small hot objects, one-hit objects, and shifting bursts coexist.

> Our same-candidate analysis isolates this effect. When RSD and learned baselines rank the same candidate set, RSD produces lower hindsight regret on traces with strong size/frequency conflicts, indicating that its gain is not only caused by candidate coverage. Conversely, when learned models improve on RSD's candidate set, the result shows that RSD's candidate design exposes higher-quality eviction alternatives. In both cases, the comparison explains why RSD achieves better miss-ratio robustness: it combines a candidate set tailored to eviction with a scoring objective closer to the final cache metric.

### 7.3 Explaining why RSD is faster than heavy learned policies

> RSD differs from learned caches that predict reuse time or reuse distance for individual objects. Rather than invoking a heavy model on the critical path, RSD learns the weights of a lightweight scoring layer at epoch boundaries. During eviction, it only ranks a bounded candidate set collected from recency, frequency, size, and random sources. This design keeps the online operation close to heuristic policies while still allowing the policy to move across a richer family of eviction preferences.

### 7.4 Explaining why candidate pooling matters

> The candidate pool is not only an optimization. It is part of the policy design. Structured candidates expose objects that are extreme under individual signals, such as old, low-frequency, or large objects, while random candidates provide coverage for objects that are not extreme in any single dimension but are poor under the learned combination. Our candidate ablation shows that combining these sources reaches nearly the same miss ratio as larger candidate budgets, while preserving high throughput.

### 7.5 Explaining why fixed weights are insufficient

> A single fixed weight vector cannot be optimal across traces because the relative cost of recency, frequency, and size mistakes changes with workload composition. The fixed-weight ablation confirms this: a globally tuned vector performs well on some traces but loses robustness on others. Online CMA-ES closes much of the gap to per-trace offline weights, indicating that RSD's gains come from adapting the preference vector rather than from a lucky static configuration.

## 8. 结果呈现建议

主文不要塞太多 ablation 表。建议主文保留以下图表：

1. Overall OMR/BMR relative to LRU，含 average rank。
2. Feature ablation summary，显示 full RSD 相对去掉某项的 gain。
3. Fixed/global/per-trace/online weight 对比。
4. Candidate budget vs miss ratio/throughput 曲线。
5. Throughput tradeoff table，对比 heuristic、RSD、learned baselines。

附录放以下内容：

- 每个 trace/cache size 的完整 ablation 表。
- 每个 trace 的 learned weights。
- candidate source breakdown。
- workload descriptors 与 gain 的相关性矩阵。
- 运行参数和日志路径。

## 9. 需要避免的表述

下面这些说法容易被 reviewer 追问，建议不要作为主叙事：

- “RSD 好是因为 CMA-ES 比 baseline 更强。”
  问题：这无法解释为什么不用更强模型，也无法解释在线开销。

- “RSD 好是因为用了更多特征。”
  问题：更多特征可能只是过拟合，需要 ablation 和跨 trace rank 支撑。

- “RSD 在平均值上最好。”
  问题：平均值可能掩盖 workload 失配，建议同时报告 rank、worst-case、robustness score。

- “RSD 接近 learned cache 但更快。”
  问题：需要 throughput、candidate count、per-eviction latency 或 profiling 支撑。

更稳的说法是：RSD 选择了适合 cache eviction 的学习粒度，以轻量 score family 表达多信号偏好，并用 bounded candidate ranking 保持在线成本可控。

## 10. 实验执行注意事项

后续如果把上述实验落成脚本，建议遵守以下约束：

- 每个实验目录使用 `sweeps/YYYYMMDD-<name>/`，短期中间日志可以放 `tmp/YYYYMMDD-<name>/logs/`。
- Python/RL 相关流程必须使用项目 `.venv`，并显式设置 `PATH`。
- cachesim 运行需要显式设置 `LD_LIBRARY_PATH`，确保 libcmaes、xgboost、lightgbm 动态库可见。
- 每次切换配置用干净 shell，避免残留 `LOH_*` 环境变量污染结果。
- 长实验必须后台运行，并写 PID、launcher log、driver log/watchdog log。
- 修改 `LOH_INCLUDE_*`、共享内存结构、编译期 profiling 或 `LOH.c` 代码后必须重新编译；只改运行时环境变量则不应覆盖旧构建。
- 对每个结果保存完整 env dump、git diff summary、cachesim stdout/stderr、trace path、cache size、num requests。

## 11. 最终论证闭环

最终论文里可以按下面顺序讲：

1. Production traces are heterogeneous。
2. Single-signal and small-policy-family baselines fail under different heterogeneity patterns。
3. RSD's feature family captures the relevant signals and interactions。
4. Online adaptation chooses different weights for different workloads。
5. Candidate pooling makes this expressive policy cheap enough for online eviction。
6. Experiments validate each step with ablation, weight analysis, candidate sensitivity, and throughput results。

这套叙事的好处是：即使某个 trace 上某个 baseline 接近或超过 RSD，也不会破坏主结论。因为主结论不是“RSD 每个点都赢”，而是“RSD 在异构 workload 上提供了更好的 accuracy/latency/robustness tradeoff”。

## 12. 离线 Belady/BeladySize 结果对 learned-target 论证的启示

本节根据 `tmp/20260506-belady-bsize-cache0001-from-20260504-plan/results/` 中的 Belady/BeladySize 结果，使用 `docs/20260423-ablation-per-group-cache0001/cmaes版本/` 各组文档表4/表5的 LRU 值，计算每条 trace 的 `x/LRU`，再在组内做简单平均。v7 对照值来自同目录 `20260519-v7-16cfg-relative-lru-6groups.md` 的 v7 行。

计算日志保存于 `tmp/20260525-belady-v7-relative-lru.log`。口径说明：

- `ratio < 1` 表示优于 LRU；越小越好。
- `delta = Belady ratio - v7 ratio`；正数表示 v7 更好，负数表示 Belady/BeladySize 更好。
- v7 的相对 LRU 汇总文档采用 6 组口径，并显式排除 cloudphysics 的组间平均；因此主对比使用 `alibabaBlock`、`metaCDN`、`metaKV`、`tencentBlock`、`wiki` 五组，即同文档的 `avg_excluding_tencentPhoto` 口径。
- tencentPhoto 没有 BeladySize 可用结果；wiki 缺 1 条 BeladySize；alibabaBlock 和 tencentBlock 各缺 1 条 BeladySize。下面表中的 `n` 是实际参与计算的 trace 数。

### 12.1 组内相对 LRU 结果

| group | algo | n | MR/LRU | v7 MR/LRU | delta MR | BMR/LRU | v7 BMR/LRU | delta BMR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| alibabaBlock | Belady | 1000 | 0.797541 | 0.877191 | -0.079650 | 0.893656 | 0.951320 | -0.057664 |
| alibabaBlock | BeladySize | 999 | 0.756053 | 0.877191 | -0.121138 | 0.880616 | 0.951320 | -0.070704 |
| metaCDN | Belady | 3 | 0.864485 | 0.684855 | +0.179630 | 0.930525 | 0.918730 | +0.011795 |
| metaCDN | BeladySize | 3 | 0.683818 | 0.684855 | -0.001037 | 0.877982 | 0.918730 | -0.040748 |
| metaKV | Belady | 5 | 1.370371 | 0.557128 | +0.813243 | 1.260194 | 0.963001 | +0.297193 |
| metaKV | BeladySize | 5 | 0.531749 | 0.557128 | -0.025379 | 1.144305 | 0.963001 | +0.181304 |
| tencentBlock | Belady | 4755 | 0.803754 | 0.879309 | -0.075555 | 0.871712 | 0.943648 | -0.071936 |
| tencentBlock | BeladySize | 4754 | 0.750648 | 0.879309 | -0.128661 | 0.860678 | 0.943648 | -0.082970 |
| tencentPhoto | Belady | 2 | 0.731017 | 0.873155 | -0.142138 | 0.715701 | 1.045179 | -0.329478 |
| wiki | Belady | 3 | 0.646007 | 0.660313 | -0.014306 | 0.730636 | 0.907399 | -0.176763 |
| wiki | BeladySize | 2 | 0.564321 | 0.660313 | -0.095992 | 0.826356 | 0.907399 | -0.081043 |

### 12.2 组间平均结果

| aggregate | algo | groups_n | MR/LRU avg | v7 MR/LRU avg | delta MR | BMR/LRU avg | v7 BMR/LRU avg | delta BMR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| avg_excluding_tencentPhoto | Belady | 5 | 0.896432 | 0.731759 | +0.164672 | 0.937345 | 0.936820 | +0.000525 |
| avg_excluding_tencentPhoto | BeladySize | 5 | 0.657318 | 0.731759 | -0.074441 | 0.917987 | 0.936820 | -0.018832 |
| avg_including_tencentPhoto | Belady | 6 | 0.868863 | 0.755325 | +0.113537 | 0.900404 | 0.954879 | -0.054475 |
| avg_including_tencentPhoto | BeladySize | 5 | 0.657318 | 0.731759 | -0.074441 | 0.917987 | 0.936820 | -0.018832 |

### 12.3 metaCDN/metaKV 逐 trace 对照

下表把 `docs/20260423-ablation-per-group-cache0001/cmaes版本/` 中 metaCDN 与 metaKV 每条 trace 的 `LRU`、`LRB-BMR`、`ThreeLCache-BMR`、`ThreeLCache-OMR`、`best_LOH` 复制出来，并补上 `tmp/20260506-belady-bsize-cache0001-from-20260504-plan/results/` 对应的 Belady/BeladySize 结果。这里将 `best_LOH` 记为 `LOH-v7`，数值是绝对 MR/BMR，不是相对 LRU。

#### 12.3.1 Miss Ratio

| group | trace | LRU | LRB-BMR | ThreeLCache-BMR | ThreeLCache-OMR | LOH-v7 | Belady | BeladySize |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| metaCDN | meta_reag | 0.434200 | 0.420600 | 0.432100 | 0.489205 | 0.312774 | 0.374596 | 0.308680 |
| metaCDN | meta_rnha | 0.664500 | 0.650900 | 0.669500 | 0.736570 | 0.445479 | 0.579839 | 0.451691 |
| metaCDN | meta_rprn | 0.589300 | 0.567300 | 0.584000 | 0.672001 | 0.391190 | 0.505699 | 0.389405 |
| metaKV | 202206_kv_traces_all | 0.220900 | 0.180031 | 0.177733 | 0.132044 | 0.127965 | 0.433819 | 0.143578 |
| metaKV | 202210_kv_traces_all_sort | 0.197301 | 0.153333 | 0.154036 | 0.095506 | 0.091465 | 0.118572 | 0.071873 |
| metaKV | 202401_kv_traces_all_sort | 0.274800 | 0.241700 | 0.241600 | 0.162686 | 0.157420 | 0.198659 | 0.141132 |
| metaKV | meta_kvcache_traces_1 | 0.315300 | 0.257400 | 0.254700 | 0.200403 | 0.194657 | 0.556478 | 0.239359 |
| metaKV | 202312_kv_traces_all | 0.193681 | - | 0.198805 | 0.105336 | 0.082235 | 0.348466 | 0.072004 |

#### 12.3.2 Byte Miss Ratio

| group | trace | LRU | LRB-BMR | ThreeLCache-BMR | ThreeLCache-OMR | LOH-v7 | Belady | BeladySize |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| metaCDN | meta_reag | 0.222700 | 0.220400 | 0.219700 | 0.250859 | 0.205810 | 0.206083 | 0.200234 |
| metaCDN | meta_rnha | 0.286500 | 0.289600 | 0.285100 | 0.315054 | 0.244558 | 0.264113 | 0.246520 |
| metaCDN | meta_rprn | 0.284300 | 0.285700 | 0.281600 | 0.308716 | 0.252472 | 0.268473 | 0.248584 |
| metaKV | 202206_kv_traces_all | 0.299400 | 0.282171 | 0.275452 | 0.313062 | 0.274747 | 0.524831 | 0.395631 |
| metaKV | 202210_kv_traces_all_sort | 0.295849 | 0.285049 | 0.281083 | 0.314835 | 0.275724 | 0.201390 | 0.305366 |
| metaKV | 202401_kv_traces_all_sort | 0.229000 | 0.207400 | 0.202500 | 0.219189 | 0.208088 | 0.149551 | 0.250824 |
| metaKV | meta_kvcache_traces_1 | 0.429400 | 0.382900 | 0.378200 | 0.418789 | 0.377558 | 0.643821 | 0.508077 |
| metaKV | 202312_kv_traces_all | 0.208508 | - | 0.219086 | 0.231640 | 0.184590 | 0.357570 | 0.227152 |

这个逐 trace 表更直观地显示：metaCDN 上 BeladySize 与 LOH-v7 基本同量级，且 BMR 往往更低；metaKV 上 Belady/BeladySize 的 BMR 不稳定，尤其 `202206_kv_traces_all`、`meta_kvcache_traces_1` 和 `202312_kv_traces_all` 明显高于 LOH-v7。因此这里的证据更支持“plain reuse distance 不鲁棒、reuse distance*size 是强 oracle proxy 但不稳定对齐 BMR”，而不是简单否定 reuse-based oracle。

### 12.4 meta_reag 个案：为什么需要负载偏好中间层

`meta_reag` 是说明 RSD 中间层价值的一个更干净个案，因为它同时具备短 reuse、长尾 reuse、极端 frequency 头部、极端 size 变异和明显非平稳访问结构。已有 trace 分析位于 `docs/20260409-TRACE_CHARACTERISTIC_COMPARISON.md`，对应图在 `figures/20260409-trace-characteristic-comparison/`，聚合统计在 `analysis/summary.json` 与 `analysis/trace_preference_report.md`。

从 trace 结构看，`meta_reag` 不是单一 reuse-distance 信号可以稳定概括的负载。`meta_reag_reuse_vt.png` 显示 CDF 起点附近快速跃升，但尾部继续延伸；统计报告中 reuse p50=10s，p90=17.0m，p99=2.73d，`<=1h` 占 0.918、`>1d` 仍有 0.029。这说明该 trace 同时有 burst/极短复用和长间隔回访。对象级 learned RD 模型如果只学一个 future-interval 排序，很容易在这两类样本之间形成不稳定边界：短期 burst 要保留，长尾回访也可能有价值，但它们的历史特征和标签成熟速度不同。

frequency 维度也不是普通 Zipf，而是极端头部主导。`analysis/summary.json` 中 `meta_reag` 的 top1=0.243850、top10=0.260909、top100=0.295644、top1pct=0.511356；`meta_reag_pop_rank.png` 也显示头部陡降远强于其他真实 trace。也就是说，少数超热对象贡献了大量访问，但同时还有超过 1200 万对象的冷尾。`analysis/trace_preference_report.md` 还给出 cold object ratio mean=0.576、p90=0.676。这个结构会放大对象级预测的代价：超热对象一旦被误判，MR 会明显变差；大量冷对象如果被过度保留，又会浪费容量并伤害 BMR。

size 维度进一步把 OMR 与 BMR 的偏好拉开。trace 特征文档指出 `meta_reag` 对象大小横跨 1B 到 4.3GB；`analysis/summary.json` 的窗口统计中，size_p50 mean=461.8KB 但 std=5.375MB，size_p90 mean=11.93MB 且 std=35.45MB，size_p99 mean=403.6MB 且 std=699.6MB；`analysis/trace_preference_report.md` 中 bytes/req mean=27.95MB、cv=0.628。换言之，size 不是附属特征，而是和 frequency/reuse 同等级的核心决策维度。一个纯 OMR 排序即使对象数命中合理，也可能牺牲 byte miss；一个过强的 size scaling 又可能误踢大而热的对象。

这正好解释了表 12.3 中 learned baseline 的异常：cache=0.001 时，`ThreeLCache-OMR` 在 `meta_reag` 上 MR=0.489205、BMR=0.250859，分别差于 LRU 的 0.434200/0.222700；而 `ThreeLCache-BMR` 为 0.432100/0.219700，`LRB-BMR` 为 0.420600/0.220400，只是小幅优于 LRU。相对地，LOH-v7 为 0.312774/0.205810，BeladySize 为 0.308680/0.200234。这组结果不说明 oracle reuse objective 错，而说明实际 learned RD predictor 在 `meta_reag` 这种多维冲突负载上容易把预测误差放大为坏的 victim ranking。

更关键的是，`meta_reag` 不只是“难以取得好命中率”，而是提出了一个更具体的可验证假设：3LCache/LRB 这类对象级 future-value/ranking 目标，在该 trace 上可能比 RSD 的负载偏好目标更难稳定学习。3LCache/LRB 需要学习的是每个对象、每个访问时刻的 future interval/reuse time：命中样本用真实 future distance 作为标签，超过窗口阈值或 ghost/out-cache 过期的样本则直接被标成远未来/不再访问。代码中 LRB 的 timeout mature 会写入 `memory_window * 2` 或 `current_seq - past_timestamp + memory_window`，3LCache 的 ghost expire 会写入基于 `MAX_EVICTION_BOUNDARY` 的远未来标签。这个阈值化机制本身不是问题，它是 learned reuse predictor 处理远未来样本的合理方式；短复用、跨天复用和远未来对象共存也不必然难学，如果它们在模型可见特征空间里分得开，反而可以形成清晰监督信号。真正需要证明的难点是：在 `meta_reag` 上，这些 future-value 类别是否在 3LCache/LRB 使用的历史距离、频率、EDC、size 等特征空间中发生重叠，或者同一特征区域的 future label 是否随 phase、热点身份和对象大小结构变化。`meta_reag` 的 reuse p50=10s、p99=2.73d，`spread_log=9.973`，只能说明目标跨度很大；它本身不是充分证明，必须配合 feature-label separability 或 window-wise prediction error 分析。

RSD 的中间层学习目标则更低维也更平滑。它不要求判断“这个具体对象下一次何时回来”，而是判断“当前窗口里 recency、frequency、size 和交互项哪个更应该被放大”。这个目标由窗口级 MR/BMR 反馈给出，天然把许多对象级偶然性平均掉；大量冷对象不需要被分别预测为某个远未来距离，它们只通过窗口 miss/byte miss 的总体结果改变权重。换句话说，3LCache/LRB 学的是一个从对象历史特征到未来时间标签或阈值化远未来标签的高维映射；RSD 学的是一个从负载状态到少量权重的低维 preference。前者是否更难，要看 feature-label separability 和跨窗口泛化误差；后者虽然更粗粒度，但更接近“当前负载下哪类排序方向稳健”这个控制问题。

`meta_reag` 的样本结构会进一步拉开二者难度。top1 对象贡献 24.4% 请求、top1% 贡献 51.1%，同时 cold object ratio 均值 57.6%。对象级模型的训练样本会被超热对象和短复用样本强烈主导，但缓存容量压力又大量来自冷尾和大对象是否应被保留。也就是说，训练 loss 中最容易学到的是“少数热点的未来复用”，但 eviction 质量还取决于如何处理大量低频、大跨度、标签稀疏的对象。RSD 的负载偏好目标不需要给每个冷尾对象预测精确 future interval，只需要从窗口反馈中学到“当前应提高 frequency/size/recency 哪些方向”，因此对这种样本不均衡更不敏感。

非平稳性也让对象级 future-label 目标更难。`analysis/summary.json` 标记 `meta_reag` 的 distribution、identity、size 都是 unstable，top-k Jaccard mean 只有 0.2085；`meta_reag_access_vt.png` 也显示明显分层结构。对于对象级模型，同一组历史特征在不同 phase 下对应的未来复用可能不同，旧窗口学到的映射会直接污染当前 victim ranking。RSD 的权重目标则允许 phase 变化后把 preference 从一种信号组合切到另一种信号组合，而不是要求同一个 predictor 在所有 phase 上给出精确的对象级 future time。

最后，3LCache/LRB 的目标误差会在排序阶段被放大。3LCache 的 OMR 分支使用 `exp(score)`，BMR 分支使用 `size * exp(score)`；LRB 的 BMR 分支也会把 score 乘以 size。在 `meta_reag` 这种对象大小跨 1B 到 4.3GB、size_p99 窗口标准差达到 699.6MB 的 workload 上，小的 future-score 误差会被指数变换或 size scaling 放大成巨大的 eviction-score 差异。RSD 的 score 虽然也使用 size/frequency/recency，但它学习的是这些项的相对权重，并通过窗口级反馈纠偏；它不依赖一个精确对象级 future-time predictor 再把预测值指数化。因此，这里真正更难学的是 3LCache/LRB 的对象级、长尾、非平稳 future-value/ranking 目标，而 RSD 的负载偏好目标是低维、聚合反馈、可随窗口更新的控制目标。

因此，`meta_reag` 更适合支持下面这个、更精确的论点：RSD 的中间层并不是否定 reuse distance oracle；相反，它承认 reuse/frequency/size 都是有效信号，但不把某个固定代理目标强行绑定到所有窗口。RSD 学的是负载级 preference：在当前窗口中，recency、frequency、size 以及交互项应该如何平衡。已有 CMA-ES 演化日志也与此一致：`meta_reag` 的稳定收敛权重中 freq=0.92、freq_sq=0.85、size_ratio=0.71、recency_ratio=0.93，说明最优行为不是单独追逐 reuse、frequency 或 size，而是多信号共同参与。

这给论文中的 robustness 叙事提供了一个具体证据链：`meta_reag` 的 trace 图和统计证明负载存在多维冲突；learned RD baseline 在同一 trace 上退化，提示对象级 future-label 学习可能没有稳定对齐最终 eviction objective；LOH-v7/BeladySize 接近，说明 size-aware future information 是强上界；而 RSD/LOH 能接近该上界，说明中间层的候选与低维 preference 至少提供了一个更稳的适配路径。最终要证明“对象级目标更难学”，还需要补充 feature-label separability、window-wise prediction error 或同候选集 ranking regret 分析。

要证明“同一组历史特征在不同 phase 下对应的未来复用可能不同”，不能只引用 `access_vt` 图或 stationarity label；那些只能说明负载非平稳，不能直接说明 feature-label mapping 变了。更直接的验证应以 LRB/3LCache 的训练样本为单位，把每条样本表示成 `(feature_bin, phase_id, future_label)`：`feature_bin` 由模型可见特征分桶，例如 past distances、frequency/EDC、size；`phase_id` 用固定窗口（如每 1M 或 5M req）或按 access_vt/reqRate 变化切段；`future_label` 用真实 future distance 或远未来标签，也可以离散成 short/medium/far。然后做四类检验。

第一，做同一 feature bin 的跨 phase 标签分布漂移。对每个样本数足够的 bin，比较不同 phase 下 `P(future_label | feature_bin, phase)`；如果同一个 bin 在 phase A 中大多是 short reuse，在 phase B 中大多是 far/long reuse，说明仅凭该组历史特征无法得到稳定映射。可报告 JS divergence、Wasserstein distance、KS statistic，或更直观地报告 `P(short | bin, phase)` 的最大-最小差。

第二，做条件熵或互信息检验。比较 `H(Y | feature_bin)` 与 `H(Y | feature_bin, phase)`，或者计算 `I(Y; phase | feature_bin)`。如果加入 phase 后 future label 的不确定性显著下降，说明 phase 含有历史特征之外的标签信息，即 feature-label mapping 随 phase 变化。

第三，做 train-on-phase / test-on-phase 的泛化实验。用 phase A 的 3LCache/LRB 训练样本训练一个同结构或轻量替代模型，在 phase A 内测试、相邻 phase 测试、远端 phase 测试，比较 future-label RMSE/logloss、short/far 分类 AUC，以及基于预测分数的 candidate ranking regret。如果跨 phase 误差明显高于同 phase 随机切分误差，说明对象级预测目标存在 phase-specific mapping。

第四，做同候选集 ranking regret。固定一批 eviction candidate，把上一 phase 学到的对象级 predictor、当前 phase predictor、RSD/LOH score 和 oracle future/BeladySize 排序放在同一候选集上比较。若上一 phase predictor 在当前 phase 的 regret 明显升高，而 RSD 的窗口偏好能较快恢复，就能把“对象级目标更难学”连接到实际 eviction 结果，而不是只停留在标签统计上。

因此，当前文档中关于 `meta_reag` 的正确表述应是：现有 trace 图和 summary 已证明它具备多维冲突与非平稳性，表 12.3 已显示 learned RD baseline 在该 trace 上退化；但“同一历史特征跨 phase 对应不同 future reuse”仍是待验证机制。最合适的补充实验是 feature-label separability 与 cross-phase generalization，而不是继续只看最终 MR/BMR。

#### 12.4.1 合成 trace：phase-flip preference workload

为直接展示“对象级 future-value/ranking 目标比负载偏好目标更难学”的机制，可以设计一个专门的 phase-flip 合成 trace，而不是只依赖真实 trace 的事后解释。生成脚本为 `scripts/gen_phase_flip_preference_trace.py`，样例产物位于 `tmp/20260528-phase-flip-preference-trace/`。

这个 trace 交替生成两类 phase：

- `freq_preference` phase：小对象先连续访问 3 次，形成 `small_freq3` 特征桶；大对象只访问 1 次，形成 `large_freq1` 特征桶；经过一段 filler scan 后，只有 `small_freq3` 返回。因此该 phase 中应偏好 frequency/recency，保留小而高频的对象。
- `size_preference` phase：前半段仍生成相同的 `small_freq3` 与 `large_freq1` 特征桶；经过 filler scan 后，只有 `large_freq1` 返回。因此该 phase 中应偏好 size/byte value，保留大对象。

关键点是：该 trace 不是让所有算法都“看不懂”，而是让两种学习目标的难度差异可视化。对 3LCache/LRB 这类对象级 predictor 来说，如果输入只包含对象历史距离、频率、EDC、size 等对象局部特征，那么 `small_freq3` 和 `large_freq1` 两个 feature bin 在不同 phase 下对应相反的 future label：`P(short reuse | small_freq3, phase)` 在 frequency phase 为 1、size phase 为 0；`P(short reuse | large_freq1, phase)` 正好相反。没有 phase/context 时，单个对象级映射会看到同一 feature bin 的冲突标签；若模型用较长训练历史或全局模型，会倾向于学到平均化结果，从而在两个 phase 都排错一部分 victim。

对 RSD/LOH 的中间层来说，这个目标更简单：它不需要分别预测每个对象的 future interval，只需要在窗口级反馈中识别当前 phase 更偏 `frequency` 还是更偏 `size/byte value`。因此可视化上应出现两张图：

- `feature_label_flip_heatmap.png`：展示 `P(short reuse | feature bin, phase)` 的棋盘式翻转，用于证明对象级 feature-label mapping 随 phase 变化。
- `phase_preference_timeline.png`：展示 oracle workload preference 在 `frequency` 和 `size` 之间切换，用于说明中间层目标是低维 phase preference。

样例生成日志：`tmp/20260528-phase-flip-preference-trace/logs/generate.log`。默认样例包含 8 个 phase、307,200 条请求，足够画出目标结构；正式实验可以把 `--rounds-per-phase` 和 `--cycles` 放大，并用 `--trace-type-params "time-col=1,obj-id-col=2,obj-size-col=3,obj-id-is-num=1,has-header=0"` 运行 cachesim。

建议的验证口径如下。

1. Feature-label separability：直接用 metadata 画 `P(short reuse | feature_bin, phase)`，证明对象级目标在没有 phase/context 时不可由单一 feature bin 稳定决定。
2. Cross-phase prediction：用 phase A 的样本训练一个 LRB/3LCache 同类特征模型，在 phase A 与 phase B 上分别测试 future-label 分类/排序误差；如果跨 phase error 接近随机或明显高于同 phase error，说明对象级目标难学来自 phase-dependent mapping。
3. Same-candidate ranking regret：固定每轮 filler 后的候选集合，比较对象级 predictor、当前 phase oracle predictor、RSD/LOH score 与 oracle victim 排序的 regret。这个指标能把“目标难学”直接连接到 eviction 结果。
4. End-to-end cache result：在放大版 trace 上比较 LRU、Size、LRB-BMR、ThreeLCache-BMR/OMR、固定权重 LOH、动态 RSD/LOH。预期不是证明 Size 或 LFU 永远差，而是证明固定单目标和对象级 future predictor 在 phase flip 下更容易平均化；动态 preference 能在 phase 内恢复到接近当前 oracle preference。

这个合成 trace 的论文价值在于，它把“为什么中间层更好学”从文字论证变成可视化事实：对象级目标看到的是同一 feature bin 的 phase-dependent label，而中间层看到的是一个低维的 preference switch。

### 12.5 结论

这组计算给出的结论不是“reuse distance / reuse distance*size 一定不适合作为 learned cache 目标”。更准确的结论如下。

第一，plain reuse distance 作为唯一 eviction 指标不够鲁棒。主口径五组平均中，Belady 的 MR/LRU 是 0.896432，而 v7 是 0.731759，v7 明显更好；BMR/LRU 两者几乎持平，Belady 仅比 v7 高 0.000525。尤其在 metaKV 上，Belady 的 MR/LRU=1.370371、BMR/LRU=1.260194，说明只看下一次 reuse distance 会在某些 size/frequency 结构下严重失配。

第二，reuse distance*size 是很强的离线 proxy。主口径五组平均中，BeladySize 的 MR/LRU=0.657318、BMR/LRU=0.917987，都优于 v7 的 0.731759 和 0.936820。因此不能用这组离线结果来证明 `reuse distance*size` 这个目标本身不合适。相反，它说明如果能准确知道未来 reuse 并结合 size，目标上界很强。

第三，BeladySize 仍然不是全局无风险目标。metaKV 上 BeladySize 的 MR/LRU=0.531749 略好于 v7 的 0.557128，但 BMR/LRU=1.144305 明显差于 v7 的 0.963001。也就是说，`reuse distance*size` 可以改善平均，但在某些 workload 上会牺牲 byte miss。这正好支持 RSD 需要学习 preference：不同 workload 下，MR 与 BMR、future distance 与 object size 的权衡不应固定。

第四，这个实验更适合作为 learned-target 上界诊断，而不是在线算法公平对比。Belady/BeladySize 使用 oracle future information；3LCache/LRB 只能预测 reuse time/distance，预测误差、标签延迟、censoring 和 workload shift 都会让实际效果低于这个离线上界。因此论文里更稳的说法应是：

> Offline `reuse distance*size` is a strong proxy, but it is not uniformly aligned with both OMR and BMR across workloads. Plain reuse distance is clearly less robust. RSD does not claim that reuse-based targets are useless; instead, it learns a workload-specific preference over recency, frequency, size, and their interactions, which can avoid fixed proxy-objective failures such as the metaKV BMR degradation observed for BeladySize.

因此，若要证明 RSD 相比 3LCache/LRB 这类 learned algorithm 的效果原因，不能只说“reuse distance/reuse distance*size 不合适”。更准确的因果假设应改成：

1. `reuse distance` 单指标不足，已有 Belady 结果支持。
2. `reuse distance*size` 是强代理目标，但不是跨 workload、跨 OMR/BMR 都稳定对齐，metaKV BMR 反例支持。
3. RSD 的优势应表述为 learning a workload-specific preference，而不是否定 reuse-based oracle objective。
4. 后续最关键实验应比较 online learned prediction 与 oracle BeladySize 的 gap：如果 3LCache/LRB 明显低于 BeladySize 上界，而 RSD 接近或超过它们，说明问题来自代理目标的在线可学习性、预测误差和固定目标失配，而不是 oracle proxy 本身完全无效。
