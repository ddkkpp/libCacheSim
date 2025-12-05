# LOH + RL 实验测试与功能增强历史总结（截至 2025-11-17）

本文件按时间顺序，回顾 LOH 逐出算法与 RL（stable-baselines3）集成过程中的 **实验测试** 与 **功能增强** 两条主线。

- 第一部分：侧重“跑实验”过程中遇到的问题、设计的 ablation、观察到的结果和阶段性结论。
- 第二部分：侧重“为支撑这些实验”所做的工程与功能改动，包括 C 端、Python 端、脚本与文档。

> 说明：
> - 以下阶段编号是“逻辑时间线”，基于当前对话中能追溯到的历史。从“candidate 输出与严格编译”这一阶段开始，记录后续所有相关问题与改动。
> - 若之后有新的实验与改动，可在本文件末尾继续追加新的阶段。

---

## 一、实验测试时间线

### 阶段一：candidate 特征输出与构建稳定性相关实验

- **问题现象**
  - 需要在实验中观察和对比 candidate 特征，但 C 端打印格式混乱，不利于后续画图、对比和脚本解析。
    - 具体需求：candidate 应该最后打印，并且每行 12 个值，分别对应 `[candidate_features_1]` 到 `[candidate_features_6]`。
  - 使用严格编译选项（`-Werror` / `-Wshadow` 等）时，出现编译失败，使得批量实验的构建过程不稳定。

- **尝试 / 改动**
  - 调整 C 端 candidate 特征的打印逻辑：
    - 保证 candidate 部分总是位于整行状态向量输出的最后；
    - 每行打印 12 个 candidate 值，并按照 6 组特征进行分组，方便人工和脚本解析。
  - 修复编译告警：
    - 处理变量遮蔽、未使用变量等问题，使得在 `-Werror` / `-Wshadow` 等标志下也能稳定通过编译。

- **实验或分析结果**
  - `cachesim` 在严格编译选项下可以稳定构建，消除“编译不过”这一类阻塞实验的问题。
  - candidate 特征输出结构化、可预期：
    - 分组与顺序稳定，便于后续用 Python/脚本从日志中抽取 candidate 特征做可视化或进一步统计。

- **阶段性结论**
  - 输出格式与编译稳定性不再是实验主矛盾，可以把注意力转向 RL 策略、特征设计与 IPC 细节上。

---

### 阶段二：RL 环境配置与日志可视化支撑实验

- **问题现象**
  - 需要系统性地进行 RL 实验（PPO/SAC/TD3），但多处配置（环境变量、默认值、脚本参数）分散在 C/Python/shell 中：
    - 不容易复现某一次实验的精确配置；
    - 调参和 ablation 很费力。
  - SAC 已有 TensorBoard 日志，而 `mr_PPO` 变体缺少统一的 TB logging，导致多算法对比训练曲线不直观。

- **尝试 / 改动**
  - 梳理并文档化环境变量：
    - 在 `docs/LOH_ENV_VARS.md` 中总结 LOH 相关环境变量，包括：IPC/共享内存、信号量开关、状态维度、奖励配置、脚本参数等，并标注默认值。
  - 为 SAC / TD3 增加超参数 env 覆盖能力：
    - 在相应 Python 脚本中，从环境变量读取 buffer_size、batch_size、learning_rate、train_freq、gamma 等关键超参；
    - 未设置时使用脚本内的默认值（与 SB3 官方默认值兼容或略作调整以适应缓存场景）。
  - 给 `mr_PPO` 增加 TensorBoard logging：
    - 仿照 SAC 的做法，为 PPO 训练过程接入 TB；
    - 统一指标命名（例如 `rollout/ep_rew_mean` 等），以便在同一 TB Panel 中直接对比不同算法。

- **实验或分析结果**
  - RL 训练过程有统一的 TB 可视化：
    - SAC、TD3、PPO 的 reward、loss、策略熵等指标可以同时展示，便于分析收敛速度与稳定性；
    - 结合 C 端 miss ratio 统计，可以对“RL 是否真正提高缓存性能”进行多维对比。
  - 环境变量文档化后，配置透明度显著提升：
    - 可用一组 env 描述某次实验（包括 RL 超参和 LOH 特定参数），方便之后复现或比较不同 run。

