# LOH 算法框架与变种 + 实验问题总览

> 本文汇总当前仓库中 LOH 驱逐算法及其 C/Python 变种的整体框架，并结合 `result/wiki_2019t.oracleGeneral.zst.cachesim` 和已有 TB/日志总结实验现象与问题，作为后续调试与论文整理的统一入口。

---

## 1. 整体框架概览

### 1.1 系统组成

- **C 端（`libCacheSim` 驱逐算法）**
  - 核心实现：`libCacheSim/cache/eviction/LOH.c`。
  - 关键数据结构：
    - LRU 队列（q_head/q_tail）维护 recency；
    - 频率表 `freq_table[1..FREQ_MAX]` 维护 LFU 维度；
    - 尺寸桶 `size_buckets` 维护 size 维度；
    - 3 个 IRT 堆维护 IRT 历史（访问间隔）；
    - Ghost cache 保存被驱逐对象的历史特征；
    - penalty 队列，用于延迟惩罚和事后奖励修正；
    - 38 或 26 维基础状态向量 + 可选 72 维候选汇总特征（共 `CONTEXT_DIM`）。
  - RL 集成：通过 `shm_data_t` 共享内存 + POSIX 信号量，与 Python 进程同步：
    - C 端定期在 `sync_with_actor_critic()` 中写入状态向量、miss 统计和 penalty 聚合；
    - Python 端读取 state，执行策略网络推理并写回 6 维特征权重；
    - C 端在驱逐评分时使用这些权重线性加权 6 维特征。

- **Python 端（RL 训练 / 推理脚本）**
  - 主脚本：`scripts/loh_actor_critic_sb3.py`（SAC + 事后惩罚 + 丰富 profiling）。
  - 其它 RL 变种：`loh_actor_critic_sb3_mr_PPO.py`、`loh_actor_critic_sb3_mr_SAC.py`、`loh_actor_critic_sb3_pen_*_SAC.py`、`loh_actor_critic_sb3_pen_d_TD3.py` 等，用于 miss-ratio-only、不同 penalty 缩放、不同算法（PPO/SAC/TD3）的实验。
  - 公共职责：
    - 通过 ctypes 描述与 C 端一致的 `SharedMemoryData`；
    - 管理信号量/轮询握手；
    - 实现 `LohEnv` Gym 环境，对接 SB3 算法；
    - 负责 miss-ratio / penalty / trend 组合奖励设计；
    - 将 TB 日志写入 `runs/<timestamp>/tensorboard/...` 目录。

- **测试与运行脚本**
  - `test_loh_rl_sb3.sh`：统一的端到端驱动脚本，负责：
    - 选择 Python 脚本（默认 `loh_actor_critic_sb3.py`，可切到 `*_mr_PPO`、`*_mr_SAC` 等）；
    - 选择 C 端 eviction 算法名（`LOH`、`loh-mr-blocked`、`loh-mr-noblocked` 等）；
    - 决定状态维度（`LOH_STATE_DIM` 26/38）并重建 `libCacheSim`；
    - 生成 `RUN_TIMESTAMP`、`LOH_SHM_KEY`，启动 Python 与 `_build_dbg/bin/cachesim`；
    - 将 cachesim 输出汇总到 `result/*.cachesim`，并记录详细日志 `cachesim_sb3_*.log` / `ac_sb3_*.log`。

---

## 2. C 端 LOH 算法及变种

### 2.1 基础版本：`LOH.c`

- **特征与评分**
  - 每个候选对象提取 6 维特征：
    1. Recency：基于逻辑时间戳差值；
    2. Frequency：访问次数；
    3. Size：对象大小（MB）；
    4–6. IRT 历史：最近三次访问间隔；
  - `FEATURE_LOG` 运行期开关控制是否对这些特征使用 `log1p` 压缩：
    - `g_loh_feature_log=0`（默认）：
      - recency: \(1/(1+\Delta t)\)；
      - frequency: \(f/(f+1)\)；
      - size: \(1/(1+A\cdot MB)\)；
      - IRT: \(1/(1+IRT)\)。
    - `FEATURE_LOG=1`：对 \(\Delta t,f,A\cdot MB,IRT\) 先 `log1p` 再做归一化，缓解长尾分布。

