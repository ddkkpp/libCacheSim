# LOH 环境变量速查（2026-03-19 更新）

本文按当前代码重新整理，覆盖 C 端 `LOH.c`、Python 端 `loh_actor_critic_sb3.py`、构建脚本 `debug.sh` 与运行脚本 `test_loh_rl_sb3.sh`。

## 1. 使用规则（先看这个）

- 优先级：运行时环境变量 > 脚本内默认值 > 代码硬编码兜底。
- C/Python 共享内存结构必须一致：`LOH_INCLUDE_*` 相关开关如果改动，必须重建并保证两端一致。
- 信号量开关按“禁用优先”：`LOH_DISABLE_SEMAPHORE` 优先于 `LOH_ENABLE_SEMAPHORE`。
- 构建输出目录：Debug 通常在 `_build_dbg/`，Release 通常在 `_build_rel/`，历史兼容目录可能是 `_build/`。

## 2. IPC 与同步

- `LOH_SHM_KEY`：共享内存与信号量 key（默认 `9876`）。
- `LOH_ENABLE_SEMAPHORE`：强制启用 POSIX 信号量。
- `LOH_DISABLE_SEMAPHORE`：强制禁用 POSIX 信号量（优先级更高）。
- `LOH_WAIT_MODE`：C 端等待模式（`blocked`/`nonblocked`）。
- `LOH_SEM_TIMEOUT_S`：Python 端等待信号量超时秒数（默认 `1.0`）。
- `LOH_POLL_SLEEP_US`：Python 轮询退化路径 sleep（默认 `200` 微秒）。
- `LOH_DISABLE_FSYNC`：Python 写 SHM 后是否跳过 fsync。
- `LOH_PRINT_SHM_LAYOUT`：是否打印 Python 侧共享内存布局。

## 3. 维度与特征开关（C/Python 必须一致）

- `LOH_INCLUDE_HIT_MISS_FEATURES`
- `LOH_INCLUDE_CACHE_FEATURES`
- `LOH_INCLUDE_CANDIDATE_FEATURES`
- `LOH_INCLUDE_TOPK_CANDIDATE_FEATURES`
- `LOH_INCLUDE_AVGTOPK_CANDIDATE_FEATURES`
- `LOH_INCLUDE_REQUEST`
- `LOH_INCLUDE_WEIGHTS_IN_OBS`
- `RL_STATE_USE_MISSRATIO`

说明：这些变量会改变观测/状态维度；如果只改 Python 不改 C 编译宏，会导致 SHM 布局不匹配。

### 3.1 关键变量解释

- `LOH_INCLUDE_REQUEST`
	- 作用：把请求历史段追加到状态尾部。
	- 影响：维度变化最大，必须 C/Python 同步开启并重建。

- `LOH_INCLUDE_TOPK_CANDIDATE_FEATURES` / `LOH_INCLUDE_AVGTOPK_CANDIDATE_FEATURES`
	- 作用：启用 TopK 与 AvgTopK 候选特征。
	- 影响：通常显著提升观测表达力，同时增加计算与 SHM 体积。

- `LOH_INCLUDE_WEIGHTS_IN_OBS`
	- 作用：把当前权重注入观测。
	- 影响：策略能“看到自己当前策略状态”，但也可能引入反馈耦合。

- `RL_STATE_USE_MISSRATIO`
	- 作用：RL 输入是否使用前 2 维命中率。
	- 影响：关闭可做“盲化”实验，减少直接命中率泄漏。

## 4. 动作空间与打分

- `LOH_DUAL_CHANNEL`：动作是否双通道。
- `LOH_USE_SOFTMAX`：动作是否 softmax 化。
- `LOH_ACTION_BOUND`：动作边界。
- `LOH_ACTION_SCALE`：动作缩放。
- `LOH_SOFTMAX_TEMP`：历史温度参数（兼容用，已弱化）。
- `LOH_WEIGHT_EMA`：写回权重 EMA。
- `LOH_WEIGHT_CLIP`：写回权重裁剪。
- `LOH_FIXED_OBS`：固定观测模式。
- `LOH_FEATURE_LOG1P`
- `LOH_FEATURE_RECIPROCAL`
- `LOH_FEATURE_LOG1P_RECIPROCAL`
- `LOH_FEATURE_UNIFIED_FORMULA`
- `LOH_FEATURE_IDENTITY`
- `LOH_SCORE_MODEL`：`linear` 或 `mlp`。
- `LOH_MLP_HIDDEN`
- `LOH_INITIAL_WEIGHTS`
- `LOH_FIXED_WEIGHTS`
- `LOH_FIXED_MLP_PARAMS`

### 4.1 核心打分公式

- 线性打分（默认）：

$$
\text{score}(x)=\sum_i f_i(x)\cdot w_i\cdot s_i
$$