- **阶段性结论**
  - 已具备较完整的“实验配置 → 日志 → TB 可视化”链路，为后续深入的 ablation 和多算法对比提供基础设施。

---

### 阶段三：miss ratio ≈ 0.607 不变现象及相关实验

- **问题现象**
  - 在某些实验配置（包括将 observation/reward 固定为常数等 ablation）下，观测到 miss ratio 长时间维持在约 **0.607** 左右，且对配置改动不敏感：
    - 调整部分 RL 设置后，miss ratio 曲线变化很小，似乎被某种“基础逻辑”或默认策略主导；
    - 引发怀疑：RL 信号是否过于稀疏、reward 设计是否难以引导策略进一步优化，或 cache 基本逻辑已经高度主导整体行为。

- **尝试 / 改动**
  - 设计对照实验：
    - 通过固定 observation / reward，测试「关掉 RL 信号」或简化 RL 反馈时，miss ratio 是否仍维持在类似水平；
    - 对比 RL 开启和“几乎无 RL”两种情况下的 miss ratio 曲线。
  - 使用 TB 日志和 Python 脚本对比多次 run：
    - 提取不同实验的 miss ratio、reward 轨迹；
    - 对比在相同 trace 和缓存配置下，改变 RL 超参或特征变换后的差异。

- **实验或分析结果**
  - 多个实验表明：
    - 在某些配置下，miss ratio 曲线确实表现出「接近常数」的行为（约 0.607），对部分改动并不敏感；
    - 但对话中尚未给出这一现象的最终归因（仍属于开放问题）。

- **阶段性结论 / 下一步计划**
  - 将“miss ratio ≈ 0.607 不变”列为后续重点研究对象：
    - 后续通过 FEATURE_LOG、奖励权重、不同 RL 算法（SAC/TD3/PPO）以及是否启用某些观测/奖励组件等一系列变量，构造系统性的 ablation；
    - 结合更强的日志和分析工具，尝试定位是“特征不足”“reward 设计问题”还是“基础策略已经接近最优”等原因。

---

### 阶段四：日志分析脚本 `analyze_cache.py` 的稳定性实验

- **问题现象**
  - 在对大量实验日志进行离线分析时，`analyze_cache.py` 抛出 `UnboundLocalError`：
    - 原因是当某些 run 缺失 weights 相关字段或 CSV 列时，脚本中对应的路径变量未被赋值就被使用；
    - 导致整个批量分析流程因为单个异常 run 而中断，影响整体实验数据的汇总和可视化。

- **尝试 / 改动**
  - 对 `analyze_cache.py` 做防御式修复：
    - 在 `save_to_csv` 等函数中，对 `weights_path`、`global_path`、`request_path` 等变量进行初始化（例如设为 `None`）；
    - 在写入前检查对应数据是否存在，避免引用未赋值变量。

- **实验或分析结果**
  - 修复后：
    - 即使某些 run 缺失 weights 信息，脚本也不会崩溃，只是相应 CSV 列为空或缺失；
    - 可以顺利完成对所有 run 的 miss ratio、权重轨迹等指标的汇总和导出。

- **阶段性结论**
  - 分析工具链的健壮性大幅提高，为后续 FEATURE_LOG 等 ablation 的大规模运行与统计分析提供保证。

---

### 阶段五：FEATURE_LOG 对数特征 ablation 实验准备与验证

- **问题现象**
  - 希望比较“线性特征 vs 对数特征”的效果：
    - 特征包括 recency、frequency、size 以及 IRT 等；
    - 直觉上，对数变换（`log1p`）有助于压缩长尾分布，使特征尺度更适合 RL 学习。
  - 初始 FEATURE_LOG 实现存在问题：
    - 使用 constructor / init-once 之类的复杂初始化模式；
    - 在 `LOH.c`、`LOH_mr_blocked.c`、`LOH_mr_noblocked.c` 三个实现中，有的路径接入了 FEATURE_LOG，有的路径仍然使用旧公式（没改完）。