- **状态向量与统计（参考 `09241141-LOH_Algorithm_Architecture.md`）**
  - 基础 38 维结构：
    - [0–1]：对象命中率、字节命中率（epoch 级统计）；
    - [2–25]：命中/未命中 6 维特征的均值/方差（窗口统计）；
    - [26–37]：当前缓存内容上 6 维特征的均值/方差（长期统计，不重置）。
  - `LOH_INCLUDE_CACHE_FEATURES=0` 时只保留前 26 维（无缓存内容段）。
  - `LOH_INCLUDE_CANDIDATE_FEATURES=1` 时再追加 72 维候选汇总特征，打印在状态行末尾。

- **Ghost cache 与 penalty 队列**
  - Ghost cache 记录被驱逐对象的 `access_count`、`last_access_counter`、IRT 历史及驱逐版本号等，用于：
    - 新请求 miss 时恢复历史特征；
    - 发生“历史驱逐导致 miss”时生成延迟惩罚。
  - penalty 队列按版本号记录 `eviction_to_access` 距离和对象大小，C 端在 RL 周期结束时批量写入共享内存，Python 端用于事后奖励修正（SAC/TD3 变体中通过自定义 ReplayBuffer 实现）。

- **在线 RL 同步**
  - 在 `LOH_get()` 中按 `rl_update_interval` 周期：
    1. 调用 `update_state_vector()` 刷新 26/38(+72) 维 state；
    2. 写入 `shm_data_t` 并置 `ready_for_inference=1`，可选 `sem_post` 通知；
    3. 等待 Python 写回 `weights` 并 ack（是否阻塞取决于具体变种）；
    4. 将新权重应用到内存中的 `params->weights`，用于后续驱逐评分。

### 2.2 Miss-ratio 变种：`LOH_mr_blocked.c` 与 `LOH_mr_noblocked.c`

这两个文件在数据结构和特征计算上与 `LOH.c` 基本一致，但在 RL 集成与运行模式上有所区别，主要用于“只看 miss ratio” 或更强的 RL 干预实验。

- **共同点**
  - 同样支持 `FEATURE_LOG`，特征变换逻辑与 `LOH.c` 对齐；
  - 共享 `FREQ_MAX`、`SIZE_BUCKET_COUNT`、IRT 堆、ghost cache、penalty 队列等基础设施；
  - 状态维度仍由 `LOH_INCLUDE_CACHE_FEATURES` / `LOH_INCLUDE_CANDIDATE_FEATURES` 控制。

- **`LOH_mr_blocked.c`（“阻塞训练版”）**
  - 文件头注释：
    - “不管是否训练，继续等待权重 // 使用PPO”。
  - 特点：
    - C 端在每次 RL 同步时会 **阻塞等待** Python 侧权重更新，即使 Python 在训练阶段；
    - 适合配合 `*_mr_PPO` 等 on-policy 算法，保证每一步驱逐都使用“最新策略”；
    - 代价是 cachesim 吞吐下降较明显，更偏“研究/可视化”场景。

- **`LOH_mr_noblocked.c`（“非阻塞训练版”）**
  - 文件头注释：
    - “训练时C端不阻塞，使用上次权重继续运行”。
  - 特点：
    - 在 Python 训练阶段，C 端不会等待新权重，而是使用最近一次成功同步的权重继续评估；
    - 减少了 RL 训练对 cachesim 吞吐的影响，更接近实际在线部署场景；
    - 但会引入策略延迟：训练过程中看到的轨迹与当前正在执行的策略有一定滞后。

- **命令行算法名映射**
  - 在 `test_loh_rl_sb3.sh` 中，可以通过第 6 个参数或 `EVICTION_ALGO` 选择算法：
    - `EVICTION_ALGO=LOH`：绑定 `LOH.c` 基础版本；
    - `EVICTION_ALGO=loh-mr-blocked`：绑定 `LOH_mr_blocked.c`；
    - `EVICTION_ALGO=loh-mr-noblocked`：绑定 `LOH_mr_noblocked.c`；
  - `result/wiki_2019t.oracleGeneral.zst.cachesim` 中的 `LOH-OMR` / `LOH-BMR` 标签，对应不同 reward/算法组合（例如 miss-ratio-only + blocked/non-blocked 训练），具体映射由当时运行脚本决定，日志尾注中通常会标记 `mr-PPO`、`mr-SAC`、`pen-d-TD3` 等说明。

