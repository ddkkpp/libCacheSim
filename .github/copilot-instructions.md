# Copilot 对话行为指令

完成后call vscode_askQuestions（提供空白选项），等待程序运行结果时采取后台等待，前台call vscode_askQuestions。

只用 Copilot 补丁工具改源码/文档，不再用终端脚本直接改内容。
记住有待运行的任务时永远不要编译覆盖原来的版本

实验测试必须后台运行，避免误关闭终端导致实验中断。

只用可视化编辑方式改文件（通过编辑补丁），不再用终端脚本直接改源码。这样 Copilot 对话框会显示“已更改 N 个文件”，并且每处修改都能看到“保留/撤销”

每个 terminal command 旁边都要写注释，说明命令、参数、选项的意义。
命令日志保存在本项目 tmp 目录，日志名不要出现 $.

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

- 本章已移动并整合到文末“## 10. 实验运行与构建整合章（原 3/10/11）”。
- 说明：构建/测试/批量实验前必须 Ask_User。

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

## 10. 实验运行与构建整合章（原 3/10/11）

### 10.1 运行前环境（必须遵守）

- 必须在项目 venv 中运行 Python 相关流程（推荐：`PATH="$PWD/.venv/bin:$PATH"`）。
	原因：系统 Python 启用 PEP 668 外部管理策略，`pip install --user` 会被拒绝，且易出现依赖版本漂移。
- `PATH` 与 `LD_LIBRARY_PATH` 作用不同：
	- `PATH` 决定“找哪个可执行文件”（如 python、bash）。
	- `LD_LIBRARY_PATH` 决定“运行时找哪些动态库 .so”（如 libcmaes/xgboost/lightgbm）。
- 必须保证以下 Python 依赖在 venv 可导入：`gymnasium`、`stable-baselines3`、`tensorboard`、`tqdm`、`rich`。
	原因：缺任一包会导致 AC 进程在启动或 callback 初始化阶段提前退出，C 端随后会误判为通信异常。
- 运行 cachesim 时必须确保动态库搜索路径包含 libcmaes/xgboost/lightgbm，建议：
	`LD_LIBRARY_PATH="/home/丁坤鹏/libcmaes/build/src:/usr/local/lib:${LD_LIBRARY_PATH:-}"`。
	原因：否则会出现 `libcmaes.so.0` / `libxgboost.so.3` / `lib_lightgbm.so` 加载失败。
- **每次切换配置或启动新实验必须使用干净 shell**，避免残留环境变量污染结果。
	推荐方式：`env -i HOME="$HOME" PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" LD_LIBRARY_PATH="/home/丁坤鹏/libcmaes/build/src:/usr/local/lib" <命令>`
	原因：LOH 有大量 `LOH_*` 环境变量（如 `LOH_ADAPTIVE_BUDGET_LOG`），若上一次 export 未 unset，会静默改变行为。
	已观察到的问题：`LOH_ADAPTIVE_BUDGET_LOG=1` 残留导致 ADAPTIVE 日志意外输出。
- 本机常用 trace 绝对路径（优先使用）：
	- `/mnt/serverpool/dingkp_trace/tencentBlock/v2/else/tencentBlock_1063.oracleGeneral.zst`
	- `/mnt/serverpool/dingkp_trace/wiki/wiki_2019t.oracleGeneral.zst`
	- `/mnt/serverpool/dingkp_trace/metaCDN/meta_reag.oracleGeneral.zst`

### 10.2 构建与产物约定

- Debug 构建（全量 clean）: `bash scripts/debug.sh -c`
- Debug 构建（增量 rebuild）: `bash scripts/debug.sh`
- Release 构建（全量 clean）: `bash scripts/debug.sh -r -c`
- Release 构建（增量 rebuild）: `bash scripts/debug.sh -r`
- 构建产物目录：`_build_dbg/`（Debug）、`_build_rel/`（Release）；历史兼容目录可能为 `_build/`。
- 默认构建模式使用 Release，并优先使用 `_build_rel/bin/cachesim`。

### 10.3 场景分流（CMA-ES 与 RL）

- 只验证 CMA-ES（C 侧优化）时：必须直接使用 `_build_rel/bin/cachesim`，不要使用 `scripts/test_loh_rl_sb3.sh`。
	原因：`test_loh_rl_sb3.sh` 是 Python+cache 双进程流程，会引入不必要的 RL 链路。
- 需要 RL 训练/推理或做 CMA-ES vs RL 对照时：使用 `scripts/test_loh_rl_sb3.sh`（或等价双进程流程）。

