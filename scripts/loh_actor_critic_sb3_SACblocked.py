#!/usr/bin/env python3
# Print actual script filename at runtime (dynamic)
import os, sys
_loh_script_name = os.path.basename(__file__) if '__file__' in globals() and __file__ else (os.path.basename(sys.argv[0]) if sys.argv and sys.argv[0] else '<unknown>')
print(f"[LOH SCRIPT] { _loh_script_name }")

#该版本根据callback函数管理训练/推理状态切换

import gymnasium as gym
from gymnasium import spaces
import numpy as np
import ctypes
import threading
import mmap
import os
import sys
import errno

import time
from datetime import datetime
from typing import Optional

from stable_baselines3 import PPO  # 保留作参考
from stable_baselines3 import SAC
from stable_baselines3.common.buffers import ReplayBuffer
import numpy as np

# 常数定义
LOH_DEBUG_LEVEL = 2

def LOH_DEBUG_BASIC():
    return LOH_DEBUG_LEVEL >= 1

def LOH_DEBUG_VERBOSE():
    return LOH_DEBUG_LEVEL >= 2

from stable_baselines3 import PPO  # 保留作参考
# from stable_baselines3.common.logger import configure
# from stable_baselines3.common.env_checker import check_env
import torch

# POSIX 信号量绑定（基于 libc）
libc = ctypes.CDLL("libc.so.6", use_errno=True)

class Timespec(ctypes.Structure):
    _fields_ = [("tv_sec", ctypes.c_long), ("tv_nsec", ctypes.c_long)]

SEM_FAILED = ctypes.c_void_p(-1).value

libc.sem_open.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_uint, ctypes.c_uint]
libc.sem_open.restype = ctypes.c_void_p
libc.sem_close.argtypes = [ctypes.c_void_p]
libc.sem_close.restype = ctypes.c_int
libc.sem_post.argtypes = [ctypes.c_void_p]
libc.sem_post.restype = ctypes.c_int
libc.sem_timedwait.argtypes = [ctypes.c_void_p, ctypes.POINTER(Timespec)]
libc.sem_timedwait.restype = ctypes.c_int
libc.sem_trywait.argtypes = [ctypes.c_void_p]
libc.sem_trywait.restype = ctypes.c_int
libc.sem_wait.argtypes = [ctypes.c_void_p]
libc.sem_wait.restype = ctypes.c_int
if hasattr(libc, "sem_unlink"):
    libc.sem_unlink.argtypes = [ctypes.c_char_p]
    libc.sem_unlink.restype = ctypes.c_int

# 添加获取单调时钟的函数
def get_monotonic_time():
    """获取单调时钟时间，与C端CLOCK_MONOTONIC一致"""
    return time.clock_gettime(time.CLOCK_MONOTONIC)


def _env_flag(name: str, default: bool) -> bool:
    """读取布尔型环境变量，允许多种表示方式."""
    raw = os.environ.get(name)
    if raw is None:
        return default
    lowered = raw.strip().lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    return default


def _env_float(name: str, default: Optional[float]) -> Optional[float]:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


# 是否启用 log1p(raw) 特征与“原始权重”模式
LOH_FEATURE_LOG1P = _env_flag("LOH_FEATURE_LOG1P", False)

# --- 常量和共享内存结构定义 ---
SHM_KEY = 9876
FEATURE_DIM = 6

# 动态解析状态维度（与 C 端 -DLOH_INCLUDE_CACHE_FEATURES / LOH_INCLUDE_CANDIDATE_FEATURES 对齐）
def _env_truthy(name: str) -> bool:
    v = os.environ.get(name)
    if v is None:
        return False
    return v.strip().lower() in {"1", "true", "yes", "on"}

def _get_state_dim() -> int:
    """基础维度 (26/38) + 可选候选特征附加 72 维，完全由 LOH_INCLUDE_* 决定。"""
    base = 38
    cache_flag = os.environ.get("LOH_INCLUDE_CACHE_FEATURES", "").strip().lower()
    if cache_flag in {"0", "false", "no", "off"}:
        base = 26
    cand_flag = os.environ.get("LOH_INCLUDE_CANDIDATE_FEATURES", "0").strip().lower()
    cand_enabled = cand_flag in {"1", "true", "yes", "on"}
    return base + (72 if cand_enabled else 0)

CONTEXT_DIM = _get_state_dim()  # 26/38 (+72) 维状态向量
STATE_DIM = CONTEXT_DIM  # 与C端一致

# 【移除】惩罚队列常量 - 改为动态读取
# MAX_PENALTY_QUEUE_SIZE = 128  # 不再需要固定大小

# 惩罚条目结构（存储原始数据，与 C 端完全一致）
class PenaltyEntry(ctypes.Structure):
    _fields_ = [
        ("penalty_version", ctypes.c_uint64),
        ("eviction_to_access", ctypes.c_int64),   # 驱逐到访问的距离
        ("obj_size", ctypes.c_int64),             # 对象大小
        ("obj_id", ctypes.c_uint64),
    ]

def create_shared_memory_class(context_dim):
    """动态创建共享内存数据结构类"""
    class SharedMemoryData(ctypes.Structure):
        _fields_ = [
            ("ready_for_inference", ctypes.c_int),
            ("weights_updated", ctypes.c_int),
            ("terminate", ctypes.c_int),
            ("is_training", ctypes.c_int),
            ("state", ctypes.c_double * context_dim),
            ("weights", ctypes.c_double * FEATURE_DIM),
            # 【修改】驱逐统计
            ("total_evicted_bytes", ctypes.c_uint64),  # 周期累计驱逐字节数
            ("total_evicted_count", ctypes.c_uint64),  # 周期累计驱逐对象数
            ("state_version", ctypes.c_uint64),
            ("ack_version", ctypes.c_uint64),
            ("timestamp", ctypes.c_int64),
            # 【优化】只传递 penalty 数量，数据从文件偏移读取
            ("pending_penalty_count", ctypes.c_int),  # 当前周期待处理的惩罚数量
        ]
    return SharedMemoryData

SharedMemoryData = create_shared_memory_class(CONTEXT_DIM)

# 可选：打印 sizeof/offset，用于与 C 端核对对齐
if _env_truthy("LOH_PRINT_SHM_LAYOUT"):
    try:
        _sz = ctypes.sizeof(SharedMemoryData)
        print(f"[SHM] Python SharedMemoryData sizeof={_sz} bytes (STATE_DIM={STATE_DIM})")
        for _fname, _ in SharedMemoryData._fields_:
            try:
                _off = getattr(SharedMemoryData, _fname).offset
                print(f"[SHM] field {_fname:>22s} @ offset {_off}")
            except Exception:
                pass
    except Exception:
        pass

def _print_candidate_block(state_arr: np.ndarray):
    """打印候选特征段（72维），与 C 端顺序一致: 每来源6特征的 mean,var 扁平展开"""
    total = state_arr.shape[0]
    if total == 26:
        return  # 无附加段
    if total == 38:
        return  # 无候选段
    # 可能是 26+72 或 38+72
    if total not in (26+72, 38+72):
        return
    base_off = 26 if total == 98 else 38
    cand_total = total - base_off
    if cand_total != 72:
        return
    flat = ", ".join([f"{state_arr[base_off + j]:.6f}" for j in range(cand_total)])
    print(f"[candidate_features]: [{flat}]")