### 2.3 其它相关 C 实现

- `actor_critic_functions.c`
  - 提供 RL 权重更新、评分函数等与多种 eviction 算法共用的辅助函数；
  - LOH 与其它 RL 化算法可在此共享一些逻辑（例如 softmax 权重归一化）。

- 历史/备份文件
  - `LOH.c.bak`、`LOH.c.with_manual_sync` 等主要是旧版本或带手动同步逻辑的备份，当前主线以 `LOH.c` + penalty 队列 + 统一 FEATURE_LOG 为准。

---

## 3. Python 端 RL 脚本及变种

### 3.1 主脚本：`scripts/loh_actor_critic_sb3.py`

- **环境与共享内存**
  - 通过 `create_shared_memory_class(CONTEXT_DIM)` 定义 `SharedMemoryData`，字段顺序与 C 端 `shm_data_t` 对齐（ready/weights/state/weights/miss/byte_miss/reward/state_version/ack_version/timestamp 等）。
  - `LOH_STATE_DIM` / `LOH_INCLUDE_CACHE_FEATURES` / `LOH_INCLUDE_CANDIDATE_FEATURES` 决定 `CONTEXT_DIM`，并在启动时可打印 sizeof/offset 以校验布局。
  - 通过 libc 绑定使用 `sem_open/sem_wait/sem_post` 与 C 端握手，支持超时后回退轮询；受 `LOH_ENABLE_SEMAPHORE` / `LOH_DISABLE_SEMAPHORE` 控制。

- **`LohEnv` Gym 环境**
  - `observation_space`: `Box(shape=(STATE_DIM,))`；
  - `action_space`: `Box(shape=(6,))`，通过 softmax 映射为 6 维权重；
  - `step()` 逻辑大致为：
    1. 等待 C 端设置 `ready_for_inference=1`（优先 sem_wait，超时则轮询）；
    2. 从共享内存读入 state + miss 统计 + penalty 聚合；
    3. 将上一步 RL 动作映射成权重写回，置 `weights_updated=1` 并（可选）`sem_post` ack；
    4. 根据 miss ratio、penalty 等组合成本步 reward，并返回给 SB3 算法；
    5. 管理 episode/warmup、TB logging 等。

- **SAC + RetrospectiveReplayBuffer**
  - 在主脚本中实现了带版本映射与事后奖励修正的 `RetrospectiveReplayBuffer`：
    - 存储时记录 `state_version -> buffer_position`；
    - C 端通过 penalty 队列把某个版本的 `eviction_to_access` / obj_size 传回；
    - Python 端调用 `retrospective_correct_reward(version, distance, size)`，按设计的 penalty 缩放修正历史奖励；
  - 奖励设计通过环境变量控制：
    - `LOH_REWARD_USE_PENALTY / MISS_RATIO / TREND` 决定是否启用 penalty / miss-ratio / trend 组件；
    - `LOH_REWARD_W_*` 控制各组件权重；
    - miss 组件可配置为 `neg` 或 `improve` 模式；
    - trend 组件通过窗口差分/斜率衡量近期 miss ratio 趋势。

- **profiling 与日志**
  - `GLOBAL_TIMER` 记录 env.step / shm 读写 / SAC.train 等各阶段耗时，并在退出时打印分解报告；
  - 结合 TB（在 `runs/<ts>/tensorboard` 下）记录 rollout/ep_rew_mean、loss 等指标，便于排查“时间花在何处”和训练稳定性。

### 3.2 mr-only / PPO 变种：`loh_actor_critic_sb3_mr_PPO.py`

