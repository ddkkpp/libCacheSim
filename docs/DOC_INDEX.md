# LOH强化学习文档索引

本文件提供libCacheSim中LOH强化学习集成的快速导航。

## 📁 文件夹结构

```
libCacheSim/
├── test_loh_rl_sb3.sh        # 主测试脚本（保留在根目录）
├── test_scripts/              # 其他测试脚本（按时间戳命名）
│   ├── README.md             # 脚本使用说明
│   ├── 10282046-test_reward_improvement.sh
│   └── ...
├── docs/                      # 说明文档（按时间戳命名）
│   ├── README.md             # 文档索引
│   ├── 10282026-REWARD_IMPROVEMENT_PLAN.md  # ⭐ 最新改进方案
│   ├── 10272237-PENALTY_QUEUE_OPTIMIZATION.md
│   └── ...
└── DOC_INDEX.md              # 本文件
```

## 🚀 快速开始

### 1. 运行主测试
```bash
# 从仓库根目录执行
CACHESIM_NUM_REQ=10000000 LOH_DEBUG_BASIC=1 \
bash ./scripts/test_loh_rl_sb3.sh data/WikiCDN/wiki_2019t.oracleGeneral.zst
```

### 2. 查看TensorBoard
```bash
tensorboard --logdir ./runs --port 6006
```

### 3. 关键监控指标
- `loh/reward_std` - 奖励标准差（期望 > 0.1）
- `loh/penalty_baseline` - Penalty基线（应逐渐下降）
- `train/actor_loss` - Actor损失
- `train/critic_loss` - Critic损失

## 📚 重要文档

### 必读（按优先级）
1. **[奖励改进方案](docs/10282026-REWARD_IMPROVEMENT_PLAN.md)** ⭐ 最新
   - 解决reward缺乏差异性问题
   - 纯penalty-based奖励公式
   - 连续运行策略

2. **[测试脚本说明](test_scripts/README.md)**
   - 各个测试脚本的用途
   - 使用方法和注意事项

3. **[文档索引](docs/README.md)**
   - 所有文档的分类和阅读顺序
   - 快速参考配置

### 进阶阅读
- [SAC算法回顾](docs/10230213-SAC_RETROSPECTIVE_GUIDE.md) - 算法原理
- [超参数调优](docs/10230213-TUNING_GUIDE.md) - 调优技巧
- [Ctrl+C行为](docs/10241746-CTRL_C_BEHAVIOR.md) - 优雅停止

### 问题排查
- [Penalty修复总结](docs/10232259-PENALTY_FIXES_SUMMARY.md)
- [时间戳改进](docs/10232259-EVICTION_TIMESTAMP_IMPROVEMENT.md)

## 🔧 当前配置（2025-11-25）

### 环境变量

#### 状态向量模块控制（编译时）
| 环境变量 | 默认值 | 说明 |
|---------|-------|------|
| `LOH_INCLUDE_HIT_MISS_FEATURES` | 0 | 包含命中/未命中特征（24维） |
| `LOH_INCLUDE_CACHE_FEATURES` | 0 | 包含缓存统计特征（12维） |
| `LOH_INCLUDE_CANDIDATE_FEATURES` | 0 | 包含候选对象特征（72维） |
| `LOH_INCLUDE_SAMPLE_FEATURES` | 1 | 包含蓄水池采样特征（192维） |

**默认状态维度**：2（GLOBAL）+ 192（SAMPLE）= 194 维

#### 蓄水池采样参数
| 参数 | 值 | 说明 |
|-----|-----|------|
| `N_SAMPLES` | 32 | 总采样容量（8组 × 4对象/组） |
| `SAMPLES_PER_EVICTION` | 4 | 每次驱逐采集的最低分数对象数 |
| **算法** | 真蓄水池 | 前8组直接填充，之后以概率 8/i 替换随机组 |

#### 其他运行时变量
| 环境变量 | 默认值 | 说明 |
|---------|-------|------|
| `LOH_DEBUG_LEVEL` | 0 | 调试级别（0=关闭，1=BASIC，2=VERBOSE，3=DETAILED） |
| `LOH_PARALLEL_SAFE` | 0 | 并行安全模式（共享内存同步） |
| `LOH_FEATURE_LOG1P` | 0 | 特征使用 log1p 变换 |
| `CACHESIM_NUM_REQ` | - | 模拟请求数量 |
| `PYTHON_SCRIPT` | - | Python RL 脚本名称 |
| `EVICTION_ALGO` | - | 驱逐算法名称 |

