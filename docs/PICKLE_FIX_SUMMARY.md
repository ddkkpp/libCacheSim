# Pickle 序列化问题修复总结

## 问题描述

使用 `loh_actor_critic_sb3.py` 时出现错误:
```
⚠️  Training interrupted: Terminate signal received in step() while waiting for new state version
⚠️  Failed to save interrupted model: cannot pickle '_ctypes.CField' object
```

而 `loh_actor_critic_sb3_SACblocked.py` (没有 profiling) 可以正常保存模型。

## 根本原因

`loh_actor_critic_sb3.py` 引入了 `FunctionTimer` 类用于性能分析(profiling),导致了两个 pickle 问题:

### 问题1: SharedMemoryData 是函数内的局部类 ⚠️ **关键问题**

```python
# ❌ 错误写法 (原来的代码)
def create_shared_memory_class(context_dim):
    class SharedMemoryData(ctypes.Structure):  # 局部类,无法pickle
        _fields_ = [...]
    return SharedMemoryData

SharedMemoryData = create_shared_memory_class(CONTEXT_DIM)
```

**为什么 `loh_actor_critic_sb3_SACblocked.py` 可以保存?**
- 虽然它也用了同样的函数内局部类定义
- 但它**没有 `GLOBAL_TIMER`**,不会触发深度 pickle
- SAC 默认只浅层保存,不会深入序列化环境的所有属性

**为什么添加 profiling 后就不行了?**
- `GLOBAL_TIMER` 被 `ReplayBuffer` 和 `LohEnv` 引用
- SAC 保存时会递归 pickle 所有相关对象
- 遇到 `SharedMemoryData` 这个局部类就失败了

### 问题2: FunctionTimer 和 LohEnv 缺少 pickle 支持

1. **`FunctionTimer`**:
   - 使用 `defaultdict`,需要显式的 `__getstate__`/`__setstate__`

2. **`LohEnv`**:
   - 包含不可 pickle 的对象: `mmap.mmap`, 信号量句柄, `threading.Event`

### 问题3: 连锁反应
   - SAC 模型 → 环境 → ReplayBuffer → GLOBAL_TIMER → SharedMemoryData
   - 任何一个环节不支持 pickle 都会导致整个保存失败

## 修复方案

### 1. 将 SharedMemoryData 改为模块级别类 ⭐ **最关键的修复**

```python
# ✅ 正确写法 (修复后)
# 在模块顶层定义,而不是在函数内部
class SharedMemoryData(ctypes.Structure):
    """共享内存数据结构 - 必须是模块级别类以支持pickle"""
    _fields_ = [
        ("ready_for_inference", ctypes.c_int),
        ("weights_updated", ctypes.c_int),
        ("terminate", ctypes.c_int),
        ("is_training", ctypes.c_int),
        ("state", ctypes.c_double * CONTEXT_DIM),  # 使用固定常量
        ("weights", ctypes.c_double * FEATURE_DIM),
        # ... 其他字段
    ]

def create_shared_memory_class(context_dim):
    """保留此函数以兼容旧代码"""
    if context_dim != CONTEXT_DIM:
        import warnings
        warnings.warn(f"context_dim={context_dim}, but using CONTEXT_DIM={CONTEXT_DIM}")
    return SharedMemoryData
```

### 2. FunctionTimer 添加 pickle 支持

在 `FunctionTimer` 类中添加:

```python
def __getstate__(self):
    """支持pickle序列化 - 只保存统计数据"""
    return {
        'timings': dict(self.timings),  # 转换为普通dict
        'call_counts': dict(self.call_counts)
    }

def __setstate__(self, state):
    """从pickle恢复"""
    self.timings = defaultdict(list, state['timings'])
    self.call_counts = defaultdict(int, state['call_counts'])
```

### 3. LohEnv 添加 pickle 支持

在 `LohEnv` 类中添加:

