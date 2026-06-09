# 不同版本 best_LOH 相对 LRU 对比

数据来源：

- **cs01**：`docs/20260422-ablation-per-group-cache01/cmaes版本LOH/baseline_summary_v7_3lcache-omr.md`
- **cs0001**：`docs/20260423-ablation-per-group-cache0001/cmaes版本/baseline_summary_v7_3lcache-omr.md`
- **cs0001-fix**：`docs/20260423-ablation-per-group-fixxxx-cache0001/cmaes版本LOH/baseline_summary_v7_3lcache-target.md`

全部使用 v7 固定策略（MR=f001_orig，BMR 按 one_hit 阈值分流）。cs0001-fix 仅在 fix content.log 涉及的 8 条 trace 上有 BMR 修正（metaKV×3、wiki×3、tencentPhoto×2）。

| 版本 | 指标 | alibabaBlock | metaCDN | metaKV | tencentBlock | tencentPhoto | wiki | 6组平均 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| cs01 | MR | 0.7577 | 0.7957 | 0.6803 | 0.7436 | 0.8910 | 0.5323 | 0.7334 |
| cs01 | BMR | 0.8743 | 0.8749 | 0.9258 | 0.8935 | 0.9945 | 0.7708 | 0.8890 |
| cs0001 | MR | 0.8772 | 0.6849 | 0.5571 | 0.8793 | 0.8732 | 0.6603 | 0.7553 |
| cs0001 | BMR | 0.9513 | 0.9187 | 0.9630 | 0.9436 | 1.0452 | 0.9074 | 0.9549 |
| cs0001-fix | MR | 0.8772 | 0.6849 | 0.5571 | 0.8793 | 0.8732 | 0.6603 | 0.7553 |
| cs0001-fix | BMR | 0.9513 | 0.9187 | **0.9028** | 0.9436 | **0.9606** | **0.8631** | **0.9234** |

> MR 三版本完全一致；BMR 仅 cs0001-fix 在 metaKV、tencentPhoto、wiki 三组有变化（加粗标出），其余同 cs0001。cs01 独立为另一 cache 设置。

## 综合指标 (cs01+cs0001)

四值均值：`(cs01_MR + cs01_BMR + cs0001_MR + cs0001_BMR) / 4`。

| 版本组合 | alibabaBlock | metaCDN | metaKV | tencentBlock | tencentPhoto | wiki | 6组平均 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| cs01 + cs0001 | 0.8651 | 0.8186 | 0.7816 | 0.8650 | 0.9510 | 0.7177 | 0.8332 |
| cs01 + cs0001-fix | 0.8651 | 0.8186 | **0.7665** | 0.8650 | **0.9298** | **0.7066** | **0.8253** |
