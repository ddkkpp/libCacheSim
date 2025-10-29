# LOH RL 调参与测试指南

## 🎯 核心概念理解

### 关键换算关系

```
1 step (RL步) = 1次RL update = rl_update_interval个请求 (默认200)

示例：
- buffer_size=10000 → 存储10000步 = 2M请求的数据
- learning_starts=1000 → 收集1000步 = 200K请求后开始训练
- exclude_recent_steps=50 → 排除最新50步 = 10K请求
```

### 在线训练 vs 离线训练

**当前实现：在线训练（Online Training）** ✅ **推荐**

| 特性 | 在线训练（当前） | 离线训练 |
|------|---------------|---------|
| **数据收集** | 边运行cachesim边训练 | 先运行完cachesim，记录所有数据 |
| **训练时机** | 实时：每N步训练一次 | 事后：运行结束后批量训练 |
| **权重更新** | 实时反馈到缓存决策 | 无法影响当前运行 |
| **适用场景** | ✅ 在线自适应、持续学习 | ❌ 评估固定策略 |
| **优点** | 1. 权重立即生效<br>2. 自适应workload变化<br>3. 符合RL理念 | 1. 稳定可重现<br>2. 便于调试 |
| **缺点** | 1. 早期权重不准<br>2. 需要warm-up | 1. 无法自适应<br>2. 需要大量存储 |

**为什么选择在线训练？**

1. **实时适应**：缓存workload是动态的，在线训练能持续优化
2. **闭环反馈**：训练的权重立即用于决策，形成完整学习循环
3. **节省资源**：无需存储大量离线数据

**在线训练的挑战与应对**：

| 挑战 | 应对策略 |
|------|---------|
| 早期权重不准 | `learning_starts=1000` 延迟训练 |
| 近期奖励未修正 | `exclude_recent_steps=50` 排除采样 |
| 训练不稳定 | `train_freq=4` 降低频率 + `gradient_steps=4` 保持总量 |

---

## 📊 当前默认参数（已优化）

```python
# 训练模式默认参数
--buffer-size 10000            # Buffer容量：10000步 = 2M请求
--learning-starts 1000         # 延迟训练：1000步 = 200K请求
--exclude-recent-steps 50      # 排除采样：50步 = 10K请求
--miss-ratio-weight 1.0        # 奖励权重：100%对象miss rate

# SAC固定参数（代码中设定）
train_freq = 4                 # 每4步训练一次
gradient_steps = 4             # 每次训练4个梯度步
batch_size = 256               # 每批采样256个transitions
```

### 参数相互关系

```
buffer_size (10000)
    ↓ 存储容量
learning_starts (1000) ← 应该 < buffer_size
    ↓ 训练启动
exclude_recent_steps (50) ← 应该 << buffer_size (约5%)
    ↓ 采样保护
可采样数据 = buffer_size - exclude_recent_steps = 9950步
```

---

## 🔬 测试步骤

### 1. 基础测试（验证功能）

```bash
# 小规模测试：10K请求，检查各模块是否工作
bash test_loh_rl_sb3.sh \
    data/MetaCDN/meta_reag.oracleGeneral.zst \
    26 \
    0.1 \
    1.0 \
    200 \
    10000
```

**参数说明**：
- `26`: 26维状态向量
- `0.1`: 缓存大小10%
- `1.0`: 100% miss ratio权重
- `200`: rl_update_interval（每200请求更新一次）
- `10000`: 只处理10000个请求

### 2. 完整测试（评估性能）

```bash
# 完整运行：处理所有请求
bash test_loh_rl_sb3.sh \
    data/MetaCDN/meta_reag.oracleGeneral.zst \
    26 \
    0.1 \
    1.0 \
    200
```

---

## 📈 如何查看结果

### A. 实时监控（运行中）

```bash
# 监控Python训练日志
tail -f ac_sb3_*.log

# 关键指标：
# 1. "🔍 [SAMPLE DEBUG]" - 采样调试信息（每50次打印）
# 2. "rollout/ep_rew_mean" - 平均episode奖励
# 3. "✏️ [RETROSPECTIVE]" - 奖励修正记录
# 4. "Correction stats" - 修正统计
```

