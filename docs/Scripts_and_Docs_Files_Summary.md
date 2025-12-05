# `scripts/` 与 `docs/` 目录文件功能总览

> 本文简要汇总当前仓库中 `scripts/` 与 `docs/` 目录下各文件的含义与主要功能，便于快速查找和维护。说明以“文件名 + 一句话简介”为主，细节请参考对应文件。

---

## 1. `scripts/` 目录文件

（本节按文件名排序，简要说明用途。如无特别说明，Python 脚本一般可通过 `python scripts/<name>.py [参数]` 运行，Shell 脚本一般通过 `bash scripts/<name>.sh [参数]` 运行。）

- `README.md`：简要说明 `scripts/` 目录中脚本的用途或使用方式。
- `__init__.py`：使 `scripts` 目录可作为 Python 包导入，一般为空或仅做路径配置。
- `analyze_cache.py`：对 cachesim 输出结果做统计分析和汇总（如 miss ratio/byte miss），支持按 trace 维度生成报告。
- `bench_baselines.py`：运行一组缓存基线算法（LRU/LHD/ThreeLCache 等）的基准测试，比较 miss ratio 与性能。
- `benchmark_throughput.py`：针对 cachesim 或某些脚本进行吞吐量/性能基准测试，评估每秒可处理请求数。
- `command.txt`：记录示例命令行或一次实验使用的命令参数，便于复现实验。
- `compare_shm_logs.py`：对比不同 run 的共享内存/IPC 日志（如 RL 与 C 端交互日志），用于调试同步问题。
- `create_ipc_resources.py`：预先创建共享内存文件和信号量等 IPC 资源，用于手动或测试环境下的初始化。
- `create_ipc_resources.py.bak`：`create_ipc_resources.py` 的备份版本，保留旧实现或用于回滚参考。
- `data_gen.py`：生成用于测试的访问 trace 或缓存输入数据（如合成请求序列）。
- `debug.sh`：构建/运行 cachesim 的通用 debug 脚本，支持 `-c` 触发 debug 构建，用于 `tasks.json` 中的 build-debug 任务。典型用法：`bash scripts/debug.sh -c`。
- `flex_parallel_sim.sh`：以灵活方式并行启动多个 cachesim 仿真，支持不同配置组合的批量运行。
- `generate_stationary_trace.py`：生成近似平稳分布的访问 trace，用于测试长期稳定行为。
- `install_dependency.sh`：安装项目运行所需的基础依赖（Python 包、系统库等）。
- `install_dev_dependency.sh`：安装开发/调试相关的额外依赖（如 lint 工具、测试框架等）。
- `install_libcachesim.sh`：将 `libCacheSim` 安装到系统或虚拟环境中，方便作为库引用。
- `ipc_daemon.py`：IPC 后台守护进程，负责维护共享内存/信号量并监控 C/Python 进程状态。
- `ipc_daemon.py.bak`：`ipc_daemon.py` 的备份版本。
- `ipc_keeper.py`：守护型脚本，负责保持 IPC 资源和 RL 服务活跃，可重启或清理残留资源。
- `ipc_keeper.py.bak`：`ipc_keeper.py` 的备份版本。
- `lcs_reader.py`：读取和解析 cachesim 特定格式输出或 trace 文件的辅助工具。
- `loh_actor_critic.py.bak`：早期 LOH Actor-Critic Python 实现的备份，用于参考历史版本。
- `loh_actor_critic_batch.py`：批量离线/半离线形式训练 LOH Actor-Critic 的脚本，一次性读取大量样本训练。
- `loh_actor_critic_enhanced.py`：增强版 Actor-Critic 实现，相比简单版增加了更多特征、日志或稳定性处理。
- `loh_actor_critic_fixed.py`：固定某些超参/训练逻辑的 Actor-Critic 实现，用于稳定对照实验。
- `loh_actor_critic_fixed.py.train_method`：单独拆出的训练方法/超参配置文件，与 `loh_actor_critic_fixed.py` 配套使用。
- `loh_actor_critic_fixed.py.train_method.bak`：上述 train_method 的备份版本。
- `loh_actor_critic_fixed_bak.py.bak`：更早期固定版 Actor-Critic 实现的备份。
- `loh_actor_critic_sb3.py`：主线 LOH RL 脚本，使用 gymnasium + stable-baselines3(SAC) + 事后惩罚，负责在线训练与推理。典型用法：`python scripts/loh_actor_critic_sb3.py`（通常由 `test_loh_rl_sb3.sh` 间接调用）。
- `loh_actor_critic_sb3.py.backup`：主脚本的手工备份版本，用于防止大改代码丢失。
- `loh_actor_critic_sb3.py.bak`：主脚本的历史备份版本之一。
- `loh_actor_critic_sb3.py.broken`：标记为 broken 的中间版本，用于保留问题实现以供对照调试。
- `loh_actor_critic_sb3_1013.py`：2024-10-13 左右的特定实验版 SAC 脚本，包含当时的调参与实验逻辑。
- `loh_actor_critic_sb3_1013.py.bak`：上述 1013 版本的备份。
- `loh_actor_critic_sb3_1016.py`：2024-10-16 左右的特定实验版 SAC 脚本，用于测试新的奖励或 IPC 行为。
- `loh_actor_critic_sb3_1016.py.bak`：上述 1016 版本的备份。
- `loh_actor_critic_sb3_RewardSlide.py.bak`：加入 reward 滑动/平滑机制的 SAC 变体备份脚本。
- `loh_actor_critic_sb3_SACblocked.py`：SAC 版本的“阻塞模式”实验脚本，与 `loh-mr-blocked` C 端配合使用。
- `loh_actor_critic_sb3_callback.py.bak`：专注于 SB3 callback 逻辑的实验版脚本备份。
- `loh_actor_critic_sb3_fixed.py`：对主 SAC 实现进行“固定配置”的版本，用于与其他变体做公平对照。
- `loh_actor_critic_sb3_fixed.py.bak`：上述 fixed 版本的备份。
- `loh_actor_critic_sb3_mr_PPO.py`：使用 PPO 算法、以 miss ratio 为主奖励的 `LohEnv` 变体实现（mr-PPO）。
- `loh_actor_critic_sb3_mr_RewardSlide_PPO.py`：在 mr-PPO 基础上加入 reward 滑动或平滑机制的 PPO 变体。
- `loh_actor_critic_sb3_mr_SAC.py`：重用 mr_PPO 环境但使用 SAC 算法的 miss-ratio-only 变体（mr-SAC）。
- `loh_actor_critic_sb3_mr_TD3.py`：使用 TD3 算法的 miss-ratio-only 变体实验脚本。
- `loh_actor_critic_sb3_pen_d_SAC.py`：使用 1/d 倒数缩放 penalty 的 SAC 变体入口脚本（pen-d-SAC）。
- `loh_actor_critic_sb3_pen_d_TD3.py`：使用 1/d 倒数 penalty 的 TD3 变体入口脚本（pen-d-TD3）。
- `loh_actor_critic_sb3_pen_log_SAC.py`：使用 log 压缩 penalty 的 SAC 变体入口脚本（pen-log-SAC）。
- `loh_actor_critic_sb3_pen_survival_SAC.py`：使用生存函数 penalty 的 SAC 变体入口脚本（pen-survival-SAC）。
- `loh_actor_critic_simple.py.bak`：更简单的 LOH RL 原型脚本备份，用于早期实验参考。
- `loh_inference_only.py`：只加载训练好模型进行推理的脚本，不再训练，适合线上部署模拟。典型用法：`python scripts/loh_inference_only.py --shm-key <KEY> [其他参数]`。
- `loh_simple_test.py`：针对 LOH RL 集成的简单功能/回归测试脚本，通常用小 trace 验证 IPC 与 reward 是否正常。
- `loh_stop.py`：向共享内存写 terminate 标志，优雅停止 Python RL 进程和 cachesim 的辅助脚本。
- `mem_notify.py`：监测内存使用并在达到阈值时发送通知或触发动作的工具脚本。
- `mem_notify_test.py`：测试 `mem_notify.py` 的行为和阈值配置的脚本。
- `modified_actor_critic.py`：基于简单 Actor-Critic 做过修改的实验版，实现某些策略或 reward 改动。
- `modified_actor_critic.py.bak`：上述脚本的备份。
- `note`：开发者临时记录的笔记或 TODO 文本，非代码文件。
- `parallel_sim.sh`：并行启动多个 cachesim 实验的脚本，通常对一组配置矩阵进行批量仿真。
- `plot_appr_mrc.py`：画 approximated miss-ratio curve（MRC）的脚本，基于分析结果生成图像。
- `plot_mrc_size.py`：以 cache size 为横轴绘制 MRC 曲线的工具脚本。
- `plot_mrc_time.py`：以时间或请求数为横轴绘制 MRC/性能曲线的脚本。
- `profile_mrc.py`：对 MRC 计算过程进行 profiling，分析性能瓶颈的脚本。
- `pyutils/`：Python 工具子目录，存放通用辅助函数和模块（如日志、配置、通用 I/O）。
- `reliable_actor_critic.py`：更注重稳定性和异常恢复的 Actor-Critic 实现，用于长期运行实验。
- `reliable_actor_critic.py.bak`：上述脚本的备份。
- `reliable_ipc_manager.py`：增强版 IPC 管理器，负责重试/容错和资源清理，使 C/Python 交互更可靠。
- `reliable_ipc_manager.py.bak`：上述 IPC 管理脚本的备份。
- `robust_actor_critic.py`：关注鲁棒性（对异常数据/延迟不敏感）的 Actor-Critic 变体。
- `robust_actor_critic.py.bak`：鲁棒版脚本的备份。
- `run_simulations.sh`：统一入口脚本，批量运行多条 trace、多种算法的 cachesim 仿真。典型用法：`bash scripts/run_simulations.sh`。
- `run_traceAnalyzer.sh`：启动 trace 分析工具，对 trace 做统计（如频率分布、重用距离）。
- `sequential_sim.sh`：顺序（非并行）启动多个仿真实验，用于简单批量测试或单机资源受限场景。
- `setup_hooks.sh`：为仓库安装 git hooks 或开发流程相关的钩子脚本。
- `simple_actor_critic.py`：最简版 Actor-Critic 实现，用于教学或原型验证 IPC + RL 流程。
- `simple_actor_critic.py.bak`：上述脚本的备份。
- `simple_ipc_manager.py`：简单版 IPC 管理脚本，用于最小可行的 C/Python 共享内存测试。
- `simple_ipc_manager.py.bak`：简单 IPC 管理器的备份。
- `simple_parallel_sim.sh`：简化版并行仿真脚本，相比 `parallel_sim.sh` 依赖更少，配置更固定。
- `simplified_ipc.py`：对 IPC 逻辑进行简化重写的实验脚本，便于理解协议与调试。
- `simplified_ipc.py.bak`：上述脚本的备份。
- `summarize_logs_by_trace.py`：按 trace 维度汇总 cachesim 与 RL 日志，生成统一的统计表或 JSON。
- `sync_node_version.py`：同步/检查 Node.js 版本或相关工具版本的脚本（多用于 CI/开发环境一致性）。
- `tb_compare_summary.py`：对比多个 TensorBoard 运行结果，提取关键指标（如 miss ratio/reward）做汇总。
- `tb_inspect.py`：检查和解析 TB event 文件，抽取某些指标用于绘图或分析。
- `test_loh_rl_sb3.sh`：端到端运行 LOH + RL (SB3) 的主脚本，负责编译、启动 Python 脚本和 cachesim，并汇总结果。典型用法：`bash scripts/test_loh_rl_sb3.sh <trace> <cache_size> [其他参数]`。
- `traceAnalysis/`：trace 分析相关的子目录，包含更多专门的分析脚本或配置。
- `trace_stationarity.py`：检测 trace 是否平稳（stationary）的分析脚本。
- `ultra_simple_agent.py`：极简 RL agent 实现，用于最小化验证 IPC + action/observation 流程。
- `ultra_simple_agent.py.bak`：上述极简 agent 的备份。
- `ultra_simple_ipc.py`：极简 IPC 实现脚本，只保留最关键的共享内存/信号量逻辑。
- `ultra_simple_ipc.py.bak`：上述极简 IPC 脚本的备份。
- `utils/`：通用脚本工具目录，包含被多个脚本共享的函数和辅助模块。