#### 特征归一化参数（运行时，C 端）
| 环境变量 | 默认值 | 说明 |
|---------|-------|------|
| `LOH_FEATURE_NORM_MAX_RECENCY` | 128e6 | Recency 特征归一化上限（时间差/IRT 同阶） |
| `LOH_FEATURE_NORM_MAX_FREQ` | 1e6 | Frequency 特征归一化上限（访问次数） |
| `LOH_FEATURE_NORM_MAX_SIZE` | 16e9 | Size 特征归一化上限（字节） |
| `LOH_FEATURE_NORM_MAX_IRT` | 128e6 | IRT 特征归一化上限（所有 IRT 共享） |

#### 动作 / Softmax / Soft Prior（Python 端）
| 环境变量 | 默认值 | 说明 |
|---------|-------|------|
| `LOH_RL_ALGO` | SAC | RL 算法选择（SAC / PPO / TD3） |
| `LOH_DUAL_CHANNEL` | 1 | 是否使用双通道动作（2×6 logits，pos-neg 差分） |
| `LOH_USE_SOFTMAX` | 1 | 是否对动作做 softmax（1=概率形式，0=直接权重） |
| `LOH_SOFTMAX_TEMP` | 1.0 | softmax 温度系数，>1 更平滑，<1 更尖锐 |
| `LOH_PPO_SOFT_PRIOR` | 0 | PPO 是否启用软先验初始化（只在模型创建时生效一次） |
| `LOH_PPO_SOFT_PRIOR_BIAS` | 0.5 | 软先验偏置强度（logits 级别，越大初始越靠近启发式） |

> 典型大规模 trace（Wiki / Meta）建议适当放大这些上限，以减少特征裁剪（clip），可结合 C 端 epoch 统计中的 `feature_clip_count/feature_sample_count` 比例做调参。

### 奖励机制
```python
# 无驱逐时中性奖励
if evicted_count == 0:
    reward = 0.0

# 基于penalty的相对奖励
else:
    penalty_sum = obj_penalty_weight * obj_penalty +
                  byte_penalty_weight * byte_penalty

    if baseline > 1e-6:
        reward = (baseline - penalty_sum) / baseline
    else:
        reward = -penalty_sum

    baseline = 0.99 * baseline + 0.01 * penalty_sum
    reward = clip(reward, -1.0, 1.0)
```

### 超参数
| 参数 | 值 | 说明 |
|-----|-----|------|
| `learning_starts` | 1000 | 开始训练前的步数 |
| `exclude_recent_steps` | 100 | 排除最近N步计算final reward |
| `obj_penalty_weight` | 1.0 | 对象penalty权重 |
| `byte_penalty_weight` | 0.0 | 字节penalty权重 |
| `buffer_size` | 10000 | 经验回放缓冲区大小 |

### 运行模式
- ✅ 连续运行（`truncated = False`）
- ✅ 无episode边界
- ✅ 100%样本利用率

## 📝 命名规则

### 时间戳格式：`MMDDHHMM`
- `MM` - 月份（10 = 10月）
- `DD` - 日期（28 = 28日）
- `HH` - 小时（20 = 20点）
- `MM` - 分钟（26 = 26分）

### 示例
- `10282026-REWARD_IMPROVEMENT_PLAN.md` = 2025年10月28日 20:26
- `10282044-test_loh_rl_sb3.sh` = 2025年10月28日 20:44

## 🔍 查找文档

### 按时间查找
```bash
# 查看今天的文档
ls -lt docs/1028*.md

# 查看最新的测试脚本
ls -lt test_scripts/*.sh | head -5
```

### 按内容查找
```bash
# 搜索包含"reward"的文档
grep -r "reward" docs/*.md

# 搜索包含"penalty"的脚本
grep -r "penalty" test_scripts/*.sh
```

## 📞 联系与贡献

- 维护者：libCacheSim开发团队
- 最后更新：2025年10月28日
- 版本：v1.0

---

**提示**：所有路径都相对于仓库根目录 `/home/dingkp/libCacheSim/`
