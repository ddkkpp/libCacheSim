#!/usr/bin/env python3

"""
LOH模型推理脚本 - 仅用于推理，不进行训练
使用训练好的PPO模型为LOH缓存算法提供实时权重
"""

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
import argparse

from stable_baselines3 import PPO
import torch

# 常数定义
FEATURE_DIM = 6
def _env_truthy(name: str) -> bool:
    v = os.environ.get(name)
    if v is None:
        return False
    return v.strip().lower() in {"1", "true", "yes", "on"}

def get_state_dim() -> int:
    """基础维度 (26/38) + 可选候选特征附加 72 维，完全由 LOH_INCLUDE_* 决定。"""
    base = 38
    cache_flag = os.environ.get("LOH_INCLUDE_CACHE_FEATURES", "").strip().lower()
    if cache_flag in {"0", "false", "no", "off"}:
        base = 26
    cand_flag = os.environ.get("LOH_INCLUDE_CANDIDATE_FEATURES", "0").strip().lower()
    cand_enabled = cand_flag in {"1", "true", "yes", "on"}
    return base + (72 if cand_enabled else 0)

CONTEXT_DIM = get_state_dim()
STATE_DIM = CONTEXT_DIM
SHM_KEY = 9876

# 调试级别控制
LOH_DEBUG_LEVEL = 2

def LOH_DEBUG_BASIC():
    return LOH_DEBUG_LEVEL >= 1

def LOH_DEBUG_VERBOSE():
    return LOH_DEBUG_LEVEL >= 2

# POSIX 信号量绑定
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
    """获取单调时钟时间，与C端CLOCK_MONOTONIC一致"""
    return time.clock_gettime(time.CLOCK_MONOTONIC)

def _env_flag(name: str, default: bool) -> bool:
    """读取布尔型环境变量"""
    raw = os.environ.get(name)
    if raw is None:
        return default
    lowered = raw.strip().lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    return default