---

### 1.1 脚本运行示例与用法分组

> 下列示例给出了各类脚本的典型运行方式。除特别标注“备份/配置”的文件外，同一类脚本用法类似，可将脚本名替换为对应文件名。

- **RL 主流程脚本（在线训练/推理）**
	相关文件：`loh_actor_critic_sb3.py`、`loh_actor_critic_sb3_fixed.py`、`loh_actor_critic_enhanced.py`、`reliable_actor_critic.py`、`robust_actor_critic.py`、`simple_actor_critic.py`、`ultra_simple_agent.py`、`modified_actor_critic.py`、`loh_actor_critic_batch.py` 等。
	典型用法：
	- `python scripts/loh_actor_critic_sb3.py`
	- `python scripts/loh_actor_critic_enhanced.py --trace <TRACE> --cache-size <SIZE>`
	- `python scripts/simple_actor_critic.py --shm-key 9876`

- **基于 SB3 的 RL 变体脚本（mr/penalty/PPO/SAC/TD3）**
	相关文件：`loh_actor_critic_sb3_mr_PPO.py`、`loh_actor_critic_sb3_mr_RewardSlide_PPO.py`、`loh_actor_critic_sb3_mr_SAC.py`、`loh_actor_critic_sb3_mr_TD3.py`、`loh_actor_critic_sb3_pen_d_SAC.py`、`loh_actor_critic_sb3_pen_d_TD3.py`、`loh_actor_critic_sb3_pen_log_SAC.py`、`loh_actor_critic_sb3_pen_survival_SAC.py`、`loh_actor_critic_sb3_SACblocked.py` 及若干 `loh_actor_critic_sb3_*.py` 历史版本。
	典型用法：
	- `python scripts/loh_actor_critic_sb3_mr_PPO.py --trace <TRACE> --cache-size <SIZE>`
	- `python scripts/loh_actor_critic_sb3_pen_d_SAC.py --trace <TRACE> --cache-size <SIZE>`