其中：
- $f_i$ 由特征模式决定（`LOH_FEATURE_LOG1P` / `LOH_FEATURE_LOG1P_RECIPROCAL` / unified 族）。
- $w_i$ 由 RL 动作映射得到（受 `LOH_DUAL_CHANNEL`、`LOH_USE_SOFTMAX`、`LOH_ACTION_SCALE` 影响）。
- $s_i$ 由启发式符号决定（`LOH_USE_HEURISTIC_SIGNS`，例如 recency 负号、frequency 正号）。

- compound 模式（`LOH_SCORE_USE_COMPOUND=1`）下，特征集合扩展为：

$$
[recency,frequency,size,freq\_recency,freq\_size,recency\_size]
$$

- MLP 模式（`LOH_SCORE_MODEL=mlp`）下由 `LOH_MLP_HIDDEN` 与 `LOH_FIXED_MLP_PARAMS` 控制网络结构/参数注入。

### 4.2 特征变换变量详解（重点）

- `LOH_FEATURE_LOG1P`
	- 作用：把 recency/frequency/size/IRT 等基础特征转换为 `log1p(raw)` 族，减弱重尾分布。
	- 默认：当前统一脚本默认开启（`1`）。
	- 影响：会改变特征量纲，从而改变同一组权重下的打分斜率。

- `LOH_FEATURE_RECIPROCAL`
	- 作用：启用倒数型衰减（老行为兼容开关）。
	- 常见形式：

$$
f(x)=\frac{1}{1+x}
$$

- `LOH_FEATURE_LOG1P_RECIPROCAL`
	- 作用：先 log1p，再 reciprocal，兼顾压缩与单调衰减。
	- 常见形式：

$$
f(x)=\frac{1}{1+\log(1+x)}
$$

- `LOH_FEATURE_UNIFIED_FORMULA`
	- 作用：切换到 unified 特征公式族（与 `LOH_UNIFIED_*` 组合使用）。

- `LOH_FEATURE_IDENTITY`
	- 作用：尽量保留原始尺度（最少变换），便于对照实验。

- `LOH_DUAL_CHANNEL`
	- 作用：动作是否采用正负双通道写回权重。
	- 典型解释：双通道时每个特征由 `(pos,neg)` 组合得到有效权重。

- `LOH_USE_SOFTMAX`
	- 作用：动作是否先做 softmax。
	- 关闭时通常直接使用连续动作值（含正负）。

- `LOH_ACTION_SCALE`
	- 作用：动作温度/幅度缩放，直接影响权重分布陡峭程度。

- `LOH_SOFTMAX_TEMP`
	- 作用：历史温度参数；新脚本更推荐用 `LOH_ACTION_SCALE`。

## 5. 评分候选与结构化采样

- `LOH_STRUCTURED_CANDIDATES`
- `LOH_RANDOM_CANDIDATES`
- `LOH_TAIL_SAMPLE`
- `LOH_TAIL_SAMPLE_DECAY`
- `LOH_USE_SIZE_BUCKETS`
- `LOH_ADAPTIVE_BUDGET`
- `LOH_USE_SCORE_REBALANCE`
- `LOH_SCORE_USE_IRT`
- `LOH_SCORE_USE_COMPOUND`
- `LOH_SCORE_COMPOUND_V2`
- `LOH_USE_HEURISTIC_SIGNS`

### 5.1 关键变量解释

- `LOH_STRUCTURED_CANDIDATES`
	- 作用：控制结构化候选池规模与启用方式。
	- 影响：过小会丢失可驱逐优选对象，过大增加评分开销。

- `LOH_RANDOM_CANDIDATES`
	- 作用：追加随机候选，提升探索性。
	- 影响：能缓解局部最优，但会增加波动。

- `LOH_SCORE_USE_COMPOUND` / `LOH_SCORE_COMPOUND_V2`
	- 作用：启用组合特征打分与新版本组合策略。
	- 影响：可提升表达力，但参数更敏感。

- `LOH_USE_HEURISTIC_SIGNS`
	- 作用：固定特征正负方向先验。
	- 影响：提高稳定性，减少方向性学习负担；关闭后更灵活但更难学稳。

- `LOH_USE_SIZE_BUCKETS`
	- 作用：切换 size 组织结构（bucket vs heap）。
	- 影响：影响候选检索复杂度与缓存分布适配。

### 5.2 CMA-ES 在线优化参数（C 端）

- `LOH_ENABLE_CMAES`
	- 作用：开启 C 侧 CMA-ES 在线优化。
	- 默认：`0`（关闭）。

- `LOH_CMAES_ALGO`
	- 作用：选择 CMA-ES 算法族（如 `default/cmaes`、`abipop`、`sep`、`vd` 等）。
	- 默认：`abipop`。

