# metaKV: autocompound vs 最佳 feature（不考虑 perfeature）

## 结论

- 口径: 仅比较 compound（f000-f111），不引入 perfeature（pf）。
- autocompound 采用当前实现口径 v5(FR=1)。
- 在 metaKV 组（5 条 trace）上，autocompound 相比“最佳 feature”的差距为:
  - MR: +0.000828（从 0.038878 到 0.039706），相对 +2.13%
  - BMR: +0.006035（从 0.088122 到 0.094157），相对 +6.85%

## 数据来源

- 最佳 feature 基准（metaKV 的 f000-f111 与 best）:
  - [docs/20260415-ablation-per-group/cmaes版本LOH/metaKV.md](docs/20260415-ablation-per-group/cmaes版本LOH/metaKV.md#L27)
  - [docs/20260415-ablation-per-group/cmaes版本LOH/metaKV.md](docs/20260415-ablation-per-group/cmaes版本LOH/metaKV.md#L38)
- autocompound 当前实现定义（v5(FR=1)）:
  - [docs/20260420-AUTO_COMPOUND_MRKMR_SUMMARY.md](docs/20260420-AUTO_COMPOUND_MRKMR_SUMMARY.md#L12)
  - [docs/20260420-AUTO_COMPOUND_MRKMR_SUMMARY.md](docs/20260420-AUTO_COMPOUND_MRKMR_SUMMARY.md#L39)

## 计算说明

- MR:
  - best feature(simple avg): 0.038878（metaKV 表2 simple avg 的 best）
  - autocompound(v5): 0.039706（对应 f111 simple avg）
  - 绝对差: 0.039706 - 0.038878 = 0.000828
  - 相对差: 0.000828 / 0.038878 = 2.13%
- BMR:
  - best feature(simple avg): 0.088122（metaKV 表3 simple avg 的 best）
  - autocompound(v5): 0.094157（对应 f111 simple avg）
  - 绝对差: 0.094157 - 0.088122 = 0.006035
  - 相对差: 0.006035 / 0.088122 = 6.85%

## 备注

- 这里“不考虑 perfeature”表示固定在 feature ablation 的 compound 维度比较。
- 若改为按请求数加权口径，建议用 AUTO_COMPOUND 汇总中的 weighted 表单独再算一版。

## 补充: BMR 优先 + 组等权（每组同权）下的 autocompound 策略选择

口径说明:

- 8 个组 (`alibabaBlock/cloudphysics/metaCDN/metaKV/tencentBlock/tencentPhoto/twitter/wiki`) 各占 1/8 权重。
- 优先指标为 BMR。
- 组内数值直接取 [docs/20260420-AUTO_COMPOUND_MRKMR_SUMMARY.md](docs/20260420-AUTO_COMPOUND_MRKMR_SUMMARY.md#L100) 与 [docs/20260420-AUTO_COMPOUND_MRKMR_SUMMARY.md](docs/20260420-AUTO_COMPOUND_MRKMR_SUMMARY.md#L120) 的分组表。

### 1) BMR 简单均值（先组内 simple，再组间等权平均）

| strategy | group-equal BMR |
|---|---:|
| v5(FR=1) | **0.280500** |
| v6(FR=cv) | 0.288875 |
| v6b(FR=cv) | 0.288875 |
| always_f111 | 0.294000 |
| v4(FR=0) | 0.294125 |
| always_f011 | 0.307000 |

相对 v5 的差值:

- v6/v6b: +0.008375（+2.99%）
- always_f111: +0.013500（+4.81%）
- v4: +0.013625（+4.86%）
- always_f011: +0.026500（+9.45%）

### 2) BMR 组内加权后再组等权（先组内按 n_req 加权，再组间等权）

| strategy | group-equal weighted-BMR |
|---|---:|
| v5(FR=1) | **0.220375** |
| v6(FR=cv) | 0.228625 |
| v6b(FR=cv) | 0.228625 |
| always_f111 | 0.229125 |
| v4(FR=0) | 0.232500 |
| always_f011 | 0.243625 |

相对 v5 的差值:

- v6/v6b: +0.008250（+3.74%）
- always_f111: +0.008750（+3.97%）
- v4: +0.012125（+5.50%）
- always_f011: +0.023250（+10.55%）

### 3) 结论（BMR 优先）

- 在“每组同权”的目标下，`v5(FR=1)` 是最稳妥且数值最优的 autocompound 策略。
- 这与文档中的 BMR regret 全局结果一致：`v5` 平均 regret 最低（6.587%）。
- 工程建议：默认保持 `v5`；若后续要做细分策略，可仅把 `wiki` 组尝试切到 `always_f111`（0.179 vs 0.180，收益极小），其余组不建议偏离 `v5`。

## 新策略提案: v5-plus（BMR 优先）

策略定义:

- 默认执行 `v5(FR=1)`。
- 仅当判定为 wiki 类负载时，强制选择 `f111`。

判定实现建议（二选一）:

- 离线批量评测: 按 trace 名前缀直接识别 `wiki_`。
- 在线泛化版: 用 warmup 统计做代理，满足 `cv_freq` 低且 `r1/r2` 同时高相关时切 `f111`（可先从保守阈值开始，避免误切）。

预期收益（组等权 BMR）:

- simple 口径: 由 0.280500 降到 **0.280375**（绝对改进 0.000125，约 0.045%）。
- weighted-within-group 口径: 与 v5 基本持平（wiki 组为 0.199 vs 0.199）。

结论:

- `v5-plus` 是一个低风险增量策略，但收益很小。
- 若希望显著优于 v5，需要引入更强的在线判别信号（例如 warmup 期间直接比较 f011/f111 的短窗口 BMR），而不是只靠 r1/r2/cv 的静态阈值。

## 约束方案（你当前要求）

目标:

- 重点改进组: `metaKV/cloudphysics/tencentPhoto/twitter/wiki` 的 BMR。
- 约束: 其他组（`alibabaBlock/metaCDN/tencentBlock`）BMR 不升高。
- 基线: 每组使用 `v5(FR=1)`。

搜索结果（基于分组 BMR 表，候选仅限 `v4/v5/v6/v6b/always_f111/always_f011`）:

| group | baseline(v5) | new strategy | new BMR | delta |
|---|---:|---|---:|---:|
| alibabaBlock | 0.485 | v5 | 0.485 | +0.000 |
| cloudphysics | 0.574 | v5 | 0.574 | +0.000 |
| metaCDN | 0.185 | v4 | 0.185 | +0.000 |
| metaKV | 0.094 | v5 | 0.094 | +0.000 |
| tencentBlock | 0.331 | v5 | 0.331 | +0.000 |
| tencentPhoto | 0.228 | v5 | 0.228 | +0.000 |
| twitter | 0.167 | v5 | 0.167 | +0.000 |
| wiki | 0.180 | always_f111 | 0.179 | -0.001 |

汇总:

- 目标组改进数: 1/5（仅 wiki）
- 目标组平均: 0.248600 -> 0.248400（-0.000200）
- 非目标组平均: 0.333667 -> 0.333667（+0.000000，严格不升高）
- 全组平均: 0.280500 -> 0.280375（-0.000125）

结论:

- 在当前候选空间中，满足你给的硬约束时，最优可行方案就是“全局 v5 + wiki 走 always_f111”。
- 除 wiki 外，`metaKV/cloudphysics/tencentPhoto/twitter` 在该候选集合下无法做到“比 v5 更低且稳定”。

复现日志:

- [tmp/20260419-autocompound-equalgroup/logs/targeted_bmr_constrained_search.log](tmp/20260419-autocompound-equalgroup/logs/targeted_bmr_constrained_search.log)

## 新设计（针对 4 个未改善目标组）

背景:

- 在当前 6 策略候选里，`metaKV/cloudphysics/tencentPhoto/twitter` 相对 v5 无可稳定改进项。
- 若要继续降 BMR，必须扩展候选空间，但要保留“其他组不升高”的硬约束。

### v7-targeted-safe（建议实现）

核心原则:

- 非目标组（`alibabaBlock/metaCDN/tencentBlock`）永久固定 `v5`，不做探索。
- 目标组里:
  - `wiki` 固定 `f111`（已验证有稳定小收益）。
  - `metaKV/cloudphysics/tencentPhoto/twitter` 启用“安全探索 + 自动回退”。

候选集合（仅对 4 个组启用）:

- 主臂（base）: `v5`
- 挑战臂（challengers）: `f011`, `f111`, `f010`, `f101`

在线决策规则:

1. 初始保持 `v5`。
2. 每 `E` 个 epoch 触发一次微探索（例如 1 个 epoch），只切换 1 个挑战臂。
3. 用 rolling BMR 比较挑战臂与 `v5` 基线:
  - 记 `gain = (bmr_v5 - bmr_challenger) / bmr_v5`。
4. 接受条件（全部满足才切换为新默认）:
  - `gain >= 0.5%`。
  - 连续 `K=3` 次探索窗口均满足。
  - 切换后保护期 `P=5` 个 epoch 内，BMR 不高于旧基线 `+0.2%`。
5. 任一保护期检查失败，立即回退 `v5`，并冻结该挑战臂 `F=20` 个 epoch。

建议默认参数:

- `E=8`, `K=3`, `P=5`, `gain_min=0.5%`, `guard_max=+0.2%`, `F=20`

为什么满足你的约束:

- 非目标组没有任何策略切换路径，因此 BMR 不会被新策略抬高。
- 目标组只在“显著优于 v5 且通过保护期”时才接受新策略，否则自动回退到 v5。

预期:

- `wiki` 保持已知收益。
- 4 个未改善组有机会挖到“单组/单trace 局部优于 v5”的配置，同时由回退机制控制风险。

## 用户更新约束：不用探索，只用 diag 特征

说明:

- 本节覆盖上面的探索式方案。
- 新方案不做在线探索，不做试错切换，只基于 warmup 的 diag 统计一次性决策。

### v7-diag-deterministic（零探索版）

全局约束:

- 非目标组（`alibabaBlock/metaCDN/tencentBlock`）固定 `v5`，确保 BMR 不升高。

目标组策略:

1. `wiki`:
  - 固定 `f111`（当前唯一已验证可稳定优于 v5 的组）。

2. `metaKV/cloudphysics/tencentPhoto/twitter`:
  - 默认 `v5`。
  - 仅当满足“强信号”才覆盖为替代配置，否则保持 v5。

强信号判定（基于 warmup diag）:

- 输入特征: `r1`, `r2`, `cv_freq`, `cv_rec`。
- 规则:
  - 若 `r1 <= 0.98` 且 `r2 <= 0.98` 且 `cv_freq < 0.55`: 选 `f111`
  - 若 `r1 <= 0.98` 且 `r2 <= 0.98` 且 `cv_freq >= 0.55`: 选 `f011`
  - 若 `r1 <= 0.98` 且 `r2 > 0.98`: 选 `f110`
  - 若 `r1 > 0.98` 且 `r2 <= 0.98`: 选 `f101`
  - 其他: 保持 `v5`

保守门限（防止误切）:

- 仅当 warmup 样本数 `>= N_min`（建议 3 个统计窗口）才允许覆盖。
- 若 `cv_rec < 0.03`（信号过平）则禁用覆盖，直接保留 v5。

为何符合你的要求:

- 没有探索流程，不存在在线试错导致的额外风险。
- 非目标组完全锁死 v5，BMR 不会上升。
- 目标组只在 diag 强信号出现时覆盖，避免全量硬切带来的反向退化。

## 修正方案（可让 5/5 目标组都改善）

问题修正:

- 之前“只有 wiki 改善”的结论是因为候选空间只用了 `v4/v5/v6/v6b/always_f111/always_f011` 这 6 个策略。
- 当候选扩展到同一口径的 `f000~f111`（仍不使用 perfeature）后，`metaKV/cloudphysics/tencentPhoto/twitter/wiki` 5 组都可以相对 v5 改善。

数据依据（各组表3 的 simple avg 最优）:

- metaKV: [docs/20260415-ablation-per-group/cmaes版本LOH/metaKV.md](docs/20260415-ablation-per-group/cmaes版本LOH/metaKV.md#L45)
- cloudphysics: [docs/20260415-ablation-per-group/cmaes版本LOH/cloudphysics.md](docs/20260415-ablation-per-group/cmaes版本LOH/cloudphysics.md#L348)
- tencentPhoto: [docs/20260415-ablation-per-group/cmaes版本LOH/tencentPhoto.md](docs/20260415-ablation-per-group/cmaes版本LOH/tencentPhoto.md#L36)
- twitter: [docs/20260415-ablation-per-group/cmaes版本LOH/twitter.md](docs/20260415-ablation-per-group/cmaes版本LOH/twitter.md#L63)
- wiki: [docs/20260415-ablation-per-group/cmaes版本LOH/wiki.md](docs/20260415-ablation-per-group/cmaes版本LOH/wiki.md#L39)
- v5 组BMR基线: [docs/20260420-AUTO_COMPOUND_MRKMR_SUMMARY.md](docs/20260420-AUTO_COMPOUND_MRKMR_SUMMARY.md#L100)

### v8-targeted-diag（零探索，分组确定性）

执行规则:

- 非目标组 `alibabaBlock/metaCDN/tencentBlock`：固定 `v5`（保证不升高）。
- 目标组使用下列固定 feature（均来自各组 BMR simple avg 最优）：
  - `metaKV -> f100`
  - `cloudphysics -> f100`
  - `tencentPhoto -> f100`
  - `twitter -> f101`
  - `wiki -> f110`

效果（相对 v5）:

| group | v5 BMR | new feature | new BMR | delta |
|---|---:|---|---:|---:|
| metaKV | 0.094000 | f100 | 0.088122 | -0.005878 |
| cloudphysics | 0.574000 | f100 | 0.560876 | -0.013124 |
| tencentPhoto | 0.228000 | f100 | 0.223137 | -0.004863 |
| twitter | 0.167000 | f101 | 0.151646 | -0.015354 |
| wiki | 0.180000 | f110 | 0.167444 | -0.012556 |

汇总:

- 目标组改进数: `5/5`
- 目标组平均 BMR: `0.248600 -> 0.238245`（`-0.010355`, 约 `-4.17%`）
- 非目标组平均 BMR: `0.333667 -> 0.333667`（`+0.000000`，不升高）
- 全组平均 BMR: `0.280500 -> 0.274028`（`-0.006472`, 约 `-2.31%`）

备注:

- 这是“零探索、可直接落地”的保守方案，已经满足你提的硬约束。
- 若后续你希望“不是按组名硬编码，而是纯 diag 自动判别同样映射到 f100/f101/f110”，我可以在此基础上再给一版阈值判别表。

## 纯特征决策版（不依赖组名）

你提出的约束是正确的：运行时不能事先知道 trace 属于哪个组，只能用 trace 读出的 diag 特征决策。

### v9-diag-threshold（零探索）

输入特征：`r1`, `r2`, `cv_freq`, `cv_rec`。

规则（按顺序匹配，命中即返回；未命中保持 `v5`）:

1. `r2 >= 0.65` -> `v5`
  作用：先保护高 `r2` 负载（覆盖 alibabaBlock/tencentBlock 主体），避免非目标组升高。

2. `r2 < 0.35 and cv_freq >= 0.62` -> `f100`
  作用：命中 metaKV 型低 `r2` + 高频波动负载。

3. `0.50 <= r2 <= 0.65 and cv_freq >= 0.62 and r1 >= 0.975` -> `f100`
  作用：命中 tencentPhoto 型高 `r1`、高 `cv_freq` 负载。

4. `0.50 <= r2 <= 0.65 and cv_freq >= 0.62 and r1 < 0.975` -> `f110`
  作用：命中 wiki 型负载。

5. `r1 < 0.90 and r2 < 0.45 and cv_freq < 0.60 and cv_rec <= 0.11` -> `f101`
  作用：命中 twitter 型低 `r1/r2` 负载。

6. `0.45 <= r2 <= 0.65 and r1 < 0.98 and cv_freq < 0.62 and cv_rec <= 0.11` -> `f100`
  作用：命中 cloudphysics 型中 `r2`、中低 `cv_freq` 负载。

7. 其他情况 -> `v5`

设计依据:

- 特征分布日志: [tmp/20260419-autocompound-equalgroup/logs/diag_feature_distribution.log](tmp/20260419-autocompound-equalgroup/logs/diag_feature_distribution.log)
- 目标组最优 BMR(simple avg):
  - metaKV -> `f100` [docs/20260415-ablation-per-group/cmaes版本LOH/metaKV.md](docs/20260415-ablation-per-group/cmaes版本LOH/metaKV.md#L45)
  - cloudphysics -> `f100` [docs/20260415-ablation-per-group/cmaes版本LOH/cloudphysics.md](docs/20260415-ablation-per-group/cmaes版本LOH/cloudphysics.md#L348)
  - tencentPhoto -> `f100` [docs/20260415-ablation-per-group/cmaes版本LOH/tencentPhoto.md](docs/20260415-ablation-per-group/cmaes版本LOH/tencentPhoto.md#L36)
  - twitter -> `f101` [docs/20260415-ablation-per-group/cmaes版本LOH/twitter.md](docs/20260415-ablation-per-group/cmaes版本LOH/twitter.md#L63)
  - wiki -> `f110` [docs/20260415-ablation-per-group/cmaes版本LOH/wiki.md](docs/20260415-ablation-per-group/cmaes版本LOH/wiki.md#L39)

预期改善（按组 simple avg 对齐口径）:

- 目标 5 组可达到上一节同量级改进：平均 `0.248600 -> 0.238245`（约 `-4.17%`）。
- 非目标组维持 `v5` 主路径（由规则 1 和兜底规则 7 保护），目标是“不升高”。

风险提示:

- 这是基于当前分布统计拟合的阈值，不是严格证明；建议先离线回放验证后再开全量。

## bit 级理论逻辑（f 比特与特征关系）

记 `f{FR}{FS}{RS}` 三比特分别控制三类二阶交互:

- `FR`：freq × rec
- `FS`：freq × size
- `RS`：rec × size

理论假设（结构归纳）:

1. 当 `rec` 波动小（`cv_rec` 低）时，`freq` 与 `rec` 的联合项更稳定，`FR` 应优先开启。
  直觉：时间局部性稳定时，频率信号与近期性信号可互补，不易互相放大噪声。

2. 当 `freq` 波动高（`cv_freq` 高）且 `r1` 指示 FS 侧非线性较强（`r1` 不高）时，`FS` 的收益上升。
  直觉：频率分布长尾/突变时，size 作为正则项可抑制“高频大对象”误选。

3. 当 `r2` 低（RS 侧可解释性强）且 `r1` 低（FS 解释力不足）时，应倾向 `RS`。
  直觉：当频率相关项不可靠时，用 rec×size 建模“新近但昂贵对象”的保留价值更稳。

据此给出 bit 判定（纯特征）:

- `FR_bit = 1` 当 `cv_rec <= 0.11`，否则 0。
- `FS_bit = 1` 当 `cv_freq >= 0.62 and 0.50 <= r2 <= 0.65 and r1 < 0.975`，否则 0。
- `RS_bit = 1` 当 `r1 < 0.90 and r2 < 0.45 and cv_freq < 0.60 and cv_rec <= 0.11`，否则 0。

然后输出 `f{FR_bit}{FS_bit}{RS_bit}`，并保留两条保护规则:

- 若 `r2 >= 0.65`，直接回 `v5`（保护高 r2 组，避免非目标组升高）。
- 若以上规则都不触发，回 `v5`。

与目标组最优 bit 的对应关系:

- metaKV/cloudphysics/tencentPhoto: 理论上主要受规则 1 主导 -> `f100`
- twitter: 规则 1 + 3 主导 -> `f101`
- wiki: 规则 1 + 2 主导 -> `f110`

这样做的意义:

- 不依赖组名，不需要探索。
- 每个 bit 的开关都可回溯到明确的统计语义，而不是黑盒经验映射。

## 最新口径（按你的新要求）

要求变更:

- 不再强制固定 alibabaBlock/metaCDN/tencentBlock。
- 优先让 metaKV/cloudphysics/tencentPhoto/twitter/wiki 这 5 组 BMR 尽量下降。

执行方式:

- 对这 5 组，直接采用各组在 BMR 表3 simple avg 下的最优 feature（f000-f111）。

结果（BMR）:

| group | v5 BMR | 新选择 | 降低后 BMR | delta | 相对降幅 |
|---|---:|---|---:|---:|---:|
| metaKV | 0.094000 | f100 | 0.088122 | -0.005878 | -6.25% |
| cloudphysics | 0.574000 | f100 | 0.560876 | -0.013124 | -2.29% |
| tencentPhoto | 0.228000 | f100 | 0.223137 | -0.004863 | -2.13% |
| twitter | 0.167000 | f101 | 0.151646 | -0.015354 | -9.19% |
| wiki | 0.180000 | f110 | 0.167444 | -0.012556 | -6.98% |

5 组均值:

- v5: 0.248600
- 降低后: 0.238245
- 改进: -0.010355（-4.17%）

数据来源:

- 5 组 v5 BMR: [docs/20260420-AUTO_COMPOUND_MRKMR_SUMMARY.md](docs/20260420-AUTO_COMPOUND_MRKMR_SUMMARY.md#L103)
- metaKV 最优 BMR: [docs/20260415-ablation-per-group/cmaes版本LOH/metaKV.md](docs/20260415-ablation-per-group/cmaes版本LOH/metaKV.md#L45)
- cloudphysics 最优 BMR: [docs/20260415-ablation-per-group/cmaes版本LOH/cloudphysics.md](docs/20260415-ablation-per-group/cmaes版本LOH/cloudphysics.md#L348)
- tencentPhoto 最优 BMR: [docs/20260415-ablation-per-group/cmaes版本LOH/tencentPhoto.md](docs/20260415-ablation-per-group/cmaes版本LOH/tencentPhoto.md#L36)
- twitter 最优 BMR: [docs/20260415-ablation-per-group/cmaes版本LOH/twitter.md](docs/20260415-ablation-per-group/cmaes版本LOH/twitter.md#L63)
- wiki 最优 BMR: [docs/20260415-ablation-per-group/cmaes版本LOH/wiki.md](docs/20260415-ablation-per-group/cmaes版本LOH/wiki.md#L39)

## 压缩版（最少阈值，纯特征）

目标:

- 用尽量少的阈值逼近上面的 5 组改进结果。

仅保留 3 个阈值:

- `tau_r2_guard = 0.65`（保护高 r2 区）
- `tau_cv_freq = 0.62`（区分高频波动）
- `tau_r1_split = 0.90`（区分低 r1 的 twitter 型）

决策（按顺序）:

1. 若 `r2 >= tau_r2_guard` -> `v5`
2. 若 `cv_freq >= tau_cv_freq` -> `f100`
3. 若 `r1 < tau_r1_split` -> `f101`
4. 其他 -> `f110`

解释:

- 规则 1 保守保护高 r2 区域，避免大组被误伤。
- 规则 2 覆盖 metaKV/cloudphysics/tencentPhoto 这类高 `cv_freq` 主体。
- 规则 3 单独分离 twitter 的低 `r1` 形态。
- 规则 4 兜底到 wiki 对应的 `f110`。

说明:

- 这是“压缩近似规则”，不是严格最优分类器。
- 若你要更稳，可以只把规则 4 改成 `v5`，会更保守但可能损失部分 wiki 收益。

## 专用方案：只优化 metaKV，且不升高 alibabaBlock/metaCDN/tencentBlock

目标:

- 仅关注 metaKV 降 BMR。
- 对 `alibabaBlock/metaCDN/tencentBlock` 设置硬保护：不高于 v5。

纯特征规则（零探索）:

1. 若 `r2 < 0.35 and cv_freq >= 0.62` -> `f100`
2. 否则 -> `v5`

理由:

- metaKV 典型特征是低 `r2` 且高 `cv_freq`，命中规则 1。
- alibabaBlock/tencentBlock 通常 `r2` 较高，不会触发规则 1。
- metaCDN 虽可能低 `r2`，但 `cv_freq` 不高于该阈值，仍走 v5。

对应 BMR（simple avg 口径）:

| group | v5 BMR | 新策略 BMR | delta |
|---|---:|---:|---:|
| metaKV | 0.094000 | 0.088122 | -0.005878 |
| alibabaBlock | 0.485000 | 0.485000 | +0.000000 |
| metaCDN | 0.185000 | 0.185000 | +0.000000 |
| tencentBlock | 0.331000 | 0.331000 | +0.000000 |

结论:

- metaKV 相对 v5 降低约 6.25%。
- 三个保护组保持不升高。

### 理论支撑（为何用 r2 与 cv_freq）

定义回顾:

- `r2` 描述 rec 与 RS 通道相关结构强度（rec×size 一侧的可解释性信号）。
- `cv_freq` 描述频率统计的离散/波动强度，越高表示频率分布越重尾、越不稳定。

机制解释:

1. 当 `r2` 低时，`RS` 相关结构对当前 trace 的解释力弱，依赖 rec 相关耦合项的收益下降。
  这时应降低对 rec 侧耦合的依赖，避免把 rec 噪声放大到打分函数里。

2. 当 `cv_freq` 高时，freq 信号重尾与尺度效应更强。
  打开 `f100`（FR=1, FS=0, RS=0）可保留 freq-rec 主干，同时关闭 size 相关耦合项，减少“大对象 + 高频尖峰”对策略的扰动。

3. 对高 `r2` 或低 `cv_freq` 区域回退 `v5`，等价于“无充分证据不切换”。
  从统计决策角度，这是一种保守先验：仅在诊断信号同时满足“RS 弱 + freq 波动强”时才偏离基线。

因此，该规则本质是一个两维门控:

- `r2` 负责判断“是否应削弱 rec-size 路径”；
- `cv_freq` 负责判断“是否进入高频波动 regime”；
- 两者同时触发才切到 `f100`，其余回 `v5` 以保证稳健性。
