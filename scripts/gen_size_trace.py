#!/usr/bin/env python3
"""
生成 size-dominant 合成 trace（CSV: time,obj-id,obj-size,ttl）

设计思路：
  - 极端大小分布：700K 小对象（128B, 70%) + 200K 中对象（10KB, 20%) + 100K 大对象（1MB, 10%)
  - 总共 1000K 个对象
  - 每次请求均匀随机从各层采样（保证频率无信息）
  - 无时间局部性、频率差异（i.i.d. 均匀采样）
  - SIZE 精确匹配大小分布 → 最优

改进（vs v1）：
  - 增大大小层级差距：从 (128B, 10KB, 1MB) 改为 (64B, 64KB, 16MB)
  - 这使得缓存命中率对大小维度的敏感度更高
"""

import sys
import numpy as np

N_REQUESTS = 10_000_000
# 两层大小分布：小对象极多但极小，大对象极少但极大，SIZE 策略优势最显著
N_SMALL = 90_000         # 90%，极小对象
N_LARGE = 10_000         # 10%，极大对象
N_OBJECTS = N_SMALL + N_LARGE  # = 100_000，与 recencytest/lfutest2 一致

SIZE_SMALL = 64           # 64B，极小
SIZE_LARGE = 4_194_304    # 4 MB，极大
SIZE_MEDIUM = SIZE_SMALL  # 兼容旧代码

SEED = 42
BATCH = 1_000_000

OUTPUT = sys.argv[1] if len(sys.argv) > 1 else "sizetest_10m.csv"


def main():
    rng = np.random.RandomState(SEED)

    # 构建对象大小数组（两层：极小 + 极大）
    sizes = np.concatenate([
        np.full(N_SMALL, SIZE_SMALL, dtype=np.int32),
        np.full(N_LARGE, SIZE_LARGE, dtype=np.int32)
    ])

    print(f"Size distribution: {N_SMALL/1e6:.1f}M × {SIZE_SMALL}B, "
          f"{N_LARGE/1e6:.1f}M × {SIZE_LARGE}B")
    print(f"Object pool: {N_OBJECTS/1e6:.1f}M objects")

    with open(OUTPUT, "wb") as f:
        for batch_start in range(0, N_REQUESTS, BATCH):
            bs = min(BATCH, N_REQUESTS - batch_start)
            # 均匀采样所有对象池（i.i.d.，无局部性）
            obj_ids = rng.randint(0, N_OBJECTS, bs, dtype=np.int32)

            times = np.arange(batch_start + 1, batch_start + bs + 1)
            obj_sizes = sizes[obj_ids]
            zeros = np.zeros(bs, dtype=np.int32)

            data = np.column_stack([times, obj_ids, obj_sizes, zeros])
            lines = [f"{r[0]},{r[1]},{r[2]},{r[3]}\n" for r in data]
            f.write("".join(lines).encode())

            done = batch_start + bs
            print(f"  {done / 1e6:.1f}M / {N_REQUESTS / 1e6:.0f}M", flush=True)

    print(f"Done: {OUTPUT}")


if __name__ == "__main__":
    main()