### 10.4 并行与长任务防护

- 并行运行 `scripts/test_loh_rl_sb3.sh` 时必须设置 `LOH_PARALLEL_SAFE=1`。
- 并行 case 必须显式设置不同 `RUN_TIMESTAMP`（或至少错开 1 秒以上启动）。
- 并行实验必须为每个 case 分配不同 `LOH_SHM_KEY`。
- 设置 `LOH_SKIP_BUILD=1` 前，必须确认目标构建产物已存在且与运行模式一致。
- 修改 `LOH_INCLUDE_*` / 共享内存结构，必须重新编译并做 C/Python 维度一致性核对。
- 实验任务统一后台运行，并把命令日志写入 `tmp/YYYYMMDD-<name>/logs/`。
- 启动后必须做“活性双检”：进程存在 + 日志文件持续增长。

### 10.5 示例命令（可直接复用）

- Release 增量编译：
	- `export LOH_BUILD_RELEASE=1`
	- `bash scripts/debug.sh -r`

- 以下参数/改动必须先重编译，不能直接“边跑边改”生效：
	- `LOH_INCLUDE_*`（会改变状态维度/共享内存布局）
	- `LOH_ENABLE_PENALTY` 及与 penalty 结构相关的编译期开关
	- `LOH_DEBUG_LEVEL`（编译期宏）
	- C/Python 共享内存结构字段、维度、顺序
	- 任何 `LOH.c` / 相关 C/C++ 源码改动

- CMA-ES-only 示例（不启 RL，最简命令）：
	- `export LD_LIBRARY_PATH="/home/丁坤鹏/libcmaes/build/src:/usr/local/lib:${LD_LIBRARY_PATH:-}"`
	- `export LOH_ENABLE_CMAES=1`
	- `export LOH_ENABLE_RL=0`
	- `_build_rel/bin/cachesim /mnt/serverpool/dingkp_trace/tencentBlock/v2/else/tencentBlock_1063.oracleGeneral.zst oracleGeneral LOH 0.1 --num-req=0`
	- 以下变量已是代码默认值，无需显式设置：
	  - `LOH_RANDOM_CANDIDATES=128`（随机候选数，代码默认 128；对应 MR+BMR 综合最优 r128_s16）
	  - `LOH_STRUCTURED_CANDIDATES=16`（结构化候选数，代码默认 16；对应 r128_s16）
	  - `LOH_MIN_CAND_PER_FEATURE=1`（每特征最低候选配额，代码默认 1；可 sweep 1/2/4）
	  - `LOH_CMAES_ALGO=aipop`（默认算法，代码默认 aIPOP_CMAES）
	  - `LOH_CMAES_ASYNC=1`（异步 CMA-ES 线程，默认开启）
	  - `LOH_BATCH_EVICT_SIZE=16`（批量驱逐，代码默认 16）
	  - `LOH_CMAES_FEEDBACK=weighted`（反馈模式，代码默认 mode=2=weighted）
	  - `LOH_FEATURE_LOG1P=1`（log1p 特征变换，代码默认 1）
	  - `LOH_SCORE_USE_COMPOUND=1`（复合评分，代码默认 1）
	  - `LOH_AUTO_COMPOUND=1`（自适应 compound 特征检测，代码默认 1=开启；warmup 后自动决定 freq_rec/freq_size/rec_size 开关）
	  - `LOH_SCORE_USE_IRT=0`（IRT 评分关闭，代码默认 0）
	  - `LOH_DEBUG_LEVEL=0`（无 debug 输出，代码默认 0）
	  - `LOH_PERF_PROFILING=0`（编译期宏，当前 release 已设为 0）

- RL 示例（Python + cachesim 双进程）：
	- `export PATH="$PWD/.venv/bin:$PATH"`
	- `export LD_LIBRARY_PATH="/home/丁坤鹏/libcmaes/build/src:/usr/local/lib:${LD_LIBRARY_PATH:-}"`
	- `export LOH_BUILD_RELEASE=1`
	- `export LOH_ENABLE_RL=1`
	- `export LOH_ENABLE_CMAES=0`
	- `export LOH_SKIP_BUILD=1`
	- `export LOH_SKIP_PIP_INSTALL=1`
	- `bash scripts/test_loh_rl_sb3.sh /mnt/serverpool/dingkp_trace/tencentBlock/v2/else/tencentBlock_1063.oracleGeneral.zst 0.1`
