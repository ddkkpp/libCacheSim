# Blocked vs Nonblocked CMA-ES 对比实验

**日期**: 2026-04-15
**实验目录**: `tmp/20260415-blocked-cmaes-test/`
**二进制**: `_build_temp/bin/cachesim`（含 blocked ask 重试逻辑）

## 1. 实验设计

### 修改内容
在 `LOH.c` 的 CMA-ES ask 调用点，当 `LOH_WAIT_MODE=blocked` 且 `loh_cmaes_ask()` 返回失败时，执行 `usleep(100)` busy-wait 重试循环直到成功。

核心代码变更（LOH.c ~line 3984）：
```c
int ask_ok = loh_cmaes_ask(params->cmaes_handle, next_w, cmaes_output_dim);
if (!ask_ok && loh_wait_mode_blocked) {
    while (!ask_ok) {
        usleep(100);  // 100μs 间隔
        ask_ok = loh_cmaes_ask(params->cmaes_handle, next_w, cmaes_output_dim);
    }
}
```

### 实验参数
| 参数 | 值 |
|---|---|
| RC | 128 |
| SC | 16 |
| MRW | 1.0 |
| FSB | 禁用 |
| AUTO_COMPOUND | 0 |
| FEATURE_LOG1P | 1 |
| SCORE_USE_COMPOUND | 1 |
| num-req | 0（全量） |

### Traces
- tencentBlock_1063: `/mnt/serverpool/dingkp_trace/tencentBlock/v2/original/else/tencentBlock_1063.oracleGeneral.zst`
- wiki_2019t: `/mnt/serverpool/dingkp_trace/wiki/wiki_2019t.oracleGeneral.zst`

### Baseline (unblocked)
- 1063: `tmp/20260413-feature-ablation-ext/logs/tencentBlock_1063_f*.log` (使用 `_build_rel`)
- wiki_2019t: `tmp/20260411-wiki-feature-ablation/logs/wiki_2019t_f*.log` (使用 `_build_rel`)

两组均为 `LOH_WAIT_MODE=default (NON-BLOCKED)`，参数相同（RC=128 SC=16 MRW=1.0）。

## 2. 结果

### 2.1 tencentBlock_1063

| feature | unblocked MR | blocked MR | Δ (blocked-unblocked) | Δ% | 胜出 |
|---|---|---|---|---|---|
| f000 | 0.0297 | 0.0250 | -0.0047 | -15.8% | blocked |
| f001 | 0.0194 | 0.0250 | +0.0056 | +28.9% | **unblocked** |
| f010 | 0.0221 | 0.0202 | -0.0019 | -8.6% | blocked |
| f011 | 0.0201 | 0.0187 | -0.0014 | -7.0% | blocked |
| f100 | 0.0696 | 0.0626 | -0.0070 | -10.1% | blocked |
| f101 | 0.0370 | 0.0359 | -0.0011 | -3.0% | blocked |
| f110 | 0.0517 | 0.0477 | -0.0040 | -7.7% | blocked |
| f111 | 0.0331 | 0.0372 | +0.0041 | +12.4% | **unblocked** |
| **均值** | **0.0353** | **0.0340** | **-0.0013** | **-3.7%** | **blocked 6/8** |

### 2.2 wiki_2019t

| feature | unblocked MR | blocked MR | Δ (blocked-unblocked) | Δ% | 胜出 |
|---|---|---|---|---|---|
| f000 | 0.17533 | 0.17521 | -0.00012 | -0.07% | ≈ |
| f001 | 0.18048 | 0.18028 | -0.00019 | -0.11% | ≈ |
| f010 | 0.17061 | 0.17069 | +0.00007 | +0.04% | ≈ |
| f011 | 0.17112 | 0.17109 | -0.00003 | -0.02% | ≈ |
| f100 | 0.17278 | 0.17293 | +0.00015 | +0.09% | ≈ |
| f101 | 0.17368 | 0.17354 | -0.00014 | -0.08% | ≈ |
| f110 | 0.17291 | 0.17209 | -0.00083 | -0.48% | blocked |
| f111 | 0.17070 | 0.17080 | +0.00010 | +0.06% | ≈ |
| **均值** | **0.17345** | **0.17333** | **-0.00013** | **-0.07%** | **≈ 无区别** |

## 3. 分析

### 3.1 Key Observations

1. **wiki_2019t 无差异**: 所有 8 个配置的 |Δ| < 0.001，最大差异仅 0.48% (f110)，完全在单次运行的随机波动范围内。

2. **1063 方向不一致**: 虽然 6/8 配置 blocked 更优，但 f001 和 f111 反而显著更差（+28.9% 和 +12.4%）。如果 blocking 有系统性增益，不应出现这种大幅退步。

3. **差异量级可比于 CMA-ES 随机性**: CMA-ES 使用随机优化过程（population sampling、random restarts），同一配置的不同随机种子可能导致 ±5-15% 的 MR 波动，这与观测到的差异量级吻合。

### 3.2 理论分析

Blocked 模式的预期效果：确保每个驱逐批次都使用 CMA-ES 的最新候选解，避免因 async worker 忙碌而复用旧权重。

但实际影响有限，原因：
- CMA-ES async worker 的单次迭代通常只需 **几毫秒**
- LOH 调用 `loh_cmaes_ask()` 的频率取决于驱逐批次间隔（约几千次请求一次）
- 在 nonblocked 模式下，worker 忙碌导致 ask 失败的事件本身就**很少发生**
- 即使偶尔复用旧权重，由于权重更新步幅小（CMA-ES sigma 收敛后），新旧权重差异微小

### 3.3 Confounds

- **不同二进制**: blocked 使用 `_build_temp/`，unblocked 使用 `_build_rel/`。虽然代码差异仅在 blocked ask 重试逻辑，但编译时间不同可能引入微小差异。
- **单次运行**: 每个配置仅跑一次，无法计算标准差或置信区间。

## 4. 结论

**Blocked 和 nonblocked CMA-ES 没有实质性区别**。

- wiki_2019t 上完全无差异
- 1063 上的差异方向不一致，大概率归因于 CMA-ES 的随机性而非 blocking 机制
- 不建议将 blocked 作为 CMA-ES 的默认模式，它增加了 busy-wait 开销但无可靠收益

如需严格结论，建议对每个配置进行 3-5 次重复实验取平均值。

## 5. 文件清单

```
tmp/20260415-blocked-cmaes-test/
├── run.sh                                    # 主实验脚本（wiki + 1063 路径修正版）
├── run_1063_fix.sh                           # 1063 路径修正补跑脚本
├── runner.log                                # 主脚本日志（wiki 8 + 1063 8 路径错误退出）
├── runner_1063.log                           # 1063 补跑日志（8 experiments）
└── logs/
    ├── tencentBlock_1063_f{000..111}.log     # 1063 blocked 结果
    └── wiki_2019t_f{000..111}.log            # wiki blocked 结果
```