# --- 自定义 ReplayBuffer：支持延迟奖励修正 ---
class RetrospectiveReplayBuffer(ReplayBuffer):
    """
    支持事后修正奖励的 ReplayBuffer

    核心思想：
    - 维护一个 version -> buffer_index 的映射
    - 当检测到"延迟惩罚"时，回溯修正历史transition的奖励
    - SAC在采样时会自动使用修正后的奖励进行训练
    - 【新增】采样时避开最新的N个数据，等待惩罚修正
    """

    def __init__(self, *args, exclude_recent_steps=200,
                 obj_penalty_weight=1.0, byte_penalty_weight=0.0, **kwargs):
        """
        Args:
            exclude_recent_steps: 采样时排除最近N步的数据（默认200，约等于rl_update_interval）
            obj_penalty_weight: 对象hit_ratio权重 (alpha)，默认1.0
            byte_penalty_weight: 字节hit_ratio权重 (beta)，默认0.0
        """
        super().__init__(*args, **kwargs)
        # version -> buffer position 映射（用于快速查找）
        self.version_to_pos = {}  # {state_version: buffer_pos}

        # 【修改】存储原始惩罚数据（每个buffer位置对应一个列表）
        # penalty_data[pos] = [(eviction_to_access, obj_size), ...]
        self.penalty_data = [[] for _ in range(self.buffer_size)]

        # 【新增】存储每个位置对应的驱逐统计（用于延迟计算）
        self.evicted_bytes_at_pos = [0] * self.buffer_size  # 该位置epoch的total_evicted_bytes
        self.evicted_count_at_pos = [0] * self.buffer_size  # 该位置epoch的total_evicted_count

        # 【新增】记录哪些位置的奖励已经被最终计算
        self.reward_finalized = [False] * self.buffer_size

        # 奖励修正统计
        self.reward_corrections = 0  # 累积的惩罚次数
        self.total_obj_penalty = 0.0  # 累积的对象惩罚总和
        self.total_byte_penalty = 0.0  # 累积的字节惩罚总和

        # 【新增】Penalty baseline（滑动平均）
        self.penalty_baseline = 0.0  # 初始为0
        self.baseline_decay = 0.99   # 指数衰减系数

        # 奖励计算参数
        self.obj_penalty_weight = obj_penalty_weight    # 默认1.0
        self.byte_penalty_weight = byte_penalty_weight  # 默认0.0

        # 采样保护窗口
        self.exclude_recent_steps = exclude_recent_steps
        self.excluded_samples = 0  # 统计：因保护窗口而跳过采样的次数

        print(f"[ReplayBuffer] Initialized with:")
        print(f"  obj_penalty_weight={obj_penalty_weight}")
        print(f"  byte_penalty_weight={byte_penalty_weight}")
        print(f"  exclude_recent_steps={exclude_recent_steps}")

    def add(self, obs, next_obs, action, reward, done, infos):
        """
        重写add方法，记录version映射并初始化惩罚列表

        注意：reward参数是根据state中的global_features计算的加权命中率
        """
        # 【性能优化】测量 add 函数的耗时
        add_start = time.perf_counter()

        # 【调试】记录add前的状态
        pos_before = self.pos
        full_before = self.full

        # 记录当前position对应的state_version
        if len(infos) > 0 and 'state_version' in infos[0]:
            state_version = infos[0]['state_version']
            self.version_to_pos[state_version] = pos_before  # 使用add前的pos

            if LOH_DEBUG_VERBOSE() and pos_before % 100 == 0:
                print(f"[ReplayBuffer] Added transition at pos={pos_before}, version={state_version}")

        # 【修改】初始化该位置的惩罚数据和驱逐统计
        # 注意：这是必需的，因为环形buffer会覆盖旧数据
        init_start = time.perf_counter()
        self.penalty_data[pos_before] = []
        self.evicted_bytes_at_pos[pos_before] = infos[0].get('total_evicted_bytes', 0) if len(infos) > 0 else 0
        self.evicted_count_at_pos[pos_before] = infos[0].get('total_evicted_count', 0) if len(infos) > 0 else 0
        self.reward_finalized[pos_before] = False
        init_end = time.perf_counter()

        # 【优化】只在 VERBOSE 模式或每 100 步打印一次（减少日志开销）
        if LOH_DEBUG_VERBOSE() or (LOH_DEBUG_BASIC() and pos_before % 100 == 0):
            # 【优化】直接使用 .item()，因为 SB3 内部已将 reward 转为 numpy 数组
            reward_scalar = reward.item() if hasattr(reward, 'item') else float(reward)
            print(f"[ReplayBuffer] pos={pos_before}, reward={reward_scalar:.6f}, "
                  f"evicted_bytes={self.evicted_bytes_at_pos[pos_before]}, "
                  f"evicted_count={self.evicted_count_at_pos[pos_before]}")

        # 调用父类方法存储（reward是基于global_features的加权命中率）
        super_start = time.perf_counter()
        super().add(obs, next_obs, action, reward, done, infos)
        super_end = time.perf_counter()

        add_end = time.perf_counter()

        # 【性能监控】如果 add 函数耗时超过 0.1ms，打印警告
        total_add_time = (add_end - add_start) * 1000  # 转换为毫秒
        if total_add_time > 0.1:
            init_time = (init_end - init_start) * 1000
            super_time = (super_end - super_start) * 1000
            print(f"⚠️  [PERF] ReplayBuffer.add() took {total_add_time:.4f}ms "
                  f"(init: {init_time:.4f}ms, super: {super_time:.4f}ms)")

        # 【调试】检测buffer满的时刻
        if not full_before and self.full:
            print(f"🔄 [ReplayBuffer] Buffer just became FULL! pos: {pos_before} -> {self.pos}, full: {full_before} -> {self.full}")

        # 【调试】在接近满的时候详细打印
        if pos_before >= self.buffer_size - 5:
            print(f"⚠️  [ReplayBuffer] Near full: pos_before={pos_before}, buffer_size={self.buffer_size}")
            print(f"    After super().add(): pos={self.pos}, full={self.full}, size={self.size()}")

        # 【额外调试】每1000步打印一次状态
        if self.pos % 1000 == 0 and LOH_DEBUG_BASIC():
            print(f"📊 [ReplayBuffer] pos={self.pos}, full={self.full}, size={self.size()}")

    def retrospective_correct_reward(self, state_version, eviction_to_access, obj_size):
        """
        累积原始惩罚数据（不立即计算最终奖励）

        【新逻辑】:
        - 只存储原始数据：eviction_to_access 和 obj_size
        - 最终奖励将在 compute_final_rewards() 中延迟计算
        - 使用该位置记录的 epoch_evicted_bytes 和 epoch_evicted_count

        Args:
            state_version: 需要修正的状态版本号
            eviction_to_access: 驱逐到访问的距离
            obj_size: 对象大小
        """
        if state_version not in self.version_to_pos:
            if LOH_DEBUG_VERBOSE():
                print(f"[ReplayBuffer] Version {state_version} not in buffer (已被覆盖或未存储)")
            return False

        pos = self.version_to_pos[state_version]

        # 检查position是否仍然有效（循环buffer可能已覆盖）
        if not self.full and pos >= self.pos:
            if LOH_DEBUG_VERBOSE():
                print(f"[ReplayBuffer] Position {pos} invalid (buffer not full yet)")
            return False

        # 【新增】将原始数据添加到列表中
        self.penalty_data[pos].append((eviction_to_access, obj_size))

        # 统计
        self.reward_corrections += 1

        # 【新增】详细打印
        if LOH_DEBUG_BASIC():
            print(f"[Buffer→Modify] � Accumulated penalty at pos {pos}:")
            print(f"  - state_version: {state_version}")
            print(f"  - eviction_to_access: {eviction_to_access}")
            print(f"  - obj_size: {obj_size}")
            print(f"  - total penalties at pos: {len(self.penalty_data[pos])}")
            print(f"  - evicted_bytes at pos: {self.evicted_bytes_at_pos[pos]}")
            print(f"  - evicted_count at pos: {self.evicted_count_at_pos[pos]}")
            print(f"  - reward_corrections: {self.reward_corrections}")

        return True

    def compute_final_rewards(self, start_pos, end_pos):
        """
        计算指定范围内的最终奖励

        在数据超过 exclude_recent_steps 后调用，使用存储的驱逐统计计算惩罚

        公式:
        1. obj_penalty = Σ(1/evicted_count * 1/distance)
        2. byte_penalty = Σ(size/evicted_bytes * 1/distance)
        3. reward = initial_reward - pow(α*obj_penalty + β*byte_penalty, γ)

        Args:
            start_pos: 起始位置（包含）
            end_pos: 结束位置（不包含）
        """
        count_computed = 0
        for pos in range(start_pos, end_pos):
            if pos >= self.buffer_size:
                pos = pos % self.buffer_size

            # 跳过已经最终化的位置
            if self.reward_finalized[pos]:
                continue

            # 获取该位置的驱逐统计
            evicted_count = self.evicted_count_at_pos[pos]
            evicted_bytes = self.evicted_bytes_at_pos[pos]

            # 【关键】如果该周期没有驱逐，reward直接置为0
            if evicted_count == 0:
                final_reward = 0.0
                self.rewards[pos, 0] = final_reward
                self.reward_finalized[pos] = True
                count_computed += 1

                if LOH_DEBUG_BASIC() and count_computed <= 5:
                    print(f"[Reward→Final] 🎯 pos {pos}:")
                    print(f"  📊 No evictions (evicted_count=0)")
                    print(f"  🎁 final_reward: 0.0 (neutral)")
                continue

            # 计算加权penalty（对象惩罚 + 字节惩罚）
            obj_penalty = 0.0
            byte_penalty = 0.0
            raw_penalty_count = len(self.penalty_data[pos])

            for (eviction_to_access, obj_size) in self.penalty_data[pos]:
                # 对象惩罚：1/evicted_count * 1/distance
                obj_penalty += (1.0 / evicted_count) * (1.0 / eviction_to_access)

                # 字节惩罚：size/evicted_bytes * 1/distance
                if evicted_bytes > 0:
                    byte_penalty += (obj_size / evicted_bytes) * (1.0 / eviction_to_access)

            # 加权求和
            penalty_sum = (self.obj_penalty_weight * obj_penalty +
                          self.byte_penalty_weight * byte_penalty)

            # 【Reward公式】Reward = (baseline - current) / baseline
            # - 相对于baseline的改进
            # - 范围：[-∞, 1]，clip到[-1, 1]
            #
            # 为什么用 1e-6 作为边界？
            # - 避免除零错误：如果 baseline=0，除法会崩溃
            # - 判断baseline有效性：baseline < 1e-6 认为是"接近零"（实际上无意义）
            # - 浮点数精度：1e-6 是合理的"非零"阈值（比机器精度1e-15大得多）
            if self.penalty_baseline > 1e-6:
                # 有有效baseline：计算相对变化
                reward = (self.penalty_baseline - penalty_sum) / self.penalty_baseline
            else:
                # 无有效baseline（初期或baseline接近0）：直接用负penalty
                reward = -penalty_sum if penalty_sum > 0 else 0.0

            # 更新baseline（指数移动平均）
            self.penalty_baseline = (self.baseline_decay * self.penalty_baseline +
                                    (1 - self.baseline_decay) * penalty_sum)

            # Clip到[-1, 1]
            final_reward = max(-1.0, min(1.0, reward))

            # 更新统计
            self.reward_corrections += raw_penalty_count
            self.total_obj_penalty += obj_penalty
            self.total_byte_penalty += byte_penalty

            # 写入buffer
            self.rewards[pos, 0] = final_reward
            self.reward_finalized[pos] = True
            count_computed += 1

            # 【增强】打印前 5 个详细的奖励计算过程
            if LOH_DEBUG_BASIC() and count_computed <= 5:
                print(f"[Reward→Final] 🎯 pos {pos}:")
                print(f"  📊 penalty_data: {raw_penalty_count} items")
                print(f"  📊 evicted_count: {evicted_count}, evicted_bytes: {evicted_bytes}")
                print(f"  📐 obj_penalty: {obj_penalty:.8f}")
                print(f"  📐 byte_penalty: {byte_penalty:.8f}")
                print(f"  📐 penalty_sum (weighted): {penalty_sum:.8f}")
                print(f"  📐 penalty_baseline: {self.penalty_baseline:.8f}")
                print(f"  📐 relative_change: {(self.penalty_baseline - penalty_sum):.8f}")
                print(f"  🎁 reward (before clip): {reward:.6f}")
                print(f"  🎁 final_reward (after clip): {final_reward:.6f}")
            elif LOH_DEBUG_BASIC() and count_computed == 6:
                print(f"[Reward→Final] ... (computed {count_computed} rewards, suppressing further output)")

        if LOH_DEBUG_BASIC() and count_computed > 0:
            print(f"[ReplayBuffer] ✅ Computed {count_computed} final rewards "
                  f"for positions [{start_pos}, {end_pos})")

        return count_computed

    def sample(self, batch_size, env=None):
        """
        重写sample方法：采样时避开最新的exclude_recent_steps步数据

        原因：
        - 最新数据可能还未被惩罚修正（Ghost cache miss需要时间）
        - 避免使用错误奖励训练，提高数据质量
        """
        if not self.optimize_memory_usage:
            # 计算可采样范围
            effective_size = self.size()
            buffer_full = self.full  # 使用self.full判断是否已满

            # 【调试打印】采样前的状态
            if LOH_DEBUG_BASIC() and self.excluded_samples % 50 == 0:  # 每50次打印一次
                print(f"\n🔍 [SAMPLE DEBUG #{self.excluded_samples}]")
                print(f"  - effective_size: {effective_size}")
                print(f"  - self.pos: {self.pos}")
                print(f"  - self.full: {self.full}")
                print(f"  - buffer_full: {buffer_full}")
                print(f"  - exclude_recent_steps: {self.exclude_recent_steps}")
                print(f"  - batch_size: {batch_size}")

            if effective_size <= self.exclude_recent_steps:
                # 缓冲区太小，无法排除足够数据，使用全部数据
                if LOH_DEBUG_BASIC() and self.excluded_samples == 0:
                    print(f"⚠️  Buffer too small ({effective_size} <= {self.exclude_recent_steps}), using all data")
                return super().sample(batch_size, env)

            # 【修正】无论buffer是否已满，都排除最新N个数据
            # Buffer未满：采样范围 [0, pos - exclude_recent_steps)
            # Buffer已满：采样范围避开 [pos - exclude_recent_steps, pos) 的环形区域

            if not buffer_full:
                # Buffer未满：简单情况，采样 [0, pos - exclude_recent_steps)
                upper = self.pos - self.exclude_recent_steps
                if upper <= 0:
                    # 没有足够老的数据，使用全部
                    upper = max(1, self.pos)  # 至少为1，避免 randint(0, 0)
                batch_inds = np.random.randint(0, upper, size=batch_size)

                if LOH_DEBUG_BASIC() and self.excluded_samples % 50 == 0:
                    print(f"  - Buffer未满，采样范围: [0, {upper})")
                    print(f"  - Sample indices (first 5): {batch_inds[:5]}")
            else:
                # Buffer已满：环形缓冲区，需要小心处理
                # 最新的数据在 [pos, pos + exclude_recent_steps) 位置（环形）
                # 我们从剩余的 buffer_size - exclude_recent_steps 个位置采样
                safe_count = self.buffer_size - self.exclude_recent_steps
                # 安全区域从 pos + exclude_recent_steps 开始（环形）
                safe_start = (self.pos + self.exclude_recent_steps) % self.buffer_size

                # 生成 [0, safe_count) 的索引，然后映射到安全区域
                random_offsets = np.random.randint(0, safe_count, size=batch_size)
                batch_inds = (safe_start + random_offsets) % self.buffer_size

                if LOH_DEBUG_BASIC() and self.excluded_samples % 50 == 0:
                    print(f"  - Buffer已满，pos={self.pos}")
                    print(f"  - 排除区域 (unsafe): [{self.pos}, {(self.pos + self.exclude_recent_steps) % self.buffer_size})")
                    print(f"  - 安全区域起点: {safe_start}, 可采样数: {safe_count}")
                    print(f"  - Sample indices (first 5): {batch_inds[:5]}")
                    # 验证没有采样到排除区域
                    unsafe_start = self.pos
                    unsafe_end = (self.pos + self.exclude_recent_steps) % self.buffer_size
                    for idx in batch_inds[:10]:  # 检查前10个
                        if unsafe_end > unsafe_start:
                            in_unsafe = (unsafe_start <= idx < unsafe_end)
                        else:  # 环形越界
                            in_unsafe = (idx >= unsafe_start or idx < unsafe_end)
                        if in_unsafe:
                            print(f"    ⚠️  WARNING: Sampled from unsafe zone! idx={idx}")

                self.excluded_samples += 1
        else:
            # optimize_memory_usage=True 的情况，直接用父类方法
            return super().sample(batch_size, env)

        # 返回采样的transitions（使用修正后的奖励）
        return self._get_samples(batch_inds, env=env)

    def get_correction_stats(self):
        """获取奖励修正统计"""
        return {
            'corrections': self.reward_corrections,
            'total_penalty': self.total_penalty_applied,
            'avg_penalty': self.total_penalty_applied / max(1, self.reward_corrections),
            'excluded_samples': self.excluded_samples,  # 新增：因保护窗口跳过的批次数
        }