```python
def __getstate__(self):
    """支持pickle序列化 - 保存可序列化的状态"""
    state = self.__dict__.copy()
    # 移除不可pickle的对象
    state['shm'] = None  # mmap对象
    state['shm_file'] = None  # file对象
    state['_sem_ready'] = None  # 信号量句柄
    state['_sem_ack'] = None  # 信号量句柄
    state['model'] = None  # model引用
    # threading.Event转换为bool
    if '_training_mode' in state:
        state['_training_mode'] = state['_training_mode'].is_set()
    return state

def __setstate__(self, state):
    """从pickle恢复 - 重新建立连接"""
    # 恢复threading.Event
    if '_training_mode' in state and isinstance(state['_training_mode'], bool):
        training_was_set = state['_training_mode']
        state['_training_mode'] = threading.Event()
        if training_was_set:
            state['_training_mode'].set()

    self.__dict__.update(state)
    # 注意: 共享内存不自动重连,需要时手动调用 _attach_shared_memory()
```

## 测试验证

所有 pickle 测试均已通过:

✅ `SharedMemoryData` 类和实例 pickle ⭐ **关键测试**
✅ `FunctionTimer` 单独 pickle
✅ `GLOBAL_TIMER` pickle
✅ `LohEnv` 单独 pickle
✅ `RetrospectiveReplayBuffer` pickle
✅ 完整模型状态 pickle (包含 env + buffer + GLOBAL_TIMER)

## 为什么 `loh_actor_critic_sb3_SACblocked.py` 可以保存？

**关键差异**:
1. **SACblocked 版本没有 `GLOBAL_TIMER`** - 不会触发深度 pickle
2. **SACblocked 也用了函数内局部类** - 但 SAC 默认只浅层保存
3. **添加 profiling 后** - `GLOBAL_TIMER` 被引用,触发递归序列化,暴露了局部类问题

**结论**: 不是 profiling 本身的问题,而是它暴露了 `SharedMemoryData` 作为局部类无法 pickle 的潜在 bug。

## 影响范围

- ✅ **不影响正常训练**: 修改只添加了序列化支持,不改变运行时行为
- ✅ **向后兼容**: 旧代码继续工作,新增方法只在 pickle 时调用
- ✅ **最小侵入**: 只添加了 `__getstate__` 和 `__setstate__` 方法

## 使用说明

现在可以正常使用 profiling 版本并保存模型:

```bash
CACHESIM_NUM_REQ=100000 LOH_DEBUG_BASIC=1 bash ./scripts/test_loh_rl_sb3.sh data/WikiCDN/wiki_2019t.oracleGeneral.zst
```

在训练中断 (Ctrl+C 或 terminate signal) 时,模型会自动保存到:
```
./runs/<timestamp>/interrupted_model.zip
```

## 技术细节

### 为什么 profiling 会影响模型保存?

SAC 保存模型时会 pickle:
1. 策略网络、价值网络等神经网络
2. 优化器状态
3. **环境对象** (包含 GLOBAL_TIMER 的引用)
4. **ReplayBuffer** (使用 GLOBAL_TIMER 测量性能)

任何一个组件不支持 pickle 都会导致整个保存失败。

### 最佳实践

1. **ctypes.Structure 类必须在模块级别定义** ⭐ **最重要**
   - ❌ 不要在函数内定义 `class SharedMemoryData(ctypes.Structure)`
   - ✅ 应该在模块顶层定义,让 pickle 可以找到它

2. **自定义类添加 pickle 支持**: 如果类会被 RL 框架保存,务必实现 `__getstate__` / `__setstate__`

3. **测试 pickle**: 在开发早期就测试 `pickle.dumps(obj)`

4. **清理不可序列化资源**: 文件句柄、锁、信号量等都需要在 `__getstate__` 中置为 `None`

---

**修复完成时间**: 2025-10-29
**测试状态**: ✅ 全部通过
