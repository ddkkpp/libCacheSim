# LOH 参数覆盖总结（已测试 vs 未测试）

更新时间：2026-01-31

本文件把当前项目内的实验记录（主要来自 sweeps 结果汇总与根目录历史 logs）做一次“参数覆盖”归纳：
- **已测试**：表示在现有记录中能看到该参数被显式设置/出现过不同取值（或存在明确对照）。
- **未测试/缺对照**：表示在现有记录中没有看到该参数出现，或只出现了单侧取值（因此缺少对照，不能说明行为影响）。

数据来源（只做归纳，不重跑实验）：
- `LOH_TESTED_CONFIGS_SUMMARY.md`：sweeps 全量索引、各 trace 的 sweep 细表、根目录 logs 汇总。
- `scripts/sweep_configs_*.txt`：sweep 配置来源。
- 根目录 `cachesim_sb3_*.log` / `ac_sb3_*.log`：历史运行日志（summary 行与 init 配置打印）。

---

## 1) 已测试/覆盖到的参数

### 1.1 工作负载与运行规模
- `CACHESIM_NUM_REQ`：出现过多个请求规模（例如 3M/10M/更大规模），并在部分 trace 章节里按 req 分组统计。
- `CACHE_RATIO`：在 sweeps 中以不同值出现（属于环境/运行参数维度）。

### 1.2 LOH 动作与打分路径
- `LOH_USE_SOFTMAX`：存在 softmax 与 linear（对照/切换）。
- `LOH_SCORE_MODEL`：至少出现 `linear` 与 `mlp` 两类（对照/切换）。
- `LOH_SCORE_USE_IRT` / `LOH_SCORE_USE_COMPOUND`：出现过不同组合（以 `irt`/`cpd` 的 0/1 体现）。
- `LOH_USE_HEURISTIC_SIGNS`：在 sweeps 的通用配置里出现（用于符号/方向约束）。

### 1.3 特征与状态维度开关
- `LOH_INCLUDE_CACHE_FEATURES`：cacheF=0/1 出现过。
- `LOH_INCLUDE_CANDIDATE_FEATURES`：candF=0/1 出现过。
- state 维度/模式：日志里出现过不同的 state dims（属于“确实跑过不同维度/模式”的证据）。

### 1.4 温度/缩放/更新节奏
- `LOH_SOFTMAX_TEMP`：temp 多值。
- `LOH_ACTION_SCALE`：scale 多值。
- `RL_UPDATE_INTERVAL`：int 多值。

### 1.5 惩罚项（至少一次对照）
- `LOH_ENABLE_PENALTY` + `LOH_PENALTY_SCALE`：出现过 `pen=...`（例如 `survival`）。

### 1.6 RL 侧：算法与训练超参（有记录）
- 算法：至少覆盖 `SAC / TD3 / PPO / A2C / TQC`（历史 logs 中还出现过 `PPO_LSTM`）。
- 常见超参：`batch_size`、`learning_rate`、`gamma`、`ent_coef` 在日志/汇总中多次出现。
- 部分算法特定超参：在 sweeps 配置中出现（例如 PPO/A2C/TD3/TQC 的 `*_N_STEPS`、`*_BUFFER_SIZE`、`*_TRAIN_FREQ` 等）。

---

## 2) 未测试/缺对照的参数（现有记录无法证明覆盖）

### 2.1 “只出现单侧取值”的典型项（缺对照）
- `LOH_FEATURE_LOG1P`：记录中基本只看到 `log1p=1`，未看到 `log1p=0` 的系统对照。
- `LOH_ENABLE_FEATURE_NORMALIZATION`：记录中基本只看到 `norm=1`，未看到 `norm=0` 的系统对照。
- `LOH_FEATURE_LOG1P_RECIPROCAL`：记录中多为 `recip=0`，未见 `recip=1` 的系统对照。

### 2.2 RL/SB3 深层训练项（在汇总文档里缺少显式覆盖证据）
说明：即使某些配置文件里出现过字段名，如果汇总/日志没有覆盖到或没有形成对照，这里仍把它们归为“缺少覆盖证据”。
- `tau`
- `train_freq`
- `buffer_size`
- `learning_starts`
- `gradient_steps`
- `target_entropy`
- PPO 常见：`gae_lambda`、`clip_range`

### 2.3 奖励权重的系统性网格
- `LOH_MISS_RATIO_WEIGHT` / `LOH_BYTE_MISS_RATIO_WEIGHT`：在历史 logs 中大多固定（常见为 mr=1, bmr=0），在 sweeps 中虽出现 `mrw=0.0` 这类字段，但缺少完整的“多值网格对照 + 明确赢家”归纳。

---

## 3) 下一步建议（如果要补齐覆盖）

- 在固定基础配置下补齐三组关键对照：`log1p=0/1`、`norm=0/1`、`recip=0/1`。
- 对 `LOH_MISS_RATIO_WEIGHT` 做一个小网格（例如 0/0.25/0.5/0.75/1）并固定其它参数，避免混淆。
- 对每个新加入的 sweep，在汇总中保证“通用配置 + 表内差异项”齐全，这样后续覆盖统计就不依赖人工猜测。

---

## 4) 固定权重（不使用 RL）搜索：wiki2019t / 1063（3M req）

使用脚本：`scripts/sweep_loh_constant_weights_norl.sh`

本次搜索限定的配置（按你的要求）：
- `LOH_SCORE_USE_IRT=1`
- `LOH_SCORE_USE_COMPOUND=0`
- `LOH_USE_HEURISTIC_SIGNS=1`
- `LOH_USE_SOFTMAX=1`
- `LOH_FEATURE_LOG1P=1`

同时为了减少不确定性，运行时也固定了：
- `LOH_FEATURE_LOG1P_RECIPROCAL=0`
- `LOH_ENABLE_FEATURE_NORMALIZATION=1`
- `LOH_SCORE_MODEL=linear`

运行参数：
- `CACHESIM_NUM_REQ=3000000`
- `CACHE_RATIO=0.1`
- 扫描网格：`OVERRIDE_VALUES="0,1"`（即 0/1 粗粒度组合；并启用脚本自带 refine：对 top-K 做 ±0.5 微调）

输出目录：`runs/constant_weight_norl_v01_20260131_wiki2019t_1063_3m/`

结果（以 miss ratio 最小优先，其次 byte miss ratio）：

- WikiCDN/wiki_2019t（refine 最优）
	- weights：`0.500,1,1,0,0,0`
	- miss_ratio：`0.591093`
	- byte_miss_ratio：`0.476332`
	- 证据：见 `wiki_201_refine_results.tsv` 与对应 log

- TencentCBS/1063（refine 最优）
	- weights：`1,1,1.500,0,0,0`
	- miss_ratio：`0.352518`
	- byte_miss_ratio：`0.320008`
	- 证据：见 `1063.ora_refine_results.tsv` 与对应 log

备注：这里的“最优”是指在 `0/1` 粗网格 + `±0.5` refine 范围内找到的最优；如果你要更彻底的全局搜索，可以把 `OVERRIDE_VALUES` 留空（默认 0/1/2 → 728 组合/trace），但运行时间会显著增加。
