## LOH Cache Miss Ratio 权重参数功能

### 概述
为 LOH 缓存算法添加了命令行配置 reward 函数中 miss ratio 和 byte miss ratio 权重的功能。

### 功能特性

#### 1. C 端支持（LOH.c）
- 在 `LOH_params_t` 结构中添加了权重参数：
  - `miss_ratio_weight`: 对象 miss ratio 的权重（默认 1.0）
  - `byte_miss_ratio_weight`: 字节 miss ratio 的权重（默认 0.0）

- 支持通过 cachesim 的 `--eviction-params` 传递参数：
  ```bash
  cachesim trace.zst oracleGeneral LOH 0.1 --eviction-params="miss-ratio-weight=0.7"
  ```

- Reward 计算公式更新为：
  ```c
  reward = params->miss_ratio_weight * (1.0 - miss_ratio) +
           params->byte_miss_ratio_weight * (1.0 - byte_miss_ratio)
  ```

#### 2. Python 端支持（loh_actor_critic_sb3.py）
- 添加命令行参数解析：
  ```bash
  python3 loh_actor_critic_sb3.py --miss-ratio-weight 0.7
  ```

- 参数验证：权重必须在 0.0-1.0 之间
- 自动显示配置的权重信息

#### 3. 测试脚本支持（test_loh_rl_sb3.sh）
- 扩展为支持 4 个参数：
  ```bash
  test_loh_rl_sb3.sh [trace_file] [state_dim] [cache_size] [miss_ratio_weight]
  ```

- 使用示例：
  ```bash
  # 默认权重（100% object miss ratio, 0% byte miss ratio）
  ./test_loh_rl_sb3.sh

  # 自定义权重（60% object miss ratio, 40% byte miss ratio）
  ./test_loh_rl_sb3.sh data/trace.zst 26 0.1 0.6
  ```

### 权重说明

- **miss_ratio_weight**: 对象级别未命中率的权重
  - 关注缓存命中的对象数量
  - 适用于优化对象级别的性能

- **byte_miss_ratio_weight**: 字节级别未命中率的权重
  - 关注缓存命中的字节数量
  - 适用于优化带宽使用效率
  - 自动计算为 `1.0 - miss_ratio_weight`

### 使用场景

1. **纯对象优化** (miss_ratio_weight=1.0)：
   - 最大化缓存命中的对象数量
   - 适合小对象为主的场景

2. **纯字节优化** (miss_ratio_weight=0.0)：
   - 最大化缓存命中的字节数
   - 适合大对象为主的场景

3. **混合优化** (0.0 < miss_ratio_weight < 1.0)：
   - 平衡对象数量和字节数的优化
   - 适合对象大小分布不均匀的场景

### 验证测试

所有功能已通过测试：
- ✅ C 代码编译成功
- ✅ 参数验证正常工作
- ✅ Python 脚本参数解析正确
- ✅ Test 脚本参数传递正常
- ✅ 权重信息正确显示
- ✅ **权重参数正确应用到reward计算中**（已修复）

### 修复的问题

**问题**: 初始版本中，虽然Python脚本正确解析了命令行权重参数，但没有传递给`LohEnv`环境，导致reward计算仍使用硬编码的默认权重(1.0, 0.0)。

**解决方案**:
1. 修改`LohEnv.__init__()`方法，添加`miss_ratio_weight`和`byte_miss_ratio_weight`参数
2. 在`main()`函数中将解析的权重参数传递给环境实例
3. 添加详细的reward计算日志，便于验证权重应用情况
4. 在环境初始化时显示权重配置信息

### 示例输出

```bash
$ ./test_loh_rl_sb3.sh data/trace.zst 26 0.1 0.7
使用您指定的权重: miss_ratio_weight=0.7, byte_miss_ratio_weight=0.3
Running cachesim with the following parameters:
  Miss ratio weight: 0.7
  Byte miss ratio weight: 0.3
```
