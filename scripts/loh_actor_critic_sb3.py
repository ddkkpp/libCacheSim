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
from collections import deque
import threading
import mmap
import os
import sys
import errno

import time
from datetime import datetime
from typing import Optional
import cProfile
import pstats
from collections import defaultdict
import math

# ====== 调试/统计输出全局控制 ======
# 0: 无调试输出  1: 仅关键统计  2: 详细调试
LOH_DEBUG_LEVEL = 2

def LOH_DEBUG_BASIC():
    return LOH_DEBUG_LEVEL >= 1

def LOH_DEBUG_VERBOSE():
    return LOH_DEBUG_LEVEL >= 2

# ====== Profiling工具 ======
class FunctionTimer:
    """函数执行时间统计器"""
    def __init__(self):
        self.timings = defaultdict(list)  # {function_name: [duration1, duration2, ...]}
        self.call_counts = defaultdict(int)

    def record(self, name: str, duration: float):
        """手动记录一次耗时（秒）。用于不便用 with 包裹的跨段统计。"""
        try:
            d = float(duration)
        except Exception:
            return
        self.timings[name].append(d)
        self.call_counts[name] += 1

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

    def time_function(self, func_name):
        """装饰器或上下文管理器"""
        class TimerContext:
            def __init__(self, timer, name):
                self.timer = timer
                self.name = name
                self.start = None

            def __enter__(self):
                # 使用与其余计时一致的单调时钟，避免不同时钟源造成聚合误差
                self.start = get_monotonic_time()
                return self

            def __exit__(self, *args):
                duration = get_monotonic_time() - self.start
                self.timer.timings[self.name].append(duration)
                self.timer.call_counts[self.name] += 1

        return TimerContext(self, func_name)

    def report(self, top_n=20):
        """打印耗时统计报告"""
        print("\n" + "="*80)
        print("⏱️  PROFILING REPORT (Top Functions by Total Time)")
        print("="*80)

        # 计算总耗时并排序
        stats = []
        for name, durations in self.timings.items():
            total_time = sum(durations)
            avg_time = total_time / len(durations)
            max_time = max(durations)
            min_time = min(durations)
            count = self.call_counts[name]
            stats.append({
                'name': name,
                'total': total_time,
                'avg': avg_time,
                'max': max_time,
                'min': min_time,
                'count': count
            })

        stats.sort(key=lambda x: x['total'], reverse=True)

        # 打印报告
        print(f"{'Function':<40} {'Calls':>8} {'Total(s)':>10} {'Avg(ms)':>10} {'Max(ms)':>10}")
        print("-"*80)
        for stat in stats[:top_n]:
            print(f"{stat['name']:<40} {stat['count']:>8} "
                  f"{stat['total']:>10.4f} {stat['avg']*1000:>10.2f} {stat['max']*1000:>10.2f}")

        # 追加前缀分组汇总
        group_totals = defaultdict(float)
        overall = 0.0
        for name, durations in self.timings.items():
            total = sum(durations)
            overall += total
            if '.' in name:
                prefix = name.split('.', 1)[0]
            elif ':' in name:
                prefix = name.split(':', 1)[0]
            elif '[' in name:
                prefix = name.split('[', 1)[0]
            else:
                prefix = name
            group_totals[prefix] += total

        if group_totals:
            print("\nGroup totals by prefix (seconds):")
            print("-"*80)
            for k in sorted(group_totals.keys()):
                print(f"{k:<16} {group_totals[k]:>12.4f}")
            # overall 行去掉（不具参考意义，存在重叠）

        # 非重叠核对：将 learn.total 视为总时长，分解为 rollout.phase_total + SAC.train_total + 余项
        try:
            learn_total = sum(self.timings.get("learn.total", []))
            rollout_total = sum(self.timings.get("rollout.phase_total", []))
            train_total = sum(self.timings.get("SAC.train_total", []))
            if learn_total > 0:
                overhead = learn_total - (rollout_total + train_total)
                pct = lambda x: (x / learn_total * 100.0)
                print("\nNon-overlap reconciliation (within learn.total):")
                print("-"*80)
                print(f"learn.total         : {learn_total:10.4f} s (100.0%)")
                print(f"  rollout.phase_total: {rollout_total:10.4f} s ({pct(rollout_total):5.1f}%)")
                print(f"  SAC.train_total   : {train_total:10.4f} s ({pct(train_total):5.1f}%)")
                print(f"  learn.overhead    : {overhead:10.4f} s ({pct(overhead):5.1f}%)")
                prog_total = sum(self.timings.get("program.total", []))
                if prog_total > 0:
                    print("-"*80)
                    print(f"program.total       : {prog_total:10.4f} s (script lifetime)")
                    print(f"  program/learn gap : {prog_total - learn_total:10.4f} s (setup/teardown/other)")
        except Exception:
            pass

        # rollout 内部非重叠分解: rollout.phase_total = env.step_total + rollout.other
        try:
            rollout_total = sum(self.timings.get("rollout.phase_total", []))
            steps_total = sum(self.timings.get("env.step_total", []))
            if rollout_total > 0 and steps_total > 0:
                rollout_other = rollout_total - steps_total
                print("\nRollout internal decomposition (non-overlap):")
                print("-"*80)
                print(f"rollout.phase_total : {rollout_total:10.4f} s (100.0%)")
                print(f"  env.step_total    : {steps_total:10.4f} s ({steps_total/rollout_total*100:5.1f}%)")
                print(f"  rollout.other     : {rollout_other:10.4f} s ({rollout_other/rollout_total*100:5.1f}%)")
        except Exception:
            pass

        # program.total 分解: program.other = program.total - learn.total
        try:
            prog_total = sum(self.timings.get("program.total", []))
            learn_total = sum(self.timings.get("learn.total", []))
            if prog_total > 0 and learn_total > 0:
                prog_other = prog_total - learn_total
                print("\nProgram lifetime decomposition (non-overlap):")
                print("-"*80)
                print(f"program.total       : {prog_total:10.4f} s (100.0%)")
                print(f"  learn.total       : {learn_total:10.4f} s ({learn_total/prog_total*100:5.1f}%)")
                print(f"  program.other     : {prog_other:10.4f} s ({prog_other/prog_total*100:5.1f}%)")
        except Exception:
            pass

        # env.step_total 与 step.add.total 的一致性校验
        try:
            step_total_sum = sum(self.timings.get("env.step_total", []))
            add_total_sum = sum(self.timings.get("step.add.total", []))
            if step_total_sum > 0 and add_total_sum > 0:
                delta = step_total_sum - add_total_sum
                print("\nStep additive reconciliation:")
                print("-"*80)
                print(f"sum(env.step_total) : {step_total_sum:10.4f} s")
                print(f"sum(step.add.total) : {add_total_sum:10.4f} s")
                print(f"delta               : {delta:10.6f} s  (expected ≈0; step.add.total equals per-step wall time)")
                # 额外一致性检查：逐项次数
                step_calls = len(self.timings.get("env.step_total", []))
                add_calls = len(self.timings.get("step.add.total", []))
                if step_calls != add_calls:
                    print(f"WARNING: env.step_total calls={step_calls} vs step.add.total calls={add_calls}")
        except Exception:
            pass

        # Rollout 的非重叠加总分解：将 rollout.phase_total 拆为 step.add.*（互斥求和） + rollout.other
        try:
            rollout_total = sum(self.timings.get("rollout.phase_total", []))
            if rollout_total > 0:
                # 聚合 step.add.* 的各子项（排除 total 本身以避免重复）
                preferred_order = [
                    "step.add.softmax",
                    "step.add.read_shm0",
                    "step.add.wait_ready",
                    "step.add.write_weights",
                    "step.add.wait_new_state",
                    "step.add.read_penalty",
                    "step.add.process_penalty",
                    "step.add.finalize_rewards",
                    "step.add.misc",
                ]
                add_parts = []
                for name in preferred_order:
                    if name in self.timings:
                        add_parts.append((name, sum(self.timings[name])))
                # 兜底：把任何遗漏的 step.add.* 也加入
                for name, durations in self.timings.items():
                    if name.startswith("step.add.") and name not in dict(add_parts) and name != "step.add.total":
                        add_parts.append((name, sum(durations)))

                add_total = sum(self.timings.get("step.add.total", []))
                if add_total == 0.0:
                    # 如果没有记录 step.add.total，则用子项之和近似
                    add_total = sum(val for _, val in add_parts)
                rollout_other = rollout_total - add_total

                print("\nRollout additive decomposition (non-overlap):")
                print("-"*80)
                print(f"rollout.phase_total : {rollout_total:10.4f} s (100.0%)")
                for name, val in add_parts:
                    pct = (val / rollout_total * 100.0) if rollout_total > 0 else 0.0
                    print(f"  {name:<18}: {val:10.4f} s ({pct:5.1f}%)")
                print(f"  step.add.total    : {add_total:10.4f} s ({add_total/rollout_total*100:5.1f}%)")
                print(f"  rollout.other     : {rollout_other:10.4f} s ({rollout_other/rollout_total*100:5.1f}%)")
        except Exception:
            pass

        # 将 rollout.other 再拆为 step-external 段：callback 和起止钩子 + 剩余（保证互斥可加）
        try:
            rollout_total = sum(self.timings.get("rollout.phase_total", []))
            if rollout_total > 0:
                step_total = sum(self.timings.get("env.step_total", []))
                cb_on_step = sum(self.timings.get("callback._on_step", []))
                cb_start = sum(self.timings.get("callback._on_rollout_start", []))
                cb_end = sum(self.timings.get("callback._on_rollout_end", []))
                external_sum = cb_on_step + cb_start + cb_end
                rest = rollout_total - (step_total + external_sum)

                print("\nRollout step-external decomposition (non-overlap):")
                print("-"*80)
                print(f"rollout.phase_total : {rollout_total:10.4f} s (100.0%)")
                print(f"  env.step_total    : {step_total:10.4f} s ({step_total/rollout_total*100:5.1f}%)")
                print(f"  callback._on_step : {cb_on_step:10.4f} s ({cb_on_step/rollout_total*100:5.1f}%)")
                print(f"  cb.on_rollout_start: {cb_start:10.4f} s ({cb_start/rollout_total*100:5.1f}%)")
                print(f"  cb.on_rollout_end : {cb_end:10.4f} s ({cb_end/rollout_total*100:5.1f}%)")
                print(f"  rollout.rest      : {rest:10.4f} s ({rest/rollout_total*100:5.1f}%)")
        except Exception:
            pass

        # 打印 env.step（重叠视图）与 step.add（非重叠视图）的汇总
        try:
            # env.step breakdown（重叠，供对照）
            step_total_sum = sum(self.timings.get("env.step_total", []))
            names = [n for n in self.timings.keys() if n.startswith("env.step_") and n != "env.step_total"]
            names.sort()
            print("\nENV.STEP breakdown (overlapping):")
            print("-"*80)
            print(f"env.step_total      : {step_total_sum:10.4f} s")
            for n in names:
                tot = sum(self.timings.get(n, []))
                print(f"  {n:<20}: {tot:10.4f} s")

            # step.add breakdown（非重叠，可加和）
            add_total_sum = sum(self.timings.get("step.add.total", []))
            add_names = [
                "step.add.softmax",
                "step.add.read_shm0",
                "step.add.wait_ready",
                "step.add.write_weights",
                "step.add.wait_new_state",
                "step.add.read_penalty",
                "step.add.process_penalty",
                "step.add.finalize_rewards",
                "step.add.misc",
            ]
            print("\nSTEP.ADD breakdown (non-overlap):")
            print("-"*80)
            print(f"step.add.total      : {add_total_sum:10.4f} s")
            for n in add_names:
                if n in self.timings:
                    tot = sum(self.timings.get(n, []))
                    print(f"  {n:<20}: {tot:10.4f} s")
        except Exception:
            pass

        print("="*80 + "\n")

# 全局计时器
GLOBAL_TIMER = FunctionTimer()

