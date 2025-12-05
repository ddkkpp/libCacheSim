# LOH 环境变量与默认值速查（2025-01 更新）

本文件汇总 LOH 相关的环境变量、默认值及生效优先级，覆盖 C 端、Python RL（stable-baselines3）以及测试脚本（shell harness）。用于快速定位配置来源、避免两端不一致导致的 IPC 问题。

> 快速原则：
> - **状态维度**：前2维 (hit_ratio, byte_hit_ratio) 始终传递（因为奖励计算需要），其他维度通过构建宏控制。
> - **RL 观测**：Python 端通过 `RL_STATE_USE_MISSRATIO` 控制 RL 是否使用前2维（默认使用）。
> - 信号量启用/禁用以"禁用优先"解析（LOH_DISABLE_SEMAPHORE 优先于 LOH_ENABLE_SEMAPHORE）。
> - 共享内存 key 未指定时，测试脚本会按"时间戳+PID"生成；C/Python若都未设置则回退到默认 9876。
> - **新增统一 RL 脚本**：`loh_actor_critic_sb3.py` 现已整合 PPO/SAC/TD3 算法，通过 `LOH_RL_ALGO` 切换。

---

## 一、IPC 与同步

- LOH_SHM_KEY
  - 作用：共享内存文件与 POSIX 命名信号量的键值。
  - 默认：
    - Python：未设置时默认 9876。
    - C：若未设置，使用编译期宏 `SHM_KEY=9876`。
    - 测试脚本：若未设置，会生成 `HHMMSS*1000 + (PID%1000)`，并导出为本次运行的键。
  - 命名：`/dev/shm/loh_ac_<key>`、`/loh_ac_ready_<key>`、`/loh_ac_ack_<key>`

- LOH_ENABLE_SEMAPHORE / LOH_DISABLE_SEMAPHORE
  - 作用：启用/禁用 POSIX 信号量握手。
  - 默认：启用。
  - 优先级：若设置了 LOH_DISABLE_SEMAPHORE，则禁用；否则若设置 LOH_ENABLE_SEMAPHORE 则按其值启/停；否则启用。
  - 生效端：C 与 Python 两端都按该逻辑解析。

- LOH_WAIT_MODE
  - 作用：C 端在与 Python 同步 RL 权重时的等待模式。
  - 可选：
    - `blocked`：阻塞等待 Python 写回权重后再继续（默认）。
    - `nonblocked` / `non-blocked`：非阻塞模式，在训练阶段若暂时拿不到新权重则继续使用缓存中的旧权重。
  - 默认：未设置或取值非法时，视为 `blocked`。

- LOH_SEM_TIMEOUT_S
  - 作用：Python 端 `sem_wait/sem_timedwait` 超时时间（秒）。
  - 默认：1.0

- LOH_POLL_SLEEP_US
  - 作用：Python 端轮询退化路径的睡眠间隔（微秒）。
  - 默认：200（0.2ms）

- LOH_DISABLE_FSYNC
  - 作用：Python 写共享内存后是否调用 `fsync`，以降低系统调用开销（有风险）。
  - 默认：false（调用 fsync）

- LOH_PRINT_SHM_LAYOUT
  - 作用：Python 启动时打印 ctypes 结构体 sizeof 与字段偏移，便于与 C 比对。
  - 默认：true（非 0/false/False 即打印）

---

## 二、状态维度与构建宏（C/Python 对齐）

**状态向量结构**（从 C 端共享内存传递）：
```
CONTEXT_DIM = MISSRATIO_DIM(2)
            + HIT_MISS_DIM(0/24)
            + CACHE_DIM(0/12)
            + CAND_DIM(0/72)
            + TOPK_DIM(0/192)
            + AVGTOPK_DIM(0/24)
            + REQUEST_DIM(0/REQUEST_HISTORY_LEN*6)
```

- **MISSRATIO_DIM = 2**（始终传递）
  - 前2维 (hit_ratio, byte_hit_ratio) 始终从 C 端传递，因为奖励计算需要这两项。
  - Python 端通过 `RL_STATE_USE_MISSRATIO` 控制 RL 观测是否包含这两维。

- **RL_STATE_USE_MISSRATIO**（Python 端，运行期环境变量）
  - 作用：控制 RL 观测是否包含前2维 (hit_ratio, byte_hit_ratio)。
  - 默认：1（包含）
  - 设为 0：RL 观测从索引 2 开始，不包含前2维（但共享内存仍传递）。
  - 使用场景：当你希望 RL 模型不直接"看到"当前 miss ratio，而只依赖其他特征做决策时。

- LOH_INCLUDE_HIT_MISS_FEATURES（编译期宏 + 运行期环境）
  - 作用：控制是否包含 Hit/Miss 特征统计（24 维）。
  - 默认：0（不包含）；设为 1/true/yes/on 则包含。

- LOH_INCLUDE_CACHE_FEATURES（编译期宏 + 运行期环境）
  - 作用：控制是否包含缓存特征统计（12 维）。
  - 默认：0（不包含）；设为 1/true/yes/on 则包含。

- LOH_INCLUDE_CANDIDATE_FEATURES（编译期宏 + 运行期环境）
  - 作用：是否附加候选特征 72 维（6×12）。
  - 默认：0（不附加）；设为 1/true/yes/on 则附加。

- LOH_INCLUDE_TOPK_CANDIDATE_FEATURES（编译期宏 + 运行期环境）
  - 作用：是否附加 TopK 候选对象特征（32×6=192 维）。
  - 默认：1（包含）；设为 0/false/no/off 则不包含。

