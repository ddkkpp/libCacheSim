#!/usr/bin/env python3
"""
生成 recency-dominant 合成 trace（CSV 格式: time,obj-id,obj-size,ttl）

设计：
  - N_OBJECTS=50000 个对象，固定 size=10000B
  - 维护"热窗口"（最近访问的 WINDOW=2000 个不同对象）
  - 每次请求：
    * 概率 P_RECENT=0.85 → 从热窗口均匀采样
    * 概率 1-P_RECENT=0.15 → 从全部 50000 对象均匀采样
  - 新对象进入热窗口时，最老的自然滑出

这使得：
  - LRU 优势明显：缓存保留热窗口内的对象 → 命中率高
  - LFU 无优势：长期所有对象频率趋同（无 Zipf 偏斜）
  - Size 无优势：对象大小均匀
"""

import sys
import numpy as np

N_REQUESTS = 10_000_000
N_OBJECTS = 100_000
OBJ_SIZE = 10_000
WINDOW = 1000             # 默认固定为 sweep 选中版本（W=1000）
P_RECENT = 0.70           # 默认固定为 sweep 选中版本（P=0.70）
SEED = 42
BATCH = 500_000

OUTPUT = sys.argv[1] if len(sys.argv) > 1 else "recencytest_10m.csv"


def main():
    rng = np.random.RandomState(SEED)

    # 热窗口用 circular buffer
    win_arr = np.arange(WINDOW, dtype=np.int32)
    win_set = set(range(WINDOW))
    head = 0

    with open(OUTPUT, "wb") as f:
        for batch_start in range(0, N_REQUESTS, BATCH):
            bs = min(BATCH, N_REQUESTS - batch_start)
            coin = rng.random(bs)
            win_idx = rng.randint(0, WINDOW, bs)
            all_idx = rng.randint(0, N_OBJECTS, bs)

            obj_ids = np.empty(bs, dtype=np.int32)
            for i in range(bs):
                if coin[i] < P_RECENT:
                    obj_ids[i] = win_arr[win_idx[i]]
                else:
                    oid = all_idx[i]
                    obj_ids[i] = oid
                    if oid not in win_set:
                        old = int(win_arr[head])
                        win_set.discard(old)
                        win_arr[head] = oid
                        win_set.add(oid)
                        head = (head + 1) % WINDOW

            # 向量化字符串构建
            times = np.arange(batch_start + 1, batch_start + bs + 1)
            sizes = np.full(bs, OBJ_SIZE, dtype=np.int32)
            zeros = np.zeros(bs, dtype=np.int32)
            # 用 numpy 拼接所有列，再写入
            data = np.column_stack([times, obj_ids, sizes, zeros])
            lines = [f"{r[0]},{r[1]},{r[2]},{r[3]}\n" for r in data]
            f.write("".join(lines).encode())

            done = batch_start + bs
            print(f"  {done / 1e6:.1f}M / {N_REQUESTS / 1e6:.0f}M", flush=True)

    print(f"Done: {OUTPUT}")


if __name__ == "__main__":
    main()
