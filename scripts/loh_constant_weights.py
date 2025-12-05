#!/usr/bin/env python3
"""
LOH 常数策略脚本：
- 不训练模型，只根据给定的 6 维固定权重向 C 端写入 weights；
- 仍然通过共享内存 + POSIX 信号量与 C 端同步，保证 "enable_rl" 路径被使用；
- 用于遍历不同固定权重组合，测试哪组权重在某个 trace 上表现最好。

用法示例：

  # 使用默认均匀权重 [1/6,...,1/6]
  PYTHON_SCRIPT=loh_constant_weights.py \
    LOH_FIXED_WEIGHTS=0.5,1.0,0.8,0.6,0.4,0.3 \
    bash ./scripts/test_loh_rl_sb3.sh data/WikiCDN/wiki_2019t.oracleGeneral.zst 26 0.075

- 通过环境变量 LOH_FIXED_WEIGHTS="w1,w2,w3,w4,w5,w6" 指定权重；
- 若未设置则默认均匀权重；
- 会自动归一化到和为 1。
"""

import os
import sys
import time
import ctypes
import mmap
import math
from typing import List

# ==== 常量与工具 ====
FEATURE_DIM = 6


def _env_truthy(name: str) -> bool:
    v = os.environ.get(name)
    if v is None:
        return False
    return v.strip().lower() in {"1", "true", "yes", "on"}


def _env_float_list(name: str, default: List[float]) -> List[float]:
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        vals = [float(p) for p in parts]
        if len(vals) != FEATURE_DIM:
            print(f"[loh_constant_weights] WARNING: {name} 期望 {FEATURE_DIM} 个值，实际 {len(vals)} 个，使用默认 {default}")
            return default
        return vals
    except Exception as e:
        print(f"[loh_constant_weights] 解析 {name} 失败: {e}，使用默认 {default}")
        return default


def _normalize_weights(ws: List[float]) -> List[float]:
    s = sum(ws)
    if s <= 0 or not math.isfinite(s):
        return [1.0 / FEATURE_DIM] * FEATURE_DIM
    return [w / s for w in ws]


# ==== 状态维度与共享内存结构 ====

# LOH_mr_blocked.c 固定配置：
#   GLOBAL_DIM = 2
#   HIT_MISS_DIM = 24 (LOH_INCLUDE_HIT_MISS_FEATURES=1)
#   CACHE_DIM = 0
#   CAND_FEATURE_DIM = 0
#   SAMPLE_FEATURE_DIM = 0 (LOH_INCLUDE_SAMPLE_FEATURES=0)
# CONTEXT_DIM = 2 + 24 + 0 + 0 + 0 = 26
STATE_DIM = 26


def _env_penalty_enabled() -> bool:
    """检查是否启用 penalty 模式（与 C 端 LOH_ENABLE_PENALTY 一致）"""
    v = os.environ.get("LOH_ENABLE_PENALTY", "0").strip().lower()
    return v in {"1", "true", "yes", "on"}


def create_shared_memory_class(state_dim: int, penalty_enabled: bool = False):
    """
    动态创建与 C 端 shm_data_t 完全一致的 ctypes 结构体。
    C 端定义（LOH_mr_blocked.c）：
      int ready_for_inference;
      int weights_updated;
      int terminate;
      int is_training;
      double state[CONTEXT_DIM];
      double weights[FEATURE_DIM];
      uint64_t total_evicted_bytes;
      uint64_t total_evicted_count;
      uint64_t state_version;
      uint64_t ack_version;
      int64_t timestamp;
      [如果 LOH_ENABLE_PENALTY] int pending_penalty_count;
      uint32_t struct_magic;
      uint32_t context_dim_check;
      uint32_t feature_dim_check;
      uint32_t struct_size_check;
    """
    fields = [
        ("ready_for_inference", ctypes.c_int),
        ("weights_updated", ctypes.c_int),
        ("terminate", ctypes.c_int),
        ("is_training", ctypes.c_int),
        ("state", ctypes.c_double * state_dim),
        ("weights", ctypes.c_double * FEATURE_DIM),
        ("total_evicted_bytes", ctypes.c_uint64),
        ("total_evicted_count", ctypes.c_uint64),
        ("state_version", ctypes.c_uint64),
        ("ack_version", ctypes.c_uint64),
        ("timestamp", ctypes.c_int64),
    ]
    if penalty_enabled:
        fields.append(("pending_penalty_count", ctypes.c_int))
    fields.extend([
        ("struct_magic", ctypes.c_uint32),
        ("context_dim_check", ctypes.c_uint32),
        ("feature_dim_check", ctypes.c_uint32),
        ("struct_size_check", ctypes.c_uint32),
    ])

    class SharedMemoryData(ctypes.Structure):
        _fields_ = fields

    return SharedMemoryData


