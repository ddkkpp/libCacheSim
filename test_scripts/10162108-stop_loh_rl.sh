#!/bin/bash
# 优雅停止LOH RL测试：将terminate=1写入共享内存，并终止相关进程
set -e

SHM_PATH=/dev/shm/loh_ac_9876

echo "[stop_loh_rl] 尝试设置terminate=1..."
python3 - <<'PY'
import ctypes, mmap, os, sys

FEATURE_DIM=6
CONTEXT_DIM=26

class SharedMemoryData(ctypes.Structure):
    _fields_ = [
        ("ready_for_inference", ctypes.c_int),
        ("weights_updated", ctypes.c_int),
        ("terminate", ctypes.c_int),
        ("python_ready", ctypes.c_int),
        ("state", ctypes.c_double * CONTEXT_DIM),
        ("weights", ctypes.c_double * FEATURE_DIM),
        ("miss_ratio", ctypes.c_double),
        ("byte_miss_ratio", ctypes.c_double),
        ("reward", ctypes.c_double),
        ("state_version", ctypes.c_uint64),
        ("ack_version", ctypes.c_uint64),
        ("timestamp", ctypes.c_int64),
    ]

path = "/dev/shm/loh_ac_9876"
if not os.path.exists(path):
    print("[stop_loh_rl] 共享内存未找到，跳过terminate设置。")
    sys.exit(0)

size = ctypes.sizeof(SharedMemoryData)
with open(path, 'r+b') as f:
    mm = mmap.mmap(f.fileno(), size)
    try:
        mm.seek(0)
        raw = mm.read(size)
        data = SharedMemoryData.from_buffer_copy(raw)
        data.terminate = 1
        data.python_ready = 1
        buf = ctypes.string_at(ctypes.byref(data), size)
        mm.seek(0)
        mm.write(buf)
        mm.flush()
        print("[stop_loh_rl] 已写入 terminate=1。")
    finally:
        mm.close()
PY

echo "[stop_loh_rl] 尝试终止Python和cachesim进程..."
pkill -f scripts/loh_actor_critic_sb3.py || true
pkill -f "_build_dbg/bin/cachesim.* LOH" || true

if [ -f "$SHM_PATH" ]; then
  rm -f "$SHM_PATH"
  echo "[stop_loh_rl] 已删除共享内存文件。"
fi

echo "[stop_loh_rl] 完成。"
