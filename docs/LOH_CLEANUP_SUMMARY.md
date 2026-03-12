# LOH RL 脚本整合与清理总结（2025-01）

## 一、问题背景

在整合 7 个独立 LOH RL 脚本变体（mr_PPO, mr_SAC, mr_RewardSlide_PPO, pen_d_SAC, pen_d_TD3, pen_log_SAC, pen_survival_SAC）到统一脚本 `loh_actor_critic_sb3.py` 的过程中，出现了以下问题：

1. **重复的 `_penalty_scale()` 方法**：两个不同实现（line 697 与 line 910）
2. **重复的 LOH_PENALTY_SCALE 解析代码**：两处解析（line 553 与 line 633）
3. **缺少 penalty 机制的开关控制**：penalty 相关代码总是启用，无法禁用

## 二、清理内容

### 2.1 删除重复代码

#### 删除 1：重复的 LOH_PENALTY_SCALE 解析（line 633-646）

**删除位置**：`scripts/loh_actor_critic_sb3.py` 第 633-646 行

**删除内容**：
```python
scale_name = os.environ.get("LOH_PENALTY_SCALE", "reciprocal").strip().lower()
if scale_name == "reciprocal":
    scale_desc = "reciprocal (1/d)"
elif scale_name == "pen_d":
    scale_desc = "pen_d (custom penalty distribution)"
elif scale_name == "survival":
    scale_desc = "survival-based (survival function scaling)"
else:
    scale_desc = scale_name

print(f"[ReplayBuffer] Initialized with:")
print(f"  obj_penalty_weight={obj_penalty_weight}")
print(f"  byte_penalty_weight={byte_penalty_weight}")
print(f"  exclude_recent_steps={exclude_recent_steps}")
print(f"  penalty_scale={scale_desc}")
```

**保留原因**：line 553 的实现是正确的，设置了 `self.penalty_scale_mode` 并包含完整的模式验证。

#### 删除 2：重复的 _penalty_scale() 方法（line 697-722）

**删除位置**：`scripts/loh_actor_critic_sb3.py` 第 697-722 行

**删除内容**：
```python
def _penalty_scale(self, distance: float) -> float:
    """将距离映射到 [0,1] 的惩罚强度，支持多种模式（通过 penalty_mode 配置）。
    此处log和survival和单独文件的不一样
    reciprocal: p(d) = 1 / max(d, 1)
    log:        p(d) = 1 / log(2 + d)
    survival:   p(d) = exp(-d / dmax)
    """
    # ... 实现代码 ...
```

**保留版本**：line 910 版本（现为 line 872），因为它正确实现了与独立脚本一致的 reciprocal/log/survival 模式：
- `reciprocal`: `1 / max(d, 1)`
- `log`: `1 - log1p(d) / log1p(dmax)`
- `survival`: `S(d) = 1 - F(d)` with histogram-based CDF

#### 删除 3：重复的 penalty_dmax/_log_denom 设置（line 618-631）

**删除位置**：在 `self.obj_hit_ratio_at_pos` 初始化后的重复 penalty 参数设置

**原因**：这些参数已在 `if self.enable_penalty:` 块中正确初始化。

### 2.2 新增 LOH_ENABLE_PENALTY 环境变量

**新增位置**：`scripts/loh_actor_critic_sb3.py` RetrospectiveReplayBuffer.__init__()

**实现**：
```python
# 【新增】LOH_ENABLE_PENALTY 控制（默认为 0，不启用 penalty 机制）
self.enable_penalty = _env_flag("LOH_ENABLE_PENALTY", False)
```

**行为**：
- **LOH_ENABLE_PENALTY=0**（默认）：
  - 跳过 penalty_scale_mode、penalty_dmax、survival 参数的初始化
  - 设置占位字段：`penalty_scale_mode="reciprocal"`, `penalty_dmax=400000`, `_log_denom=1.0`
  - 打印：`[ReplayBuffer] LOH_ENABLE_PENALTY=0, penalty mechanism disabled`

- **LOH_ENABLE_PENALTY=1**：
  - 完整初始化 penalty 相关配置（reciprocal/log/survival 模式）
  - 根据 LOH_PENALTY_SCALE 选择缩放模式
  - survival 模式时初始化直方图（bins, quantile, min_count）
  - 打印：`[ReplayBuffer] LOH_ENABLE_PENALTY=1, penalty mechanism enabled`

### 2.3 更新文档 docs/LOH_ENV_VARS.md

**更新内容**：

