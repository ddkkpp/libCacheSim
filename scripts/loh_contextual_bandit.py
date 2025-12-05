#!/usr/bin/env python3
"""
LOH Contextual Bandit 权重搜索脚本（LinUCB 版本）：
- 使用 26 维原始状态作为上下文（若 C 端 state 更长，仅取前 26 维）；
- 在一组候选权重臂之间，用线性 UCB 上下文 bandit 进行在线选择；
- 仍然通过共享内存 + POSIX 信号量与 C 端同步，保证 enable_rl 路径被使用；
- 奖励定义默认为 r = - miss_ratio（越小越好），也支持 delta_miss 模式。

用法示例：

  # 使用默认候选权重集合 + LinUCB 上下文 bandit
  PYTHON_SCRIPT=loh_contextual_bandit.py \
    bash ./scripts/test_loh_rl_sb3.sh data/WikiCDN/wiki_2019t.oracleGeneral.zst 26 0.075

环境变量：
  LOH_BANDIT_ARMS          自定义权重臂集合，格式：
                           "w11,w12,w13,w14,w15,w16;w21,w22,...;..."，每个臂 6 个数
  LOH_CTX_BANDIT_ALPHA     LinUCB 中置信区间系数 alpha，默认 1.0
  LOH_BANDIT_REWARD_MODE   奖励模式："neg_miss"（默认）或 "delta_miss"（使用 miss_ratio 差分）
  LOH_SEM_TIMEOUT_S        信号量等待超时时间（秒），默认 1.0
  LOH_POLL_SLEEP_US        轮询等待 ready_for_inference 时的 sleep 微秒，默认 200
"""

import os
import sys
import time
import ctypes
import mmap
import math
from typing import List

import numpy as np

FEATURE_DIM = 6
CONTEXT_DIM = 26  # 仅使用前 26 维作为上下文


def _env_truthy(name: str) -> bool:
    v = os.environ.get(name)
    if v is None:
        return False
    return v.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except Exception:
        return default


def _normalize_weights(ws: List[float]) -> List[float]:
    s = sum(ws)
    if s <= 0 or not math.isfinite(s):
        return [1.0 / FEATURE_DIM] * FEATURE_DIM
    return [w / s for w in ws]


def _parse_arms_from_env() -> List[List[float]]:
    raw = os.environ.get("LOH_BANDIT_ARMS")
    if not raw:
        return []
    arms: List[List[float]] = []
    for arm_str in raw.split(";"):
        arm_str = arm_str.strip()
        if not arm_str:
            continue
        try:
            vals = [float(x.strip()) for x in arm_str.split(",") if x.strip()]
            if len(vals) == FEATURE_DIM:
                arms.append(_normalize_weights(vals))
        except Exception:
            continue
    return arms


def get_state_dim() -> int:
    """推断 C 端 state 数组长度，用于共享内存结构对齐。

    注意：上下文只使用前 CONTEXT_DIM=26 维，但结构体长度必须与 C 端一致。
    现在完全由 LOH_INCLUDE_CACHE_FEATURES / LOH_INCLUDE_CANDIDATE_FEATURES 决定，不再读取 LOH_STATE_DIM。
    """
    base = 38
    cache_flag = os.environ.get("LOH_INCLUDE_CACHE_FEATURES", "").strip().lower()
    if cache_flag in {"0", "false", "no", "off"}:
        base = 26

    cand_flag = os.environ.get("LOH_INCLUDE_CANDIDATE_FEATURES", "0").strip().lower()
    cand_enabled = cand_flag in {"1", "true", "yes", "on"}
    return base + (72 if cand_enabled else 0)


STATE_DIM = get_state_dim()


