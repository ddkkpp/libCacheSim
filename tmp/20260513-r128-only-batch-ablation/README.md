# r128-only batch ablation 路径说明

本目录为 r128-only no-step batch size 对照实验。实验已按用户口令启动，并已迁移到 `nohup` detached 运行。2026-05-13 为追加进程 CPU time 与主线程 CPU time 打印，旧运行已停止并归档，Release 重新编译后已重启。

## 输入 manifest

- MR/OMR manifest: `tmp/20260510-drl-v7-omr-cache01-plan/manifest.tsv`
- BMR manifest: `tmp/20260506-drl-v7-bmr-cache01-plan/manifest.tsv`
- 读取规则: 只纳入 `trace_exists=1` 的行，复用 manifest 内的 `group/trace/cfg/trace_path/trace_type/cache_size/one_hit`。
- 随机种子: `FINAL_SEED=101`。
- 请求数: `FINAL_NUM_REQ=0`，即全量 trace。

## 两个 case

- `r128_no_step_batch16`: `LOH_RANDOM_CANDIDATES=128`，`LOH_BATCH_EVICT_SIZE=16`，所有 evict pool step 开关显式关闭。
- `r128_no_step_batch128`: `LOH_RANDOM_CANDIDATES=128`，`LOH_BATCH_EVICT_SIZE=128`，所有 evict pool step 开关显式关闭。

关键约束：两个 case 都显式设置 `LOH_EVICT_POOL_ENABLE=0`。`LOH.c` 在 pool 关闭时会在每次 `LOH_find()` 请求边界清空 `evict_queue`，因此无论 `LOH_BATCH_EVICT_SIZE` 是 16 还是 128，都只影响单个请求/同一次 eviction burst 内的 batch 队列，不会跨请求复用候选。

## 环境变量配置

外层启动脚本使用 `env -i`，只保留以下基础环境：

- `HOME=$HOME`
- `PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin`
- `LD_LIBRARY_PATH=/home/丁坤鹏/libcmaes/build/src:/usr/local/lib`
- `PYTHONUNBUFFERED=1`

每个 `cachesim` 子进程的公共环境如下：

- `CACHESIM_VERBOSE=0`
- `LOH_ENABLE_RL=0`
- `LOH_ENABLE_CMAES=1`
- `LOH_BUILD_RELEASE=1`
- `LOH_DEBUG_LEVEL=0`
- `LOH_PERF_PROFILING=0`
- `LOH_ENABLE_PROFILING=0`
- `LOH_AUTO_COMPOUND=0`
- `LOH_SCORE_USE_IRT=0`
- `LOH_SCORE_USE_COMPOUND=1`
- `LOH_INCLUDE_HIT_MISS_FEATURES=1` 记录在 command env 中，但这是编译期宏；当前 `_build_rel` 实际日志显示 `HIT_MISS=0`，因此本轮运行有效状态为未启用 hit/miss state 维度。
- `LOH_FEATURE_LOG1P=1`
- `LOH_MISS_RATIO_WEIGHT=1.0`
- `LOH_RANDOM_CANDIDATES=128`
- `LOH_STRUCTURED_CANDIDATES=16`
- `LOH_CMAES_DEGRADE_DETECT=0`
- `LOH_CMAES_FEEDBACK=weighted`
- `LOH_CMAES_ASYNC=1`
- `LOH_CMAES_ALGO=aipop`
- `LOH_PARALLEL_SAFE=1`
- `LOH_RNG_SEED=101`

所有 no-step / evict pool 相关环境显式关闭：

- `LOH_EVICT_POOL_ENABLE=0`
- `LOH_EVICT_POOL_REFILL=0`
- `LOH_EVICT_POOL_NEWOBJ=0`
- `LOH_EVICT_POOL_GUARD=0`
- `LOH_EVICT_POOL_HEALTH_LOG=0`
- `LOH_EVICT_POOL_EVENT_REBUILD=0`
- `LOH_EVICT_POOL_GUARD_REBUILD_ONLY=0`
- `LOH_EVICT_POOL_ADAPTIVE=0`
- `LOH_EVICT_POOL_SOURCE_ADAPTIVE=0`
- `LOH_EVICT_POOL_NEWOBJ_STAGING=0`
- `LOH_EVICT_POOL_WARMUP_ALLOWLIST=0`
- `LOH_EVICT_POOL_LOW_WATERMARK=0`

两个 case 只有 batch size 不同：

- `r128_no_step_batch16`: `LOH_BATCH_EVICT_SIZE=16`
- `r128_no_step_batch128`: `LOH_BATCH_EVICT_SIZE=128`

以下 feature 开关从 manifest 的 `cfg`/字段逐 case 带入，因此会随 trace/target 对应配置变化：

- `LOH_USE_FREQ_REC`
- `LOH_USE_FREQ_SIZE`
- `LOH_USE_REC_SIZE`
- `LOH_USE_SIZE`

