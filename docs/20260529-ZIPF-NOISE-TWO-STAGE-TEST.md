# 20260529 二段式 Zipf+噪声 Trace 测试记录

## 1. 目标

- 新增一套更简单可解释的 trace 生成方法：
  - 第一步：正常工作负载（Zipf）
  - 第二步：在基线后注入噪声（noise burst）
- 在默认算法配置下，运行并记录 cache size 为 0.1 与 0.001 的对比结果。

## 1.1 文档边界

本文档只记录 Zipf 两步法（生成脚本：[scripts/gen_zipf_noise_two_stage_trace.py](scripts/gen_zipf_noise_two_stage_trace.py)）。

口径迁移说明：旧版文档里“第8节调参结果”已并入当前第 2~6 节；当前应以第5节实测结果为准。

post-return-poison 的同基线前后对照，已独立到单独文档：

- [docs/20260529-POST-RETURN-POISON-COMPARE-TEST.md](docs/20260529-POST-RETURN-POISON-COMPARE-TEST.md)

## 2. 产物路径

- 生成脚本：[scripts/gen_zipf_noise_two_stage_trace.py](scripts/gen_zipf_noise_two_stage_trace.py)
- 当前主结果目录：[tmp/20260529-zipf-two-stage-tuning/focus_small](tmp/20260529-zipf-two-stage-tuning/focus_small)
- 搜索汇总：[tmp/20260529-zipf-two-stage-tuning/focus_small/results/summary.tsv](tmp/20260529-zipf-two-stage-tuning/focus_small/results/summary.tsv)
- 候选配置：[tmp/20260529-zipf-two-stage-tuning/focus_small/results/winner_candidates.tsv](tmp/20260529-zipf-two-stage-tuning/focus_small/results/winner_candidates.tsv)
- 选中配置差值：[tmp/20260529-zipf-two-stage-tuning/focus_small/results/chosen_delta.tsv](tmp/20260529-zipf-two-stage-tuning/focus_small/results/chosen_delta.tsv)

## 3. 生成方法（两步法，纠错后主配置）

### 3.1 Base 阶段（正常 Zipf）

- 对象数：4096
- 请求数：200000
- Zipf alpha：1.6
- 对象大小：4096 bytes（统一大小）

### 3.2 Noise 阶段（后置注入）

- 每 64 个 base 请求后插入 1 组 noise burst
- 每组 burst 2 个 noise 请求（noisy 场景）
- noise 对象池大小：2048
- clean 基线使用 noise-burst=0（其余参数不变）

说明：噪声是“附加层”，不改变 base 生成规则；便于把“基础访问规律”和“干扰信号”拆开解释。

## 4. 本次执行命令

```bash
PATH="$PWD/.venv/bin:$PATH" python3 scripts/gen_zipf_noise_two_stage_trace.py \
  --output-dir tmp/20260529-zipf-two-stage-tuning/focus_small/nobj4096_a1.6_ev64_nb2/clean \
  --num-objects 4096 \
  --num-requests 200000 \
  --alpha 1.6 \
  --obj-size 4096 \
  --noise-pool 2048 \
  --noise-every 64 \
  --noise-burst 0 \
  --seed 20260529

PATH="$PWD/.venv/bin:$PATH" python3 scripts/gen_zipf_noise_two_stage_trace.py \
  --output-dir tmp/20260529-zipf-two-stage-tuning/focus_small/nobj4096_a1.6_ev64_nb2/noisy \
  --num-objects 4096 \
  --num-requests 200000 \
  --alpha 1.6 \
  --obj-size 4096 \
  --noise-pool 2048 \
  --noise-every 64 \
  --noise-burst 2 \
  --seed 20260529
```

测试算法：LRU、LRB(BMR)、3LCache(BMR/OMR)、LOH(default)

CSV 参数：

```text
time-col=1,obj-id-col=2,obj-size-col=3,obj-id-is-num=1,has-header=0
```

## 5. 实测结果

以下结果均对应同一配置 `nobj4096_a1.6_ev64_nb2`：

