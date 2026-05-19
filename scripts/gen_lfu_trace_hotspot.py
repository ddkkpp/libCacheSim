#!/usr/bin/env python3
"""
Generate an LFU-favoring anti-LRU trace with hot bursts and long cold scans.

Design goal:
- LFU should be much lower than LRU/Size at cache_size=0.1.

CSV format: time,obj-id,obj-size,ttl
"""

import sys

import numpy as np


N_REQUESTS = 10_000_000
SEED = 42

N_OBJECTS = 100_000
N_HOT = 9_000
N_COLD = N_OBJECTS - N_HOT

# One cycle = hot burst + long cold scan.
# With object-uniform traces and cache_size=0.1, cache can hold ~10k objects.
# SCAN_UNIQUE > 10k intentionally flushes LRU's recency state.
HOT_PASS_LEN = 9_000
SCAN_UNIQUE = 10_001

# Inside hot burst, use a mild Zipf to amplify stable hot frequency ranking.
HOT_ZIPF_ALPHA = 1.10

OBJ_SIZE = 10_000

OUTPUT = sys.argv[1] if len(sys.argv) > 1 else "lfutest_hotspot_10m.csv"


def main() -> None:
    rng = np.random.RandomState(SEED)

    hot_ids = np.arange(0, N_HOT, dtype=np.int32)
    cold_ids = np.arange(N_HOT, N_HOT + N_COLD, dtype=np.int32)

    hot_ranks = np.arange(1, N_HOT + 1, dtype=np.float64)
    hot_pmf = 1.0 / np.power(hot_ranks, HOT_ZIPF_ALPHA)
    hot_pmf /= hot_pmf.sum()

    print(
        f"n_objects={N_OBJECTS}, hot={N_HOT}, cold={N_COLD}, "
        f"hot_pass_len={HOT_PASS_LEN}, scan_unique={SCAN_UNIQUE}, obj_size={OBJ_SIZE}, "
        f"hot_zipf_alpha={HOT_ZIPF_ALPHA}, "
        f"hot_top1={hot_pmf[0] * 100:.2f}%",
        flush=True,
    )

    t = 1
    cycle = 0
    with open(OUTPUT, "w", encoding="utf-8") as output_file:
        while t <= N_REQUESTS:
            cycle += 1

            # Phase A: one hot pass with minimal short-term recency advantage.
            n_hot = min(HOT_PASS_LEN, N_REQUESTS - t + 1)
            pass_ids = rng.choice(hot_ids, size=n_hot, replace=False if n_hot <= hot_ids.size else True, p=hot_pmf)
            for oid in pass_ids:
                output_file.write(f"{t},{int(oid)},{OBJ_SIZE},0\n")
                t += 1
                if t > N_REQUESTS:
                    break

            if t > N_REQUESTS:
                break

            # Phase B: long unique cold scan to destroy recency ordering.
            n_scan = min(SCAN_UNIQUE, N_REQUESTS - t + 1, cold_ids.size)
            scan_ids = rng.choice(cold_ids, size=n_scan, replace=False)
            for oid in scan_ids:
                output_file.write(f"{t},{int(oid)},{OBJ_SIZE},0\n")
                t += 1
                if t > N_REQUESTS:
                    break

            if cycle % 5 == 0 or t > N_REQUESTS:
                done = t - 1
                print(f"  cycle={cycle} {done / 1e6:.1f}M / {N_REQUESTS / 1e6:.0f}M", flush=True)

    print(f"Done: {OUTPUT}", flush=True)


if __name__ == "__main__":
    main()