- `LOH_CMAES_LAMBDA`
	- 作用：种群大小。
	- 默认：`10`（有效范围由代码约束为 `[2, 64]`）。

- `LOH_CMAES_INIT_MEAN`
	- 作用：初始化均值。
	- 默认：`0.5`（运行时会夹紧到 `[0,1]`）。

- `LOH_CMAES_INIT_SIGMA`
	- 作用：初始化步长。
	- 默认：`0.2`（运行时最小值 `0.01`）。

- `LOH_CMAES_FEEDBACK`
	- 作用：tell 阶段反馈指标（`miss` / `byte` / `weighted` / `abg_delta`）。
	- 默认：`weighted`。

- `LOH_CMAES_FEEDBACK_ALPHA` / `LOH_CMAES_FEEDBACK_BETA` / `LOH_CMAES_FEEDBACK_GAMMA`
	- 作用：`abg_delta` 反馈模式下的系数。
	- 默认：均为 `1.0`。

## 6. 特征归一化与自动模式

- `LOH_ENABLE_FEATURE_NORMALIZATION`
- `LOH_ENABLE_ADAPTIVE_FEATURE_NORMALIZATION`
- `LOH_FEATURE_NORM_MAX_RECENCY`
- `LOH_FEATURE_NORM_MAX_FREQ`
- `LOH_FEATURE_NORM_MAX_SIZE`
- `LOH_FEATURE_NORM_MAX_IRT`
- `LOH_ADAPTIVE_NORM_LO_Q`
- `LOH_ADAPTIVE_NORM_HI_Q`
- `LOH_ADAPTIVE_NORM_WARMUP`
- `LOH_ADAPTIVE_NORM_TRANSFORM_QUANTILE`
- `LOH_AUTO_FEATURE_MODE`
- `LOH_AUTO_DETECT_REQS`
- `LOH_AUTO_CV_THRESHOLD`
- `LOH_UNIFIED_VARIANT`
- `LOH_UNIFIED_METHOD`
- `LOH_UNIFIED_ALPHA`
- `LOH_UNIFIED_BETA`
- `LOH_UNIFIED_GAMMA`
- `LOH_UNIFIED_FREQ_CAP`

### 6.1 归一化公式

- 固定上限归一化（`LOH_ENABLE_FEATURE_NORMALIZATION=1`）：

$$
f_i' = \min\left(1,\ \frac{f_i}{\log(1+\text{max}_i)}\right)
$$

其中 `max_i` 由以下变量覆盖：
- `LOH_FEATURE_NORM_MAX_RECENCY`
- `LOH_FEATURE_NORM_MAX_FREQ`
- `LOH_FEATURE_NORM_MAX_SIZE`
- `LOH_FEATURE_NORM_MAX_IRT`

- 自适应分位（`LOH_ENABLE_ADAPTIVE_FEATURE_NORMALIZATION=1`）由以下变量控制窗口与分位：
- `LOH_ADAPTIVE_NORM_LO_Q`
- `LOH_ADAPTIVE_NORM_HI_Q`
- `LOH_ADAPTIVE_NORM_WARMUP`
- `LOH_ADAPTIVE_NORM_TRANSFORM_QUANTILE`

## 7. 奖励与惩罚（Python 主导）

- `LOH_ENABLE_PENALTY`
- `LOH_PENALTY_SCALE` / `LOH_PENALTY_MODE`
- `LOH_PENALTY_DMAX`
- `LOH_PENALTY_CUTOFF`
- `LOH_SURVIVAL_QUANTILE`
- `LOH_SURVIVAL_BINS`
- `LOH_SURVIVAL_MINCOUNT`
- `LOH_REWARD_MODE`
- `LOH_REWARD_SCALE`
- `LOH_REWARD_USE_PENALTY`
- `LOH_REWARD_USE_MISSRATIO`
- `LOH_REWARD_USE_MISSRATIOTREND`
- `LOH_REWARD_USE_ORIGINAL`
- `LOH_REWARD_MIX_MODE`
- `LOH_REWARD_W_PENALTY`
- `LOH_REWARD_W_MISS`
- `LOH_REWARD_W_TREND`
- `LOH_REWARD_W_ORIGINAL`
- `LOH_REWARD_W_BASE_ORIG`
- `LOH_REWARD_W_BASE_MISS`
- `LOH_REWARD_W_BASE_TREND`
- `LOH_REWARD_W_PENALTY_DELTA`
- `LOH_REWARD_ORIGINAL_MAP`
- `LOH_PENALTY_GATE_MINCOUNT`
- `LOH_PENALTY_GATE_GOODRATE`
- `LOH_PENALTY_GATE_PENALTYSCALE`
- `LOH_PENALTY_GATE_NO_CUTOFF_SCALE`
- `LOH_PENALTY_DELTA_SCALE`
- `LOH_PENALTY_REWARD_FORMULA`
- `LOH_PENALTY_NET_GOOD_SCALE`
- `LOH_PENALTY_NET_PENALTY_SCALE`
- `LOH_PENALTY_EMPTY_AS_GOOD`
- `LOH_PENALTY_REFINE_ON_LATE`
- `LOH_PENALTY_NO_EVICT_REWARD`
- `LOH_PENALTY_BASELINE_DECAY`
- `LOH_PENALTY_SEND_POSITIVE`（C 端）
- `LOH_MISS_COMPONENT`
- `LOH_MISSRATIOTREND_WINDOW`
- `LOH_MISSRATIOTREND_MODE`
- `LOH_TREND_WINDOW`
- `LOH_TREND_MODE`
- `LOH_REWARD_EMA`
- `LOH_REWARD_EMAWINDOW`
- `LOH_MISS_RATIO_WEIGHT`

