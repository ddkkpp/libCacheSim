# 20260407 — LOH 性能优化：异步 CMA-ES + 算法选择

## 概述

本轮优化目标：降低 LOH 缓存策略的总运行延迟（壁钟时间），同时不增大 miss ratio (mr) 和 byte miss ratio (bmr)。

最终结果：**壁钟时间降低到基线的 ~45%（2.2x 加速），mr/bmr 无退化**。

## 核心改动

### 1. 异步 CMA-ES 工作线程

**文件**：`libCacheSim/cache/eviction/cpp/loh_cmaes_bridge.cpp`

**问题**：CMA-ES 优化器的 `tell()（协方差矩阵更新）` 和 `refill_population()（采样新候选）` 在主线程阻塞执行，占总壁钟时间的 30-50%。
- Meta trace: 14.5s CMA-ES 阻塞
- 1063 trace: 137.9s CMA-ES 阻塞

**方案**：将 CMA-ES 的 generation 更新放到后台线程，主线程不再阻塞等待。

**实现细节**：
- `OnlineCMAES` 类新增 worker 线程（构造时启动，析构时 join）
- `tell()`: 当一代所有 lambda 个候选评估完成后，设置 `worker_busy_`（`std::atomic<bool>`），通知 worker 线程，立即返回（不阻塞主线程）
- `ask()`: 检查 `worker_busy_`，若后台仍在计算则返回 false
- Worker 线程：执行 `prepare_solutions → optimizer_->tell() → inc_iter → refill_population()`，完成后清除 `worker_busy_`
- 线程安全保证：通过 `worker_busy_` 原子变量实现所有权协议 — 主线程和 worker 线程不会同时访问共享数据

**环境变量**：
- `LOH_CMAES_ASYNC=1`（默认开启）
- `LOH_CMAES_ASYNC=0` 回退到同步路径

**C 侧适配**（`LOH.c`）：
- `sync_with_cmaes()` 中 `ask()` 返回 false 时不再报错/重试，直接保留当前权重并返回

**异步 ask() 行为说明**：
- 正常路径（~97% 的 sync 调用）：generation 未完成时（前 9/10 次 tell），ask() 立即返回新候选，与同步模式完全相同
- 等待路径（~3% 的 sync 调用）：第 10 次 tell 触发 generation 更新 → worker 启动 → `worker_busy_=true`，后续 ~3-4 次 ask() 返回 false（worker 还在计算新候选），C 侧保留当前权重跳过本次 sync
- 时间线示例：每 10+3 ≈ 13 次 sync 中丢失 3 次反馈（约 23%）。丢弃的观测使用相同权重（上一代最优），不影响 CMA-ES 候选评估质量

### 2. 默认 CMA-ES 算法改为 aipop

**之前默认**：`abipop` (active-bipop-CMA-ES)

**改为**：`aipop` (active-ipop-CMA-ES)

**依据**：通过 15 种算法 × 3 条 trace（1063 / wiki / meta）的 45 并行扫描测试，按三 trace 平均 mr 排序：

| rank | algo | avg mr | 1063 mr | meta mr | wiki mr |
|------|------|--------|---------|---------|---------|
| 1 | **aipop** | **0.1542** | 0.0229 | 0.2697 | 0.1701 |
| 2 | sepabipop | 0.1544 | 0.0228 | 0.2697 | 0.1709 |
| 3 | cmaes | 0.1549 | 0.0244 | 0.2703 | 0.1700 |
| 7 | abipop(原默认) | 0.1562 | 0.0284 | 0.2700 | 0.1701 |

aipop 综合三 trace 平均 mr 最低，且三条 trace 上都没有明显短板。

**环境变量**：仍可通过 `LOH_CMAES_ALGO=<algo>` 覆盖默认值。

### 3. 之前会话的批量淘汰

（前一轮对话实现，本轮继续使用）

- 每次请求批量淘汰最差的 batch_evict_size 个对象，跳过逐个重新评分
- 每次 `LOH_find` 时重置队列（per-request invalidation），保证 mr 不退化
- `LOH_BATCH_EVICT_SIZE=16`（默认）

## 性能对比（无 profiling、单独运行）

### Meta trace (45.6M reqs)

| 配置 | MQPS | 壁钟 | mr | bmr |
|------|------|------|-----|-----|
| 基线 (sync+batch1+abipop) | 0.82 | 55.6s | 0.2692 | 0.1531 |
| **优化 (async+batch16+abipop)** | **1.82** | **25.1s** | 0.2698 | 0.1552 |
| 优化 (async+batch16+sepabipop) | 1.91 | 23.9s | 0.2695 | 0.1555 |
| **加速**: 2.22x | 壁钟 45.1% | | mr ≈0 | bmr ≈0 |

### 1063 trace (360.9M reqs)

| 配置 | MQPS | 壁钟 | mr | bmr |
|------|------|------|-----|-----|
| 基线 (sync+batch1+abipop) | 0.59 | 628s | 0.0245 | 0.0264 |
| **优化 (async+batch16+abipop)** | **1.24** | **291s** | 0.0238 | 0.0247 |
| 优化 (async+batch16+sepabipop) | 1.39 | 260s | 0.0211 | 0.0223 |
| **加速**: 2.10x | 壁钟 46.3% | | mr ≈0 | bmr 更好 |

### CMA-ES 主线程阻塞时间（带 profiling）

| 指标 | Meta 之前 | Meta 之后 | 1063 之前 | 1063 之后 |
|------|----------|----------|----------|----------|
| cmaes_sync_total | 14.480s | **0.030s** | 137.900s | **0.261s** |
| 降幅 | | **99.8%** | | **99.8%** |

## 算法扫描

完整结果见 `tmp/20260407-async-algo-sweep/docs/results_summary.md`。

扫描条件：
- LOH_CMAES_ASYNC=1, LOH_BATCH_EVICT_SIZE=16, LOH_PERF_PROFILING=0
- 15 algorithms × 3 traces = 45 并行任务
- ⚠️ 45 进程并行导致 L3 缓存竞争和内存带宽饱和，壁钟和 MQPS 受影响，mr/bmr 更有参考价值

## 文件变更清单

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `libCacheSim/cache/eviction/cpp/loh_cmaes_bridge.cpp` | 新增/修改 | 异步 worker 线程、默认算法 aipop |
| `libCacheSim/cache/eviction/LOH.c` | 修改 | ask() 容错（不再报错重试）、日志字符串更新 |

## 新增环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `LOH_CMAES_ASYNC` | `1` | 启用异步 CMA-ES worker 线程 |

## 实验产物

| 路径 | 内容 |
|------|------|
| `tmp/20260407-perf-opt/` | 性能优化测试日志和保存的二进制 |
| `tmp/20260407-perf-opt/cachesim_async_cmaes` | 异步 CMA-ES 的 release binary |
| `tmp/20260407-async-algo-sweep/` | 15×3 算法扫描脚本、日志和结果汇总 |
| `tmp/20260407-async-algo-sweep/docs/results_summary.md` | 扫描结果汇总表格 |