- LOH_INCLUDE_AVGTOPK_CANDIDATE_FEATURES（编译期宏 + 运行期环境）
  - 作用：是否附加 AvgTopK 候选对象平均特征（4×6=24 维）。
  - 默认：1（包含）；设为 0/false/no/off 则不包含。

- LOH_INCLUDE_REQUEST（编译期宏 + 运行期环境）
  - 作用：是否在状态尾部追加“最近 N 次请求”的 6 维特征序列（按时间展开）。
  - C 端：
    - 编译期宏 `LOH_INCLUDE_REQUEST` 控制是否启用请求历史缓冲；
    - 若为 1，C 端会在 `LOH_get` 中对每个请求计算 6 维特征（recency/freq/size/3×IRT），
      写入环形缓冲 `REQUEST_HISTORY_LEN×6`，并在 `update_state_vector()` 中按
      “最旧→最新”的顺序展平成 `REQUEST_DIM = REQUEST_HISTORY_LEN*6` 追加到 `state[]` 尾部；
    - 当前实现中 `REQUEST_HISTORY_LEN=200`，可在 C 端宏中调整；每个 RL epoch 结束
     （`sync_with_actor_critic` 后）会清空一次缓冲，使不同 epoch 的序列互不污染。
  - Python 端：
    - 运行期环境变量 `LOH_INCLUDE_REQUEST` 控制 `get_state_dim()` 是否将
      `REQUEST_DIM = REQUEST_HISTORY_LEN*6` 计入 `CONTEXT_DIM`，并更新
      `[CONTEXT_DIM_CONFIG]` 日志中的 `REQUEST=` 字段；
    - `LohEnv` 直接从共享内存读取扩展后的 `state[0:CONTEXT_DIM]`，不额外处理
      REQUEST 段；`_print_state_by_category` 会在调试模式下打印部分
      `[STATE_REQUEST_k]` 方便校验。
  - 默认：0（不启用请求历史）；
  - ⚠️ 注意：
    - C 端：需要在编译时通过环境变量 `LOH_INCLUDE_REQUEST=1` 触发 `scripts/debug.sh`
      将其映射为编译宏（`-DLOH_INCLUDE_REQUEST=1`），否则 C 端始终按 0 编译，
      不会分配 `request_history` 也不会在 `update_state_vector()` 中展开该段；
    - Python 端：仅设置环境变量 `LOH_INCLUDE_REQUEST=1` 只会扩展 Python 侧
      `CONTEXT_DIM`，如果 C 端仍按 0 编译，则共享内存结构体大小与 Python 预期不符，
      读取到的 REQUEST 段通常为 0 或未定义数据；
    - 正确用法：**同时**在构建时导出 `LOH_INCLUDE_REQUEST=1` 并运行 `bash scripts/debug.sh -c`
      或由 `test_loh_rl_sb3.sh` 自动触发一次构建，然后在运行时继续导出
      `LOH_INCLUDE_REQUEST=1` 给 Python，使 C/Python 两端对 `CONTEXT_DIM` 完全一致。

  RL_STATE_USE_MISSRATIOTREND
  不传递，而是python自己计算

**状态维度计算示例**：
```
# 仅启用 TOPK（默认，AVGTOPK=1, REQUEST=0）
CONTEXT_DIM = 2 + 0 + 0 + 0 + 192 + 24 + 0 = 218

# 启用 CACHE_FEATURES（保留 TOPK 与 AVGTOPK）
CONTEXT_DIM = 2 + 0 + 12 + 0 + 192 + 24 + 0 = 230

# 启用 REQUEST_HISTORY（N=200）且关闭 TOPK/AVGTOPK
CONTEXT_DIM = 2 + 24 + 12 + 72 + 0 + 0 + 200*6 = 1312
```

说明：端到端运行时，确保 C 编译宏与 Python 环境变量一致；`scripts/debug.sh` 会自动同步。

---

## 三、观察空间与动作缩放（Python）

- **RL_STATE_USE_MISSRATIO**
  - 作用：控制 RL 观测是否包含前2维 (hit_ratio, byte_hit_ratio)。
  - 默认：1（包含所有维度）
  - 设为 0：RL 观测从索引 2 开始，不包含前2维（共享内存仍传递，奖励计算可用）。

- LOH_FIXED_OBS
  - 作用：强制 RL 环境输出固定观测，用于调试 IPC 与奖励逻辑，而不依赖真实缓存特征。
  - 默认：0（正常观测）。
  - 取值：
    - 0：正常观测；
    - 1：观测全 0；
    - 2：观测全 0.5；
    - 3：观测全 1。
  - 生效端：`scripts/loh_actor_critic_sb3.py` 中的 `LohEnv`，在 `reset()/step()` 中根据该模式替换 obs。

- LOH_OBS_ADD_HIT_DELTAS
  - 作用：是否把"命中率 delta"附加到观测。
  - 默认：false

- LOH_HIT_DELTA_MODE
  - 作用：命中率 delta 的统计模式（`mean|tail`）。
  - 默认：`mean`

- LOH_HIT_DELTA_WINDOW
  - 作用：命中率 delta 的窗口长度。
  - 默认：100

- LOH_SOFTMAX_TEMP
  - 作用：动作 softmax 的温度（权重平滑）。
  - 默认：1.0

- LOH_OBS_KEEP
  - 作用：在 TD3 变体 `loh_actor_critic_sb3_pen_d_TD3.py` 中对观测空间做裁剪/子集选择，例如去掉命中率或某些特征段。
  - 默认：空字符串（不过滤，使用完整 state）。
  - 示例：`LOH_OBS_KEEP=nohit` 表示不保留“命中率相关”观测分量，具体子集规则以脚本实现为准。

