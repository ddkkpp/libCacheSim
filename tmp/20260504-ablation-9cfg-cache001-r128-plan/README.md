# 20260504-ablation-9cfg-cache001-r128-plan

本目录仿照 `tmp/20260430-ablation-9cfg-cache001-plan` 新建。

唯一实验变量改动：
- `LOH_RANDOM_CANDIDATES=128`

其余保持与原 9cfg/cache=0.01 方案一致（trace 集、cfg 集、cache_size、并行调度框架）。

## 关键约束（修正旧方案踩坑）

- 不提供“只重试 fail 子任务”的独立入口脚本。
- 调度采用“fail 优先 + 全量主循环”：启动时先做 fail 优先轮次，且主循环中每轮派发前也会执行 fail 优先轮次；不是 only-fail。
- 断点恢复以 `results/*.txt` 是否存在为准。
- 若需重跑，使用同一个主脚本重新调度，不做中途 fail-only 选择性重试。
- 内存看门狗超限时优先杀最新启动的 `cachesim`（而非最老）。
- 派发新任务有恢复阈值：只有当内存用量低于 230GB 时才会继续派发。

## 使用方式

1. 生成计划（只生成，不运行）

```bash
python3 generate_plan.py
```

2. 启动前检查（只检查，不运行）

```bash
bash run_9cfg_cache001.sh --prepare
```

3. 真正启动（需口令后执行）

```bash
bash run_9cfg_cache001.sh --go --parallel 80
```