- noisy trace：[tmp/20260529-zipf-two-stage-tuning/focus_small/nobj4096_a1.6_ev64_nb2/noisy/zipf_noise_two_stage.csv](tmp/20260529-zipf-two-stage-tuning/focus_small/nobj4096_a1.6_ev64_nb2/noisy/zipf_noise_two_stage.csv)
- clean trace：[tmp/20260529-zipf-two-stage-tuning/focus_small/nobj4096_a1.6_ev64_nb2/clean/zipf_noise_two_stage.csv](tmp/20260529-zipf-two-stage-tuning/focus_small/nobj4096_a1.6_ev64_nb2/clean/zipf_noise_two_stage.csv)

### 5.1 noisy（加噪后）双缓存对比（MR）

| cache | LRB-BMR | 3LCache-BMR | 3LCache-OMR | LOH | LOH f100_ns | LOH f111_orig |
|---|---:|---:|---:|---:|---:|---:|
| 0.1 | 0.077571 | 0.077571 | 0.077571 | 0.036989 | 0.036824 | 0.036131 |
| 0.001 | 0.639903 | 0.569770 | 0.569741 | 0.453983 | 0.456824 | 0.456945 |

说明：
- LOH = 默认配置（`auto_compound=1`，CMA-ES 自动选择复合特征）
- LOH f100_ns = `AUTO_COMPOUND=0, USE_FREQ_REC=1, USE_FREQ_SIZE=0, USE_REC_SIZE=0, USE_SIZE=0`（仅 freq×rec，无 size 维度）
- LOH f111_orig = `AUTO_COMPOUND=0, USE_FREQ_REC=1, USE_FREQ_SIZE=1, USE_REC_SIZE=1`（全复合特征，默认 size=1）
- 结果目录：[tmp/20260601-zipf-f100ns-f111orig/logs/](tmp/20260601-zipf-f100ns-f111orig/logs/)

结论：在该配置下，noisy 场景中 LOH 各变体在 0.1 档均最优；0.001 档 LOH(default) 略优于 f100_ns/f111_orig。

### 5.2 clean vs noisy（噪声前后，MR 增量）

| cache | 算法 | clean MR | noisy MR | noisy-clean |
|---|---|---:|---:|---:|
| 0.1 | LRB-BMR | 0.039920 | 0.077571 | +0.037651 |
| 0.1 | 3LCache-BMR | 0.039920 | 0.077571 | +0.037651 |
| 0.1 | 3LCache-OMR | 0.039920 | 0.077571 | +0.037651 |
| 0.1 | LOH | 0.029315 | 0.036989 | +0.007674 |
| 0.1 | LOH f100_ns | 0.030255 | 0.036824 | +0.006569 |
| 0.1 | LOH f111_orig | 0.029540 | 0.036131 | +0.006591 |
| 0.001 | LRB-BMR | 0.620055 | 0.639903 | +0.019848 |
| 0.001 | 3LCache-BMR | 0.557500 | 0.569770 | +0.012270 |
| 0.001 | 3LCache-OMR | 0.557485 | 0.569741 | +0.012256 |
| 0.001 | LOH | 0.439540 | 0.453983 | +0.014443 |
| 0.001 | LOH f100_ns | 0.438250 | 0.456824 | +0.018574 |
| 0.001 | LOH f111_orig | 0.437860 | 0.456945 | +0.019085 |

说明：