- 复用与主脚本相同的共享内存与环境逻辑，只是：
  - 算法改为 PPO（on-policy）；
  - 专注于 miss ratio 作为奖励主来源（`mr_PPO`）；
  - 训练/推理切换通过 callback 管理，确保 C 端在 on-policy 场景下使用最新策略。
- `loh_actor_critic_sb3_mr_SAC.py` 则是一个轻量 wrapper：
  - 重用 `mr_PPO` 中 `LohEnv` 和训练逻辑；
  - 替换算法为 SAC，接收一组 SAC_* 环境变量覆盖 SB3 超参；
  - 在日志中标记 `[MR-SAC]` 并写入 run 目录，结果在 `wiki_2019t` 试验中以 `mr-SAC` 注释出现。

### 3.3 penalty 缩放变种：`pen_d`、`pen_log`、`pen_survival`

这些脚本都基于主脚本实现的 `RetrospectiveReplayBuffer`，通过“运行时替换”方式注入不同的 penalty 缩放策略：

- **`loh_actor_critic_sb3_pen_d_SAC.py` / `loh_actor_critic_sb3_pen_d_TD3.py`**
  - `pen_d`（倒数）版本：使用 \(p(d) = 1/\max(d,1)\) 或类似的 1/d 缩放方式，将 `eviction_to_access` 转成 penalty；
  - 脚本本身只做入口转发，主要逻辑在基准 SAC/TD3 实现中。

- **`loh_actor_critic_sb3_pen_log_SAC.py`**
  - 定义 `LogReplayBuffer` 继承 `RetrospectiveReplayBuffer`，重定义 `_penalty_scale(distance)`：
    - 使用压缩形式 \(1 - \log(1+d)/\log(1+d_{max})\)，并裁剪到 [0,1]；
    - `dmax` 由环境变量 `LOH_PENALTY_DMAX` 控制，默认 400000；
  - 在 `__main__` 中将 `base.RetrospectiveReplayBuffer` 替换为 `LogReplayBuffer` 后调用基准 `main()`。

- **`loh_actor_critic_sb3_pen_survival_SAC.py`**
  - 定义 `SurvivalReplayBuffer`：
    - 建立对 `distance` 的直方图，估计经验 CDF \(F(d)\)；
    - 使用生存函数 \(S(d)=1-F(d)\) 作为 penalty 缩放（头部距离惩罚大，尾部惩罚趋于 0）；
    - 在高分位数（如 0.99）之后直接置 0 惩罚，避免长尾 miss 过度影响训练；
  - 搭配 `SurvivalTrainingCallback` 将直方图、分位点写入独立 TB 目录 `survival/`，可视化距离分布与阈值。

### 3.4 其它脚本

- `loh_inference_only.py`：
  - 只加载训练好的 PPO 模型进行 **纯推理**，不再训练；
  - 适合线上部署场景，用于给 C 端长期提供权重预测服务；
  - 配置通过 `--shm-key`、`LOH_*` 环境变量控制，日志与 TB 记录推理频率和响应时间。

- 早期/简化版本：`loh_actor_critic.py`、`loh_actor_critic_fixed.py`、`simple_actor_critic.py`、`ultra_simple_agent.py` 等主要用于早期实验和 IPC 原型验证，当前主线以 `loh_actor_critic_sb3*.py` 系列为主。

---

## 4. wiki_2019t 实验结果与现象

### 4.1 结果文件结构

文件 `result/wiki_2019t.oracleGeneral.zst.cachesim` 按“trace + 缓存大小 + 算法”记录多个实验的最终 miss ratio：

- 前半部分是传统基线算法：LRU、LHD、GDSF、ARC、Sieve、S3FIFO、WTinyLFU、LeCaR、Cacheus、LRB-BMR、ThreeLCache-BMR 等，在 3GiB / 39GiB / 6GiB 等不同配置下的 miss/byte miss 比例。
- 后面大量行是 `LOH-OMR`/`LOH-BMR` 在不同缓存大小、请求数和 RL 配置下的结果，行尾注释记录了时间戳与对应 RL 算法，例如：
  - `--1030_183716 pen-d?-SAC 5e-5 512 4 1 1000`
  - `--1031_015607 mr-PPO`
  - `--1106_093058 mr-SAC`
  - `--pen-d-TD3` 等；
