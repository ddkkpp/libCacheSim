#!/usr/bin/env python3
"""
LOH Bandit 权重搜索脚本（UCB 版本）：
- 不使用深度 RL 模型，仅使用多臂 bandit 在一组候选权重之间在线选择；
- 与 `loh_bandit_weights.py` 的接口兼容，但使用 UCB 而不是 epsilon-greedy；
- 仍然通过共享内存 + POSIX 信号量与 C 端同步，保证 enable_rl 路径被使用；
- 奖励定义为 r = - miss_ratio（越小越好），也支持 delta_miss 模式。

用法示例：

  # 使用默认候选权重集合 + UCB bandit
  PYTHON_SCRIPT=loh_bandit_ucb.py \
    bash ./scripts/test_loh_rl_sb3.sh data/WikiCDN/wiki_2019t.oracleGeneral.zst 26 0.075

环境变量：
  LOH_BANDIT_UCB_C        UCB 探索系数 c，默认 1.0（越大越偏向探索）
  LOH_BANDIT_ARMS         自定义权重臂集合，格式：
                          "w11,w12,w13,w14,w15,w16;w21,w22,...;..."，每个臂 6 个数
  LOH_BANDIT_REWARD_MODE  奖励模式："neg_miss"（默认）或 "delta_miss"，后者用 miss_ratio 的差分
"""

import os
import sys
import time
import ctypes
import mmap
import math
from typing import List

FEATURE_DIM = 6


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
    """推断 C 端 state 数组长度：基础 26/38 + 可选候选 72，完全由 LOH_INCLUDE_* 决定。"""
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


class UCBBandit:
    """标准非上下文 UCB 多臂 bandit。

    对第 i 个臂维护 (count[i], value[i])，在时间步 t 选择：
        UCB_i = value[i] + c * sqrt(2 * ln t / count[i])
    未被尝试过的臂会优先选一次。
    """

    def __init__(self, n_arms: int, c: float, reward_mode: str = "neg_miss"):
        self.n = n_arms
        self.c = c
        self.reward_mode = reward_mode
        self.counts = [0] * self.n
        self.values = [0.0] * self.n
        self.total_steps = 0
        self.last_miss = None  # 用于 delta_miss 模式

    def _compute_reward(self, miss_ratio: float) -> float:
        if self.reward_mode == "delta_miss":
            if self.last_miss is None:
                reward = -miss_ratio
            else:
                reward = self.last_miss - miss_ratio
            self.last_miss = miss_ratio
        else:
            reward = -miss_ratio
        return reward

    def select_arm(self) -> int:
        if self.n == 0:
            raise RuntimeError("No arms configured for bandit")

        # 先保证每个臂至少被试一次
        for i in range(self.n):
            if self.counts[i] == 0:
                return i

        self.total_steps += 1
        t = self.total_steps
        best = 0
        best_ucb = -1e30
        for i in range(self.n):
            mean = self.values[i]
            ci = self.c * math.sqrt(2.0 * math.log(max(1.0, t)) / float(self.counts[i]))
            ucb = mean + ci
            if ucb > best_ucb:
                best_ucb = ucb
                best = i
        return best

    def update(self, arm: int, miss_ratio: float) -> None:
        reward = self._compute_reward(miss_ratio)
        self.counts[arm] += 1
        n = self.counts[arm]
        old = self.values[arm]
        self.values[arm] = old + (reward - old) / float(n)


class BanditService:
    def __init__(self, arms: List[List[float]], c: float, reward_mode: str, shm_key: int):
        self.arms = [_normalize_weights(a) for a in arms]
        self.bandit = UCBBandit(len(self.arms), c, reward_mode)
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

        print(
            f"[loh_bandit_ucb] 启动 UCB Bandit 策略，arms={len(self.arms)}, "
            f"c={c}, mode={reward_mode}"
        )

    def _attach_shared_memory(self):
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
        print(f"[loh_bandit_ucb] 已连接共享内存 {shm_path} (size={expected_size})")

    def _init_semaphores(self):
        disable_override = os.environ.get("LOH_DISABLE_SEMAPHORE")
        enable_override = os.environ.get("LOH_ENABLE_SEMAPHORE")
        if disable_override is not None:
            sem_requested = not _env_truthy("LOH_DISABLE_SEMAPHORE")
        elif enable_override is not None:
            sem_requested = _env_truthy("LOH_ENABLE_SEMAPHORE")
        else:
            sem_requested = True

        if not sem_requested:
            print("[loh_bandit_ucb] 信号量已禁用，使用轮询模式")
            return

        ready_name = f"/loh_ac_ready_{self.shm_key}".encode()
        ack_name = f"/loh_ac_ack_{self.shm_key}".encode()

        sem_ready = libc.sem_open(ready_name, os.O_CREAT, 0o666, 0)
        if sem_ready == SEM_FAILED:
            err = ctypes.get_errno()
            print(f"[loh_bandit_ucb] sem_open ready 失败: {os.strerror(err)}，退化为轮询")
            return

        sem_ack = libc.sem_open(ack_name, os.O_CREAT, 0o666, 0)
        if sem_ack == SEM_FAILED:
            err = ctypes.get_errno()
            print(f"[loh_bandit_ucb] sem_open ack 失败: {os.strerror(err)}，退化为轮询")
            libc.sem_close(sem_ready)
            return

        self._sem_ready = sem_ready
        self._sem_ack = sem_ack
        self._sem_enabled = True

        self._sem_drain(self._sem_ready)
        self._sem_drain(self._sem_ack)

        print("[loh_bandit_ucb] 信号量模式已启用")

    def _sem_drain(self, sem):
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
                pass

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
                    print("[loh_bandit_ucb] 收到 terminate 或等待失败，退出")
                    break

                # 选臂并写入对应权重
                arm = self.bandit.select_arm()
                weights = self.arms[arm]
                for i in range(FEATURE_DIM):
                    self.data.weights[i] = float(weights[i])
                self.data.weights_updated = 1
                self.data.ready_for_inference = 0
                self.data.is_training = 0
                self.data.ack_version = self.data.state_version

                # 读当前 miss_ratio 计算奖励
                miss_ratio = float(self.data.miss_ratio)
                self.bandit.update(arm, miss_ratio)

                step += 1
                if step % 1000 == 0:
                    elapsed = get_monotonic_time() - start
                    print(f"[loh_bandit_ucb] step={step}, elapsed={elapsed:.1f}s")
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


def main():
    shm_key_str = os.environ.get("LOH_SHM_KEY", "9876")
    try:
        shm_key = int(shm_key_str)
    except Exception:
        shm_key = 9876

    c = _env_float("LOH_BANDIT_UCB_C", 1.0)
    reward_mode = os.environ.get("LOH_BANDIT_REWARD_MODE", "neg_miss").strip().lower()

    arms = _parse_arms_from_env()
    if not arms:
        arms = _default_arms()

    print(
        f"[loh_bandit_ucb] STATE_DIM={STATE_DIM}, arms={len(arms)}, "
        f"c={c}, mode={reward_mode}, SHM_KEY={shm_key}"
    )

    service = BanditService(arms, c, reward_mode, shm_key)
    service.run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("[loh_bandit_ucb] KeyboardInterrupt, exiting", file=sys.stderr)
