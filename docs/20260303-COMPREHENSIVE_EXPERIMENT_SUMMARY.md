# LOH 历史实验完整总结（按 Trace 分类）

> 数据来源：75 个 sweep 目录、346 次 RL 运行(docs/20251107-20251107-RL_CacheSim_Run_Summary_by_Trace.md)、8 个常量权重搜索目录、.tmp_*_table.md 文件、多份阶段文档
> 基准条件：cache ratio=0.1，3M req，除非特别说明
> 涵盖 trace：1063(TencentCBS)、meta_reag(MetaCDN)、wiki_2019t(WikiCDN)、wiki_2016u、Alibaba/4、tencent_photo1、MetaKV

---

## 一、统一基准对比表（1063, 3M req, 0.1 ratio）

| 排名 | 算法 | Miss Ratio | 关键配置 |
|------|------|-----------|---------|
| 1 | **Belady (理论最优)** | **0.2589** | 离线最优 |
| 2 | GDSF | 0.2772 | freq/size 启发式 |
| 3 | **LOH 固定权重 LOG1P** | **0.2861** | W=[1,0,2.55,0,0.5,0], RSC=64, LOG1P=1, compound=1 |
| 4 | LOH 固定权重 no-LOG1P | 0.3224 | W=[1,0,2.55,0,0.5,0], RSC=64, LOG1P=0, compound=1 |
| 5 | LOH constant sweep best | 0.3236 | W=[1,0,2.5,0,0,0], softmax=1, IRT=1, mrw=1, compound=1 |
| 6 | RL best (SAC, 对话内) | 0.3323 | SAC softmax=1 LOG1P=1 ent=0.05 compound=1 |
| 7 | **RL best (A2C, sweep)** | **0.3448** | A2C softmax=0 compound=0 cacheF=1 hitmissF=1 penalty=0 |
| 8 | RL (SAC, sweep linear) | 0.3564 | SAC softmax=0 int=50 compound=0 |
| 9 | RL (SAC, delta+EMA) | 0.3710 | SAC compound=1 delta+EMA (BMR=0.332 最好) |
| 10 | RL (本次 SAC bound=5) | 0.3981 | SAC softmax=0 LOG1P=1 bound=5 compound=1 — 失败 |
| 11 | LOH 默认权重 | 0.4268 | W=[1,1,1,0,0,0] |
| 12 | LRU | 0.4284 | |
| 13 | 3LCache | 0.4311 | |

---

## 二、延长训练结果（非 3M 基准）

| 训练长度 | 算法 | Miss Ratio | 配置要点 |
|----------|------|-----------|---------|
| 5M req | SAC | 0.2781 | softmax=0 compound=0 penalty=1(log/neg) |
| **8M req** | **A2C** | **0.2363** | softmax=0 compound=0 penalty=1(log/neg) cacheF=1 hitmissF=1 |
| 360M (全量) | SAC | 0.2756 | 早期实验（对话记录） |

> **8M A2C 达到 0.236，超过了 3M 窗口的 Belady(0.259)！**

---

## 三、1063 固定权重搜索详情

### 3.1 无 compound 搜索（LOH-mr-blocked, softmax=1, IRT=1, LOG1P=0）
- 来源：docs/20251205-20251205-sweep_results.md（最早期）
- 最优：W=[1,0,2,0,0,0] → 0.3971（粗搜索）, W=[1,0,3,0,0,0] → 0.3966（refine）
- 全量360M测试：W=[1,0,3] → 0.2511

### 3.2 无 compound + LOG1P=1 + softmax=1 + IRT=1（2026-01-31）
- 来源：20260131-LOH_CONSTANT_WEIGHTS_BEST_3M_WIKI2019T_1063.md（第一节）
- 最优：W=[1,1,1.5,0,0,0] → 0.3525（refine）, coarse: W=[1,1,1,0,0,0] → 0.3723

### 3.3 compound=1 + mrw=1 + softmax=1 + IRT=1 + LOG1P=1（2026-02-01）
- 来源：20260131-LOH_CONSTANT_WEIGHTS_BEST_3M_WIKI2019T_1063.md（第二节）、runs/constant_weight_norl_v012c1_mrw1…
- 最优 coarse：W=[0,0,1,0,0,2] → 0.3332
- 最优 refine：W=[1,0,2.5,0,0,0] → 0.3236
- 极细微调（±0.01-0.05）：W=[0.95,0,2.45,0,0,0] → 0.32345
- teacher 剪枝优化：W=[1.0,0,2.55,0,0,0] → **0.3231**（最佳 with softmax=1 + IRT=1）