每个子进程还设置 `RUN_TIMESTAMP=<case_id>`，用于并行安全与日志区分。实际下发的 `argv/env` 逐条记录在 `tmp/20260513-r128-only-batch-ablation/logs/r128_only_batch_ablation_command.log`。

注意：`LOH_INCLUDE_HIT_MISS_FEATURES` 这类 `LOH_INCLUDE_*` 是编译期宏，必须在构建 `_build_rel` 时通过 `scripts/debug.sh` 注入 `-DLOH_INCLUDE_HIT_MISS_FEATURES=1` 才会改变 `CONTEXT_DIM`。仅把它放进运行时 env 不会改变已编译二进制。本轮单 case 日志已出现 `Build-time dims: ... HIT_MISS=0 ... -> CONTEXT_DIM=2` 和 `Runtime state dims: HIT_MISS=0 ... -> ACTIVE=2/2`，说明当前实验没有启用 hit/miss state 维度。

## 启动入口

- Python runner: `tmp/20260513-r128-only-batch-ablation/run_r128_only_batch_ablation.py`
- 外层启动脚本: `tmp/20260513-r128-only-batch-ablation/run_r128_only_batch_ablation.sh`
- detached/nohup 启动脚本: `tmp/20260513-r128-only-batch-ablation/start_detached_nohup.sh`
- 外层脚本使用 `env -i` 干净环境，避免 shell 残留 `LOH_*` 变量污染实验。

## 当前后台方式与 VS Code 退出影响

- 当前启动方式: `nohup` detached 运行。
- 当前 nohup runner PID: `2242230`，记录在 `tmp/20260513-r128-only-batch-ablation/r128_only_batch_ablation_nohup.pid`。
- 迁移日志: `tmp/20260513-r128-only-batch-ablation/logs/migration_checks.log`。
- CPU time 重启记录: `tmp/20260513-r128-only-batch-ablation/logs/cpu_time_restart_record.log`。
- CPU time 重编译日志: `tmp/20260513-r128-only-batch-ablation/logs/cpu_time_rebuild_release.log`。
- CPU time smoke 日志: `tmp/20260513-r128-only-batch-ablation/logs/cpu_time_smoke.log`。
- CPU time 前旧口径部分结果归档: `tmp/20260513-r128-only-batch-ablation/archive_pre_cpu_time/20260513-112037/`。
- 主线程 CPU time 重启记录: `tmp/20260513-r128-only-batch-ablation/logs/main_thread_cpu_restart_record.log`。
- 主线程 CPU time 重编译日志: `tmp/20260513-r128-only-batch-ablation/logs/main_thread_cpu_rebuild_release.log`。
- 主线程 CPU time smoke 日志: `tmp/20260513-r128-only-batch-ablation/logs/main_thread_cpu_smoke.log`。
- 主线程 CPU time 前旧口径部分结果归档: `tmp/20260513-r128-only-batch-ablation/archive_pre_main_thread_cpu_time/20260513-113915/`。
- `nohup` 后 runner 的 PPID 为 1，不再依赖当前 VS Code 终端；关闭本地 VS Code 窗口或普通 SSH 断开不应直接终止实验。
- 仍需注意: 如果远端机器重启、用户会话/进程被管理员回收，或手动 kill 该 PID/进程组，实验仍会停止。
- detached 启动器 `tmp/20260513-r128-only-batch-ablation/start_detached_nohup.sh` 会先检查是否已有 `run_r128_only_batch_ablation.py` 在运行；若已有 runner，会拒绝重复启动，避免同一批任务双派发。

## 并行、重试、内存监控

- 并行数: `--parallel 80`。
- 重试次数: `--max-retries 1000000`，近似无限重试。
- 失败优先调度: 复用 `run_staged_cmaes.py::run_task_queue()`，失败任务重新入队时 priority=0，普通新任务 priority=1，因此 fail/retry 优先。
- dispatch 内存门控: `--dispatch-resume-gb 230`，内存使用达到 230GB 时暂停派发新任务。
- mem watchdog: `--mem-limit-gb 246 --mem-interval-s 20`，内存使用达到 246GB 时 kill 最新启动的 live cachesim。
- watchdog kill 策略: `run_staged_cmaes.py::MonitorState` 在 `active` 中记录每个 live cachesim 的启动时间、case_id 和进程；超过阈值时取启动时间最大的 live 进程执行 `proc.kill()`。它不会 kill Python runner，也不是按 RSS 最大进程选择目标。

## 启动后生成的计划文件

runner 会在真正 dispatch 前先写计划文件：

- `tmp/20260513-r128-only-batch-ablation/r128_only_batch_ablation_plan.tsv`
- `tmp/20260513-r128-only-batch-ablation/r128_only_batch_ablation_plan.json`

## 日志位置

