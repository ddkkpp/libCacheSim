#!/usr/bin/env python3
"""
生成 frequency-dominant 合成 trace（CSV: time,obj-id,obj-size,ttl）

设计思路：
  - 全局单一 Zipf(alpha) 分布，i.i.d. 采样
  - 固定 size=10000（消除 size 信号）
  - 无时间局部性，重点突出 frequency 信号

CLI: gen_lfu_trace.py [output] [zipf_alpha]
"""

import sys
import numpy as np

N_REQUESTS = 10_000_000
N_OBJECTS = 100_000
OBJ_SIZE = 10_000
SEED = 42
BATCH = 1_000_000

OUTPUT     = sys.argv[1] if len(sys.argv) > 1 else "lfutest2_10m.csv"
ZIPF_ALPHA = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0


def zipf_pmf(n, alpha):
    """计算 Zipf PMF: P(k) = 1/k^alpha / H_n"""
    ranks = np.arange(1, n + 1, dtype=np.float64)
    weights = 1.0 / np.power(ranks, alpha)
    weights /= weights.sum()
    return weights


def main():
    rng = np.random.RandomState(SEED)
    pmf = zipf_pmf(N_OBJECTS, ZIPF_ALPHA)
    obj_ids_all = np.arange(N_OBJECTS, dtype=np.int32)

    print(f"n_objects={N_OBJECTS}, zipf_alpha={ZIPF_ALPHA}, top1={pmf[0]*100:.2f}%", flush=True)

    with open(OUTPUT, "wb") as f:
        for batch_start in range(0, N_REQUESTS, BATCH):
            bs = min(BATCH, N_REQUESTS - batch_start)
            obj_ids = rng.choice(obj_ids_all, size=bs, p=pmf)
            times = np.arange(batch_start + 1, batch_start + bs + 1, dtype=np.int32)
            sizes = np.full(bs, OBJ_SIZE, dtype=np.int32)
            zeros = np.zeros(bs, dtype=np.int32)
            data = np.column_stack([times, obj_ids, sizes, zeros])
            lines = [f"{r[0]},{r[1]},{r[2]},{r[3]}\n" for r in data]
            f.write("".join(lines).encode())

    print(f"Done: {OUTPUT}", flush=True)


if __name__ == "__main__":
    main()