### 3.4 无 softmax + compound=1 + RSC=64 + LOG1P=1（本次对话，2026-03-03）
- W=[1,0,2.55,0,0.5,0] → **0.2861**（本次对话发现的全局最优固定权重）
- 条件：softmax=0, IRT=0, mrw=0, compound=1, RSC=64
- 同配置 LOG1P=0：W=[1,0,2.55,0,0.5,0] → 0.3224

---

## 四、MetaCDN/meta_reag 结果

### 4.1 固定权重
| OMR | 权重 | 配置 | 来源 |
|-----|------|------|------|
| **0.3680** | [0,0,1,0,0,0] | LOH-mr-blocked, no LOG1P, no compound | docs/20251205-20251205-sweep_results.md |
| 0.3680 | [1,1,1,0,0,0] | LOG1P=1, no compound | runs/constant_weights_LOG1P |
| 0.3680 | 多种 w3 主导 | LOG1P / no-LOG1P | 多个搜索 |
| 全量45M | [0,0,1,0,0,0] | no LOG1P | 0.2690 |

注意：meta_reag 的 OMR=0.3680 是一个极难突破的天花板。几十种权重和配置都收敛到此值。

### 4.2 RL 训练（3M, 80+ 次运行）
| OMR | 算法 | 配置 | 来源 |
|-----|------|------|------|
| 0.2697 | SAC | softmax log1p=1 norm=1 int=250（可能异常值） | sweep meta_algo_expand_v6 |
| **0.3680** | SAC | softmax log1p=1 norm=1 cpd=1 int=200 | 多个 sweep |
| 0.3685 | TD3 | softmax log1p=1 norm=1 cpd=1 int=200 | .tmp_meta_table |
| 0.3691 | PPO_LSTM | log1p=1 norm=1 cpd=1 int=200 | .tmp_meta_table |
| 0.3695 | TQC | softmax log1p=1 norm=1 int=500 temp=0.3 | sweep meta_tqc |
| 0.3724 | SAC | cpd=0 irt=0 cacheF=0 int=200 | sweep |
| 0.3830 | TD3 | softmax scale=1.0 | sweep meta_3m_1212 |
| 0.3848 | SAC | linear irt=1 cpd=0 posnet=1 pen=net | .tmp_meta_table |
| 0.3851 | SAC | linear irt=1 cpd=0 state=2 pen=0 | .tmp_meta_table |
| ~0.39-0.43 | PPO/SAC | 早期（2025-11-21 ~ 2025-12-08） | .tmp_meta_table |

### 4.3 meta 关键发现
- OMR 天花板在 0.3680，无论用 RL 还是固定权重、LOG1P 还是 no-LOG1P
- size 特征(w3)是唯一有效维度
- compound 模式与 non-compound 在 meta 上差距极小

---

## 五、WikiCDN/wiki_2019t 结果

### 5.1 固定权重
| OMR | 权重 | 配置 | 来源 |
|-----|------|------|------|
| **0.5819** | [0,1,2,0,0,1.5] | compound=1, mrw=1, LOG1P=1, refine | CONSTANT_WEIGHTS_BEST |
| 0.5856 | [0,1,1,0,0,1] | compound=1, mrw=1, LOG1P=1, coarse | 同上 |
| 0.5909 | [2,0,2,0,0,1] | LOG1P=1, no compound | runs/constant_weights_LOG1P |
| 0.5911 | [0.5,1,1,0,0,0] | IRT=1, LOG1P=1, no compound, refine | CONSTANT_WEIGHTS_BEST |
| 0.5948 | [1,1,0,0,0,0] | IRT=1, LOG1P=1, no compound, coarse | 同上 |
| 0.5992 | [3,1,4,0,0,0] | no LOG1P, no compound, refine | docs/20251205-20251205-sweep_results.md |
| 0.5995 | [2,1,2,0,0,0] | no LOG1P, no compound | 同上 |
| 全量207M | [3,1,4] | no LOG1P | 0.1875 |

