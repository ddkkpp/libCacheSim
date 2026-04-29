# alibabaBlock 的 MR 加权相对 LRU 比例分解

## 背景

在 [docs/20260415-ablation-per-group/cmaes版本LOH/robustness_summary_v4.md](docs/20260415-ablation-per-group/cmaes版本LOH/robustness_summary_v4.md#L247) 的 “MR 加权相对LRU比例 — 各组排名详情” 中，best_LOH 在 alibabaBlock 上是第 9 名，见 [docs/20260415-ablation-per-group/cmaes版本LOH/robustness_summary_v4.md](docs/20260415-ablation-per-group/cmaes版本LOH/robustness_summary_v4.md#L251)。

对应的组级原始值在 [docs/20260415-ablation-per-group/cmaes版本LOH/baseline_summary_v4.md](docs/20260415-ablation-per-group/cmaes版本LOH/baseline_summary_v4.md#L177)：

- alibabaBlock 的 best_LOH = 1.0588
- 同行 LHD = 0.8575，Cacheus = 0.9858，LeCaR = 0.9782

因此这个排名不是汇总脚本错误，而是该指标下的真实结果。

## 分解方法

该指标定义为：对每条 trace 先计算 MR(best_LOH) / MR(LRU)，再按 n_req 加权平均。

本次分解直接复用了 [tmp/gen_v4_summaries.py](tmp/gen_v4_summaries.py#L259) 与 [tmp/gen_v4_summaries.py](tmp/gen_v4_summaries.py#L339) 的解析与聚合逻辑，分析日志保存在 [tmp/20260421-alibaba-contrib/logs/alibaba_mr_wrel_breakdown.log](tmp/20260421-alibaba-contrib/logs/alibaba_mr_wrel_breakdown.log)。

## 总体结论

- alibabaBlock 的 MR 加权相对 LRU 比例为 1.058763
- 总净抬升量只有 +0.058763
- 但其中 alibabaBlock_10 单条 trace 就贡献了 +0.247621
- 也就是说，alibabaBlock_10 单独带来的正向抬升，约为最终净抬升的 4.21 倍
- 其余大流量 trace 大多是负贡献，只是没能完全抵消 alibabaBlock_10

换句话说，这不是“很多大流量 trace 都略差一点”的情况，而是“一个超大流量异常主导项，把整体均值直接拉到 1 以上”。

## 主要抬升来源

### 1. alibabaBlock_10 是决定性主因

元数据见 [docs/20260415-ablation-per-group/cmaes版本LOH/alibabaBlock.md](docs/20260415-ablation-per-group/cmaes版本LOH/alibabaBlock.md#L32)：

- n_req = 2,756,726,994
- 权重 = 0.136249
- r1 = 0.9773，r2 = 0.7213

按 v4 规则，r1 <= 0.98 且 r2 <= 0.98，因此该 trace 选择 f011。对应 MR cfg 行见 [docs/20260415-ablation-per-group/cmaes版本LOH/alibabaBlock.md](docs/20260415-ablation-per-group/cmaes版本LOH/alibabaBlock.md#L1037)。

对应 baseline MR 行见 [docs/20260415-ablation-per-group/cmaes版本LOH/alibabaBlock.md](docs/20260415-ablation-per-group/cmaes版本LOH/alibabaBlock.md#L3053)：

- best_LOH = 0.096919
- LRU = 0.034400
- 比值 = 2.8174
- 加权抬升 = 0.136249 x (2.8174 - 1) = +0.247621

这是全组唯一一个真正决定总体排序的样本。

### 2. alibabaBlock_4 只有很弱的附加抬升

元数据见 [docs/20260415-ablation-per-group/cmaes版本LOH/alibabaBlock.md](docs/20260415-ablation-per-group/cmaes版本LOH/alibabaBlock.md#L465)。

对应 MR cfg 行见 [docs/20260415-ablation-per-group/cmaes版本LOH/alibabaBlock.md](docs/20260415-ablation-per-group/cmaes版本LOH/alibabaBlock.md#L1470)，该 trace 的 v4 选择值为 0.033094。

对应 baseline MR 行见 [docs/20260415-ablation-per-group/cmaes版本LOH/alibabaBlock.md](docs/20260415-ablation-per-group/cmaes版本LOH/alibabaBlock.md#L3486)：

- n_req = 1,576,134,095
- 权重 = 0.077899
- best_LOH = 0.033094
- LRU = 0.031700
- 比值 = 1.0440
- 加权抬升 = +0.003426

它是第二大正贡献项，但量级已经比 alibabaBlock_10 小了两个数量级。

### 3. 其余正贡献项几乎都可以忽略

从 [tmp/20260421-alibaba-contrib/logs/alibaba_mr_wrel_breakdown.log](tmp/20260421-alibaba-contrib/logs/alibaba_mr_wrel_breakdown.log) 可见：

- 第 3 名 alibabaBlock_64 仅 +0.000927
- 第 4 名 alibabaBlock_810 仅 +0.000284
- ratio > 1 的 trace 一共只有 19 条
- 这 19 条 trace 的总权重为 0.235494
- 这 19 条 trace 的总正向抬升为 +0.252975

其中绝大部分正向抬升都来自 alibabaBlock_10。

## 主要抵消来源

虽然 alibabaBlock_10 把整体值抬高了，但大量高流量 trace 实际上在帮 best_LOH 往下拉。

最强的负贡献项包括：

- alibabaBlock_740: delta = -0.016831
- alibabaBlock_124: delta = -0.011271
- alibabaBlock_206: delta = -0.011151
- alibabaBlock_225: delta = -0.009789
- alibabaBlock_40: delta = -0.009654
- alibabaBlock_7: delta = -0.009594
- alibabaBlock_38: delta = -0.008219，源行见 [docs/20260415-ablation-per-group/cmaes版本LOH/alibabaBlock.md](docs/20260415-ablation-per-group/cmaes版本LOH/alibabaBlock.md#L342)、[docs/20260415-ablation-per-group/cmaes版本LOH/alibabaBlock.md](docs/20260415-ablation-per-group/cmaes版本LOH/alibabaBlock.md#L1347)、[docs/20260415-ablation-per-group/cmaes版本LOH/alibabaBlock.md](docs/20260415-ablation-per-group/cmaes版本LOH/alibabaBlock.md#L3363)
- alibabaBlock_225: 源行见 [docs/20260415-ablation-per-group/cmaes版本LOH/alibabaBlock.md](docs/20260415-ablation-per-group/cmaes版本LOH/alibabaBlock.md#L160)、[docs/20260415-ablation-per-group/cmaes版本LOH/alibabaBlock.md](docs/20260415-ablation-per-group/cmaes版本LOH/alibabaBlock.md#L1165)、[docs/20260415-ablation-per-group/cmaes版本LOH/alibabaBlock.md](docs/20260415-ablation-per-group/cmaes版本LOH/alibabaBlock.md#L3181)

如果没有这些负贡献项，总体值会更高；只是它们仍然不足以抵消 alibabaBlock_10 的超大正贡献。

## 一个更直观的判断

- 当前总体值 = 1.058763
- 总净抬升量 = +0.058763
- 单独去掉 alibabaBlock_10 的贡献后，总体值会降到约 0.811142

这说明：

- alibabaBlock 上 best_LOH 在这个指标变差，并不是组内普遍退化
- 真正的根因是少数超大流量 trace，尤其是 alibabaBlock_10
- 因此“其他表常常第一，但这个表第九”是完全可能的，因为这个指标对超大 n_req trace 极端敏感

## 结论

alibabaBlock 在 MR 加权相对 LRU 比例上的 rank 9 是对的。根因不是汇总表算错，而是：

- alibabaBlock_10 的流量权重极大
- 它在该指标上的 LOH/LRU 比值高达 2.8174
- 这个单点异常足以压过大量其他 trace 的改进

因此，这个指标更像是在回答“面对超大流量 trace，best_LOH 相对 LRU 是否稳健”，而不是“平均意义上 MR 是否更优”。