- 外层 stdout/stderr: `tmp/20260513-r128-only-batch-ablation/logs/r128_only_batch_ablation_stdout.log`
- driver 日志: `tmp/20260513-r128-only-batch-ablation/logs/driver.log`
- 派发/完成/重试 schedule: `tmp/20260513-r128-only-batch-ablation/logs/r128_only_batch_ablation_schedule.log`
- 每个 case 的实际 argv/env 命令记录: `tmp/20260513-r128-only-batch-ablation/logs/r128_only_batch_ablation_command.log`
- 重试耗尽记录: `tmp/20260513-r128-only-batch-ablation/logs/r128_only_batch_ablation_fail.log`
- 内存 watchdog: `tmp/20260513-r128-only-batch-ablation/monitor/r128_only_batch_ablation_mem_watchdog.log`
- 单 case cachesim 日志: `tmp/20260513-r128-only-batch-ablation/logs/final_<target>_<case>/<case_id>.log`

## 结果行 runtime / MQPS 口径

- 单 case 日志中的最终结果行由 `libCacheSim/bin/cachesim/sim.c` 打印。
- `runtime` 计算方式: 通过 `gettime()` 记录开始和结束时间后相减，`gettime()` 在 `libCacheSim/utils/mysys.c` 中使用 `gettimeofday()`，因此这是 wall-clock elapsed time，不是 CPU time。
- 已新增 CPU time 打印: 重编译后的 cachesim 最终结果行会追加 `cpu time <sec> sec`，该值来自进程 CPU 时钟 `CLOCK_PROCESS_CPUTIME_ID`，若不可用则回退到 `clock()`；它表示该进程消耗的 CPU 时间，不等同于 wall-clock runtime。
- `cpu time` 可能大于 `runtime`: `CLOCK_PROCESS_CPUTIME_ID` 统计的是整个进程的累计 CPU 时间，会把该进程内所有线程相加。当前 LOH CMA-ES 默认 `LOH_CMAES_ASYNC=1`，`loh_cmaes_bridge.cpp` 会启动 async worker thread，因此主 trace replay 线程和 CMA-ES worker 并行用 CPU 时，进程 CPU time 可以超过 wall-clock runtime。`cpu time / runtime` 可理解为该进程在测量区间内的平均 core-equivalent 占用。
- 已新增主线程 CPU time 打印: 再追加 `main thread cpu time <sec> sec`，该值来自当前 replay 主线程的 `CLOCK_THREAD_CPUTIME_ID`；它不累计 CMA-ES async worker 线程，适合观察主 replay 线程自身消耗。
- `runtime` 与 `main thread cpu time` 可能看起来相等: 当前结果行按 `%.1lf` 只打印 1 位小数，细微差别会被四舍五入抹平。若主 replay 线程在测量区间内基本一直 CPU-bound、不明显等待 I/O/锁/睡眠，那么主线程 CPU time 本来也会非常接近 wall-clock runtime。若主线程发生明显阻塞或等待，则 `main thread cpu time` 会小于 `runtime`。
- 计时起点: 过 warmup 后首次进入正式统计请求时设置 `start_time`；本实验未额外传 warmup 参数，因此基本是全量正式运行口径，但 trace 中相对时间戳等于 0 的起始请求会落在代码的 warmup 分支。
- `MQPS` 计算方式: `req_cnt / 1000000.0 / runtime`，其中 `runtime` 就是上面的 wall-clock 时间。
- runner 结果 TSV 中的 `runtime_sec` 和 `mqps` 是从 cachesim 最终结果行解析出来的；schedule 日志里的 `elapsed` 是 Python runner 用 `time.time()` 包住子进程得到的 wall-clock 调度耗时，二者不是同一个字段。
- staged runner 已兼容解析新增的 `cpu_time_sec` 和 `main_thread_cpu_time_sec` 字段；旧日志没有对应字段时会记为 `NA`。
- 由于本实验并发 `80` 个 cachesim，单 case 的 `runtime/MQPS` 会受到同机 CPU、内存带宽、I/O 调度竞争影响，不是 CPU time 归一化吞吐。

## 结果位置

- 单 case TSV: `tmp/20260513-r128-only-batch-ablation/results/final_<target>_<case>/<case_id>.tsv`
- 分 case 汇总:
  - `tmp/20260513-r128-only-batch-ablation/final_mr_r128_no_step_batch16_results.tsv`
  - `tmp/20260513-r128-only-batch-ablation/final_bmr_r128_no_step_batch16_results.tsv`
  - `tmp/20260513-r128-only-batch-ablation/final_mr_r128_no_step_batch128_results.tsv`
  - `tmp/20260513-r128-only-batch-ablation/final_bmr_r128_no_step_batch128_results.tsv`
- 全量合并结果: `tmp/20260513-r128-only-batch-ablation/r128_only_batch_ablation_results.tsv`
- 简要均值汇总: `tmp/20260513-r128-only-batch-ablation/r128_only_batch_ablation_summary.tsv`
