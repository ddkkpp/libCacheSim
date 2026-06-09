# 各实验配置异同对比

## 实验概览

| 实验 | 数据来源 | 缓存 | 用途 |
|---|---|---|---|
| **cs01 / cs0001 (CMA-ES v7)** | `docs/baseline_three_cache_compare.md`（来自 per-group ablation） | cache01 + cache0001 | 各 group 独立 CMA-ES 的 best_LOH（v7 策略） |
| **step2** | `tmp/20260514-step2-cache0001-manifest/` | cache0001 | step02_event_rebuild，预评分队列完整版 |
| **r128** | `tmp/20260512-loh-route-ablation/final-step01-step02-r128/` | cache01 | step01_health_guard + step02_event_rebuild |
| **original** | `tmp/20260606-loh-adaptive-batch-experiments/` | cache01 + cache0001 | 当前 LOH 默认行为，f001_orig |
| **pool_off_b16** | `tmp/20260606-loh-adaptive-batch-experiments/` | cache01 + cache0001 | 驱逐池全关，batch=16 |

---

## 并行数与任务规模

| 实验 | 并行数 | 任务数 | 缓存数 | 备注 |
|---|---|---|---|---|
| step2 | 80 | 11748（MR+BMK 各 5874） | cache0001 仅 1 种 | 逐 variant 顺序执行 |
| r128 | 80 | 11748（MR+BMK 各 5874） | cache01 仅 1 种 | step01 + step02 各 1 组 |
| original | 80 | 11536/variant | cache01 + cache0001 共 2 种 | 含 12 个 variant，overlap 调度 |
| pool_off_b16 | 80 | 11536/variant | cache01 + cache0001 共 2 种 | 同上批 |
| per-group (cs01) | - | 各 group 独立运行 | 固定 0.1/0.001 | CMA-ES 每个 group 单独跑 |

---

## LOH 环境变量完全一致

以下参数在 step2、r128、original 三组实验中完全相同：

| 参数 | 值 | 说明 |
|---|---|---|
| `LOH_EVICT_POOL_ENABLE` | 1 | 启用跨请求驱逐队列 |
| `LOH_EVICT_POOL_NEWOBJ` | 1 | 新对象尝试插入队列 |
| `LOH_EVICT_POOL_REFILL` | 1 | 弹出时同源补填 |
| `LOH_EVICT_POOL_GUARD` | 1 | 守卫审计 |
| `LOH_EVICT_POOL_EVENT_REBUILD` | 1 | 健康事件重建队列 |
| `LOH_EVICT_POOL_GUARD_REBUILD_ONLY` | 1 | 守卫仅重建不关池 |
| `LOH_EVICT_POOL_HEALTH_LOG` | 1 | 健康日志 |
| `LOH_EVICT_POOL_ADAPTIVE` | 0 | 非自适应模式 |
| `LOH_EVICT_POOL_SOURCE_ADAPTIVE` | 0 | 非源自适应 |
| `LOH_EVICT_POOL_LOW_WATERMARK` | 0 | 不启用低水位重建 |
| `LOH_EVICT_POOL_NEWOBJ_STAGING` | 0 | 不启用暂存模式 |
| `LOH_EVICT_POOL_WARMUP_ALLOWLIST` | 0 | 不启用预热白名单 |
| `LOH_BATCH_EVICT_SIZE` | 4 | 队列容量 4 |
| `LOH_SCORE_USE_COMPOUND` | 1 | compound 评分 |
| `LOH_SCORE_USE_IRT` | 0 | 不使用 IRT 特征 |
| `LOH_FEATURE_LOG1P` | 1 | log1p 特征变换 |
| `LOH_USE_SIZE` | 1 | size 特征 |
| `LOH_USE_REC_SIZE` | 1 | rec×size 特征 |
| `LOH_USE_FREQ_SIZE` | 0 | 关闭 freq×size |
| `LOH_STRUCTURED_CANDIDATES` | 16 | 结构化候选数 |
| `LOH_ENABLE_CMAES` | 1 | CMA-ES 启用 |
| `LOH_BUILD_RELEASE` | 1 | release 编译 |
| `LOH_DEBUG_LEVEL` | 0 | 关闭调试日志 |

> step02_event_rebuild 在 **per-group ablation（cs01/cs0001）** 中也使用相同的 step 定义，因此上述配置一致。

---

## 环境变量差异

### 明显差异

