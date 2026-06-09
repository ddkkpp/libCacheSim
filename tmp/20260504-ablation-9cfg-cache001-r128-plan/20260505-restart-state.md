# 20260505 Restart State

## Summary

- existing_results: 5467
- active_running_tasks: 9
- stalled_reason: VS Code/PTTY 断开后，旧脚本中的 `tee -a command.log` 卡住，令牌未归还，launcher 阻塞在 `pipe_read`
- restart_policy: 重启时同时跳过 `results/*.txt` 已完成任务与 `running_tasks.tsv` 中仍在运行任务

## Existing Results

- 结果目录: `tmp/20260504-ablation-9cfg-cache001-r128-plan/results`
- 当前已有结果文件数: 5467
- 示例:
  - `alibabaBlock__alibabaBlock_0__f100_ns.txt`
  - `alibabaBlock__alibabaBlock_0__f000_orig.txt`
  - `alibabaBlock__alibabaBlock_0__f001_orig.txt`
  - `alibabaBlock__alibabaBlock_0__f010_orig.txt`
  - `alibabaBlock__alibabaBlock_0__f011_orig.txt`

## Running Tasks Preserved Across Restart

以下 9 个任务在当前检查时仍在运行，不应在重启后重复派发：

- `alibabaBlock__alibabaBlock_10__f100_ns`
- `alibabaBlock__alibabaBlock_10__f000_orig`
- `alibabaBlock__alibabaBlock_10__f001_orig`
- `alibabaBlock__alibabaBlock_10__f010_orig`
- `alibabaBlock__alibabaBlock_10__f011_orig`
- `alibabaBlock__alibabaBlock_10__f100_orig`
- `alibabaBlock__alibabaBlock_10__f101_orig`
- `alibabaBlock__alibabaBlock_10__f110_orig`
- `alibabaBlock__alibabaBlock_10__f111_orig`

## Current-Dir Processes To Clean

可清理但不应影响其他目录的对象：

- 当前目录旧 launcher: `209792`
- 当前目录 watchdog: `209798`
- 当前目录孤儿 watchdog: `129971`, `182495`
- 当前目录下无 `cachesim` 子进程、只剩 `tee -a command.log` 的 wrapper 子进程

保留对象：

- 上述 9 个 `alibabaBlock_10` 对应的 wrapper + cachesim 进程