- LOH_FEATURE_LOG1P / LOH_FEATURE_LOG1P_RECIPROCAL
  - 作用：统一控制 C 端 6 维特征（recency/freq/size/3×IRT）的归一化模式，并与 Python 端权重处理配合。
  - 模式与优先级（主要由 C 端决定，Python 通过 `LOH_FEATURE_LOG1P` 与 `LOH_USE_SOFTMAX` 组合决定动作解释方式）：
    1. `LOH_FEATURE_LOG1P`
       - 若为 1/true：
         - C：recency/freq/size/IRT 全部使用 `log1p(raw)` 作为特征；size 直接以字节为单位（不再除以 MB），包括 ghost cache 特征与新对象 size；
         - C：内部变量 `loh_feature_log1p=1`，同时强制 `loh_feature_log1p_reciprocal=0`；
         - Python：通常与 `LOH_USE_SOFTMAX=0` 搭配使用，将动作视为“有符号连续权重”（不做 softmax，可为负且不要求和为 1）。
       - 优先级最高：一旦开启，`LOH_FEATURE_LOG1P_RECIPROCAL` 不再生效。
    2. `LOH_FEATURE_LOG1P_RECIPROCAL`
       - 在未开启 LOG1P 模式时生效；
       - 若为 1/true：C 端使用 `log1p`+`1/(1+x)` 的 reciprocal 归一化：
         - recency: `1/(1 + log1p(delta_t))`；
         - freq: `f/(f+1)`，其中 `f` 先经过 `log1p(f)`；
         - size: `1/(1 + log1p(A * size_MB))`；
         - IRT: `1/(1 + log1p(irt))`；
         - ghost cache 与新对象的 size/recency/freq 也使用同一套映射；
       - 内部变量：`loh_feature_log1p=0`，`loh_feature_log1p_reciprocal=1`。
  - 默认：
    - 若两个变量均未设置或为 0/false：
      - C：使用旧特征归一化：`1/(1+delta_t)`、`f/(f+1)`、`1/(1+A*size_MB)`、`1/(1+irt)`；ghost cache 与新对象特征保持一致；
      - Python：继续对动作做 softmax 得到 6 维概率权重。

  - LOH_ENABLE_FEATURE_NORMALIZATION
    - 作用：在 C 端对计算出的 6 维特征进行额外的归一化（运行期），计算方式为：
      - 对每个特征 i，使用常数 max_i（recency=6.4e6, frequency=256, size=16e9, irt1/2/3=6.4e6）计算 denom = log1p(max_i)
      - 以 features[i] = features[i] / denom 并将结果 clip 到不超过 1
      - 同时在 `LOH_params_t` 中记录每个特征的裁剪次数与样本数（用于后续分析）
    - 默认：0（禁用）
    - 生效方式：运行时通过环境变量设置（无需重建）

  - LOH_FEATURE_NORM_MAX_RECENCY / LOH_FEATURE_NORM_MAX_FREQ / LOH_FEATURE_NORM_MAX_SIZE / LOH_FEATURE_NORM_MAX_IRT
    - 作用：覆盖 C 端用于 `LOH_ENABLE_FEATURE_NORMALIZATION` 的特征最大值数组 `feature_norm_max[]`，便于根据 trace 量级手动调节归一化尺度。
    - 默认：
      - recency：约 `6.4e6`
      - freq：`256`
      - size：约 `1.6e10`（16GB 等级）
      - irt：`6.4e6`（3 个 IRT 分量共用同一个最大值）
    - 取值：写成浮点字符串，如 `LOH_FEATURE_NORM_MAX_SIZE=1e9`；未设置的维度保持默认。

