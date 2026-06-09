# 20260506-belady-bsize-cache0001-from-20260504-plan

本目录用于在旧计划目录 `tmp/20260504-ablation-9cfg-cache001-r128-plan` 的 trace 顺序基础上，批量运行：

- Belady
- BeladySize

固定参数：

- cache_size=0.001
- 默认并行度=90
- trace 顺序：按旧 manifest 首次出现顺序去重后保留

## 产物

- `manifest.tsv`: 由运行脚本自动从旧 manifest 派生
- `logs/`: 每任务详细日志
- `results/`: 每任务结果尾行
- `command.log`: 命令与阶段日志
- `schedule.log`: 派发日志
- `success.log`: 成功日志
- `fail.log`: 失败日志
- `running_tasks.tsv`: 当前派发任务记录

## 用法

准备但不执行：

```bash
bash run_baseline_cache0001.sh --prepare
```

后台执行：

```bash
bash run_baseline_cache0001.sh --go --parallel 90
```