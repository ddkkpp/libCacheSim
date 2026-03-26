#!/usr/bin/env python3
"""
LOH Bandit 权重搜索脚本（epsilon-greedy 版本）：
- 不使用深度 RL 模型，仅使用多臂 bandit 在一组候选权重之间在线选择；
- 仍然通过共享内存 + POSIX 信号量与 C 端同步，保证 enable_rl 路径被使用；
- 奖励定义为 r = - miss_ratio（越小越好），按窗口持续更新各臂的平均奖励；
- 算法使用 epsilon-greedy，多数情况下可视为 baseline 版本；

用法示例：

  # 使用默认候选权重集合 + epsilon-greedy
  PYTHON_SCRIPT=loh_bandit_weights.py \
    bash ./scripts/test_loh_rl_sb3.sh data/WikiCDN/wiki_2019t.oracleGeneral.zst 26 0.075

环境变量：
    LOH_BANDIT_EPSILON       epsilon-greedy 的探索概率，默认 0.1
  LOH_BANDIT_ARMS          自定义权重臂集合，格式：
                           "w11,w12,w13,w14,w15,w16;w21,w22,...;..."，每个臂 6 个数
  LOH_BANDIT_REWARD_MODE   奖励模式："neg_miss"（默认）或 "delta_miss"，后者用 miss_ratio 的差分
"""

import os
import sys
import time

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from loh_actor_critic_sb3 import SharedMemoryData, CONTEXT_DIM, STATE_DIM, SHM_WEIGHT_DIM, SCORE_FEATURE_DIM

# Map FEATURE_DIM to SHM_WEIGHT_DIM for compatibility with weights array
FEATURE_DIM = SHM_WEIGHT_DIM
# Effective arm dimension follows actor_critic score feature dimension.
ARM_DIM = SCORE_FEATURE_DIM
import ctypes
import mmap
import math
from typing import List, Tuple




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
    # Keep arm dimensionality aligned with shared-memory weight vector.
    if len(ws) < ARM_DIM:
        ws = ws + [0.0] * (ARM_DIM - len(ws))
    elif len(ws) > ARM_DIM:
        ws = ws[:ARM_DIM]

    s = sum(ws)
    if s <= 0 or not math.isfinite(s):
        return [1.0 / ARM_DIM] * ARM_DIM
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
            if len(vals) == ARM_DIM:
                arms.append(_normalize_weights(vals))
        except Exception:
            continue
    return arms


def _to_shm_weights(weights_eff: List[float]) -> List[float]:
    """Map SCORE_FEATURE_DIM effective weights to SHM_WEIGHT_DIM like actor_critic."""
    ws = list(weights_eff)
    if len(ws) > SCORE_FEATURE_DIM:
        ws = ws[:SCORE_FEATURE_DIM]
    elif len(ws) < SCORE_FEATURE_DIM:
        ws = ws + [0.0] * (SCORE_FEATURE_DIM - len(ws))

    out = [0.0] * FEATURE_DIM
    use_compound = _env_truthy("LOH_SCORE_USE_COMPOUND")
    use_irt = _env_truthy("LOH_SCORE_USE_IRT")

    if use_compound:
        n = min(SCORE_FEATURE_DIM, FEATURE_DIM)
    elif not use_irt:
        n = min(SCORE_FEATURE_DIM, 3)
    else:
        n = min(SCORE_FEATURE_DIM, 6)

    for i in range(n):
        out[i] = float(ws[i])
    return out









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


class EpsilonGreedyBandit:
    def __init__(self, arms: List[List[float]], epsilon: float, reward_mode: str = "neg_miss"):
        self.arms = arms
        self.epsilon = epsilon
        self.n = len(arms)
        self.counts = [0] * self.n
        self.values = [0.0] * self.n
        self.reward_mode = reward_mode
        self.last_miss = None  # 用于 delta_miss 模式

    def select_arm(self) -> int:
        import random
        if self.n == 0:
            raise RuntimeError("No arms configured for bandit")
        if random.random() < self.epsilon:
            return random.randrange(self.n)
        # exploit: 选当前估计值最大的臂
        best = 0
        best_val = self.values[0]
        for i in range(1, self.n):
            if self.values[i] > best_val:
                best = i
                best_val = self.values[i]
        return best

    def update(self, arm: int, miss_ratio: float):
        # 奖励定义
        if self.reward_mode == "delta_miss":
            if self.last_miss is None:
                reward = -miss_ratio
            else:
                reward = self.last_miss - miss_ratio
            self.last_miss = miss_ratio
        else:  # 默认 neg_miss
            reward = -miss_ratio

        self.counts[arm] += 1
        n = self.counts[arm]
        value = self.values[arm]
        # 在线更新均值
        self.values[arm] = value + (reward - value) / float(n)