- LOH_SCORE_USE_IRT / LOH_SCORE_USE_COMPOUND
  - 作用：控制 C 端评分所使用的特征组合，并与 Python 端动作维度对齐。
  - 生效端：
    - C：在 `LOH.c` 的 `LOH_to_evict()` 中选择用于线性打分的特征；
    - Python：在 `loh_actor_critic_sb3.py` 中通过 `SCORE_FEATURE_DIM` 决定 `ACTION_DIM` 以及动作→权重映射方式。
  - 模式：
    1. 默认模式（未设置或 `LOH_SCORE_USE_IRT=1, LOH_SCORE_USE_COMPOUND=0`）
       - C 端评分特征：
         - 6 维基础特征：`[recency, frequency, size, irt1, irt2, irt3]`；
       - Python：
         - `SCORE_FEATURE_DIM = 6`；
         - `ACTION_DIM = 2 * SCORE_FEATURE_DIM`（若 `LOH_DUAL_CHANNEL=1`）或 `SCORE_FEATURE_DIM`（若 `LOH_DUAL_CHANNEL=0`）；
         - 策略输出的 6 维权重依次对应上述 6 个基础特征。
    2. 仅基础三维模式（`LOH_SCORE_USE_IRT=0, LOH_SCORE_USE_COMPOUND=0`）
       - C 端评分特征：
         - 仅使用前 3 维基础特征：`[recency, frequency, size]`；3 个 IRT 分量不参与分数计算；
       - Python：
         - `SCORE_FEATURE_DIM = 3`，动作维度随之变为 3 或 6：
           - `ACTION_DIM = 2 * 3 = 6`（`LOH_DUAL_CHANNEL=1`）；
           - `ACTION_DIM = 3`（`LOH_DUAL_CHANNEL=0`）；
         - 策略输出首先映射为长度为 3 的有效权重 `[w_rec, w_freq, w_size]`，再填充到共享内存中固定的 6 维 `weights[FEATURE_DIM]` 的前 3 个位置，后 3 维保留给 IRT（在该模式下被 C 端忽略）。
    3. compound 模式（`LOH_SCORE_USE_COMPOUND=1`，优先生效）
       - C 端：
         - IRT 不再参与评分（等价于 `LOH_SCORE_USE_IRT=0`），改为使用：
           - `recency, frequency, size, freq_recency, freq_size, recency_size` 共 6 维；
         - compound 特征定义与符号由 `LOH_FEATURE_LOG1P` 决定：
           - 若 `LOH_FEATURE_LOG1P=1`：
             - `freq_recency = freq / recency`（内部做安全除 0 保护）；
             - `freq_size    = freq / size`；
             - `recency_size = recency * size`；
             - 评分符号 `sign = [-1, 1, -1, 1, 1, -1]`；
           - 若 `LOH_FEATURE_LOG1P=0`：
             - `freq_recency = freq * recency`；
             - `freq_size    = freq * size`；
             - `recency_size = recency * size`；
             - 评分符号为全 1，即 `sign = [1, 1, 1, 1, 1, 1]`；
         - 在 compound 模式下，`LOH_USE_HEURISTIC_SIGNS` 对评分符号不再生效（由上述规则完全确定）。
       - Python：
         - `SCORE_FEATURE_DIM = 6`，动作维度与默认模式相同：
           - `ACTION_DIM = 2 * 6 = 12`（`LOH_DUAL_CHANNEL=1`）；
           - `ACTION_DIM = 6`（`LOH_DUAL_CHANNEL=0`）；
         - 策略输出的 6 维有效权重按顺序对应
           `[recency, frequency, size, freq_recency, freq_size, recency_size]`，
           再一一写入共享内存中的 `weights[0..5]`。
  - 默认：
    - `LOH_SCORE_USE_COMPOUND` 未设置或为 0；
    - `LOH_SCORE_USE_IRT` 未设置或为 1；
    - 即默认行为为“含 IRT 的 6 维基础特征”，与旧版本保持兼容。

- LOH_DUAL_CHANNEL
  - 作用：控制动作维度与解释方式。
  - 默认：1（启用）。
  - 语义：
    - 为 1 时：动作维度 `ACTION_DIM = 2 * FEATURE_DIM = 12`，采用正/负双通道：
      - Python 端先对 12 维动作施加温度缩放（`LOH_SOFTMAX_TEMP`），再按需 softmax；
      - 每个特征 i 使用一对通道 `(2*i, 2*i+1)`，权重 `w[i] = pos - neg`，其中 `pos,neg` 来自 softmax 概率或原始 logits；
      - 这样可以在同一策略下自然产生正/负权重，便于结合 sign 约束；
    - 为 0 时：动作维度 `ACTION_DIM = FEATURE_DIM = 6`，每个特征只有单通道，直接映射为权重。

- LOH_USE_SOFTMAX
  - 作用：控制是否对策略输出作为 logits 施加 softmax。
  - 默认：1（开启 softmax）。
  - 语义：
    - `LOH_DUAL_CHANNEL=1` 时：
      - 若为 1：对 12 维动作做 softmax 得到概率分布 p，再按 `w[i] = p[2*i] - p[2*i+1]` 得到有符号权重；
      - 若为 0：跳过 softmax，直接使用温度缩放后的 logits，`w[i] = logits[2*i] - logits[2*i+1]`；
    - `LOH_DUAL_CHANNEL=0` 时：
      - 若为 1：对 6 维动作做 softmax 并直接作为非负权重；
      - 若为 0：动作本身（范围 [-1,1]）直接作为 6 维连续权重。
  - 典型搭配：
    - `LOH_FEATURE_LOG1P=0, LOH_USE_SOFTMAX=1`：将权重视作概率分布，更接近“带权随机驱逐”风格；
    - `LOH_FEATURE_LOG1P=1, LOH_USE_SOFTMAX=0`：将权重视作任意有符号系数，更接近“静态线性打分”。

- LOH_USE_HEURISTIC_SIGNS
  - 作用：控制 C 端是否启用特征符号先验（sign），即各特征与“分数/被驱逐倾向”之间的**固有单调关系**。
  - 默认：1（启用启发式符号）。
  - C 端行为（见 `LOH.c` 中 `calculate_score`）：
    - 若为 1：
      - 评分公式为 `score = Σ f[k] * w[k] * sign[k]`，其中：
        - Recency: `sign[0] = -1.0`（访问时间间隔越长 → 分数越低 → 越容易被驱逐）
        - Frequency: `sign[1] =  1.0`（访问频率越高 → 分数越高 → 越不容易被驱逐）
        - Size: `sign[2] = -1.0`（对象越大 → 分数越低，在同等命中收益下更倾向驱逐大对象）
        - IRT1/2/3: `sign[3..5] = -1.0`（IRT 越大 → 越“冷” → 越倾向被驱逐）
      - 此时 **w[k] 更像“强度/重要性”系数**，而方向（正/负）由 sign 固定，保证上述单调关系始终成立；
    - 若为 0：
      - `sign[k] = 1.0` 对所有特征，方向完全交给 RL 权重 `w[k]` 决定；
  - Python 端行为：
    - PPO 软先验（`LOH_PPO_SOFT_PRIOR`，见下）会读该变量，组合出 `target_signs`，保证最终的 `w[k]*sign[k]` 与 recency/freq/IRT 之间的预期单调关系一致或由 RL 自由学习。