# --- 自定义Gymnasium环境 ---
class LohEnv(gym.Env):
    """快速通信版本的LOH环境"""
    metadata = {"render_modes": []}

    def __init__(self, shm_key=SHM_KEY, miss_ratio_weight=1.0, byte_miss_ratio_weight=0.0):
        super(LohEnv, self).__init__()

        # 1. 定义动作空间和观测空间
        self.action_space = spaces.Box(
            low=-1.0, high=1.0, shape=(FEATURE_DIM,), dtype=np.float32
        )
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(STATE_DIM,), dtype=np.float32
        )

        # 2. 连接共享内存
        self.shm_key = shm_key
        self.shm = None
        self.shm_file = None
        self._attach_shared_memory()

        # POSIX 信号量（默认启用，如果C端支持）
        self._sem_ready = None
        self._sem_ack = None
        self._sem_enabled = False
        # semaphore wait timeout (seconds) - can be overridden by env for tuning
        try:
            self._sem_timeout = float(os.environ.get("LOH_SEM_TIMEOUT_S", "1.0"))
        except Exception:
            self._sem_timeout = 1.0
        self._sem_disabled_logged = False
        self._last_sem_timeout_log = 0.0
        # 显式读取 LOH_DISABLE_FSYNC，使其在有/无信号量两条路径下都生效
        # 默认为 False（即默认会调用 fsync）
        self._disable_fsync = _env_flag("LOH_DISABLE_FSYNC", False)
        disable_override = os.environ.get("LOH_DISABLE_SEMAPHORE")
        enable_override = os.environ.get("LOH_ENABLE_SEMAPHORE")
        if disable_override is not None:
            # disable=1 表示强制关闭
            self._sem_requested = not _env_flag("LOH_DISABLE_SEMAPHORE", False)
        elif enable_override is not None:
            self._sem_requested = _env_flag("LOH_ENABLE_SEMAPHORE", True)
        else:
            self._sem_requested = True
        self._init_semaphores()
        # 初始化轮询睡眠参数（微秒）
        # LOH_POLL_SLEEP_US: 主线程轮询间隔（微秒），默认 200 (0.2ms)
        try:
            self._poll_sleep_us = int(os.environ.get("LOH_POLL_SLEEP_US", "200"))
        except Exception:
            self._poll_sleep_us = 200

        # 允许禁用每次写入后的文件同步以降低系统调用开销（仅在你确信文件可见性不是问题时使用）
        # 上面已统一读取 LOH_DISABLE_FSYNC，为安全起见在此再次确保该属性存在
        if not hasattr(self, '_disable_fsync'):
            self._disable_fsync = _env_flag("LOH_DISABLE_FSYNC", False)

        if not self._sem_enabled:
            # 允许后续轮询路径打印一次提示
            self._sem_disabled_logged = False

        # 轮询统计：用于输出是否仍在轮询
        self._poll_fallback_count = 0
        self._poll_last_log_ts = 0.0

        # 3. 初始化环境参数（使用传入的权重参数）
        self.reward_alpha = miss_ratio_weight      # miss ratio权重
        self.reward_beta = byte_miss_ratio_weight  # byte miss ratio权重
        self.max_episode_steps = 512
        self.current_step = 0
        self.weight_update_count = 0
        self.episode_count = 0
        self.last_state_version = 0
        self._training_mode = threading.Event()
        # 训练/推理状态管理
        self._last_step_ack_time = 0.0
        # 存储上次使用的权重，用于reset时快速响应
        self._last_weights = np.ones(FEATURE_DIM, dtype=np.float32) / FEATURE_DIM  # 初始均匀分布

        # 【新增】用于事后惩罚的 model 引用
        self.model = None

    # BG线程配置（暂时禁用，仅保留注释用于排查需要时快速恢复）
    # try:
    #     self._bg_sleep_us = int(os.environ.get("LOH_BG_SLEEP_US", "200"))
    # except Exception:
    #     self._bg_sleep_us = 200
    # try:
    #     self._bg_emergency_threshold = float(os.environ.get("LOH_BG_EMERGENCY_THRESHOLD", "0.050"))
    # except Exception:
    #     self._bg_emergency_threshold = 0.050
    # self._bg_emergency_ack = _env_flag("LOH_BG_EMERGENCY_ACK", True)
    # self._bg_loop_counter = 0
    # self._bg_last_heartbeat = get_monotonic_time()
    # self._bg_ready_seen_version = -1
    # self._bg_ready_seen_t = 0.0
    # self._bg_last_acked_version = -1
    # self._last_weights = np.zeros(FEATURE_DIM, dtype=np.float64)
    # self._stop_bg = False
    # self._bg_thread = threading.Thread(target=self._ipc_background_pump, name="loh-bg", daemon=True)
    # self._bg_thread.start()

        print("✅ LohEnv initialization completed (fast version)")
        if LOH_DEBUG_BASIC():
            print(
                "   Reward weight config: miss_ratio_weight="
                f"{self.reward_alpha:.3f}, byte_miss_ratio_weight={self.reward_beta:.3f}"
            )
            print(
                "   IPC config: semaphore_requested="
                f"{int(self._sem_requested)}, poll_sleep_us={self._poll_sleep_us}"
            )

        # 计算结构字段偏移，便于对单字段进行原子式写入，避免整块覆盖造成竞态
        try:
            self._offset_is_training = SharedMemoryData.is_training.offset
            self._offset_ready_for_inference = SharedMemoryData.ready_for_inference.offset
            self._offset_weights_updated = SharedMemoryData.weights_updated.offset
            self._offset_ack_version = SharedMemoryData.ack_version.offset
            self._offset_state_version = SharedMemoryData.state_version.offset
        except Exception:
            # 在部分ctypes实现上不可用时，退化为整块写，但仍尽量减少写入频率
            self._offset_is_training = None

        # 默认开启推理模式，确保is_training=0
        self._set_training_mode(False)

    def _attach_shared_memory(self):
        """连接到共享内存"""
        try:
            shm_path = f"/dev/shm/loh_ac_{self.shm_key}"
            expected_size = ctypes.sizeof(SharedMemoryData)

            if not os.path.exists(shm_path):
                with open(shm_path, 'wb') as f:
                    f.write(b'\x00' * expected_size)

            # 如果已存在但大小与期望不符，则调整大小
            if os.path.exists(shm_path):
                try:
                    current_size = os.path.getsize(shm_path)
                    if current_size != expected_size:
                        with open(shm_path, 'r+b') as f:
                            f.truncate(expected_size)
                except Exception:
                    pass
            self.shm_file = open(shm_path, 'r+b')
            self.shm = mmap.mmap(self.shm_file.fileno(), expected_size)
            os.chmod(shm_path, 0o666)  # 确保权限
            print(f"✅ Shared memory connected: {shm_path}")

        except Exception as e:
            print(f"❌ Shared memory connection failed: {e}")
            raise

    def _init_semaphores(self):
        """初始化命名信号量，若失败则回退至轮询模式"""
        # 先释放已有句柄，避免重复打开
        self._disable_semaphores()

        if not getattr(self, "_sem_requested", True):
            if LOH_DEBUG_BASIC():
                print("[SEM] semaphore mode disabled via configuration; using polling only")
            return

        ready_name = f"/loh_ac_ready_{self.shm_key}".encode()
        ack_name = f"/loh_ac_ack_{self.shm_key}".encode()

        sem_ready = libc.sem_open(ready_name, os.O_CREAT, 0o666, 0)
        if sem_ready == SEM_FAILED:
            err = ctypes.get_errno()
            if LOH_DEBUG_BASIC():
                print(f"[SEM] sem_open ready failed: {os.strerror(err)}")
            return

        sem_ack = libc.sem_open(ack_name, os.O_CREAT, 0o666, 0)
        if sem_ack == SEM_FAILED:
            err = ctypes.get_errno()
            if LOH_DEBUG_BASIC():
                print(f"[SEM] sem_open ack failed: {os.strerror(err)}")
            libc.sem_close(sem_ready)
            return

        self._sem_ready = sem_ready
        self._sem_ack = sem_ack
        self._sem_enabled = True

        # 清理残留计数，避免历史脏数据
        self._sem_drain(self._sem_ready)
        self._sem_drain(self._sem_ack)

        if LOH_DEBUG_BASIC():
            print("[SEM] POSIX semaphore handshake enabled")

    def _disable_semaphores(self, reason: Optional[str] = None):
        if reason and LOH_DEBUG_BASIC():
            print("[SEM] disable semaphore mode: %s" % reason)

        if self._sem_ready is not None:
            libc.sem_close(self._sem_ready)
            self._sem_ready = None
        if self._sem_ack is not None:
            libc.sem_close(self._sem_ack)
            self._sem_ack = None

        self._sem_enabled = False
        self._sem_disabled_logged = True

    def _sem_drain(self, sem_handle):
        if not self._sem_enabled or sem_handle is None:
            return

        while True:
            res = libc.sem_trywait(sem_handle)
            if res == 0:
                continue
            err = ctypes.get_errno()
            if err == errno.EINTR:
                continue
            if err == errno.EAGAIN:
                break
            self._disable_semaphores(f"sem_trywait error: {os.strerror(err)}")
            break

    def _sem_wait(self, sem_handle, timeout_s: Optional[float], label: Optional[str] = None) -> bool:
        if not self._sem_enabled or sem_handle is None:
            return False

        if timeout_s is None:
            deadline_ts = None
        else:
            deadline = time.time() + timeout_s
            deadline_sec = int(deadline)
            deadline_nsec = int((deadline - deadline_sec) * 1e9)
            deadline_ts = Timespec(deadline_sec, deadline_nsec)

        while True:
            if deadline_ts is None:
                res = libc.sem_wait(sem_handle)
            else:
                res = libc.sem_timedwait(sem_handle, ctypes.byref(deadline_ts))

            if res == 0:
                if LOH_DEBUG_BASIC():
                    suffix = f" {label}" if label else ""
                    print(f"[SEM][Python] sem_wait success{suffix}")
                return True

            err = ctypes.get_errno()
            if err == errno.EINTR:
                continue
            if timeout_s is not None and err == errno.ETIMEDOUT:
                now = get_monotonic_time()
                if LOH_DEBUG_BASIC() and (now - self._last_sem_timeout_log) > 0.5:
                    suffix = f" {label}" if label else ""
                    print(f"[SEM][Python] sem_wait timeout{suffix}, switching to polling")
                    self._last_sem_timeout_log = now
                return False

            self._disable_semaphores(f"sem_wait error: {os.strerror(err)}")
            return False

    def _sem_post(self, sem_handle, label: Optional[str] = None):
        if not self._sem_enabled or sem_handle is None:
            return

        res = libc.sem_post(sem_handle)
        if res != 0:
            err = ctypes.get_errno()
            self._disable_semaphores(f"sem_post error: {os.strerror(err)}")
        elif LOH_DEBUG_VERBOSE() and label:
            print(f"[SEM][Python] sem_post {label}")

    def _read_shm(self):
        """快速读取共享内存"""
        try:
            read_start = get_monotonic_time()

            self.shm.seek(0)
            raw_data = self.shm.read(ctypes.sizeof(SharedMemoryData))
            data = SharedMemoryData.from_buffer_copy(raw_data)

            read_end = get_monotonic_time()
            read_duration = read_end - read_start

            # 获取绝对时间戳
            current_timestamp = get_monotonic_time()
            if LOH_DEBUG_VERBOSE() and read_duration > 0.001:  # 只打印超1ms的读取
                print(f"[{current_timestamp:.6f}] read memory span {read_duration:.6f} seconds")

            return data
        except Exception as e:
            if LOH_DEBUG_BASIC():
                print(f"❌ read shared memory failed: {e}")
            return None

    def _read_penalty_data(self, data=None):
        """
        从共享内存文件读取 penalty 数据（扩展区域）

        参数:
            data: 可选，已读取的 SharedMemoryData 对象。如果为 None，则重新读取。

        返回: List[PenaltyEntry] 或 []
        """
        try:
            # 1. 先读取 shm_data_t 获取 pending_penalty_count（如果未提供）
            if data is None:
                data = self._read_shm()
            if data is None or data.pending_penalty_count <= 0:
                if LOH_DEBUG_BASIC() and data is not None:
                    print(f"[Python←C] 📭 No penalties (pending_penalty_count={data.pending_penalty_count})")
                return []

            penalty_count = data.pending_penalty_count

            # 2. 计算 penalty 数据起始偏移
            shm_data_size = ctypes.sizeof(SharedMemoryData)
            penalty_entry_size = ctypes.sizeof(PenaltyEntry)
            offset = shm_data_size

            if LOH_DEBUG_BASIC():
                print(f"[Python←C] 📥 Reading {penalty_count} penalties from offset {offset} "
                      f"(shm_data_size={shm_data_size}, penalty_entry_size={penalty_entry_size})")

            # 【关键修复】重新打开文件以获取C端刚写入的扩展数据
            # 原因：文件缓存可能导致无法读取到C端通过fwrite扩展的内容
            # 必须重新打开文件才能看到最新的文件大小和内容
            shm_path = f"/dev/shm/loh_ac_{self.shm_key}"
            try:
                # 临时打开文件读取 penalty 数据
                with open(shm_path, 'rb') as fresh_file:
                    fresh_file.seek(offset)
                    penalties = []
                    for i in range(penalty_count):
                        penalty_bytes = fresh_file.read(penalty_entry_size)
                        if len(penalty_bytes) < penalty_entry_size:
                            print(f"[Python][ERROR] ❌ Incomplete penalty data at index {i}: "
                                  f"got {len(penalty_bytes)}/{penalty_entry_size} bytes")
                            print(f"[Python][DEBUG] File size: {fresh_file.tell()}, expected offset: {offset + (i+1)*penalty_entry_size}")
                            break

                        penalty = PenaltyEntry.from_buffer_copy(penalty_bytes)
                        penalties.append(penalty)
            except Exception as read_error:
                print(f"[Python][ERROR] Failed to reopen file for penalty reading: {read_error}")
                return []

            # 4. 打印前 5 个 penalty 的详细信息（调试用）
            if LOH_DEBUG_BASIC() and len(penalties) > 0:
                print(f"[Python←C] ✅ Successfully read {len(penalties)} penalties:")
                print_count = min(5, len(penalties))
                for i in range(print_count):
                    p = penalties[i]
                    print(f"[Python←C]   📋 penalty[{i}]: version={p.penalty_version}, "
                          f"evict_to_access={p.eviction_to_access}, "
                          f"size={p.obj_size}, obj_id={p.obj_id}")
                if len(penalties) > 5:
                    print(f"[Python←C]   ... ({len(penalties) - 5} more penalties)")

            return penalties

        except Exception as e:
            if LOH_DEBUG_BASIC():
                print(f"[Python][ERROR] Failed to read penalty data: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _write_shm(self, data_struct):
        """快速写入共享内存，并强制同步到磁盘，确保C端可见"""
        try:
            raw_data = ctypes.string_at(ctypes.byref(data_struct), ctypes.sizeof(data_struct))
            self.shm.seek(0)
            self.shm.write(raw_data)
            self.shm.flush()
            # 强制同步到磁盘，避免C端读到旧内容（可通过环境变量关闭以减少系统调用）
            if self.shm_file is not None and not getattr(self, "_disable_fsync", False):
                import os
                os.fsync(self.shm_file.fileno())
            return True
        except Exception as e:
            if LOH_DEBUG_BASIC():
                print(f"❌ write shared memory failed: {e}")
            return False

    def _write_field_int32(self, offset, value):
        """仅写入一个4字节整型字段，避免整块覆盖导致的竞态"""
        try:
            if offset is None:
                return False
            self.shm.seek(offset)
            # 按C的int32写入（小端）
            self.shm.write(int(value).to_bytes(4, byteorder=sys.byteorder, signed=True))
            self.shm.flush()
            # 确保立即同步到磁盘，让C端能立即读取
            if hasattr(self.shm, 'fileno'):
                os.fsync(self.shm.fileno())
            return True
        except Exception:
            return False

    def _update_is_training(self, value: int):
        """更新is_training标志，优先使用字段写入，失败时回退整块写"""
        value = 1 if value else 0
        if self._write_field_int32(self._offset_is_training, value):
            return
        data = self._read_shm()
        if not data:
            return
        data.is_training = value
        self._write_shm(data)

    def _set_training_mode(self, enabled: bool):
        """切换训练模式，同时更新共享内存中的is_training标志"""
        if enabled:
            if not self._training_mode.is_set():
                ts = get_monotonic_time()
                self._training_mode.set()
                self._update_is_training(1)  # 训练中：is_training=1
                if LOH_DEBUG_BASIC():
                    print(f"[{ts:.6f}] _set_training_mode(True) - is_training=1 written")
        else:
            if self._training_mode.is_set():
                ts = get_monotonic_time()
                self._training_mode.clear()
                self._update_is_training(0)  # 空闲：is_training=0
                if LOH_DEBUG_BASIC():
                    print(f"[{ts:.6f}] _set_training_mode(False) - is_training=0 written")

    def reset(self, seed=None, options=None):
        """重置环境"""
        super().reset(seed=seed)

        reset_start = get_monotonic_time()
        if LOH_DEBUG_BASIC():
            print(f"[{reset_start:.6f}] 🔄 Episode #{self.episode_count + 1} Reset started")

        self.current_step = 0
        self.episode_count += 1

        wait_start = get_monotonic_time()
        if LOH_DEBUG_BASIC():
            print(f"[{wait_start:.6f}] 🔄 Episode #{self.episode_count} Reset - Checking for existing state from C...")

        # 无限等待初始 ready 状态，不再使用10秒回退零状态；每2秒打印一次心跳
        timeout_counter = 0
        heartbeat_every = 4000  # 约2秒（4000 x 0.5ms）
        initial_data = None
        while True:
            data = self._read_shm()
            # 若收到终止信号，立刻中断训练，走主流程的优雅退出
            if data and data.terminate == 1:
                raise KeyboardInterrupt("Terminate signal received in reset() via shared memory")
            if data and data.ready_for_inference:
                initial_data = data
                found_time = get_monotonic_time()
                if LOH_DEBUG_BASIC():
                    print(f"[{found_time:.6f}] Reset found initial state [seq {int(data.state_version)}], waited {found_time - wait_start:.6f}s")
                break
            # 告知C端：Python此时处于等待初始状态的状态
            # 训练状态由回调函数管理，这里无需设置
            pass
            waited_sem = False
            if self._sem_enabled:
                waited_sem = self._sem_wait(self._sem_ready, self._sem_timeout, label="ready@reset")
                if waited_sem:
                    if LOH_DEBUG_VERBOSE():
                        print("[SEM][Python] reset() resumed via semaphore")
                    continue
            elif LOH_DEBUG_BASIC() and not self._sem_disabled_logged:
                print("[SEM][Python] semaphore not enabled, using polling mode in reset()")
                self._sem_disabled_logged = True
            if not waited_sem:
                self._poll_fallback_count += 1
                if LOH_DEBUG_VERBOSE():
                    print(
                        f"[POLL][Python] reset() waiting via polling (fallback_count={self._poll_fallback_count})"
                    )
            time.sleep(self._poll_sleep_us / 1e6)  # poll sleep (configurable)
            timeout_counter += 1
            if timeout_counter % heartbeat_every == 0:  # 每2秒报告一次
                elapsed_time = timeout_counter * 0.0005
                now = get_monotonic_time()
                if LOH_DEBUG_VERBOSE():
                    print(f"[{now:.6f}] reset() waiting for initial state... waited {elapsed_time:.1f}s")

        # 收到初始状态，由回调函数管理训练状态

        initial_observation = np.array(initial_data.state, dtype=np.float32)
        # 从 state[0] 和 state[1] 获取全局特征（obj_hit_ratio 和 byte_hit_ratio）
        # 注意：C 端存储的是 hit_ratio，miss_ratio = 1 - hit_ratio
        initial_miss_ratio = 1.0 - initial_observation[0]  # state[0] 是 obj_hit_ratio
        initial_byte_miss_ratio = 1.0 - initial_observation[1]  # state[1] 是 byte_hit_ratio

        # 清除历史性能指标
        if hasattr(self, '_previous_miss_ratio'):
            delattr(self, '_previous_miss_ratio')
        if hasattr(self, '_previous_byte_miss_ratio'):
            delattr(self, '_previous_byte_miss_ratio')

        print(f"✅ Episode #{self.episode_count} Reset Complete:")
        print(f"   [seq {int(initial_data.state_version)}] Initial state aligned (state_version)")
        print(f"   Initial miss_ratio: {initial_miss_ratio:.4f}")
        print(f"   Initial byte_miss_ratio: {initial_byte_miss_ratio:.4f}")
        print(f"   State vector shape: {initial_observation.shape}")

        # 【新增】输出状态向量详细信息 - 与C端格式一致
        if LOH_DEBUG_VERBOSE():
            if CONTEXT_DIM == 26:
                print(f"[global_features]: [{initial_observation[0]:.6f}, {initial_observation[1]:.6f}]")
                request_features = ", ".join([f"{initial_observation[i]:.6f}" for i in range(2, 26)])
                print(f"[request_features]: [{request_features}]")
                # 候选特征（如启用 +72 维）
                try:
                    base_dim = 26
                    cand_dim = CONTEXT_DIM - base_dim
                    if cand_dim >= 72 and len(initial_observation) >= base_dim + 72:
                        cand_slice = initial_observation[base_dim:base_dim + 72]
                        print(f"[candidate_features]: [{', '.join([f'{x:.6f}' for x in cand_slice])}]")
                except Exception:
                    pass
            elif CONTEXT_DIM == 38:
                print(f"[global_features]: [{initial_observation[0]:.6f}, {initial_observation[1]:.6f}]")
                request_features = ", ".join([f"{initial_observation[i]:.6f}" for i in range(2, 26)])
                print(f"[request_features]: [{request_features}]")
                cache_features = ", ".join([f"{initial_observation[i]:.6f}" for i in range(26, 38)])
                print(f"[cache_features]: [{cache_features}]")
                # 候选特征（如启用 +72 维）
                try:
                    base_dim = 38
                    cand_dim = CONTEXT_DIM - base_dim
                    if cand_dim >= 72 and len(initial_observation) >= base_dim + 72:
                        cand_slice = initial_observation[base_dim:base_dim + 72]
                        print(f"[candidate_features]: [{', '.join([f'{x:.6f}' for x in cand_slice])}]")
                except Exception:
                    pass

        # 记录当前状态版本，供下一步动作对齐
        self.last_state_version = int(initial_data.state_version)

        # 【重要】不在reset()中消费状态或发送ACK
        # 让step(1)去处理第一个状态，保持seq/step完全对齐

        # 训练状态现在由回调函数管理，reset只负责环境重置
        if LOH_DEBUG_BASIC():
            ts = get_monotonic_time()
            print(f"[{ts:.6f}] Reset completed - training state managed by callback")

        return initial_observation, {}

    def set_model(self, model):
        """
        设置 RL model 引用，用于访问 replay buffer 进行事后惩罚

        Args:
            model: SAC 模型实例
        """
        self.model = model
        if LOH_DEBUG_BASIC():
            print(f"[LohEnv] Model reference set, replay buffer available: {hasattr(model, 'replay_buffer')}")

    def step(self, action):
        """
        执行一步操作 - 与C端交互流程 (回调函数版本)

        训练状态管理已转移到SAC回调函数:
        ┌─────────────────────────────────────────────────────────────┐
        │ on_rollout_start() -> is_training=0 (推理阶段开始)         │
        │ env.step() × N次   -> 与C端正常通信                        │
        │ on_rollout_end()   -> is_training=1 (训练阶段开始)         │
        │ SAC.train()        -> C端使用缓存权重                       │
        │ 循环...                                                     │
        └─────────────────────────────────────────────────────────────┘

        流程概述：
        1. 将RL action转换为缓存权重（softmax归一化）
        2. 【等待C端发送状态】循环等待C端的ready_for_inference=1
        3. 【响应C端请求】写入权重 + ACK，清除ready标志
        4. 【等待C端反馈】等待C端应用权重后发送新状态
        5. 【计算奖励】根据新状态的miss_ratio计算reward
        6. 【返回】(observation, reward, terminated, truncated, info)
        """
        step_start = get_monotonic_time()
        if LOH_DEBUG_VERBOSE():
            print(f"[Step {self.current_step + 1}] [{step_start:.6f}] step started")

        self.current_step += 1

        # ========== 步骤1: 将RL动作转换为缓存权重 ==========
        # 默认：对动作向量做 softmax，得到正且和为 1 的权重；
        # 当 LOH_FEATURE_LOG1P 为真时：直接使用连续动作向量作为权重
        # （可为负数且不要求和为 1），便于配合 C 端 log1p(raw) 特征模式。
        action_start = get_monotonic_time()
        if LOH_FEATURE_LOG1P:
            weights = action.astype(np.float64)
        else:
            action_tensor = torch.from_numpy(action)
            weights = torch.nn.functional.softmax(action_tensor, dim=-1).numpy()
        action_end = get_monotonic_time()

        # 【新增】时间分解：推理时间（总是打印，不管多快）
        inference_duration = action_end - action_start
        if LOH_DEBUG_BASIC():
            print(f"[TIMING][Python] Model inference (softmax/raw): {inference_duration:.6f} seconds")

        if LOH_DEBUG_VERBOSE() and action_end - action_start > 0.001:
            print(f"[{action_end:.6f}] action conversion took {action_end - action_start:.6f} seconds")

        # ========== 步骤2: 等待C端发送状态（ready_for_inference=1）==========
        # C端会在每次缓存操作后更新状态，设置ready_for_inference=1
        # Python需要等待这个标志，然后才能写入新权重
        read_start = get_monotonic_time()
        data = self._read_shm()
        if data is None:
            raise RuntimeError("无法读取共享内存")

        write_start = get_monotonic_time()
        acked_version = None
        ack_weights_fmt = None
        polling_logged = False
        used_polling_this_step = False

        # 循环等待C端的ready_for_inference=1
        wait_loop_iterations = 0
        wait_loop_start = get_monotonic_time()
        while True:
            wait_loop_iterations += 1
            current = self._read_shm()
            if current is None:
                raise RuntimeError("无法读取共享内存用于写入")

            if current.terminate == 1:
                # 收到终止请求：立即中断训练主循环
                raise KeyboardInterrupt("Terminate signal received in step() while waiting to ack current ready state")

            if current.ready_for_inference == 1:
                wait_loop_end = get_monotonic_time()
                # 【新增】时间分解：等待 C 端发送状态的时间
                wait_for_ready_duration = wait_loop_end - wait_loop_start
                if LOH_DEBUG_BASIC():
                    print(f"[TIMING][Python] Wait for C ready: {wait_for_ready_duration:.6f} seconds ({wait_loop_iterations} iterations)")

                # ========== 步骤3: 写入权重并发送ACK ==========
                # 找到了C端的ready状态，现在写入权重并清除ready标志
                weight_write_start = get_monotonic_time()
                for i in range(FEATURE_DIM):
                    current.weights[i] = float(weights[i])

                # 保存权重供下次reset使用
                self._last_weights = weights.copy()

                acked_version = int(current.state_version)
                self.last_state_version = acked_version
                current.ack_version = int(current.state_version)
                current.weights_updated = 1
                current.ready_for_inference = 0  # 清除ready标志，表示已处理
                # 根据当前训练模式设置 is_training
                current.is_training = 1 if self._training_mode.is_set() else 0

                # 【新增】时间分解：写入共享内存的时间
                shm_write_start = get_monotonic_time()
                self._write_shm(current)
                shm_write_end = get_monotonic_time()

                # 通过信号量通知C端"权重已更新"
                sem_post_start = get_monotonic_time()
                if self._sem_enabled and LOH_DEBUG_VERBOSE():
                    print(f"[SEM][Python] posting ack semaphore for seq {acked_version}")
                self._sem_post(self._sem_ack, label=f"ack seq {acked_version}")
                sem_post_end = get_monotonic_time()

                weight_write_end = get_monotonic_time()
                # 【新增】时间分解：详细打印各环节耗时
                total_write_duration = weight_write_end - weight_write_start
                shm_write_duration = shm_write_end - shm_write_start
                sem_post_duration = sem_post_end - sem_post_start
                if LOH_DEBUG_BASIC():
                    print(f"[TIMING][Python] Write weights total: {total_write_duration:.6f} seconds (shm: {shm_write_duration:.6f}, sem_post: {sem_post_duration:.6f})")

                # 打印实际写入的权重
                ack_weights_fmt = ", ".join([f"{float(weights[i]):.3f}" for i in range(FEATURE_DIM)])
                if LOH_DEBUG_VERBOSE():
                    print(f"[seq {acked_version}] Python weights written -> [Written weights]: [{ack_weights_fmt}]")
                self._last_step_ack_time = get_monotonic_time()
                data = current
                break  # ACK完成，退出循环

            # 使用信号量或轮询等待C端发送状态
            waited_via_sem = False
            if self._sem_enabled:
                waited_via_sem = self._sem_wait(self._sem_ready, self._sem_timeout, label="ready@step")
                if waited_via_sem:
                    if LOH_DEBUG_VERBOSE():
                        print("[SEM][Python] step() resumed via semaphore for ready state")
                    continue
            elif LOH_DEBUG_BASIC() and not self._sem_disabled_logged:
                print("[SEM][Python] semaphore not enabled, using polling mode in step() ready loop")
                self._sem_disabled_logged = True

            if not waited_via_sem:
                self._poll_fallback_count += 1
                now_poll = get_monotonic_time()
                used_polling_this_step = True
                if LOH_DEBUG_VERBOSE() and not polling_logged:
                    print(
                        f"[POLL][Python] step() waiting via polling (state_version={self.last_state_version})"
                    )
                    polling_logged = True
                    self._poll_last_log_ts = now_poll

            # 减少轮询间隔，更快响应
            time.sleep(self._poll_sleep_us / 1e6)
        write_end = get_monotonic_time()

        if used_polling_this_step and LOH_DEBUG_VERBOSE():
            print(f"[POLL][Python] step() handled ready via polling before seq {acked_version}")

        if LOH_DEBUG_VERBOSE():
            print(f"[Step {self.current_step}] Weights: {weights}")
            print(f"[{write_end:.6f}] weights write completed, total time {write_end - step_start:.6f} seconds")

        # ========== 步骤4: 等待C端应用权重并发送新状态 ==========
        # C端收到ACK后，会应用新权重，然后继续处理请求
        # 处理完下一个请求后，会发送新的状态（新的state_version）
        wait_start = get_monotonic_time()
        if LOH_DEBUG_VERBOSE():
            print(f"[{wait_start:.6f}] waiting for C-side response (expecting new version != {acked_version})")

        timeout_counter = 0
        # 连续超时检测：sem_timeout=1.0秒，10次连续超时=10秒
        max_consecutive_timeouts = 10  # 连续超时10次（10 × 1.0秒 = 10秒）则判断C端已结束
        consecutive_timeouts = 0

        # 心跳日志：让用户知道Python还在运行（每20次检查=20秒打印一次）
        heartbeat_interval_checks = 20  # 每20次检查（约20秒）报告一次心跳

        # 空闲检测：state_version/timestamp均无变化超过此时间，则认为C端挂死
        idle_threshold = 15.0  # 15秒无活动则退出
        check_idle_every = 5  # 每5次循环检查一次idle（减少开销）

        last_seen_version = acked_version
        last_seen_timestamp = None
        last_progress_t = wait_start

        # 循环等待C端发送新状态
        while True:
            # 优先使用信号量阻塞以避免轮询（若信号量不可用或超时则回退到轮询）
            sem_wait_used = False
            if self._sem_enabled:
                sem_wait_used = True
                waited_via_sem = self._sem_wait(self._sem_ready, self._sem_timeout, label="wait@newstate")
                if waited_via_sem:
                    # sem 被唤醒后直接读取共享内存并检查是否为期待的新版本
                    consecutive_timeouts = 0  # 【新增】成功等到信号，重置计数器
                    new_data = self._read_shm()
                    if new_data and new_data.terminate == 1:
                        raise KeyboardInterrupt("Terminate signal received in step() while waiting for new state version")
                    if new_data and new_data.ready_for_inference and (
                        acked_version is None or int(new_data.state_version) != acked_version
                    ):
                        data = new_data
                        wait_end = get_monotonic_time()
                        wait_duration = wait_end - wait_start
                        if LOH_DEBUG_VERBOSE():
                            print(f"[{wait_end:.6f}] [SEM][Python] C-side response (via sem) received, waited {wait_duration:.6f} seconds — [seq {int(new_data.state_version)}]")
                        break
                    # sem 唤醒但未得到新版本时，继续循环（可能为噪声或另一种事件）
                else:
                    # sem_wait 超时或出错 -> 回退到轮询检查（并计数）
                    consecutive_timeouts += 1  # 【修改】使用新的连续超时计数器
                    self._poll_fallback_count += 1

                    # 【新增】连续超时多次，很可能C端已结束，提前退出
                    if consecutive_timeouts >= max_consecutive_timeouts:
                        now = get_monotonic_time()
                        elapsed = now - wait_start
                        if LOH_DEBUG_BASIC():
                            print(f"\n{'='*70}")
                            print(f"⚠️  检测到C端可能已结束（连续 {consecutive_timeouts} 次信号量超时，共 {elapsed:.1f}秒）")
                            print(f"   每次超时: 1.0秒")
                            print(f"   最后确认的序列号: {acked_version}")
                            print(f"   说明: C端程序已正常结束或被中断（Ctrl+C）")
                            print(f"         Python端将优雅退出以保存训练进度")
                            print(f"{'='*70}\n")
                        raise KeyboardInterrupt(f"C-side program may have ended: {consecutive_timeouts} consecutive sem_wait timeouts ({elapsed:.1f}s), training stopped automatically")

                    if LOH_DEBUG_BASIC() and consecutive_timeouts <= 3:  # 只打印前3次，避免刷屏
                        print(f"[SEM][Python] wait@newstate timed out ({consecutive_timeouts}/{max_consecutive_timeouts}), falling back to polling (fallback_count={self._poll_fallback_count})")
                    new_data = self._read_shm()
            else:
                # 信号量不可用，使用轮询读取
                new_data = self._read_shm()

            # 下面统一处理轮询时的检测/心跳/退出逻辑
            if new_data and new_data.terminate == 1:
                raise KeyboardInterrupt("Terminate signal received in step() while waiting for new state version")

            if new_data and new_data.ready_for_inference and (
                acked_version is None or int(new_data.state_version) != acked_version
            ):
                data = new_data
                wait_end = get_monotonic_time()
                wait_duration = wait_end - wait_start
                if LOH_DEBUG_VERBOSE():
                    print(f"[{wait_end:.6f}] [POLL][Python] C-side response received, waited {wait_duration:.6f} seconds (checked {timeout_counter} times) — [seq {int(new_data.state_version)}]")
                break

            # 【优化】定期检查空闲超时（不是每次循环都检查）
            if timeout_counter % check_idle_every == 0:
                # 记录进展（用于检测C端是否挂死）
                if new_data:
                    if last_seen_timestamp is None:
                        last_seen_timestamp = int(new_data.timestamp)
                    if int(new_data.state_version) != int(last_seen_version) or int(new_data.timestamp) != int(last_seen_timestamp):
                        last_seen_version = int(new_data.state_version)
                        last_seen_timestamp = int(new_data.timestamp)
                        last_progress_t = get_monotonic_time()

                # 检查是否超过空闲阈值
                now = get_monotonic_time()
                if (now - last_progress_t) > idle_threshold:
                    if LOH_DEBUG_BASIC():
                        print(f"\n{'='*70}")
                        print(f"⚠️  检测到C端无响应（{now - last_progress_t:.1f}秒无活动）")
                        print(f"   state_version和timestamp均未变化")
                        print(f"   最后确认的序列号: {acked_version}")
                        print(f"{'='*70}\n")
                    raise KeyboardInterrupt(f"C-side program may have ended: no activity for {now - last_progress_t:.1f}s (state_version/timestamp unchanged), training stopped automatically")

            time.sleep(self._poll_sleep_us / 1e6)

            timeout_counter += 1

            if timeout_counter % heartbeat_interval_checks == 0:
                now = get_monotonic_time()
                elapsed = now - wait_start
                if LOH_DEBUG_VERBOSE():
                    print(
                        f"[POLL][Python] waiting for new state — waited {elapsed:.3f}s (expect version != {acked_version})"
                    )

        # is_training 状态已在 ACK 阶段同步到训练/推理模式，此处无需额外处理

        # 6. 使用状态作为新观测
        new_observation = np.array(data.state, dtype=np.float32)

        # 【修改】从 state 的前两个元素获取 global_features（命中率）
        # state[0] = obj_hit_ratio, state[1] = byte_hit_ratio
        obj_hit_ratio = float(new_observation[0])
        byte_hit_ratio = float(new_observation[1])

        # 获取驱逐统计
        total_evicted_bytes = data.total_evicted_bytes
        total_evicted_count = data.total_evicted_count

        if LOH_DEBUG_VERBOSE():
            print(f"[Step {self.current_step}] State info:")
            print(f"  obj_hit_ratio (state[0]): {obj_hit_ratio:.6f}")
            print(f"  byte_hit_ratio (state[1]): {byte_hit_ratio:.6f}")
            print(f"  total_evicted_bytes: {total_evicted_bytes}")
            print(f"  total_evicted_count: {total_evicted_count}")

        #【新增】输出状态向量详细信息 - 与C端格式一致
        if LOH_DEBUG_VERBOSE():
            if CONTEXT_DIM == 26:
                # 26维状态向量输出
                print(f"[global_features]: [{new_observation[0]:.6f}, {new_observation[1]:.6f}]")
                request_features = ", ".join([f"{new_observation[i]:.6f}" for i in range(2, 26)])
                print(f"[request_features]: [{request_features}]")
                # 候选特征（如启用 +72 维）
                try:
                    base_dim = 26
                    cand_dim = CONTEXT_DIM - base_dim
                    if cand_dim >= 72 and len(new_observation) >= base_dim + 72:
                        cand_slice = new_observation[base_dim:base_dim + 72]
                        print(f"[candidate_features]: [{', '.join([f'{x:.6f}' for x in cand_slice])}]")
                except Exception:
                    pass
            elif CONTEXT_DIM == 38:
                # 38维状态向量输出
                print(f"[global_features]: [{new_observation[0]:.6f}, {new_observation[1]:.6f}]")
                request_features = ", ".join([f"{new_observation[i]:.6f}" for i in range(2, 26)])
                print(f"[request_features]: [{request_features}]")
                cache_features = ", ".join([f"{new_observation[i]:.6f}" for i in range(26, 38)])
                print(f"[cache_features]: [{cache_features}]")
                # 候选特征（如启用 +72 维）
                try:
                    base_dim = 38
                    cand_dim = CONTEXT_DIM - base_dim
                    if cand_dim >= 72 and len(new_observation) >= base_dim + 72:
                        cand_slice = new_observation[base_dim:base_dim + 72]
                        print(f"[candidate_features]: [{', '.join([f'{x:.6f}' for x in cand_slice])}]")
                except Exception:
                    pass

        # 7. 【修改】计算初始奖励（基于global_features的加权命中率）
        # reward = alpha * obj_hit_ratio + beta * byte_hit_ratio
        # 最终奖励将在 ReplayBuffer 中通过惩罚延迟修正
        reward = self.reward_alpha * obj_hit_ratio + self.reward_beta * byte_hit_ratio

        if LOH_DEBUG_BASIC():
            print(f"[Step {self.current_step}] Initial reward: "
                  f"{self.reward_alpha:.3f} * {obj_hit_ratio:.6f} + "
                  f"{self.reward_beta:.3f} * {byte_hit_ratio:.6f} = {reward:.6f}")

        # 【优化】从扩展共享内存文件读取 penalty 数据（传入 data 避免重复读取）
        penalties = []
        if data.pending_penalty_count > 0:
            penalty_read_start = get_monotonic_time()
            penalties = self._read_penalty_data(data)  # 传入 data 参数
            penalty_read_end = get_monotonic_time()

            if LOH_DEBUG_BASIC():
                print(f"[TIMING][Python] Read penalty data: {penalty_read_end - penalty_read_start:.6f} seconds")
                print(f"\n[PENALTY] Received {len(penalties)} penalty entries from C-side:")

            # 获取replay buffer（如果存在）
            replay_buffer = None
            if hasattr(self, 'model') and self.model is not None:
                if hasattr(self.model, 'replay_buffer') and self.model.replay_buffer is not None:
                    replay_buffer = self.model.replay_buffer

            # 逐一处理每个惩罚
            for i, penalty_entry in enumerate(penalties):
                penalty_version = int(penalty_entry.penalty_version)
                eviction_to_access = int(penalty_entry.eviction_to_access)
                obj_size = int(penalty_entry.obj_size)
                obj_id = int(penalty_entry.obj_id)

                if LOH_DEBUG_BASIC():
                    print(f"[step→Process] 📋 Penalty #{i+1}: version={penalty_version}, "
                          f"evict_to_access={eviction_to_access}, "
                          f"size={obj_size}, obj_id={obj_id}")

                # 如果 replay buffer 存在，累积惩罚数据
                if replay_buffer is not None and hasattr(replay_buffer, 'retrospective_correct_reward'):
                    success = replay_buffer.retrospective_correct_reward(
                        penalty_version, eviction_to_access, obj_size)
                    if success:
                        if LOH_DEBUG_BASIC():
                            print(f"[step→Process] ✅ Accumulated for version {penalty_version}")
                    else:
                        if LOH_DEBUG_BASIC():
                            print(f"[step→Process] ⚠️ Version {penalty_version} not in buffer (overwritten)")
                elif LOH_DEBUG_BASIC():
                    print(f"[step→Process] ⚠️ Replay buffer unavailable, penalty skipped")

            # 清空惩罚队列（通知C端已处理）
            data.penalty_queue_size = 0
            self._write_shm(data)

            if LOH_DEBUG_BASIC():
                print(f"[PENALTY] All penalties processed and queue cleared\n")

        # 【新增】计算旧数据的最终奖励
        # 对于超过 exclude_recent_steps 的数据，计算最终奖励
        if hasattr(self, 'model') and self.model is not None:
            replay_buffer = getattr(self.model, 'replay_buffer', None)
            if (replay_buffer is not None and
                hasattr(replay_buffer, 'compute_final_rewards') and
                hasattr(replay_buffer, 'exclude_recent_steps')):

                buffer_size = replay_buffer.size()
                exclude_steps = replay_buffer.exclude_recent_steps

                # 只有当buffer中有足够数据时才计算
                if buffer_size > exclude_steps:
                    # 计算应该被最终化的范围
                    # 例如：buffer_size=500, exclude_steps=200
                    # 则应该最终化 [0, 300) 的数据
                    current_pos = replay_buffer.pos

                    # Buffer未满的情况：简单计算
                    if not replay_buffer.full:
                        finalize_end = max(0, current_pos - exclude_steps)
                        if finalize_end > 0:
                            replay_buffer.compute_final_rewards(0, finalize_end)
                    else:
                        # Buffer已满的情况：需要考虑环形
                        # 当前写入位置是 current_pos
                        # 排除区域是 [current_pos - exclude_steps, current_pos)
                        # 安全区域是其他所有位置

                        # 为简化，我们计算所有"老"数据
                        # 从 (current_pos) 到 (current_pos - exclude_steps - 1)
                        # 即环形buffer中不在排除窗口的部分

                        # 实际上，每次step只需要finalize刚刚离开排除窗口的那一个位置
                        # 即 current_pos - exclude_steps (mod buffer_size)
                        pos_to_finalize = (current_pos - exclude_steps) % replay_buffer.buffer_size
                        if not replay_buffer.reward_finalized[pos_to_finalize]:
                            replay_buffer.compute_final_rewards(pos_to_finalize, pos_to_finalize + 1)

        # 8. 【修改】不再保存 miss_ratio（已从共享内存移除）
        # self._previous_miss_ratio = new_miss_ratio
        # self._previous_byte_miss_ratio = new_byte_miss_ratio

        # 9. 检查终止条件
        terminated = (data.terminate == 1)
        # 【改进】移除truncated，连续运行不reset
        truncated = False  # 永不truncate，实现连续运行

        if terminated:
            if LOH_DEBUG_BASIC():
                print(f"[Step {self.current_step}] Episode ending - terminated by C-side signal")

        # 10. 返回信息（包含state_version用于ReplayBuffer映射）
        info = {
            'step': self.current_step,
            'obj_hit_ratio': obj_hit_ratio,  # 【新增】用于日志
            'byte_hit_ratio': byte_hit_ratio,  # 【新增】用于日志
            'total_evicted_bytes': total_evicted_bytes,  # 【新增】驱逐统计
            'total_evicted_count': total_evicted_count,  # 【新增】驱逐统计
            'state_version': int(data.state_version),  # 【新增】用于ReplayBuffer追踪
        }

        step_end = get_monotonic_time()
        total_duration = step_end - step_start
        if LOH_DEBUG_VERBOSE():
            print(f"[{step_end:.6f}] Step {self.current_step} completed, total duration {total_duration:.6f} seconds")
            print("=" * 50)

        return new_observation, reward, terminated, truncated, info

    # def _ipc_background_pump(self):
    #     """后台线程：仅在主线程未及时处理时做应急写入，当前已停用"""
    #     while not self._stop_bg:
    #         try:
    #             data = self._read_shm()
    #             if not data:
    #                 time.sleep(self._bg_sleep_us / 1e6)
    #                 continue
    #             if data.terminate == 1:
    #                 break
    #             now = get_monotonic_time()
    #             self._bg_loop_counter += 1
    #             if LOH_DEBUG_VERBOSE() and (now - self._bg_last_heartbeat) > 1.0:
    #                 print(
    #                     f"[BG][heartbeat] sem_enabled={self._sem_enabled} ready={int(data.ready_for_inference)} "
    #                     f"ack_version={int(data.ack_version)} poll_fallbacks={self._poll_fallback_count}"
    #                 )
    #                 self._bg_last_heartbeat = now
    #             if data.ready_for_inference == 1:
    #                 if self._training_mode.is_set():
    #                     if data.is_training != 1:
    #                         self._update_is_training(1)
    #                     continue
    #                 if int(data.state_version) != int(self._bg_ready_seen_version):
    #                     self._bg_ready_seen_version = int(data.state_version)
    #                     self._bg_ready_seen_t = now
    #                 elif self._bg_emergency_ack and (now - self._bg_ready_seen_t) > self._bg_emergency_threshold and int(data.state_version) != int(self._bg_last_acked_version):
    #                     for i in range(FEATURE_DIM):
    #                         data.weights[i] = float(self._last_weights[i])
    #                     data.ack_version = int(data.state_version)
    #                     data.weights_updated = 1
    #                     data.ready_for_inference = 0
    #                     data.is_training = 0
    #                     self._write_shm(data)
    #                     self._sem_post(self._sem_ack, label="bg emergency ack")
    #                     self._bg_last_acked_version = int(data.state_version)
    #                     if LOH_DEBUG_BASIC():
    #                         print(
    #                             f"[BG-FAST][seq {int(data.state_version)}] fast weights written (delay {now - self._bg_ready_seen_t:.3f}s)"
    #                         )
    #             if not self._training_mode.is_set() and data.is_training != 0:
    #                 if not self._write_field_int32(self._offset_is_training, 0):
    #                     data.is_training = 0
    #                     self._write_shm(data)
    #             elif self._training_mode.is_set() and data.is_training != 1:
    #                 self._update_is_training(1)
    #         except Exception:
    #             pass
    #         time.sleep(self._bg_sleep_us / 1e6)

    def close(self):
        """清理资源"""
        self._set_training_mode(False)
        # 停止后台线程（BG已停用，仅保留注释）
        # self._stop_bg = True
        # if hasattr(self, '_bg_thread') and self._bg_thread.is_alive():
        #     try:
        #         self._bg_thread.join(timeout=1.0)
        #     except Exception:
        #         pass

        # 关闭共享内存与文件
        if self.shm:
            try:
                self.shm.close()
            except Exception:
                pass
        if self.shm_file:
            try:
                self.shm_file.close()
            except Exception:
                pass
        self._disable_semaphores("env close")
        if LOH_DEBUG_BASIC():
            print("✅ resource environment cleaned up")

# ===== SAC 训练状态回调函数 =====
from stable_baselines3.common.callbacks import BaseCallback

class LOHTrainingCallback(BaseCallback):
    """LOH算法的训练状态回调 - 负责在正确时机通知C端训练状态"""

    def __init__(self, env_ref, verbose=1):
        super().__init__(verbose)
        self.env_ref = env_ref  # LohEnv环境引用
        self.rollout_count = 0
        self.step_count = 0

    def _get_timestamp(self):
        """获取高精度时间戳"""
        return get_monotonic_time()

    def _log_with_timestamp(self, message, level="INFO"):
        """带时间戳的日志输出"""
        ts = self._get_timestamp()
        if LOH_DEBUG_BASIC():
            print(f"[{ts:.6f}] [CALLBACK-{level}] {message}")

    def _on_training_start(self) -> None:
        """整个训练开始"""
        self._log_with_timestamp("=== SAC训练开始 ===", "START")
        self._log_with_timestamp("初始设置: is_training=1 (避免启动竞态条件)")
        # 初始设置为训练状态，避免启动时的竞态条件
        self.env_ref._update_is_training(1)

    def _on_rollout_start(self) -> None:
        """推理阶段开始 - 关键时机！"""
        self.rollout_count += 1
        self._log_with_timestamp(f">>> 推理阶段开始 (rollout #{self.rollout_count}) - 通知C端可以通信", "ROLLOUT")
        # 告诉C端现在是推理阶段，可以正常通信
        self.env_ref._set_training_mode(False)

    def _on_step(self) -> bool:
        """每个step后调用"""
        self.step_count += 1
        if self.step_count % 100 == 0:  # 每100步记录一次，避免日志过多
            self._log_with_timestamp(f"推理步骤: step #{self.step_count}", "STEP")

            # 调试：检查是否能访问到model和logger
            if LOH_DEBUG_BASIC() and self.step_count == 100:
                self._log_with_timestamp(f"Debug: hasattr(self, 'model')={hasattr(self, 'model')}", "DEBUG")
                self._log_with_timestamp(f"Debug: self.model is not None={self.model is not None if hasattr(self, 'model') else 'N/A'}", "DEBUG")
                self._log_with_timestamp(f"Debug: hasattr(self, 'logger')={hasattr(self, 'logger')}", "DEBUG")
                if hasattr(self, 'model') and self.model is not None:
                    self._log_with_timestamp(f"Debug: hasattr(model, 'replay_buffer')={hasattr(self.model, 'replay_buffer')}", "DEBUG")

            # 【新增】记录reward和penalty统计到TensorBoard
            if hasattr(self, 'model') and self.model is not None:
                buffer = getattr(self.model, 'replay_buffer', None)
                if buffer is not None and hasattr(buffer, 'rewards'):
                    # 计算最近100个样本的reward统计
                    recent_size = min(100, buffer.size())
                    if recent_size > 0:
                        if buffer.full:
                            start_idx = (buffer.pos - recent_size) % buffer.buffer_size
                            if start_idx + recent_size <= buffer.buffer_size:
                                recent_rewards = buffer.rewards[start_idx:start_idx + recent_size, 0]
                            else:
                                # 环形buffer跨界
                                part1 = buffer.rewards[start_idx:, 0]
                                part2 = buffer.rewards[:((start_idx + recent_size) % buffer.buffer_size), 0]
                                recent_rewards = np.concatenate([part1, part2])
                        else:
                            start_idx = max(0, buffer.pos - recent_size)
                            recent_rewards = buffer.rewards[start_idx:buffer.pos, 0]

                        # 记录到TensorBoard
                        self.logger.record("loh/reward_mean", float(np.mean(recent_rewards)))
                        self.logger.record("loh/reward_std", float(np.std(recent_rewards)))
                        self.logger.record("loh/reward_min", float(np.min(recent_rewards)))
                        self.logger.record("loh/reward_max", float(np.max(recent_rewards)))

                        if LOH_DEBUG_BASIC() and self.step_count == 100:
                            self._log_with_timestamp(f"Debug: Recorded reward stats to logger", "DEBUG")

                    # 记录penalty baseline
                    if hasattr(buffer, 'penalty_baseline'):
                        self.logger.record("loh/penalty_baseline", float(buffer.penalty_baseline))

                    # 记录reward corrections
                    if hasattr(buffer, 'reward_corrections'):
                        self.logger.record("loh/total_reward_corrections", int(buffer.reward_corrections))

                    # 手动触发logger dump（重要！）
                    self.logger.dump(step=self.num_timesteps)

        return True  # 继续训练

    def _on_rollout_end(self) -> None:
        """推理阶段结束 - 另一个关键时机！"""
        self._log_with_timestamp(f"<<< 推理阶段结束 (rollout #{self.rollout_count}) - 通知C端进入训练模式", "ROLLOUT")
        self._log_with_timestamp(f"本轮推理收集了 {self.env_ref.current_step} 步数据", "STATS")
        # 告诉C端即将进入训练阶段，使用缓存权重
        self.env_ref._set_training_mode(True)

    def _on_training_end(self) -> None:
        """整个训练结束"""
        self._log_with_timestamp("=== SAC训练结束 ===", "END")
        self._log_with_timestamp(f"总计完成 {self.rollout_count} 轮推理，{self.step_count} 个步骤", "STATS")
        # 训练结束，设置为空闲状态
        self.env_ref._set_training_mode(False)

def main():
    """主函数 - 使用SAC + 事后奖励修正"""

    # 解析命令行参数
    import argparse
    parser = argparse.ArgumentParser(description="LOH Actor-Critic with SAC (Retrospective Reward Correction)")
    parser.add_argument("--miss-ratio-weight", type=float, default=1.0,
                       help="Weight for miss ratio in reward calculation (default: 1.0)")
    parser.add_argument("--buffer-size", type=int, default=10000,
                       help="Replay buffer capacity (default: 10000, reduced for faster penalty coverage)")
    parser.add_argument("--learning-starts", type=int, default=1000,
                       help="Steps before training starts (default: 1000, should be >= batch_size)")
    parser.add_argument("--exclude-recent-steps", type=int, default=100,
                       help="Exclude recent N steps when sampling from replay buffer (default: 100, allow more penalties to arrive)")
    args = parser.parse_args()

    # 验证权重参数有效性
    if args.miss_ratio_weight < 0.0 or args.miss_ratio_weight > 1.0:
        print(f"error: miss-ratio-weight must be between 0.0 and 1.0, current value: {args.miss_ratio_weight}")
        sys.exit(1)

    byte_miss_ratio_weight = 1.0 - args.miss_ratio_weight

    # obj_penalty_weight 和 miss_ratio_weight 是同一个值（统一权重）
    obj_penalty_weight = args.miss_ratio_weight
    byte_penalty_weight = byte_miss_ratio_weight

    if LOH_DEBUG_BASIC():
        print("LOH RL Agent: Using SAC with Retrospective Reward Correction")
        print("26-dimensional state vector")
        print(f"Reward weights: miss_ratio={args.miss_ratio_weight:.3f}, byte_miss_ratio={byte_miss_ratio_weight:.3f}")
        print(f"Penalty weights: obj_penalty={obj_penalty_weight:.3f}, byte_penalty={byte_penalty_weight:.3f}")

    # 设置输出目录（使用环境变量RUN_TIMESTAMP以便与test_loh_rl_sb3.sh对齐）
    timestamp = os.environ.get("RUN_TIMESTAMP") or datetime.now().strftime("%m%d_%H%M%S")
    run_dir = f"./runs/{timestamp}"
    os.makedirs(run_dir, exist_ok=True)

    # TensorBoard目录
    tensorboard_log = os.path.join(run_dir, "tensorboard")
    os.makedirs(tensorboard_log, exist_ok=True)

    try:
        # 1. 实例化自定义环境
        env = LohEnv(miss_ratio_weight=args.miss_ratio_weight, byte_miss_ratio_weight=byte_miss_ratio_weight)

        # 2. 跳过环境检查
        if LOH_DEBUG_BASIC():
            print("⚡ skip environment check, directly start training")

        # 3. 实例化SAC模型（使用自定义ReplayBuffer）
        # SAC训练配置说明（针对RL update每200请求一次的场景）：
        # ⚠️ 关键理解：每一"步"(step) = 一次RL update = 约200个cache请求
        #
        # - buffer_size: 10000步 = 2M请求的数据
        # - learning_starts: 1000步 = 200K请求后开始训练
        # - exclude_recent_steps: 50步 = 最新10K请求不采样
        # - train_freq: 4 = 每4步（800请求）训练一次
        # - gradient_steps: 4 = 每次训练4个梯度步
        #
        # 惩罚延迟估计：
        # - Ghost cache miss通常在驱逐后20-100步内发生（4K-20K请求）
        # - exclude_recent_steps=50 足以覆盖大部分未修正数据
        #
        # 参数调优建议（见下方说明）
        model = SAC(
            "MlpPolicy",
            env,
            verbose=1,
            buffer_size=args.buffer_size,          # 默认10000
            learning_rate=3e-4,
            batch_size=256,
            tau=0.005,
            gamma=0.99,
            train_freq=4,                          # 【修改】每4步训练1次（不是每步）
            gradient_steps=4,                      # 【修改】每次训练4个steps（保持训练总量）
            learning_starts=args.learning_starts,  # 【修改】默认5000（原1000）
            tensorboard_log=tensorboard_log,       # 【新增】TensorBoard日志
            policy_kwargs=dict(
                net_arch=[256, 256],
                activation_fn=torch.nn.ReLU,
            ),
            replay_buffer_class=RetrospectiveReplayBuffer,  # 【关键】使用自定义buffer
            replay_buffer_kwargs=dict(
                exclude_recent_steps=args.exclude_recent_steps,  # 【新增】采样时排除最新N步
                obj_penalty_weight=obj_penalty_weight,           # 【修改】使用统一的对象权重
                byte_penalty_weight=byte_penalty_weight,         # 【修改】使用统一的字节权重
            ),
        )

        # 【新增】将model引用传递给env，使其能访问replay buffer
        env.set_model(model)
        if LOH_DEBUG_BASIC():
            print("✅ Model reference passed to environment for retrospective correction")

        # 4. 开始训练
        if LOH_DEBUG_BASIC():
            print("🧠 start SAC training with retrospective reward correction")
            print(f"📋 training configuration:")
            print(f"   - algorithm: SAC (off-policy)")
            print(f"   - state dimension: {CONTEXT_DIM}")
            print(f"   - action dimension: {FEATURE_DIM}")
            print(f"   - buffer size: {args.buffer_size}")
            print(f"   - learning starts: {args.learning_starts}")
            print(f"   - retrospective correction: ENABLED")

        # 记录训练开始时间
        training_start_time = datetime.now()
        if LOH_DEBUG_BASIC():
            print(f"⏰ training start time: {training_start_time.strftime('%Y-%m-%d %H:%M:%S')}")

        # 创建训练回调（用于 TensorBoard 日志记录）
        training_callback = LOHTrainingCallback(env_ref=env, verbose=1)

        model.learn(
            total_timesteps=int(1e12),  # 无限训练，直到C端终止
            callback=training_callback,
            progress_bar=True,
            log_interval=1,  # 每次训练更新都记录（从10改为1，获得更密集的train曲线）
        )

        # 5. 保存最终模型
        training_end_time = datetime.now()
        training_duration = training_end_time - training_start_time
        if LOH_DEBUG_BASIC():
            print(f"⏰ training end time: {training_end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"⌛ total training duration: {str(training_duration).split('.')[0]}")

        model.save(f"{run_dir}/sac_loh_final")
        if LOH_DEBUG_BASIC():
            print(f"💾 final model saved as {run_dir}/sac_loh_final.zip")

    except KeyboardInterrupt as e:
        training_end_time = datetime.now()
        if 'training_start_time' in locals():
            training_duration = training_end_time - training_start_time
            if LOH_DEBUG_BASIC():
                print(f"⏰ training interrupted time: {training_end_time.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"⌛ actual running time: {str(training_duration).split('.')[0]}")

        if LOH_DEBUG_BASIC():
            if "C端程序可能已结束" in str(e) or "Terminate signal received" in str(e):
                print(f"\n✅ C-side ends, training naturally terminates: {e}")
            else:
                print("\n⚠️  User interrupted training.")
        if 'model' in locals():
            model.save(f"{run_dir}/sac_loh_interrupted")
            if LOH_DEBUG_BASIC():
                print(f"💾 model saved as {run_dir}/sac_loh_interrupted.zip")
    except Exception as e:
        if LOH_DEBUG_BASIC():
            print(f"❌ fatal error occurred: {e}")

    finally:
        # 无论如何都打印结束时间（如果还没打印过）
        if 'training_start_time' in locals() and 'training_end_time' not in locals():
            final_end_time = datetime.now()
            final_duration = final_end_time - training_start_time
            if LOH_DEBUG_BASIC():
                print(f"⏰ training end time: {final_end_time.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"⌛ total running time: {str(final_duration).split('.')[0]}")

        if 'env' in locals() and env is not None:
            env.close()

if __name__ == "__main__":
    main()

# ===== SAC 主流程（保留但暂时注释） =====
'''
def main():
    """使用SAC算法的主入口，依赖stable-baselines3提供的训练/推理并行机制"""

    import argparse

    def _parse_ent_coef(raw: str):
        text = raw.strip()
        lowered = text.lower()
        if lowered == "auto" or lowered.startswith("auto_"):
            return text
        try:
            return float(text)
        except ValueError as exc:  # noqa: B904
            raise argparse.ArgumentTypeError(f"invalid entropy coefficient: {raw}") from exc

    parser = argparse.ArgumentParser(description="LOH Actor-Critic with SAC (stable-baselines3)")
    parser.add_argument("--miss-ratio-weight", type=float, default=1.0,
                        help="Weight for miss ratio in reward calculation (default: 1.0)")
    parser.add_argument("--buffer-size", type=int, default=65536,
                        help="Replay buffer capacity for SAC")
    parser.add_argument("--batch-size", type=int, default=256,
                        help="Gradient batch size sampled from the replay buffer")
    parser.add_argument("--learning-rate", type=float, default=3e-4,
                        help="Learning rate for both actor and critic optimizers")
    parser.add_argument("--gamma", type=float, default=0.99,
                        help="Discount factor for future rewards")
    parser.add_argument("--tau", type=float, default=0.005,
                        help="Soft update coefficient for target networks")
    parser.add_argument("--train-freq", type=int, default=1,
                        help="Environment steps between each SAC gradient update")
    parser.add_argument("--gradient-steps", type=int, default=1,
                        help="Number of gradient steps per training round")
    parser.add_argument("--learning-starts", type=int, default=100,
                        help="Warmup steps before SAC starts updating the networks (default: 100, reduced for more training)")
    parser.add_argument("--ent-coef", type=_parse_ent_coef, default="auto",
                        help="Entropy coefficient (float value or 'auto')")
    parser.add_argument("--target-update-interval", type=int, default=1,
                        help="How often (in gradient steps) to update target networks")
    parser.add_argument("--exclude-recent-steps", type=int, default=20,
                        help="Exclude recent N steps when sampling from replay buffer (default: 20, reduced for more training data)")
    parser.add_argument("--reward-exponent", type=float, default=5.0,
                        help="Exponent for reward calculation (default: 5.0)")
    parser.add_argument("--tensorboard-log", type=str, default="",
                        help="Optional TensorBoard log directory")
    args = parser.parse_args()

    if args.miss_ratio_weight < 0.0 or args.miss_ratio_weight > 1.0:
        print(f"error: miss-ratio-weight must be between 0.0 and 1.0, current value: {args.miss_ratio_weight}")
        sys.exit(1)

    byte_miss_ratio_weight = 1.0 - args.miss_ratio_weight

    # obj_penalty_weight 和 miss_ratio_weight 是同一个值（统一权重）
    obj_penalty_weight = args.miss_ratio_weight
    byte_penalty_weight = byte_miss_ratio_weight

    if LOH_DEBUG_BASIC():
        print("LOH RL Agent: Using 26-dimensional state vector")
        print(f"Reward weights: miss_ratio={args.miss_ratio_weight:.3f}, byte_miss_ratio={byte_miss_ratio_weight:.3f}")
        print(f"Penalty weights: obj_penalty={obj_penalty_weight:.3f}, byte_penalty={byte_penalty_weight:.3f}")
        print("SAC hyper-parameters:")
        print(f"  buffer_size={args.buffer_size}, batch_size={args.batch_size}, learning_rate={args.learning_rate}")
        print(f"  train_freq={args.train_freq}, gradient_steps={args.gradient_steps}, learning_starts={args.learning_starts}")

    timestamp = datetime.now().strftime("%m%d_%H%M%S")
    run_dir = f"./runs/{timestamp}"
    os.makedirs(run_dir, exist_ok=True)

    if args.tensorboard_log:
        tensorboard_log = args.tensorboard_log
    else:
        tensorboard_log = os.path.join(run_dir, "tensorboard")
    os.makedirs(tensorboard_log, exist_ok=True)

    logger_dir = os.path.join(run_dir, "sb3_logs")
    os.makedirs(logger_dir, exist_ok=True)

    env = None
    model = None
    training_start_time = None
    try:
        env = LohEnv(miss_ratio_weight=args.miss_ratio_weight, byte_miss_ratio_weight=byte_miss_ratio_weight)

        if LOH_DEBUG_BASIC():
            print("🚀 SAC agent initialized, relying on SB3 for asynchronous training updates")

        model = SAC(
            "MlpPolicy",
            env,
            verbose=1 if LOH_DEBUG_BASIC() else 0,
            buffer_size=args.buffer_size,
            batch_size=args.batch_size,
            gamma=args.gamma,
            tau=args.tau,
            learning_rate=args.learning_rate,
            train_freq=(args.train_freq, "step"),
            gradient_steps=args.gradient_steps,
            learning_starts=args.learning_starts,
            ent_coef=args.ent_coef,
            target_update_interval=args.target_update_interval,
            tensorboard_log=tensorboard_log,
            policy_kwargs=dict(
                net_arch=[256, 256],
                activation_fn=torch.nn.ReLU,
            ),
            device="auto",
            replay_buffer_class=RetrospectiveReplayBuffer,  # 【关键】使用自定义buffer
            replay_buffer_kwargs=dict(
                exclude_recent_steps=args.exclude_recent_steps,  # 【新增】采样时排除最新N步
                obj_penalty_weight=obj_penalty_weight,           # 【修改】使用统一的对象权重
                byte_penalty_weight=byte_penalty_weight,         # 【修改】使用统一的字节权重
            ),
        )

        logger_formats = ["stdout", "tensorboard", "csv"]
        custom_logger = configure(logger_dir, logger_formats)
        model.set_logger(custom_logger)

        training_start_time = datetime.now()
        if LOH_DEBUG_BASIC():
            print(f"⏰ training start time: {training_start_time.strftime('%Y-%m-%d %H:%M:%S')}")

        model.learn(
            total_timesteps=int(1e12),
            log_interval=1,
            progress_bar=True,
            tb_log_name="loh_sacblocked_run",
        )

        training_end_time = datetime.now()
        training_duration = training_end_time - training_start_time
        if LOH_DEBUG_BASIC():
            print(f"⏰ training end time: {training_end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"⌛ total training duration: {str(training_duration).split('.')[0]}")

        model.save(f"{run_dir}/sac_loh_final")
        if LOH_DEBUG_BASIC():
            print(f"💾 final model saved as {run_dir}/sac_loh_final.zip")

    except KeyboardInterrupt as exc:
        interrupt_time = datetime.now()
        if training_start_time is not None and LOH_DEBUG_BASIC():
            duration = interrupt_time - training_start_time
            print(f"⏰ training interrupted time: {interrupt_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"⌛ actual running time: {str(duration).split('.')[0]}")

        if LOH_DEBUG_BASIC():
            print(f"⚠️  Training interrupted: {exc}")

        if model is not None:
            try:
                checkpoint_path = f"{run_dir}/sac_loh_interrupted"
                model.save(checkpoint_path)
                if LOH_DEBUG_BASIC():
                    print(f"💾 interrupted model saved as {checkpoint_path}.zip")
            except Exception as save_exc:  # noqa: BLE001
                if LOH_DEBUG_BASIC():
                    print(f"⚠️  Failed to save interrupted model: {save_exc}")

    except Exception as exc:  # noqa: BLE001
        if LOH_DEBUG_BASIC():
            print(f"❌ fatal error occurred: {exc}")
        raise

    finally:
        if env is not None:
            env.close()


if __name__ == "__main__":
    main()
'''