from stable_baselines3 import PPO  # 保留作参考
from stable_baselines3 import SAC
from stable_baselines3.common.buffers import ReplayBuffer
import numpy as np


class ProfiledSAC(SAC):
    """SAC 带全局计时的子类"""

    def train(self, gradient_steps: int, batch_size: int = 64):  # noqa: D401
        """Measure total SAC.train time without monkey patching."""
        with GLOBAL_TIMER.time_function("SAC.train_total"):
            return super().train(gradient_steps, batch_size)


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

# --- 常量和共享内存结构定义 ---
try:
    SHM_KEY = int(os.environ.get("LOH_SHM_KEY", "9876"))
except Exception:
    SHM_KEY = 9876
FEATURE_DIM = 6
# 动态读取状态维度：基础维度(26/38) + 可选候选特征维度(+72)
# 规则：
#   - LOH_STATE_DIM=26/38 决定基础维度（或由 LOH_INCLUDE_CACHE_FEATURES 推断）
#   - 若 LOH_INCLUDE_CANDIDATE_FEATURES 为真，则在基础上追加 72 维候选统计
try:
    _env_state_dim = int(os.environ.get("LOH_STATE_DIM", "26"))
except Exception:
    _env_state_dim = 26
if _env_state_dim not in (26, 38):
    # 容错：任何非合法值回退到 26，并打印警告
    print(f"[WARN] LOH_STATE_DIM={_env_state_dim} unsupported; falling back to 26")
    _env_state_dim = 26
_cand_enabled_raw = os.environ.get("LOH_INCLUDE_CANDIDATE_FEATURES", "0").strip().lower()
_cand_enabled = _cand_enabled_raw in {"1", "true", "yes", "on"}
CONTEXT_DIM = _env_state_dim + (72 if _cand_enabled else 0)
STATE_DIM = CONTEXT_DIM  # 与C端共享内存 state[] 长度一致

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