- **尝试 / 改动**
  - 统一设计 FEATURE_LOG 为运行期开关：
    - 使用全局 `g_loh_feature_log`，默认值为 0（不开启 log1p）；
    - 在各算法的 init 函数中读取环境变量 `FEATURE_LOG`，解析 `1/true/yes/on` → 1，`0/false/no/off` → 0；
    - 在 init 结束时打印一次生效值，如：`[LOH] FEATURE_LOG=%d (use log1p in features when 1)`，方便在实验日志中确认配置。
  - 简化实现，去掉 constructor/init-once：
    - 按你的要求，删除“只在进程加载时调用一次”的初始化模式；
    - 只依赖对应算法的 init 函数（如 `LOH_init`、`LOH_mr_blocked_init`、`LOH_mr_noblocked_init`）在运行时读取环境和打印。
  - 在 `LOH.c` 中完善所有特征路径：
    - 在 `calculate_object_features` 和相关 helper 中：
      - recency：
        - FEATURE_LOG=0 时：`1 / (1 + dt)`；
        - FEATURE_LOG=1 时：`1 / (1 + log1p(dt))`；
      - frequency：
        - FEATURE_LOG=0 时：`f / (f + 1)`；
        - FEATURE_LOG=1 时：先 `f = log1p(f)` 再 `f / (f + 1)`；
      - size：
        - FEATURE_LOG=0 时：`1 / (1 + A * MB)`；
        - FEATURE_LOG=1 时：`1 / (1 + log1p(A * MB))`；
      - IRT 特征：在 `calculate_irt_feature` 中对原始 IRT 值做 `log1p`（在开启 FEATURE_LOG 时），再进行归一化。
    - 在 ghost miss 路径以及“新对象 size”路径中，同样引入 FEATURE_LOG 条件逻辑，保持与主路径一致。
  - 在 `LOH_mr_blocked.c` 中：
    - 在 init 中读取 `FEATURE_LOG` 并打印值；
    - 在 `calculate_object_features` 已有基础上，补齐：
      - ghost miss 路径的 recency/frequency/size：使用与 `LOH.c` 相同的 FEATURE_LOG 条件；
      - 新对象 size 的计算：同样根据 FEATURE_LOG 决定是否使用 `log1p`；
      - helper 函数 `calculate_recency/frequency/size`：全部改为在 FEATURE_LOG=1 时使用对数变换后再归一化。
  - 在 `LOH_mr_noblocked.c` 中：
    - 同步 init 中的 `FEATURE_LOG` 读取和打印逻辑；
    - 在 `calculate_object_features`、ghost miss 路径、新对象 size 以及相应 helper 函数中，按与 `LOH.c` / `LOH_mr_blocked.c` 一致的方式接入 FEATURE_LOG。

- **实验或分析结果**
  - 三个 C 文件中，与 recency/frequency/size/IRT 相关的所有已知路径（包括正常访问、ghost miss、helper 计算）都接入了统一的 FEATURE_LOG 条件逻辑。通过 grep 和审查确认没有明显遗漏。
  - 多次 debug 构建（`bash scripts/debug.sh -c`）均成功，说明改动至少在编译层面是正确的。
  - 当设置 `FEATURE_LOG=1` 或不设置/设置为 0 时，日志中会在 init 阶段打印出 FEATURE_LOG 的生效值，便于对比不同实验 run。

- **阶段性结论 / 下一步计划**
  - FEATURE_LOG 现已成为一个可控、实现一致的核心 ablation 开关：
    - 可在不改代码的前提下，通过环境变量快速切换“线性特征 vs 对数特征”；
    - 后续实验可以系统对比 FEATURE_LOG=0 与 1 在不同 trace、不同 RL 算法和奖励配置下的 miss ratio、奖励收敛以及策略差异。
  - 建议的下一步：
    - 正式在文档（如 `LOH_ENV_VARS.md`）中加入 FEATURE_LOG 的说明（默认 0，作用于 6 个特征）；
    - 设计一组基础对照实验矩阵，如：
      - 维度：FEATURE_LOG ∈ {0,1} × 算法 ∈ {PPO,SAC,TD3} × 若干典型 trace；
      - 观察指标：miss ratio 曲线、reward 曲线、策略权重轨迹等。

---

## 二、功能增强时间线

> 本部分从“工程与功能”的视角，按时间顺序总结为支持上述实验所做的改动。