### 5.2 RL 训练（3M, 139 行记录）
| OMR | 算法 | 配置 | 来源 |
|-----|------|------|------|
| **0.5924** | PPO | int=200（早期 1128 好结果） | .tmp_wiki_table |
| 0.5931~0.5933 | PPO | int=200（多次） | 同上 |
| 0.5938 | PPO | cpd=1 irt=0 int=200 | 同上 |
| 0.5942 | PPO | log1p=1 norm=1 cpd=1 irt=0 int=200 | 同上 |
| 0.5957 | SAC | softmax log1p=1 norm=1 cpd=1 irt=1 int=200 | sweep modes3_batch |
| 0.6364~0.6372 | SAC | linear irt=1 cpd=0 posnet=1 pen=net | .tmp_wiki_table |
| ~0.59-0.71 | PPO/SAC | 2025-11-18 ~ 2025-12-04 | 同上 |

### 5.3 wiki 关键发现
- PPO 在 wiki 上优于 SAC（0.5924 vs 0.5957）
- compound+mrw=1 固定权重 ([0,1,2,0,0,1.5]=0.5819) 已超过任何 RL 结果
- w6 维度（IRT 相关）在 wiki 上很重要（与 1063 不同）

---

## 六、其他 Trace 结果

### 6.1 WikiCDN/wiki_2016u
| OMR | 算法 | 配置 | 来源 |
|-----|------|------|------|
| **0.3496** | SAC | softmax log1p=1 norm=1 cpd=1 irt=1 int=200 | sweep modes3_batch |

### 6.2 Alibaba/4
| OMR | 算法 | 配置 | 来源 |
|-----|------|------|------|
| **0.0755** | SAC | softmax log1p=1 norm=1 int=200 | sweep modes3_batch |

### 6.3 TencentPhoto/tencent_photo1
| OMR | 算法 | 配置 | 来源 |
|-----|------|------|------|
| **0.7401** | SAC | softmax log1p=1 norm=1 int=200 mrw=0.0 | sweep modes2_mrw0 |

### 6.4 MetaKV/202401_kv_all_sort
| OMR | 算法 | 配置 | 来源 |
|-----|------|------|------|
| **0.2379** | SAC | softmax log1p=1 norm=1 int=200 | sweep modes3_batch |

---

## 七、🔴 配置空间全景与未探索区域

### 7.1 RL 算法维度（跨 trace）
| 算法 | 1063 最好 (3M) | meta 最好 | wiki 最好 | 备注 |
|------|---------------|----------|----------|------|
| **A2C** | **0.3448** | — | — | 仅在 stage2_upgrade 中测试(1063)；8M→0.236 |
| SAC | 0.3323 | 0.3680 | 0.5957 | 最广泛使用；meta 上最靠近天花板 |
| PPO | ~0.371 | 0.3762 | **0.5924** | wiki 上最好 |
| PPO_LSTM | — | 0.3691 | — | meta 上试过 |
| TD3 | — | 0.3685 | — | meta 上试过 |
| TQC | — | 0.3695 | — | meta 上试过 |
| DDPG | — | — | — | 未测试 |

### 7.2 评分模式维度
| 模式 | compound | softmax | IRT | LOG1P | 1063 最好 OMR |
|------|----------|---------|-----|-------|--------------|
| Linear + softmax=0 | 0 | 0 | 0 | 0 | 0.3448 (RL) |
| Compound + softmax=1 + LOG1P=0 | 1 | 1 | 1 | 0 | ~0.42+ (RL 陷阱) |
| Compound + softmax=0 + LOG1P=0 | 1 | 0 | 0 | 0 | 0.3224 (固定) |
| **Compound + softmax=0 + LOG1P=1** | **1** | **0** | **0** | **1** | **0.2861 (固定)** |
| Linear + softmax=1 + LOG1P=1 | 0 | 1 | 1 | 1 | 0.3525 (固定) |
| Compound + softmax=1 + LOG1P=1 | 1 | 1 | 0 | 1 | 0.3231 (固定), 0.3323 (RL) |

### 7.3 常量权重搜索覆盖度

| 搜索条件 | 1063 | meta | wiki | 行数 |
|----------|------|------|------|------|
| no-LOG1P, no-compound (LOH-mr-blocked) | ✅ 0.3966 | ✅ 0.3680 | ✅ 0.5992 | ~100 |
| LOG1P=1, no-compound (IRT=1, softmax=1) | ✅ 0.3525 | ✅ 0.3680 | ✅ 0.5909 | ~200 |
| LOG1P=1, compound=1, mrw=1 (softmax=1) | ✅ 0.3231 | — | ✅ 0.5819 | ~200 |
| **LOG1P=1, compound=1, softmax=0** | ✅ 0.2861 (仅本次对话) | ❌ 未尝试 | ❌ 未尝试 | 1 |