### B. 测试完成后分析

#### 1. 检查采样是否正常

```bash
grep "SAMPLE DEBUG" ac_sb3_*.log | head -20
```

**期望看到**：
```
🔍 [SAMPLE DEBUG #0]
  - effective_size: 1000
  - self.pos: 1000
  - buffer_full: False
  - exclude_recent_steps: 50
  - batch_size: 256
  - Buffer未满，采样范围: [0, 950)
  - Sample indices (first 5): [123 456 789 234 567]
```

**关键检查点**：
- ✅ `采样范围` 正确排除了最新50步
- ✅ `Sample indices` 没有超出范围
- ✅ 没有 "WARNING: Sampled from unsafe zone"

#### 2. 检查惩罚修正是否生效

```bash
grep "RETROSPECTIVE" ac_sb3_*.log | head -10
```

**期望看到**：
```
✏️ [RETROSPECTIVE] reward corrected for step #123
  - state_version: 123
  - original_reward: 0.850000
  - penalty: 0.500000
  - corrected_reward: 0.350000
  - delta: -0.500000
```

**关键指标**：
- `Correction stats: {'corrections': 42, ...}` → 修正次数
- `avg_penalty: 0.45` → 平均惩罚值
- `excluded_samples: 15` → 排除次数

#### 3. 检查训练收敛

```bash
grep "rollout/ep_rew_mean" ac_sb3_*.log
```

**健康的训练曲线**：
```
rollout/ep_rew_mean    | -0.85
rollout/ep_rew_mean    | -0.78
rollout/ep_rew_mean    | -0.72   ← 逐渐上升
rollout/ep_rew_mean    | -0.68
rollout/ep_rew_mean    | -0.65
```

#### 4. 检查C++/Python通信

```bash
# C++ 发送性能指标
grep "Sending RL request" cachesim_sb3_*.log | wc -l

# C++ 接收权重更新
grep "Updated weights from Actor-Critic" cachesim_sb3_*.log | wc -l

# 两者应该接近（允许差1-2次）
```

---

## 🎛️ 参数调优策略

### 调优流程图

```
开始测试
    ↓
检查采样是否正常？
    NO → 增大 buffer_size 或减小 exclude_recent_steps
    YES ↓
检查惩罚修正次数？
    太少(<10) → 检查Ghost cache逻辑，或延长测试时间
    正常 ↓
检查训练收敛？
    不收敛 → 调整学习率或网络结构
    震荡 → 减小 train_freq 或增大 batch_size
    收敛 ↓
检查最终性能？
    Miss rate高 → 增大 cache_size 或调整 rl_update_interval
    性能好 → 完成✅
```

### 常见问题与解决

#### 问题1：采样时报警 "Sampled from unsafe zone"

**原因**：环形buffer采样逻辑错误，采样到了应排除的区域

**解决**：
```bash
# 检查代码逻辑（已在本次修复中处理）
grep -A 20 "def sample" scripts/loh_actor_critic_sb3.py
```

#### 问题2：惩罚修正次数为0

**原因**：
1. Ghost cache miss没有发生（缓存太大或测试时间太短）
2. 惩罚队列被覆盖（`MAX_PENALTY_QUEUE_SIZE`太小）
3. 版本号映射失败

**诊断**：
```bash
# 检查Ghost cache miss
grep "Ghost cache miss" cachesim_sb3_*.log | wc -l

# 检查惩罚入队
grep "enqueue_penalty" cachesim_sb3_*.log | wc -l

# 检查Python端接收
grep "Processing penalty queue" ac_sb3_*.log | wc -l
```

**解决**：
- 如果miss=0：减小cache_size（如0.05）或增加测试请求数
- 如果入队>0但接收=0：检查共享内存同步
- 如果接收>0但修正=0：检查version映射逻辑

#### 问题3：训练不收敛或震荡

**原因**：
1. `learning_starts` 太小，早期数据质量差
2. `train_freq` 太小（=1），使用了未修正数据
3. `exclude_recent_steps` 太小，采样到未修正数据

**诊断**：
```bash
# 检查早期训练时的buffer状态
grep -A 5 "SAMPLE DEBUG" ac_sb3_*.log | head -50

# 检查修正延迟
# 计算：惩罚版本号 - 当前步数
```