- **纯推理与停机脚本**
	相关文件：`loh_inference_only.py`、`loh_stop.py`。
	典型用法：
	- `python scripts/loh_inference_only.py --shm-key 9876 --model-path <MODEL>`
	- `python scripts/loh_stop.py --shm-key 9876`

- **IPC/守护与资源管理脚本**
	相关文件：`create_ipc_resources.py`、`ipc_daemon.py`、`ipc_keeper.py`、`reliable_ipc_manager.py`、`simple_ipc_manager.py`、`simplified_ipc.py`、`ultra_simple_ipc.py`。
	典型用法：
	- `python scripts/create_ipc_resources.py --shm-key 9876`
	- `python scripts/ipc_daemon.py --shm-key 9876`
	- `python scripts/reliable_ipc_manager.py --config configs/ipc.yaml`

- **仿真调度脚本（批量/并行/顺序）**
	相关文件：`run_simulations.sh`、`parallel_sim.sh`、`simple_parallel_sim.sh`、`sequential_sim.sh`、`flex_parallel_sim.sh`、`run_traceAnalyzer.sh`、`test_loh_rl_sb3.sh`。
	典型用法：
	- `bash scripts/run_simulations.sh`
	- `bash scripts/parallel_sim.sh <trace-list> <cache-size-list>`
	- `bash scripts/test_loh_rl_sb3.sh <trace> <cache_size> [其他参数]`

