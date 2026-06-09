# cache=0.001 missing 补跑准备

- 本目录用途：仅准备并承载补跑计划与日志。
- 分组顺序：metaKV -> alibabaBlock -> tencentBlock。
- 输入清单：`missing_selected.tsv`。
- 启动脚本：`run_missing_cache0001_seq.sh`。

## 启动方式

1. 预览（不执行）：

   bash tmp/20260423-missing-cache0001-prepare/run_missing_cache0001_seq.sh

2. 真正执行（收到口令后再运行）：

   bash tmp/20260423-missing-cache0001-prepare/run_missing_cache0001_seq.sh --go --parallel 40

## 执行策略

- 分组顺序固定：metaKV -> alibabaBlock -> tencentBlock。
- 组内并行：由 `--parallel N` 控制（例如 40）。
- 任务选择：每个 trace 只跑 `missing_union` 中对应缺失算法，不跑非缺失算法。

## 产物位置

- 计划文件：`launch_plan.txt`
- 运行摘要：`launch_summary.txt`
- 单任务日志：`logs/*.log`

## 说明

- 环境使用干净 shell 方式执行（`env -i`），减少残留环境变量污染。
- `trace path` 从 `tmp/20260422-autocompound-cache0001-ready/mr/logs/*.log` 自动解析。
- 运行命令固定使用 `_build_rel/bin/cachesim` 与 cache ratio `0.001`。
