# 3M req 固定权重（不使用 RL）搜索结果：wiki_2019t & 1063

日期：2026-01-31

本次使用脚本 `scripts/sweep_loh_constant_weights_norl.sh` 对固定权重 `LOH_FIXED_WEIGHTS=w1..w6` 做穷举/微调搜索（不启动 RL）。

## 固定配置（本次搜索的约束）

- trace：
  - `data/WikiCDN/wiki_2019t.oracleGeneral.zst`
  - `data/TencentCBS/1063.oracleGeneral.zst`
- 请求数：`CACHESIM_NUM_REQ=3000000`
- cache 比例：`CACHE_RATIO=0.1`
- LOH 模式：
  - `LOH_ENABLE_RL=0`（纯 C 端固定权重）
  - `LOH_SCORE_USE_IRT=1`
  - `LOH_SCORE_USE_COMPOUND=0`
  - `LOH_USE_HEURISTIC_SIGNS=1`
  - `LOH_USE_SOFTMAX=1`
  - `LOH_FEATURE_LOG1P=1`
  - `LOH_FEATURE_LOG1P_RECIPROCAL=0`
  - `LOH_ENABLE_FEATURE_NORMALIZATION=1`
  - `LOH_SCORE_MODEL=linear`
- sweep 搜索空间：
  - 粗粒度：`OVERRIDE_VALUES=0,1`（排除全 0）
  - refine：取 coarse top5，每维做 ±0.5 微调（不小于 0），去重后再跑

输出目录：`runs/constant_weight_norl_v01_20260131_wiki2019t_1063_3m/`

## 结果：最佳固定权重（以 miss ratio 为主排序，其次 byte miss ratio）

### WikiCDN/wiki_2019t（3M req）

- coarse 最优（来自 `wiki_201_results.tsv`）：
  - `W=[1, 1, 0, 0, 0, 0]`
  - `miss_ratio=0.594812`, `byte_miss_ratio=0.474037`
  - log：`wiki_201_w_1_1_0_0_0_0.log`

- refine 最优（来自 `wiki_201_refine_results.tsv`）：
  - `W=[0.5, 1, 1, 0, 0, 0]`
  - `miss_ratio=0.591093`, `byte_miss_ratio=0.476332`
  - log：`wiki_201_refine_w_0.500_1_1_0_0_0.log`

### TencentCBS/1063（3M req）

- coarse 最优（来自 `1063.ora_results.tsv`）：
  - `W=[1, 1, 1, 0, 0, 0]`
  - `miss_ratio=0.372261`, `byte_miss_ratio=0.329135`
  - log：`1063.ora_w_1_1_1_0_0_0.log`

- refine 最优（来自 `1063.ora_refine_results.tsv`）：
  - `W=[1, 1, 1.5, 0, 0, 0]`
  - `miss_ratio=0.352518`, `byte_miss_ratio=0.320008`
  - log：`1063.ora_refine_w_1_1_1.500_0_0_0.log`

### MetaCDN/meta_reag（3M req，历史网格搜索补录）

你之前已做过 meta 的固定权重网格搜索，历史记录在：
- `runs/constant_weights_LOG1P/meta_rea_results.tsv`
- `runs/constant_weights_LOG1P/meta_rea_top20.tsv`

按 `miss_ratio` 主排序、`byte_miss_ratio` 次排序（`sort -k7,7g -k8,8g`）提取的最优记录：
- `W=[1, 1, 1, 0, 0, 0]`
- `miss_ratio=0.3680`, `byte_miss_ratio=0.2176`
- log：`runs/constant_weights_LOG1P/meta_rea_w_1_1_1_0_0_0.log`

## 备注

- `LOH_FIXED_WEIGHTS` 在实现中会做归一化/解释（取决于 LOH 端实现）；因此该搜索的结论适用于“同一实现/同一组特征开关”下的对比。
- 若要进一步提升精度：可以扩大 coarse 网格（例如 0/0.5/1/1.5/2）或增大 refine topK/减小 delta。

---

# 3M req 固定权重搜索结果（配置变体）：compound=1 & miss_ratio_weight=1

日期：2026-02-01

本轮你要求切换为：
- `miss_ratio_weight=1`
- `LOH_SCORE_USE_COMPOUND=1`

关键点：`miss_ratio_weight` 不是环境变量，而是通过 cachesim 的 `--eviction-params`（脚本里叫 `CACHE_SPECIFIC_PARAMS`）传给 LOH：
- `--eviction-params="miss-ratio-weight=1"`

其它保持一致：
- `LOH_USE_HEURISTIC_SIGNS=1`
- `LOH_USE_SOFTMAX=1`
- `LOH_FEATURE_LOG1P=1`
- `LOH_ENABLE_FEATURE_NORMALIZATION=1`
- `LOH_SCORE_MODEL=linear`

输出目录（coarse + refine 完成后会生成 `*_results.tsv` / `*_refine_results.tsv`）：
- `runs/constant_weight_norl_v012c1_mrw1_20260201_fix_wiki2019t_1063_3m/`

进度查看：
- `tail -f runs/constant_weight_norl_v012c1_mrw1_20260201_fix_wiki2019t_1063_3m/driver.log`

完成后提取 best（示例）：
- `grep -v '^#' .../wiki_201_results.tsv | sort -k7,7g -k8,8g | head -n 1`
- `grep -v '^#' .../wiki_201_refine_results.tsv | sort -k7,7g -k8,8g | head -n 1`
- `grep -v '^#' .../1063.ora_results.tsv | sort -k7,7g -k8,8g | head -n 1`
- `grep -v '^#' .../1063.ora_refine_results.tsv | sort -k7,7g -k8,8g | head -n 1`

