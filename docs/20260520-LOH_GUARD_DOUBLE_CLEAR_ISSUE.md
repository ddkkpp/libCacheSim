# LOH Guard 双重清空问题备忘

日期：2026-05-20

## 问题描述

Guard shadow audit 在 bad_rate ≥ threshold 时会触发**两次** `loh_evict_queue_clear`：

### 第一次 clear（快路径，无条件）

```c
// LOH.c 快路径，每 256 次 pool pop 触发一次 guard audit
if (loh_evict_pool_guard_should_audit(params)) {
    guard_shadow_audit = 1;
    guard_queued_obj_id = params->evict_queue_obj_id[pos];
    guard_queued_score  = params->evict_queue_score[pos];
    guard_queued_source = params->evict_queue_source[pos];
    loh_evict_queue_clear(params);   // ← 第一次：清空旧 buffer
    break;                            // 跳出快路径 → fresh scoring
}
```

此时必然走完整 fresh scoring（272 个候选），选出新 victim，并填入新的 3 个候选到 buffer。

### 第二次 clear（guard_record，条件触发）

```c
// loh_evict_pool_guard_record 内
if (bad_rate >= loh_evict_pool_guard_bad_rate) {   // bad_rate ≥ 0.25
    if (loh_evict_pool_guard_rebuild_only || loh_evict_pool_event_rebuild) {
        params->evict_pool_event_rebuilds++;
        loh_evict_queue_clear(params);   // ← 第二次：清空刚刚 fresh scoring 填好的新 buffer
        params->evict_pool_guard_audits = 0;
        params->evict_pool_guard_bad = 0;
        return;
    }
}
```

此时刚刚由 fresh scoring 填好的 3 个候选（第 2/3/4 低分）被立即清掉，下次驱逐又要做一次 fresh scoring。

## 问题分析

**第二次 clear 的逻辑存疑**：

- fresh scoring 刚用全量 272 个候选重新打分，建好的 buffer 是最新状态
- 理论上这个 fresh buffer 质量最高，没有理由立即清掉
- 第二次 clear 只是保守地"强制下次驱逐也做 fresh scoring"
- 实际效果：bad_rate 高时，连续两次驱逐都走 fresh scoring，之后才恢复快路径

**可能的改进方向**：

1. **去掉第二次 clear**：bad_rate 高时只重置计数器窗口，不清刚建好的 fresh buffer。这样 guard audit 后的那个 fresh buffer 可以正常被复用。
2. **降低 guard interval**：如果 bad_rate 持续高，可以缩短 256 pop 的间隔（但代码目前固定 256，不动态调整）。
3. **保持现状**：第二次 clear 是一种额外的保守机制，在 bad_rate 高的阶段强制更频繁的 fresh scoring。成本是多了一次不必要的 fresh scoring。
4. **全量排序 + 部分 guard 采样**：fresh scoring 时对所有 ~272 个候选全排序，将全部候选存入 buffer（batch 等于候选总数），guard 不做全量 fresh scoring 而只是对 buffer 中随机采样的若干候选重新评分，与 buffer 头比较。这样 buffer 可以跨更多次驱逐复用，guard 开销更低，且 buffer 耗尽前无需重建。代价是 buffer 内存占用增大（需要存 ~272 个候选而非 3 个），且全排序的一次性成本更高（O(N log N) 而非当前的 O(K×N)，K=3）。

## 相关参数

| 参数 | 默认值 | 含义 |
|---|---|---|
| `LOH_EVICT_POOL_GUARD_INTERVAL` | 256 | 每隔多少次 pool pop 触发一次 audit |
| `LOH_EVICT_POOL_GUARD_MIN_SAMPLES` | 8 | 至少多少次 audit 后才比较 bad_rate |
| `LOH_EVICT_POOL_GUARD_BAD_RATE` | 0.25 | 触发第二次 clear 的 bad_rate 阈值 |
| `LOH_EVICT_POOL_GUARD_REL_EPS` | 0.01 | 相对容差（fresh_score 需低于 queued_score 的比例） |

## 代码位置

- 第一次 clear：`LOH_to_evict` 快路径，约第 9692 行
- 第二次 clear：`loh_evict_pool_guard_record`，约第 1583 行
- Guard interval 判断：`loh_evict_pool_guard_should_audit`，约第 1541 行

## 论文影响

论文中 guard 机制描述（Score-reuse eviction 第三段末尾）写的是：

> "at fixed intervals, the decision layer performs a full candidate collection and scoring—the same procedure as a regular eviction—and compares the resulting best candidate with the current buffer head. When such comparisons more frequently find that the fresh result is a better eviction target than the buffer head, the buffer is cleared before eviction quality visibly degrades."

该描述隐含"clearing 是 bad_rate 高才发生"，但实际上：
- **每次 guard audit 都会 clear + fresh scoring**（无条件）
- bad_rate 高时额外再清一次刚建好的 fresh buffer（第二次 clear）

论文描述在高层上不完全准确，但属于实现细节的抽象简化，暂不修改。若未来改代码去掉第二次 clear，则论文描述反而会更准确。