- 在 3GiB、300 万请求的小规模实验段，存在大量以 `pen_d_SAC`、`pen_d_TD3`、`pen_log_SAC`、`mr-PPO` 等注释的行，对应不同 penalty/奖励/算法变体。

### 4.2 典型数值与对比

- **大缓存（40GiB，完整 trace）**
  - 传统算法：
    - GDSF: miss ≈ 0.1805（39GiB）
    - ThreeLCache-BMR: miss ≈ 0.1829（39GiB）
  - LOH 相关：
    - `LOH cache size 40GiB, ... miss ratio 0.1898`；
    - `LOH-OMR cache size 40GiB, ... miss ratio 0.1928 (SAC-mr)`；
    - penalty + TD3/SAC 的一些变体在 40GiB 下 miss 约 0.1925–0.2211 左右；
  - 总体来看，大缓存下 LOH-OMR 接近（但尚未明显超越）最强基线的 miss ratio，reward-slide 变体略有提升空间（例如 `LOH-OMR(reward-slide) ... miss 0.1929`）。

- **中等缓存（6GiB，1e7 请求）**
  - LRU miss ≈ 0.52；
  - ThreeLCache-BMR miss ≈ 0.464；
  - 多个 `LOH-OMR` 变体 miss ≈ 0.479–0.486 附近：
    - `pen-d?-SAC`、`mr-PPO`、`mr-SAC`、`pen-d-TD3` 等均处于 0.478–0.486 区间；
  - 说明在该配置下，不同 RL 算法和 penalty 设计在最终 miss ratio 上差异不大，大多落在一个较窄的区间内。

- **小规模 3GiB + 300 万请求段（重点）**
  - 多个 RL 组合（mr-SAC、mr-TD3、mr-PPO、pen_d_SAC、pen_log_SAC 等）在同一段 trace + 缓存配置下的结果高度集中：
    - miss ratio 基本落在 0.605–0.607 之间，byte miss ratio ≈ 0.485–0.486；
    - 即使调节 `ENT_COEF`、`GRADIENT_STEPS`、`LOH_OBS_KEEP`、reward 组件（miss/趋势/deltas）等，最终 miss ratio 仍在 0.606±0.002 的微小波动范围内；
  - 文件末尾的注释中也记录了部分极端对照实验：
    - `mr_SAC 故意设置reward固定0.5`；
    - `mr_SAC 故意设置reward固定0.5 故意设置obs0.5`；
    - 固定权重 1/6 无 RL 等，以确认 “关闭 RL 信号” 时的表现。

### 4.3 实验问题总结

结合 `LOH_EXP_HISTORY.md`、TB 曲线和该结果文件，可以归纳出当前实验中的几个核心问题：

1. **miss ratio ≈ 0.607 平台现象**
   - 在 3GiB + 300 万请求的场景中：
     - 无论使用 `mr-PPO`、`mr-SAC`、`pen_d_SAC`、`pen_log_SAC`、`pen_survival_SAC` 还是 TD3 变体；
     - 无论 reward 只用 miss，还是叠加 trend/deltas，多数 run 的最终 miss ratio 都在 0.606–0.607 之间轻微波动；
   - 即便将 observation/reward 固定为常数或使用“固定 1/6 权重无 RL”的对照，miss ratio 也变化不大，说明：
     - 当前 LOH 基础启发式（recency/freq/size/IRT + ghost）本身已经决定了主要行为；
     - RL 信号在这一区域可能难以进一步降低 miss ratio，或者 reward/特征设计未能提供足够梯度信息。

2. **不同 RL 算法之间差异有限**
   - 在相同 trace + 缓存配置下，PPO/SAC/TD3 的最终 miss ratio 差距往往只有第 3 位小数级别；
   - TB 中 rollout/ep_rew_mean 曲线也多呈现“在一个极窄带内上下抖动”的状态，而不是明显单调提升；
   - 这与 penalty/reward 重新设计前后的一些 run 对比一致：即使 penalty 缩放方式从 1/d 到 log 压缩/生存函数，最终 miss ratio 提升有限。