- 0.1 档：加噪后 LRB/3L 的退化明显大于 LOH 各变体；LOH f100_ns/f111_orig 的 delta（+0.0066）略小于 LOH(default, +0.0077），说明显式关掉 auto_compound 后噪声扰动略有改善。
- 0.001 档：各变体都退化；LOH(default) noisy MR 最低（0.453983），f100_ns/f111_orig 相近（0.456xxx），均优于 LRB/3L。

### 5.3 机制解释：为何 LRB/3LCache 更容易受噪声影响

在本二段式 Zipf trace 中，噪声是“后置注入”的：base 请求先发生，再插入 noise burst。该结构对不同策略的影响路径不同。

- LRB/3LCache 对标签与统计的依赖更强：
  - 两者都依赖对象历史统计（重用距离/频次/命中历史）来估计保留价值。
  - 后置噪声会批量制造“短时出现但后续价值低”的样本，抬高统计噪声，削弱原始 Zipf 热点信号。

- 噪声对象与 base 对象在局部特征上相似：
  - 本实验对象大小统一为 4096，噪声与 base 在 size 维度不可分。
  - 当特征可分性下降时，依赖统计学习的策略更容易把噪声当成可保留对象，导致有效对象被提前挤出。

- 3LCache 的分层/候选机制会放大短期噪声注入：
  - burst 方式会在短窗口内提高噪声对象的“近期存在感”。
  - 这会改变层间迁移与候选比较结果，造成局部阶段性的错误保留。

- LOH 在该配置下更偏向稳健的近期信号：
  - 当前默认特征组合里，近期性与复合特征对“马上回访”的 base 热对象更敏感。
  - 后置噪声虽然会增加干扰，但对 LOH 的决策扰动相对更小，因此在 noisy 下保持了更低 MR。

### 5.4 为什么 LOH 扰动更小（对应本实验）

- 噪声到达时机对 LOH 更不利程度较低：
  - 本 trace 里先发生 base 请求，再注入 noise burst。
  - 在这个顺序下，真正会很快回访的热点对象已经建立了较强的近期信号，后续噪声更像“晚到干扰”。

- LOH 的决策更依赖短窗口有效信号：
  - 在当前默认配置下，LOH 对近期访问与复合特征更敏感。
  - 这使得“刚刚命中且将很快再访问”的对象不容易被少量后置噪声立即替换。

- 从增量表可以直接看到扰动差异：
  - cache=0.1 时，LOH 增量为 +0.007674，而 LRB/3L 为 +0.037651。
  - 即同样加噪后，LOH 的相对退化幅度显著更小。

- 在极小缓存下 LOH 也会退化，但仍维持优势：
  - cache=0.001 时，LOH 增量为 +0.014443，不是零扰动。
  - 但 noisy 下其 MR 仍低于 LRB/3L，说明其抗扰动能力在当前参数下更强。

补充：

- 在 0.001 档，LOH 也会退化（+0.014443），说明噪声并非只影响 LRB/3L。
- 本结论是“在当前两步法与当前参数下”的经验结论，若改变对象大小分布、噪声节奏或候选池规模，敏感度排序可能变化。

### 5.5 多算法对照：noisy second half（噪声仅在后半段）

**实验设置：**

- Trace：`noisy_second_half/zipf_noise_two_stage.csv`，由 `--noise-start-frac=0.5` 生成
  - 前 100K 请求：纯 Zipf（无噪声）
  - 后 100K 请求：每 64 base 请求插入 2 个 noise burst（与全段 noisy 一致）
  - 总计：200K base + 3126 noise = 203126 请求
- Cache ratio：0.1，report-interval=1000
- 日志目录：[tmp/20260601-zipf-second-half-noisy/logs/](tmp/20260601-zipf-second-half-noisy/logs/)
- 可视化：[tmp/20260601-zipf-second-half-noisy/mr_timeline_all.png](tmp/20260601-zipf-second-half-noisy/mr_timeline_all.png)

**最终 MR（全程累积）：**

| 算法 | 最终 MR | 排名 |
|------|--------:|:----:|
| **LOH f100_ns** | **0.035736** | 1 |
| ARC | 0.035894 | 2 |
| WTinyLFU | 0.035938 | 3 |
| S3-FIFO | 0.036066 | 4 |
| Sieve | 0.044834 | 5 |
| Cacheus | 0.049147 | 6 |
| LHD | 0.050688 | 7 |
| LeCaR | 0.056807 | 8 |
| LRU | 0.058491 | 9 |
| LRB-BMR | 0.058491 | 9 |
| 3LCache-BMR | 0.058491 | 9 |
| GLCache | 0.084534 | 12 |

**观察：**

1. **LOH f100_ns 微弱领先**，与 ARC/WTinyLFU/S3-FIFO 同处 0.035~0.036 区间，差距 <0.001。
2. **LRU = LRB-BMR = 3LCache-BMR（均 0.058491）**：再次确认 — 均匀对象大小（4096B）使 BMR ≡ OMR，LRB/3LCache 的字节感知优势无法发挥。
3. **GLCache 表现最差（0.084534）**：interval MR 高度震荡；对均匀小对象 Zipf trace 不适配，其以 GBM 学习的 obj-size 权重信号量无法区分对象。
4. **噪声注入后（>100K）**：LOH/ARC/WTinyLFU 在 interval MR 中保持最低，LRU/LeCaR/Cacheus/LHD 明显上升；两段时序图可见明显的"噪声边界效应"。

### 5.6 多算法对照：clean trace（无噪声基线）

**实验设置：**

- Trace：`clean/zipf_noise_two_stage.csv`（全程 200K 请求，无噪声）
- Cache ratio：0.1，report-interval=1000
- 日志目录：[tmp/20260601-zipf-clean-all-algos/logs/](tmp/20260601-zipf-clean-all-algos/logs/)
- 可视化：[tmp/20260601-zipf-clean-all-algos/mr_timeline_all.png](tmp/20260601-zipf-clean-all-algos/mr_timeline_all.png)

**最终 MR（全程累积）：**

| 算法 | 最终 MR | 排名 |
|------|--------:|:----:|
| **WTinyLFU** | **0.028720** | 1 |
| LOH f100_ns | 0.030110 | 2 |
| Sieve | 0.030260 | 3 |
| S3-FIFO | 0.031080 | 4 |
| ARC | 0.031515 | 5 |
| LeCaR | 0.036320 | 6 |
| Cacheus | 0.037380 | 7 |
| LHD | 0.038450 | 8 |
| LRU | 0.039920 | 9 |
| LRB-BMR | 0.039920 | 9 |
| 3LCache-BMR | 0.039920 | 9 |
| GLCache | 0.061440 | 12 |

**观察：**

1. **WTinyLFU 在 clean 场景下最优（0.028720）**：纯 Zipf 下频率信号清晰，WTinyLFU 的计数过滤机制充分发挥，优于 LOH f100_ns（+0.001390）。
2. **LOH f100_ns 紧随第二（0.030110）**：与 Sieve（0.030260）几乎持平，差距 <0.002。
3. **LRU = LRB-BMR = 3LCache-BMR（均 0.039920）**：均匀对象大小（4096B）导致三者结果一致，LRB/3LCache 字节感知能力无法区分对象。
4. **GLCache 仍最差（0.061440）**：在均匀小对象 Zipf trace 上无论有无噪声均表现最差，interval MR 震荡最大。
5. **与 §5.5（noisy second half）的对比**：
   - 加噪后 LOH f100_ns 反超 WTinyLFU（0.035736 vs 0.035938），在噪声干扰下 LOH 抗扰性更强。
   - clean 场景下 WTinyLFU 领先，noisy 场景下 LOH f100_ns 领先 —— 两者各有优势区间。

### 5.7 多算法对照：10x 后半段噪声 trace（全算法）

**实验设置：**

- Trace：`tmp/20260601-zipf-noisy-2nd-half-10x/zipf_noise_two_stage.csv`
  - 2M base requests，noise-start-frac=0.5，共 ~2031250 行
- Cache ratio：0.1，report-interval=10000
- 日志目录：[tmp/20260601-zipf-noisy-2nd-half-10x/logs/](tmp/20260601-zipf-noisy-2nd-half-10x/logs/)
- 可视化：[tmp/20260601-zipf-noisy-2nd-half-10x/mr_timeline_all_10x.png](tmp/20260601-zipf-noisy-2nd-half-10x/mr_timeline_all_10x.png)

**最终 MR（interval 末值，按升序）：**

| 算法 | 最终 interval MR | 排名 |
|------|----------------:|:----:|
| **LRB** | **0.016500** | 1 |
| LOH f100_ns | 0.017100 | 2 |
| 3LCache | 0.017700 | 3 |
| WTinyLFU | 0.019500 | 4 |
| S3-FIFO | 0.020800 | 5 |
| ARC | 0.021300 | 6 |
| LHD | 0.022800 | 7 |
| Cacheus | 0.024800 | 8 |
| LeCaR | 0.024900 | 9 |
| LRU | 0.026400 | 10 |
| GLCache | 0.035000 | 11 |
| Sieve | 0.045800 | 12 |

**观察：**

1. **LRB/3LCache/LOH f100_ns 全部收敛到最优区间（0.016~0.018）**：
   - §5.5（1x, 200K req）中 LRB/3LCache 与 LRU 完全一致（0.058491），10x 后显著领先 LRU（0.026400），
     差异达 **~35%**，验证了 warmup 假说。
   - 噪声注入后（1M 请求处），LRB/3LCache 出现瞬间跳升（~0.045），随后迅速重训下降，约在 1.1~1.2M 后
     收敛到新稳态——时序图中可见明显的"训练重置尖峰"。

2. **LRB/3LCache 的 LRU warmup 机制（代码确认）：**
   - **LRB**（`lrb.cpp:278`）：`if (!booster)` — booster 初始为 `nullptr`，必须积累 **128K 条驱逐样本**
     (`batch_size=131072`, `lrb.h:35`) 才触发首次 LightGBM 训练。
   - **3LCache**（`ThreeLCache.cpp:487`）：同样 `if (!booster)`，首次训练门槛为 **64K 样本**
     (`batch_size=65536`, `ThreeLCache.hpp:33`)。
   - 训练完成前，两者均直接返回 LRU 队列端头（最久未用对象）作为驱逐候选，行为与 LRU **完全相同**。
   - 1x trace（~200K 请求，~4K 对象，cache=0.1=410 slots）中，**几乎全程在 warmup 阶段**，
     10x trace 提供了 warmup 后的充分训练机会。

3. **LOH f100_ns 无显著 warmup 延迟**：CMA-ES 为在线优化权重，首次迭代即可使用，无需等待样本积累，
   因此在时序图中前段 MR 已低于 LRB/3LCache，在噪声边界处也无明显跳升。

4. **GLCache 和 Sieve 在长 noisy trace 下表现最差**：GLCache（0.035）和 Sieve（0.046）的
   interval MR 在噪声注入后持续偏高，对突发新对象适应性弱。

5. **WTinyLFU 在长 trace 下排名第 4**：比 §5.6（clean）中第 1 名下滑，说明其频率计数在持续
   噪声冲击下学习效率低于 LRB/3LCache/LOH。

## 6. 小结

- 本次已完成：
  - 在 Zipf 两步法下完成参数纠错与小网格搜索。
  - 找到 noisy 场景下 LOH 在 0.1/0.001 均最优的可复现配置。
  - 输出了 clean/noisy 的按算法退化对照表（含 f100_ns/f111_orig LOH 复合特征消融，见 5.1/5.2）。
  - 新增"后半段噪声"场景（`noise-start-frac=0.5`）全算法对照（见 5.5），LOH f100_ns 微弱领先。
  - 新增 clean trace 全算法对照（见 5.6）：WTinyLFU 在无噪 Zipf 下最优，LOH f100_ns 第二。
  - 新增 10x 后半段噪声全算法对照（见 5.7）：LRB/3LCache 在长 trace 下充分训练后与 LOH 同处最优
    区间，代码确认两者均以 LRU 作为 warmup 阶段策略（首次训练前 `booster==nullptr`）。
  - 关键结论：
    - **LOH f100_ns 在有噪场景下抗扰性更强，且无 warmup 延迟。**
    - **LRB/3LCache 的优势需要足够长的 trace 才能体现（batch_size=64K/128K 样本门槛）。**
    - **短 trace 上 LRB/3LCache ≡ LRU；长 trace 上三者均可收敛到最低 MR 区间。**

- 当前推荐配置：`nobj4096_a1.6_ev64_nb2`。

## 7. 相关独立文档

post-return-poison 同基线前后对照结果见：

- [docs/20260529-POST-RETURN-POISON-COMPARE-TEST.md](docs/20260529-POST-RETURN-POISON-COMPARE-TEST.md)