- LOH_PPO_SOFT_PRIOR / LOH_PPO_SOFT_PRIOR_BIAS
  - 作用：仅当 `LOH_RL_ALGO=PPO` 时生效，用于在 PPO 策略的动作输出层上施加一次性的**软先验偏置**，引导初始权重的符号谱系；
  - `LOH_PPO_SOFT_PRIOR`
    - 默认：0（关闭）；
    - 设为 1/true：在创建 PPO 模型后，按照预设的“全谱系先验”调整最后一层 Linear 的 bias：
      - 预期符号（intended_signs）：`[-1, 1, -1, -1, -1, -1]`，对应 Recency(-)、Freq(+)、Size(-)、IRT(-)；
      - 若 `LOH_USE_HEURISTIC_SIGNS=1`（C 端也使用同一符号向量），Python 会将策略输出的目标符号调整为全正，使得 `w[k]` 表示强度，而最终方向由 C 侧 sign 固定；
      - 若 `LOH_USE_HEURISTIC_SIGNS=0`，则 Python 直接按 `[-1,1,-1,...]` 施加偏置，让 PPO 自身学到“freq 正相关、recency/IRT 负相关”的方向。
  - `LOH_PPO_SOFT_PRIOR_BIAS`
    - 作用：控制上述 bias 的强度（对 logits 级别的偏移量）。
    - 默认：0.5；数值越大，初始策略越“贴近”启发式符号，数值越小越接近无先验。

---

## 四、算法选择（Python RL）

- **LOH_RL_ALGO**
  - 作用：选择 RL 算法（`PPO`、`PPO_LSTM`、`SAC`、`TD3`）。
  - 默认：`SAC`
  - 说明：统一脚本 `loh_actor_critic_sb3.py` 根据此变量创建对应模型：
    - `SAC`：`ProfiledSAC("MlpPolicy")` + 事后惩罚回放缓冲区（默认）。
    - `PPO`：`ProfiledPPO("MlpPolicy")`，纯 MLP 策略网络，可选启用 `LOH_PPO_SOFT_PRIOR`。
    - `PPO_LSTM`：使用 `sb3-contrib.RecurrentPPO("MlpLstmPolicy")`（需要额外安装 `sb3-contrib`），在策略前加入 LSTM 序列单元以编码访问历史；其余超参与 `PPO` 分支一致，并可同样使用 `LOH_PPO_SOFT_PRIOR` 对动作头做软先验偏置。

- LOH_RL_SEED
  - 作用：为 Python 端所有随机数源（`random` / `numpy` / `torch`）设定统一种子，以便实验可复现。
  - 默认：未设置时，脚本回退到 `SEED` 或自身默认种子。
  - 优先级：若同时设置 `LOH_RL_SEED` 与 `SEED`，则优先使用 `LOH_RL_SEED`。
  - 生效脚本：`loh_actor_critic_sb3.py`、`loh_actor_critic_sb3_pen_log_SAC.py`、`loh_actor_critic_sb3_pen_d_TD3.py` 等基于 SB3 的 RL 脚本。

## 五、奖励/惩罚（Python ReplayBuffer + 组合策略）

- **LOH_ENABLE_PENALTY**
  - 作用：启用/禁用 penalty 机制（0=禁用，1=启用）。
  - 默认：**0**（禁用）
  - **⚠️ 重要**：此变量同时影响 C 端编译和 Python 端运行。
    - 设置 `LOH_ENABLE_PENALTY=1` 后需要**重新构建**（`bash scripts/debug.sh -c`），否则 C 端不会写入 penalty 数据。
    - `test_loh_rl_sb3.sh` 会自动检测该变量并触发增量构建。
  - 说明：当为 0 时，跳过 penalty 相关初始化与计算；为 1 时启用 retrospective penalty correction。

- LOH_MISS_RATIO_WEIGHT
  - 作用：控制对象 miss ratio 与字节 miss ratio 在 C 端 reward/统计中的权重，shell 脚本会将其转成 `--eviction-params "miss-ratio-weight=<value>"` 传给 cachesim。
  - 默认：1.0（仅使用对象 miss ratio，`byte_miss_ratio_weight` 默认为 0）。
  - 生效路径：`scripts/test_loh_rl_sb3.sh` 读取该环境变量并导出为 `LOH_MISS_RATIO_WEIGHT`，C 端在 `LOH.c` / `LOH_mr_blocked.c` 中解析 `miss-ratio-weight` 参数。

- LOH_PENALTY_SCALE
  - 作用：惩罚缩放模式；支持 `reciprocal`（倒数）、`log`（对数压缩）、`survival`（生存函数）。
  - 默认：`reciprocal`
  - 生效条件：仅在 `LOH_ENABLE_PENALTY=1` 时有效。

- LOH_PENALTY_DMAX
  - 作用：penalty 缩放的最大距离参数（用于 log 和 survival 模式）。
  - 默认：400000
  - 生效条件：仅在 `LOH_ENABLE_PENALTY=1` 时有效。

- LOH_SURVIVAL_QUANTILE
  - 作用：survival 模式的高分位数阈值（钝化 penalty）。
  - 默认：0.99
  - 生效条件：`LOH_ENABLE_PENALTY=1` 且 `LOH_PENALTY_SCALE=survival`。

- LOH_SURVIVAL_BINS
  - 作用：survival 模式的直方图 bin 数量。
  - 默认：64
  - 生效条件：`LOH_ENABLE_PENALTY=1` 且 `LOH_PENALTY_SCALE=survival`。