### 阶段一：候选特征输出规范与严格构建支持

- **动机 / 问题**
  - 实验需要长期依赖 candidate 特征进行分析与可视化，因此必须有稳定、易解析的输出格式；
  - 严格编译选项下的告警会中止构建，影响持续改动和批量实验。

- **功能改动**
  - 统一 candidate 打印格式：
    - candidate 特征固定在状态输出的最后；
    - 每行 12 个值，对应 6 组特征 `[candidate_features_1..6]`。
  - 修复 `-Werror` / `-Wshadow` 下的告警，使得 debug/release 构建可以稳定通过。

- **对实验的直接影响**
  - 实验日志对机器和人类都更友好：
    - Python 分析脚本可以方便地分割 candidate 特征，用于绘图和对比；
    - 老日志格式混乱的问题得到解决。
  - 构建失败不再是阻塞因素，可以频繁迭代 C 端实现以支持新的 ablation。

---

### 阶段二：IPC / 共享内存 / 状态维度及信号量逻辑梳理

- **动机 / 问题**
  - C 端 `LOH.c` 与 Python RL 进程通过共享内存和 POSIX 信号量通信，配置项较多（SHM key、sem 开关、状态维度等），容易因“端到端不一致”导致奇怪的实验问题：
    - 例如共享内存结构体大小不一致、信号量行为不符合预期等。

- **功能改动**
  - 梳理 SHM 与 sem 配置逻辑（贯穿 C、Python、shell 脚本）：
    - `LOH_SHM_KEY` 的默认值与脚本生成策略；
    - `/dev/shm/loh_ac_<key>` 与 `/loh_ac_ready_<key>`、`/loh_ac_ack_<key>` 的命名约定；
    - `LOH_ENABLE_SEMAPHORE` / `LOH_DISABLE_SEMAPHORE` 的“禁用优先”解析逻辑，在 C 和 Python 两端保持一致；
    - `LOH_SEM_TIMEOUT_S` 与 `LOH_POLL_SLEEP_US` 的默认值与作用。
  - 梳理状态维度与构建宏：
    - 通过 `LOH_INCLUDE_CACHE_FEATURES`（26 vs 38）、`LOH_INCLUDE_CANDIDATE_FEATURES`（是否 +72）、`LOH_STATE_DIM` 环境变量以及 `scripts/debug.sh` 的逻辑，保证 C 宏与 Python 解析在端到端运行时保持一致；
    - 文档中明确说明“端到端脚本会触发重建，以对齐 C 宏和 Python 侧维度”。

- **对实验的直接影响**
  - 明确了共享内存结构体大小与字段偏移必须在 C/Python 两端一致，并给出了校验建议；
  - 降低了“莫名其妙的 IPC 异常”在实验中的出现频率，使得在跑 RL 实验时更有信心“问题出在算法/特征，而不是底层 IPC bug”。

---

### 阶段三：环境变量与 SB3 超参覆盖文档化

- **动机 / 问题**
  - 实验中使用了大量环境变量来配置 RL、奖励、脚本行为、缓存算法参数，不记录清楚会导致：
    - 难以复现某次实验配置；
    - 难以进行系统性的超参探索与 ablation。

- **功能改动**
  - 创建并维护 `docs/LOH_ENV_VARS.md`：
    - 列出 IPC / 同步相关 env（SHM key、信号量、fsync 等）；
    - 列出状态维度、构建宏相关 env；
    - 列出奖励/惩罚相关 env（penalty、miss_ratio、trend 组件、权重、窗口等）；
    - 列出测试脚本相关 env（LEARNING_STARTS、EXCLUDE_RECENT_STEPS、PYTHON_SCRIPT、EVICTION_ALGO 等）；
    - 列出 SAC/TD3/PPO 的超参覆盖 env 及默认值。
  - 在 SB3 对应脚本中实现从 env 读取超参并覆盖默认配置的逻辑。

- **对实验的直接影响**
  - 任何一次实验都可以用一组 env 清晰描述，从而容易被记录和复现；
  - 通过 env 的超参覆盖机制，能够在不改代码的前提下进行大规模的 ablation（例如改变 buffer_size、train_freq、reward 组件权重等）。