### 7.1 奖励组合公式

- 默认线性组合（`legacy` 思路）：

$$
R = w_p\cdot R_{penalty} + w_m\cdot R_{miss} + w_t\cdot R_{trend} + w_o\cdot R_{orig}
$$

对应变量：
- `LOH_REWARD_W_PENALTY` = $w_p$
- `LOH_REWARD_W_MISS` = $w_m$
- `LOH_REWARD_W_TREND` = $w_t$
- `LOH_REWARD_W_ORIGINAL` = $w_o$

- gated 模式（`LOH_REWARD_MIX_MODE=gated_penalty_mix`）会先计算基础项，再按 gate 条件叠加 penalty 增量：

$$
R = R_{base} + g\cdot \Delta R_{penalty}
$$

其中 gate 由以下变量控制：
- `LOH_PENALTY_GATE_MINCOUNT`
- `LOH_PENALTY_GATE_GOODRATE`
- `LOH_PENALTY_GATE_PENALTYSCALE`
- `LOH_PENALTY_GATE_NO_CUTOFF_SCALE`

### 7.2 惩罚缩放公式

- `LOH_PENALTY_SCALE=log` 常见形式：

$$
p(d)=\log(1+d)\ \text{或}\ \log\left(1+\frac{d}{d_{max}}\right)
$$

- `LOH_PENALTY_SCALE=reciprocal` 常见形式：

$$
p(d)=\frac{1}{1+d}
$$

- `LOH_PENALTY_SCALE=survival` 由 `LOH_SURVIVAL_QUANTILE` / `LOH_SURVIVAL_BINS` / `LOH_SURVIVAL_MINCOUNT` 决定分桶与分位映射。

其中 $d$ 受 `LOH_PENALTY_DMAX` 截断（必要时）并可由 `LOH_PENALTY_CUTOFF` 过滤。

### 7.3 奖励变量逐项说明（高频）

- `LOH_REWARD_MODE`
	- `absolute`：直接使用当前时刻组合奖励。
	- `delta`：更关注相邻阶段改善量。

- `LOH_REWARD_SCALE`
	- 作用：对最终奖励做线性缩放，便于与算法学习率/熵项协调。

- `LOH_REWARD_USE_PENALTY` / `LOH_REWARD_USE_MISSRATIO` / `LOH_REWARD_USE_MISSRATIOTREND`
	- 作用：控制三类分量是否参与总奖励。

- `LOH_MISS_COMPONENT`
	- 常见取值：`neg` 或 `improve`。
	- 影响：miss 分量是按“绝对坏度”还是“改进幅度”计入。

- `LOH_REWARD_EMA` + `LOH_REWARD_EMAWINDOW`
	- 作用：对奖励做滑动平滑，减少高方差抖动。

- `LOH_PENALTY_REWARD_FORMULA`
	- 常见选项：`centered` / `relative` / `net` / `net2`。
	- 作用：改变 penalty 转换为 reward 的符号与尺度语义。

- `LOH_PENALTY_NET_GOOD_SCALE` 与 `LOH_PENALTY_NET_PENALTY_SCALE`
	- 作用：分别调节正向 good 事件与负向 penalty 事件在 net 公式中的权重。

- `LOH_PENALTY_EMPTY_AS_GOOD`
	- 作用：当有驱逐但无 penalty 事件时，是否计正反馈。

- `LOH_PENALTY_REFINE_ON_LATE`
	- 作用：late penalty 到达后，是否回补修正对应奖励。

- `LOH_PENALTY_NO_EVICT_REWARD`
	- 作用：无驱逐阶段奖励如何处理（如 `keep` 或 `zero`）。

## 8. RL 算法与训练流程