- LOH_SURVIVAL_MINCOUNT
  - 作用：survival 模式冷启动最小样本数（低于此数回退到 log 模式）。
  - 默认：1000
  - 生效条件：`LOH_ENABLE_PENALTY=1` 且 `LOH_PENALTY_SCALE=survival`。

- LOH_REWARD_USE_PENALTY / LOH_REWARD_USE_MISSRATIO / LOH_REWARD_USE_MISSRATIOTREND
  - 作用：奖励是否包含 penalty / miss_ratio / missratiotrend 组件。
  - 默认：penalty=true，missratio=false，missratiotrend=false

- LOH_REWARD_W_PENALTY / LOH_REWARD_W_MISS / LOH_REWARD_W_TREND
  - 作用：各奖励组件权重。
  - 默认：1.0 / 1.0 / 0.5

- **LOH_REWARD_EMA**
  - 作用：是否启用 EMA 平滑（0=禁用，1=启用）。
  - 默认：0（禁用）
  - 说明：启用时对最终 reward 应用指数加权移动平均。
    - 当 `LOH_ENABLE_PENALTY=0` 时，EMA 在 `step()` 中应用于即时 reward。
    - 当 `LOH_ENABLE_PENALTY=1` 时，EMA 在 `compute_final_rewards()` 中应用于修正后的 reward。

- **LOH_REWARD_EMAWINDOW**
  - 作用：EMA 平滑窗口大小。
  - 默认：10
  - 生效条件：`LOH_REWARD_EMA=1`

- LOH_MISSRATIOTREND_WINDOW
  - 作用：miss ratio 趋势计算窗口大小。
  - 默认：100
  - 生效条件：`LOH_REWARD_USE_MISSRATIOTREND=1`
  - 兼容：支持旧变量名 `LOH_TREND_WINDOW`（fallback）

- LOH_MISSRATIOTREND_MODE
  - 作用：趋势计算模式（`slope|delta`）。
  - 默认：`slope`
  - 生效条件：`LOH_REWARD_USE_MISSRATIOTREND=1`
  - 兼容：支持旧变量名 `LOH_TREND_MODE`（fallback）

- LOH_MISS_COMPONENT
  - 作用：miss 组件模式（`neg` 或 `improve`）。
  - 默认：`neg`

---

## 六、日志（Python/Shell）

- LOH_ENABLE_PROFILING
  - 作用：控制 Python 端 profiling 计时器是否启用，对关键路径做耗时统计并在训练结束或中断时打印概要。
  - 默认：1（开启；设置为 `0/false/no/off` 时禁用 profiling，所有计时调用退化为空操作）。
  - 生效端：`scripts/loh_actor_critic_sb3.py` 以及基于它的 penalty / TD3 / PPO 变体共用的 `GLOBAL_TIMER`。

- RUN_TIMESTAMP（shell 生成）
  - 作用：用于 run 目录与日志文件前缀，对齐两端日志时间。
  - 默认：`test_loh_rl_sb3.sh` 导出当前时间；Python独立运行时若无，则用系统时间新建 `runs/<timestamp>`。

---

## 七、测试脚本（shell harness）相关

- LEARNING_STARTS
  - 作用：训练启动前的暖启动步数（传给 Python 脚本的 `--learning-starts`）。
  - 默认：1000

- EXCLUDE_RECENT_STEPS
  - 作用：采样时排除最近的步数（传给 Python 的 `--exclude-recent-steps`）。
  - 默认：100

- PYTHON_SCRIPT
  - 作用：选择 Python 训练脚本。
  - 默认：`loh_actor_critic_sb3.py`（位置参数 5 可覆盖）

- EVICTION_ALGO
  - 作用：cachesim 逐出算法名。
  - 默认：`LOH`（位置参数 6 可覆盖；如 `loh-mr-blocked`、`loh-mr-noblocked`）

- RL_UPDATE_INTERVAL
  - 作用：传给 C 端（eviction-params）的 RL 更新间隔。
  - 默认：未设置（不传）

- CACHESIM_NUM_REQ
  - 作用：限制 cachesim 处理的请求数。
  - 默认：未设置（处理整个 trace）

- LOH_PARALLEL_SAFE
  - 作用：并行安全模式；仅清理本次 `LOH_SHM_KEY` 对应的共享内存，避免干扰其它实例。
  - 默认：0（关闭）

### C 端 RL 开关与固定权重（不经 Python 训练）

- LOH_ENABLE_RL / LOH_DISABLE_RL
  - 作用：控制 C 端 LOH / LOH-mr-blocked 是否启用与 Python 进程的 RL 同步（共享内存 + 信号量）。
  - 默认：启用 RL（`enable_rl=1`）。
  - 解析规则：
    - 若设置了 `LOH_ENABLE_RL`，则优先按其布尔值解析（`1/true/yes/on`=开启；`0/false/no/off`=关闭）；
    - 否则若设置了 `LOH_DISABLE_RL`，则 `1/true/yes/on` 表示关闭 RL，`0/false/no/off` 表示保持开启；
    - 两个变量均未设置时，保持默认（启用 RL，同步 Python 权重）。
  - 生效端：C 端 `LOH`、`LOH-mr-blocked` 以及基于同一实现的变体；可在直接运行 `_build_dbg/bin/cachesim` 时使用，无需经过 shell 脚本。

