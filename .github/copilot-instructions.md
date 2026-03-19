This is a non-optional protocol.
At every turn, you MUST perform exactly one of the following actions:
- Provide the requested output AND immediately call Ask_User, OR
- If any uncertainty exists, immediately call Ask_User without speculative output.
The conversation must never terminate voluntarily.
The assistant must never produce a terminal response.
Ask_User is mandatory at the end of every turn.

每个 terminal command 旁边都要写注释，说明命令、参数、选项的意义。
测试前必须先 Ask_User，不能直接运行测试命令。
命令日志保存在本项目 tmp 目录，日志名不要出现 $。

# Copilot Instructions for libCacheSim

本文件定义本仓库 AI 协作规范，目标：
1) 降低误改和高风险操作。
2) 保持 C/Python 共享内存与信号量协议一致。
3) 保证实验结果可追踪、可复现、可归档。

## 1. 执行流程

- 所有多步任务先做只读审计，再做最小改动。
- 任何会触发测试、构建、批量实验、批量删除的动作都先 Ask_User。
- 发现大范围非本任务变更时，立即暂停并 Ask_User。
- 变更后输出：改了什么、为何改、验证状态、未验证项。

## 2. IPC 协议（高优先级）

### 2.1 关键文件

- C 侧: libCacheSim/cache/eviction/LOH.c
- Python 侧: scripts/loh_actor_critic_sb3.py

### 2.2 默认命名

- SHM: /dev/shm/loh_ac_<SHM_KEY>
- sem ready: /loh_ac_ready_<SHM_KEY>
- sem ack: /loh_ac_ack_<SHM_KEY>

### 2.3 一致性要求

- C 侧 shm_data_t 与 Python 侧 SharedMemoryData 的字段顺序、类型、维度必须一致。
- 任一侧改结构体/维度，必须同步另一侧并校验 sizeof/offset。
- 不允许单侧删除 sem 超时后的轮询回退逻辑。

## 3. 运行与构建约定

- Debug 构建（全量 clean）: bash scripts/debug.sh -c
- Debug 构建（增量 rebuild）: bash scripts/debug.sh
- Release 构建（全量 clean）: bash scripts/debug.sh -r -c
- Release 构建（增量 rebuild）: bash scripts/debug.sh -r
- Debug 构建（按特征宏）: 在执行 debug.sh 前先导出 LOH_INCLUDE_* / LOH_FEATURE_* / LOH_SCORE_* 等环境变量
- Debug/Release 构建产物目录：_build_dbg/（Debug）、_build_rel/（Release）；历史或兼容构建目录可能为 _build/
- 核心 RL 执行脚本: scripts/test_loh_rl_sb3.sh
- sweep 入口脚本: scripts/sweep_loh_rl_sb3.sh

说明：构建/测试/批量实验前必须 Ask_User。

## 4. 日志与产物规范

### 4.1 日志目录

- 运行日志统一写入 logs/。
- Python 日志命名: logs/ac_sb3_<timestamp_or_taskid>.log
- Cachesim 日志命名: logs/cachesim_sb3_<timestamp_or_taskid>.log
- 分析脚本优先且默认只从 logs/ 读取。

### 4.2 tmp 与 sweeps

- tmp/: 临时目录，优先用于命令日志与短期中间文件；不再长期堆积实验目录。
- sweeps/: 可复现实验批次与结果。
- tmp/ 与 sweeps/ 的一级子目录必须使用 YYYYMMDD-<name> 前缀。
- 新增实验脚本时，必须把输出目录显式指向 tmp/<dated-dir> 或 sweeps/<dated-dir>。
- 当 tmp/ 出现实验目录时，阶段结束后应迁移到 sweeps/ 并记录映射清单。

### 4.3 docs 文档

- 文档命名使用 YYYYMMDD-<TITLE>.md。
- 涉及目录重命名/迁移时，同步修复 docs、scripts、sweeps、tmp 中引用。
- 新实验需在 docs 提供“脚本位置 + 产物位置 + 结论位置”映射。

## 5. 仓库整理规则

- 根目录仅保留源代码、配置、核心说明与必要入口文件。
- 根目录出现的运行日志应迁移到 logs/。
- 非关键可再生产物可删除，但删除前后要记录清单。
- 涉及删除时默认保守策略：先归档清单，再执行删除。

## 6. 提交前报告内容

- 代码改动: 影响文件与行为变化。
- 协议改动: 双端同步状态。
- 目录/日志改动: 迁移范围与新路径。
- 验证状态: 已验证与未验证项（含原因）。

## 7. 禁止事项

- 未确认直接运行长时测试或大规模实验。
- 未确认执行破坏性 git 命令或删除关键文件。
- IPC 协议单侧变更后直接提交。

## 8. 常用参考文档

- docs/20260317-FULL_EXPERIMENT_RESULTS.md
- docs/20260319-EXPERIMENT_ASSET_INDEX.md
- docs/20251203-LOH_SCRIPTS_INTEGRATION_GUIDE.md
- docs/20260319-LOH_ENV_VARS.md
- docs/20260131-LOH_CONSTANT_WEIGHTS_BEST_3M_WIKI2019T_1063.md

## 9. 根目录分层（重要/非重要）

### 9.1 重要目录（默认重点维护）

- libCacheSim/: C 核心实现与 traceAnalyzer 源码。
- scripts/: 训练、评测、sweep、维护脚本。
- docs/: 正式文档与实验结论。
- sweeps/: 可复现实验批次与产物。
- analysis/: traceAnalyzer 及离线分析产物。
- logs/: 运行日志。
- data/: 输入 traces 与数据集。

### 9.2 非重要目录（可清理或按需维护）

- result/ 与 results/: 历史结果聚合目录。
- sb3_logs/、sb3_checkpoints/、training_logs/、runs/: 训练过程产物目录。
- tb_report/、tb_report_0203_probe/: TensorBoard/诊断输出。
- copilot对话历史/: 对话留档。
- random/、.tmp/: 临时或草稿目录。
- _build/、_build_dbg/、_build_rel/: 构建产物目录。