- `LOH_RL_ALGO`（常见：`SAC` / `PPO` / `PPO_LSTM` / `TD3`）
- `LOH_ASYNC_TRAIN`
- `LOH_EXCLUDE_RECENT_STEPS`
- `LOH_SOFT_PRIOR`
- `LOH_SOFT_PRIOR_BIAS`
- `LOH_RL_SEED`（未设时通常回退 `SEED`）
- `LOH_RL_UPDATE_INTERVAL`（C 端 epoch/update 周期）
- `LOH_ENABLE_RL`

### 8.1 关键变量解释

- `LOH_RL_ALGO`
	- 作用：选择 SB3 算法分支。
	- 影响：不同算法对奖励尺度、稳定性、样本效率差异明显。

- `LOH_ASYNC_TRAIN`
	- 作用：训练与推理是否异步解耦。
	- 影响：吞吐通常更高，但参数更新时序更复杂。

- `LOH_EXCLUDE_RECENT_STEPS`
	- 作用：off-policy 训练时排除最近样本。
	- 影响：降低时序相关偏差，代价是样本利用率下降。

- `LOH_SOFT_PRIOR` / `LOH_SOFT_PRIOR_BIAS`
	- 作用：对动作头施加软先验（符号/幅度倾向）。
	- 影响：可加速冷启动；偏置过强会抑制探索。

- `LOH_RL_UPDATE_INTERVAL`
	- 作用：C 端触发一次同步更新的请求间隔。
	- 影响：直接决定同步频率、训练节奏与运行开销。

## 9. 断点续训与产物

- `LOH_RESUME`
- `LOH_RESUME_DIR`
- `LOH_RESUME_PATH`
- `LOH_CHECKPOINT_FREQ`
- `RUN_TIMESTAMP`

## 10. 构建期变量（debug.sh 透传为编译宏）

常见透传键：

- `LOH_INCLUDE_*`
- `LOH_FEATURE_*`
- `LOH_SCORE_*`
- `LOH_DEBUG_LEVEL`

建议：在执行 `bash scripts/debug.sh -c` 或 `bash scripts/debug.sh` 之前先导出这些变量，再运行测试脚本。

常用构建命令：

- Debug clean：`bash scripts/debug.sh -c`（产物在 `_build_dbg/`）
- Debug incremental：`bash scripts/debug.sh`（产物在 `_build_dbg/`）
- Release clean：`bash scripts/debug.sh -r -c`（产物在 `_build_rel/`）
- Release incremental：`bash scripts/debug.sh -r`（产物在 `_build_rel/`）

## 11. 其它相关变量

- `MIN_SCAN_SIZE`：traceAnalyzer scanDetector 使用。

## 12. 推荐最小配置模板

```bash
export LOH_SHM_KEY=9876
export LOH_ENABLE_SEMAPHORE=1
export LOH_DISABLE_SEMAPHORE=0

export LOH_INCLUDE_TOPK_CANDIDATE_FEATURES=1
export LOH_INCLUDE_AVGTOPK_CANDIDATE_FEATURES=1
export LOH_INCLUDE_REQUEST=0

export LOH_RL_ALGO=SAC
export LOH_ASYNC_TRAIN=1
export LOH_ENABLE_PENALTY=0

bash scripts/debug.sh -c
bash scripts/test_loh_rl_sb3.sh <trace_path>
```

## 13. 维护约定

- 新增环境变量时，需同步更新本文件与 `docs/20260319-EXPERIMENT_ASSET_INDEX.md`。
- 涉及 C/Python 结构体或维度改动时，必须在提交说明里写明双端同步状态。

## 14. 全量逐项表（变量-默认值-作用-影响）

### 14.1 IPC / 同步

| 变量 | 默认值 | 作用 | 影响/备注 |
|---|---|---|---|
| LOH_SHM_KEY | 9876 | 共享内存与信号量 key | C/Python 必须一致 |
| LOH_ENABLE_SEMAPHORE | 未强制 | 强制启用信号量 | 被 `LOH_DISABLE_SEMAPHORE` 覆盖 |
| LOH_DISABLE_SEMAPHORE | 未强制 | 强制禁用信号量 | 优先级最高 |
| LOH_WAIT_MODE | blocked | C 端等待模式 | `nonblocked` 用旧权重继续 |
| LOH_SEM_TIMEOUT_S | 1.0 | Python sem wait 超时 | 超时后走轮询或降级 |
| LOH_POLL_SLEEP_US | 200 | Python 轮询 sleep | 影响 CPU 占用与延迟 |
| LOH_DISABLE_FSYNC | 0 | Python 写 SHM 后跳过 fsync | 提升速度，降低落盘安全性 |
| LOH_PRINT_SHM_LAYOUT | 1 | 打印共享内存布局 | 用于排查结构体偏移问题 |

### 14.2 状态维度 / 观测

