# 4 阶段 Sweep 实验

## 目录结构
```
tmp/20260410-full-sweep/
├── common.sh          # 公共函数
├── tracelist.txt      # 114 个 traces (<=10GB)
├── analyze.sh         # 通用结果分析脚本
├── run_phase1.sh      # Phase 1: AC=0 vs AC=1
├── run_phase2.sh      # Phase 2: 7×7 r×s sweep
├── run_phase3.sh      # Phase 3: MCP=1,2,4
├── run_phase4.sh      # Phase 4: MRW=0~1 (步长0.2)
└── phase{1,2,3,4}/    # 各阶段结果
    ├── logs/          # 每个实验的完整日志
    └── results.csv    # 汇总结果
```

## 实验规模
| 阶段 | 配置数 | trace数 | 总实验 |
|------|--------|---------|--------|
| 1    | 2      | 114     | 228    |
| 2    | 49     | 114     | 5586   |
| 3    | 3      | 114     | 342    |
| 4    | 6      | 114     | 684    |

## 运行方式（每个阶段后台运行）

### Phase 1
```bash
cd /home/丁坤鹏/libcachesim_new
nohup bash tmp/20260410-full-sweep/run_phase1.sh > tmp/20260410-full-sweep/phase1_run.log 2>&1 &
```

### 分析 Phase 1 结果
```bash
bash tmp/20260410-full-sweep/analyze.sh tmp/20260410-full-sweep/phase1/results.csv "auto_compound"
```

### Phase 2（确认 AC=1 胜出后）
```bash
nohup bash tmp/20260410-full-sweep/run_phase2.sh > tmp/20260410-full-sweep/phase2_run.log 2>&1 &
```

### 分析 Phase 2 结果
```bash
bash tmp/20260410-full-sweep/analyze.sh tmp/20260410-full-sweep/phase2/results.csv "rand_cand,struct_cand"
```

### Phase 3（带入 Phase 2 最优 r,s）
```bash
# 替换 BEST_R 和 BEST_S 为 Phase 2 的最优值
nohup bash tmp/20260410-full-sweep/run_phase3.sh BEST_R BEST_S > tmp/20260410-full-sweep/phase3_run.log 2>&1 &
```

### 分析 Phase 3 结果
```bash
bash tmp/20260410-full-sweep/analyze.sh tmp/20260410-full-sweep/phase3/results.csv "min_cand_per_feature"
```

### Phase 4（带入最优 r,s,mcp）
```bash
nohup bash tmp/20260410-full-sweep/run_phase4.sh BEST_R BEST_S BEST_MCP > tmp/20260410-full-sweep/phase4_run.log 2>&1 &
```

### 分析 Phase 4 结果
```bash
bash tmp/20260410-full-sweep/analyze.sh tmp/20260410-full-sweep/phase4/results.csv "miss_ratio_weight"
```

## 最优配置判定标准
1. 最佳平均 MR + BMR
2. 若两配置 avg_mr 差距 <1%，优先选在某些 trace 表现差时相差最优不太大的（即 max_gap 更小）

## 注意事项
- 在干净 shell 中运行（env -i）避免环境变量残留
- 80 并行度，112 核 CPU
- 不足 80 的实验补齐到 80 并行自动处理
- Phase 2-4 依赖前一阶段结果，需手动分析后触发
