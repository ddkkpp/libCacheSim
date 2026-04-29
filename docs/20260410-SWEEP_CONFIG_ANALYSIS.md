# LOH CMA-ES 配置参数影响分析 & 117-Trace Sweep 设计

日期: 2026-04-10

## 1. 所有可配置参数及其对 MR 的影响

### 1.1 候选数量参数（影响极大）

| 环境变量 | 含义 | 代码默认值 | 实测影响 | 证据 |
|---------|------|-----------|---------|------|
| `LOH_RANDOM_CANDIDATES` | 随机采样候选数 | 128 | **极大**：1063 上 r16→0.19, r256→0.025 | `tmp/20260412-cand-sweep/results.csv` |
| `LOH_STRUCTURED_CANDIDATES` | 结构化（排序）候选数 | 16 | **大**：与 random 交互，1063 上 s16→0.036 vs s96→0.022 | 同上 |
| `LOH_MIN_CAND_PER_FEATURE` | 每特征最低候选配额 | 1 | **小**：mcp=1/2/4 差异通常 <1% | `tmp/20260409-mcp-ac-sweep/results.csv` (13行) |

- `RANDOM_CANDIDATES` × `STRUCTURED_CANDIDATES` 是 **最重要的调参维度**
- 在 1063 上 MR 差距可达 10 倍（0.019 vs 0.194）
- 在 meta_reag 上差距约 19%（0.269 vs 0.319）
- 在 CloudPhysics 上差距约 20%（0.219 vs 0.268）

### 1.2 特征变换参数（影响大，已定论）

| 环境变量 | 含义 | 代码默认值 | 实测影响 | 证据 |
|---------|------|-----------|---------|------|
| `LOH_FEATURE_LOG1P` | log1p(raw) 特征变换 | 1 | **大**：log1p=1 全面优于 raw | `sweeps/20260317-log1p_*` |
| `LOH_FEATURE_RECIPROCAL` | 1/(1+x) 特征变换 | 0 | **中**：wiki 上 reciprocal 略好，其他 log1p 好 | 同上 |
| `LOH_FEATURE_LOG1P_RECIPROCAL` | log1p + reciprocal 双变换 | 0 | **小**：增益不明显 | 同上 |

**结论**：`LOG1P=1` 已确认在绝大多数 trace 上最优，**无需再 sweep**。

### 1.3 Compound 评分参数（影响大，已定论）

| 环境变量 | 含义 | 代码默认值 | 实测影响 | 证据 |
|---------|------|-----------|---------|------|
| `LOH_SCORE_USE_COMPOUND` | 启用交叉特征 | 1 | **大**：compound=1 比 compound=0 平均好 3% | `tmp/20260409-comp0-irt0-all/full_comparison.csv` (109 trace) |
| `LOH_AUTO_COMPOUND` | 自适应 compound 选择 | 1 | **极大**：AC=1 在 1063 上 49 配置全胜 AC=0，avg +71% | `tmp/20260410-cand-sweep-ac/` |
| `LOH_SCORE_USE_IRT` | IRT 评分 | 0 | **小**：IRT=0 普遍更好 | `tmp/20260409-comp0-irt0-all/` |
| `LOH_USE_FREQ_REC` | freq×rec 交叉项 | (auto) | 由 auto_compound 控制 | `tmp/20260409-compound-sweep/results.csv` |
| `LOH_USE_FREQ_SIZE` | freq×size 交叉项 | (auto) | 由 auto_compound 控制 | 同上 |
| `LOH_USE_REC_SIZE` | rec×size 交叉项 | (auto) | 由 auto_compound 控制 | 同上 |

**结论**：`COMPOUND=1, AUTO_COMPOUND=1, IRT=0` 已确认最优，**无需再 sweep**。
auto_compound 在 warmup 后自动选择最佳 compound 子集（基于共线性诊断），人工设定不如自适应。

### 1.4 CMA-ES 算法参数（影响中等，已定论）

| 环境变量 | 含义 | 代码默认值 | 实测影响 | 证据 |
|---------|------|-----------|---------|------|
| `LOH_CMAES_ALGO` | CMA-ES 算法变体 | aipop | **中**：aIPOP 在多 trace 上最稳定 | `tmp/20260408-cmaes-algo-sweep/` |
| `LOH_CMAES_FEEDBACK` | 反馈模式 | weighted | **小** | `tmp/20260401-feedback-formula-fix/` |
| `LOH_CMAES_ASYNC` | 异步训练线程 | 1 | **小**：主要影响吞吐 | 代码默认 |

**结论**：`algo=aipop, feedback=weighted, async=1` 已确认，**无需再 sweep**。

### 1.5 Reward 权重参数（影响中等，值得 sweep）

| 环境变量 | 含义 | 代码默认值 | 实测影响 | 证据 |
|---------|------|-----------|---------|------|
| `LOH_MISS_RATIO_WEIGHT` | MR vs BMR 权重 | 1.0 (纯MR) | **中**：mrw=0.7 在 CloudPhysics 上 BMR 明显改善，MR 略降 | `tmp/20260407-cmaes-mrw03/05/07-cloudphysics/` |

