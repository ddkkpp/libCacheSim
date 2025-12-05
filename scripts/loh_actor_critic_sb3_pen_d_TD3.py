#!/usr/bin/env python3
# Print actual script filename at runtime (dynamic)
import os, sys
_loh_script_name = os.path.basename(__file__) if '__file__' in globals() and __file__ else (os.path.basename(sys.argv[0]) if sys.argv and sys.argv[0] else '<unknown>')
print(f"[LOH SCRIPT] { _loh_script_name }")

# 该文件基于 loh_actor_critic_sb3.py 修改为使用 TD3 的实现

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
import cProfile
import pstats
import traceback
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
        self.timings = defaultdict(list)
        self.call_counts = defaultdict(int)

    def __getstate__(self):
        return {'timings': dict(self.timings), 'call_counts': dict(self.call_counts)}

    def __setstate__(self, state):
        self.timings = defaultdict(list, state['timings'])
        self.call_counts = defaultdict(int, state['call_counts'])

    def time_function(self, func_name):
        class TimerContext:
            def __init__(self, timer, name):
                self.timer = timer
                self.name = name
                self.start = None

            def __enter__(self):
                self.start = time.perf_counter()
                return self

            def __exit__(self, *args):
                duration = time.perf_counter() - self.start
                self.timer.timings[self.name].append(duration)
                self.timer.call_counts[self.name] += 1

        return TimerContext(self, func_name)

    def report(self, top_n=20):
        print("\n" + "="*80)
        print("⏱️  PROFILING REPORT (Top Functions by Total Time)")
        print("="*80)
        stats = []
        for name, durations in self.timings.items():
            total_time = sum(durations)
            avg_time = total_time / len(durations)
            max_time = max(durations)
            min_time = min(durations)
            count = self.call_counts[name]
            stats.append({'name': name, 'total': total_time, 'avg': avg_time, 'max': max_time, 'min': min_time, 'count': count})
        stats.sort(key=lambda x: x['total'], reverse=True)
        print(f"{ 'Function':<40} {'Calls':>8} {'Total(s)':>10} {'Avg(ms)':>10} {'Max(ms)':>10}")
        print("-"*80)
        for stat in stats[:top_n]:
            print(f"{stat['name']:<40} {stat['count']:>8} {stat['total']:>10.4f} {stat['avg']*1000:>10.2f} {stat['max']*1000:>10.2f}")
        print("="*80 + "\n")

# 全局计时器
GLOBAL_TIMER = FunctionTimer()

from stable_baselines3 import PPO
from stable_baselines3 import TD3
from stable_baselines3.common.buffers import ReplayBuffer
from stable_baselines3.common.noise import NormalActionNoise
import numpy as np


class ProfiledTD3(TD3):
    """TD3 带全局计时的子类"""

    def train(self, gradient_steps: int, batch_size: int = 64):
        with GLOBAL_TIMER.time_function("TD3.train_total"):
            return super().train(gradient_steps, batch_size)

import torch

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

def get_monotonic_time():
    return time.clock_gettime(time.CLOCK_MONOTONIC)


def _env_flag(name: str, default: bool) -> bool:
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
def _env_truthy(name: str) -> bool:
    v = os.environ.get(name)
    if v is None:
        return False
    return v.strip().lower() in {"1", "true", "yes", "on"}

def get_state_dim() -> int:
    """返回完整 CONTEXT_DIM (基础 26/38 + 可选候选特征 72)，完全由 LOH_INCLUDE_* 决定。"""
    base = 38
    cache_flag = os.environ.get("LOH_INCLUDE_CACHE_FEATURES", "").strip().lower()
    if cache_flag in {"0", "false", "no", "off"}:
        base = 26
    cand_flag = os.environ.get("LOH_INCLUDE_CANDIDATE_FEATURES", "0").strip().lower()
    cand_enabled = cand_flag in {"1", "true", "yes", "on"}
    return base + (72 if cand_enabled else 0)

CONTEXT_DIM = get_state_dim()
STATE_DIM = CONTEXT_DIM

class PenaltyEntry(ctypes.Structure):
    _fields_ = [
        ("penalty_version", ctypes.c_uint64),
        ("eviction_to_access", ctypes.c_int64),
        ("obj_size", ctypes.c_int64),
        ("obj_id", ctypes.c_uint64),
    ]