---

### 阶段四：RL 日志（尤其是 mr_PPO）与分析工具增强

- **动机 / 问题**
  - 需要对比 PPO 与 SAC/TD3 等算法在相同 trace 下的训练行为和性能；
  - 日志分析脚本在数据缺失时容易崩溃，影响整批实验的统计分析。

- **功能改动**
  - 为 `mr_PPO` 加入 TensorBoard logging：
    - 与 SAC 采用类似的回调与指标命名，保证在一个 TB Panel 中直接比较不同算法的训练曲线。
  - 修复并增强 `analyze_cache.py`：
    - 防御性初始化 CSV 路径变量，避免因某些 run 缺失部分数据而抛出 `UnboundLocalError`；
    - 保证脚本能够稳定处理“部分数据缺失”的日志文件。

- **对实验的直接影响**
  - SAC、TD3、PPO 的训练曲线与 miss ratio 可以在 TB 中统一查看，加速定位“哪种算法/配置更优”；
  - 批量实验结束后，可以用一个脚本处理所有 run，即使其中一些日志不完整也不会拖垮整体分析流程。

---

### 阶段五：FEATURE_LOG 开关的统一实现与多文件一致性

- **动机 / 问题**
  - 希望将“特征是否使用 log1p 变换”抽象为统一的实验开关，以便：
    - 快速切换线性特征与对数特征；
    - 在论文或报告中直接引用这一开关进行实验分类；
    - 避免不同文件/路径各自实现一套不一致的逻辑。

- **功能改动**
  - 在 `LOH.c`、`LOH_mr_blocked.c`、`LOH_mr_noblocked.c` 中统一 FEATURE_LOG 的实现：
    - 使用全局 `g_loh_feature_log`，默认 0；
    - 在各自 `*_init` 中读取 `FEATURE_LOG` 环境变量并打印最终生效值；
    - 在所有涉及 recency/frequency/size/IRT 的路径（包含 ghost 路径和 helper 函数）中加入 FEATURE_LOG 条件逻辑，统一采用：
      - 时间 → `1/(1+dt)` vs `1/(1+log1p(dt))`；
      - 频率 → `f/(f+1)` vs 先 `log1p(f)` 再 `f/(f+1)`；
      - 大小 → `1/(1+A*MB)` vs `1/(1+log1p(A*MB))`；
      - IRT → raw IRT vs `log1p(IRT)` 后归一化。

- **对实验的直接影响**
  - FEATURE_LOG 成为一个“一处设置，三处生效”的统一开关：
    - 不再担心某个变种（如 mr_blocked / mr_noblocked）遗漏 log1p 逻辑；
    - 便于开展“有无 log 特征”的对比实验并在日志中一眼确认开关状态。
  - 通过 debug 构建验证改动不会破坏现有构建流程，为后续在此基础上继续改进提供了信心。

---

## 三、未解决问题与后续实验计划（简要）

- **未完全解决的问题**
  - miss ratio ≈ 0.607 在部分配置下“几乎不变”的根本原因尚未完全厘清：
    - 可能与 reward 设计、特征表达能力、基础策略或 trace 特性有关。

- **建议的后续实验方向**
  - FEATURE_LOG ablation：
    - 在多个 trace 与缓存配置下，对比 FEATURE_LOG ∈ {0,1} 的 miss ratio 和 reward 曲线；
    - 观察对数特征是否在某些场景下显著改善学习质量或收敛速度。
  - 算法对比与超参 ablation：
    - 在统一的环境与 IPC 配置下，对比 PPO / SAC / TD3 在不同超参、不同 reward 组件权重下的表现；
    - 借助 TB 和 `analyze_cache.py`，收集系统性的实验矩阵结果。
  - 奖励设计与命中率组件：
    - 调整 `LOH_REWARD_USE_PENALTY / MISS_RATIO / TREND` 及其权重，探索更能直接驱动 miss ratio 优化的 reward 形态；
    - 尝试引入更细粒度的命中率或延迟指标，改善 RL 信号质量。

---

> 若后续有新的实验阶段或功能改动，请在本文件中继续追加相应阶段，以保持 LOH+RL 演进历史的完整性。
