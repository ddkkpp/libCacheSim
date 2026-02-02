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