# 【修复】将 SharedMemoryData 定义为模块级别的类，以支持 pickle
# 注意: ctypes 数组需要在模块级别定义才能被 pickle
class SharedMemoryData(ctypes.Structure):
    """共享内存数据结构 - 必须是模块级别类以支持pickle"""
    _fields_ = [
        ("ready_for_inference", ctypes.c_int),
        ("weights_updated", ctypes.c_int),
        ("terminate", ctypes.c_int),
        ("is_training", ctypes.c_int),
        ("state", ctypes.c_double * CONTEXT_DIM),  # 使用固定的 CONTEXT_DIM
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

# 运行时校验 sizeof 与字段偏移（可选，首次导入即打印）
def _print_shm_layout_once():
    if os.environ.get("LOH_PRINT_SHM_LAYOUT", "1") not in ("0", "false", "False"):
        try:
            smd_size = ctypes.sizeof(SharedMemoryData)
            print(f"[SHM] Python SharedMemoryData sizeof={smd_size} bytes (STATE_DIM={STATE_DIM})")
            for name, _ in SharedMemoryData._fields_:
                try:
                    off = getattr(SharedMemoryData, name).offset
                    print(f"[SHM]   offset {off:4d} : {name}")
                except Exception:
                    pass
        except Exception as e:
            print(f"[SHM] Layout print failed: {e}")

_print_shm_layout_once()

def create_shared_memory_class(context_dim):
    """
    保留此函数以兼容旧代码，但现在直接返回模块级别的 SharedMemoryData

    注意: 如果 context_dim != CONTEXT_DIM，会发出警告
    """
    if context_dim != CONTEXT_DIM:
        import warnings
        warnings.warn(f"create_shared_memory_class called with context_dim={context_dim}, "
                     f"but using fixed CONTEXT_DIM={CONTEXT_DIM}")
    return SharedMemoryData

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

    def __init__(self, *args, exclude_recent_steps, obj_penalty_weight, byte_penalty_weight, **kwargs):
        """
        Args:
            exclude_recent_steps: 采样时排除最近N步的数据（由外部参数提供，运行时必须传入）
            obj_penalty_weight: 对象hit_ratio权重 (alpha)，由外部参数提供
            byte_penalty_weight: 字节hit_ratio权重 (beta)，由外部参数提供

        NOTE: 默认值已移出此构造函数；请通过上层配置（例如命令行参数 --exclude-recent-steps）
        将值传入 `replay_buffer_kwargs`。这样运行时参数优先于类定义。
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

        # 奖励修正统计（历史命名 reward_corrections 语义混合：现拆分为收到/已应用）
        # 统一命名：corrected_num（收到的惩罚事件） / finalized_num（最终化并用于奖励的事件）
        # reward_corrections 保持兼容 = corrected_num + finalized_num
        self.corrected_num = 0          # retrospective_correct_reward() 收到的原始惩罚事件次数
        self.finalized_num = 0          # compute_final_rewards() 中实际用于奖励计算的事件条数（raw_penalty_count 累加）
        self.reward_corrections = 0     # 兼容旧逻辑聚合：= corrected_num + finalized_num（同步维护）
        self.total_obj_penalty = 0.0  # 累积的对象惩罚总和
        self.total_byte_penalty = 0.0  # 累积的字节惩罚总和
        # 统计：对已 final reward 的位置进行修正的次数
        self.corrections_on_finalized = 0

        # 存储 compute_final_rewards 实际应用的 penalty（按位置记录）
        # 这些是 finalize 时计算并真正用于更新 final reward 的惩罚值
        self.applied_penalties = []

        # 【新增】Penalty baseline（滑动平均）
        self.penalty_baseline = 0.0  # 初始为0
        self.baseline_decay = 0.99   # 指数衰减系数

        # 奖励计算参数
        self.obj_penalty_weight = obj_penalty_weight    # 默认1.0
        self.byte_penalty_weight = byte_penalty_weight  # 默认0.0

        # 采样保护窗口
        self.exclude_recent_steps = exclude_recent_steps
        self.excluded_samples = 0  # 统计：因保护窗口而跳过采样的次数

        # 存储每个位置对应的权重向量（若env在infos中传入weights）
        try:
            self.weights_at_pos = np.zeros((self.buffer_size, FEATURE_DIM), dtype=np.float32)
        except Exception:
            # 若 FEATURE_DIM 未定义或其他问题，退化为None
            self.weights_at_pos = None

        # 【新增】存储每个位置对应的命中率（用于与 reward 同窗口统计到 TB）
        try:
            self.obj_hit_ratio_at_pos = np.zeros((self.buffer_size,), dtype=np.float32)
            self.byte_hit_ratio_at_pos = np.zeros((self.buffer_size,), dtype=np.float32)
        except Exception:
            self.obj_hit_ratio_at_pos = None
            self.byte_hit_ratio_at_pos = None

        # 惩罚缩放：使用距离倒数（1/d）。为保持向后兼容仍保留 dmax 读取但不参与计算。
        try:
            env_dmax = os.environ.get("LOH_PENALTY_DMAX")
            penalty_dmax = int(env_dmax) if env_dmax is not None and env_dmax.strip() != "" else 400000
        except Exception:
            penalty_dmax = 400000
        self.penalty_dmax = max(1, int(penalty_dmax))
        # 为旧实现保留字段，占位不用
        self._log_denom = 1.0

        if LOH_DEBUG_BASIC():
            # 支持通过环境变量 LOH_PENALTY_SCALE 指定缩放类型
            # 支持值: reciprocal (默认), pen_d, survival, 或自定义标签
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

        # --- 奖励组合配置（通过环境变量控制，默认保持 penalty-only 行为） ---
        self.reward_use_penalty = _env_flag("LOH_REWARD_USE_PENALTY", True)
        self.reward_use_miss = _env_flag("LOH_REWARD_USE_MISS_RATIO", False)
        self.reward_use_trend = _env_flag("LOH_REWARD_USE_TREND", False)
        # 权重
        try:
            self.reward_w_penalty = float(os.environ.get("LOH_REWARD_W_PENALTY", "1.0"))
        except Exception:
            self.reward_w_penalty = 1.0
        try:
            self.reward_w_miss = float(os.environ.get("LOH_REWARD_W_MISS", "1.0"))
        except Exception:
            self.reward_w_miss = 1.0
        try:
            self.reward_w_trend = float(os.environ.get("LOH_REWARD_W_TREND", "0.5"))
        except Exception:
            self.reward_w_trend = 0.5
        # 罚项模式（与 LOH_PENALTY_SCALE 对齐）
        self.penalty_mode = os.environ.get("LOH_PENALTY_MODE", os.environ.get("LOH_PENALTY_SCALE", "reciprocal")).strip().lower()
        # 趋势配置
        try:
            self.trend_window = int(os.environ.get("LOH_TREND_WINDOW", "100"))
        except Exception:
            self.trend_window = 100
        self.trend_mode = os.environ.get("LOH_TREND_MODE", "slope").strip().lower()  # slope | delta
        # miss 项配置：neg（-miss_ratio）或 improve（baseline_miss - miss）
        self.miss_component_mode = os.environ.get("LOH_MISS_COMPONENT", "neg").strip().lower()
        # 存储最近一次 finalize 的各组件，便于TB读取
        self._last_reward_components = {
            'penalty': 0.0,
            'miss': 0.0,
            'trend': 0.0,
            'final': 0.0,
            'final_pre_clip': 0.0,
            'clip_delta': 0.0,
        }

        # --- Finalize 事件统计（用于诊断 baseline 激增原因） ---
        self.finalize_events_total = 0            # compute_final_rewards 被调用的总次数
        self.finalize_positions_total = 0         # 被最终化的位置总数（累计）
        self.finalize_last_step_applied_count = 0 # 最近一次调用中最终化的位置数量
        self.finalize_last_step_penalty_sum = 0.0 # 最近一次调用中应用的 penalty 总和
        self.first_finalize_step = -1             # 首次 finalize 发生时的全局步数（env 的 num_timesteps）
        self._env_step_provider = None            # 由 env.set_model 设置后回填（用于读取当前步数）
        self.penalty_baseline_last_finalize = 0.0  # 最近一次 finalize 后的 baseline 值
        # --- 新增：区分“收到的惩罚事件(原始 corrections)”与“已应用到最终奖励的惩罚” ---
        self.applied_penalties_count = 0          # compute_final_rewards 中累计实际用于计算奖励的 penalty 条目数（Σ每个最终化位置的 raw_penalty_count）

    def _penalty_scale(self, distance: float) -> float:
        """将距离映射到 [0,1] 的惩罚强度，支持多种模式（通过 penalty_mode 配置）。
        此处log和survival和单独文件的不一样
        reciprocal: p(d) = 1 / max(d, 1)
        log:        p(d) = 1 / log(2 + d)
        survival:   p(d) = exp(-d / dmax)
        """
        try:
            d = float(distance)
        except Exception:
            d = 0.0
        mode = getattr(self, 'penalty_mode', 'reciprocal')
        if mode == 'log':
            import math
            return 1.0 / max(math.log(2.0 + max(d, 0.0)), 1.0)
        if mode == 'survival':
            import math
            dmax = max(1.0, float(getattr(self, 'penalty_dmax', 400000)))
            return float(math.exp(-max(d, 0.0) / dmax))
        # default: reciprocal
        if d <= 1.0:
            return 1.0
        return 1.0 / d

    def _get_window_indices(self, center_pos: int, window: int):
        """获取以 center_pos 结尾的窗口索引（不含 center_pos），用于趋势计算。"""
        if window <= 0 or self.size() == 0:
            return []
        n = min(window, self.size())
        start = (center_pos - n) % self.buffer_size
        idxs = []
        if not self.full and start < 0:
            start = 0
        for k in range(n):
            idxs.append((start + k) % self.buffer_size)
        # 不包含 center_pos 自身
        if idxs and idxs[-1] == center_pos:
            idxs = idxs[:-1]
        return idxs

    def _compute_trend_component(self, pos: int) -> float:
        """计算命中率趋势分量（正值代表近期改善）。"""
        if self.obj_hit_ratio_at_pos is None or self.size() == 0:
            return 0.0
        idxs = self._get_window_indices(pos, getattr(self, 'trend_window', 100))
        if not idxs:
            return 0.0
        vals = np.array([float(self.obj_hit_ratio_at_pos[i]) for i in idxs], dtype=np.float64)
        if vals.size < 2:
            return 0.0
        mode = getattr(self, 'trend_mode', 'slope')
        comp = 0.0
        if mode == 'delta':
            comp = float(self.obj_hit_ratio_at_pos[pos]) - float(vals[0])
        else:
            try:
                x = np.arange(vals.size, dtype=np.float64)
                # 一阶线性回归斜率
                slope = float(np.polyfit(x, vals, 1)[0])
                # 归一化：乘以窗口长度，保证数量级可控
                comp = slope * float(vals.size)
            except Exception:
                comp = 0.0
        # 限幅到 [-1,1]
        if comp > 1.0:
            comp = 1.0
        elif comp < -1.0:
            comp = -1.0
        return comp

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
        # 记录命中率（若可用）
        try:
            if self.obj_hit_ratio_at_pos is not None and len(infos) > 0:
                self.obj_hit_ratio_at_pos[pos_before] = float(infos[0].get('obj_hit_ratio', 0.0))
            if self.byte_hit_ratio_at_pos is not None and len(infos) > 0:
                self.byte_hit_ratio_at_pos[pos_before] = float(infos[0].get('byte_hit_ratio', 0.0))
        except Exception:
            pass
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
        # 如果infos中包含weights，把它保存在weights_at_pos以便后续分析
        if self.weights_at_pos is not None and len(infos) > 0 and 'weights' in infos[0]:
            try:
                w = np.asarray(infos[0]['weights'], dtype=np.float32)
                if w.shape[0] == self.weights_at_pos.shape[1]:
                    self.weights_at_pos[pos_before, :] = w
            except Exception:
                pass

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

        # 检查该位置是否已被最终化（finalized）
        was_finalized = bool(self.reward_finalized[pos])

        # 【新增】将原始数据添加到列表中
        self.penalty_data[pos].append((eviction_to_access, obj_size))  # 记录原始惩罚数据

        # 统计（仅收到）
        self.corrected_num += 1
        self.reward_corrections = self.corrected_num + self.finalized_num
        if was_finalized:
            # 这表示我们正在修正一个已经被 compute_final_rewards 标记为最终化的位置
            self.corrections_on_finalized += 1

        # 【新增】详细打印
        if LOH_DEBUG_BASIC():
            print(f"[Buffer→Modify] Accumulated penalty at pos {pos}:")
            print(f"  - state_version: {state_version}")
            print(f"  - eviction_to_access: {eviction_to_access}")
            print(f"  - obj_size: {obj_size}")
            print(f"  - total penalties at pos: {len(self.penalty_data[pos])}")
            print(f"  - evicted_bytes at pos: {self.evicted_bytes_at_pos[pos]}")
            print(f"  - evicted_count at pos: {self.evicted_count_at_pos[pos]}")
            print(f"  - reward_corrections: {self.reward_corrections}")
            print(f"  - corrected_num: {self.corrected_num}")

        return True

    def compute_final_rewards(self, start_pos, end_pos):
        """
        计算指定范围内的最终奖励

        在数据超过 exclude_recent_steps 后调用，使用存储的驱逐统计计算惩罚

    公式（更新后的惩罚缩放）:
    1. 定义 pd = penalty_scale(distance) = 1 / max(d, 1)
    2. obj_penalty = Σ(1/evicted_count * pd)
    3. byte_penalty = Σ(size/evicted_bytes * pd)
    4. reward = 基于 penalty 与 baseline 的相对变化（保持原逻辑）

        Args:
            start_pos: 起始位置（包含）
            end_pos: 结束位置（不包含）
        """
        count_computed = 0
        penalty_sum_this_call = 0.0
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
                pd = self._penalty_scale(eviction_to_access)

                # 对象惩罚：1/evicted_count * pd
                obj_penalty += (1.0 / evicted_count) * pd

                # 字节惩罚：size/evicted_bytes * pd
                if evicted_bytes > 0:
                    byte_penalty += (obj_size / evicted_bytes) * pd

            # 加权求和 -> penalty
            penalty = (self.obj_penalty_weight * obj_penalty +
                       self.byte_penalty_weight * byte_penalty)

            # 记录本次 finalize 实际应用的 penalty
            try:
                self.applied_penalties.append(float(penalty))
            except Exception:
                pass
            penalty_sum_this_call += float(penalty)

            # 【Reward公式】Reward = (baseline - current) / baseline
            # - 相对于baseline的改进
            # - 范围：[-∞, 1]，clip到[-1, 1]
            #
            # 为什么用 1e-6 作为边界？
            # - 避免除零错误：如果 baseline=0，除法会崩溃
            # - 判断baseline有效性：baseline < 1e-6 认为是"接近零"（实际上无意义）
            # - 浮点数精度：1e-6 是合理的"非零"阈值（比机器精度1e-15大得多）
            if self.penalty_baseline > 1e-6:
                # 有效baseline：计算相对变化
                reward = (self.penalty_baseline - penalty) / self.penalty_baseline
            else:
                # 无有效baseline（初期或baseline接近0）：直接用负penalty
                reward = -penalty if penalty > 0 else 0.0

            # 更新baseline（指数移动平均）
            self.penalty_baseline = (self.baseline_decay * self.penalty_baseline +
                                     (1 - self.baseline_decay) * penalty)

            # Clip到[-1, 1]
            final_reward = max(-1.0, min(1.0, reward))

            # 更新统计（已应用部分）
            self.finalized_num += raw_penalty_count
            self.reward_corrections = self.corrected_num + self.finalized_num
            self.applied_penalties_count += raw_penalty_count
            self.total_obj_penalty += obj_penalty
            self.total_byte_penalty += byte_penalty

            # 写入buffer
            # 组合奖励（可选）：penalty/miss/trend
            mixed = 0.0
            penalty_comp = final_reward  # penalty 映射后的奖励（已裁剪）
            miss_comp = 0.0
            trend_comp = 0.0
            if getattr(self, 'reward_use_miss', False) and self.obj_hit_ratio_at_pos is not None:
                try:
                    obj_hit = float(self.obj_hit_ratio_at_pos[pos])
                    miss_ratio = max(0.0, min(1.0, 1.0 - obj_hit))
                    if getattr(self, 'miss_component_mode', 'neg') == 'improve':
                        # 使用 miss 改善量：相对窗口均值的改进（越小越好）
                        idxs_for_miss = self._get_window_indices(pos, getattr(self, 'trend_window', 100))
                        if idxs_for_miss:
                            baseline_miss = 1.0 - float(np.mean([self.obj_hit_ratio_at_pos[i] for i in idxs_for_miss]))
                            miss_comp = float(baseline_miss - miss_ratio)
                        else:
                            miss_comp = -miss_ratio
                    else:
                        # 直接用 -miss_ratio（命中越高越好）
                        miss_comp = -miss_ratio
                    # 限幅
                    miss_comp = max(-1.0, min(1.0, miss_comp))
                except Exception:
                    miss_comp = 0.0
            if getattr(self, 'reward_use_trend', False):
                try:
                    trend_comp = float(self._compute_trend_component(pos))
                except Exception:
                    trend_comp = 0.0
            # 聚合：默认 penalty-only（当 miss/trend 均未启用时，保持原行为）
            mixed_terms = []
            if getattr(self, 'reward_use_penalty', True):
                mixed += self.reward_w_penalty * float(penalty_comp)
                mixed_terms.append(('pen', self.reward_w_penalty, float(penalty_comp)))
            if getattr(self, 'reward_use_miss', False):
                mixed += self.reward_w_miss * float(miss_comp)
                mixed_terms.append(('miss', self.reward_w_miss, float(miss_comp)))
            if getattr(self, 'reward_use_trend', False):
                mixed += self.reward_w_trend * float(trend_comp)
                mixed_terms.append(('trend', self.reward_w_trend, float(trend_comp)))
            final_mixed_pre_clip = float(mixed)
            final_mixed = max(-1.0, min(1.0, final_mixed_pre_clip))
            # 保存组件供诊断
            try:
                self._last_reward_components = {
                    'penalty': float(penalty_comp),
                    'miss': float(miss_comp),
                    'trend': float(trend_comp),
                    'final': float(final_mixed),
                    'final_pre_clip': float(final_mixed_pre_clip),
                    'clip_delta': float(final_mixed - final_mixed_pre_clip),
                }
            except Exception:
                pass

            # 写到buffer（使用组合结果）
            self.rewards[pos, 0] = final_mixed
            self.reward_finalized[pos] = True
            count_computed += 1

            # 【增强】打印前 5 个详细的奖励计算过程
            if LOH_DEBUG_BASIC() and count_computed <= 5:
                print(f"[Reward→Final] 🎯 pos {pos}:")
                print(f"  📊 penalty_data: {raw_penalty_count} items")
                print(f"  📊 evicted_count: {evicted_count}, evicted_bytes: {evicted_bytes}")
                print(f"  📐 obj_penalty: {obj_penalty:.8f}")
                print(f"  📐 byte_penalty: {byte_penalty:.8f}")
                print(f"  📐 penalty (weighted): {penalty:.8f}")
                print(f"  📐 penalty_baseline: {self.penalty_baseline:.8f}")
                print(f"  📐 relative_change: {(self.penalty_baseline - penalty):.8f}")
                print(f"  🎁 reward (before clip): {reward:.6f}")
                print(f"  🎁 final_reward (after clip): {final_reward:.6f}")
            elif LOH_DEBUG_BASIC() and count_computed == 6:
                print(f"[Reward→Final] ... (computed {count_computed} rewards, suppressing further output)")

        if LOH_DEBUG_BASIC() and count_computed > 0:
            print(f"[ReplayBuffer] ✅ Computed {count_computed} final rewards "
                  f"for positions [{start_pos}, {end_pos})")

        # 更新 finalize 统计
        if count_computed > 0:
            self.finalize_events_total += 1
            self.finalize_positions_total += count_computed
            self.finalize_last_step_applied_count = count_computed
            self.finalize_last_step_penalty_sum = penalty_sum_this_call
            self.penalty_baseline_last_finalize = float(self.penalty_baseline)
            # 记录首次 finalize 发生的步数（用于解释 baseline 激增时机）
            if self.first_finalize_step < 0:
                # 尝试从 env 的 model 中读取当前 timesteps（回调中使用 self.num_timesteps，也可使用 model._total_timesteps 或 logger 的 step）
                try:
                    if self._env_step_provider is not None and hasattr(self._env_step_provider, 'num_timesteps'):
                        self.first_finalize_step = int(getattr(self._env_step_provider, 'num_timesteps'))
                    elif hasattr(self, 'model') and self.model is not None and hasattr(self.model, 'num_timesteps'):
                        self.first_finalize_step = int(self.model.num_timesteps)
                except Exception:
                    self.first_finalize_step = -2  # -2 表示记录失败
            if LOH_DEBUG_BASIC():
                print(f"[ReplayBuffer] FINALIZE_STATS: count={count_computed}, penalty_sum={penalty_sum_this_call:.6f}, total_finalized={self.finalize_positions_total}")

        return count_computed

    def sample(self, batch_size, env=None):
        """
        重写sample方法：采样时避开最新的exclude_recent_steps步数据

        原因：
        - 最新数据可能还未被惩罚修正（Ghost cache miss需要时间）
        - 避免使用错误奖励训练，提高数据质量
        """
        with GLOBAL_TIMER.time_function("ReplayBuffer.sample_total"):
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
        """获取奖励修正统计（拆分：收到 vs 已应用）"""
        # 平均 penalty 仅基于 finalize 时实际应用的列表计算，避免误导
        if hasattr(self, 'applied_penalties') and len(self.applied_penalties) > 0:
            avg_penalty = float(np.mean(self.applied_penalties))
        else:
            avg_penalty = 0.0

        # 兼容旧打印逻辑：提供 'corrections', 'corrections_on_finalized', 'prop_on_finalized'
        corr_recv = int(getattr(self, 'corrected_num', 0))
        corr_applied = int(getattr(self, 'finalized_num', 0))
        corr_on_finalized = int(getattr(self, 'corrections_on_finalized', 0))
        if corr_recv > 0:
            prop_on_finalized = float(corr_on_finalized / corr_recv)
        else:
            prop_on_finalized = 0.0

        return {
            # 新语义
            'corrected_num': corr_recv,                 # 收到的惩罚事件总数（retrospective_correct_reward）
            'finalized_num': corr_applied,              # 实际用于奖励计算的事件数（compute_final_rewards 原始条目数求和）
            'correct_on_finalized': corr_on_finalized,  # 对已finalized位置的后续修正次数
            'prop_on_finalized': prop_on_finalized,     # correct_on_finalized / corrected_num

            # 旧字段兼容（用于已有日志/打印）
            'corrections_received': corr_recv,
            'corrections_applied': corr_applied,
            'corrections': corr_recv,                   # 打印 total 使用
            'corrections_on_finalized': corr_on_finalized,  # 打印 on_finalized 使用

            # 其他诊断
            'reward_corrections': int(self.reward_corrections),
            'avg_penalty': float(avg_penalty),
            'excluded_samples': int(self.excluded_samples),
            'finalize_last_step_applied_count': int(self.finalize_last_step_applied_count),
            'finalize_last_step_penalty_sum': float(self.finalize_last_step_penalty_sum),
            'finalize_events_total': int(self.finalize_events_total),
            'finalize_positions_total': int(self.finalize_positions_total),
            'first_finalize_step': int(self.first_finalize_step),
            'penalty_baseline_last_finalize': float(self.penalty_baseline_last_finalize),
            'applied_penalties_total': int(self.applied_penalties_count),
            # 最近一次 finalize 的奖励组件（便于TB记录）
            'last_reward_penalty': float(self._last_reward_components.get('penalty', 0.0) if hasattr(self, '_last_reward_components') else 0.0),
            'last_reward_miss': float(self._last_reward_components.get('miss', 0.0) if hasattr(self, '_last_reward_components') else 0.0),
            'last_reward_trend': float(self._last_reward_components.get('trend', 0.0) if hasattr(self, '_last_reward_components') else 0.0),
            'last_reward_final': float(self._last_reward_components.get('final', 0.0) if hasattr(self, '_last_reward_components') else 0.0),
            'last_reward_final_pre_clip': float(self._last_reward_components.get('final_pre_clip', 0.0) if hasattr(self, '_last_reward_components') else 0.0),
            'last_reward_clip_delta': float(self._last_reward_components.get('clip_delta', 0.0) if hasattr(self, '_last_reward_components') else 0.0),
        }

# --- 自定义Gymnasium环境 ---
def _parse_obs_keep(spec: str, context_dim: int):
    """Parse an index/range spec into a sorted unique index list.

    Examples:
      "all" -> [0..context_dim-1]
      "nohit" -> [2..context_dim-1] (drop first two hit ratios)
      "hit" -> [0,1]
      "features" -> [2..min(26, context_dim)-1]
      "cache" -> [26..min(38, context_dim)-1]
      "0-1,4,6-8" -> explicit indices
    """
    if not spec:
        # 默认：仅保留 cache 特征区间
        start = 26
        end = min(38, context_dim)
        return [i for i in range(start, end) if i < context_dim]

    s = str(spec).strip().lower()
    if s == "all":
        return [i for i in range(context_dim)]
    if s == "nohit":
        return [i for i in range(2, context_dim)] if context_dim > 2 else []
    if s == "hit":
        return [i for i in range(min(2, context_dim))]
    if s == "features":
        start = 2
        end = min(26, context_dim)
        return [i for i in range(start, end)]
    if s == "cache":
        start = 26
        end = min(38, context_dim)
        return [i for i in range(start, end) if i < context_dim]

    # generic list/range parser, e.g. "0-1,4,6-8"
    idx = set()
    for token in s.replace(" ", "").split(','):
        if not token:
            continue
        if '-' in token:
            a, b = token.split('-', 1)
            try:
                a_i = int(a); b_i = int(b)
            except Exception:
                continue
            if a_i > b_i:
                a_i, b_i = b_i, a_i
            for i in range(max(0, a_i), min(context_dim - 1, b_i) + 1):
                idx.add(i)
        else:
            try:
                i = int(token)
            except Exception:
                continue
            if 0 <= i < context_dim:
                idx.add(i)
    if not idx:
        return None
    return sorted(idx)


class LohEnv(gym.Env):
    """快速通信版本的LOH环境"""
    metadata = {"render_modes": []}

    def __init__(self, shm_key=SHM_KEY, miss_ratio_weight=1.0, byte_miss_ratio_weight=0.0,
                 obs_keep_indices=None):
        super(LohEnv, self).__init__()

        # 1. 定义动作空间和观测空间
        self.action_space = spaces.Box(
            low=-1.0, high=1.0, shape=(FEATURE_DIM,), dtype=np.float32
        )
        # softmax 温度（用于将 logits 映射为权重时的锐化/平滑），可用环境变量 LOH_SOFTMAX_TEMP 配置
        try:
            self._softmax_temp = float(os.environ.get("LOH_SOFTMAX_TEMP", "1.0"))
            if not (self._softmax_temp > 0):
                self._softmax_temp = 1.0
        except Exception:
            self._softmax_temp = 1.0
        # 观测空间：维度可配置（共享内存中的 CONTEXT_DIM 不变，仅对观察做投影）
        # obs_keep_indices: list[int] 选择暴露给RL的维度；None 表示全部维度
        self._obs_idx = None
        if obs_keep_indices is not None and len(obs_keep_indices) > 0:
            self._obs_idx = np.array(sorted(set(int(i) for i in obs_keep_indices if 0 <= int(i) < CONTEXT_DIM)), dtype=np.int64)
        else:
            self._obs_idx = np.arange(CONTEXT_DIM, dtype=np.int64)

        # 命中率差分特征配置（默认关闭，仅Python端追加，不影响共享内存）
        self._add_hit_deltas = _env_flag("LOH_OBS_ADD_HIT_DELTAS", False)
        self._hit_delta_mode = os.environ.get("LOH_HIT_DELTA_MODE", "mean").strip().lower()  # mean | tail
        try:
            self._hit_delta_window = int(os.environ.get("LOH_HIT_DELTA_WINDOW", "100"))
        except Exception:
            self._hit_delta_window = 100
        self._obj_hit_history = deque(maxlen=self._hit_delta_window)
        self._byte_hit_history = deque(maxlen=self._hit_delta_window)
        extra_dims = 2 if self._add_hit_deltas else 0
        self.observation_space = spaces.Box(
            low=0.0, high=1.0, shape=(int(self._obs_idx.shape[0] + extra_dims),), dtype=np.float32
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
    # 仅使用 obs_keep_indices 控制观测维度，不再支持隐藏命中率两维的开关
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
            print("   State feature config: observation via obs_keep_indices (no separate hit toggle)")
            print(
                "   Observation view: obs_dim=",
                int(self._obs_idx.shape[0]),
                "indices=",
                self._obs_idx.tolist()
            )
            if self._add_hit_deltas:
                print(f"   Extra delta features enabled: window={self._hit_delta_window}, mode={self._hit_delta_mode}")

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
        timer_label = f"ipc.sem_wait[{label}]" if label else "ipc.sem_wait"
        with GLOBAL_TIMER.time_function(timer_label):
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
        with GLOBAL_TIMER.time_function("ipc.sem_post"):
            res = libc.sem_post(sem_handle)
            if res != 0:
                err = ctypes.get_errno()
                self._disable_semaphores(f"sem_post error: {os.strerror(err)}")
            elif LOH_DEBUG_VERBOSE() and label:
                print(f"[SEM][Python] sem_post {label}")

    def _read_shm(self):
        """快速读取共享内存"""
        try:
            with GLOBAL_TIMER.time_function("ipc.read_shm"):
                read_start = get_monotonic_time()
                self.shm.seek(0)
                raw_data = self.shm.read(ctypes.sizeof(SharedMemoryData))
                data = SharedMemoryData.from_buffer_copy(raw_data)
                read_end = get_monotonic_time()
                read_duration = read_end - read_start
                current_timestamp = get_monotonic_time()
                if LOH_DEBUG_VERBOSE() and read_duration > 0.001:
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
            with GLOBAL_TIMER.time_function("ipc.write_shm"):
                raw_data = ctypes.string_at(ctypes.byref(data_struct), ctypes.sizeof(data_struct))
                self.shm.seek(0)
                self.shm.write(raw_data)
                self.shm.flush()
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
            with GLOBAL_TIMER.time_function("ipc.write_field_int32"):
                if offset is None:
                    return False
                self.shm.seek(offset)
                self.shm.write(int(value).to_bytes(4, byteorder=sys.byteorder, signed=True))
                self.shm.flush()
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

        # 原始观测（含 state[0:2]）
        initial_observation_raw = np.array(initial_data.state, dtype=np.float32)
        try:
            initial_observation_raw = np.clip(initial_observation_raw, 0.0, 1.0)
        except Exception:
            pass
        # 生成reset返回的观测，遵循与step相同的选择逻辑
        # 若提供了 obs_keep_indices，则始终按索引选择（即使与 CONTEXT_DIM 相同，也走统一分支）
        if self._obs_idx is not None:
            initial_observation = initial_observation_raw[self._obs_idx]
        else:
            initial_observation = initial_observation_raw
        # 初始化命中率历史并追加 delta 特征（复位时差分=0）
        try:
            self._obj_hit_history.clear(); self._byte_hit_history.clear()
            self._obj_hit_history.append(float(initial_observation_raw[0]))
            self._byte_hit_history.append(float(initial_observation_raw[1]))
        except Exception:
            pass
        if self._add_hit_deltas:
            initial_observation = np.concatenate([initial_observation, np.zeros((2,), dtype=np.float32)])
        # 从 state[0] 和 state[1] 获取全局特征（obj_hit_ratio 和 byte_hit_ratio）
        # 注意：C 端存储的是 hit_ratio，miss_ratio = 1 - hit_ratio
        # 奖励基于原始命中率（不受观测选择影响）
        initial_miss_ratio = 1.0 - initial_observation_raw[0]  # state[0] 是 obj_hit_ratio
        initial_byte_miss_ratio = 1.0 - initial_observation_raw[1]  # state[1] 是 byte_hit_ratio

        # 清除历史性能指标
        if hasattr(self, '_previous_miss_ratio'):
            delattr(self, '_previous_miss_ratio')
        if hasattr(self, '_previous_byte_miss_ratio'):
            delattr(self, '_previous_byte_miss_ratio')

        print(f"✅ Episode #{self.episode_count} Reset Complete:")
        print(f"   [seq {int(initial_data.state_version)}] Initial state aligned (state_version)")
        print(f"   Initial miss_ratio: {initial_miss_ratio:.4f}")
        print(f"   Initial byte_miss_ratio: {initial_byte_miss_ratio:.4f}")
        print(f"   Observation shape: {initial_observation.shape} (raw_state_dim={CONTEXT_DIM}, obs_indices={self._obs_idx.tolist()})")
        # 【重构】统一输出状态向量详细信息（原始状态），覆盖 26/38/98/110 场景
        if LOH_DEBUG_VERBOSE():
            self._print_state_segments(initial_observation_raw)

        # 记录当前状态版本，供下一步动作对齐
        self.last_state_version = int(initial_data.state_version)

        # 【重要】不在reset()中消费状态或发送ACK
        # 让step(1)去处理第一个状态，保持seq/step完全对齐

        # 训练状态现在由回调函数管理，reset只负责环境重置
        if LOH_DEBUG_BASIC():
            ts = get_monotonic_time()
            print(f"[{ts:.6f}] Reset completed - training state managed by callback")

        return initial_observation, {}

    def _print_state_segments(self, raw_state: np.ndarray):
        """
        统一打印状态向量分段：
        - [global_features]: [0..1]
    - [request_features]: [2..25]
    - [cache_features]: [26..37]（仅当基础维度=38时）
    - [candidate_features_1..6]: 候选统计共72维，按来源分为6行，每行12个值（6个特征×均值/方差）
        始终基于原始 raw_state 打印，避免 obs_keep 的省略影响诊断。
        """
        try:
            base_dim = 38 if _env_state_dim == 38 else 26
            cand_dim = CONTEXT_DIM - base_dim

            # global
            print(f"[global_features]: [{raw_state[0]:.6f}, {raw_state[1]:.6f}]")

            # request
            req_vals = [f"{raw_state[i]:.6f}" for i in range(2, 26) if i < len(raw_state)]
            print(f"[request_features]: [{', '.join(req_vals)}]")

            # cache (only base=38)
            if base_dim == 38:
                cache_vals = [f"{raw_state[i]:.6f}" for i in range(26, 38) if i < len(raw_state)]
                print(f"[cache_features]: [{', '.join(cache_vals)}]")

            # candidate (print last, grouped by 12 with labels)
            if cand_dim >= 72 and len(raw_state) >= base_dim + 72:
                for s in range(6):
                    start = base_dim + s * 12
                    end = start + 12
                    vals = ", ".join([f"{raw_state[i]:.6f}" for i in range(start, end)])
                    print(f"[candidate_features_{s+1}]: [{vals}]")
        except Exception:
            pass

    def set_model(self, model):
        """
        设置 RL model 引用，用于访问 replay buffer 进行事后惩罚

        Args:
            model: SAC 模型实例
        """
        self.model = model
        if LOH_DEBUG_BASIC():
            print(f"[LohEnv] Model reference set, replay buffer available: {hasattr(model, 'replay_buffer')}")
        # 如果回放缓冲区已创建，设置其步数提供者用于记录 first_finalize_step
        try:
            if hasattr(model, 'replay_buffer') and model.replay_buffer is not None:
                model.replay_buffer._env_step_provider = model
        except Exception:
            pass

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
        # 外层总时长（全覆盖）：用手动 record 确保包含整个函数体
        step_wall_t0 = get_monotonic_time()
        with GLOBAL_TIMER.time_function("env.step_phaseA"):
            step_start = get_monotonic_time()
            if LOH_DEBUG_VERBOSE():
                print(f"[Step {self.current_step + 1}] [{step_start:.6f}] step started")

            self.current_step += 1

            # additive phases（互斥求和）临时变量
            _dur_softmax = 0.0
            _dur_read_shm0 = 0.0
            _dur_wait_ready = 0.0
            _dur_write_weights = 0.0
            _dur_wait_new_state = 0.0
            _dur_read_penalty = 0.0
            _dur_process_penalty = 0.0
            _dur_finalize_rewards = 0.0

            # ========== 步骤1: 将RL动作转换为缓存权重 ==========
            # RL算法输出的是logits，需要通过softmax转换为概率分布（权重）
            with GLOBAL_TIMER.time_function("env.step_softmax"):
                action_start = get_monotonic_time()
                action_tensor = torch.from_numpy(action)
                # 引入 softmax 温度，temp>1 更平滑，temp<1 更尖锐
                try:
                    logits = action_tensor / float(self._softmax_temp)
                except Exception:
                    logits = action_tensor
                weights = torch.nn.functional.softmax(logits, dim=-1).numpy()
                action_end = get_monotonic_time()
            _dur_softmax = float(action_end - action_start)

            # 【新增】时间分解：推理时间（总是打印，不管多快）
            inference_duration = action_end - action_start
            if LOH_DEBUG_BASIC():
                print(f"[TIMING][Python] Model inference (softmax): {inference_duration:.6f} seconds")

            if LOH_DEBUG_VERBOSE() and action_end - action_start > 0.001:
                print(f"[{action_end:.6f}] action conversion took {action_end - action_start:.6f} seconds")

            # 记录动作分布的一些统计到 TensorBoard（低频，避免开销）
            try:
                if hasattr(self, 'model') and self.model is not None and hasattr(self.model, 'logger'):
                    if (self.current_step % 100) == 1:  # 每100步记录一次
                        w = np.asarray(weights, dtype=np.float64)
                        w = np.clip(w, 1e-12, 1.0)
                        ent = float(-np.sum(w * np.log(w)))
                        w_max = float(np.max(w))
                        self.model.logger.record("action/entropy", ent)
                        self.model.logger.record("action/max_weight", w_max)
                        self.model.logger.record("action/softmax_temp", float(self._softmax_temp))
            except Exception:
                pass

            # ========== 步骤2: 等待C端发送状态（ready_for_inference=1）==========
            # C端会在每次缓存操作后更新状态，设置ready_for_inference=1
            # Python需要等待这个标志，然后才能写入新权重
            with GLOBAL_TIMER.time_function("env.step_read_shm"):
                read_start = get_monotonic_time()
                data = self._read_shm()
                if data is None:
                    raise RuntimeError("无法读取共享内存")

            write_start = get_monotonic_time()
            _dur_read_shm0 = float(write_start - read_start)
            acked_version = None
            ack_weights_fmt = None
            polling_logged = False
            used_polling_this_step = False

            # 循环等待C端的ready_for_inference=1
            wait_loop_iterations = 0
            wait_loop_start = get_monotonic_time()
            with GLOBAL_TIMER.time_function("env.step_wait_for_ready"):
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
                        _dur_wait_ready = float(wait_for_ready_duration)

                        # ========== 步骤3: 写入权重并发送ACK ==========
                        # 找到了C端的ready状态，现在写入权重并清除ready标志
                        with GLOBAL_TIMER.time_function("env.step_write_weights"):
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
                            _dur_write_weights = float(total_write_duration)

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
        wait_total_start = get_monotonic_time()
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

        # 记录等待新状态总耗时
        try:
            _dur_wait_new_state = float(get_monotonic_time() - wait_total_start)
            GLOBAL_TIMER.record("env.step_wait_new_state", _dur_wait_new_state)
        except Exception:
            pass

        # is_training 状态已在 ACK 阶段同步到训练/推理模式，此处无需额外处理

        # 6. 使用状态作为新观测
        # 先读取“原始”观测（含 state[0:2] 的命中率），用于奖励与日志
        new_observation_raw = np.array(data.state, dtype=np.float32)
        # 如果观测已在0..1范围内，强制clip以避免数值漂移（并与 observation_space 保持一致）
        try:
            new_observation_raw = np.clip(new_observation_raw, 0.0, 1.0)
        except Exception:
            if LOH_DEBUG_BASIC():
                print("[WARN] Failed to clip observation to [0,1], using raw observation")

        # 从原始观测的前两维获取 global_features（命中率），始终用于奖励与info
        obj_hit_ratio = float(new_observation_raw[0])
        byte_hit_ratio = float(new_observation_raw[1])

        # 生成观测：优先根据 obs_keep_indices 做选择；若未选择并且显式关闭命中率，则置零
        if self._obs_idx is not None:
            # 自定义选择：忽略 use_state_hit_features
            new_observation = new_observation_raw[self._obs_idx]
        else:
            # 全量观测
            new_observation = new_observation_raw

        # 追加命中率差分特征
        if self._add_hit_deltas:
            try:
                self._obj_hit_history.append(obj_hit_ratio)
                self._byte_hit_history.append(byte_hit_ratio)
                obj_delta = 0.0; byte_delta = 0.0
                if self._hit_delta_mode == 'tail' and len(self._obj_hit_history) >= self._hit_delta_window:
                    obj_delta = obj_hit_ratio - self._obj_hit_history[0]
                    byte_delta = byte_hit_ratio - self._byte_hit_history[0]
                else:
                    obj_delta = obj_hit_ratio - float(np.mean(self._obj_hit_history))
                    byte_delta = byte_hit_ratio - float(np.mean(self._byte_hit_history))
                obj_delta = max(-1.0, min(1.0, obj_delta))
                byte_delta = max(-1.0, min(1.0, byte_delta))
                new_observation = np.concatenate([new_observation, np.array([obj_delta, byte_delta], dtype=np.float32)])
            except Exception:
                pass

        # 获取驱逐统计
        total_evicted_bytes = data.total_evicted_bytes
        total_evicted_count = data.total_evicted_count

        if LOH_DEBUG_VERBOSE():
            print(f"[Step {self.current_step}] State info:")
            print(f"  obj_hit_ratio (raw[0]): {obj_hit_ratio:.6f}")
            print(f"  byte_hit_ratio (raw[1]): {byte_hit_ratio:.6f}")
            print(f"  total_evicted_bytes: {total_evicted_bytes}")
            print(f"  total_evicted_count: {total_evicted_count}")

        #【重构】输出原始状态向量分段（覆盖 26/38/98/110），与C端顺序一致
        if LOH_DEBUG_VERBOSE():
            self._print_state_segments(new_observation_raw)

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
            _t_rp0 = get_monotonic_time()
            with GLOBAL_TIMER.time_function("env.step_read_penalty"):
                penalties = self._read_penalty_data(data)  # 传入 data 参数
            _dur_read_penalty = float(get_monotonic_time() - _t_rp0)

            if LOH_DEBUG_BASIC():
                print(f"\n[PENALTY] Received {len(penalties)} penalty entries from C-side:")

            # 获取replay buffer（如果存在）
            replay_buffer = None
            if hasattr(self, 'model') and self.model is not None:
                if hasattr(self.model, 'replay_buffer') and self.model.replay_buffer is not None:
                    replay_buffer = self.model.replay_buffer

            # 逐一处理每个惩罚
            _t_pp0 = get_monotonic_time()
            with GLOBAL_TIMER.time_function("env.step_process_penalty"):
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
            _dur_process_penalty = float(get_monotonic_time() - _t_pp0)

            # 清空惩罚队列（通知C端已处理）
            # 使用与共享内存结构一致的字段名：pending_penalty_count
            data.pending_penalty_count = 0
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
                    _t_fr0 = get_monotonic_time()
                    with GLOBAL_TIMER.time_function("env.step_finalize_rewards"):
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
                    _dur_finalize_rewards += float(get_monotonic_time() - _t_fr0)

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
            'obj_hit_ratio': obj_hit_ratio,  # 始终来自原始观测
            'byte_hit_ratio': byte_hit_ratio,  # 始终来自原始观测
            'total_evicted_bytes': total_evicted_bytes,  # 【新增】驱逐统计
            'total_evicted_count': total_evicted_count,  # 【新增】驱逐统计
            'state_version': int(data.state_version),  # 【新增】用于ReplayBuffer追踪
            'weights': weights.copy(),  # 保存本次写入的权重，供ReplayBuffer记录和后续分析
            'hit_ratio_delta_mode': self._hit_delta_mode if self._add_hit_deltas else 'disabled',
        }

        step_end = get_monotonic_time()
        total_duration = step_end - step_start
        try:
            # 统一做非负裁剪，避免时钟抖动造成的微负值
            _dur_softmax = max(0.0, float(_dur_softmax))
            _dur_read_shm0 = max(0.0, float(_dur_read_shm0))
            _dur_wait_ready = max(0.0, float(_dur_wait_ready))
            _dur_write_weights = max(0.0, float(_dur_write_weights))
            _dur_wait_new_state = max(0.0, float(_dur_wait_new_state))
            _dur_read_penalty = max(0.0, float(_dur_read_penalty))
            _dur_process_penalty = max(0.0, float(_dur_process_penalty))
            _dur_finalize_rewards = max(0.0, float(_dur_finalize_rewards))

            parts = (
                _dur_softmax + _dur_read_shm0 + _dur_wait_ready + _dur_write_weights +
                _dur_wait_new_state + _dur_read_penalty + _dur_process_penalty + _dur_finalize_rewards
            )
            misc = max(0.0, float(total_duration - parts))

            GLOBAL_TIMER.record("step.add.softmax", _dur_softmax)
            GLOBAL_TIMER.record("step.add.read_shm0", _dur_read_shm0)
            GLOBAL_TIMER.record("step.add.wait_ready", _dur_wait_ready)
            GLOBAL_TIMER.record("step.add.write_weights", _dur_write_weights)
            GLOBAL_TIMER.record("step.add.wait_new_state", _dur_wait_new_state)
            GLOBAL_TIMER.record("step.add.read_penalty", _dur_read_penalty)
            GLOBAL_TIMER.record("step.add.process_penalty", _dur_process_penalty)
            GLOBAL_TIMER.record("step.add.finalize_rewards", _dur_finalize_rewards)
            GLOBAL_TIMER.record("step.add.misc", misc)
            # 保证 step.add.total 与本步 env.step_total 完全一致（用于对账）
            GLOBAL_TIMER.record("step.add.total", float(total_duration))
            if LOH_DEBUG_BASIC() and (self.current_step % 200 == 0 or abs(total_duration - (parts + misc)) > 1e-4):
                print(f"[STEP-ADD] total={total_duration:.6f}s, sum(parts+misc)={parts + misc:.6f}s, diff={(total_duration - (parts + misc)):.6f}s")
        except Exception:
            pass
        # 记录本步结束的时间戳给回调（仅作为辅助，不参与计时）
        try:
            self._last_step_wall_end_ts = float(step_end)
        except Exception:
            pass
        if LOH_DEBUG_VERBOSE():
            print(f"[{step_end:.6f}] Step {self.current_step} completed, total duration {total_duration:.6f} seconds")
            print("=" * 50)

        # 记录完整 step 总时长（非重叠，大账用）
        try:
            GLOBAL_TIMER.record("env.step_total", float(get_monotonic_time() - step_wall_t0))
        except Exception:
            pass

        return new_observation, reward, terminated, truncated, info

    def close(self):
        """清理资源"""
        self._set_training_mode(False)

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
        # 用于计算 callback 间隔内新增的 penalty 数量
        self._last_total_corrections = 0

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
        with GLOBAL_TIMER.time_function("callback._on_rollout_start"):
            self.rollout_count += 1
            # 记录rollout阶段起点，用于统计 rollout 总耗时
            try:
                self._rollout_t0 = get_monotonic_time()
            except Exception:
                self._rollout_t0 = None
            self._log_with_timestamp(f">>> 推理阶段开始 (rollout #{self.rollout_count}) - 通知C端可以通信", "ROLLOUT")
            # 告诉C端现在是推理阶段，可以正常通信
            self.env_ref._set_training_mode(False)

    def _on_step(self) -> bool:
        """每个step后调用"""
        with GLOBAL_TIMER.time_function("callback._on_step"):
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

                            # 记录到TensorBoard（归类到 reward/ 前缀）
                            self.logger.record("reward/reward_mean", float(np.mean(recent_rewards)))
                            self.logger.record("reward/reward_std", float(np.std(recent_rewards)))
                            self.logger.record("reward/reward_min", float(np.min(recent_rewards)))
                            self.logger.record("reward/reward_max", float(np.max(recent_rewards)))

                            # 【新增】与 reward 同窗口记录命中率（直接命中率，不经奖励变换）
                            try:
                                if hasattr(buffer, 'obj_hit_ratio_at_pos') and buffer.obj_hit_ratio_at_pos is not None:
                                    if buffer.full:
                                        if start_idx + recent_size <= buffer.buffer_size:
                                            recent_obj_hit = buffer.obj_hit_ratio_at_pos[start_idx:start_idx + recent_size]
                                            recent_byte_hit = buffer.byte_hit_ratio_at_pos[start_idx:start_idx + recent_size]
                                        else:
                                            part1_o = buffer.obj_hit_ratio_at_pos[start_idx:]
                                            part2_o = buffer.obj_hit_ratio_at_pos[:((start_idx + recent_size) % buffer.buffer_size)]
                                            recent_obj_hit = np.concatenate([part1_o, part2_o])
                                            part1_b = buffer.byte_hit_ratio_at_pos[start_idx:]
                                            part2_b = buffer.byte_hit_ratio_at_pos[:((start_idx + recent_size) % buffer.buffer_size)]
                                            recent_byte_hit = np.concatenate([part1_b, part2_b])
                                    else:
                                        recent_obj_hit = buffer.obj_hit_ratio_at_pos[start_idx:buffer.pos]
                                        recent_byte_hit = buffer.byte_hit_ratio_at_pos[start_idx:buffer.pos]

                                    if recent_obj_hit.size > 0:
                                        mean_obj_hit = float(np.mean(recent_obj_hit))
                                        self.logger.record("reward/hit_ratio_mean", mean_obj_hit)
                                    if recent_byte_hit.size > 0:
                                        mean_byte_hit = float(np.mean(recent_byte_hit))
                                        self.logger.record("reward/byte_hit_ratio_mean", mean_byte_hit)
                            except Exception:
                                # 诊断项失败不影响训练
                                pass

                            # 如果buffer保存了权重向量，也记录最近窗口的权重统计
                            if hasattr(buffer, 'weights_at_pos') and buffer.weights_at_pos is not None:
                                try:
                                    # recent_weights shape: (recent_size, FEATURE_DIM)
                                    if buffer.full:
                                        wstart = (buffer.pos - recent_size) % buffer.buffer_size
                                        if wstart + recent_size <= buffer.buffer_size:
                                            recent_weights = buffer.weights_at_pos[wstart:wstart + recent_size, :]
                                        else:
                                            part1 = buffer.weights_at_pos[wstart:, :]
                                            part2 = buffer.weights_at_pos[:((wstart + recent_size) % buffer.buffer_size), :]
                                            recent_weights = np.concatenate([part1, part2], axis=0)
                                    else:
                                        wstart = max(0, buffer.pos - recent_size)
                                        recent_weights = buffer.weights_at_pos[wstart:buffer.pos, :]

                                    # 记录每个维度的均值到TensorBoard: weight/buffer_weight_0_mean ...
                                    mean_weights = np.mean(recent_weights, axis=0)
                                    for wi in range(min(len(mean_weights), FEATURE_DIM)):
                                        self.logger.record(f"weight/buffer_weight_{wi}_mean", float(mean_weights[wi]))

                                    # 记录平均范数
                                    try:
                                        mean_norm = float(np.mean(np.linalg.norm(recent_weights, axis=1)))
                                        self.logger.record("weight/buffer_weights_mean_norm", mean_norm)
                                    except Exception:
                                        pass
                                except Exception:
                                    if LOH_DEBUG_BASIC():
                                        self._log_with_timestamp("Warning: failed to record buffer weight stats", "DEBUG")

                            if LOH_DEBUG_BASIC() and self.step_count == 100:
                                self._log_with_timestamp(f"Debug: Recorded reward stats to logger", "DEBUG")

                        # 记录penalty baseline
                        if hasattr(buffer, 'penalty_baseline'):
                            self.logger.record("loh/penalty_baseline", float(buffer.penalty_baseline))

                        # 记录 reward corrections（拆分为 received/applied，并保留总量），统一通过 cstats
                        if hasattr(buffer, 'reward_corrections'):
                            try:
                                cstats = buffer.get_correction_stats() if hasattr(buffer, 'get_correction_stats') else {}
                            except Exception:
                                cstats = {}

                            total_corr = int(getattr(buffer, 'reward_corrections', 0))
                            self.logger.record("loh/total_reward_corrections", total_corr)

                            # 兼容字段：corrections_received / corrections_applied
                            try:
                                self.logger.record("loh/corrections_received", int(cstats.get('corrections_received', cstats.get('corrected_num', 0))))
                                self.logger.record("loh/corrections_applied", int(cstats.get('corrections_applied', cstats.get('finalized_num', 0))))
                            except Exception:
                                pass

                            # 记录 penalty 相关的统计到 TensorBoard（均值与部分 finalize 诊断）
                            try:
                                avg_pen = float(cstats.get('avg_penalty', 0.0))
                                self.logger.record("loh/avg_penalty", avg_pen)
                                # finalize 诊断指标
                                self.logger.record("loh/finalize_last_penalty_sum", float(cstats.get('finalize_last_step_penalty_sum', 0.0)))
                                self.logger.record("loh/applied_penalties_total", float(cstats.get('applied_penalties_total', 0)))
                                # 新增：记录最近一次 finalize 的奖励组件到 TensorBoard（以 reward/ 前缀归类）
                                try:
                                    self.logger.record("reward/component_penalty", float(cstats.get('last_reward_penalty', 0.0)))
                                    self.logger.record("reward/component_miss", float(cstats.get('last_reward_miss', 0.0)))
                                    self.logger.record("reward/component_trend", float(cstats.get('last_reward_trend', 0.0)))
                                    self.logger.record("reward/final_mixed_pre_clip", float(cstats.get('last_reward_final_pre_clip', 0.0)))
                                    self.logger.record("reward/final_mixed", float(cstats.get('last_reward_final', 0.0)))
                                    self.logger.record("reward/clip_delta", float(cstats.get('last_reward_clip_delta', 0.0)))
                                except Exception:
                                    pass
                            except Exception:
                                # 不要让诊断代码中断训练流程
                                if LOH_DEBUG_BASIC():
                                    self._log_with_timestamp("Warning: failed to record TB stats from cstats", "DEBUG")

                            # 记录此回调间的新增 corrections（自上次记录以来的 delta）
                            try:
                                prev = getattr(self, '_last_total_corrections', 0)
                                new = int(buffer.reward_corrections)
                                delta = new - prev
                                self.logger.record("loh/penalty_delta_since_last_tb", float(delta))
                                self._last_total_corrections = new
                            except Exception:
                                pass

                        # corrections summary is intentionally not printed here to avoid
                        # noisy per-step logs; it will be printed at training end.

                        # 记录最新一次写入的权重（仅在callback执行，避免env中高频dump）
                        try:
                            latest_weights = None
                            # 优先使用env中保存的 _last_weights（最精确的时序）
                            if hasattr(self.env_ref, '_last_weights') and getattr(self.env_ref, '_last_weights') is not None:
                                latest_weights = np.array(self.env_ref._last_weights, dtype=np.float32)
                            # 如果env不可用，再尝试从replay buffer读取最近写入的位置
                            elif buffer is not None and hasattr(buffer, 'weights_at_pos') and buffer.weights_at_pos is not None and buffer.size() > 0:
                                last_idx = (buffer.pos - 1) % buffer.buffer_size
                                latest_weights = buffer.weights_at_pos[last_idx]

                            if latest_weights is not None:
                                for wi in range(min(len(latest_weights), FEATURE_DIM)):
                                    self.logger.record(f"weight/weight_{wi}", float(latest_weights[wi]))
                                try:
                                    wnorm = float(np.linalg.norm(latest_weights))
                                    self.logger.record("weight/weights_norm", wnorm)
                                except Exception:
                                    pass
                            # 记录当前一步的 hit ratio（与均值并存）
                            try:
                                if buffer is not None and hasattr(buffer, 'obj_hit_ratio_at_pos') and buffer.obj_hit_ratio_at_pos is not None and buffer.size() > 0:
                                    last_idx = (buffer.pos - 1) % buffer.buffer_size
                                    cur_o = float(buffer.obj_hit_ratio_at_pos[last_idx])
                                    cur_b = float(buffer.byte_hit_ratio_at_pos[last_idx]) if hasattr(buffer, 'byte_hit_ratio_at_pos') and buffer.byte_hit_ratio_at_pos is not None else None
                                    self.logger.record("reward/hit_ratio_current", cur_o)
                                    if cur_b is not None:
                                        self.logger.record("reward/byte_hit_ratio_current", cur_b)
                            except Exception:
                                pass
                        except Exception:
                            if LOH_DEBUG_BASIC():
                                self._log_with_timestamp("Warning: failed to record latest weights to logger", "DEBUG")

                        # 手动触发logger dump（重要！）
                        self.logger.dump(step=self.num_timesteps)

                        # 低频记录观测差分特征相关的配置，便于 TB 比对（数值化编码以适配TB标量）
                        try:
                            mode_enc = 0  # disabled
                            if hasattr(self.env_ref, '_add_hit_deltas') and getattr(self.env_ref, '_add_hit_deltas'):
                                mode = getattr(self.env_ref, '_hit_delta_mode', 'mean')
                                mode_enc = 1 if mode == 'mean' else (2 if mode == 'tail' else 3)
                            self.logger.record("obs/hit_delta_mode", int(mode_enc))
                            # 记录窗口与实际暴露给策略的观察维度
                            if hasattr(self.env_ref, '_hit_delta_window'):
                                self.logger.record("obs/hit_delta_window", int(getattr(self.env_ref, '_hit_delta_window')))
                            try:
                                obs_dim = int(self.env_ref.observation_space.shape[0]) if hasattr(self.env_ref, 'observation_space') else None
                                if obs_dim is not None:
                                    self.logger.record("obs/obs_dim", obs_dim)
                            except Exception:
                                pass
                        except Exception:
                            pass

            return True  # 继续训练

    def _on_rollout_end(self) -> None:
        """推理阶段结束 - 另一个关键时机！"""
        with GLOBAL_TIMER.time_function("callback._on_rollout_end"):
            self._log_with_timestamp(f"<<< 推理阶段结束 (rollout #{self.rollout_count}) - 通知C端进入训练模式", "ROLLOUT")
            self._log_with_timestamp(f"本轮推理收集了 {self.env_ref.current_step} 步数据", "STATS")
            # 汇总并记录 rollout 阶段总耗时
            try:
                if getattr(self, '_rollout_t0', None) is not None:
                    _t1 = get_monotonic_time()
                    GLOBAL_TIMER.record("rollout.phase_total", float(_t1 - self._rollout_t0))
            except Exception:
                pass
            # 当收集的样本数未达到 learning_starts 时，不进入训练模式，保持推理模式，避免 C 端提前切换
            try:
                can_train = True
                target_steps = None
                if hasattr(self, 'model') and self.model is not None:
                    num_steps = getattr(self.model, 'num_timesteps', None)
                    ls = getattr(self.model, 'learning_starts', None)
                    if isinstance(num_steps, (int, np.integer)) and isinstance(ls, (int, np.integer)):
                        target_steps = int(ls)
                        if int(num_steps) < int(ls):
                            can_train = False
                if not can_train:
                    self._log_with_timestamp(
                        f"gating: 当前 num_timesteps={num_steps}, learning_starts={ls}，继续推理模式，等待达到学习起点再切换训练",
                        "GATE"
                    )
                    # 明确保持 C 端为推理状态
                    self.env_ref._set_training_mode(False)
                else:
                    self.env_ref._set_training_mode(True)
            except Exception:
                # 任意异常都不阻断既有流程，回退为原有行为：切换到训练模式
                self.env_ref._set_training_mode(True)

    def _on_training_end(self) -> None:
        """整个训练结束"""
        self._log_with_timestamp("=== SAC训练结束 ===", "END")
        self._log_with_timestamp(f"总计完成 {self.rollout_count} 轮推理，{self.step_count} 个步骤", "STATS")
        # 打印最终的 corrections 统计到 AC 日志（不写入 TensorBoard）
        try:
            if hasattr(self, 'model') and self.model is not None and hasattr(self, 'model') and hasattr(self.model, 'replay_buffer'):
                buffer = self.model.replay_buffer
                if hasattr(buffer, 'get_correction_stats'):
                    cstats = buffer.get_correction_stats()
                    corrected_num = int(cstats.get('corrected_num', cstats.get('corrections', 0)))
                    finalized_num = int(cstats.get('finalized_num', cstats.get('corrections_applied', 0)))
                    correct_on_finalized = int(cstats.get('correct_on_finalized', cstats.get('corrections_on_finalized', 0)))
                    prop = float(cstats.get('prop_on_finalized', 0.0))
                    self._log_with_timestamp(
                        f"FINAL_CORRECTIONS: correct={corrected_num}, finalize={finalized_num}, correct_on_finalized={correct_on_finalized}, prop_on_finalized={prop:.6f}",
                        "FINAL_CORR"
                    )
        except Exception:
            if LOH_DEBUG_BASIC():
                self._log_with_timestamp('Warning: failed to read final correction stats from buffer', 'DEBUG')
        # 训练结束，设置为空闲状态
        self.env_ref._set_training_mode(False)

def main():
    """主函数 - 使用SAC + 事后奖励修正"""
    # 统一使用单调时钟，避免 clock 源差异导致 program.total 与各分项存在微小偏差
    _prog_t0 = get_monotonic_time()
    # 解析命令行参数
    import argparse
    parser = argparse.ArgumentParser(description="LOH Actor-Critic with SAC (Retrospective Reward Correction)")
    parser.add_argument("--miss-ratio-weight", type=float, default=1.0,
                       help="Weight for miss ratio in reward calculation (default: 1.0)")
    # 移除模型原生参数的命令行（统一用环境变量）；保留应用层参数
    parser.add_argument("--exclude-recent-steps", type=int, default=2000,
                       help="Exclude recent N steps when sampling from replay buffer (default: 2000, allow more penalties to arrive)")
    # 可配置的观测维度选择
    parser.add_argument("--obs-keep", type=str, default=os.environ.get("LOH_OBS_KEEP", ""),
                        help="Observation index spec, e.g., 'all', 'nohit', '2-25', '0-1,2-25'.")
    args = parser.parse_args()
    # 打印本次运行的关键配置（与其他启动信息对齐，便于复现实验）
    def _envb(name: str, default: str = ""):
        v = os.environ.get(name)
        return v if v is not None and v != "" else default

    print("=== LOH RL Reward & Obs Config ===")
    print(f"  LOH_PENALTY_MODE/LOH_PENALTY_SCALE: {_envb('LOH_PENALTY_MODE', _envb('LOH_PENALTY_SCALE','reciprocal'))}")
    print(f"  LOH_REWARD_USE_PENALTY: {_envb('LOH_REWARD_USE_PENALTY','1')}  LOH_REWARD_W_PENALTY: {_envb('LOH_REWARD_W_PENALTY','1.0')}")
    print(f"  LOH_REWARD_USE_MISS_RATIO: {_envb('LOH_REWARD_USE_MISS_RATIO','0')}  LOH_REWARD_W_MISS: {_envb('LOH_REWARD_W_MISS','1.0')}  LOH_MISS_COMPONENT: {_envb('LOH_MISS_COMPONENT','neg')}")
    print(f"  LOH_REWARD_USE_TREND: {_envb('LOH_REWARD_USE_TREND','0')}  LOH_REWARD_W_TREND: {_envb('LOH_REWARD_W_TREND','0.5')}  LOH_TREND_MODE: {_envb('LOH_TREND_MODE','slope')}  LOH_TREND_WINDOW: {_envb('LOH_TREND_WINDOW','100')}")
    print(f"  LOH_OBS_ADD_HIT_DELTAS: {_envb('LOH_OBS_ADD_HIT_DELTAS','0')}  LOH_HIT_DELTA_MODE: {_envb('LOH_HIT_DELTA_MODE','mean')}  LOH_HIT_DELTA_WINDOW: {_envb('LOH_HIT_DELTA_WINDOW','100')}")
    try:
        _w_pen = float(_envb('LOH_REWARD_W_PENALTY','1.0')) if _envb('LOH_REWARD_USE_PENALTY','1') in ('1','true','TRUE') else 0.0
    except Exception:
        _w_pen = 0.0
    try:
        _w_miss = float(_envb('LOH_REWARD_W_MISS','1.0')) if _envb('LOH_REWARD_USE_MISS_RATIO','0') in ('1','true','TRUE') else 0.0
    except Exception:
        _w_miss = 0.0
    try:
        _w_trend = float(_envb('LOH_REWARD_W_TREND','0.5')) if _envb('LOH_REWARD_USE_TREND','0') in ('1','true','TRUE') else 0.0
    except Exception:
        _w_trend = 0.0
    print(f"  reward weight sum (enabled only): {_w_pen + _w_miss + _w_trend:.3f}")
    print("===================================")

    # 验证权重参数有效性
    if args.miss_ratio_weight < 0.0 or args.miss_ratio_weight > 1.0:
        print(f"error: miss-ratio-weight must be between 0.0 and 1.0, current value: {args.miss_ratio_weight}")
        sys.exit(1)

    byte_miss_ratio_weight = 1.0 - args.miss_ratio_weight

    # obj_penalty_weight 和 miss_ratio_weight 是同一个值（统一权重）
    obj_penalty_weight = args.miss_ratio_weight
    byte_penalty_weight = byte_miss_ratio_weight

    # ------------------ Seed handling (ENV only) ------------------
    # Only read seed from environment variables. Priority: LOH_RL_SEED > SEED
    seed = None
    loh_seed_raw = os.environ.get("LOH_RL_SEED")
    if loh_seed_raw is not None and loh_seed_raw != "":
        try:
            seed = int(loh_seed_raw)
        except Exception:
            seed = None
    else:
        seed_raw = os.environ.get("SEED")
        if seed_raw is not None and seed_raw != "":
            try:
                seed = int(seed_raw)
            except Exception:
                seed = None

    if seed is not None:
        try:
            import random as _random
            _random.seed(seed)
        except Exception:
            pass
        try:
            np.random.seed(seed)
        except Exception:
            pass
        try:
            torch.manual_seed(seed)
            if torch.cuda.is_available():
                torch.cuda.manual_seed_all(seed)
        except Exception:
            pass
        if LOH_DEBUG_BASIC():
            print(f"Using random seed = {seed} (applied to random/numpy/torch) via environment")
    # ---------------- end seed handling -----------------

    if LOH_DEBUG_BASIC():
        print("LOH RL Agent: Using SAC with Retrospective Reward Correction")
        print("26-dimensional state vector")
        print(f"Reward weights: miss_ratio={args.miss_ratio_weight:.3f}, byte_miss_ratio={byte_miss_ratio_weight:.3f}")
        print(f"Penalty weights: obj_penalty={obj_penalty_weight:.3f}, byte_penalty={byte_penalty_weight:.3f}")
        print(f"exclude_recent_steps={args.exclude_recent_steps}")
        if args.obs_keep:
            print(f"obs_keep={args.obs_keep}")

    # 设置输出目录（使用环境变量RUN_TIMESTAMP以便与test_loh_rl_sb3.sh对齐）
    timestamp = os.environ.get("RUN_TIMESTAMP") or datetime.now().strftime("%m%d_%H%M%S")
    run_dir = f"./runs/{timestamp}"
    os.makedirs(run_dir, exist_ok=True)

    # TensorBoard目录
    tensorboard_log = os.path.join(run_dir, "tensorboard")
    os.makedirs(tensorboard_log, exist_ok=True)

    try:
        # 1. 实例化自定义环境
        # 读取共享内存键（优先环境变量）
        try:
            shm_key = int(os.environ.get("LOH_SHM_KEY", str(SHM_KEY)))
        except Exception:
            shm_key = SHM_KEY
        obs_keep_indices = _parse_obs_keep(args.obs_keep, CONTEXT_DIM) if args.obs_keep else None
        env = LohEnv(
            shm_key=shm_key,
            miss_ratio_weight=args.miss_ratio_weight,
            byte_miss_ratio_weight=byte_miss_ratio_weight,
            obs_keep_indices=obs_keep_indices,
        )

        # 2. 跳过环境检查
        if LOH_DEBUG_BASIC():
            print("⚡ skip environment check, directly start training")

        # 3. 实例化SAC模型（使用自定义ReplayBuffer）
        # 从环境变量读取可覆盖的 SAC 超参数（未设置则使用默认/现有参数）
        def _env_int(name, default):
            try:
                raw = os.environ.get(name)
                return int(raw) if raw is not None and raw != "" else default
            except Exception:
                return default

        def _env_float_local(name, default):
            try:
                raw = os.environ.get(name)
                return float(raw) if raw is not None and raw != "" else default
            except Exception:
                return default

        # ------------------ 统一读取与初始化 SAC 环境变量参数 ------------------
        buffer_size = _env_int("SAC_BUFFER_SIZE", 10000)
        batch_size = _env_int("SAC_BATCH_SIZE", 256)
        learning_rate = _env_float_local("SAC_LEARNING_RATE", 3e-4)
        tau = _env_float_local("SAC_TAU", 0.005)
        gamma = _env_float_local("SAC_GAMMA", 0.99)
        train_freq = _env_int("SAC_TRAIN_FREQ", 16)
        gradient_steps = _env_int("SAC_GRADIENT_STEPS", 1)
        learning_starts = _env_int("SAC_LEARNING_STARTS", 3000)
        ent_coef_raw = os.environ.get("SAC_ENT_COEF", "").strip()
        ent_coef = ent_coef_raw if ent_coef_raw != "" else "auto"
        target_entropy_env = os.environ.get("SAC_TARGET_ENTROPY", "").strip()
        target_entropy_val = None
        if target_entropy_env != "":
            try:
                target_entropy_val = float(target_entropy_env)
            except Exception:
                target_entropy_val = None  # 非数值则忽略
        # 其他可扩展参数占位（例如 future: alpha, beta 等）
        # -------------------------------------------------------------------

        # 统一参数打印改为在下方“从模型实例解析的配置”中输出，避免与实际实例不一致

        # 网络结构与激活函数
        net_arch_env = os.environ.get("SAC_NET_ARCH", "").strip()
        if net_arch_env:
            try:
                net_arch = [int(x) for x in net_arch_env.replace(" ", "").split(",") if x]
            except Exception:
                net_arch = [256, 256]
        else:
            net_arch = [256, 256]

        act_name = os.environ.get("SAC_ACTIVATION_FN", "ReLU").strip().lower()
        if act_name == "tanh":
            activation_fn = torch.nn.Tanh
        elif act_name == "elu":
            activation_fn = torch.nn.ELU
        elif act_name == "leakyrelu":
            activation_fn = torch.nn.LeakyReLU
        else:
            activation_fn = torch.nn.ReLU

        # 将 SAC 超参数收集到一个 dict 中，便于打印与复用
        sac_config = dict(
            buffer_size=buffer_size,
            learning_rate=learning_rate,
            batch_size=batch_size,
            tau=tau,
            gamma=gamma,
            train_freq=train_freq,
            gradient_steps=gradient_steps,
            learning_starts=learning_starts,
            ent_coef=ent_coef,
            tensorboard_log=tensorboard_log,
            policy_kwargs=dict(
                net_arch=net_arch,
                activation_fn=activation_fn,
            ),
            replay_buffer_class=RetrospectiveReplayBuffer,
            replay_buffer_kwargs=dict(
                exclude_recent_steps=args.exclude_recent_steps,
                obj_penalty_weight=obj_penalty_weight,
                byte_penalty_weight=byte_penalty_weight,
            ),
        )

        # 若显式提供了目标熵，则传入模型（否则使用 SB3 默认根据动作维度推断）
        if target_entropy_val is not None:
            sac_config["target_entropy"] = target_entropy_val

        model = ProfiledSAC(
            "MlpPolicy",
            env,
            verbose=1,
            **sac_config,
        )

        # 【新增】将model引用传递给env，使其能访问replay buffer
        env.set_model(model)
        if LOH_DEBUG_BASIC():
            print("✅ Model reference passed to environment for retrospective correction")

        # 4. 开始训练
        if LOH_DEBUG_BASIC():
            # 从 model 实例读取真实的运行配置，避免 kwargs/默认值与实例不一致
            def _fmt_train_freq(tf):
                try:
                    # SB3 TrainFreq dataclass
                    unit = getattr(tf, 'unit', None)
                    freq = getattr(tf, 'frequency', None)
                    if unit is not None and freq is not None:
                        return f"{freq} {str(unit).split('.')[-1]}"
                except Exception:
                    pass
                try:
                    # tuple like (16, 'step')
                    if isinstance(tf, (tuple, list)) and len(tf) == 2:
                        return f"{tf[0]} {tf[1]}"
                except Exception:
                    pass
                return str(tf)

            def _resolved_lr(m):
                try:
                    # lr_schedule(1) 给出初始学习率
                    return float(m.lr_schedule(1))
                except Exception:
                    try:
                        return float(getattr(m, 'learning_rate', learning_rate))
                    except Exception:
                        return None

            # 提取 actor 隐藏层结构与激活函数（尽力，从 model 实例反射）
            def _infer_actor_hidden(policy):
                try:
                    hidden = []
                    activ_name = None
                    # 搜集线性层（排除输出 mu/log_std）
                    for name, mod in policy.actor.named_modules():
                        if isinstance(mod, torch.nn.Linear):
                            if name.endswith('mu') or name.endswith('log_std'):
                                continue
                            hidden.append(int(mod.out_features))
                        # 第一个激活层类名
                        if activ_name is None and isinstance(mod, (
                            torch.nn.ReLU, torch.nn.ELU, torch.nn.LeakyReLU, torch.nn.Tanh
                        )):
                            activ_name = mod.__class__.__name__
                    return hidden if hidden else None, activ_name
                except Exception:
                    return None, None

            resolved_lr = _resolved_lr(model)
            tfmt = _fmt_train_freq(getattr(model, 'train_freq', train_freq))
            hidden_arch, activ = _infer_actor_hidden(model.policy)

            print("🧠 start SAC training with retrospective reward correction")
            print(f"📋 training configuration (resolved from model):")
            print(f"   - algorithm: SAC (off-policy)")
            print(f"   - state dimension: {CONTEXT_DIM}")
            print(f"   - action dimension: {FEATURE_DIM}")
            print(f"   - shm_key: {shm_key}")
            # 关键超参数（从 model 实例读取）
            try:
                print(f"   - buffer_size: {getattr(model.replay_buffer, 'buffer_size', 'N/A')}")
            except Exception:
                print(f"   - buffer_size: N/A")
            print(f"   - batch_size: {getattr(model, 'batch_size', 'N/A')}")
            print(f"   - learning_rate: {resolved_lr if resolved_lr is not None else 'N/A'}")
            print(f"   - tau: {getattr(model, 'tau', 'N/A')}")
            print(f"   - gamma: {getattr(model, 'gamma', 'N/A')}")
            print(f"   - train_freq: {tfmt}")
            print(f"   - gradient_steps: {getattr(model, 'gradient_steps', 'N/A')}")
            print(f"   - learning_starts: {getattr(model, 'learning_starts', 'N/A')}")
            print(f"   - ent_coef: {getattr(model, 'ent_coef', 'N/A')}")
            # 目标熵（从模型实例获取；若不存在则按 SB3 默认 -action_dim 回退）
            try:
                _te = getattr(model, 'target_entropy', None)
            except Exception:
                _te = None
            if _te is None:
                try:
                    _ad = int(np.prod(getattr(model, 'action_space', None).shape)) if getattr(model, 'action_space', None) is not None else int(FEATURE_DIM)
                    _te = -float(_ad)
                except Exception:
                    _te = 'N/A'
            print(f"   - target_entropy: {_te}")
            # 策略网络信息（尽力从实例反射得到）
            if hidden_arch is not None:
                print(f"   - policy.hidden_layers: {hidden_arch}")
            if activ is not None:
                print(f"   - policy.activation_fn: {activ}")
            # 自定义回放缓冲区关键参数（从实例读取）
            try:
                rb = model.replay_buffer
                print(f"   - replay_buffer.exclude_recent_steps: {getattr(rb, 'exclude_recent_steps', 'N/A')}")
                print(f"   - replay_buffer.obj_penalty_weight: {getattr(rb, 'obj_penalty_weight', 'N/A')}")
                print(f"   - replay_buffer.byte_penalty_weight: {getattr(rb, 'byte_penalty_weight', 'N/A')}")
            except Exception:
                pass
            print(f"   - retrospective correction: ENABLED")

        # 记录训练开始时间
        training_start_time = datetime.now()
        if LOH_DEBUG_BASIC():
            print(f"⏰ training start time: {training_start_time.strftime('%Y-%m-%d %H:%M:%S')}")

        # 创建训练回调
        training_callback = LOHTrainingCallback(env_ref=env, verbose=1)

        with GLOBAL_TIMER.time_function("learn.total"):
            model.learn(
                total_timesteps=int(1e12),  # 无限训练，直到C端终止
                callback=training_callback,
                progress_bar=True,
                log_interval=1,  # 每次训练更新都记录（从10改为1，获得更密集的train曲线）
            )

        # 5. 保存最终模型（处理pickle错误）
        training_end_time = datetime.now()
        training_duration = training_end_time - training_start_time
        if LOH_DEBUG_BASIC():
            print(f"⏰ training end time: {training_end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"⌛ total training duration: {str(training_duration).split('.')[0]}")

        # 保存最终模型（移除env以避免pickle错误）
        try:
            model.save(f"{run_dir}/sac_loh_final")
            if LOH_DEBUG_BASIC():
                print(f"� Final model saved as {run_dir}/sac_loh_final.zip")

        except Exception as save_error:
            if LOH_DEBUG_BASIC():
                print(f"⚠️  Failed to save final model: {save_error}")
                import traceback
                traceback.print_exc()

    except KeyboardInterrupt as exc:
        interrupt_time = datetime.now()
        if 'training_start_time' in locals() and LOH_DEBUG_BASIC():
            duration = interrupt_time - training_start_time
            print(f"⏰ training interrupted time: {interrupt_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"⌛ actual running time: {str(duration).split('.')[0]}")

        if LOH_DEBUG_BASIC():
            print(f"⚠️  Training interrupted: {exc}")

        if 'model' in locals() and model is not None:
            try:
                checkpoint_path = f"{run_dir}/sac_loh_interrupted"
                model.save(checkpoint_path)
                if LOH_DEBUG_BASIC():
                    print(f"💾 interrupted model saved as {checkpoint_path}.zip")
            except Exception as save_exc:
                if LOH_DEBUG_BASIC():
                    print(f"⚠️  Failed to save interrupted model: {save_exc}")
                    import traceback
                    traceback.print_exc()

    except Exception as exc:
        if LOH_DEBUG_BASIC():
            print(f"❌ fatal error occurred: {exc}")
        raise

    finally:
        # 记录脚本总时长（非重叠）
        try:
            GLOBAL_TIMER.record("program.total", float(get_monotonic_time() - _prog_t0))
        except Exception:
            pass
        # 无论如何都打印结束时间（如果还没打印过）
        if 'training_start_time' in locals() and 'training_end_time' not in locals():
            final_end_time = datetime.now()
            final_duration = final_end_time - training_start_time
            if LOH_DEBUG_BASIC():
                print(f"⏰ training end time: {final_end_time.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"⌛ total running time: {str(final_duration).split('.')[0]}")

        # 确保回调的训练结束钩子被调用一次（防止 model.learn 在异常路径未调用回调）
        try:
            if 'training_callback' in locals() and training_callback is not None:
                # 使用 public wrapper，内部会转到 _on_training_end
                try:
                    training_callback.on_training_end()
                except Exception:
                    if LOH_DEBUG_BASIC():
                        print("⚠️  training_callback.on_training_end() raised an exception:")
                        traceback.print_exc()
        except Exception:
            # 守护性捕获，确保 finally 能继续执行后续清理
            if LOH_DEBUG_BASIC():
                print("⚠️  Unexpected error when attempting to call training_callback.on_training_end()")
                traceback.print_exc()

        # 打印profiling报告
        GLOBAL_TIMER.report(top_n=30)

        if 'env' in locals() and env is not None:
            env.close()

if __name__ == "__main__":
    main()