| 变量 | 默认值 | 作用 | 影响/备注 |
|---|---|---|---|
| LOH_INCLUDE_HIT_MISS_FEATURES | 0 | 是否包含 Hit/Miss 特征 | 改变 CONTEXT_DIM |
| LOH_INCLUDE_CACHE_FEATURES | 0 | 是否包含 Cache 特征 | 改变 CONTEXT_DIM |
| LOH_INCLUDE_CANDIDATE_FEATURES | 0 | 是否包含候选统计特征 | 改变 CONTEXT_DIM |
| LOH_INCLUDE_TOPK_CANDIDATE_FEATURES | 0/构建可覆盖 | 是否包含 TopK 特征 | 改变 CONTEXT_DIM |
| LOH_INCLUDE_AVGTOPK_CANDIDATE_FEATURES | 0/构建可覆盖 | 是否包含 AvgTopK 特征 | 改变 CONTEXT_DIM |
| LOH_INCLUDE_REQUEST | 0 | 是否包含请求历史特征 | 改变 CONTEXT_DIM，需重建 |
| LOH_INCLUDE_WEIGHTS_IN_OBS | 1 | 是否把当前权重并入观测 | 影响策略输入 |
| RL_STATE_USE_MISSRATIO | 1 | RL 观测是否含前2维命中率 | 不改变 SHM 传输本身 |
| LOH_FIXED_OBS | 0 | 固定观测调试模式 | IPC/奖励联调常用 |

### 14.3 特征与动作映射

| 变量 | 默认值 | 作用 | 影响/备注 |
|---|---|---|---|
| LOH_FEATURE_LOG1P | 1 | 特征 log1p 变换 | 缓解重尾分布 |
| LOH_FEATURE_RECIPROCAL | 0 | 倒数衰减变换 | 常见 $1/(1+x)$ |
| LOH_FEATURE_LOG1P_RECIPROCAL | 0 | log1p 后再倒数 | 常见 $1/(1+log(1+x))$ |
| LOH_FEATURE_UNIFIED_FORMULA | 0 | 启用 unified 公式族 | 与 `LOH_UNIFIED_*` 联动 |
| LOH_FEATURE_IDENTITY | 0 | 尽量保持原始尺度 | 用于对照实验 |
| LOH_DUAL_CHANNEL | 0 | 双通道动作映射 | 每特征正负两通道 |
| LOH_USE_SOFTMAX | 1 | 动作是否 softmax | 关闭时可直接连续权重 |
| LOH_ACTION_BOUND | 1.0 | 动作边界 | 限制动作幅度 |
| LOH_ACTION_SCALE | 1.0 | 动作缩放 | 控制分布陡峭程度 |
| LOH_SOFTMAX_TEMP | 兼容参数 | 历史温度参数 | 建议优先 `LOH_ACTION_SCALE` |
| LOH_WEIGHT_EMA | 0.0 | 写回权重 EMA | 降低权重抖动 |
| LOH_WEIGHT_CLIP | 0.0 | 写回权重裁剪 | 限制极端权重 |
| LOH_SCORE_MODEL | linear | 评分模型类型 | 可设 `mlp` |
| LOH_MLP_HIDDEN | 16 | MLP 隐层宽度 | 仅 MLP 模式生效 |
| LOH_INITIAL_WEIGHTS | 未设 | 初始化权重 | C 启动时覆盖默认 |
| LOH_FIXED_WEIGHTS | 未设 | 固定线性权重 | 调试/回放常用 |
| LOH_FIXED_MLP_PARAMS | 未设 | 固定 MLP 参数 | 调试/回放常用 |

### 14.4 候选池、归一化与自动模式