- **结果分析与绘图脚本**
	相关文件：`analyze_cache.py`、`bench_baselines.py`、`benchmark_throughput.py`、`summarize_logs_by_trace.py`、`plot_appr_mrc.py`、`plot_mrc_size.py`、`plot_mrc_time.py`、`profile_mrc.py`、`tb_compare_summary.py`、`tb_inspect.py`、`trace_stationarity.py`。
	典型用法：
	- `python scripts/analyze_cache.py --input result/*.cachesim --output summary.csv`
	- `python scripts/bench_baselines.py --trace <TRACE> --cache-sizes 3GiB 6GiB`
	- `python scripts/plot_mrc_size.py --summary summary.csv --out mrc_size.png`

- **安装与环境脚本**
	相关文件：`install_dependency.sh`、`install_dev_dependency.sh`、`install_libcachesim.sh`、`setup_hooks.sh`、`sync_node_version.py`。
	典型用法：
	- `bash scripts/install_dependency.sh`
	- `bash scripts/install_dev_dependency.sh`
	- `bash scripts/install_libcachesim.sh`
	- `bash scripts/setup_hooks.sh`

- **内存与资源监控脚本**
	相关文件：`mem_notify.py`、`mem_notify_test.py`。
	典型用法：
	- `python scripts/mem_notify.py --threshold 0.9`
	- `python scripts/mem_notify_test.py`