PENALTY_ENABLED = _env_penalty_enabled()
SharedMemoryData = create_shared_memory_class(STATE_DIM, PENALTY_ENABLED)

# 启动时打印结构信息，方便调试对齐问题
print(f"[loh_constant_weights] STATE_DIM={STATE_DIM}, PENALTY={PENALTY_ENABLED}, "
      f"sizeof={ctypes.sizeof(SharedMemoryData)}, weights_offset={SharedMemoryData.weights.offset}")


# POSIX 信号量绑定（与 loh_inference_only.py 保持一致）
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


def get_monotonic_time() -> float:
    return time.clock_gettime(time.CLOCK_MONOTONIC)


class ConstantPolicyService:
    """简单常数策略服务：每次 C 端请求时写入同一组权重。"""

    def __init__(self, weights: List[float], shm_key: int):
        self.weights = _normalize_weights(weights)
        self.shm_key = shm_key
        self.shm = None
        self.shm_file = None
        self.data = None

        self._sem_ready = None
        self._sem_ack = None
        self._sem_enabled = False
        self._sem_timeout = float(os.environ.get("LOH_SEM_TIMEOUT_S", "1.0"))

        self._attach_shared_memory()
        self._init_semaphores()

        print(f"[loh_constant_weights] 启动常数策略，权重 = {self.weights}")

    def _attach_shared_memory(self):
        shm_path = f"/dev/shm/loh_ac_{self.shm_key}"
        expected_size = ctypes.sizeof(SharedMemoryData)

        if not os.path.exists(shm_path):
            with open(shm_path, "wb") as f:
                f.write(b"\x00" * expected_size)

        # 若大小不匹配则截断
        try:
            current_size = os.path.getsize(shm_path)
            if current_size != expected_size:
                with open(shm_path, "r+b") as f:
                    f.truncate(expected_size)
        except Exception:
            pass

        self.shm_file = open(shm_path, "r+b")
        self.shm = mmap.mmap(self.shm_file.fileno(), expected_size)
        os.chmod(shm_path, 0o666)

        # 将 mmap 视为结构体
        buf = (ctypes.c_char * expected_size).from_buffer(self.shm)
        self.data = SharedMemoryData.from_buffer(buf)
        print(f"[loh_constant_weights] 已连接共享内存 {shm_path} (size={expected_size})")

    def _init_semaphores(self):
        # 可通过环境开关禁用信号量
        disable_override = os.environ.get("LOH_DISABLE_SEMAPHORE")
        enable_override = os.environ.get("LOH_ENABLE_SEMAPHORE")
        if disable_override is not None:
            sem_requested = not _env_truthy("LOH_DISABLE_SEMAPHORE")
        elif enable_override is not None:
            sem_requested = _env_truthy("LOH_ENABLE_SEMAPHORE")
        else:
            sem_requested = True

        if not sem_requested:
            print("[loh_constant_weights] 信号量已禁用，使用轮询模式")
            return

        ready_name = f"/loh_ac_ready_{self.shm_key}".encode()
        ack_name = f"/loh_ac_ack_{self.shm_key}".encode()

        sem_ready = libc.sem_open(ready_name, os.O_CREAT, 0o666, 0)
        if sem_ready == SEM_FAILED:
            err = ctypes.get_errno()
            print(f"[loh_constant_weights] sem_open ready 失败: {os.strerror(err)}，退化为轮询")
            return

        sem_ack = libc.sem_open(ack_name, os.O_CREAT, 0o666, 0)
        if sem_ack == SEM_FAILED:
            err = ctypes.get_errno()
            print(f"[loh_constant_weights] sem_open ack 失败: {os.strerror(err)}，退化为轮询")
            libc.sem_close(sem_ready)
            return

        self._sem_ready = sem_ready
        self._sem_ack = sem_ack
        self._sem_enabled = True

        # 清理残留信号
        self._sem_drain(self._sem_ready)
        self._sem_drain(self._sem_ack)

        print("[loh_constant_weights] 信号量模式已启用")

    def _sem_drain(self, sem):
        if not sem:
            return
        while True:
            r = libc.sem_trywait(sem)
            if r != 0:
                break

    def _wait_ready(self) -> bool:
        """等待 C 端 ready_for_inference==1。返回 False 表示应退出。"""
        if self.data is None:
            return False

        if self._sem_enabled:
            # 有信号量就优先 sem_timedwait
            ts = Timespec()
            sec = int(self._sem_timeout)
            nsec = int((self._sem_timeout - sec) * 1e9)
            now = time.time()
            ts.tv_sec = int(now) + sec
            ts.tv_nsec = nsec
            r = libc.sem_timedwait(self._sem_ready, ctypes.byref(ts))
            if r != 0:
                # 超时或错误时退化为轮询
                pass

        # 简单轮询，避免 busy-wait
        poll_sleep_us = int(os.environ.get("LOH_POLL_SLEEP_US", "200"))
        while True:
            if self.data.terminate:
                return False
            if self.data.ready_for_inference:
                return True
            time.sleep(poll_sleep_us / 1e6)

    def _post_ack(self):
        if self._sem_enabled and self._sem_ack:
            libc.sem_post(self._sem_ack)

    def run(self):
        step = 0
        start = get_monotonic_time()
        try:
            while True:
                if not self._wait_ready():
                    print("[loh_constant_weights] 收到 terminate 或等待失败，退出")
                    break

                # 写入固定权重
                for i in range(FEATURE_DIM):
                    self.data.weights[i] = float(self.weights[i])
                self.data.weights_updated = 1
                self.data.ready_for_inference = 0
                # 可选：写入 is_training=0 表示推理模式
                self.data.is_training = 0

                # 递增版本号（若需要）
                self.data.ack_version = self.data.state_version

                # 通过信号量通知 C 端
                self._post_ack()

                step += 1
                if step % 1000 == 0:
                    elapsed = get_monotonic_time() - start
                    print(f"[loh_constant_weights] 已响应 {step} 次 RL 请求，用时 {elapsed:.1f}s")

        finally:
            if self._sem_ready:
                libc.sem_close(self._sem_ready)
            if self._sem_ack:
                libc.sem_close(self._sem_ack)
            if self.shm is not None:
                self.shm.close()
            if self.shm_file is not None:
                self.shm_file.close()


def main():
    # 从环境读取 SHM_KEY（与 test_loh_rl_sb3.sh 保持一致）
    shm_key_str = os.environ.get("LOH_SHM_KEY", "9876")
    try:
        shm_key = int(shm_key_str)
    except Exception:
        shm_key = 9876

    default_w = [1.0 / FEATURE_DIM] * FEATURE_DIM
    weights = _env_float_list("LOH_FIXED_WEIGHTS", default_w)

    print(f"[loh_constant_weights] STATE_DIM={STATE_DIM}, 使用 LOH_FIXED_WEIGHTS={weights}, SHM_KEY={shm_key}")

    service = ConstantPolicyService(weights, shm_key)
    service.run()


if __name__ == "__main__":
    main()