3. **奖励量纲与 miss ratio 对齐难度**
   - 旧版 penalty 直接从 reward 中“减去”一个基于距离的量，量纲与 miss ratio 不一致；
   - 虽然在 `10230213-PENALTY_MECHANISM_REDESIGN.md` 中已改为基于“单次 miss 对 miss ratio 的增量”的方式，并在 SAC 中通过事后修正奖励实现，但：
     - 惩罚值、窗口大小、rl_update_interval 等参数组合仍然复杂；
     - 不同 penalty 缩放（1/d、log、生存函数）之间的直观含义虽然更清晰，但在 miss ratio 上的增益仍然有限。

4. **训练稳定性与样本效率**
   - 从 TB 和 `RL_CacheSim_Run_Summary_by_Trace.md` 中可以看到：
     - SAC/TD3 在合理的 buffer_size、learning_starts、train_freq、gradient_steps 设置下收敛较快，但 reward 曲线往往在 0 附近小幅波动；
     - 一些 run 在更激进的超参（例如更小的 learning_starts 或更大的 train_freq）下会出现 reward 震荡，但对应 miss ratio 改善不明显；
   - 说明当前 reward 形态与 cache 行为之间的耦合仍不够强，训练“学到的东西”在最终 miss ratio 上的体现较弱。

---

## 5. 开放问题与后续方向

结合当前 C/Python 变种与 wiki_2019t 实验现象，可以明确以下几个开放问题：

1. **LOH 启发式 vs RL 提升空间**
   - 现有 LOH 基础逻辑（多维特征 + ghost cache）在 3GiB + 300 万请求上表现已经相对稳定，RL 在 miss ratio 上的空间有限；
   - 需要通过更多 trace 和更极端配置（小 cache、大 cache、不同工作负载）确认 RL 是否在某些场景下具有明显优势。

2. **reward 设计与信号质量**
   - 目前 reward 主要基于窗口 miss ratio 及其趋势，再叠加 penalty；
   - 可以尝试：
     - 直接用“相对于强基线（如 ThreeLCache-BMR）的超额命中”作为 reward；
     - 引入更局部的指标（如候选得分排序与真实 hit/miss 的一致性）作为辅助监督信号；
     - 考虑对重排/替换对的 pairwise 比较损失，而不仅仅是全局 miss ratio。

3. **特征与观测空间**
   - FEATURE_LOG 已经统一到 C 端多个变种中，但目前缺乏系统性的 ablation 结果：
     - FEATURE_LOG=0 与 1 在不同 trace、不同 cache 配置下的收益如何；
     - 候选特征 72 维（开启 `LOH_INCLUDE_CANDIDATE_FEATURES`）是否实际帮助 RL 探索更优策略；
   - 后续可以设计 FEATURE_LOG × CANDIDATE_FEATURES × 算法（三维矩阵）的实验，并用 TB/脚本自动汇总。

4. **同步模式对策略的影响**
   - `LOH` vs `loh-mr-blocked` vs `loh-mr-noblocked`：
     - 阻塞/非阻塞训练对策略稳定性和性能的差别尚未系统量化；
     - 特别是在高并发/多线程场景下，阻塞训练可能放大 RL 带来的性能抖动；
   - 建议后续在相同 RL 配置下对比这三种 C 端变体的 TB 与 miss ratio 曲线。

---

## 6. 本文定位与后续维护建议

- 本文作为“LOH 算法 + RL 实验”的总览：
  - 第 2、3 节概括了 C 端与 Python 端各主要变种及其职责；
  - 第 4 节基于 `wiki_2019t.oracleGeneral.zst.cachesim` 和 TB/日志总结了关键实验现象；
  - 第 5 节列出了当前尚未解决的问题与可行的下一步方向。
- 后续建议：
  - 每完成一批新的对照实验（例如 FEATURE_LOG ablation、不同 reward 组合、不同算法/超参矩阵），在本文件追加一小节简要记录结论；
  - 若 C/Python 结构体或 IPC 协议有变动，务必同步更新 `LOH_ENV_VARS.md` 与本文第 1、2 节相关描述。