- LOH_FIXED_WEIGHTS
  - 作用：在 C 端直接指定 6 维固定权重，完全绕过 Python 训练/推理，走“纯 C 固定权重”路径。
  - 格式：字符串形式的 6 个浮点数，例如：`"0,0,1,0,0,0"`，逗号/分号/空格分隔均可；必须恰好给出 6 个数，否则 C 端会忽略并保留默认权重。
  - 默认：未设置时，C 端使用内建缺省 `weights=[1,0,0,0,0,0]`。
  - 生效端：C 端 `LOH` / `LOH-mr-blocked`；通常配合 `LOH_ENABLE_RL=0` 一起使用，例如：
    - `LOH_ENABLE_RL=0 LOH_FIXED_WEIGHTS="0,0,1,0,0,0" _build_dbg/bin/cachesim ... LOH 0.1`。

  - 提示：若仍通过 `scripts/test_loh_rl_sb3.sh` 启动 RL pipeline，但只想在 C 端覆盖权重，可以设置 `LOH_FIXED_WEIGHTS` 而不关闭 RL，此时 Python 会照常运行，但 C 在每次同步后会用该固定向量覆盖从 Python 读取的权重。

---

## 八、SB3 超参覆盖（Python）

**说明**：统一脚本 `loh_actor_critic_sb3.py` 现已整合 PPO/SAC/TD3 三种算法，通过 `LOH_RL_ALGO` 环境变量选择。各算法的超参数可通过对应前缀的环境变量覆盖。

### PPO 超参覆盖

- PPO_BUFFER_SIZE：默认 20480（on-policy buffer）
- PPO_BATCH_SIZE：默认 32
- PPO_N_STEPS：默认 512（每次 rollout 步数）
- PPO_N_EPOCHS：默认 10（每次更新的 epoch 数）
- PPO_LEARNING_RATE：默认 1e-4
- PPO_CLIP_RANGE：默认 0.2
- PPO_ENT_COEF：默认 0.02（熵系数）
- PPO_VF_COEF：默认 0.5（价值函数系数）
- PPO_MAX_GRAD_NORM：默认 0.5（梯度裁剪）
- PPO_GAE_LAMBDA：默认 0.95（GAE λ）
- PPO_NET_ARCH：默认 "256,256"（逗号分隔整数）
- PPO_ACTIVATION_FN：默认 ReLU（支持 tanh/elu/leakyrelu/relu）

### SAC 超参覆盖

- SAC_BUFFER_SIZE：默认 10000（mr_SAC 变体 100000）
- SAC_BATCH_SIZE：默认 256
- SAC_LEARNING_RATE：默认 3e-4
- SAC_TAU：默认 0.005
- SAC_GAMMA：默认 0.99
- SAC_TRAIN_FREQ：默认 16 （表示每 16 step 训练一次）
- SAC_GRADIENT_STEPS：默认 1
- SAC_LEARNING_STARTS：默认 3000（开始更新前的收集步数）
- SAC_ENT_COEF：默认 "auto"（若设置为数值或字符串如 0.1 则传入模型）
- SAC_TARGET_ENTROPY：默认 None（未设置时让 SB3 根据动作维度自动推断）
- SAC_NET_ARCH：默认 "256,256"（逗号分隔整数，非法输入回退到 [256,256]）
- SAC_ACTIVATION_FN：默认 ReLU（支持 tanh / elu / leakyrelu / relu）

含义简述：
- buffer_size：ReplayBuffer 最大条目数；较小值减小内存占用，加快回放的“新鲜度”。
- train_freq / gradient_steps：交替控制策略更新频率与每次批量梯度步数；在高频 eviction 事件下避免过度训练卡住 C 端。
- ent_coef / target_entropy：熵调节，可通过 `ent_coef="auto"` 自适应；显式 target_entropy 时传入 sac_config 覆盖。

### TD3 超参覆盖

脚本 `scripts/loh_actor_critic_sb3_pen_d_TD3.py` 中支持以下环境变量：

- TD3_BUFFER_SIZE：默认 10000
- TD3_LEARNING_STARTS：默认 3000
- TD3_BATCH_SIZE：默认 256
- TD3_LEARNING_RATE：默认 3e-4
- TD3_GAMMA：默认 0.99
- TD3_TAU：默认 0.005
- TD3_TRAIN_FREQ：默认 16（表示 (16, 'step')）
- TD3_GRADIENT_STEPS：默认 1
- TD3_POLICY_DELAY：默认 2（延迟策略更新频率）
- TD3_NET_ARCH：默认 "256,256"（可覆盖 MLP 层结构）
- TD3_ACTIVATION_FN：默认 ReLU（同 SAC 支持 tanh / elu / leakyrelu / relu）
- TD3_TARGET_POLICY_NOISE：默认 None（未设置使用 SB3 默认噪声）
- TD3_TARGET_NOISE_CLIP：默认 None（未设置使用 SB3 默认裁剪）
- TD3_ACTION_NOISE：默认 None；若提供数值（如 0.05）则构造 `NormalActionNoise`（sigma 为该值）。

说明与差异：
- TD3_POLICY_DELAY 控制 actor 的更新节奏；默认 2 与 SB3 一致。
- 噪声相关变量只有在显式设置时才写入配置，保持与 SB3 默认行为兼容。
- ACTION_NOISE 仅在环境变量提供时注入高斯探索噪声，方便快速对比“确定性 vs 带噪声”策略对缓存 miss 的影响。

---

## 九、默认值来源与优先级小结

- **算法选择**：`LOH_RL_ALGO` 环境变量控制算法（PPO/SAC/TD3），默认 SAC。
- **Penalty 机制**：`LOH_ENABLE_PENALTY` 控制启用/禁用（默认 0，禁用）；启用时才读取 `LOH_PENALTY_SCALE` 等相关变量。