class SharedMemoryData(ctypes.Structure):
    _fields_ = [
        ("ready_for_inference", ctypes.c_int),
        ("weights_updated", ctypes.c_int),
        ("terminate", ctypes.c_int),
        ("is_training", ctypes.c_int),
        ("state", ctypes.c_double * CONTEXT_DIM),
        ("weights", ctypes.c_double * FEATURE_DIM),
        ("total_evicted_bytes", ctypes.c_uint64),
        ("total_evicted_count", ctypes.c_uint64),
        ("state_version", ctypes.c_uint64),
        ("ack_version", ctypes.c_uint64),
        ("timestamp", ctypes.c_int64),
        ("pending_penalty_count", ctypes.c_int),
    ]


def create_shared_memory_class(context_dim):
    if context_dim != CONTEXT_DIM:
        import warnings
        warnings.warn(f"create_shared_memory_class called with context_dim={context_dim}, but using fixed CONTEXT_DIM={CONTEXT_DIM}")
    return SharedMemoryData

# RetrospectiveReplayBuffer and LohEnv implementations are identical to SAC file
# For brevity we will import the implementations from the original module to avoid duplication
from loh_actor_critic_sb3 import RetrospectiveReplayBuffer, LohEnv, LOHTrainingCallback, GLOBAL_TIMER, _parse_obs_keep