# 共享内存结构定义
def create_shared_memory_class(context_dim):
    """动态创建共享内存数据结构类"""
    class SharedMemoryData(ctypes.Structure):
        _fields_ = [
            ("ready_for_inference", ctypes.c_int),
            ("weights_updated", ctypes.c_int),
            ("terminate", ctypes.c_int),
            ("is_training", ctypes.c_int),              # 添加缺失的字段！
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

if _env_truthy("LOH_PRINT_SHM_LAYOUT"):
    try:
        sz = ctypes.sizeof(SharedMemoryData)
        print(f"[SHM] Python SharedMemoryData sizeof={sz} bytes (STATE_DIM={STATE_DIM})")
        for name, _ in SharedMemoryData._fields_:
            try:
                off = getattr(SharedMemoryData, name).offset
                print(f"[SHM] field {name:>20s} @ offset {off}")
            except Exception:
                pass
    except Exception:
        pass

class LOHInferenceService:
    """LOH推理服务 - 仅用于推理，不进行训练"""

    def __init__(self, model_path, shm_key=SHM_KEY):
        self.shm_key = shm_key
        self.model_path = model_path
        self.shm = None
        self.shm_file = None

        # 初始化共享内存
        self._attach_shared_memory()

        # 初始化信号量
        self._sem_ready = None
        self._sem_ack = None
        self._sem_enabled = False
        self._sem_timeout = float(os.environ.get("LOH_SEM_TIMEOUT_S", "1.0"))
        self._sem_disabled_logged = False
        self._last_sem_timeout_log = 0.0
        self._disable_fsync = _env_flag("LOH_DISABLE_FSYNC", False)

        # 决定是否使用信号量
        disable_override = os.environ.get("LOH_DISABLE_SEMAPHORE")
        enable_override = os.environ.get("LOH_ENABLE_SEMAPHORE")
        if disable_override is not None:
            self._sem_requested = not _env_flag("LOH_DISABLE_SEMAPHORE", False)
        elif enable_override is not None:
            self._sem_requested = _env_flag("LOH_ENABLE_SEMAPHORE", True)
        else:
            self._sem_requested = True

        self._init_semaphores()

        # 轮询参数
        self._poll_sleep_us = int(os.environ.get("LOH_POLL_SLEEP_US", "200"))
        self._poll_fallback_count = 0

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

        # 加载训练好的模型
        self._load_model()

        # 统计信息
        self.inference_count = 0
        self.start_time = get_monotonic_time()

        print(f"✅ LOH推理服务初始化完成")
        print(f"   模型路径: {model_path}")
        print(f"   共享内存键: {shm_key}")
        print(f"   信号量模式: {'启用' if self._sem_enabled else '禁用'}")

    def _attach_shared_memory(self):
        """连接到共享内存"""
        try:
            shm_path = f"/dev/shm/loh_ac_{self.shm_key}"
            expected_size = ctypes.sizeof(SharedMemoryData)

            if not os.path.exists(shm_path):
                with open(shm_path, 'wb') as f:
                    f.write(b'\x00' * expected_size)

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
            os.chmod(shm_path, 0o666)
            print(f"✅ 共享内存连接成功: {shm_path}")

        except Exception as e:
            print(f"❌ 共享内存连接失败: {e}")
            raise

    def _init_semaphores(self):
        """初始化信号量"""
        self._disable_semaphores()

        if not getattr(self, "_sem_requested", True):
            if LOH_DEBUG_BASIC():
                print("[SEM] 信号量模式已禁用，使用轮询模式")
            return

        ready_name = f"/loh_ac_ready_{self.shm_key}".encode()
        ack_name = f"/loh_ac_ack_{self.shm_key}".encode()

        sem_ready = libc.sem_open(ready_name, os.O_CREAT, 0o666, 0)
        if sem_ready == SEM_FAILED:
            err = ctypes.get_errno()
            if LOH_DEBUG_BASIC():
                print(f"[SEM] sem_open ready 失败: {os.strerror(err)}")
            return

        sem_ack = libc.sem_open(ack_name, os.O_CREAT, 0o666, 0)
        if sem_ack == SEM_FAILED:
            err = ctypes.get_errno()
            if LOH_DEBUG_BASIC():
                print(f"[SEM] sem_open ack 失败: {os.strerror(err)}")
            libc.sem_close(sem_ready)
            return

        self._sem_ready = sem_ready
        self._sem_ack = sem_ack
        self._sem_enabled = True

        # 清理残留信号
        self._sem_drain(self._sem_ready)
        self._sem_drain(self._sem_ack)

        if LOH_DEBUG_BASIC():
            print("[SEM] POSIX 信号量已启用")

    def _disable_semaphores(self, reason: Optional[str] = None):
        """禁用信号量"""
        if reason and LOH_DEBUG_BASIC():
            print(f"[SEM] 禁用信号量: {reason}")

        if self._sem_ready is not None:
            libc.sem_close(self._sem_ready)
            self._sem_ready = None
        if self._sem_ack is not None:
            libc.sem_close(self._sem_ack)
            self._sem_ack = None

        self._sem_enabled = False
        self._sem_disabled_logged = True

    def _sem_drain(self, sem_handle):
        """清空信号量"""
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
        """等待信号量"""
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
                if LOH_DEBUG_VERBOSE():
                    suffix = f" {label}" if label else ""
                    print(f"[SEM][Python] sem_wait 成功{suffix}")
                return True

            err = ctypes.get_errno()
            if err == errno.EINTR:
                continue
            if timeout_s is not None and err == errno.ETIMEDOUT:
                now = get_monotonic_time()
                if LOH_DEBUG_BASIC() and (now - self._last_sem_timeout_log) > 0.5:
                    suffix = f" {label}" if label else ""
                    print(f"[SEM][Python] sem_wait 超时{suffix}，切换到轮询")
                    self._last_sem_timeout_log = now
                return False

            self._disable_semaphores(f"sem_wait error: {os.strerror(err)}")
            return False

    def _sem_post(self, sem_handle, label: Optional[str] = None):
        """发送信号量"""
        if not self._sem_enabled or sem_handle is None:
            return

        res = libc.sem_post(sem_handle)
        if res != 0:
            err = ctypes.get_errno()
            self._disable_semaphores(f"sem_post error: {os.strerror(err)}")
        elif LOH_DEBUG_VERBOSE() and label:
            print(f"[SEM][Python] sem_post {label}")

    def _read_shm(self):
        """读取共享内存"""
        try:
            self.shm.seek(0)
            raw_data = self.shm.read(ctypes.sizeof(SharedMemoryData))
            data = SharedMemoryData.from_buffer_copy(raw_data)
            return data
        except Exception as e:
            if LOH_DEBUG_BASIC():
                print(f"❌ 读取共享内存失败: {e}")
            return None

    def _write_shm(self, data_struct):
        """写入共享内存"""
        try:
            raw_data = ctypes.string_at(ctypes.byref(data_struct), ctypes.sizeof(data_struct))
            self.shm.seek(0)
            self.shm.write(raw_data)
            self.shm.flush()
            if self.shm_file is not None and not getattr(self, "_disable_fsync", False):
                os.fsync(self.shm_file.fileno())
            return True
        except Exception as e:
            if LOH_DEBUG_BASIC():
                print(f"❌ 写入共享内存失败: {e}")
            return False

    def _write_field_int32(self, offset, value):
        """写入单个int32字段"""
        try:
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
        """更新is_training标志"""
        value = 1 if value else 0
        if self._write_field_int32(self._offset_is_training, value):
            return
        data = self._read_shm()
        if not data:
            return
        data.is_training = value
        self._write_shm(data)

    def _set_inference_mode(self):
        """设置推理模式：is_training=0"""
        data = self._read_shm()
        if not data:
            print("❌ 无法读取共享内存来设置推理模式")
            return

        # 设置推理模式标志
        data.is_training = 0       # 不在训练状态
        data.terminate = 0         # 不终止

        success = self._write_shm(data)
        if success:
            print("✅ 已设置推理模式 (is_training=0)")
        else:
            print("❌ 设置推理模式失败")

    def _load_model(self):
        """加载训练好的PPO模型"""
        try:
            if not os.path.exists(self.model_path):
                raise FileNotFoundError(f"模型文件不存在: {self.model_path}")

            # 创建虚拟环境用于模型加载
            dummy_env = gym.spaces.Box(
                low=-np.inf, high=np.inf, shape=(STATE_DIM,), dtype=np.float32
            )

            # 加载模型
            self.model = PPO.load(self.model_path)

            print(f"✅ 模型加载成功: {self.model_path}")

            # 打印模型信息
            if LOH_DEBUG_BASIC():
                print(f"   策略网络: {type(self.model.policy).__name__}")
                print(f"   状态维度: {STATE_DIM}")
                print(f"   动作维度: {FEATURE_DIM}")

        except Exception as e:
            print(f"❌ 模型加载失败: {e}")
            raise

    def predict_weights(self, state):
        """使用模型预测权重"""
        try:
            # 确保输入格式正确
            state_array = np.array(state, dtype=np.float32)
            if state_array.shape != (STATE_DIM,):
                raise ValueError(f"状态维度错误: 期望 {STATE_DIM}, 实际 {state_array.shape}")

            # 使用模型预测动作
            action, _ = self.model.predict(state_array, deterministic=True)

            # 将动作转换为权重（softmax归一化）
            action_tensor = torch.from_numpy(action)
            weights = torch.nn.functional.softmax(action_tensor, dim=-1).numpy()

            return weights.astype(np.float64)

        except Exception as e:
            print(f"❌ 权重预测失败: {e}")
            # 返回均匀分布权重作为回退
            return np.ones(FEATURE_DIM, dtype=np.float64) / FEATURE_DIM

    def run_inference_loop(self):
        """运行推理循环"""
        print("🚀 开始推理服务...")

        # 确保设置为推理模式
        self._set_inference_mode()

        last_heartbeat = get_monotonic_time()
        heartbeat_interval = 10.0  # 每10秒输出一次心跳信息

        try:
            while True:
                # 检查终止信号
                data = self._read_shm()
                if data and data.terminate == 1:
                    print("收到终止信号，退出推理服务")
                    break

                # 等待C端发送推理请求
                request_found = False

                # 使用信号量或轮询等待请求
                if self._sem_enabled:
                    waited_via_sem = self._sem_wait(self._sem_ready, self._sem_timeout, label="inference_ready")
                    if waited_via_sem:
                        data = self._read_shm()
                        if data and data.ready_for_inference == 1:
                            request_found = True
                elif LOH_DEBUG_BASIC() and not self._sem_disabled_logged:
                    print("[SEM] 信号量未启用，使用轮询模式")
                    self._sem_disabled_logged = True

                if not request_found:
                    # 轮询检查
                    data = self._read_shm()
                    if data and data.ready_for_inference == 1:
                        request_found = True
                    else:
                        time.sleep(self._poll_sleep_us / 1e6)

                        # 心跳信息
                        now = get_monotonic_time()
                        if now - last_heartbeat > heartbeat_interval:
                            elapsed = now - self.start_time
                            print(f"[心跳] 推理服务运行中... 已运行 {elapsed:.1f}s, 完成推理 {self.inference_count} 次")
                            last_heartbeat = now
                        continue

                if not request_found or not data:
                    continue

                # 处理推理请求
                try:
                    inference_start = get_monotonic_time()

                    # 获取状态
                    state = np.array(data.state, dtype=np.float32)
                    seq_no = int(data.state_version)

                    # 预测权重
                    weights = self.predict_weights(state)

                    # 写入权重
                    for i in range(FEATURE_DIM):
                        data.weights[i] = float(weights[i])

                    data.ack_version = seq_no
                    data.weights_updated = 1
                    data.ready_for_inference = 0
                    data.is_training = 0  # 推理模式下始终为0

                    self._write_shm(data)

                    # 发送ACK信号
                    self._sem_post(self._sem_ack, label=f"inference_ack seq {seq_no}")

                    inference_end = get_monotonic_time()
                    inference_time = inference_end - inference_start

                    self.inference_count += 1

                    if LOH_DEBUG_VERBOSE():
                        weights_str = ", ".join([f"{w:.3f}" for w in weights])
                        print(f"[推理] [seq {seq_no}] 权重: [{weights_str}] (耗时 {inference_time:.6f}s)")

                        # 输出状态向量信息
                        if CONTEXT_DIM == 26:
                            print(f"[global_features]: [{state[0]:.6f}, {state[1]:.6f}]")
                            request_features = ", ".join([f"{state[i]:.6f}" for i in range(2, 26)])
                            print(f"[request_features]: [{request_features}]")
                    elif LOH_DEBUG_BASIC() and self.inference_count % 100 == 0:
                        print(f"[推理] 已完成 {self.inference_count} 次推理，平均响应时间 {inference_time:.6f}s")

                except Exception as e:
                    print(f"❌ 推理处理失败: {e}")
                    continue

        except KeyboardInterrupt:
            print("收到中断信号，退出推理服务")
        except Exception as e:
            print(f"❌ 推理服务异常: {e}")
        finally:
            self.cleanup()

    def cleanup(self):
        """清理资源"""
        print("清理推理服务资源...")

        # 设置is_training=0
        self._update_is_training(0)

        # 关闭共享内存
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

        # 关闭信号量
        self._disable_semaphores("服务关闭")

        # 输出统计信息
        total_time = get_monotonic_time() - self.start_time
        if self.inference_count > 0:
            avg_time = total_time / self.inference_count
            print(f"✅ 推理服务统计:")
            print(f"   总运行时间: {total_time:.2f}s")
            print(f"   总推理次数: {self.inference_count}")
            print(f"   平均推理时间: {avg_time:.6f}s")

        print("✅ 资源清理完成")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="LOH模型推理服务")
    parser.add_argument("model_path", help="训练好的PPO模型路径 (.zip文件)")
    parser.add_argument("--shm-key", type=int, default=SHM_KEY,
                       help=f"共享内存键 (默认: {SHM_KEY})")
    parser.add_argument("--debug-level", type=int, default=2, choices=[0, 1, 2],
                       help="调试级别: 0=无输出, 1=基本信息, 2=详细信息 (默认: 2)")

    args = parser.parse_args()

    # 设置调试级别
    global LOH_DEBUG_LEVEL
    LOH_DEBUG_LEVEL = args.debug_level

    # 检查模型文件
    if not os.path.exists(args.model_path):
        print(f"❌ 模型文件不存在: {args.model_path}")
        sys.exit(1)

    print(f"🤖 LOH推理服务启动")
    print(f"   模型路径: {args.model_path}")
    print(f"   共享内存键: {args.shm_key}")
    print(f"   调试级别: {args.debug_level}")
    print(f"   启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 创建并运行推理服务
    try:
        service = LOHInferenceService(args.model_path, args.shm_key)
        service.run_inference_loop()
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断推理服务")
    except Exception as e:
        print(f"❌ 推理服务失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
