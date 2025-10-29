# LOH RL训练的正确终止方式

## 问题说明

当运行 `test_loh_rl_sb3.sh` 后，如果需要提前终止训练，使用不同的方式会有不同的效果：

### ❌ 错误方式：Ctrl+Z（暂停）

```bash
# 运行测试
CACHESIM_NUM_REQ=1000000 bash test_loh_rl_sb3.sh
# 然后按 Ctrl+Z
```

**问题**：
- `Ctrl+Z` 发送的是 `SIGTSTP`（暂停信号），不是终止信号
- 整个进程组（C端和Python端）都会被暂停（suspended）
- 进程只是暂停，没有终止，也不会写入终止标志
- Python端恢复后会继续等待C端响应，但C端已经暂停了
- 导致Python端反复超时（79次日志就是这个原因）

### ✅ 正确方式1：Ctrl+C（中断）

```bash
# 运行测试
CACHESIM_NUM_REQ=1000000 bash test_loh_rl_sb3.sh
# 然后按 Ctrl+C
```

**效果**：
- `Ctrl+C` 发送 `SIGINT`（中断信号）到整个进程组
- C端和Python端都会收到中断信号
- Python端捕获 `KeyboardInterrupt` 异常，保存模型并优雅退出
- 测试脚本也会执行清理操作

### ✅ 正确方式2：让trace自然结束

```bash
# 设置较小的请求数，让程序自然结束
CACHESIM_NUM_REQ=10000 bash test_loh_rl_sb3.sh
```

**效果**：
- C端处理完所有请求后正常退出
- 测试脚本通过 `loh_stop.py` 向共享内存写入 `terminate=1`
- Python端检测到终止标志，优雅退出

### ✅ 正确方式3：使用停止脚本

在另一个终端执行：
```bash
python3 scripts/loh_stop.py
```

**效果**：
- 向共享内存写入 `terminate=1`
- Python端检测到终止标志，优雅退出
- C端会在下次RL更新时检测到终止标志并退出

## 改进后的检测机制

### 连续超时检测（已实现）

Python端现在有更快的检测机制：

```python
max_consecutive_timeouts = 5  # 连续超时5次（约2.5秒）
```

**触发条件**：
- 在等待C端新状态时，信号量连续超时5次
- 每次超时约0.5秒，总共约2.5秒

**退出消息**：
```
======================================================================
⚠️  检测到C端可能已结束（连续 5 次信号量超时）
   等待新状态耗时: 2.5秒
   最后确认的序列号: 3866
   说明: C端程序已正常结束或被中断（Ctrl+C/Ctrl+Z）
         Python端将优雅退出以保存训练进度
======================================================================
```

### 空闲检测（备用机制）

```python
idle_threshold = 3.0  # 3秒无活动判断C端结束
```

如果信号量功能正常但C端确实结束了，会通过检测共享内存中 `state_version` 和 `timestamp` 是否变化来判断。

## 如果进程被暂停了怎么办？

### 查看暂停的进程

```bash
jobs
# 输出示例：
# [1]+  Stopped    bash test_loh_rl_sb3.sh
```

### 方式1：终止暂停的进程

```bash
# 终止最近的后台任务
kill %1

# 或者查找并终止所有相关进程
pkill -9 -f "loh_actor_critic_sb3.py"
pkill -9 -f "cachesim.*LOH"
```

### 方式2：恢复并正确终止

```bash
# 将任务调到前台
fg

# 然后按 Ctrl+C 正确终止
```

## 清理残留资源

如果进程异常退出，需要手动清理：

```bash
# 停止所有LOH相关进程
./scripts/stop_loh_rl.sh

# 或手动清理
pkill -9 -f "loh_actor_critic_sb3.py"
pkill -9 -f "cachesim.*LOH"
rm -f /dev/shm/loh_ac_9876
```

## 最佳实践

1. **开发测试**：使用小数据集（1000-10000请求）
   ```bash
   CACHESIM_NUM_REQ=1000 bash test_loh_rl_sb3.sh
   ```

2. **需要中断时**：使用 Ctrl+C，不要用 Ctrl+Z

3. **并行运行**：每个实例使用不同的 SHM_KEY
   ```bash
   # 实例1
   SHM_KEY=9876 CACHESIM_NUM_REQ=100000 bash test_loh_rl_sb3.sh

   # 实例2（修改脚本中的SHM_KEY）
   SHM_KEY=9877 CACHESIM_NUM_REQ=100000 bash test_loh_rl_sb3.sh
   ```

4. **监控训练进度**：在另一个终端查看TensorBoard
   ```bash
   tensorboard --logdir ./runs --bind_all --port 6006
   # 浏览器打开 http://localhost:6006
   ```

## 总结

- ✅ **Ctrl+C** - 正确的中断方式
- ✅ **自然结束** - 最优雅的方式
- ✅ **loh_stop.py** - 远程终止
- ❌ **Ctrl+Z** - 会导致进程暂停，不是终止

现在Python端已优化，即使C端异常结束，也能在约2.5秒内检测到并优雅退出。