def main():
    """主函数 - 使用TD3 + 事后奖励修正"""

    import argparse
    parser = argparse.ArgumentParser(description="LOH Actor-Critic with TD3 (Retrospective Reward Correction)")
    parser.add_argument("--miss-ratio-weight", type=float, default=1.0,
                       help="Weight for miss ratio in reward calculation (default: 1.0)")
    # 保留自定义参数：与模型原生无关
    parser.add_argument("--exclude-recent-steps", type=int, default=2000,
                       help="Exclude recent N steps when sampling from replay buffer (default: 2000, allow more penalties to arrive)")
    args = parser.parse_args()

    if args.miss_ratio_weight < 0.0 or args.miss_ratio_weight > 1.0:
        print(f"error: miss-ratio-weight must be between 0.0 and 1.0, current value: {args.miss_ratio_weight}")
        sys.exit(1)

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
        # Set seeds for Python random, numpy and torch to improve reproducibility
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

    byte_miss_ratio_weight = 1.0 - args.miss_ratio_weight
    obj_penalty_weight = args.miss_ratio_weight
    byte_penalty_weight = byte_miss_ratio_weight

    if LOH_DEBUG_BASIC():
        print("LOH RL Agent: Using TD3 with Retrospective Reward Correction")
        print(f"{STATE_DIM}-dimensional state vector")
        print(f"Reward weights: miss_ratio={args.miss_ratio_weight:.3f}, byte_miss_ratio={byte_miss_ratio_weight:.3f}")
        print(f"Penalty weights: obj_penalty={obj_penalty_weight:.3f}, byte_penalty={byte_penalty_weight:.3f}")
        print(f"Shared memory key (LOH_SHM_KEY): {SHM_KEY}")
        print(f"exclude_recent_steps={args.exclude_recent_steps}")

    timestamp = os.environ.get("RUN_TIMESTAMP") or datetime.now().strftime("%m%d_%H%M%S")
    run_dir = f"./runs/{timestamp}"
    os.makedirs(run_dir, exist_ok=True)
    tensorboard_log = os.path.join(run_dir, "tensorboard")
    os.makedirs(tensorboard_log, exist_ok=True)

    try:
        # 读取共享内存键
        try:
            shm_key = int(os.environ.get("LOH_SHM_KEY", str(SHM_KEY)))
        except Exception:
            shm_key = SHM_KEY
        # 观测空间配置：仅支持 LOH_OBS_KEEP（不再支持 LOH_USE_STATE_HIT 开关）
        obs_keep_spec = os.environ.get("LOH_OBS_KEEP", "").strip()
        obs_keep_indices = _parse_obs_keep(obs_keep_spec, CONTEXT_DIM) if obs_keep_spec else None

        env = LohEnv(
            shm_key=shm_key,
            miss_ratio_weight=args.miss_ratio_weight,
            byte_miss_ratio_weight=byte_miss_ratio_weight,
            obs_keep_indices=obs_keep_indices,
        )

        if LOH_DEBUG_BASIC():
            print("⚡ skip environment check, directly start training")
            # 打印观测配置
            visible_dim = (len(obs_keep_indices) if (obs_keep_indices is not None and len(obs_keep_indices) > 0)
                           else CONTEXT_DIM)
            print("🧩 observation config:")
            print(f"   - obs_keep (LOH_OBS_KEEP): '{obs_keep_spec or ''}'")
            if obs_keep_indices:
                print(f"   - obs_keep_indices parsed: {obs_keep_indices}")
            print(f"   - visible_state_dim: {visible_dim}")

        # TD3 超参数（统一使用一致的 env 解析辅助函数）
        def env_int(name: str, default: int) -> int:
            raw = os.environ.get(name)
            if raw is None or raw == "":
                return default
            try:
                return int(raw)
            except Exception:
                return default

        def env_float(name: str, default: float) -> float:
            raw = os.environ.get(name)
            if raw is None or raw == "":
                return default
            try:
                return float(raw)
            except Exception:
                return default

        def env_maybe_float(name: str):
            raw = os.environ.get(name)
            if raw is None or raw == "":
                return None
            try:
                return float(raw)
            except Exception:
                return None

        # 基本超参：显式设置“之前代码默认”（非噪声参数），环境变量可覆盖；噪声仍使用 SB3 默认，除非显式提供
        td3_config = dict(
            tensorboard_log=tensorboard_log,
            buffer_size=env_int("TD3_BUFFER_SIZE", 10000),         # previous default 10000
            learning_starts=env_int("TD3_LEARNING_STARTS", 3000),  # previous default 3000
            batch_size=env_int("TD3_BATCH_SIZE", 256),             # previous/SB3 default 256
            learning_rate=env_float("TD3_LEARNING_RATE", 3e-4),    # previous/SB3 default 3e-4
            gamma=env_float("TD3_GAMMA", 0.99),                    # previous/SB3 default 0.99
            tau=env_float("TD3_TAU", 0.005),                       # previous/SB3 default 0.005
            train_freq=(env_int("TD3_TRAIN_FREQ", 16), "step"),   # previous default (16, 'step')
            gradient_steps=env_int("TD3_GRADIENT_STEPS", 1),       # previous/SB3 default 1
            policy_delay=env_int("TD3_POLICY_DELAY", 2),           # previous/SB3 default 2
            policy_kwargs=dict(net_arch=[256, 256], activation_fn=torch.nn.ReLU),
            replay_buffer_class=RetrospectiveReplayBuffer,
            replay_buffer_kwargs=dict(
                exclude_recent_steps=args.exclude_recent_steps,
                obj_penalty_weight=obj_penalty_weight,
                byte_penalty_weight=byte_penalty_weight,
            ),
        )

        # 可选 policy_kwargs（在默认基础上覆盖）
        net_arch_env = os.environ.get("TD3_NET_ARCH", "").strip()
        act_name = os.environ.get("TD3_ACTIVATION_FN", "").strip().lower()
        policy_kwargs = dict(td3_config.get("policy_kwargs", {}))
        if net_arch_env:
            try:
                policy_kwargs["net_arch"] = [int(x) for x in net_arch_env.replace(" ", "").split(",") if x]
            except Exception:
                pass
        if act_name:
            if act_name == "tanh":
                activation_fn = torch.nn.Tanh
            elif act_name == "elu":
                activation_fn = torch.nn.ELU
            elif act_name == "leakyrelu":
                activation_fn = torch.nn.LeakyReLU
            elif act_name == "relu":
                activation_fn = torch.nn.ReLU
            else:
                activation_fn = None
            if activation_fn is not None:
                policy_kwargs["activation_fn"] = activation_fn
        if policy_kwargs:
            td3_config["policy_kwargs"] = policy_kwargs

        # 噪声相关：保持 SB3 默认；若提供环境变量则启用
        tpn = env_maybe_float("TD3_TARGET_POLICY_NOISE")
        if tpn is not None:
            td3_config["target_policy_noise"] = tpn
        tnc = env_maybe_float("TD3_TARGET_NOISE_CLIP")
        if tnc is not None:
            td3_config["target_noise_clip"] = tnc

        exploration_sigma_raw = os.environ.get("TD3_ACTION_NOISE")
        if exploration_sigma_raw is not None and exploration_sigma_raw != "":
            try:
                action_dim = env.action_space.shape[0]
                exploration_sigma = float(exploration_sigma_raw)
                action_noise = NormalActionNoise(mean=np.zeros(action_dim), sigma=exploration_sigma * np.ones(action_dim))
                td3_config["action_noise"] = action_noise
            except Exception:
                pass

        model = ProfiledTD3(
            "MlpPolicy",
            env,
            verbose=1,
            **td3_config,
        )

        env.set_model(model)
        if LOH_DEBUG_BASIC():
            print("✅ Model reference passed to environment for retrospective correction")

        if LOH_DEBUG_BASIC():
            # 从模型对象读取已生效的参数，避免与 kwargs 不一致
            def _fmt_noise(n):
                try:
                    import numpy as _np
                    if n is None:
                        return "None"
                    name = n.__class__.__name__
                    sigma = getattr(n, 'sigma', None)
                    if sigma is not None:
                        # 展示第一维即可
                        try:
                            val = float(_np.array(sigma).reshape(-1)[0])
                            return f"{name}(sigma~{val:.4f})"
                        except Exception:
                            return f"{name}(sigma=...)"
                    return name
                except Exception:
                    return str(n)

            print("🧠 start TD3 training with retrospective reward correction")
            print(f"📋 training configuration (resolved from model):")
            print(f"   - algorithm: TD3 (off-policy)")
            print(f"   - state dimension: {CONTEXT_DIM}")
            print(f"   - action dimension: {FEATURE_DIM}")
            print(f"   - shm_key: {shm_key}")
            print(f"   - buffer_size: {getattr(model, 'buffer_size', 'N/A')}  # previous default 10000")
            print(f"   - learning_starts: {getattr(model, 'learning_starts', 'N/A')}  # previous default 3000")
            print(f"   - batch_size: {getattr(model, 'batch_size', 'N/A')}   # previous/SB3 default 256")
            print(f"   - learning_rate: {getattr(model, 'learning_rate', 'N/A')}  # previous/SB3 default 3e-4")
            print(f"   - gamma: {getattr(model, 'gamma', 'N/A')}   # previous/SB3 default 0.99")
            print(f"   - tau: {getattr(model, 'tau', 'N/A')}      # previous/SB3 default 0.005")
            print(f"   - train_freq: {getattr(model, 'train_freq', 'N/A')}  # previous default (16, 'step')")
            print(f"   - gradient_steps: {getattr(model, 'gradient_steps', 'N/A')}  # previous/SB3 default 1")
            print(f"   - policy_delay: {getattr(model, 'policy_delay', 'N/A')}  # previous/SB3 default 2")
            # 噪声三项从模型读取
            print(f"   - target_policy_noise: {getattr(model, 'target_policy_noise', 'N/A')}  # SB3 default 0.2 (env-overridable)")
            print(f"   - target_noise_clip: {getattr(model, 'target_noise_clip', 'N/A')}    # SB3 default 0.5 (env-overridable)")
            print(f"   - action_noise: {_fmt_noise(getattr(model, 'action_noise', None))}  # SB3 default None")

        training_start_time = datetime.now()
        if LOH_DEBUG_BASIC():
            print(f"⏰ training start time: {training_start_time.strftime('%Y-%m-%d %H:%M:%S')}")

        training_callback = LOHTrainingCallback(env_ref=env, verbose=1)

        model.learn(
            total_timesteps=int(1e12),
            callback=training_callback,
            progress_bar=True,
            log_interval=1,
        )

        training_end_time = datetime.now()
        training_duration = training_end_time - training_start_time
        if LOH_DEBUG_BASIC():
            print(f"⏰ training end time: {training_end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"⌛ total training duration: {str(training_duration).split('.')[0]}")

        try:
            model.save(f"{run_dir}/td3_loh_final")
            if LOH_DEBUG_BASIC():
                print(f"� Final model saved as {run_dir}/td3_loh_final.zip")
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
                checkpoint_path = f"{run_dir}/td3_loh_interrupted"
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
        if 'training_start_time' in locals() and 'training_end_time' not in locals():
            final_end_time = datetime.now()
            final_duration = final_end_time - training_start_time
            if LOH_DEBUG_BASIC():
                print(f"⏰ training end time: {final_end_time.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"⌛ total running time: {str(final_duration).split('.')[0]}")

        try:
            if 'training_callback' in locals() and training_callback is not None:
                try:
                    training_callback.on_training_end()
                except Exception:
                    if LOH_DEBUG_BASIC():
                        print("⚠️  training_callback.on_training_end() raised an exception:")
                        traceback.print_exc()
        except Exception:
            if LOH_DEBUG_BASIC():
                print("⚠️  Unexpected error when attempting to call training_callback.on_training_end()")
                traceback.print_exc()

        GLOBAL_TIMER.report(top_n=30)

        if 'env' in locals() and env is not None:
            env.close()


if __name__ == "__main__":
    main()