**调参建议**：

| 当前值 | 症状 | 建议调整 | 新值 |
|--------|------|---------|------|
| learning_starts=1000 | 训练早就震荡 | 增大 | 2000 |
| train_freq=4 | 收敛太慢 | 减小（更频繁训练）| 2 |
| exclude_recent_steps=50 | 仍有未修正数据 | 增大 | 100 |
| buffer_size=10000 | Buffer经常满 | 增大 | 20000 |

#### 问题4：Ghost cache miss延迟过大

**现象**：
```
步骤 1000: 驱逐对象A
步骤 1500: 对象A重访（延迟500步 = 100K请求）
```

**影响**：`exclude_recent_steps=50` 不足以覆盖延迟

**解决**：
1. 测量实际延迟分布
```bash
# 从日志中提取驱逐和重访的时间差
# TODO: 编写分析脚本
```

2. 根据测量结果调整
```bash
# 如果延迟中位数是200步
python scripts/loh_actor_critic_sb3.py \
    --exclude-recent-steps 200
```

---

## 🔧 高级调优

### 自适应 exclude_recent_steps

**概念**：根据实际测量的Ghost miss延迟动态调整排除窗口

**实现**（需要扩展代码）：
```python
class AdaptiveReplayBuffer(RetrospectiveReplayBuffer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.miss_delays = []  # 记录延迟

    def update_exclude_window(self):
        if len(self.miss_delays) > 100:
            # 使用90分位数
            self.exclude_recent_steps = int(np.percentile(self.miss_delays, 90))
```

### 分阶段训练策略

**Phase 1: Warm-up**（0-1000步）
- 只收集数据，不训练
- 让buffer积累多样化数据

**Phase 2: Aggressive Training**（1000-5000步）
- `train_freq=2`（更频繁）
- 快速学习基本模式

**Phase 3: Stable Training**（5000+步）
- `train_freq=4`（当前设置）
- 稳定优化策略

---

## 📝 实验记录模板

```markdown
## 实验 #1
- **日期**: 2025-10-23
- **配置**:
  - buffer_size: 10000
  - learning_starts: 1000
  - exclude_recent_steps: 50
  - train_freq: 4
  - rl_update_interval: 200
- **数据集**: meta_reag.oracleGeneral.zst
- **请求数**: 100K
- **结果**:
  - Miss Rate: 42.3%
  - 惩罚修正次数: 87
  - 训练更新次数: 245
  - 收敛性: ✅ 稳定
- **观察**:
  - [填写具体观察]
- **下一步**:
  - [填写调整计划]
```

---

## 🎓 总结：推荐起始配置

### 快速测试（10K请求）

```bash
bash test_loh_rl_sb3.sh \
    data/MetaCDN/meta_reag.oracleGeneral.zst \
    26 0.1 1.0 200 10000

# 使用默认参数：
# buffer_size=10000 (足够大)
# learning_starts=1000 (50步后开始训练)
# exclude_recent_steps=50 (排除最新2.5%数据)
```

### 完整运行（所有请求）

```bash
bash test_loh_rl_sb3.sh \
    data/MetaCDN/meta_reag.oracleGeneral.zst \
    26 0.1 1.0 200

# 如果需要调整，使用Python参数：
python scripts/loh_actor_critic_sb3.py \
    --miss-ratio-weight 1.0 \
    --buffer-size 20000 \
    --learning-starts 2000 \
    --exclude-recent-steps 100
```

### 关键成功指标

✅ **功能正常**：
- `corrections > 0`（有惩罚修正）
- `excluded_samples > 0`（排除机制生效）
- 无 "unsafe zone" 警告

✅ **训练收敛**：
- `rollout/ep_rew_mean` 逐渐上升
- 权重更新次数 > 10
- 无大幅震荡

✅ **性能提升**：
- Miss rate < 基准算法（如LRU）
- 字节miss rate合理

---

**快速诊断命令**：
```bash
# 一键检查所有关键指标
bash scripts/analyze_training.sh ac_sb3_*.log cachesim_sb3_*.log
# TODO: 创建此脚本
```