class SharedMemoryData(ctypes.Structure):
    _fields_ = [
        ("ready_for_inference", ctypes.c_int),
        ("weights_updated", ctypes.c_int),
        ("terminate", ctypes.c_int),
        ("is_training", ctypes.c_int),
        ("state", ctypes.c_double * STATE_DIM),
        ("weights", ctypes.c_double * FEATURE_DIM),
        ("miss_ratio", ctypes.c_double),
        ("byte_miss_ratio", ctypes.c_double),
        ("reward", ctypes.c_double),
        ("state_version", ctypes.c_uint64),
        ("ack_version", ctypes.c_uint64),
        ("timestamp", ctypes.c_int64),
    ]


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


class LinUCBBandit:
    """简单的 LinUCB 上下文 bandit，每个臂一套线性模型。"""

    def __init__(self, n_arms: int, context_dim: int, alpha: float, reward_mode: str = "neg_miss"):
        self.n_arms = n_arms
        self.d = context_dim
        self.alpha = alpha
        self.reward_mode = reward_mode

        self.A = [np.eye(self.d, dtype=float) for _ in range(self.n_arms)]
        self.A_inv = [np.eye(self.d, dtype=float) for _ in range(self.n_arms)]
        self.b = [np.zeros(self.d, dtype=float) for _ in range(self.n_arms)]
        self.counts = [0] * self.n_arms
        self.values = [0.0] * self.n_arms  # 仅用于日志（平均奖励）

        self.last_miss: float | None = None  # 用于 delta_miss 模式

    def _compute_reward(self, miss_ratio: float) -> float:
        if self.reward_mode == "delta_miss":
            if self.last_miss is None:
                reward = -miss_ratio
            else:
                reward = self.last_miss - miss_ratio
            self.last_miss = miss_ratio
        else:  # 默认 neg_miss
            reward = -miss_ratio
        return reward

    def select_arm(self, x: np.ndarray) -> int:
        """根据上下文 x 选择臂（LinUCB）。"""
        if x.shape[0] != self.d:
            raise ValueError(f"context dim mismatch: expected {self.d}, got {x.shape[0]}")

        best_arm = 0
        best_score = -1e30
        for i in range(self.n_arms):
            A_inv = self.A_inv[i]
            b = self.b[i]

            theta = A_inv @ b  # 估计参数
            mean = float(theta @ x)

            var = float(x @ (A_inv @ x))
            if var < 0:
                var = 0.0
            bonus = self.alpha * math.sqrt(var)
            score = mean + bonus

            if score > best_score:
                best_score = score
                best_arm = i
        return best_arm

    def update(self, arm: int, x: np.ndarray, miss_ratio: float) -> None:
        """用 (x, miss_ratio) 更新指定臂的线性模型。"""
        reward = self._compute_reward(miss_ratio)

        self.counts[arm] += 1

        A = self.A[arm]
        A_inv = self.A_inv[arm]
        b = self.b[arm]

        x_vec = x.reshape(-1, 1)  # (d, 1)

        # A_new = A + x x^T
        # A_inv_new = A_inv - A_inv x x^T A_inv / (1 + x^T A_inv x)
        A_inv_x = A_inv @ x_vec
        denom = float(x_vec.T @ A_inv_x) + 1.0
        if denom <= 0:
            denom = 1e-8
        self.A_inv[arm] = A_inv - (A_inv_x @ A_inv_x.T) / denom
        self.A[arm] = A + (x_vec @ x_vec.T)

        self.b[arm] = b + reward * x

        # 更新平均奖励用于日志
        n = self.counts[arm]
        old_val = self.values[arm]
        self.values[arm] = old_val + (reward - old_val) / float(n)


