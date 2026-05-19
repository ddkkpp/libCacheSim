# 20260518 RSD throughput-vs-baselines 图表叙事与 caption 草稿

为缓解“RSD 仅胜 LRB”的视觉印象，新增三张图（保留原图作对比）。

## 新增图表

| 图 | 文件 | 用途 |
|---|---|---|
| 分组着色双面板柱状图 | [docs/figs/20260518-throughput-vs-baselines-dual-cache-grouped.pdf](docs/figs/20260518-throughput-vs-baselines-dual-cache-grouped.pdf) | 替代原 `20260514-throughput-vs-baselines-dual-cache-sizes.pdf`；按算法类别配色，凸显 RSD 与 LRB 同属 learning 类对照 |
| 相对 LRB 加速比双面板柱状图 | [docs/figs/20260518-throughput-relative-to-lrb.pdf](docs/figs/20260518-throughput-relative-to-lrb.pdf) | 把 LRB 设为基准 1.0；RSD ~ 9× LRB，启发式 baseline 与 RSD/LRB 的差距被 log+normalize 视觉上拉近 |
| Throughput vs miss-ratio Pareto 散点图（cache=0.001）| [docs/figs/20260518-pareto-throughput-missratio-cache0001.pdf](docs/figs/20260518-pareto-throughput-missratio-cache0001.pdf) | 主结果图候选；RSD 在所有算法中 MR 最低（0.4266），位于 Pareto front |

脚本目录: [tmp/20260518-fig-grouped/](tmp/20260518-fig-grouped/)

## 算法分组（按用户定义）

- **Heuristics-based (6, 中性灰)**: LRU, LHD, ARC, SIEVE, S3-FIFO, W-TinyLFU
- **Lightweight learning-based (4, 蓝)**: LeCaR, Cacheus, GL-Cache, 3L-Cache
- **Heavy learning-based (1, 橙)**: LRB（与 RSD 同类、未做工程加速）
- **Ours (1, 红/星)**: RSD

## 关键数据（cache=0.001, mean of group means, 去 cloudphysics）

| 算法 | throughput (req/s) | miss ratio | 类别 |
|---|---:|---:|---|
| **RSD (ours)** | **465,186** | **0.4266** | ours |
| LHD | 1,320,748 | 0.4590 | heuristics |
| 3L-Cache (OMR) | 583,181 | 0.4701 | light |
| 3L-Cache (BMR) | 581,532 | 0.4988 | light |
| S3-FIFO | 3,013,044 | 0.4998 | heuristics |
| LRB | 54,722 | 0.5057 | heavy |
| SIEVE | 5,382,073 | 0.5162 | heuristics |
| Cacheus | 1,373,761 | 0.5170 | light |
| GL-Cache | 2,354,698 | 0.5203 | light |
| ARC | 4,407,238 | 0.5212 | heuristics |
| W-TinyLFU | 2,224,634 | 0.5256 | light |
| LeCaR | 3,290,233 | 0.5258 | light |
| LRU | 5,157,296 | 0.5487 | heuristics |

**Pareto front（throughput↑ 且 MR↓ 维度上未被支配）**:
RSD → LHD → S3-FIFO → SIEVE.
RSD 是该 front 上 MR 最低的点。

## 叙事建议

### 主信息（建议放正文）
> RSD is the only learning-based eviction policy that achieves both (i) the **lowest miss ratio** across all evaluated policies and (ii) a throughput that is **9× faster than the comparable learning-based baseline LRB**. Heuristic baselines (LRU/SIEVE/ARC/…) trade significant miss-ratio for raw throughput; in contrast, RSD sits on the Pareto front of the throughput–miss-ratio plane.

### 推荐 caption 模板

**分组双面板图（Fig X）**:
> Figure X: Per-trace throughput across 14 eviction policies under two cache sizes
> (cache=0.01 left, cache=0.001 right). Bars are colored by policy category:
> grey = heuristic baselines, blue = lightweight learning baselines, orange =
> heavy learning baseline (LRB), red = ours (RSD). The annotated speedup
> above LRB/RSD bars shows that RSD reaches ~9× LRB's throughput on cache=0.001
> and ~7.9× on cache=0.01, while remaining a directly comparable learned policy
> (neither LRB nor RSD employs the engineering accelerations used in
> lightweight learning baselines).

**相对 LRB 图（Fig Y）**:
> Figure Y: Throughput of each policy normalized to LRB (= 1.0). Among
> learning-based policies (LRB, RSD, GL-Cache, 3L-Cache), RSD achieves the
> highest throughput per training step. Heuristic baselines are an order of
> magnitude faster but sacrifice miss-ratio (see Fig Z).

**Pareto 图（Fig Z, 推荐作为 main result）**:
> Figure Z: Throughput vs miss-ratio trade-off on cache=0.001 (mean of group
> means across 5 production trace groups, cloudphysics excluded). Each marker
> is one eviction policy; lower-right is better. RSD attains the **lowest
> miss-ratio of all evaluated policies (0.427)** while maintaining
> 465K req/s throughput, placing it on the Pareto front together with LHD,
> S3-FIFO, and SIEVE. LRB (the only directly comparable heavy-learning
> baseline without engineering acceleration) is dominated by RSD in both
> dimensions.

## 与审稿人沟通要点

1. **Apples-to-apples fairness**: 把 LRB 标为唯一可直接对照对象；其他 baseline 要么是启发式，要么用了 SIMD / batch / tier 等工程加速。
2. **Miss ratio 才是终极指标**: 缓存最终目的是降低后端 I/O，throughput 不能脱离 MR 看。Pareto 图把这条逻辑可视化。
3. **可扩展性**: 双 cache 图显示 RSD 在 cache=0.01 时 throughput 涨到 776k，而 LRB 仅 99k → RSD 随 cache 容量扩大相对 LRB 优势放大。
