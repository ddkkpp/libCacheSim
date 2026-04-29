# 20260418 LeCaR 补跑缺失项根因排查

## LeCaR 修改逻辑（代码开头说明同步）

为解决 LeCaR 在长 trace 场景下“看似卡住/极慢”的问题，当前代码采用以下策略：

1. 对 LFU 频次做上限截断（`LECAR_MAX_FREQ`，当前为 `4096`）。
2. `update_LFU_min_freq` 不再面对无限增长的 `max_freq`，避免热路径退化为超大跨度线性扫描。
3. 在高命中、长时运行场景中，优先保证吞吐稳定和可完成性，避免因频次爆炸导致实验补跑无法收敛。

该逻辑已写入 `libCacheSim/cache/eviction/LeCaR.c` 文件头，并作为 LeCaR 长跑稳定性修复的统一说明。

## 结论

`tmp/20260418-lecar-fill` 里的 9 个任务，不是同一种失败原因：

1. `202312_kv_traces_all` 是源 trace 路径问题。
2. `alibabaBlock_4` 是超大任务，旧批次里已经启动，但长时间只推进到早期进度，未在旧批次窗口内写出最终结果。
3. 其余 7 个任务在旧批次结果目录中没有落盘；其中 `cluster1` 与 6 个 tencentBlock 缺失项，在旧总日志中没有对应 trace 记录，更像是旧补跑流程没有真正完成到这些任务，而不是 LeCaR 对这些 trace 直接崩溃。
4. 当前补跑验证最容易误判的点是“只看日志不看进程状态”。同一 trace 可能在长时间运行阶段没有新日志行，但进程仍在计算；因此必须同时看进程活性和结果文件落盘。

## 证据

### 1. 缺失清单来源

9 个任务正好对应 4 月 15 日按算法统计出的 LeCaR 缺失项：

- alibabaBlock 缺 `alibabaBlock_4`：[docs/20260415-ablation-per-group/missing_baselines.md](docs/20260415-ablation-per-group/missing_baselines.md#L7)
- metaKV 缺 `202312_kv_traces_all`：[docs/20260415-ablation-per-group/missing_baselines.md](docs/20260415-ablation-per-group/missing_baselines.md#L23)
- tencentBlock 缺 6 项：[docs/20260415-ablation-per-group/missing_baselines.md](docs/20260415-ablation-per-group/missing_baselines.md#L31)
- twitter 缺 `cluster1`：[docs/20260415-ablation-per-group/missing_baselines.md](docs/20260415-ablation-per-group/missing_baselines.md#L71)

### 2. metaKV 不是算法问题，是 trace 文件缺失

任务生成日志明确记录：

- `WARN: 202312_kv_traces_all trace file not found in /mnt/serverpool/dingkp_trace/metaKV`：[tmp/20260415-baseline-fill/logs/gen_tasks_v2.log](tmp/20260415-baseline-fill/logs/gen_tasks_v2.log#L3)

这说明该项在 4 月 15 日就已经是输入文件缺失，而不是 LeCaR 运行失败。

### 3. alibabaBlock_4 是“已启动但极慢”

旧总日志中可以看到：

- 01:17:35 已启动 `alibabaBlock_4`：[tmp/20260415-baseline-fill/logs/all_tasks.log](tmp/20260415-baseline-fill/logs/all_tasks.log#L229)
- 到 05:44:07 仍只推进到 24 小时 trace-time 进度：[tmp/20260415-baseline-fill/logs/all_tasks.log](tmp/20260415-baseline-fill/logs/all_tasks.log#L465)

同时旧结果目录里没有对应输出文件，说明它不是“秒退失败”，而是旧批次结束前没有完成落盘。

### 4. 旧批次流程本身存在中断风险

旧版并行脚本使用 `xargs -P` 跑混合任务：[tmp/20260415-baseline-fill/run_parallel.sh](tmp/20260415-baseline-fill/run_parallel.sh)

同一批日志开头就出现：

- `do not support algorithm ThreeLCache-BMR`：[tmp/20260415-baseline-fill/logs/all_tasks.log](tmp/20260415-baseline-fill/logs/all_tasks.log#L2)
- `xargs: bash: terminated by signal 6`：[tmp/20260415-baseline-fill/logs/all_tasks.log](tmp/20260415-baseline-fill/logs/all_tasks.log#L5)

这说明旧补跑环境把“不支持算法的任务”和 LeCaR 任务混在一起跑，流程鲁棒性较差。即使部分 LeCaR 任务继续输出，也不能把“缺文件”直接归因为 LeCaR 本身不适配。

### 5. 当前直接单跑验证的关键教训

本次对 `tencentBlock_1468` 的排查表明：

- 日志会推进到多个 24 小时区间：[tmp/20260418-lecar-rootcause/logs/tencentBlock_1468.run.log](tmp/20260418-lecar-rootcause/logs/tencentBlock_1468.run.log#L1)
- 但如果重复启动同一任务（包括带 strace 的诊断命令），会形成多进程并发，容易造成“看起来没结束、也没结果文件”的假象。

因此本次补跑策略上应坚持两点：

1. LeCaR 在该 trace 上不是“启动即失败”
2. 补跑判断必须同时结合：进程活性、日志增长、结果文件落盘

## 本次修正

已更新两个补跑脚本，使其在运行前就能区分“trace 不存在”和“运行失败”：

- Bash 版本：[tmp/20260418-lecar-fill/run.sh](tmp/20260418-lecar-fill/run.sh)
- Python 版本：[tmp/20260418-lecar-fill/run_py.py](tmp/20260418-lecar-fill/run_py.py)

新增行为：

1. 运行前检查 trace 是否存在，缺失时直接标记 `missing-trace`
2. 为每个任务标记规模等级：`fast`、`medium`、`large`、`xlarge`
3. Bash 版本在命令退出 0 但没有 `.cachesim` 结果时标记 `no-output`
4. Bash 版本输出分片状态表到 `logs/status_shard_<index>_of_<count>.tsv`
5. Bash 版本支持用 `LECAR_TASK_FILTER` 只跑指定任务子集

## 建议

1. 先单独补跑 6 个 tencentBlock 快任务，确认结果可稳定落盘。
2. `cluster1` 单独后台跑，不和 `alibabaBlock_4`、`202312_kv_traces_all` 混跑。
3. `alibabaBlock_4` 单独后台长跑，并单独观察日志增长。
4. `202312_kv_traces_all` 先确认真实 trace 路径，再决定是否启动。