| 参数 | step2 | r128 | original | pool_off_b16 | 影响分析 |
|---|---|---|---|---|---|
| `LOH_RANDOM_CANDIDATES` | **128** | **128** | 256 | 256 | 256 候选→更多样本→理论上 MR 应更好，但 original 反而差 |
| `LOH_RNG_SEED` | **101** | **101** | 未设置 | 未设置 | 影响 CMA-ES 随机收敛路径 |
| `LOH_USE_FREQ_REC`（MR 目标） | 0 | 0 | 0 | 0 | 一致 |
| `LOH_USE_FREQ_REC`（BMR 目标） | 1 | 1 | — | — | original/pool_off 仅 f001_orig，无 BMR 分流 |

### 缓存大小模式

| 实验 | 模式 | 说明 |
|---|---|---|
| step2 | **固定比例** | cache_size=0.001（cachesim 在线算 WSS × 比例） |
| r128 | **固定比例** | cache_size=0.1（同上） |
| original/pool_off_b16 | **wss-map** | 从预计算 WSS 映射表读 WSS × 比例 |

昨日验证：`wss_map.tsv` 中的 WSS 值与 cachesim 在线计算的 WSS **完全一致**（alibabaBlock_0 = 828316282880 B），因此实际缓存大小等价。

### cfg 策略

| 实验 | MR 目标 | BMR 目标 |
|---|---|---|
| cs01/cs0001 (v7) | `f001_orig`（fallback `f100_ns`） | `one_hit≤0.72→f100_ns`，否则 `f101_orig` |
| step2 | `f001_orig` | `one_hit≤0.72→f100_ns`，否则 `f101_orig` |
| r128 | `f001_orig` | 同上 |
| original | `f001_orig`（固定） | `f001_orig`（固定） |
| pool_off_b16 | `f001_orig`（固定） | `f001_orig`（固定） |

original/pool_off 固定跑 f001_orig，**不按 one_hit 阈值分流**，这是 BMR 偏高的主要原因。

### trace 顺序

各实验使用不同的 manifest 文件，trace 遍历顺序不同，影响 CMA-ES 权重收敛路径：

| 实验 | manifest 来源 | group 顺序 |
|---|---|---|
| step2 | `tmp/20260507-drl-v7-cache0001-plan/manifest.tsv` | （manifest 默认顺序） |
| r128 | `tmp/20260510-drl-v7-omr-cache01-plan/manifest.tsv` + BMR 版本 | （manifest 默认顺序） |
| original | `tmp/20260524-drl-v7-manifest-selected/cache01_mr.tsv` | tencentPhoto→metaKV→wiki→metaCDN→alibabaBlock→tencentBlock |

---

## MR 表现汇总

### cache01 — 相对 MR（越低越好）

| 配置 | 组平均 | 说明 |
|---|---|---|
| cs01 (CMA-ES v7) | **0.7334** | per-group CMA-ES，pre-5/19 代码 |
| r128 step02 | **0.7333** | cross-group CMA-ES，pre-5/19 代码 |
| pool_off_b16 | **0.7477** | post-5/19 代码，但 NEWOBJ=0（pool 全关） |
| original | **0.8451** | post-5/19 代码，pool 全开，NEWOBJ=1 |

### cache0001 — 相对 MR

| 配置 | 组平均 | 说明 |
|---|---|---|
| cs0001 (CMA-ES v7) | **0.7553** | per-group CMA-ES，pre-5/19 代码 |
| step2 | **0.7539** | cross-group CMA-ES，pre-5/19 代码 |
| pool_off_b16 | **0.7710** | post-5/19 代码，NEWOBJ=0 |
| original | **0.7872** | post-5/19 代码，NEWOBJ=1 |

> **关键现象**：pre-5/19 代码（step2/r128）与 per-group 结果一致（~0.73-0.75）。post-5/19 代码下，pool_off_b16（NEWOBJ=0）介于二者之间，original（NEWOBJ=1）最差。

---

## 未决问题

1. **RANDOM_CANDIDATES=256 反而不如 128** — step2 用 128 候选取得 0.7539，original 用 256 仅 0.7872。候选更多应找到更优淘汰对象，但实际相反。可能与其他因素（种子、顺序）耦合。
2. **post-5/19 代码 vs pre-5/19 代码的隐含差异** — 虽然 pool 配置变量一致，但 post-5/19 代码在队列管理逻辑上有实质变更（如 `evict_queue_insert_scored` 使用 obj_id 哈希表查找替代原指针直接引用、新增 `weight_epoch` 同步、队列最大年龄默认 500 等），这些可能影响 CMA-ES 权重更新的稳定性。
3. **建议控制实验**：在 step2 代码上跑 `RANDOM_CANDIDATES=256`，或在 post-5/19 代码上设 `NEWOBJ=0+REFILL=0` 跑一组，分别隔离两个变量的影响。
