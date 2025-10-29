#!/usr/bin/env python3
"""
LOH Actor-Critic Simple Test - 仅测试共享内存功能
不使用stable-baselines3，先验证基本的共享内存通信
"""

import numpy as np
import ctypes
import mmap
import os
import sys
import time
from datetime import datetime

# --- 常量和共享内存结构定义 ---
SHM_KEY = 9876
FEATURE_DIM = 6

# 获取状态向量维度
def get_state_dim():
    """获取状态向量维度，默认为26维"""
    state_dim = os.environ.get('LOH_STATE_DIM', '26')
    return int(state_dim)

CONTEXT_DIM = get_state_dim()
STATE_DIM = CONTEXT_DIM

print(f"LOH RL Agent: Using {STATE_DIM}-dimensional state vector")

# 动态创建共享内存结构
def create_shared_memory_class(state_dim):
    """动态创建与 C 端 shm_data_t 结构匹配的类"""
    class SharedMemoryData(ctypes.Structure):
        _fields_ = [
            # 控制标志位
            ('ready_for_inference', ctypes.c_int),
            ('weights_updated', ctypes.c_int),
            ('terminate', ctypes.c_int),
            # 动态维度状态向量
            ('state', ctypes.c_double * state_dim),
            # 6维权重向量
            ('weights', ctypes.c_double * FEATURE_DIM),
            # 性能指标
            ('miss_ratio', ctypes.c_double),
            ('byte_miss_ratio', ctypes.c_double),
            ('reward', ctypes.c_double),
            ('timestamp', ctypes.c_int64),
        ]
    return SharedMemoryData

SharedMemoryData = create_shared_memory_class(CONTEXT_DIM)

class SimpleLohEnv:
    """简单的LOH环境，仅测试共享内存通信"""

    def __init__(self, shm_key=SHM_KEY):
        print("🚀 初始化简单LOH测试环境...")
        self.shm_key = shm_key
        self.shm = None
        self.shm_file = None
        self.shm_mmap = None
        self.step_count = 0
        self._attach_shared_memory()
        print("✅ 环境初始化完成")

    def _attach_shared_memory(self):
        """连接到共享内存文件，如不存在则主动创建并初始化"""
        try:
            shm_path = f"/dev/shm/loh_ac_{self.shm_key}"
            size = ctypes.sizeof(SharedMemoryData)

            if not os.path.exists(shm_path):
                print(f"🔨 共享内存文件不存在，Python端主动创建: {shm_path}")
                # 创建并初始化为全零
                with open(shm_path, 'wb') as f:
                    f.write(b'\x00' * size)
            else:
                print(f"⏳ 共享内存文件已存在: {shm_path}")

            self.shm_file = open(shm_path, 'r+b')
            self.shm_mmap = mmap.mmap(self.shm_file.fileno(), size)
            self.shm = self.shm_mmap
            print(f"✅ 成功连接到共享内存 ({size} bytes)")
        except Exception as e:
            print(f"❌ 共享内存连接失败: {e}")
            raise e

    def _read_shm(self):
        """从共享内存读取数据"""
        try:
            self.shm.seek(0)
            raw_data = self.shm.read(ctypes.sizeof(SharedMemoryData))
            return SharedMemoryData.from_buffer_copy(raw_data)
        except Exception as e:
            print(f"❌ 共享内存读取错误: {e}")
            return None

    def _write_shm(self, data_struct):
        """将数据结构写入共享内存"""
        try:
            self.shm.seek(0)
            self.shm.write(data_struct)
            self.shm.flush()
            return True
        except Exception as e:
            print(f"❌ 共享内存写入错误: {e}")
            return False

    def wait_for_state(self, timeout_seconds=60):
        """等待C端发送状态"""
        print(f"🔄 等待C端发送状态... (超时: {timeout_seconds}秒)")

        timeout_counter = 0
        max_timeout = timeout_seconds * 100  # 10ms检查一次

        while timeout_counter < max_timeout:
            data = self._read_shm()
            if data and data.ready_for_inference:
                print(f"✅ 收到C端状态 (等待了 {timeout_counter * 0.01:.2f}秒)")
                return data
            time.sleep(0.01)
            timeout_counter += 1

            # 每10秒打印一次进度
            if timeout_counter % 1000 == 0:
                elapsed = timeout_counter * 0.01
                print(f"⏳ 仍在等待状态... {elapsed:.1f}s 已过去")

        print(f"❌ 等待超时 ({timeout_seconds}秒)")
        return None

    def send_weights(self, weights):
        """发送权重给C端"""
        data = self._read_shm()
        if data is None:
            return False

        data.weights[:] = weights
        data.weights_updated = 1
        data.ready_for_inference = 0

        success = self._write_shm(data)
        if success:
            self.step_count += 1
            print(f"[Step {self.step_count}] 发送权重: {weights}")
        return success

    def run_test_loop(self, max_steps=5):
        """运行测试循环"""
        print(f"\n🧪 开始测试循环 (最多 {max_steps} 步)...")

        for step in range(max_steps):
            print(f"\n--- Step {step + 1} ---")

            # 等待C端状态
            data = self.wait_for_state(timeout_seconds=30)
            if data is None:
                print("❌ 无法获取状态，退出测试")
                break

            # 显示状态信息
            state = np.array(data.state)
            print(f"📊 状态向量: shape={state.shape}")
            print(f"📊 性能指标: miss_ratio={data.miss_ratio:.4f}, byte_miss_ratio={data.byte_miss_ratio:.4f}")

            # 生成随机权重
            weights = np.random.rand(FEATURE_DIM)
            weights = weights / weights.sum()  # 归一化

            # 发送权重
            if not self.send_weights(weights):
                print("❌ 权重发送失败，退出测试")
                break

            print(f"✅ Step {step + 1} 完成")

        print("\n🏁 测试循环结束")

    def close(self):
        """清理资源"""
        if self.shm_mmap:
            self.shm_mmap.close()
        if self.shm_file:
            self.shm_file.close()
        print("🧹 环境已清理")

def main():
    print("=" * 60)
    print("LOH Simple Communication Test")
    print("=" * 60)
    print(f"状态维度: {CONTEXT_DIM}")
    print(f"动作维度: {FEATURE_DIM}")
    print(f"共享内存键: {SHM_KEY}")
    print()

    env = None
    try:
        env = SimpleLohEnv()

        print("✅ 共享内存创建成功！")
        print("💡 现在可以启动C端缓存模拟器了")
        print("💡 此脚本将等待C端发送状态并进行简单的交互测试")

        # 运行测试循环
        env.run_test_loop(max_steps=10)

    except KeyboardInterrupt:
        print("\n⚠️ 用户中断测试")
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if env:
            env.close()

if __name__ == "__main__":
    main()