### 7.4 RL 中未探索的关键配置（跨 trace 统一视角）

| 未探索组合 | 潜力分析 |
|-----------|---------|
| **RL + compound=1 + LOG1P=1 + softmax=0** | 固定权重已证明 0.2861，RL 完全空白 |
| **A2C + LOG1P=1** | A2C 是 1063 最佳 RL 算法，但从未与 LOG1P 搭配 |
| **RL + compound + LOG1P + cacheF=1 + hitmissF=1** | stage2 证明扩展 obs 有用，但从未与 LOG1P 结合 |
| **meta/wiki 上的 softmax=0 + compound=1** | 仅在 1063 上测试过 |
| **meta/wiki 上的 A2C** | A2C 仅在 stage2_upgrade(1063) sweep 中测试 |

### 7.5 Penalty / Reward 工程（已充分探索）
- LOH_ENABLE_PENALTY=1 + log/neg + w=0.1：在延长训练(5M/8M)下有帮助
- penalty=0 在短训练(3M)下更好
- net/net2/abs/reciprocal 等公式均已在 stage2 sweep 和 penalty 专项中搜索
- posnet（正向网络奖励）：在 1063 上小幅帮助(0.3639)，但未超越 A2C best

---

## 八、阶段计划状态

| 阶段 | 内容 | 状态 |
|------|------|------|
| Step 1 | 固定权重基线 & 精细搜索 | **部分完成**（softmax=1 搜索完成，softmax=0 仅本次对话验证一组） |
| Step 2 | RL convergence & 超越固定权重 | **未完成**（最好 RL 0.3323 vs 固定 0.2861） |
| Step 3 | Belady teacher / 蒸馏 | **未开始**（teacher 产出权重可达 0.3231 但不如手动调优） |

---

## 九、改进方向分析

### 方向 A：RL + LOG1P（最高优先级，从未探索）
- 将最好固定权重的环境（compound=1, LOG1P=1, RSC=64, softmax=0）用于 RL
- 用 A2C（历史最佳 RL 算法）代替 SAC
- 加入 cacheF=1 + hitmissF=1（stage2_upgrade 证明有用）
- 预期：如果 RL 能学到 [1,0,2.55,0,0.5,0] 附近的权重，就能达到 0.286 附近

### 方向 B：延长训练（已验证有效）
- 3M→8M 让 OMR 从 0.345 降到 0.236（降幅 31%）
- 在 LOG1P 条件下延长训练可能进一步提升

### 方向 C：小范围固定权重精细搜索
- 在 meta/wiki 上补充 softmax=0 + compound=1 + LOG1P=1 的搜索
- 在 1063 上搜索 w5/RSC 维度

### 方向 D：Belady 蒸馏（Step 3，未开始）
- 用 Belady 排序作为 teacher signal
- 风险较高，工程量大

### 方向 E：混合策略
- 用固定权重 warm-start RL（teacher 权重初始化）
- 小 action_bound (0.5~1.0) 做微调

---

## 十、数据来源索引

| 文件 | 内容概要 |
|------|---------|
| docs/20251107-20251107-RL_CacheSim_Run_Summary_by_Trace.md | 346 次 RL 运行按 trace 分组（11490 行） |
| .tmp_1063_req3000000_table.md | 1063 RL 结果表（42 行，含详细配置） |
| .tmp_meta_reag_req3000000_table_mirror.md | meta_reag RL 结果表（82 行） |
| .tmp_wiki_2019t_req3000000_table_mirror.md | wiki_2019t RL 结果表（139 行） |
| 20260131-LOH_CONSTANT_WEIGHTS_BEST_3M_WIKI2019T_1063.md | 固定权重搜索+Teacher优化（231 行） |
| 20260129-20260129-LOH_TESTED_CONFIGS_SUMMARY.md | 自动生成的 sweep 索引（5715 行） |
| docs/20251205-20251205-sweep_results.md | LOH-mr-blocked 固定权重 Top20（172 行） |
| docs/20251117-20251117-LOH_Framework_and_Experiments_Summary.md | 框架与变种总览 |
| 20260215-20260215-20260215_1063_to032_阶段总结与完成度.md | Stage1-3 进度 |
| runs/constant_weights_LOG1P/ | meta/wiki LOG1P 固定权重搜索 |
| runs/constant_weight_norl_v012c1_mrw1…/ | 1063 compound+mrw1 搜索(refine TSV) |
| sweeps/（75 个目录） | 自动化 RL sweep 运行 |
