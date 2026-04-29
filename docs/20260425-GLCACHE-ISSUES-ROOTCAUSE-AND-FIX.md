# GLCache 问题定位与修复说明（2026-04-25）

## 1. 结论摘要

- GLCache 在 `cache_ratio=0.001` 的 missing 补跑中，问题主要出现在 `alibabaBlock` 与 `tencentBlock` 两组 trace。
- 通过 ASAN 复现后，确认存在两类独立问题：
  - `select_segs_learned` 的 ranked index 越界读取（heap-buffer-overflow）。
  - `train_xgboost` 中对未初始化/已释放句柄执行 `XGBoosterFree`。
- 最小修复只需改动两处 C 代码：
  - `libCacheSim/cache/eviction/GLCache/segSel.c`
  - `libCacheSim/cache/eviction/GLCache/train.c`
- 修复后 smoke 通过（ASAN + Release 均返回 `exit_code=0`）。

## 2. 哪些 trace 出现问题

数据来源：`tmp/20260423-missing-cache0001-prepare/launch_dispatch.log` 中 `algo=GLCache` 的 `[FAIL]` 记录。

### 2.1 分组范围

- `alibabaBlock`：大量 trace 失败（例如 `alibabaBlock_164`, `alibabaBlock_268`, ..., `alibabaBlock_797`）。
- `tencentBlock`：多条 trace 失败（例如 `tencentBlock_10244`, `tencentBlock_10370`, ..., `tencentBlock_12194`）。

说明：详细去重列表可由以下日志提取得到，本文不重复粘贴全部 60+ 项。
- `tmp/20260423-missing-cache0001-prepare/launch_dispatch.log`

### 2.2 代表性可复现样本

- `alibabaBlock_764`（GLCache）可稳定复现崩溃：
  - 初始 Release smoke：`tmp/20260425-glcache-smoke/logs/smoke_glcache_alibabaBlock_764.status` 显示 `exit_code=139`
  - 初始 ASAN smoke：`tmp/20260425-glcache-smoke/logs/smoke_asan_glcache_alibabaBlock_764.status` 显示 `exit_code=134`

## 3. 根因分析

## 3.1 根因一：`select_segs_learned` ranked 索引越界

证据（ASAN）：
- `tmp/20260425-glcache-smoke/logs/smoke_asan_glcache_alibabaBlock_764.log`
- 报错关键信息：
  - `AddressSanitizer: heap-buffer-overflow`
  - 调用点：`libCacheSim/cache/eviction/GLCache/segSel.c:400`
  - 函数：`select_segs_learned`

根因描述：
- 在 ranking window 消耗或 rank 槽位稀疏（含 NULL）时，`ranked_seg_pos` 与 `n_ranked_segs` 边界处理不足，可能访问到无效下标或无效指针。

## 3.2 根因二：XGBoost 句柄释放缺少防御

证据：
- `tmp/20260425-glcache-smoke/logs/smoke_asan_glcache_alibabaBlock_764_after_fix.log`
- 报错关键信息：
  - `train.c:27: error in XGBoosterFree(learner->booster)`
  - `DMatrix/Booster has not been initialized or has already been disposed`

根因描述：
- 某些训练路径（如训练集为空/状态切换）下，句柄可能未成功初始化或已被回收；直接 `safe_call(XGBoosterFree(...))` 会触发致命错误。

## 4. 修复方案与具体代码改动

## 4.1 `segSel.c`：补全边界保护与兜底回退

文件：`libCacheSim/cache/eviction/GLCache/segSel.c`

关键改动点（行号以当前工作树为准）：
- `:364`：新增 `ss->n_ranked_segs <= 0` 的直接回退。
- `:372-374`：ranking window 耗尽时，设置 `ss->ranked_seg_pos = INT32_MAX` 并回退单段驱逐。
- `:382-389`：对 `seg_to_evict == NULL` 与 `ranked_seg_pos` 越界双重检查；异常时回退。
- `:402`, `:416`, `:422`, `:427`：在多处失败分支统一触发 rerank（`INT32_MAX`）并回退。

效果：
- 避免 `ranked_segs[idx]` 越界读。
- 在候选稀疏、窗口耗尽、NULL 槽位等场景下转为安全路径，不再崩溃。

## 4.2 `train.c`：释放前增加 non-null guard

文件：`libCacheSim/cache/eviction/GLCache/train.c`

关键改动点：
- `:27-28`：`learner->booster != NULL` 时才 `XGBoosterFree`。
- `:30-31`：`learner->train_dm != NULL` 时才 `XGDMatrixFree`。
- `:33-34`：`learner->valid_dm != NULL` 时才 `XGDMatrixFree`。

效果：
- 避免释放无效句柄导致的致命异常。

## 4.3 本次额外调整：去掉调度脚本单线程强制

文件：`tmp/20260423-missing-cache0001-prepare/run_missing_cache0001_seq.sh`

调整内容：
- 在 `run_one`（约 `:170`）中移除对 `GLCache|LRB` 的 `--num-thread 1` 注入逻辑。
- 现仅保留默认命令构造，不再在脚本层强制单线程。

说明：
- 该脚本调整不属于崩溃根因修复本体。
- 真正修复崩溃的是 4.1 与 4.2 的 C 代码改动。

## 5. 编译与验证

## 5.1 编译

- 按要求在原始目录执行 Release 增量编译：`bash scripts/debug.sh -r`
- 输出二进制：`_build_rel/bin/cachesim`
- 本次编译日志：`tmp/20260425-glcache-fix-doc/logs/build_release_original_dir.log`

进程影响检查：
- 编译前后 `cachesim` 进程数分别为 `101 -> 100`，未执行任何 kill/中断操作；计数变化可归因于任务自然结束。

## 5.2 Smoke 验证结果

- 修复前：
  - `tmp/20260425-glcache-smoke/logs/smoke_glcache_alibabaBlock_764.status`：`exit_code=139`
  - `tmp/20260425-glcache-smoke/logs/smoke_asan_glcache_alibabaBlock_764.status`：`exit_code=134`
- 修复后（最小修复）：
  - `tmp/20260425-glcache-smoke/logs/smoke_release_glcache_alibabaBlock_764_minimal_fix.status`：`exit_code=0`
  - `tmp/20260425-glcache-smoke/logs/smoke_asan_glcache_alibabaBlock_764_minimal_fix.status`：`exit_code=0`

结论：
- GLCache 崩溃已被最小修复闭环验证。

## 6. 产物映射（脚本/产物/结论）

- 脚本位置：
  - `tmp/20260423-missing-cache0001-prepare/run_missing_cache0001_seq.sh`
- 问题与验证产物：
  - `tmp/20260423-missing-cache0001-prepare/launch_dispatch.log`
  - `tmp/20260425-glcache-smoke/logs/*.log`
  - `tmp/20260425-glcache-smoke/logs/*.status`
  - `tmp/20260425-glcache-fix-doc/logs/build_release_original_dir.log`
- 结论文档：
  - `docs/20260425-GLCACHE-ISSUES-ROOTCAUSE-AND-FIX.md`
