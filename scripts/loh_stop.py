#!/usr/bin/env python3
"""
向共享内存写 terminate=1 的小工具，用于优雅停止两端进程。
"""
import ctypes
import mmap
import os
import sys
import time

FEATURE_DIM = 6
DEFAULT_KEY = int(os.environ.get("LOH_SHM_KEY", "9876"))

def create_shared_memory_class(context_dim: int):
    class SharedMemoryData(ctypes.Structure):
        _fields_ = [
            ("ready_for_inference", ctypes.c_int),
            ("weights_updated", ctypes.c_int),
            ("terminate", ctypes.c_int),
            ("is_training", ctypes.c_int),
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

def main():
    # 共享内存键：优先命令行参数，其次环境变量，最后默认
    key = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_KEY
    shm_path = f"/dev/shm/loh_ac_{key}"
    if not os.path.exists(shm_path):
        print(f"共享内存文件不存在: {shm_path}")
        sys.exit(1)
    # 尝试从环境获取状态维度（默认26）
    try:
        context_dim = int(os.environ.get("LOH_STATE_DIM", "26"))
    except Exception:
        context_dim = 26
    SharedMemoryData = create_shared_memory_class(context_dim)
    size = ctypes.sizeof(SharedMemoryData)
    with open(shm_path, 'r+b') as f:
        mm = mmap.mmap(f.fileno(), size)
        # 读取
        mm.seek(0)
        raw = mm.read(size)
        data = SharedMemoryData.from_buffer_copy(raw)
        # 设置terminate
        data.terminate = 1
        # 不修改 is_training 字段
        # 写回
        mm.seek(0)
        mm.write(ctypes.string_at(ctypes.byref(data), size))
        mm.flush()
        print(f"已写入 terminate=1，state_version={int(data.state_version)}, ack_version={int(data.ack_version)}")
        mm.close()

if __name__ == "__main__":
    main()
