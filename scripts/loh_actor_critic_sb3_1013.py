#!/usr/bin/env python3

#该版本训练时后台写权重

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

# ====== 调试/统计输出全局控制 ======
# 0: 无调试输出  1: 仅关键统计  2: 详细调试
LOH_DEBUG_LEVEL = 2

def LOH_DEBUG_BASIC():
    return LOH_DEBUG_LEVEL >= 1

def LOH_DEBUG_VERBOSE():
    return LOH_DEBUG_LEVEL >= 2

from stable_baselines3 import PPO  # 保留作参考
# from stable_baselines3 import SAC

# 常数定义
FEATURE_DIM = 6
CONTEXT_DIM = 26
STATE_DIM = 28  # CONTEXT_DIM + 2 global features
SHM_KEY = 9876
LOH_DEBUG_LEVEL = 2

def LOH_DEBUG_BASIC():
    return LOH_DEBUG_LEVEL >= 1

def LOH_DEBUG_VERBOSE():
    return LOH_DEBUG_LEVEL >= 2

from stable_baselines3 import PPO  # 保留作参考
# from stable_baselines3 import SAC
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
SHM_KEY = 9876
FEATURE_DIM = 6
CONTEXT_DIM = 26  # 26维状态向量
STATE_DIM = CONTEXT_DIM  # 与C端一致

def create_shared_memory_class(context_dim):
    """动态创建共享内存数据结构类"""
    class SharedMemoryData(ctypes.Structure):
        _fields_ = [
            ("ready_for_inference", ctypes.c_int),
            ("weights_updated", ctypes.c_int),
            ("terminate", ctypes.c_int),
            ("python_ready", ctypes.c_int),
            ("state", ctypes.c_double * context_dim),
            ("weights", ctypes.c_double * FEATURE_DIM),
            ("miss_ratio", ctypes.c_double),
            ("byte_miss_ratio", ctypes.c_double),
            ("reward", ctypes.c_double),
            ("state_version", ctypes.c_uint64),
            ("ack_version", ctypes.c_uint64),
            ("timestamp", ctypes.c_int64),
        ]
    return SharedMemoryData

