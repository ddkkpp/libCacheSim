# 说明文档文件夹

此文件夹包含LOH强化学习集成的各种设计文档、修复总结和使用指南。

## 文件命名规则

格式：`MMDDHHMM-文档名称.md`
- 前缀为文档最后修改时间（月日时分）
- 例如：`10282026-REWARD_IMPROVEMENT_PLAN.md` 表示10月28日20:26修改

## 文档分类

### 改进计划 & 优化
- `10282026-REWARD_IMPROVEMENT_PLAN.md` ⭐ **最新** - 奖励差异性与训练效率改进方案
  - 解决reward普遍接近1的问题
  - 纯penalty-based奖励公式
  - 连续运行策略（不reset）
  - 超参数优化建议
- `10272237-PENALTY_QUEUE_OPTIMIZATION.md` - Penalty队列优化
  - 延迟penalty信号优化
  - 队列管理策略
- `10230213-PENALTY_MECHANISM_REDESIGN.md` - Penalty机制重新设计
- `10230213-SAMPLING_EXCLUSION_STRATEGY.md` - 采样排除策略

### 行为控制 & 停止机制
- `10241746-CTRL_C_BEHAVIOR.md` - Ctrl+C优雅停止机制
  - 信号处理
  - 多进程协调
  - 资源清理
- `10241746-LOH_GRACEFUL_SHUTDOWN.md` - LOH优雅关闭机制

### Bug修复总结
- `10232259-PENALTY_FIXES_SUMMARY.md` - Penalty读取修复总结
- `10232259-EVICTION_TIMESTAMP_IMPROVEMENT.md` - 驱逐时间戳改进
- `10230213-PENALTY_FIX_SUMMARY.md` - Penalty修复总结（旧版）
- `09021644-LOH_FIX_SUMMARY.md` - LOH修复总结
- `08081537-LOH_DEEP_ANALYSIS_FIXES.md` - LOH深度分析与修复
- `07291843-LOH_SHARED_MEMORY_FIX.md` - 共享内存修复
- `07291843-loh_file_shm_patch.md` - 文件共享内存补丁

### 实现与测试报告
- `10232259-TWO_COMPONENT_PENALTY_IMPLEMENTATION.md` - 双组件penalty实现
- `10232259-TWO_COMPONENT_PENALTY_TEST_REPORT.md` - 双组件penalty测试报告
- `10230213-TEST_RETROSPECTIVE_PENALTY.md` - Penalty测试回顾

### 使用指南
- `10230213-SAC_RETROSPECTIVE_GUIDE.md` - SAC算法回顾指南
- `10230213-TUNING_GUIDE.md` - 超参数调优指南
- `10170043-LOH_INFERENCE_GUIDE.md` - LOH推理模式使用指南

### 架构与特性
- `09241141-LOH_Algorithm_Architecture.md` - LOH算法架构详解
- `09251949-LOH_REWARD_WEIGHTS_FEATURE.md` - Reward权重特性
- `08081537-LOH_IMPROVEMENTS_SUMMARY.md` - LOH改进总结

## 推荐阅读顺序

### 新手入门
1. `10282026-REWARD_IMPROVEMENT_PLAN.md` - 了解当前最新的奖励机制
2. `09241141-LOH_Algorithm_Architecture.md` - 了解LOH算法架构
3. `10230213-TUNING_GUIDE.md` - 学习如何调整超参数
4. `10241746-CTRL_C_BEHAVIOR.md` - 了解如何正确停止训练

### 深入理解
1. `10230213-SAC_RETROSPECTIVE_GUIDE.md` - SAC算法原理
2. `10272237-PENALTY_QUEUE_OPTIMIZATION.md` - Penalty队列优化
3. `10232259-TWO_COMPONENT_PENALTY_IMPLEMENTATION.md` - 双组件penalty实现
4. `10232259-PENALTY_FIXES_SUMMARY.md` - Penalty机制细节
5. `10170043-LOH_INFERENCE_GUIDE.md` - 推理模式使用

### 问题排查
1. 检查对应时间的修复总结文档（按时间戳查找）
2. 参考 `10232259-EVICTION_TIMESTAMP_IMPROVEMENT.md` 了解时间戳问题
3. 参考 `08081537-LOH_DEEP_ANALYSIS_FIXES.md` 了解深层bug修复
4. 查看 `../test_scripts/` 中的对应测试脚本

## 快速参考

### 当前有效配置（2025-10-28）

**奖励公式**：
```python
if evicted_count == 0:
    reward = 0.0
else:
    penalty_sum = α*obj_penalty + β*byte_penalty
    if baseline > 1e-6:
        reward = (baseline - penalty_sum) / baseline
    else:
        reward = -penalty_sum
    reward = clip(reward, -1, 1)
```

**超参数**：
- `learning_starts = 1000`
- `exclude_recent_steps = 100`
- `obj_penalty_weight = 1.0`
- `byte_penalty_weight = 0.0`
- `buffer_size = 10000`

**运行模式**：
- 连续运行（不reset）
- `truncated = False`

## 文档维护

新增文档时请：
1. 使用时间戳前缀（MMDDHHMM格式）
2. 更新本README的对应分类
3. 如果废弃旧文档，在旧文档开头注明并指向新文档