| 变量 | 默认值 | 作用 | 影响/备注 |
|---|---|---|---|
| LOH_STRUCTURED_CANDIDATES | 源码默认 | 候选池规模/结构 | 影响驱逐搜索空间 |
| LOH_RANDOM_CANDIDATES | 源码默认 | 随机候选数量 | 提升探索性 |
| LOH_TAIL_SAMPLE | 源码默认 | tail 采样开关/规模 | 调整长尾覆盖 |
| LOH_TAIL_SAMPLE_DECAY | 源码默认 | tail 衰减系数 | 控制采样权重衰减 |
| LOH_USE_SIZE_BUCKETS | 源码默认 | size 结构模式 | heap vs bucket |
| LOH_ADAPTIVE_BUDGET | 源码默认 | 自适应预算 | 候选与打分开销控制 |
| LOH_USE_SCORE_REBALANCE | 源码默认 | 打分再平衡 | 抑制偏置特征 |
| LOH_SCORE_USE_IRT | 源码默认 | IRT 参与打分 | 改变特征集合 |
| LOH_SCORE_USE_COMPOUND | 源码默认 | compound 特征打分 | 扩展到组合特征 |
| LOH_SCORE_COMPOUND_V2 | 源码默认 | compound v2 策略 | 新组合形式 |
| LOH_USE_HEURISTIC_SIGNS | 1 | 启发式符号先验 | 影响正负方向语义 |
| LOH_ENABLE_FEATURE_NORMALIZATION | 0 | 固定上限归一化 | 使用 $f_i'=min(1,f_i/log(1+max_i))$ |
| LOH_ENABLE_ADAPTIVE_FEATURE_NORMALIZATION | 0 | 自适应归一化 | 分位动态缩放 |
| LOH_FEATURE_NORM_MAX_RECENCY | 源码默认 | recency 上限 | 固定归一化参数 |
| LOH_FEATURE_NORM_MAX_FREQ | 源码默认 | freq 上限 | 固定归一化参数 |
| LOH_FEATURE_NORM_MAX_SIZE | 源码默认 | size 上限 | 固定归一化参数 |
| LOH_FEATURE_NORM_MAX_IRT | 源码默认 | irt 上限 | 固定归一化参数 |
| LOH_ADAPTIVE_NORM_LO_Q | 源码默认 | 低分位 | 自适应归一化窗口参数 |
| LOH_ADAPTIVE_NORM_HI_Q | 源码默认 | 高分位 | 自适应归一化窗口参数 |
| LOH_ADAPTIVE_NORM_WARMUP | 源码默认 | 预热步数 | 预热后再启用自适应 |
| LOH_ADAPTIVE_NORM_TRANSFORM_QUANTILE | 源码默认 | 变换分位策略 | 影响缩放曲线 |
| LOH_AUTO_FEATURE_MODE | 源码默认 | 自动特征模式 | 运行期自动切换 |
| LOH_AUTO_DETECT_REQS | 源码默认 | 自动检测窗口请求数 | 自动模式稳定性参数 |
| LOH_AUTO_CV_THRESHOLD | 源码默认 | CV 阈值 | 自动切换触发条件 |
| LOH_UNIFIED_VARIANT | 源码默认 | unified 变体 | 公式具体形态 |
| LOH_UNIFIED_METHOD | 源码默认 | unified 方法 | 公式实现分支 |
| LOH_UNIFIED_ALPHA | 源码默认 | unified alpha | 公式系数 |
| LOH_UNIFIED_BETA | 源码默认 | unified beta | 公式系数 |
| LOH_UNIFIED_GAMMA | 源码默认 | unified gamma | 公式系数 |
| LOH_UNIFIED_FREQ_CAP | 源码默认 | unified freq 截断 | 抑制频率极值 |

### 14.5 奖励/惩罚与 RL 训练