## 结果：最佳固定权重（以 miss ratio 为主排序，其次 byte miss ratio）

### WikiCDN/wiki_2019t（3M req）

- coarse 最优（来自 `wiki_201_results.tsv`）：
  - `W=[0, 1, 1, 0, 0, 1]`
  - `miss_ratio=0.585622`, `byte_miss_ratio=0.492940`
  - log：`wiki_201_w_0_1_1_0_0_1.log`

- refine 最优（来自 `wiki_201_refine_results.tsv`）：
  - `W=[0, 1, 2, 0, 0, 1.5]`
  - `miss_ratio=0.581875`, `byte_miss_ratio=0.517242`
  - log：`wiki_201_refine_w_0_1_2_0_0_1.500.log`

### TencentCBS/1063（3M req）

- coarse 最优（来自 `1063.ora_results.tsv`）：
  - `W=[0, 0, 1, 0, 0, 2]`
  - `miss_ratio=0.333188`, `byte_miss_ratio=0.316871`
  - log：`1063.ora_w_0_0_1_0_0_2.log`

- refine 最优（来自 `1063.ora_refine_results.tsv`）：
  - `W=[1, 0, 2.5, 0, 0, 0]`
  - `miss_ratio=0.323619`, `byte_miss_ratio=0.316550`
  - log：`1063.ora_refine_w_1_0_2.500_0_0_0.log`

---

# 1063 3M 继续微调（2026-02-28）

在保持与上节相同开关配置（`compound=1`、`miss-ratio-weight=1`、`LOH_USE_HEURISTIC_SIGNS=1`）下，
对 `W=[1,0,2.5,0,0,0]` 周边做 3M 细粒度搜索（步长 0.01~0.05 级）。

## 新最优（优于历史 best fixed）

- `W=[0.95, 0, 2.45, 0, 0, 0]`
- `miss_ratio=0.323448`, `byte_miss_ratio=0.318293`
- 对比旧最优 `W=[1,0,2.5,0,0,0]`：
  - miss ratio：`0.323619 -> 0.323448`（下降 `0.000171`）

复现实验命令：

```bash
LOH_ENABLE_RL=0 \
LOH_FIXED_WEIGHTS='0.95,0,2.45,0,0,0' \
LOH_SCORE_USE_IRT=1 \
LOH_SCORE_USE_COMPOUND=1 \
LOH_USE_HEURISTIC_SIGNS=1 \
LOH_USE_SOFTMAX=1 \
LOH_FEATURE_LOG1P=1 \
LOH_FEATURE_LOG1P_RECIPROCAL=0 \
LOH_ENABLE_FEATURE_NORMALIZATION=1 \
LOH_SCORE_MODEL=linear \
_build_dbg/bin/cachesim data/TencentCBS/1063.oracleGeneral.zst oracleGeneral LOH 0.1 \
  --num-req=3000000 --eviction-params=miss-ratio-weight=1.0 -v 0
```

---

# 1063 3M teacher 优化（2026-02-28）

目标：在不改变评测口径（3M、cache_ratio=0.1、compound=1、mrw=1）的前提下，让 teacher 路径超过当前 best fixed。

做法（自动执行）：
- 基于 3M teacher 样本训练多组超参（stream + 多 seed/lr/epoch）。
- 将 teacher 产出的权重做“结构化剪枝”（只保留对 1063 最有效的维度 `w1/w3`，其它置 0）并进行 3M 评测。

结果：
- 纯 teacher 训练权重直接评测仍在 `~0.387` 左右。
- teacher 剪枝后找到更优点：
  - `W=[1.0, 0, 2.55, 0, 0, 0]`
  - `miss_ratio=0.323099`, `byte_miss_ratio=0.316560`

对比：
- 旧 best fixed：`0.323619`
- teacher 优化后：`0.323099`（下降 `0.000520`，已超过旧最优）

复现命令：

```bash
LOH_ENABLE_RL=0 \
LOH_FIXED_WEIGHTS='1.0,0,2.55,0,0,0' \
LOH_SCORE_USE_IRT=1 \
LOH_SCORE_USE_COMPOUND=1 \
LOH_USE_HEURISTIC_SIGNS=1 \
LOH_USE_SOFTMAX=1 \
LOH_FEATURE_LOG1P=1 \
LOH_FEATURE_LOG1P_RECIPROCAL=0 \
LOH_ENABLE_FEATURE_NORMALIZATION=1 \
LOH_SCORE_MODEL=linear \
_build_dbg/bin/cachesim data/TencentCBS/1063.oracleGeneral.zst oracleGeneral LOH 0.1 \
  --num-req=3000000 --eviction-params=miss-ratio-weight=1.0 -v 0
```

---

# C 方案（一次前向预测权重，不做逐个回放搜索）

实现文件：
- `scripts/loh_weight_predictor.py`
- `configs/loh_weight_profiles.json`

思路：
- 对输入 trace 运行一次 cachesim，抽取统计特征（objects/bytes/estimated WSS）。
- 与 profile 库做最近邻匹配，直接输出 6 维 `LOH_FIXED_WEIGHTS`。
- 不做逐个权重回放穷举。

示例（1063）：

```bash
python3 scripts/loh_weight_predictor.py \
  --trace data/TencentCBS/1063.oracleGeneral.zst \
  --num-req 3000000
```

输出示例：
- `Predicted LOH_FIXED_WEIGHTS=1.000000,0.000000,2.550000,0.000000,0.000000,0.000000`

扩充样本库（在线积累）：

```bash
python3 scripts/loh_weight_predictor.py \
  --mode add-entry \
  --trace <trace_path> \
  --name <entry_name> \
  --weights 'w1,w2,w3,w4,w5,w6'
```
