#!/usr/bin/env python3
"""
生成 frequency-dominant 合成 trace（CSV: time,obj-id,obj-size,ttl）

设计思路：
  - 纯 i.i.d. Zipf 采样：每次请求独立从 Zipf(alpha=2.0) 分布中选对象
  - N_OBJECTS=100000 个对象，alpha=2.0 意味着 top-1 占 ~61% 请求
  - 固定 size=10000（消除 size 信号）
  - 无时间局部性（i.i.d.），recency 完全无用
  - LFU 精确匹配 Zipf 分布 → 最优

验证：
  - LFU 直接按频率排序 → 命中 ranking 与 Zipf 一致 → 最优
  - LRU 被随机访问的冷对象不断冲刷 → 差
  - GDSF = LFU（size 相同时退化为频率策略）
  - LOH CMA-ES 需要时间学习 → 可能不如纯 LFU 好
"""

import sys
import numpy as np

N_REQUESTS = 10_000_000
N_OBJECTS = 500_000       # 大对象池，working set ~5GB
OBJ_SIZE = 10_000
ZIPF_ALPHA = 1.0          # 经典 Zipf（非极端），区分度好
SEED = 42
BATCH = 1_000_000

OUTPUT = sys.argv[1] if len(sys.argv) > 1 else "lfutest2_10m.csv"


def zipf_pmf(n, alpha):
    """计算 Zipf PMF: P(k) = 1/k^alpha / H_n"""
    ranks = np.arange(1, n + 1, dtype=np.float64)
    weights = 1.0 / np.power(ranks, alpha)
    weights /= weights.sum()
    return weights


def main():
    rng = np.random.RandomState(SEED)
    pmf = zipf_pmf(N_OBJECTS, ZIPF_ALPHA)

    # 预计算累积分布函数用于快速采样
    cdf = np.cumsum(pmf)

    print(f"Zipf alpha={ZIPF_ALPHA}, top1={pmf[0]*100:.1f}%, top10={pmf[:10].sum()*100:.1f}%, "
          f"top100={pmf[:100].sum()*100:.1f}%")

    with open(OUTPUT, "wb") as f:
        for batch_start in range(0, N_REQUESTS, BATCH):
            bs = min(BATCH, N_REQUESTS - batch_start)
            # i.i.d. 采样：每次独立从 Zipf 分布采样
            obj_ids = rng.choice(N_OBJECTS, size=bs, p=pmf)

            times = np.arange(batch_start + 1, batch_start + bs + 1)
            sizes = np.full(bs, OBJ_SIZE, dtype=np.int32)
            zeros = np.zeros(bs, dtype=np.int32)
            data = np.column_stack([times, obj_ids, sizes, zeros])
            lines = [f"{r[0]},{r[1]},{r[2]},{r[3]}\n" for r in data]
            f.write("".join(lines).encode())

            done = batch_start + bs
            print(f"  {done / 1e6:.1f}M / {N_REQUESTS / 1e6:.0f}M", flush=True)

    print(f"Done: {OUTPUT}")


if __name__ == "__main__":
    main()