SharedMemoryData = create_shared_memory_class(CONTEXT_DIM)

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
        # 初始化轮询/后台休眠参数（微秒），无论信号量是否启用都需要这些字段
        # LOH_POLL_SLEEP_US: 主线程轮询间隔（微秒），默认 200 (0.2ms)
        # LOH_BG_SLEEP_US: 后台线程休眠间隔（微秒），默认 500 (0.5ms)
        try:
            self._poll_sleep_us = int(os.environ.get("LOH_POLL_SLEEP_US", "200"))
        except Exception:
            self._poll_sleep_us = 200
        try:
            self._bg_sleep_us = int(os.environ.get("LOH_BG_SLEEP_US", "500"))
        except Exception:
            self._bg_sleep_us = 500

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
        # 背景握手支持：在训练阶段也能及时应答C端，避免超时
        self._last_weights = np.array([1.0 / FEATURE_DIM] * FEATURE_DIM, dtype=np.float64)
        self._bg_last_acked_version = -1
        self._stop_bg = False
        # 仅在主线程长时间未响应时，后台线程执行“应急”应答，平时只维持 python_ready
        self._bg_emergency_ack = True
        threshold_override = _env_float("LOH_BG_EMERGENCY_THRESHOLD", None)
        threshold_override_ms = _env_float("LOH_BG_EMERGENCY_THRESHOLD_MS", None)
        if threshold_override_ms is not None:
            threshold_value = threshold_override_ms / 1000.0
        elif threshold_override is not None:
            threshold_value = threshold_override
        else:
            threshold_value = 0.01
        self._bg_emergency_threshold = max(0.0, threshold_value)
        self._bg_ready_seen_version = -1
        self._bg_ready_seen_t = 0.0
        self._last_step_ack_time = 0.0
        self._bg_loop_counter = 0
        self._bg_last_heartbeat = 0.0
        self._bg_thread = threading.Thread(target=self._ipc_background_pump, name="loh_ipc_bg", daemon=True)
        self._bg_thread.start()

        # 始终允许后台在主线程长时间未响应时执行应急 ack（即使启用了信号量）
        # 这样可以作为对主线程阻塞/调度延迟的安全网，避免C端超时回退到缓存路径
        self._bg_emergency_ack = True

        print("✅ LohEnv initialization completed (fast version)")
        if LOH_DEBUG_BASIC():
            print(
                "   Reward weight config: miss_ratio_weight="
                f"{self.reward_alpha:.3f}, byte_miss_ratio_weight={self.reward_beta:.3f}"
            )
            print(
                "   IPC config: semaphore_requested="
                f"{int(self._sem_requested)}, bg_emergency_threshold={self._bg_emergency_threshold * 1000:.1f}ms"
            )

        # 计算结构字段偏移，便于对单字段进行原子式写入，避免整块覆盖造成竞态
        try:
            self._offset_python_ready = SharedMemoryData.python_ready.offset
            self._offset_ready_for_inference = SharedMemoryData.ready_for_inference.offset
            self._offset_weights_updated = SharedMemoryData.weights_updated.offset
            self._offset_ack_version = SharedMemoryData.ack_version.offset
            self._offset_state_version = SharedMemoryData.state_version.offset
        except Exception:
            # 在部分ctypes实现上不可用时，退化为整块写，但仍尽量减少写入频率
            self._offset_python_ready = None

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
            return True
        except Exception:
            return False

    def _ipc_background_pump(self):
        """后台线程：仅在主线程未及时处理时做“应急”写入，平时只维持 python_ready=1"""
        while not self._stop_bg:
            try:
                data = self._read_shm()
                if not data:
                    time.sleep(self._bg_sleep_us / 1e6)
                    continue
                if data.terminate == 1:
                    # 终止信号，退出后台循环
                    break
                now = get_monotonic_time()
                self._bg_loop_counter += 1
                if LOH_DEBUG_VERBOSE() and (now - self._bg_last_heartbeat) > 1.0:
                    print(
                        f"[BG][heartbeat] sem_enabled={self._sem_enabled} ready={int(data.ready_for_inference)} "
                        f"ack_version={int(data.ack_version)} poll_fallbacks={self._poll_fallback_count}"
                    )
                    self._bg_last_heartbeat = now
                if data.ready_for_inference == 1:
                    # 记录本次 ready 首次被看到的时间
                    if int(data.state_version) != int(self._bg_ready_seen_version):
                        self._bg_ready_seen_version = int(data.state_version)
                        self._bg_ready_seen_t = now
                    # 若主线程长时间未处理，触发一次应急写，避免C端超时
                    elif self._bg_emergency_ack and (now - self._bg_ready_seen_t) > self._bg_emergency_threshold and int(data.state_version) != int(self._bg_last_acked_version):
                        for i in range(FEATURE_DIM):
                            data.weights[i] = float(self._last_weights[i])
                        # 优化方案1: 简化ACK，移除复杂版本校验
                        data.ack_version = int(data.state_version)
                        data.weights_updated = 1
                        data.ready_for_inference = 0
                        data.python_ready = 1
                        self._write_shm(data)
                        self._sem_post(self._sem_ack, label="bg emergency ack")
                        self._bg_last_acked_version = int(data.state_version)
                        # 限制日志，避免刷屏
                        try:
                            if LOH_DEBUG_BASIC():
                                print(f"[BG-FAST][seq {int(data.state_version)}] fast weights written (delay {now - self._bg_ready_seen_t:.3f}s)")
                        except Exception:
                            pass
                # 平时仅维持就绪标志
                if data.python_ready != 1:
                    # 仅写该字段，避免覆盖主线程刚写入的 ack/weights_updated
                    if not self._write_field_int32(self._offset_python_ready, 1):
                        # 回退策略：必要时才整块写
                        data.python_ready = 1
                        self._write_shm(data)
            except Exception:
                # 任何异常不影响主流程，短暂休眠后重试
                pass
            # 优化方案2: 更短的后台轮询间隔，降低响应延迟
            time.sleep(self._bg_sleep_us / 1e6)

    def reset(self, seed=None, options=None):
        """重置环境"""
        super().reset(seed=seed)

        self.current_step = 0
        self.episode_count += 1

        if LOH_DEBUG_BASIC():
            print(f"🔄 Episode #{self.episode_count} Reset - Checking for existing state from C...")

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
                break
            # 告知C端：Python此时处于等待初始状态，已就绪
            if data:
                try:
                    # 仅写 python_ready 字段，避免覆盖C端新状态
                    if not self._write_field_int32(self._offset_python_ready, 1):
                        data.python_ready = 1
                        self._write_shm(data)
                except Exception:
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

        # 收到初始状态后，声明Python已就绪，便于C端后续同步
        try:
            initial_data.python_ready = 1
            self._write_shm(initial_data)
        except Exception:
            pass

        initial_observation = np.array(initial_data.state, dtype=np.float32)
        initial_miss_ratio = initial_data.miss_ratio
        initial_byte_miss_ratio = initial_data.byte_miss_ratio

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
            elif CONTEXT_DIM == 38:
                print(f"[global_features]: [{initial_observation[0]:.6f}, {initial_observation[1]:.6f}]")
                request_features = ", ".join([f"{initial_observation[i]:.6f}" for i in range(2, 26)])
                print(f"[request_features]: [{request_features}]")
                cache_features = ", ".join([f"{initial_observation[i]:.6f}" for i in range(26, 38)])
                print(f"[cache_features]: [{cache_features}]")

        # 记录当前状态版本，供下一步动作对齐
        self.last_state_version = int(initial_data.state_version)

        return initial_observation, {}


    def step(self, action):
        """执行一步操作 - 优化版本"""
        step_start = get_monotonic_time()
        if LOH_DEBUG_VERBOSE():
            print(f"[Step {self.current_step + 1}] [{step_start:.6f}] step started")

        self.current_step += 1

        # 1. 将动作转换为权重
        action_start = get_monotonic_time()
        action_tensor = torch.from_numpy(action)
        weights = torch.nn.functional.softmax(action_tensor, dim=-1).numpy()
        # 将最新权重保存给后台线程使用
        try:
            self._last_weights = weights.astype(np.float64, copy=True)
        except Exception:
            pass
        action_end = get_monotonic_time()

        if LOH_DEBUG_VERBOSE() and action_end - action_start > 0.001:
            print(f"[{action_end:.6f}] action conversion took {action_end - action_start:.6f} seconds")

        # 2. 先响应当前可用状态：读取一次并立即写入权重（对当前ready的版本进行ack）
        read_start = get_monotonic_time()
        data = self._read_shm()
        if data is None:
            raise RuntimeError("无法读取共享内存")

        write_start = get_monotonic_time()
        acked_version = None
        ack_weights_fmt = None
        polling_logged = False
        used_polling_this_step = False
        # 永不跳过：始终等待直到C端提供ready的状态或检测到终止
        while True:
            current = self._read_shm()
            if current is None:
                raise RuntimeError("无法读取共享内存用于写入")

            if current.terminate == 1:
                # 收到终止请求：立即中断训练主循环（由main捕获并优雅退出）
                raise KeyboardInterrupt("Terminate signal received in step() while waiting to ack current ready state")

            if current.ready_for_inference == 1:
                # 优化方案1: 简化权重写入，移除复杂ACK版本校验
                for i in range(FEATURE_DIM):
                    current.weights[i] = float(weights[i])
                acked_version = int(current.state_version)
                self.last_state_version = acked_version
                current.ack_version = int(current.state_version)
                current.weights_updated = 1
                current.ready_for_inference = 0
                current.python_ready = 1
                self._write_shm(current)
                if self._sem_enabled and LOH_DEBUG_VERBOSE():
                    print(f"[SEM][Python] posting ack semaphore for seq {acked_version}")
                self._sem_post(self._sem_ack, label=f"ack seq {acked_version}")
                # 打印实际写入的权重，格式与C端接近（3位小数）
                ack_weights_fmt = ", ".join([f"{float(weights[i]):.3f}" for i in range(FEATURE_DIM)])
                if LOH_DEBUG_VERBOSE():
                    print(f"[seq {acked_version}] Python weights written -> [Written weights]: [{ack_weights_fmt}]")
                self._last_step_ack_time = get_monotonic_time()
                data = current
                break

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

            # 优化方案2: 减少主线程轮询间隔，更快响应
            time.sleep(self._poll_sleep_us / 1e6)
        write_end = get_monotonic_time()

        if used_polling_this_step and LOH_DEBUG_VERBOSE():
            print(f"[POLL][Python] step() handled ready via polling before seq {acked_version}")

        if LOH_DEBUG_VERBOSE():
            print(f"[Step {self.current_step}] Weights: {weights}")
            print(f"[{write_end:.6f}] weights write completed, total time {write_end - step_start:.6f} seconds")

        # 5. 等待C端处理权重并发送新状态（期待出现新版本号）
        wait_start = get_monotonic_time()
        if LOH_DEBUG_VERBOSE():
            print(f"[{wait_start:.6f}] waiting for C-side response (expecting new version != {acked_version})")

        timeout_counter = 0
        # 连续超时检测：sem_timeout=1.0秒，10次连续超时=10秒
        max_consecutive_timeouts = 10
        consecutive_timeouts = 0

        # 心跳日志：让用户知道Python还在运行（每20次检查=20秒）
        heartbeat_interval_checks = 20

        # 空闲检测：state_version/timestamp均无变化超过此时间
        idle_threshold = 15.0
        check_idle_every = 5

        last_seen_version = acked_version
        last_seen_timestamp = None
        last_progress_t = wait_start
        while True:
            # 优先使用信号量阻塞以避免轮询（若信号量不可用或超时则回退到轮询）
            sem_wait_used = False
            if self._sem_enabled:
                sem_wait_used = True
                waited_via_sem = self._sem_wait(self._sem_ready, self._sem_timeout, label="wait@newstate")
                if waited_via_sem:
                    # sem 被唤醒后直接读取共享内存并检查是否为期待的新版本
                    consecutive_timeouts = 0  # 成功等到信号，重置计数器
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
                    consecutive_timeouts += 1
                    self._poll_fallback_count += 1

                    if consecutive_timeouts >= max_consecutive_timeouts:
                        now = get_monotonic_time()
                        elapsed = now - wait_start
                        if LOH_DEBUG_BASIC():
                            print(f"⚠️  C端可能已结束（{consecutive_timeouts}次超时，共{elapsed:.1f}秒）")
                        raise KeyboardInterrupt(f"C-side ended: {consecutive_timeouts} timeouts ({elapsed:.1f}s)")

                    if LOH_DEBUG_BASIC() and consecutive_timeouts <= 3:
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

            # 记录进展（用于检测C端是否挂死）- 每5次循环检查一次
            if timeout_counter % check_idle_every == 0 and new_data:
                if last_seen_timestamp is None:
                    last_seen_timestamp = int(new_data.timestamp)
                if int(new_data.state_version) != int(last_seen_version) or int(new_data.timestamp) != int(last_seen_timestamp):
                    last_seen_version = int(new_data.state_version)
                    last_seen_timestamp = int(new_data.timestamp)
                    last_progress_t = get_monotonic_time()

            time.sleep(self._poll_sleep_us / 1e6)

            timeout_counter += 1

            if timeout_counter % heartbeat_interval_checks == 0:
                now = get_monotonic_time()
                elapsed = now - wait_start
                if LOH_DEBUG_VERBOSE():
                    print(
                        f"[POLL][Python] 心跳：等待C端新状态 — 已等待 {elapsed:.1f}秒 (期望版本 != {acked_version})"
                    )
                # 检查空闲超时
                if (now - last_progress_t) > idle_threshold:
                    if LOH_DEBUG_BASIC():
                        print(f"⚠️  C端无响应（{now - last_progress_t:.1f}秒无活动）")
                    raise KeyboardInterrupt(f"C-side program may have ended: no activity during waiting for new state {now - last_progress_t:.1f}s (state_version/timestamp unchanged), training stopped automatically")

        # 保持python_ready=1，提示C端Python随时可接收（不再清零，避免误判未就绪）

        # 6. 使用状态作为新观测
        new_observation = np.array(data.state, dtype=np.float32)
        new_miss_ratio = data.miss_ratio
        new_byte_miss_ratio = data.byte_miss_ratio

        if LOH_DEBUG_VERBOSE():
            print(f"[Step {self.current_step}] Using state (miss_ratio: {new_miss_ratio:.4f}) — [seq {int(data.state_version)}]")

        #【新增】输出状态向量详细信息 - 与C端格式一致
        if LOH_DEBUG_VERBOSE():
            if CONTEXT_DIM == 26:
                # 26维状态向量输出
                print(f"[global_features]: [{new_observation[0]:.6f}, {new_observation[1]:.6f}]")
                request_features = ", ".join([f"{new_observation[i]:.6f}" for i in range(2, 26)])
                print(f"[request_features]: [{request_features}]")
            elif CONTEXT_DIM == 38:
                # 38维状态向量输出
                print(f"[global_features]: [{new_observation[0]:.6f}, {new_observation[1]:.6f}]")
                request_features = ", ".join([f"{new_observation[i]:.6f}" for i in range(2, 26)])
                print(f"[request_features]: [{request_features}]")
                cache_features = ", ".join([f"{new_observation[i]:.6f}" for i in range(26, 38)])
                print(f"[cache_features]: [{cache_features}]")

        # 7. 计算奖励
        obj_hit_ratio = 1.0 - new_miss_ratio
        byte_hit_ratio = 1.0 - new_byte_miss_ratio
        reward = self.reward_alpha * obj_hit_ratio + self.reward_beta * byte_hit_ratio

        if LOH_DEBUG_VERBOSE():
            print(f"[Step {self.current_step}] Final reward: {self.reward_alpha:.3f} * {obj_hit_ratio:.4f} + {self.reward_beta:.3f} * {byte_hit_ratio:.4f} = {reward:.6f}")

        # 8. 保存性能指标
        self._previous_miss_ratio = new_miss_ratio
        self._previous_byte_miss_ratio = new_byte_miss_ratio

        # 9. 检查终止条件
        terminated = (data.terminate == 1)
        truncated = (self.current_step >= self.max_episode_steps)

        if terminated or truncated:
            if LOH_DEBUG_BASIC():
                print(f"[Step {self.current_step}] Episode ending - terminated={terminated}, truncated={truncated}")

        # 10. 返回信息
        info = {
            'miss_ratio': new_miss_ratio,
            'byte_miss_ratio': new_byte_miss_ratio,
            'step': self.current_step,
            'obj_hit_ratio': obj_hit_ratio,
            'byte_hit_ratio': byte_hit_ratio
        }

        step_end = get_monotonic_time()
        total_duration = step_end - step_start
        if LOH_DEBUG_VERBOSE():
            print(f"[{step_end:.6f}] Step {self.current_step} completed, total duration {total_duration:.6f} seconds")
            print("=" * 50)

        return new_observation, reward, terminated, truncated, info

    def close(self):
        """清理资源"""
        # 停止后台线程
        self._stop_bg = True
        if hasattr(self, '_bg_thread') and self._bg_thread.is_alive():
            try:
                self._bg_thread.join(timeout=1.0)
            except Exception:
                pass
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

