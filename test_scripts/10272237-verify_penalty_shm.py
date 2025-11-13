#!/usr/bin/env python3
"""
验证 C 端写入的 penalty 数据是否正确

用法：
  python3 verify_penalty_shm.py

前提：
  1. C 端已启动并至少执行过一次 sync（写入了 penalty 数据）
  2. 共享内存文件存在：/dev/shm/loh_ac_9876
"""

import ctypes
import os
import struct

# 共享内存文件路径
SHM_FILENAME = "/dev/shm/loh_ac_9876"

# C 端结构体定义（需与 LOH.c 中的定义完全一致）
class PenaltyEntry(ctypes.Structure):
    _fields_ = [
        ("penalty_version", ctypes.c_uint64),
        ("eviction_to_access", ctypes.c_int64),
        ("obj_size", ctypes.c_int64),
        ("obj_id", ctypes.c_uint64),
    ]

# 简化的 shm_data_t（只包含关键字段）
class SharedMemoryData(ctypes.Structure):
    _fields_ = [
        ("ready_for_inference", ctypes.c_int),
        ("weights_updated", ctypes.c_int),
        ("terminate", ctypes.c_int),
        ("is_training", ctypes.c_int),
        ("state", ctypes.c_double * 26),  # 假设 26 维
        ("weights", ctypes.c_double * 6),
        ("total_evicted_bytes", ctypes.c_uint64),
        ("total_evicted_count", ctypes.c_uint64),
        ("state_version", ctypes.c_uint64),
        ("ack_version", ctypes.c_uint64),
        ("timestamp", ctypes.c_int64),
        ("pending_penalty_count", ctypes.c_int),
    ]

def verify_penalty_data():
    """验证 penalty 数据的读取"""
    if not os.path.exists(SHM_FILENAME):
        print(f"[ERROR] Shared memory file not found: {SHM_FILENAME}")
        print("Make sure C process is running and has written data.")
        return False

    try:
        with open(SHM_FILENAME, "rb") as f:
            # 1. 读取 shm_data_t
            shm_size = ctypes.sizeof(SharedMemoryData)
            shm_bytes = f.read(shm_size)

            if len(shm_bytes) < shm_size:
                print(f"[ERROR] Incomplete shm_data_t: got {len(shm_bytes)}/{shm_size} bytes")
                return False

            shm_data = SharedMemoryData.from_buffer_copy(shm_bytes)

            print(f"[INFO] Read shm_data_t ({shm_size} bytes)")
            print(f"  - ready_for_inference: {shm_data.ready_for_inference}")
            print(f"  - weights_updated: {shm_data.weights_updated}")
            print(f"  - state_version: {shm_data.state_version}")
            print(f"  - pending_penalty_count: {shm_data.pending_penalty_count}")
            print(f"  - total_evicted_bytes: {shm_data.total_evicted_bytes}")
            print(f"  - total_evicted_count: {shm_data.total_evicted_count}")

            # 2. 检查是否有 penalty 数据
            if shm_data.pending_penalty_count <= 0:
                print(f"[INFO] No penalty data (pending_penalty_count={shm_data.pending_penalty_count})")
                return True

            # 3. 读取 penalty 数据
            penalty_count = shm_data.pending_penalty_count
            penalty_size = ctypes.sizeof(PenaltyEntry)
            print(f"\n[INFO] Reading {penalty_count} penalty entries ({penalty_size} bytes each)...")

            penalties = []
            for i in range(penalty_count):
                penalty_bytes = f.read(penalty_size)
                if len(penalty_bytes) < penalty_size:
                    print(f"[ERROR] Incomplete penalty data at index {i}: got {len(penalty_bytes)}/{penalty_size} bytes")
                    break

                penalty = PenaltyEntry.from_buffer_copy(penalty_bytes)
                penalties.append(penalty)

            # 4. 打印 penalty 数据
            print(f"\n[SUCCESS] Read {len(penalties)} penalty entries:")
            for i, p in enumerate(penalties):
                print(f"  [{i}] version={p.penalty_version}, "
                      f"evict_to_access={p.eviction_to_access}, "
                      f"size={p.obj_size}, obj_id={p.obj_id}")

            # 5. 验证数据合理性
            print(f"\n[VALIDATION]")
            valid_count = 0
            for i, p in enumerate(penalties):
                if p.penalty_version > 0 and p.obj_size > 0:
                    valid_count += 1
                else:
                    print(f"  [WARNING] Penalty {i} has invalid data (version={p.penalty_version}, size={p.obj_size})")

            print(f"  Valid penalties: {valid_count}/{len(penalties)}")

            return valid_count == len(penalties)

    except Exception as e:
        print(f"[ERROR] Failed to read penalty data: {e}")
        import traceback
        traceback.print_exc()
        return False

def print_struct_sizes():
    """打印结构体大小（用于调试）"""
    print("\n[DEBUG] Structure sizes:")
    print(f"  sizeof(SharedMemoryData) = {ctypes.sizeof(SharedMemoryData)} bytes")
    print(f"  sizeof(PenaltyEntry) = {ctypes.sizeof(PenaltyEntry)} bytes")

    print("\n[DEBUG] PenaltyEntry field offsets:")
    for field_name, field_type in PenaltyEntry._fields_:
        offset = getattr(PenaltyEntry, field_name).offset
        print(f"  {field_name}: offset={offset}, size={ctypes.sizeof(field_type)}")

if __name__ == "__main__":
    print("=" * 60)
    print("Penalty Data Verification Tool")
    print("=" * 60)

    print_struct_sizes()

    print("\n" + "=" * 60)
    print("Reading penalty data from shared memory...")
    print("=" * 60)

    success = verify_penalty_data()

    print("\n" + "=" * 60)
    if success:
        print("[RESULT] ✅ Verification PASSED")
    else:
        print("[RESULT] ❌ Verification FAILED")
    print("=" * 60)