class ContextualBanditService:
    def __init__(self, arms: List[List[float]], alpha: float, reward_mode: str, shm_key: int):
        self.arms = [_normalize_weights(a) for a in arms]
        self.n_arms = len(self.arms)
        self.alpha = alpha
        self.reward_mode = reward_mode
        self.shm_key = shm_key

        if self.n_arms == 0:
            raise RuntimeError("No arms configured for contextual bandit")

        self.bandit = LinUCBBandit(self.n_arms, CONTEXT_DIM, alpha, reward_mode)

        self.shm = None
        self.shm_file = None
        self.data: SharedMemoryData | None = None

        self._sem_ready = None
        self._sem_ack = None
        self._sem_enabled = False
        self._sem_timeout = float(os.environ.get("LOH_SEM_TIMEOUT_S", "1.0"))

        self._attach_shared_memory()
        self._init_semaphores()

        print(
            f"[loh_contextual_bandit] 启动上下文 Bandit：arms={self.n_arms}, "
            f"alpha={alpha}, mode={reward_mode}, CONTEXT_DIM={CONTEXT_DIM}, STATE_DIM={STATE_DIM}"
        )

    def _attach_shared_memory(self) -> None:
        shm_path = f"/dev/shm/loh_ac_{self.shm_key}"
        expected_size = ctypes.sizeof(SharedMemoryData)

        if not os.path.exists(shm_path):
            with open(shm_path, "wb") as f:
                f.write(b"\x00" * expected_size)

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

        buf = (ctypes.c_char * expected_size).from_buffer(self.shm)
        self.data = SharedMemoryData.from_buffer(buf)
        print(f"[loh_contextual_bandit] 已连接共享内存 {shm_path} (size={expected_size})")

    def _init_semaphores(self) -> None:
        disable_override = os.environ.get("LOH_DISABLE_SEMAPHORE")
        enable_override = os.environ.get("LOH_ENABLE_SEMAPHORE")
        if disable_override is not None:
            sem_requested = not _env_truthy("LOH_DISABLE_SEMAPHORE")
        elif enable_override is not None:
            sem_requested = _env_truthy("LOH_ENABLE_SEMAPHORE")
        else:
            sem_requested = True

        if not sem_requested:
            print("[loh_contextual_bandit] 信号量已禁用，使用轮询模式")
            return

        ready_name = f"/loh_ac_ready_{self.shm_key}".encode()
        ack_name = f"/loh_ac_ack_{self.shm_key}".encode()

        sem_ready = libc.sem_open(ready_name, os.O_CREAT, 0o666, 0)
        if sem_ready == SEM_FAILED:
            err = ctypes.get_errno()
            print(f"[loh_contextual_bandit] sem_open ready 失败: {os.strerror(err)}，退化为轮询")
            return

        sem_ack = libc.sem_open(ack_name, os.O_CREAT, 0o666, 0)
        if sem_ack == SEM_FAILED:
            err = ctypes.get_errno()
            print(f"[loh_contextual_bandit] sem_open ack 失败: {os.strerror(err)}，退化为轮询")
            libc.sem_close(sem_ready)
            return

        self._sem_ready = sem_ready
        self._sem_ack = sem_ack
        self._sem_enabled = True

        self._sem_drain(self._sem_ready)
        self._sem_drain(self._sem_ack)

        print("[loh_contextual_bandit] 信号量模式已启用")

    def _sem_drain(self, sem) -> None:
        if not sem:
            return
        while True:
            r = libc.sem_trywait(sem)
            if r != 0:
                break

    def _wait_ready(self) -> bool:
        if self.data is None:
            return False

        if self._sem_enabled:
            ts = Timespec()
            sec = int(self._sem_timeout)
            nsec = int((self._sem_timeout - sec) * 1e9)
            now = time.time()
            ts.tv_sec = int(now) + sec
            ts.tv_nsec = nsec
            r = libc.sem_timedwait(self._sem_ready, ctypes.byref(ts))
            if r != 0:
                # 超时后退化为轮询
                pass

        poll_sleep_us = int(os.environ.get("LOH_POLL_SLEEP_US", "200"))
        while True:
            if self.data.terminate:
                return False
            if self.data.ready_for_inference:
                return True
            time.sleep(poll_sleep_us / 1e6)

    def _post_ack(self) -> None:
        if self._sem_enabled and self._sem_ack:
            libc.sem_post(self._sem_ack)

    def _read_context(self) -> np.ndarray:
        """从共享内存 state 读取前 CONTEXT_DIM 维作为上下文。"""
        assert self.data is not None
        dim = min(CONTEXT_DIM, STATE_DIM)
        vals = [float(self.data.state[i]) for i in range(dim)]
        if dim < CONTEXT_DIM:
            vals.extend([0.0] * (CONTEXT_DIM - dim))
        return np.array(vals, dtype=float)

    def run(self) -> None:
        if self.data is None:
            print("[loh_contextual_bandit] 未正确连接共享内存，退出")
            return

        step = 0
        start = get_monotonic_time()
        try:
            while True:
                if not self._wait_ready():
                    print("[loh_contextual_bandit] 收到 terminate 或等待失败，退出")
                    break

                # 读取上下文
                x = self._read_context()

                # 选臂并写入对应权重
                arm = self.bandit.select_arm(x)
                weights = self.arms[arm]
                for i in range(FEATURE_DIM):
                    self.data.weights[i] = float(weights[i])
                self.data.weights_updated = 1
                self.data.ready_for_inference = 0
                self.data.is_training = 0
                self.data.ack_version = self.data.state_version

                # 读当前 miss_ratio 计算奖励并更新 bandit
                miss_ratio = float(self.data.miss_ratio)
                self.bandit.update(arm, x, miss_ratio)

                step += 1
                if step % 1000 == 0:
                    elapsed = get_monotonic_time() - start
                    print(f"[loh_contextual_bandit] step={step}, elapsed={elapsed:.1f}s")
                    for i, (c, v) in enumerate(zip(self.bandit.counts, self.bandit.values)):
                        print(f"  arm[{i}]: count={c}, avg_reward={v:.6f}")

                self._post_ack()

        finally:
            if self._sem_ready:
                libc.sem_close(self._sem_ready)
            if self._sem_ack:
                libc.sem_close(self._sem_ack)
            if self.shm is not None:
                self.shm.close()
            if self.shm_file is not None:
                self.shm_file.close()


