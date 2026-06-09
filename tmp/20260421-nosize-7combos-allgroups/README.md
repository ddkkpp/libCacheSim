# 20260421 nosize 7-combo all-groups

## 目标

- 仿照 `tmp/20260420-nosize-allgroups`
- 固定 `LOH_USE_SIZE=0`
- sweep 剩余 7 个特征组合：`f000 f001 f010 f011 f101 f110 f111`
- 排除 `twitter` 和 `tencentphoto`
- group 顺序固定为：`metakv wiki metacdn alibaba tencentblock cloudphysics`
- 每个组合内按上述顺序把全部 trace 启动完，再进入下一个组合
- 最大并行数 `60`

## 固定配置

- `cache_size=0.1`
- `LOH_ENABLE_CMAES=1`
- `LOH_ENABLE_RL=0`
- `LOH_AUTO_COMPOUND=0`
- `LOH_SCORE_USE_COMPOUND=1`
- `LOH_SCORE_USE_IRT=0`
- `LOH_FEATURE_LOG1P=1`
- `LOH_MISS_RATIO_WEIGHT=1.0`
- `LOH_RANDOM_CANDIDATES=256`
- `LOH_STRUCTURED_CANDIDATES=16`

## 目录

- `run.sh`: 主批量脚本，当前仅已生成，尚未启动
- `mem_watchdog.sh`: 内存看门狗，只匹配本批次 `results/` 路径对应的 `cachesim` 进程
- `logs/`: 运行日志，按组合分子目录
- `results/`: `cachesim --output` 结果，按组合分子目录
- `summary.csv`: 任务完成后汇总为 `combo,group,trace,miss_ratio,byte_miss_ratio`
- `requeue.txt`: 如 watchdog 杀进程，会记录被中断任务

## 启动方式

- 主任务：`bash tmp/20260421-nosize-7combos-allgroups/run.sh > tmp/20260421-nosize-7combos-allgroups/run.log 2>&1 &`
- 看门狗：`bash tmp/20260421-nosize-7combos-allgroups/mem_watchdog.sh > tmp/20260421-nosize-7combos-allgroups/watchdog.log 2>&1 &`

当前状态：脚本已准备，按你的要求等待启动口令。
