# Penalty 优化复盘（2026-03-26）

## 结论
- 如果 20260325-penalty-full-3traces 已显示 gate 调参收益很小，后续应降低 gate 扫描优先级。
- 优先从奖励构型与可学习信号入手，而不是继续扩大 gate 网格。

## 当前方案问题
1. 奖励混合后，penalty 分量容易被 base 分量淹没。
2. 仅看最终 miss ratio，难以判断 penalty 的边际贡献。
3. 观测对 penalty 上下文表达不足，策略难做条件化决策。

## 优先优化顺序
1. 增加三路奖励日志: reward_base / reward_penalty / reward_total。
2. 奖励重标定: 调整 penalty 增量权重与 clip/归一化策略。
3. 观测增强: 补充 penalty 触发上下文特征。
4. 采样策略: 提高 penalty 相关 transition 的回放占比。
5. gate 微调: 仅做少量关键参数试探，不做大规模扫描。

## 成功判据
1. 相比 penalty off，至少两条 trace 稳定改善。
2. reward_penalty 与 reward_total 相关方向符合预期。
3. 训练波动未显著恶化。