# ===== SAC 主流程 =====
def main():
    """主函数 - 去掉所有回调的版本"""

    # 解析命令行参数
    import argparse
    parser = argparse.ArgumentParser(description="LOH Actor-Critic with stable-baselines3")
    parser.add_argument("--miss-ratio-weight", type=float, default=1.0,
                       help="Weight for miss ratio in reward calculation (default: 1.0)")
    parser.add_argument("--tensorboard-log", type=str, default="",
                       help="Optional TensorBoard log directory")
    args = parser.parse_args()

    # 验证权重参数有效性
    if args.miss_ratio_weight < 0.0 or args.miss_ratio_weight > 1.0:
        print(f"error: miss-ratio-weight must be between 0.0 and 1.0, current value: {args.miss_ratio_weight}")
        sys.exit(1)

    byte_miss_ratio_weight = 1.0 - args.miss_ratio_weight

    if LOH_DEBUG_BASIC():
        print("LOH RL Agent: Using 26-dimensional state vector")
        print(f"Reward weights: miss_ratio={args.miss_ratio_weight:.3f}, byte_miss_ratio={byte_miss_ratio_weight:.3f}")

    # 设置输出目录（使用环境变量RUN_TIMESTAMP以便与test_loh_rl_sb3.sh对齐）
    timestamp = os.environ.get("RUN_TIMESTAMP") or datetime.now().strftime("%m%d_%H%M%S")
    run_dir = f"./runs/{timestamp}"
    os.makedirs(run_dir, exist_ok=True)

    # TensorBoard目录
    tensorboard_log = os.path.join(run_dir, "tensorboard")
    os.makedirs(tensorboard_log, exist_ok=True)

    try:
        # 1. 实例化自定义环境（无监控包装）- 传递权重参数
        env = LohEnv(miss_ratio_weight=args.miss_ratio_weight, byte_miss_ratio_weight=byte_miss_ratio_weight)

        # 2. 跳过环境检查以避免干扰训练流程
        if LOH_DEBUG_BASIC():
            print("⚡ skip environment check, directly start training (to avoid interfering with C-Python communication)")

        # 3. 实例化SAC模型（无回调）
        model = PPO(
            "MlpPolicy",
            env,
            verbose=1,
            n_steps=512,
            batch_size=32,
            n_epochs=10,
            learning_rate=1e-4,
            clip_range=0.2,
            ent_coef=0.02,
            vf_coef=0.5,
            max_grad_norm=0.5,
            policy_kwargs=dict(
                net_arch=dict(pi=[128, 128], vf=[128, 128]),
                activation_fn=torch.nn.ReLU,
            ),
            gae_lambda=0.95,
            use_sde=False,
            sde_sample_freq=-1,
            target_kl=0.02,
            tensorboard_log=tensorboard_log,
        )

        # 4. 开始训练（无回调）
        if LOH_DEBUG_BASIC():
            print("🧠 start train model")
            print(f"📋 training configuration (zero timeout optimization version):")
            print(f"   - state dimension: {CONTEXT_DIM}")
            print(f"   - action dimension: {FEATURE_DIM}")

        # 记录训练开始时间
        training_start_time = datetime.now()
        if LOH_DEBUG_BASIC():
            print(f"⏰ training start time: {training_start_time.strftime('%Y-%m-%d %H:%M:%S')}")

        model.learn(
            total_timesteps=int(1e12),  # 无限训练，直到C端终止
            callback=None,  # 无回调
            progress_bar=True,
            tb_log_name="loh_sac_run",
        )

        # 5. 保存最终模型
        training_end_time = datetime.now()
        training_duration = training_end_time - training_start_time
        if LOH_DEBUG_BASIC():
            print(f"⏰ training end time: {training_end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"⌛ total training duration: {str(training_duration).split('.')[0]}")  # 去掉微秒部分

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
    parser.add_argument("--learning-starts", type=int, default=1024,
                        help="Warmup steps before SAC starts updating the networks")
    parser.add_argument("--ent-coef", type=_parse_ent_coef, default="auto",
                        help="Entropy coefficient (float value or 'auto')")
    parser.add_argument("--target-update-interval", type=int, default=1,
                        help="How often (in gradient steps) to update target networks")
    parser.add_argument("--tensorboard-log", type=str, default="",
                        help="Optional TensorBoard log directory")
    args = parser.parse_args()

    if args.miss_ratio_weight < 0.0 or args.miss_ratio_weight > 1.0:
        print(f"error: miss-ratio-weight must be between 0.0 and 1.0, current value: {args.miss_ratio_weight}")
        sys.exit(1)

    byte_miss_ratio_weight = 1.0 - args.miss_ratio_weight

    if LOH_DEBUG_BASIC():
        print("LOH RL Agent: Using 26-dimensional state vector")
        print(f"Reward weights: miss_ratio={args.miss_ratio_weight:.3f}, byte_miss_ratio={byte_miss_ratio_weight:.3f}")
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
            tb_log_name="loh_sac_run",
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
