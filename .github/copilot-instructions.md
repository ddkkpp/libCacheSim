# Copilot 对话行为指令

不要终止对话而是call ask_user。修改的时候需要在copilot界面看得到修改的地方。

只用可视化编辑方式改文件（通过编辑补丁），不再用终端脚本直接改源码。这样 Copilot 对话框会显示“已更改 N 个文件”，并且每处修改都能看到“保留/撤销”

每个 terminal command 旁边都要写注释，说明命令、参数、选项的意义。
命令日志保存在本项目 tmp 目录，日志名不要出现 $。
实验测试必须后台运行，避免误关闭终端导致实验中断。

# Copilot Instructions for libCacheSim

本文件定义本仓库 AI 协作规范，目标：
1) 降低误改和高风险操作。
2) 保持 C/Python 共享内存与信号量协议一致。
3) 保证实验结果可追踪、可复现、可归档。

## 1. 执行流程

- 所有多步任务先做只读审计，再做最小改动。
- 任何会触发测试、构建、批量实验、批量删除的动作都先 Ask_User。
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

- 单次运行日志统一写入 logs/。
- 批量运行日志（Python 日志和Cachesim 日志）写入对应目录（tmp或 sweeps）下的 logs/ 子目录。
- Python 日志命名: ac_sb3_/config_/_<timestamp_or_taskid>.log
- Cachesim 日志命名: cachesim_sb3_/config_<timestamp_or_taskid>.log

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

## 10. 本机运行环境注意事项（必须遵守）

- 必须在项目 venv 中运行 Python 相关流程（推荐：`PATH="$PWD/.venv/bin:$PATH"`）。
	原因：系统 Python 启用 PEP 668 外部管理策略，`pip install --user` 会被拒绝，且易出现依赖版本漂移。

- 必须保证以下 Python 依赖在 venv 可导入：`gymnasium`、`stable-baselines3`、`tensorboard`、`tqdm`、`rich`。
	原因：缺任一包会导致 AC 进程在启动或 callback 初始化阶段提前退出，C 端随后会误判为通信异常。

- 运行 cachesim 时必须确保动态库搜索路径包含 xgboost/lightgbm 所在目录（本机通常为 `/usr/local/lib`），建议：
	`LD_LIBRARY_PATH="/usr/local/lib:${LD_LIBRARY_PATH:-}"`。
	原因：否则会出现 `libxgboost.so.3` / `lib_lightgbm.so` 加载失败，cachesim 启动即退出。

- 默认构建模式使用 Release（`LOH_BUILD_RELEASE` 默认按 1 处理），并优先使用 `_build_rel/bin/cachesim`。
	原因：与当前实验基线一致，性能与日志行为更稳定；Debug 构建仅用于问题定位。

- 实验测试统一后台运行，且命令日志写入 `tmp/`。
	原因：避免终端中断导致长任务丢失，并保留可追溯的完整执行证据。

- 本机常用 trace 绝对路径（优先使用，避免工作区缺少 `data/` 软链接导致路径失效）：
	- `/mnt/serverpool/dingkp_trace/tencentBlock/v2/else/tencentBlock_1063.oracleGeneral.zst`
	- `/mnt/serverpool/dingkp_trace/wiki/wiki_2019t.oracleGeneral.zst`
	- `/mnt/serverpool/dingkp_trace/metaCDN/meta_reag.oracleGeneral.zst`
	原因：当前机器上多仓库并存，部分仓库不含 `data/` 目录；统一绝对路径可减少“Trace file not found”误报并提高复现实验稳定性。
