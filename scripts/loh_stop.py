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
WEIGHT_DIM = 7
DEFAULT_KEY = int(os.environ.get("LOH_SHM_KEY", "9876"))

def create_shared_memory_class(context_dim: int):
    class SharedMemoryData(ctypes.Structure):
        _fields_ = [
            ("ready_for_inference", ctypes.c_int),
            ("weights_updated", ctypes.c_int),
            ("terminate", ctypes.c_int),
            ("is_training", ctypes.c_int),
            ("state", ctypes.c_double * context_dim),
            ("weights", ctypes.c_double * WEIGHT_DIM),
            # 与 loh_actor_critic_sb3.py 保持一致
            ("total_evicted_bytes", ctypes.c_uint64),
            ("total_evicted_count", ctypes.c_uint64),
            ("state_version", ctypes.c_uint64),
            ("ack_version", ctypes.c_uint64),
            ("timestamp", ctypes.c_int64),
            ("pending_penalty_count", ctypes.c_int),
        ]
    return SharedMemoryData

def main():
    # 共享内存键：优先命令行参数，其次环境变量，最后默认
    key = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_KEY
    shm_path = f"/dev/shm/loh_ac_{key}"
    if not os.path.exists(shm_path):
        print(f"共享内存文件不存在: {shm_path}")
        sys.exit(1)

    N_TOPK_SAMPLES = 32
    SAMPLES_PER_EVICTION = 4

    # 根据环境变量推导状态维度（与 loh_actor_critic_sb3.py 保持一致）
    missratio_dim = 2

    hit_miss_flag = os.environ.get("LOH_INCLUDE_HIT_MISS_FEATURES", "0").strip().lower()
    hit_miss_dim = 24 if hit_miss_flag in {"1", "true", "yes", "on"} else 0

    cache_flag = os.environ.get("LOH_INCLUDE_CACHE_FEATURES", "0").strip().lower()
    cache_dim = 12 if cache_flag in {"1", "true", "yes", "on"} else 0

    cand_flag = os.environ.get("LOH_INCLUDE_CANDIDATE_FEATURES", "0").strip().lower()
    cand_dim = 72 if cand_flag in {"1", "true", "yes", "on"} else 0

    topk_flag = os.environ.get("LOH_INCLUDE_TOPK_CANDIDATE_FEATURES", "0").strip().lower()
    topk_dim = (N_TOPK_SAMPLES * 6) if topk_flag in {"1", "true", "yes", "on"} else 0

    avgtopk_flag = os.environ.get("LOH_INCLUDE_AVGTOPK_CANDIDATE_FEATURES", "1").strip().lower()
    avgtopk_dim = (SAMPLES_PER_EVICTION * 6) if avgtopk_flag in {"1", "true", "yes", "on"} else 0

    context_dim = missratio_dim + hit_miss_dim + cache_dim + cand_dim + topk_dim + avgtopk_dim
    print(f"Calculated context_dim={context_dim} (missratio={missratio_dim}, hit_miss={hit_miss_dim}, cache={cache_dim}, cand={cand_dim}, topk={topk_dim}, avgtopk={avgtopk_dim})")

    SharedMemoryData = create_shared_memory_class(context_dim)
    size = ctypes.sizeof(SharedMemoryData)

    # 检查文件大小
    file_size = os.path.getsize(shm_path)
    if file_size < size:
        print(f"Warning: file size ({file_size}) < expected size ({size}), using file size")
        size = file_size

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