def _default_arms() -> List[List[float]]:
    """给一组覆盖性比较好的默认权重模式。"""
    return [
        [1.0, 0.0, 0.0, 0.0, 0.0, 0.0],  # 纯 recency
        [0.0, 1.0, 0.0, 0.0, 0.0, 0.0],  # 纯 frequency
        [0.0, 0.0, 1.0, 0.0, 0.0, 0.0],  # 纯 size
        [0.4, 0.4, 0.2, 0.0, 0.0, 0.0],  # recency+freq+size
        [0.3, 0.3, 0.2, 0.1, 0.1, 0.0],  # 加入短 IRT
        [0.2, 0.2, 0.2, 0.2, 0.1, 0.1],  # 较均衡
        [1/6, 1/6, 1/6, 1/6, 1/6, 1/6],  # 完全均匀
    ]


def main() -> None:
    shm_key_str = os.environ.get("LOH_SHM_KEY", "9876")
    try:
        shm_key = int(shm_key_str)
    except Exception:
        shm_key = 9876

    alpha = _env_float("LOH_CTX_BANDIT_ALPHA", 1.0)
    reward_mode = os.environ.get("LOH_BANDIT_REWARD_MODE", "neg_miss").strip().lower()

    arms = _parse_arms_from_env()
    if not arms:
        arms = _default_arms()

    print(
        f"[loh_contextual_bandit] STATE_DIM={STATE_DIM}, CONTEXT_DIM={CONTEXT_DIM}, "
        f"arms={len(arms)}, alpha={alpha}, mode={reward_mode}, SHM_KEY={shm_key}"
    )

    service = ContextualBanditService(arms, alpha, reward_mode, shm_key)
    service.run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("[loh_contextual_bandit] KeyboardInterrupt, exiting", file=sys.stderr)