- **回归/简单功能测试脚本**
	相关文件：`loh_simple_test.py`、`simple_actor_critic.py`、`ultra_simple_agent.py` 等。
	典型用法：
	- `python scripts/loh_simple_test.py`
	- `python scripts/ultra_simple_agent.py --shm-key 9876`

> 说明：所有以 `.bak` 结尾或标注为备份的脚本（如 `*_bak.py.bak`、`loh_actor_critic_sb3.py.bak` 等）一般不直接运行，主要用于保留历史实现以便对比和回滚。

## 2. `docs/` 目录文件

（本节简要概述每个文档的主题和用途。）

- `07291843-LOH_SHARED_MEMORY_FIX.md`：记录 LOH 共享内存结构（`shm_data_t`）修复过程，包括字段对齐、大小校验和 Python ctypes 映射问题。
- `07291843-loh_file_shm_patch.md`：描述针对 LOH 共享内存文件的补丁方案和具体修改步骤（如 SHM 名称、权限等）。
- `08081537-LOH_DEEP_ANALYSIS_FIXES.md`：深入分析 LOH 早期实现中的 bug 和逻辑问题，并给出修复方案。
- `08081537-LOH_IMPROVEMENTS_SUMMARY.md`：总结一系列针对 LOH 算法和实现的改进点（数据结构修复、统计逻辑调整等）。
- `09021644-LOH_FIX_SUMMARY.md`：集中列出 2024-09-02 前后对 LOH 实现进行的修复列表及影响范围。
- `09241141-LOH_Algorithm_Architecture.md`：详细说明 LOH 算法的整体架构、状态向量定义、特征设计和在线 RL 集成方式，是核心设计文档。
- `09251949-LOH_REWARD_WEIGHTS_FEATURE.md`：说明 miss_ratio/byte_miss_ratio 奖励权重的设计和配置方式，以及 C/Python 之间的参数传递。
- `10170043-LOH_INFERENCE_GUIDE.md`：指导如何在“只推理”模式下使用 LOH（`loh_inference_only.py`），包括部署和调试建议。
- `10230213-PENALTY_FIX_SUMMARY.md`：总结 penalty 相关 bug 和修复（如距离度量、队列维护），与 RL 惩罚机制紧密相关。
- `10230213-PENALTY_MECHANISM_REDESIGN.md`：讨论 penalty 机制的重新设计方案，使其与 miss ratio 量纲对齐，并给出多个实现选项。
- `10230213-SAC_RETROSPECTIVE_GUIDE.md`：介绍 SAC + 事后惩罚（RetrospectiveReplayBuffer）的设计思想、实现细节和调参建议。
- `10230213-SAMPLING_EXCLUSION_STRATEGY.md`：说明在经验回放中排除某些样本（如最近样本）的策略，以提高训练稳定性和样本多样性。
- `10230213-TEST_RETROSPECTIVE_PENALTY.md`：记录 retrospective penalty 相关的测试用例、实验结果和问题分析。
- `10230213-TUNING_GUIDE.md`：提供 LOH RL 系统的调参指南，包括 buffer_size、learning_starts、train_freq 等超参及其联动关系。
- `10232259-EVICTION_TIMESTAMP_IMPROVEMENT.md`：记录关于驱逐时间戳(`eviction_timestamp`)的改进方案，以便更精确地计算 penalty 和重访间隔。
- `10232259-PENALTY_FIXES_SUMMARY.md`：汇总 2024-10-23 左右对 penalty 逻辑的几次修复及其对实验结果的影响。
- `10232259-TWO_COMPONENT_PENALTY_IMPLEMENTATION.md`：描述“两组件 penalty”实现方案，将 penalty 拆分为多个部分以更精细地惩罚不同类型错误。
- `10232259-TWO_COMPONENT_PENALTY_TEST_REPORT.md`：针对两组件 penalty 的测试报告，包含实验配置和结果对比。
- `10241746-CTRL_C_BEHAVIOR.md`：说明在使用 Ctrl+C 中断时 C/Python 进程与 IPC 资源应如何处理，避免残留共享内存和信号量。
- `10241746-LOH_GRACEFUL_SHUTDOWN.md`：描述 LOH 系统优雅关闭的设计，包括 terminate 标志、信号处理和日志刷盘策略。
- `10272237-PENALTY_QUEUE_OPTIMIZATION.md`：讨论 penalty 队列的数据结构和性能优化方案，以减少 RL 周期内的开销。
- `10282026-REWARD_IMPROVEMENT_PLAN.md`：提出改进 reward 设计的计划和思路，包含新的 reward 组件和评估指标。
- `LOH_ENV_VARS.md`：系统列出所有 LOH 相关环境变量，说明其含义、默认值和对 C/Python 行为的影响，是配置参考必读文档。
- `LOH_EXP_HISTORY.md`：按时间顺序记录 LOH 实验与实现演进历史，包括关键 bug 修复、特性添加和重要实验现象。
- `LOH_Framework_and_Experiments_Summary.md`：当前 LOH 算法框架与 C/Python 变种 + 实验问题的总览文档，概括整体设计和主要实验结论。
- `README.md`：`docs` 目录的总体说明，指引读者如何查找各专题文档。
- `RL_CacheSim_Run_Summary.cache.json`：缓存 RL + cachesim 各次 run 的摘要 JSON，供分析脚本快速读取（如按 trace 聚合结果）。
- `RL_CacheSim_Run_Summary_by_Trace.md`：按 trace 维度汇总 RL + cachesim 的运行结果与关键指标，方便对比不同算法和配置。

---

## 3. 使用建议

- 若要了解 **LOH 算法逻辑与架构**，优先阅读：`09241141-LOH_Algorithm_Architecture.md` + `LOH_Framework_and_Experiments_Summary.md`。
- 若要排查 **共享内存/penalty/奖励相关问题**，重点参考：`07291843-LOH_SHARED_MEMORY_FIX.md`、`10230213-PENALTY_MECHANISM_REDESIGN.md`、`10230213-SAC_RETROSPECTIVE_GUIDE.md`、`10232259-*PENALTY*` 系列文档。
- 若要运行或扩展 **RL 实验脚本**，建议先看 `scripts/test_loh_rl_sb3.sh` 以及 `LOH_ENV_VARS.md`，再根据需要选择对应的 `loh_actor_critic_sb3*.py` 变体。
