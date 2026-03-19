# 为什么 loh_actor_critic_sb3_SACblocked.py 可以保存模型？

## 核心问题

两个文件都使用了**函数内局部类**定义 `SharedMemoryData`:

```python
def create_shared_memory_class(context_dim):
    class SharedMemoryData(ctypes.Structure):  # 局部类
        _fields_ = [...]
    return SharedMemoryData

SharedMemoryData = create_shared_memory_class(CONTEXT_DIM)
```

这种局部类**无法被 pickle 序列化**,因为 pickle 无法在模块中找到它。

## 关键差异对比

| 特性 | loh_actor_critic_sb3_SACblocked.py | loh_actor_critic_sb3.py (带 profiling) |
|------|-----------------------------------|---------------------------------------|
| SharedMemoryData 定义 | ❌ 函数内局部类 | ❌ 函数内局部类 (已修复✅) |
| 有 GLOBAL_TIMER | ❌ 无 | ✅ 有 |
| 有 FunctionTimer | ❌ 无 | ✅ 有 |
| 深度 pickle 触发 | ❌ 否 | ✅ 是 |
| 模型保存结果 | ✅ 成功 | ❌ 失败 (已修复✅) |

## 为什么 SACblocked 可以保存？

### 1. SAC 的保存机制

`stable-baselines3` 的 SAC 在保存模型时:
- 主要保存**神经网络权重**和**优化器状态**
- 对环境和 ReplayBuffer 只做**浅层保存**
- 不会深度递归序列化所有引用

### 2. 没有 GLOBAL_TIMER 的影响

```python
# SACblocked: 简单引用链
SAC → env → SharedMemoryData (浅层,不深入 pickle)

# 带 profiling: 复杂引用链
SAC → env → ReplayBuffer → GLOBAL_TIMER → SharedMemoryData
                                        ↓
                                  深度 pickle 触发
                                  发现局部类,失败!
```

### 3. Profiling 暴露了潜在 Bug

- **SACblocked 也有 bug**,只是没被触发
- 添加 `GLOBAL_TIMER` 后触发了深度序列化
- 暴露了 `SharedMemoryData` 作为局部类的问题

## 完整的修复

### 修复前 (两个文件都有问题)

```python
# ❌ 局部类,无法 pickle (但 SACblocked 侥幸能用)
def create_shared_memory_class(context_dim):
    class SharedMemoryData(ctypes.Structure):
        _fields_ = [
            ("state", ctypes.c_double * context_dim),  # 动态数组
            ...
        ]
    return SharedMemoryData
```

### 修复后 (模块级别类)

```python
# ✅ 模块级别类,可以 pickle
class SharedMemoryData(ctypes.Structure):
    """共享内存数据结构 - 必须是模块级别类以支持pickle"""
    _fields_ = [
        ("state", ctypes.c_double * CONTEXT_DIM),  # 固定维度
        ("weights", ctypes.c_double * FEATURE_DIM),
        ...
    ]

def create_shared_memory_class(context_dim):
    """保留以兼容旧代码"""
    if context_dim != CONTEXT_DIM:
        warnings.warn(f"Dimension mismatch: {context_dim} vs {CONTEXT_DIM}")
    return SharedMemoryData
```

## 额外修复

除了 `SharedMemoryData`,还需要:

### 1. FunctionTimer pickle 支持

```python
class FunctionTimer:
    def __getstate__(self):
        return {
            'timings': dict(self.timings),
            'call_counts': dict(self.call_counts)
        }

    def __setstate__(self, state):
        self.timings = defaultdict(list, state['timings'])
        self.call_counts = defaultdict(int, state['call_counts'])
```

### 2. LohEnv pickle 支持

```python
class LohEnv:
    def __getstate__(self):
        state = self.__dict__.copy()
        # 移除不可 pickle 的资源
        state['shm'] = None
        state['shm_file'] = None
        state['_sem_ready'] = None
        state['_sem_ack'] = None
        if '_training_mode' in state:
            state['_training_mode'] = state['_training_mode'].is_set()
        return state

    def __setstate__(self, state):
        if '_training_mode' in state and isinstance(state['_training_mode'], bool):
            was_set = state['_training_mode']
            state['_training_mode'] = threading.Event()
            if was_set:
                state['_training_mode'].set()
        self.__dict__.update(state)
```

### 3. 移除不当的 pickle helper（已删除）

在早期调试过程中，代码中曾加入 `LohEnv.__getstate__/__setstate__` 来尝试让环境可被 pickle，从而让 `model.save()` 在含有复杂引用时不失败。

这是一个误导性的变通：它会在序列化时静默丢弃关键的 IPC 资源（mmap、文件句柄、POSIX 信号量），并在反序列化时不自动恢复它们。这样会掩盖真正的根因（例如局部类、局部闭包或线程锁被意外地包含在模型对象图中），并且在恢复后需要调用者手动重连共享内存，导致不一致的运行时行为。

因此这些 helper 已被移除（参见 `scripts/loh_actor_critic_sb3.py` 中的注释）。正确的修复路径是：

- 将 `SharedMemoryData` 定义为模块级别类（可 pickle）
- 为 profiling 数据（`FunctionTimer`）提供明确的序列化支持
- 消除将本地闭包/函数注入 `model` 的做法（不再 monkey-patch），改为 `ProfiledSAC` 子类和在方法内计时

移除这些 helper 后，`model.save()` 成功的原因是对象图内不再包含不可序列化的本地对象；如果需要恢复环境的 IPC 连接，恢复代码应显式调用 `_attach_shared_memory()` 和 `_init_semaphores()`，而不是隐式依赖 `__setstate__`。

## 测试验证

```bash
# 修复前
python3 -c "import pickle; from loh_actor_critic_sb3 import SharedMemoryData; pickle.dumps(SharedMemoryData())"
# ❌ AttributeError: Can't pickle local object 'create_shared_memory_class.<locals>.SharedMemoryData'

# 修复后
python3 -c "import pickle; from loh_actor_critic_sb3 import SharedMemoryData; pickle.dumps(SharedMemoryData())"
# ✅ 成功
```

## 结论

1. **SACblocked 能保存只是侥幸** - 因为没触发深度 pickle
2. **profiling 不是问题的原因** - 它只是暴露了已存在的 bug
3. **真正的问题**: ctypes.Structure 类定义在函数内部
4. **正确做法**: 所有会被 pickle 的类都应该定义在模块级别

---

**修复完成**: 现在两个版本都可以正确保存模型了! ✅