| 变量 | 默认值 | 作用 | 影响/备注 |
|---|---|---|---|
| LOH_ENABLE_PENALTY | 0 | 启用 penalty 流 | 影响 reward 与 IPC 载荷 |
| LOH_PENALTY_SCALE | log | penalty 缩放方式 | `log`/`reciprocal`/`survival` |
| LOH_PENALTY_DMAX | 400000 | penalty 距离上限 | 控制极值影响 |
| LOH_PENALTY_CUTOFF | 0 | penalty 截断阈值 | 0 表示不截断 |
| LOH_SURVIVAL_QUANTILE | 0.99 | survival 分位 | survival 映射参数 |
| LOH_SURVIVAL_BINS | 64 | survival 分桶数 | 分辨率参数 |
| LOH_SURVIVAL_MINCOUNT | 1000 | survival 最小样本 | 防止冷启动噪声 |
| LOH_REWARD_MODE | absolute | 奖励形态 | `absolute`/`delta` |
| LOH_REWARD_SCALE | 1.0 | 奖励线性缩放 | 调节学习信号幅度 |
| LOH_REWARD_MIX_MODE | legacy | 奖励混合策略 | `gated_penalty_mix` 为门控混合 |
| LOH_REWARD_USE_PENALTY | 1 | 是否使用 penalty 分量 | 控制 $R_{penalty}$ |
| LOH_REWARD_USE_MISSRATIO | 0 | 是否使用 miss 分量 | 控制 $R_{miss}$ |
| LOH_REWARD_USE_MISSRATIOTREND | 0 | 是否使用趋势分量 | 控制 $R_{trend}$ |
| LOH_REWARD_USE_ORIGINAL | auto | 是否使用原始分量 | 与 penalty 开关联动 |
| LOH_REWARD_W_PENALTY | 1.0 | penalty 权重 | 线性组合系数 |
| LOH_REWARD_W_MISS | 1.0 | miss 权重 | 线性组合系数 |
| LOH_REWARD_W_TREND | 0.5 | trend 权重 | 线性组合系数 |
| LOH_REWARD_W_ORIGINAL | 0.5 | original 权重 | 线性组合系数 |
| LOH_REWARD_W_BASE_ORIG | 0.7 | gated 基础项权重 | 门控混合基础项 |
| LOH_REWARD_W_BASE_MISS | 0.3 | gated 基础项权重 | 门控混合基础项 |
| LOH_REWARD_W_BASE_TREND | 0.0 | gated 基础项权重 | 门控混合基础项 |
| LOH_REWARD_W_PENALTY_DELTA | 0.35 | gated 增量项权重 | 门控混合增量项 |
| LOH_REWARD_ORIGINAL_MAP | auto | 原始分量映射方式 | raw/clip01/center01 |
| LOH_PENALTY_GATE_MINCOUNT | 8 | gate 最小事件数 | 门控触发条件 |
| LOH_PENALTY_GATE_GOODRATE | 0.15 | gate goodrate 阈值 | 门控触发条件 |
| LOH_PENALTY_GATE_PENALTYSCALE | 1.0 | gate penalty 缩放 | 门控强度 |
| LOH_PENALTY_GATE_NO_CUTOFF_SCALE | 0.5 | 无 cutoff gate 折扣 | 门控强度 |
| LOH_PENALTY_DELTA_SCALE | 1.0 | penalty 增量缩放 | 门控增量强度 |
| LOH_PENALTY_REWARD_FORMULA | centered | penalty->reward 公式 | relative/centered/net/net2 |
| LOH_PENALTY_NET_GOOD_SCALE | 1.0 | net 公式正项系数 | net 家族公式 |
| LOH_PENALTY_NET_PENALTY_SCALE | 1.0 | net 公式负项系数 | net 家族公式 |
| LOH_PENALTY_EMPTY_AS_GOOD | 1 | 无 penalty 是否给正反馈 | 影响稀疏阶段奖励 |
| LOH_PENALTY_REFINE_ON_LATE | 1 | late penalty 是否回补 | 影响奖励时序一致性 |
| LOH_PENALTY_NO_EVICT_REWARD | keep | 无驱逐阶段奖励策略 | keep/zero |
| LOH_PENALTY_BASELINE_DECAY | 0.99 | penalty 基线衰减 | 平滑尺度估计 |
| LOH_PENALTY_SEND_POSITIVE | 源码默认 | C 端是否发送正向样本 | 影响 reward 样本分布 |
| LOH_MISS_COMPONENT | neg | miss 分量定义 | neg/improve |
| LOH_MISSRATIOTREND_WINDOW | 100 | miss trend 窗口 | 趋势平滑长度 |
| LOH_MISSRATIOTREND_MODE | slope | miss trend 模式 | slope/delta |
| LOH_TREND_WINDOW | 100 | trend 通用窗口 | 趋势平滑长度 |
| LOH_TREND_MODE | slope | trend 通用模式 | slope/delta |
| LOH_REWARD_EMA | 0 | 是否启用奖励 EMA | 降低高频噪声 |
| LOH_REWARD_EMAWINDOW | 10 | 奖励 EMA 窗口 | 平滑强度 |
| LOH_MISS_RATIO_WEIGHT | 0.7 | miss 相关权重因子 | 对 OMR/BMR 组合有影响 |
| LOH_RL_ALGO | SAC | RL 算法选择 | SAC/PPO/PPO_LSTM/TD3 等 |
| LOH_ASYNC_TRAIN | 1 | 异步训练开关 | 吞吐与稳定性权衡 |
| LOH_EXCLUDE_RECENT_STEPS | 2000 | 排除最近样本 | off-policy 采样稳定性 |
| LOH_SOFT_PRIOR | 0 | 动作头软先验开关 | 缩短收敛冷启动 |
| LOH_SOFT_PRIOR_BIAS | 0.5 | 软先验强度 | 偏置过强会抑制探索 |
| LOH_RL_SEED | 未设 | RL 随机种子 | 未设通常回退 `SEED` |
| LOH_RL_UPDATE_INTERVAL | 源码默认 | C 端触发更新间隔 | 影响同步频率 |
| LOH_ENABLE_RL | 源码默认 | 启用 RL 路径 | 关闭时回退非 RL 行为 |
| LOH_RESUME | 0 | 自动恢复训练 | 与路径变量配合 |
| LOH_RESUME_DIR | ./runs | 恢复扫描目录 | 与 `LOH_RESUME_PATH` 互补 |
| LOH_RESUME_PATH | 未设 | 显式恢复路径 | 优先级高于目录扫描 |
| LOH_CHECKPOINT_FREQ | 50000 | checkpoint 频率 | 0 可关闭自动保存 |
| RUN_TIMESTAMP | 空 | 运行标签时间戳 | 用于产物命名归档 |
| LOH_ENABLE_PROFILING | 0 | Python profiling 开关 | 影响日志与开销 |
| LOH_DEBUG_LEVEL | 0 | 调试级别 | 同时影响 C/Python 输出 |