- **状态维度**（新设计）：
  - C 端始终传递前 2 维（hit_ratio, byte_hit_ratio），用于奖励计算
  - 总维度公式：`CONTEXT_DIM = 2 + HIT_MISS(0/24) + CACHE(0/12) + CAND(0/72) + TOPK(0/192)`
  - 默认配置：`LOH_INCLUDE_TOPK_CANDIDATE_FEATURES=1` → 2 + 192 = 194 维

- **RL 观察空间控制**：
  - `RL_STATE_USE_MISSRATIO`：控制 RL 模型是否"看到"前 2 维（默认 1，包含）
  - 设为 0 时，RL 观察空间从索引 2 开始，但奖励计算仍使用完整 state

- 信号量：禁用优先（`LOH_DISABLE_SEMAPHORE` 覆盖 `LOH_ENABLE_SEMAPHORE`）。超时后自动回退轮询。
- 共享内存 key：优先脚本生成；否则 C/Python各自默认 9876。

---

## 十、验证建议

1) Python 端打印 ctypes 结构（开启 `LOH_PRINT_SHM_LAYOUT=1`）：
```
[SHM] Python SharedMemoryData sizeof=... bytes (STATE_DIM=...)
[SHM] field ready_for_inference @ offset ...
...
```
2) C 端在初始化处打印 `sizeof(shm_data_t)`（已有日志）。
3) 若大小或偏移不一致：检查状态维度相关环境变量是否 C/Python 两端一致：
   - `LOH_INCLUDE_HIT_MISS_FEATURES`
   - `LOH_INCLUDE_CACHE_FEATURES`
   - `LOH_INCLUDE_CANDIDATE_FEATURES`
   - `LOH_INCLUDE_TOPK_CANDIDATE_FEATURES`

---

## 十一、示例：统一脚本使用与配置

### 示例 1：默认配置（TOPK 特征，194 维）

```bash
# 默认：2 + 192 = 194 维
export LOH_RL_ALGO=SAC
export LOH_DEBUG_LEVEL=1
bash scripts/test_loh_rl_sb3.sh /path/to/trace 0.1 1.0
```

### 示例 2：启用所有特征（302 维）

```bash
# 2 + 24 + 12 + 72 + 192 = 302 维
export LOH_INCLUDE_HIT_MISS_FEATURES=1
export LOH_INCLUDE_CACHE_FEATURES=1
export LOH_INCLUDE_CANDIDATE_FEATURES=1
export LOH_INCLUDE_TOPK_CANDIDATE_FEATURES=1
export LOH_RL_ALGO=SAC
bash scripts/test_loh_rl_sb3.sh /path/to/trace 0.1 1.0
```

### 示例 3：RL 模型不观察 miss ratio（但奖励仍使用）

```bash
# RL 观察空间从索引 2 开始，但奖励计算使用完整 state
export RL_STATE_USE_MISSRATIO=0
export LOH_RL_ALGO=PPO
export PPO_N_STEPS=1024
bash scripts/test_loh_rl_sb3.sh /path/to/trace 0.1 1.0
```

### 示例 4：使用 TD3 算法 + survival penalty

```bash
export LOH_RL_ALGO=TD3
export LOH_ENABLE_PENALTY=1
export LOH_PENALTY_SCALE=survival
export LOH_SURVIVAL_BINS=128
export TD3_ACTION_NOISE=0.1
bash scripts/test_loh_rl_sb3.sh /path/to/trace 0.1 1.0
```

### 示例 5：候选特征配置（86 维）

```bash
# 2 + 12 + 72 = 86 维（缓存 + 候选特征）
export LOH_INCLUDE_CACHE_FEATURES=1
export LOH_INCLUDE_CANDIDATE_FEATURES=1
export LOH_INCLUDE_TOPK_CANDIDATE_FEATURES=0
export LOH_SHM_KEY=24680
bash scripts/test_loh_rl_sb3.sh /path/to/trace 0.1 1.0
```

- 期望：
  - C/Python 打印统一，候选特征最后输出为 `[candidate_features_1..6]`，每行 12 个值
  - 总维度 = 2 + 12 + 72 = 86

---

## 十二、Bandit 实验（`loh_bandit_ucb.py`）相关环境变量

脚本 `scripts/loh_bandit_ucb.py` 提供一个基于 UCB 的 bandit 策略，用于在若干固定权重臂之间做在线试探与选择，其主要环境变量为：

- LOH_BANDIT_UCB_C
  - 作用：UCB 算法的探索系数 `c`，控制探索 vs 利用的权衡。
  - 默认：1.0

- LOH_BANDIT_ARMS
  - 作用：自定义一组待比较的静态权重“臂”（arms），供 bandit 策略在线选择。
  - 格式示例：`"0,0,1,0,0,0; 0.5,0,0.5,0,0,0"` 表示两组 6 维权重；具体解析规则以 `scripts/loh_bandit_ucb.py` 实现为准。
  - 默认：未设置时使用脚本内置的一小组典型权重向量。

- LOH_BANDIT_REWARD_MODE
  - 作用：bandit 奖励模式。
  - 取值：
    - `neg_miss`（默认）：奖励使用 `-miss_ratio`；
    - `delta_miss`：奖励使用 miss ratio 的差分（相对基础策略的改善量）。
  - 默认：`neg_miss`。

---

如需补充本清单或发现默认值与代码不符，请在 `docs/` 目录提交更新 PR。
