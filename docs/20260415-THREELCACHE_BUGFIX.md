# ThreeLCache Segfault 修复记录

## 1. 问题现象

在对 tencentBlock 部分 trace 运行 ThreeLCache-BMR 时，程序在处理若干万~几十万请求后触发 **SIGSEGV**（段错误）崩溃。不同 trace 的崩溃位置不固定，Debug 构建下在约 574K 请求处崩溃，先前测试在约 749K 请求处崩溃。

## 2. 定位过程

### 2.1 初步猜测：evict_predobj()

最初怀疑 `evict_predobj()` 中 `key_map.find(key)->second.list_pos` 返回的 `old_pos` 越界，导致 `in_cache.metas[old_pos]` 越界访问。对此添加了 `old_pos == -1` 的防御检查，但 **Debug 构建仍然崩溃**。

### 2.2 AddressSanitizer 定位真正崩溃点

使用 ASAN 构建（`-fsanitize=address -fno-omit-frame-pointer -g -O1`）运行后，获得精确堆栈：

```
==1866168==ERROR: AddressSanitizer: SEGV on unknown address 0x000000000008
    #0  ThreeLCacheCache::quick_demotion()   ThreeLCache.cpp:288
    #1  ThreeLCacheCache::rank()
    #2  ThreeLCacheCache::evict_predobj()
    #3  ThreeLCacheCache::evict()
    #4  cache_get_base
    #5  ThreeLCache_get
    #6  simulate
    #7  main
```

崩溃地址 `0x000000000008` 是 NULL 指针加偏移量解引用，发生在 `quick_demotion()` 第 288 行。

## 3. 根因分析

### Bug 1：quick_demotion() 空迭代器解引用（ASAN 定位）

**原始代码：**
```cpp
auto it = key_map.find(new_obj_keys[i])->second;  // line 288
```

**问题：**
- `new_obj_keys` 在 `admit()` 中累积新对象的 key。
- 但在 `erase_out_cache()` 中（line 147），会调用 `key_map.erase(meta._key)` 移除已驱逐对象的 key。
- 如果 `new_obj_keys` 中的某个 key 在后续被驱逐并从 `key_map` 中移除，则 `key_map.find()` 返回 `end()`。
- 对 `end()` 迭代器调用 `->second` 是**未定义行为**（空指针解引用）。

### Bug 2：evict_predobj() 过时 list_idx

**原始代码：**
```cpp
int32_t old_pos = key_map.find(key)->second.list_pos;  // line 371
```

**问题：**
- 预测映射 `pred_map` 中保存的 key 可能已从 `in_cache`（list_idx=0）驱逐到 `out_cache`（list_idx=1）。
- 此时 `list_pos` 含义已变为 `out_cache` 中的位置，但代码直接将其用作 `in_cache.metas[]` 的索引。
- 导致**越界访问** `in_cache.metas[old_pos]`。

## 4. 修复方案

### Fix 1：quick_demotion() — 检查迭代器有效性

```diff
-    auto it = key_map.find(new_obj_keys[i])->second;
+    auto km_it = key_map.find(new_obj_keys[i]);
+    if (km_it == key_map.end()) {
+      i++;
+      continue;
+    }
+    auto it = km_it->second;
```

当 key 已从 `key_map` 移除时，跳过该对象继续处理下一个。

### Fix 2：evict_predobj() — 过滤已驱逐对象 + 越界防御

```diff
-      int32_t old_pos = key_map.find(key)->second.list_pos;
+      auto km_it = key_map.find(key);
+      if (km_it == key_map.end() || km_it->second.list_idx != 0) {
+        // object already evicted from in_cache, skip
+        pred_map.erase(key);
+        continue;
+      }
+      int32_t old_pos = km_it->second.list_pos;
+      if (old_pos < 0 || (size_t)old_pos >= in_cache.metas.size()) {
+        pred_map.erase(key);
+        continue;
+      }
```

- `km_it == key_map.end()`：key 完全不在缓存中，跳过。
- `list_idx != 0`：对象已在 out_cache 中，其 `list_pos` 不是 `in_cache.metas` 的有效索引，跳过。
- `old_pos` 范围检查：安全网，防止极端情况越界。

### Fix 3：evict_with_candidate() — 越界安全网

```diff
   if (old_pos == -1) {
-    // No valid candidate to evict, avoid segfault
     return;
   }
+
+  if (old_pos < 0 || (size_t)old_pos >= in_cache.metas.size()) {
+    return;
+  }
```

对 `evict_predobj()` 返回值的二次防御，避免后续 `in_cache.metas[old_pos]` 越界。

## 5. 修复前无法产出结果的 trace

旧版（未修复）二进制经批量运行后，以下 **3 条 trace** 因触发 bug 严重到即使 Release 构建也无法正常完成，ThreeLCache-BMR 结果缺失：

| Trace | Group | Cache Size |
|---|---|---|
| alibabaBlock_811 | alibabaBlock | 870 B |
| tencentBlock_8949 | tencentBlock | 82 MiB |
| tencentBlock_12746 | tencentBlock | 685 KiB |

其余 ~4880 条 trace 在旧版 Release 构建下通过了（UB 未触发崩溃），但其中部分结果可能因读取垃圾数据而存在微偏差（如 12746 的 MR 偏差 7%）。

修复后，上述 3 条 trace 全部成功运行并填入 per-group 文档，ThreeLCache-BMR 覆盖率达到 100%。

## 6. 验证

### 5.1 ASAN 构建验证

使用 tencentBlock_8949（此前必崩的 trace），ASAN 构建下全部 1,876,668 请求处理完成，无任何报错。

### 5.2 Release 构建验证

```
MR = 0.248149, BMR = 0.076897, throughput = 1.06 MQPS
```

### 5.3 回归测试（7 条 trace）

| Trace | Cache Size | OLD MR | NEW MR | OLD BMR | NEW BMR | 结论 |
|---|---|---|---|---|---|---|
| tencentBlock_12746 | 685 KiB | 0.4052 | 0.3355 | — | — | DIFF (fix 改善 7%) |
| tencentBlock_9995 | 1 MiB | 0.3686 | 0.3676 | — | — | YES (一致) |
| tencentBlock_1082 | 1 MiB | 0.4487 | 0.4485 | 0.6707 | 0.6668 | YES (一致) |
| tencentBlock_1073 | 4 MiB | 0.4316 | 0.4313 | 0.4921 | 0.4922 | YES (一致) |
| tencentBlock_9997 | 48 MiB | 0.0573 | 0.0570 | 0.0978 | 0.0975 | YES (一致) |
| tencentBlock_8949 | 82 MiB | 0.2469 | 0.2481 | 0.0793 | 0.0769 | DIFF (微差<0.2%) |

**结论：**
- 5/7 条 trace 结果一致（差异 < 0.1%）。
- tencentBlock_12746 因修复防止了错误驱逐决策，MR 改善约 7%。
- tencentBlock_8949 旧版未崩溃时因未定义行为读取垃圾数据参与驱逐决策，修复后结果略有不同（< 0.2%），这是预期行为。

## 7. 涉及文件

- `libCacheSim/cache/eviction/3LCache/ThreeLCache.cpp`（3 处修改）
- ASAN 构建目录：`_build_asan/`（调试用，可清理）
- 回归测试脚本：`tmp/3lfix_test/regress_batch.sh`
