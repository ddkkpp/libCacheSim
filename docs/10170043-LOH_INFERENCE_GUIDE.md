# LOH模型推理使用指南

## 概述

`loh_inference_only.py` 是一个专门用于LOH缓存算法推理的服务脚本。它加载训练好的PPO模型，为C端LOH缓存算法提供实时权重预测，**不进行任何训练**。

## 功能特点

- ✅ **纯推理模式**：只进行模型推理，不更新模型参数
- ✅ **高性能**：优化的通信机制，支持信号量和轮询模式
- ✅ **实时响应**：快速响应C端的权重请求
- ✅ **资源高效**：相比训练模式，内存和CPU使用更少
- ✅ **稳定运行**：专为生产环境设计，支持长时间运行

## 使用方法

### 1. 基本使用

```bash
# 使用训练好的模型进行推理
python3 scripts/loh_inference_only.py runs/1016_123456/ppo_loh_final.zip
```

### 2. 完整参数

```bash
python3 scripts/loh_inference_only.py [模型路径] [选项]

参数说明：
  模型路径                  训练好的PPO模型文件路径 (.zip格式)

选项：
  --shm-key KEY            共享内存键，默认9876
  --debug-level LEVEL      调试级别：0=无输出, 1=基本信息, 2=详细信息，默认2
  -h, --help              显示帮助信息
```

### 3. 使用示例

```bash
# 基本推理服务
python3 scripts/loh_inference_only.py runs/1016_145032/ppo_loh_final.zip

# 自定义共享内存键
python3 scripts/loh_inference_only.py runs/1016_145032/ppo_loh_final.zip --shm-key 1234

# 静默模式（生产环境推荐）
python3 scripts/loh_inference_only.py runs/1016_145032/ppo_loh_final.zip --debug-level 0

# 基本监控模式
python3 scripts/loh_inference_only.py runs/1016_145032/ppo_loh_final.zip --debug-level 1
```

## 工作流程

```
C端缓存请求 → 共享内存 → Python推理服务 → 权重预测 → 共享内存 → C端应用权重
     ↑                                                                    ↓
     └─────────────── 继续缓存操作，处理下一个请求 ←────────────────────────┘
```

1. **等待请求**：监听C端发送的推理请求 (`ready_for_inference=1`)
2. **读取状态**：从共享内存读取26维状态向量
3. **模型推理**：使用PPO模型预测6维权重向量
4. **权重归一化**：通过softmax确保权重和为1
5. **写入结果**：将权重写入共享内存，设置ACK标志
6. **发送通知**：通过信号量通知C端权重已更新

## 性能优化

### 环境变量配置

```bash
# 禁用信号量，使用轮询模式（某些系统上更稳定）
export LOH_DISABLE_SEMAPHORE=1

# 启用信号量（默认，更低延迟）
export LOH_ENABLE_SEMAPHORE=1

# 设置轮询间隔（微秒）
export LOH_POLL_SLEEP_US=100  # 0.1ms轮询间隔

# 禁用文件同步（提高性能，但可能影响数据一致性）
export LOH_DISABLE_FSYNC=1

# 设置信号量超时时间（秒）
export LOH_SEM_TIMEOUT_S=0.5
```

### 推荐配置

**开发/调试环境：**
```bash
export LOH_DEBUG_LEVEL=2
export LOH_POLL_SLEEP_US=200
export LOH_SEM_TIMEOUT_S=1.0
```

**生产环境：**
```bash
export LOH_DEBUG_LEVEL=0        # 最小日志输出
export LOH_POLL_SLEEP_US=100    # 更快响应
export LOH_SEM_TIMEOUT_S=0.5    # 更短超时
export LOH_DISABLE_FSYNC=1      # 提高性能
```

## 监控和诊断

### 输出信息说明

**启动信息：**
```
🤖 LOH推理服务启动
   模型路径: runs/1016_145032/ppo_loh_final.zip
   共享内存键: 9876
   调试级别: 2
   启动时间: 2025-10-16 14:50:32
✅ LOH推理服务初始化完成
   模型路径: runs/1016_145032/ppo_loh_final.zip
   共享内存键: 9876
   信号量模式: 启用
```

**推理日志（debug-level=2）：**
```
[推理] [seq 12345] 权重: [0.167, 0.145, 0.198, 0.156, 0.178, 0.156] (耗时 0.001234s)
[global_features]: [0.750000, 0.234567]
[request_features]: [0.123, 0.456, 0.789, ...]
```

**心跳信息：**
```
[心跳] 推理服务运行中... 已运行 60.1s, 完成推理 1247 次
```

**统计信息（退出时）：**
```
✅ 推理服务统计:
   总运行时间: 120.45s
   总推理次数: 2456
   平均推理时间: 0.001203s
```

## 与训练模式的区别

| 特性 | 训练模式 | 推理模式 |
|------|---------|---------|
| 模型更新 | ✅ 持续更新参数 | ❌ 参数固定 |
| 内存使用 | 高（梯度、缓冲区等） | 低（仅模型参数） |
| CPU使用 | 高（反向传播计算） | 低（仅前向传播） |
| 响应延迟 | 变化（训练期间较高） | 稳定且低 |
| 资源需求 | GPU友好 | CPU友好 |
| 适用场景 | 模型开发、优化 | 生产部署 |

## 常见问题

### 1. 模型文件不存在
```
❌ 模型文件不存在: runs/xxx/ppo_loh_final.zip
```
**解决方案：** 检查模型路径是否正确，确保训练已完成并保存了模型。

### 2. 共享内存连接失败
```
❌ 共享内存连接失败: [Errno 13] Permission denied
```
**解决方案：** 确保C端程序已启动，或使用sudo运行。

### 3. 信号量初始化失败
```
[SEM] sem_open ready 失败: Function not implemented
```
**解决方案：** 使用环境变量禁用信号量：`export LOH_DISABLE_SEMAPHORE=1`

### 4. 推理服务无响应
**检查步骤：**
1. 确认C端程序正在运行
2. 检查共享内存键是否匹配
3. 查看debug日志确认请求是否到达
4. 尝试降低`LOH_POLL_SLEEP_US`值

## 生产部署建议

1. **使用systemd服务**：创建系统服务确保自动重启
2. **监控脚本**：监控推理服务状态和性能指标
3. **日志轮转**：配置日志轮转避免磁盘空间问题
4. **资源限制**：使用cgroup限制CPU和内存使用
5. **健康检查**：定期检查推理响应时间和准确性

## 集成示例

```bash
#!/bin/bash
# 生产环境启动脚本示例

export LOH_DEBUG_LEVEL=1
export LOH_DISABLE_FSYNC=1
export LOH_POLL_SLEEP_US=100

MODEL_PATH="models/production/ppo_loh_v1.2.zip"
LOG_FILE="logs/loh_inference_$(date +%Y%m%d_%H%M%S).log"

echo "启动LOH推理服务..."
python3 scripts/loh_inference_only.py "$MODEL_PATH" 2>&1 | tee "$LOG_FILE"
```