- mrw=1.0：纯 MR 优化
- mrw=0.7：MR×0.7 + BMR×0.3 综合优化，CloudPhysics BMR 改善显著
- 之前 mrw sweep 只在 CloudPhysics 上做过，不含 metaCDN/metaKV/wiki

**结论**：**值得在 117 trace 上做 mrw=1.0 vs mrw=0.7 对比**。

### 1.6 其他参数（影响小，无需 sweep）

| 环境变量 | 含义 | 代码默认值 | 影响 |
|---------|------|-----------|------|
| `LOH_BATCH_EVICT_SIZE` | 批量驱逐大小 | 16 | 小 |
| `LOH_ADAPTIVE_BUDGET` | 自适应预算分配 | 1 | 小，开启更好 |
| `LOH_SCORE_MODEL` | 评分模型 | linear | 小，linear 稳定 |
| `LOH_PERF_HOTPATH_SAMPLE_STRIDE` | 采样步长 | 16 | 仅影响吞吐 |
| `LOH_HEURISTIC_SIGNS` | 启发式符号 | 1 | 小 |

---

## 2. 需要 Sweep 的变量总结

| 优先级 | 变量 | Sweep 值 | 理由 |
|--------|------|---------|------|
| **P0 (最高)** | `RANDOM_CANDIDATES × STRUCTURED_CANDIDATES` | r128_s16, r96_s96, r128_s96, r192_s64 | MR 影响 10×，4-trace 数据不足以定论 |
| **P1 (高)** | `MISS_RATIO_WEIGHT` | 1.0 vs 0.7 | 中等影响，仅在 CloudPhysics 上验证过 |
| **P2 (可选)** | `MIN_CAND_PER_FEATURE` | 1 vs 4 | 小影响，但全量 trace 仅有 4-trace 数据 |

**不需要 sweep 的变量**（已有充分 117-trace 或 109-trace 证据）：
- AUTO_COMPOUND=1 ✅
- FEATURE_LOG1P=1 ✅
- SCORE_USE_COMPOUND=1 ✅
- SCORE_USE_IRT=0 ✅
- CMAES_ALGO=aipop ✅
- CMAES_FEEDBACK=weighted ✅
- BATCH_EVICT_SIZE=16 ✅
- ADAPTIVE_BUDGET=1 ✅

---

## 3. 推荐 Sweep 方案

### 阶段一：r×s 主 sweep (4 配置 × 117 trace = 468 次)

固定参数：
```bash
LOH_AUTO_COMPOUND=1
LOH_FEATURE_LOG1P=1
LOH_SCORE_USE_COMPOUND=1
LOH_SCORE_USE_IRT=0
LOH_MIN_CAND_PER_FEATURE=1
LOH_MISS_RATIO_WEIGHT=1.0  # 纯 MR 优化
LOH_ENABLE_CMAES=1
LOH_ENABLE_RL=0
LOH_DEBUG_LEVEL=0
LOH_PERF_PROFILING=0
cache_ratio=0.1
--num-req=0  # 全量
```

Sweep 值：
| 配置 | RANDOM | STRUCTURED | 选择理由 |
|------|--------|-----------|---------|
| r128_s16 | 128 | 16 | 当前代码默认，速度基线 |
| r96_s96 | 96 | 96 | CloudPhysics (w82/w74) MR 最优 |
| r128_s96 | 128 | 96 | 1063 MR 最优区 |
| r192_s64 | 192 | 64 | AC=1 全局最优 (1063) |

### 阶段二：MRW 对比 (最优 r×s × 2 = 234 次)

在阶段一找到最优 r×s 配置后：
- `LOH_MISS_RATIO_WEIGHT=1.0` vs `LOH_MISS_RATIO_WEIGHT=0.7`
- 目标：确认 mrw=0.7 是否在 117 trace 上也改善 BMR

### 阶段三（可选）：MCP 对比 (最优 r×s × 2 = 234 次)

- `LOH_MIN_CAND_PER_FEATURE=1` vs `LOH_MIN_CAND_PER_FEATURE=4`

---

## 4. 参考数据来源

| 数据 | 路径 | 内容 |
|------|------|------|
| 117-trace 基线 (旧代码 r256_s16) | `tmp/20260407-cmaes-sweep/` | comparison_tables.md, 117 result files |
| 4-trace 7×7 r×s sweep | `tmp/20260412-cand-sweep/results.csv` | 196 行 |
| AC=0 vs AC=1 对照 | `tmp/20260410-cand-sweep-ac/` | ac0/, ac1/ 各 196 行 |
| Compound 消融 | `tmp/20260409-compound-sweep/results.csv` | 32 行 |
| comp0 vs comp1 109-trace | `tmp/20260409-comp0-irt0-all/full_comparison.csv` | 110 行 |
| MCP sweep | `tmp/20260409-mcp-ac-sweep/results.csv` | 13 行 |
| MRW 0.3/0.5/0.7 CloudPhysics | `tmp/20260407-cmaes-mrw03/05/07-cloudphysics/` | 各 ~106 logs |
| CMA-ES 算法对比 | `tmp/20260408-cmaes-algo-sweep/` | 多配置 |
| R² 共线性验证 | `tmp/20260410-collinearity-test/r2sum_all.csv` | 110 行 |
