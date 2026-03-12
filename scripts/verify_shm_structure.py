#!/usr/bin/env python3
"""
验证Python端与C端共享内存结构的对齐
"""

import ctypes
import sys
import os

# 添加scripts目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))

from loh_actor_critic_sb3 import (
    PenaltyEntry, create_shared_memory_class,
    CONTEXT_DIM, FEATURE_DIM, MAX_PENALTY_QUEUE_SIZE
)

def print_structure_info():
    """打印Python结构体的详细信息"""
    print("=" * 60)
    print("Python端共享内存结构验证")
    print("=" * 60)

    # 创建共享内存类
    SharedMemoryData = create_shared_memory_class(CONTEXT_DIM)

    print(f"\n配置:")
    print(f"  CONTEXT_DIM: {CONTEXT_DIM}")
    print(f"  FEATURE_DIM: {FEATURE_DIM}")
    print(f"  MAX_PENALTY_QUEUE_SIZE: {MAX_PENALTY_QUEUE_SIZE}")

    print(f"\nPenaltyEntry 结构:")
    print(f"  sizeof(PenaltyEntry): {ctypes.sizeof(PenaltyEntry)} 字节")
    for name, _ in PenaltyEntry._fields_:
        offset = getattr(PenaltyEntry, name).offset
        size = getattr(PenaltyEntry, name).size
        print(f"    {name:25s}: offset={offset:4d}, size={size:4d}")

    print(f"\nSharedMemoryData 结构:")
    print(f"  sizeof(SharedMemoryData): {ctypes.sizeof(SharedMemoryData)} 字节")
    for name, _ in SharedMemoryData._fields_:
        offset = getattr(SharedMemoryData, name).offset
        size = getattr(SharedMemoryData, name).size
        print(f"    {name:25s}: offset={offset:4d}, size={size:4d}")

    print("\n" + "=" * 60)
    print("请与C端的结构大小进行比对:")
    print("在C端添加如下代码到LOH_init中:")
    print("  printf(\"C sizeof(penalty_entry_t) = %zu\\n\", sizeof(penalty_entry_t));")
    print("  printf(\"C sizeof(shm_data_t) = %zu\\n\", sizeof(shm_data_t));")
    print("=" * 60)

    return ctypes.sizeof(SharedMemoryData)

if __name__ == "__main__":
    total_size = print_structure_info()
    print(f"\n总大小: {total_size} 字节")

    # 计算期望的大小（手动验证）
    expected_size = (
        4 * 4 +  # 4个int (ready_for_inference, weights_updated, terminate, is_training)
        8 * CONTEXT_DIM +  # state数组
        8 * FEATURE_DIM +  # weights数组
        8 +  # total_evicted_bytes (uint64_t)
        8 +  # total_evicted_count (uint64_t)
        8 +  # state_version (uint64_t)
        8 +  # ack_version (uint64_t)
        8 +  # timestamp (int64_t)
        4 +  # penalty_queue_size (int)
        4 +  # padding (对齐到8字节边界)
        ctypes.sizeof(PenaltyEntry) * MAX_PENALTY_QUEUE_SIZE  # penalty_queue数组
    )

    print(f"期望大小 (手动计算): {expected_size} 字节")

    if total_size == expected_size:
        print("✅ 大小匹配!")
    else:
        print(f"⚠️  大小不匹配! 差异: {total_size - expected_size} 字节")
        print("   这可能是由于结构体对齐造成的，请检查C端的实际大小")