class BanditService:
    def __init__(self, arms: List[List[float]], epsilon: float, reward_mode: str, shm_key: int):
        self.arms = [_normalize_weights(a) for a in arms]
        self.bandit = EpsilonGreedyBandit(self.arms, epsilon, reward_mode)
        self.shm_key = shm_key
        self.shm = None
        self.shm_file = None
        self.data = None

        self._sem_ready = None
        self._sem_ack = None
        self._sem_enabled = False
        self._sem_timeout = float(os.environ.get("LOH_SEM_TIMEOUT_S", "0.02"))

        self._attach_shared_memory()
        self._init_semaphores()

        print(f"[loh_bandit_weights] 启动 Bandit 策略，arms={len(self.arms)}, epsilon={epsilon}, mode={reward_mode}")

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
        print(f"[loh_bandit_weights] 已连接共享内存 {shm_path} (size={expected_size})")

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
            print("[loh_bandit_weights] 信号量已禁用，使用轮询模式")
            return

        ready_name = f"/loh_ac_ready_{self.shm_key}".encode()
        ack_name = f"/loh_ac_ack_{self.shm_key}".encode()

        sem_ready = libc.sem_open(ready_name, os.O_CREAT, 0o666, 0)
        if sem_ready == SEM_FAILED:
            err = ctypes.get_errno()
            print(f"[loh_bandit_weights] sem_open ready 失败: {os.strerror(err)}，退化为轮询")
            return

        sem_ack = libc.sem_open(ack_name, os.O_CREAT, 0o666, 0)
        if sem_ack == SEM_FAILED:
            err = ctypes.get_errno()
            print(f"[loh_bandit_weights] sem_open ack 失败: {os.strerror(err)}，退化为轮询")
            libc.sem_close(sem_ready)
            return

        self._sem_ready = sem_ready
        self._sem_ack = sem_ack
        self._sem_enabled = True

        self._sem_drain(self._sem_ready)
        self._sem_drain(self._sem_ack)

        print("[loh_bandit_weights] 信号量模式已启用")

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

        if self.data.terminate:
            return False
        if self.data.ready_for_inference:
            return True

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
                    print("[loh_bandit_weights] 收到 terminate 或等待失败，退出")
                    break

                # 选臂并写入对应权重
                arm = self.bandit.select_arm()
                weights_eff = self.arms[arm]
                weights = _to_shm_weights(weights_eff)
                for i in range(FEATURE_DIM):
                    self.data.weights[i] = float(weights[i])
                self.data.weights_updated = 1
                self.data.ready_for_inference = 0
                self.data.is_training = 0
                self.data.ack_version = self.data.state_version

                # 读当前 miss_ratio 计算奖励
                obj_hit = max(0.0, min(1.0, float(self.data.state[0])))
                byte_hit = max(0.0, min(1.0, float(self.data.state[1])))
                miss_w = max(0.0, min(1.0, _env_float("LOH_MISS_RATIO_WEIGHT", 1.0)))
                byte_miss_w = 1.0 - miss_w
                miss_mix = miss_w * (1.0 - obj_hit) + byte_miss_w * (1.0 - byte_hit)
                self.bandit.update(arm, miss_mix)

                step += 1
                if step % 1000 == 0:
                    elapsed = get_monotonic_time() - start
                    print(f"[loh_bandit_weights] step={step}, elapsed={elapsed:.1f}s")
                    for i, (c, v) in enumerate(zip(self.bandit.counts, self.bandit.values)):
                        print(f"  arm[{i}]: count={c}, avg_reward={v:.9e}")

                self._post_ack()

        finally:
            # Release exported pointer created by ctypes.from_buffer before closing mmap.
            self.data = None
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

    epsilon = _env_float("LOH_BANDIT_EPSILON", 0.1)
    reward_mode = os.environ.get("LOH_BANDIT_REWARD_MODE", "neg_miss").strip().lower()

    arms = _parse_arms_from_env()
    if not arms:
        arms = _default_arms()

    print(f"[LOH CONFIG] Shared state dims: CONTEXT_DIM=26, STATE_DIM={STATE_DIM}\n"); print(f"[loh_bandit_weights] STATE_DIM={STATE_DIM}, arms={len(arms)}, epsilon={epsilon}, mode={reward_mode}, SHM_KEY={shm_key}")

    service = BanditService(arms, epsilon, reward_mode, shm_key)
    service.run()


if __name__ == "__main__":
    main()