1. **新增章节**：
   - 第四章：算法选择（Python RL）
     - LOH_RL_ALGO（PPO/SAC/TD3，默认 SAC）

2. **扩展第五章**：奖励/惩罚
   - **LOH_ENABLE_PENALTY**（0/1，默认 0）
   - LOH_PENALTY_SCALE（reciprocal/log/survival，默认 reciprocal）
   - LOH_SURVIVAL_QUANTILE（默认 0.99）
   - LOH_SURVIVAL_BINS（默认 64）
   - LOH_SURVIVAL_MINCOUNT（默认 1000）
   - **LOH_REWARD_WINDOW**（0/integer，默认 0）

3. **更新第八章**：SB3 超参覆盖
   - 明确说明统一脚本整合了 PPO/SAC/TD3
   - 补充 PPO 完整超参列表（PPO_BUFFER_SIZE, PPO_GAE_LAMBDA, PPO_NET_ARCH 等）
   - 更新 SAC/TD3 超参说明，删除过时的 mr_SAC 变体引用

4. **新增第十一章**：统一脚本使用示例
   - 示例 1：SAC + penalty
   - 示例 2：PPO + reward window
   - 示例 3：TD3 + survival penalty

5. **更新章节编号**：
   - 原"七、SB3 超参覆盖" → "八、SB3 超参覆盖"
   - 原"八、默认值来源" → "九、默认值来源"（增加算法选择与 penalty 机制说明）
   - 原"九、验证建议" → "十、验证建议"
   - 原"十、示例" → "十一、示例"

## 三、影响与兼容性

### 3.1 向后兼容性

- **默认行为**：LOH_ENABLE_PENALTY=0，penalty 机制禁用，与未启用 penalty 的旧代码行为一致
- **现有脚本**：如需使用 penalty，需显式设置 `LOH_ENABLE_PENALTY=1`
- **测试脚本**：`test_loh_rl_sb3.sh` 无需修改，可通过环境变量控制

### 3.2 新功能启用

**启用 penalty + survival 模式**：
```bash
export LOH_ENABLE_PENALTY=1
export LOH_PENALTY_SCALE=survival
export LOH_SURVIVAL_BINS=128
bash scripts/test_loh_rl_sb3.sh /path/to/trace 38 0.1 1.0
```

**启用 PPO + reward smoothing**：
```bash
export LOH_RL_ALGO=PPO
export LOH_REWARD_WINDOW=50
bash scripts/test_loh_rl_sb3.sh /path/to/trace 26 0.1 1.0
```

## 四、验证清单

- [x] 确认只有一个 `_penalty_scale()` 方法（line 872）
- [x] 确认只有一处 LOH_PENALTY_SCALE 解析（line 561，在 `if self.enable_penalty:` 内）
- [x] 确认 LOH_ENABLE_PENALTY 默认为 0
- [x] 确认 penalty 相关初始化在 `if self.enable_penalty:` 条件内
- [x] 确认文档更新包含所有新环境变量
- [x] 确认文档章节编号正确
- [x] 确认文档包含使用示例

## 五、后续建议

1. **测试验证**：运行 `test_loh_rl_sb3.sh` 验证 LOH_ENABLE_PENALTY=0/1 的行为差异
2. **性能对比**：对比启用/禁用 penalty 机制的训练效率与 miss ratio
3. **文档完善**：在 LOH_SCRIPTS_INTEGRATION_GUIDE.md 中补充 LOH_ENABLE_PENALTY 的使用说明
4. **清理旧脚本**：考虑将 7 个独立脚本移到 `scripts/legacy/` 目录，避免混淆

## 六、修改文件清单

1. `scripts/loh_actor_critic_sb3.py`
   - 删除 line 633-646（重复的 scale_name 解析）
   - 删除 line 697-722（重复的 _penalty_scale 方法）
   - 删除 line 618-631（重复的 penalty_dmax/_log_denom 设置）
   - 新增 line 516（LOH_ENABLE_PENALTY 控制）
   - 新增 line 559-610（条件化的 penalty 初始化）

2. `docs/LOH_ENV_VARS.md`
   - 更新文档标题时间戳为 2025-01
   - 新增第四章（算法选择）
   - 扩展第五章（penalty 机制与新变量）
   - 更新第八章（统一脚本超参）
   - 更新第九章（优先级说明）
   - 更新第十、十一章（验证与示例）

---

**维护者**：Copilot Agent
**日期**：2025-01
**关联 Issue/PR**：LOH RL 脚本整合与清理
